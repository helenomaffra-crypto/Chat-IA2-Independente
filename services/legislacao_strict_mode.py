"""
Modo Legislação Estrita - Respostas baseadas APENAS em trechos de legislação fornecidos
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

LEGISLACAO_STRICT_SYSTEM_PROMPT = """Você é um assistente especializado em LEGISLACAO ADUANEIRA BRASILEIRA.

Seu trabalho AGORA é responder SOMENTE com base nos trechos de legislação que serão fornecidos na mensagem do usuário.

REGRAS OBRIGATÓRIAS:

1) FONTES
- Você só pode usar como base os trechos de legislação que eu enviar abaixo.
- NÃO use conhecimento externo, lembranças genéricas ou "entendimento comum" do modelo.
- Se a pergunta exigir algo que NÃO está coberto claramente pelos trechos, diga explicitamente que não foi possível localizar a base legal exata.

2) COMO LER OS TRECHOS
- Cada trecho vem com: ATO (ex.: Decreto 6759/2009), ARTIGO, PARÁGRAFO, INCISO, e às vezes um CONTEXTO (título/capítulo).
- A legislação aduaneira frequentemente usa remissões do tipo:
  - "neste artigo",
  - "neste Capítulo",
  - "na forma do art. X",
  - "nos termos do § Y".
- Quando um trecho fizer referência a outro (ex.: "na forma do art. 18"), use também os outros trechos que mencionam esse artigo para montar o raciocínio.
- Se um artigo estiver dentro de um TÍTULO ou CAPÍTULO específico (ex.: "Das multas"), considere esse contexto para interpretar o alcance da norma.

3) FORMA DA RESPOSTA
Sempre que responder, siga esta estrutura:

1. VISÃO GERAL CURTA
   - Explique em 2–4 frases, em linguagem clara, qual é a ideia central da norma em relação à pergunta do usuário.

2. BASE LEGAL DETALHADA
   - Liste os artigos relevantes da forma:
     - Ato (sigla + número/ano) + artigo + parágrafo/inciso, e um resumo da regra.
   - Exemplo de formato:
     - Decreto 6759/2009, art. 87, caput: trata da forma de determinar o valor dos bens na bagagem, com base na fatura ou documento equivalente.
     - Decreto 6759/2009, art. 87, parágrafo único: prevê que, na falta do valor em fatura ou documento equivalente, a autoridade aduaneira pode fixar o valor com base em critérios gerais.

3. APLICAÇÃO AO CASO PERGUNTADO
   - Relacione explicitamente a pergunta do usuário com os dispositivos citados.
   - Se a pergunta for sobre "multas por fatura em desacordo", por exemplo:
     - indique quais artigos tratam de multa, infração ou consequências,
     - explique se a infração é formal ou material (quando isso for claro no texto),
     - deixe claro o que a legislação prevê (multa, perdimento, exigência de retificação etc.).

4. LIMITES DA RESPOSTA
   - Se o texto não trouxer todos os detalhes (por exemplo, cálculo exato da multa, percentuais, ou hipóteses muito específicas), deixe isso claro.
   - Use frases do tipo:
     - "Com base apenas nos trechos fornecidos, é possível afirmar que..."
     - "Os trechos fornecidos indicam que..."
     - "Não há informação suficiente nos trechos para detalhar X ou Y."

4) O QUE NÃO FAZER
- NÃO invente artigo, número, parágrafo ou percentual que não esteja nos trechos.
- NÃO cite "jurisprudência", "doutrina" ou "entendimento da fiscalização" se isso não estiver claramente nos trechos fornecidos.
- NÃO responda com frases genéricas do tipo "a legislação prevê" sem apontar pelo menos um ato + artigo.

5) CASOS EM QUE VOCÊ DEVE ADMITIR LIMITAÇÃO
- Se a pergunta for muito ampla e os trechos forem poucos ou muito indiretos, diga claramente que a resposta é limitada.
- Se os trechos não forem suficientes para responder com segurança, diga que "não foi possível localizar um dispositivo específico que trate de X" e, se fizer sentido, indique o artigo mais próximo, explicando a limitação.

