import logging
import sqlite3

logger = logging.getLogger(__name__)


def criar_tabela_nesh_chunks(cursor: sqlite3.Cursor) -> None:
    """
    Cria a tabela `nesh_chunks` (SQLite) para armazenar as Notas Explicativas (NESH).

    Motivação:
    - Remover dependência de JSON gigante em runtime
    - Permitir busca determinística por NCM (posição/subposição) via índices
    - Manter compatibilidade com o formato atual (`nesh_chunks.json`)
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS nesh_chunks (
            record_key TEXT PRIMARY KEY, -- ex: "0101:" (posição) ou "010121:0101" (subposição)
            section TEXT,
            chapter TEXT,
            chapter_code TEXT,
            chapter_title TEXT,
            position_code TEXT,
            position_code_clean TEXT,
            position_title TEXT,
            subposition_code TEXT,
            subposition_code_clean TEXT,
            subposition_title TEXT,
            text TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Índices para buscas por NCM
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_nesh_position_clean ON nesh_chunks(position_code_clean)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_nesh_subposition_clean ON nesh_chunks(subposition_code_clean)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_nesh_chapter_code ON nesh_chunks(chapter_code)"
    )

    logger.info("✅ Tabela 'nesh_chunks' e índices verificados/criados.")

