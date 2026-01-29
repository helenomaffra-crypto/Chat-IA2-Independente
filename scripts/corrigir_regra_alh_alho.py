#!/usr/bin/env python3
"""
Script para corrigir a regra "alh tambem chamado de alho" 
para o tipo correto (cliente_categoria).

Uso:
    python scripts/corrigir_regra_alh_alho.py
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.learned_rules_service import salvar_regra_aprendida, buscar_regras_aprendidas

def corrigir_regra_alh_alho():
    """Corrige a regra ALH → ALHO para tipo cliente_categoria."""
    
    print("🔧 Corrigindo regra 'alh tambem chamado de alho'...")
    print()
    
    # Buscar regra existente
    regras = buscar_regras_aprendidas()
    regra_alh = None
    
    for regra in regras:
        if 'alh' in regra.get('nome_regra', '').lower() and 'alho' in regra.get('nome_regra', '').lower():
            regra_alh = regra
            break
    
    if not regra_alh:
        print("❌ Regra 'alh tambem chamado de alho' não encontrada!")
        return False
    
    print(f"📋 Regra encontrada (ID: {regra_alh.get('id')}):")
    print(f"   Tipo atual: {regra_alh.get('tipo_regra')}")
    print(f"   Contexto atual: {regra_alh.get('contexto')}")
    print(f"   Nome: {regra_alh.get('nome_regra')}")
    print()
    
    # Criar nova regra com tipo correto
    print("✅ Criando regra corrigida...")
    resultado = salvar_regra_aprendida(
        tipo_regra='cliente_categoria',
        contexto='normalizacao_cliente',
        nome_regra='alho → ALH',
        descricao='Mapeia o termo "alho" (sem H) para a categoria ALH',
        aplicacao_texto='alho → ALH',
        exemplo_uso='Quando o usuário perguntar "como estão os processos do alho?", usar categoria ALH',
        criado_por='script_corrigir_regra_alh_alho'
    )
    
    if resultado.get('sucesso'):
        print(f"✅ Regra corrigida criada! (ID: {resultado.get('id')})")
        print()
        print("📝 Nova regra:")
        print("   Tipo: cliente_categoria")
        print("   Contexto: normalizacao_cliente")
        print("   Nome: alho → ALH")
        print("   Aplicação: alho → ALH")
        print()
        print("💡 Agora a regra será:")
        print("   ✅ Incluída na normalização de termos (PrecheckService)")
        print("   ✅ Aparecerá na seção 'REGRAS DE MAPEAMENTO CLIENTE → CATEGORIA'")
        print("   ✅ Funcionará quando você perguntar 'como estão os processos do alho?'")
        return True
    else:
        print(f"❌ Erro ao criar regra: {resultado.get('erro')}")
        return False


if __name__ == '__main__':
    try:
        sucesso = corrigir_regra_alh_alho()
        sys.exit(0 if sucesso else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

