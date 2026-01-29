"""
Schema/migrações da tabela `processo_documentos`.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_processo_documentos(cursor: sqlite3.Cursor) -> None:
    """Cria a tabela `processo_documentos` (vinculação de documentos a processos)."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processo_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,
            numero_documento TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(processo_referencia, tipo_documento, numero_documento),
            FOREIGN KEY (processo_referencia) REFERENCES processos(processo_referencia)
        )
        """
    )

