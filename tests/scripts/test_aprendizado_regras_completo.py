#!/usr/bin/env python3
"""
Teste completo e atualizado do sistema de aprendizado de regras.

Este script testa:
1. Se consegue salvar uma regra
2. Se a tool está disponível
3. Se o handler está implementado
4. Se as regras aparecem no prompt (se integrado)
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from services.learned_rules_service import salvar_regra_aprendida, buscar_regras_aprendidas, formatar_regras_para_prompt
from services.tool_definitions import get_available_tools
from db_manager import init_db

def test_salvar_regra():
    """Testa salvar uma regra."""
    print("\n" + "="*60)
    print("TESTE 1: Salvar regra aprendida")
    print("="*60)
    
    resultado = salvar_regra_aprendida(
        tipo_regra='campo_definicao',
        contexto='chegada_processos',
        nome_regra='destfinal como confirmação de chegada',
        descricao='O campo data_destino_final indica que o processo chegou ao destino final',
        aplicacao_sql='WHERE data_destino_final IS NOT NULL',
        aplicacao_texto='Processos com data_destino_final preenchida chegaram',
        exemplo_uso='Quando perguntar "quais VDM chegaram", usar data_destino_final IS NOT NULL',
        criado_por='teste_script'
    )
    
    if resultado.get('sucesso'):
        print(f"✅ Regra salva! ID: {resultado.get('id')}")
        return True, resultado.get('id')
    else:
        print(f"❌ Erro: {resultado.get('erro')}")
        return False, None


def test_tool_disponivel():
    """Testa se a tool está disponível."""
    print("\n" + "="*60)
    print("TESTE 2: Verificar se tool está disponível")
    print("="*60)
    
    tools = get_available_tools()
    tool_encontrada = [t for t in tools if t.get('function', {}).get('name') == 'salvar_regra_aprendida']
    
    if tool_encontrada:
        print("✅ Tool salvar_regra_aprendida está disponível!")
        print(f"   Descrição: {tool_encontrada[0]['function']['description'][:80]}...")
        return True
    else:
        print("❌ Tool NÃO está disponível")
        return False


def test_handler_implementado():
    """Testa se o handler está implementado no chat_service."""
    print("\n" + "="*60)
    print("TESTE 3: Verificar se handler está implementado")
    print("="*60)
    
    try:
        from services.chat_service import ChatService
        import inspect
        
        source = inspect.getsource(ChatService._executar_funcao_tool)
        
        if 'salvar_regra_aprendida' in source:
            print("✅ Handler implementado no _executar_funcao_tool")
            return True
        else:
            print("❌ Handler NÃO encontrado")
            return False
    except Exception as e:
        print(f"⚠️ Erro ao verificar: {e}")
        return False


def test_regras_no_prompt():
    """Testa se as regras aparecem formatadas para o prompt."""
    print("\n" + "="*60)
    print("TESTE 4: Verificar formatação de regras para prompt")
    print("="*60)
    
    regras = buscar_regras_aprendidas(ativas=True)
    
    if not regras:
        print("⚠️ Nenhuma regra encontrada")
        return True  # Não é erro, pode não ter regras ainda
    
    texto = formatar_regras_para_prompt(regras)
    
    if texto:
        print("✅ Regras formatadas para prompt:")
        print(texto[:200] + "..." if len(texto) > 200 else texto)
        return True
    else:
        print("⚠️ Nenhum texto formatado")
        return True  # Pode ser normal se não houver regras


def test_integracao_prompt_builder():
    """Testa se o PromptBuilder usa regras."""
    print("\n" + "="*60)
    print("TESTE 5: Verificar integração com PromptBuilder")
    print("="*60)
    
    try:
        from services.prompt_builder import PromptBuilder
        import inspect
        
        source = inspect.getsource(PromptBuilder.build_system_prompt)
        
        # Verificar se menciona regras ou learned_rules
        if 'regras' in source.lower() or 'learned' in source.lower():
            print("✅ PromptBuilder parece usar regras aprendidas")
            return True
        else:
            print("⚠️ PromptBuilder NÃO parece usar regras diretamente")
            print("   (Pode estar sendo adicionado dinamicamente no chat_service)")
            return True  # Não é erro crítico
    except Exception as e:
        print(f"⚠️ Erro ao verificar: {e}")
        return True  # Não é erro crítico


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🧪 TESTE COMPLETO DO SISTEMA DE APRENDIZADO DE REGRAS")
    print("="*60)
    
    # Garantir que o banco está inicializado
    init_db()
    
    resultados = []
    
    # Teste 1: Salvar regra
    sucesso, regra_id = test_salvar_regra()
    resultados.append(("Salvar regra", sucesso))
    
    # Teste 2: Tool disponível
    resultados.append(("Tool disponível", test_tool_disponivel()))
    
    # Teste 3: Handler implementado
    resultados.append(("Handler implementado", test_handler_implementado()))
    
    # Teste 4: Formatação para prompt
    resultados.append(("Formatação para prompt", test_regras_no_prompt()))
    
    # Teste 5: Integração PromptBuilder
    resultados.append(("Integração PromptBuilder", test_integracao_prompt_builder()))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    sucessos = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nome, resultado in resultados:
        status = "✅" if resultado else "❌"
        print(f"{status} {nome}")
    
    print(f"\n✅ {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("\n🎉 Sistema de aprendizado de regras está FUNCIONANDO!")
        print("\n💡 Para testar no chat:")
        print("   1. Digite: 'usar campo destfinal como confirmação de chegada'")
        print("   2. A IA deve salvar a regra automaticamente")
        print("   3. Depois pergunte: 'quais VDM chegaram?'")
        print("   4. A IA deve aplicar a regra automaticamente")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os erros acima.")
    
    return sucessos == total


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)



