"""
Utilitário para formatar texto para TTS (Text-to-Speech).

Converte referências de processos (ex: ALH.0166/25) em texto falável
seguindo as regras de negócio:
- Não diz "ponto" (usuário acostumado a ALH0166)
- Não diz "barra" e ano se for o ano atual
- Só menciona ano se for ano anterior ao vigente
"""
import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def formatar_processo_para_tts(processo_referencia: str, ano_atual: Optional[int] = None) -> str:
    """
    Converte referência de processo para texto falável em TTS.
    
    Regras conforme especificação:
    - Soletrar letras individualmente: "ALH" → "A L H"
    - Dígitos por extenso: "0168" → "zero um seis oito"
    - Sempre mencionar ano com "barra": "/25" → "barra dois cinco"
    
    Args:
        processo_referencia: Referência do processo (ex: "ALH.0168/25", "VDM.0001/24")
        ano_atual: Ano atual (ignorado - sempre menciona o ano)
        
    Returns:
        Texto formatado para TTS (ex: "A L H zero um seis oito barra dois cinco")
    
    Exemplos:
        >>> formatar_processo_para_tts("ALH.0168/25", 2025)
        "A L H zero um seis oito barra dois cinco"
        
        >>> formatar_processo_para_tts("ALH.0166/24", 2025)
        "A L H zero um seis seis barra dois quatro"
    """
    if not processo_referencia or not processo_referencia.strip():
        return ""
    
    # Normalizar entrada
    processo = processo_referencia.strip().upper()
    
    # Padrão: CATEGORIA.NUMERO/ANO
    # Exemplos: ALH.0168/25, VDM.0001/24, MV5.0022/25
    padrao = r'^([A-Z0-9]+)\.(\d{4})/(\d{2})$'
    match = re.match(padrao, processo)
    
    if not match:
        # Tentar padrão alternativo sem ponto
        padrao_alt = r'^([A-Z0-9]+)(\d{4})/(\d{2})$'
        match = re.match(padrao_alt, processo)
    
    if not match:
        # Se não matchar o padrão, retornar como está
        logger.warning(f"⚠️ Formato de processo não reconhecido: {processo_referencia}")
        return processo_referencia
    
    categoria = match.group(1)  # ALH, VDM, etc.
    numero = match.group(2)     # 0168, 0001, etc.
    ano_str = match.group(3)    # 25, 24, etc.
    
    # Soletrar letras individualmente: "ALH" → "A L H"
    categoria_soletrada = " ".join([c for c in categoria])
    
    # Converter número para extenso (dígito por dígito)
    numero_extenso = " ".join([_digito_para_extenso(d) for d in numero])
    
    # Converter ano para extenso (dígito por dígito)
    ano_extenso = " ".join([_digito_para_extenso(d) for d in ano_str])
    
    # Sempre mencionar o ano com "barra"
    texto = f"{categoria_soletrada} {numero_extenso} barra {ano_extenso}"
    
    return texto.strip()


def _letra_para_portugues(letra: str) -> str:
    """
    Converte uma letra para pronúncia em português.
    Isso força o TTS a pronunciar as letras em português, não em inglês.
    """
    letras_portugues = {
        'A': 'á',  # "á" ao invés de "ei" (inglês)
        'B': 'bê',
        'C': 'cê',
        'D': 'dê',
        'E': 'é',  # "é" ao invés de "i" (inglês)
        'F': 'éfe',
        'G': 'gê',
        'H': 'agá',
        'I': 'í',
        'J': 'jota',
        'K': 'cá',
        'L': 'éle',
        'M': 'éme',
        'N': 'éne',
        'O': 'ó',  # "ó" ao invés de "ou" (inglês)
        'P': 'pê',
        'Q': 'quê',
        'R': 'érre',
        'S': 'ésse',
        'T': 'tê',
        'U': 'ú',
        'V': 'vê',
        'W': 'dáblio',
        'X': 'xis',
        'Y': 'ípsilon',
        'Z': 'zê'
    }
    # Se for número, retornar como está
    if letra.isdigit():
        return letra
    # Retornar pronúncia em português (maiúscula ou minúscula)
    return letras_portugues.get(letra.upper(), letra)


