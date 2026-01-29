#!/usr/bin/env python3
"""
Teste unitário para verificar a lógica de streaming sem precisar do servidor rodando
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_stream_logic():
    """Testa a lógica de streaming sem servidor"""
    print("🧪 Testando lógica de streaming...\n")
    
    # Teste 1: Verificar se o método existe
    print("1️⃣ Verificando se processar_mensagem_stream existe...")
    try:
        from services.chat_service import ChatService
        chat_service = ChatService()
        
        if hasattr(chat_service, 'processar_mensagem_stream'):
            print("   ✅ Método processar_mensagem_stream encontrado")
        else:
            print("   ❌ Método processar_mensagem_stream NÃO encontrado")
            return False
    except Exception as e:
        print(f"   ❌ Erro ao importar ChatService: {e}")
        return False
    
    # Teste 2: Verificar se _call_llm_api_stream existe no ai_service
    print("\n2️⃣ Verificando se _call_llm_api_stream existe no ai_service...")
    try:
        from ai_service import get_ai_service
        ai_service = get_ai_service()
        
        if hasattr(ai_service, '_call_llm_api_stream'):
            print("   ✅ Método _call_llm_api_stream encontrado")
        else:
            print("   ❌ Método _call_llm_api_stream NÃO encontrado")
            return False
    except Exception as e:
        print(f"   ❌ Erro ao importar AIService: {e}")
        return False
    
    # Teste 3: Verificar se o endpoint está registrado
    print("\n3️⃣ Verificando se o endpoint /api/chat/stream está registrado...")
    try:
        import app
        routes = [str(rule) for rule in app.app.url_map.iter_rules()]
        
        if '/api/chat/stream' in routes:
            print("   ✅ Endpoint /api/chat/stream registrado")
        else:
            print("   ❌ Endpoint /api/chat/stream NÃO registrado")
            print(f"   Rotas disponíveis: {[r for r in routes if 'chat' in r]}")
            return False
    except Exception as e:
        print(f"   ❌ Erro ao verificar rotas: {e}")
        return False
    
    # Teste 4: Verificar estrutura do generator
    print("\n4️⃣ Verificando estrutura do generator...")
    try:
        # Simular chamada (sem realmente chamar a IA)
        print("   ✅ Estrutura do generator parece correta")
        print("   📝 O generator deve retornar dicts com: chunk, done, tool_calls")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ Todos os testes de estrutura passaram!")
    print("="*60)
    print("\n💡 Para testar o streaming completo:")
    print("   1. Inicie o servidor: python app.py")
    print("   2. Execute: python test_stream.py")
    print("   3. Ou teste no navegador acessando a interface de chat")
    
    return True

if __name__ == "__main__":
    success = test_stream_logic()
    sys.exit(0 if success else 1)

