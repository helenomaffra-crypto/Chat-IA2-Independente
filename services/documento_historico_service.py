# -*- coding: utf-8 -*-
"""
Serviço de Histórico de Mudanças em Documentos Aduaneiros
==========================================================
Detecta e grava histórico de mudanças em DI, DUIMP, CE, CCT quando consulta APIs.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
from decimal import Decimal

logger = logging.getLogger(__name__)


class DocumentoHistoricoService:
    """Serviço para gerenciar histórico de mudanças em documentos aduaneiros"""
    
    def __init__(self):
        """Inicializa o serviço"""
        self._schema_checked = False

    def _ensure_schema(self) -> None:
        """
        Ajustes defensivos no schema do banco novo para evitar truncamentos.
        """
        if self._schema_checked:
            return
        self._schema_checked = True
        try:
            from utils.sql_server_adapter import get_sql_adapter

            sql_adapter = get_sql_adapter()
            if not sql_adapter:
                return

            def _ensure_varchar_len(table: str, column: str, target_len: int) -> None:
                q = f"""
                    SELECT CHARACTER_MAXIMUM_LENGTH AS len
                    FROM mAIke_assistente.INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_NAME='{table}'
                      AND COLUMN_NAME='{column}'
                """
                r = sql_adapter.execute_query(q, database="mAIke_assistente", notificar_erro=False)
                if not (r and r.get("success") and r.get("data")):
                    return
                try:
                    cur_len = int((r.get("data") or [{}])[0].get("len") or 0)
                except Exception:
                    cur_len = 0
                if cur_len and cur_len < target_len:
                    sql_adapter.execute_query(
                        f"ALTER TABLE mAIke_assistente.dbo.{table} ALTER COLUMN {column} VARCHAR({int(target_len)}) NULL",
                        database="mAIke_assistente",
                        notificar_erro=False,
                    )

            # status_documento_codigo pode ser longo (ex.: REGISTRADA_AGUARDANDO_CANAL)
            _ensure_varchar_len("DOCUMENTO_ADUANEIRO", "status_documento_codigo", 50)
            _ensure_varchar_len("HISTORICO_DOCUMENTO_ADUANEIRO", "status_documento_codigo", 50)
        except Exception:
            # defensivo: não bloquear o fluxo por schema check
            return
    
    def detectar_e_gravar_mudancas(
        self,
        numero_documento: str,
        tipo_documento: str,
        dados_novos: Dict[str, Any],
        fonte_dados: str,
        api_endpoint: str,
        processo_referencia: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detecta mudanças em um documento e grava histórico.
        
        Args:
            numero_documento: Número do documento (CE, DI, DUIMP, CCT)
            tipo_documento: Tipo do documento ('CE', 'CCT', 'DI', 'DUIMP')
            dados_novos: Dados novos retornados pela API
            fonte_dados: Fonte dos dados ('INTEGRACOMEX', 'DUIMP_API', 'PORTAL_UNICO')
            api_endpoint: Endpoint da API consultada
            processo_referencia: Referência do processo (opcional)
        
        Returns:
            Lista de mudanças detectadas e gravadas
        """
        try:
            # ✅ Garantir schema antes de gravar histórico/documento (evita truncamento)
            self._ensure_schema()

            # 1. Buscar versão anterior do documento
            documento_anterior = self._buscar_documento_anterior(numero_documento, tipo_documento)
            
            # 2. Extrair campos relevantes dos dados novos
            campos_novos = self._extrair_campos_relevantes(dados_novos, tipo_documento)
            
            # 3. Comparar e detectar mudanças
            mudancas = self._detectar_mudancas(documento_anterior, campos_novos, tipo_documento)
            
            # 4. Gravar histórico para cada mudança
            historicos_gravados = []
            for mudanca in mudancas:
                historico = self._gravar_historico(
                    numero_documento=numero_documento,
                    tipo_documento=tipo_documento,
                    processo_referencia=processo_referencia,
                    mudanca=mudanca,
                    fonte_dados=fonte_dados,
                    api_endpoint=api_endpoint,
                    dados_novos=dados_novos
                )
                if historico:
                    historicos_gravados.append(historico)
            
            # 5. Atualizar documento atual
            # ✅ OTIMIZAÇÃO: Só gravar se houver mudanças OU se for a primeira vez (documento não existe)
            # Isso evita gravações desnecessárias em sincronizações subsequentes sem mudanças
            deve_gravar = False
            
            if not documento_anterior:
                # Primeira vez - sempre gravar
                deve_gravar = True
                logger.debug(f"🔍 Primeira gravação do documento {tipo_documento} {numero_documento} no SQL Server...")
            elif mudancas and len(mudancas) > 0:
                # Houve mudanças - gravar
                deve_gravar = True
                logger.debug(f"🔍 Documento {tipo_documento} {numero_documento} teve {len(mudancas)} mudança(ões) - atualizando...")
            elif processo_referencia and not documento_anterior.get('processo_referencia'):
                # Documento existe mas não tem processo_referencia - atualizar para adicionar processo
                deve_gravar = True
                logger.debug(f"🔍 Documento {tipo_documento} {numero_documento} sem processo - adicionando {processo_referencia}...")
            else:
                # Sem mudanças e já tem processo - não precisa gravar
                logger.debug(f"ℹ️ Documento {tipo_documento} {numero_documento} sem mudanças - pulando gravação")
            
            if deve_gravar:
                resultado_gravacao = self._atualizar_documento(
                    numero_documento=numero_documento,
                    tipo_documento=tipo_documento,
                    processo_referencia=processo_referencia,
                    campos_novos=campos_novos,
                    fonte_dados=fonte_dados,
                    dados_novos=dados_novos,
                )
                
                if resultado_gravacao:
                    # ✅ NOVO: Verificar se realmente houve gravação (pode ter sido pulada por não ter mudanças)
                    # O _atualizar_documento retorna True mesmo quando pula UPDATE, então verificamos se houve mudanças
                    if mudancas and len(mudancas) > 0:
                        processo_info = f" (processo: {processo_referencia})" if processo_referencia else " (sem processo)"
                        logger.info(f"✅ Documento {tipo_documento} {numero_documento}{processo_info} gravado/atualizado no SQL Server")
                    elif not documento_anterior:
                        # Primeira gravação - sempre logar
                        processo_info = f" (processo: {processo_referencia})" if processo_referencia else " (sem processo)"
                        logger.info(f"✅ Documento {tipo_documento} {numero_documento}{processo_info} gravado/atualizado no SQL Server")
                    # Se não há mudanças e documento já existe, não logar (já foi logado como debug em _atualizar_documento)
                else:
                    logger.warning(f"⚠️ Falha ao gravar documento {tipo_documento} {numero_documento} no SQL Server")
            
            if historicos_gravados:
                logger.info(f"✅ {len(historicos_gravados)} mudança(ões) detectada(s) e gravada(s) para {tipo_documento} {numero_documento}")
            
            return historicos_gravados
            
        except Exception as e:
            logger.error(f"❌ Erro ao detectar e gravar mudanças para {tipo_documento} {numero_documento}: {e}", exc_info=True)
            return []

    def _sql_literal(self, value: Any) -> str:
        """
        Converte um valor Python em literal SQL seguro (para o adapter Node.js sem parâmetros).
        """
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float, Decimal)):
            return str(value)
        if isinstance(value, datetime):
            # SQL Server aceita ISO 8601
            return f"'{value.isoformat(sep=' ', timespec='seconds')}'"
        # strings e outros tipos
        s = str(value)
        s = s.replace("'", "''")
        return f"'{s}'"

    def _normalizar_versao_documento(self, versao: Optional[str]) -> Optional[str]:
        if versao is None:
            return None
        v = str(versao).strip()
        return v if v else None

    def _extrair_versao_documento(self, dados: Optional[Dict[str, Any]], tipo_documento: str) -> Optional[str]:
        """
        Tenta extrair um identificador de "versão/retificação" para suportar unicidade.
        Hoje é usado principalmente para DI (retificações).
        """
        if not dados:
            return None
        # DI costuma ter número de retificação
        if tipo_documento == "DI":
            v = (
                dados.get("numeroRetificacao")
                or dados.get("numero_retificacao")
                or dados.get("retificacao")
                or dados.get("versaoDocumento")
                or dados.get("versao_documento")
            )
            return self._normalizar_versao_documento(v)
        # Outros: manter extensível (sem forçar)
        v = dados.get("versaoDocumento") or dados.get("versao_documento")
        return self._normalizar_versao_documento(v)
    
    def _buscar_documento_anterior(self, numero_documento: str, tipo_documento: str) -> Optional[Dict[str, Any]]:
        """
        Busca versão anterior do documento no banco.
        
        Tenta buscar de:
        1. SQL Server (DOCUMENTO_ADUANEIRO) - se disponível
        2. SQLite (ces_cache, dis_cache, etc.) - fallback
        """
        try:
            # Tentar SQL Server primeiro
            from utils.sql_server_adapter import get_sql_adapter
            adapter = get_sql_adapter()
            
            if adapter:
                query = """
                    SELECT TOP 1 
                        numero_documento,
                        tipo_documento,
                        versao_documento,
                        status_documento,
                        status_documento_codigo,
                        canal_documento,
                        situacao_documento,
                        data_registro,
                        data_situacao,
                        data_desembaraco,
                        json_dados_originais
                    FROM DOCUMENTO_ADUANEIRO
                    -- ✅ CORREÇÃO (16/01/2026): compatibilidade com colunas antigas tipo TEXT
                    -- SQL Server não permite comparar TEXT = VARCHAR diretamente.
                    WHERE CAST(numero_documento AS VARCHAR(50)) = ? AND CAST(tipo_documento AS VARCHAR(50)) = ?
                    ORDER BY atualizado_em DESC
                """
                query_formatted = query
                query_formatted = query_formatted.replace("?", self._sql_literal(numero_documento), 1)
                query_formatted = query_formatted.replace("?", self._sql_literal(tipo_documento), 1)
                result = adapter.execute_query(query_formatted, database=adapter.database)
                if result and result.get('success') and result.get('data'):
                    data = result.get('data', [])
                    if data and len(data) > 0:
                        return data[0]
        except Exception as e:
            logger.debug(f"⚠️ Não foi possível buscar do SQL Server: {e}")
        
        # Fallback: SQLite
        try:
            from db_manager import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            
            if tipo_documento == 'CE':
                cursor.execute('''
                    SELECT 
                        numero_ce as numero_documento,
                        situacao_carga as status_documento,
                        data_situacao_carga as data_situacao,
                        json_completo as json_dados_originais
                    FROM ces_cache
                    WHERE numero_ce = ?
                    ORDER BY atualizado_em DESC
                    LIMIT 1
                ''', (numero_documento,))
            elif tipo_documento == 'CCT':
                cursor.execute('''
                    SELECT 
                        numero_cct as numero_documento,
                        situacao_atual as status_documento,
                        data_hora_situacao_atual as data_situacao,
                        json_completo as json_dados_originais
                    FROM ccts_cache
                    WHERE numero_cct = ?
                    ORDER BY atualizado_em DESC
                    LIMIT 1
                ''', (numero_documento,))
            elif tipo_documento == 'DI':
                cursor.execute('''
                    SELECT 
                        numero_di as numero_documento,
                        situacao_di as status_documento,
                        data_hora_situacao as data_situacao,
                        canal_di as canal_documento,
                        json_completo as json_dados_originais
                    FROM dis_cache
                    WHERE numero_di = ?
                    ORDER BY atualizado_em DESC
                    LIMIT 1
                ''', (numero_documento,))
            elif tipo_documento == 'DUIMP':
                cursor.execute('''
                    SELECT 
                        numero as numero_documento,
                        situacao as status_documento,
                        json_payload as json_dados_originais
                    FROM duimps
                    WHERE numero = ?
                    ORDER BY atualizado_em DESC
                    LIMIT 1
                ''', (numero_documento,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return row
        except Exception as e:
            logger.debug(f"⚠️ Não foi possível buscar do SQLite: {e}")
        
        return None
    
    def _extrair_campos_relevantes(self, dados: Dict[str, Any], tipo_documento: str) -> Dict[str, Any]:
        """
        Extrai campos relevantes dos dados retornados pela API.
        
        Campos extraídos dependem do tipo de documento.
        """
        campos = {
            'status_documento': None,
            'status_documento_codigo': None,
            'canal_documento': None,
            'situacao_documento': None,
            'data_registro': None,
            'data_situacao': None,
            'data_desembaraco': None,
            # ✅ CORREÇÃO: Removido valor_ii_brl e valor_ipi_brl (não são essenciais para comparação básica)
            # 'valor_ii_brl': None,
            # 'valor_ipi_brl': None,
        }
        
        if tipo_documento == 'CE':
            campos['status_documento'] = dados.get('situacaoCarga') or dados.get('situacao_carga')
            campos['status_documento_codigo'] = (
                dados.get('situacaoCargaCodigo')
                or dados.get('statusDocumentoCodigo')
                or dados.get('codigoSituacao')
            )
            campos['data_situacao'] = dados.get('dataSituacaoCarga') or dados.get('data_situacao_carga')
            campos['data_desembaraco'] = dados.get('dataDesembaraco') or dados.get('data_desembaraco')
            # CE normalmente não possui "dataRegistro" como DI/DUIMP.
            # Usar data de emissão como equivalente de "registro" para relatórios por período.
            campos['data_registro'] = (
                dados.get('dataRegistro')
                or dados.get('data_registro')
                or dados.get('dataEmissao')
                or dados.get('data_emissao')
            )
        
        elif tipo_documento == 'CCT':
            campos['status_documento'] = dados.get('situacaoAtual') or dados.get('situacao_atual')
            campos['status_documento_codigo'] = (
                dados.get('situacaoAtualCodigo')
                or dados.get('statusDocumentoCodigo')
                or dados.get('codigoSituacao')
            )
            campos['data_situacao'] = dados.get('dataHoraSituacaoAtual') or dados.get('data_hora_situacao_atual')
            campos['data_chegada_efetiva'] = dados.get('dataChegadaEfetiva') or dados.get('data_chegada_efetiva')
        
        elif tipo_documento == 'DI':
            campos['status_documento'] = dados.get('situacaoDi') or dados.get('situacao_di')
            campos['status_documento_codigo'] = (
                dados.get('situacaoDiCodigo')
                or dados.get('statusDocumentoCodigo')
                or dados.get('codigoSituacao')
            )
            # ✅ Melhorar compatibilidade de chaves (Kanban/Serpro/normalizações)
            campos['canal_documento'] = (
                dados.get('canal')
                or dados.get('canalDi')
                or dados.get('canal_di')
                or dados.get('canalSelecaoParametrizada')
                or dados.get('canal_selecao_parametrizada')
            )
            campos['data_registro'] = dados.get('dataHoraRegistro') or dados.get('data_hora_registro')
            campos['data_situacao'] = dados.get('dataHoraSituacao') or dados.get('data_hora_situacao')
            campos['data_desembaraco'] = dados.get('dataHoraDesembaraco') or dados.get('data_hora_desembaraco')
            # ✅ CORREÇÃO: Removido valores financeiros (não são essenciais para comparação básica)
            # campos['valor_ii_brl'] = dados.get('valorIiBrl') or dados.get('valor_ii_brl')
            # campos['valor_ipi_brl'] = dados.get('valorIpiBrl') or dados.get('valor_ipi_brl')
        
        elif tipo_documento == 'DUIMP':
            campos['status_documento'] = dados.get('situacao') or dados.get('ultimaSituacao')
            campos['status_documento_codigo'] = (
                dados.get('situacaoCodigo')
                or dados.get('statusDocumentoCodigo')
                or dados.get('codigoSituacao')
            )
            campos['canal_documento'] = (
                dados.get('canal')
                or dados.get('canalDuimp')
                or dados.get('canal_duimp')
                or dados.get('canalConsolidado')
                or dados.get('canal_consolidado')
            )
            campos['data_registro'] = dados.get('dataRegistro') or dados.get('identificacao', {}).get('dataRegistro')
            campos['data_situacao'] = dados.get('dataSituacao') or dados.get('ultimaSituacaoData')
            # ✅ CORREÇÃO: Removido valores financeiros (não são essenciais para comparação básica)
            # campos['valor_ii_brl'] = dados.get('valorIiBrl') or dados.get('valor_ii_brl')
            # campos['valor_ipi_brl'] = dados.get('valorIpiBrl') or dados.get('valor_ipi_brl')
        
        # ✅ Normalizações úteis para evitar campos vazios quando há informação equivalente
        if not campos.get('situacao_documento') and campos.get('status_documento'):
            campos['situacao_documento'] = campos.get('status_documento')
        if not campos.get('status_documento_codigo') and campos.get('status_documento'):
            # Não sabemos sempre um "código" numérico; pelo menos persistir o identificador disponível
            campos['status_documento_codigo'] = campos.get('status_documento')

        return campos
    
    def _detectar_mudancas(
        self,
        documento_anterior: Optional[Dict[str, Any]],
        campos_novos: Dict[str, Any],
        tipo_documento: str
    ) -> List[Dict[str, Any]]:
        """
        Detecta mudanças comparando documento anterior com campos novos.
        
        Returns:
            Lista de mudanças detectadas, cada uma com:
            - tipo_evento: Tipo da mudança
            - campo_alterado: Campo que mudou
            - valor_anterior: Valor anterior
            - valor_novo: Valor novo
        """
        mudancas = []
        
        if not documento_anterior:
            # Documento novo - não há mudanças a detectar
            return mudancas
        
        # Campos a comparar
        # ✅ CORREÇÃO: Removido valor_ii_brl e valor_ipi_brl (colunas podem não existir ou causar erro)
        campos_comparar = [
            ('status_documento', 'MUDANCA_STATUS'),
            ('canal_documento', 'MUDANCA_CANAL'),
            ('data_registro', 'MUDANCA_DATA'),
            ('data_situacao', 'MUDANCA_DATA'),
            ('data_desembaraco', 'MUDANCA_DATA'),
            # ('valor_ii_brl', 'MUDANCA_VALOR'),  # Removido - pode causar erro se coluna não existir
            # ('valor_ipi_brl', 'MUDANCA_VALOR'),  # Removido - pode causar erro se coluna não existir
        ]
        
        for campo, tipo_evento in campos_comparar:
            valor_anterior = documento_anterior.get(campo)
            valor_novo = campos_novos.get(campo)
            
            # Normalizar valores para comparação
            valor_anterior_str = str(valor_anterior) if valor_anterior is not None else None
            valor_novo_str = str(valor_novo) if valor_novo is not None else None
            
            # Detectar mudança
            if valor_anterior_str != valor_novo_str and valor_novo is not None:
                mudancas.append({
                    'tipo_evento': tipo_evento,
                    'campo_alterado': campo,
                    'valor_anterior': valor_anterior_str,
                    'valor_novo': valor_novo_str,
                    'data_evento': datetime.now()  # Usar data atual ou extrair da API se disponível
                })
        
        return mudancas
    
    def _gravar_historico(
        self,
        numero_documento: str,
        tipo_documento: str,
        processo_referencia: Optional[str],
        mudanca: Dict[str, Any],
        fonte_dados: str,
        api_endpoint: str,
        dados_novos: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Grava histórico de mudança no banco SQL Server.
        """
        try:
            from utils.sql_server_adapter import get_sql_adapter
            adapter = get_sql_adapter()
            
            if not adapter:
                logger.warning("⚠️ SQL Server adapter não disponível - histórico não será gravado")
                return None
            
            # Buscar id_documento se existir
            id_documento = None
            query_id = """
                SELECT TOP 1 id_documento
                FROM DOCUMENTO_ADUANEIRO
                -- ✅ CORREÇÃO (16/01/2026): compatibilidade com colunas antigas tipo TEXT
                WHERE CAST(numero_documento AS VARCHAR(50)) = ? AND CAST(tipo_documento AS VARCHAR(50)) = ?
                ORDER BY atualizado_em DESC
            """
            # ✅ CORREÇÃO: Formatar query com parâmetros
            query_id_formatted = query_id.replace('?', f"'{numero_documento}'", 1).replace('?', f"'{tipo_documento}'", 1)
            result_id = adapter.execute_query(query_id_formatted)
            if result_id and result_id.get('success') and result_id.get('data'):
                data = result_id.get('data', [])
                if data and len(data) > 0:
                    id_documento = data[0].get('id_documento')
            
            # Preparar dados para inserção
            json_dados_originais = json.dumps(dados_novos, ensure_ascii=False, default=str)
            
            # Inserir histórico
            query = """
                INSERT INTO HISTORICO_DOCUMENTO_ADUANEIRO (
                    id_documento,
                    numero_documento,
                    tipo_documento,
                    processo_referencia,
                    data_evento,
                    tipo_evento,
                    tipo_evento_descricao,
                    campo_alterado,
                    valor_anterior,
                    valor_novo,
                    status_documento,
                    status_documento_codigo,
                    canal_documento,
                    situacao_documento,
                    fonte_dados,
                    api_endpoint,
                    json_dados_originais,
                    usuario_ou_sistema,
                    criado_em
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, GETDATE()
                )
            """
            
            # Extrair status atual dos dados novos
            status_atual = dados_novos.get('situacaoCarga') or dados_novos.get('situacao') or dados_novos.get('situacaoAtual')
            canal_atual = dados_novos.get('canal') or dados_novos.get('canalDi') or dados_novos.get('canalDuimp')
            status_codigo_atual = (
                dados_novos.get('situacaoCargaCodigo')
                or dados_novos.get('situacaoDiCodigo')
                or dados_novos.get('situacaoAtualCodigo')
                or dados_novos.get('situacaoCodigo')
                or dados_novos.get('statusDocumentoCodigo')
                or dados_novos.get('codigoSituacao')
            )
            
            params = (
                id_documento,
                numero_documento,
                tipo_documento,
                processo_referencia,
                mudanca.get('data_evento') or datetime.now(),
                mudanca.get('tipo_evento'),
                f"{mudanca.get('campo_alterado')} mudou de '{mudanca.get('valor_anterior')}' para '{mudanca.get('valor_novo')}'",
                mudanca.get('campo_alterado'),
                mudanca.get('valor_anterior'),
                mudanca.get('valor_novo'),
                status_atual,
                status_codigo_atual,
                canal_atual,
                status_atual,  # situacao_documento = status_atual
                fonte_dados,
                api_endpoint,
                json_dados_originais,
                'SISTEMA'  # usuario_ou_sistema
            )
            
            query_formatted = query
            for param in params:
                query_formatted = query_formatted.replace("?", self._sql_literal(param), 1)

            adapter.execute_query(query_formatted, database=adapter.database)
            
            logger.debug(f"✅ Histórico gravado: {tipo_documento} {numero_documento} - {mudanca.get('campo_alterado')}")
            
            return {
                'numero_documento': numero_documento,
                'tipo_documento': tipo_documento,
                'tipo_evento': mudanca.get('tipo_evento'),
                'campo_alterado': mudanca.get('campo_alterado'),
                'valor_anterior': mudanca.get('valor_anterior'),
                'valor_novo': mudanca.get('valor_novo')
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gravar histórico: {e}", exc_info=True)
            return None
    
    def _atualizar_documento(
        self,
        numero_documento: str,
        tipo_documento: str,
        processo_referencia: Optional[str],
        campos_novos: Dict[str, Any],
        fonte_dados: str,
        dados_novos: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Atualiza documento na tabela DOCUMENTO_ADUANEIRO.
        
        Se documento não existir, cria novo registro.
        """
        try:
            from utils.sql_server_adapter import get_sql_adapter
            adapter = get_sql_adapter()
            
            if not adapter:
                logger.warning("⚠️ SQL Server adapter não disponível - documento não será atualizado")
                return False
            
            # ✅ CORREÇÃO: Verificar se documento já existe (por número + tipo)
            # Busca o mais recente para evitar duplicatas
            numero_escaped = numero_documento.replace("'", "''")
            tipo_escaped = tipo_documento.replace("'", "''")
            versao_documento = self._extrair_versao_documento(dados_novos, tipo_documento)
            versao_norm = self._normalizar_versao_documento(versao_documento)
            if not versao_norm:
                versao_where = "versao_documento IS NULL"
            else:
                versao_escaped = versao_norm.replace("'", "''")
                versao_where = f"versao_documento = '{versao_escaped}'"
            
            query_check = f"""
                SELECT TOP 1 id_documento, processo_referencia
                FROM DOCUMENTO_ADUANEIRO
                -- ✅ CORREÇÃO (16/01/2026): compatibilidade com colunas antigas tipo TEXT
                WHERE CAST(numero_documento AS VARCHAR(50)) = '{numero_escaped}' 
                  AND CAST(tipo_documento AS VARCHAR(50)) = '{tipo_escaped}'
                  AND ({versao_where})
                ORDER BY atualizado_em DESC
            """
            
            result_check = adapter.execute_query(query_check, database=adapter.database)
            
            # ✅ CORREÇÃO: Verificar se result_check tem dados corretamente
            documento_existe = False
            id_documento_existente = None
            if result_check and result_check.get('success'):
                data = result_check.get('data', [])
                if data and len(data) > 0:
                    documento_existe = True
                    id_documento_existente = data[0].get('id_documento')
            
            if documento_existe:
                # ✅ NOVO: Buscar valores atuais do documento para comparar
                query_atual = f"""
                    SELECT TOP 1 
                        processo_referencia,
                        versao_documento,
                        status_documento,
                        status_documento_codigo,
                        canal_documento,
                        situacao_documento,
                        data_registro,
                        data_situacao,
                        data_desembaraco,
                        json_dados_originais
                    FROM DOCUMENTO_ADUANEIRO
                    WHERE id_documento = {id_documento_existente}
                """
                result_atual = adapter.execute_query(query_atual, database=adapter.database)
                documento_atual = result_atual.get('data', [{}])[0] if result_atual.get('success') and result_atual.get('data') else {}
                
                # ✅ NOVO: Verificar se realmente há mudanças antes de fazer UPDATE
                status_val = campos_novos.get('status_documento')
                status_codigo_val = campos_novos.get('status_documento_codigo')
                canal_val = campos_novos.get('canal_documento')
                situacao_val = campos_novos.get('situacao_documento')
                data_registro_val = campos_novos.get('data_registro')
                data_situacao_val = campos_novos.get('data_situacao')
                data_desembaraco_val = campos_novos.get('data_desembaraco')
                json_val = None
                try:
                    if dados_novos is not None:
                        json_val = json.dumps(dados_novos, ensure_ascii=False, default=str)
                except Exception:
                    json_val = None
                
                # Comparar valores (normalizar para comparação)
                def normalizar_valor(val):
                    if val is None:
                        return None
                    return str(val).strip() if isinstance(val, str) else str(val)
                
                tem_mudancas = False
                
                # Verificar processo_referencia
                processo_atual = normalizar_valor(documento_atual.get('processo_referencia'))
                processo_novo = normalizar_valor(processo_referencia)
                if processo_novo and processo_atual != processo_novo:
                    tem_mudancas = True

                # Verificar versao_documento (preencher se vier e estiver vazio no banco)
                versao_atual = normalizar_valor(documento_atual.get('versao_documento'))
                versao_nova = normalizar_valor(versao_norm)
                if versao_nova and not versao_atual:
                    tem_mudancas = True
                
                # Verificar outros campos
                if not tem_mudancas:
                    if normalizar_valor(documento_atual.get('status_documento')) != normalizar_valor(status_val):
                        tem_mudancas = True
                    elif normalizar_valor(documento_atual.get('status_documento_codigo')) != normalizar_valor(status_codigo_val):
                        tem_mudancas = True
                    elif normalizar_valor(documento_atual.get('canal_documento')) != normalizar_valor(canal_val):
                        tem_mudancas = True
                    elif normalizar_valor(documento_atual.get('situacao_documento')) != normalizar_valor(situacao_val):
                        tem_mudancas = True
                    elif normalizar_valor(documento_atual.get('data_registro')) != normalizar_valor(data_registro_val):
                        tem_mudancas = True
                    elif normalizar_valor(documento_atual.get('data_situacao')) != normalizar_valor(data_situacao_val):
                        tem_mudancas = True
                    elif normalizar_valor(documento_atual.get('data_desembaraco')) != normalizar_valor(data_desembaraco_val):
                        tem_mudancas = True
                    # ✅ Se ainda não temos JSON salvo, preencher mesmo sem outras mudanças
                    elif documento_atual.get('json_dados_originais') is None and json_val:
                        tem_mudancas = True
                
                # Se não há mudanças, retornar True mas sem fazer UPDATE (evita log desnecessário)
                if not tem_mudancas:
                    logger.debug(f"ℹ️ Documento {tipo_documento} {numero_documento} sem mudanças - pulando UPDATE no SQL Server")
                    return True  # Retorna True para indicar "sucesso" mas sem fazer UPDATE
                
                # ✅ CORREÇÃO: Atualizar existente usando id_documento (evita duplicatas)
                processo_escaped = processo_referencia.replace("'", "''") if processo_referencia else None
                
                # Construir SET clauses dinamicamente (evitar f-strings aninhadas)
                set_parts = []
                # ✅ CORREÇÃO: Sempre atualizar processo_referencia se foi fornecido
                if processo_referencia:
                    set_parts.append(f"processo_referencia = '{processo_escaped}'")
                if versao_norm:
                    versao_escaped = versao_norm.replace("'", "''")
                    set_parts.append(f"versao_documento = '{versao_escaped}'")
                # Se processo_referencia for None mas queremos limpar, não fazemos nada (mantém o valor atual)
                
                # Formatar valores para SQL
                # ✅ CORREÇÃO: Converter para string se for dict ou outro tipo
                def formatar_valor_sql(val):
                    if val is None:
                        return 'NULL'
                    if isinstance(val, dict):
                        # Se for dict, tentar extrair valor útil ou converter para string JSON
                        val_str = str(val)
                    elif isinstance(val, (list, tuple)):
                        val_str = str(val)
                    else:
                        val_str = str(val)
                    # Escapar aspas simples
                    val_str = val_str.replace("'", "''")
                    return f"'{val_str}'"
                
                status_sql = formatar_valor_sql(status_val)
                status_codigo_sql = formatar_valor_sql(status_codigo_val)
                canal_sql = formatar_valor_sql(canal_val)
                situacao_sql = formatar_valor_sql(situacao_val)
                data_registro_sql = f"'{data_registro_val}'" if data_registro_val else 'NULL'
                data_situacao_sql = f"'{data_situacao_val}'" if data_situacao_val else 'NULL'
                data_desembaraco_sql = f"'{data_desembaraco_val}'" if data_desembaraco_val else 'NULL'
                fonte_escaped = str(fonte_dados).replace("'", "''")
                fonte_sql = "'" + fonte_escaped + "'"
                json_sql = formatar_valor_sql(json_val)
                
                set_parts.append(f"status_documento = {status_sql}")
                set_parts.append(f"status_documento_codigo = {status_codigo_sql}")
                set_parts.append(f"canal_documento = {canal_sql}")
                set_parts.append(f"situacao_documento = {situacao_sql}")
                set_parts.append(f"data_registro = {data_registro_sql}")
                set_parts.append(f"data_situacao = {data_situacao_sql}")
                set_parts.append(f"data_desembaraco = {data_desembaraco_sql}")
                set_parts.append(f"fonte_dados = {fonte_sql}")
                set_parts.append(f"json_dados_originais = {json_sql}")
                set_parts.append("ultima_sincronizacao = GETDATE()")
                set_parts.append("atualizado_em = GETDATE()")
                
                query = f"""
                    UPDATE DOCUMENTO_ADUANEIRO
                    SET {', '.join(set_parts)}
                    WHERE id_documento = {id_documento_existente}
                """
                params = None  # Query já formatada
            else:
                # Criar novo
                json_insert = None
                try:
                    if dados_novos is not None:
                        json_insert = json.dumps(dados_novos, ensure_ascii=False, default=str)
                except Exception:
                    json_insert = None
                query_formatted = f"""
                    INSERT INTO DOCUMENTO_ADUANEIRO (
                        numero_documento,
                        tipo_documento,
                        versao_documento,
                        processo_referencia,
                        status_documento,
                        status_documento_codigo,
                        canal_documento,
                        situacao_documento,
                        data_registro,
                        data_situacao,
                        data_desembaraco,
                        fonte_dados,
                        json_dados_originais,
                        ultima_sincronizacao,
                        criado_em,
                        atualizado_em
                    ) VALUES (
                        {self._sql_literal(numero_documento)},
                        {self._sql_literal(tipo_documento)},
                        {self._sql_literal(versao_norm)},
                        {self._sql_literal(processo_referencia)},
                        {self._sql_literal(campos_novos.get('status_documento'))},
                        {self._sql_literal(campos_novos.get('status_documento_codigo'))},
                        {self._sql_literal(campos_novos.get('canal_documento'))},
                        {self._sql_literal(campos_novos.get('situacao_documento'))},
                        {self._sql_literal(campos_novos.get('data_registro'))},
                        {self._sql_literal(campos_novos.get('data_situacao'))},
                        {self._sql_literal(campos_novos.get('data_desembaraco'))},
                        {self._sql_literal(fonte_dados)},
                        {self._sql_literal(json_insert)},
                        GETDATE(),
                        GETDATE(),
                        GETDATE()
                    )
                """
                params = None
                query = query_formatted
            
            # ✅ CORREÇÃO: Formatar query com parâmetros (apenas se não foi formatada antes)
            if params is not None:
                query_formatted = query
                for param in params:
                    if param is None:
                        query_formatted = query_formatted.replace('?', 'NULL', 1)
                    elif isinstance(param, str):
                        # Escapar aspas simples
                        param_escaped = param.replace("'", "''")
                        query_formatted = query_formatted.replace('?', f"'{param_escaped}'", 1)
                    else:
                        query_formatted = query_formatted.replace('?', str(param), 1)
            else:
                query_formatted = query  # Já formatada
            
            result = adapter.execute_query(query_formatted, database=adapter.database)
            if result and result.get('success'):
                logger.debug(f"✅ Documento {'atualizado' if documento_existe else 'criado'}: {tipo_documento} {numero_documento}")
                return True
            else:
                error_msg = result.get('error', 'Erro desconhecido') if result else 'Sem resposta'
                logger.warning(f"⚠️ Erro ao {'atualizar' if documento_existe else 'criar'} documento {tipo_documento} {numero_documento}: {error_msg}")
                logger.debug(f"   Query executada: {query_formatted[:200]}...")  # Log parcial da query para debug
                return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar documento: {e}", exc_info=True)
            return False