Você SEMPRE deve priorizar fidelidade ao texto legal fornecido, mesmo que isso deixe a resposta menos completa."""


def montar_user_prompt_legislacao(pergunta_usuario: str, trechos: List[Dict[str, Any]]) -> str:
    """
    Monta o user prompt para modo legislação estrita.
    
    Args:
        pergunta_usuario: Pergunta do usuário
        trechos: Lista de dicts com trechos de legislação. Cada dict deve ter:
            - legislacao_info: dict com tipo_ato, numero, ano, sigla_orgao
            - referencia: str (ex: "Art. 87º", "Art. 87º, § 1º")
            - tipo_trecho: str (ex: "caput", "paragrafo", "inciso")
            - texto: str (texto do trecho)
            - texto_com_artigo: str (texto com contexto do artigo)
            - numero_artigo: int (número do artigo)
            - ordem: int (ordem na legislação)
    
    Returns:
        String formatada com pergunta + trechos
    """
    partes = []
    partes.append("PERGUNTA DO USUÁRIO:")
    partes.append(pergunta_usuario.strip())
    partes.append("")
    partes.append("TRECHOS DE LEGISLAÇÃO DISPONÍVEIS (use APENAS estes como base):")
    partes.append("")
    
    for i, t in enumerate(trechos, start=1):
        # Extrair informações da legislação
        leg_info = t.get('legislacao_info', {})
        tipo_ato = leg_info.get('tipo_ato', '')
        numero = leg_info.get('numero', '')
        ano = leg_info.get('ano', '')
        sigla_orgao = leg_info.get('sigla_orgao', '')
        
        # Montar identificação do ato
        ato_parts = [tipo_ato]
        if numero:
            ato_parts.append(str(numero))
        if ano:
            ato_parts.append(str(ano))
        ato = " ".join(ato_parts)
        if sigla_orgao:
            ato += f" ({sigla_orgao})"
        
        # Montar referência completa
        referencia = t.get('referencia', '')
        tipo_trecho = t.get('tipo_trecho', '')
        numero_artigo = t.get('numero_artigo')
        
        # Montar header
        header_parts = []
        if ato:
            header_parts.append(ato)
        if referencia:
            header_parts.append(referencia)
        elif numero_artigo:
            header_parts.append(f"Art. {numero_artigo}º")
        if tipo_trecho and tipo_trecho != 'caput':
            header_parts.append(f"({tipo_trecho})")
        
        header = " - ".join(header_parts) if header_parts else f"Trecho {i}"
        
        # Texto do trecho (usar texto_com_artigo se disponível para ter contexto)
        texto = t.get('texto_com_artigo', t.get('texto', '')).strip()
        
        partes.append(f"{i}. {header}")
        partes.append(f"   Texto: {texto}")
        partes.append("")
    
    partes.append(
        "INSTRUÇÃO FINAL: Responda à pergunta do usuário ANCORANDO-SE nesses trechos. "
        "Se não forem suficientes para responder com segurança, explique a limitação."
    )
    
    return "\n".join(partes)


def detectar_modo_estrito(mensagem: str) -> bool:
    """
    Detecta se a mensagem indica necessidade de modo legislação estrita.
    
    Padrões que indicam modo estrito:
    - "base legal", "qual artigo", "onde está previsto", "no Decreto", "na IN"
    - "artigo específico", "dispositivo legal", "norma que trata"
    - Perguntas diretas sobre legislação específica
    
    ⚠️ NÃO ativa para perguntas conceituais puras:
    - "o que é X?", "me explica X?", "o que significa X?" → NÃO é modo estrito
    
    Args:
        mensagem: Mensagem do usuário
    
    Returns:
        True se deve usar modo estrito, False caso contrário
    """
    mensagem_lower = mensagem.lower()
    
    # ✅ NOVO: Verificar se é pergunta conceitual PURA (não usar modo estrito)
    padroes_conceituais = [
        r'^o\s+que\s+é\s+',
        r'^me\s+explica\s+o\s+que\s+é\s+',
        r'^explique\s+o\s+que\s+é\s+',
        r'^o\s+que\s+significa\s+',
        r'^me\s+explica\s+o\s+que\s+significa\s+',
    ]
    
    import re
    for padrao in padroes_conceituais:
        if re.search(padrao, mensagem_lower):
            # Se é conceitual PURA (sem "base legal", "artigo", etc.), não usar modo estrito
            if not any(palavra in mensagem_lower for palavra in ['base legal', 'artigo', 'previsto', 'dispositivo', 'norma']):
                return False
    
    # Padrões que indicam modo estrito
    padroes_estrito = [
        'base legal',
        'qual artigo',
        'onde está previsto',
        'dispositivo legal',
        'norma que trata',
        'artigo específico',
        'no decreto',
        'na in',
        'na lei',
        'artigo que trata',
        'qual o artigo',
        'que artigo',
        'artigo prevê',
        'previsto no',
        'previsto na',
        'disposto no',
        'disposto na',
        'estabelecido no',
        'estabelecido na',
    ]
    
    # Verificar se contém algum padrão
    for padrao in padroes_estrito:
        if padrao in mensagem_lower:
            return True
    
    # Verificar se menciona legislação específica (ex: "Decreto 6759", "IN 680")
    padrao_legislacao = r'\b(IN|Decreto|Lei|Portaria)\s+\d+'
    if re.search(padrao_legislacao, mensagem, re.IGNORECASE):
        return True
    
    return False


def eh_pergunta_conceitual_pura(mensagem: str) -> bool:
    """
    Detecta se a pergunta é conceitual PURA (sem pedido de base legal).
    
    Exemplos:
    - "o que é perdimento?" → True
    - "me explica o que é multa?" → True
    - "o que significa abandono?" → True
    - "me explica perdimento e qual a base legal?" → False (mista)
    - "qual a base legal para perdimento?" → False (base legal)
    
    Args:
        mensagem: Mensagem do usuário
    
    Returns:
        True se é pergunta conceitual pura, False caso contrário
    """
    mensagem_lower = mensagem.lower()
    
    # Padrões de perguntas conceituais
    padroes_conceituais = [
        r'^o\s+que\s+é\s+',
        r'^me\s+explica\s+o\s+que\s+é\s+',
        r'^explique\s+o\s+que\s+é\s+',
        r'^o\s+que\s+significa\s+',
        r'^me\s+explica\s+o\s+que\s+significa\s+',
        r'^o\s+que\s+são\s+',
        r'^me\s+explica\s+',
        r'^explique\s+',
    ]
    
    import re
    for padrao in padroes_conceituais:
        if re.search(padrao, mensagem_lower):
            # Se contém palavras de base legal, NÃO é conceitual pura
            palavras_base_legal = ['base legal', 'artigo', 'previsto', 'dispositivo', 'norma', 'legislação', 'decreto', 'lei', 'in']
            if not any(palavra in mensagem_lower for palavra in palavras_base_legal):
                return True
    
    return False

