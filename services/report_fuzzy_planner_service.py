"""
ReportFuzzyPlannerService: interpreta pedidos "fuzzy" de filtro/agrupamento para relatórios.

Escopo (V1):
- Apenas relatórios (REPORT_META / report_service)
- Saída sempre estruturada para aplicação determinística (sem regex no core)

Backend:
- Opcional: LangChain (se instalado) via env REPORT_FUZZY_PLANNER_BACKEND=langchain
- Fallback: AIService (openai) já existente no projeto
- Fallback final: heurística simples (quando IA estiver desabilitada)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_PLANNER_SYSTEM_PROMPT = (
    "Você é um PLANNER de filtros para relatórios do mAIke.\n"
    "\n"
    "Tarefa: converter o pedido do usuário em um PLANO ESTRUTURADO.\n"
    "\n"
    "REGRAS:\n"
    "- Responda APENAS com JSON válido (um único objeto). Sem texto extra.\n"
    "- NÃO resuma o relatório e NÃO invente dados.\n"
    "- Use `report_meta.secoes` (se existir) para escolher uma `secao` válida.\n"
    "- Se o pedido for claramente por CATEGORIA (ex.: 'filtre DMD', 'só GLT'), use `filtrar_categoria`.\n"
    "- Se o pedido for por UMA SEÇÃO (ex.: 'mostra pendências', 'só DIs'), use `buscar_secao`.\n"
    "- Se o pedido for para AGRUPAR (ex.: 'agrupe por canal'), use `agrupar_por_canal`.\n"
    "\n"
    "AÇÕES VÁLIDAS (`acao`):\n"
    "- filtrar_categoria\n"
    "- buscar_secao\n"
    "- agrupar_por_canal\n"
    "\n"
    "CAMPOS POSSÍVEIS:\n"
    "- categoria: string (ex.: 'DMD')\n"
    "- secao: string (ex.: 'dis_analise', 'duimps_analise', 'pendencias', 'eta_alterado', 'alertas')\n"
    "- canal: 'Verde' | 'Vermelho'\n"
    "- status_contains: string (substring)\n"
    "- min_age_dias: int\n"
    "- tipo_pendencia: 'Frete' | 'ICMS' | 'AFRMM' | 'LPCO' | 'Bloqueio CE'\n"
    "- tipo_mudanca: 'ATRASO' | 'ADIANTADO'\n"
    "- min_dias: int\n"
    "- tipo_relatorio: string (opcional; use se o usuário mencionar 'fechamento' ou 'o que temos')\n"
    "\n"
    "EXEMPLOS:\n"
    "- Pedido: 'filtre DMD' -> {\"acao\":\"filtrar_categoria\",\"categoria\":\"DMD\"}\n"
    "- Pedido: 'só canal verde' -> {\"acao\":\"buscar_secao\",\"secao\":\"dis_analise\",\"canal\":\"Verde\"}\n"
    "- Pedido: 'pendências de frete' -> {\"acao\":\"buscar_secao\",\"secao\":\"pendencias\",\"tipo_pendencia\":\"Frete\"}\n"
    "- Pedido: 'agrupe por canal' -> {\"acao\":\"agrupar_por_canal\"}\n"
)

def _ensure_openai_api_key_for_langchain() -> None:
    """
    LangChain (langchain-openai) por padrão lê OPENAI_API_KEY.
    No projeto, a chave costuma estar em DUIMP_AI_API_KEY.
    """
    if os.getenv("OPENAI_API_KEY"):
        return
    key = os.getenv("DUIMP_AI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if key:
        os.environ["OPENAI_API_KEY"] = key


def _safe_json_loads(texto: str) -> Optional[Dict[str, Any]]:
    if not texto or not isinstance(texto, str):
        return None
    s = texto.strip()
    if not s:
        return None
    # Remover fences
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s).strip()
        s = re.sub(r"\s*```$", "", s).strip()
    # Tentar extrair o primeiro objeto JSON
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        s = m.group(0)
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else None
    except Exception:
        return None


def _log_preview(prefix: str, texto: Any, *, limit: int = 240) -> None:
    """
    Loga um preview curto (sem vazar conteúdo grande).
    """
    try:
        s = texto if isinstance(texto, str) else str(texto)
        s = s.replace("\n", "\\n")
        logger.info(f"{prefix}: {s[:limit]}{'…' if len(s) > limit else ''}")
    except Exception:
        return


def _normalizar_plano(plano: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normaliza chaves comuns que modelos podem variar (ex.: action vs acao).
    Mantém compatibilidade sem depender de regex.
    """
    if not plano or not isinstance(plano, dict):
        return None

    VALID_ACOES = {
        "filtrar_categoria",
        "buscar_secao",
        "agrupar_por_canal",
    }

    # Alias: action -> acao
    if "acao" not in plano and "action" in plano:
        plano["acao"] = plano.get("action")

    # Alias: section -> secao
    if "secao" not in plano and "section" in plano:
        plano["secao"] = plano.get("section")

    # Alias: reportId -> report_id
    if "report_id" not in plano and "reportId" in plano:
        plano["report_id"] = plano.get("reportId")

    # ✅ Suportar formato alternativo: {"filtrar_categoria": {"categoria": "DMD"}}
    # Alguns modelos devolvem "acao" como chave do objeto (em vez de campo).
    if "acao" not in plano:
        for k, v in list(plano.items()):
            if k in VALID_ACOES and isinstance(v, dict):
                normalized = dict(v)
                normalized["acao"] = k
                return normalized

    # Normalizações adicionais (best-effort)
    if isinstance(plano.get("categoria"), str):
        plano["categoria"] = plano["categoria"].strip().upper()

    return plano


