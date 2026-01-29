-- ============================================================================
-- Tabela: HISTORICO_PAGAMENTOS
-- Descrição: Histórico completo de pagamentos (BOLETO, PIX, TED, BARCODE)
-- Banco: mAIke_assistente
-- Data: 13/01/2026
-- ============================================================================

-- ✅ Criar tabela se não existir
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.HISTORICO_PAGAMENTOS') AND type in (N'U'))
BEGIN
    CREATE TABLE dbo.HISTORICO_PAGAMENTOS (
        id_historico_pagamento INT IDENTITY(1,1) PRIMARY KEY,
        payment_id NVARCHAR(255) NOT NULL UNIQUE,
        tipo_pagamento NVARCHAR(50) NOT NULL,  -- 'BOLETO', 'PIX', 'TED', 'BARCODE'
        banco NVARCHAR(50) NOT NULL,  -- 'SANTANDER', 'BANCO_DO_BRASIL'
        ambiente NVARCHAR(50) NOT NULL,  -- 'SANDBOX', 'PRODUCAO'
        status NVARCHAR(50) NOT NULL,  -- 'READY_TO_PAY', 'PENDING_VALIDATION', 'PAYED', 'CANCELLED', 'FAILED'
        valor DECIMAL(18,2) NOT NULL,
        codigo_barras NVARCHAR(255) NULL,  -- Para boletos
        beneficiario NVARCHAR(500) NULL,
        vencimento DATE NULL,  -- Data de vencimento
        agencia_origem NVARCHAR(20) NULL,
        conta_origem NVARCHAR(50) NULL,
        saldo_disponivel_antes DECIMAL(18,2) NULL,
        saldo_apos_pagamento DECIMAL(18,2) NULL,
        workspace_id NVARCHAR(255) NULL,
        payment_date DATE NULL,  -- Data do pagamento
        data_inicio DATETIME NULL,  -- Quando foi iniciado
        data_efetivacao DATETIME NULL,  -- Quando foi efetivado
        dados_completos NVARCHAR(MAX) NULL,  -- JSON com todos os dados retornados pela API
        observacoes NVARCHAR(MAX) NULL,
        criado_em DATETIME NOT NULL DEFAULT GETDATE(),
        atualizado_em DATETIME NOT NULL DEFAULT GETDATE()
    )
    
    PRINT '✅ Tabela HISTORICO_PAGAMENTOS criada com sucesso!'
END
ELSE
BEGIN
    PRINT '⚠️ Tabela HISTORICO_PAGAMENTOS já existe.'
END
GO

-- ✅ Criar índices para consultas rápidas
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_historico_pagamentos_payment_id' AND object_id = OBJECT_ID(N'dbo.HISTORICO_PAGAMENTOS'))
BEGIN
    CREATE INDEX idx_historico_pagamentos_payment_id ON dbo.HISTORICO_PAGAMENTOS(payment_id)
    PRINT '✅ Índice idx_historico_pagamentos_payment_id criado.'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_historico_pagamentos_status' AND object_id = OBJECT_ID(N'dbo.HISTORICO_PAGAMENTOS'))
BEGIN
    CREATE INDEX idx_historico_pagamentos_status ON dbo.HISTORICO_PAGAMENTOS(status, data_efetivacao)
    PRINT '✅ Índice idx_historico_pagamentos_status criado.'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_historico_pagamentos_tipo' AND object_id = OBJECT_ID(N'dbo.HISTORICO_PAGAMENTOS'))
BEGIN
    CREATE INDEX idx_historico_pagamentos_tipo ON dbo.HISTORICO_PAGAMENTOS(tipo_pagamento, banco, ambiente)
    PRINT '✅ Índice idx_historico_pagamentos_tipo criado.'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_historico_pagamentos_data' AND object_id = OBJECT_ID(N'dbo.HISTORICO_PAGAMENTOS'))
BEGIN
    CREATE INDEX idx_historico_pagamentos_data ON dbo.HISTORICO_PAGAMENTOS(data_efetivacao DESC)
    PRINT '✅ Índice idx_historico_pagamentos_data criado.'
END
GO

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_historico_pagamentos_banco_ambiente' AND object_id = OBJECT_ID(N'dbo.HISTORICO_PAGAMENTOS'))
BEGIN
    CREATE INDEX idx_historico_pagamentos_banco_ambiente ON dbo.HISTORICO_PAGAMENTOS(banco, ambiente, data_efetivacao DESC)
    PRINT '✅ Índice idx_historico_pagamentos_banco_ambiente criado.'
END
GO

PRINT '✅ Script de criação da tabela HISTORICO_PAGAMENTOS concluído!'
GO
