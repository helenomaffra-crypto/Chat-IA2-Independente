#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Python para Criar Tabela HISTORICO_PAGAMENTOS
====================================================
Cria a tabela automaticamente via SQL Server adapter.

Uso:
    python3 scripts/criar_tabela_historico_pagamentos.py
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def criar_tabela_historico_pagamentos():
    """Cria a tabela HISTORICO_PAGAMENTOS no SQL Server"""
    logger.info("=" * 80)
    logger.info("Criando Tabela HISTORICO_PAGAMENTOS")
    logger.info("=" * 80)
    
    try:
        from utils.sql_server_adapter import get_sql_adapter
        
        adapter = get_sql_adapter()
        if not adapter:
            logger.error("❌ Adapter SQL Server não disponível")
            return False
        
        logger.info(f"✅ Adapter obtido: {adapter.server}\\{adapter.instance or ''} - {adapter.database}")
        
        # Verificar se tabela já existe
        logger.info("🔍 Verificando se tabela já existe...")
        check_query = """
            SELECT COUNT(*) as total
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_PAGAMENTOS'
        """
        result = adapter.execute_query(check_query, database=adapter.database, notificar_erro=True)
        
        if isinstance(result, dict) and result.get('success', False):
            data = result.get('data', [])
            if data and len(data) > 0:
                # Verificar se encontrou a tabela
                total = 0
                if isinstance(data[0], dict):
                    total = data[0].get('total', 0)
                elif isinstance(data[0], (list, tuple)):
                    total = data[0][0] if len(data[0]) > 0 else 0
                
                if total > 0:
                    logger.info("ℹ️ Tabela HISTORICO_PAGAMENTOS já existe!")
                    logger.info("   Tabela pronta para uso.")
                    return True
        
        # Criar tabela (sem comandos GO e PRINT)
        logger.info("🔨 Criando tabela...")
        
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_PAGAMENTOS]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[HISTORICO_PAGAMENTOS] (
                id_historico_pagamento INT IDENTITY(1,1) PRIMARY KEY,
                payment_id NVARCHAR(255) NOT NULL UNIQUE,
                tipo_pagamento NVARCHAR(50) NOT NULL,
                banco NVARCHAR(50) NOT NULL,
                ambiente NVARCHAR(50) NOT NULL,
                status NVARCHAR(50) NOT NULL,
                valor DECIMAL(18,2) NOT NULL,
                codigo_barras NVARCHAR(255) NULL,
                beneficiario NVARCHAR(500) NULL,
                vencimento DATE NULL,
                agencia_origem NVARCHAR(20) NULL,
                conta_origem NVARCHAR(50) NULL,
                saldo_disponivel_antes DECIMAL(18,2) NULL,
                saldo_apos_pagamento DECIMAL(18,2) NULL,
                workspace_id NVARCHAR(255) NULL,
                payment_date DATE NULL,
                data_inicio DATETIME NULL,
                data_efetivacao DATETIME NULL,
                dados_completos NVARCHAR(MAX) NULL,
                observacoes NVARCHAR(MAX) NULL,
                criado_em DATETIME NOT NULL DEFAULT GETDATE(),
                atualizado_em DATETIME NOT NULL DEFAULT GETDATE()
            )
        END
        """
        
        logger.info("📝 Executando CREATE TABLE...")
        result = adapter.execute_query(create_table_sql, database=adapter.database, notificar_erro=True)
        
        if not isinstance(result, dict) or not result.get('success', False):
            error_msg = result.get('error', 'Erro desconhecido') if isinstance(result, dict) else str(result)
            logger.error(f"❌ Erro ao criar tabela: {error_msg}")
            return False
        
        logger.info("✅ Tabela HISTORICO_PAGAMENTOS criada com sucesso!")
        
        # Criar índices
        logger.info("🔨 Criando índices...")
        
        indices = [
            {
                'name': 'idx_historico_pagamentos_payment_id',
                'sql': 'CREATE INDEX idx_historico_pagamentos_payment_id ON [dbo].[HISTORICO_PAGAMENTOS](payment_id)'
            },
            {
                'name': 'idx_historico_pagamentos_status',
                'sql': 'CREATE INDEX idx_historico_pagamentos_status ON [dbo].[HISTORICO_PAGAMENTOS](status, data_efetivacao)'
            },
            {
                'name': 'idx_historico_pagamentos_tipo',
                'sql': 'CREATE INDEX idx_historico_pagamentos_tipo ON [dbo].[HISTORICO_PAGAMENTOS](tipo_pagamento, banco, ambiente)'
            },
            {
                'name': 'idx_historico_pagamentos_data',
                'sql': 'CREATE INDEX idx_historico_pagamentos_data ON [dbo].[HISTORICO_PAGAMENTOS](data_efetivacao DESC)'
            },
            {
                'name': 'idx_historico_pagamentos_banco_ambiente',
                'sql': 'CREATE INDEX idx_historico_pagamentos_banco_ambiente ON [dbo].[HISTORICO_PAGAMENTOS](banco, ambiente, data_efetivacao DESC)'
            }
        ]
        
        for idx in indices:
            # Verificar se índice já existe
            check_idx_sql = f"""
                SELECT COUNT(*) as total
                FROM sys.indexes
                WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_PAGAMENTOS]')
                  AND name = '{idx['name']}'
            """
            
            result_check = adapter.execute_query(check_idx_sql, database=adapter.database, notificar_erro=False)
            
            idx_existe = False
            if isinstance(result_check, dict) and result_check.get('success', False):
                data_check = result_check.get('data', [])
                if data_check and len(data_check) > 0:
                    total = 0
                    if isinstance(data_check[0], dict):
                        total = data_check[0].get('total', 0)
                    elif isinstance(data_check[0], (list, tuple)):
                        total = data_check[0][0] if len(data_check[0]) > 0 else 0
                    
                    if total > 0:
                        idx_existe = True
            
            if not idx_existe:
                logger.info(f"   Criando índice: {idx['name']}...")
                result_idx = adapter.execute_query(idx['sql'], database=adapter.database, notificar_erro=False)
                
                if isinstance(result_idx, dict) and result_idx.get('success', False):
                    logger.info(f"   ✅ Índice {idx['name']} criado")
                else:
                    error_idx = result_idx.get('error', 'Erro desconhecido') if isinstance(result_idx, dict) else str(result_idx)
                    logger.warning(f"   ⚠️ Erro ao criar índice {idx['name']}: {error_idx}")
            else:
                logger.info(f"   ℹ️ Índice {idx['name']} já existe")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ Tabela HISTORICO_PAGAMENTOS criada com sucesso!")
        logger.info("✅ Todos os índices foram criados/verificados")
        logger.info("=" * 80)
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    print("=" * 80)
    print("🚀 Criando Tabela HISTORICO_PAGAMENTOS no SQL Server")
    print("=" * 80)
    print()
    
    sucesso = criar_tabela_historico_pagamentos()
    
    print()
    if sucesso:
        print("✅ SUCESSO! Tabela criada e pronta para uso.")
        print()
        print("💡 Próximo passo: Verificar se foi criada corretamente:")
        print("   python3 testes/verificar_tabela_historico_pagamentos.py")
        sys.exit(0)
    else:
        print("❌ FALHA! Verifique os erros acima.")
        sys.exit(1)
