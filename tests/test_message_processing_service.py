#!/usr/bin/env python3
"""
Testes para MessageProcessingService - Validação do refatoramento Passo 3.5.

Este script testa todos os métodos movidos do chat_service.py para o MessageProcessingService,
garantindo que a funcionalidade foi preservada corretamente.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import pytest
from services.message_processing_service import MessageProcessingService
from services.prompt_builder import PromptBuilder
from services.precheck_service import PrecheckService

# ⚠️ IMPORTANTE:
# Este arquivo foi escrito como "script de validação manual" (prints e execução sequencial),
# não como suíte pytest com fixtures. Para não quebrar `pytest tests/`, pulamos por padrão.
# Para habilitar explicitamente:
#   RUN_MANUAL_MPS_TESTS=1 python -m pytest tests/test_message_processing_service.py
if os.environ.get("RUN_MANUAL_MPS_TESTS") != "1":
    pytest.skip("tests/test_message_processing_service.py é manual. Defina RUN_MANUAL_MPS_TESTS=1 para rodar.", allow_module_level=True)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_imports():
    """Testa se todos os imports funcionam."""
    print("\n" + "="*80)
    print("TESTE 1: Imports")
    print("="*80)
    try:
        from services.message_processing_service import MessageProcessingService
        from services.prompt_builder import PromptBuilder
        from services.precheck_service import PrecheckService
        print("✅ Todos os imports funcionaram corretamente")
        return True
    except Exception as e:
        print(f"❌ Erro nos imports: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inicializacao():
    """Testa inicialização do MessageProcessingService."""
    print("\n" + "="*80)
    print("TESTE 2: Inicialização do MessageProcessingService")
    print("="*80)
    try:
        prompt_builder = PromptBuilder()
        precheck_service = PrecheckService(chat_service=None)
        
        service = MessageProcessingService(
            confirmation_handler=None,
            precheck_service=precheck_service,
            tool_execution_service=None,
            prompt_builder=prompt_builder,
            ai_service=None,
            obter_email_para_enviar=None,
            extrair_processo_referencia=None,
        )
        print("✅ MessageProcessingService inicializado com sucesso")
        return True, service
    except Exception as e:
        print(f"❌ Erro na inicialização: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_construir_contexto_str(service):
    """Testa construção de contexto_str."""
    print("\n" + "="*80)
    print("TESTE 3: Construção de contexto_str")
    print("="*80)
    try:
        # Teste 1: Contexto de processo
        contexto_str = service._construir_contexto_str(
            processo_ref="DMD.0073/25",
            contexto_processo={'encontrado': True, 'processo_referencia': 'DMD.0073/25'},
            categoria_atual=None,
            categoria_contexto=None,
            numero_ce_contexto=None,
            numero_cct=None,
            mensagem="como está o DMD.0073/25?",
            eh_pergunta_generica=False,
            eh_pergunta_pendencias=False,
            eh_pergunta_situacao=False,
            eh_fechamento_dia=False,
            acao_info={}
        )
        assert "DMD.0073/25" in contexto_str, "Contexto de processo não encontrado"
        print("✅ Contexto de processo construído corretamente")
        
        # Teste 2: Contexto de categoria
        contexto_str = service._construir_contexto_str(
            processo_ref=None,
            contexto_processo=None,
            categoria_atual="DMD",
            categoria_contexto=None,
            numero_ce_contexto=None,
            numero_cct=None,
            mensagem="como estão os DMD?",
            eh_pergunta_generica=False,
            eh_pergunta_pendencias=False,
            eh_pergunta_situacao=False,
            eh_fechamento_dia=False,
            acao_info={}
        )
        assert "DMD" in contexto_str, "Contexto de categoria não encontrado"
        print("✅ Contexto de categoria construído corretamente")
        
        # Teste 3: Contexto de CE
        contexto_str = service._construir_contexto_str(
            processo_ref=None,
            contexto_processo=None,
            categoria_atual=None,
            categoria_contexto=None,
            numero_ce_contexto="132505415819133",
            numero_cct=None,
            mensagem="como está o CE?",
            eh_pergunta_generica=False,
            eh_pergunta_pendencias=False,
            eh_pergunta_situacao=False,
            eh_fechamento_dia=False,
            acao_info={}
        )
        assert "132505415819133" in contexto_str, "Contexto de CE não encontrado"
        print("✅ Contexto de CE construído corretamente")
        
        # Teste 4: Contexto de CCT
        contexto_str = service._construir_contexto_str(
            processo_ref=None,
            contexto_processo=None,
            categoria_atual=None,
            categoria_contexto=None,
            numero_ce_contexto=None,
            numero_cct="MIA4683",
            mensagem="como está o CCT?",
            eh_pergunta_generica=False,
            eh_pergunta_pendencias=False,
            eh_pergunta_situacao=False,
            eh_fechamento_dia=False,
            acao_info={}
        )
        assert "MIA4683" in contexto_str, "Contexto de CCT não encontrado"
        print("✅ Contexto de CCT construído corretamente")
        
        return True
    except Exception as e:
        print(f"❌ Erro na construção de contexto_str: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_construir_historico_str(service):
    """Testa construção de historico_str."""
    print("\n" + "="*80)
    print("TESTE 4: Construção de historico_str")
    print("="*80)
    try:
        historico = [
            {'mensagem': 'como está o DMD.0073/25?', 'resposta': 'O processo DMD.0073/25 está...'},
            {'mensagem': 'tem pendência?', 'resposta': 'Sim, há pendências...'}
        ]
        
        def extrair_processo(msg):
            if 'DMD.0073' in msg:
                return 'DMD.0073/25'
            return None
        
        historico_str, instrucao_processo = service._construir_historico_str(
            historico=historico,
            mensagem="qual a situação?",
            processo_ref="DMD.0073/25",
            extrair_processo_referencia_fn=extrair_processo
        )
        
        assert len(historico_str) > 0, "historico_str não foi construído"
        print("✅ historico_str construído corretamente")
        print(f"   Tamanho: {len(historico_str)} caracteres")
        
        return True
    except Exception as e:
        print(f"❌ Erro na construção de historico_str: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_buscar_contexto_sessao(service):
    """Testa busca de contexto_sessao."""
    print("\n" + "="*80)
    print("TESTE 5: Busca de contexto_sessao")
    print("="*80)
    try:
        def extrair_processo(msg):
            if 'DMD.0073' in msg:
                return 'DMD.0073/25'
            return None
        
        contexto_sessao = service._buscar_contexto_sessao(
            session_id="test_session_123",
            mensagem="como está o processo?",
            processo_ref=None,
            extrair_processo_referencia_fn=extrair_processo,
            eh_fechamento_dia=False
        )
        
        # Pode ser vazio se não há contexto salvo, mas não deve dar erro
        assert isinstance(contexto_sessao, str), "contexto_sessao deve ser string"
        print("✅ Busca de contexto_sessao funcionou corretamente")
        print(f"   Resultado: {len(contexto_sessao)} caracteres")
        
        return True
    except Exception as e:
        print(f"❌ Erro na busca de contexto_sessao: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_construir_user_prompt(service):
    """Testa construção de user_prompt."""
    print("\n" + "="*80)
    print("TESTE 6: Construção de user_prompt")
    print("="*80)
    try:
        user_prompt, usar_tool_calling, system_prompt_final = service._construir_user_prompt(
            mensagem="como está o DMD.0073/25?",
            contexto_str="\n\n📋 ⚠️ CONTEXTO EXCLUSIVO DO PROCESSO DMD.0073/25",
            historico_str="\n\n📜 Histórico da conversa",
            contexto_sessao_texto="",
            acao_info={},
            resposta_base_precheck=None,
            eh_pedido_melhorar_email=False,
            email_para_melhorar_contexto=None,
            system_prompt="System prompt de teste"
        )
        
        assert len(user_prompt) > 0, "user_prompt não foi construído"
        assert isinstance(usar_tool_calling, bool), "usar_tool_calling deve ser bool"
        assert len(system_prompt_final) > 0, "system_prompt_final não foi construído"
        print("✅ user_prompt construído corretamente")
        print(f"   Tamanho: {len(user_prompt)} caracteres")
        print(f"   Usar tool calling: {usar_tool_calling}")
        
        return True
    except Exception as e:
        print(f"❌ Erro na construção de user_prompt: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_construir_prompt_completo(service):
    """Testa construção completa de prompt."""
    print("\n" + "="*80)
    print("TESTE 7: Construção completa de prompt (método principal)")
    print("="*80)
    try:
        def extrair_processo(msg):
            if 'DMD.0073' in msg:
                return 'DMD.0073/25'
            return None
        
        resultado = service.construir_prompt_completo(
            mensagem="como está o DMD.0073/25?",
            historico=[],
            session_id="test_session_123",
            nome_usuario="Teste",
            processo_ref="DMD.0073/25",
            categoria_atual=None,
            categoria_contexto=None,
            numero_ce_contexto=None,
            numero_cct=None,
            contexto_processo={'encontrado': True, 'processo_referencia': 'DMD.0073/25'},
            acao_info={},
            resposta_base_precheck=None,
            eh_pedido_melhorar_email=False,
            email_para_melhorar_contexto=None,
            eh_pergunta_generica=False,
            eh_pergunta_pendencias=False,
            eh_pergunta_situacao=False,
            precisa_contexto=False,
            eh_fechamento_dia=False,
            extrair_processo_referencia_fn=extrair_processo
        )
        
        assert 'system_prompt' in resultado, "system_prompt não está no resultado"
        assert 'user_prompt' in resultado, "user_prompt não está no resultado"
        assert 'usar_tool_calling' in resultado, "usar_tool_calling não está no resultado"
        assert len(resultado['system_prompt']) > 0, "system_prompt está vazio"
        assert len(resultado['user_prompt']) > 0, "user_prompt está vazio"
        
        print("✅ Construção completa de prompt funcionou corretamente")
        print(f"   System prompt: {len(resultado['system_prompt'])} caracteres")
        print(f"   User prompt: {len(resultado['user_prompt'])} caracteres")
        print(f"   Usar tool calling: {resultado['usar_tool_calling']}")
        
        return True
    except Exception as e:
        print(f"❌ Erro na construção completa de prompt: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_modo_legislacao_estrita(service):
    """Testa detecção de modo legislação estrita."""
    print("\n" + "="*80)
    print("TESTE 8: Modo legislação estrita")
    print("="*80)
    try:
        # Teste com pergunta que deve ativar modo estrito
        user_prompt, usar_tool_calling, system_prompt_final = service._construir_user_prompt(
            mensagem="qual a base legal para perdimento?",
            contexto_str="",
            historico_str="",
            contexto_sessao_texto="",
            acao_info={},
            resposta_base_precheck=None,
            eh_pedido_melhorar_email=False,
            email_para_melhorar_contexto=None,
            system_prompt="System prompt de teste"
        )
        
        # Verificar se modo estrito foi detectado (pode não encontrar trechos, mas deve tentar)
        print("✅ Modo legislação estrita testado (pode não encontrar trechos se legislação não estiver importada)")
        print(f"   Usar tool calling: {usar_tool_calling}")
        
        return True
    except Exception as e:
        print(f"❌ Erro no modo legislação estrita: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes."""
    print("\n" + "="*80)
    print("TESTES DO MessageProcessingService - Refatoramento Passo 3.5")
    print("="*80)
    
    resultados = []
    
    # Teste 1: Imports
    resultados.append(("Imports", test_imports()))
    
    # Teste 2: Inicialização
    sucesso, service = test_inicializacao()
    resultados.append(("Inicialização", sucesso))
    
    if not sucesso or service is None:
        print("\n❌ Não foi possível inicializar o serviço. Parando testes.")
        return
    
    # Teste 3: Construção de contexto_str
    resultados.append(("Construção de contexto_str", test_construir_contexto_str(service)))
    
    # Teste 4: Construção de historico_str
    resultados.append(("Construção de historico_str", test_construir_historico_str(service)))
    
    # Teste 5: Busca de contexto_sessao
    resultados.append(("Busca de contexto_sessao", test_buscar_contexto_sessao(service)))
    
    # Teste 6: Construção de user_prompt
    resultados.append(("Construção de user_prompt", test_construir_user_prompt(service)))
    
    # Teste 7: Construção completa de prompt
    resultados.append(("Construção completa de prompt", test_construir_prompt_completo(service)))
    
    # Teste 8: Modo legislação estrita
    resultados.append(("Modo legislação estrita", test_modo_legislacao_estrita(service)))
    
    # Resumo
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)
    
    total = len(resultados)
    passou = sum(1 for _, resultado in resultados if resultado)
    falhou = total - passou
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status}: {nome}")
    
    print(f"\nTotal: {total} | Passou: {passou} | Falhou: {falhou}")
    
    if falhou == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return 0
    else:
        print(f"\n⚠️ {falhou} TESTE(S) FALHARAM")
        return 1


if __name__ == "__main__":
    sys.exit(main())
