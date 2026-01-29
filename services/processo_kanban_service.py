"""
Serviço para sincronizar processos do Kanban com SQLite.
Sincronização automática a cada 5 minutos.
"""
import requests
import json
import logging
import sqlite3
import threading
import time
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ProcessoKanbanService:
    """Serviço para sincronizar processos do Kanban"""
    
    # ✅ Configurável via .env (KANBAN_API_URL). Fallback mantém compatibilidade.
    API_URL = os.getenv("KANBAN_API_URL", "http://172.16.10.211:5000/api/kanban/pedidos")
    SYNC_INTERVAL = 300  # 5 minutos
    
    def __init__(self, db_path: Optional[str] = None):
        """Inicializa o serviço"""
        from db_manager import get_db_connection, DB_PATH
        self.db_path = Path(db_path) if db_path else Path(DB_PATH)
    
    def sincronizar(self) -> bool:
        """Sincroniza processos do Kanban para SQLite"""
        started = datetime.now()
        repo_sync = None
        try:
            from services.sync_status_repository import SyncStatusRepository

            repo_sync = SyncStatusRepository()
            repo_sync.registrar_attempt("kanban")
        except Exception:
            repo_sync = None

        try:
            # ✅ Garantir que o banco está inicializado com todas as colunas (apenas uma vez por sincronização)
            from db_manager import init_db
            init_db()
            
            logger.info("🔄 Iniciando sincronização de processos do Kanban...")
            
            # 1. Buscar da API
            processos_json = self._buscar_api()
            if not processos_json:
                erro_msg = "Nenhum processo retornado da API"
                logger.error(f"❌ {erro_msg}")
                try:
                    if repo_sync:
                        dur_ms = int((datetime.now() - started).total_seconds() * 1000)
                        repo_sync.registrar_erro("kanban", erro_msg, duration_ms=dur_ms)
                except Exception:
                    pass
                return False
            
            logger.info(f"✅ {len(processos_json)} processos retornados da API")
            
            # 2. Limpar processos antigos (que não estão mais no Kanban)
            processos_ativos_refs = [p.get('numeroPedido') for p in processos_json if p.get('numeroPedido')]
            self._limpar_processos_antigos(processos_ativos_refs)
            
            # 3. Salvar processos atuais
            salvos = 0
            for processo_json in processos_json:
                if self._salvar_processo(processo_json):
                    salvos += 1
            
            logger.info(f"✅ Sincronização concluída: {salvos}/{len(processos_json)} processos salvos")
            
            # ✅ NOVO: Limpar histórico antigo (> 30 dias) após sincronização
            try:
                from services.notificacao_service import NotificacaoService
                notificacao_service = NotificacaoService()
                notificacao_service._limpar_historico_antigo(dias_retencao=30)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao limpar histórico antigo: {e}")
            
            try:
                if repo_sync:
                    dur_ms = int((datetime.now() - started).total_seconds() * 1000)
                    repo_sync.registrar_sucesso("kanban", count=int(len(processos_json) or 0), duration_ms=dur_ms)
            except Exception:
                pass

            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar processos do Kanban: {e}", exc_info=True)
            try:
                if repo_sync:
                    dur_ms = int((datetime.now() - started).total_seconds() * 1000)
                    repo_sync.registrar_erro("kanban", str(e), duration_ms=dur_ms)
            except Exception:
                pass
            return False
    
    def _buscar_api(self) -> List[Dict[str, Any]]:
        """Busca processos da API Kanban tentando múltiplos IPs candidatos"""
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

        last_error = None
        for url in urls_para_tentar:
            try:
                logger.info(f"📡 Tentando sincronizar Kanban via: {url}")
                response = requests.get(url, timeout=5) # Timeout curto para o loop ser rápido
                response.raise_for_status()
                
                # ✅ Verificar Content-Type
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' not in content_type and 'text/json' not in content_type:
                    continue # Tenta o próximo IP se não for JSON
                
                processos = response.json()
                if isinstance(processos, list):
                    # ✅ Sucesso! Atualizar a URL da instância para as próximas chamadas serem diretas
                    if url != self.API_URL:
                        logger.info(f"🎯 API Kanban encontrada e ativa em: {url}")
                        self.API_URL = url
                    
                    # ✅ NOVO (24/01/2026): Se teve sucesso, limpar erro anterior no banco de status
                    try:
                        from services.sync_status_repository import SyncStatusRepository
                        repo = SyncStatusRepository()
                        # Registrar tentativa sem erro para limpar o campo last_error
                        repo.registrar_attempt("kanban")
                    except Exception as e_status:
                        logger.debug(f"Erro ao limpar status de erro: {e_status}")

                    return processos
            except Exception as e:
                last_error = e
                continue
        
        # Se chegou aqui, todos falharam
        if last_error:
            # Erro de DNS/conexão - mensagem mais clara
            hostname = self.API_URL.split("//")[1].split("/")[0] if "//" in self.API_URL else self.API_URL
            erro_detalhado = str(last_error)
            if "Failed to resolve" in erro_detalhado or "No address associated" in erro_detalhado:
                erro_msg = f"DNS não resolve: {hostname}. Verifique conectividade ou configure KANBAN_API_URL com IP direto."
            else:
                erro_msg = f"Erro de conexão: {hostname} não acessível. Verifique se o servidor está online."
            logger.error(f"❌ Todas as tentativas de conexão à API Kanban falharam. Último erro: {last_error}")
            raise requests.exceptions.ConnectionError(erro_msg) from last_error
        
        return []
    
    def _limpar_processos_antigos(self, processos_ativos_refs: List[str]) -> None:
        """Remove processos do SQLite que não estão mais no Kanban"""
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Criar lista de placeholders para IN clause
            if processos_ativos_refs:
                placeholders = ','.join('?' * len(processos_ativos_refs))
                cursor.execute(f'''
                    DELETE FROM processos_kanban 
                    WHERE processo_referencia NOT IN ({placeholders})
                ''', processos_ativos_refs)
                deletados = cursor.rowcount
                if deletados > 0:
                    logger.info(f"🗑️ {deletados} processos antigos removidos do cache")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"❌ Erro ao limpar processos antigos: {e}")
    
    def _buscar_processo_anterior(self, processo_referencia: str) -> Optional[Dict[str, Any]]:
        """Busca versão anterior do processo no SQLite para comparação"""
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT dados_completos_json FROM processos_kanban 
                WHERE processo_referencia = ?
            ''', (processo_referencia,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row[0]:
                return json.loads(row[0])
            
            return None
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar processo anterior {processo_referencia}: {e}")
            return None
    
    def _salvar_processo(self, processo_json: Dict[str, Any]) -> bool:
        """Salva um processo no SQLite usando o DTO para parse correto e detecta mudanças"""
        try:
            from db_manager import get_db_connection
            from services.models.processo_kanban_dto import ProcessoKanbanDTO
            from services.notificacao_service import NotificacaoService
            from services.shipsgo_sync_service import ShipsGoSyncService
            
            # Usar DTO para extrair dados corretamente do JSON
            dto = ProcessoKanbanDTO.from_kanban_json(processo_json)
            
            if not dto.processo_referencia:
                logger.warning(f"⚠️ Processo sem número de pedido, ignorando...")
                return False
            
            # ✅ NOVO: Buscar versão anterior para comparação
            processo_anterior_json = self._buscar_processo_anterior(dto.processo_referencia)
            dto_anterior_para_etapa = None
            if processo_anterior_json:
                try:
                    dto_anterior_para_etapa = ProcessoKanbanDTO.from_kanban_json(processo_anterior_json)
                except Exception:
                    dto_anterior_para_etapa = None
            
            # ✅ CORREÇÃO CRÍTICA: Verificar se processo é antigo/finalizado ANTES de criar notificações
            # Não criar notificações para processos entregues ou processos antigos inativos
            deve_criar_notificacoes = True
            
            # Verificar se está entregue
            situacao_ce = (dto.situacao_ce or '').upper()
            situacao_entrega = (dto.situacao_entrega or '').upper()
            if 'ENTREGUE' in situacao_ce or 'ENTREGUE' in situacao_entrega:
                deve_criar_notificacoes = False
                logger.debug(f"ℹ️ Processo {dto.processo_referencia} está ENTREGUE - não criar notificações")
            
            # Verificar se é processo antigo inativo (sem documentos, sem ETA futuro)
            if deve_criar_notificacoes and dto.processo_referencia:
                try:
                    # Extrair ano do processo (formato: CATEGORIA.NUMERO/AA)
                    partes = dto.processo_referencia.split('/')
                    if len(partes) == 2:
                        ano = partes[1]
                        if ano and len(ano) == 2:
                            ano_completo = 2000 + int(ano)
                            ano_atual = datetime.now().year
                            
                            # Se processo é de 2024 ou anterior
                            if ano_completo < ano_atual:
                                tem_documentos = bool(
                                    dto.numero_ce or 
                                    (dto.numero_di and dto.numero_di not in ('', '/       -')) or 
                                    dto.numero_duimp
                                )
                                tem_eta_futuro = False
                                if dto.eta_iso:
                                    try:
                                        if isinstance(dto.eta_iso, str):
                                            if 'T' in dto.eta_iso:
                                                eta_date = datetime.fromisoformat(dto.eta_iso.replace('Z', '').split('+')[0].split('.')[0])
                                            else:
                                                eta_date = datetime.strptime(dto.eta_iso.split(' ')[0], '%Y-%m-%d')
                                        else:
                                            eta_date = dto.eta_iso
                                        
                                        if eta_date.date() >= datetime.now().date():
                                            tem_eta_futuro = True
                                    except:
                                        pass
                                
                                # Se não tem documentos nem ETA futuro, é processo antigo inativo
                                if not tem_documentos and not tem_eta_futuro:
                                    deve_criar_notificacoes = False
                                    logger.debug(f"ℹ️ Processo {dto.processo_referencia} é antigo ({ano_completo}) e inativo - não criar notificações")
                except Exception as e:
                    logger.debug(f"Erro ao verificar se processo é antigo: {e}")
            
            # ✅ NOVO: Detectar mudanças e criar notificações ANTES de salvar (apenas se deve criar)
            if deve_criar_notificacoes and processo_anterior_json:
                # Converter processo anterior para DTO para comparação correta
                dto_anterior = ProcessoKanbanDTO.from_kanban_json(processo_anterior_json)
                notificacao_service = NotificacaoService()
                notificacoes_criadas = notificacao_service.detectar_mudancas_e_notificar(dto_anterior, dto)
                if notificacoes_criadas:
                    logger.info(f"🔔 {len(notificacoes_criadas)} notificação(ões) criada(s) para {dto.processo_referencia}")
            elif not deve_criar_notificacoes:
                logger.debug(f"ℹ️ Processo {dto.processo_referencia} não deve receber notificações (entregue/antigo) - pulando detecção de mudanças")
            else:
                logger.debug(f"ℹ️ Processo {dto.processo_referencia} é novo - sem versão anterior para comparar")

            # ✅ NOVO (19/01/2026): Registrar mudança de etapa (lead time por etapa)
            # Mesmo que não crie notificações, o histórico é útil para monitoramento de processos ativos.
            try:
                if deve_criar_notificacoes:
                    etapa_anterior = (dto_anterior_para_etapa.etapa_kanban if dto_anterior_para_etapa else None)
                    etapa_nova = dto.etapa_kanban or ''
                    if etapa_nova and etapa_nova != (etapa_anterior or ''):
                        self._registrar_mudanca_etapa(
                            processo_referencia=dto.processo_referencia,
                            etapa_anterior=etapa_anterior,
                            etapa_nova=etapa_nova,
                            modal=dto.modal,
                        )
            except Exception as e:
                logger.debug(f"ℹ️ Erro ao registrar mudança de etapa para {dto.processo_referencia}: {e}")
            
            # Preparar dados completos JSON
            dados_completos_json_novo = json.dumps(processo_json, ensure_ascii=False, default=str)

            # ✅ REGRA CRÍTICA (fonte da verdade / evitar regressão):
            # Kanban é fonte derivada e pode vir "capado" (ex.: sem shipgov2). NÃO podemos apagar
            # campos logísticos já conhecidos (ETA/Navio/Status/Porto) nem sobrescrever um JSON rico
            # por um JSON menor que perdeu shipgov2.
            eta_iso_final = dto.eta_iso
            porto_codigo_final = dto.porto_codigo
            porto_nome_final = dto.porto_nome
            nome_navio_final = dto.nome_navio
            status_shipsgo_final = dto.status_shipsgo
            dados_completos_json_final = dados_completos_json_novo

            try:
                conn_prev = get_db_connection()
                conn_prev.row_factory = sqlite3.Row
                cur_prev = conn_prev.cursor()
                cur_prev.execute(
                    """
                    SELECT eta_iso, porto_codigo, porto_nome, nome_navio, status_shipsgo, dados_completos_json
                    FROM processos_kanban
                    WHERE processo_referencia = ?
                    """,
                    (dto.processo_referencia,),
                )
                prev = cur_prev.fetchone()
                conn_prev.close()

                if prev:
                    # Preservar campos se o novo vier vazio
                    if eta_iso_final is None and prev["eta_iso"]:
                        eta_iso_final = prev["eta_iso"]
                    if not porto_codigo_final and prev["porto_codigo"]:
                        porto_codigo_final = prev["porto_codigo"]
                    if not porto_nome_final and prev["porto_nome"]:
                        porto_nome_final = prev["porto_nome"]
                    if not nome_navio_final and prev["nome_navio"]:
                        nome_navio_final = prev["nome_navio"]
                    if not status_shipsgo_final and prev["status_shipsgo"]:
                        status_shipsgo_final = prev["status_shipsgo"]

                    # Preservar JSON rico (shipgov2) se o novo perdeu essa seção
                    try:
                        prev_json_raw = prev["dados_completos_json"] or ""
                        prev_has_shipgov2 = False
                        if prev_json_raw:
                            prev_json = json.loads(prev_json_raw)
                            prev_has_shipgov2 = isinstance(prev_json.get("shipgov2"), dict) and bool(prev_json.get("shipgov2"))

                        novo_has_shipgov2 = isinstance(processo_json.get("shipgov2"), dict) and bool(processo_json.get("shipgov2"))

                        if prev_has_shipgov2 and not novo_has_shipgov2:
                            dados_completos_json_final = prev_json_raw
                    except Exception:
                        # Se der erro no parse, não bloquear o salvamento
                        pass
            except Exception:
                pass
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Formatar datas para string (SQLite)
            def format_date(dt):
                if dt is None:
                    return None
                if isinstance(dt, str):
                    return dt
                return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
            
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
                dto.processo_referencia,
                dto.id_processo_importacao,
                dto.id_importacao,
                dto.etapa_kanban or '',
                dto.modal or '',
                dto.numero_ce,
                dto.numero_di,
                dto.numero_duimp,
                dto.numero_dta,  # ✅ NOVO: DTA
                dto.documento_despacho,  # ✅ NOVO: Tipo de documento (DTA, DI, DUIMP)
                dto.numero_documento_despacho,  # ✅ NOVO: Número do documento
                dto.bl_house,  # BL (marítimo) ou AWB (aéreo) - depende do modal
                dto.master_bl,
                dto.situacao_ce,
                dto.situacao_di,
                dto.situacao_entrega,
                1 if dto.tem_pendencias else 0,
                dto.pendencia_icms,
                1 if dto.pendencia_frete else 0,
                format_date(dto.data_criacao),
                format_date(dto.data_embarque),
                format_date(dto.data_desembaraco),
                format_date(dto.data_entrega),
                format_date(dto.data_destino_final),
                format_date(dto.data_armazenamento),
                format_date(dto.data_situacao_carga_ce),
                format_date(dto.data_atracamento),
                format_date(eta_iso_final),
                porto_codigo_final,
                porto_nome_final,
                nome_navio_final,
                status_shipsgo_final,
                dados_completos_json_final,
                'kanban'
            ))
            
            conn.commit()
            conn.close()

            # ✅ ShipsGo (API oficial) → cache shipsgo_tracking (não bloqueante)
            # Regra: só chama se houver requestId (id_externo_shipsgo) e respeita TTL para evitar custos.
            try:
                # Só sincronizar se o Kanban marcou que o tracking está ativo
                shipsgo_sync_enabled = (os.getenv("SHIPSGO_SYNC_ENABLED", "true") or "true").strip().lower()
                if shipsgo_sync_enabled not in ("1", "true", "yes", "on"):
                    raise RuntimeError("SHIPSGO_SYNC_ENABLED desabilitado")

                consulta_shipgo = (processo_json.get("consulta_shipgo") or (processo_json.get("dados_processo_kanban") or {}).get("consulta_shipgo") or "").lower()
                if consulta_shipgo == "ativo":
                    if not hasattr(self, "_shipsgo_sync_service") or self._shipsgo_sync_service is None:
                        self._shipsgo_sync_service = ShipsGoSyncService(
                            ttl_minutes=int(os.getenv("SHIPSGO_SYNC_TTL_MIN", "60") or "60")
                        )
                    _ = self._shipsgo_sync_service.sync_from_kanban_snapshot(
                    processo_referencia=dto.processo_referencia,
                    processo_json=processo_json,
                    )
            except Exception as e:
                logger.debug(f"ℹ️ ShipsGo sync não executado para {dto.processo_referencia}: {e}")
            
            # ✅ NOVO: Gravar histórico de documentos após salvar processo
            try:
                self._gravar_historico_documentos(dto, processo_json)
            except Exception as e:
                # Não bloquear se houver erro no histórico
                logger.warning(f"⚠️ Erro ao gravar histórico de documentos para {dto.processo_referencia}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar processo {processo_json.get('numeroPedido', 'N/A')}: {e}", exc_info=True)
            return False

    def _registrar_mudanca_etapa(
        self,
        processo_referencia: str,
        etapa_anterior: Optional[str],
        etapa_nova: str,
        modal: Optional[str] = None,
    ) -> None:
        """Registra mudanças de etapa_kanban para cálculo de lead time por etapa."""
        from db_manager import get_db_connection
        from datetime import datetime

        conn = get_db_connection()
        cursor = conn.cursor()

        dados_extras = {
            "modal": modal,
            "changed_at": datetime.now().isoformat(),
        }

        cursor.execute(
            """
            INSERT INTO processo_etapas_historico (
                processo_referencia, etapa_anterior, etapa_nova, changed_at, fonte, dados_extras
            ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'kanban', ?)
            """,
            (processo_referencia, etapa_anterior, etapa_nova, json.dumps(dados_extras, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
    
    def _gravar_historico_documentos(
        self,
        dto: Any,  # ProcessoKanbanDTO
        processo_json: Dict[str, Any]
    ) -> None:
        """
        Grava histórico de mudanças em documentos (CE, DI, DUIMP, CCT) do processo.
        
        Extrai documentos do JSON do Kanban e grava histórico para cada um.
        """
        try:
            from services.documento_historico_service import DocumentoHistoricoService
            
            historico_service = DocumentoHistoricoService()
            processo_ref = dto.processo_referencia
            
            # Extrair documentos do JSON do Kanban
            # O JSON pode ter documentos em diferentes formatos:
            # 1. Números diretos: numeroCE, numeroDI, numeroDUIMP
            # 2. Objetos completos: ce, di, duimp, cct (dentro de dados_processo_kanban ou na raiz)
            
            dados = processo_json.get('dados_processo_kanban', {})
            
            # CE (Conhecimento de Embarque)
            if dto.numero_ce:
                ce_data = self._extrair_documento_do_json(processo_json, 'ce', dto.numero_ce)
                if ce_data:
                    historico_service.detectar_e_gravar_mudancas(
                        numero_documento=str(dto.numero_ce),
                        tipo_documento='CE',
                        dados_novos=ce_data,
                        fonte_dados='KANBAN_API',
                        api_endpoint='/api/kanban/pedidos',
                        processo_referencia=processo_ref
                    )
            
            # DI (Declaração de Importação)
            if dto.numero_di and dto.numero_di not in ('', '/       -'):
                di_data = self._extrair_documento_do_json(processo_json, 'di', dto.numero_di)
                if di_data:
                    historico_service.detectar_e_gravar_mudancas(
                        numero_documento=str(dto.numero_di),
                        tipo_documento='DI',
                        dados_novos=di_data,
                        fonte_dados='KANBAN_API',
                        api_endpoint='/api/kanban/pedidos',
                        processo_referencia=processo_ref
                    )
            
            # DUIMP (Declaração Única de Importação)
            if dto.numero_duimp:
                duimp_data = self._extrair_documento_do_json(processo_json, 'duimp', dto.numero_duimp)
                if duimp_data:
                    historico_service.detectar_e_gravar_mudancas(
                        numero_documento=str(dto.numero_duimp),
                        tipo_documento='DUIMP',
                        dados_novos=duimp_data,
                        fonte_dados='KANBAN_API',
                        api_endpoint='/api/kanban/pedidos',
                        processo_referencia=processo_ref
                    )
            
            # CCT (Conhecimento de Carga Aérea)
            # Para CCT, pode estar no bl_house se for modal aéreo
            if dto.modal and ('AÉREO' in dto.modal.upper() or 'AEREO' in dto.modal.upper()):
                if dto.bl_house:
                    cct_data = self._extrair_documento_do_json(processo_json, 'cct', dto.bl_house)
                    if cct_data:
                        historico_service.detectar_e_gravar_mudancas(
                            numero_documento=str(dto.bl_house),
                            tipo_documento='CCT',
                            dados_novos=cct_data,
                            fonte_dados='KANBAN_API',
                            api_endpoint='/api/kanban/pedidos',
                            processo_referencia=processo_ref
                        )
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gravar histórico de documentos: {e}", exc_info=True)
    
    def _extrair_documento_do_json(
        self,
        processo_json: Dict[str, Any],
        tipo_documento: str,
        numero_documento: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai dados completos de um documento do JSON do Kanban.
        
        Tenta buscar em diferentes lugares:
        1. Objeto completo (ex: processo_json['ce'])
        2. Dentro de dados_processo_kanban (ex: dados['ce'])
        3. Campos individuais (ex: situacaoCargaCe, numeroCE)
        
        Args:
            processo_json: JSON completo do processo
            tipo_documento: 'ce', 'di', 'duimp', 'cct'
            numero_documento: Número do documento
        
        Returns:
            Dict com dados do documento ou None se não encontrar
        """
        dados = processo_json.get('dados_processo_kanban', {})
        
        # Tentar objeto completo primeiro
        documento_obj = None
        
        # Tentar na raiz
        if tipo_documento == 'ce':
            documento_obj = processo_json.get('ce') or dados.get('ce')
        elif tipo_documento == 'di':
            documento_obj = processo_json.get('di') or dados.get('di')
        elif tipo_documento == 'duimp':
            documento_obj = processo_json.get('duimp') or dados.get('duimp')
        elif tipo_documento == 'cct':
            documento_obj = processo_json.get('cct') or dados.get('cct')
        
        # Se encontrou objeto completo, retornar
        if documento_obj and isinstance(documento_obj, dict):
            return documento_obj
        
        # Se não encontrou objeto completo, construir a partir de campos individuais
        documento_data = {
            'numero': numero_documento
        }
        
        if tipo_documento == 'ce':
            documento_data['situacaoCarga'] = processo_json.get('situacaoCargaCe') or dados.get('situacao_ce')
            documento_data['dataSituacaoCarga'] = processo_json.get('dataSituacaoCargaCe') or dados.get('data_situacao_carga_ce')
            documento_data['dataDesembaraco'] = processo_json.get('dataDesembaraco') or dados.get('data_desembaraco')
            documento_data['dataRegistro'] = processo_json.get('dataRegistro') or dados.get('data_registro')
        elif tipo_documento == 'di':
            documento_data['situacaoDi'] = processo_json.get('situacaoDi') or dados.get('situacao_di')
            documento_data['canal'] = processo_json.get('canalDi') or dados.get('canal_di')
            documento_data['dataHoraRegistro'] = processo_json.get('dataHoraRegistro') or dados.get('data_hora_registro')
            documento_data['dataHoraDesembaraco'] = processo_json.get('dataHoraDesembaraco') or dados.get('data_hora_desembaraco')
        elif tipo_documento == 'duimp':
            documento_data['situacao'] = processo_json.get('situacaoDuimp') or dados.get('situacao_duimp')
            documento_data['canal'] = processo_json.get('canalDuimp') or dados.get('canal_duimp')
            documento_data['dataRegistro'] = processo_json.get('dataRegistroDuimp') or dados.get('data_registro_duimp')
        elif tipo_documento == 'cct':
            documento_data['situacaoAtual'] = processo_json.get('situacaoCct') or dados.get('situacao_cct')
            documento_data['dataHoraSituacaoAtual'] = processo_json.get('dataHoraSituacaoCct') or dados.get('data_hora_situacao_cct')
        
        return documento_data if documento_data.get('numero') else None


# =============================================================================
# SINCRONIZAÇÃO AUTOMÁTICA EM BACKGROUND
# =============================================================================

_sync_thread: Optional[threading.Thread] = None
_sync_running = False


def iniciar_sincronizacao_background(intervalo_segundos: int = 300) -> bool:
    """
    Inicia sincronização automática em background.
    
    Args:
        intervalo_segundos: Intervalo entre sincronizações (padrão: 300 = 5 minutos)
    
    Returns:
        True se iniciou com sucesso, False caso contrário
    """
    global _sync_thread, _sync_running
    
    if _sync_running:
        logger.warning("⚠️ Sincronização automática já está em execução")
        return False
    
    service = ProcessoKanbanService()
    _sync_running = True
    
    def sincronizar_periodicamente():
        """Loop de sincronização periódica"""
        logger.info(f"✅ Sincronização automática iniciada (intervalo: {intervalo_segundos}s)")
        
        # ✅ CORREÇÃO: Primeira sincronização com timeout para não travar inicialização
        # Aguardar um pouco antes da primeira sincronização para não bloquear startup
        time.sleep(2)  # Dar tempo para o servidor Flask iniciar
        
        # Primeira sincronização imediata (com timeout implícito via requests)
        try:
            logger.info("🔄 Executando primeira sincronização...")
            service.sincronizar()
            logger.info("✅ Primeira sincronização concluída")
        except Exception as e:
            logger.error(f"❌ Erro na primeira sincronização: {e}")
            # Continuar mesmo com erro (não travar inicialização)
        
        # Loop periódico
        while _sync_running:
            try:
                time.sleep(intervalo_segundos)
                if _sync_running:  # Verificar novamente após o sleep
                    service.sincronizar()
            except Exception as e:
                logger.error(f"❌ Erro na sincronização periódica: {e}")
                # Continuar mesmo com erro (aguardar próximo ciclo)
        
        logger.info("🛑 Sincronização automática encerrada")
    
    _sync_thread = threading.Thread(target=sincronizar_periodicamente, daemon=True)
    _sync_thread.start()
    
    return True


def parar_sincronizacao_background() -> bool:
    """
    Para a sincronização automática em background.
    
    Returns:
        True se parou com sucesso, False caso contrário
    """
    global _sync_running
    
    if not _sync_running:
        logger.warning("⚠️ Sincronização automática já está parada")
        return False
    
    logger.info("🛑 Parando sincronização automática...")
    _sync_running = False
    
    return True


def status_sincronizacao() -> Dict[str, Any]:
    """
    Retorna status da sincronização automática.
    
    Returns:
        Dict com informações sobre o status
    """
    return {
        'ativa': _sync_running,
        'thread_viva': _sync_thread.is_alive() if _sync_thread else False
    }

