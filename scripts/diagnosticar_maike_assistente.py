#!/usr/bin/env python3
"""
Diagnóstico do banco SQL Server `mAIke_assistente` para apoiar a transição
para "fonte da verdade".

Gera um relatório com:
- contagens por tabela
- perfil de nulos/vazios para colunas essenciais
- checagens de duplicidade por chaves naturais
- "top piores registros" (mais campos essenciais vazios)

Uso:
  python3 scripts/diagnosticar_maike_assistente.py
  python3 scripts/diagnosticar_maike_assistente.py --output docs/DIAGNOSTICO_MAIKE.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Adicionar raiz do projeto ao path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402


DB_NAME_DEFAULT = "mAIke_assistente"


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _md_escape(s: Any) -> str:
    if s is None:
        return ""
    text = str(s)
    return text.replace("|", "\\|")


def _as_int(v: Any) -> int:
    try:
        return int(v)
    except Exception:
        return 0


def _sql_identifier(name: str) -> str:
    # Identificadores simples (dbo.TABELA/coluna). Não aceitar lixo.
    safe = "".join(ch for ch in name if (ch.isalnum() or ch in "._[]"))
    return safe


def _sql_col_is_null_or_empty(col: str) -> str:
    c = _sql_identifier(col)
    # NVARCHAR/TEXT: tratar '' como vazio também
    return f"({c} IS NULL OR LTRIM(RTRIM(CAST({c} AS NVARCHAR(MAX)))) = '')"


def _exec(adapter, sql: str, database: str) -> Dict[str, Any]:
    return adapter.execute_query(sql, database=database)


def _fetch_rows(adapter, sql: str, database: str) -> List[Dict[str, Any]]:
    r = _exec(adapter, sql, database)
    if not r or not r.get("success"):
        return []
    data = r.get("data") or []
    # Adapter pode retornar lista de dicts (esperado)
    return data if isinstance(data, list) else []


def _fetch_scalar_int(adapter, sql: str, database: str, key: str = "total") -> int:
    rows = _fetch_rows(adapter, sql, database)
    if not rows:
        return 0
    return _as_int(rows[0].get(key))


@dataclass(frozen=True)
class TableCheck:
    table: str
    essential_columns: Tuple[str, ...]


@dataclass(frozen=True)
class DuplicateCheck:
    table: str
    key_columns: Tuple[str, ...]
    where_sql: Optional[str] = None


def _build_checks() -> Tuple[List[TableCheck], List[DuplicateCheck]]:
    table_checks: List[TableCheck] = [
        TableCheck(
            table="dbo.PROCESSO_IMPORTACAO",
            essential_columns=(
                "numero_processo",
                "id_importacao",
                "status_processo",
                "data_embarque",
                "data_chegada_prevista",
                "data_desembaraco",
                "atualizado_em|data_ultima_modificacao",
            ),
        ),
        TableCheck(
            table="dbo.DOCUMENTO_ADUANEIRO",
            essential_columns=(
                "numero_documento",
                "tipo_documento",
                "processo_referencia",
                "status_documento",
                "status_documento_codigo",
                "situacao_documento",
                "canal_documento",
                "data_registro",
                "data_situacao",
                "data_desembaraco",
                "json_dados_originais",
                "atualizado_em",
            ),
        ),
        TableCheck(
            table="dbo.HISTORICO_DOCUMENTO_ADUANEIRO",
            essential_columns=(
                "id_documento",
                "tipo_evento|tipo_mudanca",
                "campo_alterado",
                "valor_anterior",
                "valor_novo",
                "data_evento|data_mudanca",
                "fonte_dados",
            ),
        ),
        TableCheck(
            table="dbo.VALOR_MERCADORIA",
            essential_columns=(
                "processo_referencia",
                "numero_documento",
                "tipo_documento",
                "tipo_valor",
                "moeda",
                "valor",
                "atualizado_em",
            ),
        ),
        TableCheck(
            table="dbo.IMPOSTO_IMPORTACAO",
            essential_columns=(
                "processo_referencia",
                "numero_documento",
                "tipo_documento",
                "tipo_imposto",
                "valor_brl|valor",
                "valor_usd",
                "atualizado_em",
            ),
        ),
        TableCheck(
            table="dbo.MOVIMENTACAO_BANCARIA",
            essential_columns=(
                "id_movimentacao",
                "banco_origem",
                "data_movimentacao",
                "valor_movimentacao",
                "sinal_movimentacao",
                "descricao_movimentacao",
            ),
        ),
        TableCheck(
            table="dbo.LANCAMENTO_TIPO_DESPESA",
            essential_columns=(
                "id_movimentacao_bancaria|id_movimentacao",
                "id_tipo_despesa",
                "valor_despesa|valor_classificado",
                "criado_em|atualizado_em",
            ),
        ),
    ]

    duplicate_checks: List[DuplicateCheck] = [
        DuplicateCheck(
            table="dbo.DOCUMENTO_ADUANEIRO",
            key_columns=("tipo_documento", "numero_documento", "versao_documento"),
        ),
        DuplicateCheck(
            table="dbo.VALOR_MERCADORIA",
            key_columns=("processo_referencia", "numero_documento", "tipo_documento", "tipo_valor", "moeda"),
        ),
        DuplicateCheck(
            table="dbo.IMPOSTO_IMPORTACAO",
            key_columns=("processo_referencia", "numero_documento", "tipo_documento", "tipo_imposto", "numero_retificacao"),
        ),
        DuplicateCheck(
            table="dbo.PROCESSO_IMPORTACAO",
            key_columns=("numero_processo",),
        ),
    ]
    return table_checks, duplicate_checks


def _get_table_columns(adapter, database: str, table: str) -> List[str]:
    parts = table.split(".")
    if len(parts) == 2:
        schema, name = parts
    else:
        schema, name = "dbo", parts[-1]
    schema = schema.strip("[]")
    name = name.strip("[]")
    sql = f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{name}'
        ORDER BY ORDINAL_POSITION
    """
    rows = _fetch_rows(adapter, sql, database)
    return [r.get("COLUMN_NAME") for r in rows if isinstance(r, dict) and r.get("COLUMN_NAME")]


