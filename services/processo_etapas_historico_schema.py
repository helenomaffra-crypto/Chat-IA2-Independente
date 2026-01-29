"""
Schema/migrações da tabela `processo_etapas_historico`.

Objetivo:
- Persistir mudanças de `etapa_kanban` para permitir cálculo de lead time por etapa
- Base para alertas de "tempo parado na etapa" (SLA)
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def criar_tabela_processo_etapas_historico(cursor: sqlite3.Cursor) -> None:
    """Cria/migra a tabela `processo_etapas_historico` e índices."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processo_etapas_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL,
            etapa_anterior TEXT,
            etapa_nova TEXT NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fonte TEXT DEFAULT 'kanban',
            dados_extras TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_processo_etapas_hist_proc_changed
        ON processo_etapas_historico(processo_referencia, changed_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_processo_etapas_hist_etapa
        ON processo_etapas_historico(etapa_nova, changed_at DESC)
        """
    )

    logger.info("✅ Tabela 'processo_etapas_historico' e índices verificados/criados.")

