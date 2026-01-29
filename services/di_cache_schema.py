import sqlite3


def criar_tabelas_di_cache(cursor: sqlite3.Cursor) -> None:
    """Cria/migra tabelas de cache de DI e seus ajustes compatíveis."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS dis_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_di TEXT,
            numero_identificacao TEXT,
            numero_protocolo TEXT,
            chave_unica TEXT UNIQUE NOT NULL,
            json_completo TEXT NOT NULL,
            consultado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processo_referencia TEXT,
            canal_selecao_parametrizada TEXT,
            data_hora_desembaraco TIMESTAMP,
            data_hora_registro TIMESTAMP,
            situacao_di TEXT,
            situacao_entrega_carga TEXT,
            data_hora_situacao_di TIMESTAMP,
            ultima_alteracao_api TIMESTAMP
        )
        """
    )

    # Migrações compatíveis (instalações antigas)
    for ddl in (
        "ALTER TABLE dis_cache ADD COLUMN canal_selecao_parametrizada TEXT",
        "ALTER TABLE dis_cache ADD COLUMN data_hora_desembaraco TIMESTAMP",
        "ALTER TABLE dis_cache ADD COLUMN data_hora_registro TIMESTAMP",
        "ALTER TABLE dis_cache ADD COLUMN situacao_di TEXT",
        "ALTER TABLE dis_cache ADD COLUMN situacao_entrega_carga TEXT",
        "ALTER TABLE dis_cache ADD COLUMN data_hora_situacao_di TIMESTAMP",
        "ALTER TABLE dis_cache ADD COLUMN ultima_alteracao_api TIMESTAMP",
    ):
        try:
            cursor.execute(ddl)
        except sqlite3.OperationalError:
            pass

