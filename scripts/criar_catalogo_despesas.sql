-- ============================================
-- Script: Catálogo de Despesas Padrão
-- Descrição: Cria tabela de tipos de despesas padrão para processos de importação
-- Data: 07/01/2026
-- ============================================

USE [mAIke_assistente];
GO

-- ============================================
-- 1. TIPO_DESPESA (Catálogo de Despesas Padrão)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TIPO_DESPESA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[TIPO_DESPESA] (
        id_tipo_despesa BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Identificação
        codigo_tipo_despesa VARCHAR(50) UNIQUE NOT NULL,  -- Ex: 'FRETE_INTERNACIONAL', 'AFRMM', 'TAXA_SISCOMEX_DI'
        nome_despesa VARCHAR(255) NOT NULL,  -- Ex: 'Frete Internacional', 'AFRMM', 'Taxa Siscomex (D.I.)'
        descricao_despesa TEXT,
        
        -- Categorização
        categoria_despesa VARCHAR(50),  -- Ex: 'FRETE', 'IMPOSTO', 'TAXA', 'SERVICO'
        tipo_custo VARCHAR(50),  -- Ex: 'INTERNACIONAL', 'NACIONAL', 'BUROCRATICO'
        
        -- Plano de Contas (preparado para futuro)
        plano_contas_codigo VARCHAR(50),  -- Código do plano de contas contábil (quando implementado)
        plano_contas_descricao VARCHAR(255),
        
        -- Controle
        ativo BIT DEFAULT 1,
        ordem_exibicao INT DEFAULT 0,  -- Ordem para exibição na UI
        observacoes TEXT,
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_codigo ON [dbo].[TIPO_DESPESA](codigo_tipo_despesa);
    CREATE INDEX idx_categoria ON [dbo].[TIPO_DESPESA](categoria_despesa);
    CREATE INDEX idx_ativo ON [dbo].[TIPO_DESPESA](ativo, ordem_exibicao);
    CREATE INDEX idx_plano_contas ON [dbo].[TIPO_DESPESA](plano_contas_codigo);
    
    PRINT '✅ Tabela TIPO_DESPESA criada.';
    
    -- ✅ Inserir despesas padrão
    INSERT INTO [dbo].[TIPO_DESPESA] (codigo_tipo_despesa, nome_despesa, categoria_despesa, tipo_custo, ordem_exibicao) VALUES
    ('FRETE_INTERNACIONAL', 'Frete Internacional', 'FRETE', 'INTERNACIONAL', 1),
    ('SEGURO', 'Seguro', 'SEGURO', 'INTERNACIONAL', 2),
    ('AFRMM', 'AFRMM', 'IMPOSTO', 'NACIONAL', 3),
    ('MULTAS', 'Multas', 'MULTA', 'NACIONAL', 4),
    ('TAXA_SISCOMEX_DI', 'Tx Siscomex (D.I.)', 'TAXA', 'BUROCRATICO', 5),
    ('TAXA_SISCOMEX_DA', 'Tx Siscomex (D.A.)', 'TAXA', 'BUROCRATICO', 6),
    ('OUTROS_CUSTOS_INTERNAC', 'Outros Custos Internac.', 'CUSTO', 'INTERNACIONAL', 7),
    ('LIBERACAO_BL', 'Liberação B/L', 'SERVICO', 'BUROCRATICO', 8),
    ('INSPECAO_MERCADORIA', 'Inspeção de Mercadoria', 'SERVICO', 'BUROCRATICO', 9),
    ('ARMAZENAGEM_DTA', 'Armazenagem DTA', 'SERVICO', 'NACIONAL', 10),
    ('FRETE_DTA', 'Frete DTA', 'FRETE', 'NACIONAL', 11),
    ('ARMAZENAGEM', 'Armazenagem', 'SERVICO', 'NACIONAL', 12),
    ('GRU_TAXA_LI', 'GRU / Tx LI', 'TAXA', 'BUROCRATICO', 13),
    ('DESPACHANTE', 'Despachante', 'SERVICO', 'BUROCRATICO', 14),
    ('SDA', 'SDA', 'SERVICO', 'BUROCRATICO', 15),
    ('CARRETO', 'Carreto', 'SERVICO', 'NACIONAL', 16),
    ('ESCOLTA', 'Escolta', 'SERVICO', 'NACIONAL', 17),
    ('LAVAGEM_CTNR', 'Lavagem CTNR', 'SERVICO', 'NACIONAL', 18),
    ('DEMURRAGE', 'Demurrage', 'MULTA', 'INTERNACIONAL', 19),
    ('ANTIDUMPING', 'Antidumping', 'IMPOSTO', 'NACIONAL', 20),
    ('CONTRATO_CAMBIO', 'Contrato de Câmbio', 'CAMBIO', 'NACIONAL', 21),
    ('TARIFAS_BANCARIAS', 'Tarifas Bancárias', 'TAXA', 'NACIONAL', 22),
    ('OUTROS', 'Outros', 'OUTROS', 'NACIONAL', 23);
    
    PRINT '✅ Despesas padrão inseridas na tabela TIPO_DESPESA.';
END
ELSE
BEGIN
    PRINT 'ℹ️ Tabela TIPO_DESPESA já existe.';
    -- ✅ Verificar se despesas padrão já foram inseridas
    IF NOT EXISTS (SELECT 1 FROM [dbo].[TIPO_DESPESA] WHERE codigo_tipo_despesa = 'FRETE_INTERNACIONAL')
    BEGIN
        -- Inserir apenas se não existir
        INSERT INTO [dbo].[TIPO_DESPESA] (codigo_tipo_despesa, nome_despesa, categoria_despesa, tipo_custo, ordem_exibicao) VALUES
        ('FRETE_INTERNACIONAL', 'Frete Internacional', 'FRETE', 'INTERNACIONAL', 1),
        ('SEGURO', 'Seguro', 'SEGURO', 'INTERNACIONAL', 2),
        ('AFRMM', 'AFRMM', 'IMPOSTO', 'NACIONAL', 3),
        ('MULTAS', 'Multas', 'MULTA', 'NACIONAL', 4),
        ('TAXA_SISCOMEX_DI', 'Tx Siscomex (D.I.)', 'TAXA', 'BUROCRATICO', 5),
        ('TAXA_SISCOMEX_DA', 'Tx Siscomex (D.A.)', 'TAXA', 'BUROCRATICO', 6),
        ('OUTROS_CUSTOS_INTERNAC', 'Outros Custos Internac.', 'CUSTO', 'INTERNACIONAL', 7),
        ('LIBERACAO_BL', 'Liberação B/L', 'SERVICO', 'BUROCRATICO', 8),
        ('INSPECAO_MERCADORIA', 'Inspeção de Mercadoria', 'SERVICO', 'BUROCRATICO', 9),
        ('ARMAZENAGEM_DTA', 'Armazenagem DTA', 'SERVICO', 'NACIONAL', 10),
        ('FRETE_DTA', 'Frete DTA', 'FRETE', 'NACIONAL', 11),
        ('ARMAZENAGEM', 'Armazenagem', 'SERVICO', 'NACIONAL', 12),
        ('GRU_TAXA_LI', 'GRU / Tx LI', 'TAXA', 'BUROCRATICO', 13),
        ('DESPACHANTE', 'Despachante', 'SERVICO', 'BUROCRATICO', 14),
        ('SDA', 'SDA', 'SERVICO', 'BUROCRATICO', 15),
        ('CARRETO', 'Carreto', 'SERVICO', 'NACIONAL', 16),
        ('ESCOLTA', 'Escolta', 'SERVICO', 'NACIONAL', 17),
        ('LAVAGEM_CTNR', 'Lavagem CTNR', 'SERVICO', 'NACIONAL', 18),
        ('DEMURRAGE', 'Demurrage', 'MULTA', 'INTERNACIONAL', 19),
        ('ANTIDUMPING', 'Antidumping', 'IMPOSTO', 'NACIONAL', 20),
        ('CONTRATO_CAMBIO', 'Contrato de Câmbio', 'CAMBIO', 'NACIONAL', 21),
        ('TARIFAS_BANCARIAS', 'Tarifas Bancárias', 'TAXA', 'NACIONAL', 22),
        ('OUTROS', 'Outros', 'OUTROS', 'NACIONAL', 23);
        
        PRINT '✅ Despesas padrão inseridas na tabela TIPO_DESPESA.';
    END
    ELSE
    BEGIN
        PRINT 'ℹ️ Despesas padrão já existem na tabela TIPO_DESPESA.';
    END
END
GO

-- ============================================
-- 2. LANCAMENTO_TIPO_DESPESA (N:N)
-- Permite vincular um lançamento bancário a múltiplos tipos de despesa
-- E permite vincular um tipo de despesa a múltiplos processos
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[LANCAMENTO_TIPO_DESPESA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[LANCAMENTO_TIPO_DESPESA] (
        id_lancamento_tipo_despesa BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Relacionamentos
        id_movimentacao_bancaria BIGINT NOT NULL,
        id_tipo_despesa BIGINT NOT NULL,
        
        -- Vinculação a Processo (opcional - um lançamento pode ter despesas de múltiplos processos)
        processo_referencia VARCHAR(50),
        categoria_processo VARCHAR(10),
        
        -- Valores e distribuição
        valor_despesa DECIMAL(18,2),  -- Valor específico desta despesa neste lançamento
        percentual_valor DECIMAL(5,2),  -- Percentual do valor total do lançamento (se dividido)
        
        -- Validação e controle
        origem_classificacao VARCHAR(50) DEFAULT 'MANUAL',  -- 'MANUAL', 'AUTOMATICA', 'IA', 'REGRA'
        nivel_confianca DECIMAL(3,2),  -- 0.00 a 1.00 (para classificação automática/IA)
        classificacao_validada BIT DEFAULT 0,
        data_validacao DATETIME,
        usuario_validacao VARCHAR(100),
        
        -- Observações
        observacoes TEXT,
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        -- Constraints
        FOREIGN KEY (id_movimentacao_bancaria) REFERENCES [dbo].[MOVIMENTACAO_BANCARIA](id_movimentacao),
        FOREIGN KEY (id_tipo_despesa) REFERENCES [dbo].[TIPO_DESPESA](id_tipo_despesa)
    );
    
    CREATE INDEX idx_movimentacao ON [dbo].[LANCAMENTO_TIPO_DESPESA](id_movimentacao_bancaria);
    CREATE INDEX idx_tipo_despesa ON [dbo].[LANCAMENTO_TIPO_DESPESA](id_tipo_despesa);
    CREATE INDEX idx_processo ON [dbo].[LANCAMENTO_TIPO_DESPESA](processo_referencia);
    CREATE INDEX idx_categoria ON [dbo].[LANCAMENTO_TIPO_DESPESA](categoria_processo);
    CREATE INDEX idx_validado ON [dbo].[LANCAMENTO_TIPO_DESPESA](classificacao_validada, origem_classificacao);
    
    PRINT '✅ Tabela LANCAMENTO_TIPO_DESPESA criada.';
END
ELSE
    PRINT 'ℹ️ Tabela LANCAMENTO_TIPO_DESPESA já existe.';
GO

-- ============================================
-- 3. Atualizar MOVIMENTACAO_BANCARIA_PROCESSO (se necessário)
-- Adicionar campo para referenciar tipo de despesa
-- ============================================
IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MOVIMENTACAO_BANCARIA_PROCESSO]') AND type in (N'U'))
BEGIN
    -- Verificar se coluna id_tipo_despesa já existe
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID(N'[dbo].[MOVIMENTACAO_BANCARIA_PROCESSO]') AND name = 'id_tipo_despesa')
    BEGIN
        ALTER TABLE [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO]
        ADD id_tipo_despesa BIGINT NULL,
            valor_despesa DECIMAL(18,2) NULL;
        
        -- Adicionar FK se necessário
        ALTER TABLE [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO]
        ADD CONSTRAINT FK_MOV_BANCO_PROC_TIPO_DESPESA
        FOREIGN KEY (id_tipo_despesa) REFERENCES [dbo].[TIPO_DESPESA](id_tipo_despesa);
        
        CREATE INDEX idx_tipo_despesa_mov_proc ON [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO](id_tipo_despesa);
        
        PRINT '✅ Colunas adicionadas à tabela MOVIMENTACAO_BANCARIA_PROCESSO (id_tipo_despesa, valor_despesa).';
    END
    ELSE
    BEGIN
        PRINT 'ℹ️ Colunas id_tipo_despesa e valor_despesa já existem na tabela MOVIMENTACAO_BANCARIA_PROCESSO.';
    END
