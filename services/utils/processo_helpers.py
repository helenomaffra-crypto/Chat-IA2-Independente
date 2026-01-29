"""
Helpers para detecção de tipos de perguntas relacionadas a processos.

Separa claramente:
- Perguntas de painel/visão geral (categoria, datas, status)
- Perguntas de processo específico (ALH.0001/25, MV5.0009/25)
- Follow-ups de processo ("e a DI?", "e a DUIMP?")
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def eh_pergunta_painel(mensagem_lower: str) -> bool:
    """
    Detecta se a mensagem é uma pergunta de painel/visão geral.
    
    Perguntas de painel NÃO devem usar processo_atual, pois são consultas
    de categoria, datas, status logístico, etc.
    
    Args:
        mensagem_lower: Mensagem em minúsculas
        
    Returns:
        True se for pergunta de painel, False caso contrário
    """
    mensagem_lower = mensagem_lower.strip()
    
    # Padrões de perguntas de painel/visão geral
    padroes_painel = [
        # Perguntas sobre "o que temos"
        r'\b(o\s+que\s+temos|o\s+que\s+tem|o\s+que\s+chegou|o\s+que\s+chega)',
        r'\b(o\s+que\s+temos\s+pra\s+hoje|o\s+que\s+tem\s+pra\s+hoje)',
        r'\b(o\s+que\s+chegou\s+hoje|o\s+que\s+chega\s+hoje)',
        r'\b(o\s+que\s+chega\s+semana|o\s+que\s+chega\s+essa\s+semana)',
        r'\b(o\s+que\s+chega\s+proxima\s+semana|o\s+que\s+chega\s+próxima\s+semana)',
        
        # Perguntas sobre categoria (sem processo específico)
        r'\b(como\s+est[aã]o?\s+os?\s+[a-z0-9]{2,4}\b)',  # "como estão os mv5", "como estão os alh"
        r'\b(como\s+est[aã]o?\s+as?\s+[a-z0-9]{2,4}\b)',  # "como estão as vdm"
        
        # Fechamento e resumos
        r'\b(fechamento\s+(?:do\s+)?dia|fechar\s+(?:o\s+)?dia)',
        r'\b(resumo\s+(?:do\s+)?dia|resumo\s+das?\s+movimenta[cç][oõ]es?)',
        
        # Painel e dashboard
        r'\b(painel|dashboard)',
        r'\b(painel\s+de\s+chegadas|dashboard\s+de\s+chegadas)',
        
        # Listagens gerais
        r'\b(lista\s+de\s+processos|listar\s+processos)',
        r'\b(processos\s+com\s+eta|processos\s+por\s+status)',
        
        # Perguntas sobre chegadas/ETAs
        r'\b(o\s+que\s+chega|o\s+que\s+chegou)',
        r'\b(chegadas\s+de\s+hoje|chegadas\s+da\s+semana)',
        r'\b(eta\s+de\s+hoje|eta\s+da\s+semana)',
    ]
    
    # Verificar se algum padrão bate
    for padrao in padroes_painel:
        if re.search(padrao, mensagem_lower):
            logger.debug(f"[PROCESSO_HELPER] Pergunta de painel detectada: '{mensagem_lower}' (padrão: {padrao})")
            return True
    
    # Verificar palavras-chave específicas de painel
    palavras_painel = [
        'o que temos pra hoje',
        'o que tem pra hoje',
        'o que chegou hoje',
        'o que chega hoje',
        'o que chega semana',
        'fechamento do dia',
        'fechar o dia',
        'resumo do dia',
        'painel',
        'dashboard',
    ]
    
    for palavra in palavras_painel:
        if palavra in mensagem_lower:
            logger.debug(f"[PROCESSO_HELPER] Pergunta de painel detectada: '{mensagem_lower}' (palavra-chave: {palavra})")
            return True
    
    return False


def eh_pergunta_conceitual(mensagem_lower: str) -> bool:
    """
    Detecta se a mensagem é uma pergunta conceitual sobre um documento/processo.
    
    Perguntas conceituais são aquelas que pedem explicação sobre o que é algo,
    não consultas sobre um processo específico.
    
    Exemplos que DEVEM retornar True:
    - "vc sabe o que é uma DI?"
    - "o que é um CE?"
    - "o que é uma DUIMP?"
    - "o que significa CCT?"
    - "definição de DI"
    - "explique o que é uma declaração de importação"
    
    Exemplos que NÃO devem retornar True:
    - "qual a DI do processo X?" (consulta específica)
    - "situação da DI" (consulta sobre DI específica)
    - "e a DI?" (follow-up de processo)
    
    Args:
        mensagem_lower: Mensagem em minúsculas
    
    Returns:
        True se for pergunta conceitual, False caso contrário
    """
    mensagem_lower = mensagem_lower.strip()
    
    # Padrões que indicam pergunta conceitual
    padroes_conceituais = [
        r'\bo\s+que\s+é\s+(?:uma?\s+)?(?:di|duimp|ce|cct|declara[çc][aã]o|conhecimento)',
        r'\bo\s+que\s+significa\s+(?:di|duimp|ce|cct)',
        r'\b(?:vc|você|voce)\s+(?:sabe|conhece)\s+o\s+que\s+é',
        r'\bdefini[çc][aã]o\s+(?:de|da|do)\s+(?:di|duimp|ce|cct)',
        r'\bexplique\s+o\s+que\s+é',
        r'\b(?:me\s+)?explique\s+(?:o\s+que\s+é|sobre)\s+(?:uma?\s+)?(?:di|duimp|ce|cct)',
        r'\b(?:o\s+que\s+é|o\s+que\s+significa)\s+(?:uma?\s+)?(?:di|duimp|ce|cct)',
    ]
    
    for padrao in padroes_conceituais:
        if re.search(padrao, mensagem_lower, re.IGNORECASE):
            return True
    
    # Verificar se menciona documento mas é pergunta conceitual (não consulta)
    menciona_documento = bool(re.search(r'\b(di|duimp|ce|cct)\b', mensagem_lower, re.IGNORECASE))
    eh_pergunta_sobre = bool(re.search(r'\b(?:o\s+que|o\s+que\s+é|o\s+que\s+significa|defini[çc][aã]o|explique)\b', mensagem_lower, re.IGNORECASE))
    
    # Se menciona documento E é pergunta sobre (não consulta), é conceitual
    if menciona_documento and eh_pergunta_sobre:
        # Verificar se NÃO é consulta específica (não tem número, não tem "do processo", etc.)
        nao_tem_numero = not re.search(r'\d{10,15}', mensagem_lower)  # Não tem número de DI/CE
        nao_tem_processo = not re.search(r'(?:do|da)\s+processo|processo\s+[a-z0-9]', mensagem_lower, re.IGNORECASE)  # Não menciona "do processo"
        nao_tem_situacao = not re.search(r'situa[çc][aã]o|status|dados|informa[çc][oõ]es', mensagem_lower, re.IGNORECASE)  # Não pede situação/dados
        
        if nao_tem_numero and nao_tem_processo and nao_tem_situacao:
            return True
    
    return False


def eh_followup_processo(mensagem_lower: str) -> bool:
    """
    Detecta se a mensagem é um follow-up claro sobre um processo.
    
    Follow-ups são perguntas curtas que dependem do contexto de processo_atual,
    como "e a DI?", "e a DUIMP?", "situação dele?", etc.
    
    Args:
        mensagem_lower: Mensagem em minúsculas
        
    Returns:
        True se for follow-up de processo, False caso contrário
    """
    mensagem_lower = mensagem_lower.strip()
    
    # Follow-ups são geralmente mensagens curtas
    if len(mensagem_lower) > 100:
        return False
    
    # Padrões de follow-up (mais específicos primeiro)
    # "e a DI?", "e a DUIMP?", "e o CE?", "e a CCT?"
    if re.match(r'^\s*e\s+(?:a|o|as?|os?)\s+(di|duimp|ce|cct)\s*\??\s*$', mensagem_lower, re.IGNORECASE):
        logger.debug(f"[PROCESSO_HELPER] Follow-up de processo detectado: '{mensagem_lower}' (padrão: e a/o documento)")
        return True
    
    # "e a situação?", "e a situação dele?", "situação dele?"
    if re.match(r'^\s*(e\s+(?:a|o)\s+)?(situa[cç][aã]o|status|detalhe)\s*(?:dele|dela|desse|dessa)?\s*\??\s*$', mensagem_lower):
        logger.debug(f"[PROCESSO_HELPER] Follow-up de processo detectado: '{mensagem_lower}' (padrão: situação)")
        return True
    
    # "e como está?", "como está esse?", "como está ele?"
    if re.match(r'^\s*(e\s+)?como\s+est[aã]o?\s*(?:ele|ela|esse|essa)?\s*\??\s*$', mensagem_lower):
        logger.debug(f"[PROCESSO_HELPER] Follow-up de processo detectado: '{mensagem_lower}' (padrão: como está)")
        return True
    
    # "e qual a situação?", "qual a situação?"
    if re.match(r'^\s*(e\s+)?qual\s+(?:a|o)\s+(?:situa[cç][aã]o|status)\s*\??\s*$', mensagem_lower):
        logger.debug(f"[PROCESSO_HELPER] Follow-up de processo detectado: '{mensagem_lower}' (padrão: qual situação)")
        return True
    
    # "e a DI, como está?", "e a DUIMP, qual a situação?"
    if re.search(r'^\s*e\s+(?:a|o)\s+(di|duimp|ce|cct)\s*,?\s*(?:como\s+est[aã]o?|qual\s+(?:a|o)\s+situa[cç][aã]o)\s*\??\s*$', mensagem_lower, re.IGNORECASE):
        logger.debug(f"[PROCESSO_HELPER] Follow-up de processo detectado: '{mensagem_lower}' (padrão: e a/o documento, como está)")
        return True
    
    # "qual a situação da DI?", "qual a situação do CE?"
    if re.search(r'^\s*qual\s+(?:a|o)\s+(?:situa[cç][aã]o|status)\s+(?:da|do|das?|dos?)\s+(di|duimp|ce|cct)\s*\??\s*$', mensagem_lower, re.IGNORECASE):
        logger.debug(f"[PROCESSO_HELPER] Follow-up de processo detectado: '{mensagem_lower}' (padrão: qual situação da/o documento)")
        return True
    
    # Verificar se menciona documento específico sem processo explícito
    # Padrão mais flexível para capturar variações
    menciona_documento = bool(re.search(r'\b(di|duimp|ce|cct)\b', mensagem_lower, re.IGNORECASE))
    eh_curta = len(mensagem_lower) <= 50  # Aumentado para 50 para capturar mais variações
    termina_interrogacao = mensagem_lower.endswith('?')
    comeca_com_e = mensagem_lower.startswith('e ') or mensagem_lower.startswith('e,')
    
    # Se menciona documento, é curta e começa com "e" ou termina com "?", é provável follow-up
    if menciona_documento and eh_curta and (termina_interrogacao or comeca_com_e):
        logger.debug(f"[PROCESSO_HELPER] Possível follow-up de processo detectado: '{mensagem_lower}'")
        return True
    
    return False

