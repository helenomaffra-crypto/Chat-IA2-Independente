#!/usr/bin/env python3
"""
Teste detalhado de conexão SQL Server - mostra erro completo
"""
import sys
import os
import subprocess
import json
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

print("=" * 80)
print("🔍 TESTE DETALHADO DE CONEXÃO SQL SERVER")
print("=" * 80)

# Mostrar configuração
print("\n📋 Configuração:")
print(f"   SQL_SERVER: {os.getenv('SQL_SERVER', 'NÃO DEFINIDO')}")
print(f"   SQL_USERNAME: {os.getenv('SQL_USERNAME', 'NÃO DEFINIDO')}")
print(f"   SQL_DATABASE: {os.getenv('SQL_DATABASE', 'NÃO DEFINIDO')}")
print(f"   SQL_PASSWORD: {'***' if os.getenv('SQL_PASSWORD') else 'NÃO DEFINIDO'}")

# Testar conexão direta via Node.js
print("\n1️⃣ Testando conexão direta via Node.js...")
node_script = Path(root_dir) / 'utils' / 'sql_server_node.js'

if not node_script.exists():
    print(f"   ❌ Script Node.js não encontrado: {node_script}")
    sys.exit(1)

# Query simples de teste
test_query = "SELECT DB_NAME() as current_database, @@VERSION as version"

# Preparar variáveis de ambiente
env = os.environ.copy()
env['SQL_SERVER'] = os.getenv('SQL_SERVER', '172.16.10.8\\SQLEXPRESS')
env['SQL_USERNAME'] = os.getenv('SQL_USERNAME', 'sa')
env['SQL_PASSWORD'] = os.getenv('SQL_PASSWORD', '')
env['SQL_DATABASE'] = os.getenv('SQL_DATABASE', 'mAIke_assistente')

print(f"\n   Executando: node {node_script.name} query '{test_query}' mAIke_assistente")
print(f"   Servidor: {env['SQL_SERVER']}")
print(f"   Database: {env['SQL_DATABASE']}")

try:
    cmd = [
        'node',
        str(node_script),
        'query',
        test_query,
        'mAIke_assistente'
    ]
    
    print("\n   ⏳ Aguardando resposta (timeout: 30s)...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        env=env
    )
    
    print(f"\n   Return code: {result.returncode}")
    
    if result.stdout:
        print(f"\n   📤 STDOUT ({len(result.stdout)} chars):")
        print("   " + "-" * 76)
        stdout_lines = result.stdout.strip().split('\n')
        for line in stdout_lines[:20]:  # Primeiras 20 linhas
            print(f"   {line}")
        if len(stdout_lines) > 20:
            print(f"   ... ({len(stdout_lines) - 20} linhas a mais)")
        print("   " + "-" * 76)
    
    if result.stderr:
        print(f"\n   📤 STDERR ({len(result.stderr)} chars):")
        print("   " + "-" * 76)
        stderr_lines = result.stderr.strip().split('\n')
        for line in stderr_lines[:20]:  # Primeiras 20 linhas
            print(f"   {line}")
        if len(stderr_lines) > 20:
            print(f"   ... ({len(stderr_lines) - 20} linhas a mais)")
        print("   " + "-" * 76)
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout.strip())
            if data.get('success'):
                print("\n   ✅ CONEXÃO BEM-SUCEDIDA!")
                if data.get('data'):
                    print(f"   Database atual: {data['data'][0].get('current_database', 'N/A')}")
            else:
                print(f"\n   ❌ Erro retornado: {data.get('error', 'Erro desconhecido')}")
        except json.JSONDecodeError as e:
            print(f"\n   ⚠️ Resposta não é JSON válido: {e}")
            print(f"   Conteúdo: {result.stdout[:200]}")
    else:
        print("\n   ❌ FALHA NA CONEXÃO")
        print("\n   💡 Possíveis causas:")
        print("      - Servidor SQL Server não está acessível")
        print("      - Credenciais incorretas")
        print("      - Firewall bloqueando conexão")
        print("      - Timeout de conexão")
        print("      - Instância SQL Server não está rodando")
        
except subprocess.TimeoutExpired:
    print("\n   ❌ TIMEOUT (30 segundos)")
    print("   💡 A conexão demorou mais de 30 segundos")
    print("   💡 Possíveis causas:")
    print("      - Servidor não está acessível")
    print("      - Rede muito lenta")
    print("      - Firewall bloqueando")
    
except Exception as e:
    print(f"\n   ❌ ERRO INESPERADO: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("✅ Teste concluído")
print("=" * 80)


