#!/usr/bin/env python3
"""
Script de teste para o endpoint de streaming /api/chat/stream
"""
import requests
import json
import sys

def test_stream():
    """Testa o endpoint de streaming"""
    url = "http://localhost:5001/api/chat/stream"
    
    payload = {
        "mensagem": "olá, como você está?",
        "historico": [],
        "session_id": "test_stream_123"
    }
    
    print("🔄 Testando endpoint de streaming...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\n" + "="*60)
    print("Resposta (chunks):")
    print("="*60 + "\n")
    
    try:
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Erro HTTP {response.status_code}")
            print(f"Resposta: {response.text}")
            return False
        
        print("✅ Conexão estabelecida! Recebendo chunks...\n")
        
        full_response = ""
        chunk_count = 0
        
        # Processar Server-Sent Events
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])  # Remove "data: "
                        
                        if data.get('chunk'):
                            chunk = data['chunk']
                            full_response += chunk
                            chunk_count += 1
                            # Mostrar chunk em tempo real
                            print(chunk, end='', flush=True)
                        
                        if data.get('done'):
                            print("\n\n" + "="*60)
                            print(f"✅ Streaming concluído!")
                            print(f"Total de chunks recebidos: {chunk_count}")
                            print(f"Resposta completa ({len(full_response)} caracteres):")
                            print("="*60)
                            print(full_response)
                            
                            if data.get('tool_calls'):
                                print(f"\n🔧 Tool calls detectados: {len(data['tool_calls'])}")
                            
                            if data.get('resposta_final'):
                                print(f"\n📝 Resposta final: {data['resposta_final'][:200]}...")
                            
                            return True
                        
                        if data.get('error'):
                            print(f"\n❌ Erro no streaming: {data['error']}")
                            return False
                            
                    except json.JSONDecodeError as e:
                        print(f"\n⚠️ Erro ao parsear JSON: {e}")
                        print(f"Linha recebida: {line_str}")
        
        print("\n\n⚠️ Streaming terminou sem flag 'done'")
        print(f"Resposta acumulada: {full_response[:500]}...")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor")
        print("💡 Certifique-se de que o servidor está rodando em http://localhost:5001")
        return False
    except requests.exceptions.Timeout:
        print("❌ Erro: Timeout na requisição")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_stream()
    sys.exit(0 if success else 1)

