#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Python para Criar Tabela HISTORICO_DOCUMENTO_ADUANEIRO
==============================================================
Cria a tabela automaticamente via SQL Server adapter.
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
        
        logger.info(f"✅ Adapter obtido: {adapter.server}\\{adapter.instance} - {adapter.database}")
        
        # Verificar se tabela já existe
        logger.info("🔍 Verificando se tabela já existe...")
        check_query = """
            SELECT COUNT(*) as total
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
        """
        result = adapter.execute_query(check_query, notificar_erro=True)
        
        if isinstance(result, dict) and result.get('success', False):
            data = result.get('data', [])
            if data and len(data) > 0 and data[0].get('total', 0) > 0:
                logger.info("ℹ️ Tabela HISTORICO_DOCUMENTO_ADUANEIRO já existe!")
                logger.info("   Se quiser recriar, execute: DROP TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO];")
                return True
        
        # Criar tabela
        logger.info("🔨 Criando tabela...")
        
        create_table_sql = """
        IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]') AND type in (N'U'))
        BEGIN
            CREATE TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO] (
                id_historico BIGINT IDENTITY(1,1) PRIMARY KEY,
                
                -- Vínculo com Documento Principal
                id_documento BIGINT,
                numero_documento VARCHAR(50) NOT NULL,
                tipo_documento VARCHAR(50) NOT NULL,
                processo_referencia VARCHAR(50),
                
                -- Detalhes do Evento
                data_evento DATETIME NOT NULL DEFAULT GETDATE(),
                tipo_evento VARCHAR(50) NOT NULL,
                tipo_evento_descricao VARCHAR(255),
                
                -- Valores Anteriores e Novos
                campo_alterado VARCHAR(100) NOT NULL,
                valor_anterior VARCHAR(500),
                valor_novo VARCHAR(500),
                
                -- Status e Situação (snapshot no momento do evento)
                status_documento VARCHAR(100),
                status_documento_codigo VARCHAR(20),
                canal_documento VARCHAR(20),
                situacao_documento VARCHAR(100),
                
                -- Datas (snapshot no momento do evento)
                data_registro DATETIME,
                data_situacao DATETIME,
                data_desembaraco DATETIME,
                
                -- Contexto da API
                fonte_dados VARCHAR(50) NOT NULL,
                api_endpoint VARCHAR(500),
                json_dados_originais NVARCHAR(MAX),
                
                -- Metadados
                usuario_ou_sistema VARCHAR(100) DEFAULT 'SISTEMA_AUTOMATICO',
                observacoes TEXT,
                criado_em DATETIME DEFAULT GETDATE()
            );
            
            -- Criar índices para performance
            CREATE INDEX idx_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](id_documento, data_evento DESC);
            CREATE INDEX idx_numero_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](numero_documento, tipo_documento, data_evento DESC);
            CREATE INDEX idx_processo ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](processo_referencia, data_evento DESC);
            CREATE INDEX idx_tipo_evento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](tipo_evento, data_evento DESC);
            CREATE INDEX idx_campo_alterado ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](campo_alterado, data_evento DESC);
            CREATE INDEX idx_fonte_dados ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](fonte_dados, data_evento DESC);
        END
        """
        
        result = adapter.execute_query(create_table_sql, notificar_erro=True)
        
        if isinstance(result, dict):
            if result.get('success', False):
                logger.info("✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO criada com sucesso!")
                
                # Verificar criação
                logger.info("🔍 Verificando criação...")
                verify_result = adapter.execute_query(check_query, notificar_erro=True)
                
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
                        cols_result = adapter.execute_query(count_cols_query, notificar_erro=True)
                        if isinstance(cols_result, dict) and cols_result.get('success', False):
                            cols_data = cols_result.get('data', [])
                            if cols_data:
                                logger.info(f"📊 Colunas criadas: {cols_data[0].get('total', 0)}")
                        
                        # Contar índices
                        count_idx_query = """
                            SELECT COUNT(*) as total
                            FROM sys.indexes
                            WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]')
                              AND index_id > 0
                        """
                        idx_result = adapter.execute_query(count_idx_query, notificar_erro=True)
                        if isinstance(idx_result, dict) and idx_result.get('success', False):
                            idx_data = idx_result.get('data', [])
                            if idx_data:
                                logger.info(f"📊 Índices criados: {idx_data[0].get('total', 0)}")
                        
                        return True
                    else:
                        logger.warning("⚠️ Tabela não encontrada após criação (pode ser problema de verificação)")
                        return False
                else:
                    logger.warning("⚠️ Não foi possível verificar criação da tabela")
                    return True  # Assumir sucesso se criação não retornou erro
            else:
                error = result.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro ao criar tabela: {error}")
                return False
        else:
            logger.warning(f"⚠️ Formato de resposta inesperado: {type(result)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabela: {e}", exc_info=True)
        return False


def main():
    """Executa criação da tabela"""
    logger.info("🚀 Iniciando criação da tabela HISTORICO_DOCUMENTO_ADUANEIRO...")
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
        logger.info("Tente executar o script SQL manualmente:")
        logger.info("   scripts/criar_tabela_historico_documentos.sql")
        return 1


if __name__ == '__main__':
    sys.exit(main())

