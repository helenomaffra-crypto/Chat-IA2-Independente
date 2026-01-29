import logging
import sqlite3


def criar_tabelas_cct_cache(cursor: sqlite3.Cursor) -> None:
    """Cria/migra tabelas de cache de CCT e seus ajustes compatíveis."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ccts_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_cct TEXT UNIQUE NOT NULL,
            tipo TEXT,
            ruc TEXT,
            cnpj_responsavel_arquivo TEXT,
            identificacao_documento_consignatario TEXT,
            aeroporto_origem TEXT,
            aeroporto_destino TEXT,
            situacao_atual TEXT,
            data_hora_situacao_atual TIMESTAMP,
            data_chegada_efetiva TIMESTAMP,
            quantidade_volumes INTEGER,
            peso_bruto REAL,
            tem_bloqueios BOOLEAN DEFAULT 0,
            bloqueios_ativos TEXT,
            bloqueios_baixados TEXT,
            valor_frete_total REAL,
            moeda_frete TEXT,
            duimp_vinculada TEXT,
            versao_duimp TEXT,
            di_numero TEXT,
            json_completo TEXT NOT NULL,
            json_resumo TEXT,
            consultado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processo_referencia TEXT
        )
        """
    )

    # Migrações compatíveis (instalações antigas)
    try:
        cursor.execute("ALTER TABLE ccts_cache ADD COLUMN bloqueios_baixados TEXT")
        logging.info("✅ Coluna bloqueios_baixados adicionada à tabela ccts_cache")
    except sqlite3.OperationalError:
        pass  # Coluna já existe

    try:
        cursor.execute("ALTER TABLE ccts_cache ADD COLUMN di_numero TEXT")
        logging.info("✅ Coluna di_numero adicionada à tabela ccts_cache")
    except sqlite3.OperationalError:
        pass  # Coluna já existe

