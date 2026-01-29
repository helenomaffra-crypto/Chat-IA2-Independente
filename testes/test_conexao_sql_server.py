#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Diagnóstico - Conexão SQL Server
===========================================
Testa conexão com SQL Server e verifica configurações.
"""

import sys
import os
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


def test_conexao_sql_server():
    """Testa conexão com SQL Server"""
    logger.info("=" * 80)
    logger.info("DIAGNÓSTICO: Conexão SQL Server")
    logger.info("=" * 80)
    
    try:
        from utils.sql_server_adapter import get_sql_adapter, load_env_from_file
        import os
        
        # Recarregar .env
        logger.info("📋 Carregando variáveis de ambiente...")
        load_env_from_file()
        
        # Mostrar configurações (sem senha)
        logger.info("📋 Configurações detectadas:")
        logger.info(f"   SQL_SERVER: {os.getenv('SQL_SERVER', 'NÃO DEFINIDO')}")
        logger.info(f"   SQL_USERNAME: {os.getenv('SQL_USERNAME', 'NÃO DEFINIDO')}")
        logger.info(f"   SQL_DATABASE: {os.getenv('SQL_DATABASE', 'NÃO DEFINIDO')}")
        logger.info(f"   SQL_PASSWORD: {'***' if os.getenv('SQL_PASSWORD') else 'NÃO DEFINIDO'}")
        
        logger.info("")
        logger.info("🔍 Obtendo adapter SQL Server...")
        adapter = get_sql_adapter()
        
        if not adapter:
            logger.error("❌ Não foi possível obter adapter SQL Server")
            return False
        
        logger.info(f"✅ Adapter obtido:")
        logger.info(f"   Server: {adapter.server}")
        logger.info(f"   Instance: {adapter.instance}")
        logger.info(f"   Database: {adapter.database}")
        logger.info(f"   Username: {adapter.username}")
        logger.info(f"   Use Node: {adapter.use_node}")
        logger.info(f"   Use pyodbc: {adapter.use_pyodbc}")
        
        logger.info("")
        logger.info("🔍 Testando conexão com query simples...")
        
        # Testar query simples
        result = adapter.execute_query("SELECT 1 AS test", notificar_erro=True)
        
        if isinstance(result, dict):
            if result.get('success', False):
                logger.info("✅ Conexão bem-sucedida!")
                data = result.get('data', [])
                if data:
                    logger.info(f"   Resultado: {data}")
                return True
            else:
                error = result.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro na conexão: {error}")
                return False
        else:
            logger.warning(f"⚠️ Formato de resposta inesperado: {type(result)}")
            logger.info(f"   Resposta: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexão: {e}", exc_info=True)
        return False


def test_tabela_historico():
    """Testa se tabela HISTORICO_DOCUMENTO_ADUANEIRO existe"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("DIAGNÓSTICO: Tabela HISTORICO_DOCUMENTO_ADUANEIRO")
    logger.info("=" * 80)
    
    try:
        from utils.sql_server_adapter import get_sql_adapter
        
        adapter = get_sql_adapter()
        if not adapter:
            logger.error("❌ Adapter não disponível")
            return False
        
        # Verificar se tabela existe
        query = """
            SELECT COUNT(*) as total
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
        """
        
        logger.info("🔍 Verificando se tabela existe...")
        result = adapter.execute_query(query, notificar_erro=True)
        
        if isinstance(result, dict):
            if result.get('success', False):
                data = result.get('data', [])
                if data and len(data) > 0:
                    total = data[0].get('total', 0)
                    if total > 0:
                        logger.info("✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO existe!")
                        return True
                    else:
                        logger.warning("⚠️ Tabela HISTORICO_DOCUMENTO_ADUANEIRO não encontrada")
                        logger.info("   Execute o script SQL: scripts/criar_banco_maike_completo.sql")
                        return False
                else:
                    logger.warning("⚠️ Tabela não encontrada (resposta vazia)")
                    return False
            else:
                error = result.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro ao verificar tabela: {error}")
                return False
        else:
            logger.warning(f"⚠️ Formato de resposta inesperado: {type(result)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabela: {e}", exc_info=True)
        return False


def main():
    """Executa diagnóstico completo"""
    logger.info("🚀 Iniciando diagnóstico de conexão SQL Server...")
    logger.info("")
    
    # Testar conexão
    conexao_ok = test_conexao_sql_server()
    
    # Se conexão OK, testar tabela
    if conexao_ok:
        tabela_ok = test_tabela_historico()
    else:
        logger.warning("⚠️ Pulando teste de tabela (conexão falhou)")
        tabela_ok = False
    
    # Resumo
    logger.info("")
    logger.info("=" * 80)
    logger.info("RESUMO DO DIAGNÓSTICO")
    logger.info("=" * 80)
    logger.info(f"Conexão SQL Server: {'✅ OK' if conexao_ok else '❌ FALHOU'}")
    logger.info(f"Tabela HISTORICO_DOCUMENTO_ADUANEIRO: {'✅ EXISTE' if tabela_ok else '❌ NÃO ENCONTRADA' if conexao_ok else '⚠️ NÃO TESTADO'}")
    
    if conexao_ok and tabela_ok:
        logger.info("")
        logger.info("🎉 Tudo OK! SQL Server está acessível e tabela existe.")
        return 0
    elif conexao_ok:
        logger.info("")
        logger.warning("⚠️ Conexão OK, mas tabela não existe.")
        logger.info("   Execute: scripts/criar_banco_maike_completo.sql")
        return 1
    else:
        logger.info("")
        logger.error("❌ Problema de conexão com SQL Server.")
        logger.info("   Verifique:")
        logger.info("   1. Está na rede do escritório?")
        logger.info("   2. VPN está conectada?")
        logger.info("   3. Credenciais no .env estão corretas?")
        logger.info("   4. SQL Server está rodando?")
        return 1


if __name__ == '__main__':
    sys.exit(main())

