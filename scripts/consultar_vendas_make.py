"""
Consulta vendas no SQL Server (Make/Spalla) e imprime resumo por período.

Uso (exemplo):
  docker compose exec web python3 scripts/consultar_vendas_make.py --inicio 2025-01-01 --fim 2025-02-01
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Garantir imports quando rodar via Docker (/app/scripts -> adicionar /app)
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from utils.sql_server_adapter import get_sql_adapter


def _print_rows(title: str, rows: List[Dict[str, Any]], limit: int) -> None:
    print("")
    print(title)
    if not rows:
        print("(sem resultados)")
        return

    keys = list(rows[0].keys())
    print("\t".join(keys))
    for row in rows[:limit]:
        print("\t".join("" if row.get(k) is None else str(row.get(k)) for k in keys))


def _run_query(sql: str, database: Optional[str]) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    adapter = get_sql_adapter()
    if not adapter:
        return None, "SQL adapter indisponível (pyodbc/node não encontrados)."
    result = adapter.execute_query(sql, database=database) if database else adapter.execute_query(sql)
    if not result.get("success"):
        return None, result.get("error") or "erro_desconhecido"
    data = result.get("data") or []
    if isinstance(data, list):
        return data, None
    # alguns adapters podem retornar dict; normalizar em lista 1 item
    if isinstance(data, dict):
        return [data], None
    return [{"value": data}], None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", required=True, help="YYYY-MM-DD (inclusivo)")
    parser.add_argument("--fim", required=True, help="YYYY-MM-DD (exclusivo)")
    parser.add_argument("--db", default="Make", help="Database padrão do adapter (default: Make)")
    parser.add_argument("--top", type=int, default=30, help="Limite de linhas a imprimir")
    parser.add_argument(
        "--like",
        default="VENDA,FATUR,NF",
        help="Filtros LIKE para venda (separados por vírgula). Ex: VENDA,FATUR,NF",
    )
    args = parser.parse_args(argv)

    dt_ini = args.inicio
    dt_fim = args.fim
    top = int(args.top)
    database = args.db.strip() or None
    like_terms = [t.strip() for t in (args.like or "").split(",") if t.strip()]

    # 1) Quais tipos de operação aparecem no período (para você decidir o que é VENDA)
    q1 = f"""
SELECT TOP {top}
    FORMAT(CONVERT(date, d.data_emissao), 'yyyy-MM') AS periodo,
    d.tipo_movimento AS tipo_movimento_documento,
    tds.TD_DES AS descricao_tipo_operacao_documento,
    SUM(CAST(d.valor_documento AS decimal(18,2))) AS total_valor_documento,
    COUNT(1) AS qtd_documentos
FROM spalla.dbo.documentos d
JOIN Make.dbo.TIPOS_DOCUMENTO_SPALLA tds
    ON tds.TD_COD = d.codigo_tipo_documento
WHERE d.data_emissao >= '{dt_ini}'
  AND d.data_emissao <  '{dt_fim}'
GROUP BY
    FORMAT(CONVERT(date, d.data_emissao), 'yyyy-MM'),
    d.tipo_movimento,
    tds.TD_DES
ORDER BY total_valor_documento DESC;
""".strip()

    rows1, err1 = _run_query(q1, database)
    if err1:
        # fallback: tentar sem db explícito (alguns ambientes têm SQL_DATABASE diferente no .env)
        rows1, err1 = _run_query(q1, None)
    if err1:
        print("ERRO:", err1)
        return 2

    _print_rows("=== JANEIRO (período) - TOP tipos de operação (TD_DES) por total ===", rows1 or [], top)

    # 2) Break-down por centro de custo + % no mês (heurística: LIKE)
    def _escape_sql_like_term(term: str) -> str:
        # escape básico para string literal SQL
        return (term or "").replace("'", "''")

    like_where = " OR ".join([f"tds.TD_DES LIKE '%{_escape_sql_like_term(t)}%'" for t in like_terms]) or "1=0"
    q2 = f"""
WITH base AS (
    SELECT
        FORMAT(CONVERT(date, d.data_emissao), 'yyyy-MM') AS periodo,
        d.tipo_movimento AS tipo_movimento_documento,
        tds.TD_DES AS descricao_tipo_operacao_documento,
        d.codigo_setor AS codigo_centro_custo_documento,
        cc.descricao_centro_custo AS descricao_centro_custo_documento,
        CAST(d.valor_documento AS decimal(18,2)) AS valor_documento
    FROM spalla.dbo.documentos d
    JOIN Make.dbo.TIPOS_DOCUMENTO_SPALLA tds
        ON tds.TD_COD = d.codigo_tipo_documento
    LEFT JOIN spalla.dbo.centro_custo cc
        ON cc.codigo_centro_custo = d.codigo_setor
    WHERE d.data_emissao >= '{dt_ini}'
      AND d.data_emissao <  '{dt_fim}'
      AND ({like_where})
),
agg AS (
    SELECT
        periodo,
        tipo_movimento_documento,
        descricao_tipo_operacao_documento,
        codigo_centro_custo_documento,
        descricao_centro_custo_documento,
        SUM(valor_documento) AS total_valor
    FROM base
    GROUP BY
        periodo,
        tipo_movimento_documento,
        descricao_tipo_operacao_documento,
        codigo_centro_custo_documento,
        descricao_centro_custo_documento
)
SELECT TOP {top}
    a.*,
    CAST(100.0 * a.total_valor / NULLIF(SUM(a.total_valor) OVER (PARTITION BY a.periodo), 0) AS decimal(9,2)) AS pct_no_mes
FROM agg a
ORDER BY a.total_valor DESC;
""".strip()

    rows2, err2 = _run_query(q2, database)
    if err2:
        rows2, err2 = _run_query(q2, None)

    if err2:
        print("")
        print("=== Break-down por centro de custo (LIKE) ===")
        print("ERRO:", err2)
        return 0

    _print_rows("=== Break-down por centro de custo (LIKE venda/fatur/nf) ===", rows2 or [], top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

