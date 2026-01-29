"""
SyncStatus schema (SQLite)

Persiste status/telemetria das rotinas de sincronização (ex.: Kanban).
"""

from __future__ import annotations

import sqlite3


def criar_tabela_sync_status(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_status (
            nome TEXT PRIMARY KEY,
            last_attempt_at TEXT,
            last_success_at TEXT,
            last_error TEXT,
            last_count INTEGER,
            last_duration_ms INTEGER
        )
        """
    )

