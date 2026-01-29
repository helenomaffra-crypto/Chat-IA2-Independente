"""
Schema para tabela de sugestões de vinculação bancária automática.
"""
import sqlite3
from typing import Optional


def criar_tabela_sugestoes_vinculacao(cursor: sqlite3.Cursor) -> None:
    """
    Cria tabela para armazenar sugestões de vinculação bancária.
    
    Estrutura:
    - id: ID único da sugestão
    - processo_referencia: Processo (ex: GLT.0011/26)
    - tipo_documento: 'DI' ou 'DUIMP'
    - numero_documento: Número da DI/DUIMP
    - data_desembaraco: Data do desembaraço
    - total_impostos: Valor total dos impostos (II + IPI + PIS + COFINS + TAXA_UTILIZACAO)
    - id_movimentacao_sugerida: ID do lançamento bancário sugerido
    - score_confianca: Score de confiança (0-100)
    - status: 'pendente', 'aplicada', 'ignorada', 'expirada'
    - criado_em: Data de criação
    - aplicado_em: Data de aplicação (se aplicada)
    - observacoes: Observações adicionais
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sugestoes_vinculacao_bancaria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            processo_referencia TEXT NOT NULL,
            tipo_documento TEXT NOT NULL,  -- 'DI' ou 'DUIMP'
            numero_documento TEXT,
            data_desembaraco TEXT,  -- YYYY-MM-DD
            total_impostos DECIMAL(18,2) NOT NULL,
            id_movimentacao_sugerida INTEGER,
            score_confianca INTEGER DEFAULT 0,  -- 0-100
            status TEXT DEFAULT 'pendente',  -- 'pendente', 'aplicada', 'ignorada', 'expirada'
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aplicado_em TIMESTAMP,
            observacoes TEXT
            -- ✅ NOTA: Foreign key removida porque MOVIMENTACAO_BANCARIA está no SQL Server, não no SQLite
            -- A validação será feita na aplicação quando a sugestão for aplicada
        )
    """)
    
    # Índices para consultas rápidas
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sugestoes_processo 
        ON sugestoes_vinculacao_bancaria(processo_referencia)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sugestoes_status 
        ON sugestoes_vinculacao_bancaria(status)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sugestoes_movimentacao 
        ON sugestoes_vinculacao_bancaria(id_movimentacao_sugerida)
    """)
