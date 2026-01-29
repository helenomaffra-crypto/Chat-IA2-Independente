"""
Helpers para manipulação segura de JSON.
"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def safe_json_loads(json_str: Optional[str], default: Any = None) -> Any:
    """
    Faz parse seguro de uma string JSON.
    
    Args:
        json_str: String JSON para fazer parse (pode ser None, vazio, ou string)
        default: Valor padrão a retornar se o parse falhar
    
    Returns:
        Objeto parseado ou default se falhar
    """
    if json_str is None:
        return default
    
    if not isinstance(json_str, str):
        # Se não é string, tentar converter
        try:
            json_str = str(json_str)
        except:
            return default
    
    # Remover espaços em branco
    json_str = json_str.strip()
    
    # Se está vazio, retornar default
    if not json_str:
        return default
    
    # Tentar fazer parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.debug(f"Erro ao fazer parse de JSON: {e}")
        return default
    except Exception as e:
        logger.warning(f"Erro inesperado ao fazer parse de JSON: {e}")
        return default


def safe_json_dumps(obj: Any, default: str = "{}", ensure_ascii: bool = False, indent: Optional[int] = None) -> str:
    """
    Converte objeto para string JSON de forma segura.
    
    Args:
        obj: Objeto para serializar
        default: String padrão a retornar se a serialização falhar
        ensure_ascii: Se True, escapa caracteres não-ASCII
        indent: Número de espaços para indentação (None = compacto)
    
    Returns:
        String JSON ou default se falhar
    """
    if obj is None:
        return default
    
    try:
        return json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent, default=str)
    except (TypeError, ValueError) as e:
        logger.warning(f"Erro ao serializar objeto para JSON: {e}")
        return default
    except Exception as e:
        logger.warning(f"Erro inesperado ao serializar JSON: {e}")
        return default

