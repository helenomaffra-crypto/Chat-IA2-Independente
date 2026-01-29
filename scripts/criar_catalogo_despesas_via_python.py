#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para criar catálogo de despesas padrão no banco de dados.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_server_adapter import get_sql_adapter

# Lista de despesas padrão
DESPESAS_PADRAO = [
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
    ('OUTROS', 'Outros', 'OUTROS', 'NACIONAL', 23),
]

SQL_CREATE_TABLES = """
-- 1. TIPO_DESPESA
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TIPO_DESPESA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[TIPO_DESPESA] (
        id_tipo_despesa BIGINT IDENTITY(1,1) PRIMARY KEY,
        codigo_tipo_despesa VARCHAR(50) UNIQUE NOT NULL,
        nome_despesa VARCHAR(255) NOT NULL,
        descricao_despesa TEXT,
        categoria_despesa VARCHAR(50),
        tipo_custo VARCHAR(50),
        plano_contas_codigo VARCHAR(50),
        plano_contas_descricao VARCHAR(255),
        ativo BIT DEFAULT 1,
        ordem_exibicao INT DEFAULT 0,
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE()
    );
    
    CREATE INDEX idx_codigo ON [dbo].[TIPO_DESPESA](codigo_tipo_despesa);
    CREATE INDEX idx_categoria ON [dbo].[TIPO_DESPESA](categoria_despesa);
    CREATE INDEX idx_ativo ON [dbo].[TIPO_DESPESA](ativo, ordem_exibicao);
    
    PRINT '✅ Tabela TIPO_DESPESA criada.';
END

-- 2. LANCAMENTO_TIPO_DESPESA
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[LANCAMENTO_TIPO_DESPESA]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[LANCAMENTO_TIPO_DESPESA] (
        id_lancamento_tipo_despesa BIGINT IDENTITY(1,1) PRIMARY KEY,
        id_movimentacao_bancaria BIGINT NOT NULL,
        id_tipo_despesa BIGINT NOT NULL,
        processo_referencia VARCHAR(50),
        categoria_processo VARCHAR(10),
        valor_despesa DECIMAL(18,2),
        percentual_valor DECIMAL(5,2),
        origem_classificacao VARCHAR(50) DEFAULT 'MANUAL',
        nivel_confianca DECIMAL(3,2),
        classificacao_validada BIT DEFAULT 0,
        data_validacao DATETIME,
        usuario_validacao VARCHAR(100),
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (id_movimentacao_bancaria) REFERENCES [dbo].[MOVIMENTACAO_BANCARIA](id_movimentacao),
        FOREIGN KEY (id_tipo_despesa) REFERENCES [dbo].[TIPO_DESPESA](id_tipo_despesa)
    );
    
    CREATE INDEX idx_movimentacao ON [dbo].[LANCAMENTO_TIPO_DESPESA](id_movimentacao_bancaria);
    CREATE INDEX idx_tipo_despesa ON [dbo].[LANCAMENTO_TIPO_DESPESA](id_tipo_despesa);
    CREATE INDEX idx_processo ON [dbo].[LANCAMENTO_TIPO_DESPESA](processo_referencia);
    
    PRINT '✅ Tabela LANCAMENTO_TIPO_DESPESA criada.';
END

-- 3. PLANO_CONTAS (preparado para futuro)
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PLANO_CONTAS]') AND type in (N'U'))
BEGIN
    CREATE TABLE [dbo].[PLANO_CONTAS] (
        id_plano_contas BIGINT IDENTITY(1,1) PRIMARY KEY,
        codigo_contabil VARCHAR(50) UNIQUE NOT NULL,
        descricao_contabil VARCHAR(255) NOT NULL,
        tipo_conta VARCHAR(20),
        categoria_conta VARCHAR(50),
        nivel_conta INT,
        id_tipo_despesa BIGINT,
        ativo BIT DEFAULT 1,
        observacoes TEXT,
        criado_em DATETIME DEFAULT GETDATE(),
        atualizado_em DATETIME DEFAULT GETDATE(),
        FOREIGN KEY (id_tipo_despesa) REFERENCES [dbo].[TIPO_DESPESA](id_tipo_despesa)
    );
    
    CREATE INDEX idx_codigo_contabil ON [dbo].[PLANO_CONTAS](codigo_contabil);
    CREATE INDEX idx_tipo_despesa_plan ON [dbo].[PLANO_CONTAS](id_tipo_despesa);
    
    PRINT '✅ Tabela PLANO_CONTAS criada.';
END
"""

