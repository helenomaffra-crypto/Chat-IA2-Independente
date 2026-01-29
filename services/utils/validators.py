"""
Funções de validação de parâmetros.
"""
import re
from typing import Optional, Tuple


def validate_processo_referencia(processo_referencia: str) -> Tuple[bool, Optional[str]]:
    """
    Valida formato de referência de processo.
    
    Args:
        processo_referencia: Referência a validar
    
    Returns:
        Tuple (valido, mensagem_erro)
    """
    if not processo_referencia or not processo_referencia.strip():
        return False, "Referência de processo não pode ser vazia"
    
    # Padrão: XXX.NNNN/AA (aceita letras e números na categoria, ex: MV5, ALH, VDM)
    # Categoria: 2-4 caracteres (letras e/ou números), ex: ALH, VDM, MV5, GPS
    padrao = r'^[A-Z0-9]{2,4}\.\d{1,4}/\d{2}$'
    if not re.match(padrao, processo_referencia.upper()):
        return False, f"Formato inválido: {processo_referencia}. Esperado: XXX.NNNN/AA (ex: ALH.0001/25, MV5.0013/25)"
    
    return True, None