def _resolve_column_token(token: str, table_columns_set: set[str]) -> Optional[str]:
    """
    token pode ser "coluna" ou "alternativa1|alternativa2".
    Retorna o primeiro match exato (case-insensitive) existente na tabela.
    """
    options = [p.strip() for p in (token or "").split("|") if p.strip()]
    if not options:
        return None
    lower_map = {c.lower(): c for c in table_columns_set}
    for opt in options:
        hit = lower_map.get(opt.lower())
        if hit:
            return hit
    return None


def _table_exists(adapter, database: str, table: str) -> bool:
    # table: dbo.NOME
    parts = table.split(".")
    if len(parts) == 2:
        schema, name = parts
    else:
        schema, name = "dbo", parts[-1]
    schema = schema.strip("[]")
    name = name.strip("[]")
    sql = f"""
        SELECT COUNT(*) as total
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{name}'
    """
    return _fetch_scalar_int(adapter, sql, database) > 0


def _count_rows(adapter, database: str, table: str) -> int:
    sql = f"SELECT COUNT(*) as total FROM {_sql_identifier(table)}"
    return _fetch_scalar_int(adapter, sql, database)


def _null_profile(adapter, database: str, table: str, cols: Iterable[str]) -> Dict[str, int]:
    # Resolver colunas com fallback e ignorar tokens que não existirem na tabela
    table_cols = set(_get_table_columns(adapter, database, table))
    resolved: List[Tuple[str, str]] = []
    missing: List[str] = []

    for token in cols:
        col = _resolve_column_token(token, table_cols)
        if not col:
            missing.append(token)
            continue
        resolved.append((token, col))

    if not resolved:
        return {c: -1 for c in cols}

    selects = []
    alias_map: Dict[str, str] = {}
    for i, (token, col) in enumerate(resolved):
        alias = f"c{i}"
        alias_map[alias] = token
        selects.append(f"SUM(CASE WHEN {_sql_col_is_null_or_empty(col)} THEN 1 ELSE 0 END) AS [{alias}]")

    sql = f"SELECT {', '.join(selects)} FROM {_sql_identifier(table)}"
    rows = _fetch_rows(adapter, sql, database)
    if not rows:
        return {c: -1 for c in cols}

    row = rows[0]
    out: Dict[str, int] = {}
    for alias, token in alias_map.items():
        out[token] = _as_int(row.get(alias))
    # Tokens ausentes: marcar -1 (sinaliza mismatch)
    for token in missing:
        out[token] = -1
    return out


