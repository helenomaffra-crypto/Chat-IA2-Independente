"""
PendingIntentService - Gerencia ações pendentes de confirmação de forma persistente.

✅ NOVO (14/01/2026): Sistema de pending intents para substituir estado em memória.

Este serviço permite que ações pendentes (email, DUIMP, etc.) sejam persistidas no banco,
garantindo que o estado não se perca em refresh ou interrupções.

Regra de ouro: Estado persistido no banco é fonte da verdade, não memória.
"""

import json
import logging
import hashlib
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)

# TTL padrão: 2 horas
DEFAULT_TTL_HOURS = 2


class PendingIntentService:
    """
    Serviço para gerenciar pending intents (ações pendentes de confirmação).
    
    Funcionalidades:
    - Criar pending intent
    - Buscar pending intent por session_id e status
    - Marcar como executado/cancelado/expirado
    - Limpar intents expiradas automaticamente
    - Detecção de duplicatas via payload_hash
    """
    
    @staticmethod
    def criar_pending_intent(
        session_id: str,
        action_type: str,
        tool_name: str,
        args_normalizados: Dict[str, Any],
        preview_text: str,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        observacoes: Optional[str] = None,
        args_hash: Optional[Dict[str, Any]] = None  # ✅ NOVO: Args para hash (campos essenciais)
    ) -> Optional[str]:
        """
        Cria um novo pending intent.
        
        ✅ NOVO (14/01/2026): Minimiza preview_text (apenas primeiros 200 chars).
        
        Args:
            session_id: ID da sessão
            action_type: Tipo da ação ('send_email', 'create_duimp', etc.)
            tool_name: Nome da tool que será executada
            args_normalizados: Argumentos normalizados (será convertido para JSON)
            preview_text: Texto do preview mostrado ao usuário (será truncado para 200 chars)
            ttl_hours: Tempo de vida em horas (padrão: 2h)
            observacoes: Observações adicionais (opcional)
        
        Returns:
            intent_id (UUID) se criado com sucesso, None caso contrário
        """
        try:
            intent_id = str(uuid.uuid4())
            created_at = datetime.now()
            expires_at = created_at + timedelta(hours=ttl_hours)
            
            # ✅ NOVO (14/01/2026): Minimizar preview_text (apenas primeiros 200 chars)
            # ✅ MELHORIA (14/01/2026): Mascarar dados sensíveis antes de truncar
            preview_text_sanitizado = PendingIntentService._sanitizar_preview_text(preview_text)
            preview_text_minimizado = preview_text_sanitizado[:200] + ('...' if len(preview_text_sanitizado) > 200 else '')
            
            # ✅✅✅ CRÍTICO (14/01/2026): Gerar hash apenas com campos essenciais (não resumo_texto completo)
            # Se args_hash fornecido, usar para hash (campos essenciais)
            # Senão, usar args_normalizados completo (fallback)
            args_para_hash = args_hash if args_hash is not None else args_normalizados
            payload_str = json.dumps(args_para_hash, sort_keys=True, ensure_ascii=False)
            payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # ✅✅✅ CRÍTICO (14/01/2026): Verificar se já existe pending intent com mesmo hash (duplicata)
            cursor.execute('''
                SELECT intent_id FROM pending_intents 
                WHERE session_id = ? 
                AND action_type = ? 
                AND payload_hash = ? 
                AND status = 'pending'
                ORDER BY created_at DESC
                LIMIT 1
            ''', (session_id, action_type, payload_hash))
            
            existing_intent = cursor.fetchone()
            if existing_intent:
                intent_id_existente = existing_intent[0]
                conn.close()
                logger.info(f'✅ Pending intent duplicado detectado - retornando existente: {intent_id_existente} (action: {action_type}, tool: {tool_name})')
                return intent_id_existente
            
            # Se não existe duplicata, criar novo
            intent_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO pending_intents 
                (intent_id, session_id, action_type, tool_name, args_normalizados, 
                 payload_hash, preview_text, status, created_at, expires_at, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            ''', (
                intent_id,
                session_id,
                action_type,
                tool_name,
                json.dumps(args_normalizados, ensure_ascii=False),
                payload_hash,
                preview_text_minimizado,  # ✅ NOVO: Usar preview minimizado
                created_at.isoformat(),
                expires_at.isoformat(),
                observacoes
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f'✅ Pending intent criado: {intent_id} (action: {action_type}, tool: {tool_name})')
            return intent_id
            
        except Exception as e:
            logger.error(f'❌ Erro ao criar pending intent: {e}', exc_info=True)
            return None
    
    @staticmethod
    def buscar_pending_intent(
        session_id: str,
        status: str = 'pending',
        action_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca o último pending intent de uma sessão.
        
        Args:
            session_id: ID da sessão
            status: Status do intent ('pending', 'executed', etc.)
            action_type: Tipo da ação (opcional, para filtrar)
        
        Returns:
            Dict com dados do intent se encontrado, None caso contrário
        """
        try:
            conn = get_db_connection()
            conn.row_factory = lambda cursor, row: {
                col[0]: row[idx] for idx, col in enumerate(cursor.description)
            }
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM pending_intents 
                WHERE session_id = ? AND status = ?
            '''
            params = [session_id, status]
            
            if action_type:
                query += ' AND action_type = ?'
                params.append(action_type)
            
            query += ' ORDER BY created_at DESC LIMIT 1'
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # ✅ NOVO (14/01/2026): Verificar expiração antes de retornar
            expires_at_str = row.get('expires_at')
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() > expires_at:
                        # ✅ NOVO (14/01/2026): Marcar como EXPIRED (não cancelled)
                        try:
                            PendingIntentService.marcar_como_expirado(row['intent_id'])
                            logger.info(f'⚠️ Pending intent {row["intent_id"]} expirado e marcado como expired')
                        except Exception as e:
                            logger.warning(f'⚠️ Erro ao marcar intent como expirado: {e}')
                        return None
                except (ValueError, TypeError) as e:
                    logger.warning(f'⚠️ Erro ao verificar expiração: {e}')
            
            # Parse JSON fields
            if row.get('args_normalizados'):
                try:
                    row['args_normalizados'] = json.loads(row['args_normalizados'])
                except (json.JSONDecodeError, TypeError):
                    row['args_normalizados'] = {}
            
            return row
            
        except Exception as e:
            logger.error(f'❌ Erro ao buscar pending intent: {e}', exc_info=True)
            return None
    
    @staticmethod
    def buscar_pending_intent_por_id(intent_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um pending intent por ID.
        
        Args:
            intent_id: ID do intent
        
        Returns:
            Dict com dados do intent se encontrado, None caso contrário
        """
        try:
            conn = get_db_connection()
            conn.row_factory = lambda cursor, row: {
                col[0]: row[idx] for idx, col in enumerate(cursor.description)
            }
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM pending_intents WHERE intent_id = ?', (intent_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Parse JSON fields
            if row.get('args_normalizados'):
                try:
                    row['args_normalizados'] = json.loads(row['args_normalizados'])
                except (json.JSONDecodeError, TypeError):
                    row['args_normalizados'] = {}
            
            return row
            
        except Exception as e:
            logger.error(f'❌ Erro ao buscar pending intent por ID: {e}', exc_info=True)
            return None
    
    @staticmethod
    def marcar_como_executando(intent_id: str) -> bool:
        """
        ✅✅✅ CRÍTICO (14/01/2026): Marca um pending intent como executando (lock atômico).
        
        Este método implementa um "compare-and-set" atômico: só muda para "executing"
        se ainda estiver "pending". Isso previne envios duplicados em concorrência.
        
        ✅ CORRIGIDO (14/01/2026): Usa transação com context manager para garantir atomicidade.
        
        Args:
            intent_id: ID do intent
        
        Returns:
            True se lock foi obtido (status mudou de 'pending' para 'executing'), False caso contrário
        """
        try:
            conn = get_db_connection()
            
            # ✅✅✅ CRÍTICO: Usar context manager para transação atômica
            # Isso garante commit/rollback automático e thread-safety
            with conn:
                cursor = conn.cursor()
                
                # ✅✅✅ CRÍTICO: Update atômico - só muda se ainda estiver 'pending'
                # Isso garante que apenas uma requisição consegue obter o lock
                # (compare-and-set: só atualiza se status ainda for 'pending')
                # ✅ CORRIGIDO: Usar 'executing' (sem 'a') para alinhar com schema
                # ✅✅✅ CRÍTICO (14/01/2026): Setar executing_at = CURRENT_TIMESTAMP para recovery
                cursor.execute('''
                    UPDATE pending_intents 
                    SET status = 'executing', executing_at = CURRENT_TIMESTAMP
                    WHERE intent_id = ? AND status = 'pending'
                ''', (intent_id,))
                
                affected = cursor.rowcount
            
            conn.close()
            
            if affected > 0:
                logger.info(f'✅✅✅ Lock obtido: Pending intent {intent_id} marcado como executing')
                return True
            else:
                logger.warning(f'⚠️ Lock NÃO obtido: Pending intent {intent_id} não encontrado ou já processado (status não era pending)')
                return False
                
        except Exception as e:
            logger.error(f'❌ Erro ao marcar pending intent como executing: {e}', exc_info=True)
            return False
    
    @staticmethod
    def marcar_como_executado(intent_id: str, observacoes: Optional[str] = None) -> bool:
        """
        Marca um pending intent como executado.
        
        ✅✅✅ CRÍTICO (14/01/2026): Só marca como executado se status for 'executing'.
        Isso garante que o fluxo correto seja: pending → executing → executed
        
        ✅ CORRIGIDO (14/01/2026): Usa transação com context manager para garantir atomicidade.
        
        Args:
            intent_id: ID do intent
            observacoes: Observações adicionais (opcional)
        
        Returns:
            True se marcado com sucesso, False caso contrário
        """
        try:
            conn = get_db_connection()
            
            # ✅✅✅ CRÍTICO: Usar context manager para transação atômica
            with conn:
                cursor = conn.cursor()
                
                # ✅✅✅ CRÍTICO: Só marca como executed se status for 'executing'
                # Isso garante que o lock foi obtido antes
                # ✅ CORRIGIDO: Usar 'executing' (sem 'a') para alinhar com schema
                # ✅ CORRIGIDO (14/01/2026): Usar CURRENT_TIMESTAMP (não isoformat()) para consistência com SQLite
                cursor.execute('''
                    UPDATE pending_intents 
                    SET status = 'executed', executed_at = CURRENT_TIMESTAMP, observacoes = ?
                    WHERE intent_id = ? AND status = 'executing'
                ''', (observacoes, intent_id))
                
                affected = cursor.rowcount
            
            conn.close()
            
            if affected > 0:
                logger.info(f'✅ Pending intent {intent_id} marcado como executed')
                return True
            else:
                logger.warning(f'⚠️ Pending intent {intent_id} não encontrado ou status não era executing (pode ter sido cancelado/expirado)')
                return False
                
        except Exception as e:
            logger.error(f'❌ Erro ao marcar pending intent como executed: {e}', exc_info=True)
            return False
    
    @staticmethod
    def marcar_como_cancelado(intent_id: str, observacoes: Optional[str] = None) -> bool:
        """
        Marca um pending intent como cancelado.
        
        ✅ CORRIGIDO (14/01/2026): Usa transação com context manager para garantir atomicidade.
        
        Args:
            intent_id: ID do intent
            observacoes: Observações adicionais (opcional)
        
        Returns:
            True se marcado com sucesso, False caso contrário
        """
        try:
            conn = get_db_connection()
            
            # ✅✅✅ CRÍTICO: Usar context manager para transação atômica
            with conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE pending_intents 
                    SET status = 'cancelled', observacoes = ?
                    WHERE intent_id = ? AND status = 'pending'
                ''', (observacoes, intent_id))
                
                affected = cursor.rowcount
            
            conn.close()
            
            if affected > 0:
                logger.info(f'✅ Pending intent {intent_id} marcado como cancelled')
                return True
            else:
                logger.warning(f'⚠️ Pending intent {intent_id} não encontrado ou já processado')
                return False
                
        except Exception as e:
            logger.error(f'❌ Erro ao marcar pending intent como cancelled: {e}', exc_info=True)
            return False
    
    @staticmethod
    def marcar_como_expirado(intent_id: str) -> bool:
        """
        ✅ NOVO (14/01/2026): Marca um pending intent como expirado.
        
        ✅ CORRIGIDO (14/01/2026): Também expira intents em 'executing' antigos (timeout).
        
        Args:
            intent_id: ID do intent
        
        Returns:
            True se marcado com sucesso, False caso contrário
        """
        try:
            conn = get_db_connection()
            
            # ✅✅✅ CRÍTICO: Usar context manager para transação atômica
            with conn:
                cursor = conn.cursor()
                
                # ✅ CORRIGIDO: Expirar tanto 'pending' quanto 'executing' (timeout)
                cursor.execute('''
                    UPDATE pending_intents 
                    SET status = 'expired', observacoes = 'Expirado automaticamente'
                    WHERE intent_id = ? AND status IN ('pending', 'executing')
                ''', (intent_id,))
                
                affected = cursor.rowcount
            
            conn.close()
            
            if affected > 0:
                logger.info(f'✅ Pending intent {intent_id} marcado como expired')
                return True
            else:
                logger.warning(f'⚠️ Pending intent {intent_id} não encontrado ou já processado')
                return False
                
        except Exception as e:
            logger.error(f'❌ Erro ao marcar pending intent como expired: {e}', exc_info=True)
            return False
    
    @staticmethod
    def recuperar_intents_travados(timeout_minutos: int = 10) -> int:
        """
        ✅✅✅ CRÍTICO (14/01/2026): Recupera intents travados em 'executing' há mais de X minutos.
        
        Se o processo cair depois de marcar 'executing' e antes de marcar 'executed',
        o intent pode ficar preso. Este método expira esses intents automaticamente.
        
        ✅✅✅ CORRIGIDO (14/01/2026):
        - Usa executing_at (não created_at) para detectar quando virou executing
        - Usa SQLite datetime functions para comparação (evita problema de formato)
        - Corrige interpolação de string no SQL usando concatenação
        
        Args:
            timeout_minutos: Tempo em minutos para considerar intent travado (padrão: 10 min)
        
        Returns:
            Número de intents recuperados
        """
        try:
            conn = get_db_connection()
            
            # ✅✅✅ CRÍTICO: Usar context manager para transação atômica
            with conn:
                cursor = conn.cursor()
                
                # ✅✅✅ CORRIGIDO (14/01/2026):
                # 1. Usar executing_at (não created_at) - timestamp de quando virou executing
                # 2. Usar SQLite datetime('now','-X minutes') para comparação (evita problema de formato)
                #    Nota: SQLite não aceita parâmetros dentro de datetime(), então construímos a string
                # 3. Corrigir interpolação de string usando concatenação SQL (||)
                # Construir intervalo SQLite (ex: '-10 minutes')
                intervalo_sqlite = f'-{timeout_minutos} minutes'
                observacao_texto = f'Executando travado (timeout de {timeout_minutos} minutos)'
                
                cursor.execute('''
                    UPDATE pending_intents
                    SET status = 'expired', 
                        observacoes = ?
                    WHERE status = 'executing'
                    AND executing_at IS NOT NULL
                    AND executing_at < datetime('now', ?)
                ''', (observacao_texto, intervalo_sqlite))
                
                affected = cursor.rowcount
            
            conn.close()
            
            if affected > 0:
                logger.warning(f'⚠️ {affected} intent(s) travado(s) em executing foram recuperados (timeout: {timeout_minutos} min)')
            
            return affected
                
        except Exception as e:
            logger.error(f'❌ Erro ao recuperar intents travados: {e}', exc_info=True)
            return 0
    
    @staticmethod
    def marcar_pendings_antigos_como_superseded(
        session_id: str,
        action_type: str,
        except_id: str
    ) -> int:
        """
        ✅ NOVO (14/01/2026): Marca pending intents antigos como 'superseded'.
        
        Quando um novo pending intent é criado, os anteriores do mesmo tipo
        devem ser marcados como superseded para evitar confusão.
        
        Args:
            session_id: ID da sessão
            action_type: Tipo da ação ('send_email', 'create_duimp', etc.)
            except_id: ID do pending intent que NÃO deve ser marcado como superseded
        
        Returns:
            Número de intents marcadas como superseded
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE pending_intents 
                SET status = 'superseded', observacoes = 'Substituído por novo pending intent'
                WHERE session_id = ? 
                AND action_type = ? 
                AND status = 'pending'
                AND intent_id != ?
            ''', (session_id, action_type, except_id))
            
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            
            if affected > 0:
                logger.info(f'✅ {affected} pending intent(s) antigo(s) marcado(s) como superseded (session: {session_id}, action: {action_type})')
            
            return affected
                
        except Exception as e:
            logger.error(f'❌ Erro ao marcar pendings antigos como superseded: {e}', exc_info=True)
            return 0
    
    @staticmethod
    def limpar_intents_expiradas() -> int:
        """
        Limpa intents expiradas (marca como 'expired').
        
        ✅ NOVO (14/01/2026): Usa método marcar_como_expirado() para cada intent.
        ✅ CORRIGIDO (14/01/2026): Também recupera intents travados em 'executing'.
        
        Returns:
            Número de intents limpas
        """
        try:
            conn = get_db_connection()
            conn.row_factory = lambda cursor, row: {
                col[0]: row[idx] for idx, col in enumerate(cursor.description)
            }
            cursor = conn.cursor()
            
            agora = datetime.now().isoformat()
            
            # Buscar intents expiradas
            cursor.execute('''
                SELECT intent_id FROM pending_intents 
                WHERE status = 'pending' AND expires_at < ?
            ''', (agora,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Marcar cada uma como expirada
            count = 0
            for row in rows:
                intent_id = row['intent_id']
                if PendingIntentService.marcar_como_expirado(intent_id):
                    count += 1
            
            # ✅✅✅ CRÍTICO (14/01/2026): Recuperar intents travados em 'executing'
            count_travados = PendingIntentService.recuperar_intents_travados(timeout_minutos=10)
            count += count_travados
            
            if count > 0:
                logger.info(f'✅ {count} pending intent(s) limpo(s) ({count - count_travados} expirados, {count_travados} travados)')
            
            return count
            
        except Exception as e:
            logger.error(f'❌ Erro ao limpar intents expiradas: {e}', exc_info=True)
            return 0
    
    @staticmethod
    def listar_pending_intents(
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        action_type: Optional[str] = None,
        limite: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Lista pending intents com filtros opcionais.
        
        Args:
            session_id: ID da sessão (opcional)
            status: Status do intent (opcional)
            action_type: Tipo da ação (opcional)
            limite: Limite de resultados (padrão: 10)
        
        Returns:
            Lista de dicts com dados dos intents
        """
        try:
            conn = get_db_connection()
            conn.row_factory = lambda cursor, row: {
                col[0]: row[idx] for idx, col in enumerate(cursor.description)
            }
            cursor = conn.cursor()
            
            query = 'SELECT * FROM pending_intents WHERE 1=1'
            params = []
            
            if session_id:
                query += ' AND session_id = ?'
                params.append(session_id)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if action_type:
                query += ' AND action_type = ?'
                params.append(action_type)
            
            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limite)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Parse JSON fields
            for row in rows:
                if row.get('args_normalizados'):
                    try:
                        row['args_normalizados'] = json.loads(row['args_normalizados'])
                    except (json.JSONDecodeError, TypeError):
                        row['args_normalizados'] = {}
            
            return rows
            
        except Exception as e:
            logger.error(f'❌ Erro ao listar pending intents: {e}', exc_info=True)
            return []
    
    @staticmethod
    def _sanitizar_preview_text(preview_text: str) -> str:
        """
        ✅ NOVO (14/01/2026): Sanitiza preview_text mascarando dados sensíveis.
        
        Mascara:
        - Emails: usuario@exemplo.com → us***@exemplo.com
        - CNPJ: 12.345.678/0001-90 → 12.***.***/****-**
        - CPF: 123.456.789-00 → 123.***.***-**
        - Valores monetários: R$ 1.234,56 → R$ ***,**
        
        Args:
            preview_text: Texto do preview
        
        Returns:
            Texto sanitizado
        """
        import re
        
        texto = preview_text
        
        # Mascarar emails
        texto = re.sub(
            r'([a-zA-Z0-9._%+-]{1,3})([a-zA-Z0-9._%+-]*)(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'\1***\3',
            texto
        )
        
        # Mascarar CNPJ (XX.XXX.XXX/XXXX-XX)
        texto = re.sub(
            r'(\d{2}\.)(\d{3}\.)(\d{3}/)(\d{4}-)(\d{2})',
            r'\1***.***/****-\5',
            texto
        )
        
        # Mascarar CPF (XXX.XXX.XXX-XX)
        texto = re.sub(
            r'(\d{3}\.)(\d{3}\.)(\d{3}-)(\d{2})',
            r'\1***.***-**',
            texto
        )
        
        # Mascarar valores monetários (R$ X.XXX,XX ou USD X.XXX,XX)
        texto = re.sub(
            r'(R\$\s*|USD\s*)(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'\1***,**',
            texto
        )
        
        return texto


# Singleton instance
_pending_intent_service_instance = None


def get_pending_intent_service() -> PendingIntentService:
    """
    Retorna instância singleton do PendingIntentService.
    
    Returns:
        Instância do PendingIntentService
    """
    global _pending_intent_service_instance
    if _pending_intent_service_instance is None:
        _pending_intent_service_instance = PendingIntentService()
    return _pending_intent_service_instance
