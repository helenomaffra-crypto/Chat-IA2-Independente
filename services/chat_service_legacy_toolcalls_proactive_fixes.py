"""
Correções e detecção proativa pós tool-calls (fluxo legado, sem MPS).

Este módulo concentra o bloco grande de "ajustes" que roda após a IA retornar tool_calls
no fluxo legado, reduzindo o tamanho de `services/chat_service.py`.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def aplicar_fixes_pos_toolcalls_legacy(
    *,
    chat_service: Any,
    mensagem: str,
    tool_calls: List[Dict[str, Any]],
    resultados_tools: List[Dict[str, Any]],
    acao_info: Dict[str, Any],
    categoria_atual: Optional[str],
    logger_override: Optional[logging.Logger] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """
    Aplica correções proativas no fluxo legado após tool_calls.

    Retorna:
      (tool_calls, resultados_tools, acao_info) atualizados.
    """
    log = logger_override or logger
    import re

    # ✅✅✅ PRIORIDADE MÁXIMA: Interceptar se IA chamou listar_processos_por_situacao com 'registrado' mas mensagem é comando de criar DUIMP
    mensagem_lower = mensagem.lower()
    # ✅ CORREÇÃO: Aceitar "registrar duimp do", "criar duimp do", etc.
    eh_comando_criar_duimp_pos = bool(
        re.search(r'registr[ae]r?\s+(?:a\s+)?(?:duimp|o\s+duimp)', mensagem_lower)
        or re.search(r'registr[ae]r?\s+duimp\s+do', mensagem_lower)  # ✅ "registrar duimp do"
        or re.search(r'cri[ae]r?\s+(?:a\s+)?duimp', mensagem_lower)
        or re.search(r'cri[ae]r?\s+duimp\s+do', mensagem_lower)  # ✅ "criar duimp do"
        or re.search(r'ger[ae]r?\s+(?:a\s+)?duimp', mensagem_lower)
        or re.search(r'ger[ae]r?\s+duimp\s+do', mensagem_lower)  # ✅ "gerar duimp do"
        or re.search(r'fazer\s+(?:a\s+)?duimp', mensagem_lower)
        or re.search(r'fazer\s+duimp\s+do', mensagem_lower)  # ✅ "fazer duimp do"
    )

    if eh_comando_criar_duimp_pos:
        # Verificar se IA chamou listar_processos_por_situacao com situacao='registrado'
        tem_listar_registrado = False
        for tc in tool_calls:
            if tc['function']['name'] == 'listar_processos_por_situacao':
                try:
                    func_args = json.loads(tc['function'].get('arguments', '{}'))
                    situacao_arg = func_args.get('situacao', '').lower()
                    if 'registrado' in situacao_arg:
                        tem_listar_registrado = True
                        break
                except (json.JSONDecodeError, AttributeError, KeyError):
                    args_str = str(tc['function'].get('arguments', ''))
                    if 'registrado' in args_str.lower():
                        tem_listar_registrado = True
                        break

        if tem_listar_registrado:
            log.warning(
                '🚨🚨🚨 CORREÇÃO PÓS-RESPOSTA: IA chamou listar_processos_por_situacao(registrado) '
                'mas mensagem é comando de criar DUIMP. Forçando criar_duimp...'
            )
            processo_duimp_correcao = chat_service._extrair_processo_referencia(mensagem)
            if processo_duimp_correcao:
                try:
                    resultado_correcao = chat_service._executar_funcao_tool(
                        'criar_duimp',
                        {
                            'processo_referencia': processo_duimp_correcao,
                            'ambiente': 'validacao',
                            'confirmar': False,  # ✅ SEMPRE mostrar resumo primeiro
                        },
                        mensagem_original=mensagem,
                    )

                    if resultado_correcao and resultado_correcao.get('resposta'):
                        log.info(f'✅✅✅ Correção aplicada - DUIMP será criada para {processo_duimp_correcao}')
                        resultados_tools = [resultado_correcao]
                        tool_calls = []
                        acao_info['acao'] = 'criar_duimp'
                        acao_info['processo_referencia'] = processo_duimp_correcao
                        acao_info['confianca'] = 0.95
                        acao_info['executar_automatico'] = False
                except Exception as e:
                    log.error(f'❌ Erro ao corrigir chamada de criar_duimp: {e}', exc_info=True)

    # ✅ DETECÇÃO PROATIVA: Verificar se IA deveria ter chamado listar_processos_por_categoria, listar_processos_com_pendencias ou listar_processos_por_situacao
    # mesmo quando há tool_calls (pode ter chamado outra função incorreta)

    # ✅ PRIORIDADE MÁXIMA: Detectar perguntas sobre NCM de produtos (ANTES de consultas pendentes)
    eh_pergunta_ncm_produto = bool(
        re.search(
            r'(?:qual|quais)\s+(?:o|os|a|as)?\s*ncm\s+(?:do|da|de|para|d[eo]?\s+produto?|de\s+)?|ncm\s+(?:do|da|de|para)|^ncm\s+[a-z0-9]|^qual\s+(?:a|o)\s+ncm',
            mensagem_lower,
        )
    ) and not bool(re.search(r'processo|processos|categoria|ALH|VDM|MSS|BND|DMD|GYM|SLL', mensagem_lower))

    produto_detectado = None
    if eh_pergunta_ncm_produto:
        match_produto = (
            re.search(
                r'(?:qual|quais)\s+(?:o|os|a|as)?\s*ncm\s+(?:do|da|de|para|d[eo]?\s+produto?|de\s+)?\s*([^?\.]+)',
                mensagem_lower,
            )
            or re.search(r'ncm\s+(?:do|da|de|para|d[eo]?\s+produto?)\s+([^?\.]+)', mensagem_lower)
            or re.search(r'^ncm\s+([a-z0-9]+(?:\s+[a-z0-9]+)*)', mensagem_lower)
            or re.search(r'^qual\s+(?:a|o)\s+ncm\s+(?:para|de|do|da)\s+([^?\.]+)', mensagem_lower)
        )
        if match_produto:
            produto_detectado = match_produto.group(1).strip()
            produto_detectado = re.sub(r'^[^\w]+|[^\w]+$', '', produto_detectado)
            if not produto_detectado or len(produto_detectado) < 2:
                match_simples = re.search(r'^ncm\s+(.+)', mensagem_lower)
                if match_simples:
                    produto_detectado = match_simples.group(1).strip()
                    produto_detectado = re.sub(r'[?\.]+$', '', produto_detectado)

    tem_sugerir_ncm = any(tc['function']['name'] == 'sugerir_ncm_com_ia' for tc in tool_calls) if tool_calls else False
    tem_buscar_ncm = any(tc['function']['name'] == 'buscar_ncms_por_descricao' for tc in tool_calls) if tool_calls else False

    if eh_pergunta_ncm_produto and produto_detectado:
        if not tem_sugerir_ncm:
            log.warning(
                f'🔍🔍🔍 PRIORIDADE MÁXIMA: Pergunta sobre NCM de produto "{produto_detectado}" detectada. '
                'Forçando sugerir_ncm_com_ia (substituindo buscar_ncms_por_descricao se necessário)...'
            )
            try:
                resultado_forcado = chat_service._executar_funcao_tool(
                    'sugerir_ncm_com_ia',
                    {'descricao': produto_detectado, 'usar_cache': True, 'validar_sugestao': True},
                    mensagem_original=mensagem,
                )
                if resultado_forcado.get('resposta') or resultado_forcado.get('mensagem'):
                    resultado_forcado['_forcado'] = True
                    resultados_tools.insert(0, resultado_forcado)
                    resultados_tools = [
                        r
                        for r in resultados_tools
                        if r.get('_forcado') is True
                        or not (
                            'buscar_ncms_por_descricao' in str(r.get('nome_funcao', ''))
                            or 'Nenhum NCM encontrado' in str(r.get('resposta', ''))
                            or 'NCMs encontrados para' in str(r.get('resposta', ''))
                        )
                    ]
                    log.info(f'✅✅✅ Resposta da função sugerir_ncm_com_ia forçada (PRIORIDADE MÁXIMA) - produto: {produto_detectado}')
            except Exception as e:
                log.error(f'❌ Erro ao forçar chamada de sugerir_ncm_com_ia: {e}', exc_info=True)

    # ✅⚠️⚠️⚠️ VALIDAÇÃO CRÍTICA: Detectar quando IA chama função errada para "pronto para registro"
    eh_pergunta_pronto_registro = bool(
        re.search(
            r'pronto[s]?\s+(?:para|pra)\s+registro|precisam\s+de\s+registro|precisam\s+registrar|precisam\s+de\s+di|precisam\s+de\s+duimp|chegaram\s+sem\s+despacho|est[ao]\s+pronto[s]?\s+(?:para|pra)\s+registro|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+(?:pra|para|de)\s+registrar|temos\s+(?:pra|para|de)\s+registrar|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+pra\s+registro|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+para\s+registro',
            mensagem_lower,
        )
    )
    tem_listar_liberados = any(tc['function']['name'] == 'listar_processos_liberados_registro' for tc in tool_calls) if tool_calls else False
    tem_listar_situacao_registrado = (
        any(
            tc['function']['name'] == 'listar_processos_por_situacao'
            and 'registrado' in str(tc.get('function', {}).get('arguments', '')).lower()
            for tc in tool_calls
        )
        if tool_calls
        else False
    )
    tem_criar_duimp_call = any(tc['function']['name'] == 'criar_duimp' for tc in tool_calls) if tool_calls else False

    if eh_pergunta_pronto_registro and (tem_listar_situacao_registrado or tem_criar_duimp_call) and not tem_listar_liberados:
        log.warning(
            f'🚨🚨🚨 ERRO DETECTADO: IA chamou função ERRADA para "pronto para registro" '
            f'(chamou {"criar_duimp" if tem_criar_duimp_call else "listar_processos_por_situacao"}). Corrigindo...'
        )
        categoria_corrigir = categoria_atual
        try:
            resultado_corrigido = chat_service._executar_funcao_tool(
                'listar_processos_liberados_registro',
                {
                    'categoria': categoria_corrigir.upper() if categoria_corrigir else None,
                    'dias_retroativos': 30,
                    'limit': 200,
                },
                mensagem_original=mensagem,
            )

            if resultado_corrigido and resultado_corrigido.get('resposta'):
                resultados_tools = [
                    r
                    for r in resultados_tools
                    if 'listar_processos_por_situacao' not in str(r.get('nome_funcao', ''))
                    and 'criar_duimp' not in str(r.get('nome_funcao', ''))
                ]
                resultados_tools.insert(0, resultado_corrigido)
                log.info(
                    f'✅✅✅ Função corrigida: listar_processos_liberados_registro chamada no lugar de '
                    f'{"criar_duimp" if tem_criar_duimp_call else "listar_processos_por_situacao"}'
                )
        except Exception as e:
            log.error(f'Erro ao corrigir função para "pronto para registro": {e}', exc_info=True)

    # ✅ PRIORIDADE MÁXIMA: Detectar processo específico na mensagem e forçar consultar_status_processo
    processo_ref_detectado = chat_service._extrair_processo_referencia(mensagem)
    tem_consultar_status_processo = any(tc['function']['name'] == 'consultar_status_processo' for tc in tool_calls) if tool_calls else False
    eh_pergunta_generica_sem_processo = bool(
        re.search(r'quais\s+processos|quais\s+os\s+processos|quais\s+as\s+processos|processos\s+que|processos\s+com', mensagem_lower)
        and not processo_ref_detectado
    )
    tem_criar_duimp = any(tc['function']['name'] == 'criar_duimp' for tc in tool_calls) if tool_calls else False
    mensagem_lower_check = mensagem.lower()
    intencao_criar_duimp = bool(
        re.search(r'cri[ae]r?\s+duimp|cri[ae]r?\s+a\s+duimp|registr[ae]r?\s+duimp|ger[ae]r?\s+duimp', mensagem_lower_check)
    )

    if (
        processo_ref_detectado
        and not tem_consultar_status_processo
        and not eh_pergunta_generica_sem_processo
        and not tem_criar_duimp
        and not intencao_criar_duimp
    ):
        log.warning(
            f'⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Processo específico {processo_ref_detectado} detectado mas IA não chamou consultar_status_processo. Forçando chamada...'
        )
        try:
            resultado_forcado = chat_service._executar_funcao_tool(
                'consultar_status_processo',
                {'processo_referencia': processo_ref_detectado},
                mensagem_original=mensagem,
            )
            if resultado_forcado.get('resposta'):
                resultado_forcado['_forcado'] = True
                resultados_tools.insert(0, resultado_forcado)
                log.info(f'✅✅✅ Resposta da função consultar_status_processo forçada (PRIORIDADE MÁXIMA) - processo: {processo_ref_detectado}')
            elif resultado_forcado.get('mensagem'):
                resultado_forcado['_forcado'] = True
                resultados_tools.insert(0, resultado_forcado)
                log.info(f'✅✅✅ Mensagem da função consultar_status_processo forçada (PRIORIDADE MÁXIMA) - processo: {processo_ref_detectado}')
        except Exception as e:
            log.error(f'❌ Erro ao forçar chamada de consultar_status_processo: {e}', exc_info=True)

    # ✅ NOVO: Detectar perguntas sobre consultas bilhetadas pendentes (PRIORIDADE MÁXIMA)
    eh_pergunta_consultas_pendentes = bool(re.search(r'consultas?\s+pendentes?|consultas?\s+aguardando|consultas?\s+estão|quais\s+consultas?', mensagem_lower))
    tem_listar_consultas_pendentes = any(
        tc['function']['name'] == 'listar_consultas_bilhetadas_pendentes' for tc in tool_calls
    ) if tool_calls else False

    if eh_pergunta_consultas_pendentes and not tem_listar_consultas_pendentes:
        log.warning(
            '⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Pergunta sobre consultas pendentes detectada mas IA não chamou listar_consultas_bilhetadas_pendentes. Forçando chamada...'
        )
        try:
            resultado_forcado = chat_service._executar_funcao_tool(
                'listar_consultas_bilhetadas_pendentes',
                {'status': 'pendente', 'limite': 50},
                mensagem_original=mensagem,
            )
            if resultado_forcado.get('resposta'):
                resultado_forcado['_forcado'] = True
                resultados_tools.insert(0, resultado_forcado)
                log.info('✅✅✅ Resposta da função listar_consultas_bilhetadas_pendentes forçada (PRIORIDADE MÁXIMA)')
        except Exception as e:
            log.error(f'❌ Erro ao forçar chamada de listar_consultas_bilhetadas_pendentes: {e}', exc_info=True)

    # Verificar se é pergunta sobre pendências (de processos, não consultas)
    tem_pendencia = bool(re.search(r'pend[êe]ncia|pendente', mensagem_lower)) and not eh_pergunta_consultas_pendentes

    # ✅ NOVO: Verificar se é pergunta sobre situação específica (desembaraçado, registrado, entregue, etc.)
    # ⚠️ CRÍTICO: NÃO detectar "registrado" se a pergunta contém "tem DUIMP registrada para [PROCESSO]"
    eh_pergunta_duimp_registrada = bool(re.search(r'tem\s+duimp\s+registrada\s+para|tem\s+duimp\s+para', mensagem_lower))

    situacoes_comuns = {
        'desembaraçado': 'desembaraçado',
        'desembaracado': 'desembaraçado',
        'desembaraçada': 'desembaraçado',
        'desembaracada': 'desembaraçado',
        'desembaraco': 'desembaraçado',
        # 'registrado': 'registrado',  # Removido - causa confusão com "tem DUIMP registrada"
        'registrada': 'registrado',
        'entregue': 'entregue',
        'armazenado': 'armazenado',
        'armazenada': 'armazenado',
        'manifestado': 'manifestado',
        'manifestada': 'manifestado',
    }

    situacao_detectada = None
    if not eh_pergunta_duimp_registrada:
        for palavra, situacao in situacoes_comuns.items():
            if palavra in mensagem_lower:
                if (palavra == 'registrado' or palavra == 'registrada') and (
                    'tem duimp' in mensagem_lower or 'duimp registrada' in mensagem_lower
                ):
                    continue
                situacao_detectada = situacao
                break

    # ⚠️ CRÍTICO: Verificar PRIMEIRO se há número de processo específico (formato CATEGORIA.NNNN/AA)
    padrao_processo_especifico = r'\b([a-z]{3})\.\d{4}/\d{2}\b'
    match_processo_especifico = re.search(padrao_processo_especifico, mensagem_lower)

    # ✅ PADRÃO MELHORADO para detectar categoria (flexível)
    padrao_categoria_pergunta = r'(?:como|quais|mostre|liste|como\s+estao|como\s+estão)\s+([a-z]{3})\b.*?(?:processos|processo|estao|estão|com\s+)|(?:como|quais|mostre|liste|como\s+estao|como\s+estão).*(?:processos|processo)\s+([a-z]{3})\b|(?:^|\s)([a-z]{3})\b.*?(?:processos|processo)'
    match_categoria = re.search(padrao_categoria_pergunta, mensagem_lower) if not match_processo_especifico else None

    # ✅ VALIDAÇÃO FLEXÍVEL: Aceitar qualquer categoria de 3 letras, apenas rejeitar palavras comuns
    if match_categoria:
        cat_candidata = (match_categoria.group(1) or match_categoria.group(2) or match_categoria.group(3) or '').strip().lower()
        palavras_ignorar = {
            'dos', 'das', 'estao', 'estão', 'com', 'são', 'sao', 'tem', 'têm', 'por', 'que', 'qual', 'como', 'est', 'par', 'uma',
            'uns', 'todos', 'todas', 'todo', 'toda',
            'vem', 'vêm', 'semana', 'proxima', 'próxima', 'mes', 'mês', 'dia', 'dias', 'hoje', 'amanha', 'amanhã',
            'essa', 'esta', 'nessa', 'nesta',
            'vao', 'vão', 'irão', 'irao', 'chegam', 'chega', 'chegar', 'chegara', 'chegaram',
            'ncm',
        }
        if cat_candidata in palavras_ignorar:
            match_categoria = None
        elif cat_candidata in ('essa', 'esta', 'nessa', 'nesta'):
            pos_match = match_categoria.end()
            texto_apos = mensagem_lower[pos_match:pos_match + 10]
            if 'semana' in texto_apos:
                match_categoria = None
        elif len(cat_candidata) == 3:
            if not re.search(rf'\b{re.escape(cat_candidata)}\b', mensagem_lower.replace('processos', ' ').replace('processo', ' ')):
                match_categoria = None
        else:
            match_categoria = None

    # ✅ NOVO: Detectar perguntas sobre valores (frete, seguro, FOB, CIF)
    valores_keywords = {
        'frete': 'frete',
        'seguro': 'seguro',
        'fob': 'fob',
        'cif': 'cif',
        'valor': 'todos',
        'valores': 'todos',
        'quanto': 'todos',
        'moeda': 'todos',
    }

    valor_detectado = None
    for keyword, tipo in valores_keywords.items():
        if keyword in mensagem_lower:
            valor_detectado = tipo
            break

    padrao_processo = r'([A-Z]{3}\.\d{4}/\d{2})'
    match_processo_valor = re.search(padrao_processo, mensagem, re.IGNORECASE)
    processo_valor = match_processo_valor.group(1).upper() if match_processo_valor else None

    padrao_ce_valor = r'CE\s+(\d{10,15})'
    match_ce_valor = re.search(padrao_ce_valor, mensagem, re.IGNORECASE)
    ce_valor = match_ce_valor.group(1) if match_ce_valor else None

    tem_listar_categoria = any(tc['function']['name'] == 'listar_processos_por_categoria' for tc in tool_calls) if tool_calls else False
    tem_listar_pendencias = any(tc['function']['name'] == 'listar_processos_com_pendencias' for tc in tool_calls) if tool_calls else False
    tem_listar_situacao = any(tc['function']['name'] == 'listar_processos_por_situacao' for tc in tool_calls) if tool_calls else False
    tem_listar_todos_situacao_call = any(tc['function']['name'] == 'listar_todos_processos_por_situacao' for tc in tool_calls) if tool_calls else False
    tem_obter_valores_processo = any(tc['function']['name'] == 'obter_valores_processo' for tc in tool_calls) if tool_calls else False
    tem_obter_valores_ce = any(tc['function']['name'] == 'obter_valores_ce' for tc in tool_calls) if tool_calls else False

    # ✅ PRIORIDADE MÁXIMA (ANTES DE TUDO): Valores de processo/CE específico
    if valor_detectado and (processo_valor or ce_valor) and not tem_obter_valores_processo and not tem_obter_valores_ce:
        if processo_valor:
            log.warning(f'💰💰💰 PRIORIDADE MÁXIMA: Valores do processo {processo_valor} detectado mas IA não chamou obter_valores_processo. Forçando chamada...')
            try:
                resultado_forcado = chat_service._executar_funcao_tool(
                    'obter_valores_processo',
                    {'processo_referencia': processo_valor, 'tipo_valor': valor_detectado},
                    mensagem_original=mensagem,
                )
                if resultado_forcado.get('resposta'):
                    resultado_forcado['_forcado'] = True
                    resultados_tools.insert(0, resultado_forcado)
                    resultados_tools = [
                        r for r in resultados_tools if not (r.get('_forcado') is False and 'listar_processos_por_categoria' in str(r))
                    ]
                    log.info(f'✅✅✅ Resposta da função obter_valores_processo forçada para processo {processo_valor} (PRIORIDADE MÁXIMA)')
            except Exception as e:
                log.error(f'❌ Erro ao forçar chamada de obter_valores_processo para processo {processo_valor}: {e}', exc_info=True)
        elif ce_valor:
            log.warning(f'💰💰💰 PRIORIDADE MÁXIMA: Valores do CE {ce_valor} detectado mas IA não chamou obter_valores_ce. Forçando chamada...')
            try:
                resultado_forcado = chat_service._executar_funcao_tool(
                    'obter_valores_ce',
                    {'numero_ce': ce_valor, 'tipo_valor': valor_detectado},
                    mensagem_original=mensagem,
                )
                if resultado_forcado.get('resposta'):
                    resultado_forcado['_forcado'] = True
                    resultados_tools.insert(0, resultado_forcado)
                    log.info(f'✅✅✅ Resposta da função obter_valores_ce forçada para CE {ce_valor} (PRIORIDADE MÁXIMA)')
            except Exception as e:
                log.error(f'❌ Erro ao forçar chamada de obter_valores_ce para CE {ce_valor}: {e}', exc_info=True)

    # ✅ CORREÇÃO: Prioridade correta - número de processo específico tem prioridade sobre categoria
    categoria_detectada_regex = None
    if match_categoria:
        categoria_detectada_regex = (match_categoria.group(1) or match_categoria.group(2) or match_categoria.group(3) or '').strip().upper()
    categoria_detectada_funcao = chat_service._extrair_categoria_da_mensagem(mensagem)
    categoria_detectada = categoria_detectada_funcao or categoria_detectada_regex

    situacao_detectada_tool_calls = None
    if re.search(r'\b(?:desembarac|desembaraç|di_desembaracada)', mensagem_lower):
        situacao_detectada_tool_calls = 'di_desembaracada'
    elif re.search(r'\b(?:registrad|registr)\w*\b', mensagem_lower):
        situacao_detectada_tool_calls = 'registrado'
    elif re.search(r'\b(?:entregu|entreg)\w*\b', mensagem_lower):
        situacao_detectada_tool_calls = 'entregue'
    elif re.search(r'\b(?:armazenad|armazen)\w*\b', mensagem_lower):
        situacao_detectada_tool_calls = 'armazenado'

    if categoria_detectada and situacao_detectada_tool_calls and not match_processo_especifico:
        eh_pergunta_quando_chegaram = bool(re.search(r'quando\s+(?:chegaram|chegou|chegara)', mensagem_lower))
        eh_pergunta_quando_chegam = bool(re.search(r'quando\s+(?:chegam|chega)', mensagem_lower))
        if not (eh_pergunta_quando_chegaram or eh_pergunta_quando_chegam):
            log.warning(
                f'⚠️⚠️⚠️ PRIORIDADE MÁXIMA (TOOL_CALLS): Categoria {categoria_detectada} + situação "{situacao_detectada_tool_calls}" detectada '
                'mas IA não chamou listar_processos_por_situacao. Forçando chamada...'
            )
            try:
                resultado_forcado = chat_service._executar_funcao_tool(
                    'listar_processos_por_situacao',
                    {'categoria': categoria_detectada, 'situacao': situacao_detectada_tool_calls, 'limite': 200},
                    mensagem_original=mensagem,
                )
                log.info(
                    f'🔍 Resultado da função forçada: sucesso={resultado_forcado.get("sucesso")}, '
                    f'tem_resposta={bool(resultado_forcado.get("resposta"))}, '
                    f'tem_mensagem={bool(resultado_forcado.get("mensagem"))}, '
                    f'tamanho_resposta={len(resultado_forcado.get("resposta", ""))}'
                )
                if resultado_forcado.get('resposta'):
                    resultado_forcado['_forcado'] = True
                    resultados_tools.insert(0, resultado_forcado)
                    log.info(
                        f'✅✅✅ Resposta da função forçada adicionada para categoria {categoria_detectada} + situação "{situacao_detectada_tool_calls}" '
                        f'(PRIORIDADE MÁXIMA, tamanho: {len(resultado_forcado.get("resposta", ""))})'
                    )
                elif resultado_forcado.get('mensagem'):
                    resultado_forcado['_forcado'] = True
                    resultados_tools.insert(0, resultado_forcado)
                    log.info(
                        f'✅✅✅ Mensagem da função forçada adicionada para categoria {categoria_detectada} + situação "{situacao_detectada_tool_calls}" (PRIORIDADE MÁXIMA)'
                    )
                else:
                    log.warning(f'⚠️ Função forçada não retornou resposta nem mensagem. resultado_forcado={resultado_forcado}')
            except Exception as e:
                log.error(f'❌ Erro ao forçar chamada da função para categoria {categoria_detectada} com situação "{situacao_detectada_tool_calls}": {e}', exc_info=True)

    elif match_categoria and not match_processo_especifico:
        if categoria_detectada and len(categoria_detectada) == 3:
            if tem_pendencia and not tem_listar_pendencias:
                log.warning(f'⚠️ Categoria {categoria_detectada} com pendências detectada mas IA não chamou listar_processos_com_pendencias. Forçando chamada...')
                try:
                    resultado_forcado = chat_service._executar_funcao_tool(
                        'listar_processos_com_pendencias',
                        {'categoria': categoria_detectada, 'limite': 200},
                        mensagem_original=mensagem,
                    )
                    if resultado_forcado.get('resposta'):
                        resultado_forcado['_forcado'] = True
                        resultados_tools.insert(0, resultado_forcado)
                        log.info(f'✅ Resposta da função forçada adicionada para categoria {categoria_detectada} com pendências (marcada como prioridade)')
                except Exception as e:
                    log.error(f'❌ Erro ao forçar chamada da função para categoria {categoria_detectada} com pendências: {e}', exc_info=True)

            if categoria_detectada and situacao_detectada and not tem_listar_situacao and not tem_pendencia:
                eh_pergunta_quando_chegaram = bool(re.search(r'quando\s+(?:chegaram|chegou|chegara)', mensagem_lower))
                eh_pergunta_quando_chegam = bool(re.search(r'quando\s+(?:chegam|chega)', mensagem_lower))
                if not (eh_pergunta_quando_chegaram or eh_pergunta_quando_chegam):
                    log.warning(f'⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Categoria {categoria_detectada} + situação "{situacao_detectada}" detectada mas IA não chamou listar_processos_por_situacao. Forçando chamada...')
                try:
                    resultado_forcado = chat_service._executar_funcao_tool(
                        'listar_processos_por_situacao',
                        {'categoria': categoria_detectada, 'situacao': situacao_detectada, 'limite': 200},
                        mensagem_original=mensagem,
                    )
                    if resultado_forcado.get('resposta'):
                        resultado_forcado['_forcado'] = True
                        resultados_tools.insert(0, resultado_forcado)
                        log.info(f'✅✅✅ Resposta da função forçada adicionada para categoria {categoria_detectada} com situação "{situacao_detectada}" (PRIORIDADE MÁXIMA)')
                except Exception as e:
                    log.error(f'❌ Erro ao forçar chamada da função para categoria {categoria_detectada} com situação "{situacao_detectada}": {e}', exc_info=True)

            elif situacao_detectada and not categoria_detectada and not tem_listar_situacao and not tem_pendencia:
                log.warning(f'⚠️ Situação "{situacao_detectada}" detectada mas sem categoria válida. Usando função genérica...')
                try:
                    args_todos = {'limite': 500}
                    if situacao_detectada:
                        args_todos['situacao'] = situacao_detectada
                    if tem_pendencia:
                        args_todos['filtro_pendencias'] = True

                    resultado_forcado = chat_service._executar_funcao_tool(
                        'listar_todos_processos_por_situacao',
                        args_todos,
                        mensagem_original=mensagem,
                    )
                    if resultado_forcado.get('resposta'):
                        resultado_forcado['_forcado'] = True
                        resultados_tools.insert(0, resultado_forcado)
                        log.info(f'✅ Resposta da função genérica forçada para situação "{situacao_detectada}"')
                except Exception as e:
                    log.error(f'❌ Erro ao forçar chamada da função genérica para situação "{situacao_detectada}": {e}', exc_info=True)

            elif not tem_pendencia and not situacao_detectada and not tem_listar_categoria:
                log.warning(f'⚠️ Categoria {categoria_detectada} detectada mas IA não chamou listar_processos_por_categoria. Forçando chamada...')
                try:
                    resultado_forcado = chat_service._executar_funcao_tool(
                        'listar_processos_por_categoria',
                        {'categoria': categoria_detectada, 'limite': 200},
                        mensagem_original=mensagem,
                    )
                    if resultado_forcado.get('resposta'):
                        resultado_forcado['_forcado'] = True
                        resultados_tools.insert(0, resultado_forcado)
                        log.info(f'✅ Resposta da função forçada adicionada para categoria {categoria_detectada} (marcada como prioridade)')
                except Exception as e:
                    log.error(f'❌ Erro ao forçar chamada da função para categoria {categoria_detectada}: {e}', exc_info=True)

    elif situacao_detectada and not match_categoria and not tem_listar_todos_situacao_call and not valor_detectado:
        log.warning(f'🔍 Situação "{situacao_detectada}" detectada mas sem categoria válida. Usando função genérica...')
        try:
            args_todos = {'limite': 500}
            if situacao_detectada:
                args_todos['situacao'] = situacao_detectada
            if tem_pendencia:
                args_todos['filtro_pendencias'] = True

            resultado_forcado = chat_service._executar_funcao_tool(
                'listar_todos_processos_por_situacao',
                args_todos,
                mensagem_original=mensagem,
            )
            if resultado_forcado.get('resposta'):
                resultado_forcado['_forcado'] = True
                resultados_tools.insert(0, resultado_forcado)
                log.info(f'✅ Resposta da função genérica forçada para situação "{situacao_detectada}" (marcada como prioridade)')
        except Exception as e:
            log.error(f'❌ Erro ao forçar chamada da função genérica: {e}', exc_info=True)

    return tool_calls, resultados_tools, acao_info

