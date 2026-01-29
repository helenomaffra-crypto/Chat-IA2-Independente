"""
Wrapper de compatibilidade para o novo database_service.
"""
from services.database_service import get_db_connection as _get, DB_PATH, SQLITE_TIMEOUT

def get_db_connection():
    """Retorna conexão via database_service."""
    return _get()
