"""
Repositório para consultar processos de importação.
Busca em múltiplas fontes: SQLite (Kanban) → API Kanban → SQL Server (processos antigos)
"""
import logging
import sqlite3
import json
import requests
import os
from typing import Optional, Dict, Any
from datetime import datetime

from .models.processo_kanban_dto import ProcessoKanbanDTO

logger = logging.getLogger(__name__)


class ProcessoRepository:
    """Repositório para consultar processos"""
    
    # ✅ Configurável via .env (KANBAN_API_URL). Fallback mantém compatibilidade.
    API_KANBAN_URL = os.getenv("KANBAN_API_URL", "http://172.16.10.211:5000/api/kanban/pedidos")
    
    def __init__(self):
        """Inicializa o repositório"""
        from db_manager import get_db_connection, DB_PATH
        self.db_path = DB_PATH
    
    def buscar_por_referencia(self, processo_referencia: str) -> Optional[ProcessoKanbanDTO]:
        """
        Busca processo por referência.
        
        ⚠️ CRÍTICO: Ordem de busca restaurada (cache primeiro, como antes)
        
        Estratégia de busca (em ordem):
        1. SQLite (cache do Kanban) - busca rápida primeiro
        2. SQL Server (banco novo 'mAIke_assistente' → banco antigo 'Make' como fallback)
        3. API Kanban (processos ativos) - último recurso
        
        Args:
            processo_referencia: Ex: "ALH.0168/25"
        
        Returns:
            ProcessoKanbanDTO ou None se não encontrar
        """
        processo_ref_upper = processo_referencia.upper().strip()
        logger.info(f"🔍 Buscando processo: {processo_ref_upper}")
        
        # ✅ CORREÇÃO: Restaurar ordem original (cache primeiro, depois SQL Server)
        # Isso garante que processos no cache sejam encontrados rapidamente
        # e processos antigos no banco antigo também sejam encontrados
        
        # ✅ PRIORIDADE 1: SQLite (cache do Kanban) - busca rápida primeiro
        logger.debug(f"📡 Buscando no SQLite (cache)...")
        processo = self._buscar_sqlite(processo_ref_upper)
        if processo:
            logger.info(f"✅ Processo {processo_ref_upper} encontrado no SQLite (cache)")

            # ✅ AUTO-HEAL (Kanban → SQLite):
            # Se o processo existe no cache mas está "capado" (ex.: sem ETA/porto/navio/status ou sem shipgov2),
            # tentar buscar a versão mais recente na API do Kanban e atualizar o cache.
            #
            # Motivação: o mAIke recebe mudanças via snapshots do Kanban; às vezes um snapshot pode perder campos.
            # Aqui corrigimos no momento da consulta (sob demanda) sem depender do job de sincronização.
            try:
                shipgov2_presente = bool(
                    processo.dados_completos
                    and isinstance(processo.dados_completos, dict)
                    and isinstance(processo.dados_completos.get("shipgov2"), dict)
                    and bool(processo.dados_completos.get("shipgov2"))
                )
                tracking_incompleto = bool(
                    processo.eta_iso is None
                    or not processo.porto_codigo
                    or not processo.porto_nome
                    or not processo.nome_navio
                    or not processo.status_shipsgo
                    or not shipgov2_presente
                )

                if tracking_incompleto:
                    logger.info(
                        f"🔄 [AUTO-HEAL] Cache do processo {processo_ref_upper} está incompleto "
                        f"(eta={bool(processo.eta_iso)}, porto={bool(processo.porto_codigo)}, navio={bool(processo.nome_navio)}, "
                        f"status={bool(processo.status_shipsgo)}, shipgov2={shipgov2_presente}). "
                        "Buscando versão atual na API Kanban..."
                    )
                    processo_api = self._buscar_api_kanban(processo_ref_upper)
                    if processo_api:
                        try:
                            self._salvar_sqlite(processo_api)
                        except Exception as e:
                            logger.debug(f"Erro ao salvar auto-heal no cache (não crítico): {e}")
                        # Se a API trouxe dados melhores, retornar ela
                        return processo_api
            except Exception as e:
                logger.debug(f"⚠️ [AUTO-HEAL] Falha ao avaliar/atualizar tracking do cache: {e}")
            
            # ✅ CRÍTICO (10/01/2026): Verificar se cache tem documentos (CE, DI, DUIMP)
            # Para processos antigos, o cache pode ter o processo mas sem documentos
            # Nesse caso, SEMPRE buscar do SQL Server (fonte primária que tem dados completos)
            tem_documentos_no_cache = bool(
                processo.numero_ce or 
                processo.numero_di or 
                processo.numero_duimp or
                (processo.dados_completos and isinstance(processo.dados_completos, dict) and (
                    processo.dados_completos.get('ce', {}).get('numero') or
                    processo.dados_completos.get('di', {}).get('numero') or
                    processo.dados_completos.get('duimp', {}).get('numero')
                ))
            )

            # ✅ NOVO (22/01/2026): Auto-enriquecer documento de despacho (DI/DUIMP) quando:
            # - o cache tem CE, mas NÃO tem DI e NÃO tem DUIMP
            # - e a situação do CE indica que já está vinculada a documento de despacho
            #
            # Motivação: alguns snapshots do Kanban trazem a situação do CE (ex: VINCULADA_A_DOCUMENTO_DE_DESPACHO)
            # antes de preencher numero_di/numero_duimp. Nesse caso, o SQL Server já tem a vinculação, e o status do chat
            # ficava "sem DUIMP" mesmo existindo (ex: VDM.0006/25).
            try:
                tem_ce_no_cache = bool(processo.numero_ce)
                falta_doc_despacho = (not processo.numero_di) and (not processo.numero_duimp)
                situacao_ce_upper = (processo.situacao_ce or "").upper().strip()
                indicio_vinculo_despacho = (
                    "DOCUMENTO_DE_DESPACHO" in situacao_ce_upper
                    or "VINCULAD" in situacao_ce_upper
                    or "DESPACHO" in situacao_ce_upper
                )

                if tem_ce_no_cache and falta_doc_despacho and indicio_vinculo_despacho:
                    logger.info(
                        f"🔄 [AUTO-ENRICH DOCS] CE indica vínculo a despacho ({situacao_ce_upper}). "
                        f"Buscando DI/DUIMP no SQL Server para {processo_ref_upper}..."
                    )
                    processo_sql_server = self._buscar_sql_server(processo_ref_upper)
                    if processo_sql_server and (processo_sql_server.numero_duimp or processo_sql_server.numero_di):
                        processo_final = self._mesclar_cache_com_sql_server(
                            processo_cache=processo, processo_sql=processo_sql_server
                        )
                        try:
                            self._salvar_sqlite(processo_final)
                        except Exception as e:
                            logger.debug(f"Erro ao salvar auto-enrich docs no cache (não crítico): {e}")
                        return processo_final
            except Exception as e:
                logger.debug(f"⚠️ [AUTO-ENRICH DOCS] Falha ao enriquecer DI/DUIMP via SQL Server: {e}")
            
            # ✅ CRÍTICO: Se não tem documentos no cache, SEMPRE buscar do SQL Server
            if not tem_documentos_no_cache:
                logger.warning(f"⚠️ Processo {processo_ref_upper} encontrado no cache mas SEM documentos (CE/DI/DUIMP). Buscando do SQL Server (banco novo e antigo)...")
                try:
                    processo_sql_server = self._buscar_sql_server(processo_ref_upper)
                    if processo_sql_server:
                        # ✅ SQL Server tem dados completos - SUBSTITUIR cache completamente
                        logger.info(f"✅ SQL Server retornou dados completos com documentos, substituindo cache...")
                        try:
                            self._salvar_sqlite(processo_sql_server)
                            logger.info(f"✅ Cache atualizado com dados completos do SQL Server")
                        except Exception as e:
                            logger.debug(f'Erro ao atualizar cache com dados do SQL Server (não crítico): {e}')
                        # Retornar processo do SQL Server (mais completo)
                        return processo_sql_server
                    else:
                        logger.warning(f"⚠️ Processo {processo_ref_upper} não encontrado no SQL Server também. Retornando cache sem documentos.")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar do SQL Server (retornando cache): {e}")
                    # Retornar cache mesmo com erro (melhor que nada)
                    return processo
            
            # ✅ Se tem documentos no cache, verificar se tem dados completos (valores/impostos)
            # Se SQL Server tiver mais dados, SUBSTITUIR completamente o cache (não apenas mesclar)
            try:
                if processo.dados_completos and isinstance(processo.dados_completos, dict):
                    di_data = processo.dados_completos.get('di', {}) or {}
                    ce_data = processo.dados_completos.get('ce', {}) or {}
                    # Verificar se tem valores/impostos completos (com tratamento de erros)
                    tem_valores_di = bool(di_data.get('valor_mercadoria_descarga_real') or di_data.get('valor_mercadoria_embarque_real'))
                    # ✅ CORREÇÃO: Verificar se pagamentos é lista antes de usar len()
                    pagamentos_di = di_data.get('pagamentos')
                    tem_impostos_di = bool(pagamentos_di and isinstance(pagamentos_di, list) and len(pagamentos_di) > 0)
                    tem_frete_ce = bool(ce_data.get('valor_frete_total'))
                    
                    # ✅ CORREÇÃO: Só buscar do SQL Server se realmente faltar TODOS os dados importantes
                    # Se tiver pelo menos valores OU impostos OU frete, não precisa buscar
                    if not tem_valores_di and not tem_impostos_di and not tem_frete_ce:
                        # Cache não tem NENHUM dado importante, buscar do SQL Server (fonte primária)
                        logger.info(f"📊 Cache tem documentos mas não tem dados importantes (valores/impostos/frete), buscando do SQL Server...")
                        try:
                            processo_sql_server = self._buscar_sql_server(processo_ref_upper)
                            if processo_sql_server:
                                # ✅ Mescla conservadora:
                                # - Kanban/SQLite é melhor para ETAPA/operacional e tracking (ETA/navio/shipgov2)
                                # - SQL Server é melhor para valores/impostos/frete
                                processo_final = self._mesclar_cache_com_sql_server(processo_cache=processo, processo_sql=processo_sql_server)

                                logger.info(f"✅ SQL Server retornou dados completos, mesclando com cache (tracking/etapa preservados)...")
                                try:
                                    self._salvar_sqlite(processo_final)
                                    logger.info(f"✅ Cache atualizado com dados completos do SQL Server")
                                except Exception as e:
                                    logger.debug(f'Erro ao atualizar cache com dados do SQL Server (não crítico): {e}')
                                # Retornar processo mesclado (mais completo + tracking/etapa preservados)
                                return processo_final
                        except Exception as e:
                            logger.debug(f"⚠️ Erro ao buscar do SQL Server para enriquecer dados (não crítico): {e}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao verificar dados completos do cache: {e}. Retornando cache como está.")
            
            return processo
        
        # ✅ PRIORIDADE 2: SQL Server (banco novo e antigo) - se cache não encontrou
        # ✅ CORREÇÃO: Tentar buscar no SQL Server mesmo se a verificação inicial falhar
        # (pode estar disponível durante a busca, ou pode ter processos apenas no banco antigo)
        logger.info(f"📊 Tentando buscar no SQL Server (banco novo e antigo) para {processo_ref_upper}...")
        try:
            processo = self._buscar_sql_server(processo_ref_upper)
            if processo:
                logger.info(f"✅ Processo {processo_ref_upper} encontrado no SQL Server")
                # Salvar no SQLite para cache rápido na próxima vez
                try:
                    self._salvar_sqlite(processo)
                except Exception as e:
                    logger.debug(f'Erro ao salvar no cache (não crítico): {e}')
                return processo
            else:
                logger.debug(f"⚠️ Processo {processo_ref_upper} não encontrado no SQL Server")
        except Exception as e:
            logger.debug(f"⚠️ Erro ao buscar no SQL Server (não crítico, continuando busca): {e}")
        
        # ✅ PRIORIDADE 3: API Kanban (processos ativos) - último recurso
        logger.debug(f"📡 Processo não encontrado no cache nem no SQL Server, buscando na API Kanban...")
        processo = self._buscar_api_kanban(processo_ref_upper)
        if processo:
            # Salvar no SQLite para próxima vez
            logger.info(f"✅ Processo {processo_ref_upper} encontrado na API Kanban, salvando no cache...")
            self._salvar_sqlite(processo)
            return processo
        
        logger.warning(f"⚠️ Processo {processo_ref_upper} não encontrado em nenhuma fonte")
        return None
    
    def _verificar_sql_server_disponivel(self) -> bool:
        """
        Verifica rapidamente se SQL Server está disponível (sem timeout longo).
        
        Returns:
            True se SQL Server está disponível, False caso contrário
        """
        try:
            from utils.sql_server_adapter import get_sql_adapter
            
            sql_adapter = get_sql_adapter()
            if not sql_adapter:
                return False
            
            # Testar conexão com query simples e timeout curto
            result = sql_adapter.execute_query("SELECT 1 AS test", notificar_erro=False)
            return result.get('success', False) if result else False
            
        except Exception as e:
            logger.debug(f"⚠️ SQL Server não disponível: {e}")
            return False
    
    def _buscar_sqlite(self, processo_referencia: str) -> Optional[ProcessoKanbanDTO]:
        """Busca processo no SQLite (cache do Kanban)"""
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM processos_kanban
                WHERE processo_referencia = ?
            ''', (processo_referencia,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Converter Row para dict
                dados = dict(row)
                
                # Parse JSON completo
                dados_completos = {}
                if dados.get('dados_completos_json'):
                    try:
                        dados_completos = json.loads(dados['dados_completos_json'])
                    except:
                        pass
                
                # Criar DTO
                dto = ProcessoKanbanDTO(
                    processo_referencia=dados['processo_referencia'],
                    id_processo_importacao=dados.get('id_processo_importacao'),
                    id_importacao=dados.get('id_importacao'),
                    etapa_kanban=dados.get('etapa_kanban', ''),
                    modal=dados.get('modal', ''),
                    numero_ce=dados.get('numero_ce'),
                    numero_di=dados.get('numero_di'),
                    numero_duimp=dados.get('numero_duimp'),
                    bl_house=dados.get('bl_house'),
                    master_bl=dados.get('master_bl'),
                    situacao_ce=dados.get('situacao_ce'),
                    situacao_di=dados.get('situacao_di'),
                    situacao_entrega=dados.get('situacao_entrega'),
                    tem_pendencias=bool(dados.get('tem_pendencias', 0)),
                    pendencia_icms=dados.get('pendencia_icms'),
                    pendencia_frete=bool(dados.get('pendencia_frete', 0)) if dados.get('pendencia_frete') is not None else None,
                    data_criacao=self._parse_datetime(dados.get('data_criacao')),
                    data_embarque=self._parse_datetime(dados.get('data_embarque')),
                    data_desembaraco=self._parse_datetime(dados.get('data_desembaraco')),
                    data_entrega=self._parse_datetime(dados.get('data_entrega')),
                    data_destino_final=self._parse_datetime(dados.get('data_destino_final')),
                    data_armazenamento=self._parse_datetime(dados.get('data_armazenamento')),
                    data_situacao_carga_ce=self._parse_datetime(dados.get('data_situacao_carga_ce')),
                    data_atracamento=self._parse_datetime(dados.get('data_atracamento')),
                    eta_iso=self._parse_datetime(dados.get('eta_iso')),
                    porto_codigo=dados.get('porto_codigo'),
                    porto_nome=dados.get('porto_nome'),
                    nome_navio=dados.get('nome_navio'),
                    status_shipsgo=dados.get('status_shipsgo'),
                    dados_completos=dados_completos,
                    fonte='sqlite'
                )
                
                return dto
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar processo no SQLite: {e}")
            return None

    def _mesclar_cache_com_sql_server(
        self,
        *,
        processo_cache: ProcessoKanbanDTO,
        processo_sql: ProcessoKanbanDTO,
    ) -> ProcessoKanbanDTO:
        """
        Mescla dois DTOs de forma conservadora:
        - Mantém tracking/etapa do cache (Kanban) quando presente
        - Mantém valores/impostos/frete do SQL Server
        """
        # Começar pelo SQL Server (dados financeiros/tributários)
        merged = processo_sql

        # Preservar ETAPA/MODAL do Kanban (operacional)
        if processo_cache.etapa_kanban:
            merged.etapa_kanban = processo_cache.etapa_kanban
        if processo_cache.modal:
            merged.modal = processo_cache.modal

        # ✅ CRÍTICO: Preservar documentos do Kanban quando SQL vier vazio
        # (cenário típico: Kanban já tem DUIMP/DI mas o consolidado do SQL ainda não trouxe o número no cabeçalho)
        if not merged.numero_ce and processo_cache.numero_ce:
            merged.numero_ce = processo_cache.numero_ce
        if not merged.numero_di and processo_cache.numero_di:
            merged.numero_di = processo_cache.numero_di
        if not merged.numero_duimp and processo_cache.numero_duimp:
            merged.numero_duimp = processo_cache.numero_duimp
        if not merged.numero_dta and getattr(processo_cache, "numero_dta", None):
            merged.numero_dta = getattr(processo_cache, "numero_dta", None)
        if not merged.documento_despacho and getattr(processo_cache, "documento_despacho", None):
            merged.documento_despacho = getattr(processo_cache, "documento_despacho", None)
        if not merged.numero_documento_despacho and getattr(processo_cache, "numero_documento_despacho", None):
            merged.numero_documento_despacho = getattr(processo_cache, "numero_documento_despacho", None)

        # Preservar tracking do Kanban (shipgov2/POD)
        if processo_cache.eta_iso:
            merged.eta_iso = processo_cache.eta_iso
        if processo_cache.porto_codigo:
            merged.porto_codigo = processo_cache.porto_codigo
        if processo_cache.porto_nome:
            merged.porto_nome = processo_cache.porto_nome
        if processo_cache.nome_navio:
            merged.nome_navio = processo_cache.nome_navio
        if processo_cache.status_shipsgo:
            merged.status_shipsgo = processo_cache.status_shipsgo

        # Preservar shipgov2 dentro do JSON completo (se o SQL Server não tiver)
        try:
            cache_json = processo_cache.dados_completos if isinstance(processo_cache.dados_completos, dict) else {}
            sql_json = merged.dados_completos if isinstance(merged.dados_completos, dict) else {}

            cache_shipgov2 = cache_json.get("shipgov2")
            sql_shipgov2 = sql_json.get("shipgov2")
            if isinstance(cache_shipgov2, dict) and cache_shipgov2 and not (isinstance(sql_shipgov2, dict) and sql_shipgov2):
                sql_json["shipgov2"] = cache_shipgov2
                merged.dados_completos = sql_json
        except Exception:
            pass

        # ✅ CRÍTICO: preservar bloco DUIMP do Kanban no JSON completo se o SQL não tiver
        # (isso ajuda o formatter a extrair número/situação/impostos diretamente do snapshot)
        try:
            cache_json = processo_cache.dados_completos if isinstance(processo_cache.dados_completos, dict) else {}
            sql_json = merged.dados_completos if isinstance(merged.dados_completos, dict) else {}

            cache_duimp = cache_json.get("duimp")
            sql_duimp = sql_json.get("duimp")
            sql_duimp_vazio = (
                sql_duimp is None
                or (isinstance(sql_duimp, dict) and len(sql_duimp) == 0)
                or (isinstance(sql_duimp, list) and len(sql_duimp) == 0)
            )
            if cache_duimp is not None and sql_duimp_vazio:
                sql_json["duimp"] = cache_duimp
                merged.dados_completos = sql_json
        except Exception:
            pass

        return merged
    
    def _buscar_api_kanban(self, processo_referencia: str) -> Optional[ProcessoKanbanDTO]:
        """Busca processo na API Kanban tentando múltiplos IPs candidatos"""
        # Lista de IPs candidatos (Escritório, VPN, Legado)
        candidatos = [
            os.getenv("KANBAN_API_URL"), # 1. O que estiver no .env
            "http://172.16.10.211:5000/api/kanban/pedidos", # 2. IP interno Make
            "http://172.16.10.8:5000/api/kanban/pedidos",   # 3. IP SQL Server Office
            "http://172.16.20.10:5000/api/kanban/pedidos",  # 4. IP VPN
            "http://servicesmake.matriz.local:5000/api/kanban/pedidos" # 5. DNS local
        ]
        
        # Remover duplicados e None
        urls_para_tentar = []
        for c in candidatos:
            if c and c not in urls_para_tentar:
                urls_para_tentar.append(c)

        processo_ref_normalizado = processo_referencia.upper().strip()
        
        for url in urls_para_tentar:
            try:
                logger.debug(f"🔍 Tentando API Kanban em: {url} para {processo_ref_normalizado}")
                response = requests.get(url, timeout=5)
                response.raise_for_status()
                
                processos = response.json()
                if isinstance(processos, list):
                    # Buscar processo específico na lista
                    for processo_json in processos:
                        numero_pedido = processo_json.get('numeroPedido', '').strip()
                        if numero_pedido.upper() == processo_ref_normalizado:
                            logger.info(f"🎯 Processo {processo_referencia} encontrado na API Kanban em: {url}")
                            # ✅ Sucesso! Atualizar a URL da classe para as próximas chamadas serem diretas
                            if url != self.API_KANBAN_URL:
                                self.API_KANBAN_URL = url
                            return ProcessoKanbanDTO.from_kanban_json(processo_json)
            except Exception:
                continue
        
        logger.warning(f"⚠️ Processo {processo_referencia} não encontrado na API Kanban em nenhuma das URLs tentadas")
        return None
    
    def _buscar_sql_server(self, processo_referencia: str) -> Optional[ProcessoKanbanDTO]:
        """
        Busca processo no SQL Server (fonte primária - alimenta o JSON Kanban) com dados consolidados.
        
        ⚠️ CRÍTICO: SQL Server é a fonte primária e contém valores/impostos/frete completos.
        
        Estratégia:
        1. Sempre tentar banco NOVO (mAIke_assistente) primeiro (fonte da verdade)
        2. Se não encontrar no NOVO, consultar banco ANTIGO (Make) APENAS para migrar/atualizar o NOVO
        3. Após migrar, re-buscar no NOVO e retornar do NOVO
        4. Se o NOVO estiver indisponível/erro e não for possível migrar, retornar o que for possível (degradação controlada)
        """
        try:
            from .sql_server_processo_schema import buscar_processo_consolidado_sql_server
            
            logger.info(f"📊 Buscando processo {processo_referencia} no SQL Server (fonte primária)...")
            
            # ✅ NOVO: Tentar banco NOVO primeiro (mAIke_assistente)
            logger.info(f"🔍 [_buscar_sql_server] Tentando banco NOVO (mAIke_assistente) para {processo_referencia}...")
            processo_consolidado = buscar_processo_consolidado_sql_server(processo_referencia, database='mAIke_assistente')

            encontrado_no_banco_antigo = False

            # ✅ REGRA: Banco antigo só entra para MIGRAR/ATUALIZAR o banco novo (fonte da verdade)
            if not processo_consolidado:
                from services.db_policy_service import (
                    get_legacy_database,
                    log_legacy_fallback,
                    should_use_legacy_database
                )
                
                # Verificar se fallback está permitido
                if not should_use_legacy_database(processo_referencia):
                    logger.warning(
                        f"🔒 [_buscar_sql_server] Processo {processo_referencia} não encontrado no banco NOVO "
                        f"e fallback para Make está desabilitado"
                    )
                else:
                    log_legacy_fallback(
                        processo_referencia=processo_referencia,
                        tool_name='_buscar_sql_server',
                        caller_function='ProcessoRepository._buscar_sql_server',
                        reason="Processo não encontrado no banco primário, tentando migração/auto-heal"
                    )
                    processo_consolidado_antigo = buscar_processo_consolidado_sql_server(
                        processo_referencia, 
                        database=get_legacy_database()
                    )
                    if processo_consolidado_antigo:
                        encontrado_no_banco_antigo = True
                        logger.info(f"✅ [_buscar_sql_server] Processo {processo_referencia} encontrado no banco ANTIGO (Make)")

                        try:
                            self._migrar_processo_para_banco_novo(processo_consolidado_antigo)
                            logger.info(f"✅ Processo {processo_referencia} migrado/atualizado no banco NOVO (mAIke_assistente)")
                        except Exception as e:
                            logger.warning(
                                f"⚠️ Erro ao migrar processo {processo_referencia} para banco novo (não crítico): {e}"
                            )

                        # Re-buscar no banco NOVO (fonte da verdade)
                        logger.info(f"🔁 [_buscar_sql_server] Re-buscando processo {processo_referencia} no banco NOVO após migração...")
                        try:
                            from services.db_policy_service import get_primary_database
                            db_primary = get_primary_database()
                        except Exception:
                            db_primary = 'mAIke_assistente'

                        processo_consolidado = buscar_processo_consolidado_sql_server(processo_referencia, database=db_primary)
                        if not processo_consolidado:
                            # Degradação controlada: não conseguimos materializar no novo; retornamos o consolidado antigo
                            logger.warning(
                                f"⚠️ [_buscar_sql_server] Migração executada, mas processo {processo_referencia} ainda não aparece no banco NOVO. "
                                "Retornando dados do banco ANTIGO (apenas esta vez)."
                            )
                            processo_consolidado = processo_consolidado_antigo
                    else:
                        logger.warning(f"⚠️ [_buscar_sql_server] Processo {processo_referencia} não encontrado nem no banco ANTIGO (Make)")
            
            if not processo_consolidado:
                logger.debug(f"⚠️ Processo {processo_referencia} não encontrado em nenhum banco SQL Server")
                return None
            
            logger.info(f"✅ Processo {processo_referencia} encontrado no SQL Server com dados consolidados")
            
            # Extrair dados do CE
            ce_data = processo_consolidado.get('ce', {})
            di_data = processo_consolidado.get('di', {})
            duimp_data = processo_consolidado.get('duimp', {})
            cct_data = processo_consolidado.get('cct', {})
            
            # Determinar modal (se houver CCT, provavelmente é aéreo)
            modal = "Aéreo" if cct_data else "Marítimo"
            
            # Determinar etapa/situação
            etapa_kanban = ""
            if di_data.get('situacao'):
                etapa_kanban = di_data['situacao']
            elif duimp_data.get('situacao'):
                etapa_kanban = duimp_data['situacao']
            elif ce_data.get('situacao'):
                etapa_kanban = ce_data['situacao']
            
            # Determinar pendências
            pendencia_frete = ce_data.get('pendencia_frete', False) or cct_data.get('pendencia_frete', False)
            tem_pendencias = pendencia_frete or ce_data.get('pendencia_afrmm', False) or bool(cct_data.get('bloqueios_ativos', []))
            
            # Parse de datas
            def parse_date(date_str):
                if not date_str:
                    return None
                try:
                    if isinstance(date_str, datetime):
                        return date_str
                    return self._parse_datetime(str(date_str))
                except:
                    return None
            
            # ✅ CRÍTICO: Criar DTO completo a partir dos dados consolidados do SQL Server
            # SQL Server tem TODOS os dados: valores, impostos, frete, etc.
            dto = ProcessoKanbanDTO(
                processo_referencia=processo_consolidado.get('processo_referencia', processo_referencia),
                id_processo_importacao=processo_consolidado.get('id_processo_importacao'),
                id_importacao=processo_consolidado.get('id_importacao'),
                etapa_kanban=etapa_kanban,
                modal=modal,
                numero_ce=processo_consolidado.get('numero_ce') or ce_data.get('numero'),
                numero_di=processo_consolidado.get('numero_di') or di_data.get('numero'),
                numero_duimp=processo_consolidado.get('numero_duimp') or duimp_data.get('numero'),
                situacao_ce=ce_data.get('situacao'),
                situacao_di=di_data.get('situacao'),
                situacao_entrega=di_data.get('situacao_entrega'),
                tem_pendencias=tem_pendencias,
                pendencia_frete=pendencia_frete,
                pendencia_icms=None,  # Não disponível no SQL Server diretamente
                data_embarque=parse_date(processo_consolidado.get('data_embarque')),
                data_desembaraco=parse_date(di_data.get('data_desembaraco') or processo_consolidado.get('data_desembaraco')),
                data_entrega=parse_date(ce_data.get('data_destino_final')),
                dados_completos=processo_consolidado,  # ✅ CRÍTICO: Guardar dados completos consolidados (com valores/impostos/frete do SQL Server)
                fonte='sql_server'
            )
            
            # ✅ LOG: Verificar se dados_completos tem valores
            if processo_consolidado.get('ce') and processo_consolidado['ce'].get('valor_frete_total'):
                logger.info(f"✅ Processo {processo_referencia}: CE tem valor_frete_total: {processo_consolidado['ce'].get('valor_frete_total')}")
            if processo_consolidado.get('di'):
                di_consolidado = processo_consolidado['di']
                if di_consolidado.get('valor_mercadoria_descarga_real') or di_consolidado.get('valor_mercadoria_embarque_real'):
                    logger.info(f"✅ Processo {processo_referencia}: DI tem valores de mercadoria (descarga: {di_consolidado.get('valor_mercadoria_descarga_real')}, embarque: {di_consolidado.get('valor_mercadoria_embarque_real')})")
                if di_consolidado.get('nome_importador'):
                    logger.info(f"✅ Processo {processo_referencia}: DI tem nome_importador: {di_consolidado.get('nome_importador')}")
            
            logger.info(f"✅ Processo {processo_referencia} convertido para DTO (fonte: SQL Server) - dados completos com valores/impostos/frete")
            return dto
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar processo no SQL Server: {e}", exc_info=True)
            return None
    
    def _migrar_processo_para_banco_novo(self, processo_consolidado: Dict[str, Any]) -> bool:
        """
        Migra processo do banco antigo (Make) para o banco novo (mAIke_assistente).
        
        ✅ NOVO: Quando um processo é encontrado apenas no banco antigo, ele é automaticamente
        migrado para o banco novo, permitindo migração gradual e eventual descontinuação do banco antigo.
        
        Args:
            processo_consolidado: Dict com dados consolidados do processo
        
        Returns:
            True se migração foi bem-sucedida, False caso contrário
        """
        try:
            from utils.sql_server_adapter import get_sql_adapter
            
            sql_adapter = get_sql_adapter()
            if not sql_adapter:
                logger.warning("⚠️ SQL Server adapter não disponível - migração não será realizada")
                return False
            
            processo_ref = processo_consolidado.get('processo_referencia', '')
            processo_ref_escaped = processo_ref.replace("'", "''")
            
            # Verificar se processo já existe no banco novo
            # ✅ CORREÇÃO: Verificar se tabela existe antes de tentar migrar
            query_check_table = """
                SELECT COUNT(*) as existe
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PROCESSO_IMPORTACAO'
            """
            result_table = sql_adapter.execute_query(query_check_table, 'mAIke_assistente', None, notificar_erro=False)
            
            tabela_existe = False
            if result_table and result_table.get('success') and result_table.get('data'):
                tabela_existe = len(result_table.get('data', [])) > 0 and result_table.get('data', [{}])[0].get('existe', 0) > 0
            
            if not tabela_existe:
                logger.warning(f"⚠️ Tabela PROCESSO_IMPORTACAO não existe no banco novo - migração não será realizada")
                return False
            
            query_check = f"""
                SELECT TOP 1 numero_processo
                FROM mAIke_assistente.dbo.PROCESSO_IMPORTACAO
                WHERE numero_processo = '{processo_ref_escaped}'
            """
            
            result_check = sql_adapter.execute_query(query_check, 'mAIke_assistente', None, notificar_erro=False)
            
            processo_existe = False
            if result_check and result_check.get('success') and result_check.get('data'):
                processo_existe = len(result_check.get('data', [])) > 0
            
            # Preparar valores para INSERT/UPDATE
            numero_ce = processo_consolidado.get('numero_ce') or (processo_consolidado.get('ce', {}).get('numero') if processo_consolidado.get('ce') else None)
            numero_di = processo_consolidado.get('numero_di') or (processo_consolidado.get('di', {}).get('numero') if processo_consolidado.get('di') else None)
            numero_duimp = processo_consolidado.get('numero_duimp') or (processo_consolidado.get('duimp', {}).get('numero') if processo_consolidado.get('duimp') else None)
            id_importacao = processo_consolidado.get('id_importacao')
            id_processo_importacao = processo_consolidado.get('id_processo_importacao')
            
            # Formatar valores para SQL
            def formatar_valor(val):
                if val is None:
                    return 'NULL'
                if isinstance(val, str):
                    # Escape seguro para SQL Server (string literal)
                    val_sql = val.replace("'", "''")
                    return f"'{val_sql}'"
                if isinstance(val, (datetime,)):
                    return f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'"
                return str(val)
            
            numero_ce_sql = formatar_valor(numero_ce)
            numero_di_sql = formatar_valor(numero_di)
            numero_duimp_sql = formatar_valor(numero_duimp)
            id_importacao_sql = formatar_valor(id_importacao)
            data_embarque_sql = formatar_valor(processo_consolidado.get('data_embarque'))
            data_chegada_prevista_sql = formatar_valor(processo_consolidado.get('data_chegada_prevista'))
            data_desembaraco_sql = formatar_valor(processo_consolidado.get('data_desembaraco'))
            status_processo_sql = formatar_valor(processo_consolidado.get('status_processo'))

            # ✅ CRÍTICO: O schema do banco novo (mAIke_assistente.dbo.PROCESSO_IMPORTACAO) é DIFERENTE do legado.
            # Colunas atuais (19/01/2026): id_processo_importacao (IDENTITY), id_importacao, numero_processo, numero_ce,
            # numero_di, numero_duimp, data_embarque, data_chegada_prevista, data_desembaraco, status_processo,
            # criado_em, atualizado_em.
            #
            # Portanto: migramos SOMENTE os campos compatíveis.
            if processo_existe:
                # UPDATE - atualizar dados existentes
                query = f"""
                    UPDATE mAIke_assistente.dbo.PROCESSO_IMPORTACAO
                    SET 
                        id_importacao = {id_importacao_sql},
                        numero_ce = {numero_ce_sql},
                        numero_di = {numero_di_sql},
                        numero_duimp = {numero_duimp_sql},
                        data_embarque = {data_embarque_sql},
                        data_chegada_prevista = {data_chegada_prevista_sql},
                        data_desembaraco = {data_desembaraco_sql},
                        status_processo = {status_processo_sql},
                        atualizado_em = GETDATE()
                    WHERE numero_processo = '{processo_ref_escaped}'
                """
                logger.debug(f"🔄 Atualizando processo {processo_ref} no banco novo...")
            else:
                # INSERT - criar novo registro
                # ✅ CORREÇÃO: Não incluir id_processo_importacao (é IDENTITY no banco novo)
                query = f"""
                    INSERT INTO mAIke_assistente.dbo.PROCESSO_IMPORTACAO (
                        id_importacao,
                        numero_processo,
                        numero_ce,
                        numero_di,
                        numero_duimp,
                        data_embarque,
                        data_chegada_prevista,
                        data_desembaraco,
                        status_processo,
                        criado_em,
                        atualizado_em
                    ) VALUES (
                        {id_importacao_sql},
                        '{processo_ref_escaped}',
                        {numero_ce_sql},
                        {numero_di_sql},
                        {numero_duimp_sql},
                        {data_embarque_sql},
                        {data_chegada_prevista_sql},
                        {data_desembaraco_sql},
                        {status_processo_sql},
                        GETDATE(),
                        GETDATE()
                    )
                """
                logger.debug(f"🔄 Inserindo processo {processo_ref} no banco novo...")
            
            result = sql_adapter.execute_query(query, 'mAIke_assistente', None, notificar_erro=False)
            
            if result and result.get('success'):
                logger.info(f"✅ Processo {processo_ref} {'atualizado' if processo_existe else 'inserido'} no banco novo com sucesso (migração automática)")
                return True
            else:
                error_msg = result.get('error', 'Erro desconhecido') if result else 'Sem resposta'
                logger.warning(f"⚠️ Erro ao migrar processo {processo_ref}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao migrar processo para banco novo: {e}", exc_info=True)
            return False
    
    def _salvar_sqlite(self, processo: ProcessoKanbanDTO) -> bool:
        """Salva processo no SQLite (cache)"""
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            dados_completos_json_novo = json.dumps(processo.dados_completos, ensure_ascii=False, default=str)

            # ✅ Política conservadora: não apagar dados bons com None/vazio
            eta_iso_final = processo.eta_iso.isoformat() if processo.eta_iso else None
            porto_codigo_final = processo.porto_codigo
            porto_nome_final = processo.porto_nome
            nome_navio_final = processo.nome_navio
            status_shipsgo_final = processo.status_shipsgo
            dados_completos_json_final = dados_completos_json_novo

            # ✅ CRÍTICO: também preservar documentos / documento de despacho (DI/DUIMP/DTA)
            numero_ce_final = processo.numero_ce
            numero_di_final = processo.numero_di
            numero_duimp_final = processo.numero_duimp
            numero_dta_final = getattr(processo, "numero_dta", None)
            documento_despacho_final = getattr(processo, "documento_despacho", None)
            numero_documento_despacho_final = getattr(processo, "numero_documento_despacho", None)

            try:
                conn_prev = get_db_connection()
                conn_prev.row_factory = sqlite3.Row
                cur_prev = conn_prev.cursor()
                cur_prev.execute(
                    """
                    SELECT
                        eta_iso, porto_codigo, porto_nome, nome_navio, status_shipsgo, dados_completos_json,
                        numero_ce, numero_di, numero_duimp,
                        numero_dta, documento_despacho, numero_documento_despacho
                    FROM processos_kanban
                    WHERE processo_referencia = ?
                    """,
                    (processo.processo_referencia,),
                )
                prev = cur_prev.fetchone()
                conn_prev.close()

                if prev:
                    if not eta_iso_final and prev["eta_iso"]:
                        eta_iso_final = prev["eta_iso"]
                    if not porto_codigo_final and prev["porto_codigo"]:
                        porto_codigo_final = prev["porto_codigo"]
                    if not porto_nome_final and prev["porto_nome"]:
                        porto_nome_final = prev["porto_nome"]
                    if not nome_navio_final and prev["nome_navio"]:
                        nome_navio_final = prev["nome_navio"]
                    if not status_shipsgo_final and prev["status_shipsgo"]:
                        status_shipsgo_final = prev["status_shipsgo"]

                    # Preservar documentos se o novo vier vazio
                    if (not numero_ce_final) and prev["numero_ce"]:
                        numero_ce_final = prev["numero_ce"]
                    if (not numero_di_final) and prev["numero_di"]:
                        numero_di_final = prev["numero_di"]
                    if (not numero_duimp_final) and prev["numero_duimp"]:
                        numero_duimp_final = prev["numero_duimp"]

                    # Preservar documento de despacho (duimp/di/dta) se o novo vier vazio
                    if (not numero_dta_final) and prev["numero_dta"]:
                        numero_dta_final = prev["numero_dta"]
                    if (not documento_despacho_final) and prev["documento_despacho"]:
                        documento_despacho_final = prev["documento_despacho"]
                    if (not numero_documento_despacho_final) and prev["numero_documento_despacho"]:
                        numero_documento_despacho_final = prev["numero_documento_despacho"]

                    # Preservar shipgov2 se novo não tiver
                    try:
                        prev_json_raw = prev["dados_completos_json"] or ""
                        prev_has_shipgov2 = False
                        if prev_json_raw:
                            prev_json = json.loads(prev_json_raw)
                            prev_has_shipgov2 = isinstance(prev_json.get("shipgov2"), dict) and bool(prev_json.get("shipgov2"))

                        novo_has_shipgov2 = isinstance((processo.dados_completos or {}).get("shipgov2"), dict) and bool((processo.dados_completos or {}).get("shipgov2"))
                        if prev_has_shipgov2 and not novo_has_shipgov2:
                            dados_completos_json_final = prev_json_raw
                    except Exception:
                        pass
            except Exception:
                pass
            
            cursor.execute('''
                INSERT OR REPLACE INTO processos_kanban (
                    processo_referencia, id_processo_importacao, id_importacao,
                    etapa_kanban, modal, numero_ce, numero_di, numero_duimp,
                    numero_dta, documento_despacho, numero_documento_despacho,
                    bl_house, master_bl, situacao_ce, situacao_di, situacao_entrega,
                    tem_pendencias, pendencia_icms, pendencia_frete,
                    data_criacao, data_embarque, data_desembaraco, data_entrega,
                    data_destino_final, data_armazenamento, data_situacao_carga_ce, data_atracamento,
                    eta_iso, porto_codigo, porto_nome, nome_navio, status_shipsgo,
                    dados_completos_json, fonte
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                processo.processo_referencia,
                processo.id_processo_importacao,
                processo.id_importacao,
                processo.etapa_kanban,
                processo.modal,
                numero_ce_final,
                numero_di_final,
                numero_duimp_final,
                numero_dta_final,
                documento_despacho_final,
                numero_documento_despacho_final,
                processo.bl_house,
                processo.master_bl,
                processo.situacao_ce,
                processo.situacao_di,
                processo.situacao_entrega,
                1 if processo.tem_pendencias else 0,
                processo.pendencia_icms,
                1 if processo.pendencia_frete else 0,
                processo.data_criacao.isoformat() if processo.data_criacao else None,
                processo.data_embarque.isoformat() if processo.data_embarque else None,
                processo.data_desembaraco.isoformat() if processo.data_desembaraco else None,
                processo.data_entrega.isoformat() if processo.data_entrega else None,
                processo.data_destino_final.isoformat() if processo.data_destino_final else None,
                processo.data_armazenamento.isoformat() if processo.data_armazenamento else None,
                processo.data_situacao_carga_ce.isoformat() if processo.data_situacao_carga_ce else None,
                processo.data_atracamento.isoformat() if processo.data_atracamento else None,
                eta_iso_final,
                porto_codigo_final,
                porto_nome_final,
                nome_navio_final,
                status_shipsgo_final,
                dados_completos_json_final,
                processo.fonte
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar processo no SQLite: {e}")
            return False
    
    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime de string"""
        if not date_str:
            return None
        try:
            # Tentar vários formatos
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d",
                "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.replace('Z', '').split('.')[0], fmt)
                except:
                    continue
            return None
        except:
            return None

