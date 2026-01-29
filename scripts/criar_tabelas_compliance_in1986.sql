/*
    Tabelas para Gestão de Saldo Virtual por Cliente e Compliance IN 1986/2020
    Objetivo: Segregar recursos de VENDA de recursos de APORTE DE TRIBUTOS.
*/

-- 1. Tabela de Saldo Acumulado por Cliente
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[SALDO_RECURSO_CLIENTE]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[SALDO_RECURSO_CLIENTE] (
        [id_saldo] INT IDENTITY(1,1) PRIMARY KEY,
        [cnpj_cliente] VARCHAR(20) NOT NULL UNIQUE,
        [nome_cliente] VARCHAR(255),
        [saldo_disponivel] DECIMAL(18,2) DEFAULT 0.00,
        [total_aportado] DECIMAL(18,2) DEFAULT 0.00,
        [total_utilizado] DECIMAL(18,2) DEFAULT 0.00,
        [ultima_atualizacao] DATETIME DEFAULT GETDATE()
    );
    PRINT '✅ Tabela SALDO_RECURSO_CLIENTE criada.';
END

-- 2. Tabela de Log de Movimentação da Carteira Virtual (O "Razão" do Cliente)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CARTEIRA_VIRTUAL_LOG]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[CARTEIRA_VIRTUAL_LOG] (
        [id_log] INT IDENTITY(1,1) PRIMARY KEY,
        [cnpj_cliente] VARCHAR(20) NOT NULL,
        [id_movimentacao_bancaria] INT NOT NULL, -- FK para MOVIMENTACAO_BANCARIA
        [tipo_operacao] VARCHAR(20) NOT NULL, -- 'APORTE' (Crédito) ou 'UTILIZACAO' (Débito)
        [valor] DECIMAL(18,2) NOT NULL,
        [saldo_anterior] DECIMAL(18,2),
        [saldo_posterior] DECIMAL(18,2),
        [processo_referencia] VARCHAR(50), -- Vinculado se for UTILIZACAO
        [data_operacao] DATETIME DEFAULT GETDATE(),
        [observacoes] VARCHAR(MAX)
    );
    PRINT '✅ Tabela CARTEIRA_VIRTUAL_LOG criada.';
END

-- 3. Adicionar coluna de Natureza Jurídica na tabela de classificações se não existir
-- Isso permite marcar se uma entrada é VENDA ou APORTE
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[LANCAMENTO_TIPO_DESPESA]') AND name = 'natureza_recurso')
BEGIN
    ALTER TABLE [dbo].[LANCAMENTO_TIPO_DESPESA] 
    ADD [natureza_recurso] VARCHAR(50) DEFAULT 'OPERACIONAL'; -- 'VENDA', 'APORTE_TRIBUTOS', 'OPERACIONAL'
    PRINT '✅ Coluna natureza_recurso adicionada à LANCAMENTO_TIPO_DESPESA.';
END

