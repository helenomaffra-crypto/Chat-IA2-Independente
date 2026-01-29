import sqlite3


def criar_tabela_historico_pagamentos(cursor: sqlite3.Cursor) -> None:
    """Cria/migra tabela `historico_pagamentos` e seus índices."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS historico_pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id TEXT NOT NULL UNIQUE,
            tipo_pagamento TEXT NOT NULL,  -- 'BOLETO', 'PIX', 'TED', 'BARCODE'
            banco TEXT NOT NULL,  -- 'SANTANDER', 'BANCO_DO_BRASIL'
            ambiente TEXT NOT NULL,  -- 'SANDBOX', 'PRODUCAO'
            status TEXT NOT NULL,  -- 'READY_TO_PAY', 'PENDING_VALIDATION', 'PAYED', 'CANCELLED', 'FAILED'
            valor REAL NOT NULL,
            codigo_barras TEXT,  -- Para boletos
            beneficiario TEXT,
            vencimento TEXT,  -- Data de vencimento (YYYY-MM-DD)
            agencia_origem TEXT,
            conta_origem TEXT,
            saldo_disponivel_antes REAL,
            saldo_apos_pagamento REAL,
            workspace_id TEXT,
            payment_date TEXT,  -- Data do pagamento (YYYY-MM-DD)
            data_inicio TIMESTAMP,  -- Quando foi iniciado
            data_efetivacao TIMESTAMP,  -- Quando foi efetivado
            dados_completos TEXT,  -- JSON com todos os dados retornados pela API
            observacoes TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_pagamentos_payment_id
        ON historico_pagamentos(payment_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_pagamentos_status
        ON historico_pagamentos(status, data_efetivacao)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_pagamentos_tipo
        ON historico_pagamentos(tipo_pagamento, banco, ambiente)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_historico_pagamentos_data
        ON historico_pagamentos(data_efetivacao DESC)
        """
    )

