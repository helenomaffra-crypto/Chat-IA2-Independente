"""
EmailSendCoordinator - Ponto único de convergência para envio de emails.

Este serviço garante que TODOS os envios de email passem por um único ponto,
sempre usando draft_id como fonte da verdade e verificando idempotência.

Regra de ouro: Todo envio tem que convergir para send_from_draft(draft_id),
e esse ponto sempre carrega a última revisão do banco.
"""

import logging
import re
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


def _markdown_to_html(texto: str) -> str:
    """
    Converte markdown básico para HTML formatado.
    
    Suporta:
    - **texto** → <strong>texto</strong>
    - *texto* → <em>texto</em>
    - Quebras de linha → preservadas como <br> ou <p>
    - Links [texto](url) → <a href="url">texto</a>
    """
    if not texto:
        return texto
    
    html = texto
    
    # ✅ Converter negrito **texto** → <strong>texto</strong> primeiro
    # Usar regex não-greedy para capturar múltiplos negritos na mesma linha
    html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
    
    # ✅ Converter itálico *texto* → <em>texto</em> (apenas asteriscos simples)
    # Precisamos ter cuidado para não converter * que já foram usados em **
    # Converter apenas *texto* que não está dentro de **texto**
    html = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', html)
    
    # ✅ Converter quebras de linha
    # Substituir duplas quebras de linha por </p><p> (parágrafos)
    html = re.sub(r'\n\n+', '</p><p>', html)
    # Substituir quebras simples por <br>
    html = html.replace('\n', '<br>')
    
    # ✅ Envolver em tags <p> se necessário
    if not html.strip().startswith('<p>'):
        html = f'<p>{html}'
    if not html.strip().endswith('</p>'):
        html = f'{html}</p>'
    
    # ✅ Converter links [texto](url) → <a href="url">texto</a>
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # ✅ Criar HTML completo com estilo básico
    html_completo = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        p {{ margin: 0.5em 0; }}
        strong {{ font-weight: bold; color: #2c3e50; }}
        em {{ font-style: italic; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    {html}
</body>
</html>
"""
    
    return html_completo


@dataclass
class PendingAction:
    """
    Representa uma ação pendente de confirmação.
    
    Usado para criar uma state machine simples que não depende do texto do chat.
    """
    kind: str  # "send_email" | "create_duimp" | "send_report"
    id: str  # draft_id, duimp_id, report_id, etc.
    expires_at: Optional[str] = None  # Timestamp de expiração (opcional)
    metadata: Optional[Dict[str, Any]] = None  # Dados adicionais


class EmailSendCoordinator:
    """
    Coordenador centralizado para envio de emails.
    
    Garante:
    - draft_id é sempre fonte da verdade
    - Idempotência (não envia duas vezes)
    - Todos os caminhos de envio convergem aqui
    """
    
    def __init__(
        self,
        email_draft_service: Any = None,
        email_service: Any = None,
    ):
        """
        Inicializa o coordenador.
        
        Args:
            email_draft_service: Serviço de gerenciamento de drafts
            email_service: Serviço de envio de emails
        """
        self.email_draft_service = email_draft_service
        self.email_service = email_service
        
        # Lazy loading se não fornecido
        if not self.email_draft_service:
            try:
                from services.email_draft_service import get_email_draft_service
                self.email_draft_service = get_email_draft_service()
            except Exception as e:
                logger.warning(f'⚠️ Erro ao carregar EmailDraftService: {e}')
        
        if not self.email_service:
            try:
                from services.email_service import get_email_service
                self.email_service = get_email_service()
            except Exception as e:
                logger.warning(f'⚠️ Erro ao carregar EmailService: {e}')
    
    def send_from_draft(
        self,
        draft_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Envia email a partir de um draft_id.
        
        Este é o PONTO ÚNICO de convergência para envio de emails.
        Todos os outros caminhos devem convergir aqui.
        
        Regras:
        1. Sempre carrega a última revisão do banco (fonte da verdade)
        2. Verifica idempotência (não envia se já foi enviado)
        3. Marca como enviado após sucesso
        
        Args:
            draft_id: ID do draft a enviar
            force: Se True, força envio mesmo se já foi enviado (para reenvio)
        
        Returns:
            Dict com resultado do envio:
            - sucesso: bool
            - resposta: str
            - erro: str (se houver)
            - draft_id: str
            - revision: int (revisão enviada)
        """
        if not self.email_draft_service:
            return {
                'sucesso': False,
                'erro': 'EMAIL_DRAFT_SERVICE_NAO_DISPONIVEL',
                'resposta': '❌ Serviço de drafts não disponível'
            }
        
        if not self.email_service:
            return {
                'sucesso': False,
                'erro': 'EMAIL_SERVICE_NAO_DISPONIVEL',
                'resposta': '❌ Serviço de email não disponível'
            }
        
        try:
            # ✅ REGRA 1: Sempre carregar do banco (fonte da verdade)
            draft = self.email_draft_service.obter_draft(draft_id)
            
            if not draft:
                return {
                    'sucesso': False,
                    'erro': 'DRAFT_NAO_ENCONTRADO',
                    'resposta': f'❌ Draft {draft_id} não encontrado no banco de dados'
                }
            
            # ✅ REGRA 2: Verificar idempotência (não enviar duas vezes)
            if draft.status == 'sent' and not force:
                logger.info(f'✅ Draft {draft_id} já foi enviado (revision {draft.revision}). Retornando mensagem de idempotência.')
                return {
                    'sucesso': True,
                    'resposta': f'✅ Este email já foi enviado anteriormente (revisão {draft.revision}).',
                    'draft_id': draft_id,
                    'revision': draft.revision,
                    'ja_enviado': True
                }
            
            # ✅ REGRA 3: Enviar usando a última revisão do banco
            logger.info(f'✅✅✅ [EMAIL_COORDINATOR] Enviando email do draft {draft_id} (revision {draft.revision})')
            
            # ✅ NOVO (09/01/2026): Converter markdown para HTML antes de enviar
            body_html = _markdown_to_html(draft.conteudo)
            
            # Enviar via email_service (com HTML)
            resultado_envio = self.email_service.send_email(
                to=draft.destinatarios,
                subject=draft.assunto,
                body_text=draft.conteudo,  # Manter texto plano como fallback
                body_html=body_html,  # ✅ NOVO: Enviar HTML convertido
                cc=draft.cc if draft.cc else None,
                bcc=draft.bcc if draft.bcc else None,
                from_mailbox=None  # Usar mailbox padrão
            )
            
            if resultado_envio.get('sucesso'):
                # ✅ REGRA 4: Marcar como enviado após sucesso
                self.email_draft_service.marcar_como_enviado(draft_id)
                logger.info(f'✅✅✅ [EMAIL_COORDINATOR] Email enviado com sucesso. Draft {draft_id} marcado como enviado.')
                
                return {
                    'sucesso': True,
                    'resposta': f"✅ Email enviado com sucesso para {len(draft.destinatarios)} destinatário(s):\n- {', '.join(draft.destinatarios)}\n\n**Assunto:** {draft.assunto}\n\n**Mensagem:**\n{draft.conteudo}",
                    'draft_id': draft_id,
                    'revision': draft.revision,
                    'destinatarios': draft.destinatarios,
                    'metodo': resultado_envio.get('metodo', 'SMTP')
                }
            else:
                erro_msg = resultado_envio.get('erro') or resultado_envio.get('mensagem', 'Erro desconhecido')
                logger.error(f'❌ [EMAIL_COORDINATOR] Erro ao enviar email do draft {draft_id}: {erro_msg}')
                return {
                    'sucesso': False,
                    'erro': resultado_envio.get('erro', 'ERRO_ENVIO_EMAIL'),
                    'resposta': f'❌ Erro ao enviar email: {erro_msg}',
                    'draft_id': draft_id,
                    'revision': draft.revision
                }
        
        except Exception as e:
            logger.error(f'❌ [EMAIL_COORDINATOR] Erro inesperado ao enviar email do draft {draft_id}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INESPERADO',
                'resposta': f'❌ Erro inesperado ao enviar email: {str(e)}',
                'draft_id': draft_id
            }
    
    def send_report_email(
        self,
        destinatario: str,
        resumo_texto: str,
        assunto: str,
        categoria: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia relatório por email (sem draft).
        
        Este método é para relatórios que não usam sistema de drafts.
        Ainda assim, convergimos para email_service para manter consistência.
        
        Args:
            destinatario: Email do destinatário
            resumo_texto: Texto do relatório
            assunto: Assunto do email
            categoria: Categoria do relatório (opcional)
        
        Returns:
            Dict com resultado do envio
        """
        if not self.email_service:
            return {
                'sucesso': False,
                'erro': 'EMAIL_SERVICE_NAO_DISPONIVEL',
                'resposta': '❌ Serviço de email não disponível'
            }
        
        try:
            resultado = self.email_service.enviar_resumo_por_email(
                destinatario=destinatario,
                resumo_texto=resumo_texto,
                categoria=categoria
            )
            
            if resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'resposta': f"✅ Relatório enviado por email com sucesso para {destinatario}\n\n**Assunto:** {assunto}",
                    'destinatario': destinatario,
                    'metodo': resultado.get('metodo', 'SMTP')
                }
            else:
                erro_msg = resultado.get('erro') or resultado.get('mensagem', 'Erro desconhecido')
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'ERRO_ENVIO_EMAIL'),
                    'resposta': f'❌ Erro ao enviar relatório por email: {erro_msg}'
                }
        
        except Exception as e:
            logger.error(f'❌ [EMAIL_COORDINATOR] Erro ao enviar relatório por email: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INESPERADO',
                'resposta': f'❌ Erro ao enviar relatório por email: {str(e)}'
            }
    
    def send_simple_email(
        self,
        destinatario: str,
        assunto: str,
        corpo: str
    ) -> Dict[str, Any]:
        """
        Envia email simples (sem draft, para compatibilidade com código antigo).
        
        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            corpo: Corpo do email
        
        Returns:
            Dict com resultado do envio
        """
        if not self.email_service:
            return {
                'sucesso': False,
                'erro': 'EMAIL_SERVICE_NAO_DISPONIVEL',
                'resposta': '❌ Serviço de email não disponível'
            }
        
        try:
            resultado = self.email_service.enviar_email(
                destinatario=destinatario,
                assunto=assunto,
                corpo_texto=corpo
            )
            
            if resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'resposta': f"✅ Email enviado com sucesso para {destinatario}\n\n**Assunto:** {assunto}",
                    'destinatario': destinatario,
                    'metodo': resultado.get('metodo', 'SMTP')
                }
            else:
                erro_msg = resultado.get('erro') or resultado.get('mensagem', 'Erro desconhecido')
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'ERRO_ENVIO_EMAIL'),
                    'resposta': f'❌ Erro ao enviar email: {erro_msg}'
                }
        
        except Exception as e:
            logger.error(f'❌ [EMAIL_COORDINATOR] Erro ao enviar email simples: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INESPERADO',
                'resposta': f'❌ Erro ao enviar email: {str(e)}'
            }


def get_email_send_coordinator() -> EmailSendCoordinator:
    """Factory function para obter instância singleton do coordenador."""
    if not hasattr(get_email_send_coordinator, '_instance'):
        get_email_send_coordinator._instance = EmailSendCoordinator()
    return get_email_send_coordinator._instance
