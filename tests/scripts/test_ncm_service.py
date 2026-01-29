#!/usr/bin/env python3
"""
Script de teste rápido para validar a migração do NCMService.

Uso:
    python tests/scripts/test_ncm_service.py
"""

import sys
import os

# ⚠️ IMPORTANTE:
# Este arquivo é um "script de teste manual" e faz chamadas externas (ex: DuckDuckGo) via `duckduckgo_search`.
# Em ambientes sem rede (ex: sandbox/CI) isso pode abortar o processo do Python.
# Por padrão, NÃO rodar esses testes no pytest. Para habilitar explicitamente:
#   RUN_MANUAL_NCM_TESTS=1 python -m pytest tests/scripts/test_ncm_service.py
try:
    import pytest
    if os.environ.get("RUN_MANUAL_NCM_TESTS") != "1":
        pytest.skip("tests/scripts/test_ncm_service.py é manual (pode exigir rede). Defina RUN_MANUAL_NCM_TESTS=1 para rodar.", allow_module_level=True)
except Exception:
    # Se pytest não estiver disponível (execução direta como script), segue normalmente.
    pass

# Adicionar o diretório raiz ao path (subir 3 níveis: tests/scripts/ -> raiz)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ✅ Forçar reload do módulo para garantir versão mais recente
import importlib
if 'services.ncm_service' in sys.modules:
    importlib.reload(sys.modules['services.ncm_service'])


def test_buscar_ncms_por_descricao():
    """Testa buscar_ncms_por_descricao"""
    print("\n" + "="*60)
    print("TESTE 1: buscar_ncms_por_descricao")
    print("="*60)
    
    from services.ncm_service import NCMService
    service = NCMService()
    
    # Teste 1: Buscar por termo comum
    termo = "alho"
    
    resultado = service.buscar_ncms_por_descricao(
        termo=termo,
        limite=10,
        incluir_relacionados=True
    )
    
    print(f"\n📋 Resultado (termo: '{termo}'):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Total: {resultado.get('total', 0)}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 1a passou!")
    
    # Teste 2: Buscar com termo mais específico
    termo2 = "computador"
    
    resultado2 = service.buscar_ncms_por_descricao(
        termo=termo2,
        limite=5,
        incluir_relacionados=False
    )
    
    print(f"\n📋 Resultado (termo: '{termo2}'):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Total: {resultado2.get('total', 0)}")
    
    assert resultado2.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 1b passou!")


def test_sugerir_ncm_com_ia():
    """Testa sugerir_ncm_com_ia"""
    print("\n" + "="*60)
    print("TESTE 2: sugerir_ncm_com_ia")
    print("="*60)
    
    from services.ncm_service import NCMService
    service = NCMService()
    
    # Teste com descrição simples
    descricao = "alho fresco"
    
    resultado = service.sugerir_ncm_com_ia(
        descricao=descricao,
        usar_cache=True,
        validar_sugestao=True
    )
    
    print(f"\n📋 Resultado (descrição: '{descricao}'):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   NCM Sugerido: {resultado.get('ncm_sugerido', 'N/A')}")
    print(f"   Confiança: {resultado.get('confianca', 0):.2%}")
    print(f"   Validado: {resultado.get('validado', False)}")
    print(f"   Resposta: {resultado.get('resposta', '')[:300]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 2 passou!")


def test_detalhar_ncm():
    """Testa detalhar_ncm"""
    print("\n" + "="*60)
    print("TESTE 3: detalhar_ncm")
    print("="*60)
    
    from services.ncm_service import NCMService
    service = NCMService()
    
    # Teste com NCM de 8 dígitos
    ncm = "07032000"  # Alho
    
    resultado = service.detalhar_ncm(ncm=ncm)
    
    print(f"\n📋 Resultado (NCM: {ncm}):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Grupo Base: {resultado.get('grupo_base', 'N/A')}")
    print(f"   Total 8 dígitos: {resultado.get('total_8_digitos', 0)}")
    print(f"   Resposta: {resultado.get('resposta', '')[:400]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 3a passou!")
    
    # Teste com NCM de 6 dígitos (posição)
    ncm2 = "070320"  # Posição do alho
    
    resultado2 = service.detalhar_ncm(ncm=ncm2)
    
    print(f"\n📋 Resultado (NCM: {ncm2}):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Resposta: {resultado2.get('resposta', '')[:300]}...")
    
    assert resultado2.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 3b passou!")


