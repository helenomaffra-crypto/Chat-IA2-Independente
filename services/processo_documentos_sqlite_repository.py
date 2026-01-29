"""
Repositório SQLite: tabela `processo_documentos` e fallback via `processos_kanban`.

Objetivo: reduzir o monolito `db_manager.py` extraindo operações simples de vínculo de documentos.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any, Dict, List, Optional

from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)


def listar_documentos_processo(processo_referencia: str) -> List[Dict[str, Any]]:
    """Lista todos os documentos vinculados a um processo.

    Busca em:
    1) processo_documentos (tabela de vínculos)
    2) processos_kanban (fallback - documentos do Kanban)
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1) Buscar em processo_documentos
        cursor.execute(
            """
            SELECT * FROM processo_documentos
            WHERE processo_referencia = ?
            ORDER BY criado_em DESC
            """,
            (processo_referencia,),
        )

        rows = cursor.fetchall()
        result: List[Dict[str, Any]] = [dict(row) for row in rows]

        # 2) Fallback: buscar do Kanban (processos_kanban)
        if not result:
            cursor.execute(
                """
                SELECT
                    processo_referencia,
                    numero_ce,
                    numero_di,
                    numero_duimp,
                    documento_despacho,
                    numero_documento_despacho
                FROM processos_kanban
                WHERE processo_referencia = ?
                LIMIT 1
                """,
                (processo_referencia,),
            )

            kanban_row = cursor.fetchone()
            if kanban_row:
                if kanban_row["numero_ce"]:
                    result.append(
                        {
                            "tipo_documento": "CE",
                            "numero_documento": kanban_row["numero_ce"],
                            "processo_referencia": processo_referencia,
                        }
                    )
                if kanban_row["numero_di"]:
                    result.append(
                        {
                            "tipo_documento": "DI",
                            "numero_documento": kanban_row["numero_di"],
                            "processo_referencia": processo_referencia,
                        }
                    )
                if kanban_row["numero_duimp"]:
                    result.append(
                        {
                            "tipo_documento": "DUIMP",
                            "numero_documento": kanban_row["numero_duimp"],
                            "processo_referencia": processo_referencia,
                        }
                    )

                logger.info(
                    f"✅ Processo {processo_referencia}: Documentos encontrados no Kanban: "
                    f"CE={bool(kanban_row['numero_ce'])}, DI={bool(kanban_row['numero_di'])}, "
                    f"DUIMP={bool(kanban_row['numero_duimp'])}"
                )

        conn.close()
        return result
    except Exception as e:
        logger.error(f"Erro ao listar documentos do processo: {e}")
        return []


def desvincular_documento_processo(processo_referencia: str, tipo_documento: str, numero_documento: str) -> bool:
    """Desvincula um documento de um processo."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM processo_documentos
            WHERE processo_referencia = ? AND tipo_documento = ? AND numero_documento = ?
            """,
            (processo_referencia, tipo_documento, numero_documento),
        )

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected > 0:
            logger.info(
                f"✅ Documento {tipo_documento} {numero_documento} desvinculado do processo {processo_referencia}"
            )
            return True

        logger.warning(
            f"⚠️ Documento {tipo_documento} {numero_documento} não estava vinculado ao processo {processo_referencia}"
        )
        return False
    except Exception as e:
        logger.error(f"Erro ao desvincular documento do processo: {e}")
        return False


def desvincular_todos_documentos_tipo(processo_referencia: str, tipo_documento: str) -> int:
    """Desvincula todos os documentos de um tipo específico de um processo."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM processo_documentos
            WHERE processo_referencia = ? AND tipo_documento = ?
            """,
            (processo_referencia, tipo_documento),
        )

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected > 0:
            logger.info(
                f"✅ {rows_affected} documento(s) {tipo_documento} desvinculado(s) do processo {processo_referencia}"
            )

        return rows_affected
    except Exception as e:
        logger.error(f"Erro ao desvincular documentos do processo: {e}")
        return 0


def obter_processo_por_documento(tipo_documento: str, numero_documento: str) -> Optional[str]:
    """Obtém o processo_referencia vinculado a um documento (fonte da verdade: processo_documentos)."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT processo_referencia FROM processo_documentos
            WHERE tipo_documento = ? AND numero_documento = ?
            LIMIT 1
            """,
            (tipo_documento, numero_documento),
        )

        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar processo por documento: {e}")
        return None

