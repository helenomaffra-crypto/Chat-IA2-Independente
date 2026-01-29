"""
Handlers pequenos para tools de "sistema" (observabilidade, fontes de dados, aprendizado).

Objetivo: evitar crescer monólitos (ChatService / ToolExecutionService) com lógica grande.
Esses handlers são usados pelo ToolExecutionService (e, via ToolRouter, pelo SistemaAgent).
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemToolsHandler:
    """Coleção de handlers estáticos para ToolExecutionService."""

    @staticmethod
    def verificar_fontes_dados(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Tool: verificar_fontes_dados (sem argumentos)."""
        # SQLite
        sqlite_ok = False
        sqlite_error: Optional[str] = None
        try:
            from db_manager import get_db_connection

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            conn.close()
            sqlite_ok = True
        except Exception as e:
            sqlite_ok = False
            sqlite_error = str(e)

        # SQL Server (não notifica erro para não gerar alertas só por auditoria)
        sql_ok = False
        sql_error: Optional[str] = None
        sql_mode = os.getenv("SQL_SERVER_MODE", "auto")
        sql_office = os.getenv("SQL_SERVER_OFFICE", "")
        sql_vpn = os.getenv("SQL_SERVER_VPN", "")
        sql_host = os.getenv("SQL_SERVER_HOST", "")
        try:
            from utils.sql_server_adapter import get_sql_adapter

            adapter = get_sql_adapter()
            res = adapter.test_connection(notificar_erro=False)
            sql_ok = bool(res.get("success"))
            sql_error = res.get("error")
        except Exception as e:
            sql_ok = False
            sql_error = str(e)

        # Configs principais (apenas presença/configuração)
        kanban_url = os.getenv("KANBAN_API_URL", "")
        portal_token = bool(os.getenv("PORTAL_UNICO_TOKEN"))
        integracomex_token = bool(os.getenv("INTEGRACOMEX_TOKEN"))
        ai_provider = os.getenv("DUIMP_AI_PROVIDER", "")
        ai_key = bool(os.getenv("DUIMP_AI_API_KEY"))
        assistant_id = os.getenv("ASSISTANT_ID_LEGISLACAO", "")
        vector_store_id = os.getenv("VECTOR_STORE_ID_LEGISLACAO", "")

        def _ok(flag: bool) -> str:
            return "✅" if flag else "❌"

        linhas = []
        linhas.append("🧩 **Fontes de dados / integrações**\n")
        linhas.append(f"- SQLite: {_ok(sqlite_ok)}")
        if sqlite_error and not sqlite_ok:
            linhas.append(f"  - erro: {sqlite_error}")

        linhas.append(f"- SQL Server: {_ok(sql_ok)} (modo={sql_mode})")
        if sql_office or sql_vpn:
            if sql_office:
                linhas.append(f"  - office: `{sql_office}`")
            if sql_vpn:
                linhas.append(f"  - vpn: `{sql_vpn}`")
        elif sql_host:
            linhas.append(f"  - host: `{sql_host}`")
        if sql_error and not sql_ok:
            linhas.append(f"  - erro: {sql_error}")
            if sql_office and sql_vpn and (sql_mode or "").lower() in ("auto", "vpn", "office"):
                linhas.append("  - dica: se estiver fora do escritório, conecte a VPN e tente novamente.")

        linhas.append(f"- Kanban API URL configurada: {_ok(bool(kanban_url))} `{kanban_url or '(vazio)'}`")
        linhas.append(f"- Portal Único token: {_ok(portal_token)}")
        linhas.append(f"- IntegraComex token: {_ok(integracomex_token)}")
        linhas.append(f"- IA provider: `{ai_provider or '(não definido)'}` | API key: {_ok(ai_key)}")
        linhas.append(f"- Legislação (Assistants/RAG): assistant_id={_ok(bool(assistant_id))}, vector_store_id={_ok(bool(vector_store_id))}")

        return {
            "sucesso": True,
            "resposta": "\n".join(linhas).strip(),
            "dados": {
                "sqlite": {"ok": sqlite_ok, "erro": sqlite_error},
                "sql_server": {
                    "ok": sql_ok,
                    "erro": sql_error,
                    "mode": sql_mode,
                    "office": sql_office,
                    "vpn": sql_vpn,
                    "host": sql_host,
                },
                "kanban": {"url": kanban_url},
                "tokens": {"portal_unico": portal_token, "integracomex": integracomex_token},
                "ai": {"provider": ai_provider, "api_key_configurada": ai_key},
                "legislacao_rag": {"assistant_id": assistant_id, "vector_store_id": vector_store_id},
            },
        }

    @staticmethod
    def obter_resumo_aprendizado(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Tool: obter_resumo_aprendizado."""
        session_id = (argumentos.get("session_id") or getattr(context, "session_id", None) or "").strip()
        if not session_id:
            return {
                "sucesso": False,
                "erro": "SESSION_ID_REQUIRED",
                "resposta": "❌ Não consegui identificar a sessão para montar o resumo de aprendizado.",
            }

        from db_manager import get_db_connection

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, tipo_regra, contexto, nome_regra, criado_em, vezes_usado
            FROM regras_aprendidas
            WHERE criado_por = ?
            ORDER BY criado_em DESC
            LIMIT 15
            """,
            (session_id,),
        )
        regras = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT id, nome_exibicao, slug, criado_em, vezes_usado
            FROM consultas_salvas
            WHERE criado_por = ?
            ORDER BY criado_em DESC
            LIMIT 15
            """,
            (session_id,),
        )
        consultas = [dict(r) for r in cur.fetchall()]
        conn.close()

        linhas = []
        linhas.append("📚 **Resumo de aprendizado (sessão)**")
        linhas.append(f"- session_id: `{session_id}`\n")

        linhas.append(f"🎓 **Regras aprendidas criadas nesta sessão:** {len(regras)}")
        if regras:
            for i, r in enumerate(regras[:10], 1):
                nome = r.get("nome_regra") or "Sem nome"
                tipo = r.get("tipo_regra") or "N/A"
                ctx = r.get("contexto") or "-"
                usado = r.get("vezes_usado", 0)
                linhas.append(f"{i}. {nome}  _(tipo={tipo}, contexto={ctx}, usos={usado})_")
        else:
            linhas.append("— nenhuma regra encontrada para esta sessão.")

        linhas.append("")
        linhas.append(f"📋 **Consultas salvas criadas nesta sessão:** {len(consultas)}")
        if consultas:
            for i, c in enumerate(consultas[:10], 1):
                nome = c.get("nome_exibicao") or "Sem nome"
                slug = c.get("slug") or "-"
                usado = c.get("vezes_usado", 0)
                linhas.append(f"{i}. {nome}  _(slug={slug}, usos={usado})_")
        else:
            linhas.append("— nenhuma consulta salva encontrada para esta sessão.")

        return {
            "sucesso": True,
            "resposta": "\n".join(linhas).strip(),
            "dados": {"session_id": session_id, "regras": regras, "consultas": consultas},
        }

    @staticmethod
    def obter_relatorio_observabilidade(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Tool: obter_relatorio_observabilidade."""
        data_inicio = argumentos.get("data_inicio")
        data_fim = argumentos.get("data_fim")

        from services import observability_service

        rel_bilhetadas = observability_service.obter_relatorio_consultas_bilhetadas(
            data_inicio=data_inicio,
            data_fim=data_fim,
            agrupar_por="dia",
        )
        rel_consultas = observability_service.obter_relatorio_uso_consultas_salvas()
        rel_regras = observability_service.obter_relatorio_uso_regras_aprendidas()

        texto = observability_service.formatar_relatorio_observabilidade(rel_bilhetadas, rel_consultas, rel_regras)
        return {
            "sucesso": True,
            "resposta": texto,
            "dados": {
                "consultas_bilhetadas": rel_bilhetadas,
                "consultas_salvas": rel_consultas,
                "regras_aprendidas": rel_regras,
            },
        }

