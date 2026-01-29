"""
Utilitários para manipulação de banco de dados - reduz código duplicado.
"""
import sqlite3
import logging
from typing import Optional, Any, Iterator
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection_context(db_path: Optional[str] = None):
    """
    Context manager para conexões SQLite - garante fechamento automático.
    
    Args:
        db_path: Caminho do banco (opcional, usa padrão se None)
    
    Yields:
        sqlite3.Connection: Conexão com o banco
    
    Examples:
        >>> with get_db_connection_context() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute('SELECT 1')
        ...     result = cursor.fetchone()
        >>> # Conexão fechada automaticamente
    """
    from db_manager import get_db_connection, DB_PATH
    
    if db_path:
        import os
        from pathlib import Path
        conn = sqlite3.connect(Path(db_path), timeout=10.0)
    else:
        conn = get_db_connection()
    
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        logger.error(f'❌ Erro na transação: {e}')
        raise
    finally:
        conn.close()


def execute_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = True) -> Optional[Any]:
    """
    Executa uma query SQL e retorna o resultado.
    
    Args:
        query: Query SQL
        params: Parâmetros da query (tupla)
        fetch_one: Se True, retorna apenas uma linha
        fetch_all: Se True, retorna todas as linhas (default: True)
    
    Returns:
        Resultado da query (linha única, lista de linhas, ou None)
    
    Examples:
        >>> execute_query('SELECT nome FROM usuarios WHERE id = ?', (1,), fetch_one=True)
        ('João',)
        >>> execute_query('SELECT * FROM usuarios')
        [('João', 1), ('Maria', 2)]
    """
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            conn.commit()
            return None


def execute_update(query: str, params: tuple = ()) -> int:
    """
    Executa uma query de UPDATE/INSERT/DELETE e retorna número de linhas afetadas.
    
    Args:
        query: Query SQL
        params: Parâmetros da query (tupla)
    
    Returns:
        Número de linhas afetadas
    
    Examples:
        >>> execute_update('UPDATE usuarios SET nome = ? WHERE id = ?', ('João Silva', 1))
        1
    """
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount


def execute_insert(query: str, params: tuple = ()) -> Optional[int]:
    """
    Executa uma query INSERT e retorna o ID da última linha inserida.
    
    Args:
        query: Query SQL INSERT
        params: Parâmetros da query (tupla)
    
    Returns:
        ID da última linha inserida ou None
    
    Examples:
        >>> execute_insert('INSERT INTO usuarios (nome) VALUES (?)', ('João',))
        1
    """
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid

