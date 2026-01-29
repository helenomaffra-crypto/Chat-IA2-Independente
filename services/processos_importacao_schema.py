import sqlite3


def criar_tabelas_processos_importacao(cursor: sqlite3.Cursor) -> None:
    """Cria tabelas relacionadas a processos de importação (integração externa) e índices associados."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processos_importacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT UNIQUE NOT NULL,
            categoria TEXT,
            numero_processo TEXT,
            ano TEXT,

            status TEXT DEFAULT 'pendente',
            mensagem_erro TEXT,

            duimp_numero TEXT,
            duimp_versao TEXT,

            payload_json TEXT NOT NULL,
            payload_atualizado TEXT,

            itens_aguardando_produto TEXT,

            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processado_em TIMESTAMP
        )
        """
    )

    # FASE 1: Tabela para vincular itens do processo a produtos CATP
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processo_itens_vinculacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL,
            numero_item INTEGER NOT NULL,

            -- Vinculação ao produto CATP
            produto_catp_codigo INTEGER,
            produto_catp_versao TEXT,
            produto_catp_denominacao TEXT,
            produto_catp_ncm TEXT,

            -- Dados do fabricante (vem do produto CATP)
            fabricante_codigo TEXT,
            fabricante_versao TEXT,
            fabricante_ni_operador TEXT,
            fabricante_pais TEXT,

            -- Status da vinculação
            status TEXT DEFAULT 'pendente',
            dados_item_completos TEXT,

            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(processo_referencia, numero_item),
            FOREIGN KEY (processo_referencia) REFERENCES processos_importacao(processo_referencia)
        )
        """
    )

    # Tabela de log para processos de importação
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processo_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL,
            nivel TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            dados_adicionais TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (processo_referencia) REFERENCES processos_importacao(processo_referencia)
        )
        """
    )

    # Índice para performance nas consultas de log (se falhar, seguimos sem travar init_db)
    try:
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_processo_log_ref
            ON processo_log(processo_referencia, criado_em DESC)
            """
        )
    except Exception:
        pass

