#!/usr/bin/env python3
"""
Script de diagnóstico do SQL Server
Verifica configuração, conectividade e database usado
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter
import os

def diagnostico():
    """Diagnóstico completo do SQL Server"""
    
    print("=" * 80)
    print("🔍 DIAGNÓSTICO SQL SERVER")
    print("=" * 80)
    
    # 1. Verificar variáveis de ambiente
    print("\n1️⃣ Variáveis de Ambiente (.env):")
    print(f"   SQL_SERVER: {os.getenv('SQL_SERVER', 'NÃO DEFINIDO')}")
    print(f"   SQL_USERNAME: {os.getenv('SQL_USERNAME', 'NÃO DEFINIDO')}")
    print(f"   SQL_DATABASE: {os.getenv('SQL_DATABASE', 'NÃO DEFINIDO')}")
    print(f"   SQL_PASSWORD: {'***' if os.getenv('SQL_PASSWORD') else 'NÃO DEFINIDO'}")
    
    # 2. Verificar adapter
    print("\n2️⃣ Configuração do Adapter:")
    sql_adapter = get_sql_adapter()
    if sql_adapter:
        print(f"   Server: {sql_adapter.server}")
        print(f"   Instance: {sql_adapter.instance}")
        print(f"   Username: {sql_adapter.username}")
        print(f"   Database padrão: {sql_adapter.database}")
        print(f"   Usa Node.js: {sql_adapter.use_node}")
        print(f"   Usa pyodbc: {sql_adapter.use_pyodbc}")
    else:
        print("   ❌ Adapter não inicializado")
        return
    
    # 3. Testar conexão com database padrão
    print("\n3️⃣ Testando conexão com database padrão...")
    test_query = "SELECT DB_NAME() as current_database, @@VERSION as version"
    result = sql_adapter.execute_query(test_query, database=None)  # Usa padrão
    
    if result.get('success'):
        data = result.get('data', [])
        if data:
            print(f"   ✅ Conectado ao database: {data[0].get('current_database', 'N/A')}")
            print(f"   ✅ SQL Server versão: {data[0].get('version', 'N/A')[:50]}...")
        else:
            print("   ⚠️ Conectado mas sem dados retornados")
    else:
        print(f"   ❌ Erro: {result.get('error', 'Erro desconhecido')}")
    
    # 4. Testar conexão com mAIke_assistente explicitamente
    print("\n4️⃣ Testando conexão com mAIke_assistente...")
    result2 = sql_adapter.execute_query(test_query, database='mAIke_assistente')
    
    if result2.get('success'):
        data = result2.get('data', [])
        if data:
            print(f"   ✅ Conectado ao database: {data[0].get('current_database', 'N/A')}")
        else:
            print("   ⚠️ Conectado mas sem dados retornados")
    else:
        print(f"   ❌ Erro: {result2.get('error', 'Erro desconhecido')}")
    
    # 5. Verificar se banco mAIke_assistente existe
    print("\n5️⃣ Verificando se banco mAIke_assistente existe...")
    check_db_query = "SELECT name FROM sys.databases WHERE name = 'mAIke_assistente'"
    result3 = sql_adapter.execute_query(check_db_query, database='master')
    
    if result3.get('success'):
        data = result3.get('data', [])
        if data:
            print("   ✅ Banco mAIke_assistente existe")
        else:
            print("   ❌ Banco mAIke_assistente NÃO existe")
    else:
        print(f"   ⚠️ Erro ao verificar: {result3.get('error', 'Erro desconhecido')}")
    
    # 6. Listar databases disponíveis
    print("\n6️⃣ Databases disponíveis no servidor:")
    list_db_query = "SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name"
    result4 = sql_adapter.execute_query(list_db_query, database='master')
    
    if result4.get('success'):
        data = result4.get('data', [])
        if data:
            print(f"   Encontrados {len(data)} database(s):")
            for db in data[:10]:  # Mostrar até 10
                print(f"     - {db.get('name', 'N/A')}")
        else:
            print("   ⚠️ Nenhum database encontrado")
    else:
        print(f"   ⚠️ Erro ao listar: {result4.get('error', 'Erro desconhecido')}")
    
    # 7. Testar query simples em mAIke_assistente
    print("\n7️⃣ Testando query simples em mAIke_assistente...")
    simple_query = "SELECT TOP 1 'OK' as status"
    result5 = sql_adapter.execute_query(simple_query, database='mAIke_assistente')
    
    if result5.get('success'):
        print("   ✅ Query executada com sucesso")
    else:
        print(f"   ❌ Erro: {result5.get('error', 'Erro desconhecido')}")
        print("   💡 Possíveis causas:")
        print("      - Banco não existe")
        print("      - Sem permissão de acesso")
        print("      - Timeout de conexão")
        print("      - Servidor offline")
    
    # 8. Verificar tabelas em mAIke_assistente
    print("\n8️⃣ Verificando tabelas em mAIke_assistente...")
    list_tables_query = """
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    result6 = sql_adapter.execute_query(list_tables_query, database='mAIke_assistente')
    
    if result6.get('success'):
        data = result6.get('data', [])
        if data:
            print(f"   ✅ Encontradas {len(data)} tabela(s):")
            for table in data[:10]:  # Mostrar até 10
                schema = table.get('TABLE_SCHEMA', 'dbo')
                name = table.get('TABLE_NAME', 'N/A')
                print(f"     - {schema}.{name}")
        else:
            print("   ⚠️ Nenhuma tabela encontrada")
    else:
        print(f"   ❌ Erro: {result6.get('error', 'Erro desconhecido')}")
    
    print("\n" + "=" * 80)
    print("✅ Diagnóstico concluído")
    print("=" * 80)
    
    # Recomendações
    print("\n💡 RECOMENDAÇÕES:")
    if os.getenv('SQL_DATABASE') != 'mAIke_assistente':
        print("   ⚠️ SQL_DATABASE no .env não está como 'mAIke_assistente'")
        print("   💡 Adicione ao .env: SQL_DATABASE=mAIke_assistente")
    else:
        print("   ✅ SQL_DATABASE está configurado corretamente")
    
    print("\n   Se conexão falhar intermitentemente:")
    print("   - Verificar se está na rede/VPN")
    print("   - Verificar timeout de conexão")
    print("   - Verificar se servidor está acessível (ping)")

if __name__ == '__main__':
    diagnostico()


