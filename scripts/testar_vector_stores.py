#!/usr/bin/env python3
"""
Script de teste para verificar se vector_stores está disponível na API.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from openai import OpenAI
    import os
    
    # Carregar .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
    
    api_key = os.getenv('DUIMP_AI_API_KEY', '')
    if not api_key:
        print("❌ DUIMP_AI_API_KEY não configurado")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
    print("🔍 Verificando estrutura da API...")
    print(f"   client.beta: {hasattr(client, 'beta')}")
    
    if hasattr(client, 'beta'):
        beta = client.beta
        print(f"   client.beta.assistants: {hasattr(beta, 'assistants')}")
        print(f"   client.beta.vector_stores: {hasattr(beta, 'vector_stores')}")
        
        if hasattr(beta, 'vector_stores'):
            vs = beta.vector_stores
            print(f"   ✅ vector_stores encontrado!")
            print(f"   Métodos disponíveis: {[x for x in dir(vs) if not x.startswith('_')]}")
        else:
            print("   ❌ vector_stores NÃO encontrado em client.beta")
            print("   Tentando alternativas...")
            
            # Verificar se está em outro lugar
            if hasattr(beta, 'assistants'):
                assistants = beta.assistants
                print(f"   client.beta.assistants.vector_stores: {hasattr(assistants, 'vector_stores')}")
    
    print("\n💡 Se vector_stores não estiver disponível, pode ser necessário:")
    print("   1. Atualizar biblioteca: pip install --upgrade openai")
    print("   2. Verificar versão mínima: openai>=1.12.0")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()