def criar_catalogo_despesas():
    """Cria catálogo de despesas padrão no banco de dados."""
    
    print("=" * 80)
    print("📋 CRIAÇÃO DO CATÁLOGO DE DESPESAS")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    
    if not adapter.test_connection():
        print("❌ SQL Server não está acessível.")
        return False
    
    print(f"✅ Conectado ao banco: {adapter.database}")
    print()
    
    try:
        # 1. Criar tabelas
        print("🔨 Criando tabelas...")
        resultado = adapter.execute_query(SQL_CREATE_TABLES, database=adapter.database)
        
        if not resultado.get('success'):
            print(f"❌ Erro ao criar tabelas: {resultado.get('error')}")
            return False
        
        print("✅ Tabelas criadas/verificadas")
        print()
        
        # 2. Verificar se despesas já foram inseridas
        query_check = """
        SELECT COUNT(*) as total
        FROM dbo.TIPO_DESPESA
        WHERE codigo_tipo_despesa = 'FRETE_INTERNACIONAL'
        """
        
        resultado_check = adapter.execute_query(query_check, database=adapter.database)
        
        if resultado_check.get('success') and resultado_check.get('data'):
            row = resultado_check['data'][0] if len(resultado_check['data']) > 0 else {}
            total = row.get('total', 0)
            
            if total > 0:
                print("ℹ️ Despesas padrão já existem. Verificando se todas estão presentes...")
                
                # Verificar quantas despesas existem
                query_count = "SELECT COUNT(*) as total FROM dbo.TIPO_DESPESA WHERE ativo = 1"
                resultado_count = adapter.execute_query(query_count, database=adapter.database)
                if resultado_count.get('success') and resultado_count.get('data'):
                    count_row = resultado_count['data'][0]
                    total_existente = count_row.get('total', 0)
                    print(f"   Total de despesas existentes: {total_existente}")
                    print(f"   Esperado: {len(DESPESAS_PADRAO)}")
                    
                    if total_existente >= len(DESPESAS_PADRAO):
                        print("✅ Todas as despesas padrão já estão cadastradas!")
                        return True
            else:
                print("📝 Inserindo despesas padrão...")
        
        # 3. Inserir despesas padrão
        print(f"📝 Inserindo {len(DESPESAS_PADRAO)} despesas padrão...")
        
        for codigo, nome, categoria, tipo_custo, ordem in DESPESAS_PADRAO:
            # Verificar se já existe antes de inserir
            query_exists = f"""
            SELECT id_tipo_despesa
            FROM dbo.TIPO_DESPESA
            WHERE codigo_tipo_despesa = '{codigo}'
            """
            
            resultado_exists = adapter.execute_query(query_exists, database=adapter.database)
            
            if resultado_exists.get('success') and resultado_exists.get('data') and len(resultado_exists['data']) > 0:
                print(f"   ⏭️ {nome} já existe, pulando...")
                continue
            
            # Inserir despesa
            query_insert = f"""
            INSERT INTO dbo.TIPO_DESPESA 
                (codigo_tipo_despesa, nome_despesa, categoria_despesa, tipo_custo, ordem_exibicao, ativo)
            VALUES 
                ('{codigo}', '{nome}', '{categoria}', '{tipo_custo}', {ordem}, 1)
            """
            
            resultado_insert = adapter.execute_query(query_insert, database=adapter.database)
            
            if resultado_insert.get('success'):
                print(f"   ✅ {nome} inserido")
            else:
                print(f"   ❌ Erro ao inserir {nome}: {resultado_insert.get('error')}")
        
        print()
        
        # 4. Verificar resultado final
        query_final = "SELECT COUNT(*) as total FROM dbo.TIPO_DESPESA WHERE ativo = 1"
        resultado_final = adapter.execute_query(query_final, database=adapter.database)
        
        if resultado_final.get('success') and resultado_final.get('data'):
            row = resultado_final['data'][0]
            total = row.get('total', 0)
            print(f"✅ Total de despesas cadastradas: {total}")
            
            if total >= len(DESPESAS_PADRAO):
                print()
                print("=" * 80)
                print("✅ Catálogo de Despesas criado com sucesso!")
                print("=" * 80)
                print()
                print("📋 Estrutura criada:")
                print("  1. TIPO_DESPESA - Catálogo de despesas padrão")
                print("  2. LANCAMENTO_TIPO_DESPESA - Relação N:N (lançamento ↔ despesa ↔ processo)")
                print("  3. PLANO_CONTAS - Preparada para futuro (contabilidade)")
                print()
                print("💡 Próximos passos:")
                print("  - Criar interface para classificar lançamentos")
                print("  - Implementar detecção automática de tipo de despesa")
                print("  - Vincular plano de contas quando necessário")
                print()
                return True
            else:
                print(f"⚠️ Esperado {len(DESPESAS_PADRAO)} despesas, mas encontrado {total}")
                return False
        else:
            print("❌ Erro ao verificar resultado final")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao criar catálogo: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = criar_catalogo_despesas()
    sys.exit(0 if sucesso else 1)

