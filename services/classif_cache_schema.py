import sqlite3


def criar_tabelas_classif_cache(cursor: sqlite3.Cursor) -> None:
    """Cria as tabelas de cache do Classif (NCM) e metadados."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS classif_cache (
            ncm TEXT PRIMARY KEY,
            unidade_medida_estatistica TEXT,
            descricao TEXT,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS classif_metadata (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

