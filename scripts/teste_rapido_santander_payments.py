#!/usr/bin/env python3
"""
Teste rápido do Santander Payments - Execute após reiniciar Flask.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("🧪 TESTE RÁPIDO: Santander Payments")
print("=" * 60)

# Importar serviço
try:
    from services.santander_payments_service import SantanderPaymentsService
    print("✅ Módulos importados")
except Exception as e:
    print(f"❌ Erro ao importar: {e}")
    sys.exit(1)

# Inicializar serviço
try:
    service = SantanderPaymentsService()
    print(f"✅ Serviço inicializado")
    print(f"   Habilitado: {service.enabled}")
    
    if not service.enabled:
        print("❌ Serviço não está habilitado")
        sys.exit(1)
    
    # Verificar configuração
    if service.api:
        config = service.api.config
        print(f"   Base URL: {config.base_url}")
        print(f"   Client ID: {config.client_id[:20] + '...' if config.client_id else 'NÃO CONFIGURADO'}")
        print(f"   Client Secret: {'✅ Configurado' if config.client_secret else '❌ NÃO CONFIGURADO'}")
        
        if "sandbox" in config.base_url.lower():
            print("   ✅ Ambiente: SANDBOX")
        else:
            print("   ⚠️ Ambiente: PRODUÇÃO (não é sandbox!)")
        
        # Verificar certificados
        if config.cert_file:
            print(f"   Certificado: {config.cert_file}")
            if os.path.exists(config.cert_file):
                print("      ✅ Arquivo existe")
            else:
                print("      ❌ Arquivo não encontrado")
        else:
            print("   ⚠️ Certificado não configurado (verificar fallback)")
        
        if config.key_file:
            print(f"   Chave: {config.key_file}")
            if os.path.exists(config.key_file):
                print("      ✅ Arquivo existe")
            else:
                print("      ❌ Arquivo não encontrado")
        else:
            print("   ⚠️ Chave não configurada (verificar fallback)")
    
    # Testar conexão
    print("\n📡 Testando conexão com API...")
    resultado = service.listar_workspaces()
    
    if resultado.get('sucesso'):
        print("✅ CONEXÃO BEM-SUCEDIDA!")
        resposta = resultado.get('resposta', '')
        print(f"\nResposta:\n{resposta[:500]}")
    else:
        print(f"❌ Erro na conexão:")
        print(f"   {resultado.get('erro', 'Erro desconhecido')}")
        print(f"   {resultado.get('resposta', '')[:300]}")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ TESTE CONCLUÍDO!")
print("=" * 60)
