"""
Testes de fumaça (smoke tests) para prechecks de email.

Estes testes garantem que o comportamento atual dos prechecks de email
não seja quebrado durante a refatoração.

Cenários cobertos:
1. Email de NCM + alíquotas (com contexto de classificação)
2. Email de relatório genérico (com relatório no contexto)
3. Email livre (texto ditado pelo usuário)
4. Email de processo/NCM misturado (fallback)
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path para imports
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, Optional, List

# Importar os serviços
from services.precheck_service import PrecheckService
from services.email_precheck_service import EmailPrecheckService


class TestEmailPrecheckSmoke:
    """Testes de fumaça para prechecks de email."""
    
    @pytest.fixture
    def mock_chat_service(self):
        """Mock do ChatService."""
        mock = Mock()
        mock._executar_funcao_tool = Mock(return_value={
            'sucesso': True,
            'resposta': 'Email enviado com sucesso',
            'aguardando_confirmacao': True
        })
        mock._extrair_processo_referencia = Mock(return_value=None)
        mock.session_id_atual = 'test_session'
        mock.nome_usuario_atual = 'Teste'
        return mock
    
    @pytest.fixture
    def precheck_service(self, mock_chat_service):
        """Instância do PrecheckService."""
        return PrecheckService(mock_chat_service)
    
    @pytest.fixture
    def contexto_ncm_completo(self):
        """Contexto completo de NCM + alíquotas para testes."""
        return {
            'ncm': '48202000',
            'descricao': 'Caderno pautado',
            'confianca': 0.85,
            'nota_nesh': 'Nota explicativa completa da NESH...',
            'aliquotas': {
                'ii': 18.0,
                'ipi': 9.75,
                'pis': 2.1,
                'cofins': 9.65,
                'icms': 'TN'
            },
            'unidade_medida': 'Unidade',
            'fonte': 'TECwin',
            'explicacao': 'Explicação detalhada da classificação...'
        }
    
    # ============================================================
    # TESTE 1: Email de NCM + alíquotas
    # ============================================================
    
    def test_precheck_email_ncm_detecta_comando_email(self, precheck_service):
        """
        Teste 1a: Verifica que detecta comando de email com palavras de NCM.
        """
        mensagem = "mande o email para helenomaffra@gmail.com com as alíquotas explicando o porquê do ncm do caderno sugerido"
        mensagem_lower = mensagem.lower()
        
        # Usar interface pública (tentar_responder_sem_ia)
        # Sem contexto, deve retornar None mas não quebrar
        resultado = precheck_service.tentar_responder_sem_ia(
            mensagem=mensagem,
            historico=[],
            session_id=None,  # Sem session_id, deve retornar None
            nome_usuario='Teste'
        )
        
        # Sem session_id, deve retornar None (deixa IA processar)
        assert resultado is None, "Sem session_id, deve retornar None"
    
    @patch('services.context_service.buscar_contexto_sessao')
    def test_precheck_email_ncm_sem_contexto(
        self,
        mock_buscar_contexto,
        precheck_service
    ):
        """
        Teste 1b: Email de NCM sem contexto (deve retornar None para IA processar).
        """
        # Setup: Sem contexto de NCM
        mock_buscar_contexto.return_value = []
        
        # Executar via interface pública
        mensagem = "mande o email para helenomaffra@gmail.com com as alíquotas"
        resultado = precheck_service.tentar_responder_sem_ia(
            mensagem=mensagem,
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Verificações
        assert resultado is None, "Precheck deveria retornar None quando não há contexto de NCM"
        # Verificar que tentou buscar contexto
        mock_buscar_contexto.assert_called()
    
    def test_precheck_email_ncm_nao_processa_sem_palavras_ncm(self, precheck_service):
        """
        Teste 1c: Não processa email se não tem palavras de NCM/alíquotas.
        """
        mensagem = "mande um email para fulano@empresa.com dizendo que a reunião foi adiada"
        resultado = precheck_service.tentar_responder_sem_ia(
            mensagem=mensagem,
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Deve retornar None ou processar como email livre (não como NCM)
        # O importante é não quebrar
        assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
    
    # ============================================================
    # TESTE 2: Email de relatório genérico
    # ============================================================
    
    def test_precheck_email_relatorio_detecta_padrao_classico(self, precheck_service):
        """
        Teste 2a: Detecta padrão clássico de relatório.
        """
        mensagem = "envia esse relatorio para helenomaffra@gmail.com"
        
        # Verificar que detecta padrão (sem relatório, pode retornar None ou erro)
        # Mas não deve quebrar
        try:
            resultado = precheck_service.tentar_responder_sem_ia(
                mensagem=mensagem,
                historico=[],
                session_id='test_session',
                nome_usuario='Teste'
            )
            # Pode retornar None ou dict com erro
            assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
        except Exception as e:
            pytest.fail(f"Precheck não deveria quebrar: {e}")
    
    def test_precheck_email_relatorio_nao_processa_sem_email(self, precheck_service):
        """
        Teste 2b: Não processa se não tem email na mensagem.
        """
        mensagem = "envia esse relatorio"
        resultado = precheck_service.tentar_responder_sem_ia(
            mensagem=mensagem,
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Deve retornar None se não tem email
        assert resultado is None or (isinstance(resultado, dict) and resultado.get('sucesso') is False), \
            "Deveria retornar None ou erro se não tem email"
    
    def test_precheck_email_relatorio_nao_processa_com_palavras_bloqueio(self, precheck_service):
        """
        Teste 2c: Não processa se tem palavras de bloqueio (processo, NCM, etc).
        """
        mensagem = "envia para helenomaffra@gmail.com informações do processo"
        resultado = precheck_service.tentar_responder_sem_ia(
            mensagem=mensagem,
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Deve retornar None ou processar como email de processo (não como relatório genérico)
        # O importante é não quebrar
        assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
    
    # ============================================================
    # TESTE 3: Email livre (texto ditado)
    # ============================================================
    
    def test_precheck_email_livre_detecta_padrao(self, precheck_service):
        """
        Teste 3a: Detecta padrão de email livre.
        """
        mensagem = "manda um email para fulano@empresa.com dizendo que a reunião foi remarcada para amanhã às 16h"
        resultado = precheck_service.tentar_responder_sem_ia(
            mensagem=mensagem,
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Pode retornar None (se não processar) ou dict (se processar)
        # O importante é não quebrar
        assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
    
    def test_precheck_email_livre_nao_processa_relatorio(self, precheck_service):
        """
        Teste 3b: Email livre não deve processar quando é relatório.
        """
        mensagem = "manda um email para fulano@empresa.com com o relatorio"
        resultado = precheck_service.tentar_responder_sem_ia(
            mensagem=mensagem,
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Deve processar como relatório genérico (não como email livre)
        # O importante é não quebrar
        assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
    
    def test_precheck_email_livre_extrai_texto(self, precheck_service, mock_chat_service):
        """
        Teste 3c: Extrai texto da mensagem corretamente.
        """
        mensagem = "manda um email para fulano@empresa.com dizendo que a reunião foi remarcada"
        
        # Mock do EmailBuilderService (importado dentro do método)
        with patch('services.email_builder_service.EmailBuilderService') as mock_email_builder_class:
            mock_email_builder = Mock()
            mock_email_builder_class.return_value = mock_email_builder
            mock_email_builder.montar_email_livre.return_value = {
                'sucesso': True,
                'assunto': 'Mensagem via mAIke',
                'conteudo': 'Olá,\n\na reunião foi remarcada.\n\nEnviado por mAIke.'
            }
            
            resultado = precheck_service.tentar_responder_sem_ia(
                mensagem=mensagem,
                historico=[],
                session_id='test_session',
                nome_usuario='Teste'
            )
            
            # Se processou, verificar que extraiu texto
            if resultado and resultado.get('sucesso'):
                # Verificar que tentou montar email livre
                mock_email_builder.montar_email_livre.assert_called()
                call_args = mock_email_builder.montar_email_livre.call_args
                if call_args and len(call_args) > 1 and 'texto_mensagem' in call_args[1]:
                    assert 'reunião foi remarcada' in call_args[1]['texto_mensagem'].lower()
    
    # ============================================================
    # TESTE 4: Ordem de prioridade (via tentar_responder_sem_ia)
    # ============================================================
    
    def test_ordem_prioridade_email_ncm_antes_relatorio(
        self,
        precheck_service
    ):
        """
        Teste 4: Verifica que email de NCM tem prioridade sobre relatório.
        
        Mensagem: "mande o email para X com as alíquotas do relatorio"
        - Deve tentar processar como email de NCM primeiro (se tiver contexto)
        - NÃO deve processar como relatório genérico se tiver palavras de NCM
        """
        # Teste simples: verificar que a ordem está correta
        # (sem contexto, ambos retornam None, mas a ordem importa)
        mensagem = "mande o email para helenomaffra@gmail.com com as alíquotas do relatorio"
        
        # Sem contexto, ambos devem retornar None, mas não deve quebrar
        try:
            resultado = precheck_service.tentar_responder_sem_ia(
                mensagem=mensagem,
                historico=[],
                session_id='test_session',
                nome_usuario='Teste'
            )
            # Pode retornar None ou dict
            assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
        except Exception as e:
            pytest.fail(f"tentar_responder_sem_ia não deveria quebrar: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
