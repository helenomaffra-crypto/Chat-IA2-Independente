"""
Índices do SQLite para `processos_kanban`.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import sqlite3


def criar_indices_processos_kanban(cursor: sqlite3.Cursor) -> None:
    """Cria índices para `processos_kanban` (best-effort)."""
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_kanban_numero_ce ON processos_kanban(numero_ce)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_kanban_numero_di ON processos_kanban(numero_di)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_kanban_numero_duimp ON processos_kanban(numero_duimp)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_kanban_atualizado ON processos_kanban(atualizado_em)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_kanban_eta ON processos_kanban(eta_iso)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_kanban_data_destino_final ON processos_kanban(data_destino_final)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_kanban_data_armazenamento ON processos_kanban(data_armazenamento)"
    )

