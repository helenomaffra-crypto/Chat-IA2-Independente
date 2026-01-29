import sqlite3


def criar_tabelas_legislacao(cursor: sqlite3.Cursor) -> None:
    """
    Cria/migra tabelas de legislação (`legislacao`, `legislacao_trecho`) e seus índices.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS legislacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_ato TEXT NOT NULL,  -- 'IN', 'Lei', 'Decreto', 'Portaria', etc.
            numero TEXT NOT NULL,  -- '680', '12345', etc.
            ano INTEGER NOT NULL,  -- 2006, 2024, etc.
            sigla_orgao TEXT,  -- 'RFB', 'MF', 'MDIC', etc.
            titulo_oficial TEXT,  -- Título ou ementa do ato
            fonte_url TEXT,  -- URL oficial de onde foi baixado
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            em_vigor BOOLEAN DEFAULT 1,  -- Flag simples para indicar se está em vigor
            texto_integral TEXT,  -- Texto completo do ato (opcional, para referência)
            UNIQUE(tipo_ato, numero, ano, sigla_orgao)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS legislacao_trecho (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            legislacao_id INTEGER NOT NULL,
            referencia TEXT NOT NULL,  -- 'Art. 5º', 'Art. 5º, § 2º', 'Art. 7º, inciso III', etc.
            tipo_trecho TEXT NOT NULL,  -- 'artigo', 'caput', 'paragrafo', 'inciso', 'alinea'
            texto TEXT NOT NULL,  -- Texto do trecho em si
            texto_com_artigo TEXT NOT NULL,  -- Texto do trecho + caput do artigo completo para contexto
            ordem INTEGER NOT NULL,  -- Ordem de leitura dentro da legislação
            numero_artigo INTEGER,  -- Número do artigo (5, 7, etc.) para facilitar agrupamento
            hierarquia_json TEXT,  -- JSON com { "artigo": 5, "paragrafo": 2, "inciso": "III" }
            revogado BOOLEAN DEFAULT 0,  -- Flag para indicar se o trecho está revogado
            FOREIGN KEY (legislacao_id) REFERENCES legislacao(id) ON DELETE CASCADE
        )
        """
    )

    # Índices para consultas rápidas
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legislacao_ato ON legislacao(tipo_ato, numero, ano, sigla_orgao)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legislacao_trecho_legislacao ON legislacao_trecho(legislacao_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legislacao_trecho_artigo ON legislacao_trecho(numero_artigo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legislacao_trecho_ordem ON legislacao_trecho(legislacao_id, ordem)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legislacao_trecho_texto ON legislacao_trecho(texto)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legislacao_trecho_texto_com_artigo ON legislacao_trecho(texto_com_artigo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_legislacao_trecho_revogado ON legislacao_trecho(revogado)")

    # MIGRAÇÃO: adicionar coluna revogado se não existir (para instalações antigas)
    try:
        cursor.execute("ALTER TABLE legislacao_trecho ADD COLUMN revogado BOOLEAN DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Coluna já existe

