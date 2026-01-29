#!/usr/bin/env python3
"""
Script para visualizar como as regras aprendidas são incluídas no prompt da IA.

Uso:
    python scripts/ver_regras_no_prompt.py
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.learned_rules_service import buscar_regras_aprendidas, formatar_regras_para_prompt

def mostrar_regras_no_prompt():
    """Mostra como as regras aprendidas aparecem no prompt da IA."""
    
    print("=" * 70)
    print("📚 REGRAS APRENDIDAS NO PROMPT DA IA")
    print("=" * 70)
    print()
    
    # Buscar regras ativas
    print("🔍 Buscando regras aprendidas no SQLite...")
    regras = buscar_regras_aprendidas(ativas=True)
    
    if not regras:
        print("⚠️  Nenhuma regra aprendida encontrada no banco.")
        print()
        print("💡 Para criar regras, use o chat:")
        print('   - "maike o ALH vai ser alho ok?"')
        print('   - "maike Diamond vai ser DMD"')
        return
    
    print(f"✅ {len(regras)} regra(s) encontrada(s)")
    print()
    
    # Mostrar todas as regras
    print("=" * 70)
    print("📋 TODAS AS REGRAS NO BANCO:")
    print("=" * 70)
    print()
    
    for i, regra in enumerate(regras, 1):
        print(f"{i}. **{regra.get('nome_regra', 'N/A')}**")
        print(f"   Tipo: {regra.get('tipo_regra', 'N/A')}")
        print(f"   Contexto: {regra.get('contexto', 'N/A')}")
        print(f"   Descrição: {regra.get('descricao', 'N/A')}")
        if regra.get('aplicacao_texto'):
            print(f"   Aplicação: {regra.get('aplicacao_texto')}")
        if regra.get('aplicacao_sql'):
            print(f"   SQL: {regra.get('aplicacao_sql')}")
        print(f"   Vezes usado: {regra.get('vezes_usado', 0)}")
        print(f"   ID: {regra.get('id')}")
        print()
    
    # Mostrar como aparece no prompt (limitado a 5)
    print("=" * 70)
    print("📝 COMO APARECE NO PROMPT DA IA:")
    print("=" * 70)
    print()
    print("(Limitado às 5 regras mais usadas/recentes)")
    print()
    
    texto_prompt = formatar_regras_para_prompt(regras)
    
    if texto_prompt:
        print(texto_prompt)
    else:
        print("(Nenhuma regra será incluída no prompt)")
    
    print()
    print("=" * 70)
    print("🔍 DETALHES TÉCNICOS:")
    print("=" * 70)
    print()
    print("1. Busca no SQLite:")
    print("   SELECT * FROM regras_aprendidas")
    print("   WHERE ativa = 1")
    print("   ORDER BY vezes_usado DESC, ultimo_usado_em DESC")
    print()
    print("2. Limitação:")
    print("   - Apenas as 5 primeiras regras são incluídas")
    print("   - Ordenadas por: vezes_usado DESC, ultimo_usado_em DESC")
    print()
    print("3. Formato no prompt:")
    print("   📚 **REGRAS APRENDIDAS:**")
    print("   - **nome_regra**: descricao")
    print("   💡 Aplique essas regras quando fizer sentido.")
    print()
    print("4. Onde é adicionado:")
    print("   - No final do system_prompt")
    print("   - Antes de enviar para a IA (GPT-4o)")
    print()
    
    # Mostrar regras de mapeamento cliente→categoria especificamente
    regras_cliente = [r for r in regras if r.get('tipo_regra') == 'cliente_categoria']
    
    if regras_cliente:
        print("=" * 70)
        print("🎯 REGRAS DE MAPEAMENTO CLIENTE → CATEGORIA:")
        print("=" * 70)
        print()
        
        for i, regra in enumerate(regras_cliente, 1):
            print(f"{i}. {regra.get('nome_regra', 'N/A')}")
            print(f"   → {regra.get('aplicacao_texto', 'N/A')}")
            print()
        
        print("💡 Essas regras são usadas pela normalização de termos")
        print("   (PrecheckService._normalizar_termo_cliente)")
        print()


if __name__ == '__main__':
    try:
        mostrar_regras_no_prompt()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

