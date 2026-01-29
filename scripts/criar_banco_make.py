#!/usr/bin/env python3
"""
Script Python para criar o banco de dados "Make" no SQL Server.

Este script usa as credenciais do .env para conectar ao SQL Server
e criar o banco de dados e tabelas principais.

Uso:
    python scripts/criar_banco_make.py

Requisitos:
    - Credenciais SQL Server configuradas no .env
    - Acesso ao servidor SQL Server
    - Permissões de DBA (para criar banco de dados)
"""
import os
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_server_adapter import get_sql_adapter
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def criar_banco_make():
    """Cria o banco de dados Make e suas tabelas principais."""
    try:
        # Obter adaptador SQL Server
        sql_adapter = get_sql_adapter()
        
        logger.info("🔍 Conectando ao SQL Server...")
        logger.info(f"   Servidor: {sql_adapter.server}")
        logger.info(f"   Instância: {sql_adapter.instance or 'N/A'}")
        logger.info(f"   Usuário: {sql_adapter.username}")
        logger.info(f"   Banco alvo: master (para criar novo banco)")
        
        # 1. Verificar se o banco já existe
        banco_nome = 'mAIke_assistente'
        logger.info(f"\n📋 Verificando se o banco '{banco_nome}' já existe...")
        query_check = f"SELECT name FROM sys.databases WHERE name = '{banco_nome}'"
        result = sql_adapter.execute_query(query_check, 'master', None, notificar_erro=False)
        
        if result.get('success') and result.get('data') and len(result.get('data', [])) > 0:
            logger.info(f"✅ Banco '{banco_nome}' já existe. Criando apenas tabelas que não existem...")
        else:
            logger.info(f"✅ Banco '{banco_nome}' não existe. Criando novo banco...")
        
        # 2. Testar conexão primeiro
        logger.info("\n📋 Testando conexão com SQL Server...")
        query_test = "SELECT @@VERSION AS version"
        result_test = sql_adapter.execute_query(query_test, 'master', None, notificar_erro=False)
        if not result_test.get('success'):
            logger.error(f"❌ Erro ao conectar ao SQL Server: {result_test.get('error')}")
            logger.error("   Verifique se:")
            logger.error("   - O servidor está acessível")
            logger.error("   - As credenciais no .env estão corretas")
            logger.error("   - O SQL Server está rodando")
            return False
        else:
            logger.info("✅ Conexão com SQL Server estabelecida!")
            if result_test.get('data'):
                version = result_test['data'][0].get('version', 'N/A')
                logger.info(f"   Versão SQL Server: {version[:50]}...")
        
        # 3. Criar banco de dados (se não existir)
        logger.info(f"\n📋 Criando banco de dados '{banco_nome}'...")
        # Query simplificada - deixar SQL Server escolher o caminho dos arquivos
        banco_nome_escaped = banco_nome.replace("'", "''")
        query_create_db = f"CREATE DATABASE [{banco_nome}]"
        
        # Verificar se já existe antes de criar
        query_check_again = f"SELECT name FROM sys.databases WHERE name = '{banco_nome_escaped}'"
        result_check_again = sql_adapter.execute_query(query_check_again, 'master', None, notificar_erro=False)
        
        if result_check_again.get('success') and result_check_again.get('data') and len(result_check_again.get('data', [])) > 0:
            logger.info(f"✅ Banco '{banco_nome}' já existe. Pulando criação...")
        else:
            result_create = sql_adapter.execute_query(query_create_db, 'master', None, notificar_erro=True)
            if result_create.get('success'):
                logger.info(f"✅ Banco '{banco_nome}' criado com sucesso!")
            else:
                error_msg = result_create.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro ao criar banco: {error_msg}")
                # Tentar criar com query mais detalhada
                logger.info("   Tentando criar com configurações detalhadas...")
                query_create_detailed = f"""
                    CREATE DATABASE [{banco_nome}]
                    ON (
                        NAME = '{banco_nome_escaped}',
                        SIZE = 100MB,
                        MAXSIZE = 10GB,
                        FILEGROWTH = 10MB
                    )
                    LOG ON (
                        NAME = '{banco_nome_escaped}_Log',
                        SIZE = 10MB,
                        MAXSIZE = 1GB,
                        FILEGROWTH = 10%
                    )
                """
                result_create_detailed = sql_adapter.execute_query(query_create_detailed, 'master', None, notificar_erro=True)
                if result_create_detailed.get('success'):
                    logger.info(f"✅ Banco '{banco_nome}' criado com sucesso (método alternativo)!")
                else:
                    logger.error(f"❌ Erro ao criar banco (método alternativo): {result_create_detailed.get('error')}")
                    return False
        
        # 3. Criar tabelas principais
        logger.info("\n📋 Criando tabelas principais...")
        
        # Tabela PROCESSO_IMPORTACAO
        query_processo = """
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[PROCESSO_IMPORTACAO]') AND type in (N'U'))
            BEGIN
                CREATE TABLE [dbo].[PROCESSO_IMPORTACAO] (
                    [id_processo_importacao] INT IDENTITY(1,1) PRIMARY KEY,
                    [id_importacao] INT NULL,
                    [numero_processo] NVARCHAR(50) NOT NULL UNIQUE,
                    [numero_ce] NVARCHAR(50) NULL,
                    [numero_di] NVARCHAR(50) NULL,
                    [numero_duimp] NVARCHAR(50) NULL,
                    [data_embarque] DATETIME NULL,
                    [data_chegada_prevista] DATETIME NULL,
                    [data_desembaraco] DATETIME NULL,
                    [status_processo] NVARCHAR(50) NULL,
                    [criado_em] DATETIME DEFAULT GETDATE(),
                    [atualizado_em] DATETIME DEFAULT GETDATE()
                );
                
                CREATE INDEX [idx_processo_numero] ON [dbo].[PROCESSO_IMPORTACAO]([numero_processo]);
                CREATE INDEX [idx_processo_id_importacao] ON [dbo].[PROCESSO_IMPORTACAO]([id_importacao]);
                CREATE INDEX [idx_processo_numero_ce] ON [dbo].[PROCESSO_IMPORTACAO]([numero_ce]);
                CREATE INDEX [idx_processo_numero_di] ON [dbo].[PROCESSO_IMPORTACAO]([numero_di]);
                CREATE INDEX [idx_processo_numero_duimp] ON [dbo].[PROCESSO_IMPORTACAO]([numero_duimp]);
            END
        """
        
        result_processo = sql_adapter.execute_query(query_processo, banco_nome, None, notificar_erro=True)
        if result_processo.get('success'):
            logger.info("✅ Tabela PROCESSO_IMPORTACAO criada ou já existe.")
        else:
            logger.error(f"❌ Erro ao criar tabela PROCESSO_IMPORTACAO: {result_processo.get('error')}")
            return False
        
        # Tabela TRANSPORTE
        query_transporte = """
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[TRANSPORTE]') AND type in (N'U'))
            BEGIN
                CREATE TABLE [dbo].[TRANSPORTE] (
                    [id_transporte] INT IDENTITY(1,1) PRIMARY KEY,
                    [id_processo_importacao] INT NULL,
                    [numero_processo] NVARCHAR(50) NULL,
                    [numero_container] NVARCHAR(50) NULL,
                    [numero_ce] NVARCHAR(50) NULL,
                    [nome_navio] NVARCHAR(200) NULL,
                    [porto_origem] NVARCHAR(100) NULL,
                    [porto_destino] NVARCHAR(100) NULL,
                    [eta] DATETIME NULL,
                    [status] NVARCHAR(50) NULL,
                    [payload_raw] NVARCHAR(MAX) NULL,
                    [criado_em] DATETIME DEFAULT GETDATE(),
                    [atualizado_em] DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY ([id_processo_importacao]) REFERENCES [dbo].[PROCESSO_IMPORTACAO]([id_processo_importacao])
                );
                
                CREATE INDEX [idx_transporte_processo] ON [dbo].[TRANSPORTE]([id_processo_importacao]);
                CREATE INDEX [idx_transporte_numero_processo] ON [dbo].[TRANSPORTE]([numero_processo]);
                CREATE INDEX [idx_transporte_ce] ON [dbo].[TRANSPORTE]([numero_ce]);
            END
        """
        
        result_transporte = sql_adapter.execute_query(query_transporte, banco_nome, None, notificar_erro=True)
        if result_transporte.get('success'):
            logger.info("✅ Tabela TRANSPORTE criada ou já existe.")
        else:
            logger.error(f"❌ Erro ao criar tabela TRANSPORTE: {result_transporte.get('error')}")
            return False
        
        # 4. Verificar estrutura criada
        logger.info("\n📋 Verificando estrutura criada...")
        query_tables = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
        result_tables = sql_adapter.execute_query(query_tables, banco_nome, None, notificar_erro=False)
        
        if result_tables.get('success') and result_tables.get('data'):
            tables = result_tables['data']
            logger.info(f"✅ Tabelas encontradas no banco '{banco_nome}': {len(tables)}")
            for table in tables:
                logger.info(f"   - {table.get('TABLE_NAME')}")
        
        logger.info("\n" + "="*60)
        logger.info(f"✅✅✅ Banco '{banco_nome}' criado com sucesso!")
        logger.info("="*60)
        logger.info("\n⚠️ NOTAS IMPORTANTES:")
        logger.info(f"1. Este script cria apenas as tabelas básicas do banco '{banco_nome}'")
        logger.info("2. As tabelas de DUIMP, DI, CE e CCT estão em outros bancos:")
        logger.info("   - duimp.dbo (DUIMPs)")
        logger.info("   - Serpro.dbo (DIs e CEs)")
        logger.info("   - comex.dbo (Importacoes - tabela de vínculo)")
        logger.info("\n3. Para criar os outros bancos, você precisará:")
        logger.info("   - Acesso ao servidor SQL Server")
        logger.info("   - Scripts de criação dos outros bancos (se disponíveis)")
        logger.info("   - Ou restaurar de backup existente")
        logger.info("\n4. Verifique o arquivo docs/MAPEAMENTO_SQL_SERVER.md para")
        logger.info("   entender a estrutura completa do sistema.")
        logger.info("\n" + "="*60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar banco 'Make': {e}", exc_info=True)
        return False


if __name__ == '__main__':
    print("="*60)
    print("🚀 Script de Criação do Banco de Dados 'mAIke_assistente'")
    print("="*60)
    print()
    
    sucesso = criar_banco_make()
    
    if sucesso:
        print("\n✅ Script concluído com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Script falhou. Verifique os erros acima.")
        sys.exit(1)

