"""
Gerenciador de banco de dados SQLite para armazenar DUIMPs locais.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import json
import logging
import time
import os

# Logger do módulo
logger = logging.getLogger(__name__)

# Usar variável de ambiente se disponível, senão usar padrão
DB_PATH = Path(os.getenv('DB_PATH', 'chat_ia.db'))

# ✅ CORREÇÃO: Timeout para evitar "database is locked"
SQLITE_TIMEOUT = 10.0  # 10 segundos de timeout
SQLITE_RETRY_ATTEMPTS = 3  # Número de tentativas em caso de lock
SQLITE_RETRY_DELAY = 0.1  # Delay entre tentativas (100ms)

def get_db_connection():
    """
    Cria conexão SQLite com timeout configurado.
    Retorna conexão que será fechada automaticamente.
    """
    # ✅ Wrapper: implementação centralizada em `services/sqlite_db.py`
    from services.sqlite_db import get_db_connection as _get
    return _get()


def _criar_tabela_pending_intents(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/pending_intents_schema.py`."""
    from services.pending_intents_schema import criar_tabela_pending_intents
    criar_tabela_pending_intents(cursor)


def _criar_tabela_email_drafts(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/email_drafts_schema.py`."""
    from services.email_drafts_schema import criar_tabela_email_drafts
    criar_tabela_email_drafts(cursor)


def _criar_tabela_consultas_salvas(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/consultas_salvas_schema.py`."""
    from services.consultas_salvas_schema import criar_tabela_consultas_salvas
    criar_tabela_consultas_salvas(cursor)


def _criar_tabela_regras_aprendidas(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/regras_aprendidas_schema.py`."""
    from services.regras_aprendidas_schema import criar_tabela_regras_aprendidas
    criar_tabela_regras_aprendidas(cursor)


def _criar_tabela_contexto_sessao(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/contexto_sessao_schema.py`."""
    from services.contexto_sessao_schema import criar_tabela_contexto_sessao
    criar_tabela_contexto_sessao(cursor)


def _criar_tabela_processo_documentos(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/processo_documentos_schema.py`."""
    from services.processo_documentos_schema import criar_tabela_processo_documentos
    criar_tabela_processo_documentos(cursor)

def _criar_tabela_nesh_chunks(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/nesh_schema.py`."""
    from services.nesh_schema import criar_tabela_nesh_chunks
    criar_tabela_nesh_chunks(cursor)


def _criar_tabelas_consultas_bilhetadas(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/consultas_bilhetadas_schema.py`."""
    from services.consultas_bilhetadas_schema import criar_tabelas_consultas_bilhetadas
    criar_tabelas_consultas_bilhetadas(cursor)


def _criar_tabela_historico_pagamentos(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/pagamentos_historico_schema.py`."""
    from services.pagamentos_historico_schema import criar_tabela_historico_pagamentos
    criar_tabela_historico_pagamentos(cursor)


def _criar_tabela_shipsgo_tracking(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/shipsgo_schema.py`."""
    from services.shipsgo_schema import criar_tabela_shipsgo_tracking
    criar_tabela_shipsgo_tracking(cursor)


def _criar_tabela_sugestoes_vinculacao(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/sugestoes_vinculacao_schema.py`."""
    from services.sugestoes_vinculacao_schema import criar_tabela_sugestoes_vinculacao
    criar_tabela_sugestoes_vinculacao(cursor)


def _criar_tabelas_duimp(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/duimp_schema.py`."""
    from services.duimp_schema import criar_tabelas_duimp
    criar_tabelas_duimp(cursor)


def _criar_tabelas_processos_importacao(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/processos_importacao_schema.py`."""
    from services.processos_importacao_schema import criar_tabelas_processos_importacao
    criar_tabelas_processos_importacao(cursor)


def _criar_tabelas_ce_cache(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/ce_cache_schema.py`."""
    from services.ce_cache_schema import criar_tabelas_ce_cache
    criar_tabelas_ce_cache(cursor)


def _criar_tabelas_cct_cache(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/cct_cache_schema.py`."""
    from services.cct_cache_schema import criar_tabelas_cct_cache
    criar_tabelas_cct_cache(cursor)


def _criar_tabelas_di_cache(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/di_cache_schema.py`."""
    from services.di_cache_schema import criar_tabelas_di_cache
    criar_tabelas_di_cache(cursor)


def _criar_tabelas_processos_e_kanban(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/processos_kanban_schema.py`."""
    from services.processos_kanban_schema import criar_tabelas_processos_e_kanban
    criar_tabelas_processos_e_kanban(cursor)


def _criar_tabela_notificacoes_processos(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/notificacoes_processos_schema.py`."""
    from services.notificacoes_processos_schema import criar_tabela_notificacoes_processos
    criar_tabela_notificacoes_processos(cursor)


def _criar_tabela_ia_feedback_ncm(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/ia_feedback_ncm_schema.py`."""
    from services.ia_feedback_ncm_schema import criar_tabela_ia_feedback_ncm
    criar_tabela_ia_feedback_ncm(cursor)


def _criar_tabelas_classif_cache(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/classif_cache_schema.py`."""
    from services.classif_cache_schema import criar_tabelas_classif_cache
    criar_tabelas_classif_cache(cursor)


def _criar_tabela_chat_alertas(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/chat_alertas_schema.py`."""
    from services.chat_alertas_schema import criar_tabela_chat_alertas
    criar_tabela_chat_alertas(cursor)


def _criar_tabelas_legislacao(cursor: sqlite3.Cursor) -> None:
    """
    Cria/migra tabelas de legislação (`legislacao`, `legislacao_trecho`) e seus índices.
    """
    # ✅ Wrapper: schema extraído para `services/legislacao_schema.py`
    from services.legislacao_schema import criar_tabelas_legislacao
    criar_tabelas_legislacao(cursor)


def _criar_tabela_sync_status(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/sync_status_schema.py`."""
    from services.sync_status_schema import criar_tabela_sync_status
    criar_tabela_sync_status(cursor)

def _criar_tabela_sales_watch_state(cursor: sqlite3.Cursor) -> None:
    """Wrapper: schema extraído para `services/sales_watch_schema.py`."""
    from services.sales_watch_schema import criar_tabela_sales_watch_state
    criar_tabela_sales_watch_state(cursor)

def init_db():
    """Inicializa o banco de dados (SQLite ou Postgres)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ✅ CORREÇÃO: Habilitar WAL mode apenas para SQLite
    if not os.getenv("USE_POSTGRES", "false").lower() == "true":
        try:
            cursor.execute('PRAGMA journal_mode')
            result = cursor.fetchone()
            current_mode = result[0].upper() if result and result[0] else ''
            
            if current_mode != 'WAL':
                cursor.execute('PRAGMA journal_mode=WAL')
                result = cursor.fetchone()
                if result and result[0] and result[0].upper() == 'WAL':
                    logging.info('✅ WAL mode habilitado no SQLite')
        except Exception as e:
            logging.warning(f'⚠️ Não foi possível habilitar WAL mode: {e}')
    
    # ✅ SCHEMAS EXTRAÍDOS (19/01/2026): manter init_db mais enxuto
    _criar_tabelas_consultas_bilhetadas(cursor)
    _criar_tabela_historico_pagamentos(cursor)
    
    # ✅ SCHEMAS EXTRAÍDOS (19/01/2026): shipsgo + DUIMP
    _criar_tabela_shipsgo_tracking(cursor)
    _criar_tabelas_duimp(cursor)
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): processos de importação / vinculação / log
    _criar_tabelas_processos_importacao(cursor)
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): feedback NCM da IA + índices
    _criar_tabela_ia_feedback_ncm(cursor)
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): CE cache + previsão de atracação + itens do CE
    _criar_tabelas_ce_cache(cursor)
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): CCT cache + migrações
    _criar_tabelas_cct_cache(cursor)
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): DI cache + migrações
    _criar_tabelas_di_cache(cursor)
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): processos + processos_kanban (tabelas + migrações)
    _criar_tabelas_processos_e_kanban(cursor)

    # ✅ NOVO (23/01/2026): status das sincronizações (Kanban, etc.)
    _criar_tabela_sync_status(cursor)

    # ✅ NOVO (28/01/2026): estado do watch de vendas (evita notificações repetidas)
    _criar_tabela_sales_watch_state(cursor)
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): notificações de processos + índices
    _criar_tabela_notificacoes_processos(cursor)
    
    # ✅ NOVO (14/01/2026): pending intents (ações pendentes de confirmação)
    _criar_tabela_pending_intents(cursor)
    
    # ✅ NOVO (17/01/2026): Tabela de notícias do Siscomex (feeds RSS) - schema extraído
    from services.noticias_siscomex_schema import criar_tabela_noticias_siscomex
    criar_tabela_noticias_siscomex(cursor)

    # ✅ NOVO (18/01/2026): NESH em SQLite (substitui JSON gigante em runtime)
    _criar_tabela_nesh_chunks(cursor)
    
    # ✅ Tabela de histórico de mudanças nos processos (schema extraído)
    from services.processos_kanban_historico_schema import criar_tabela_processos_kanban_historico
    criar_tabela_processos_kanban_historico(cursor)
    
    # ✅ Tabela de perfil do usuário (schema extraído)
    from services.usuarios_chat_schema import criar_tabela_usuarios_chat
    criar_tabela_usuarios_chat(cursor)
    
    # ✅ Tabela para categorias de processo aprendidas dinamicamente (schema extraído)
    from services.categorias_processo_schema import criar_tabela_categorias_processo
    criar_tabela_categorias_processo(cursor)
    
    # ✅ Tabela de conversas do chat (schema extraído)
    from services.conversas_chat_schema import criar_tabela_conversas_chat
    criar_tabela_conversas_chat(cursor)

    # ✅ NOVO (19/01/2026): Monitoramento de ocorrências + lead time por etapa (processos ativos)
    from services.ocorrencias_processos_schema import criar_tabela_ocorrencias_processos
    from services.processo_etapas_historico_schema import criar_tabela_processo_etapas_historico
    criar_tabela_ocorrencias_processos(cursor)
    criar_tabela_processo_etapas_historico(cursor)
    
    # ✅ NOVO (09/01/2026): drafts de email (sistema de versões)
    _criar_tabela_email_drafts(cursor)
    
    # ✅ NOVO: consultas analíticas salvas (use cases dinâmicos)
    _criar_tabela_consultas_salvas(cursor)
    
    # ✅ NOVO: regras/definições aprendidas + contexto persistente de sessão
    _criar_tabela_regras_aprendidas(cursor)
    _criar_tabela_contexto_sessao(cursor)
    
    # Índices para processos_kanban (schema extraído)
    from services.processos_kanban_indexes_schema import criar_indices_processos_kanban
    criar_indices_processos_kanban(cursor)
    
    # ✅ Vinculação de documentos + legislação
    _criar_tabela_processo_documentos(cursor)
    
    # ✅ NOVO (23/01/2026): Sugestões de vinculação bancária automática
    _criar_tabela_sugestoes_vinculacao(cursor)
    _criar_tabelas_legislacao(cursor)
    
    # ✅ Tabela para persistir estado do temporizador de monitoramento (schema extraído)
    from services.temporizador_monitoramento_schema import criar_tabela_temporizador_monitoramento
    criar_tabela_temporizador_monitoramento(cursor)
    
    # Índices para melhorar performance (schema extraído)
    from services.sqlite_indexes_schema import criar_indices_otimizacao_sqlite
    criar_indices_otimizacao_sqlite(cursor)
    
    conn.commit()
    conn.close()

def salvar_historico_pagamento(
    payment_id: str,
    tipo_pagamento: str,
    banco: str,
    ambiente: str,
    status: str,
    valor: float,
    codigo_barras: Optional[str] = None,
    beneficiario: Optional[str] = None,
    vencimento: Optional[str] = None,
    agencia_origem: Optional[str] = None,
    conta_origem: Optional[str] = None,
    saldo_disponivel_antes: Optional[float] = None,
    saldo_apos_pagamento: Optional[float] = None,
    workspace_id: Optional[str] = None,
    payment_date: Optional[str] = None,
    dados_completos: Optional[Dict[str, Any]] = None,
    observacoes: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_efetivacao: Optional[datetime] = None
) -> bool:
    """
    Salva ou atualiza histórico de pagamento.
    
    ✅ NOVO (13/01/2026): Grava em SQL Server (principal) e SQLite (cache).
    
    Args:
        payment_id: ID único do pagamento
        tipo_pagamento: 'BOLETO', 'PIX', 'TED', 'BARCODE'
        banco: 'SANTANDER', 'BANCO_DO_BRASIL'
        ambiente: 'SANDBOX', 'PRODUCAO'
        status: Status atual do pagamento
        valor: Valor do pagamento
        dados_completos: Dict com todos os dados retornados pela API (será convertido para JSON)
        data_inicio: Quando foi iniciado (None = agora)
        data_efetivacao: Quando foi efetivado (None = não efetivado ainda)
    
    Returns:
        True se salvou com sucesso (em pelo menos um banco), False caso contrário
    """
    # Wrapper fino: implementação foi extraída para reduzir o monolito do db_manager.py
    from services.historico_pagamentos_service import salvar_historico_pagamento as _impl

    return _impl(
        payment_id=payment_id,
        tipo_pagamento=tipo_pagamento,
        banco=banco,
        ambiente=ambiente,
        status=status,
        valor=valor,
        codigo_barras=codigo_barras,
        beneficiario=beneficiario,
        vencimento=vencimento,
        agencia_origem=agencia_origem,
        conta_origem=conta_origem,
        saldo_disponivel_antes=saldo_disponivel_antes,
        saldo_apos_pagamento=saldo_apos_pagamento,
        workspace_id=workspace_id,
        payment_date=payment_date,
        dados_completos=dados_completos,
        observacoes=observacoes,
        data_inicio=data_inicio,
        data_efetivacao=data_efetivacao,
    )

def salvar_duimp(numero: str, versao: str, payload: Dict[str, Any], ambiente: str = 'validacao', processo_referencia: Optional[str] = None) -> bool:
    """Salva uma DUIMP no banco local.
    
    Args:
        numero: Número da DUIMP
        versao: Versão da DUIMP
        payload: Payload completo da DUIMP
        ambiente: Ambiente (validacao ou producao)
        processo_referencia: Referência do processo de importação (ex: ALH.0001/25), opcional
                          Se fornecido, vincula automaticamente na tabela processo_documentos
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO duimps (numero, versao, payload_completo, ambiente, processo_referencia, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (numero, versao, json.dumps(payload, ensure_ascii=False), ambiente, processo_referencia, datetime.now()))
            
            conn.commit()
            
            # ✅ CRÍTICO: Vincular DUIMP ao processo na tabela processo_documentos se processo_referencia foi fornecido
            # Isso garante que a DUIMP apareça quando consultar documentos do processo
            # ⚠️ IMPORTANTE: Para DUIMPs de validação, não desvincular DUIMPs de produção existentes
            # Ambientes de validação e produção são independentes e podem coexistir
            if processo_referencia:
                try:
                    # ✅ Para DUIMPs de validação, verificar se já existe DUIMP de produção vinculada
                    # Se existir, não desvincular - permitir ambas coexistirem
                    if ambiente == 'validacao':
                        # Verificar se já existe DUIMP de produção vinculada ao processo
                        conn_check = get_db_connection()
                        cursor_check = conn_check.cursor()
                        cursor_check.execute('''
                            SELECT COUNT(*) FROM processo_documentos 
                            WHERE processo_referencia = ? 
                            AND tipo_documento = 'DUIMP'
                            AND numero_documento IN (
                                SELECT numero FROM duimps 
                                WHERE processo_referencia = ? 
                                AND ambiente = 'producao'
                            )
                        ''', (processo_referencia, processo_referencia))
                        tem_duimp_producao = cursor_check.fetchone()[0] > 0
                        conn_check.close()
                        
                        if tem_duimp_producao:
                            logging.info(f'⚠️ DUIMP de validação {numero} v{versao} será vinculada ao processo {processo_referencia}, mas mantendo DUIMP de produção existente')
                    
                    # Vincular DUIMP (não desvincula DUIMPs existentes - INSERT OR REPLACE apenas substitui mesmo tipo+número)
                    vincular_documento_processo(processo_referencia, 'DUIMP', numero)
                    logging.info(f'✅ DUIMP {numero} v{versao} (ambiente: {ambiente}) vinculada ao processo {processo_referencia} na tabela processo_documentos')
                except Exception as e:
                    logging.warning(f'⚠️ Erro ao vincular DUIMP {numero} ao processo {processo_referencia}: {e}')
                    # Não retornar False se falhar o vínculo - DUIMP já foi salva
            
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))  # Backoff exponencial
                continue
            logging.error(f"Erro ao salvar DUIMP (tentativa {tentativa + 1}): {e}")
            return False
        except Exception as e:
            logging.error(f"Erro ao salvar DUIMP: {e}")
            return False
    return False

def listar_duimps(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Lista DUIMPs do banco local.
    
    ✅ CORREÇÃO: Mostra apenas a versão mais recente de cada DUIMP para evitar duplicatas.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # ✅ Usar GROUP BY para mostrar apenas a versão mais recente de cada número
        # ✅ processo_referencia já está na tabela duimps, não precisa JOIN
        if status:
            cursor.execute('''
                SELECT d.id, d.numero, d.versao, d.status, d.ambiente, d.processo_referencia, d.criado_em, d.atualizado_em
                FROM duimps d
                INNER JOIN (
                    SELECT numero, MAX(CAST(versao AS INTEGER)) as max_versao
                    FROM duimps
                    WHERE status = ?
                    GROUP BY numero
                ) t ON d.numero = t.numero AND CAST(d.versao AS INTEGER) = t.max_versao
                WHERE d.status = ?
                ORDER BY d.atualizado_em DESC
                LIMIT ?
            ''', (status, status, limit))
        else:
            cursor.execute('''
                SELECT d.id, d.numero, d.versao, d.status, d.ambiente, d.processo_referencia, d.criado_em, d.atualizado_em
                FROM duimps d
                INNER JOIN (
                    SELECT numero, MAX(CAST(versao AS INTEGER)) as max_versao
                    FROM duimps
                    GROUP BY numero
                ) t ON d.numero = t.numero AND CAST(d.versao AS INTEGER) = t.max_versao
                ORDER BY d.atualizado_em DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
        conn.close()
        return result
    except Exception as e:
        print(f"Erro ao listar DUIMPs: {e}")
        # ✅ Fallback: se houver erro com CAST, usar método simples sem GROUP BY
        try:
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT id, numero, versao, status, ambiente, criado_em, atualizado_em
                    FROM duimps
                    WHERE status = ?
                    ORDER BY atualizado_em DESC
                    LIMIT ?
                ''', (status, limit))
            else:
                cursor.execute('''
                    SELECT id, numero, versao, status, ambiente, criado_em, atualizado_em
                    FROM duimps
                    ORDER BY atualizado_em DESC
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            conn.close()
            return result
        except Exception as e2:
            print(f"Erro ao listar DUIMPs (fallback): {e2}")
            return []

# =============================================================================
# SHIPSGO HELPERS
# =============================================================================
def shipsgo_upsert_tracking(
    processo_referencia: str,
    eta_iso: Optional[str],
    porto_codigo: Optional[str],
    porto_nome: Optional[str],
    payload_raw: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
    navio: Optional[str] = None,
) -> bool:
    """Insere/atualiza dados de ETA/porto/status para um processo."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ✅ Adicionar coluna status se não existir (migração)
        try:
            cursor.execute('ALTER TABLE shipsgo_tracking ADD COLUMN status TEXT')
        except sqlite3.OperationalError:
            pass  # Coluna já existe

        # ✅ Adicionar coluna navio se não existir (migração)
        try:
            cursor.execute('ALTER TABLE shipsgo_tracking ADD COLUMN navio TEXT')
        except sqlite3.OperationalError:
            pass  # Coluna já existe
        
        payload_str = json.dumps(payload_raw, ensure_ascii=False) if isinstance(payload_raw, dict) else (payload_raw or None)
        cursor.execute('''
            INSERT INTO shipsgo_tracking (processo_referencia, eta_iso, porto_codigo, porto_nome, navio, status, payload_raw, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(processo_referencia) DO UPDATE SET
                eta_iso=excluded.eta_iso,
                porto_codigo=excluded.porto_codigo,
                porto_nome=excluded.porto_nome,
                navio=excluded.navio,
                status=excluded.status,
                payload_raw=excluded.payload_raw,
                atualizado_em=CURRENT_TIMESTAMP
        ''', (processo_referencia, eta_iso, porto_codigo, porto_nome, navio, status, payload_str))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f'Erro ao upsert shipsgo_tracking para {processo_referencia}: {e}')
        return False

def shipsgo_get_tracking_map(processos_refs: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Retorna mapa processo_ref -> dados ETA/porto/status do registro MAIS RECENTE do histórico.
    
    ⚠️ CRÍTICO: Esta função retorna o ETA do ShipsGo (Data POD) — fonte da verdade —
    que é mais confiável do que o ETA vindo do Kanban.
    """
    if not processos_refs:
        return {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Montar query com IN - ✅ CRÍTICO: Pegar o registro mais recente de cada processo (histórico)
        # Usar ROW_NUMBER() ou subquery para pegar apenas o mais recente por processo
        params = ','.join('?' for _ in processos_refs)
        
        # ✅ TENTAR ROW_NUMBER() primeiro (SQLite 3.25+)
        try:
            cursor.execute(f'''
                SELECT processo_referencia, eta_iso, porto_codigo, porto_nome, navio, status
                FROM (
                    SELECT processo_referencia, eta_iso, porto_codigo, porto_nome, navio, status,
                           ROW_NUMBER() OVER (PARTITION BY processo_referencia ORDER BY atualizado_em DESC) as rn
                    FROM shipsgo_tracking
                    WHERE processo_referencia IN ({params})
                ) ranked
                WHERE rn = 1
            ''', processos_refs)
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # ✅ FALLBACK: Para SQLite antigo sem ROW_NUMBER(), usar subquery
            logging.warning('⚠️ SQLite não suporta ROW_NUMBER(), usando fallback com subquery')
            cursor.execute(f'''
                SELECT processo_referencia, eta_iso, porto_codigo, porto_nome, navio, status
                FROM shipsgo_tracking s1
                WHERE s1.processo_referencia IN ({params})
                AND s1.atualizado_em = (
                    SELECT MAX(s2.atualizado_em)
                    FROM shipsgo_tracking s2
                    WHERE s2.processo_referencia = s1.processo_referencia
                )
            ''', processos_refs)
            rows = cursor.fetchall()
        
        conn.close()
        mapa: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            proc = row[0]
            # ✅ CRÍTICO: Usar 'eta_iso' como chave (não 'shipsgo_eta') para compatibilidade
            # ✅ Este é o ETA mais recente do histórico do ShipsGo (Data POD)
            if row[1]:  # Só adicionar se tiver eta_iso
                mapa[proc] = {
                    'eta_iso': row[1],  # ✅ ETA do ShipsGo (Data POD) - mais recente do histórico
                    'porto_codigo': row[2],
                    'porto_nome': row[3],
                    'navio': row[4],  # Navio do ShipsGo (quando disponível)
                    'status': row[5],  # Status do ShipsGo
                }
                logging.info(f'✅✅✅ shipsgo_get_tracking_map: Processo {proc} - ETA ShipsGo encontrado: {row[1]} (Data POD)')
            else:
                logging.warning(f'⚠️ shipsgo_get_tracking_map: Processo {proc} encontrado na tabela mas SEM eta_iso (NULL)')
        
        processos_sem_dados = [p for p in processos_refs if p not in mapa]
        if processos_sem_dados:
            logging.warning(f'⚠️⚠️⚠️ shipsgo_get_tracking_map: {len(processos_sem_dados)} processo(s) SEM dados no ShipsGo: {processos_sem_dados}')
        
        logging.info(f'✅ shipsgo_get_tracking_map: Retornando {len(mapa)} processos com dados do ShipsGo (mais recente do histórico) de {len(processos_refs)} solicitados')
        return mapa
    except Exception as e:
        logging.error(f'Erro ao buscar shipsgo_tracking: {e}')
        # ✅ Fallback: Tentar query simples se ROW_NUMBER não funcionar (SQLite antigo)
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            params = ','.join('?' for _ in processos_refs)
            # Para cada processo, pegar o mais recente
            mapa: Dict[str, Dict[str, Any]] = {}
            for proc_ref in processos_refs:
                cursor.execute('''
                    SELECT eta_iso, porto_codigo, porto_nome, navio, status
                    FROM shipsgo_tracking
                    WHERE processo_referencia = ?
                    ORDER BY atualizado_em DESC
                    LIMIT 1
                ''', (proc_ref,))
                row = cursor.fetchone()
                if row:
                    mapa[proc_ref] = {
                        'eta_iso': row[0],
                        'porto_codigo': row[1],
                        'porto_nome': row[2],
                        'navio': row[3],
                        'status': row[4],
                    }
            conn.close()
            return mapa
        except Exception as e2:
            logging.error(f'Erro ao buscar shipsgo_tracking (fallback): {e2}')
            return {}

def listar_processos_por_eta(filtro_data: str = 'semana', data_especifica: Optional[str] = None, 
                             categoria: Optional[str] = None, limit: int = 200, incluir_passado: bool = False) -> List[Dict[str, Any]]:
    """Lista processos filtrados por ETA (Estimated Time of Arrival) do Kanban.
    
    Args:
        filtro_data: Filtro de data relativa ('hoje', 'amanha', 'amanhã', 'semana', 'proxima_semana', 'mes', 'proximo_mes', 'futuro', 'todos_futuros', 'data_especifica')
            - 'mes': Este mês (ETA >= hoje até o último dia do mês atual)
            - 'proximo_mes': Mês que vem (do primeiro dia do próximo mês até o último dia do próximo mês)
            - 'futuro' ou 'todos_futuros': TODOS os processos com ETA >= hoje, SEM limite de mês/ano (usado para perguntas genéricas como "quais processos estão chegando?")
        data_especifica: Data específica no formato DD/MM/AAAA ou AAAA-MM-DD (usado quando filtro_data='data_especifica')
        categoria: Categoria do processo (ex: 'ALH', 'VDM', 'MV5'). Opcional.
        limit: Limite de resultados
    
    Returns:
        Lista de processos com dados completos incluindo ShipsGo
    """
    try:
        from datetime import datetime, timedelta
        import re
        
        # Calcular intervalo de datas baseado no filtro
        hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # ✅ NOVO: Variáveis para intervalos de semana/mês (necessárias para filtro Python quando incluir_passado=True)
        # ✅ CORREÇÃO: Semana no Brasil começa no DOMINGO (ABNT)
        # Sempre calcular para garantir disponibilidade no filtro Python
        dia_semana_hoje = hoje.weekday()  # 0=segunda, 1=terça, ..., 6=domingo (padrão Python)
        # ✅ Converter para padrão brasileiro: 0=domingo, 1=segunda, ..., 6=sábado
        dia_semana_br = (dia_semana_hoje + 1) % 7
        dias_ate_domingo = dia_semana_br  # Quantos dias atrás está o domingo
        domingo_desta_semana = hoje - timedelta(days=dias_ate_domingo)
        sabado_desta_semana = domingo_desta_semana + timedelta(days=6)  # Sábado = domingo + 6 dias
        # Manter compatibilidade com código antigo (não usar mais)
        segunda_desta_semana = domingo_desta_semana + timedelta(days=1)  # Segunda = domingo + 1
        domingo_desta_semana_old = sabado_desta_semana  # Para compatibilidade (não usar)
        
        if filtro_data == 'hoje':
            data_inicio = hoje
            data_fim = hoje + timedelta(days=1)
        elif filtro_data in ('amanha', 'amanhã'):
            data_inicio = hoje + timedelta(days=1)
            data_fim = hoje + timedelta(days=2)
        elif filtro_data == 'semana':
            # ✅ CORREÇÃO CRÍTICA: Semana no Brasil começa no DOMINGO e termina no SÁBADO (ABNT)
            # - Semana = Domingo até Sábado (exemplo: 21/12 domingo - termina 27/12 sábado)
            # - "esta semana" = de domingo desta semana até sábado desta semana
            # - FUTURO: ETA >= hoje (domingo) até sábado desta semana (processos que vão chegar)
            # - PASSADO (incluir_passado=True): Domingo até sábado (processos que chegaram, incluindo passado)
            
            if incluir_passado:
                # ✅ Para passado: buscar de domingo até sábado (incluindo passado)
                # Intervalo: [domingo, sábado+1) para incluir o sábado inteiro (até 23:59:59 do sábado)
                data_inicio = domingo_desta_semana  # Domingo desta semana
                data_fim = sabado_desta_semana + timedelta(days=1)  # +1 para incluir o sábado inteiro (até 23:59:59 do sábado)
                logging.info(f'🔍 listar_processos_por_eta: Filtro "esta semana" (PASSADO) = ETA de {data_inicio.date()} até {sabado_desta_semana.date()} (hoje={hoje.date()}, dia_semana={dia_semana_br})')
            else:
                # ✅ CORREÇÃO: "esta semana" = de domingo desta semana até sábado desta semana
                # Semana termina no sábado, não no próximo domingo
                # Mas ainda vamos verificar se o processo já chegou (dataDestinoFinal) para excluir
                data_inicio = domingo_desta_semana  # Domingo desta semana (inclui passado da semana)
                data_fim = sabado_desta_semana + timedelta(days=1)  # +1 para incluir o sábado inteiro (até 23:59:59 do sábado)
                
                logging.info(f'🔍 listar_processos_por_eta: Filtro "esta semana" (Brasil) = ETA de {data_inicio.date()} até {sabado_desta_semana.date()} (hoje={hoje.date()}, dia_semana={dia_semana_br})')
                logging.info(f'💡 Nota: Processos que já chegaram (dataDestinoFinal/dataHoraChegadaEfetiva) serão excluídos automaticamente')
        elif filtro_data == 'proxima_semana':
            # ✅ CORREÇÃO: "semana que vem" = da próxima segunda-feira até o próximo domingo
            # Se estivermos ainda dentro da semana atual, a "semana que vem" começa na próxima segunda
            # isoweekday(): 1=segunda, 2=terça, ..., 7=domingo
            dia_semana = hoje.isoweekday()  # 1=segunda, 7=domingo
            dias_ate_proxima_segunda = 8 - dia_semana  # Quantos dias até a próxima segunda
            proxima_segunda = hoje + timedelta(days=dias_ate_proxima_segunda)
            proximo_domingo = proxima_segunda + timedelta(days=6)
            # Semana que vem sempre começa na próxima segunda (não em hoje)
            data_inicio = proxima_segunda
            data_fim = proximo_domingo + timedelta(days=1)  # +1 para incluir o domingo inteiro
            logging.info(f'🔍 listar_processos_por_eta: Filtro "semana que vem" = {data_inicio.date()} até {proximo_domingo.date()}')
        elif filtro_data == 'mes':
            # ✅ CORREÇÃO: "este mês" = ETA >= hoje até o último dia do mês atual
            # Exemplo: se hoje é 20/11/2025, retorna ETA >= 20/11/2025 até 30/11/2025
            # Não mostra processos que já chegaram no passado (ETA < hoje)
            from calendar import monthrange
            ano_atual = hoje.year
            mes_atual = hoje.month
            ultimo_dia_mes = monthrange(ano_atual, mes_atual)[1]  # Último dia do mês
            # ✅ SEMPRE começar de hoje (ETA >= hoje), não do primeiro dia do mês
            data_inicio = hoje  # ETA >= hoje
            data_fim = datetime(ano_atual, mes_atual, ultimo_dia_mes) + timedelta(days=1)  # +1 para incluir o último dia inteiro
            logging.info(f'🔍 listar_processos_por_eta: Filtro "este mês" = ETA >= {data_inicio.date()} até {data_fim.date() - timedelta(days=1)}')
        elif filtro_data == 'proximo_mes':
            # ✅ CORREÇÃO: "mês que vem" = do primeiro dia do próximo mês até o último dia do próximo mês
            # Exemplo: se hoje é 15/11/2025, retorna 01/12/2025 até 31/12/2025
            from calendar import monthrange
            ano_atual = hoje.year
            mes_atual = hoje.month
            # Calcular próximo mês e ano
            if mes_atual == 12:
                proximo_mes = 1
                proximo_ano = ano_atual + 1
            else:
                proximo_mes = mes_atual + 1
                proximo_ano = ano_atual
            primeiro_dia_proximo_mes = datetime(proximo_ano, proximo_mes, 1)
            ultimo_dia_proximo_mes = monthrange(proximo_ano, proximo_mes)[1]  # Último dia do próximo mês
            data_inicio = primeiro_dia_proximo_mes
            data_fim = datetime(proximo_ano, proximo_mes, ultimo_dia_proximo_mes) + timedelta(days=1)  # +1 para incluir o último dia inteiro
            logging.info(f'🔍 listar_processos_por_eta: Filtro "mês que vem" = {data_inicio.date()} até {data_fim.date() - timedelta(days=1)}')
        elif filtro_data == 'data_especifica' and data_especifica:
            # Tentar parsear data em diferentes formatos
            try:
                # Formato DD/MM/AAAA (aceita também DD/MM/AA assumindo 20AA)
                if '/' in data_especifica:
                    partes = data_especifica.split('/')
                    if len(partes) == 3:
                        ano_in = str(partes[2]).strip()
                        # ✅ Suporte a ano com 2 dígitos (ex: 23/01/25 -> 2025)
                        if len(ano_in) == 2 and ano_in.isdigit():
                            ano = 2000 + int(ano_in)
                        else:
                            ano = int(ano_in)
                            if 0 <= ano < 100:
                                ano = 2000 + ano
                        data_inicio = datetime(ano, int(partes[1]), int(partes[0]))
                        # ✅ NOVO: Se a data é o primeiro dia do mês (01/MM/AAAA), buscar todo o mês
                        # Isso permite buscar por mês inteiro quando o usuário menciona apenas o mês (ex: "dezembro")
                        if int(partes[0]) == 1:
                            # É o primeiro dia do mês - buscar todo o mês
                            from calendar import monthrange
                            ultimo_dia_mes = monthrange(int(partes[2]), int(partes[1]))[1]
                            data_fim = datetime(int(partes[2]), int(partes[1]), ultimo_dia_mes) + timedelta(days=1)
                            logging.info(f'🔍 listar_processos_por_eta: Data específica é primeiro dia do mês - buscando mês inteiro: {data_inicio.date()} até {data_fim.date() - timedelta(days=1)}')
                        else:
                            # Data específica normal - apenas um dia
                            data_fim = data_inicio + timedelta(days=1)
                    else:
                        logging.warning(f'Formato de data inválido: {data_especifica}')
                        return []
                # Formato AAAA-MM-DD
                elif '-' in data_especifica:
                    data_inicio = datetime.fromisoformat(data_especifica)
                    # ✅ NOVO: Se a data é o primeiro dia do mês, buscar todo o mês
                    if data_inicio.day == 1:
                        from calendar import monthrange
                        ultimo_dia_mes = monthrange(data_inicio.year, data_inicio.month)[1]
                        data_fim = datetime(data_inicio.year, data_inicio.month, ultimo_dia_mes) + timedelta(days=1)
                        logging.info(f'🔍 listar_processos_por_eta: Data específica é primeiro dia do mês - buscando mês inteiro: {data_inicio.date()} até {data_fim.date() - timedelta(days=1)}')
                    else:
                        # Data específica normal - apenas um dia
                        data_fim = data_inicio + timedelta(days=1)
                else:
                    logging.warning(f'Formato de data inválido: {data_especifica}')
                    return []
            except Exception as e:
                logging.error(f'Erro ao parsear data específica {data_especifica}: {e}')
                return []
        elif filtro_data == 'futuro' or filtro_data == 'todos_futuros':
            # ✅ NOVO: "futuro" ou "todos_futuros"
            # - incluir_passado=False: ETA >= hoje, SEM limite de data final (usado para perguntas "vão chegar")
            # - incluir_passado=True: janela ampliada para incluir chegados (ETA <= hoje) até 1 ano atrás
            if incluir_passado:
                data_inicio = hoje - timedelta(days=365)  # buscar passado de até 1 ano
            else:
                data_inicio = hoje  # ETA >= hoje
            data_fim = datetime(hoje.year + 10, 12, 31)  # 31 de dezembro de 10 anos no futuro
            logging.info(f'🔍 listar_processos_por_eta: Filtro "futuro" (incluir_passado={incluir_passado}) = ETA >= {data_inicio.date()} até {data_fim.date()}')
        else:
            # Padrão: semana
            data_inicio = hoje
            data_fim = hoje + timedelta(days=7)
        
        # Buscar processos com ETA no intervalo
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        # Query para buscar processos com ETA no intervalo
        # SQLite compara strings ISO datetime diretamente
        # ✅ CORREÇÃO: Garantir formato ISO correto (sem timezone para comparação)
        # O eta_iso no banco pode estar em formato ISO sem timezone ou com timezone
        # ✅ IMPORTANTE: Garantir que data_inicio seja >= hoje APENAS se não for passado
        # Exceção: filtro "semana" pode começar de domingo (passado) para incluir toda a semana
        # Mas ainda vamos verificar se o processo já chegou (dataDestinoFinal) para excluir
        if filtro_data == 'semana' and data_inicio < hoje:
            # ✅ Permitir passado da semana, mas processos que já chegaram serão excluídos pela verificação de chegada
            logging.info(f'✅ listar_processos_por_eta: Filtro "semana" - data_inicio ({data_inicio.date()}) < hoje ({hoje.date()}) - OK (domingo desta semana). Processos que já chegaram serão excluídos.')
        elif not incluir_passado and data_inicio < hoje:
            logging.warning(f'⚠️ listar_processos_por_eta: data_inicio ({data_inicio.date()}) < hoje ({hoje.date()}), ajustando para hoje')
            data_inicio = hoje
        elif incluir_passado and data_inicio < hoje:
            logging.info(f'✅ listar_processos_por_eta: data_inicio ({data_inicio.date()}) < hoje ({hoje.date()}) - OK para buscar passado (incluir_passado=True)')
        
        data_inicio_iso = data_inicio.isoformat()
        data_fim_iso = data_fim.isoformat()
        
        logging.info(f'🔍 listar_processos_por_eta: Buscando ETA >= {data_inicio_iso} e < {data_fim_iso} (hoje={hoje.isoformat()}, filtro={filtro_data}, categoria={categoria})')
        
        # ✅ MUDANÇA: Buscar ETA da tabela processos_kanban (do JSON do Kanban)
        # Não precisa mais do ShipsGo para processos ativos!
        query = '''
            SELECT DISTINCT pk.processo_referencia, pk.eta_iso, pk.porto_codigo, pk.porto_nome, pk.nome_navio, pk.status_shipsgo
            FROM processos_kanban pk
            WHERE pk.eta_iso IS NOT NULL
            AND pk.eta_iso != ''
            AND SUBSTR(pk.eta_iso, 1, 19) >= ?
            AND SUBSTR(pk.eta_iso, 1, 19) < ?
        '''
        # Usar apenas os primeiros 19 caracteres (YYYY-MM-DDTHH:MM:SS) para comparação, ignorando timezone
        params = [data_inicio_iso[:19], data_fim_iso[:19]]
        
        # Filtrar por categoria se fornecido
        if categoria:
            # Extrair prefixo da categoria do processo_referencia
            query += ' AND pk.processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        query += ' ORDER BY pk.eta_iso ASC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        logging.info(f'🔍 listar_processos_por_eta: Encontrados {len(rows)} processos com ETA no intervalo')
        
        if not rows:
            conn.close()
            logging.info(f'🔍 listar_processos_por_eta: Nenhum processo encontrado com ETA entre {data_inicio_iso} e {data_fim_iso}')
            return []
        
        # ✅ CORREÇÃO CRÍTICA: Filtrar novamente no Python para garantir que ETA está no intervalo correto
        # A comparação SQL pode falhar com timezones ou formatos diferentes
        # IMPORTANTE: O ETA pode estar em diferentes formatos (ISO, DD/MM/AAAA, etc)
        # - Se incluir_passado=False: ETA >= hoje (futuro)
        # - Se incluir_passado=True: ETA <= hoje E no intervalo (passado)
        processos_com_eta = []
        hoje_date_only = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if incluir_passado:
            logging.info(f'🔍 listar_processos_por_eta: Filtrando {len(rows)} resultados com ETA <= hoje ({hoje_date_only.date()}) no intervalo {data_inicio.date()} até {data_fim.date() - timedelta(days=1)}')
        else:
            logging.info(f'🔍 listar_processos_por_eta: Filtrando {len(rows)} resultados com ETA >= hoje ({hoje_date_only.date()})')
        
        # ✅ Criar mapa de ETA/porto/navio/status da query para usar depois
        eta_porto_navio_map = {}
        for row in rows:
            processo_ref = row['processo_referencia']
            eta_iso = row['eta_iso']
            # ✅ CORREÇÃO: sqlite3.Row não tem .get(), usar indexação direta com try/except
            porto_codigo = row['porto_codigo'] if 'porto_codigo' in row.keys() else None
            porto_nome = row['porto_nome'] if 'porto_nome' in row.keys() else None
            nome_navio = row['nome_navio'] if 'nome_navio' in row.keys() else None
            status_shipsgo = row['status_shipsgo'] if 'status_shipsgo' in row.keys() else None
            
            eta_porto_navio_map[processo_ref] = {
                'eta_iso': eta_iso,
                'porto_codigo': porto_codigo,
                'porto_nome': porto_nome,
                'nome_navio': nome_navio,
                'status_shipsgo': status_shipsgo
            }
            
            # ✅ VALIDAÇÃO ADICIONAL: Parsear ETA e verificar se é >= hoje
            # Tentar diferentes formatos de data
            eta_date = None
            
            try:
                # ✅ CORREÇÃO CRÍTICA: Remover timezone antes de parsear para evitar erro de comparação
                # O ETA pode vir com timezone (ex: "2025-11-22T12:00:00-03:00") ou sem (ex: "2025-11-22T12:00:00")
                # Precisamos remover o timezone para comparar com hoje (timezone-naive)
                
                # Remover microsegundos primeiro (antes do timezone)
                eta_str_no_ms = eta_iso.split('.')[0]
                
                # Remover timezone (pode ser Z, +00:00, -00:00, -03:00, +03:00, etc)
                # Padrão: remover tudo depois do último : ou Z no final
                import re
                # Remover timezone no formato -03:00 ou +03:00 ou Z
                eta_str_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', eta_str_no_ms)  # Remove -03:00 ou +03:00
                eta_str_clean = eta_str_clean.replace('Z', '')  # Remove Z
                eta_str_clean = eta_str_clean.strip()
                
                # Tentar formato ISO primeiro (YYYY-MM-DD ou YYYY-MM-DDTHH:MM:SS)
                if 'T' in eta_str_clean:
                    eta_date = datetime.fromisoformat(eta_str_clean)
                elif len(eta_str_clean) == 10 and '-' in eta_str_clean:  # Apenas data ISO: YYYY-MM-DD
                    eta_date = datetime.fromisoformat(eta_str_clean + 'T00:00:00')
                elif len(eta_str_clean) == 10 and '/' in eta_str_clean:  # Formato brasileiro: DD/MM/AAAA
                    # Parsear formato brasileiro DD/MM/AAAA
                    partes = eta_str_clean.split('/')
                    if len(partes) == 3:
                        dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                        eta_date = datetime(ano, mes, dia, 0, 0, 0)
                    else:
                        raise ValueError(f'Formato de data brasileiro inválido: {eta_str_clean}')
                else:
                    # Tentar parsear diretamente como ISO
                    eta_date = datetime.fromisoformat(eta_str_clean)
                
                # ✅ GARANTIR: eta_date é timezone-naive (sem timezone) para comparar com hoje
                if eta_date.tzinfo is not None:
                    # Se tiver timezone, remover (converter para naive)
                    eta_date = eta_date.replace(tzinfo=None)
                
                # Comparar apenas a data (ignorar hora) com hoje
                eta_date_only = eta_date.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # ✅ FILTRO BASEADO EM incluir_passado
                if incluir_passado:
                    # ✅ CORREÇÃO CRÍTICA: Para "esta semana" (incluir_passado=True + filtro_data='semana'),
                    # incluir TODOS os processos com ETA dentro do intervalo da semana (domingo até sábado),
                    # independente de terem chegado ou não. Isso permite mostrar tanto processos que já chegaram
                    # quanto os que vão chegar nesta semana.
                    if filtro_data == 'semana' and domingo_desta_semana and sabado_desta_semana:
                        # Para "esta semana": aceitar TODOS os processos com ETA dentro do intervalo
                        if domingo_desta_semana.date() <= eta_date_only.date() <= sabado_desta_semana.date():
                            processos_com_eta.append((processo_ref, eta_iso))
                            status_chegada = "já chegou" if eta_date_only <= hoje_date_only else "vai chegar"
                            logging.info(f'✅ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} ACEITO ({status_chegada}, no intervalo desta semana - dom {domingo_desta_semana.date()} até sáb {sabado_desta_semana.date()})')
                        else:
                            logging.warning(f'❌ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} REJEITADO (fora do intervalo desta semana - dom {domingo_desta_semana.date()} até sáb {sabado_desta_semana.date()})')
                    else:
                        # Para outros filtros com incluir_passado: incluir apenas processos que JÁ chegaram (ETA <= hoje) E estão no intervalo
                        if domingo_desta_semana and sabado_desta_semana:
                            if domingo_desta_semana.date() <= eta_date_only.date() <= sabado_desta_semana.date():
                                if eta_date_only <= hoje_date_only:
                                    processos_com_eta.append((processo_ref, eta_iso))
                                    logging.info(f'✅ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} ACEITO (passado, no intervalo desta semana - dom {domingo_desta_semana.date()} até sáb {sabado_desta_semana.date()})')
                                else:
                                    logging.warning(f'❌ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} REJEITADO (passado mas ETA > hoje {hoje_date_only.date()})')
                            else:
                                logging.warning(f'❌ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} REJEITADO (fora do intervalo desta semana - dom {domingo_desta_semana.date()} até sáb {sabado_desta_semana.date()})')
                        else:
                            # Se não tem intervalo definido, usar apenas verificação ETA <= hoje
                            if eta_date_only <= hoje_date_only:
                                processos_com_eta.append((processo_ref, eta_iso))
                                logging.info(f'✅ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} ACEITO (passado, ETA <= hoje)')
                            else:
                                logging.warning(f'❌ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} REJEITADO (ETA > hoje {hoje_date_only.date()})')
                else:
                    # ✅ CORREÇÃO CRÍTICA: Para futuro, verificar BOTH:
                    # 1. ETA >= hoje (não incluir passado) - EXCETO para filtro "semana"
                    # 2. ETA dentro do intervalo calculado (data_inicio até data_fim)
                    # Isso garante que "semana que vem" realmente retorne apenas processos da próxima semana
                    # Mas "esta semana" pode incluir passado da semana (domingo a sábado)
                    eta_dentro_intervalo = data_inicio.date() <= eta_date_only.date() < data_fim.date()
                    
                    # ✅ CORREÇÃO: Filtro "semana" pode incluir ETA < hoje (passado da semana)
                    # Processos que já chegaram serão excluídos pela verificação de chegada depois
                    if filtro_data == 'semana':
                        # Para "semana", aceitar qualquer ETA dentro do intervalo (domingo a sábado)
                        if eta_dentro_intervalo:
                            processos_com_eta.append((processo_ref, eta_iso))
                            logging.info(f'✅ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} ACEITO (dentro do intervalo da semana {data_inicio.date()} até {data_fim.date() - timedelta(days=1)})')
                        else:
                            logging.warning(f'❌ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} REJEITADO (fora do intervalo da semana {data_inicio.date()} até {data_fim.date() - timedelta(days=1)})')
                    else:
                        # Para outros filtros, exigir ETA >= hoje (futuro)
                        eta_futuro = eta_date_only >= hoje_date_only
                        if eta_dentro_intervalo and eta_futuro:
                            processos_com_eta.append((processo_ref, eta_iso))
                            logging.info(f'✅ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} ACEITO (futuro, dentro do intervalo {data_inicio.date()} até {data_fim.date() - timedelta(days=1)})')
                        else:
                            if not eta_dentro_intervalo:
                                logging.warning(f'❌ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} REJEITADO (fora do intervalo {data_inicio.date()} até {data_fim.date() - timedelta(days=1)})')
                            if not eta_futuro:
                                logging.warning(f'❌ listar_processos_por_eta: Processo {processo_ref} com ETA {eta_iso} -> {eta_date_only.date()} REJEITADO (ETA < hoje {hoje_date_only.date()})')
            except Exception as e:
                # Se não conseguir parsear, REJEITAR para garantir que não incluímos processos inválidos
                logging.error(f'❌ listar_processos_por_eta: Erro ao parsear ETA "{eta_iso}" do processo {processo_ref}: {e}. REJEITANDO processo.')
                # NÃO incluir processos com ETA inválido para garantir segurança
                continue
        
        # ✅ LOG FINAL: Mostrar resumo do filtro
        filtro_tipo = "passado (ETA <= hoje)" if incluir_passado else "futuro (ETA >= hoje)"
        logging.info(f'🔍 listar_processos_por_eta: Resultado final: {len(processos_com_eta)} processos com ETA {filtro_tipo} de {len(rows)} encontrados na query SQL')
        
        if not processos_com_eta:
            conn.close()
            filtro_msg = "passado (ETA <= hoje)" if incluir_passado else "futuro (ETA >= hoje)"
            logging.info(f'🔍 listar_processos_por_eta: Nenhum processo com ETA {filtro_msg} encontrado após filtro adicional')
            return []
        
        filtro_tipo = "passado (ETA <= hoje)" if incluir_passado else "futuro (ETA >= hoje)"
        logging.info(f'🔍 listar_processos_por_eta: Após filtro adicional ({filtro_tipo}): {len(processos_com_eta)} processos válidos')
        
        conn.close()
        
        resultados = []
        
        # ✅ NOVO: Buscar ETA do SQL Server (TRANSPORTE) + ShipsGo tracking (SQLite)
        # Regra de fonte da verdade (ver docs/prompt): ShipsGo oficial > derivados.
        # Prioridade para ETA/POD: ShipsGo (shipsgo_tracking) → SQL Server (replica/cache) → Kanban (processos_kanban)
        processos_refs_list = [proc_ref for proc_ref, _ in processos_com_eta]
        eta_sql_server_map = {}
        shipsgo_map = {}
        
        if processos_refs_list:
            # 0) ShipsGo tracking (SQLite) - fonte da verdade para ETA/POD quando disponível
            try:
                shipsgo_map = shipsgo_get_tracking_map(processos_refs_list)
            except Exception:
                shipsgo_map = {}

            try:
                from utils.sql_server_adapter import get_sql_adapter
                sql_adapter = get_sql_adapter()
                if sql_adapter:
                    # Buscar ETA do SQL Server (TRANSPORTE) para todos os processos
                    # A tabela TRANSPORTE tem histórico (múltiplos registros por processo)
                    # Precisamos pegar o mais recente ou o evento DISC/ARRV do porto de destino
                    processos_escaped = [proc_ref.replace("'", "''") for proc_ref in processos_refs_list]
                    processos_list = "', '".join(processos_escaped)
                    
                    # ✅ Query para buscar ETA do SQL Server (TRANSPORTE)
                    # Prioridade: DISC (POD) > destino_data_chegada > ARRV > mais recente
                    # ✅ CRÍTICO: Usar ROW_NUMBER() para pegar apenas o registro mais prioritário de cada processo
                    query_sql_server = f'''
                        SELECT 
                            numero_processo,
                            destino_data_chegada,
                            atual_evento,
                            atual_data_evento,
                            destino_nome,
                            navio,
                            status
                        FROM (
                            SELECT 
                                t.numero_processo,
                                t2.destino_data_chegada,
                                t2.atual_evento,
                                t2.atual_data_evento,
                                t2.destino_nome,
                                t2.navio,
                                t2.status,
                                ROW_NUMBER() OVER (
                                    PARTITION BY t.numero_processo 
                                    ORDER BY 
                                        CASE 
                                            WHEN t2.atual_evento = 'DISC' THEN 1
                                            WHEN t2.destino_data_chegada IS NOT NULL THEN 2
                                            WHEN t2.atual_evento = 'ARRV' THEN 3
                                            ELSE 4
                                        END,
                                        t2.id_movimento DESC,
                                        t2.criado_em DESC
                                ) as rn
                            FROM make.dbo.PROCESSO_IMPORTACAO t WITH (NOLOCK)
                            LEFT JOIN make.dbo.TRANSPORTE t2 WITH (NOLOCK)
                                ON t2.id_processo_importacao = t.id_processo_importacao
                            WHERE t.numero_processo IN ('{processos_list}')
                            AND t2.destino_data_chegada IS NOT NULL
                        ) ranked
                        WHERE rn = 1
                    '''
                    
                    result_sql = sql_adapter.execute_query(query_sql_server, 'Make', None, notificar_erro=False)
                    if result_sql.get('success') and result_sql.get('data'):
                        # Processar resultados - pegar o primeiro (mais prioritário) de cada processo
                        for row in result_sql['data']:
                            proc_ref = row.get('numero_processo', '').strip()
                            if proc_ref and proc_ref not in eta_sql_server_map:
                                destino_data_chegada = row.get('destino_data_chegada')
                                atual_evento = row.get('atual_evento', '')
                                atual_data_evento = row.get('atual_data_evento')
                                
                                # Priorizar: DISC > destino_data_chegada > ARRV
                                eta_final = None
                                if atual_evento == 'DISC' and atual_data_evento:
                                    eta_final = atual_data_evento
                                elif destino_data_chegada:
                                    eta_final = destino_data_chegada
                                elif atual_evento == 'ARRV' and atual_data_evento:
                                    eta_final = atual_data_evento
                                
                                if eta_final:
                                    # Converter para ISO format se necessário
                                    try:
                                        if isinstance(eta_final, str):
                                            # Tentar parsear e converter para ISO
                                            from datetime import datetime
                                            # Tentar vários formatos
                                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y']:
                                                try:
                                                    dt = datetime.strptime(eta_final.split('.')[0], fmt)
                                                    eta_final = dt.isoformat()
                                                    break
                                                except:
                                                    continue
                                    except:
                                        pass
                                    
                                    eta_sql_server_map[proc_ref] = {
                                        'eta_iso': eta_final,
                                        'evento': atual_evento,
                                        'porto_destino': row.get('destino_nome'),
                                        'navio': row.get('navio'),
                                        'status': row.get('status'),
                                        'fonte': 'sql_server_transporte'
                                    }
                                    logging.info(f'✅ [SQL Server] ETA encontrado para {proc_ref}: {eta_final} (evento: {atual_evento})')
                        
                        logging.info(f'✅ [SQL Server] {len(eta_sql_server_map)} processos com ETA do SQL Server de {len(processos_refs_list)} solicitados')
                    else:
                        logging.warning(f'⚠️ [SQL Server] Query não retornou sucesso ou dados: {result_sql.get("error")}')
            except Exception as e:
                logging.warning(f'⚠️ [SQL Server] Erro ao buscar ETA do SQL Server: {e}')
        
        # ✅ NOVO: Filtrar processos usando ETA mais confiável (ShipsGo > SQL Server > Kanban)
        # ✅ CORREÇÃO CRÍTICA: Se ETA do SQL Server (POD) está disponível, usar TANTO para filtro QUANTO para exibição
        # Se ETA do SQL Server está fora do intervalo, o processo NÃO deve aparecer
        processos_filtrados = []
        for processo_ref, eta_iso_original in processos_com_eta:
            # Prioridade: ShipsGo (oficial) → SQL Server → Kanban
            eta_para_filtro_e_exibicao = None
            # Fonte do ETA:
            # - sql_server: tabela TRANSPORTE (mais confiável)
            # - shipsgo: tabela shipsgo_tracking (API oficial)
            # - kanban: processos_kanban (ETA alimentado pelo ShipsGo via Kanban)
            fonte_eta = 'kanban'
            
            # 1. PRIORIDADE: ShipsGo (shipsgo_tracking) - POD (fonte oficial)
            shipsgo_info = shipsgo_map.get(processo_ref) or {}
            if shipsgo_info and shipsgo_info.get('eta_iso'):
                eta_para_filtro_e_exibicao = shipsgo_info.get('eta_iso')
                fonte_eta = 'shipsgo'
                logging.debug(f'✅ {processo_ref}: ETA do ShipsGo (POD) disponível: {eta_para_filtro_e_exibicao}')
            # 2. FALLBACK: SQL Server (TRANSPORTE) - replica/cache
            elif processo_ref in eta_sql_server_map:
                eta_para_filtro_e_exibicao = eta_sql_server_map[processo_ref]['eta_iso']
                fonte_eta = 'sql_server'
                logging.debug(f'✅ {processo_ref}: ETA do SQL Server (POD) disponível (fallback): {eta_para_filtro_e_exibicao}')
            
            # 3. ÚLTIMO FALLBACK: Kanban (eta_iso_original da tabela processos_kanban)
            if not eta_para_filtro_e_exibicao:
                eta_para_filtro_e_exibicao = eta_iso_original
                fonte_eta = 'kanban'
            
            # ✅ CRÍTICO: Usar ETA mais confiável (SQL Server/ShipsGo se disponível, senão tabela) para verificar intervalo
            # Se ETA do SQL Server está fora do intervalo, o processo NÃO deve aparecer
            if eta_para_filtro_e_exibicao:
                try:
                    # Parsear ETA (SQL Server/ShipsGo se disponível, senão tabela)
                    eta_str_clean = str(eta_para_filtro_e_exibicao).split('.')[0]
                    import re
                    eta_str_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', eta_str_clean)
                    eta_str_clean = eta_str_clean.replace('Z', '').strip()
                    
                    if 'T' in eta_str_clean:
                        eta_date = datetime.fromisoformat(eta_str_clean)
                    elif len(eta_str_clean) == 10 and '-' in eta_str_clean:
                        eta_date = datetime.fromisoformat(eta_str_clean + 'T00:00:00')
                    else:
                        # Tentar formato brasileiro DD/MM/YYYY
                        if '/' in eta_str_clean and len(eta_str_clean) >= 10:
                            try:
                                partes = eta_str_clean.split(' ')
                                data_part = partes[0]
                                if len(data_part.split('/')) == 3:
                                    dia, mes, ano = data_part.split('/')
                                    hora = partes[1] if len(partes) > 1 else '00:00:00'
                                    eta_date = datetime.fromisoformat(f'{ano}-{mes}-{dia}T{hora}')
                                else:
                                    continue
                            except:
                                continue
                        else:
                            continue
                    
                    if eta_date.tzinfo:
                        eta_date = eta_date.replace(tzinfo=None)
                    
                    eta_date_only = eta_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # ✅ CRÍTICO: Verificar se está no intervalo usando ETA mais confiável (SQL Server POD > ShipsGo > Kanban)
                    # Se ETA do SQL Server está fora do intervalo, o processo NÃO deve aparecer
                    if not incluir_passado:
                        eta_dentro_intervalo = data_inicio.date() <= eta_date_only.date() < data_fim.date()
                        # ✅ CORREÇÃO: Filtro "semana" pode incluir ETA < hoje (passado da semana)
                        # Mas processos que já chegaram serão excluídos pela verificação de chegada depois
                        if filtro_data == 'semana':
                            # Para "semana", aceitar qualquer ETA dentro do intervalo (domingo a sábado)
                            if eta_dentro_intervalo:
                                # ✅ Usar o mesmo ETA para exibição (já é o mais confiável disponível)
                                processos_filtrados.append((processo_ref, eta_para_filtro_e_exibicao, fonte_eta))
                                logging.info(f'✅ {processo_ref}: ETA ({fonte_eta}) = {eta_date_only.date()} está no intervalo da semana. ACEITO.')
                            else:
                                logging.warning(f'❌ {processo_ref}: ETA ({fonte_eta}) = {eta_date_only.date()} FORA do intervalo da semana ({data_inicio.date()} a {data_fim.date() - timedelta(days=1)}). REJEITADO.')
                        else:
                            # Para outros filtros, exigir ETA >= hoje (futuro)
                            eta_futuro = eta_date_only >= hoje_date_only
                            if eta_dentro_intervalo and eta_futuro:
                                # ✅ Usar o mesmo ETA para exibição (já é o mais confiável disponível)
                                processos_filtrados.append((processo_ref, eta_para_filtro_e_exibicao, fonte_eta))
                                logging.info(f'✅ {processo_ref}: ETA ({fonte_eta}) = {eta_date_only.date()} está no intervalo. ACEITO.')
                            else:
                                logging.warning(f'❌ {processo_ref}: ETA ({fonte_eta}) = {eta_date_only.date()} FORA do intervalo. REJEITADO.')
                    else:
                        # incluir_passado=True: verificar se está no intervalo
                        if data_inicio.date() <= eta_date_only.date() < data_fim.date():
                            # ✅ Usar o mesmo ETA para exibição (já é o mais confiável disponível)
                            processos_filtrados.append((processo_ref, eta_para_filtro_e_exibicao, fonte_eta))
                            logging.info(f'✅ {processo_ref}: ETA ({fonte_eta}) = {eta_date_only.date()} está no intervalo (passado). ACEITO.')
                except Exception as e:
                    logging.warning(f'Erro ao verificar ETA ({fonte_eta}) para {processo_ref}: {e}. Usando ETA original.')
                    processos_filtrados.append((processo_ref, eta_iso_original, 'kanban'))
            else:
                # Se não tem ETA, usar ETA original
                processos_filtrados.append((processo_ref, eta_iso_original, 'kanban'))
        
        logging.info(f'✅ Após filtrar com ETA (SQL Server/ShipsGo/Kanban): {len(processos_filtrados)} processos de {len(processos_com_eta)} iniciais')
        
        # ✅ CORREÇÃO: Processar mantendo a ordenação por ETA
        for processo_ref, eta_iso_original, fonte_eta in processos_filtrados:
            try:
                # Buscar dados completos do processo
                dados_docs = obter_dados_documentos_processo(processo_ref)
                
                # Extrair informações relevantes (similar a listar_processos_por_categoria_e_situacao)
                # ✅ CORREÇÃO: Extrair categoria do processo_referencia
                categoria_processo = processo_ref.split('.')[0].upper() if '.' in processo_ref else None
                
                processo_info = {
                    'processo_referencia': processo_ref,
                    'categoria': categoria_processo  # ✅ Adicionar categoria extraída
                }
                
                # DI
                dis = dados_docs.get('dis', [])
                if dis:
                    di = dis[0]
                    processo_info['di'] = {
                        'numero': di.get('numero_di', ''),
                        'situacao': di.get('situacao_di', ''),
                        'canal': di.get('canal_selecao_parametrizada', ''),
                        'data_desembaraco': di.get('data_hora_desembaraco', ''),
                        'data_registro': di.get('data_hora_registro', ''),
                        'situacao_entrega': di.get('situacao_entrega_carga', '')
                    }
                
                # DUIMP (apenas produção)
                duimps = dados_docs.get('duimps', [])
                duimps_producao = [d for d in duimps if d.get('vinda_do_ce', False) or d.get('ambiente') == 'producao']
                if duimps_producao:
                    duimp = duimps_producao[0]
                    processo_info['duimp'] = {
                        'numero': duimp.get('numero_duimp', ''),
                        'versao': duimp.get('versao_duimp', ''),
                        'situacao': duimp.get('situacao_duimp', ''),
                        'canal': duimp.get('canal_consolidado', ''),
                        'data_registro': duimp.get('data_registro', '')
                    }
                
                # CE
                ces = dados_docs.get('ces', [])
                if ces:
                    ce = ces[0]
                    processo_info['ce'] = {
                        'numero': ce.get('numero', ''),
                        'situacao': ce.get('situacao', ''),
                        'pendencia_frete': ce.get('pendencia_frete', False),
                        'pendencia_afrmm': ce.get('pendencia_afrmm', False),
                        'carga_bloqueada': ce.get('carga_bloqueada', False),
                        'bloqueio_impede_despacho': ce.get('bloqueio_impede_despacho', False)
                    }
                
                # CCT
                ccts = dados_docs.get('ccts', [])
                if ccts:
                    cct = ccts[0]
                    processo_info['cct'] = {
                        'numero': cct.get('numero', ''),
                        'situacao': cct.get('situacao_atual', ''),
                        'pendencia_frete': cct.get('pendencia_frete', False),
                        'tem_bloqueios': cct.get('tem_bloqueios', False)
                    }
                
                # ✅ ETA/Porto/Navio/Status - PRIORIDADE: ShipsGo (oficial) → SQL Server → Kanban
                sql_server_eta = eta_sql_server_map.get(processo_ref, {})
                
                # ShipsGo tracking (SQLite) - fonte oficial quando presente
                shipsgo_info = shipsgo_map.get(processo_ref) or {}
                
                # Dados do Kanban (processos_kanban) como último fallback
                eta_info = eta_porto_navio_map.get(processo_ref, {})
                
                # ✅ CRÍTICO: Priorizar ShipsGo oficial sobre caches/derivados
                eta_final = None
                fonte_eta_usada = 'kanban'
                
                if shipsgo_info and shipsgo_info.get('eta_iso'):
                    # ✅ PRIORIDADE 1: ShipsGo ETA (POD) - oficial
                    eta_final = shipsgo_info.get('eta_iso')
                    fonte_eta_usada = 'shipsgo'
                    logging.debug(f'✅ Processo {processo_ref}: Priorizando ShipsGo ETA (POD): {eta_final}')
                elif sql_server_eta and sql_server_eta.get('eta_iso'):
                    # ✅ PRIORIDADE 2: SQL Server ETA (TRANSPORTE) - replica/cache
                    eta_final = sql_server_eta.get('eta_iso')
                    fonte_eta_usada = 'sql_server'
                    logging.debug(f'✅ Processo {processo_ref}: Usando SQL Server ETA (fallback): {eta_final} (evento: {sql_server_eta.get("evento")})')
                elif eta_info and eta_info.get('eta_iso'):
                    # ✅ PRIORIDADE 3: ETA do Kanban (alimentado por ShipsGo via Kanban)
                    eta_final = eta_info.get('eta_iso')
                    fonte_eta_usada = 'kanban'
                    logging.debug(f'ℹ️ Processo {processo_ref}: Usando ETA do Kanban (alimentado por ShipsGo): {eta_final}')
                else:
                    # ✅ PRIORIDADE 4: ETA original da query
                    eta_final = eta_iso_original
                    fonte_eta_usada = 'kanban'
                    logging.debug(f'⚠️ Processo {processo_ref}: Usando ETA original da query: {eta_final}')
                
                processo_info['eta'] = {
                    'eta_iso': eta_final,  # ✅ Usar ETA do SQL Server se disponível
                    'fonte_eta': fonte_eta_usada,  # ✅ Indicar fonte do ETA usado
                    'porto_codigo': sql_server_eta.get('porto_codigo') if sql_server_eta.get('porto_codigo') else (shipsgo_info.get('porto_codigo') if shipsgo_info.get('porto_codigo') else eta_info.get('porto_codigo')),
                    'porto_nome': sql_server_eta.get('porto_destino') if sql_server_eta.get('porto_destino') else (shipsgo_info.get('porto_nome') if shipsgo_info.get('porto_nome') else eta_info.get('porto_nome')),
                    'nome_navio': sql_server_eta.get('navio') if sql_server_eta.get('navio') else (eta_info.get('nome_navio') if eta_info.get('nome_navio') else None),  # ✅ Priorizar navio do SQL Server
                    'status_shipsgo': shipsgo_info.get('status') if shipsgo_info.get('status') else eta_info.get('status_shipsgo')
                }
                
                # ✅ CRÍTICO: Manter dados do ShipsGo separadamente (para priorização no ProcessoListService)
                # ✅ CORREÇÃO: shipsgo_info pode ser dict vazio {}, então verificar se tem 'eta_iso' diretamente
                shipsgo_eta_final = None
                if shipsgo_info:
                    shipsgo_eta_final = shipsgo_info.get('eta_iso')
                    logging.debug(f'🔍 Processo {processo_ref}: shipsgo_info encontrado: eta_iso={shipsgo_eta_final}, porto={shipsgo_info.get("porto_codigo")}, status={shipsgo_info.get("status")}')
                else:
                    logging.debug(f'⚠️ Processo {processo_ref}: shipsgo_info não encontrado (dict vazio ou None)')
                
                processo_info['shipsgo'] = {
                    'shipsgo_eta': shipsgo_eta_final,  # ✅ ETA do ShipsGo (Data POD) - fonte da verdade
                    'shipsgo_porto_codigo': shipsgo_info.get('porto_codigo') if shipsgo_info and shipsgo_info.get('porto_codigo') else None,
                    'shipsgo_porto_nome': shipsgo_info.get('porto_nome') if shipsgo_info and shipsgo_info.get('porto_nome') else None,
                    'shipsgo_navio': eta_info.get('nome_navio') if eta_info else None,  # Navio vem do Kanban
                    'shipsgo_status': shipsgo_info.get('status') if shipsgo_info and shipsgo_info.get('status') else None
                }
                
                # ✅ LOG CRÍTICO: Verificar se ShipsGo ETA foi encontrado
                if shipsgo_eta_final:
                    logging.info(f'✅✅✅ Processo {processo_ref}: ShipsGo ETA encontrado: {shipsgo_eta_final} (Data POD - PRIORIZADO sobre Kanban)')
                elif eta_info and eta_info.get('eta_iso'):
                    logging.warning(
                        f'⚠️⚠️⚠️ Processo {processo_ref}: ShipsGo ETA NÃO encontrado! '
                        f'Usando ETA do Kanban (alimentado por ShipsGo): {eta_info.get("eta_iso")}'
                    )
                else:
                    logging.warning(f'⚠️ Processo {processo_ref}: Nenhum ETA encontrado (nem ShipsGo nem Kanban)')
                
                # ✅ CRÍTICO: Verificar se o processo já chegou (dataDestinoFinal ou dataHoraChegadaEfetiva)
                # Se já chegou, NÃO deve aparecer em "chegando" - deve aparecer em "prontos para registro"
                # Mesma lógica de obter_processos_chegando_hoje
                data_chegada_confirmada = None
                
                # Buscar dados do processo para verificar chegada
                try:
                    conn_temp = get_db_connection()
                    conn_temp.row_factory = sqlite3.Row
                    cursor_temp = conn_temp.cursor()
                    cursor_temp.execute('''
                        SELECT dados_completos_json, modal, data_destino_final, data_armazenamento
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                    ''', (processo_ref,))
                    row_temp = cursor_temp.fetchone()
                    conn_temp.close()
                    
                    if row_temp:
                        # 1. PRIORIDADE: Verificar campo da tabela primeiro (mais rápido)
                        if row_temp['data_destino_final']:
                            try:
                                from datetime import datetime
                                data_str = str(row_temp['data_destino_final']).split('T')[0].split(' ')[0]
                                data_chegada_confirmada = datetime.strptime(data_str, '%Y-%m-%d').date()
                                logging.debug(f'✅ {processo_ref}: Chegada confirmada via data_destino_final da tabela: {data_chegada_confirmada}')
                            except Exception as e:
                                logging.debug(f'Erro ao parsear data_destino_final para {processo_ref}: {e}')
                        
                        # 2. Se não encontrou na tabela, buscar do JSON (mesma lógica de obter_processos_chegando_hoje)
                        if not data_chegada_confirmada and row_temp['dados_completos_json']:
                            try:
                                import json
                                dados_json = json.loads(row_temp['dados_completos_json'])
                                modal_proc = row_temp['modal'] or 'Marítimo'

                                # ✅ CORREÇÃO (escala/transbordo): derivar navio/status do POD pelos eventos do shipgov2
                                # Evita casos como NTM.0001/26: navio final do POD muda (ex: LOG IN ENDURANCE -> LOG IN PANTANAL)
                                try:
                                    shipgov2 = dados_json.get('shipgov2') or {}
                                    if isinstance(shipgov2, dict) and shipgov2.get('eventos'):
                                        from services.utils.shipgov2_tracking_utils import resumir_shipgov2_para_painel

                                        resumo = resumir_shipgov2_para_painel(shipgov2)
                                        if resumo.navio_pod:
                                            processo_info['eta']['nome_navio'] = resumo.navio_pod
                                        if resumo.status:
                                            processo_info['eta']['status_shipsgo'] = resumo.status
                                except Exception:
                                    pass
                                
                                # ✅ Para CE marítimo: dataDestinoFinal ou dataArmazenamento
                                # ✅ Para CCT aéreo: dataHoraChegadaEfetiva
                                if 'MARITIMO' in modal_proc.upper() or dados_json.get('ceMercante') or dados_json.get('numero_ce'):
                                    # CE marítimo - campo principal: dataDestinoFinal
                                    if dados_json.get('dataDestinoFinal'):
                                        try:
                                            data_str = str(dados_json.get('dataDestinoFinal')).split('T')[0].split(' ')[0]
                                            data_chegada_confirmada = datetime.strptime(data_str, '%Y-%m-%d').date()
                                            logging.debug(f'✅ {processo_ref}: Chegada confirmada via dataDestinoFinal do JSON: {data_chegada_confirmada}')
                                        except:
                                            pass
                                    # Fallback: dataArmazenamento (confirma que chegou e foi armazenada)
                                    if not data_chegada_confirmada and dados_json.get('dataArmazenamento'):
                                        try:
                                            data_str = str(dados_json.get('dataArmazenamento')).split('T')[0].split(' ')[0]
                                            data_chegada_confirmada = datetime.strptime(data_str, '%Y-%m-%d').date()
                                            logging.debug(f'✅ {processo_ref}: Chegada confirmada via dataArmazenamento do JSON: {data_chegada_confirmada}')
                                        except:
                                            pass
                                elif 'AEREO' in modal_proc.upper() or dados_json.get('cct_data') or dados_json.get('awbBl'):
                                    # CCT aéreo - campo principal: dataHoraChegadaEfetiva
                                    if dados_json.get('dataHoraChegadaEfetiva'):
                                        try:
                                            data_str = str(dados_json.get('dataHoraChegadaEfetiva')).split('T')[0].split(' ')[0]
                                            data_chegada_confirmada = datetime.strptime(data_str, '%Y-%m-%d').date()
                                            logging.debug(f'✅ {processo_ref}: Chegada confirmada via dataHoraChegadaEfetiva do JSON: {data_chegada_confirmada}')
                                        except:
                                            pass
                                    # Fallback: Shipsgo_air.dataHoraChegadaEfetiva
                                    if not data_chegada_confirmada and dados_json.get('Shipsgo_air', {}).get('dataHoraChegadaEfetiva'):
                                        try:
                                            data_str = str(dados_json.get('Shipsgo_air', {}).get('dataHoraChegadaEfetiva')).split('T')[0].split(' ')[0]
                                            data_chegada_confirmada = datetime.strptime(data_str, '%Y-%m-%d').date()
                                            logging.debug(f'✅ {processo_ref}: Chegada confirmada via Shipsgo_air.dataHoraChegadaEfetiva: {data_chegada_confirmada}')
                                        except:
                                            pass
                            except Exception as e:
                                logging.debug(f'Erro ao extrair data de chegada do JSON para {processo_ref}: {e}')
                except Exception as e:
                    logging.debug(f'Erro ao buscar dados para verificar chegada de {processo_ref}: {e}')
                
                # ✅ CRÍTICO: Se o processo já chegou, NÃO incluir na lista de "chegando"
                if data_chegada_confirmada:
                    logging.info(f'⚠️ {processo_ref}: Processo JÁ CHEGOU em {data_chegada_confirmada}. EXCLUÍDO de "chegando".')
                    continue  # Pular este processo - já chegou, não deve aparecer em "chegando"
                
                # ✅ CORREÇÃO: Adicionar ETA original para manter ordenação
                processo_info['_eta_iso_ordenacao'] = eta_iso_original
                
                resultados.append(processo_info)
            except Exception as e:
                logging.warning(f'Erro ao obter dados do processo {processo_ref}: {e}')
                continue
        
        # ✅ CORREÇÃO: Reordenar resultados por ETA (caso a ordenação tenha sido perdida)
        resultados.sort(key=lambda x: x.get('_eta_iso_ordenacao', ''))
        
        # Remover campo auxiliar de ordenação
        for proc in resultados:
            proc.pop('_eta_iso_ordenacao', None)
        
        return resultados
    except Exception as e:
        logging.error(f'Erro ao listar processos por ETA: {e}')
        import traceback
        logging.error(traceback.format_exc())
        return []

def listar_processos_por_navio(nome_navio: str, categoria: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Wrapper fino: implementação extraída para `services/processos_kanban_repository.py`."""
    from services.processos_kanban_repository import listar_processos_por_navio as _impl

    return _impl(
        nome_navio=nome_navio,
        categoria=categoria,
        limit=limit,
        obter_dados_documentos_processo=obter_dados_documentos_processo,
    )

def listar_processos_liberados_registro(categoria: Optional[str] = None, dias_retroativos: Optional[int] = 5, data_inicio: Optional[str] = None, data_fim: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Wrapper fino: implementação extraída para `services/processos_registro_repository.py`."""
    from services.processos_registro_repository import listar_processos_liberados_registro as _impl

    return _impl(
        categoria=categoria,
        dias_retroativos=dias_retroativos,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
        obter_dados_documentos_processo=obter_dados_documentos_processo,
    )


def listar_processos_registrados_hoje(
    categoria: Optional[str] = None,
    limit: int = 200,
    dias_atras: int = 0,
) -> List[Dict[str, Any]]:
    """Wrapper fino: implementação extraída para `services/processos_kanban_repository.py`."""
    from services.processos_kanban_repository import listar_processos_registrados_hoje as _impl

    return _impl(categoria=categoria, limit=limit, dias_atras=dias_atras)


def listar_processos_desembaracados_hoje(
    categoria: Optional[str] = None,
    modal: Optional[str] = None,
    limit: int = 200,
    dias_atras: int = 0,
) -> List[Dict[str, Any]]:
    """
    Lista processos que desembaraçaram HOJE (data/hora de desembaraço).

    Útil para distinguir de "registrados hoje" (registro → canal → exigências → desembaraço).
    Fonte: `obter_movimentacoes_hoje()` (mesma base do fechamento do dia).
    """
    mov = obter_movimentacoes_hoje(categoria=categoria, modal=modal, dias_atras=dias_atras) or {}
    itens = mov.get('processos_desembaracados', []) or []
    try:
        # Ordenar por data/hora de desembaraço quando existir
        itens.sort(key=lambda x: str(x.get('data_desembaraco') or ''), reverse=True)
    except Exception:
        pass
    return itens[:limit]


def listar_processos_em_dta(categoria: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Wrapper fino: implementação extraída para `services/processos_kanban_repository.py`."""
    from services.processos_kanban_repository import listar_processos_em_dta as _impl

    return _impl(categoria=categoria, limit=limit)


def atualizar_status_duimp(numero: str, versao: str, status: str, ambiente: str = 'validacao', nova_versao: Optional[str] = None) -> bool:
    """Atualiza o status de uma DUIMP no banco local.
    
    Args:
        numero: Número da DUIMP
        versao: Versão atual (pode ser "0" para rascunho)
        status: Novo status
        ambiente: Ambiente (validacao/producao)
        nova_versao: Se fornecido, atualiza a versão (ex: "0" -> "1" após registro)
    
    Returns:
        True se atualizou com sucesso, False se não encontrou no banco local
    
    ✅ IMPORTANTE: Não cria entrada automaticamente. Apenas atualiza DUIMPs que já existem
                   no banco local (criadas através desta aplicação).
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # ✅ Verificar se o UPDATE encontrou alguma linha
            rowcount_final = 0
            
            # Se tem nova versão, atualizar versão (ex: 0 -> 1 após registro)
            if nova_versao and nova_versao != versao:
                # ✅ PRIMEIRO: Verificar se já existe entrada com nova versão
                cursor.execute('''
                    SELECT id FROM duimps 
                    WHERE numero = ? AND versao = ?
                ''', (numero, nova_versao))
                existe_nova_versao = cursor.fetchone() is not None
                
                if existe_nova_versao:
                    # ✅ Já existe com nova versão - apenas atualizar status
                    cursor.execute('''
                        UPDATE duimps 
                        SET status = ?, atualizado_em = ?
                        WHERE numero = ? AND versao = ?
                    ''', (status, datetime.now(), numero, nova_versao))
                    rowcount_final = cursor.rowcount
                    
                    # ✅ Remover entrada antiga (versão 0) para evitar duplicata
                    cursor.execute('''
                        DELETE FROM duimps 
                        WHERE numero = ? AND versao = ?
                    ''', (numero, versao))
                    
                    # Atualizar versão nos itens também (mesmo se já existe nova versão)
                    cursor.execute('''
                        UPDATE duimp_itens 
                        SET duimp_versao = ?
                        WHERE duimp_numero = ? AND duimp_versao = ?
                    ''', (nova_versao, numero, versao))
                else:
                    # ✅ NÃO existe com nova versão - fazer UPDATE normal
                    cursor.execute('''
                        UPDATE duimps 
                        SET versao = ?, status = ?, atualizado_em = ?
                        WHERE numero = ? AND versao = ?
                    ''', (nova_versao, status, datetime.now(), numero, versao))
                    rowcount_final = cursor.rowcount
                    
                    # Atualizar versão nos itens também
                    if cursor.rowcount > 0:
                        cursor.execute('''
                            UPDATE duimp_itens 
                            SET duimp_versao = ?
                            WHERE duimp_numero = ? AND duimp_versao = ?
                        ''', (nova_versao, numero, versao))
                
                logging.info(f'✅ Versão atualizada de {versao} para {nova_versao} para DUIMP {numero}')
            else:
                # Apenas atualizar status
                # ✅ Garantir que versão é string para comparação correta
                versao_str = str(versao).strip()
                cursor.execute('''
                    UPDATE duimps 
                    SET status = ?, atualizado_em = ?
                    WHERE numero = ? AND CAST(versao AS TEXT) = ?
                ''', (status, datetime.now(), numero, versao_str))
                rowcount_final = cursor.rowcount
            
            if rowcount_final == 0 and not (nova_versao and nova_versao != versao):
                # ✅ Se não existe e não houve mudança de versão, primeiro verificar se realmente não existe a versão solicitada
                versao_str = str(versao).strip()
                cursor.execute('''
                    SELECT versao FROM duimps 
                    WHERE numero = ? AND CAST(versao AS TEXT) = ?
                ''', (numero, versao_str))
                versao_solicitada_existe = cursor.fetchone()
                
                if versao_solicitada_existe:
                    # ✅ Existe mas UPDATE falhou - pode ser problema de lock ou outra coisa. Tentar UPDATE novamente
                    cursor.execute('''
                        UPDATE duimps 
                        SET status = ?, atualizado_em = ?
                        WHERE numero = ? AND CAST(versao AS TEXT) = ?
                    ''', (status, datetime.now(), numero, versao_str))
                    rowcount_final = cursor.rowcount
                    if rowcount_final > 0:
                        logging.info(f'✅ Status atualizado na segunda tentativa para DUIMP {numero} v{versao_str}')
                else:
                    # ✅ Não existe versão solicitada - verificar se existe outra versão
                    cursor.execute('''
                        SELECT versao FROM duimps 
                        WHERE numero = ?
                        ORDER BY CAST(versao AS INTEGER) DESC
                        LIMIT 1
                    ''', (numero,))
                    versao_existente = cursor.fetchone()
                    
                    if versao_existente:
                        versao_existente_str = str(versao_existente[0]).strip()  # ✅ Garantir que é string
                        
                        # ✅ Se existe versão diferente (ex: 0 quando recebeu 1), atualizar essa versão
                        if versao_existente_str != versao_str:
                            # ✅ Se existe versão menor, atualizar para versão maior
                            if int(versao_existente_str) < int(versao_str):
                                cursor.execute('''
                                    UPDATE duimps 
                                    SET versao = ?, status = ?, atualizado_em = ?
                                    WHERE numero = ? AND versao = ?
                                ''', (versao_str, status, datetime.now(), numero, versao_existente_str))
                                
                                # Atualizar versão nos itens também
                                if cursor.rowcount > 0:
                                    cursor.execute('''
                                        UPDATE duimp_itens 
                                        SET duimp_versao = ?
                                        WHERE duimp_numero = ? AND duimp_versao = ?
                                    ''', (versao_str, numero, versao_existente_str))
                                    
                                logging.info(f'✅ Versão atualizada de {versao_existente_str} para {versao_str} para DUIMP {numero}')
                            else:
                                # ✅ Versão existente é maior - atualizar ela ao invés de criar nova
                                cursor.execute('''
                                    UPDATE duimps 
                                    SET status = ?, atualizado_em = ?
                                    WHERE numero = ? AND versao = ?
                                ''', (status, datetime.now(), numero, versao_existente_str))
                                logging.info(f'✅ Status atualizado na versão existente {versao_existente_str} para DUIMP {numero}')
                        else:
                            # ✅ Existe com mesma versão mas UPDATE não funcionou - tentar uma última vez
                            logging.warning(f'⚠️ DUIMP {numero} v{versao_str} existe no banco mas UPDATE inicial não funcionou. Tentando novamente...')
                            cursor.execute('''
                                UPDATE duimps 
                                SET status = ?, atualizado_em = ?
                                WHERE numero = ? AND CAST(versao AS TEXT) = ?
                            ''', (status, datetime.now(), numero, versao_str))
                            if cursor.rowcount == 0:
                                logging.error(f'❌ Falha ao atualizar DUIMP {numero} v{versao_str} mesmo após verificações. Status não atualizado.')
                                conn.commit()
                                conn.close()
                                return False
                            else:
                                logging.info(f'✅ Status atualizado com sucesso na segunda tentativa para DUIMP {numero} v{versao_str}')
                    else:
                        # ✅ Não existe nenhuma entrada - NÃO criar automaticamente (apenas logar aviso)
                        logging.warning(f'⚠️ DUIMP {numero} v{versao} não encontrada no banco local. Status não foi atualizado. Use "Criar DUIMP" para salvar no banco local primeiro.')
                        conn.commit()
                        conn.close()
                        return False  # ✅ Retornar False ao invés de criar entrada
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))  # Backoff exponencial
                logging.warning(f"⚠️ Database locked ao atualizar status DUIMP {numero}/{versao}, tentando novamente ({tentativa + 1}/{SQLITE_RETRY_ATTEMPTS})")
                continue
            logging.error(f"Erro ao atualizar status DUIMP {numero}/{versao} (tentativa {tentativa + 1}): {e}", exc_info=True)
            return False
        except sqlite3.IntegrityError as e:
            conn.close() if 'conn' in locals() else None
            # ✅ Violação de UNIQUE constraint - pode ser duplicata
            logging.warning(f"⚠️ Tentativa de duplicata ao atualizar DUIMP {numero}/{versao}: {e}")
            # Tentar atualizar a entrada existente
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                versao_final = nova_versao if nova_versao else versao
                cursor.execute('''
                    UPDATE duimps 
                    SET status = ?, atualizado_em = ?
                    WHERE numero = ? AND versao = ?
                ''', (status, datetime.now(), numero, versao_final))
                conn.commit()
                conn.close()
                return True
            except Exception as e2:
                logging.error(f"Erro ao corrigir duplicata: {e2}")
                return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f"Erro ao atualizar status DUIMP {numero}/{versao}: {e}", exc_info=True)
            return False

def buscar_duimp(numero: str, versao: str) -> Optional[Dict[str, Any]]:
    """Busca uma DUIMP no banco local (verifica se existe).
    
    Args:
        numero: Número da DUIMP
        versao: Versão da DUIMP
    
    Returns:
        Dict com dados básicos da DUIMP ou None se não encontrada
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT numero, versao, status, ambiente, processo_referencia
            FROM duimps
            WHERE numero = ? AND versao = ?
        ''', (numero, versao))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        logging.error(f'Erro ao buscar DUIMP {numero}/{versao}: {e}')
        return None


def carregar_duimp(numero: str, versao: str) -> Optional[Dict[str, Any]]:
    """Carrega uma DUIMP do banco local."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT payload_completo, status, ambiente, processo_referencia
            FROM duimps
            WHERE numero = ? AND versao = ?
        ''', (numero, versao))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'payload_completo': json.loads(row['payload_completo']),
                'status': row['status'],
                'ambiente': row['ambiente'],
                'processo_referencia': row['processo_referencia']
            }
        return None
    except Exception as e:
        print(f"Erro ao carregar DUIMP: {e}")
        return None

def adicionar_item_duimp(numero: str, versao: str, numero_item: int, payload_item: Dict[str, Any]) -> bool:
    """Adiciona um item à DUIMP no banco local."""
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO duimp_itens 
                (duimp_numero, duimp_versao, numero_item, payload_item, criado_em)
                VALUES (?, ?, ?, ?, ?)
            ''', (numero, versao, numero_item, json.dumps(payload_item, ensure_ascii=False), datetime.now()))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f"Erro ao adicionar item (tentativa {tentativa + 1}): {e}")
            return False
        except Exception as e:
            logging.error(f"Erro ao adicionar item: {e}")
            return False
    return False

def listar_itens_duimp(numero: str, versao: str) -> List[Dict[str, Any]]:
    """Lista todos os itens de uma DUIMP.
    
    ✅ CORREÇÃO CRÍTICA: Inclui numero_item da coluna no payload_item para garantir
    que identificacao.numeroItem seja preservado ao restaurar itens.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT numero_item, payload_item
            FROM duimp_itens
            WHERE duimp_numero = ? AND duimp_versao = ?
            ORDER BY numero_item
        ''', (numero, versao))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            numero_item_db = row[0]  # numero_item da coluna
            payload_item = json.loads(row[1])  # JSON do item
            
            # ✅ CORREÇÃO CRÍTICA: Garantir que identificacao.numeroItem está no payload
            # Se o payload não tem numeroItem mas temos na coluna, incluir
            if isinstance(payload_item, dict):
                if 'identificacao' not in payload_item:
                    payload_item['identificacao'] = {}
                
                # Se não tem numeroItem no payload mas temos na coluna, incluir
                if 'numeroItem' not in payload_item.get('identificacao', {}) and numero_item_db:
                    payload_item['identificacao']['numeroItem'] = int(numero_item_db)
                    logging.info(f'[LISTAR_ITENS] ✅ numeroItem={numero_item_db} adicionado ao payload do item')
            
            result.append(payload_item)
        
        conn.close()
        return result
    except Exception as e:
        logging.error(f"Erro ao listar itens: {e}")
        return []

def excluir_duimp(numero: str, versao: str) -> bool:
    """Exclui uma DUIMP e seus itens do banco local."""
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
        
            # Excluir itens primeiro (foreign key)
            cursor.execute('DELETE FROM duimp_itens WHERE duimp_numero = ? AND duimp_versao = ?', (numero, versao))
            # Excluir DUIMP
            cursor.execute('DELETE FROM duimps WHERE numero = ? AND versao = ?', (numero, versao))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f"Erro ao excluir DUIMP (tentativa {tentativa + 1}): {e}")
            return False
        except Exception as e:
            logging.error(f"Erro ao excluir DUIMP: {e}")
            return False
    return False

def limpar_duplicatas_duimps() -> int:
    """Remove duplicatas de DUIMPs, mantendo apenas a versão mais recente de cada número.
    
    Returns:
        Número de registros removidos
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # ✅ Encontrar todas as DUIMPs duplicadas (mesmo número, múltiplas versões)
            cursor.execute('''
                SELECT numero, GROUP_CONCAT(versao) as versoes
                FROM duimps
                GROUP BY numero
                HAVING COUNT(*) > 1
            ''')
            
            duplicatas = cursor.fetchall()
            total_removidos = 0
            
            for duimp_numero, versoes_str in duplicatas:
                # Buscar todas as versões desta DUIMP
                cursor.execute('''
                    SELECT versao, atualizado_em
                    FROM duimps
                    WHERE numero = ?
                    ORDER BY CAST(versao AS INTEGER) DESC, atualizado_em DESC
                ''', (duimp_numero,))
                
                versoes = cursor.fetchall()
                
                if len(versoes) > 1:
                    # ✅ Manter apenas a primeira (mais recente)
                    versao_manter = versoes[0][0]
                    
                    # ✅ Remover todas as outras versões
                    for versao_tuple in versoes[1:]:
                        versao_remover = versao_tuple[0]
                        cursor.execute('''
                            DELETE FROM duimp_itens WHERE duimp_numero = ? AND duimp_versao = ?
                        ''', (duimp_numero, versao_remover))
                        cursor.execute('''
                            DELETE FROM duimps WHERE numero = ? AND versao = ?
                        ''', (duimp_numero, versao_remover))
                        total_removidos += 1
                        
                        logging.info(f'✅ Removida duplicata: {duimp_numero} v{versao_remover} (mantida v{versao_manter})')
            
            conn.commit()
            conn.close()
            
            logging.info(f'✅ Limpeza concluída: {total_removidos} duplicata(s) removida(s)')
            return total_removidos
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                logging.warning(f"⚠️ Database locked ao limpar duplicatas, tentando novamente ({tentativa + 1}/{SQLITE_RETRY_ATTEMPTS})")
                continue
            logging.error(f"Erro ao limpar duplicatas (tentativa {tentativa + 1}): {e}")
            return 0
        except Exception as e:
            logging.error(f"Erro ao limpar duplicatas: {e}")
            return 0
    return 0

# ============================================================================
# Funções para Cache do Classif (Nomenclatura Fiscal)
# ============================================================================

def init_classif_cache():
    """Inicializa tabela de cache do Classif."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ✅ SCHEMA EXTRAÍDO (19/01/2026): classif_cache + classif_metadata
    _criar_tabelas_classif_cache(cursor)
    
    conn.commit()
    conn.close()

def _ensure_classif_cache_schema() -> None:
    """
    Self-heal: garante que o schema do Classif existe.

    Em Docker (volume novo), é comum o SQLite existir mas ainda sem `classif_cache`,
    causando erros "no such table: classif_cache" e quebrando a lógica determinística
    de subitens (ex.: semeadura vs outros).
    """
    try:
        init_classif_cache()
    except Exception:
        pass

def get_classif_unidade(ncm: str) -> Optional[str]:
    """Busca unidade de medida estatística de um NCM no cache local."""
    resultado = get_classif_ncm_completo(ncm)
    return resultado['unidade'] if resultado else None

def buscar_hierarquia_ncm(ncm: str) -> List[Dict[str, Any]]:
    """
    Busca a hierarquia completa de um NCM (4, 6 e 8 dígitos).
    
    Args:
        ncm: NCM de 8 dígitos (ex: "07129020")
    
    Returns:
        Lista com hierarquia completa:
        - NCM de 4 dígitos (capítulo): "0712"
        - NCM de 6 dígitos (posição/item): "071290"
        - NCM de 8 dígitos (subitem): "07129020"
    """
    try:
        if not ncm or len(ncm) != 8 or not ncm.isdigit():
            return []
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        hierarquia = []
        
        # 1. Buscar NCM de 4 dígitos (capítulo)
        ncm_4 = ncm[:4]
        cursor.execute('''
            SELECT ncm, descricao, unidade_medida_estatistica
            FROM classif_cache
            WHERE ncm = ?
            LIMIT 1
        ''', (ncm_4,))
        row_4 = cursor.fetchone()
        if row_4:
            hierarquia.append({
                'ncm': row_4[0],
                'descricao': row_4[1] or '',
                'unidade': row_4[2] or '',
                'nivel': 'capitulo',
                'formato': f"{ncm_4[:2]}.{ncm_4[2:]}"
            })
        
        # 2. Buscar NCM de 6 dígitos (posição/item)
        ncm_6 = ncm[:6]
        cursor.execute('''
            SELECT ncm, descricao, unidade_medida_estatistica
            FROM classif_cache
            WHERE ncm = ?
            LIMIT 1
        ''', (ncm_6,))
        row_6 = cursor.fetchone()
        if row_6:
            hierarquia.append({
                'ncm': row_6[0],
                'descricao': row_6[1] or '',
                'unidade': row_6[2] or '',
                'nivel': 'posicao',
                'formato': f"{ncm_6[:2]}.{ncm_6[2:4]}.{ncm_6[4:]}"
            })
        
        # 3. Buscar NCM de 8 dígitos (subitem) - o próprio NCM
        cursor.execute('''
            SELECT ncm, descricao, unidade_medida_estatistica
            FROM classif_cache
            WHERE ncm = ?
            LIMIT 1
        ''', (ncm,))
        row_8 = cursor.fetchone()
        if row_8:
            hierarquia.append({
                'ncm': row_8[0],
                'descricao': row_8[1] or '',
                'unidade': row_8[2] or '',
                'nivel': 'subitem',
                'formato': f"{ncm[:2]}.{ncm[2:4]}.{ncm[4:6]}.{ncm[6:]}"
            })
        
        conn.close()
        return hierarquia
    except Exception as e:
        logging.error(f"Erro ao buscar hierarquia do NCM {ncm}: {e}")
        try:
            conn.close()
        except:
            pass
        return []

def buscar_ncms_do_grupo(ncm_grupo: str) -> Dict[str, Any]:
    """
    Busca todos os NCMs de 8 dígitos que pertencem a um grupo (4 ou 6 dígitos).
    Também retorna a hierarquia completa do grupo.
    
    Args:
        ncm_grupo: NCM de 4, 6 ou 8 dígitos (ex: "8414", "841451", "84145100")
    
    Returns:
        Dict com:
        - hierarquia: Lista com hierarquia completa (4, 6 e 8 dígitos)
        - ncms_8_digitos: Lista com todos os NCMs de 8 dígitos do grupo
        - grupo_base: NCM base do grupo (4 ou 6 dígitos)
    """
    try:
        # Normalizar NCM (remover pontos, traços, espaços)
        ncm_clean = str(ncm_grupo).strip().replace('.', '').replace('-', '').replace(' ', '')
        
        # Determinar grupo base
        if len(ncm_clean) >= 6:
            grupo_base = ncm_clean[:6]  # Grupo de 6 dígitos
        elif len(ncm_clean) >= 4:
            grupo_base = ncm_clean[:4]  # Grupo de 4 dígitos
        else:
            return {
                'hierarquia': [],
                'ncms_8_digitos': [],
                'grupo_base': None,
                'erro': 'NCM_INVALIDO'
            }
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Buscar hierarquia completa (4, 6 e 8 dígitos)
        hierarquia = []
        
        # NCM de 4 dígitos (capítulo)
        ncm_4 = grupo_base[:4]
        cursor.execute('''
            SELECT ncm, descricao, unidade_medida_estatistica
            FROM classif_cache
            WHERE ncm = ?
            LIMIT 1
        ''', (ncm_4,))
        row_4 = cursor.fetchone()
        if row_4:
            hierarquia.append({
                'ncm': row_4[0],
                'descricao': row_4[1] or '',
                'unidade': row_4[2] or '',
                'nivel': 'capitulo',
                'formato': f"{ncm_4[:2]}.{ncm_4[2:]}"
            })
        
        # NCM de 6 dígitos (posição/item) - se grupo_base for 6 dígitos
        if len(grupo_base) >= 6:
            ncm_6 = grupo_base[:6]
            cursor.execute('''
                SELECT ncm, descricao, unidade_medida_estatistica
                FROM classif_cache
                WHERE ncm = ?
                LIMIT 1
            ''', (ncm_6,))
            row_6 = cursor.fetchone()
            if row_6:
                hierarquia.append({
                    'ncm': row_6[0],
                    'descricao': row_6[1] or '',
                    'unidade': row_6[2] or '',
                    'nivel': 'posicao',
                    'formato': f"{ncm_6[:2]}.{ncm_6[2:4]}.{ncm_6[4:]}"
                })
        
        # Se o NCM informado for de 8 dígitos, incluir na hierarquia também
        if len(ncm_clean) == 8:
            cursor.execute('''
                SELECT ncm, descricao, unidade_medida_estatistica
                FROM classif_cache
                WHERE ncm = ?
                LIMIT 1
            ''', (ncm_clean,))
            row_8 = cursor.fetchone()
            if row_8:
                # Verificar se já não está na hierarquia (evitar duplicação)
                ja_existe = any(item.get('ncm') == ncm_clean for item in hierarquia)
                if not ja_existe:
                    hierarquia.append({
                        'ncm': row_8[0],
                        'descricao': row_8[1] or '',
                        'unidade': row_8[2] or '',
                        'nivel': 'subitem',
                        'formato': f"{ncm_clean[:2]}.{ncm_clean[2:4]}.{ncm_clean[4:6]}.{ncm_clean[6:]}"
                    })
        
        # 2. Buscar TODOS os NCMs de 8 dígitos que pertencem ao grupo
        ncms_8_digitos = []
        cursor.execute('''
            SELECT ncm, descricao, unidade_medida_estatistica
            FROM classif_cache
            WHERE ncm LIKE ? || '%'
            AND LENGTH(ncm) = 8
            ORDER BY ncm ASC
        ''', (grupo_base,))
        
        rows_8 = cursor.fetchall()
        for row in rows_8:
            ncm_8 = row[0]
            ncms_8_digitos.append({
                'ncm': ncm_8,
                'descricao': row[1] or '',
                'unidade': row[2] or '',
                'formato': f"{ncm_8[:2]}.{ncm_8[2:4]}.{ncm_8[4:6]}.{ncm_8[6:]}"
            })
        
        conn.close()
        
        return {
            'hierarquia': hierarquia,
            'ncms_8_digitos': ncms_8_digitos,
            'grupo_base': grupo_base,
            'total_8_digitos': len(ncms_8_digitos)
        }
    except Exception as e:
        logging.error(f"Erro ao buscar NCMs do grupo {ncm_grupo}: {e}")
        try:
            conn.close()
        except:
            pass
        return {
            'hierarquia': [],
            'ncms_8_digitos': [],
            'grupo_base': None,
            'erro': str(e)
        }

def get_classif_ncm_completo(ncm: str) -> Optional[Dict[str, Any]]:
    """Busca informações completas de um NCM no cache local (NCM, unidade e descrição)."""
    if not ncm or len(str(ncm).strip()) != 8:
        return None
    try:
        # Normalizar NCM (garantir 8 dígitos)
        ncm_clean = str(ncm).strip().replace('.', '').replace('-', '').replace(' ', '')
        if len(ncm_clean) > 8:
            ncm_clean = ncm_clean[:8]
        if len(ncm_clean) != 8 or not ncm_clean.isdigit():
            return None
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ncm, unidade_medida_estatistica, descricao
            FROM classif_cache
            WHERE ncm = ?
        ''', (ncm_clean,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            unidade = row[1] if row[1] else None
            descricao = row[2] if row[2] else None
            
            # Se encontrou o registro (mesmo que unidade ou descrição sejam None)
            return {
                'ncm': ncm_clean,
                'unidade': unidade.strip() if unidade and unidade.strip() else None,
                'descricao': descricao.strip() if descricao and descricao.strip() else None
            }
        return None
    except sqlite3.OperationalError as e:
        # Self-heal: schema pode não existir ainda no DB do Docker
        if "no such table" in str(e).lower() and "classif_cache" in str(e).lower():
            try:
                _ensure_classif_cache_schema()
                # retry uma vez
                return get_classif_ncm_completo(ncm)
            except Exception:
                pass
        import logging
        logging.error(f"Erro ao buscar NCM completo no Classif: {e}")
        return None
    except Exception as e:
        import logging
        logging.error(f"Erro ao buscar NCM completo no Classif: {e}")
        return None

def buscar_ncms_relacionados_hierarquia(ncm_encontrado: str) -> List[Dict[str, Any]]:
    """
    Busca NCMs relacionados na hierarquia (mesmo grupo hierárquico).
    
    Exemplo: Se encontrar qualquer NCM do grupo 070320, retorna também:
    - 07032010 (Alhos para semeadura)
    - 07032090 (Outros)
    
    ✅ CORREÇÃO: Usa os 6 primeiros dígitos para identificar o grupo (item).
    Não assume que existe um NCM "completo" com 8 dígitos terminando em 00.
    ✅ CORREÇÃO: Também busca por 4 dígitos se o NCM encontrado for de 4 ou 6 dígitos.
    
    Args:
        ncm_encontrado: NCM encontrado na busca (ex: "07032010", "07032090", "070320", "0703")
    
    Returns:
        Lista de NCMs relacionados do mesmo grupo hierárquico
    """
    if not ncm_encontrado or len(ncm_encontrado) < 4:
        return []
    
    try:
        # ✅ CORREÇÃO: Determinar código do grupo baseado no tamanho do NCM
        # - NCM de 4 dígitos (0703): buscar todos que começam com 0703
        # - NCM de 6 dígitos (070320): buscar todos que começam com 070320 (8 dígitos)
        # - NCM de 8 dígitos (07032010): buscar todos que começam com 070320 (6 dígitos)
        if len(ncm_encontrado) >= 6:
            codigo_grupo = ncm_encontrado[:6]  # 6 dígitos = item
            tamanho_minimo = 6  # Buscar NCMs de 6 ou 8 dígitos
        elif len(ncm_encontrado) >= 4:
            codigo_grupo = ncm_encontrado[:4]  # 4 dígitos = posição
            tamanho_minimo = 4  # Buscar NCMs de 4, 6 ou 8 dígitos
        else:
            return []
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # ✅ CORREÇÃO: Buscar todos os NCMs que começam com o mesmo código de grupo
        # Excluir o próprio NCM encontrado
        # Buscar NCMs de qualquer tamanho válido (4, 6 ou 8 dígitos)
        cursor.execute('''
            SELECT ncm, descricao, unidade_medida_estatistica
            FROM classif_cache
            WHERE ncm LIKE ? || '%'
            AND ncm != ?
            AND LENGTH(ncm) IN (4, 6, 8)
            ORDER BY LENGTH(ncm) ASC, ncm ASC
            LIMIT 20
        ''', (codigo_grupo, ncm_encontrado))
        
        rows = cursor.fetchall()
        conn.close()
        
        resultados = []
        for row in rows:
            resultados.append({
                'ncm': row[0],
                'descricao': row[1] or '',
                'unidadeMedidaEstatistica': row[2] or '',
                'relacionado': True  # Flag para indicar que é relacionado
            })
        
        return resultados
    except Exception as e:
        import logging
        logging.error(f"Erro ao buscar NCMs relacionados na hierarquia: {e}")
        return []

def buscar_ncms_por_descricao(termo: str, limite: int = 50, incluir_relacionados: bool = True) -> List[Dict[str, Any]]:
    """
    Busca NCMs por descrição (busca parcial case-insensitive).
    
    ✅ NOVO: Agora inclui NCMs relacionados na hierarquia quando encontra um NCM.
    ✅ CORREÇÃO: Busca por palavras completas para evitar falsos positivos
    (ex: "alhos" não encontra mais "soalhos").
    
    Args:
        termo: Termo de busca (ex: "alho")
        limite: Número máximo de resultados principais (padrão: 50)
        incluir_relacionados: Se True, inclui NCMs relacionados na hierarquia (padrão: True)
    
    Returns:
        Lista de dicionários com ncm, descricao, unidade_medida_estatistica e grupo_hierarquico
    """
    if not termo or len(termo.strip()) < 2:
        return []
    
    try:
        termo_clean = termo.strip().lower()
        
        # ✅ CORREÇÃO CRÍTICA: Buscar APENAS palavras completas, não substrings
        # Exemplo: "alho" deve encontrar "alhos-porros" mas NÃO "cascalho"
        # Usar delimitadores: espaços, vírgulas, hífens, parênteses, dois-pontos, etc.
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # ✅ CORREÇÃO: Buscar plural/singular
        termo_plural = f'{termo_clean}s'
        termo_singular = termo_clean.rstrip('s')
        
        # ✅ NOVO: Busca melhorada que inclui hierarquia (grupos pais)
        # Busca em duas etapas:
        # 1. Busca direta na descrição do NCM (APENAS palavras completas)
        # 2. Busca nos grupos pais (4 e 6 dígitos) e inclui todos os NCMs de 8 dígitos desses grupos
        
        # ETAPA 1: Buscar NCMs que têm o termo como PALAVRA COMPLETA na descrição
        # Delimitadores: espaço, vírgula, hífen, parêntese, dois-pontos, ponto-e-vírgula
        # ✅ IMPORTANTE: NÃO usar '%{termo}%' que encontra substrings como "cascalho"
        cursor.execute('''
            SELECT ncm, descricao, unidade_medida_estatistica
            FROM classif_cache
            WHERE (
                -- Começa com termo (singular ou plural) seguido de delimitador ou fim
                LOWER(descricao) LIKE ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || ',' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || '-' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || '(' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || ':' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || ';' COLLATE NOCASE OR
                LOWER(descricao) = ? COLLATE NOCASE OR
                -- Termo no meio (delimitado antes e depois)
                LOWER(descricao) LIKE '% ' || ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || ',' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || '-' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || '(' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || ':' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || ';' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? COLLATE NOCASE OR
                -- Termo no meio (delimitado antes por vírgula, hífen, etc.)
                LOWER(descricao) LIKE '%, ' || ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE '%-' || ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE '%(' || ? || ' %' COLLATE NOCASE OR
                -- Plural (mesmas condições)
                LOWER(descricao) LIKE ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || ',' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || '-' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || '(' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || ':' COLLATE NOCASE OR
                LOWER(descricao) LIKE ? || ';' COLLATE NOCASE OR
                LOWER(descricao) = ? COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || ',' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || '-' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || '(' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || ':' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? || ';' COLLATE NOCASE OR
                LOWER(descricao) LIKE '% ' || ? COLLATE NOCASE OR
                LOWER(descricao) LIKE '%, ' || ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE '%-' || ? || ' %' COLLATE NOCASE OR
                LOWER(descricao) LIKE '%(' || ? || ' %' COLLATE NOCASE
            )
            ORDER BY 
                CASE 
                    WHEN LOWER(descricao) LIKE ? || ' %' COLLATE NOCASE THEN 1
                    WHEN LOWER(descricao) LIKE ? || ',' COLLATE NOCASE THEN 1
                    WHEN LOWER(descricao) LIKE ? || '-' COLLATE NOCASE THEN 1
                    WHEN LOWER(descricao) = ? COLLATE NOCASE THEN 1
                    WHEN LOWER(descricao) LIKE '% ' || ? || ' %' COLLATE NOCASE THEN 2
                    WHEN LOWER(descricao) LIKE '% ' || ? || ',' COLLATE NOCASE THEN 2
                    WHEN LOWER(descricao) LIKE '% ' || ? || '-' COLLATE NOCASE THEN 2
                    WHEN LOWER(descricao) LIKE '% ' || ? COLLATE NOCASE THEN 2
                    ELSE 3
                END,
                descricao ASC
            LIMIT ?
        ''', (
            # Singular - começa com termo
            termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean,
            # Singular - no meio
            termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean,
            # Singular - delimitado antes
            termo_clean, termo_clean, termo_clean,
            # Plural - começa com termo
            termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural,
            # Plural - no meio
            termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural,
            # Plural - delimitado antes
            termo_plural, termo_plural, termo_plural,
            # ORDER BY
            termo_clean, termo_clean, termo_clean, termo_clean,
            termo_clean, termo_clean, termo_clean, termo_clean,
            limite
        ))
        
        rows_diretos = cursor.fetchall()
        
        # ETAPA 2: Buscar grupos (4 e 6 dígitos) que têm o termo como PALAVRA COMPLETA na descrição
        # Usar a mesma lógica de palavras completas para evitar falsos positivos
        grupos_com_termo = set()
        cursor.execute('''
            SELECT DISTINCT ncm
            FROM classif_cache
            WHERE (
                (LENGTH(ncm) = 4 OR LENGTH(ncm) = 6)
                AND (
                    -- Mesma lógica de palavras completas da ETAPA 1
                    LOWER(descricao) LIKE ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || ',' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || '-' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || '(' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || ':' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || ';' COLLATE NOCASE OR
                    LOWER(descricao) = ? COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ',' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || '-' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || '(' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ':' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ';' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? COLLATE NOCASE OR
                    LOWER(descricao) LIKE '%, ' || ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '%-' || ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '%(' || ? || ' %' COLLATE NOCASE OR
                    -- Plural
                    LOWER(descricao) LIKE ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || ',' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || '-' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || '(' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || ':' COLLATE NOCASE OR
                    LOWER(descricao) LIKE ? || ';' COLLATE NOCASE OR
                    LOWER(descricao) = ? COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ',' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || '-' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || '(' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ':' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? || ';' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '% ' || ? COLLATE NOCASE OR
                    LOWER(descricao) LIKE '%, ' || ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '%-' || ? || ' %' COLLATE NOCASE OR
                    LOWER(descricao) LIKE '%(' || ? || ' %' COLLATE NOCASE
                )
            )
        ''', (
            # Singular
            termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean,
            termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean, termo_clean,
            termo_clean, termo_clean, termo_clean,
            # Plural
            termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural,
            termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural, termo_plural,
            termo_plural, termo_plural, termo_plural
        ))
        
        grupos_rows = cursor.fetchall()
        for grupo_row in grupos_rows:
            grupo_ncm = grupo_row[0]
            grupos_com_termo.add(grupo_ncm)
            
            # Se for grupo de 4 dígitos, também adicionar grupos de 6 dígitos filhos
            if len(grupo_ncm) == 4:
                cursor.execute('''
                    SELECT DISTINCT ncm
                    FROM classif_cache
                    WHERE LENGTH(ncm) = 6
                    AND ncm LIKE ? || '%'
                ''', (grupo_ncm,))
                grupos_6_filhos = cursor.fetchall()
                for grupo_6_row in grupos_6_filhos:
                    grupos_com_termo.add(grupo_6_row[0])
        
        # Buscar todos os NCMs de 8 dígitos que pertencem a esses grupos
        ncms_dos_grupos = []
        if grupos_com_termo:
            grupos_list = list(grupos_com_termo)
            
            or_clauses = ' OR '.join(['ncm LIKE ? || \'%\'' for _ in grupos_list])
            cursor.execute(f'''
                SELECT ncm, descricao, unidade_medida_estatistica
                FROM classif_cache
                WHERE LENGTH(ncm) = 8
                AND (
                    {or_clauses}
                )
                ORDER BY ncm ASC
            ''', grupos_list)
            
            ncms_dos_grupos = cursor.fetchall()
        
        resultados = []
        ncms_adicionados = set()  # Para evitar duplicatas
        grupos_processados = set()  # Para evitar duplicatas
        
        # Processar resultados diretos (NCMs que têm o termo na própria descrição)
        for row in rows_diretos:
            ncm = row[0]
            descricao = row[1] or ''
            unidade = row[2] or ''
            
            # ✅ FILTRO ADICIONAL: Validar com regex que é realmente palavra completa
            # A query SQL já filtra, mas este é um double-check para garantir
            # Evitar falsos positivos como "cascalho" quando busca "alho"
            import re
            
            descricao_lower = descricao.lower()
            termo_lower = termo_clean.lower()
            
            # Normalizar para comparação (remover acentos)
            def normalizar_termo(t):
                # Remover acentos básicos
                t = t.replace('á', 'a').replace('à', 'a').replace('ã', 'a').replace('â', 'a')
                t = t.replace('é', 'e').replace('ê', 'e')
                t = t.replace('í', 'i').replace('î', 'i')
                t = t.replace('ó', 'o').replace('ô', 'o').replace('õ', 'o')
                t = t.replace('ú', 'u').replace('û', 'u')
                return t.lower()
            
            termo_norm = normalizar_termo(termo_lower)
            descricao_norm = normalizar_termo(descricao_lower)
            
            # ✅ CORREÇÃO CRÍTICA: Verificar se é palavra completa usando word boundaries
            # Word boundary \b funciona com: início/fim de string, espaços, pontuação
            # Isso garante que "alho" NÃO encontra "cascalho"
            # Mas encontra "alhos-porros" (porque "alhos" é delimitado por hífen)
            termo_escaped = re.escape(termo_norm)
            termo_plural_escaped = re.escape(termo_norm + 's')
            
            # Padrões: palavra completa delimitada por word boundaries
            # Exemplos que devem MATCH:
            # - "alho" em "alho fresco" → \balho\b
            # - "alhos" em "alhos-porros" → \balhos\b (hífen é word boundary)
            # - "alho" em "produto: alho" → \balho\b
            # Exemplos que NÃO devem MATCH:
            # - "alho" em "cascalho" → \balho\b NÃO match (porque "alho" não está delimitado)
            padrao_singular = r'\b' + termo_escaped + r'\b'
            padrao_plural = r'\b' + termo_plural_escaped + r'\b'
            
            palavra_completa = re.search(padrao_singular, descricao_norm)
            palavra_completa_plural = re.search(padrao_plural, descricao_norm)
            
            # Também verificar se começa com o termo (caso especial)
            comeca_com_termo = descricao_norm.startswith(termo_norm + ' ') or \
                              descricao_norm.startswith(termo_norm + ',') or \
                              descricao_norm.startswith(termo_norm + '-') or \
                              descricao_norm.startswith(termo_norm + '(') or \
                              descricao_norm.startswith(termo_norm + ':') or \
                              descricao_norm == termo_norm or \
                              descricao_norm.startswith(termo_plural_escaped + ' ') or \
                              descricao_norm.startswith(termo_plural_escaped + ',') or \
                              descricao_norm.startswith(termo_plural_escaped + '-') or \
                              descricao_norm.startswith(termo_plural_escaped + '(') or \
                              descricao_norm.startswith(termo_plural_escaped + ':') or \
                              descricao_norm == termo_plural_escaped
            
            # ✅ Só incluir se for palavra completa (validado por regex)
            if not (palavra_completa or palavra_completa_plural or comeca_com_termo):
                continue
            
            # Adicionar NCM encontrado
            if ncm not in ncms_adicionados:
                ncms_adicionados.add(ncm)
                resultados.append({
                    'ncm': ncm,
                    'descricao': descricao,
                    'unidadeMedidaEstatistica': unidade,
                    'relacionado': False,
                    'grupoHierarquico': ncm[:6] if len(ncm) >= 6 else ncm[:4]  # ✅ CORREÇÃO: Usar 6 dígitos se disponível, senão 4
                })
            
            # ✅ NOVO: Buscar NCMs relacionados na hierarquia
            if incluir_relacionados:
                # ✅ CORREÇÃO: Determinar código do grupo baseado no tamanho do NCM
                # - NCM de 4 dígitos (0703): grupo = 0703
                # - NCM de 6 dígitos (070320): grupo = 070320
                # - NCM de 8 dígitos (07032010): grupo = 070320 (6 dígitos)
                if len(ncm) >= 6:
                    codigo_grupo = ncm[:6]  # Usar 6 dígitos para agrupar subitens
                elif len(ncm) >= 4:
                    codigo_grupo = ncm[:4]  # Usar 4 dígitos para agrupar itens
                else:
                    codigo_grupo = ncm  # Usar o próprio código se menor que 4
                
                if codigo_grupo not in grupos_processados:
                    grupos_processados.add(codigo_grupo)
                    relacionados = buscar_ncms_relacionados_hierarquia(ncm)
                    # Adicionar relacionados ao resultado
                    for rel in relacionados:
                        # Verificar se já não está na lista (evitar duplicatas)
                        if not any(r['ncm'] == rel['ncm'] for r in resultados):
                            rel['grupoHierarquico'] = codigo_grupo
                            # ✅ CORREÇÃO: Marcar como relacionado mesmo que não tenha o termo na descrição
                            rel['relacionado'] = True
                            resultados.append(rel)
        
        # ✅ NOVO: Adicionar NCMs dos grupos encontrados (hierarquia)
        # Estes são NCMs de 8 dígitos cujos grupos pais (4 ou 6 dígitos) contêm o termo
        for grupo_row in ncms_dos_grupos:
            ncm_grupo = grupo_row[0]
            descricao_grupo = grupo_row[1] or ''
            unidade_grupo = grupo_row[2] or ''
            
            # Adicionar apenas se não foi adicionado nos resultados diretos
            if ncm_grupo not in ncms_adicionados:
                ncms_adicionados.add(ncm_grupo)
                # Determinar grupo hierárquico
                grupo_hierarquico = ncm_grupo[:6] if len(ncm_grupo) >= 6 else ncm_grupo[:4]
                
                resultados.append({
                    'ncm': ncm_grupo,
                    'descricao': descricao_grupo,
                    'unidadeMedidaEstatistica': unidade_grupo,
                    'relacionado': True,  # ✅ Marcar como relacionado (vem da hierarquia)
                    'grupoHierarquico': grupo_hierarquico
                })
        
        conn.close()
        
        # ✅ CORREÇÃO: Se não encontrou resultados diretos mas encontrou relacionados,
        # ainda assim retornar os relacionados agrupados
        if len(resultados) == 0 and incluir_relacionados:
            # Tentar buscar por grupos hierárquicos conhecidos
            # Exemplo: se buscar "alho", tentar buscar grupo 070320
            grupos_conhecidos = {
                'alho': '070320',
                'alhos': '070320',
            }
            termo_lower = termo_clean.lower()
            if termo_lower in grupos_conhecidos:
                codigo_grupo_esperado = grupos_conhecidos[termo_lower]
                # Buscar todos os NCMs desse grupo
                try:
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT ncm, descricao, unidade_medida_estatistica
                        FROM classif_cache
                        WHERE ncm LIKE ? || '%'
                        AND LENGTH(ncm) = 8
                        ORDER BY ncm ASC
                        LIMIT 20
                    ''', (codigo_grupo_esperado,))
                    rows_grupo = cursor.fetchall()
                    conn.close()
                    
                    for row in rows_grupo:
                        resultados.append({
                            'ncm': row[0],
                            'descricao': row[1] or '',
                            'unidadeMedidaEstatistica': row[2] or '',
                            'relacionado': False,  # Primeiro do grupo não é relacionado
                            'grupoHierarquico': codigo_grupo_esperado
                        })
                except Exception as e:
                    import logging
                    logging.warning(f"Erro ao buscar grupo conhecido {codigo_grupo_esperado}: {e}")
        
        return resultados
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower() and "classif_cache" in str(e).lower():
            try:
                _ensure_classif_cache_schema()
                # retry uma vez
                return buscar_ncms_por_descricao(termo, limite=limite, incluir_relacionados=incluir_relacionados)
            except Exception:
                pass
        import logging
        logging.error(f"Erro ao buscar NCMs por descrição: {e}")
        return []
    except Exception as e:
        import logging
        logging.error(f"Erro ao buscar NCMs por descrição: {e}")
        return []

def salvar_feedback_ncm(descricao_produto: str, ncm_sugerido: str, ncm_correto: str, descricao_ncm_correto: Optional[str] = None, contexto: Optional[Dict[str, Any]] = None) -> bool:
    """
    Salva feedback de correção de NCM sugerido pela IA.
    
    Args:
        descricao_produto: Descrição do produto que foi buscado
        ncm_sugerido: NCM que a IA sugeriu (incorreto)
        ncm_correto: NCM correto fornecido pelo usuário
        descricao_ncm_correto: Descrição do NCM correto (opcional)
        contexto: Contexto adicional (opcional)
    
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        contexto_json = json.dumps(contexto, ensure_ascii=False) if contexto else None
        
        cursor.execute('''
            INSERT INTO ia_feedback_ncm 
            (descricao_produto, ncm_sugerido, ncm_correto, descricao_ncm_correto, contexto)
            VALUES (?, ?, ?, ?, ?)
        ''', (descricao_produto, ncm_sugerido, ncm_correto, descricao_ncm_correto, contexto_json))
        
        conn.commit()
        conn.close()
        
        logging.info(f'✅ Feedback salvo: "{descricao_produto}" → {ncm_sugerido} (errado) → {ncm_correto} (correto)')
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar feedback NCM: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def buscar_feedbacks_similares(descricao_produto: str, limite: int = 5) -> List[Dict[str, Any]]:
    """
    Busca feedbacks históricos similares à descrição do produto.
    
    Args:
        descricao_produto: Descrição do produto a buscar
        limite: Número máximo de feedbacks a retornar
    
    Returns:
        Lista de feedbacks similares ordenados por relevância (mais recentes primeiro)
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar feedbacks que contenham palavras-chave da descrição
        palavras_chave = [p.lower() for p in descricao_produto.split() if len(p) > 2]
        
        if not palavras_chave:
            return []
        
        # Construir query com LIKE para cada palavra-chave
        condicoes = []
        params = []
        for palavra in palavras_chave[:5]:  # Máximo 5 palavras-chave
            condicoes.append('LOWER(descricao_produto) LIKE ?')
            params.append(f'%{palavra}%')
        
        query = f'''
            SELECT descricao_produto, ncm_sugerido, ncm_correto, descricao_ncm_correto, contexto, criado_em
            FROM ia_feedback_ncm
            WHERE {' OR '.join(condicoes)}
            ORDER BY criado_em DESC
            LIMIT ?
        '''
        params.append(limite)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        feedbacks = []
        for row in rows:
            feedbacks.append({
                'descricao_produto': row[0],
                'ncm_sugerido': row[1],
                'ncm_correto': row[2],
                'descricao_ncm_correto': row[3],
                'contexto': json.loads(row[4]) if row[4] else None,
                'criado_em': row[5]
            })
        
        return feedbacks
    except Exception as e:
        logging.error(f"Erro ao buscar feedbacks similares: {e}")
        try:
            conn.close()
        except:
            pass
        return []

def save_classif_ncm(ncm: str, unidade: str, descricao: Optional[str] = None) -> bool:
    """
    Salva/atualiza informação de um NCM no cache.
    
    Returns:
        True se salvou com sucesso, False caso contrário
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO classif_cache 
            (ncm, unidade_medida_estatistica, descricao, data_atualizacao)
            VALUES (?, ?, ?, ?)
        ''', (ncm, unidade, descricao or '', datetime.now()))
        
        conn.commit()
        conn.close()
        
        # ✅ Log apenas para debug (comentar em produção se necessário)
        # import logging
        # logging.debug(f'NCM salvo no cache: {ncm}')
        
        return True
    except Exception as e:
        import logging
        logging.error(f"Erro ao salvar NCM {ncm} no cache Classif: {e}")
        # Tentar fechar conexão se ainda estiver aberta
        try:
            conn.close()
        except:
            pass
        return False

def get_classif_last_update() -> Optional[datetime]:
    """Retorna data da última atualização do cache Classif."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT valor FROM classif_metadata
            WHERE chave = 'last_update'
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None
    except Exception as e:
        print(f"Erro ao buscar data de atualização Classif: {e}")
        return None

def set_classif_last_update(dt: datetime) -> bool:
    """Define data da última atualização do cache Classif."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO classif_metadata (chave, valor, atualizado_em)
            VALUES (?, ?, ?)
        ''', ('last_update', dt.isoformat(), datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao salvar data de atualização Classif: {e}")
        return False

# ============================================================================
# Funções para processos de importação
# ============================================================================

def listar_processos_importacao(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista processos de importação do banco.
    
    Args:
        status: Filtro opcional por status (pendente, processando, sucesso, erro, etc.)
    
    Returns:
        Lista de processos com seus dados
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT processo_referencia, categoria, status, duimp_numero, duimp_versao, 
                       itens_aguardando_produto, mensagem_erro, criado_em, atualizado_em
                FROM processos_importacao
                WHERE status = ?
                ORDER BY criado_em DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT processo_referencia, categoria, status, duimp_numero, duimp_versao,
                       itens_aguardando_produto, mensagem_erro, criado_em, atualizado_em
                FROM processos_importacao
                ORDER BY criado_em DESC
            ''')
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            proc_dict = dict(row)
            # Parse JSON fields que podem estar como string
            try:
                if proc_dict.get('itens_aguardando_produto') and isinstance(proc_dict['itens_aguardando_produto'], str):
                    proc_dict['itens_aguardando_produto'] = json.loads(proc_dict['itens_aguardando_produto'])
                elif proc_dict.get('itens_aguardando_produto') is None:
                    proc_dict['itens_aguardando_produto'] = []
            except:
                proc_dict['itens_aguardando_produto'] = []
            result.append(proc_dict)
        conn.close()
        return result
    except Exception as e:
        logging.error(f"Erro ao listar processos: {e}")
        import traceback
        traceback.print_exc()
        return []

def buscar_processo_importacao(referencia: str) -> Optional[Dict[str, Any]]:
    """Busca um processo de importação por referência."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT processo_referencia, categoria, numero_processo, ano, status, mensagem_erro,
                   duimp_numero, duimp_versao, payload_json, payload_atualizado,
                   itens_aguardando_produto, criado_em, atualizado_em, processado_em
            FROM processos_importacao
            WHERE processo_referencia = ?
        ''', (referencia,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            proc_dict = dict(row)
            # Parse JSON fields
            try:
                if proc_dict.get('payload_json') and isinstance(proc_dict['payload_json'], str):
                    proc_dict['payload_json'] = json.loads(proc_dict['payload_json'])
                if proc_dict.get('payload_atualizado') and isinstance(proc_dict['payload_atualizado'], str):
                    proc_dict['payload_atualizado'] = json.loads(proc_dict['payload_atualizado'])
                if proc_dict.get('itens_aguardando_produto') and isinstance(proc_dict['itens_aguardando_produto'], str):
                    proc_dict['itens_aguardando_produto'] = json.loads(proc_dict['itens_aguardando_produto'])
                elif proc_dict.get('itens_aguardando_produto') is None:
                    proc_dict['itens_aguardando_produto'] = []
            except:
                pass
            return proc_dict
        return None
    except Exception as e:
        logging.error(f"Erro ao buscar processo: {e}")
        return None

def atualizar_processo_importacao(referencia: str, status: Optional[str] = None,
                                  duimp_numero: Optional[str] = None, duimp_versao: Optional[str] = None,
                                  itens_aguardando: Optional[List[int]] = None,
                                  mensagem_erro: Optional[str] = None,
                                  payload_atualizado: Optional[Dict[str, Any]] = None) -> bool:
    """Atualiza um processo de importação."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status:
            updates.append('status = ?')
            params.append(status)
        
        if duimp_numero:
            updates.append('duimp_numero = ?')
            params.append(duimp_numero)
        
        if duimp_versao:
            updates.append('duimp_versao = ?')
            params.append(duimp_versao)
        
        if itens_aguardando is not None:
            updates.append('itens_aguardando_produto = ?')
            params.append(json.dumps(itens_aguardando))
        
        if mensagem_erro is not None:
            updates.append('mensagem_erro = ?')
            params.append(mensagem_erro)
        
        if payload_atualizado:
            updates.append('payload_atualizado = ?')
            params.append(json.dumps(payload_atualizado, ensure_ascii=False))
        
        if status == 'sucesso' or status == 'processando':
            updates.append('processado_em = ?')
            params.append(datetime.now())
        
        updates.append('atualizado_em = ?')
        params.append(datetime.now())
        
        params.append(referencia)
        
        cursor.execute(f'''
            UPDATE processos_importacao
            SET {', '.join(updates)}
            WHERE processo_referencia = ?
        ''', params)
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Erro ao atualizar processo: {e}")
        return False

# ============================================================================
# FASE 1: Funções para vinculação de itens a produtos CATP
# ============================================================================

def vincular_item_produto_catp(processo_referencia: str, numero_item: int, 
                                produto_catp_codigo: int, produto_catp_versao: str,
                                produto_catp_denominacao: str = None, produto_catp_ncm: str = None,
                                fabricante_codigo: str = None, fabricante_versao: str = None,
                                fabricante_ni_operador: str = None, fabricante_pais: str = None) -> bool:
    """Vincula um item do processo a um produto CATP.
    
    Args:
        processo_referencia: Referência do processo (ex: "ALH.0001/25")
        numero_item: Número do item no processo
        produto_catp_codigo: Código do produto CATP
        produto_catp_versao: Versão do produto CATP
        produto_catp_denominacao: Denominação do produto (opcional)
        produto_catp_ncm: NCM do produto (opcional)
        fabricante_*: Dados do fabricante vinculado ao produto (opcional)
    
    Returns:
        True se vinculou com sucesso, False caso contrário
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO processo_itens_vinculacao 
                (processo_referencia, numero_item, produto_catp_codigo, produto_catp_versao,
                 produto_catp_denominacao, produto_catp_ncm, fabricante_codigo, fabricante_versao,
                 fabricante_ni_operador, fabricante_pais, status, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'vinculado', ?)
            ''', (processo_referencia, numero_item, produto_catp_codigo, produto_catp_versao,
                  produto_catp_denominacao, produto_catp_ncm, fabricante_codigo, fabricante_versao,
                  fabricante_ni_operador, fabricante_pais, datetime.now()))
            
            conn.commit()
            conn.close()
            logging.info(f'✅ Item {numero_item} do processo {processo_referencia} vinculado ao produto CATP {produto_catp_codigo}')
            return True
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao vincular item: {e}')
            return False
        except Exception as e:
            logging.error(f'Erro ao vincular item: {e}')
            return False
    
    return False

def listar_itens_processo(processo_referencia: str) -> List[Dict[str, Any]]:
    """Lista todos os itens de um processo com suas vinculações.
    
    Args:
        processo_referencia: Referência do processo
    
    Returns:
        Lista de itens com informações de vinculação
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar processo
        cursor.execute('''
            SELECT payload_json FROM processos_importacao
            WHERE processo_referencia = ?
        ''', (processo_referencia,))
        processo_row = cursor.fetchone()
        
        if not processo_row:
            conn.close()
            return []
        
        # Parse do JSON do processo
        payload = json.loads(processo_row['payload_json'])
        itens_processo = payload.get('itens', [])
        
        # Buscar vinculações
        cursor.execute('''
            SELECT numero_item, produto_catp_codigo, produto_catp_versao, 
                   produto_catp_denominacao, produto_catp_ncm,
                   fabricante_codigo, fabricante_versao, fabricante_ni_operador, fabricante_pais,
                   status, dados_item_completos
            FROM processo_itens_vinculacao
            WHERE processo_referencia = ?
        ''', (processo_referencia,))
        
        vinculacoes = {row['numero_item']: dict(row) for row in cursor.fetchall()}
        
        # Combinar itens do processo com vinculações
        resultado = []
        for item in itens_processo:
            num_item = item.get('numero_item', len(resultado) + 1)
            vinculacao = vinculacoes.get(num_item, {})
            
            item_completo = {
                'numero_item': num_item,
                'item_processo': item,
                'vinculacao': vinculacao if vinculacao else None,
                'status': vinculacao.get('status', 'pendente') if vinculacao else 'pendente'
            }
            resultado.append(item_completo)
        
        conn.close()
        return resultado
    except Exception as e:
        logging.error(f'Erro ao listar itens do processo: {e}')
        return []

def buscar_item_vinculado(processo_referencia: str, numero_item: int) -> Optional[Dict[str, Any]]:
    """Busca dados de vinculação de um item específico.
    
    Returns:
        Dict com dados da vinculação ou None se não encontrado
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM processo_itens_vinculacao
            WHERE processo_referencia = ? AND numero_item = ?
        ''', (processo_referencia, numero_item))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        logging.error(f'Erro ao buscar item vinculado: {e}')
        return None

# ============================================================================
# Funções para log de processos
# ============================================================================

def adicionar_log_processo(processo_referencia: str, nivel: str, mensagem: str, 
                           dados_adicionais: Optional[Dict[str, Any]] = None) -> Optional[int]:
    """Adiciona uma entrada de log para um processo.
    
    Args:
        processo_referencia: Referência do processo
        nivel: Nível do log (INFO, WARNING, ERROR, SUCCESS)
        mensagem: Mensagem do log
        dados_adicionais: Dados adicionais em formato JSON (opcional)
    
    Returns:
        ID do log criado ou None em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            dados_json = None
            if dados_adicionais:
                dados_json = json.dumps(dados_adicionais, ensure_ascii=False)
            
            cursor.execute('''
                INSERT INTO processo_log 
                (processo_referencia, nivel, mensagem, dados_adicionais, criado_em)
                VALUES (?, ?, ?, ?, ?)
            ''', (processo_referencia, nivel.upper(), mensagem, dados_json, datetime.now()))
            
            log_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return log_id
        except sqlite3.OperationalError as e:
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao adicionar log (tentativa {tentativa + 1}): {e}')
            return None
        except Exception as e:
            logging.error(f'Erro ao adicionar log: {e}')
            return None
    return None

def listar_logs_processo(processo_referencia: str, nivel: Optional[str] = None, 
                        limit: int = 100) -> List[Dict[str, Any]]:
    """Lista logs de um processo.
    
    Args:
        processo_referencia: Referência do processo
        nivel: Filtrar por nível (opcional)
        limit: Limite de registros (padrão: 100)
    
    Returns:
        Lista de logs ordenados por data (mais recente primeiro)
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if nivel:
            cursor.execute('''
                SELECT id, nivel, mensagem, dados_adicionais, criado_em
                FROM processo_log
                WHERE processo_referencia = ? AND nivel = ?
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (processo_referencia, nivel.upper(), limit))
        else:
            cursor.execute('''
                SELECT id, nivel, mensagem, dados_adicionais, criado_em
                FROM processo_log
                WHERE processo_referencia = ?
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (processo_referencia, limit))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            log_dict = dict(row)
            # Parse dados_adicionais se existir
            try:
                if log_dict.get('dados_adicionais') and isinstance(log_dict['dados_adicionais'], str):
                    log_dict['dados_adicionais'] = json.loads(log_dict['dados_adicionais'])
            except:
                pass
            result.append(log_dict)
        
        conn.close()
        return result
    except Exception as e:
        logging.error(f'Erro ao listar logs: {e}')
        return []

def salvar_processo_importacao(processo_referencia: str, payload_json: Dict[str, Any],
                               categoria: Optional[str] = None, numero_processo: Optional[str] = None,
                               ano: Optional[str] = None) -> bool:
    """Salva um novo processo de importação.
    
    Args:
        processo_referencia: Referência do processo (ex: "ALH.0001/25")
        payload_json: JSON completo do processo
        categoria: Categoria do processo (opcional, será extraída da referência se não informado)
        numero_processo: Número do processo (opcional)
        ano: Ano do processo (opcional)
    
    Returns:
        True se salvou com sucesso, False se já existe ou erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Tentar extrair categoria, número e ano da referência se não informados
            if not categoria and '.' in processo_referencia:
                categoria = processo_referencia.split('.')[0]
            if not numero_processo and '/' in processo_referencia:
                parte_num = processo_referencia.split('.')[-1].split('/')[0]
                numero_processo = parte_num if parte_num else None
            if not ano and '/' in processo_referencia:
                ano = processo_referencia.split('/')[-1]
            
            cursor.execute('''
                INSERT INTO processos_importacao 
                (processo_referencia, categoria, numero_processo, ano, payload_json, status, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, 'pendente', ?, ?)
            ''', (processo_referencia, categoria, numero_processo, ano, 
                  json.dumps(payload_json, ensure_ascii=False), datetime.now(), datetime.now()))
            
            conn.commit()
            conn.close()
            
            # Adicionar log
            adicionar_log_processo(processo_referencia, 'INFO', 'Processo recebido com sucesso')
            
            logging.info(f'✅ Processo {processo_referencia} salvo com sucesso')
            return True
        except sqlite3.IntegrityError:
            # Processo já existe
            conn.close()
            logging.warning(f'⚠️ Processo {processo_referencia} já existe')
            return False
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao salvar processo (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao salvar processo: {e}')
            return False
    return False


# =============================================================================
# FUNÇÕES DE GESTÃO DE PROCESSOS (Monitoramento)
# =============================================================================

def criar_ou_atualizar_processo(processo_referencia: str, categoria: Optional[str] = None, descricao: Optional[str] = None, observacoes: Optional[str] = None, status: str = 'ativo') -> bool:
    """Cria ou atualiza um processo.
    
    Args:
        processo_referencia: Número do processo (ex: "ALH.0001/25")
        categoria: Categoria do processo (ex: "ALH", "CE", "CCT")
        descricao: Descrição do processo
        observacoes: Observações adicionais
        status: Status do processo (ativo, concluido, cancelado, pausado)
    
    Returns:
        True se salvou com sucesso, False em caso de erro
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Extrair categoria do processo_referencia se não fornecido
        if not categoria and processo_referencia:
            partes = processo_referencia.split('.')
            if len(partes) >= 1:
                categoria = partes[0]
        
        cursor.execute('''
            INSERT OR REPLACE INTO processos 
            (processo_referencia, categoria, status, descricao, observacoes, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (processo_referencia, categoria, status, descricao, observacoes, datetime.now()))
        
        conn.commit()
        conn.close()
        logging.info(f'✅ Processo {processo_referencia} salvo com sucesso')
        return True
    except Exception as e:
        logging.error(f'Erro ao salvar processo: {e}')
        return False


def vincular_documento_processo(processo_referencia: str, tipo_documento: str, numero_documento: str) -> bool:
    """Vincula um documento (CE, CCT, etc) a um processo.
    
    Args:
        processo_referencia: Número do processo (ex: "ALH.0001/25")
        tipo_documento: Tipo do documento ("CE", "CCT", "RODOVIARIO")
        numero_documento: Número do documento
    
    Returns:
        True se vinculou com sucesso, False em caso de erro
    """
    try:
        # Primeiro, garantir que o processo existe
        criar_ou_atualizar_processo(processo_referencia)
        
        # ✅ IMPORTANTE: Para CEs, sempre desvincular CEs antigos (cada processo deve ter apenas um CE)
        if tipo_documento == 'CE':
            desvincular_todos_documentos_tipo(processo_referencia, 'CE')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO processo_documentos 
            (processo_referencia, tipo_documento, numero_documento, atualizado_em)
            VALUES (?, ?, ?, ?)
        ''', (processo_referencia, tipo_documento, numero_documento, datetime.now()))
        
        conn.commit()
        conn.close()
        logging.info(f'✅ Documento {tipo_documento} {numero_documento} vinculado ao processo {processo_referencia}')
        return True
    except Exception as e:
        logging.error(f'Erro ao vincular documento ao processo: {e}')
        return False


def listar_processos(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Lista processos, opcionalmente filtrados por status.
    
    Args:
        status: Filtrar por status (opcional)
        limit: Limite de resultados
    
    Returns:
        Lista de dicts com dados dos processos
    """
    # Wrapper fino: implementação extraída para reduzir o monolito.
    from services.processos_sqlite_repository import listar_processos as _impl
    return _impl(status=status, limit=limit)


def buscar_processo(processo_referencia: str) -> Optional[Dict[str, Any]]:
    """Busca um processo pelo número.
    
    Args:
        processo_referencia: Número do processo
    
    Returns:
        Dict com dados do processo ou None se não encontrado
    """
    # Wrapper fino: implementação extraída para reduzir o monolito.
    from services.processos_sqlite_repository import buscar_processo as _impl
    return _impl(processo_referencia)


def listar_processos_por_categoria(categoria: str, limit: int = 200) -> List[str]:
    """Lista processos por categoria (ex: ALH, VDM, MSS, MV5).
    
    Args:
        categoria: Categoria do processo (ex: "ALH", "MV5")
        limit: Limite máximo de processos a retornar
    
    Returns:
        Lista de processo_referencia que começam com a categoria (ex: ["ALH.0001/25", "ALH.0002/25", ...])
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        # Buscar processos que começam com a categoria (ex: "ALH.%")
        # Formato: CATEGORIA.NNNN/AA (ex: ALH.0001/25)
        categoria_upper = categoria.upper().strip()
        padrao = f"{categoria_upper}.%"
        
        # ✅ NOVO: Buscar em múltiplas tabelas (prioridade: processos_kanban > processo_documentos > processos)
        # ✅ CORREÇÃO: Priorizar processos ativos (Kanban) e limitar busca para evitar lentidão
        
        processos_set = set()
        
        # 1. Primeiro: buscar na tabela processos_kanban (processos ativos do Kanban)
        # ✅ CORREÇÃO: Excluir processos finalizados/entregues (apenas processos ativos)
        # ✅ CORREÇÃO: Excluir processos sem documentos E sem ETA futuro ou chegada recente (processos órfãos/antigos)
        # ✅ Priorizar processos mais recentes (ORDER BY processo_referencia DESC para pegar os mais recentes primeiro)
        cursor.execute('''
            SELECT DISTINCT processo_referencia
            FROM processos_kanban
            WHERE processo_referencia LIKE ?
            AND (situacao_ce IS NULL OR situacao_ce != 'ENTREGUE')
            AND (situacao_entrega IS NULL OR situacao_entrega != 'ENTREGUE')
            AND (
                -- Tem pelo menos um documento vinculado
                numero_ce IS NOT NULL 
                OR (numero_di IS NOT NULL AND numero_di != '' AND numero_di != '/       -')
                OR (numero_duimp IS NOT NULL AND numero_duimp != '')
                -- OU tem ETA futuro (ainda não chegou)
                OR (eta_iso IS NOT NULL AND eta_iso != '' AND DATE(eta_iso) >= DATE('now'))
                -- OU chegou recentemente (últimos 30 dias)
                OR (data_destino_final IS NOT NULL AND DATE(data_destino_final) >= DATE('now', '-30 days'))
                -- OU tem DI/DUIMP desembaraçada (ainda é processo ativo que precisa acompanhamento)
                OR (situacao_di IS NOT NULL AND situacao_di LIKE '%DESEMBARAC%')
                OR (situacao_entrega IS NOT NULL AND (situacao_entrega LIKE '%DESEMBARAC%' OR situacao_entrega LIKE '%ENTREGA AUTORIZADA%'))
            )
            ORDER BY processo_referencia DESC
            LIMIT ?
        ''', (padrao, limit))
        
        rows_kanban = cursor.fetchall()
        for row in rows_kanban:
            processos_set.add(row['processo_referencia'])
        
        # 2. Se ainda não atingiu o limite, buscar em processo_documentos (processos com documentos vinculados)
        if len(processos_set) < limit:
            # Buscar mais do que precisa para depois filtrar duplicatas
            cursor.execute('''
                SELECT DISTINCT processo_referencia
                FROM processo_documentos
                WHERE processo_referencia LIKE ?
                ORDER BY processo_referencia DESC
                LIMIT ?
            ''', (padrao, limit))
            
            rows_docs = cursor.fetchall()
            for row in rows_docs:
                if row['processo_referencia'] not in processos_set:
                    processos_set.add(row['processo_referencia'])
                    if len(processos_set) >= limit:
                        break
        
        # 3. Se ainda não atingiu o limite, buscar na tabela processos (processos sem documentos)
        if len(processos_set) < limit:
            cursor.execute('''
                SELECT DISTINCT processo_referencia
                FROM processos
                WHERE processo_referencia LIKE ?
                ORDER BY processo_referencia DESC
                LIMIT ?
            ''', (padrao, limit))
            
            rows_processos = cursor.fetchall()
            for row in rows_processos:
                if row['processo_referencia'] not in processos_set:
                    processos_set.add(row['processo_referencia'])
                    if len(processos_set) >= limit:
                        break
        
        conn.close()
        
        # Ordenar e limitar (manter ordem: Kanban primeiro, depois por referência)
        processos = sorted(list(processos_set))[:limit]
        return processos
    except Exception as e:
        logging.error(f'Erro ao listar processos por categoria {categoria}: {e}')
        return []


def listar_processos_por_categoria_e_situacao(categoria: str, situacao_filtro: Optional[str] = None, filtro_pendencias: Optional[bool] = None, filtro_bloqueio: Optional[bool] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Wrapper fino: implementação extraída para `services/processos_situacao_categoria_repository.py`."""
    from services.processos_situacao_categoria_repository import listar_processos_por_categoria_e_situacao as _impl

    return _impl(
        categoria=categoria,
        situacao_filtro=situacao_filtro,
        filtro_pendencias=filtro_pendencias,
        filtro_bloqueio=filtro_bloqueio,
        limit=limit,
        listar_processos_por_categoria=listar_processos_por_categoria,
        obter_dados_documentos_processo=obter_dados_documentos_processo,
        buscar_di_cache=buscar_di_cache,
    )


def listar_todos_processos_por_situacao(situacao_filtro: Optional[str] = None, filtro_pendencias: Optional[bool] = None, filtro_bloqueio: Optional[bool] = None, filtro_data_desembaraco: Optional[str] = None, limit: int = 500) -> List[Dict[str, Any]]:
    """Wrapper fino: implementação extraída para `services/processos_situacao_todos_repository.py`."""
    from services.processos_situacao_todos_repository import listar_todos_processos_por_situacao as _impl

    return _impl(
        situacao_filtro=situacao_filtro,
        filtro_pendencias=filtro_pendencias,
        filtro_bloqueio=filtro_bloqueio,
        filtro_data_desembaraco=filtro_data_desembaraco,
        limit=limit,
        obter_dados_documentos_processo=obter_dados_documentos_processo,
    )


def listar_documentos_processo(processo_referencia: str) -> List[Dict[str, Any]]:
    """Lista todos os documentos vinculados a um processo.
    
    Busca em:
    1. processo_documentos (tabela de vínculos)
    2. processos_kanban (fallback - documentos do Kanban)
    
    Args:
        processo_referencia: Número do processo
    
    Returns:
        Lista de dicts com dados dos documentos
    """
    # Wrapper fino: implementação extraída para reduzir o monolito.
    from services.processo_documentos_sqlite_repository import listar_documentos_processo as _impl
    return _impl(processo_referencia)


def desvincular_documento_processo(processo_referencia: str, tipo_documento: str, numero_documento: str) -> bool:
    """Desvincula um documento de um processo.
    
    Args:
        processo_referencia: Número do processo (ex: "ALH.0001/25")
        tipo_documento: Tipo do documento ("CE", "CCT", "DI", "RODOVIARIO")
        numero_documento: Número do documento
    
    Returns:
        True se desvinculou com sucesso, False em caso de erro
    """
    # Wrapper fino: implementação extraída para reduzir o monolito.
    from services.processo_documentos_sqlite_repository import desvincular_documento_processo as _impl
    return _impl(processo_referencia, tipo_documento, numero_documento)


def desvincular_todos_documentos_tipo(processo_referencia: str, tipo_documento: str) -> int:
    """Desvincula todos os documentos de um tipo específico de um processo.
    
    Útil para garantir que cada processo tenha apenas um CE, por exemplo.
    
    Args:
        processo_referencia: Número do processo (ex: "ALH.0001/25")
        tipo_documento: Tipo do documento ("CE", "CCT", "DI", "RODOVIARIO")
    
    Returns:
        Número de documentos desvinculados
    """
    # Wrapper fino: implementação extraída para reduzir o monolito.
    from services.processo_documentos_sqlite_repository import desvincular_todos_documentos_tipo as _impl
    return _impl(processo_referencia, tipo_documento)


def obter_processo_por_documento(tipo_documento: str, numero_documento: str) -> Optional[str]:
    """Obtém o processo_referencia vinculado a um documento.
    
    ✅ Esta é a fonte de verdade para vinculações (tabela processo_documentos).
    Use esta função para verificar se um documento está vinculado a um processo,
    mesmo que o campo processo_referencia no cache do documento esteja vazio.
    
    Args:
        tipo_documento: Tipo do documento ("CE", "CCT", "DI", "RODOVIARIO", etc)
        numero_documento: Número do documento
    
    Returns:
        processo_referencia ou None se não encontrado
    """
    # Wrapper fino: implementação extraída para reduzir o monolito.
    from services.processo_documentos_sqlite_repository import obter_processo_por_documento as _impl
    return _impl(tipo_documento, numero_documento)


# =============================================================================
# FUNÇÕES DE CACHE DE CE (Conhecimento de Embarque) - Integra Comex
# =============================================================================

def salvar_ce_cache(numero_ce: str, json_completo: Dict[str, Any], ultima_alteracao_api: Optional[str] = None, processo_referencia: Optional[str] = None) -> bool:
    """Salva ou atualiza um CE no cache local.
    
    Args:
        numero_ce: Número do CE
        json_completo: JSON completo retornado pela API Integra Comex
        ultima_alteracao_api: Data da última alteração da API pública (opcional)
        processo_referencia: Número do processo vinculado (opcional)
    
    Returns:
        True se salvou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Extrair campos principais do JSON
            tipo = json_completo.get('tipo', '')
            ul_destino_final = json_completo.get('ulDestinoFinal', '')
            pais_procedencia = json_completo.get('paisProcedencia', '')
            cpf_cnpj_consignatario = json_completo.get('cpfCnpjConsignatario', '')
            porto_destino = json_completo.get('portoDestino', '')
            porto_origem = json_completo.get('portoOrigem', '')
            situacao_carga = json_completo.get('situacaoCarga', '')
            carga_bloqueada = 1 if json_completo.get('cargaBloqueada', False) else 0
            bloqueio_impede_despacho = 1 if json_completo.get('bloqueioImpedeVinculacaodespacho', False) else 0
            
            # ✅ Extrair DI e DUIMP do documentoDespacho
            # ✅ CORREÇÃO: Trata tanto lista de objetos quanto objeto único
            di_numero = None
            duimp_numero = None
            documento_despacho = json_completo.get('documentoDespacho', [])
            
            # Tratar tanto lista quanto objeto único
            docs_para_processar = []
            if isinstance(documento_despacho, list):
                # Formato: [{ "documentoDespacho": "DI", "numero": "123" }, ...]
                docs_para_processar = documento_despacho
            elif isinstance(documento_despacho, dict):
                # Formato: { "documentoDespacho": "DI", "numero": "123" }
                docs_para_processar = [documento_despacho]
            
            for doc in docs_para_processar:
                if isinstance(doc, dict):
                    doc_tipo = doc.get('documentoDespacho', '')
                    doc_numero = doc.get('numero', '')
                    if doc_tipo == 'DI' and doc_numero:
                        di_numero = doc_numero
                    elif doc_tipo == 'DUIMP' and doc_numero:
                        duimp_numero = doc_numero
            
            # Data de última alteração (prioridade: parâmetro > campo do JSON)
            ultima_alteracao = None
            if ultima_alteracao_api:
                ultima_alteracao = ultima_alteracao_api
            elif 'dataSituacaoCarga' in json_completo:
                try:
                    ultima_alteracao = datetime.fromisoformat(
                        json_completo['dataSituacaoCarga'].replace('Z', '+00:00')
                    ).isoformat()
                except Exception as e:
                    logging.debug(f'Erro ao parsear dataSituacaoCarga: {e}')
                    pass
            
            # Preparar valores
            json_str = json.dumps(json_completo, ensure_ascii=False)
            agora = datetime.now().isoformat()
            
            # Preparar tupla de valores
            valores = (
                numero_ce, tipo, ul_destino_final, pais_procedencia, cpf_cnpj_consignatario,
                porto_destino, porto_origem, situacao_carga, carga_bloqueada,
                bloqueio_impede_despacho, json_str, agora, ultima_alteracao,
                di_numero, duimp_numero
            )
            
            # Adicionar processo_referencia se fornecido
            colunas_sql = '''numero_ce, tipo, ul_destino_final, pais_procedencia, cpf_cnpj_consignatario,
                 porto_destino, porto_origem, situacao_carga, carga_bloqueada,
                 bloqueio_impede_despacho, json_completo, atualizado_em, ultima_alteracao_api,
                 di_numero, duimp_numero'''
            valores_sql = valores
            
            if processo_referencia:
                colunas_sql += ', processo_referencia'
                valores_sql = valores + (processo_referencia,)
            
            cursor.execute(f'''
                INSERT OR REPLACE INTO ces_cache 
                ({colunas_sql})
                VALUES ({', '.join(['?'] * len(valores_sql))})
            ''', valores_sql)
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            # Verificar se realmente foi salvo
            cursor.execute('SELECT numero_ce FROM ces_cache WHERE numero_ce = ?', (numero_ce,))
            verificado = cursor.fetchone()
            conn.close()
            
            if verificado:
                logging.info(f'✅ CE {numero_ce} salvo no cache com sucesso (verificado)')
                return True
            else:
                logging.error(f'❌ ERRO: CE {numero_ce} não foi encontrado após salvar no cache!')
                return False
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao salvar CE no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao salvar CE no cache: {e}')
            return False
    return False


def atualizar_processo_ce_cache(numero_ce: str, processo_referencia: str) -> bool:
    """Atualiza o processo_referencia de um CE já existente no cache.
    
    Args:
        numero_ce: Número do CE
        processo_referencia: Número do processo a vincular
    
    Returns:
        True se atualizou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se o CE existe
            cursor.execute('SELECT numero_ce FROM ces_cache WHERE numero_ce = ?', (numero_ce,))
            ce_existe = cursor.fetchone()
            
            if not ce_existe:
                conn.close()
                logging.warning(f'⚠️ CE {numero_ce} não encontrado no cache para vincular processo')
                return False
            
            # Atualizar processo_referencia
            cursor.execute('''
                UPDATE ces_cache 
                SET processo_referencia = ?, atualizado_em = ?
                WHERE numero_ce = ?
            ''', (processo_referencia, datetime.now().isoformat(), numero_ce))
            
            conn.commit()
            conn.close()
            
            # Também vincular na tabela processo_documentos
            vincular_documento_processo(processo_referencia, 'CE', numero_ce)
            
            logging.info(f'✅ Processo {processo_referencia} vinculado ao CE {numero_ce} com sucesso')
            return True
            
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao atualizar processo do CE no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao atualizar processo do CE no cache: {e}')
            return False
    return False


def atualizar_processo_cct_cache(numero_cct: str, processo_referencia: str) -> bool:
    """Atualiza o processo_referencia de um CCT já existente no cache.
    
    Args:
        numero_cct: Número do CCT
        processo_referencia: Número do processo a vincular
    
    Returns:
        True se atualizou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se o CCT existe
            cursor.execute('SELECT numero_cct FROM ccts_cache WHERE numero_cct = ?', (numero_cct,))
            cct_existe = cursor.fetchone()
            
            if not cct_existe:
                conn.close()
                logging.warning(f'⚠️ CCT {numero_cct} não encontrado no cache para vincular processo')
                return False
            
            # Atualizar processo_referencia
            cursor.execute('''
                UPDATE ccts_cache 
                SET processo_referencia = ?, atualizado_em = ?
                WHERE numero_cct = ?
            ''', (processo_referencia, datetime.now().isoformat(), numero_cct))
            
            conn.commit()
            conn.close()
            
            # Também vincular na tabela processo_documentos
            vincular_documento_processo(processo_referencia, 'CCT', numero_cct)
            
            logging.info(f'✅ Processo {processo_referencia} vinculado ao CCT {numero_cct} com sucesso')
            return True
            
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao atualizar processo do CCT no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao atualizar processo do CCT no cache: {e}')
            return False
    return False


def atualizar_processo_di_cache(numero_di: str, processo_referencia: str) -> bool:
    """Atualiza o processo_referencia de uma DI já existente no cache.
    
    Args:
        numero_di: Número da DI
        processo_referencia: Número do processo a vincular
    
    Returns:
        True se atualizou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se a DI existe
            cursor.execute('SELECT numero_di FROM dis_cache WHERE numero_di = ?', (numero_di,))
            di_existe = cursor.fetchone()
            
            if not di_existe:
                conn.close()
                logging.warning(f'⚠️ DI {numero_di} não encontrada no cache para vincular processo')
                return False
            
            # Atualizar processo_referencia
            cursor.execute('''
                UPDATE dis_cache 
                SET processo_referencia = ?, atualizado_em = ?
                WHERE numero_di = ?
            ''', (processo_referencia, datetime.now().isoformat(), numero_di))
            
            conn.commit()
            conn.close()
            
            # Também vincular na tabela processo_documentos
            vincular_documento_processo(processo_referencia, 'DI', numero_di)
            
            logging.info(f'✅ Processo {processo_referencia} vinculado à DI {numero_di} com sucesso')
            return True
            
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao atualizar processo da DI no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao atualizar processo da DI no cache: {e}')
            return False
    return False


def atualizar_processo_duimp_cache(numero_duimp: str, versao_duimp: str, processo_referencia: str) -> bool:
    """Atualiza o processo_referencia de uma DUIMP já existente no banco.
    
    Args:
        numero_duimp: Número da DUIMP
        versao_duimp: Versão da DUIMP
        processo_referencia: Número do processo a vincular
    
    Returns:
        True se atualizou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar se a DUIMP existe
            cursor.execute('SELECT numero FROM duimps WHERE numero = ? AND versao = ?', (numero_duimp, versao_duimp))
            duimp_existe = cursor.fetchone()
            
            if not duimp_existe:
                conn.close()
                logging.warning(f'⚠️ DUIMP {numero_duimp} v{versao_duimp} não encontrada no banco para vincular processo')
                return False
            
            # Atualizar processo_referencia
            cursor.execute('''
                UPDATE duimps 
                SET processo_referencia = ?, atualizado_em = ?
                WHERE numero = ? AND versao = ?
            ''', (processo_referencia, datetime.now().isoformat(), numero_duimp, versao_duimp))
            
            conn.commit()
            conn.close()
            
            # Também vincular na tabela processo_documentos
            vincular_documento_processo(processo_referencia, 'DUIMP', f"{numero_duimp}v{versao_duimp}")
            
            logging.info(f'✅ Processo {processo_referencia} vinculado à DUIMP {numero_duimp} v{versao_duimp} com sucesso')
            return True
            
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao atualizar processo da DUIMP no banco (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao atualizar processo da DUIMP no banco: {e}')
            return False
    return False


def buscar_ce_cache(numero_ce: str) -> Optional[Dict[str, Any]]:
    """Busca um CE no cache local.
    
    Args:
        numero_ce: Número do CE
    
    Returns:
        Dict com dados do CE (incluindo json_completo) ou None se não encontrado
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        cursor.execute('''
            SELECT * FROM ces_cache WHERE numero_ce = ?
        ''', (numero_ce,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Converter para dict
        ce_data = dict(row)
        
        # Parse JSON completo
        try:
            ce_data['json_completo'] = json.loads(ce_data['json_completo'])
        except:
            pass
        
        # Converter booleanos
        ce_data['carga_bloqueada'] = bool(ce_data.get('carga_bloqueada', 0))
        ce_data['bloqueio_impede_despacho'] = bool(ce_data.get('bloqueio_impede_despacho', 0))
        
        return ce_data
    except Exception as e:
        logging.error(f'Erro ao buscar CE no cache: {e}')
        return None


def salvar_ce_itens_cache(numero_ce: str, json_itens: Dict[str, Any]) -> bool:
    """Salva ou atualiza os itens do CE no cache local.
    
    ⚠️ IMPORTANTE: Esta consulta é BILHETADA, mas só precisa ser feita UMA VEZ por CE.
    Essas informações não mudam (quem muda é apenas o CE).
    
    Args:
        numero_ce: Número do CE
        json_itens: JSON completo retornado pela API Integra Comex (/conhecimentos-embarque/{numero}/itens/)
    
    Returns:
        True se salvou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Extrair campos principais do JSON
            qtd_total_itens = json_itens.get('qtdTotalItens', 0)
            qtd_itens_recebidos = json_itens.get('qtdItensRecebidos', 0)
            qtd_itens_restantes = json_itens.get('qtdItensRestantes', 0)
            
            # Preparar valores
            json_str = json.dumps(json_itens, ensure_ascii=False)
            agora = datetime.now().isoformat()
            
            cursor.execute('''
                INSERT OR REPLACE INTO ce_itens_cache 
                (numero_ce, qtd_total_itens, qtd_itens_recebidos, qtd_itens_restantes, json_itens_completo, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (numero_ce, qtd_total_itens, qtd_itens_recebidos, qtd_itens_restantes, json_str, agora))
            
            conn.commit()
            
            # Verificar se realmente foi salvo
            cursor.execute('SELECT numero_ce FROM ce_itens_cache WHERE numero_ce = ?', (numero_ce,))
            verificado = cursor.fetchone()
            conn.close()
            
            if verificado:
                logging.info(f'✅ Itens do CE {numero_ce} salvos no cache: {qtd_total_itens} total, {qtd_itens_recebidos} recebidos')
                return True
            else:
                logging.warning(f'⚠️ Itens do CE {numero_ce} não foram salvos corretamente')
                return False
                
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao salvar itens do CE no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao salvar itens do CE no cache: {e}')
            return False
    return False


def buscar_ce_itens_cache(numero_ce: str) -> Optional[Dict[str, Any]]:
    """Busca os itens do CE no cache local.
    
    Args:
        numero_ce: Número do CE
    
    Returns:
        Dict com dados dos itens do CE (incluindo json_itens_completo) ou None se não encontrado
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        cursor.execute('''
            SELECT * FROM ce_itens_cache WHERE numero_ce = ?
        ''', (numero_ce,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Converter para dict
        itens_data = dict(row)
        
        # Parse JSON completo
        try:
            itens_data['json_itens_completo'] = json.loads(itens_data['json_itens_completo'])
        except:
            pass
        
        return itens_data
    except Exception as e:
        logging.error(f'Erro ao buscar itens do CE no cache: {e}')
        return None


def listar_ces_cache(cnpj: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Lista CEs do cache, opcionalmente filtrados por CNPJ.
    
    Args:
        cnpj: CNPJ do consignatário (opcional)
        limit: Limite de resultados (padrão: 100)
    
    Returns:
        Lista de dicts com dados dos CEs
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        if cnpj:
            cursor.execute('''
                SELECT numero_ce, tipo, ul_destino_final, pais_procedencia,
                       cpf_cnpj_consignatario, situacao_carga, carga_bloqueada,
                       atualizado_em, processo_referencia
                FROM ces_cache
                WHERE cpf_cnpj_consignatario = ?
                ORDER BY atualizado_em DESC
                LIMIT ?
            ''', (cnpj, limit))
        else:
            cursor.execute('''
                SELECT numero_ce, tipo, ul_destino_final, pais_procedencia,
                       cpf_cnpj_consignatario, situacao_carga, carga_bloqueada,
                       atualizado_em, processo_referencia
                FROM ces_cache
                ORDER BY atualizado_em DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            ce_dict = dict(row)
            ce_dict['carga_bloqueada'] = bool(ce_dict.get('carga_bloqueada', 0))
            result.append(ce_dict)
        
        return result
    except Exception as e:
        logging.error(f'Erro ao listar CEs do cache: {e}')
        return []

# =============================================================================
# FUNÇÕES DE CACHE DE CCT (Conhecimento de Carga Aérea)
# =============================================================================

def _calcular_frete_valor_aduaneiro_db(frete_data: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """Calcula o valor do frete para valor aduaneiro conforme regras do RA/2009.
    
    ⚖️ FUNDAMENTO LEGAL (Art. 77 RA/2009):
    O valor aduaneiro inclui o frete internacional até o ponto de entrada no território aduaneiro.
    
    🧭 REGRAS DE CÁLCULO:
    - Somente Prepaid: Usa total Prepaid
    - Somente Collect: Usa total Collect
    - Prepaid + Collect: Soma ambos (frete total internacional até o Brasil)
    - Outros serviços ("A" e "C"): Incluir se forem custos de transporte internacional
    
    Args:
        frete_data: Dicionário com dados de frete do CCT (campo "frete" do JSON)
    
    Returns:
        Tuple (valor_frete, moeda) ou (None, None) se não encontrado
        - valor_frete: Valor total do frete para valor aduaneiro (float)
        - moeda: Código ISO da moeda (ex: "USD")
    """
    if not isinstance(frete_data, dict):
        return None, None
    
    # ✅ Prioridade 1: Buscar moeda de origem (fallback para moeda)
    moeda_frete_fallback = ''
    if 'moedaOrigem' in frete_data:
        moeda_origem_info = frete_data.get('moedaOrigem', {})
        if isinstance(moeda_origem_info, dict):
            moeda_frete_fallback = moeda_origem_info.get('codigo', '')
    
    valor_prepaid = None
    valor_collect = None
    moeda_prepaid = None
    moeda_collect = None
    
    # ✅ Prioridade 2: Buscar Prepaid e Collect do total (tipo "T")
    if 'totaisMoedaOrigem' in frete_data:
        for total in frete_data['totaisMoedaOrigem']:
            if total.get('tipo', {}).get('codigo') == 'T':
                # Buscar valorPrepaid
                valor_prepaid_dict = total.get('valorPrepaid')
                if valor_prepaid_dict is not None and isinstance(valor_prepaid_dict, dict):
                    valor_prepaid = valor_prepaid_dict.get('valor', 0)
                    if valor_prepaid and valor_prepaid != 0:
                        moeda_info = valor_prepaid_dict.get('moeda', {})
                        moeda_prepaid = moeda_info.get('codigo', '') if moeda_info else moeda_frete_fallback
                
                # Buscar valorCollect
                valor_collect_dict = total.get('valorCollect')
                if valor_collect_dict is not None and isinstance(valor_collect_dict, dict):
                    valor_collect = valor_collect_dict.get('valor', 0)
                    if valor_collect and valor_collect != 0:
                        moeda_info = valor_collect_dict.get('moeda', {})
                        moeda_collect = moeda_info.get('codigo', '') if moeda_info else moeda_frete_fallback
                
                break  # Tipo "T" é único, não precisa continuar
    
    # ✅ REGRA DE VALOR ADUANEIRO: Somar Prepaid + Collect (se ambos existirem)
    valor_frete_total = None
    moeda_frete = None
    
    if valor_prepaid and valor_prepaid != 0 and valor_collect and valor_collect != 0:
        # ✅ Caso 1: Ambos existem → Somar ambos (frete total internacional)
        valor_frete_total = float(valor_prepaid) + float(valor_collect)
        # Usar moeda do Prepaid (ou Collect se Prepaid não tiver)
        moeda_frete = moeda_prepaid or moeda_collect or moeda_frete_fallback
        logging.info(f'[CALCULAR_FRETE_DB] ✅ Frete calculado (Prepaid + Collect): {moeda_frete} {valor_frete_total} (Prepaid: {valor_prepaid}, Collect: {valor_collect})')
    elif valor_prepaid and valor_prepaid != 0:
        # ✅ Caso 2: Somente Prepaid
        valor_frete_total = float(valor_prepaid)
        moeda_frete = moeda_prepaid or moeda_frete_fallback
        logging.info(f'[CALCULAR_FRETE_DB] ✅ Frete calculado (somente Prepaid): {moeda_frete} {valor_frete_total}')
    elif valor_collect and valor_collect != 0:
        # ✅ Caso 3: Somente Collect
        valor_frete_total = float(valor_collect)
        moeda_frete = moeda_collect or moeda_frete_fallback
        logging.info(f'[CALCULAR_FRETE_DB] ✅ Frete calculado (somente Collect): {moeda_frete} {valor_frete_total}')
    
    # ✅ Prioridade 3: Se não encontrou no total, tentar somatorioFretePorItemCarga (fallback)
    if (not valor_frete_total or valor_frete_total == 0) and 'somatorioFretePorItemCarga' in frete_data:
        somatorio = frete_data['somatorioFretePorItemCarga']
        if isinstance(somatorio, dict):
            valor_somatorio = somatorio.get('valor', 0)
            if valor_somatorio and valor_somatorio != 0:
                valor_frete_total = float(valor_somatorio)
                moeda_info = somatorio.get('moeda', {})
                moeda_frete = moeda_info.get('codigo', '') if moeda_info else moeda_frete_fallback
                logging.info(f'[CALCULAR_FRETE_DB] ✅ Frete calculado (somatorioFretePorItemCarga): {moeda_frete} {valor_frete_total}')
    
    # ✅ Se ainda não encontrou moeda, usar moedaOrigem como fallback
    if valor_frete_total and valor_frete_total != 0 and not moeda_frete:
        if 'moedaOrigem' in frete_data:
            moeda_origem_info = frete_data['moedaOrigem']
            if isinstance(moeda_origem_info, dict):
                moeda_frete = moeda_origem_info.get('codigo', '')
    
    # ⚠️ TODO FUTURO: Considerar outros serviços ("A" e "C") se forem custos internacionais
    # Por enquanto, não incluímos para evitar erros, mas pode ser adicionado depois
    
    if valor_frete_total and valor_frete_total != 0:
        return valor_frete_total, moeda_frete
    else:
        return None, None


def salvar_cct_cache(numero_cct: str, json_completo: Dict[str, Any], json_resumo: Optional[Dict[str, Any]] = None, processo_referencia: Optional[str] = None) -> bool:
    """Salva ou atualiza um CCT no cache local.
    
    Args:
        numero_cct: Número do CCT (identificacao)
        json_completo: JSON completo retornado pela API (detalhe)
        json_resumo: JSON resumido retornado pela API (opcional)
        processo_referencia: Número do processo vinculado (opcional)
    
    Returns:
        True se salvou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # CCT pode vir como array (primeiro item) ou objeto único
            cct_data = json_completo[0] if isinstance(json_completo, list) and len(json_completo) > 0 else json_completo
            
            # Extrair campos principais do JSON
            tipo = cct_data.get('tipo', '')
            ruc = cct_data.get('ruc', '')
            cnpj_responsavel = cct_data.get('cnpjResponsavelArquivo', '')
            identificacao_consignatario = cct_data.get('identificacaoDocumentoConsignatario', '')
            aeroporto_origem = cct_data.get('codigoAeroportoOrigemConhecimento', '')
            aeroporto_destino = cct_data.get('codigoAeroportoDestinoConhecimento', '')
            quantidade_volumes = cct_data.get('quantidadeVolumesConhecimento', 0)
            peso_bruto = cct_data.get('pesoBrutoConhecimento', 0)
            
            # Extrair situação atual (do primeiro item de partesEstoque se existir)
            # IMPORTANTE: Esta informação só existe no DETALHE, não no resumo
            situacao_atual = None
            data_hora_situacao_atual = None
            data_chegada_efetiva = None
            if 'partesEstoque' in cct_data and isinstance(cct_data['partesEstoque'], list) and len(cct_data['partesEstoque']) > 0:
                parte_estoque = cct_data['partesEstoque'][0]
                situacao_atual = parte_estoque.get('situacaoAtual', '')
                data_hora_str = parte_estoque.get('dataHoraSituacaoAtual', '')
                if data_hora_str:
                    try:
                        # Formato: "13/10/2025 13:46:43"
                        from datetime import datetime
                        data_hora_situacao_atual = datetime.strptime(data_hora_str, '%d/%m/%Y %H:%M:%S').isoformat()
                    except:
                        pass
            # Se não encontrou situação no detalhe, tentar no nível raiz (resumo pode ter)
            if not situacao_atual:
                situacao_atual = cct_data.get('situacao', '')
            
            # Extrair data de chegada efetiva (do primeiro item de viagensAssociadas se existir)
            if 'viagensAssociadas' in cct_data and isinstance(cct_data['viagensAssociadas'], list) and len(cct_data['viagensAssociadas']) > 0:
                viagem = cct_data['viagensAssociadas'][0]
                data_chegada_str = viagem.get('dataHoraChegadaEfetiva', '')
                if data_chegada_str:
                    try:
                        from datetime import datetime
                        data_chegada_efetiva = datetime.fromisoformat(data_chegada_str.replace('Z', '+00:00')).isoformat()
                    except:
                        pass
            
            # Verificar bloqueios (ativos e baixados para histórico)
            bloqueios_ativos = cct_data.get('bloqueiosAtivos', [])
            bloqueios_baixados = cct_data.get('bloqueiosBaixados', [])
            tem_bloqueios = 1 if bloqueios_ativos and len(bloqueios_ativos) > 0 else 0
            bloqueios_json = json.dumps(bloqueios_ativos, ensure_ascii=False) if bloqueios_ativos else ''
            # Salvar também bloqueios baixados (histórico) - importante para o usuário ver quando foram baixados
            bloqueios_baixados_json = json.dumps(bloqueios_baixados, ensure_ascii=False) if bloqueios_baixados else ''
            
            # ✅ Extrair valores de frete (do detalhe) - REGRA DE VALOR ADUANEIRO (Art. 77 RA/2009)
            # ⚖️ Somar Prepaid + Collect se ambos existirem (frete total internacional até o Brasil)
            valor_frete_total = None
            moeda_frete = None
            if 'frete' in cct_data:
                frete = cct_data['frete']
                # ✅ Usar função auxiliar que segue regras de valor aduaneiro
                valor_frete_total, moeda_frete = _calcular_frete_valor_aduaneiro_db(frete)
                
                # Log para debug
                if valor_frete_total and valor_frete_total != 0:
                    logging.info(f'[SALVAR_CCT_CACHE] ✅ Frete extraído para CCT {numero_cct}: {moeda_frete} {valor_frete_total}')
                else:
                    logging.warning(f'[SALVAR_CCT_CACHE] ⚠️ Frete não encontrado para CCT {numero_cct}')
            
            # ✅ Extrair DI e DUIMP vinculadas (do documentosSaida)
            # ✅ REGRA: Tipo 10 = DI, Tipo 30 = DUIMP (conforme documentação Portal Único)
            di_numero = None
            duimp_vinculada = None
            versao_duimp = None
            if 'documentosSaida' in cct_data and isinstance(cct_data['documentosSaida'], list) and len(cct_data['documentosSaida']) > 0:
                for doc in cct_data['documentosSaida']:
                    doc_tipo = doc.get('tipo', '')
                    # Tipo 10 = DI
                    if doc_tipo == '10' or str(doc_tipo) == '10':
                        di_numero = doc.get('numero', '')
                    # Tipo 30 = DUIMP
                    elif doc_tipo == '30' or str(doc_tipo) == '30':
                        duimp_vinculada = doc.get('numero', '')
                        versao_duimp = doc.get('versaoDuimp', '')
            
            # Preparar valores
            json_completo_str = json.dumps(cct_data if not isinstance(json_completo, list) else json_completo, ensure_ascii=False)
            json_resumo_str = json.dumps(json_resumo, ensure_ascii=False) if json_resumo else None
            agora = datetime.now().isoformat()
            
            # Preparar tupla de valores
            valores = (
                numero_cct, tipo, ruc, cnpj_responsavel, identificacao_consignatario,
                aeroporto_origem, aeroporto_destino, situacao_atual, data_hora_situacao_atual,
                data_chegada_efetiva, quantidade_volumes, peso_bruto, tem_bloqueios,
                bloqueios_json, bloqueios_baixados_json, valor_frete_total, moeda_frete, di_numero,
                duimp_vinculada, versao_duimp, json_completo_str, json_resumo_str, agora
            )
            
            # Adicionar processo_referencia se fornecido
            colunas_sql = '''numero_cct, tipo, ruc, cnpj_responsavel_arquivo, identificacao_documento_consignatario,
                 aeroporto_origem, aeroporto_destino, situacao_atual, data_hora_situacao_atual,
                 data_chegada_efetiva, quantidade_volumes, peso_bruto, tem_bloqueios,
                 bloqueios_ativos, bloqueios_baixados, valor_frete_total, moeda_frete, di_numero,
                 duimp_vinculada, versao_duimp, json_completo, json_resumo, atualizado_em'''
            valores_sql = valores
            
            if processo_referencia:
                colunas_sql += ', processo_referencia'
                valores_sql = valores + (processo_referencia,)
            
            cursor.execute(f'''
                INSERT OR REPLACE INTO ccts_cache 
                ({colunas_sql})
                VALUES ({', '.join(['?'] * len(valores_sql))})
            ''', valores_sql)
            
            conn.commit()
            
            # Verificar se realmente foi salvo
            cursor.execute('SELECT numero_cct FROM ccts_cache WHERE numero_cct = ?', (numero_cct,))
            verificado = cursor.fetchone()
            conn.close()
            
            if verificado:
                logging.info(f'✅ CCT {numero_cct} salvo no cache com sucesso (verificado)')
                return True
            else:
                logging.error(f'❌ ERRO: CCT {numero_cct} não foi encontrado após salvar no cache!')
                return False
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao salvar CCT no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao salvar CCT no cache: {e}')
            import traceback
            logging.error(traceback.format_exc())
            return False
    return False


def buscar_cct_cache(numero_cct: str) -> Optional[Dict[str, Any]]:
    """Busca um CCT no cache local.
    
    Args:
        numero_cct: Número do CCT (identificacao)
    
    Returns:
        Dict com dados do CCT (incluindo json_completo) ou None se não encontrado
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        cursor.execute('''
            SELECT * FROM ccts_cache WHERE numero_cct = ?
        ''', (numero_cct,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Converter para dict
        cct_data = dict(row)
        
        # Parse JSON completo
        try:
            cct_data['json_completo'] = json.loads(cct_data['json_completo'])
        except:
            pass
        
        # Parse JSON resumo se existir
        if cct_data.get('json_resumo'):
            try:
                cct_data['json_resumo'] = json.loads(cct_data['json_resumo'])
            except:
                pass
        
        # Parse bloqueios ativos se existir
        if cct_data.get('bloqueios_ativos'):
            try:
                cct_data['bloqueios_ativos'] = json.loads(cct_data['bloqueios_ativos'])
            except:
                # Se falhar o parse, garantir que seja uma lista vazia
                cct_data['bloqueios_ativos'] = []
        else:
            # Se não existir, garantir que seja uma lista vazia
            cct_data['bloqueios_ativos'] = []
        
        # ✅ NOVO: Parse bloqueios baixados se existir
        if cct_data.get('bloqueios_baixados'):
            try:
                cct_data['bloqueios_baixados'] = json.loads(cct_data['bloqueios_baixados'])
            except:
                # Se falhar o parse, garantir que seja uma lista vazia
                cct_data['bloqueios_baixados'] = []
        else:
            # Se não existir, garantir que seja uma lista vazia
            cct_data['bloqueios_baixados'] = []
        
        # Converter booleanos
        cct_data['tem_bloqueios'] = bool(cct_data.get('tem_bloqueios', 0))
        
        return cct_data
    except Exception as e:
        logging.error(f'Erro ao buscar CCT no cache: {e}')
        return None


def listar_ccts_cache(cnpj: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Lista CCTs do cache, opcionalmente filtrados por CNPJ.
    
    Args:
        cnpj: CNPJ do consignatário (opcional)
        limit: Limite de resultados (padrão: 100)
    
    Returns:
        Lista de dicts com dados dos CCTs
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        if cnpj:
            cursor.execute('''
                SELECT numero_cct, tipo, ruc, identificacao_documento_consignatario,
                       situacao_atual, data_hora_situacao_atual, tem_bloqueios,
                       atualizado_em, processo_referencia
                FROM ccts_cache
                WHERE identificacao_documento_consignatario = ?
                ORDER BY atualizado_em DESC
                LIMIT ?
            ''', (cnpj, limit))
        else:
            cursor.execute('''
                SELECT numero_cct, tipo, ruc, identificacao_documento_consignatario,
                       situacao_atual, data_hora_situacao_atual, tem_bloqueios,
                       atualizado_em, processo_referencia
                FROM ccts_cache
                ORDER BY atualizado_em DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            cct_dict = dict(row)
            cct_dict['tem_bloqueios'] = bool(cct_dict.get('tem_bloqueios', 0))
            result.append(cct_dict)
        
        return result
    except Exception as e:
        logging.error(f'Erro ao listar CCTs do cache: {e}')
        return []


def _gerar_chave_unica_di(numero_di: Optional[str] = None, numero_identificacao: Optional[str] = None, numero_protocolo: Optional[str] = None) -> str:
    """Gera chave única para DI baseada nos parâmetros disponíveis.
    
    Args:
        numero_di: Número da DI
        numero_identificacao: CNPJ/CPF Importador
        numero_protocolo: Protocolo da DI
    
    Returns:
        Chave única para identificar a DI no cache
    """
    # Prioridade: numero_di > numero_protocolo > numero_identificacao
    if numero_di:
        return f"DI_{numero_di}"
    elif numero_protocolo:
        return f"PROT_{numero_protocolo}"
    elif numero_identificacao:
        return f"CNPJ_{numero_identificacao}"
    else:
        # Fallback: usar timestamp (não recomendado, mas necessário)
        import time
        return f"DI_{int(time.time())}"


def salvar_di_cache(numero_di: Optional[str] = None, numero_identificacao: Optional[str] = None, numero_protocolo: Optional[str] = None, json_completo: Dict[str, Any] = None, ultima_alteracao_api: Optional[str] = None, processo_referencia: Optional[str] = None) -> bool:
    """Salva ou atualiza uma DI no cache local.
    
    Args:
        numero_di: Número da DI (opcional)
        numero_identificacao: CNPJ/CPF Importador (opcional)
        numero_protocolo: Protocolo da DI (opcional)
        json_completo: JSON completo retornado pela API Integra Comex
        ultima_alteracao_api: Data da última alteração da API pública (opcional) - CRÍTICO para evitar consultas duplicadas
        processo_referencia: Número do processo vinculado (opcional)
    
    Returns:
        True se salvou com sucesso, False em caso de erro
    """
    if not json_completo:
        return False
    
    chave_unica = _gerar_chave_unica_di(numero_di, numero_identificacao, numero_protocolo)
    
    # ✅ Extrair campos importantes do JSON
    dados_gerais = json_completo.get('dadosGerais', {})
    dados_despacho = json_completo.get('dadosDespacho', {})
    
    # Extrair campos importantes
    canal_selecao = dados_despacho.get('canalSelecaoParametrizada', '')
    data_hora_desembaraco = dados_despacho.get('dataHoraDesembaraco')
    # ✅ CORREÇÃO: dataHoraRegistro pode estar em dadosDespacho OU na raiz do JSON
    data_hora_registro = (
        dados_despacho.get('dataHoraRegistro') or
        json_completo.get('dataHoraRegistro') or
        dados_gerais.get('dataHoraRegistro')
    )
    situacao_di = dados_gerais.get('situacaoDI', '')
    situacao_entrega = dados_gerais.get('situacaoEntregaCarga', '')
    data_hora_situacao_di = dados_gerais.get('dataHoraSituacaoDI')  # ✅ NOVO: Data/hora da situação da DI
    
    # Garantir que numero_di e numero_protocolo estejam extraídos do JSON se não fornecidos
    if not numero_di:
        numero_di = dados_gerais.get('numeroDI', '')
    if not numero_protocolo:
        numero_protocolo = dados_gerais.get('numeroProtocolo', '')
    
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Preparar valores
            json_str = json.dumps(json_completo, ensure_ascii=False)
            agora = datetime.now().isoformat()
            
            # ✅ CRÍTICO: Processar ultima_alteracao_api (pode ser string ISO ou datetime)
            ultima_alteracao_str = None
            if ultima_alteracao_api:
                if isinstance(ultima_alteracao_api, datetime):
                    ultima_alteracao_str = ultima_alteracao_api.isoformat()
                elif isinstance(ultima_alteracao_api, str):
                    ultima_alteracao_str = ultima_alteracao_api
                else:
                    logging.warning(f'⚠️ ultima_alteracao_api com tipo inesperado: {type(ultima_alteracao_api)}')
            
            # Preparar tupla de valores (incluindo campos importantes)
            valores = (
                numero_di or '',
                numero_identificacao or '',
                numero_protocolo or '',
                chave_unica,
                json_str,
                agora,
                agora,
                canal_selecao,
                data_hora_desembaraco,
                data_hora_registro,
                situacao_di,
                situacao_entrega,
                data_hora_situacao_di,  # ✅ NOVO: Data/hora da situação da DI
                ultima_alteracao_str  # ✅ CRÍTICO: Data da última alteração da API pública
            )
            
            # Adicionar processo_referencia se fornecido
            colunas_sql = '''numero_di, numero_identificacao, numero_protocolo, chave_unica, json_completo, consultado_em, atualizado_em,
                 canal_selecao_parametrizada, data_hora_desembaraco, data_hora_registro, situacao_di, situacao_entrega_carga, data_hora_situacao_di, ultima_alteracao_api'''
            valores_sql = valores
            
            if processo_referencia:
                colunas_sql += ', processo_referencia'
                valores_sql = valores + (processo_referencia,)
            
            cursor.execute(f'''
                INSERT OR REPLACE INTO dis_cache 
                ({colunas_sql})
                VALUES ({', '.join(['?'] * len(valores_sql))})
            ''', valores_sql)
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            # Verificar se realmente foi salvo
            cursor.execute('SELECT chave_unica FROM dis_cache WHERE chave_unica = ?', (chave_unica,))
            verificado = cursor.fetchone()
            conn.close()
            
            if verificado:
                logging.info(f'✅ DI (chave: {chave_unica}) salva no cache com sucesso')
                return True
            else:
                logging.error(f'❌ ERRO: DI (chave: {chave_unica}) não foi encontrada após salvar no cache!')
                return False
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao salvar DI no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao salvar DI no cache: {e}')
            return False
    return False


def atualizar_campos_di_cache(numero_di: Optional[str] = None) -> bool:
    """Atualiza os campos extraídos de uma DI existente no cache a partir do JSON completo.
    
    Útil para DIs que foram salvas antes da implementação da extração de campos.
    
    Args:
        numero_di: Número da DI
    
    Returns:
        True se atualizou com sucesso, False em caso de erro
    """
    try:
        di_cache = buscar_di_cache(numero_di=numero_di)
        if not di_cache:
            return False
        
        json_completo = di_cache.get('json_completo', {})
        if isinstance(json_completo, str):
            import json
            json_completo = json.loads(json_completo)
        
        if not json_completo:
            return False
        
        # Extrair campos do JSON (mesma lógica de salvar_di_cache)
        dados_gerais = json_completo.get('dadosGerais', {})
        dados_despacho = json_completo.get('dadosDespacho', {})
        
        canal_selecao = dados_despacho.get('canalSelecaoParametrizada', '')
        data_hora_desembaraco = dados_despacho.get('dataHoraDesembaraco')
        data_hora_registro = dados_despacho.get('dataHoraRegistro')
        situacao_di = dados_gerais.get('situacaoDI', '')
        situacao_entrega = dados_gerais.get('situacaoEntregaCarga', '')
        data_hora_situacao_di = dados_gerais.get('dataHoraSituacaoDI')
        
        # Atualizar apenas os campos que estão faltando
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE dis_cache SET
                canal_selecao_parametrizada = COALESCE(?, canal_selecao_parametrizada),
                data_hora_desembaraco = COALESCE(?, data_hora_desembaraco),
                data_hora_registro = COALESCE(?, data_hora_registro),
                situacao_di = COALESCE(?, situacao_di),
                situacao_entrega_carga = COALESCE(?, situacao_entrega_carga),
                data_hora_situacao_di = COALESCE(?, data_hora_situacao_di)
            WHERE numero_di = ?
        ''', (canal_selecao or None, data_hora_desembaraco, data_hora_registro, 
              situacao_di or None, situacao_entrega or None, data_hora_situacao_di, numero_di))
        
        conn.commit()
        conn.close()
        
        logging.info(f'✅ Campos da DI {numero_di} atualizados no cache')
        return True
    except Exception as e:
        logging.error(f'Erro ao atualizar campos da DI {numero_di}: {e}')
        return False


def buscar_di_cache(numero_di: Optional[str] = None, numero_identificacao: Optional[str] = None, numero_protocolo: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Busca uma DI no cache local.
    
    Args:
        numero_di: Número da DI (opcional)
        numero_identificacao: CNPJ/CPF Importador (opcional)
        numero_protocolo: Protocolo da DI (opcional)
    
    Returns:
        Dict com dados da DI (incluindo json_completo) ou None se não encontrado
    """
    chave_unica = _gerar_chave_unica_di(numero_di, numero_identificacao, numero_protocolo)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        cursor.execute('''
            SELECT * FROM dis_cache WHERE chave_unica = ?
        ''', (chave_unica,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Converter para dict
        di_data = dict(row)
        
        # Parse JSON completo
        json_completo_parsed = None
        try:
            json_completo_parsed = json.loads(di_data['json_completo'])
            di_data['json_completo'] = json_completo_parsed
        except:
            pass
        
        # ✅ NOVO: Se os campos importantes estão faltando, extrair do JSON completo
        if json_completo_parsed and isinstance(json_completo_parsed, dict):
            # Verificar se algum campo importante está faltando
            campos_faltando = []
            if not di_data.get('canal_selecao_parametrizada'):
                campos_faltando.append('canal_selecao_parametrizada')
            if not di_data.get('data_hora_desembaraco'):
                campos_faltando.append('data_hora_desembaraco')
            if not di_data.get('data_hora_registro'):
                campos_faltando.append('data_hora_registro')
            if not di_data.get('situacao_di'):
                campos_faltando.append('situacao_di')
            if not di_data.get('situacao_entrega_carga'):
                campos_faltando.append('situacao_entrega_carga')
            if not di_data.get('data_hora_situacao_di'):
                campos_faltando.append('data_hora_situacao_di')
            
            # Se há campos faltando, extrair do JSON e atualizar no banco
            if campos_faltando:
                try:
                    dados_gerais = json_completo_parsed.get('dadosGerais', {})
                    dados_despacho = json_completo_parsed.get('dadosDespacho', {})
                    
                    # Preencher campos faltantes no dict retornado (para uso imediato)
                    if 'canal_selecao_parametrizada' in campos_faltando:
                        di_data['canal_selecao_parametrizada'] = dados_despacho.get('canalSelecaoParametrizada', '')
                    if 'data_hora_desembaraco' in campos_faltando:
                        di_data['data_hora_desembaraco'] = dados_despacho.get('dataHoraDesembaraco')
                    if 'data_hora_registro' in campos_faltando:
                        di_data['data_hora_registro'] = dados_despacho.get('dataHoraRegistro')
                    if 'situacao_di' in campos_faltando:
                        di_data['situacao_di'] = dados_gerais.get('situacaoDI', '')
                    if 'situacao_entrega_carga' in campos_faltando:
                        di_data['situacao_entrega_carga'] = dados_gerais.get('situacaoEntregaCarga', '')
                    if 'data_hora_situacao_di' in campos_faltando:
                        di_data['data_hora_situacao_di'] = dados_gerais.get('dataHoraSituacaoDI')
                    
                    # Atualizar no banco (em background, não bloquear a resposta)
                    numero_di = di_data.get('numero_di')
                    if numero_di:
                        # Executar atualização de forma assíncrona (não bloquear)
                        try:
                            atualizar_campos_di_cache(numero_di)
                        except:
                            pass  # Não falhar se a atualização assíncrona falhar
                except Exception as e:
                    logging.warning(f'Erro ao extrair campos faltantes do JSON da DI: {e}')
        
        return di_data
    except Exception as e:
        logging.error(f'Erro ao buscar DI no cache: {e}')
        return None

# =============================================================================
# FUNÇÕES DE MONITORAMENTO DE PROCESSOS (Agregação de dados)
# =============================================================================

def buscar_previsao_atracacao_cache(numero_ce: str, horas_validade: int = 24) -> Optional[Dict[str, Any]]:
    """Busca previsão de atracação no cache local.
    
    Args:
        numero_ce: Número do CE
        horas_validade: Horas de validade do cache (padrão: 24 horas)
    
    Returns:
        Dict com dados da previsão de atracação ou None se não encontrado ou expirado
    """
    try:
        from datetime import datetime, timedelta
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        cursor.execute('''
            SELECT * FROM previsao_atracacao_cache 
            WHERE numero_ce = ?
        ''', (numero_ce,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Verificar se cache ainda é válido
        consultado_em_str = row['consultado_em']
        if consultado_em_str:
            try:
                from datetime import timezone
                consultado_em = datetime.fromisoformat(consultado_em_str.replace('Z', '+00:00'))
                if consultado_em.tzinfo is None:
                    consultado_em = consultado_em.replace(tzinfo=timezone.utc)
                
                # Verificar se cache expirou
                agora = datetime.now(consultado_em.tzinfo)
                idade_cache = agora - consultado_em
                
                if idade_cache > timedelta(hours=horas_validade):
                    logging.info(f'⚠️ Cache de previsão de atracação para CE {numero_ce} expirado (idade: {idade_cache})')
                    return None
            except (ValueError, AttributeError) as e:
                logging.warning(f'Erro ao verificar validade do cache para CE {numero_ce}: {e}')
                # Se não conseguir verificar, retornar cache mesmo assim
        
        # Converter para dict
        previsao_data = dict(row)
        
        # Parse JSON completo
        try:
            previsao_data['json_resposta_completa'] = json.loads(previsao_data['json_resposta_completa'])
            if previsao_data.get('dados_completos_escala'):
                previsao_data['dados_completos_escala'] = json.loads(previsao_data['dados_completos_escala'])
        except:
            pass
        
        # Converter booleanos
        previsao_data['escala_encerrada'] = bool(previsao_data.get('escala_encerrada', 0))
        
        logging.info(f'✅ Previsão de atracação para CE {numero_ce} encontrada no cache (válido)')
        return previsao_data
    except Exception as e:
        logging.error(f'Erro ao buscar previsão de atracação no cache: {e}')
        return None


def salvar_previsao_atracacao_cache(numero_ce: str, resposta_api: Dict[str, Any]) -> bool:
    """Salva ou atualiza previsão de atracação no cache local.
    
    Args:
        numero_ce: Número do CE
        resposta_api: Resposta completa da API de previsão de atracação
    
    Returns:
        True se salvou com sucesso, False em caso de erro
    """
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Extrair dados da resposta
            previsao = resposta_api.get('previsao_atracacao', {})
            dados_completos = resposta_api.get('dados_completos_escala')
            
            # Converter dados_completos para JSON string
            dados_completos_json = None
            if dados_completos:
                try:
                    dados_completos_json = json.dumps(dados_completos, ensure_ascii=False)
                except:
                    pass
            
            # Converter resposta completa para JSON string
            resposta_json = json.dumps(resposta_api, ensure_ascii=False)
            
            # INSERT OR REPLACE
            cursor.execute('''
                INSERT OR REPLACE INTO previsao_atracacao_cache (
                    numero_ce, porto_destino, numero_manifesto, numero_escala,
                    data_previsao_atracacao, data_atracacao_real,
                    data_previsao_passe_saida, data_passe_saida,
                    data_inicio_operacao, data_fim_operacao,
                    situacao, terminal_atracacao, local_atracacao,
                    tipo_operacao, escala_encerrada, estrategia_usada,
                    dados_completos_escala, json_resposta_completa,
                    consultado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                numero_ce,
                resposta_api.get('porto_destino'),
                resposta_api.get('numero_manifesto'),
                resposta_api.get('numero_escala'),
                previsao.get('data_previsao_atracacao'),
                previsao.get('data_atracacao_real'),
                previsao.get('data_previsao_passe_saida'),
                previsao.get('data_passe_saida'),
                previsao.get('data_inicio_operacao'),
                previsao.get('data_fim_operacao'),
                previsao.get('situacao'),
                previsao.get('terminal_atracacao'),
                previsao.get('local_atracacao'),
                previsao.get('tipo_operacao'),
                1 if previsao.get('escala_encerrada') else 0,
                resposta_api.get('estrategia_usada'),
                dados_completos_json,
                resposta_json
            ))
            
            conn.commit()
            conn.close()
            
            logging.info(f'✅ Previsão de atracação para CE {numero_ce} salva no cache')
            return True
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao salvar previsão de atracação no cache (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao salvar previsão de atracação no cache: {e}')
            return False
    return False


def obter_previsao_atracacao_ce(numero_ce: str, ce_json: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Obtém previsão de atracação para um CE de forma leve (sem consultar API bilhetada).
    
    Esta função NÃO consulta a API bilhetada. Primeiro verifica o cache de previsão,
    depois tenta obter dados básicos do CE.
    
    Para obter previsão completa (consultando API), use o endpoint:
    GET /api/int/integracomex/ce/{numero_ce}/previsao-atracacao
    
    Args:
        numero_ce: Número do CE
        ce_json: JSON do CE (opcional, se não fornecido busca do cache)
    
    Returns:
        Dict com previsão de atracação ou None se não disponível:
        {
            'data_previsao_atracacao': str (ISO 8601),
            'data_atracacao_real': str (ISO 8601) ou None,
            'situacao_escala': str,
            'status_visual': str,  # "Aguardando", "Em trânsito", "Atracado", "Descargado"
            'terminal_atracacao': str,
            'local_atracacao': str,
            'tem_previsao': bool  # True se tem previsão, False se não tem
        }
    """
    try:
        # 1. Tentar buscar do cache de previsão primeiro (mais completo)
        previsao_cache = buscar_previsao_atracacao_cache(numero_ce, horas_validade=24)
        if previsao_cache:
            previsao = previsao_cache.get('json_resposta_completa', {}).get('previsao_atracacao', {})
            
            # Determinar status visual baseado na situação
            situacao = previsao.get('situacao', '')
            status_visual = None
            if situacao == 'DESCARREGADA' or previsao.get('escala_encerrada'):
                status_visual = 'Descargado'
            elif previsao.get('data_atracacao_real'):
                status_visual = 'Atracado'
            elif situacao == 'EM_TRANSITO':
                status_visual = 'Em trânsito'
            else:
                status_visual = 'Em trânsito'
            
            return {
                'tem_previsao': True,
                'status_visual': status_visual,
                'situacao_carga': situacao,
                'data_previsao_atracacao': previsao.get('data_previsao_atracacao'),
                'data_previsao_atracacao_formatada': previsao.get('data_previsao_atracacao_formatada'),
                'data_atracacao_real': previsao.get('data_atracacao_real'),
                'data_atracacao_real_formatada': previsao.get('data_atracacao_real_formatada'),
                'data_fim_operacao': previsao.get('data_fim_operacao'),
                'data_fim_operacao_formatada': previsao.get('data_fim_operacao_formatada'),
                'data_inicio_operacao': previsao.get('data_inicio_operacao'),
                'data_inicio_operacao_formatada': previsao.get('data_inicio_operacao_formatada'),
                'data_passe_saida': previsao.get('data_passe_saida'),
                'data_passe_saida_formatada': previsao.get('data_passe_saida_formatada'),
                'data_previsao_passe_saida': previsao.get('data_previsao_passe_saida'),
                'data_previsao_passe_saida_formatada': previsao.get('data_previsao_passe_saida_formatada'),
                'terminal_atracacao': previsao.get('terminal_atracacao'),
                'local_atracacao': previsao.get('local_atracacao'),
                'escala_encerrada_texto': previsao.get('escala_encerrada_texto'),
                'fonte': 'cache',
                'tem_cache': True,
                'mensagem': 'Previsão obtida do cache (economizou consultas bilhetadas)'
            }
        
        # 2. Se não tem no cache, buscar dados básicos do CE
        if ce_json is None:
            ce_cache = buscar_ce_cache(numero_ce)
            if ce_cache:
                ce_json = ce_cache.get('json_completo')
        
        if not ce_json:
            return None
        
        # Extrair dados básicos do CE
        porto_destino = ce_json.get('portoDestino')
        situacao_carga = ce_json.get('situacaoCarga', '')
        data_situacao_carga = ce_json.get('dataSituacaoCarga')
        
        # Determinar status visual baseado na situação
        status_visual = None
        if situacao_carga == 'DESCARREGADA':
            status_visual = 'Descargado'
        elif situacao_carga == 'EM_TRANSITO':
            status_visual = 'Em trânsito'
        elif situacao_carga in ['EMBARCADA', 'A_EMBARCAR']:
            status_visual = 'Aguardando'
        else:
            status_visual = 'Em trânsito'  # Default
        
        # Se não tem porto destino, não podemos obter previsão
        if not porto_destino:
            return {
                'tem_previsao': False,
                'status_visual': status_visual,
                'situacao_carga': situacao_carga
            }
        
        # Retornar dados básicos sem consultar API bilhetada
        return {
            'tem_previsao': False,  # Indica que precisa consultar API para obter previsão completa
            'status_visual': status_visual,
            'situacao_carga': situacao_carga,
            'porto_destino': porto_destino,
            'data_situacao_carga': data_situacao_carga,
            'mensagem': 'Clique para obter previsão de atracação',
            'fonte': 'ce_cache'
        }
    except Exception as e:
        import logging
        from datetime import timezone
        logging.warning(f'Erro ao obter previsão de atracação para CE {numero_ce}: {e}')
        return None

def obter_dados_documentos_processo(processo_referencia: str, usar_sql_server: bool = True) -> Dict[str, Any]:
    """Obtém dados agregados de todos os documentos (CE, CCT, DI, Rodoviário) de um processo.
    
    Args:
        processo_referencia: Número do processo
        usar_sql_server: Se True, busca do SQL Server quando não encontrar no cache. Se False, usa apenas cache (mais rápido, útil para listagens por categoria).
    
    Returns:
        Dict com dados agregados dos documentos:
        {
            'ces': [...],  # Lista de CEs com dados completos
            'ccts': [...], # Lista de CCTs com dados completos
            'dis': [...],  # Lista de DIs com dados completos (incluindo campos importantes)
            'rodoviarios': [...], # Lista de Rodoviários (futuro)
            'resumo': {
                'total_documentos': int,
                'ces_count': int,
                'ccts_count': int,
                'dis_count': int,
                'rodoviarios_count': int,
                'tem_bloqueios': bool,
                'situacoes': [...],
                'alertas': [...]
            }
        }
        
        Campos importantes da DI incluídos:
        - canal_selecao_parametrizada
        - data_hora_desembaraco
        - data_hora_registro
        - situacao_di
        - situacao_entrega_carga
        - numero_di
        - numero_protocolo
    """
    try:
        from services.documentos_processo_prep import (
            carregar_documentos_base,
            ordenar_documentos_e_identificar_di_prioritaria,
        )
        from services.ce_documento_handler import processar_documento_ce
        from services.cct_documento_handler import processar_documento_cct
        from services.di_documento_handler import processar_documento_di
        from services.duimp_documento_handler import buscar_duimps_vinculadas_ao_processo

        documentos, processo_sql_server_data = carregar_documentos_base(
            processo_referencia,
            listar_documentos_processo=listar_documentos_processo,
            usar_sql_server=usar_sql_server,
        )
        
        ces = []
        ccts = []
        dis = []  # ✅ DIs (Declarações de Importação)
        duimps = []  # ✅ DUIMPs (Declarações Únicas de Importação)
        rodoviarios = []
        alertas = []
        tem_bloqueios = False
        
        # ✅ CORREÇÃO: Processar CEs primeiro para obter di_numero antes de processar DIs
        # ✅ REGRA 1:1: Identificar DI prioritária do CE antes de processar DIs
        documentos_ordenados, di_prioritaria_do_ce = ordenar_documentos_e_identificar_di_prioritaria(
            processo_referencia,
            documentos,
            buscar_ce_cache=buscar_ce_cache,
        )
        
        for doc in documentos_ordenados:
            tipo = doc.get('tipo_documento', '')
            numero = doc.get('numero_documento', '')
            
            if tipo == 'CE':
                ce_data, alertas_ce, bloqueios_ce = processar_documento_ce(
                    processo_referencia,
                    numero,
                    buscar_ce_cache=buscar_ce_cache,
                    buscar_ce_itens_cache=buscar_ce_itens_cache,
                    obter_previsao_atracacao_ce=obter_previsao_atracacao_ce,
                    buscar_di_cache=buscar_di_cache,
                    obter_processo_por_documento=obter_processo_por_documento,
                    vincular_documento_processo=vincular_documento_processo,
                    processo_sql_server_data=processo_sql_server_data,
                )
                if ce_data:
                    ces.append(ce_data)
                if alertas_ce:
                    alertas.extend(alertas_ce)
                if bloqueios_ce:
                    tem_bloqueios = True
            
            elif tipo == 'CCT':
                cct_data, alertas_cct, bloqueios_cct = processar_documento_cct(
                    processo_referencia,
                    numero,
                    buscar_cct_cache=buscar_cct_cache,
                )
                if cct_data:
                    ccts.append(cct_data)
                if alertas_cct:
                    alertas.extend(alertas_cct)
                if bloqueios_cct:
                    tem_bloqueios = True
            
            elif tipo == 'DI':
                # ✅ REGRA 1:1 CRÍTICA: Um processo deve ter apenas uma DI, e essa DI deve estar vinculada ao CE
                # Priorizar a DI que está no documentoDespacho do CE (di_numero do CE)
                
                # 1. ✅ REGRA 1:1: Se já temos uma DI vinculada ao CE (di_prioritaria_do_ce), ignorar outras DIs
                if di_prioritaria_do_ce and di_prioritaria_do_ce != numero:
                    logging.debug(f'⚠️ Processo {processo_referencia}: DI {numero} ignorada (regra 1:1 - já existe DI {di_prioritaria_do_ce} vinculada ao CE)')
                    continue
                
                # 2. ✅ REGRA 1:1: Se já processamos uma DI anteriormente (na lista dis), ignorar esta
                if dis:
                    # Verificar se já temos uma DI na lista
                    logging.debug(f'⚠️ Processo {processo_referencia}: DI {numero} ignorada (regra 1:1 - já existe DI {dis[0].get("numero_di", "N/A")} processada)')
                    continue
                
                # 3. Verificar se esta DI está no documentoDespacho do CE (confirmação)
                di_no_ce = False
                ce_vinculado = None
                for ce in ces:
                    if ce.get('di_numero') == numero:
                        di_no_ce = True
                        ce_vinculado = ce.get("numero", "N/A")
                        logging.debug(f'✅ Processo {processo_referencia}: DI {numero} encontrada no documentoDespacho do CE {ce_vinculado} (PRIORIDADE)')
                        break
                
                # 4. Se não está no CE mas está na tabela processo_documentos, incluir (mas apenas se não há outra DI)
                if not di_no_ce:
                    logging.debug(f'ℹ️ Processo {processo_referencia}: DI {numero} vinculada ao processo (não está no documentoDespacho do CE, mas está na tabela processo_documentos)')
                di_data = processar_documento_di(
                    processo_referencia,
                    numero,
                    buscar_di_cache=buscar_di_cache,
                    usar_sql_server=usar_sql_server,
                    processo_sql_server_data=processo_sql_server_data,
                )
                if di_data:
                    dis.append(di_data)
        
        # ✅ NOVO: Buscar DUIMPs vinculadas ao processo (produção via CE/Kanban + validação vinculada)
        try:
            duimps = buscar_duimps_vinculadas_ao_processo(
                processo_referencia,
                ces,
                get_db_connection=get_db_connection,
            )
        except Exception as e:
            logging.warning(f'Erro ao buscar DUIMPs do processo {processo_referencia}: {e}')
        
        # Continuar processando RODOVIARIO no loop principal (já existe acima)
        
        # ✅ REMOVIDO: Busca de ShipsGo como fallback - usar apenas Kanban
        # Os dados de ETA/Porto/Navio/Status agora vêm apenas do Kanban (processos_kanban)
        shipsgo_data = None
        
        # Resumo
        resumo = {
            'total_documentos': len(documentos),
            'ces_count': len(ces),
            'ccts_count': len(ccts),
            'dis_count': len(dis),  # ✅ Contador de DIs
            'duimps_count': len(duimps),  # ✅ Contador de DUIMPs
            'rodoviarios_count': len(rodoviarios),
            'tem_bloqueios': tem_bloqueios,
            'situacoes': [],
            'alertas': alertas
        }
        
        # Coletar situações únicas
        situacoes_ce = [ce['situacao'] for ce in ces if ce.get('situacao')]
        situacoes_cct = [cct['situacao_atual'] for cct in ccts if cct.get('situacao_atual')]
        situacoes_di = [di['situacao_di'] for di in dis if di.get('situacao_di')]  # ✅ Situações de DI
        situacoes_duimp = [duimp['situacao_duimp'] for duimp in duimps if duimp.get('situacao_duimp')]  # ✅ Situações de DUIMP
        resumo['situacoes'] = list(set(situacoes_ce + situacoes_cct + situacoes_di + situacoes_duimp))
        
        return {
            'ces': ces,
            'ccts': ccts,
            'dis': dis,  # ✅ DIs incluídas no retorno
            'duimps': duimps,  # ✅ DUIMPs incluídas no retorno
            'rodoviarios': rodoviarios,
            'shipsgo': shipsgo_data,  # ✅ NOVO: Dados do ShipsGo (ETA/Porto)
            'resumo': resumo
        }
    except Exception as e:
        logging.error(f'Erro ao obter dados de documentos do processo: {e}')
        import traceback
        logging.error(traceback.format_exc())
        return {
            'ces': [],
            'ccts': [],
            'dis': [],
            'duimps': [],
            'rodoviarios': [],
            'shipsgo': None,  # ✅ CORREÇÃO: Incluir shipsgo mesmo em caso de erro
            'resumo': {
                'total_documentos': 0,
                'ces_count': 0,
                'ccts_count': 0,
                'dis_count': 0,
                'duimps_count': 0,
                'rodoviarios_count': 0,
                'tem_bloqueios': False,
                'situacoes': [],
                'alertas': []
            }
        }


# ✅ Função para gerar JSON consolidado do processo (estrutura completa para IA)
def gerar_json_consolidado_processo(processo_referencia: str) -> Dict[str, Any]:
    """
    Gera JSON consolidado completo de um processo, incluindo todos os documentos (CE, CCT, DI, DUIMP),
    valores, tributos, timeline, semântica, etc.
    
    Esta função consolida todos os dados do processo em um único JSON estruturado,
    facilitando consultas da IA e respostas enriquecidas.
    
    Args:
        processo_referencia: Número do processo (ex: "ALH.0165/25")
    
    Returns:
        Dict com estrutura consolidada do processo (similar ao exemplo fornecido)
    """
    try:
        from services.processo_consolidado_init import inicializar_json_consolidado
        from services.processo_consolidado_ce import processar_ces
        from services.processo_consolidado_cct import processar_ccts
        from services.processo_consolidado_di import processar_dis
        from services.processo_consolidado_duimp import processar_duimps_producao
        from services.processo_consolidado_finalize import finalizar_consolidado
        
        # 1. Obter dados dos documentos do processo
        dados_docs = obter_dados_documentos_processo(processo_referencia)
        
        # 2. Inicializar estrutura consolidada
        json_consolidado = inicializar_json_consolidado(processo_referencia)

        # 3. Processar CEs (Conhecimentos de Embarque Marítimo)
        ces = dados_docs.get('ces', [])
        processar_ces(json_consolidado, ces)

        # 4. Processar CCTs (Conhecimentos de Carga Aérea)
        ccts = dados_docs.get('ccts', [])
        processar_ccts(json_consolidado, ccts)
        
        # 5. Processar DIs (Declarações de Importação)
        dis = dados_docs.get('dis', [])
        processar_dis(json_consolidado, dis)
        
        # 6. Processar DUIMPs (Declarações Únicas de Importação)
        duimps = dados_docs.get('duimps', [])
        processar_duimps_producao(json_consolidado, duimps, processo_referencia=processo_referencia)

        finalizar_consolidado(json_consolidado, ces=ces, ccts=ccts)
        
        return json_consolidado
        
    except Exception as e:
        logging.error(f'Erro ao gerar JSON consolidado do processo {processo_referencia}: {e}')
        import traceback
        logging.error(traceback.format_exc())
        from datetime import datetime
        return {
            "meta": {
                "schema_version": "2.0",
                "id": processo_referencia,
                "closed": False,
                "last_updated": datetime.now().isoformat() + "Z"
            },
            "erro": str(e)
        }


# ✅ Funções para persistir estado do temporizador de monitoramento
def salvar_estado_temporizador(ativo: bool, intervalo_minutos: int, ultima_execucao: Optional[datetime] = None, 
                                proxima_execucao: Optional[datetime] = None, estatisticas: Optional[Dict[str, Any]] = None) -> bool:
    """Salva estado do temporizador no banco de dados."""
    for tentativa in range(SQLITE_RETRY_ATTEMPTS):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Converter estatísticas para JSON
            ultimo_resultado_json = None
            execucoes_total = 0
            execucoes_sucesso = 0
            execucoes_erro = 0
            
            if estatisticas:
                execucoes_total = estatisticas.get('execucoes_total', 0)
                execucoes_sucesso = estatisticas.get('execucoes_sucesso', 0)
                execucoes_erro = estatisticas.get('execucoes_erro', 0)
                ultimo_resultado = estatisticas.get('ultimo_resultado')
                if ultimo_resultado:
                    ultimo_resultado_json = json.dumps(ultimo_resultado, ensure_ascii=False, default=str)
            
            # Converter datas para ISO string
            ultima_execucao_str = ultima_execucao.isoformat() if ultima_execucao else None
            proxima_execucao_str = proxima_execucao.isoformat() if proxima_execucao else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO temporizador_monitoramento 
                (id, ativo, intervalo_minutos, ultima_execucao, proxima_execucao,
                 execucoes_total, execucoes_sucesso, execucoes_erro, ultimo_resultado, atualizado_em)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (1 if ativo else 0, intervalo_minutos, ultima_execucao_str, proxima_execucao_str,
                  execucoes_total, execucoes_sucesso, execucoes_erro, ultimo_resultado_json, datetime.now()))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.OperationalError as e:
            conn.close() if 'conn' in locals() else None
            if 'locked' in str(e).lower() and tentativa < SQLITE_RETRY_ATTEMPTS - 1:
                time.sleep(SQLITE_RETRY_DELAY * (tentativa + 1))
                continue
            logging.error(f'Erro ao salvar estado do temporizador (tentativa {tentativa + 1}): {e}')
            return False
        except Exception as e:
            conn.close() if 'conn' in locals() else None
            logging.error(f'Erro ao salvar estado do temporizador: {e}')
            return False
    return False


def restaurar_estado_temporizador() -> Optional[Dict[str, Any]]:
    """Restaura estado do temporizador do banco de dados."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ativo, intervalo_minutos, ultima_execucao, proxima_execucao,
                   execucoes_total, execucoes_sucesso, execucoes_erro, ultimo_resultado
            FROM temporizador_monitoramento
            WHERE id = 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        ativo, intervalo_minutos, ultima_execucao_str, proxima_execucao_str, \
        execucoes_total, execucoes_sucesso, execucoes_erro, ultimo_resultado_json = row
        
        # Converter datas de volta
        ultima_execucao = None
        if ultima_execucao_str:
            try:
                ultima_execucao = datetime.fromisoformat(ultima_execucao_str)
            except (ValueError, TypeError):
                pass
        
        proxima_execucao = None
        if proxima_execucao_str:
            try:
                proxima_execucao = datetime.fromisoformat(proxima_execucao_str)
            except (ValueError, TypeError):
                pass
        
        # Converter estatísticas
        ultimo_resultado = None
        if ultimo_resultado_json:
            try:
                ultimo_resultado = json.loads(ultimo_resultado_json)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return {
            'ativo': bool(ativo),
            'intervalo_minutos': intervalo_minutos or 60,
            'ultima_execucao': ultima_execucao,
            'proxima_execucao': proxima_execucao,
            'estatisticas': {
                'execucoes_total': execucoes_total or 0,
                'execucoes_sucesso': execucoes_sucesso or 0,
                'execucoes_erro': execucoes_erro or 0,
                'ultimo_resultado': ultimo_resultado
            }
        }
    except Exception as e:
        logging.error(f'Erro ao restaurar estado do temporizador: {e}')
        return None


# ========== RASTREAMENTO DE CONSULTAS BILHETADAS ==========

def registrar_consulta_bilhetada(
    tipo_consulta: str,
    endpoint: str,
    metodo: str = 'GET',
    status_code: Optional[int] = None,
    sucesso: bool = True,
    numero_documento: Optional[str] = None,
    processo_referencia: Optional[str] = None,
    usou_api_publica_antes: bool = False,
    observacoes: Optional[str] = None
) -> bool:
    """
    Registra uma consulta bilhetada no banco de dados.
    
    ⚠️ IMPORTANTE: Esta função verifica duplicatas antes de inserir para evitar
    race conditions quando múltiplas chamadas simultâneas tentam registrar a mesma consulta.
    
    Args:
        tipo_consulta: Tipo da consulta ('CE', 'DI', 'Manifesto', 'Escala', 'CCT')
        endpoint: Endpoint da API chamado
        metodo: Método HTTP (GET, POST, etc.)
        status_code: Código de status HTTP
        sucesso: Se a consulta foi bem-sucedida
        numero_documento: Número do documento consultado (opcional)
        processo_referencia: Processo relacionado (opcional)
        usou_api_publica_antes: Se verificou API pública antes da bilhetada
        observacoes: Observações adicionais (opcional)
    
    Returns:
        True se registrado com sucesso, False caso contrário (ou se já existe duplicata)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ✅ CORREÇÃO CRÍTICA: Verificar duplicata ANTES de inserir (prevenir race condition)
        # Verificar se já existe uma consulta idêntica nos últimos 10 segundos
        # ✅ Incluir CE_ITENS (consulta de itens é diferente de consulta de resumo)
        if tipo_consulta in ('CE', 'CE_ITENS', 'DI') and numero_documento:
            cursor.execute('''
                SELECT id FROM consultas_bilhetadas
                WHERE tipo_consulta = ?
                AND numero_documento = ?
                AND endpoint = ?
                AND data_consulta >= datetime('now', '-10 seconds')
                AND sucesso = 1
                LIMIT 1
            ''', (tipo_consulta, numero_documento, endpoint))
            duplicata = cursor.fetchone()
            
            if duplicata:
                # Já existe uma consulta idêntica muito recente - não inserir duplicata
                logging.info(f'⚠️ Consulta bilhetada duplicada detectada e ignorada: {tipo_consulta} {numero_documento} (já registrada nos últimos 10 segundos)')
                conn.close()
                return False  # Retornar False indica que não foi registrado (já existe)
        
        cursor.execute('''
            INSERT INTO consultas_bilhetadas 
            (tipo_consulta, numero_documento, endpoint, metodo, status_code, sucesso, 
             processo_referencia, usou_api_publica_antes, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tipo_consulta, numero_documento, endpoint, metodo, status_code, 
              sucesso, processo_referencia, usou_api_publica_antes, observacoes))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f'Erro ao registrar consulta bilhetada: {e}')
        if 'conn' in locals():
            conn.close()
        return False


def obter_ultimas_consultas_processo(processo_referencia: str) -> Dict[str, Any]:
    """
    Obtém informações sobre as últimas consultas (pública e bilhetada) de CE e DI para um processo.
    
    Args:
        processo_referencia: Número do processo
    
    Returns:
        Dict com:
        {
            'ce': {
                'ultima_publica': str ou None,  # Data da última atualização da API pública
                'ultima_bilhetada': str ou None  # Data da última consulta bilhetada
            },
            'di': {
                'ultima_publica': str ou None,
                'ultima_bilhetada': str ou None
            }
        }
    """
    resultado = {
        'ce': {'ultima_publica': None, 'ultima_bilhetada': None},
        'di': {'ultima_publica': None, 'ultima_bilhetada': None}
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        # Buscar CEs do processo
        cursor.execute('''
            SELECT numero_documento FROM processo_documentos
            WHERE processo_referencia = ? AND tipo_documento = 'CE'
            LIMIT 1
        ''', (processo_referencia,))
        ce_row = cursor.fetchone()
        
        if ce_row:
            numero_ce = ce_row['numero_documento']
            
            # Buscar última atualização pública do CE (do cache)
            cursor.execute('''
                SELECT ultima_alteracao_api FROM ces_cache
                WHERE numero_ce = ?
            ''', (numero_ce,))
            ce_cache_row = cursor.fetchone()
            if ce_cache_row and ce_cache_row['ultima_alteracao_api']:
                resultado['ce']['ultima_publica'] = ce_cache_row['ultima_alteracao_api']
            
            # Buscar última consulta bilhetada do CE
            cursor.execute('''
                SELECT MAX(data_consulta) as ultima_consulta FROM consultas_bilhetadas
                WHERE tipo_consulta = 'CE' AND numero_documento = ? AND sucesso = 1
            ''', (numero_ce,))
            ce_bilhetada_row = cursor.fetchone()
            if ce_bilhetada_row and ce_bilhetada_row['ultima_consulta']:
                resultado['ce']['ultima_bilhetada'] = ce_bilhetada_row['ultima_consulta']
        
        # Buscar DIs do processo
        cursor.execute('''
            SELECT numero_documento FROM processo_documentos
            WHERE processo_referencia = ? AND tipo_documento = 'DI'
            LIMIT 1
        ''', (processo_referencia,))
        di_row = cursor.fetchone()
        
        if di_row:
            numero_di = di_row['numero_documento']
            
            # ✅ Para DI, buscar a última consulta bilhetada que usou API pública antes
            # Isso indica quando foi a última vez que verificamos a API pública (gratuita) antes de consultar bilhetada
            # NOTA: Não rastreamos verificações públicas que não resultam em consulta bilhetada
            # para evitar duplicatas e poluição da tabela consultas_bilhetadas
            cursor.execute('''
                SELECT MAX(data_consulta) as ultima_consulta FROM consultas_bilhetadas
                WHERE tipo_consulta = 'DI' AND numero_documento = ? 
                AND usou_api_publica_antes = 1 AND sucesso = 1
            ''', (numero_di,))
            di_publica_row = cursor.fetchone()
            if di_publica_row and di_publica_row['ultima_consulta']:
                # A data da consulta bilhetada que usou API pública antes indica
                # quando foi a última vez que verificamos a API pública (gratuita) antes de consultar bilhetada
                resultado['di']['ultima_publica'] = di_publica_row['ultima_consulta']
            
            # Buscar última consulta bilhetada do DI
            cursor.execute('''
                SELECT MAX(data_consulta) as ultima_consulta FROM consultas_bilhetadas
                WHERE tipo_consulta = 'DI' AND numero_documento = ? AND sucesso = 1
            ''', (numero_di,))
            di_bilhetada_row = cursor.fetchone()
            if di_bilhetada_row and di_bilhetada_row['ultima_consulta']:
                resultado['di']['ultima_bilhetada'] = di_bilhetada_row['ultima_consulta']
        
        conn.close()
    except Exception as e:
        logging.warning(f'Erro ao obter últimas consultas do processo {processo_referencia}: {e}')
        try:
            conn.close()
        except:
            pass
    
    return resultado


def obter_estatisticas_consultas_bilhetadas(
    tipo_consulta: Optional[str] = None,
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    processo_referencia: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtém estatísticas de consultas bilhetadas.
    
    Args:
        tipo_consulta: Filtrar por tipo ('CE', 'DI', 'Manifesto', 'Escala', 'CCT')
        data_inicio: Data inicial (opcional)
        data_fim: Data final (opcional)
        processo_referencia: Filtrar por processo (opcional)
    
    Returns:
        Dict com estatísticas:
        {
            'total': int,
            'por_tipo': Dict[str, int],
            'com_api_publica': int,
            'sem_api_publica': int,
            'sucesso': int,
            'erro': int,
            'por_dia': List[Dict],
            'ultimas_consultas': List[Dict]
        }
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        # Construir query base
        where_clauses = []
        params = []
        
        if tipo_consulta:
            where_clauses.append('tipo_consulta = ?')
            params.append(tipo_consulta)
        
        if data_inicio:
            where_clauses.append('data_consulta >= ?')
            params.append(data_inicio.isoformat())
        
        if data_fim:
            where_clauses.append('data_consulta <= ?')
            params.append(data_fim.isoformat())
        
        if processo_referencia:
            where_clauses.append('processo_referencia = ?')
            params.append(processo_referencia)
        
        where_sql = ' WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        # Total de consultas
        cursor.execute(f'SELECT COUNT(*) as total FROM consultas_bilhetadas{where_sql}', params)
        total = cursor.fetchone()['total']
        
        # Por tipo
        cursor.execute(f'''
            SELECT tipo_consulta, COUNT(*) as count 
            FROM consultas_bilhetadas{where_sql}
            GROUP BY tipo_consulta
        ''', params)
        por_tipo = {row['tipo_consulta']: row['count'] for row in cursor.fetchall()}
        
        # ✅ CORREÇÃO CRÍTICA: Todas as consultas na tabela consultas_bilhetadas SÃO bilhetadas
        # O flag usou_api_publica_antes apenas indica se verificou API pública ANTES de bilhetar
        # NÃO indica se foi bilhetada ou não - TODAS foram bilhetadas
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_bilhetadas,
                SUM(CASE WHEN usou_api_publica_antes = 1 THEN 1 ELSE 0 END) as com_api_publica_antes,
                SUM(CASE WHEN usou_api_publica_antes = 0 THEN 1 ELSE 0 END) as sem_api_publica_antes
            FROM consultas_bilhetadas{where_sql}
        ''', params)
        row = cursor.fetchone()
        total_bilhetadas = row['total_bilhetadas'] or 0  # ✅ Todas são bilhetadas
        com_api_publica_antes = row['com_api_publica_antes'] or 0  # ✅ Verificaram API pública antes de bilhetar
        sem_api_publica_antes = row['sem_api_publica_antes'] or 0  # ✅ Bilhetaram direto (sem verificar API pública antes)
        
        # ✅ Mantendo compatibilidade com código existente
        com_api_publica = com_api_publica_antes
        sem_api_publica = sem_api_publica_antes
        
        # Sucesso/erro
        cursor.execute(f'''
            SELECT 
                SUM(CASE WHEN sucesso = 1 THEN 1 ELSE 0 END) as sucesso,
                SUM(CASE WHEN sucesso = 0 THEN 1 ELSE 0 END) as erro
            FROM consultas_bilhetadas{where_sql}
        ''', params)
        row = cursor.fetchone()
        sucesso_count = row['sucesso'] or 0
        erro_count = row['erro'] or 0
        
        # Por dia (SQLite usa date() ou strftime())
        cursor.execute(f'''
            SELECT 
                date(data_consulta) as dia,
                COUNT(*) as count,
                SUM(CASE WHEN usou_api_publica_antes = 1 THEN 1 ELSE 0 END) as com_api_publica
            FROM consultas_bilhetadas{where_sql}
            GROUP BY date(data_consulta)
            ORDER BY dia DESC
            LIMIT 30
        ''', params)
        por_dia = [dict(row) for row in cursor.fetchall()]
        
        # Últimas consultas
        cursor.execute(f'''
            SELECT * FROM consultas_bilhetadas{where_sql}
            ORDER BY data_consulta DESC
            LIMIT 50
        ''', params)
        ultimas_consultas = [dict(row) for row in cursor.fetchall()]
        
        # Por documento (top 10 mais consultados)
        cursor.execute(f'''
            SELECT 
                tipo_consulta,
                numero_documento,
                COUNT(*) as total,
                MAX(data_consulta) as ultima_consulta
            FROM consultas_bilhetadas{where_sql}
            WHERE numero_documento IS NOT NULL AND numero_documento != ''
            GROUP BY tipo_consulta, numero_documento
            ORDER BY total DESC
            LIMIT 10
        ''', params)
        por_documento = [dict(row) for row in cursor.fetchall()]
        
        # Por processo (se houver processo_referencia)
        cursor.execute(f'''
            SELECT 
                processo_referencia,
                COUNT(*) as total
            FROM consultas_bilhetadas{where_sql}
            WHERE processo_referencia IS NOT NULL AND processo_referencia != ''
            GROUP BY processo_referencia
            ORDER BY total DESC
            LIMIT 20
        ''', params)
        por_processo = [dict(row) for row in cursor.fetchall()]
        
        # ✅ NOVO: Estimar consultas evitadas (API pública + cache)
        # Contar CEs e CCTs no cache que têm ultima_alteracao_api (foram verificados pela API pública)
        consultas_evitadas_ce = 0
        consultas_evitadas_cct = 0
        
        try:
            # CEs no cache com verificação de API pública
            cursor.execute('''
                SELECT COUNT(*) as total
                FROM ces_cache
                WHERE ultima_alteracao_api IS NOT NULL
            ''')
            row = cursor.fetchone()
            consultas_evitadas_ce = row['total'] if row else 0
            
            # CCTs no cache (não há API pública para CCT, mas cache evita consultas)
            cursor.execute('''
                SELECT COUNT(*) as total
                FROM ccts_cache
            ''')
            row = cursor.fetchone()
            consultas_evitadas_cct = row['total'] if row else 0
        except Exception as e:
            logging.warning(f'Erro ao contar consultas evitadas: {e}')
        
        consultas_evitadas_total = consultas_evitadas_ce + consultas_evitadas_cct
        
        conn.close()
        
        return {
            'total': total,
            'total_consultas': total,  # Alias para compatibilidade
            'total_bilhetadas': total_bilhetadas,  # ✅ NOVO: Total de consultas bilhetadas (todas na tabela são bilhetadas)
            'por_tipo': por_tipo,
            'com_api_publica': com_api_publica,  # ✅ Mantém compatibilidade: consultas que verificaram API pública antes de bilhetar
            'sem_api_publica': sem_api_publica,  # ✅ Mantém compatibilidade: consultas que bilhetaram direto (sem verificar API pública antes)
            'com_api_publica_antes': com_api_publica_antes,  # ✅ NOVO: Nome mais claro - verificaram API pública ANTES de bilhetar
            'sem_api_publica_antes': sem_api_publica_antes,  # ✅ NOVO: Nome mais claro - bilhetaram direto sem verificar API pública antes
            'sucesso': sucesso_count,
            'erro': erro_count,
            'por_dia': por_dia,
            'por_documento': por_documento,
            'por_processo': por_processo,
            'ultimas_consultas': ultimas_consultas,
            # ✅ NOVO: Consultas evitadas (estimativa baseada em cache)
            'consultas_evitadas': {
                'total': consultas_evitadas_total,
                'ce': consultas_evitadas_ce,
                'cct': consultas_evitadas_cct
            },
            # ✅ NOVO: Informação crítica sobre todas as consultas serem bilhetadas
            'observacao': '⚠️ IMPORTANTE: Todas as consultas nesta tabela foram BILHETADAS. O flag "usou_api_publica_antes" indica apenas se a API pública foi verificada ANTES de bilhetar, não se foi bilhetada ou não.'
        }
    except Exception as e:
        logging.error(f'Erro ao obter estatísticas de consultas bilhetadas: {e}')
        if 'conn' in locals():
            conn.close()
        return {
            'total': 0,
            'total_consultas': 0,
            'por_tipo': {},
            'com_api_publica': 0,
            'sem_api_publica': 0,
            'sucesso': 0,
            'erro': 0,
            'por_dia': [],
            'por_documento': [],
            'por_processo': [],
            'ultimas_consultas': []
        }


# =============================================================================
# FUNÇÕES DE ALERTAS PROATIVOS DO CHAT IA
# =============================================================================

def criar_alerta_chat(
    tipo: str,
    mensagem: str,
    processo_referencia: Optional[str] = None,
    documento_tipo: Optional[str] = None,
    documento_numero: Optional[str] = None,
    nivel: str = 'info'
) -> Optional[int]:
    """
    Cria um alerta proativo para o chat IA.
    
    Args:
        tipo: Tipo do alerta ('bloqueio', 'pendencia_frete', 'pendencia_afrmm', 'situacao_mudou', etc)
        mensagem: Mensagem gerada pela IA para o usuário
        processo_referencia: Referência do processo (opcional)
        documento_tipo: Tipo do documento ('CE', 'CCT', 'DI', 'DUIMP') (opcional)
        documento_numero: Número do documento (opcional)
        nivel: Nível do alerta ('info', 'warning', 'error', 'success')
    
    Returns:
        ID do alerta criado ou None se erro
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ✅ SCHEMA EXTRAÍDO (19/01/2026): chat_alertas
        _criar_tabela_chat_alertas(cursor)
        conn.commit()
        
        # ✅ CORREÇÃO CRÍTICA: Verificar duplicata ANTES de inserir (evita race condition)
        # Verificar se já existe alerta idêntico nos últimos 5 minutos
        # ✅ MELHORIA: Para alertas de situação, verificar também se a mensagem contém a mesma situação final
        # Construir query dinamicamente para lidar com valores None
        query_conditions = ['tipo = ?', 'criado_em >= datetime(\'now\', \'-5 minutes\')']
        query_params = [tipo]
        
        if processo_referencia:
            query_conditions.append('processo_referencia = ?')
            query_params.append(processo_referencia)
        else:
            query_conditions.append('processo_referencia IS NULL')
        
        if documento_numero:
            query_conditions.append('documento_numero = ?')
            query_params.append(documento_numero)
        else:
            query_conditions.append('documento_numero IS NULL')
        
        # ✅ MELHORIA: Para alertas de situação, verificar também se a mensagem contém a mesma situação
        # Isso evita duplicatas quando a mesma mudança é detectada múltiplas vezes
        if tipo == 'situacao_mudou' and mensagem:
            # Extrair situação final da mensagem (ex: "DESCARREGADA")
            import re
            # Tentar encontrar situação em maiúsculas na mensagem
            match_situacao = re.search(r'\b([A-Z_]{5,})\b', mensagem)
            if match_situacao:
                situacao_final = match_situacao.group(1)
                # Verificar se a mensagem contém essa situação
                query_conditions.append('mensagem LIKE ?')
                query_params.append(f'%{situacao_final}%')
        
        query = f'''
            SELECT id FROM chat_alertas
            WHERE {' AND '.join(query_conditions)}
            LIMIT 1
        '''
        
        cursor.execute(query, query_params)
        alerta_existente = cursor.fetchone()
        
        if alerta_existente:
            # Alerta duplicado encontrado - retornar ID do alerta existente
            alerta_id = alerta_existente[0]
            conn.close()
            logging.info(f'⚠️ Alerta duplicado detectado: {tipo} para processo {processo_referencia} documento {documento_numero} (ID existente: {alerta_id})')
            return alerta_id
        
        # Não existe duplicata - inserir novo alerta
        cursor.execute('''
            INSERT INTO chat_alertas 
            (tipo, processo_referencia, documento_tipo, documento_numero, mensagem, nivel)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tipo, processo_referencia, documento_tipo, documento_numero, mensagem, nivel))
        
        alerta_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logging.info(f'✅ Alerta do chat criado: {tipo} para processo {processo_referencia} (ID: {alerta_id})')
        return alerta_id
    except Exception as e:
        logging.error(f'Erro ao criar alerta do chat: {e}')
        if 'conn' in locals():
            conn.close()
        return None


def buscar_alertas_chat_pendentes(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Busca alertas do chat que ainda não foram lidos.
    
    Args:
        limit: Limite de alertas a retornar
    
    Returns:
        Lista de alertas pendentes ordenados por data (mais recente primeiro)
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM chat_alertas
            WHERE lido = 0
            ORDER BY criado_em DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        alertas = []
        for row in rows:
            alertas.append({
                'id': row['id'],
                'tipo': row['tipo'],
                'processo_referencia': row['processo_referencia'],
                'documento_tipo': row['documento_tipo'],
                'documento_numero': row['documento_numero'],
                'mensagem': row['mensagem'],
                'nivel': row['nivel'],
                'lido': bool(row['lido']),
                'criado_em': row['criado_em'],
                'lido_em': row['lido_em']
            })
        
        return alertas
    except Exception as e:
        logging.error(f'Erro ao buscar alertas do chat: {e}')
        if 'conn' in locals():
            conn.close()
        return []


def marcar_alerta_chat_lido(alerta_id: int) -> bool:
    """
    Marca um alerta do chat como lido.
    
    Args:
        alerta_id: ID do alerta
    
    Returns:
        True se marcou com sucesso, False caso contrário
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE chat_alertas
            SET lido = 1, lido_em = ?
            WHERE id = ?
        ''', (datetime.now(), alerta_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logging.debug(f'✅ Alerta {alerta_id} marcado como lido')
            return True
        else:
            logging.warning(f'⚠️ Alerta {alerta_id} não encontrado')
            return False
    except Exception as e:
        logging.error(f'Erro ao marcar alerta como lido: {e}')
        if 'conn' in locals():
            conn.close()
        return False


        alertas = []
        for row in rows:
            alertas.append({
                'id': row['id'],
                'tipo': row['tipo'],
                'processo_referencia': row['processo_referencia'],
                'documento_tipo': row['documento_tipo'],
                'documento_numero': row['documento_numero'],
                'mensagem': row['mensagem'],
                'nivel': row['nivel'],
                'lido': bool(row['lido']),
                'criado_em': row['criado_em'],
                'lido_em': row['lido_em']
            })
        
        return alertas
    except Exception as e:
        logging.error(f'Erro ao buscar alertas do chat: {e}')
        if 'conn' in locals():
            conn.close()
        return []


def marcar_alerta_chat_lido(alerta_id: int) -> bool:
    """
    Marca um alerta do chat como lido.
    
    Args:
        alerta_id: ID do alerta
    
    Returns:
        True se marcou com sucesso, False caso contrário
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE chat_alertas
            SET lido = 1, lido_em = ?
            WHERE id = ?
        ''', (datetime.now(), alerta_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            logging.debug(f'✅ Alerta {alerta_id} marcado como lido')
            return True
        else:
            logging.warning(f'⚠️ Alerta {alerta_id} não encontrado')
            return False
    except Exception as e:
        logging.error(f'Erro ao marcar alerta como lido: {e}')
        if 'conn' in locals():
            conn.close()
        return False



# ============================================================================
# Funções para gerenciar fila de consultas bilhetadas pendentes de aprovação
# ============================================================================

def adicionar_consulta_pendente(
    tipo_consulta: str,
    numero_documento: str,
    endpoint: str,
    processo_referencia: Optional[str] = None,
    motivo: Optional[str] = None,
    data_publica_verificada: Optional[datetime] = None,
    data_ultima_alteracao_cache: Optional[datetime] = None,
    observacoes: Optional[str] = None
) -> Optional[int]:
    """
    Adiciona uma consulta bilhetada à fila de pendências para aprovação manual.
    
    Args:
        tipo_consulta: Tipo da consulta ('CE', 'DI', etc.)
        numero_documento: Número do documento
        endpoint: Endpoint da API
        processo_referencia: Número do processo (opcional)
        motivo: Motivo da consulta (ex: "API pública indica mudança")
        data_publica_verificada: Data da última verificação na API pública
        data_ultima_alteracao_cache: Data da última alteração no cache
        observacoes: Observações adicionais
    
    Returns:
        ID da consulta pendente criada ou None em caso de erro
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se já existe uma consulta pendente idêntica
        cursor.execute('''
            SELECT id FROM consultas_bilhetadas_pendentes
            WHERE tipo_consulta = ? AND numero_documento = ? AND status = 'pendente'
        ''', (tipo_consulta, numero_documento))
        existente = cursor.fetchone()
        
        if existente:
            # Já existe uma consulta pendente para este documento
            logging.debug(f'⚠️ Consulta pendente já existe para {tipo_consulta} {numero_documento}')
            conn.close()
            return existente[0]
        
        # Inserir nova consulta pendente
        cursor.execute('''
            INSERT INTO consultas_bilhetadas_pendentes
            (tipo_consulta, numero_documento, endpoint, metodo, processo_referencia,
             motivo, data_publica_verificada, data_ultima_alteracao_cache, observacoes)
            VALUES (?, ?, ?, 'GET', ?, ?, ?, ?, ?)
        ''', (
            tipo_consulta,
            numero_documento,
            endpoint,
            processo_referencia,
            motivo,
            data_publica_verificada.isoformat() if data_publica_verificada else None,
            data_ultima_alteracao_cache.isoformat() if data_ultima_alteracao_cache else None,
            observacoes
        ))
        
        consulta_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logging.info(f'✅ Consulta pendente adicionada: {tipo_consulta} {numero_documento} (ID: {consulta_id})')
        return consulta_id
    except Exception as e:
        logging.error(f'Erro ao adicionar consulta pendente: {e}')
        if 'conn' in locals():
            conn.close()
        return None


def listar_consultas_pendentes(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Lista consultas bilhetadas pendentes de aprovação.
    
    Args:
        status: Filtrar por status ('pendente', 'aprovado', 'rejeitado', 'executado')
        limit: Limite de resultados
    
    Returns:
        Lista de consultas pendentes
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute('''
                SELECT * FROM consultas_bilhetadas_pendentes
                WHERE status = ?
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (status, limit))
        else:
            cursor.execute('''
                SELECT * FROM consultas_bilhetadas_pendentes
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f'Erro ao listar consultas pendentes: {e}')
        if 'conn' in locals():
            conn.close()
        return []


def aprovar_consultas_pendentes(ids: List[int], aprovado_por: str = 'usuario') -> Dict[str, Any]:
    """
    Aprova múltiplas consultas pendentes para execução.
    
    Args:
        ids: Lista de IDs das consultas a aprovar
        aprovado_por: Nome do usuário que aprovou
    
    Returns:
        Dict com estatísticas da aprovação
    """
    resultado = {
        'aprovadas': 0,
        'erros': []
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for consulta_id in ids:
            try:
                # ✅ CRÍTICO: Verificar status atual antes de aprovar
                cursor.execute('SELECT status FROM consultas_bilhetadas_pendentes WHERE id = ?', (consulta_id,))
                row = cursor.fetchone()
                
                if not row:
                    resultado['erros'].append(f'Consulta {consulta_id} não encontrada')
                    continue
                
                status_atual = row[0]
                
                # ✅ CRÍTICO: Só pode aprovar se estiver pendente
                # Se já foi rejeitada, não pode aprovar
                if status_atual != 'pendente':
                    resultado['erros'].append(f'Consulta {consulta_id} não pode ser aprovada (status atual: {status_atual})')
                    logging.warning(f'⚠️ Tentativa de aprovar consulta {consulta_id} com status {status_atual} (deve ser "pendente")')
                    continue
                
                # ✅ LOCK: Verificar se já está sendo processada (timeout de 5 minutos)
                cursor.execute('SELECT processando_aprovacao FROM consultas_bilhetadas_pendentes WHERE id = ?', (consulta_id,))
                row_processando = cursor.fetchone()
                if row_processando and row_processando[0]:
                    try:
                        dt_processando_str = row_processando[0]
                        # Tentar parsear com timezone
                        if 'Z' in dt_processando_str or '+' in dt_processando_str or dt_processando_str.count('-') > 2:
                            dt_processando = datetime.fromisoformat(dt_processando_str.replace('Z', '+00:00'))
                            dt_processando_naive = dt_processando.replace(tzinfo=None) if dt_processando.tzinfo else dt_processando
                        else:
                            dt_processando_naive = datetime.fromisoformat(dt_processando_str)
                        
                        tempo_decorrido = (datetime.now() - dt_processando_naive).total_seconds()
                        if tempo_decorrido < 300:  # 5 minutos
                            resultado['erros'].append(f'Consulta {consulta_id} já está sendo processada')
                            logging.warning(f'⚠️ Consulta {consulta_id} já está sendo processada (iniciado há {tempo_decorrido:.0f}s)')
                            continue
                        else:
                            # Timeout - limpar lock
                            logging.warning(f'⚠️ Consulta {consulta_id} tinha lock expirado, limpando...')
                    except Exception as e:
                        logging.debug(f'Erro ao verificar lock da consulta {consulta_id}: {e}')
                        pass  # Se erro ao parsear, continuar
                
                # ✅ LOCK: Marcar como processando
                cursor.execute('''
                    UPDATE consultas_bilhetadas_pendentes
                    SET processando_aprovacao = ?
                    WHERE id = ? AND status = 'pendente'
                ''', (datetime.now().isoformat(), consulta_id))
                
                if cursor.rowcount == 0:
                    resultado['erros'].append(f'Consulta {consulta_id} não encontrada ou já processada')
                    continue
                
                cursor.execute('''
                    UPDATE consultas_bilhetadas_pendentes
                    SET status = 'aprovado',
                        aprovado_em = ?,
                        aprovado_por = ?,
                        processando_aprovacao = NULL
                    WHERE id = ? AND status = 'pendente'
                ''', (datetime.now().isoformat(), aprovado_por, consulta_id))
                
                if cursor.rowcount > 0:
                    resultado['aprovadas'] += 1
                    logging.info(f'✅ Consulta {consulta_id} aprovada por {aprovado_por}')
                else:
                    resultado['erros'].append(f'Consulta {consulta_id} não encontrada ou já processada')
            except Exception as e:
                resultado['erros'].append(f'Erro ao aprovar consulta {consulta_id}: {e}')
        
        conn.commit()
        conn.close()
        
        return resultado
    except Exception as e:
        logging.error(f'Erro ao aprovar consultas: {e}')
        if 'conn' in locals():
            conn.close()
        resultado['erros'].append(f'Erro geral: {e}')
        return resultado


def rejeitar_consultas_pendentes(ids: List[int], motivo: Optional[str] = None) -> Dict[str, Any]:
    """
    Rejeita múltiplas consultas pendentes.
    
    Args:
        ids: Lista de IDs das consultas a rejeitar
        motivo: Motivo da rejeição
    
    Returns:
        Dict com estatísticas da rejeição
    """
    resultado = {
        'rejeitadas': 0,
        'erros': []
    }
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for consulta_id in ids:
            try:
                # ✅ CRÍTICO: Verificar status atual antes de rejeitar
                cursor.execute('SELECT status FROM consultas_bilhetadas_pendentes WHERE id = ?', (consulta_id,))
                row = cursor.fetchone()
                
                if not row:
                    resultado['erros'].append(f'Consulta {consulta_id} não encontrada')
                    continue
                
                status_atual = row[0]
                
                # ✅ CRÍTICO: Só pode rejeitar se estiver pendente
                # Se já foi aprovada ou executada, não pode rejeitar
                if status_atual != 'pendente':
                    resultado['erros'].append(f'Consulta {consulta_id} não pode ser rejeitada (status atual: {status_atual})')
                    logging.warning(f'⚠️ Tentativa de rejeitar consulta {consulta_id} com status {status_atual} (deve ser "pendente")')
                    continue
                
                cursor.execute('''
                    UPDATE consultas_bilhetadas_pendentes
                    SET status = 'rejeitado',
                        observacoes = COALESCE(observacoes || '\n' || ?, ?)
                    WHERE id = ? AND status = 'pendente'
                ''', (f'Rejeitado: {motivo}' if motivo else 'Rejeitado pelo usuário', motivo, consulta_id))
                
                if cursor.rowcount > 0:
                    resultado['rejeitadas'] += 1
                    logging.info(f'✅ Consulta {consulta_id} rejeitada')
                else:
                    resultado['erros'].append(f'Consulta {consulta_id} não encontrada ou já processada')
            except Exception as e:
                resultado['erros'].append(f'Erro ao rejeitar consulta {consulta_id}: {e}')
        
        conn.commit()
        conn.close()
        
        return resultado
    except Exception as e:
        logging.error(f'Erro ao rejeitar consultas: {e}')
        if 'conn' in locals():
            conn.close()
        resultado['erros'].append(f'Erro geral: {e}')
        return resultado


def contar_consultas_pendentes() -> Dict[str, int]:
    """
    Conta consultas pendentes por status.
    
    Returns:
        Dict com contagem por status
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) as total
            FROM consultas_bilhetadas_pendentes
            GROUP BY status
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        resultado = {'pendente': 0, 'aprovado': 0, 'rejeitado': 0, 'executado': 0}
        for row in rows:
            status = row[0]
            total = row[1]
            if status in resultado:
                resultado[status] = total
        
        return resultado
    except Exception as e:
        logging.error(f'Erro ao contar consultas pendentes: {e}')
        if 'conn' in locals():
            conn.close()
        return {'pendente': 0, 'aprovado': 0, 'rejeitado': 0, 'executado': 0}


# ============================================================================
# NESH - Nomenclatura Estatística SH (Notas Explicativas)
# ============================================================================

# Cache global para NESH (carregado sob demanda)
_NESH_CACHE: Optional[List[Dict[str, Any]]] = None
_NESH_LOADED = False
_NESH_SQLITE_READY: Optional[bool] = None


def _nesh_sqlite_ready() -> bool:
    """
    Verifica se a tabela `nesh_chunks` existe e tem dados.

    Cache em memória para evitar bater no SQLite toda hora.
    """
    global _NESH_SQLITE_READY
    if _NESH_SQLITE_READY is not None:
        return _NESH_SQLITE_READY
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='nesh_chunks' LIMIT 1"
        )
        if not cursor.fetchone():
            conn.close()
            _NESH_SQLITE_READY = False
            return False
        cursor.execute("SELECT COUNT(1) FROM nesh_chunks")
        total = cursor.fetchone()[0]
        conn.close()
        _NESH_SQLITE_READY = bool(total and int(total) > 0)
        return _NESH_SQLITE_READY
    except Exception:
        _NESH_SQLITE_READY = False
        return False


def _normalizar_codigo_nesh(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return str(code).strip().replace(".", "").replace("-", "").replace(" ", "")


def _nesh_row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "section": row["section"],
        "chapter": row["chapter"],
        "chapter_code": row["chapter_code"],
        "chapter_title": row["chapter_title"],
        "position_code": row["position_code"],
        "position_title": row["position_title"],
        "subposition_code": row["subposition_code"],
        "subposition_title": row["subposition_title"],
        "text": row["text"],
        # ✅ Extra (compat): permite mostrar "fonte" no rodapé da resposta
        "_nesh_source": "SQLITE",
    }

def _carregar_nesh_cache() -> List[Dict[str, Any]]:
    """
    Carrega o arquivo NESH em cache (lazy loading).
    
    Returns:
        Lista de registros NESH
    """
    global _NESH_CACHE, _NESH_LOADED
    
    if _NESH_LOADED and _NESH_CACHE is not None:
        return _NESH_CACHE
    
    try:
        # ✅ Configurável via ENV (permite mover arquivo para fora do workspace)
        from services.path_config import get_nesh_chunks_path
        nesh_path = get_nesh_chunks_path()
        if not nesh_path.exists():
            logging.warning('⚠️ Arquivo nesh_chunks.json não encontrado')
            _NESH_CACHE = []
            _NESH_LOADED = True
            return _NESH_CACHE
        
        logging.info('📚 Carregando arquivo NESH...')
        with open(nesh_path, 'r', encoding='utf-8') as f:
            _NESH_CACHE = json.load(f)
        
        _NESH_LOADED = True
        logging.info(f'✅ NESH carregado: {len(_NESH_CACHE)} registros')
        return _NESH_CACHE
    except Exception as e:
        logging.error(f'❌ Erro ao carregar NESH: {e}')
        _NESH_CACHE = []
        _NESH_LOADED = True
        return _NESH_CACHE

def buscar_nota_explicativa_nesh_por_ncm(ncm: str) -> Optional[Dict[str, Any]]:
    """
    Busca nota explicativa NESH por código NCM.
    
    Args:
        ncm: Código NCM (4, 6 ou 8 dígitos, com ou sem pontos)
    
    Returns:
        Dict com nota explicativa ou None se não encontrado
    """
    try:
        log_source = str(os.getenv("NESH_LOG_SOURCE", "false")).strip().lower() in ("1", "true", "yes", "y", "on")

        # Normalizar NCM (remover pontos, espaços)
        ncm_clean = str(ncm).strip().replace('.', '').replace('-', '').replace(' ', '')
        
        if not ncm_clean or len(ncm_clean) < 4:
            return None
        
        # Preferir SQLite quando disponível (evita JSON gigante em runtime)
        if _nesh_sqlite_ready():
            if log_source:
                logging.info(f"📚 NESH fonte=SQLITE modo=ncm ncm={ncm_clean}")
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            ncm_4 = ncm_clean[:4]
            ncm_6 = ncm_clean[:6] if len(ncm_clean) >= 6 else None

            # Prioridade 1: subposição exata (6)
            if ncm_6:
                cursor.execute(
                    """
                    SELECT * FROM nesh_chunks
                    WHERE subposition_code_clean = ?
                    LIMIT 1
                    """,
                    (ncm_6,),
                )
                row = cursor.fetchone()
                if row:
                    conn.close()
                    return _nesh_row_to_dict(row)

            # Prioridade 2: nota geral da posição (4) (sem subposição)
            cursor.execute(
                """
                SELECT * FROM nesh_chunks
                WHERE position_code_clean = ?
                  AND (subposition_code_clean IS NULL OR subposition_code_clean = '')
                LIMIT 1
                """,
                (ncm_4,),
            )
            row = cursor.fetchone()
            if row:
                conn.close()
                return _nesh_row_to_dict(row)

            # Prioridade 3: qualquer registro com a posição
            cursor.execute(
                """
                SELECT * FROM nesh_chunks
                WHERE position_code_clean = ?
                LIMIT 1
                """,
                (ncm_4,),
            )
            row = cursor.fetchone()
            conn.close()
            return _nesh_row_to_dict(row) if row else None

        # Fallback: JSON
        if log_source:
            logging.info(f"📚 NESH fonte=JSON modo=ncm ncm={ncm_clean}")
        nesh_data = _carregar_nesh_cache()
        
        # Buscar por código de posição (4 dígitos) ou subposição (6 dígitos)
        ncm_4 = ncm_clean[:4]
        ncm_6 = ncm_clean[:6] if len(ncm_clean) >= 6 else None
        
        # Prioridade 1: Buscar subposição exata (6 dígitos)
        if ncm_6:
            for registro in nesh_data:
                subpos = registro.get('subposition_code', '')
                if subpos:
                    subpos_clean = str(subpos).strip().replace('.', '').replace('-', '').replace(' ', '')
                    if subpos_clean == ncm_6:
                        out = dict(registro) if isinstance(registro, dict) else {}
                        out["_nesh_source"] = "JSON"
                        return out
        
        # Prioridade 2: Buscar posição (4 dígitos)
        for registro in nesh_data:
            pos = registro.get('position_code', '')
            if pos:
                pos_clean = str(pos).strip().replace('.', '').replace('-', '').replace(' ', '')
                if pos_clean == ncm_4:
                    # Preferir registros sem subposição (nota geral da posição)
                    if not registro.get('subposition_code'):
                        out = dict(registro) if isinstance(registro, dict) else {}
                        out["_nesh_source"] = "JSON"
                        return out
        
        # Prioridade 3: Buscar qualquer registro com a posição (incluindo subposições)
        for registro in nesh_data:
            pos = registro.get('position_code', '')
            if pos:
                pos_clean = str(pos).strip().replace('.', '').replace('-', '').replace(' ', '')
                if pos_clean == ncm_4:
                    out = dict(registro) if isinstance(registro, dict) else {}
                    out["_nesh_source"] = "JSON"
                    return out
        
        return None
    except Exception as e:
        logging.error(f'Erro ao buscar nota explicativa NESH por NCM {ncm}: {e}')
        return None

def buscar_notas_explicativas_nesh_por_descricao(termo: str, limite: int = 5) -> List[Dict[str, Any]]:
    """
    Busca notas explicativas NESH por descrição do produto (busca semântica simples).
    
    Args:
        termo: Termo de busca (descrição do produto)
        limite: Número máximo de resultados
    
    Returns:
        Lista de registros NESH ordenados por relevância
    """
    try:
        if not termo or len(termo.strip()) < 2:
            return []

        log_source = str(os.getenv("NESH_LOG_SOURCE", "false")).strip().lower() in ("1", "true", "yes", "y", "on")
        termo_log = (termo or "").strip().replace("\n", " ")
        if len(termo_log) > 80:
            termo_log = termo_log[:77] + "..."

        # ✅ HF/FAISS (opcional): se habilitado e pronto, usar como 1ª tentativa.
        # Mantém fallback automático para o SQLite/LIKE atual se não estiver configurado.
        try:
            from services.nesh_hf_service import get_nesh_hf_service
            svc = get_nesh_hf_service()
            if svc.is_ready():
                resultados_hf = svc.buscar_por_descricao(termo, limite=int(limite or 5))
                if resultados_hf:
                    if log_source:
                        logging.info(f"📚 NESH fonte=HF modo=descricao hits={len(resultados_hf)} termo='{termo_log}'")
                    return resultados_hf
                if log_source:
                    logging.info(f"📚 NESH fonte=HF modo=descricao hits=0 (fallback) termo='{termo_log}'")
        except Exception:
            # Best-effort: nunca quebrar busca NESH por dependência opcional
            pass
        
        termo_lower = termo.strip().lower()
        palavras_chave_originais = [p for p in termo_lower.split() if len(p) > 2]
        
        if not palavras_chave_originais:
            return []
        
        # ✅ CRÍTICO: Verificar se é frase composta ANTES do stemming
        # Frase composta = múltiplas palavras na entrada original (ex: "placa solar")
        # NÃO é frase composta quando há apenas variações da mesma palavra (ex: "alho" → "alho", "alhos")
        tem_frase_composta = len(palavras_chave_originais) > 1
        termo_completo_lower = termo_lower if tem_frase_composta else None
        
        # ✅ MELHORIA: Stemming básico (alho/alhos, ventilador/ventiladores, etc.)
        # Expandir palavras-chave com variações comuns
        palavras_expandidas = []
        for palavra in palavras_chave_originais:
            palavras_expandidas.append(palavra)
            # Adicionar variações comuns
            if palavra.endswith('o'):
                palavras_expandidas.append(palavra + 's')  # alho -> alhos
            elif palavra.endswith('s'):
                palavras_expandidas.append(palavra[:-1])  # alhos -> alho
            if palavra.endswith('dor'):
                palavras_expandidas.append(palavra + 'es')  # ventilador -> ventiladores
            elif palavra.endswith('dores'):
                palavras_expandidas.append(palavra[:-2])  # ventiladores -> ventilador
        
        # Remover duplicatas mantendo ordem
        palavras_chave = list(dict.fromkeys(palavras_expandidas))
        
        # Preferir SQLite: filtrar candidatos via LIKE e pontuar em Python
        if _nesh_sqlite_ready():
            if log_source:
                logging.info(f"📚 NESH fonte=SQLITE modo=descricao termo='{termo_log}'")
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # montar WHERE por tokens (OR)
            like_terms = []
            params = []
            for p in palavras_chave:
                pat = f"%{p}%"
                like_terms.append("(lower(text) LIKE ? OR lower(position_title) LIKE ? OR lower(subposition_title) LIKE ?)")
                params.extend([pat, pat, pat])

            where = " OR ".join(like_terms) if like_terms else "1=0"
            cursor.execute(
                f"""
                SELECT * FROM nesh_chunks
                WHERE {where}
                LIMIT 200
                """,
                params,
            )
            rows = cursor.fetchall()
            conn.close()

            candidatos = [_nesh_row_to_dict(r) for r in rows]
            resultados = []

            # scoring simples (mantém funcionalidade: retorna notas relevantes)
            for registro in candidatos:
                texto = (registro.get("text") or "").lower()
                titulo_posicao = (registro.get("position_title") or "").lower()
                titulo_subposicao = (registro.get("subposition_title") or "").lower()
                blob = f"{titulo_posicao} {titulo_subposicao} {texto}"

                # ✅ Preservar regra antiga: se for frase composta (múltiplas palavras),
                # exigir que TODAS as palavras originais apareçam em algum lugar (evita falso positivo).
                if tem_frase_composta and palavras_chave_originais:
                    if not all(p in blob for p in palavras_chave_originais):
                        continue

                score = 0
                if termo_completo_lower and termo_completo_lower in texto:
                    score += 10
                for palavra in palavras_chave:
                    if palavra in titulo_posicao or palavra in titulo_subposicao:
                        score += 3
                    if palavra in texto:
                        score += 2
                if score > 0:
                    resultados.append((score, registro))

            resultados.sort(key=lambda x: x[0], reverse=True)
            return [r for _, r in resultados[: int(limite)]]

        # Fallback: JSON
        if log_source:
            logging.info(f"📚 NESH fonte=JSON modo=descricao termo='{termo_log}'")
        nesh_data = _carregar_nesh_cache()
        resultados = []
        
        # Buscar registros que contenham as palavras-chave no texto
        import re
        for registro in nesh_data:
            # ✅ CORREÇÃO: Tratar campos None
            texto = (registro.get('text') or '').lower()
            titulo_posicao = (registro.get('position_title') or '').lower()
            titulo_subposicao = (registro.get('subposition_title') or '').lower()
            titulo_capitulo = (registro.get('chapter_title') or '').lower()
            
            # Contar quantas palavras-chave aparecem
            score = 0
            palavras_encontradas_titulo = set()  # ✅ Mudança: usar set para palavras únicas
            palavras_encontradas_texto = set()  # ✅ Mudança: usar set para palavras únicas
            frase_completa_encontrada = False
            
            # ✅ PRIORIDADE 1: Buscar frase completa (se for frase composta)
            if tem_frase_composta and termo_completo_lower:
                # Buscar frase completa no texto (palavras próximas, até ~100 caracteres de distância)
                # Padrão: palavra1 (com até ~15 palavras entre) palavra2
                palavras_escaped = [re.escape(p) for p in palavras_chave]
                # Padrão mais flexível: permite espaços, pontuação e até ~100 caracteres entre palavras
                pattern_frase = r'\b' + r'\b[\s\S]{0,100}?\b'.join(palavras_escaped) + r'\b'
                
                # ✅ ALTERNATIVA: Buscar também a frase exata (palavras adjacentes)
                pattern_frase_exata = r'\b' + r'\s+'.join(palavras_escaped) + r'\b'
                
                # Buscar frase exata primeiro (palavras adjacentes - maior prioridade)
                if re.search(pattern_frase_exata, texto):
                    score += 80  # Score muito alto para frase exata no texto
                    frase_completa_encontrada = True
                    palavras_encontradas_texto.update(palavras_chave)  # ✅ Adicionar todas as palavras
                elif re.search(pattern_frase, texto):
                    score += 50  # Score alto para frase completa no texto
                    frase_completa_encontrada = True
                    palavras_encontradas_texto.update(palavras_chave)  # ✅ Adicionar todas as palavras
                
                if re.search(pattern_frase_exata, titulo_posicao):
                    score += 150  # Score extremamente alto para frase exata no título
                    frase_completa_encontrada = True
                    palavras_encontradas_titulo.update(palavras_chave)  # ✅ Adicionar todas as palavras
                elif re.search(pattern_frase, titulo_posicao):
                    score += 100  # Score muito alto para frase completa no título
                    frase_completa_encontrada = True
                    palavras_encontradas_titulo.update(palavras_chave)  # ✅ Adicionar todas as palavras
                
                if re.search(pattern_frase_exata, titulo_subposicao):
                    score += 150  # Score extremamente alto para frase exata no título
                    frase_completa_encontrada = True
                    palavras_encontradas_titulo.update(palavras_chave)  # ✅ Adicionar todas as palavras
                elif re.search(pattern_frase, titulo_subposicao):
                    score += 100  # Score muito alto para frase completa no título
                    frase_completa_encontrada = True
                    palavras_encontradas_titulo.update(palavras_chave)  # ✅ Adicionar todas as palavras
                
                if re.search(pattern_frase_exata, titulo_capitulo):
                    score += 120  # Score extremamente alto para frase exata no capítulo
                    frase_completa_encontrada = True
                    palavras_encontradas_titulo.update(palavras_chave)  # ✅ Adicionar todas as palavras
                elif re.search(pattern_frase, titulo_capitulo):
                    score += 80  # Score muito alto para frase completa no capítulo
                    frase_completa_encontrada = True
                    palavras_encontradas_titulo.update(palavras_chave)  # ✅ Adicionar todas as palavras
            
            # ✅ PRIORIDADE 2: Buscar palavras individuais (sempre buscar palavras expandidas)
            # Para palavras únicas, sempre buscar. Para frases compostas, buscar se não encontrou frase completa.
            # IMPORTANTE: Buscar palavras expandidas (stemming) para capturar variações
            if not frase_completa_encontrada:
                for palavra in palavras_chave:
                    # ✅ MELHORIA: Buscar palavra completa (não substring)
                    # Usar regex para encontrar palavra completa (com limites de palavra)
                    pattern = r'\b' + re.escape(palavra) + r'\b'
                    
                    # Buscar em todos os campos com pesos diferentes
                    encontrou_texto = bool(re.search(pattern, texto))
                    encontrou_titulo_posicao = bool(re.search(pattern, titulo_posicao))
                    encontrou_titulo_subposicao = bool(re.search(pattern, titulo_subposicao))
                    encontrou_titulo_capitulo = bool(re.search(pattern, titulo_capitulo))
                    
                    if encontrou_texto:
                        if frase_completa_encontrada:
                            score += 0  # Se já tem frase completa, não adicionar score extra
                        else:
                            score += 1  # Peso menor no texto (pode ter falsos positivos)
                        palavras_encontradas_texto.add(palavra)  # ✅ Adicionar palavra ao set
                    if encontrou_titulo_posicao:
                        if frase_completa_encontrada:
                            score += 0  # Se já tem frase completa, não adicionar score extra
                        else:
                            score += 10  # Peso muito maior no título da posição (mais confiável)
                        palavras_encontradas_titulo.add(palavra)  # ✅ Adicionar palavra ao set
                    if encontrou_titulo_subposicao:
                        if frase_completa_encontrada:
                            score += 0  # Se já tem frase completa, não adicionar score extra
                        else:
                            score += 10  # Peso muito maior no título da subposição (mais confiável)
                        palavras_encontradas_titulo.add(palavra)  # ✅ Adicionar palavra ao set
                    if encontrou_titulo_capitulo:
                        if frase_completa_encontrada:
                            score += 0  # Se já tem frase completa, não adicionar score extra
                        else:
                            score += 8  # Peso alto no título do capítulo
                        palavras_encontradas_titulo.add(palavra)  # ✅ Adicionar palavra ao set
            
            # ✅ MELHORIA: Priorizar resultados que têm a palavra no título
            # Se encontrou no título, dar bônus extra (apenas se não é frase completa)
            if len(palavras_encontradas_titulo) > 0 and not frase_completa_encontrada:
                score += 20  # Bônus grande para resultados com palavra no título
            
            # ✅ FILTRO MELHORADO: Para frases compostas, só incluir se TODAS as palavras foram encontradas
            if score > 0:
                # ✅ Marcar fonte (não mutar cache em memória)
                registro_out = dict(registro) if isinstance(registro, dict) else {}
                registro_out["_nesh_source"] = "JSON"

                # ✅ Verificar se TODAS as palavras-chave ORIGINAIS foram encontradas (usando sets para contagem única)
                # IMPORTANTE: Comparar com palavras_chave_originais, não palavras_chave expandidas
                todas_palavras_unicas = palavras_encontradas_titulo.union(palavras_encontradas_texto)
                # Verificar se pelo menos as palavras originais foram encontradas (pode ter encontrado variações também)
                todas_palavras_encontradas = len(todas_palavras_unicas) >= len(palavras_chave_originais)
                
                if frase_completa_encontrada:
                    # Se encontrou frase completa, incluir sempre (score muito alto)
                    resultados.append({
                        'registro': registro_out,
                        'score': score
                    })
                elif tem_frase_composta:
                    # ✅ CRÍTICO: Para frases compostas, SÓ incluir se TODAS as palavras foram encontradas
                    if todas_palavras_encontradas:
                        if len(palavras_encontradas_titulo) > 0:
                            # Se encontrou todas no título, incluir sempre
                            resultados.append({
                                'registro': registro_out,
                                'score': score
                            })
                        elif len(palavras_encontradas_texto) >= len(palavras_chave_originais):
                            # Se encontrou todas as palavras originais no texto, incluir
                            resultados.append({
                                'registro': registro_out,
                                'score': score
                            })
                    # Se não encontrou todas as palavras, NÃO incluir (evitar falsos positivos)
                else:
                    # ✅ Para palavras únicas, incluir se encontrou a palavra (em qualquer lugar)
                    if len(palavras_encontradas_titulo) > 0 or len(palavras_encontradas_texto) > 0:
                        resultados.append({
                            'registro': registro_out,
                            'score': score
                        })
        
        # Ordenar por score (maior primeiro) e limitar
        resultados.sort(key=lambda x: x['score'], reverse=True)
        resultados = resultados[:limite]
        
        # Retornar apenas os registros (sem score)
        return [r['registro'] for r in resultados]
    except Exception as e:
        logging.error(f'Erro ao buscar notas explicativas NESH por descrição: {e}')
        return []

def buscar_notas_explicativas_nesh_por_ncm_e_descricao(ncm: str, descricao_produto: Optional[str] = None, limite: int = 3) -> List[Dict[str, Any]]:
    """
    Busca notas explicativas NESH combinando código NCM e descrição do produto.
    
    Args:
        ncm: Código NCM (4, 6 ou 8 dígitos)
        descricao_produto: Descrição do produto (opcional, para refinar busca)
        limite: Número máximo de resultados
    
    Returns:
        Lista de registros NESH ordenados por relevância
    """
    try:
        resultados = []
        
        # Buscar por NCM primeiro
        nota_por_ncm = buscar_nota_explicativa_nesh_por_ncm(ncm)
        if nota_por_ncm:
            resultados.append(nota_por_ncm)
        
        # Se forneceu descrição, buscar também por descrição
        if descricao_produto:
            notas_por_desc = buscar_notas_explicativas_nesh_por_descricao(descricao_produto, limite=limite)
            # Adicionar apenas se não for duplicata
            for nota in notas_por_desc:
                if nota not in resultados:
                    resultados.append(nota)
        
        return resultados[:limite]
    except Exception as e:
        logging.error(f'Erro ao buscar notas explicativas NESH por NCM e descrição: {e}')
        return []

# ============================================================================
# Funções para gerenciar categorias de processo dinamicamente
# ============================================================================

def obter_categorias_processo() -> List[str]:
    """
    Retorna lista de todas as categorias de processo conhecidas (do banco de dados).
    
    Returns:
        Lista de categorias (ex: ['ALH', 'VDM', 'BND', ...])
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT categoria FROM categorias_processo ORDER BY categoria')
        resultados = cursor.fetchall()
        conn.close()
        return [row[0] for row in resultados]
    except Exception as e:
        logging.error(f'Erro ao obter categorias de processo: {e}')
        # Retornar lista padrão em caso de erro
        return ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MDA', 'NTM', 'UPI', 'GLT', 'GPS', 'MV5']

def verificar_categoria_processo(categoria: str) -> bool:
    """
    Verifica se uma categoria de processo é conhecida.
    
    Args:
        categoria: Categoria a verificar (ex: 'ABN')
    
    Returns:
        True se a categoria é conhecida, False caso contrário
    """
    try:
        categoria_upper = categoria.upper().strip()
        if len(categoria_upper) < 2 or len(categoria_upper) > 4:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM categorias_processo WHERE categoria = ?', (categoria_upper,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado is not None
    except Exception as e:
        logging.error(f'Erro ao verificar categoria de processo: {e}')
        return False

def adicionar_categoria_processo(categoria: str, confirmada_por_usuario: bool = True) -> bool:
    """
    Adiciona uma nova categoria de processo ao banco de dados.
    
    Args:
        categoria: Categoria a adicionar (ex: 'ABN')
        confirmada_por_usuario: Se foi confirmada pelo usuário (padrão: True)
    
    Returns:
        True se foi adicionada com sucesso, False caso contrário
    """
    try:
        categoria_upper = categoria.upper().strip()
        if len(categoria_upper) < 2 or len(categoria_upper) > 4:
            logging.warning(f'⚠️ Categoria inválida: {categoria_upper} (deve ter 2-4 caracteres)')
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO categorias_processo (categoria, confirmada_por_usuario, atualizado_em)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (categoria_upper, confirmada_por_usuario))
        conn.commit()
        conn.close()
        logging.info(f'✅ Categoria de processo adicionada: {categoria_upper}')
        return True
    except Exception as e:
        logging.error(f'Erro ao adicionar categoria de processo: {e}')
        return False

def listar_categorias_processo() -> List[Dict[str, Any]]:
    """
    Lista todas as categorias de processo com informações adicionais.
    
    Returns:
        Lista de dicionários com informações das categorias
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT categoria, confirmada_por_usuario, criado_em, atualizado_em
            FROM categorias_processo
            ORDER BY categoria
        ''')
        resultados = cursor.fetchall()
        conn.close()
        return [dict(row) for row in resultados]
    except Exception as e:
        logging.error(f'Erro ao listar categorias de processo: {e}')
        return []

# ============================================================================
# Funções para Dashboard "O QUE TEMOS PRA HOJE"
# ============================================================================

def obter_processos_chegando_hoje(categoria: Optional[str] = None, modal: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Busca processos que chegam hoje.
    
    ✅ REGRA: Considera processos que:
    1. Têm dataDestinoFinal = hoje (chegada confirmada) OU
    2. Têm ETA = hoje E NÃO têm dataDestinoFinal (previsto para chegar hoje, mas ainda não confirmado)
    
    ✅ Busca data de múltiplas fontes:
    - data_destino_final (tabela) / dataDestinoFinal (JSON) - chegada confirmada
    - eta_iso (tabela) / shipgov2.destino_data_chegada (JSON) / dataPrevisaoChegada (JSON) - ETA previsto
    
    Args:
        categoria: Filtro opcional por categoria (ex: 'ALH', 'VDM')
        modal: Filtro opcional por modal ('Marítimo', 'Aéreo')
    
    Returns:
        Lista de processos chegando hoje
    """
    try:
        import json
        from datetime import datetime, date
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query base - buscar processos que podem ter data de chegada ou ETA hoje
        # Incluir processos com data_destino_final = hoje OU com dados_completos_json (para buscar ETA do JSON)
        query = '''
            SELECT 
                processo_referencia,
                modal,
                data_destino_final,
                porto_codigo,
                porto_nome,
                eta_iso,
                situacao_ce,
                numero_ce,
                dados_completos_json
            FROM processos_kanban
            WHERE 
                (
                    DATE(data_destino_final) = DATE('now')
                    OR (eta_iso IS NOT NULL AND DATE(eta_iso) = DATE('now'))
                    OR (data_destino_final IS NULL AND dados_completos_json IS NOT NULL)
                )
                AND (situacao_ce IS NULL OR situacao_ce != 'ENTREGUE')
                AND (situacao_entrega IS NULL OR situacao_entrega != 'ENTREGUE')
                AND (numero_di IS NULL OR numero_di = '' OR numero_di = '/       -')
                AND (numero_duimp IS NULL OR numero_duimp = '')
        '''
        
        params = []
        
        # Filtro por categoria (extrair do processo_referencia)
        if categoria:
            query += ' AND processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        # Filtro por modal
        if modal:
            query += ' AND modal = ?'
            params.append(modal)
        
        query += ' ORDER BY processo_referencia ASC'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        
        hoje = date.today()
        processos = []
        
        # Helper para parsear data
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                if isinstance(date_str, date):
                    return date_str
                if isinstance(date_str, datetime):
                    return date_str.date()
                if isinstance(date_str, str):
                    # Tentar vários formatos
                    date_str_clean = date_str.split('T')[0].split(' ')[0]
                    for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            return datetime.strptime(date_str_clean, fmt.split()[0] if ' ' in fmt else fmt).date()
                        except:
                            continue
            except:
                pass
            return None
        
        for row in resultados:
            # Extrair categoria do processo_referencia
            categoria_proc = row['processo_referencia'].split('.')[0] if '.' in row['processo_referencia'] else None
            
            # Verificar data de chegada confirmada (dataDestinoFinal)
            data_chegada_confirmada = None
            
            # 1. Tentar campo da tabela primeiro
            if row['data_destino_final']:
                data_chegada_confirmada = parse_date(row['data_destino_final'])
            
            # 2. Se não encontrou, buscar do JSON
            if not data_chegada_confirmada and row['dados_completos_json']:
                try:
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # Buscar dataDestinoFinal (chegada confirmada)
                    if dados_json.get('dataDestinoFinal'):
                        data_chegada_confirmada = parse_date(dados_json.get('dataDestinoFinal'))
                    
                    # Se não encontrou e é aéreo, buscar dataHoraChegadaEfetiva
                    if not data_chegada_confirmada and row['modal'] == 'Aéreo':
                        if dados_json.get('dataHoraChegadaEfetiva'):
                            data_chegada_confirmada = parse_date(dados_json.get('dataHoraChegadaEfetiva'))
                except:
                    pass
            
            # Verificar ETA (previsão de chegada)
            eta_data = None
            
            # ✅ PRIORIDADE: Buscar do JSON primeiro (mais atualizado)
            if row['dados_completos_json']:
                try:
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # 1. PRIORIDADE MÁXIMA: Evento DISC (Discharge/Descarga) no porto de destino = POD
                    # DISC indica quando a carga foi descarregada no porto de destino (POD)
                    shipgov2 = dados_json.get('shipgov2', {})
                    if shipgov2:
                        eventos = shipgov2.get('eventos', [])
                        if isinstance(eventos, list) and len(eventos) > 0:
                            # Buscar eventos DISC (Discharge) no porto de destino
                            porto_destino = shipgov2.get('destino_codigo', '')
                            eventos_disc = [
                                e for e in eventos 
                                if isinstance(e, dict) 
                                and e.get('atual_evento') == 'DISC'
                                and (not porto_destino or e.get('atual_codigo') == porto_destino)
                            ]
                            if eventos_disc:
                                # Pegar o mais recente (último DISC)
                                ultimo_disc = max(eventos_disc, key=lambda x: x.get('atual_data_evento', ''))
                                if ultimo_disc.get('atual_data_evento'):
                                    eta_data = parse_date(ultimo_disc.get('atual_data_evento'))
                    
                    # 2. Se não encontrou DISC, usar dataPrevisaoChegada
                    if not eta_data:
                        if dados_json.get('dataPrevisaoChegada'):
                            eta_data = parse_date(dados_json.get('dataPrevisaoChegada'))
                    
                    # 3. Se não encontrou, verificar último evento ARRV no histórico
                    if not eta_data:
                        shipgov2 = dados_json.get('shipgov2', {})
                        if shipgov2:
                            eventos = shipgov2.get('eventos', [])
                            if isinstance(eventos, list) and len(eventos) > 0:
                                # Buscar último evento ARRV (arrival)
                                eventos_arrv = [e for e in eventos if isinstance(e, dict) and e.get('atual_evento') == 'ARRV']
                                if eventos_arrv:
                                    # Pegar o mais recente (último)
                                    ultimo_arrv = max(eventos_arrv, key=lambda x: x.get('atual_data_evento', ''))
                                    if ultimo_arrv.get('atual_data_evento'):
                                        eta_data = parse_date(ultimo_arrv.get('atual_data_evento'))
                    
                    # 3. Fallback: shipgov2.destino_data_chegada (pode ser histórico antigo)
                    if not eta_data:
                        shipgov2 = dados_json.get('shipgov2', {})
                        if shipgov2 and shipgov2.get('destino_data_chegada'):
                            eta_data = parse_date(shipgov2.get('destino_data_chegada'))
                except:
                    pass
            
            # 5. Último fallback: eta_iso da tabela (pode ser histórico)
            if not eta_data and row['eta_iso']:
                eta_data = parse_date(row['eta_iso'])
            
            # ✅ REGRA: Incluir APENAS se:
            # - Tem ETA = hoje E NÃO tem dataDestinoFinal (previsto para hoje, mas ainda não chegou/confirmado)
            # ⚠️ NÃO incluir se tem dataDestinoFinal = hoje (já chegou, deve aparecer em "PRONTOS PARA REGISTRO")
            deve_incluir = False
            
            if eta_data and eta_data == hoje and not data_chegada_confirmada:
                # ETA é hoje mas ainda não tem chegada confirmada (dataDestinoFinal)
                # Este processo está previsto para chegar hoje mas ainda não chegou
                deve_incluir = True
            
            if deve_incluir:
                # ✅ Usar ETA do JSON (mais atualizado) se disponível, senão usar da tabela
                eta_final = None
                if eta_data:
                    eta_final = eta_data.isoformat()
                elif row['eta_iso']:
                    eta_final = row['eta_iso']
                
                processos.append({
                    'processo_referencia': row['processo_referencia'],
                    'categoria': categoria_proc,
                    'modal': row['modal'] or 'N/A',
                    'data_destino_final': row['data_destino_final'] or (data_chegada_confirmada.isoformat() if data_chegada_confirmada else None),
                    'porto_codigo': row['porto_codigo'],
                    'porto_nome': row['porto_nome'],
                    'eta_iso': eta_final,
                    'situacao_ce': row['situacao_ce'],
                    'numero_ce': row['numero_ce'],
                    'tem_chegada_confirmada': bool(data_chegada_confirmada),
                    'tem_apenas_eta': bool(eta_data and not data_chegada_confirmada)
                })
        
        return processos
    except Exception as e:
        logging.error(f'Erro ao obter processos chegando hoje: {e}')
        return []


def obter_processos_prontos_registro(categoria: Optional[str] = None, modal: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Busca processos prontos para registro DI/DUIMP (chegaram e não têm DI/DUIMP).
    
    ⚠️ REGRA CRÍTICA: Se o processo TEM LPCO, ele só pode ser considerado "pronto" 
    se o LPCO estiver DEFERIDO. Processos com LPCO indeferido ou pendente NÃO podem 
    registrar DI/DUIMP.
    
    Args:
        categoria: Filtro opcional por categoria
        modal: Filtro opcional por modal
    
    Returns:
        Lista de processos prontos para registro
    """
    try:
        import json
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                processo_referencia,
                modal,
                data_destino_final,
                numero_ce,
                situacao_ce,
                situacao_di,
                numero_di,
                numero_duimp,
                situacao_entrega,
                data_armazenamento,
                dados_completos_json
            FROM processos_kanban
            WHERE 
                DATE(data_destino_final) <= DATE('now')
                -- ✅ CORREÇÃO: Excluir processos com DI ou DUIMP registrada (devem aparecer em análise, não aqui)
                AND (numero_di IS NULL OR numero_di = '' OR numero_di = '/       -')
                AND (numero_duimp IS NULL OR numero_duimp = '')
                AND (situacao_ce IS NULL OR situacao_ce != 'ENTREGUE')
                AND (situacao_entrega IS NULL OR situacao_entrega != 'ENTREGUE')
        '''
        
        params = []
        
        # Filtro por categoria
        if categoria:
            query += ' AND processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        # Filtro por modal
        if modal:
            query += ' AND modal = ?'
            params.append(modal)
        
        # Filtrar por status que indica que chegou (descarregada, recepcionada, armazenada, vinculada)
        # ✅ IMPORTANTE: Incluir VINCULADA_A_DOCUMENTO_DE_DESPACHO pois indica que chegou e foi vinculada
        query += ''' AND (
            situacao_ce IN ('DESCARREGADA', 'RECEPCIONADA', 'ARMAZENADA', 'MANIFESTADA', 'VINCULADA_A_DOCUMENTO_DE_DESPACHO')
            OR data_armazenamento IS NOT NULL
            OR data_destino_final IS NOT NULL
        )'''
        
        query += ' ORDER BY data_destino_final DESC, processo_referencia ASC'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        
        processos = []
        for row in resultados:
            # ✅ NOVO: Verificar LPCO antes de adicionar à lista
            tem_lpco = False
            lpco_deferido = False
            numero_lpco = None
            situacao_lpco = None
            
            # Buscar dados de LPCO do JSON
            if row['dados_completos_json']:
                try:
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # Buscar LPCO no JSON (pode estar em 'lpco' ou 'lpcoDetails')
                    lpco_data = None
                    if dados_json.get('lpco'):
                        lpco_data = dados_json.get('lpco', {})
                        if isinstance(lpco_data, list) and len(lpco_data) > 0:
                            lpco_data = lpco_data[0]
                    elif dados_json.get('lpcoDetails'):
                        lpco_data = dados_json.get('lpcoDetails', {})
                        if isinstance(lpco_data, list) and len(lpco_data) > 0:
                            lpco_data = lpco_data[0]
                    
                    if lpco_data:
                        tem_lpco = True
                        numero_lpco = lpco_data.get('LPCO') or lpco_data.get('numero_lpco') or lpco_data.get('numero')
                        situacao_lpco = lpco_data.get('situacao') or lpco_data.get('situacao_lpco') or lpco_data.get('status')
                        
                        # Verificar se está deferido
                        if situacao_lpco:
                            situacao_lpco_lower = str(situacao_lpco).lower()
                            lpco_deferido = 'deferido' in situacao_lpco_lower
                except Exception as e:
                    logging.warning(f'Erro ao verificar LPCO do processo {row["processo_referencia"]}: {e}')
            
            # ✅ REGRA CRÍTICA: Se tem LPCO e NÃO está deferido, NÃO pode registrar DI/DUIMP
            if tem_lpco and not lpco_deferido:
                # Pular este processo - não está pronto para registro
                logging.debug(f'Processo {row["processo_referencia"]} tem LPCO mas não está deferido (situação: {situacao_lpco}). Não pode registrar DI/DUIMP.')
                continue
            
            # ✅ CORREÇÃO: Se processo TEM DI ou DUIMP registrada, NÃO incluir em "prontos para registro"
            # Processos com DI/DUIMP registrada devem aparecer em "DI/DUIMP em análise", não aqui
            if (row['numero_di'] and row['numero_di'].strip() and row['numero_di'] != '/       -'):
                logging.debug(f'Processo {row["processo_referencia"]} tem DI {row["numero_di"]} registrada. Não incluindo em "prontos para registro".')
                continue
            if row['numero_duimp'] and row['numero_duimp'].strip():
                logging.debug(f'Processo {row["processo_referencia"]} tem DUIMP {row["numero_duimp"]} registrada. Não incluindo em "prontos para registro".')
                continue
            
            # Extrair categoria
            categoria_proc = row['processo_referencia'].split('.')[0] if '.' in row['processo_referencia'] else (row['categoria'] if 'categoria' in row.keys() else None)
            
            # Determinar tipo de documento necessário
            modal_proc = row['modal'] or ''
            tipo_documento = 'DUIMP' if modal_proc == 'Aéreo' or row['numero_ce'] else 'DUIMP' if row['numero_ce'] else 'DI'
            
            motivo_prontidao = f"Chegou em {row['data_destino_final'] or 'data desconhecida'}, sem {tipo_documento}"
            if tem_lpco:
                if lpco_deferido:
                    motivo_prontidao += f" - LPCO {numero_lpco or 'N/A'} deferido"
                else:
                    # Não deveria chegar aqui (já foi filtrado), mas por segurança:
                    motivo_prontidao += f" - LPCO {numero_lpco or 'N/A'} não deferido (bloqueado)"
            
            processos.append({
                'processo_referencia': row['processo_referencia'],
                'categoria': categoria_proc,
                'modal': modal_proc,
                'data_destino_final': row['data_destino_final'],
                'numero_ce': row['numero_ce'],
                'situacao_ce': row['situacao_ce'],
                'tipo_documento': tipo_documento,
                'motivo_prontidao': motivo_prontidao,
                'tem_lpco': tem_lpco,
                'lpco_deferido': lpco_deferido,
                'numero_lpco': numero_lpco,
                'situacao_lpco': situacao_lpco
            })
        
        return processos
    except Exception as e:
        logging.error(f'Erro ao obter processos prontos para registro: {e}')
        return []


def obter_pendencias_ativas(categoria: Optional[str] = None, modal: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Busca pendências ativas (ICMS, AFRMM, LPCO, bloqueios).
    
    Args:
        categoria: Filtro opcional por categoria
        modal: Filtro opcional por modal
    
    Returns:
        Lista de processos com pendências
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar processos com pendências na tabela processos_kanban
        # ✅ CORREÇÃO CRÍTICA: Envolver todas as condições OR em parênteses para aplicar filtro de categoria corretamente
        query_base = '''
            SELECT 
                processo_referencia,
                modal,
                pendencia_icms,
                pendencia_frete,
                tem_pendencias,
                dados_completos_json,
                situacao_di,
                situacao_entrega,
                numero_di,
                numero_duimp,
                atualizado_em
            FROM processos_kanban
            WHERE (
                pendencia_frete = 1
                OR (
                    pendencia_icms IS NOT NULL 
                    AND pendencia_icms != '' 
                    AND UPPER(pendencia_icms) NOT LIKE '%OK%' 
                    AND UPPER(pendencia_icms) NOT LIKE '%PAGO%'
                    -- ✅ AJUSTE: Excluir valores que não são realmente pendências (valores informativos/históricos)
                    AND UPPER(pendencia_icms) NOT LIKE '%RESOLVID%'
                    AND UPPER(pendencia_icms) NOT LIKE '%LIQUIDAD%'
                    AND UPPER(pendencia_icms) NOT LIKE '%QUITAD%'
                    AND UPPER(pendencia_icms) NOT LIKE '%FINALIZAD%'
                    AND (
                        -- Só buscar ICMS se tem DI/DUIMP desembaraçada
                        (numero_di IS NOT NULL AND numero_di != '' AND numero_di != '/       -' AND situacao_di LIKE '%DESEMBARAC%')
                        OR (numero_duimp IS NOT NULL AND numero_duimp != '')
                        OR (situacao_entrega LIKE '%DESEMBARAC%' OR situacao_entrega LIKE '%ENTREGUE%' OR situacao_entrega LIKE '%ENTREGA AUTORIZADA%')
                    )
                )
                OR dados_completos_json IS NOT NULL  -- ✅ Buscar também processos com JSON (para verificar AFRMM, LPCO, bloqueios)
            )
        '''
        
        params = []
        
        # ✅ CORREÇÃO CRÍTICA: Filtro por categoria aplicado DEPOIS de todas as condições OR
        # Agora que todas as condições OR estão em parênteses, o filtro de categoria será aplicado a TODAS elas
        if categoria:
            query_base += ' AND processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        query = query_base
        
        # Filtro por modal
        if modal:
            query += ' AND modal = ?'
            params.append(modal)
        
        query += ' ORDER BY atualizado_em ASC'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        
        pendencias = []
        for row in resultados:
            # Extrair categoria
            categoria_proc = row['processo_referencia'].split('.')[0] if '.' in row['processo_referencia'] else None
            
            # Tentar extrair pendências do JSON se disponível
            pendencia_icms = row['pendencia_icms']
            pendencia_afrmm = False
            lpco_exigencia = None
            bloqueios_ce = None
            
            # ✅ Buscar situação da tabela primeiro (prioridade)
            situacao_di = row['situacao_di'] if 'situacao_di' in row.keys() and row['situacao_di'] else ''
            situacao_entrega = row['situacao_entrega'] if 'situacao_entrega' in row.keys() and row['situacao_entrega'] else ''
            situacao_duimp = None  # DUIMP não tem campo direto na tabela, buscar do JSON
            
            if row['dados_completos_json']:
                try:
                    import json
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # Buscar pendências no JSON do CE
                    if dados_json.get('ce'):
                        ce_data = dados_json.get('ce', {})
                        if isinstance(ce_data, list) and len(ce_data) > 0:
                            ce_data = ce_data[0]
                        pendencia_afrmm_raw = ce_data.get('pendencia_afrmm', False)
                        # ✅ Converter para boolean: True, 1, ou string "true" = True
                        if pendencia_afrmm_raw is True or pendencia_afrmm_raw == 1 or (isinstance(pendencia_afrmm_raw, str) and pendencia_afrmm_raw.lower() == 'true'):
                            pendencia_afrmm = True
                        else:
                            pendencia_afrmm = False
                        bloqueios_ce = ce_data.get('bloqueios') or ce_data.get('bloqueios_baixados')
                    
                    # Buscar LPCO (pode estar em 'lpco' ou 'lpcoDetails')
                    lpco_data = None
                    if dados_json.get('lpco'):
                        lpco_data = dados_json.get('lpco', {})
                        if isinstance(lpco_data, list) and len(lpco_data) > 0:
                            lpco_data = lpco_data[0]
                    elif dados_json.get('lpcoDetails'):
                        lpco_data = dados_json.get('lpcoDetails', {})
                        if isinstance(lpco_data, list) and len(lpco_data) > 0:
                            lpco_data = lpco_data[0]
                    
                    if lpco_data:
                        # Buscar situação e exigência do LPCO
                        situacao_lpco = lpco_data.get('situacao') or lpco_data.get('situacao_lpco') or lpco_data.get('status')
                        numero_lpco = lpco_data.get('LPCO') or lpco_data.get('numero_lpco') or lpco_data.get('numero')
                        lpco_exigencia = lpco_data.get('exigencia')
                        
                        # ✅ NOVO: Se LPCO não está deferido, considerar como pendência bloqueante
                        if situacao_lpco:
                            situacao_lpco_lower = str(situacao_lpco).lower()
                            lpco_deferido = 'deferido' in situacao_lpco_lower
                            
                            # Se não está deferido, é pendência bloqueante (mesmo sem exigência)
                            if not lpco_deferido:
                                lpco_exigencia = lpco_exigencia or f"LPCO {numero_lpco or 'N/A'} não deferido - Situação: {situacao_lpco}"
                        elif lpco_exigencia:
                            # Se tem exigência, manter
                            pass
                        else:
                            # Se não tem situação nem exigência, não considerar como pendência
                            lpco_exigencia = None
                    
                    # ✅ NOVO: Buscar situação da DI/DUIMP para validar ICMS
                    # Se não encontrou na tabela, buscar do JSON
                    if not situacao_di and dados_json.get('di'):
                        di_data = dados_json.get('di', {})
                        if isinstance(di_data, list) and len(di_data) > 0:
                            di_data = di_data[0]
                        situacao_di = di_data.get('situacao', '') or di_data.get('situacao_di', '')
                    
                    # Buscar situação da DUIMP do JSON (não tem na tabela)
                    if dados_json.get('duimp'):
                        duimp_data = dados_json.get('duimp', {})
                        if isinstance(duimp_data, list) and len(duimp_data) > 0:
                            duimp_data = duimp_data[0]
                        situacao_duimp = duimp_data.get('situacao', '') or duimp_data.get('status', '') or duimp_data.get('situacao_duimp', '')
                    
                    # Buscar situação de entrega do JSON se não encontrou na tabela
                    if not situacao_entrega:
                        situacao_entrega = dados_json.get('situacao_entrega', '') or dados_json.get('situacaoEntrega', '')
                except:
                    pass
            
            # ✅ REGRA LEGAL: ICMS só pode ser cobrado APÓS desembaraço
            # Ato gerador do ICMS é o desembaraço da carga
            # Só considerar ICMS pendente se:
            # 1. DI/DUIMP está desembaraçada OU
            # 2. Situação é "ENTREGA AUTORIZADA SEM PROSSEGUIMENTO DO DESPACHO"
            icms_pode_ser_cobrado = False
            # ✅ AJUSTE: Validar se pendencia_icms realmente indica pendência antes de processar
            pendencia_icms_valida = False
            if pendencia_icms:
                pendencia_icms_str_check = str(pendencia_icms).upper().strip()
                # Excluir valores que claramente não são pendências
                valores_nao_pendencia_check = ['OK', 'PAGO', 'RESOLVID', 'LIQUIDAD', 'QUITAD', 'FINALIZAD', 'N/A', 'NULL', 'NONE', '']
                pendencia_icms_valida = pendencia_icms_str_check and not any(valor in pendencia_icms_str_check for valor in valores_nao_pendencia_check)
            
            if pendencia_icms_valida:
                # Combinar situações da tabela e do JSON (já inicializadas acima)
                situacao_di_final = situacao_di or ''
                situacao_duimp_final = situacao_duimp or ''
                situacao_entrega_final = situacao_entrega or ''
                
                situacao_di_lower = situacao_di_final.lower()
                situacao_duimp_lower = situacao_duimp_final.lower()
                situacao_entrega_lower = situacao_entrega_final.lower()
                
                # Verificar se tem número de DI/DUIMP (indica que foi registrada)
                numero_di = row['numero_di'] if 'numero_di' in row.keys() and row['numero_di'] else ''
                numero_duimp = row['numero_duimp'] if 'numero_duimp' in row.keys() and row['numero_duimp'] else ''
                tem_di_ou_duimp = bool(numero_di and numero_di not in ['', '/       -']) or bool(numero_duimp)
                
                # ✅ REGRA CRÍTICA: Lógica diferenciada para DI vs DUIMP
                # Para DI: ICMS pode ser cobrado se está desembaraçada
                # Para DUIMP: ICMS só pode ser cobrado se situação é uma destas:
                #   - DESEMBARACADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS
                #   - ENTREGA_ANTECIPADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS
                
                if tem_di_ou_duimp:
                    # Verificar se é DI ou DUIMP
                    tem_di = bool(numero_di and numero_di not in ['', '/       -'])
                    tem_duimp = bool(numero_duimp)
                    
                    if tem_di:
                        # Para DI: verificar se está desembaraçada
                        # Padrões que indicam desembaraço (ato gerador do ICMS):
                        # - "desembaraçado", "desembaracado", "desembaraçada", "desembaracada"
                        # - "entregue", "entregue ao destinatário"
                        # - "entrega autorizada sem prosseguimento do despacho"
                        # - "entrega autorizada"
                        if (
                            'desembara' in situacao_di_lower or
                            'desembara' in situacao_entrega_lower or
                            'entregue' in situacao_entrega_lower or
                            'entrega autorizada sem prosseguimento do despacho' in situacao_entrega_lower or
                            'entrega autorizada' in situacao_entrega_lower
                        ):
                            icms_pode_ser_cobrado = True
                    
                    elif tem_duimp:
                        # ✅ Para DUIMP: SÓ considerar pendência se situação é uma das específicas
                        # Situações que indicam pendência de ICMS para DUIMP:
                        situacao_duimp_upper = situacao_duimp_final.upper()
                        if (
                            'DESEMBARACADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS' in situacao_duimp_upper or
                            'ENTREGA_ANTECIPADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS' in situacao_duimp_upper
                        ):
                            icms_pode_ser_cobrado = True
                        # ✅ Se situação é outra (ex: DESEMBARACADA_CARGA_ENTREGUE), NÃO considerar pendência
            
            # Determinar tipo de pendência
            tipo_pendencia = None
            descricao_pendencia = None
            
            if bloqueios_ce:
                tipo_pendencia = 'Bloqueio CE'
                descricao_pendencia = str(bloqueios_ce)
            elif lpco_exigencia:
                tipo_pendencia = 'LPCO'
                descricao_pendencia = str(lpco_exigencia)
            elif pendencia_icms_valida and icms_pode_ser_cobrado:
                # ✅ Só considerar ICMS pendente se pode ser cobrado (desembaraçado) E valor é válido
                # ✅ Validação já foi feita acima (pendencia_icms_valida)
                tipo_pendencia = 'ICMS'
                descricao_pendencia = str(pendencia_icms)
            elif pendencia_afrmm:
                tipo_pendencia = 'AFRMM'
                descricao_pendencia = 'Pendente de pagamento'
            elif row['pendencia_frete']:
                tipo_pendencia = 'Frete'
                descricao_pendencia = 'Pendente de pagamento'
            
            if tipo_pendencia:
                # Calcular tempo desde última atualização
                data_atualizacao = row['atualizado_em']
                tempo_pendente = None
                if data_atualizacao:
                    try:
                        from datetime import datetime
                        data_atual = datetime.now()
                        data_pend = datetime.fromisoformat(data_atualizacao) if isinstance(data_atualizacao, str) else data_atualizacao
                        dias = (data_atual - data_pend).days
                        tempo_pendente = f"{dias} dia(s)" if dias > 0 else "hoje"
                    except:
                        pass
                
                pendencias.append({
                    'processo_referencia': row['processo_referencia'],
                    'categoria': categoria_proc,
                    'modal': row['modal'] or 'N/A',
                    'tipo_pendencia': tipo_pendencia,
                    'descricao_pendencia': descricao_pendencia,
                    'tempo_pendente': tempo_pendente,
                    'acao_sugerida': _sugerir_acao_pendencia(tipo_pendencia)
                })
        
        return pendencias
    except Exception as e:
        logging.error(f'Erro ao obter pendências ativas: {e}')
        return []


def _sugerir_acao_pendencia(tipo_pendencia: str) -> str:
    """Sugere ação baseada no tipo de pendência."""
    acoes = {
        'ICMS': 'Verificar pagamento',
        'AFRMM': 'Verificar pagamento',
        'LPCO': 'Verificar documentação',
        'Bloqueio CE': 'Verificar motivo do bloqueio',
        'Frete': 'Verificar pagamento'
    }
    return acoes.get(tipo_pendencia, 'Verificar situação')


def obter_duimps_em_analise(categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Busca DUIMPs em análise (status: EM_ANALISE, AGUARDANDO_RESPOSTA, PENDENTE).
    ✅ NOVO: Também busca processos com DUIMP registrada mas não desembaraçada do JSON do Kanban.
    
    Args:
        categoria: Filtro opcional por categoria (ex: 'ALH', 'VDM', 'MV5')
    
    Returns:
        Lista de DUIMPs em análise
    """
    try:
        import json
        from datetime import datetime
        
        duimps = []
        
        # 1. Buscar da tabela duimps (método antigo)
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                d.numero as numero_duimp,
                d.versao,
                d.status,
                d.criado_em,
                d.processo_referencia
            FROM duimps d
            WHERE 
                d.status IN ('EM_ANALISE', 'AGUARDANDO_RESPOSTA', 'PENDENTE', 'rascunho')
        '''
        params = []
        if categoria:
            query += ' AND d.processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        query += ' ORDER BY d.criado_em ASC'
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        for row in resultados:
            # Calcular tempo em análise
            tempo_analise = None
            if row['criado_em']:
                try:
                    data_atual = datetime.now()
                    data_criacao = datetime.fromisoformat(row['criado_em']) if isinstance(row['criado_em'], str) else row['criado_em']
                    dias = (data_atual - data_criacao).days
                    tempo_analise = f"{dias} dia(s)" if dias > 0 else "hoje"
                except:
                    pass
            
            duimps.append({
                'numero_duimp': row['numero_duimp'],
                'versao': row['versao'],
                'status': row['status'],
                'processo_referencia': row['processo_referencia'],
                'data_criacao': row['criado_em'],
                'tempo_analise': tempo_analise
            })
        
        # 2. ✅ NOVO: Buscar processos com DUIMP registrada mas não desembaraçada do JSON do Kanban
        query_kanban = '''
            SELECT 
                processo_referencia,
                numero_duimp,
                dados_completos_json
            FROM processos_kanban
            WHERE 
                numero_duimp IS NOT NULL 
                AND numero_duimp != ''
                AND (numero_di IS NULL OR numero_di = '' OR numero_di = '/       -')
                AND (situacao_ce IS NULL OR situacao_ce != 'ENTREGUE')
        '''
        params_kanban = []
        if categoria:
            query_kanban += ' AND processo_referencia LIKE ?'
            params_kanban.append(f'{categoria.upper()}.%')
        
        cursor.execute(query_kanban, params_kanban)
        resultados_kanban = cursor.fetchall()
        conn.close()
        
        # Processar cada processo do Kanban
        processos_duimp_ja_adicionados = {d['numero_duimp'] for d in duimps if d.get('numero_duimp')}
        
        for row in resultados_kanban:
            numero_duimp = row['numero_duimp']
            processo_ref = row['processo_referencia']
            
            # Pular se já foi adicionado da tabela duimps
            if numero_duimp in processos_duimp_ja_adicionados:
                continue
            
            # Buscar situação da DUIMP do JSON do Kanban
            situacao_duimp = None
            versao_duimp = None
            data_registro = None
            situacao_entrega_carga_duimp = None  # ✅ NOVO: situacaoEntregaCarga para DUIMP
            canal_duimp = None  # ✅ NOVO: Canal da DUIMP
            data_desembaraco_duimp = None  # ✅ NOVO: Data de desembaraço da DUIMP
            
            try:
                if row['dados_completos_json']:
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # ✅ NOVO: Buscar situacaoEntregaCarga no nível raiz do JSON (da API externa)
                    situacao_entrega_carga_duimp = dados_json.get('situacaoEntregaCarga') or dados_json.get('situacao_entrega_carga')
                    
                    # ✅ NOVO: Buscar canal no nível raiz do JSON (pode ser para DUIMP também)
                    canal_duimp = dados_json.get('canal') or dados_json.get('canal_duimp')
                    
                    duimps_json = dados_json.get('duimp', [])
                    
                    if isinstance(duimps_json, list) and len(duimps_json) > 0:
                        for duimp_item in duimps_json:
                            if isinstance(duimp_item, dict) and duimp_item.get('numero') == numero_duimp:
                                situacao_duimp = (
                                    duimp_item.get('situacao_duimp') or
                                    duimp_item.get('situacao_duimp_agr') or
                                    duimp_item.get('ultima_situacao') or
                                    ''
                                )
                                versao_duimp = duimp_item.get('versao', '1')
                                data_registro = duimp_item.get('data_registro_mais_recente') or duimp_item.get('data_ultimo_evento')
                                # ✅ NOVO: Buscar canal dentro do objeto duimp
                                if not canal_duimp:
                                    canal_duimp = (
                                        duimp_item.get('canal') or
                                        duimp_item.get('canal_duimp') or
                                        duimp_item.get('canal_consolidado')
                                    )
                                # ✅ NOVO: Buscar data de desembaraço da DUIMP
                                data_desembaraco_duimp = (
                                    duimp_item.get('data_desembaraco') or
                                    duimp_item.get('data_hora_desembaraco') or
                                    duimp_item.get('dataDesembaraco')
                                )
                                break
                    elif isinstance(duimps_json, dict) and duimps_json.get('numero') == numero_duimp:
                        situacao_duimp = (
                            duimps_json.get('situacao_duimp') or
                            duimps_json.get('situacao_duimp_agr') or
                            duimps_json.get('ultima_situacao') or
                            ''
                        )
                        versao_duimp = duimps_json.get('versao', '1')
                        data_registro = duimps_json.get('data_registro_mais_recente') or duimps_json.get('data_ultimo_evento')
                        # ✅ NOVO: Buscar canal dentro do objeto duimp
                        if not canal_duimp:
                            canal_duimp = (
                                duimps_json.get('canal') or
                                duimps_json.get('canal_duimp') or
                                duimps_json.get('canal_consolidado')
                            )
                        # ✅ NOVO: Buscar data de desembaraço da DUIMP
                        data_desembaraco_duimp = (
                            duimps_json.get('data_desembaraco') or
                            duimps_json.get('data_hora_desembaraco') or
                            duimps_json.get('dataDesembaraco')
                        )
            except Exception as e:
                logging.debug(f'Erro ao buscar situação DUIMP do JSON para {processo_ref}: {e}')
            
            # ✅ NOVO: Verificar também situacao_entrega do processo (campo da tabela)
            situacao_entrega = None
            try:
                conn_entrega = get_db_connection()
                cursor_entrega = conn_entrega.cursor()
                cursor_entrega.row_factory = sqlite3.Row
                cursor_entrega.execute('SELECT situacao_entrega FROM processos_kanban WHERE processo_referencia = ?', (processo_ref,))
                row_entrega = cursor_entrega.fetchone()
                conn_entrega.close()
                
                if row_entrega and row_entrega['situacao_entrega']:
                    situacao_entrega = str(row_entrega['situacao_entrega']).upper()
            except:
                pass
            
            # ✅ CORREÇÃO: Lógica de exclusão para DUIMP (mesma lógica da DI)
            # Excluir apenas se:
            # 1. Está desembaraçada E tem entrega autorizada ou condicionada (ICMS)
            # 2. Ou tem "ENTREGA AUTORIZADA SEM PROSSEGUIMENTO"
            # 3. Ou tem "ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE ARRECADACAO DO ICMS"
            
            if situacao_duimp:
                situacao_duimp_upper = str(situacao_duimp).upper()
                situacao_entrega_upper = str(situacao_entrega).upper() if situacao_entrega else ''
                situacao_entrega_carga_upper = str(situacao_entrega_carga_duimp).upper() if situacao_entrega_carga_duimp else ''
                
                # Verificar se está desembaraçada
                esta_desembaracada = (
                    'DESEMBARACADA' in situacao_duimp_upper or 
                    'DESEMBARACADO' in situacao_duimp_upper
                )
                
                # Verificar se tem entrega autorizada ou condicionada (ICMS) - pode estar em qualquer campo
                tem_entrega_autorizada = (
                    'ENTREGA AUTORIZADA' in situacao_entrega_upper or
                    'ENTREGA AUTORIZADA' in situacao_entrega_carga_upper
                )
                tem_entrega_condicionada_icms = (
                    'ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE ARRECADACAO DO ICMS' in situacao_entrega_upper or
                    'ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE ARRECADACAO DO ICMS' in situacao_entrega_carga_upper
                )
                
                tem_entrega_autorizada_sem_prosseguimento = (
                    'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO' in situacao_duimp_upper or
                    'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO' in situacao_entrega_upper or
                    'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO' in situacao_entrega_carga_upper
                )
                
                # Excluir se:
                # - Está desembaraçada E (tem entrega autorizada OU tem entrega condicionada ICMS)
                # - OU tem entrega autorizada sem prosseguimento
                if (esta_desembaracada and (tem_entrega_autorizada or tem_entrega_condicionada_icms)) or tem_entrega_autorizada_sem_prosseguimento:
                    continue
                
                # Se passou todas as verificações, adicionar à lista
                # Calcular tempo em análise
                tempo_analise = None
                if data_registro:
                    try:
                        data_atual = datetime.now()
                        if isinstance(data_registro, str):
                            # Tentar vários formatos
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y']:
                                try:
                                    data_reg = datetime.strptime(data_registro, fmt)
                                    dias = (data_atual - data_reg).days
                                    tempo_analise = f"{dias} dia(s)" if dias > 0 else "hoje"
                                    break
                                except:
                                    continue
                    except:
                        pass
                
                duimps.append({
                    'numero_duimp': numero_duimp,
                    'versao': versao_duimp or '1',
                    'status': situacao_duimp,  # Usar situação do JSON
                    'canal_duimp': canal_duimp,  # ✅ NOVO: Canal da DUIMP
                    'situacao_entrega_carga': situacao_entrega_carga_duimp,  # ✅ NOVO: Incluir situação da entrega
                    'situacao_entrega_tabela': situacao_entrega,  # ✅ NOVO: Incluir situação da entrega (tabela)
                    'data_desembaraco': data_desembaraco_duimp,  # ✅ NOVO: Data de desembaraço
                    'processo_referencia': processo_ref,
                    'data_criacao': data_registro,
                    'tempo_analise': tempo_analise
                })
                processos_duimp_ja_adicionados.add(numero_duimp)
        
        return duimps
    except Exception as e:
        logging.error(f'Erro ao obter DUIMPs em análise: {e}')
        return []


def obter_dis_em_analise(categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Busca DIs em análise (registradas mas não desembaraçadas).
    ✅ Busca processos com DI registrada do JSON do Kanban.
    Exclui DIs desembaraçadas ou com "ENTREGA AUTORIZADA SEM PROSSEGUIMENTO DO DESPACHO".
    
    Args:
        categoria: Filtro opcional por categoria (ex: 'ALH', 'VDM', 'MV5')
    
    Returns:
        Lista de DIs em análise
    """
    try:
        import json
        from datetime import datetime
        
        dis = []
        
        # Buscar processos com DI registrada do Kanban
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                processo_referencia,
                numero_di,
                situacao_di,
                situacao_entrega,
                dados_completos_json
            FROM processos_kanban
            WHERE 
                numero_di IS NOT NULL 
                AND numero_di != ''
                AND numero_di != '/       -'
                AND (situacao_ce IS NULL OR situacao_ce != 'ENTREGUE')
        '''
        params = []
        if categoria:
            query += ' AND processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        
        # Processar cada processo
        for row in resultados:
            numero_di = row['numero_di']
            processo_ref = row['processo_referencia']
            
            # Buscar situação da DI (prioridade: JSON > campo da tabela)
            # ✅ CORREÇÃO: Buscar do campo da tabela, mas se estiver vazio, buscar do JSON
            situacao_di = row['situacao_di'] if row['situacao_di'] and row['situacao_di'].strip() else None
            situacao_entrega_carga = None  # ✅ NOVO: situacaoEntregaCarga do JSON
            situacao_entrega_tabela_temp = row['situacao_entrega'] if 'situacao_entrega' in row.keys() and row['situacao_entrega'] else None  # ✅ NOVO: Buscar do campo da tabela também
            canal_di = None  # ✅ NOVO: Canal da DI
            data_registro = None
            data_desembaraco = None
            
            try:
                if row['dados_completos_json']:
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # ✅ NOVO: Buscar situacaoEntregaCarga no nível raiz do JSON (da API externa)
                    situacao_entrega_carga = dados_json.get('situacaoEntregaCarga') or dados_json.get('situacao_entrega_carga')
                    
                    # ✅ NOVO: Buscar canal no nível raiz do JSON (para processos rodoviários como ARG)
                    canal_di = dados_json.get('canal') or dados_json.get('canal_di')
                    
                    # ✅ NOVO: Buscar situacaoDI no nível raiz (pode estar aqui para processos rodoviários)
                    if not situacao_di:
                        situacao_di = dados_json.get('situacaoDI') or dados_json.get('situacao_di')

                    # ✅ NOVO (16/01/2026): Buscar data de registro da DI no nível raiz (quando disponível)
                    if not data_registro:
                        data_registro = (
                            dados_json.get('dataHoraRegistro')
                            or dados_json.get('dataHoraRegistroDi')
                            or dados_json.get('dataRegistro')
                            or dados_json.get('data_registro')
                        )
                    
                    # ✅ NOVO: Buscar dataDesembaraco no nível raiz (para processos rodoviários)
                    if not data_desembaraco:
                        data_desembaraco = dados_json.get('dataDesembaraco') or dados_json.get('data_desembaraco') or dados_json.get('dataDesembaraco')
                    
                    # ✅ CORREÇÃO: Para processos rodoviários (ARG), sempre buscar dados no nível raiz
                    # mesmo que numeroDi não corresponda exatamente (pode ter formato diferente)
                    numero_di_json = dados_json.get('numeroDi') or dados_json.get('numero_di')
                    
                    # Se numeroDi corresponde, usar dados do nível raiz
                    if numero_di_json and str(numero_di_json) == str(numero_di):
                        # Se corresponde, usar dados do nível raiz (processos rodoviários)
                        if not situacao_di:
                            situacao_di = dados_json.get('situacaoDI') or dados_json.get('situacao_di')
                        if not canal_di:
                            canal_di = dados_json.get('canal') or dados_json.get('canal_di')
                        if not data_desembaraco:
                            data_desembaraco = dados_json.get('dataDesembaraco') or dados_json.get('data_desembaraco')
                        if not situacao_entrega_carga:
                            situacao_entrega_carga = dados_json.get('situacaoEntregaCarga') or dados_json.get('situacao_entrega_carga')
                    # ✅ NOVO: Se tem dados no nível raiz mas numeroDi não corresponde, usar mesmo assim
                    # (para processos rodoviários onde o formato pode ser diferente)
                    elif dados_json.get('situacaoDI') or dados_json.get('canal') or dados_json.get('situacaoEntregaCarga'):
                        # Tem dados no nível raiz, usar mesmo que numeroDi não corresponda
                        if not situacao_di:
                            situacao_di = dados_json.get('situacaoDI') or dados_json.get('situacao_di')
                        if not canal_di:
                            canal_di = dados_json.get('canal') or dados_json.get('canal_di')
                        if not data_desembaraco:
                            data_desembaraco = dados_json.get('dataDesembaraco') or dados_json.get('data_desembaraco')
                        if not situacao_entrega_carga:
                            situacao_entrega_carga = dados_json.get('situacaoEntregaCarga') or dados_json.get('situacao_entrega_carga')
                    
                    # A DI pode estar em dados_json['di'] (lista ou dict)
                    dis_json = dados_json.get('di', [])
                    
                    if isinstance(dis_json, list) and len(dis_json) > 0:
                        for di_item in dis_json:
                            if isinstance(di_item, dict):
                                numero_di_json = di_item.get('numero_di') or di_item.get('numero', '')
                                if numero_di_json == numero_di or not situacao_di:
                                    situacao_di = (
                                        di_item.get('situacao_di') or
                                        di_item.get('situacao') or
                                        situacao_di or
                                        ''
                                    )
                                    # ✅ NOVO: Buscar também situacao_entrega_carga dentro do objeto di
                                    if not situacao_entrega_carga:
                                        situacao_entrega_carga = di_item.get('situacao_entrega_carga') or di_item.get('situacaoEntregaCarga')
                                    # ✅ NOVO: Buscar canal dentro do objeto di
                                    if not canal_di:
                                        canal_di = (
                                            di_item.get('canal') or
                                            di_item.get('canal_selecao_parametrizada') or
                                            di_item.get('canal_di')
                                        )
                                    # ✅ NOVO: Buscar data de desembaraço dentro do objeto di
                                    if not data_desembaraco:
                                        data_desembaraco = (
                                            di_item.get('data_hora_desembaraco') or
                                            di_item.get('data_desembaraco') or
                                            di_item.get('dataDesembaraco')
                                        )
                                    # ✅ NOVO (16/01/2026): Cobrir variações de chave para data/hora de registro
                                    data_registro = (
                                        di_item.get('data_hora_registro')
                                        or di_item.get('data_registro')
                                        or di_item.get('dataHoraRegistro')
                                        or di_item.get('dataRegistro')
                                        or data_registro
                                    )
                                    break
                    elif isinstance(dis_json, dict):
                        numero_di_json = dis_json.get('numero_di') or dis_json.get('numero', '')
                        if numero_di_json == numero_di or not situacao_di:
                            situacao_di = (
                                dis_json.get('situacao_di') or
                                dis_json.get('situacao') or
                                situacao_di or
                                ''
                            )
                            # ✅ NOVO: Buscar também situacao_entrega_carga dentro do objeto di
                            if not situacao_entrega_carga:
                                situacao_entrega_carga = dis_json.get('situacao_entrega_carga') or dis_json.get('situacaoEntregaCarga')
                            # ✅ NOVO: Buscar canal dentro do objeto di
                            if not canal_di:
                                canal_di = (
                                    dis_json.get('canal') or
                                    dis_json.get('canal_selecao_parametrizada') or
                                    dis_json.get('canal_di')
                                )
                            # ✅ NOVO: Buscar data de desembaraço dentro do objeto di
                            if not data_desembaraco:
                                data_desembaraco = (
                                    dis_json.get('data_hora_desembaraco') or
                                    dis_json.get('data_desembaraco') or
                                    dis_json.get('dataDesembaraco')
                                )
                            # ✅ NOVO (16/01/2026): Cobrir variações de chave para data/hora de registro
                            data_registro = (
                                dis_json.get('data_hora_registro')
                                or dis_json.get('data_registro')
                                or dis_json.get('dataHoraRegistro')
                                or dis_json.get('dataRegistro')
                                or data_registro
                            )
            except Exception as e:
                logging.debug(f'Erro ao buscar situação DI do JSON para {processo_ref}: {e}')
            
            # ✅ NOVO: Usar situacao_entrega já buscada do campo da tabela (ou buscar se não tiver)
            situacao_entrega_tabela = None
            if situacao_entrega_tabela_temp:
                situacao_entrega_tabela = str(situacao_entrega_tabela_temp).upper()
            else:
                # Se não tinha no row, buscar separadamente
                try:
                    conn_check = get_db_connection()
                    cursor_check = conn_check.cursor()
                    cursor_check.row_factory = sqlite3.Row
                    cursor_check.execute('SELECT situacao_entrega FROM processos_kanban WHERE processo_referencia = ?', (processo_ref,))
                    row_entrega = cursor_check.fetchone()
                    conn_check.close()
                    
                    if row_entrega and row_entrega['situacao_entrega']:
                        situacao_entrega_tabela = str(row_entrega['situacao_entrega']).upper()
                except:
                    pass
            
            # ✅ CORREÇÃO: Lógica de exclusão atualizada conforme regras de negócio
            # Excluir apenas se:
            # 1. Está desembaraçada E tem entrega autorizada ou condicionada (ICMS)
            # 2. Ou tem "ENTREGA AUTORIZADA SEM PROSSEGUIMENTO"
            # 3. Ou tem "ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE ARRECADACAO DO ICMS"
            
            situacao_di_upper = str(situacao_di).upper() if situacao_di else ''
            situacao_entrega_carga_upper = str(situacao_entrega_carga).upper() if situacao_entrega_carga else ''
            
            # Verificar se está desembaraçada (apenas pela situação, não pela data)
            esta_desembaracada = (
                'DESEMBARACADA' in situacao_di_upper or 
                'DESEMBARACADO' in situacao_di_upper
            )
            
            # Verificar se tem entrega autorizada ou condicionada (ICMS)
            tem_entrega_autorizada = (
                'ENTREGA AUTORIZADA' in situacao_entrega_carga_upper or
                'ENTREGA AUTORIZADA' in situacao_entrega_tabela if situacao_entrega_tabela else False
            )
            
            tem_entrega_condicionada_icms = (
                'ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE ARRECADACAO DO ICMS' in situacao_entrega_carga_upper or
                'ENTREGA CONDICIONADA A APRESENTACAO E RETENCAO DOS SEGUINTES DOCUMENTOS: DOCUMENTO DE ARRECADACAO DO ICMS' in (situacao_entrega_tabela if situacao_entrega_tabela else '')
            )
            
            tem_entrega_autorizada_sem_prosseguimento = (
                'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO' in situacao_di_upper or
                'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO' in situacao_entrega_carga_upper or
                'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO' in (situacao_entrega_tabela if situacao_entrega_tabela else '')
            )
            
            # Excluir se:
            # - Está desembaraçada E (tem entrega autorizada OU tem entrega condicionada ICMS)
            # - OU tem entrega autorizada sem prosseguimento
            if (esta_desembaracada and (tem_entrega_autorizada or tem_entrega_condicionada_icms)) or tem_entrega_autorizada_sem_prosseguimento:
                continue
            
            # ✅ Todas as outras situações devem aparecer em análise (INTERROMPIDA, ENTREGA NAO AUTORIZADA, etc.)
            
            # Calcular tempo em análise
            tempo_analise = None
            if data_registro:
                try:
                    data_atual = datetime.now()
                    if isinstance(data_registro, str):
                        # Tentar vários formatos
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                            try:
                                data_reg = datetime.strptime(data_registro.split('.')[0].replace('Z', ''), fmt)
                                dias = (data_atual - data_reg).days
                                tempo_analise = f"{dias} dia(s)" if dias > 0 else "hoje"
                                break
                            except:
                                continue
                except:
                    pass
            
            dis.append({
                'numero_di': numero_di,
                'situacao_di': situacao_di,
                'canal_di': canal_di,  # ✅ NOVO: Canal da DI
                'situacao_entrega_carga': situacao_entrega_carga,  # ✅ NOVO: Incluir situação da entrega
                'situacao_entrega_tabela': situacao_entrega_tabela,  # ✅ NOVO: Incluir situação da entrega (tabela)
                'data_registro': data_registro,
                'data_desembaraco': data_desembaraco,  # ✅ NOVO: Data de desembaraço
                'processo_referencia': processo_ref,
                'tempo_analise': tempo_analise
            })
        
        return dis
    except Exception as e:
        logging.error(f'Erro ao obter DIs em análise: {e}')
        return []


def obter_processos_eta_alterado(categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Busca processos com ETA alterado comparando primeiro e último evento ARRV.
    Usa eventos do shipgov2 para detectar mudanças de ETA.
    
    ⚠️ IMPORTANTE: Retorna apenas processos ATIVOS/RELEVANTES para hoje:
    - Processos que ainda não chegaram (sem dataDestinoFinal)
    - Processos que chegaram recentemente (últimos 7 dias)
    - Processos com ETA futuro (último ETA >= hoje)
    
    Args:
        categoria: Filtro opcional por categoria
    
    Returns:
        Lista de processos com ETA alterado, incluindo diferença em dias
    """
    try:
        import json
        from datetime import datetime, date, timedelta
        
        hoje = date.today()
        limite_recente = hoje - timedelta(days=7)  # Processos que chegaram nos últimos 7 dias
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT processo_referencia, dados_completos_json, data_destino_final, porto_codigo, porto_nome
            FROM processos_kanban
            WHERE dados_completos_json IS NOT NULL
            AND dados_completos_json LIKE '%shipgov2%'
            AND dados_completos_json LIKE '%eventos%'
        '''
        
        params = []
        
        # Filtro por categoria
        if categoria:
            query += ' AND processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        conn.close()
        
        processos_com_mudanca = []
        
        for row in resultados:
            try:
                # ✅ FILTRO: Verificar se o processo é ativo/relevante
                data_destino_final = None
                if row['data_destino_final']:
                    try:
                        if isinstance(row['data_destino_final'], str):
                            if 'T' in row['data_destino_final']:
                                data_destino_final = datetime.fromisoformat(row['data_destino_final'].replace('Z', '+00:00')).date()
                            else:
                                data_destino_final = datetime.strptime(row['data_destino_final'], '%Y-%m-%d').date()
                        else:
                            data_destino_final = row['data_destino_final']
                    except:
                        pass
                
                dados_json = json.loads(row['dados_completos_json'])
                shipgov2 = dados_json.get('shipgov2', {})
                eventos = shipgov2.get('eventos', [])
                
                # ✅ OBTER PORTO DE DESTINO para filtrar apenas eventos ARRV desse porto
                porto_destino_codigo = row['porto_codigo']  # Ex: BRRIO
                porto_destino_nome = row['porto_nome']  # Ex: RIO DE JANEIRO
                
                if eventos:
                    # ✅ CRÍTICO: Filtrar apenas eventos ARRV do PORTO DE DESTINO FINAL
                    # Ignorar escalas intermediárias (ex: SINGAPORE, SHANGHAI, etc.)
                    eventos_arrv_destino = []
                    
                    for e in eventos:
                        if (isinstance(e, dict) 
                            and e.get('atual_evento') == 'ARRV' 
                            and e.get('atual_data_evento')):
                            
                            # Verificar se é do porto de destino
                            codigo_evento = e.get('atual_codigo', '')
                            nome_evento = e.get('atual_nome', '')
                            
                            # Comparar código do porto
                            if porto_destino_codigo and codigo_evento == porto_destino_codigo:
                                eventos_arrv_destino.append(e)
                            # Se não encontrou por código, tentar por nome (fallback)
                            elif porto_destino_nome and porto_destino_nome.upper() in str(nome_evento).upper():
                                eventos_arrv_destino.append(e)
                    
                    # ✅ ESTRATÉGIA: Comparar ETA original com ETA atual do porto de destino
                    primeiro_eta = None
                    ultimo_eta = None
                    primeiro_eta_str = None
                    ultimo_eta_str = None
                    
                    # OPÇÃO 1: Se há múltiplos eventos ARRV do porto de destino, usar o primeiro e último
                    if len(eventos_arrv_destino) > 1:
                        eventos_arrv_sorted = sorted(
                            eventos_arrv_destino, 
                            key=lambda x: x.get('atual_data_evento', '')
                        )
                        primeiro_eta_str = eventos_arrv_sorted[0].get('atual_data_evento')
                        ultimo_eta_str = eventos_arrv_sorted[-1].get('atual_data_evento')
                    
                    # OPÇÃO 2: Se há apenas 1 evento ARRV do porto de destino, comparar com destino_data_chegada
                    elif len(eventos_arrv_destino) == 1:
                        ultimo_eta_str = eventos_arrv_destino[0].get('atual_data_evento')
                        # Buscar ETA original em shipgov2.destino_data_chegada
                        if shipgov2.get('destino_data_chegada'):
                            primeiro_eta_str = shipgov2.get('destino_data_chegada')
                    
                    # OPÇÃO 3: Se não há eventos ARRV do porto de destino, usar dataPrevisaoChegada vs destino_data_chegada
                    elif len(eventos_arrv_destino) == 0:
                        # Buscar qualquer evento ARRV (pode ser de escala, mas é melhor que nada)
                        eventos_arrv_qualquer = [
                            e for e in eventos 
                            if isinstance(e, dict) 
                            and e.get('atual_evento') == 'ARRV' 
                            and e.get('atual_data_evento')
                        ]
                        if eventos_arrv_qualquer:
                            # Pegar o mais recente
                            eventos_arrv_sorted = sorted(
                                eventos_arrv_qualquer, 
                                key=lambda x: x.get('atual_data_evento', ''),
                                reverse=True
                            )
                            ultimo_eta_str = eventos_arrv_sorted[0].get('atual_data_evento')
                        
                        # ETA original: destino_data_chegada ou dataPrevisaoChegada
                        if shipgov2.get('destino_data_chegada'):
                            primeiro_eta_str = shipgov2.get('destino_data_chegada')
                        elif dados_json.get('dataPrevisaoChegada'):
                            primeiro_eta_str = dados_json.get('dataPrevisaoChegada')
                    
                    # ✅ Calcular diferença se temos ambos os ETAs
                    if primeiro_eta_str and ultimo_eta_str:
                        try:
                            # Parse do primeiro ETA
                            if 'T' in str(primeiro_eta_str):
                                primeiro_eta = datetime.fromisoformat(str(primeiro_eta_str).replace('Z', '+00:00')).date()
                            else:
                                primeiro_eta = datetime.strptime(str(primeiro_eta_str), '%Y-%m-%d').date()
                            
                            # Parse do último ETA
                            if 'T' in str(ultimo_eta_str):
                                ultimo_eta = datetime.fromisoformat(str(ultimo_eta_str).replace('Z', '+00:00')).date()
                            else:
                                ultimo_eta = datetime.strptime(str(ultimo_eta_str), '%Y-%m-%d').date()
                            
                            diferenca_dias = (ultimo_eta - primeiro_eta).days
                            
                            # Só incluir se houve mudança significativa (mais de 1 dia)
                            if abs(diferenca_dias) > 1:
                                # ✅ FILTRO CRÍTICO: Só incluir processos que AINDA NÃO CHEGARAM
                                # Objetivo: Mostrar apenas processos que estão atrasados/adiantados para chegar
                                # Processos que já chegaram não devem aparecer nesta seção
                                processo_nao_chegou = False
                                
                                # ✅ CORREÇÃO: Apenas processos que ainda não chegaram
                                # 1. Processo ainda não chegou (sem dataDestinoFinal) E último ETA >= hoje
                                if not data_destino_final and ultimo_eta >= hoje:
                                    processo_nao_chegou = True
                                
                                # 2. Processo ainda não chegou (sem dataDestinoFinal) E último ETA é futuro (mesmo que < hoje)
                                elif not data_destino_final and ultimo_eta > hoje:
                                    processo_nao_chegou = True
                                
                                # 3. Último ETA é futuro (ainda não chegou) - mesmo sem dataDestinoFinal confirmada
                                elif ultimo_eta >= hoje:
                                    processo_nao_chegou = True
                                
                                if processo_nao_chegou:
                                    tipo_mudanca = 'ATRASO' if diferenca_dias > 0 else 'ADIANTADO'
                                    
                                    processos_com_mudanca.append({
                                        'processo_referencia': row['processo_referencia'],
                                        'primeiro_eta': primeiro_eta_str,
                                        'ultimo_eta': ultimo_eta_str,
                                        'primeiro_eta_formatado': primeiro_eta.strftime('%d/%m/%Y'),
                                        'ultimo_eta_formatado': ultimo_eta.strftime('%d/%m/%Y'),
                                        'dias_diferenca': diferenca_dias,
                                        'tipo_mudanca': tipo_mudanca,
                                        'tipo_mudanca_descricao': f"{tipo_mudanca} de {abs(diferenca_dias)} dia(s)"
                                    })
                        except Exception as e:
                            logging.debug(f'Erro ao processar ETA do processo {row["processo_referencia"]}: {e}')
            except Exception as e:
                logging.debug(f'Erro ao processar processo {row["processo_referencia"]}: {e}')
        
        # Ordenar por diferença absoluta (maiores mudanças primeiro)
        processos_com_mudanca.sort(key=lambda x: abs(x['dias_diferenca']), reverse=True)
        
        return processos_com_mudanca
        
    except Exception as e:
        logging.error(f'Erro ao obter processos com ETA alterado: {e}', exc_info=True)
        return []


def obter_alertas_recentes(limite: int = 10, categoria: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Busca alertas recentes do sistema de notificações.
    
    Args:
        limite: Número máximo de alertas a retornar
        categoria: Filtro opcional por categoria (ex: 'ALH', 'VDM', 'MV5')
    
    Returns:
        Lista de alertas recentes com status atual quando aplicável
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                n.processo_referencia,
                n.tipo_notificacao,
                n.titulo,
                n.mensagem,
                n.criado_em,
                pk.situacao_ce,
                pk.situacao_di,
                pk.numero_di,
                pk.numero_duimp
            FROM notificacoes_processos n
            LEFT JOIN processos_kanban pk ON n.processo_referencia = pk.processo_referencia
            WHERE 
                DATE(n.criado_em) >= DATE('now', '-1 day')
        '''
        params = []
        if categoria:
            query += ' AND n.processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        query += ' ORDER BY n.criado_em DESC LIMIT ?'
        params.append(limite)
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        alertas = []
        for row in resultados:
            # ✅ NOVO: Para alertas de status, buscar status atual do processo
            status_atual = None
            tipo_alerta = row['tipo_notificacao'] or ''
            
            if 'status_ce' in tipo_alerta.lower():
                status_atual = row['situacao_ce']
            elif 'status_di' in tipo_alerta.lower():
                status_atual = row['situacao_di']
            elif 'status_duimp' in tipo_alerta.lower():
                # Para DUIMP, buscar do banco de DUIMPs
                numero_duimp = row['numero_duimp']
                processo_ref = row['processo_referencia']
                if numero_duimp:
                    try:
                        cursor.execute('''
                            SELECT status FROM duimps 
                            WHERE numero = ? AND (processo_referencia = ? OR processo_referencia IS NULL)
                            ORDER BY criado_em DESC LIMIT 1
                        ''', (numero_duimp, processo_ref))
                        duimp_row = cursor.fetchone()
                        if duimp_row:
                            status_atual = duimp_row['status']
                    except Exception as e:
                        logging.warning(f'Erro ao buscar status DUIMP para alerta: {e}')
            
            alertas.append({
                'processo_referencia': row['processo_referencia'],
                'tipo': tipo_alerta,
                'titulo': row['titulo'],
                'mensagem': row['mensagem'],
                'data': row['criado_em'],
                'status_atual': status_atual  # ✅ NOVO: Status atual do processo
            })
        
        conn.close()
        return alertas
    except Exception as e:
        logging.error(f'Erro ao obter alertas recentes: {e}')
        return []


def obter_movimentacoes_hoje(
    categoria: Optional[str] = None,
    modal: Optional[str] = None,
    dias_atras: int = 0,
) -> Dict[str, Any]:
    """
    Busca todas as movimentações do dia atual (fechamento do dia).
    
    Inclui:
    - Processos que chegaram hoje
    - Processos desembaraçados hoje
    - DUIMPs criadas hoje
    - Mudanças de status hoje (CE, DI, DUIMP)
    - Pendências resolvidas hoje
    
    Args:
        categoria: Filtro opcional por categoria (ex: 'ALH', 'VDM')
        modal: Filtro opcional por modal ('Marítimo', 'Aéreo')
    
    Returns:
        Dict com todas as movimentações do dia agrupadas por tipo
    """
    try:
        from datetime import datetime, timedelta
        import json
        
        # ✅ Usar data BR (America/Sao_Paulo) como referência (evita UTC causar “vazio”)
        try:
            from zoneinfo import ZoneInfo
            hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        except Exception:
            hoje = datetime.now().date()

        try:
            dias_atras_int = int(dias_atras or 0)
        except Exception:
            dias_atras_int = 0
        if dias_atras_int < 0:
            dias_atras_int = 0

        dia_ref = (hoje - timedelta(days=dias_atras_int))
        dia_ref_str = dia_ref.isoformat()
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        movimentacoes = {
            'data': dia_ref_str,
            'processos_chegaram': [],
            'processos_desembaracados': [],
            'duimps_criadas': [],
            'dis_registradas': [],  # ✅ CORRIGIDO: Lista separada para DIs registradas hoje
            'mudancas_status_ce': [],
            'mudancas_status_di': [],
            'mudancas_status_duimp': [],
            'pendencias_resolvidas': [],
            'total_movimentacoes': 0
        }
        
        # 1. Processos que chegaram hoje (data_destino_final = hoje)
        query_chegadas = '''
            SELECT 
                processo_referencia,
                modal,
                data_destino_final,
                numero_ce,
                situacao_ce,
                porto_nome
            FROM processos_kanban
            WHERE DATE(data_destino_final) = DATE(?)
        '''
        params_chegadas = [dia_ref_str]
        if categoria:
            query_chegadas += ' AND processo_referencia LIKE ?'
            params_chegadas.append(f'{categoria.upper()}.%')
        if modal:
            query_chegadas += ' AND modal = ?'
            params_chegadas.append(modal)
        query_chegadas += ' ORDER BY processo_referencia ASC'
        
        cursor.execute(query_chegadas, params_chegadas)
        for row in cursor.fetchall():
            movimentacoes['processos_chegaram'].append({
                'processo_referencia': row['processo_referencia'],
                'modal': row['modal'],
                'data_chegada': row['data_destino_final'],
                'numero_ce': row['numero_ce'],
                'situacao_ce': row['situacao_ce'],
                'porto_nome': row['porto_nome']
            })
        
        # 2. Processos armazenados hoje (data_armazenamento = hoje)
        # ✅ CORREÇÃO: Apenas incluir processos que foram armazenados hoje MAS que também chegaram hoje
        # Não incluir processos que chegaram antes mas foram armazenados hoje
        query_armazenados = '''
            SELECT 
                processo_referencia,
                modal,
                numero_ce,
                situacao_ce,
                data_armazenamento,
                data_destino_final
            FROM processos_kanban
            WHERE DATE(data_armazenamento) = DATE(?)
            AND (data_destino_final IS NULL OR DATE(data_destino_final) = DATE(?))
        '''
        params_armazenados = [dia_ref_str, dia_ref_str]
        if categoria:
            query_armazenados += ' AND processo_referencia LIKE ?'
            params_armazenados.append(f'{categoria.upper()}.%')
        if modal:
            query_armazenados += ' AND modal = ?'
            params_armazenados.append(modal)
        query_armazenados += ' ORDER BY processo_referencia ASC'
        
        cursor.execute(query_armazenados, params_armazenados)
        processos_armazenados_ids = set()
        for row in cursor.fetchall():
            # ✅ CORREÇÃO: Só adicionar se não foi já adicionado pela query de chegadas
            if row['processo_referencia'] not in [p['processo_referencia'] for p in movimentacoes['processos_chegaram']]:
                processos_armazenados_ids.add(row['processo_referencia'])
                movimentacoes['processos_chegaram'].append({
                    'processo_referencia': row['processo_referencia'],
                    'modal': row['modal'],
                    'data_chegada': row['data_armazenamento'],
                    'numero_ce': row['numero_ce'],
                    'situacao_ce': row['situacao_ce'],
                    'tipo': 'armazenado'
                })
        
        # 3. Processos desembaraçados hoje (data_desembaraco = hoje)
        # Buscar do Kanban primeiro
        query_desembaraco_kanban = '''
            SELECT 
                processo_referencia,
                modal,
                numero_di,
                numero_duimp,
                situacao_di,
                situacao_entrega,
                data_desembaraco
            FROM processos_kanban
            WHERE DATE(data_desembaraco) = DATE(?)
            AND (
                (situacao_di LIKE '%DESEMBARAC%' OR situacao_di LIKE '%ENTREGUE%')
                OR (situacao_entrega LIKE '%DESEMBARAC%' OR situacao_entrega LIKE '%ENTREGUE%')
            )
        '''
        params_desembaraco = [dia_ref_str]
        if categoria:
            query_desembaraco_kanban += ' AND processo_referencia LIKE ?'
            params_desembaraco.append(f'{categoria.upper()}.%')
        if modal:
            query_desembaraco_kanban += ' AND modal = ?'
            params_desembaraco.append(modal)
        query_desembaraco_kanban += ' ORDER BY processo_referencia ASC'
        
        cursor.execute(query_desembaraco_kanban, params_desembaraco)
        processos_desembaracados_kanban = {}
        for row in cursor.fetchall():
            processos_desembaracados_kanban[row['processo_referencia']] = {
                'processo_referencia': row['processo_referencia'],
                'modal': row['modal'],
                'numero_di': row['numero_di'],
                'numero_duimp': row['numero_duimp'],
                'situacao_di': row['situacao_di'],
                'situacao_entrega': row['situacao_entrega'],
                'data_desembaraco': row['data_desembaraco']
            }
        
        # Buscar também do cache de DIs (data_hora_desembaraco = hoje)
        query_desembaraco_cache = '''
            SELECT DISTINCT
                pd.processo_referencia,
                di.numero_di,
                di.data_hora_desembaraco,
                di.situacao_di
            FROM processo_documentos pd
            INNER JOIN dis_cache di ON pd.numero_documento = di.numero_di
            WHERE pd.tipo_documento = 'DI'
            AND DATE(di.data_hora_desembaraco) = DATE(?)
            AND (di.situacao_di LIKE '%DESEMBARAC%' OR di.situacao_di LIKE '%ENTREGUE%')
        '''
        params_desembaraco_cache = [dia_ref_str]
        if categoria:
            query_desembaraco_cache += ' AND pd.processo_referencia LIKE ?'
            params_desembaraco_cache.append(f'{categoria.upper()}.%')
        query_desembaraco_cache += ' ORDER BY pd.processo_referencia ASC'
        
        cursor.execute(query_desembaraco_cache, params_desembaraco_cache)
        for row in cursor.fetchall():
            proc_ref = row['processo_referencia']
            # Se já não está na lista do Kanban, adicionar
            if proc_ref not in processos_desembaracados_kanban:
                # Buscar dados do processo do Kanban
                cursor.execute('''
                    SELECT modal, numero_duimp, situacao_entrega
                    FROM processos_kanban
                    WHERE processo_referencia = ?
                    LIMIT 1
                ''', (proc_ref,))
                kanban_row = cursor.fetchone()
                
                movimentacoes['processos_desembaracados'].append({
                    'processo_referencia': proc_ref,
                    'modal': kanban_row['modal'] if kanban_row else None,
                    'numero_di': row['numero_di'],
                    'numero_duimp': kanban_row['numero_duimp'] if kanban_row else None,
                    'situacao_di': row['situacao_di'],
                    'situacao_entrega': kanban_row['situacao_entrega'] if kanban_row else None,
                    'data_desembaraco': row['data_hora_desembaraco']
                })
        
        # Adicionar processos do Kanban que não estão no cache
        for proc_ref, dados in processos_desembaracados_kanban.items():
            movimentacoes['processos_desembaracados'].append(dados)
        
        # ✅ NOVO: Adicionar processos com DUIMP desembaraçada que tiveram mudança de status hoje
        # Se um processo está em "mudancas_status_duimp" com status DESEMBARACADA, incluir em "processos_desembaracados"
        # Isso será feito DEPOIS de buscar as mudanças de status DUIMP (mais abaixo)
        
        # 4. DIs/DUIMPs registradas hoje (data_registro = hoje)
        # ✅ PRIORIDADE 1: Buscar DIs registradas hoje do SQL Server (fonte mais confiável)
        # ✅ CORREÇÃO: Usar adapter (Node.js no Mac) ao invés de pyodbc direto
        dis_registradas_sql_server = []
        try:
            from utils.sql_server_adapter import get_sql_adapter
            from datetime import datetime, date
            
            sql_adapter = get_sql_adapter()
            
            # Buscar DIs registradas hoje do SQL Server
            # ✅ CORREÇÃO: Usar vínculo correto via id_importacao (como na query di_kanban.sql)
            # Buscar através de: Hi_Historico_Di.idImportacao → comex.dbo.Importacoes.id → make.dbo.PROCESSO_IMPORTACAO.id_importacao
            query_sql_server = '''
                SELECT DISTINCT
                    ddg.numeroDi,
                    diDesp.dataHoraRegistro,
                    ddg.situacaoDi,
                    diDesp.canalSelecaoParametrizada,
                    pi.numero_processo AS processo_referencia
                FROM Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
                INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                    ON diH.diId = diRoot.dadosDiId
                INNER JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                INNER JOIN comex.dbo.Importacoes i WITH (NOLOCK)
                    ON i.id = diH.idImportacao
                INNER JOIN make.dbo.PROCESSO_IMPORTACAO pi WITH (NOLOCK)
                    ON pi.id_importacao = i.id
                WHERE CAST(diDesp.dataHoraRegistro AS DATE) = CAST(GETDATE() AS DATE)
                AND diDesp.dataHoraRegistro IS NOT NULL
            '''
            # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?, usar interpolação de string
            if categoria:
                categoria_upper = categoria.upper()
                categoria_escaped = categoria_upper.replace("'", "''")
                query_sql_server += f" AND pi.numero_processo LIKE '{categoria_escaped}.%'"
            
            query_sql_server += ' ORDER BY diDesp.dataHoraRegistro DESC'
            
            logging.info(f'🔍 [FECHAMENTO DIA] Buscando DIs registradas hoje no SQL Server (categoria={categoria})')
            result = sql_adapter.execute_query(query_sql_server, 'Serpro', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
            
            if result.get('success') and result.get('data'):
                rows_di = result['data']
                logging.info(f'🔍 [FECHAMENTO DIA] SQL Server retornou {len(rows_di)} DI(s) registrada(s) hoje')
                
                for sql_row in rows_di:
                    # O adapter retorna dict, não tuple
                    if isinstance(sql_row, dict):
                        numero_di = sql_row.get('numeroDi') or sql_row.get('numero_di')
                        data_hora_registro = sql_row.get('dataHoraRegistro') or sql_row.get('data_hora_registro')
                        situacao_di = sql_row.get('situacaoDi') or sql_row.get('situacao_di') or ''
                        canal = sql_row.get('canalSelecaoParametrizada') or sql_row.get('canal_selecao_parametrizada') or ''
                        processo_ref = sql_row.get('processo_referencia') or ''
                    else:
                        # Fallback para tuple (caso retorne assim)
                        numero_di = sql_row[0] if len(sql_row) > 0 else None
                        data_hora_registro = sql_row[1] if len(sql_row) > 1 else None
                        situacao_di = sql_row[2] if len(sql_row) > 2 else ''
                        canal = sql_row[3] if len(sql_row) > 3 else ''
                        processo_ref = sql_row[4] if len(sql_row) > 4 else ''
                    
                    if not numero_di:
                        continue
                    
                    # ✅ CORREÇÃO: Buscar status ATUAL da DI (não o status do momento do registro)
                    # O status pode ter mudado após o registro, então precisamos buscar o status mais recente
                    situacao_di_atual = situacao_di  # Usar como fallback
                    canal_atual = canal  # Usar como fallback
                    try:
                        # Buscar status atual da DI do SQL Server
                        # ✅ CORREÇÃO: Ordenar por desembaraço primeiro para pegar status mais atualizado
                        query_status_atual = f'''
                            SELECT TOP 1
                                ddg.situacaoDi,
                                diDesp.canalSelecaoParametrizada,
                                diDesp.dataHoraDesembaraco
                            FROM Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                                ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                            INNER JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                                ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                            WHERE ddg.numeroDi = '{numero_di}'
                            ORDER BY 
                                CASE WHEN diDesp.dataHoraDesembaraco IS NOT NULL THEN 0 ELSE 1 END,
                                diDesp.dataHoraDesembaraco DESC,
                                diDesp.dataHoraRegistro DESC
                        '''
                        result_status = sql_adapter.execute_query(query_status_atual, 'Serpro', [], notificar_erro=False)
                        if result_status.get('success') and result_status.get('data'):
                            rows_status = result_status['data']
                            if rows_status and len(rows_status) > 0:
                                row_status = rows_status[0]
                                if isinstance(row_status, dict):
                                    situacao_di_atual = row_status.get('situacaoDi') or row_status.get('situacao_di') or situacao_di
                                    canal_atual = row_status.get('canalSelecaoParametrizada') or row_status.get('canal_selecao_parametrizada') or canal
                                else:
                                    situacao_di_atual = row_status[0] if len(row_status) > 0 else situacao_di
                                    canal_atual = row_status[1] if len(row_status) > 1 else canal
                                
                                if situacao_di_atual != situacao_di:
                                    logging.info(f'🔄 [FECHAMENTO DIA] Status da DI {numero_di} atualizado na busca inicial: {situacao_di} → {situacao_di_atual}')
                    except Exception as e:
                        logging.debug(f'⚠️ [FECHAMENTO DIA] Erro ao buscar status atual da DI {numero_di}: {e}')
                        # Usar status original se falhar
                    
                    # Se não veio na query, tentar do cache como fallback
                    if not processo_ref:
                        cursor.execute('''
                            SELECT processo_referencia
                            FROM processo_documentos
                            WHERE tipo_documento = 'DI' AND numero_documento = ?
                            LIMIT 1
                        ''', (numero_di,))
                        proc_row_cache = cursor.fetchone()
                        if proc_row_cache:
                            processo_ref = proc_row_cache['processo_referencia']
                    
                    # ✅ CORREÇÃO: Adicionar mesmo sem processo_referencia (pode ser DI órfã)
                    # Mas logar como warning para investigar
                    if not processo_ref:
                        logging.warning(f'⚠️ [FECHAMENTO DIA] DI {numero_di} registrada hoje mas sem processo_referencia encontrado')
                    
                    # Adicionar à lista mesmo sem processo_referencia (para não perder a informação)
                    if True:  # Sempre adicionar, mesmo sem processo_referencia
                        # Verificar se já está na lista (CORRIGIDO: verificar em dis_registradas, não duimps_criadas)
                        ja_na_lista = any(
                            d.get('numero') == numero_di 
                            for d in movimentacoes['dis_registradas']
                        )
                        if not ja_na_lista:
                            # Converter dataHoraRegistro para string ISO
                            if isinstance(data_hora_registro, datetime):
                                data_registro_str = data_hora_registro.isoformat()
                            elif isinstance(data_hora_registro, date):
                                data_registro_str = data_hora_registro.isoformat()
                            else:
                                data_registro_str = str(data_hora_registro) if data_hora_registro else None
                            
                            dis_registradas_sql_server.append({
                                'numero': numero_di,
                                'status': situacao_di_atual,  # ✅ Usar status ATUAL, não o do momento do registro
                                'ambiente': 'producao',
                                'processo_referencia': processo_ref or 'N/A',  # Permitir N/A se não encontrou
                                'criado_em': data_registro_str,
                                'tipo': 'DI',
                                'canal': canal_atual  # ✅ Usar canal ATUAL
                            })
                            logging.info(f'✅ [FECHAMENTO DIA] DI {numero_di} adicionada (processo: {processo_ref or "N/A"}, status atual: {situacao_di_atual}, data: {data_registro_str})')
            else:
                error_msg = result.get('error', 'Erro desconhecido')
                logging.warning(f'⚠️ [FECHAMENTO DIA] Não foi possível buscar DIs registradas hoje do SQL Server: {error_msg}')
        except Exception as e:
            logging.error(f'❌ [FECHAMENTO DIA] Erro ao buscar DIs registradas hoje do SQL Server: {e}', exc_info=True)
        
        # Adicionar DIs do SQL Server à lista (CORRIGIDO: adicionar em dis_registradas, não duimps_criadas)
        logging.info(f'🔍 [FECHAMENTO DIA] Adicionando {len(dis_registradas_sql_server)} DI(s) do SQL Server à lista')
        for di_sql in dis_registradas_sql_server:
            movimentacoes['dis_registradas'].append(di_sql)
            logging.info(f'✅ [FECHAMENTO DIA] DI {di_sql.get("numero")} adicionada (processo: {di_sql.get("processo_referencia")})')
        
        # ✅ PRIORIDADE 2: Buscar DIs registradas hoje do cache SQLite (fallback)
        query_dis_registradas = '''
            SELECT DISTINCT
                pd.processo_referencia,
                di.numero_di,
                di.data_hora_registro,
                di.situacao_di,
                di.canal_selecao_parametrizada
            FROM processo_documentos pd
            INNER JOIN dis_cache di ON pd.numero_documento = di.numero_di
            WHERE pd.tipo_documento = 'DI'
            AND DATE(di.data_hora_registro) = DATE('now')
            AND di.data_hora_registro IS NOT NULL
        '''
        params_dis_registradas = []
        if categoria:
            query_dis_registradas += ' AND pd.processo_referencia LIKE ?'
            params_dis_registradas.append(f'{categoria.upper()}.%')
        query_dis_registradas += ' ORDER BY pd.processo_referencia ASC'
        
        cursor.execute(query_dis_registradas, params_dis_registradas)
        rows_cache_di = cursor.fetchall()
        logging.info(f'🔍 [FECHAMENTO DIA] Cache SQLite retornou {len(rows_cache_di)} DI(s) registrada(s) hoje')
        dis_cache_numeros = {d.get('numero') for d in movimentacoes['dis_registradas']}  # ✅ CORRIGIDO: verificar em dis_registradas
        for row in rows_cache_di:
            numero_di = row['numero_di']
            # Só adicionar se não estiver já na lista (do SQL Server)
            if numero_di not in dis_cache_numeros:
                # ✅ CORREÇÃO: Buscar status ATUAL da DI (não o status do cache que pode estar desatualizado)
                situacao_di_cache = row['situacao_di']
                canal_cache = row.get('canal_selecao_parametrizada', '')
                
                # Tentar buscar status atual do SQL Server
                try:
                    from utils.sql_server_adapter import get_sql_adapter
                    sql_adapter_cache = get_sql_adapter()
                    query_status_cache = f'''
                        SELECT TOP 1
                            ddg.situacaoDi,
                            diDesp.canalSelecaoParametrizada,
                            diDesp.dataHoraDesembaraco
                        FROM Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                        INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                            ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                        INNER JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                            ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                        WHERE ddg.numeroDi = '{numero_di}'
                        ORDER BY 
                            CASE WHEN diDesp.dataHoraDesembaraco IS NOT NULL THEN 0 ELSE 1 END,
                            diDesp.dataHoraDesembaraco DESC,
                            diDesp.dataHoraRegistro DESC
                    '''
                    result_status_cache = sql_adapter_cache.execute_query(query_status_cache, 'Serpro', [], notificar_erro=False)
                    if result_status_cache.get('success') and result_status_cache.get('data'):
                        rows_status_cache = result_status_cache['data']
                        if rows_status_cache and len(rows_status_cache) > 0:
                            row_status_cache = rows_status_cache[0]
                            if isinstance(row_status_cache, dict):
                                situacao_di_cache = row_status_cache.get('situacaoDi') or row_status_cache.get('situacao_di') or situacao_di_cache
                                canal_cache = row_status_cache.get('canalSelecaoParametrizada') or row_status_cache.get('canal_selecao_parametrizada') or canal_cache
                            else:
                                situacao_di_cache = row_status_cache[0] if len(row_status_cache) > 0 else situacao_di_cache
                                canal_cache = row_status_cache[1] if len(row_status_cache) > 1 else canal_cache
                            
                            if situacao_di_cache != row['situacao_di']:
                                logging.info(f'🔄 [FECHAMENTO DIA] Status da DI {numero_di} do cache atualizado: {row["situacao_di"]} → {situacao_di_cache}')
                except Exception as e:
                    logging.debug(f'⚠️ [FECHAMENTO DIA] Erro ao buscar status atual da DI {numero_di} do cache: {e}')
                    # Usar status do cache se falhar
                
                # ✅ CORRIGIDO: Adicionar em dis_registradas, não duimps_criadas (DIs não têm versão)
                movimentacoes['dis_registradas'].append({
                    'numero': numero_di,
                    'status': situacao_di_cache,  # ✅ Usar status ATUAL
                    'ambiente': 'producao',
                    'processo_referencia': row['processo_referencia'],
                    'criado_em': row['data_hora_registro'],
                    'tipo': 'DI',
                    'canal': canal_cache  # ✅ Usar canal ATUAL
                })
                dis_cache_numeros.add(numero_di)
        
        # ✅ PRIORIDADE 1: Buscar DUIMPs registradas hoje do SQL Server (fonte mais confiável)
        # Para DUIMP, não há data/hora de registro, apenas a data máxima de gravação no banco
        # Usar situação REGISTRADA_AGUARDANDO_CANAL para identificar DUIMPs registradas
        # ✅ CORREÇÃO: Usar adapter (Node.js no Mac) ao invés de pyodbc direto
        duimps_registradas_sql_server = []
        try:
            from utils.sql_server_adapter import get_sql_adapter
            from datetime import datetime, date
            
            sql_adapter = get_sql_adapter()
            
            # Buscar DUIMPs registradas hoje do SQL Server
            # ✅ CRÍTICO: Para DUIMP, a situação pode mudar no mesmo dia após o registro
            # Preciso buscar no HISTÓRICO (duimp_diagnostico) quando a situação mudou para REGISTRADA_AGUARDANDO_CANAL HOJE
            # Não confiar apenas na situação atual, porque ela pode ter mudado depois
            query_duimp_sql_server = '''
                SELECT DISTINCT
                    d.numero,
                    d.versao,
                    d.numero_processo,
                    dd.data_geracao AS data_registro_historico,
                    dd.situacao_duimp AS situacao_historico,
                    d.data_ultimo_evento,
                    d.ultima_situacao AS situacao_atual
                FROM duimp.dbo.duimp d WITH (NOLOCK)
                INNER JOIN duimp.dbo.duimp_diagnostico dd WITH (NOLOCK)
                    ON dd.duimp_id = d.duimp_id
                WHERE CAST(dd.data_geracao AS DATE) = CAST(GETDATE() AS DATE)
                AND (
                    dd.situacao_duimp LIKE '%REGISTRADA%AGUARDANDO%CANAL%'
                    OR dd.situacao_duimp LIKE '%REGISTRADA_AGUARDANDO_CANAL%'
                    OR dd.situacao LIKE '%REGISTRADA%AGUARDANDO%CANAL%'
                    OR dd.situacao LIKE '%REGISTRADA_AGUARDANDO_CANAL%'
                    OR dd.situacao_duimp LIKE '%CARGA%REGISTRADA%'
                    OR dd.situacao LIKE '%CARGA%REGISTRADA%'
                )
            '''
            # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?, usar interpolação de string
            if categoria:
                categoria_upper = categoria.upper()
                categoria_escaped = categoria_upper.replace("'", "''")
                query_duimp_sql_server += f" AND d.numero_processo LIKE '{categoria_escaped}.%'"
            
            query_duimp_sql_server += ' ORDER BY dd.data_geracao DESC'
            
            logging.info(f'🔍 [FECHAMENTO DIA] Buscando DUIMPs registradas hoje no SQL Server (histórico de diagnósticos, categoria={categoria})')
            result = sql_adapter.execute_query(query_duimp_sql_server, 'duimp', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
            
            if result.get('success') and result.get('data'):
                rows_duimp = result['data']
                logging.info(f'🔍 [FECHAMENTO DIA] SQL Server retornou {len(rows_duimp)} DUIMP(s) registrada(s) hoje (do histórico)')
                
                for sql_row in rows_duimp:
                    # O adapter retorna dict, não tuple
                    if isinstance(sql_row, dict):
                        numero_duimp = sql_row.get('numero')
                        versao_duimp = sql_row.get('versao') or 'N/A'
                        processo_ref_raw = sql_row.get('numero_processo') or ''
                        data_registro_historico = sql_row.get('data_registro_historico') or sql_row.get('data_geracao')
                        situacao_historico = sql_row.get('situacao_historico') or sql_row.get('situacao_duimp') or 'REGISTRADA_AGUARDANDO_CANAL'
                        data_ultimo_evento = sql_row.get('data_ultimo_evento')
                        situacao_atual = sql_row.get('situacao_atual') or sql_row.get('ultima_situacao') or ''
                    else:
                        # Fallback para tuple
                        numero_duimp = sql_row[0] if len(sql_row) > 0 else None
                        versao_duimp = sql_row[1] if len(sql_row) > 1 else 'N/A'
                        processo_ref_raw = sql_row[2] if len(sql_row) > 2 else ''
                        data_registro_historico = sql_row[3] if len(sql_row) > 3 else None
                        situacao_historico = sql_row[4] if len(sql_row) > 4 else 'REGISTRADA_AGUARDANDO_CANAL'
                        data_ultimo_evento = sql_row[5] if len(sql_row) > 5 else None
                        situacao_atual = sql_row[6] if len(sql_row) > 6 else ''
                    
                    if not numero_duimp:
                        continue
                    
                    # ✅ Usar data_geracao do histórico (quando mudou para REGISTRADA_AGUARDANDO_CANAL)
                    # Esta é a data real de registro, mesmo que a situação tenha mudado depois
                    data_gravacao = data_registro_historico if data_registro_historico else data_ultimo_evento
                    situacao_duimp = situacao_historico  # Usar situação do histórico (quando foi registrada)
                    
                    # ✅ Buscar processo_referencia se não veio na query
                    processo_ref = processo_ref_raw
                    if not processo_ref:
                        try:
                            # Tentar buscar de make.dbo.PROCESSO_IMPORTACAO usando adapter
                            query_proc = f'''
                                SELECT TOP 1 numero_processo
                                FROM make.dbo.PROCESSO_IMPORTACAO WITH (NOLOCK)
                                WHERE numero_duimp = '{numero_duimp}'
                            '''
                            result_proc = sql_adapter.execute_query(query_proc, 'Make', [], notificar_erro=False)
                            if result_proc.get('success') and result_proc.get('data'):
                                proc_rows = result_proc['data']
                                if proc_rows and len(proc_rows) > 0:
                                    processo_ref = proc_rows[0].get('numero_processo') or ''
                        except Exception as e:
                            logging.debug(f'⚠️ [FECHAMENTO DIA] Erro ao buscar processo_referencia para DUIMP {numero_duimp}: {e}')
                    
                    # ✅ CORREÇÃO: Adicionar mesmo sem processo_referencia (pode ser DUIMP órfã)
                    # Mas logar como warning para investigar
                    if not processo_ref:
                        logging.warning(f'⚠️ [FECHAMENTO DIA] DUIMP {numero_duimp} registrada hoje mas sem processo_referencia encontrado')
                    
                    # Adicionar à lista mesmo sem processo_referencia (para não perder a informação)
                    if True:  # Sempre adicionar, mesmo sem processo_referencia
                        # Verificar se já está na lista
                        ja_na_lista = any(
                            d.get('numero') == numero_duimp 
                            for d in movimentacoes['duimps_criadas']
                        )
                        if not ja_na_lista:
                            # Converter data para string ISO
                            if isinstance(data_gravacao, datetime):
                                data_gravacao_str = data_gravacao.isoformat()
                            elif isinstance(data_gravacao, date):
                                data_gravacao_str = data_gravacao.isoformat()
                            else:
                                data_gravacao_str = str(data_gravacao) if data_gravacao else None
                            
                            duimps_registradas_sql_server.append({
                                'numero': numero_duimp,
                                'versao': versao_duimp,
                                'status': situacao_duimp,
                                'ambiente': 'producao',
                                'processo_referencia': processo_ref or 'N/A',  # Permitir N/A se não encontrou
                                'criado_em': data_gravacao_str,
                                'tipo': 'DUIMP',
                                'fonte': 'sql_server'
                            })
                            logging.info(f'✅ [FECHAMENTO DIA] DUIMP {numero_duimp} adicionada (processo: {processo_ref or "N/A"}, situação: {situacao_duimp}, data: {data_gravacao_str})')
            else:
                error_msg = result.get('error', 'Erro desconhecido')
                logging.warning(f'⚠️ [FECHAMENTO DIA] Não foi possível buscar DUIMPs registradas hoje do SQL Server: {error_msg}')
        except Exception as e:
            logging.error(f'❌ [FECHAMENTO DIA] Erro ao buscar DUIMPs registradas hoje do SQL Server: {e}', exc_info=True)
        
        # Adicionar DUIMPs do SQL Server à lista
        logging.info(f'🔍 [FECHAMENTO DIA] Adicionando {len(duimps_registradas_sql_server)} DUIMP(s) do SQL Server à lista')
        for duimp_sql in duimps_registradas_sql_server:
            movimentacoes['duimps_criadas'].append(duimp_sql)
            logging.info(f'✅ [FECHAMENTO DIA] DUIMP {duimp_sql.get("numero")} adicionada (processo: {duimp_sql.get("processo_referencia")}, situação: {duimp_sql.get("status")})')
        
        # ✅ PRIORIDADE 2: Buscar DUIMPs criadas hoje do cache SQLite (fallback)
        query_duimps_criadas = '''
            SELECT 
                d.numero,
                d.versao,
                d.status,
                d.ambiente,
                d.processo_referencia,
                d.criado_em
            FROM duimps d
            WHERE DATE(d.criado_em) = DATE('now')
        '''
        params_duimps_criadas = []
        if categoria:
            query_duimps_criadas += ' AND d.processo_referencia LIKE ?'
            params_duimps_criadas.append(f'{categoria.upper()}.%')
        query_duimps_criadas += ' ORDER BY d.criado_em DESC'
        
        cursor.execute(query_duimps_criadas, params_duimps_criadas)
        rows_cache_duimp = cursor.fetchall()
        logging.info(f'🔍 [FECHAMENTO DIA] Cache SQLite retornou {len(rows_cache_duimp)} DUIMP(s) criada(s) hoje')
        duimps_cache_numeros = {d.get('numero') for d in movimentacoes['duimps_criadas']}
        for row in rows_cache_duimp:
            numero_duimp = row['numero']
            # Só adicionar se não estiver já na lista (do SQL Server)
            if numero_duimp not in duimps_cache_numeros:
                movimentacoes['duimps_criadas'].append({
                    'numero': numero_duimp,
                    'versao': row['versao'],
                    'status': row['status'],
                    'ambiente': row['ambiente'],
                    'processo_referencia': row['processo_referencia'],
                    'criado_em': row['criado_em'],
                    'tipo': 'DUIMP'
                })
                duimps_cache_numeros.add(numero_duimp)
        
        # 5b. DUIMPs registradas hoje (dataRegistro no payload = hoje)
        query_duimps_registradas = '''
            SELECT 
                d.numero,
                d.versao,
                d.status,
                d.ambiente,
                d.processo_referencia,
                d.atualizado_em,
                d.payload_completo
            FROM duimps d
            WHERE d.processo_referencia IS NOT NULL
            AND d.processo_referencia != ''
        '''
        params_duimps_registradas = []
        if categoria:
            query_duimps_registradas += ' AND d.processo_referencia LIKE ?'
            params_duimps_registradas.append(f'{categoria.upper()}.%')
        query_duimps_registradas += ' ORDER BY d.atualizado_em DESC'
        
        cursor.execute(query_duimps_registradas, params_duimps_registradas)
        duimps_registradas_hoje = []
        for row in cursor.fetchall():
            # Extrair dataRegistro do payload
            try:
                payload_json = json.loads(row['payload_completo']) if row['payload_completo'] else {}
                identificacao = payload_json.get('identificacao', {})
                data_registro = identificacao.get('dataRegistro')
                
                if data_registro:
                    # Parsear data de registro
                    from datetime import datetime
                    data_limpa = str(data_registro).replace('Z', '').replace('+00:00', '').strip()
                    if '.' in data_limpa:
                        data_limpa = data_limpa.split('.')[0]
                    
                    dt_registro = None
                    if 'T' in data_limpa:
                        try:
                            dt_registro = datetime.fromisoformat(data_limpa)
                        except:
                            pass
                    
                    if not dt_registro:
                        formatos = [
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%d %H:%M:%S", 
                            "%Y-%m-%d"
                        ]
                        for fmt in formatos:
                            try:
                                dt_registro = datetime.strptime(data_limpa, fmt)
                                break
                            except:
                                continue
                    
                    if dt_registro and dt_registro.date() == hoje:
                        # DUIMP foi registrada hoje
                        duimps_registradas_hoje.append({
                            'numero': row['numero'],
                            'versao': row['versao'],
                            'status': row['status'],
                            'ambiente': row['ambiente'],
                            'processo_referencia': row['processo_referencia'],
                            'criado_em': row['atualizado_em'],
                            'data_registro': data_registro,
                            'tipo': 'DUIMP'
                        })
            except Exception as e:
                logging.debug(f'Erro ao extrair dataRegistro da DUIMP {row["numero"]}: {e}')
        
        # Adicionar DUIMPs registradas hoje (se não já estiverem em duimps_criadas)
        duimps_criadas_numeros = {d['numero'] for d in movimentacoes['duimps_criadas']}
        for duimp_reg in duimps_registradas_hoje:
            if duimp_reg['numero'] not in duimps_criadas_numeros:
                movimentacoes['duimps_criadas'].append(duimp_reg)
        
        # 5c. DUIMPs com mudança de status hoje (atualizado_em = hoje e status mudou)
        query_duimps_status_hoje = '''
            SELECT 
                d.numero,
                d.versao,
                d.status,
                d.ambiente,
                d.processo_referencia,
                d.atualizado_em
            FROM duimps d
            WHERE DATE(d.atualizado_em) = DATE('now')
            AND d.status IS NOT NULL
            AND d.status != ''
            AND d.status != 'rascunho'
        '''
        params_duimps_status = []
        if categoria:
            query_duimps_status_hoje += ' AND d.processo_referencia LIKE ?'
            params_duimps_status.append(f'{categoria.upper()}.%')
        query_duimps_status_hoje += ' ORDER BY d.atualizado_em DESC'
        
        cursor.execute(query_duimps_status_hoje, params_duimps_status)
        duimps_status_hoje_numeros = set()
        for row in cursor.fetchall():
            duimp_num = row['numero']
            # Evitar duplicatas
            if duimp_num in duimps_status_hoje_numeros:
                continue
            duimps_status_hoje_numeros.add(duimp_num)
            
            # Verificar se já está na lista de mudanças de status
            ja_na_lista = any(
                m.get('numero_duimp') == duimp_num 
                for m in movimentacoes['mudancas_status_duimp']
            )
            
            if not ja_na_lista:
                # ✅ Enriquecer com data real do evento (ex.: desembaraço) quando disponível
                data_desembaraco = None
                try:
                    cursor.execute(
                        "SELECT data_desembaraco FROM processos_kanban WHERE processo_referencia = ? LIMIT 1",
                        (row['processo_referencia'],),
                    )
                    row_dt = cursor.fetchone()
                    if row_dt and row_dt['data_desembaraco']:
                        data_desembaraco = row_dt['data_desembaraco']
                except Exception:
                    data_desembaraco = None

                movimentacoes['mudancas_status_duimp'].append({
                    'processo_referencia': row['processo_referencia'],
                    'numero_duimp': duimp_num,
                    'status': row['status'],
                    'ambiente': row['ambiente'],
                    'atualizado_em': row['atualizado_em'],
                    'data_desembaraco': data_desembaraco,
                })
        
        # 5d. DUIMPs do Kanban registradas hoje (buscar dataRegistro do JSON do Kanban)
        query_duimp_kanban_registradas = '''
            SELECT 
                pk.processo_referencia,
                pk.modal,
                pk.numero_duimp,
                pk.atualizado_em,
                pk.dados_completos_json
            FROM processos_kanban pk
            WHERE pk.numero_duimp IS NOT NULL
            AND pk.numero_duimp != ''
            AND DATE(pk.atualizado_em) = DATE('now')
        '''
        params_duimp_kanban_reg = []
        if categoria:
            query_duimp_kanban_registradas += ' AND pk.processo_referencia LIKE ?'
            params_duimp_kanban_reg.append(f'{categoria.upper()}.%')
        if modal:
            query_duimp_kanban_registradas += ' AND pk.modal = ?'
            params_duimp_kanban_reg.append(modal)
        query_duimp_kanban_registradas += ' ORDER BY pk.processo_referencia ASC'
        
        cursor.execute(query_duimp_kanban_registradas, params_duimp_kanban_reg)
        for row in cursor.fetchall():
            proc_ref = row['processo_referencia']
            duimp_num = row['numero_duimp']
            
            # Extrair dataRegistro do JSON do Kanban
            data_registro_hoje = False
            if row['dados_completos_json']:
                try:
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # Buscar dataRegistro em vários lugares possíveis
                    data_registro = None
                    
                    # 1. Tentar em identificacao.dataRegistro (estrutura padrão)
                    if dados_json.get('identificacao') and isinstance(dados_json.get('identificacao'), dict):
                        data_registro = dados_json['identificacao'].get('dataRegistro')
                    
                    # 2. Tentar em duimp[0].data_registro_mais_recente (estrutura do Kanban)
                    if not data_registro:
                        duimp_data = dados_json.get('duimp')
                        if isinstance(duimp_data, list) and len(duimp_data) > 0:
                            duimp_data = duimp_data[0]
                        if isinstance(duimp_data, dict):
                            # ✅ NOVO: Verificar data_registro_mais_recente primeiro (estrutura mais comum)
                            data_registro = duimp_data.get('data_registro_mais_recente')
                            
                            # Se não encontrou, tentar identificacao.dataRegistro
                            if not data_registro:
                                identificacao = duimp_data.get('identificacao', {})
                                if isinstance(identificacao, dict):
                                    data_registro = identificacao.get('dataRegistro')
                    
                    # 3. Tentar em documentoDespacho (para DUIMPs de produção)
                    if not data_registro:
                        ce_data = dados_json.get('ce')
                        if isinstance(ce_data, list) and len(ce_data) > 0:
                            ce_data = ce_data[0]
                        if isinstance(ce_data, dict):
                            documento_despacho = ce_data.get('documentoDespacho', {})
                            if isinstance(documento_despacho, list) and len(documento_despacho) > 0:
                                for doc in documento_despacho:
                                    if isinstance(doc, dict) and doc.get('tipo') == 'DUIMP':
                                        identificacao = doc.get('identificacao', {})
                                        if isinstance(identificacao, dict):
                                            data_registro = identificacao.get('dataRegistro')
                                            break
                    
                    if data_registro:
                        # Parsear data de registro
                        from datetime import datetime
                        data_limpa = str(data_registro).replace('Z', '').replace('+00:00', '').strip()
                        if '.' in data_limpa:
                            data_limpa = data_limpa.split('.')[0]
                        
                        dt_registro = None
                        if 'T' in data_limpa:
                            try:
                                dt_registro = datetime.fromisoformat(data_limpa)
                            except:
                                pass
                        
                        if not dt_registro:
                            formatos = [
                                "%Y-%m-%dT%H:%M:%S",
                                "%Y-%m-%d %H:%M:%S", 
                                "%Y-%m-%d"
                            ]
                            for fmt in formatos:
                                try:
                                    dt_registro = datetime.strptime(data_limpa, fmt)
                                    break
                                except:
                                    continue
                        
                        if dt_registro and dt_registro.date() == hoje:
                            data_registro_hoje = True
                            
                            # ✅ CORREÇÃO: Buscar situação real da DUIMP do JSON
                            situacao_real = 'REGISTRADA'
                            versao_real = 'N/A'
                            
                            # Tentar buscar de duimp[0] primeiro
                            duimp_data_json = dados_json.get('duimp')
                            if isinstance(duimp_data_json, list) and len(duimp_data_json) > 0:
                                duimp_data_json = duimp_data_json[0]
                            if isinstance(duimp_data_json, dict):
                                situacao_real = (
                                    duimp_data_json.get('situacao_duimp') or
                                    duimp_data_json.get('ultima_situacao') or
                                    duimp_data_json.get('situacao_duimp_agr') or
                                    'REGISTRADA'
                                )
                                versao_real = duimp_data_json.get('versao', 'N/A')
                            
                            # Adicionar como DUIMP registrada hoje
                            ja_na_lista = any(
                                d.get('numero') == duimp_num 
                                for d in movimentacoes['duimps_criadas']
                            )
                            if not ja_na_lista:
                                movimentacoes['duimps_criadas'].append({
                                    'numero': duimp_num,
                                    'versao': versao_real,
                                    'status': situacao_real,
                                    'ambiente': 'producao',
                                    'processo_referencia': proc_ref,
                                    'criado_em': row['atualizado_em'],
                                    'data_registro': data_registro,
                                    'tipo': 'DUIMP'
                                })
                except Exception as e:
                    logging.debug(f'Erro ao extrair dataRegistro do Kanban para {proc_ref}: {e}')
        
        # 6. Mudanças de status DUIMP no Kanban hoje (situacao_entrega indica DUIMP registrada)
        # ✅ CORREÇÃO: Buscar TODAS as DUIMPs atualizadas hoje, não apenas com situação específica
        query_duimp_kanban_hoje = '''
            SELECT DISTINCT
                pk.processo_referencia,
                pk.modal,
                pk.numero_duimp,
                pk.situacao_entrega,
                pk.situacao_di,
                pk.atualizado_em,
                pk.dados_completos_json
            FROM processos_kanban pk
            WHERE DATE(pk.atualizado_em) = DATE('now')
            AND pk.numero_duimp IS NOT NULL
            AND pk.numero_duimp != ''
        '''
        params_duimp_kanban = []
        if categoria:
            query_duimp_kanban_hoje += ' AND pk.processo_referencia LIKE ?'
            params_duimp_kanban.append(f'{categoria.upper()}.%')
        if modal:
            query_duimp_kanban_hoje += ' AND pk.modal = ?'
            params_duimp_kanban.append(modal)
        query_duimp_kanban_hoje += ' ORDER BY pk.processo_referencia ASC'
        
        cursor.execute(query_duimp_kanban_hoje, params_duimp_kanban)
        duimps_kanban_numeros = set()
        for row in cursor.fetchall():
            duimp_num = row['numero_duimp']
            proc_ref = row['processo_referencia']
            situacao_entrega = row['situacao_entrega'] or ''
            situacao_di = row['situacao_di'] or ''
            
            # Evitar duplicatas
            if duimp_num in duimps_kanban_numeros:
                continue
            duimps_kanban_numeros.add(duimp_num)
            
            # ✅ CORREÇÃO: Verificar se indica DUIMP registrada (situacao_entrega ou situacao_di)
            indica_registrada = (
                'REGISTRADA' in situacao_entrega.upper() or
                'AGUARDANDO CANAL' in situacao_entrega.upper() or
                'AGUARDANDO_CANAL' in situacao_entrega.upper() or
                'REGISTRADA' in situacao_di.upper() or
                'AGUARDANDO' in situacao_di.upper()
            )
            
            # ✅ NOVO: Se tem DUIMP mas situação está vazia, verificar no JSON
            if not indica_registrada and row['dados_completos_json']:
                try:
                    dados_json = json.loads(row['dados_completos_json'])
                    
                    # 1. Buscar situação da DUIMP em duimp[0] (estrutura do Kanban)
                    duimp_data = dados_json.get('duimp')
                    if isinstance(duimp_data, list) and len(duimp_data) > 0:
                        duimp_data = duimp_data[0]
                    if isinstance(duimp_data, dict):
                        # Verificar várias possíveis chaves de situação
                        situacao_duimp_json = (
                            duimp_data.get('situacao_duimp') or
                            duimp_data.get('ultima_situacao') or
                            duimp_data.get('situacao_duimp_agr') or
                            duimp_data.get('situacao_analise_retificacao') or
                            ''
                        )
                        if situacao_duimp_json and ('REGISTRADA' in situacao_duimp_json.upper() or 'AGUARDANDO' in situacao_duimp_json.upper()):
                            indica_registrada = True
                            situacao_entrega = situacao_duimp_json
                    
                    # 2. Se ainda não encontrou, buscar em documentoDespacho
                    if not indica_registrada:
                        ce_data = dados_json.get('ce')
                        if isinstance(ce_data, list) and len(ce_data) > 0:
                            ce_data = ce_data[0]
                        if isinstance(ce_data, dict):
                            documento_despacho = ce_data.get('documentoDespacho', [])
                            if isinstance(documento_despacho, list):
                                for doc in documento_despacho:
                                    if isinstance(doc, dict) and doc.get('tipo') == 'DUIMP':
                                        situacao_doc = doc.get('situacao', '')
                                        if situacao_doc and ('REGISTRADA' in situacao_doc.upper() or 'AGUARDANDO' in situacao_doc.upper()):
                                            indica_registrada = True
                                            situacao_entrega = situacao_doc
                                            break
                except Exception as e:
                    logging.debug(f'Erro ao buscar situação DUIMP no JSON para {proc_ref}: {e}')
            
            # ✅ NOVO: Se processo foi atualizado hoje e tem DUIMP, verificar se data_registro_mais_recente é hoje
            if not indica_registrada and row['dados_completos_json']:
                try:
                    dados_json = json.loads(row['dados_completos_json'])
                    duimp_data = dados_json.get('duimp')
                    if isinstance(duimp_data, list) and len(duimp_data) > 0:
                        duimp_data = duimp_data[0]
                    if isinstance(duimp_data, dict):
                        data_registro_mais_recente = duimp_data.get('data_registro_mais_recente')
                        if data_registro_mais_recente:
                            # Parsear data
                            from datetime import datetime
                            data_limpa = str(data_registro_mais_recente).replace('Z', '').replace('+00:00', '').strip()
                            if '.' in data_limpa:
                                data_limpa = data_limpa.split('.')[0]
                            
                            dt_registro = None
                            if 'T' in data_limpa:
                                try:
                                    dt_registro = datetime.fromisoformat(data_limpa)
                                except:
                                    pass
                            
                            if not dt_registro:
                                formatos = [
                                    "%Y-%m-%dT%H:%M:%S",
                                    "%Y-%m-%d %H:%M:%S", 
                                    "%Y-%m-%d"
                                ]
                                for fmt in formatos:
                                    try:
                                        dt_registro = datetime.strptime(data_limpa, fmt)
                                        break
                                    except:
                                        continue
                            
                            if dt_registro and dt_registro.date() == hoje:
                                # DUIMP foi registrada hoje!
                                indica_registrada = True
                                situacao_entrega = duimp_data.get('situacao_duimp') or duimp_data.get('ultima_situacao') or 'REGISTRADA'
                                
                                # ✅ NOVO: Também adicionar à lista de DUIMPs registradas hoje
                                ja_na_lista_duimp = any(
                                    d.get('numero') == duimp_num 
                                    for d in movimentacoes['duimps_criadas']
                                )
                                if not ja_na_lista_duimp:
                                    movimentacoes['duimps_criadas'].append({
                                        'numero': duimp_num,
                                        'versao': duimp_data.get('versao', 'N/A'),
                                        'status': situacao_entrega,
                                        'ambiente': 'producao',
                                        'processo_referencia': proc_ref,
                                        'criado_em': row['atualizado_em'],
                                        'data_registro': data_registro_mais_recente,
                                        'tipo': 'DUIMP'
                                    })
                except Exception as e:
                    logging.debug(f'Erro ao verificar data_registro_mais_recente para {proc_ref}: {e}')
            
            # Se indica que foi registrada hoje, adicionar como mudança de status E como DUIMP registrada
            if indica_registrada:
                # Buscar status completo da DUIMP
                cursor.execute('''
                    SELECT status, ambiente, versao
                    FROM duimps
                    WHERE numero = ? AND (processo_referencia = ? OR processo_referencia IS NULL)
                    ORDER BY criado_em DESC
                    LIMIT 1
                ''', (duimp_num, proc_ref))
                duimp_row = cursor.fetchone()
                
                status_final = duimp_row['status'] if duimp_row else (situacao_entrega or situacao_di or 'REGISTRADA')
                versao_final = duimp_row['versao'] if duimp_row else 'N/A'
                
                # ✅ NOVO: Adicionar à lista de DUIMPs registradas hoje (se não já estiver)
                ja_na_lista_duimp = any(
                    d.get('numero') == duimp_num 
                    for d in movimentacoes['duimps_criadas']
                )
                if not ja_na_lista_duimp:
                    # Buscar dataRegistro do JSON se disponível
                    data_registro_duimp = None
                    if row['dados_completos_json']:
                        try:
                            dados_json_duimp = json.loads(row['dados_completos_json'])
                            duimp_data_json = dados_json_duimp.get('duimp')
                            if isinstance(duimp_data_json, list) and len(duimp_data_json) > 0:
                                duimp_data_json = duimp_data_json[0]
                            if isinstance(duimp_data_json, dict):
                                data_registro_duimp = (
                                    duimp_data_json.get('data_registro_mais_recente') or
                                    duimp_data_json.get('identificacao', {}).get('dataRegistro')
                                )
                        except:
                            pass
                    
                    movimentacoes['duimps_criadas'].append({
                        'numero': duimp_num,
                        'versao': versao_final,
                        'status': status_final,
                        'ambiente': duimp_row['ambiente'] if duimp_row else 'producao',
                        'processo_referencia': proc_ref,
                        'criado_em': row['atualizado_em'],
                        'data_registro': data_registro_duimp,
                        'tipo': 'DUIMP'
                    })
                
                # Verificar se já está na lista de mudanças de status
                ja_na_lista = any(
                    m.get('numero_duimp') == duimp_num 
                    for m in movimentacoes['mudancas_status_duimp']
                )
                
                if not ja_na_lista:
                    # ✅ Enriquecer com data real do evento (ex.: desembaraço) quando disponível
                    data_desembaraco = None
                    try:
                        cursor.execute(
                            "SELECT data_desembaraco FROM processos_kanban WHERE processo_referencia = ? LIMIT 1",
                            (proc_ref,),
                        )
                        row_dt = cursor.fetchone()
                        if row_dt and row_dt['data_desembaraco']:
                            data_desembaraco = row_dt['data_desembaraco']
                    except Exception:
                        data_desembaraco = None

                    movimentacoes['mudancas_status_duimp'].append({
                        'processo_referencia': proc_ref,
                        'numero_duimp': duimp_num,
                        'status': status_final,
                        'ambiente': duimp_row['ambiente'] if duimp_row else 'producao',
                        'atualizado_em': row['atualizado_em'],
                        'data_desembaraco': data_desembaraco,
                    })
        
        # 7. Mudanças de status HOJE (buscar de notificações criadas hoje)
        query_notificacoes_hoje = '''
            SELECT DISTINCT
                n.processo_referencia,
                n.tipo_notificacao,
                n.titulo,
                n.mensagem,
                n.criado_em
            FROM notificacoes_processos n
            WHERE DATE(n.criado_em) = DATE('now')
            AND (
                n.tipo_notificacao LIKE '%status%' 
                OR n.tipo_notificacao LIKE '%chegada%'
                OR n.tipo_notificacao LIKE '%armazenamento%'
            )
        '''
        params_notificacoes = []
        if categoria:
            query_notificacoes_hoje += ' AND n.processo_referencia LIKE ?'
            params_notificacoes.append(f'{categoria.upper()}.%')
        query_notificacoes_hoje += ' ORDER BY n.criado_em DESC'
        
        cursor.execute(query_notificacoes_hoje, params_notificacoes)
        processos_status_alterado = set()
        for row in cursor.fetchall():
            proc_ref = row['processo_referencia']
            tipo_notif = row['tipo_notificacao'] or ''
            
            # Evitar duplicatas
            if proc_ref in processos_status_alterado:
                continue
            processos_status_alterado.add(proc_ref)
            
            # Buscar dados do processo para determinar tipo de mudança
            cursor.execute('''
                SELECT modal, numero_ce, situacao_ce, numero_di, situacao_di, numero_duimp
                FROM processos_kanban
                WHERE processo_referencia = ?
                LIMIT 1
            ''', (proc_ref,))
            proc_row = cursor.fetchone()
            
            if 'status_ce' in tipo_notif.lower() or 'chegada' in tipo_notif.lower() or 'armazenamento' in tipo_notif.lower():
                if proc_row and proc_row['situacao_ce']:
                    # Verificar se já está na lista
                    ja_na_lista = any(
                        m.get('processo_referencia') == proc_ref and m.get('numero_ce') == proc_row['numero_ce']
                        for m in movimentacoes['mudancas_status_ce']
                    )
                    if not ja_na_lista:
                        movimentacoes['mudancas_status_ce'].append({
                            'processo_referencia': proc_ref,
                            'modal': proc_row['modal'],
                            'numero_ce': proc_row['numero_ce'],
                            'situacao_ce': proc_row['situacao_ce'],
                            'atualizado_em': row['criado_em']
                        })
            elif 'status_di' in tipo_notif.lower():
                if proc_row and proc_row['situacao_di']:
                    # Verificar se já está na lista
                    ja_na_lista = any(
                        m.get('processo_referencia') == proc_ref and m.get('numero_di') == proc_row['numero_di']
                        for m in movimentacoes['mudancas_status_di']
                    )
                    if not ja_na_lista:
                        # ✅ Enriquecer com data real do evento (ex.: desembaraço) para bater com o dashboard
                        data_desembaraco = None
                        try:
                            cursor.execute(
                                "SELECT data_desembaraco FROM processos_kanban WHERE processo_referencia = ? LIMIT 1",
                                (proc_ref,),
                            )
                            row_dt = cursor.fetchone()
                            if row_dt and row_dt['data_desembaraco']:
                                data_desembaraco = row_dt['data_desembaraco']
                        except Exception:
                            data_desembaraco = None

                        movimentacoes['mudancas_status_di'].append({
                            'processo_referencia': proc_ref,
                            'modal': proc_row['modal'],
                            'numero_di': proc_row['numero_di'],
                            'situacao_di': proc_row['situacao_di'],
                            'atualizado_em': row['criado_em'],
                            'data_desembaraco': data_desembaraco,
                        })
            elif 'status_duimp' in tipo_notif.lower():
                if proc_row and proc_row['numero_duimp']:
                    # Verificar se já está na lista
                    ja_na_lista = any(
                        m.get('numero_duimp') == proc_row['numero_duimp']
                        for m in movimentacoes['mudancas_status_duimp']
                    )
                    if not ja_na_lista:
                        # Buscar status da DUIMP
                        cursor.execute('''
                            SELECT status, ambiente
                            FROM duimps
                            WHERE numero = ? AND (processo_referencia = ? OR processo_referencia IS NULL)
                            ORDER BY criado_em DESC
                            LIMIT 1
                        ''', (proc_row['numero_duimp'], proc_ref))
                        duimp_row = cursor.fetchone()
                        if duimp_row:
                            # ✅ Enriquecer com data real do evento (ex.: desembaraço) quando disponível
                            data_desembaraco = None
                            try:
                                cursor.execute(
                                    "SELECT data_desembaraco FROM processos_kanban WHERE processo_referencia = ? LIMIT 1",
                                    (proc_ref,),
                                )
                                row_dt = cursor.fetchone()
                                if row_dt and row_dt['data_desembaraco']:
                                    data_desembaraco = row_dt['data_desembaraco']
                            except Exception:
                                data_desembaraco = None

                            movimentacoes['mudancas_status_duimp'].append({
                                'processo_referencia': proc_ref,
                                'numero_duimp': proc_row['numero_duimp'],
                                'status': duimp_row['status'],
                                'ambiente': duimp_row['ambiente'],
                                'atualizado_em': row['criado_em'],
                                'data_desembaraco': data_desembaraco,
                            })
        
        # Remover duplicatas de processos_chegaram (pode ter chegado e armazenado no mesmo dia)
        processos_chegaram_unicos = {}
        for proc in movimentacoes['processos_chegaram']:
            proc_ref = proc['processo_referencia']
            if proc_ref not in processos_chegaram_unicos:
                processos_chegaram_unicos[proc_ref] = proc
        movimentacoes['processos_chegaram'] = list(processos_chegaram_unicos.values())
        
        # ✅ NOVO: Adicionar processos com DUIMP desembaraçada que tiveram mudança de status hoje
        # Se um processo está em "mudancas_status_duimp" com status contendo "DESEMBARACADA", incluir em "processos_desembaracados"
        processos_desembaracados_refs = {p.get('processo_referencia') for p in movimentacoes['processos_desembaracados']}
        
        for mudanca_duimp in movimentacoes.get('mudancas_status_duimp', []):
            proc_ref = mudanca_duimp.get('processo_referencia')
            status_duimp = mudanca_duimp.get('status', '')
            
            # ✅ Se status contém "DESEMBARACADA" (mesmo que tenha pendências), incluir em desembaraçados
            if proc_ref and status_duimp and ('DESEMBARACADA' in status_duimp.upper() or 'DESEMBARACADO' in status_duimp.upper()):
                if proc_ref not in processos_desembaracados_refs:
                    # Buscar dados do processo do Kanban
                    cursor.execute('''
                        SELECT modal, numero_duimp
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                        LIMIT 1
                    ''', (proc_ref,))
                    kanban_row = cursor.fetchone()
                    
                    movimentacoes['processos_desembaracados'].append({
                        'processo_referencia': proc_ref,
                        'modal': kanban_row['modal'] if kanban_row else None,
                        'numero_di': None,
                        'numero_duimp': mudanca_duimp.get('numero_duimp') or (kanban_row['numero_duimp'] if kanban_row else None),
                        'situacao_di': None,
                        'situacao_entrega': None,
                        'data_desembaraco': mudanca_duimp.get('atualizado_em'),
                        'tipo': 'duimp_desembaracada',
                        'status_duimp': status_duimp  # ✅ NOVO: Incluir status para exibição
                    })
                    processos_desembaracados_refs.add(proc_ref)
        
        # ✅ REMOVER DUPLICATAS: Manter apenas a DI/DUIMP mais recente por número
        # Agrupar por número e manter a que tem a data mais recente
        duimps_criadas_unicas = {}
        for doc in movimentacoes['duimps_criadas']:
            numero = doc.get('numero')
            if not numero:
                continue
            
            # Se já existe, comparar datas e manter a mais recente
            if numero in duimps_criadas_unicas:
                doc_existente = duimps_criadas_unicas[numero]
                data_existente = doc_existente.get('criado_em', '')
                data_nova = doc.get('criado_em', '')
                
                # Se a nova tem data mais recente, substituir
                if data_nova and data_nova > data_existente:
                    duimps_criadas_unicas[numero] = doc
            else:
                duimps_criadas_unicas[numero] = doc
        
        # Substituir lista por versão sem duplicatas
        movimentacoes['duimps_criadas'] = list(duimps_criadas_unicas.values())
        
        # ✅ CORREÇÃO FINAL: Atualizar status de TODAS as DIs na lista para garantir status atualizado
        # Isso é necessário porque a remoção de duplicatas pode ter mantido uma versão com status antigo
        try:
            from utils.sql_server_adapter import get_sql_adapter
            sql_adapter_final = get_sql_adapter()
            
            for doc in movimentacoes['duimps_criadas']:
                if doc.get('tipo') == 'DI':
                    numero_di = doc.get('numero')
                    if not numero_di:
                        continue
                    
                    # Buscar status atual da DI
                    # ✅ CORREÇÃO: Usar query mais simples que pega diretamente o status atual
                    # O status atual está em Di_Dados_Gerais.situacaoDi, que é único por DI
                    try:
                        query_status_final = f'''
                            SELECT TOP 1
                                ddg.situacaoDi,
                                diDesp.canalSelecaoParametrizada,
                                diDesp.dataHoraDesembaraco
                            FROM Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                                ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                            INNER JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                                ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                            WHERE ddg.numeroDi = '{numero_di}'
                            ORDER BY 
                                CASE WHEN diDesp.dataHoraDesembaraco IS NOT NULL THEN 0 ELSE 1 END,
                                diDesp.dataHoraDesembaraco DESC,
                                diDesp.dataHoraRegistro DESC
                        '''
                        result_status_final = sql_adapter_final.execute_query(query_status_final, 'Serpro', [], notificar_erro=False)
                        if result_status_final.get('success') and result_status_final.get('data'):
                            rows_status_final = result_status_final['data']
                            if rows_status_final and len(rows_status_final) > 0:
                                row_status_final = rows_status_final[0]
                                if isinstance(row_status_final, dict):
                                    status_atual = row_status_final.get('situacaoDi') or row_status_final.get('situacao_di')
                                    canal_atual = row_status_final.get('canalSelecaoParametrizada') or row_status_final.get('canal_selecao_parametrizada')
                                else:
                                    status_atual = row_status_final[0] if len(row_status_final) > 0 else None
                                    canal_atual = row_status_final[1] if len(row_status_final) > 1 else None
                                
                                # Atualizar status e canal se encontrou valores
                                if status_atual:
                                    status_anterior = doc.get('status', 'N/A')
                                    doc['status'] = status_atual
                                    if status_anterior != status_atual:
                                        logging.info(f'🔄 [FECHAMENTO DIA] Status da DI {numero_di} atualizado: {status_anterior} → {status_atual}')
                                    else:
                                        logging.debug(f'✅ [FECHAMENTO DIA] Status da DI {numero_di} já estava correto: {status_atual}')
                                if canal_atual:
                                    doc['canal'] = canal_atual
                        else:
                            error_msg = result_status_final.get('error', 'Erro desconhecido')
                            logging.warning(f'⚠️ [FECHAMENTO DIA] Erro ao buscar status final da DI {numero_di}: {error_msg}')
                    except Exception as e:
                        logging.warning(f'⚠️ [FECHAMENTO DIA] Erro ao atualizar status final da DI {numero_di}: {e}', exc_info=True)
        except Exception as e:
            logging.warning(f'⚠️ [FECHAMENTO DIA] Erro ao atualizar status final das DIs: {e}')
        
        # Calcular total de movimentações
        # ✅ Inclui: chegadas, desembaraços, DIs registradas, DUIMPs criadas/registradas,
        # mudanças de status (CE/DI/DUIMP) e pendências resolvidas.
        movimentacoes['total_movimentacoes'] = (
            len(movimentacoes['processos_chegaram']) +
            len(movimentacoes['processos_desembaracados']) +
            len(movimentacoes['duimps_criadas']) +
            len(movimentacoes.get('dis_registradas', [])) +  # ✅ CORRIGIDO: incluir DIs separadamente
            len(movimentacoes['mudancas_status_ce']) +
            len(movimentacoes['mudancas_status_di']) +
            len(movimentacoes['mudancas_status_duimp']) +
            len(movimentacoes.get('pendencias_resolvidas', []))
        )
        
        # ✅ LOG FINAL: Resumo de DIs/DUIMPs encontradas (CORRIGIDO: usar listas corretas)
        dis_encontradas = movimentacoes.get('dis_registradas', [])
        duimps_encontradas = [d for d in movimentacoes['duimps_criadas'] if d.get('tipo') == 'DUIMP']
        logging.info(f'📊 [FECHAMENTO DIA] Resumo final: {len(dis_encontradas)} DI(s) e {len(duimps_encontradas)} DUIMP(s) registradas hoje (após remoção de duplicatas)')
        
        conn.close()
        return movimentacoes
    except Exception as e:
        logging.error(f'Erro ao obter movimentações hoje: {e}', exc_info=True)
        return {
            'data': date.today().isoformat(),
            'processos_chegaram': [],
            'processos_desembaracados': [],
            'duimps_criadas': [],
            'dis_registradas': [],  # ✅ CORRIGIDO: Lista separada para DIs registradas hoje
            'mudancas_status_ce': [],
            'mudancas_status_di': [],
            'mudancas_status_duimp': [],
            'pendencias_resolvidas': [],
            'total_movimentacoes': 0,
            'erro': str(e)
        }
