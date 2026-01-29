-- ============================================
-- Script de Criação Completo - Banco mAIke_assistente
-- Versão: 1.4 (08/01/2026)
-- Baseado em: docs/PLANEJAMENTO_BANCO_DADOS_MAIKE.md
-- ============================================
-- 
-- Este script cria TODAS as tabelas do planejamento completo
-- incluindo schemas, tabelas principais, integrações, despesas,
-- validações, comunicação, IA, legislação e auditoria.
--
-- ⚠️ IMPORTANTE: Execute este script como usuário com permissões de DBA
-- ⚠️ BACKUP: Faça backup do banco antes de executar se já existir
-- ⚠️ ORDEM: Execute na ordem apresentada (dependências respeitadas)
--
-- ============================================

USE master;
GO

-- Verificar se o banco já existe
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'mAIke_assistente')
BEGIN
    PRINT 'ℹ️ Banco "mAIke_assistente" já existe. Continuando com criação de tabelas...'
END
ELSE
BEGIN
    -- Criar banco de dados
    CREATE DATABASE [mAIke_assistente]
    ON (
        NAME = 'mAIke_assistente',
        SIZE = 100MB,
        MAXSIZE = 10GB,
        FILEGROWTH = 10MB
    )
    LOG ON (
        NAME = 'mAIke_assistente_Log',
        SIZE = 10MB,
        MAXSIZE = 1GB,
        FILEGROWTH = 10%
    );
    PRINT '✅ Banco "mAIke_assistente" criado com sucesso.';
END
GO

USE [mAIke_assistente];
GO

-- ============================================
-- CRIAR SCHEMAS
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'comunicacao')
BEGIN
    EXEC('CREATE SCHEMA [comunicacao]');
    PRINT '✅ Schema [comunicacao] criado.';
END
ELSE
    PRINT 'ℹ️ Schema [comunicacao] já existe.';

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'ia')
BEGIN
    EXEC('CREATE SCHEMA [ia]');
    PRINT '✅ Schema [ia] criado.';
END
ELSE
    PRINT 'ℹ️ Schema [ia] já existe.';

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'legislacao')
BEGIN
    EXEC('CREATE SCHEMA [legislacao]');
    PRINT '✅ Schema [legislacao] criado.';
END
ELSE
    PRINT 'ℹ️ Schema [legislacao] já existe.';

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'auditoria')
BEGIN
    EXEC('CREATE SCHEMA [auditoria]');
    PRINT '✅ Schema [auditoria] criado.';
END
ELSE
    PRINT 'ℹ️ Schema [auditoria] já existe.';

GO

-- ============================================
-- FASE 1: TABELAS CRÍTICAS - COMPLIANCE E RASTREAMENTO
-- ============================================

PRINT '';
PRINT '============================================';
PRINT 'FASE 1: TABELAS CRÍTICAS - COMPLIANCE';
PRINT '============================================';
PRINT '';

