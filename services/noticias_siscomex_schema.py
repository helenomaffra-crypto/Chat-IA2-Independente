"""
Schema para tabela de notícias do Siscomex (feeds RSS).
Extraído do db_manager.py para seguir padrão de refatoração.
"""
import sqlite3


def criar_tabela_noticias_siscomex(cursor: sqlite3.Cursor) -> None:
    """
    Cria tabela de notícias do Siscomex e seus índices.
    
    Args:
        cursor: Cursor SQLite
    """
    # Tabela de notícias do Siscomex (feeds RSS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS noticias_siscomex (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guid TEXT UNIQUE NOT NULL,  -- ID único da notícia (evita duplicatas)
            titulo TEXT NOT NULL,
            descricao TEXT,
            link TEXT NOT NULL,
            data_publicacao TIMESTAMP,
            fonte TEXT NOT NULL,  -- 'siscomex_importacao' ou 'siscomex_sistemas'
            notificada BOOLEAN DEFAULT 0,  -- Se já foi criada notificação
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Índices para notícias Siscomex
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_noticias_guid 
        ON noticias_siscomex(guid)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_noticias_fonte_data 
        ON noticias_siscomex(fonte, data_publicacao DESC)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_noticias_notificada 
        ON noticias_siscomex(notificada, criado_em DESC)
    ''')
