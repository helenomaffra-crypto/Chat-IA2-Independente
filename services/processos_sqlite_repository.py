"""
Repositório SQLite: tabela `processos`.

Objetivo: reduzir o monolito `db_manager.py` extraindo operações simples de CRUD/listagem
sem criar dependências circulares.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, List, Optional

from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)


def listar_processos(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Lista processos, opcionalmente filtrados por status."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if status:
            cursor.execute(
                """
                SELECT * FROM processos
                WHERE status = ?
                ORDER BY atualizado_em DESC
                LIMIT ?
                """,
                (status, limit),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM processos
                ORDER BY atualizado_em DESC
                LIMIT ?
                """,
                (limit,),
            )

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar processos: {e}")
        return []


def buscar_processo(processo_referencia: str) -> Optional[Dict[str, Any]]:
    """Busca um processo pelo número (processo_referencia)."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM processos WHERE processo_referencia = ?",
            (processo_referencia,),
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar processo: {e}")
        return None

