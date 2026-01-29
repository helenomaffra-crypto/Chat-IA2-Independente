-- ============================================
-- Script para Criar Tabela HISTORICO_DOCUMENTO_ADUANEIRO
-- Versão: 1.0 (08/01/2026)
-- ============================================
-- 
-- Este script cria APENAS a tabela de histórico de documentos.
-- Execute no banco mAIke_assistente.
--
-- ⚠️ IMPORTANTE: Execute como usuário com permissões de DBA
-- ⚠️ BANCO: Certifique-se de estar no banco mAIke_assistente
--
-- ============================================

USE [mAIke_assistente];
GO

PRINT '============================================';
PRINT 'Criando tabela HISTORICO_DOCUMENTO_ADUANEIRO';
PRINT '============================================';
PRINT '';

-- Verificar se tabela já existe
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]') AND type in (N'U'))
BEGIN
    PRINT 'ℹ️ Tabela HISTORICO_DOCUMENTO_ADUANEIRO já existe.';
    PRINT '   Se quiser recriar, execute: DROP TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO];'
    GO
END
ELSE
BEGIN
    -- Criar tabela
    CREATE TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO] (
        id_historico BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Vínculo com Documento Principal
        id_documento BIGINT,
        numero_documento VARCHAR(50) NOT NULL,
        tipo_documento VARCHAR(50) NOT NULL,
        processo_referencia VARCHAR(50),
        
        -- Detalhes do Evento
        data_evento DATETIME NOT NULL DEFAULT GETDATE(),
        tipo_evento VARCHAR(50) NOT NULL,
        tipo_evento_descricao VARCHAR(255),
        
        -- Valores Anteriores e Novos
        campo_alterado VARCHAR(100) NOT NULL,
        valor_anterior VARCHAR(500),
        valor_novo VARCHAR(500),
        
        -- Status e Situação (snapshot no momento do evento)
        status_documento VARCHAR(100),
        status_documento_codigo VARCHAR(20),
        canal_documento VARCHAR(20),
        situacao_documento VARCHAR(100),
        
        -- Datas (snapshot no momento do evento)
        data_registro DATETIME,
        data_situacao DATETIME,
        data_desembaraco DATETIME,
        
        -- Contexto da API
        fonte_dados VARCHAR(50) NOT NULL,
        api_endpoint VARCHAR(500),
        json_dados_originais NVARCHAR(MAX),
        
        -- Metadados
        usuario_ou_sistema VARCHAR(100) DEFAULT 'SISTEMA_AUTOMATICO',
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE()
    );
    
    -- Criar índices para performance
    CREATE INDEX idx_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](id_documento, data_evento DESC);
    CREATE INDEX idx_numero_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](numero_documento, tipo_documento, data_evento DESC);
    CREATE INDEX idx_processo ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](processo_referencia, data_evento DESC);
    CREATE INDEX idx_tipo_evento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](tipo_evento, data_evento DESC);
    CREATE INDEX idx_campo_alterado ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](campo_alterado, data_evento DESC);
    CREATE INDEX idx_fonte_dados ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](fonte_dados, data_evento DESC);
    
    PRINT '✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO criada com sucesso!';
    PRINT '✅ Índices criados com sucesso!';
END
GO

-- Verificar criação
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]') AND type in (N'U'))
BEGIN
    PRINT '';
    PRINT '============================================';
    PRINT '✅ VERIFICAÇÃO: Tabela criada com sucesso!';
    PRINT '============================================';
    
    -- Contar colunas
    DECLARE @col_count INT;
    SELECT @col_count = COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO';
    
    PRINT '';
    PRINT '📊 Estatísticas:';
    PRINT '   - Colunas: ' + CAST(@col_count AS VARCHAR(10));
    
    -- Contar índices
    DECLARE @idx_count INT;
    SELECT @idx_count = COUNT(*)
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]')
      AND index_id > 0;  -- Excluir heap (index_id = 0)
    
    PRINT '   - Índices: ' + CAST(@idx_count AS VARCHAR(10));
    PRINT '';
    PRINT '✅ Pronto para uso!';
END
ELSE
BEGIN
    PRINT '';
    PRINT '❌ ERRO: Tabela não foi criada. Verifique permissões e erros acima.';
END
GO