def _digito_para_extenso(digito: str) -> str:
    """Converte um dígito (0-9) para extenso."""
    digitos = {
        '0': 'zero',
        '1': 'um',
        '2': 'dois',
        '3': 'três',
        '4': 'quatro',
        '5': 'cinco',
        '6': 'seis',
        '7': 'sete',
        '8': 'oito',
        '9': 'nove'
    }
    return digitos.get(digito, digito)


def _formatar_data_para_tts(data_str: str) -> str:
    """
    Formata data para TTS em formato falável.
    
    Converte datas como "15/12/25" ou "15/12/2025" para "dia quinze de dezembro"
    (sem mencionar o ano).
    
    Args:
        data_str: Data no formato DD/MM/YY ou DD/MM/YYYY
        
    Returns:
        Data formatada para TTS (ex: "dia quinze de dezembro")
    """
    # Padrões de data: DD/MM/YY ou DD/MM/YYYY
    padrao_data = r'(\d{1,2})/(\d{1,2})/(\d{2,4})'
    match = re.match(padrao_data, data_str.strip())
    
    if not match:
        return data_str  # Retornar como está se não for data válida
    
    dia = int(match.group(1))
    mes = int(match.group(2))
    # ano = match.group(3)  # Não usar o ano
    
    # Nomes dos meses
    meses = [
        '', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
    ]
    
    if mes < 1 or mes > 12:
        return data_str  # Mês inválido, retornar como está
    
    # Converter dia para extenso
    dia_extenso = _numero_para_extenso(dia)
    mes_nome = meses[mes]
    
    # Retornar "dia X de Y" (sem ano)
    return f"dia {dia_extenso} de {mes_nome}"


def _formatar_data_hora_para_tts(data_hora_str: str) -> str:
    """
    Formata data e hora para TTS em formato falável.
    
    Converte datas com hora como "15/12/25 14:30" para "dia quinze de dezembro às quatorze horas e trinta"
    (sem mencionar o ano).
    
    Args:
        data_hora_str: Data e hora no formato DD/MM/YY HH:MM ou DD/MM/YYYY HH:MM
        
    Returns:
        Data e hora formatada para TTS
    """
    # Padrão: DD/MM/YY HH:MM ou DD/MM/YYYY HH:MM
    padrao_data_hora = r'(\d{1,2})/(\d{1,2})/(\d{2,4})\s+(\d{1,2}):(\d{2})'
    match = re.match(padrao_data_hora, data_hora_str.strip())
    
    if not match:
        # Tentar apenas data (sem hora)
        return _formatar_data_para_tts(data_hora_str)
    
    dia = int(match.group(1))
    mes = int(match.group(2))
    hora = int(match.group(4))
    minuto = int(match.group(5))
    
    # Nomes dos meses
    meses = [
        '', 'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
        'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
    ]
    
    if mes < 1 or mes > 12:
        return data_hora_str  # Mês inválido
    
    # Converter para extenso
    dia_extenso = _numero_para_extenso(dia)
    mes_nome = meses[mes]
    hora_extenso = _numero_para_extenso(hora)
    minuto_extenso = _numero_para_extenso(minuto)
    
    # Formatar hora
    if minuto == 0:
        hora_formatada = f"{hora_extenso} horas"
    else:
        hora_formatada = f"{hora_extenso} horas e {minuto_extenso}"
    
    # Retornar "dia X de Y às Z horas"
    return f"dia {dia_extenso} de {mes_nome} às {hora_formatada}"


def _numero_para_extenso(numero: int) -> str:
    """
    Converte um número (ex: 2025, 24) para extenso.
    Versão simplificada para anos (usa apenas os 2 últimos dígitos).
    """
    # Para anos, usar apenas os 2 últimos dígitos (2024 → "vinte e quatro", não "dois mil vinte e quatro")
    if numero >= 2000:
        # Pegar apenas os 2 últimos dígitos
        numero = numero % 100
    
    if numero < 20:
        unidades = ['zero', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 
                   'oito', 'nove', 'dez', 'onze', 'doze', 'treze', 'quatorze', 
                   'quinze', 'dezesseis', 'dezessete', 'dezoito', 'dezenove']
        return unidades[numero]
    
    # Para números de 20 a 99
    dezena = numero // 10
    unidade = numero % 10
    
    dezenas = ['', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 
              'sessenta', 'setenta', 'oitenta', 'noventa']
    
    if unidade == 0:
        return dezenas[dezena]
    else:
        return f"{dezenas[dezena]} e {_numero_para_extenso(unidade)}"


