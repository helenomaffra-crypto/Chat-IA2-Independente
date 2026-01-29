"""
Schema: sales_watch_state (SQLite)
---------------------------------
Persistência do estado do "watch" de vendas (evitar notificar repetido).
"""

from __future__ import annotations

import sqlite3


def criar_tabela_sales_watch_state(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_watch_state (
            termo TEXT PRIMARY KEY,
            seen_keys_json TEXT,
            updated_at TEXT
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_sales_watch_state_updated_at ON sales_watch_state(updated_at)"
    )