def _duplicate_summary(adapter, database: str, check: DuplicateCheck, top_n: int = 50) -> Tuple[int, List[Dict[str, Any]]]:
    where_sql = f"WHERE {check.where_sql}" if check.where_sql else ""
    table_cols = set(_get_table_columns(adapter, database, check.table))
    resolved_keys: List[str] = []
    for token in check.key_columns:
        col = _resolve_column_token(token, table_cols)
        if col:
            resolved_keys.append(col)
    if not resolved_keys:
        return 0, []
    keys = ", ".join(f"[{k}]" for k in resolved_keys)
    sql_total = f"""
        SELECT COUNT(*) as total
        FROM (
            SELECT {keys}, COUNT(*) as qtd
            FROM {_sql_identifier(check.table)}
            {where_sql}
            GROUP BY {keys}
            HAVING COUNT(*) > 1
        ) t
    """
    total_groups = _fetch_scalar_int(adapter, sql_total, database)
    sql_top = f"""
        SELECT TOP {int(top_n)}
            {keys}, COUNT(*) as qtd
        FROM {_sql_identifier(check.table)}
        {where_sql}
        GROUP BY {keys}
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
    """
    rows = _fetch_rows(adapter, sql_top, database)
    return total_groups, rows


def _worst_records_documento(adapter, database: str, limit: int = 20) -> List[Dict[str, Any]]:
    # Score: número de campos essenciais vazios (estimativa)
    missing_exprs = [
        f"CASE WHEN {_sql_col_is_null_or_empty('processo_referencia')} THEN 1 ELSE 0 END",
        f"CASE WHEN {_sql_col_is_null_or_empty('status_documento')} THEN 1 ELSE 0 END",
        f"CASE WHEN {_sql_col_is_null_or_empty('status_documento_codigo')} THEN 1 ELSE 0 END",
        f"CASE WHEN {_sql_col_is_null_or_empty('situacao_documento')} THEN 1 ELSE 0 END",
        f"CASE WHEN {_sql_col_is_null_or_empty('canal_documento')} THEN 1 ELSE 0 END",
        f"CASE WHEN (data_registro IS NULL) THEN 1 ELSE 0 END",
        f"CASE WHEN (data_situacao IS NULL) THEN 1 ELSE 0 END",
        f"CASE WHEN (data_desembaraco IS NULL) THEN 1 ELSE 0 END",
        f"CASE WHEN {_sql_col_is_null_or_empty('json_dados_originais')} THEN 1 ELSE 0 END",
    ]
    score_sql = " + ".join(missing_exprs)
    sql = f"""
        SELECT TOP {int(limit)}
            id_documento,
            tipo_documento,
            numero_documento,
            processo_referencia,
            status_documento,
            status_documento_codigo,
            situacao_documento,
            canal_documento,
            data_registro,
            data_situacao,
            data_desembaraco,
            atualizado_em,
            ({score_sql}) AS missing_score
        FROM dbo.DOCUMENTO_ADUANEIRO
        ORDER BY ({score_sql}) DESC, atualizado_em DESC
    """
    return _fetch_rows(adapter, sql, database)