def _formatar_siglas_para_tts(texto: str) -> str:
    """
    Detecta e formata siglas conhecidas para soletração em português.
    
    Args:
        texto: Texto a formatar
        
    Returns:
        Texto com siglas soletradas em português
    """
    # Dicionário de siglas conhecidas que devem ser soletradas
    # Formato: SIGLA -> "letra1 letra2 letra3..." (nomes das letras em português)
    # ✅ CORREÇÃO: DUIMP é uma palavra (duimpê), não sigla soletrada
    # ✅ MELHORIA: Adicionar vírgulas entre letras para melhor clareza no TTS
    siglas_conhecidas = {
        # Documentos de COMEX
        'AFRMM': 'á, éfe, érre, éme, éme',  # Adicional ao Frete para Renovação da Marinha Mercante
        'DI': 'dê í',  # Declaração de Importação
        'DTA': 'dê tê á',  # Declaração de Trânsito Aduaneiro
        'CE': 'cê é',  # Conhecimento de Embarque
        'CCT': 'cê cê tê',  # Conhecimento de Carga Aérea
        'DUIMP': 'duimpê',  # Declaração Única de Importação (palavra, não sigla)
        'LPCO': 'éle pê cê ó',  # Licença de Processamento em Consignação
        'NESH': 'éne é ésse agá',  # Nota Explicativa do Sistema Harmonizado
        'RUC': 'érre ú cê',  # Remessa Única de Carga (CCT aéreo)
        'AWB': 'á dáblio bê',  # Air Waybill (CCT aéreo)
        
        # Impostos e Tributos
        'ICMS': 'í cê éme ésse',  # Imposto sobre Circulação de Mercadorias e Serviços
        'II': 'í í',  # Imposto de Importação
        'IPI': 'í pê í',  # Imposto sobre Produtos Industrializados
        'PIS': 'pê í ésse',  # Programa de Integração Social
        'COFINS': 'cê ó éfe í éne ésse',  # Contribuição para o Financiamento da Seguridade Social
        
        # Classificação Fiscal
        'NCM': 'éne cê éme',  # Nomenclatura Comum do Mercosul
        
        # Documentos Pessoais
        'CNPJ': 'cê éne pê jota',  # Cadastro Nacional da Pessoa Jurídica
        'CPF': 'cê pê éfe',  # Cadastro de Pessoa Física
        
        # Tecnologia
        'API': 'á pê í',  # Application Programming Interface
        'PDF': 'pê dê éfe',  # Portable Document Format
        'JSON': 'jota ésse ó éne',  # JavaScript Object Notation
        'XML': 'xis éme éle',  # eXtensible Markup Language
        'HTTP': 'agá tê tê pê',  # Hypertext Transfer Protocol
        'HTTPS': 'agá tê tê pê ésse',  # Hypertext Transfer Protocol Secure
        'URL': 'ú érre éle',  # Uniform Resource Locator
        
        # Países e Regiões
        'BR': 'bê érre',  # Brasil
        'USA': 'ú ésse á',  # United States of America
        'EUA': 'é ú á',  # Estados Unidos da América
        
        # Outros
        'ETA': 'eta',  # Estimated Time of Arrival (tratado como palavra)
        'BL': 'bê éle',  # Bill of Lading
        'FOB': 'éfe ó bê',  # Free On Board
        'CIF': 'cê í éfe',  # Cost, Insurance and Freight
    }
    
    texto_formatado = texto
    
    # Substituir siglas conhecidas (case-insensitive, mas preservar contexto)
    # Usar \b para garantir que é palavra completa (não parte de outra)
    for sigla, soletracao in siglas_conhecidas.items():
        # Padrão: palavra completa (não parte de outra palavra)
        # Ex: "AFRMM" mas não "AFRMM123" ou "XAFRMM"
        padrao = r'\b' + re.escape(sigla) + r'\b'
        texto_formatado = re.sub(padrao, soletracao, texto_formatado, flags=re.IGNORECASE)
    
    # ✅ NOVO: Tratar ETA como palavra em português "eta" (não sigla)
    # Substituir "ETA" isolado por "eta" em minúsculas
    texto_formatado = re.sub(r'\bETA\b', 'eta', texto_formatado, flags=re.IGNORECASE)
    
    # ✅ NOVO: Tratar DUIMP como palavra "duimpê" (não sigla soletrada)
    # Substituir "DUIMP" isolado por "duimpê"
    texto_formatado = re.sub(r'\bDUIMP\b', 'duimpê', texto_formatado, flags=re.IGNORECASE)
    
    return texto_formatado


