#!/usr/bin/env python3
"""
Script de teste para verificar configuração do Santander Payments (Sandbox).
"""
import os
import sys
from dotenv import load_dotenv

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carregar .env (com tratamento de erro)
try:
    load_dotenv()
except Exception as e:
    print(f"⚠️ Aviso: Não foi possível carregar .env diretamente: {e}")
    print("   Continuando com variáveis de ambiente já carregadas...")

def main():
    print("=" * 60)
    print("🧪 TESTE: Santander Payments (Sandbox)")
    print("=" * 60)
    
    # 1. Verificar credenciais
    print("\n📋 1. Verificando Credenciais...")
    client_id = os.getenv("SANTANDER_PAYMENTS_CLIENT_ID")
    client_secret = os.getenv("SANTANDER_PAYMENTS_CLIENT_SECRET")
    base_url = os.getenv("SANTANDER_PAYMENTS_BASE_URL")
    
    if client_id:
        print(f"   ✅ Client ID: {client_id[:20]}...")
    else:
        print("   ❌ Client ID não configurado")
        return False
    
    if client_secret:
        print(f"   ✅ Client Secret: {'*' * len(client_secret)}")
    else:
        print("   ❌ Client Secret não configurado")
        return False
    
    if base_url:
        print(f"   ✅ Base URL: {base_url}")
        if "sandbox" in base_url.lower():
            print("   ✅ Ambiente: SANDBOX (teste)")
        else:
            print("   ⚠️ Ambiente: PRODUÇÃO (não é sandbox!)")
    else:
        print("   ⚠️ Base URL não configurado (usando padrão)")
    
    # 2. Verificar certificados
    print("\n📋 2. Verificando Certificados...")
    cert_payments = os.getenv("SANTANDER_PAYMENTS_CERT_FILE")
    key_payments = os.getenv("SANTANDER_PAYMENTS_KEY_FILE")
    cert_extrato = os.getenv("SANTANDER_CERT_FILE")
    key_extrato = os.getenv("SANTANDER_KEY_FILE")
    
    cert_usado = None
    key_usado = None
    
    if cert_payments and os.path.exists(cert_payments):
        print(f"   ✅ Certificado Pagamentos: {cert_payments}")
        cert_usado = cert_payments
    elif cert_extrato and os.path.exists(cert_extrato):
        print(f"   ✅ Certificado (fallback Extrato): {cert_extrato}")
        cert_usado = cert_extrato
    else:
        print("   ❌ Certificado não encontrado")
        if cert_payments:
            print(f"      Tentado: {cert_payments}")
        if cert_extrato:
            print(f"      Fallback: {cert_extrato}")
        return False
    
    if key_payments and os.path.exists(key_payments):
        print(f"   ✅ Chave Pagamentos: {key_payments}")
        key_usado = key_payments
    elif key_extrato and os.path.exists(key_extrato):
        print(f"   ✅ Chave (fallback Extrato): {key_extrato}")
        key_usado = key_extrato
    else:
        print("   ❌ Chave não encontrada")
        if key_payments:
            print(f"      Tentado: {key_payments}")
        if key_extrato:
            print(f"      Fallback: {key_extrato}")
        return False
    
    # 3. Testar importação
    print("\n📋 3. Testando Importação...")
    try:
        from utils.santander_payments_api import SantanderPaymentsAPI, SantanderPaymentsConfig
        from services.santander_payments_service import SantanderPaymentsService
        print("   ✅ Módulos importados com sucesso")
    except ImportError as e:
        print(f"   ❌ Erro ao importar: {e}")
        return False
    
    # 4. Testar inicialização
    print("\n📋 4. Testando Inicialização...")
    try:
        service = SantanderPaymentsService()
        if service.enabled:
            print("   ✅ SantanderPaymentsService inicializado")
        else:
            print("   ❌ SantanderPaymentsService não está habilitado")
            return False
    except Exception as e:
        print(f"   ❌ Erro ao inicializar: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Testar conexão (listar workspaces)
    print("\n📋 5. Testando Conexão com API (listar workspaces)...")
    try:
        resultado = service.listar_workspaces()
        if resultado.get('sucesso'):
            print("   ✅ Conexão bem-sucedida!")
            resposta = resultado.get('resposta', '')
            if 'SANDBOX' in resposta or 'sandbox' in resposta.lower():
                print("   ✅ Ambiente SANDBOX confirmado")
            print(f"\n   Resposta:\n   {resposta[:200]}...")
        else:
            print(f"   ❌ Erro na conexão: {resultado.get('erro', 'Erro desconhecido')}")
            print(f"   Resposta: {resultado.get('resposta', '')[:200]}")
            return False
    except Exception as e:
        print(f"   ❌ Erro ao conectar: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    print("\n💡 Próximos passos:")
    print("   1. Teste no chat: 'listar workspaces do santander'")
    print("   2. Crie um workspace: 'criar workspace santander agencia 3003 conta 000130827180'")
    print("   3. Teste TED: 'fazer ted de 100 reais para conta 1234 agencia 5678 banco 001'")
    
    return True

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
