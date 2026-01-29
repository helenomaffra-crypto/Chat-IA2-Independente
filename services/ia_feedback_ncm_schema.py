import sqlite3


def criar_tabela_ia_feedback_ncm(cursor: sqlite3.Cursor) -> None:
    """Cria tabela e índices para feedback das sugestões de NCM da IA."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ia_feedback_ncm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao_produto TEXT NOT NULL,
            ncm_sugerido TEXT NOT NULL,
            ncm_correto TEXT NOT NULL,
            descricao_ncm_correto TEXT,
            contexto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Índices para performance nas consultas de feedback
    for ddl in (
        "CREATE INDEX IF NOT EXISTS idx_ia_feedback_descricao ON ia_feedback_ncm(descricao_produto)",
        "CREATE INDEX IF NOT EXISTS idx_ia_feedback_ncm_correto ON ia_feedback_ncm(ncm_correto)",
        "CREATE INDEX IF NOT EXISTS idx_ia_feedback_criado ON ia_feedback_ncm(criado_em DESC)",
    ):
        try:
            cursor.execute(ddl)
        except sqlite3.OperationalError:
            # Se o SQLite recusar (ex: schema/colation antiga), não quebrar init_db.
            pass

