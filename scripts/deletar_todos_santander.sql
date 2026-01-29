-- Script SQL para deletar TODOS os lançamentos do Santander
-- Execute este script no SQL Server Management Studio ou via Python

USE mAIke_assistente;
GO

-- 1. Deletar classificações vinculadas
DELETE ltd
FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
INNER JOIN dbo.MOVIMENTACAO_BANCARIA mb ON ltd.id_movimentacao_bancaria = mb.id_movimentacao
WHERE mb.banco_origem = 'SANTANDER';
GO

-- 2. Deletar impostos vinculados (se a tabela existir)
IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'IMPOSTO_IMPORTACAO')
BEGIN
    DELETE imp
    FROM dbo.IMPOSTO_IMPORTACAO imp
    INNER JOIN dbo.MOVIMENTACAO_BANCARIA mb ON imp.id_movimentacao_bancaria = mb.id_movimentacao
    WHERE mb.banco_origem = 'SANTANDER';
END
GO

-- 3. Deletar TODOS os lançamentos do Santander
DELETE FROM dbo.MOVIMENTACAO_BANCARIA
WHERE banco_origem = 'SANTANDER';
GO

-- Verificar resultado
SELECT 
    'Lançamentos restantes do Santander' as resultado,
    COUNT(*) as total
FROM dbo.MOVIMENTACAO_BANCARIA
WHERE banco_origem = 'SANTANDER';
GO


