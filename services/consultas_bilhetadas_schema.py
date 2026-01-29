import sqlite3


def criar_tabelas_consultas_bilhetadas(cursor: sqlite3.Cursor) -> None:
    """Cria/migra tabelas de consultas bilhetadas e pendências + índices."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS consultas_bilhetadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_consulta TEXT NOT NULL,  -- 'CE', 'DI', 'Manifesto', 'Escala', 'CCT'
            numero_documento TEXT,
            endpoint TEXT NOT NULL,
            metodo TEXT DEFAULT 'GET',
            status_code INTEGER,
            sucesso BOOLEAN DEFAULT 1,
            data_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processo_referencia TEXT,
            usou_api_publica_antes BOOLEAN DEFAULT 0,  -- Se verificou API pública antes
            observacoes TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS consultas_bilhetadas_pendentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_consulta TEXT NOT NULL,  -- 'CE', 'DI', 'Manifesto', 'Escala', 'CCT'
            numero_documento TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            metodo TEXT DEFAULT 'GET',
            processo_referencia TEXT,
            motivo TEXT,  -- Por que precisa consultar (ex: "API pública indica mudança")
            data_publica_verificada TIMESTAMP,  -- Data da última verificação na API pública
            data_ultima_alteracao_cache TIMESTAMP,  -- Data da última alteração no cache
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprovado_em TIMESTAMP,
            aprovado_por TEXT,  -- Usuário que aprovou
            status TEXT DEFAULT 'pendente',  -- 'pendente', 'aprovado', 'rejeitado', 'executado'
            observacoes TEXT
        )
        """
    )

    # MIGRAÇÃO: adicionar coluna processando_aprovacao se não existir
    try:
        cursor.execute("ALTER TABLE consultas_bilhetadas_pendentes ADD COLUMN processando_aprovacao TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultas_pendentes_status
        ON consultas_bilhetadas_pendentes(status, criado_em)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultas_pendentes_tipo
        ON consultas_bilhetadas_pendentes(tipo_consulta, numero_documento)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultas_bilhetadas_tipo
        ON consultas_bilhetadas(tipo_consulta, data_consulta)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultas_bilhetadas_processo
        ON consultas_bilhetadas(processo_referencia, data_consulta)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultas_bilhetadas_data
        ON consultas_bilhetadas(data_consulta)
        """
    )

