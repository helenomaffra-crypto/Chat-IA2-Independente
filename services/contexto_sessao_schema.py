"""
Schema/migrações da tabela `contexto_sessao`.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_contexto_sessao(cursor: sqlite3.Cursor) -> None:
    """Cria a tabela `contexto_sessao` (contexto persistente por sessão) e seu índice."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contexto_sessao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            tipo_contexto TEXT NOT NULL,  -- 'processo_atual', 'categoria_atual', 'ultima_consulta', etc.
            chave TEXT NOT NULL,  -- Chave do contexto (ex: 'processo_referencia', 'categoria', etc.)
            valor TEXT NOT NULL,  -- Valor do contexto (ex: 'VDM.0004/25', 'VDM', etc.)
            dados_json TEXT,  -- Dados adicionais em JSON
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, tipo_contexto, chave)
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_contexto_sessao ON contexto_sessao(session_id, tipo_contexto)"
    )

