"""
ReportNormalizationService: normalização de relatórios JSON (REPORT_META / dados_json).

Objetivo:
- Garantir consistência de chaves para filtros/agrupamentos determinísticos
- Evitar regex e “fallbacks” frágeis em follow-ups

Regra principal (pedido do usuário):
- Todo item (dict) em qualquer seção deve ter:
  - `processo_referencia`
  - `categoria`
Mesmo que o item original venha heterogêneo (ex.: `processo`, `referencia`, etc.).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


_PROC_REF_KEYS = (
    "processo_referencia",
    "processoReferencia",
    "processo_ref",
    "processo",
    "referencia",
    "ref",
    "processoRef",
)

_CATEGORIA_KEYS = (
    "categoria",
    "cliente_categoria",
    "sigla",
    "grupo",
)


def _to_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        return s or None
    try:
        s = str(v).strip()
        return s or None
    except Exception:
        return None


def _infer_categoria_from_processo_referencia(processo_referencia: Optional[str]) -> Optional[str]:
    """
    Infere categoria a partir do prefixo de `AAA.0001/26`.
    Aceita também formatos tipo `AAA0001/26` (best-effort).
    """
    pr = _to_str(processo_referencia)
    if not pr:
        return None

    # Formato clássico: DMD.0001/26
    if "." in pr:
        prefix = pr.split(".", 1)[0].strip().upper()
        if prefix and 2 <= len(prefix) <= 6 and re.fullmatch(r"[A-Z0-9]+", prefix):
            return prefix

    # Formato alternativo: DMD0001/26
    m = re.match(r"^\s*([A-Z]{2,6})\d{2,6}/\d{2,4}\s*$", pr.upper())
    if m:
        return m.group(1)

    return None


def _extract_processo_referencia(item: Dict[str, Any]) -> Optional[str]:
    for k in _PROC_REF_KEYS:
        v = item.get(k)
        s = _to_str(v)
        if s:
            return s

    # Às vezes vem como dict aninhado
    proc = item.get("processo")
    if isinstance(proc, dict):
        for k in _PROC_REF_KEYS:
            v = proc.get(k)
            s = _to_str(v)
            if s:
                return s

    return None


def _extract_categoria(item: Dict[str, Any]) -> Optional[str]:
    for k in _CATEGORIA_KEYS:
        v = item.get(k)
        s = _to_str(v)
        if s:
            return s.upper()
    return None


def _normalize_item(
    item: Dict[str, Any],
    *,
    default_categoria: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Normaliza um item (dict) garantindo chaves `processo_referencia` e `categoria`.
    """
    pr = _extract_processo_referencia(item)
    cat = _extract_categoria(item)

    # Inferir categoria do processo, senão usar default (do relatório)
    if not cat:
        cat = _infer_categoria_from_processo_referencia(pr) or (_to_str(default_categoria) or None)
        if isinstance(cat, str):
            cat = cat.upper()

    # Garantir presença das chaves
    if "processo_referencia" not in item:
        item["processo_referencia"] = pr
    elif not _to_str(item.get("processo_referencia")) and pr:
        item["processo_referencia"] = pr

    if "categoria" not in item:
        item["categoria"] = cat
    elif not _to_str(item.get("categoria")) and cat:
        item["categoria"] = cat

    return item


def normalize_report_json(dados_json: Any) -> Any:
    """
    Normaliza `dados_json` (estrutura de relatório) de forma best-effort.
    Se não for dict, retorna como está.
    """
    if not isinstance(dados_json, dict):
        return dados_json

    # Categoria default (do relatório)
    default_categoria = _to_str(dados_json.get("categoria"))
    if isinstance(default_categoria, str):
        default_categoria = default_categoria.upper()

    secoes = dados_json.get("secoes")
    if isinstance(secoes, dict):
        for nome_secao, conteudo in list(secoes.items()):
            if isinstance(conteudo, list):
                novos: List[Any] = []
                for it in conteudo:
                    if isinstance(it, dict):
                        novos.append(_normalize_item(it, default_categoria=default_categoria))
                    else:
                        novos.append(it)
                secoes[nome_secao] = novos
            elif isinstance(conteudo, dict):
                # Caso raro: seção como dict de itens/agrupamentos - tentar normalizar valores que forem listas
                for k, v in list(conteudo.items()):
                    if isinstance(v, list):
                        nv: List[Any] = []
                        for it in v:
                            if isinstance(it, dict):
                                nv.append(_normalize_item(it, default_categoria=default_categoria))
                            else:
                                nv.append(it)
                        conteudo[k] = nv

    # Também normalizar listas diretas no topo (compat/legado)
    for k, v in list(dados_json.items()):
        if k == "secoes":
            continue
        if isinstance(v, list):
            nv2: List[Any] = []
            for it in v:
                if isinstance(it, dict):
                    nv2.append(_normalize_item(it, default_categoria=default_categoria))
                else:
                    nv2.append(it)
            dados_json[k] = nv2

    return dados_json

