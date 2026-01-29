import sqlite3


def criar_tabela_chat_alertas(cursor: sqlite3.Cursor) -> None:
    """Cria tabela de alertas proativos do chat (idempotente)."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            processo_referencia TEXT,
            documento_tipo TEXT,
            documento_numero TEXT,
            mensagem TEXT NOT NULL,
            nivel TEXT DEFAULT 'info',
            lido INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lido_em TIMESTAMP
        )
        """
    )

