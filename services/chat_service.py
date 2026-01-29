"""
=============================================================================
🤖 SERVIÇO DE CHAT IA - ASSISTENTE INTELIGENTE PARA DUIMP E PROCESSOS
=============================================================================
Este arquivo implementa o serviço de chat conversacional com IA que permite
interagir com o sistema de DUIMP e processos de importação usando linguagem
natural.

📊 ESTRUTURA DO ARQUIVO:
   - Total de linhas: ~8.024
   - Classe principal: ChatService
   - Método principal: processar_mensagem()
   - Funcionalidades: Chat IA, sugestão de NCM, gestão de processos, etc.

🎯 PRINCIPAIS FUNCIONALIDADES:

   1. PROCESSAMENTO DE MENSAGENS EM LINGUAGEM NATURAL
      ───────────────────────────────────────────────────────────────────────
      - Interpreta comandos e perguntas em português
      - Identifica intenções do usuário automaticamente
      - Executa ações baseadas no contexto da conversa
      - Suporta múltiplos modelos de IA (GPT-3.5, GPT-4, etc.)

   2. GESTÃO DE PROCESSOS DE IMPORTAÇÃO
      ───────────────────────────────────────────────────────────────────────
      - Consulta de status de processos (ALH, VDM, MSS, BND, DMD, GYM, SLL)
      - Listagem por categoria, situação, ETA, pendências, bloqueios
      - Extração automática de referências de processo da mensagem
      - Contexto inteligente entre mensagens

   3. CRIAÇÃO AUTOMÁTICA DE DUIMP
      ───────────────────────────────────────────────────────────────────────
      - Detecta quando usuário quer criar DUIMP para um processo
      - Extrai dados do processo automaticamente
      - Cria DUIMP via API do Portal Único
      - Confirmação inteligente de ações

   4. SUGESTÃO INTELIGENTE DE NCM
      ───────────────────────────────────────────────────────────────────────
      - Busca NCM por descrição de produto
      - Integração com busca web (DuckDuckGo) para contexto
      - Validação genérica baseada em tipo de produto
      - Notas explicativas NESH para contexto adicional
      - Sistema de cache para otimização

   5. VINCULAÇÃO DE DOCUMENTOS
      ───────────────────────────────────────────────────────────────────────
      - Vinculação de CE, CCT, DI, DUIMP a processos
      - Desvinculação de documentos
      - Detecção automática de documentos na mensagem

   6. CONSULTAS BILHETADAS (INTEGRA COMEX)
      ───────────────────────────────────────────────────────────────────────
      - Listagem de consultas pendentes
      - Aprovação/rejeição de consultas
      - Execução automática de consultas aprovadas
      - Sistema de proteção contra consultas duplicadas

   7. INTEGRAÇÃO COM SHIPSGO
      ───────────────────────────────────────────────────────────────────────
      - Consulta de ETA (previsão de chegada)
      - Informações de porto de destino
      - Filtros por data de chegada (hoje, amanhã, semana, mês)

🔧 ARQUITETURA:

   - ToolRouter: Sistema de roteamento de funções (arquitetura escalável)
   - Tool Calling: Execução de funções baseada em intenções da IA
   - Precheck Logic: Detecção proativa de intenções antes da IA
   - Context Management: Gerenciamento inteligente de contexto entre mensagens

📚 DEPENDÊNCIAS PRINCIPAIS:

   - ai_service: Serviço de IA (OpenAI, etc.)
   - db_manager: Gerenciamento de banco de dados SQLite
   - tool_definitions: Definições de funções disponíveis para IA
   - tool_router: Roteador de funções (fallback inteligente)

⚠️ REGRAS CRÍTICAS:

   1. SEMPRE priorizar DUIMPs de PRODUÇÃO sobre validação
   2. NUNCA misturar informações de processos diferentes
   3. SEMPRE validar NCM sugerido com tipo de produto identificado
   4. SEMPRE usar cache quando possível para evitar consultas bilhetadas
   5. SEMPRE detectar confirmações do usuário antes de executar ações críticas

🔗 VER TAMBÉM:

   - app.py: Endpoint principal /api/chat que usa este serviço
   - services/ai_service.py: Serviço de IA subjacente
   - services/tool_definitions.py: Definições de funções
   - services/tool_router.py: Roteador de funções
   - db_manager.py: Gerenciamento de banco de dados
=============================================================================
"""
import json
import logging
import re
import requests
from typing import Dict, Any, Optional, List, Tuple
from db_manager import obter_dados_documentos_processo
from ai_service import get_ai_service, AI_MODEL_DEFAULT, AI_MODEL_ANALITICO, AI_MODEL_CONHECIMENTO_GERAL
from services.tool_definitions import get_available_tools
from services.tool_router import ToolRouter
from services.precheck_service import PrecheckService
from services.prompt_builder import PromptBuilder
from services.tool_executor import ToolExecutor
from services.chat_service_streaming_mixin import ChatServiceStreamingMixin
from services.saved_queries_service import ensure_consultas_padrao
from services.learned_rules_service import buscar_regras_aprendidas, formatar_regras_para_prompt
from services.context_service import buscar_contexto_sessao, formatar_contexto_para_prompt
from services.legislacao_strict_mode import (
    LEGISLACAO_STRICT_SYSTEM_PROMPT,
    montar_user_prompt_legislacao,
    detectar_modo_estrito,
    eh_pergunta_conceitual_pura
)

logger = logging.getLogger(__name__)


