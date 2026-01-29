import sqlite3


def criar_tabelas_ce_cache(cursor: sqlite3.Cursor) -> None:
    """Cria/migra tabelas de cache de CE + previsões/itens e seus ajustes compatíveis."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ces_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ce TEXT UNIQUE NOT NULL,
            tipo TEXT,
            ul_destino_final TEXT,
            pais_procedencia TEXT,
            cpf_cnpj_consignatario TEXT,
            porto_destino TEXT,
            porto_origem TEXT,
            situacao_carga TEXT,
            carga_bloqueada BOOLEAN DEFAULT 0,
            bloqueio_impede_despacho BOOLEAN DEFAULT 0,
            json_completo TEXT NOT NULL,
            consultado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ultima_alteracao_api TIMESTAMP,
            processo_referencia TEXT,
            di_numero TEXT,
            duimp_numero TEXT
        )
        """
    )

    # Cache de previsão de atracação (para evitar consultas bilhetadas repetidas)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS previsao_atracacao_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ce TEXT UNIQUE NOT NULL,
            porto_destino TEXT,
            numero_manifesto TEXT,
            numero_escala TEXT,
            data_previsao_atracacao TEXT,
            data_atracacao_real TEXT,
            data_previsao_passe_saida TEXT,
            data_passe_saida TEXT,
            data_inicio_operacao TEXT,
            data_fim_operacao TEXT,
            situacao TEXT,
            terminal_atracacao TEXT,
            local_atracacao TEXT,
            tipo_operacao TEXT,
            escala_encerrada BOOLEAN,
            estrategia_usada TEXT,
            dados_completos_escala TEXT,
            json_resposta_completa TEXT NOT NULL,
            consultado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (numero_ce) REFERENCES ces_cache(numero_ce)
        )
        """
    )

    # Cache de itens do CE (containers, cargas soltas, graneis) — consulta bilhetada, mas só 1x por CE
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ce_itens_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_ce TEXT UNIQUE NOT NULL,
            qtd_total_itens INTEGER DEFAULT 0,
            qtd_itens_recebidos INTEGER DEFAULT 0,
            qtd_itens_restantes INTEGER DEFAULT 0,
            json_itens_completo TEXT NOT NULL,
            consultado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (numero_ce) REFERENCES ces_cache(numero_ce)
        )
        """
    )

    # Migrações compatíveis (instalações antigas)
    for ddl in (
        "ALTER TABLE ces_cache ADD COLUMN processo_referencia TEXT",
        "ALTER TABLE ces_cache ADD COLUMN ultima_alteracao_api TIMESTAMP",
        "ALTER TABLE ces_cache ADD COLUMN di_numero TEXT",
        "ALTER TABLE ces_cache ADD COLUMN duimp_numero TEXT",
    ):
        try:
            cursor.execute(ddl)
        except sqlite3.OperationalError:
            pass

