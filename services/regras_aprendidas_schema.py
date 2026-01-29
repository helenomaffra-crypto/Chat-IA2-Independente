"""
Schema (DDL) da tabela `regras_aprendidas`.

Extraído do `db_manager.py` para reduzir tamanho/complexidade do arquivo monolítico,
mantendo compatibilidade via wrappers.
"""

from __future__ import annotations

import sqlite3


def criar_tabela_regras_aprendidas(cursor: sqlite3.Cursor) -> None:
    """
    Cria a tabela `regras_aprendidas` (regras/definições aprendidas) e seus índices.

    Args:
        cursor: Cursor SQLite ativo.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS regras_aprendidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_regra TEXT NOT NULL,  -- 'campo_definicao', 'regra_negocio', 'preferencia_usuario', etc.
            contexto TEXT,  -- Contexto onde a regra se aplica (ex: 'chegada_processos', 'analise_vdm', etc.)
            nome_regra TEXT NOT NULL,  -- Nome amigável (ex: 'destfinal como confirmação de chegada')
            descricao TEXT NOT NULL,  -- Descrição completa da regra
            aplicacao_sql TEXT,  -- Como aplicar em SQL (ex: 'WHERE data_destino_final IS NOT NULL')
            aplicacao_texto TEXT,  -- Como aplicar em texto/linguagem natural
            exemplo_uso TEXT,  -- Exemplo de quando usar
            criado_por TEXT,  -- user_id ou session_id
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vezes_usado INTEGER DEFAULT 0,
            ultimo_usado_em TIMESTAMP,
            ativa BOOLEAN DEFAULT 1  -- Se a regra está ativa
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regras_tipo ON regras_aprendidas(tipo_regra, contexto)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_regras_ativa ON regras_aprendidas(ativa, vezes_usado DESC)")

