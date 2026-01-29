"""
Serviço para envio e recebimento de emails via Microsoft Graph API (Office 365).
Suporta também SMTP como fallback.
"""
import logging
import smtplib
import os
import json
import re
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

# Tentar importar msal (Microsoft Authentication Library)
try:
    from msal import ConfidentialClientApplication
    HAS_MSAL = True
except ImportError:
    HAS_MSAL = False
    logger = logging.getLogger(__name__)
    logger.warning("⚠️ Biblioteca 'msal' não encontrada. Instale com: pip install msal")

# Tentar carregar variáveis do .env se disponível
try:
    from dotenv import load_dotenv
    try:
        load_dotenv()
    except PermissionError as e:
        # Em ambientes sandboxados/CI, o arquivo pode existir mas não ser acessível
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️ Não foi possível ler .env (permissão negada): {e}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"⚠️ Falha ao carregar .env via python-dotenv: {e}")
except ImportError:
    pass

if not HAS_MSAL:
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger(__name__)


class EmailService:
    """Serviço para envio de emails via SMTP ou Microsoft Graph API."""
    
    def __init__(self):
        """Inicializa o serviço de email."""
        # Carregar configurações SMTP do .env
        self.smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.smtp_username = os.getenv('EMAIL_SENDER', '')
        self.smtp_password = os.getenv('EMAIL_PASSWORD', '')
        
        # Carregar configurações Microsoft Graph do .env
        self.tenant_id = os.getenv('EMAIL_TENANT_ID', '')
        self.client_id = os.getenv('EMAIL_CLIENT_ID', '')
        self.client_secret = os.getenv('EMAIL_CLIENT_SECRET', '')
        self.default_mailbox = os.getenv('EMAIL_DEFAULT_MAILBOX', self.smtp_username)
        
        # Verificar se tem Microsoft Graph configurado
        self.has_microsoft_graph = bool(
            self.tenant_id and 
            self.client_id and 
            self.client_secret and
            self.default_mailbox
        )
        
        # Habilitar se tiver SMTP completo OU Microsoft Graph
        self.enabled = bool((self.smtp_username and self.smtp_password) or self.has_microsoft_graph)
        
        if not self.enabled:
            if self.smtp_username and not self.smtp_password:
                logger.warning(f"⚠️ Email parcialmente configurado. EMAIL_SENDER={self.smtp_username}, mas EMAIL_PASSWORD está vazio.")
            logger.warning(f"⚠️ Email não configurado. Configure EMAIL_SENDER e EMAIL_PASSWORD (SMTP) ou EMAIL_TENANT_ID, EMAIL_CLIENT_ID, EMAIL_CLIENT_SECRET e EMAIL_DEFAULT_MAILBOX (Microsoft Graph) no .env")
        elif self.has_microsoft_graph:
            logger.info(f"✅ Email habilitado via Microsoft Graph API (mailbox: {self.default_mailbox})")
        else:
            logger.info(f"✅ Email habilitado via SMTP (servidor: {self.smtp_server})")
    
    def _obter_token_microsoft_graph(self) -> Optional[str]:
        """
        Obtém token de acesso do Microsoft Graph API usando client credentials flow (fallback).
        
        Returns:
            Token de acesso ou None se falhar
        """
        try:
            # URL de autenticação
            auth_url = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'
            
            # Dados para obter token
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }
            
            # Fazer requisição
            response = requests.post(auth_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            
            if access_token:
                logger.debug("✅ Token Microsoft Graph obtido com sucesso (via requests)")
                return access_token
            else:
                logger.error(f"❌ Token não encontrado na resposta: {token_data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao obter token Microsoft Graph: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Detalhes do erro: {error_detail}")
                except:
                    logger.error(f"Resposta: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao obter token: {e}", exc_info=True)
            return None
    
    def _enviar_via_microsoft_graph(
        self,
        destinatario: str,
        assunto: str,
        corpo_texto: str,
        corpo_html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia email via Microsoft Graph API.
        
        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            corpo_texto: Corpo do email em texto
            corpo_html: Corpo do email em HTML (opcional)
        
        Returns:
            Dict com sucesso, mensagem, erro
        """
        try:
            # Obter token
            access_token = self._obter_token_microsoft_graph()
            if not access_token:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_TOKEN',
                    'mensagem': 'Não foi possível obter token do Microsoft Graph'
                }
            
            # Preparar corpo do email (usar HTML se disponível, senão texto)
            body_content = corpo_html if corpo_html else corpo_texto
            body_content_type = 'HTML' if corpo_html else 'Text'
            
            # Montar mensagem conforme formato do Microsoft Graph API
            email_message = {
                'message': {
                    'subject': assunto,
                    'body': {
                        'contentType': body_content_type,
                        'content': body_content
                    },
                    'toRecipients': [
                        {
                            'emailAddress': {
                                'address': destinatario
                            }
                        }
                    ]
                }
            }
            
            # URL da API do Microsoft Graph
            graph_url = f'https://graph.microsoft.com/v1.0/users/{self.default_mailbox}/sendMail'
            
            # Headers
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Enviar email
            response = requests.post(graph_url, json=email_message, headers=headers, timeout=30)
            
            if response.status_code == 202:
                logger.info(f"✅ Email enviado via Microsoft Graph para {destinatario}: {assunto}")
                return {
                    'sucesso': True,
                    'mensagem': f'Email enviado com sucesso para {destinatario}',
                    'destinatario': destinatario,
                    'metodo': 'Microsoft Graph API'
                }
            else:
                error_text = response.text
                logger.error(f"❌ Erro ao enviar email via Microsoft Graph: {response.status_code} - {error_text}")
                return {
                    'sucesso': False,
                    'erro': 'ERRO_GRAPH_API',
                    'mensagem': f'Erro ao enviar email via Microsoft Graph: {response.status_code} - {error_text}'
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro de requisição ao enviar email via Microsoft Graph: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_REQUISICAO',
                'mensagem': f'Erro de requisição ao enviar email: {str(e)}'
            }
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao enviar email via Microsoft Graph: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro interno ao enviar email: {str(e)}'
            }
    
    def _enviar_via_smtp(
        self,
        destinatario: str,
        assunto: str,
        corpo_texto: str,
        corpo_html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia email via SMTP tradicional.
        
        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            corpo_texto: Corpo do email em texto
            corpo_html: Corpo do email em HTML (opcional)
        
        Returns:
            Dict com sucesso, mensagem, erro
        """
        try:
            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_username
            msg['To'] = destinatario
            msg['Subject'] = assunto
            
            # Adicionar corpo em texto
            part_texto = MIMEText(corpo_texto, 'plain', 'utf-8')
            msg.attach(part_texto)
            
            # Adicionar corpo em HTML se fornecido
            if corpo_html:
                part_html = MIMEText(corpo_html, 'html', 'utf-8')
                msg.attach(part_html)
            
            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email enviado via SMTP para {destinatario}: {assunto}")
            
            return {
                'sucesso': True,
                'mensagem': f'Email enviado com sucesso para {destinatario}',
                'destinatario': destinatario,
                'metodo': 'SMTP'
            }
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Erro de autenticação SMTP: {e}")
            return {
                'sucesso': False,
                'erro': 'ERRO_AUTENTICACAO',
                'mensagem': f'Erro de autenticação ao enviar email: {str(e)}'
            }
        except smtplib.SMTPException as e:
            logger.error(f"❌ Erro SMTP ao enviar email: {e}")
            return {
                'sucesso': False,
                'erro': 'ERRO_SMTP',
                'mensagem': f'Erro ao enviar email: {str(e)}'
            }
        except Exception as e:
            logger.error(f"❌ Erro ao enviar email via SMTP: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro interno ao enviar email: {str(e)}'
            }
    
    def send_email(
        self,
        to: List[str],
        subject: str,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        from_mailbox: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia email via Microsoft Graph API (compatível com versão 1.5).
        
        Args:
            to: Lista de destinatários (emails)
            subject: Assunto do email
            body_html: Corpo do email em HTML (opcional)
            body_text: Corpo do email em texto plano (opcional, usado se body_html não fornecido)
            cc: Lista de emails em cópia (opcional)
            bcc: Lista de emails em cópia oculta (opcional)
            attachments: Lista de anexos (opcional). Cada item: {'name': str, 'content': bytes, 'contentType': str}
            from_mailbox: Email de origem (se None, usa default_mailbox)
        
        Returns:
            Dict com resultado:
            {
                'sucesso': bool,
                'mensagem_id': str (se sucesso),
                'erro': str (se falhou)
            }
        """
        if not self.has_microsoft_graph:
            return {
                'sucesso': False,
                'erro': 'EmailService não está habilitado. Configure as credenciais Microsoft Graph no .env'
            }
        
        if not to:
            return {
                'sucesso': False,
                'erro': 'Lista de destinatários vazia'
            }
        
        # Determinar email de origem
        from_email = from_mailbox or self.default_mailbox or to[0]
        
        # Obter token
        token = self.get_access_token()
        if not token:
            return {
                'sucesso': False,
                'erro': 'Não foi possível obter token de acesso do Microsoft Graph'
            }
        
        # Preparar corpo do email
        content_type = "html" if body_html else "text"
        content = body_html if body_html else (body_text or "")
        
        # Preparar payload
        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": content_type,
                    "content": content
                },
                "toRecipients": [
                    {"emailAddress": {"address": email}} for email in to
                ]
            }
        }
        
        # Adicionar CC se fornecido
        if cc:
            message["message"]["ccRecipients"] = [
                {"emailAddress": {"address": email}} for email in cc
            ]
        
        # Adicionar BCC se fornecido
        if bcc:
            message["message"]["bccRecipients"] = [
                {"emailAddress": {"address": email}} for email in bcc
            ]
        
        # Preparar anexos se fornecidos
        if attachments:
            message["message"]["attachments"] = []
            for att in attachments:
                import base64
                att_data = {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": att.get('name', 'anexo'),
                    "contentType": att.get('contentType', 'application/octet-stream'),
                    "contentBytes": base64.b64encode(att.get('content', b'')).decode('utf-8')
                }
                message["message"]["attachments"].append(att_data)
        
        # Enviar email via Graph API
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Endpoint para enviar email: POST /users/{id}/sendMail
            url = f"https://graph.microsoft.com/v1.0/users/{from_email}/sendMail"
            
            response = requests.post(
                url,
                headers=headers,
                json=message,
                timeout=30
            )
            
            if response.status_code in (200, 202):
                logger.info(f"✅ Email enviado com sucesso: {subject} → {', '.join(to)}")
                return {
                    'sucesso': True,
                    'mensagem_id': response.headers.get('Location', 'N/A'),
                    'destinatarios': to
                }
            else:
                error_msg = f"Erro ao enviar email: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    'sucesso': False,
                    'erro': error_msg
                }
        
        except Exception as e:
            error_msg = f"Erro ao enviar email: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'sucesso': False,
                'erro': error_msg
            }
    
    def enviar_email(
        self,
        destinatario: str,
        assunto: str,
        corpo_texto: str,
        corpo_html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia email usando Microsoft Graph API (se configurado) ou SMTP (fallback).
        Método compatível com código antigo.
        
        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            corpo_texto: Corpo do email em texto
            corpo_html: Corpo do email em HTML (opcional)
        
        Returns:
            Dict com sucesso, mensagem, erro
        """
        if not self.enabled:
            return {
                'sucesso': False,
                'erro': 'EMAIL_NAO_CONFIGURADO',
                'mensagem': 'Email não está configurado. Configure EMAIL_SENDER e EMAIL_PASSWORD (SMTP) ou EMAIL_TENANT_ID, EMAIL_CLIENT_ID, EMAIL_CLIENT_SECRET e EMAIL_DEFAULT_MAILBOX (Microsoft Graph) no .env'
            }
        
        # Priorizar Microsoft Graph se configurado
        if self.has_microsoft_graph:
            return self._enviar_via_microsoft_graph(destinatario, assunto, corpo_texto, corpo_html)
        elif self.smtp_username and self.smtp_password:
            return self._enviar_via_smtp(destinatario, assunto, corpo_texto, corpo_html)
        else:
            return {
                'sucesso': False,
                'erro': 'EMAIL_NAO_CONFIGURADO',
                'mensagem': 'Email não está configurado corretamente'
            }
    
    def enviar_resumo_por_email(
        self,
        destinatario: str,
        resumo_texto: str,
        categoria: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envia resumo/dashboard por email.
        
        Args:
            destinatario: Email do destinatário
            resumo_texto: Texto do resumo (markdown)
            categoria: Categoria do resumo (opcional)
        
        Returns:
            Dict com sucesso, mensagem, erro
        """
        # Converter markdown para HTML simples
        # Substituir quebras de linha por <br>
        html_corpo = resumo_texto.replace('\n', '<br>\n')
        # Converter markdown básico para HTML
        html_corpo = html_corpo.replace('**', '<strong>').replace('**', '</strong>')
        html_corpo = html_corpo.replace('*', '<em>').replace('*', '</em>')
        html_corpo = html_corpo.replace('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', '<hr>')
        
        # Criar HTML completo
        html_completo = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                hr {{ border: none; border-top: 2px solid #eee; margin: 20px 0; }}
                strong {{ color: #2c3e50; }}
            </style>
        </head>
        <body>
            {html_corpo}
        </body>
        </html>
        """
        
        # Assunto do email
        hoje = datetime.now().strftime('%d/%m/%Y')
        assunto = f"Resumo do Dia - {hoje}"
        if categoria:
            assunto = f"Resumo {categoria.upper()} - {hoje}"
        
        return self.enviar_email(
            destinatario=destinatario,
            assunto=assunto,
            corpo_texto=resumo_texto,
            corpo_html=html_completo
        )
    
    def get_access_token(self) -> Optional[str]:
        """
        Obtém token de acesso do Microsoft Graph API usando msal (se disponível) ou requests.
        
        Returns:
            Token de acesso ou None em caso de erro
        """
        if not self.has_microsoft_graph:
            logger.error("EmailService não está habilitado (credenciais Microsoft Graph não configuradas)")
            return None
        
        try:
            # Tentar usar msal primeiro (mais robusto)
            if HAS_MSAL:
                app_auth = ConfidentialClientApplication(
                    self.client_id,
                    authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                    client_credential=self.client_secret,
                )
                
                result = app_auth.acquire_token_for_client(
                    scopes=["https://graph.microsoft.com/.default"]
                )
                
                if "access_token" not in result:
                    logger.error(f"❌ Erro ao obter token Graph: {result}")
                    return None
                
                return result["access_token"]
            else:
                # Fallback para método requests (já implementado)
                return self._obter_token_microsoft_graph()
        
        except Exception as e:
            logger.error(f"❌ Erro ao obter token de acesso: {e}", exc_info=True)
            return None
    
    def read_emails(
        self,
        mailbox: Optional[str] = None,
        limit: int = 10,
        filter_read: bool = False,
        max_days: int = 7
    ) -> Dict[str, Any]:
        """
        Lê emails da caixa de entrada via Microsoft Graph API.
        
        Args:
            mailbox: Email da caixa de entrada (se None, usa default_mailbox)
            limit: Número máximo de emails para retornar (padrão: 10)
            filter_read: Se True, retorna apenas emails não lidos (padrão: False - todos)
            max_days: Número máximo de dias para buscar emails (padrão: 7)
        
        Returns:
            Dict com resultado:
            {
                'sucesso': bool,
                'emails': List[Dict] (se sucesso),
                'erro': str (se falhou)
            }
        """
        if not self.has_microsoft_graph:
            return {
                'sucesso': False,
                'erro': 'EmailService não está habilitado. Configure as credenciais Microsoft Graph no .env'
            }
        
        # Usar mailbox fornecido ou default
        target_mailbox = mailbox or self.default_mailbox
        if not target_mailbox:
            return {
                'sucesso': False,
                'erro': 'Nenhum mailbox especificado para leitura de emails'
            }
        
        # Obter token
        token = self.get_access_token()
        if not token:
            return {
                'sucesso': False,
                'erro': 'Não foi possível obter token de acesso do Microsoft Graph'
            }
        
        try:
            # ✅ IMPORTANTE: usar UTC para filtro de datas (Graph usa DateTimeOffset).
            # Se usarmos datetime.now() local e carimbarmos "Z", podemos filtrar errado e retornar 0 emails.
            now_utc = datetime.now(timezone.utc)
            cutoff_dt = now_utc - timedelta(days=max_days)
            cutoff_date = cutoff_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

            # Construir filtro OData
            filters = [f"receivedDateTime ge {cutoff_date}"]
            if filter_read:
                filters.append("isRead eq false")
            filter_query = " and ".join(filters)

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            def _parse_emails(graph_json: Dict[str, Any], folder_name: str) -> list[dict]:
                emails_local: list[dict] = []
                for msg in graph_json.get('value', []) or []:
                    emails_local.append(
                        {
                            'id': msg.get('id'),
                            'subject': msg.get('subject', 'Sem assunto'),
                            'from': msg.get('from', {}).get('emailAddress', {}).get('address', 'Desconhecido'),
                            'from_name': msg.get('from', {}).get('emailAddress', {}).get('name', ''),
                            'received_datetime': msg.get('receivedDateTime'),
                            'is_read': msg.get('isRead', False),
                            'body_preview': msg.get('bodyPreview', ''),
                            'body': msg.get('body', {}).get('content', '') if isinstance(msg.get('body'), dict) else '',
                            'folder': folder_name,
                        }
                    )
                return emails_local

            # ✅ Preferir Inbox explicitamente (mais previsível do que /messages)
            inbox_url = f"https://graph.microsoft.com/v1.0/users/{target_mailbox}/mailFolders/Inbox/messages"
            junk_url = f"https://graph.microsoft.com/v1.0/users/{target_mailbox}/mailFolders/JunkEmail/messages"
            # 🔎 Fallback: buscar em TODAS as pastas (regras/subpastas/arquivo/etc.)
            all_messages_url = f"https://graph.microsoft.com/v1.0/users/{target_mailbox}/messages"
            params = {
                '$filter': filter_query,
                '$orderby': 'receivedDateTime desc',
                '$top': limit,
                '$select': 'id,subject,from,receivedDateTime,bodyPreview,body,isRead',
            }

            response = requests.get(inbox_url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                inbox_emails = _parse_emails(data, folder_name="inbox")

                # ✅ Se o inbox vier com poucos emails, complementar com JunkEmail
                # (muitos recebidos podem cair como spam/quarentena no M365).
                emails = list(inbox_emails)
                ids = {e.get('id') for e in emails if e.get('id')}
                if len(emails) < limit:
                    try:
                        faltando = max(0, limit - len(emails))
                        if faltando > 0:
                            params_junk = dict(params)
                            params_junk['$top'] = faltando
                            rj = requests.get(junk_url, headers=headers, params=params_junk, timeout=30)
                            if rj.status_code == 200:
                                junk_data = rj.json()
                                junk_emails = _parse_emails(junk_data, folder_name="junk")
                                # dedupe por id
                                for e in junk_emails:
                                    if e.get('id') and e.get('id') not in ids:
                                        emails.append(e)
                                        ids.add(e.get('id'))
                    except Exception:
                        # Não falhar leitura se junk der problema
                        pass

                # ✅ Se ainda estiver curto (ou Inbox/Junk não acharem), buscar globalmente (/messages).
                # Isso captura emails que caíram em subpastas, arquivo, regras, etc.
                if len(emails) < limit:
                    try:
                        faltando = max(0, limit - len(emails))
                        params_all = dict(params)
                        params_all['$top'] = max(5, faltando)  # garantir algum resultado
                        ra = requests.get(all_messages_url, headers=headers, params=params_all, timeout=30)
                        if ra.status_code == 200:
                            all_data = ra.json()
                            all_emails = _parse_emails(all_data, folder_name="any")
                            for e in all_emails:
                                if e.get('id') and e.get('id') not in ids:
                                    emails.append(e)
                                    ids.add(e.get('id'))
                    except Exception:
                        pass

                # 🔁 Fallback de robustez:
                # Se não vier nada (mas o usuário diz que há emails), tentar sem filtro de data.
                if not emails:
                    params_sem_data = dict(params)
                    if filter_read:
                        params_sem_data['$filter'] = "isRead eq false"
                    else:
                        params_sem_data.pop('$filter', None)

                    response2 = requests.get(inbox_url, headers=headers, params=params_sem_data, timeout=30)
                    if response2.status_code == 200:
                        data2 = response2.json()
                        emails2 = _parse_emails(data2, folder_name="inbox")
                        if emails2:
                            logger.warning(
                                "⚠️ read_emails: filtro por data retornou 0, mas sem filtro retornou emails. "
                                f"mailbox={target_mailbox} cutoff={cutoff_date} max_days={max_days}"
                            )
                            return {
                                'sucesso': True,
                                'emails': emails2,
                                'total': len(emails2),
                                'debug': {
                                    'mailbox': target_mailbox,
                                    'cutoff_utc': cutoff_date,
                                    'max_days': max_days,
                                    'fallback_sem_filtro_data': True,
                                },
                            }

                logger.info(f"✅ {len(emails)} emails lidos da caixa de entrada {target_mailbox}")
                return {
                    'sucesso': True,
                    'emails': emails,
                    'total': len(emails),
                    'debug': {
                        'mailbox': target_mailbox,
                        'cutoff_utc': cutoff_date,
                        'max_days': max_days,
                        'fallback_sem_filtro_data': False,
                    },
                }

            error_msg = f"Erro ao ler emails: {response.status_code} - {response.text}"
            logger.error(f"❌ {error_msg}")
            return {'sucesso': False, 'erro': error_msg}

        except Exception as e:
            error_msg = f"Erro ao ler emails: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {'sucesso': False, 'erro': error_msg}
    
    def get_email_by_id(
        self,
        message_id: str,
        mailbox: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca um email específico pelo ID via Microsoft Graph API.
        
        Args:
            message_id: ID da mensagem (obtido de read_emails)
            mailbox: Email da caixa de entrada (se None, usa default_mailbox)
        
        Returns:
            Dict com resultado:
            {
                'sucesso': bool,
                'email': Dict (se sucesso),
                'erro': str (se falhou)
            }
        """
        if not self.has_microsoft_graph:
            return {
                'sucesso': False,
                'erro': 'EmailService não está habilitado. Configure as credenciais Microsoft Graph no .env'
            }
        
        target_mailbox = mailbox or self.default_mailbox
        if not target_mailbox:
            return {
                'sucesso': False,
                'erro': 'Nenhum mailbox especificado'
            }
        
        token = self.get_access_token()
        if not token:
            return {
                'sucesso': False,
                'erro': 'Não foi possível obter token de acesso do Microsoft Graph'
            }
        
        try:
            # Endpoint para buscar mensagem específica: GET /users/{id}/messages/{message-id}
            url = f"https://graph.microsoft.com/v1.0/users/{target_mailbox}/messages/{message_id}"
            params = {
                '$select': 'id,subject,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,bodyPreview,body,isRead,importance,hasAttachments'
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                msg = response.json()
                
                # Processar corpo do email (remover HTML se necessário)
                body_content = ''
                body_type = 'text'
                if isinstance(msg.get('body'), dict):
                    body_content = msg.get('body', {}).get('content', '')
                    body_type = msg.get('body', {}).get('contentType', 'text')
                
                # Processar destinatários
                to_recipients = []
                if msg.get('toRecipients'):
                    to_recipients = [r.get('emailAddress', {}).get('address', '') for r in msg.get('toRecipients', [])]
                
                cc_recipients = []
                if msg.get('ccRecipients'):
                    cc_recipients = [r.get('emailAddress', {}).get('address', '') for r in msg.get('ccRecipients', [])]
                
                email_info = {
                    'id': msg.get('id'),
                    'subject': msg.get('subject', 'Sem assunto'),
                    'from': msg.get('from', {}).get('emailAddress', {}).get('address', 'Desconhecido'),
                    'from_name': msg.get('from', {}).get('emailAddress', {}).get('name', ''),
                    'to': to_recipients,
                    'cc': cc_recipients,
                    'received_datetime': msg.get('receivedDateTime'),
                    'is_read': msg.get('isRead', False),
                    'body_preview': msg.get('bodyPreview', ''),
                    'body': body_content,
                    'body_type': body_type,
                    'importance': msg.get('importance', 'normal'),
                    'has_attachments': msg.get('hasAttachments', False)
                }
                
                logger.info(f"✅ Email {message_id} encontrado")
                return {
                    'sucesso': True,
                    'email': email_info
                }
            else:
                error_msg = f"Erro ao buscar email: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    'sucesso': False,
                    'erro': error_msg
                }
        
        except Exception as e:
            error_msg = f"Erro ao buscar email: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'sucesso': False,
                'erro': error_msg
            }
    
    def extract_processos_from_email(self, email_content: str) -> List[str]:
        """
        Extrai números de processos mencionados no conteúdo do email.
        
        Procura por padrões como: ALH.0001/25, MV5.0014/25, VDM.0030/25, etc.
        Formato: [CATEGORIA].[NUMERO]/[ANO]
        
        Args:
            email_content: Conteúdo do email (assunto + corpo)
        
        Returns:
            Lista de processos encontrados (ex: ['ALH.0001/25', 'MV5.0014/25'])
        """
        # Padrão para encontrar processos: CATEGORIA.NUMERO/ANO
        # Exemplos: ALH.0001/25, MV5.0014/25, VDM.0030/25, BND.0094/25
        # Categoria: 2-4 letras/números maiúsculos
        # Número: 1-4 dígitos
        # Ano: 2 dígitos
        pattern = r'\b([A-Z0-9]{2,4})\.(\d{1,4})/(\d{2})\b'
        
        matches = re.findall(pattern, email_content.upper())
        
        # Formatar processos encontrados (garantir 4 dígitos no número)
        processos = []
        for categoria, numero, ano in matches:
            numero_formatado = numero.zfill(4)  # Garantir 4 dígitos
            processo = f"{categoria}.{numero_formatado}/{ano}"
            if processo not in processos:  # Evitar duplicatas
                processos.append(processo)
        
        return processos
    
    def reply_to_email(
        self,
        message_id: str,
        reply_content: str,
        mailbox: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Responde a um email via Microsoft Graph API.
        
        Args:
            message_id: ID da mensagem original (obtido de read_emails)
            reply_content: Conteúdo da resposta (texto ou HTML)
            mailbox: Email da caixa de entrada (se None, usa default_mailbox)
        
        Returns:
            Dict com resultado:
            {
                'sucesso': bool,
                'mensagem_id': str (se sucesso),
                'erro': str (se falhou)
            }
        """
        if not self.has_microsoft_graph:
            return {
                'sucesso': False,
                'erro': 'EmailService não está habilitado. Configure as credenciais no .env'
            }
        
        # Usar mailbox fornecido ou default
        target_mailbox = mailbox or self.default_mailbox
        if not target_mailbox:
            return {
                'sucesso': False,
                'erro': 'Nenhum mailbox especificado para responder email'
            }
        
        if not message_id:
            return {
                'sucesso': False,
                'erro': 'message_id é obrigatório'
            }
        
        if not reply_content:
            return {
                'sucesso': False,
                'erro': 'Conteúdo da resposta não pode ser vazio'
            }
        
        # Obter token
        token = self.get_access_token()
        if not token:
            return {
                'sucesso': False,
                'erro': 'Não foi possível obter token de acesso do Microsoft Graph'
            }
        
        try:
            # Preparar payload para resposta
            # O Graph API automaticamente inclui o email original na resposta
            # O comment é a nossa mensagem de resposta
            payload = {
                "comment": reply_content
            }
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Endpoint para responder email: POST /users/{id}/messages/{message-id}/reply
            url = f"https://graph.microsoft.com/v1.0/users/{target_mailbox}/messages/{message_id}/reply"
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in (200, 202):
                logger.info(f"✅ Email respondido com sucesso: message_id={message_id}")
                return {
                    'sucesso': True,
                    'mensagem_id': message_id,
                    'resposta_enviada': True
                }
            else:
                error_msg = f"Erro ao responder email: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return {
                    'sucesso': False,
                    'erro': error_msg
                }
        
        except Exception as e:
            error_msg = f"Erro ao responder email: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return {
                'sucesso': False,
                'erro': error_msg
            }
    
    def send_report_email(
        self,
        to: List[str],
        report_title: str,
        report_content: str,
        process_reference: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Envia relatório formatado por email.
        
        Args:
            to: Lista de destinatários
            report_title: Título do relatório
            report_content: Conteúdo do relatório (pode ser HTML ou texto)
            process_reference: Referência do processo (opcional, para incluir no assunto)
            attachments: Anexos (opcional)
        
        Returns:
            Dict com resultado do envio
        """
        # Preparar assunto
        subject = f"Relatório: {report_title}"
        if process_reference:
            subject = f"[{process_reference}] {subject}"
        
        # Preparar corpo HTML formatado
        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                .metadata {{
                    background-color: #ecf0f1;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .metadata p {{
                    margin: 5px 0;
                }}
                .content {{
                    margin-top: 20px;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 0.9em;
                    color: #7f8c8d;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{report_title}</h1>
                <div class="metadata">
                    <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                    {f'<p><strong>Processo:</strong> {process_reference}</p>' if process_reference else ''}
                    <p><strong>Enviado por:</strong> Chat IA Independente (Sistema Automático)</p>
                </div>
                <div class="content">
                    {report_content if '<' in report_content else f'<pre style="white-space: pre-wrap;">{report_content}</pre>'}
                </div>
                <div class="footer">
                    <p>Este email foi enviado automaticamente pelo Chat IA Independente</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Usar send_email que aceita lista de destinatários
        return self.send_email(
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=report_content if '<' not in report_content else None,
            cc=cc,
            bcc=bcc,
            attachments=attachments
        )


# Instância global do serviço
_email_service_instance = None

def get_email_service() -> EmailService:
    """Retorna instância singleton do EmailService."""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance







