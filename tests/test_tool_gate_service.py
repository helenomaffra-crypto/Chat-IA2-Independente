"""
Testes para ToolGateService - Fase 2A.

Testa resolução automática de contexto (report_id) para tools de relatório.
"""
import os
import sys

# Permitir rodar este arquivo diretamente via:
#   python tests/test_tool_gate_service.py
# garantindo que o project root esteja no sys.path (para importar `services.*`).
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from services.tool_gate_service import ToolGateService, TOOL_GATE_ENABLED


class TestToolGateService(unittest.TestCase):
    """Testes unitários para ToolGateService."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.service = ToolGateService()
        self.session_id = "test_session_123"
    
    def test_tool_gate_desabilitado_retorna_args_originais(self):
        """Testa que quando ToolGate está desabilitado, retorna args originais."""
        self.service.enabled = False
        
        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='buscar_secao_relatorio_salvo',
            args=args,
            session_id=self.session_id
        )
        
        self.assertEqual(resultado['args_resolvidos'], args)
        self.assertEqual(len(resultado['injections']), 0)
        self.assertIsNone(resultado['erro'])
    
    def test_nao_injeta_se_report_id_explicito(self):
        """Testa que não injeta report_id se já foi fornecido explicitamente."""
        args = {
            'secao': 'processos_chegando',
            'categoria': 'DMD',
            'report_id': 'rel_explicito_123'
        }
        
        resultado = self.service.resolver_contexto_tool(
            nome_tool='buscar_secao_relatorio_salvo',
            args=args,
            session_id=self.session_id
        )
        
        # Args devem permanecer iguais (não injetar)
        self.assertEqual(resultado['args_resolvidos']['report_id'], 'rel_explicito_123')
        self.assertEqual(len(resultado['injections']), 0)
        self.assertIsNone(resultado['erro'])
    
    @patch('services.report_service.obter_active_report_info')
    def test_injeta_active_report_id_quando_faltar(self, mock_obter_active_info):
        """Testa que injeta active_report_id quando faltar report_id."""
        mock_obter_active_info.return_value = {
            'id': 'rel_active_456',
            'meta_json': {'created_at': datetime.now().isoformat()},
            'criado_em': datetime.now().isoformat(),
        }
        
        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='buscar_secao_relatorio_salvo',
            args=args,
            session_id=self.session_id
        )
        
        # Deve ter injetado report_id
        self.assertEqual(resultado['args_resolvidos']['report_id'], 'rel_active_456')
        self.assertEqual(len(resultado['injections']), 1)
        self.assertEqual(resultado['injections'][0]['fonte'], 'active_report_id')
        self.assertIsNone(resultado['erro'])
    
    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    def test_fallback_para_last_visible_se_active_nao_existe(self, mock_last_visible, mock_active):
        """Testa que usa last_visible_report_id se active_report_id não existe."""
        mock_active.return_value = None
        mock_last_visible.return_value = {'id': 'rel_last_789'}
        
        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='filtrar_relatorio',
            args=args,
            session_id=self.session_id
        )
        
        # Deve ter injetado last_visible_report_id
        self.assertEqual(resultado['args_resolvidos']['report_id'], 'rel_last_789')
        self.assertEqual(len(resultado['injections']), 1)
        self.assertEqual(resultado['injections'][0]['fonte'], 'last_visible_report_id')
        self.assertIsNone(resultado['erro'])
    
    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    def test_retorna_erro_se_nao_consegue_resolver(self, mock_last_visible, mock_active):
        """Testa que retorna erro controlado se não consegue resolver report_id."""
        mock_active.return_value = None
        mock_last_visible.return_value = None
        
        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='buscar_secao_relatorio_salvo',
            args=args,
            session_id=self.session_id
        )
        
        # Deve retornar erro
        self.assertIsNotNone(resultado['erro'])
        self.assertIn('Nenhum relatório ativo', resultado['erro'])
        self.assertEqual(len(resultado['injections']), 0)

    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    def test_nao_injeta_report_stale(self, mock_last_visible, mock_active_info):
        """Se active_report_id for velho (stale), deve ignorar e tentar last_visible (se recente)."""
        ts_velho = (datetime.now() - timedelta(minutes=120)).isoformat()
        ts_novo = (datetime.now() - timedelta(minutes=5)).isoformat()

        mock_active_info.return_value = {
            'id': 'rel_active_stale',
            'meta_json': {'created_at': ts_velho},
            'criado_em': ts_velho,
        }
        mock_last_visible.return_value = {'id': 'rel_last_ok', 'meta_json': {'created_at': ts_novo}}

        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='buscar_secao_relatorio_salvo',
            args=args,
            session_id=self.session_id
        )

        self.assertIsNone(resultado['erro'])
        self.assertEqual(resultado['args_resolvidos']['report_id'], 'rel_last_ok')
        self.assertEqual(resultado['injections'][0]['fonte'], 'last_visible_report_id')

    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    @patch('services.report_service.obter_report_history')
    @patch('services.report_service.buscar_relatorio_por_id')
    def test_report_meta_valido_injeta_quando_active_last_visible_nao_existem(
        self,
        mock_buscar_por_id,
        mock_history,
        mock_last_visible,
        mock_active_info
    ):
        """REPORT_META injeta quando active/last_visible não existem (e report existe no banco)."""
        mock_active_info.return_value = None
        mock_last_visible.return_value = None
        ts_novo = datetime.now().isoformat()
        mock_history.return_value = [{'id': 'rel_meta_ok', 'tipo': 'o_que_tem_hoje', 'created_at': ts_novo}]

        class _Rel:
            tipo_relatorio = 'o_que_tem_hoje'

        mock_buscar_por_id.return_value = _Rel()

        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='filtrar_relatorio',
            args=args,
            session_id=self.session_id
        )

        self.assertIsNone(resultado['erro'])
        self.assertEqual(resultado['args_resolvidos']['report_id'], 'rel_meta_ok')
        self.assertEqual(resultado['injections'][0]['fonte'], 'REPORT_META')

    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    @patch('services.report_service.obter_report_history')
    @patch('services.report_service.buscar_relatorio_por_id')
    def test_report_meta_stale_ignorado_e_erro_controlado(
        self,
        mock_buscar_por_id,
        mock_history,
        mock_last_visible,
        mock_active_info
    ):
        """REPORT_META stale deve ser ignorado e terminar em erro controlado se não houver outras fontes."""
        mock_active_info.return_value = None
        mock_last_visible.return_value = None
        ts_velho = (datetime.now() - timedelta(minutes=120)).isoformat()
        mock_history.return_value = [{'id': 'rel_meta_stale', 'tipo': 'o_que_tem_hoje', 'created_at': ts_velho}]

        class _Rel:
            tipo_relatorio = 'o_que_tem_hoje'

        mock_buscar_por_id.return_value = _Rel()

        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='buscar_secao_relatorio_salvo',
            args=args,
            session_id=self.session_id
        )

        self.assertIsNotNone(resultado['erro'])
        self.assertIn('Nenhum relatório ativo', resultado['erro'])

    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    @patch('services.report_service.obter_report_history')
    @patch('services.report_service.buscar_relatorio_por_id')
    def test_report_meta_timestamp_invalido_ignora_sem_quebrar(
        self,
        mock_buscar_por_id,
        mock_history,
        mock_last_visible,
        mock_active_info
    ):
        """created_at inválido em REPORT_META deve ser ignorado sem crash."""
        mock_active_info.return_value = None
        mock_last_visible.return_value = None
        mock_history.return_value = [{'id': 'rel_meta_bad_ts', 'tipo': 'o_que_tem_hoje', 'created_at': 'not-a-date'}]
        mock_buscar_por_id.return_value = None

        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='filtrar_relatorio',
            args=args,
            session_id=self.session_id
        )

        self.assertIsNotNone(resultado['erro'])

    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    @patch('services.report_service.obter_report_history')
    @patch('services.report_service.buscar_relatorio_por_id')
    def test_report_meta_id_nao_existe_no_banco_ignora(
        self,
        mock_buscar_por_id,
        mock_history,
        mock_last_visible,
        mock_active_info
    ):
        """REPORT_META com id inexistente no banco deve ser ignorado."""
        mock_active_info.return_value = None
        mock_last_visible.return_value = None
        ts_novo = datetime.now().isoformat()
        mock_history.return_value = [{'id': 'rel_meta_missing', 'tipo': 'o_que_tem_hoje', 'created_at': ts_novo}]
        mock_buscar_por_id.return_value = None

        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='filtrar_relatorio',
            args=args,
            session_id=self.session_id
        )

        self.assertIsNotNone(resultado['erro'])

    @patch('services.report_service.obter_active_report_info')
    @patch('services.report_service.obter_last_visible_report_id')
    @patch('services.report_service.obter_report_history')
    def test_report_meta_nao_sobrescreve_report_id_explicito(self, mock_history, mock_last_visible, mock_active_info):
        """Mesmo com REPORT_META, se report_id veio explícito, não deve sobrescrever."""
        mock_active_info.return_value = None
        mock_last_visible.return_value = None
        mock_history.return_value = [{'id': 'rel_meta_ok', 'tipo': 'o_que_tem_hoje', 'created_at': datetime.now().isoformat()}]

        args = {'secao': 'processos_chegando', 'categoria': 'DMD', 'report_id': 'rel_explicito_123'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='filtrar_relatorio',
            args=args,
            session_id=self.session_id
        )

        self.assertIsNone(resultado['erro'])
        self.assertEqual(resultado['args_resolvidos']['report_id'], 'rel_explicito_123')
        self.assertEqual(len(resultado['injections']), 0)
    
    def test_retorna_erro_sem_session_id(self):
        """Testa que retorna erro se session_id não for fornecido."""
        args = {'secao': 'processos_chegando', 'categoria': 'DMD'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='buscar_secao_relatorio_salvo',
            args=args,
            session_id=None
        )
        
        # Deve retornar erro
        self.assertIsNotNone(resultado['erro'])
        self.assertIn('Nenhum relatório ativo', resultado['erro'])
    
    def test_nao_resolve_para_tools_nao_relatorio(self):
        """Testa que não tenta resolver report_id para tools que não são de relatório."""
        args = {'processo_referencia': 'DMD.0001/26'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='consultar_status_processo',
            args=args,
            session_id=self.session_id
        )
        
        # Não deve injetar nada (tool não está na allowlist)
        self.assertEqual(len(resultado['injections']), 0)
        self.assertIsNone(resultado['erro'])


class TestToolGateIntegration(unittest.TestCase):
    """Testes de integração para ToolGateService."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.service = ToolGateService()
        self.session_id = "test_session_integration"
    
    @patch('services.report_service.obter_active_report_info')
    def test_integracao_enviar_relatorio_email_sem_report_id(self, mock_active):
        """Testa integração: enviar_relatorio_email sem report_id injeta e funciona."""
        mock_active.return_value = {'id': 'rel_integration_999', 'meta_json': {'created_at': datetime.now().isoformat()}}
        
        args = {'destinatario': 'test@exemplo.com'}
        resultado = self.service.resolver_contexto_tool(
            nome_tool='enviar_relatorio_email',
            args=args,
            session_id=self.session_id
        )
        
        # Deve ter injetado report_id
        self.assertEqual(resultado['args_resolvidos']['report_id'], 'rel_integration_999')
        self.assertEqual(resultado['args_resolvidos']['destinatario'], 'test@exemplo.com')
        self.assertEqual(len(resultado['injections']), 1)
        self.assertIsNone(resultado['erro'])


if __name__ == '__main__':
    unittest.main()
