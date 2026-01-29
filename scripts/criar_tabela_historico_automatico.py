#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Automático para Criar Tabela HISTORICO_DOCUMENTO_ADUANEIRO
===================================================================
Executa o SQL diretamente via adapter, sem precisar do SQL Server Management Studio.
"""

import sys
from pathlib import Path
import os

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Carregar .env manualmente primeiro
env_path = root_dir / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def criar_tabela_historico():
    """Cria a tabela HISTORICO_DOCUMENTO_ADUANEIRO no SQL Server"""
    logger.info("=" * 80)
    logger.info("Criando Tabela HISTORICO_DOCUMENTO_ADUANEIRO")
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
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
        """
        result = adapter.execute_query(check_query, database=adapter.database, notificar_erro=True)
        
        if isinstance(result, dict) and result.get('success', False):
            data = result.get('data', [])
            if data and len(data) > 0 and data[0].get('total', 0) > 0:
                logger.info("ℹ️ Tabela HISTORICO_DOCUMENTO_ADUANEIRO já existe!")
                logger.info("   Tabela pronta para uso.")
                return True
        
        # Criar tabela (sem comandos GO e PRINT)
        logger.info("🔨 Criando tabela...")
        
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO] (
                id_historico BIGINT IDENTITY(1,1) PRIMARY KEY,
                id_documento BIGINT,
                numero_documento VARCHAR(50) NOT NULL,
                tipo_documento VARCHAR(50) NOT NULL,
                processo_referencia VARCHAR(50),
                data_evento DATETIME NOT NULL DEFAULT GETDATE(),
                tipo_evento VARCHAR(50) NOT NULL,
                tipo_evento_descricao VARCHAR(255),
                campo_alterado VARCHAR(100) NOT NULL,
                valor_anterior VARCHAR(500),
                valor_novo VARCHAR(500),
                status_documento VARCHAR(100),
                status_documento_codigo VARCHAR(20),
                canal_documento VARCHAR(20),
                situacao_documento VARCHAR(100),
                data_registro DATETIME,
                data_situacao DATETIME,
                data_desembaraco DATETIME,
                fonte_dados VARCHAR(50) NOT NULL,
                api_endpoint VARCHAR(500),
                json_dados_originais NVARCHAR(MAX),
                usuario_ou_sistema VARCHAR(100) DEFAULT 'SISTEMA_AUTOMATICO',
                observacoes TEXT,
                criado_em DATETIME DEFAULT GETDATE()
            )
        END
        """
        
        result = adapter.execute_query(create_table_sql, database=adapter.database, notificar_erro=True)
        
        if not isinstance(result, dict) or not result.get('success', False):
            error = result.get('error', 'Erro desconhecido') if isinstance(result, dict) else str(result)
            logger.error(f"❌ Erro ao criar tabela: {error}")
            return False
        
        logger.info("✅ Tabela criada com sucesso!")
        
        # Criar índices (um por vez para evitar problemas)
        indices = [
            ("idx_documento", "id_documento, data_evento DESC"),
            ("idx_numero_documento", "numero_documento, tipo_documento, data_evento DESC"),
            ("idx_processo", "processo_referencia, data_evento DESC"),
            ("idx_tipo_evento", "tipo_evento, data_evento DESC"),
            ("idx_campo_alterado", "campo_alterado, data_evento DESC"),
            ("idx_fonte_dados", "fonte_dados, data_evento DESC"),
        ]
        
        logger.info("🔨 Criando índices...")
        for idx_name, idx_columns in indices:
            create_idx_sql = f"""
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = '{idx_name}' AND object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]'))
            BEGIN
                CREATE INDEX {idx_name} ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]({idx_columns})
            END
            """
            idx_result = adapter.execute_query(create_idx_sql, database=adapter.database, notificar_erro=False)
            if isinstance(idx_result, dict) and idx_result.get('success', False):
                logger.info(f"   ✅ Índice {idx_name} criado")
            else:
                # Índice pode já existir, não é erro crítico
                logger.debug(f"   ⚠️ Índice {idx_name} (pode já existir)")
        
        # Verificar criação
        logger.info("🔍 Verificando criação...")
        verify_result = adapter.execute_query(check_query, database=adapter.database, notificar_erro=True)
        
        if isinstance(verify_result, dict) and verify_result.get('success', False):
            verify_data = verify_result.get('data', [])
            if verify_data and len(verify_data) > 0 and verify_data[0].get('total', 0) > 0:
                logger.info("✅ Verificação: Tabela existe e está acessível!")
                
                # Contar colunas
                count_cols_query = """
                    SELECT COUNT(*) as total
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
                """
                cols_result = adapter.execute_query(count_cols_query, database=adapter.database, notificar_erro=False)
                if isinstance(cols_result, dict) and cols_result.get('success', False):
                    cols_data = cols_result.get('data', [])
                    if cols_data:
                        logger.info(f"📊 Colunas: {cols_data[0].get('total', 0)}")
                
                # Contar índices
                count_idx_query = """
                    SELECT COUNT(*) as total
                    FROM sys.indexes
                    WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]')
                      AND index_id > 0
                """
                idx_result = adapter.execute_query(count_idx_query, database=adapter.database, notificar_erro=False)
                if isinstance(idx_result, dict) and idx_result.get('success', False):
                    idx_data = idx_result.get('data', [])
                    if idx_data:
                        logger.info(f"📊 Índices: {idx_data[0].get('total', 0)}")
                
                return True
            else:
                logger.warning("⚠️ Tabela não encontrada após criação")
                return False
        else:
            logger.warning("⚠️ Não foi possível verificar criação da tabela")
            return True  # Assumir sucesso se criação não retornou erro
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela: {e}", exc_info=True)
        return False


def main():
    """Executa criação da tabela"""
    logger.info("🚀 Iniciando criação automática da tabela HISTORICO_DOCUMENTO_ADUANEIRO...")
    logger.info("")
    
    sucesso = criar_tabela_historico()
    
    logger.info("")
    logger.info("=" * 80)
    if sucesso:
        logger.info("✅ SUCESSO: Tabela criada ou já existe!")
        logger.info("")
        logger.info("Próximos passos:")
        logger.info("1. Executar testes: python3 testes/test_historico_documentos.py")
        logger.info("2. Validar em produção consultando um documento via mAIke")
        return 0
    else:
        logger.error("❌ FALHA: Não foi possível criar a tabela")
        logger.info("")
        logger.info("Verifique:")
        logger.info("1. Conexão com SQL Server está funcionando")
        logger.info("2. Usuário tem permissões de DBA")
        logger.info("3. Banco mAIke_assistente existe")
        return 1


if __name__ == '__main__':
    sys.exit(main())

