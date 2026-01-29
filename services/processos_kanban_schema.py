import sqlite3


def criar_tabelas_processos_e_kanban(cursor: sqlite3.Cursor) -> None:
    """Cria/migra tabelas relacionadas a processos e cache do Kanban (processos ativos)."""
    # Tabela de processos (monitoramento básico)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT UNIQUE NOT NULL,
            categoria TEXT,
            status TEXT DEFAULT 'ativo',
            descricao TEXT,
            observacoes TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Cache de processos do Kanban (processos ativos)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processos_kanban (
            processo_referencia TEXT PRIMARY KEY,
            id_processo_importacao INTEGER,
            id_importacao INTEGER,
            etapa_kanban TEXT,
            modal TEXT,
            numero_ce TEXT,
            numero_di TEXT,
            numero_duimp TEXT,
            bl_house TEXT,
            master_bl TEXT,
            situacao_ce TEXT,
            situacao_di TEXT,
            situacao_entrega TEXT,
            tem_pendencias BOOLEAN DEFAULT 0,
            pendencia_icms TEXT,
            pendencia_frete BOOLEAN,
            data_criacao TEXT,
            data_embarque TEXT,
            data_desembaraco TEXT,
            data_entrega TEXT,
            data_destino_final TEXT,
            data_armazenamento TEXT,
            data_situacao_carga_ce TEXT,
            data_atracamento TEXT,
            eta_iso TEXT,
            porto_codigo TEXT,
            porto_nome TEXT,
            nome_navio TEXT,
            status_shipsgo TEXT,
            numero_dta TEXT,
            documento_despacho TEXT,
            numero_documento_despacho TEXT,
            dados_completos_json TEXT,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fonte TEXT DEFAULT 'kanban'
        )
        """
    )

    # Migrações: instalações antigas podem não ter colunas novas (antes de criar índices!)
    for ddl in (
        "ALTER TABLE processos_kanban ADD COLUMN eta_iso TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN porto_codigo TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN porto_nome TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN nome_navio TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN status_shipsgo TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN data_destino_final TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN data_armazenamento TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN data_situacao_carga_ce TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN data_atracamento TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN numero_dta TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN documento_despacho TEXT",
        "ALTER TABLE processos_kanban ADD COLUMN numero_documento_despacho TEXT",
    ):
        try:
            cursor.execute(ddl)
        except sqlite3.OperationalError:
            pass