class ChatService(ChatServiceStreamingMixin):
    """
    Serviço de chat com IA para comandos em linguagem natural.
    
    Esta classe é o coração do sistema de chat inteligente, permitindo que usuários
    interajam com o sistema de DUIMP e processos usando linguagem natural.
    
    🎯 PRINCIPAIS CAPACIDADES:
       - Processamento de mensagens em português
       - Identificação automática de intenções
       - Execução de ações baseadas em contexto
       - Sugestão inteligente de NCM
       - Criação automática de DUIMP
       - Consulta de processos e documentos
    
    🔧 ARQUITETURA:
       - ToolRouter: Sistema de roteamento de funções (fallback inteligente)
       - AI Service: Integração com modelos de IA (GPT-3.5, GPT-4, etc.)
       - Tool Calling: Execução de funções baseada em intenções da IA
       - Precheck Logic: Detecção proativa antes da IA processar
    """
    
    def __init__(self):
        """
        Inicializa o serviço de chat.
        
        Configura:
        - Serviço de IA (ai_service)
        - ToolRouter para roteamento de funções
        - Estado habilitado/desabilitado baseado na disponibilidade da IA
        """
        self.ai_service = get_ai_service()
        self.enabled = self.ai_service.enabled
        # Builder responsável por montar system_prompt e user_prompt
        self.prompt_builder = PromptBuilder()
        
        # 🆕 Inicializar ToolRouter para arquitetura escalável
        # ToolRouter fornece fallback inteligente quando IA não chama função correta
        try:
            self.tool_router = ToolRouter()
            logger.info("✅ ToolRouter inicializado com sucesso")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar ToolRouter: {e}. Usando implementação antiga.")
            self.tool_router = None

        # Executor de tools (nova camada fina sobre o ToolRouter)
        try:
            self.tool_executor = ToolExecutor(self.tool_router)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar ToolExecutor: {e}")
            self.tool_executor = None
        
        # ✅ NOVO (09/01/2026): ToolExecutionService para extrair lógica de tools
        try:
            from services.tool_execution_service import ToolExecutionService, ToolContext
            from services.email_send_coordinator import get_email_send_coordinator
            from services.email_draft_service import get_email_draft_service
            from services.email_service import get_email_service
            from services.utils.entity_extractors import EntityExtractors
            
            # Criar contexto enxuto
            # ✅ REFATORADO (10/01/2026): Usar EntityExtractors diretamente para extrair_processo_referencia
            tool_context = ToolContext(
                email_service=get_email_service(),
                email_draft_service=get_email_draft_service(),
                email_send_coordinator=get_email_send_coordinator(),
                obter_email_para_enviar=self._obter_email_para_enviar,
                extrair_processo_referencia=EntityExtractors.extrair_processo_referencia,  # ✅ Usar método estático
                obter_contexto_processo=self._obter_contexto_processo if hasattr(self, '_obter_contexto_processo') else None,
                limpar_frases_problematicas=self._limpar_frases_problematicas if hasattr(self, '_limpar_frases_problematicas') else None,
                logger=logger
            )
            self.tool_execution_service = ToolExecutionService(tool_context=tool_context)
            logger.info("✅ ToolExecutionService inicializado com sucesso")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar ToolExecutionService: {e}")
            self.tool_execution_service = None
        
        # ✅ NOVO: Estado para aguardar confirmação de email
        self.ultima_resposta_aguardando_email = None
        # ✅ MULTIUSUÁRIO (16/01/2026): isolar estados pendentes por sessão para evitar vazamento entre usuários
        # Mantemos os atributos "legacy" acima por compatibilidade, mas preferimos os mapas por session_id.
        self._email_pendente_por_sessao = {}  # session_id -> dict payload email preview
        self._duimp_pendente_por_sessao = {}  # session_id -> dict payload duimp pendente
        # ✅ NOVO: Armazenar última lista de emails para obter_detalhes_email
        self.ultima_lista_emails = None

        # ✅ IMPORTANTE: garantir atributo sempre presente (evita AttributeError no streaming)
        self.message_processing_service = None

        # Serviço de precheck determinístico (situação de processo, NCM, etc.)
        try:
            self.precheck_service = PrecheckService(self)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar PrecheckService: {e}")
            self.precheck_service = None

        # ✅ NOVO (09/01/2026): ConfirmationHandler para centralizar lógica de confirmação
        try:
            from services.handlers.confirmation_handler import ConfirmationHandler
            from services.email_send_coordinator import get_email_send_coordinator
            from services.utils.entity_extractors import EntityExtractors
            email_send_coordinator = get_email_send_coordinator()
            self.confirmation_handler = ConfirmationHandler(
                email_send_coordinator=email_send_coordinator,
                obter_email_para_enviar=self._obter_email_para_enviar,
                executar_funcao_tool=self._executar_funcao_tool,
                extrair_processo_referencia=EntityExtractors.extrair_processo_referencia  # ✅ REFATORADO (10/01/2026): Usar EntityExtractors
            )
            logger.info("✅ ConfirmationHandler inicializado com sucesso (com EmailSendCoordinator)")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar ConfirmationHandler: {e}")
            self.confirmation_handler = None
        
        # ✅ NOVO (09/01/2026): EmailImprovementHandler para centralizar lógica de melhorar email
        try:
            from services.handlers.email_improvement_handler import get_email_improvement_handler
            self.email_improvement_handler = get_email_improvement_handler()
            logger.info("✅ EmailImprovementHandler inicializado com sucesso")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar EmailImprovementHandler: {e}")
            self.email_improvement_handler = None

        # Consultas analíticas padrão (relatórios determinísticos simples)
        try:
            ensure_consultas_padrao()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao garantir consultas analíticas padrão: {e}")
        
        # ✅ PASSO 3.5 - FASE 3.5.2: Inicializar MessageProcessingService
        try:
            from services.message_processing_service import MessageProcessingService
            from services.handlers.response_formatter import ResponseFormatter
            from services.utils.email_utils import EmailUtils
            
            # Criar ResponseFormatter
            response_formatter = ResponseFormatter(
                limpar_frases_callback=EmailUtils.limpar_frases_problematicas
            )
            
            # Inicializar MessageProcessingService
            self.message_processing_service = MessageProcessingService(
                confirmation_handler=self.confirmation_handler,
                precheck_service=self.precheck_service,
                tool_execution_service=self.tool_execution_service,
                prompt_builder=self.prompt_builder,
                ai_service=self.ai_service,
                obter_email_para_enviar=self._obter_email_para_enviar,
                extrair_processo_referencia=self._extrair_processo_referencia,
                response_formatter=response_formatter
            )
            logger.info("✅ MessageProcessingService inicializado com sucesso")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar MessageProcessingService: {e}", exc_info=True)
            self.message_processing_service = None

    def _get_email_pendente(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return self.ultima_resposta_aguardando_email
        if hasattr(self, "_email_pendente_por_sessao") and isinstance(self._email_pendente_por_sessao, dict):
            return self._email_pendente_por_sessao.get(session_id)
        return self.ultima_resposta_aguardando_email

    def _set_email_pendente(self, session_id: Optional[str], payload: Optional[Dict[str, Any]]) -> None:
        if session_id and hasattr(self, "_email_pendente_por_sessao") and isinstance(self._email_pendente_por_sessao, dict):
            if payload is None:
                self._email_pendente_por_sessao.pop(session_id, None)
            else:
                self._email_pendente_por_sessao[session_id] = payload
        else:
            self.ultima_resposta_aguardando_email = payload

    def _clear_email_pendente(self, session_id: Optional[str]) -> None:
        self._set_email_pendente(session_id, None)

    def _get_duimp_pendente(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if session_id and hasattr(self, "_duimp_pendente_por_sessao") and isinstance(self._duimp_pendente_por_sessao, dict):
            return self._duimp_pendente_por_sessao.get(session_id)
        return getattr(self, "ultima_resposta_aguardando_duimp", None)

    def _set_duimp_pendente(self, session_id: Optional[str], payload: Optional[Dict[str, Any]]) -> None:
        if session_id and hasattr(self, "_duimp_pendente_por_sessao") and isinstance(self._duimp_pendente_por_sessao, dict):
            if payload is None:
                self._duimp_pendente_por_sessao.pop(session_id, None)
            else:
                self._duimp_pendente_por_sessao[session_id] = payload
        else:
            self.ultima_resposta_aguardando_duimp = payload

    def _clear_duimp_pendente(self, session_id: Optional[str]) -> None:
        self._set_duimp_pendente(session_id, None)

    # ------------------------------------------------------------------
    # 🔍 Detecção de perguntas analíticas / BI
    # ------------------------------------------------------------------

    def _eh_pergunta_analitica(self, mensagem: str) -> bool:
        """
        Detecta perguntas de análise/BI onde vale a pena usar o modelo analítico.
        
        ✅ REFATORADO (10/01/2026): Delegado para QuestionClassifier.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.question_classifier import QuestionClassifier
        return QuestionClassifier.eh_pergunta_analitica(mensagem)
    
    def _eh_pergunta_conhecimento_geral(self, mensagem: str) -> bool:
        """
        Detecta perguntas de conhecimento geral onde vale a pena usar GPT-5.
        
        ✅ REFATORADO (10/01/2026): Delegado para QuestionClassifier.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.question_classifier import QuestionClassifier
        return QuestionClassifier.eh_pergunta_conhecimento_geral(mensagem)
    
    def _extrair_processo_referencia(self, mensagem: str) -> Optional[str]:
        """
        Extrai referência de processo da mensagem (ex: ALH.0001/25, vdm.003, etc.).
        
        ✅ REFATORADO (10/01/2026): Delegado para EntityExtractors.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.entity_extractors import EntityExtractors
        return EntityExtractors.extrair_processo_referencia(mensagem, buscar_no_banco=True)
    
    def _buscar_processo_por_variacao(self, prefixo: str, numero: str) -> Optional[str]:
        """
        Busca processo completo no banco por variação parcial (ex: VDM, 003).
        
        ✅ REFATORADO (10/01/2026): Delegado para EntityExtractors.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.entity_extractors import EntityExtractors
        return EntityExtractors.buscar_processo_por_variacao(prefixo, numero)
    
    def _verificar_duimp_processo(self, processo_referencia: str) -> Dict[str, Any]:
        """Verifica se há DUIMP registrada para o processo.
        
        ✅ CRÍTICO: 
        - SEMPRE prioriza DUIMPs de PRODUÇÃO sobre validação
        - Retorna DUIMP de produção se existir, senão retorna None (não retorna validação)
        - DUIMPs de validação são apenas para testes e não devem ser consideradas como produção
        """
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # ✅ CRÍTICO: Buscar PRIMEIRO DUIMP de PRODUÇÃO (prioridade máxima)
            cursor.execute('''
                SELECT numero, versao, status, ambiente, criado_em, payload_completo
                FROM duimps
                WHERE processo_referencia = ? AND ambiente = 'producao'
                ORDER BY CAST(versao AS INTEGER) DESC, criado_em DESC
                LIMIT 1
            ''', (processo_referencia,))
            
            row_producao = cursor.fetchone()
            
            if row_producao:
                # ✅ Encontrou DUIMP de PRODUÇÃO - processar e retornar
                duimp_numero = row_producao['numero']
                duimp_versao = row_producao['versao']
                versao_int = int(duimp_versao) if duimp_versao.isdigit() else 0
                
                # ✅ VALIDAÇÃO: Verificar se o payload não é uma mensagem de erro
                payload_completo_str = row_producao['payload_completo']
                if payload_completo_str:
                    try:
                        import json
                        payload_completo = json.loads(payload_completo_str) if isinstance(payload_completo_str, str) else payload_completo_str
                        if isinstance(payload_completo, dict) and payload_completo.get('code') == 'PUCX-ER0014':
                            conn.close()
                            return {'registrada': False, 'existe': False}  # Ignorar payloads de erro
                    except:
                        pass
                
                # Extrair situação do payload se disponível
                situacao_duimp = None
                try:
                    import json
                    payload_str = row_producao['payload_completo']
                    if payload_str:
                        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                        if isinstance(payload, dict):
                            situacao_obj = payload.get('situacao', {})
                            if isinstance(situacao_obj, dict):
                                situacao_duimp = situacao_obj.get('situacaoDuimp', '')
                except:
                    pass
                
                conn.close()
                
                resultado = {
                    'registrada': versao_int >= 1,  # ✅ Registrada se versão >= 1
                    'numero': duimp_numero,
                    'versao': duimp_versao,
                    'status': row_producao['status'],
                    'situacao': situacao_duimp or row_producao['status'],
                    'ambiente': 'producao',  # ✅ SEMPRE produção
                    'criado_em': row_producao['criado_em'],
                    'existe': True,  # ✅ Flag indicando que existe
                    'eh_producao': True  # ✅ Flag crítica: é produção
                }
                
                return resultado
            
            # ✅ NÃO encontrou DUIMP de PRODUÇÃO - retornar None
            # NÃO retornar DUIMP de validação aqui - ela é apenas para testes
            conn.close()
            return {'registrada': False, 'existe': False, 'eh_producao': False}
        except Exception as e:
            logger.warning(f'Erro ao verificar DUIMP do processo {processo_referencia}: {e}')
            return {'registrada': False, 'erro': str(e)}
    
    def _buscar_documentos_duimp(self, duimp_numero: str, duimp_versao: str) -> List[Dict[str, Any]]:
        """Busca documentos enviados na DUIMP do banco de dados."""
        try:
            import sqlite3
            import json
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT payload_completo
                FROM duimps
                WHERE numero = ? AND versao = ?
                LIMIT 1
            ''', (duimp_numero, duimp_versao))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                payload_str = row[0]
                try:
                    payload = json.loads(payload_str)
                    documentos = payload.get('documentos', {}).get('documentosInstrucao', [])
                    return documentos if isinstance(documentos, list) else []
                except json.JSONDecodeError:
                    logger.warning(f'Erro ao parsear payload da DUIMP {duimp_numero} v{duimp_versao}')
                    return []
            
            return []
        except Exception as e:
            logger.warning(f'Erro ao buscar documentos da DUIMP {duimp_numero} v{duimp_versao}: {e}')
            return []
    
    def _extrair_numero_ce(self, mensagem: str) -> Optional[str]:
        """
        Extrai número de CE da mensagem.
        
        ✅ REFATORADO (10/01/2026): Delegado para EntityExtractors.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.entity_extractors import EntityExtractors
        return EntityExtractors.extrair_numero_ce(mensagem)
    
    def _extrair_numero_cct(self, mensagem: str) -> Optional[str]:
        """
        Extrai número de CCT da mensagem.
        
        ✅ REFATORADO (10/01/2026): Delegado para EntityExtractors.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.entity_extractors import EntityExtractors
        return EntityExtractors.extrair_numero_cct(mensagem)
    
    def _extrair_numero_duimp_ou_di(self, mensagem: str) -> Optional[Dict[str, str]]:
        """
        Extrai número de DUIMP ou DI da mensagem com reconhecimento automático.
        
        ✅ REFATORADO (10/01/2026): Delegado para EntityExtractors.
        Mantido como método de instância para compatibilidade com código existente.
        
        Retorna:
            Dict com:
            - 'tipo': 'DUIMP' ou 'DI'
            - 'numero': número sem versão (ex: '25BR0000194844')
            - 'versao': versão se informada (ex: '1'), ou None
            - 'numero_completo': número completo como informado (ex: '25BR0000194844-1')
        """
        from services.utils.entity_extractors import EntityExtractors
        return EntityExtractors.extrair_numero_duimp_ou_di(mensagem)
    
    def _obter_contexto_processo(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Obtém contexto completo de um processo, incluindo DUIMP se houver.
        
        ✅ REFATORADO (10/01/2026): Delegado para ContextExtractionHandler.
        Mantido como método de instância para compatibilidade com código existente.
        """
        if not hasattr(self, '_context_extraction_handler'):
            from services.handlers.context_extraction_handler import ContextExtractionHandler
            self._context_extraction_handler = ContextExtractionHandler(chat_service=self)
        
        return self._context_extraction_handler.obter_contexto_processo(processo_referencia)
    
    def _identificar_acao(self, mensagem: str, contexto_processo: Optional[Dict] = None) -> Dict[str, Any]:
        """Identifica a ação solicitada na mensagem."""
        mensagem_lower = mensagem.lower()
        
        # ✅ NOVO: Primeiro verificar se é uma PERGUNTA (não um comando)
        # Perguntas não devem criar DUIMP automaticamente
        perguntas = [
            r'^(?:tem|tem\s+algum|tem\s+alguma|tem\s+alguns|tem\s+algumas)',
            r'^(?:qual|quais|quando|onde|como|quem|por\s+que|por\s+quê)',
            r'^(?:esse|esta|este|esse\s+ce|esta\s+ce|este\s+ce)',
            r'pend[êe]ncia',
            r'bloqueio',
            r'frete',
            r'situa[çc][ãa]o',
            r'status',
            r'consignat[áa]rio',
            r'origem',
            r'destino',
            r'navio',
            r'afrmm',
            r'tum',
            r'peso',
            r'cubagem'
        ]
        
        eh_pergunta = False
        for padrao_pergunta in perguntas:
            if re.search(padrao_pergunta, mensagem_lower):
                eh_pergunta = True
                break
        
        # Padrões de comandos
        acoes = {
            'criar_duimp': [
                r'cri[ae]r?\s+duimp',
                r'registr[ae]r?\s+(?:a\s+)?duimp',  # ✅ MELHORIA: Aceita "registre a duimp" ou "registre duimp"
                r'registr[ae]r?\s+(?:o\s+)?duimp',    # ✅ Aceita "registre o duimp"
                r'ger[ae]r?\s+duimp',
                r'fazer\s+duimp',
                r'^(?:sim|pode\s+prosseguir|prosseguir|confirmar|confirma|pode\s+criar|pode\s+registrar)',  # ✅ NOVO: Confirmações após IA perguntar
            ],
            'consultar_status': [
                r'status',
                r'como\s+est[áa]',
                r'situa[çc][ãa]o',
                r'verificar',
                r'consultar'
            ],
            'consultar_documentos': [
                r'documentos?',
                r'quais?\s+documentos?',
                r'faltam\s+documentos?'
            ],
            'consultar_bloqueios': [
                r'bloqueios?',
                r'tem\s+bloqueio',
                r'bloqueado'
            ]
        }
        
        acao_identificada = None
        for acao, padroes in acoes.items():
            for padrao in padroes:
                if re.search(padrao, mensagem_lower):
                    acao_identificada = acao
                    break
            if acao_identificada:
                break
        
        # ✅ MELHORIA: Se identificou "registre" sem "duimp", verificar se há processo na mensagem
        # Mas NUNCA criar DUIMP se for uma pergunta
        if not acao_identificada and not eh_pergunta and re.search(r'registr[ae]r', mensagem_lower):
            # Se há processo na mensagem, provavelmente é para criar DUIMP
            if contexto_processo and contexto_processo.get('processo_referencia'):
                acao_identificada = 'criar_duimp'
        
        # ✅ NOVO: Se for uma pergunta, NUNCA criar DUIMP automaticamente
        if eh_pergunta and acao_identificada == 'criar_duimp':
            acao_identificada = None  # Cancelar criação de DUIMP se for pergunta
        
        # Calcular confiança baseada na clareza do comando
        confianca = 0.8 if acao_identificada else 0.3
        if acao_identificada == 'criar_duimp' and contexto_processo and contexto_processo.get('processo_referencia'):
            # Se há processo claro e comando claro, confiança alta
            # Mas NUNCA se for uma pergunta
            if not eh_pergunta:
                confianca = 0.95
            else:
                confianca = 0.1  # Confiança muito baixa se for pergunta
                acao_identificada = None  # Cancelar ação
        
        # ✅ NOVO: Não executar automaticamente quando usuário pede para "registre"
        # Sempre mostrar informações primeiro e aguardar confirmação
        executar_automatico = False  # ✅ SEMPRE False - sempre mostrar informações antes de criar
        
        return {
            'acao': acao_identificada,
            'processo_referencia': contexto_processo.get('processo_referencia') if contexto_processo else None,
            'confianca': confianca,
            'executar_automatico': executar_automatico  # ✅ SEMPRE False - sempre mostrar informações antes
        }
    
    def _executar_funcao_tool(self, nome_funcao: str, argumentos: Dict[str, Any], mensagem_original: Optional[str] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Executa uma função chamada pela IA via tool calling.

        Ordem: ToolExecutionService → ToolExecutor/ToolRouter.
        """
        # ✅ NOVO (09/01/2026): Tentar usar ToolExecutionService primeiro (handlers extraídos)
        if hasattr(self, "tool_execution_service") and self.tool_execution_service is not None:
            try:
                # ✅ Garantir variável definida mesmo se tool_context não existir
                session_id_ctx = session_id or getattr(self, 'session_id_atual', None)

                # Atualizar contexto com session_id e mensagem_original
                if self.tool_execution_service.tool_context:
                    # ✅ CRÍTICO: garantir session_id correto e estável (nunca boolean False)
                    self.tool_execution_service.tool_context.session_id = session_id_ctx if session_id_ctx else None
                    self.tool_execution_service.tool_context.mensagem_original = mensagem_original
                    # ✅ CRÍTICO: garantir que previews via ToolExecutionService criem PendingIntent no SQLite
                    # (confirmação "sim/enviar" depende de context.confirmation_handler)
                    self.tool_execution_service.tool_context.confirmation_handler = getattr(self, 'confirmation_handler', None)
                
                resultado_service = self.tool_execution_service.executar_tool(
                    nome_funcao=nome_funcao,
                    argumentos=argumentos
                )
                
                # Se retornou resultado (não None), usar
                if resultado_service is not None:
                    logger.info(f'✅ Tool {nome_funcao} executada via ToolExecutionService')
                    
                    # ✅ CRÍTICO (09/01/2026): Processar _resultado_interno para salvar draft_id no estado
                    if isinstance(resultado_service, dict):
                        resultado_interno = resultado_service.get('_resultado_interno', {})
                        if resultado_interno and 'ultima_resposta_aguardando_email' in resultado_interno:
                            self._set_email_pendente(session_id_ctx, resultado_interno['ultima_resposta_aguardando_email'])
                            dados_salvos = self._get_email_pendente(session_id_ctx)
                            draft_id_salvo = dados_salvos.get('draft_id') if isinstance(dados_salvos, dict) else None
                            if draft_id_salvo:
                                logger.info(f'✅✅✅ [TOOL_EXECUTION] draft_id {draft_id_salvo} salvo no estado após execução via ToolExecutionService')
                            else:
                                logger.warning(f'⚠️ [TOOL_EXECUTION] ToolExecutionService retornou resultado mas sem draft_id')
                    
                    return resultado_service
            except Exception as e:
                logger.warning(f'⚠️ Erro no ToolExecutionService para {nome_funcao}: {e}. Usando fallback.', exc_info=True)
        # 🆕 Tentar usar ToolExecutor/ToolRouter (arquitetura nova)
        if hasattr(self, "tool_executor") and self.tool_executor is not None:
            resultado_router = self.tool_executor.executar(
                chat_service=self,
                nome_funcao=nome_funcao,
                argumentos=argumentos,
                mensagem_original=mensagem_original,
            )
            # ✅ 19/01/2026: fallback legado removido — não aceitar mais "_use_fallback"/"use_fallback".
            if resultado_router and (resultado_router.get("_use_fallback", False) or resultado_router.get("use_fallback", False)):
                logger.error(f"❌ ToolRouter pediu fallback para '{nome_funcao}', mas o legado foi removido.")
                return {
                    "sucesso": False,
                    "erro": "FALLBACK_LEGADO_REMOVIDO",
                    "resposta": f"❌ Não consegui executar a tool **{nome_funcao}** (fallback legado removido). Reinicie o servidor e tente novamente.",
                }
            # Se o executor retornou resultado, retornar diretamente
            if resultado_router:
                # ✅ NOVO: Se for capa de DUIMP (mostrar_antes_criar), salvar estado aguardando confirmação
                try:
                    if (nome_funcao == "criar_duimp"
                        and isinstance(resultado_router, dict)
                        and resultado_router.get('acao') == 'criar_duimp'
                        and resultado_router.get('mostrar_antes_criar')):
                        processo_ref_router = argumentos.get('processo_referencia', '')
                        ambiente_router = argumentos.get('ambiente', 'validacao')
                        session_id_para_salvar = getattr(self, 'session_id_atual', None) or session_id
                        self._set_duimp_pendente(session_id_para_salvar, {
                            'processo_referencia': (resultado_router.get('processo_referencia') or processo_ref_router),
                            'ambiente': ambiente_router,
                            'payload_duimp': resultado_router.get('payload_duimp')
                        })
                        duimp_salvo = self._get_duimp_pendente(session_id_para_salvar) or {}
                        logger.info(f'🧭 [DUIMP] (Router) Estado aguardando confirmação salvo: processo={duimp_salvo.get("processo_referencia")}, ambiente={duimp_salvo.get("ambiente")}')
                        # ✅ Persistir no contexto da sessão para sobreviver a reinicializações entre mensagens
                        try:
                            from services.context_service import salvar_contexto_sessao
                            if session_id_para_salvar:
                                salvar_contexto_sessao(
                                    session_id=session_id_para_salvar,
                                    tipo_contexto='duimp_aguardando_confirmacao',
                                    chave='processo',
                                    valor=(resultado_router.get('processo_referencia') or processo_ref_router or ''),
                                    dados_adicionais={'ambiente': ambiente_router}
                                )
                                logger.info('[DUIMP] (Router) Estado persistido em contexto_sessao (duimp_aguardando_confirmacao)')
                        except Exception as _e_ctx:
                            logger.debug(f'[DUIMP] (Router) Falha ao persistir estado no contexto: {_e_ctx}')
                except Exception as _e:
                    logger.debug(f'[DUIMP] (Router) Não foi possível salvar estado aguardando confirmação: {_e}')
                return resultado_router
        
        # ⚠️ LEGADO (19/01/2026): mantido apenas por compatibilidade/histórico (não deve mais ser atingido).
        try:
            logger.error(f"❌ Execução caiu no bloco legado de tool '{nome_funcao}' (não deveria ocorrer).")
            return {
                "sucesso": False,
                "erro": "FALLBACK_LEGADO_DESABILITADO",
                "resposta": f"❌ Tool **{nome_funcao}** não executou pelo pipeline oficial e o fallback legado está desabilitado. Reinicie o servidor e tente novamente.",
            }
            if nome_funcao == "criar_duimp":
                # ✅ REFATORAÇÃO: Usar DuimpService em vez de lógica duplicada
                processo_ref = argumentos.get('processo_referencia', '')
                ambiente = argumentos.get('ambiente', 'validacao')
                if not processo_ref:
                    return {'erro': 'processo_referencia é obrigatório'}
                try:
                    from services.duimp_service import DuimpService
                    duimp_service = DuimpService(chat_service=self)
                    
                    # Buscar contexto do processo
                    contexto_processo = self._obter_contexto_processo(processo_ref) if hasattr(self, '_obter_contexto_processo') else None
                    
                    resultado = duimp_service.preparar_criacao_duimp(
                        processo_referencia=processo_ref,
                        ambiente=ambiente,
                        contexto_processo=contexto_processo
                    )
                    # ✅ NOVO: Guardar estado de "aguardando confirmação de DUIMP" na instância
                    # Isso permite que uma resposta simples "sim" seja capturada ANTES da IA,
                    # mesmo que o histórico não seja passado no próximo turno.
                    try:
                        if isinstance(resultado, dict) and resultado.get('acao') == 'criar_duimp' and resultado.get('mostrar_antes_criar'):
                            session_id_para_salvar = getattr(self, 'session_id_atual', None) or session_id
                            self._set_duimp_pendente(session_id_para_salvar, {
                                'processo_referencia': (resultado.get('processo_referencia') or processo_ref),
                                'ambiente': ambiente or 'validacao',
                                'payload_duimp': resultado.get('payload_duimp')
                            })
                            duimp_salvo = self._get_duimp_pendente(session_id_para_salvar) or {}
                            logger.info(f'🧭 [DUIMP] Estado aguardando confirmação salvo: processo={duimp_salvo.get("processo_referencia")}, ambiente={duimp_salvo.get("ambiente")}')
                            # ✅ Persistir no contexto da sessão para sobreviver a reinicializações entre mensagens
                            try:
                                from services.context_service import salvar_contexto_sessao
                                session_id_para_salvar = getattr(self, 'session_id_atual', None) or session_id
                                if session_id_para_salvar:
                                    salvar_contexto_sessao(
                                        session_id=session_id_para_salvar,
                                        tipo_contexto='duimp_aguardando_confirmacao',
                                        chave='processo',
                                        valor=(resultado.get('processo_referencia') or processo_ref or ''),
                                        dados_adicionais={'ambiente': ambiente or 'validacao'}
                                    )
                                    logger.info('[DUIMP] Estado persistido em contexto_sessao (duimp_aguardando_confirmacao)')
                            except Exception as _e_ctx:
                                logger.debug(f'[DUIMP] Falha ao persistir estado no contexto: {_e_ctx}')
                    except Exception as _e:
                        logger.debug(f'[DUIMP] Não foi possível salvar estado aguardando confirmação: {_e}')
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao preparar criação de DUIMP via DuimpService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao preparar criação de DUIMP: {str(e)}'
                    }
            
            elif nome_funcao == "consultar_status_processo":
                # ✅ REFATORAÇÃO: Usar ProcessoStatusService em vez de lógica duplicada
                processo_ref = argumentos.get('processo_referencia', '')
                
                if not processo_ref:
                    return {'erro': 'processo_referencia é obrigatório'}
                
                try:
                    from services.processo_status_service import ProcessoStatusService
                    status_service = ProcessoStatusService()
                    resultado = status_service.consultar_status_processo(
                        processo_referencia=processo_ref,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao consultar status do processo via ProcessoStatusService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao consultar o status do processo {processo_ref}: {str(e)}'
                    }
            
            elif nome_funcao == "listar_processos":
                # ✅ REFATORAÇÃO: Usar ProcessoListService em vez de lógica duplicada
                status = argumentos.get('status')
                limite = argumentos.get('limite', 20)
                
                try:
                    from services.processo_list_service import ProcessoListService
                    list_service = ProcessoListService(chat_service=self)
                    resultado = list_service.listar_processos(status=status, limite=limite)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar processos via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao listar processos: {str(e)}'
                    }
            
            elif nome_funcao == "listar_processos_com_situacao_ce":
                # ✅ REFATORAÇÃO: Usar ProcessoListService em vez de lógica duplicada
                situacao_filtro = argumentos.get('situacao_filtro', '').strip().upper() or None
                limite = argumentos.get('limite', 50)
                
                try:
                    from services.processo_list_service import ProcessoListService
                    list_service = ProcessoListService(chat_service=self)
                    resultado = list_service.listar_processos_com_situacao_ce(situacao_filtro=situacao_filtro, limite=limite)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar processos com situação de CE via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao listar processos com situação de CE: {str(e)}'
                    }
            
            elif nome_funcao == "listar_processos_com_duimp":
                # ✅ REFATORAÇÃO: Usar ProcessoListService em vez de lógica duplicada
                limite = argumentos.get('limite', 50)
                
                try:
                    from services.processo_list_service import ProcessoListService
                    list_service = ProcessoListService(chat_service=self)
                    resultado = list_service.listar_processos_com_duimp(limite=limite)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar processos com DUIMP via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao listar processos com DUIMP: {str(e)}'
                    }
            
            elif nome_funcao == "verificar_duimp_registrada":
                # ✅ REFATORAÇÃO: Usar DuimpService em vez de lógica duplicada
                processo_ref = argumentos.get('processo_referencia', '')
                
                if not processo_ref:
                    return {'erro': 'processo_referencia é obrigatório'}
                
                try:
                    from services.duimp_service import DuimpService
                    duimp_service = DuimpService(chat_service=self)
                    resultado = duimp_service.verificar_duimp_registrada(processo_ref)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao verificar DUIMP registrada via DuimpService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao verificar DUIMP registrada: {str(e)}'
                    }
            
            elif nome_funcao == "listar_processos_por_categoria":
                # ✅ MIGRADO: Usar ProcessoListService
                from services.processo_list_service import ProcessoListService
                
                categoria = argumentos.get('categoria', '').strip().upper()
                limite = argumentos.get('limite', 200)
                
                try:
                    processo_list_service = ProcessoListService(chat_service=self)
                    resultado = processo_list_service.listar_processos_por_categoria(
                        categoria=categoria,
                        limite=limite,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar processos por categoria via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro ao buscar processos da categoria {categoria}: {str(e)}'
                    }
            
            elif nome_funcao == "listar_processos_por_eta":
                # ✅ MIGRADO: Usar ProcessoListService
                from services.processo_list_service import ProcessoListService
                
                filtro_data = argumentos.get('filtro_data', 'semana')
                data_especifica = argumentos.get('data_especifica')
                categoria = argumentos.get('categoria')
                limite = argumentos.get('limite', 200)
                
                try:
                    processo_list_service = ProcessoListService(chat_service=self)
                    resultado = processo_list_service.listar_processos_por_eta(
                        filtro_data=filtro_data,
                        data_especifica=data_especifica,
                        categoria=categoria,
                        limite=limite,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar processos por ETA via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_BUSCA',
                        'mensagem': f'Erro ao buscar processos por ETA: {str(e)}'
                    }
            
            elif nome_funcao == "listar_processos_por_situacao":
                # ✅ MIGRADO: Usar ProcessoListService
                from services.processo_list_service import ProcessoListService
                
                categoria = argumentos.get('categoria', '').strip().upper()
                situacao = argumentos.get('situacao', '').strip().lower()
                limite = argumentos.get('limite', 200)
                
                try:
                    processo_list_service = ProcessoListService(chat_service=self)
                    resultado = processo_list_service.listar_processos_por_situacao(
                        categoria=categoria,
                        situacao=situacao,
                        limite=limite,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar processos por situação via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_BUSCA',
                        'mensagem': f'Erro ao buscar processos {categoria} com situação {situacao}: {str(e)}'
                    }
            
            elif nome_funcao == "listar_processos_com_pendencias":
                # ✅ MIGRADO: Usar ProcessoListService
                from services.processo_list_service import ProcessoListService
                
                categoria = argumentos.get('categoria', '').strip().upper()
                limite = argumentos.get('limite', 200)
                
                try:
                    processo_list_service = ProcessoListService(chat_service=self)
                    resultado = processo_list_service.listar_processos_com_pendencias(
                        categoria=categoria,
                        limite=limite,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar processos com pendências via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_BUSCA',
                        'mensagem': f'Erro ao buscar processos {categoria} com pendências: {str(e)}'
                    }
            
            elif nome_funcao == "obter_valores_processo":
                # ✅ REFATORAÇÃO: Usar DocumentoService em vez de lógica duplicada
                processo_ref = argumentos.get('processo_referencia', '').strip()
                tipo_valor = argumentos.get('tipo_valor', 'todos').strip().lower()
                
                try:
                    from services.documento_service import DocumentoService
                    documento_service = DocumentoService(chat_service=self)
                    resultado = documento_service.obter_valores_processo(processo_ref, tipo_valor)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao obter valores do processo via DocumentoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao obter valores do processo: {str(e)}'
                    }
            
            elif nome_funcao == "obter_valores_ce":
                # ✅ REFATORAÇÃO: Usar DocumentoService em vez de lógica duplicada
                numero_ce = argumentos.get('numero_ce', '').strip()
                tipo_valor = argumentos.get('tipo_valor', 'todos').strip().lower()
                
                try:
                    from services.documento_service import DocumentoService
                    documento_service = DocumentoService(chat_service=self)
                    resultado = documento_service.obter_valores_ce(numero_ce, tipo_valor)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao obter valores do CE via DocumentoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao obter valores do CE: {str(e)}'
                    }
            
            elif nome_funcao == "obter_dados_di":
                # ✅ REFATORAÇÃO: Usar DocumentoService em vez de lógica duplicada
                numero_di = argumentos.get('numero_di', '').strip()
                
                try:
                    from services.documento_service import DocumentoService
                    documento_service = DocumentoService(chat_service=self)
                    resultado = documento_service.obter_dados_di(numero_di)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao obter dados da DI via DocumentoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao obter dados da DI: {str(e)}'
                    }
            
            elif nome_funcao == "obter_dados_duimp":
                # ✅ REFATORAÇÃO: Usar DocumentoService em vez de lógica duplicada
                numero_duimp_raw = argumentos.get('numero_duimp', '').strip()
                versao_duimp_param = argumentos.get('versao_duimp', '').strip() if argumentos.get('versao_duimp') else None
                
                try:
                    from services.documento_service import DocumentoService
                    documento_service = DocumentoService(chat_service=self)
                    resultado = documento_service.obter_dados_duimp(numero_duimp_raw, versao_duimp_param)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao obter dados da DUIMP via DocumentoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao obter dados da DUIMP: {str(e)}'
                    }
            
            elif nome_funcao == "listar_todos_processos_por_situacao":
                # ✅ MIGRADO: Usar ProcessoListService
                from services.processo_list_service import ProcessoListService
                
                situacao = argumentos.get('situacao', '').strip().lower() or None
                filtro_pendencias = argumentos.get('filtro_pendencias', False)
                filtro_bloqueio = argumentos.get('filtro_bloqueio', False)
                filtro_data_desembaraco = argumentos.get('filtro_data_desembaraco')
                limite = argumentos.get('limite', 500)
                
                try:
                    processo_list_service = ProcessoListService(chat_service=self)
                    resultado = processo_list_service.listar_todos_processos_por_situacao(
                        situacao=situacao,
                        filtro_pendencias=filtro_pendencias,
                        filtro_bloqueio=filtro_bloqueio,
                        filtro_data_desembaraco=filtro_data_desembaraco,
                        limite=limite,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar todos os processos por situação via ProcessoListService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_BUSCA',
                        'mensagem': f'Erro ao buscar processos: {str(e)}'
                    }
            
            elif nome_funcao == "verificar_atualizacao_ce":
                # ✅ MIGRADO: Usar ConsultaService
                from services.consulta_service import ConsultaService
                
                numero_ce = argumentos.get('numero_ce', '').strip()
                
                if not numero_ce:
                    return {
                        'sucesso': False,
                        'erro': 'PARAMETRO_OBRIGATORIO',
                        'mensagem': 'numero_ce é obrigatório'
                    }
                
                try:
                    consulta_service = ConsultaService(chat_service=self)
                    resultado = consulta_service.verificar_atualizacao_ce(numero_ce)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao verificar atualização do CE via ConsultaService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'resposta': f"❌ **Erro ao verificar atualização do CE {numero_ce}:** {str(e)}"
                    }
            
            elif nome_funcao == "consultar_ce_maritimo":
                # ✅ MIGRADO: Usar ConsultaService
                from services.consulta_service import ConsultaService
                
                numero_ce = argumentos.get('numero_ce', '').strip()
                processo_ref = argumentos.get('processo_referencia', '').strip()
                usar_cache_apenas = argumentos.get('usar_cache_apenas', False)
                forcar_consulta_api = argumentos.get('forcar_consulta_api', False)
                mensagem_original_param = mensagem_original  # Passar mensagem original se disponível
                
                try:
                    consulta_service = ConsultaService(chat_service=self)
                    resultado = consulta_service.consultar_ce_maritimo(
                        numero_ce=numero_ce if numero_ce else None,
                        processo_referencia=processo_ref if processo_ref else None,
                        usar_cache_apenas=usar_cache_apenas,
                        forcar_consulta_api=forcar_consulta_api,
                        mensagem_original=mensagem_original_param
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao consultar CE via ConsultaService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'resposta': f"❌ **Erro ao consultar CE:** {str(e)}"
                    }
            
            elif nome_funcao == "desvincular_documento_processo":
                # ✅ REFATORAÇÃO: Usar VinculacaoService em vez de lógica duplicada
                processo_ref = argumentos.get('processo_referencia', '').strip()
                tipo_doc = argumentos.get('tipo_documento', '').strip().upper()
                numero_doc = argumentos.get('numero_documento', '').strip()
                
                try:
                    from services.vinculacao_service import VinculacaoService
                    vinculacao_service = VinculacaoService(chat_service=self)
                    resultado = vinculacao_service.desvincular_documento(processo_ref, tipo_doc, numero_doc if numero_doc else None)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao desvincular documento via VinculacaoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao desvincular documento: {str(e)}'
                    }
            
            elif nome_funcao == "vincular_processo_ce":
                # ✅ REFATORAÇÃO: Usar VinculacaoService em vez de lógica duplicada
                numero_ce = argumentos.get('numero_ce', '').strip()
                processo_ref = argumentos.get('processo_referencia', '').strip()
                
                try:
                    from services.vinculacao_service import VinculacaoService
                    vinculacao_service = VinculacaoService(chat_service=self)
                    resultado = vinculacao_service.vincular_ce(numero_ce, processo_ref)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao vincular CE via VinculacaoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao vincular CE: {str(e)}'
                    }
            
            elif nome_funcao == "vincular_processo_cct":
                # ✅ REFATORAÇÃO: Usar VinculacaoService em vez de lógica duplicada
                numero_cct = argumentos.get('numero_cct', '').strip()
                processo_ref = argumentos.get('processo_referencia', '').strip()
                
                try:
                    from services.vinculacao_service import VinculacaoService
                    vinculacao_service = VinculacaoService(chat_service=self)
                    resultado = vinculacao_service.vincular_cct(numero_cct, processo_ref)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao vincular CCT via VinculacaoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao vincular CCT: {str(e)}'
                    }
            
            elif nome_funcao == "vincular_processo_di":
                # ✅ REFATORAÇÃO: Usar VinculacaoService em vez de lógica duplicada
                numero_di = argumentos.get('numero_di', '').strip()
                processo_ref = argumentos.get('processo_referencia', '').strip()
                
                try:
                    from services.vinculacao_service import VinculacaoService
                    vinculacao_service = VinculacaoService(chat_service=self)
                    resultado = vinculacao_service.vincular_di(numero_di, processo_ref)
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao vincular DI via VinculacaoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': str(e),
                        'resposta': f'❌ Erro ao vincular DI: {str(e)}'
                    }
            
            elif nome_funcao == "vincular_processo_duimp":
                # ✅ MIGRADO: Usar VinculacaoService
                from services.vinculacao_service import VinculacaoService
                
                numero_duimp_raw = argumentos.get('numero_duimp', '').strip()
                versao_duimp_param = argumentos.get('versao_duimp', '').strip() if argumentos.get('versao_duimp') else None
                processo_ref = argumentos.get('processo_referencia', '').strip()
                
                if not numero_duimp_raw:
                    return {
                        'erro': 'PARAMETRO_OBRIGATORIO',
                        'mensagem': 'numero_duimp é obrigatório'
                    }
                
                if not processo_ref:
                    return {
                        'erro': 'PARAMETRO_OBRIGATORIO',
                        'mensagem': 'processo_referencia é obrigatório'
                    }
                
                try:
                    vinculacao_service = VinculacaoService(chat_service=self)
                    resultado = vinculacao_service.vincular_processo_duimp(
                        numero_duimp_raw=numero_duimp_raw,
                        processo_referencia=processo_ref,
                        versao_duimp=versao_duimp_param
                    )
                    
                    # Manter compatibilidade com formato antigo
                    if resultado.get('sucesso'):
                        return {
                            'sucesso': True,
                            'mensagem': resultado.get('mensagem') or resultado.get('resposta'),
                            'resposta': resultado.get('resposta') or resultado.get('mensagem'),
                            'processo': resultado.get('processo'),
                            'duimp': resultado.get('duimp'),
                            'di': resultado.get('di'),
                            'versao': resultado.get('versao'),
                            'tipo': resultado.get('tipo')
                        }
                    else:
                        return {
                            'sucesso': False,
                            'erro': resultado.get('erro', 'ERRO_DESCONHECIDO'),
                            'mensagem': resultado.get('mensagem') or resultado.get('resposta', 'Erro ao vincular processo')
                        }
                        
                except Exception as e:
                    logger.error(f'Erro ao vincular processo à DUIMP/DI via VinculacaoService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro interno ao vincular processo: {str(e)}'
                    }
            
            elif nome_funcao == "consultar_processo_consolidado":
                # ✅ MIGRADO: Usar ConsultaService
                from services.consulta_service import ConsultaService
                
                processo_ref = argumentos.get('processo_referencia', '').strip()
                
                if not processo_ref:
                    return {
                        'sucesso': False,
                        'erro': 'PARAMETRO_OBRIGATORIO',
                        'mensagem': 'processo_referencia é obrigatório'
                    }
                
                try:
                    consulta_service = ConsultaService(chat_service=self)
                    resultado = consulta_service.consultar_processo_consolidado(processo_ref)
                    
                    # Manter compatibilidade com formato antigo
                    if resultado.get('sucesso'):
                        return {
                            'sucesso': True,
                            'resposta': resultado.get('resposta'),
                            'dados': resultado.get('dados'),
                            'processo': resultado.get('processo_referencia')
                        }
                    else:
                        return {
                            'sucesso': False,
                            'erro': resultado.get('erro', 'ERRO_DESCONHECIDO'),
                            'mensagem': resultado.get('mensagem') or resultado.get('resposta', 'Erro ao consultar processo consolidado')
                        }
                        
                except Exception as e:
                    logger.error(f'Erro ao consultar processo consolidado via ConsultaService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro interno ao consultar processo consolidado: {str(e)}'
                    }
            
            elif nome_funcao == "buscar_ncms_por_descricao":
                # ✅ MIGRADO: Implementação completa está no ToolExecutionService.
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        "❌ Busca de NCMs por descrição (buscar_ncms_por_descricao) foi migrada para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }
            
            elif nome_funcao == "calcular_impostos_ncm":
                # ✅ MIGRADO: Implementação completa está no ToolExecutionService.
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        "❌ Cálculo de impostos (calcular_impostos_ncm) foi migrado para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }
            
            elif nome_funcao == "sugerir_ncm_com_ia":
                # ✅ MIGRADO: Implementação completa está no ToolExecutionService.
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        "❌ Sugestão de NCM com IA (sugerir_ncm_com_ia) foi migrada para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }
            
            elif nome_funcao == "detalhar_ncm":
                # ✅ MIGRADO: Implementação completa está no ToolExecutionService.
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        "❌ Detalhamento de NCM (detalhar_ncm) foi migrado para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }
            
            elif nome_funcao == "baixar_nomenclatura_ncm":
                # ✅ MIGRADO: Implementação completa está no ToolExecutionService.
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        "❌ Baixar nomenclatura NCM (baixar_nomenclatura_ncm) foi migrado para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }
            
            elif nome_funcao == "buscar_nota_explicativa_nesh":
                # ✅ MIGRADO: Implementação completa está no ToolExecutionService.
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        "❌ Busca de NESH (buscar_nota_explicativa_nesh) foi migrada para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }
            
            elif nome_funcao == "listar_consultas_bilhetadas_pendentes":
                # ✅ MIGRADO: Usar ConsultasBilhetadasService
                from services.consultas_bilhetadas_service import ConsultasBilhetadasService
                
                status_filtro = argumentos.get('status', '').strip() or None
                limite = argumentos.get('limite', 50)
                tipo_consulta = argumentos.get('tipo_consulta', '').strip() or None
                
                try:
                    service = ConsultasBilhetadasService(chat_service=self)
                    resultado = service.listar_consultas_bilhetadas_pendentes(
                        status_filtro=status_filtro,
                        limite=limite,
                        tipo_consulta=tipo_consulta,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar consultas pendentes via ConsultasBilhetadasService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro ao listar consultas: {str(e)}'
                    }
            
            elif nome_funcao == "aprovar_consultas_bilhetadas":
                # ✅ MIGRADO: Usar ConsultasBilhetadasService
                from services.consultas_bilhetadas_service import ConsultasBilhetadasService
                
                ids_raw = argumentos.get('ids', [])
                tipo_consulta = argumentos.get('tipo_consulta', '').strip() or None
                aprovar_todas = argumentos.get('aprovar_todas', False)
                
                try:
                    service = ConsultasBilhetadasService(chat_service=self)
                    resultado = service.aprovar_consultas_bilhetadas(
                        ids_raw=ids_raw,
                        tipo_consulta=tipo_consulta,
                        aprovar_todas=aprovar_todas,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao aprovar consultas via ConsultasBilhetadasService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro ao aprovar consultas: {str(e)}'
                    }
            
            elif nome_funcao == "rejeitar_consultas_bilhetadas":
                # ✅ MIGRADO: Usar ConsultasBilhetadasService
                from services.consultas_bilhetadas_service import ConsultasBilhetadasService
                
                ids_raw = argumentos.get('ids', [])
                tipo_consulta = argumentos.get('tipo_consulta', '').strip() or None
                rejeitar_todas = argumentos.get('rejeitar_todas', False)
                motivo = argumentos.get('motivo', '').strip() or None
                
                try:
                    service = ConsultasBilhetadasService(chat_service=self)
                    resultado = service.rejeitar_consultas_bilhetadas(
                        ids_raw=ids_raw,
                        tipo_consulta=tipo_consulta,
                        rejeitar_todas=rejeitar_todas,
                        motivo=motivo,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao rejeitar consultas via ConsultasBilhetadasService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro ao rejeitar consultas: {str(e)}'
                    }
            
            elif nome_funcao == "ver_status_consultas_bilhetadas":
                consulta_id = argumentos.get('consulta_id')
                
                try:
                    from db_manager import listar_consultas_pendentes
                    from datetime import datetime
                    
                    if consulta_id:
                        # Buscar consulta específica
                        consultas = listar_consultas_pendentes(status=None, limit=10000)
                        consulta = next((c for c in consultas if c.get('id') == consulta_id), None)
                        
                        if not consulta:
                            return {
                                'sucesso': False,
                                'erro': 'CONSULTA_NAO_ENCONTRADA',
                                'resposta': f'⚠️ **Consulta #{consulta_id} não encontrada.**'
                            }
                        
                        # Formatar resposta detalhada
                        resposta = f"📋 **Consulta #{consulta_id}**\n\n"
                        resposta += f"**Tipo:** {consulta.get('tipo_consulta', 'N/A')}\n"
                        resposta += f"**Documento:** {consulta.get('numero_documento', 'N/A')}\n"
                        resposta += f"**Processo:** {consulta.get('processo_referencia', 'N/A')}\n"
                        resposta += f"**Status:** {consulta.get('status', 'N/A')}\n"
                        resposta += f"**Motivo:** {consulta.get('motivo', 'N/A')}\n"
                        
                        if consulta.get('aprovado_em'):
                            try:
                                dt = datetime.fromisoformat(consulta.get('aprovado_em').replace('Z', '+00:00'))
                                resposta += f"**Aprovada em:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                            except:
                                resposta += f"**Aprovada em:** {consulta.get('aprovado_em')}\n"
                        
                        if consulta.get('aprovado_por'):
                            resposta += f"**Aprovada por:** {consulta.get('aprovado_por')}\n"
                        
                        return {
                            'sucesso': True,
                            'resposta': resposta,
                            'consulta': consulta
                        }
                    else:
                        # Mostrar estatísticas gerais
                        from db_manager import contar_consultas_pendentes
                        contagem = contar_consultas_pendentes()
                        
                        resposta = f"📊 **Estatísticas de Consultas Bilhetadas**\n\n"
                        resposta += f"**Pendentes:** {contagem.get('pendente', 0)}\n"
                        resposta += f"**Aprovadas:** {contagem.get('aprovado', 0)}\n"
                        resposta += f"**Rejeitadas:** {contagem.get('rejeitado', 0)}\n"
                        resposta += f"**Executadas:** {contagem.get('executado', 0)}\n"
                        
                        return {
                            'sucesso': True,
                            'resposta': resposta,
                            'contagem': contagem
                        }
                except Exception as e:
                    logger.error(f'Erro ao ver status de consultas: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro ao ver status: {str(e)}'
                    }
            
            elif nome_funcao == "listar_consultas_aprovadas_nao_executadas":
                # ✅ MIGRADO: Usar ConsultasBilhetadasService
                from services.consultas_bilhetadas_service import ConsultasBilhetadasService
                
                tipo_consulta = argumentos.get('tipo_consulta', '').strip() or None
                limite = argumentos.get('limite', 50)
                
                try:
                    service = ConsultasBilhetadasService(chat_service=self)
                    resultado = service.listar_consultas_aprovadas_nao_executadas(
                        tipo_consulta=tipo_consulta,
                        limite=limite,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao listar consultas aprovadas via ConsultasBilhetadasService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro ao listar consultas aprovadas: {str(e)}'
                    }
            
            elif nome_funcao == "executar_consultas_aprovadas":
                # ✅ MIGRADO: Usar ConsultasBilhetadasService
                from services.consultas_bilhetadas_service import ConsultasBilhetadasService
                
                ids_raw = argumentos.get('ids', [])
                tipo_consulta = argumentos.get('tipo_consulta', '').strip() or None
                executar_todas = argumentos.get('executar_todas', False)
                
                try:
                    service = ConsultasBilhetadasService(chat_service=self)
                    resultado = service.executar_consultas_aprovadas(
                        ids_raw=ids_raw,
                        tipo_consulta=tipo_consulta,
                        executar_todas=executar_todas,
                        mensagem_original=mensagem_original
                    )
                    return resultado
                except Exception as e:
                    logger.error(f'Erro ao executar consultas via ConsultasBilhetadasService: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'mensagem': f'Erro ao executar consultas: {str(e)}'
                    }
            
            # ✅ NOVO: Tools de consultas analíticas e regras aprendidas
            elif nome_funcao == "executar_consulta_analitica":
                # ✅ MIGRADO: Implementação completa está no ToolExecutionService.
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        "❌ Consulta analítica (executar_consulta_analitica) foi migrada para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }

            elif nome_funcao in (
                "enviar_email",
                "enviar_relatorio_email",
                "enviar_email_personalizado",
                "melhorar_email_draft",
                "ler_emails",
                "obter_detalhes_email",
                "responder_email",
            ):
                # ✅ 19/01/2026: caminho oficial está no ToolExecutionService (handlers extraídos).
                return {
                    "sucesso": False,
                    "erro": "TOOL_MIGRADA",
                    "resposta": (
                        f"❌ Tool **{nome_funcao}** foi migrada para o ToolExecutionService. "
                        "Tente novamente (pipeline novo)."
                    ),
                }
            
            else:
                return {
                    'erro': 'FUNCAO_DESCONHECIDA',
                    'mensagem': f'Função {nome_funcao} não está implementada.'
                }
        
        except Exception as e:
            logger.error(f'Erro ao executar função {nome_funcao}: {e}')
            return {
                'erro': 'ERRO_EXECUCAO',
                'mensagem': f'Erro ao executar função: {str(e)}'
            }
    
    def _extrair_contexto_do_historico(self, mensagem: str, historico: Optional[List[Dict]] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrai contexto de processo/CE do histórico da conversa.
        Útil quando o usuário faz perguntas sem mencionar o processo explicitamente.
        
        Retorna: (processo_referencia, numero_ce)
        
        Exemplo:
        - Usuário: "consulte o CE do processo MSS.0018/25"
        - IA: [resposta com dados do CE]
        - Usuário: "tem bloqueio?"  ← Não menciona processo, mas o contexto está no histórico
        """
        if not historico:
            return None, None
        
        processo_hist = None
        numero_ce_hist = None
        
        # Verificar últimas 6 mensagens do histórico (ida e volta)
        for item in reversed(historico[-6:]):  # Últimas 6 mensagens (3 pares usuário/IA)
            item_msg = item.get('mensagem', '') or item.get('resposta', '')
            if not item_msg:
                continue
            
            # Tentar extrair processo do histórico
            if not processo_hist:
                processo_hist = self._extrair_processo_referencia(item_msg)
            
            # Tentar extrair número de CE do histórico
            # Padrão: "CE 152505190990910" ou "📦 **CE 132505329336481**" ou "consulte o CE 152505190990910"
            padrao_ce = r'(?:CE|ce)\s+(\d{10,15})'
            match_ce = re.search(padrao_ce, item_msg, re.IGNORECASE)
            if match_ce and not numero_ce_hist:
                numero_ce_hist = match_ce.group(1)
        
        return processo_hist, numero_ce_hist
    
    def _extrair_categoria_do_historico(self, mensagem: str, historico: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Extrai categoria (ALH, VDM, DMD, etc.) do histórico da conversa.
        
        ✅ REFATORADO (10/01/2026): Delegado para ContextExtractionHandler.
        Mantido como método de instância para compatibilidade com código existente.
        """
        if not hasattr(self, '_context_extraction_handler'):
            from services.handlers.context_extraction_handler import ContextExtractionHandler
            self._context_extraction_handler = ContextExtractionHandler(chat_service=self)
        
        return self._context_extraction_handler.extrair_categoria_do_historico(
            mensagem,
            historico,
            extrair_categoria_callback=self._extrair_categoria_da_mensagem
        )
    
    def _extrair_categoria_da_mensagem(self, mensagem: str) -> Optional[str]:
        """
        Extrai categoria (ALH, VDM, DMD, MSS, MV5, etc.) da mensagem.
        Aceita categorias de 2-4 letras, podendo incluir números (ex: MV5).
        """
        mensagem_upper = mensagem.upper()
        mensagem_lower = mensagem.lower()

        # 1) Perguntas de NCM / classificação fiscal → nunca tratar nada como categoria de processo
        if 'ncm' in mensagem_lower or re.search(r'\bclassifica[cç][aã]o\s+fiscal\b', mensagem_lower):
            return None

        # 2) Perguntas meta / ajuda / acesso a BD → não é categoria
        if any(p in mensagem_lower for p in [
            'vc tem acesso ao bd',
            'vc tem acesso ao banco',
            'acesso ao bd',
            'acesso ao banco',
            'o que voce consegue fazer',
            'o que você consegue fazer',
            'como usar',
            'help',
            'ajuda',
        ]):
            return None
        
        # ✅ CORREÇÃO: Categorias válidas (aceitar 2-4 letras + números opcionais)
        # Palavras comuns a IGNORAR (não são categorias)
        # ✅ CRÍTICO: Incluir palavras temporais para evitar falsos positivos (ex: "VEM" de "semana que vem")
        palavras_ignorar = {'DOS', 'DAS', 'DO', 'DA', 'ESTAO', 'ESTÃO', 'COM', 'SÃO', 'SAO', 'TEM', 'TÊM', 'POR', 'QUE', 'QUAL', 'COMO', 'EST', 'PAR', 'UMA', 'UNS', 'TODOS', 'TODAS', 'TODO', 'TODA', 'OS', 'AS', 
                            # ✅ Palavras temporais (CRÍTICO: incluir variações de "esta/essa semana")
                            'VEM', 'VÊM', 'SEMANA', 'PROXIMA', 'PRÓXIMA', 'MES', 'MÊS', 'DIA', 'DIAS', 'HOJE', 'AMANHA', 'AMANHÃ', 'SAB', 'DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX',
                            'ESSA', 'ESTA', 'NESSA', 'NESTA',  # ✅ CRÍTICO: Ignorar "essa semana", "esta semana", "nessa semana", "nesta semana"
                            # ✅ Verbos temporais (não são categorias)
                            'VAO', 'VÃO', 'IRÃO', 'IRAO', 'CHEGAM', 'CHEGA', 'CHEGAR', 'CHEGARA', 'CHEGARAM',
                            # ✅ Preposições/ações (não são categorias)
                            'PRA', 'PARA',
                            # ✅ NCM (Nomenclatura Comum do Mercosul) - não é categoria de processo
                            'NCM',
                            # ✅ CRÍTICO: Ignorar "DO" e "DA" que aparecem em "duimp do" ou "duimp da"
                            'DUIMP',
                            # Conversas genéricas / palavras comuns que não são categoria
                            'VC', 'VOCE', 'VOCÊ', 'CONSEGUE', 'CONSEGUIR', 'ACHAR', 'ENCONTRAR', 'VER', 'FAZER', 'FAZ',
                            'EM', 'ANO', 'ANOS', 'TOP', 'MAIS', 'MENOS', 'CLIENTES', 'CLIENTE',
                            'FORNECEDORES', 'FORNECEDOR', 'VALOR', 'CIF', 'IMPORTADO', 'ATRASO', 'ATRASOS'
                            }  # ✅ Também ignorar DUIMP se aparecer isolado
        # 0. Padrão: "o que temos de mv5?" ou "o que temos de vdm?" (com "de" antes da categoria)
        padrao_0 = r'(?:o\s+que|quais|mostre|liste)\s+(?:temos|tem|têm|há|ha)\s+de\s+([a-z]{2,4}\d*)\b'
        match_0 = re.search(padrao_0, mensagem_lower)
        if match_0:
            cat = match_0.group(1).upper()
            if cat not in palavras_ignorar and (len(cat) >= 2 and len(cat) <= 5):
                return cat
        
        # 1. Padrão: "como estao os vdm?" ou "como estão os mv5?" (sem mencionar "processos")
        padrao_1 = r'(?:como|quais|mostre|liste|como\s+estao|como\s+estão)\s+(?:os|as|os\s+processos|as\s+processos)?\s*([a-z]{2,4}\d*)\b'
        match_1 = re.search(padrao_1, mensagem_lower)
        if match_1:
            cat = match_1.group(1).upper()
            if cat not in palavras_ignorar and (len(cat) >= 2 and len(cat) <= 5):
                return cat
        
        # 2. Padrão: "processos VDM", "processos MV5", "processos de MV5" ou "categoria MV5"
        padrao_2 = r'(?:processos?|categoria)\s+(?:de\s+)?([a-z]{2,4}\d*)\b'
        match_2 = re.search(padrao_2, mensagem_lower)
        if match_2:
            cat = match_2.group(1).upper()
            if cat not in palavras_ignorar and (len(cat) >= 2 and len(cat) <= 5):
                return cat
        
        # 3. Padrão: "os ALH", "as MV5" (isolado)
        padrao_3 = r'(?:^|\s)(?:os|as)\s+([a-z]{2,4}\d*)\b'
        match_3 = re.search(padrao_3, mensagem_lower)
        if match_3:
            cat = match_3.group(1).upper()
            if cat not in palavras_ignorar and (len(cat) >= 2 and len(cat) <= 5):
                return cat
        
        # 4. Padrão: "de [categoria]" (ex: "o que temos de mv5 pra hoje?")
        padrao_4_de = r'\bde\s+([a-z]{2,4}\d*)\b'
        match_4_de = re.search(padrao_4_de, mensagem_lower)
        if match_4_de:
            cat = match_4_de.group(1).upper()
            if cat not in palavras_ignorar and (len(cat) >= 2 and len(cat) <= 5):
                return cat
        
        # 4. Padrão: Qualquer categoria isolada (2-4 letras + números opcionais) - fallback
        padrao_4 = r'\b([A-Z]{2,4}\d*)\b'
        matches = re.findall(padrao_4, mensagem_upper)
        # Tentar validar contra categorias conhecidas no banco, se possível
        try:
            from db_manager import verificar_categoria_processo
        except ImportError:
            verificar_categoria_processo = None

        for match in matches:
            if match in palavras_ignorar or not (2 <= len(match) <= 5):
                continue

            if verificar_categoria_processo:
                try:
                    if verificar_categoria_processo(match):
                        return match
                except Exception:
                    # Se der erro no DB, não assumimos nada
                    continue
        # Se nada foi aceito, não há categoria
        return None
    
    def _eh_pergunta_generica(self, mensagem: str) -> bool:
        """
        Identifica se a mensagem é uma pergunta genérica que deve limpar o contexto anterior.
        
        ✅ REFATORADO (10/01/2026): Delegado para QuestionClassifier.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.question_classifier import QuestionClassifier
        # Passar callback para extrair categoria usando método da instância
        return QuestionClassifier.eh_pergunta_generica(
            mensagem, 
            extrair_categoria_callback=self._extrair_categoria_da_mensagem
        )
    
    def _obter_email_para_enviar(self, dados_email_para_enviar: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Obtém dados do email para envio, priorizando banco de dados quando tem draft_id.
        
        Regra: Se tem draft_id → banco é fonte da verdade
               Se não tem draft_id → usa memória
        
        Args:
            dados_email_para_enviar: Dados do email da memória
        
        Returns:
            Dict com dados do email para envio, ou None se não encontrado
        """
        if not dados_email_para_enviar:
            return None
        
        draft_id = dados_email_para_enviar.get('draft_id')
        if draft_id:
            try:
                from services.email_draft_service import get_email_draft_service
                draft_service = get_email_draft_service()
                draft = draft_service.obter_draft(draft_id)
                
                if draft:
                    # ✅ Banco é fonte da verdade quando tem draft_id
                    logger.info(f'✅ [OBTER_EMAIL] Usando draft {draft_id} (revision {draft.revision}) do banco como fonte da verdade')
                    
                    # Validar consistência (opcional, mas útil para debug)
                    revision_memoria = dados_email_para_enviar.get('revision')
                    if revision_memoria and revision_memoria != draft.revision:
                        logger.warning(f'⚠️ [OBTER_EMAIL] Inconsistência detectada: memória tem revision {revision_memoria}, banco tem revision {draft.revision}. Usando banco (fonte da verdade).')
                    
                    return {
                        'destinatarios': draft.destinatarios,
                        'cc': draft.cc or [],
                        'bcc': draft.bcc or [],
                        'assunto': draft.assunto,
                        'conteudo': draft.conteudo,
                        'funcao': draft.funcao_email,
                        'draft_id': draft_id,
                        'revision': draft.revision
                    }
                else:
                    logger.warning(f'⚠️ [OBTER_EMAIL] Draft {draft_id} não encontrado no banco, usando memória como fallback')
                    # Fallback: usar memória se draft não encontrado
                    return dados_email_para_enviar
            except Exception as e:
                logger.warning(f'⚠️ [OBTER_EMAIL] Erro ao obter draft {draft_id} do banco: {e}. Usando memória como fallback.')
                # Fallback: usar memória se erro ao buscar draft
                return dados_email_para_enviar
        else:
            # Sem draft_id: usar memória
            logger.debug(f'✅ [OBTER_EMAIL] Sem draft_id, usando memória como fonte da verdade')
            return dados_email_para_enviar
    
    def _identificar_se_precisa_contexto(self, mensagem: str) -> bool:
        """
        Identifica se a mensagem precisa de contexto de processo/CE mas não o menciona.
        
        ✅ REFATORADO (10/01/2026): Delegado para QuestionClassifier.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.question_classifier import QuestionClassifier
        # Passar callback para extrair processo usando método da instância
        return QuestionClassifier.identificar_se_precisa_contexto(
            mensagem,
            extrair_processo_callback=self._extrair_processo_referencia
        )

    def _detectar_comando_interface(self, mensagem: str) -> Optional[Dict[str, Any]]:
        """
        Detecta comandos de interface (ex: "maike menu") antes de qualquer processamento.

        Returns:
            Dict com comando_interface se detectado; caso contrário, None.
        """
        try:
            from services.message_intent_service import MessageIntentService

            intent_service = MessageIntentService(self)
            return intent_service.detectar_comando_interface(mensagem)
        except Exception as e:
            logger.debug(f"⚠️ Erro ao detectar comando de interface (continuando normalmente): {e}")
            return None

    def _selecionar_modelo_automatico(self, mensagem: str, model: Optional[str]) -> Optional[str]:
        """
        Seleção automática de modelo (operacional x analítico x conhecimento geral).
        Mantém o comportamento atual, apenas encapsula o bloco para reduzir complexidade do método.
        """
        if model is not None:
            return model
        try:
            # ✅ Estratégia híbrida: detectar se é pergunta de conhecimento geral
            if self._eh_pergunta_conhecimento_geral(mensagem):
                selected = AI_MODEL_CONHECIMENTO_GERAL
                logger.info(f"🧠 [MODEL_ROUTER] Pergunta de conhecimento geral detectada - usando {selected}")
                return selected
            if self._eh_pergunta_analitica(mensagem):
                return AI_MODEL_ANALITICO
            return AI_MODEL_DEFAULT
        except Exception as e:
            # Se algo der errado aqui, não quebra o fluxo – deixa AIService escolher o default
            import logging as _logging
            _logging.getLogger(__name__).warning(f"[MODEL_ROUTER] Erro ao detectar tipo de pergunta: {e}")
            return model

    def _obter_estado_email_pendente(
        self,
        historico: List[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Obtém estado de "email em preview" pendente.

        Prioridade: estado em memória (instância) → último `_resultado_interno` do histórico.
        Se encontrar no histórico, também sincroniza `self.ultima_resposta_aguardando_email`.
        """
        ultima_resposta_aguardando_email = False
        dados_email_para_enviar = None

        # 1) Memória (por sessão) (fonte mais confiável)
        dados_memoria = self._get_email_pendente(session_id) if hasattr(self, "_get_email_pendente") else getattr(self, 'ultima_resposta_aguardando_email', None)
        if dados_memoria:
            ultima_resposta_aguardando_email = True
            dados_email_para_enviar = dados_memoria
            return ultima_resposta_aguardando_email, dados_email_para_enviar

        # 2) Histórico (última interação)
        if historico:
            ultimo_resultado = historico[-1].get('_resultado_interno', {})
            if isinstance(ultimo_resultado, dict) and 'ultima_resposta_aguardando_email' in ultimo_resultado:
                ultima_resposta_aguardando_email = True
                dados_email_para_enviar = ultimo_resultado.get('ultima_resposta_aguardando_email')
                if dados_email_para_enviar:
                    # sincronizar estado em memória para próximos passos
                    try:
                        self._set_email_pendente(session_id, dados_email_para_enviar)
                    except Exception:
                        if hasattr(self, 'ultima_resposta_aguardando_email'):
                            self.ultima_resposta_aguardando_email = dados_email_para_enviar
                return ultima_resposta_aguardando_email, dados_email_para_enviar

        return ultima_resposta_aguardando_email, dados_email_para_enviar

    def _processar_confirmacao_email_antes_precheck(
        self,
        mensagem: str,
        historico: List[Dict[str, Any]],
        session_id: Optional[str],
        eh_pedido_melhorar_email: bool,
        estado_email_pendente: Optional[Tuple[bool, Optional[Dict[str, Any]]]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], bool, Optional[Dict[str, Any]]]:
        """
        Processa confirmação de email ANTES de qualquer precheck/IA.

        Returns:
            - resultado (dict) se executou confirmação e deve retornar imediatamente; caso contrário None
            - ultima_resposta_aguardando_email (bool)
            - dados_email_para_enviar (dict|None)
        """
        if estado_email_pendente is not None:
            ultima_resposta_aguardando_email, dados_email_para_enviar = estado_email_pendente
        else:
            ultima_resposta_aguardando_email, dados_email_para_enviar = self._obter_estado_email_pendente(historico, session_id=session_id)
        if ultima_resposta_aguardando_email and dados_email_para_enviar:
            draft_id_atual = dados_email_para_enviar.get('draft_id') if dados_email_para_enviar else None
            logger.info(
                f'✅✅✅ [PRIMEIRO] Preview de email detectado - aguardando confirmação. '
                f'Função: {dados_email_para_enviar.get("funcao", "N/A") if dados_email_para_enviar else "N/A"}, '
                f'draft_id: {draft_id_atual}'
            )

        # 2) Se detectou preview e mensagem é confirmação, executar ANTES de tudo
        if ultima_resposta_aguardando_email and dados_email_para_enviar and not eh_pedido_melhorar_email:
            # ✅ NOVO (09/01/2026): Usar ConfirmationHandler para detectar confirmação
            if self.confirmation_handler:
                eh_confirmacao_email = self.confirmation_handler.detectar_confirmacao_email(
                    mensagem=mensagem,
                    dados_email_para_enviar=dados_email_para_enviar,
                )
            else:
                mensagem_lower_check = mensagem.lower().strip()
                confirmacoes_email = ['sim', 'enviar', 'pode enviar', 'envia', 'manda', 'mandar', 'confirma', 'confirmar', 'ok', 'pode']
                padroes_confirmacao = [
                    'envie esse email', 'mande esse email', 'envia esse email', 'manda esse email',
                    'envie esse', 'mande esse', 'envia esse', 'manda esse',
                    'envie o email', 'mande o email', 'envia o email', 'manda o email',
                    'envie o', 'mande o', 'envia o', 'manda o'
                ]
                eh_confirmacao_email = (
                    any(conf in mensagem_lower_check for conf in confirmacoes_email)
                    or any(padrao in mensagem_lower_check for padrao in padroes_confirmacao)
                    or mensagem_lower_check.strip() in ['sim', 'enviar', 'ok']
                )

            if eh_confirmacao_email:
                if self.confirmation_handler:
                    try:
                        resultado = self.confirmation_handler.processar_confirmacao_email(
                            mensagem=mensagem,
                            dados_email_para_enviar=dados_email_para_enviar,
                            session_id=session_id,
                        )
                        self.ultima_resposta_aguardando_email = None
                        return resultado, ultima_resposta_aguardando_email, dados_email_para_enviar
                    except Exception as e:
                        logger.error(f'❌ Erro no ConfirmationHandler: {e}', exc_info=True)
                        # Fallback para lógica antiga se handler falhar
                        pass

                # Fallback: manter comportamento antigo (envio via tool)
                funcao_email = dados_email_para_enviar.get('funcao', 'enviar_email_personalizado')
                logger.info(f'✅✅✅ [PRIMEIRO] Confirmação de email detectada - enviando email via {funcao_email} (fallback)')
                try:
                    if funcao_email == 'enviar_relatorio_email':
                        argumentos_relatorio = dados_email_para_enviar.get('argumentos', {})
                        argumentos_relatorio['confirmar_envio'] = True
                        resultado_email = self._executar_funcao_tool('enviar_relatorio_email', argumentos_relatorio, mensagem_original=mensagem)
                    elif funcao_email == 'enviar_email':
                        resultado_email = self._executar_funcao_tool('enviar_email', {
                            'destinatario': dados_email_para_enviar.get('destinatario'),
                            'assunto': dados_email_para_enviar.get('assunto'),
                            'corpo': dados_email_para_enviar.get('corpo'),
                            'confirmar_envio': True
                        }, mensagem_original=mensagem)
                    else:
                        dados_email_final = self._obter_email_para_enviar(dados_email_para_enviar)
                        if not dados_email_final:
                            return {
                                'sucesso': False,
                                'erro': 'DADOS_EMAIL_NAO_ENCONTRADOS',
                                'resposta': '❌ Não foi possível encontrar os dados do email para envio.'
                            }, ultima_resposta_aguardando_email, dados_email_para_enviar

                        resultado_email = self._executar_funcao_tool('enviar_email_personalizado', {
                            'destinatarios': dados_email_final.get('destinatarios', []),
                            'assunto': dados_email_final.get('assunto'),
                            'conteudo': dados_email_final.get('conteudo'),
                            'cc': dados_email_final.get('cc', []),
                            'bcc': dados_email_final.get('bcc', []),
                            'confirmar_envio': True
                        }, mensagem_original=mensagem)

                    self._clear_email_pendente(session_id)
                    if resultado_email and resultado_email.get('sucesso'):
                        return {
                            'sucesso': True,
                            'resposta': resultado_email.get('resposta', '✅ Email enviado com sucesso!'),
                            'tool_calling': {'name': funcao_email, 'arguments': {'confirmar_envio': True}},
                            'email_enviado': True
                        }, ultima_resposta_aguardando_email, dados_email_para_enviar

                    return {
                        'sucesso': False,
                        'resposta': resultado_email.get('resposta', '❌ Erro ao enviar email') if resultado_email else '❌ Erro ao enviar email',
                        'erro': resultado_email.get('erro') if resultado_email else 'ERRO_ENVIO_EMAIL'
                    }, ultima_resposta_aguardando_email, dados_email_para_enviar
                except Exception as e:
                    logger.error(f'❌ Erro ao enviar email após confirmação: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'resposta': f'❌ Erro ao enviar email: {str(e)}',
                        'erro': 'ERRO_ENVIO_EMAIL'
                    }, ultima_resposta_aguardando_email, dados_email_para_enviar

        return None, ultima_resposta_aguardando_email, dados_email_para_enviar

    def _detectar_pedido_melhorar_email_preview(
        self,
        mensagem: str,
        ultima_resposta_aguardando_email: bool,
        dados_email_para_enviar: Optional[Dict[str, Any]],
        eh_correcao_email_destinatario: bool,
        *,
        log_prefix: str = "",
    ) -> bool:
        """
        Detecta se o usuário está pedindo para melhorar/elaborar um email que está em preview.

        Quando True, salva contexto em `self._email_para_melhorar_contexto` para uso no prompt.
        """
        if not ultima_resposta_aguardando_email or not dados_email_para_enviar or eh_correcao_email_destinatario:
            return False

        mensagem_lower_check = mensagem.lower().strip()
        pedidos_melhorar = [
            'elaborar', 'elabore', 'melhorar', 'melhore', 'refinar', 'refine',
            'reescrever', 'reescreva', 'reescreva melhor', 'melhore esse email', 'melhore esse eamail',  # ✅ Typos comuns
            'elabore melhor', 'elabora melhor', 'melhore o email', 'melhore esse',
            'assine', 'assinar', 'mude a assinatura', 'troque a assinatura',
            'mais', 'mais elaborado', 'mais carinhoso', 'mais formal', 'mais didático'
        ]

        eh_pedido_melhorar_email = (
            any(pedido in mensagem_lower_check for pedido in pedidos_melhorar)
            or bool(re.search(r'melhore\s+(?:o|esse|este)\s+(?:e?mail|e?maile?|correio)', mensagem_lower_check, re.IGNORECASE))
            or bool(re.search(r'melhore\s+esse\s+e?a?m?a?i?l', mensagem_lower_check, re.IGNORECASE))
        )

        if eh_pedido_melhorar_email:
            logger.info(f'✅✅✅ {log_prefix}[MELHORAR EMAIL] Usuário pediu para melhorar email em preview: "{mensagem}"')
            self._email_para_melhorar_contexto = dados_email_para_enviar.copy()

        return eh_pedido_melhorar_email

    def _processar_confirmacao_duimp_antes_precheck(
        self,
        mensagem: str,
        historico: List[Dict[str, Any]],
        session_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Processa confirmação de DUIMP ANTES de qualquer outro processamento.

        Mantém o comportamento atual do `processar_mensagem`, apenas encapsula para reduzir complexidade.
        """
        # 0) Verificar se há estado pendente na instância (mais confiável do que depender do historico)
        try:
            # 0.a) Se não há estado em memória, tentar recuperar do contexto persistente
            if (not self._get_duimp_pendente(session_id)) and session_id:
                try:
                    from services.context_service import buscar_contexto_sessao
                    ctxs = buscar_contexto_sessao(session_id=session_id, tipo_contexto='duimp_aguardando_confirmacao')
                    if ctxs:
                        ctx0 = ctxs[0]
                        proc_ctx = ctx0.get('valor', '')
                        amb_ctx = (ctx0.get('dados') or {}).get('ambiente', 'validacao')
                        self._set_duimp_pendente(session_id, {
                            'processo_referencia': proc_ctx,
                            'ambiente': amb_ctx
                        })
                        logger.info(f'🧭 [DUIMP] Estado recuperado do contexto persistente: processo={proc_ctx}, ambiente={amb_ctx}')
                except Exception as _e_ctx_load:
                    logger.debug(f'[DUIMP] Falha ao recuperar estado do contexto: {_e_ctx_load}')

            duimp_state = self._get_duimp_pendente(session_id)
            
            # ✅ CRÍTICO (21/01/2026): Verificar se há realmente um pending intent de DUIMP
            # Não processar apenas baseado em estado em memória (pode estar desatualizado)
            tem_pending_intent_duimp = False
            if session_id:
                try:
                    from services.pending_intent_service import get_pending_intent_service
                    service = get_pending_intent_service()
                    if service:
                        pending_duimp = service.buscar_pending_intent(session_id, action_type='create_duimp')
                        tem_pending_intent_duimp = bool(pending_duimp and pending_duimp.get('status') == 'pending')
                        if tem_pending_intent_duimp:
                            logger.info(f'✅ [DUIMP] Pending intent de DUIMP encontrado: {pending_duimp.get("intent_id")}')
                        else:
                            logger.debug(f'🔍 [DUIMP] Nenhum pending intent de DUIMP encontrado (ou não está pending)')
                except Exception as e:
                    logger.debug(f'[DUIMP] Erro ao verificar pending intent: {e}')
            
            # ✅ Só processar se houver estado pendente E pending intent válido
            if duimp_state and tem_pending_intent_duimp:
                mensagem_lower_check = mensagem.lower().strip()
                logger.info(f'🔍 [DUIMP] Estado pendente + pending intent encontrados: processo={duimp_state.get("processo_referencia")}, mensagem="{mensagem_lower_check}"')
                eh_comando_novo_duimp_state = bool(
                    re.search(r'registr[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check) or
                    re.search(r'cri[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check) or
                    re.search(r'ger[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check) or
                    re.search(r'fazer\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check)
                )
                if not eh_comando_novo_duimp_state:
                    # ✅ CORREÇÃO: Detecção determinística (exata match, não substring)
                    confirmacoes_duimp_exatas = {'sim', 'pode prosseguir', 'prosseguir', 'confirmar', 'confirma', 'pode criar', 'pode registrar', 'confirmo', 'ok', 'criar', 'pode'}
                    eh_confirmacao_duimp_state = mensagem_lower_check in confirmacoes_duimp_exatas
                    logger.info(f'🔍 [DUIMP] Confirmação detectada: {eh_confirmacao_duimp_state}, comando_novo: {eh_comando_novo_duimp_state}')
                else:
                    eh_confirmacao_duimp_state = False
                    logger.info('🔍 [DUIMP] Comando novo detectado, não é confirmação')

                if eh_confirmacao_duimp_state:
                    processo_msg = self._extrair_processo_referencia(mensagem)
                    processo_para_criar_duimp_state = processo_msg or duimp_state.get('processo_referencia')
                    ambiente_para_criar_duimp_state = duimp_state.get('ambiente', 'validacao')
                    logger.info(f'✅✅✅ [DUIMP] Confirmação detectada via estado pendente - criando DUIMP do processo {processo_para_criar_duimp_state} (ambiente={ambiente_para_criar_duimp_state})')
                    try:
                        from services.agents.duimp_agent import DuimpAgent
                        duimp_agent = DuimpAgent()
                        resultado = duimp_agent._criar_duimp({
                            'processo_referencia': processo_para_criar_duimp_state,
                            'ambiente': ambiente_para_criar_duimp_state,
                            'confirmar': True
                        }, context={'chat_service': self})

                        # Limpar estado após uso (sucesso ou falha)
                        self._clear_duimp_pendente(session_id)
                        # Limpar também do contexto persistente
                        try:
                            if session_id:
                                from services.context_service import limpar_contexto_sessao
                                limpar_contexto_sessao(session_id=session_id, tipo_contexto='duimp_aguardando_confirmacao')
                                logger.info('[DUIMP] Contexto persistente limpo (duimp_aguardando_confirmacao)')
                        except Exception as _e_ctx_clear:
                            logger.debug(f'[DUIMP] Falha ao limpar contexto persistente: {_e_ctx_clear}')

                        if resultado.get('sucesso'):
                            return {
                                'sucesso': True,
                                'resposta': resultado.get('resposta', 'DUIMP criada com sucesso'),
                                'tool_calling': {
                                    'name': 'criar_duimp',
                                    'arguments': {
                                        'processo_referencia': processo_para_criar_duimp_state,
                                        'ambiente': ambiente_para_criar_duimp_state,
                                        'confirmar': True
                                    }
                                },
                                'numero_duimp': resultado.get('numero'),
                                'versao_duimp': resultado.get('versao')
                            }
                        return {
                            'sucesso': False,
                            'resposta': resultado.get('resposta', 'Erro ao criar DUIMP'),
                            'erro': resultado.get('erro')
                        }
                    except Exception as e:
                        logger.error(f'❌ Erro ao criar DUIMP após confirmação (estado): {e}', exc_info=True)
                        # Limpar estado mesmo em erro, para não ficar travado
                        self._clear_duimp_pendente(session_id)
                        try:
                            if session_id:
                                from services.context_service import limpar_contexto_sessao
                                limpar_contexto_sessao(session_id=session_id, tipo_contexto='duimp_aguardando_confirmacao')
                        except Exception:
                            pass
                        return {
                            'sucesso': False,
                            'resposta': f'❌ Erro ao criar DUIMP: {str(e)}',
                            'erro': 'ERRO_CRIACAO_DUIMP'
                        }
        except Exception as _e:
            logger.debug(f'[DUIMP] Erro ao processar confirmação via estado pendente: {_e}')

        # 1) Verificar confirmação baseada na última resposta da IA (capa/convite para criar)
        ultima_ia_perguntou_criar_duimp = False
        processo_para_criar_duimp = None
        ambiente_para_criar_duimp = 'validacao'

        if historico and len(historico) > 0:
            ultima_resposta = historico[-1].get('resposta', '')
            if (
                'deseja criar' in ultima_resposta.lower()
                or 'criar a duimp' in ultima_resposta.lower()
                or 'pronto para criar duimp' in ultima_resposta.lower()
                or 'capa da duimp' in ultima_resposta.lower()
            ):
                ultima_ia_perguntou_criar_duimp = True
                logger.info('🔍 [DUIMP] Última resposta perguntou sobre criar DUIMP')

                processo_para_criar_duimp = self._extrair_processo_referencia(mensagem)
                logger.info(f'🔍 [DUIMP] Processo extraído da mensagem atual: {processo_para_criar_duimp}')

                if not processo_para_criar_duimp:
                    processo_para_criar_duimp = self._extrair_processo_referencia(ultima_resposta)
                    logger.info(f'🔍 [DUIMP] Processo extraído da última resposta da IA: {processo_para_criar_duimp}')

                if not processo_para_criar_duimp:
                    processo_para_criar_duimp, _ = self._extrair_contexto_do_historico(mensagem, historico)
                    logger.info(f'🔍 [DUIMP] Processo extraído do histórico: {processo_para_criar_duimp}')

                if 'produção' in ultima_resposta.lower() or 'producao' in ultima_resposta.lower():
                    ambiente_para_criar_duimp = 'producao'
                elif 'validação' in ultima_resposta.lower() or 'validacao' in ultima_resposta.lower():
                    ambiente_para_criar_duimp = 'validacao'

                mensagem_lower_check = mensagem.lower().strip()
                eh_comando_novo_duimp = bool(
                    re.search(r'registr[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check) or
                    re.search(r'cri[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check) or
                    re.search(r'ger[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check) or
                    re.search(r'fazer\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower_check)
                )

                if not eh_comando_novo_duimp:
                    confirmacoes_duimp = ['sim', 'pode prosseguir', 'prosseguir', 'confirmar', 'confirma', 'pode criar', 'pode registrar', 'confirmo', 'ok', 'criar']
                    eh_confirmacao_duimp = any(conf in mensagem_lower_check for conf in confirmacoes_duimp) or mensagem_lower_check.strip() in ['sim', 'pode', 'ok', 'confirmo', 'criar']
                else:
                    eh_confirmacao_duimp = False

                logger.info(f'🔍 [DUIMP] Mensagem: "{mensagem_lower_check}", eh_confirmacao: {eh_confirmacao_duimp}, processo: {processo_para_criar_duimp}')

                if ultima_ia_perguntou_criar_duimp and eh_confirmacao_duimp and processo_para_criar_duimp and not eh_comando_novo_duimp:
                    logger.info(f'✅✅✅ [DUIMP] Confirmação detectada - criando DUIMP do processo {processo_para_criar_duimp}')
                    try:
                        from services.agents.duimp_agent import DuimpAgent
                        duimp_agent = DuimpAgent()
                        resultado = duimp_agent._criar_duimp({
                            'processo_referencia': processo_para_criar_duimp,
                            'ambiente': ambiente_para_criar_duimp,
                            'confirmar': True
                        }, context={'chat_service': self})

                        if resultado.get('sucesso'):
                            return {
                                'sucesso': True,
                                'resposta': resultado.get('resposta', 'DUIMP criada com sucesso'),
                                'tool_calling': {
                                    'name': 'criar_duimp',
                                    'arguments': {
                                        'processo_referencia': processo_para_criar_duimp,
                                        'ambiente': ambiente_para_criar_duimp,
                                        'confirmar': True
                                    }
                                },
                                'numero_duimp': resultado.get('numero'),
                                'versao_duimp': resultado.get('versao')
                            }
                        return {
                            'sucesso': False,
                            'resposta': resultado.get('resposta', 'Erro ao criar DUIMP'),
                            'erro': resultado.get('erro')
                        }
                    except Exception as e:
                        logger.error(f'❌ Erro ao criar DUIMP após confirmação: {e}', exc_info=True)
                        return {
                            'sucesso': False,
                            'resposta': f'❌ Erro ao criar DUIMP: {str(e)}',
                            'erro': 'ERRO_CRIACAO_DUIMP'
                        }

        return None

    def _processar_confirmacao_duimp_estado_pendente_stream(
        self,
        mensagem: str,
        session_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Versão do streaming: checa apenas estado pendente de DUIMP (memória/contexto) e,
        se confirmar, executa e retorna um payload "stream" (chunk/done/...).
        """
        try:
            if (not hasattr(self, 'ultima_resposta_aguardando_duimp') or not self.ultima_resposta_aguardando_duimp) and session_id:
                try:
                    from services.context_service import buscar_contexto_sessao
                    ctxs = buscar_contexto_sessao(session_id=session_id, tipo_contexto='duimp_aguardando_confirmacao')
                    if ctxs:
                        ctx0 = ctxs[0]
                        proc_ctx = ctx0.get('valor', '')
                        amb_ctx = (ctx0.get('dados') or {}).get('ambiente', 'validacao')
                        self.ultima_resposta_aguardando_duimp = {
                            'processo_referencia': proc_ctx,
                            'ambiente': amb_ctx
                        }
                        logger.info(f'🧭 [STREAM] [DUIMP] Estado recuperado do contexto persistente: processo={proc_ctx}, ambiente={amb_ctx}')
                except Exception as _e_ctx_load:
                    logger.debug(f'[STREAM] [DUIMP] Falha ao recuperar estado do contexto: {_e_ctx_load}')

            # ✅ CRÍTICO (21/01/2026): Verificar se há realmente um pending intent de DUIMP
            # Não processar apenas baseado em estado em memória (pode estar desatualizado)
            tem_pending_intent_duimp = False
            if session_id:
                try:
                    from services.pending_intent_service import get_pending_intent_service
                    service = get_pending_intent_service()
                    if service:
                        pending_duimp = service.buscar_pending_intent(session_id, action_type='create_duimp')
                        tem_pending_intent_duimp = bool(pending_duimp and pending_duimp.get('status') == 'pending')
                        if tem_pending_intent_duimp:
                            logger.info(f'✅ [STREAM] [DUIMP] Pending intent de DUIMP encontrado: {pending_duimp.get("intent_id")}')
                        else:
                            logger.debug(f'🔍 [STREAM] [DUIMP] Nenhum pending intent de DUIMP encontrado (ou não está pending)')
                except Exception as e:
                    logger.debug(f'[STREAM] [DUIMP] Erro ao verificar pending intent: {e}')
            
            # ✅ Só processar se houver estado pendente E pending intent válido
            if hasattr(self, 'ultima_resposta_aguardando_duimp') and self.ultima_resposta_aguardando_duimp and tem_pending_intent_duimp:
                duimp_state = self.ultima_resposta_aguardando_duimp
                mensagem_lower_duimp = mensagem.lower().strip()
                # ✅ CORREÇÃO: Detecção determinística (exata match, não substring)
                confirmacoes_duimp_exatas = {'sim', 'confirma', 'confirmar', 'ok', 'pode', 'certo', 'correto', 'yes'}
                eh_confirmacao_duimp = mensagem_lower_duimp in confirmacoes_duimp_exatas

                if eh_confirmacao_duimp:
                    logger.info(f'✅✅✅ [STREAM] [DUIMP] Confirmação detectada - criando DUIMP para processo {duimp_state.get("processo_referencia")}')
                    try:
                        resultado_duimp = self._executar_funcao_tool('criar_duimp', {
                            'processo_referencia': duimp_state.get('processo_referencia'),
                            'ambiente': duimp_state.get('ambiente', 'validacao'),
                            'confirmar': True
                        }, mensagem_original=mensagem)

                        self.ultima_resposta_aguardando_duimp = None
                        try:
                            from services.context_service import limpar_contexto_sessao
                            if session_id:
                                limpar_contexto_sessao(session_id=session_id, tipo_contexto='duimp_aguardando_confirmacao')
                                logger.info('[STREAM] [DUIMP] Estado persistente limpo após criação')
                        except Exception as _e_ctx_clear:
                            logger.debug(f'[STREAM] [DUIMP] Falha ao limpar estado persistente: {_e_ctx_clear}')

                        if resultado_duimp and resultado_duimp.get('sucesso'):
                            resposta_final = resultado_duimp.get('resposta', '✅ DUIMP criada com sucesso!')
                            return {'chunk': resposta_final, 'done': True, 'tool_calls': None, 'resposta_final': resposta_final}

                        erro_msg = resultado_duimp.get('resposta', '❌ Erro ao criar DUIMP') if resultado_duimp else '❌ Erro ao criar DUIMP'
                        return {
                            'chunk': erro_msg,
                            'done': True,
                            'tool_calls': None,
                            'resposta_final': erro_msg,
                            'error': resultado_duimp.get('erro') if resultado_duimp else 'ERRO_CRIACAO_DUIMP'
                        }
                    except Exception as e:
                        logger.error(f'❌ [STREAM] Erro ao criar DUIMP após confirmação: {e}', exc_info=True)
                        return {
                            'chunk': f'❌ Erro ao criar DUIMP: {str(e)}',
                            'done': True,
                            'tool_calls': None,
                            'resposta_final': f'❌ Erro ao criar DUIMP: {str(e)}',
                            'error': 'ERRO_CRIACAO_DUIMP'
                        }
        except Exception as e_duimp_check:
            logger.debug(f'[STREAM] [DUIMP] Erro ao verificar confirmação de DUIMP: {e_duimp_check}')

        return None

    def _processar_comando_limpar_contexto_antes_precheck(
        self,
        mensagem: str,
        session_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta e executa o comando de limpar contexto antes de qualquer precheck/IA.
        Mantém o comportamento atual (limpa contexto persistente + histórico no DB e retorna cedo).
        """
        mensagem_lower = mensagem.lower().strip()
        comandos_limpar_contexto = [
            r'limpar\s+contexto',
            r'resetar\s+contexto',
            r'limpar\s+hist[óo]rico',
            r'resetar\s+hist[óo]rico',
            r'come[çc]ar\s+do\s+zero',
            r'come[çc]ar\s+novo',
            r'nova\s+conversa',
            r'esquecer\s+tudo',
            r'limpar\s+tudo',
            r'^reset\b',  # Apenas no início
            r'^clear\b',  # Apenas no início
            # ✅ NOVO: Comandos mais flexíveis (aceita em qualquer lugar)
            r'reset[aei].*tudo',
            r'limp[aeo]u?\s+tudo',
            r'resetei\s+tudo',
            r'resetei\s+contexto',
            r'limpei\s+tudo',
            r'limpei\s+contexto',
            r'apagar\s+tudo',
            r'apagar\s+contexto',
            r'deletar\s+tudo',
            r'deletar\s+contexto',
        ]

        for padrao in comandos_limpar_contexto:
            if re.search(padrao, mensagem_lower):
                logger.info(f'✅ Comando de limpar contexto detectado: "{mensagem}" (padrão: {padrao})')
                logger.info('✅✅✅ Comando de limpar contexto detectado - limpando TUDO')

                try:
                    if session_id:
                        from services.context_service import limpar_contexto_sessao
                        limpar_ok = limpar_contexto_sessao(session_id=session_id)
                        if not limpar_ok:
                            logger.warning(f"[CONTEXTO] Falha ao limpar contexto persistente para sessão {session_id}")
                        else:
                            logger.info(f"[CONTEXTO] Contexto persistente limpo para sessão {session_id}")

                        try:
                            from db_manager import get_db_connection
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute('DELETE FROM conversas_chat WHERE session_id = ?', (session_id,))
                            linhas_deletadas = cursor.rowcount
                            conn.commit()
                            conn.close()
                            logger.info(
                                f"[CONTEXTO] ✅ Histórico de conversas limpo: {linhas_deletadas} conversa(s) deletada(s) da sessão {session_id}"
                            )
                        except Exception as e:
                            logger.error(f"[CONTEXTO] Erro ao limpar histórico de conversas: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"[CONTEXTO] Erro ao limpar contexto persistente: {e}", exc_info=True)

                return {
                    'resposta': (
                        '✅ **Contexto limpo com sucesso!**\n\n'
                        '🔄 Todas as informações de conversas anteriores foram descartadas (incluindo processos e documentos em contexto).\n\n'
                        '💡 **A partir de agora:**\n'
                        '- Não vou usar contexto de processos anteriores\n'
                        '- Não vou usar contexto de CEs/DIs anteriores\n'
                        '- Cada pergunta será tratada de forma independente\n\n'
                        'Pode fazer suas perguntas normalmente!'
                    ),
                    'acao': None,
                    'contexto_limpo': True,
                    'limpar_historico_frontend': True
                }

        return None

    def _processar_correcao_email_destinatario_antes_precheck(
        self,
        mensagem: str,
        ultima_resposta_aguardando_email: bool,
        dados_email_para_enviar: Optional[Dict[str, Any]],
        session_id: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], bool, Optional[Dict[str, Any]]]:
        """
        Detecta e processa correção do destinatário do email antes do precheck.

        Returns:
            - resultado (dict) se gerou preview e deve retornar imediatamente; caso contrário None
            - eh_correcao_email_destinatario (bool)
            - dados_email_para_enviar atualizado (dict|None)
        """
        eh_correcao_email_destinatario = False
        if not ultima_resposta_aguardando_email or not dados_email_para_enviar:
            return None, eh_correcao_email_destinatario, dados_email_para_enviar

        mensagem_lower_check = mensagem.lower().strip()
        padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        match_email = re.search(padrao_email, mensagem_lower_check)

        if not match_email:
            return None, eh_correcao_email_destinatario, dados_email_para_enviar

        email_novo = match_email.group(1)
        verbos_enviar = ['mande', 'manda', 'envie', 'envia', 'enviar', 'mandar']
        verbos_corrigir = ['corrija', 'corrigir', 'correto', 'corrige', 'corriga', 'corrigido']
        tem_verbo_enviar = any(verbo in mensagem_lower_check for verbo in verbos_enviar)
        tem_verbo_corrigir = any(verbo in mensagem_lower_check for verbo in verbos_corrigir)

        palavras_conteudo = ['dizendo', 'avisando', 'informando', 'que', 'sobre', 'com']
        tem_conteudo_novo = any(palavra in mensagem_lower_check for palavra in palavras_conteudo)
        mensagem_curta = len(mensagem_lower_check) < 60

        palavras_excluir = ['relatorio', 'relatório', 'resumo', 'santander', 'bnd', 'processo', 'extrato', 'dados', 'informacoes', 'informações']
        tem_palavra_excluir = any(palavra in mensagem_lower_check for palavra in palavras_excluir)

        palavras_mensagem = mensagem_lower_check.split()
        tem_poucas_palavras = len(palavras_mensagem) <= 6

        padrao_correcao_email = re.search(
            r'corrig[aei]r?\s+(?:o\s+)?email\s+(?:para\s+)?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            mensagem_lower_check
        )
        eh_padrao_correcao = padrao_correcao_email is not None

        eh_apenas_correcao_email = (
            (
                tem_verbo_enviar
                or tem_verbo_corrigir
                or 'para' in mensagem_lower_check
                or len(palavras_mensagem) <= 3
                or eh_padrao_correcao
            )
            and mensagem_curta
            and tem_poucas_palavras
            and not tem_conteudo_novo
            and not tem_palavra_excluir
        )

        if not eh_apenas_correcao_email:
            return None, eh_correcao_email_destinatario, dados_email_para_enviar

        eh_correcao_email_destinatario = True
        logger.info(
            f'✅✅✅ [CORREÇÃO EMAIL] Usuário está corrigindo apenas o destinatário: "{email_novo}" (mensagem: "{mensagem_lower_check}")'
        )

        dados_email_para_enviar['destinatarios'] = [email_novo]

        draft_id = dados_email_para_enviar.get('draft_id')
        if draft_id:
            try:
                from services.email_draft_service import get_email_draft_service
                draft_service = get_email_draft_service()
                draft = draft_service.obter_draft(draft_id)
                if draft:
                    draft_service.revisar_draft(
                        draft_id=draft_id,
                        assunto=draft.assunto,
                        conteudo=draft.conteudo
                    )
                    logger.info(f'✅ [CORREÇÃO EMAIL] Draft {draft_id} atualizado com novo destinatário')
            except Exception as e:
                logger.warning(f'⚠️ Erro ao atualizar draft {draft_id}: {e}')

        # ✅ MULTIUSUÁRIO: persistir correção por sessão (sem vazar para outros usuários)
        self._set_email_pendente(session_id, dados_email_para_enviar)

        funcao_email = dados_email_para_enviar.get('funcao', 'enviar_email_personalizado')
        if funcao_email == 'enviar_email_personalizado':
            from datetime import datetime
            preview = "📧 **Email para Envio (Email Corrigido)**\n\n"
            preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += "**De:** Sistema mAIke (Make Consultores)\n"
            preview += f"**Para:** {email_novo}\n"
            if dados_email_para_enviar.get('cc'):
                preview += f"**CC:** {', '.join(dados_email_para_enviar.get('cc', []))}\n"
            if dados_email_para_enviar.get('bcc'):
                preview += f"**BCC:** {', '.join(dados_email_para_enviar.get('bcc', []))}\n"
            preview += f"**Assunto:** {dados_email_para_enviar.get('assunto')}\n"
            preview += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            preview += "**Mensagem:**\n\n"
            preview += f"{dados_email_para_enviar.get('conteudo')}\n\n"
            preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += "⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"

            return {
                'sucesso': True,
                'resposta': preview,
                'aguardando_confirmacao': True,
                'tool_calling': {'name': 'enviar_email_personalizado', 'arguments': dados_email_para_enviar},
                '_resultado_interno': {'ultima_resposta_aguardando_email': dados_email_para_enviar}
            }, eh_correcao_email_destinatario, dados_email_para_enviar

        return None, eh_correcao_email_destinatario, dados_email_para_enviar

    def _executar_precheck_centralizado(
        self,
        mensagem: str,
        historico: List[Dict[str, Any]],
        session_id: Optional[str],
        nome_usuario: Optional[str],
        *,
        ultima_resposta_aguardando_email: bool,
        dados_email_para_enviar: Optional[Dict[str, Any]],
        eh_correcao_email_destinatario: bool,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], bool]:
        """
        Executa o PrecheckService de forma centralizada (inclui execução de tool_calls retornadas pelo precheck).

        Returns:
            - resposta_imediata: dict para retornar imediatamente (ou None)
            - resposta_base_precheck: texto base quando o precheck pede refinamento por IA
            - deve_chamar_ia_para_refinar: flag indicando que a IA deve refinar a resposta base
        """
        resposta_base_precheck = None
        deve_chamar_ia_para_refinar = False

        # ✅ CRÍTICO: NÃO executar precheck se há email em preview pendente (exceto se já foi tratado como correção)
        if not ((not ultima_resposta_aguardando_email or not dados_email_para_enviar or eh_correcao_email_destinatario) and hasattr(self, "precheck_service") and self.precheck_service is not None):
            return None, resposta_base_precheck, deve_chamar_ia_para_refinar

        try:
            resposta_precheck = self.precheck_service.tentar_responder_sem_ia(
                mensagem=mensagem,
                historico=historico,
                session_id=session_id,
                nome_usuario=nome_usuario,
            )
            if not resposta_precheck:
                return None, resposta_base_precheck, deve_chamar_ia_para_refinar

            # ✅ NOVO: Verificar se o precheck retornou tool_calls para executar
            if resposta_precheck.get('tool_calls'):
                logger.info(f"[CHAT] Precheck retornou tool_calls: {len(resposta_precheck['tool_calls'])} tool(s)")
                tool_calls = resposta_precheck['tool_calls']
                resultados_tools = []

                for tool_call in tool_calls:
                    func_name = tool_call.get('function', {}).get('name')
                    func_args = tool_call.get('function', {}).get('arguments', {})

                    if func_name:
                        logger.info(f"[CHAT] Executando tool do precheck: {func_name}")
                        resultado_tool = self._executar_funcao_tool(
                            func_name,
                            func_args,
                            mensagem_original=mensagem
                        )
                        if resultado_tool:
                            resultados_tools.append(resultado_tool)

                # Se tem resultados de tools, retornar a resposta da primeira tool
                if resultados_tools:
                    resultado_final = resultados_tools[0]
                    logger.info("[CHAT] Resposta do precheck (tool executada). Origem: precheck+tool")
                    return resultado_final, resposta_base_precheck, deve_chamar_ia_para_refinar

            # ✅ NOVO: Verificar se o precheck indica que a IA deve ser chamada para refinar
            deve_chamar_ia_para_refinar = resposta_precheck.get('_deve_chamar_ia_para_refinar', False)

            # ✅ CRÍTICO (09/01/2026): Processar _resultado_interno do precheck para salvar draft_id no estado
            if isinstance(resposta_precheck, dict):
                resultado_interno_precheck = resposta_precheck.get('_resultado_interno', {})
                if resultado_interno_precheck and 'ultima_resposta_aguardando_email' in resultado_interno_precheck:
                    self.ultima_resposta_aguardando_email = resultado_interno_precheck['ultima_resposta_aguardando_email']
                    draft_id_salvo = self.ultima_resposta_aguardando_email.get('draft_id') if self.ultima_resposta_aguardando_email else None
                    if draft_id_salvo:
                        logger.info(f'✅✅✅ [PRECHECK] draft_id {draft_id_salvo} salvo no estado após precheck')
                    else:
                        logger.warning('⚠️ [PRECHECK] Precheck retornou resultado mas sem draft_id')

            if deve_chamar_ia_para_refinar:
                resposta_base_precheck = resposta_precheck.get('resposta', '')
                logger.info(
                    f"[CHAT] Precheck retornou resposta mas pediu refinamento pela IA. "
                    f"Resposta base: '{resposta_base_precheck[:100]}...'"
                )
                return None, resposta_base_precheck, deve_chamar_ia_para_refinar

            if resposta_precheck.get('resposta'):
                logger.info("[CHAT] Resposta final do precheck (sem refinamento pela IA). Origem: precheck")
                return resposta_precheck, resposta_base_precheck, deve_chamar_ia_para_refinar

            return None, resposta_base_precheck, deve_chamar_ia_para_refinar
        except Exception as e:
            logger.error(f"[PRECHECK] Erro inesperado no PrecheckService: {e}", exc_info=True)
            return None, resposta_base_precheck, deve_chamar_ia_para_refinar

    def _processar_prechecks_forcados_alta_prioridade(
        self,
        mensagem: str,
        mensagem_lower_precheck: str,
        session_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Prechecks hardcoded de alta prioridade que devem retornar cedo (SEM chamar IA).
        Extrai o bloco gigante do `processar_mensagem` para reduzir complexidade.
        """
        # ✅✅✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar pedidos de AJUDA/HELP
        eh_ajuda_precheck = bool(
            re.search(
                r'\bajuda\b|\bhelp\b|como\s+usar|o\s+que\s+posso\s+fazer|quais\s+comandos|palavras\s+chave|funcionalidades|guia|manual|instru[çc][õo]es|como\s+funciona|o\s+que\s+voc[êe]\s+faz|o\s+que\s+voc[êe]\s+pode\s+fazer|me\s+ajude|preciso\s+de\s+ajuda',
                mensagem_lower_precheck,
            )
        )
        if eh_ajuda_precheck:
            logger.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pedido de ajuda detectado. '
                'Chamando obter_ajuda e retornando diretamente (SEM chamar IA).'
            )
            try:
                resultado_ajuda_precheck = self._executar_funcao_tool('obter_ajuda', {}, mensagem_original=mensagem)
                resposta_ajuda_txt = (resultado_ajuda_precheck or {}).get('resposta') or ''
                if resultado_ajuda_precheck and resposta_ajuda_txt:
                    logger.info(
                        f'✅✅✅ Resposta forçada ANTES da IA (AJUDA) - tamanho: {len(resposta_ajuda_txt)}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resposta_ajuda_txt,
                        'tool_calling': {'name': 'obter_ajuda', 'arguments': {}},
                        '_processado_precheck': True,
                    }
                logger.warning(f'❌ Resposta vazia da tool obter_ajuda para "{mensagem}". Prosseguindo com a IA.')
            except Exception as e:
                logger.error(f'❌ Erro ao forçar tool obter_ajuda para "{mensagem}": {e}', exc_info=True)

        # ✅ CORREÇÃO: Verificar primeiro se é pergunta sobre chegada com período (semana, mês) ANTES do dashboard de hoje
        tem_periodo_temporal_especifico_precheck = bool(
            re.search(
                r'\b(?:dezembro|janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro)\b',
                mensagem_lower_precheck,
            )
            or re.search(
                r'\b(?:semana\s*(?:q\s*|que\s*)?vem|semana\s*(?:q\s*|que\s*)?vêm|próxima\s*semana|proxima\s*semana)\b',
                mensagem_lower_precheck,
            )
            or re.search(
                r'\b(?:mês\s+que\s+vem|mes\s+que\s+vem|próximo\s+mês|proximo\s+mes)\b',
                mensagem_lower_precheck,
            )
            or re.search(r'\b(?:esta\s*semana|nesta\s*semana|essa\s*semana|nessa\s*semana)\b', mensagem_lower_precheck)
            or re.search(r'\b(?:este mês|neste mês|neste mes)\b', mensagem_lower_precheck)
            or re.search(r'\b(?:amanhã|amanha)\b', mensagem_lower_precheck)
        )

        eh_pergunta_chegada_periodo_temporal_precheck = bool(
            # Caso geral: mensagem fala de período (semana/mês/amanhã) + algum verbo de chegada
            (
                tem_periodo_temporal_especifico_precheck
                and re.search(
                    # Inclui "chega" (singular) além de "chegar"/"chegam"/"chegando"
                    r'\bchega\b|chegando|chegam|chegar|temchgando|tem.*chegando',
                    mensagem_lower_precheck,
                )
            )
            # Padrões específicos já mapeados
            or re.search(
                r'o\s+que\s+tem\s*ch?egando\s+(?:essa|esta|nessa|nesta)\s*semana',
                mensagem_lower_precheck,
                re.IGNORECASE,
            )
            or re.search(
                r'o\s+que\s+tem\s*ch?egando\s+semana\s*(?:que\s*)?vem',
                mensagem_lower_precheck,
                re.IGNORECASE,
            )
            or re.search(
                r'quais\s+(?:os|as)?\s*(?:processos?)?\s*chegam\s+(?:essa|esta|nessa|nesta)\s*semana',
                mensagem_lower_precheck,
                re.IGNORECASE,
            )
            or re.search(
                r'quais\s+(?:os|as)?\s*(?:processos?)?\s*chegam\s+semana\s*(?:que\s*)?vem',
                mensagem_lower_precheck,
                re.IGNORECASE,
            )
            or re.search(
                r'processos?\s+que\s+chegam\s+semana\s*(?:que\s*)?vem',
                mensagem_lower_precheck,
                re.IGNORECASE,
            )
            or re.search(
                r'processos?\s+chegando\s+semana\s*(?:que\s*)?vem',
                mensagem_lower_precheck,
                re.IGNORECASE,
            )
        )
        if eh_pergunta_chegada_periodo_temporal_precheck:
            logger.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA: Pergunta sobre chegada com período temporal detectada ANTES do dashboard. '
                'Usando listar_processos_por_eta.'
            )
            try:
                filtro_data = 'semana'
                if re.search(r'\b(?:semana\s*(?:q\s*|que\s*)?vem|semana\s*(?:q\s*|que\s*)?vêm|próxima\s*semana|proxima\s*semana)\b', mensagem_lower_precheck):
                    filtro_data = 'proxima_semana'
                    logger.info(f'✅ Filtro detectado: "proxima_semana" para mensagem: "{mensagem}"')
                elif re.search(r'\b(?:este mês|neste mês|neste mes)\b', mensagem_lower_precheck):
                    filtro_data = 'mes'
                elif re.search(r'\b(?:mês\s+que\s+vem|mes\s+que\s+vem|próximo\s+mês|proximo\s+mes)\b', mensagem_lower_precheck):
                    filtro_data = 'proximo_mes'
                elif re.search(r'\b(?:amanhã|amanha)\b', mensagem_lower_precheck):
                    filtro_data = 'amanha'
                else:
                    filtro_data = 'semana'
                    logger.info(f'✅ Filtro padrão: "semana" (esta semana) para mensagem: "{mensagem}"')

                categoria_precheck = None
                categoria_na_mensagem = self._extrair_categoria_da_mensagem(mensagem)
                if categoria_na_mensagem:
                    mensagem_lower_para_categoria = mensagem.lower()
                    palavras_negacao = ['não', 'nao', 'sem', 'exceto', 'menos', 'fora']
                    categoria_negada = any(
                        palavra in mensagem_lower_para_categoria and categoria_na_mensagem.lower() in mensagem_lower_para_categoria
                        for palavra in palavras_negacao
                    )
                    if not categoria_negada:
                        categoria_precheck = categoria_na_mensagem
                        logger.info(f'✅ Categoria {categoria_precheck} detectada explicitamente na mensagem - usando filtro')
                    else:
                        logger.info(f'⚠️ Categoria {categoria_na_mensagem} foi negada na mensagem - não usar filtro')
                else:
                    logger.info('✅ Nenhuma categoria mencionada explicitamente - buscando TODOS os processos')

                resultado_forcado_chegada = self._executar_funcao_tool(
                    'listar_processos_por_eta',
                    {
                        'filtro_data': filtro_data,
                        'limite': 500,
                        **({'categoria': categoria_precheck} if categoria_precheck else {}),
                    },
                    mensagem_original=mensagem,
                )
                if resultado_forcado_chegada.get('resposta'):
                    resposta_chegada_txt = resultado_forcado_chegada.get('resposta') or ''
                    logger.info(
                        f'✅ Resposta forçada para chegada com período "{filtro_data}" - '
                        f'tamanho: {len(resposta_chegada_txt)}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resposta_chegada_txt,
                        'tool_used': 'listar_processos_por_eta',
                        'tool_calling': 'listar_processos_por_eta',
                        'dados': resultado_forcado_chegada.get('dados'),
                        'precheck': True,
                        'precheck_tipo': 'chegada_periodo',
                    }
            except Exception as e:
                logger.error(f'❌ Erro ao executar listar_processos_por_eta no pre-check para período: {e}', exc_info=True)

        # ✅ NOVO: Detectar fechamento do dia ANTES do dashboard (prioridade mais alta)
        eh_fechamento_dia_precheck = bool(
            re.search(r'fechar\s+(?:o\s+)?dia', mensagem_lower_precheck)
            or re.search(r'fechamento\s+(?:do\s+)?dia', mensagem_lower_precheck)
            or re.search(r'finalizar\s+(?:o\s+)?dia', mensagem_lower_precheck)
            or re.search(r'finalizacao\s+(?:do\s+)?dia', mensagem_lower_precheck)
            or re.search(r'finalização\s+(?:do\s+)?dia', mensagem_lower_precheck)
        )
        if eh_fechamento_dia_precheck:
            logger.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Fechamento do dia detectado. '
                'Chamando fechar_dia e retornando diretamente (SEM chamar IA).'
            )
            try:
                categoria_filtro = None
                modal_filtro = None

                categoria_extraida = self._extrair_categoria_da_mensagem(mensagem)
                if categoria_extraida:
                    categoria_filtro = categoria_extraida
                    logger.info(f'✅ Categoria {categoria_filtro} mencionada explicitamente na mensagem - usando no fechamento')
                else:
                    logger.info('✅ Fechamento do dia SEM categoria - retornando todas as movimentações')

                if re.search(r'\ba[ée]reo\b', mensagem_lower_precheck):
                    modal_filtro = 'Aéreo'
                elif re.search(r'\bmar[íi]timo\b', mensagem_lower_precheck):
                    modal_filtro = 'Marítimo'

                args_fechamento: Dict[str, Any] = {}
                if categoria_filtro:
                    args_fechamento['categoria'] = categoria_filtro
                if modal_filtro:
                    args_fechamento['modal'] = modal_filtro

                resultado_fechamento = self._executar_funcao_tool('fechar_dia', args_fechamento, mensagem_original=mensagem)
                if resultado_fechamento.get('resposta'):
                    resposta_fechamento_txt = resultado_fechamento.get('resposta') or ''
                    logger.info(
                        f'✅✅✅ Resposta forçada ANTES da IA (FECHAMENTO DO DIA) - tamanho: {len(resposta_fechamento_txt)}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resposta_fechamento_txt,
                        'tool_used': 'fechar_dia',
                        'tool_calling': 'fechar_dia',
                        'dados': resultado_fechamento.get('dados'),
                        'precheck': True,
                        'precheck_tipo': 'fechamento_dia',
                    }
            except Exception as e:
                logger.error(f'❌ Erro ao executar fechar_dia no pre-check: {e}', exc_info=True)

        # ✅ Dashboard do dia
        eh_dashboard_hoje_precheck = bool(
            re.search(r'o\s+que\s+temos?\s+(?:pra|para)\s+hoje', mensagem_lower_precheck)
            or re.search(r'o\s+que\s+temos?\s+hoje', mensagem_lower_precheck)
            or re.search(r'o\s+que\s+tem\s+(?:pra|para)\s+hoje', mensagem_lower_precheck)
            or re.search(r'dashboard\s+de\s+hoje', mensagem_lower_precheck)
            or re.search(r'resumo\s+do\s+dia', mensagem_lower_precheck)
            or re.search(r'o\s+que\s+precisa\s+ser\s+feito\s+hoje', mensagem_lower_precheck)
            or (re.search(r'o\s+que\s+est[áa]\s+chegando\s+hoje', mensagem_lower_precheck) and not tem_periodo_temporal_especifico_precheck)
            or re.search(r'processos?\s+de\s+hoje', mensagem_lower_precheck)
        )
        if eh_dashboard_hoje_precheck:
            logger.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Dashboard do dia detectado. '
                'Chamando obter_dashboard_hoje e retornando diretamente (SEM chamar IA).'
            )
            if session_id:
                try:
                    from services.context_service import limpar_contexto_sessao
                    limpar_contexto_sessao(session_id, tipo_contexto="categoria_atual")
                    limpar_contexto_sessao(session_id, tipo_contexto="processo_atual")
                    logger.info(f"🗑️ Contexto de categoria e processo limpo devido a dashboard do dia: {mensagem_lower_precheck}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao limpar contexto ao gerar dashboard: {e}")

            try:
                categoria_filtro = None
                modal_filtro = None
                apenas_pendencias = False

                categoria_extraida = self._extrair_categoria_da_mensagem(mensagem)
                if categoria_extraida:
                    categoria_filtro = categoria_extraida

                if re.search(r'\ba[ée]reo\b', mensagem_lower_precheck):
                    modal_filtro = 'Aéreo'
                elif re.search(r'\bmar[íi]timo\b', mensagem_lower_precheck):
                    modal_filtro = 'Marítimo'

                if re.search(r'com\s+pendencias?|pendencias?\s+de\s+hoje|apenas\s+pendencias?', mensagem_lower_precheck):
                    apenas_pendencias = True

                args_tool: Dict[str, Any] = {}
                if categoria_filtro:
                    args_tool['categoria'] = categoria_filtro
                if modal_filtro:
                    args_tool['modal'] = modal_filtro
                if apenas_pendencias:
                    args_tool['apenas_pendencias'] = True

                resultado_dashboard_precheck = self._executar_funcao_tool('obter_dashboard_hoje', args_tool, mensagem_original=mensagem)
                if resultado_dashboard_precheck and resultado_dashboard_precheck.get('resposta'):
                    dados_json = resultado_dashboard_precheck.get('dados_json')
                    precisa_formatar = resultado_dashboard_precheck.get('precisa_formatar', False)
                    resposta_final = resultado_dashboard_precheck.get('resposta') or ''

                    if dados_json and precisa_formatar:
                        try:
                            from services.agents.processo_agent import RelatorioFormatterService
                            resposta_fallback = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)
                            if resposta_fallback:
                                logger.info(
                                    f'✅✅✅ [PRECHECK] Relatório formatado com fallback simples (tipo: {dados_json.get("tipo_relatorio", "desconhecido")}) - rápido para chat'
                                )
                                resposta_final = resposta_fallback
                            else:
                                logger.debug('⚠️ [PRECHECK] Fallback simples falhou. Usando resposta manual.')
                        except Exception as e:
                            logger.error(f'❌ [PRECHECK] Erro ao formatar relatório com fallback simples: {e}', exc_info=True)

                    resposta_final = self._limpar_frases_problematicas(resposta_final)
                    logger.info(f'✅✅✅ Resposta forçada ANTES da IA (DASHBOARD HOJE) - tamanho: {len(resposta_final)}')
                    return {
                        'sucesso': True,
                        'resposta': resposta_final,
                        'tool_calling': {'name': 'obter_dashboard_hoje', 'arguments': args_tool},
                        '_processado_precheck': True,
                    }
                logger.warning(f'❌ Resposta vazia da tool obter_dashboard_hoje para "{mensagem}". Prosseguindo com a IA.')
            except Exception as e:
                logger.error(f'❌ Erro ao forçar tool obter_dashboard_hoje para "{mensagem}": {e}', exc_info=True)

        # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Extrato do CCT (por número ou por processo)
        match_numero_cct = None
        if 'cct' in mensagem_lower_precheck:
            match_numero_cct = re.search(r'(?<!\d)([A-Z]{3}(?:-)?\d{4,12})(?!\d)', mensagem, re.IGNORECASE)

        match_extrato_cct = re.search(
            r'extrato\s+(?:do\s+)?cct\s+(?:do\s+(?:processo\s+)?)?([a-z]{3}\.?\d{1,4}/?\d{2})',
            mensagem_lower_precheck,
        ) or re.search(
            r'pdf\s+(?:do\s+)?cct\s+(?:do\s+(?:processo\s+)?)?([a-z]{3}\.?\d{1,4}/?\d{2})',
            mensagem_lower_precheck,
        )

        processo_extrato_cct = None
        numero_cct_extrato = None

        if match_numero_cct and isinstance(match_numero_cct, re.Match) and match_numero_cct.lastindex and match_numero_cct.group(1):
            numero_cct_extrato = match_numero_cct.group(1)
            logger.warning(
                f'🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pedido de extrato do CCT detectado por número. '
                f'CCT: {numero_cct_extrato}. Chamando obter_extrato_cct e retornando diretamente (SEM chamar IA).'
            )
            try:
                resultado_extrato_precheck = self._executar_funcao_tool(
                    'obter_extrato_cct',
                    {'numero_cct': numero_cct_extrato},
                    mensagem_original=mensagem,
                )
                resposta_extrato_cct_txt = resultado_extrato_precheck.get('resposta') or ''
                if resposta_extrato_cct_txt:
                    logger.info(
                        f'✅✅✅ Resposta forçada ANTES da IA (EXTRATO CCT por número) - tamanho: {len(resposta_extrato_cct_txt)}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resposta_extrato_cct_txt,
                        'tool_calling': {'name': 'obter_extrato_cct', 'arguments': {'numero_cct': numero_cct_extrato}},
                        '_processado_precheck': True,
                    }
                logger.warning(f'❌ Resposta vazia da tool obter_extrato_cct para CCT "{numero_cct_extrato}". Prosseguindo com a IA.')
            except Exception as e:
                logger.error(f'❌ Erro ao forçar tool obter_extrato_cct para CCT "{numero_cct_extrato}": {e}', exc_info=True)

        if match_extrato_cct and isinstance(match_extrato_cct, re.Match) and match_extrato_cct.lastindex and match_extrato_cct.group(1):
            processo_extrato_cct = match_extrato_cct.group(1).upper()
            if not re.match(r'[A-Z]{2,4}\.\d{4}/\d{2}', processo_extrato_cct):
                processo_extrato_cct = self._extrair_processo_referencia(processo_extrato_cct) or processo_extrato_cct
        elif match_extrato_cct:
            processo_extrato_cct = self._extrair_processo_referencia(mensagem)

        if not processo_extrato_cct and not numero_cct_extrato and re.search(r'extrato\s+(?:do\s+)?cct', mensagem_lower_precheck):
            match_numero = re.search(r'(?<!\d)([A-Z]{3}(?:-)?\d{4,12})(?!\d)', mensagem, re.IGNORECASE)
            if match_numero:
                numero_cct_extrato = match_numero.group(1)
            else:
                processo_extrato_cct = self._extrair_processo_referencia(mensagem)

        if processo_extrato_cct:
            logger.warning(
                f'🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pedido de extrato do CCT detectado. '
                f'Processo: {processo_extrato_cct}. Chamando obter_extrato_cct e retornando diretamente (SEM chamar IA).'
            )
            try:
                resultado_extrato_precheck = self._executar_funcao_tool(
                    'obter_extrato_cct',
                    {'processo_referencia': processo_extrato_cct},
                    mensagem_original=mensagem,
                )
                resposta_extrato_cct_proc_txt = resultado_extrato_precheck.get('resposta') or ''
                if resposta_extrato_cct_proc_txt:
                    logger.info(
                        f'✅✅✅ Resposta forçada ANTES da IA (EXTRATO CCT) - tamanho: {len(resposta_extrato_cct_proc_txt)}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resposta_extrato_cct_proc_txt,
                        'tool_calling': {'name': 'obter_extrato_cct', 'arguments': {'processo_referencia': processo_extrato_cct}},
                        '_processado_precheck': True,
                    }
                logger.warning(f'❌ Resposta vazia da tool obter_extrato_cct para "{mensagem}". Prosseguindo com a IA.')
            except Exception as e:
                logger.error(f'❌ Erro ao forçar tool obter_extrato_cct para "{mensagem}": {e}', exc_info=True)

        return None

    def _resolver_contexto_processo_categoria_e_acao_antes_prompt(
        self,
        mensagem: str,
        historico: List[Dict[str, Any]],
        session_id: Optional[str],
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Resolve contexto de processo/categoria/CE/CCT e identifica ação (inclui vinculação automática).

        Este bloco era um dos maiores do `processar_mensagem` e foi extraído para reduzir complexidade.

        Returns:
            - resultado_imediato: dict para retornar imediatamente (ex: categoria desconhecida / confirmação DUIMP executada), ou None
            - ctx: dict com chaves usadas no restante do fluxo:
                processo_ref, categoria_atual, categoria_contexto, numero_ce_contexto, numero_cct,
                contexto_processo, acao_info, eh_pergunta_generica, eh_pergunta_pendencias,
                eh_pergunta_situacao, precisa_contexto, eh_fechamento_dia
        """
        # Defaults
        processo_ref = None
        numero_ce_contexto = None
        numero_cct = None
        categoria_atual = None
        categoria_contexto = None
        contexto_processo = None
        acao_info: Dict[str, Any] = {}
        eh_pergunta_generica = self._eh_pergunta_generica(mensagem)
        eh_pergunta_pendencias = bool(re.search(r'pend[êe]ncia|pendente|bloqueio|bloqueado', mensagem.lower()))
        eh_pergunta_situacao = bool(re.search(r'situa[çc][ãa]o|status|como\s+est[ao]|est[ao]\s+os', mensagem.lower()))
        precisa_contexto = self._identificar_se_precisa_contexto(mensagem)
        mensagem_lower_categoria = mensagem.lower()
        eh_fechamento_dia = bool(
            re.search(r'fechar\s+(?:o\s+)?dia|fechamento\s+(?:do\s+)?dia|finalizar\s+(?:o\s+)?dia|finalizacao\s+(?:do\s+)?dia', mensagem_lower_categoria)
        )

        # ✅ NOVO: Verificar se a última resposta da IA perguntou sobre criar DUIMP
        ultima_ia_perguntou_criar_duimp = False
        processo_para_criar_duimp = None
        ambiente_para_criar_duimp = 'validacao'
        payload_duimp_para_criar = None

        # ✅ NOVO: Vinculação (CE/CCT/DI/DUIMP)
        ultima_ia_perguntou_vincular = False
        tipo_documento_para_vincular = None
        numero_documento_para_vincular = None

        if historico and len(historico) > 0:
            ultima_resposta = historico[-1].get('resposta', '')
            if (
                'deseja criar' in ultima_resposta.lower()
                or 'criar a duimp' in ultima_resposta.lower()
                or 'pronto para criar duimp' in ultima_resposta.lower()
                or 'capa da duimp' in ultima_resposta.lower()
            ):
                ultima_ia_perguntou_criar_duimp = True
                processo_para_criar_duimp = self._extrair_processo_referencia(mensagem)
                logger.info(f'🔍 [DUIMP] Processo extraído da mensagem atual: {processo_para_criar_duimp}')

                if not processo_para_criar_duimp:
                    processo_para_criar_duimp = self._extrair_processo_referencia(ultima_resposta)
                    logger.info(f'🔍 [DUIMP] Processo extraído da última resposta da IA: {processo_para_criar_duimp}')

                if not processo_para_criar_duimp:
                    processo_para_criar_duimp, _ = self._extrair_contexto_do_historico(mensagem, historico)
                    logger.info(f'🔍 [DUIMP] Processo extraído do histórico: {processo_para_criar_duimp}')

                if not processo_para_criar_duimp and session_id:
                    from services.context_service import buscar_contexto_sessao
                    contextos = buscar_contexto_sessao(session_id, tipo_contexto="processo_atual")
                    if contextos:
                        processo_contexto = contextos[0].get('valor', '').strip()
                        processo_na_mensagem = self._extrair_processo_referencia(mensagem)
                        if not processo_na_mensagem:
                            processo_para_criar_duimp = processo_contexto
                            logger.info(f'🔍 [DUIMP] Processo do contexto de sessão: {processo_para_criar_duimp}')
                        else:
                            logger.warning(
                                f'⚠️ [DUIMP] Processo {processo_na_mensagem} mencionado na mensagem, mas contexto tem {processo_contexto} - IGNORANDO contexto'
                            )

                if 'produção' in ultima_resposta.lower() or 'producao' in ultima_resposta.lower():
                    ambiente_para_criar_duimp = 'producao'
                elif 'validação' in ultima_resposta.lower() or 'validacao' in ultima_resposta.lower():
                    ambiente_para_criar_duimp = 'validacao'

                ultimo_resultado = historico[-1].get('_resultado_interno', {})
                if isinstance(ultimo_resultado, dict) and 'payload_duimp' in ultimo_resultado:
                    payload_duimp_para_criar = ultimo_resultado.get('payload_duimp')

            mensagem_lower = mensagem.lower().strip()
            eh_comando_novo_duimp = bool(
                re.search(r'registr[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
                or re.search(r'cri[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
                or re.search(r'ger[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
                or re.search(r'fazer\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
            )
            if not eh_comando_novo_duimp:
                confirmacoes = ['sim', 'pode prosseguir', 'prosseguir', 'confirmar', 'confirma', 'pode criar', 'pode registrar', 'confirmo', 'ok']
                eh_confirmacao = any(conf in mensagem_lower for conf in confirmacoes) or mensagem_lower.strip() in ['sim', 'pode', 'ok', 'confirmo']
            else:
                eh_confirmacao = False

            if ultima_ia_perguntou_criar_duimp and eh_confirmacao and processo_para_criar_duimp and not eh_comando_novo_duimp:
                logger.info(f'✅ Confirmação detectada para criar DUIMP do processo {processo_para_criar_duimp}')
                try:
                    from services.agents.duimp_agent import DuimpAgent
                    duimp_agent = DuimpAgent()
                    resultado = duimp_agent._criar_duimp({
                        'processo_referencia': processo_para_criar_duimp,
                        'ambiente': ambiente_para_criar_duimp,
                        'confirmar': True
                    }, context={'chat_service': self})

                    if resultado.get('sucesso'):
                        return {
                            'sucesso': True,
                            'resposta': resultado.get('resposta', 'DUIMP criada com sucesso'),
                            'tool_calling': {
                                'name': 'criar_duimp',
                                'arguments': {'processo_referencia': processo_para_criar_duimp, 'ambiente': ambiente_para_criar_duimp, 'confirmar': True}
                            },
                            'numero_duimp': resultado.get('numero'),
                            'versao_duimp': resultado.get('versao')
                        }, {}
                    return {
                        'sucesso': False,
                        'resposta': resultado.get('resposta', 'Erro ao criar DUIMP'),
                        'erro': resultado.get('erro')
                    }, {}
                except Exception as e:
                    logger.error(f'❌ Erro ao executar criação da DUIMP: {e}', exc_info=True)
                    return {'sucesso': False, 'resposta': f'❌ **Erro ao criar DUIMP:** {str(e)}'}, {}

        # ✅ NOVO: Verificar se a última resposta perguntou sobre vincular processo
        if historico and len(historico) > 0:
            ultima_resposta = historico[-1].get('resposta', '')
            if ('qual processo você quer vincular' in ultima_resposta.lower()) or ('qual processo' in ultima_resposta.lower() and 'vincular' in ultima_resposta.lower()):
                ultima_ia_perguntou_vincular = True
                if 'cct' in ultima_resposta.lower():
                    tipo_documento_para_vincular = 'CCT'
                elif 'ce' in ultima_resposta.lower() or 'conhecimento de embarque' in ultima_resposta.lower():
                    tipo_documento_para_vincular = 'CE'
                elif 'di' in ultima_resposta.lower() or 'declaração de importação' in ultima_resposta.lower():
                    tipo_documento_para_vincular = 'DI'
                elif 'duimp' in ultima_resposta.lower():
                    tipo_documento_para_vincular = 'DUIMP'

                if len(historico) >= 2:
                    for i in range(min(5, len(historico))):
                        msg_anterior = historico[-(i + 1)].get('mensagem', '') or historico[-(i + 1)].get('resposta', '')
                        if tipo_documento_para_vincular == 'CCT':
                            numero_cct_temp = self._extrair_numero_cct(msg_anterior)
                            if numero_cct_temp:
                                numero_documento_para_vincular = numero_cct_temp
                                logger.info(
                                    f'✅ Número do CCT extraído do histórico: {numero_documento_para_vincular} (da mensagem {i + 1} do histórico)'
                                )
                                break
                        elif tipo_documento_para_vincular == 'CE':
                            numero_ce_temp = self._extrair_numero_ce(msg_anterior)
                            if numero_ce_temp:
                                numero_documento_para_vincular = numero_ce_temp
                                break
                        elif tipo_documento_para_vincular == 'DI':
                            di_info = self._extrair_numero_duimp_ou_di(msg_anterior)
                            if di_info and di_info.get('tipo') == 'DI':
                                numero_documento_para_vincular = di_info.get('numero')
                                break
                        elif tipo_documento_para_vincular == 'DUIMP':
                            duimp_info = self._extrair_numero_duimp_ou_di(msg_anterior)
                            if duimp_info and duimp_info.get('tipo') == 'DUIMP':
                                numero_documento_para_vincular = duimp_info.get('numero')
                                break

        # ✅ CRÍTICO: Se há CCT na mensagem, não usar contexto de processo anterior
        numero_cct = self._extrair_numero_cct(mensagem)
        if numero_cct:
            logger.info(f'✅ CCT {numero_cct} encontrado na mensagem atual - contexto do processo será ignorado')
            processo_ref = None
            numero_ce_contexto = None
        else:
            processo_ref = self._extrair_processo_referencia(mensagem)
            if processo_ref:
                from db_manager import verificar_categoria_processo
                categoria_detectada = processo_ref.split('.')[0] if '.' in processo_ref else None
                if categoria_detectada and 2 <= len(categoria_detectada) <= 4:
                    if not verificar_categoria_processo(categoria_detectada):
                        logger.info(f'🔍 Categoria desconhecida detectada: {categoria_detectada}')
                        return {
                            'resposta': (
                                f'❓ **Categoria desconhecida detectada: {categoria_detectada}**\n\n'
                                f'Vi que você mencionou "{categoria_detectada}", mas essa categoria não está cadastrada no sistema.\n\n'
                                f'**{categoria_detectada} é uma categoria de processo?**\n\n'
                                f'Se sim, responda "sim" ou "é" e eu vou adicionar ao sistema.\n'
                                f'Se não, pode ser que você tenha digitado errado ou seja um número de CCT/CE.'
                            ),
                            'acao': 'perguntar_categoria',
                            'categoria_detectada': categoria_detectada,
                            'processo_referencia': processo_ref,
                            'tool_calling': [],
                        }, {}

        numero_ce_contexto = None

        # ✅ Extrair categoria (bloquear para comandos de DUIMP para evitar "DO")
        eh_comando_duimp_antes_categoria = bool(
            re.search(r'registr[ae]r?\s+duimp', mensagem_lower_categoria)
            or re.search(r'cri[ae]r?\s+duimp', mensagem_lower_categoria)
            or re.search(r'ger[ae]r?\s+duimp', mensagem_lower_categoria)
            or re.search(r'fazer\s+duimp', mensagem_lower_categoria)
        )
        if not eh_comando_duimp_antes_categoria:
            categoria_atual = self._extrair_categoria_da_mensagem(mensagem)
        else:
            categoria_atual = None
            logger.info('🔍 Comando de DUIMP detectado - bloqueando extração de categoria para evitar falsos positivos (ex: "DO" de "duimp do")')

        if categoria_atual:
            mensagem_lower_cat = mensagem.lower()
            categoria_lower = categoria_atual.lower()
            padroes_descarte = [
                rf'\b(?:não|nao|sem|nunca|jamais|nada|nenhum|nenhuma)\s+{re.escape(categoria_lower)}\b',
                rf'\b{re.escape(categoria_lower)}\s+(?:não|nao|nunca|jamais|não são|nao são)\b',
                rf'\b(?:não|nao)\s+tem\s+{re.escape(categoria_lower)}\b',
                rf'\b(?:não|nao)\s+tem\s+nada\s+de\s+{re.escape(categoria_lower)}\b',
                rf'\b(?:não|nao)\s+é\s+{re.escape(categoria_lower)}\b',
                rf'\b(?:não|nao)\s+são\s+{re.escape(categoria_lower)}\b',
            ]
            for padrao in padroes_descarte:
                if re.search(padrao, mensagem_lower_cat):
                    logger.info(f'⚠️ Categoria {categoria_atual} foi descartada/negada na mensagem atual - não usar')
                    categoria_atual = None
                    break

        # ✅ Categoria do histórico (quando aplicável)
        categoria_contexto = None
        if eh_fechamento_dia:
            categoria_contexto = None
            logger.info('✅ Comando de fechamento do dia detectado - categoria do contexto será ignorada')
        else:
            processo_no_historico = None
            if historico:
                for item in reversed(historico[-6:]):
                    item_msg = item.get('mensagem', '') or item.get('resposta', '')
                    if not item_msg:
                        continue
                    processo_hist = self._extrair_processo_referencia(item_msg)
                    if processo_hist:
                        processo_no_historico = processo_hist
                        break

            if categoria_atual:
                logger.info(f'✅ Categoria {categoria_atual} encontrada na mensagem atual - contexto do histórico será ignorado')
            elif eh_pergunta_generica and (eh_pergunta_pendencias or eh_pergunta_situacao) and not processo_no_historico:
                categoria_contexto = self._extrair_categoria_do_historico(mensagem, historico)
                if categoria_contexto:
                    logger.info(
                        f'✅ Categoria {categoria_contexto} preservada do histórico para pergunta genérica sobre pendências/situação (sem processo específico)'
                    )
            elif eh_pergunta_generica and processo_no_historico:
                categoria_contexto = None
                logger.info(f'✅ Categoria limpa - pergunta genérica após processo específico {processo_no_historico}')
            elif not eh_pergunta_generica:
                categoria_contexto = self._extrair_categoria_do_historico(mensagem, historico)
                if categoria_contexto:
                    logger.info(f'Categoria {categoria_contexto} extraída do histórico da conversa')

        # ✅ Contexto de processo do histórico (quando aplicável)
        numero_ce_mensagem = self._extrair_numero_ce(mensagem)
        usar_contexto_processo = (
            not processo_ref
            and not numero_cct
            and not numero_ce_mensagem
            and (
                not eh_pergunta_generica
                or (eh_pergunta_generica and not (eh_pergunta_pendencias or eh_pergunta_situacao) and not categoria_contexto)
            )
        )

        if usar_contexto_processo:
            processo_ref, numero_ce_contexto = self._extrair_contexto_do_historico(mensagem, historico)
            if processo_ref:
                logger.info(f'Processo {processo_ref} extraído do histórico da conversa')
            elif numero_ce_contexto:
                logger.info(f'CE {numero_ce_contexto} extraído do histórico da conversa')
        elif eh_pergunta_generica and (eh_pergunta_pendencias or eh_pergunta_situacao) and categoria_contexto:
            processo_ref = None
            numero_ce_contexto = None
            logger.info(f'✅ Contexto de processo limpo - usando apenas categoria {categoria_contexto} do histórico')

        if ultima_ia_perguntou_criar_duimp and processo_para_criar_duimp:
            processo_ref = processo_para_criar_duimp
            logger.info(f'Confirmação detectada - processo {processo_ref} será usado para criar DUIMP')

        if processo_ref:
            contexto_processo = self._obter_contexto_processo(processo_ref)

        acao_info = self._identificar_acao(mensagem, contexto_processo)

        # ✅ Vinculação automática
        if ultima_ia_perguntou_vincular and tipo_documento_para_vincular and numero_documento_para_vincular:
            processo_para_vincular = self._extrair_processo_referencia(mensagem)
            if processo_para_vincular:
                if tipo_documento_para_vincular == 'CCT':
                    acao_info['acao'] = 'vincular_processo_cct'
                    acao_info['numero_cct'] = numero_documento_para_vincular
                elif tipo_documento_para_vincular == 'CE':
                    acao_info['acao'] = 'vincular_processo_ce'
                    acao_info['numero_ce'] = numero_documento_para_vincular
                elif tipo_documento_para_vincular == 'DI':
                    acao_info['acao'] = 'vincular_processo_di'
                    acao_info['numero_di'] = numero_documento_para_vincular
                elif tipo_documento_para_vincular == 'DUIMP':
                    acao_info['acao'] = 'vincular_processo_duimp'
                    acao_info['numero_duimp'] = numero_documento_para_vincular
                acao_info['processo_referencia'] = processo_para_vincular
                acao_info['confianca'] = 0.95
                acao_info['executar_automatico'] = True
                acao_info['pular_tool_calling'] = True
                logger.info(
                    f'✅ Vinculação de {tipo_documento_para_vincular} detectada - doc {numero_documento_para_vincular} será vinculado ao processo {processo_para_vincular}'
                )

        # ✅ Ajustar ação_info para DUIMP (confirmada)
        if ultima_ia_perguntou_criar_duimp and processo_para_criar_duimp:
            mensagem_lower = mensagem.lower().strip()
            eh_comando_novo_duimp_com_processo = bool(
                re.search(r'registr[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
                or re.search(r'cri[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
                or re.search(r'ger[ae]r?\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
                or re.search(r'fazer\s+duimp\s+(?:do\s+)?[a-z0-9]', mensagem_lower)
            )
            if not eh_comando_novo_duimp_com_processo:
                confirmacoes = [
                    r'^(?:sim|pode\s+prosseguir|prosseguir|confirmar|confirma|pode\s+criar|pode\s+registrar|ok|tudo\s+bem|vamos|pode|pode\s+ir|vai|faz|executar|executa)$',
                    r'^(?:sim|pode|ok|confirmo)$',
                ]
                eh_confirmacao = any(re.search(padrao, mensagem_lower) for padrao in confirmacoes)
            else:
                eh_confirmacao = False

            if eh_confirmacao and not eh_comando_novo_duimp_com_processo:
                acao_info['acao'] = 'criar_duimp'
                acao_info['processo_referencia'] = processo_para_criar_duimp
                acao_info['confianca'] = 0.95
                acao_info['executar_automatico'] = True
                acao_info['pular_tool_calling'] = True
                logger.info(
                    f'✅ Confirmação detectada - DUIMP será criada automaticamente para {processo_para_criar_duimp} (pulando tool calling)'
                )

        ctx = {
            'processo_ref': processo_ref,
            'categoria_atual': categoria_atual,
            'categoria_contexto': categoria_contexto,
            'numero_ce_contexto': numero_ce_contexto,
            'numero_cct': numero_cct,
            'contexto_processo': contexto_processo,
            'acao_info': acao_info,
            'eh_pergunta_generica': eh_pergunta_generica,
            'eh_pergunta_pendencias': eh_pergunta_pendencias,
            'eh_pergunta_situacao': eh_pergunta_situacao,
            'precisa_contexto': precisa_contexto,
            'eh_fechamento_dia': eh_fechamento_dia,
        }
        return None, ctx
    
    def processar_mensagem(
        self,
        mensagem: str,
        historico: Optional[List[Dict]] = None,
        usar_tool_calling: bool = True,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        nome_usuario: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processa mensagem do usuário e retorna resposta inteligente.
        
        Este é o método principal do serviço de chat. Ele:
        1. Analisa a mensagem do usuário
        2. Identifica a intenção (consulta, criação, vinculação, etc.)
        3. Executa ações apropriadas (tool calling)
        4. Retorna resposta formatada
        
        🔄 FLUXO DE PROCESSAMENTO:
        
        1. PRECHECK (Detecção Proativa)
           - Detecta perguntas sobre NCM → chama sugerir_ncm_com_ia diretamente
           - Detecta perguntas sobre chegada → chama listar_processos_por_eta
           - Detecta confirmações → executa ações pendentes (criar DUIMP, vincular, etc.)
        
        2. IDENTIFICAÇÃO DE AÇÃO
           - Extrai processo, categoria, documento da mensagem
           - Identifica tipo de ação (consulta, criação, vinculação)
           - Preserva contexto do histórico quando relevante
        
        3. CHAMADA DA IA
           - Constrói prompt com contexto e regras
           - Chama modelo de IA (GPT-3.5, GPT-4, etc.)
           - Processa tool calls retornados pela IA
        
        4. EXECUÇÃO DE FUNÇÕES
           - Executa cada função solicitada pela IA
           - Prioriza resultados de funções sobre texto da IA
           - Combina múltiplos resultados quando necessário
        
        5. RESPOSTA FINAL
           - Formata resposta com dados das funções
           - Adiciona contexto adicional quando necessário
           - Retorna estrutura padronizada
        
        Args:
            mensagem: Mensagem do usuário em linguagem natural
            historico: Histórico de mensagens anteriores (para contexto)
            usar_tool_calling: Se True, permite IA chamar funções (padrão: True)
            model: Modelo de IA a usar (opcional, usa padrão do ai_service)
            temperature: Temperatura para geração (0.0-2.0, opcional, padrão 0.5)
        
        Returns:
            Dict com:
            - 'resposta': Texto da resposta formatada
            - 'acao': Tipo de ação identificada (opcional)
            - 'tool_calls': Lista de funções chamadas (opcional)
            - 'erro': Código de erro se houver (opcional)
        """
        if not self.enabled:
            return {
                'resposta': 'Serviço de IA não está habilitado. Configure DUIMP_AI_ENABLED=true e DUIMP_AI_API_KEY no arquivo .env',
                'acao': None,
                'erro': 'IA_DESABILITADA'
            }
        
        historico = historico or []

        # ✅ Estabilização mínima: variáveis usadas antes de serem atribuídas
        # Evita UnboundLocalError (ex: `eh_pedido_melhorar_email` é usado na verificação de confirmação de email).
        eh_pedido_melhorar_email = False
        # ✅ Estabilização: variáveis/flags usadas ao longo do fluxo
        resposta_base_precheck = None
        precisa_contexto = False
        eh_fechamento_dia = False
        deve_chamar_ia_para_refinar = False
        email_para_melhorar_contexto = getattr(self, "_email_para_melhorar_contexto", None)
        tem_criar_duimp = False
        resposta_criar_duimp = None
        # ✅ CRÍTICO: sempre inicializar para evitar UnboundLocalError
        resposta_ia = None
        resposta_ia_raw = None
        ja_processou_pergunta_chegada_generica = False
        ja_processou_categoria_situacao = False
        resposta_ia_categoria_situacao = None
        
        # ✅ NOVO: Detectar comandos de interface ANTES de qualquer processamento
        # Permite que o usuário diga "maike menu" ou "maike quero conciliar banco" e abra diretamente
        comando_interface = self._detectar_comando_interface(mensagem)
        if comando_interface:
            logger.info(f"🎯 Comando de interface detectado: {comando_interface}")
            return {
                'resposta': f"✅ {comando_interface.get('tipo', 'comando')} detectado!",
                'comando_interface': comando_interface,  # ✅ Flag especial para o frontend
                'acao': 'comando_interface',
                'tool_calls': []
            }
        
        # ✅ NOVO: Armazenar nome do usuário e session_id para uso no prompt/contexto
        self.nome_usuario_atual = nome_usuario
        self.session_id_atual = session_id

        # ✅ Seleção automática de modelo (operacional x analítico x conhecimento geral) se caller não especificar
        model = self._selecionar_modelo_automatico(mensagem, model)
        
        # ✅ CRÍTICO: Verificar confirmação de email ANTES de qualquer outro processamento
        resultado_confirmacao_email, ultima_resposta_aguardando_email, dados_email_para_enviar = (
            self._processar_confirmacao_email_antes_precheck(
                mensagem=mensagem,
                historico=historico,
                session_id=session_id,
                eh_pedido_melhorar_email=eh_pedido_melhorar_email,
            )
        )
        if resultado_confirmacao_email:
            return resultado_confirmacao_email

        # ✅ CRÍTICO: Detectar correção de destinatário ANTES de "melhorar email" (evita colisões)
        resultado_correcao_email, eh_correcao_email_destinatario, dados_email_para_enviar = (
            self._processar_correcao_email_destinatario_antes_precheck(
                mensagem=mensagem,
                ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
                dados_email_para_enviar=dados_email_para_enviar,
                session_id=session_id,
            )
        )
        if resultado_correcao_email:
            return resultado_correcao_email

        # ✅ NOVO: Detectar se usuário está pedindo para melhorar/elaborar email em preview
        eh_pedido_melhorar_email = self._detectar_pedido_melhorar_email_preview(
            mensagem=mensagem,
            ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
            dados_email_para_enviar=dados_email_para_enviar,
            eh_correcao_email_destinatario=eh_correcao_email_destinatario,
        )

        # ✅ CRÍTICO (21/01/2026): Verificar confirmação de pagamento AFRMM ANTES de DUIMP
        # Prioridade: Pagamento AFRMM > DUIMP (porque pagamento é ação mais recente/urgente)
        if self.confirmation_handler and session_id:
            try:
                from services.pending_intent_service import get_pending_intent_service
                service = get_pending_intent_service()
                if service:
                    # Buscar pending intent de pagamento
                    pending_payment = service.buscar_pending_intent(session_id, action_type='payment')
                    if pending_payment:
                        mensagem_lower = mensagem.lower().strip()
                        # ✅ CORREÇÃO: Detecção determinística (exata match, não substring)
                        # Evita falso positivo: "simpático" contém "sim"
                        confirmacoes_exatas = {'sim', 'pagar', 'pode pagar', 'confirmar', 'confirma', 'ok', 'enviar', 'executar', 'pode enviar', 'pode'}
                        eh_confirmacao = mensagem_lower in confirmacoes_exatas
                        
                        if eh_confirmacao:
                            logger.info(f'✅✅✅ [CONFIRMACAO] Confirmação de pagamento AFRMM detectada (mensagem: "{mensagem}")')
                            resultado_pagamento = self.confirmation_handler.processar_confirmacao_pagamento_afrmm(
                                mensagem, session_id=session_id
                            )
                            if resultado_pagamento:
                                return resultado_pagamento
            except Exception as e:
                logger.debug(f'[ChatService] Erro ao processar confirmação de pagamento AFRMM: {e}')
        
        # ✅ CRÍTICO: Verificar confirmação de DUIMP DEPOIS de pagamento AFRMM
        resultado_confirmacao_duimp = self._processar_confirmacao_duimp_antes_precheck(
            mensagem=mensagem,
            historico=historico,
            session_id=session_id,
        )
        if resultado_confirmacao_duimp:
            return resultado_confirmacao_duimp

        # ✅ NOVO: Detectar comando para limpar contexto
        resultado_limpar_contexto = self._processar_comando_limpar_contexto_antes_precheck(
            mensagem=mensagem,
            session_id=session_id,
        )
        if resultado_limpar_contexto:
            return resultado_limpar_contexto
        
        # ✅ PRECHECK CENTRALIZADO: tentar responder sem IA (situação de processo, NCM, etc.)
        # ✅ CRÍTICO: NÃO executar precheck se há email em preview pendente (exceto confirmação/melhoria/correção já tratadas)
        # Isso evita que o precheck pegue contexto errado de outras conversas quando usuário está apenas corrigindo email
        resultado_precheck_imediato, resposta_base_precheck, deve_chamar_ia_para_refinar = (
            self._executar_precheck_centralizado(
                mensagem=mensagem,
                historico=historico,
                session_id=session_id,
                nome_usuario=nome_usuario,
                ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
                dados_email_para_enviar=dados_email_para_enviar,
                eh_correcao_email_destinatario=eh_correcao_email_destinatario,
            )
        )
        if resultado_precheck_imediato:
            return resultado_precheck_imediato
        
        # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar "o que temos pra hoje" ANTES de qualquer outra coisa
        mensagem_lower_precheck = mensagem.lower()

        resultado_precheck_forcado = self._processar_prechecks_forcados_alta_prioridade(
            mensagem=mensagem,
            mensagem_lower_precheck=mensagem_lower_precheck,
            session_id=session_id,
        )
        if resultado_precheck_forcado:
            return resultado_precheck_forcado

        resultado_ctx, ctx = self._resolver_contexto_processo_categoria_e_acao_antes_prompt(
            mensagem=mensagem,
            historico=historico,
            session_id=session_id,
        )
        if resultado_ctx:
            return resultado_ctx

        processo_ref = ctx.get('processo_ref')
        categoria_atual = ctx.get('categoria_atual')
        categoria_contexto = ctx.get('categoria_contexto')
        numero_ce_contexto = ctx.get('numero_ce_contexto')
        numero_cct = ctx.get('numero_cct')
        contexto_processo = ctx.get('contexto_processo')
        acao_info = ctx.get('acao_info', {})
        eh_pergunta_generica = ctx.get('eh_pergunta_generica', False)
        eh_pergunta_pendencias = ctx.get('eh_pergunta_pendencias', False)
        eh_pergunta_situacao = ctx.get('eh_pergunta_situacao', False)
        precisa_contexto = ctx.get('precisa_contexto', False)
        eh_fechamento_dia = ctx.get('eh_fechamento_dia', False)
        
        # 4. Construir prompt para a IA
        # ✅ PASSO 3.5 - FASE 3.5.1: Usar MessageProcessingService para construir prompt
        prompt_construido_via_mps = False
        system_prompt_mps = None
        user_prompt_mps = None
        usar_tool_calling_mps = None
        if self.message_processing_service:
            try:
                prompt_result = self.message_processing_service.construir_prompt_completo(
                    mensagem=mensagem,
                    historico=historico,
                    session_id=session_id,
                    nome_usuario=nome_usuario,
                    processo_ref=processo_ref,
                    categoria_atual=categoria_atual,
                    categoria_contexto=categoria_contexto,
                    numero_ce_contexto=numero_ce_contexto,
                    numero_cct=numero_cct,
                    contexto_processo=contexto_processo,
                    acao_info=acao_info,
                    resposta_base_precheck=resposta_base_precheck,
                    eh_pedido_melhorar_email=eh_pedido_melhorar_email,
                    email_para_melhorar_contexto=email_para_melhorar_contexto,
                    eh_pergunta_generica=eh_pergunta_generica,
                    eh_pergunta_pendencias=eh_pergunta_pendencias,
                    eh_pergunta_situacao=eh_pergunta_situacao,
                    precisa_contexto=precisa_contexto,
                    eh_fechamento_dia=eh_fechamento_dia,
                    extrair_processo_referencia_fn=self._extrair_processo_referencia
                )
                system_prompt_mps = prompt_result.get('system_prompt', '')
                user_prompt_mps = prompt_result.get('user_prompt', '')
                usar_tool_calling_mps = prompt_result.get('usar_tool_calling', True)
                system_prompt = system_prompt_mps
                user_prompt_base = user_prompt_mps
                usar_tool_calling = usar_tool_calling_mps
                prompt_construido_via_mps = True
                logger.info("✅ Prompt construído via MessageProcessingService")
            except Exception as e:
                logger.error(f"❌ Erro ao construir prompt via MessageProcessingService: {e}", exc_info=True)
                # Fallback para construção manual (código antigo)
                system_prompt = ""
                user_prompt_base = ""
                usar_tool_calling = True
        else:
            # Fallback: construção manual (código antigo mantido para compatibilidade)
            logger.warning("⚠️ MessageProcessingService não disponível - usando construção manual de prompt")
            system_prompt = ""
            user_prompt_base = ""
            usar_tool_calling = True

        # ✅ Fluxo principal: se MPS montou o prompt, não fazemos retrabalho legado
        if prompt_construido_via_mps:
            user_prompt = user_prompt_base
        else:
            # ✅ Fallback mínimo (só se MPS falhar/não existir): garantir que ainda chamamos a IA
            try:
                user_prompt = self.prompt_builder.build_user_prompt(
                    mensagem=mensagem,
                    contexto_str="",
                    historico_str="",
                    acao_info=acao_info,
                    contexto_sessao="",
                )
            except Exception:
                user_prompt = mensagem
            # manter tool calling ligado no fallback
            usar_tool_calling = True
        
        # 5. Chamar IA - ✅ NOVO: Com suporte a tool calling
        tools = None
        resultado_tool_calling = None
        
        # ✅ CRÍTICO: Se confirmação foi detectada, pular tool calling e retornar diretamente
        if acao_info.get('pular_tool_calling', False):
            acao_detectada = acao_info.get('acao')
            
            # Criar DUIMP
            if acao_detectada == 'criar_duimp':
                resposta_ia = f"✅ **Confirmado!** Criando DUIMP para o processo {acao_info.get('processo_referencia', 'N/A')}...\n\n"
                resposta_ia += "⏳ Aguarde enquanto a DUIMP é criada..."
                logger.info(f'✅ Confirmação detectada - pulando tool calling e retornando para execução direta')
                return {
                    'resposta': resposta_ia,
                    'acao': 'criar_duimp',
                    'processo_referencia': acao_info.get('processo_referencia'),
                    'contexto_processo': contexto_processo,
                    'confianca': acao_info.get('confianca', 0.95),
                    'executar_automatico': True,
                    'tool_calling': None
                }
            
            # Vincular CCT
            elif acao_detectada == 'vincular_processo_cct':
                numero_cct = acao_info.get('numero_cct')
                processo_ref = acao_info.get('processo_referencia')
                logger.info(f'✅ Vinculação de CCT detectada - executando diretamente: CCT {numero_cct} → Processo {processo_ref}')
                
                # ✅ CORREÇÃO: Normalizar número do CCT antes de executar
                # A API retorna sem hífen (ex: MIA4673), mas _extrair_numero_cct normaliza com hífen (MIA-4673)
                # Tentar ambos os formatos na função de vinculação
                # Executar vinculação diretamente
                resultado = self._executar_funcao_tool('vincular_processo_cct', {
                    'numero_cct': numero_cct,
                    'processo_referencia': processo_ref
                }, mensagem_original=mensagem)
                return {
                    'resposta': resultado.get('mensagem', resultado.get('resposta', f'✅ Processo {processo_ref} vinculado ao CCT {numero_cct} com sucesso!')),
                    'acao': None,  # Já executado
                    'sucesso': resultado.get('sucesso', False),
                    'tool_calling': None
                }
            
            # Vincular CE
            elif acao_detectada == 'vincular_processo_ce':
                numero_ce = acao_info.get('numero_ce')
                processo_ref = acao_info.get('processo_referencia')
                logger.info(f'✅ Vinculação de CE detectada - executando diretamente: CE {numero_ce} → Processo {processo_ref}')
                # Executar vinculação diretamente
                resultado = self._executar_funcao_tool('vincular_processo_ce', {
                    'numero_ce': numero_ce,
                    'processo_referencia': processo_ref
                }, mensagem_original=mensagem)
                return {
                    'resposta': resultado.get('mensagem', resultado.get('resposta', f'✅ Processo {processo_ref} vinculado ao CE {numero_ce} com sucesso!')),
                    'acao': None,  # Já executado
                    'sucesso': resultado.get('sucesso', False),
                    'tool_calling': None
                }
            
            # Vincular DI
            elif acao_detectada == 'vincular_processo_di':
                numero_di = acao_info.get('numero_di')
                processo_ref = acao_info.get('processo_referencia')
                logger.info(f'✅ Vinculação de DI detectada - executando diretamente: DI {numero_di} → Processo {processo_ref}')
                # Executar vinculação diretamente
                resultado = self._executar_funcao_tool('vincular_processo_di', {
                    'numero_di': numero_di,
                    'processo_referencia': processo_ref
                }, mensagem_original=mensagem)
                return {
                    'resposta': resultado.get('mensagem', resultado.get('resposta', f'✅ Processo {processo_ref} vinculado à DI {numero_di} com sucesso!')),
                    'acao': None,  # Já executado
                    'sucesso': resultado.get('sucesso', False),
                    'tool_calling': None
                }
            
            # Vincular DUIMP
            elif acao_detectada == 'vincular_processo_duimp':
                numero_duimp = acao_info.get('numero_duimp')
                processo_ref = acao_info.get('processo_referencia')
                logger.info(f'✅ Vinculação de DUIMP detectada - executando diretamente: DUIMP {numero_duimp} → Processo {processo_ref}')
                # Executar vinculação diretamente
                resultado = self._executar_funcao_tool('vincular_processo_duimp', {
                    'numero_duimp': numero_duimp,
                    'processo_referencia': processo_ref
                }, mensagem_original=mensagem)
                return {
                    'resposta': resultado.get('mensagem', resultado.get('resposta', f'✅ Processo {processo_ref} vinculado à DUIMP {numero_duimp} com sucesso!')),
                    'acao': None,  # Já executado
                    'sucesso': resultado.get('sucesso', False),
                    'tool_calling': None
                }
        elif usar_tool_calling:
            # ✅ CORREÇÃO: Inicializar tool_calls antes do try para evitar UnboundLocalError
            tool_calls = []
            try:
                from services.chat_service_forced_prechecks_toolcalling import tentar_prechecks_forcados_tool_calling

                resultado_forcado_precheck = tentar_prechecks_forcados_tool_calling(
                    chat_service=self,
                    mensagem=mensagem,
                    session_id=session_id,
                    logger_override=logger,
                )
                if resultado_forcado_precheck:
                    return resultado_forcado_precheck

                # `mensagem_lower_precheck` ainda é usada nos prechecks seguintes
                mensagem_lower_precheck = mensagem.lower()
                
                # ✅✅✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar comandos de criar/registrar DUIMP ANTES de qualquer outra coisa
                # Isso evita que "registrar duimp" seja interpretado como situação "registrado"
                # ✅ CORREÇÃO: Aceitar "registrar duimp do", "criar duimp do", etc.
                eh_comando_criar_duimp_precheck = bool(
                    re.search(r'registr[ae]r?\s+(?:a\s+)?(?:duimp|o\s+duimp)', mensagem_lower_precheck) or
                    re.search(r'registr[ae]r?\s+duimp\s+do', mensagem_lower_precheck) or  # ✅ "registrar duimp do"
                    re.search(r'cri[ae]r?\s+(?:a\s+)?duimp', mensagem_lower_precheck) or
                    re.search(r'cri[ae]r?\s+duimp\s+do', mensagem_lower_precheck) or  # ✅ "criar duimp do"
                    re.search(r'ger[ae]r?\s+(?:a\s+)?duimp', mensagem_lower_precheck) or
                    re.search(r'ger[ae]r?\s+duimp\s+do', mensagem_lower_precheck) or  # ✅ "gerar duimp do"
                    re.search(r'fazer\s+(?:a\s+)?duimp', mensagem_lower_precheck) or
                    re.search(r'fazer\s+duimp\s+do', mensagem_lower_precheck)  # ✅ "fazer duimp do"
                )
                
                if eh_comando_criar_duimp_precheck:
                    # Extrair processo da mensagem
                    processo_duimp = self._extrair_processo_referencia(mensagem)
                    if processo_duimp:
                        logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Comando de criar/registrar DUIMP detectado. Processo: {processo_duimp}. Pulando precheck de situação e deixando IA processar.')
                        # Não fazer nada aqui - deixar a IA processar normalmente
                        # O importante é que este precheck tenha prioridade sobre o de situação
                    else:
                        logger.warning(f'🚨🚨🚨 Comando de criar/registrar DUIMP detectado mas sem processo. Deixando IA processar.')
                
                # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar perguntas sobre "quais processos estão armazenados/desembaraçados/entregues" ANTES de qualquer outra coisa
                # mensagem_lower_precheck já foi definida acima
                # ⚠️ IMPORTANTE: Este precheck só deve rodar se NÃO for comando de criar DUIMP
                if not eh_comando_criar_duimp_precheck:
                    eh_pergunta_processos_situacao_precheck = bool(
                        re.search(r'quais\s+processos?\s+(?:est[ãa]o|estao|s[ãa]o|sao)\s+(?:armazenado|desembara[çc]ado|entregue|registrado)', mensagem_lower_precheck) or
                        re.search(r'listar\s+processos?\s+(?:armazenado|desembara[çc]ado|entregue|registrado)', mensagem_lower_precheck) or
                        re.search(r'mostre\s+processos?\s+(?:armazenado|desembara[çc]ado|entregue|registrado)', mensagem_lower_precheck) or
                        re.search(r'o\s+que\s+(?:desembara[çc]ou|desembaracou)', mensagem_lower_precheck) or  # ✅ "o que desembaracou hoje?"
                        re.search(r'quais\s+processos?\s+(?:desembara[çc]aram|desembaracaram|foram\s+desembara[çc]ados)', mensagem_lower_precheck) or  # ✅ "quais processos foram desembaracados hoje?"
                        re.search(r'quais\s+processos?\s+(?:est[ãa]o|estao)\s+desembara[çc]ados', mensagem_lower_precheck)  # ✅ "quais processos estão desembaracados hoje?"
                    )
                else:
                    eh_pergunta_processos_situacao_precheck = False
                
                situacao_detectada_precheck = None
                filtro_data_desembaraco_precheck = None  # ✅ NOVO: Filtro de data
                
                if eh_pergunta_processos_situacao_precheck:
                    if re.search(r'armazenado|armazenada', mensagem_lower_precheck):
                        situacao_detectada_precheck = 'armazenado'
                    elif re.search(r'desembara[çc]ado|desembara[çc]ada|desembara[çc]ou|desembaracou|desembara[çc]aram|desembaracaram|foram\s+desembara[çc]ados', mensagem_lower_precheck):
                        situacao_detectada_precheck = 'desembaraçado'
                        
                        # ✅ NOVO: Detectar filtro de data para desembaraço (verificar ANTES de detectar situação)
                        if re.search(r'\bhoje\b', mensagem_lower_precheck):
                            filtro_data_desembaraco_precheck = 'hoje'
                        elif re.search(r'\bontem\b', mensagem_lower_precheck):
                            filtro_data_desembaraco_precheck = 'ontem'
                        elif re.search(r'(?:esta|nesta)\s+semana', mensagem_lower_precheck):
                            filtro_data_desembaraco_precheck = 'semana'
                        elif re.search(r'(?:este|neste)\s+mes', mensagem_lower_precheck):
                            filtro_data_desembaraco_precheck = 'mes'
                    elif re.search(r'entregue', mensagem_lower_precheck):
                        situacao_detectada_precheck = 'entregue'
                    elif re.search(r'registrado|registrada', mensagem_lower_precheck) and not eh_comando_criar_duimp_precheck:
                        # ⚠️ IMPORTANTE: Só detectar "registrado" como situação se NÃO for comando de criar DUIMP
                        situacao_detectada_precheck = 'registrado'
                
                # ✅✅✅ CRÍTICO: Só executar precheck de situação se NÃO for comando de criar DUIMP
                # Isso evita que "registrar duimp do mv5.0022/25" seja interpretado como situação "registrado"
                if eh_pergunta_processos_situacao_precheck and situacao_detectada_precheck and not eh_comando_criar_duimp_precheck:
                    logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Pergunta sobre processos com situação "{situacao_detectada_precheck}" detectada. Filtro de data: {filtro_data_desembaraco_precheck or "nenhum"}. Chamando listar_todos_processos_por_situacao e retornando diretamente (SEM chamar IA).')
                    try:
                        args_tool = {
                            'situacao': situacao_detectada_precheck
                        }
                        # ✅ NOVO: Adicionar filtro de data se detectado
                        if filtro_data_desembaraco_precheck:
                            args_tool['filtro_data_desembaraco'] = filtro_data_desembaraco_precheck
                        
                        resultado_precheck = self._executar_funcao_tool('listar_todos_processos_por_situacao', args_tool, mensagem_original=mensagem)
                        
                        if resultado_precheck and resultado_precheck.get('resposta'):
                            logger.info(f'✅✅✅ Resposta forçada ANTES da IA (PROCESSOS POR SITUAÇÃO) - tamanho: {len(resultado_precheck.get("resposta"))}')
                            return {
                                'sucesso': True,
                                'resposta': resultado_precheck.get('resposta'),
                                'tool_calling': {'name': 'listar_todos_processos_por_situacao', 'arguments': {'situacao': situacao_detectada_precheck}},
                                '_processado_precheck': True
                            }
                        else:
                            logger.warning(f'❌ Resposta vazia ou inválida da tool listar_todos_processos_por_situacao para "{mensagem}". Prosseguindo com a IA.')
                    except Exception as e:
                        logger.error(f'❌ Erro ao forçar tool listar_todos_processos_por_situacao para "{mensagem}": {e}', exc_info=True)
                        # Se houver erro, deixar a IA tentar processar
                
                # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar perguntas sobre processos que chegaram ANTES de qualquer outra coisa
                # Isso garante que SEMPRE usemos listar_processos_liberados_registro para essas perguntas
                # mensagem_lower_precheck já foi definida acima
                
                # ✅⚠️⚠️⚠️ CRÍTICO: Detectar perguntas genéricas sobre processos que chegaram (sem categoria)
                # Padrões: "quais processos chegaram?", "quais processos chegou?", etc.
                # Isso é DIFERENTE de "quando chegam" (futuro) - "chegaram" é passado (processos que já chegaram sem DI/DUIMP)
                eh_pergunta_processos_chegaram_precheck = bool(
                    re.search(r'quais\s+processos?\s+chegaram', mensagem_lower_precheck) or
                    re.search(r'quais\s+processos?\s+chegou', mensagem_lower_precheck) or
                    re.search(r'processos?\s+que\s+chegaram', mensagem_lower_precheck)
                ) and not re.search(r'quando\s+chegaram', mensagem_lower_precheck)  # Excluir "quando chegaram" (que é sobre ETA futuro)
                
                # ✅⚠️⚠️⚠️ CRÍTICO: Detectar perguntas sobre "embarques que chegaram" (processos que chegaram sem DI/DUIMP)
                # Padrões: "quais os embarques GYM chegaram?", "quais embarques ALH chegaram?", etc.
                eh_pergunta_embarques_chegaram_precheck = bool(
                    re.search(r'quais\s+(?:os|as)?\s*embarques?\s+[a-z]{3}\s+chegaram', mensagem_lower_precheck) or
                    re.search(r'quais\s+embarques?\s+[a-z]{3}\s+chegaram', mensagem_lower_precheck) or
                    re.search(r'embarques?\s+[a-z]{3}\s+chegaram', mensagem_lower_precheck)
                )
                
                categoria_embarques_chegaram_precheck = None
                if eh_pergunta_embarques_chegaram_precheck:
                    # Extrair categoria da pergunta sobre embarques que chegaram
                    # Tentar vários padrões
                    match_embarques = (
                        re.search(r'embarques?\s+([a-z]{3})\s+chegaram', mensagem_lower_precheck) or
                        re.search(r'quais\s+(?:os|as)?\s*embarques?\s+([a-z]{3})\s+chegaram', mensagem_lower_precheck) or
                        re.search(r'quais\s+embarques?\s+([a-z]{3})\s+chegaram', mensagem_lower_precheck)
                    )
                    if match_embarques:
                        cat_candidata = match_embarques.group(1).upper()
                        palavras_ignorar = {'DOS', 'DAS', 'ESTAO', 'ESTÃO', 'COM', 'SÃO', 'SAO', 'TEM', 'TÊM', 'POR', 'QUE', 'QUAL', 'COMO', 'EST', 'PAR', 'UMA', 'UNS', 'TODOS', 'TODAS', 'TODO', 'TODA', 'OS', 'AS',
                                            'ESSA', 'ESTA', 'NESSA', 'NESTA',  # ✅ CRÍTICO: Ignorar "essa semana", "esta semana", "nessa semana", "nesta semana"
                                            'VEM', 'VÊM', 'SEMANA', 'PROXIMA', 'PRÓXIMA', 'MES', 'MÊS', 'DIA', 'DIAS', 'HOJE', 'AMANHA', 'AMANHÃ'}
                        if len(cat_candidata) == 3 and cat_candidata not in palavras_ignorar:
                            categoria_embarques_chegaram_precheck = cat_candidata
                    
                    # Se não encontrou categoria, tentar extrair de outra forma
                    if not categoria_embarques_chegaram_precheck:
                        categoria_embarques_chegaram_precheck = self._extrair_categoria_da_mensagem(mensagem)
                
                # ✅ "o que registramos 22/01" / "dia 22/01" / "em 22/01/26" — ano omitido = ano atual (27/01/2026)
                match_data_registramos = re.search(
                    r'(?:o\s+que|quais?)\s+(?:registramos|foi\s+registrado|foram\s+registrados)\s+(?:(?:dia|em|no\s+dia)\s*)?(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?=\D|$)',
                    mensagem_lower_precheck,
                )
                if match_data_registramos:
                    from datetime import date
                    dd, mm, yy_opt = match_data_registramos.group(1), match_data_registramos.group(2), match_data_registramos.group(3)
                    ano_eff = date.today().year if not yy_opt else (2000 + int(yy_opt)) if len(yy_opt) == 2 else int(yy_opt)
                    data_dd_mm_aaaa = f"{int(dd):02d}/{int(mm):02d}/{ano_eff}"
                    categoria_registrados = categoria_atual
                    logger.info(f'🔍 "O que registramos dia {data_dd_mm_aaaa}" detectado. Categoria: {categoria_registrados or "TODAS"}. Usando listar_processos_registrados_periodo(periodo_especifico).')
                    try:
                        resultado_forcado = self._executar_funcao_tool('listar_processos_registrados_periodo', {
                            'categoria': categoria_registrados.upper() if categoria_registrados else None,
                            'periodo': 'periodo_especifico',
                            'data_inicio': data_dd_mm_aaaa,
                            'data_fim': data_dd_mm_aaaa,
                            'limite': 200,
                        }, mensagem_original=mensagem)
                        if resultado_forcado and resultado_forcado.get('resposta'):
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado.get('resposta'),
                                'acao': 'listar_processos_registrados_periodo',
                                'tool_used': 'listar_processos_registrados_periodo',
                                'tool_calling': 'listar_processos_registrados_periodo',
                                'dados': resultado_forcado.get('dados'),
                                'precheck': True,
                                'precheck_tipo': 'registrados_dia_especifico'
                            }
                    except Exception as e:
                        logger.error(f'❌ Erro ao forçar listar_processos_registrados_periodo(dia={data_dd_mm_aaaa}) para "{mensagem}": {e}', exc_info=True)

                # ✅ COERÊNCIA COM DASHBOARD (27/01/2026): "o que registramos ontem" usa DOCUMENTO_ADUANEIRO.data_registro
                # (mesmo critério do "o que temos pra hoje" / DIs com Registro: DD/MM). Evita notificacoes_processos.criado_em.
                eh_pergunta_registrados_ontem_precheck = bool(
                    re.search(r'(?:o\s+que|quais?)\s+(?:registramos|foi\s+registrado|foram\s+registrados)\s+ontem', mensagem_lower_precheck) or
                    re.search(r'registramos\s+ontem|foi\s+registrado\s+ontem|foram\s+registrados\s+ontem', mensagem_lower_precheck)
                )
                if eh_pergunta_registrados_ontem_precheck:
                    categoria_registrados = categoria_atual
                    logger.info(f'🔍 "O que registramos ontem" detectado. Categoria: {categoria_registrados or "TODAS"}. Usando listar_processos_registrados_periodo(periodo=ontem).')
                    try:
                        resultado_forcado = self._executar_funcao_tool('listar_processos_registrados_periodo', {
                            'categoria': categoria_registrados.upper() if categoria_registrados else None,
                            'periodo': 'ontem',
                            'limite': 200,
                        }, mensagem_original=mensagem)
                        if resultado_forcado and resultado_forcado.get('resposta'):
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado.get('resposta'),
                                'acao': 'listar_processos_registrados_periodo',
                                'tool_used': 'listar_processos_registrados_periodo',
                                'tool_calling': 'listar_processos_registrados_periodo',
                                'dados': resultado_forcado.get('dados'),
                                'precheck': True,
                                'precheck_tipo': 'registrados_ontem'
                            }
                    except Exception as e:
                        logger.error(f'❌ Erro ao forçar listar_processos_registrados_periodo(ontem) para "{mensagem}": {e}', exc_info=True)

                # ✅⚠️⚠️⚠️ PRIORIDADE MÁXIMA ABSOLUTA: Detectar perguntas sobre "o que registramos hoje" ANTES de "pronto para registro"
                # Padrões: "o que registramos hoje?", "o que foi registrado hoje?", "quais processos foram registrados hoje?"
                eh_pergunta_registrados_hoje_precheck = bool(
                    re.search(r'(?:o\s+que|quais?)\s+(?:registramos|foi\s+registrado|foram\s+registrados|registramos)\s+hoje', mensagem_lower_precheck) or
                    re.search(r'registramos\s+hoje|foi\s+registrado\s+hoje|foram\s+registrados\s+hoje', mensagem_lower_precheck)
                )
                
                if eh_pergunta_registrados_hoje_precheck:
                    # ✅ COERÊNCIA (27/01/2026): "hoje" também usa listar_processos_registrados_periodo(periodo='hoje')
                    # para mesma fonte que "ontem" e dashboard: DOCUMENTO_ADUANEIRO.data_registro
                    categoria_registrados = categoria_atual
                    logger.info(f'🔍 "O que registramos hoje" detectado. Categoria: {categoria_registrados or "TODAS"}. Usando listar_processos_registrados_periodo(periodo=hoje).')
                    try:
                        resultado_forcado_registrados = self._executar_funcao_tool('listar_processos_registrados_periodo', {
                            'categoria': categoria_registrados.upper() if categoria_registrados else None,
                            'periodo': 'hoje',
                            'limite': 200,
                        }, mensagem_original=mensagem)
                        if resultado_forcado_registrados and resultado_forcado_registrados.get('resposta'):
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado_registrados.get('resposta'),
                                'acao': 'listar_processos_registrados_periodo',
                                'tool_used': 'listar_processos_registrados_periodo',
                                'tool_calling': 'listar_processos_registrados_periodo',
                                'dados': resultado_forcado_registrados.get('dados'),
                                'precheck': True,
                                'precheck_tipo': 'registrados_hoje'
                            }
                    except Exception as e:
                        logger.error(f'❌ Erro ao forçar listar_processos_registrados_periodo(hoje) para "{mensagem}": {e}', exc_info=True)
                
                # ✅⚠️⚠️⚠️ PRIORIDADE MÁXIMA ABSOLUTA: Detectar perguntas sobre "pronto para registro" ANTES de qualquer outra coisa
                # Padrões: "pronto para registro", "pronto pra registro", "precisam de registro", "precisam registrar", "precisam de di", "precisam de duimp", "chegaram sem despacho"
                # ✅ NOVO: Adicionar padrões para "o que temos pra registrar", "temos pra registrar", "quais temos pra registrar", etc.
                eh_pergunta_pronto_registro_precheck = bool(
                    re.search(
                        r'pronto[s]?\s+(?:para|pra)\s+registro'
                        r'|precisam\s+de\s+registro'
                        r'|precisam\s+registrar'
                        r'|precisam\s+de\s+di'
                        r'|precisam\s+de\s+duimp'
                        r'|chegaram\s+sem\s+despacho'
                        r'|est[ao]\s+pronto[s]?\s+(?:para|pra)\s+registro'
                        r'|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+(?:pra|para|de)\s+registrar'
                        r'|temos\s+(?:pra|para|de)\s+registrar'
                        r'|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+pra\s+registro'
                        r'|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+para\s+registro'
                        r'|posso\s+registrar\s+di\s+ou\s+duimp'
                        r'|posso\s+registrar\s+(?:di|duimp)'
                        r'|podemos\s+registrar\s+(?:di|duimp)'
                        r'|d[áa]\s+pra\s+registrar\s+(?:di|duimp)'
                        r'|da\s+para\s+registrar\s+(?:di|duimp)',
                        mensagem_lower_precheck,
                    )
                )
                
                if eh_pergunta_pronto_registro_precheck:
                    categoria_pronto_registro = categoria_atual
                    # ✅ Se menciona "hoje" ou "pra hoje", buscar todos os processos que chegaram até hoje (sem limite de dias)
                    # Caso contrário, usar 30 dias retroativos
                    menciona_hoje = bool(re.search(r'\bhoje\b|\bpra\s+hoje\b|\bpara\s+hoje\b', mensagem_lower_precheck))
                    dias_retroativos_pronto = None if menciona_hoje else 30
                    logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pergunta "pronto para registro" detectada. Categoria: {categoria_pronto_registro or "TODAS"}. Dias retroativos: {dias_retroativos_pronto or "sem limite (até hoje)"}. Usando listar_processos_liberados_registro.')
                    try:
                        resultado_forcado_pronto = self._executar_funcao_tool('listar_processos_liberados_registro', {
                            'categoria': categoria_pronto_registro.upper() if categoria_pronto_registro else None,
                            'dias_retroativos': dias_retroativos_pronto,
                            'limit': 200
                        }, mensagem_original=mensagem)
                        
                        if resultado_forcado_pronto and resultado_forcado_pronto.get('resposta'):
                            logger.info(f'✅✅✅ Resposta forçada ANTES da IA (pronto para registro) - tamanho: {len(str(resultado_forcado_pronto.get("resposta", "")))}')
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado_pronto.get('resposta'),
                                'acao': 'listar_processos_pronto_registro',
                                'tool_used': 'listar_processos_liberados_registro',
                                'tool_calling': 'listar_processos_liberados_registro',
                                'dados': resultado_forcado_pronto.get('dados'),
                                'precheck': True,
                                'precheck_tipo': 'pronto_para_registro'
                            }
                    except Exception as e:
                        logger.error(f'Erro ao executar listar_processos_liberados_registro no pre-check (pronto para registro): {e}', exc_info=True)
                
                # ✅ Se detectou pergunta genérica sobre processos que chegaram (sem categoria), usar listar_processos_liberados_registro imediatamente
                if eh_pergunta_processos_chegaram_precheck:
                    logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Pergunta genérica "quais processos chegaram?" detectada. Usando listar_processos_liberados_registro (sem categoria, apenas processos que chegaram sem DI/DUIMP).')
                    try:
                        resultado_forcado_chegaram = self._executar_funcao_tool('listar_processos_liberados_registro', {
                            'categoria': None,  # Sem categoria - buscar todos
                            'dias_retroativos': None,  # Sem limite de dias - buscar todos que chegaram até hoje
                            'limite': 200
                        }, mensagem_original=mensagem)
                        
                        if resultado_forcado_chegaram.get('resposta'):
                            logger.info(f'✅ Resposta forçada para "quais processos chegaram?" - tamanho: {len(resultado_forcado_chegaram.get("resposta"))}')
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado_chegaram.get('resposta'),
                                'tool_used': 'listar_processos_liberados_registro',
                                'tool_calling': 'listar_processos_liberados_registro',
                                'dados': resultado_forcado_chegaram.get('dados'),
                                'precheck': True,
                                'precheck_tipo': 'processos_chegaram'
                            }
                    except Exception as e:
                        logger.error(f'Erro ao executar listar_processos_liberados_registro no pre-check (processos chegaram): {e}', exc_info=True)
                        # Continuar processamento normal se der erro
                
                # ✅ Se detectou pergunta sobre embarques que chegaram, usar listar_processos_liberados_registro imediatamente
                if eh_pergunta_embarques_chegaram_precheck:
                    logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Pergunta sobre "embarques que chegaram" detectada. Categoria: {categoria_embarques_chegaram_precheck or "TODAS"}. Usando listar_processos_liberados_registro.')
                    try:
                        resultado_forcado_embarques = self._executar_funcao_tool('listar_processos_liberados_registro', {
                            'categoria': categoria_embarques_chegaram_precheck,
                            'dias_retroativos': 30,  # Usar 30 dias para garantir que encontra processos recentes
                            'limite': 200
                        }, mensagem_original=mensagem)
                        
                        if resultado_forcado_embarques.get('resposta'):
                            logger.info(f'✅ Resposta forçada para "embarques que chegaram" - tamanho: {len(resultado_forcado_embarques.get("resposta"))}')
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado_embarques.get('resposta'),
                                'tool_used': 'listar_processos_liberados_registro',
                                'tool_calling': 'listar_processos_liberados_registro',
                                'dados': resultado_forcado_embarques.get('dados'),
                                'precheck': True,
                                'precheck_tipo': 'embarques_chegaram'
                            }
                    except Exception as e:
                        logger.error(f'Erro ao executar listar_processos_liberados_registro no pre-check: {e}', exc_info=True)
                        # Continuar processamento normal se der erro
                
                # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar "como estão os [CATEGORIA]?" ANTES de qualquer outra coisa
                # Padrões: "como estão os dmd?", "como estao os alh?", "mostre os vdm", etc.
                eh_pergunta_como_estao_precheck = bool(
                    re.search(r'como\s+(?:estao|estão)\s+os\s+[a-z]{2,4}\b', mensagem_lower_precheck) or
                    re.search(r'mostre\s+os\s+[a-z]{2,4}\b', mensagem_lower_precheck) or
                    re.search(r'quais\s+(?:são|sao)\s+os\s+[a-z]{2,4}\b', mensagem_lower_precheck)
                )
                
                categoria_como_estao_precheck = None
                if eh_pergunta_como_estao_precheck:
                    categoria_como_estao_precheck = self._extrair_categoria_da_mensagem(mensagem)
                    if categoria_como_estao_precheck and len(categoria_como_estao_precheck) == 3:
                        # ✅ CORREÇÃO: Usar listar_processos_por_categoria mas com limite menor e apenas cache
                        # O formato do dashboard é apenas para "hoje", mas "como estão os BND" deve mostrar TODOS os ativos
                        logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Pergunta "como estão os {categoria_como_estao_precheck}?" detectada. Chamando listar_processos_por_categoria (apenas cache) e retornando diretamente (SEM chamar IA).')
                        try:
                            resultado_como_estao_precheck = self._executar_funcao_tool('listar_processos_por_categoria', {
                                'categoria': categoria_como_estao_precheck,
                                'limite': 50  # ✅ Limitar a 50 para evitar lentidão, mas mostrar todos os ativos
                            }, mensagem_original=mensagem)
                            
                            if resultado_como_estao_precheck.get('resposta'):
                                logger.info(f'✅ Resposta forçada para "como estão os {categoria_como_estao_precheck}?" - tamanho: {len(resultado_como_estao_precheck.get("resposta"))}')
                                return {
                                    'sucesso': True,
                                    'resposta': resultado_como_estao_precheck.get('resposta'),
                                    'tool_used': 'listar_processos_por_categoria',
                                    'tool_calling': 'listar_processos_por_categoria',
                                    'dados': resultado_como_estao_precheck.get('dados'),
                                    'precheck': True,
                                    'precheck_tipo': 'como_estao_categoria'
                                }
                            else:
                                logger.warning(f'❌ Resposta vazia da tool listar_processos_por_categoria para "{categoria_como_estao_precheck}". Prosseguindo com a IA.')
                        except Exception as e:
                            logger.error(f'❌ Erro ao executar listar_processos_por_categoria no pre-check: {e}', exc_info=True)
                            # Continuar processamento normal se der erro
                
                from services.chat_service_forced_precheck_extrato_processo import (
                    tentar_precheck_extrato_generico_por_processo,
                )

                resultado_extrato_generico = tentar_precheck_extrato_generico_por_processo(
                    chat_service=self,
                    mensagem=mensagem,
                    mensagem_lower_precheck=mensagem_lower_precheck,
                    logger_override=logger,
                )
                if resultado_extrato_generico:
                    return resultado_extrato_generico
                
                # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar "extrato da duimp" ANTES de qualquer outra coisa
                match_extrato_duimp = re.search(
                    r'extrato\s+(?:da\s+)?duimp\s+(?:do\s+)?([a-z]{3}\.?\d{1,4}/?\d{2})',
                    mensagem_lower_precheck
                ) or re.search(
                    r'pdf\s+(?:da\s+)?duimp\s+(?:do\s+)?([a-z]{3}\.?\d{1,4}/?\d{2})',
                    mensagem_lower_precheck
                ) or (
                    re.search(r'extrato\s+(?:da\s+)?duimp', mensagem_lower_precheck) and
                    self._extrair_processo_referencia(mensagem)
                )
                
                if match_extrato_duimp:
                    processo_extrato = None
                    # Tentar extrair processo do match
                    if match_extrato_duimp.lastindex and match_extrato_duimp.group(1):
                        processo_extrato = match_extrato_duimp.group(1).upper()
                    else:
                        # Tentar extrair processo da mensagem
                        processo_extrato = self._extrair_processo_referencia(mensagem)
                    
                    if processo_extrato:
                        logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Pedido de extrato PDF da DUIMP detectado. Processo: {processo_extrato}. Chamando obter_extrato_pdf_duimp e retornando diretamente (SEM chamar IA).')
                        try:
                            resultado_extrato_precheck = self._executar_funcao_tool('obter_extrato_pdf_duimp', {
                                'processo_referencia': processo_extrato
                            }, mensagem_original=mensagem)
                            
                            if resultado_extrato_precheck and isinstance(resultado_extrato_precheck, dict) and resultado_extrato_precheck.get('resposta'):
                                logger.info(f'✅✅✅ Resposta forçada ANTES da IA (EXTRATO PDF DUIMP) - tamanho: {len(resultado_extrato_precheck.get("resposta"))}')
                                return {
                                    'sucesso': True,
                                    'resposta': resultado_extrato_precheck.get('resposta'),
                                    'tool_calling': {'name': 'obter_extrato_pdf_duimp', 'arguments': {'processo_referencia': processo_extrato}},
                                    '_processado_precheck': True
                                }
                            else:
                                logger.warning(f'❌ Resposta vazia ou inválida da tool obter_extrato_pdf_duimp para "{mensagem}". Prosseguindo com a IA.')
                        except Exception as e:
                            logger.error(f'❌ Erro ao forçar tool obter_extrato_pdf_duimp para "{mensagem}": {e}', exc_info=True)
                            # Se houver erro, retornar mensagem de erro estruturada ao invés de deixar quebrar
                            return {
                                'sucesso': False,
                                'erro': 'ERRO_PRECheck_EXTRATO',
                                'resposta': f'❌ Erro ao processar extrato da DUIMP para {processo_extrato}: {str(e)}',
                                'mensagem': f'Erro ao processar extrato da DUIMP: {str(e)}'
                            }
                
                # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar "extrato da di" ANTES de qualquer outra coisa
                match_extrato_di = None
                processo_extrato_di_fallback = None
                
                # Tentar padrão 1: "extrato da di do processo ALH.0176/25" ou "extrato da di ALH.0176/25"
                match1 = re.search(
                    r'extrato\s+(?:da\s+)?di\s+(?:do\s+(?:processo\s+)?)?([a-z]{3}\.?\d{1,4}/?\d{2})',
                    mensagem_lower_precheck
                )
                if match1:
                    match_extrato_di = match1
                
                # Tentar padrão 2: "pdf da di do processo ALH.0176/25"
                if not match_extrato_di:
                    match2 = re.search(
                        r'pdf\s+(?:da\s+)?di\s+(?:do\s+(?:processo\s+)?)?([a-z]{3}\.?\d{1,4}/?\d{2})',
                        mensagem_lower_precheck
                    )
                    if match2:
                        match_extrato_di = match2
                
                # Tentar padrão 3: "extrato da di" + processo extraído separadamente
                if not match_extrato_di:
                    if re.search(r'extrato\s+(?:da\s+)?di', mensagem_lower_precheck):
                        processo_extrato_di_fallback = self._extrair_processo_referencia(mensagem)
                        if processo_extrato_di_fallback:
                            # Criar um match fake para manter compatibilidade
                            match_extrato_di = type('Match', (), {
                                'lastindex': 1,
                                'group': lambda self, n=0: processo_extrato_di_fallback if n == 1 else None
                            })()
                
                # Tentar padrão 4: número de DI direto (ex: "extrato da di 2524635120")
                if not match_extrato_di:
                    match4 = re.search(r'extrato\s+(?:da\s+)?di\s+(\d{10})', mensagem_lower_precheck)
                    if match4:
                        match_extrato_di = match4
                
                # Tentar padrão 5: "pdf da di" + número DI
                if not match_extrato_di:
                    match5 = re.search(r'pdf\s+(?:da\s+)?di\s+(\d{10})', mensagem_lower_precheck)
                    if match5:
                        match_extrato_di = match5
                
                if match_extrato_di:
                    processo_extrato_di = None
                    numero_di_extrato = None
                    
                    # Se já temos processo do fallback, usar diretamente
                    if processo_extrato_di_fallback:
                        processo_extrato_di = processo_extrato_di_fallback
                    else:
                        # Tentar extrair processo do match
                        try:
                            if hasattr(match_extrato_di, 'lastindex') and match_extrato_di.lastindex:
                                valor_extraido = match_extrato_di.group(1)
                                if valor_extraido:
                                    valor_extraido = valor_extraido.upper()
                                    # Verificar se é processo (tem ponto e barra) ou número DI (10 dígitos)
                                    if '.' in valor_extraido and '/' in valor_extraido:
                                        processo_extrato_di = valor_extraido
                                    elif valor_extraido.isdigit() and len(valor_extraido) == 10:
                                        numero_di_extrato = valor_extraido
                        except (AttributeError, IndexError, TypeError) as e:
                            logger.debug(f'Erro ao extrair processo do match_extrato_di: {e}')
                    
                    # Se não extraiu do match, tentar extrair processo da mensagem
                    if not processo_extrato_di and not numero_di_extrato:
                        processo_extrato_di = self._extrair_processo_referencia(mensagem)
                        
                        # Se não encontrou processo, tentar extrair número DI direto
                        if not processo_extrato_di:
                            match_numero_di = re.search(r'extrato\s+(?:da\s+)?di\s+(\d{10})', mensagem_lower_precheck) or \
                                             re.search(r'pdf\s+(?:da\s+)?di\s+(\d{10})', mensagem_lower_precheck) or \
                                             re.search(r'di\s+(\d{10})', mensagem_lower_precheck)
                            if match_numero_di:
                                numero_di_extrato = match_numero_di.group(1)
                    
                    if processo_extrato_di or numero_di_extrato:
                        logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Pedido de extrato PDF da DI detectado. Processo: {processo_extrato_di or "N/A"}, DI: {numero_di_extrato or "N/A"}. Chamando obter_extrato_pdf_di e retornando diretamente (SEM chamar IA).')
                        try:
                            args_extrato_di = {}
                            if processo_extrato_di:
                                args_extrato_di['processo_referencia'] = processo_extrato_di
                            if numero_di_extrato:
                                args_extrato_di['numero_di'] = numero_di_extrato
                            
                            resultado_extrato_di_precheck = self._executar_funcao_tool('obter_extrato_pdf_di', args_extrato_di, mensagem_original=mensagem)
                            
                            if resultado_extrato_di_precheck and isinstance(resultado_extrato_di_precheck, dict) and resultado_extrato_di_precheck.get('resposta'):
                                logger.info(f'✅✅✅ Resposta forçada ANTES da IA (EXTRATO PDF DI) - tamanho: {len(resultado_extrato_di_precheck.get("resposta"))}')
                                return {
                                    'sucesso': True,
                                    'resposta': resultado_extrato_di_precheck.get('resposta'),
                                    'tool_calling': {'name': 'obter_extrato_pdf_di', 'arguments': args_extrato_di},
                                    '_processado_precheck': True
                                }
                            else:
                                logger.warning(f'❌ Resposta vazia ou inválida da tool obter_extrato_pdf_di para "{mensagem}". Prosseguindo com a IA.')
                        except Exception as e:
                            logger.error(f'❌ Erro ao forçar tool obter_extrato_pdf_di para "{mensagem}": {e}', exc_info=True)
                            # Se houver erro, retornar mensagem de erro estruturada ao invés de deixar quebrar
                            return {
                                'sucesso': False,
                                'erro': 'ERRO_PRECheck_EXTRATO_DI',
                                'resposta': f'❌ Erro ao processar extrato da DI para {processo_extrato_di or numero_di_extrato or "processo desconhecido"}: {str(e)}',
                                'mensagem': f'Erro ao processar extrato da DI: {str(e)}'
                            }
                
                # ✅ REMOVIDO: Esta detecção já foi feita ANTES do dashboard_hoje (linha ~2307)
                # Não duplicar aqui para evitar conflitos
                    # Detectar se o usuário pediu agrupamento por categoria
                    pediu_agrupado_categoria = bool(
                        re.search(r'agrup', mensagem_lower_precheck)
                        and re.search(r'categoria', mensagem_lower_precheck)
                    )
                    if pediu_agrupado_categoria:
                        logger.warning(
                            '🚨🚨🚨 PRIORIDADE MÁXIMA: Pergunta de chegada na semana COM '
                            'agrupamento por categoria detectada. Usando camada analítica '
                            '(analytics_service).'
                        )
                        try:
                            from services.analytics_service import (
                                obter_chegadas_agrupadas_por_categoria,
                                formatar_resumo_chegadas_agrupadas_por_categoria,
                            )
                            dados_agrupados = obter_chegadas_agrupadas_por_categoria(
                                filtro_data='semana',
                                categoria=None,
                                limite=500,
                                incluir_passado=False,
                            )
                            resposta_agrupada = formatar_resumo_chegadas_agrupadas_por_categoria(
                                dados_agrupados,
                                'esta semana',
                            )
                            return {
                                'sucesso': True,
                                'resposta': resposta_agrupada,
                                'precheck': True,
                                'precheck_tipo': 'chegada_semana_agrupada_categoria',
                                'dados_agrupados': dados_agrupados,
                            }
                        except Exception as e:
                            logger.error(
                                f'❌ Erro ao executar analytics de chegadas agrupadas por categoria: {e}',
                                exc_info=True,
                            )
                            # Se der erro na camada analítica, cair para o comportamento antigo
                    logger.warning(
                        '🚨🚨🚨 PRIORIDADE MÁXIMA: Pergunta sobre chegada com período temporal detectada. '
                        'Usando listar_processos_por_eta com filtro "semana" (SEM categoria).'
                    )
                    try:
                        resultado_forcado_chegada_semana = self._executar_funcao_tool(
                            'listar_processos_por_eta',
                            {
                                'filtro_data': 'semana',  # Esta semana
                                'limite': 500,  # Limite maior para pegar mais processos
                            },
                            mensagem_original=mensagem,
                        )
                        
                        if resultado_forcado_chegada_semana.get('resposta'):
                            logger.info(
                                '✅ Resposta forçada para "quais processos chegam esta/essa semana?" - '
                                f'tamanho: {len(resultado_forcado_chegada_semana.get("resposta"))}'
                            )
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado_chegada_semana.get('resposta'),
                                'tool_used': 'listar_processos_por_eta',
                                'tool_calling': 'listar_processos_por_eta',
                                'dados': resultado_forcado_chegada_semana.get('dados'),
                                'precheck': True,
                                'precheck_tipo': 'chegada_semana',
                            }
                        else:
                            logger.warning(
                                '❌ Resposta vazia da tool listar_processos_por_eta para "esta semana". '
                                'Prosseguindo com a IA.'
                            )
                    except Exception as e:
                        logger.error(
                            f'❌ Erro ao executar listar_processos_por_eta no pre-check para "esta semana": {e}',
                            exc_info=True,
                        )
                        # Continuar processamento normal se der erro
                
                # ✅ APENAS se NÃO há período temporal específico, detectar como pergunta genérica sobre chegada
                eh_pergunta_generica_chegada_precheck = False
                categoria_chegada_generica_precheck = None

                # ✅ NOVO (ETA de processo específico): "quando chega o NTM.0001/26?"
                # Regra: se detectar processo + intenção de ETA/chegada, responder via listar_processos_por_eta(processo_referencia=...)
                # (mesmo pipeline do relatório de chegadas) antes de chamar IA.
                try:
                    processo_ref_eta_precheck = self._extrair_processo_referencia(mensagem)
                    if processo_ref_eta_precheck and bool(
                        re.search(r'\b(quando|qdo)\b.*\bcheg', mensagem_lower_precheck)
                        or re.search(r'\beta\b|\bprevis[aã]o\b|\bprevisao\b', mensagem_lower_precheck)
                    ):
                        logger.warning(
                            f'🚨 PRIORIDADE (ETA PROCESSO): Pergunta de ETA detectada para {processo_ref_eta_precheck}. '
                            'Chamando listar_processos_por_eta(processo_referencia=...) e retornando diretamente (SEM IA).'
                        )
                        try:
                            resultado_eta_proc = self._executar_funcao_tool(
                                'listar_processos_por_eta',
                                {
                                    'processo_referencia': processo_ref_eta_precheck,
                                    'limite': 1,
                                },
                                mensagem_original=mensagem,
                            )
                            if resultado_eta_proc and (resultado_eta_proc.get('resposta') or resultado_eta_proc.get('mensagem')):
                                return {
                                    'sucesso': True,
                                    'resposta': resultado_eta_proc.get('resposta') or resultado_eta_proc.get('mensagem'),
                                    'tool_calls': [],
                                    'mensagem_original': mensagem,
                                    '_processado_precheck': True,
                                }
                        except Exception as _e_eta:
                            logger.error(f'❌ Erro ao executar listar_processos_por_eta (processo_referencia) no precheck: {_e_eta}', exc_info=True)
                except Exception:
                    pass
                
                # ✅ CORREÇÃO (20/01/2026): variável pode não existir neste ramo (evitar NameError)
                if 'tem_periodo_temporal_especifico_precheck' not in locals():
                    tem_periodo_temporal_especifico_precheck = False

                if not tem_periodo_temporal_especifico_precheck:
                    eh_pergunta_generica_chegada_precheck = bool(re.search(
                        r'(?:quais|como|mostre)\s+(?:os|as|processos?)?\s*(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar|vai\s+chegar|vão\s+chegar)',
                        mensagem_lower_precheck
                    )) or bool(re.search(
                        r'quais\s+(?:os|as)?\s*[a-z]{3}\s+(?:que\s+)?(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar)',
                        mensagem_lower_precheck
                    )) or bool(re.search(
                        r'quais\s+[a-z]{3}\s+(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar)',
                        mensagem_lower_precheck
                    )) or bool(re.search(
                        r'o\s+que\s+tem\s+chegando|o\s+que\s+est[áa]\s+chegando|o\s+que\s+tem\s+pra\s+chegar',
                        mensagem_lower_precheck
                    ))
                    
                    if eh_pergunta_generica_chegada_precheck:
                        # Extrair categoria
                        categoria_chegada_generica_precheck = self._extrair_categoria_da_mensagem(mensagem)
                        if not categoria_chegada_generica_precheck:
                            match_cat_chegada_precheck = re.search(r'quais\s+(?:os|as)?\s*([a-z]{3})\s+(?:que\s+)?(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar)', mensagem_lower_precheck) or re.search(r'quais\s+([a-z]{3})\s+(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar)', mensagem_lower_precheck)
                            if match_cat_chegada_precheck:
                                cat_candidata_precheck = match_cat_chegada_precheck.group(1).upper()
                                palavras_ignorar_precheck = {'DOS', 'DAS', 'ESTAO', 'ESTÃO', 'COM', 'SÃO', 'SAO', 'TEM', 'TÊM', 'POR', 'QUE', 'QUAL', 'COMO', 'EST', 'PAR', 'UMA', 'UNS', 'TODOS', 'TODAS', 'TODO', 'TODA', 'OS', 'AS', 
                                                            'VEM', 'VÊM', 'SEMANA', 'PROXIMA', 'PRÓXIMA', 'MES', 'MÊS', 'DIA', 'DIAS', 'HOJE', 'AMANHA', 'AMANHÃ',
                                                            'ESSA', 'ESTA', 'NESSA', 'NESTA',  # ✅ CRÍTICO: Ignorar "essa semana", "esta semana", "nessa semana", "nesta semana"
                                                            'VAO', 'VÃO', 'IRÃO', 'IRAO', 'CHEGAM', 'CHEGA', 'CHEGAR', 'CHEGARA', 'CHEGARAM', 'PRA', 'PARA'}
                                if cat_candidata_precheck not in palavras_ignorar_precheck and len(cat_candidata_precheck) == 3:
                                    categoria_chegada_generica_precheck = cat_candidata_precheck
                
                # ✅ Se detectou pergunta genérica sobre chegada ANTES de chamar a IA, forçar uso de listar_processos_por_eta e retornar diretamente
                if eh_pergunta_generica_chegada_precheck:
                    logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pergunta genérica sobre chegada detectada ANTES de chamar IA. Categoria: {categoria_chegada_generica_precheck or "TODAS"}. Chamando listar_processos_por_eta com filtro "mes" (sem categoria) ou "futuro" (com categoria) e retornando diretamente (SEM chamar IA).')
                    try:
                        if categoria_chegada_generica_precheck:
                            resultado_forcado_precheck = self._executar_funcao_tool('listar_processos_por_eta', {
                                'filtro_data': 'futuro',  # ✅ ETA >= hoje, SEM limite de data final
                                'categoria': categoria_chegada_generica_precheck,
                                'limite': 200
                            }, mensagem_original=mensagem)
                        else:
                            resultado_forcado_precheck = self._executar_funcao_tool('listar_processos_por_eta', {
                                'filtro_data': 'mes',  # ✅ ETA neste mês (padrão para perguntas genéricas sem categoria)
                                'limite': 500
                            }, mensagem_original=mensagem)
                        
                        if resultado_forcado_precheck.get('resposta'):
                            logger.info(f'✅✅✅ Resposta forçada ANTES da IA (PERGUNTA GENÉRICA CHEGADA) - tamanho: {len(resultado_forcado_precheck.get("resposta"))}')
                            # ✅ CRÍTICO: Retornar diretamente, SEM chamar a IA
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado_precheck.get('resposta'),
                                'tool_calls': [],
                                'mensagem_original': mensagem,
                                '_processado_precheck': True  # Marcar que foi processado no precheck
                            }
                        elif resultado_forcado_precheck.get('mensagem'):
                            logger.info(f'✅✅✅ Mensagem forçada ANTES da IA (PERGUNTA GENÉRICA CHEGADA)')
                            return {
                                'sucesso': True,
                                'resposta': resultado_forcado_precheck.get('mensagem'),
                                'tool_calls': [],
                                'mensagem_original': mensagem,
                                '_processado_precheck': True
                            }
                    except Exception as e:
                        logger.error(f'❌ Erro ao forçar chamada ANTES da IA para pergunta genérica sobre chegada: {e}', exc_info=True)
                        # Continuar com processamento normal da IA se erro
                
                # ✅ PASSO 3.5 - FASE 3.5.2: Usar MessageProcessingService para chamar IA e processar tool calls
                if self.message_processing_service:
                    try:
                        # 1. Detectar busca direta NESH (antes de chamar IA)
                        resultado_busca_nesh = self.message_processing_service.detectar_busca_direta_nesh(
                            mensagem=mensagem,
                            executar_funcao_tool_fn=self._executar_funcao_tool
                        )
                        if resultado_busca_nesh:
                            logger.info("✅ Busca direta NESH detectada - retornando resultado sem chamar IA")
                            return resultado_busca_nesh
                        
                        # 2. Chamar IA com tools
                        resposta_ia_raw = self.message_processing_service.chamar_ia_com_tools(
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            usar_tool_calling=usar_tool_calling,
                            mensagem=mensagem,
                            model=model,
                            temperature=temperature
                        )
                        
                        # 3. Processar tool calls
                        resultado_tool_calls = self.message_processing_service.processar_tool_calls(
                            resposta_ia_raw=resposta_ia_raw,
                            mensagem=mensagem,
                            usar_tool_calling=usar_tool_calling,
                            session_id=session_id,
                            executar_funcao_tool_fn=self._executar_funcao_tool,
                            response_formatter=self._response_formatter if hasattr(self, '_response_formatter') else None
                        )
                        
                        # Extrair resultados
                        resposta_final = resultado_tool_calls.get('resposta_final', '')
                        tool_calls = resultado_tool_calls.get('tool_calls_executados', [])
                        ultima_resposta_aguardando_email = resultado_tool_calls.get('ultima_resposta_aguardando_email')
                        ultima_resposta_aguardando_duimp = resultado_tool_calls.get('ultima_resposta_aguardando_duimp')
                        
                        # Atualizar estado do chat_service
                        if ultima_resposta_aguardando_email:
                            self.ultima_resposta_aguardando_email = ultima_resposta_aguardando_email
                        if ultima_resposta_aguardando_duimp:
                            self.ultima_resposta_aguardando_duimp = ultima_resposta_aguardando_duimp
                        
                        logger.info("✅ Tool calls processados via MessageProcessingService")
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar via MessageProcessingService: {e}", exc_info=True)
                        # Fallback para código antigo
                        resposta_final = ""
                        tool_calls = []
                else:
                    # Fallback: código antigo (manter para compatibilidade)
                    logger.warning("⚠️ MessageProcessingService não disponível - usando código antigo")
                    from services.chat_service_toolcalling_legacy_fallback import executar_toolcalling_legado_sem_mps

                    resultado_legado = executar_toolcalling_legado_sem_mps(
                        chat_service=self,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        mensagem=mensagem,
                        session_id=session_id,
                        model=model,
                        temperature=temperature,
                        acao_info=acao_info,
                        logger_override=logger,
                    )

                    resposta_final = resultado_legado.get('resposta_final', '')
                    tool_calls = resultado_legado.get('tool_calls', []) or []
                    resultados_tools = resultado_legado.get('resultados_tools', []) or []
                    resposta_ia_texto = resultado_legado.get('resposta_ia_texto', '') or ''
                    acao_info = resultado_legado.get('acao_info', acao_info) or acao_info
                    
                    from services.chat_service_legacy_toolcalls_proactive_fixes import aplicar_fixes_pos_toolcalls_legacy

                    tool_calls, resultados_tools, acao_info = aplicar_fixes_pos_toolcalls_legacy(
                        chat_service=self,
                        mensagem=mensagem,
                        tool_calls=tool_calls,
                        resultados_tools=resultados_tools,
                        acao_info=acao_info,
                        categoria_atual=categoria_atual,
                        logger_override=logger,
                    )
                    
                    # Se houve tool calls, usar resposta dos tools
                    resposta_criar_duimp = None  # ✅ Definir no escopo correto
                    tem_criar_duimp = False  # ✅ Definir no escopo correto
                    resposta_ia = None  # ✅ CRÍTICO: Inicializar antes de usar
                    if resultados_tools:
                        # ✅ MELHORIA: Se for criar_duimp, não mostrar mensagem de outras funções
                        # A resposta será atualizada após execução no endpoint com resultado real
                        tem_criar_duimp = any(
                            tc['function']['name'] == 'criar_duimp' 
                            for tc in tool_calls
                        )
                        
                        if tem_criar_duimp:
                            # ✅ NOVO: Para criar_duimp, usar a resposta da função (com informações do processo)
                            # A função criar_duimp retorna informações detalhadas do processo para mostrar antes de criar
                            
                            # Buscar resposta da função criar_duimp (contém informações do processo)
                            for i, resultado in enumerate(resultados_tools):
                                # Verificar se este resultado é da função criar_duimp
                                # Comparar com o tool_call correspondente
                                if i < len(tool_calls):
                                    tool_call_nome = tool_calls[i]['function']['name']
                                    if tool_call_nome == 'criar_duimp' and resultado.get('resposta'):
                                        resposta_criar_duimp = resultado.get('resposta', '')
                                        break
                            
                            # Usar resposta da função criar_duimp se encontrada, senão usar resposta da IA
                            if resposta_criar_duimp:
                                resposta_ia = resposta_criar_duimp
                            else:
                                resposta_ia = resposta_ia_texto if resposta_ia_texto else '📋 Preparando informações para criar DUIMP...'
                        else:
                            # ✅ CORREÇÃO: Para outras funções, priorizar resposta das funções sobre texto da IA
                            # Se a função retornou uma resposta, usar essa resposta diretamente
                            # A resposta textual da IA (como "vou verificar...") não deve ser mostrada
                            resposta_ia = ''
                            
                            # ✅ NOVO: Verificar se algum resultado indica que precisa vincular processo
                            precisa_vincular = False
                            numero_ce_para_vincular = None
                            
                            # ✅ PRIORIDADE CRÍTICA: Se há resultado_forcado (da detecção proativa), usar ele primeiro e ignorar outros
                            resultado_forcado_lista = [r for r in resultados_tools if r.get('_forcado')]
                            logger.info(f'🔍 Verificando resultados forçados: total_resultados={len(resultados_tools)}, resultados_forcados={len(resultado_forcado_lista)}')
                            if resultado_forcado_lista:
                                # Usar apenas resultado forçado (detecção proativa)
                                resultado_forcado = resultado_forcado_lista[0]
                                logger.info(f'✅✅✅ PRIORIDADE MÁXIMA: Usando resultado forçado (detecção proativa) sobre outras tool_calls e resposta da IA')
                                if resultado_forcado.get('resposta'):
                                    resposta_ia = resultado_forcado.get('resposta')
                                    logger.info(f'✅✅✅ RESPOSTA FINAL: Usando resposta da função forçada (tamanho: {len(resposta_ia)}, primeiros 150 chars: {resposta_ia[:150]})')
                                elif resultado_forcado.get('mensagem'):
                                    resposta_ia = resultado_forcado.get('mensagem')
                                    logger.info(f'✅✅✅ RESPOSTA FINAL: Usando mensagem da função forçada (tamanho: {len(resposta_ia)})')
                                else:
                                    logger.warning(f'⚠️ Resultado forçado não tem resposta nem mensagem. resultado_forcado={resultado_forcado}')
                            else:
                                logger.info(f'ℹ️ Nenhum resultado forçado encontrado. Processando resultados normalmente. Total de resultados: {len(resultados_tools)}')
                                # Processar resultados normalmente
                                for i, resultado in enumerate(resultados_tools):
                                    func_name = tool_calls[i]['function']['name'] if i < len(tool_calls) else 'desconhecida'
                                    logger.info(f'🔍 Processando resultado da função {func_name}: sucesso={resultado.get("sucesso")}, tem_resposta={bool(resultado.get("resposta"))}, tem_mensagem={bool(resultado.get("mensagem"))}')
                                    
                                    # ✅ PRIORIDADE: Usar resposta da função, não texto da IA
                                    if resultado.get('resposta'):
                                        if resposta_ia:
                                            resposta_ia += '\n\n'
                                        resposta_ia += resultado.get('resposta', '')
                                        logger.info(f'✅ Adicionando resposta da função {func_name} à resposta final (tamanho: {len(resultado.get("resposta", ""))})')
                                    elif resultado.get('mensagem'):
                                        if resposta_ia:
                                            resposta_ia += '\n\n'
                                        resposta_ia += resultado.get('mensagem', '')
                                        logger.info(f'✅ Adicionando mensagem da função {func_name} à resposta final')
                                    
                                    # Verificar se precisa vincular processo
                                    if resultado.get('precisa_vincular_processo'):
                                        precisa_vincular = True
                                        # Tentar extrair número do CE da resposta ou dos dados
                                        if resultado.get('dados'):
                                            # O número do CE pode estar no contexto da função consultar_ce_maritimo
                                            # Vamos adicionar instrução para a IA perguntar
                                            pass
                            
                            logger.info(f'🔍 Resposta final após processar resultados: tamanho={len(resposta_ia)}, usando_texto_ia={not resposta_ia}')
                            
                            # ✅ CRÍTICO: Se não há resposta mas há resultados_tools, usar a primeira resposta disponível
                            if not resposta_ia or len(resposta_ia.strip()) == 0:
                                if resultados_tools:
                                    logger.warning(f'⚠️ Nenhuma resposta construída, mas há {len(resultados_tools)} resultado(s) de tools. Tentando usar primeiro resultado...')
                                    primeiro_resultado = resultados_tools[0]
                                    if primeiro_resultado.get('resposta'):
                                        resposta_ia = primeiro_resultado.get('resposta')
                                        logger.info(f'✅ Usando resposta do primeiro resultado (tamanho: {len(resposta_ia)})')
                                    elif primeiro_resultado.get('mensagem'):
                                        resposta_ia = primeiro_resultado.get('mensagem')
                                        logger.info(f'✅ Usando mensagem do primeiro resultado')
                                    elif primeiro_resultado.get('erro'):
                                        resposta_ia = f"❌ Erro: {primeiro_resultado.get('erro')}"
                                    if primeiro_resultado.get('mensagem'):
                                        resposta_ia += f" - {primeiro_resultado.get('mensagem')}"
                                    logger.warning(f'⚠️ Primeiro resultado contém erro: {primeiro_resultado.get("erro")}')
                            
                            # ✅ Se nenhuma função retornou resposta, usar texto da IA como fallback
                            # ⚠️ CRÍTICO: Só usar fallback se realmente não há resposta das funções
                            # ✅ NOVO: Se veio do precheck para refinar, SEMPRE priorizar resposta da IA sobre funções
                            if deve_chamar_ia_para_refinar and resposta_ia_texto:
                                # Precheck pediu para IA refinar - usar resposta da IA mesmo se funções retornaram algo
                                logger.info(f'✅✅✅ Precheck pediu refinamento pela IA - usando resposta da IA (tamanho: {len(resposta_ia_texto)}) sobre resultados de funções')
                                resposta_ia = resposta_ia_texto
                            elif not resposta_ia or len(resposta_ia.strip()) == 0:
                                logger.warning(f'⚠️ Nenhuma função retornou resposta (resposta_ia está vazia), usando texto da IA como fallback: {resposta_ia_texto[:100] if resposta_ia_texto else "None"}')
                                resposta_ia = resposta_ia_texto if resposta_ia_texto else ''
                            else:
                                logger.info(f'✅✅✅ Resposta das funções encontrada (tamanho: {len(resposta_ia)}), IGNORANDO texto da IA')
                            
                            # Se precisa vincular, adicionar instrução explícita na resposta da IA
                            if precisa_vincular and not resposta_ia_texto:
                                # A resposta já deve ter sido formatada pela função consultar_ce_maritimo
                                # A IA deve interpretar isso e perguntar ao usuário
                                pass
                        
                        resultado_tool_calling = {
                            'tool_calls': tool_calls,
                            'resultados': resultados_tools
                        }
                        
                        # Combinar resultados das tools
                        resposta_ia = self._combinar_resultados_tools(resultados_tools, resposta_ia_texto)
                        
                        # ✅ NOVO: Se criar_duimp foi chamada, garantir que a resposta da função seja incluída
                        if tem_criar_duimp and resposta_criar_duimp:
                            # A resposta já foi definida acima, mas garantir que está correta
                            if not resposta_ia or resposta_ia == resposta_ia_texto:
                                resposta_ia = resposta_criar_duimp
                    else:
                        # Resposta normal (string) - mas pode ser que a IA deveria ter chamado uma função
                        logger.info(f'⚠️ Resposta da IA é string, não dict (não há tool calls). Resposta: {str(resposta_ia_raw)[:200] if resposta_ia_raw else "None"}')
                        
                        # ✅ CRÍTICO: Garantir resposta_ia inicializada
                        if resposta_ia is None:
                            resposta_ia = resposta_ia_raw
                        
                        # ✅ NOVO: Se veio do precheck para refinar, usar resposta da IA diretamente
                        if deve_chamar_ia_para_refinar and resposta_ia_raw:
                            logger.info(f'✅✅✅ Precheck pediu refinamento pela IA - usando resposta da IA diretamente (tamanho: {len(str(resposta_ia_raw))})')
                            resposta_ia = str(resposta_ia_raw)
                    
                    # ✅ DETECÇÃO PROATIVA: Se a mensagem pergunta sobre processos de uma categoria ou genérico, forçar chamada da função
                    from services.chat_service_no_toolcalls_proactive_detection import (
                        aplicar_deteccao_proativa_sem_toolcalls,
                    )

                    resultado_proativo = aplicar_deteccao_proativa_sem_toolcalls(
                        chat_service=self,
                        mensagem=mensagem,
                        tool_calls=tool_calls,
                        resposta_ia_raw=resposta_ia_raw,
                        resposta_ia=resposta_ia,
                        deve_chamar_ia_para_refinar=deve_chamar_ia_para_refinar,
                        ja_processou_categoria_situacao=ja_processou_categoria_situacao,
                        resposta_ia_categoria_situacao=resposta_ia_categoria_situacao,
                        logger_override=logger,
                    )
                    resposta_ia = resultado_proativo.get("resposta_ia", resposta_ia)
                    ja_processou_categoria_situacao = resultado_proativo.get(
                        "ja_processou_categoria_situacao",
                        ja_processou_categoria_situacao,
                    )
                    resposta_ia_categoria_situacao = resultado_proativo.get(
                        "resposta_ia_categoria_situacao",
                        resposta_ia_categoria_situacao,
                    )
            except Exception as e:
                logger.error(f'❌ Erro ao usar tool calling, usando fallback: {e}', exc_info=True)
                # Fallback para chamada normal
                resposta_ia = self.ai_service._call_llm_api(user_prompt, system_prompt, model=model, temperature=temperature)
        else:
            # Chamada normal sem tool calling
            resposta_ia = self.ai_service._call_llm_api(user_prompt, system_prompt, model=model, temperature=temperature)
        
        # ✅ CRÍTICO: Verificar se já processou categoria+situação e preservar resposta
        if ja_processou_categoria_situacao and resposta_ia_categoria_situacao:
            if not resposta_ia or len(resposta_ia) < 50:
                # Se resposta_ia foi sobrescrita ou está vazia, restaurar resposta da categoria+situação
                resposta_ia = resposta_ia_categoria_situacao
                logger.warning(f'⚠️⚠️⚠️ Resposta de categoria+situação foi sobrescrita! Restaurando resposta (tamanho: {len(resposta_ia)})')
        
        # ✅ Limpar frases problemáticas (remover "pode mandar o email" etc.)
        if resposta_ia:
            resposta_ia_antes_limpeza = resposta_ia[:200] if len(resposta_ia) > 200 else resposta_ia
            resposta_ia = self._limpar_frases_problematicas(resposta_ia)
            resposta_ia_depois_limpeza = resposta_ia[:200] if len(resposta_ia) > 200 else resposta_ia
            if resposta_ia_antes_limpeza != resposta_ia_depois_limpeza:
                logger.info(f'✅ Frases problemáticas removidas. Antes: "{resposta_ia_antes_limpeza[:100]}...", Depois: "{resposta_ia_depois_limpeza[:100]}..."')
        
        # ✅ NOVO: Garantir que o nome do usuário seja usado na resposta se disponível
        if hasattr(self, 'nome_usuario_atual') and self.nome_usuario_atual and resposta_ia:
            nome = self.nome_usuario_atual
            # Verificar se o nome já está na resposta (case-insensitive)
            resposta_lower = resposta_ia.lower()
            nome_lower = nome.lower()
            if nome_lower not in resposta_lower:
                # Nome não está na resposta - adicionar de forma natural
                # Se a resposta não começa com saudação, adicionar
                if not resposta_ia.strip().startswith(('Olá', 'Oi', 'Olá,', 'Oi,', 'Bom', 'Boa')):
                    resposta_ia = f"Olá, {nome}! 👋\n\n{resposta_ia}"
                else:
                    # Se já tem saudação mas não tem o nome, tentar adicionar o nome
                    # Substituir "Olá!" por "Olá, {nome}!" se possível
                    resposta_ia = re.sub(r'^(Olá|Oi)(!|,|\.)', rf'\1, {nome}\2', resposta_ia, count=1, flags=re.IGNORECASE)
        
        if not resposta_ia:
            # Fallback: resposta detalhada sem IA
            if processo_ref and contexto_processo and contexto_processo.get('encontrado'):
                resposta_ia = f"📋 **Processo {processo_ref}**\n\n"
                
                # ✅ MELHORIA: Informações sobre DUIMP se houver
                # ✅ CRÍTICO: Verificar DUIMP de PRODUÇÃO primeiro
                duimp_info = contexto_processo.get('duimp', {})
                ambiente_duimp_info = duimp_info.get('ambiente', '').lower() if duimp_info.get('ambiente') else ''
                eh_producao_info = duimp_info.get('eh_producao', False) or ambiente_duimp_info == 'producao'
                
                if duimp_info.get('existe') and eh_producao_info:
                    # ✅ Encontrou DUIMP de PRODUÇÃO
                    resposta_ia += f"📋 **DUIMP {duimp_info.get('numero', 'N/A')}** v{duimp_info.get('versao', 'N/A')}\n"
                    resposta_ia += f"   - Situação: {duimp_info.get('situacao', duimp_info.get('status', 'N/A'))}\n"
                    resposta_ia += f"   - Ambiente: Produção\n"
                    if duimp_info.get('criado_em'):
                        resposta_ia += f"   - Criada em: {duimp_info.get('criado_em')}\n"
                    resposta_ia += "\n"
                elif duimp_info.get('existe') and not eh_producao_info:
                    # ✅ Existe DUIMP mas é de validação (apenas informação adicional)
                    resposta_ia += f"⚠️ **DUIMP de PRODUÇÃO:** Não encontrada para este processo.\n\n"
                    resposta_ia += f"ℹ️ **Informação adicional (ambiente de testes):**\n"
                    resposta_ia += f"   - DUIMP {duimp_info.get('numero', 'N/A')} v{duimp_info.get('versao', 'N/A')} (Validação - apenas testes)\n\n"
                else:
                    # ✅ Não encontrou DUIMP de produção nem validação
                    resposta_ia += f"⚠️ **DUIMP de PRODUÇÃO:** Não encontrada para este processo.\n\n"
                
                # Informações sobre CEs
                ces = contexto_processo.get('ces', [])
                if ces:
                    resposta_ia += "**📦 Conhecimentos de Embarque (CE):**\n\n"
                    for ce in ces:
                        resposta_ia += f"**CE {ce.get('numero', 'N/A')}**\n"
                        
                        situacao = ce.get('situacao', '')
                        if situacao:
                            resposta_ia += f"✅ Situação: **{situacao}**\n"
                        else:
                            resposta_ia += f"⚠️ Situação: Não informada\n"
                        
                        if ce.get('data_situacao'):
                            resposta_ia += f"📅 Data da situação: {ce.get('data_situacao')}\n"
                        
                        bloqueios_ativos = ce.get('bloqueios_ativos', 0)
                        bloqueios_baixados = ce.get('bloqueios_baixados', 0)
                        carga_bloqueada = ce.get('carga_bloqueada', False)
                        
                        if carga_bloqueada or bloqueios_ativos > 0:
                            resposta_ia += f"🚫 **ATENÇÃO:** Carga bloqueada ou com bloqueios ativos!\n"
                            resposta_ia += f"   - Bloqueios ativos: {bloqueios_ativos}\n"
                            resposta_ia += f"   - Bloqueios baixados: {bloqueios_baixados}\n"
                        elif bloqueios_baixados > 0:
                            resposta_ia += f"✅ Bloqueios: {bloqueios_baixados} baixado(s) (sem bloqueios ativos)\n"
                        else:
                            resposta_ia += f"✅ Sem bloqueios\n"
                        
                        if ce.get('pais_procedencia'):
                            resposta_ia += f"🌍 País de procedência: {ce.get('pais_procedencia')}\n"
                        if ce.get('ul_destino_final'):
                            resposta_ia += f"📍 UL Destino Final: {ce.get('ul_destino_final')}\n"
                        
                        resposta_ia += "\n"
                
                # Informações sobre CCTs
                ccts = contexto_processo.get('ccts', [])
                if ccts:
                    resposta_ia += "**Conhecimentos de Carga Aérea (CCT):**\n"
                    for cct in ccts:
                        ruc = cct.get('ruc', '') or cct.get('numero', 'N/A')
                        resposta_ia += f"• RUC {ruc}\n"
                        if cct.get('situacao'):
                            resposta_ia += f"  - Situação: {cct.get('situacao')}\n"
                        if cct.get('data_situacao'):
                            resposta_ia += f"  - Data da situação: {cct.get('data_situacao')}\n"
                        bloqueios_ativos = cct.get('bloqueios_ativos', 0)
                        bloqueios_baixados = cct.get('bloqueios_baixados', 0)
                        if bloqueios_ativos > 0 or bloqueios_baixados > 0:
                            resposta_ia += f"  - Bloqueios: {bloqueios_ativos} ativo(s), {bloqueios_baixados} baixado(s)\n"
                        if cct.get('aeroporto_origem'):
                            resposta_ia += f"  - Aeroporto de origem: {cct.get('aeroporto_origem')}\n"
                        if cct.get('pais_procedencia'):
                            resposta_ia += f"  - País de procedência: {cct.get('pais_procedencia')}\n"
                        resposta_ia += "\n"
                
                if not ces and not ccts:
                    resposta_ia += "⚠️ Nenhum CE ou CCT encontrado para este processo.\n"
            else:
                resposta_ia = "Desculpe, não consegui processar sua mensagem. Tente reformular ou verifique se o processo existe."
        
        # ✅ CRÍTICO: Verificação final - se processou categoria+situação, garantir que a resposta seja preservada
        if ja_processou_categoria_situacao and resposta_ia_categoria_situacao:
            # Se a resposta atual é muito curta ou é a resposta genérica da IA, substituir pela resposta da função
            if not resposta_ia or len(resposta_ia) < 100 or 'Entendi' in resposta_ia or 'Vou buscar' in resposta_ia:
                resposta_ia = resposta_ia_categoria_situacao
                logger.warning(f'⚠️⚠️⚠️ Resposta foi sobrescrita! Restaurando resposta de categoria+situação (tamanho: {len(resposta_ia)})')
        
        # ✅ NOVO: Verificação final - garantir que o nome do usuário seja usado na resposta
        if hasattr(self, 'nome_usuario_atual') and self.nome_usuario_atual and resposta_ia:
            nome = self.nome_usuario_atual
            resposta_lower = resposta_ia.lower()
            nome_lower = nome.lower()
            # Se o nome não está na resposta, adicionar de forma natural
            if nome_lower not in resposta_lower:
                # Tentar adicionar o nome de forma natural no início ou durante a resposta
                if not resposta_ia.strip().startswith(('Olá', 'Oi', 'Olá,', 'Oi,', 'Bom', 'Boa', '✅', '📋', '⚠️', '❌')):
                    # Resposta não começa com saudação - adicionar
                    resposta_ia = f"Olá, {nome}! 👋\n\n{resposta_ia}"
                elif resposta_ia.strip().startswith(('Olá', 'Oi')):
                    # Já tem saudação mas sem nome - adicionar nome
                    resposta_ia = re.sub(r'^(Olá|Oi)(!|,|\.|\s)', rf'\1, {nome}\2 ', resposta_ia, count=1, flags=re.IGNORECASE)
        
        # ✅ CRÍTICO: Determinar origem da resposta final (IA ou precheck)
        origem_resposta = 'ia' if not resposta_base_precheck or deve_chamar_ia_para_refinar else 'precheck'
        
        if resposta_ia:
            resumo_txt = resposta_ia[:120]
        else:
            resumo_txt = 'vazia'
            
        if deve_chamar_ia_para_refinar and resposta_ia:
            logger.info(
                f"[CHAT] ✅ Resposta final escolhida | origem=ia (refinada) | session_id={session_id} | "
                f"resumo='{resumo_txt}...'"
            )
        elif resposta_base_precheck and not deve_chamar_ia_para_refinar:
            # Precheck retornou resposta final sem precisar de IA
            resposta_ia = resposta_base_precheck
            logger.info(
                f"[CHAT] ✅ Resposta final escolhida | origem=precheck | session_id={session_id} | "
                f"resumo='{resumo_txt}...'"
            )
        else:
            # Resposta veio da IA normalmente
            logger.info(
                f"[CHAT] ✅ Resposta final escolhida | origem=ia | session_id={session_id} | "
                f"resumo='{resumo_txt}...'"
            )
        
        # ✅ REFATORADO (09/01/2026): Usar EmailImprovementHandler para processar melhoria de email
        if ultima_resposta_aguardando_email and dados_email_para_enviar and eh_pedido_melhorar_email:
            logger.info(f'✅✅✅ [MELHORAR EMAIL] Processando resposta da IA usando EmailImprovementHandler...')
            
            if self.email_improvement_handler:
                try:
                    resultado = self.email_improvement_handler.processar_resposta_melhorar_email(
                        resposta_ia=resposta_ia,
                        dados_email_original=dados_email_para_enviar,
                        session_id=session_id or (hasattr(self, 'session_id_atual') and self.session_id_atual) or 'default',
                        ultima_resposta_aguardando_email=self.ultima_resposta_aguardando_email
                    )
                    
                    if resultado.get('sucesso'):
                        # Atualizar estado com dados atualizados do handler
                        self.ultima_resposta_aguardando_email = resultado.get('dados_email_atualizados', dados_email_para_enviar)
                        resposta_ia = resultado.get('resposta', resposta_ia)
                        logger.info(f'✅✅✅ [MELHORAR EMAIL] Handler processou com sucesso - draft_id: {resultado.get("draft_id")}, revision: {resultado.get("revision")}')
                    else:
                        # Handler não conseguiu processar (extração falhou, etc.)
                        resposta_ia = resultado.get('resposta', resposta_ia)
                        logger.warning(f'⚠️⚠️⚠️ [MELHORAR EMAIL] Handler retornou sucesso=False: {resultado.get("erro")}')
                        
                except Exception as e:
                    logger.error(f'❌ [MELHORAR EMAIL] Erro ao usar EmailImprovementHandler: {e}', exc_info=True)
                    # Fallback: manter resposta original da IA
            else:
                logger.warning(f'⚠️⚠️⚠️ [MELHORAR EMAIL] EmailImprovementHandler não disponível - usando método antigo como fallback')
                # Fallback para método antigo se handler não estiver disponível
                try:
                    email_refinado = self._extrair_email_da_resposta_ia(resposta_ia, dados_email_para_enviar)
                    if email_refinado:
                        # Atualização básica (sem banco)
                        dados_email_para_enviar['assunto'] = email_refinado.get('assunto', dados_email_para_enviar.get('assunto'))
                        dados_email_para_enviar['conteudo'] = email_refinado.get('conteudo', dados_email_para_enviar.get('conteudo'))
                        self.ultima_resposta_aguardando_email = dados_email_para_enviar
                except Exception as e:
                    logger.error(f'❌ [MELHORAR EMAIL] Erro no fallback: {e}', exc_info=True)
        
        # ✅ NOVO: Adicionar indicador de fonte quando resposta vem apenas do conhecimento do modelo (sem tool calls)
        if resposta_ia:
            # Verificar se não há tool calls (resposta veio apenas do conhecimento do modelo)
            tem_tool_calls = (
                resultado_tool_calling is not None and 
                resultado_tool_calling and 
                resultado_tool_calling.get('tool_calls') and 
                len(resultado_tool_calling.get('tool_calls', [])) > 0
            )
            
            # Verificar se a resposta já tem indicador de fonte (vem de tool)
            tem_indicador_fonte = (
                '🔍 **FONTE:' in resposta_ia or 
                '✅ **Fonte:' in resposta_ia or
                'FONTE: Responses API' in resposta_ia or
                'FONTE: Busca Local' in resposta_ia
            )
            
            # Se não tem tool calls e não tem indicador de fonte, adicionar
            # MAS: Se é preview de email refinado, NÃO adicionar indicador de fonte
            eh_preview_email_refinado = '📧 **Preview do Email' in resposta_ia or 'Preview do Email (Atualizado)' in resposta_ia
            
            # ✅ CORREÇÃO (10/01/2026): Não mostrar indicador de fonte para respostas simples/conversacionais
            # Verificar se é resposta simples (teste, oi, ok, etc.) ou muito curta (< 100 caracteres)
            eh_resposta_simples = (
                len(resposta_ia) < 100 or
                mensagem.lower().strip() in ['teste', 'enviar teste', 'oi', 'ok', 'tudo bem', 'beleza'] or
                'teste' in mensagem.lower() and len(mensagem.split()) <= 3
            )
            
            if not tem_tool_calls and not tem_indicador_fonte and not eh_preview_email_refinado and not eh_resposta_simples:
                indicador_fonte = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                indicador_fonte += "🔍 **FONTE: Conhecimento do Modelo (GPT-4o)**\n"
                indicador_fonte += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                indicador_fonte += "💡 Esta resposta foi gerada com base no conhecimento geral do modelo GPT-4o.\n"
                indicador_fonte += "⚠️ **Nota:** Para informações específicas de legislação ou processos, use ferramentas de busca.\n"
                indicador_fonte += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                resposta_ia = resposta_ia + indicador_fonte
        
        return {
            'resposta': resposta_ia,
            'acao': acao_info.get('acao'),
            'processo_referencia': processo_ref or acao_info.get('processo_referencia'),
            'contexto_processo': contexto_processo,
            'confianca': acao_info.get('confianca', 0.5),
            'executar_automatico': acao_info.get('executar_automatico', False),
            'tool_calling': resultado_tool_calling,  # ✅ NOVO: Informações sobre tool calling usado
            '_origem_resposta': origem_resposta  # ✅ NOVO: Flag indicando origem da resposta
        }


    def _extrair_email_da_resposta_ia(self, resposta_ia: str, dados_email_original: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        ⚠️ DEPRECATED: Este método está mantido apenas como fallback.
        A lógica foi movida para EmailImprovementHandler._extrair_email_da_resposta_ia().
        
        Este método será removido após validação completa da integração do handler.
        
        Args:
            resposta_ia: Resposta da IA (pode conter preview de email ou texto livre)
            dados_email_original: Dados do email original em preview
            
        Returns:
            Dict com 'assunto' e 'conteudo' refinados, ou None se não conseguir extrair
        """
        from services.chat_service_email_extraction_fallback import extrair_email_da_resposta_ia_fallback
        return extrair_email_da_resposta_ia_fallback(
            resposta_ia=resposta_ia,
            dados_email_original=dados_email_original,
            logger_override=logger,
        )

    def gerar_mensagem_proativa(self, tipo: str, dados: Dict[str, Any]) -> Optional[str]:
        """
        Gera mensagem proativa da IA baseada no tipo de alerta.
        Faz parecer natural, como se fosse uma pessoa ajudando.
        
        Args:
            tipo: Tipo do alerta ('bloqueio', 'pendencia_frete', 'pendencia_afrmm', 'situacao_mudou', etc)
            dados: Dados do processo/documento para contexto
        
        Returns:
            Mensagem formatada para o usuário ou None se erro
        """
        try:
            processo_ref = dados.get('processo_referencia', '')
            documento_tipo = dados.get('documento_tipo', '')
            documento_numero = dados.get('documento_numero', '')
            
            # Gerar mensagens naturais baseadas no tipo
            if tipo == 'bloqueio':
                ce_numero = documento_numero or 'N/A'
                mensagem = f"⚠️ **Detectei um bloqueio no {documento_tipo} {ce_numero}** do processo **{processo_ref}**.\n\n"
                mensagem += "Quer que eu verifique os detalhes do bloqueio para você?"
                
            elif tipo == 'pendencia_frete':
                ce_numero = documento_numero or 'N/A'
                mensagem = f"💰 **Pendência de frete detectada** no {documento_tipo} {ce_numero} do processo **{processo_ref}**.\n\n"
                mensagem += "Isso pode impedir o desembaraço. Quer que eu investigue mais?"
                
            elif tipo == 'pendencia_afrmm':
                ce_numero = documento_numero or 'N/A'
                mensagem = f"⚓ **Pendência de AFRMM** no {documento_tipo} {ce_numero} do processo **{processo_ref}**.\n\n"
                mensagem += "O AFRMM ainda não foi pago. Quer ver mais detalhes?"
                
            elif tipo == 'situacao_mudou':
                situacao_nova = dados.get('situacao_nova', 'N/A')
                situacao_anterior = dados.get('situacao_anterior', 'N/A')
                mensagem = f"📋 **Mudança detectada no processo {processo_ref}**.\n\n"
                mensagem += f"Situação mudou de **{situacao_anterior}** para **{situacao_nova}**.\n\n"
                mensagem += "Quer que eu verifique o status atual completo?"
                
            elif tipo == 'pendencia_resolvida':
                tipo_pendencia = dados.get('tipo_pendencia', 'pendência')
                mensagem = f"✅ **Ótima notícia!** A {tipo_pendencia} do processo **{processo_ref}** foi resolvida.\n\n"
                mensagem += "O processo pode prosseguir normalmente."
                
            elif tipo == 'duimp_pronta':
                duimp_numero = documento_numero or 'N/A'
                mensagem = f"🎯 **DUIMP {duimp_numero} está pronta para registro!**\n\n"
                mensagem += f"O processo **{processo_ref}** tem todos os dados necessários. Quer que eu faça o diagnóstico antes de registrar?"
                
            else:
                # Fallback genérico
                mensagem = f"📢 **Atualização no processo {processo_ref}**.\n\n"
                mensagem += f"Detectei uma mudança do tipo **{tipo}**. Quer que eu verifique os detalhes?"
            
            return mensagem
            
        except Exception as e:
            logger.error(f'Erro ao gerar mensagem proativa: {e}')
            return None
    
# Instância global
_chat_service = None

def get_chat_service() -> ChatService:
    """Retorna instância singleton do serviço de chat."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service