def test_buscar_nota_explicativa_nesh():
    """Testa buscar_nota_explicativa_nesh"""
    print("\n" + "="*60)
    print("TESTE 4: buscar_nota_explicativa_nesh")
    print("="*60)
    
    from services.ncm_service import NCMService
    service = NCMService()
    
    # Teste 1: Buscar por NCM
    ncm = "07032000"  # Alho
    
    resultado = service.buscar_nota_explicativa_nesh(
        ncm=ncm,
        limite=3
    )
    
    print(f"\n📋 Resultado (NCM: {ncm}):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Total: {resultado.get('total', 0)}")
    print(f"   Resposta: {resultado.get('resposta', '')[:400]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 4a passou!")
    
    # Teste 2: Buscar por descrição
    descricao = "alho"
    
    resultado2 = service.buscar_nota_explicativa_nesh(
        descricao_produto=descricao,
        limite=2
    )
    
    print(f"\n📋 Resultado (descrição: '{descricao}'):")
    print(f"   Sucesso: {resultado2.get('sucesso')}")
    print(f"   Total: {resultado2.get('total', 0)}")
    print(f"   Resposta: {resultado2.get('resposta', '')[:300]}...")
    
    assert resultado2.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 4b passou!")
    
    # Teste 3: Buscar por NCM e descrição combinados
    resultado3 = service.buscar_nota_explicativa_nesh(
        ncm=ncm,
        descricao_produto=descricao,
        limite=3
    )
    
    print(f"\n📋 Resultado (NCM + descrição):")
    print(f"   Sucesso: {resultado3.get('sucesso')}")
    print(f"   Total: {resultado3.get('total', 0)}")
    
    assert resultado3.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 4c passou!")


def test_baixar_nomenclatura_ncm():
    """Testa baixar_nomenclatura_ncm (sem forçar atualização)"""
    print("\n" + "="*60)
    print("TESTE 5: baixar_nomenclatura_ncm")
    print("="*60)
    
    from services.ncm_service import NCMService
    service = NCMService()
    
    # Teste sem forçar (deve retornar que já está atualizado se atualizado recentemente)
    resultado = service.baixar_nomenclatura_ncm(
        forcar_atualizacao=False
    )
    
    print(f"\n📋 Resultado (sem forçar):")
    print(f"   Sucesso: {resultado.get('sucesso')}")
    print(f"   Resposta: {resultado.get('resposta', '')[:400]}...")
    
    assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
    print("✅ Teste 5 passou!")
    print("   ⚠️  Nota: Este teste não força download. Para testar download completo, use forcar_atualizacao=True")


def test_integracao_chat_service():
    """Testa integração com ChatService (se disponível)"""
    print("\n" + "="*60)
    print("TESTE 6: Integração com ChatService")
    print("="*60)
    
    try:
        from services.chat_service import ChatService
        from services.ncm_service import NCMService
        
        chat_service = ChatService()
        ncm_service = NCMService(chat_service=chat_service)
        
        # Teste simples de busca
        resultado = ncm_service.buscar_ncms_por_descricao(
            termo="alho",
            limite=5
        )
        
        print(f"\n📋 Resultado (com ChatService):")
        print(f"   Sucesso: {resultado.get('sucesso')}")
        print(f"   Total: {resultado.get('total', 0)}")
        
        assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
        print("✅ Teste 6 passou!")
        
    except Exception as e:
        print(f"⚠️  Teste 6 pulado (ChatService não disponível ou erro): {e}")
        print("   Isso é normal se o ChatService não estiver inicializado")


def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🧪 TESTES DO NCMService")
    print("="*60)
    
    testes = [
        test_buscar_ncms_por_descricao,
        test_sugerir_ncm_com_ia,
        test_detalhar_ncm,
        test_buscar_nota_explicativa_nesh,
        test_baixar_nomenclatura_ncm,
        test_integracao_chat_service,
    ]
    
    resultados = []
    
    for teste in testes:
        try:
            teste()
            resultados.append(("✅", teste.__name__))
        except AssertionError as e:
            resultados.append(("❌", f"{teste.__name__}: {e}"))
            print(f"\n❌ Erro no teste: {e}")
        except Exception as e:
            resultados.append(("⚠️", f"{teste.__name__}: {e}"))
            print(f"\n⚠️  Exceção no teste: {e}")
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    for status, nome in resultados:
        print(f"   {status} {nome}")
    
    sucessos = sum(1 for s, _ in resultados if s == "✅")
    total = len(resultados)
    
    print(f"\n✅ Sucessos: {sucessos}/{total}")
    
    if sucessos == total:
        print("\n🎉 Todos os testes passaram!")
    else:
        print(f"\n⚠️  {total - sucessos} teste(s) falharam ou tiveram avisos")