def _render_markdown_report(
    database: str,
    counts: Dict[str, int],
    nulls: Dict[str, Dict[str, int]],
    duplicates: Dict[str, Dict[str, Any]],
    worst_docs: List[Dict[str, Any]],
    started_at: str,
    finished_at: str,
) -> str:
    lines: List[str] = []
    lines.append("# Diagnóstico `mAIke_assistente`")
    lines.append("")
    lines.append(f"- **Database**: `{database}`")
    lines.append(f"- **Gerado em**: `{finished_at}`")
    lines.append("")
    lines.append("## Contagens por tabela")
    lines.append("")
    lines.append("| Tabela | Registros |")
    lines.append("|---|---:|")
    for t, c in counts.items():
        lines.append(f"| `{t}` | {c:,} |")
    lines.append("")
    lines.append("## Perfil de nulos/vazios (colunas essenciais)")
    lines.append("")
    for table, cols_map in nulls.items():
        lines.append(f"### `{table}`")
        lines.append("")
        lines.append("| Coluna | Nulos/Vazios |")
        lines.append("|---|---:|")
        for col, n in cols_map.items():
            lines.append(f"| `{col}` | {n:,} |")
        lines.append("")
    lines.append("## Duplicidades (chaves naturais)")
    lines.append("")
    for key, info in duplicates.items():
        lines.append(f"### `{key}`")
        lines.append("")
        lines.append(f"- **Grupos duplicados**: {info.get('groups', 0):,}")
        top = info.get("top", []) or []
        if top:
            lines.append("")
            lines.append("| Chave | Qtd |")
            lines.append("|---|---:|")
            for row in top:
                qtd = row.get("qtd", "")
                chave = ", ".join(f"{k}={_md_escape(row.get(k))}" for k in info.get("key_columns", []))
                lines.append(f"| `{chave}` | {qtd} |")
        lines.append("")
    lines.append("## Top 20 piores registros (DOCUMENTO_ADUANEIRO)")
    lines.append("")
    if not worst_docs:
        lines.append("_Sem dados ou tabela não disponível._")
        lines.append("")
    else:
        lines.append("| id | tipo | número | processo | status | código | situação | canal | missing_score | atualizado_em |")
        lines.append("|---:|---|---|---|---|---|---|---|---:|---|")
        for r in worst_docs:
            lines.append(
                "| {id} | {tipo} | {num} | {proc} | {st} | {cod} | {sit} | {can} | {sc} | {upd} |".format(
                    id=_md_escape(r.get("id_documento")),
                    tipo=_md_escape(r.get("tipo_documento")),
                    num=_md_escape(r.get("numero_documento")),
                    proc=_md_escape(r.get("processo_referencia")),
                    st=_md_escape(r.get("status_documento")),
                    cod=_md_escape(r.get("status_documento_codigo")),
                    sit=_md_escape(r.get("situacao_documento")),
                    can=_md_escape(r.get("canal_documento")),
                    sc=_md_escape(r.get("missing_score")),
                    upd=_md_escape(r.get("atualizado_em")),
                )
            )
        lines.append("")
    lines.append("## Metadados (JSON)")
    lines.append("")
    meta = {
        "database": database,
        "started_at": started_at,
        "finished_at": finished_at,
        "counts": counts,
        "duplicates": {k: {"groups": v.get("groups", 0)} for k, v in duplicates.items()},
    }
    lines.append("```json")
    lines.append(json.dumps(meta, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnosticar qualidade do banco mAIke_assistente (SQL Server).")
    parser.add_argument("--database", default=DB_NAME_DEFAULT, help="Nome do database (default: mAIke_assistente)")
    parser.add_argument("--output", default="", help="Caminho para salvar relatório Markdown (default: docs/DIAGNOSTICO_MAIKE_ASSISTENTE_<timestamp>.md)")
    parser.add_argument("--top-duplicates", type=int, default=30, help="Quantos grupos duplicados listar por check (default: 30)")
    parser.add_argument("--worst-limit", type=int, default=20, help="Quantos 'piores' registros listar (default: 20)")
    args = parser.parse_args()

    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server adapter não disponível")
        return 2

    database = args.database
    started_at = datetime.now().isoformat()

    table_checks, duplicate_checks = _build_checks()

    counts: Dict[str, int] = {}
    nulls: Dict[str, Dict[str, int]] = {}
    duplicates: Dict[str, Dict[str, Any]] = {}

    print("=" * 80)
    print("🔍 DIAGNÓSTICO mAIke_assistente")
    print("=" * 80)
    print(f"Database: {database}")
    print()

    # Contagens e perfil de nulos
    for tc in table_checks:
        if not _table_exists(adapter, database, tc.table):
            counts[tc.table] = 0
            nulls[tc.table] = {c: -1 for c in tc.essential_columns}
            continue
        counts[tc.table] = _count_rows(adapter, database, tc.table)
        nulls[tc.table] = _null_profile(adapter, database, tc.table, tc.essential_columns)

    # Duplicidades
    for dc in duplicate_checks:
        key = f"{dc.table}({', '.join(dc.key_columns)})"
        if not _table_exists(adapter, database, dc.table):
            duplicates[key] = {"groups": 0, "top": [], "key_columns": list(dc.key_columns)}
            continue
        groups, top = _duplicate_summary(adapter, database, dc, top_n=args.top_duplicates)
        duplicates[key] = {"groups": groups, "top": top, "key_columns": list(dc.key_columns)}

    worst_docs: List[Dict[str, Any]] = []
    if _table_exists(adapter, database, "dbo.DOCUMENTO_ADUANEIRO"):
        worst_docs = _worst_records_documento(adapter, database, limit=args.worst_limit)

    finished_at = datetime.now().isoformat()

    md = _render_markdown_report(
        database=database,
        counts=counts,
        nulls=nulls,
        duplicates=duplicates,
        worst_docs=worst_docs,
        started_at=started_at,
        finished_at=finished_at,
    )

    out_path = args.output.strip()
    if not out_path:
        out_path = str(ROOT_DIR / "docs" / f"DIAGNOSTICO_MAIKE_ASSISTENTE_{_now_stamp()}.md")

    try:
        Path(out_path).write_text(md, encoding="utf-8")
        print(f"✅ Relatório salvo em: {out_path}")
    except Exception as e:
        print(f"⚠️ Não consegui salvar relatório em {out_path}: {e}")
        print("📄 Conteúdo do relatório (início):")
        print(md[:4000])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

