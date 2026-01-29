"""
MessageProcessingService - Core comum de processamento de mensagens.

Este serviço extrai a lógica comum entre processar_mensagem() e processar_mensagem_stream(),
eliminando duplicação e facilitando manutenção.

A ideia é que processar_mensagem() e processar_mensagem_stream() sejam apenas "views"
diferentes do mesmo core: um retorna resultado final, outro retorna generator de chunks.

Data: 09/01/2026
Status: ⏳ EM DESENVOLVIMENTO
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """
    Resultado estruturado do processamento de mensagem.
    
    Este é o formato comum que o core produz, independente de streaming ou não.
    """
    resposta: str
    sucesso: bool = True
    tool_calls: Optional[List[Dict]] = None
    aguardando_confirmacao: bool = False
    ultima_resposta_aguardando_email: Optional[Dict] = None
    ultima_resposta_aguardando_duimp: Optional[Dict] = None
    comando_interface: Optional[Dict] = None
    acao: Optional[str] = None
    erro: Optional[str] = None
    _resultado_interno: Optional[Dict] = None
    eh_pedido_melhorar_email: bool = False  # ✅ FASE 2: Flag para indicar pedido de melhorar email
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte ProcessingResult para dict (compatibilidade com código existente).
        
        Returns:
            Dict com todos os campos do ProcessingResult
        """
        return {
            'resposta': self.resposta,
            'sucesso': self.sucesso,
            'tool_calls': self.tool_calls,
            'aguardando_confirmacao': self.aguardando_confirmacao,
            'ultima_resposta_aguardando_email': self.ultima_resposta_aguardando_email,
            'ultima_resposta_aguardando_duimp': self.ultima_resposta_aguardando_duimp,
            'comando_interface': self.comando_interface,
            'acao': self.acao,
            'erro': self.erro,
            '_resultado_interno': self._resultado_interno,
            'eh_pedido_melhorar_email': self.eh_pedido_melhorar_email
        }


