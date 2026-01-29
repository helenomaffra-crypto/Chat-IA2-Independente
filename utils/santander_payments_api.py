"""
Cliente Python para API de Pagamentos (TED, PIX, etc.) do Santander.

⚠️ ISOLADO: Esta API é completamente separada da API de Extratos.
Cada tipo de API pode precisar de credenciais diferentes (Client ID/Secret diferentes).

Versão independente integrada ao projeto Chat-IA-Independente.
Não depende de diretório externo.
"""
import requests
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import json
import time
import os
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

def _resolver_caminho_certificado(
    caminho_atual: Optional[str],
    *,
    candidatos: List[Path],
    label: str,
) -> Optional[str]:
    """Fallback seguro de caminhos quando o projeto foi movido/renomeado e o .env ficou com path antigo."""
    try:
        if caminho_atual and os.path.exists(caminho_atual):
            return caminho_atual
        for c in candidatos:
            try:
                if c and c.exists():
                    logger.warning(f"🔄 {label} não encontrado em '{caminho_atual}'. Usando fallback: {str(c)}")
                    return str(c)
            except Exception:
                continue
    except Exception:
        pass
    return caminho_atual


@dataclass
class SantanderPaymentsConfig:
    """
    Configuração da API Santander para Pagamentos (TED, PIX, etc.).
    
    ⚠️ IMPORTANTE: Esta configuração é SEPARADA da API de Extratos.
    Você pode precisar de credenciais diferentes (Client ID/Secret diferentes)
    se criou aplicações separadas no Developer Portal do Santander.
    """
    # Credenciais OAuth2 (podem ser diferentes das de extratos)
    client_id: str = None
    client_secret: str = None
    
    # URLs da API
    base_url: str = None
    token_url: str = None
    
    # Workspace ID (pré-requisito para usar pagamentos)
    workspace_id: str = None
    
    # Certificados para mTLS (mutual TLS)
    # Pode usar os mesmos certificados ou diferentes
    cert_file: str = None  # Caminho para o certificado .pem ou .crt
    key_file: str = None   # Caminho para a chave privada .key
    cert_path: str = None  # Caminho para certificado combinado (cert + key)
    
    def __post_init__(self):
        """Carrega valores do .env se não fornecidos"""
        # ⚠️ Variáveis de ambiente SEPARADAS para pagamentos
        if self.client_id is None:
            self.client_id = os.getenv("SANTANDER_PAYMENTS_CLIENT_ID", "") or os.getenv("SANTANDER_CLIENT_ID", "")
        if self.client_secret is None:
            self.client_secret = os.getenv("SANTANDER_PAYMENTS_CLIENT_SECRET", "") or os.getenv("SANTANDER_CLIENT_SECRET", "")
        
        if self.base_url is None:
            # ✅ Padrão: Sandbox (mais seguro para desenvolvimento)
            self.base_url = os.getenv("SANTANDER_PAYMENTS_BASE_URL", "https://trust-sandbox.api.santander.com.br")
        
        if self.token_url is None:
            token_url_env = os.getenv("SANTANDER_PAYMENTS_TOKEN_URL")
            if token_url_env:
                self.token_url = token_url_env
            else:
                # Determinar URL baseado no base_url
                if "sandbox" in self.base_url.lower():
                    self.token_url = "https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token"
                else:
                    self.token_url = "https://trust-open.api.santander.com.br/auth/oauth/v2/token"
        
        # Workspace ID (pode ser configurado no .env ou criado automaticamente)
        if self.workspace_id is None:
            self.workspace_id = os.getenv("SANTANDER_WORKSPACE_ID", "")
        
        # Certificados (pode usar os mesmos ou diferentes)
        # ✅ Alinhado com implementação de Extratos que funciona
        if self.cert_file is None:
            # Tentar certificados específicos de pagamentos primeiro, depois fallback para genérico
            self.cert_file = os.getenv("SANTANDER_PAYMENTS_CERT_FILE") or os.getenv("SANTANDER_CERT_FILE")
        if self.key_file is None:
            self.key_file = os.getenv("SANTANDER_PAYMENTS_KEY_FILE") or os.getenv("SANTANDER_KEY_FILE")
        if self.cert_path is None:
            self.cert_path = os.getenv("SANTANDER_PAYMENTS_CERT_PATH") or os.getenv("SANTANDER_CERT_PATH")

        # ✅ Robustez: se .env apontar para pasta antiga, tentar .secure/ do projeto atual
        project_root = Path(__file__).resolve().parents[1]
        secure_dir = project_root / ".secure"
        cert_basename = Path(self.cert_file).name if self.cert_file else None
        key_basename = Path(self.key_file).name if self.key_file else None
        cert_path_basename = Path(self.cert_path).name if self.cert_path else None

        if cert_basename:
            self.cert_file = _resolver_caminho_certificado(
                self.cert_file,
                candidatos=[secure_dir / cert_basename],
                label="SANTANDER_PAYMENTS_CERT_FILE",
            )
        if key_basename:
            self.key_file = _resolver_caminho_certificado(
                self.key_file,
                candidatos=[secure_dir / key_basename],
                label="SANTANDER_PAYMENTS_KEY_FILE",
            )
        if cert_path_basename:
            self.cert_path = _resolver_caminho_certificado(
                self.cert_path,
                candidatos=[secure_dir / cert_path_basename],
                label="SANTANDER_PAYMENTS_CERT_PATH",
            )
        
        # ✅ Log de diagnóstico (igual ao Extrato)
        # Nota: debug não é atributo de Config, apenas de API
        if not self.cert_file and not self.cert_path:
            logger.warning("⚠️ Certificados mTLS não configurados para Pagamentos. A API do Santander EXIGE certificados mTLS.")
        
        # Validar credenciais obrigatórias
        if not self.client_id or not self.client_secret:
            logger.warning(
                "⚠️ Client ID e Client Secret de Pagamentos não configurados. "
                "Configure SANTANDER_PAYMENTS_CLIENT_ID e SANTANDER_PAYMENTS_CLIENT_SECRET no .env "
                "ou use SANTANDER_CLIENT_ID/SANTANDER_CLIENT_SECRET como fallback."
            )
        
        # Aviso sobre certificados mTLS
        if not self.cert_file and not self.cert_path:
            logger.warning("⚠️ Certificados mTLS não configurados para Pagamentos. A API do Santander EXIGE certificados mTLS.")


