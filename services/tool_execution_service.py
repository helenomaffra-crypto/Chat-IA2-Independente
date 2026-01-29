"""
ToolExecutionService - Execução centralizada de tools com contexto enxuto.

Este serviço extrai a lógica de execução de tools do ChatService, usando um contexto
enxuto em vez de passar o chat_service inteiro.

Regra de ouro: Cada tool handler recebe apenas o que precisa, não o chat_service inteiro.
"""

import logging
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """
    Contexto enxuto para execução de tools.
    
    Contém apenas as dependências necessárias, não o chat_service inteiro.
    Isso permite testar tools isoladamente sem instanciar o ChatService.
    """
    # Serviços principais
    email_service: Optional[Any] = None
    email_draft_service: Optional[Any] = None
    email_send_coordinator: Optional[Any] = None
    duimp_service: Optional[Any] = None
    processo_status_service: Optional[Any] = None
    processo_list_service: Optional[Any] = None
    ncm_service: Optional[Any] = None
    documento_service: Optional[Any] = None
    context_service: Optional[Any] = None
    confirmation_handler: Optional[Any] = None  # ✅ FASE 1/Segurança: criar pending intents (email/duimp/pagamento)
    
    # Funções auxiliares (do chat_service, mas isoladas)
    obter_email_para_enviar: Optional[Callable] = None
    extrair_processo_referencia: Optional[Callable] = None
    obter_contexto_processo: Optional[Callable] = None
    limpar_frases_problematicas: Optional[Callable] = None
    
    # Dados de sessão
    session_id: Optional[str] = None
    mensagem_original: Optional[str] = None
    
    # Logger
    logger: Optional[Any] = None


