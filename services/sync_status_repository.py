"""
SyncStatusRepository (SQLite)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Retorna timestamp ISO 8601 com timezone UTC explícito para compatibilidade com JavaScript"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SyncStatusRepository:
    def __init__(self) -> None:
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            from db_manager import get_db_connection
            from services.sync_status_schema import criar_tabela_sync_status

            conn = get_db_connection()
            if conn:  # ✅ Verificar se conn não é None
                cur = conn.cursor()
                criar_tabela_sync_status(cur)
                conn.commit()
                conn.close()
        except Exception as e:
            logger.warning(f"[SyncStatus] ⚠️ Falha ao garantir tabela sync_status: {e}")

    def registrar_attempt(self, nome: str) -> None:
        try:
            from db_manager import get_db_connection

            conn = get_db_connection()
            if conn:  # ✅ Verificar se conn não é None
                cur = conn.cursor()
                # ✅ CORREÇÃO: Limpar last_error ao iniciar uma nova tentativa
                cur.execute(
                    """
                    INSERT INTO sync_status (nome, last_attempt_at, last_error)
                    VALUES (?, ?, NULL)
                    ON CONFLICT(nome) DO UPDATE SET 
                        last_attempt_at=excluded.last_attempt_at,
                        last_error=NULL
                    """,
                    ((nome or "").strip(), _now_iso()),
                )
                conn.commit()
                conn.close()
                logger.debug(f"🔄 [SyncStatus] Nova tentativa iniciada para '{nome}'")
        except Exception as e:
            logger.error(f"❌ [SyncStatus] Erro ao registrar tentativa: {e}")

    def registrar_sucesso(self, nome: str, *, count: Optional[int] = None, duration_ms: Optional[int] = None) -> None:
        try:
            from db_manager import get_db_connection

            conn = get_db_connection()
            if conn:  # ✅ Verificar se conn não é None
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO sync_status (nome, last_attempt_at, last_success_at, last_error, last_count, last_duration_ms)
                    VALUES (?, ?, ?, NULL, ?, ?)
                    ON CONFLICT(nome) DO UPDATE SET
                        last_attempt_at=excluded.last_attempt_at,
                        last_success_at=excluded.last_success_at,
                        last_error=NULL,
                        last_count=excluded.last_count,
                        last_duration_ms=excluded.last_duration_ms
                    """,
                    (
                        (nome or "").strip(),
                        _now_iso(),
                        _now_iso(),
                        int(count) if count is not None else None,
                        int(duration_ms) if duration_ms is not None else None,
                    ),
                )
                conn.commit()
                conn.close()
                logger.info(f"✅ [SyncStatus] Sucesso registrado para '{nome}': {count} itens em {duration_ms}ms")
        except Exception as e:
            logger.error(f"❌ [SyncStatus] Erro ao registrar sucesso: {e}")

    def registrar_erro(self, nome: str, erro: str, *, duration_ms: Optional[int] = None) -> None:
        try:
            from db_manager import get_db_connection

            conn = get_db_connection()
            if conn:  # ✅ Verificar se conn não é None
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO sync_status (nome, last_attempt_at, last_error, last_duration_ms)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(nome) DO UPDATE SET
                        last_attempt_at=excluded.last_attempt_at,
                        last_error=excluded.last_error,
                        last_duration_ms=excluded.last_duration_ms
                    """,
                    (
                        (nome or "").strip(),
                        _now_iso(),
                        (erro or "").strip()[:500],
                        int(duration_ms) if duration_ms is not None else None,
                    ),
                )
                conn.commit()
                conn.close()
                logger.warning(f"⚠️ [SyncStatus] Erro registrado para '{nome}': {erro}")
        except Exception as e:
            logger.error(f"❌ [SyncStatus] Erro ao registrar erro: {e}")

    def obter(self, nome: str) -> Optional[Dict[str, Any]]:
        try:
            from db_manager import get_db_connection
            import sqlite3

            conn = get_db_connection()
            if conn:  # ✅ Verificar se conn não é None
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("SELECT * FROM sync_status WHERE nome = ? LIMIT 1", ((nome or "").strip(),))
                row = cur.fetchone()
                conn.close()
                return dict(row) if row else None
            return None
        except Exception:
            return None

