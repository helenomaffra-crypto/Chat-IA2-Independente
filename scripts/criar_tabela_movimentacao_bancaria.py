#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para criar a tabela MOVIMENTACAO_BANCARIA no banco mAIke_assistente.
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_server_adapter import get_sql_adapter

SQL_CREATE_TABLE = """
-- Tabela MOVIMENTACAO_BANCARIA (base para tudo)
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
    CREATE INDEX idx_hash_dados ON [dbo].[MOVIMENTACAO_BANCARIA](hash_dados);
    
    PRINT '✅ Tabela MOVIMENTACAO_BANCARIA criada.';
END
ELSE
BEGIN
    PRINT 'ℹ️ Tabela MOVIMENTACAO_BANCARIA já existe.';
END
"""

def criar_tabela():
    """Cria a tabela MOVIMENTACAO_BANCARIA no banco de dados."""
    
    print("=" * 80)
    print("🔧 CRIAÇÃO DA TABELA MOVIMENTACAO_BANCARIA")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    
    # Mostrar configuração
    print(f"🔧 Configuração:")
    print(f"   Servidor: {adapter.server}")
    print(f"   Instância: {adapter.instance or '(nenhuma)'}")
    print(f"   Banco de dados: {adapter.database}")
    print(f"   Usuário: {adapter.username}")
    print()
    
    # Verificar conexão
    if not adapter.test_connection():
        print("❌ SQL Server não está acessível. Verifique a conexão.")
        return False
    
    print("✅ Conectado ao SQL Server")
    print()
    
    # Verificar se banco existe
    print("🔍 Verificando banco de dados...")
    query_check_db = f"""
    SELECT name 
    FROM sys.databases 
    WHERE name = '{adapter.database}'
    """
    
    result_db = adapter.execute_query(query_check_db)
    if not result_db.get('success') or not result_db.get('data'):
        print(f"❌ Banco de dados '{adapter.database}' não encontrado!")
        print("   Execute primeiro o script: scripts/criar_banco_maike_completo.sql")
        return False
    
    print(f"✅ Banco '{adapter.database}' encontrado")
    print()
    
    # Verificar se tabela já existe
    print("🔍 Verificando se tabela já existe...")
    query_check_table = """
    SELECT 
        CASE 
            WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'MOVIMENTACAO_BANCARIA')
            THEN 'SIM'
            ELSE 'NÃO'
        END as tabela_existe
    """
    
    result_table = adapter.execute_query(query_check_table, database=adapter.database)
    if result_table.get('success') and result_table.get('data'):
        row = result_table['data'][0] if len(result_table['data']) > 0 else {}
        tabela_existe = row.get('tabela_existe', 'NÃO')
        if tabela_existe == 'SIM':
            print("ℹ️ Tabela MOVIMENTACAO_BANCARIA já existe!")
            print("   Não é necessário criar novamente.")
            return True
        else:
            print("ℹ️ Tabela MOVIMENTACAO_BANCARIA não existe. Criando...")
    else:
        print("⚠️ Não foi possível verificar se a tabela existe. Tentando criar...")
    print()
    
    # Criar tabela
    print("🔨 Criando tabela MOVIMENTACAO_BANCARIA...")
    try:
        result = adapter.execute_query(SQL_CREATE_TABLE, database=adapter.database)
        
        if result.get('success'):
            print("✅ Tabela MOVIMENTACAO_BANCARIA criada com sucesso!")
            print()
            
            # Verificar novamente
            result_verify = adapter.execute_query(query_check_table, database=adapter.database)
            if result_verify.get('success') and result_verify.get('data'):
                row = result_verify['data'][0] if len(result_verify['data']) > 0 else {}
                if row.get('tabela_existe') == 'SIM':
                    print("✅ Verificação: Tabela confirmada no banco de dados!")
                    return True
                else:
                    print("⚠️ A tabela foi criada, mas não foi encontrada na verificação.")
                    return False
            else:
                print("⚠️ Tabela criada, mas não foi possível verificar.")
                return True
        else:
            error = result.get('error', 'Erro desconhecido')
            print(f"❌ Erro ao criar tabela: {error}")
            
            # Se erro diz que já existe, está OK
            if 'already exists' in str(error).lower() or 'já existe' in str(error).lower():
                print("ℹ️ Tabela já existe (conforme erro).")
                return True
            
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar script SQL: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print()
        print("=" * 80)

if __name__ == '__main__':
    sucesso = criar_tabela()
    if sucesso:
        print("✅ Processo concluído com sucesso!")
        print()
        print("💡 Agora você pode:")
        print("   1. Sincronizar extratos bancários via interface")
        print("   2. Verificar lançamentos com: python3 testes/test_verificar_lancamentos_bb.py")
    else:
        print("❌ Processo não concluído. Verifique os erros acima.")
        sys.exit(1)

