"""
ChatServiceStreamingMixin

Mantém a implementação de streaming fora do `chat_service.py` para reduzir o
tamanho/complexidade do arquivo principal (sem mudar comportamento).
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChatServiceStreamingMixin:
    def processar_mensagem_stream(
        self,
        mensagem: str,
        historico: Optional[List[Dict]] = None,
        usar_tool_calling: bool = True,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        nome_usuario: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        Processa mensagem do usuário com streaming - retorna generator de chunks.

        Este método é similar a processar_mensagem, mas retorna chunks progressivamente
        usando streaming da API da OpenAI.

        Yields:
            Dict com chunks contendo:
            - 'chunk': str (pedaço do texto)
            - 'done': bool (se terminou)
            - 'tool_calls': list (se houver tool calls)
            - 'resposta_final': str (resposta completa quando terminar)
        """
        if not self.enabled:
            yield {
                'chunk': 'Serviço de IA não está habilitado. Configure DUIMP_AI_ENABLED=true e DUIMP_AI_API_KEY no arquivo .env',
                'done': True,
                'tool_calls': None,
                'resposta_final': 'Serviço de IA não está habilitado.'
            }
            return

        historico = historico or []
        self.nome_usuario_atual = nome_usuario
        self.session_id_atual = session_id

        # ✅ NOVO: Detectar comandos de interface ANTES de qualquer processamento (igual ao método normal)
        # Permite que o usuário diga "maike menu" ou "maike quero conciliar banco" e abra diretamente
        comando_interface = self._detectar_comando_interface(mensagem)
        if comando_interface:
            logger.info(f"🎯 [STREAM] Comando de interface detectado: {comando_interface}")
            # Retornar como um chunk especial indicando comando de interface
            # IMPORTANTE: O frontend deve processar este chunk e executar a ação imediatamente
            yield {
                'chunk': '',  # Não há chunk de texto
                'done': True,  # Termina imediatamente
                'tool_calls': None,
                'resposta_final': f"✅ {comando_interface.get('tipo', 'comando')} detectado!",
                'comando_interface': comando_interface,  # ✅ Flag especial para o frontend - deve ser processado antes de qualquer outro chunk
                'acao': 'comando_interface'
            }
            logger.info(f"✅ [STREAM] Comando de interface enviado ao frontend: {comando_interface}")
            return  # Retorna imediatamente sem processar pela IA

        # ✅ CRÍTICO (21/01/2026): Reset/limpar contexto deve funcionar também no STREAM.
        # O endpoint /api/chat/stream não passava pelo handler de reset do método normal,
        # então o comando acabava caindo em RAG/legislação e "grudando" na sessão.
        try:
            resultado_limpar_contexto = self._processar_comando_limpar_contexto_antes_precheck(
                mensagem=mensagem,
                session_id=session_id,
            )
            if resultado_limpar_contexto:
                resposta_final = resultado_limpar_contexto.get('resposta', '✅ Contexto limpo com sucesso!')
                yield {
                    'chunk': resposta_final,
                    'done': True,
                    'tool_calls': None,
                    'resposta_final': resposta_final,
                    'acao': resultado_limpar_contexto.get('acao'),
                    'contexto_limpo': resultado_limpar_contexto.get('contexto_limpo', True),
                    'limpar_historico_frontend': resultado_limpar_contexto.get('limpar_historico_frontend', True),
                }
                return
        except Exception as e_reset_stream:
            logger.error(f"❌ [STREAM] Erro ao processar comando de limpar contexto: {e_reset_stream}", exc_info=True)
            resposta_final = (
                "❌ Tive um erro ao limpar o contexto.\n\n"
                "💡 Tente novamente com `reset`. Se persistir, recarregue a página."
            )
            yield {
                'chunk': resposta_final,
                'done': True,
                'tool_calls': None,
                'resposta_final': resposta_final,
                'sucesso': False,
                'erro': 'ERRO_LIMPAR_CONTEXTO_STREAM',
            }
            return

        # ✅ COERÊNCIA (27/01/2026): "o que registramos ontem/hoje/dia DD/MM" no STREAM (evita cair na IA e dar "Unexpected token")
        mensagem_lower_precheck = (mensagem or '').lower().strip()
        categoria_reg = getattr(self, '_extrair_categoria_da_mensagem', lambda m: None)(mensagem) if hasattr(self, '_extrair_categoria_da_mensagem') else None
        # "o que registramos 22/01" / "dia 22/01/26" — ano omitido = ano atual
        match_data_registramos = re.search(
            r'(?:o\s+que|quais?)\s+(?:registramos|foi\s+registrado|foram\s+registrados)\s+(?:(?:dia|em|no\s+dia)\s*)?(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?=\D|$)',
            mensagem_lower_precheck,
        )
        if match_data_registramos:
            from datetime import date
            dd, mm, yy_opt = match_data_registramos.group(1), match_data_registramos.group(2), match_data_registramos.group(3)
            ano_eff = date.today().year if not yy_opt else (2000 + int(yy_opt)) if len(yy_opt) == 2 else int(yy_opt)
            data_dd_mm_aaaa = f"{int(dd):02d}/{int(mm):02d}/{ano_eff}"
            logger.info(f'🔍 [STREAM] "O que registramos dia {data_dd_mm_aaaa}" detectado. Categoria: {categoria_reg or "TODAS"}.')
            try:
                resultado_reg = self._executar_funcao_tool('listar_processos_registrados_periodo', {
                    'categoria': (categoria_reg or '').upper() if categoria_reg else None,
                    'periodo': 'periodo_especifico',
                    'data_inicio': data_dd_mm_aaaa,
                    'data_fim': data_dd_mm_aaaa,
                    'limite': 200,
                }, mensagem_original=mensagem)
                if resultado_reg and resultado_reg.get('resposta'):
                    yield {
                        'chunk': resultado_reg.get('resposta', ''),
                        'done': True,
                        'tool_calls': None,
                        'resposta_final': resultado_reg.get('resposta', ''),
                        'sucesso': True,
                    }
                    return
            except Exception as e_reg:
                logger.error(f'❌ [STREAM] Erro em listar_processos_registrados_periodo(dia={data_dd_mm_aaaa}): {e_reg}', exc_info=True)
        eh_ontem = bool(
            re.search(r'(?:o\s+que|quais?)\s+(?:registramos|foi\s+registrado|foram\s+registrados)\s+ontem', mensagem_lower_precheck)
            or re.search(r'registramos\s+ontem|foi\s+registrado\s+ontem|foram\s+registrados\s+ontem', mensagem_lower_precheck)
        )
        eh_hoje = bool(
            re.search(r'(?:o\s+que|quais?)\s+(?:registramos|foi\s+registrado|foram\s+registrados)\s+hoje', mensagem_lower_precheck)
            or re.search(r'registramos\s+hoje|foi\s+registrado\s+hoje|foram\s+registrados\s+hoje', mensagem_lower_precheck)
        )
        if eh_ontem or eh_hoje:
            periodo = 'ontem' if eh_ontem else 'hoje'
            logger.info(f'🔍 [STREAM] "O que registramos {periodo}" detectado. Categoria: {categoria_reg or "TODAS"}.')
            try:
                resultado_reg = self._executar_funcao_tool('listar_processos_registrados_periodo', {
                    'categoria': (categoria_reg or '').upper() if categoria_reg else None,
                    'periodo': periodo,
                    'limite': 200,
                }, mensagem_original=mensagem)
                if resultado_reg and resultado_reg.get('resposta'):
                    resposta_final = resultado_reg.get('resposta', '')
                    yield {
                        'chunk': resposta_final,
                        'done': True,
                        'tool_calls': None,
                        'resposta_final': resposta_final,
                        'sucesso': True,
                    }
                    return
            except Exception as e_reg:
                logger.error(f'❌ [STREAM] Erro em listar_processos_registrados_periodo({periodo}): {e_reg}', exc_info=True)
            # Se falhou, não return – deixa cair no fluxo normal (IA pode tentar)

        # ✅ Estado de email em preview (usado para detectar "melhorar email" antes de confirmação)
        ultima_resposta_aguardando_email, dados_email_para_enviar = self._obter_estado_email_pendente(historico, session_id=session_id)
        if ultima_resposta_aguardando_email and dados_email_para_enviar:
            logger.info(
                f'✅✅✅ [STREAM] Preview de email detectado - aguardando confirmação. '
                f'Função: {dados_email_para_enviar.get("funcao", "N/A")}'
            )

        # ✅ CRÍTICO: Detectar se usuário está pedindo para melhorar email ANTES de verificar confirmação
        eh_correcao_email_destinatario = False  # Inicializar variável
        eh_pedido_melhorar_email = self._detectar_pedido_melhorar_email_preview(
            mensagem=mensagem,
            ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
            dados_email_para_enviar=dados_email_para_enviar,
            eh_correcao_email_destinatario=eh_correcao_email_destinatario,
            log_prefix='[STREAM] ',
        )

        # ✅ Correção de destinatário (antes do precheck)
        resultado_correcao_email, eh_correcao_email_destinatario, dados_email_para_enviar = (
            self._processar_correcao_email_destinatario_antes_precheck(
                mensagem=mensagem,
                ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
                dados_email_para_enviar=dados_email_para_enviar,
                session_id=session_id,
            )
        )
        if resultado_correcao_email:
            resposta_final = resultado_correcao_email.get('resposta', '')
            yield {
                'chunk': resposta_final,
                'done': True,
                'tool_calls': None,
                'resposta_final': resposta_final,
                '_resultado_interno': resultado_correcao_email.get('_resultado_interno'),
            }
            return

        # ✅ Confirmação de email centralizada (igual ao método normal)
        resultado_confirmacao_email, ultima_resposta_aguardando_email, dados_email_para_enviar = (
            self._processar_confirmacao_email_antes_precheck(
                mensagem=mensagem,
                historico=historico,
                session_id=session_id,
                eh_pedido_melhorar_email=eh_pedido_melhorar_email,
            )
        )
        if resultado_confirmacao_email:
            resposta_final = resultado_confirmacao_email.get('resposta', '')
            yield {
                'chunk': resposta_final,
                'done': True,
                'tool_calls': None,
                'resposta_final': resposta_final,
                '_resultado_interno': resultado_confirmacao_email.get('_resultado_interno'),
                'email_enviado': resultado_confirmacao_email.get('email_enviado', False),
                'error': resultado_confirmacao_email.get('erro') if not resultado_confirmacao_email.get('sucesso', True) else None,
            }
            return

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
                        
                        logger.info(f'🔍 [STREAM] Verificando confirmação de pagamento AFRMM: mensagem="{mensagem}", eh_confirmacao={eh_confirmacao}, pending_payment={pending_payment.get("intent_id") if pending_payment else None}')
                        
                        if eh_confirmacao:
                            logger.info(f'✅✅✅ [STREAM] Confirmação de pagamento AFRMM detectada (mensagem: "{mensagem}")')
                            resultado_pagamento = self.confirmation_handler.processar_confirmacao_pagamento_afrmm(
                                mensagem, session_id=session_id
                            )
                            logger.info(f'🔍 [STREAM] Resultado da confirmação: sucesso={resultado_pagamento.get("sucesso") if resultado_pagamento else None}, erro={resultado_pagamento.get("erro") if resultado_pagamento else None}, resposta={resultado_pagamento.get("resposta")[:100] if resultado_pagamento and resultado_pagamento.get("resposta") else None}')
                            
                            # ✅ CRÍTICO: Retornar resultado mesmo se sucesso=False (para mostrar erro ao usuário)
                            if resultado_pagamento:
                                # Retornar resultado como chunk final
                                resposta_final = resultado_pagamento.get('resposta', 'Pagamento AFRMM executado')
                                yield {
                                    'chunk': resposta_final,
                                    'done': True,
                                    'tool_calls': None,
                                    'resposta_final': resposta_final,
                                    'sucesso': resultado_pagamento.get('sucesso', True),
                                    'erro': resultado_pagamento.get('erro'),
                                }
                                logger.info(f'✅✅✅ [STREAM] Retornando resultado de confirmação de pagamento AFRMM (sem chamar IA) - sucesso={resultado_pagamento.get("sucesso")}')
                                return  # Retornar imediatamente sem chamar IA
                            else:
                                logger.warning(f'⚠️ [STREAM] processar_confirmacao_pagamento_afrmm retornou None - continuando processamento normal')
                    else:
                        logger.debug(f'🔍 [STREAM] Nenhum pending intent de pagamento encontrado para session_id={session_id}')
            except Exception as e:
                # ✅ CRÍTICO: Se a confirmação falhar, NÃO continuar para IA (evita loop + tool call sem confirmar_pagamento)
                logger.error(f'❌ [STREAM] Erro ao processar confirmação de pagamento AFRMM: {e}', exc_info=True)
                resposta_final = (
                    "❌ Erro ao processar a confirmação do pagamento AFRMM.\n\n"
                    "💡 Tente novamente em instantes. Se persistir, gere o preview de novo."
                )
                yield {
                    'chunk': resposta_final,
                    'done': True,
                    'tool_calls': None,
                    'resposta_final': resposta_final,
                    'sucesso': False,
                    'erro': 'ERRO_CONFIRMACAO_PAGAMENTO_AFRMM',
                }
                return
        
        # ✅ CRÍTICO: Verificar confirmação de DUIMP DEPOIS de pagamento AFRMM (igual ao método normal)
        resultado_duimp_stream = self._processar_confirmacao_duimp_estado_pendente_stream(
            mensagem=mensagem,
            session_id=session_id,
        )
        if resultado_duimp_stream:
            yield resultado_duimp_stream
            return

        # ✅ PRECHECK (STREAM) - ETA de processo específico:
        # O frontend usa /api/chat/stream; precisamos do mesmo comportamento determinístico do método normal.
        # Se detectar processo + intenção "quando chega/ETA/previsão", responder via listar_processos_por_eta(processo_referencia=...)
        # antes de chamar a IA, evitando rodapé "Conhecimento do Modelo" e garantindo consistência com o relatório de chegadas.
        try:
            mensagem_lower = (mensagem or "").lower()
            processo_ref = self._extrair_processo_referencia(mensagem)
            if processo_ref and (
                re.search(r"\b(quando|qdo)\b.*\bcheg", mensagem_lower)
                or re.search(r"\beta\b|\bprevis[aã]o\b|\bprevisao\b", mensagem_lower)
            ):
                logger.warning(
                    f"🚨 [STREAM] PRECHECK ETA PROCESSO: {processo_ref} detectado. "
                    "Chamando listar_processos_por_eta(processo_referencia=...) e retornando (SEM IA)."
                )
                resultado_eta = self._executar_funcao_tool(
                    "listar_processos_por_eta",
                    {"processo_referencia": processo_ref, "limite": 1},
                    mensagem_original=mensagem,
                    session_id=session_id,
                )
                resposta_eta = (
                    (resultado_eta or {}).get("resposta")
                    or (resultado_eta or {}).get("mensagem")
                    or ""
                )
                yield {
                    "chunk": resposta_eta,
                    "done": True,
                    "tool_calls": None,
                    "resposta_final": resposta_eta,
                }
                return
        except Exception as e:
            logger.debug(f"⚠️ [STREAM] Falha no precheck ETA processo: {e}")

        # ✅ Seleção automática de modelo (reutiliza helper do método normal)
        model = self._selecionar_modelo_automatico(mensagem, model)

        # ✅ Precheck centralizado (executa tool_calls do precheck quando houver)
        resposta_base_precheck_stream = None
        deve_chamar_ia_para_refinar_stream = False
        try:
            if not hasattr(self, "precheck_service") or self.precheck_service is None:
                from services.precheck_service import PrecheckService
                self.precheck_service = PrecheckService(self)

            resultado_precheck_imediato, resposta_base_precheck_stream, deve_chamar_ia_para_refinar_stream = (
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
                resposta_precheck = (
                    resultado_precheck_imediato.get('resposta')
                    or resultado_precheck_imediato.get('mensagem')
                    or ''
                )
                yield {
                    'chunk': resposta_precheck,
                    'done': True,
                    'tool_calls': resultado_precheck_imediato.get('tool_calls') or resultado_precheck_imediato.get('tool_calling'),
                    'resposta_final': resposta_precheck,
                    '_resultado_interno': resultado_precheck_imediato.get('_resultado_interno'),
                }
                return
        except Exception as e:
            logger.error(f"[PRECHECK] Erro no precheck centralizado (stream): {e}", exc_info=True)

        # ✅ Alinhar com o fluxo do método normal: resolver contexto/ação antes do prompt
        resultado_ctx, ctx = self._resolver_contexto_processo_categoria_e_acao_antes_prompt(
            mensagem=mensagem,
            historico=historico,
            session_id=session_id,
        )
        if resultado_ctx:
            # Early-return no streaming: enviar resposta completa e encerrar
            resposta_ctx = resultado_ctx.get('resposta', '') if isinstance(resultado_ctx, dict) else str(resultado_ctx)
            yield {
                'chunk': resposta_ctx,
                'done': True,
                'tool_calls': None,
                'resposta_final': resposta_ctx,
            }
            return

        processo_ref_stream = ctx.get('processo_ref')
        categoria_atual_stream = ctx.get('categoria_atual')
        categoria_contexto_stream = ctx.get('categoria_contexto')
        numero_ce_contexto_stream = ctx.get('numero_ce_contexto')
        numero_cct_stream = ctx.get('numero_cct')
        contexto_processo_stream = ctx.get('contexto_processo')
        acao_info_stream = ctx.get('acao_info', {})
        eh_pergunta_generica_stream = ctx.get('eh_pergunta_generica', False)
        eh_pergunta_pendencias_stream = ctx.get('eh_pergunta_pendencias', False)
        eh_pergunta_situacao_stream = ctx.get('eh_pergunta_situacao', False)
        precisa_contexto_stream = ctx.get('precisa_contexto', False)
        eh_fechamento_dia_stream = ctx.get('eh_fechamento_dia', False)

        # ✅ Construção de prompt (helper): MPS preferencial + fallback PromptBuilder
        try:
            system_prompt, user_prompt, usar_tool_calling = self._construir_prompts_stream(
                mensagem=mensagem,
                historico=historico,
                session_id=session_id,
                nome_usuario=nome_usuario,
                usar_tool_calling=usar_tool_calling,
                processo_ref=processo_ref_stream,
                categoria_atual=categoria_atual_stream,
                categoria_contexto=categoria_contexto_stream,
                numero_ce_contexto=numero_ce_contexto_stream,
                numero_cct=numero_cct_stream,
                contexto_processo=contexto_processo_stream,
                acao_info=acao_info_stream,
                eh_pedido_melhorar_email=eh_pedido_melhorar_email,
                eh_pergunta_generica=eh_pergunta_generica_stream,
                eh_pergunta_pendencias=eh_pergunta_pendencias_stream,
                eh_pergunta_situacao=eh_pergunta_situacao_stream,
                precisa_contexto=precisa_contexto_stream,
                eh_fechamento_dia=eh_fechamento_dia_stream,
                resposta_base_precheck=resposta_base_precheck_stream,
                deve_chamar_ia_para_refinar=deve_chamar_ia_para_refinar_stream,
            )
        except Exception as e:
            logger.error(f"Erro ao construir prompts: {e}", exc_info=True)
            yield {
                'chunk': 'Erro ao processar mensagem.',
                'done': True,
                'tool_calls': None,
                'resposta_final': 'Erro ao processar mensagem.'
            }
            return

        # ✅ Chamar IA com streaming
        tools = None
        if usar_tool_calling:
            from services.tool_definitions import get_available_tools
            tools = get_available_tools(compact=True)

        tool_calls_accumulated = []
        # Conteúdo bruto (como veio do stream do modelo). Usado para tool-calls e para o "final".
        full_content = ""
        # Conteúdo já enviado ao frontend (sanitizado). Mantemos separado para evitar "flash" de frases removidas.
        sent_clean = ""
        # ✅ Estratégia anti-flash: segurar uma cauda para evitar enviar trechos que podem ser removidos logo depois.
        HOLD_BACK_CHARS = 80

        try:
            # ✅ STREAMING: Iterar sobre chunks da resposta
            for chunk_data in self.ai_service._call_llm_api_stream(
                user_prompt, system_prompt, tools=tools, model=model, temperature=temperature
            ):
                chunk = chunk_data.get('chunk', '')
                done = chunk_data.get('done', False)
                tool_calls = chunk_data.get('tool_calls')
                error = chunk_data.get('error')

                if error:
                    logger.error(f"Erro no streaming: {error}")
                    yield {
                        'chunk': f'\n\n❌ Erro: {error}',
                        'done': True,
                        'tool_calls': None,
                        'resposta_final': full_content + f'\n\n❌ Erro: {error}'
                    }
                    return

                if chunk:
                    full_content += chunk
                    # ✅ Sanitização DURANTE o streaming:
                    # - aplica limpeza no acumulado
                    # - envia apenas o delta já limpo
                    # - segura uma "cauda" para evitar flash quando a limpeza remove frases no final
                    try:
                        # Manter o mesmo comportamento do final: NÃO limpar se for preview de email
                        texto_para_exibir = full_content
                        if not (texto_para_exibir and texto_para_exibir.startswith('📧 **Preview do Email')):
                            texto_para_exibir = self._limpar_frases_problematicas(texto_para_exibir)

                        safe_len = max(0, len(texto_para_exibir) - HOLD_BACK_CHARS)
                        if safe_len > len(sent_clean):
                            delta = texto_para_exibir[len(sent_clean):safe_len]
                            sent_clean = texto_para_exibir[:safe_len]

                            # ✅ Log para debug: verificar se chunks estão sendo enviados incrementalmente
                            logger.debug(f"📦 [STREAM] Enviando chunk limpo ({len(delta)} chars): '{delta[:50]}...'")
                            yield {
                                'chunk': delta,
                                'done': False,
                                'tool_calls': None
                            }
                    except Exception as e:
                        # Se algo der errado na sanitização incremental, não quebra o streaming.
                        logger.debug(f"⚠️ [STREAM] Falha ao sanitizar chunk incrementalmente: {e}")
                        logger.debug(f"📦 [STREAM] Enviando chunk bruto ({len(chunk)} chars): '{chunk[:50]}...'")
                        yield {
                            'chunk': chunk,
                            'done': False,
                            'tool_calls': None
                        }

                if tool_calls:
                    tool_calls_accumulated = tool_calls

                if done:
                    # ✅ Se tem tool calls, executar e depois continuar streaming
                    if tool_calls_accumulated:
                        logger.info(f'✅ Tool calls detectados no streaming: {len(tool_calls_accumulated)} chamada(s)')

                        yield self._executar_tool_calls_stream(
                            tool_calls=tool_calls_accumulated,
                            mensagem_original=mensagem,
                            session_id=session_id,
                            resposta_ia_texto=full_content,
                        )
                    else:
                        yield self._finalizar_stream_sem_toolcalls(
                            mensagem=mensagem,
                            full_content=full_content,
                            eh_pedido_melhorar_email=eh_pedido_melhorar_email,
                            ultima_resposta_aguardando_email=ultima_resposta_aguardando_email,
                            dados_email_para_enviar=dados_email_para_enviar,
                            session_id=session_id,
                        )
                    return

        except Exception as e:
            logger.error(f"Erro no streaming: {e}", exc_info=True)
            yield {
                'chunk': f'\n\n❌ Erro ao processar: {str(e)}',
                'done': True,
                'tool_calls': None,
                'resposta_final': full_content + f'\n\n❌ Erro: {str(e)}'
            }

    def _limpar_frases_problematicas(self, texto: str) -> str:
        """
        Remove frases problemáticas que a IA insiste em adicionar.
        
        ✅ REFATORADO (10/01/2026): Delegado para EmailUtils.
        Mantido como método de instância para compatibilidade com código existente.
        """
        from services.utils.email_utils import EmailUtils
        return EmailUtils.limpar_frases_problematicas(texto)

    def _construir_prompts_stream(
        self,
        *,
        mensagem: str,
        historico: List[Dict],
        session_id: Optional[str],
        nome_usuario: Optional[str],
        usar_tool_calling: bool,
        processo_ref: Optional[str],
        categoria_atual: Optional[str],
        categoria_contexto: Optional[str],
        numero_ce_contexto: Optional[str],
        numero_cct: Optional[str],
        contexto_processo: Optional[Dict],
        acao_info: Optional[Dict],
        eh_pedido_melhorar_email: bool,
        eh_pergunta_generica: bool,
        eh_pergunta_pendencias: bool,
        eh_pergunta_situacao: bool,
        precisa_contexto: bool,
        eh_fechamento_dia: bool,
        resposta_base_precheck: Optional[str],
        deve_chamar_ia_para_refinar: bool,
    ) -> tuple[str, str, bool]:
        """
        Constrói system_prompt/user_prompt para o modo streaming.

        Preferência: `MessageProcessingService` (mesma lógica do modo normal).
        Fallback: `PromptBuilder` com user_prompt simplificado.
        """
        system_prompt = ""
        user_prompt = ""
        acao_info = acao_info or {}

        prompt_construido_via_mps = False

        mps = getattr(self, "message_processing_service", None)
        if mps:
            try:
                email_para_melhorar_contexto = (
                    getattr(self, '_email_para_melhorar_contexto', None)
                    if eh_pedido_melhorar_email else None
                )

                prompt_result = mps.construir_prompt_completo(
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
                    resposta_base_precheck=resposta_base_precheck if deve_chamar_ia_para_refinar else None,
                    eh_pedido_melhorar_email=eh_pedido_melhorar_email,
                    email_para_melhorar_contexto=email_para_melhorar_contexto,
                    eh_pergunta_generica=eh_pergunta_generica,
                    eh_pergunta_pendencias=eh_pergunta_pendencias,
                    eh_pergunta_situacao=eh_pergunta_situacao,
                    precisa_contexto=precisa_contexto,
                    eh_fechamento_dia=eh_fechamento_dia,
                    extrair_processo_referencia_fn=self._extrair_processo_referencia,
                )

                system_prompt = prompt_result.get('system_prompt', '')
                user_prompt = prompt_result.get('user_prompt', '')
                usar_tool_calling = prompt_result.get('usar_tool_calling', usar_tool_calling)
                prompt_construido_via_mps = True
                logger.info("✅ [STREAM] Prompt construído via MessageProcessingService")
            except Exception as e:
                logger.error(
                    f"❌ [STREAM] Erro ao construir prompt via MessageProcessingService: {e}",
                    exc_info=True
                )
                prompt_construido_via_mps = False

        if not prompt_construido_via_mps:
            from services.prompt_builder import PromptBuilder
            from services.learned_rules_service import buscar_regras_aprendidas
            from services.context_service import buscar_contexto_sessao

            prompt_builder = PromptBuilder()

            # Buscar regras aprendidas
            regras_aprendidas = None
            try:
                regras = buscar_regras_aprendidas()
                if regras:
                    from services.learned_rules_service import formatar_regras_para_prompt
                    regras_aprendidas = formatar_regras_para_prompt(regras)
            except Exception as e:
                logger.debug(f"Erro ao buscar regras aprendidas: {e}")

            # Buscar contexto de sessão
            contexto_sessao = None
            try:
                if session_id:
                    contextos = buscar_contexto_sessao(session_id)
                    if contextos:
                        from services.context_service import formatar_contexto_para_prompt
                        contexto_sessao = formatar_contexto_para_prompt(contextos)
            except Exception as e:
                logger.debug(f"Erro ao buscar contexto de sessão: {e}")

            saudacao_personalizada = ""
            if nome_usuario:
                saudacao_personalizada = f"\n\n👤 O nome do usuário é **{nome_usuario}** - use o nome nas respostas."

            system_prompt = prompt_builder.build_system_prompt(
                saudacao_personalizada,
                regras_aprendidas=regras_aprendidas,
            )

            # Fallback: user_prompt simplificado (mantido)
            historico_str = ''
            if historico:
                historico_str = "\n\n📜 Histórico:\n"
                for item in historico[-5:]:
                    msg = item.get('mensagem', '')[:150]
                    resp = item.get('resposta', '')[:500]
                    historico_str += f"Usuário: {msg}\nmAIke: {resp}\n\n"

            user_prompt = prompt_builder.build_user_prompt(
                mensagem=mensagem,
                contexto_str='',
                historico_str=historico_str,
                acao_info=acao_info,
                contexto_sessao=contexto_sessao,
            )

        return system_prompt, user_prompt, usar_tool_calling

    def _combinar_resultados_tools(self, resultados_tools: List[Dict], resposta_ia_texto: str = '') -> str:
        """
        Combina resultados de múltiplas tools em uma resposta final.
        
        ✅ REFATORADO (10/01/2026): Delegado para ResponseFormatter.
        Mantido como método de instância para compatibilidade com código existente.
        """
        if not hasattr(self, '_response_formatter'):
            from services.handlers.response_formatter import ResponseFormatter
            from services.utils.email_utils import EmailUtils
            self._response_formatter = ResponseFormatter(
                limpar_frases_callback=EmailUtils.limpar_frases_problematicas
            )
        
        return self._response_formatter.combinar_resultados_tools(resultados_tools, resposta_ia_texto)

    def _executar_tool_calls_stream(
        self,
        *,
        tool_calls: List[Dict[str, Any]],
        mensagem_original: str,
        session_id: Optional[str],
        resposta_ia_texto: str,
    ) -> Dict[str, Any]:
        """
        Executa tool_calls detectadas no streaming e retorna payload final para `yield`.

        Mantém o comportamento atual: executa tools via `_executar_funcao_tool` e
        combina tudo com `_combinar_resultados_tools`.
        """
        import json

        resultados_tools: List[Dict[str, Any]] = []

        for tool_call in tool_calls:
            try:
                func_name = tool_call.get('function', {}).get('name')
                func_args_str = tool_call.get('function', {}).get('arguments', '{}')
                if not func_name:
                    continue

                try:
                    func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else (func_args_str or {})
                except json.JSONDecodeError:
                    logger.warning(f'Erro ao parsear argumentos da função {func_name}: {func_args_str}')
                    continue

                resultado = self._executar_funcao_tool(
                    func_name,
                    func_args,
                    mensagem_original=mensagem_original,
                    session_id=session_id,
                )
                if resultado:
                    resultados_tools.append(resultado)
            except Exception as e:
                logger.error(f"Erro ao executar tool_call no streaming: {e}", exc_info=True)

        resposta_final = self._combinar_resultados_tools(resultados_tools, resposta_ia_texto)

        return {
            'chunk': resposta_final,
            'done': True,
            'tool_calls': tool_calls,
            'resposta_final': resposta_final,
        }

    def _finalizar_stream_sem_toolcalls(
        self,
        *,
        mensagem: str,
        full_content: str,
        eh_pedido_melhorar_email: bool,
        ultima_resposta_aguardando_email: bool,
        dados_email_para_enviar: Optional[Dict[str, Any]],
        session_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Finaliza o streaming quando não há tool calls.

        Mantém o comportamento atual:
        - processa melhoria de email (EmailImprovementHandler/fallback)
        - limpa frases problemáticas (exceto preview de email)
        - adiciona indicador de fonte (exceto preview e respostas simples)
        - retorna payload final com `_resultado_interno` quando aplicável
        """
        resposta_final_para_processar = full_content

        # ✅ REFATORADO (09/01/2026): Usar EmailImprovementHandler para processar melhoria de email
        if eh_pedido_melhorar_email and ultima_resposta_aguardando_email and dados_email_para_enviar:
            logger.info('✅✅✅ [STREAM] [MELHORAR EMAIL] Processando resposta da IA usando EmailImprovementHandler...')

            if self.email_improvement_handler:
                try:
                    resultado = self.email_improvement_handler.processar_resposta_melhorar_email(
                        resposta_ia=resposta_final_para_processar,
                        dados_email_original=dados_email_para_enviar,
                        session_id=session_id
                        or (hasattr(self, 'session_id_atual') and self.session_id_atual)
                        or 'default',
                        ultima_resposta_aguardando_email=self.ultima_resposta_aguardando_email,
                    )

                    if resultado.get('sucesso'):
                        # Atualizar estado com dados atualizados do handler
                        self.ultima_resposta_aguardando_email = resultado.get(
                            'dados_email_atualizados',
                            dados_email_para_enviar,
                        )
                        resposta_final_para_processar = resultado.get('resposta', resposta_final_para_processar)
                        logger.info(
                            '✅✅✅ [STREAM] [MELHORAR EMAIL] Handler processou com sucesso - '
                            f'draft_id: {resultado.get("draft_id")}, revision: {resultado.get("revision")}'
                        )
                    else:
                        # Handler não conseguiu processar (extração falhou, etc.)
                        resposta_final_para_processar = resultado.get('resposta', resposta_final_para_processar)
                        logger.warning(
                            '⚠️⚠️⚠️ [STREAM] [MELHORAR EMAIL] Handler retornou sucesso=False: '
                            f'{resultado.get("erro")}'
                        )
                except Exception as e:
                    logger.error(f'❌ [STREAM] [MELHORAR EMAIL] Erro ao usar EmailImprovementHandler: {e}', exc_info=True)
                    # Fallback: manter resposta original
            else:
                logger.warning(
                    '⚠️⚠️⚠️ [STREAM] [MELHORAR EMAIL] EmailImprovementHandler não disponível - '
                    'usando método antigo como fallback'
                )
                # Fallback para método antigo se handler não estiver disponível
                try:
                    email_refinado = self._extrair_email_da_resposta_ia(
                        resposta_final_para_processar,
                        dados_email_para_enviar,
                    )
                    if email_refinado:
                        # Atualização básica (sem banco)
                        dados_email_para_enviar['assunto'] = email_refinado.get(
                            'assunto',
                            dados_email_para_enviar.get('assunto'),
                        )
                        dados_email_para_enviar['conteudo'] = email_refinado.get(
                            'conteudo',
                            dados_email_para_enviar.get('conteudo'),
                        )
                        self.ultima_resposta_aguardando_email = dados_email_para_enviar
                except Exception as e:
                    logger.error(f'❌ [STREAM] [MELHORAR EMAIL] Erro no fallback: {e}', exc_info=True)

        # ✅ CRÍTICO (09/01/2026): NÃO limpar frases problemáticas se for preview de email
        if resposta_final_para_processar and resposta_final_para_processar.startswith('📧 **Preview do Email'):
            resposta_final_limpa = resposta_final_para_processar
        else:
            resposta_antes_limpeza_stream = (
                resposta_final_para_processar[:200]
                if len(resposta_final_para_processar) > 200
                else resposta_final_para_processar
            )
            resposta_final_limpa = self._limpar_frases_problematicas(resposta_final_para_processar)
            resposta_depois_limpeza_stream = (
                resposta_final_limpa[:200]
                if len(resposta_final_limpa) > 200
                else resposta_final_limpa
            )
            if resposta_antes_limpeza_stream != resposta_depois_limpeza_stream:
                logger.info(
                    '✅ [STREAM] Frases problemáticas removidas. '
                    f'Antes: "{resposta_antes_limpeza_stream[:100]}...", '
                    f'Depois: "{resposta_depois_limpeza_stream[:100]}..."'
                )

        # ✅ NOVO: Indicador de fonte (exceto preview e respostas simples)
        eh_resposta_simples_stream = (
            resposta_final_limpa
            and (
                len(resposta_final_limpa) < 100
                or mensagem.lower().strip() in ['teste', 'enviar teste', 'oi', 'ok', 'tudo bem', 'beleza']
                or ('teste' in mensagem.lower() and len(mensagem.split()) <= 3)
            )
        )

        if (
            resposta_final_limpa
            and not resposta_final_limpa.startswith('📧 **Preview do Email')
            and not eh_resposta_simples_stream
        ):
            indicador_fonte = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            indicador_fonte += "🔍 **FONTE: Conhecimento do Modelo (GPT-4o)**\n"
            indicador_fonte += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            indicador_fonte += "💡 Esta resposta foi gerada com base no conhecimento geral do modelo GPT-4o.\n"
            indicador_fonte += "⚠️ **Nota:** Para informações específicas de legislação ou processos, use ferramentas de busca.\n"
            indicador_fonte += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            resposta_final_limpa = resposta_final_limpa + indicador_fonte

        return {
            'chunk': '',
            'done': True,
            'tool_calls': None,
            'resposta_final': resposta_final_limpa,
            '_resultado_interno': {
                'ultima_resposta_aguardando_email': self.ultima_resposta_aguardando_email
                if (eh_pedido_melhorar_email and ultima_resposta_aguardando_email and dados_email_para_enviar)
                else None
            }
            if (eh_pedido_melhorar_email and ultima_resposta_aguardando_email and dados_email_para_enviar)
            else None,
        }

