"""
Serviço centralizado de banco de dados (suporta SQLite e Postgres).
"""
import os
import logging
from typing import Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

# Configurações SQLite
DB_PATH = Path(os.getenv("DB_PATH", "chat_ia.db"))
SQLITE_TIMEOUT = 10.0

# Configurações Postgres
USE_POSTGRES = os.getenv("USE_POSTGRES", "false").lower() == "true"
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "maike_chat")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

def get_db_connection() -> Any:
    """
    Retorna uma conexão com o banco de dados configurado (Postgres ou SQLite).
    A conexão retornada é envolvida em um wrapper para compatibilidade de sintaxe.
    """
    # ✅ Robustez: Verificar se deve usar Postgres
    use_postgres_env = os.getenv("USE_POSTGRES", "false").lower() == "true"
    
    if use_postgres_env:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                connect_timeout=10
            )
            return PostgresConnectionWrapper(conn)
        except (ImportError, Exception) as e:
            logger.error(f"❌ Erro ao conectar ao Postgres: {e}. Tentando fallback para SQLite...")
            # Fallback para SQLite se o Postgres falhar ou a biblioteca não estiver instalada
            import sqlite3
            try:
                conn = sqlite3.connect(DB_PATH, timeout=SQLITE_TIMEOUT)
                conn.execute("PRAGMA foreign_keys = ON")
                return SQLiteConnectionWrapper(conn)
            except Exception as e2:
                logger.error(f"❌ Erro fatal ao conectar ao SQLite (fallback): {e2}")
                raise
    else:
        import sqlite3
        try:
            conn = sqlite3.connect(DB_PATH, timeout=SQLITE_TIMEOUT)
            conn.execute("PRAGMA foreign_keys = ON")
            return SQLiteConnectionWrapper(conn)
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao SQLite: {e}")
            raise

class SQLiteConnectionWrapper:
    """Wrapper para conexão SQLite para manter consistência com PostgresConnectionWrapper."""
    def __init__(self, conn):
        # Guardar conexão real (sqlite3.Connection)
        self.conn = conn

    # ✅ Compatibilidade: várias partes do código (ex: db_manager.py) esperam poder setar
    # `conn.row_factory = sqlite3.Row`. Se não repassarmos isso para a conexão real,
    # o cursor retorna tuplas e o código quebra ao acessar row['coluna'].
    @property
    def row_factory(self):
        return getattr(self.conn, "row_factory", None)

    @row_factory.setter
    def row_factory(self, value):
        setattr(self.conn, "row_factory", value)

    def __getattr__(self, name: str):
        # Delegar atributos/métodos não definidos para a conexão real
        return getattr(self.conn, name)
    
    def cursor(self):
        return self.conn.cursor()
    
    def commit(self):
        return self.conn.commit()
    
    def rollback(self):
        return self.conn.rollback()
    
    def close(self):
        return self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

class PostgresConnectionWrapper:
    """Wrapper para conexão Postgres para traduzir sintaxe SQLite (?) para Postgres (%s)."""
    def __init__(self, conn):
        self.conn = conn
    
    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor())
    
    def commit(self):
        return self.conn.commit()
    
    def rollback(self):
        return self.conn.rollback()
    
    def close(self):
        return self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

class PostgresCursorWrapper:
    """Wrapper para cursor Postgres para traduzir sintaxe SQLite (?) para Postgres (%s)."""
    def __init__(self, cursor):
        self.cursor = cursor
    
    def execute(self, query, params=None):
        # Traduzir ? para %s
        query = query.replace('?', '%s')
        # Traduzir INSERT OR REPLACE para INSERT ... ON CONFLICT (se necessário)
        # Nota: Esta tradução é complexa e pode não cobrir todos os casos.
        # Idealmente, o código deve ser atualizado para usar sintaxe compatível ou abstraída.
        if 'INSERT OR REPLACE' in query.upper():
            # Tradução básica para Postgres (requer que a tabela tenha PK ou UNIQUE constraint)
            # Ex: INSERT OR REPLACE INTO table (col1, col2) VALUES (%s, %s)
            # vira: INSERT INTO table (col1, col2) VALUES (%s, %s) ON CONFLICT (pk) DO UPDATE SET col2 = EXCLUDED.col2
            # Como não sabemos a PK aqui, vamos apenas logar um aviso por enquanto.
            logger.warning(f"⚠️ Detectado 'INSERT OR REPLACE' em query Postgres. Isso pode falhar se não houver ON CONFLICT. Query: {query}")
            query = query.replace('INSERT OR REPLACE', 'INSERT')
            
        if params:
            return self.cursor.execute(query, params)
        return self.cursor.execute(query)
    
    def fetchone(self):
        return self.cursor.fetchone()
    
    def fetchall(self):
        return self.cursor.fetchall()
    
    def close(self):
        return self.cursor.close()
    
    @property
    def rowcount(self):
        return self.cursor.rowcount

def is_postgres() -> bool:
    """Retorna True se estiver usando Postgres."""
    return USE_POSTGRES
