#!/usr/bin/env python3
"""
Script de teste para o endpoint de relatório de averbações.
"""

import requests
import json
import sys

# URL base do servidor (ajuste se necessário)
BASE_URL = "http://localhost:5001"

def testar_relatorio_averbacoes(mes="2025-06", categoria="BND"):
    """
    Testa o endpoint de relatório de averbações.
    
    Args:
        mes: Mês no formato "YYYY-MM" (ex: "2025-06")
        categoria: Categoria do processo (ex: "BND", "ALH", "VDM") ou None
    """
    url = f"{BASE_URL}/api/relatorio/averbacoes"
    
    payload = {
        "mes": mes
    }
    
    if categoria:
        payload["categoria"] = categoria
    
    print(f"🔍 Testando endpoint: {url}")
    print(f"📋 Parâmetros: {json.dumps(payload, indent=2)}")
    print("-" * 60)
    
    try:
        response = requests.post(url, json=payload, timeout=300)  # 5 minutos de timeout
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Headers: {dict(response.headers)}")
        print("-" * 60)
        
        try:
            resultado = response.json()
            print(f"✅ Resposta JSON:")
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
            
            if resultado.get('sucesso'):
                arquivo = resultado.get('arquivo', '')
                if arquivo:
                    print(f"\n📁 Arquivo gerado: {BASE_URL}{arquivo}")
                    print(f"💡 Para baixar: curl {BASE_URL}{arquivo} -o relatorio.xlsx")
            else:
                erro = resultado.get('erro', 'Erro desconhecido')
                print(f"\n❌ Erro: {erro}")
                
        except json.JSONDecodeError:
            print(f"⚠️ Resposta não é JSON:")
            print(response.text[:500])
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Erro: Não foi possível conectar ao servidor em {BASE_URL}")
        print("💡 Certifique-se de que o servidor Flask está rodando (python app.py)")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"⏱️ Erro: Timeout após 5 minutos")
        print("💡 O relatório pode estar demorando muito para gerar")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Exemplo de uso:
    # python test_relatorio_averbacoes.py
    # python test_relatorio_averbacoes.py 2025-06 BND
    # python test_relatorio_averbacoes.py 2025-06
    
    mes = sys.argv[1] if len(sys.argv) > 1 else "2025-06"
    categoria = sys.argv[2] if len(sys.argv) > 2 else "BND"
    
    testar_relatorio_averbacoes(mes=mes, categoria=categoria)