class MessageProcessingService:
    """
    Serviço centralizado para processamento de mensagens.
    
    Este serviço contém a lógica comum entre processar_mensagem() e processar_mensagem_stream().
    Ele produz um ProcessingResult estruturado, que pode ser:
    - Retornado diretamente (modo não-streaming)
    - Transformado em chunks (modo streaming)
    """
    
    def __init__(
        self,
        confirmation_handler=None,
        precheck_service=None,
        tool_execution_service=None,
        prompt_builder=None,
        ai_service=None,
        # Funções auxiliares do chat_service
        obter_email_para_enviar=None,
        extrair_processo_referencia=None,
        response_formatter=None,
        # ... outros helpers conforme necessário
    ):
        """
        Inicializa o serviço.
        
        Args:
            confirmation_handler: Handler para confirmações (email, DUIMP, etc.)
            precheck_service: Serviço de precheck (detecção proativa)
            tool_execution_service: Serviço de execução de tools
            prompt_builder: Builder de prompts
            ai_service: Serviço de IA
            obter_email_para_enviar: Função helper para obter email
            extrair_processo_referencia: Função helper para extrair processo
            response_formatter: Formatter para combinar resultados de tools
        """
        self.confirmation_handler = confirmation_handler
        self.precheck_service = precheck_service
        self.tool_execution_service = tool_execution_service
        self.prompt_builder = prompt_builder
        self.ai_service = ai_service
        self.obter_email_para_enviar = obter_email_para_enviar
        self.extrair_processo_referencia = extrair_processo_referencia
        self.response_formatter = response_formatter
    
    def _detectar_comando_interface(self, mensagem: str) -> Optional[Dict[str, Any]]:
        """
        Detecta comandos de interface (menu, conciliação, etc.).
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            Dict com comando de interface ou None
        """
        try:
            from services.message_intent_service import MessageIntentService
            # MessageIntentService funciona sem chat_service para detecção de comandos
            intent_service = MessageIntentService(chat_service=None)
            comando = intent_service.detectar_comando_interface(mensagem)
            if comando:
                logger.info(f"🎯 [CORE] Comando de interface detectado: {comando}")
            return comando
        except Exception as e:
            logger.debug(f"⚠️ [CORE] Erro ao detectar comando de interface: {e}")
            return None
    
    def _detectar_melhorar_email(self, mensagem: str) -> bool:
        """
        Detecta se usuário está pedindo para melhorar/elaborar email.
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            True se é pedido para melhorar email, False caso contrário
        """
        mensagem_lower = mensagem.lower().strip()
        padroes_melhorar = [
            'melhore', 'melhorar', 'melhore o email', 'melhore esse email',
            'elabore', 'elaborar', 'elabore melhor', 'elabora melhor',
            'reescrever', 'reescreva', 'reescreva melhor', 'melhore esse',
            'torne mais formal', 'torne mais informal', 'torne mais profissional',
            'melhore a escrita', 'melhore o texto', 'melhore o conteúdo'
        ]
        
        for padrao in padroes_melhorar:
            if padrao in mensagem_lower:
                logger.info(f"🎯 [CORE] Pedido para melhorar email detectado: '{padrao}'")
                return True
        
        return False
    
    def processar_core(
        self,
        mensagem: str,
        historico: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        nome_usuario: Optional[str] = None,
        ultima_resposta_aguardando_email: Optional[Dict] = None,
        ultima_resposta_aguardando_duimp: Optional[Dict] = None,
        usar_tool_calling: bool = True,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> ProcessingResult:
        """
        Core de processamento de mensagem.
        
        Este método contém a lógica comum entre processar_mensagem() e processar_mensagem_stream().
        Ele produz um ProcessingResult estruturado que pode ser usado por ambos.
        
        Args:
            mensagem: Mensagem do usuário
            historico: Histórico de mensagens
            session_id: ID da sessão
            nome_usuario: Nome do usuário
            ultima_resposta_aguardando_email: Estado de email pendente
            ultima_resposta_aguardando_duimp: Estado de DUIMP pendente
            usar_tool_calling: Se deve usar tool calling
            model: Modelo de IA a usar
            temperature: Temperatura para geração
        
        Returns:
            ProcessingResult com resultado estruturado
        """
        historico = historico or []
        
        # ✅ FASE 2: Detecções comuns
        
        # 1. Detectar comandos de interface (menu, conciliação, etc.)
        comando_interface = self._detectar_comando_interface(mensagem)
        if comando_interface:
            return ProcessingResult(
                resposta=f"✅ {comando_interface.get('tipo', 'comando')} detectado!",
                sucesso=True,
                tool_calls=[],
                aguardando_confirmacao=False,
                ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
                ultima_resposta_aguardando_duimp=ultima_resposta_aguardando_duimp,
                comando_interface=comando_interface,
                acao='comando_interface',
                erro=None,
                _resultado_interno=None
            )
        
        # 2. Detectar melhorar email (se há email em preview)
        eh_pedido_melhorar_email = False
        if ultima_resposta_aguardando_email:
            eh_pedido_melhorar_email = self._detectar_melhorar_email(mensagem)
            if eh_pedido_melhorar_email:
                logger.info(f'✅✅✅ [CORE] Pedido para melhorar email detectado: "{mensagem}"')
        
        # ✅ FASE 3: Detecções de confirmação (via ConfirmationHandler)
        dados_email_para_enviar = ultima_resposta_aguardando_email
        
        # Se há email pendente e não é pedido de melhorar, verificar confirmação
        if dados_email_para_enviar and not eh_pedido_melhorar_email and self.confirmation_handler:
            try:
                eh_confirmacao_email = self.confirmation_handler.detectar_confirmacao_email(
                    mensagem=mensagem,
                    dados_email_para_enviar=dados_email_para_enviar
                )
                
                if eh_confirmacao_email:
                    logger.info(f'✅✅✅ [CORE] Confirmação de email detectada - processando envio')
                    resultado_confirmacao = self.confirmation_handler.processar_confirmacao_email(
                        mensagem=mensagem,
                        dados_email_para_enviar=dados_email_para_enviar,
                        session_id=session_id
                    )
                    # Converter resultado para ProcessingResult
                    return ProcessingResult(
                        resposta=resultado_confirmacao.get('resposta', ''),
                        sucesso=resultado_confirmacao.get('sucesso', True),
                        tool_calls=None,
                        aguardando_confirmacao=False,
                        ultima_resposta_aguardando_email=None,  # Limpar após envio
                        ultima_resposta_aguardando_duimp=ultima_resposta_aguardando_duimp,
                        comando_interface=None,
                        acao='email_enviado',
                        erro=resultado_confirmacao.get('erro'),
                        _resultado_interno=None,
                        eh_pedido_melhorar_email=False
                    )
            except Exception as e:
                logger.error(f'❌ [CORE] Erro ao processar confirmação de email: {e}', exc_info=True)
                # Continuar processamento normal se confirmação falhar
        
        # Se há DUIMP pendente, verificar confirmação
        if ultima_resposta_aguardando_duimp and self.confirmation_handler:
            try:
                eh_confirmacao_duimp = self.confirmation_handler.detectar_confirmacao_duimp(
                    mensagem=mensagem,
                    estado_duimp=ultima_resposta_aguardando_duimp
                )
                
                if eh_confirmacao_duimp:
                    logger.info(f'✅✅✅ [CORE] Confirmação de DUIMP detectada - processando criação')
                    resultado_confirmacao = self.confirmation_handler.processar_confirmacao_duimp(
                        mensagem=mensagem,
                        estado_duimp=ultima_resposta_aguardando_duimp,
                        session_id=session_id
                    )
                    # Converter resultado para ProcessingResult
                    return ProcessingResult(
                        resposta=resultado_confirmacao.get('resposta', ''),
                        sucesso=resultado_confirmacao.get('sucesso', True),
                        tool_calls=None,
                        aguardando_confirmacao=False,
                        ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
                        ultima_resposta_aguardando_duimp=None,  # Limpar após criação
                        comando_interface=None,
                        acao='duimp_criada',
                        erro=resultado_confirmacao.get('erro'),
                        _resultado_interno=None,
                        eh_pedido_melhorar_email=eh_pedido_melhorar_email
                    )
            except Exception as e:
                logger.error(f'❌ [CORE] Erro ao processar confirmação de DUIMP: {e}', exc_info=True)
                # Continuar processamento normal se confirmação falhar
        
        # ✅ FASE 3: Detecção de correção de email (se há email pendente)
        # Isso deve ser feito ANTES do precheck para evitar que precheck pegue contexto errado
        eh_correcao_email_destinatario = False
        if dados_email_para_enviar and not eh_pedido_melhorar_email:
            # Detectar se usuário está apenas corrigindo o email destinatário
            # Padrão: "mande para X@gmail.com" ou "corrija o email para X@gmail.com"
            import re
            mensagem_lower_check = mensagem.lower().strip()
            padrao_email = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
            match_email = re.search(padrao_email, mensagem_lower_check)
            
            if match_email:
                email_novo = match_email.group(1)
                verbos_enviar = ['mande', 'manda', 'envie', 'envia', 'enviar', 'mandar']
                verbos_corrigir = ['corrija', 'corrigir', 'correto', 'corrige', 'corriga', 'corrigido']
                tem_verbo_enviar = any(verbo in mensagem_lower_check for verbo in verbos_enviar)
                tem_verbo_corrigir = any(verbo in mensagem_lower_check for verbo in verbos_corrigir)
                palavras_mensagem = mensagem_lower_check.split()
                tem_poucas_palavras = len(palavras_mensagem) <= 6
                mensagem_curta = len(mensagem_lower_check) < 60
                palavras_excluir = ['relatorio', 'relatório', 'resumo', 'santander', 'bnd', 'processo', 'extrato', 'dados', 'informacoes', 'informações']
                tem_palavra_excluir = any(palavra in mensagem_lower_check for palavra in palavras_excluir)
                padrao_correcao_email = re.search(r'corrig[aei]r?\s+(?:o\s+)?email\s+(?:para\s+)?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', mensagem_lower_check)
                eh_padrao_correcao = padrao_correcao_email is not None
                
                eh_apenas_correcao_email = (
                    (tem_verbo_enviar or tem_verbo_corrigir or 'para' in mensagem_lower_check or len(palavras_mensagem) <= 3 or eh_padrao_correcao)
                    and mensagem_curta
                    and tem_poucas_palavras
                    and not tem_palavra_excluir
                )
                
                if eh_apenas_correcao_email:
                    eh_correcao_email_destinatario = True
                    logger.info(f'✅✅✅ [CORE] Correção de email destinatário detectada: "{email_novo}"')
                    # Atualizar destinatário no dados_email_para_enviar
                    dados_email_para_enviar = dados_email_para_enviar.copy() if isinstance(dados_email_para_enviar, dict) else {}
                    dados_email_para_enviar['destinatarios'] = [email_novo]
                    # Retornar preview atualizado
                    funcao_email = dados_email_para_enviar.get('funcao', 'enviar_email_personalizado')
                    if funcao_email == 'enviar_email_personalizado':
                        preview = f"📧 **Preview do Email (Email Corrigido):**\n\n"
                        preview += f"**Para:** {email_novo}\n"
                        if dados_email_para_enviar.get('cc'):
                            preview += f"**CC:** {', '.join(dados_email_para_enviar.get('cc', []))}\n"
                        if dados_email_para_enviar.get('bcc'):
                            preview += f"**BCC:** {', '.join(dados_email_para_enviar.get('bcc', []))}\n"
                        preview += f"**Assunto:** {dados_email_para_enviar.get('assunto')}\n\n"
                        preview += f"**Conteúdo:**\n{dados_email_para_enviar.get('conteudo')}\n\n"
                        preview += "💡 Confirme para enviar (digite 'sim' ou 'enviar')"
                        
                        return ProcessingResult(
                            resposta=preview,
                            sucesso=True,
                            tool_calls=[{'name': 'enviar_email_personalizado', 'arguments': dados_email_para_enviar}],
                            aguardando_confirmacao=True,
                            ultima_resposta_aguardando_email=dados_email_para_enviar,  # Atualizar com email corrigido
                            ultima_resposta_aguardando_duimp=ultima_resposta_aguardando_duimp,
                            comando_interface=None,
                            acao='email_preview',
                            erro=None,
                            _resultado_interno={'ultima_resposta_aguardando_email': dados_email_para_enviar},
                            eh_pedido_melhorar_email=False
                        )
        
        # ✅ FASE 3: Precheck (detecção proativa)
        # Só executar precheck se não há email pendente (exceto se for correção)
        # Isso evita que precheck pegue contexto errado quando usuário está apenas corrigindo email
        if (not dados_email_para_enviar or eh_correcao_email_destinatario) and self.precheck_service:
            try:
                resposta_precheck = self.precheck_service.tentar_responder_sem_ia(
                    mensagem=mensagem,
                    historico=historico,
                    session_id=session_id,
                    nome_usuario=nome_usuario,
                )
                
                if resposta_precheck:
                    # Se precheck retornou tool_calls, marcar para executar depois
                    if resposta_precheck.get('tool_calls'):
                        tool_calls = resposta_precheck.get('tool_calls')
                        logger.info(f'[CORE] Precheck retornou tool_calls: {len(tool_calls)} tool(s)')
                        # TODO: Executar tool calls via ToolExecutionService na Fase 3.5
                        # Por enquanto, retornar tool_calls no resultado para o chat_service processar
                    
                    # Se precheck indica que deve chamar IA para refinar, continuar processamento
                    deve_chamar_ia_para_refinar = resposta_precheck.get('_deve_chamar_ia_para_refinar', False)
                    
                    if not deve_chamar_ia_para_refinar and resposta_precheck.get('resposta'):
                        # Precheck retornou resposta final - retornar diretamente
                        logger.info(f'[CORE] Resposta final do precheck (sem refinamento pela IA)')
                        return ProcessingResult(
                            resposta=resposta_precheck.get('resposta', ''),
                            sucesso=resposta_precheck.get('sucesso', True),
                            tool_calls=resposta_precheck.get('tool_calls'),
                            aguardando_confirmacao=resposta_precheck.get('aguardando_confirmacao', False),
                            ultima_resposta_aguardando_email=resposta_precheck.get('ultima_resposta_aguardando_email') or ultima_resposta_aguardando_email,
                            ultima_resposta_aguardando_duimp=resposta_precheck.get('ultima_resposta_aguardando_duimp') or ultima_resposta_aguardando_duimp,
                            comando_interface=None,
                            acao=resposta_precheck.get('acao'),
                            erro=resposta_precheck.get('erro'),
                            _resultado_interno={'precheck': True, 'resposta_base': resposta_precheck.get('resposta_base')},
                            eh_pedido_melhorar_email=eh_pedido_melhorar_email
                        )
            except Exception as e:
                logger.error(f'❌ [CORE] Erro no precheck: {e}', exc_info=True)
                # Continuar processamento normal se precheck falhar
        
        # ✅ FASE 3.5: Construção de prompt e chamada da IA
        # Construção de prompt agora é feita no método construir_prompt_completo()
        # Processamento de tool calls será feito no método processar_tool_calls()
        
        # Por enquanto, retornar estrutura básica com flag
        # O chat_service vai chamar construir_prompt_completo() e depois processar_tool_calls()
        
        return ProcessingResult(
            resposta="",
            sucesso=True,
            tool_calls=None,
            aguardando_confirmacao=False,
            ultima_resposta_aguardando_email=dados_email_para_enviar if dados_email_para_enviar else ultima_resposta_aguardando_email,
            ultima_resposta_aguardando_duimp=ultima_resposta_aguardando_duimp,
            comando_interface=None,
            acao=None,
            erro=None,
            _resultado_interno={
                'precisa_ia': True,  # Flag indicando que precisa processar pela IA
                'eh_correcao_email_destinatario': eh_correcao_email_destinatario,  # Flag para correção detectada
                'eh_pedido_melhorar_email': eh_pedido_melhorar_email  # Flag para melhorar email
            },
            eh_pedido_melhorar_email=eh_pedido_melhorar_email
        )
    
    def construir_prompt_completo(
        self,
        mensagem: str,
        historico: List[Dict],
        session_id: Optional[str],
        nome_usuario: Optional[str],
        processo_ref: Optional[str] = None,
        categoria_atual: Optional[str] = None,
        categoria_contexto: Optional[str] = None,
        numero_ce_contexto: Optional[str] = None,
        numero_cct: Optional[str] = None,
        contexto_processo: Optional[Dict] = None,
        acao_info: Optional[Dict] = None,
        resposta_base_precheck: Optional[str] = None,
        eh_pedido_melhorar_email: bool = False,
        email_para_melhorar_contexto: Optional[Dict] = None,
        eh_pergunta_generica: bool = False,
        eh_pergunta_pendencias: bool = False,
        eh_pergunta_situacao: bool = False,
        precisa_contexto: bool = False,
        eh_fechamento_dia: bool = False,
        # Helpers do chat_service (via callbacks)
        extrair_processo_referencia_fn: Optional[Callable] = None,
        # Prompt builder já está no __init__
    ) -> Dict[str, Any]:
        """
        ✅ PASSO 3.5 - FASE 3.5.1: Constrói prompt completo para a IA.
        
        Este método extrai toda a lógica de construção de prompt do chat_service.py,
        centralizando em um único lugar e facilitando manutenção e testes.
        
        Args:
            mensagem: Mensagem do usuário
            historico: Histórico de mensagens
            session_id: ID da sessão
            nome_usuario: Nome do usuário
            processo_ref: Processo de referência extraído
            categoria_atual: Categoria extraída da mensagem atual
            categoria_contexto: Categoria do contexto/histórico
            numero_ce_contexto: Número do CE do contexto
            numero_cct: Número do CCT mencionado
            contexto_processo: Contexto completo do processo (se encontrado)
            acao_info: Informações de ação detectada
            resposta_base_precheck: Resposta base do precheck (para refinar)
            eh_pedido_melhorar_email: Se é pedido para melhorar email
            email_para_melhorar_contexto: Contexto do email para melhorar
            eh_pergunta_generica: Se é pergunta genérica
            eh_pergunta_pendencias: Se é pergunta sobre pendências
            eh_pergunta_situacao: Se é pergunta sobre situação
            precisa_contexto: Se precisa de contexto
            eh_fechamento_dia: Se é comando de fechamento do dia
            extrair_processo_referencia_fn: Função helper para extrair processo
        
        Returns:
            Dict com:
            - 'system_prompt': str
            - 'user_prompt': str
            - 'usar_tool_calling': bool (False no modo legislação estrita)
        """
        import json
        import re
        from typing import Callable, List, Dict, Any, Optional
        from services.learned_rules_service import buscar_regras_aprendidas, formatar_regras_para_prompt
        
        # Inicializar variáveis
        acao_info = acao_info or {}
        historico = historico or []
        
        # ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 1: Construir saudação personalizada e regras aprendidas
        # ✅ NOVO: Adicionar saudação personalizada se tiver nome do usuário
        saudacao_personalizada = ""
        if nome_usuario:
            nome = nome_usuario
            saudacao_personalizada = f"""

👤 **INFORMAÇÃO CRÍTICA DO USUÁRIO:**
- O nome do usuário é **{nome}**
- ⚠️⚠️⚠️ OBRIGATÓRIO: SEMPRE use o nome do usuário nas respostas
- Use o nome de forma natural e cordial, como um colega de trabalho
- Exemplos OBRIGATÓRIOS de uso do nome:
  * Início de resposta: "Olá, {nome}!" ou "Oi, {nome}!"
  * Durante a resposta: "Entendi, {nome}!", "Perfeito, {nome}!", "Claro, {nome}!"
  * Final de resposta: "Precisa de mais alguma coisa, {nome}?", "Estou aqui para ajudar, {nome}!"
- ⚠️ NÃO esqueça de usar o nome - é muito importante para criar uma experiência personalizada
- Seja amigável, profissional e use o nome frequentemente (pelo menos 1-2 vezes por resposta)
"""
        
        # ✅ NOVO: Buscar regras aprendidas para incluir no system_prompt
        regras_aprendidas_texto = ""
        try:
            regras = buscar_regras_aprendidas(ativas=True)
            if regras:
                regras_aprendidas_texto = formatar_regras_para_prompt(regras)
                logger.debug(f"✅ {len(regras)} regras aprendidas incluídas no prompt")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar regras aprendidas: {e}")
        
        # Construir system_prompt via PromptBuilder (conteúdo equivalente ao original)
        if not self.prompt_builder:
            logger.error("❌ PromptBuilder não está inicializado no MessageProcessingService")
            return {
                'system_prompt': '',
                'user_prompt': '',
                'usar_tool_calling': True,
                '_precisa_chat_service': True  # Flag temporária para indicar que precisa do chat_service
            }
        
        system_prompt = self.prompt_builder.build_system_prompt(
            saudacao_personalizada,
            regras_aprendidas=regras_aprendidas_texto
        )
        
        # ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 3: Construir contexto_str (processo, categoria, CE/CCT)
        contexto_str = self._construir_contexto_str(
            processo_ref=processo_ref,
            contexto_processo=contexto_processo,
            categoria_atual=categoria_atual,
            categoria_contexto=categoria_contexto,
            numero_ce_contexto=numero_ce_contexto,
            numero_cct=numero_cct,
            mensagem=mensagem,
            eh_pergunta_generica=eh_pergunta_generica,
            eh_pergunta_pendencias=eh_pergunta_pendencias,
            eh_pergunta_situacao=eh_pergunta_situacao,
            eh_fechamento_dia=eh_fechamento_dia,
            acao_info=acao_info
        )
        
        # ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 4: Construir historico_str e instrucao_processo
        historico_str, instrucao_processo = self._construir_historico_str(
            historico=historico,
            mensagem=mensagem,
            processo_ref=processo_ref,
            extrair_processo_referencia_fn=extrair_processo_referencia_fn
        )
        
        # Adicionar instrucao_processo ao contexto_str se houver
        if instrucao_processo:
            contexto_str += instrucao_processo
        
        # ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 5: Buscar contexto_sessao
        contexto_sessao_texto = self._buscar_contexto_sessao(
            session_id=session_id,
            mensagem=mensagem,
            processo_ref=processo_ref,
            extrair_processo_referencia_fn=extrair_processo_referencia_fn,
            eh_fechamento_dia=eh_fechamento_dia
        )
        
        # ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 6: Construir user_prompt e modo legislação estrita
        user_prompt, usar_tool_calling_final, system_prompt_final = self._construir_user_prompt(
            mensagem=mensagem,
            contexto_str=contexto_str,
            historico_str=historico_str,
            contexto_sessao_texto=contexto_sessao_texto,
            acao_info=acao_info,
            resposta_base_precheck=resposta_base_precheck,
            eh_pedido_melhorar_email=eh_pedido_melhorar_email,
            email_para_melhorar_contexto=email_para_melhorar_contexto,
            system_prompt=system_prompt,
            session_id=session_id  # ✅ NOVO: Passar session_id para adicionar JSON salvo
        )
        
        # Retornar prompts completos construídos
        return {
            'system_prompt': system_prompt_final,
            'user_prompt': user_prompt,
            'usar_tool_calling': usar_tool_calling_final,
            'contexto_str': contexto_str,  # Manter para compatibilidade
            'historico_str': historico_str,  # Manter para compatibilidade
            'contexto_sessao_texto': contexto_sessao_texto,  # Manter para compatibilidade
        }
    
    def _construir_user_prompt(
        self,
        mensagem: str,
        contexto_str: str,
        historico_str: str,
        contexto_sessao_texto: str,
        acao_info: Optional[Dict] = None,
        resposta_base_precheck: Optional[str] = None,
        eh_pedido_melhorar_email: bool = False,
        email_para_melhorar_contexto: Optional[Dict] = None,
        system_prompt: str = '',
        session_id: Optional[str] = None,  # ✅ NOVO: session_id para buscar JSON salvo
    ) -> tuple[str, bool, str]:
        """
        ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 6: Constrói user_prompt e detecta modo legislação estrita.
        
        Extrai toda a lógica de construção de user_prompt do chat_service.py,
        incluindo prompt adicional para melhorar email, resposta do precheck,
        detecção de modo estrito de legislação, e substituição de prompts.
        
        Args:
            mensagem: Mensagem do usuário
            contexto_str: Contexto estruturado construído
            historico_str: Histórico construído
            contexto_sessao_texto: Contexto de sessão formatado
            acao_info: Informações de ação detectada
            resposta_base_precheck: Resposta base do precheck (para refinar)
            eh_pedido_melhorar_email: Se é pedido para melhorar email
            email_para_melhorar_contexto: Contexto do email para melhorar
            system_prompt: System prompt construído (pode ser substituído no modo estrito)
        
        Returns:
            Tuple com (user_prompt, usar_tool_calling, system_prompt_final)
        """
        import re
        from services.legislacao_strict_mode import (
            LEGISLACAO_STRICT_SYSTEM_PROMPT,
            montar_user_prompt_legislacao,
            detectar_modo_estrito,
            eh_pergunta_conceitual_pura
        )
        
        acao_info = acao_info or {}
        
        # Construir base_user_prompt usando PromptBuilder
        if not self.prompt_builder:
            logger.error("❌ PromptBuilder não está inicializado no MessageProcessingService")
            return ("", True, system_prompt)
        
        base_user_prompt = self.prompt_builder.build_user_prompt(
            mensagem=mensagem,
            contexto_str=contexto_str,
            historico_str=historico_str,
            acao_info=acao_info,
            contexto_sessao=contexto_sessao_texto,
        )
        
        # ✅ NOVO: Adicionar resposta_base_precheck ao prompt se existir (para IA refinar)
        prompt_adicional = ""
        
        # ✅ NOVO: Se usuário pediu para melhorar email em preview, adicionar contexto do email atual
        if eh_pedido_melhorar_email and email_para_melhorar_contexto:
            prompt_adicional += f"\n\n📧 **MELHORAR EMAIL - INSTRUÇÕES CRÍTICAS:** 🚨🚨🚨\n"
            prompt_adicional += f"O usuário pediu para MELHORAR/ELABORAR um email que está em preview.\n"
            prompt_adicional += f"Email atual:\n"
            prompt_adicional += f"**Para:** {', '.join(email_para_melhorar_contexto.get('destinatarios', []))}\n"
            prompt_adicional += f"**Assunto:** {email_para_melhorar_contexto.get('assunto', 'Mensagem')}\n"
            prompt_adicional += f"**Conteúdo:**\n{email_para_melhorar_contexto.get('conteudo', '')}\n\n"
            prompt_adicional += f"🚨🚨🚨 **REGRA ABSOLUTA:** 🚨🚨🚨\n"
            prompt_adicional += f"Você DEVE retornar o email MELHORADO/ELABORADO no formato abaixo.\n"
            prompt_adicional += f"Se o usuário pediu para 'assinar Maria', inclua 'Maria' na assinatura.\n"
            prompt_adicional += f"Se pediu 'mais carinhoso', use tom mais afetuoso.\n"
            prompt_adicional += f"Se pediu 'mais formal', use tom profissional.\n"
            prompt_adicional += f"Retorne EXATAMENTE no formato abaixo:\n\n"
            prompt_adicional += f"📧 **Preview do Email:**\n\n"
            prompt_adicional += f"**Para:** {', '.join(email_para_melhorar_contexto.get('destinatarios', []))}\n"
            prompt_adicional += f"**Assunto:** [assunto MELHORADO - elabore se necessário]\n\n"
            prompt_adicional += f"**Conteúdo:**\n[conteúdo MELHORADO e ELABORADO - seja criativo e bem escrito]\n\n"
            prompt_adicional += f"💡 Confirme para enviar (digite 'sim' ou 'enviar')\n\n"
            prompt_adicional += f"**IMPORTANTE:** NÃO adicione saudações, explicações ou qualquer outro texto fora do formato acima.\n"
            prompt_adicional += f"Retorne APENAS o preview formatado acima.\n\n"
        
        if resposta_base_precheck:
            # ✅ CRÍTICO: Verificar se é preview de email (contém "Preview do Email" ou "📧")
            eh_preview_email = "📧" in resposta_base_precheck or "Preview do Email" in resposta_base_precheck or "preview do email" in resposta_base_precheck.lower()
            
            if eh_preview_email and not eh_pedido_melhorar_email:
                # ✅ CORREÇÃO: Para preview de email, instruir a IA a APENAS refinar o texto do email
                # NÃO responder como pessoa, apenas melhorar o conteúdo do email
                prompt_adicional += f"\n\n📧 **REFINAMENTO DE EMAIL - INSTRUÇÕES CRÍTICAS:** 🚨🚨🚨\n"
                prompt_adicional += f"O sistema preparou um preview de email:\n"
                prompt_adicional += f"{resposta_base_precheck}\n\n"
                prompt_adicional += f"🚨🚨🚨 **REGRA ABSOLUTA - NÃO VIOLAR:** 🚨🚨🚨\n"
                prompt_adicional += f"Você DEVE retornar APENAS o preview refinado, SEM QUALQUER texto adicional antes ou depois.\n"
                prompt_adicional += f"Retorne EXATAMENTE no formato abaixo, apenas refinando o assunto e conteúdo:\n\n"
                prompt_adicional += f"📧 **Preview do Email:**\n\n"
                prompt_adicional += f"**Para:** [email do preview]\n"
                prompt_adicional += f"**Assunto:** [assunto REFINADO - melhore se necessário]\n\n"
                prompt_adicional += f"**Conteúdo:**\n[conteúdo REFINADO - melhore se necessário]\n\n"
                prompt_adicional += f"⚠️⚠️⚠️ **CONFIRME PARA ENVIAR** (digite 'sim' ou 'enviar')\n\n"
                prompt_adicional += f"**IMPORTANTE:** NÃO adicione saudações, explicações ou qualquer outro texto fora do formato acima.\n\n"
            else:
                # Para outros tipos de resposta do precheck, instruir refinamento genérico
                prompt_adicional += f"\n\n📋 **CONTEXTO DO PRECHECK:**\n"
                prompt_adicional += f"O sistema detectou automaticamente sua intenção e preparou uma resposta inicial:\n"
                prompt_adicional += f"{resposta_base_precheck}\n\n"
                prompt_adicional += f"💡 **IMPORTANTE:** Melhore e refine essa resposta. Torne-a mais clara, profissional e completa.\n"
        
        user_prompt_base = (
            base_user_prompt
            + prompt_adicional
            + "\n\nResponda de forma clara e útil. Se o usuário pedir para criar uma DUIMP, "
              "confirme a ação e explique o que será feito.\n"
              "Se não tiver informações suficientes, peça ao usuário para fornecer mais detalhes.\n\n"
              "IMPORTANTE: Use APENAS as informações do processo mencionado na mensagem atual ou no contexto do histórico. "
              "NÃO misture dados de processos diferentes.\n"
              "Se a mensagem não menciona um processo/CE específico mas parece ser uma pergunta sobre um processo/CE, "
              "verifique o histórico ou pergunte ao usuário qual processo/CE ele quer consultar."
        )
        
        # ✅ NOVO: Verificar se deve usar modo legislação estrita
        usar_modo_estrito = False
        trechos_legislacao_estrito = []
        system_prompt_final = system_prompt
        usar_tool_calling_final = True
        
        # ⚠️ IMPORTANTE: Se for pergunta conceitual PURA, NÃO buscar na legislação
        if eh_pergunta_conceitual_pura(mensagem):
            logger.info(f"💡 Pergunta conceitual pura detectada: '{mensagem}' - NÃO buscará na legislação")
            # Deixar a IA responder com conhecimento geral apenas
        elif detectar_modo_estrito(mensagem):
            logger.info(f"🔍 Modo legislação estrita detectado para: '{mensagem}'")
            
            # Buscar trechos relevantes na legislação
            try:
                from services.legislacao_service import LegislacaoService
                legislacao_service = LegislacaoService()
                
                # Extrair termos da mensagem para buscar
                # Extrair termos relevantes (palavras-chave)
                termos_extraidos = []
                
                # Padrões comuns de perguntas legais
                padroes_termos = [
                    r'perdimento',
                    r'multa',
                    r'infra[cç][ãa]o',
                    r'abandono',
                    r'penalidade',
                    r'embargo',
                    r'apreens[ãa]o',
                    r'base\s+legal',
                    r'artigo',
                    r'art\.',
                    r'onde\s+est[áa]\s+previsto',
                    r'dispositivo\s+legal',
                    r'norma\s+que\s+trata',
                ]
                
                for padrao in padroes_termos:
                    matches = re.findall(padrao, mensagem.lower(), re.IGNORECASE)
                    if matches:
                        termos_extraidos.extend(matches)
                
                # Remover duplicatas
                termos_extraidos = list(set(termos_extraidos))
                
                if termos_extraidos:
                    logger.info(f"🔍 Buscando trechos na legislação com termos: {termos_extraidos}")
                    trechos_legislacao_estrito = legislacao_service.buscar_em_todas_legislacoes(
                        termos=termos_extraidos,
                        limit=20,  # Limitar a 20 trechos para não sobrecarregar
                        incluir_revogados=False
                    )
                    
                    if trechos_legislacao_estrito:
                        logger.info(f"✅ {len(trechos_legislacao_estrito)} trechos encontrados para modo estrito")
                        usar_modo_estrito = True
                    else:
                        logger.info(f"⚠️ Nenhum trecho encontrado. Usando modo normal.")
                else:
                    logger.info(f"⚠️ Não foi possível extrair termos. Usando modo normal.")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao buscar trechos para modo estrito: {e}", exc_info=True)
                # Continuar com modo normal se houver erro
        
        # Se deve usar modo estrito, substituir prompts
        if usar_modo_estrito and trechos_legislacao_estrito:
            logger.info(f"📚 Usando modo legislação estrita com {len(trechos_legislacao_estrito)} trechos")
            system_prompt_final = LEGISLACAO_STRICT_SYSTEM_PROMPT
            user_prompt = montar_user_prompt_legislacao(mensagem, trechos_legislacao_estrito)
            # No modo estrito, não usar tool calling (resposta direta baseada nos trechos)
            usar_tool_calling_final = False
        else:
            user_prompt = user_prompt_base
        
        return user_prompt, usar_tool_calling_final, system_prompt_final
    
    def detectar_busca_direta_nesh(
        self,
        mensagem: str,
        executar_funcao_tool_fn: Optional[Callable] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        ✅ PASSO 3.5 - FASE 3.5.2 - SUB-ETAPA 4: Detecta busca direta NESH ANTES de chamar IA.
        
        Se detectar pedido de buscar APENAS na NESH (sem IA), executa diretamente
        e retorna resultado sem chamar a IA.
        
        Args:
            mensagem: Mensagem do usuário
            executar_funcao_tool_fn: Função helper para executar tools
        
        Returns:
            Dict com resultado se for busca direta NESH, None caso contrário
        """
        import re
        
        mensagem_lower = mensagem.lower()
        
        # Detectar pedidos de buscar APENAS na NESH (busca direta, sem IA)
        # Padrões: "buscar na nesh", "consultar nesh", "pesquisar nesh", "buscar nesh", "nesh de [produto]"
        eh_busca_direta_nesh = bool(re.search(
            r'(?:buscar|consultar|pesquisar|procurar|ver|mostrar|mostre).*?(?:na\s+)?nesh',
            mensagem_lower
        )) or bool(re.search(
            r'nesh\s+(?:de|do|da|para|sobre)',
            mensagem_lower
        )) or bool(re.search(
            r'(?:nota\s+explicativa|notas\s+explicativas).*?(?:nesh|sh)',
            mensagem_lower
        ))
        
        if not eh_busca_direta_nesh:
            return None
        
        logger.warning(f'🚨🚨🚨 PRIORIDADE MÁXIMA: Busca DIRETA na NESH detectada. Chamando buscar_nota_explicativa_nesh e retornando diretamente (SEM chamar IA).')
        
        if not executar_funcao_tool_fn:
            logger.error('❌ executar_funcao_tool_fn não fornecida - não é possível executar busca direta NESH')
            return None
        
        try:
            # Extrair NCM se mencionado (formato: 0703, 0703.20, 070320, etc.)
            ncm_extraido = None
            match_ncm = re.search(r'(\d{2}\.?\d{2}(?:\.?\d{2})?(?:\.?\d{2})?)', mensagem)
            if match_ncm:
                ncm_extraido = match_ncm.group(1).replace('.', '').strip()
                # Normalizar para 4, 6 ou 8 dígitos
                if len(ncm_extraido) > 8:
                    ncm_extraido = ncm_extraido[:8]
            
            # Extrair descrição do produto (tudo após "nesh de", "nesh para", etc.)
            descricao_extraida = None
            match_desc = re.search(
                r'nesh\s+(?:de|do|da|para|sobre)\s+(.+)',
                mensagem_lower
            ) or re.search(
                r'(?:buscar|consultar|pesquisar|procurar|ver|mostrar|mostre).*?nesh.*?(?:de|do|da|para|sobre)\s+(.+)',
                mensagem_lower
            )
            if match_desc:
                descricao_extraida = match_desc.group(1).strip()
                # Remover pontuação final se houver
                descricao_extraida = re.sub(r'[.,;:!?]+$', '', descricao_extraida).strip()
            
            # Se não encontrou descrição explícita, tentar extrair produto da mensagem
            if not descricao_extraida:
                # Padrão: "nesh [produto]" ou "buscar nesh [produto]"
                match_produto = re.search(
                    r'(?:nesh|buscar\s+nesh|consultar\s+nesh)\s+([a-záàâãéêíóôõúç\s]+?)(?:\s+qual|\s+para|\s+do|\s+da|\?|$)',
                    mensagem_lower
                )
                if match_produto:
                    descricao_extraida = match_produto.group(1).strip()
            
            resultado_nesh_direto = executar_funcao_tool_fn(
                nome_funcao='buscar_nota_explicativa_nesh',
                argumentos={
                    'ncm': ncm_extraido if ncm_extraido else None,
                    'descricao_produto': descricao_extraida if descricao_extraida else None,
                    'limite': 5  # Limite maior para busca direta
                },
                mensagem_original=mensagem
            )
            
            if resultado_nesh_direto and isinstance(resultado_nesh_direto, dict) and resultado_nesh_direto.get('resposta'):
                logger.info(f'✅✅✅ Resposta forçada ANTES da IA (BUSCA DIRETA NESH) - tamanho: {len(resultado_nesh_direto.get("resposta"))}')
                return {
                    'sucesso': True,
                    'resposta': resultado_nesh_direto.get('resposta'),
                    'tool_calling': {
                        'name': 'buscar_nota_explicativa_nesh',
                        'arguments': {
                            'ncm': ncm_extraido,
                            'descricao_produto': descricao_extraida,
                            'limite': 5
                        }
                    },
                    '_processado_precheck': True,
                    '_busca_direta_nesh': True
                }
            else:
                logger.warning(f'❌ Resposta vazia ou inválida da tool buscar_nota_explicativa_nesh para "{mensagem}". Prosseguindo com a IA.')
                return None
        except Exception as e:
            logger.error(f'❌ Erro ao executar busca direta NESH: {e}', exc_info=True)
            return None
    
    def chamar_ia_com_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        usar_tool_calling: bool,
        mensagem: Optional[str] = None,
        ultima_resposta_texto: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Any:
        """
        ✅ PASSO 3.5 - FASE 3.5.2 - SUB-ETAPA 2: Chama IA com tools preparadas.
        
        Prepara tools e chama a IA com tool calling habilitado.
        
        Args:
            system_prompt: System prompt para a IA
            user_prompt: User prompt para a IA
            usar_tool_calling: Se deve usar tool calling
            model: Modelo de IA a usar
            temperature: Temperatura para geração
        
        Returns:
            Resposta raw da IA (pode ter tool_calls)
        """
        if not self.ai_service:
            logger.error("❌ AI service não está inicializado no MessageProcessingService")
            return None
        
        if not usar_tool_calling:
            # Chamar IA sem tools
            return self.ai_service._call_llm_api(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                tools=None,
                model=model,
                temperature=temperature
            )
        
        # ✅ Heurística leve (28/01/2026): preferir "vendas por NF" quando o usuário pedir "vendas ..."
        # e não estiver pedindo apenas o total ("quanto vendeu").
        # Motivo: evita casos como "vendas vdm em janeiro" cair no relatório agregado (sem listar NFs).
        tool_choice_override = None
        try:
            if mensagem:
                import re

                m = mensagem.strip().lower()
                pediu_total = bool(re.search(r"\bquanto\b|\btotal\b", m))
                pediu_nf = bool(re.search(r"\bpor\s+nf\b|\bnf\b|\bnota\s+fiscal\b", m))
                pediu_lista = bool(re.search(r"\blist(a|e|ar)\b|\bmostr(a|e)\b|\bvendas?\b", m))

                if (pediu_nf or (pediu_lista and not pediu_total)) and "consultar_vendas_nf_make":
                    tool_choice_override = {"type": "function", "function": {"name": "consultar_vendas_nf_make"}}
        except Exception as _e:
            tool_choice_override = None

        # ✅ FASE 2D (14/01/2026): Tool allowlist por intenção (Layer A)
        # Para intenções sensíveis (email/relatório/extrato/DUIMP), expor ao modelo apenas as tools da whitelist.
        # Isso reduz drasticamente risco de tool errada (ex: criar_duimp ao pedir email).
        whitelist_tools = None
        try:
            if mensagem:
                from services.intent_detection_service import IntentDetectionService, IntentType
                intent_service = IntentDetectionService()
                intent_detectado = intent_service.detectar_intencao(
                    mensagem=mensagem,
                    historico=None,
                    ultima_resposta_texto=ultima_resposta_texto
                )
                intent_type = intent_detectado.get('intent_type') if intent_detectado else None
                confidence = float(intent_detectado.get('confidence', 0.0)) if intent_detectado else 0.0
                if intent_type and intent_type != IntentType.OUTROS and confidence >= 0.80:
                    whitelist_tools = intent_service.obter_whitelist_tools(intent_type)
                    logger.info(f"🔒 [CORE][TOOL_ALLOWLIST] intent={intent_type.value} conf={confidence:.2f} whitelist={whitelist_tools}")
        except Exception as e:
            logger.warning(f"⚠️ [CORE][TOOL_ALLOWLIST] Erro ao detectar intenção/whitelist: {e}")

        # Garantir que a tool escolhida esteja na whitelist (se houver).
        if tool_choice_override and whitelist_tools is not None:
            try:
                chosen = tool_choice_override.get("function", {}).get("name")
                if chosen and chosen not in whitelist_tools:
                    whitelist_tools = list(whitelist_tools) + [chosen]
            except Exception:
                pass

        # Preparar tools (versão compacta para reduzir tokens)
        try:
            from services.tool_definitions import get_available_tools
            tools = get_available_tools(compact=True, whitelist=whitelist_tools)
            tools_expostas_count = len(tools) if tools else 0
            logger.info(f'🔍 Tool calling ativado - {tools_expostas_count} ferramentas disponíveis (compact)')
        except Exception as e:
            logger.error(f'❌ Erro ao obter tools: {e}', exc_info=True)
            tools = None
            tools_expostas_count = 0
        
        # Chamar IA com tools
        resposta_ia_raw = self.ai_service._call_llm_api(
            prompt=user_prompt,  # ✅ CORREÇÃO: usar 'prompt' ao invés de 'user_prompt'
            system_prompt=system_prompt,
            tools=tools,
            tool_choice=tool_choice_override,
            model=model,
            temperature=temperature
        )
        
        logger.debug(f'🔍 Resposta da IA (tipo: {type(resposta_ia_raw).__name__}): {str(resposta_ia_raw)[:200] if resposta_ia_raw else "None"}')
        
        return resposta_ia_raw
    
    def processar_tool_calls(
        self,
        resposta_ia_raw: Any,
        mensagem: str,
        usar_tool_calling: bool,
        session_id: Optional[str] = None,
        executar_funcao_tool_fn: Optional[Callable] = None,
        response_formatter: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        ✅ PASSO 3.5 - FASE 3.5.2: Processa tool calls retornados pela IA.
        
        Extrai toda a lógica de processamento de tool calls do chat_service.py,
        incluindo execução de tools, combinação de resultados, e tratamento de casos especiais.
        
        Args:
            resposta_ia_raw: Resposta raw da IA (pode ter tool_calls)
            mensagem: Mensagem original do usuário
            usar_tool_calling: Se deve processar tool calls
            session_id: ID da sessão
            executar_funcao_tool_fn: Função helper para executar tools (do chat_service)
            response_formatter: Instância de ResponseFormatter para combinar resultados
        
        Returns:
            Dict com:
            - 'resposta_final': str
            - 'tool_calls_executados': List[Dict]
            - 'ultima_resposta_aguardando_email': Optional[Dict]
            - 'ultima_resposta_aguardando_duimp': Optional[Dict]
            - 'sucesso': bool
        """
        import json
        
        # Se não deve usar tool calling, retornar resposta direta da IA
        if not usar_tool_calling:
            resposta_ia_texto = ''
            if isinstance(resposta_ia_raw, dict):
                resposta_ia_texto = resposta_ia_raw.get('content', '')
            elif isinstance(resposta_ia_raw, str):
                resposta_ia_texto = resposta_ia_raw
            
            # Limpar frases problemáticas se houver formatter
            if response_formatter and hasattr(response_formatter, 'limpar_frases_callback'):
                resposta_ia_texto = response_formatter.limpar_frases_callback(resposta_ia_texto) if response_formatter.limpar_frases_callback else resposta_ia_texto
            
            return {
                'resposta_final': resposta_ia_texto,
                'tool_calls_executados': [],
                'ultima_resposta_aguardando_email': None,
                'ultima_resposta_aguardando_duimp': None,
                'sucesso': True
            }
        
        # Verificar se há tool calls na resposta
        if not isinstance(resposta_ia_raw, dict) or 'tool_calls' not in resposta_ia_raw:
            # Não há tool calls, retornar resposta direta da IA
            resposta_ia_texto = resposta_ia_raw.get('content', '') if isinstance(resposta_ia_raw, dict) else str(resposta_ia_raw)
            
            # Limpar frases problemáticas se houver formatter
            if response_formatter and hasattr(response_formatter, 'limpar_frases_callback'):
                resposta_ia_texto = response_formatter.limpar_frases_callback(resposta_ia_texto) if response_formatter.limpar_frases_callback else resposta_ia_texto
            
            return {
                'resposta_final': resposta_ia_texto,
                'tool_calls_executados': [],
                'ultima_resposta_aguardando_email': None,
                'ultima_resposta_aguardando_duimp': None,
                'sucesso': True
            }
        
        # Há tool calls - processar
        tool_calls = resposta_ia_raw.get('tool_calls', [])
        resposta_ia_texto = resposta_ia_raw.get('content', '')
        
        logger.info(f'✅ Tool calls detectados: {len(tool_calls)} chamada(s)')
        
        # ✅ CASOS ESPECIAIS: Aplicar correções automáticas antes de executar
        tool_calls = self._aplicar_correcoes_tool_calls(tool_calls, mensagem)
        
        # Executar cada tool call
        resultados_tools = []
        ultima_resposta_aguardando_email = None
        ultima_resposta_aguardando_duimp = None
        
        # ✅ NOVO (14/01/2026): Gate de mismatch - validar tool escolhida vs intenção
        # (intent_detectado deve ser passado como parâmetro ou armazenado no contexto)
        # Por enquanto, vamos detectar novamente aqui se necessário
        
        for tool_call in tool_calls:
            func_name = tool_call.get('function', {}).get('name', '')
            func_args_str = tool_call.get('function', {}).get('arguments', '{}')
            
            # ✅ GATE DE MISMATCH: Validar tool escolhida vs intenção detectada
            tool_escolhida_pelo_modelo = func_name
            tool_final_pos_gate = func_name
            
            # Detectar intenção novamente se necessário (ou usar do contexto)
            try:
                from services.intent_detection_service import IntentDetectionService, IntentType
                intent_service = IntentDetectionService()
                intent_detectado = intent_service.detectar_intencao(
                    mensagem=mensagem,
                    historico=None,  # Não temos histórico aqui, mas mensagem deve ser suficiente
                    ultima_resposta_texto=None  # Não temos última resposta aqui
                )
                
                if intent_detectado and intent_detectado.get('intent_type'):
                    validacao = intent_service.validar_tool_vs_intencao(
                        tool_escolhida=func_name,
                        intent_type=intent_detectado['intent_type']
                    )
                    
                    if not validacao['valido']:
                        logger.warning(f'🚨🚨🚨 [GATE_MISMATCH] {validacao["motivo"]}')
                        
                        if validacao['deve_forcar'] and validacao['tool_correta']:
                            # ✅ FORÇAR tool correta
                            tool_final_pos_gate = validacao['tool_correta']
                            logger.info(f'✅✅✅ [GATE_MISMATCH] Forçando tool correta: {tool_final_pos_gate} (era: {func_name})')
                            
                            # ✅ Substituir tool_call pela tool correta
                            tool_call['function']['name'] = tool_final_pos_gate
                            func_name = tool_final_pos_gate  # Atualizar para usar na execução
                            
                            # ✅ Se intenção é "enviar relatório", forçar argumentos corretos
                            if intent_detectado['intent_type'] == IntentType.ENVIAR_RELATORIO_EMAIL:
                                # Buscar last_visible_report_id_processos
                                try:
                                    from services.report_service import obter_last_visible_report_id, _detectar_dominio_por_mensagem
                                    dominio = _detectar_dominio_por_mensagem(mensagem)
                                    last_visible = obter_last_visible_report_id(session_id, dominio=dominio)
                                    if last_visible and last_visible.get('id'):
                                        # Forçar report_id no tool_call
                                        func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
                                        func_args['report_id'] = last_visible['id']
                                        func_args_str = json.dumps(func_args)
                                        tool_call['function']['arguments'] = func_args_str
                                        logger.info(f'✅✅✅ [GATE_MISMATCH] Forçado report_id={last_visible["id"]} (domínio: {dominio})')
                                except Exception as e:
                                    logger.warning(f'⚠️ Erro ao forçar report_id: {e}')
            except Exception as e:
                logger.warning(f'⚠️ Erro no gate de mismatch: {e}', exc_info=True)
                # Continuar com tool original se houver erro
            
            if not func_name:
                logger.warning(f'⚠️ Tool call sem nome de função: {tool_call}')
                continue
            
            try:
                func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
            except json.JSONDecodeError as e:
                logger.warning(f'⚠️ Erro ao parsear argumentos da função {func_name}: {func_args_str} - {e}')
                continue
            
            # ✅ CASO ESPECIAL 1: Se for criar_duimp, SEMPRE forçar confirmar=False na primeira chamada
            # Isso garante que o resumo seja mostrado primeiro, nunca criando direto
            if func_name == 'criar_duimp':
                if 'confirmar' in func_args:
                    logger.warning(f'⚠️ IA tentou passar confirmar={func_args.get("confirmar")} para criar_duimp. Forçando confirmar=False para mostrar resumo primeiro.')
                func_args['confirmar'] = False
            
            # Executar tool via função helper
            if not executar_funcao_tool_fn:
                logger.error(f'❌ executar_funcao_tool_fn não fornecida - não é possível executar {func_name}')
                continue
            
            try:
                resultado_raw = executar_funcao_tool_fn(
                    nome_funcao=func_name,
                    argumentos=func_args,
                    mensagem_original=mensagem,
                    session_id=session_id
                )

                # ✅ CRÍTICO (14/01/2026): Normalizar resultado para garantir contrato sempre-dict (nunca None)
                from services.tool_result import normalize_tool_result
                resultado_tool = normalize_tool_result(func_name, resultado_raw)

                # ✅✅✅ CRÍTICO: NUNCA adicionar fallback dict em resultados_tools (sinal interno)
                if isinstance(resultado_tool, dict):
                    use_fallback = resultado_tool.get("use_fallback") is True
                    error_fallback = resultado_tool.get("error") == "FALLBACK_REQUIRED"
                    if use_fallback or error_fallback:
                        logger.warning(f'⚠️ [CORE] Tentativa de adicionar fallback dict em resultados_tools para {func_name} - ignorando')
                        continue

                resultados_tools.append(resultado_tool)

                # Verificar se tool retornou estado de email ou DUIMP pendente
                resultado_interno = resultado_tool.get('_resultado_interno', {}) if isinstance(resultado_tool, dict) else {}
                if resultado_interno:
                    if 'ultima_resposta_aguardando_email' in resultado_interno:
                        ultima_resposta_aguardando_email = resultado_interno['ultima_resposta_aguardando_email']
                    if 'ultima_resposta_aguardando_duimp' in resultado_interno:
                        ultima_resposta_aguardando_duimp = resultado_interno['ultima_resposta_aguardando_duimp']

                # Também verificar diretamente no resultado
                if isinstance(resultado_tool, dict):
                    if 'ultima_resposta_aguardando_email' in resultado_tool:
                        ultima_resposta_aguardando_email = resultado_tool['ultima_resposta_aguardando_email']
                    if 'ultima_resposta_aguardando_duimp' in resultado_tool:
                        ultima_resposta_aguardando_duimp = resultado_tool['ultima_resposta_aguardando_duimp']
                        
            except Exception as e:
                logger.error(f'❌ Erro ao executar tool {func_name}: {e}', exc_info=True)
                resultados_tools.append({
                    'sucesso': False,
                    'erro': str(e),
                    'resposta': f'❌ Erro ao executar {func_name}: {str(e)}'
                })
        
        # Combinar resultados usando ResponseFormatter
        formatter = response_formatter or self.response_formatter
        if formatter:
            resposta_final = formatter.combinar_resultados_tools(
                resultados_tools=resultados_tools,
                resposta_ia_texto=resposta_ia_texto
            )
        else:
            # Fallback simples se não houver formatter
            if resultados_tools:
                resposta_final = resultados_tools[0].get('resposta', '')
            else:
                resposta_final = resposta_ia_texto
        
        return {
            'resposta_final': resposta_final,
            'tool_calls_executados': tool_calls,
            'ultima_resposta_aguardando_email': ultima_resposta_aguardando_email,
            'ultima_resposta_aguardando_duimp': ultima_resposta_aguardando_duimp,
            'sucesso': True
        }
    
    def _aplicar_correcoes_tool_calls(
        self,
        tool_calls: List[Dict],
        mensagem: str
    ) -> List[Dict]:
        """
        ✅ PASSO 3.5 - FASE 3.5.2 - SUB-ETAPA 4: Aplica correções automáticas em tool calls.
        
        Corrige chamadas incorretas da IA antes de executar, incluindo:
        - Correção de listar_processos_por_situacao com situacao='registrado'
        - Detecção de perguntas sobre NCM de produtos
        - Outras correções automáticas
        
        Args:
            tool_calls: Lista de tool calls retornados pela IA
            mensagem: Mensagem original do usuário
        
        Returns:
            Lista de tool calls corrigidos
        """
        import json
        import re
        
        tool_calls_corrigidos = []
        
        for tool_call in tool_calls:
            func_name = tool_call.get('function', {}).get('name', '')
            func_args_str = tool_call.get('function', {}).get('arguments', '{}')
            
            try:
                func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
            except json.JSONDecodeError:
                func_args = {}
            
            # ✅ CORREÇÃO 1: Verificar se IA chamou listar_processos_por_situacao com situacao='registrado'
            # Isso geralmente indica que a IA deveria ter chamado criar_duimp ou obter_dashboard_hoje
            if func_name == 'listar_processos_por_situacao':
                situacao_arg = func_args.get('situacao', '').lower()
                if 'registrado' in situacao_arg:
                    logger.warning(f'⚠️ IA chamou listar_processos_por_situacao com situacao="registrado". Isso geralmente indica que deveria chamar obter_dashboard_hoje ou criar_duimp.')
                    # Não corrigir automaticamente - deixar executar e ver o resultado
                    # A correção será feita após ver o resultado
            
            # ✅ CORREÇÃO 2: Detectar perguntas sobre NCM de produtos
            # Se a IA chamou buscar_ncms_por_descricao mas deveria ter chamado sugerir_ncm_com_ia
            mensagem_lower = mensagem.lower()
            eh_pergunta_ncm_produto = bool(re.search(
                r'(?:qual|quais)\s+(?:o|os|a|as)?\s*ncm\s+(?:do|da|de|para|d[eo]?\s+produto?|de\s+)?|ncm\s+(?:do|da|de|para)|^ncm\s+[a-z0-9]|^qual\s+(?:a|o)\s+ncm',
                mensagem_lower
            ))
            
            if eh_pergunta_ncm_produto and func_name == 'buscar_ncms_por_descricao':
                # Extrair produto da mensagem
                produto_match = re.search(
                    r'(?:ncm\s+(?:do|da|de|para)\s+)?([a-z0-9\s]+?)(?:\s+qual|\s+para|\s+do|\s+da|\?|$)',
                    mensagem_lower
                )
                produto_detectado = produto_match.group(1).strip() if produto_match else None
                
                if produto_detectado and len(produto_detectado) > 2:
                    logger.warning(f'🔍 Pergunta sobre NCM de produto "{produto_detectado}" detectada. Substituindo buscar_ncms_por_descricao por sugerir_ncm_com_ia.')
                    # Substituir tool call
                    tool_call_corrigido = {
                        'function': {
                            'name': 'sugerir_ncm_com_ia',
                            'arguments': json.dumps({
                                'descricao': produto_detectado,
                                'usar_cache': True,
                                'validar_sugestao': True
                            })
                        }
                    }
                    tool_calls_corrigidos.append(tool_call_corrigido)
                    continue
            
            # Adicionar tool call original (sem correção)
            tool_calls_corrigidos.append(tool_call)
        
        return tool_calls_corrigidos
    
    def _construir_contexto_str(
        self,
        processo_ref: Optional[str] = None,
        contexto_processo: Optional[Dict] = None,
        categoria_atual: Optional[str] = None,
        categoria_contexto: Optional[str] = None,
        numero_ce_contexto: Optional[str] = None,
        numero_cct: Optional[str] = None,
        mensagem: str = '',
        eh_pergunta_generica: bool = False,
        eh_pergunta_pendencias: bool = False,
        eh_pergunta_situacao: bool = False,
        eh_fechamento_dia: bool = False,
        acao_info: Optional[Dict] = None,
    ) -> str:
        """
        ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 3: Constrói contexto_str (processo, categoria, CE/CCT).
        
        Extrai toda a lógica de construção de contexto do chat_service.py,
        incluindo contexto de processo, categoria, CE, CCT e avisos sobre perguntas genéricas.
        
        Args:
            processo_ref: Processo de referência extraído
            contexto_processo: Contexto completo do processo (se encontrado)
            categoria_atual: Categoria extraída da mensagem atual
            categoria_contexto: Categoria do contexto/histórico
            numero_ce_contexto: Número do CE do contexto
            numero_cct: Número do CCT mencionado
            mensagem: Mensagem do usuário (para detectar perguntas temporais)
            eh_pergunta_generica: Se é pergunta genérica
            eh_pergunta_pendencias: Se é pergunta sobre pendências
            eh_pergunta_situacao: Se é pergunta sobre situação
            eh_fechamento_dia: Se é comando de fechamento do dia
            acao_info: Informações de ação detectada
        
        Returns:
            String com contexto formatado para o prompt
        """
        import json
        import re
        
        contexto_str = ''
        acao_info = acao_info or {}
        
        # ✅ CORREÇÃO: Não incluir contexto de processo se é pergunta genérica sobre pendências/situação com categoria no histórico
        # Isso evita usar processo antigo (ex: VDM.0003/25) quando a pergunta é sobre categoria (ex: ALH)
        incluir_contexto_processo = (
            processo_ref and
            not (eh_pergunta_generica and (eh_pergunta_pendencias or eh_pergunta_situacao) and categoria_contexto)
        )
        
        if incluir_contexto_processo:
            if contexto_processo and contexto_processo.get('encontrado'):
                contexto_str = f"\n\n📋 ⚠️ CONTEXTO EXCLUSIVO DO PROCESSO {processo_ref} (USE APENAS ESTES DADOS):\n"
                contexto_str += json.dumps(contexto_processo, ensure_ascii=False, indent=2)
                contexto_str += f"\n\n⚠️ LEMBRE-SE: Use APENAS os dados acima para o processo {processo_ref}. Ignore qualquer informação de outros processos."
            elif processo_ref:
                contexto_str = f"\n\n⚠️ Processo {processo_ref} não encontrado no sistema."
        elif eh_pergunta_generica and (eh_pergunta_pendencias or eh_pergunta_situacao) and categoria_contexto:
            # ✅ CORREÇÃO: Pergunta genérica sobre pendências/situação com categoria no histórico
            # Não incluir contexto de processo - usar apenas categoria
            contexto_str = f"\n\n⚠️ PERGUNTA GENÉRICA SOBRE PENDÊNCIAS/SITUAÇÃO COM CATEGORIA NO HISTÓRICO:\n"
            contexto_str += f"⚠️ IGNORE qualquer contexto de processo anterior (ex: VDM.0003/25).\n"
            contexto_str += f"⚠️ Use APENAS a categoria {categoria_contexto} do histórico para filtrar os resultados.\n"
        
        # ✅ NOVO: Adicionar contexto do CE se houver
        if numero_ce_contexto and not processo_ref:
            contexto_str += f"\n\n📋 ⚠️ CONTEXTO DO CE {numero_ce_contexto} (extraído do histórico da conversa):\n"
            contexto_str += f"O usuário está fazendo perguntas sobre o CE {numero_ce_contexto} que foi consultado anteriormente.\n"
            contexto_str += f"⚠️ IMPORTANTE: Use a função consultar_ce_maritimo com numero_ce='{numero_ce_contexto}' para obter os dados atualizados do CE antes de responder.\n"
            contexto_str += f"NÃO responda com informações genéricas - SEMPRE consulte o CE primeiro usando a função consultar_ce_maritimo."
        
        # ✅ CRÍTICO: Adicionar contexto de CCT se detectado na mensagem (deve limpar contexto do processo)
        if numero_cct:
            contexto_str += f"\n\n✈️ ⚠️ CONTEXTO DE CCT: {numero_cct}\n"
            contexto_str += f"O usuário está perguntando sobre o CCT {numero_cct} especificamente.\n"
            contexto_str += f"⚠️ CRÍTICO: Use a função consultar_cct com numero_cct='{numero_cct}' para consultar este CCT.\n"
            contexto_str += f"⚠️ IGNORE qualquer contexto de processo anterior (como VDM.0003/25) - o usuário está perguntando sobre um CCT específico.\n"
            contexto_str += f"⚠️ NÃO use consultar_status_processo - use consultar_cct diretamente com o número do CCT.\n"
        
        # ✅ NOVO: Adicionar contexto de categoria se houver
        categoria_para_usar = categoria_atual or categoria_contexto
        
        # ✅ CRÍTICO: Detectar se é pergunta sobre chegada com período temporal (não deve usar categoria do histórico)
        eh_pergunta_chegada_temporal = bool(
            re.search(r'chegando|chegam|chegar', mensagem.lower()) and
            re.search(r'(?:esta|essa|nesta|nessa)\s*semana|(?:este|neste)\s*m[êe]s|(?:semana|pr[óo]xima)\s*(?:que\s*)?vem|(?:m[êe]s\s+que\s+vem)|amanh[ãa]|hoje', mensagem.lower())
        )
        
        # ✅ CORREÇÃO: Incluir contexto de categoria mesmo em perguntas genéricas sobre pendências/situação
        # quando há categoria no histórico (ex: "como estao os alh?" → "tem pendencia?")
        # ✅ CRÍTICO: NÃO incluir categoria do histórico em perguntas sobre chegada com período temporal
        # ✅ CRÍTICO: NÃO incluir categoria do histórico em comandos de fechamento do dia
        incluir_contexto_categoria = (
            categoria_para_usar and 
            not numero_cct and
            not eh_fechamento_dia and  # ✅ NOVO: Fechamento do dia NUNCA usa categoria do contexto
            not eh_pergunta_chegada_temporal and  # ✅ CRÍTICO: Não usar categoria em perguntas sobre chegada com período
            (
                not eh_pergunta_generica or  # Pergunta não genérica
                (eh_pergunta_generica and (eh_pergunta_pendencias or eh_pergunta_situacao) and categoria_contexto)  # Pergunta genérica sobre pendências/situação com categoria no histórico
            )
        )
        
        if incluir_contexto_categoria:
            contexto_str += f"\n\n📋 ⚠️ CONTEXTO DE CATEGORIA: {categoria_para_usar}\n"
            contexto_str += f"O usuário está fazendo perguntas sobre processos da categoria {categoria_para_usar}.\n"
            if categoria_atual:
                contexto_str += f"⚠️ CRÍTICO: Esta categoria foi extraída da mensagem atual do usuário. Use {categoria_para_usar} para filtrar os resultados e IGNORE qualquer categoria do histórico anterior.\n"
            elif categoria_contexto:
                contexto_str += f"⚠️ IMPORTANTE: Esta categoria foi extraída do histórico da conversa (pergunta anterior sobre {categoria_para_usar}). Use {categoria_para_usar} para filtrar os resultados.\n"
                if eh_pergunta_pendencias:
                    contexto_str += f"⚠️ CRÍTICO: Esta é uma pergunta genérica sobre pendências, mas você DEVE usar a categoria {categoria_para_usar} do histórico. Use listar_processos_com_pendencias(categoria='{categoria_para_usar}').\n"
                elif eh_pergunta_situacao:
                    contexto_str += f"⚠️ CRÍTICO: Esta é uma pergunta genérica sobre situação, mas você DEVE usar a categoria {categoria_para_usar} do histórico. Use listar_processos_por_categoria(categoria='{categoria_para_usar}') ou listar_processos_por_situacao(categoria='{categoria_para_usar}').\n"
            contexto_str += f"⚠️ Quando o usuário fizer perguntas sem mencionar categoria (ex: 'quais estão bloqueados?', 'quais têm pendência?', 'tem pendencia?'), você DEVE usar a categoria {categoria_para_usar} para filtrar os resultados.\n"
            contexto_str += f"⚠️ EXCEÇÃO: Se a pergunta mencionar 'processos' ou 'todos' explicitamente E não for sobre pendências/situação após pergunta de categoria, IGNORE este contexto e busque TODOS os processos.\n"
        
        # ✅ NOVO: Adicionar aviso sobre pergunta genérica
        # ✅ EXCEÇÃO: Se é pergunta genérica sobre pendências/situação com categoria no histórico, NÃO mostrar aviso genérico
        # (o contexto de categoria já foi adicionado acima)
        mostrar_aviso_generico = (
            eh_pergunta_generica and 
            (
                not (eh_pergunta_pendencias or eh_pergunta_situacao) or  # Não é sobre pendências/situação
                not categoria_contexto  # Ou não tem categoria no histórico
            )
        )
        
        if mostrar_aviso_generico:
            contexto_str += f"\n\n⚠️ PERGUNTA GENÉRICA DETECTADA: Esta pergunta menciona 'processos' ou 'todos' explicitamente.\n"
            contexto_str += f"⚠️ IMPORTANTE: IGNORE qualquer contexto anterior de categoria ou processo específico.\n"
            contexto_str += f"⚠️ Busque TODOS os processos sem filtro de categoria.\n"
        
        # ✅ NOVO: Adicionar informação sobre necessidade de vincular processo se houver flag
        # Isso será adicionado dinamicamente após a execução de consultar_ce_maritimo
        
        if acao_info.get('acao'):
            contexto_str += f"\n\n🎯 AÇÃO IDENTIFICADA: {acao_info['acao']}"
        
        return contexto_str
    
    def _construir_historico_str(
        self,
        historico: List[Dict],
        mensagem: str,
        processo_ref: Optional[str] = None,
        extrair_processo_referencia_fn: Optional[Callable] = None,
    ) -> tuple[str, str]:
        """
        ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 4: Constrói historico_str e instrucao_processo.
        
        Extrai toda a lógica de construção de histórico do chat_service.py,
        incluindo filtragem por processo, detecção de vinculação, e formatação diferenciada
        para emails/relatórios vs outros comandos.
        
        Args:
            historico: Histórico de mensagens
            mensagem: Mensagem atual do usuário
            processo_ref: Processo de referência extraído
            extrair_processo_referencia_fn: Função helper para extrair processo
        
        Returns:
            Tuple com (historico_str, instrucao_processo)
        """
        import re
        
        historico_str = ''
        instrucao_processo = ''
        
        # ✅ NOVO (14/01/2026): Sempre extrair JSON inline da última resposta se existir
        # Abordagem natural: se há JSON na última resposta, sempre destacá-lo para a IA
        json_inline_ultima_resposta = None
        if historico and len(historico) > 0:
            ultima_resposta = historico[-1].get('resposta', '')
            # Procurar por [REPORT_META:{...}]
            match_json = re.search(r'\[REPORT_META:(\{.+?\})\]', ultima_resposta, re.DOTALL)
            if match_json:
                json_inline_ultima_resposta = match_json.group(1)
                logger.info(f"✅ JSON inline encontrado na última resposta - será destacado para a IA")
        
        # ✅ NOVO: Detectar se a última resposta da IA perguntou sobre vincular processo
        ultima_resposta_ia_perguntou_vinculacao = False
        numero_ce_para_vincular = None
        
        if historico:
            # Verificar última resposta da IA para ver se perguntou sobre vinculação
            if len(historico) > 0:
                ultima_resposta = historico[-1].get('resposta', '')
                if 'processo não vinculado' in ultima_resposta.lower() or 'qual processo você quer vincular' in ultima_resposta.lower() or 'processo vincular' in ultima_resposta.lower() or 'atencao: processo nao vinculado' in ultima_resposta.lower():
                    ultima_resposta_ia_perguntou_vinculacao = True
                    # Tentar extrair número do CE da última resposta da IA
                    padrao_ce_resposta = r'CE\s+(\d{10,15})'
                    match_ce = re.search(padrao_ce_resposta, ultima_resposta, re.IGNORECASE)
                    if match_ce:
                        numero_ce_para_vincular = match_ce.group(1)
                    
                    # Se não encontrou na resposta, tentar no histórico de mensagens anteriores do usuário
                    if not numero_ce_para_vincular:
                        for item in reversed(historico[-5:]):
                            item_msg = item.get('mensagem', '')
                            # Padrões para encontrar CE: "CE 132505338584530" ou "consulte o CE 132505338584530"
                            padrao_ce_msg = r'(?:CE|ce)\s+(\d{10,15})'
                            match_ce_msg = re.search(padrao_ce_msg, item_msg, re.IGNORECASE)
                            if match_ce_msg:
                                numero_ce_para_vincular = match_ce_msg.group(1)
                                break
                    
                    # Se ainda não encontrou, tentar buscar no resultado de tool calls anteriores
                    if not numero_ce_para_vincular:
                        # Verificar se há tool calls no histórico que consultaram CE
                        for item in reversed(historico[-3:]):
                            # Se houver dados de tool calling, tentar extrair número do CE
                            tool_calling = item.get('tool_calling')
                            if tool_calling and isinstance(tool_calling, dict):
                                # Verificar se há resultado de consultar_ce_maritimo
                                resultado = tool_calling.get('resultado')
                                if resultado and isinstance(resultado, dict):
                                    # Tentar extrair número do CE do resultado
                                    numero_ce_resultado = resultado.get('numero_ce') or resultado.get('numero')
                                    if numero_ce_resultado:
                                        numero_ce_para_vincular = str(numero_ce_resultado)
                                        break
                                    # Se não encontrou, tentar buscar no texto do resultado
                                    resultado_texto = str(resultado)
                                    padrao_ce_resultado = r'(?:CE|ce|numero[_\s]*ce)\s*[:\s]*(\d{10,15})'
                                    match_ce_resultado = re.search(padrao_ce_resultado, resultado_texto, re.IGNORECASE)
                                    if match_ce_resultado:
                                        numero_ce_para_vincular = match_ce_resultado.group(1)
                                        break
                                if numero_ce_para_vincular:
                                    break
            
            # Se há um processo específico na mensagem atual, filtrar histórico para remover outros processos
            historico_filtrado = []
            if processo_ref and extrair_processo_referencia_fn:
                # Incluir apenas mensagens do mesmo processo ou mensagens gerais (sem processo)
                for item in historico[-5:]:  # Últimas 5 mensagens
                    item_msg = item.get('mensagem', '')
                    item_proc = extrair_processo_referencia_fn(item_msg)
                    # Incluir se for do mesmo processo ou se não tiver processo (mensagem geral)
                    if not item_proc or item_proc == processo_ref:
                        historico_filtrado.append(item)
            else:
                # ✅ MELHORIA: Para outros comandos, aumentar de 2 para 5 mensagens para melhor contexto
                historico_filtrado = historico[-5:]  # Aumentado de 2 para 5 mensagens
                logger.debug(f"✅ Incluindo {len(historico_filtrado)} mensagens do histórico para contexto")
            
            if historico_filtrado:
                historico_str = "\n\n📜 Histórico da conversa (relevante):\n"
                # ✅ MELHORIA: Para emails e relatórios, não truncar tanto - precisamos do contexto completo
                mensagem_lower_hist = mensagem.lower()
                eh_comando_email_hist = any(palavra in mensagem_lower_hist for palavra in [
                    'email', 'envie', 'mande', 'envia', 'manda', 'monte', 'crie', 'prepare'
                ])
                eh_comando_relatorio = any(palavra in mensagem_lower_hist for palavra in [
                    'resumo', 'relatorio', 'relatório', 'dashboard', 'briefing', 'fechamento'
                ])
                
                for item in historico_filtrado:
                    # Limitar tamanho da mensagem do usuário
                    msg_usuario = item.get('mensagem', '')
                    limite_usuario = 200 if eh_comando_email_hist else 150
                    if len(msg_usuario) > limite_usuario:
                        msg_usuario = msg_usuario[:limite_usuario] + "..."
                    historico_str += f"Usuário: {msg_usuario}\n"
                    
                    # ✅ CRÍTICO: Para emails e relatórios, não truncar respostas - precisamos de TODAS as informações (NCM, alíquotas, etc.)
                    resposta_hist = item.get('resposta', '')
                    
                    # ✅ NOVO (14/01/2026): Extrair JSON inline antes de truncar para preservá-lo
                    json_inline_item = None
                    match_json_item = re.search(r'\[REPORT_META:(\{.+?\})\]', resposta_hist, re.DOTALL)
                    if match_json_item:
                        json_inline_item = match_json_item.group(0)  # Preservar o formato completo [REPORT_META:{...}]
                        # Remover JSON inline do texto antes de truncar
                        resposta_hist_sem_json = re.sub(r'\[REPORT_META:\{.+?\}\]', '', resposta_hist, flags=re.DOTALL).strip()
                    else:
                        resposta_hist_sem_json = resposta_hist
                    
                    if eh_comando_email_hist or eh_comando_relatorio:
                        # ✅ MELHORIA: Para emails e relatórios, incluir resposta completa (até 5000 caracteres) para capturar NCM, alíquotas, NESH, etc.
                        limite_resposta = 5000  # Aumentado de 2000 para 5000 caracteres
                        if len(resposta_hist_sem_json) > limite_resposta:
                            # Se for muito grande, tentar manter as partes mais importantes (NCM, alíquotas, NESH)
                            if 'NCM' in resposta_hist_sem_json or 'Alíquotas' in resposta_hist_sem_json or 'NESH' in resposta_hist_sem_json or 'TECwin' in resposta_hist_sem_json or 'Processo' in resposta_hist_sem_json:
                                # Manter início (geralmente tem NCM/Processo) e fim (geralmente tem alíquotas/detalhes)
                                inicio = resposta_hist_sem_json[:2000]  # Aumentado de 800 para 2000
                                fim = resposta_hist_sem_json[-2000:]  # Aumentado de 800 para 2000
                                resposta_hist = f"{inicio}\n\n[... conteúdo intermediário removido para economizar tokens ...]\n\n{fim}"
                            else:
                                resposta_hist = resposta_hist_sem_json[:limite_resposta] + "..."
                        else:
                            resposta_hist = resposta_hist_sem_json
                        
                        # ✅ CRÍTICO: Sempre adicionar JSON inline no final se existir
                        if json_inline_item:
                            resposta_hist = f"{resposta_hist}\n\n{json_inline_item}"
                        
                        historico_str += f"Assistente: {resposta_hist}\n"
                    else:
                        # ✅ MELHORIA: Para outros comandos, aumentar limite de 150 para 500 caracteres
                        if len(resposta_hist_sem_json) > 500:  # Aumentado de 150 para 500
                            resposta_hist = resposta_hist_sem_json[:500] + "..."
                        else:
                            resposta_hist = resposta_hist_sem_json
                        
                        # ✅ CRÍTICO: Sempre adicionar JSON inline no final se existir (mesmo em comandos não-relatório)
                        if json_inline_item:
                            resposta_hist = f"{resposta_hist}\n\n{json_inline_item}"
                        
                        historico_str += f"Assistente: {resposta_hist}\n"
        
        # ✅ NOVO (14/01/2026): Adicionar instrução natural sobre JSON inline se existir
        # Abordagem simples: se há JSON na última resposta, destacá-lo naturalmente para a IA
        if json_inline_ultima_resposta:
            try:
                import json
                json_data = json.loads(json_inline_ultima_resposta)
                # Construir instrução natural e simples para a IA
                instrucao_json = "\n\n📊 **Contexto da última resposta (JSON estruturado):**\n"
                instrucao_json += "A última resposta contém dados estruturados em formato JSON. Use essas informações para responder naturalmente:\n\n"
                instrucao_json += f"```json\n{json.dumps(json_data, indent=2, ensure_ascii=False)}\n```\n\n"
                
                # Adicionar informações úteis de forma natural
                if 'tipo' in json_data:
                    instrucao_json += f"💡 Tipo de relatório: {json_data['tipo']}\n"
                if 'secoes' in json_data and isinstance(json_data['secoes'], dict):
                    instrucao_json += "💡 Seções disponíveis com dados:\n"
                    for secao, dados in json_data['secoes'].items():
                        if isinstance(dados, list) and len(dados) > 0:
                            instrucao_json += f"   - {secao}: {len(dados)} item(ns)\n"
                        elif isinstance(dados, dict) and dados.get('count', 0) > 0:
                            instrucao_json += f"   - {secao}: {dados['count']} item(ns)\n"
                
                instrucao_json += "\n💡 **Dica:** Se a pergunta do usuário se refere ao que foi mostrado na última resposta, use os dados do JSON acima diretamente.\n"
                
                # ✅✅✅ CRÍTICO (14/01/2026): Se usuário pedir para enviar por email, instruir explicitamente a usar enviar_relatorio_email
                # Verificar se mensagem contém comando de envio por email
                mensagem_lower_check = mensagem.lower()
                if any(palavra in mensagem_lower_check for palavra in ['envie', 'enviar', 'mande', 'mandar', 'envia', 'manda']) and 'email' in mensagem_lower_check:
                    instrucao_json += "\n\n🚨🚨🚨 **INSTRUÇÃO CRÍTICA - ENVIO POR EMAIL:**\n"
                    instrucao_json += "A última resposta contém [REPORT_META:...] (relatório de processos).\n"
                    instrucao_json += "Quando o usuário pedir para enviar esse relatório por email, você DEVE usar a função enviar_relatorio_email.\n"
                    instrucao_json += "⚠️ NÃO use enviar_email_personalizado quando há [REPORT_META:...] na última resposta.\n"
                    instrucao_json += "⚠️ NÃO use outras funções relacionadas a NCM ou processos - use APENAS enviar_relatorio_email.\n"
                    instrucao_json += f"💡 O relatório tem ID: {json_data.get('id', 'N/A')} e tipo: {json_data.get('tipo', 'N/A')}\n"
                    logger.info(f"✅✅✅ Instrução CRÍTICA de envio por email adicionada (há [REPORT_META:...] na última resposta)")
                
                instrucao_processo = instrucao_json + (instrucao_processo if instrucao_processo else "")
                logger.info(f"✅ Instrução explícita sobre JSON inline adicionada ao prompt")
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"⚠️ Erro ao processar JSON inline: {e}")
                # Continuar normalmente mesmo se houver erro
        
        # ✅ MELHORIA: Ser explícito sobre qual processo está sendo consultado AGORA
        if processo_ref:
            # ✅ NOVO: Se a última resposta perguntou sobre vincular processo e o usuário forneceu um processo, instruir a IA a vincular
            if ultima_resposta_ia_perguntou_vinculacao:
                # Se não encontrou o número do CE ainda, tentar extrair da mensagem atual ou do histórico mais recente
                if not numero_ce_para_vincular:
                    # Tentar extrair da mensagem atual (caso o usuário tenha mencionado)
                    padrao_ce_atual = r'(?:CE|ce)\s+(\d{10,15})'
                    match_ce_atual = re.search(padrao_ce_atual, mensagem, re.IGNORECASE)
                    if match_ce_atual:
                        numero_ce_para_vincular = match_ce_atual.group(1)
                    else:
                        # Tentar buscar nas mensagens anteriores do usuário (últimas 3)
                        for item in reversed(historico[-3:]):
                            item_msg = item.get('mensagem', '')
                            padrao_ce_msg = r'(?:CE|ce)\s+(\d{10,15})'
                            match_ce_msg = re.search(padrao_ce_msg, item_msg, re.IGNORECASE)
                            if match_ce_msg:
                                numero_ce_para_vincular = match_ce_msg.group(1)
                                break
                
                if numero_ce_para_vincular:
                    instrucao_processo = f"\n\n⚠️⚠️⚠️ **VINCULAR PROCESSO AO CE - INSTRUÇÃO CRÍTICA:**\n"
                    instrucao_processo += f"O usuário forneceu o processo {processo_ref} para vincular ao CE {numero_ce_para_vincular}.\n"
                    instrucao_processo += f"⚠️ CRÍTICO: Você DEVE usar a função vincular_ce_ao_processo com:\n"
                    instrucao_processo += f"  - numero_ce='{numero_ce_para_vincular}'\n"
                    instrucao_processo += f"  - processo_referencia='{processo_ref}'\n"
                    instrucao_processo += f"⚠️ NÃO pergunte novamente - o usuário já forneceu o processo.\n"
                else:
                    instrucao_processo = f"\n\n⚠️⚠️⚠️ **VINCULAR PROCESSO AO CE - INSTRUÇÃO CRÍTICA:**\n"
                    instrucao_processo += f"A última resposta perguntou sobre vincular processo ao CE, e o usuário forneceu o processo {processo_ref}.\n"
                    instrucao_processo += f"⚠️ CRÍTICO: Você DEVE usar a função vincular_ce_ao_processo, mas PRIMEIRO precisa consultar o CE para obter o número.\n"
                    instrucao_processo += f"⚠️ Use consultar_ce_maritimo para encontrar o CE relacionado ao processo {processo_ref}, depois use vincular_ce_ao_processo.\n"
            else:
                instrucao_processo = f"\n\n⚠️ **PROCESSO ATUAL:** {processo_ref}\n"
                instrucao_processo += f"⚠️ IMPORTANTE: O usuário está perguntando sobre o processo {processo_ref} especificamente.\n"
                instrucao_processo += f"⚠️ Use consultar_status_processo com processo_referencia='{processo_ref}' para obter informações atualizadas.\n"
        
        return historico_str, instrucao_processo
    
    def _buscar_contexto_sessao(
        self,
        session_id: Optional[str],
        mensagem: str,
        processo_ref: Optional[str] = None,
        extrair_processo_referencia_fn: Optional[Callable] = None,
        eh_fechamento_dia: bool = False,
    ) -> str:
        """
        ✅ PASSO 3.5 - FASE 3.5.1 - SUB-ETAPA 5: Busca e formata contexto_sessao.
        
        Extrai toda a lógica de busca e limpeza de contexto de sessão do chat_service.py,
        incluindo detecção de processos diferentes, limpeza de contexto antigo, e formatação
        para incluir no prompt.
        
        Args:
            session_id: ID da sessão
            mensagem: Mensagem atual do usuário
            processo_ref: Processo de referência extraído
            extrair_processo_referencia_fn: Função helper para extrair processo
            eh_fechamento_dia: Se é comando de fechamento do dia
        
        Returns:
            String formatada com contexto de sessão para incluir no prompt
        """
        import re
        from services.context_service import buscar_contexto_sessao, formatar_contexto_para_prompt, limpar_contexto_sessao
        
        contexto_sessao_texto = ""
        
        try:
            if session_id:
                # Verificar se há processo mencionado na mensagem atual
                processo_na_mensagem = None
                if extrair_processo_referencia_fn:
                    processo_na_mensagem = extrair_processo_referencia_fn(mensagem)
                
                # Buscar contexto atual
                contextos = buscar_contexto_sessao(session_id, tipo_contexto="processo_atual")
                processo_do_contexto = None
                if contextos:
                    processo_do_contexto = contextos[0].get('valor', '').strip()
                
                # ✅ CORREÇÃO: Se usuário mencionou outro processo, limpar contexto antigo
                if processo_na_mensagem and processo_do_contexto:
                    if processo_na_mensagem.upper() != processo_do_contexto.upper():
                        logger.info(f"🔄 Processo diferente mencionado ({processo_na_mensagem} vs {processo_do_contexto}). Limpando contexto antigo.")
                        limpar_contexto_sessao(session_id, tipo_contexto="processo_atual")
                        processo_do_contexto = None
                
                # ✅ CORREÇÃO: Só usar contexto se:
                # 1. Não há processo mencionado na mensagem atual E
                # 2. A mensagem parece ser relacionada ao processo (não é "teste", "oi", etc.) E
                # 3. Não é pergunta genérica sobre "todos" ou "processos"
                usar_contexto = False
                
                # Verificar se mensagem parece ser relacionada ao processo
                mensagem_lower = mensagem.lower().strip()
                palavras_gerais = ['teste', 'oi', 'olá', 'hello', 'hi', 'tchau', 'bye', 'reset', 'limpar']
                eh_mensagem_geral = any(palavra in mensagem_lower for palavra in palavras_gerais)
                
                # Verificar se é pergunta genérica sobre "todos" ou "processos" ou "cargas" ou "status"
                # ✅ CORREÇÃO (12/01/2026): Incluir perguntas sobre cargas, status, etc. que não devem usar contexto de processo antigo
                eh_pergunta_todos = bool(
                    re.search(r'\b(?:todos|todas|tudo)\s+(?:os|as)?\s*(?:processos|processo)', mensagem_lower) or
                    re.search(r'(?:processos|processo)\s+(?:todos|todas|tudo)', mensagem_lower) or
                    re.search(r'quais?\s+(?:são|estão|tem)\s+(?:os|as)?\s*(?:processos|processo)', mensagem_lower) or
                    # Perguntas sobre cargas/status que não mencionam processo específico
                    re.search(r'quais?\s+(?:cargas?|processos?)\s+(?:que|com|estão|está)\s+(?:com|tem|têm)', mensagem_lower) or
                    re.search(r'quais?\s+(?:cargas?|processos?)\s+(?:estão|está)\s+(?:com|tem|têm)\s+(?:status|situação)', mensagem_lower) or
                    re.search(r'(?:cargas?|processos?)\s+(?:que|com|estão|está)\s+(?:com|tem|têm)\s+(?:status|situação)', mensagem_lower)
                )
                
                # Verificar se há processo_ref na mensagem atual (via processo_ref passado)
                tem_processo_na_mensagem = bool(processo_na_mensagem or processo_ref)
                
                # Usar contexto se:
                # - Não há processo mencionado na mensagem atual E
                # - Não é mensagem geral (teste, oi, etc.) E
                # - Não é pergunta genérica sobre "todos" E
                # - Há processo no contexto OU não há processo_ref (para não usar contexto quando há processo_ref mas não no contexto)
                usar_contexto = (
                    not tem_processo_na_mensagem and
                    not eh_mensagem_geral and
                    not eh_pergunta_todos and
                    processo_do_contexto is not None
                )
                
                # Buscar todos os contextos (incluindo categoria, etc.)
                if usar_contexto:
                    contextos_todos = buscar_contexto_sessao(session_id)
                    if contextos_todos:
                        contexto_sessao_texto = formatar_contexto_para_prompt(contextos_todos)
                        logger.debug(f"✅ {len(contextos_todos)} contextos de sessão incluídos no prompt")
                else:
                    # Buscar apenas contextos que não são processo_atual (categoria, etc.)
                    # ✅ CORREÇÃO: Se mensagem é sobre enviar relatorio/resumo ou dashboard, limpar também categoria
                    mensagem_lower_check = mensagem.lower().strip()
                    eh_comando_relatorio = any(palavra in mensagem_lower_check for palavra in [
                        'enviar relatorio', 'enviar relatório', 'enviar resumo', 
                        'enviar briefing', 'enviar dashboard', 'envia esse relatorio', 'envia esse relatório'
                    ])
                    eh_dashboard_hoje_check = bool(re.search(
                        r'o\s+que\s+tem(?:os)?\s+(?:pra|para)\s+hoje|dashboard\s+de\s+hoje|resumo\s+do\s+dia|o\s+que\s+est[áa]\s+chegando\s+hoje',
                        mensagem_lower_check
                    ))
                    eh_fechamento_dia_check = bool(re.search(
                        r'fechar\s+(?:o\s+)?dia|fechamento\s+(?:do\s+)?dia|resumo\s+(?:do\s+)?dia|finalizar\s+(?:o\s+)?dia|finalizacao\s+(?:do\s+)?dia',
                        mensagem_lower_check
                    ))
                    
                    if eh_comando_relatorio or eh_dashboard_hoje_check or eh_fechamento_dia_check or eh_fechamento_dia:
                        # ✅ CORREÇÃO (12/01/2026): Com JSON inline, NÃO limpar contexto automaticamente
                        # O JSON inline [REPORT_META:...] permite que a IA veja o que está na tela diretamente
                        # Mantendo o contexto, a IA pode usar tanto o JSON inline quanto o contexto salvo
                        # Isso torna o sistema mais inteligente e humanizado
                        # 
                        # ⚠️ NOTA: Ainda limpamos quando é comando explícito de reset/limpar
                        # Mas para relatórios gerais (dashboard, fechamento), mantemos o contexto
                        # porque o JSON inline já mostra o que está na tela e a IA pode decidir o que usar
                        if eh_fechamento_dia_check or eh_fechamento_dia:
                            tipo_comando = 'fechamento do dia'
                        elif eh_dashboard_hoje_check:
                            tipo_comando = 'dashboard do dia'
                        else:
                            tipo_comando = 'relatório'
                        logger.info(f"✅ Contexto MANTIDO para {tipo_comando} (JSON inline disponível - IA pode ver o que está na tela): {mensagem_lower_check}")
                        # ✅ NOVO: Buscar contexto normalmente (não limpar) - IA pode usar JSON inline + contexto
                        contextos_nao_processo = buscar_contexto_sessao(session_id)
                        contextos_nao_processo = [c for c in contextos_nao_processo if c.get('tipo_contexto') != 'processo_atual']
                    else:
                        contextos_nao_processo = buscar_contexto_sessao(session_id)
                        contextos_nao_processo = [c for c in contextos_nao_processo if c.get('tipo_contexto') != 'processo_atual']
                    
                    if contextos_nao_processo:
                        contexto_sessao_texto = formatar_contexto_para_prompt(contextos_nao_processo)
                        logger.debug(f"✅ {len(contextos_nao_processo)} contextos de sessão (não processo) incluídos no prompt")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar contexto de sessão: {e}")
        
        return contexto_sessao_texto