class ToolExecutionService:
    """
    Serviço centralizado para execução de tools.
    
    Roteia chamadas de tools para handlers específicos, cada um recebendo
    apenas o contexto necessário (não o chat_service inteiro).
    """
    
    def __init__(self, tool_context: Optional[ToolContext] = None):
        """
        Inicializa o serviço.
        
        Args:
            tool_context: Contexto enxuto para execução de tools
        """
        self.tool_context = tool_context or ToolContext()
        self._handlers = {}
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """Inicializa handlers de tools."""
        # Registrar handlers conforme são extraídos
        self.registrar_handler('enviar_email_personalizado', self._handler_enviar_email_personalizado)
        self.registrar_handler('enviar_email', self._handler_enviar_email)
        self.registrar_handler('enviar_relatorio_email', self._handler_enviar_relatorio_email)
        self.registrar_handler('melhorar_email_draft', self._handler_melhorar_email_draft)
        self.registrar_handler('ler_emails', self._handler_ler_emails)
        self.registrar_handler('obter_detalhes_email', self._handler_obter_detalhes_email)
        self.registrar_handler('responder_email', self._handler_responder_email)
        self.registrar_handler('buscar_ncms_por_descricao', self._handler_buscar_ncms_por_descricao)
        self.registrar_handler('sugerir_ncm_com_ia', self._handler_sugerir_ncm_com_ia)
        self.registrar_handler('detalhar_ncm', self._handler_detalhar_ncm)
        self.registrar_handler('baixar_nomenclatura_ncm', self._handler_baixar_nomenclatura_ncm)
        self.registrar_handler('buscar_nota_explicativa_nesh', self._handler_buscar_nota_explicativa_nesh)
        self.registrar_handler('obter_valores_processo', self._handler_obter_valores_processo)
        self.registrar_handler('obter_valores_ce', self._handler_obter_valores_ce)
        self.registrar_handler('obter_dados_di', self._handler_obter_dados_di)
        self.registrar_handler('obter_dados_duimp', self._handler_obter_dados_duimp)
        self.registrar_handler('salvar_regra_aprendida', self._handler_salvar_regra_aprendida)
        self.registrar_handler('salvar_consulta_personalizada', self._handler_salvar_consulta_personalizada)
        self.registrar_handler('buscar_consulta_personalizada', self._handler_buscar_consulta_personalizada)
        self.registrar_handler('executar_consulta_analitica', self._handler_executar_consulta_analitica)
        self.registrar_handler('listar_consultas_bilhetadas_pendentes', self._handler_listar_consultas_bilhetadas_pendentes)
        self.registrar_handler('aprovar_consultas_bilhetadas', self._handler_aprovar_consultas_bilhetadas)
        self.registrar_handler('rejeitar_consultas_bilhetadas', self._handler_rejeitar_consultas_bilhetadas)
        self.registrar_handler('ver_status_consultas_bilhetadas', self._handler_ver_status_consultas_bilhetadas)
        self.registrar_handler('listar_consultas_aprovadas_nao_executadas', self._handler_listar_consultas_aprovadas_nao_executadas)
        self.registrar_handler('executar_consultas_aprovadas', self._handler_executar_consultas_aprovadas)
        self.registrar_handler('calcular_impostos_ncm', self._handler_calcular_impostos_ncm)

        # ========== SISTEMA / OBSERVABILIDADE / APRENDIZADO ==========
        # Mantidos em módulo separado para evitar crescer o ToolExecutionService.
        try:
            from services.handlers.system_tools_handler import SystemToolsHandler

            self.registrar_handler('verificar_fontes_dados', SystemToolsHandler.verificar_fontes_dados)
            self.registrar_handler('obter_resumo_aprendizado', SystemToolsHandler.obter_resumo_aprendizado)
            self.registrar_handler('obter_relatorio_observabilidade', SystemToolsHandler.obter_relatorio_observabilidade)
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível registrar handlers de sistema (observabilidade/aprendizado): {e}")

        # ========== FASE 2: ELIMINAR FALLBACK REAL RESTANTE ==========
        # Mantido em módulo separado para não crescer este arquivo.
        try:
            from services.handlers.fallback_phase2_tools_handler import Phase2ToolsHandler

            self.registrar_handler('listar_categorias_disponiveis', Phase2ToolsHandler.listar_categorias_disponiveis)
            self.registrar_handler('adicionar_categoria_processo', Phase2ToolsHandler.adicionar_categoria_processo)
            self.registrar_handler('desvincular_documento_processo', Phase2ToolsHandler.desvincular_documento_processo)
            self.registrar_handler('vincular_processo_cct', Phase2ToolsHandler.vincular_processo_cct)
            self.registrar_handler('gerar_resumo_reuniao', Phase2ToolsHandler.gerar_resumo_reuniao)
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível registrar handlers da Fase 2 (fallback residual): {e}")

        # ========== VENDAS (Make/Spalla) ==========
        # Mantido em módulo separado para evitar crescer este arquivo.
        try:
            from services.handlers.sales_tools_handler import SalesToolsHandler

            self.registrar_handler('consultar_vendas_make', SalesToolsHandler.consultar_vendas_make)
            self.registrar_handler('consultar_vendas_nf_make', SalesToolsHandler.consultar_vendas_nf_make)
            self.registrar_handler('filtrar_relatorio_vendas', SalesToolsHandler.filtrar_relatorio_vendas)
            self.registrar_handler('curva_abc_vendas', SalesToolsHandler.curva_abc_vendas)
            self.registrar_handler('inspecionar_schema_nf_make', SalesToolsHandler.inspecionar_schema_nf_make)
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível registrar handlers de vendas (Make/Spalla): {e}")
    
    def executar_tool(
        self,
        nome_funcao: str,
        argumentos: Dict[str, Any],
        tool_context: Optional[ToolContext] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executa uma tool.
        
        Args:
            nome_funcao: Nome da função/tool a executar
            argumentos: Argumentos da função
            tool_context: Contexto enxuto (opcional, usa self.tool_context se não fornecido)
        
        Returns:
            Dict com resultado da execução, ou None para indicar "sem handler" (deixe o próximo nível resolver).
        """
        context = tool_context or self.tool_context
        
        # Verificar se tem handler específico
        handler = self._handlers.get(nome_funcao)
        if handler:
            try:
                return handler(argumentos, context)
            except Exception as e:
                logger.error(f'❌ Erro ao executar tool {nome_funcao}: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': str(e),
                    'resposta': f'❌ Erro ao executar {nome_funcao}: {str(e)}'
                }
        
        # Sem handler aqui → deixe o próximo nível decidir (ToolRouter e/ou legado do ChatService).
        return None
    
    def registrar_handler(self, nome_funcao: str, handler: Callable):
        """
        Registra um handler para uma tool específica.
        
        Args:
            nome_funcao: Nome da função/tool
            handler: Função que recebe (argumentos, context) e retorna Dict
        """
        self._handlers[nome_funcao] = handler
        logger.info(f'✅ Handler registrado para tool: {nome_funcao}')
    
    # ========================================================================
    # Handlers de Tools (serão extraídos incrementalmente)
    # ========================================================================
    
    def _handler_enviar_email_personalizado(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext
    ) -> Dict[str, Any]:
        """
        Handler para enviar_email_personalizado.
        
        ✅ NOVO (09/01/2026): Usa EmailSendCoordinator quando tem draft_id.
        """
        destinatarios = argumentos.get('destinatarios', [])
        assunto = argumentos.get('assunto', '')
        conteudo = argumentos.get('conteudo', '')
        cc = argumentos.get('cc', [])
        bcc = argumentos.get('bcc', [])
        confirmar_envio = argumentos.get('confirmar_envio', False)
        draft_id = argumentos.get('draft_id')  # ✅ NOVO: Suportar draft_id direto
        
        # Limpar frases problemáticas
        if conteudo and context.limpar_frases_problematicas:
            conteudo = context.limpar_frases_problematicas(conteudo)
        
        if not destinatarios or not assunto or not conteudo:
            return {
                'sucesso': False,
                'erro': 'PARAMETROS_OBRIGATORIOS',
                'resposta': '❌ destinatarios, assunto e conteudo são obrigatórios.'
            }
        
        # ✅ NOVO: Se tem draft_id e confirmar_envio, usar EmailSendCoordinator
        if draft_id and confirmar_envio and context.email_send_coordinator:
            logger.info(f'✅✅✅ [TOOL_EXECUTION] Usando EmailSendCoordinator para enviar draft {draft_id}')
            resultado = context.email_send_coordinator.send_from_draft(draft_id, force=False)
            return resultado
        
        # Se não confirmou, mostrar preview e pedir confirmação
        if not confirmar_envio:
            # Criar draft se não tem draft_id
            if not draft_id and context.email_draft_service:
                try:
                    draft_id = context.email_draft_service.criar_draft(
                        destinatarios=destinatarios,
                        assunto=assunto,
                        conteudo=conteudo,
                        session_id=context.session_id or 'default',
                        funcao_email='enviar_email_personalizado',
                        cc=cc if cc else None,
                        bcc=bcc if bcc else None
                    )
                    logger.info(f'✅ Draft criado: {draft_id}')
                except Exception as e:
                    logger.warning(f'⚠️ Erro ao criar draft: {e}')
            
            from datetime import datetime
            preview = f"📧 **Email para Envio**\n\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += f"**De:** Sistema mAIke (Make Consultores)\n"
            preview += f"**Para:** {', '.join(destinatarios)}\n"
            if cc:
                preview += f"**CC:** {', '.join(cc)}\n"
            if bcc:
                preview += f"**BCC:** {', '.join(bcc)}\n"
            preview += f"**Assunto:** {assunto}\n"
            preview += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            preview += f"**Mensagem:**\n\n"
            preview += f"{conteudo}\n\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += f"⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"

            # ✅ FASE 1/Segurança (14/01/2026): Criar PendingIntent no preview (SQLite como fonte da verdade)
            # Isso garante que a confirmação ("sim") funcione mesmo sem memória e após refresh.
            try:
                if context.confirmation_handler and context.session_id:
                    destinatario_hash = destinatarios[0] if isinstance(destinatarios, list) and len(destinatarios) == 1 else (', '.join(destinatarios) if destinatarios else None)
                    dados_email_pendente = {
                        'funcao': 'enviar_email_personalizado',
                        'destinatario': destinatario_hash,
                        'assunto': assunto,
                        'draft_id': draft_id,
                    }
                    intent_id = context.confirmation_handler.criar_pending_intent_email(
                        session_id=context.session_id,
                        dados_email=dados_email_pendente,
                        preview_text=preview[:500]
                    )
                    if intent_id:
                        logger.info(f'✅ PendingIntent criado (email_personalizado): {intent_id}')
            except Exception as e:
                logger.warning(f'⚠️ Erro ao criar PendingIntent (email_personalizado): {e}')
            
            return {
                'sucesso': True,
                'resposta': preview,
                'aguardando_confirmacao': True,
                'draft_id': draft_id,
                'tool_calling': {'name': 'enviar_email_personalizado', 'arguments': argumentos},
                '_resultado_interno': {
                    'ultima_resposta_aguardando_email': {
                        'destinatarios': destinatarios,
                        'cc': cc,
                        'bcc': bcc,
                        'assunto': assunto,
                        'conteudo': conteudo,
                        'funcao': 'enviar_email_personalizado',
                        'draft_id': draft_id
                    }
                }
            }
        
        # Se confirmou e não tem draft_id, criar e enviar
        if confirmar_envio and not draft_id:
            # Fallback: usar email_service diretamente (compatibilidade com código antigo)
            if not context.email_service:
                from services.email_service import get_email_service
                context.email_service = get_email_service()
            
            # Enviar para todos os destinatários (compatível com implementação antiga)
            resultados = []
            for destinatario in destinatarios:
                resultado = context.email_service.enviar_email(
                    destinatario=destinatario,
                    assunto=assunto,
                    corpo_texto=conteudo
                )
                resultados.append({
                    'destinatario': destinatario,
                    'sucesso': resultado.get('sucesso', False),
                    'erro': resultado.get('erro')
                })
            
            # Verificar se todos foram enviados
            sucessos = sum(1 for r in resultados if r['sucesso'])
            if sucessos == len(resultados):
                resposta = f"✅ Email enviado com sucesso para {len(destinatarios)} destinatário(s):\n"
                for r in resultados:
                    resposta += f"  - {r['destinatario']}\n"
                resposta += f"\n**Assunto:** {assunto}\n\n**Mensagem:**\n{conteudo[:200]}..."
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'destinatarios': destinatarios
                }
            else:
                resposta = f"⚠️ Email enviado parcialmente:\n"
                for r in resultados:
                    if r['sucesso']:
                        resposta += f"  ✅ {r['destinatario']}\n"
                    else:
                        resposta += f"  ❌ {r['destinatario']}: {r.get('erro', 'Erro desconhecido')}\n"
                return {
                    'sucesso': False,
                    'erro': 'ENVIO_PARCIAL',
                    'resposta': resposta
                }
        
        return {
            'sucesso': False,
            'erro': 'ESTADO_INCONSISTENTE',
            'resposta': '❌ Estado inconsistente: confirmação sem draft_id e sem email_service'
        }
    
    def _handler_enviar_email(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext
    ) -> Dict[str, Any]:
        """
        Handler para enviar_email (email simples).
        
        Compatível com código antigo, mas pode usar EmailSendCoordinator no futuro.
        """
        destinatario = argumentos.get('destinatario')
        assunto = argumentos.get('assunto', '')
        corpo = argumentos.get('corpo', '')
        confirmar_envio = argumentos.get('confirmar_envio', False)
        
        # Limpar frases problemáticas
        if corpo and context.limpar_frases_problematicas:
            corpo = context.limpar_frases_problematicas(corpo)
        
        if not destinatario or not assunto or not corpo:
            return {
                'sucesso': False,
                'erro': 'PARAMETROS_OBRIGATORIOS',
                'resposta': '❌ destinatario, assunto e corpo são obrigatórios.'
            }
        
        # Se não confirmou, mostrar preview e pedir confirmação
        if not confirmar_envio:
            from datetime import datetime
            preview = f"📧 **Email para Envio**\n\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += f"**De:** Sistema mAIke (Make Consultores)\n"
            preview += f"**Para:** {destinatario}\n"
            preview += f"**Assunto:** {assunto}\n"
            preview += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            preview += f"**Mensagem:**\n\n"
            preview += f"{corpo}\n\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += f"⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"
            
            return {
                'sucesso': True,
                'resposta': preview,
                'aguardando_confirmacao': True,
                'tool_calling': {'name': 'enviar_email', 'arguments': argumentos},
                '_resultado_interno': {
                    'ultima_resposta_aguardando_email': {
                        'funcao': 'enviar_email',
                        'destinatario': destinatario,
                        'assunto': assunto,
                        'corpo': corpo
                    }
                }
            }
        
        # Se confirmou, enviar por email
        if not context.email_service:
            from services.email_service import get_email_service
            context.email_service = get_email_service()
        
        resultado = context.email_service.enviar_email(
            destinatario=destinatario,
            assunto=assunto,
            corpo_texto=corpo
        )
        
        if resultado.get('sucesso'):
            return {
                'sucesso': True,
                'resposta': f"✅ Email enviado com sucesso para **{destinatario}**\n\n**Assunto:** {assunto}\n\n**Mensagem:**\n{corpo}",
                'destinatario': destinatario,
                'metodo': resultado.get('metodo', 'SMTP'),
                '_resultado_interno': {'ultima_resposta_aguardando_email': None}
            }
        else:
            erro_msg = resultado.get('erro') or resultado.get('mensagem', 'Erro desconhecido')
            return {
                'sucesso': False,
                'erro': resultado.get('erro', 'ERRO_ENVIO_EMAIL'),
                'resposta': f"❌ Erro ao enviar email: {erro_msg}"
            }
    
    def _handler_enviar_relatorio_email(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext
    ) -> Optional[Dict[str, Any]]:
        """
        Handler para enviar_relatorio_email.
        
        ✅ Refactor (15/01/2026): Centraliza preview + pending intent + envio aqui,
        usando `services.report_service` (REPORT_META/last_visible/active) em vez de lógica legada do ChatService.
        """
        destinatario = argumentos.get('destinatario')
        confirmar_envio = argumentos.get('confirmar_envio', False)
        categoria = argumentos.get('categoria')
        tipo_relatorio = argumentos.get('tipo_relatorio', 'resumo')
        modal = argumentos.get('modal')
        apenas_pendencias = argumentos.get('apenas_pendencias', False)
        report_id = argumentos.get('report_id')

        if not destinatario:
            # A tool_definitions orienta perguntar antes de enviar para email errado.
            return {
                'sucesso': False,
                'erro': 'PARAMETROS_OBRIGATORIOS',
                'resposta': '❌ destinatario é obrigatório. Informe o email (ex: "envie para helenomaffra@gmail.com").'
            }

        # 1) Resolver relatório (preferir report_id injetado pelo ToolGate / fornecido explicitamente).
        session_id = context.session_id
        mensagem_original = context.mensagem_original or ''

        relatorio = None
        relatorio_meta = None
        resolved_report_id = None

        try:
            from services import report_service

            if report_id and session_id:
                relatorio = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=report_id)
                resolved_report_id = report_id
            elif session_id:
                # pick_report considera active_report_id, TTL e ambiguidade.
                escolha = report_service.pick_report(session_id=session_id, mensagem=mensagem_original)
                relatorio = escolha.get('relatorio')
                relatorio_meta = escolha
                if relatorio and getattr(relatorio, 'texto_chat', None):
                    # Tentar extrair o id pelo histórico (melhor-effort)
                    try:
                        history = report_service.obter_report_history(session_id=session_id, limite=10) or []
                        if history and history[0].get('id'):
                            resolved_report_id = history[0].get('id')
                    except Exception:
                        resolved_report_id = None
            else:
                relatorio = None
        except Exception as e:
            logger.warning(f'⚠️ Erro ao resolver relatório para enviar_relatorio_email: {e}')
            relatorio = None

        if relatorio_meta and relatorio_meta.get('ambiguo'):
            opcoes = relatorio_meta.get('opcoes') or []
            linhas = []
            for i, opt in enumerate(opcoes[:5], start=1):
                rid = opt.get('id') or '(sem id)'
                tipo = opt.get('tipo') or 'relatorio'
                data = opt.get('created_at') or ''
                linhas.append(f'({i}) {tipo} - {rid} {f"- {data}" if data else ""}'.strip())
            lista = "\n".join(linhas) if linhas else "(sem opções)"
            return {
                'sucesso': False,
                'erro': 'RELATORIO_AMBIGUO',
                'resposta': (
                    "📋 Há mais de um relatório recente na sessão.\n\n"
                    f"{lista}\n\n"
                    "Diga qual você quer enviar (ex: \"envie o (1)\"), ou gere um novo relatório."
                ),
            }

        if not relatorio or not getattr(relatorio, 'texto_chat', None):
            return {
                'sucesso': False,
                'erro': 'RELATORIO_NAO_ENCONTRADO',
                'resposta': '❌ Não encontrei um relatório salvo para enviar. Gere um relatório primeiro (ex: "o que temos pra hoje?") e tente novamente.',
            }

        # 2) Montar resumo_texto a enviar (remover REPORT_META do corpo do email).
        resumo_texto = relatorio.texto_chat
        try:
            import re
            resumo_texto = re.sub(r'\[REPORT_META:\{.+?\}\]\s*', '', resumo_texto, flags=re.DOTALL).strip()
        except Exception:
            resumo_texto = (resumo_texto or '').strip()

        # 3) Se confirmou (fluxo legado/confirm handler), enviar imediatamente via EmailSendCoordinator.
        if confirmar_envio:
            if not context.email_send_coordinator:
                from services.email_send_coordinator import get_email_send_coordinator
                context.email_send_coordinator = get_email_send_coordinator()

            assunto = argumentos.get('assunto')
            if not assunto:
                # Assunto determinístico (simples) baseado no tipo e categoria.
                assunto_base = 'Relatório'
                if getattr(relatorio, 'tipo_relatorio', None):
                    assunto_base = str(relatorio.tipo_relatorio).replace('_', ' ').strip().title() or 'Relatório'
                assunto = f"{assunto_base}{f' - {categoria}' if categoria else ''}"

            logger.info('✅✅✅ [TOOL_EXECUTION] Enviando relatório via EmailSendCoordinator')
            return context.email_send_coordinator.send_report_email(
                destinatario=destinatario,
                resumo_texto=resumo_texto,
                assunto=assunto,
                categoria=categoria
            )

        # 4) Preview + criar PendingIntent (fonte da verdade no SQLite).
        from datetime import datetime
        assunto = argumentos.get('assunto')
        if not assunto:
            assunto_base = 'Relatório'
            if getattr(relatorio, 'tipo_relatorio', None):
                assunto_base = str(relatorio.tipo_relatorio).replace('_', ' ').strip().title() or 'Relatório'
            assunto = f"{assunto_base}{f' - {categoria}' if categoria else ''}"

        preview = "📊 **Relatório para Envio por Email**\n\n"
        preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        preview += "**De:** Sistema mAIke (Make Consultores)\n"
        preview += f"**Para:** {destinatario}\n"
        preview += f"**Assunto:** {assunto}\n"
        preview += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        if resolved_report_id:
            preview += f"**Report ID:** {resolved_report_id}\n"
        if categoria:
            preview += f"**Categoria:** {categoria}\n"
        if tipo_relatorio:
            preview += f"**Tipo:** {tipo_relatorio}\n"
        if modal:
            preview += f"**Modal:** {modal}\n"
        if apenas_pendencias:
            preview += "**Filtro:** apenas pendências\n"
        preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        preview += "**Conteúdo:**\n\n"
        preview += f"{resumo_texto}\n\n"
        preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        preview += "⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"

        # Criar pending intent (se disponível) com args completos para execução.
        try:
            if context.confirmation_handler and context.session_id:
                args_para_execucao = {
                    'destinatario': destinatario,
                    'categoria': categoria,
                    'tipo_relatorio': tipo_relatorio,
                    'modal': modal,
                    'apenas_pendencias': apenas_pendencias,
                }
                if resolved_report_id:
                    args_para_execucao['report_id'] = resolved_report_id
                elif report_id:
                    args_para_execucao['report_id'] = report_id

                dados_email_pendente = {
                    'funcao': 'enviar_relatorio_email',
                    'destinatario': destinatario,
                    'assunto': assunto,
                    'resumo_texto': resumo_texto,
                    'argumentos': args_para_execucao
                }
                intent_id = context.confirmation_handler.criar_pending_intent_email(
                    session_id=context.session_id,
                    dados_email=dados_email_pendente,
                    preview_text=preview[:500]
                )
                if intent_id:
                    logger.info(f'✅ PendingIntent criado (enviar_relatorio_email): {intent_id}')
        except Exception as e:
            logger.warning(f'⚠️ Erro ao criar PendingIntent (enviar_relatorio_email): {e}')

        return {
            'sucesso': True,
            'resposta': preview,
            'aguardando_confirmacao': True,
            'tool_calling': {'name': 'enviar_relatorio_email', 'arguments': argumentos},
            '_resultado_interno': {
                'ultima_resposta_aguardando_email': {
                    'funcao': 'enviar_relatorio_email',
                    'destinatario': destinatario,
                    'assunto': assunto,
                    'resumo_texto': resumo_texto,
                    'argumentos': {
                        'categoria': categoria,
                        'tipo_relatorio': tipo_relatorio,
                        'modal': modal,
                        'apenas_pendencias': apenas_pendencias,
                        'report_id': resolved_report_id or report_id,
                    }
                }
            }
        }

    # ========================================================================
    # Handlers adicionais (migração do legado do ChatService)
    # ========================================================================

    def _handler_melhorar_email_draft(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Handler para melhorar_email_draft (sistema de versões)."""
        draft_id = argumentos.get('draft_id')
        assunto = argumentos.get('assunto')
        conteudo = argumentos.get('conteudo')

        if not assunto and not conteudo:
            return {
                'sucesso': False,
                'erro': 'PARAMETROS_OBRIGATORIOS',
                'resposta': '❌ É necessário fornecer pelo menos assunto ou conteudo melhorado.'
            }

        try:
            if not context.email_draft_service:
                from services.email_draft_service import get_email_draft_service
                context.email_draft_service = get_email_draft_service()

            # Se não tem draft_id, tentar achar o último draft da sessão
            if not draft_id and context.session_id:
                drafts = context.email_draft_service.listar_drafts(
                    session_id=context.session_id,
                    status=None,
                    limit=1,
                )
                if drafts:
                    draft_id = drafts[0].draft_id

            if not draft_id:
                return {
                    'sucesso': False,
                    'erro': 'DRAFT_ID_NAO_ENCONTRADO',
                    'resposta': '❌ Não foi possível encontrar o draft do email para melhorar. Gere um preview de email primeiro.'
                }

            nova_revision = context.email_draft_service.revisar_draft(
                draft_id=draft_id,
                assunto=assunto,
                conteudo=conteudo,
            )
            if not nova_revision:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_REVISAO',
                    'resposta': '❌ Erro ao revisar draft.'
                }

            draft_atualizado = context.email_draft_service.obter_draft(draft_id)
            if not draft_atualizado:
                return {
                    'sucesso': False,
                    'erro': 'DRAFT_NAO_ENCONTRADO',
                    'resposta': '❌ Draft não encontrado após revisão.'
                }

            from datetime import datetime
            preview = f"📧 **Email para Envio (Atualizado - Revisão {nova_revision})**\n\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += f"**De:** Sistema mAIke (Make Consultores)\n"
            preview += f"**Para:** {', '.join(draft_atualizado.destinatarios)}\n"
            if draft_atualizado.cc:
                preview += f"**CC:** {', '.join(draft_atualizado.cc)}\n"
            if draft_atualizado.bcc:
                preview += f"**BCC:** {', '.join(draft_atualizado.bcc)}\n"
            preview += f"**Assunto:** {draft_atualizado.assunto}\n"
            preview += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            preview += f"**Mensagem:**\n\n"
            preview += f"{draft_atualizado.conteudo}\n\n"
            preview += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview += f"⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"

            return {
                'sucesso': True,
                'resposta': preview,
                'aguardando_confirmacao': True,
                'draft_id': draft_id,
                'revision': nova_revision,
                '_resultado_interno': {
                    'ultima_resposta_aguardando_email': {
                        'funcao': 'enviar_email_personalizado',
                        'draft_id': draft_id,
                    }
                }
            }
        except Exception as e:
            logger.error(f'❌ Erro ao melhorar_email_draft: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao melhorar email: {str(e)}'
            }

    def _handler_ler_emails(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Handler para ler_emails."""
        limit = argumentos.get('limit', 10)
        apenas_nao_lidos = argumentos.get('apenas_nao_lidos', False)
        max_dias = argumentos.get('max_dias', 7)

        try:
            if not context.email_service:
                from services.email_service import get_email_service
                context.email_service = get_email_service()

            resultado = context.email_service.read_emails(
                limit=limit,
                filter_read=apenas_nao_lidos,
                max_days=max_dias,
            )

            if not resultado.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'ERRO_LER_EMAILS'),
                    'resposta': f"❌ Erro ao ler emails: {resultado.get('erro', 'Erro desconhecido')}"
                }

            emails = resultado.get('emails', []) or []
            if not emails:
                return {
                    'sucesso': True,
                    'resposta': f"📥 Nenhum email encontrado{' não lido' if apenas_nao_lidos else ''} nos últimos {max_dias} dias.",
                    'emails': []
                }

            debug_info = resultado.get('debug') or {}
            fallback_sem_filtro_data = bool(debug_info.get('fallback_sem_filtro_data', False))
            cutoff_utc = debug_info.get('cutoff_utc')
            mailbox = debug_info.get('mailbox')

            resposta = f"📥 **Emails encontrados:** {len(emails)}\n\n"
            if fallback_sem_filtro_data:
                # ✅ Transparência: se o filtro por data não retornou nada, avisar para evitar confusão
                # (ex.: usuário espera emails de hoje, mas a caixa lida não tem emails recentes).
                detalhe = f" (mailbox: {mailbox})" if mailbox else ""
                detalhe += f" (cutoff UTC: {cutoff_utc})" if cutoff_utc else ""
                resposta = (
                    f"⚠️ Não encontrei emails nos últimos {max_dias} dias com o filtro padrão."
                    f" Vou mostrar os emails mais recentes disponíveis{detalhe}.\n\n"
                ) + resposta
            for i, email in enumerate(emails, 1):
                data_recebido = email.get('received_datetime', 'N/A')
                if data_recebido and data_recebido != 'N/A':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(data_recebido.replace('Z', '+00:00'))
                        data_recebido = dt.strftime('%d/%m/%Y %H:%M')
                    except Exception:
                        pass

                status_emoji = '📬' if not email.get('is_read', False) else '✅'
                assunto = email.get('subject', 'Sem assunto')
                remetente = email.get('from', 'Desconhecido')
                preview = email.get('body_preview', '')

                resposta += f"{i}. {status_emoji} **{assunto}**\n"
                resposta += f"   De: {remetente}\n"
                resposta += f"   Data: {data_recebido}\n"
                if preview:
                    resposta += f"   Preview: {preview[:100]}...\n"
                resposta += "\n"

            resposta += "💡 Para ver detalhes de um email, diga: 'detalhe email 1' ou 'ler email 3'."

            return {
                'sucesso': True,
                'resposta': resposta,
                'emails': emails,
            }
        except Exception as e:
            logger.error(f'❌ Erro ao ler_emails: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao ler emails: {str(e)}'
            }

    def _handler_obter_detalhes_email(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Handler para obter_detalhes_email."""
        message_id = argumentos.get('message_id')
        email_index = argumentos.get('email_index')

        try:
            if not context.email_service:
                from services.email_service import get_email_service
                context.email_service = get_email_service()

            # Se veio só índice, refazer listagem e pegar o ID
            if not message_id and isinstance(email_index, int) and email_index > 0:
                lista = context.email_service.read_emails(limit=max(10, email_index), filter_read=False, max_days=7)
                if lista.get('sucesso') and lista.get('emails'):
                    emails = lista['emails']
                    if 0 <= (email_index - 1) < len(emails):
                        message_id = emails[email_index - 1].get('id')

            if not message_id:
                return {
                    'sucesso': False,
                    'erro': 'PARAMETROS_OBRIGATORIOS',
                    'resposta': '❌ message_id ou email_index é obrigatório.'
                }

            resultado = context.email_service.get_email_by_id(message_id=message_id)
            if not resultado.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'ERRO_OBTER_EMAIL'),
                    'resposta': f"❌ Erro ao obter detalhes do email: {resultado.get('erro', 'Erro desconhecido')}"
                }

            email = resultado.get('email', {})
            data_recebido = email.get('received_datetime', 'N/A')
            if data_recebido and data_recebido != 'N/A':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(data_recebido.replace('Z', '+00:00'))
                    data_recebido = dt.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    pass

            body = email.get('body', '')
            body_type = (email.get('body_type') or '').lower()
            if body_type == 'html' and body:
                try:
                    from html import unescape
                    import re
                    body = re.sub(r'<[^>]+>', '', body)
                    body = unescape(body)
                except Exception:
                    pass

            resposta = "📧 **Detalhes do Email**\n\n"
            resposta += f"**Assunto:** {email.get('subject', 'Sem assunto')}\n"
            resposta += f"**De:** {email.get('from_name', '')} <{email.get('from', 'Desconhecido')}>\n"
            if email.get('to'):
                resposta += f"**Para:** {', '.join(email.get('to', []))}\n"
            if email.get('cc'):
                resposta += f"**CC:** {', '.join(email.get('cc', []))}\n"
            resposta += f"**Data:** {data_recebido}\n"
            resposta += f"**Status:** {'✅ Lido' if email.get('is_read') else '📬 Não lido'}\n"
            resposta += f"**Importância:** {email.get('importance', 'normal').upper()}\n"
            if email.get('has_attachments'):
                resposta += "**Anexos:** Sim\n"
            resposta += f"\n**Corpo do Email:**\n{body or email.get('body_preview', 'N/A')}\n"

            return {'sucesso': True, 'resposta': resposta, 'email': email}
        except Exception as e:
            logger.error(f'❌ Erro ao obter_detalhes_email: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao obter detalhes do email: {str(e)}'
            }

    def _handler_responder_email(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """Handler para responder_email."""
        message_id = argumentos.get('message_id')
        resposta_txt = argumentos.get('resposta')
        if not message_id or not resposta_txt:
            return {
                'sucesso': False,
                'erro': 'PARAMETROS_OBRIGATORIOS',
                'resposta': '❌ message_id e resposta são obrigatórios.'
            }

        try:
            if not context.email_service:
                from services.email_service import get_email_service
                context.email_service = get_email_service()

            resultado = context.email_service.reply_to_email(
                message_id=message_id,
                reply_content=resposta_txt,
            )
            if resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'resposta': f"✅ Email respondido com sucesso!\n\n**Resposta enviada:**\n{resposta_txt}",
                    'message_id': message_id,
                }
            return {
                'sucesso': False,
                'erro': resultado.get('erro', 'ERRO_RESPONDER_EMAIL'),
                'resposta': f"❌ Erro ao responder email: {resultado.get('erro', 'Erro desconhecido')}"
            }
        except Exception as e:
            logger.error(f'❌ Erro ao responder_email: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao responder email: {str(e)}'
            }

    def _handler_buscar_ncms_por_descricao(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        termo = argumentos.get('termo') or argumentos.get('descricao') or ''
        limite = argumentos.get('limite', 50)
        incluir_relacionados = argumentos.get('incluir_relacionados', True)
        try:
            if not context.ncm_service:
                from services.ncm_service import NCMService
                context.ncm_service = NCMService(chat_service=None)
            return context.ncm_service.buscar_ncms_por_descricao(
                termo=termo,
                limite=limite,
                incluir_relacionados=incluir_relacionados,
                mensagem_original=context.mensagem_original,
            )
        except Exception as e:
            logger.error(f'❌ Erro ao buscar_ncms_por_descricao: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao buscar NCMs: {str(e)}'}

    def _handler_sugerir_ncm_com_ia(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        descricao = argumentos.get('descricao') or ''
        try:
            if not context.ncm_service:
                from services.ncm_service import NCMService
                context.ncm_service = NCMService(chat_service=None)
            resultado = context.ncm_service.sugerir_ncm_com_ia(
                descricao=descricao,
                contexto=argumentos.get('contexto'),
                usar_cache=argumentos.get('usar_cache', True),
                validar_sugestao=argumentos.get('validar_sugestao', True),
                mensagem_original=context.mensagem_original,
            )
            # ✅ Preservar comportamento do legado: salvar contexto para uso em emails
            try:
                if resultado and resultado.get('sucesso') and resultado.get('ncm_sugerido') and context.session_id:
                    from services.context_service import salvar_contexto_sessao
                    contexto_ncm = {
                        'ncm': resultado.get('ncm_sugerido', ''),
                        'descricao': descricao,
                        'confianca': resultado.get('confianca', 0.0),
                        'nota_nesh': resultado.get('nota_nesh', ''),
                        'ncms_alternativos': resultado.get('ncms_alternativos', []),
                        'explicacao': resultado.get('explicacao', ''),
                    }
                    salvar_contexto_sessao(
                        session_id=context.session_id,
                        tipo_contexto='ultima_classificacao_ncm',
                        chave='ncm',
                        valor=resultado.get('ncm_sugerido', ''),
                        dados_adicionais=contexto_ncm,
                    )
            except Exception as _e:
                logger.debug(f'⚠️ Falha ao salvar contexto de NCM: {_e}')

            return resultado
        except Exception as e:
            logger.error(f'❌ Erro ao sugerir_ncm_com_ia: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao sugerir NCM: {str(e)}'}

    def _handler_detalhar_ncm(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        ncm = argumentos.get('ncm') or ''
        try:
            if not context.ncm_service:
                from services.ncm_service import NCMService
                context.ncm_service = NCMService(chat_service=None)
            return context.ncm_service.detalhar_ncm(ncm=ncm, mensagem_original=context.mensagem_original)
        except Exception as e:
            logger.error(f'❌ Erro ao detalhar_ncm: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao detalhar NCM: {str(e)}'}

    def _handler_baixar_nomenclatura_ncm(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        forcar = argumentos.get('forcar_atualizacao', False)
        try:
            if not context.ncm_service:
                from services.ncm_service import NCMService
                context.ncm_service = NCMService(chat_service=None)
            return context.ncm_service.baixar_nomenclatura_ncm(
                forcar_atualizacao=forcar,
                mensagem_original=context.mensagem_original,
            )
        except Exception as e:
            logger.error(f'❌ Erro ao baixar_nomenclatura_ncm: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao baixar nomenclatura NCM: {str(e)}'}

    def _handler_buscar_nota_explicativa_nesh(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            if not context.ncm_service:
                from services.ncm_service import NCMService
                context.ncm_service = NCMService(chat_service=None)
            return context.ncm_service.buscar_nota_explicativa_nesh(
                ncm=(argumentos.get('ncm') or None),
                descricao_produto=(argumentos.get('descricao_produto') or None),
                limite=argumentos.get('limite', 3),
                mensagem_original=context.mensagem_original,
            )
        except Exception as e:
            logger.error(f'❌ Erro ao buscar_nota_explicativa_nesh: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao buscar NESH: {str(e)}'}

    def _handler_obter_valores_processo(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            if not context.documento_service:
                from services.documento_service import DocumentoService
                context.documento_service = DocumentoService(chat_service=None)
            return context.documento_service.obter_valores_processo(
                argumentos.get('processo_referencia', '').strip(),
                argumentos.get('tipo_valor', 'todos').strip().lower(),
            )
        except Exception as e:
            logger.error(f'❌ Erro ao obter_valores_processo: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao obter valores do processo: {str(e)}'}

    def _handler_obter_valores_ce(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            if not context.documento_service:
                from services.documento_service import DocumentoService
                context.documento_service = DocumentoService(chat_service=None)
            return context.documento_service.obter_valores_ce(
                argumentos.get('numero_ce', '').strip(),
                argumentos.get('tipo_valor', 'todos').strip().lower(),
            )
        except Exception as e:
            logger.error(f'❌ Erro ao obter_valores_ce: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao obter valores do CE: {str(e)}'}

    def _handler_obter_dados_di(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            if not context.documento_service:
                from services.documento_service import DocumentoService
                context.documento_service = DocumentoService(chat_service=None)
            return context.documento_service.obter_dados_di(argumentos.get('numero_di', '').strip())
        except Exception as e:
            logger.error(f'❌ Erro ao obter_dados_di: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao obter dados da DI: {str(e)}'}

    def _handler_obter_dados_duimp(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            if not context.documento_service:
                from services.documento_service import DocumentoService
                context.documento_service = DocumentoService(chat_service=None)
            return context.documento_service.obter_dados_duimp(
                numero_duimp=argumentos.get('numero_duimp', '').strip(),
                versao_duimp=(argumentos.get('versao_duimp') or None),
            )
        except Exception as e:
            logger.error(f'❌ Erro ao obter_dados_duimp: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao obter dados da DUIMP: {str(e)}'}

    def _handler_salvar_regra_aprendida(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            from services.learned_rules_service import salvar_regra_aprendida
            resultado = salvar_regra_aprendida(
                tipo_regra=argumentos.get('tipo_regra', ''),
                contexto=argumentos.get('contexto', ''),
                nome_regra=argumentos.get('nome_regra', ''),
                descricao=argumentos.get('descricao', ''),
                aplicacao_sql=argumentos.get('aplicacao_sql'),
                aplicacao_texto=argumentos.get('aplicacao_texto'),
                exemplo_uso=argumentos.get('exemplo_uso'),
                criado_por=context.session_id,
            )
            if resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'resposta': f"✅ Regra aprendida salva (ID: {resultado.get('id')}).",
                    'regra_id': resultado.get('id'),
                }
            return {
                'sucesso': False,
                'erro': resultado.get('erro', 'ERRO_SALVAR_REGRA'),
                'resposta': f"❌ Erro ao salvar regra: {resultado.get('erro', 'Erro desconhecido')}",
            }
        except Exception as e:
            logger.error(f'❌ Erro ao salvar_regra_aprendida: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao salvar regra: {str(e)}'}

    def _handler_salvar_consulta_personalizada(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            from services.saved_queries_service import salvar_consulta_personalizada
            resultado = salvar_consulta_personalizada(
                nome_exibicao=argumentos.get('nome_exibicao', ''),
                slug=argumentos.get('slug', ''),
                descricao=argumentos.get('descricao', ''),
                sql=argumentos.get('sql', ''),
                parametros=argumentos.get('parametros'),
                exemplos_pergunta=argumentos.get('exemplos_pergunta'),
                criado_por=context.session_id,
                regra_aprendida_id=argumentos.get('regra_aprendida_id'),
                contexto_regra=argumentos.get('contexto_regra'),
            )
            if resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'resposta': f"✅ Consulta salva com sucesso (ID: {resultado.get('id')}).",
                    'consulta_id': resultado.get('id'),
                }
            return {
                'sucesso': False,
                'erro': resultado.get('erro', 'ERRO_SALVAR_CONSULTA'),
                'resposta': f"❌ Erro ao salvar consulta: {resultado.get('erro', 'Erro desconhecido')}",
            }
        except Exception as e:
            logger.error(f'❌ Erro ao salvar_consulta_personalizada: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao salvar consulta: {str(e)}'}

    @staticmethod
    def _formatar_tabela_markdown(dados: Any, limite_linhas: int = 50) -> str:
        """Formata lista de dicts em tabela Markdown simples."""
        if not dados:
            return "ℹ️ Nenhum resultado encontrado."
        if not isinstance(dados, list):
            return "ℹ️ Resultado em formato não tabular."
        if not dados:
            return "ℹ️ Nenhum resultado encontrado."
        primeira = dados[0]
        if not isinstance(primeira, dict):
            return "ℹ️ Resultado em formato não tabular."

        cabecalhos = list(primeira.keys())
        out = "| " + " | ".join(cabecalhos) + " |\n"
        out += "|" + "|".join(["---"] * len(cabecalhos)) + "|\n"
        for linha in dados[:limite_linhas]:
            if not isinstance(linha, dict):
                continue
            valores = [str(linha.get(c, ''))[:50] for c in cabecalhos]
            out += "| " + " | ".join(valores) + " |\n"
        if len(dados) > limite_linhas:
            out += f"\n⚠️ Mostrando apenas as primeiras {limite_linhas} linhas de {len(dados)} resultados."
        return out

    def _handler_buscar_consulta_personalizada(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        try:
            from services.saved_queries_service import buscar_consulta_personalizada
            from services.analytical_query_service import executar_consulta_analitica

            texto = argumentos.get('texto_pedido_usuario') or argumentos.get('texto') or context.mensagem_original or ''
            if not texto:
                return {
                    'sucesso': False,
                    'erro': 'TEXTO_OBRIGATORIO',
                    'resposta': '❌ Texto do pedido é obrigatório para buscar consulta personalizada.'
                }

            resultado_busca = buscar_consulta_personalizada(texto)
            if not resultado_busca.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': 'CONSULTA_NAO_ENCONTRADA',
                    'resposta': f"❌ {resultado_busca.get('erro', 'Consulta não encontrada')}"
                }

            consulta = resultado_busca.get('consulta') or {}
            sql = consulta.get('sql_base', '')
            nome = consulta.get('nome_exibicao', 'Consulta salva')

            resultado_exec = executar_consulta_analitica(sql=sql)
            if not resultado_exec.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': resultado_exec.get('erro', 'ERRO_EXECUCAO'),
                    'resposta': f"❌ Erro ao executar consulta salva: {resultado_exec.get('erro', 'Erro desconhecido')}"
                }

            dados = resultado_exec.get('dados', []) or []
            linhas = resultado_exec.get('linhas_retornadas', 0)

            resposta = f"✅ **{nome}** ({linhas} linha{'s' if linhas != 1 else ''})\n\n"
            resposta += self._formatar_tabela_markdown(dados)

            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': dados,
                'consulta': consulta
            }
        except Exception as e:
            logger.error(f'❌ Erro ao buscar_consulta_personalizada: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao buscar consulta: {str(e)}'}

    def _handler_executar_consulta_analitica(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        sql = argumentos.get('sql', '')
        limit = argumentos.get('limit')
        if not sql:
            return {
                'sucesso': False,
                'erro': 'SQL_OBRIGATORIO',
                'resposta': '❌ SQL é obrigatório para executar consulta analítica.'
            }
        try:
            from services.analytical_query_service import executar_consulta_analitica
            resultado = executar_consulta_analitica(sql=sql, limit=limit)
            if not resultado.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'ERRO_DESCONHECIDO'),
                    'resposta': f"❌ Erro ao executar consulta: {resultado.get('erro', 'Erro desconhecido')}"
                }
            dados = resultado.get('dados', []) or []
            linhas = resultado.get('linhas_retornadas', 0)
            fonte = resultado.get('fonte', 'sqlite')
            resposta = f"✅ **Consulta executada com sucesso** ({linhas} linha{'s' if linhas != 1 else ''}, fonte: {fonte})\n\n"
            resposta += self._formatar_tabela_markdown(dados)
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': dados,
                'linhas_retornadas': linhas,
                'fonte': fonte
            }
        except Exception as e:
            logger.error(f'❌ Erro ao executar_consulta_analitica: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao executar consulta analítica: {str(e)}'
            }

    def _handler_listar_consultas_bilhetadas_pendentes(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        from services.consultas_bilhetadas_service import ConsultasBilhetadasService
        service = ConsultasBilhetadasService(chat_service=None)
        return service.listar_consultas_bilhetadas_pendentes(
            status_filtro=(argumentos.get('status') or '').strip() or None,
            limite=argumentos.get('limite', 50),
            tipo_consulta=(argumentos.get('tipo_consulta') or '').strip() or None,
            mensagem_original=context.mensagem_original,
        )

    def _handler_aprovar_consultas_bilhetadas(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        from services.consultas_bilhetadas_service import ConsultasBilhetadasService
        service = ConsultasBilhetadasService(chat_service=None)
        return service.aprovar_consultas_bilhetadas(
            ids_raw=argumentos.get('ids', []) or [],
            tipo_consulta=(argumentos.get('tipo_consulta') or '').strip() or None,
            aprovar_todas=bool(argumentos.get('aprovar_todas', False)),
            mensagem_original=context.mensagem_original,
        )

    def _handler_rejeitar_consultas_bilhetadas(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        from services.consultas_bilhetadas_service import ConsultasBilhetadasService
        service = ConsultasBilhetadasService(chat_service=None)
        return service.rejeitar_consultas_bilhetadas(
            ids_raw=argumentos.get('ids', []) or [],
            tipo_consulta=(argumentos.get('tipo_consulta') or '').strip() or None,
            rejeitar_todas=bool(argumentos.get('rejeitar_todas', False)),
            motivo=(argumentos.get('motivo') or '').strip() or None,
            mensagem_original=context.mensagem_original,
        )

    def _handler_ver_status_consultas_bilhetadas(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        from services.consultas_bilhetadas_service import ConsultasBilhetadasService
        service = ConsultasBilhetadasService(chat_service=None)
        return service.ver_status_consultas_bilhetadas(
            consulta_id=argumentos.get('consulta_id'),
            mensagem_original=context.mensagem_original,
        )

    def _handler_listar_consultas_aprovadas_nao_executadas(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        from services.consultas_bilhetadas_service import ConsultasBilhetadasService
        service = ConsultasBilhetadasService(chat_service=None)
        return service.listar_consultas_aprovadas_nao_executadas(
            tipo_consulta=(argumentos.get('tipo_consulta') or '').strip() or None,
            limite=argumentos.get('limite', 50),
            mensagem_original=context.mensagem_original,
        )

    def _handler_executar_consultas_aprovadas(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        from services.consultas_bilhetadas_service import ConsultasBilhetadasService
        service = ConsultasBilhetadasService(chat_service=None)
        return service.executar_consultas_aprovadas(
            ids_raw=argumentos.get('ids', []) or [],
            tipo_consulta=(argumentos.get('tipo_consulta') or '').strip() or None,
            executar_todas=bool(argumentos.get('executar_todas', False)),
            mensagem_original=context.mensagem_original,
        )

    def _handler_calcular_impostos_ncm(
        self,
        argumentos: Dict[str, Any],
        context: ToolContext,
    ) -> Dict[str, Any]:
        """
        Handler para calcular_impostos_ncm.

        Migrado do fallback do ChatService para evitar dependência de legado.
        Regras:
        - Busca alíquotas do contexto TECwin (session_id) se não forem fornecidas pelo usuário
        - Aceita CIF direto (cif_usd) OU custo_usd+frete_usd(+seguro_usd)
        - Se usuário pedir "explicando/passso a passo", inclui explicação detalhada
        """
        from services.calculo_impostos_service import CalculoImpostosService
        from services.context_service import buscar_contexto_sessao

        session_id = getattr(context, "session_id", None)
        if not session_id:
            return {
                'sucesso': False,
                'erro': 'SESSION_ID_REQUIRED',
                'resposta': '❌ **Erro:** Não foi possível identificar a sessão para buscar alíquotas do TECwin.'
            }

        calculo_service = CalculoImpostosService()

        # Alíquotas: usuário tem prioridade
        aliquotas_ii_usuario = argumentos.get('aliquotas_ii')
        aliquotas_ipi_usuario = argumentos.get('aliquotas_ipi')
        aliquotas_pis_usuario = argumentos.get('aliquotas_pis')
        aliquotas_cofins_usuario = argumentos.get('aliquotas_cofins')

        aliquotas: Dict[str, float] = {}
        if any(v is not None for v in [aliquotas_ii_usuario, aliquotas_ipi_usuario, aliquotas_pis_usuario, aliquotas_cofins_usuario]):
            try:
                if aliquotas_ii_usuario is not None:
                    aliquotas['ii'] = float(aliquotas_ii_usuario)
                if aliquotas_ipi_usuario is not None:
                    aliquotas['ipi'] = float(aliquotas_ipi_usuario)
                if aliquotas_pis_usuario is not None:
                    aliquotas['pis'] = float(aliquotas_pis_usuario)
                if aliquotas_cofins_usuario is not None:
                    aliquotas['cofins'] = float(aliquotas_cofins_usuario)
            except Exception:
                return {
                    'sucesso': False,
                    'erro': 'ALIQUOTAS_INVALIDAS',
                    'resposta': '❌ **Alíquotas inválidas.** Verifique se você informou percentuais numéricos (ex: 18, 9.75).'
                }
        else:
            aliquotas = calculo_service.extrair_aliquotas_do_contexto(session_id) or {}

        if not aliquotas:
            return {
                'sucesso': False,
                'erro': 'ALIQUOTAS_NAO_ENCONTRADAS',
                'resposta': (
                    '❌ **Alíquotas não encontradas!**\n\n'
                    'Para calcular impostos, primeiro consulte o NCM no TECwin (ex: `tecwin 07129020`).\n'
                    'Depois, peça: “calcule os impostos…”'
                )
            }

        cif_usd = argumentos.get('cif_usd')
        custo_usd = argumentos.get('custo_usd')
        frete_usd = argumentos.get('frete_usd')
        seguro_usd = argumentos.get('seguro_usd', 0.0)
        cotacao_ptax = argumentos.get('cotacao_ptax')

        # Validar valores de entrada
        if cif_usd is not None:
            if cotacao_ptax is None:
                return {
                    'sucesso': False,
                    'erro': 'COTACAO_FALTANDO',
                    'resposta': '❌ **Cotação PTAX faltando.** Informe a cotação (R$/USD) para calcular com CIF direto.'
                }
        else:
            faltando = []
            if custo_usd is None:
                faltando.append('custo_usd (USD) ou cif_usd (USD)')
            if frete_usd is None:
                faltando.append('frete_usd (USD) ou cif_usd (USD)')
            if cotacao_ptax is None:
                faltando.append('cotacao_ptax (R$/USD)')
            if faltando:
                return {
                    'sucesso': False,
                    'erro': 'VALORES_FALTANDO',
                    'resposta': (
                        '❌ **Valores faltando:**\n\n' +
                        '\n'.join([f'• {v}' for v in faltando]) +
                        '\n\n💡 Você também pode informar **CIF direto** usando `cif_usd`.'
                    )
                }

        # Buscar NCM do contexto (se houver)
        contextos_ncm = buscar_contexto_sessao(session_id, tipo_contexto='ncm_aliquotas')
        ncm = contextos_ncm[0].get('valor') if contextos_ncm else None

        resultado = calculo_service.calcular_impostos(
            custo_usd=custo_usd,
            frete_usd=frete_usd,
            seguro_usd=seguro_usd,
            cotacao_ptax=cotacao_ptax,
            aliquotas=aliquotas,
            ncm=ncm,
            cif_usd=cif_usd,
        )

        if not resultado.get('sucesso'):
            return {
                'sucesso': False,
                'erro': resultado.get('erro', 'ERRO_DESCONHECIDO'),
                'resposta': f'❌ **Erro ao calcular impostos:** {resultado.get("erro", "Erro desconhecido")}'
            }

        msg_lower = (context.mensagem_original or '').lower()
        incluir_explicacao = any(k in msg_lower for k in [
            'explicando', 'explicar', 'detalhado', 'detalhada', 'mostrando',
            'mostrar', 'fórmulas', 'formulas', 'passo a passo', 'como chegou'
        ])

        resposta_formatada = calculo_service.formatar_resposta_calculo(
            resultado,
            incluir_explicacao=incluir_explicacao
        )
        return {
            'sucesso': True,
            'resposta': resposta_formatada,
            'dados': resultado
        }


def get_tool_execution_service(tool_context: Optional[ToolContext] = None) -> ToolExecutionService:
    """Factory function para obter instância do serviço."""
    return ToolExecutionService(tool_context=tool_context)
