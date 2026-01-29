#!/usr/bin/env python3
"""
Script para verificar se a despesa do BGR.0069/25 está no SQL Server
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# ✅ FORÇAR CARREGAMENTO DO .env ANTES DE IMPORTAR ADAPTER
env_path = Path(root_dir) / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

from utils.sql_server_adapter import get_sql_adapter

def verificar_despesa():
    """Verifica se a despesa do BGR.0069/25 está no SQL Server"""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE DESPESA - BGR.0069/25")
    print("=" * 80)
    
    # Verificar qual database será usado
    database_para_usar = os.getenv('SQL_DATABASE', 'mAIke_assistente')
    print(f"\n💡 Database configurado: {database_para_usar}")
    print(f"   SQL_SERVER: {os.getenv('SQL_SERVER', 'NÃO DEFINIDO')}")
    
    sql_adapter = get_sql_adapter()
    
    # ✅ Usar database do .env ou mAIke_assistente como fallback
    if not database_para_usar or database_para_usar == 'Make':
        database_para_usar = 'mAIke_assistente'
        print(f"   ⚠️ Ajustando para usar: {database_para_usar}")
    
    print(f"\n   Database do adapter: {sql_adapter.database}")
    
    # Query exata usada pelo serviço
    query = """
        SELECT 
            ltd.id_lancamento_tipo_despesa,
            ltd.id_movimentacao_bancaria,
            ltd.id_tipo_despesa,
            ltd.processo_referencia,
            ltd.categoria_processo,
            ltd.valor_despesa,
            ltd.percentual_valor,
            ltd.origem_classificacao,
            ltd.criado_em as data_classificacao,
            td.nome_despesa,
            td.categoria_despesa,
            mb.data_movimentacao,
            mb.data_lancamento,
            mb.valor_movimentacao,
            mb.sinal_movimentacao,
            mb.descricao_movimentacao,
            mb.banco_origem,
            mb.agencia_origem,
            mb.conta_origem,
            mb.cpf_cnpj_contrapartida,
            mb.nome_contrapartida
        FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
        INNER JOIN dbo.TIPO_DESPESA td ON ltd.id_tipo_despesa = td.id_tipo_despesa
        INNER JOIN dbo.MOVIMENTACAO_BANCARIA mb ON ltd.id_movimentacao_bancaria = mb.id_movimentacao
        WHERE ltd.processo_referencia = 'BGR.0069/25'
        ORDER BY mb.data_movimentacao DESC, ltd.criado_em DESC
    """
    
    print("\n1️⃣ Executando query no SQL Server...")
    print(f"   Database: {database_para_usar}")
    print(f"   Processo: BGR.0069/25")
    
    result = sql_adapter.execute_query(query, database=database_para_usar)
    
    if result.get('success'):
        data = result.get('data', [])
        if data:
            print(f"\n✅ Encontradas {len(data)} despesa(s) no SQL Server!")
            print("\n📋 Detalhes:")
            
            for i, row in enumerate(data, 1):
                print(f"\n  {i}. {row.get('nome_despesa', 'N/A')}")
                print(f"     Valor: R$ {float(row.get('valor_despesa', 0)):,.2f}")
                print(f"     Data Movimentação: {row.get('data_movimentacao', 'N/A')}")
                print(f"     Banco: {row.get('banco_origem', 'N/A')} - Ag. {row.get('agencia_origem', 'N/A')} C/C {row.get('conta_origem', 'N/A')}")
                print(f"     Descrição: {row.get('descricao_movimentacao', 'N/A')}")
                print(f"     Origem: {row.get('origem_classificacao', 'N/A')}")
                print(f"     ID Movimentação: {row.get('id_movimentacao_bancaria', 'N/A')}")
                print(f"     ID Tipo Despesa: {row.get('id_tipo_despesa', 'N/A')}")
            
            print("\n✅✅✅ CONFIRMADO: Dados estão no SQL Server!")
        else:
            print("\n⚠️ Nenhuma despesa encontrada no SQL Server")
            print("   💡 Isso significa que os dados podem estar apenas no cache local")
    else:
        error_msg = result.get('error', 'Erro desconhecido')
        print(f"\n❌ Erro ao consultar: {error_msg}")
        
        if '[SQL Server Node] Conectando a:' in error_msg:
            print(f"\n💡 Este é apenas um log de conexão, não o erro real.")
            print(f"   O erro real pode estar sendo suprimido.")
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída")
    print("=" * 80)

if __name__ == '__main__':
    verificar_despesa()


