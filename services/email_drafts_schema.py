"""
Schema (DDL) da tabela `email_drafts`.

Extraído do `db_manager.py` para reduzir tamanho/complexidade do arquivo monolítico,
mantendo compatibilidade via wrappers.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_email_drafts(cursor: sqlite3.Cursor) -> None:
    """
    Cria a tabela `email_drafts` (sistema de versões) e seus índices.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT UNIQUE NOT NULL,  -- ID único do draft (ex: "email_1739")
            session_id TEXT NOT NULL,
            destinatarios TEXT NOT NULL,  -- JSON array de emails
            assunto TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            cc TEXT,  -- JSON array de emails (opcional)
            bcc TEXT,  -- JSON array de emails (opcional)
            revision INTEGER DEFAULT 1,  -- Número da revisão (1, 2, 3...)
            status TEXT DEFAULT 'draft',  -- 'draft' | 'ready_to_send' | 'sent'
            funcao_email TEXT DEFAULT 'enviar_email_personalizado',  -- Tipo de email
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Índices para buscas rápidas
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_email_drafts_draft_id
        ON email_drafts(draft_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_email_drafts_session
        ON email_drafts(session_id, criado_em DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_email_drafts_status
        ON email_drafts(status, draft_id)
        """
    )

