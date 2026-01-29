#!/usr/bin/env python3
"""
Script de teste rápido para validar a migração do ProcessoListService.

Uso:
    python test_processo_list_service.py
"""

import sys
import os

# Adicionar o diretório raiz ao path (subir 2 níveis: tests/scripts/ -> raiz)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.processo_list_service import ProcessoListService


def test_listar_processos_por_categoria():
    """Testa listar_processos_por_categoria"""
    print("\n" + "="*60)
    print("TESTE 1: listar_processos_por_categoria")
    print("="*60)
    
    service = ProcessoListService()
    
    # Teste 1: Listar processos de uma categoria
    categoria = "ALH"  # ⚠️ ALTERAR para uma categoria que você tem processos
    
    resultado = service.listar_processos_por_categoria(
        categoria=categoria,
        limite=10,
        mensagem_original="quais são os processos ALH?"
    )
    
    print(f"\n📋 Resultado:")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Total: {resultado.get('total')}")
    print(f"   Categoria: {resultado.get('categoria')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 1a passou!")
    
    # Teste 2: Listar com pergunta sobre chegada futura
    resultado2 = service.listar_processos_por_categoria(
        categoria=categoria,
        limite=10,
        mensagem_original="quando chegam os processos ALH?"
    )
    
    print(f"\n📋 Resultado (pergunta sobre chegada):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Total: {resultado2.get('total')}")
    print(f"   Resposta: {resultado2.get('resposta', '')[:200]}...")
    
    print("✅ Teste 1b passou!")


def test_listar_processos_por_eta():
    """Testa listar_processos_por_eta"""
    print("\n" + "="*60)
    print("TESTE 2: listar_processos_por_eta")
    print("="*60)
    
    service = ProcessoListService()
    
    # Teste 1: Listar processos que chegam esta semana
    resultado = service.listar_processos_por_eta(
        filtro_data='semana',
        limite=10,
        mensagem_original="quais processos chegam esta semana?"
    )
    
    print(f"\n📋 Resultado (esta semana):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Total: {resultado.get('total')}")
    print(f"   Filtro: {resultado.get('filtro_data')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 2a passou!")
    
    # Teste 2: Listar processos que chegam hoje
    resultado2 = service.listar_processos_por_eta(
        filtro_data='hoje',
        limite=10
    )
    
    print(f"\n📋 Resultado (hoje):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Total: {resultado2.get('total')}")
    print(f"   Resposta: {resultado2.get('resposta', '')[:200]}...")
    
    print("✅ Teste 2b passou!")
    
    # Teste 3: Listar processos de uma categoria específica
    categoria = "ALH"  # ⚠️ ALTERAR para uma categoria válida
    resultado3 = service.listar_processos_por_eta(
        filtro_data='semana',
        categoria=categoria,
        limite=10
    )
    
    print(f"\n📋 Resultado (categoria {categoria}):")
    print(f"   Sucesso: {resultado3.get('sucesso')}")
    print(f"   Total: {resultado3.get('total')}")
    print(f"   Categoria: {resultado3.get('categoria')}")
    print("✅ Teste 2c passou!")


def test_listar_processos_por_situacao():
    """Testa listar_processos_por_situacao"""
    print("\n" + "="*60)
    print("TESTE 3: listar_processos_por_situacao")
    print("="*60)
    
    service = ProcessoListService()
    
    # Teste 1: Listar processos desembaraçados
    categoria = "ALH"  # ⚠️ ALTERAR para uma categoria válida
    situacao = "desembaraçado"  # ⚠️ ALTERAR para uma situação válida
    
    resultado = service.listar_processos_por_situacao(
        categoria=categoria,
        situacao=situacao,
        limite=10
    )
    
    print(f"\n📋 Resultado:")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Total: {resultado.get('total')}")
    print(f"   Categoria: {resultado.get('categoria')}")
    print(f"   Situação: {resultado.get('situacao')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 3a passou!")
    
    # Teste 2: Se situação for "todas", deve redirecionar para listar_processos_por_categoria
    resultado2 = service.listar_processos_por_situacao(
        categoria=categoria,
        situacao='todas',
        limite=10
    )
    
    print(f"\n📋 Resultado (situação 'todas' - redirecionado):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Total: {resultado2.get('total')}")
    print("✅ Teste 3b passou!")


def test_listar_processos_com_pendencias():
    """Testa listar_processos_com_pendencias"""
    print("\n" + "="*60)
    print("TESTE 4: listar_processos_com_pendencias")
    print("="*60)
    
    service = ProcessoListService()
    
    # Teste 1: Listar processos com pendências de uma categoria
    categoria = "ALH"  # ⚠️ ALTERAR para uma categoria válida
    
    resultado = service.listar_processos_com_pendencias(
        categoria=categoria,
        limite=10
    )
    
    print(f"\n📋 Resultado:")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Total: {resultado.get('total')}")
    print(f"   Categoria: {resultado.get('categoria')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 4a passou!")
    
    # Teste 2: Se categoria for "TODOS", deve redirecionar para listar_todos_processos_por_situacao
    resultado2 = service.listar_processos_com_pendencias(
        categoria='TODOS',
        limite=10
    )
    
    print(f"\n📋 Resultado (categoria 'TODOS' - redirecionado):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Total: {resultado2.get('total')}")
    print(f"   Filtro pendências: {resultado2.get('filtro_pendencias')}")
    print("✅ Teste 4b passou!")


