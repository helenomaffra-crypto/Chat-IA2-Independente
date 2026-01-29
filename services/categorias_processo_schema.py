"""
Schema/migrações da tabela `categorias_processo` + seed de categorias padrão.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_categorias_processo(cursor: sqlite3.Cursor) -> None:
    """Cria/migra `categorias_processo`, índice e insere categorias padrão."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias_processo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT UNIQUE NOT NULL,  -- Ex: 'ABN', 'XYZ'
            confirmada_por_usuario BOOLEAN DEFAULT 1,  -- Se foi confirmada pelo usuário
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_categorias_categoria
        ON categorias_processo(categoria)
        """
    )

    # ✅ Inserir categorias padrão conhecidas se não existirem
    categorias_padrao = [
        "ALH",
        "VDM",
        "MSS",
        "BND",
        "DMD",
        "GYM",
        "SLL",
        "MDA",
        "NTM",
        "UPI",
        "GLT",
        "GPS",
        "MV5",
    ]
    for cat in categorias_padrao:
        cursor.execute(
            """
            INSERT OR IGNORE INTO categorias_processo (categoria, confirmada_por_usuario)
            VALUES (?, 1)
            """,
            (cat,),
        )

