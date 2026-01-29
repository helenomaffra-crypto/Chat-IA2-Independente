#!/usr/bin/env python3
"""
Script de teste simples para testar o chat via HTTP.

Uso:
    python tests/test_chat_simples.py
    
Requisitos:
    - Flask rodando na porta 5001
    - Variáveis de ambiente configuradas (.env)
"""
import sys
import os
import json
import pytest
import requests
from datetime import datetime

# ⚠️ IMPORTANTE:
# Este arquivo é um script manual (depende de Flask rodando em localhost:5001).
# Para evitar falhas no `pytest tests/`, pulamos por padrão.
# Para habilitar explicitamente:
#   RUN_MANUAL_CHAT_HTTP_TESTS=1 python -m pytest tests/test_chat_simples.py
if os.environ.get("RUN_MANUAL_CHAT_HTTP_TESTS") != "1":
    pytest.skip("tests/test_chat_simples.py é manual (depende de servidor HTTP). Defina RUN_MANUAL_CHAT_HTTP_TESTS=1 para rodar.", allow_module_level=True)

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:5001"

def test_chat(mensagem: str, session_id: str = "test_session_" + str(int(datetime.now().timestamp()))):
    """Testa uma mensagem no chat."""
    print(f"\n{'='*60}")
    print(f"TESTE: {mensagem}")
    print(f"{'='*60}")
    print(f"Session ID: {session_id}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json={
                "mensagem": mensagem,
                "session_id": session_id,
                "historico": []
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Sucesso: {data.get('sucesso', False)}")
            print(f"\n📝 Resposta:")
            print(f"{data.get('resposta', 'Sem resposta')[:500]}...")
            
            if data.get('tool_calling'):
                print(f"\n🔧 Tool calls: {len(data.get('tool_calling', []))}")
                for tool in data.get('tool_calling', []):
                    if isinstance(tool, dict):
                        print(f"   - {tool.get('name', 'unknown')}")
            
            return data
        else:
            print(f"\n❌ Erro HTTP {response.status_code}")
            print(f"Resposta: {response.text[:200]}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Erro: Não foi possível conectar ao servidor em {BASE_URL}")
        print("   Certifique-se de que o Flask está rodando na porta 5001")
        return None
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return None

def test_limpar_contexto(session_id: str):
    """Testa limpeza de contexto."""
    print(f"\n{'='*60}")
    print(f"TESTE: Limpar Contexto")
    print(f"{'='*60}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/chat/limpar-contexto",
            json={"session_id": session_id},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ {data.get('mensagem', 'Contexto limpo')}")
            return True
        else:
            print(f"\n❌ Erro HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return False

def main():
    """Executa testes do chat."""
    print("="*60)
    print("TESTES DO CHAT - mAIke Assistente")
    print("="*60)
    print(f"\n⚠️  Certifique-se de que o Flask está rodando em {BASE_URL}")
    print("   Execute: python app.py")
    
    session_id = "test_session_" + str(int(datetime.now().timestamp()))
    
    # Teste 1: Limpar contexto
    print("\n\n1️⃣ TESTE: Limpar contexto")
    test_limpar_contexto(session_id)
    
    # Teste 2: Perguntar sobre contexto (deve estar vazio)
    print("\n\n2️⃣ TESTE: Consultar contexto (deve estar vazio)")
    test_chat("o que está no seu contexto?", session_id)
    
    # Teste 3: Perguntar sobre processo (vai salvar contexto)
    print("\n\n3️⃣ TESTE: Consultar processo (vai salvar contexto)")
    test_chat("como está o BND.0083/25?", session_id)
    
    # Teste 4: Perguntar sobre contexto novamente (deve ter o processo)
    print("\n\n4️⃣ TESTE: Consultar contexto novamente (deve ter processo)")
    test_chat("o que está no seu contexto?", session_id)
    
    # Teste 5: Dashboard (deve limpar contexto)
    print("\n\n5️⃣ TESTE: Dashboard (deve limpar contexto)")
    test_chat("o que temos pra hoje?", session_id)
    
    # Teste 6: Perguntar sobre contexto após dashboard (deve estar limpo)
    print("\n\n6️⃣ TESTE: Consultar contexto após dashboard (deve estar limpo)")
    test_chat("o que está no seu contexto?", session_id)
    
    print("\n\n" + "="*60)
    print("✅ TESTES CONCLUÍDOS")
    print("="*60)

if __name__ == '__main__':
    main()