def _heuristica_minima(instrucao: str) -> Dict[str, Any]:
    """
    Heurística simples apenas para não ficar sem resposta quando IA está desabilitada.
    (Mantemos escopo mínimo; o objetivo é depender do planner via IA.)
    """
    txt = (instrucao or "").strip().lower()
    plan: Dict[str, Any] = {"acao": "buscar_secao"}

    # categoria (AAA.0001/26 ou "DMD")
    mcat = re.search(r"\b([A-Z]{2,5})\b", instrucao or "")
    if mcat:
        cat = mcat.group(1).upper()
        # evitar palavras comuns
        if cat not in {"MAIKE", "HOJE"}:
            plan["categoria"] = cat
            plan["acao"] = "filtrar_categoria"

    if "canal verde" in txt:
        plan["canal"] = "Verde"
    if "canal vermelho" in txt:
        plan["canal"] = "Vermelho"

    if "pend" in txt:
        plan["secao"] = "pendencias"
        plan["acao"] = "buscar_secao"
        for tipo in ("frete", "icms", "afrmm", "lpco", "bloqueio ce"):
            if tipo in txt:
                plan["tipo_pendencia"] = (
                    "Bloqueio CE" if tipo == "bloqueio ce" else tipo.upper()
                ).title() if tipo not in ("icms", "afrmm", "lpco") else tipo.upper()
                break

    if "eta" in txt and ("atras" in txt or "adiant" in txt):
        plan["secao"] = "eta_alterado"
        plan["acao"] = "buscar_secao"
        if "atras" in txt:
            plan["tipo_mudanca"] = "ATRASO"
        elif "adiant" in txt:
            plan["tipo_mudanca"] = "ADIANTADO"
        md = re.search(r"\b(\d{1,3})\s*(dia|dias)\b", txt)
        if md:
            try:
                plan["min_dias"] = int(md.group(1))
            except Exception:
                pass

    if "agru" in txt and "canal" in txt:
        plan = {"acao": "agrupar_por_canal"}

    return plan


