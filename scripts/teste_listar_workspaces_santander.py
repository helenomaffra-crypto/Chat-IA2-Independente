#!/usr/bin/env python3
"""
Script de teste para listar workspaces do Santander Payments API.
Usa a implementação real com mTLS e certificados.
"""
import sys
import os
import json

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.santander_payments_service import SantanderPaymentsService

print("🔍 Testando listagem de workspaces do Santander...")
print()

try:
    # Usar nossa implementação que já tem mTLS configurado
    service = SantanderPaymentsService()
    
    if not service.enabled:
        print("❌ Serviço de pagamentos não está habilitado")
        print("   Verifique as variáveis de ambiente SANTANDER_PAYMENTS_*")
        exit(1)
    
    print(f"✅ Serviço inicializado")
    print(f"   Base URL: {service.api.config.base_url}")
    print()
    
    # Listar workspaces
    print("📋 Listando workspaces...")
    resultado = service.listar_workspaces()
    
    if resultado.get('sucesso'):
        print("✅ Workspaces encontrados:")
        print()
        workspaces = resultado.get('dados', {}).get('_content', [])
        
        if not workspaces:
            print("   ⚠️ Nenhum workspace encontrado")
        else:
            for i, ws in enumerate(workspaces, 1):
                print(f"   {i}. {ws.get('type', 'N/A')} (ID: {ws.get('id', 'N/A')})")
                print(f"      Status: {ws.get('status', 'N/A')}")
                print(f"      Descrição: {ws.get('description', 'N/A')}")
                
                main_account = ws.get('mainDebitAccount', {})
                if main_account:
                    print(f"      Conta Principal: Ag. {main_account.get('branch')} / C/C {main_account.get('number')}")
                
                print(f"      TED Ativo: {'✅' if ws.get('bankTransferPaymentsActive') else '❌'}")
                print()
        
        print(f"\n📊 Total: {len(workspaces)} workspace(s)")
        print()
        print("📄 Resposta completa:")
        print(json.dumps(resultado.get('dados', {}), indent=2, ensure_ascii=False))
    else:
        print(f"❌ Erro ao listar workspaces:")
        print(f"   {resultado.get('erro', 'Erro desconhecido')}")
        print(f"   {resultado.get('resposta', '')}")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
