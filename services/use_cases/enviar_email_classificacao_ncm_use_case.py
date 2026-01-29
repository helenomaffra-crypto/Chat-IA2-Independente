"""
Use case para envio de email de classificação NCM com alíquotas.

Este use case centraliza a lógica de negócio para enviar emails de classificação fiscal,
utilizando o contexto salvo de NCM + alíquotas TECwin.
"""
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from services.email_builder_service import EmailBuilderService
from services.context_service import buscar_contexto_sessao
from services.email_service import get_email_service

logger = logging.getLogger(__name__)


@dataclass
class EnviarEmailClassificacaoNcmRequest:
    """Request para envio de email de classificação NCM."""
    session_id: str
    destinatario: str
    nome_destinatario: Optional[str] = None
    nome_usuario: Optional[str] = None
    confirmar_envio: bool = True  # Se True, só mostra preview; se False, já envia


@dataclass
class EnviarEmailClassificacaoNcmResult:
    """Resultado do envio de email de classificação NCM."""
    sucesso: bool
    mensagem_chat: str
    preview_email: Optional[Dict[str, Any]] = None
    erro: Optional[str] = None


class EnviarEmailClassificacaoNcmUseCase:
    """
    Use case para envio de email de classificação NCM com alíquotas.
    
    Fluxo:
    1. Buscar contexto de ultima_classificacao_ncm para o session_id
    2. Se não houver contexto → retornar mensagem amigável
    3. Se houver:
       - Chamar EmailBuilderService.montar_email_classificacao_ncm
       - Se confirmar_envio=True: retornar preview e aguardar confirmação
       - Se confirmar_envio=False: enviar email real e confirmar envio
    """
    
    def __init__(self):
        """Inicializa o use case."""
        self.email_builder = EmailBuilderService()
        # EmailService será obtido via get_email_service() quando necessário
    
    def executar(
        self,
        request: EnviarEmailClassificacaoNcmRequest
    ) -> EnviarEmailClassificacaoNcmResult:
        """
        Executa o use case de envio de email de classificação NCM.
        
        Args:
            request: Request com session_id, destinatario, etc.
        
        Returns:
            Result com sucesso, mensagem_chat, preview_email (se preview), erro
        """
        try:
            logger.info(f"[USE_CASE] Iniciando envio de email de classificação NCM para {request.destinatario}")
            
            # 1. Buscar contexto de ultima_classificacao_ncm
            contextos = buscar_contexto_sessao(
                session_id=request.session_id,
                tipo_contexto='ultima_classificacao_ncm'
            )
            
            if not contextos or len(contextos) == 0:
                logger.warning(f"[USE_CASE] ⚠️ Nenhum contexto de NCM encontrado para session_id {request.session_id}")
                return EnviarEmailClassificacaoNcmResult(
                    sucesso=False,
                    mensagem_chat=(
                        "⚠️ **Não encontrei nenhuma classificação de NCM recente nesta conversa.**\n\n"
                        "💡 **Para enviar um email com classificação fiscal e alíquotas, você precisa:**\n"
                        "1. Perguntar sobre a NCM de um produto (ex: \"qual a ncm de oculos?\")\n"
                        "2. Consultar as alíquotas no TECwin (ex: \"tecwin 90041000\")\n"
                        "3. Depois pedir para enviar o email\n\n"
                        "**Ou me diga qual NCM ou descreva o produto para eu classificar e depois montar o email.**"
                    ),
                    erro='CONTEXTO_NCM_NAO_ENCONTRADO'
                )
            
            # Pegar o contexto mais recente
            contexto_ncm = contextos[0].get('dados', {})
            
            if not contexto_ncm or not contexto_ncm.get('ncm'):
                logger.warning(f"[USE_CASE] ⚠️ Contexto de NCM encontrado mas sem NCM válido")
                return EnviarEmailClassificacaoNcmResult(
                    sucesso=False,
                    mensagem_chat=(
                        "⚠️ **Contexto de NCM encontrado, mas sem informações válidas.**\n\n"
                        "💡 Por favor, faça uma nova classificação de NCM e consulte as alíquotas no TECwin."
                    ),
                    erro='NCM_INVALIDO_NO_CONTEXTO'
                )
            
            ncm = contexto_ncm.get('ncm', '')
            logger.info(f"[USE_CASE] ✅ Contexto de NCM encontrado: {ncm}")
            
            # 2. Montar email usando EmailBuilderService
            resultado_email = self.email_builder.montar_email_classificacao_ncm(
                destinatario=request.destinatario,
                contexto_ncm=contexto_ncm,
                texto_pedido_usuario=None,  # Não necessário, já temos o contexto completo
                nome_usuario=request.nome_usuario
            )
            
            if not resultado_email.get('sucesso'):
                logger.error(f"[USE_CASE] ❌ Erro ao montar email: {resultado_email.get('erro')}")
                return EnviarEmailClassificacaoNcmResult(
                    sucesso=False,
                    mensagem_chat=f"❌ **Erro ao montar email:** {resultado_email.get('erro', 'Erro desconhecido')}",
                    erro=resultado_email.get('erro')
                )
            
            assunto = resultado_email.get('assunto', 'Classificação Fiscal e Alíquotas')
            conteudo = resultado_email.get('conteudo', '')
            
            logger.info(f"[USE_CASE] ✅ Email montado com sucesso. Assunto: {assunto[:50]}...")
            
            # 3. Se confirmar_envio=True, retornar preview
            if request.confirmar_envio:
                preview = self._formatar_preview_email(
                    destinatario=request.destinatario,
                    assunto=assunto,
                    conteudo=conteudo
                )
                
                preview_dict = {
                    'destinatario': request.destinatario,
                    'assunto': assunto,
                    'conteudo': conteudo
                }
                
                logger.info(f"[USE_CASE] ✅ Preview gerado. Aguardando confirmação do usuário.")
                
                return EnviarEmailClassificacaoNcmResult(
                    sucesso=True,
                    mensagem_chat=preview,
                    preview_email=preview_dict
                )
            
            # 4. Se confirmar_envio=False, enviar email real
            logger.info(f"[USE_CASE] Enviando email real para {request.destinatario}")
            
            email_service = get_email_service()
            resultado_envio = email_service.enviar_email(
                destinatario=request.destinatario,
                assunto=assunto,
                corpo_texto=conteudo
            )
            
            if resultado_envio.get('sucesso'):
                logger.info(f"[USE_CASE] ✅ Email enviado com sucesso para {request.destinatario}")
                return EnviarEmailClassificacaoNcmResult(
                    sucesso=True,
                    mensagem_chat=(
                        f"✅ **Email enviado com sucesso!**\n\n"
                        f"**Para:** {request.destinatario}\n"
                        f"**Assunto:** {assunto}\n\n"
                        f"O email contém:\n"
                        f"• Classificação NCM {ncm}\n"
                        f"• Alíquotas de importação (TECwin)\n"
                        f"• Nota Explicativa NESH\n"
                        f"• Justificativa da classificação"
                    )
                )
            else:
                erro_envio = resultado_envio.get('erro', 'Erro desconhecido')
                logger.error(f"[USE_CASE] ❌ Erro ao enviar email: {erro_envio}")
                return EnviarEmailClassificacaoNcmResult(
                    sucesso=False,
                    mensagem_chat=f"❌ **Erro ao enviar email:** {erro_envio}",
                    erro=erro_envio
                )
                
        except Exception as e:
            logger.error(f"[USE_CASE] ❌ Erro inesperado ao executar use case: {e}", exc_info=True)
            return EnviarEmailClassificacaoNcmResult(
                sucesso=False,
                mensagem_chat=f"❌ **Erro inesperado:** {str(e)}",
                erro=str(e)
            )
    
    def _formatar_preview_email(
        self,
        destinatario: str,
        assunto: str,
        conteudo: str
    ) -> str:
        """
        Formata preview do email para exibir no chat.
        
        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            conteudo: Conteúdo do email
        
        Returns:
            String formatada com preview
        """
        from datetime import datetime
        
        preview = "📧 **Email para Envio**\n\n"
        preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        preview += f"**De:** Sistema mAIke (Make Consultores)\n"
        preview += f"**Para:** {destinatario}\n"
        preview += f"**Assunto:** {assunto}\n"
        preview += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        preview += "**Mensagem:**\n\n"
        
        # Limitar tamanho do preview (primeiras 1000 caracteres)
        if len(conteudo) > 1000:
            preview += conteudo[:1000] + "\n\n... (conteúdo completo será enviado no email)"
        else:
            preview += conteudo
        
        preview += "\n\n"
        preview += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        preview += "⚠️ **Confirme para enviar** (digite 'sim' ou 'pode enviar' ou 'enviar')"
        
        return preview

