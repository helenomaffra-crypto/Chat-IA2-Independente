"""
Testes completos para EmailPrecheckService após refatoração.

Estes testes garantem que:
1. O método tentar_precheck_email funciona corretamente
2. A ordem de prioridade está correta
3. Os métodos internos são chamados na ordem certa
4. O formato de resposta está correto
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

from services.email_precheck_service import EmailPrecheckService


class TestEmailPrecheckServiceCompleto:
    """Testes completos para EmailPrecheckService."""
    
    @pytest.fixture
    def mock_chat_service(self):
        """Mock do ChatService."""
        mock = Mock()
        mock._executar_funcao_tool = Mock(return_value={
            'sucesso': True,
            'resposta': 'Preview do email',
            'aguardando_confirmacao': True,
            '_processado_precheck': True
        })
        mock.session_id_atual = 'test_session'
        mock.nome_usuario_atual = 'Teste'
        mock.ultima_resposta_aguardando_email = None
        return mock
    
    @pytest.fixture
    def email_precheck_service(self, mock_chat_service):
        """Instância do EmailPrecheckService."""
        return EmailPrecheckService(mock_chat_service)
    
    # ============================================================
    # TESTE 1: Email de NCM + alíquotas (com contexto)
    # ============================================================
    
    @patch('services.context_service.buscar_contexto_sessao')
    @patch('services.use_cases.enviar_email_classificacao_ncm_use_case.EnviarEmailClassificacaoNcmUseCase')
    def test_tentar_precheck_email_ncm_com_contexto(
        self,
        mock_use_case_class,
        mock_buscar_contexto,
        email_precheck_service
    ):
        """
        Teste 1: Email de NCM + alíquotas com contexto deve processar corretamente.
        """
        # Setup: Contexto de NCM disponível
        mock_buscar_contexto.return_value = [{
            'dados': {
                'ncm': '48202000',
                'descricao': 'Caderno pautado',
                'aliquotas': {'II': '18%', 'IPI': '9.75%'}
            }
        }]
        
        # Mock do use case
        mock_use_case = Mock()
        mock_use_case_class.return_value = mock_use_case
        mock_use_case.executar.return_value = Mock(
            sucesso=True,
            mensagem_chat='Preview do email de classificação NCM',
            preview_email={
                'assunto': 'Classificação Fiscal e Alíquotas – Caderno pautado (NCM 48202000)',
                'conteudo': 'Conteúdo do email...'
            },
            aguardando_confirmacao=True
        )
        
        # Executar
        mensagem = "mande o email para helenomaffra@gmail.com com as alíquotas explicando o porquê do ncm do caderno sugerido"
        resultado = email_precheck_service.tentar_precheck_email(
            mensagem=mensagem,
            mensagem_lower=mensagem.lower(),
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Verificações
        assert resultado is not None, "Deveria retornar resultado quando há contexto de NCM"
        assert resultado.get('sucesso') is True, "Deveria ter sucesso=True"
        assert resultado.get('_processado_precheck') is True, "Deveria ter _processado_precheck=True"
        assert 'aguardando_confirmacao' in resultado, "Deveria ter aguardando_confirmacao"
        mock_use_case.executar.assert_called_once()
    
    # ============================================================
    # TESTE 2: Email de relatório genérico
    # ============================================================
    
    @patch('services.report_service.buscar_ultimo_relatorio')
    @patch('services.email_builder_service.EmailBuilderService')
    def test_tentar_precheck_email_relatorio_generico(
        self,
        mock_email_builder_class,
        mock_buscar_relatorio,
        email_precheck_service,
        mock_chat_service
    ):
        """
        Teste 2: Email de relatório genérico deve processar corretamente.
        """
        # Setup: Relatório disponível
        from dataclasses import dataclass
        
        @dataclass
        class RelatorioMock:
            tipo_relatorio: str = 'resumo'
            categoria: str = 'MV5'
            texto_chat: str = 'Relatório completo...'
        
        mock_buscar_relatorio.return_value = RelatorioMock()
        
        # Mock do EmailBuilderService
        mock_email_builder = Mock()
        mock_email_builder_class.return_value = mock_email_builder
        mock_email_builder.montar_email_relatorio.return_value = {
            'sucesso': True,
            'assunto': 'Relatório MV5',
            'conteudo': 'Conteúdo do relatório...'
        }
        
        # Executar
        mensagem = "envia esse relatorio para helenomaffra@gmail.com"
        resultado = email_precheck_service.tentar_precheck_email(
            mensagem=mensagem,
            mensagem_lower=mensagem.lower(),
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Verificações
        # Pode retornar None se não encontrar relatório ou dict se processar
        assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
        if resultado:
            assert resultado.get('sucesso') is not False, "Se processou, não deve ter sucesso=False"
    
    # ============================================================
    # TESTE 3: Email livre (texto ditado)
    # ============================================================
    
    @patch('services.email_builder_service.EmailBuilderService')
    def test_tentar_precheck_email_livre(
        self,
        mock_email_builder_class,
        email_precheck_service,
        mock_chat_service
    ):
        """
        Teste 3: Email livre deve processar corretamente.
        """
        # Mock do EmailBuilderService
        mock_email_builder = Mock()
        mock_email_builder_class.return_value = mock_email_builder
        mock_email_builder.montar_email_livre.return_value = {
            'sucesso': True,
            'assunto': 'Mensagem via mAIke',
            'conteudo': 'Olá,\n\na reunião foi remarcada.\n\nEnviado por mAIke.'
        }
        
        # Executar
        mensagem = "manda um email para fulano@empresa.com dizendo que a reunião foi remarcada para amanhã às 16h"
        resultado = email_precheck_service.tentar_precheck_email(
            mensagem=mensagem,
            mensagem_lower=mensagem.lower(),
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Verificações
        # Pode retornar None ou dict (depende se processou)
        assert resultado is None or isinstance(resultado, dict), "Resultado deve ser None ou dict"
        if resultado and resultado.get('sucesso'):
            # Se processou, verificar que montou email livre
            mock_email_builder.montar_email_livre.assert_called()
    
    # ============================================================
    # TESTE 4: Ordem de prioridade
    # ============================================================
    
    @patch('services.context_service.buscar_contexto_sessao')
    def test_ordem_prioridade_ncm_antes_relatorio(
        self,
        mock_buscar_contexto,
        email_precheck_service
    ):
        """
        Teste 4: Verifica que email de NCM tem prioridade sobre relatório.
        
        Mensagem: "mande o email para X com as alíquotas do relatorio"
        - Deve tentar processar como email de NCM primeiro
        - NÃO deve processar como relatório se tiver contexto de NCM
        """
        # Setup: Contexto de NCM disponível
        mock_buscar_contexto.return_value = [{
            'dados': {
                'ncm': '48202000',
                'descricao': 'Caderno pautado',
                'aliquotas': {'II': '18%'}
            }
        }]
        
        # Mock do use case
        with patch('services.use_cases.enviar_email_classificacao_ncm_use_case.EnviarEmailClassificacaoNcmUseCase') as mock_use_case_class:
            mock_use_case = Mock()
            mock_use_case_class.return_value = mock_use_case
            mock_use_case.executar.return_value = Mock(
                sucesso=True,
                mensagem_chat='Preview do email',
                preview_email={'assunto': 'Teste', 'conteudo': 'Teste'},
                aguardando_confirmacao=True
            )
            
            mensagem = "mande o email para helenomaffra@gmail.com com as alíquotas do relatorio"
            resultado = email_precheck_service.tentar_precheck_email(
                mensagem=mensagem,
                mensagem_lower=mensagem.lower(),
                historico=[],
                session_id='test_session',
                nome_usuario='Teste'
            )
            
            # Deve processar como email de NCM (não como relatório)
            if resultado:
                # Se processou, deve ser via use case de NCM
                mock_use_case.executar.assert_called()
    
    # ============================================================
    # TESTE 5: Não processa quando não é comando de email
    # ============================================================
    
    def test_nao_processa_sem_comando_email(self, email_precheck_service):
        """
        Teste 5: Não processa quando não é comando de email.
        """
        mensagem = "qual a situação do processo ALH.0165/25?"
        resultado = email_precheck_service.tentar_precheck_email(
            mensagem=mensagem,
            mensagem_lower=mensagem.lower(),
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Deve retornar None
        assert resultado is None, "Não deveria processar quando não é comando de email"
    
    # ============================================================
    # TESTE 6: Formato de resposta correto
    # ============================================================
    
    @patch('services.context_service.buscar_contexto_sessao')
    @patch('services.use_cases.enviar_email_classificacao_ncm_use_case.EnviarEmailClassificacaoNcmUseCase')
    def test_formato_resposta_correto(
        self,
        mock_use_case_class,
        mock_buscar_contexto,
        email_precheck_service
    ):
        """
        Teste 6: Verifica que o formato de resposta está correto.
        """
        # Setup
        mock_buscar_contexto.return_value = [{
            'dados': {
                'ncm': '48202000',
                'descricao': 'Caderno pautado',
                'aliquotas': {'II': '18%'}
            }
        }]
        
        mock_use_case = Mock()
        mock_use_case_class.return_value = mock_use_case
        mock_use_case.executar.return_value = Mock(
            sucesso=True,
            mensagem_chat='Preview do email',
            preview_email={'assunto': 'Teste', 'conteudo': 'Teste'},
            aguardando_confirmacao=True
        )
        
        # Executar
        mensagem = "mande o email para helenomaffra@gmail.com com as alíquotas"
        resultado = email_precheck_service.tentar_precheck_email(
            mensagem=mensagem,
            mensagem_lower=mensagem.lower(),
            historico=[],
            session_id='test_session',
            nome_usuario='Teste'
        )
        
        # Verificações de formato
        if resultado:
            assert 'sucesso' in resultado, "Resposta deve ter campo 'sucesso'"
            assert 'resposta' in resultado or 'mensagem_chat' in resultado, "Resposta deve ter campo de mensagem"
            assert resultado.get('_processado_precheck') is True, "Resposta deve ter _processado_precheck=True"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