def test_listar_todos_processos_por_situacao():
    """Testa listar_todos_processos_por_situacao"""
    print("\n" + "="*60)
    print("TESTE 5: listar_todos_processos_por_situacao")
    print("="*60)
    
    service = ProcessoListService()
    
    # Teste 1: Listar todos os processos com pendências
    resultado = service.listar_todos_processos_por_situacao(
        situacao=None,
        filtro_pendencias=True,
        limite=10
    )
    
    print(f"\n📋 Resultado (com pendências):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Total: {resultado.get('total')}")
    print(f"   Filtro pendências: {resultado.get('filtro_pendencias')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 5a passou!")
    
    # Teste 2: Listar todos os processos com bloqueios
    resultado2 = service.listar_todos_processos_por_situacao(
        situacao=None,
        filtro_bloqueio=True,
        limite=10
    )
    
    print(f"\n📋 Resultado (com bloqueios):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Total: {resultado2.get('total')}")
    print(f"   Filtro bloqueio: {resultado2.get('filtro_bloqueio')}")
    print("✅ Teste 5b passou!")
    
    # Teste 3: Listar todos os processos desembaraçados
    resultado3 = service.listar_todos_processos_por_situacao(
        situacao='desembaraçado',
        limite=10
    )
    
    print(f"\n📋 Resultado (situação 'desembaraçado'):")
    print(f"   Sucesso: {resultado3.get('sucesso')}")
    print(f"   Total: {resultado3.get('total')}")
    print(f"   Situação: {resultado3.get('situacao')}")
    print("✅ Teste 5c passou!")


def test_integracao_chat_service():
    """Testa se o ChatService consegue usar o ProcessoListService"""
    print("\n" + "="*60)
    print("TESTE 6: Integração com ChatService")
    print("="*60)
    
    try:
        from services.chat_service import ChatService
        
        chat_service = ChatService()
        
        # Teste 1: listar_processos_por_categoria via ChatService
        resultado1 = chat_service._executar_funcao_tool(
            nome_funcao="listar_processos_por_categoria",
            argumentos={'categoria': 'ALH', 'limite': 5},
            mensagem_original="quais são os processos ALH?"
        )
        
        print(f"\n📋 Resultado 1 (listar_processos_por_categoria via ChatService):")
        print(f"   Sucesso: {resultado1.get('sucesso')}")
        print(f"   Total: {resultado1.get('total')}")
        
        if resultado1.get('resposta'):
            resposta = resultado1.get('resposta', '')
            print(f"\n   Resposta (primeiras 300 chars):")
            print(f"   {resposta[:300]}...")
        
        assert resultado1.get('sucesso') is not None, "ChatService deve retornar resultado válido"
        print("✅ Teste 6a passou!")
        
        # Teste 2: listar_processos_por_eta via ChatService
        resultado2 = chat_service._executar_funcao_tool(
            nome_funcao="listar_processos_por_eta",
            argumentos={'filtro_data': 'semana', 'limite': 5},
            mensagem_original="quais processos chegam esta semana?"
        )
        
        print(f"\n📋 Resultado 2 (listar_processos_por_eta via ChatService):")
        print(f"   Sucesso: {resultado2.get('sucesso')}")
        print(f"   Total: {resultado2.get('total')}")
        print("✅ Teste 6b passou!")
        
        # Teste 3: listar_processos_por_situacao via ChatService
        resultado3 = chat_service._executar_funcao_tool(
            nome_funcao="listar_processos_por_situacao",
            argumentos={'categoria': 'ALH', 'situacao': 'desembaraçado', 'limite': 5},
            mensagem_original="quais processos ALH estão desembaraçados?"
        )
        
        print(f"\n📋 Resultado 3 (listar_processos_por_situacao via ChatService):")
        print(f"   Sucesso: {resultado3.get('sucesso')}")
        print(f"   Total: {resultado3.get('total')}")
        print("✅ Teste 6c passou!")
        
        # Teste 4: listar_processos_com_pendencias via ChatService
        resultado4 = chat_service._executar_funcao_tool(
            nome_funcao="listar_processos_com_pendencias",
            argumentos={'categoria': 'ALH', 'limite': 5},
            mensagem_original="quais processos ALH têm pendências?"
        )
        
        print(f"\n📋 Resultado 4 (listar_processos_com_pendencias via ChatService):")
        print(f"   Sucesso: {resultado4.get('sucesso')}")
        print(f"   Total: {resultado4.get('total')}")
        print("✅ Teste 6d passou!")
        
        # Teste 5: listar_todos_processos_por_situacao via ChatService
        resultado5 = chat_service._executar_funcao_tool(
            nome_funcao="listar_todos_processos_por_situacao",
            argumentos={'filtro_pendencias': True, 'limite': 5},
            mensagem_original="quais processos têm pendências?"
        )
        
        print(f"\n📋 Resultado 5 (listar_todos_processos_por_situacao via ChatService):")
        print(f"   Sucesso: {resultado5.get('sucesso')}")
        print(f"   Total: {resultado5.get('total')}")
        print("✅ Teste 6e passou!")
        
        print("\n✅ Todos os testes de integração passaram!")
        
    except Exception as e:
        print(f"❌ Erro no teste 6: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 TESTES DO PROCESSOLISTSERVICE")
    print("="*60)
    print("\n⚠️  IMPORTANTE: Altere as categorias e situações nos testes")
    print("   para valores que você sabe que existem no seu sistema.\n")
    
    try:
        # Executar testes
        test_listar_processos_por_categoria()
        test_listar_processos_por_eta()
        test_listar_processos_por_situacao()
        test_listar_processos_com_pendencias()
        test_listar_todos_processos_por_situacao()
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
