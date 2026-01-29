"""
Serviço de precheck especializado em comandos de envio de email.

Este serviço centraliza toda a lógica de detecção e processamento de comandos
de envio de email, organizando os diferentes tipos de email em uma hierarquia
clara de prioridades.
"""
import re
import logging
from typing import Optional, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from services.chat_service import ChatService

logger = logging.getLogger(__name__)


class EmailPrecheckService:
    """
    Serviço de precheck especializado em comandos de envio de email.
    
    Hierarquia de decisão (ordem de prioridade):
    1. Email de classificação NCM + alíquotas (requer contexto de NCM)
    2. Email de relatório genérico (dashboard, "o que temos pra hoje", etc.)
    3. Email de resumo/briefing específico
    4. Email livre (texto ditado pelo usuário)
    5. Email com informações de processo/NCM misturado
    """
    
    def __init__(self, chat_service: "ChatService"):
        """Inicializa o serviço de precheck de email."""
        self.chat_service = chat_service
    
    def tentar_precheck_email(
        self,
        mensagem: str,
        mensagem_lower: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        nome_usuario: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Tenta processar comandos de envio de email.
        
        Ordem de prioridade:
        1. Email pessoal/amoroso/informal (IGNORA contexto anterior)
        2. Email de NCM + alíquotas
        3. Email de relatório genérico
        4. Email de resumo/briefing
        5. Email livre
        6. Email de processo/NCM misturado
        """
        # ✅ NOVO: Detectar emails pessoais/amorosos/informais PRIMEIRO
        # Se detectar, IGNORAR TODO contexto anterior e deixar IA processar normalmente
        palavras_email_pessoal = [
            'amoroso', 'amorosa', 'amor', 'carinhoso', 'carinhosa', 'carinho',
            'convite', 'convidar', 'convidando', 'convidando para',
            'almocar', 'almoçar', 'almoco', 'almoço', 'cafe', 'café', 'lanche',
            'jantar', 'jantar com', 'encontrar', 'encontro', 'saida', 'saída',
            'pessoal', 'pessoalmente', 'informal', 'casual'
        ]
        
        tem_email_pessoal = any(palavra in mensagem_lower for palavra in palavras_email_pessoal)
        
        if tem_email_pessoal:
            logger.info(f"[EMAIL_PRECHECK] ✅ Email pessoal/amoroso/informal detectado - IGNORANDO contexto anterior e deixando IA processar")
            # Retornar None para deixar IA processar normalmente (sem contexto de NCM/processo)
            return None
        historico = historico or []
        # ✅ NOVO: Salvar histórico para uso em outros métodos
        self._ultimo_historico_verificado = historico
        
        # Garantir que mensagem_lower está normalizada
        if not mensagem_lower:
            mensagem_lower = mensagem.lower().strip()
        
        # ✅ CRÍTICO: Verificar "mandar esse relatório" ANTES da verificação genérica de email
        # Isso permite detectar comandos como "envie esse raltatorio acima para X" mesmo sem "email" explícito
        eh_comando_esse_relatorio = self._parece_comando_mandar_esse_relatorio(mensagem_lower)
        
        # ✅✅✅ FLAG CRÍTICA (14/01/2026): Indica se encontrou relatório visível
        # Se True, NÃO deve processar como NCM mesmo que tenha contexto de NCM
        tem_relatorio_visivel = False
        
        if eh_comando_esse_relatorio:
            # É comando "mandar esse relatório" - processar diretamente (não precisa ter "email" na mensagem)
            logger.debug(f"[EMAIL_PRECHECK] Comando 'mandar esse relatório' detectado na verificação inicial - processando")
            
            # ✅✅✅ CRÍTICO (14/01/2026): Quando detectar "esse relatorio", verificar PRIMEIRO se há relatório visível
            # ANTES de verificar contexto de NCM. Se houver relatório visível, processar como relatório.
            # Isso evita que contexto de NCM antigo interfira quando há um relatório visível na tela.
            if session_id:
                try:
                    from services.report_service import obter_last_visible_report_id, buscar_relatorio_por_id, _detectar_dominio_por_mensagem
                    
                    # Detectar domínio e buscar last_visible_report_id
                    dominio_detectado = _detectar_dominio_por_mensagem(mensagem)
                    last_visible = obter_last_visible_report_id(session_id, dominio=dominio_detectado)
                    
                    if last_visible and last_visible.get('id'):
                        # Há relatório visível - processar como relatório (PRIORIDADE MÁXIMA)
                        relatorio_salvo = buscar_relatorio_por_id(session_id, last_visible['id'])
                        if relatorio_salvo and relatorio_salvo.texto_chat:
                            tem_relatorio_visivel = True  # ✅ FLAG: Tem relatório visível
                            logger.info(f"[EMAIL_PRECHECK] ✅✅✅ Relatório visível encontrado (ID: {last_visible['id']}) - PRIORIZANDO relatório sobre contexto de NCM")
                            # Processar como relatório ad hoc (que vai usar o report_id correto)
                            resposta_relatorio_adhoc = self._precheck_envio_email_relatorio_adhoc(
                                mensagem=mensagem,
                                mensagem_lower=mensagem_lower,
                                historico=historico,
                                session_id=session_id,
                            )
                            if resposta_relatorio_adhoc is not None:
                                return resposta_relatorio_adhoc
                        else:
                            logger.warning(f"[EMAIL_PRECHECK] ⚠️ last_visible_report_id encontrado mas relatório não foi encontrado no banco - continuando verificação normal")
                except Exception as e:
                    logger.warning(f"[EMAIL_PRECHECK] ⚠️ Erro ao verificar relatório visível: {e} - continuando verificação normal")
            
            # ✅ Fase 2C (14/01/2026): Se NÃO encontrou relatório visível, ainda assim pode ser
            # "envie isso/esse relatório" referindo-se à ÚLTIMA resposta do chat (ex: legislação).
            # Nessa situação, não devemos "cair" para comportamento aleatório (ex: extrato bancário).
            # Se houver email na mensagem, montar um preview usando a última resposta do assistente como base.
            if not tem_relatorio_visivel:
                resposta_ultimo_texto = self._precheck_envio_email_esse_relatorio_sem_report(
                    mensagem=mensagem,
                    mensagem_lower=mensagem_lower,
                    historico=historico,
                    session_id=session_id,
                )
                if resposta_ultimo_texto is not None:
                    return resposta_ultimo_texto
        else:
            # Verificar se é comando de email genérico (verbo + "email")
            tem_verbo_email = any(v in mensagem_lower for v in [
                'manda', 'mandar', 'mande', 'envia', 'envie', 'enviar',
                'monte', 'prepare', 'crie', 'montar', 'preparar', 'criar'
            ])
            tem_token_email = 'email' in mensagem_lower
            
            if not (tem_verbo_email and tem_token_email):
                return None
        
        # 1) Email de classificação NCM + alíquotas (PRIORIDADE MÁXIMA - mas só se NÃO tiver relatório visível)
        # ✅✅✅ CRÍTICO: Se tem relatório visível, NÃO processar como NCM mesmo que tenha contexto de NCM
        if not tem_relatorio_visivel:
            resposta_ncm = self._precheck_envio_email_ncm(
                mensagem=mensagem,
                mensagem_lower=mensagem_lower,
                historico=historico,
                session_id=session_id,
                nome_usuario=nome_usuario,
            )
            if resposta_ncm is not None:
                return resposta_ncm
        else:
            logger.info(f"[EMAIL_PRECHECK] ✅✅✅ Relatório visível detectado - PULANDO verificação de NCM para evitar conflito")
        
        # 2) ✅ CRÍTICO: Email de relatório analítico ad hoc (ANTES do genérico - PRIORIDADE MÁXIMA para "esse relatorio")
        # Isso garante que "envie esse relatorio" sempre use enviar_relatorio_email quando há [REPORT_META:...]
        # Nota: Se já foi processado acima (quando detectou "esse relatorio" com relatório visível), não vai processar novamente
        if not eh_comando_esse_relatorio:  # Só processar se não foi processado acima
            resposta_relatorio_adhoc = self._precheck_envio_email_relatorio_adhoc(
                mensagem=mensagem,
                mensagem_lower=mensagem_lower,
                historico=historico,
                session_id=session_id,
            )
            if resposta_relatorio_adhoc is not None:
                return resposta_relatorio_adhoc
        
        # 3) Email de relatório genérico
        resposta_relatorio = self._precheck_envio_email_relatorio_generico(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            historico=historico,
            session_id=session_id,
        )
        if resposta_relatorio is not None:
            return resposta_relatorio
        
        # 4) Email de resumo/briefing específico
        resposta_resumo = self._precheck_envio_email(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            historico=historico,
            session_id=session_id,
        )
        if resposta_resumo is not None:
            return resposta_resumo
        
        # 4) Email livre (texto ditado)
        resposta_livre = self._precheck_envio_email_livre(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            session_id=session_id,
        )
        if resposta_livre is not None:
            return resposta_livre
        
        # 5) Email de processo/NCM misturado (fallback)
        resposta_processo = self._precheck_envio_email_processo(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            historico=historico,
            session_id=session_id,
        )
        if resposta_processo is not None:
            return resposta_processo
        
        return None
    
    def _precheck_envio_email_ncm(
        self,
        mensagem: str,
        mensagem_lower: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        nome_usuario: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Precheck para comandos de envio de email de classificação NCM + alíquotas.
        
        Detecta padrões como:
        - "mande o email para helenomaffra@gmail.com com as alíquotas explicando o porquê do ncm do caderno sugerido"
        - "envia email para X com as alíquotas"
        - "mande email para Y explicando o ncm"
        
        Regras:
        - Só processa se houver contexto de ultima_classificacao_ncm
        - Usa EnviarEmailClassificacaoNcmUseCase
        - Sempre mostra preview primeiro
        """
        # ✅ CORREÇÃO (10/01/2026): Verificar se é "esse relatorio" ANTES de bloquear
        # Se for "esse relatorio" e houver contexto de NCM, deve processar como email de NCM
        eh_esse_relatorio = self._parece_comando_mandar_esse_relatorio(mensagem_lower)
        
        # ✅ CORREÇÃO: Verificar se NÃO é relatório genérico, processo ou email pessoal/livre
        # Lista expandida de palavras que indicam email pessoal/genérico (NÃO é email de NCM)
        palavras_bloqueio = [
            'resumo', 'briefing', 'dashboard', 'fechamento',
            'processo', 'alh', 'vdm', 'mss', 'bnd', 'dmd', 'gym', 'sll', 'mv5',
            'dizendo que', 'informando que', 'avisando', 'aviso', 'reuniao', 'reunião',
            'jantar', 'jantar com', 'romantica', 'romântica', 'romantico', 'romântico',
            'noite', 'essa noite', 'hoje a noite', 'pessoal', 'pessoalmente',
            'convite', 'convidar', 'encontrar', 'encontro', 'saida', 'saída',
            'amoroso', 'amorosa', 'amor', 'carinhoso', 'carinhosa', 'carinho',
            'almocar', 'almoçar', 'almoco', 'almoço', 'cafe', 'café', 'lanche',
            'hoje', 'amanha', 'amanhã', 'agora', 'depois', 'mais tarde'
        ]
        
        # ✅ CORREÇÃO CRÍTICA (10/01/2026): "relatorio" só bloqueia se NÃO for "esse relatorio"
        # Se for "esse relatorio", permitir processar (será verificado se há contexto de NCM depois)
        if not eh_esse_relatorio:
            palavras_bloqueio.append('relatorio')
            palavras_bloqueio.append('relatório')
        
        tem_palavra_bloqueio = any(palavra in mensagem_lower for palavra in palavras_bloqueio)
        tem_palavra_ncm = any(palavra in mensagem_lower for palavra in [
            'ncm', 'aliquotas', 'alíquotas', 'classificacao', 'classificação', 'nesh',
            'tecwin', 'explicando o porque', 'explicando o porquê', 'explicando porque',
            'explicando porquê', 'justificativa', 'justificativa da classificacao',
            'justificativa da classificação', 'porque do ncm', 'porquê do ncm',
            'porque da classificacao', 'porquê da classificação', 'caderno sugerido',
            'produto sugerido', 'motivo da classificacao', 'motivo da classificação',
            'motivo da classificacao fiscal', 'motivo da classificação fiscal'
        ])
        
        # ✅ CORREÇÃO CRÍTICA (10/01/2026): "esse relatorio" só força NCM quando houver SINAIS de NCM.
        # Motivo: usuários usam "esse relatório" para se referir a respostas recentes (ex: legislação),
        # e forçar NCM aqui causa contexto errado (ou "desvia" para fluxos não relacionados).
        # Regra: só forçar NCM se a própria mensagem mencionar NCM/aliquotas/classificação/nesh/tecwin.
        if eh_esse_relatorio and session_id and tem_palavra_ncm:
            # Verificar se há contexto de NCM primeiro
            try:
                from services.context_service import buscar_contexto_sessao
                contextos = buscar_contexto_sessao(
                    session_id=session_id,
                    tipo_contexto='ultima_classificacao_ncm'
                )
                if contextos and len(contextos) > 0:
                    contexto_ncm = contextos[0].get('dados', {})
                    if contexto_ncm and contexto_ncm.get('ncm'):
                        # ✅ Há contexto de NCM e é "esse relatorio" - processar como email de NCM
                        logger.info(f"[EMAIL_PRECHECK] 🎯 'Esse relatorio' detectado + contexto de NCM encontrado - processando como email de NCM")
                        # tem_palavra_ncm já é True aqui (guard acima). Mantemos explícito para clareza.
                        tem_palavra_ncm = True
            except Exception as e:
                logger.debug(f"[EMAIL_PRECHECK] Erro ao verificar contexto de NCM: {e}")
        
        # ✅ CORREÇÃO CRÍTICA: Se tem palavra de bloqueio (email pessoal/genérico), SEMPRE retornar None
        # Não processar como email de NCM mesmo que tenha contexto de NCM
        # ✅ EXCEÇÃO: Se for "esse relatorio" e houver contexto de NCM, NÃO bloquear
        # ✅ Ajuste: palavras de bloqueio NÃO devem impedir email de NCM quando há sinais claros de NCM (ex: "alíquotas").
        # Caso clássico: "mande o email ... com as alíquotas do relatorio" deve ser tratado como NCM, não como relatório genérico.
        if tem_palavra_bloqueio and (not tem_palavra_ncm) and not (eh_esse_relatorio and tem_palavra_ncm):
            logger.debug(f"[EMAIL_PRECHECK] Email detectado mas tem palavra de bloqueio (email pessoal/genérico) - deixando outros prechecks processarem")
            return None
        
        # ✅ CORREÇÃO: Se NÃO tem palavra de NCM na mensagem E NÃO é "esse relatorio" com contexto, NÃO processar como email de NCM
        # Mesmo que tenha contexto de NCM, se a mensagem não menciona NCM e não é "esse relatorio", não é email de NCM
        if not tem_palavra_ncm:
            logger.debug(f"[EMAIL_PRECHECK] Email detectado mas sem palavras relacionadas a NCM na mensagem - deixando outros prechecks processarem")
            return None
        
        if not session_id:
            logger.debug(f"[EMAIL_PRECHECK] Email NCM detectado mas sem session_id - deixando IA processar")
            return None
        
        try:
            from services.context_service import buscar_contexto_sessao
            contextos = buscar_contexto_sessao(
                session_id=session_id,
                tipo_contexto='ultima_classificacao_ncm'
            )
            
            if not contextos or len(contextos) == 0:
                logger.debug(f"[EMAIL_PRECHECK] Email NCM detectado mas sem contexto de NCM - deixando IA processar")
                return None
            
            contexto_ncm = contextos[0].get('dados', {})
            if not contexto_ncm or not contexto_ncm.get('ncm'):
                logger.debug(f"[EMAIL_PRECHECK] Email NCM detectado mas contexto inválido - deixando IA processar")
                return None
            
            logger.info(f"[EMAIL_PRECHECK] 🎯 Email de classificação NCM detectado. NCM: {contexto_ncm.get('ncm')}")
            
            # Extrair email
            email = None
            padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
            match_email = re.search(padrao_email, mensagem_lower)
            if match_email:
                email = match_email.group(1)
            
            if not email:
                logger.debug(f"[EMAIL_PRECHECK] Email NCM detectado mas sem email na mensagem - deixando IA processar")
                return None
            
            # Usar o use case
            from services.use_cases.enviar_email_classificacao_ncm_use_case import (
                EnviarEmailClassificacaoNcmUseCase,
                EnviarEmailClassificacaoNcmRequest
            )
            
            use_case = EnviarEmailClassificacaoNcmUseCase()
            request = EnviarEmailClassificacaoNcmRequest(
                session_id=session_id,
                destinatario=email,
                nome_usuario=nome_usuario,
                confirmar_envio=True  # Sempre mostrar preview primeiro
            )
            
            resultado = use_case.executar(request)
            
            if resultado.sucesso:
                logger.info(f"[EMAIL_PRECHECK] ✅ Email de classificação NCM processado com sucesso via use case")
                
                # Salvar estado para confirmação posterior
                preview_dict = resultado.preview_email
                if preview_dict and hasattr(self, 'chat_service') and self.chat_service:
                    if not hasattr(self.chat_service, 'ultima_resposta_aguardando_email'):
                        self.chat_service.ultima_resposta_aguardando_email = None
                    self.chat_service.ultima_resposta_aguardando_email = {
                        'funcao': 'enviar_email_personalizado',
                        'tipo': 'email_classificacao_ncm',
                        'destinatarios': [email],
                        'assunto': preview_dict.get('assunto', 'Classificação Fiscal e Alíquotas'),
                        'conteudo': preview_dict.get('conteudo', ''),
                        'use_case': 'EnviarEmailClassificacaoNcmUseCase',
                        'session_id': session_id
                    }
                
                return {
                    'sucesso': resultado.sucesso,
                    'resposta': resultado.mensagem_chat,
                    'preview_email': preview_dict,
                    'aguardando_confirmacao': True,
                    '_processado_precheck': True,
                    '_resultado_interno': {
                        'ultima_resposta_aguardando_email': self.chat_service.ultima_resposta_aguardando_email if hasattr(self, 'chat_service') and self.chat_service and hasattr(self.chat_service, 'ultima_resposta_aguardando_email') else None
                    }
                }
            else:
                logger.warning(f"[EMAIL_PRECHECK] ⚠️ Erro ao processar email de NCM: {resultado.erro}")
                return {
                    'sucesso': False,
                    'resposta': resultado.mensagem_chat,
                    '_processado_precheck': True
                }
                
        except Exception as e:
            logger.error(f"[EMAIL_PRECHECK] ❌ Erro ao processar email de NCM: {e}", exc_info=True)
            return None
    
    def _precheck_envio_email_relatorio_generico(
        self,
        mensagem: str,
        mensagem_lower: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Precheck genérico para comandos de envio de QUALQUER relatório por email.
        
        Detecta padrões como:
        - envia esse relatório para fulano@empresa.com
        - manda esse resumo pra helenomaffra@gmail.com
        - envia para helenomaffra@gmail.com (mensagem curta quando há relatório recente)
        
        IMPORTANTE: Comandos "manda esse relatório" são deixados para _precheck_envio_email_relatorio_adhoc
        """
        # ✅ TAREFA 1: Verificar se é comando "mandar esse relatório" ANTES de qualquer processamento
        # Se for, deixar o fluxo de relatório ad hoc processar
        if self._parece_comando_mandar_esse_relatorio(mensagem_lower):
            logger.debug(f"[EMAIL_PRECHECK] Comando 'mandar esse relatório' detectado - deixando _precheck_envio_email_relatorio_adhoc processar")
            return None
        
        # Extrair email primeiro
        email = None
        padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        match_email = re.search(padrao_email, mensagem_lower)
        if match_email:
            email = match_email.group(1)
        
        # 1) CASOS CLÁSSICOS: Padrões explícitos de relatório (mas não "esse relatório")
        # ✅ NOVO: Incluir typos comuns (realtorio, reltorio, raltatorio) nos padrões
        padroes_relatorio = [
            r'\b(envia|envie|manda|mandar|enviar|mande|monte|montar)\s+(relatorio|relatório|realtorio|reltorio|raltatorio|ralatório|resumo|dashboard|fechamento)\s+(para|por|via|pra)',
            r'\b(envia|envie|manda|mandar|enviar|mande|monte|montar)\s+(por|via)\s+email\s+(relatorio|relatório|realtorio|reltorio|raltatorio|ralatório|resumo|dashboard|fechamento)',
            r'\b(monte|montar)\s+(um|uma)\s+(relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+(e\s+)?(envia|envie|manda|mandar|enviar|mande)',  # ✅ NOVO: "monte um realtorio e envia"
        ]
        
        tem_pedido_relatorio_classico = any(re.search(p, mensagem_lower) for p in padroes_relatorio)
        
        # 2) NOVO CASO: Mensagem curta só com "envia para X" (quando há relatório recente)
        tem_verbo_envio = any(verbo in mensagem_lower for verbo in ['envia', 'envie', 'manda', 'mandar', 'enviar', 'mande'])
        mensagem_curta = len(mensagem_lower.strip()) <= 80
        
        # Palavras de bloqueio
        palavras_bloqueio = [
            'processo', 'processos',
            'informacao', 'informação', 'informacoes', 'informações',
            'ncm', 'alíquota', 'aliquota', 'classificacao', 'classificação',
            'duimp', 'icms', 'cct'
        ]
        tem_palavra_bloqueio = any(palavra in mensagem_lower for palavra in palavras_bloqueio)
        
        # Verificar 'di' e 'ce' como palavras inteiras
        if re.search(r'\bdi\b', mensagem_lower) or re.search(r'\bce\b', mensagem_lower):
            tem_palavra_bloqueio = True
        
        mensagem_longa = len(mensagem_lower.strip()) > 100
        
        # Decidir se deve processar como relatório genérico
        deve_processar_relatorio = False
        
        if tem_pedido_relatorio_classico:
            deve_processar_relatorio = True
            logger.info(f"[EMAIL_PRECHECK] 🎯 Padrão clássico de relatório detectado")
        elif tem_verbo_envio and email and mensagem_curta and not tem_palavra_bloqueio and not mensagem_longa:
            # ✅ Guardrail: NÃO tratar como "envia relatório recente" quando a mensagem parece email livre
            # Ex: "manda um email para X dizendo que ..." → deve ir para `_precheck_envio_email_livre`.
            if ('email' in mensagem_lower) and re.search(r'\b(dizendo|avisando|informando)\b', mensagem_lower):
                return None
            # Verificar se há relatório recente
            from services.report_service import buscar_ultimo_relatorio
            session_id_para_buscar = session_id or getattr(self.chat_service, 'session_id_atual', None) if hasattr(self, 'chat_service') else None
            
            if session_id_para_buscar:
                relatorio_teste = buscar_ultimo_relatorio(session_id_para_buscar)
                if relatorio_teste and relatorio_teste.texto_chat:
                    deve_processar_relatorio = True
                    logger.info(f"[EMAIL_PRECHECK] 🎯 Mensagem curta 'envia para X' detectada + relatório recente encontrado. Tratando como relatório genérico.")
                else:
                    logger.info(f"[EMAIL_PRECHECK] Mensagem curta 'envia para X' detectada, mas NÃO há relatório recente. Deixando outros prechecks processarem.")
            else:
                logger.info(f"[EMAIL_PRECHECK] Mensagem curta 'envia para X' detectada, mas session_id não disponível. Deixando outros prechecks processarem.")
        
        if not deve_processar_relatorio:
            if tem_palavra_bloqueio:
                logger.info(f"[EMAIL_PRECHECK] Mensagem contém palavras de bloqueio. NÃO é relatório genérico - deixando outros prechecks processarem.")
            elif mensagem_longa:
                logger.info(f"[EMAIL_PRECHECK] Mensagem é longa ({len(mensagem_lower)} chars). NÃO é relatório genérico - provavelmente email livre.")
            elif not email:
                logger.info(f"[EMAIL_PRECHECK] Mensagem não contém email. NÃO é relatório genérico - deixando outros prechecks processarem.")
            return None
        
        if not email:
            logger.info(f"[EMAIL_PRECHECK] Comando de envio de relatório genérico detectado, mas não encontrou email. Deixando IA processar.")
            return None
        
        logger.info(f"[EMAIL_PRECHECK] 🎯 Comando de envio de relatório genérico por email detectado. Email: {email}")
        
        # ✅ NOVO: Verificar se é relatório ad hoc ANTES de buscar do report_service
        # Se a última resposta do histórico não é dashboard padrão, deixar o novo método processar
        historico = historico or []
        if historico and len(historico) > 0:
            ultima_resposta = historico[-1].get('resposta', '')
            if ultima_resposta and len(ultima_resposta.strip()) > 50:
                # Verificar se NÃO é dashboard padrão
                titulos_dashboard_padrao = [
                    'O QUE TEMOS PRA HOJE',
                    'FECHAMENTO DO DIA',
                    'PROCESSOS',
                    'STATUS GERAL',
                ]
                eh_dashboard_padrao = any(titulo in ultima_resposta.upper() for titulo in titulos_dashboard_padrao)
                
                if not eh_dashboard_padrao:
                    # Não é dashboard padrão - deixar _precheck_envio_email_relatorio_adhoc processar
                    logger.info(f"[EMAIL_PRECHECK] Última resposta NÃO é dashboard padrão (primeiros 100 chars: '{ultima_resposta[:100]}...') - deixando _precheck_envio_email_relatorio_adhoc processar")
                    return None
        
        # Buscar último relatório no contexto
        try:
            from services.report_service import buscar_ultimo_relatorio
            session_id_para_buscar = session_id or getattr(self.chat_service, 'session_id_atual', None) if hasattr(self, 'chat_service') else None
            
            if not session_id_para_buscar:
                # ✅ TAREFA 2: Não encerrar o fluxo - deixar outros prechecks tentarem (ex: relatório ad hoc)
                logger.info(f"[EMAIL_PRECHECK] Session ID não disponível para buscar relatório - deixando outros prechecks processarem")
                return None
            
            relatorio = buscar_ultimo_relatorio(session_id_para_buscar)
            
            # ✅ TAREFA 2: Se não encontrar relatório, não encerrar o fluxo - deixar outros prechecks tentarem
            if not relatorio:
                logger.info(f"[EMAIL_PRECHECK] Nenhum relatório encontrado no report_service - deixando outros prechecks processarem (ex: relatório ad hoc)")
                return None  # Não retornar erro final, apenas None para dar chance ao ad hoc
            
            if not relatorio.texto_chat:
                logger.info(f"[EMAIL_PRECHECK] Relatório encontrado mas texto vazio - deixando outros prechecks processarem")
                return None  # Não retornar erro final, apenas None para dar chance ao ad hoc
            
            # ✅ NOVO: Verificar se o relatório do report_service é dashboard padrão
            # Se não for, deixar o novo método processar
            texto_relatorio = relatorio.texto_chat or ''
            titulos_dashboard_padrao = [
                'O QUE TEMOS PRA HOJE',
                'FECHAMENTO DO DIA',
                'PROCESSOS',
                'STATUS GERAL',
            ]
            eh_dashboard_padrao = any(titulo in texto_relatorio.upper() for titulo in titulos_dashboard_padrao)
            
            if not eh_dashboard_padrao:
                # Não é dashboard padrão - deixar _precheck_envio_email_relatorio_adhoc processar
                logger.info(f"[EMAIL_PRECHECK] Relatório do report_service NÃO é dashboard padrão - deixando _precheck_envio_email_relatorio_adhoc processar")
                return None
            
            logger.info(f"[EMAIL_PRECHECK] ✅ Relatório encontrado no contexto: {relatorio.tipo_relatorio} (categoria: {relatorio.categoria})")
            
            # Montar email usando email_builder_service
            try:
                from services.email_builder_service import EmailBuilderService
                email_builder = EmailBuilderService()
                
                nome_usuario = getattr(self.chat_service, 'nome_usuario_atual', None) if hasattr(self, 'chat_service') else None
                
                resultado_email = email_builder.montar_email_relatorio(
                    relatorio=relatorio,
                    destinatario=email,
                    nome_usuario=nome_usuario
                )
                
                if resultado_email.get('sucesso'):
                    if hasattr(self, 'chat_service') and self.chat_service:
                        resultado = self.chat_service._executar_funcao_tool('enviar_email_personalizado', {
                            'destinatarios': [email],
                            'assunto': resultado_email.get('assunto', 'Relatório'),
                            'conteudo': resultado_email.get('conteudo', ''),
                            'confirmar_envio': False
                        }, mensagem_original=mensagem)
                        
                        if resultado and resultado.get('sucesso'):
                            logger.info(f"[EMAIL_PRECHECK] ✅ Email de relatório genérico montado e enviado via precheck (tipo: {relatorio.tipo_relatorio})")
                            return resultado
                        else:
                            logger.warning(f"[EMAIL_PRECHECK] Erro ao executar enviar_email_personalizado: {resultado.get('erro') if resultado else 'resultado vazio'}")
                else:
                    logger.warning(f"[EMAIL_PRECHECK] Erro ao montar email de relatório: {resultado_email.get('erro')}")
            except Exception as e:
                logger.error(f"[EMAIL_PRECHECK] Erro ao usar email_builder_service para relatório genérico: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"[EMAIL_PRECHECK] Erro ao buscar relatório no contexto: {e}", exc_info=True)
        
        logger.info(f"[EMAIL_PRECHECK] Comando de envio de relatório genérico detectado, mas deixando IA processar.")
        return None

    def _precheck_envio_email_esse_relatorio_sem_report(
        self,
        mensagem: str,
        mensagem_lower: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback seguro para comandos do tipo "envie esse relatório..." quando NÃO há report_id visível.

        Cenário típico:
        - Usuário faz uma pergunta (ex: legislação)
        - Assistente responde com um texto longo
        - Usuário: "melhore esse relatório e envie pra X (assine Y)"

        Aqui "relatório" significa "a resposta anterior", não um relatório persistido em report_service.
        """
        historico = historico or []

        # Só faz sentido se houver um destinatário de email explícito
        email = self._extrair_email_da_mensagem(mensagem_lower)
        if not email:
            return None

        ultimo_texto_assistente = self._extrair_ultima_resposta_assistente(historico)
        if not ultimo_texto_assistente:
            logger.info("[EMAIL_PRECHECK] 'esse relatório' sem report visível, mas sem última resposta do assistente no histórico. Pedindo esclarecimento.")
            return {
                'sucesso': False,
                'resposta': "⚠️ Não encontrei um relatório recente na tela. Você quer que eu envie qual texto por email? (pode colar aqui ou dizer 'envie a resposta anterior')",
                '_processado_precheck': True
            }

        assinatura_nome = self._extrair_assinatura_solicitada(mensagem)
        assunto = self._gerar_assunto_ultimo_texto(ultimo_texto_assistente)

        conteudo_base = self._limpar_texto_para_email(ultimo_texto_assistente).strip()
        if assinatura_nome:
            conteudo_base = f"{conteudo_base}\n\nAtenciosamente,\n{assinatura_nome}"

        # Criar draft (se disponível) para suportar fluxo de melhoria/confirmar envio
        draft_id = None
        try:
            from services.email_draft_service import get_email_draft_service
            draft_service = get_email_draft_service()
            session_id_para_draft = session_id or (getattr(self.chat_service, 'session_id_atual', None) if hasattr(self, 'chat_service') and self.chat_service else None) or 'default'
            draft_id = draft_service.criar_draft(
                destinatarios=[email],
                assunto=assunto,
                conteudo=conteudo_base,
                session_id=session_id_para_draft,
                funcao_email='enviar_email_personalizado',
                cc=None,
                bcc=None
            )
            if draft_id:
                logger.info(f'✅✅✅ [EMAIL_PRECHECK] Draft criado (esse_relatorio_sem_report): {draft_id}')
        except Exception as e:
            logger.warning(f'⚠️ [EMAIL_PRECHECK] Erro ao criar draft (esse_relatorio_sem_report): {e}')

        # Salvar estado para confirmação posterior
        if hasattr(self, 'chat_service') and self.chat_service:
            if not hasattr(self.chat_service, 'ultima_resposta_aguardando_email'):
                self.chat_service.ultima_resposta_aguardando_email = None
            self.chat_service.ultima_resposta_aguardando_email = {
                'funcao': 'enviar_email_personalizado',
                'destinatarios': [email],
                'assunto': assunto,
                'conteudo': conteudo_base,
                'tipo': 'email_esse_relatorio_sem_report',
                'texto_original': conteudo_base,
                'draft_id': draft_id
            }

        from datetime import datetime
        preview_texto = f"📧 **Email para Envio**\n\n"
        preview_texto += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        preview_texto += f"**De:** Sistema mAIke (Make Consultores)\n"
        preview_texto += f"**Para:** {email}\n"
        preview_texto += f"**Assunto:** {assunto}\n"
        preview_texto += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        preview_texto += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        preview_texto += f"**Mensagem (base):**\n\n"
        preview_texto += f"{conteudo_base}\n\n"
        preview_texto += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        preview_texto += f"⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"

        # ✅ Pedir para IA refinar quando usuário explicitamente falou "melhore"
        pedir_refino = any(k in mensagem_lower for k in ["melhorar", "melhore", "refinar", "refine", "elaborar", "elabore", "reescrever", "reescreva"])
        return {
            'sucesso': True,
            'resposta': preview_texto,
            'aguardando_confirmacao': True,
            '_processado_precheck': True,
            '_deve_chamar_ia_para_refinar': bool(pedir_refino),
            # ✅ Fase 2C: quando vamos chamar IA para refinar, bloquear qualquer tool-calling
            'block_tool_calls_no_refino': bool(pedir_refino),
            '_dados_email_preview': {
                'destinatario': email,
                'assunto': assunto,
                'conteudo': conteudo_base,
                'assinatura_solicitada': assinatura_nome,
                'fonte': 'ultima_resposta_assistente'
            },
            '_resultado_interno': {
                'ultima_resposta_aguardando_email': {
                    'funcao': 'enviar_email_personalizado',
                    'destinatarios': [email],
                    'assunto': assunto,
                    'conteudo': conteudo_base,
                    'tipo': 'email_esse_relatorio_sem_report',
                    'texto_original': conteudo_base,
                    'draft_id': draft_id
                }
            }
        }

    def _extrair_email_da_mensagem(self, mensagem_lower: str) -> Optional[str]:
        padrao_email = r'\b([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})\b'
        m = re.search(padrao_email, mensagem_lower or '', re.IGNORECASE)
        return m.group(1) if m else None

    def _extrair_assinatura_solicitada(self, mensagem: str) -> Optional[str]:
        """
        Extrai "assine <nome>" / "assinar <nome>".
        Ex: "assine gustavo" -> "Gustavo"
        """
        if not mensagem:
            return None
        m = re.search(r'\bassine\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\'.-]{1,60})\b', mensagem, re.IGNORECASE)
        if not m:
            m = re.search(r'\bassinar\s+como\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s\'.-]{1,60})\b', mensagem, re.IGNORECASE)
        if not m:
            return None
        nome = m.group(1).strip()
        # Normalização simples
        nome = ' '.join([p.capitalize() for p in nome.split()])
        return nome or None

    def _extrair_ultima_resposta_assistente(self, historico: List[Dict[str, Any]]) -> Optional[str]:
        """
        Tenta recuperar o texto da última mensagem do assistente no histórico.
        Suporta diferentes formatos (role/content, tipo/resposta, etc).
        """
        for item in reversed(historico or []):
            try:
                role = (item.get('role') or item.get('autor') or item.get('tipo') or '').lower()
                if role in ['assistant', 'ia', 'bot', 'maike', 'mAIke'.lower()]:
                    # Campos comuns
                    for k in ['content', 'mensagem', 'resposta', 'texto', 'text']:
                        v = item.get(k)
                        if isinstance(v, str) and v.strip():
                            return v.strip()
            except Exception:
                continue
        return None

    def _gerar_assunto_ultimo_texto(self, texto: str) -> str:
        t = (texto or '').lower()
        if 'legisla' in t or 'decreto' in t or 'instrução normativa' in t or 'instruçao normativa' in t:
            return "Legislação - erros na fatura comercial (importação)"
        if 'ncm' in t and ('alíquota' in t or 'aliquota' in t):
            return "NCM - classificação e alíquotas"
        return "Resumo da conversa"

    def _limpar_texto_para_email(self, texto: str) -> str:
        """
        Remove separadores e blocos de rodapé comuns (ex: linhas de '━━━━━━━━', tags de fonte).
        Mantém o conteúdo principal.
        """
        linhas = (texto or '').splitlines()
        out = []
        for ln in linhas:
            l = ln.strip()
            if not l:
                out.append('')
                continue
            if set(l) <= set('━-_='):
                # separadores visuais
                continue
            if l.lower().startswith('🔍 fonte:') or l.lower().startswith('✅ fonte:'):
                continue
            if 'assistants api' in l.lower() or 'file search' in l.lower():
                continue
            if 'nota:' in l.lower() and 'assistants api' in (texto or '').lower():
                # reduzir ruído de rodapé de RAG
                continue
            out.append(ln)
        # normalizar múltiplas linhas vazias
        cleaned = '\n'.join(out)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        return cleaned
    
    def _precheck_envio_email(
        self,
        mensagem: str,
        mensagem_lower: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Precheck para comandos de envio de resumo/briefing por email.
        
        Detecta padrões como:
        - "enviar resumo mv5 por email para helenomaffra@gmail.com"
        - "resumo mv5 por email"
        - "enviar briefing por email"
        - "mandar resumo por email"
        - "mande esse relatorio para o email X" (após relatório anterior)
        - "envia esse relatorio para o email X" (após relatório anterior)
        """
        # ✅ AJUSTE: Verificar se é comando "mandar esse relatório" ANTES de processar
        # Se for, deixar o fluxo de relatório ad hoc processar (ele é chamado depois na hierarquia)
        if self._parece_comando_mandar_esse_relatorio(mensagem_lower):
            logger.debug(f"[EMAIL_PRECHECK] Comando 'mandar esse relatório' detectado em _precheck_envio_email - deixando _precheck_envio_email_relatorio_adhoc processar")
            return None

        # ✅ CRÍTICO: NÃO capturar email livre por engano.
        # Ex: "manda um email para X dizendo que ..." deve ser tratado por `_precheck_envio_email_livre`.
        try:
            tem_email = bool(re.search(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', mensagem_lower))
            tem_verbo_email_livre = bool(re.search(r'\b(dizendo|avisando|informando)\b', mensagem_lower))
            tem_palavra_relatorio = any(p in mensagem_lower for p in [
                'resumo', 'briefing', 'dashboard', 'fechamento',
                'relatorio', 'relatório', 'realtorio', 'reltorio', 'raltatorio', 'ralatório'
            ])
            if tem_email and tem_verbo_email_livre and not tem_palavra_relatorio:
                return None
        except Exception:
            # Se algo falhar, não quebrar o precheck.
            pass
        
        # ✅ CRÍTICO: Detectar referências a relatórios anteriores (mas não "manda esse relatório" que já foi tratado acima)
        # Este padrão é usado para detectar referências a relatórios anteriores em contextos específicos
        # NOTA: "esse relatorio" já foi tratado acima e deixado para o ad hoc, então não incluímos aqui
        eh_referencia_relatorio_anterior = any(palavra in mensagem_lower for palavra in [
            'raltatorio', 'ralatório', 'relatorio acima', 'relatório acima',  # Typos e variações comuns
            'realtorio', 'reltorio', 'realtorio acima', 'reltorio acima',  # ✅ NOVO: Typos adicionais
        ])

        # ✅ Guardrail: este precheck deve existir apenas para resumos/briefings/relatórios.
        # Se não há nenhuma palavra-chave de relatório, deixar os outros prechecks cuidarem (ex: email livre).
        tem_palavra_relatorio = any(p in mensagem_lower for p in [
            'resumo', 'briefing', 'dashboard', 'fechamento',
            'relatorio', 'relatório', 'realtorio', 'reltorio', 'raltatorio', 'ralatório'
        ])
        if not tem_palavra_relatorio and not eh_referencia_relatorio_anterior:
            return None
        
        # Padrões para detectar envio por email (mais flexíveis)
        # ✅ NOVO: Incluir typos comuns (realtorio, reltorio, raltatorio) nos padrões
        padroes_email = [
            r'\b(enviar|mandar|envia|manda|mande|monte|montar)\s+(resumo|briefing|dashboard|relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)',  # "envia resumo", "enviar relatorio", "mande resumo", "monte realtorio"
            r'\b(enviar|mandar|envia|manda|mande|monte|montar)\s+(resumo|briefing|dashboard|relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+\w+\s+(para|por|via)\s+email',  # "envia resumo mv5 para email", "mande resumo mv5 para email"
            r'\b(resumo|briefing|dashboard|relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+(por|via|para)\s+email',  # "resumo por email", "relatorio para email"
            r'\b(resumo|briefing|dashboard|relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+\w+\s+por\s+email',  # "resumo mv5 por email"
            r'\b(resumo|briefing|dashboard|relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+\w+\s+email',  # "resumo mv5 email" (sem "por")
            r'\b(resumo|briefing|dashboard|relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+email',  # "resumo email"
            r'\b(enviar|mandar|envia|manda|mande|monte|montar)\s+(resumo|briefing|dashboard|relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+\w+\s+para\s+o\s+email',  # "envia resumo mv5 para o email", "mande resumo mv5 para o email"
            r'\b(enviar|mandar|envia|manda|mande|monte|montar)\s+(relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+(para|por|via)\s+email',  # "enviar relatorio para email", "mande relatorio para email"
            r'\b(monte|montar)\s+(um|uma)\s+(relatorio|relatório|realtorio|reltorio|raltatorio|ralatório)\s+(e\s+)?(envia|envie|manda|mandar|enviar|mande)\s+(um\s+)?email',  # ✅ NOVO: "monte um realtorio e envia um email"
            r'email\s+(para|to)\s+[a-zA-Z0-9._%+-]+@',  # "email para helenomaffra@gmail.com"
            r'para\s+o\s+email\s+[a-zA-Z0-9._%+-]+@',  # "para o email helenomaffra@gmail.com"
        ]
        
        tem_pedido_email = any(re.search(p, mensagem_lower) for p in padroes_email) or eh_referencia_relatorio_anterior
        
        # Também verificar se tem "email" e ("resumo" ou "briefing" ou "dashboard" ou "relatorio") na mesma mensagem
        # ✅ NOVO: Incluir typos na verificação
        if not tem_pedido_email:
            tem_email = 'email' in mensagem_lower
            tem_resumo = any(palavra in mensagem_lower for palavra in [
                'resumo', 'briefing', 'dashboard', 'relatorio', 'relatório',
                'realtorio', 'reltorio', 'raltatorio', 'ralatório'  # ✅ NOVO: Typos adicionais
            ])
            tem_verbo_envio = any(verbo in mensagem_lower for verbo in ['enviar', 'mandar', 'envia', 'manda', 'mande'])
            if tem_email and (tem_resumo or tem_verbo_envio):
                tem_pedido_email = True
        
        if not tem_pedido_email:
            return None
        
        # Extrair categoria se mencionada (ex: "resumo mv5 por email", "envia resumo mv5 para o email", "enviar resumo dmd para email", "resumo do mv5", "envia um email com o resumo do mv5")
        categoria = None
        
        # ✅ PRIORIDADE 1: Padrão "resumo do [CATEGORIA]" (ex: "resumo do mv5", "envia um email com o resumo do mv5")
        # Este padrão tem prioridade porque é mais específico e comum
        padrao_resumo_do = re.search(r'resumo\s+do\s+([a-z]{2,4})', mensagem_lower, re.IGNORECASE)
        if padrao_resumo_do:
            categoria_candidata = padrao_resumo_do.group(1).upper()
            try:
                from db_manager import verificar_categoria_processo
                if verificar_categoria_processo(categoria_candidata):
                    categoria = categoria_candidata
                    logger.info(f"[EMAIL_PRECHECK] ✅ Categoria {categoria} extraída de 'resumo do {categoria_candidata}'")
            except Exception as e:
                logger.debug(f"[EMAIL_PRECHECK] Erro ao verificar categoria {categoria_candidata}: {e}")
        
        # ✅ PRIORIDADE 2: Tentar encontrar categoria diretamente após "resumo", "briefing", "dashboard" ou "relatorio" (se ainda não encontrou)
        # Padrões mais específicos primeiro (mais palavras)
        padroes_categoria = [
            # "enviar resumo dmd para email" ou "envia resumo mv5 para o email" ou "enviar relatorio mv5 para email"
            r'\b(enviar|mandar|envia|manda|mande)\s+(resumo|briefing|dashboard|relatorio|relatório)\s+([a-z]{2,4})\s+(para|por|via)\s+(o\s+)?email',
            # "resumo dmd para email" ou "resumo mv5 por email" ou "relatorio mv5 para email" ou "mande resumo mv5 para email"
            r'\b(resumo|briefing|dashboard|relatorio|relatório)\s+([a-z]{2,4})\s+(para|por|via)\s+(o\s+)?email',
            # "enviar resumo mv5" ou "envia resumo dmd" ou "enviar relatorio mv5"
            r'\b(enviar|mandar|envia|manda|mande)\s+(resumo|briefing|dashboard|relatorio|relatório)\s+([a-z]{2,4})\b',
            # "resumo mv5 email" (sem "por" ou "para") ou "mande resumo mv5"
            r'\b(resumo|briefing|dashboard|relatorio|relatório)\s+([a-z]{2,4})\s+email',
            # "resumo mv5" (pode ter email depois)
            r'\b(resumo|briefing|dashboard|relatorio|relatório)\s+([a-z]{2,4})\b',
        ]
        
        for i, padrao in enumerate(padroes_categoria):
            match_cat = re.search(padrao, mensagem_lower)
            if match_cat:
                # Pegar o grupo que contém a categoria
                categoria_candidata = None
                grupos = match_cat.groups()
                
                # A categoria está sempre no último grupo que não é palavra reservada
                # Grupos comuns: (verbo, tipo, categoria) ou (tipo, categoria)
                if len(grupos) >= 3:
                    # Padrão com verbo: grupos são (verbo, tipo, categoria, ...)
                    categoria_candidata = grupos[2]
                elif len(grupos) >= 2:
                    # Padrão sem verbo: grupos são (tipo, categoria, ...)
                    categoria_candidata = grupos[1]
                
                if categoria_candidata and len(categoria_candidata) >= 2:
                    categoria_candidata = categoria_candidata.upper()
                    try:
                        from db_manager import verificar_categoria_processo
                        if verificar_categoria_processo(categoria_candidata):
                            categoria = categoria_candidata
                            logger.info(f"[EMAIL_PRECHECK] Categoria '{categoria}' detectada usando padrão {i+1}: '{padrao}'")
                            break
                        else:
                            logger.debug(f"[EMAIL_PRECHECK] Categoria candidata '{categoria_candidata}' não é válida")
                    except Exception as e:
                        logger.debug(f"[EMAIL_PRECHECK] Erro ao verificar categoria {categoria_candidata}: {e}")
                        pass
        
        # Extrair email se mencionado
        email = None
        padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        match_email = re.search(padrao_email, mensagem_lower)
        if match_email:
            email = match_email.group(1)
        
        # ✅ NOVO: Se é referência a relatório anterior, tentar extrair categoria do histórico
        if eh_referencia_relatorio_anterior and historico and len(historico) > 0:
            # Procurar na última resposta por categoria
            for i in range(len(historico) - 1, -1, -1):
                resposta_anterior = historico[i].get('resposta', '')
                if resposta_anterior:
                    # Verificar se é um relatório (dashboard, fechamento ou "como estão os X")
                    if 'O QUE TEMOS PRA HOJE' in resposta_anterior.upper() or 'FECHAMENTO DO DIA' in resposta_anterior.upper() or 'PROCESSOS' in resposta_anterior.upper() and 'STATUS GERAL' in resposta_anterior.upper():
                        # Tentar extrair categoria do título do relatório
                        padrao_categoria_titulo = r'(?:PROCESSOS|O QUE TEMOS PRA HOJE|STATUS GERAL)[\s-]+([A-Z]{2,4})'
                        match_categoria = re.search(padrao_categoria_titulo, resposta_anterior, re.IGNORECASE)
                        if match_categoria:
                            categoria_extraida = match_categoria.group(1).upper()
                            try:
                                from db_manager import verificar_categoria_processo
                                if verificar_categoria_processo(categoria_extraida):
                                    categoria = categoria_extraida
                                    logger.info(f"[EMAIL_PRECHECK] ✅ Categoria {categoria} extraída do relatório anterior")
                                    break
                            except Exception as e:
                                logger.debug(f"[EMAIL_PRECHECK] Erro ao verificar categoria {categoria_extraida}: {e}")
                        
                        # Se não encontrou no título, tentar buscar no conteúdo (ex: "MV5 (5 processo(s))")
                        if not categoria:
                            padrao_categoria_conteudo = r'\b([A-Z]{2,4})\s*\(\d+\s+processo\(s\)\)'
                            match_categoria_conteudo = re.search(padrao_categoria_conteudo, resposta_anterior, re.IGNORECASE)
                            if match_categoria_conteudo:
                                categoria_extraida = match_categoria_conteudo.group(1).upper()
                                try:
                                    from db_manager import verificar_categoria_processo
                                    if verificar_categoria_processo(categoria_extraida):
                                        categoria = categoria_extraida
                                        logger.info(f"[EMAIL_PRECHECK] ✅ Categoria {categoria} extraída do conteúdo do relatório anterior")
                                        break
                                except Exception as e:
                                    logger.debug(f"[EMAIL_PRECHECK] Erro ao verificar categoria {categoria_extraida}: {e}")
        
        logger.info(
            f"[EMAIL_PRECHECK] Comando de envio por email detectado. Categoria: {categoria}, Email: {email} | Mensagem: '{mensagem}' | É referência anterior: {eh_referencia_relatorio_anterior}"
        )
        
        # ✅ CRÍTICO: Se detectou comando de envio de relatório E tem email, FORÇAR chamada direta
        # Isso garante que funcione mesmo se a IA não entender
        # NOTA: Não incluir "esse relatorio" aqui pois já foi tratado acima e deixado para o ad hoc
        if email and (eh_referencia_relatorio_anterior or any(palavra in mensagem_lower for palavra in ['resumo', 'dashboard', 'briefing', 'fechamento'])):
            logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Comando de envio de relatório por email detectado. Email: {email}, Categoria: {categoria}. Forçando chamada de enviar_relatorio_email.')
            try:
                # ✅ PASSO 6 - FASE 3: Buscar tipo diretamente do JSON salvo (não usar regex)
                tipo_relatorio = 'resumo'  # Padrão
                ultima_resposta_texto = ''
                if historico and len(historico) > 0:
                    # Procurar na última resposta
                    ultima_resposta = historico[-1].get('resposta', '')
                    if ultima_resposta:
                        ultima_resposta_texto = ultima_resposta
                        # Buscar tipo do JSON salvo
                        from services.report_service import obter_tipo_relatorio_salvo
                        tipo_relatorio_json = obter_tipo_relatorio_salvo(session_id, tentar_buscar_por_texto=ultima_resposta)
                        
                        if tipo_relatorio_json:
                            # ✅ CORREÇÃO (14/01/2026): Manter tipo original (não converter para "resumo" genérico)
                            # Usar tipo do JSON diretamente, não converter para "resumo"
                            if tipo_relatorio_json == 'fechamento_dia':
                                tipo_relatorio = 'fechamento'
                            else:
                                # ✅ Manter tipo original (o_que_tem_hoje, etc.) - não converter para "resumo"
                                tipo_relatorio = tipo_relatorio_json
                            logger.info(f'✅ Tipo de relatório obtido do JSON: {tipo_relatorio_json} → {tipo_relatorio}')
                        else:
                            # Fallback: usar regex apenas se não encontrar no JSON
                            if 'FECHAMENTO DO DIA' in ultima_resposta.upper():
                                tipo_relatorio = 'fechamento'
                                logger.warning('⚠️ Usando fallback regex para detectar tipo (JSON não encontrado): fechamento')
                            elif 'O QUE TEMOS PRA HOJE' in ultima_resposta.upper():
                                tipo_relatorio = 'o_que_tem_hoje'  # ✅ CORREÇÃO: Não usar "resumo" genérico
                                logger.warning('⚠️ Usando fallback regex para detectar tipo (JSON não encontrado): o_que_tem_hoje')
                            elif 'PROCESSOS' in ultima_resposta.upper() and 'STATUS GERAL' in ultima_resposta.upper():
                                tipo_relatorio = 'o_que_tem_hoje'  # ✅ CORREÇÃO: Não usar "resumo" genérico
                                logger.warning('⚠️ Usando fallback regex para detectar tipo (JSON não encontrado): o_que_tem_hoje')
                
                # ✅ FALLBACK: Se não encontrou no histórico, buscar do banco de dados
                if not ultima_resposta_texto:
                    try:
                        from db_manager import get_db_connection
                        session_id_para_buscar = session_id or getattr(self.chat_service, 'session_id_atual', None)
                        if session_id_para_buscar:
                            # ✅ PASSO 6 - FASE 3: Tentar buscar tipo do JSON salvo primeiro
                            from services.report_service import obter_tipo_relatorio_salvo
                            tipo_relatorio_json = obter_tipo_relatorio_salvo(session_id_para_buscar)
                            
                            if tipo_relatorio_json:
                                if tipo_relatorio_json == 'fechamento_dia':
                                    tipo_relatorio = 'fechamento'
                                elif tipo_relatorio_json == 'o_que_tem_hoje':
                                    tipo_relatorio = 'o_que_tem_hoje'  # ✅ CORREÇÃO: Manter tipo original
                                logger.info(f'✅ Tipo de relatório obtido do JSON (fallback banco): {tipo_relatorio_json} → {tipo_relatorio}')
                            else:
                                # Fallback final: buscar do banco e usar regex apenas se necessário
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute('''
                                    SELECT resposta FROM conversas_chat 
                                    WHERE session_id = ? 
                                    ORDER BY criado_em DESC 
                                    LIMIT 1
                                ''', (session_id_para_buscar,))
                                row = cursor.fetchone()
                                if row:
                                    ultima_resposta_texto = row[0] or ''
                                    # Tentar obter tipo do JSON usando o texto como fallback
                                    tipo_relatorio_json = obter_tipo_relatorio_salvo(session_id_para_buscar, tentar_buscar_por_texto=ultima_resposta_texto)
                                    if tipo_relatorio_json:
                                        if tipo_relatorio_json == 'fechamento_dia':
                                            tipo_relatorio = 'fechamento'
                                        elif tipo_relatorio_json == 'o_que_tem_hoje':
                                            tipo_relatorio = 'o_que_tem_hoje'  # ✅ CORREÇÃO: Manter tipo original
                                    else:
                                        # Último recurso: usar regex
                                        if 'FECHAMENTO DO DIA' in ultima_resposta_texto.upper():
                                            tipo_relatorio = 'fechamento'
                                            logger.warning('⚠️ Usando fallback regex (último recurso) para detectar tipo: fechamento')
                                        elif 'O QUE TEMOS PRA HOJE' in ultima_resposta_texto.upper():
                                            tipo_relatorio = 'o_que_tem_hoje'  # ✅ CORREÇÃO: Não usar "resumo" genérico
                                            logger.warning('⚠️ Usando fallback regex (último recurso) para detectar tipo: o_que_tem_hoje')
                                        elif 'PROCESSOS' in ultima_resposta_texto.upper() and 'STATUS GERAL' in ultima_resposta_texto.upper():
                                            tipo_relatorio = 'o_que_tem_hoje'  # ✅ CORREÇÃO: Não usar "resumo" genérico
                                            logger.warning('⚠️ Usando fallback regex (último recurso) para detectar tipo: o_que_tem_hoje')
                                conn.close()
                    except Exception as e:
                        logger.debug(f"Erro ao buscar última resposta do banco no precheck: {e}")
                
                # ✅ Se ainda não encontrou categoria mas tem relatório, tentar extrair do relatório
                if not categoria and ultima_resposta_texto:
                    # Tentar extrair categoria do título do relatório
                    padrao_categoria_titulo = r'(?:PROCESSOS|O QUE TEMOS PRA HOJE|STATUS GERAL)[\s-]+([A-Z]{2,4})'
                    match_categoria = re.search(padrao_categoria_titulo, ultima_resposta_texto, re.IGNORECASE)
                    if match_categoria:
                        categoria_extraida = match_categoria.group(1).upper()
                        try:
                            from db_manager import verificar_categoria_processo
                            if verificar_categoria_processo(categoria_extraida):
                                categoria = categoria_extraida
                                logger.info(f"[EMAIL_PRECHECK] ✅ Categoria {categoria} extraída do relatório no precheck")
                        except Exception as e:
                            logger.debug(f"[EMAIL_PRECHECK] Erro ao verificar categoria {categoria_extraida}: {e}")
                
                # Montar argumentos para enviar_relatorio_email
                args_relatorio = {
                    'destinatario': email,
                    'tipo_relatorio': tipo_relatorio,
                    'confirmar_envio': False  # Sempre mostrar preview primeiro
                }
                if categoria:
                    args_relatorio['categoria'] = categoria
                
                # Forçar chamada direta da função
                resultado_forcado = self.chat_service._executar_funcao_tool('enviar_relatorio_email', args_relatorio, mensagem_original=mensagem)
                
                if resultado_forcado and resultado_forcado.get('resposta'):
                    logger.info(f"✅✅✅ Resposta forçada ANTES da IA (ENVIO DE RELATÓRIO POR EMAIL) - tamanho: {len(resultado_forcado.get('resposta'))}")
                    return {
                        'sucesso': True,
                        'resposta': resultado_forcado.get('resposta'),
                        'tool_calling': {'name': 'enviar_relatorio_email', 'arguments': args_relatorio},
                        '_processado_precheck': True
                    }
                else:
                    logger.warning(f'❌ Resposta vazia da tool enviar_relatorio_email para "{mensagem}". Prosseguindo com a IA.')
            except Exception as e:
                logger.error(f'❌ Erro ao forçar tool enviar_relatorio_email para "{mensagem}": {e}', exc_info=True)
                # Se houver erro, deixar a IA tentar processar
        
        # ✅ FALLBACK: Se não conseguiu forçar, deixar a IA processar (mas com instruções claras)
        logger.info(f"[EMAIL_PRECHECK] Comando de envio por email detectado, mas deixando IA processar via enviar_relatorio_email para respeitar confirmação e filtros.")
        return None  # Deixar a IA processar via tool calling (enviar_relatorio_email)
    
    def _precheck_envio_email_relatorio_adhoc(
        self,
        mensagem: str,
        mensagem_lower: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Precheck para comandos de envio de relatório analítico ad hoc por email.
        
        Detecta padrões como:
        - "manda esse relatório para fulano@x"
        - "envia esse relatório por email"
        - "mande esse relatorio para xxx@xxx"
        
        Diferencia de:
        - Dashboards padrão (já tratados em _precheck_envio_email_relatorio_generico)
        - Processos específicos (já tratados em _precheck_envio_email_processo)
        - NCM/alíquotas (já tratados em _precheck_envio_email_ncm)
        
        Regras:
        - Só processa se a última resposta for um relatório analítico (não dashboard padrão)
        - Usa enviar_email_personalizado com o texto EXATO da última resposta
        - Não re-gera o relatório, apenas envia o que já foi exibido
        """
        historico = historico or []
        
        # 1. Verificar se é comando "mandar esse relatório"
        if not self._parece_comando_mandar_esse_relatorio(mensagem_lower):
            return None
        
        # 2. Extrair email
        email = None
        padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        match_email = re.search(padrao_email, mensagem_lower)
        if match_email:
            email = match_email.group(1)
        
        if not email:
            logger.debug(f"[EMAIL_PRECHECK] Comando 'mandar esse relatório' detectado mas sem email - deixando IA processar")
            return None
        
        # ✅ CRÍTICO (12/01/2026): SEMPRE buscar o último relatório SALVO primeiro
        # Isso garante que sempre envia o relatório que foi EXIBIDO NA TELA, não outras mensagens
        # (notificações, respostas de processos, etc.)
        ultima_resposta_texto = None
        tipo_relatorio_salvo = None
        
        try:
            from services.report_service import buscar_ultimo_relatorio, obter_tipo_relatorio_salvo, obter_last_visible_report_id, buscar_relatorio_por_id, _detectar_dominio_por_mensagem
            
            # ✅ REFINAMENTO 1 (14/01/2026): Usar last_visible_report_id por domínio (fonte da verdade)
            # Detectar domínio baseado na mensagem (sinais específicos de banco)
            dominio_detectado = _detectar_dominio_por_mensagem(mensagem)
            
            # ✅ PRIORIDADE MÁXIMA: Buscar last_visible_report_id do domínio correto (o que foi exibido na tela)
            last_visible = obter_last_visible_report_id(session_id, dominio=dominio_detectado)
            relatorio_salvo = None
            
            if last_visible and last_visible.get('id'):
                relatorio_salvo = buscar_relatorio_por_id(session_id, last_visible['id'])
                if relatorio_salvo:
                    ultima_resposta_texto = relatorio_salvo.texto_chat
                    tipo_relatorio_salvo = relatorio_salvo.tipo_relatorio
                    logger.info(f"[EMAIL_PRECHECK] ✅ Last visible report ID encontrado (domínio: {dominio_detectado}, ID: {last_visible['id']}, tipo: {tipo_relatorio_salvo}, filtrado: {last_visible.get('is_filtered', False)}, tamanho: {len(ultima_resposta_texto)} chars)")
            
            # ✅ FALLBACK: Se não encontrou via last_visible, buscar último relatório salvo
            if not relatorio_salvo:
                relatorio_salvo = buscar_ultimo_relatorio(session_id, tipo_relatorio=None, usar_active_report_id=True)
                if relatorio_salvo and relatorio_salvo.texto_chat:
                    ultima_resposta_texto = relatorio_salvo.texto_chat
                    tipo_relatorio_salvo = relatorio_salvo.tipo_relatorio
                    logger.info(f"[EMAIL_PRECHECK] ✅ Último relatório SALVO encontrado via fallback (tipo: {tipo_relatorio_salvo}, tamanho: {len(ultima_resposta_texto)} chars)")
            else:
                # ⚠️ Nota: este log era historicamente confuso; aqui significa que *já encontrou* via last_visible.
                logger.debug(f"[EMAIL_PRECHECK] last_visible_report_id encontrado - não é necessário fallback por histórico")
                
                # ✅ FALLBACK: Se não encontrou relatório salvo, buscar do histórico
                # (mas isso não é ideal, pois pode pegar outras mensagens)
                if historico and len(historico) > 0:
                    ultima_resposta = historico[-1].get('resposta', '')
                    if ultima_resposta and len(ultima_resposta.strip()) > 50:
                        ultima_resposta_texto = ultima_resposta
                        # Tentar detectar tipo do texto
                        tipo_relatorio_salvo = obter_tipo_relatorio_salvo(session_id, tentar_buscar_por_texto=ultima_resposta)
                        logger.warning(f"[EMAIL_PRECHECK] ⚠️ Usando última resposta do histórico como fallback (tipo detectado: {tipo_relatorio_salvo})")
        except Exception as e:
            logger.error(f"[EMAIL_PRECHECK] ❌ Erro ao buscar último relatório salvo: {e}", exc_info=True)
        
        if not ultima_resposta_texto:
            logger.info(f"[EMAIL_PRECHECK] Comando 'mandar esse relatório' detectado mas sem relatório salvo ou resposta válida - deixando IA processar")
            return None
        
        # ✅ Fase 2C (14/01/2026): Se existe last_visible_report_id, NUNCA desistir por heurística.
        # Motivo: retornar None aqui permite que a IA chame tools erradas (ex: extrato Santander).
        # Aqui a "fonte da verdade" é o report salvo/visível; se o usuário disse "esse relatório",
        # vamos gerar um preview de email determinístico e pedir confirmação.
        if last_visible and last_visible.get('id') and relatorio_salvo and ultima_resposta_texto:
            assinatura_nome = self._extrair_assinatura_solicitada(mensagem)
            pedir_refino = any(k in mensagem_lower for k in ["melhorar", "melhore", "refinar", "refine", "elaborar", "elabore", "reescrever", "reescreva"])
            try:
                import re as _re
                corpo = _re.sub(r'\[REPORT_META:\{.*?\}\]', '', ultima_resposta_texto, flags=_re.DOTALL).strip()
            except Exception:
                corpo = (ultima_resposta_texto or '').strip()

            if assinatura_nome:
                corpo = f"{corpo}\n\nAtenciosamente,\n{assinatura_nome}"

            # Tentar extrair categoria do report salvo (se existir) para assunto
            categoria_assunto = getattr(relatorio_salvo, 'categoria', None) if relatorio_salvo else None
            if not categoria_assunto and isinstance(last_visible, dict):
                # algumas versões guardam meta_json com info útil
                meta = last_visible.get('meta_json') or {}
                if isinstance(meta, dict):
                    categoria_assunto = meta.get('categoria')
            if not categoria_assunto and corpo:
                mcat = re.search(r'\bcategoria\s+([A-Z]{2,4})\b', corpo, re.IGNORECASE)
                if mcat:
                    categoria_assunto = mcat.group(1).upper()

            # Assunto amigável
            from datetime import datetime
            tipo = (tipo_relatorio_salvo or '').strip()
            if tipo == 'o_que_tem_hoje':
                assunto_base = "O que temos pra hoje"
            elif tipo == 'fechamento_dia' or tipo == 'fechamento':
                assunto_base = "Fechamento do dia"
            elif tipo:
                assunto_base = tipo.replace('_', ' ').capitalize()
            else:
                assunto_base = "Relatório"
            if categoria_assunto:
                assunto_base += f" - {str(categoria_assunto).upper()}"
            assunto = f"{assunto_base} - {datetime.now().strftime('%d/%m/%Y')}"

            try:
                if hasattr(self, 'chat_service') and self.chat_service:
                    resultado = self.chat_service._executar_funcao_tool('enviar_email_personalizado', {
                        'destinatarios': [email],
                        'assunto': assunto,
                        'conteudo': corpo,
                        'confirmar_envio': False
                    }, mensagem_original=mensagem)
                    if isinstance(resultado, dict) and resultado.get('resposta'):
                        # Marcar como precheck processado e, se pedido, acionar IA para refinar o email
                        resultado['_processado_precheck'] = True
                        if pedir_refino:
                            resultado['_deve_chamar_ia_para_refinar'] = True
                            # ✅ Fase 2C: impedir tool-calling durante refinamento
                            resultado['block_tool_calls_no_refino'] = True
                            resultado['_dados_email_preview'] = {
                                'destinatario': email,
                                'assunto': assunto,
                                'conteudo': corpo,
                                'assinatura_solicitada': assinatura_nome,
                                'fonte': 'last_visible_report_id'
                            }
                        logger.info(f"[EMAIL_PRECHECK] ✅ Email (report visível) preparado via enviar_email_personalizado. pedir_refino={pedir_refino}, assinatura={assinatura_nome}")
                        return resultado
            except Exception as e:
                logger.error(f"[EMAIL_PRECHECK] ❌ Erro ao montar email personalizado para report visível: {e}", exc_info=True)
            # Se falhar por algum motivo, continuar fluxo normal (sem retornar None silenciosamente)

        # 5. Verificar se a última resposta é um relatório analítico ad hoc (NÃO dashboard padrão)
        # Dashboards padrão têm títulos específicos que já são tratados em _precheck_envio_email_relatorio_generico
        titulos_dashboard_padrao = [
            'O QUE TEMOS PRA HOJE',
            'FECHAMENTO DO DIA',
            'PROCESSOS',
            'STATUS GERAL',
        ]
        
        eh_dashboard_padrao = any(titulo in ultima_resposta_texto.upper() for titulo in titulos_dashboard_padrao)
        
        # ✅ NOVO (12/01/2026): Verificar se é seção filtrada de relatório do sistema
        # Seções filtradas têm padrões específicos como "DIs EM ANÁLISE", "ALERTAS RECENTES", etc.
        secoes_filtradas_padrao = [
            'DIS EM ANÁLISE', 'DIs EM ANÁLISE', 'DI EM ANÁLISE',
            'DUIMPs EM ANÁLISE', 'DUIMP EM ANÁLISE',
            'ALERTAS RECENTES', 'ALERTAS',
            'PRONTOS PARA REGISTRO', 'PRONTOS PARA',
            'PENDÊNCIAS ATIVAS', 'PENDENCIAS ATIVAS',
            'ETA ALTERADO', 'ETAs ALTERADOS',
            'CHEGANDO HOJE', 'PROCESSOS CHEGANDO'
        ]
        eh_secao_filtrada = any(secao in ultima_resposta_texto.upper() for secao in secoes_filtradas_padrao)
        
        # ✅ VALIDAÇÃO DE COERÊNCIA (12/01/2026): Verificar se o que foi solicitado faz sentido
        # Diferença importante:
        # - ÚLTIMO HISTÓRICO: Última mensagem/resposta do histórico (pode ser notificação, resposta de processo, etc.)
        # - ÚLTIMO RELATÓRIO EM TELA: Relatório salvo que foi EXIBIDO na tela (o que realmente está visível)
        # 
        # REGRA: Sempre usar o último relatório SALVO (em tela), não o histórico
        # Mas validar coerência: se o usuário pediu "esse relatorio", deve haver um relatório salvo recente
        
        # ✅ VALIDAÇÃO 1: Se temos relatório salvo, validar se é coerente com a solicitação
        if tipo_relatorio_salvo:
            # Tem relatório salvo - validar coerência
            relatorio_recente = False
            try:
                if relatorio_salvo and relatorio_salvo.criado_em:
                    from datetime import datetime, timedelta
                    criado_em = datetime.fromisoformat(relatorio_salvo.criado_em.replace('Z', '+00:00').split('+')[0])
                    # Considerar recente se foi criado nas últimas 2 horas
                    if datetime.now() - criado_em < timedelta(hours=2):
                        relatorio_recente = True
                        logger.info(f"[EMAIL_PRECHECK] ✅ Relatório salvo é RECENTE (criado há {(datetime.now() - criado_em).total_seconds() / 60:.1f} minutos)")
                    else:
                        logger.warning(f"[EMAIL_PRECHECK] ⚠️ Relatório salvo é ANTIGO (criado há {(datetime.now() - criado_em).total_seconds() / 3600:.1f} horas) - pode não ser o que está na tela")
            except Exception as e:
                logger.warning(f"[EMAIL_PRECHECK] ⚠️ Erro ao validar data do relatório: {e}")
                # Se não conseguir validar data, assumir que é recente (melhor enviar do que não enviar)
                relatorio_recente = True
            
            # ✅ VALIDAÇÃO 2: Verificar se o texto do relatório salvo parece ser um relatório válido
            texto_valido = False
            if ultima_resposta_texto:
                # Verificar se tem características de relatório (não é apenas uma notificação ou resposta curta)
                tem_titulo_relatorio = any(titulo in ultima_resposta_texto.upper() for titulo in [
                    'O QUE TEMOS PRA HOJE', 'FECHAMENTO DO DIA', 'PROCESSOS', 'STATUS GERAL',
                    'DIS EM ANÁLISE', 'DUIMPs EM ANÁLISE', 'ALERTAS RECENTES', 'PRONTOS PARA REGISTRO'
                ])
                tem_conteudo_suficiente = len(ultima_resposta_texto.strip()) > 200  # Mínimo de 200 chars
                texto_valido = tem_titulo_relatorio and tem_conteudo_suficiente
                
                if not texto_valido:
                    logger.warning(f"[EMAIL_PRECHECK] ⚠️ Texto do relatório salvo não parece ser um relatório válido (título: {tem_titulo_relatorio}, tamanho: {len(ultima_resposta_texto)} chars)")
        
        # ✅ CRÍTICO: Se é dashboard padrão OU seção filtrada OU temos relatório salvo VÁLIDO, usar enviar_relatorio_email
        # Se temos relatório salvo VÁLIDO e RECENTE, SEMPRE usar enviar_relatorio_email
        # ✅ NOVO: Verificar se há [REPORT_META:...] na última resposta (indica relatório na tela)
        tem_report_meta = False
        if ultima_resposta_texto and '[REPORT_META:' in ultima_resposta_texto:
            tem_report_meta = True
            logger.info(f"[EMAIL_PRECHECK] ✅ [REPORT_META:...] detectado na última resposta - forçando uso de enviar_relatorio_email")
        
        if (tipo_relatorio_salvo and relatorio_recente and texto_valido) or eh_dashboard_padrao or eh_secao_filtrada or tem_report_meta:
            # Tem relatório salvo válido ou é dashboard padrão/seção filtrada - usar enviar_relatorio_email
            logger.info(f"[EMAIL_PRECHECK] {'Relatório salvo válido encontrado' if tipo_relatorio_salvo else ('Dashboard padrão' if eh_dashboard_padrao else 'Seção filtrada')} - usando enviar_relatorio_email")
            
            # ✅ CORREÇÃO (14/01/2026): Manter tipo original (não converter para "resumo" genérico)
            if tipo_relatorio_salvo:
                tipo_relatorio = tipo_relatorio_salvo
                # ✅ CORREÇÃO: Mapear apenas fechamento_dia → fechamento, manter o resto original
                if tipo_relatorio == 'fechamento_dia':
                    tipo_relatorio = 'fechamento'
                # ✅ NÃO converter o_que_tem_hoje para "resumo" - manter original
                logger.info(f'✅ Tipo de relatório obtido do relatório salvo: {tipo_relatorio_salvo} → {tipo_relatorio} (mantido original)')
            else:
                # Fallback: tentar detectar do texto
                try:
                    from services.report_service import obter_tipo_relatorio_salvo
                    tipo_relatorio_json = obter_tipo_relatorio_salvo(session_id)
                    if tipo_relatorio_json:
                        # ✅ CORREÇÃO: Manter tipo original (não converter para "resumo")
                        tipo_relatorio = tipo_relatorio_json
                        if tipo_relatorio == 'fechamento_dia':
                            tipo_relatorio = 'fechamento'
                        # ✅ NÃO converter o_que_tem_hoje para "resumo" - manter original
                        logger.info(f'✅ Tipo de relatório obtido do JSON: {tipo_relatorio_json} → {tipo_relatorio} (mantido original)')
                    else:
                        tipo_relatorio = 'o_que_tem_hoje'  # ✅ Padrão seguro (não "resumo")
                except Exception as e:
                    logger.warning(f'⚠️ Erro ao buscar tipo de relatório: {e}')
                    tipo_relatorio = 'o_que_tem_hoje'  # ✅ Padrão seguro (não "resumo")
            
            # Executar enviar_relatorio_email
            try:
                if hasattr(self, 'chat_service') and self.chat_service:
                    # ✅ REFINAMENTO 1: Extrair categoria do relatório filtrado se houver
                    categoria_para_enviar = None
                    if relatorio_salvo and relatorio_salvo.categoria:
                        categoria_para_enviar = relatorio_salvo.categoria
                        logger.info(f"[EMAIL_PRECHECK] ✅ Categoria extraída do relatório filtrado: {categoria_para_enviar}")
                    
                    # ✅✅✅ CRÍTICO (14/01/2026): Passar report_id nos argumentos para garantir que o relatório correto seja usado
                    # Isso evita que o sistema pegue o relatório errado quando há múltiplos relatórios
                    argumentos_tool = {
                        'destinatario': email,
                        'tipo_relatorio': tipo_relatorio,  # ✅ Mantido original (não "resumo")
                        'categoria': categoria_para_enviar,  # ✅ Incluir categoria se relatório foi filtrado
                        'confirmar_envio': False  # Sempre mostrar preview primeiro
                    }
                    
                    # ✅ CRÍTICO: Se encontrou relatório via last_visible_report_id, passar o ID explicitamente
                    if last_visible and last_visible.get('id'):
                        argumentos_tool['report_id'] = last_visible['id']
                        logger.info(f"[EMAIL_PRECHECK] ✅✅✅ Passando report_id explicitamente: {last_visible['id']} (domínio: {dominio_detectado})")
                    elif relatorio_salvo:
                        # Tentar extrair ID do texto_chat se não tiver last_visible
                        # ✅ CORREÇÃO (14/01/2026): re já está importado no topo - não reimportar
                        import json
                        match = re.search(r'\[REPORT_META:({.+?})\]', relatorio_salvo.texto_chat or '', re.DOTALL)
                        if match:
                            try:
                                meta_json = json.loads(match.group(1))
                                report_id_extraido = meta_json.get('id')
                                if report_id_extraido:
                                    argumentos_tool['report_id'] = report_id_extraido
                                    logger.info(f"[EMAIL_PRECHECK] ✅✅✅ Passando report_id extraído do texto: {report_id_extraido}")
                            except Exception as e:
                                logger.warning(f"[EMAIL_PRECHECK] ⚠️ Erro ao extrair report_id do texto: {e}")
                    
                    resultado = self.chat_service._executar_funcao_tool('enviar_relatorio_email', argumentos_tool, mensagem_original=mensagem)
                    
                    if resultado and resultado.get('sucesso'):
                        logger.info(f"[EMAIL_PRECHECK] ✅ Email de relatório montado e enviado via precheck (tipo: {tipo_relatorio})")
                        resultado['_processado_precheck'] = True
                        return resultado
                    else:
                        logger.warning(f"[EMAIL_PRECHECK] Erro ao executar enviar_relatorio_email: {resultado.get('erro') if resultado else 'resultado vazio'}")
            except Exception as e:
                logger.error(f"[EMAIL_PRECHECK] Erro ao executar enviar_relatorio_email: {e}", exc_info=True)
            
            # Se falhou, deixar outros prechecks tentarem
            return None
        elif tipo_relatorio_salvo and (not relatorio_recente or not texto_valido):
            # Tem relatório salvo mas não é válido/recente - avisar usuário
            logger.warning(f"[EMAIL_PRECHECK] ⚠️ Relatório salvo encontrado mas não é válido/recente - deixando IA processar para perguntar ao usuário")
            return None
        
        # 6. Verificar se é processo específico (formato ALH.0166/25, GPS.0010/24, etc.)
        # ✅ AJUSTE: Só considerar processo específico se a resposta for MUITO curta (menos de 200 chars)
        # Relatórios longos podem mencionar processos mas não são "sobre um processo específico"
        tem_processo_especifico = re.search(r'[A-Z]{2,4}\.\d{4}/\d{2}', ultima_resposta_texto)
        if tem_processo_especifico and len(ultima_resposta_texto.strip()) < 200:
            # É processo específico (resposta curta sobre um processo) - deixar _precheck_envio_email_processo processar
            logger.debug(f"[EMAIL_PRECHECK] Última resposta é processo específico (curta: {len(ultima_resposta_texto)} chars) - deixando _precheck_envio_email_processo processar")
            return None
        
        # 7. Verificar se tem NCM/alíquotas (já tratado em _precheck_envio_email_ncm)
        tem_ncm = (
            'NCM' in ultima_resposta_texto or 
            'NESH' in ultima_resposta_texto or 
            'Alíquotas' in ultima_resposta_texto or 
            'alíquotas' in ultima_resposta_texto or 
            'TECwin' in ultima_resposta_texto
        )
        if tem_ncm:
            # Tem NCM - deixar _precheck_envio_email_ncm processar
            logger.debug(f"[EMAIL_PRECHECK] Última resposta tem NCM - deixando _precheck_envio_email_ncm processar")
            return None
        
        # 8. ✅ TAREFA 3: É relatório analítico ad hoc! Usar enviar_email_personalizado com texto EXATO
        logger.info(f"[EMAIL_PRECHECK] 🎯 Relatório analítico ad hoc detectado - usando ultima_resposta_texto para enviar email")
        
        # 9. Gerar assunto heurístico (primeira linha ou título do relatório)
        assunto = self._gerar_assunto_relatorio_adhoc(ultima_resposta_texto)
        
        # 10. Executar enviar_email_personalizado com o texto EXATO da última resposta
        try:
            if hasattr(self, 'chat_service') and self.chat_service:
                resultado = self.chat_service._executar_funcao_tool('enviar_email_personalizado', {
                    'destinatarios': [email],
                    'assunto': assunto,
                    'conteudo': ultima_resposta_texto,  # ✅ CRÍTICO: Usar texto EXATO da última resposta (não re-gerar)
                    'confirmar_envio': False  # Sempre mostrar preview primeiro
                }, mensagem_original=mensagem)
                
                if resultado and resultado.get('sucesso'):
                    logger.info(f"[EMAIL_PRECHECK] ✅ Email de relatório analítico ad hoc montado e enviado via precheck (texto exato da última resposta)")
                    # ✅ CRÍTICO: Garantir que retorna com _processado_precheck para evitar que IA processe
                    resultado['_processado_precheck'] = True
                    return resultado
                else:
                    logger.warning(f"[EMAIL_PRECHECK] Erro ao executar enviar_email_personalizado: {resultado.get('erro') if resultado else 'resultado vazio'}")
        except Exception as e:
            logger.error(f"[EMAIL_PRECHECK] Erro ao executar enviar_email_personalizado para relatório ad hoc: {e}", exc_info=True)
        
        # Fallback: deixar IA processar
        logger.info(f"[EMAIL_PRECHECK] Comando de envio de relatório ad hoc detectado, mas deixando IA processar.")
        return None
    
    def _parece_comando_mandar_esse_relatorio(self, mensagem_lower: str) -> bool:
        """Detecta se a mensagem é um comando para mandar esse relatório."""
        # Verbos de enviar
        tem_verbo_enviar = any(verbo in mensagem_lower for verbo in [
            'envia', 'envie', 'mande', 'manda', 'enviar', 'mandar',
            'encaminha', 'encaminhe', 'encaminhar'
        ])
        
        if not tem_verbo_enviar:
            return False
        
        # Referências a relatório (incluindo typos comuns)
        # Verificar padrões com "esse" + "relatorio/raltatorio" (com ou sem "acima" ou "tambem")
        tem_esse_relatorio = any(palavra in mensagem_lower for palavra in [
            'esse relatorio', 'esse relatório', 'essa relatorio', 'essa relatório',
            'este relatorio', 'este relatório', 'esta relatorio', 'esta relatório',
            'esse raltatorio', 'esse ralatório',  # Typos comuns
            'esse realtorio', 'esse reltorio',  # ✅ NOVO: Typos adicionais
        ])
        
        # Verificar padrões com "relatorio/raltatorio" + "acima"
        tem_relatorio_acima = any(palavra in mensagem_lower for palavra in [
            'relatorio acima', 'relatório acima',
            'raltatorio acima', 'ralatório acima',  # Typos com "acima"
            'realtorio acima', 'reltorio acima',  # ✅ NOVO: Typos adicionais
        ])
        
        # ✅ NOVO: Verificar padrões com "relatorio" + "tambem/também"
        tem_relatorio_tambem = any(palavra in mensagem_lower for palavra in [
            'relatorio tambem', 'relatório também', 'relatorio também', 'relatório tambem',
            'raltatorio tambem', 'ralatório também',  # Typos com "também"
            'realtorio tambem', 'reltorio também',  # ✅ NOVO: Typos adicionais
        ])
        
        # ✅ NOVO: Verificar padrões com "um/uma" + "relatorio" (ex: "monte um realtorio")
        tem_um_relatorio = any(palavra in mensagem_lower for palavra in [
            'um relatorio', 'um relatório', 'uma relatorio', 'uma relatório',
            'um raltatorio', 'um ralatório', 'uma raltatorio', 'uma ralatório',
            'um realtorio', 'um reltorio', 'uma realtorio', 'uma reltorio',  # ✅ NOVO: Typos adicionais
        ])
        
        # Verificar outros padrões
        tem_outros_padroes = any(palavra in mensagem_lower for palavra in [
            'esse relatorio pro', 'esse relatorio para', 'esse relatório pro', 'esse relatório para',
            'esse relatorio por', 'esse relatório por',
            'isso por email', 'isso para', 'isso pro',
        ])
        
        tem_referencia_relatorio = tem_esse_relatorio or tem_relatorio_acima or tem_relatorio_tambem or tem_um_relatorio or tem_outros_padroes
        
        return tem_referencia_relatorio
    
    def _gerar_assunto_relatorio_adhoc(self, texto_relatorio: str) -> str:
        """
        Gera assunto heurístico para relatório analítico ad hoc.
        
        Tenta extrair da primeira linha/título do relatório.
        Se não encontrar, usa fallback genérico.
        """
        if not texto_relatorio:
            return "Relatório da consulta anterior"
        
        # Tentar extrair primeira linha não vazia (possível título)
        linhas = texto_relatorio.split('\n')
        for linha in linhas:
            linha_limpa = linha.strip()
            if linha_limpa and len(linha_limpa) > 5 and len(linha_limpa) < 100:
                # Remover emojis e formatação markdown básica
                linha_limpa = re.sub(r'[#*_`]', '', linha_limpa).strip()
                if linha_limpa:
                    return f"Relatório - {linha_limpa}"
        
        # Fallback genérico
        return "Relatório da consulta anterior"
    
    def _precheck_envio_email_livre(
        self,
        mensagem: str,
        mensagem_lower: str,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Precheck para comandos de envio de email livre (texto ditado pelo usuário)."""
        # Verificar se NÃO é relatório
        # ✅ NOVO: Incluir typos comuns na verificação
        eh_relatorio = any(palavra in mensagem_lower for palavra in [
            'relatorio', 'relatório', 'realtorio', 'reltorio', 'raltatorio', 'ralatório',  # ✅ NOVO: Typos adicionais
            'resumo', 'o que temos pra hoje', 'o que tem hoje',
            'dashboard', 'briefing', 'fechamento'
        ])
        
        if eh_relatorio:
            return None
        
        # ✅ CORREÇÃO: Padrões mais flexíveis para capturar variações
        # Ex: "mande um email para X avisando a ela que Y"
        # Ex: "mande um email para X dizendo que Y"
        padroes_email_livre = [
            # Padrão 1: "mande email para X avisando/dizendo/informando [a ela/que] Y"
            r'\b(manda|mandar|mande|envia|envie|enviar)\s+(um\s+|o\s+)?email\s+(para|por|via)\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:a\s+)?(?:ela|ele|eles|elas)?\s*(?:que\s+)?(?:dizendo|avisando|informando|que|com|:)',
            # Padrão 2: "mande email para X" (sem verbo explícito, mas tem texto depois)
            r'\b(manda|mandar|mande|envia|envie|enviar)\s+(um\s+|o\s+)?email\s+(para|por|via)\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+.+',
            # Padrão 3: "mande email para X" (sem texto explícito, mas mensagem tem conteúdo suficiente)
            r'\b(manda|mandar|mande|envia|envie|enviar)\s+(um\s+|o\s+)?email\s+(para|por|via)\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]
        
        tem_pedido_email_livre = any(re.search(p, mensagem_lower) for p in padroes_email_livre)
        
        # ✅ CORREÇÃO: Se tem padrão de email livre, verificar se NÃO é relatório ou NCM
        if tem_pedido_email_livre:
            # Verificar se NÃO é relatório
            eh_relatorio = any(palavra in mensagem_lower for palavra in [
                'relatorio', 'relatório', 'resumo', 'o que temos pra hoje', 'o que tem hoje',
                'dashboard', 'briefing', 'fechamento'
            ])
            if eh_relatorio:
                return None
            
            # Verificar se NÃO é NCM (já verificado antes, mas garantir)
            tem_palavra_ncm = any(palavra in mensagem_lower for palavra in [
                'ncm', 'aliquotas', 'alíquotas', 'classificacao', 'classificação', 'nesh', 'tecwin'
            ])
            if tem_palavra_ncm:
                return None
        
        if not tem_pedido_email_livre:
            return None
        
        # Extrair email
        email = None
        padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        match_email = re.search(padrao_email, mensagem_lower)
        if match_email:
            email = match_email.group(1)
        
        if not email:
            logger.info(f"[EMAIL_PRECHECK] Comando de envio de email livre detectado, mas não encontrou email. Deixando IA processar.")
            return None
        
        # Extrair texto da mensagem
        texto_mensagem = None
        # ✅ CORREÇÃO: Padrões mais flexíveis para capturar texto após email
        # Ex: "avisando a ela que quero jantar"
        # Ex: "dizendo que não vou poder ir"
        padroes_texto = [
            # Padrão 1: "avisando/dizendo/informando a ela/ele que Y"
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:a\s+)?(?:ela|ele|eles|elas)?\s*(?:que\s+)?(?:dizendo|avisando|informando)\s+(?:a\s+)?(?:ela|ele|eles|elas)?\s*(?:que\s+)?(.+)',
            # Padrão 2: "avisando/dizendo/informando que Y"
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:a\s+)?(?:ela|ele|eles|elas)?\s*(?:que\s+)?(?:dizendo|avisando|informando|que|com|:)\s+(.+)',
            # Padrão 3: "que Y" (sem verbo explícito)
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:a\s+)?(?:ela|ele|eles|elas)?\s+que\s+(.+)',
            # Padrão 4: Qualquer texto após o email
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(.+)',
        ]
        
        for padrao in padroes_texto:
            match_texto = re.search(padrao, mensagem_lower, re.IGNORECASE)
            if match_texto:
                texto_extraido = match_texto.group(1).strip()
                # Limpar texto: remover email duplicado, palavras de comando, etc.
                texto_extraido = re.sub(r'\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*$', '', texto_extraido)
                texto_extraido = re.sub(r'\s+(para|por|via|email)\s*$', '', texto_extraido, flags=re.IGNORECASE)
                # ✅ CORREÇÃO: Remover "a ela", "a ele" se estiver no início do texto extraído
                texto_extraido = re.sub(r'^(?:a\s+)?(?:ela|ele|eles|elas)\s+(?:que\s+)?', '', texto_extraido, flags=re.IGNORECASE)
                if texto_extraido and len(texto_extraido) > 3:
                    texto_mensagem = texto_extraido
                    logger.info(f"[EMAIL_PRECHECK] Texto extraído: '{texto_mensagem[:100]}...'")
                    break
        
        if not texto_mensagem:
            padrao_ultimo_recurso = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(.+)'
            match_ultimo = re.search(padrao_ultimo_recurso, mensagem_lower, re.IGNORECASE)
            if match_ultimo:
                texto_extraido = match_ultimo.group(1).strip()
                texto_extraido = re.sub(r'\s+(para|por|via|email)\s*$', '', texto_extraido, flags=re.IGNORECASE)
                if texto_extraido and len(texto_extraido) > 3:
                    texto_mensagem = texto_extraido
                    logger.info(f"[EMAIL_PRECHECK] Texto extraído (último recurso): '{texto_mensagem[:100]}...'")
        
        if not texto_mensagem:
            logger.info(f"[EMAIL_PRECHECK] Email livre detectado, mas não encontrou texto da mensagem. Pedindo esclarecimento.")
            return {
                'sucesso': False,
                'resposta': '⚠️ **Você quer que eu envie qual mensagem nesse e-mail?**\n\n💡 **Exemplo:** "manda um email para fulano@empresa.com dizendo que não vou poder ir para a reunião"',
                '_processado_precheck': True
            }
        
        logger.info(f"[EMAIL_PRECHECK] 🎯 Email livre detectado. Email: {email}, Texto: '{texto_mensagem[:50]}...'")
        
        # Montar email usando email_builder_service
        try:
            from services.email_builder_service import EmailBuilderService
            email_builder = EmailBuilderService()
            
            nome_usuario = getattr(self.chat_service, 'nome_usuario_atual', None) if hasattr(self, 'chat_service') else None
            
            resultado_email = email_builder.montar_email_livre(
                destinatario=email,
                texto_mensagem=texto_mensagem,
                nome_usuario=nome_usuario
            )
            
            if resultado_email.get('sucesso'):
                # ✅ NOVO: Retornar preview e pedir para IA refinar
                # A IA vai melhorar o texto do email antes de enviar
                preview_assunto = resultado_email.get('assunto', 'Mensagem via mAIke')
                preview_conteudo = resultado_email.get('conteudo', '')
                
                from datetime import datetime
                preview_texto = f"📧 **Email para Envio**\n\n"
                preview_texto += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                preview_texto += f"**De:** Sistema mAIke (Make Consultores)\n"
                preview_texto += f"**Para:** {email}\n"
                preview_texto += f"**Assunto:** {preview_assunto}\n"
                preview_texto += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                preview_texto += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                preview_texto += f"**Mensagem:**\n\n"
                preview_texto += f"{preview_conteudo}\n\n"
                preview_texto += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                preview_texto += f"⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"
                
                logger.info(f"[EMAIL_PRECHECK] ✅ Email livre detectado - retornando preview para IA refinar")
                
                # ✅ CRÍTICO (09/01/2026): Criar draft IMEDIATAMENTE quando preview é gerado
                draft_id = None
                try:
                    from services.email_draft_service import get_email_draft_service
                    draft_service = get_email_draft_service()
                    session_id_para_draft = session_id or (getattr(self.chat_service, 'session_id_atual', None) if hasattr(self, 'chat_service') and self.chat_service else None) or 'default'
                    draft_id = draft_service.criar_draft(
                        destinatarios=[email],
                        assunto=preview_assunto,
                        conteudo=preview_conteudo,
                        session_id=session_id_para_draft,
                        funcao_email='enviar_email_personalizado',
                        cc=None,
                        bcc=None
                    )
                    if draft_id:
                        logger.info(f'✅✅✅ [EMAIL_PRECHECK] Draft criado no precheck: {draft_id}')
                    else:
                        logger.warning(f'⚠️ [EMAIL_PRECHECK] Não foi possível criar draft, continuando sem draft')
                except Exception as e:
                    logger.warning(f'⚠️ [EMAIL_PRECHECK] Erro ao criar draft no precheck (continuando sem draft): {e}')
                
                # ✅ CRÍTICO: Salvar estado para confirmação posterior (igual aos outros tipos de email)
                if hasattr(self, 'chat_service') and self.chat_service:
                    payload_email = {
                        'funcao': 'enviar_email_personalizado',
                        'destinatarios': [email],
                        'assunto': preview_assunto,
                        'conteudo': preview_conteudo,
                        'tipo': 'email_livre',
                        'texto_original': texto_mensagem,
                        'draft_id': draft_id  # ✅ CRÍTICO: Incluir draft_id se criado
                    }
                    try:
                        if hasattr(self.chat_service, '_set_email_pendente'):
                            self.chat_service._set_email_pendente(session_id, payload_email)
                        else:
                            if not hasattr(self.chat_service, 'ultima_resposta_aguardando_email'):
                                self.chat_service.ultima_resposta_aguardando_email = None
                            self.chat_service.ultima_resposta_aguardando_email = payload_email
                    except Exception:
                        if not hasattr(self.chat_service, 'ultima_resposta_aguardando_email'):
                            self.chat_service.ultima_resposta_aguardando_email = None
                        self.chat_service.ultima_resposta_aguardando_email = payload_email
                    logger.info(f'✅✅✅ [EMAIL_PRECHECK] Estado salvo com draft_id: {draft_id}')
                
                return {
                    'sucesso': True,
                    'resposta': preview_texto,
                    'aguardando_confirmacao': True,
                    '_processado_precheck': True,
                    '_deve_chamar_ia_para_refinar': True,  # ✅ NOVO: Flag para indicar que IA deve refinar
                    '_dados_email_preview': {  # ✅ NOVO: Dados do preview para IA usar
                        'destinatario': email,
                        'assunto': preview_assunto,
                        'conteudo': preview_conteudo,
                        'texto_original': texto_mensagem
                    },
                    '_resultado_interno': {  # ✅ CRÍTICO: Salvar estado para confirmação COM draft_id
                        'ultima_resposta_aguardando_email': {
                            'funcao': 'enviar_email_personalizado',
                            'destinatarios': [email],
                            'assunto': preview_assunto,
                            'conteudo': preview_conteudo,
                            'tipo': 'email_livre',
                            'texto_original': texto_mensagem,
                            'draft_id': draft_id  # ✅ CRÍTICO: Incluir draft_id se criado
                        }
                    }
                }
            else:
                logger.warning(f"[EMAIL_PRECHECK] Erro ao montar email livre: {resultado_email.get('erro')}")
        except Exception as e:
            logger.error(f"[EMAIL_PRECHECK] Erro ao usar email_builder_service para email livre: {e}", exc_info=True)
        
        logger.info(f"[EMAIL_PRECHECK] Comando de envio de email livre detectado, mas deixando IA processar.")
        return None
    
    def _precheck_envio_email_processo(
        self,
        mensagem: str,
        mensagem_lower: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Precheck para comandos de envio de informações de processo/NCM por email."""
        # ✅ NOVO: Verificar se há relatório recente e mensagem é curta
        # Se sim, deixar o precheck de relatório genérico processar primeiro
        mensagem_curta = len(mensagem_lower.strip()) <= 80
        if mensagem_curta:
            try:
                from services.report_service import buscar_ultimo_relatorio
                session_id_para_buscar = session_id or getattr(self.chat_service, 'session_id_atual', None) if hasattr(self, 'chat_service') else None
                
                if session_id_para_buscar:
                    relatorio_teste = buscar_ultimo_relatorio(session_id_para_buscar)
                    if relatorio_teste and relatorio_teste.texto_chat:
                        # Há relatório recente e mensagem é curta - deixar precheck de relatório genérico processar
                        logger.info(f"[EMAIL_PRECHECK] Mensagem curta detectada + relatório recente encontrado. Deixando _precheck_envio_email_relatorio_generico processar primeiro.")
                        return None
            except Exception as e:
                logger.debug(f"[EMAIL_PRECHECK] Erro ao verificar relatório recente em _precheck_envio_email_processo: {e}")
        
        # ✅ SIMPLIFICAÇÃO: Checagem simples ANTES dos regex para decidir se é comando de email
        tem_verbo_email = any(v in mensagem_lower for v in ['manda', 'mandar', 'mande', 'envia', 'envie', 'enviar', 'monte', 'prepare', 'crie', 'montar', 'preparar', 'criar'])
        tem_token_email = 'email' in mensagem_lower
        
        if not (tem_verbo_email and tem_token_email):
            return None
        
        # Padrões para detectar envio de informações de processo por email
        # (Agora usados apenas para extrair conteúdo/email, não para decidir se é comando)
        padroes_email_processo = [
            # Padrões com "monte", "prepare", "crie"
            r'\b(monte|prepare|crie|montar|preparar|criar)\s+(um\s+)?email\s+(para|com|sobre)',
            r'\b(monte|prepare|crie|montar|preparar|criar)\s+(um\s+)?email',
            # Padrões com "envia", "envie", "manda", "mande"
            r'\b(envia|envie|manda|mandar|enviar|mande)\s+(esse|essa|este|esta)\s+(informacao|informação|info)\s+(para|por|via)\s+(o\s+)?email',
            r'\b(envia|envie|manda|mandar|enviar|mande)\s+(esse|essa|este|esta)\s+(informacao|informação|info)\s+email',
            r'\b(envia|envie|manda|mandar|enviar|mande)\s+(informacoes|informações|informacao|informação|info)\s+(para|por|via)\s+(o\s+)?email',
            r'\b(envia|envie|manda|mandar|enviar|mande)\s+(informacoes|informações|informacao|informação|info)\s+email',
            r'\b(envia|envie|manda|mandar|enviar|mande)\s+(para|por|via)\s+(o\s+)?email',
            r'\b(envia|envie|manda|mandar|enviar|mande)\s+email',
            # ✅ NOVO: Padrão abrangente para "mande o email", "manda um email", "envia o email", etc.
            r'\b(manda|mandar|mande|envia|envie|enviar)\s+(um\s+|o\s+)?email\b',
        ]
        
        # Verificar se algum padrão específico bate (para extrair conteúdo, não para decidir)
        tem_pedido_email_processo = any(re.search(p, mensagem_lower) for p in padroes_email_processo)
        
        # Se passou pela checagem simples mas não bateu nenhum padrão específico, ainda assim processar
        # (pode ser um comando de email genérico)
        
        # Extrair email se mencionado
        email = None
        padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
        match_email = re.search(padrao_email, mensagem_lower)
        if match_email:
            email = match_email.group(1)
        
        # ✅ NOVO: Se não encontrou email, tentar buscar no histórico (pode ter sido mencionado antes)
        if not email and historico and len(historico) > 0:
            for i in range(len(historico) - 1, -1, -1):
                msg_anterior = historico[i].get('mensagem', '')
                if msg_anterior:
                    match_email_hist = re.search(padrao_email, msg_anterior.lower())
                    if match_email_hist:
                        email = match_email_hist.group(1)
                        logger.info(f"[EMAIL_PRECHECK] Email encontrado no histórico: {email}")
                        break
        
        # ✅ CRÍTICO: Verificar se a mensagem atual tem conteúdo próprio (não é referência a relatório anterior)
        # Padrões que indicam referência ao anterior: "esse", "essa", "este", "esta", "relatorio", "relatório", "resumo", "briefing", "acima", "anterior"
        eh_referencia_anterior = any(palavra in mensagem_lower for palavra in [
            'esse relatorio', 'esse relatório', 'essa informação', 'essa informacao', 
            'esse informacao', 'esse informação', 'esse resumo', 'esse briefing',
            'essa relatorio', 'essa relatório', 'este relatorio', 'este relatório',
            'esta informação', 'esta informacao', 'mande esse', 'envia esse', 'envie esse',
            'mande esse relatorio', 'envia esse relatorio', 'mande esse relatório', 'envia esse relatório',
            'esse relatorio acima', 'esse relatório acima', 'essa informação acima', 'essa informacao acima',
            'acima', 'anterior', 'do histórico', 'da resposta anterior'
        ])
        
        # ✅ CRÍTICO: Se a mensagem tem conteúdo próprio (não é referência), usar o conteúdo da mensagem
        conteudo_email = None
        if not eh_referencia_anterior:
            # A mensagem tem conteúdo próprio - extrair o conteúdo após "de que", "que", "sobre", etc.
            # Padrões mais específicos primeiro
            padroes_conteudo = [
                # "envie (um) email para X de que Y" ou "envie (um) email para X que Y"
                r'(?:um\s+)?email\s+(?:para|por|via)\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:de\s+que|que|sobre|informando|explicando|dizendo)\s+(.+)',
                # "envie para X de que Y" ou "envie para X que Y"
                r'(?:para|por|via)\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:de\s+que|que|sobre|informando|explicando|dizendo)\s+(.+)',
                # "de que Y" ou "que Y" no final (pode estar em qualquer lugar da mensagem)
                r'(?:de\s+que|que|sobre|informando|explicando|dizendo)\s+(.+)',
            ]
            
            for padrao in padroes_conteudo:
                match_conteudo = re.search(padrao, mensagem_lower, re.IGNORECASE)
                if match_conteudo:
                    conteudo_extraido = match_conteudo.group(1).strip()
                    # Remover o email se estiver no final
                    conteudo_extraido = re.sub(r'\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*$', '', conteudo_extraido)
                    # Remover palavras finais comuns que não fazem parte do conteúdo
                    conteudo_extraido = re.sub(r'\s+(para|por|via|email)\s*$', '', conteudo_extraido, flags=re.IGNORECASE)
                    if conteudo_extraido and len(conteudo_extraido) > 5:  # Pelo menos 5 caracteres
                        conteudo_email = conteudo_extraido
                        logger.info(f"[EMAIL_PRECHECK] Conteúdo próprio extraído da mensagem: '{conteudo_email[:100]}...'")
                        break
            
            # Se não encontrou com padrões, tentar pegar tudo após o email (último recurso)
            if not conteudo_email:
                # Padrão: "envie (um) email para X Y" (sem "de que")
                padrao_geral = r'(?:um\s+)?email\s+(?:para|por|via)\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(.+)'
                match_geral = re.search(padrao_geral, mensagem_lower, re.IGNORECASE)
                if match_geral:
                    conteudo_extraido = match_geral.group(1).strip()
                    # Remover palavras finais comuns
                    conteudo_extraido = re.sub(r'\s+(para|por|via|email)\s*$', '', conteudo_extraido, flags=re.IGNORECASE)
                    if conteudo_extraido and len(conteudo_extraido) > 3:  # Reduzido para 3 caracteres
                        conteudo_email = conteudo_extraido
                        logger.info(f"[EMAIL_PRECHECK] Conteúdo próprio extraído (padrão geral): '{conteudo_email[:100]}...'")
        
        # ✅ Se é referência ao anterior OU não encontrou conteúdo próprio, buscar no histórico
        if not conteudo_email and historico and len(historico) > 0:
            # Procurar na última resposta por informações relevantes (processo, NCM, alíquotas, NESH, etc.)
            for i in range(len(historico) - 1, -1, -1):
                resposta_anterior = historico[i].get('resposta', '')
                if resposta_anterior:
                    # ✅ MELHORIA: Verificar se contém informações de processo (mais padrões)
                    # Detectar resposta de "situação do processo" ou consulta de processo específico
                    tem_processo = (
                        'Processo' in resposta_anterior or 
                        'CE' in resposta_anterior or 
                        'DI' in resposta_anterior or 
                        'DUIMP' in resposta_anterior or
                        'Categoria:' in resposta_anterior or
                        'Etapa no Kanban:' in resposta_anterior or
                        'Modal:' in resposta_anterior or
                        'Conhecimento de Embarque:' in resposta_anterior or
                        'Declaração de Importação:' in resposta_anterior or
                        'Pendências:' in resposta_anterior or
                        'Datas Importantes:' in resposta_anterior or
                        re.search(r'[A-Z]{2,4}\.\d{4}/\d{2}', resposta_anterior)  # Formato de processo: ALH.0166/25
                    )
                    # ✅ MELHORIA: Verificar se contém informações de NCM/alíquotas (mais padrões)
                    tem_ncm = ('NCM' in resposta_anterior or 'NESH' in resposta_anterior or 'Alíquotas' in resposta_anterior or 'alíquotas' in resposta_anterior or 'II:' in resposta_anterior or 'IPI:' in resposta_anterior or 'PIS:' in resposta_anterior or 'COFINS:' in resposta_anterior or 'ICMS:' in resposta_anterior or 'II (' in resposta_anterior or 'IPI (' in resposta_anterior or 'TECwin' in resposta_anterior or 'Descrição:' in resposta_anterior)
                    # Verificar se contém informações técnicas relevantes
                    tem_info_tecnica = ('Confiança' in resposta_anterior or 'Explicação' in resposta_anterior or 'Nota Explicativa' in resposta_anterior or 'classificação' in resposta_anterior.lower() or 'Unidade de Medida' in resposta_anterior or 'Fonte:' in resposta_anterior)
                    
                    if tem_processo or tem_ncm or tem_info_tecnica:
                        conteudo_email = resposta_anterior
                        tipo_conteudo = 'processo' if tem_processo else ('NCM/alíquotas' if tem_ncm else 'informações técnicas')
                        logger.info(f"[EMAIL_PRECHECK] ✅ Informações de {tipo_conteudo} encontradas na resposta anterior (índice {i}) - usando como conteúdo do email")
                        break
        
        # ✅ CRÍTICO: Se não encontrou conteúdo mas tem email E não é referência ao anterior, gerar conteúdo da mensagem
        if not conteudo_email and email and not eh_referencia_anterior:
            # Tentar extrair conteúdo diretamente da mensagem (último recurso)
            # Padrão: "envie (um) email para X Y" - pegar tudo após o email
            padrao_ultimo_recurso = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:de\s+que|que|sobre|informando|explicando|dizendo)?\s*(.+)'
            match_ultimo = re.search(padrao_ultimo_recurso, mensagem_lower, re.IGNORECASE)
            if match_ultimo:
                conteudo_extraido = match_ultimo.group(1).strip()
                # Remover palavras finais comuns que não fazem parte do conteúdo
                conteudo_extraido = re.sub(r'\s+(para|por|via|email|reuniao|reunião)\s*$', '', conteudo_extraido, flags=re.IGNORECASE)
                if conteudo_extraido and len(conteudo_extraido) > 3:  # Pelo menos 3 caracteres
                    conteudo_email = conteudo_extraido
                    logger.info(f"[EMAIL_PRECHECK] Conteúdo extraído (último recurso): '{conteudo_email[:100]}...'")
        
        # ✅ CRÍTICO: Se não encontrou conteúdo mas tem email E não é referência ao anterior, usar a mensagem completa como conteúdo
        if not conteudo_email and email and not eh_referencia_anterior:
            # Tentar usar a mensagem completa como conteúdo (removendo a parte do comando)
            # Ex: "envie um email para X de que Y" → usar "Y" ou a mensagem completa
            conteudo_email = mensagem
            # Tentar remover a parte do comando se possível
            padrao_limpar_comando = r'^(?:envie|envia|mande|manda|enviar|mandar)\s+(?:um\s+)?email\s+(?:para|por|via)\s+[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s+(?:de\s+que|que|sobre|informando|explicando|dizendo)?\s*(.+)'
            match_limpar = re.search(padrao_limpar_comando, mensagem_lower, re.IGNORECASE)
            if match_limpar and match_limpar.group(1):
                conteudo_email = match_limpar.group(1).strip()
                logger.info(f"[EMAIL_PRECHECK] Conteúdo extraído (fallback mensagem completa): '{conteudo_email[:100]}...'")
            else:
                logger.info(f"[EMAIL_PRECHECK] Usando mensagem completa como conteúdo: '{conteudo_email[:100]}...'")
        
        # ✅ CORREÇÃO: Se ainda não encontrou conteúdo mas tem email, deixar a IA processar (ela pode gerar o conteúdo)
        if not conteudo_email:
            logger.info(f"[EMAIL_PRECHECK] Comando de envio por email detectado, mas não encontrou conteúdo. Deixando IA processar para gerar conteúdo baseado na mensagem.")
            # Se tem email, deixar a IA processar (ela pode gerar o conteúdo baseado na mensagem atual)
            if email:
                return None  # Deixar IA processar
            else:
                return None  # Sem email nem conteúdo, deixar IA processar
        
        if not email:
            logger.info(f"[EMAIL_PRECHECK] Comando de envio de processo por email detectado, mas não encontrou email na mensagem. Deixando IA processar.")
            return None  # Deixar IA processar (ela pode extrair o email)
        
        logger.info(
            f"[EMAIL_PRECHECK] Comando de envio de informações por email detectado. Email: {email} | Conteúdo: '{conteudo_email[:100] if conteudo_email else 'N/A'}...' | É referência anterior: {eh_referencia_anterior}"
        )
        
        # ✅ CRÍTICO: Se não é referência ao anterior e tem conteúdo próprio, SEMPRE forçar enviar_email_personalizado
        if not eh_referencia_anterior and conteudo_email and email:
            logger.info(f"[EMAIL_PRECHECK] ✅✅✅ Email simples detectado com conteúdo próprio - FORÇANDO enviar_email_personalizado")
        
        # ✅ NOVO: Verificar se é email com NCM/alíquotas e usar email_builder_service
        # ✅ CRÍTICO: Verificar tanto na mensagem atual quanto no conteúdo extraído
        tem_ncm_aliquotas_na_mensagem = any(palavra in mensagem_lower for palavra in [
            'aliquotas', 'alíquotas', 'classificacao', 'classificação', 'ncm', 'nesh',
            'tecwin', 'explicando o porque', 'explicando o porquê', 'explicando porque',
            'explicando porquê', 'justificativa', 'justificativa da classificacao',
            'justificativa da classificação', 'porque do ncm', 'porquê do ncm',
            'porque da classificacao', 'porquê da classificação'
        ])
        
        tem_ncm_aliquotas_no_conteudo = (
            'NCM' in (conteudo_email or '') or 
            'NESH' in (conteudo_email or '') or 
            'Alíquotas' in (conteudo_email or '') or 
            'alíquotas' in (conteudo_email or '') or 
            'II:' in (conteudo_email or '') or 
            'IPI:' in (conteudo_email or '') or 
            'PIS:' in (conteudo_email or '') or 
            'COFINS:' in (conteudo_email or '') or 
            'ICMS:' in (conteudo_email or '') or 
            'TECwin' in (conteudo_email or '') or 
            'classificação fiscal' in (conteudo_email or '').lower() or 
            'classificacao fiscal' in (conteudo_email or '').lower()
        )
        
        tem_ncm_aliquotas = tem_ncm_aliquotas_na_mensagem or tem_ncm_aliquotas_no_conteudo
        
        # ✅ NOVO: Se detectou NCM/alíquotas, usar email_builder_service
        if tem_ncm_aliquotas:
            logger.info(f"[EMAIL_PRECHECK] 🎯 Email com NCM/alíquotas detectado - usando email_builder_service")
            try:
                from services.email_builder_service import EmailBuilderService
                email_builder = EmailBuilderService()
                
                # Extrair contexto NCM do histórico
                contexto_ncm = email_builder.extrair_contexto_ncm_do_historico(historico, session_id)
                
                if contexto_ncm and contexto_ncm.get('ncm'):
                    logger.info(f"[EMAIL_PRECHECK] ✅ Contexto NCM encontrado: {contexto_ncm.get('ncm')}")
                    # Montar email usando email_builder_service
                    resultado_email = email_builder.montar_email_classificacao_ncm(
                        destinatario=email,
                        contexto_ncm=contexto_ncm,
                        texto_pedido_usuario=mensagem,
                        nome_usuario=getattr(self.chat_service, 'nome_usuario_atual', None) if hasattr(self, 'chat_service') else None
                    )
                    
                    if resultado_email.get('sucesso'):
                        # Chamar enviar_email_personalizado com o email montado
                        if hasattr(self, 'chat_service') and self.chat_service:
                            resultado = self.chat_service._executar_funcao_tool('enviar_email_personalizado', {
                                'destinatarios': [email],
                                'assunto': resultado_email.get('assunto', 'Classificação Fiscal e Alíquotas'),
                                'conteudo': resultado_email.get('conteudo', ''),
                                'confirmar_envio': False  # Sempre mostrar preview primeiro
                            }, mensagem_original=mensagem)
                            
                            if resultado and resultado.get('sucesso'):
                                logger.info(f"[EMAIL_PRECHECK] ✅ Email de classificação NCM montado e enviado via precheck")
                                return resultado
                            else:
                                logger.warning(f"[EMAIL_PRECHECK] Erro ao executar enviar_email_personalizado: {resultado.get('erro') if resultado else 'resultado vazio'}")
                    else:
                        logger.warning(f"[EMAIL_PRECHECK] Erro ao montar email de classificação NCM: {resultado_email.get('erro')}")
                else:
                    logger.warning(f"[EMAIL_PRECHECK] ⚠️ Contexto NCM não encontrado")
                    # ✅ Smoke/segurança: sem contexto de NCM, NÃO interceptar (deixar IA/fluxo normal decidir)
                    return None
            except Exception as e:
                logger.error(f"[EMAIL_PRECHECK] Erro ao usar email_builder_service: {e}", exc_info=True)
                # Continuar com fluxo normal se der erro
        
        # ✅ Smoke/segurança: este precheck é para processo/NCM via histórico.
        # Se NÃO é referência ao anterior, não forçar execução aqui (evita engolir fluxos de email livre e quebrar testes).
        if not eh_referencia_anterior:
            return None

        # ✅ NOVO: Forçar chamada da função enviar_email_personalizado via chat_service
        # Isso garante que a função seja chamada mesmo se a IA não chamar
        try:
            # Usar o chat_service para executar a função diretamente
            if hasattr(self, 'chat_service') and self.chat_service:
                # ✅ CORREÇÃO: Gerar assunto apropriado baseado no conteúdo
                assunto_email = 'Informações Solicitadas'
                
                # ✅ CRÍTICO: Se o conteúdo veio da mensagem atual (não do histórico), usar assunto e formatação apropriados
                if not eh_referencia_anterior and conteudo_email and len(conteudo_email) < 500:
                    # Conteúdo curto da mensagem atual - assunto genérico e formatação profissional
                    assunto_email = 'Mensagem'
                    conteudo_formatado = f"Olá,\n\n{conteudo_email}\n\nAtenciosamente,\nMaike - Assistente de COMEX\nMake Consultores"
                    logger.info(f"[EMAIL_PRECHECK] Email simples detectado - usando conteúdo da mensagem atual: '{conteudo_email[:100]}...'")
                else:
                    # Conteúdo do histórico - detectar tipo e usar como está
                    conteudo_formatado = conteudo_email
                    # ✅ MELHORIA: Detectar melhor conteúdo de NCM/alíquotas (já verificado acima)
                    if tem_ncm_aliquotas:
                        assunto_email = 'Classificação Fiscal e Alíquotas'
                    elif 'Processo' in conteudo_email or 'O QUE TEMOS PRA HOJE' in conteudo_email or 'FECHAMENTO DO DIA' in conteudo_email:
                        assunto_email = 'Informações do Processo'
                    else:
                        assunto_email = 'Informações Solicitadas'
                    logger.info(f"[EMAIL_PRECHECK] Email com conteúdo do histórico - assunto: {assunto_email}")
                
                resultado = self.chat_service._executar_funcao_tool('enviar_email_personalizado', {
                    'destinatarios': [email],
                    'assunto': assunto_email,
                    'conteudo': conteudo_formatado,
                    'confirmar_envio': False  # Sempre mostrar preview primeiro
                }, mensagem_original=mensagem)
                
                if resultado and resultado.get('sucesso'):
                    logger.info(f"[EMAIL_PRECHECK] Função enviar_email_personalizado executada com sucesso via precheck")
                    return resultado
                else:
                    logger.warning(f"[EMAIL_PRECHECK] Erro ao executar enviar_email_personalizado: {resultado.get('erro') if resultado else 'resultado vazio'}")
            else:
                logger.warning(f"[EMAIL_PRECHECK] chat_service não disponível no precheck")
        except Exception as e:
            logger.error(f"[EMAIL_PRECHECK] Erro ao executar enviar_email_personalizado via precheck: {e}", exc_info=True)
        
        # Fallback: deixar a IA processar
        logger.info(f"[EMAIL_PRECHECK] Comando de envio de processo por email detectado, mas deixando IA processar via enviar_email_personalizado para respeitar confirmação.")
        return None  # Deixar a IA processar via tool calling (enviar_email_personalizado)
