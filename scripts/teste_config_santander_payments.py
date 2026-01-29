#!/usr/bin/env python3
"""
Script de teste para verificar configuração do Santander Payments.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ✅ Carregar .env manualmente (igual ao app.py)
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f'✅ .env carregado de: {env_path}')
    else:
        print(f'⚠️ .env não encontrado em: {env_path}')
except Exception as e:
    print(f'⚠️ Erro ao carregar .env: {e}')

print('=' * 60)
print('🔍 VERIFICAÇÃO DE CONFIGURAÇÃO SANTANDER PAYMENTS')
print('=' * 60)

# 1. Verificar variáveis de ambiente (sem carregar .env diretamente)
print('\n📋 1. Variáveis de Ambiente:')
client_id = os.getenv('SANTANDER_PAYMENTS_CLIENT_ID')
client_secret = os.getenv('SANTANDER_PAYMENTS_CLIENT_SECRET')
base_url = os.getenv('SANTANDER_PAYMENTS_BASE_URL')

print(f'   SANTANDER_PAYMENTS_CLIENT_ID: {client_id[:20] if client_id else "❌ NÃO CONFIGURADO"}...')
print(f'   SANTANDER_PAYMENTS_CLIENT_SECRET: {"✅ configurado" if client_secret else "❌ NÃO CONFIGURADO"}')
print(f'   SANTANDER_PAYMENTS_BASE_URL: {base_url or "❌ NÃO CONFIGURADO"}')

# 2. Certificados (com fallback)
print('\n📋 2. Certificados (com fallback):')
cert_payments = os.getenv('SANTANDER_PAYMENTS_CERT_FILE')
cert_extrato = os.getenv('SANTANDER_CERT_FILE')
key_payments = os.getenv('SANTANDER_PAYMENTS_KEY_FILE')
key_extrato = os.getenv('SANTANDER_KEY_FILE')

cert_final = cert_payments or cert_extrato
key_final = key_payments or key_extrato

print(f'   Certificado final (fallback): {cert_final}')
if cert_final:
    if os.path.exists(cert_final):
        print(f'      ✅ Arquivo existe')
    else:
        print(f'      ❌ Arquivo não encontrado: {cert_final}')
else:
    print('      ❌ Nenhum certificado configurado')

print(f'   Chave final (fallback): {key_final}')
if key_final:
    if os.path.exists(key_final):
        print(f'      ✅ Arquivo existe')
    else:
        print(f'      ❌ Arquivo não encontrado: {key_final}')
else:
    print('      ❌ Nenhuma chave configurada')

# 3. Testar inicialização
print('\n📋 3. Testando Inicialização:')
try:
    from utils.santander_payments_api import SantanderPaymentsAPI, SantanderPaymentsConfig
    
    config = SantanderPaymentsConfig()
    print(f'   ✅ Config criado')
    print(f'   Client ID: {config.client_id[:20] if config.client_id else "N/A"}...')
    print(f'   Base URL: {config.base_url}')
    print(f'   Token URL: {config.token_url}')
    print(f'   Cert File: {config.cert_file}')
    print(f'   Key File: {config.key_file}')
    print(f'   Cert Path: {config.cert_path}')
    
    if config.cert_file and config.key_file:
        cert_exists = os.path.exists(config.cert_file) if config.cert_file else False
        key_exists = os.path.exists(config.key_file) if config.key_file else False
        print(f'   Cert existe: {cert_exists}')
        print(f'   Key existe: {key_exists}')
        if cert_exists and key_exists:
            print(f'   ✅ Certificados encontrados e válidos')
        else:
            print(f'   ❌ Certificados não encontrados')
    elif config.cert_path:
        cert_path_exists = os.path.exists(config.cert_path) if config.cert_path else False
        print(f'   Cert Path existe: {cert_path_exists}')
        if cert_path_exists:
            print(f'   ✅ Certificado combinado encontrado')
        else:
            print(f'   ❌ Certificado combinado não encontrado')
    
    # Testar inicialização da API
    print('\n📋 4. Testando Inicialização da API:')
    api = SantanderPaymentsAPI(config, debug=True)
    print(f'   ✅ API inicializada')
    
    # Verificar se certificados foram configurados na sessão
    if hasattr(api.session, 'cert') and api.session.cert:
        print(f'   ✅ Certificados mTLS configurados na sessão')
        print(f'      Cert: {api.session.cert}')
    else:
        print(f'   ❌ Certificados mTLS NÃO configurados na sessão')
    
    # Testar obtenção de token
    print('\n📋 5. Testando Obtenção de Token:')
    try:
        token = api._get_access_token()
        print(f'   ✅ Token obtido: {token[:20]}...')
    except Exception as e:
        print(f'   ❌ Erro ao obter token: {e}')
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f'   ❌ Erro: {e}')
    import traceback
    traceback.print_exc()

print('\n' + '=' * 60)
