"""
Schema (DDL + migrações leves) da tabela `consultas_salvas`.

Extraído do `db_manager.py` para reduzir tamanho/complexidade do arquivo monolítico,
mantendo compatibilidade via wrappers.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_consultas_salvas(cursor: sqlite3.Cursor) -> None:
    """
    Cria/migra a tabela `consultas_salvas` (consultas analíticas salvas) e seus índices.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS consultas_salvas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_exibicao TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            descricao TEXT,
            sql_base TEXT NOT NULL,
            parametros_json TEXT,  -- JSON array com {nome, tipo} dos parâmetros
            exemplos_pergunta TEXT,  -- Frases de exemplo em linguagem natural
            criado_por TEXT,  -- user_id ou session_id
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vezes_usado INTEGER DEFAULT 0,
            ultimo_usado_em TIMESTAMP,
            regra_aprendida_id INTEGER,  -- ID da regra aprendida que influenciou esta consulta
            contexto_regra TEXT,  -- Contexto da regra (ex: 'chegada_processos', 'atrasos_cliente')
            FOREIGN KEY (regra_aprendida_id) REFERENCES regras_aprendidas(id)
        )
        """
    )

    # MIGRAÇÃO: adicionar colunas se não existirem (instalações antigas)
    try:
        cursor.execute("ALTER TABLE consultas_salvas ADD COLUMN regra_aprendida_id INTEGER")
    except sqlite3.OperationalError:
        pass  # coluna já existe

    try:
        cursor.execute("ALTER TABLE consultas_salvas ADD COLUMN contexto_regra TEXT")
    except sqlite3.OperationalError:
        pass  # coluna já existe

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultas_salvas_slug ON consultas_salvas(slug)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consultas_salvas_nome ON consultas_salvas(nome_exibicao)")

