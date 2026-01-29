#!/usr/bin/env python3
"""
Script de teste para verificar se a página 1 do extrato DI está funcionando corretamente.

Uso:
    python3 teste_extrato_di_pagina1.py BND.0101/25
    ou
    python3 teste_extrato_di_pagina1.py 26/0153278-4
"""

import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    if len(sys.argv) < 2:
        print("❌ Uso: python3 teste_extrato_di_pagina1.py <processo_ou_di>")
        print("   Exemplo: python3 teste_extrato_di_pagina1.py BND.0101/25")
        print("   Exemplo: python3 teste_extrato_di_pagina1.py 26/0153278-4")
        sys.exit(1)
    
    processo_ou_di = sys.argv[1]
    
    print("🔍 Testando geração de extrato DI (página 1)...")
    print(f"   Processo/DI: {processo_ou_di}")
    print()
    
    try:
        from services.di_pdf_service import DiPdfService
        
        # Inicializar serviço
        service = DiPdfService()
        
        # Determinar se é processo ou DI direta
        if '/' in processo_ou_di and len(processo_ou_di.split('/')) == 2:
            # Parece ser um processo (ex: BND.0101/25)
            print(f"📋 Interpretado como processo: {processo_ou_di}")
            resultado = service.gerar_pdf_di(processo_referencia=processo_ou_di)
        else:
            # Parece ser uma DI direta (ex: 26/0153278-4 ou 2601532784)
            print(f"📋 Interpretado como DI: {processo_ou_di}")
            resultado = service.gerar_pdf_di(numero_di=processo_ou_di)
        
        if resultado.get('sucesso'):
            print("✅ PDF gerado com sucesso!")
            print()
            print(f"📄 Arquivo: {resultado.get('nome_arquivo', 'N/A')}")
            print(f"📁 Caminho: downloads/{resultado.get('nome_arquivo', 'N/A')}")
            print()
            print("💡 Abra o PDF e verifique se a página 1 está igual ao PDF oficial:")
            print("   - Numeração no topo (Declaração: ... Data do Registro: ... 1)")
            print("   - CNPJ e Nome na mesma linha")
            print("   - Embalagem e Quantidade na mesma linha")
            print("   - Peso Bruto e Peso Líquido na mesma linha")
            print("   - Tabela de Valores com cabeçalho 'Moeda | Valor'")
            print("   - Numeração no rodapé (-- 1 of 5 --)")
        else:
            print("❌ Erro ao gerar PDF:")
            print(f"   {resultado.get('resposta', resultado.get('erro', 'Erro desconhecido'))}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
