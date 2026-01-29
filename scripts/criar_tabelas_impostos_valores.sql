-- ============================================
-- Script de Criação - Tabelas de Impostos e Valores
-- Versão: 1.0 (08/01/2026)
-- Baseado em: docs/ESTRATEGIA_POPULACAO_BANCO_MAIKE.md
-- ============================================
-- 
-- Este script cria as tabelas IMPOSTO_IMPORTACAO e VALOR_MERCADORIA
-- no banco mAIke_assistente do SQL Server.
--
-- ⚠️ IMPORTANTE: Execute este script como usuário com permissões de DBA
-- ⚠️ BACKUP: Faça backup do banco antes de executar se já existir
--
-- ============================================

USE [mAIke_assistente];
GO

-- ============================================
-- TABELA: IMPOSTO_IMPORTACAO
-- ============================================
-- Descrição: Impostos pagos da DI/DUIMP (II, IPI, PIS, COFINS, Taxa SISCOMEX)
-- Fonte: SQL Server Make (Di_Pagamento, Di_pagamentos_cod_receitas) ou Portal Único (DUIMP)

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[IMPOSTO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[IMPOSTO_IMPORTACAO] (
        id_imposto BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Vínculo
        processo_referencia VARCHAR(50) NOT NULL,
        numero_documento VARCHAR(50) NOT NULL,  -- DI ou DUIMP
        tipo_documento VARCHAR(10) NOT NULL,     -- 'DI' ou 'DUIMP'
        
        -- Tipo de Imposto
        tipo_imposto VARCHAR(50) NOT NULL,        -- 'II', 'IPI', 'PIS', 'COFINS', 'TAXA_UTILIZACAO', 'ANTIDUMPING', 'ICMS'
        codigo_receita VARCHAR(10),               -- Código da receita (0086, 1038, etc.)
        descricao_imposto NVARCHAR(200),         -- Descrição do imposto
        
        -- Valores
        valor_brl DECIMAL(18,2) NOT NULL,        -- Valor em BRL
        valor_usd DECIMAL(18,2),                  -- Valor em USD (se disponível)
        taxa_cambio DECIMAL(10,6),                -- Taxa de câmbio usada
        
        -- Datas
        data_pagamento DATETIME,                 -- Data do pagamento
        data_vencimento DATETIME,                 -- Data de vencimento (se disponível)
        
        -- Status
        pago BIT DEFAULT 1,                       -- Se foi pago
        numero_retificacao INT,                   -- Número da retificação (se aplicável)
        
        -- Fonte
        fonte_dados VARCHAR(50) NOT NULL,        -- 'SQL_SERVER', 'PORTAL_UNICO', 'INTEGRACOMEX', 'KANBAN_API'
        json_dados_originais NVARCHAR(MAX),      -- JSON completo da fonte
        
        -- Metadados
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        -- Constraints (sem Foreign Key por enquanto - será adicionada depois se necessário)
        CONSTRAINT CHK_IMPOSTO_TIPO_DOC CHECK (tipo_documento IN ('DI', 'DUIMP')),
        CONSTRAINT CHK_IMPOSTO_TIPO CHECK (tipo_imposto IN ('II', 'IPI', 'PIS', 'COFINS', 'TAXA_UTILIZACAO', 'ANTIDUMPING', 'ICMS', 'OUTROS'))
    );
    
    -- Índices
    CREATE INDEX idx_imposto_processo ON [dbo].[IMPOSTO_IMPORTACAO](processo_referencia, tipo_documento);
    CREATE INDEX idx_imposto_documento ON [dbo].[IMPOSTO_IMPORTACAO](numero_documento, tipo_documento);
    CREATE INDEX idx_imposto_tipo ON [dbo].[IMPOSTO_IMPORTACAO](tipo_imposto, data_pagamento DESC);
    CREATE INDEX idx_imposto_data_pagamento ON [dbo].[IMPOSTO_IMPORTACAO](data_pagamento DESC);
    CREATE INDEX idx_imposto_codigo_receita ON [dbo].[IMPOSTO_IMPORTACAO](codigo_receita);
    
    PRINT '✅ Tabela IMPOSTO_IMPORTACAO criada com sucesso.';
END
ELSE
BEGIN
    PRINT 'ℹ️ Tabela IMPOSTO_IMPORTACAO já existe.';
END
GO

-- ============================================
-- TABELA: VALOR_MERCADORIA
-- ============================================
-- Descrição: Valores da mercadoria (Descarga, Embarque) em BRL e USD
-- Fonte: SQL Server Make (Di_Dados_Gerais) ou Portal Único (DUIMP)

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[VALOR_MERCADORIA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[VALOR_MERCADORIA] (
        id_valor BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Vínculo
        processo_referencia VARCHAR(50) NOT NULL,
        numero_documento VARCHAR(50) NOT NULL,  -- DI ou DUIMP
        tipo_documento VARCHAR(10) NOT NULL,     -- 'DI' ou 'DUIMP'
        
        -- Tipo de Valor
        tipo_valor VARCHAR(50) NOT NULL,         -- 'DESCARGA', 'EMBARQUE', 'FOB', 'CIF', 'VMLE', 'VMLD'
        moeda VARCHAR(3) NOT NULL,                -- 'BRL', 'USD', 'EUR'
        
        -- Valores
        valor DECIMAL(18,2) NOT NULL,
        taxa_cambio DECIMAL(10,6),                -- Taxa de câmbio usada (se conversão)
        
        -- Datas
        data_valor DATETIME,                      -- Data de referência do valor
        data_atualizacao DATETIME DEFAULT GETDATE(),
        
        -- Fonte
        fonte_dados VARCHAR(50) NOT NULL,        -- 'SQL_SERVER', 'PORTAL_UNICO', 'INTEGRACOMEX', 'KANBAN_API'
        json_dados_originais NVARCHAR(MAX),      -- JSON completo da fonte
        
        -- Metadados
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        -- Constraints (sem Foreign Key por enquanto - será adicionada depois se necessário)
        CONSTRAINT CHK_VALOR_TIPO_DOC CHECK (tipo_documento IN ('DI', 'DUIMP')),
        -- ✅ Atualização (19/01/2026): incluir FRETE/SEGURO (usados pelo relatório FOB)
        CONSTRAINT CHK_VALOR_TIPO CHECK (tipo_valor IN ('DESCARGA', 'EMBARQUE', 'FOB', 'CIF', 'VMLE', 'VMLD', 'FRETE', 'SEGURO', 'OUTROS')),
        CONSTRAINT CHK_VALOR_MOEDA CHECK (moeda IN ('BRL', 'USD', 'EUR', 'OUTROS'))
    );
    
    -- Índices
    CREATE INDEX idx_valor_processo ON [dbo].[VALOR_MERCADORIA](processo_referencia, tipo_documento);
    CREATE INDEX idx_valor_documento ON [dbo].[VALOR_MERCADORIA](numero_documento, tipo_documento);
    CREATE INDEX idx_valor_tipo ON [dbo].[VALOR_MERCADORIA](tipo_valor, moeda);
    CREATE INDEX idx_valor_data ON [dbo].[VALOR_MERCADORIA](data_valor DESC);
    
    PRINT '✅ Tabela VALOR_MERCADORIA criada com sucesso.';
END
ELSE
BEGIN
    PRINT 'ℹ️ Tabela VALOR_MERCADORIA já existe.';
END
GO

-- ============================================
-- ADICIONAR FOREIGN KEYS (se PROCESSO_IMPORTACAO existir)
-- ============================================

-- Verificar se PROCESSO_IMPORTACAO existe e adicionar Foreign Key para IMPOSTO_IMPORTACAO
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PROCESSO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    -- Verificar se Foreign Key já existe
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_IMPOSTO_PROCESSO')
    BEGIN
        ALTER TABLE [dbo].[IMPOSTO_IMPORTACAO]
        ADD CONSTRAINT FK_IMPOSTO_PROCESSO FOREIGN KEY (processo_referencia) 
            REFERENCES [dbo].[PROCESSO_IMPORTACAO](processo_referencia) ON DELETE CASCADE;
        PRINT '✅ Foreign Key FK_IMPOSTO_PROCESSO adicionada.';
    END
    ELSE
    BEGIN
        PRINT 'ℹ️ Foreign Key FK_IMPOSTO_PROCESSO já existe.';
    END
END
ELSE
BEGIN
    PRINT '⚠️ Tabela PROCESSO_IMPORTACAO não existe. Foreign Key não será criada.';
END
GO

-- Verificar se PROCESSO_IMPORTACAO existe e adicionar Foreign Key para VALOR_MERCADORIA
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PROCESSO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    -- Verificar se Foreign Key já existe
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_VALOR_PROCESSO')
    BEGIN
        ALTER TABLE [dbo].[VALOR_MERCADORIA]
        ADD CONSTRAINT FK_VALOR_PROCESSO FOREIGN KEY (processo_referencia) 
            REFERENCES [dbo].[PROCESSO_IMPORTACAO](processo_referencia) ON DELETE CASCADE;
        PRINT '✅ Foreign Key FK_VALOR_PROCESSO adicionada.';
    END
    ELSE
    BEGIN
        PRINT 'ℹ️ Foreign Key FK_VALOR_PROCESSO já existe.';
    END
END
ELSE
BEGIN
    PRINT '⚠️ Tabela PROCESSO_IMPORTACAO não existe. Foreign Key não será criada.';
END
GO

-- ============================================
-- VERIFICAÇÃO FINAL
-- ============================================

PRINT '';
PRINT '========================================================================';
PRINT '✅ VERIFICAÇÃO DE TABELAS CRIADAS';
PRINT '========================================================================';

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[IMPOSTO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    DECLARE @count_imposto INT;
    SELECT @count_imposto = COUNT(*) FROM [dbo].[IMPOSTO_IMPORTACAO];
    PRINT '✅ IMPOSTO_IMPORTACAO: Existe (' + CAST(@count_imposto AS VARCHAR) + ' registros)';
END
ELSE
BEGIN
    PRINT '❌ IMPOSTO_IMPORTACAO: NÃO existe';
END

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[VALOR_MERCADORIA]') AND type in (N'U'))
BEGIN
    DECLARE @count_valor INT;
    SELECT @count_valor = COUNT(*) FROM [dbo].[VALOR_MERCADORIA];
    PRINT '✅ VALOR_MERCADORIA: Existe (' + CAST(@count_valor AS VARCHAR) + ' registros)';
END
ELSE
BEGIN
    PRINT '❌ VALOR_MERCADORIA: NÃO existe';
END

PRINT '========================================================================';
PRINT '✅ Script concluído!';
PRINT '========================================================================';
GO

