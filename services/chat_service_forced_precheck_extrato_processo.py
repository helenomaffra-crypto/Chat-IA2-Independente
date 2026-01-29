"""
Precheck forçado: "extrato do processo" (sem mencionar DI/DUIMP explicitamente).

Este bloco foi extraído do `services/chat_service.py` para reduzir o tamanho do arquivo.
Mantém o mesmo comportamento: tenta inferir se o processo tem DI ou DUIMP e chama a tool
correspondente para retornar o PDF.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def tentar_precheck_extrato_generico_por_processo(
    *,
    chat_service: Any,
    mensagem: str,
    mensagem_lower_precheck: str,
    logger_override: Optional[logging.Logger] = None,
) -> Optional[Dict[str, Any]]:
    log = logger_override or logger

    import re

    # ✅ PRIORIDADE MÁXIMA ABSOLUTA: Detectar "extrato do processo" (sem mencionar DI ou DUIMP)
    # Palavra-chave "extrato" + processo, mas SEM mencionar "di" ou "duimp" explicitamente
    tem_mencao_di_explicita = bool(re.search(r'\bdi\b', mensagem_lower_precheck))
    tem_mencao_duimp_explicita = bool(re.search(r'\bduimp\b', mensagem_lower_precheck))
    tem_palavra_extrato = bool(re.search(r'\bextrato\b', mensagem_lower_precheck) or re.search(r'\bpdf\b', mensagem_lower_precheck))

    if not (tem_palavra_extrato and not tem_mencao_di_explicita and not tem_mencao_duimp_explicita):
        return None

    # Tentar extrair processo da mensagem
    processo_extrato_generico = chat_service._extrair_processo_referencia(mensagem)
    if not processo_extrato_generico:
        return None

    log.info(
        '🔍 Detectado "extrato" sem menção explícita de DI/DUIMP. '
        f'Verificando documentos do processo {processo_extrato_generico}...'
    )

    try:
        from db_manager import obter_dados_documentos_processo

        dados_docs = obter_dados_documentos_processo(processo_extrato_generico)

        # Verificar se tem DI ou DUIMP
        tem_di = False
        tem_duimp = False
        numero_di_auto = None
        numero_duimp_auto = None

        # Verificar DIs
        dis_list = dados_docs.get('dis', [])
        if dis_list and len(dis_list) > 0:
            # Pegar a primeira DI (processo nunca tem mais de uma DI)
            di_primeira = dis_list[0]
            if di_primeira:
                # Tentar múltiplos campos possíveis
                numero_di_candidato = (
                    di_primeira.get('numero')
                    or di_primeira.get('numero_di')
                    or di_primeira.get('numeroDi')
                    or ''
                )
                if numero_di_candidato and numero_di_candidato.strip() not in ['', '/ -', '-', 'None', 'null']:
                    tem_di = True
                    numero_di_auto = numero_di_candidato.strip()

        # Verificar DUIMPs
        duimps_list = dados_docs.get('duimps', [])
        if duimps_list and len(duimps_list) > 0:
            # Pegar a primeira DUIMP (processo nunca tem mais de uma DUIMP)
            duimp_primeira = duimps_list[0]
            if duimp_primeira:
                # Tentar múltiplos campos possíveis
                numero_duimp_candidato = (
                    duimp_primeira.get('numero')
                    or duimp_primeira.get('numero_duimp')
                    or duimp_primeira.get('numeroDuimp')
                    or ''
                )
                if numero_duimp_candidato and numero_duimp_candidato.strip() not in ['', '/ -', '-', 'None', 'null']:
                    tem_duimp = True
                    numero_duimp_auto = numero_duimp_candidato.strip()

        # ✅ REGRA: Processo NUNCA tem os dois (DI e DUIMP)
        # Se tiver ambos, algo está errado (priorizar DUIMP que é mais recente)
        if tem_di and tem_duimp:
            log.warning(
                f'⚠️ Processo {processo_extrato_generico} tem AMBOS DI e DUIMP (inconsistência). '
                'Priorizando DUIMP.'
            )
            tem_di = False

        if tem_duimp:
            log.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA: Pedido de extrato detectado. '
                f'Processo {processo_extrato_generico} tem DUIMP {numero_duimp_auto}. '
                'Chamando obter_extrato_pdf_duimp automaticamente.'
            )
            try:
                resultado_extrato_auto = chat_service._executar_funcao_tool(
                    'obter_extrato_pdf_duimp',
                    {'processo_referencia': processo_extrato_generico},
                    mensagem_original=mensagem,
                )

                if resultado_extrato_auto and isinstance(resultado_extrato_auto, dict) and resultado_extrato_auto.get('resposta'):
                    log.info(
                        '✅✅✅ Resposta automática (extrato genérico → DUIMP) - tamanho: '
                        f'{len(resultado_extrato_auto.get("resposta"))}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resultado_extrato_auto.get('resposta'),
                        'tool_calling': {
                            'name': 'obter_extrato_pdf_duimp',
                            'arguments': {'processo_referencia': processo_extrato_generico},
                        },
                        '_processado_precheck': True,
                        '_auto_detectado': 'DUIMP',
                    }
            except Exception as e:
                log.error(f'❌ Erro ao chamar obter_extrato_pdf_duimp automaticamente: {e}', exc_info=True)

        elif tem_di:
            log.warning(
                '🚨🚨🚨 PRIORIDADE MÁXIMA: Pedido de extrato detectado. '
                f'Processo {processo_extrato_generico} tem DI {numero_di_auto}. '
                'Chamando obter_extrato_pdf_di automaticamente.'
            )
            try:
                resultado_extrato_auto = chat_service._executar_funcao_tool(
                    'obter_extrato_pdf_di',
                    {'processo_referencia': processo_extrato_generico},
                    mensagem_original=mensagem,
                )

                if resultado_extrato_auto and isinstance(resultado_extrato_auto, dict) and resultado_extrato_auto.get('resposta'):
                    log.info(
                        '✅✅✅ Resposta automática (extrato genérico → DI) - tamanho: '
                        f'{len(resultado_extrato_auto.get("resposta"))}'
                    )
                    return {
                        'sucesso': True,
                        'resposta': resultado_extrato_auto.get('resposta'),
                        'tool_calling': {
                            'name': 'obter_extrato_pdf_di',
                            'arguments': {'processo_referencia': processo_extrato_generico},
                        },
                        '_processado_precheck': True,
                        '_auto_detectado': 'DI',
                    }
            except Exception as e:
                log.error(f'❌ Erro ao chamar obter_extrato_pdf_di automaticamente: {e}', exc_info=True)

        else:
            # ✅ FALLBACK: Se obter_dados_documentos_processo não encontrou, tentar buscar_di_banco diretamente
            log.info(
                '⚠️ obter_dados_documentos_processo não encontrou DI/DUIMP. '
                'Tentando buscar_di_banco como fallback...'
            )
            try:
                from services.di_pdf_service import DiPdfService
                from services.duimp_pdf_service import DuimpPdfService

                di_service = DiPdfService()
                duimp_service = DuimpPdfService()

                numero_di_fallback = di_service.buscar_di_banco(processo_referencia=processo_extrato_generico)

                duimp_dict_fallback = duimp_service.buscar_duimp_banco(processo_referencia=processo_extrato_generico)
                numero_duimp_fallback = None
                if duimp_dict_fallback and isinstance(duimp_dict_fallback, dict):
                    numero_duimp_fallback = duimp_dict_fallback.get('numero') or duimp_dict_fallback.get('numero_duimp')

                if numero_duimp_fallback:
                    log.warning(
                        '🚨🚨🚨 FALLBACK: '
                        f'Processo {processo_extrato_generico} tem DUIMP {numero_duimp_fallback} '
                        '(encontrado via buscar_duimp_banco). Chamando obter_extrato_pdf_duimp.'
                    )
                    try:
                        resultado_extrato_fallback = chat_service._executar_funcao_tool(
                            'obter_extrato_pdf_duimp',
                            {'processo_referencia': processo_extrato_generico},
                            mensagem_original=mensagem,
                        )
                        if resultado_extrato_fallback and isinstance(resultado_extrato_fallback, dict) and resultado_extrato_fallback.get('resposta'):
                            log.info(
                                '✅✅✅ Resposta automática (FALLBACK → DUIMP) - tamanho: '
                                f'{len(resultado_extrato_fallback.get("resposta"))}'
                            )
                            return {
                                'sucesso': True,
                                'resposta': resultado_extrato_fallback.get('resposta'),
                                'tool_calling': {
                                    'name': 'obter_extrato_pdf_duimp',
                                    'arguments': {'processo_referencia': processo_extrato_generico},
                                },
                                '_processado_precheck': True,
                                '_auto_detectado': 'DUIMP_FALLBACK',
                            }
                    except Exception as e:
                        log.error(f'❌ Erro ao chamar obter_extrato_pdf_duimp no fallback: {e}', exc_info=True)

                elif numero_di_fallback:
                    log.warning(
                        '🚨🚨🚨 FALLBACK: '
                        f'Processo {processo_extrato_generico} tem DI {numero_di_fallback} '
                        '(encontrado via buscar_di_banco). Chamando obter_extrato_pdf_di.'
                    )
                    try:
                        resultado_extrato_fallback = chat_service._executar_funcao_tool(
                            'obter_extrato_pdf_di',
                            {'processo_referencia': processo_extrato_generico},
                            mensagem_original=mensagem,
                        )
                        if resultado_extrato_fallback and isinstance(resultado_extrato_fallback, dict) and resultado_extrato_fallback.get('resposta'):
                            log.info(
                                '✅✅✅ Resposta automática (FALLBACK → DI) - tamanho: '
                                f'{len(resultado_extrato_fallback.get("resposta"))}'
                            )
                            return {
                                'sucesso': True,
                                'resposta': resultado_extrato_fallback.get('resposta'),
                                'tool_calling': {
                                    'name': 'obter_extrato_pdf_di',
                                    'arguments': {'processo_referencia': processo_extrato_generico},
                                },
                                '_processado_precheck': True,
                                '_auto_detectado': 'DI_FALLBACK',
                            }
                    except Exception as e:
                        log.error(f'❌ Erro ao chamar obter_extrato_pdf_di no fallback: {e}', exc_info=True)

                else:
                    log.info(
                        f'⚠️ Processo {processo_extrato_generico} não tem DI nem DUIMP cadastrados (verificado em todas as fontes).'
                    )
                    return {
                        'sucesso': False,
                        'erro': 'PROCESSO_SEM_DOCUMENTO',
                        'resposta': (
                            f'❌ O processo {processo_extrato_generico} não possui DI nem DUIMP cadastrados.\n\n'
                            '💡 Dica: Este processo ainda não possui documento de importação registrado. '
                            'Verifique se o processo foi cadastrado corretamente ou se o documento ainda não foi registrado.'
                        ),
                        '_processado_precheck': True,
                    }

            except Exception as e:
                log.error(f'❌ Erro no fallback de busca de DI/DUIMP: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': 'ERRO_BUSCA_DOCUMENTO',
                    'resposta': f'❌ Erro ao buscar documentos do processo {processo_extrato_generico}: {str(e)}',
                    '_processado_precheck': True,
                }

    except Exception as e:
        log.error(f'❌ Erro ao verificar documentos do processo {processo_extrato_generico}: {e}', exc_info=True)
        return None

    return None

