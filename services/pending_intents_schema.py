"""
Schema/migrações da tabela `pending_intents`.

Extraído de `db_manager.py` para reduzir o monolito.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def criar_tabela_pending_intents(cursor: sqlite3.Cursor) -> None:
    """
    Cria/migra a tabela `pending_intents` (ações pendentes de confirmação) e seus índices.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pending_intents (
            intent_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            action_type TEXT NOT NULL,  -- 'send_email', 'create_duimp', 'send_report', etc.
            tool_name TEXT NOT NULL,
            args_normalizados TEXT,  -- JSON com argumentos normalizados
            payload_hash TEXT,  -- Hash SHA-256 do payload para detecção de duplicatas
            preview_text TEXT,  -- Texto do preview mostrado ao usuário
            status TEXT DEFAULT 'pending',  -- 'pending', 'executing', 'executed', 'cancelled', 'expired', 'superseded'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,  -- TTL (padrão: 2h após criação, 30min para emails)
            executed_at TIMESTAMP,
            executing_at TIMESTAMP,  -- Timestamp de quando virou 'executing' (para recovery)
            observacoes TEXT
        )
        """
    )

    # Migração: adicionar coluna executing_at se não existir
    try:
        cursor.execute("ALTER TABLE pending_intents ADD COLUMN executing_at TIMESTAMP")
        logger.info("✅ Coluna executing_at adicionada à tabela pending_intents")
    except sqlite3.OperationalError:
        # Coluna já existe, ignorar
        pass

    # Índices para pending intents
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pending_intents_session_status
        ON pending_intents(session_id, status, created_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pending_intents_status
        ON pending_intents(status, expires_at)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_pending_intents_action_type
        ON pending_intents(action_type, status)
        """
    )

