"""
Schema/migrações da tabela `temporizador_monitoramento`.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_temporizador_monitoramento(cursor: sqlite3.Cursor) -> None:
    """Cria a tabela para persistir estado do temporizador de monitoramento."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS temporizador_monitoramento (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ativo BOOLEAN DEFAULT 0,
            intervalo_minutos INTEGER DEFAULT 60,
            ultima_execucao TIMESTAMP,
            proxima_execucao TIMESTAMP,
            execucoes_total INTEGER DEFAULT 0,
            execucoes_sucesso INTEGER DEFAULT 0,
            execucoes_erro INTEGER DEFAULT 0,
            ultimo_resultado TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

