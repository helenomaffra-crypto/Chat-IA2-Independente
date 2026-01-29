"""
Fase 2: eliminar o "fallback real" restante do ToolRouter (tools que ainda estavam None).

IMPORTANTE: manter este módulo pequeno e focado para não virar monólito.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _normalizar_categoria(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = str(raw).strip().upper()
    if not s:
        return None
    s = re.sub(r"[^A-Z0-9]", "", s)
    if len(s) < 2 or len(s) > 4:
        return None
    return s


def _parse_data_ptbr(data_str: str) -> Optional[str]:
    """Converte DD/MM/AAAA -> YYYY-MM-DD."""
    try:
        s = (data_str or "").strip()
        if not s:
            return None
        dt = datetime.strptime(s, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None


def _periodo_para_intervalo(periodo: str, data_inicio: Optional[str], data_fim: Optional[str]) -> Tuple[str, str, str]:
    """
    Retorna (periodo_label, inicio_iso, fim_iso) (fim inclusive).
    """
    p = (periodo or "semana").strip().lower()
    hoje = datetime.now().date()

    if p == "hoje":
        start = hoje
        end = hoje
        return "hoje", start.isoformat(), end.isoformat()

    if p == "mes":
        start = hoje - timedelta(days=30)
        end = hoje
        return "últimos 30 dias", start.isoformat(), end.isoformat()

    if p == "periodo_especifico":
        start_iso = _parse_data_ptbr(data_inicio or "")
        end_iso = _parse_data_ptbr(data_fim or "")
        if start_iso and end_iso:
            return f"período {data_inicio} → {data_fim}", start_iso, end_iso
        # fallback seguro
        start = hoje - timedelta(days=7)
        end = hoje
        return "últimos 7 dias (fallback)", start.isoformat(), end.isoformat()

    # default: semana
    start = hoje - timedelta(days=7)
    end = hoje
    return "últimos 7 dias", start.isoformat(), end.isoformat()


@dataclass
class Phase2ToolsHandler:
    """Handlers para as tools da Fase 2 (tirar o que restou de fallback)."""

    @staticmethod
    def listar_categorias_disponiveis(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        from db_manager import listar_categorias_processo

        categorias = listar_categorias_processo() or []
        if not categorias:
            return {
                "sucesso": True,
                "resposta": "📂 Nenhuma categoria encontrada no banco (categorias_processo).",
                "dados": {"categorias": []},
            }

        confirmadas = [c for c in categorias if c.get("confirmada_por_usuario") in (1, True, "1", "true")]
        nao_confirmadas = [c for c in categorias if c not in confirmadas]

        linhas = []
        linhas.append(f"📂 **Categorias disponíveis:** {len(categorias)}")
        linhas.append(f"- ✅ confirmadas pelo usuário: {len(confirmadas)}")
        linhas.append(f"- ℹ️ não confirmadas: {len(nao_confirmadas)}\n")

        def _fmt(lista: List[Dict[str, Any]], titulo: str) -> None:
            if not lista:
                return
            linhas.append(f"**{titulo}**")
            for c in lista:
                cat = c.get("categoria") or "N/A"
                linhas.append(f"- {cat}")
            linhas.append("")

        _fmt(confirmadas, "Confirmadas")
        _fmt(nao_confirmadas, "Outras (não confirmadas)")

        linhas.append("💡 Para adicionar uma categoria, diga: \"sim, essa categoria existe: XYZ\" (a IA vai usar `adicionar_categoria_processo`).")

        return {"sucesso": True, "resposta": "\n".join(linhas).strip(), "dados": {"categorias": categorias}}

    @staticmethod
    def adicionar_categoria_processo(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        from db_manager import adicionar_categoria_processo as _add
        from db_manager import verificar_categoria_processo as _exists

        cat = _normalizar_categoria(argumentos.get("categoria"))
        if not cat:
            return {
                "sucesso": False,
                "erro": "CATEGORIA_INVALIDA",
                "resposta": "❌ Categoria inválida. Deve ter **2 a 4 caracteres** (ex: ALH, VDM, MV5).",
            }

        if _exists(cat):
            return {
                "sucesso": True,
                "resposta": f"ℹ️ A categoria **{cat}** já existe no sistema.",
                "dados": {"categoria": cat, "ja_existia": True},
            }

        ok = _add(cat, confirmada_por_usuario=True)
        if ok:
            return {
                "sucesso": True,
                "resposta": f"✅ Categoria **{cat}** adicionada e marcada como **confirmada pelo usuário**.",
                "dados": {"categoria": cat, "ja_existia": False},
            }

        return {
            "sucesso": False,
            "erro": "ERRO_ADICIONAR_CATEGORIA",
            "resposta": f"❌ Erro ao adicionar a categoria **{cat}**.",
        }

    @staticmethod
    def desvincular_documento_processo(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        processo = (argumentos.get("processo_referencia") or "").strip()
        tipo = (argumentos.get("tipo_documento") or "").strip().upper()
        numero = (argumentos.get("numero_documento") or "").strip()

        if not processo or not tipo or not numero:
            return {
                "sucesso": False,
                "erro": "PARAMETROS_OBRIGATORIOS",
                "resposta": "❌ processo_referencia, tipo_documento e numero_documento são obrigatórios.",
            }

        from services.vinculacao_service import VinculacaoService

        service = VinculacaoService(chat_service=None)
        resultado = service.desvincular_documento(
            processo_referencia=processo,
            tipo_documento=tipo,
            numero_documento=numero,
        )
        # Normalizar chaves para padrão do sistema
        if "mensagem" in resultado and "resposta" not in resultado:
            resultado["resposta"] = resultado.get("mensagem")
        return resultado

    @staticmethod
    def vincular_processo_cct(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        numero_cct = (argumentos.get("numero_cct") or "").strip()
        processo = (argumentos.get("processo_referencia") or "").strip()

        if not numero_cct or not processo:
            return {
                "sucesso": False,
                "erro": "PARAMETROS_OBRIGATORIOS",
                "resposta": "❌ numero_cct e processo_referencia são obrigatórios.",
            }

        from services.vinculacao_service import VinculacaoService
        from services.utils.extractors import extract_processo_referencia

        proc_norm = extract_processo_referencia(processo) or processo
        service = VinculacaoService(chat_service=None)
        resultado = service.vincular_cct(numero_cct=numero_cct, processo_referencia=proc_norm)

        # Normalizar (há retornos com 'mensagem' em vez de 'resposta')
        if "mensagem" in resultado and "resposta" not in resultado:
            resultado["resposta"] = resultado.get("mensagem")
        return resultado

    @staticmethod
    def gerar_resumo_reuniao(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Gera um resumo executivo para reunião.

        Implementação enxuta:
        - Coleta snapshot de `processos_kanban` (por categoria opcional)
        - Monta estatísticas + highlights
        - Se IA estiver habilitada, pede ao modelo analítico um texto executivo (sem tool calling)
        """
        categoria = _normalizar_categoria(argumentos.get("categoria"))
        periodo = (argumentos.get("periodo") or "semana").strip().lower()
        data_inicio = argumentos.get("data_inicio")
        data_fim = argumentos.get("data_fim")

        periodo_label, start_iso, end_iso = _periodo_para_intervalo(periodo, data_inicio, data_fim)

        from services.sqlite_db import get_db_connection

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        where = []
        params: List[Any] = []
        if categoria:
            where.append("processo_referencia LIKE ?")
            params.append(f"{categoria}.%")
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        cur.execute(
            f"""
            SELECT
                processo_referencia,
                etapa_kanban,
                modal,
                tem_pendencias,
                pendencia_icms,
                pendencia_frete,
                data_destino_final,
                eta_iso,
                porto_nome,
                nome_navio,
                numero_ce,
                numero_di,
                numero_duimp
            FROM processos_kanban
            {where_sql}
            ORDER BY atualizado_em DESC
            LIMIT 300
            """,
            params,
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        total = len(rows)
        pendentes = [r for r in rows if r.get("tem_pendencias") in (1, True, "1", "true")]
        por_etapa: Dict[str, int] = {}
        por_modal: Dict[str, int] = {}

        def _date_in_range(date_iso: Optional[str]) -> bool:
            if not date_iso:
                return False
            s = str(date_iso)[:10]
            return start_iso <= s <= end_iso

        chegando_periodo = []
        chegando_confirmado = []
        for r in rows:
            etapa = (r.get("etapa_kanban") or "N/A").strip()
            por_etapa[etapa] = por_etapa.get(etapa, 0) + 1
            modal = (r.get("modal") or "N/A").strip()
            por_modal[modal] = por_modal.get(modal, 0) + 1

            # Previsto: ETA
            if _date_in_range(r.get("eta_iso")):
                chegando_periodo.append(r)
            # Confirmado: destino final
            if _date_in_range(r.get("data_destino_final")):
                chegando_confirmado.append(r)

        # Highlights (limitados)
        top_pendencias = sorted(
            pendentes,
            key=lambda x: (1 if (x.get("pendencia_icms") or "").strip() else 0) + (1 if x.get("pendencia_frete") in (1, True, "1", "true") else 0),
            reverse=True,
        )[:12]

        def _fmt_proc(r: Dict[str, Any]) -> str:
            pr = r.get("processo_referencia", "N/A")
            etapa = r.get("etapa_kanban") or "-"
            eta = (r.get("eta_iso") or "")[:10]
            navio = r.get("nome_navio") or ""
            porto = r.get("porto_nome") or ""
            flags = []
            if r.get("pendencia_frete") in (1, True, "1", "true"):
                flags.append("frete")
            if (r.get("pendencia_icms") or "").strip():
                flags.append("ICMS")
            if r.get("numero_ce"):
                flags.append("CE")
            if r.get("numero_di"):
                flags.append("DI")
            if r.get("numero_duimp"):
                flags.append("DUIMP")
            ftxt = ", ".join(flags) if flags else "-"
            extra = " | ".join([x for x in [eta, navio, porto] if x])
            return f"- {pr} — etapa={etapa} | {extra} | {ftxt}"

        # Base (determinística) — sempre retorna, mesmo sem IA
        base = []
        base.append("📊 **Resumo para reunião**")
        base.append(f"- categoria: `{categoria or 'geral'}`")
        base.append(f"- período: **{periodo_label}** ({start_iso} → {end_iso})")
        base.append(f"- processos no snapshot: **{total}**")
        base.append(f"- com pendências: **{len(pendentes)}**")
        base.append(f"- chegando (ETA no período): **{len(chegando_periodo)}**")
        base.append(f"- chegada confirmada (destino final no período): **{len(chegando_confirmado)}**\n")

        base.append("📌 **Distribuição por etapa (top 10):**")
        for etapa, cnt in sorted(por_etapa.items(), key=lambda x: x[1], reverse=True)[:10]:
            base.append(f"- {etapa}: {cnt}")
        base.append("")

        base.append("🚨 **Pontos de atenção (pendências - top):**")
        if top_pendencias:
            for r in top_pendencias:
                base.append(_fmt_proc(r))
        else:
            base.append("- (nenhuma pendência detectada no snapshot)")
        base.append("")

        base.append("📦 **Chegando no período (ETA - amostra):**")
        for r in chegando_periodo[:10]:
            base.append(_fmt_proc(r))
        if len(chegando_periodo) > 10:
            base.append(f"- … (+{len(chegando_periodo)-10} processos)")
        base.append("")

        texto_base = "\n".join(base).strip()

        # Se IA estiver desabilitada, devolver o base
        try:
            from ai_service import get_ai_service, AI_MODEL_ANALITICO

            ai = get_ai_service()
            if not getattr(ai, "enabled", False):
                return {"sucesso": True, "resposta": texto_base, "dados": {"snapshot_count": total}}

            system_prompt = (
                "Você é um analista sênior de COMEX. Gere um resumo executivo curto, objetivo e pronto para reunião.\n"
                "Regras:\n"
                "- Não invente dados fora do input.\n"
                "- Estruture em: Resumo Executivo, Principais Números, Pontos de Atenção, Próximos Passos.\n"
                "- Use bullets curtos.\n"
            )
            user_prompt = (
                "A seguir está um snapshot/relato estruturado do sistema. Gere o resumo de reunião:\n\n"
                f"{texto_base}\n"
            )

            resp = ai._call_llm_api(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tools=None,
                tool_choice=None,
                model=AI_MODEL_ANALITICO,
                temperature=0.3,
            )
            if isinstance(resp, str) and resp.strip():
                return {"sucesso": True, "resposta": resp.strip(), "dados": {"snapshot_count": total}}

            # Fallback: devolver base
            return {"sucesso": True, "resposta": texto_base, "dados": {"snapshot_count": total}}
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gerar resumo via IA, retornando base: {e}")
            return {"sucesso": True, "resposta": texto_base, "dados": {"snapshot_count": total}}