-- 1. FORNECEDOR_CLIENTE (base para validações)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[FORNECEDOR_CLIENTE]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[FORNECEDOR_CLIENTE] (
        id_fornecedor_cliente BIGINT IDENTITY(1,1) PRIMARY KEY,
        cpf_cnpj VARCHAR(18) NOT NULL UNIQUE,
        tipo_pessoa VARCHAR(20) NOT NULL,
        
        razao_social VARCHAR(255),
        nome_fantasia VARCHAR(255),
        nome_completo VARCHAR(255),
        
        endereco_logradouro VARCHAR(255),
        endereco_numero VARCHAR(20),
        endereco_complemento VARCHAR(100),
        endereco_bairro VARCHAR(100),
        endereco_cidade VARCHAR(100),
        endereco_estado VARCHAR(2),
        endereco_cep VARCHAR(10),
        endereco_pais VARCHAR(3) DEFAULT 'BRA',
        
        telefone_principal VARCHAR(20),
        telefone_secundario VARCHAR(20),
        email_principal VARCHAR(255),
        email_secundario VARCHAR(255),
        site VARCHAR(255),
        
        inscricao_estadual VARCHAR(50),
        inscricao_municipal VARCHAR(50),
        situacao_cadastral VARCHAR(50),
        data_abertura DATE,
        capital_social DECIMAL(18,2),
        porte_empresa VARCHAR(50),
        
        fonte_dados VARCHAR(50),
        ultima_consulta DATETIME,
        ultima_atualizacao DATETIME,
        versao_dados INT DEFAULT 1,
        hash_dados VARCHAR(64),
        json_dados_originais NVARCHAR(MAX),
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_cpf_cnpj ON [dbo].[FORNECEDOR_CLIENTE](cpf_cnpj);
    CREATE INDEX idx_tipo_pessoa ON [dbo].[FORNECEDOR_CLIENTE](tipo_pessoa);
    CREATE INDEX idx_razao_social ON [dbo].[FORNECEDOR_CLIENTE](razao_social);
    CREATE INDEX idx_fonte_dados ON [dbo].[FORNECEDOR_CLIENTE](fonte_dados, ultima_atualizacao);
    
    PRINT '✅ Tabela FORNECEDOR_CLIENTE criada.';
END
ELSE
    PRINT 'ℹ️ Tabela FORNECEDOR_CLIENTE já existe.';

GO

-- 2. MOVIMENTACAO_BANCARIA (base para tudo)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MOVIMENTACAO_BANCARIA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[MOVIMENTACAO_BANCARIA] (
        id_movimentacao BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        banco_origem VARCHAR(50) NOT NULL,
        agencia_origem VARCHAR(20),
        conta_origem VARCHAR(50),
        tipo_conta_origem VARCHAR(20),
        
        agencia_destino VARCHAR(20),
        conta_destino VARCHAR(50),
        tipo_conta_destino VARCHAR(20),
        
        data_movimentacao DATETIME NOT NULL,
        data_lancamento DATETIME,
        tipo_movimentacao VARCHAR(50),
        sinal_movimentacao VARCHAR(1) NOT NULL,
        valor_movimentacao DECIMAL(18,2) NOT NULL,
        moeda VARCHAR(3) DEFAULT 'BRL',
        
        -- Contrapartida (CRÍTICO PARA COMPLIANCE)
        cpf_cnpj_contrapartida VARCHAR(18),
        nome_contrapartida VARCHAR(255),
        tipo_pessoa_contrapartida VARCHAR(20),
        banco_contrapartida VARCHAR(50),
        agencia_contrapartida VARCHAR(20),
        conta_contrapartida VARCHAR(50),
        dv_conta_contrapartida VARCHAR(5),
        
        -- Validação da Contrapartida (CRÍTICO)
        contrapartida_validada BIT DEFAULT 0,
        data_validacao_contrapartida DATETIME,
        fonte_validacao_contrapartida VARCHAR(50),
        nome_validado_contrapartida VARCHAR(255),
        
        descricao_movimentacao TEXT,
        historico_codigo VARCHAR(20),
        historico_descricao VARCHAR(255),
        informacoes_complementares TEXT,
        
        -- ⚠️ NOTA: Para relacionar um lançamento a múltiplos processos, usar tabela MOVIMENTACAO_BANCARIA_PROCESSO
        processo_referencia VARCHAR(50),
        tipo_relacionamento VARCHAR(50),
        
        -- Classificação Contábil e Histórico
        plano_contas_codigo VARCHAR(50),
        plano_contas_descricao VARCHAR(255),
        historico_interno VARCHAR(255),
        centro_custo VARCHAR(100),
        
        fonte_dados VARCHAR(50),
        ultima_sincronizacao DATETIME,
        versao_dados INT DEFAULT 1,
        hash_dados VARCHAR(64),
        json_dados_originais NVARCHAR(MAX),
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_banco_origem ON [dbo].[MOVIMENTACAO_BANCARIA](banco_origem, data_movimentacao);
    CREATE INDEX idx_data_movimentacao ON [dbo].[MOVIMENTACAO_BANCARIA](data_movimentacao);
    CREATE INDEX idx_tipo_movimentacao ON [dbo].[MOVIMENTACAO_BANCARIA](tipo_movimentacao);
    CREATE INDEX idx_processo ON [dbo].[MOVIMENTACAO_BANCARIA](processo_referencia);
    CREATE INDEX idx_contrapartida ON [dbo].[MOVIMENTACAO_BANCARIA](cpf_cnpj_contrapartida);
    CREATE INDEX idx_fonte_dados ON [dbo].[MOVIMENTACAO_BANCARIA](fonte_dados, ultima_sincronizacao);
    CREATE INDEX idx_plano_contas ON [dbo].[MOVIMENTACAO_BANCARIA](plano_contas_codigo);
    CREATE INDEX idx_historico_interno ON [dbo].[MOVIMENTACAO_BANCARIA](historico_interno);
    CREATE INDEX idx_centro_custo ON [dbo].[MOVIMENTACAO_BANCARIA](centro_custo);
    
    PRINT '✅ Tabela MOVIMENTACAO_BANCARIA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela MOVIMENTACAO_BANCARIA já existe.';

GO

-- 3. PROCESSO_IMPORTACAO (atualizar se já existir)
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PROCESSO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    PRINT 'ℹ️ Tabela PROCESSO_IMPORTACAO já existe. Verifique se precisa atualizar campos.';
    PRINT '   Use script de migração separado para adicionar campos faltantes.';
END
ELSE
BEGIN
    -- Criar versão completa (ver planejamento para campos completos)
    -- Por enquanto, criar estrutura básica - migração completa será em script separado
    CREATE TABLE [dbo].[PROCESSO_IMPORTACAO] (
        id_processo BIGINT IDENTITY(1,1) PRIMARY KEY,
        processo_referencia VARCHAR(50) NOT NULL UNIQUE,
        categoria_processo VARCHAR(10) NOT NULL,
        numero_processo VARCHAR(20),
        ano_processo VARCHAR(4),
        
        -- ⚠️ VALORES: 'ATIVO' (no Kanban), 'ARQUIVADO' (finalizado), 'ENTREGUE', 'CANCELADO'
        status_atual VARCHAR(100),
        status_anterior VARCHAR(100),
        situacao_processo VARCHAR(100),
        situacao_ce VARCHAR(100),
        situacao_di VARCHAR(100),
        situacao_duimp VARCHAR(100),
        
        data_criacao_processo DATETIME,
        data_ultima_atualizacao DATETIME,
        data_chegada DATETIME,
        data_eta DATETIME,
        data_desembaraco DATETIME,
        data_prevista_desembaraco DATETIME,
        data_destino_final DATETIME,
        
        modal_transporte VARCHAR(20),
        porto_origem_codigo VARCHAR(10),
        porto_origem_nome VARCHAR(255),
        porto_destino_codigo VARCHAR(10),
        porto_destino_nome VARCHAR(255),
        nome_navio VARCHAR(255),
        numero_viagem VARCHAR(50),
        
        eta_shipsgo DATETIME,
        porto_shipsgo_codigo VARCHAR(10),
        porto_shipsgo_nome VARCHAR(255),
        status_shipsgo VARCHAR(100),
        shipsgo_ultima_atualizacao DATETIME,
        
        numero_ce VARCHAR(50),
        numero_cct VARCHAR(50),
        numero_di VARCHAR(50),
        numero_duimp VARCHAR(50),
        numero_dta VARCHAR(50),
        numero_lpco VARCHAR(50),
        situacao_lpco VARCHAR(100),
        
        valor_fob_usd DECIMAL(18,2),
        valor_fob_brl DECIMAL(18,2),
        valor_frete_usd DECIMAL(18,2),
        valor_frete_brl DECIMAL(18,2),
        valor_seguro_usd DECIMAL(18,2),
        valor_seguro_brl DECIMAL(18,2),
        valor_cif_usd DECIMAL(18,2),
        valor_cif_brl DECIMAL(18,2),
        moeda_codigo VARCHAR(3) DEFAULT 'USD',
        taxa_cambio DECIMAL(10,6),
        
        fornecedor_cnpj VARCHAR(18),
        fornecedor_razao_social VARCHAR(255),
        cliente_cnpj VARCHAR(18),
        cliente_razao_social VARCHAR(255),
        
        tem_pendencia_icms BIT DEFAULT 0,
        tem_pendencia_frete BIT DEFAULT 0,
        tem_pendencia_afrmm BIT DEFAULT 0,
        tem_pendencia_lpco BIT DEFAULT 0,
        tem_bloqueio_ce BIT DEFAULT 0,
        descricao_pendencias TEXT,
        
        fonte_dados VARCHAR(50),
        ultima_sincronizacao DATETIME,
        versao_dados INT DEFAULT 1,
        hash_dados VARCHAR(64),
        json_dados_originais NVARCHAR(MAX),
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_processo_referencia ON [dbo].[PROCESSO_IMPORTACAO](processo_referencia);
    CREATE INDEX idx_categoria ON [dbo].[PROCESSO_IMPORTACAO](categoria_processo);
    CREATE INDEX idx_status ON [dbo].[PROCESSO_IMPORTACAO](status_atual);
    CREATE INDEX idx_data_chegada ON [dbo].[PROCESSO_IMPORTACAO](data_chegada);
    CREATE INDEX idx_eta ON [dbo].[PROCESSO_IMPORTACAO](data_eta);
    CREATE INDEX idx_desembaraco ON [dbo].[PROCESSO_IMPORTACAO](data_desembaraco);
    CREATE INDEX idx_fonte_dados ON [dbo].[PROCESSO_IMPORTACAO](fonte_dados, ultima_sincronizacao);
    CREATE INDEX idx_fornecedor ON [dbo].[PROCESSO_IMPORTACAO](fornecedor_cnpj);
    CREATE INDEX idx_cliente ON [dbo].[PROCESSO_IMPORTACAO](cliente_cnpj);
    
    PRINT '✅ Tabela PROCESSO_IMPORTACAO criada.';
END

GO

-- 4. MOVIMENTACAO_BANCARIA_PROCESSO (N:N)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MOVIMENTACAO_BANCARIA_PROCESSO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO] (
        id_relacionamento BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        id_movimentacao_bancaria BIGINT NOT NULL,
        processo_referencia VARCHAR(50),
        categoria_processo VARCHAR(10),
        
        valor_parcela DECIMAL(18,2) NOT NULL,
        moeda VARCHAR(3) DEFAULT 'BRL',
        percentual_parcela DECIMAL(5,2),
        
        tipo_relacionamento VARCHAR(50),
        tipo_relacionamento_descricao VARCHAR(255),
        
        nivel_vinculo VARCHAR(20),
        
        id_despesa_processo BIGINT,
        
        status_vinculo VARCHAR(20) DEFAULT 'ativo',
        
        validado_por VARCHAR(100),
        data_validacao DATETIME,
        observacoes_validacao TEXT,
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_movimentacao ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](id_movimentacao_bancaria);
    CREATE INDEX idx_processo ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](processo_referencia);
    CREATE INDEX idx_categoria ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](categoria_processo);
    CREATE INDEX idx_nivel_vinculo ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](nivel_vinculo, categoria_processo);
    CREATE INDEX idx_tipo_relacionamento ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](tipo_relacionamento);
    CREATE INDEX idx_status ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](status_vinculo);
    CREATE INDEX idx_despesa ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](id_despesa_processo);
    
    PRINT '✅ Tabela MOVIMENTACAO_BANCARIA_PROCESSO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela MOVIMENTACAO_BANCARIA_PROCESSO já existe.';

