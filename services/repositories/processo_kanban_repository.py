import logging
from typing import List, Optional

from db_manager import get_db_connection

logger = logging.getLogger(__name__)


class ProcessoKanbanRepository:
    """
    Repositório simples para consultar o cache `processos_kanban` (SQLite).

    Usado para features que precisam de uma lista rápida de processos ativos por categoria
    (ex: sugestão de split de despesas na conciliação bancária).
    """

    def listar_referencias_por_categoria(self, categoria: str, limite: int = 5) -> List[str]:
        categoria = (categoria or "").strip().upper()
        if not categoria:
            return []

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT processo_referencia
                FROM processos_kanban
                WHERE processo_referencia LIKE ?
                ORDER BY atualizado_em DESC
                LIMIT ?
                """,
                (f"{categoria}.%", int(limite)),
            )
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows if r and r[0]]
        except Exception as e:
            logger.warning(f"⚠️ Erro ao listar processos_kanban por categoria {categoria}: {e}")
            return []

    def existe_categoria(self, categoria: str) -> bool:
        categoria = (categoria or "").strip().upper()
        if not categoria:
            return False

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM processos_kanban
                WHERE processo_referencia LIKE ?
                LIMIT 1
                """,
                (f"{categoria}.%",),
            )
            row = cursor.fetchone()
            conn.close()
            return bool(row)
        except Exception:
            return False

