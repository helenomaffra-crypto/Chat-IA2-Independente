"""
Schema/migrações da tabela `usuarios_chat`.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_usuarios_chat(cursor: sqlite3.Cursor) -> None:
    """Cria a tabela `usuarios_chat` e seus índices."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,  -- ID da sessão do navegador
            nome TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_usuarios_session
        ON usuarios_chat(session_id)
        """
    )

