#!/usr/bin/env python3
"""
Script para verificar se a tabela HISTORICO_PAGAMENTOS existe no SQL Server
e se tem todos os campos necessários.

Uso:
    python3 testes/verificar_tabela_historico_pagamentos.py
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Campos esperados na tabela HISTORICO_PAGAMENTOS
CAMPOS_ESPERADOS = {
    'id_historico_pagamento': 'INT',
    'payment_id': 'NVARCHAR(255)',
    'tipo_pagamento': 'NVARCHAR(50)',
    'banco': 'NVARCHAR(50)',
    'ambiente': 'NVARCHAR(50)',
    'status': 'NVARCHAR(50)',
    'valor': 'DECIMAL(18,2)',
    'codigo_barras': 'NVARCHAR(255)',
    'beneficiario': 'NVARCHAR(500)',
    'vencimento': 'DATE',
    'agencia_origem': 'NVARCHAR(20)',
    'conta_origem': 'NVARCHAR(50)',
    'saldo_disponivel_antes': 'DECIMAL(18,2)',
    'saldo_apos_pagamento': 'DECIMAL(18,2)',
    'workspace_id': 'NVARCHAR(255)',
    'payment_date': 'DATE',
    'data_inicio': 'DATETIME',
    'data_efetivacao': 'DATETIME',
    'dados_completos': 'NVARCHAR(MAX)',
    'observacoes': 'NVARCHAR(MAX)',
    'criado_em': 'DATETIME',
    'atualizado_em': 'DATETIME'
}

def verificar_tabela():
    """Verifica se a tabela HISTORICO_PAGAMENTOS existe e tem os campos corretos."""
    
    try:
        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            logger.error("❌ SQL Server adapter não disponível")
            return False
        
        # 1. Verificar se tabela existe
        query_check = """
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' 
              AND TABLE_NAME = 'HISTORICO_PAGAMENTOS'
        """
        
        resultado = sql_adapter.execute_query(query_check, database=sql_adapter.database)
        
        if not resultado.get('success'):
            logger.error(f"❌ Erro ao verificar tabela: {resultado.get('error')}")
            return False
        
        data = resultado.get('data', [])
        if not data or len(data) == 0:
            logger.warning("⚠️ Tabela HISTORICO_PAGAMENTOS NÃO EXISTE no SQL Server")
            logger.info("💡 Execute o script: docs/queries/criar_tabela_historico_pagamentos.sql")
            return False
        
        count = data[0].get('count', 0) if isinstance(data[0], dict) else data[0][0] if isinstance(data[0], (list, tuple)) else 0
        
        if count == 0:
            logger.warning("⚠️ Tabela HISTORICO_PAGAMENTOS NÃO EXISTE no SQL Server")
            logger.info("💡 Execute o script: docs/queries/criar_tabela_historico_pagamentos.sql")
            return False
        
        logger.info("✅ Tabela HISTORICO_PAGAMENTOS existe no SQL Server")
        
        # 2. Verificar campos
        query_campos = """
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                IS_NULLABLE,
                COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' 
              AND TABLE_NAME = 'HISTORICO_PAGAMENTOS'
            ORDER BY ORDINAL_POSITION
        """
        
        resultado_campos = sql_adapter.execute_query(query_campos, database=sql_adapter.database)
        
        if not resultado_campos.get('success'):
            logger.error(f"❌ Erro ao verificar campos: {resultado_campos.get('error')}")
            return False
        
        campos_existentes = {}
        data_campos = resultado_campos.get('data', [])
        
        for row in data_campos:
            if isinstance(row, dict):
                nome = row.get('COLUMN_NAME')
                tipo = row.get('DATA_TYPE')
                tamanho = row.get('CHARACTER_MAXIMUM_LENGTH')
                nullable = row.get('IS_NULLABLE')
                
                # Formatar tipo com tamanho se aplicável
                tipo_completo = tipo
                if tamanho:
                    tipo_completo = f"{tipo}({tamanho})"
                elif tipo in ('DECIMAL', 'NUMERIC'):
                    # Para DECIMAL, pegar precisão e escala
                    precisao = row.get('NUMERIC_PRECISION', '')
                    escala = row.get('NUMERIC_SCALE', '')
                    if precisao and escala:
                        tipo_completo = f"{tipo}({precisao},{escala})"
                
                campos_existentes[nome] = {
                    'tipo': tipo_completo,
                    'nullable': nullable
                }
            elif isinstance(row, (list, tuple)):
                # Formato alternativo (lista/tupla)
                nome = row[0]
                tipo = row[1]
                campos_existentes[nome] = {'tipo': tipo, 'nullable': row[3] if len(row) > 3 else 'YES'}
        
        logger.info(f"✅ Encontrados {len(campos_existentes)} campos na tabela")
        
        # 3. Verificar se todos os campos esperados existem
        campos_faltando = []
        campos_ok = []
        
        for campo, tipo_esperado in CAMPOS_ESPERADOS.items():
            if campo not in campos_existentes:
                campos_faltando.append(campo)
            else:
                campos_ok.append(campo)
        
        if campos_faltando:
            logger.warning(f"⚠️ Campos faltando na tabela: {', '.join(campos_faltando)}")
            logger.info("💡 Execute o script: docs/queries/criar_tabela_historico_pagamentos.sql")
            return False
        
        logger.info(f"✅ Todos os {len(campos_ok)} campos esperados estão presentes")
        
        # 4. Verificar índices
        query_indices = """
            SELECT 
                i.name AS index_name,
                STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS columns
            FROM sys.indexes i
            INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
            INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
            WHERE i.object_id = OBJECT_ID('dbo.HISTORICO_PAGAMENTOS')
              AND i.name IS NOT NULL
            GROUP BY i.name
            ORDER BY i.name
        """
        
        resultado_indices = sql_adapter.execute_query(query_indices, database=sql_adapter.database)
        
        if resultado_indices.get('success'):
            indices = resultado_indices.get('data', [])
            logger.info(f"✅ Encontrados {len(indices)} índices na tabela")
            for idx in indices:
                if isinstance(idx, dict):
                    logger.info(f"   - {idx.get('index_name')}: {idx.get('columns')}")
                elif isinstance(idx, (list, tuple)):
                    logger.info(f"   - {idx[0]}: {idx[1] if len(idx) > 1 else 'N/A'}")
        
        logger.info("")
        logger.info("🎉 Tabela HISTORICO_PAGAMENTOS está OK!")
        logger.info("✅ Todos os campos necessários estão presentes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabela: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("🔍 Verificando tabela HISTORICO_PAGAMENTOS no SQL Server")
    print("=" * 60)
    print()
    
    sucesso = verificar_tabela()
    
    print()
    if sucesso:
        print("✅ VERIFICAÇÃO CONCLUÍDA COM SUCESSO!")
        sys.exit(0)
    else:
        print("⚠️ VERIFICAÇÃO FALHOU - Execute o script SQL para criar/atualizar a tabela")
        print("   Script: docs/queries/criar_tabela_historico_pagamentos.sql")
        sys.exit(1)
