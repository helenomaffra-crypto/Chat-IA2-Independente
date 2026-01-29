#!/usr/bin/env python3
"""
Script para criar apenas a tabela DOCUMENTO_ADUANEIRO (tabela crítica faltante)
Útil se não conseguir executar o script SQL completo
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter

def criar_tabela_documento_aduaneiro():
    """Cria apenas a tabela DOCUMENTO_ADUANEIRO"""
    
    print("=" * 80)
    print("🔨 CRIANDO TABELA DOCUMENTO_ADUANEIRO")
    print("=" * 80)
    
    sql_adapter = get_sql_adapter()
    
    # Verificar se já existe
    print("\n1️⃣ Verificando se tabela já existe...")
    check_query = """
        SELECT COUNT(*) as count
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'DOCUMENTO_ADUANEIRO'
    """
    
    result = sql_adapter.execute_query(check_query, database='mAIke_assistente')
    if result.get('success') and result.get('data'):
        count = result['data'][0].get('count', 0)
        if count > 0:
            print("✅ Tabela DOCUMENTO_ADUANEIRO já existe!")
            return True
    
    # Criar tabela (versão simplificada - campos essenciais)
    print("\n2️⃣ Criando tabela DOCUMENTO_ADUANEIRO...")
    
    # Ler definição completa do script SQL
    script_path = os.path.join(os.path.dirname(__file__), 'criar_banco_maike_completo.sql')
    
    try:
        with open(script_path, 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # Extrair apenas a parte da criação de DOCUMENTO_ADUANEIRO
        # Procurar por "-- 10. DOCUMENTO_ADUANEIRO" até próximo "--"
        start_marker = "-- 10. DOCUMENTO_ADUANEIRO"
        end_marker = "-- 11. TIMELINE_PROCESSO"
        
        start_idx = script_content.find(start_marker)
        end_idx = script_content.find(end_marker)
        
        if start_idx != -1 and end_idx != -1:
            create_table_sql = script_content[start_idx:end_idx]
            # Remover comentários e GO
            lines = create_table_sql.split('\n')
            sql_lines = []
            for line in lines:
                if line.strip().startswith('--'):
                    continue
                if line.strip().upper() == 'GO':
                    continue
                sql_lines.append(line)
            
            create_table_sql = '\n'.join(sql_lines)
            
            # Executar (pode precisar dividir em partes se tiver múltiplos comandos)
            # Por enquanto, vamos criar uma versão simplificada
            print("⚠️ Script SQL completo tem múltiplos comandos GO")
            print("💡 Criando versão simplificada da tabela...")
            
            create_simple = """
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
                    
                    porto_origem_codigo VARCHAR(10),
                    porto_origem_nome VARCHAR(255),
                    porto_destino_codigo VARCHAR(10),
                    porto_destino_nome VARCHAR(255),
                    pais_procedencia VARCHAR(3),
                    nome_navio VARCHAR(255),
                    tipo_transporte VARCHAR(20),
                    
                    descricao_mercadoria TEXT,
                    nome_importador VARCHAR(255),
                    situacao_entrega VARCHAR(100),
                    
                    fonte_dados VARCHAR(50),
                    ultima_sincronizacao DATETIME,
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
            END
            """
            
            result = sql_adapter.execute_query(create_simple, database='mAIke_assistente')
            
            if result.get('success'):
                print("✅ Tabela DOCUMENTO_ADUANEIRO criada com sucesso!")
                
                # Verificar novamente
                result_check = sql_adapter.execute_query(check_query, database='mAIke_assistente')
                if result_check.get('success') and result_check.get('data'):
                    count = result_check['data'][0].get('count', 0)
                    if count > 0:
                        print("✅ Confirmação: Tabela existe no banco!")
                        return True
                
                return True
            else:
                print(f"❌ Erro ao criar tabela: {result.get('error', 'Erro desconhecido')}")
                return False
        else:
            print("❌ Não foi possível extrair definição do script SQL")
            print("💡 Use SQL Server Management Studio para executar o script completo")
            return False
            
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {script_path}")
        print("💡 Use SQL Server Management Studio para executar o script completo")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = criar_tabela_documento_aduaneiro()
    
    if sucesso:
        print("\n" + "=" * 80)
        print("✅ SUCESSO!")
        print("=" * 80)
        print("\n💡 Próximos passos:")
        print("   1. Execute: python3 testes/verificar_todas_tabelas_banco_novo.py")
        print("   2. Verifique se DOCUMENTO_ADUANEIRO aparece como existente")
        print("   3. Para criar outras tabelas, execute o script SQL completo via SSMS")
    else:
        print("\n" + "=" * 80)
        print("❌ FALHA")
        print("=" * 80)
        print("\n💡 Recomendação:")
        print("   Use SQL Server Management Studio para executar o script completo")
        print("   Ver: docs/COMO_EXECUTAR_SCRIPT_SQL.md")


