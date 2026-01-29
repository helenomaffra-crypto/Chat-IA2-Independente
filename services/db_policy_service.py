"""
Serviço centralizado para política de escolha de banco de dados (primário vs legado).

Garante que o sistema use:
- mAIke_assistente como banco primário
- Make apenas como fallback controlado (com logs explícitos)
- Feature flag para habilitar/desabilitar fallback legado
"""
import logging
import os
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Configurações
DATABASE_PRIMARY = 'mAIke_assistente'
DATABASE_LEGACY = 'Make'

# Feature flag: permite desabilitar fallback para Make
ALLOW_LEGACY_FALLBACK = os.getenv('ALLOW_LEGACY_FALLBACK', 'true').lower() == 'true'


def get_primary_database() -> str:
    """
    Retorna o nome do banco de dados primário.
    
    Returns:
        Nome do banco primário (mAIke_assistente)
    """
    return DATABASE_PRIMARY


def get_legacy_database() -> str:
    """
    Retorna o nome do banco de dados legado.
    
    Returns:
        Nome do banco legado (Make)
    """
    return DATABASE_LEGACY


def is_legacy_fallback_allowed() -> bool:
    """
    Verifica se o fallback para banco legado está habilitado.
    
    Returns:
        True se fallback está permitido, False caso contrário
    """
    return ALLOW_LEGACY_FALLBACK


def should_use_legacy_database(processo_referencia: Optional[str] = None) -> bool:
    """
    Determina se deve usar banco legado (Make).
    
    Atualmente, retorna True apenas se:
    - Fallback está habilitado (ALLOW_LEGACY_FALLBACK=true)
    - E foi explicitamente solicitado (não é o comportamento padrão)
    
    Args:
        processo_referencia: Referência do processo (para logging)
    
    Returns:
        True se deve usar Make, False caso contrário
    """
    if not ALLOW_LEGACY_FALLBACK:
        if processo_referencia:
            logger.debug(
                f"🔒 [DB_POLICY] Fallback para Make desabilitado para processo {processo_referencia}"
            )
        return False
    return True


def log_legacy_fallback(
    processo_referencia: str,
    tool_name: Optional[str] = None,
    caller_function: Optional[str] = None,
    reason: Optional[str] = None,
    query: Optional[str] = None
) -> None:
    """
    Loga explicitamente quando ocorre fallback para banco legado (Make).
    
    Args:
        processo_referencia: Referência do processo
        tool_name: Nome da tool que causou o fallback (opcional)
        caller_function: Nome da função que chamou (opcional)
        reason: Motivo do fallback (opcional)
        query: Query SQL executada (opcional, truncada para segurança)
    """
    timestamp = datetime.now().isoformat()
    
    # Truncar query se muito longa (para não poluir logs)
    query_display = None
    if query:
        query_display = query[:200] + "..." if len(query) > 200 else query
    
    logger.warning(
        f"⚠️ [FALLBACK_MAKE] Processo {processo_referencia} não encontrado no {DATABASE_PRIMARY}\n"
        f"   → Consultando banco legado ({DATABASE_LEGACY}) para migração/auto-heal\n"
        f"   → Tool/Serviço: {tool_name or 'N/A'}\n"
        f"   → Chamador: {caller_function or 'N/A'}\n"
        f"   → Motivo: {reason or 'Processo não encontrado no banco primário'}\n"
        f"   → Query: {query_display or 'N/A'}\n"
        f"   → Timestamp: {timestamp}"
    )


def get_database_for_query(
    prefer_primary: bool = True,
    processo_referencia: Optional[str] = None,
    tool_name: Optional[str] = None,
    caller_function: Optional[str] = None
) -> str:
    """
    Retorna o nome do banco de dados a ser usado para uma query.
    
    Args:
        prefer_primary: Se True, prefere banco primário; se False, permite fallback
        processo_referencia: Referência do processo (para logging)
        tool_name: Nome da tool (para logging)
        caller_function: Nome da função chamadora (para logging)
    
    Returns:
        Nome do banco de dados a ser usado
    """
    if prefer_primary:
        return DATABASE_PRIMARY
    
    # Se não prefere primário, verifica se fallback está permitido
    if should_use_legacy_database(processo_referencia):
        if processo_referencia:
            log_legacy_fallback(
                processo_referencia=processo_referencia,
                tool_name=tool_name,
                caller_function=caller_function,
                reason="Fallback explícito solicitado"
            )
        return DATABASE_LEGACY
    
    # Fallback desabilitado, usar primário mesmo assim
    logger.warning(
        f"🔒 [DB_POLICY] Fallback para Make desabilitado, usando {DATABASE_PRIMARY} mesmo com prefer_primary=False"
    )
    return DATABASE_PRIMARY


def resolve_database_with_fallback(
    processo_referencia: str,
    tool_name: Optional[str] = None,
    caller_function: Optional[str] = None,
    query: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Resolve qual banco usar, tentando primário primeiro e fazendo fallback para legado se necessário.
    
    Args:
        processo_referencia: Referência do processo
        tool_name: Nome da tool (para logging)
        caller_function: Nome da função chamadora (para logging)
        query: Query SQL (para logging)
    
    Returns:
        Tuple (database_name, is_fallback) onde:
        - database_name: Nome do banco a ser usado
        - is_fallback: True se está usando fallback, False se usando primário
    """
    # Sempre tentar primário primeiro
    if not should_use_legacy_database(processo_referencia):
        return DATABASE_PRIMARY, False
    
    # Se fallback está permitido, retornar primário mas indicar que pode fazer fallback depois
    # (a lógica de fallback real deve ser feita pela função chamadora após tentar primário)
    return DATABASE_PRIMARY, False


def get_database_policy_info() -> dict:
    """
    Retorna informações sobre a política de banco de dados atual.
    
    Returns:
        Dict com informações da política
    """
    return {
        'primary_database': DATABASE_PRIMARY,
        'legacy_database': DATABASE_LEGACY,
        'allow_legacy_fallback': ALLOW_LEGACY_FALLBACK,
        'policy_version': '1.0.0'
    }
