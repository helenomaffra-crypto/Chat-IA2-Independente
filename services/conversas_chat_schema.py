"""
Schema/migrações da tabela `conversas_chat` (conversas importantes do chat).

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_conversas_chat(cursor: sqlite3.Cursor) -> None:
    """Cria a tabela `conversas_chat` e seus índices."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversas_chat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            mensagem_usuario TEXT NOT NULL,
            resposta_ia TEXT NOT NULL,
            tipo_conversa TEXT,  -- 'consulta', 'acao', 'geral', etc.
            processo_referencia TEXT,  -- Se relacionado a um processo
            importante BOOLEAN DEFAULT 0,  -- Se é uma conversa importante
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversas_session
        ON conversas_chat(session_id, criado_em DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversas_importante
        ON conversas_chat(importante, criado_em DESC)
        """
    )

