-- ==========================================
-- Script SQL: Criar Tabelas para TED
-- ==========================================
-- Data: 12/01/2026
-- Banco: mAIke_assistente
-- Descrição: Tabelas para cadastro de destinatários e histórico de TEDs
-- ==========================================

USE [mAIke_assistente];
GO

-- ==========================================
-- Tabela 1: TED_DESTINATARIOS
-- ==========================================
-- Armazena cadastro de pessoas/empresas que recebem TEDs

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TED_DESTINATARIOS]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[TED_DESTINATARIOS] (
        id_destinatario BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Identificação
        nome_completo VARCHAR(255) NOT NULL,
        cpf_cnpj VARCHAR(18) NOT NULL,
        tipo_pessoa VARCHAR(20) NOT NULL,  -- 'PESSOA_FISICA' ou 'PESSOA_JURIDICA'
        apelido VARCHAR(100),  -- Nome curto para facilitar busca
        
        -- Dados Bancários
        banco_codigo VARCHAR(10) NOT NULL,  -- Ex: '001', '033'
        banco_nome VARCHAR(100),  -- Ex: 'Banco do Brasil', 'Santander'
        agencia VARCHAR(20) NOT NULL,
        conta VARCHAR(50) NOT NULL,
        tipo_conta VARCHAR(20) NOT NULL,  -- 'CONTA_CORRENTE', 'CONTA_POUPANCA', 'CONTA_PAGAMENTO'
        
        -- Metadados
        observacoes TEXT,
        ativo BIT DEFAULT 1,  -- Se destinatário está ativo
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        -- Constraints
        CONSTRAINT UQ_TED_DESTINATARIOS_CPF_CNPJ UNIQUE (cpf_cnpj)
    );
    
    -- Índices para performance
    CREATE INDEX idx_ted_destinatarios_cpf_cnpj ON [dbo].[TED_DESTINATARIOS](cpf_cnpj);
    CREATE INDEX idx_ted_destinatarios_apelido ON [dbo].[TED_DESTINATARIOS](apelido);
    CREATE INDEX idx_ted_destinatarios_banco_conta ON [dbo].[TED_DESTINATARIOS](banco_codigo, agencia, conta);
    CREATE INDEX idx_ted_destinatarios_ativo ON [dbo].[TED_DESTINATARIOS](ativo);
    
    PRINT '✅ Tabela TED_DESTINATARIOS criada com sucesso!';
END
ELSE
BEGIN
    PRINT '⚠️ Tabela TED_DESTINATARIOS já existe.';
END
GO

-- ==========================================
-- Tabela 2: TED_TRANSFERENCIAS
-- ==========================================
-- Armazena histórico completo de todas as TEDs realizadas

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TED_TRANSFERENCIAS]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[TED_TRANSFERENCIAS] (
        id_transferencia BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- IDs
        transfer_id VARCHAR(100) NOT NULL UNIQUE,  -- ID retornado pela API
        workspace_id VARCHAR(100),  -- Workspace usado
        destinatario_id BIGINT,  -- FK para TED_DESTINATARIOS (opcional, pode ser NULL se não cadastrado)
        
        -- Dados da Transferência
        valor DECIMAL(18,2) NOT NULL,
        moeda VARCHAR(3) DEFAULT 'BRL',
        status VARCHAR(50) NOT NULL,  -- READY_TO_PAY, PENDING_CONFIRMATION, AUTHORIZED, SETTLED, REJECTED
        
        -- Conta Origem
        agencia_origem VARCHAR(20),
        conta_origem VARCHAR(50),
        
        -- Conta Destino (pode ser diferente do cadastrado se editado)
        banco_destino VARCHAR(10),
        agencia_destino VARCHAR(20),
        conta_destino VARCHAR(50),
        tipo_conta_destino VARCHAR(20),
        nome_destinatario VARCHAR(255),  -- Nome usado na transferência
        cpf_cnpj_destinatario VARCHAR(18),
        
        -- Datas
        data_criacao DATETIME NOT NULL DEFAULT GETDATE(),
        data_efetivacao DATETIME,
        data_consulta DATETIME,  -- Última consulta de status
        data_settled DATETIME,  -- Quando foi liquidada
        
        -- Dados Completos
        json_dados_completos NVARCHAR(MAX),  -- JSON completo da API
        
        -- Metadados
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        -- Foreign Key (opcional)
        CONSTRAINT FK_TED_TRANSFERENCIAS_DESTINATARIO 
            FOREIGN KEY (destinatario_id) 
            REFERENCES [dbo].[TED_DESTINATARIOS](id_destinatario)
            ON DELETE SET NULL
    );
    
    -- Índices para performance
    CREATE INDEX idx_ted_transferencias_transfer_id ON [dbo].[TED_TRANSFERENCIAS](transfer_id);
    CREATE INDEX idx_ted_transferencias_destinatario ON [dbo].[TED_TRANSFERENCIAS](destinatario_id);
    CREATE INDEX idx_ted_transferencias_status ON [dbo].[TED_TRANSFERENCIAS](status);
    CREATE INDEX idx_ted_transferencias_data_criacao ON [dbo].[TED_TRANSFERENCIAS](data_criacao DESC);
    CREATE INDEX idx_ted_transferencias_workspace ON [dbo].[TED_TRANSFERENCIAS](workspace_id);
    
    PRINT '✅ Tabela TED_TRANSFERENCIAS criada com sucesso!';
END
ELSE
BEGIN
    PRINT '⚠️ Tabela TED_TRANSFERENCIAS já existe.';
END
GO

-- ==========================================
-- Verificação Final
-- ==========================================

PRINT '';
PRINT '==========================================';
PRINT '✅ Verificação de Tabelas Criadas:';
PRINT '==========================================';

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TED_DESTINATARIOS]') AND type in (N'U'))
    PRINT '✅ TED_DESTINATARIOS: OK';
ELSE
    PRINT '❌ TED_DESTINATARIOS: FALTA CRIAR';

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TED_TRANSFERENCIAS]') AND type in (N'U'))
    PRINT '✅ TED_TRANSFERENCIAS: OK';
ELSE
    PRINT '❌ TED_TRANSFERENCIAS: FALTA CRIAR';

PRINT '';
PRINT '==========================================';
PRINT '✅ Script concluído!';
PRINT '==========================================';
GO
