"""
ConfirmationHandler - Centraliza lógica de confirmação de ações pendentes.

Este handler unifica a lógica de confirmação entre processar_mensagem() e processar_mensagem_stream(),
eliminando duplicação e garantindo consistência.

Regra de ouro: Confirmação sempre resolve para um objeto (ex.: draft no DB), não para "texto do chat".

State Machine: Usa PendingAction para rastrear ações pendentes sem depender do texto do chat.
"""

import re
import json
import logging
from typing import Dict, Optional, Any, Callable, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class PendingAction:
    """
    Representa uma ação pendente de confirmação.
    
    Usado para criar uma state machine simples que não depende do texto do chat.
    """
    kind: str  # "send_email" | "create_duimp" | "send_report"
    id: str  # draft_id, duimp_id, report_id, etc.
    expires_at: Optional[str] = None  # Timestamp de expiração (opcional)
    metadata: Optional[Dict[str, Any]] = None  # Dados adicionais


class ConfirmationHandler:
    """
    Handler centralizado para processar confirmações de ações pendentes.
    
    Suporta:
    - Confirmação de email (enviar_email_personalizado, enviar_relatorio_email, enviar_email)
    - Confirmação de DUIMP (criar_duimp)
    """
    
    def __init__(
        self,
        email_draft_service: Any = None,
        email_service: Any = None,
        email_send_coordinator: Any = None,
        duimp_agent: Any = None,
        context_service: Any = None,
        obter_email_para_enviar: Optional[Callable] = None,
        executar_funcao_tool: Optional[Callable] = None,
        extrair_processo_referencia: Optional[Callable] = None,
    ):
        """
        Inicializa o handler com dependências necessárias.
        
        Args:
            email_draft_service: Serviço de gerenciamento de drafts de email
            email_service: Serviço de envio de emails
            email_send_coordinator: Coordenador centralizado de envio de emails (PONTO ÚNICO)
            duimp_agent: Agent para criação de DUIMP
            context_service: Serviço de gerenciamento de contexto
            obter_email_para_enviar: Função para obter email do banco/memória
            executar_funcao_tool: Função para executar tools
            extrair_processo_referencia: Função para extrair referência de processo
        """
        self.email_draft_service = email_draft_service
        self.email_service = email_service
        self.email_send_coordinator = email_send_coordinator
        self.duimp_agent = duimp_agent
        self.context_service = context_service
        self._obter_email_para_enviar = obter_email_para_enviar
        self._executar_funcao_tool = executar_funcao_tool
        self._extrair_processo_referencia = extrair_processo_referencia
        
        # Lazy loading do coordenador se não fornecido
        if not self.email_send_coordinator:
            try:
                from services.email_send_coordinator import get_email_send_coordinator
                self.email_send_coordinator = get_email_send_coordinator()
            except Exception as e:
                logger.warning(f'⚠️ Erro ao carregar EmailSendCoordinator: {e}')
        
        # ✅ NOVO (14/01/2026): Lazy loading do PendingIntentService
        self._pending_intent_service = None
    
    def _get_pending_intent_service(self):
        """Lazy loading do PendingIntentService."""
        if self._pending_intent_service is None:
            try:
                from services.pending_intent_service import get_pending_intent_service
                self._pending_intent_service = get_pending_intent_service()
            except Exception as e:
                logger.warning(f'⚠️ Erro ao carregar PendingIntentService: {e}')
        return self._pending_intent_service
    
    def criar_pending_intent_email(
        self,
        session_id: str,
        dados_email: Dict[str, Any],
        preview_text: str
    ) -> Optional[str]:
        """
        ✅ NOVO (14/01/2026): Cria pending intent para email.
        
        Args:
            session_id: ID da sessão
            dados_email: Dados do email (será normalizado)
            preview_text: Texto do preview mostrado ao usuário
        
        Returns:
            intent_id se criado com sucesso, None caso contrário
        """
        service = self._get_pending_intent_service()
        if not service:
            return None
        
        # Normalizar argumentos
        funcao_email = dados_email.get('funcao', 'enviar_email_personalizado')
        
        # ✅✅✅ CRÍTICO (14/01/2026): Para detecção de duplicatas, usar apenas campos essenciais no hash
        # NÃO incluir resumo_texto completo no hash (pode variar com espaços/linhas)
        args_normalizados = {
            'draft_id': dados_email.get('draft_id'),
            'destinatario': dados_email.get('destinatario'),
            'assunto': dados_email.get('assunto') or dados_email.get('argumentos', {}).get('assunto'),
            'funcao': funcao_email,
        }
        
        # ✅ CRÍTICO (14/01/2026): Para enviar_relatorio_email, incluir apenas campos essenciais para hash
        if funcao_email == 'enviar_relatorio_email':
            # ✅ CORREÇÃO: Usar report_id se disponível (mais confiável que resumo_texto)
            argumentos = dados_email.get('argumentos', {})
            if argumentos.get('report_id'):
                args_normalizados['report_id'] = argumentos.get('report_id')
            args_normalizados['tipo_relatorio'] = argumentos.get('tipo_relatorio', 'o_que_tem_hoje')
            args_normalizados['categoria'] = argumentos.get('categoria')
            # ✅ NÃO incluir resumo_texto no hash (pode variar)
            # ✅ NÃO incluir argumentos completos no hash (pode variar)
        
        # Remover None values
        args_normalizados = {k: v for k, v in args_normalizados.items() if v is not None}
        
        # ✅✅✅ CRÍTICO (14/01/2026): Para armazenamento completo, criar args_completos separado
        # (usado na execução, não no hash)
        args_completos = args_normalizados.copy()
        if funcao_email == 'enviar_relatorio_email':
            # Incluir resumo_texto e argumentos completos apenas para execução
            if dados_email.get('resumo_texto'):
                args_completos['resumo_texto'] = dados_email.get('resumo_texto')
            if dados_email.get('argumentos'):
                args_completos['argumentos'] = dados_email.get('argumentos')
        else:
            # ✅ IMPORTANTE: Se não houver draft_id, precisamos guardar conteúdo para executar depois.
            # Caso contrário, a confirmação não terá como reconstruir o email.
            if not args_completos.get('draft_id'):
                if dados_email.get('destinatarios') is not None:
                    args_completos['destinatarios'] = dados_email.get('destinatarios')
                if dados_email.get('cc') is not None:
                    args_completos['cc'] = dados_email.get('cc')
                if dados_email.get('bcc') is not None:
                    args_completos['bcc'] = dados_email.get('bcc')
                if dados_email.get('conteudo') is not None:
                    args_completos['conteudo'] = dados_email.get('conteudo')
                if dados_email.get('corpo') is not None:
                    args_completos['corpo'] = dados_email.get('corpo')
        
        # ✅✅✅ CRÍTICO (14/01/2026): Usar args_normalizados para hash (campos essenciais)
        # Mas salvar args_completos no banco para execução
        # ✅ NOVO: TTL mais curto para emails (30 minutos)
        intent_id = service.criar_pending_intent(
            session_id=session_id,
            action_type='send_email',
            tool_name=args_normalizados.get('funcao', 'enviar_email_personalizado'),
            args_normalizados=args_completos,  # Salvar completo para execução
            preview_text=preview_text,
            args_hash=args_normalizados,  # Usar apenas campos essenciais para hash (detecção de duplicatas)
            ttl_hours=0.5  # ✅ NOVO: 30 minutos para emails (mais curto que padrão de 2h)
        )
        
        if intent_id:
            logger.info(f'✅ Pending intent criado para email: {intent_id}')
            
            # ✅✅✅ CRÍTICO (14/01/2026): Marcar como active_pending_email_id e invalidar anteriores
            from services.context_service import salvar_contexto_sessao
            from datetime import datetime
            salvar_contexto_sessao(
                session_id=session_id,
                tipo_contexto='active_pending_email_id',
                chave='current',
                valor=intent_id,
                dados_adicionais={
                    'created_at': datetime.now().isoformat(),
                    'action_type': 'send_email'
                }
            )
            
            # ✅ NOVO: Marcar pending intents antigos como superseded
            service.marcar_pendings_antigos_como_superseded(
                session_id=session_id,
                action_type='send_email',
                except_id=intent_id
            )
        
        return intent_id
    
    def criar_pending_intent_duimp(
        self,
        session_id: str,
        dados_duimp: Dict[str, Any],
        preview_text: str
    ) -> Optional[str]:
        """
        ✅ NOVO (14/01/2026): Cria pending intent para DUIMP.
        
        Args:
            session_id: ID da sessão
            dados_duimp: Dados da DUIMP (será normalizado)
            preview_text: Texto do preview mostrado ao usuário
        
        Returns:
            intent_id se criado com sucesso, None caso contrário
        """
        service = self._get_pending_intent_service()
        if not service:
            return None
        
        # Normalizar argumentos
        args_normalizados = {
            'processo_referencia': dados_duimp.get('processo_referencia'),
            'ambiente': dados_duimp.get('ambiente', 'Validacao')
        }
        
        # Remover None values
        args_normalizados = {k: v for k, v in args_normalizados.items() if v is not None}
        
        intent_id = service.criar_pending_intent(
            session_id=session_id,
            action_type='create_duimp',
            tool_name='criar_duimp',
            args_normalizados=args_normalizados,
            preview_text=preview_text
        )
        
        if intent_id:
            logger.info(f'✅ Pending intent criado para DUIMP: {intent_id}')
        
        return intent_id
    
    def buscar_pending_intent(
        self,
        session_id: str,
        action_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        ✅ NOVO (14/01/2026): Busca último pending intent de uma sessão.
        
        Args:
            session_id: ID da sessão
            action_type: Tipo da ação (opcional, para filtrar)
        
        Returns:
            Dict com dados do intent se encontrado, None caso contrário
        """
        service = self._get_pending_intent_service()
        if not service:
            return None
        
        return service.buscar_pending_intent(
            session_id=session_id,
            status='pending',
            action_type=action_type
        )
    
    def buscar_todos_pending_intents(
        self,
        session_id: str,
        status: str = 'pending'
    ) -> List[Dict[str, Any]]:
        """
        ✅ NOVO (14/01/2026): Busca TODOS os pending intents de uma sessão.
        
        Usado para detectar ambiguidade (múltiplos intents pendentes).
        
        Args:
            session_id: ID da sessão
            status: Status do intent (padrão: 'pending')
        
        Returns:
            Lista de dicts com dados dos intents
        """
        service = self._get_pending_intent_service()
        if not service:
            return []
        
        return service.listar_pending_intents(
            session_id=session_id,
            status=status,
            limite=10
        )
    
    def detectar_cancelamento(self, mensagem: str) -> bool:
        """
        ✅ NOVO (14/01/2026): Detecta se a mensagem é um comando de cancelamento.
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            True se é comando de cancelamento, False caso contrário
        """
        mensagem_lower = (mensagem or "").lower().strip()
        mensagem_norm = re.sub(r'\s+', ' ', mensagem_lower)
        mensagem_norm = re.sub(r'[.!?,;:]+$', '', mensagem_norm).strip()
        
        padroes_cancelamento = [
            'cancelar', 'cancela', 'cancel', 'desistir', 'desiste',
            'não quero', 'nao quero', 'não fazer', 'nao fazer',
            'não enviar', 'nao enviar', 'não criar', 'nao criar'
        ]
        
        return any(padrao in mensagem_lower for padrao in padroes_cancelamento)
    
    def detectar_confirmacao_email(self, mensagem: str, dados_email_para_enviar: Optional[Dict]) -> bool:
        """
        Detecta se a mensagem é uma confirmação de envio de email.
        
        Args:
            mensagem: Mensagem do usuário
            dados_email_para_enviar: Dados do email em preview (se houver)
        
        Returns:
            True se é confirmação de email, False caso contrário
        """
        if not dados_email_para_enviar:
            return False
        
        mensagem_lower = (mensagem or "").lower().strip()
        mensagem_norm = re.sub(r'\s+', ' ', mensagem_lower)
        mensagem_norm = re.sub(r'[.!?,;:]+$', '', mensagem_norm).strip()
        
        # Padrões de confirmação simples
        confirmacoes_email = [
            'sim', 'enviar', 'pode enviar', 'envia', 'manda', 'mandar', 
            'confirma', 'confirmar', 'ok', 'pode'
        ]
        
        # Padrões específicos para "envie esse email", "mande esse email", etc.
        padroes_confirmacao = [
            'envie esse email', 'mande esse email', 'envia esse email', 'manda esse email',
            'envie esse', 'mande esse', 'envia esse', 'manda esse',
            'envie o email', 'mande o email', 'envia o email', 'manda o email',
            'envie o', 'mande o', 'envia o', 'manda o'
        ]
        
        # ✅ CORREÇÃO CRÍTICA (14/01/2026):
        # Evitar falso positivo: "simpático" contém "sim".
        if mensagem_norm in confirmacoes_email:
            return True
        if mensagem_norm in padroes_confirmacao:
            return True
        if mensagem_norm in ['sim', 'enviar', 'ok']:
            return True
        return False
    
    def detectar_confirmacao_duimp(self, mensagem: str, estado_duimp: Optional[Dict]) -> bool:
        """
        Detecta se a mensagem é uma confirmação de criação de DUIMP.
        
        Args:
            mensagem: Mensagem do usuário
            estado_duimp: Estado pendente de confirmação de DUIMP (se houver)
        
        Returns:
            True se é confirmação de DUIMP, False caso contrário
        """
        if not estado_duimp:
            return False
        
        mensagem_lower = (mensagem or "").lower().strip()
        mensagem_norm = re.sub(r'\s+', ' ', mensagem_lower)
        mensagem_norm = re.sub(r'[.!?,;:]+$', '', mensagem_norm).strip()
        
        # Verificar se é um comando novo (não confirmação)
        eh_comando_novo = bool(
            re.search(r'registr[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower) or
            re.search(r'cri[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower) or
            re.search(r'ger[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower) or
            re.search(r'fazer\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
        )
        
        if eh_comando_novo:
            return False  # Comando novo, não é confirmação
        
        # Padrões de confirmação
        confirmacoes_duimp = [
            'sim', 'pode prosseguir', 'prosseguir', 'confirmar', 'confirma', 
            'pode criar', 'pode registrar', 'confirmo', 'ok', 'criar'
        ]
        
        # ✅ CORREÇÃO CRÍTICA (14/01/2026):
        # Evitar falso positivo: "simpático" contém "sim".
        if mensagem_norm in confirmacoes_duimp:
            return True
        if mensagem_norm in ['sim', 'pode', 'ok', 'confirmo', 'criar', 'yes']:
            return True
        return False
    
    def processar_confirmacao_email(
        self,
        mensagem: str,
        dados_email_para_enviar: Optional[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa confirmação de envio de email.
        
        ✅ NOVO (14/01/2026): Busca pending intent se dados_email_para_enviar não for fornecido.
        
        Regra: Se tem draft_id → banco é fonte da verdade (última revisão)
               Se não tem draft_id → usa memória
               Se não tem dados em memória → busca pending intent
        
        Args:
            mensagem: Mensagem do usuário
            dados_email_para_enviar: Dados do email em preview (opcional, pode ser None)
            session_id: ID da sessão (para buscar pending intent)
        
        Returns:
            Dict com resultado do envio:
            - sucesso: bool
            - resposta: str
            - erro: str (se houver)
            - email_enviado: bool (se sucesso)
        """
        # ✅✅✅ CRÍTICO (14/01/2026): Handler determinístico - SEMPRE usar active_pending_email_id primeiro
        # NÃO chamar LLM para confirmação - apenas retornar "Confirmado, enviando..." ou "Qual número?"
        
        mensagem_stripped = mensagem.strip().lower()
        mensagem_original = mensagem.strip()
        
        # ✅ NOVO: Palavras de confirmação determinísticas
        CONFIRM_WORDS = {"sim", "enviar", "confirmar", "ok", "manda", "pode enviar", "envie", "confirma"}
        # ✅ CORREÇÃO CRÍTICA: confirmação deve ser determinística (SEM substring)
        # Evita falso-positivo: "simpático" contém "sim".
        eh_confirmacao = mensagem_stripped in CONFIRM_WORDS
        
        # ✅ NOVO: Detectar "último" ou "mais recente"
        eh_ultimo = bool(re.search(r'\b(último|ultima|mais recente)\b', mensagem_stripped))
        
        # ✅ NOVO: Detectar número (escolha da lista)
        eh_numero = mensagem_stripped.isdigit()
        
        if not session_id:
            return {
                'sucesso': False,
                'erro': 'SEM_SESSION_ID',
                'resposta': '❌ Erro: session_id não fornecido.'
            }
        
        service = self._get_pending_intent_service()
        if not service:
            return {
                'sucesso': False,
                'erro': 'SERVICE_NAO_DISPONIVEL',
                'resposta': '❌ Erro: serviço de pending intents não disponível.'
            }

        # ✅ CRÍTICO: sempre inicializar para evitar UnboundLocalError
        pending_intent = None
        intent_id = None
        
        # ✅✅✅ PRIORIDADE 1: Buscar active_pending_email_id do contexto
        from services.context_service import buscar_contexto_sessao
        contextos_active = buscar_contexto_sessao(session_id, tipo_contexto='active_pending_email_id', chave='current')
        active_pending_id = contextos_active[0].get('valor') if contextos_active else None
        
        # ✅ NOVO: Buscar todos os pending intents (apenas não-superseded)
        todos_intents = self.buscar_todos_pending_intents(session_id, status='pending')
        intents_email = [
            i for i in todos_intents 
            if i.get('action_type') == 'send_email' 
            and i.get('status') != 'superseded'
        ]
        
        # ✅✅✅ PRIORIDADE 2: Se mensagem é número, processar escolha
        if eh_numero and len(intents_email) > 1:
                try:
                    escolha_numero = int(mensagem_stripped)
                    if 1 <= escolha_numero <= len(intents_email):
                        # Usuário escolheu uma opção numerada
                        intent_escolhido = intents_email[escolha_numero - 1]  # -1 porque lista começa em 0
                        intent_id = intent_escolhido.get('intent_id')
                        logger.info(f'✅✅✅ [CONFIRMACAO] Escolha numérica detectada: {escolha_numero} → intent_id={intent_id}')
                        
                        # Buscar pending intent específico escolhido
                        service = self._get_pending_intent_service()
                        if service:
                            pending_intent = service.buscar_pending_intent_por_id(intent_id)
                            if pending_intent:
                                # Verificar status
                                status_intent = pending_intent.get('status')
                                if status_intent != 'pending':
                                    if status_intent == 'executed':
                                        return {
                                            'sucesso': False,
                                            'erro': 'JA_EXECUTADO',
                                            'resposta': '❌ Este email já foi enviado anteriormente.'
                                        }
                                    elif status_intent == 'expired':
                                        return {
                                            'sucesso': False,
                                            'erro': 'EXPIRADO',
                                            'resposta': '❌ Este email expirou. Gere o preview novamente.'
                                        }
                                    elif status_intent == 'cancelled':
                                        return {
                                            'sucesso': False,
                                            'erro': 'CANCELADO',
                                            'resposta': '❌ Este email foi cancelado. Gere um novo email se necessário.'
                                        }
                                
                                # Marcar como executing (lock atômico)
                                lock_obtido = service.marcar_como_executando(intent_id)
                                if not lock_obtido:
                                    # ✅ CORRIGIDO (14/01/2026): Log detalhado para debug
                                    logger.warning(
                                        f'⚠️ Lock NÃO obtido para intent {intent_id} '
                                        f'(session: {session_id}, action: {pending_intent.get("action_type")}, '
                                        f'status atual: {pending_intent.get("status")})'
                                    )
                                    return {
                                        'sucesso': False,
                                        'erro': 'EM_EXECUCAO',
                                        'resposta': '❌ Este email está sendo processado. Aguarde alguns instantes.'
                                    }
                                
                                # Usar args_normalizados do intent escolhido
                                args = pending_intent.get('args_normalizados', {})
                                dados_email_para_enviar = {
                                    'draft_id': args.get('draft_id'),
                                    'destinatario': args.get('destinatario'),
                                    'assunto': args.get('assunto'),
                                    'funcao': args.get('funcao', 'enviar_email_personalizado')
                                }
                                logger.info(f'✅ Pending intent escolhido: {intent_id} (usando SQLite como fonte da verdade)')
                                
                                # Processar confirmação normalmente
                                funcao_email = dados_email_para_enviar.get('funcao', 'enviar_email_personalizado')
                                logger.info(f'✅✅✅ [CONFIRMACAO] Confirmação de email detectada (escolha {escolha_numero}) - enviando via {funcao_email}')
                                
                                try:
                                    if funcao_email == 'enviar_relatorio_email':
                                        resultado = self._processar_confirmacao_relatorio_email(dados_email_para_enviar, mensagem)
                                    elif funcao_email == 'enviar_email':
                                        resultado = self._processar_confirmacao_email_simples(dados_email_para_enviar, mensagem)
                                    else:
                                        resultado = self._processar_confirmacao_email_personalizado(dados_email_para_enviar, mensagem, session_id)
                                    
                                    # Marcar como executado se sucesso
                                    if isinstance(resultado, dict) and resultado.get('sucesso'):
                                        if service:
                                            service.marcar_como_executado(intent_id, observacoes='Email enviado com sucesso')
                                            logger.info(f'✅ Pending intent {intent_id} marcado como executado')
                                    
                                    return resultado
                                except Exception as e:
                                    logger.error(f'❌ Erro ao processar confirmação de email (escolha {escolha_numero}): {e}', exc_info=True)
                                    return {
                                        'sucesso': False,
                                        'resposta': f'❌ Erro ao enviar email: {str(e)}',
                                        'erro': 'ERRO_ENVIO_EMAIL'
                                    }
                            else:
                                return {
                                    'sucesso': False,
                                    'erro': 'INTENT_NAO_ENCONTRADO',
                                    'resposta': f'❌ Email número {escolha_numero} não encontrado. Pode ter expirado ou sido cancelado.'
                                }
                        else:
                            return {
                                'sucesso': False,
                                'erro': 'SERVICO_NAO_DISPONIVEL',
                                'resposta': '❌ Serviço de pending intents não disponível.'
                            }
                    else:
                        return {
                            'sucesso': False,
                            'erro': 'ESCOLHA_INVALIDA',
                            'resposta': f'❌ Número inválido. Escolha um número entre 1 e {len(intents_email)}.'
                        }
                except ValueError:
                    # Não é número válido, continuar processamento normal
                    pass
            
        # ✅✅✅ PRIORIDADE 1: Se há active_pending_email_id, usar ele
        if active_pending_id:
            pending_intent = service.buscar_pending_intent_por_id(active_pending_id)
            if pending_intent and pending_intent.get('status') == 'pending':
                intent_id = active_pending_id
                logger.info(f'✅✅✅ [CONFIRMACAO] Usando active_pending_email_id: {intent_id}')
            else:
                # Active não existe ou não está pending, limpar do contexto
                active_pending_id = None
                pending_intent = None
        
        # ✅✅✅ PRIORIDADE 2: Se não há active, usar o mais recente (se houver apenas 1)
        if not pending_intent:
            if len(intents_email) == 1:
                pending_intent = intents_email[0]
                intent_id = pending_intent.get('intent_id')
                logger.info(f'✅✅✅ [CONFIRMACAO] Usando único pending intent disponível: {intent_id}')
            elif len(intents_email) > 1:
                # ✅ Múltiplos pendentes - mostrar lista (só se não for confirmação direta)
                if not eh_confirmacao and not eh_ultimo:
                    lista_opcoes = '\n'.join([
                        f"({idx+1}) Email para {self._extrair_destinatario_intent(intent)} "
                        f"- Assunto: {self._extrair_assunto_intent(intent)}"
                        for idx, intent in enumerate(intents_email)
                    ])
                    return {
                        'sucesso': False,
                        'erro': 'MULTIPLOS_PENDENTES',
                        'resposta': f'📋 Há {len(intents_email)} emails pendentes. Qual deseja confirmar?\n\n{lista_opcoes}\n\n💡 Digite o número (1, 2, 3...) ou "cancelar" para cancelar.',
                        'requer_escolha': True,
                        'opcoes': intents_email
                    }
                else:
                    # Se disse "sim" ou "último" com múltiplos, usar o mais recente
                    pending_intent = intents_email[0]  # Mais recente (já ordenado por created_at DESC)
                    intent_id = pending_intent.get('intent_id')
                    logger.info(f'✅✅✅ [CONFIRMACAO] Múltiplos pendentes, usando mais recente: {intent_id}')
        
        # ✅✅✅ PRIORIDADE 3: Se ainda não tem pending, buscar do DB (fallback)
        if not pending_intent:
            pending_intent = service.buscar_pending_intent(session_id, action_type='send_email')
            if pending_intent:
                intent_id = pending_intent.get('intent_id')
                logger.info(f'✅✅✅ [CONFIRMACAO] Usando pending intent do DB (fallback): {intent_id}')
        
        # ✅ Se não encontrou nenhum pending, tentar "reidratar" a partir do preview em memória/histórico.
        # Isso evita o atrito do usuário ver "Nenhum email pendente..." logo após um preview.
        if not pending_intent and dados_email_para_enviar and session_id:
            try:
                funcao_email_mem = dados_email_para_enviar.get('funcao', 'enviar_email_personalizado')
                assunto_mem = dados_email_para_enviar.get('assunto') or dados_email_para_enviar.get('argumentos', {}).get('assunto')
                destinatarios_mem = dados_email_para_enviar.get('destinatarios') or dados_email_para_enviar.get('destinatarios', [])
                # Compat: alguns fluxos guardam 'destinatario' singular
                destinatario_hash = (
                    dados_email_para_enviar.get('destinatario')
                    or (destinatarios_mem[0] if isinstance(destinatarios_mem, list) and len(destinatarios_mem) == 1 else None)
                    or (', '.join(destinatarios_mem) if isinstance(destinatarios_mem, list) and destinatarios_mem else None)
                )

                preview_min = f"Email pendente: {destinatario_hash or 'destinatário'} - Assunto: {assunto_mem or 'sem assunto'}"

                dados_email_pendente = {
                    'funcao': funcao_email_mem,
                    'destinatario': destinatario_hash,
                    'assunto': assunto_mem,
                    'draft_id': dados_email_para_enviar.get('draft_id'),
                    # ✅ Campos extras (necessários quando não há draft_id)
                    'destinatarios': destinatarios_mem,
                    'cc': dados_email_para_enviar.get('cc'),
                    'bcc': dados_email_para_enviar.get('bcc'),
                    'conteudo': dados_email_para_enviar.get('conteudo'),
                    'corpo': dados_email_para_enviar.get('corpo'),
                }

                intent_id_reidratado = self.criar_pending_intent_email(
                    session_id=session_id,
                    dados_email=dados_email_pendente,
                    preview_text=preview_min,
                )
                if intent_id_reidratado:
                    pending_intent = service.buscar_pending_intent_por_id(intent_id_reidratado)
                    intent_id = intent_id_reidratado
                    logger.info(f'✅✅✅ [CONFIRMACAO] Pending intent reidratado a partir do preview: {intent_id}')
            except Exception as e:
                logger.warning(f'⚠️ [CONFIRMACAO] Falha ao reidratar pending intent a partir do preview: {e}')

        # ✅ Se não encontrou nenhum pending, retornar erro
        if not pending_intent:
            return {
                'sucesso': False,
                'erro': 'NENHUM_PENDING',
                'resposta': '❌ Nenhum email pendente encontrado. Gere um preview de email primeiro.'
            }
        
        # ✅ Verificar status (idempotência)
        status_intent = pending_intent.get('status')
        if status_intent != 'pending':
            if status_intent == 'executed':
                return {
                    'sucesso': False,
                    'erro': 'JA_EXECUTADO',
                    'resposta': '❌ Este email já foi enviado anteriormente.'
                }
            elif status_intent == 'executing':
                return {
                    'sucesso': False,
                    'erro': 'EM_EXECUCAO',
                    'resposta': '❌ Este email está sendo processado. Aguarde alguns instantes.'
                }
            elif status_intent == 'expired':
                return {
                    'sucesso': False,
                    'erro': 'EXPIRADO',
                    'resposta': '❌ Este email expirou. Gere o preview novamente.'
                }
            elif status_intent == 'cancelled':
                return {
                    'sucesso': False,
                    'erro': 'CANCELADO',
                    'resposta': '❌ Este email foi cancelado. Gere um novo email se necessário.'
                }
            elif status_intent == 'superseded':
                return {
                    'sucesso': False,
                    'erro': 'SUPERSEDED',
                    'resposta': '❌ Este email foi substituído por um mais recente. Use o preview mais recente.'
                }
        
        # ✅ Marcar como executing (lock atômico)
        lock_obtido = service.marcar_como_executando(intent_id)
        if not lock_obtido:
            # ✅ CORRIGIDO (14/01/2026): Log detalhado para debug
            logger.warning(
                f'⚠️ Lock NÃO obtido para intent {intent_id} '
                f'(session: {session_id}, action: {pending_intent.get("action_type")}, '
                f'status atual: {pending_intent.get("status")})'
            )
            return {
                'sucesso': False,
                'erro': 'EM_EXECUCAO',
                'resposta': '❌ Este email está sendo processado. Aguarde alguns instantes.'
            }
        
        # ✅ Extrair dados do pending intent
        args = pending_intent.get('args_normalizados', {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}
        
        dados_email_para_enviar = {
            'draft_id': args.get('draft_id'),
            'destinatario': args.get('destinatario'),
            'assunto': args.get('assunto'),
            'funcao': args.get('funcao', 'enviar_email_personalizado'),
            'resumo_texto': args.get('resumo_texto'),  # Para enviar_relatorio_email
            'argumentos': args.get('argumentos', {}),  # Para enviar_relatorio_email
            # ✅ Campos extras (para casos sem draft_id)
            'destinatarios': args.get('destinatarios'),
            'cc': args.get('cc'),
            'bcc': args.get('bcc'),
            'conteudo': args.get('conteudo'),
            'corpo': args.get('corpo'),
        }
        
        logger.info(f'✅✅✅ [CONFIRMACAO] Processando confirmação - intent_id={intent_id}, funcao={dados_email_para_enviar.get("funcao")}')
        
        # ✅ Processar confirmação (determinístico - sem LLM)
        try:
            funcao_email = dados_email_para_enviar.get('funcao', 'enviar_email_personalizado')
            if funcao_email == 'enviar_relatorio_email':
                resultado = self._processar_confirmacao_relatorio_email(dados_email_para_enviar, mensagem_original)
            elif funcao_email == 'enviar_email':
                resultado = self._processar_confirmacao_email_simples(dados_email_para_enviar, mensagem_original)
            else:
                resultado = self._processar_confirmacao_email_personalizado(dados_email_para_enviar, mensagem_original, session_id)
            
            # ✅ Marcar como executado se sucesso
            if isinstance(resultado, dict) and resultado.get('sucesso'):
                service.marcar_como_executado(intent_id, observacoes='Email enviado com sucesso')
                logger.info(f'✅ Pending intent {intent_id} marcado como executado')
            
            return resultado
        except Exception as e:
            logger.error(f'❌ Erro ao processar confirmação de email: {e}', exc_info=True)
            return {
                'sucesso': False,
                'resposta': f'❌ Erro ao enviar email: {str(e)}',
                'erro': 'ERRO_ENVIO_EMAIL'
            }
    
    def _extrair_destinatario_intent(self, intent: Dict[str, Any]) -> str:
        """Extrai destinatário do intent para exibição."""
        args = intent.get('args_normalizados', {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}
        return args.get('destinatario', 'N/A')
    
    def _extrair_assunto_intent(self, intent: Dict[str, Any]) -> str:
        """Extrai assunto do intent para exibição."""
        args = intent.get('args_normalizados', {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except:
                args = {}
        return args.get('assunto', 'N/A')
    
    def _processar_confirmacao_relatorio_email(self, dados_email_para_enviar: Dict, mensagem: str) -> Dict[str, Any]:
        """
        Processa confirmação de envio de relatório por email.
        
        ✅ NOVO (09/01/2026): Usa EmailSendCoordinator quando possível.
        """
        resumo_texto_salvo = dados_email_para_enviar.get('resumo_texto')
        
        if resumo_texto_salvo:
            # ✅ NOVO: Usar EmailSendCoordinator se disponível
            if self.email_send_coordinator:
                destinatario = dados_email_para_enviar.get('destinatario')
                categoria = dados_email_para_enviar.get('argumentos', {}).get('categoria')
                assunto = dados_email_para_enviar.get('argumentos', {}).get('assunto', 'Resumo')
                
                logger.info(f'✅✅✅ [CONFIRMACAO] Usando EmailSendCoordinator para enviar relatório')
                resultado = self.email_send_coordinator.send_report_email(
                    destinatario=destinatario,
                    resumo_texto=resumo_texto_salvo,
                    assunto=assunto,
                    categoria=categoria
                )
                
                if resultado.get('sucesso'):
                    tipo_relatorio = dados_email_para_enviar.get('argumentos', {}).get('tipo_relatorio', 'resumo')
                    return {
                        'sucesso': True,
                        'resposta': f"✅ **{tipo_relatorio.capitalize()} enviado por email com sucesso para {destinatario}**\n\nAssunto: {assunto}",
                        'destinatario': destinatario,
                        'metodo': resultado.get('metodo', 'SMTP'),
                        'email_enviado': True
                    }
                else:
                    return resultado
            
            # Fallback: usar método antigo
            if not self.email_service:
                from services.email_service import get_email_service
                self.email_service = get_email_service()
            
            destinatario = dados_email_para_enviar.get('destinatario')
            categoria = dados_email_para_enviar.get('argumentos', {}).get('categoria')
            
            resultado_email = self.email_service.enviar_resumo_por_email(
                destinatario=destinatario,
                resumo_texto=resumo_texto_salvo,
                categoria=categoria
            )
            
            if resultado_email.get('sucesso'):
                tipo_relatorio = dados_email_para_enviar.get('argumentos', {}).get('tipo_relatorio', 'resumo')
                return {
                    'sucesso': True,
                    'resposta': f"✅ **{tipo_relatorio.capitalize()} enviado por email com sucesso para {destinatario}**\n\nAssunto: {dados_email_para_enviar.get('argumentos', {}).get('assunto', 'Resumo')}",
                    'destinatario': destinatario,
                    'metodo': resultado_email.get('metodo', 'SMTP'),
                    'email_enviado': True
                }
            else:
                erro_msg = resultado_email.get('erro') or resultado_email.get('mensagem', 'Erro desconhecido')
                return {
                    'sucesso': False,
                    'erro': resultado_email.get('erro', 'ERRO_ENVIO_EMAIL'),
                    'resposta': f"❌ Erro ao enviar email: {erro_msg}"
                }
        else:
            # Não tem resumo salvo - gerar novo (comportamento antigo)
            if not self._executar_funcao_tool:
                return {
                    'sucesso': False,
                    'erro': 'FUNCAO_EXECUTAR_TOOL_NAO_DISPONIVEL',
                    'resposta': '❌ Função executar_tool não disponível'
                }
            
            argumentos_relatorio = dados_email_para_enviar.get('argumentos', {})
            argumentos_relatorio['confirmar_envio'] = True
            resultado_email = self._executar_funcao_tool('enviar_relatorio_email', argumentos_relatorio, mensagem_original=mensagem)
            
            return self._formatar_resultado_email(resultado_email, funcao_email='enviar_relatorio_email')
    
    def _processar_confirmacao_email_simples(self, dados_email_para_enviar: Dict, mensagem: str) -> Dict[str, Any]:
        """Processa confirmação de envio de email simples."""
        if not self._executar_funcao_tool:
            return {
                'sucesso': False,
                'erro': 'FUNCAO_EXECUTAR_TOOL_NAO_DISPONIVEL',
                'resposta': '❌ Função executar_tool não disponível'
            }
        
        resultado_email = self._executar_funcao_tool('enviar_email', {
            'destinatario': dados_email_para_enviar.get('destinatario'),
            'assunto': dados_email_para_enviar.get('assunto'),
            'corpo': dados_email_para_enviar.get('corpo'),
            'confirmar_envio': True
        }, mensagem_original=mensagem)
        
        return self._formatar_resultado_email(resultado_email, funcao_email='enviar_email')
    
    def _processar_confirmacao_email_personalizado(
        self,
        dados_email_para_enviar: Dict,
        mensagem: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa confirmação de envio de email personalizado.
        
        ✅ NOVO (09/01/2026): Usa EmailSendCoordinator como ponto único de convergência.
        """
        # ✅ CRÍTICO: Sempre usar banco como fonte da verdade quando tem draft_id
        if not self._obter_email_para_enviar:
            return {
                'sucesso': False,
                'erro': 'FUNCAO_OBTER_EMAIL_NAO_DISPONIVEL',
                'resposta': '❌ Função obter_email_para_enviar não disponível'
            }
        
        # ✅ CRÍTICO: Log detalhado para debug
        draft_id_original = dados_email_para_enviar.get('draft_id') if dados_email_para_enviar else None
        logger.info(f'✅✅✅ [CONFIRMACAO] dados_email_para_enviar recebido - draft_id: {draft_id_original}, keys: {list(dados_email_para_enviar.keys()) if dados_email_para_enviar else "None"}')
        
        dados_email_final = self._obter_email_para_enviar(dados_email_para_enviar)
        
        if not dados_email_final:
            return {
                'sucesso': False,
                'erro': 'DADOS_EMAIL_NAO_ENCONTRADOS',
                'resposta': '❌ Não foi possível encontrar os dados do email para envio.'
            }
        
        # ✅ NOVO: Se tem draft_id, usar EmailSendCoordinator (ponto único de convergência)
        draft_id_final = dados_email_final.get('draft_id')
        logger.info(f'✅✅✅ [CONFIRMACAO] dados_email_final após _obter_email_para_enviar - draft_id: {draft_id_final}, keys: {list(dados_email_final.keys())}')
        
        if draft_id_final and self.email_send_coordinator:
            logger.info(f'✅✅✅ [CONFIRMACAO] Usando EmailSendCoordinator para enviar draft {draft_id_final}')
            resultado = self.email_send_coordinator.send_from_draft(draft_id_final, force=False)
            return self._formatar_resultado_email(resultado, funcao_email='enviar_email_personalizado')
        
        # Fallback: usar método antigo se não tem draft_id ou coordenador não disponível
        if not self._executar_funcao_tool:
            return {
                'sucesso': False,
                'erro': 'FUNCAO_EXECUTAR_TOOL_NAO_DISPONIVEL',
                'resposta': '❌ Função executar_tool não disponível'
            }
        
        logger.warning(f'⚠️⚠️⚠️ [CONFIRMACAO] Fallback: enviando email sem draft_id (método antigo). draft_id_original: {draft_id_original}, draft_id_final: {draft_id_final}, tem_coordinator: {bool(self.email_send_coordinator)}')
        resultado_email = self._executar_funcao_tool('enviar_email_personalizado', {
            'destinatarios': dados_email_final.get('destinatarios', []),
            'assunto': dados_email_final.get('assunto'),
            'conteudo': dados_email_final.get('conteudo'),
            'cc': dados_email_final.get('cc', []),
            'bcc': dados_email_final.get('bcc', []),
            'confirmar_envio': True
        }, mensagem_original=mensagem)
        
        return self._formatar_resultado_email(resultado_email, funcao_email='enviar_email_personalizado')
    
    def _formatar_resultado_email(
        self, 
        resultado_email: Optional[Dict], 
        funcao_email: str,
        intent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formata resultado do envio de email.
        
        ✅ NOVO (14/01/2026): Marca pending intent como executado se sucesso.
        """
        if resultado_email and resultado_email.get('sucesso'):
            # ✅ NOVO: Marcar pending intent como executado
            if intent_id:
                service = self._get_pending_intent_service()
                if service:
                    service.marcar_como_executado(intent_id, observacoes='Email enviado com sucesso')
                    logger.info(f'✅ Pending intent {intent_id} marcado como executado')
            
            return {
                'sucesso': True,
                'resposta': resultado_email.get('resposta', '✅ Email enviado com sucesso!'),
                'tool_calling': {'name': funcao_email, 'arguments': {'confirmar_envio': True}},
                'email_enviado': True
            }
        else:
            return {
                'sucesso': False,
                'resposta': resultado_email.get('resposta', '❌ Erro ao enviar email') if resultado_email else '❌ Erro ao enviar email',
                'erro': resultado_email.get('erro') if resultado_email else 'ERRO_ENVIO_EMAIL'
            }
    
    def processar_confirmacao_duimp(
        self,
        mensagem: str,
        estado_duimp: Optional[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa confirmação de criação de DUIMP.
        
        ✅ NOVO (14/01/2026): Busca pending intent se estado_duimp não for fornecido.
        
        Args:
            mensagem: Mensagem do usuário
            estado_duimp: Estado pendente de confirmação de DUIMP (opcional)
            session_id: ID da sessão (para buscar pending intent)
        
        Returns:
            Dict com resultado da criação:
            - sucesso: bool
            - resposta: str
            - erro: str (se houver)
            - numero_duimp: str (se sucesso)
            - versao_duimp: str (se sucesso)
        """
        # ✅ NOVO (14/01/2026): SQLite como fonte da verdade - SEMPRE buscar do DB primeiro
        # Ignorar estado em memória, usar apenas SQLite
        intent_id = None
        pending_intent = None
        
        if session_id:
            # ✅ NOVO: Verificar se há múltiplos pending intents (ambiguidade)
            todos_intents = self.buscar_todos_pending_intents(session_id, status='pending')
            intents_duimp = [i for i in todos_intents if i.get('action_type') == 'create_duimp']
            
            if len(intents_duimp) > 1:
                # ✅ NOVO (14/01/2026): Múltiplas DUIMPs pendentes - pedir escolha numerada
                lista_opcoes = '\n'.join([
                    f"({idx+1}) DUIMP do processo {intent.get('args_normalizados', {}).get('processo_referencia', 'N/A')} "
                    f"- Ambiente: {intent.get('args_normalizados', {}).get('ambiente', 'N/A')}"
                    for idx, intent in enumerate(intents_duimp)
                ])
                return {
                    'sucesso': False,
                    'erro': 'MULTIPLOS_PENDENTES',
                    'resposta': f'📋 Há {len(intents_duimp)} DUIMPs pendentes. Qual deseja confirmar?\n\n{lista_opcoes}\n\n💡 Digite o número (1, 2, 3...) ou "cancelar" para cancelar.',
                    'requer_escolha': True,  # ✅ Flag para indicar que precisa escolha
                    'opcoes': intents_duimp  # ✅ Incluir opções para processamento posterior
                }
            
            # Buscar pending intent de DUIMP
            pending_intent = self.buscar_pending_intent(session_id, action_type='create_duimp')
            
            if pending_intent:
                intent_id = pending_intent.get('intent_id')
                # ✅ NOVO: Verificar status (idempotência)
                status_intent = pending_intent.get('status')
                if status_intent != 'pending':
                    if status_intent == 'executed':
                        return {
                            'sucesso': False,
                            'erro': 'JA_EXECUTADO',
                            'resposta': '❌ Esta DUIMP já foi criada anteriormente.'
                        }
                    elif status_intent == 'executing':
                        return {
                            'sucesso': False,
                            'erro': 'EM_EXECUCAO',
                            'resposta': '❌ Esta DUIMP está sendo processada. Aguarde alguns instantes.'
                        }
                    elif status_intent == 'expired':
                        return {
                            'sucesso': False,
                            'erro': 'EXPIRADO',
                            'resposta': '❌ Esta DUIMP expirou. Gere o preview novamente.'
                        }
                    elif status_intent == 'cancelled':
                        return {
                            'sucesso': False,
                            'erro': 'CANCELADO',
                            'resposta': '❌ Esta DUIMP foi cancelada. Gere uma nova DUIMP se necessário.'
                        }
                
                # ✅ NOVO (14/01/2026): Confirmação atômica - marcar como executing primeiro
                service = self._get_pending_intent_service()
                if service:
                    lock_obtido = service.marcar_como_executando(intent_id)
                    if not lock_obtido:
                        # ✅ CORRIGIDO (14/01/2026): Log detalhado para debug
                        logger.warning(
                            f'⚠️ Lock NÃO obtido para intent {intent_id} '
                            f'(session: {session_id}, action: {pending_intent.get("action_type")}, '
                            f'status atual: {pending_intent.get("status")})'
                        )
                        # Alguém já pegou o lock (concorrência)
                        return {
                            'sucesso': False,
                            'erro': 'EM_EXECUCAO',
                            'resposta': '❌ Esta DUIMP está sendo processada por outra requisição. Aguarde alguns instantes.'
                        }
                
                # ✅ SQLite como fonte da verdade - usar args_normalizados do DB
                args = pending_intent.get('args_normalizados', {})
                estado_duimp = {
                    'processo_referencia': args.get('processo_referencia'),
                    'ambiente': args.get('ambiente', 'Validacao')
                }
                logger.info(f'✅ Pending intent encontrado para DUIMP: {intent_id} (usando SQLite como fonte da verdade)')
        
        if not estado_duimp:
            return {
                'sucesso': False,
                'erro': 'ESTADO_DUIMP_NAO_ENCONTRADO',
                'resposta': '❌ Não há DUIMP pendente para criar. Crie uma DUIMP primeiro.'
            }
        
        # Processo: se o usuário mencionar outro processo agora, priorizar o da mensagem;
        # caso contrário, usar o salvo no estado.
        processo_msg = None
        if self._extrair_processo_referencia:
            processo_msg = self._extrair_processo_referencia(mensagem)
        
        processo_para_criar = processo_msg or estado_duimp.get('processo_referencia')
        ambiente_para_criar = estado_duimp.get('ambiente', 'validacao')
        
        logger.info(f'✅✅✅ [CONFIRMACAO] Confirmação de DUIMP detectada - criando DUIMP do processo {processo_para_criar} (ambiente={ambiente_para_criar})')
        
        try:
            # ✅ SEGURANÇA: não executar DUIMP diretamente via agent aqui.
            # A execução deve passar pelo ChatService/_executar_funcao_tool com selo do pending intent.
            if not self._executar_funcao_tool:
                # Sem executor: evitar execução e marcar intent como expirado para não ficar travado em 'executing'
                if intent_id:
                    service = self._get_pending_intent_service()
                    if service:
                        try:
                            service.marcar_como_expirado(intent_id, observacoes='Execução bloqueada: executor não disponível')
                        except Exception:
                            pass
                return {
                    'sucesso': False,
                    'erro': 'EXECUTOR_NAO_DISPONIVEL',
                    'resposta': '❌ Execução bloqueada: executor de tools não disponível.'
                }
            
            resultado = self._executar_funcao_tool(
                'criar_duimp',
                {
                    'processo_referencia': processo_para_criar,
                    'ambiente': ambiente_para_criar,
                    'confirmar': True,
                    '_confirmed_intent_id': intent_id,
                    '_confirmed_action_type': 'create_duimp',
                },
                mensagem_original=mensagem,
                session_id=session_id
            )
            
            if resultado.get('sucesso'):
                # ✅ NOVO: Marcar pending intent como executado
                if intent_id:
                    service = self._get_pending_intent_service()
                    if service:
                        service.marcar_como_executado(intent_id, observacoes='DUIMP criada com sucesso')
                        logger.info(f'✅ Pending intent {intent_id} marcado como executado')
                
                return {
                    'sucesso': True,
                    'resposta': resultado.get('resposta', 'DUIMP criada com sucesso'),
                    'tool_calling': {
                        'name': 'criar_duimp',
                        'arguments': {
                            'processo_referencia': processo_para_criar,
                            'ambiente': ambiente_para_criar,
                            'confirmar': True
                        }
                    },
                    'numero_duimp': resultado.get('numero'),
                    'versao_duimp': resultado.get('versao')
                }
            else:
                # Se falhou após lock, marcar como expired para evitar re-execução acidental
                if intent_id:
                    service = self._get_pending_intent_service()
                    if service:
                        try:
                            service.marcar_como_expirado(intent_id, observacoes=f'Falha ao criar DUIMP: {resultado.get("erro")}')
                        except Exception:
                            pass
                return {
                    'sucesso': False,
                    'resposta': resultado.get('resposta', 'Erro ao criar DUIMP'),
                    'erro': resultado.get('erro')
                }
        except Exception as e:
            logger.error(f'❌ Erro ao criar DUIMP após confirmação: {e}', exc_info=True)
            if intent_id:
                service = self._get_pending_intent_service()
                if service:
                    try:
                        service.marcar_como_expirado(intent_id, observacoes=f'Exceção ao criar DUIMP: {e}')
                    except Exception:
                        pass
            return {
                'sucesso': False,
                'resposta': f'❌ Erro ao criar DUIMP: {str(e)}',
                'erro': 'ERRO_CRIACAO_DUIMP'
            }
    
    def limpar_estado_email(self) -> None:
        """Limpa estado de email pendente (para ser chamado após envio)."""
        # Esta função será chamada pelo chat_service para limpar o estado
        pass  # O chat_service gerencia o estado
    
    def limpar_estado_duimp(self, session_id: Optional[str] = None) -> None:
        """Limpa estado de DUIMP pendente (para ser chamado após criação)."""
        # Esta função será chamada pelo chat_service para limpar o estado
        if session_id and self.context_service:
            try:
                self.context_service.limpar_contexto_sessao(
                    session_id=session_id,
                    tipo_contexto='duimp_aguardando_confirmacao'
                )
                logger.info('[CONFIRMACAO] Contexto persistente de DUIMP limpo')
            except Exception as e:
                logger.debug(f'[CONFIRMACAO] Falha ao limpar contexto persistente: {e}')
    
    def processar_confirmacao_pagamento_afrmm(
        self,
        mensagem: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa confirmação de pagamento AFRMM.
        
        ✅ NOVO (21/01/2026): Busca pending intent e executa pagamento após confirmação.
        
        Args:
            mensagem: Mensagem do usuário
            session_id: ID da sessão (para buscar pending intent)
        
        Returns:
            Dict com resultado do pagamento:
            - sucesso: bool
            - resposta: str
            - erro: str (se houver)
        """
        if not session_id:
            return {
                'sucesso': False,
                'erro': 'SEM_SESSION_ID',
                'resposta': '❌ Erro: session_id não fornecido.'
            }
        
        service = self._get_pending_intent_service()
        if not service:
            return {
                'sucesso': False,
                'erro': 'SERVICE_NAO_DISPONIVEL',
                'resposta': '❌ Erro: serviço de pending intents não disponível.'
            }
        
        mensagem_norm = (mensagem or "").strip().lower()
        eh_numero = mensagem_norm.isdigit()
        # ✅ Confirmação determinística (exata)
        CONFIRM_WORDS = {"sim", "pagar", "confirmar", "confirma", "ok", "enviar", "executar", "pode", "pode pagar", "pode enviar"}
        eh_confirmacao = mensagem_norm in CONFIRM_WORDS

        # Buscar pending intent de pagamento
        todos_intents = self.buscar_todos_pending_intents(session_id, status='pending')
        # ✅ CRÍTICO: filtrar apenas pagamentos AFRMM (evita misturar com outros "payment")
        intents_pagamento = [
            i for i in todos_intents
            if i.get('action_type') == 'payment'
            and i.get('tool_name') == 'executar_pagamento_afrmm'
        ]
        
        if len(intents_pagamento) > 1:
            # ✅ Se usuário digitou número, usar como escolha
            if eh_numero:
                idx = int(mensagem_norm) - 1
                if 0 <= idx < len(intents_pagamento):
                    escolhido = intents_pagamento[idx]
                    # Cancelar os outros para não voltar a aparecer lista
                    try:
                        for intent in intents_pagamento:
                            if intent.get('intent_id') != escolhido.get('intent_id'):
                                service.marcar_como_cancelado(
                                    intent.get('intent_id'),
                                    observacoes='Superseded: outro pagamento AFRMM escolhido na sessão'
                                )
                    except Exception:
                        pass
                    pending_intent = escolhido
                else:
                    return {
                        'sucesso': False,
                        'erro': 'ESCOLHA_INVALIDA',
                        'resposta': f'❌ Escolha inválida. Digite um número entre 1 e {len(intents_pagamento)} ou "cancelar".'
                    }
            # ✅ Se usuário disse "sim/confirmar", escolher automaticamente o MAIS RECENTE e cancelar os outros
            elif eh_confirmacao:
                pending_intent = intents_pagamento[0]  # já vem ordenado por created_at desc
                try:
                    for intent in intents_pagamento[1:]:
                        service.marcar_como_cancelado(
                            intent.get('intent_id'),
                            observacoes='Superseded: confirmação automática escolheu o intent mais recente'
                        )
                except Exception:
                    pass
            else:
                # Múltiplos pagamentos pendentes - pedir escolha numerada
                def _fmt_valor(val: Any) -> str:
                    if val is None:
                        return "N/D"
                    try:
                        v = float(val)
                        return f"R$ {v:,.2f}"
                    except Exception:
                        return "N/D"

                linhas = []
                for idx, intent in enumerate(intents_pagamento):
                    args_i = intent.get('args_normalizados') or {}
                    proc_i = args_i.get('processo_referencia') or 'N/A'
                    valor_i = _fmt_valor(args_i.get('valor_debito'))
                    linhas.append(f"({idx+1}) AFRMM do processo {proc_i} - Valor: {valor_i}")

                lista_opcoes = "\n".join(linhas)
                return {
                    'sucesso': False,
                    'erro': 'MULTIPLOS_PENDENTES',
                    'resposta': f'📋 Há {len(intents_pagamento)} pagamentos AFRMM pendentes. Qual deseja confirmar?\n\n{lista_opcoes}\n\n💡 Digite o número (1, 2, 3...) ou "cancelar" para cancelar.',
                    'requer_escolha': True,
                    'opcoes': intents_pagamento
                }

        else:
            pending_intent = self.buscar_pending_intent(session_id, action_type='payment')
        if not pending_intent:
            return {
                'sucesso': False,
                'erro': 'PENDING_INTENT_NAO_ENCONTRADO',
                'resposta': '❌ Não há pagamento AFRMM pendente para confirmar. Gere o preview primeiro.'
            }
        
        intent_id = pending_intent.get('intent_id')
        status_intent = pending_intent.get('status')
        
        # Verificar status (idempotência)
        if status_intent != 'pending':
            if status_intent == 'executed':
                return {
                    'sucesso': False,
                    'erro': 'JA_EXECUTADO',
                    'resposta': '❌ Este pagamento já foi executado anteriormente.'
                }
            elif status_intent == 'executing':
                return {
                    'sucesso': False,
                    'erro': 'EM_EXECUCAO',
                    'resposta': '❌ Este pagamento está sendo processado. Aguarde alguns instantes.'
                }
            elif status_intent == 'expired':
                return {
                    'sucesso': False,
                    'erro': 'EXPIRADO',
                    'resposta': '❌ Este pagamento expirou. Gere o preview novamente.'
                }
            elif status_intent == 'cancelled':
                return {
                    'sucesso': False,
                    'erro': 'CANCELADO',
                    'resposta': '❌ Este pagamento foi cancelado. Gere um novo preview se necessário.'
                }
        
        # Confirmação atômica - marcar como executing primeiro
        lock_obtido = service.marcar_como_executando(intent_id)
        if not lock_obtido:
            logger.warning(
                f'⚠️ Lock NÃO obtido para intent {intent_id} '
                f'(session: {session_id}, action: payment, status atual: {status_intent})'
            )
            return {
                'sucesso': False,
                'erro': 'EM_EXECUCAO',
                'resposta': '❌ Este pagamento está sendo processado por outra requisição. Aguarde alguns instantes.'
            }
        
        # SQLite como fonte da verdade - usar args_normalizados do DB
        args = pending_intent.get('args_normalizados', {})
        processo_ref = args.get('processo_referencia')
        ce_mercante = args.get('ce_mercante')
        parcela = args.get('parcela')
        
        logger.info(f'✅✅✅ [CONFIRMACAO] Confirmação de pagamento AFRMM detectada - executando pagamento do processo {processo_ref}')
        
        try:
            if not self._executar_funcao_tool:
                logger.error(f'❌ [CONFIRMACAO] _executar_funcao_tool não está disponível no ConfirmationHandler')
                # Sem executor: evitar execução e marcar intent como expirado
                if intent_id:
                    try:
                        service.marcar_como_expirado(intent_id, observacoes='Execução bloqueada: executor não disponível')
                    except Exception:
                        pass
                return {
                    'sucesso': False,
                    'erro': 'EXECUTOR_NAO_DISPONIVEL',
                    'resposta': '❌ Execução bloqueada: executor de tools não disponível.'
                }
            
            logger.info(f'✅✅✅ [CONFIRMACAO] Executando tool executar_pagamento_afrmm com confirmar_pagamento=True')
            # Executar via tool (o MercanteAgent vai disparar o bot com --clicar_pagar)
            # ✅ CRÍTICO: Passar session_id nos argumentos também (para garantir que chegue no context)
            resultado = self._executar_funcao_tool(
                'executar_pagamento_afrmm',
                {
                    'processo_referencia': processo_ref,
                    'parcela': parcela,
                    'confirmar_pagamento': True,  # ✅ CRÍTICO: Flag para executar pagamento (não criar preview)
                    '_confirmed_intent_id': intent_id,
                    'session_id': session_id,  # ✅ CRÍTICO: Passar session_id nos argumentos também
                },
                mensagem_original=mensagem,
                session_id=session_id
            )
            
            logger.info(f'🔍 [CONFIRMACAO] Resultado da execução: sucesso={resultado.get("sucesso") if resultado else None}, erro={resultado.get("erro") if resultado else None}')
            
            if resultado.get('sucesso'):
                # Marcar pending intent como executado
                if intent_id:
                    service.marcar_como_executado(intent_id, observacoes='Pagamento AFRMM executado com sucesso')
                    logger.info(f'✅ Pending intent {intent_id} marcado como executado')
                
                return {
                    'sucesso': True,
                    'resposta': resultado.get('resposta', 'Pagamento AFRMM executado com sucesso'),
                    'tool_calling': {
                        'name': 'executar_pagamento_afrmm',
                        'arguments': {
                            'processo_referencia': processo_ref,
                            'parcela': parcela,
                            'confirmar_pagamento': True
                        }
                    }
                }
            else:
                # Se falhou após lock, marcar como expired para evitar re-execução acidental
                if intent_id:
                    try:
                        service.marcar_como_expirado(intent_id, observacoes=f'Falha ao executar pagamento: {resultado.get("erro")}')
                    except Exception:
                        pass
                return {
                    'sucesso': False,
                    'resposta': resultado.get('resposta', 'Erro ao executar pagamento AFRMM'),
                    'erro': resultado.get('erro')
                }
        except Exception as e:
            logger.error(f'❌ Erro ao executar pagamento AFRMM após confirmação: {e}', exc_info=True)
            if intent_id:
                try:
                    service.marcar_como_expirado(intent_id, observacoes=f'Exceção ao executar pagamento: {e}')
                except Exception:
                    pass
            return {
                'sucesso': False,
                'resposta': f'❌ Erro ao executar pagamento AFRMM: {str(e)}',
                'erro': 'ERRO_EXECUCAO_PAGAMENTO'
            }