GO

-- 5. RASTREAMENTO_RECURSO (com campos de origem completos)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[RASTREAMENTO_RECURSO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[RASTREAMENTO_RECURSO] (
        id_rastreamento BIGINT IDENTITY(1,1) PRIMARY KEY,
        processo_referencia VARCHAR(50) NOT NULL,
        
        origem_recurso VARCHAR(50) NOT NULL,
        origem_recurso_descricao VARCHAR(255),
        tipo_recurso VARCHAR(50),
        
        -- ⚠️ IDENTIFICAÇÃO COMPLETA DA ORIGEM (CRÍTICO PARA COMPLIANCE)
        cpf_cnpj_origem VARCHAR(18),
        nome_origem VARCHAR(255),
        endereco_origem TEXT,
        banco_origem VARCHAR(50),
        agencia_origem VARCHAR(20),
        conta_origem VARCHAR(50),
        documento_comprovante VARCHAR(255),
        
        valor_recurso_usd DECIMAL(18,2),
        valor_recurso_brl DECIMAL(18,2),
        moeda VARCHAR(3) DEFAULT 'USD',
        taxa_cambio DECIMAL(10,6),
        
        id_movimentacao_bancaria BIGINT,
        id_despesa_processo BIGINT,
        
        data_origem DATETIME,
        data_aplicacao DATETIME,
        
        status_rastreamento VARCHAR(20) DEFAULT 'ativo',
        
        -- Validação
        origem_validada BIT DEFAULT 0,
        data_validacao_origem DATETIME,
        fonte_validacao VARCHAR(50),
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_processo ON [dbo].[RASTREAMENTO_RECURSO](processo_referencia);
    CREATE INDEX idx_origem ON [dbo].[RASTREAMENTO_RECURSO](origem_recurso);
    CREATE INDEX idx_tipo ON [dbo].[RASTREAMENTO_RECURSO](tipo_recurso);
    CREATE INDEX idx_data_aplicacao ON [dbo].[RASTREAMENTO_RECURSO](data_aplicacao);
    CREATE INDEX idx_cpf_cnpj_origem ON [dbo].[RASTREAMENTO_RECURSO](cpf_cnpj_origem);
    CREATE INDEX idx_origem_validada ON [dbo].[RASTREAMENTO_RECURSO](origem_validada, data_validacao_origem);
    
    PRINT '✅ Tabela RASTREAMENTO_RECURSO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela RASTREAMENTO_RECURSO já existe.';

GO

-- 6. DESPESA_PROCESSO (com suporte a categoria)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[DESPESA_PROCESSO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[DESPESA_PROCESSO] (
        id_despesa BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        processo_referencia VARCHAR(50),
        categoria_processo VARCHAR(10),
        
        tipo_despesa VARCHAR(50) NOT NULL,
        tipo_despesa_descricao VARCHAR(255),
        categoria_despesa VARCHAR(50),
        
        nivel_vinculo VARCHAR(20) NOT NULL,
        
        valor_previsto_usd DECIMAL(18,2),
        valor_previsto_brl DECIMAL(18,2),
        valor_realizado_usd DECIMAL(18,2),
        valor_realizado_brl DECIMAL(18,2),
        moeda VARCHAR(3) DEFAULT 'USD',
        taxa_cambio DECIMAL(10,6),
        
        status_despesa VARCHAR(20) DEFAULT 'prevista',
        data_prevista_pagamento DATE,
        data_real_pagamento DATE,
        
        id_movimentacao_bancaria BIGINT,
        conciliado BIT DEFAULT 0,
        
        fonte_dados VARCHAR(50),
        observacoes TEXT,
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_processo ON [dbo].[DESPESA_PROCESSO](processo_referencia, tipo_despesa);
    CREATE INDEX idx_categoria ON [dbo].[DESPESA_PROCESSO](categoria_processo, tipo_despesa);
    CREATE INDEX idx_nivel_vinculo ON [dbo].[DESPESA_PROCESSO](nivel_vinculo, categoria_processo);
    CREATE INDEX idx_status ON [dbo].[DESPESA_PROCESSO](status_despesa);
    CREATE INDEX idx_data_pagamento ON [dbo].[DESPESA_PROCESSO](data_real_pagamento);
    CREATE INDEX idx_conciliado ON [dbo].[DESPESA_PROCESSO](conciliado);
    
    PRINT '✅ Tabela DESPESA_PROCESSO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela DESPESA_PROCESSO já existe.';

GO

-- 7. CONCILIACAO_BANCARIA (com suporte a categoria)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CONCILIACAO_BANCARIA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[CONCILIACAO_BANCARIA] (
        id_conciliacao BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        id_movimentacao_bancaria BIGINT NOT NULL,
        processo_referencia VARCHAR(50),
        categoria_processo VARCHAR(10),
        id_despesa_processo BIGINT,
        
        tipo_conciliacao VARCHAR(50),
        tipo_relacionamento VARCHAR(50),
        
        nivel_vinculo VARCHAR(20),
        
        valor_movimentacao DECIMAL(18,2) NOT NULL,
        valor_despesa DECIMAL(18,2),
        diferenca_valor DECIMAL(18,2),
        percentual_diferenca DECIMAL(5,2),
        
        status_conciliacao VARCHAR(20) DEFAULT 'pendente',
        confianca_conciliacao DECIMAL(5,2),
        
        match_valor BIT DEFAULT 0,
        match_contrapartida BIT DEFAULT 0,
        match_data BIT DEFAULT 0,
        match_descricao BIT DEFAULT 0,
        
        validado_por VARCHAR(100),
        data_validacao DATETIME,
        observacoes_validacao TEXT,
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_movimentacao ON [dbo].[CONCILIACAO_BANCARIA](id_movimentacao_bancaria);
    CREATE INDEX idx_processo ON [dbo].[CONCILIACAO_BANCARIA](processo_referencia);
    CREATE INDEX idx_categoria ON [dbo].[CONCILIACAO_BANCARIA](categoria_processo);
    CREATE INDEX idx_nivel_vinculo ON [dbo].[CONCILIACAO_BANCARIA](nivel_vinculo, categoria_processo);
    CREATE INDEX idx_status ON [dbo].[CONCILIACAO_BANCARIA](status_conciliacao);
    CREATE INDEX idx_data_validacao ON [dbo].[CONCILIACAO_BANCARIA](data_validacao);
    
    PRINT '✅ Tabela CONCILIACAO_BANCARIA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela CONCILIACAO_BANCARIA já existe.';

GO

-- 8. COMPROVANTE_RECURSO (NOVO - para arquivar comprovantes)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[COMPROVANTE_RECURSO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[COMPROVANTE_RECURSO] (
        id_comprovante BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        id_rastreamento_recurso BIGINT,
        id_movimentacao_bancaria BIGINT,
        
        tipo_comprovante VARCHAR(50),
        numero_comprovante VARCHAR(100),
        data_comprovante DATETIME,
        valor_comprovante DECIMAL(18,2),
        
        caminho_arquivo VARCHAR(500),
        hash_arquivo VARCHAR(64),
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_rastreamento ON [dbo].[COMPROVANTE_RECURSO](id_rastreamento_recurso);
    CREATE INDEX idx_movimentacao ON [dbo].[COMPROVANTE_RECURSO](id_movimentacao_bancaria);
    CREATE INDEX idx_tipo ON [dbo].[COMPROVANTE_RECURSO](tipo_comprovante);
    CREATE INDEX idx_numero ON [dbo].[COMPROVANTE_RECURSO](numero_comprovante);
    
    PRINT '✅ Tabela COMPROVANTE_RECURSO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela COMPROVANTE_RECURSO já existe.';

GO

-- 9. VALIDACAO_ORIGEM_RECURSO (NOVO - para registrar validações)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[VALIDACAO_ORIGEM_RECURSO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[VALIDACAO_ORIGEM_RECURSO] (
        id_validacao BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        id_rastreamento_recurso BIGINT,
        id_movimentacao_bancaria BIGINT,
        
        tipo_validacao VARCHAR(50),
        status_validacao VARCHAR(20) DEFAULT 'pendente',
        resultado_validacao TEXT,
        fonte_validacao VARCHAR(50),
        
        dados_validados NVARCHAR(MAX),
        observacoes TEXT,
        
        validado_por VARCHAR(100),
        data_validacao DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_rastreamento ON [dbo].[VALIDACAO_ORIGEM_RECURSO](id_rastreamento_recurso);
    CREATE INDEX idx_movimentacao ON [dbo].[VALIDACAO_ORIGEM_RECURSO](id_movimentacao_bancaria);
    CREATE INDEX idx_tipo_validacao ON [dbo].[VALIDACAO_ORIGEM_RECURSO](tipo_validacao);
    CREATE INDEX idx_status ON [dbo].[VALIDACAO_ORIGEM_RECURSO](status_validacao);
    CREATE INDEX idx_data_validacao ON [dbo].[VALIDACAO_ORIGEM_RECURSO](data_validacao);
    
    PRINT '✅ Tabela VALIDACAO_ORIGEM_RECURSO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela VALIDACAO_ORIGEM_RECURSO já existe.';

GO

PRINT '';
PRINT '✅✅✅ FASE 1 CONCLUÍDA: Tabelas críticas de compliance criadas!';
PRINT '';

-- ============================================
-- FASE 2: TABELAS DE ESTRUTURA BASE
-- ============================================

PRINT '============================================';
PRINT 'FASE 2: TABELAS DE ESTRUTURA BASE';
PRINT '============================================';
PRINT '';

-- 10. DOCUMENTO_ADUANEIRO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[DOCUMENTO_ADUANEIRO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[DOCUMENTO_ADUANEIRO] (
        id_documento BIGINT IDENTITY(1,1) PRIMARY KEY,
        numero_documento VARCHAR(50) NOT NULL,
        tipo_documento VARCHAR(50) NOT NULL,
        tipo_documento_descricao VARCHAR(100),
        versao_documento VARCHAR(10),
        
        processo_referencia VARCHAR(50),
        id_importacao BIGINT,
        
        status_documento VARCHAR(100),
        status_documento_codigo VARCHAR(20),
        canal_documento VARCHAR(20),
        situacao_documento VARCHAR(100),
        
        data_registro DATETIME,
        data_situacao DATETIME,
        data_desembaraco DATETIME,
        data_prevista_desembaraco DATETIME,
        data_entrega_carga DATETIME,
        
        valor_fob_usd DECIMAL(18,2),
        valor_fob_brl DECIMAL(18,2),
        valor_frete_usd DECIMAL(18,2),
        valor_frete_brl DECIMAL(18,2),
        valor_seguro_usd DECIMAL(18,2),
        valor_seguro_brl DECIMAL(18,2),
        valor_cif_usd DECIMAL(18,2),
        valor_cif_brl DECIMAL(18,2),
        moeda_codigo VARCHAR(3) DEFAULT 'USD',
        taxa_cambio DECIMAL(10,6),
        
        valor_ii_usd DECIMAL(18,2),
        valor_ii_brl DECIMAL(18,2),
        valor_ipi_usd DECIMAL(18,2),
        valor_ipi_brl DECIMAL(18,2),
        valor_pis_usd DECIMAL(18,2),
        valor_pis_brl DECIMAL(18,2),
        valor_cofins_usd DECIMAL(18,2),
        valor_cofins_brl DECIMAL(18,2),
        valor_antidumping_usd DECIMAL(18,2),
        valor_antidumping_brl DECIMAL(18,2),
        valor_taxa_siscomex_usd DECIMAL(18,2),
        valor_taxa_siscomex_brl DECIMAL(18,2),
        total_impostos_usd DECIMAL(18,2),
        total_impostos_brl DECIMAL(18,2),
        
        porto_origem_codigo VARCHAR(10),
        porto_origem_nome VARCHAR(255),
        porto_destino_codigo VARCHAR(10),
        porto_destino_nome VARCHAR(255),
        pais_procedencia VARCHAR(3),
        pais_procedencia_nome VARCHAR(255),
        nome_navio VARCHAR(255),
        numero_viagem VARCHAR(50),
        tipo_transporte VARCHAR(20),
        
        descricao_mercadoria TEXT,
        quantidade_itens INT,
        peso_bruto DECIMAL(18,3),
        peso_liquido DECIMAL(18,3),
        volume DECIMAL(18,3),
        
        fonte_dados VARCHAR(50),
        ultima_sincronizacao DATETIME,
        versao_dados INT DEFAULT 1,
        hash_dados VARCHAR(64),
        json_dados_originais NVARCHAR(MAX),
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_numero_documento ON [dbo].[DOCUMENTO_ADUANEIRO](numero_documento);
    CREATE INDEX idx_tipo_documento ON [dbo].[DOCUMENTO_ADUANEIRO](tipo_documento);
    CREATE INDEX idx_processo ON [dbo].[DOCUMENTO_ADUANEIRO](processo_referencia);
    CREATE INDEX idx_status ON [dbo].[DOCUMENTO_ADUANEIRO](status_documento);
    CREATE INDEX idx_canal ON [dbo].[DOCUMENTO_ADUANEIRO](canal_documento);
    CREATE INDEX idx_data_desembaraco ON [dbo].[DOCUMENTO_ADUANEIRO](data_desembaraco);
    CREATE INDEX idx_fonte_dados ON [dbo].[DOCUMENTO_ADUANEIRO](fonte_dados, ultima_sincronizacao);
    
    PRINT '✅ Tabela DOCUMENTO_ADUANEIRO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela DOCUMENTO_ADUANEIRO já existe.';

GO

-- 11. TIMELINE_PROCESSO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TIMELINE_PROCESSO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[TIMELINE_PROCESSO] (
        id_timeline BIGINT IDENTITY(1,1) PRIMARY KEY,
        processo_referencia VARCHAR(50) NOT NULL,
        
        data_evento DATETIME NOT NULL,
        tipo_evento VARCHAR(50) NOT NULL,
        tipo_evento_descricao VARCHAR(255),
        
        valor_anterior VARCHAR(255),
        valor_novo VARCHAR(255),
        campo_alterado VARCHAR(100),
        
        usuario_ou_sistema VARCHAR(100),
        fonte_dados VARCHAR(50),
        
        observacoes TEXT,
        json_dados_originais NVARCHAR(MAX),
        
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_processo ON [dbo].[TIMELINE_PROCESSO](processo_referencia, data_evento DESC);
    CREATE INDEX idx_tipo_evento ON [dbo].[TIMELINE_PROCESSO](tipo_evento, data_evento DESC);
    CREATE INDEX idx_campo_alterado ON [dbo].[TIMELINE_PROCESSO](campo_alterado, data_evento DESC);
    
    PRINT '✅ Tabela TIMELINE_PROCESSO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela TIMELINE_PROCESSO já existe.';

GO

-- 12. SHIPSGO_TRACKING
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[SHIPSGO_TRACKING]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[SHIPSGO_TRACKING] (
        id_tracking BIGINT IDENTITY(1,1) PRIMARY KEY,
        processo_referencia VARCHAR(50) NOT NULL UNIQUE,
        
        eta_iso DATETIME,
        porto_codigo VARCHAR(10),
        porto_nome VARCHAR(255),
        status VARCHAR(100),
        
        payload_raw NVARCHAR(MAX),
        
        ultima_sincronizacao DATETIME,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_processo ON [dbo].[SHIPSGO_TRACKING](processo_referencia);
    CREATE INDEX idx_eta ON [dbo].[SHIPSGO_TRACKING](eta_iso);
    CREATE INDEX idx_porto ON [dbo].[SHIPSGO_TRACKING](porto_codigo);
    
    PRINT '✅ Tabela SHIPSGO_TRACKING criada.';
END
ELSE
    PRINT 'ℹ️ Tabela SHIPSGO_TRACKING já existe.';

GO

PRINT '';
-- 12. HISTORICO_DOCUMENTO_ADUANEIRO (NOVO - histórico de mudanças em documentos)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO] (
        id_historico BIGINT IDENTITY(1,1) PRIMARY KEY,
        id_documento BIGINT,
        numero_documento VARCHAR(50) NOT NULL,
        tipo_documento VARCHAR(50) NOT NULL,
        
        processo_referencia VARCHAR(50),
        
        data_evento DATETIME NOT NULL,
        tipo_evento VARCHAR(50) NOT NULL,
        tipo_evento_descricao VARCHAR(255),
        
        campo_alterado VARCHAR(100) NOT NULL,
        valor_anterior VARCHAR(500),
        valor_novo VARCHAR(500),
        
        status_documento VARCHAR(100),
        status_documento_codigo VARCHAR(20),
        canal_documento VARCHAR(20),
        situacao_documento VARCHAR(100),
        
        data_registro DATETIME,
        data_situacao DATETIME,
        data_desembaraco DATETIME,
        
        fonte_dados VARCHAR(50) NOT NULL,
        api_endpoint VARCHAR(500),
        json_dados_originais NVARCHAR(MAX),
        
        usuario_ou_sistema VARCHAR(100),
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](id_documento, data_evento DESC);
    CREATE INDEX idx_numero_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](numero_documento, tipo_documento, data_evento DESC);
    CREATE INDEX idx_processo ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](processo_referencia, data_evento DESC);
    CREATE INDEX idx_tipo_evento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](tipo_evento, data_evento DESC);
    CREATE INDEX idx_campo_alterado ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](campo_alterado, data_evento DESC);
    CREATE INDEX idx_fonte_dados ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](fonte_dados, data_evento DESC);
    
    PRINT '✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela HISTORICO_DOCUMENTO_ADUANEIRO já existe.';

GO

PRINT '';
PRINT '✅✅✅ FASE 2 CONCLUÍDA: Tabelas de estrutura base criadas!';
PRINT '';

-- ============================================
-- FASE 3: TABELAS DE INTEGRAÇÃO E VALIDAÇÃO
-- ============================================

PRINT '============================================';
PRINT 'FASE 3: TABELAS DE INTEGRAÇÃO E VALIDAÇÃO';
PRINT '============================================';
PRINT '';

-- 13. CONSULTA_BILHETADA
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CONSULTA_BILHETADA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[CONSULTA_BILHETADA] (
        id_consulta BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        tipo_consulta VARCHAR(50) NOT NULL,
        numero_documento VARCHAR(50),
        endpoint VARCHAR(500) NOT NULL,
        metodo VARCHAR(10) DEFAULT 'GET',
        
        status_code INT,
        sucesso BIT DEFAULT 1,
        data_consulta DATETIME DEFAULT GETDATE(),
        
        processo_referencia VARCHAR(50),
        
        usou_api_publica_antes BIT DEFAULT 0,
        data_verificacao_publica DATETIME,
        
        observacoes TEXT
    );
    
    CREATE INDEX idx_tipo_consulta ON [dbo].[CONSULTA_BILHETADA](tipo_consulta, data_consulta);
    CREATE INDEX idx_processo ON [dbo].[CONSULTA_BILHETADA](processo_referencia);
    CREATE INDEX idx_data_consulta ON [dbo].[CONSULTA_BILHETADA](data_consulta);
    
    PRINT '✅ Tabela CONSULTA_BILHETADA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela CONSULTA_BILHETADA já existe.';

GO

-- 14. CONSULTA_BILHETADA_PENDENTE
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CONSULTA_BILHETADA_PENDENTE]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[CONSULTA_BILHETADA_PENDENTE] (
        id_pendente BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        tipo_consulta VARCHAR(50) NOT NULL,
        numero_documento VARCHAR(50) NOT NULL,
        endpoint VARCHAR(500) NOT NULL,
        metodo VARCHAR(10) DEFAULT 'GET',
        
        processo_referencia VARCHAR(50),
        
        motivo TEXT,
        data_publica_verificada DATETIME,
        data_ultima_alteracao_cache DATETIME,
        
        status VARCHAR(20) DEFAULT 'pendente',
        aprovado_em DATETIME,
        aprovado_por VARCHAR(100),
        processando_aprovacao DATETIME,
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_status ON [dbo].[CONSULTA_BILHETADA_PENDENTE](status, criado_em);
    CREATE INDEX idx_tipo_consulta ON [dbo].[CONSULTA_BILHETADA_PENDENTE](tipo_consulta, numero_documento);
    
    PRINT '✅ Tabela CONSULTA_BILHETADA_PENDENTE criada.';
END
ELSE
    PRINT 'ℹ️ Tabela CONSULTA_BILHETADA_PENDENTE já existe.';

GO

-- 15. VALIDACAO_DADOS_OFICIAIS
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[VALIDACAO_DADOS_OFICIAIS]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[VALIDACAO_DADOS_OFICIAIS] (
        id_validacao BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        tipo_entidade VARCHAR(50) NOT NULL,
        id_entidade VARCHAR(100) NOT NULL,
        
        api_oficial VARCHAR(50) NOT NULL,
        endpoint_consulta VARCHAR(500),
        data_consulta DATETIME DEFAULT GETDATE(),
        
        campo_validado VARCHAR(100) NOT NULL,
        valor_armazenado VARCHAR(500),
        valor_oficial VARCHAR(500),
        valores_iguais BIT,
        diferenca_valor VARCHAR(500),
        
        status_validacao VARCHAR(20) DEFAULT 'pendente',
        acao_tomada VARCHAR(100),
        
        observacoes TEXT,
        json_resposta_oficial NVARCHAR(MAX),
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_entidade ON [dbo].[VALIDACAO_DADOS_OFICIAIS](tipo_entidade, id_entidade);
    CREATE INDEX idx_api_oficial ON [dbo].[VALIDACAO_DADOS_OFICIAIS](api_oficial, data_consulta DESC);
    CREATE INDEX idx_status ON [dbo].[VALIDACAO_DADOS_OFICIAIS](status_validacao);
    CREATE INDEX idx_campo ON [dbo].[VALIDACAO_DADOS_OFICIAIS](campo_validado);
    
    PRINT '✅ Tabela VALIDACAO_DADOS_OFICIAIS criada.';
END
ELSE
    PRINT 'ℹ️ Tabela VALIDACAO_DADOS_OFICIAIS já existe.';

GO

-- 16. VERIFICACAO_AUTOMATICA
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[VERIFICACAO_AUTOMATICA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[VERIFICACAO_AUTOMATICA] (
        id_verificacao BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        tipo_verificacao VARCHAR(50) NOT NULL,
        entidade_tipo VARCHAR(50) NOT NULL,
        filtro_entidades NVARCHAR(MAX),
        
        frequencia_verificacao VARCHAR(50),
        proxima_execucao DATETIME,
        ultima_execucao DATETIME,
        
        total_entidades_verificadas INT DEFAULT 0,
        total_divergencias_encontradas INT DEFAULT 0,
        total_atualizacoes_realizadas INT DEFAULT 0,
        total_erros INT DEFAULT 0,
        
        status_verificacao VARCHAR(20) DEFAULT 'ativa',
        ultima_execucao_status VARCHAR(20),
        mensagem_erro TEXT,
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_tipo_verificacao ON [dbo].[VERIFICACAO_AUTOMATICA](tipo_verificacao);
    CREATE INDEX idx_proxima_execucao ON [dbo].[VERIFICACAO_AUTOMATICA](proxima_execucao);
    CREATE INDEX idx_status ON [dbo].[VERIFICACAO_AUTOMATICA](status_verificacao);
    
    PRINT '✅ Tabela VERIFICACAO_AUTOMATICA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela VERIFICACAO_AUTOMATICA já existe.';

GO

PRINT '';
PRINT '✅✅✅ FASE 3 CONCLUÍDA: Tabelas de integração e validação criadas!';
PRINT '';

-- ============================================
-- FASE 4: TABELAS DE COMUNICAÇÃO
-- ============================================

PRINT '============================================';
PRINT 'FASE 4: TABELAS DE COMUNICAÇÃO';
PRINT '============================================';
PRINT '';

-- 17. EMAIL_ENVIADO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[comunicacao].[EMAIL_ENVIADO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [comunicacao].[EMAIL_ENVIADO] (
        id_email BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        email_destinatario VARCHAR(255) NOT NULL,
        nome_destinatario VARCHAR(255),
        
        assunto VARCHAR(500) NOT NULL,
        corpo_email TEXT NOT NULL,
        corpo_html TEXT,
        
        tipo_email VARCHAR(50),
        template_usado VARCHAR(100),
        
        processo_referencia VARCHAR(50),
        session_id VARCHAR(100),
        
        status_envio VARCHAR(20) DEFAULT 'enviado',
        data_envio DATETIME DEFAULT GETDATE(),
        mensagem_erro TEXT,
        
        confirmado_antes_envio BIT DEFAULT 1,
        data_confirmacao DATETIME,
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_destinatario ON [comunicacao].[EMAIL_ENVIADO](email_destinatario, data_envio DESC);
    CREATE INDEX idx_tipo_email ON [comunicacao].[EMAIL_ENVIADO](tipo_email, data_envio DESC);
    CREATE INDEX idx_processo ON [comunicacao].[EMAIL_ENVIADO](processo_referencia);
    CREATE INDEX idx_status ON [comunicacao].[EMAIL_ENVIADO](status_envio);
    
    PRINT '✅ Tabela EMAIL_ENVIADO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela EMAIL_ENVIADO já existe.';

GO

-- 18. EMAIL_AGENDADO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[comunicacao].[EMAIL_AGENDADO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [comunicacao].[EMAIL_AGENDADO] (
        id_agendamento BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        email_destinatario VARCHAR(255) NOT NULL,
        nome_destinatario VARCHAR(255),
        
        assunto VARCHAR(500) NOT NULL,
        corpo_email TEXT NOT NULL,
        corpo_html TEXT,
        
        data_agendamento DATETIME NOT NULL,
        tipo_agendamento VARCHAR(50),
        recorrente BIT DEFAULT 0,
        proxima_execucao DATETIME,
        
        status VARCHAR(20) DEFAULT 'agendado',
        tentativas INT DEFAULT 0,
        ultima_tentativa DATETIME,
        mensagem_erro TEXT,
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_data_agendamento ON [comunicacao].[EMAIL_AGENDADO](data_agendamento);
    CREATE INDEX idx_status ON [comunicacao].[EMAIL_AGENDADO](status);
    CREATE INDEX idx_proxima_execucao ON [comunicacao].[EMAIL_AGENDADO](proxima_execucao);
    
    PRINT '✅ Tabela EMAIL_AGENDADO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela EMAIL_AGENDADO já existe.';

GO

-- 19. WHATSAPP_MENSAGEM
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[comunicacao].[WHATSAPP_MENSAGEM]') AND type in (N'U'))
BEGIN
    CREATE TABLE [comunicacao].[WHATSAPP_MENSAGEM] (
        id_mensagem BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        numero_whatsapp VARCHAR(20) NOT NULL,
        nome_contato VARCHAR(255),
        
        tipo_mensagem VARCHAR(20) DEFAULT 'texto',
        conteudo_mensagem TEXT,
        url_anexo VARCHAR(500),
        
        processo_referencia VARCHAR(50),
        session_id VARCHAR(100),
        
        status_envio VARCHAR(20) DEFAULT 'pendente',
        data_envio DATETIME,
        data_entrega DATETIME,
        data_leitura DATETIME,
        mensagem_erro TEXT,
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_numero ON [comunicacao].[WHATSAPP_MENSAGEM](numero_whatsapp, data_envio DESC);
    CREATE INDEX idx_status ON [comunicacao].[WHATSAPP_MENSAGEM](status_envio);
    CREATE INDEX idx_processo ON [comunicacao].[WHATSAPP_MENSAGEM](processo_referencia);
    
    PRINT '✅ Tabela WHATSAPP_MENSAGEM criada.';
END
ELSE
    PRINT 'ℹ️ Tabela WHATSAPP_MENSAGEM já existe.';

GO

PRINT '';
PRINT '✅✅✅ FASE 4 CONCLUÍDA: Tabelas de comunicação criadas!';
PRINT '';

-- ============================================
-- FASE 5: TABELAS DE IA E APRENDIZADO
-- ============================================

PRINT '============================================';
PRINT 'FASE 5: TABELAS DE IA E APRENDIZADO';
PRINT '============================================';
PRINT '';

-- 20. CONVERSA_CHAT
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[ia].[CONVERSA_CHAT]') AND type in (N'U'))
BEGIN
    CREATE TABLE [ia].[CONVERSA_CHAT] (
        id_conversa BIGINT IDENTITY(1,1) PRIMARY KEY,
        session_id VARCHAR(100) NOT NULL,
        
        mensagem_usuario TEXT NOT NULL,
        resposta_ia TEXT NOT NULL,
        
        tipo_conversa VARCHAR(50),
        processo_referencia VARCHAR(50),
        categoria_processo VARCHAR(10),
        
        importante BIT DEFAULT 0,
        tags VARCHAR(500),
        
        modelo_ia_usado VARCHAR(50),
        tempo_resposta_ms INT,
        tokens_usados INT,
        custo_estimado DECIMAL(10,6),
        
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_session ON [ia].[CONVERSA_CHAT](session_id, criado_em DESC);
    CREATE INDEX idx_tipo_conversa ON [ia].[CONVERSA_CHAT](tipo_conversa);
    CREATE INDEX idx_processo ON [ia].[CONVERSA_CHAT](processo_referencia);
    CREATE INDEX idx_importante ON [ia].[CONVERSA_CHAT](importante, criado_em DESC);
    
    PRINT '✅ Tabela CONVERSA_CHAT criada.';
END
ELSE
    PRINT 'ℹ️ Tabela CONVERSA_CHAT já existe.';

GO

-- 21. REGRA_APRENDIDA
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[ia].[REGRA_APRENDIDA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [ia].[REGRA_APRENDIDA] (
        id_regra BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        tipo_regra VARCHAR(50) NOT NULL,
        contexto VARCHAR(100),
        nome_regra VARCHAR(255) NOT NULL,
        
        descricao TEXT NOT NULL,
        aplicacao_sql TEXT,
        aplicacao_texto TEXT,
        exemplo_uso TEXT,
        
        criado_por VARCHAR(100),
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        vezes_usado INT DEFAULT 0,
        ultimo_usado_em DATETIME,
        ativa BIT DEFAULT 1
    );
    
    CREATE INDEX idx_tipo_regra ON [ia].[REGRA_APRENDIDA](tipo_regra, contexto);
    CREATE INDEX idx_ativa ON [ia].[REGRA_APRENDIDA](ativa, vezes_usado DESC);
    CREATE INDEX idx_ultimo_usado ON [ia].[REGRA_APRENDIDA](ultimo_usado_em DESC);
    
    PRINT '✅ Tabela REGRA_APRENDIDA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela REGRA_APRENDIDA já existe.';

GO

-- 22. CONTEXTO_SESSAO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[ia].[CONTEXTO_SESSAO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [ia].[CONTEXTO_SESSAO] (
        id_contexto BIGINT IDENTITY(1,1) PRIMARY KEY,
        session_id VARCHAR(100) NOT NULL,
        
        tipo_contexto VARCHAR(50) NOT NULL,
        chave VARCHAR(100) NOT NULL,
        valor TEXT NOT NULL,
        
        dados_json NVARCHAR(MAX),
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        CONSTRAINT UQ_contexto UNIQUE(session_id, tipo_contexto, chave)
    );
    
    CREATE INDEX idx_session ON [ia].[CONTEXTO_SESSAO](session_id, tipo_contexto);
    CREATE INDEX idx_atualizado ON [ia].[CONTEXTO_SESSAO](atualizado_em DESC);
    
    PRINT '✅ Tabela CONTEXTO_SESSAO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela CONTEXTO_SESSAO já existe.';

GO

-- 23. CONSULTA_SALVA
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[ia].[CONSULTA_SALVA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [ia].[CONSULTA_SALVA] (
        id_consulta BIGINT IDENTITY(1,1) PRIMARY KEY,
        slug VARCHAR(100) NOT NULL UNIQUE,
        nome_exibicao VARCHAR(255) NOT NULL,
        
        descricao TEXT,
        sql_base TEXT NOT NULL,
        parametros_json NVARCHAR(MAX),
        exemplos_pergunta TEXT,
        
        criado_por VARCHAR(100),
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        vezes_usado INT DEFAULT 0,
        ultimo_usado_em DATETIME,
        
        regra_aprendida_id BIGINT
    );
    
    CREATE INDEX idx_slug ON [ia].[CONSULTA_SALVA](slug);
    CREATE INDEX idx_vezes_usado ON [ia].[CONSULTA_SALVA](vezes_usado DESC);
    CREATE INDEX idx_ultimo_usado ON [ia].[CONSULTA_SALVA](ultimo_usado_em DESC);
    
    PRINT '✅ Tabela CONSULTA_SALVA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela CONSULTA_SALVA já existe.';

GO

PRINT '';
PRINT '✅✅✅ FASE 5 CONCLUÍDA: Tabelas de IA e aprendizado criadas!';
PRINT '';

-- ============================================
-- FASE 6: TABELAS DE LEGISLAÇÃO
-- ============================================

PRINT '============================================';
PRINT 'FASE 6: TABELAS DE LEGISLAÇÃO';
PRINT '============================================';
PRINT '';

-- 24. LEGISLACAO_IMPORTADA
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[legislacao].[LEGISLACAO_IMPORTADA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [legislacao].[LEGISLACAO_IMPORTADA] (
        id_legislacao BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        tipo_ato VARCHAR(50) NOT NULL,
        numero_ato VARCHAR(50) NOT NULL,
        ano_ato INT NOT NULL,
        sigla_orgao VARCHAR(50),
        titulo_oficial VARCHAR(500),
        
        texto_completo TEXT NOT NULL,
        url_origem VARCHAR(500),
        arquivo_local VARCHAR(500),
        
        data_publicacao DATE,
        data_vigencia DATE,
        data_revogacao DATE,
        ato_revogador VARCHAR(255),
        
        status VARCHAR(20) DEFAULT 'ativa',
        vetorizada BIT DEFAULT 0,
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        CONSTRAINT UQ_legislacao UNIQUE(tipo_ato, numero_ato, ano_ato, sigla_orgao)
    );
    
    CREATE INDEX idx_tipo_numero ON [legislacao].[LEGISLACAO_IMPORTADA](tipo_ato, numero_ato, ano_ato);
    CREATE INDEX idx_status ON [legislacao].[LEGISLACAO_IMPORTADA](status);
    CREATE INDEX idx_vetorizada ON [legislacao].[LEGISLACAO_IMPORTADA](vetorizada);
    
    PRINT '✅ Tabela LEGISLACAO_IMPORTADA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela LEGISLACAO_IMPORTADA já existe.';

GO

-- 25. LEGISLACAO_VETORIZACAO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[legislacao].[LEGISLACAO_VETORIZACAO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [legislacao].[LEGISLACAO_VETORIZACAO] (
        id_vetorizacao BIGINT IDENTITY(1,1) PRIMARY KEY,
        id_legislacao BIGINT NOT NULL,
        
        vector_store_id VARCHAR(100),
        file_id VARCHAR(100),
        assistant_id VARCHAR(100),
        
        status VARCHAR(20) DEFAULT 'pendente',
        data_inicio DATETIME,
        data_conclusao DATETIME,
        mensagem_erro TEXT,
        
        total_chunks INT,
        total_tokens INT,
        custo_estimado DECIMAL(10,6),
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_legislacao ON [legislacao].[LEGISLACAO_VETORIZACAO](id_legislacao);
    CREATE INDEX idx_status ON [legislacao].[LEGISLACAO_VETORIZACAO](status);
    CREATE INDEX idx_vector_store ON [legislacao].[LEGISLACAO_VETORIZACAO](vector_store_id);
    
    PRINT '✅ Tabela LEGISLACAO_VETORIZACAO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela LEGISLACAO_VETORIZACAO já existe.';

GO

-- 26. LEGISLACAO_CHUNK
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[legislacao].[LEGISLACAO_CHUNK]') AND type in (N'U'))
BEGIN
    CREATE TABLE [legislacao].[LEGISLACAO_CHUNK] (
        id_chunk BIGINT IDENTITY(1,1) PRIMARY KEY,
        id_legislacao BIGINT NOT NULL,
        id_vetorizacao BIGINT,
        
        numero_chunk INT NOT NULL,
        texto_chunk TEXT NOT NULL,
        contexto_antes TEXT,
        contexto_depois TEXT,
        
        artigo VARCHAR(50),
        paragrafo VARCHAR(50),
        inciso VARCHAR(50),
        alinea VARCHAR(50),
        
        posicao_inicio INT,
        posicao_fim INT,
        tamanho_chunk INT,
        
        criado_em DATETIME DEFAULT GETDATE(),
        
        CONSTRAINT UQ_chunk UNIQUE(id_legislacao, numero_chunk)
    );
    
    CREATE INDEX idx_legislacao ON [legislacao].[LEGISLACAO_CHUNK](id_legislacao, numero_chunk);
    CREATE INDEX idx_artigo ON [legislacao].[LEGISLACAO_CHUNK](artigo, paragrafo);
    
    PRINT '✅ Tabela LEGISLACAO_CHUNK criada.';
END
ELSE
    PRINT 'ℹ️ Tabela LEGISLACAO_CHUNK já existe.';

GO

PRINT '';
PRINT '✅✅✅ FASE 6 CONCLUÍDA: Tabelas de legislação criadas!';
PRINT '';

-- ============================================
-- FASE 7: TABELAS DE AUDITORIA
-- ============================================

PRINT '============================================';
PRINT 'FASE 7: TABELAS DE AUDITORIA';
PRINT '============================================';
PRINT '';

-- 27. LOG_SINCRONIZACAO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[auditoria].[LOG_SINCRONIZACAO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [auditoria].[LOG_SINCRONIZACAO] (
        id_log BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        fonte_dados VARCHAR(50) NOT NULL,
        tipo_sincronizacao VARCHAR(50),
        
        data_inicio DATETIME NOT NULL,
        data_fim DATETIME,
        status VARCHAR(20) DEFAULT 'em_andamento',
        tempo_execucao_segundos INT,
        
        registros_processados INT DEFAULT 0,
        registros_inseridos INT DEFAULT 0,
        registros_atualizados INT DEFAULT 0,
        registros_com_erro INT DEFAULT 0,
        
        mensagem_erro TEXT,
        stack_trace TEXT,
        
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_fonte_dados ON [auditoria].[LOG_SINCRONIZACAO](fonte_dados, data_inicio DESC);
    CREATE INDEX idx_status ON [auditoria].[LOG_SINCRONIZACAO](status);
    CREATE INDEX idx_data_inicio ON [auditoria].[LOG_SINCRONIZACAO](data_inicio DESC);
    
    PRINT '✅ Tabela LOG_SINCRONIZACAO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela LOG_SINCRONIZACAO já existe.';

GO

-- 28. LOG_CONSULTA_API
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[auditoria].[LOG_CONSULTA_API]') AND type in (N'U'))
BEGIN
    CREATE TABLE [auditoria].[LOG_CONSULTA_API] (
        id_log BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        api_nome VARCHAR(50) NOT NULL,
        endpoint VARCHAR(500) NOT NULL,
        metodo VARCHAR(10) DEFAULT 'GET',
        
        parametros_requisicao NVARCHAR(MAX),
        headers_requisicao NVARCHAR(MAX),
        
        status_code INT,
        tempo_resposta_ms INT,
        tamanho_resposta_bytes INT,
        sucesso BIT DEFAULT 1,
        
        mensagem_erro TEXT,
        
        processo_referencia VARCHAR(50),
        session_id VARCHAR(100),
        
        data_consulta DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_api_nome ON [auditoria].[LOG_CONSULTA_API](api_nome, data_consulta DESC);
    CREATE INDEX idx_status_code ON [auditoria].[LOG_CONSULTA_API](status_code);
    CREATE INDEX idx_processo ON [auditoria].[LOG_CONSULTA_API](processo_referencia);
    CREATE INDEX idx_data_consulta ON [auditoria].[LOG_CONSULTA_API](data_consulta DESC);
    
    PRINT '✅ Tabela LOG_CONSULTA_API criada.';
END
ELSE
    PRINT 'ℹ️ Tabela LOG_CONSULTA_API já existe.';

GO

-- 29. LOG_ERRO
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[auditoria].[LOG_ERRO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [auditoria].[LOG_ERRO] (
        id_log BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        nivel VARCHAR(20) NOT NULL,
        mensagem_erro TEXT NOT NULL,
        stack_trace TEXT,
        tipo_erro VARCHAR(100),
        
        modulo_origem VARCHAR(255),
        funcao_origem VARCHAR(255),
        linha_erro INT,
        
        processo_referencia VARCHAR(50),
        session_id VARCHAR(100),
        api_nome VARCHAR(50),
        
        data_erro DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_nivel ON [auditoria].[LOG_ERRO](nivel, data_erro DESC);
    CREATE INDEX idx_tipo_erro ON [auditoria].[LOG_ERRO](tipo_erro);
    CREATE INDEX idx_processo ON [auditoria].[LOG_ERRO](processo_referencia);
    CREATE INDEX idx_data_erro ON [auditoria].[LOG_ERRO](data_erro DESC);
    
    PRINT '✅ Tabela LOG_ERRO criada.';
END
ELSE
    PRINT 'ℹ️ Tabela LOG_ERRO já existe.';

GO

PRINT '';
PRINT '✅✅✅ FASE 7 CONCLUÍDA: Tabelas de auditoria criadas!';
PRINT '';

-- ============================================
-- ÍNDICES ESTRATÉGICOS ADICIONAIS
-- ============================================

PRINT '============================================';
PRINT 'CRIANDO ÍNDICES ESTRATÉGICOS ADICIONAIS';
PRINT '============================================';
PRINT '';

-- Índices compostos para consultas frequentes
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_processo_categoria_status' AND object_id = OBJECT_ID('[dbo].[PROCESSO_IMPORTACAO]'))
BEGIN
    CREATE INDEX idx_processo_categoria_status 
    ON [dbo].[PROCESSO_IMPORTACAO](categoria_processo, status_atual, data_chegada);
    PRINT '✅ Índice idx_processo_categoria_status criado.';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_documento_tipo_status' AND object_id = OBJECT_ID('[dbo].[DOCUMENTO_ADUANEIRO]'))
BEGIN
    CREATE INDEX idx_documento_tipo_status 
    ON [dbo].[DOCUMENTO_ADUANEIRO](tipo_documento, status_documento, data_desembaraco);
    PRINT '✅ Índice idx_documento_tipo_status criado.';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_movimentacao_banco_data' AND object_id = OBJECT_ID('[dbo].[MOVIMENTACAO_BANCARIA]'))
BEGIN
    CREATE INDEX idx_movimentacao_banco_data 
    ON [dbo].[MOVIMENTACAO_BANCARIA](banco_origem, data_movimentacao DESC, sinal_movimentacao);
    PRINT '✅ Índice idx_movimentacao_banco_data criado.';
END

IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_conversa_session_tipo' AND object_id = OBJECT_ID('[ia].[CONVERSA_CHAT]'))
BEGIN
    CREATE INDEX idx_conversa_session_tipo 
    ON [ia].[CONVERSA_CHAT](session_id, tipo_conversa, criado_em DESC);
    PRINT '✅ Índice idx_conversa_session_tipo criado.';
END

GO

-- ============================================
-- RESUMO FINAL
-- ============================================

PRINT '';
PRINT '============================================';
PRINT '✅✅✅ SCRIPT DE CRIAÇÃO CONCLUÍDO!';
PRINT '============================================';
PRINT '';
PRINT '📊 RESUMO:';
PRINT '   - Schemas criados: 4 (dbo, comunicacao, ia, legislacao, auditoria)';
PRINT '   - Tabelas criadas: 30 (incluindo COMPROVANTE_RECURSO, VALIDACAO_ORIGEM_RECURSO e HISTORICO_DOCUMENTO_ADUANEIRO)';
PRINT '   - Índices criados: Múltiplos índices estratégicos';
PRINT '';
PRINT '⚠️ PRÓXIMOS PASSOS:';
PRINT '   1. Verificar se todas as tabelas foram criadas corretamente';
PRINT '   2. Executar script de migração (se PROCESSO_IMPORTACAO já existia)';
PRINT '   3. Testar estrutura criada';
PRINT '   4. Implementar validações automáticas (CPF/CNPJ)';
PRINT '   5. Implementar relatórios para intimações';
PRINT '';
PRINT '📚 DOCUMENTAÇÃO:';
PRINT '   - Planejamento completo: docs/PLANEJAMENTO_BANCO_DADOS_MAIKE.md';
PRINT '   - Roadmap: docs/ROADMAP_IMPLEMENTACAO_BANCO_DADOS.md';
PRINT '   - Compliance: docs/RASTREAMENTO_ORIGEM_RECURSOS_COMEX.md';
PRINT '';
PRINT '============================================';
GO

