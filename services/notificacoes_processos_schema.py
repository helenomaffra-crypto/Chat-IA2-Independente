import sqlite3


def criar_tabela_notificacoes_processos(cursor: sqlite3.Cursor) -> None:
    """Cria tabela e índices de notificações de mudanças nos processos."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS notificacoes_processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL,
            tipo_notificacao TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            dados_extras TEXT,
            lida BOOLEAN DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lida_em TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notificacoes_processo
        ON notificacoes_processos(processo_referencia, criado_em DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notificacoes_lida
        ON notificacoes_processos(lida, criado_em DESC)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_notificacoes_tipo
        ON notificacoes_processos(tipo_notificacao, criado_em DESC)
        """
    )

