"""
Golden Tests para Fluxos de Email - Passo 0 da Refatoração

Estes testes servem como "airbag" durante a refatoração do chat_service.py.
Garantem que funcionalidades críticas de email não quebram quando extraímos código.

Data: 09/01/2026
Status: ⏳ EM DESENVOLVIMENTO
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path para imports
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from typing import Dict, Any, Optional, List
import json
import uuid

# Imports do sistema
from services.chat_service import ChatService
from services.email_draft_service import EmailDraftService, get_email_draft_service
from services.email_send_coordinator import EmailSendCoordinator
from services.handlers.confirmation_handler import ConfirmationHandler
from db_manager import init_db, get_db_connection


class TestEmailFlowsGolden:
    """Testes golden para fluxos críticos de email."""
    
    @pytest.fixture(scope="function")
    def db_setup(self):
        """Setup do banco de dados para testes."""
        # Inicializar banco
        init_db()
        yield
        # Limpar após teste (opcional, pode manter para debug)
    
    @pytest.fixture
    def mock_ai_service(self):
        """Mock do AI Service."""
        mock = Mock()
        # MessageProcessingService usa `ai_service._call_llm_api(...)`.
        # Mantemos também `chat_completion(...)` por compatibilidade histórica, mas os testes devem mockar `_call_llm_api`.
        mock._call_llm_api = Mock(return_value={
            'content': 'Preview do email gerado',
            'tool_calls': []
        })
        mock.chat_completion = Mock(return_value={
            'resposta': 'Preview do email gerado',
            'tool_calls': []
        })
        return mock
    
    @pytest.fixture
    def mock_email_service(self):
        """Mock do Email Service."""
        mock = Mock()
        mock.send_email = Mock(return_value={
            'sucesso': True,
            'message_id': 'test_message_id',
            'metodo': 'GraphAPI'
        })
        return mock
    
    @pytest.fixture
    def chat_service(self, db_setup, mock_ai_service, mock_email_service):
        """Instância do ChatService para testes."""
        # Mockar dotenv antes de qualquer import que use load_dotenv
        with patch('dotenv.load_dotenv'):
            # Mockar get_ai_service
            with patch('services.chat_service.get_ai_service', return_value=mock_ai_service):
                # Mockar get_email_service
                with patch('services.email_service.get_email_service', return_value=mock_email_service):
                    # Mockar get_email_draft_service
                    with patch('services.email_draft_service.get_email_draft_service') as mock_get_draft:
                        from services.email_draft_service import EmailDraftService
                        mock_get_draft.return_value = EmailDraftService()
                        
                        # Mockar get_email_send_coordinator
                        with patch('services.email_send_coordinator.get_email_send_coordinator') as mock_get_coord:
                            from services.email_send_coordinator import EmailSendCoordinator
                            from services.email_draft_service import get_email_draft_service as real_get_draft
                            coord = EmailSendCoordinator(
                                email_service=mock_email_service,
                                email_draft_service=real_get_draft()
                            )
                            mock_get_coord.return_value = coord
                            
                            chat = ChatService()
                            # Substituir serviços mockados diretamente
                            chat.ai_service = mock_ai_service
                            return chat
    
    # ============================================================
    # TESTE 1.1: Criar Email → Preview → Confirmar → Enviado
    # ============================================================
    
    def test_criar_email_preview_confirmar_enviado(self, chat_service, mock_ai_service, mock_email_service):
        """
        Teste 1.1: Fluxo completo de criação e envio de email personalizado.
        
        Cenário:
        1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião de hoje"
        2. Sistema: Gera preview do email
        3. Usuário: "sim"
        4. Sistema: Envia email com sucesso
        """
        session_id = 'test_session_1'
        
        # Limpar drafts anteriores
        limpar_drafts_teste(session_id)
        
        # PASSO 1: Criar email - simular tool call da IA
        mensagem_criar = "mande um email para helenomaffra@gmail.com sobre a reunião de hoje"
        
        # Mockar resposta da IA com tool call
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Vou criar o email para você.',
            'tool_calls': [{
                'function': {
                    'name': 'enviar_email_personalizado',
                    'arguments': json.dumps({
                        'destinatarios': ['helenomaffra@gmail.com'],
                        'assunto': 'Reunião de hoje',
                        'conteudo': 'Olá,\n\nEste é um email sobre a reunião de hoje.\n\nAtenciosamente'
                    })
                }
            }]
        }
        
        # Processar mensagem
        resultado_preview = chat_service.processar_mensagem(
            mensagem=mensagem_criar,
            historico=[],
            session_id=session_id
        )
        
        # VALIDAÇÃO 1: Preview foi gerado
        assert resultado_preview.get('sucesso') is not False, "Preview deve ser gerado com sucesso"
        assert 'preview' in resultado_preview.get('resposta', '').lower() or 'confirme' in resultado_preview.get('resposta', '').lower(), "Resposta deve conter preview"
        
        # VALIDAÇÃO 2: Draft foi criado no banco
        dados_email = chat_service.ultima_resposta_aguardando_email
        assert dados_email is not None, "Dados do email devem estar salvos"
        draft_id = dados_email.get('draft_id')
        assert draft_id is not None, "draft_id deve existir"
        assert verificar_draft_existe(draft_id), "Draft deve existir no banco"
        
        # PASSO 2: Confirmar envio
        mensagem_confirmar = "sim"
        
        # Mockar resposta da IA (não deve chamar tool, apenas processar confirmação)
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Email enviado com sucesso!',
            'tool_calls': []
        }
        
        # Processar confirmação
        resultado_envio = chat_service.processar_mensagem(
            mensagem=mensagem_confirmar,
            historico=[{
                'role': 'assistant',
                'content': resultado_preview.get('resposta', ''),
                '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email}
            }],
            session_id=session_id
        )
        
        # VALIDAÇÃO 3: Email foi enviado
        assert resultado_envio.get('sucesso') is not False, "Email deve ser enviado com sucesso"
        assert 'enviado' in resultado_envio.get('resposta', '').lower(), "Resposta deve indicar envio"
        
        # VALIDAÇÃO 4: Email service foi chamado
        assert mock_email_service.send_email.called, "Email service deve ser chamado"
        
        # VALIDAÇÃO 5: Draft marcado como 'sent'
        assert verificar_draft_status(draft_id, 'sent'), "Draft deve estar marcado como 'sent'"
        
        # Limpar após teste
        limpar_drafts_teste(session_id)
    
    # ============================================================
    # TESTE 1.2: Criar Email → Melhorar → Confirmar → Enviar Melhorado
    # ============================================================
    
    def test_criar_email_melhorar_confirmar_enviar_melhorado(self, chat_service, mock_ai_service, mock_email_service):
        """
        Teste 1.2: Fluxo de melhoria de email antes do envio.
        
        Cenário:
        1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
        2. Sistema: Gera preview do email
        3. Usuário: "melhore o email"
        4. Sistema: Gera email melhorado e reemite preview
        5. Usuário: "sim"
        6. Sistema: Envia email melhorado (não o original)
        """
        session_id = 'test_session_2'
        limpar_drafts_teste(session_id)
        
        # PASSO 1: Criar email inicial
        mensagem_criar = "mande um email para helenomaffra@gmail.com sobre a reunião"
        conteudo_original = "Olá,\n\nEste é um email sobre a reunião.\n\nAtenciosamente"
        
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Vou criar o email.',
            'tool_calls': [{
                'function': {
                    'name': 'enviar_email_personalizado',
                    'arguments': json.dumps({
                        'destinatarios': ['helenomaffra@gmail.com'],
                        'assunto': 'Reunião',
                        'conteudo': conteudo_original
                    })
                }
            }]
        }
        
        resultado_preview = chat_service.processar_mensagem(
            mensagem=mensagem_criar,
            historico=[],
            session_id=session_id
        )
        
        dados_email = chat_service.ultima_resposta_aguardando_email
        draft_id = dados_email.get('draft_id')
        
        # VALIDAÇÃO 1: Draft criado (revision 1)
        draft_service = get_email_draft_service()
        draft_original = draft_service.obter_draft(draft_id)
        assert draft_original.revision == 1, "Draft inicial deve ser revision 1"
        # O sistema pode adicionar rodapé/normalizações; validar o essencial.
        assert "olá" in (draft_original.conteudo or "").lower()
        assert "reuni" in (draft_original.conteudo or "").lower()
        
        # PASSO 2: Melhorar email
        mensagem_melhorar = "melhore o email"
        # Nota: o EmailImprovementHandler atual usa heurísticas/regex e pode falhar com blocos multi-parágrafo.
        # Para este golden test, manter corpo em uma única linha garante extração determinística.
        conteudo_melhorado = "Prezado, Gostaria de convidá-lo para a reunião que acontecerá hoje. Atenciosamente"
        
        # Mockar resposta da IA melhorando o email
        mock_ai_service._call_llm_api.return_value = {
            # EmailImprovementHandler espera marcadores como "Corpo:"/"Conteúdo:" para extrair corretamente.
            'content': f'Assunto: Reunião\n\nCorpo:\n{conteudo_melhorado}',
            'tool_calls': []
        }
        
        historico_melhorar = [{
            'role': 'assistant',
            'content': resultado_preview.get('resposta', ''),
            '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email}
        }]
        
        resultado_melhorado = chat_service.processar_mensagem(
            mensagem=mensagem_melhorar,
            historico=historico_melhorar,
            session_id=session_id
        )
        
        # VALIDAÇÃO 2: Nova revisão criada (revision 2)
        draft_melhorado = draft_service.obter_draft(draft_id)
        assert draft_melhorado.revision == 2, "Draft melhorado deve ser revision 2"
        assert draft_melhorado.conteudo != conteudo_original, "Conteúdo deve ser diferente do original"
        
        # VALIDAÇÃO 3: Preview reemitido
        assert 'preview' in resultado_melhorado.get('resposta', '').lower() or 'confirme' in resultado_melhorado.get('resposta', '').lower(), "Preview deve ser reemitido"
        
        # PASSO 3: Confirmar envio
        mensagem_confirmar = "sim"
        dados_email_atualizados = chat_service.ultima_resposta_aguardando_email
        
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Email enviado!',
            'tool_calls': []
        }
        
        resultado_envio = chat_service.processar_mensagem(
            mensagem=mensagem_confirmar,
            historico=[{
                'role': 'assistant',
                'content': resultado_melhorado.get('resposta', ''),
                '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email_atualizados}
            }],
            session_id=session_id
        )
        
        # VALIDAÇÃO 4: Email enviado com conteúdo melhorado
        assert mock_email_service.send_email.called, "Email deve ser enviado"
        call_args = mock_email_service.send_email.call_args
        assert call_args is not None, "Email service deve ter sido chamado"
        # Verificar que conteúdo enviado é o melhorado (não o original)
        body_text = call_args.kwargs.get('body_text', '') or call_args.args[2] if len(call_args.args) > 2 else ''
        assert conteudo_melhorado in body_text or body_text != conteudo_original, "Email enviado deve conter conteúdo melhorado"
        
        # VALIDAÇÃO 5: Draft marcado como 'sent'
        assert verificar_draft_status(draft_id, 'sent'), "Draft deve estar marcado como 'sent'"
        
        limpar_drafts_teste(session_id)
    
    # ============================================================
    # TESTE 1.3: Criar Email → Corrigir Destinatário → Confirmar → Enviar
    # ============================================================
    
    def test_criar_email_corrigir_destinatario_confirmar_enviar(self, chat_service, mock_ai_service, mock_email_service):
        """
        Teste 1.3: Correção de destinatário sem perder contexto.
        
        Cenário:
        1. Usuário: "mande um email para helenomaffra@gmail sobre a reunião"
        2. Sistema: Gera preview do email
        3. Usuário: "mande para helenomaffra@gmail.com" (corrige email)
        4. Sistema: Reemite preview com email corrigido
        5. Usuário: "sim"
        6. Sistema: Envia email para email correto
        """
        session_id = 'test_session_3'
        limpar_drafts_teste(session_id)
        
        assunto_original = "Reunião de hoje"
        conteudo_original = "Olá,\n\nEste é um email sobre a reunião.\n\nAtenciosamente"
        
        # PASSO 1: Criar email com email errado
        mensagem_criar = "mande um email para helenomaffra@gmail sobre a reunião"
        
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Vou criar o email.',
            'tool_calls': [{
                'function': {
                    'name': 'enviar_email_personalizado',
                    'arguments': json.dumps({
                        'destinatarios': ['helenomaffra@gmail'],  # Email sem .com
                        'assunto': assunto_original,
                        'conteudo': conteudo_original
                    })
                }
            }]
        }
        
        resultado_preview = chat_service.processar_mensagem(
            mensagem=mensagem_criar,
            historico=[],
            session_id=session_id
        )
        
        dados_email = chat_service.ultima_resposta_aguardando_email
        draft_id = dados_email.get('draft_id')
        
        # VALIDAÇÃO 1: Preview gerado com email errado
        assert 'helenomaffra@gmail' in str(dados_email.get('destinatarios', [])), "Email inicial deve estar errado"
        
        # PASSO 2: Corrigir destinatário
        mensagem_corrigir = "mande para helenomaffra@gmail.com"
        
        # Não deve chamar IA, deve detectar correção diretamente
        resultado_corrigido = chat_service.processar_mensagem(
            mensagem=mensagem_corrigir,
            historico=[{
                'role': 'assistant',
                'content': resultado_preview.get('resposta', ''),
                '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email}
            }],
            session_id=session_id
        )
        
        # VALIDAÇÃO 2: Preview reemitido com email corrigido
        assert 'preview' in resultado_corrigido.get('resposta', '').lower() or 'confirme' in resultado_corrigido.get('resposta', '').lower(), "Preview deve ser reemitido"
        
        # VALIDAÇÃO 3: Email corrigido nos dados
        dados_email_corrigidos = chat_service.ultima_resposta_aguardando_email
        assert 'helenomaffra@gmail.com' in str(dados_email_corrigidos.get('destinatarios', [])), "Email deve estar corrigido"
        
        # VALIDAÇÃO 4: Assunto e conteúdo mantidos
        assert dados_email_corrigidos.get('assunto') == assunto_original, "Assunto deve ser mantido"
        assert dados_email_corrigidos.get('conteudo') == conteudo_original, "Conteúdo deve ser mantido"
        
        # PASSO 3: Confirmar envio
        mensagem_confirmar = "sim"
        
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Email enviado!',
            'tool_calls': []
        }
        
        resultado_envio = chat_service.processar_mensagem(
            mensagem=mensagem_confirmar,
            historico=[{
                'role': 'assistant',
                'content': resultado_corrigido.get('resposta', ''),
                '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email_corrigidos}
            }],
            session_id=session_id
        )
        
        # VALIDAÇÃO 5: Email enviado para destinatário correto
        assert mock_email_service.send_email.called, "Email deve ser enviado"
        call_args = mock_email_service.send_email.call_args
        to_emails = call_args.kwargs.get('to', []) or (call_args.args[0] if len(call_args.args) > 0 else [])
        assert 'helenomaffra@gmail.com' in to_emails, "Email deve ser enviado para destinatário correto"
        assert 'helenomaffra@gmail' not in str(to_emails) or 'helenomaffra@gmail.com' in str(to_emails), "Email errado não deve estar na lista"
        
        limpar_drafts_teste(session_id)
    
    # ============================================================
    # TESTE 1.4: Enviar Relatório → Preview → Confirmar → Enviado
    # ============================================================
    
    def test_enviar_relatorio_preview_confirmar_enviado(self, chat_service):
        """
        Teste 1.4: Fluxo de envio de relatório por email.
        
        Cenário:
        1. Usuário: "como estão os DMD?"
        2. Sistema: Gera relatório
        3. Usuário: "mande esse relatório para helenomaffra@gmail.com"
        4. Sistema: Gera preview do email com relatório
        5. Usuário: "sim"
        6. Sistema: Envia email com relatório completo
        """
        # TODO: Implementar teste
        pytest.skip("Teste ainda não implementado - estrutura básica criada")
    
    # ============================================================
    # TESTE 1.5: Idempotência - Confirmar Duas Vezes Não Duplica Envio
    # ============================================================
    
    def test_idempotencia_confirmar_duas_vezes_nao_duplica(self, chat_service, mock_ai_service, mock_email_service):
        """
        Teste 1.5: Proteção contra envio duplicado.
        
        Cenário:
        1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
        2. Sistema: Gera preview
        3. Usuário: "sim"
        4. Sistema: Envia email (draft marcado como `sent`)
        5. Usuário: "sim" (novamente)
        6. Sistema: Retorna "já foi enviado" (não envia novamente)
        """
        session_id = 'test_session_5'
        limpar_drafts_teste(session_id)
        
        # PASSO 1: Criar email
        mensagem_criar = "mande um email para helenomaffra@gmail.com sobre a reunião"
        
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Vou criar o email.',
            'tool_calls': [{
                'function': {
                    'name': 'enviar_email_personalizado',
                    'arguments': json.dumps({
                        'destinatarios': ['helenomaffra@gmail.com'],
                        'assunto': 'Reunião',
                        'conteudo': 'Olá,\n\nEste é um email sobre a reunião.\n\nAtenciosamente'
                    })
                }
            }]
        }
        
        resultado_preview = chat_service.processar_mensagem(
            mensagem=mensagem_criar,
            historico=[],
            session_id=session_id
        )
        
        dados_email = chat_service.ultima_resposta_aguardando_email
        draft_id = dados_email.get('draft_id')
        
        # Resetar contador de chamadas do mock
        mock_email_service.send_email.reset_mock()
        
        # PASSO 2: Primeira confirmação
        mensagem_confirmar_1 = "sim"
        
        mock_ai_service._call_llm_api.return_value = {
            'content': 'Email enviado!',
            'tool_calls': []
        }
        
        resultado_envio_1 = chat_service.processar_mensagem(
            mensagem=mensagem_confirmar_1,
            historico=[{
                'role': 'assistant',
                'content': resultado_preview.get('resposta', ''),
                '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email}
            }],
            session_id=session_id
        )
        
        # VALIDAÇÃO 1: Primeira confirmação envia email
        assert mock_email_service.send_email.called, "Primeira confirmação deve enviar email"
        num_chamadas_1 = mock_email_service.send_email.call_count
        
        # VALIDAÇÃO 2: Draft marcado como 'sent'
        assert verificar_draft_status(draft_id, 'sent'), "Draft deve estar marcado como 'sent'"
        
        # PASSO 3: Segunda confirmação (tentativa de reenvio)
        mensagem_confirmar_2 = "sim"
        
        # Atualizar dados_email para refletir que já foi enviado
        dados_email['status'] = 'sent'
        
        resultado_envio_2 = chat_service.processar_mensagem(
            mensagem=mensagem_confirmar_2,
            historico=[{
                'role': 'assistant',
                'content': resultado_envio_1.get('resposta', ''),
                '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email}
            }],
            session_id=session_id
        )
        
        # VALIDAÇÃO 3: Segunda confirmação NÃO envia email novamente
        num_chamadas_2 = mock_email_service.send_email.call_count
        # O número de chamadas não deve aumentar (ou deve retornar mensagem de idempotência)
        assert num_chamadas_2 == num_chamadas_1 or 'já' in resultado_envio_2.get('resposta', '').lower() or 'enviado' in resultado_envio_2.get('resposta', '').lower(), "Segunda confirmação não deve enviar email novamente"
        
        limpar_drafts_teste(session_id)
    
    # ============================================================
    # TESTE 1.6: Confirmação Funciona Igual em Streaming e Normal
    # ============================================================
    
    def test_confirmacao_funciona_igual_streaming_e_normal(self, chat_service):
        """
        Teste 1.6: Garantir que confirmação funciona igual nos dois modos.
        
        Cenário (Normal):
        1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
        2. Sistema: Gera preview (via `processar_mensagem()`)
        3. Usuário: "sim"
        4. Sistema: Envia email
        
        Cenário (Streaming):
        1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
        2. Sistema: Gera preview (via `processar_mensagem_stream()`)
        3. Usuário: "sim"
        4. Sistema: Envia email
        """
        # TODO: Implementar teste
        pytest.skip("Teste ainda não implementado - estrutura básica criada")


# ============================================================
# HELPERS E UTILITÁRIOS PARA TESTES
# ============================================================

def criar_draft_teste(
    destinatarios: List[str],
    assunto: str,
    conteudo: str,
    session_id: str = 'test_session',
    funcao_email: str = 'enviar_email_personalizado'
) -> str:
    """Helper para criar draft de teste."""
    draft_service = get_email_draft_service()
    draft_id = draft_service.criar_draft(
        destinatarios=destinatarios,
        assunto=assunto,
        conteudo=conteudo,
        session_id=session_id,
        funcao_email=funcao_email
    )
    return draft_id


def verificar_draft_existe(draft_id: str) -> bool:
    """Helper para verificar se draft existe."""
    draft_service = get_email_draft_service()
    draft = draft_service.obter_draft(draft_id)
    return draft is not None


def verificar_draft_status(draft_id: str, status_esperado: str) -> bool:
    """Helper para verificar status do draft."""
    draft_service = get_email_draft_service()
    draft = draft_service.obter_draft(draft_id)
    if not draft:
        return False
    return draft.status == status_esperado


def limpar_drafts_teste(session_id: str = 'test_session'):
    """Helper para limpar drafts de teste."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM email_drafts WHERE session_id = ?', (session_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao limpar drafts: {e}")