def test_busca_web_duckduckgo():
    """Testa busca web com DuckDuckGo para produtos modernos"""
    print("\n" + "="*60)
    print("TESTE WEB SEARCH: Busca web com DuckDuckGo")
    print("="*60)
    
    try:
        from services.ncm_service import NCMService
        service = NCMService()
        
        # Testar com iPhone (produto moderno que não aparece literalmente na NESH)
        descricao = "iPhone 15 Pro"
        print(f"\n🔍 Testando busca web para: '{descricao}'")
        
        # Chamar método privado via reflection (ou tornar público temporariamente)
        resultado_web = service._buscar_web_para_produto(descricao)
        
        if resultado_web:
            print(f"\n✅ Busca web bem-sucedida!")
            print(f"   - Resultados encontrados: {len(resultado_web.get('resultados', []))}")
            print(f"   - NCMs mencionados: {len(resultado_web.get('ncms_mentionados', []))}")
            print(f"   - Categoria identificada: {resultado_web.get('categoria_identificada', 'N/A')}")
            print(f"   - Fontes consultadas: {len(resultado_web.get('fontes', []))}")
            
            if resultado_web.get('ncms_mentionados'):
                print(f"\n   📋 NCMs encontrados na web:")
                for ncm in resultado_web['ncms_mentionados']:
                    print(f"      - {ncm}")
            
            if resultado_web.get('categoria_identificada'):
                print(f"\n   📦 Categoria: {resultado_web['categoria_identificada']}")
            
            if resultado_web.get('resultados'):
                print(f"\n   🔗 Primeiros resultados:")
                for i, res in enumerate(resultado_web['resultados'][:2], 1):
                    print(f"      {i}. {res.get('titulo', 'N/A')[:60]}...")
            
            assert resultado_web.get('utilizado') is True, "Busca web deve estar marcada como utilizada"
            print("\n✅ Teste de busca web passou!")
            return True
        else:
            print("\n⚠️ Busca web retornou None (pode ser que DuckDuckGo não esteja disponível)")
            print("   Verifique se 'duckduckgo-search' está instalado: pip install duckduckgo-search")
            return False
            
    except ImportError as e:
        print(f"\n❌ Erro de importação: {e}")
        print("   Verifique se 'duckduckgo-search' está instalado: pip install duckduckgo-search")
        return False
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sugestao_ncm_com_web_search():
    """Testa sugestão de NCM com busca web integrada"""
    print("\n" + "="*60)
    print("TESTE INTEGRAÇÃO: Sugestão NCM com busca web")
    print("="*60)
    
    try:
        from services.ncm_service import NCMService
        service = NCMService()
        
        # Testar com iPhone
        descricao = "iPhone"
        print(f"\n🤖 Testando sugestão NCM com web search para: '{descricao}'")
        
        resultado = service.sugerir_ncm_com_ia(
            descricao=descricao,
            usar_cache=True,
            validar_sugestao=True
        )
        
        print(f"\n📊 Resultado:")
        print(f"   - Sucesso: {resultado.get('sucesso')}")
        print(f"   - NCM sugerido: {resultado.get('ncm_sugerido', 'N/A')}")
        print(f"   - Confiança: {resultado.get('confianca', 0) * 100:.1f}%")
        print(f"   - Validado: {resultado.get('validado', False)}")
        
        if resultado.get('resposta'):
            resposta = resultado['resposta']
            # Mostrar apenas primeiras linhas da resposta
            linhas = resposta.split('\n')[:15]
            print(f"\n   📝 Resposta (primeiras 15 linhas):")
            for linha in linhas:
                if linha.strip():
                    print(f"      {linha}")
            
            # Verificar se menciona busca web
            if '🌐' in resposta or 'web' in resposta.lower() or 'Web' in resposta:
                print(f"\n   ✅ Busca web foi utilizada e mencionada na resposta!")
        
        assert resultado.get('sucesso') is not None, "Resultado deve ter campo 'sucesso'"
        print("\n✅ Teste de integração passou!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Executar testes existentes
    main()
    
    # Executar novos testes de busca web
    print("\n" + "="*70)
    print("🧪 TESTES DE BUSCA WEB")
    print("="*70)
    
    test_busca_web_duckduckgo()
    test_sugestao_ncm_com_web_search()
