"""
Schema/migrações da tabela `ocorrencias_processos`.

Objetivo:
- Persistir "ocorrências" detectadas automaticamente (navio em atraso, SLA estourado por etapa, etc.)
- Evitar spam de notificações (idempotência via record_key + last_notified_at)
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


def criar_tabela_ocorrencias_processos(cursor: sqlite3.Cursor) -> None:
    """
    Cria/migra a tabela `ocorrencias_processos` e índices.

    Campos importantes:
    - record_key: chave única para idempotência (ex: "navio_atraso:MSC XYZ:BRSSZ:2026-01-10")
    - status: 'open' | 'closed'
    - last_notified_at: quando a ocorrência gerou notificação pela última vez (anti-spam)
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ocorrencias_processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_key TEXT UNIQUE NOT NULL,
            tipo TEXT NOT NULL,
            severidade TEXT DEFAULT 'media', -- 'baixa' | 'media' | 'alta' | 'critica'
            processo_referencia TEXT, -- opcional (para ocorrências agregadas por navio pode ser NULL)
            nome_navio TEXT, -- opcional
            etapa_kanban TEXT, -- opcional (para SLA por etapa)
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            dados_extras TEXT, -- JSON
            status TEXT DEFAULT 'open', -- 'open' | 'closed'
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_notified_at TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_status_lastseen
        ON ocorrencias_processos(status, last_seen_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_tipo
        ON ocorrencias_processos(tipo, last_seen_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_processo
        ON ocorrencias_processos(processo_referencia, status, last_seen_at DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_navio
        ON ocorrencias_processos(nome_navio, status, last_seen_at DESC)
        """
    )

    logger.info("✅ Tabela 'ocorrencias_processos' e índices verificados/criados.")

