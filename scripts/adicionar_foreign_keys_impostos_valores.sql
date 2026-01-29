-- ============================================
-- Script para Adicionar Foreign Keys
-- Versão: 1.0 (08/01/2026)
-- ============================================
-- 
-- Este script adiciona as Foreign Keys para IMPOSTO_IMPORTACAO e VALOR_MERCADORIA
-- referenciando PROCESSO_IMPORTACAO.
--
-- ⚠️ IMPORTANTE: Execute apenas se PROCESSO_IMPORTACAO existir e tiver
--    processo_referencia como UNIQUE ou PRIMARY KEY
--
-- ============================================

USE [mAIke_assistente];
GO

-- ============================================
-- VERIFICAR SE PROCESSO_IMPORTACAO EXISTE
-- ============================================

IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PROCESSO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    PRINT '❌ Tabela PROCESSO_IMPORTACAO não existe.';
    PRINT '   Execute primeiro o script criar_banco_maike_completo.sql';
    RETURN;
END
GO

-- ============================================
-- VERIFICAR SE processo_referencia É UNIQUE/PRIMARY KEY
-- ============================================

DECLARE @tem_constraint BIT = 0;

-- Verificar se processo_referencia é PRIMARY KEY
IF EXISTS (
    SELECT 1 
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
    WHERE tc.TABLE_NAME = 'PROCESSO_IMPORTACAO'
      AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
      AND kcu.COLUMN_NAME = 'processo_referencia'
)
BEGIN
    SET @tem_constraint = 1;
    PRINT '✅ processo_referencia é PRIMARY KEY em PROCESSO_IMPORTACAO';
END

-- Verificar se processo_referencia tem UNIQUE constraint
IF EXISTS (
    SELECT 1 
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
        ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
    WHERE tc.TABLE_NAME = 'PROCESSO_IMPORTACAO'
      AND tc.CONSTRAINT_TYPE = 'UNIQUE'
      AND kcu.COLUMN_NAME = 'processo_referencia'
)
BEGIN
    SET @tem_constraint = 1;
    PRINT '✅ processo_referencia tem UNIQUE constraint em PROCESSO_IMPORTACAO';
END

IF @tem_constraint = 0
BEGIN
    PRINT '⚠️ processo_referencia não tem UNIQUE ou PRIMARY KEY em PROCESSO_IMPORTACAO';
    PRINT '   Foreign Keys não podem ser criadas.';
    PRINT '   Adicione UNIQUE constraint em processo_referencia primeiro.';
    RETURN;
END
GO

-- ============================================
-- ADICIONAR FOREIGN KEY PARA IMPOSTO_IMPORTACAO
-- ============================================

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[IMPOSTO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    -- Verificar se Foreign Key já existe
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_IMPOSTO_PROCESSO')
    BEGIN
        BEGIN TRY
            ALTER TABLE [dbo].[IMPOSTO_IMPORTACAO]
            ADD CONSTRAINT FK_IMPOSTO_PROCESSO FOREIGN KEY (processo_referencia) 
                REFERENCES [dbo].[PROCESSO_IMPORTACAO](processo_referencia) ON DELETE CASCADE;
            PRINT '✅ Foreign Key FK_IMPOSTO_PROCESSO adicionada com sucesso.';
        END TRY
        BEGIN CATCH
            PRINT '❌ Erro ao adicionar FK_IMPOSTO_PROCESSO: ' + ERROR_MESSAGE();
        END CATCH
    END
    ELSE
    BEGIN
        PRINT 'ℹ️ Foreign Key FK_IMPOSTO_PROCESSO já existe.';
    END
END
ELSE
BEGIN
    PRINT '⚠️ Tabela IMPOSTO_IMPORTACAO não existe.';
END
GO

-- ============================================
-- ADICIONAR FOREIGN KEY PARA VALOR_MERCADORIA
-- ============================================

IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[VALOR_MERCADORIA]') AND type in (N'U'))
BEGIN
    -- Verificar se Foreign Key já existe
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_VALOR_PROCESSO')
    BEGIN
        BEGIN TRY
            ALTER TABLE [dbo].[VALOR_MERCADORIA]
            ADD CONSTRAINT FK_VALOR_PROCESSO FOREIGN KEY (processo_referencia) 
                REFERENCES [dbo].[PROCESSO_IMPORTACAO](processo_referencia) ON DELETE CASCADE;
            PRINT '✅ Foreign Key FK_VALOR_PROCESSO adicionada com sucesso.';
        END TRY
        BEGIN CATCH
            PRINT '❌ Erro ao adicionar FK_VALOR_PROCESSO: ' + ERROR_MESSAGE();
        END CATCH
    END
    ELSE
    BEGIN
        PRINT 'ℹ️ Foreign Key FK_VALOR_PROCESSO já existe.';
    END
END
ELSE
BEGIN
    PRINT '⚠️ Tabela VALOR_MERCADORIA não existe.';
END
GO

-- ============================================
-- VERIFICAÇÃO FINAL
-- ============================================

PRINT '';
PRINT '========================================================================';
PRINT '✅ VERIFICAÇÃO DE FOREIGN KEYS';
PRINT '========================================================================';

-- Verificar Foreign Keys criadas
SELECT 
    fk.name AS foreign_key_name,
    OBJECT_NAME(fk.parent_object_id) AS table_name,
    COL_NAME(fc.parent_object_id, fc.parent_column_id) AS column_name,
    OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
    COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS referenced_column
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fc ON fk.object_id = fc.constraint_object_id
WHERE OBJECT_NAME(fk.parent_object_id) IN ('IMPOSTO_IMPORTACAO', 'VALOR_MERCADORIA')
ORDER BY table_name, foreign_key_name;

PRINT '========================================================================';
PRINT '✅ Script concluído!';
PRINT '========================================================================';
GO


