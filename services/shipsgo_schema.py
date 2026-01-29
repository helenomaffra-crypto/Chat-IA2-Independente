import sqlite3


def criar_tabela_shipsgo_tracking(cursor: sqlite3.Cursor) -> None:
    """Cria tabela `shipsgo_tracking` e índices."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shipsgo_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL UNIQUE,
            eta_iso TEXT,
            porto_codigo TEXT,
            porto_nome TEXT,
            navio TEXT,
            status TEXT,
            payload_raw TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # ✅ Migrações best-effort (para bases antigas que já tinham a tabela sem colunas novas)
    try:
        cursor.execute("ALTER TABLE shipsgo_tracking ADD COLUMN status TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE shipsgo_tracking ADD COLUMN navio TEXT")
    except sqlite3.OperationalError:
        pass
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipsgo_proc ON shipsgo_tracking(processo_referencia)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_shipsgo_eta ON shipsgo_tracking(eta_iso)")