class SantanderPaymentsAPI:
    """
    Cliente Python para API de Pagamentos do Santander (TED, PIX, Boleto, etc.).
    
    ⚠️ ISOLADO: Esta classe é completamente independente de SantanderExtratoAPI.
    Pode usar credenciais diferentes se você criou aplicações separadas no Developer Portal.
    """
    
    def __init__(self, config: SantanderPaymentsConfig, debug: bool = False):
        self.config = config
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self.debug = debug
        self._temp_cert_file: Optional[str] = None  # Arquivo temporário criado a partir de .pfx
        
        # Configurar certificados mTLS se fornecidos
        self._setup_mtls()
    
    def _extrair_pfx_para_pem(self, pfx_path: str, senha: str = "senha001") -> Optional[str]:
        """
        Extrai certificado e chave privada de um arquivo .pfx para .pem temporário.
        
        ✅ Igual ao Banco do Brasil - suporta .pfx automaticamente.
        
        Args:
            pfx_path: Caminho do arquivo .pfx
            senha: Senha do arquivo .pfx
        
        Returns:
            Caminho do arquivo .pem temporário ou None se falhar
        """
        import subprocess
        import tempfile
        
        try:
            # Criar arquivo temporário
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pem', prefix='santander_payments_')
            os.close(temp_fd)
            
            # Extrair certificado e chave privada do .pfx
            result = subprocess.run(
                ['openssl', 'pkcs12',
                 '-in', pfx_path,
                 '-out', temp_path,
                 '-nodes',  # Sem criptografia na chave privada
                 '-passin', f'pass:{senha}',
                 '-legacy'  # Suportar .pfx antigos
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Verificar se o arquivo foi criado e tem conteúdo
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    # Verificar se contém chave privada
                    with open(temp_path, 'r') as f:
                        content = f.read()
                        if 'BEGIN PRIVATE KEY' in content or 'BEGIN RSA PRIVATE KEY' in content:
                            if self.debug:
                                logger.debug(f"✅ Certificado .pfx extraído com sucesso para: {temp_path}")
                            return temp_path
                        else:
                            logger.warning(f"⚠️ Arquivo .pfx extraído mas não contém chave privada")
                            if os.path.exists(temp_path):
                                os.unlink(temp_path)
                            return None
                else:
                    logger.error(f"❌ Arquivo .pfx extraído mas está vazio")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    return None
            else:
                logger.error(f"❌ Erro ao extrair .pfx: {result.stderr}")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Timeout ao extrair .pfx")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao extrair .pfx: {e}", exc_info=True)
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    
    def _setup_mtls(self):
        """Configura certificados mTLS para autenticação mútua"""
        # ✅ Alinhado com implementação de Extratos que funciona
        # ✅ NOVO: Suporte para .pfx (igual ao Banco do Brasil)
        if self.config.cert_path:
            cert_path = self.config.cert_path
            
            # ✅ NOVO: Se for arquivo .pfx, extrair automaticamente
            if cert_path.lower().endswith('.pfx') or cert_path.lower().endswith('.p12'):
                if os.path.exists(cert_path):
                    # Tentar senha do .env ou padrão
                    senha_pfx = os.getenv("SANTANDER_PFX_PASSWORD", os.getenv("SANTANDER_PAYMENTS_PFX_PASSWORD", "senha001"))
                    temp_pem = self._extrair_pfx_para_pem(cert_path, senha_pfx)
                    if temp_pem:
                        self.session.cert = temp_pem
                        self._temp_cert_file = temp_pem  # Guardar para limpar depois
                        logger.info(f"✅ Certificado .pfx convertido automaticamente para uso em mTLS - Pagamentos: {cert_path}")
                    else:
                        logger.error(f"❌ Não foi possível extrair certificado do .pfx: {cert_path}")
                        logger.error(f"💡 Verifique se a senha está correta. Configure SANTANDER_PFX_PASSWORD ou SANTANDER_PAYMENTS_PFX_PASSWORD no .env se necessário.")
                else:
                    logger.warning(f"⚠️ Arquivo .pfx não encontrado: {cert_path}")
            elif os.path.exists(cert_path):
                # Certificado combinado (cert + key no mesmo arquivo)
                self.session.cert = cert_path
                logger.info(f"✅ Certificado mTLS configurado (arquivo combinado) - Pagamentos: {cert_path}")
            else:
                logger.warning(f"⚠️ Certificado não encontrado: {cert_path}")
        elif self.config.cert_file and self.config.key_file:
            # Certificado e chave separados
            if os.path.exists(self.config.cert_file) and os.path.exists(self.config.key_file):
                self.session.cert = (self.config.cert_file, self.config.key_file)
                logger.info(f"✅ Certificado mTLS configurado (cert + key separados) - Pagamentos: cert={self.config.cert_file}, key={self.config.key_file}")
            else:
                missing = []
                if not os.path.exists(self.config.cert_file):
                    missing.append(f"cert={self.config.cert_file}")
                if not os.path.exists(self.config.key_file):
                    missing.append(f"key={self.config.key_file}")
                logger.warning(f"⚠️ Certificados não encontrados: {', '.join(missing)}")
    
    def __del__(self):
        """Limpa arquivo temporário se foi criado a partir de .pfx"""
        if hasattr(self, '_temp_cert_file') and self._temp_cert_file:
            try:
                if os.path.exists(self._temp_cert_file):
                    os.unlink(self._temp_cert_file)
            except Exception:
                pass  # Ignorar erros na limpeza
    
    def _log(self, message: str):
        """Log apenas se debug estiver ativado"""
        if self.debug:
            logger.debug(f"[SantanderPaymentsAPI] {message}")
    
    def _get_access_token(self, force_refresh: bool = False) -> str:
        """
        Obtém token de acesso (JWT) para API de Pagamentos.
        
        ⚠️ IMPORTANTE: Este token é SEPARADO do token de extratos.
        Se você tem aplicações diferentes, cada uma terá seu próprio token.
        
        ✅ Alinhado com implementação de Extratos que funciona.
        """
        # Verificar se token ainda é válido (com margem de 1 minuto)
        if not force_refresh and self._access_token and self._token_expires_at:
            if time.time() < (self._token_expires_at - 60):
                return self._access_token
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        token_data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "client_credentials"
        }
        
        # ✅ Suportar múltiplas URLs (igual ao Extrato)
        if self.config.token_url:
            token_urls = [self.config.token_url]
        else:
            if "sandbox" in self.config.base_url.lower():
                token_urls = ["https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token"]
            else:
                token_urls = ["https://trust-open.api.santander.com.br/auth/oauth/v2/token"]
        
        last_error = None
        
        for i, token_url in enumerate(token_urls, 1):
            try:
                base_url = token_url.rstrip('/')
                self._log(f"Tentativa {i}/{len(token_urls)}: {base_url}")
                
                response = self.session.post(
                    base_url,
                    data=token_data,
                    headers=headers,
                    timeout=30
                )
                
                self._log(f"Resposta recebida: Status {response.status_code}")
                
                if response.status_code == 200:
                    response.raise_for_status()
                    token_response = response.json()
                    
                    self._access_token = token_response["access_token"]
                    expires_in = token_response.get("expires_in", 900)
                    self._token_expires_at = time.time() + expires_in
                    
                    self._log("✅ Token OAuth2 obtido com sucesso para Pagamentos")
                    return self._access_token
                else:
                    continue
                        
            except requests.HTTPError as e:
                self._log(f"❌ Erro HTTP {e.response.status_code}: {e.response.text[:200]}")
                last_error = e
                if e.response.status_code in [401, 400, 403, 404]:
                    continue
                if e.response.status_code == 401:
                    raise ValueError(f"Credenciais inválidas para Pagamentos. Verifique Client ID e Client Secret.")
                raise Exception(f"Erro ao obter token de Pagamentos: {e.response.text}")
            except requests.Timeout:
                self._log(f"⏱️ Timeout na URL {token_url}")
                last_error = Exception(f"Timeout ao conectar em {token_url}")
                continue
            except requests.RequestException as e:
                self._log(f"❌ Erro de conexão: {type(e).__name__}: {str(e)[:100]}")
                last_error = e
                continue
        
        # ✅ Se chegou aqui, nenhuma URL funcionou - diagnóstico detalhado (igual ao Extrato)
        error_summary = []
        error_summary.append(f"❌ Não foi possível obter token após tentar {len(token_urls)} URLs.")
        
        if not self.config.cert_file and not self.config.cert_path:
            error_summary.append("⚠️ Certificados mTLS NÃO configurados!")
        else:
            if self.config.cert_file and os.path.exists(self.config.cert_file):
                error_summary.append(f"✅ Certificado encontrado: {self.config.cert_file}")
            else:
                error_summary.append(f"❌ Certificado NÃO encontrado: {self.config.cert_file}")
            
            if self.config.key_file and os.path.exists(self.config.key_file):
                error_summary.append(f"✅ Chave encontrada: {self.config.key_file}")
            else:
                error_summary.append(f"❌ Chave NÃO encontrada: {self.config.key_file}")
        
        if last_error:
            if isinstance(last_error, requests.HTTPError):
                error_summary.append(f"Último erro HTTP: {last_error.response.status_code}")
                error_summary.append(f"Resposta: {last_error.response.text[:300]}")
            else:
                error_summary.append(f"Último erro: {type(last_error).__name__}")
                error_summary.append(f"Detalhes: {str(last_error)[:300]}")
        
        raise Exception("\n".join(error_summary))
    
    def _get_headers(self, use_token: bool = True) -> Dict[str, str]:
        """Retorna headers necessários para as requisições de Pagamentos"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if use_token:
            try:
                # ✅ Verificar se credenciais estão configuradas
                if not self.config.client_id or not self.config.client_secret:
                    raise ValueError(
                        "Client ID e Client Secret não configurados. "
                        "Configure SANTANDER_PAYMENTS_CLIENT_ID e SANTANDER_PAYMENTS_CLIENT_SECRET no .env"
                    )
                
                token = self._get_access_token()
                if not token:
                    raise ValueError("Token OAuth2 não foi gerado. Verifique credenciais e certificados mTLS.")
                
                headers["Authorization"] = f"Bearer {token}"
                headers["X-Application-Key"] = self.config.client_id
                
                logger.debug(f"✅ Headers configurados: Authorization=Bearer {token[:20]}..., X-Application-Key={self.config.client_id[:20]}...")
            except Exception as e:
                logger.error(f"❌ Erro ao configurar headers: {e}", exc_info=True)
                raise
        
        return headers
    
    # ==========================================
    # MÉTODOS DE WORKSPACE
    # ==========================================
    
    def criar_workspace(
        self,
        tipo: str,
        main_debit_account: Dict[str, str],
        description: str = "",
        pix_payments_active: bool = False,
        bar_code_payments_active: bool = False,
        bank_slip_payments_active: bool = False,
        bank_transfer_payments_active: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Cria um workspace para pagamentos.
        
        Args:
            tipo: Tipo de workspace (PAYMENTS, PHYSICAL_CORBAN, DIGITAL_CORBAN)
            main_debit_account: Dict com 'branch' e 'number' da conta principal
            description: Descrição do workspace
            pix_payments_active: Ativar PIX (opcional)
            bar_code_payments_active: Ativar código de barras (opcional)
            bank_slip_payments_active: Ativar boleto (opcional)
            bank_transfer_payments_active: Ativar transferências bancárias/TED (opcional)
            **kwargs: Outros parâmetros opcionais
        
        Returns:
            Dict com dados do workspace criado
        """
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces"
        
        # ✅ Manter como strings (API aceita strings conforme exemplo da documentação)
        branch = str(main_debit_account.get("branch", "")).strip()
        number = str(main_debit_account.get("number", "")).strip()
        
        # ✅ Limitar descrição a 30 caracteres (exigência da API)
        descricao_final = description or f"Workspace {tipo}"
        if len(descricao_final) > 30:
            descricao_final = descricao_final[:30]
        
        body = {
            "type": tipo,
            "description": descricao_final,
            "mainDebitAccount": {
                "branch": branch,
                "number": number
            },
            "pixPaymentsActive": pix_payments_active,
            "barCodePaymentsActive": bar_code_payments_active,
            "bankSlipPaymentsActive": bank_slip_payments_active,
            "bankTransferPaymentsActive": bank_transfer_payments_active,  # ✅ Ativar TED
            **kwargs
        }
        
        # ✅ DEBUG: Log do body sendo enviado
        logger.info(f"📤 Body sendo enviado para criar workspace: {json.dumps(body, indent=2, ensure_ascii=False)}")
        
        headers = self._get_headers()
        
        try:
            response = self.session.post(url, json=body, headers=headers, timeout=30)
            
            logger.info(f"📥 Resposta recebida: Status {response.status_code}")
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.post(url, json=body, headers=headers, timeout=30)
                logger.info(f"📥 Resposta após refresh token: Status {response.status_code}")
            
            # ✅ Log da resposta antes de raise_for_status para capturar erros 400
            if response.status_code >= 400:
                logger.error(f"❌ Erro HTTP {response.status_code} ao criar workspace")
                logger.error(f"📥 Resposta completa (texto): {response.text[:1000]}")
                try:
                    error_json = response.json()
                    logger.error(f"📥 Resposta completa (JSON): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                except:
                    pass
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            # Tentar extrair mensagem de erro detalhada da resposta
            error_msg = str(e)
            error_details = ""
            if hasattr(e, 'response') and e.response:
                try:
                    error_json = e.response.json()
                    logger.error(f"❌ Resposta de erro da API ao criar workspace (status {e.response.status_code}): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                    if isinstance(error_json, dict):
                        api_error = error_json.get('message') or error_json.get('error') or error_json.get('errors') or error_json
                        if api_error:
                            error_details = f"\n\nDetalhes da API:\n{json.dumps(api_error, indent=2, ensure_ascii=False)}"
                    else:
                        error_details = f"\n\nResposta completa: {e.response.text}"
                except Exception as parse_error:
                    logger.error(f"❌ Erro ao parsear resposta: {parse_error}")
                    error_details = f"\n\nResposta completa (texto): {e.response.text[:1000]}"
                    logger.error(f"❌ Resposta HTTP (texto): {e.response.text[:1000]}")
            raise Exception(f"Erro ao criar workspace: {error_msg}{error_details}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao criar workspace: {str(e)}")
    
    def listar_workspaces(self) -> Dict[str, Any]:
        """Lista todos os workspaces disponíveis"""
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces"
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            # ✅ Melhorar tratamento de erro 403
            error_msg = str(e)
            error_details = ""
            
            if hasattr(e, 'response') and e.response:
                try:
                    error_json = e.response.json()
                    logger.error(f"❌ Resposta de erro da API (status {e.response.status_code}): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                    if isinstance(error_json, dict):
                        api_error = error_json.get('message') or error_json.get('error') or error_json.get('errors') or error_json
                        if api_error:
                            error_details = f"\n\nDetalhes da API:\n{json.dumps(api_error, indent=2, ensure_ascii=False)}"
                    else:
                        error_details = f"\n\nResposta completa: {e.response.text}"
                except Exception:
                    error_details = f"\n\nResposta completa (texto): {e.response.text}"
                
                # ✅ Mensagem específica para 403
                if e.response.status_code == 403:
                    error_details += "\n\n💡 Possíveis causas de 403 Forbidden:"
                    error_details += "\n   - Credenciais (Client ID/Secret) incorretas ou não configuradas"
                    error_details += "\n   - Certificado mTLS não configurado ou inválido"
                    error_details += "\n   - Token OAuth2 inválido ou expirado"
                    error_details += "\n   - Aplicação não tem permissão para acessar workspaces"
                    error_details += "\n   - Verifique se SANTANDER_PAYMENTS_CLIENT_ID e SANTANDER_PAYMENTS_CLIENT_SECRET estão no .env"
                    error_details += "\n   - Verifique se SANTANDER_PAYMENTS_CERT_FILE e SANTANDER_PAYMENTS_KEY_FILE estão configurados"
            
            raise Exception(f"Erro ao listar workspaces: {error_msg}{error_details}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao listar workspaces: {str(e)}")
    
    def consultar_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Consulta workspace por ID"""
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}"
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao consultar workspace: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao consultar workspace: {str(e)}")
    
    # ==========================================
    # MÉTODOS DE TED TRANSFERS
    # ==========================================
    
    def iniciar_ted(
        self,
        workspace_id: str,
        source_account: Dict[str, str],
        destination_account: Dict[str, Any],
        transfer_value: str,
        destination_type: str = "STR0008",
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia uma transferência TED.
        
        Args:
            workspace_id: ID do workspace
            source_account: Dict com 'branchCode' e 'accountNumber' da conta origem
            destination_account: Dict com dados da conta destino
            transfer_value: Valor da transferência (string com 2 decimais, ex: "10.00")
            destination_type: Tipo de destino (padrão: "STR0008")
            tags: Lista de tags opcionais
        
        Returns:
            Dict com dados da TED criada (inclui transfer_id)
        """
        if not workspace_id:
            raise ValueError("workspace_id é obrigatório")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/transfer"
        
        # ✅ Manter como strings (API aceita strings conforme exemplo da documentação)
        branch_code = str(source_account.get("branchCode") or source_account.get("branch") or "").strip()
        account_number = str(source_account.get("accountNumber") or source_account.get("number") or "").strip()
        
        body = {
            "sourceAccount": {
                "branchCode": branch_code,
                "accountNumber": account_number
            },
            "destinationAccount": destination_account,
            "destinationType": destination_type,
            "transferValue": transfer_value
        }
        
        if tags:
            body["tags"] = tags
        
        # ✅ DEBUG: Log do body sendo enviado
        logger.info(f"📤 Body sendo enviado para iniciar TED: {json.dumps(body, indent=2, ensure_ascii=False)}")
        
        headers = self._get_headers()
        
        try:
            response = self.session.post(url, json=body, headers=headers, timeout=30)
            
            logger.info(f"📥 Resposta recebida: Status {response.status_code}")
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.post(url, json=body, headers=headers, timeout=30)
                logger.info(f"📥 Resposta após refresh token: Status {response.status_code}")
            
            # ✅ Log da resposta antes de raise_for_status para capturar erros 400
            if response.status_code >= 400:
                logger.error(f"❌ Erro HTTP {response.status_code} ao iniciar TED")
                logger.error(f"📥 Resposta completa (texto): {response.text[:1000]}")
                try:
                    error_json = response.json()
                    logger.error(f"📥 Resposta completa (JSON): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                except:
                    pass
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            # Tentar extrair mensagem de erro detalhada da resposta
            error_msg = str(e)
            error_details = ""
            if hasattr(e, 'response') and e.response:
                try:
                    error_json = e.response.json()
                    logger.error(f"❌ Resposta de erro da API (status {e.response.status_code}): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                    if isinstance(error_json, dict):
                        # Tentar extrair mensagem de erro da API
                        errors_list = error_json.get('_errors', [])
                        if errors_list:
                            # Formatar erros de validação de forma mais legível
                            error_messages = []
                            for err in errors_list:
                                field = err.get('_field', '')
                                message = err.get('_message', '')
                                code = err.get('_code', '')
                                if field and message:
                                    error_messages.append(f"  • {field}: {message} (código: {code})")
                            
                            if error_messages:
                                error_details = f"\n\n❌ Erros de validação:\n" + "\n".join(error_messages)
                            else:
                                error_details = f"\n\nDetalhes da API:\n{json.dumps(error_json, indent=2, ensure_ascii=False)}"
                        else:
                            api_error = error_json.get('message') or error_json.get('error') or error_json
                            if api_error:
                                error_details = f"\n\nDetalhes da API:\n{json.dumps(api_error, indent=2, ensure_ascii=False)}"
                    else:
                        error_details = f"\n\nResposta completa: {e.response.text}"
                except Exception as parse_error:
                    logger.error(f"❌ Erro ao parsear resposta: {parse_error}")
                    error_details = f"\n\nResposta completa (texto): {e.response.text}"
                    logger.error(f"❌ Resposta HTTP (texto): {e.response.text}")
            raise Exception(f"Erro ao iniciar TED: {error_msg}{error_details}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao iniciar TED: {str(e)}")
    
    def efetivar_ted(
        self,
        workspace_id: str,
        transfer_id: str,
        source_account: Dict[str, str],
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """
        Efetiva uma TED iniciada.
        
        Args:
            workspace_id: ID do workspace
            transfer_id: ID da transferência (retornado por iniciar_ted)
            source_account: Dict com 'branchCode' e 'accountNumber' da conta origem
            status: Status da autorização (padrão: "AUTHORIZED")
        
        Returns:
            Dict com dados da TED efetivada
        """
        if not workspace_id or not transfer_id:
            raise ValueError("workspace_id e transfer_id são obrigatórios")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/transfer/{transfer_id}"
        
        # ✅ Manter como strings (API aceita strings conforme exemplo da documentação)
        branch_code = str(source_account.get("branchCode") or source_account.get("branch") or "").strip()
        account_number = str(source_account.get("accountNumber") or source_account.get("number") or "").strip()
        
        body = {
            "sourceAccount": {
                "branchCode": branch_code,
                "accountNumber": account_number
            },
            "status": status
        }
        
        headers = self._get_headers()
        
        try:
            response = self.session.patch(url, json=body, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.patch(url, json=body, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao efetivar TED: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao efetivar TED: {str(e)}")
    
    def consultar_ted(
        self,
        workspace_id: str,
        transfer_id: str
    ) -> Dict[str, Any]:
        """Consulta TED por ID"""
        if not workspace_id or not transfer_id:
            raise ValueError("workspace_id e transfer_id são obrigatórios")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/transfer/{transfer_id}"
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao consultar TED: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao consultar TED: {str(e)}")
    
    def listar_teds(
        self,
        workspace_id: str,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Lista TEDs paginado (para conciliação).
        
        Args:
            workspace_id: ID do workspace
            initial_date: Data inicial (YYYY-MM-DD)
            final_date: Data final (YYYY-MM-DD)
            status: Filtro por status (PENDING_VALIDATION, READY_TO_PAY, PENDING_CONFIRMATION, PAYED, REJECTED)
            limit: Limite de registros por página (padrão: 10)
            offset: Offset para paginação (padrão: 0)
        
        Returns:
            Dict com lista paginada de TEDs
        """
        if not workspace_id:
            raise ValueError("workspace_id é obrigatório")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/transfer"
        
        params = {
            "_limit": limit,
            "_offset": offset
        }
        
        if initial_date:
            params["initialDate"] = initial_date
        if final_date:
            params["finalDate"] = final_date
        if status:
            params["status"] = status
        
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao listar TEDs: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao listar TEDs: {str(e)}")
    
    # ==========================================
    # MÉTODOS DE ACCOUNTS AND TAXES
    # Bank Slip Payments, Barcode Payments, Pix Payments,
    # Vehicle Taxes Payments, Taxes by Fields Payments
    # ==========================================
    
    def _iniciar_pagamento_generico(
        self,
        workspace_id: str,
        payment_type: str,  # 'bank_slip_payments', 'barcode_payments', 'pix_payments', 'vehicle_taxes_payments', 'taxes_by_fields_payments'
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Método genérico para iniciar pagamentos (Boleto, Código de Barras, PIX, Impostos).
        
        Args:
            workspace_id: ID do workspace
            payment_type: Tipo de pagamento (bank_slip_payments, barcode_payments, pix_payments, etc.)
            payment_data: Dados do pagamento conforme especificação da API
        
        Returns:
            Dict com dados do pagamento criado (inclui payment_id)
        """
        if not workspace_id:
            raise ValueError("workspace_id é obrigatório")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/{payment_type}"
        
        logger.info(f"📤 Body sendo enviado para iniciar {payment_type}: {json.dumps(payment_data, indent=2, ensure_ascii=False)}")
        
        headers = self._get_headers()
        
        try:
            response = self.session.post(url, json=payment_data, headers=headers, timeout=30)
            
            logger.info(f"📥 Resposta recebida: Status {response.status_code}")
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.post(url, json=payment_data, headers=headers, timeout=30)
                logger.info(f"📥 Resposta após refresh token: Status {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"❌ Erro HTTP {response.status_code} ao iniciar {payment_type}")
                logger.error(f"📥 Resposta completa (texto): {response.text[:1000]}")
                try:
                    error_json = response.json()
                    logger.error(f"📥 Resposta completa (JSON): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                except:
                    pass
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = str(e)
            error_details = ""
            if hasattr(e, 'response') and e.response:
                try:
                    error_json = e.response.json()
                    logger.error(f"❌ Resposta de erro da API (status {e.response.status_code}): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                    if isinstance(error_json, dict):
                        errors_list = error_json.get('_errors', [])
                        if errors_list:
                            error_messages = []
                            for err in errors_list:
                                field = err.get('_field', '')
                                message = err.get('_message', '')
                                code = err.get('_code', '')
                                if field and message:
                                    error_messages.append(f"  • {field}: {message} (código: {code})")
                            
                            if error_messages:
                                error_details = f"\n\n❌ Erros de validação:\n" + "\n".join(error_messages)
                            else:
                                error_details = f"\n\nDetalhes da API:\n{json.dumps(error_json, indent=2, ensure_ascii=False)}"
                        else:
                            api_error = error_json.get('message') or error_json.get('error') or error_json
                            if api_error:
                                error_details = f"\n\nDetalhes da API:\n{json.dumps(api_error, indent=2, ensure_ascii=False)}"
                    else:
                        error_details = f"\n\nResposta completa: {e.response.text}"
                except Exception as parse_error:
                    logger.error(f"❌ Erro ao parsear resposta: {parse_error}")
                    error_details = f"\n\nResposta completa (texto): {e.response.text}"
            raise Exception(f"Erro ao iniciar {payment_type}: {error_msg}{error_details}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao iniciar {payment_type}: {str(e)}")
    
    def _efetivar_pagamento_generico(
        self,
        workspace_id: str,
        payment_type: str,
        payment_id: str,
        efetivacao_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Método genérico para efetivar pagamentos.
        
        Args:
            workspace_id: ID do workspace
            payment_type: Tipo de pagamento
            payment_id: ID do pagamento (retornado por iniciar)
            efetivacao_data: Dados para efetivação (paymentValue, debitAccount, status, etc.)
        
        Returns:
            Dict com dados do pagamento efetivado
        """
        if not workspace_id or not payment_id:
            raise ValueError("workspace_id e payment_id são obrigatórios")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/{payment_type}/{payment_id}"
        
        headers = self._get_headers()
        
        try:
            response = self.session.patch(url, json=efetivacao_data, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.patch(url, json=efetivacao_data, headers=headers, timeout=30)
            
            if response.status_code >= 400:
                logger.error(f"❌ Erro HTTP {response.status_code} ao efetivar {payment_type}")
                logger.error(f"📥 Resposta completa (texto): {response.text[:1000]}")
                try:
                    error_json = response.json()
                    logger.error(f"📥 Resposta completa (JSON): {json.dumps(error_json, indent=2, ensure_ascii=False)}")
                except:
                    pass
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao efetivar {payment_type}: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao efetivar {payment_type}: {str(e)}")
    
    def _consultar_pagamento_generico(
        self,
        workspace_id: str,
        payment_type: str,
        payment_id: str
    ) -> Dict[str, Any]:
        """Consulta pagamento por ID"""
        if not workspace_id or not payment_id:
            raise ValueError("workspace_id e payment_id são obrigatórios")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/{payment_type}/{payment_id}"
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao consultar {payment_type}: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao consultar {payment_type}: {str(e)}")
    
    def _listar_pagamentos_generico(
        self,
        workspace_id: str,
        payment_type: str,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lista pagamentos paginados"""
        if not workspace_id:
            raise ValueError("workspace_id é obrigatório")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/{payment_type}"
        
        params = {
            "_limit": limit,
            "_offset": offset
        }
        
        if initial_date:
            params["initialDate"] = initial_date
        if final_date:
            params["finalDate"] = final_date
        if status:
            params["status"] = status
        
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao listar {payment_type}: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao listar {payment_type}: {str(e)}")
    
    # ==========================================
    # BANK SLIP PAYMENTS (Boleto)
    # ==========================================
    
    def iniciar_bank_slip_payment(
        self,
        workspace_id: str,
        payment_id: str,
        code: str,
        payment_date: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento de boleto.
        
        Args:
            workspace_id: ID do workspace
            payment_id: ID único do pagamento (gerado pelo cliente)
            code: Código de barras do boleto
            payment_date: Data do pagamento (YYYY-MM-DD)
            tags: Lista de tags opcionais
        
        Returns:
            Dict com dados do pagamento criado
        """
        payment_data = {
            "id": payment_id,
            "code": code,
            "paymentDate": payment_date
        }
        if tags:
            payment_data["tags"] = tags
        
        return self._iniciar_pagamento_generico(workspace_id, "bank_slip_payments", payment_data)
    
    def efetivar_bank_slip_payment(
        self,
        workspace_id: str,
        payment_id: str,
        payment_value: float,
        debit_account: Dict[str, Any],
        final_payer: Dict[str, Any] = None,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """
        Efetiva pagamento de boleto.
        
        Args:
            workspace_id: ID do workspace
            payment_id: ID do pagamento
            payment_value: Valor do pagamento
            debit_account: Dict com 'branch' e 'number' da conta de débito
            final_payer: Dict com dados do pagador final (name, documentType, documentNumber)
            status: Status da autorização (padrão: "AUTHORIZED")
        
        Returns:
            Dict com dados do pagamento efetivado
        """
        efetivacao_data = {
            "paymentValue": payment_value,
            "debitAccount": debit_account,
            "status": status
        }
        
        # finalPayer é OBRIGATÓRIO para pagamento de boleto
        if not final_payer:
            raise ValueError("finalPayer é obrigatório para pagamento de boleto. Forneça name, documentType e documentNumber.")
        
        efetivacao_data["finalPayer"] = final_payer
        
        return self._efetivar_pagamento_generico(workspace_id, "bank_slip_payments", payment_id, efetivacao_data)
    
    def consultar_bank_slip_payment(self, workspace_id: str, payment_id: str) -> Dict[str, Any]:
        """Consulta pagamento de boleto por ID"""
        return self._consultar_pagamento_generico(workspace_id, "bank_slip_payments", payment_id)
    
    def listar_bank_slip_payments(
        self,
        workspace_id: str,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lista pagamentos de boleto paginados"""
        return self._listar_pagamentos_generico(workspace_id, "bank_slip_payments", initial_date, final_date, status, limit, offset)
    
    # ==========================================
    # BARCODE PAYMENTS (Código de Barras)
    # ==========================================
    
    def iniciar_barcode_payment(
        self,
        workspace_id: str,
        payment_id: str,
        code: str,
        payment_date: str,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento por código de barras.
        
        Args:
            workspace_id: ID do workspace
            payment_id: ID único do pagamento
            code: Código de barras
            payment_date: Data do pagamento (YYYY-MM-DD)
            tags: Lista de tags opcionais
        
        Returns:
            Dict com dados do pagamento criado
        """
        payment_data = {
            "id": payment_id,
            "code": code,
            "paymentDate": payment_date
        }
        if tags:
            payment_data["tags"] = tags
        
        return self._iniciar_pagamento_generico(workspace_id, "barcode_payments", payment_data)
    
    def efetivar_barcode_payment(
        self,
        workspace_id: str,
        payment_id: str,
        payment_value: float,
        debit_account: Dict[str, Any],
        final_payer: Dict[str, Any] = None,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento por código de barras"""
        efetivacao_data = {
            "paymentValue": payment_value,
            "debitAccount": debit_account,
            "status": status
        }
        if final_payer:
            efetivacao_data["finalPayer"] = final_payer
        
        return self._efetivar_pagamento_generico(workspace_id, "barcode_payments", payment_id, efetivacao_data)
    
    def consultar_barcode_payment(self, workspace_id: str, payment_id: str) -> Dict[str, Any]:
        """Consulta pagamento por código de barras por ID"""
        return self._consultar_pagamento_generico(workspace_id, "barcode_payments", payment_id)
    
    def listar_barcode_payments(
        self,
        workspace_id: str,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lista pagamentos por código de barras paginados"""
        return self._listar_pagamentos_generico(workspace_id, "barcode_payments", initial_date, final_date, status, limit, offset)
    
    # ==========================================
    # PIX PAYMENTS
    # ==========================================
    
    def iniciar_pix_payment(
        self,
        workspace_id: str,
        payment_id: str,
        payment_value: str,
        remittance_information: str = None,
        dict_code: str = None,
        dict_code_type: str = None,
        qr_code: str = None,
        ibge_town_code: int = None,
        payment_date: str = None,
        beneficiary: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento PIX.
        
        Suporta 3 modos:
        1. DICT (chave PIX): dict_code + dict_code_type
        2. QR Code: qr_code + ibge_town_code + payment_date
        3. Beneficiário: beneficiary (dados completos)
        
        Args:
            workspace_id: ID do workspace
            payment_id: ID único do pagamento
            payment_value: Valor do pagamento (string, ex: "100.50")
            remittance_information: Informação da remessa
            dict_code: Chave PIX (para modo DICT)
            dict_code_type: Tipo da chave PIX (EMAIL, CPF, CNPJ, PHONE, RANDOM_KEY)
            qr_code: Código QR (para modo QR Code)
            ibge_town_code: Código IBGE da cidade (para modo QR Code)
            payment_date: Data do pagamento (para modo QR Code)
            beneficiary: Dict com dados do beneficiário (para modo Beneficiário)
            tags: Lista de tags opcionais
        
        Returns:
            Dict com dados do pagamento criado
        """
        payment_data = {
            "id": payment_id,
            "paymentValue": payment_value
        }
        
        if remittance_information:
            payment_data["remittanceInformation"] = remittance_information
        
        # Modo DICT
        if dict_code and dict_code_type:
            payment_data["dictCode"] = dict_code
            payment_data["dictCodeType"] = dict_code_type
        
        # Modo QR Code
        if qr_code:
            payment_data["qrCode"] = qr_code
            if ibge_town_code:
                payment_data["ibgeTownCode"] = ibge_town_code
            if payment_date:
                payment_data["paymentDate"] = payment_date
        
        # Modo Beneficiário
        if beneficiary:
            payment_data["beneficiary"] = beneficiary
        
        if tags:
            payment_data["tags"] = tags
        
        return self._iniciar_pagamento_generico(workspace_id, "pix_payments", payment_data)
    
    def efetivar_pix_payment(
        self,
        workspace_id: str,
        payment_id: str,
        payment_value: float,
        debit_account: Dict[str, Any],
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento PIX"""
        efetivacao_data = {
            "paymentValue": payment_value,
            "debitAccount": debit_account,
            "status": status
        }
        
        return self._efetivar_pagamento_generico(workspace_id, "pix_payments", payment_id, efetivacao_data)
    
    def consultar_pix_payment(self, workspace_id: str, payment_id: str) -> Dict[str, Any]:
        """Consulta pagamento PIX por ID"""
        return self._consultar_pagamento_generico(workspace_id, "pix_payments", payment_id)
    
    def listar_pix_payments(
        self,
        workspace_id: str,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lista pagamentos PIX paginados"""
        return self._listar_pagamentos_generico(workspace_id, "pix_payments", initial_date, final_date, status, limit, offset)
    
    # ==========================================
    # VEHICLE TAXES PAYMENTS (IPVA)
    # ==========================================
    
    def consultar_debitos_renavam(
        self,
        workspace_id: str,
        renavam: int = None,
        state_abbreviation: str = None
    ) -> Dict[str, Any]:
        """
        Consulta débitos do Renavam (IPVA, licenciamento, etc.).
        
        Args:
            workspace_id: ID do workspace
            renavam: Número do Renavam
            state_abbreviation: Sigla do estado (ex: "SP", "MG")
        
        Returns:
            Dict com lista de débitos disponíveis
        """
        if not workspace_id:
            raise ValueError("workspace_id é obrigatório")
        
        url = f"{self.config.base_url}/management_payments_partners/v1/workspaces/{workspace_id}/available_vehicle_taxes"
        
        params = {}
        if renavam:
            params["renavam"] = renavam
        if state_abbreviation:
            params["stateAbbreviation"] = state_abbreviation
        
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 401:
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.HTTPError as e:
            error_msg = response.text if hasattr(e, 'response') and e.response else str(e)
            raise Exception(f"Erro ao consultar débitos Renavam: {error_msg}")
        except requests.RequestException as e:
            raise Exception(f"Erro de conexão ao consultar débitos Renavam: {str(e)}")
    
    def iniciar_vehicle_tax_payment(
        self,
        workspace_id: str,
        payment_id: str,
        renavam: int,
        tax_type: str,  # "IPVA"
        exercise_year: int,
        state_abbreviation: str,
        doc_type: str,  # "CPF" ou "CNPJ"
        document_number: int,
        type_quota: str = "SINGLE",  # "SINGLE" ou "MULTIPLE"
        payment_date: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento de imposto veicular (IPVA).
        
        Args:
            workspace_id: ID do workspace
            payment_id: ID único do pagamento
            renavam: Número do Renavam
            tax_type: Tipo de imposto (ex: "IPVA")
            exercise_year: Ano de exercício
            state_abbreviation: Sigla do estado
            doc_type: Tipo de documento (CPF ou CNPJ)
            document_number: Número do documento
            type_quota: Tipo de quota (SINGLE ou MULTIPLE)
            payment_date: Data do pagamento (YYYY-MM-DD)
            tags: Lista de tags opcionais
        
        Returns:
            Dict com dados do pagamento criado
        """
        payment_data = {
            "id": payment_id,
            "renavam": renavam,
            "taxType": tax_type,
            "exerciseYear": exercise_year,
            "stateAbbreviation": state_abbreviation,
            "docType": doc_type,
            "documentNumber": document_number,
            "typeQuota": type_quota
        }
        
        if payment_date:
            payment_data["paymentDate"] = payment_date
        if tags:
            payment_data["tags"] = tags
        
        return self._iniciar_pagamento_generico(workspace_id, "vehicle_taxes_payments", payment_data)
    
    def efetivar_vehicle_tax_payment(
        self,
        workspace_id: str,
        payment_id: str,
        debit_account: Dict[str, Any],
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento de imposto veicular"""
        efetivacao_data = {
            "debitAccount": debit_account,
            "status": status
        }
        
        return self._efetivar_pagamento_generico(workspace_id, "vehicle_taxes_payments", payment_id, efetivacao_data)
    
    def consultar_vehicle_tax_payment(self, workspace_id: str, payment_id: str) -> Dict[str, Any]:
        """Consulta pagamento de imposto veicular por ID"""
        return self._consultar_pagamento_generico(workspace_id, "vehicle_taxes_payments", payment_id)
    
    def listar_vehicle_tax_payments(
        self,
        workspace_id: str,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lista pagamentos de impostos veiculares paginados"""
        return self._listar_pagamentos_generico(workspace_id, "vehicle_taxes_payments", initial_date, final_date, status, limit, offset)
    
    # ==========================================
    # TAXES BY FIELDS PAYMENTS (GARE, DARF, GPS)
    # ==========================================
    
    def iniciar_tax_by_fields_payment(
        self,
        workspace_id: str,
        payment_id: str,
        tax_type: str,  # "GARE ICMS", "GARE ITCMD", "DARF", "GPS"
        payment_date: str,
        city: str = None,
        state_abbreviation: str = None,
        fields: Dict[str, Any] = None,  # field01, field02, etc. conforme tipo de imposto
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento de imposto por campos (GARE, DARF, GPS).
        
        Args:
            workspace_id: ID do workspace
            payment_id: ID único do pagamento
            tax_type: Tipo de imposto ("GARE ICMS", "GARE ITCMD", "DARF", "GPS")
            payment_date: Data do pagamento (YYYY-MM-DD)
            city: Cidade
            state_abbreviation: Sigla do estado
            fields: Dict com campos específicos do imposto (field01, field02, etc.)
            tags: Lista de tags opcionais
        
        Returns:
            Dict com dados do pagamento criado
        """
        payment_data = {
            "id": payment_id,
            "taxType": tax_type,
            "paymentDate": payment_date
        }
        
        if city:
            payment_data["city"] = city
        if state_abbreviation:
            payment_data["stateAbbreviation"] = state_abbreviation
        
        # Adicionar campos específicos do imposto
        if fields:
            payment_data.update(fields)
        
        if tags:
            payment_data["tags"] = tags
        
        return self._iniciar_pagamento_generico(workspace_id, "taxes_by_fields_payments", payment_data)
    
    def efetivar_tax_by_fields_payment(
        self,
        workspace_id: str,
        payment_id: str,
        debit_account: Dict[str, Any],
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento de imposto por campos"""
        efetivacao_data = {
            "debitAccount": debit_account,
            "status": status
        }
        
        return self._efetivar_pagamento_generico(workspace_id, "taxes_by_fields_payments", payment_id, efetivacao_data)
    
    def consultar_tax_by_fields_payment(self, workspace_id: str, payment_id: str) -> Dict[str, Any]:
        """Consulta pagamento de imposto por campos por ID"""
        return self._consultar_pagamento_generico(workspace_id, "taxes_by_fields_payments", payment_id)
    
    def listar_tax_by_fields_payments(
        self,
        workspace_id: str,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Lista pagamentos de impostos por campos paginados"""
        return self._listar_pagamentos_generico(workspace_id, "taxes_by_fields_payments", initial_date, final_date, status, limit, offset)
