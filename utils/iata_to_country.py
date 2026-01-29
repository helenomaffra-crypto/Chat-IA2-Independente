"""
Utilitário para converter código IATA de aeroporto para código de país ISO 3166-1 alpha-2.

Exemplos:
- MIA (Miami) → US (Estados Unidos)
- GRU (Guarulhos) → BR (Brasil)
- PEK (Pequim) → CN (China)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Mapeamento de códigos IATA de aeroportos para códigos de país ISO 3166-1 alpha-2
# Baseado nos principais aeroportos internacionais
IATA_TO_COUNTRY = {
    # Estados Unidos
    'MIA': 'US',  # Miami
    'JFK': 'US',  # New York - John F. Kennedy
    'LAX': 'US',  # Los Angeles
    'ORD': 'US',  # Chicago O'Hare
    'DFW': 'US',  # Dallas/Fort Worth
    'ATL': 'US',  # Atlanta
    'SFO': 'US',  # San Francisco
    'SEA': 'US',  # Seattle
    'BOS': 'US',  # Boston
    'IAD': 'US',  # Washington Dulles
    'EWR': 'US',  # Newark
    'MSP': 'US',  # Minneapolis
    'DTW': 'US',  # Detroit
    'PHL': 'US',  # Philadelphia
    'CLT': 'US',  # Charlotte
    'DEN': 'US',  # Denver
    'IAH': 'US',  # Houston
    'PHX': 'US',  # Phoenix
    
    # Brasil
    'GRU': 'BR',  # Guarulhos (São Paulo)
    'GIG': 'BR',  # Galeão (Rio de Janeiro)
    'BSB': 'BR',  # Brasília
    'CGH': 'BR',  # Congonhas (São Paulo)
    'SDU': 'BR',  # Santos Dumont (Rio de Janeiro)
    'POA': 'BR',  # Porto Alegre
    'CWB': 'BR',  # Curitiba
    'REC': 'BR',  # Recife
    'FOR': 'BR',  # Fortaleza
    'SSA': 'BR',  # Salvador
    'BEL': 'BR',  # Belém
    'MAO': 'BR',  # Manaus
    'VCP': 'BR',  # Viracopos (Campinas)
    
    # China
    'PEK': 'CN',  # Pequim Capital
    'PVG': 'CN',  # Shanghai Pudong
    'CAN': 'CN',  # Guangzhou
    'SZX': 'CN',  # Shenzhen
    'CTU': 'CN',  # Chengdu
    'SIA': 'CN',  # Xi'an
    'KMG': 'CN',  # Kunming
    'HGH': 'CN',  # Hangzhou
    
    # Alemanha
    'FRA': 'DE',  # Frankfurt
    'MUC': 'DE',  # Munich
    'HAM': 'DE',  # Hamburg
    'BER': 'DE',  # Berlin
    'DUS': 'DE',  # Düsseldorf
    
    # Reino Unido
    'LHR': 'GB',  # London Heathrow
    'LGW': 'GB',  # London Gatwick
    'MAN': 'GB',  # Manchester
    'EDI': 'GB',  # Edinburgh
    
    # França
    'CDG': 'FR',  # Paris Charles de Gaulle
    'ORY': 'FR',  # Paris Orly
    'LYS': 'FR',  # Lyon
    
    # Espanha
    'MAD': 'ES',  # Madrid
    'BCN': 'ES',  # Barcelona
    
    # Itália
    'FCO': 'IT',  # Rome Fiumicino
    'MXP': 'IT',  # Milan Malpensa
    
    # Holanda
    'AMS': 'NL',  # Amsterdam
    
    # Suíça
    'ZRH': 'CH',  # Zurich
    
    # Emirados Árabes Unidos
    'DXB': 'AE',  # Dubai
    'AUH': 'AE',  # Abu Dhabi
    
    # Qatar
    'DOH': 'QA',  # Doha
    
    # Turquia
    'IST': 'TR',  # Istanbul
    
    # Rússia
    'SVO': 'RU',  # Moscow Sheremetyevo
    'DME': 'RU',  # Moscow Domodedovo
    
    # Japão
    'NRT': 'JP',  # Tokyo Narita
    'HND': 'JP',  # Tokyo Haneda
    'KIX': 'JP',  # Osaka Kansai
    
    # Coreia do Sul
    'ICN': 'KR',  # Seoul Incheon
    
    # Singapura
    'SIN': 'SG',  # Singapore
    
    # Tailândia
    'BKK': 'TH',  # Bangkok
    
    # Índia
    'DEL': 'IN',  # Delhi
    'BOM': 'IN',  # Mumbai
    
    # Austrália
    'SYD': 'AU',  # Sydney
    'MEL': 'AU',  # Melbourne
    
    # Canadá
    'YYZ': 'CA',  # Toronto
    'YVR': 'CA',  # Vancouver
    'YUL': 'CA',  # Montreal
    
    # México
    'MEX': 'MX',  # Mexico City
    'CUN': 'MX',  # Cancún
    
    # Argentina
    'EZE': 'AR',  # Buenos Aires Ezeiza
    'AEP': 'AR',  # Buenos Aires Aeroparque
    
    # Chile
    'SCL': 'CL',  # Santiago
    
    # Colômbia
    'BOG': 'CO',  # Bogotá
    
    # Peru
    'LIM': 'PE',  # Lima
    
    # Panamá
    'PTY': 'PA',  # Panama City
    
    # Outros importantes
    'JNB': 'ZA',  # Johannesburg (África do Sul)
    'CAI': 'EG',  # Cairo (Egito)
    'DME': 'RU',  # Moscow Domodedovo (Rússia)
}


def iata_to_country_code(iata_code: str) -> Optional[str]:
    """
    Converte código IATA de aeroporto para código de país ISO 3166-1 alpha-2.
    
    Args:
        iata_code: Código IATA do aeroporto (ex: 'MIA', 'GRU', 'PEK')
    
    Returns:
        Código de país ISO 3166-1 alpha-2 (ex: 'US', 'BR', 'CN') ou None se não encontrado
    
    Examples:
        >>> iata_to_country_code('MIA')
        'US'
        >>> iata_to_country_code('GRU')
        'BR'
        >>> iata_to_country_code('PEK')
        'CN'
        >>> iata_to_country_code('XXX')
        None
    """
    if not iata_code:
        return None
    
    # Normalizar: converter para maiúsculas e remover espaços
    iata_code = str(iata_code).strip().upper()
    
    if not iata_code or len(iata_code) != 3:
        logger.warning(f'⚠️ Código IATA inválido: {iata_code} (deve ter 3 letras)')
        return None
    
    country_code = IATA_TO_COUNTRY.get(iata_code)
    
    if country_code:
        logger.debug(f'✅ Código IATA {iata_code} → País {country_code}')
        return country_code
    else:
        logger.warning(f'⚠️ Código IATA {iata_code} não encontrado no mapeamento')
        return None


def get_country_from_airport_code(airport_code: str) -> Optional[str]:
    """
    Alias para iata_to_country_code (mantido para compatibilidade).
    
    Args:
        airport_code: Código IATA do aeroporto
    
    Returns:
        Código de país ISO 3166-1 alpha-2 ou None
    """
    return iata_to_country_code(airport_code)