def preparar_texto_tts(texto: str) -> str:
    """
    Prepara texto completo para TTS seguindo as regras especificadas.
    
    Regras:
    - Códigos de processo: "ALH.0168/25" → "A L H zero um seis oito barra dois cinco"
    - ETA: "ETA" → "eta" (palavra em português)
    - Adapta datas e números para forma falada quando fizer sentido
    
    Args:
        texto: Texto bruto da notificação
        
    Returns:
        Texto formatado para TTS
    """
    texto_formatado = texto
    
    # 1. Substituir códigos de processo no formato [A-Z]{3}\.\d{4}/\d{2}
    padrao_processo = r'\b([A-Z]{3})\.(\d{4})/(\d{2})\b'
    
    def substituir_processo(match):
        categoria = match.group(1)  # ALH
        numero = match.group(2)     # 0168
        ano = match.group(3)        # 25
        
        # Soletrar letras: "ALH" → "A L H"
        categoria_soletrada = " ".join([c for c in categoria])
        
        # Dígitos por extenso: "0168" → "zero um seis oito"
        numero_extenso = " ".join([_digito_para_extenso(d) for d in numero])
        
        # Ano por extenso: "25" → "dois cinco"
        ano_extenso = " ".join([_digito_para_extenso(d) for d in ano])
        
        return f"{categoria_soletrada} {numero_extenso} barra {ano_extenso}"
    
    texto_formatado = re.sub(padrao_processo, substituir_processo, texto_formatado)
    
    # 2. ✅ NOVO: Formatar datas antes de outras transformações
    # Formatar datas com hora primeiro (mais específico)
    # Padrão: DD/MM/YY HH:MM ou DD/MM/YYYY HH:MM (com espaços ao redor ou no início/fim)
    padrao_data_hora = r'(?<![0-9/])(\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2})(?![0-9/:])'
    def substituir_data_hora(match):
        try:
            return _formatar_data_hora_para_tts(match.group(1))
        except:
            return match.group(1)  # Se der erro, retornar original
    texto_formatado = re.sub(padrao_data_hora, substituir_data_hora, texto_formatado)
    
    # Formatar datas simples (DD/MM/YY ou DD/MM/YYYY)
    # Padrão: DD/MM/YY ou DD/MM/YYYY (não parte de outro número)
    padrao_data = r'(?<![0-9/])(\d{1,2}/\d{1,2}/\d{2,4})(?![0-9/])'
    def substituir_data(match):
        try:
            return _formatar_data_para_tts(match.group(1))
        except:
            return match.group(1)  # Se der erro, retornar original
    texto_formatado = re.sub(padrao_data, substituir_data, texto_formatado)
    
    # 3. Substituir "ETA" isolado por "eta" (palavra em português)
    texto_formatado = re.sub(r'\bETA\b', 'eta', texto_formatado, flags=re.IGNORECASE)
    
    # 4. Formatar siglas conhecidas
    texto_formatado = _formatar_siglas_para_tts(texto_formatado)
    
    # 5. Converter status em maiúsculas para formato falável
    # ✅ CORREÇÃO: Preservar grafia original (com ou sem ç)
    # Se vier "DESEMBARACADA" (sem ç), falar "desembaracada" (sem ç)
    # Se vier "DESEMBARAÇADA" (com ç), falar "desembaraçada" (com ç)
    # ✅ IMPORTANTE: Tratar também quando vem com underscore (ex: DESEMBARACADA_AGUARDANDO_PENDENCIA)
    
    # Primeiro, tratar status completos com underscore
    status_completos = {
        'VINCULADA_A_DOCUMENTO_DE_DESPACHO': 'vinculada a documento de despacho',
        'DESEMBARACADA_AGUARDANDO_PENDENCIA': 'desembaracada aguardando pendência',
        'DESEMBARAÇADA_AGUARDANDO_PENDENCIA': 'desembaraçada aguardando pendência',
        'DESEMBARACADA_CARGA_ENTREGUE': 'desembaracada carga entregue',
        'DESEMBARAÇADA_CARGA_ENTREGUE': 'desembaraçada carga entregue',
    }
    for status_upper, status_lower in status_completos.items():
        padrao = r'\b' + re.escape(status_upper) + r'\b'
        texto_formatado = re.sub(padrao, status_lower, texto_formatado, flags=re.IGNORECASE)
    
    # Depois, tratar status simples (palavras isoladas)
    status_importantes = {
        'ENTREGUE': 'entregue',
        'ARMAZENADA': 'armazenada',
        'DESCARREGADA': 'descarregada',
        'MANIFESTADA': 'manifestada',
        # ✅ CORREÇÃO: Tratar ambas as variações (com e sem ç)
        'DESEMBARACADA': 'desembaracada',  # Sem ç (como vem da API)
        'DESEMBARAÇADA': 'desembaraçada',  # Com ç (se aparecer)
        'DESEMBARACADO': 'desembaracado',  # Sem ç
        'DESEMBARAÇADO': 'desembaraçado',  # Com ç
    }
    for status_upper, status_lower in status_importantes.items():
        padrao = r'\b' + re.escape(status_upper) + r'\b'
        texto_formatado = re.sub(padrao, status_lower, texto_formatado, flags=re.IGNORECASE)
    
    # 6. Adicionar pausas estratégicas para melhorar clareza
    texto_formatado = re.sub(r'\b(Antes|Agora):\s*', r'\1: , ', texto_formatado, flags=re.IGNORECASE)
    texto_formatado = re.sub(r'\.\s+([A-ZÁÉÍÓÚ])', r'. , \1', texto_formatado)
    
    return texto_formatado.strip()


