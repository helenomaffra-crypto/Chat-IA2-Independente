"""
Índices auxiliares no SQLite (otimizações).

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_indices_otimizacao_sqlite(cursor: sqlite3.Cursor) -> None:
    """Cria índices auxiliares para melhorar performance (best-effort)."""
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ces_cache_processo ON ces_cache(processo_referencia)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ces_cache_cnpj ON ces_cache(cpf_cnpj_consignatario)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ccts_cache_processo ON ccts_cache(processo_referencia)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ccts_cache_cnpj ON ccts_cache(identificacao_documento_consignatario)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dis_cache_processo ON dis_cache(processo_referencia)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_dis_cache_chave ON dis_cache(chave_unica)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_processo_documentos_ref ON processo_documentos(processo_referencia)"
        )
    except Exception:
        # Índices são "best effort" e não podem quebrar init_db()
        pass

