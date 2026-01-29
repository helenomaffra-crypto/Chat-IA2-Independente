"""
Prechecks forçados antes da IA (modo tool-calling).

Este módulo existe para reduzir o tamanho do `services/chat_service.py`.
Aqui ficam os blocos grandes de regex + chamadas diretas de tools que devem
retornar imediatamente (SEM chamar IA) quando detectados.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def tentar_prechecks_forcados_tool_calling(
    *,
    chat_service: Any,
    mensagem: str,
    session_id: Optional[str],
    logger_override: Optional[logging.Logger] = None,
) -> Optional[Dict[str, Any]]:
    """
    Executa prechecks forçados que retornam antes da IA quando `usar_tool_calling=True`.

    Regras:
    - Se algum precheck disparar, retorna um dict pronto para ser retornado por `processar_mensagem`.
    - Se nenhum disparar (ou se houver erro interno em um precheck), retorna None e o fluxo segue normal.
    """
    log = logger_override or logger

    import re

    # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar pedidos de baixar/atualizar NCM
    mensagem_lower_precheck = mensagem.lower()

    # ✅ PRIMEIRO: Detectar pedidos de buscar APENAS na NESH (busca direta, sem IA)
    # Padrões: "buscar na nesh", "consultar nesh", "pesquisar nesh", "buscar nesh", "nesh de [produto]"
    eh_busca_direta_nesh = bool(
        re.search(
            r'(?:buscar|consultar|pesquisar|procurar|ver|mostrar|mostre).*?(?:na\s+)?nesh',
            mensagem_lower_precheck,
        )
    ) or bool(re.search(r'nesh\s+(?:de|do|da|para|sobre)', mensagem_lower_precheck)) or bool(
        re.search(r'(?:nota\s+explicativa|notas\s+explicativas).*?(?:nesh|sh)', mensagem_lower_precheck)
    )

    if eh_busca_direta_nesh:
        log.warning(
            '🚨🚨🚨 PRIORIDADE MÁXIMA: Busca DIRETA na NESH detectada. '
            'Chamando buscar_nota_explicativa_nesh e retornando diretamente (SEM chamar IA).'
        )
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
            match_desc = re.search(r'nesh\s+(?:de|do|da|para|sobre)\s+(.+)', mensagem_lower_precheck) or re.search(
                r'(?:buscar|consultar|pesquisar|procurar|ver|mostrar|mostre).*?nesh.*?(?:de|do|da|para|sobre)\s+(.+)',
                mensagem_lower_precheck,
            )
            if match_desc:
                descricao_extraida = match_desc.group(1).strip()
                # Remover NCM se estiver na descrição
                if ncm_extraido and ncm_extraido in descricao_extraida:
                    descricao_extraida = descricao_extraida.replace(ncm_extraido, '').strip()
                # Limpar pontuação final
                descricao_extraida = re.sub(r'[?.,;!]+$', '', descricao_extraida).strip()

            # Se não encontrou descrição explícita, tentar extrair do contexto geral
            if not descricao_extraida and not ncm_extraido:
                # Tentar encontrar produto mencionado (ex: "nesh alho", "nesh ventilador")
                match_produto = re.search(
                    r'nesh\s+([a-záàâãéêíóôõúç\s]+?)(?:\s|$|\.|\?|,|;)', mensagem_lower_precheck
                )
                if match_produto:
                    descricao_extraida = match_produto.group(1).strip()

            resultado_nesh_direto = chat_service._executar_funcao_tool(
                'buscar_nota_explicativa_nesh',
                {
                    'ncm': ncm_extraido if ncm_extraido else None,
                    'descricao_produto': descricao_extraida if descricao_extraida else None,
                    'limite': 5,  # Limite maior para busca direta
                },
                mensagem_original=mensagem,
            )

            if resultado_nesh_direto and isinstance(resultado_nesh_direto, dict) and resultado_nesh_direto.get('resposta'):
                log.info(
                    '✅✅✅ Resposta forçada ANTES da IA (BUSCA DIRETA NESH) - tamanho: '
                    f'{len(resultado_nesh_direto.get("resposta"))}'
                )
                return {
                    'sucesso': True,
                    'resposta': resultado_nesh_direto.get('resposta'),
                    'tool_calling': {
                        'name': 'buscar_nota_explicativa_nesh',
                        'arguments': {'ncm': ncm_extraido, 'descricao_produto': descricao_extraida, 'limite': 5},
                    },
                    '_processado_precheck': True,
                    '_busca_direta_nesh': True,
                }

            log.warning(
                f'❌ Resposta vazia ou inválida da tool buscar_nota_explicativa_nesh para "{mensagem}". '
                'Prosseguindo com a IA.'
            )
        except Exception as e:
            log.error(
                f'❌ Erro ao forçar tool buscar_nota_explicativa_nesh para "{mensagem}": {e}',
                exc_info=True,
            )

    # ✅ PRIMEIRO: Detectar pedidos de baixar/atualizar NCM (ANTES de tudo)
    # Padrões: "baixar nomenclatura NCM", "atualizar tabela NCM", "sincronizar NCM", "popular NCM"
    eh_pedido_baixar_ncm = bool(
        re.search(
            r'(?:baixar|atualizar|sincronizar|popular|atualiza|sincroniza|popula).*?(?:nomenclatura|ncm|classifica[çc][ãa]o\s+fiscal|tabela\s+ncm)',
            mensagem_lower_precheck,
        )
    ) or bool(
        re.search(
            r'(?:nomenclatura|ncm|classifica[çc][ãa]o\s+fiscal).*?(?:baixar|atualizar|sincronizar|popular)',
            mensagem_lower_precheck,
        )
    )

    if eh_pedido_baixar_ncm:
        log.warning(
            '🚨🚨🚨 PRIORIDADE MÁXIMA: Pedido de baixar/atualizar NCM detectado. '
            'Chamando baixar_nomenclatura_ncm e retornando diretamente (SEM chamar IA).'
        )
        try:
            forcar = bool(re.search(r'for[çc]ar|for[çc]a|mesmo\s+assim', mensagem_lower_precheck))
            resultado_baixar_ncm = chat_service._executar_funcao_tool(
                'baixar_nomenclatura_ncm',
                {'forcar_atualizacao': forcar},
                mensagem_original=mensagem,
            )

            if resultado_baixar_ncm and isinstance(resultado_baixar_ncm, dict) and resultado_baixar_ncm.get('resposta'):
                log.info(
                    '✅✅✅ Resposta forçada ANTES da IA (BAIXAR NCM) - tamanho: '
                    f'{len(resultado_baixar_ncm.get("resposta"))}'
                )
                return {
                    'sucesso': True,
                    'resposta': resultado_baixar_ncm.get('resposta'),
                    'tool_calling': {
                        'name': 'baixar_nomenclatura_ncm',
                        'arguments': {'forcar_atualizacao': forcar},
                    },
                    '_processado_precheck': True,
                }

            log.warning(
                f'❌ Resposta vazia ou inválida da tool baixar_nomenclatura_ncm para "{mensagem}". Prosseguindo com a IA.'
            )
        except Exception as e:
            log.error(
                f'❌ Erro ao forçar tool baixar_nomenclatura_ncm para "{mensagem}": {e}',
                exc_info=True,
            )

    # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar "extrato da duimp" ANTES de qualquer outra coisa
    match_extrato_duimp = re.search(
        r'extrato\s+(?:da\s+)?duimp\s+(?:do\s+)?([a-z]{3}\.?\d{1,4}/?\d{2})',
        mensagem_lower_precheck,
    ) or re.search(
        r'pdf\s+(?:da\s+)?duimp\s+(?:do\s+)?([a-z]{3}\.?\d{1,4}/?\d{2})',
        mensagem_lower_precheck,
    )

    # ✅ NOVO: Detectar por número de DUIMP (25BR...)
    match_numero_duimp = re.search(r'(?:extrato|qual\s+o\s+extrato|pdf).*?duimp.*?(25BR\d{11})', mensagem, re.IGNORECASE) or re.search(
        r'(?:extrato|qual\s+o\s+extrato|pdf).*?(25BR\d{11})',
        mensagem,
        re.IGNORECASE,
    )

    processo_extrato = None
    numero_duimp_extrato = None

    if match_numero_duimp:
        if isinstance(match_numero_duimp, re.Match) and match_numero_duimp.lastindex and match_numero_duimp.group(1):
            numero_duimp_extrato = match_numero_duimp.group(1).upper()
            log.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pedido de extrato PDF da DUIMP detectado por número. '
                f'DUIMP: {numero_duimp_extrato}. Chamando obter_extrato_pdf_duimp e retornando diretamente (SEM chamar IA).'
            )
            try:
                resultado_extrato_precheck = chat_service._executar_funcao_tool(
                    'obter_extrato_pdf_duimp',
                    {'numero_duimp': numero_duimp_extrato},
                    mensagem_original=mensagem,
                )
                if resultado_extrato_precheck.get('resposta'):
                    log.info(
                        '✅✅✅ Resposta forçada ANTES da IA (EXTRATO PDF DUIMP por número) - tamanho: '
                        f'{len(resultado_extrato_precheck.get("resposta"))}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resultado_extrato_precheck.get('resposta'),
                        'tool_calling': {'name': 'obter_extrato_pdf_duimp', 'arguments': {'numero_duimp': numero_duimp_extrato}},
                        '_processado_precheck': True,
                    }
                log.warning(
                    f'❌ Resposta vazia da tool obter_extrato_pdf_duimp para DUIMP "{numero_duimp_extrato}". Prosseguindo com a IA.'
                )
            except Exception as e:
                log.error(
                    f'❌ Erro ao forçar tool obter_extrato_pdf_duimp para DUIMP "{numero_duimp_extrato}": {e}',
                    exc_info=True,
                )

    if match_extrato_duimp:
        if isinstance(match_extrato_duimp, re.Match) and match_extrato_duimp.lastindex and match_extrato_duimp.group(1):
            processo_extrato = match_extrato_duimp.group(1).upper()
            if not re.match(r'[A-Z]{2,4}\.\d{4}/\d{2}', processo_extrato):
                processo_extrato = chat_service._extrair_processo_referencia(processo_extrato) or processo_extrato
        else:
            processo_extrato = chat_service._extrair_processo_referencia(mensagem)

    if not processo_extrato and not numero_duimp_extrato:
        if re.search(r'extrato\s+(?:da\s+)?duimp', mensagem_lower_precheck):
            processo_extrato = chat_service._extrair_processo_referencia(mensagem)
            match_numero = re.search(r'(25BR\d{11})', mensagem, re.IGNORECASE)
            if match_numero:
                numero_duimp_extrato = match_numero.group(1).upper()

    if processo_extrato:
        log.warning(
            '🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pedido de extrato PDF da DUIMP detectado. '
            f'Processo: {processo_extrato}. Chamando obter_extrato_pdf_duimp e retornando diretamente (SEM chamar IA).'
        )
        try:
            resultado_extrato_precheck = chat_service._executar_funcao_tool(
                'obter_extrato_pdf_duimp',
                {'processo_referencia': processo_extrato},
                mensagem_original=mensagem,
            )
            if resultado_extrato_precheck.get('resposta'):
                log.info(
                    '✅✅✅ Resposta forçada ANTES da IA (EXTRATO PDF DUIMP) - tamanho: '
                    f'{len(resultado_extrato_precheck.get("resposta"))}'
                )
                return {
                    'sucesso': True,
                    'resposta': resultado_extrato_precheck.get('resposta'),
                    'tool_calling': {'name': 'obter_extrato_pdf_duimp', 'arguments': {'processo_referencia': processo_extrato}},
                    '_processado_precheck': True,
                }
            log.warning(f'❌ Resposta vazia da tool obter_extrato_pdf_duimp para "{mensagem}". Prosseguindo com a IA.')
        except Exception as e:
            log.error(
                f'❌ Erro ao forçar tool obter_extrato_pdf_duimp para "{mensagem}": {e}',
                exc_info=True,
            )

    # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar "extrato do CE" ANTES de qualquer outra coisa
    match_extrato_ce = (
        re.search(
            r'extrato\s+(?:do\s+)?ce\s+(?:do\s+(?:processo\s+)?)?([a-z]{3}\.?\d{1,4}/?\d{2})',
            mensagem_lower_precheck,
        )
        or re.search(
            r'pdf\s+(?:do\s+)?ce\s+(?:do\s+(?:processo\s+)?)?([a-z]{3}\.?\d{1,4}/?\d{2})',
            mensagem_lower_precheck,
        )
        or re.search(r'extrato\s+ce\s+([a-z]{3}\.?\d{1,4}/?\d{2})', mensagem_lower_precheck)
    )

    match_numero_ce = re.search(r'(?:extrato|qual\s+o\s+extrato|pdf).*?ce.*?(\d{15})', mensagem, re.IGNORECASE) or re.search(
        r'(?:extrato|qual\s+o\s+extrato|pdf).*?(\d{15})',
        mensagem,
        re.IGNORECASE,
    )

    processo_extrato_ce = None
    numero_ce_extrato = None

    if match_numero_ce:
        if isinstance(match_numero_ce, re.Match) and match_numero_ce.lastindex and match_numero_ce.group(1):
            numero_ce_extrato = match_numero_ce.group(1)
            log.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pedido de extrato do CE detectado por número. '
                f'CE: {numero_ce_extrato}. Chamando obter_extrato_ce e retornando diretamente (SEM chamar IA).'
            )
            try:
                resultado_extrato_ce_precheck = chat_service._executar_funcao_tool(
                    'obter_extrato_ce',
                    {'numero_ce': numero_ce_extrato},
                    mensagem_original=mensagem,
                )
                if resultado_extrato_ce_precheck.get('resposta'):
                    log.info(
                        '✅✅✅ Resposta forçada ANTES da IA (EXTRATO CE por número) - tamanho: '
                        f'{len(resultado_extrato_ce_precheck.get("resposta"))}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resultado_extrato_ce_precheck.get('resposta'),
                        'tool_calling': {'name': 'obter_extrato_ce', 'arguments': {'numero_ce': numero_ce_extrato}},
                        '_processado_precheck': True,
                    }
                log.warning(f'❌ Resposta vazia da tool obter_extrato_ce para CE "{numero_ce_extrato}". Prosseguindo com a IA.')
            except Exception as e:
                log.error(
                    f'❌ Erro ao forçar tool obter_extrato_ce para CE "{numero_ce_extrato}": {e}',
                    exc_info=True,
                )

    if match_extrato_ce:
        if isinstance(match_extrato_ce, re.Match) and match_extrato_ce.lastindex and match_extrato_ce.group(1):
            processo_extrato_ce = match_extrato_ce.group(1).upper()
            if not re.match(r'[A-Z]{2,4}\.\d{4}/\d{2}', processo_extrato_ce):
                processo_extrato_ce = chat_service._extrair_processo_referencia(processo_extrato_ce) or processo_extrato_ce
        else:
            processo_extrato_ce = chat_service._extrair_processo_referencia(mensagem)

    if not processo_extrato_ce and not numero_ce_extrato:
        if re.search(r'extrato\s+(?:do\s+)?ce', mensagem_lower_precheck):
            processo_extrato_ce = chat_service._extrair_processo_referencia(mensagem)
            match_numero = re.search(r'(\d{15})', mensagem)
            if match_numero:
                numero_ce_extrato = match_numero.group(1)

    if processo_extrato_ce:
        log.warning(
            '🚨🚨🚨 PRIORIDADE MÁXIMA ABSOLUTA: Pedido de extrato do CE detectado. '
            f'Processo: {processo_extrato_ce}. Chamando obter_extrato_ce e retornando diretamente (SEM chamar IA).'
        )
        try:
            resultado_extrato_ce_precheck = chat_service._executar_funcao_tool(
                'obter_extrato_ce',
                {'processo_referencia': processo_extrato_ce},
                mensagem_original=mensagem,
            )
            if resultado_extrato_ce_precheck.get('resposta'):
                log.info(
                    '✅✅✅ Resposta forçada ANTES da IA (EXTRATO CE) - tamanho: '
                    f'{len(resultado_extrato_ce_precheck.get("resposta"))}'
                )
                return {
                    'sucesso': True,
                    'resposta': resultado_extrato_ce_precheck.get('resposta'),
                    'tool_calling': {'name': 'obter_extrato_ce', 'arguments': {'processo_referencia': processo_extrato_ce}},
                    '_processado_precheck': True,
                }
            log.warning(f'❌ Resposta vazia da tool obter_extrato_ce para "{mensagem}". Prosseguindo com a IA.')
        except Exception as e:
            log.error(
                f'❌ Erro ao forçar tool obter_extrato_ce para "{mensagem}": {e}',
                exc_info=True,
            )

    # ✅⚠️⚠️⚠️ NOTA:
    # O bloco completo de prechecks forçados (situação/chegada/etc.) é grande e continuará sendo
    # extraído incrementalmente para este módulo em próximos passos.
    return None