def formatar_texto_notificacao_para_tts(titulo: str, mensagem: str, processo_referencia: Optional[str] = None) -> str:
    """
    Formata texto completo de notificação para TTS.
    
    Substitui referências de processos no texto por versões faláveis.
    Formata siglas conhecidas para soletração em português.
    
    Args:
        titulo: Título da notificação
        mensagem: Mensagem da notificação
        processo_referencia: Referência do processo (opcional, para garantir formatação)
        
    Returns:
        Texto formatado para TTS
    """
    texto_completo = f"{titulo}. {mensagem}"
    
    # Usar a função preparar_texto_tts que segue as regras especificadas
    texto_formatado = preparar_texto_tts(texto_completo)
    
    return texto_formatado


# Testes unitários (executar com: python -m pytest ou python -c "from utils.tts_text_formatter import *; ...")
if __name__ == "__main__":
    # Testes
    print("🧪 Testando formatar_processo_para_tts()...")
    print()
    
    # Teste 1: Processo com ano (sempre menciona ano)
    resultado1 = formatar_processo_para_tts("ALH.0168/25")
    print(f"✅ ALH.0168/25 → '{resultado1}'")
    assert resultado1 == "A L H zero um seis oito barra dois cinco", f"Esperado 'A L H zero um seis oito barra dois cinco', obtido '{resultado1}'"
    
    # Teste 2: Processo do ano anterior (sempre menciona ano)
    resultado2 = formatar_processo_para_tts("ALH.0166/24")
    print(f"✅ ALH.0166/24 → '{resultado2}'")
    assert "barra" in resultado2 and "dois quatro" in resultado2
    
    # Teste 3: Processo com zeros à esquerda
    resultado3 = formatar_processo_para_tts("MV5.0001/25")
    print(f"✅ MV5.0001/25 → '{resultado3}'")
    assert "zero zero zero um" in resultado3 and "barra dois cinco" in resultado3
    
    print()
    print("🧪 Testando preparar_texto_tts()...")
    print()
    
    # Teste 4: ETA
    texto_eta = "ETA atualizado. ETA Anterior: 11/11/2025"
    resultado4 = preparar_texto_tts(texto_eta)
    print(f"✅ ETA → '{resultado4}'")
    assert "eta atualizado" in resultado4.lower() and "eta Anterior" in resultado4
    
    # Teste 5: Exemplo completo
    texto_completo = "ALH.0168/25: ETA atualizado"
    resultado5 = preparar_texto_tts(texto_completo)
    print(f"✅ Exemplo completo → '{resultado5}'")
    assert "A L H zero um seis oito barra dois cinco" in resultado5
    assert "eta atualizado" in resultado5.lower()
    
    print()
    print("✅ Todos os testes passaram!")

