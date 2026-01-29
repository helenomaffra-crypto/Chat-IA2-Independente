"""
ReportGroupingService: agrupamentos determinísticos para relatórios JSON.

Objetivo: permitir "agrupe por canal" (e similares) sem regex e sem nova consulta.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _norm_str(v: Any) -> str:
    return str(v).strip().lower() if v is not None else ""


def agrupar_lista_por_chave(
    itens: Any,
    *,
    chave: str,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, int]]:
    """
    Agrupa uma lista de dicts por uma chave.

    Returns:
        (grupos, counts)
    """
    if not isinstance(itens, list):
        return {}, {}

    grupos: Dict[str, List[Dict[str, Any]]] = {}
    for it in itens:
        if not isinstance(it, dict):
            continue
        key = _norm_str(it.get(chave))
        if not key:
            key = "(sem)"
        grupos.setdefault(key, []).append(it)

    counts = {k: len(v) for k, v in grupos.items()}
    return grupos, counts


def formatar_grupos_simples(
    titulo: str,
    grupos: Dict[str, List[Dict[str, Any]]],
    *,
    mostrar_max_por_grupo: int = 50,
) -> str:
    """
    Formatação simples em markdown para grupos.
    """
    titulo = (titulo or "").strip()
    linhas: List[str] = []
    if titulo:
        linhas.append(f"📊 **{titulo}**\n")

    if not grupos:
        linhas.append("✅ Nenhum item para agrupar.\n")
        return "\n".join(linhas).strip()

    # Ordenar por tamanho desc, depois nome asc
    ordenado = sorted(grupos.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    for k, itens in ordenado:
        header = k.upper() if k not in ("(sem)",) else k
        linhas.append(f"**{header}** ({len(itens)})")
        for it in itens[: max(0, int(mostrar_max_por_grupo))]:
            proc = (it.get("processo_referencia") or it.get("processo") or "").strip()
            status = (it.get("situacao_di") or it.get("status") or it.get("situacao") or "").strip()
            extra = (it.get("numero_di") or it.get("numero") or it.get("numero_duimp") or "").strip()
            linha = "•"
            if proc:
                linha += f" **{proc}**"
            if extra:
                linha += f" ({extra})"
            if status:
                linha += f" — {status}"
            linhas.append(linha)
        if len(itens) > mostrar_max_por_grupo:
            linhas.append(f"… (+{len(itens) - mostrar_max_por_grupo})")
        linhas.append("")  # spacer

    return "\n".join(linhas).strip()