END
ELSE
BEGIN
    PRINT '⚠️ Tabela MOVIMENTACAO_BANCARIA_PROCESSO não existe. Criando...';
    -- Criar tabela completa (caso não exista)
    CREATE TABLE [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO] (
        id_movimentacao_processo BIGINT IDENTITY(1,1) PRIMARY KEY,
        id_movimentacao_bancaria BIGINT NOT NULL,
        processo_referencia VARCHAR(50) NOT NULL,
        categoria_processo VARCHAR(10),
        tipo_relacionamento VARCHAR(50),
        nivel_vinculo VARCHAR(20) DEFAULT 'MEDIO',
        status_vinculo VARCHAR(20) DEFAULT 'PENDENTE',
        id_despesa_processo BIGINT,
        id_tipo_despesa BIGINT NULL,  -- ✅ NOVO: Referência ao catálogo de despesas
        valor_despesa DECIMAL(18,2) NULL,  -- ✅ NOVO: Valor específico desta despesa
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (id_movimentacao_bancaria) REFERENCES [dbo].[MOVIMENTACAO_BANCARIA](id_movimentacao)
    );
    PRINT '✅ Tabela MOVIMENTACAO_BANCARIA_PROCESSO criada.';
END
GO

-- ============================================
-- 4. PLANO_CONTAS (Preparado para futuro)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PLANO_CONTAS]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[PLANO_CONTAS] (
        id_plano_contas BIGINT IDENTITY(1,1) PRIMARY KEY,
        
        -- Código e descrição
        codigo_contabil VARCHAR(50) UNIQUE NOT NULL,  -- Ex: '3.1.01.001'
        descricao_contabil VARCHAR(255) NOT NULL,  -- Ex: 'Despesas com Frete Internacional'
        
        -- Categorização
        tipo_conta VARCHAR(20),  -- 'ATIVO', 'PASSIVO', 'RECEITA', 'DESPESA'
        categoria_conta VARCHAR(50),  -- 'CIRCULANTE', 'NÃO_CIRCULANTE', etc.
        nivel_conta INT,  -- 1, 2, 3, 4 (nível hierárquico)
        
        -- Vinculação a Tipo de Despesa
        id_tipo_despesa BIGINT,  -- FK para TIPO_DESPESA (opcional)
        
        -- Controle
        ativo BIT DEFAULT 1,
        observacoes TEXT,
        
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        
        FOREIGN KEY (id_tipo_despesa) REFERENCES [dbo].[TIPO_DESPESA](id_tipo_despesa)
    );
    
    CREATE INDEX idx_codigo_contabil ON [dbo].[PLANO_CONTAS](codigo_contabil);
    CREATE INDEX idx_tipo_despesa_plan ON [dbo].[PLANO_CONTAS](id_tipo_despesa);
    CREATE INDEX idx_tipo_conta ON [dbo].[PLANO_CONTAS](tipo_conta, categoria_conta);
    
    PRINT '✅ Tabela PLANO_CONTAS criada (preparada para futuro uso).';
END
ELSE
    PRINT 'ℹ️ Tabela PLANO_CONTAS já existe.';
GO

PRINT '';
PRINT '========================================';
PRINT '✅ Catálogo de Despesas criado com sucesso!';
PRINT '========================================';
PRINT '';
PRINT 'Estrutura criada:';
PRINT '  1. TIPO_DESPESA - Catálogo com 23 despesas padrão';
PRINT '  2. LANCAMENTO_TIPO_DESPESA - Relação N:N (lançamento ↔ tipo despesa ↔ processo)';
PRINT '  3. MOVIMENTACAO_BANCARIA_PROCESSO - Atualizada com referência a tipo de despesa';
PRINT '  4. PLANO_CONTAS - Preparada para futuro (contabilidade)';
PRINT '';
PRINT 'Próximos passos:';
PRINT '  - Criar interface para classificar lançamentos';
PRINT '  - Implementar detecção automática de tipo de despesa';
PRINT '  - Vincular plano de contas quando necessário';
PRINT '';

