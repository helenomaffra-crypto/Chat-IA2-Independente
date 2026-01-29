"""
Schema/migrações da tabela `processos_kanban_historico`.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_processos_kanban_historico(cursor: sqlite3.Cursor) -> None:
    """Cria a tabela de histórico de mudanças nos processos (compacto) e seus índices."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processos_kanban_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL,
            campo_mudado TEXT NOT NULL,  -- 'situacao_ce', 'situacao_di', 'eta_iso', etc.
            valor_anterior TEXT,
            valor_novo TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_processo
        ON processos_kanban_historico(processo_referencia, criado_em DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_campo
        ON processos_kanban_historico(campo_mudado, criado_em DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_data
        ON processos_kanban_historico(criado_em DESC)
        """
    )

