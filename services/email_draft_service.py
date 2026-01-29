"""
Serviço para gerenciar drafts de email com sistema de versões.

Este serviço permite criar, revisar e gerenciar drafts de email de forma versionada,
resolvendo o problema de emails enviando versão antiga após melhoria.
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from db_manager import get_db_connection

logger = logging.getLogger(__name__)


@dataclass
class EmailDraft:
    """Representa um draft de email versionado."""
    id: int
    draft_id: str
    session_id: str
    destinatarios: List[str]
    assunto: str
    conteudo: str
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    revision: int = 1
    status: str = 'draft'  # 'draft' | 'ready_to_send' | 'sent'
    funcao_email: str = 'enviar_email_personalizado'
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


class EmailDraftService:
    """Serviço para gerenciar drafts de email."""
    
    def __init__(self):
        """Inicializa o serviço."""
        pass
    
    def _gerar_draft_id(self) -> str:
        """Gera um ID único para o draft."""
        return f"email_{int(datetime.now().timestamp() * 1000)}"
    
    def criar_draft(
        self,
        destinatarios: List[str],
        assunto: str,
        conteudo: str,
        session_id: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        funcao_email: str = 'enviar_email_personalizado'
    ) -> Optional[str]:
        """
        Cria um novo draft de email.
        
        Args:
            destinatarios: Lista de emails dos destinatários
            assunto: Assunto do email
            conteudo: Conteúdo do email
            session_id: ID da sessão
            cc: Lista de emails em cópia (opcional)
            bcc: Lista de emails em cópia oculta (opcional)
            funcao_email: Tipo de função de email (padrão: 'enviar_email_personalizado')
        
        Returns:
            draft_id se sucesso, None se erro
        """
        try:
            draft_id = self._gerar_draft_id()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO email_drafts (
                    draft_id, session_id, destinatarios, assunto, conteudo,
                    cc, bcc, revision, status, funcao_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'draft', ?)
            ''', (
                draft_id,
                session_id,
                json.dumps(destinatarios),
                assunto,
                conteudo,
                json.dumps(cc) if cc else None,
                json.dumps(bcc) if bcc else None,
                funcao_email
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f'✅ Draft criado: {draft_id} (revision 1)')
            return draft_id
            
        except Exception as e:
            logger.error(f'❌ Erro ao criar draft: {e}', exc_info=True)
            return None
    
    def revisar_draft(
        self,
        draft_id: str,
        assunto: Optional[str] = None,
        conteudo: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Optional[int]:
        """
        Cria uma nova revisão do draft.
        
        Args:
            draft_id: ID do draft
            assunto: Novo assunto (opcional, mantém anterior se None)
            conteudo: Novo conteúdo (opcional, mantém anterior se None)
            cc: Nova lista de CC (opcional)
            bcc: Nova lista de BCC (opcional)
        
        Returns:
            Número da nova revisão se sucesso, None se erro
        """
        try:
            # Obter draft atual
            draft_atual = self.obter_draft(draft_id)
            if not draft_atual:
                logger.error(f'❌ Draft não encontrado: {draft_id}')
                return None
            
            # Preparar nova revisão
            nova_revision = draft_atual.revision + 1
            novo_assunto = assunto if assunto is not None else draft_atual.assunto
            novo_conteudo = conteudo if conteudo is not None else draft_atual.conteudo
            novo_cc = cc if cc is not None else draft_atual.cc
            novo_bcc = bcc if bcc is not None else draft_atual.bcc
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Atualizar draft com nova revisão
            cursor.execute('''
                UPDATE email_drafts
                SET assunto = ?,
                    conteudo = ?,
                    cc = ?,
                    bcc = ?,
                    revision = ?,
                    status = 'draft',
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE draft_id = ?
            ''', (
                novo_assunto,
                novo_conteudo,
                json.dumps(novo_cc) if novo_cc else None,
                json.dumps(novo_bcc) if novo_bcc else None,
                nova_revision,
                draft_id
            ))
            
            if cursor.rowcount == 0:
                conn.close()
                logger.error(f'❌ Draft não encontrado para atualizar: {draft_id}')
                return None
            
            conn.commit()
            conn.close()
            
            logger.info(f'✅ Draft revisado: {draft_id} (revision {nova_revision})')
            return nova_revision
            
        except Exception as e:
            logger.error(f'❌ Erro ao revisar draft: {e}', exc_info=True)
            return None
    
    def obter_draft(self, draft_id: str) -> Optional[EmailDraft]:
        """
        Obtém o draft mais recente (última revisão).
        
        Args:
            draft_id: ID do draft
        
        Returns:
            EmailDraft se encontrado, None se não encontrado
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, draft_id, session_id, destinatarios, assunto, conteudo,
                       cc, bcc, revision, status, funcao_email, criado_em, atualizado_em
                FROM email_drafts
                WHERE draft_id = ?
                ORDER BY revision DESC
                LIMIT 1
            ''', (draft_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Parsear JSONs
            destinatarios = json.loads(row[3]) if row[3] else []
            cc = json.loads(row[6]) if row[6] else None
            bcc = json.loads(row[7]) if row[7] else None
            
            # Parsear timestamps
            criado_em = None
            atualizado_em = None
            if row[11]:
                try:
                    criado_em = datetime.fromisoformat(row[11].replace('Z', '+00:00'))
                except:
                    pass
            if row[12]:
                try:
                    atualizado_em = datetime.fromisoformat(row[12].replace('Z', '+00:00'))
                except:
                    pass
            
            return EmailDraft(
                id=row[0],
                draft_id=row[1],
                session_id=row[2],
                destinatarios=destinatarios,
                assunto=row[4],
                conteudo=row[5],
                cc=cc,
                bcc=bcc,
                revision=row[8],
                status=row[9],
                funcao_email=row[10],
                criado_em=criado_em,
                atualizado_em=atualizado_em
            )
            
        except Exception as e:
            logger.error(f'❌ Erro ao obter draft: {e}', exc_info=True)
            return None
    
    def listar_drafts(
        self,
        session_id: str,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[EmailDraft]:
        """
        Lista drafts de uma sessão.
        
        Args:
            session_id: ID da sessão
            status: Filtrar por status (opcional)
            limit: Limite de resultados
        
        Returns:
            Lista de EmailDraft
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if status:
                cursor.execute('''
                    SELECT id, draft_id, session_id, destinatarios, assunto, conteudo,
                           cc, bcc, revision, status, funcao_email, criado_em, atualizado_em
                    FROM email_drafts
                    WHERE session_id = ? AND status = ?
                    ORDER BY criado_em DESC
                    LIMIT ?
                ''', (session_id, status, limit))
            else:
                cursor.execute('''
                    SELECT id, draft_id, session_id, destinatarios, assunto, conteudo,
                           cc, bcc, revision, status, funcao_email, criado_em, atualizado_em
                    FROM email_drafts
                    WHERE session_id = ?
                    ORDER BY criado_em DESC
                    LIMIT ?
                ''', (session_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            drafts = []
            for row in rows:
                try:
                    destinatarios = json.loads(row[3]) if row[3] else []
                    cc = json.loads(row[6]) if row[6] else None
                    bcc = json.loads(row[7]) if row[7] else None
                    
                    criado_em = None
                    atualizado_em = None
                    if row[11]:
                        try:
                            criado_em = datetime.fromisoformat(row[11].replace('Z', '+00:00'))
                        except:
                            pass
                    if row[12]:
                        try:
                            atualizado_em = datetime.fromisoformat(row[12].replace('Z', '+00:00'))
                        except:
                            pass
                    
                    drafts.append(EmailDraft(
                        id=row[0],
                        draft_id=row[1],
                        session_id=row[2],
                        destinatarios=destinatarios,
                        assunto=row[4],
                        conteudo=row[5],
                        cc=cc,
                        bcc=bcc,
                        revision=row[8],
                        status=row[9],
                        funcao_email=row[10],
                        criado_em=criado_em,
                        atualizado_em=atualizado_em
                    ))
                except Exception as e:
                    logger.warning(f'⚠️ Erro ao parsear draft: {e}')
                    continue
            
            return drafts
            
        except Exception as e:
            logger.error(f'❌ Erro ao listar drafts: {e}', exc_info=True)
            return []
    
    def marcar_como_enviado(self, draft_id: str) -> bool:
        """
        Marca o draft como enviado.
        
        Args:
            draft_id: ID do draft
        
        Returns:
            True se sucesso, False se erro
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE email_drafts
                SET status = 'sent',
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE draft_id = ?
            ''', (draft_id,))
            
            if cursor.rowcount == 0:
                conn.close()
                logger.warning(f'⚠️ Draft não encontrado para marcar como enviado: {draft_id}')
                return False
            
            conn.commit()
            conn.close()
            
            logger.info(f'✅ Draft marcado como enviado: {draft_id}')
            return True
            
        except Exception as e:
            logger.error(f'❌ Erro ao marcar draft como enviado: {e}', exc_info=True)
            return False


# Instância global do serviço
_email_draft_service_instance = None


def get_email_draft_service() -> EmailDraftService:
    """Retorna instância global do EmailDraftService."""
    global _email_draft_service_instance
    if _email_draft_service_instance is None:
        _email_draft_service_instance = EmailDraftService()
    return _email_draft_service_instance
