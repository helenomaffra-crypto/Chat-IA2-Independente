"""Serviços analíticos determinísticos (BI leve) para o mAIke.

Primeira implementação: chegadas (ETA) agrupadas por categoria.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from db_manager import listar_processos_por_eta

logger = logging.getLogger(__name__)


def obter_chegadas_agrupadas_por_categoria(
    filtro_data: str = "semana",
    data_especifica: Optional[str] = None,
    categoria: Optional[str] = None,
    limite: int = 500,
    incluir_passado: bool = False,
) -> Dict[str, Any]:
    """Busca processos por ETA e agrupa por categoria.

    Retorna estrutura determinística, sem formatação de texto, para a IA só
    transformar em resposta.
    """
    try:
        processos = listar_processos_por_eta(
            filtro_data=filtro_data,
            data_especifica=data_especifica,
            categoria=categoria.upper() if categoria else None,
            limit=limite,
            incluir_passado=incluir_passado,
        )
    except Exception as e:
        logger.error(f"[ANALYTICS] Erro ao listar processos por ETA: {e}", exc_info=True)
        return {
            "sucesso": False,
            "erro": "ERRO_LISTAR_PROCESSOS_POR_ETA",
            "mensagem": str(e),
        }

    agrupado: Dict[str, Dict[str, Any]] = {}
    total = 0

    for proc in processos:
        categoria_proc = proc.get("processo_referencia", "???")[:3].upper()
        if not categoria_proc or len(categoria_proc) < 2:
            categoria_proc = "OUTROS"

        grupo = agrupado.setdefault(
            categoria_proc,
            {"categoria": categoria_proc, "quantidade": 0, "processos": []},
        )
        grupo["quantidade"] += 1
        grupo["processos"].append(proc)
        total += 1

    return {
        "sucesso": True,
        "total_processos": total,
        "total_categorias": len(agrupado),
        "por_categoria": sorted(
            agrupado.values(), key=lambda g: g["quantidade"], reverse=True
        ),
    }


def formatar_resumo_chegadas_agrupadas_por_categoria(
    dados: Dict[str, Any],
    descricao_periodo: str,
) -> str:
    """Formata um resumo legível das chegadas agrupadas por categoria."""
    if not dados.get("sucesso"):
        return (
            "❌ Erro ao obter dados analíticos de chegadas por categoria: "
            + dados.get("mensagem", "erro desconhecido")
        )

    total = dados.get("total_processos", 0)
    grupos: List[Dict[str, Any]] = dados.get("por_categoria", [])

    if total == 0 or not grupos:
        return (
            f"✅ Nenhum processo com ETA {descricao_periodo}.\n\n"
            "💡 Dica: verifique se há processos no Kanban com ETA preenchido para este período."
        )

    linhas: List[str] = []
    linhas.append(
        f"📊 **Processos que chegam {descricao_periodo}, agrupados por categoria** "
        f"({total} processo(s) em {len(grupos)} categoria(s))\n"
    )

    for grupo in grupos:
        cat = grupo.get("categoria", "?")
        qtd = grupo.get("quantidade", 0)
        linhas.append(f"\n### {cat} — {qtd} processo(s)")

        # Mostrar no máximo alguns exemplos por categoria
        exemplos: List[Dict[str, Any]] = grupo.get("processos", [])[:5]
        for proc in exemplos:
            ref = proc.get("processo_referencia", "?")
            shipsgo = proc.get("shipsgo") or {}
            eta = shipsgo.get("shipsgo_eta") or "ETA não informada"
            porto_nome = shipsgo.get("shipsgo_porto_nome") or shipsgo.get(
                "shipsgo_porto_codigo", ""
            )
            if porto_nome:
                linhas.append(f"- **{ref}** — ETA: {eta} — Porto: {porto_nome}")
            else:
                linhas.append(f"- **{ref}** — ETA: {eta}")

    return "\n".join(linhas)













