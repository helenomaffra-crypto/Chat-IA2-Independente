#!/usr/bin/env python3
"""
Script para verificar se a despesa do BGR.0070/25 foi gravada no SQL Server
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter

def verificar_despesa():
    """Verifica se a despesa do BGR.0070/25 foi gravada"""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE DESPESA - BGR.0070/25")
    print("=" * 80)
    
    sql_adapter = get_sql_adapter()
    
    # Verificar se tabela existe
    print("\n1️⃣ Verificando se tabela LANCAMENTO_TIPO_DESPESA existe...")
    check_table_query = """
        SELECT COUNT(*) as count
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'LANCAMENTO_TIPO_DESPESA'
    """
    
    result = sql_adapter.execute_query(check_table_query, database='mAIke_assistente')
    if result.get('success') and result.get('data'):
        count = result['data'][0].get('count', 0)
        if count > 0:
            print("✅ Tabela LANCAMENTO_TIPO_DESPESA existe")
        else:
            print("❌ Tabela LANCAMENTO_TIPO_DESPESA NÃO existe")
            print("💡 Execute o script SQL para criar a tabela")
            return
    else:
        print(f"❌ Erro ao verificar tabela: {result.get('error', 'Erro desconhecido')}")
        return
    
    # Buscar despesas do BGR.0070/25
    print("\n2️⃣ Buscando despesas do BGR.0070/25...")
    query = """
        SELECT TOP 10
            ltd.id_lancamento_tipo_despesa,
            ltd.processo_referencia,
            ltd.categoria_processo,
            ltd.valor_despesa,
            ltd.percentual_valor,
            ltd.origem_recurso,
            ltd.banco_origem,
            ltd.agencia_origem,
            ltd.conta_origem,
            ltd.data_pagamento,
            td.nome_despesa,
            td.categoria_despesa,
            mb.data_movimentacao,
            mb.valor_movimentacao,
            mb.tipo_movimentacao
        FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
        LEFT JOIN dbo.TIPO_DESPESA td ON ltd.id_tipo_despesa = td.id_tipo_despesa
        LEFT JOIN dbo.MOVIMENTACAO_BANCARIA mb ON ltd.id_movimentacao_bancaria = mb.id_movimentacao_bancaria
        WHERE ltd.processo_referencia = 'BGR.0070/25'
        ORDER BY ltd.data_pagamento DESC, ltd.criado_em DESC
    """
    
    result = sql_adapter.execute_query(query, database='mAIke_assistente')
    
    if result.get('success'):
        data = result.get('data', [])
        if data:
            print(f"✅ Encontradas {len(data)} despesa(s) para BGR.0070/25")
            print("\n📋 Detalhes das despesas:")
            for i, despesa in enumerate(data, 1):
                print(f"\n  {i}. {despesa.get('nome_despesa', 'N/A')} ({despesa.get('categoria_despesa', 'N/A')})")
                print(f"     Valor: R$ {despesa.get('valor_despesa', 0):,.2f}")
                print(f"     Percentual: {despesa.get('percentual_valor', 0):.1f}%")
                print(f"     Origem: {despesa.get('origem_recurso', 'N/A')}")
                print(f"     Banco: {despesa.get('banco_origem', 'N/A')} - Ag. {despesa.get('agencia_origem', 'N/A')} C/C {despesa.get('conta_origem', 'N/A')}")
                print(f"     Data Pagamento: {despesa.get('data_pagamento', 'N/A')}")
                print(f"     Data Movimentação: {despesa.get('data_movimentacao', 'N/A')}")
                print(f"     Valor Movimentação: R$ {despesa.get('valor_movimentacao', 0):,.2f}")
                print(f"     Tipo: {despesa.get('tipo_movimentacao', 'N/A')}")
        else:
            print("⚠️ Nenhuma despesa encontrada para BGR.0070/25")
            print("\n💡 Possíveis causas:")
            print("   - Despesa ainda não foi gravada no SQL Server")
            print("   - Despesa foi gravada apenas no SQLite (cache local)")
            print("   - Tabela existe mas está vazia")
    else:
        print(f"❌ Erro ao buscar despesas: {result.get('error', 'Erro desconhecido')}")
    
    # Verificar também no SQLite para comparar
    print("\n3️⃣ Verificando também no SQLite (cache local)...")
    try:
        from db_manager import get_db_connection
        import sqlite3
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verificar se tabela existe no SQLite
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='lancamento_tipo_despesa'
        """)
        
        if cursor.fetchone():
            cursor.execute("""
                SELECT COUNT(*) as total 
                FROM lancamento_tipo_despesa 
                WHERE processo_referencia = 'BGR.0070/25'
            """)
            total_sqlite = cursor.fetchone()['total']
            print(f"✅ SQLite: {total_sqlite} despesa(s) para BGR.0070/25")
        else:
            print("⚠️ Tabela lancamento_tipo_despesa não existe no SQLite")
        
        conn.close()
    except Exception as e:
        print(f"⚠️ Erro ao verificar SQLite: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída")
    print("=" * 80)

if __name__ == '__main__':
    verificar_despesa()