def planejar_filtro(
    *,
    instrucao: str,
    report_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Retorna um plano estruturado.

    Formato esperado:
    - {"acao":"filtrar_categoria","categoria":"DMD"}
    - {"acao":"buscar_secao","secao":"dis_analise","canal":"Verde","status_contains":"desembara"}
    - {"acao":"agrupar_por_canal","secao":"dis_analise"}  (secao opcional)
    """
    instrucao = (instrucao or "").strip()
    if not instrucao:
        return {"acao": "erro", "motivo": "instrucao_vazia"}

    backend = os.getenv("REPORT_FUZZY_PLANNER_BACKEND", "native").strip().lower()
    logger.info(f"[REPORT_FUZZY_PLANNER] backend={backend}")

    # 1) Tentar LangChain (opcional)
    if backend == "langchain":
        try:
            _ensure_openai_api_key_for_langchain()
            # Importar apenas se existir no ambiente (não adicionamos dependência aqui).
            from langchain_openai import ChatOpenAI  # type: ignore
            from langchain_core.prompts import ChatPromptTemplate  # type: ignore

            model = os.getenv("REPORT_FUZZY_PLANNER_MODEL") or os.getenv("OPENAI_MODEL_ANALITICO") or "gpt-4o-mini"

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        _PLANNER_SYSTEM_PROMPT,
                    ),
                    ("human", "REPORT_META (se houver): {report_meta}\n\nPedido: {instrucao}"),
                ]
            )

            # ✅ Forçar JSON no OpenAI (evita respostas com texto solto)
            # langchain-openai suporta `model_kwargs` para passar parâmetros do provider.
            llm = ChatOpenAI(
                model=model,
                temperature=0,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
            msg = (prompt | llm).invoke({"instrucao": instrucao, "report_meta": report_meta or {}})
            texto = getattr(msg, "content", None) or str(msg)
            parsed = _normalizar_plano(_safe_json_loads(texto))
            if parsed and isinstance(parsed, dict) and parsed.get("acao"):
                logger.info("[REPORT_FUZZY_PLANNER] ✅ plano gerado via LangChain")
                return parsed
            logger.info("[REPORT_FUZZY_PLANNER] ⚠️ LangChain respondeu sem JSON válido; caindo para fallback")
            _log_preview("[REPORT_FUZZY_PLANNER] (preview langchain)", texto)
        except Exception as e:
            logger.warning(f"[REPORT_FUZZY_PLANNER] ⚠️ LangChain indisponível/erro: {e}")
            logger.info("[REPORT_FUZZY_PLANNER] ℹ️ caindo para fallback (AIService/heurística)")

    # 2) Fallback: AIService já existente (OpenAI via projeto)
    try:
        from ai_service import get_ai_service

        ai = get_ai_service()
        if ai and getattr(ai, "enabled", False):
            system_prompt = _PLANNER_SYSTEM_PROMPT
            prompt = f"REPORT_META (se houver): {json.dumps(report_meta or {}, ensure_ascii=False)}\n\nPedido: {instrucao}"
            model = os.getenv("REPORT_FUZZY_PLANNER_MODEL") or os.getenv("OPENAI_MODEL_ANALITICO") or None
            resp = ai._call_llm_api(prompt=prompt, system_prompt=system_prompt, tools=None, model=model, temperature=0.0)
            parsed = _normalizar_plano(_safe_json_loads(resp if isinstance(resp, str) else str(resp)))
            if parsed and parsed.get("acao"):
                logger.info("[REPORT_FUZZY_PLANNER] ✅ plano gerado via AIService")
                return parsed
            logger.info("[REPORT_FUZZY_PLANNER] ⚠️ AIService respondeu sem JSON válido; caindo para heurística")
            _log_preview("[REPORT_FUZZY_PLANNER] (preview aiservice)", resp)
    except Exception as e:
        logger.warning(f"[REPORT_FUZZY_PLANNER] ⚠️ AIService falhou: {e}")

    # 3) Heurística mínima
    logger.info("[REPORT_FUZZY_PLANNER] ℹ️ usando heurística mínima (IA indisponível)")
    return _heuristica_minima(instrucao)

