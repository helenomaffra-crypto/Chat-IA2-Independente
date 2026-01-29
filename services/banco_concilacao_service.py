#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviço de Conciliação/Classificação de Lançamentos Bancários.

Permite classificar lançamentos bancários vinculando-os a tipos de despesa e processos.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from utils.sql_server_adapter import get_sql_adapter

logger = logging.getLogger(__name__)

# Singleton instance
_concilacao_service_instance = None

def get_banco_concilacao_service():
    """Retorna instância singleton do serviço de conciliação."""
    global _concilacao_service_instance
    if _concilacao_service_instance is None:
        _concilacao_service_instance = BancoConcilacaoService()
    return _concilacao_service_instance

class BancoConcilacaoService:
    """Serviço para conciliação e classificação de lançamentos bancários."""
    
    def __init__(self):
        """Inicializa o serviço de conciliação."""
        self.sql_adapter = get_sql_adapter()
        logger.info("✅ BancoConcilacaoService inicializado")
    
    def _eh_lancamento_impostos(self, descricao: str) -> bool:
        """
        Verifica se um lançamento PODE SER de impostos de importação.
        
        ⚠️ IMPORTANTE: Esta é uma detecção conservadora que identifica apenas
        lançamentos que claramente são do SISCOMEX. Lançamentos genéricos como
        "Impostos" não são marcados, pois podem ser ICMS, ISS, etc.
        
        Args:
            descricao: Descrição do lançamento bancário
        
        Returns:
            True se for PROVAVELMENTE lançamento de impostos de importação
        """
        if not descricao:
            return False
        
        descricao_upper = descricao.upper().strip()
        # Normalização leve para detecção por "histórico" do Santander:
        # - Alguns lançamentos vêm com prefixos como "- " no início
        descricao_upper_strip_prefix = descricao_upper.lstrip()
        # Remover um hífen inicial (ex: "- PAGAMENTO PUCOMEX ...") sem perder o restante
        if descricao_upper_strip_prefix.startswith("-"):
            descricao_upper_strip_prefix = descricao_upper_strip_prefix[1:].lstrip()
        
        # ✅ Palavras-chave ESPECÍFICAS de importação (mais conservador)
        palavras_chave_especificas = [
            'IMPORTAÇÃO SISCOMEX',      # Muito específico
            'IMPORTACAO SISCOMEX',      # Muito específico
            'SISCOMEX',                 # Sistema de importação
            'IMPOSTO DE IMPORTAÇÃO',    # Específico
            'IMPOSTO DE IMPORTACAO',    # Específico
            'II IPI PIS COFINS',        # Combinação específica
            'TRIBUTOS IMPORTAÇÃO',      # Específico
            'TRIBUTOS IMPORTACAO',      # Específico
            'DI ',                      # Declaração de Importação
            'DUIMP',                    # Declaração Única de Importação
            # ✅ NOVO (22/01/2026): Santander / PUCOMEX
            # Usuário reportou que o "histórico" pode começar com "- PAGAMENTO PUCOMEX ...".
            # Tratamos isso como forte indício de recolhimento PUCOMEX (impostos de importação).
            'PAGAMENTO PUCOMEX',
        ]
        
        # ❌ NÃO marcar como imposto de importação se contiver palavras genéricas
        palavras_excluir = [
            'ICMS',
            'ISS',
            'IRPF',
            'IRPJ',
            'CSLL',
            'SIMPLES',
            'PARCELAMENTO',
            'REFIS',
        ]
        
        # Se contém palavras de exclusão, não é imposto de importação
        if any(palavra in descricao_upper for palavra in palavras_excluir):
            return False
        
        # ✅ Caso especial: "histórico começa com - PAGAMENTO PUCOMEX"
        # Mantém detecção conservadora (não pega "PUCOMEX" solto no meio)
        if descricao_upper_strip_prefix.startswith("PAGAMENTO PUCOMEX"):
            return True

        # Verificar se contém palavras-chave específicas
        return any(palavra in descricao_upper for palavra in palavras_chave_especificas)
    
    def _eh_possivel_imposto_importacao(self, descricao: str, processo_vinculado: Optional[str] = None) -> bool:
        """
        Verifica se um lançamento PODE SER imposto de importação (mais conservador).
        
        Esta função é mais conservadora e só retorna True se:
        1. Descrição contém palavras-chave específicas de SISCOMEX, OU
        2. Lançamento já está vinculado a um processo (indica que pode ser de importação)
        
        Args:
            descricao: Descrição do lançamento bancário
            processo_vinculado: Processo já vinculado (opcional)
        
        Returns:
            True se PODE SER imposto de importação (requer confirmação do usuário)
        """
        # Se já está vinculado a processo, pode ser imposto de importação
        if processo_vinculado:
            return True
        
        # Verificar descrição específica
        return self._eh_lancamento_impostos(descricao)
    
    def listar_lancamentos_nao_classificados(
        self, 
        limite: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
        data_inicio: Optional[str] = None, 
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista lançamentos bancários que não estão classificados (sem tipo de despesa vinculado).
        
        ✅ NOVO: Suporta paginação para melhor performance e controle de volume.
        
        Args:
            limite: Número máximo de lançamentos (DEPRECATED - use page/per_page)
            page: Número da página (padrão: 1)
            per_page: Itens por página (padrão: 50, máximo: 100)
            data_inicio: Data inicial (YYYY-MM-DD, opcional)
            data_fim: Data final (YYYY-MM-DD, opcional)
        
        Returns:
            Dict com sucesso, total, paginação e lista de lançamentos
        """
        try:
            # ✅ CORREÇÃO: Verificar qual banco está sendo usado
            database_used = self.sql_adapter.database
            logger.info(f"📊 Banco de dados configurado: {database_used}")
            
            # Query para buscar lançamentos sem classificação
            # ✅ CORREÇÃO: Construir WHERE de forma mais clara
            where_parts = []
            
            # Condição principal: não ter classificação
            where_parts.append("NOT EXISTS (")
            where_parts.append("    SELECT 1")
            where_parts.append("    FROM dbo.LANCAMENTO_TIPO_DESPESA ltd")
            where_parts.append("    WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao")
            where_parts.append(")")
            
            # Filtros de data (se fornecidos)
            if data_inicio:
                where_parts.append("AND CAST(mb.data_movimentacao AS DATE) >= '{data_inicio}'")
            if data_fim:
                where_parts.append("AND CAST(mb.data_movimentacao AS DATE) <= '{data_fim}'")
            
            where_clause = ' '.join(where_parts)
            if data_inicio:
                where_clause = where_clause.replace('{data_inicio}', data_inicio)
            if data_fim:
                where_clause = where_clause.replace('{data_fim}', data_fim)
            
            # ✅ NOVO: Paginação (mais eficiente que limite fixo)
            # Validar parâmetros de paginação
            page = max(1, int(page)) if page else 1
            per_page = min(max(1, int(per_page) if per_page else 50), 100)  # Máximo 100 por página
            
            # Calcular offset
            offset = (page - 1) * per_page
            
            # ✅ NOVO: Contar total de registros (para paginação)
            query_count = f"""
                SELECT COUNT(*) as total
                FROM dbo.MOVIMENTACAO_BANCARIA mb
                WHERE {where_clause}
            """
            
            resultado_count = self.sql_adapter.execute_query(query_count, database=self.sql_adapter.database)
            total_registros = 0
            if resultado_count.get('success') and resultado_count.get('data'):
                total_registros = resultado_count['data'][0].get('total', 0) if resultado_count['data'] else 0
            
            total_pages = (total_registros + per_page - 1) // per_page if total_registros > 0 else 0
            
            logger.info(f"📄 Paginação: página {page}, {per_page} por página, total: {total_registros} registros ({total_pages} páginas)")
            
            # ✅ NOVO: Query com paginação usando OFFSET/FETCH (SQL Server 2012+)
            # Mais eficiente que TOP quando há paginação
            # ✅ CORREÇÃO: Usar DISTINCT para garantir que não haja duplicatas na visualização
            # (mesmo que id_movimentacao seja PK, garante consistência se houver duplicatas no banco)
            query = f"""
                SELECT DISTINCT
                    mb.id_movimentacao,
                    mb.banco_origem,
                    mb.agencia_origem,
                    mb.conta_origem,
                    mb.data_movimentacao,
                    mb.data_lancamento,
                    mb.valor_movimentacao,
                    mb.sinal_movimentacao,
                    mb.tipo_movimentacao,
                    CAST(mb.descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao,
                    mb.cpf_cnpj_contrapartida,
                    CAST(mb.nome_contrapartida AS VARCHAR(MAX)) as nome_contrapartida,
                    mb.processo_referencia,
                    mb.criado_em,
                    mb.hash_dados,
                    mb.json_dados_originais
                FROM dbo.MOVIMENTACAO_BANCARIA mb
                WHERE {where_clause}
                ORDER BY mb.data_movimentacao DESC, mb.criado_em DESC
                OFFSET {offset} ROWS
                FETCH NEXT {per_page} ROWS ONLY
            """
            
            logger.info(f"🔍 Listando lançamentos não classificados (limite: {limite})")
            logger.info(f"📊 Banco de dados: {self.sql_adapter.database}")
            logger.debug(f"📝 Query SQL completa:\n{query}")
            
            # ✅ DEBUG: Verificar se há lançamentos na tabela antes de filtrar
            query_count = f"""
                SELECT COUNT(*) as total
                FROM dbo.MOVIMENTACAO_BANCARIA mb
            """
            resultado_count = self.sql_adapter.execute_query(query_count, database=self.sql_adapter.database)
            total_geral = 0
            if resultado_count.get('success') and resultado_count.get('data'):
                total_geral = resultado_count['data'][0].get('total', 0) if resultado_count['data'] else 0
                logger.info(f"📊 Total de lançamentos na tabela MOVIMENTACAO_BANCARIA: {total_geral}")
            else:
                logger.warning(f"⚠️ Não foi possível contar lançamentos: {resultado_count.get('error')}")
            
            # ✅ DEBUG: Verificar se a tabela LANCAMENTO_TIPO_DESPESA existe
            query_check_table = """
                SELECT COUNT(*) as total
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'LANCAMENTO_TIPO_DESPESA'
            """
            resultado_table = self.sql_adapter.execute_query(query_check_table, database=self.sql_adapter.database)
            if resultado_table.get('success') and resultado_table.get('data'):
                table_exists = resultado_table['data'][0].get('total', 0) > 0 if resultado_table['data'] else False
                if not table_exists:
                    logger.error(f"❌ Tabela LANCAMENTO_TIPO_DESPESA não existe no banco {self.sql_adapter.database}!")
                    return {
                        'sucesso': False,
                        'erro': 'TABELA_NAO_EXISTE',
                        'mensagem': f'Tabela LANCAMENTO_TIPO_DESPESA não existe no banco {self.sql_adapter.database}',
                        'lancamentos': []
                    }
                logger.info(f"✅ Tabela LANCAMENTO_TIPO_DESPESA existe no banco {self.sql_adapter.database}")
            else:
                logger.warning(f"⚠️ Não foi possível verificar se a tabela existe: {resultado_table.get('error')}")
            
            resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
            
            if not resultado.get('success'):
                error_msg = resultado.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro ao listar lançamentos não classificados: {error_msg}")
                logger.error(f"❌ Query que falhou:\n{query}")
                return {
                    'sucesso': False,
                    'erro': 'ERRO_CONSULTA',
                    'mensagem': f'Erro ao consultar lançamentos: {error_msg}',
                    'lancamentos': []
                }
            
            rows = resultado.get('data', [])
            logger.info(f"📊 Lançamentos não classificados encontrados na página {page}: {len(rows)} de {total_registros} total")
            
            # ✅ CORREÇÃO: Deduplicar por id_movimentacao (garantir que não haja duplicatas na visualização)
            # Mesmo que id_movimentacao seja PK, pode haver duplicatas se houver problema no banco
            ids_vistos = set()
            rows_dedup = []
            duplicatas_removidas = 0
            for row in rows:
                id_mov = row.get('id_movimentacao') if isinstance(row, dict) else (row[0] if len(row) > 0 else None)
                if id_mov and id_mov not in ids_vistos:
                    ids_vistos.add(id_mov)
                    rows_dedup.append(row)
                elif id_mov:
                    duplicatas_removidas += 1
                    logger.warning(f"⚠️ Duplicata removida na visualização: ID {id_mov}")
            
            if duplicatas_removidas > 0:
                logger.warning(f"⚠️ {duplicatas_removidas} duplicata(s) removida(s) na visualização")
            
            rows = rows_dedup
            logger.info(f"📊 Lançamentos após deduplicação: {len(rows)}")
            
            # ✅ DEBUG: Log detalhado se não encontrou nenhum
            if len(rows) == 0:
                logger.warning(f"⚠️ Nenhum lançamento não classificados encontrado!")
                logger.warning(f"⚠️ Query executada: {query[:200]}...")
                logger.warning(f"⚠️ Resultado completo: {resultado}")
                
                # ✅ DEBUG: Verificar quantos lançamentos têm classificação
                query_count_classificados = """
                    SELECT COUNT(*) as total
                    FROM dbo.MOVIMENTACAO_BANCARIA mb
                    WHERE EXISTS (
                        SELECT 1
                        FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
                        WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao
                    )
                """
                resultado_count_class = self.sql_adapter.execute_query(query_count_classificados, database=self.sql_adapter.database)
                if resultado_count_class.get('success') and resultado_count_class.get('data'):
                    total_class = resultado_count_class['data'][0].get('total', 0) if resultado_count_class['data'] else 0
                    logger.info(f"📊 Total de lançamentos CLASSIFICADOS: {total_class}")
                    logger.info(f"📊 Total de lançamentos GERAL: {total_geral}")
                    logger.info(f"📊 Diferença (não classificados esperados): {total_geral - total_class}")
            
            lancamentos = []
            for row in rows:
                if isinstance(row, dict):
                    sinal = row.get('sinal_movimentacao', 'C')
                    valor = float(row.get('valor_movimentacao', 0))
                    descricao = row.get('descricao_movimentacao', '')
                    processo_vinculado = row.get('processo_referencia')
                    
                    # ✅ Detecção conservadora: só marca se for claramente SISCOMEX ou já vinculado a processo
                    eh_possivel_imposto = self._eh_possivel_imposto_importacao(descricao, processo_vinculado)
                    
                    # ✅ NOVO: Extrair numeroDocumento do JSON original para facilitar identificação
                    numero_documento = None
                    json_original = row.get('json_dados_originais')
                    if json_original:
                        try:
                            import json as json_lib
                            dados_orig = json_lib.loads(json_original) if isinstance(json_original, str) else json_original
                            numero_documento = dados_orig.get('numeroDocumento') or dados_orig.get('transactionId')
                        except:
                            pass
                    
                    hash_dados = row.get('hash_dados', '')
                    
                    lancamento = {
                        'id_movimentacao': row.get('id_movimentacao'),
                        'id': row.get('id_movimentacao'),  # ✅ Para compatibilidade com frontend
                        'banco': row.get('banco_origem', ''),
                        'banco_origem': row.get('banco_origem', ''),
                        'agencia': row.get('agencia_origem', ''),
                        'agencia_origem': row.get('agencia_origem', ''),
                        'conta': row.get('conta_origem', ''),
                        'conta_origem': row.get('conta_origem', ''),
                        'data_movimentacao': str(row.get('data_movimentacao', ''))[:10],
                        'data_lancamento': str(row.get('data_lancamento', ''))[:10] if row.get('data_lancamento') else '',
                        'valor': valor,
                        'sinal': '+' if sinal == 'C' else '-',
                        'tipo': row.get('tipo_movimentacao', ''),
                        'tipo_movimentacao': row.get('tipo_movimentacao', ''),
                        'descricao': descricao,
                        'descricao_movimentacao': descricao,
                        'eh_possivel_imposto_importacao': eh_possivel_imposto,  # ✅ Flag conservadora
                        'requer_confirmacao': eh_possivel_imposto,  # ✅ Requer confirmação do usuário
                        'contrapartida': {
                            'cpf_cnpj': row.get('cpf_cnpj_contrapartida'),
                            'nome': row.get('nome_contrapartida')
                        },
                        'processo_vinculado': processo_vinculado,
                        'criado_em': str(row.get('criado_em', ''))[:19],
                        # ✅ NOVO: Informações para identificação de duplicatas
                        'numero_documento': numero_documento,
                        'hash_curto': hash_dados[:16] + '...' if hash_dados else None
                    }
                else:
                    # É uma tupla - mapear índices
                    sinal = row[7] if len(row) > 7 else 'C'
                    valor = float(row[6] if len(row) > 6 else 0)
                    descricao = row[9] if len(row) > 9 else ''
                    processo_vinculado = row[12] if len(row) > 12 else None
                    
                    # ✅ Detecção conservadora: só marca se for claramente SISCOMEX ou já vinculado a processo
                    eh_possivel_imposto = self._eh_possivel_imposto_importacao(descricao, processo_vinculado)
                    
                    lancamento = {
                        'id_movimentacao': row[0] if len(row) > 0 else None,
                        'id': row[0] if len(row) > 0 else None,  # ✅ Para compatibilidade com frontend
                        'banco': row[1] if len(row) > 1 else '',
                        'banco_origem': row[1] if len(row) > 1 else '',
                        'agencia': row[2] if len(row) > 2 else '',
                        'agencia_origem': row[2] if len(row) > 2 else '',
                        'conta': row[3] if len(row) > 3 else '',
                        'conta_origem': row[3] if len(row) > 3 else '',
                        'data_movimentacao': str(row[4])[:10] if len(row) > 4 and row[4] else '',
                        'data_lancamento': str(row[5])[:10] if len(row) > 5 and row[5] else '',
                        'valor': valor,
                        'sinal': '+' if sinal == 'C' else '-',
                        'tipo': row[8] if len(row) > 8 else '',
                        'tipo_movimentacao': row[8] if len(row) > 8 else '',
                        'descricao': descricao,
                        'descricao_movimentacao': descricao,
                        'eh_possivel_imposto_importacao': eh_possivel_imposto,  # ✅ Flag conservadora
                        'requer_confirmacao': eh_possivel_imposto,  # ✅ Requer confirmação do usuário
                        'contrapartida': {
                            'cpf_cnpj': row[10] if len(row) > 10 else None,
                            'nome': row[11] if len(row) > 11 else None
                        },
                        'processo_vinculado': processo_vinculado,
                        'criado_em': str(row[13])[:19] if len(row) > 13 and row[13] else ''
                    }
                lancamentos.append(lancamento)
            
            return {
                'sucesso': True,
                'total': total_registros,  # ✅ NOVO: Total de registros (não apenas da página)
                'page': page,  # ✅ NOVO: Página atual
                'per_page': per_page,  # ✅ NOVO: Itens por página
                'total_pages': total_pages,  # ✅ NOVO: Total de páginas
                'lancamentos': lancamentos
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar lançamentos não classificados: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e),
                'lancamentos': [],
                'total': 0,
                'page': page if 'page' in locals() else 1,
                'per_page': per_page if 'per_page' in locals() else 50,
                'total_pages': 0
            }
    
    def listar_lancamentos_classificados(
        self, 
        limite: int = 50, 
        processo_referencia: Optional[str] = None,
        data_inicio: Optional[str] = None, 
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista lançamentos bancários que já estão classificados (para permitir edição).
        
        Args:
            limite: Número máximo de lançamentos a retornar
            processo_referencia: Filtrar por processo específico (opcional)
            data_inicio: Data inicial (YYYY-MM-DD, opcional)
            data_fim: Data final (YYYY-MM-DD, opcional)
        
        Returns:
            Dict com sucesso, total e lista de lançamentos classificados
        """
        try:
            # Query para buscar lançamentos COM classificação
            where_parts = []
            
            # Condição principal: ter classificação
            where_parts.append("EXISTS (")
            where_parts.append("    SELECT 1")
            where_parts.append("    FROM dbo.LANCAMENTO_TIPO_DESPESA ltd")
            where_parts.append("    WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao")
            where_parts.append(")")
            
            # Filtro por processo (se fornecido)
            if processo_referencia:
                processo_ref_escaped = processo_referencia.replace("'", "''")
                where_parts.append(f"AND EXISTS (")
                where_parts.append(f"    SELECT 1")
                where_parts.append(f"    FROM dbo.LANCAMENTO_TIPO_DESPESA ltd2")
                where_parts.append(f"    WHERE ltd2.id_movimentacao_bancaria = mb.id_movimentacao")
                where_parts.append(f"    AND ltd2.processo_referencia = '{processo_ref_escaped}'")
                where_parts.append(f")")
            
            # Filtros de data (se fornecidos)
            if data_inicio:
                where_parts.append(f"AND CAST(mb.data_movimentacao AS DATE) >= '{data_inicio}'")
            if data_fim:
                where_parts.append(f"AND CAST(mb.data_movimentacao AS DATE) <= '{data_fim}'")
            
            where_clause = ' '.join(where_parts)
            
            # ✅ CORREÇÃO: processo_referencia vem de LANCAMENTO_TIPO_DESPESA, não de MOVIMENTACAO_BANCARIA
            # ✅ CORREÇÃO: Converter campos TEXT para VARCHAR antes de usar DISTINCT (SQL Server não permite DISTINCT com TEXT)
            query = f"""
                WITH LancamentosClassificados AS (
                    SELECT DISTINCT
                        mb.id_movimentacao,
                        mb.banco_origem,
                        mb.agencia_origem,
                        mb.conta_origem,
                        mb.data_movimentacao,
                        mb.data_lancamento,
                        mb.valor_movimentacao,
                        mb.sinal_movimentacao,
                        mb.tipo_movimentacao,
                        CAST(mb.descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao,
                        mb.cpf_cnpj_contrapartida,
                        CAST(mb.nome_contrapartida AS VARCHAR(MAX)) as nome_contrapartida,
                        (SELECT TOP 1 ltd3.processo_referencia 
                         FROM dbo.LANCAMENTO_TIPO_DESPESA ltd3 
                         WHERE ltd3.id_movimentacao_bancaria = mb.id_movimentacao 
                           AND ltd3.processo_referencia IS NOT NULL 
                           AND LTRIM(RTRIM(ltd3.processo_referencia)) != ''
                         ORDER BY ltd3.criado_em DESC) as processo_referencia,
                        mb.criado_em,
                        mb.hash_dados,
                        mb.json_dados_originais
                    FROM dbo.MOVIMENTACAO_BANCARIA mb
                    WHERE {where_clause}
                )
                SELECT TOP {limite} *
                FROM LancamentosClassificados
                ORDER BY data_movimentacao DESC, criado_em DESC
            """
            
            logger.info(f"🔍 Listando lançamentos classificados (limite: {limite}, processo: {processo_referencia or 'todos'})")
            logger.debug(f"📝 Query SQL: {query[:300]}...")  # Log parcial da query para debug
            
            resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
            
            if not resultado.get('success'):
                error_msg = resultado.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro ao listar lançamentos classificados: {error_msg}")
                return {
                    'sucesso': False,
                    'erro': 'ERRO_CONSULTA',
                    'mensagem': f'Erro ao consultar lançamentos: {error_msg}',
                    'lancamentos': []
                }
            
            rows = resultado.get('data', [])
            
            # ✅ CORREÇÃO: Deduplicar por id_movimentacao (garantir que não haja duplicatas na visualização)
            ids_vistos = set()
            rows_dedup = []
            duplicatas_removidas = 0
            for row in rows:
                id_mov = row.get('id_movimentacao') if isinstance(row, dict) else (row[0] if len(row) > 0 else None)
                if id_mov and id_mov not in ids_vistos:
                    ids_vistos.add(id_mov)
                    rows_dedup.append(row)
                elif id_mov:
                    duplicatas_removidas += 1
                    logger.warning(f"⚠️ Duplicata removida na visualização (classificados): ID {id_mov}")
            
            if duplicatas_removidas > 0:
                logger.warning(f"⚠️ {duplicatas_removidas} duplicata(s) removida(s) na visualização (classificados)")
            
            rows = rows_dedup[:limite]  # Limitar resultados após deduplicação
            
            lancamentos = []
            for row in rows:
                if isinstance(row, dict):
                    sinal = row.get('sinal_movimentacao', 'C')
                    valor = float(row.get('valor_movimentacao', 0))
                    descricao = row.get('descricao_movimentacao', '')
                    processo_vinculado = row.get('processo_referencia')
                    
                    # ✅ NOVO: Extrair numeroDocumento do JSON original
                    numero_documento = None
                    json_original = row.get('json_dados_originais')
                    if json_original:
                        try:
                            import json as json_lib
                            dados_orig = json_lib.loads(json_original) if isinstance(json_original, str) else json_original
                            numero_documento = dados_orig.get('numeroDocumento') or dados_orig.get('transactionId')
                        except:
                            pass
                    
                    hash_dados = row.get('hash_dados', '')
                    
                    lancamento = {
                        'id_movimentacao': row.get('id_movimentacao'),
                        'banco': row.get('banco_origem', ''),
                        'agencia': row.get('agencia_origem', ''),
                        'conta': row.get('conta_origem', ''),
                        'data_movimentacao': str(row.get('data_movimentacao', ''))[:10],
                        'data_lancamento': str(row.get('data_lancamento', ''))[:10] if row.get('data_lancamento') else '',
                        'valor': valor,
                        'sinal': '+' if sinal == 'C' else '-',
                        'tipo': row.get('tipo_movimentacao', ''),
                        'descricao': descricao,
                        'contrapartida': {
                            'cpf_cnpj': row.get('cpf_cnpj_contrapartida'),
                            'nome': row.get('nome_contrapartida')
                        },
                        'processo_vinculado': processo_vinculado,
                        # ✅ NOVO: Informações para identificação
                        'numero_documento': numero_documento,
                        'hash_curto': hash_dados[:16] + '...' if hash_dados else None,
                        'criado_em': str(row.get('criado_em', ''))[:19],
                        'classificado': True  # ✅ Flag indicando que já está classificado
                    }
                else:
                    # É uma tupla - mapear índices (similar ao código anterior)
                    sinal = row[7] if len(row) > 7 else 'C'
                    valor = float(row[6] if len(row) > 6 else 0)
                    descricao = row[9] if len(row) > 9 else ''
                    
                    lancamento = {
                        'id_movimentacao': row[0] if len(row) > 0 else None,
                        'banco': row[1] if len(row) > 1 else '',
                        'agencia': row[2] if len(row) > 2 else '',
                        'conta': row[3] if len(row) > 3 else '',
                        'data_movimentacao': str(row[4])[:10] if len(row) > 4 and row[4] else '',
                        'data_lancamento': str(row[5])[:10] if len(row) > 5 and row[5] else '',
                        'valor': valor,
                        'sinal': '+' if sinal == 'C' else '-',
                        'tipo': row[8] if len(row) > 8 else '',
                        'descricao': descricao,
                        'contrapartida': {
                            'cpf_cnpj': row[10] if len(row) > 10 else None,
                            'nome': row[11] if len(row) > 11 else None
                        },
                        'processo_vinculado': row[12] if len(row) > 12 else None,
                        'criado_em': str(row[13])[:19] if len(row) > 13 and row[13] else '',
                        'classificado': True
                    }
                
                lancamentos.append(lancamento)
            
            logger.info(f"✅ {len(lancamentos)} lançamento(s) classificado(s) encontrado(s)")
            
            return {
                'sucesso': True,
                'lancamentos': lancamentos,
                'total': len(lancamentos)
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao listar lançamentos classificados: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro ao listar lançamentos: {str(e)}',
                'lancamentos': []
            }
            
            lancamentos = []
            for row in rows:
                # ✅ CORREÇÃO: O adapter pode retornar tuplas (índice) ou dicts (chave)
                if isinstance(row, dict):
                    sinal = row.get('sinal_movimentacao', 'C')
                    valor = float(row.get('valor_movimentacao', 0))
                    descricao = row.get('descricao_movimentacao', '')
                    processo_vinculado = row.get('processo_referencia')
                    
                    # ✅ Detecção conservadora: só marca se for claramente SISCOMEX ou já vinculado a processo
                    eh_possivel_imposto = self._eh_possivel_imposto_importacao(descricao, processo_vinculado)
                    
                    lancamento = {
                        'id_movimentacao': row.get('id_movimentacao'),
                        'banco': row.get('banco_origem', ''),
                        'agencia': row.get('agencia_origem', ''),
                        'conta': row.get('conta_origem', ''),
                        'data_movimentacao': str(row.get('data_movimentacao', ''))[:10],
                        'data_lancamento': str(row.get('data_lancamento', ''))[:10] if row.get('data_lancamento') else '',
                        'valor': valor,
                        'sinal': '+' if sinal == 'C' else '-',
                        'tipo': row.get('tipo_movimentacao', ''),
                        'descricao': descricao,
                        'eh_possivel_imposto_importacao': eh_possivel_imposto,  # ✅ Flag conservadora
                        'requer_confirmacao': eh_possivel_imposto,  # ✅ Requer confirmação do usuário
                        'contrapartida': {
                            'cpf_cnpj': row.get('cpf_cnpj_contrapartida'),
                            'nome': row.get('nome_contrapartida')
                        },
                        'processo_vinculado': row.get('processo_referencia'),
                        'criado_em': str(row.get('criado_em', ''))[:19]
                    }
                else:
                    # É uma tupla - mapear índices
                    sinal = row[7] if len(row) > 7 else 'C'
                    valor = float(row[6] if len(row) > 6 else 0)
                    descricao = row[9] if len(row) > 9 else ''
                    processo_vinculado = row[12] if len(row) > 12 else None
                    
                    # ✅ Detecção conservadora: só marca se for claramente SISCOMEX ou já vinculado a processo
                    eh_possivel_imposto = self._eh_possivel_imposto_importacao(descricao, processo_vinculado)
                    
                    lancamento = {
                        'id_movimentacao': row[0] if len(row) > 0 else None,
                        'banco': row[1] if len(row) > 1 else '',
                        'agencia': row[2] if len(row) > 2 else '',
                        'conta': row[3] if len(row) > 3 else '',
                        'data_movimentacao': str(row[4])[:10] if len(row) > 4 and row[4] else '',
                        'data_lancamento': str(row[5])[:10] if len(row) > 5 and row[5] else '',
                        'valor': valor,
                        'sinal': '+' if sinal == 'C' else '-',
                        'tipo': row[8] if len(row) > 8 else '',
                        'descricao': descricao,
                        'eh_possivel_imposto_importacao': eh_possivel_imposto,  # ✅ Flag conservadora
                        'requer_confirmacao': eh_possivel_imposto,  # ✅ Requer confirmação do usuário
                        'contrapartida': {
                            'cpf_cnpj': row[10] if len(row) > 10 else None,
                            'nome': row[11] if len(row) > 11 else None
                        },
                        'processo_vinculado': processo_vinculado,
                        'criado_em': str(row[13])[:19] if len(row) > 13 and row[13] else ''
                    }
                lancamentos.append(lancamento)
            
            return {
                'sucesso': True,
                'total': len(lancamentos),
                'lancamentos': lancamentos
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar lançamentos não classificados: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e),
                'lancamentos': []
            }
    
    def listar_tipos_despesa(self) -> Dict[str, Any]:
        """
        Lista todos os tipos de despesa cadastrados.
        
        Returns:
            Dict com sucesso e lista de tipos de despesa
        """
        try:
            # ✅ CORREÇÃO: Verificar se a tabela existe primeiro
            query_check = """
                SELECT COUNT(*) as total
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'TIPO_DESPESA'
            """
            check_result = self.sql_adapter.execute_query(query_check, database=self.sql_adapter.database)
            
            if not check_result.get('success') or not check_result.get('data'):
                logger.error("❌ Erro ao verificar se tabela TIPO_DESPESA existe")
                return {
                    'sucesso': False,
                    'erro': 'TABELA_NAO_EXISTE',
                    'mensagem': 'Tabela TIPO_DESPESA não encontrada. Execute o script criar_catalogo_despesas_via_python.py primeiro.',
                    'tipos': []
                }
            
            # Verificar se tabela existe
            table_exists = False
            if check_result.get('data'):
                row = check_result['data'][0] if isinstance(check_result['data'], list) and len(check_result['data']) > 0 else {}
                if isinstance(row, dict):
                    total = row.get('total', 0)
                else:
                    total = row[0] if len(row) > 0 else 0
                table_exists = total > 0
            
            if not table_exists:
                logger.error("❌ Tabela TIPO_DESPESA não existe no banco de dados")
                return {
                    'sucesso': False,
                    'erro': 'TABELA_NAO_EXISTE',
                    'mensagem': 'Tabela TIPO_DESPESA não encontrada. Execute o script criar_catalogo_despesas_via_python.py primeiro.',
                    'tipos': []
                }
            
            # ✅ CORREÇÃO: Query usando campos corretos da tabela
            # Query simplificada que funciona mesmo se algumas colunas forem NULL
            # Tenta primeiro com filtro de ativo, depois sem filtro
            query = """
                SELECT 
                    id_tipo_despesa,
                    nome_despesa,
                    ISNULL(descricao_despesa, '') as descricao,
                    ISNULL(categoria_despesa, 'OUTROS') as categoria_despesa,
                    plano_contas_codigo
                FROM dbo.TIPO_DESPESA
                WHERE (ativo IS NULL OR ativo = 1)
                ORDER BY ISNULL(ordem_exibicao, 0), categoria_despesa, nome_despesa
            """
            
            logger.info("🔍 Listando tipos de despesa")
            
            resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
            
            # ✅ CORREÇÃO: Se falhar, tenta query mais simples (sem ativo e ordem_exibicao)
            if not resultado.get('success'):
                logger.warning("⚠️ Query completa falhou, tentando query simplificada...")
                query_simples = """
                    SELECT 
                        id_tipo_despesa,
                        nome_despesa,
                        ISNULL(descricao_despesa, '') as descricao,
                        ISNULL(categoria_despesa, 'OUTROS') as categoria_despesa,
                        plano_contas_codigo
                    FROM dbo.TIPO_DESPESA
                    ORDER BY categoria_despesa, nome_despesa
                """
                resultado = self.sql_adapter.execute_query(query_simples, database=self.sql_adapter.database)
            
            if not resultado.get('success'):
                error_msg = resultado.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro ao listar tipos de despesa: {error_msg}")
                return {
                    'sucesso': False,
                    'erro': 'ERRO_CONSULTA',
                    'mensagem': f'Erro ao consultar tipos de despesa: {error_msg}',
                    'tipos': []
                }
            
            rows = resultado.get('data', [])
            
            # ✅ CORREÇÃO: O adapter pode retornar tuplas (índice) ou dicts (chave)
            tipos_despesa = []
            for row in rows:
                # Tentar como dict primeiro, depois como tupla
                if isinstance(row, dict):
                    tipo = {
                        'id_tipo_despesa': row.get('id_tipo_despesa'),
                        'nome_despesa': row.get('nome_despesa') or '',
                        'descricao': row.get('descricao') or row.get('descricao_despesa') or None,
                        'categoria_despesa': row.get('categoria_despesa') or '',
                        'plano_contas_codigo': row.get('plano_contas_codigo') or None
                    }
                else:
                    # É uma tupla - mapear índices
                    tipo = {
                        'id_tipo_despesa': row[0] if len(row) > 0 else None,
                        'nome_despesa': row[1] if len(row) > 1 else '',
                        'descricao': row[2] if len(row) > 2 else None,
                        'categoria_despesa': row[3] if len(row) > 3 else '',
                        'plano_contas_codigo': row[4] if len(row) > 4 else None
                    }
                tipos_despesa.append(tipo)
            
            logger.info(f"✅ {len(tipos_despesa)} tipos de despesa encontrados")
            
            return {
                'sucesso': True,
                'total': len(tipos_despesa),
                'tipos': tipos_despesa  # ✅ CORREÇÃO: Mudado de 'tipos_despesa' para 'tipos' para corresponder ao frontend
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Erro ao listar tipos de despesa: {error_msg}", exc_info=True)
            
            # ✅ CORREÇÃO: Mensagem mais específica para o usuário
            if 'TIPO_DESPESA' in error_msg.upper() or 'INVALID OBJECT' in error_msg.upper():
                mensagem = 'Tabela TIPO_DESPESA não encontrada. Execute o script criar_catalogo_despesas_via_python.py primeiro.'
            elif 'COLUMN' in error_msg.upper() or 'INVALID COLUMN' in error_msg.upper():
                mensagem = f'Erro na estrutura da tabela: {error_msg}'
            else:
                mensagem = f'Erro ao consultar tipos de despesa: {error_msg}'
            
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': mensagem,
                'tipos': []
            }
    
    def classificar_lancamento(
        self,
        id_movimentacao: int,
        classificacoes: List[Dict[str, Any]],
        distribuicao_impostos: Optional[Dict[str, float]] = None,
        processo_referencia: Optional[str] = None  # ✅ NOVO: Processo quando houver apenas impostos
    ) -> Dict[str, Any]:
        # ✅ Robustez: garantir tipos esperados (evita "object of type 'int' has no len()")
        if classificacoes is None:
            classificacoes = []
        elif isinstance(classificacoes, dict):
            classificacoes = [classificacoes]
        elif not isinstance(classificacoes, list):
            logger.warning(
                f"⚠️ classificar_lancamento: classificacoes veio como {type(classificacoes).__name__}. Forçando lista vazia."
            )
            classificacoes = []

        if isinstance(distribuicao_impostos, list):
            distribuicao_dict = {}
            for item in distribuicao_impostos:
                if isinstance(item, dict):
                    tipo = item.get('tipo_imposto') or item.get('tipo') or item.get('imposto')
                    valor = item.get('valor_brl') if 'valor_brl' in item else item.get('valor')
                    if tipo is not None and valor is not None:
                        distribuicao_dict[str(tipo)] = valor
            distribuicao_impostos = distribuicao_dict
        elif distribuicao_impostos is None:
            distribuicao_impostos = {}
        elif not isinstance(distribuicao_impostos, dict):
            logger.warning(
                f"⚠️ classificar_lancamento: distribuicao_impostos veio como {type(distribuicao_impostos).__name__}. Forçando dict vazio."
            )
            distribuicao_impostos = {}

        # ✅ DEBUG: Logar parâmetros recebidos
        logger.info(f"🔍 [DEBUG classificar_lancamento] Parâmetros recebidos:")
        logger.info(f"   - id_movimentacao: {id_movimentacao}")
        logger.info(f"   - classificacoes type: {type(classificacoes).__name__}, len: {len(classificacoes)}")
        logger.info(f"   - distribuicao_impostos type: {type(distribuicao_impostos).__name__}, len: {len(distribuicao_impostos)}")
        logger.info(f"   - distribuicao_impostos keys: {list(distribuicao_impostos.keys()) if distribuicao_impostos else 'N/A'}")
        logger.info(f"   - processo_referencia (parâmetro): {processo_referencia}")
        """
        Classifica um lançamento bancário vinculando-o a tipos de despesa e processos.
        
        Args:
            id_movimentacao: ID do lançamento bancário
            classificacoes: Lista de classificações, cada uma contendo:
                - id_tipo_despesa: ID do tipo de despesa
                - processo_referencia: Referência do processo (opcional)
                - valor_despesa: Valor específico desta despesa (opcional)
                - percentual_valor: Percentual do valor total (opcional)
        
        Returns:
            Dict com sucesso e mensagem
        """
        try:
            # 1. Validar lançamento existe
            query_check = f"""
                SELECT id_movimentacao, valor_movimentacao, sinal_movimentacao
                FROM dbo.MOVIMENTACAO_BANCARIA
                WHERE id_movimentacao = {id_movimentacao}
            """
            
            resultado_check = self.sql_adapter.execute_query(query_check, database=self.sql_adapter.database)
            
            if not resultado_check.get('success') or not resultado_check.get('data'):
                return {
                    'sucesso': False,
                    'erro': 'LANCAMENTO_NAO_ENCONTRADO',
                    'mensagem': f'Lançamento {id_movimentacao} não encontrado'
                }
            
            lancamento_row = resultado_check['data'][0]
            valor_total = float(lancamento_row.get('valor_movimentacao', 0))
            
            # 2. Validar classificações OU distribuição de impostos
            tem_distribuicao_impostos = bool(distribuicao_impostos) and len(distribuicao_impostos) > 0
            if (not classificacoes or len(classificacoes) == 0) and not tem_distribuicao_impostos:
                return {
                    'sucesso': False,
                    'erro': 'CLASSIFICACOES_VAZIAS',
                    'mensagem': 'É necessário fornecer pelo menos uma classificação ou distribuição de impostos'
                }
            
            # 3. Validar soma de valores/percentuais (apenas se houver classificações)
            if classificacoes and len(classificacoes) > 0:
                soma_valores = 0.0
                soma_percentuais = 0.0
                
                for classificacao in classificacoes:
                    if 'valor_despesa' in classificacao and classificacao['valor_despesa']:
                        soma_valores += float(classificacao['valor_despesa'])
                    elif 'percentual_valor' in classificacao and classificacao['percentual_valor']:
                        soma_percentuais += float(classificacao['percentual_valor'])
                
                # Se houver valores absolutos, validar que não excedem o total
                if soma_valores > 0 and soma_valores > abs(valor_total) * 1.01:  # 1% de tolerância para arredondamento
                    return {
                        'sucesso': False,
                        'erro': 'VALORES_EXCEDEM_TOTAL',
                        'mensagem': f'A soma dos valores ({soma_valores:,.2f}) excede o valor total do lançamento ({abs(valor_total):,.2f})'
                    }
                
                # Se houver percentuais, validar que não excedem 100%
                if soma_percentuais > 0 and soma_percentuais > 100.01:  # 1% de tolerância
                    return {
                        'sucesso': False,
                        'erro': 'PERCENTUAIS_EXCEDEM_100',
                        'mensagem': f'A soma dos percentuais ({soma_percentuais:.2f}%) excede 100%'
                    }
            
            # ✅ NOVO: Se houver apenas distribuição de impostos, validar soma dos impostos
            if tem_distribuicao_impostos and (not classificacoes or len(classificacoes) == 0):
                soma_impostos = sum(float(v) for v in distribuicao_impostos.values() if v)
                valor_total_abs = abs(valor_total)  # Lançamento é negativo, usar valor absoluto
                
                if soma_impostos > valor_total_abs * 1.01:  # 1% de tolerância
                    return {
                        'sucesso': False,
                        'erro': 'IMPOSTOS_EXCEDEM_TOTAL',
                        'mensagem': f'A soma dos impostos (R$ {soma_impostos:,.2f}) excede o valor total do lançamento (R$ {valor_total_abs:,.2f})'
                    }
            
            # 4. Inserir classificações (se houver)
            sucesso_total = True
            erros = []
            
            # ✅ CORREÇÃO: Só tentar inserir classificações se houver alguma
            if classificacoes and len(classificacoes) > 0:
                for idx, classificacao in enumerate(classificacoes):
                    id_tipo_despesa = classificacao.get('id_tipo_despesa')
                    processo_referencia = classificacao.get('processo_referencia')
                    categoria_processo = None
                    
                    if processo_referencia and '.' in processo_referencia:
                        categoria_processo = processo_referencia.split('.')[0]
                    
                    valor_despesa = classificacao.get('valor_despesa')
                    percentual_valor = classificacao.get('percentual_valor')
                    
                    # Se não forneceu valor nem percentual, usar 100% (se for única classificação) ou distribuir
                    if not valor_despesa and not percentual_valor:
                        if len(classificacoes) == 1:
                            valor_despesa = valor_total
                        else:
                            # Distribuir igualmente entre todas
                            valor_despesa = valor_total / len(classificacoes)
                    
                    # Calcular valor se foi fornecido percentual
                    if not valor_despesa and percentual_valor:
                        valor_despesa = (valor_total * float(percentual_valor)) / 100.0
                    
                    # Escapar valores para SQL
                    def _escapar_sql(valor):
                        if valor is None:
                            return 'NULL'
                        if isinstance(valor, str):
                            valor_sql = valor.replace("'", "''")
                            return f"'{valor_sql}'"
                        return str(valor)
                    
                    query_insert = f"""
                        INSERT INTO dbo.LANCAMENTO_TIPO_DESPESA (
                            id_movimentacao_bancaria,
                            id_tipo_despesa,
                            processo_referencia,
                            categoria_processo,
                            valor_despesa,
                            percentual_valor,
                            origem_classificacao,
                            natureza_recurso
                        ) VALUES (
                            {id_movimentacao},
                            {id_tipo_despesa},
                            {_escapar_sql(processo_referencia)},
                            {_escapar_sql(categoria_processo)},
                            {valor_despesa if valor_despesa else 'NULL'},
                            {percentual_valor if percentual_valor else 'NULL'},
                            'MANUAL',
                            {_escapar_sql(classificacao.get('natureza_recurso', 'OPERACIONAL'))}
                        )
                    """
                    
                    resultado_insert = self.sql_adapter.execute_query(query_insert, database=self.sql_adapter.database)
                    
                    # ✅ NOVO (24/01/2026): Se for APORTE_TRIBUTOS, registrar na carteira virtual
                    if resultado_insert.get('success') and classificacao.get('natureza_recurso') == 'APORTE_TRIBUTOS':
                        try:
                            from services.banco_carteira_virtual_service import BancoCarteiraVirtualService
                            from services.consulta_cpf_cnpj_service import ConsultaCpfCnpjService
                            
                            # 1. Obter CNPJ/Nome da contrapartida do lançamento
                            query_lanc = f"SELECT cpf_cnpj_contrapartida, nome_contrapartida FROM dbo.MOVIMENTACAO_BANCARIA WHERE id_movimentacao = {id_movimentacao}"
                            res_lanc = self.sql_adapter.execute_query(query_lanc)
                            
                            if res_lanc.get('success') and res_lanc.get('data'):
                                lanc = res_lanc['data'][0]
                                cnpj = lanc.get('cpf_cnpj_contrapartida')
                                nome = lanc.get('nome_contrapartida') or 'Cliente Desconhecido'
                                
                                if cnpj:
                                    carteira_svc = BancoCarteiraVirtualService()
                                    carteira_svc.registrar_aporte(
                                        cnpj_cliente=cnpj,
                                        nome_cliente=nome,
                                        id_movimentacao=id_movimentacao,
                                        valor=float(valor_despesa)
                                    )
                                    logger.info(f"✅ Aporte de R$ {valor_despesa} registrado para CNPJ {cnpj}")
                        except Exception as e_aporte:
                            logger.error(f"⚠️ Erro ao registrar aporte na carteira: {e_aporte}")

                    # ✅ NOVO (24/01/2026): Se for UTILIZACAO (Imposto), registrar saída da carteira
                    if resultado_insert.get('success') and (
                        classificacao.get('tipo_despesa_nome') == 'Impostos de Importação' or 
                        classificacao.get('id_tipo_despesa') == 1 # ID padrão para impostos
                    ):
                        try:
                            from services.banco_carteira_virtual_service import BancoCarteiraVirtualService
                            from services.processo_repository import ProcessoRepository
                            
                            if processo_referencia:
                                # 1. Descobrir o CNPJ do importador do processo
                                repo = ProcessoRepository()
                                proc = repo.buscar_por_referencia(processo_referencia)
                                
                                if proc and proc.dados_completos:
                                    # Tentar pegar CNPJ do importador (DI ou DUIMP)
                                    di = proc.dados_completos.get('di', {})
                                    duimp = proc.dados_completos.get('duimp', {})
                                    cnpj_importador = di.get('cnpj_importador') or duimp.get('cnpj_importador')
                                    
                                    if cnpj_importador:
                                        carteira_svc = BancoCarteiraVirtualService()
                                        carteira_svc.registrar_utilizacao(
                                            cnpj_cliente=cnpj_importador,
                                            id_movimentacao=id_movimentacao,
                                            valor=float(valor_despesa),
                                            processo_ref=processo_referencia
                                        )
                                        logger.info(f"✅ Utilização de R$ {valor_despesa} registrada para cliente {cnpj_importador}")
                        except Exception as e_util:
                            logger.error(f"⚠️ Erro ao registrar utilização na carteira: {e_util}")
                    
                    if not resultado_insert.get('success'):
                        erro_msg = resultado_insert.get('error', 'Erro desconhecido')
                        erros.append(f"Classificação {idx + 1}: {erro_msg}")
                        sucesso_total = False
                        logger.error(f"❌ Erro ao inserir classificação {idx + 1}: {erro_msg}")
            else:
                # ✅ Se não houver classificações, mas houver distribuição de impostos, considerar sucesso
                if tem_distribuicao_impostos:
                    logger.info(f"✅ Processando apenas distribuição de impostos (sem classificações)")
            
            # ✅ NOVO: Se houver distribuição de impostos confirmada, gravar na tabela IMPOSTO_IMPORTACAO
            # Esta é a forma INTELIGENTE: usuário confirma, informa processo, sistema busca DI/DUIMP pela API oficial
            # e preenche automaticamente. Ao salvar, grava tudo automaticamente.
            
            # Verificar se alguma classificação tem flag de "impostos_importacao" confirmado
            # ✅ CORREÇÃO: Se houver distribuição de impostos, considerar como confirmação implícita
            tem_confirmacao_impostos = (
                (isinstance(distribuicao_impostos, dict) and len(distribuicao_impostos) > 0) or  # ✅ Se houver distribuição, já é confirmação
                any(
                    classificacao.get('impostos_importacao_confirmado', False)
                    for classificacao in classificacoes
                )
            )
            
            logger.info(f"🔍 Verificando gravação de impostos:")
            logger.info(f"   - sucesso_total: {sucesso_total}")
            logger.info(f"   - tem_confirmacao_impostos: {tem_confirmacao_impostos}")
            logger.info(f"   - distribuicao_impostos existe: {bool(distribuicao_impostos)}")
            logger.info(f"   - distribuicao_impostos len: {len(distribuicao_impostos) if isinstance(distribuicao_impostos, dict) else 0}")
            logger.info(
                f"   - distribuicao_impostos keys: {list(distribuicao_impostos.keys()) if isinstance(distribuicao_impostos, dict) and distribuicao_impostos else 'N/A'}"
            )
            logger.info(f"   - processo_referencia: {processo_referencia}")
            logger.info(f"   - classificacoes len: {len(classificacoes)}")
            
            # ✅ NOVO: Se houver distribuição de impostos no body, usar ela (já vem preenchida da API oficial)
            if sucesso_total and tem_confirmacao_impostos and isinstance(distribuicao_impostos, dict) and len(distribuicao_impostos) > 0:
                logger.info(f"✅ Condições atendidas para gravar impostos. Distribuição: {list(distribuicao_impostos.keys())}")
                
                # ✅ CORREÇÃO: Buscar processo_referencia das classificações OU do parâmetro direto
                processos_impostos = []
                
                # 1. Tentar das classificações
                for classificacao in classificacoes:
                    proc_ref = classificacao.get('processo_referencia')
                    if proc_ref and proc_ref not in processos_impostos:
                        processos_impostos.append(proc_ref)
                
                # 2. Se não encontrou nas classificações, usar o parâmetro direto
                if not processos_impostos and processo_referencia:
                    processos_impostos.append(processo_referencia)
                    logger.info(f"✅ Usando processo_referencia do parâmetro direto: '{processo_referencia}'")
                
                logger.info(f"📋 Processos para gravar impostos: {processos_impostos}")
                
                # Para cada processo, gravar impostos distribuídos
                if processos_impostos:
                    logger.info(f"✅ Iniciando gravação de impostos para {len(processos_impostos)} processo(s)")
                    try:
                        from services.imposto_valor_service import get_imposto_valor_service
                        from db_manager import obter_dados_documentos_processo
                        
                        imposto_service = get_imposto_valor_service()
                        
                        for proc_ref in processos_impostos:
                            # ✅ CORREÇÃO: Normalizar processo_referencia (trim e uppercase para consistência)
                            proc_ref_normalizado = proc_ref.strip().upper() if proc_ref else ''
                            logger.info(f"💰 Gravando impostos para processo '{proc_ref}' (normalizado: '{proc_ref_normalizado}')")
                            
                            # Buscar DI/DUIMP do processo para obter número do documento
                            dados_docs = obter_dados_documentos_processo(proc_ref, usar_sql_server=True)
                            di_data = dados_docs.get('dis', [])
                            duimp_data = dados_docs.get('duimps', [])
                            
                            numero_documento = None
                            tipo_documento = None
                            
                            # Priorizar DI, depois DUIMP
                            if di_data and len(di_data) > 0:
                                numero_documento = di_data[0].get('numero', '')
                                tipo_documento = 'DI'
                            elif duimp_data and len(duimp_data) > 0:
                                numero_documento = duimp_data[0].get('numero', '')
                                tipo_documento = 'DUIMP'
                            
                            # Gravar cada imposto da distribuição
                            total_gravados = 0
                            for tipo_imposto, valor_brl in distribuicao_impostos.items():
                                # ✅ Robustez: aceitar valor como float/int ou string pt-BR ("746,79", "R$ 746,79")
                                try:
                                    if isinstance(valor_brl, str):
                                        valor_txt = (
                                            valor_brl.replace("R$", "")
                                            .replace(" ", "")
                                            .replace(".", "")
                                            .replace(",", ".")
                                        )
                                        valor_float = float(valor_txt) if valor_txt else 0.0
                                    else:
                                        valor_float = float(valor_brl) if valor_brl is not None else 0.0
                                except Exception:
                                    logger.warning(
                                        f"⚠️ Valor de imposto inválido para '{tipo_imposto}': {valor_brl!r}. Ignorando."
                                    )
                                    continue

                                if valor_float > 0:
                                    # ✅ CORREÇÃO: Usar processo_referencia normalizado ao gravar
                                    proc_ref_escaped = proc_ref_normalizado.replace("'", "''")
                                    # Montar literais SQL sem f-string aninhada (evita SyntaxError)
                                    numero_documento_sql = "'" + ((numero_documento or "N/A").replace("'", "''")) + "'"
                                    tipo_documento_sql = "'" + ((tipo_documento or "DI").replace("'", "''")) + "'"
                                    query = f"""
                                        INSERT INTO dbo.IMPOSTO_IMPORTACAO (
                                            processo_referencia,
                                            numero_documento,
                                            tipo_documento,
                                            tipo_imposto,
                                            valor_brl,
                                            data_pagamento,
                                            pago,
                                            fonte_dados
                                        ) VALUES (
                                            '{proc_ref_escaped}',
                                            {numero_documento_sql},
                                            {tipo_documento_sql},
                                            '{tipo_imposto}',
                                            {valor_float},
                                            GETDATE(),
                                            1,
                                            'CONCILIACAO_BANCARIA'
                                        )
                                    """
                                    logger.info(
                                        f"📝 Executando INSERT para imposto {tipo_imposto} (processo: '{proc_ref_normalizado}', valor: R$ {valor_float:,.2f})"
                                    )
                                    resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
                                    if resultado.get('success'):
                                        total_gravados += 1
                                        logger.info(
                                            f"✅ Imposto {tipo_imposto} (R$ {valor_float:,.2f}) gravado para processo '{proc_ref_normalizado}' (numero_documento: {numero_documento or 'N/A'})"
                                        )
                                    else:
                                        # ✅ CORREÇÃO: Tratar chave duplicada em IMPOSTO_IMPORTACAO como sucesso lógico
                                        # (mesma ideia do serviço V2) para não travar a classificação quando os
                                        # impostos já existem na tabela.
                                        error_msg = str(resultado.get('error', 'Erro desconhecido'))
                                        error_upper = error_msg.upper()
                                        if (
                                            "UX_IMPOSTO_IMPORTACAO_KEY" in error_upper
                                            or "CANNOT INSERT DUPLICATE KEY ROW IN OBJECT 'DBO.IMPOSTO_IMPORTACAO'" in error_upper
                                        ):
                                            logger.warning(
                                                f"⚠️ Imposto {tipo_imposto} para processo '{proc_ref_normalizado}' e documento "
                                                f"{numero_documento or 'N/A'} já existe em IMPOSTO_IMPORTACAO (chave única). "
                                                f"Tratando como já gravado."
                                            )
                                            # Considerar como gravado para fins de marcar o lançamento como classificado
                                            total_gravados += 1
                                        else:
                                            logger.error(
                                                f"❌ Erro ao gravar imposto {tipo_imposto} para processo '{proc_ref_normalizado}': {error_msg}"
                                            )
                                            logger.debug(f"📝 Query que falhou: {query[:200]}...")
                            
                            # ✅ NOVO: Marcar lançamento como classificado criando registro em LANCAMENTO_TIPO_DESPESA
                            # Isso evita que o lançamento continue aparecendo na lista de não classificados
                            # Fazer isso apenas uma vez por processo, após gravar todos os impostos
                            if total_gravados > 0:
                                logger.info(f"✅ {total_gravados} imposto(s) gravado(s) via conciliação para {proc_ref}")
                                
                                # Marcar como classificado apenas se não houver classificações normais
                                if not classificacoes or len(classificacoes) == 0:
                                    # ✅ CORREÇÃO: Buscar ID do tipo de despesa "IMPOSTOS_IMPORTACAO" criado especificamente para isso
                                    query_tipo = """
                                        SELECT TOP 1 id_tipo_despesa
                                        FROM dbo.TIPO_DESPESA
                                        WHERE codigo_tipo_despesa = 'IMPOSTOS_IMPORTACAO' OR nome_despesa = 'Impostos de Importação'
                                        ORDER BY id_tipo_despesa
                                    """
                                    resultado_tipo = self.sql_adapter.execute_query(query_tipo, database=self.sql_adapter.database)
                                    id_tipo_despesa = None
                                    
                                    if resultado_tipo.get('success') and resultado_tipo.get('data'):
                                        row = resultado_tipo['data'][0]
                                        if isinstance(row, dict):
                                            id_tipo_despesa = row.get('id_tipo_despesa')
                                        else:
                                            id_tipo_despesa = row[0] if len(row) > 0 else None
                                    
                                    if not id_tipo_despesa:
                                        logger.warning("⚠️ Tipo de despesa 'IMPOSTOS_IMPORTACAO' não encontrado. Criando automaticamente...")
                                        # Criar o tipo de despesa se não existir
                                        query_criar = """
                                            INSERT INTO dbo.TIPO_DESPESA (
                                                codigo_tipo_despesa,
                                                nome_despesa,
                                                descricao_despesa,
                                                categoria_despesa,
                                                tipo_custo,
                                                ativo,
                                                ordem_exibicao
                                            ) VALUES (
                                                'IMPOSTOS_IMPORTACAO',
                                                'Impostos de Importação',
                                                'Impostos de importação (II, IPI, PIS, COFINS, Taxa SISCOMEX, etc.) pagos via conciliação bancária',
                                                'IMPOSTO',
                                                'NACIONAL',
                                                1,
                                                24
                                            );
                                            SELECT SCOPE_IDENTITY() as id_tipo_despesa;
                                        """
                                        resultado_criar = self.sql_adapter.execute_query(query_criar, database=self.sql_adapter.database)
                                        if resultado_criar.get('success') and resultado_criar.get('data'):
                                            row = resultado_criar['data'][0]
                                            if isinstance(row, dict):
                                                id_tipo_despesa = row.get('id_tipo_despesa')
                                            else:
                                                id_tipo_despesa = row[0] if len(row) > 0 else None
                                            logger.info(f"✅ Tipo de despesa 'IMPOSTOS_IMPORTACAO' criado com ID: {id_tipo_despesa}")
                                        else:
                                            error_msg = resultado_criar.get('error', 'Erro desconhecido')
                                            logger.error(f"❌ Erro ao criar tipo de despesa 'IMPOSTOS_IMPORTACAO': {error_msg}")
                                    
                                    if id_tipo_despesa:
                                        proc_ref_escaped = proc_ref_normalizado.replace("'", "''")
                                        categoria_proc = proc_ref_normalizado.split(".")[0] if "." in proc_ref_normalizado else "OUTROS"
                                        query_marcar = f"""
                                            INSERT INTO dbo.LANCAMENTO_TIPO_DESPESA (
                                                id_movimentacao_bancaria,
                                                id_tipo_despesa,
                                                processo_referencia,
                                                categoria_processo,
                                                valor_despesa,
                                                origem_classificacao
                                            ) VALUES (
                                                {id_movimentacao},
                                                {id_tipo_despesa},  -- ✅ Usar tipo de despesa "OUTROS" ou primeiro disponível
                                                '{proc_ref_escaped}',
                                                '{categoria_proc}',
                                                {abs(valor_total)},  -- Valor total do lançamento
                                                'IMPOSTOS_IMPORTACAO'
                                            )
                                        """
                                        resultado_marcar = self.sql_adapter.execute_query(query_marcar, database=self.sql_adapter.database)
                                        if resultado_marcar.get('success'):
                                            logger.info(f"✅ Lançamento {id_movimentacao} marcado como classificado (impostos de importação para {proc_ref})")
                                        else:
                                            error_msg = resultado_marcar.get('error', 'Erro desconhecido')
                                            logger.warning(f"⚠️ Erro ao marcar lançamento como classificado: {error_msg}")
                                    else:
                                        logger.error("❌ Não foi possível encontrar nenhum tipo de despesa para marcar o lançamento como classificado")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao gravar impostos do lançamento: {e}", exc_info=True)
                        # Não falhar a classificação por causa disso
            else:
                logger.warning(f"⚠️ Condições NÃO atendidas para gravar impostos:")
                logger.warning(f"   - sucesso_total={sucesso_total} (deve ser True)")
                logger.warning(f"   - tem_confirmacao_impostos={tem_confirmacao_impostos} (deve ser True)")
                logger.warning(f"   - distribuicao_impostos existe={bool(distribuicao_impostos)} (deve ser True)")
                logger.warning(
                    f"   - distribuicao_impostos len={len(distribuicao_impostos) if isinstance(distribuicao_impostos, dict) else 0} (deve ser > 0)"
                )
            
            if sucesso_total:
                logger.info(f"✅ Lançamento {id_movimentacao} classificado com {len(classificacoes)} classificação(ões)")
                return {
                    'sucesso': True,
                    'mensagem': f'Lançamento classificado com sucesso ({len(classificacoes)} classificação(ões))'
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_PARCIAL',
                    'mensagem': f'Erro ao classificar: {"; ".join(erros)}'
                }
            
        except Exception as e:
            logger.error(f"❌ Erro ao classificar lançamento: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e)
            }
    
    def obter_lancamento_com_classificacoes(self, id_movimentacao: int) -> Dict[str, Any]:
        """
        Obtém um lançamento bancário com suas classificações (tipos de despesa e processos).
        
        Args:
            id_movimentacao: ID do lançamento bancário
        
        Returns:
            Dict com dados do lançamento e suas classificações
        """
        try:
            # 1. Buscar lançamento
            query_lancamento = f"""
                SELECT 
                    mb.id_movimentacao,
                    mb.banco_origem,
                    mb.agencia_origem,
                    mb.conta_origem,
                    mb.data_movimentacao,
                    mb.valor_movimentacao,
                    mb.sinal_movimentacao,
                    mb.tipo_movimentacao,
                    mb.descricao_movimentacao,
                    mb.processo_referencia,
                    mb.criado_em
                FROM dbo.MOVIMENTACAO_BANCARIA mb
                WHERE mb.id_movimentacao = {id_movimentacao}
            """
            
            resultado_lancamento = self.sql_adapter.execute_query(query_lancamento, database=self.sql_adapter.database)
            
            if not resultado_lancamento.get('success') or not resultado_lancamento.get('data'):
                return {
                    'sucesso': False,
                    'erro': 'LANCAMENTO_NAO_ENCONTRADO',
                    'mensagem': f'Lançamento {id_movimentacao} não encontrado'
                }
            
            lancamento_row = resultado_lancamento['data'][0]
            
            sinal = lancamento_row.get('sinal_movimentacao', 'C')
            sinal_exibicao = '+' if sinal == 'C' else '-'
            
            lancamento = {
                'id_movimentacao': lancamento_row.get('id_movimentacao'),
                'banco': lancamento_row.get('banco_origem', ''),
                'agencia': lancamento_row.get('agencia_origem', ''),
                'conta': lancamento_row.get('conta_origem', ''),
                'data_movimentacao': str(lancamento_row.get('data_movimentacao', ''))[:10],
                'valor': float(lancamento_row.get('valor_movimentacao', 0)),
                'sinal': sinal_exibicao,
                'tipo': lancamento_row.get('tipo_movimentacao', ''),
                'descricao': lancamento_row.get('descricao_movimentacao', ''),
                'processo_vinculado': lancamento_row.get('processo_referencia'),
                'criado_em': str(lancamento_row.get('criado_em', ''))[:19]
            }
            
            # 2. Buscar classificações
            query_classificacoes = f"""
                SELECT 
                    ltd.id_lancamento_tipo_despesa,
                    ltd.id_tipo_despesa,
                    ltd.processo_referencia,
                    ltd.categoria_processo,
                    ltd.valor_despesa,
                    ltd.percentual_valor,
                    ltd.origem_classificacao,
                    ltd.classificacao_validada,
                    td.nome_despesa,
                    td.categoria_despesa
                FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
                JOIN dbo.TIPO_DESPESA td ON ltd.id_tipo_despesa = td.id_tipo_despesa
                WHERE ltd.id_movimentacao_bancaria = {id_movimentacao}
                ORDER BY ltd.criado_em
            """
            
            resultado_classificacoes = self.sql_adapter.execute_query(query_classificacoes, database=self.sql_adapter.database)
            
            classificacoes = []
            if resultado_classificacoes.get('success') and resultado_classificacoes.get('data'):
                for row in resultado_classificacoes['data']:
                    classificacao = {
                        'id_lancamento_tipo_despesa': row.get('id_lancamento_tipo_despesa'),
                        'id_tipo_despesa': row.get('id_tipo_despesa'),
                        'tipo_despesa': row.get('nome_despesa', ''),
                        'categoria_despesa': row.get('categoria_despesa', ''),
                        'processo_referencia': row.get('processo_referencia'),
                        'categoria_processo': row.get('categoria_processo'),
                        'valor_despesa': float(row.get('valor_despesa', 0)) if row.get('valor_despesa') else None,
                        'percentual_valor': float(row.get('percentual_valor', 0)) if row.get('percentual_valor') else None,
                        'origem': row.get('origem_classificacao', 'MANUAL'),
                        'validada': bool(row.get('classificacao_validada', False))
                    }
                    classificacoes.append(classificacao)
            
            lancamento['classificacoes'] = classificacoes
            
            return {
                'sucesso': True,
                'lancamento': lancamento
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter lançamento com classificações: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e)
            }
    
    def remover_classificacao(self, id_lancamento_tipo_despesa: int) -> Dict[str, Any]:
        """
        Remove uma classificação de lançamento (desvincula tipo de despesa e processo).
        
        Args:
            id_lancamento_tipo_despesa: ID da classificação a remover
        
        Returns:
            Dict com sucesso e mensagem
        """
        if not self.sql_adapter:
            return {
                'sucesso': False,
                'erro': 'SQL Server não disponível',
                'mensagem': '❌ SQL Server não está disponível.'
            }
        
        try:
            # 1. Verificar se a classificação existe
            query_check = f"""
                SELECT 
                    ltd.id_lancamento_tipo_despesa,
                    ltd.id_movimentacao_bancaria,
                    ltd.processo_referencia
                FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
                WHERE ltd.id_lancamento_tipo_despesa = {id_lancamento_tipo_despesa}
            """
            
            resultado_check = self.sql_adapter.execute_query(query_check, database=self.sql_adapter.database)
            
            if not resultado_check.get('success') or not resultado_check.get('data'):
                return {
                    'sucesso': False,
                    'erro': 'CLASSIFICACAO_NAO_ENCONTRADA',
                    'mensagem': f'❌ Classificação {id_lancamento_tipo_despesa} não encontrada'
                }
            
            rows = resultado_check.get('data', [])
            if not rows:
                return {
                    'sucesso': False,
                    'erro': 'CLASSIFICACAO_NAO_ENCONTRADA',
                    'mensagem': f'❌ Classificação {id_lancamento_tipo_despesa} não encontrada'
                }
            
            row = rows[0]
            id_movimentacao = row.get('id_movimentacao_bancaria') if isinstance(row, dict) else (row[1] if len(row) > 1 else None)
            processo_ref = row.get('processo_referencia') if isinstance(row, dict) else (row[2] if len(row) > 2 else None)
            
            # 2. Remover impostos vinculados (se houver)
            query_delete_impostos = f"""
                DELETE FROM dbo.IMPOSTO_IMPORTACAO
                WHERE id_movimentacao_bancaria = {id_movimentacao}
                  AND processo_referencia = '{processo_ref.replace("'", "''") if processo_ref else ""}'
            """
            self.sql_adapter.execute_query(query_delete_impostos, database=self.sql_adapter.database)
            
            # 3. Remover classificação
            query_delete = f"""
                DELETE FROM dbo.LANCAMENTO_TIPO_DESPESA
                WHERE id_lancamento_tipo_despesa = {id_lancamento_tipo_despesa}
            """
            
            resultado = self.sql_adapter.execute_query(query_delete, database=self.sql_adapter.database)
            
            if resultado.get('success'):
                logger.info(f"✅ Classificação {id_lancamento_tipo_despesa} removida (lançamento {id_movimentacao}, processo {processo_ref})")
                return {
                    'sucesso': True,
                    'mensagem': f'✅ Classificação removida. Lançamento {id_movimentacao} desvinculado do processo {processo_ref or "N/A"}.',
                    'id_movimentacao': id_movimentacao,
                    'processo_referencia': processo_ref
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_REMOCAO',
                    'mensagem': f'❌ Erro ao remover classificação: {resultado.get("error", "Erro desconhecido")}'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro ao remover classificação: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'❌ Erro interno: {str(e)}'
            }
    
    def consultar_despesas_processo(
        self,
        processo_referencia: str,
        incluir_pendentes: bool = True,
        incluir_rastreamento: bool = False
    ) -> Dict[str, Any]:
        """
        Consulta despesas vinculadas a um processo.
        
        Args:
            processo_referencia: Referência do processo (ex: BGR.0070/25)
            incluir_pendentes: Se True, inclui despesas pendentes de conciliação (default: True)
            incluir_rastreamento: Se True, inclui rastreamento completo de origem dos recursos (default: False)
        
        Returns:
            Dict com despesas conciliadas, pendentes, totais e percentuais
        """
        try:
            # ✅ CORREÇÃO: Normalizar processo_referencia recebido
            processo_referencia = processo_referencia.strip() if processo_referencia else ''
            logger.info(f"🔍 Consultando despesas do processo '{processo_referencia}' (tipo: {type(processo_referencia).__name__}, len: {len(processo_referencia)})")
            
            # ✅ PASSO 1: Buscar despesas conciliadas (já vinculadas)
            # ✅ CORREÇÃO: Usar normalização para garantir match mesmo com diferenças de formato
            processo_ref_escaped = processo_referencia.replace("'", "''")
            processo_ref_upper = processo_referencia.upper()
            processo_ref_original = processo_referencia
            
            query_conciliadas = f"""
                SELECT 
                    ltd.id_lancamento_tipo_despesa,
                    ltd.id_movimentacao_bancaria,
                    ltd.id_tipo_despesa,
                    ltd.processo_referencia,
                    ltd.categoria_processo,
                    ltd.valor_despesa,
                    ltd.percentual_valor,
                    ltd.origem_classificacao,
                    ltd.criado_em as data_classificacao,
                    td.nome_despesa,
                    td.categoria_despesa,
                    mb.data_movimentacao,
                    mb.data_lancamento,
                    mb.valor_movimentacao,
                    mb.sinal_movimentacao,
                    mb.descricao_movimentacao,
                    mb.banco_origem,
                    mb.agencia_origem,
                    mb.conta_origem,
                    mb.cpf_cnpj_contrapartida,
                    mb.nome_contrapartida
                FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
                INNER JOIN dbo.TIPO_DESPESA td ON ltd.id_tipo_despesa = td.id_tipo_despesa
                INNER JOIN dbo.MOVIMENTACAO_BANCARIA mb ON ltd.id_movimentacao_bancaria = mb.id_movimentacao
                WHERE UPPER(LTRIM(RTRIM(ltd.processo_referencia))) = '{processo_ref_upper}'
                   OR LTRIM(RTRIM(ltd.processo_referencia)) = '{processo_ref_original.replace("'", "''")}'
                   OR ltd.processo_referencia = '{processo_ref_escaped}'
                ORDER BY mb.data_movimentacao DESC, ltd.criado_em DESC
            """
            
            resultado_conciliadas = self.sql_adapter.execute_query(query_conciliadas, database=self.sql_adapter.database)
            
            despesas_conciliadas = []
            total_conciliado = 0.0
            
            if resultado_conciliadas.get('success') and resultado_conciliadas.get('data'):
                for row in resultado_conciliadas.get('data', []):
                    origem_classificacao = row.get('origem_classificacao', 'MANUAL') if isinstance(row, dict) else (row[7] if len(row) > 7 else 'MANUAL')
                    nome_despesa = row.get('nome_despesa', '') if isinstance(row, dict) else (row[9] if len(row) > 9 else '')
                    
                    # ✅ CORREÇÃO: Não incluir despesa genérica "Impostos de Importação" se vamos mostrar os impostos individuais
                    # Isso evita duplicação: a despesa genérica é apenas um marcador para indicar que o lançamento foi classificado
                    if origem_classificacao == 'IMPOSTOS_IMPORTACAO' or nome_despesa == 'Impostos de Importação':
                        logger.debug(f"⏭️ Pulando despesa genérica 'Impostos de Importação' (será substituída pelos impostos individuais)")
                        continue
                    
                    if isinstance(row, dict):
                        valor = float(row.get('valor_despesa', 0))
                        total_conciliado += valor
                        
                        despesa = {
                            'id_lancamento_tipo_despesa': row.get('id_lancamento_tipo_despesa'),
                            'id_movimentacao_bancaria': row.get('id_movimentacao_bancaria'),
                            'tipo_despesa': row.get('nome_despesa', ''),
                            'categoria_despesa': row.get('categoria_despesa', ''),
                            'valor': valor,
                            'data_pagamento': str(row.get('data_movimentacao', ''))[:10] if row.get('data_movimentacao') else '',
                            'data_classificacao': str(row.get('data_classificacao', ''))[:19] if row.get('data_classificacao') else '',
                            'banco': row.get('banco_origem', ''),
                            'agencia': row.get('agencia_origem', ''),
                            'conta': row.get('conta_origem', ''),
                            'descricao_lancamento': row.get('descricao_movimentacao', ''),
                            'contrapartida': {
                                'cpf_cnpj': row.get('cpf_cnpj_contrapartida'),
                                'nome': row.get('nome_contrapartida')
                            },
                            'origem_classificacao': origem_classificacao
                        }
                    else:
                        # É uma tupla - mapear índices
                        valor = float(row[5] if len(row) > 5 else 0)
                        total_conciliado += valor
                        
                        despesa = {
                            'id_lancamento_tipo_despesa': row[0] if len(row) > 0 else None,
                            'id_movimentacao_bancaria': row[1] if len(row) > 1 else None,
                            'tipo_despesa': nome_despesa,
                            'categoria_despesa': row[10] if len(row) > 10 else '',
                            'valor': valor,
                            'data_pagamento': str(row[11])[:10] if len(row) > 11 and row[11] else '',
                            'data_classificacao': str(row[8])[:19] if len(row) > 8 and row[8] else '',
                            'banco': row[17] if len(row) > 17 else '',
                            'agencia': row[18] if len(row) > 18 else '',
                            'conta': row[19] if len(row) > 19 else '',
                            'descricao_lancamento': row[16] if len(row) > 16 else '',
                            'contrapartida': {
                                'cpf_cnpj': row[20] if len(row) > 20 else None,
                                'nome': row[21] if len(row) > 21 else None
                            },
                            'origem_classificacao': origem_classificacao
                        }
                    
                    despesas_conciliadas.append(despesa)
            
            # ✅ NOVO: Buscar impostos de importação gravados na tabela IMPOSTO_IMPORTACAO
            # ✅ CORREÇÃO: Buscar tanto com formato normalizado quanto formato original (para pegar registros antigos)
            processo_ref_escaped = processo_referencia.replace("'", "''")
            processo_ref_upper = processo_referencia.strip().upper()
            processo_ref_original = processo_referencia.strip()
            
            # ✅ CORREÇÃO: Buscar também sem normalização (caso tenha sido gravado exatamente como veio)
            # ✅ CORREÇÃO: Usar ROW_NUMBER() para pegar apenas o registro mais recente de cada tipo de imposto
            # ✅ NOVO: JOIN com LANCAMENTO_TIPO_DESPESA e MOVIMENTACAO_BANCARIA para pegar informações do banco
            # ✅ NOVO: Ordenar na ordem específica: II, IPI, PIS, COFINS, ANTIDUMPING, MULTA, TAXA_UTILIZACAO
            query_impostos = f"""
                WITH ImpostosRanked AS (
                    SELECT 
                        imp.id_imposto,
                        imp.processo_referencia as imp_processo_ref,
                        imp.numero_documento,
                        imp.tipo_documento,
                        imp.tipo_imposto,
                        imp.valor_brl,
                        imp.data_pagamento,
                        imp.pago,
                        imp.fonte_dados,
                        imp.criado_em,
                        mb.banco_origem,
                        mb.agencia_origem,
                        mb.conta_origem,
                        mb.data_movimentacao,
                        mb.descricao_movimentacao,
                        ROW_NUMBER() OVER (
                            PARTITION BY imp.tipo_imposto, imp.numero_documento 
                            ORDER BY imp.criado_em DESC, imp.id_imposto DESC
                        ) as rn
                    FROM dbo.IMPOSTO_IMPORTACAO imp
                    LEFT JOIN dbo.LANCAMENTO_TIPO_DESPESA ltd ON 
                        (UPPER(LTRIM(RTRIM(ltd.processo_referencia))) = UPPER(LTRIM(RTRIM(imp.processo_referencia)))
                         OR LTRIM(RTRIM(ltd.processo_referencia)) = LTRIM(RTRIM(imp.processo_referencia)))
                        AND ltd.origem_classificacao = 'IMPOSTOS_IMPORTACAO'
                    LEFT JOIN dbo.MOVIMENTACAO_BANCARIA mb ON ltd.id_movimentacao_bancaria = mb.id_movimentacao
                    WHERE UPPER(LTRIM(RTRIM(imp.processo_referencia))) = '{processo_ref_upper}'
                       OR LTRIM(RTRIM(imp.processo_referencia)) = '{processo_ref_original.replace("'", "''")}'
                       OR imp.processo_referencia = '{processo_ref_escaped}'
                )
                SELECT 
                    id_imposto,
                    imp_processo_ref as processo_referencia,
                    numero_documento,
                    tipo_documento,
                    tipo_imposto,
                    valor_brl,
                    data_pagamento,
                    pago,
                    fonte_dados,
                    criado_em,
                    banco_origem,
                    agencia_origem,
                    conta_origem,
                    data_movimentacao,
                    descricao_movimentacao,
                    CASE tipo_imposto
                        WHEN 'II' THEN 1
                        WHEN 'IPI' THEN 2
                        WHEN 'PIS' THEN 3
                        WHEN 'COFINS' THEN 4
                        WHEN 'ANTIDUMPING' THEN 5
                        WHEN 'MULTA' THEN 6
                        WHEN 'TAXA_UTILIZACAO' THEN 7
                        ELSE 99
                    END as ordem_imposto
                FROM ImpostosRanked
                WHERE rn = 1
                ORDER BY ordem_imposto, data_pagamento DESC, criado_em DESC
            """
            
            logger.info(f"🔍 Buscando impostos para processo '{processo_referencia}' (normalizado: '{processo_ref_upper}', original: '{processo_ref_original}') na tabela IMPOSTO_IMPORTACAO")
            logger.debug(f"📝 Query SQL: {query_impostos[:200]}...")
            resultado_impostos = self.sql_adapter.execute_query(query_impostos, database=self.sql_adapter.database)
            
            if not resultado_impostos.get('success'):
                error_msg = resultado_impostos.get('error', 'Erro desconhecido')
                logger.warning(f"⚠️ Erro ao buscar impostos: {error_msg}")
            else:
                data_count = len(resultado_impostos.get('data', []))
                logger.info(f"✅ Query de impostos executada. Encontrados {data_count} registro(s) para '{processo_referencia}'")
                if data_count > 0:
                    logger.info(f"📋 Primeiros impostos encontrados: {[r.get('tipo_imposto', 'N/A') if isinstance(r, dict) else 'N/A' for r in resultado_impostos.get('data', [])[:3]]}")
                else:
                    # ✅ DEBUG: Verificar se há impostos para outros processos
                    logger.debug(f"🔍 Nenhum imposto encontrado. Verificando se há impostos na tabela...")
                    query_debug = "SELECT TOP 5 processo_referencia, tipo_imposto, valor_brl FROM dbo.IMPOSTO_IMPORTACAO ORDER BY criado_em DESC"
                    result_debug = self.sql_adapter.execute_query(query_debug, database=self.sql_adapter.database)
                    if result_debug.get('success') and result_debug.get('data'):
                        logger.info(f"📊 Total de impostos na tabela: {len(result_debug.get('data', []))}")
                        for imp in result_debug.get('data', [])[:3]:
                            if isinstance(imp, dict):
                                logger.info(f"  - Exemplo: processo='{imp.get('processo_referencia', 'N/A')}', tipo={imp.get('tipo_imposto', 'N/A')}, valor=R$ {imp.get('valor_brl', 0):,.2f}")
            
            if resultado_impostos.get('success') and resultado_impostos.get('data'):
                logger.info(f"💰 Processando {len(resultado_impostos.get('data', []))} imposto(s) encontrado(s)")
                for row in resultado_impostos.get('data', []):
                    if isinstance(row, dict):
                        valor = float(row.get('valor_brl', 0))
                        total_conciliado += valor
                        
                        # Mapear tipo de imposto para nome legível
                        tipo_imposto = row.get('tipo_imposto', '')
                        nome_imposto = {
                            'II': 'Imposto de Importação',
                            'IPI': 'Imposto sobre Produtos Industrializados',
                            'PIS': 'Programa de Integração Social',
                            'COFINS': 'Contribuição para o Financiamento da Seguridade Social',
                            'ANTIDUMPING': 'Antidumping',
                            'TAXA_UTILIZACAO': 'Taxa SISCOMEX',  # ✅ CORREÇÃO: Nome conforme solicitado
                            'ICMS': 'Imposto sobre Circulação de Mercadorias e Serviços',
                            'MULTA': 'Multa'  # ✅ NOVO: Para multas quando houver
                        }.get(tipo_imposto, tipo_imposto)
                        
                        # ✅ NOVO: Pegar informações do banco do lançamento
                        banco_origem = row.get('banco_origem', '')
                        agencia_origem = row.get('agencia_origem', '')
                        conta_origem = row.get('conta_origem', '')
                        descricao_movimentacao = row.get('descricao_movimentacao', '')
                        data_movimentacao = row.get('data_movimentacao')
                        
                        despesa_imposto = {
                            'id_imposto': row.get('id_imposto'),
                            'tipo_despesa': nome_imposto,
                            'categoria_despesa': 'IMPOSTOS',
                            'valor': valor,
                            'data_pagamento': str(data_movimentacao)[:10] if data_movimentacao else (str(row.get('data_pagamento', ''))[:10] if row.get('data_pagamento') else ''),
                            'data_classificacao': str(row.get('criado_em', ''))[:19] if row.get('criado_em') else '',
                            'banco': banco_origem,  # ✅ NOVO: Informação do banco
                            'agencia': agencia_origem,  # ✅ NOVO: Informação da agência
                            'conta': conta_origem,  # ✅ NOVO: Informação da conta
                            'descricao_lancamento': descricao_movimentacao or f'Imposto {tipo_imposto} - {row.get("numero_documento", "N/A")}',
                            'contrapartida': {
                                'cpf_cnpj': None,
                                'nome': None
                            },
                            'origem_classificacao': row.get('fonte_dados', 'CONCILIACAO_BANCARIA'),
                            'numero_documento': row.get('numero_documento'),
                            'tipo_documento': row.get('tipo_documento'),
                            'tipo_imposto': tipo_imposto,
                            'ordem_imposto': row.get('ordem_imposto', 99)  # ✅ NOVO: Para manter ordem
                        }
                    else:
                        # É uma tupla - mapear índices
                        valor = float(row[5] if len(row) > 5 else 0)
                        total_conciliado += valor
                        
                        tipo_imposto = row[4] if len(row) > 4 else ''
                        nome_imposto = {
                            'II': 'Imposto de Importação',
                            'IPI': 'Imposto sobre Produtos Industrializados',
                            'PIS': 'Programa de Integração Social',
                            'COFINS': 'Contribuição para o Financiamento da Seguridade Social',
                            'ANTIDUMPING': 'Antidumping',
                            'TAXA_UTILIZACAO': 'Taxa SISCOMEX',  # ✅ CORREÇÃO: Nome conforme solicitado
                            'ICMS': 'Imposto sobre Circulação de Mercadorias e Serviços',
                            'MULTA': 'Multa'  # ✅ NOVO: Para multas quando houver
                        }.get(tipo_imposto, tipo_imposto)
                        
                        # ✅ NOVO: Pegar informações do banco do lançamento (índices ajustados)
                        banco_origem = row[10] if len(row) > 10 else ''
                        agencia_origem = row[11] if len(row) > 11 else ''
                        conta_origem = row[12] if len(row) > 12 else ''
                        descricao_movimentacao = row[15] if len(row) > 15 else ''
                        data_movimentacao = row[13] if len(row) > 13 else None
                        
                        despesa_imposto = {
                            'id_imposto': row[0] if len(row) > 0 else None,
                            'tipo_despesa': nome_imposto,
                            'categoria_despesa': 'IMPOSTOS',
                            'valor': valor,
                            'data_pagamento': str(data_movimentacao)[:10] if data_movimentacao else (str(row[6])[:10] if len(row) > 6 and row[6] else ''),
                            'data_classificacao': str(row[9])[:19] if len(row) > 9 and row[9] else '',
                            'banco': banco_origem,  # ✅ NOVO: Informação do banco
                            'agencia': agencia_origem,  # ✅ NOVO: Informação da agência
                            'conta': conta_origem,  # ✅ NOVO: Informação da conta
                            'descricao_lancamento': descricao_movimentacao or f'Imposto {tipo_imposto} - {row[2] if len(row) > 2 else "N/A"}',
                            'contrapartida': {
                                'cpf_cnpj': None,
                                'nome': None
                            },
                            'origem_classificacao': row[8] if len(row) > 8 else 'CONCILIACAO_BANCARIA',
                            'numero_documento': row[2] if len(row) > 2 else None,
                            'tipo_documento': row[3] if len(row) > 3 else None,
                            'tipo_imposto': tipo_imposto,
                            'ordem_imposto': row[16] if len(row) > 16 else 99  # ✅ NOVO: Para manter ordem
                        }
                    
                    despesas_conciliadas.append(despesa_imposto)
                    logger.debug(f"✅ Imposto {tipo_imposto} (R$ {valor:,.2f}) adicionado às despesas conciliadas")
            else:
                logger.info(f"ℹ️ Nenhum imposto encontrado na tabela IMPOSTO_IMPORTACAO para '{processo_referencia}'")
            
            # ✅ NOVO: Ordenar despesas - impostos primeiro (na ordem específica), depois outras despesas
            def ordenar_despesas(despesa):
                # Se for imposto, usar ordem_imposto (já vem ordenado da query)
                if despesa.get('categoria_despesa') == 'IMPOSTOS':
                    ordem_imposto = despesa.get('ordem_imposto', 99)
                    return (0, ordem_imposto)  # Impostos primeiro (grupo 0)
                else:
                    # Outras despesas depois (grupo 1), ordenadas por data
                    data_pag = despesa.get('data_pagamento', '')
                    return (1, data_pag)
            
            despesas_conciliadas.sort(key=ordenar_despesas)
            
            logger.info(f"✅ {len(despesas_conciliadas)} despesa(s) conciliada(s) encontrada(s) para {processo_referencia} (incluindo {len([d for d in despesas_conciliadas if d.get('categoria_despesa') == 'IMPOSTOS'])} imposto(s))")
            
            # ✅ PASSO 2: Buscar despesas pendentes (se solicitado)
            # Por enquanto, retornamos lista vazia - pode ser expandido no futuro
            # para buscar despesas esperadas mas não conciliadas (ex: baseado em DI/DUIMP)
            despesas_pendentes = []
            
            # ✅ PASSO 3: Calcular totais e percentuais
            total_pendente = 0.0
            for pendente in despesas_pendentes:
                total_pendente += float(pendente.get('valor_estimado', 0))
            
            total_geral = total_conciliado + total_pendente
            percentual_conciliado = (total_conciliado / total_geral * 100) if total_geral > 0 else 100.0
            
            return {
                'sucesso': True,
                'processo_referencia': processo_referencia,
                'despesas_conciliadas': despesas_conciliadas,
                'despesas_pendentes': despesas_pendentes,
                'total_conciliado': total_conciliado,
                'total_pendente': total_pendente,
                'total_geral': total_geral,
                'percentual_conciliado': percentual_conciliado,
                'quantidade_conciliadas': len(despesas_conciliadas),
                'quantidade_pendentes': len(despesas_pendentes)
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao consultar despesas do processo {processo_referencia}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro ao consultar despesas: {str(e)}',
                'processo_referencia': processo_referencia,
                'despesas_conciliadas': [],
                'despesas_pendentes': [],
                'total_conciliado': 0.0,
                'total_pendente': 0.0,
                'total_geral': 0.0,
                'percentual_conciliado': 0.0
            }
