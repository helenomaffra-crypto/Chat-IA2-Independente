"""
Fallback legado de tool-calling (quando MessageProcessingService não está disponível).

Este módulo foi extraído do `services/chat_service.py` para reduzir o tamanho e a
complexidade do arquivo principal, mantendo o comportamento atual.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def executar_toolcalling_legado_sem_mps(
    *,
    chat_service: Any,
    system_prompt: str,
    user_prompt: str,
    mensagem: str,
    session_id: Optional[str],
    model: Optional[str],
    temperature: Optional[float],
    acao_info: Dict[str, Any],
    logger_override: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Executa o fluxo antigo de tool calling:
    - monta lista de tools
    - chama LLM com tools
    - executa tool calls
    - combina resultados
    - atualiza `acao_info` quando aplicável

    Returns:
        Dict com:
        - resposta_final: str
        - tool_calls: list
        - acao_info: dict (possivelmente atualizado)
    """
    log = logger_override or logger

    from services.tool_definitions import get_available_tools

    tools = get_available_tools(compact=True)
    log.info(f'🔍 Tool calling ativado - {len(tools) if tools else 0} ferramentas disponíveis (compact)')

    resposta_ia_raw = chat_service.ai_service._call_llm_api(
        user_prompt,
        system_prompt,
        tools=tools,
        model=model,
        temperature=temperature,
    )

    log.debug(
        f'🔍 Resposta da IA (tipo: {type(resposta_ia_raw).__name__}): '
        f'{str(resposta_ia_raw)[:200] if resposta_ia_raw else "None"}'
    )

    tool_calls: List[Dict[str, Any]] = []
    resultados_tools: List[Dict[str, Any]] = []
    resposta_ia_texto: str = ""
    resposta_final = ""

    if isinstance(resposta_ia_raw, dict) and 'tool_calls' in resposta_ia_raw:
        log.info(f'✅ Tool calls detectados: {len(resposta_ia_raw.get("tool_calls", []))} chamada(s)')
        tool_calls = resposta_ia_raw.get('tool_calls', []) or []
        resposta_ia_texto = resposta_ia_raw.get('content', '') or ''

        for tool_call in tool_calls:
            func_name = tool_call['function']['name']
            func_args_str = tool_call['function']['arguments']

            try:
                func_args = json.loads(func_args_str)
            except json.JSONDecodeError:
                log.warning(f'Erro ao parsear argumentos da função {func_name}: {func_args_str}')
                continue

            # ✅ CRÍTICO: Se for criar_duimp, SEMPRE forçar confirmar=False na primeira chamada
            if func_name == 'criar_duimp':
                if 'confirmar' in func_args:
                    log.warning(
                        f'⚠️ IA tentou passar confirmar={func_args.get("confirmar")} para criar_duimp. '
                        'Forçando confirmar=False para mostrar resumo primeiro.'
                    )
                    func_args['confirmar'] = False

            resultado = chat_service._executar_funcao_tool(
                func_name,
                func_args,
                mensagem_original=mensagem,
                session_id=session_id,
            )
            resultados_tools.append(resultado)

        # Combinar resultados das tools
        resposta_final = chat_service._combinar_resultados_tools(resultados_tools, resposta_ia_texto)

        # ✅ CRÍTICO: Se for criar_duimp e retornou mostrar_antes_criar, salvar estado aguardando confirmação
        for resultado_tool in resultados_tools:
            if resultado_tool.get('mostrar_antes_criar') and resultado_tool.get('acao') == 'criar_duimp':
                try:
                    processo_ref_guardado = resultado_tool.get('processo_referencia', '')
                    ambiente_guardado = resultado_tool.get('ambiente', 'validacao')
                    payload = {
                        'processo_referencia': processo_ref_guardado,
                        'ambiente': ambiente_guardado,
                        'payload_duimp': resultado_tool.get('payload_duimp'),
                    }
                    if hasattr(chat_service, "_set_duimp_pendente"):
                        chat_service._set_duimp_pendente(session_id, payload)
                    else:
                        chat_service.ultima_resposta_aguardando_duimp = payload
                    log.info(
                        f'🧭 [DUIMP] (Tool Call) Estado aguardando confirmação salvo: '
                        f'processo={processo_ref_guardado}, ambiente={ambiente_guardado}'
                    )
                except Exception as _e:
                    log.debug(f'[DUIMP] (Tool Call) Não foi possível salvar estado aguardando confirmação: {_e}')

        # Se for criar_duimp, marcar para execução no endpoint (mas NUNCA se for pergunta)
        for resultado_tool_check in resultados_tools:
            if resultado_tool_check.get('acao') == 'criar_duimp' and resultado_tool_check.get('sucesso'):
                mensagem_lower = mensagem.lower()
                eh_pergunta = any(
                    [
                        __import__('re').search(r'^(?:tem|tem\s+algum|tem\s+alguma|tem\s+alguns|tem\s+algumas)', mensagem_lower),
                        __import__('re').search(r'^(?:qual|quais|quando|onde|como|quem)', mensagem_lower),
                        __import__('re').search(r'^(?:esse|esta|este)', mensagem_lower),
                        __import__('re').search(r'pend[êe]ncia', mensagem_lower),
                        __import__('re').search(r'bloqueio', mensagem_lower),
                        __import__('re').search(r'frete', mensagem_lower),
                    ]
                )

                if not eh_pergunta:
                    acao_info['acao'] = 'criar_duimp'
                    acao_info['processo_referencia'] = resultado_tool_check.get('processo_referencia')
                    acao_info['confianca'] = 0.95
                    acao_info['executar_automatico'] = False
                else:
                    log.warning(f'⚠️ Tentativa de criar DUIMP cancelada - mensagem é uma pergunta: {mensagem}')
                    acao_info['acao'] = None
                    acao_info['executar_automatico'] = False

    return {
        'resposta_final': resposta_final,
        'tool_calls': tool_calls,
        'resultados_tools': resultados_tools,
        'resposta_ia_texto': resposta_ia_texto,
        'acao_info': acao_info,
    }

