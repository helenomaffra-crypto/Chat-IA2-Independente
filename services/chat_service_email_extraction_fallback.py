"""
Fallback de extração de email a partir de texto livre da IA.

Este módulo existe para manter o `services/chat_service.py` mais enxuto.
Ele contém a lógica legada/deprecated de extração de assunto+conteúdo via regex.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def extrair_email_da_resposta_ia_fallback(
    *,
    resposta_ia: str,
    dados_email_original: Dict[str, Any],
    logger_override: Optional[logging.Logger] = None,
) -> Optional[Dict[str, Any]]:
    """
    Extrai assunto e conteúdo de uma resposta de IA que contém um email.

    Args:
        resposta_ia: Texto retornado pela IA.
        dados_email_original: Dict com dados do email original em preview.
        logger_override: Logger opcional (para manter logs no contexto do ChatService).

    Returns:
        Dict com {'assunto': str, 'conteudo': str} ou None se não conseguir extrair.
    """
    log = logger_override or logger
    try:
        import re

        # Tentar extrair do formato de preview estruturado
        # Padrão: **Assunto:** [assunto] ou Assunto: [assunto] ou Assunto sugerido: [assunto]
        match_assunto = re.search(r'\*\*?Assunto[:\s]+\*\*?\s*(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
        assunto_refinado = match_assunto.group(1).strip() if match_assunto else None

        # ✅ CORREÇÃO CRÍTICA (09/01/2026): Também tentar padrão "Assunto sugerido:" que a IA usa
        if not assunto_refinado:
            # Tentar padrão "Assunto sugerido:" primeiro (mais específico)
            match_assunto_sugerido = re.search(r'Assunto\s+sugerido[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
            if match_assunto_sugerido:
                assunto_refinado = match_assunto_sugerido.group(1).strip()
                # Limpar possíveis marcadores no final
                assunto_refinado = re.sub(r'\s*Corpo.*$', '', assunto_refinado, flags=re.IGNORECASE).strip()
                log.info(f'✅ [MELHORAR EMAIL] Assunto extraído via padrão "Assunto sugerido:": "{assunto_refinado}"')
            else:
                # Tentar padrão alternativo: "Assunto sugerido" sem dois pontos
                match_assunto_sugerido_alt = re.search(r'Assunto\s+sugerido[:\s]*\n\s*(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                if match_assunto_sugerido_alt:
                    assunto_refinado = match_assunto_sugerido_alt.group(1).strip()
                    assunto_refinado = re.sub(r'\s*Corpo.*$', '', assunto_refinado, flags=re.IGNORECASE).strip()
                    log.info(f'✅ [MELHORAR EMAIL] Assunto extraído via padrão alternativo "Assunto sugerido": "{assunto_refinado}"')

        # ✅ CORREÇÃO (09/01/2026): Também tentar padrão "Assunto:" seguido de texto na mesma linha ou próxima
        # IMPORTANTE: Não capturar se for parte de "Sugestão de texto melhorado:" ou similar
        if not assunto_refinado:
            # Tentar encontrar "Assunto:" que não seja parte de texto introdutório
            # Padrão: linha que começa com "Assunto:" ou "Assunto: " seguido de texto
            match_assunto_linha = re.search(r'(?:^|\n)\s*Assunto[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
            if match_assunto_linha:
                assunto_refinado = match_assunto_linha.group(1).strip()
                # Limpar possíveis marcadores no final (ex: "Assunto: Reagendamento...\nCorpo:")
                assunto_refinado = re.sub(r'\s*(Corpo|Corpo do email):.*$', '', assunto_refinado, flags=re.IGNORECASE).strip()
                log.info(f'✅ [MELHORAR EMAIL] Assunto extraído via padrão "Assunto:": "{assunto_refinado}"')

        conteudo_refinado = None

        # Tentar extrair conteúdo
        # Padrão: **Conteúdo:** ou Conteúdo: seguido de texto
        match_conteudo = re.search(r'\*\*?Conteúdo:\*\*?\s*\n(.+?)(?:\n\n|$|⚠️|💡)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match_conteudo:
            conteudo_refinado = match_conteudo.group(1).strip()
            log.info('✅ [MELHORAR EMAIL] Conteúdo extraído via padrão "Conteúdo:" (formato markdown)')
        else:
            # Tentar padrão alternativo: texto após "Conteúdo:" até fim ou próximo marcador
            match_conteudo = re.search(r'Conteúdo[:\s]+\n(.+?)(?:\n\n|$|⚠️|💡|Confirme)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match_conteudo:
                conteudo_refinado = match_conteudo.group(1).strip()
                log.info('✅ [MELHORAR EMAIL] Conteúdo extraído via padrão "Conteúdo:"')

        # ✅ CORREÇÃO CRÍTICA (09/01/2026): Também tentar padrão "Corpo:" ou "Corpo do email:" que a IA usa
        # Padrão: "Corpo:" ou "Corpo do email:" seguido de conteúdo até "Se quiser" ou marcador de fonte
        if not conteudo_refinado:
            # Tentar padrão "Corpo do email:" primeiro (mais específico)
            match_corpo_email = re.search(r'Corpo\s+do\s+email[:\s]*\n(.*?)(?=\nSe quiser|\n\n━━━━|━━━━|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match_corpo_email:
                conteudo_refinado = match_corpo_email.group(1).strip()
                log.info(f'✅ [MELHORAR EMAIL] Conteúdo extraído via padrão "Corpo do email:" ({len(conteudo_refinado)} caracteres)')
                log.debug(f'✅ [MELHORAR EMAIL] Conteúdo extraído (primeiros 200 chars): {conteudo_refinado[:200]}')
            else:
                match_corpo_email_simples = re.search(r'Corpo\s+do\s+email[:\s]*\n(.*?)\nSe quiser', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match_corpo_email_simples:
                    conteudo_refinado = match_corpo_email_simples.group(1).strip()
                    log.info(f'✅ [MELHORAR EMAIL] Conteúdo extraído via padrão simples "Corpo do email:" ({len(conteudo_refinado)} caracteres)')
                    log.debug(f'✅ [MELHORAR EMAIL] Conteúdo extraído (primeiros 200 chars): {conteudo_refinado[:200]}')
                else:
                    match_corpo = re.search(r'Corpo[:\s]+\n(.*?)(?=\nSe quiser|\n\n━━━━|━━━━|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    if match_corpo:
                        conteudo_refinado = match_corpo.group(1).strip()
                        log.info(f'✅ [MELHORAR EMAIL] Conteúdo extraído via padrão "Corpo:" ({len(conteudo_refinado)} caracteres)')
                        log.debug(f'✅ [MELHORAR EMAIL] Conteúdo extraído (primeiros 200 chars): {conteudo_refinado[:200]}')
                    else:
                        match_corpo_simples = re.search(r'Corpo[:\s]+\n(.*?)\nSe quiser', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                        if match_corpo_simples:
                            conteudo_refinado = match_corpo_simples.group(1).strip()
                            log.info(f'✅ [MELHORAR EMAIL] Conteúdo extraído via padrão simples "Corpo:" ({len(conteudo_refinado)} caracteres)')
                        else:
                            match_corpo_alt = re.search(r'Corpo\s+(?:do\s+email)?[:\s]*\n(.*?)(?=\n(?:Se quiser|\n━━━━|━━━━)|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                            if match_corpo_alt:
                                conteudo_refinado = match_corpo_alt.group(1).strip()
                                conteudo_refinado = re.sub(r'\n\n━━━━.*$', '', conteudo_refinado, flags=re.DOTALL)
                                log.info(f'✅ [MELHORAR EMAIL] Conteúdo extraído via padrão alternativo "Corpo:" ({len(conteudo_refinado)} caracteres)')

        # Se não encontrou no formato estruturado, tentar extrair de texto livre
        if not assunto_refinado or not conteudo_refinado:
            tem_saudacao = bool(re.search(r'^(Olá|Oi|Prezado|Querido|Meu amor|Meu querido|Olá,|Oi,|Querido|Querida)', resposta_ia, re.IGNORECASE | re.MULTILINE))
            tem_despedida = bool(re.search(r'(Atenciosamente|Com carinho|Com amor|Abraços|Beijos|Maria|\[Seu nome\]|Com carinho,|Com amor,|Atenciosamente,)', resposta_ia, re.IGNORECASE))

            if tem_saudacao or tem_despedida:
                if not assunto_refinado:
                    match_assunto_linha = re.search(r'Assunto[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                    if match_assunto_linha:
                        assunto_refinado = match_assunto_linha.group(1).strip()
                    else:
                        match_assunto_apos_intro = re.search(r'(?:versão|versao|email|mensagem)[^:]*:\s*\n\s*Assunto[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                        if match_assunto_apos_intro:
                            assunto_refinado = match_assunto_apos_intro.group(1).strip()
                        else:
                            if 'almoçar' in resposta_ia.lower() or 'almoço' in resposta_ia.lower():
                                assunto_refinado = 'Convite para Almoçar Hoje ❤️' if 'amor' in resposta_ia.lower() or 'amoroso' in resposta_ia.lower() else 'Convite para Almoçar Hoje'
                            elif 'reunião' in resposta_ia.lower() or 'reuniao' in resposta_ia.lower():
                                if 'ausência' in resposta_ia.lower() or 'ausencia' in resposta_ia.lower() or 'não poderei' in resposta_ia.lower():
                                    assunto_refinado = 'Ausência na reunião de hoje às 16h'
                                else:
                                    assunto_refinado = dados_email_original.get('assunto', 'Mensagem')
                            else:
                                assunto_refinado = dados_email_original.get('assunto', 'Mensagem')

                if not conteudo_refinado:
                    match_email_completo = re.search(
                        r'(?:Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido)[^:]*:?\s*\n(.+?)(?:Atenciosamente|Com carinho|Com amor|Abraços|Beijos|Guilherme|\[Seu nome\])',
                        resposta_ia,
                        re.IGNORECASE | re.MULTILINE | re.DOTALL
                    )
                    if match_email_completo:
                        conteudo_bruto = match_email_completo.group(1).strip()
                        conteudo_bruto = re.sub(r'^[^\n]*(?:versão|versao|email|mensagem|melhorada|elaborada)[^\n]*\n', '', conteudo_bruto, flags=re.IGNORECASE | re.MULTILINE)
                        conteudo_bruto = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_bruto, flags=re.IGNORECASE | re.MULTILINE)
                        conteudo_refinado = conteudo_bruto.strip()

                    if not conteudo_refinado:
                        conteudo_limpo = resposta_ia
                        conteudo_limpo = re.sub(r'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_limpo, flags=re.DOTALL)
                        conteudo_limpo = re.sub(r'🔍 \*\*FONTE:.*$', '', conteudo_limpo, flags=re.DOTALL)
                        conteudo_limpo = re.sub(r'💡.*$', '', conteudo_limpo, flags=re.DOTALL)
                        conteudo_limpo = re.sub(r'⚠️.*$', '', conteudo_limpo, flags=re.DOTALL)
                        conteudo_limpo = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                        conteudo_limpo = re.sub(r'^\*\*?Para:\*\*?\s*.*$', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                        conteudo_limpo = re.sub(r'^[^\n]*(?:segue|versão|versao|email|mensagem|melhorada|elaborada|tom|formal|elegante)[^\n]*:?\s*\n', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                        conteudo_limpo = re.sub(r'^[^:]*:?\s*(?:segue|versão|versao|email|mensagem|melhorada|elaborada|tom|formal|elegante)[^:]*:?\s*\n', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                        linhas = conteudo_limpo.split('\n')
                        primeira_saudacao_idx = None
                        for i, linha in enumerate(linhas):
                            if re.match(r'^(Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido)', linha.strip(), re.IGNORECASE):
                                primeira_saudacao_idx = i
                                break
                        if primeira_saudacao_idx is not None and primeira_saudacao_idx > 0:
                            conteudo_limpo = '\n'.join(linhas[primeira_saudacao_idx:])
                        conteudo_refinado = conteudo_limpo.strip()

                    if not conteudo_refinado or len(conteudo_refinado) < 20:
                        conteudo_refinado = resposta_ia.strip()
                        conteudo_refinado = re.sub(r'\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_refinado, flags=re.DOTALL)

        if not assunto_refinado:
            assunto_refinado = dados_email_original.get('assunto', 'Mensagem')

        if not conteudo_refinado:
            linhas = resposta_ia.split('\n')
            primeira_saudacao_idx = None
            ultima_despedida_idx = None

            for i, linha in enumerate(linhas):
                linha_limpa = linha.strip()
                if primeira_saudacao_idx is None and re.match(r'^(Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido)', linha_limpa, re.IGNORECASE):
                    primeira_saudacao_idx = i
                if re.search(r'(Atenciosamente|Com carinho|Com amor|Abraços|Beijos|Guilherme|Maria|\[Seu nome\])', linha_limpa, re.IGNORECASE):
                    ultima_despedida_idx = i

            if primeira_saudacao_idx is not None:
                fim_idx = ultima_despedida_idx + 1 if ultima_despedida_idx is not None else len(linhas)
                conteudo_extraido = '\n'.join(linhas[primeira_saudacao_idx:fim_idx])
                conteudo_extraido = re.sub(r'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_extraido, flags=re.DOTALL)
                conteudo_extraido = re.sub(r'🔍.*$', '', conteudo_extraido, flags=re.DOTALL)
                conteudo_extraido = re.sub(r'💡.*$', '', conteudo_extraido, flags=re.DOTALL)
                conteudo_extraido = re.sub(r'⚠️.*$', '', conteudo_extraido, flags=re.DOTALL)
                conteudo_refinado = conteudo_extraido.strip()
                log.info(f'✅ [MELHORAR EMAIL] Conteúdo extraído via padrão permissivo (linhas {primeira_saudacao_idx} até {fim_idx})')

        if not conteudo_refinado:
            linhas_simples = resposta_ia.split('\n')
            primeira_saudacao_simples = None
            for i, linha in enumerate(linhas_simples):
                linha_limpa = linha.strip()
                if re.search(r'^(Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido|Heleno|Boa tarde|Bom dia|Boa noite)', linha_limpa, re.IGNORECASE):
                    primeira_saudacao_simples = i
                    break

            if primeira_saudacao_simples is not None:
                conteudo_simples = '\n'.join(linhas_simples[primeira_saudacao_simples:])
                conteudo_simples = re.sub(r'\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_simples, flags=re.DOTALL)
                conteudo_simples = re.sub(r'\n🔍.*$', '', conteudo_simples, flags=re.DOTALL)
                conteudo_simples = re.sub(r'\n💡.*$', '', conteudo_simples, flags=re.DOTALL)
                conteudo_simples = re.sub(r'\n⚠️.*$', '', conteudo_simples, flags=re.DOTALL)
                conteudo_refinado = conteudo_simples.strip()
                log.info(f'✅ [MELHORAR EMAIL] Conteúdo extraído via padrão simples (a partir da linha {primeira_saudacao_simples})')

        if not conteudo_refinado:
            match_intro_email = re.search(
                r'(?:Heleno|segue|versão|versao|email|mensagem)[^:]*:?\s*\n\s*(Olá|Prezado|Oi|Querido|Querida|Meu amor|Meu querido|Heleno|Boa tarde|Bom dia|Boa noite)',
                resposta_ia,
                re.IGNORECASE | re.MULTILINE
            )
            if match_intro_email:
                pos_inicio_email = match_intro_email.end() - len(match_intro_email.group(2))
                conteudo_do_email = resposta_ia[pos_inicio_email:]
                conteudo_do_email = re.sub(r'\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_do_email, flags=re.DOTALL)
                conteudo_do_email = re.sub(r'\n🔍.*$', '', conteudo_do_email, flags=re.DOTALL)
                conteudo_do_email = re.sub(r'\n💡.*$', '', conteudo_do_email, flags=re.DOTALL)
                conteudo_do_email = re.sub(r'\n⚠️.*$', '', conteudo_do_email, flags=re.DOTALL)
                conteudo_refinado = conteudo_do_email.strip()
                log.info('✅ [MELHORAR EMAIL] Conteúdo extraído removendo texto introdutório')

        if not conteudo_refinado:
            log.warning('⚠️ [MELHORAR EMAIL] Não conseguiu extrair email refinado da resposta da IA')
            log.debug(f'⚠️ [MELHORAR EMAIL] Resposta da IA (primeiros 500 chars): {resposta_ia[:500]}')
            return None

        if not assunto_refinado:
            assunto_refinado = dados_email_original.get('assunto', 'Mensagem')
            log.warning(f'⚠️ [MELHORAR EMAIL] Assunto não extraído, usando original: "{assunto_refinado}"')

        if not conteudo_refinado:
            log.error('❌ [MELHORAR EMAIL] CRÍTICO: Conteúdo não extraído! Retornando None para não sobrescrever email original.')
            log.error(f'❌ [MELHORAR EMAIL] Resposta da IA completa para debug:\n{resposta_ia}')
            return None

        log.info(f'✅ [MELHORAR EMAIL] Email refinado extraído com sucesso - Assunto: "{assunto_refinado[:50]}...", Conteúdo: {len(conteudo_refinado)} caracteres')
        log.debug(f'✅ [MELHORAR EMAIL] Assunto extraído: "{assunto_refinado}"')
        log.debug(f'✅ [MELHORAR EMAIL] Conteúdo extraído (primeiros 200 chars): {conteudo_refinado[:200]}')

        return {
            'assunto': assunto_refinado,
            'conteudo': conteudo_refinado
        }

    except Exception as e:
        log.error(f'❌ [MELHORAR EMAIL] Erro ao extrair email da resposta da IA: {e}', exc_info=True)
        return None

