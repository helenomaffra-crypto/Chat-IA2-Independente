-- ============================================
-- Script de Criação do Banco de Dados "Make"
-- Para o sistema Chat IA Independente (maike)
-- ============================================
-- 
-- Este script cria o banco de dados "Make" e suas tabelas principais
-- baseado no mapeamento documentado em docs/MAPEAMENTO_SQL_SERVER.md
--
-- ⚠️ IMPORTANTE: Execute este script como usuário com permissões de DBA
-- ⚠️ BACKUP: Faça backup do banco antes de executar se já existir
--
-- ============================================

USE master;
GO

-- Verificar se o banco já existe
IF EXISTS (SELECT name FROM sys.databases WHERE name = 'Make')
BEGIN
    PRINT '⚠️ Banco "Make" já existe. Deseja recriar? (Comente as linhas abaixo se não quiser recriar)'
    -- Descomente as linhas abaixo para DROPAR o banco existente:
    -- ALTER DATABASE Make SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    -- DROP DATABASE Make;
    -- PRINT '✅ Banco "Make" removido.';
END
ELSE
BEGIN
    -- Criar banco de dados
    CREATE DATABASE Make
    ON (
        NAME = 'Make',
        FILENAME = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\DATA\Make.mdf',
        SIZE = 100MB,
        MAXSIZE = 10GB,
        FILEGROWTH = 10MB
    )
    LOG ON (
        NAME = 'Make_Log',
        FILENAME = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\DATA\Make_Log.ldf',
        SIZE = 10MB,
        MAXSIZE = 1GB,
        FILEGROWTH = 10%
    );
    PRINT '✅ Banco "Make" criado com sucesso.';
END
GO

USE Make;
GO

-- ============================================
-- Tabela: PROCESSO_IMPORTACAO
-- Tabela principal de processos de importação
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PROCESSO_IMPORTACAO]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[PROCESSO_IMPORTACAO] (
        [id_processo_importacao] INT IDENTITY(1,1) PRIMARY KEY,
        [id_importacao] INT NULL,
        [numero_processo] NVARCHAR(50) NOT NULL UNIQUE,
        [numero_ce] NVARCHAR(50) NULL,
        [numero_di] NVARCHAR(50) NULL,
        [numero_duimp] NVARCHAR(50) NULL,
        [data_embarque] DATETIME NULL,
        [data_chegada_prevista] DATETIME NULL,
        [data_desembaraco] DATETIME NULL,
        [status_processo] NVARCHAR(50) NULL,
        [criado_em] DATETIME DEFAULT GETDATE(),
        [atualizado_em] DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX [idx_processo_numero] ON [dbo].[PROCESSO_IMPORTACAO]([numero_processo]);
    CREATE INDEX [idx_processo_id_importacao] ON [dbo].[PROCESSO_IMPORTACAO]([id_importacao]);
    CREATE INDEX [idx_processo_numero_ce] ON [dbo].[PROCESSO_IMPORTACAO]([numero_ce]);
    CREATE INDEX [idx_processo_numero_di] ON [dbo].[PROCESSO_IMPORTACAO]([numero_di]);
    CREATE INDEX [idx_processo_numero_duimp] ON [dbo].[PROCESSO_IMPORTACAO]([numero_duimp]);
    
    PRINT '✅ Tabela PROCESSO_IMPORTACAO criada.';
END
ELSE
BEGIN
    PRINT 'ℹ️ Tabela PROCESSO_IMPORTACAO já existe.';
END
GO

-- ============================================
-- Tabela: TRANSPORTE
-- Dados de rastreamento (ShipsGo)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TRANSPORTE]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[TRANSPORTE] (
        [id_transporte] INT IDENTITY(1,1) PRIMARY KEY,
        [id_processo_importacao] INT NULL,
        [numero_processo] NVARCHAR(50) NULL,
        [numero_container] NVARCHAR(50) NULL,
        [numero_ce] NVARCHAR(50) NULL,
        [nome_navio] NVARCHAR(200) NULL,
        [porto_origem] NVARCHAR(100) NULL,
        [porto_destino] NVARCHAR(100) NULL,
        [eta] DATETIME NULL,
        [status] NVARCHAR(50) NULL,
        [payload_raw] NVARCHAR(MAX) NULL,
        [criado_em] DATETIME DEFAULT GETDATE(),
        [atualizado_em] DATETIME DEFAULT GETDATE(),
        FOREIGN KEY ([id_processo_importacao]) REFERENCES [dbo].[PROCESSO_IMPORTACAO]([id_processo_importacao])
    );
    
    CREATE INDEX [idx_transporte_processo] ON [dbo].[TRANSPORTE]([id_processo_importacao]);
    CREATE INDEX [idx_transporte_numero_processo] ON [dbo].[TRANSPORTE]([numero_processo]);
    CREATE INDEX [idx_transporte_ce] ON [dbo].[TRANSPORTE]([numero_ce]);
    
    PRINT '✅ Tabela TRANSPORTE criada.';
END
ELSE
BEGIN
    PRINT 'ℹ️ Tabela TRANSPORTE já existe.';
END
GO

-- ============================================
-- Observações Importantes
-- ============================================
PRINT '';
PRINT '============================================';
PRINT '✅ Script de criação concluído!';
PRINT '============================================';
PRINT '';
PRINT '⚠️ NOTAS IMPORTANTES:';
PRINT '1. Este script cria apenas as tabelas básicas do banco "Make"';
PRINT '2. As tabelas de DUIMP, DI, CE e CCT estão em outros bancos:';
PRINT '   - duimp.dbo (DUIMPs)';
PRINT '   - Serpro.dbo (DIs e CEs)';
PRINT '   - comex.dbo (Importacoes - tabela de vínculo)';
PRINT '';
PRINT '3. Para criar os outros bancos, você precisará:';
PRINT '   - Acesso ao servidor SQL Server';
PRINT '   - Scripts de criação dos outros bancos (se disponíveis)';
PRINT '   - Ou restaurar de backup existente';
PRINT '';
PRINT '4. Verifique o arquivo docs/MAPEAMENTO_SQL_SERVER.md para';
PRINT '   entender a estrutura completa do sistema.';
PRINT '';
PRINT '5. Após criar o banco, configure as credenciais no .env:';
PRINT '   SQL_SERVER=172.16.10.8\SQLEXPRESS';
PRINT '   SQL_USERNAME=sa';
PRINT '   SQL_PASSWORD=sua_senha';
PRINT '   SQL_DATABASE=Make';
PRINT '';
PRINT '============================================';
GO



