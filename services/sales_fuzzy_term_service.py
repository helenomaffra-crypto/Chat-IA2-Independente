"""
SalesFuzzyTermService: normalização "cirúrgica" de termo de vendas.

Objetivo:
- Evitar manutenção infinita de regex/dicionários de typos ("hakvision", "hikvison", etc.)
- Usar IA apenas quando necessário: quando a consulta por vendas retorna 0 linhas.

Backend:
- Opcional: LangChain (langchain-openai) via env SALES_FUZZY_TERM_BACKEND=langchain
- Fallback: AIService (openai) já existente no projeto
- Fallback final: retorna o termo original
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "Você é um normalizador de termos de busca para vendas (Make/Spalla).\n"
    "Tarefa: dado um termo digitado pelo usuário (com possíveis erros), sugerir o termo correto.\n"
    "\n"
    "REGRAS:\n"
    "- Responda APENAS com JSON válido (um único objeto). Sem texto extra.\n"
    "- Não invente filtros; apenas sugira termo(s) plausíveis.\n"
    "- Se o termo já parece correto, retorne o mesmo.\n"
    "- Evite devolver mês/ano no termo.\n"
    "\n"
    "FORMATO:\n"
    "{\n"
    '  "termo_principal": "<string>",\n'
    '  "alternativas": ["<string>", ...]\n'
    "}\n"
    "\n"
    "Exemplos:\n"
    "- hakvision -> termo_principal=hikvision, alternativas=[hikvison]\n"
    "- hikvision -> termo_principal=hikvision, alternativas=[hikvison]\n"
    "- rastreado -> termo_principal=rastreador, alternativas=[]\n"
)


def _ensure_openai_api_key_for_langchain() -> None:
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
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s).strip()
        s = re.sub(r"\s*```$", "", s).strip()
    m = re.search(r"\{[\s\S]*\}", s)
    if m:
        s = m.group(0)
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else None
    except Exception:
        return None


def _clean_term(termo: str) -> str:
    t = (termo or "").strip()
    # remover pedaços típicos de período
    t = re.sub(
        r"\b("
        r"janeiro|jan|fevereiro|fev|mar[cç]o|mar|abril|abr|maio|mai|junho|jun|julho|jul|"
        r"agosto|ago|setembro|set|outubro|out|novembro|nov|dezembro|dez"
        r")\b(?:\s+de)?\s*(?:/|\s)\s*\d{2,4}\b",
        " ",
        t,
        flags=re.IGNORECASE,
    ).strip()
    t = re.sub(r"\b(0?[1-9]|1[0-2])\s*/\s*\d{2,4}\b", " ", t).strip()
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


class SalesFuzzyTermService:
    @staticmethod
    def sugerir(termo: str) -> Dict[str, Any]:
        termo = _clean_term(termo)
        if not termo:
            return {"termo_principal": "", "alternativas": []}

        # feature flag
        if os.getenv("SALES_FUZZY_TERM_ENABLED", "true").strip().lower() in {"0", "false", "no"}:
            return {"termo_principal": termo, "alternativas": []}

        backend = os.getenv("SALES_FUZZY_TERM_BACKEND", "native").strip().lower()

        # 1) LangChain (opcional)
        if backend == "langchain":
            try:
                _ensure_openai_api_key_for_langchain()
                from langchain_openai import ChatOpenAI  # type: ignore
                from langchain_core.prompts import ChatPromptTemplate  # type: ignore

                model = os.getenv("SALES_FUZZY_TERM_MODEL") or os.getenv("OPENAI_MODEL_ANALITICO") or "gpt-4o-mini"
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", _SYSTEM_PROMPT),
                        ("human", "Termo do usuário: {termo}"),
                    ]
                )
                llm = ChatOpenAI(model=model, temperature=0, model_kwargs={"response_format": {"type": "json_object"}})
                msg = (prompt | llm).invoke({"termo": termo})
                texto = getattr(msg, "content", None) or str(msg)
                parsed = _safe_json_loads(texto) or {}
                return {
                    "termo_principal": str(parsed.get("termo_principal") or termo).strip(),
                    "alternativas": [str(x).strip() for x in (parsed.get("alternativas") or []) if str(x).strip()],
                }
            except Exception as e:
                logger.info(f"[SALES_FUZZY_TERM] LangChain indisponível/erro: {e}")

        # 2) AIService (fallback)
        try:
            from ai_service import get_ai_service

            ai = get_ai_service()
            if ai and getattr(ai, "enabled", False):
                model = os.getenv("SALES_FUZZY_TERM_MODEL") or os.getenv("OPENAI_MODEL_ANALITICO") or None
                resp = ai._call_llm_api(
                    prompt=f"Termo do usuário: {termo}",
                    system_prompt=_SYSTEM_PROMPT,
                    tools=None,
                    model=model,
                    temperature=0.0,
                )
                parsed = _safe_json_loads(resp if isinstance(resp, str) else str(resp)) or {}
                return {
                    "termo_principal": str(parsed.get("termo_principal") or termo).strip(),
                    "alternativas": [str(x).strip() for x in (parsed.get("alternativas") or []) if str(x).strip()],
                }
        except Exception as e:
            logger.info(f"[SALES_FUZZY_TERM] AIService indisponível/erro: {e}")

        # 3) Fallback final
        return {"termo_principal": termo, "alternativas": []}

