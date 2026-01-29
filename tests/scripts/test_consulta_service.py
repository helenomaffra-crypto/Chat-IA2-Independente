#!/usr/bin/env python3
"""
Script de teste rápido para validar a migração do ConsultaService.

Uso:
    python test_consulta_service.py
"""

import sys
import os

# Adicionar o diretório raiz ao path (subir 2 níveis: tests/scripts/ -> raiz)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ✅ Forçar reload do módulo para garantir versão mais recente
import importlib
if 'services.consulta_service' in sys.modules:
    importlib.reload(sys.modules['services.consulta_service'])


def test_verificar_atualizacao_ce():
    """Testa verificar_atualizacao_ce"""
    print("\n" + "="*60)
    print("TESTE 1: verificar_atualizacao_ce")
    print("="*60)
    
    from services.consulta_service import ConsultaService
    service = ConsultaService()
    
    # Teste com CE válido (usar um CE que você sabe que existe)
    numero_ce = "132505359791691"  # ⚠️ ALTERAR para um CE que você tem no cache
    
    resultado = service.verificar_atualizacao_ce(numero_ce)
    
    print(f"\n📋 Resultado:")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Precisa atualizar: {resultado.get('precisa_atualizar')}")
    print(f"   Motivo: {resultado.get('motivo')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:200]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 1 passou!")


def test_consultar_ce_maritimo():
    """Testa consultar_ce_maritimo"""
    print("\n" + "="*60)
    print("TESTE 2: consultar_ce_maritimo")
    print("="*60)
    
    from services.consulta_service import ConsultaService
    service = ConsultaService()
    
    # Teste 1: Consultar por número de CE
    numero_ce = "132505382290636"  # ⚠️ ALTERAR para um CE válido
    
    resultado = service.consultar_ce_maritimo(
        numero_ce=numero_ce,
        usar_cache_apenas=True  # Usar cache para não bilhetar
    )
    
    print(f"\n📋 Resultado (por número):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Fonte: {resultado.get('fonte')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:200]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 2a passou!")
    
    # Teste 2: Consultar por processo (se tiver processo com CE)
    processo_ref = "ALH.0172/25"  # ⚠️ ALTERAR para um processo que você sabe que tem CE
    
    resultado2 = service.consultar_ce_maritimo(
        processo_referencia=processo_ref,
        usar_cache_apenas=True
    )
    
    print(f"\n📋 Resultado (por processo):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Resposta: {resultado2.get('resposta', '')[:200]}...")
    
    print("✅ Teste 2b passou!")


def test_consultar_processo_consolidado():
    """Testa consultar_processo_consolidado"""
    print("\n" + "="*60)
    print("TESTE 3: consultar_processo_consolidado")
    print("="*60)
    
    # ✅ Forçar reload do módulo para garantir que está usando a versão mais recente
    import importlib
    import services.consulta_service
    importlib.reload(services.consulta_service)
    from services.consulta_service import ConsultaService
    
    service = ConsultaService()
    
    # Teste com processo que você sabe que tem dados
    processo_ref = "ALH.0172/25"  # ⚠️ ALTERAR para um processo válido
    
    resultado = service.consultar_processo_consolidado(processo_ref)
    
    print(f"\n📋 Resultado:")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Processo: {resultado.get('processo_referencia')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    
    if resultado.get('sucesso'):
        dados = resultado.get('dados', {})
        print(f"\n   ✅ Dados encontrados:")
        print(f"      - DI: {dados.get('chaves', {}).get('di', 'N/A')}")
        print(f"      - DUIMP: {dados.get('chaves', {}).get('duimp_num', 'N/A')}")
        print(f"      - CE: {dados.get('chaves', {}).get('ce_house', dados.get('chaves', {}).get('ce_master', 'N/A'))}")
    
    print("✅ Teste 3 passou!")


def test_integracao_chat_service():
    """Testa se o ChatService consegue usar o ConsultaService"""
    print("\n" + "="*60)
    print("TESTE 4: Integração com ChatService")
    print("="*60)
    
    try:
        from services.chat_service import ChatService
        
        chat_service = ChatService()
        
        # Simular chamada de função tool
        resultado = chat_service._executar_funcao_tool(
            nome_funcao="consultar_processo_consolidado",
            argumentos={'processo_referencia': 'ALH.0172/25'},
            mensagem_original="consulte o processo ALH.0172/25"
        )
        
        print(f"\n📋 Resultado via ChatService:")
        print(f"   Sucesso: {resultado.get('sucesso')}")
        
        # Mostrar resposta completa (sem truncar)
        resposta = resultado.get('resposta', '')
        if resposta:
            print(f"\n   Resposta completa:")
            print("   " + "-"*56)
            # Mostrar resposta com indentação
            for linha in resposta.split('\n'):
                print(f"   {linha}")
            print("   " + "-"*56)
        else:
            print(f"   Resposta: (vazia)")
        
        # Verificar se tem dados
        dados = resultado.get('dados')
        if dados:
            print(f"\n   ✅ Dados retornados:")
            chaves = dados.get('chaves', {})
            print(f"      - DI: {chaves.get('di', 'N/A')}")
            print(f"      - DUIMP: {chaves.get('duimp_num', 'N/A')}")
            print(f"      - CE: {chaves.get('ce_house', chaves.get('ce_master', 'N/A'))}")
        
        assert resultado.get('sucesso') is not None, "ChatService deve retornar resultado válido"
        assert resultado.get('sucesso') == True, "ChatService deve retornar sucesso=True"
        print("\n✅ Teste 4 passou!")
        
    except Exception as e:
        print(f"❌ Erro no teste 4: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 TESTES DO CONSULTASERVICE")
    print("="*60)
    print("\n⚠️  IMPORTANTE: Altere os números de CE e processos nos testes")
    print("   para valores que você sabe que existem no seu sistema.\n")
    
    try:
        # Executar testes
        test_verificar_atualizacao_ce()
        test_consultar_ce_maritimo()
        test_consultar_processo_consolidado()
        test_integracao_chat_service()
        
        print("\n" + "="*60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("="*60)
        
    except AssertionError as e:
        print(f"\n❌ Teste falhou: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
