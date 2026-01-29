import sqlite3


def criar_tabelas_duimp(cursor: sqlite3.Cursor) -> None:
    """Cria/migra tabelas de DUIMP (`duimps`, `duimp_itens`) e seus ajustes básicos."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS duimps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL,
            versao TEXT NOT NULL,
            status TEXT DEFAULT 'rascunho',
            ambiente TEXT DEFAULT 'validacao',
            payload_completo TEXT NOT NULL,
            processo_referencia TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(numero, versao)
        )
        """
    )

    # Migração: adicionar coluna processo_referencia se não existir (instalações antigas)
    try:
        cursor.execute("ALTER TABLE duimps ADD COLUMN processo_referencia TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS duimp_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            duimp_numero TEXT NOT NULL,
            duimp_versao TEXT NOT NULL,
            numero_item INTEGER NOT NULL,
            payload_item TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (duimp_numero, duimp_versao) REFERENCES duimps(numero, versao),
            UNIQUE(duimp_numero, duimp_versao, numero_item)
        )
        """
    )

