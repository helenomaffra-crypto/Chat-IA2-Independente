#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviço para gravar Impostos de Importação e Valores da Mercadoria.

Grava impostos (II, IPI, PIS, COFINS, etc.) e valores (Descarga, Embarque, FOB, CIF)
na tabela IMPOSTO_IMPORTACAO e VALOR_MERCADORIA do SQL Server.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from utils.sql_server_adapter import get_sql_adapter

logger = logging.getLogger(__name__)

# Singleton instance
_imposto_valor_service_instance = None

def get_imposto_valor_service():
    """Retorna instância singleton do serviço de impostos e valores."""
    global _imposto_valor_service_instance
    if _imposto_valor_service_instance is None:
        _imposto_valor_service_instance = ImpostoValorService()
    return _imposto_valor_service_instance

class ImpostoValorService:
    """Serviço para gravar impostos e valores de importação."""
    
    # Mapeamento de códigos de receita para tipos de imposto
    CODIGOS_RECEITA = {
        '0086': 'II',  # Imposto de Importação
        '86': 'II',
        '1038': 'IPI',  # Imposto sobre Produtos Industrializados
        '38': 'IPI',
        '5602': 'PIS',  # PIS/PASEP Importação
        '602': 'PIS',
        '5629': 'COFINS',  # COFINS Importação
        '629': 'COFINS',
        '5529': 'ANTIDUMPING',  # Antidumping
        '529': 'ANTIDUMPING',
        '7811': 'TAXA_UTILIZACAO',  # Taxa de Utilização SISCOMEX
        '811': 'TAXA_UTILIZACAO',
    }
    
    def __init__(self):
        """Inicializa o serviço de impostos e valores."""
        self.sql_adapter = get_sql_adapter()
        # ✅ Fonte da verdade: SEMPRE operar no banco primário
        try:
            from services.db_policy_service import get_primary_database
            self._database = get_primary_database()
        except Exception:
            self._database = "mAIke_assistente"
        logger.info("✅ ImpostoValorService inicializado")
    
    def gravar_impostos_di(
        self,
        processo_referencia: str,
        numero_di: str,
        pagamentos: List[Dict[str, Any]],
        fonte_dados: str = 'SQL_SERVER',
        data_pagamento: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Grava impostos de uma DI na tabela IMPOSTO_IMPORTACAO.
        
        Args:
            processo_referencia: Referência do processo (ex: BGR.0070/25)
            numero_di: Número da DI
            pagamentos: Lista de pagamentos da DI (de Di_Pagamento ou similar)
            fonte_dados: Fonte dos dados ('SQL_SERVER', 'PORTAL_UNICO', 'INTEGRACOMEX', 'KANBAN_API')
            data_pagamento: Data do pagamento (opcional, será extraída dos pagamentos se não fornecida)
        
        Returns:
            Dict com sucesso, total de impostos gravados e lista de impostos
        """
        try:
            if not self.sql_adapter:
                logger.warning("⚠️ SQL Server adapter não disponível")
                return {
                    'sucesso': False,
                    'erro': 'ADAPTER_NAO_DISPONIVEL',
                    'mensagem': 'SQL Server adapter não disponível'
                }
            
            if not pagamentos or len(pagamentos) == 0:
                logger.debug(f"ℹ️ Nenhum pagamento encontrado para DI {numero_di}")
                return {
                    'sucesso': True,
                    'total': 0,
                    'impostos': [],
                    'mensagem': 'Nenhum imposto encontrado para gravar'
                }
            
            impostos_gravados = []
            erros = []
            
            for pagamento in pagamentos:
                # Extrair dados do pagamento
                codigo_receita = str(pagamento.get('codigoReceita') or pagamento.get('codigo_receita') or '').strip()
                nome_receita = pagamento.get('nomeReceita') or pagamento.get('nome_receita') or ''
                valor_total = float(pagamento.get('valorTotal') or pagamento.get('valor_total') or 0)
                numero_retificacao = pagamento.get('numeroRetificacao') or pagamento.get('numero_retificacao')
                try:
                    numero_retificacao = int(numero_retificacao) if numero_retificacao is not None and str(numero_retificacao).strip() != '' else None
                except Exception:
                    numero_retificacao = None
                
                # Determinar tipo de imposto pelo código
                tipo_imposto = self.CODIGOS_RECEITA.get(codigo_receita, 'OUTROS')
                
                # Se não encontrou pelo código, tentar pelo nome
                if tipo_imposto == 'OUTROS' and nome_receita:
                    nome_upper = nome_receita.upper()
                    if 'IMPOSTO DE IMPORTAÇÃO' in nome_upper or 'II' in nome_upper:
                        tipo_imposto = 'II'
                    elif 'IMPOSTO SOBRE PRODUTOS INDUSTRIALIZADOS' in nome_upper or 'IPI' in nome_upper:
                        tipo_imposto = 'IPI'
                    elif 'PIS' in nome_upper and 'PASEP' in nome_upper:
                        tipo_imposto = 'PIS'
                    elif 'COFINS' in nome_upper:
                        tipo_imposto = 'COFINS'
                    elif 'ANTIDUMPING' in nome_upper:
                        tipo_imposto = 'ANTIDUMPING'
                    elif 'TAXA' in nome_upper and 'SISCOMEX' in nome_upper:
                        tipo_imposto = 'TAXA_UTILIZACAO'
                
                # Extrair data de pagamento
                data_pag = data_pagamento
                if not data_pag:
                    data_pag_str = pagamento.get('dataPagamento') or pagamento.get('data_pagamento')
                    if data_pag_str:
                        try:
                            if isinstance(data_pag_str, str):
                                data_pag = datetime.fromisoformat(data_pag_str.replace('Z', '+00:00'))
                            else:
                                data_pag = data_pag_str
                        except:
                            data_pag = None
                
                # Preparar JSON dos dados originais
                import json
                json_dados = json.dumps(pagamento, ensure_ascii=False, default=str)
                
                # ✅ Idempotente: usar MERGE (evita duplicar e respeita índice único)
                proc_esc = processo_referencia.replace("'", "''")
                di_esc = numero_di.replace("'", "''")
                tipo_imp_esc = tipo_imposto.replace("'", "''")
                if codigo_receita:
                    cod_esc = codigo_receita.replace("'", "''")
                    cod_sql = "'" + cod_esc + "'"
                else:
                    cod_sql = "NULL"
                if nome_receita:
                    desc_esc = str(nome_receita).replace("'", "''")
                    desc_sql = "'" + desc_esc + "'"
                else:
                    desc_sql = "NULL"
                data_sql = "'" + data_pag.isoformat() + "'" if data_pag else "NULL"
                fonte_sql = "'" + str(fonte_dados).replace("'", "''") + "'"
                json_sql = "'" + json_dados.replace("'", "''") + "'"
                ret_sql = str(numero_retificacao) if numero_retificacao is not None else "NULL"

                query = f"""
                    MERGE dbo.IMPOSTO_IMPORTACAO WITH (HOLDLOCK) AS tgt
                    USING (
                        SELECT
                            '{proc_esc}' AS processo_referencia,
                            '{di_esc}' AS numero_documento,
                            'DI' AS tipo_documento,
                            '{tipo_imp_esc}' AS tipo_imposto,
                            {ret_sql} AS numero_retificacao
                    ) AS src
                    ON tgt.processo_referencia = src.processo_referencia
                       AND tgt.numero_documento = src.numero_documento
                       AND tgt.tipo_documento = src.tipo_documento
                       AND tgt.tipo_imposto = src.tipo_imposto
                       AND (
                           (tgt.numero_retificacao IS NULL AND src.numero_retificacao IS NULL)
                           OR (tgt.numero_retificacao = src.numero_retificacao)
                       )
                    WHEN MATCHED THEN
                        UPDATE SET
                            codigo_receita = {cod_sql},
                            descricao_imposto = {desc_sql},
                            valor_brl = {valor_total},
                            data_pagamento = {data_sql},
                            pago = 1,
                            fonte_dados = {fonte_sql},
                            json_dados_originais = {json_sql},
                            atualizado_em = GETDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (
                            processo_referencia,
                            numero_documento,
                            tipo_documento,
                            tipo_imposto,
                            codigo_receita,
                            descricao_imposto,
                            valor_brl,
                            valor_usd,
                            taxa_cambio,
                            data_pagamento,
                            data_vencimento,
                            pago,
                            numero_retificacao,
                            fonte_dados,
                            json_dados_originais,
                            criado_em,
                            atualizado_em
                        )
                        VALUES (
                            src.processo_referencia,
                            src.numero_documento,
                            src.tipo_documento,
                            src.tipo_imposto,
                            {cod_sql},
                            {desc_sql},
                            {valor_total},
                            NULL,
                            NULL,
                            {data_sql},
                            NULL,
                            1,
                            src.numero_retificacao,
                            {fonte_sql},
                            {json_sql},
                            GETDATE(),
                            GETDATE()
                        );
                """
                
                resultado = self.sql_adapter.execute_query(query, database=self._database)
                
                if resultado.get('success'):
                    impostos_gravados.append({
                        'tipo_imposto': tipo_imposto,
                        'codigo_receita': codigo_receita,
                        'valor_brl': valor_total
                    })
                    logger.debug(f"✅ Imposto {tipo_imposto} (R$ {valor_total:,.2f}) gravado para DI {numero_di}")
                else:
                    erro_msg = resultado.get('error', 'Erro desconhecido')
                    erros.append(f"{tipo_imposto} ({codigo_receita}): {erro_msg}")
                    logger.error(f"❌ Erro ao gravar imposto {tipo_imposto}: {erro_msg}")
            
            if len(impostos_gravados) > 0:
                logger.info(f"✅ {len(impostos_gravados)} imposto(s) gravado(s) para DI {numero_di} (processo {processo_referencia})")
                return {
                    'sucesso': True,
                    'total': len(impostos_gravados),
                    'impostos': impostos_gravados,
                    'erros': erros if erros else None
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'NENHUM_IMPOSTO_GRAVADO',
                    'mensagem': f'Nenhum imposto foi gravado. Erros: {"; ".join(erros)}' if erros else 'Nenhum imposto encontrado',
                    'erros': erros
                }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gravar impostos da DI {numero_di}: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e)
            }
    
    def gravar_valores_di(
        self,
        processo_referencia: str,
        numero_di: str,
        valores: Dict[str, Any],
        fonte_dados: str = 'SQL_SERVER'
    ) -> Dict[str, Any]:
        """
        Grava valores da mercadoria de uma DI na tabela VALOR_MERCADORIA.
        
        Args:
            processo_referencia: Referência do processo
            numero_di: Número da DI
            valores: Dict com valores (ex: {'descarga_brl': 1000, 'descarga_usd': 200, 'embarque_brl': 950, ...})
            fonte_dados: Fonte dos dados
        
        Returns:
            Dict com sucesso e total de valores gravados
        """
        try:
            if not self.sql_adapter:
                logger.warning("⚠️ SQL Server adapter não disponível")
                return {
                    'sucesso': False,
                    'erro': 'ADAPTER_NAO_DISPONIVEL',
                    'mensagem': 'SQL Server adapter não disponível'
                }
            
            valores_gravados = []
            
            # Mapear valores
            tipos_valores = [
                ('DESCARGA', 'descarga_brl', 'descarga_usd', 'BRL', 'USD'),
                ('EMBARQUE', 'embarque_brl', 'embarque_usd', 'BRL', 'USD'),
                ('VMLE', 'vmle_brl', 'vmle_usd', 'BRL', 'USD'),
                ('VMLD', 'vmld_brl', 'vmld_usd', 'BRL', 'USD'),
                ('FOB', 'fob_brl', 'fob_usd', 'BRL', 'USD'),
                ('CIF', 'cif_brl', 'cif_usd', 'BRL', 'USD'),
                # ✅ NOVO (19/01/2026): permitir persistir frete/seguro também (constraint já aceita)
                ('FRETE', 'frete_brl', 'frete_usd', 'BRL', 'USD'),
                ('SEGURO', 'seguro_brl', 'seguro_usd', 'BRL', 'USD'),
            ]
            
            for tipo_valor, chave_brl, chave_usd, moeda_brl, moeda_usd in tipos_valores:
                # Valor em BRL
                valor_brl = valores.get(chave_brl) or valores.get(f'{tipo_valor.lower()}_brl')
                if valor_brl and float(valor_brl) > 0:
                    proc_esc = processo_referencia.replace("'", "''")
                    di_esc = numero_di.replace("'", "''")
                    tipo_val_esc = tipo_valor.replace("'", "''")
                    moeda_esc = moeda_brl.replace("'", "''")
                    fonte_esc = str(fonte_dados).replace("'", "''")
                    query = f"""
                        MERGE dbo.VALOR_MERCADORIA WITH (HOLDLOCK) AS tgt
                        USING (
                            SELECT
                                '{proc_esc}' AS processo_referencia,
                                '{di_esc}' AS numero_documento,
                                'DI' AS tipo_documento,
                                '{tipo_val_esc}' AS tipo_valor,
                                '{moeda_esc}' AS moeda
                        ) AS src
                        ON tgt.processo_referencia = src.processo_referencia
                           AND tgt.numero_documento = src.numero_documento
                           AND tgt.tipo_documento = src.tipo_documento
                           AND tgt.tipo_valor = src.tipo_valor
                           AND tgt.moeda = src.moeda
                        WHEN MATCHED THEN
                            UPDATE SET
                                valor = {float(valor_brl)},
                                data_atualizacao = GETDATE(),
                                fonte_dados = '{fonte_esc}',
                                atualizado_em = GETDATE()
                        WHEN NOT MATCHED THEN
                            INSERT (
                                processo_referencia,
                                numero_documento,
                                tipo_documento,
                                tipo_valor,
                                moeda,
                                valor,
                                taxa_cambio,
                                data_valor,
                                data_atualizacao,
                                fonte_dados,
                                json_dados_originais,
                                criado_em,
                                atualizado_em
                            ) VALUES (
                                src.processo_referencia,
                                src.numero_documento,
                                src.tipo_documento,
                                src.tipo_valor,
                                src.moeda,
                                {float(valor_brl)},
                                NULL,
                                NULL,
                                GETDATE(),
                                '{fonte_esc}',
                                NULL,
                                GETDATE(),
                                GETDATE()
                            );
                    """
                    resultado = self.sql_adapter.execute_query(query, database=self._database)
                    if resultado.get('success'):
                        valores_gravados.append(f'{tipo_valor} ({moeda_brl})')
                
                # Valor em USD
                valor_usd = valores.get(chave_usd) or valores.get(f'{tipo_valor.lower()}_usd')
                if valor_usd and float(valor_usd) > 0:
                    proc_esc = processo_referencia.replace("'", "''")
                    di_esc = numero_di.replace("'", "''")
                    tipo_val_esc = tipo_valor.replace("'", "''")
                    moeda_esc = moeda_usd.replace("'", "''")
                    fonte_esc = str(fonte_dados).replace("'", "''")
                    query = f"""
                        MERGE dbo.VALOR_MERCADORIA WITH (HOLDLOCK) AS tgt
                        USING (
                            SELECT
                                '{proc_esc}' AS processo_referencia,
                                '{di_esc}' AS numero_documento,
                                'DI' AS tipo_documento,
                                '{tipo_val_esc}' AS tipo_valor,
                                '{moeda_esc}' AS moeda
                        ) AS src
                        ON tgt.processo_referencia = src.processo_referencia
                           AND tgt.numero_documento = src.numero_documento
                           AND tgt.tipo_documento = src.tipo_documento
                           AND tgt.tipo_valor = src.tipo_valor
                           AND tgt.moeda = src.moeda
                        WHEN MATCHED THEN
                            UPDATE SET
                                valor = {float(valor_usd)},
                                data_atualizacao = GETDATE(),
                                fonte_dados = '{fonte_esc}',
                                atualizado_em = GETDATE()
                        WHEN NOT MATCHED THEN
                            INSERT (
                                processo_referencia,
                                numero_documento,
                                tipo_documento,
                                tipo_valor,
                                moeda,
                                valor,
                                taxa_cambio,
                                data_valor,
                                data_atualizacao,
                                fonte_dados,
                                json_dados_originais,
                                criado_em,
                                atualizado_em
                            ) VALUES (
                                src.processo_referencia,
                                src.numero_documento,
                                src.tipo_documento,
                                src.tipo_valor,
                                src.moeda,
                                {float(valor_usd)},
                                NULL,
                                NULL,
                                GETDATE(),
                                '{fonte_esc}',
                                NULL,
                                GETDATE(),
                                GETDATE()
                            );
                    """
                    resultado = self.sql_adapter.execute_query(query, database=self._database)
                    if resultado.get('success'):
                        valores_gravados.append(f'{tipo_valor} ({moeda_usd})')
            
            if len(valores_gravados) > 0:
                logger.info(f"✅ {len(valores_gravados)} valor(es) gravado(s) para DI {numero_di}")
                return {
                    'sucesso': True,
                    'total': len(valores_gravados),
                    'valores': valores_gravados
                }
            else:
                return {
                    'sucesso': True,
                    'total': 0,
                    'mensagem': 'Nenhum valor encontrado para gravar'
                }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gravar valores da DI {numero_di}: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e)
            }
    
    def buscar_impostos_processo(
        self,
        processo_referencia: str,
        numero_documento: Optional[str] = None,
        tipo_documento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca impostos gravados para um processo.
        
        Args:
            processo_referencia: Referência do processo
            numero_documento: Número do documento (opcional, filtra por documento específico)
            tipo_documento: Tipo do documento ('DI' ou 'DUIMP', opcional)
        
        Returns:
            Dict com lista de impostos
        """
        try:
            if not self.sql_adapter:
                return {
                    'sucesso': False,
                    'erro': 'ADAPTER_NAO_DISPONIVEL',
                    'impostos': []
                }
            
            # Escapar aspas simples para SQL
            processo_ref_sql = (processo_referencia or '').replace("'", "''")
            where_clauses = [f"processo_referencia = '{processo_ref_sql}'"]
            
            if numero_documento:
                numero_documento_sql = (numero_documento or '').replace("'", "''")
                where_clauses.append(f"numero_documento = '{numero_documento_sql}'")
            
            if tipo_documento:
                where_clauses.append(f"tipo_documento = '{tipo_documento}'")
            
            query = f"""
                SELECT 
                    id_imposto,
                    tipo_imposto,
                    codigo_receita,
                    descricao_imposto,
                    valor_brl,
                    valor_usd,
                    data_pagamento,
                    pago
                FROM dbo.IMPOSTO_IMPORTACAO
                WHERE {' AND '.join(where_clauses)}
                ORDER BY tipo_imposto, data_pagamento DESC
            """
            
            resultado = self.sql_adapter.execute_query(query, database=self._database)
            
            if not resultado.get('success'):
                return {
                    'sucesso': False,
                    'erro': resultado.get('error', 'Erro desconhecido'),
                    'impostos': []
                }
            
            impostos = resultado.get('data', [])
            
            return {
                'sucesso': True,
                'total': len(impostos),
                'impostos': impostos
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar impostos do processo {processo_referencia}: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e),
                'impostos': []
            }
    
    def distribuir_impostos_lancamento(
        self,
        processo_referencia: str,
        numero_di: str,
        valor_total_lancamento: float,
        distribuicao: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Distribui um lançamento bancário de impostos entre os tipos de imposto.
        
        Args:
            processo_referencia: Referência do processo
            numero_di: Número da DI
            valor_total_lancamento: Valor total do lançamento bancário
            distribuicao: Dict com distribuição (ex: {'II': 10000, 'IPI': 5000, 'PIS': 2000, 'COFINS': 3000})
        
        Returns:
            Dict com sucesso e impostos gravados
        """
        try:
            # Validar que soma da distribuição não excede o total
            soma_distribuicao = sum(distribuicao.values())
            if soma_distribuicao > valor_total_lancamento * 1.01:  # 1% tolerância
                return {
                    'sucesso': False,
                    'erro': 'DISTRIBUICAO_EXCEDE_TOTAL',
                    'mensagem': f'A soma da distribuição ({soma_distribuicao:,.2f}) excede o valor total ({valor_total_lancamento:,.2f})'
                }
            
            impostos_gravados = []
            
            for tipo_imposto, valor in distribuicao.items():
                if valor <= 0:
                    continue
                
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
                        '{processo_referencia.replace("'", "''")}',
                        '{numero_di.replace("'", "''")}',
                        'DI',
                        '{tipo_imposto}',
                        {valor},
                        GETDATE(),
                        1,
                        'CONCILIACAO_BANCARIA'
                    )
                """
                
                resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
                
                if resultado.get('success'):
                    impostos_gravados.append({
                        'tipo_imposto': tipo_imposto,
                        'valor_brl': valor
                    })
            
            if len(impostos_gravados) > 0:
                logger.info(f"✅ {len(impostos_gravados)} imposto(s) gravado(s) via conciliação para DI {numero_di}")
                return {
                    'sucesso': True,
                    'total': len(impostos_gravados),
                    'impostos': impostos_gravados
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'NENHUM_IMPOSTO_GRAVADO',
                    'mensagem': 'Nenhum imposto foi gravado'
                }
            
        except Exception as e:
            logger.error(f"❌ Erro ao distribuir impostos do lançamento: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': str(e)
            }


