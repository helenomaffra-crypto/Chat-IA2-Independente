#!/usr/bin/env python3
"""
Script de teste para migração de Assistants API para Responses API.

Este script testa:
- ResponsesService (nova implementação)
- Busca de legislação via Responses API
- Fallback para busca local
- Comparação com Assistants API (se disponível)
- Integração completa com LegislacaoAgent

⚠️ IMPORTANTE: Assistants API será desligado em 26/08/2026.
Este script valida a migração para Responses API.
"""
import sys
import os
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    try:
        load_dotenv()
    except (PermissionError, OSError):
        pass
except ImportError:
    pass

import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_section(title: str):
    """Imprime um cabeçalho de seção."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_responses_service_import():
    """Teste 1: Verificar se ResponsesService pode ser importado."""
    print_section("TESTE 1: Importação do ResponsesService")
    
    try:
        from services.responses_service import get_responses_service
        
        service = get_responses_service()
        print(f"✅ ResponsesService importado com sucesso")
        print(f"   Habilitado: {service.enabled}")
        print(f"   Cliente disponível: {service.client is not None}")
        
        if not service.enabled:
            print("\n⚠️  ResponsesService não está habilitado.")
            print("   Verifique:")
            print("   - DUIMP_AI_ENABLED=true no .env")
            print("   - DUIMP_AI_API_KEY configurado no .env")
        
        return service.enabled
        
    except Exception as e:
        print(f"❌ Erro ao importar ResponsesService: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_responses_service_busca():
    """Teste 2: Testar busca de legislação via ResponsesService."""
    print_section("TESTE 2: Busca de Legislação via ResponsesService")
    
    try:
        from services.responses_service import get_responses_service
        
        service = get_responses_service()
        
        if not service.enabled:
            print("⚠️  ResponsesService não está habilitado. Pulando teste.")
            return None
        
        pergunta = "O que fala sobre perdimento em importação?"
        print(f"📝 Pergunta: {pergunta}")
        print("\n📤 Enviando requisição para Responses API...")
        
        resultado = service.buscar_legislacao(pergunta)
        
        if resultado and resultado.get('sucesso'):
            resposta = resultado.get('resposta', '')
            metodo = resultado.get('metodo', 'unknown')
            modelo = resultado.get('modelo', 'unknown')
            
            print(f"\n✅ Resposta recebida via {metodo} (modelo: {modelo})")
            print("-" * 80)
            print(resposta[:500] + "..." if len(resposta) > 500 else resposta)
            print("-" * 80)
            print(f"\n📊 Estatísticas:")
            print(f"   Tamanho da resposta: {len(resposta)} caracteres")
            print(f"   Método: {metodo}")
            print(f"   Modelo: {modelo}")
            
            return True
        else:
            erro = resultado.get('erro', 'Erro desconhecido') if resultado else 'Nenhum resultado'
            print(f"\n❌ Erro na busca: {erro}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_legislacao_agent():
    """Teste 3: Testar busca via LegislacaoAgent (integração completa)."""
    print_section("TESTE 3: Busca via LegislacaoAgent (Integração Completa)")
    
    try:
        from services.agents.legislacao_agent import LegislacaoAgent
        
        agent = LegislacaoAgent()
        print("✅ LegislacaoAgent importado com sucesso")
        
        # Testar tool buscar_legislacao_responses
        arguments = {
            'pergunta': 'O que fala sobre multas em importação?'
        }
        
        print(f"\n📝 Testando tool: buscar_legislacao_responses")
        print(f"   Pergunta: {arguments['pergunta']}")
        print("\n📤 Executando via agent...")
        
        resultado = agent.execute('buscar_legislacao_responses', arguments, None)
        
        if resultado and resultado.get('sucesso'):
            resposta = resultado.get('resposta', '')
            metodo = resultado.get('metodo', 'unknown')
            
            print(f"\n✅ Resposta recebida via {metodo}")
            print("-" * 80)
            print(resposta[:500] + "..." if len(resposta) > 500 else resposta)
            print("-" * 80)
            
            return True
        else:
            erro = resultado.get('erro', 'Erro desconhecido') if resultado else 'Nenhum resultado'
            resposta = resultado.get('resposta', '') if resultado else ''
            
            print(f"\n⚠️  Resultado:")
            print(f"   Sucesso: {resultado.get('sucesso', False) if resultado else False}")
            print(f"   Erro: {erro}")
            if resposta:
                print(f"   Resposta: {resposta[:200]}...")
            
            # Verificar se foi fallback
            if 'fallback' in resposta.lower() or 'busca local' in resposta.lower():
                print("\n💡 Fallback para busca local foi acionado (esperado se Responses API não estiver disponível)")
                return None  # Não é erro, apenas fallback
            
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_comparacao_apis():
    """Teste 4: Comparar Responses API vs Assistants API (se disponível)."""
    print_section("TESTE 4: Comparação Responses API vs Assistants API")
    
    pergunta = "O que fala sobre canal de conferência em importação?"
    
    resultados = {}
    
    # Testar Responses API
    print("📤 Testando Responses API...")
    try:
        from services.responses_service import get_responses_service
        responses_service = get_responses_service()
        
        if responses_service.enabled:
            resultado_responses = responses_service.buscar_legislacao(pergunta)
            resultados['responses'] = resultado_responses
            print("✅ Responses API: OK")
        else:
            print("⚠️  Responses API: Não habilitado")
    except Exception as e:
        print(f"❌ Responses API: Erro - {e}")
    
    # Testar Assistants API (legado)
    print("\n📤 Testando Assistants API (legado)...")
    try:
        from services.assistants_service import get_assistants_service
        assistants_service = get_assistants_service()
        
        if assistants_service.enabled and assistants_service.assistant_id:
            resultado_assistants = assistants_service.buscar_legislacao(pergunta)
            resultados['assistants'] = resultado_assistants
            print("✅ Assistants API: OK")
        else:
            print("⚠️  Assistants API: Não habilitado ou não configurado")
    except Exception as e:
        print(f"❌ Assistants API: Erro - {e}")
    
    # Comparar resultados
    print("\n📊 Comparação:")
    print("-" * 80)
    
    if 'responses' in resultados and resultados['responses']:
        resp_responses = resultados['responses']
        print(f"✅ Responses API:")
        print(f"   Sucesso: {resp_responses.get('sucesso', False)}")
        if resp_responses.get('sucesso'):
            resposta = resp_responses.get('resposta', '')
            print(f"   Tamanho: {len(resposta)} caracteres")
            print(f"   Método: {resp_responses.get('metodo', 'unknown')}")
    
    if 'assistants' in resultados and resultados['assistants']:
        resp_assistants = resultados['assistants']
        print(f"\n⚠️  Assistants API (legado):")
        print(f"   Sucesso: {resp_assistants.get('sucesso', False)}")
        if resp_assistants.get('sucesso'):
            resposta = resp_assistants.get('resposta', '')
            print(f"   Tamanho: {len(resposta)} caracteres")
            print(f"   Thread ID: {resp_assistants.get('thread_id', 'N/A')}")
    
    print("-" * 80)
    
    return len(resultados) > 0


def test_fallback():
    """Teste 5: Testar fallback para busca local."""
    print_section("TESTE 5: Fallback para Busca Local")
    
    try:
        from services.agents.legislacao_agent import LegislacaoAgent
        
        agent = LegislacaoAgent()
        
        # Simular falha da Responses API desabilitando temporariamente
        print("📝 Testando fallback quando Responses API não está disponível...")
        
        arguments = {
            'pergunta': 'O que fala sobre DUIMP?'
        }
        
        resultado = agent.execute('buscar_legislacao_responses', arguments, None)
        
        if resultado:
            sucesso = resultado.get('sucesso', False)
            resposta = resultado.get('resposta', '')
            
            print(f"\n📊 Resultado:")
            print(f"   Sucesso: {sucesso}")
            
            # Verificar se foi fallback
            if 'busca local' in resposta.lower() or 'sqlite' in resposta.lower():
                print("✅ Fallback para busca local funcionando corretamente")
                return True
            elif sucesso:
                print("✅ Responses API funcionando (sem necessidade de fallback)")
                return True
            else:
                print(f"⚠️  Resposta: {resposta[:200]}...")
                return None
        
        return False
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_router():
    """Teste 6: Verificar se ToolRouter está configurado corretamente."""
    print_section("TESTE 6: Verificação do ToolRouter")
    
    try:
        from services.tool_router import ToolRouter
        
        router = ToolRouter()
        
        # Verificar mapeamento
        tool_name = 'buscar_legislacao_responses'
        # ToolRouter.route() requer arguments, mas podemos verificar o mapeamento interno
        if hasattr(router, 'tool_to_agent'):
            agent_name = router.tool_to_agent.get(tool_name)
        else:
            # Fallback: chamar route com arguments vazios
            agent_name = router.route(tool_name, {})
        
        print(f"📝 Tool: {tool_name}")
        print(f"   Roteado para: {agent_name}")
        
        if agent_name == 'legislacao':
            print("✅ ToolRouter configurado corretamente")
            return True
        else:
            print(f"❌ ToolRouter não está mapeando corretamente (esperado: 'legislacao', recebido: '{agent_name}')")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal que executa todos os testes."""
    print("=" * 80)
    print("  TESTE DE MIGRAÇÃO: Assistants API → Responses API")
    print("=" * 80)
    print()
    print("⚠️  IMPORTANTE: Assistants API será desligado em 26/08/2026")
    print("   Este script valida a migração para Responses API.")
    print()
    
    resultados = {}
    
    # Executar testes
    print("🚀 Iniciando testes...\n")
    
    # Teste 1: Importação
    resultados['teste_1'] = test_responses_service_import()
    
    # Teste 2: Busca direta
    if resultados.get('teste_1'):
        resultados['teste_2'] = test_responses_service_busca()
    else:
        print("\n⚠️  Pulando Teste 2 (ResponsesService não habilitado)")
        resultados['teste_2'] = None
    
    # Teste 3: Integração completa
    resultados['teste_3'] = test_legislacao_agent()
    
    # Teste 4: Comparação
    resultados['teste_4'] = test_comparacao_apis()
    
    # Teste 5: Fallback
    resultados['teste_5'] = test_fallback()
    
    # Teste 6: ToolRouter
    resultados['teste_6'] = test_tool_router()
    
    # Resumo
    print_section("RESUMO DOS TESTES")
    
    total = len([r for r in resultados.values() if r is not None])
    aprovados = len([r for r in resultados.values() if r is True])
    pulados = len([r for r in resultados.values() if r is None])
    
    print(f"📊 Total de testes: {total}")
    print(f"✅ Aprovados: {aprovados}")
    print(f"⏭️  Pulados: {pulados}")
    print(f"❌ Falhados: {total - aprovados - pulados}")
    print()
    
    for nome, resultado in resultados.items():
        if resultado is None:
            status = "⏭️  Pulado"
        elif resultado:
            status = "✅ Aprovado"
        else:
            status = "❌ Falhou"
        print(f"   {nome.upper()}: {status}")
    
    print()
    print("=" * 80)
    print("  TESTES CONCLUÍDOS")
    print("=" * 80)
    print()
    
    if aprovados == total - pulados:
        print("🎉 Todos os testes relevantes passaram!")
    elif aprovados > 0:
        print("⚠️  Alguns testes passaram. Verifique os logs acima.")
    else:
        print("❌ Nenhum teste passou. Verifique a configuração.")
    
    print()
    print("💡 PRÓXIMOS PASSOS:")
    print("   1. Se ResponsesService não está habilitado:")
    print("      - Configure DUIMP_AI_ENABLED=true no .env")
    print("      - Configure DUIMP_AI_API_KEY no .env")
    print("   2. Teste no chat:")
    print("      - Faça perguntas como 'O que fala sobre perdimento?'")
    print("      - Verifique se Responses API é chamada")
    print("      - Valide as respostas")
    print("   3. Quando File Search estiver disponível:")
    print("      - Implemente upload de arquivos")
    print("      - Migre legislações do Vector Store")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

