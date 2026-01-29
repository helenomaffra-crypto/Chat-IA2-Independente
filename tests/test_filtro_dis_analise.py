#!/usr/bin/env python3
"""
Teste para verificar se o filtro de "DIs em análise" está funcionando corretamente.
Simula o fluxo completo: gerar relatório → filtrar DIs em análise
"""
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:5001/api/chat"
SESSION_ID = "test_filtro_dis_analise"

def send_message(message, session_id=SESSION_ID, historico=None):
    """Envia mensagem para o chat"""
    payload = {
        "mensagem": message,
        "session_id": session_id,
        "historico": historico or []
    }
    try:
        response = requests.post(BASE_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        return None

def main():
    print("=" * 80)
    print("TESTE: Filtro de DIs em Análise")
    print("=" * 80)
    print()
    
    historico = []
    
    # 1. Gerar relatório "o que temos pra hoje?"
    print("1️⃣ Gerando relatório 'o que temos pra hoje?'...")
    res1 = send_message("o que temos pra hoje?", SESSION_ID, historico)
    if res1 and res1.get('sucesso'):
        resposta1 = res1.get('resposta', '')
        print(f"   ✅ Resposta recebida ({len(resposta1)} chars)")
        print(f"   Primeiros 200 chars: {resposta1[:200]}...")
        
        # Adicionar ao histórico
        historico.append({
            'mensagem': 'o que temos pra hoje?',
            'resposta': resposta1
        })
        
        # Verificar se tem dados_json
        if res1.get('dados_json'):
            secoes = res1.get('dados_json', {}).get('secoes', {})
            print(f"   ✅ JSON recebido com {len(secoes)} seções")
            if 'dis_analise' in secoes:
                print(f"   ✅ Seção 'dis_analise' encontrada: {len(secoes['dis_analise'])} DIs")
            else:
                print(f"   ⚠️ Seção 'dis_analise' NÃO encontrada no JSON")
        else:
            print(f"   ⚠️ Nenhum dados_json na resposta")
    else:
        print(f"   ❌ Erro ao gerar relatório: {res1}")
        return
    
    print()
    time.sleep(2)  # Dar tempo para salvar no banco
    
    # 2. Filtrar DIs em análise
    print("2️⃣ Filtrando 'mostre as DIs em análise'...")
    res2 = send_message("mostre as DIs em análise", SESSION_ID, historico)
    if res2 and res2.get('sucesso'):
        resposta2 = res2.get('resposta', '')
        print(f"   ✅ Resposta recebida ({len(resposta2)} chars)")
        print(f"   Primeiros 500 chars:")
        print(f"   {resposta2[:500]}")
        print()
        
        # Verificar se foi processado pelo precheck
        if res2.get('_processado_precheck'):
            print(f"   ✅ Processado pelo PRECHECK (usou JSON salvo)")
        else:
            print(f"   ⚠️ NÃO foi processado pelo precheck (pode ter ido para IA)")
        
        # Verificar se tem dados_json filtrado
        if res2.get('dados_json'):
            secoes_filtradas = res2.get('dados_json', {}).get('secoes', {})
            print(f"   ✅ JSON filtrado recebido com {len(secoes_filtradas)} seções")
            if 'dis_analise' in secoes_filtradas:
                print(f"   ✅ Seção 'dis_analise' no JSON filtrado: {len(secoes_filtradas['dis_analise'])} DIs")
            else:
                print(f"   ⚠️ Seção 'dis_analise' NÃO encontrada no JSON filtrado")
                print(f"   Seções encontradas: {list(secoes_filtradas.keys())}")
        else:
            print(f"   ⚠️ Nenhum dados_json na resposta filtrada")
    else:
        print(f"   ❌ Erro ao filtrar: {res2}")
        return
    
    print()
    print("=" * 80)
    print("✅ Teste concluído!")
    print("=" * 80)

if __name__ == "__main__":
    main()
