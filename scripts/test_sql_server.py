#!/usr/bin/env python3
"""
Script de teste para verificar conexão com SQL Server.
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_env():
    """Carrega variáveis de ambiente do .env"""
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)
    except ImportError:
        # Se dotenv não estiver instalado, tentar carregar manualmente
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip().strip('"').strip("'")
            except (PermissionError, OSError):
                # Ignorar erro de permissão (sandbox)
                pass
    except (PermissionError, OSError):
        # Ignorar erro de permissão (sandbox)
        pass

def test_sql_server():
    """Testa conexão com SQL Server"""
    print("=" * 80)
    print("TESTE DE CONEXÃO SQL SERVER")
    print("=" * 80)
    print()
    
    # Carregar .env
    load_env()
    
    # Verificar variáveis de ambiente
    sql_server = os.getenv('SQL_SERVER_HOST') or os.getenv('SQL_SERVER')
    sql_database = os.getenv('SQL_SERVER_DATABASE') or os.getenv('SQL_DATABASE')
    sql_user = os.getenv('SQL_SERVER_USER') or os.getenv('SQL_USERNAME')
    sql_password = os.getenv('SQL_SERVER_PASSWORD') or os.getenv('SQL_PASSWORD')
    
    print("📋 Configuração:")
    print(f"   Host: {sql_server or 'NÃO CONFIGURADO'}")
    print(f"   Database: {sql_database or 'NÃO CONFIGURADO'}")
    print(f"   User: {sql_user or 'NÃO CONFIGURADO'}")
    print(f"   Password: {'***' if sql_password else 'NÃO CONFIGURADO'}")
    print()
    
    if not sql_server:
        print("❌ ERRO: SQL_SERVER_HOST ou SQL_SERVER não configurado no .env")
        return False
    
    # Testar adaptador
    try:
        from utils.sql_server_adapter import get_sql_adapter
        
        print("🔄 Inicializando adaptador SQL Server...")
        adapter = get_sql_adapter()
        
        if not adapter:
            print("❌ ERRO: Não foi possível criar adaptador SQL Server")
            print("   Verifique se pyodbc está instalado ou Node.js adapter está configurado")
            return False
        
        print(f"✅ Adaptador criado:")
        print(f"   - Usando pyodbc: {adapter.use_pyodbc}")
        print(f"   - Usando Node.js: {adapter.use_node}")
        print()
        
        # Testar conexão (sem notificar erro)
        print("🔄 Testando conexão (SELECT 1)...")
        result = adapter.test_connection(notificar_erro=False)
        
        if result.get('success'):
            print("✅ CONEXÃO OK!")
            print()
            
            # Testar query simples
            print("🔄 Testando query simples (SELECT GETDATE())...")
            query_result = adapter.execute_query("SELECT GETDATE() AS data_atual", notificar_erro=False)
            
            if query_result.get('success'):
                data = query_result.get('data', [])
                if data:
                    print(f"✅ Query executada com sucesso!")
                    print(f"   Data/Hora do servidor: {data[0].get('data_atual', 'N/A')}")
                else:
                    print("⚠️ Query executada mas sem dados retornados")
            else:
                error = query_result.get('error', 'Erro desconhecido')
                print(f"⚠️ Query falhou: {error}")
                print("   (Mas a conexão básica está OK)")
            
            print()
            print("=" * 80)
            print("✅ RESULTADO: SQL Server está funcionando!")
            print("=" * 80)
            return True
        else:
            error = result.get('error', 'Erro desconhecido')
            print(f"❌ FALHA NA CONEXÃO:")
            print(f"   {error}")
            print()
            print("💡 Possíveis causas:")
            print("   - SQL Server não está acessível na rede")
            print("   - Credenciais incorretas")
            print("   - Firewall bloqueando conexão")
            print("   - SQL Server não está rodando")
            print()
            print("=" * 80)
            print("❌ RESULTADO: SQL Server NÃO está funcionando")
            print("=" * 80)
            return False
            
    except ImportError as e:
        print(f"❌ ERRO: Não foi possível importar módulos necessários: {e}")
        print("   Execute: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_sql_server()
    sys.exit(0 if success else 1)

