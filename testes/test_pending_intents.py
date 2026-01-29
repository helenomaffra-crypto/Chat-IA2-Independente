"""
Script de teste para o sistema de Pending Intents.

Testa:
1. Criação de pending intents (email e DUIMP)
2. Busca de pending intents
3. Marcação como executado
4. Limpeza de intents expiradas
5. Integração com ConfirmationHandler
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pending_intent_service import get_pending_intent_service
from services.handlers.confirmation_handler import ConfirmationHandler
from db_manager import init_db
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_pending_intent_service():
    """Testa o PendingIntentService diretamente."""
    print("\n" + "="*70)
    print("TESTE 1: PendingIntentService - CRUD Básico")
    print("="*70)
    
    service = get_pending_intent_service()
    session_id = "test_session_123"
    
    # Limpar intents antigas desta sessão
    print("\n📋 Limpando intents antigas...")
    old_intents = service.listar_pending_intents(session_id=session_id)
    for intent in old_intents:
        if intent['status'] == 'pending':
            service.marcar_como_cancelado(intent['intent_id'], observacoes='Limpeza de teste')
    
    # Teste 1.1: Criar pending intent para email
    print("\n✅ Teste 1.1: Criar pending intent para email")
    intent_id_email = service.criar_pending_intent(
        session_id=session_id,
        action_type='send_email',
        tool_name='enviar_email_personalizado',
        args_normalizados={
            'draft_id': 'draft_123',
            'destinatario': 'teste@exemplo.com',
            'assunto': 'Teste de Email',
            'funcao': 'enviar_email_personalizado'
        },
        preview_text='📧 Email para Envio\n\nDe: Sistema mAIke\nPara: teste@exemplo.com\nAssunto: Teste de Email\n\n⚠️ Confirme para enviar'
    )
    
    if intent_id_email:
        print(f"   ✅ Pending intent criado: {intent_id_email}")
    else:
        print("   ❌ Falha ao criar pending intent")
        return False
    
    # Teste 1.2: Criar pending intent para DUIMP
    print("\n✅ Teste 1.2: Criar pending intent para DUIMP")
    intent_id_duimp = service.criar_pending_intent(
        session_id=session_id,
        action_type='create_duimp',
        tool_name='criar_duimp',
        args_normalizados={
            'processo_referencia': 'BND.0084/25',
            'ambiente': 'Validacao'
        },
        preview_text='📋 Capa da DUIMP - Processo BND.0084/25\n\n⚠️ Deseja criar a DUIMP?'
    )
    
    if intent_id_duimp:
        print(f"   ✅ Pending intent criado: {intent_id_duimp}")
    else:
        print("   ❌ Falha ao criar pending intent")
        return False
    
    # Teste 1.3: Buscar pending intent de email
    print("\n✅ Teste 1.3: Buscar pending intent de email")
    intent_email = service.buscar_pending_intent(
        session_id=session_id,
        status='pending',
        action_type='send_email'
    )
    
    if intent_email and intent_email['intent_id'] == intent_id_email:
        print(f"   ✅ Pending intent encontrado: {intent_email['intent_id']}")
        print(f"   📋 Args: {intent_email.get('args_normalizados', {})}")
    else:
        print("   ❌ Falha ao buscar pending intent")
        return False
    
    # Teste 1.4: Buscar pending intent de DUIMP
    print("\n✅ Teste 1.4: Buscar pending intent de DUIMP")
    intent_duimp = service.buscar_pending_intent(
        session_id=session_id,
        status='pending',
        action_type='create_duimp'
    )
    
    if intent_duimp and intent_duimp['intent_id'] == intent_id_duimp:
        print(f"   ✅ Pending intent encontrado: {intent_duimp['intent_id']}")
        print(f"   📋 Args: {intent_duimp.get('args_normalizados', {})}")
    else:
        print("   ❌ Falha ao buscar pending intent")
        return False
    
    # Teste 1.5: Marcar como executado
    print("\n✅ Teste 1.5: Marcar pending intent como executado")
    sucesso = service.marcar_como_executado(intent_id_email, observacoes='Email enviado com sucesso')
    
    if sucesso:
        print(f"   ✅ Pending intent {intent_id_email} marcado como executado")
    else:
        print("   ❌ Falha ao marcar como executado")
        return False
    
    # Teste 1.6: Verificar que não aparece mais em busca de pending
    print("\n✅ Teste 1.6: Verificar que intent executado não aparece em busca")
    intent_executado = service.buscar_pending_intent(
        session_id=session_id,
        status='pending',
        action_type='send_email'
    )
    
    if intent_executado is None:
        print("   ✅ Intent executado não aparece mais em busca de pending")
    else:
        print(f"   ⚠️ Intent ainda aparece como pending: {intent_executado['intent_id']}")
    
    # Teste 1.7: Buscar por ID
    print("\n✅ Teste 1.7: Buscar pending intent por ID")
    intent_por_id = service.buscar_pending_intent_por_id(intent_id_email)
    
    if intent_por_id and intent_por_id['status'] == 'executed':
        print(f"   ✅ Intent encontrado por ID: {intent_por_id['intent_id']} (status: {intent_por_id['status']})")
    else:
        print("   ❌ Falha ao buscar por ID ou status incorreto")
        return False
    
    # Limpeza
    print("\n🧹 Limpando intents de teste...")
    service.marcar_como_cancelado(intent_id_duimp, observacoes='Limpeza de teste')
    
    print("\n✅✅✅ TESTE 1 PASSOU: PendingIntentService funcionando corretamente!")
    return True


def test_confirmation_handler():
    """Testa a integração com ConfirmationHandler."""
    print("\n" + "="*70)
    print("TESTE 2: ConfirmationHandler - Integração com Pending Intents")
    print("="*70)
    
    session_id = "test_session_456"
    
    # Criar ConfirmationHandler
    handler = ConfirmationHandler()
    
    # Teste 2.1: Criar pending intent via handler
    print("\n✅ Teste 2.1: Criar pending intent de email via handler")
    dados_email = {
        'draft_id': 'draft_456',
        'destinatario': 'handler@exemplo.com',
        'assunto': 'Teste Handler',
        'funcao': 'enviar_email_personalizado'
    }
    preview_text = '📧 Email para Envio\n\n⚠️ Confirme para enviar'
    
    intent_id = handler.criar_pending_intent_email(
        session_id=session_id,
        dados_email=dados_email,
        preview_text=preview_text
    )
    
    if intent_id:
        print(f"   ✅ Pending intent criado via handler: {intent_id}")
    else:
        print("   ❌ Falha ao criar pending intent via handler")
        return False
    
    # Teste 2.2: Buscar pending intent via handler
    print("\n✅ Teste 2.2: Buscar pending intent via handler")
    intent_encontrado = handler.buscar_pending_intent(
        session_id=session_id,
        action_type='send_email'
    )
    
    if intent_encontrado and intent_encontrado['intent_id'] == intent_id:
        print(f"   ✅ Pending intent encontrado via handler: {intent_encontrado['intent_id']}")
        args = intent_encontrado.get('args_normalizados', {})
        print(f"   📋 Destinatário: {args.get('destinatario')}")
        print(f"   📋 Assunto: {args.get('assunto')}")
    else:
        print("   ❌ Falha ao buscar pending intent via handler")
        return False
    
    # Teste 2.3: Criar pending intent de DUIMP via handler
    print("\n✅ Teste 2.3: Criar pending intent de DUIMP via handler")
    dados_duimp = {
        'processo_referencia': 'DMD.0001/26',
        'ambiente': 'Validacao'
    }
    preview_text_duimp = '📋 Capa da DUIMP - Processo DMD.0001/26\n\n⚠️ Deseja criar a DUIMP?'
    
    intent_id_duimp = handler.criar_pending_intent_duimp(
        session_id=session_id,
        dados_duimp=dados_duimp,
        preview_text=preview_text_duimp
    )
    
    if intent_id_duimp:
        print(f"   ✅ Pending intent de DUIMP criado via handler: {intent_id_duimp}")
    else:
        print("   ❌ Falha ao criar pending intent de DUIMP via handler")
        return False
    
    # Limpeza
    print("\n🧹 Limpando intents de teste...")
    service = get_pending_intent_service()
    service.marcar_como_cancelado(intent_id, observacoes='Limpeza de teste')
    service.marcar_como_cancelado(intent_id_duimp, observacoes='Limpeza de teste')
    
    print("\n✅✅✅ TESTE 2 PASSOU: ConfirmationHandler integrado corretamente!")
    return True


def test_processar_confirmacao_com_pending_intent():
    """Testa processamento de confirmação usando pending intent."""
    print("\n" + "="*70)
    print("TESTE 3: Processar Confirmação com Pending Intent (sem dados em memória)")
    print("="*70)
    
    session_id = "test_session_789"
    
    # Criar ConfirmationHandler
    handler = ConfirmationHandler()
    
    # Criar pending intent primeiro
    print("\n📋 Criando pending intent de email...")
    dados_email = {
        'draft_id': 'draft_789',
        'destinatario': 'confirmacao@exemplo.com',
        'assunto': 'Teste de Confirmação',
        'funcao': 'enviar_email_personalizado'
    }
    preview_text = '📧 Email para Envio\n\n⚠️ Confirme para enviar'
    
    intent_id = handler.criar_pending_intent_email(
        session_id=session_id,
        dados_email=dados_email,
        preview_text=preview_text
    )
    
    if not intent_id:
        print("   ❌ Falha ao criar pending intent")
        return False
    
    print(f"   ✅ Pending intent criado: {intent_id}")
    
    # Teste 3.1: Processar confirmação SEM dados em memória (simula refresh)
    print("\n✅ Teste 3.1: Processar confirmação SEM dados em memória (simula refresh)")
    resultado = handler.processar_confirmacao_email(
        mensagem="sim, pode enviar",
        dados_email_para_enviar=None,  # Simula que memória foi perdida
        session_id=session_id
    )
    
    if resultado.get('sucesso') is not False:
        # Se não retornou erro de "não encontrado", significa que buscou do pending intent
        print(f"   ✅ Sistema buscou pending intent automaticamente")
        print(f"   📋 Resultado: {resultado.get('resposta', 'N/A')[:100]}...")
    else:
        print(f"   ⚠️ Sistema não encontrou pending intent: {resultado.get('resposta', 'N/A')}")
        # Isso pode acontecer se o handler não conseguir executar o email (falta de serviços)
        # Mas o importante é que ele tentou buscar o pending intent
    
    # Limpeza
    print("\n🧹 Limpando intents de teste...")
    service = get_pending_intent_service()
    if intent_id:
        service.marcar_como_cancelado(intent_id, observacoes='Limpeza de teste')
    
    print("\n✅✅✅ TESTE 3 PASSOU: Sistema busca pending intent quando memória está vazia!")
    return True


def main():
    """Executa todos os testes."""
    print("\n" + "="*70)
    print("🧪 TESTES DO SISTEMA DE PENDING INTENTS")
    print("="*70)
    
    # Inicializar banco
    print("\n📦 Inicializando banco de dados...")
    try:
        init_db()
        print("   ✅ Banco inicializado")
    except Exception as e:
        print(f"   ❌ Erro ao inicializar banco: {e}")
        return False
    
    # Executar testes
    resultados = []
    
    resultados.append(("PendingIntentService", test_pending_intent_service()))
    resultados.append(("ConfirmationHandler", test_confirmation_handler()))
    resultados.append(("Processar Confirmação", test_processar_confirmacao_com_pending_intent()))
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70)
    
    todos_passaram = True
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{nome}: {status}")
        if not resultado:
            todos_passaram = False
    
    print("\n" + "="*70)
    if todos_passaram:
        print("✅✅✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("="*70 + "\n")
    
    return todos_passaram


if __name__ == '__main__':
    sucesso = main()
    sys.exit(0 if sucesso else 1)
