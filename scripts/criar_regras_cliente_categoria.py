#!/usr/bin/env python3
"""
Script para criar regras aprendidas de mapeamento cliente → categoria.

Uso:
    python scripts/criar_regras_cliente_categoria.py

Cria regras para:
- Diamond → DMD
- Bandimar → BND
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.learned_rules_service import salvar_regra_aprendida, buscar_regras_aprendidas

def criar_regras_iniciais():
    """Cria regras aprendidas iniciais de mapeamento cliente → categoria."""
    
    print("🔧 Criando regras aprendidas de mapeamento cliente → categoria...\n")
    
    # Lista de regras a criar
    regras = [
        {
            'tipo_regra': 'cliente_categoria',
            'contexto': 'normalizacao_cliente',
            'nome_regra': 'Diamond → DMD',
            'descricao': 'Mapeia o termo "Diamond" e "diamonds" para a categoria DMD',
            'aplicacao_texto': 'Diamond → DMD',
            'exemplo_uso': 'Quando o usuário perguntar "como estão os processos do Diamond?", usar categoria DMD'
        },
        {
            'tipo_regra': 'cliente_categoria',
            'contexto': 'normalizacao_cliente',
            'nome_regra': 'Bandimar → BND',
            'descricao': 'Mapeia o termo "Bandimar" para a categoria BND',
            'aplicacao_texto': 'Bandimar → BND',
            'exemplo_uso': 'Quando o usuário perguntar "como estão os processos do Bandimar?", usar categoria BND'
        },
        {
            'tipo_regra': 'cliente_categoria',
            'contexto': 'normalizacao_cliente',
            'nome_regra': 'diamonds → DMD',
            'descricao': 'Mapeia o termo "diamonds" (plural) para a categoria DMD',
            'aplicacao_texto': 'diamonds → DMD',
            'exemplo_uso': 'Quando o usuário perguntar "como estão os diamonds?", usar categoria DMD'
        },
    ]
    
    regras_criadas = 0
    regras_atualizadas = 0
    regras_erro = 0
    
    for regra in regras:
        try:
            print(f"📝 Processando: {regra['nome_regra']}...")
            
            # Verificar se já existe
            regras_existentes = buscar_regras_aprendidas(
                tipo_regra=regra['tipo_regra'],
                ativas=True
            )
            
            existe = False
            for regra_existente in regras_existentes:
                if regra_existente.get('nome_regra') == regra['nome_regra']:
                    existe = True
                    break
            
            if existe:
                print(f"  ⚠️  Regra já existe: {regra['nome_regra']}")
                print(f"  🔄 Atualizando regra existente...")
            else:
                print(f"  ➕ Criando nova regra...")
            
            # Salvar/atualizar regra
            resultado = salvar_regra_aprendida(
                tipo_regra=regra['tipo_regra'],
                contexto=regra['contexto'],
                nome_regra=regra['nome_regra'],
                descricao=regra['descricao'],
                aplicacao_texto=regra.get('aplicacao_texto'),
                exemplo_uso=regra.get('exemplo_uso'),
                criado_por='script_criar_regras_cliente_categoria'
            )
            
            if resultado.get('sucesso'):
                if existe:
                    regras_atualizadas += 1
                    print(f"  ✅ Regra atualizada com sucesso!")
                else:
                    regras_criadas += 1
                    print(f"  ✅ Regra criada com sucesso! (ID: {resultado.get('id')})")
            else:
                regras_erro += 1
                print(f"  ❌ Erro ao criar/atualizar regra: {resultado.get('erro')}")
            
            print()
            
        except Exception as e:
            regras_erro += 1
            print(f"  ❌ Erro inesperado: {e}")
            print()
    
    # Resumo
    print("=" * 60)
    print("📊 RESUMO:")
    print(f"  ✅ Regras criadas: {regras_criadas}")
    print(f"  🔄 Regras atualizadas: {regras_atualizadas}")
    print(f"  ❌ Erros: {regras_erro}")
    print("=" * 60)
    
    if regras_erro == 0:
        print("\n✅ Todas as regras foram criadas/atualizadas com sucesso!")
        print("\n💡 Agora você pode testar no chat:")
        print("   - 'como estão os processos do Diamond?'")
        print("   - 'como estão os diamonds?'")
        print("   - 'como estão os processos do Bandimar?'")
    else:
        print(f"\n⚠️  {regras_erro} regra(s) tiveram erro. Verifique os logs acima.")
    
    return regras_erro == 0


def listar_regras_existentes():
    """Lista todas as regras de mapeamento cliente → categoria existentes."""
    
    print("\n📋 Regras de mapeamento cliente → categoria existentes:\n")
    
    regras = buscar_regras_aprendidas(
        tipo_regra='cliente_categoria',
        ativas=True
    )
    
    if not regras:
        print("  (nenhuma regra encontrada)")
        return
    
    for i, regra in enumerate(regras, 1):
        print(f"{i}. {regra.get('nome_regra', 'N/A')}")
        print(f"   Descrição: {regra.get('descricao', 'N/A')}")
        print(f"   Aplicação: {regra.get('aplicacao_texto', 'N/A')}")
        print(f"   ID: {regra.get('id')}")
        print()


if __name__ == '__main__':
    try:
        # Criar regras
        sucesso = criar_regras_iniciais()
        
        # Listar regras existentes
        listar_regras_existentes()
        
        sys.exit(0 if sucesso else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

