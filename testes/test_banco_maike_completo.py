#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste Completo - Banco mAIke_assistente
==================================================
Testa todas as funcionalidades do novo banco SQL Server.

Cenários testados:
1. Conexão e estrutura básica
2. Tabelas principais
3. Histórico de documentos
4. Consultas básicas
5. Integração com serviços
"""

import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TesteBancoMaike:
    """Classe para testar o banco mAIke_assistente"""
    
    def __init__(self):
        self.adapter = None
        self.resultados = {
            'passou': 0,
            'falhou': 0,
            'total': 0
        }
    
    def executar_todos_testes(self):
        """Executa todos os testes"""
        logger.info("=" * 80)
        logger.info("TESTE COMPLETO: Banco mAIke_assistente")
        logger.info("=" * 80)
        logger.info("")
        
        # Teste 1: Conexão
        self._testar_conexao()
        
        # Teste 2: Estrutura do banco
        self._testar_estrutura()
        
        # Teste 3: Tabela de histórico
        self._testar_tabela_historico()
        
        # Teste 4: Consultas básicas
        self._testar_consultas_basicas()
        
        # Teste 5: Integração com serviços
        self._testar_integracao_servicos()
        
        # Resumo
        self._mostrar_resumo()
    
    def _testar_conexao(self):
        """Testa conexão com o banco"""
        logger.info("=" * 80)
        logger.info("TESTE 1: Conexão com SQL Server")
        logger.info("=" * 80)
        
        try:
            from utils.sql_server_adapter import get_sql_adapter
            
            self.adapter = get_sql_adapter()
            if not self.adapter:
                self._falhar("Adapter não disponível")
                return
            
            # Testar query simples
            result = self.adapter.execute_query("SELECT 1 AS test", notificar_erro=True)
            
            if isinstance(result, dict) and result.get('success', False):
                self._passar("Conexão OK")
                logger.info(f"   Server: {self.adapter.server}\\{self.adapter.instance or ''}")
                logger.info(f"   Database: {self.adapter.database}")
                logger.info(f"   Username: {self.adapter.username}")
            else:
                self._falhar(f"Conexão falhou: {result.get('error', 'Erro desconhecido')}")
        except Exception as e:
            self._falhar(f"Erro ao testar conexão: {e}")
    
    def _testar_estrutura(self):
        """Testa estrutura do banco (tabelas principais)"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("TESTE 2: Estrutura do Banco")
        logger.info("=" * 80)
        
        if not self.adapter:
            self._falhar("Adapter não disponível")
            return
        
        # Tabelas principais que devem existir
        tabelas_principais = [
            'HISTORICO_DOCUMENTO_ADUANEIRO',
            'PROCESSO_IMPORTACAO',
            'DOCUMENTO_ADUANEIRO',
            'FORNECEDOR_CLIENTE',
            'CONSULTA_BILHETADA',
        ]
        
        for tabela in tabelas_principais:
            query = f"""
                SELECT COUNT(*) as total
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{tabela}'
            """
            result = self.adapter.execute_query(query, notificar_erro=False)
            
            if isinstance(result, dict) and result.get('success', False):
                data = result.get('data', [])
                if data and len(data) > 0 and data[0].get('total', 0) > 0:
                    self._passar(f"Tabela {tabela} existe")
                else:
                    self._falhar(f"Tabela {tabela} não encontrada")
            else:
                self._falhar(f"Erro ao verificar tabela {tabela}")
    
    def _testar_tabela_historico(self):
        """Testa tabela de histórico de documentos"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("TESTE 3: Tabela HISTORICO_DOCUMENTO_ADUANEIRO")
        logger.info("=" * 80)
        
        if not self.adapter:
            self._falhar("Adapter não disponível")
            return
        
        # Verificar se tabela existe
        query = """
            SELECT COUNT(*) as total
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
        """
        result = self.adapter.execute_query(query, notificar_erro=False)
        
        if not (isinstance(result, dict) and result.get('success', False)):
            self._falhar("Erro ao verificar tabela HISTORICO_DOCUMENTO_ADUANEIRO")
            return
        
        data = result.get('data', [])
        if not (data and len(data) > 0 and data[0].get('total', 0) > 0):
            self._falhar("Tabela HISTORICO_DOCUMENTO_ADUANEIRO não encontrada")
            return
        
        self._passar("Tabela HISTORICO_DOCUMENTO_ADUANEIRO existe")
        
        # Verificar colunas principais
        colunas_principais = [
            'id_historico',
            'numero_documento',
            'tipo_documento',
            'processo_referencia',
            'data_evento',
            'tipo_evento',
            'campo_alterado',
            'valor_anterior',
            'valor_novo',
            'fonte_dados',
        ]
        
        query_cols = """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
        """
        result_cols = self.adapter.execute_query(query_cols, notificar_erro=False)
        
        if isinstance(result_cols, dict) and result_cols.get('success', False):
            colunas_existentes = [row.get('COLUMN_NAME', '') for row in result_cols.get('data', [])]
            
            for coluna in colunas_principais:
                if coluna in colunas_existentes:
                    self._passar(f"Coluna {coluna} existe")
                else:
                    self._falhar(f"Coluna {coluna} não encontrada")
        else:
            self._falhar("Erro ao verificar colunas")
        
        # Verificar índices
        query_idx = """
            SELECT name, type_desc
            FROM sys.indexes
            WHERE object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]')
              AND index_id > 0
        """
        result_idx = self.adapter.execute_query(query_idx, notificar_erro=False)
        
        if isinstance(result_idx, dict) and result_idx.get('success', False):
            indices = result_idx.get('data', [])
            if len(indices) >= 6:
                self._passar(f"Índices criados: {len(indices)}")
            else:
                self._falhar(f"Poucos índices encontrados: {len(indices)} (esperado: 6+)")
        else:
            self._falhar("Erro ao verificar índices")
    
    def _testar_consultas_basicas(self):
        """Testa consultas básicas"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("TESTE 4: Consultas Básicas")
        logger.info("=" * 80)
        
        if not self.adapter:
            self._falhar("Adapter não disponível")
            return
        
        # Teste: Contar registros de histórico
        query = "SELECT COUNT(*) as total FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]"
        result = self.adapter.execute_query(query, notificar_erro=False)
        
        if isinstance(result, dict) and result.get('success', False):
            data = result.get('data', [])
            if data:
                total = data[0].get('total', 0)
                self._passar(f"Consulta COUNT OK: {total} registro(s)")
            else:
                self._falhar("Consulta COUNT retornou dados vazios")
        else:
            self._falhar("Erro ao executar consulta COUNT")
        
        # Teste: SELECT com ORDER BY
        query = """
            SELECT TOP 5 
                numero_documento,
                tipo_documento,
                tipo_evento,
                data_evento
            FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
            ORDER BY data_evento DESC
        """
        result = self.adapter.execute_query(query, notificar_erro=False)
        
        if isinstance(result, dict) and result.get('success', False):
            self._passar("Consulta SELECT com ORDER BY OK")
        else:
            self._falhar("Erro ao executar consulta SELECT")
    
    def _testar_integracao_servicos(self):
        """Testa integração com serviços"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("TESTE 5: Integração com Serviços")
        logger.info("=" * 80)
        
        # Teste: DocumentoHistoricoService
        try:
            from services.documento_historico_service import DocumentoHistoricoService
            
            service = DocumentoHistoricoService()
            if service:
                self._passar("DocumentoHistoricoService pode ser instanciado")
            else:
                self._falhar("DocumentoHistoricoService não pode ser instanciado")
        except Exception as e:
            self._falhar(f"Erro ao instanciar DocumentoHistoricoService: {e}")
        
        # Teste: SQL Server Adapter (singleton)
        try:
            from utils.sql_server_adapter import get_sql_adapter
            
            adapter1 = get_sql_adapter()
            adapter2 = get_sql_adapter()
            
            if adapter1 is adapter2:
                self._passar("Singleton do adapter funcionando")
            else:
                self._falhar("Singleton do adapter não funcionando")
        except Exception as e:
            self._falhar(f"Erro ao testar singleton: {e}")
    
    def _passar(self, mensagem: str):
        """Registra teste que passou"""
        self.resultados['passou'] += 1
        self.resultados['total'] += 1
        logger.info(f"✅ PASSOU: {mensagem}")
    
    def _falhar(self, mensagem: str):
        """Registra teste que falhou"""
        self.resultados['falhou'] += 1
        self.resultados['total'] += 1
        logger.error(f"❌ FALHOU: {mensagem}")
    
    def _mostrar_resumo(self):
        """Mostra resumo dos testes"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("RESUMO DOS TESTES")
        logger.info("=" * 80)
        logger.info(f"Total: {self.resultados['total']}")
        logger.info(f"Passou: {self.resultados['passou']}")
        logger.info(f"Falhou: {self.resultados['falhou']}")
        logger.info("")
        
        if self.resultados['falhou'] == 0:
            logger.info("🎉 TODOS OS TESTES PASSARAM!")
        else:
            logger.warning(f"⚠️ {self.resultados['falhou']} teste(s) falharam")


def main():
    """Executa todos os testes"""
    teste = TesteBancoMaike()
    teste.executar_todos_testes()
    
    return 0 if teste.resultados['falhou'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

