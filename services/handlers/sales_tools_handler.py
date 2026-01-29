"""
SalesToolsHandler
-----------------
Handlers extraídos para tools de vendas (Make/Spalla).

Mantemos em módulo separado para não crescer `services/tool_execution_service.py`.
"""

from __future__ import annotations

import logging
import os
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SalesToolsHandler:
    @staticmethod
    def _normalizar_data_br_para_iso(value: Any) -> Any:
        """
        Aceita datas em:
        - YYYY-MM-DD (mantém)
        - DD/MM/AAAA ou DD/MM/AA (converte para YYYY-MM-DD)
        - DD-MM-AAAA ou DD-MM-AA (converte para YYYY-MM-DD)

        Se não casar, retorna o value original.
        """
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            # date/datetime -> ISO (mantém compat)
            try:
                s = value.isoformat()  # type: ignore[attr-defined]
                return s[:10] if len(s) >= 10 else s
            except Exception:
                pass
        s = str(value).strip()
        if not s:
            return None
        # já está em ISO
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return s
        m = re.match(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2}|\d{4})$", s)
        if not m:
            return value

    @staticmethod
    def _extrair_data_do_termo(termo: Any) -> Dict[str, Any]:
        """
        Extrai uma data explícita dentro do termo (ex.: "rastreador 29/01/26") para evitar
        que a data vire token de busca e para permitir recorte correto por dia.

        Retorna:
          - data_iso: "YYYY-MM-DD" | None
          - termo_limpo: str | None
          - encontrado_raw: str | None
        """
        if not isinstance(termo, str):
            return {"data_iso": None, "termo_limpo": termo, "encontrado_raw": None}
        t = termo.strip()
        if not t:
            return {"data_iso": None, "termo_limpo": None, "encontrado_raw": None}

        m = re.search(r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b", t)
        if not m:
            return {"data_iso": None, "termo_limpo": t, "encontrado_raw": None}

        raw = m.group(1)
        dt_iso = SalesToolsHandler._normalizar_data_br_para_iso(raw)
        if not isinstance(dt_iso, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", dt_iso):
            return {"data_iso": None, "termo_limpo": t, "encontrado_raw": raw}

        termo_limpo = (t.replace(raw, " ").strip() or None)
        if isinstance(termo_limpo, str):
            termo_limpo = re.sub(r"\s{2,}", " ", termo_limpo).strip() or None

        return {"data_iso": dt_iso, "termo_limpo": termo_limpo, "encontrado_raw": raw}
        dd = int(m.group(1))
        mm = int(m.group(2))
        yy_raw = m.group(3)
        yy = int(yy_raw)
        if len(yy_raw) == 2:
            # Heurística: 00-79 => 2000-2079 ; 80-99 => 1980-1999
            yy = 2000 + yy if yy <= 79 else 1900 + yy
        try:
            # valida data
            dt = datetime(yy, mm, dd).date()
            return dt.isoformat()
        except Exception:
            return value

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        """
        Converte estruturas arbitrárias (rows vindas do SQL) para algo serializável em JSON.
        - date/datetime -> ISO string
        - Decimal -> float
        - dict/list -> recursivo
        """
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Decimal):
            try:
                return float(value)
            except Exception:
                return str(value)
        # date/datetime (e similares com isoformat)
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()  # type: ignore[attr-defined]
            except Exception:
                pass
        if isinstance(value, dict):
            return {str(k): SalesToolsHandler._to_json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [SalesToolsHandler._to_json_safe(v) for v in value]
        # Fallback
        return str(value)

    @staticmethod
    def _max_output_lines(default: int = 500) -> int:
        """
        Limite de segurança para não explodir UI.
        Se SALES_OUTPUT_MAX_LINES=0 ou -1 -> sem limite (não recomendado).
        """
        raw = os.getenv("SALES_OUTPUT_MAX_LINES", str(default)).strip()
        try:
            n = int(raw)
        except Exception:
            n = default
        return n

    @staticmethod
    def consultar_vendas_make(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Tool: consultar_vendas_make

        Argumentos esperados (best-effort):
        - inicio: YYYY-MM-DD (inclusivo)
        - fim: YYYY-MM-DD (exclusivo)
        - periodo_mes: YYYY-MM (alternativa a inicio/fim)
        - apenas_hoje: bool
        - termo: string (produto/serviço) ex: "alho", "rastreador"
        - venda_td_des_like: list[str] (definição de "venda" via TD_DES)
        - top: int
        - granularidade: "mes" | "dia"
        """
        try:
            from services.vendas_make_service import VendasMakeService

            svc = VendasMakeService()
            if not svc.is_ready():
                return {
                    "sucesso": False,
                    "erro": "SQL_ADAPTER_INDISPONIVEL",
                    "resposta": "❌ SQL Server adapter indisponível (pyodbc/node não encontrados).",
                }

            inicio = argumentos.get("inicio")
            fim = argumentos.get("fim")
            periodo_mes = argumentos.get("periodo_mes")
            apenas_hoje = bool(argumentos.get("apenas_hoje", False))
            termo = argumentos.get("termo")
            venda_td_des_like = argumentos.get("venda_td_des_like")
            top = argumentos.get("top", 50)
            granularidade = argumentos.get("granularidade", "mes")

            # ✅ Aceitar datas no padrão BR (DD/MM/AA ou DD/MM/AAAA) no chat/WhatsApp
            inicio = SalesToolsHandler._normalizar_data_br_para_iso(inicio)
            fim = SalesToolsHandler._normalizar_data_br_para_iso(fim)

            # ✅ UX: data dentro do termo (ex.: "rastreador 29/01/26")
            # -> vira período de 1 dia e remove do termo para não poluir a busca.
            try:
                extracted = SalesToolsHandler._extrair_data_do_termo(termo)
                if (
                    extracted.get("data_iso")
                    and (not inicio)
                    and (not fim)
                    and (not periodo_mes)
                    and (not apenas_hoje)
                ):
                    dt_ini = extracted["data_iso"]
                    dt_fim = (datetime.fromisoformat(dt_ini) + timedelta(days=1)).date().isoformat()
                    inicio = dt_ini
                    fim = dt_fim
                    termo = extracted.get("termo_limpo")
            except Exception:
                pass

            resultado = svc.consultar_vendas(
                inicio=inicio,
                fim=fim,
                periodo_mes=periodo_mes,
                apenas_hoje=apenas_hoje,
                termo=termo,
                venda_td_des_like=venda_td_des_like,
                top=int(top) if top is not None else 50,
                granularidade=str(granularidade or "mes"),
            )

            if not resultado.get("sucesso"):
                err = resultado.get("erro") or "erro_desconhecido"
                # erro mais comum: sem acesso à rede do escritório
                if "ETIMEOUT" in str(err) or "no acess" in str(err).lower():
                    msg = (
                        "⚠️ SQL Server não acessível (fora da rede/VPN do escritório).\n\n"
                        "💡 Quando estiver na rede, tente novamente."
                    )
                else:
                    msg = f"❌ Erro ao consultar vendas: {err}"
                return {
                    "sucesso": False,
                    "erro": err,
                    "resposta": msg,
                    "dados": resultado.get("dados"),
                    "meta": resultado.get("meta"),
                }

            rows = resultado.get("dados") or []
            meta = resultado.get("meta") or {}
            inicio_r = meta.get("inicio") or inicio
            fim_r = meta.get("fim") or fim
            termo_r = meta.get("termo")
            granularidade_r = meta.get("granularidade", "mes")

            titulo = "📈 **Vendas (Make/Spalla)**\n\n"
            titulo += f"Período: **{inicio_r}** até **{fim_r}** (fim exclusivo)\n"
            if termo_r:
                titulo += f"Filtro (termo): **{termo_r}**\n"
            titulo += f"Granularidade: **{granularidade_r}**\n"
            titulo += f"Linhas: **{meta.get('linhas', len(rows))}**\n\n"

            def _fmt_brl(value: Any) -> str:
                try:
                    n = float(value)
                except Exception:
                    return "" if value is None else str(value)
                s = f"{n:,.2f}"
                s = s.replace(",", "X").replace(".", ",").replace("X", ".")
                return f"R$ {s}"

            def _escape_html(s: Any) -> str:
                t = "" if s is None else str(s)
                return (
                    t.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;")
                )

            colors_enabled = os.getenv("SALES_REPORT_COLORS", "true").strip().lower() not in {"0", "false", "no"}

            def _span(cls: str, txt: Any) -> str:
                safe = _escape_html(txt)
                return f'<span class="{cls}">{safe}</span>' if colors_enabled else safe

            def _parse_date_any(v: Any):
                if v is None:
                    return None
                if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
                    try:
                        return v.date() if hasattr(v, "date") else v
                    except Exception:
                        pass
                s = str(v).strip()
                if not s:
                    return None
                try:
                    return datetime.fromisoformat(s).date()
                except Exception:
                    pass
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        continue
                return None

            hoje = datetime.now().date()

            def _parse_float_any(v: Any) -> float:
                if v is None:
                    return 0.0
                if isinstance(v, (int, float)):
                    try:
                        return float(v)
                    except Exception:
                        return 0.0
                s = str(v).strip()
                if not s:
                    return 0.0
                if "," in s and "." in s:
                    s = s.replace(".", "").replace(",", ".")
                elif "," in s and "." not in s:
                    s = s.replace(",", ".")
                s = re.sub(r"[^\d.\-]", "", s)
                try:
                    return float(s)
                except Exception:
                    return 0.0

            def _parse_float_any(v: Any) -> float:
                if v is None:
                    return 0.0
                if isinstance(v, (int, float)):
                    try:
                        return float(v)
                    except Exception:
                        return 0.0
                s = str(v).strip()
                if not s:
                    return 0.0
                # BRL comum: 1.234,56
                s2 = s
                if "," in s2 and "." in s2:
                    s2 = s2.replace(".", "").replace(",", ".")
                elif "," in s2 and "." not in s2:
                    s2 = s2.replace(",", ".")
                # remover lixo
                s2 = re.sub(r"[^\d.\-]", "", s2)
                try:
                    return float(s2)
                except Exception:
                    return 0.0

            def _parse_date_any(v: Any):
                if v is None:
                    return None
                if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
                    try:
                        return v.date() if hasattr(v, "date") else v
                    except Exception:
                        pass
                s = str(v).strip()
                if not s:
                    return None
                try:
                    return datetime.fromisoformat(s).date()
                except Exception:
                    pass
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        continue
                return None

            hoje = datetime.now().date()

            def _op_base(desc: Any) -> str:
                s = (str(desc) if desc is not None else "").strip()
                if not s:
                    return "Outros"
                s = s.replace(" - SEM CONFERÊNCIA", "").replace(" - Sem Conferência", "")
                if " - " in s:
                    s = s.split(" - ", 1)[0].strip()
                return s or "Outros"

            def _is_excluded_op(op_name: str) -> bool:
                """
                Regras de negócio: operações que NÃO são "venda" (não devem aparecer no relatório).
                """
                op_u = (op_name or "").strip().upper()
                # Nacionalização por Conta Própria = entrada/importação (não é venda)
                if ("CONTA" in op_u) and ("PROPR" in op_u) and ("NACIONALIZ" in op_u):
                    return True
                return False

            def _cc_label(r: Dict[str, Any]) -> str:
                cc = (r.get("descricao_centro_custo_documento") or "").strip()
                cod = r.get("codigo_centro_custo_documento")
                cod_s = str(cod).strip() if cod is not None else ""
                if cc and cod_s:
                    return f"{cc} | {cod_s}"
                return cc or (cod_s or "")

            # Formatar resposta "executiva" (evita tabela crua)
            if not rows:
                return {
                    "sucesso": True,
                    "resposta": titulo + "ℹ️ Nenhum resultado encontrado nesse recorte.",
                    "dados": [],
                    "meta": meta,
                }

            # Mostrar tudo (sem truncar) na maioria dos casos, mas com limite de segurança configurável.
            hard_cap = SalesToolsHandler._max_output_lines(default=500)
            max_linhas = len(rows) if hard_cap <= 0 else min(len(rows), hard_cap)
            out = titulo

            # Agrupar por período -> centro -> operação
            # rows já vem ordenado por periodo desc, total desc (do SQL)
            shown = 0
            periodos = []
            for r in rows:
                if not isinstance(r, dict):
                    continue
                p = str(r.get("periodo") or "").strip()
                if p and p not in periodos:
                    periodos.append(p)

            for periodo in periodos:
                period_rows = [r for r in rows if isinstance(r, dict) and str(r.get("periodo") or "").strip() == periodo]
                if not period_rows:
                    continue
                out += f"**{periodo}**\n\n"

                # centros dentro do período
                centros = {}
                for rr in period_rows:
                    cc = _cc_label(rr)
                    centros.setdefault(cc or "N/A", []).append(rr)

                for cc_label, cc_rows in sorted(centros.items(), key=lambda kv: sum(float(x.get("total_valor") or 0) for x in kv[1] if isinstance(x, dict)), reverse=True):
                    if cc_label and cc_label != "N/A":
                        out += f"Centro: **{cc_label}**\n"
                    # operações dentro do centro
                    ops = {}
                    for rr in cc_rows:
                        op = _op_base(rr.get("descricao_tipo_operacao_documento"))
                        if _is_excluded_op(op):
                            continue
                        ops.setdefault(op, []).append(rr)

                    for op_name, op_rows in sorted(ops.items(), key=lambda kv: sum(float(x.get("total_valor") or 0) for x in kv[1] if isinstance(x, dict)), reverse=True):
                        # tipo_movimento pode ser útil como etiqueta curta
                        # ex: C / F
                        tipo_mov = str((op_rows[0].get("tipo_movimento_documento") or "")).strip() if op_rows and isinstance(op_rows[0], dict) else ""
                        tipo_tag = f" ({tipo_mov})" if tipo_mov else ""
                        out += f"- **{op_name}**{tipo_tag}\n"

                        # geralmente haverá 1 linha por operação/centro/periodo, mas suportar múltiplas
                        for rr in op_rows:
                            if shown >= max_linhas:
                                break
                            total = _fmt_brl(rr.get("total_valor"))
                            qtd = rr.get("qtd_documentos")
                            pct = rr.get("pct_no_periodo")
                            extras = []
                            if qtd is not None:
                                extras.append(f"qtd {qtd}")
                            if pct is not None:
                                try:
                                    extras.append(f"{float(pct):.0f}%")
                                except Exception:
                                    pass
                            extra_txt = (" (" + ", ".join(extras) + ")") if extras else ""
                            out += f"  - {total}{extra_txt}\n"
                            shown += 1
                        out += "\n"
                        if shown >= max_linhas:
                            break
                    out += "\n"
                    if shown >= max_linhas:
                        break

                out += "\n"
                if shown >= max_linhas:
                    break

            if len(rows) > max_linhas:
                out += (
                    f"⚠️ Mostrando {max_linhas} de {len(rows)} linhas (formato resumido). "
                    f"Para ver tudo, aumente `SALES_OUTPUT_MAX_LINES` no .env.\n"
                )

            return {
                "sucesso": True,
                "resposta": out,
                "dados": rows,
                "meta": meta,
            }
        except Exception as e:
            logger.error(f"❌ Erro em consultar_vendas_make: {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": str(e),
                "resposta": f"❌ Erro ao consultar vendas: {str(e)}",
            }

    @staticmethod
    def inspecionar_schema_nf_make(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Tool: inspecionar_schema_nf_make
        Descobre colunas/tabelas prováveis para NF/cliente/itens no legado.
        """
        try:
            from services.vendas_make_service import VendasMakeService

            top = argumentos.get("top", 80)
            svc = VendasMakeService()
            if not svc.is_ready():
                return {
                    "sucesso": False,
                    "erro": "SQL_ADAPTER_INDISPONIVEL",
                    "resposta": "❌ SQL Server adapter indisponível (pyodbc/node não encontrados).",
                }

            resultado = svc.inspecionar_schema_nf(top=int(top) if top is not None else 80)
            if not resultado.get("sucesso"):
                err = resultado.get("erro") or "erro_desconhecido"
                return {"sucesso": False, "erro": err, "resposta": f"❌ Erro ao inspecionar schema: {err}"}

            dados = (resultado.get("dados") or {}) if isinstance(resultado.get("dados"), dict) else {}
            cand = dados.get("candidatos") or {}
            cols = dados.get("documentos_colunas") or []
            tabs = dados.get("tabelas_sugeridas_itens_produtos") or []

            resp = "🔎 **Schema legado (Make/Spalla) — NF/Vendas**\n\n"
            resp += "**Candidatos encontrados em `spalla.dbo.documentos`:**\n"
            resp += f"- Número NF: `{', '.join(cand.get('numero_nf') or []) or 'N/A'}`\n"
            resp += f"- Cliente: `{', '.join(cand.get('cliente') or []) or 'N/A'}`\n"
            resp += f"- Observações/descrição: `{', '.join(cand.get('observacoes') or []) or 'N/A'}`\n\n"
            resp += f"**Total de colunas em documentos:** {len(cols)}\n"
            resp += "💡 Se o número NF/cliente não aparecer nos candidatos, ele pode estar em outra tabela (ex.: NFe/itens).\n\n"
            if tabs:
                resp += "**Tabelas sugeridas (itens/produtos/NFe):**\n"
                for i, t in enumerate(tabs[:40], start=1):
                    if not isinstance(t, dict):
                        continue
                    resp += f"- {t.get('schema_name','dbo')}.{t.get('table_name','?')}\n"
                if len(tabs) > 40:
                    resp += f"\n… (+{len(tabs) - 40} tabelas)\n"

            return {"sucesso": True, "resposta": resp, "dados": dados}
        except Exception as e:
            logger.error(f"❌ Erro em inspecionar_schema_nf_make: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "resposta": f"❌ Erro ao inspecionar schema: {str(e)}"}

    @staticmethod
    def consultar_vendas_nf_make(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Tool: consultar_vendas_nf_make
        Retorna vendas por NF (nível documento).
        """
        try:
            from services.vendas_make_service import VendasMakeService

            svc = VendasMakeService()
            if not svc.is_ready():
                return {
                    "sucesso": False,
                    "erro": "SQL_ADAPTER_INDISPONIVEL",
                    "resposta": "❌ SQL Server adapter indisponível (pyodbc/node não encontrados).",
                }

            # ✅ UX: permitir "vendas vdm jan 26 cobranca" sem depender do roteamento separar args.
            # Se "cobranca/cobrança/vencidas/..." vierem junto no termo, removemos do filtro SQL e setamos modo.
            try:
                termo_raw = argumentos.get("termo")
                modo_raw = str(argumentos.get("modo") or "").strip().lower()
                somente_vencidas_raw = bool(argumentos.get("somente_vencidas", False))
                if isinstance(termo_raw, str) and termo_raw.strip():
                    cobranca_tokens = {
                        "cobranca",
                        "cobrança",
                        "cobrar",
                        "vencida",
                        "vencidas",
                        "inadimplente",
                        "inadimplentes",
                        "atraso",
                        "atrasada",
                        "atrasadas",
                        "atrasado",
                        "atrasados",
                        "em",
                        "aberto",  # comum em "em aberto" (não deve virar token do SQL)
                        "vencido",
                        "vencidos",
                    }
                    parts = [p for p in re.split(r"\s+", termo_raw.strip()) if p]
                    parts_lower = [p.lower() for p in parts]
                    pediu_cobranca = any(p in cobranca_tokens for p in parts_lower)
                    if pediu_cobranca:
                        if (not modo_raw) or (modo_raw == "normal"):
                            argumentos["modo"] = "cobranca"
                        # Em cobrança, por padrão já é "somente vencidas"
                        if not somente_vencidas_raw:
                            argumentos["somente_vencidas"] = True
                        # Remover palavras-chave do termo (mantém o resto, ex.: "vdm")
                        kept = [p for p in parts if p.lower() not in cobranca_tokens]
                        argumentos["termo"] = " ".join(kept).strip() or None
            except Exception:
                pass

            # ✅ Aceitar datas no padrão BR (DD/MM/AA ou DD/MM/AAAA) no chat/WhatsApp
            argumentos["inicio"] = SalesToolsHandler._normalizar_data_br_para_iso(argumentos.get("inicio"))
            argumentos["fim"] = SalesToolsHandler._normalizar_data_br_para_iso(argumentos.get("fim"))

            # ✅ UX: data dentro do termo (ex.: "rastreador 29/01/26")
            # -> define inicio/fim do dia e remove do termo para evitar fuzzy_term/ruído.
            try:
                extracted = SalesToolsHandler._extrair_data_do_termo(argumentos.get("termo"))
                if (
                    extracted.get("data_iso")
                    and (not argumentos.get("inicio"))
                    and (not argumentos.get("fim"))
                    and (not argumentos.get("periodo_mes"))
                    and (not bool(argumentos.get("apenas_hoje", False)))
                ):
                    dt_ini = extracted["data_iso"]
                    dt_fim = (datetime.fromisoformat(dt_ini) + timedelta(days=1)).date().isoformat()
                    argumentos["inicio"] = dt_ini
                    argumentos["fim"] = dt_fim
                    argumentos["termo"] = extracted.get("termo_limpo")
            except Exception:
                pass

            resultado = svc.consultar_vendas_por_nf(
                inicio=argumentos.get("inicio"),
                fim=argumentos.get("fim"),
                periodo_mes=argumentos.get("periodo_mes"),
                apenas_hoje=bool(argumentos.get("apenas_hoje", False)),
                termo=argumentos.get("termo"),
                venda_td_des_like=argumentos.get("venda_td_des_like"),
                top=int(argumentos.get("top", 80) or 80),
            )

            if not resultado.get("sucesso"):
                # Se veio resposta pronta, respeitar
                if resultado.get("resposta"):
                    return {
                        "sucesso": False,
                        "erro": resultado.get("erro"),
                        "resposta": resultado.get("resposta"),
                        "dados": resultado.get("dados"),
                        "meta": resultado.get("meta"),
                    }
                err = resultado.get("erro") or "erro_desconhecido"
                return {"sucesso": False, "erro": err, "resposta": f"❌ Erro ao consultar vendas por NF: {err}"}

            rows = resultado.get("dados") or []
            meta = resultado.get("meta") or {}
            inicio_r = meta.get("inicio")
            fim_r = meta.get("fim")
            termo_r = meta.get("termo")
            termo_tokens = meta.get("termo_tokens") or []

            titulo = "🧾 **Vendas por NF (Make/Spalla)**\n\n"
            titulo += f"Período: **{inicio_r}** até **{fim_r}** (fim exclusivo)\n"
            if termo_r:
                titulo += f"Filtro (termo): **{termo_r}**\n"
                if termo_tokens:
                    titulo += f"Tokens aplicados (AND): `{', '.join(str(t) for t in termo_tokens)}`\n"
            # Se houve autocorreção de termo (fuzzy), mostrar de forma discreta.
            try:
                fuzzy = meta.get("fuzzy_term") if isinstance(meta, dict) else None
                if isinstance(fuzzy, dict) and fuzzy.get("termo_original") and fuzzy.get("termo_corrigido"):
                    titulo += f"ℹ️ Termo corrigido: `{fuzzy.get('termo_original')}` → `{fuzzy.get('termo_corrigido')}`\n"
            except Exception:
                pass
            titulo += f"Linhas: **{meta.get('linhas', len(rows))}**\n\n"

            if not rows:
                return {"sucesso": True, "resposta": titulo + "ℹ️ Nenhuma NF encontrada nesse recorte.", "dados": [], "meta": meta}

            # ✅ Resumos úteis
            # ✅ Regra: NÃO somar DOC/ICMS nos totais (mas manter as linhas no relatório)
            total_sum_vendas_brutas = 0.0
            total_sum_devolucoes = 0.0
            total_sum_doc = 0.0
            total_sum_recebido = 0.0
            total_sum_em_aberto = 0.0
            # ✅ Alertas de cobrança no modo "normal":
            # - vencidas (venc < hoje) e ainda em aberto
            # - vencem hoje (venc == hoje) e ainda em aberto
            count_vencidas = 0
            sum_vencidas_aberto = 0.0
            count_vence_hoje = 0
            sum_vence_hoje_aberto = 0.0
            centros = {}
            cliente_vazio = True

            def _is_excluded_op(op_name: str) -> bool:
                """
                Operações que devem ser removidas do relatório de vendas por NF.
                Ex.: compras não são "venda" e poluem o relatório.
                """
                op_u = (op_name or "").strip().upper()
                # ✅ Regra de negócio: "Nacionalização por Conta Própria" NÃO é venda (é entrada/importação).
                if ("CONTA" in op_u) and ("PROPR" in op_u) and ("NACIONALIZ" in op_u):
                    return True
                return op_u in {
                    "COMPRA DE MERCADORIA PARA REVENDA",
                    "COMISSÃO DE VENDA",
                    "COMISSAO DE VENDA",
                }

            def _is_devolucao_op(op_name: str) -> bool:
                op_u = (op_name or "").strip().upper()
                # Variações comuns no legado:
                # - "DEVOLUÇÃO DE VENDA ..."
                # - "DEVOLUCAO DE VENDA ..." (sem acento)
                return ("DEVOLU" in op_u) or ("DEVOLUC" in op_u)

            def _op_base_totais(desc: Any) -> str:
                s = (str(desc) if desc is not None else "").strip()
                if not s:
                    return "Outros"
                s = s.replace(" - SEM CONFERÊNCIA", "").replace(" - Sem Conferência", "")
                if " - " in s:
                    s = s.split(" - ", 1)[0].strip()
                return s or "Outros"

            # ✅ Modo "cobrança": listar NFs em aberto e vencidas (quem não pagou no vencimento)
            modo = str(argumentos.get("modo") or "normal").strip().lower()
            somente_vencidas = bool(argumentos.get("somente_vencidas", False))
            if modo == "cobranca":
                somente_vencidas = True

            if modo == "cobranca":
                def _fmt_brl2(value: Any) -> str:
                    try:
                        n = float(value)
                    except Exception:
                        return "" if value is None else str(value)
                    s = f"{n:,.2f}"
                    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
                    return f"R$ {s}"

                def _escape_html2(s: Any) -> str:
                    t = "" if s is None else str(s)
                    return (
                        t.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace('"', "&quot;")
                        .replace("'", "&#39;")
                    )

                colors_enabled = os.getenv("SALES_REPORT_COLORS", "true").strip().lower() not in {"0", "false", "no"}

                def _span2(cls: str, txt: Any) -> str:
                    safe = _escape_html2(txt)
                    return f'<span class="{cls}">{safe}</span>' if colors_enabled else safe

                def _parse_date2(v: Any):
                    if v is None:
                        return None
                    # datetime/date vindo do driver
                    if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
                        try:
                            # datetime -> date
                            return v.date() if hasattr(v, "date") else v
                        except Exception:
                            pass
                    s = str(v).strip()
                    if not s:
                        return None
                    try:
                        return datetime.fromisoformat(s).date()
                    except Exception:
                        pass
                    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                        try:
                            return datetime.strptime(s, fmt).date()
                        except Exception:
                            continue
                    return None

                hoje = datetime.now().date()

                # Agrupar por empresa e NF (pode haver múltiplas linhas por NF/operação)
                agrupado: Dict[str, Dict[str, Dict[str, Any]]] = {}
                for r in rows:
                    if not isinstance(r, dict):
                        continue
                    op = _op_base_totais(r.get("descricao_tipo_operacao_documento"))
                    if _is_excluded_op(op) or _is_devolucao_op(op) or (op.strip().upper() == "ICMS"):
                        continue

                    nf = str(r.get("numero_nf") or "").strip()
                    if not nf:
                        continue

                    try:
                        em_aberto = float(r.get("valor_em_aberto") or 0.0)
                    except Exception:
                        em_aberto = 0.0
                    if em_aberto <= 0:
                        continue

                    venc_dt = _parse_date2(r.get("proximo_vencimento"))
                    if somente_vencidas and (not venc_dt or venc_dt >= hoje):
                        continue

                    emp = (r.get("empresa_vendedora") or "N/A").strip()
                    cli = (r.get("cliente") or "").strip() or "—"
                    try:
                        total_nf = float(r.get("total_nf") or 0.0)
                    except Exception:
                        total_nf = 0.0
                    try:
                        recebido = float(r.get("valor_recebido") or 0.0)
                    except Exception:
                        recebido = 0.0

                    key = f"{nf}"
                    agrupado.setdefault(emp, {})
                    item = agrupado[emp].get(key) or {
                        "nf": nf,
                        "cliente": cli,
                        "total_nf": 0.0,
                        "valor_em_aberto": 0.0,
                        "valor_recebido": 0.0,
                        "proximo_vencimento": venc_dt,
                    }
                    # Somar por NF (best-effort)
                    item["total_nf"] = float(item.get("total_nf") or 0.0) + total_nf
                    item["valor_em_aberto"] = float(item.get("valor_em_aberto") or 0.0) + em_aberto
                    item["valor_recebido"] = float(item.get("valor_recebido") or 0.0) + recebido
                    # manter o menor vencimento (mais crítico) se houver conflito
                    if venc_dt and (not item.get("proximo_vencimento") or venc_dt < item.get("proximo_vencimento")):
                        item["proximo_vencimento"] = venc_dt
                    item["cliente"] = item.get("cliente") if item.get("cliente") not in {"—", ""} else cli
                    agrupado[emp][key] = item

                if not agrupado:
                    cab = "📌 **Cobrança — NFs em aberto e vencidas**\n\n"
                    cab += f"Período: **{inicio_r}** até **{fim_r}** (fim exclusivo)\n"
                    if termo_r:
                        cab += f"Filtro (termo): **{termo_r}**\n"
                    cab += "\n✅ Nenhuma NF vencida/em aberto encontrada nesse recorte."
                    return {"sucesso": True, "resposta": cab, "dados": rows, "meta": meta}

                total_aberto = 0.0
                total_nfs = 0
                out = "📌 **Cobrança — NFs em aberto e vencidas**\n\n"
                out += f"Período: **{inicio_r}** até **{fim_r}** (fim exclusivo)\n"
                if termo_r:
                    out += f"Filtro (termo): **{termo_r}**\n"
                out += "\n"

                first_empresa = True
                for emp in sorted(agrupado.keys()):
                    itens = list(agrupado.get(emp, {}).values())
                    # ordenar por mais dias vencida primeiro, depois valor em aberto desc
                    def _sort_key(x: Dict[str, Any]):
                        venc = x.get("proximo_vencimento")
                        dias = (hoje - venc).days if venc else 0
                        return (-dias, -float(x.get("valor_em_aberto") or 0.0))

                    itens.sort(key=_sort_key)
                    if not itens:
                        continue

                    if not first_empresa:
                        out += "<br><br>"
                    first_empresa = False

                    emp_label = _span2("mk-color-empresa", emp)
                    out += f"**Empresa: {emp_label}** — {len(itens)} NF(s) vencida(s)\n\n"

                    for it in itens:
                        nf = it.get("nf")
                        cli = it.get("cliente") or "—"
                        venc = it.get("proximo_vencimento")
                        ab = float(it.get("valor_em_aberto") or 0.0)
                        tot = float(it.get("total_nf") or 0.0)

                        dias_v = (hoje - venc).days if venc else 0
                        venc_txt = f"{venc.day:02d}/{venc.month:02d}" if venc else "--/--"

                        status = f"Vencida ({dias_v}d)" if venc else "Vencida"
                        status_col = _span2("mk-color-aberto", status)
                        cli_col = _span2("mk-color-cliente", cli) if cli != "—" else _span2("mk-color-muted", cli)

                        # Linha no padrão pedido (compacto)
                        total_txt = _fmt_brl2(tot) if tot else _fmt_brl2(ab)
                        # Se parcial, mostrar em aberto também
                        extra = ""
                        if tot and abs(tot - ab) > 0.01:
                            extra = f" | Em aberto: {_span2('mk-color-aberto', _fmt_brl2(ab))}"
                        out += f"- NF **{_escape_html2(nf)}** | **{_escape_html2(total_txt)}**{extra} | Cliente: {cli_col} | Venc: **{_escape_html2(venc_txt)}** | Status: {status_col}\n"

                        total_aberto += ab
                        total_nfs += 1

                out += "\n"
                out += f"**Total em aberto (vencidas):** {_span2('mk-color-aberto', _fmt_brl2(total_aberto))} | **NFs:** {total_nfs}\n"
                return {"sucesso": True, "resposta": out.strip(), "dados": rows, "meta": meta}

            # ✅ Data-base (normal mode): usada para detectar vencidos/em atraso.
            # (No modo cobrança já existe `hoje`, mas no modo normal também precisamos.)
            hoje = datetime.now().date()

            def _parse_float_any(v: Any) -> float:
                """
                Parser best-effort para números vindos do SQL (float/Decimal/str BR).
                Aceita, por ex.: "6.212,11", "6212.11", 6212.11
                """
                if v is None:
                    return 0.0
                if isinstance(v, (int, float)):
                    try:
                        return float(v)
                    except Exception:
                        return 0.0
                s = str(v).strip()
                if not s:
                    return 0.0
                # BRL comum: 1.234,56
                s2 = s
                if "," in s2 and "." in s2:
                    s2 = s2.replace(".", "").replace(",", ".")
                elif "," in s2 and "." not in s2:
                    s2 = s2.replace(",", ".")
                s2 = re.sub(r"[^\d.\-]", "", s2)
                try:
                    return float(s2)
                except Exception:
                    return 0.0

            for r in rows:
                if not isinstance(r, dict):
                    continue
                v = r.get("total_nf")
                op = _op_base_totais(r.get("descricao_tipo_operacao_documento"))
                is_doc = op.strip().upper() == "ICMS"
                is_excluded = _is_excluded_op(op)
                is_devolucao = _is_devolucao_op(op)
                try:
                    if is_doc:
                        total_sum_doc += float(v) if v is not None else 0.0
                    elif not is_excluded:
                        vv = float(v) if v is not None else 0.0
                        if is_devolucao:
                            # Devolução é listada como documento de "venda", mas entra no bloco B (para subtrair).
                            total_sum_devolucoes += abs(vv)
                        else:
                            # Vendas brutas (A): tudo que não é DOC/ICMS e não é devolução.
                            total_sum_vendas_brutas += vv
                            # ✅ Financeiro (MVP): somar recebido/em aberto apenas para vendas brutas (A)
                            try:
                                rec = float(r.get("valor_recebido") or 0.0)
                                aberto = float(r.get("valor_em_aberto") or 0.0)
                                total_sum_recebido += rec
                                total_sum_em_aberto += aberto
                                # ✅ Cobrança: detectar vencidas / vencem hoje (apenas quando há em aberto > 0)
                                try:
                                    if aberto > 0:
                                        venc_raw = r.get("proximo_vencimento")
                                        venc_s = str(venc_raw or "").strip()
                                        venc_s10 = venc_s[:10] if len(venc_s) >= 10 else venc_s
                                        if re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10):
                                            hoje_s = hoje.isoformat()
                                            if venc_s10 < hoje_s:
                                                count_vencidas += 1
                                                sum_vencidas_aberto += float(aberto)
                                            elif venc_s10 == hoje_s:
                                                count_vence_hoje += 1
                                                sum_vence_hoje_aberto += float(aberto)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                except Exception:
                    pass
                cc = (r.get("descricao_centro_custo_documento") or "").strip()
                if cc:
                    try:
                        # Totais por centro seguem o mesmo racional do total (A: vendas brutas).
                        # Não somar DOC/ICMS, compras, nem devoluções no "Top centros".
                        if (not is_doc) and (not is_excluded) and (not is_devolucao):
                            centros[cc] = centros.get(cc, 0.0) + (float(v) if v is not None else 0.0)
                    except Exception:
                        centros[cc] = centros.get(cc, 0.0)
                if (r.get("cliente") or "").strip():
                    cliente_vazio = False

            total_sum_liquido = total_sum_vendas_brutas - total_sum_devolucoes

            if total_sum_vendas_brutas or total_sum_devolucoes:
                # A / B / A-B
                if total_sum_vendas_brutas:
                    titulo += f"A - Total de vendas (bruto, sem devolução): **R$ {total_sum_vendas_brutas:,.2f}**\n".replace(
                        ",", "X"
                    ).replace(".", ",").replace("X", ".")
                    # ✅ Totais financeiros do cabeçalho (MVP): recebido + em aberto (para bater com A)
                    titulo += f"**Recebido (A):** **R$ {total_sum_recebido:,.2f}** | **Em aberto (A):** **R$ {total_sum_em_aberto:,.2f}**\n".replace(
                        ",", "X"
                    ).replace(".", ",").replace("X", ".")
                if total_sum_devolucoes:
                    titulo += f"B - Total de devoluções: **R$ {total_sum_devolucoes:,.2f}**\n".replace(",", "X").replace(
                        ".", ","
                    ).replace("X", ".")
                titulo += f"A-B - Vendas líquidas: **R$ {total_sum_liquido:,.2f}**\n".replace(",", "X").replace(".", ",").replace(
                    "X", "."
                )
            if total_sum_doc:
                titulo += f"DOC/ICMS (listado, mas não somado): **R$ {total_sum_doc:,.2f}**\n".replace(",", "X").replace(".", ",").replace("X", ".")
            if centros:
                top_cc = sorted(centros.items(), key=lambda x: x[1], reverse=True)[:5]
                titulo += "Top centros (por total): " + ", ".join(
                    f"{cc} (R$ {val:,.2f})".replace(",", "X").replace(".", ",").replace("X", ".")
                    for cc, val in top_cc
                ) + "\n"
            # ✅ Aviso de cobrança (apenas modo normal): venceram / vencem hoje e ainda em aberto
            if (count_vence_hoje or count_vencidas) and (total_sum_em_aberto > 0):
                def _fmt_brl_inline(n: float) -> str:
                    s = f"{float(n or 0.0):,.2f}"
                    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
                    return f"R$ {s}"
                parts = []
                if count_vence_hoje:
                    parts.append(f"vence hoje: **{_fmt_brl_inline(sum_vence_hoje_aberto)}** ({count_vence_hoje} NF)")
                if count_vencidas:
                    parts.append(f"vencidas: **{_fmt_brl_inline(sum_vencidas_aberto)}** ({count_vencidas} NF)")
                titulo += "⚠️ **Cobrança (em aberto):** " + " | ".join(parts) + "\n"
            titulo += "\n"

            # ✅ Formato "executivo": agrupar por empresa + tipo de operação e remover repetição
            # Mostrar tudo (sem truncar) na maioria dos casos, mas com limite de segurança configurável.
            hard_cap = SalesToolsHandler._max_output_lines(default=500)
            max_linhas = len(rows) if hard_cap <= 0 else min(len(rows), hard_cap)

            def _fmt_brl(value: Any) -> str:
                try:
                    n = float(value)
                except Exception:
                    return "" if value is None else str(value)
                # 1,234,567.89 -> 1.234.567,89
                s = f"{n:,.2f}"
                s = s.replace(",", "X").replace(".", ",").replace("X", ".")
                return f"R$ {s}"

            def _escape_html(s: Any) -> str:
                t = "" if s is None else str(s)
                return (
                    t.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;")
                )

            colors_enabled = os.getenv("SALES_REPORT_COLORS", "true").strip().lower() not in {"0", "false", "no"}

            def _span(cls: str, txt: Any) -> str:
                safe = _escape_html(txt)
                return f'<span class="{cls}">{safe}</span>' if colors_enabled else safe

            def _op_base(desc: Any) -> str:
                s = (str(desc) if desc is not None else "").strip()
                if not s:
                    return "Outros"
                # remover sufixos repetitivos
                s = s.replace(" - SEM CONFERÊNCIA", "").replace(" - Sem Conferência", "")
                # cortar no primeiro " - " para evitar repetir detalhes longos
                if " - " in s:
                    s = s.split(" - ", 1)[0].strip()
                return s or "Outros"

            def _cc_label(r: Dict[str, Any]) -> str:
                cc = (r.get("descricao_centro_custo_documento") or "").strip()
                cod = r.get("codigo_centro_custo_documento")
                cod_s = str(cod).strip() if cod is not None else ""
                if cc and cod_s:
                    return f"{cc} | {cod_s}"
                return cc or (cod_s or "")

            out = titulo
            if cliente_vazio:
                out += "Cliente: ⚠️ ainda não localizado no legado por este caminho (provável em tabelas de NF-e/itens, dependendo do schema).\n\n"

            empresa_key = "empresa_vendedora"
            # ✅ Melhor UX: ordenar blocos por total (evita começar por "Empresa: 12" e confundir que o relatório é só daquele centro)
            # Se não vier empresa, agrupa tudo como "N/A".
            emp_aggs: Dict[str, Dict[str, float]] = {}
            for rr in rows:
                if not isinstance(rr, dict):
                    continue
                emp_k = (rr.get(empresa_key) or "N/A")
                emp_k = str(emp_k).strip() or "N/A"
                emp_aggs.setdefault(emp_k, {"vendas": 0.0, "devol": 0.0, "doc": 0.0})
                try:
                    op_t = _op_base_totais(rr.get("descricao_tipo_operacao_documento"))
                    is_doc_t = op_t.strip().upper() == "ICMS"
                    is_excluded_t = _is_excluded_op(op_t)
                    is_devol_t = _is_devolucao_op(op_t)
                    v_t = float(rr.get("total_nf")) if rr.get("total_nf") is not None else 0.0
                    if is_doc_t:
                        emp_aggs[emp_k]["doc"] += v_t
                    elif not is_excluded_t:
                        if is_devol_t:
                            emp_aggs[emp_k]["devol"] += abs(v_t)
                        else:
                            emp_aggs[emp_k]["vendas"] += v_t
                except Exception:
                    pass

            def _emp_sort_key(item):
                name, agg = item
                liq = float(agg.get("vendas", 0.0)) - float(agg.get("devol", 0.0))
                # Empates: manter ordem estável por nome
                return (liq, name.lower())

            empresas = [k for k, _agg in sorted(emp_aggs.items(), key=_emp_sort_key, reverse=True)]

            # ✅ Quando for "geral" (sem termo), mostrar um resumo por centro logo no topo.
            try:
                termo_r_local = (termo_r or "").strip()
                if not termo_r_local and centros:
                    out += "📌 **Resumo por centro de custo (vendas brutas A)**\n"
                    # Top 10 centros por total
                    top_cc2 = sorted(centros.items(), key=lambda x: x[1], reverse=True)[:10]
                    for cc_name, cc_total in top_cc2:
                        # contar docs do centro (inclui docs de venda; não tenta excluir devol/doc aqui para ser simples)
                        count_docs = 0
                        try:
                            for rr in rows:
                                if not isinstance(rr, dict):
                                    continue
                                if (rr.get("descricao_centro_custo_documento") or "").strip() == cc_name:
                                    count_docs += 1
                        except Exception:
                            count_docs = 0
                        out += f"- **{cc_name}**: **{_fmt_brl(cc_total)}** — {count_docs} doc(s)\n"
                    out += "\n"
            except Exception:
                pass

            shown = 0
            first_empresa = True
            for emp in empresas:
                emp_rows = [r for r in rows if isinstance(r, dict) and ((r.get(empresa_key) or "N/A").strip() == emp)]
                if not emp_rows:
                    continue

                agg_emp = emp_aggs.get(emp) or {}
                emp_total_vendas_brutas = float(agg_emp.get("vendas", 0.0) or 0.0)
                emp_total_devolucoes = float(agg_emp.get("devol", 0.0) or 0.0)
                emp_total_doc = float(agg_emp.get("doc", 0.0) or 0.0)
                emp_total_liquido = emp_total_vendas_brutas - emp_total_devolucoes
                emp_total_fmt = f"{emp_total_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                emp_doc_fmt = f"{emp_total_doc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                emp_vendas_fmt = f"{emp_total_vendas_brutas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                emp_devol_fmt = f"{emp_total_devolucoes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                # Centro de custo (se for único no bloco, mostrar só uma vez)
                cc_set = []
                for rr in emp_rows:
                    cc_set.append(_cc_label(rr))
                cc_unique = sorted({x for x in cc_set if x})
                cc_line = f"Centro: **{cc_unique[0]}**\n" if len(cc_unique) == 1 else ""

                # Separar empresas em blocos (o frontend comprime \n\n -> <br>, então usar <br><br>)
                if not first_empresa:
                    out += "<br><br>"
                first_empresa = False

                emp_label = _span("mk-color-empresa", emp)
                out += f"**Empresa: {emp_label}** — {len(emp_rows)} doc(s) — Total líquido (A-B): **R$ {emp_total_fmt}**\n"
                if emp_total_vendas_brutas:
                    out += f"A (vendas brutas): **R$ {emp_vendas_fmt}**\n"
                if emp_total_devolucoes:
                    out += f"B (devoluções): **R$ {emp_devol_fmt}**\n"
                if emp_total_doc:
                    out += f"DOC/ICMS (não somado): **R$ {emp_doc_fmt}**\n"
                if cc_line:
                    out += cc_line
                out += "\n"

                # Agrupar por tipo de operação (base) dentro da empresa
                ops = {}
                for rr in emp_rows:
                    op = _op_base(rr.get("descricao_tipo_operacao_documento"))
                    if _is_excluded_op(op):
                        continue
                    ops.setdefault(op, []).append(rr)

                for op_name, op_rows in sorted(ops.items(), key=lambda kv: len(kv[1]), reverse=True):
                    out += f"- **{op_name}**\n"
                    for rr in op_rows:
                        if shown >= max_linhas:
                            break
                        data = rr.get("data_emissao") or ""
                        nf = rr.get("numero_nf") or ""
                        nf_str = str(nf).strip()
                        cli = (rr.get("cliente") or "").strip()
                        cli_txt = cli if cli else "—"
                        cli_disp = _span("mk-color-cliente", cli_txt) if cli_txt != "—" else _span("mk-color-muted", cli_txt)
                        val = _fmt_brl(rr.get("total_nf"))
                        # ⚠️ Aviso na linha da NF (mais visível): em aberto > 0 e vencimento <= hoje
                        # (não depende de <span>; usa só texto/markdown)
                        alert_nf = ""
                        try:
                            ab_num = _parse_float_any(rr.get("valor_em_aberto"))
                            venc_raw = rr.get("proximo_vencimento")
                            venc_s = str(venc_raw or "").strip()
                            venc_s10 = venc_s[:10] if len(venc_s) >= 10 else ""
                            hoje_s = hoje.isoformat()
                            overdue = bool(venc_s10 and re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10) and (venc_s10 < hoje_s))
                            due_today = bool(venc_s10 and re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10) and (venc_s10 == hoje_s))
                            if ab_num > 0 and overdue:
                                dias = None
                                try:
                                    venc_dt2 = datetime.strptime(venc_s10, "%Y-%m-%d").date()
                                    dias = (hoje - venc_dt2).days
                                except Exception:
                                    dias = None
                                alert_nf = f" ⚠️{dias}d" if isinstance(dias, int) else " ⚠️"
                            elif ab_num > 0 and due_today:
                                alert_nf = " ⏰hoje"
                        except Exception:
                            alert_nf = ""
                        # Alguns movimentos (ex.: ICMS) podem usar um "número de documento/ref" que não é NF-e padrão.
                        rotulo_doc = "NF"
                        if op_name.strip().upper() == "ICMS":
                            rotulo_doc = "DOC"
                        # Destaques: NF em negrito, valor em negrito
                        out += f"  - {data} | {rotulo_doc} **{_escape_html(nf_str)}** | **{_escape_html(val)}** | {cli_disp}{alert_nf}\n"
                        # ✅ MVP financeiro: mostrar recebido/em aberto logo abaixo (apenas quando fizer sentido)
                        try:
                            if rotulo_doc == "NF" and (not _is_devolucao_op(_op_base_totais(rr.get('descricao_tipo_operacao_documento')))):
                                rec = rr.get("valor_recebido")
                                aberto = rr.get("valor_em_aberto")
                                venc = rr.get("proximo_vencimento")
                                if rec is not None or aberto is not None:
                                    rec_txt = _fmt_brl(rec or 0.0)
                                    ab_txt = _fmt_brl(aberto or 0.0)
                                    # Vencimento:
                                    # - se vencido e em aberto: **bold** + ⚠️
                                    # - se vence hoje e em aberto: **bold** + ⏰
                                    venc_txt = ""
                                    try:
                                        ab_num = _parse_float_any(aberto)
                                        venc_s = str(venc or "").strip()
                                        venc_s10 = venc_s[:10] if len(venc_s) >= 10 else ""
                                        hoje_s = hoje.isoformat()
                                        overdue = bool(venc_s10 and re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10) and (venc_s10 < hoje_s))
                                        due_today = bool(venc_s10 and re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10) and (venc_s10 == hoje_s))
                                        if venc_s:
                                            if ab_num > 0 and overdue:
                                                venc_txt = f" | Venc: **{_escape_html(venc_s10 or venc_s)}** ⚠️"
                                            elif ab_num > 0 and due_today:
                                                venc_txt = f" | Venc: **{_escape_html(venc_s10 or venc_s)}** ⏰"
                                            else:
                                                venc_txt = f" | Venc: {_escape_html(venc_s10 or venc_s)}"
                                    except Exception:
                                        venc_txt = f" | Venc: {_escape_html(str(venc))}" if venc else ""
                                    rec_col = _span("mk-color-recebido", rec_txt)
                                    ab_col = _span("mk-color-aberto", ab_txt)
                                    # ⚠️ Aviso automático: NF em aberto e vencida / vence hoje
                                    alert_txt = ""
                                    try:
                                        ab_num = _parse_float_any(aberto)
                                        venc_s = str(venc or "").strip()
                                        venc_s10 = venc_s[:10] if len(venc_s) >= 10 else ""
                                        hoje_s = hoje.isoformat()
                                        overdue = bool(venc_s10 and re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10) and (venc_s10 < hoje_s))
                                        due_today = bool(venc_s10 and re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10) and (venc_s10 == hoje_s))
                                        if ab_num > 0 and overdue and venc_s10:
                                            dias = (hoje - datetime.strptime(venc_s10, "%Y-%m-%d").date()).days
                                            # ✅ Não depender de HTML/CSS para o alerta aparecer
                                            alert_txt = f" | ⚠️ Vencida ({dias}d)"
                                        elif ab_num > 0 and due_today:
                                            alert_txt = " | ⏰ Vence hoje"
                                    except Exception:
                                        alert_txt = ""

                                    out += f"    **Recebido:** {rec_col} | **Em aberto:** {ab_col}{venc_txt}{alert_txt}\n"
                                    shown += 1
                        except Exception:
                            pass
                        shown += 1
                    out += "\n"
                    if shown >= max_linhas:
                        break

                if shown >= max_linhas:
                    break

            if len(rows) > max_linhas:
                out += (
                    f"⚠️ Mostrando {max_linhas} de {len(rows)} linhas (formato resumido por empresa/operação). "
                    f"Para ver tudo, aumente `SALES_OUTPUT_MAX_LINES` no .env.\n"
                )

            # 🔎 Debug opcional: diagnosticar por que alertas de vencimento não aparecem
            # Ativar via .env: SALES_REPORT_DEBUG_ALERTS=true
            try:
                debug_flag = os.getenv("SALES_REPORT_DEBUG_ALERTS", "false").strip().lower()
                if (debug_flag in {"1", "true", "yes"}) or bool(argumentos.get("_debug_alerts")):
                    def _parse_date_any_dbg(v: Any):
                        """
                        Parser local (somente debug) para evitar NameError caso helpers não existam neste escopo.
                        Aceita:
                        - date/datetime do driver
                        - strings ISO (YYYY-MM-DD / YYYY-MM-DDTHH:MM:SS)
                        - strings DD/MM/YYYY
                        """
                        if v is None:
                            return None
                        # datetime/date vindo do driver
                        if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
                            try:
                                return v.date() if hasattr(v, "date") else v
                            except Exception:
                                pass
                        s = str(v).strip()
                        if not s:
                            return None
                        try:
                            return datetime.fromisoformat(s).date()
                        except Exception:
                            pass
                        # Se vier "YYYY-MM-DD ..." (com hora), pegar só a data
                        if len(s) >= 10 and re.match(r"^\d{4}-\d{2}-\d{2}$", s[:10]):
                            try:
                                return datetime.strptime(s[:10], "%Y-%m-%d").date()
                            except Exception:
                                pass
                        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                            try:
                                return datetime.strptime(s, fmt).date()
                            except Exception:
                                continue
                        return None

                    debug_lines = []
                    debug_lines.append("🧪 **DEBUG (Sales alert)**")
                    debug_lines.append(f"- SALES_REPORT_DEBUG_ALERTS: `{debug_flag}`")
                    debug_lines.append(f"- hoje (container): `{hoje}`")
                    samples = 0
                    for rr in (rows or []):
                        if not isinstance(rr, dict):
                            continue
                        nf = rr.get("numero_nf")
                        venc_raw = rr.get("proximo_vencimento")
                        ab_raw = rr.get("valor_em_aberto")
                        ab_num = _parse_float_any(ab_raw)
                        venc_s = str(venc_raw or "").strip()
                        venc_dt = _parse_date_any_dbg(venc_raw)
                        cond = bool(venc_dt and ab_num > 0 and venc_dt < hoje)
                        # mostrar poucas linhas pra não poluir
                        debug_lines.append(
                            f"- nf={nf!r} ab_raw={ab_raw!r} ab_num={ab_num!r} venc_raw={venc_raw!r} venc_dt={venc_dt!r} cond={cond}"
                        )
                        samples += 1
                        if samples >= 8:
                            break
                    out += "\n\n" + "\n".join(debug_lines) + "\n"
            except Exception:
                pass

            # ✅ Persistir como "relatório ativo" (domínio: vendas) para permitir refinamentos sem reconsultar SQL.
            try:
                session_id = (argumentos.get("session_id") or getattr(context, "session_id", None) or "").strip()
                if session_id:
                    from services import report_service

                    report_id = f"rel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    report_meta_inline = {
                        "tipo": "vendas_nf",
                        "id": report_id,
                        "created_at": datetime.now().isoformat(),
                        "ttl_min": 240,
                        "filtrado": False,
                    }
                    out_com_meta = out.rstrip() + f"\n\n[REPORT_META:{json.dumps(report_meta_inline, ensure_ascii=False)}]"

                    # ⚠️ IMPORTANTE: rows/meta podem conter Decimal/date → tornar JSON-safe antes de persistir no SQLite.
                    rows_json_safe = SalesToolsHandler._to_json_safe(rows)
                    meta_json_safe = SalesToolsHandler._to_json_safe(meta)

                    relatorio = report_service.criar_relatorio_gerado(
                        tipo_relatorio="vendas_nf",
                        texto_chat=out_com_meta,
                        categoria=None,
                        filtros={
                            "inicio": inicio_r,
                            "fim": fim_r,
                            "termo": termo_r,
                        },
                        meta_json={
                            "dados_json": {
                                "tipo_relatorio": "vendas_nf",
                                "rows": rows_json_safe,
                                "meta": meta_json_safe,
                            }
                        },
                    )
                    report_service.salvar_ultimo_relatorio(session_id=session_id, relatorio=relatorio)
                    out = out_com_meta
            except Exception as e:
                logger.debug(f"⚠️ Não foi possível salvar relatório de vendas no contexto: {e}")

            return {"sucesso": True, "resposta": out, "dados": rows, "meta": meta}
        except Exception as e:
            logger.error(f"❌ Erro em consultar_vendas_nf_make: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "resposta": f"❌ Erro ao consultar vendas por NF: {str(e)}"}

    @staticmethod
    def filtrar_relatorio_vendas(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Tool: filtrar_relatorio_vendas
        Aplica filtros sobre o último relatório de vendas salvo (domínio: vendas), sem reconsultar SQL.
        """
        try:
            session_id = (argumentos.get("session_id") or getattr(context, "session_id", None) or "").strip()
            if not session_id:
                return {
                    "sucesso": False,
                    "erro": "SESSION_ID_REQUIRED",
                    "resposta": "❌ Não consegui identificar a sessão para filtrar o relatório de vendas.",
                }

            from services import report_service

            report_id = (argumentos.get("report_id") or "").strip() or None
            relatorio_base = None
            relatorio_base_id = None

            if report_id:
                relatorio_base = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=report_id)
                relatorio_base_id = report_id if relatorio_base else None
            else:
                last_visible = report_service.obter_last_visible_report_id(session_id=session_id, dominio="vendas") or {}
                relatorio_base_id = last_visible.get("id")
                if relatorio_base_id:
                    relatorio_base = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=relatorio_base_id)

            if not relatorio_base:
                return {
                    "sucesso": False,
                    "erro": "NO_ACTIVE_SALES_REPORT",
                    "resposta": "❌ Não encontrei um relatório de vendas ativo para filtrar. Gere primeiro um relatório com `vendas ... por NF`.",
                }

            base_meta = relatorio_base.meta_json or {}
            dados_json = base_meta.get("dados_json") if isinstance(base_meta, dict) else None
            base_rows = (dados_json.get("rows") if isinstance(dados_json, dict) else None) or []
            base_query_meta = (dados_json.get("meta") if isinstance(dados_json, dict) else None) or {}
            if not isinstance(base_rows, list) or not base_rows:
                return {
                    "sucesso": False,
                    "erro": "SALES_REPORT_ROWS_MISSING",
                    "resposta": "❌ Este relatório salvo não contém as linhas de vendas para filtrar. Gere novamente o relatório de vendas por NF.",
                }

            # ---------- filtros ----------
            cliente = (argumentos.get("cliente") or "").strip() or None
            empresa = (argumentos.get("empresa") or "").strip() or None
            operacao = (argumentos.get("operacao") or "").strip() or None
            centro = (argumentos.get("centro") or "").strip() or None
            apenas_devolucao = bool(argumentos.get("apenas_devolucao", False))
            apenas_icms = bool(argumentos.get("apenas_icms", False))
            data = (argumentos.get("data") or "").strip() or None
            inicio = (argumentos.get("inicio") or "").strip() or None
            fim = (argumentos.get("fim") or "").strip() or None
            min_valor = argumentos.get("min_valor")
            max_valor = argumentos.get("max_valor")

            ordenar_por = (argumentos.get("ordenar_por") or "").strip().lower() or None  # data|valor|nf
            ordem = (argumentos.get("ordem") or "desc").strip().lower()
            top = argumentos.get("top")
            try:
                top_n = int(top) if top is not None else None
                if top_n is not None and top_n <= 0:
                    top_n = None
            except Exception:
                top_n = None

            def _parse_date(s: str) -> str:
                if not s:
                    return ""
                t = s.strip()
                # aceitar YYYY-MM-DD e DD/MM/YYYY (best-effort)
                try:
                    if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
                        return t
                    if re.match(r"^\d{2}/\d{2}/\d{4}$", t):
                        dd, mm, yyyy = t.split("/")
                        return f"{yyyy}-{mm}-{dd}"
                except Exception:
                    pass
                return t

            data_n = _parse_date(data) if data else None
            inicio_n = _parse_date(inicio) if inicio else None
            fim_n = _parse_date(fim) if fim else None

            def _op_base_totais(desc: Any) -> str:
                s = (str(desc) if desc is not None else "").strip()
                if not s:
                    return "Outros"
                s = s.replace(" - SEM CONFERÊNCIA", "").replace(" - Sem Conferência", "")
                if " - " in s:
                    s = s.split(" - ", 1)[0].strip()
                return s or "Outros"

            def _is_devolucao_op(op_name: str) -> bool:
                op_u = (op_name or "").strip().upper()
                return ("DEVOLU" in op_u) or ("DEVOLUC" in op_u)

            def _to_float(x: Any) -> float:
                try:
                    return float(x)
                except Exception:
                    return 0.0

            filtered = []
            for r in base_rows:
                if not isinstance(r, dict):
                    continue
                op_full = r.get("descricao_tipo_operacao_documento")
                op_base = _op_base_totais(op_full)
                is_doc = op_base.strip().upper() == "ICMS"
                is_devol = _is_devolucao_op(op_base)

                if apenas_icms and not is_doc:
                    continue
                if apenas_devolucao and not is_devol:
                    continue

                if cliente:
                    cli = (r.get("cliente") or "").strip()
                    if cliente.lower() not in cli.lower():
                        continue
                if empresa:
                    emp = (r.get("empresa_vendedora") or "").strip()
                    if empresa.lower() not in emp.lower():
                        continue
                if centro:
                    cc = (r.get("descricao_centro_custo_documento") or "").strip()
                    if centro.lower() not in cc.lower():
                        continue
                if operacao:
                    cc = (r.get("descricao_centro_custo_documento") or "").strip()
                    if (
                        operacao.lower() not in (op_base or "").lower()
                        and operacao.lower() not in (str(op_full or "")).lower()
                        and operacao.lower() not in cc.lower()
                    ):
                        continue

                d = (r.get("data_emissao") or "").strip()
                if data_n and d != data_n:
                    continue
                if inicio_n and d and d < inicio_n:
                    continue
                if fim_n and d and d >= fim_n:
                    continue

                v = _to_float(r.get("total_nf"))
                if min_valor is not None:
                    try:
                        if v < float(min_valor):
                            continue
                    except Exception:
                        pass
                if max_valor is not None:
                    try:
                        if v > float(max_valor):
                            continue
                    except Exception:
                        pass

                filtered.append(r)

            # Ordenação
            reverse = ordem != "asc"
            if ordenar_por == "valor":
                filtered.sort(key=lambda rr: _to_float(rr.get("total_nf")), reverse=reverse)
            elif ordenar_por == "nf":
                filtered.sort(key=lambda rr: str(rr.get("numero_nf") or ""), reverse=reverse)
            else:
                # default: data
                filtered.sort(key=lambda rr: str(rr.get("data_emissao") or ""), reverse=reverse)

            if top_n is not None:
                filtered = filtered[:top_n]

            # Reusar formatação do relatório de vendas por NF (sem SQL).
            meta = dict(base_query_meta or {})
            meta["linhas"] = len(filtered)
            meta["filtrado_de_report_id"] = relatorio_base_id
            meta["filtros_aplicados"] = {
                k: v
                for k, v in {
                    "cliente": cliente,
                    "empresa": empresa,
                    "operacao": operacao,
                    "centro": centro,
                    "apenas_devolucao": apenas_devolucao,
                    "apenas_icms": apenas_icms,
                    "data": data_n,
                    "inicio": inicio_n,
                    "fim": fim_n,
                    "min_valor": min_valor,
                    "max_valor": max_valor,
                    "ordenar_por": ordenar_por,
                    "ordem": ordem,
                    "top": top_n,
                }.items()
                if v not in (None, "", False)
            }

            # Montar um "resultado" no mesmo formato esperado pela renderização existente:
            # copiar o bloco principal de renderização de consultar_vendas_nf_make, mas usando `filtered` e `meta`.
            inicio_r = meta.get("inicio") or ""
            fim_r = meta.get("fim") or ""
            termo_r = meta.get("termo")
            termo_tokens = meta.get("termo_tokens") or []

            titulo = "🧾 **Vendas por NF (Make/Spalla) — FILTRADO**\n\n"
            if relatorio_base_id:
                titulo += f"Base: `{relatorio_base_id}`\n"
            titulo += f"Período: **{inicio_r}** até **{fim_r}** (fim exclusivo)\n"
            if termo_r:
                titulo += f"Filtro (termo original): **{termo_r}**\n"
                if termo_tokens:
                    titulo += f"Tokens aplicados (AND): `{', '.join(str(t) for t in termo_tokens)}`\n"
            if meta.get("filtros_aplicados"):
                titulo += f"Filtros aplicados: `{json.dumps(meta['filtros_aplicados'], ensure_ascii=False)}`\n"
            titulo += f"Linhas: **{meta.get('linhas', len(filtered))}**\n\n"

            if not filtered:
                return {"sucesso": True, "resposta": titulo + "ℹ️ Nenhuma NF encontrada após aplicar os filtros.", "dados": [], "meta": meta}

            # ✅ Resumos úteis (A / B / A-B, DOC/ICMS fora)
            total_sum_vendas_brutas = 0.0
            total_sum_devolucoes = 0.0
            total_sum_doc = 0.0
            centros = {}
            cliente_vazio = True
            # ✅ Alertas de cobrança no relatório filtrado (modo normal):
            count_vencidas = 0
            sum_vencidas_aberto = 0.0
            count_vence_hoje = 0
            sum_vence_hoje_aberto = 0.0

            def _is_excluded_op(op_name: str) -> bool:
                op_u = (op_name or "").strip().upper()
                # ✅ Regra de negócio: "Nacionalização por Conta Própria" NÃO é venda (é entrada/importação).
                if ("CONTA" in op_u) and ("PROPR" in op_u) and ("NACIONALIZ" in op_u):
                    return True
                return op_u in {
                    "COMPRA DE MERCADORIA PARA REVENDA",
                    "COMISSÃO DE VENDA",
                    "COMISSAO DE VENDA",
                }

            for r in filtered:
                if not isinstance(r, dict):
                    continue
                v = r.get("total_nf")
                op = _op_base_totais(r.get("descricao_tipo_operacao_documento"))
                is_doc = op.strip().upper() == "ICMS"
                is_excluded = _is_excluded_op(op)
                is_devolucao = _is_devolucao_op(op)
                try:
                    if is_doc:
                        total_sum_doc += float(v) if v is not None else 0.0
                    elif not is_excluded:
                        vv = float(v) if v is not None else 0.0
                        if is_devolucao:
                            total_sum_devolucoes += abs(vv)
                        else:
                            total_sum_vendas_brutas += vv
                            # ✅ Cobrança: venceram/vence hoje e ainda em aberto
                            try:
                                hoje_s = datetime.now().date().isoformat()
                                aberto = float(r.get("valor_em_aberto") or 0.0)
                                if aberto > 0:
                                    venc_s = str(r.get("proximo_vencimento") or "").strip()
                                    venc_s10 = venc_s[:10] if len(venc_s) >= 10 else venc_s
                                    if re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s10):
                                        if venc_s10 < hoje_s:
                                            count_vencidas += 1
                                            sum_vencidas_aberto += float(aberto)
                                        elif venc_s10 == hoje_s:
                                            count_vence_hoje += 1
                                            sum_vence_hoje_aberto += float(aberto)
                            except Exception:
                                pass
                except Exception:
                    pass
                cc = (r.get("descricao_centro_custo_documento") or "").strip()
                if cc:
                    try:
                        if (not is_doc) and (not is_excluded) and (not is_devolucao):
                            centros[cc] = centros.get(cc, 0.0) + (float(v) if v is not None else 0.0)
                    except Exception:
                        centros[cc] = centros.get(cc, 0.0)
                if (r.get("cliente") or "").strip():
                    cliente_vazio = False

            total_sum_liquido = total_sum_vendas_brutas - total_sum_devolucoes
            if total_sum_vendas_brutas or total_sum_devolucoes:
                if total_sum_vendas_brutas:
                    titulo += f"A - Total de vendas (bruto, sem devolução): **R$ {total_sum_vendas_brutas:,.2f}**\n".replace(
                        ",", "X"
                    ).replace(".", ",").replace("X", ".")
                if total_sum_devolucoes:
                    titulo += f"B - Total de devoluções: **R$ {total_sum_devolucoes:,.2f}**\n".replace(",", "X").replace(
                        ".", ","
                    ).replace("X", ".")
                titulo += f"A-B - Vendas líquidas: **R$ {total_sum_liquido:,.2f}**\n".replace(",", "X").replace(".", ",").replace(
                    "X", "."
                )
            if total_sum_doc:
                titulo += f"DOC/ICMS (listado, mas não somado): **R$ {total_sum_doc:,.2f}**\n".replace(",", "X").replace(".", ",").replace("X", ".")
            if centros:
                top_cc = sorted(centros.items(), key=lambda x: x[1], reverse=True)[:5]
                titulo += "Top centros (por total): " + ", ".join(
                    f"{cc} (R$ {val:,.2f})".replace(",", "X").replace(".", ",").replace("X", ".")
                    for cc, val in top_cc
                ) + "\n"
            if count_vence_hoje or count_vencidas:
                def _fmt_brl_inline(n: float) -> str:
                    s = f"{float(n or 0.0):,.2f}"
                    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
                    return f"R$ {s}"
                parts = []
                if count_vence_hoje:
                    parts.append(f"vence hoje: **{_fmt_brl_inline(sum_vence_hoje_aberto)}** ({count_vence_hoje} NF)")
                if count_vencidas:
                    parts.append(f"vencidas: **{_fmt_brl_inline(sum_vencidas_aberto)}** ({count_vencidas} NF)")
                titulo += "⚠️ **Cobrança (em aberto):** " + " | ".join(parts) + "\n"
            titulo += "\n"

            # Render "executivo" por empresa/operação (mesma lógica)
            hard_cap = SalesToolsHandler._max_output_lines(default=500)
            max_linhas = len(filtered) if hard_cap <= 0 else min(len(filtered), hard_cap)

            def _fmt_brl(value: Any) -> str:
                try:
                    n = float(value)
                except Exception:
                    return "" if value is None else str(value)
                s = f"{n:,.2f}"
                s = s.replace(",", "X").replace(".", ",").replace("X", ".")
                return f"R$ {s}"

            def _escape_html(s: Any) -> str:
                t = "" if s is None else str(s)
                return (
                    t.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;")
                )

            colors_enabled = os.getenv("SALES_REPORT_COLORS", "true").strip().lower() not in {"0", "false", "no"}

            def _span(cls: str, txt: Any) -> str:
                safe = _escape_html(txt)
                return f'<span class="{cls}">{safe}</span>' if colors_enabled else safe

            def _parse_date_any(v: Any):
                if v is None:
                    return None
                if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
                    try:
                        return v.date() if hasattr(v, "date") else v
                    except Exception:
                        pass
                s = str(v).strip()
                if not s:
                    return None
                try:
                    return datetime.fromisoformat(s).date()
                except Exception:
                    pass
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        continue
                return None

            hoje = datetime.now().date()

            def _op_base(desc: Any) -> str:
                s = (str(desc) if desc is not None else "").strip()
                if not s:
                    return "Outros"
                s = s.replace(" - SEM CONFERÊNCIA", "").replace(" - Sem Conferência", "")
                if " - " in s:
                    s = s.split(" - ", 1)[0].strip()
                return s or "Outros"

            def _cc_label(r: Dict[str, Any]) -> str:
                cc = (r.get("descricao_centro_custo_documento") or "").strip()
                cod = r.get("codigo_centro_custo_documento")
                cod_s = str(cod).strip() if cod is not None else ""
                if cc and cod_s:
                    return f"{cc} | {cod_s}"
                return cc or (cod_s or "")

            out = titulo
            if cliente_vazio:
                out += "Cliente: ⚠️ ainda não localizado no legado por este caminho.\n\n"

            empresa_key = "empresa_vendedora"
            empresas = sorted({(r.get(empresa_key) or "N/A").strip() for r in filtered if isinstance(r, dict)})
            shown = 0
            first_empresa = True
            for emp in empresas:
                emp_rows = [r for r in filtered if isinstance(r, dict) and ((r.get(empresa_key) or "N/A").strip() == emp)]
                if not emp_rows:
                    continue

                emp_total_vendas_brutas = 0.0
                emp_total_devolucoes = 0.0
                emp_total_doc = 0.0
                for rr in emp_rows:
                    try:
                        op = _op_base_totais(rr.get("descricao_tipo_operacao_documento"))
                        is_doc = op.strip().upper() == "ICMS"
                        is_excluded = _is_excluded_op(op)
                        is_devolucao = _is_devolucao_op(op)
                        if is_doc:
                            emp_total_doc += float(rr.get("total_nf")) if rr.get("total_nf") is not None else 0.0
                        elif not is_excluded:
                            vv = float(rr.get("total_nf")) if rr.get("total_nf") is not None else 0.0
                            if is_devolucao:
                                emp_total_devolucoes += abs(vv)
                            else:
                                emp_total_vendas_brutas += vv
                    except Exception:
                        pass

                emp_total_liquido = emp_total_vendas_brutas - emp_total_devolucoes
                emp_total_fmt = f"{emp_total_liquido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                emp_doc_fmt = f"{emp_total_doc:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                emp_vendas_fmt = f"{emp_total_vendas_brutas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                emp_devol_fmt = f"{emp_total_devolucoes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                cc_unique = sorted({_cc_label(rr) for rr in emp_rows if isinstance(rr, dict) and _cc_label(rr)})
                cc_line = f"Centro: **{cc_unique[0]}**\n" if len(cc_unique) == 1 else ""

                # Separar empresas em blocos (o frontend comprime \n\n -> <br>, então usar <br><br>)
                if not first_empresa:
                    out += "<br><br>"
                first_empresa = False

                emp_label = _span("mk-color-empresa", emp)
                out += f"**Empresa: {emp_label}** — {len(emp_rows)} doc(s) — Total líquido (A-B): **R$ {emp_total_fmt}**\n"
                if emp_total_vendas_brutas:
                    out += f"A (vendas brutas): **R$ {emp_vendas_fmt}**\n"
                if emp_total_devolucoes:
                    out += f"B (devoluções): **R$ {emp_devol_fmt}**\n"
                if emp_total_doc:
                    out += f"DOC/ICMS (não somado): **R$ {emp_doc_fmt}**\n"
                if cc_line:
                    out += cc_line
                out += "\n"

                ops = {}
                for rr in emp_rows:
                    opn = _op_base(rr.get("descricao_tipo_operacao_documento"))
                    if _is_excluded_op(opn):
                        continue
                    ops.setdefault(opn, []).append(rr)

                for op_name, op_rows in sorted(ops.items(), key=lambda kv: len(kv[1]), reverse=True):
                    out += f"- **{op_name}**\n"
                    for rr in op_rows:
                        if shown >= max_linhas:
                            break
                        d = rr.get("data_emissao") or ""
                        nf = str(rr.get("numero_nf") or "").strip()
                        cli = (rr.get("cliente") or "").strip() or "—"
                        cli_disp = _span("mk-color-cliente", cli) if cli != "—" else _span("mk-color-muted", cli)
                        val = _fmt_brl(rr.get("total_nf"))
                        # ⚠️ Aviso na linha da NF (mais visível): em aberto > 0 e vencimento <= hoje
                        alert_nf = ""
                        try:
                            venc_dt = _parse_date_any(rr.get("proximo_vencimento"))
                            ab_raw = rr.get("valor_em_aberto")
                            ab_num = _parse_float_any(ab_raw)
                            venc_s = str(rr.get("proximo_vencimento") or "").strip()
                            overdue = (venc_dt is not None and venc_dt < hoje) or (
                                bool(re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s)) and venc_s < hoje.isoformat()
                            )
                            due_today = (venc_dt is not None and venc_dt == hoje) or (
                                bool(re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s)) and venc_s == hoje.isoformat()
                            )
                            if ab_num > 0 and overdue:
                                dias = (hoje - venc_dt).days
                                # ✅ Não depender de HTML/CSS para o alerta aparecer
                                alert_nf = f" ⚠️{dias}d"
                            elif ab_num > 0 and due_today:
                                alert_nf = " ⏰hoje"
                        except Exception:
                            alert_nf = ""
                        rotulo_doc = "DOC" if op_name.strip().upper() == "ICMS" else "NF"
                        out += f"  - {d} | {rotulo_doc} **{_escape_html(nf)}** | **{_escape_html(val)}** | {cli_disp}{alert_nf}\n"
                        # ✅ MVP financeiro também no filtrado (mantém consistência visual)
                        try:
                            if rotulo_doc == "NF" and (not _is_devolucao_op(_op_base_totais(rr.get('descricao_tipo_operacao_documento')))):
                                rec = rr.get("valor_recebido")
                                aberto = rr.get("valor_em_aberto")
                                venc = rr.get("proximo_vencimento")
                                if rec is not None or aberto is not None:
                                    rec_txt = _fmt_brl(rec or 0.0)
                                    ab_txt = _fmt_brl(aberto or 0.0)
                                    # Destacar vencimento:
                                    # - vencido: vermelho/bold + ⚠️
                                    # - vence hoje: laranja/bold + ⏰
                                    venc_txt = ""
                                    try:
                                        ab_num = _parse_float_any(aberto)
                                        venc_dt = _parse_date_any(venc)
                                        venc_s = str(venc or "").strip()
                                        overdue = (venc_dt is not None and venc_dt < hoje) or (
                                            bool(re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s)) and venc_s < hoje.isoformat()
                                        )
                                        due_today = (venc_dt is not None and venc_dt == hoje) or (
                                            bool(re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s)) and venc_s == hoje.isoformat()
                                        )
                                        if venc:
                                            venc_disp = _escape_html(venc_s)
                                            if ab_num > 0 and overdue:
                                                venc_disp = f'<span style="color:#c62828;font-weight:800;">{venc_disp}</span>'
                                            elif ab_num > 0 and due_today:
                                                venc_disp = f'<span style="color:#ef6c00;font-weight:800;">{venc_disp}</span> ⏰'
                                            venc_txt = f" | Venc: {venc_disp}"
                                    except Exception:
                                        venc_txt = f" | Venc: {_escape_html(str(venc))}" if venc else ""
                                    rec_col = _span("mk-color-recebido", rec_txt)
                                    ab_col = _span("mk-color-aberto", ab_txt)
                                    # ⚠️ Aviso automático: NF em aberto e vencida / vence hoje
                                    alert_txt = ""
                                    try:
                                        ab_num = _parse_float_any(aberto)
                                        venc_dt = _parse_date_any(venc)
                                        venc_s = str(venc or "").strip()
                                        overdue = (venc_dt is not None and venc_dt < hoje) or (
                                            bool(re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s)) and venc_s < hoje.isoformat()
                                        )
                                        due_today = (venc_dt is not None and venc_dt == hoje) or (
                                            bool(re.match(r"^\d{4}-\d{2}-\d{2}$", venc_s)) and venc_s == hoje.isoformat()
                                        )
                                        if ab_num > 0 and overdue:
                                            dias = (hoje - venc_dt).days
                                            # ✅ Não depender de HTML/CSS para o alerta aparecer
                                            alert_txt = f" | ⚠️ Vencida ({dias}d)"
                                        elif ab_num > 0 and due_today:
                                            alert_txt = " | ⏰ Vence hoje"
                                    except Exception:
                                        alert_txt = ""

                                    out += f"    **Recebido:** {rec_col} | **Em aberto:** {ab_col}{venc_txt}{alert_txt}\n"
                                    shown += 1
                        except Exception:
                            pass
                        shown += 1
                    out += "\n"
                    if shown >= max_linhas:
                        break

                if shown >= max_linhas:
                    break

            if len(filtered) > max_linhas:
                out += (
                    f"⚠️ Mostrando {max_linhas} de {len(filtered)} linhas (formato resumido por empresa/operação). "
                    f"Para ver tudo, aumente `SALES_OUTPUT_MAX_LINES` no .env.\n"
                )

            # ✅ Persistir como novo relatório filtrado (domínio: vendas)
            try:
                new_report_id = f"rel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                report_meta_inline = {
                    "tipo": "vendas_nf",
                    "id": new_report_id,
                    "created_at": datetime.now().isoformat(),
                    "ttl_min": 240,
                    "filtrado": True,
                    "base_id": relatorio_base_id,
                }
                out_com_meta = out.rstrip() + f"\n\n[REPORT_META:{json.dumps(report_meta_inline, ensure_ascii=False)}]"

                filtered_json_safe = SalesToolsHandler._to_json_safe(filtered)
                meta_safe = SalesToolsHandler._to_json_safe(meta)

                relatorio = report_service.criar_relatorio_gerado(
                    tipo_relatorio="vendas_nf",
                    texto_chat=out_com_meta,
                    categoria=None,
                    filtros=meta.get("filtros_aplicados") or {},
                    meta_json={
                        "dados_json": {
                            "tipo_relatorio": "vendas_nf",
                            "rows": filtered_json_safe,
                            "meta": meta_safe,
                            "filtrado": True,
                            "base_id": relatorio_base_id,
                        }
                    },
                )
                report_service.salvar_ultimo_relatorio(session_id=session_id, relatorio=relatorio)
                out = out_com_meta
            except Exception as e:
                logger.debug(f"⚠️ Não foi possível salvar relatório filtrado de vendas: {e}")

            return {"sucesso": True, "resposta": out, "dados": filtered, "meta": meta}
        except Exception as e:
            logger.error(f"❌ Erro em filtrar_relatorio_vendas: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "resposta": f"❌ Erro ao filtrar relatório de vendas: {str(e)}"}

    @staticmethod
    def curva_abc_vendas(argumentos: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Tool: curva_abc_vendas
        Monta Curva ABC sobre o relatório de vendas salvo (domínio: vendas), sem reconsultar SQL.
        """
        try:
            session_id = (argumentos.get("session_id") or getattr(context, "session_id", None) or "").strip()
            if not session_id:
                return {
                    "sucesso": False,
                    "erro": "SESSION_ID_REQUIRED",
                    "resposta": "❌ Não consegui identificar a sessão para gerar a Curva ABC.",
                }

            from services import report_service

            report_id = (argumentos.get("report_id") or "").strip() or None
            relatorio_base = None
            relatorio_base_id = None
            if report_id:
                relatorio_base = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=report_id)
                relatorio_base_id = report_id if relatorio_base else None
            else:
                last_visible = report_service.obter_last_visible_report_id(session_id=session_id, dominio="vendas") or {}
                relatorio_base_id = last_visible.get("id")
                if relatorio_base_id:
                    relatorio_base = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=relatorio_base_id)

            if not relatorio_base:
                return {
                    "sucesso": False,
                    "erro": "NO_ACTIVE_SALES_REPORT",
                    "resposta": "❌ Não encontrei um relatório de vendas ativo. Gere primeiro um relatório com `vendas ... por NF`.",
                }

            base_meta = relatorio_base.meta_json or {}
            dados_json = base_meta.get("dados_json") if isinstance(base_meta, dict) else None
            rows = (dados_json.get("rows") if isinstance(dados_json, dict) else None) or []
            query_meta = (dados_json.get("meta") if isinstance(dados_json, dict) else None) or {}
            if not isinstance(rows, list) or not rows:
                return {
                    "sucesso": False,
                    "erro": "SALES_REPORT_ROWS_MISSING",
                    "resposta": "❌ O relatório salvo não contém as linhas necessárias para Curva ABC. Gere novamente o relatório de vendas por NF.",
                }

            agrupar_por = (argumentos.get("agrupar_por") or "cliente").strip().lower()
            a_pct = argumentos.get("a_pct", 0.80)
            b_pct = argumentos.get("b_pct", 0.95)
            top = argumentos.get("top", 30)
            incluir_outros = bool(argumentos.get("incluir_outros", True))
            min_total = argumentos.get("min_total")

            try:
                a_pct = float(a_pct)
            except Exception:
                a_pct = 0.80
            try:
                b_pct = float(b_pct)
            except Exception:
                b_pct = 0.95
            if a_pct <= 0 or a_pct >= 1:
                a_pct = 0.80
            if b_pct <= a_pct or b_pct >= 1:
                b_pct = 0.95
            try:
                top = int(top)
            except Exception:
                top = 30
            top = max(5, min(top, 200))

            def _fmt_brl(value: Any) -> str:
                try:
                    n = float(value)
                except Exception:
                    n = 0.0
                s = f"{n:,.2f}"
                s = s.replace(",", "X").replace(".", ",").replace("X", ".")
                return f"R$ {s}"

            def _op_base(desc: Any) -> str:
                s = (str(desc) if desc is not None else "").strip()
                if not s:
                    return "Outros"
                s = s.replace(" - SEM CONFERÊNCIA", "").replace(" - Sem Conferência", "")
                if " - " in s:
                    s = s.split(" - ", 1)[0].strip()
                return s or "Outros"

            def _is_devolucao_op(op_name: str) -> bool:
                op_u = (op_name or "").strip().upper()
                return ("DEVOLU" in op_u) or ("DEVOLUC" in op_u)

            def _is_excluded_op(op_name: str) -> bool:
                op_u = (op_name or "").strip().upper()
                return op_u in {
                    "COMPRA DE MERCADORIA PARA REVENDA",
                    "COMISSÃO DE VENDA",
                    "COMISSAO DE VENDA",
                }

            def _group_key(r: Dict[str, Any]) -> str:
                if agrupar_por == "centro":
                    cc = (r.get("descricao_centro_custo_documento") or "").strip()
                    cod = r.get("codigo_centro_custo_documento")
                    cod_s = str(cod).strip() if cod is not None else ""
                    if cc and cod_s:
                        return f"{cc} | {cod_s}"
                    return cc or (cod_s or "—")
                if agrupar_por == "empresa":
                    return (r.get("empresa_vendedora") or "—").strip() or "—"
                if agrupar_por == "operacao":
                    return _op_base(r.get("descricao_tipo_operacao_documento"))
                # default: cliente
                return (r.get("cliente") or "—").strip() or "—"

            # Agregar líquido por grupo (venda - devolução), excluindo DOC/ICMS e operações excluídas.
            grupos: Dict[str, Dict[str, Any]] = {}
            for r in rows:
                if not isinstance(r, dict):
                    continue
                op = _op_base(r.get("descricao_tipo_operacao_documento"))
                op_u = op.strip().upper()
                if op_u == "ICMS":
                    continue
                if _is_excluded_op(op):
                    continue

                val = 0.0
                try:
                    val = float(r.get("total_nf")) if r.get("total_nf") is not None else 0.0
                except Exception:
                    val = 0.0

                k = _group_key(r)
                if k not in grupos:
                    grupos[k] = {"key": k, "vendas": 0.0, "devolucoes": 0.0, "liquido": 0.0, "docs": 0}
                grupos[k]["docs"] += 1
                if _is_devolucao_op(op):
                    grupos[k]["devolucoes"] += abs(val)
                else:
                    grupos[k]["vendas"] += val

            for g in grupos.values():
                g["liquido"] = float(g.get("vendas", 0.0)) - float(g.get("devolucoes", 0.0))

            itens = list(grupos.values())
            # ABC usual: usa participação no total positivo (se total <= 0, não faz sentido)
            total_liquido_positivo = sum(max(0.0, float(x.get("liquido", 0.0))) for x in itens)
            if total_liquido_positivo <= 0:
                return {
                    "sucesso": True,
                    "resposta": "ℹ️ Não há total líquido positivo suficiente para calcular Curva ABC neste relatório (após exclusões).",
                    "dados": [],
                    "meta": {"base_report_id": relatorio_base_id, "agrupar_por": agrupar_por},
                }

            # Filtro min_total (aplica no líquido positivo)
            if min_total is not None:
                try:
                    mt = float(min_total)
                    itens = [x for x in itens if float(x.get("liquido", 0.0)) >= mt]
                except Exception:
                    pass

            itens.sort(key=lambda x: float(x.get("liquido", 0.0)), reverse=True)

            # Montar classificação ABC
            acumulado = 0.0
            linhas = []
            for i, x in enumerate(itens, start=1):
                liquido = float(x.get("liquido", 0.0))
                contrib = max(0.0, liquido)
                acumulado += contrib
                pct = (contrib / total_liquido_positivo) if total_liquido_positivo else 0.0
                pct_acum = (acumulado / total_liquido_positivo) if total_liquido_positivo else 0.0
                if pct_acum <= a_pct:
                    cls = "A"
                elif pct_acum <= b_pct:
                    cls = "B"
                else:
                    cls = "C"
                linhas.append(
                    {
                        "rank": i,
                        "grupo": x.get("key"),
                        "vendas": float(x.get("vendas", 0.0)),
                        "devolucoes": float(x.get("devolucoes", 0.0)),
                        "liquido": liquido,
                        "pct": pct,
                        "pct_acum": pct_acum,
                        "classe": cls,
                        "docs": int(x.get("docs", 0)),
                    }
                )

            # Cortar output (mantém dados completos no retorno)
            top_linhas = linhas[:top]
            resto = linhas[top:]

            inicio_r = query_meta.get("inicio") or ""
            fim_r = query_meta.get("fim") or ""
            termo_r = query_meta.get("termo")

            titulo = "📊 **Curva ABC — Vendas (Make/Spalla)**\n\n"
            if relatorio_base_id:
                titulo += f"Base: `{relatorio_base_id}`\n"
            if inicio_r or fim_r:
                titulo += f"Período: **{inicio_r}** até **{fim_r}** (fim exclusivo)\n"
            if termo_r:
                titulo += f"Termo original: **{termo_r}**\n"
            titulo += f"Agrupar por: **{agrupar_por}**\n"
            titulo += f"Total líquido (base ABC, somente positivo): **{_fmt_brl(total_liquido_positivo)}**\n"
            titulo += f"Cortes: A até **{int(a_pct*100)}%**, B até **{int(b_pct*100)}%**, C restante\n\n"

            out = titulo
            out += "rank | grupo | líquido | % | % acum | classe | docs\n"
            out += "---|---|---:|---:|---:|:---:|---:\n"
            for r in top_linhas:
                out += (
                    f"{r['rank']} | {r['grupo']} | { _fmt_brl(r['liquido']) } | "
                    f"{r['pct']*100:,.1f}% | {r['pct_acum']*100:,.1f}% | {r['classe']} | {r['docs']}\n"
                ).replace(",", "X").replace(".", ",").replace("X", ".")

            if incluir_outros and resto:
                # Agrupar "resto" como OUTROS
                outros_liq_pos = sum(max(0.0, float(r.get("liquido", 0.0))) for r in resto)
                outros_pct = outros_liq_pos / total_liquido_positivo if total_liquido_positivo else 0.0
                out += f"\nOutros ({len(resto)}): **{_fmt_brl(outros_liq_pos)}** ({outros_pct*100:,.1f}%)\n".replace(
                    ",", "X"
                ).replace(".", ",").replace("X", ".")
            elif resto:
                out += f"\n⚠️ Mostrando top {top} de {len(linhas)} grupos.\n"

            return {
                "sucesso": True,
                "resposta": out.strip(),
                "dados": linhas,
                "meta": {
                    "base_report_id": relatorio_base_id,
                    "agrupar_por": agrupar_por,
                    "a_pct": a_pct,
                    "b_pct": b_pct,
                    "total_liquido_positivo": total_liquido_positivo,
                    "total_grupos": len(linhas),
                },
            }
        except Exception as e:
            logger.error(f"❌ Erro em curva_abc_vendas: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "resposta": f"❌ Erro ao gerar Curva ABC: {str(e)}"}

