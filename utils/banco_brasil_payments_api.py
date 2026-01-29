"""
Cliente Python para API de Pagamentos em Lote do Banco do Brasil.

Baseado na documentação oficial:
- Portal: https://developers.bb.com.br
- API: Pagamentos em Lote API
- Autenticação: OAuth 2.0 Client Credentials
- Documentação: https://apoio.developers.bb.com.br/sandbox/spec/61bc753bd9b75d00121497a1
"""
import requests
import base64
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import os
import logging
import tempfile
import subprocess
import json
import urllib3
from pathlib import Path

# ✅ Suprimir aviso SSL para ambiente sandbox (certificado auto-assinado)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

# ✅ Carregar .env se disponível (usando python-dotenv se instalado, senão função manual)
def _load_env_file():
    """Carrega variáveis de ambiente do arquivo .env"""
    try:
        from dotenv import load_dotenv
        try:
            load_dotenv()
            return
        except (PermissionError, OSError) as e:
            logger.warning(f"⚠️ Não foi possível carregar .env (erro de permissão): {e}. Continuando sem .env.")
            return
        except Exception as e:
            logger.debug(f"⚠️ Erro ao carregar .env com dotenv: {e}. Tentando método manual.")
    except ImportError:
        pass
    
    from pathlib import Path
    possible_paths = [
        Path('.env'),
        Path(__file__).parent.parent / '.env',
        Path(os.getcwd()) / '.env',
    ]
    
    for env_path in possible_paths:
        if env_path and env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            if key.strip() not in os.environ:
                                os.environ[key.strip()] = value.strip().strip('"').strip("'")
                logger.debug(f"✅ Variáveis de ambiente carregadas do .env: {env_path.absolute()}")
                return
            except (PermissionError, OSError) as e:
                logger.warning(f"⚠️ Não foi possível carregar .env de {env_path} (erro de permissão): {e}. Continuando sem .env.")
                continue
            except Exception as e:
                logger.debug(f"⚠️ Erro ao carregar .env de {env_path}: {e}")
                continue

try:
    _load_env_file()
except Exception as e:
    logger.warning(f"⚠️ Erro ao carregar .env (não crítico): {e}. Continuando sem .env.")


@dataclass
class BancoBrasilPaymentsConfig:
    """Configuração da API de Pagamentos em Lote do Banco do Brasil"""
    client_id: str = None
    client_secret: str = None
    gw_dev_app_key: str = None
    base_url: str = None
    token_url: str = None
    environment: str = "sandbox"  # sandbox ou production
    # Certificados para mTLS (mutual TLS) - opcional para sandbox, obrigatório para produção
    cert_file: str = None
    key_file: str = None
    cert_path: str = None
    
    def __post_init__(self):
        """Carrega valores do .env se não fornecidos"""
        # ✅ IMPORTANTE: API de Pagamentos tem credenciais SEPARADAS da API de Extratos
        # Cada API precisa de suas próprias credenciais (não há fallback)
        if self.client_id is None:
            self.client_id = os.getenv("BB_PAYMENTS_CLIENT_ID", "")
        if self.client_secret is None:
            self.client_secret = os.getenv("BB_PAYMENTS_CLIENT_SECRET", "")
        if self.gw_dev_app_key is None:
            self.gw_dev_app_key = os.getenv("BB_PAYMENTS_DEV_APP_KEY", "")
        
        # ✅ IMPORTANTE: API de Pagamentos tem sua própria variável de ambiente
        # Priorizar BB_PAYMENTS_ENVIRONMENT, depois BB_ENVIRONMENT como fallback
        env_from_file = os.getenv("BB_PAYMENTS_ENVIRONMENT", "").strip().lower()
        if not env_from_file:
            # Fallback para variável genérica (usada pela API de Extratos)
            env_from_file = os.getenv("BB_ENVIRONMENT", "").strip().lower()
        
        if env_from_file:
            # ⚠️ IMPORTANTE: Se estiver como "production", usar produção
            # Caso contrário, SEMPRE usar sandbox (homologação)
            if env_from_file == "production":
                self.environment = "production"
            else:
                self.environment = "sandbox"  # Qualquer outro valor = sandbox
        elif self.environment is None:
            self.environment = "sandbox"  # Padrão: sandbox
        
        # Log para debug (sempre logar)
        env_used = os.getenv("BB_PAYMENTS_ENVIRONMENT") or os.getenv("BB_ENVIRONMENT") or "não configurado"
        logger.info(f"🔍 Ambiente BB Pagamentos: {self.environment} (BB_PAYMENTS_ENVIRONMENT={env_used})")
        
        # URLs por ambiente (conforme documentação BB)
        if self.base_url is None:
            if self.environment == "production":
                self.base_url = os.getenv("BB_PAYMENTS_BASE_URL", "https://api.bb.com.br/pagamentos-lote/v1")
            else:
                # ✅ Sandbox - URL conforme documentação oficial
                # Documentação mostra: https://homologa-api-ip.bb.com.br:7144/pagamentos-lote/v1
                # Mas também pode usar: https://api.sandbox.bb.com.br/pagamentos-lote/v1
                # Tentar primeiro a URL da documentação, depois fallback
                self.base_url = os.getenv("BB_PAYMENTS_BASE_URL", "https://homologa-api-ip.bb.com.br:7144/pagamentos-lote/v1")
        
        if self.token_url is None:
            if self.environment == "production":
                self.token_url = os.getenv("BB_PAYMENTS_TOKEN_URL", "https://oauth.bb.com.br/oauth/token")
            else:
                # ✅ URL conforme documentação da API de Pagamentos em Lote
                # A documentação da API mostra: https://oauth.sandbox.bb.com.br/oauth/token
                # Mas a documentação OAuth 2.0 geral mostra: https://oauth.hm.bb.com.br/oauth/token
                # Tentar primeiro a URL da documentação da API específica
                self.token_url = os.getenv("BB_PAYMENTS_TOKEN_URL", "https://oauth.sandbox.bb.com.br/oauth/token")
        
        # Log para debug (sempre logar - informações importantes)
        logger.info(f"🔍 BB Pagamentos - Token URL: {self.token_url}, Base URL: {self.base_url}")
        
        # Carregar certificados do .env se não fornecidos
        if self.cert_file is None:
            self.cert_file = os.getenv("BB_CERT_FILE")
        if self.key_file is None:
            self.key_file = os.getenv("BB_KEY_FILE")
        if self.cert_path is None:
            self.cert_path = os.getenv("BB_CERT_PATH")

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
                label="BB_CERT_FILE",
            )
        if key_basename:
            self.key_file = _resolver_caminho_certificado(
                self.key_file,
                candidatos=[secure_dir / key_basename],
                label="BB_KEY_FILE",
            )
        if cert_path_basename:
            self.cert_path = _resolver_caminho_certificado(
                self.cert_path,
                candidatos=[secure_dir / cert_path_basename],
                label="BB_CERT_PATH",
            )
        
        # Validar credenciais obrigatórias
        if not self.client_id or not self.client_secret or not self.gw_dev_app_key:
            logger.warning(
                "⚠️ Client ID, Client Secret ou gw-dev-app-key não configurados para Pagamentos. "
                "Configure BB_PAYMENTS_CLIENT_ID, BB_PAYMENTS_CLIENT_SECRET, BB_PAYMENTS_DEV_APP_KEY no .env"
            )


class BancoBrasilPaymentsAPI:
    """Cliente Python para API de Pagamentos em Lote do Banco do Brasil"""
    
    def __init__(self, config: BancoBrasilPaymentsConfig, debug: bool = False):
        self.config = config
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self.debug = debug
        self._temp_cert_file: Optional[str] = None
        self._mtls_cert = None
        self._setup_mtls()
    
    def __del__(self):
        """Limpa arquivo temporário se foi criado a partir de .pfx"""
        if self._temp_cert_file and os.path.exists(self._temp_cert_file):
            try:
                os.unlink(self._temp_cert_file)
            except:
                pass
    
    def _extrair_pfx_para_pem(self, pfx_path: str, senha: str = "senha001") -> Optional[str]:
        """
        Extrai certificado e chave privada de um arquivo .pfx para .pem temporário.
        
        ✅ Igual ao Banco do Brasil Extratos - suporta .pfx automaticamente.
        
        Args:
            pfx_path: Caminho do arquivo .pfx
            senha: Senha do arquivo .pfx
        
        Returns:
            Caminho do arquivo .pem temporário ou None se falhar
        """
        try:
            # Criar arquivo temporário
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pem', prefix='bb_payments_')
            os.close(temp_fd)
            
            # Extrair certificado e chave privada do .pfx
            result = subprocess.run(
                ['openssl', 'pkcs12', '-in', pfx_path, '-nodes', '-out', temp_path,
                 '-passin', f'pass:{senha}', '-legacy'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Verificar se o arquivo tem chave privada
                with open(temp_path, 'r') as f:
                    content = f.read()
                    if 'BEGIN PRIVATE KEY' in content or 'BEGIN RSA PRIVATE KEY' in content or 'BEGIN EC PRIVATE KEY' in content:
                        self._temp_cert_file = temp_path
                        logger.info(f"✅ Certificado .pfx convertido automaticamente para uso em mTLS - Pagamentos: {pfx_path}")
                        return temp_path
                    else:
                        logger.error("❌ Arquivo .pfx não contém chave privada")
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
        """Configura certificados mTLS se disponíveis"""
        # ✅ NOVO: Se for arquivo .pfx, extrair automaticamente
        if self.config.cert_path and os.path.exists(self.config.cert_path):
            cert_path = self.config.cert_path
            
            # Se for .pfx, extrair automaticamente
            if cert_path.lower().endswith('.pfx') or cert_path.lower().endswith('.p12'):
                senha_pfx = os.getenv("BB_PAYMENTS_PFX_PASSWORD", os.getenv("BB_PFX_PASSWORD", "senha001"))
                pem_path = self._extrair_pfx_para_pem(cert_path, senha_pfx)
                if pem_path:
                    self._mtls_cert = pem_path
                    if self.debug:
                        logger.debug(f"✅ Certificado mTLS preparado (extraído de .pfx): {cert_path}")
                else:
                    logger.warning(f"⚠️ Não foi possível extrair certificado de .pfx: {cert_path}")
                    self._mtls_cert = None
            else:
                # Certificado já em formato PEM
                self._mtls_cert = cert_path
                if self.debug:
                    logger.debug("✅ Certificado mTLS preparado (cert_path)")
        elif self.config.cert_file and self.config.key_file:
            if os.path.exists(self.config.cert_file) and os.path.exists(self.config.key_file):
                self._mtls_cert = (self.config.cert_file, self.config.key_file)
                if self.debug:
                    logger.debug("✅ Certificado mTLS preparado (cert + key separados)")
            else:
                logger.warning(f"⚠️ Certificado ou chave não encontrados: cert={self.config.cert_file}, key={self.config.key_file}")
                self._mtls_cert = None
        else:
            self._mtls_cert = None
    
    def _obter_token(self) -> str:
        """
        Obtém token de acesso OAuth 2.0 (Client Credentials).
        
        Returns:
            Token de acesso
        """
        import time
        
        # Se token ainda válido, retornar
        if self._access_token and self._token_expires_at:
            if time.time() < self._token_expires_at - 60:  # Renovar 1 minuto antes
                return self._access_token
        
        # Validar credenciais
        if not self.config.client_id or not self.config.client_secret:
            raise ValueError("Client ID e Client Secret são obrigatórios")
        
        # Obter novo token
        # ✅ Usar BB_PAYMENTS_BASIC_AUTH (credenciais específicas de pagamentos)
        basic_auth = os.getenv("BB_PAYMENTS_BASIC_AUTH")
        if basic_auth:
            encoded_credentials = basic_auth
            if self.debug:
                logger.debug("🔑 Usando BB_PAYMENTS_BASIC_AUTH pré-codificado diretamente")
        else:
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            if self.debug:
                logger.debug(f"🔑 Codificando client_id:client_secret")
        
        # ⚠️ IMPORTANTE: gw-dev-app-key NÃO é enviado na requisição OAuth
        # Ele é usado apenas nas requisições subsequentes da API
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "grant_type": "client_credentials",
            # ✅ Scopes conforme documentação da API de Pagamentos em Lote
            # Usar scopes específicos ou scope genérico (depende da autorização)
            # Se autorizou todos os scopes, pode usar scope genérico ou listar os principais
            "scope": "pagamentos-lote.lotes-requisicao pagamentos-lote.lotes-info pagamentos-lote.boletos-requisicao pagamentos-lote.boletos-info pagamentos-lote.transferencias-requisicao pagamentos-lote.transferencias-info pagamentos-lote.transferencias-pix-requisicao pagamentos-lote.transferencias-pix-info pagamentos-lote.pix-info pagamentos-lote.guias-codigo-barras-requisicao pagamentos-lote.guias-codigo-barras-info pagamentos-lote.pagamentos-guias-sem-codigo-barras-requisicao pagamentos-lote.pagamentos-guias-sem-codigo-barras-info pagamentos-lote.pagamentos-info pagamentos-lote.pagamentos-codigo-barras-info pagamentos-lote.cancelar-requisicao pagamentos-lote.devolvidos-info pagamentos-lote.lancamentos-info"
            # Nota: Se der erro, tente scope genérico: "pagamentos-lote" (sem sufixos)
        }
        
        # Logs detalhados (sempre, não apenas em debug)
        logger.info(f"🔑 Tentando obter token OAuth de: {self.config.token_url}")
        logger.info(f"🔑 Headers: Content-Type={headers.get('Content-Type')}, Authorization={'Basic ***' if headers.get('Authorization') else 'NÃO CONFIGURADO'}")
        logger.info(f"🔑 Data: grant_type={data.get('grant_type')}, scope={data.get('scope')}")
        logger.info(f"🔑 Client ID (primeiros 10 chars): {self.config.client_id[:10] if self.config.client_id else 'NÃO CONFIGURADO'}...")
        logger.info(f"🔑 Client Secret configurado: {'SIM' if self.config.client_secret else 'NÃO'}")
        logger.info(f"🔑 gw-dev-app-key configurado: {'SIM' if self.config.gw_dev_app_key else 'NÃO'}")
        
        if self.debug:
            logger.debug(f"🔑 Headers completos: {headers}")
            logger.debug(f"🔑 Data completo: {data}")
        
        try:
            # Requisição de token OAuth NÃO usa certificado mTLS
            response = requests.post(
                self.config.token_url,
                headers=headers,
                data=data,
                timeout=30,
                verify=True
            )
            
            # ✅ Status 200 (OK) e 201 (Created) são válidos para criação de token OAuth
            if response.status_code not in [200, 201]:
                logger.error(f"❌ Erro ao obter token OAuth: {response.status_code}")
                logger.error(f"❌ URL: {self.config.token_url}")
                logger.error(f"❌ Headers da resposta: {dict(response.headers)}")
                
                # Tentar obter resposta como JSON primeiro
                error_data = None
                response_text = None
                try:
                    parsed_response = response.json()
                    # Verificar se é dict ou string
                    if isinstance(parsed_response, dict):
                        error_data = parsed_response
                        logger.error(f"❌ Resposta JSON (dict): {error_data}")
                    else:
                        # Se for string ou outro tipo, tratar como texto
                        response_text = str(parsed_response)
                        logger.error(f"❌ Resposta JSON (string): {response_text}")
                except (ValueError, requests.exceptions.JSONDecodeError):
                    # Se não for JSON, mostrar como texto
                    response_text = response.text
                    logger.error(f"❌ Resposta (texto): {response_text}")
                
                # Se response_text ainda não foi definido, obter do response
                if response_text is None:
                    response_text = response.text if hasattr(response, 'text') else str(response.content)
                
                # Mensagens de erro mais específicas (se conseguiu parsear JSON como dict)
                if error_data and isinstance(error_data, dict):
                    if error_data.get("error") == "invalid_client":
                        logger.error("❌ 'Software não cadastrado' - Verifique:")
                        logger.error(f"   1. Ambiente configurado: {self.config.environment}")
                        logger.error(f"   2. Token URL: {self.config.token_url}")
                        logger.error(f"   3. Se BB_PAYMENTS_CLIENT_ID e BB_PAYMENTS_CLIENT_SECRET estão corretos")
                        logger.error(f"   4. Se a aplicação está cadastrada no portal do BB")
                        logger.error(f"   5. Se o scope 'pagamento-lote' está autorizado")
                        logger.error(f"   6. Se está usando credenciais de SANDBOX (não produção)")
                    elif error_data.get("error") == "invalid_scope":
                        logger.error("❌ 'Cliente não possui autorização para nenhum dos escopos solicitados' - Verifique:")
                        logger.error(f"   1. Scope solicitado: {data.get('scope', 'não informado')}")
                        logger.error(f"   2. Se a aplicação está cadastrada no portal do BB")
                        logger.error(f"   3. Se o scope 'pagamento-lote' está AUTORIZADO para esta aplicação")
                        logger.error(f"   4. Acesse: https://developers.bb.com.br/ e verifique os scopes autorizados")
                        logger.error(f"   5. Verifique se está usando a aplicação CORRETA (não a de Extratos)")
                        logger.error(f"   6. O scope pode ter nome diferente - verifique na documentação da API")
                else:
                    # Mensagens genéricas quando não conseguiu parsear JSON como dict
                    logger.error("❌ Erro genérico 'Bad Request' - Verifique:")
                    logger.error(f"   1. Token URL está correto: {self.config.token_url}")
                    logger.error(f"   2. Client ID e Secret estão corretos e configurados")
                    logger.error(f"   3. A aplicação está cadastrada no portal do BB para esta API")
                    logger.error(f"   4. O scope 'pagamento-lote' está autorizado para esta aplicação")
                    logger.error(f"   5. As credenciais são da aplicação CORRETA (não a de Extratos)")
                    logger.error(f"   6. Verifique se está usando ambiente SANDBOX (não produção)")
                    logger.error(f"   7. Resposta recebida: {response_text}")
                
                response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            self._token_expires_at = time.time() + expires_in
            
            if self.debug:
                logger.debug("✅ Token OAuth obtido com sucesso")
            
            return self._access_token
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter token OAuth: {e}", exc_info=True)
            raise
    
    def _fazer_requisicao(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                         json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Faz requisição à API de Pagamentos em Lote.
        
        Args:
            method: Método HTTP (GET, POST, PUT, DELETE)
            endpoint: Endpoint da API (sem base_url)
            data: Dados para enviar (form-urlencoded)
            json_data: Dados JSON para enviar
        
        Returns:
            Resposta da API como dict
        """
        token = self._obter_token()
        url = f"{self.config.base_url}/{endpoint.lstrip('/')}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "gw-dev-app-key": self.config.gw_dev_app_key,
            "Content-Type": "application/json" if json_data else "application/x-www-form-urlencoded"
        }
        
        if self.debug:
            logger.debug(f"📤 {method} {url}")
            if json_data:
                logger.debug(f"📤 Body JSON: {json.dumps(json_data, indent=2)}")
        
        try:
            # Usar certificado mTLS se configurado
            cert = self._mtls_cert if self._mtls_cert else None
            
            # ✅ Para ambiente sandbox, o servidor pode usar certificado auto-assinado
            # Desabilitar verificação SSL apenas em sandbox (não em produção!)
            verify_ssl = self.config.environment != "sandbox"
            
            if self.debug:
                logger.debug(f"🔐 SSL Verification: {verify_ssl} (ambiente: {self.config.environment})")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, cert=cert, timeout=30, verify=verify_ssl)
            elif method.upper() == "POST":
                if json_data:
                    response = requests.post(url, headers=headers, json=json_data, cert=cert, timeout=30, verify=verify_ssl)
                else:
                    response = requests.post(url, headers=headers, data=data, cert=cert, timeout=30, verify=verify_ssl)
            elif method.upper() == "PUT":
                if json_data:
                    response = requests.put(url, headers=headers, json=json_data, cert=cert, timeout=30, verify=verify_ssl)
                else:
                    response = requests.put(url, headers=headers, data=data, cert=cert, timeout=30, verify=verify_ssl)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, cert=cert, timeout=30, verify=verify_ssl)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
            
            if self.debug:
                logger.debug(f"📥 Resposta: Status {response.status_code}")
                if response.text:
                    logger.debug(f"📥 Body: {response.text[:500]}")
            
            # Tentar parsear JSON
            try:
                return response.json()
            except:
                return {"_raw_response": response.text, "_status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"❌ Erro ao fazer requisição {method} {endpoint}: {e}", exc_info=True)
            raise
    
    def iniciar_pagamento_lote(
        self,
        agencia: str,
        conta: str,
        pagamentos: List[Dict[str, Any]],
        data_pagamento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia um pagamento em lote.
        
        Args:
            agencia: Agência da conta (4 dígitos)
            conta: Número da conta (sem dígito verificador)
            pagamentos: Lista de pagamentos, cada um com:
                - tipo: str - Tipo de pagamento ('BOLETO', 'PIX', 'TED', etc.)
                - codigo_barras: str - Código de barras (para boleto)
                - valor: float - Valor do pagamento
                - beneficiario: str - Nome do beneficiário (opcional)
                - vencimento: str - Data de vencimento YYYY-MM-DD (opcional)
            data_pagamento: Data do pagamento YYYY-MM-DD (opcional, padrão: hoje)
        
        Returns:
            Dict com resultado contendo:
            - id_lote: str - ID do lote criado
            - status: str - Status do lote
            - pagamentos: List[Dict] - Lista de pagamentos processados
        """
        if not data_pagamento:
            data_pagamento = datetime.now().strftime('%Y-%m-%d')
        
        # Preparar payload conforme documentação BB
        payload = {
            "agencia": agencia.zfill(4),
            "conta": conta.zfill(12),
            "dataPagamento": data_pagamento,
            "pagamentos": []
        }
        
        for pagamento in pagamentos:
            pagamento_item = {
                "tipo": pagamento.get('tipo', 'BOLETO'),
                "valor": pagamento.get('valor', 0),
            }
            
            # Adicionar campos específicos por tipo
            if pagamento.get('tipo') == 'BOLETO':
                pagamento_item["codigoBarras"] = pagamento.get('codigo_barras', '')
                if pagamento.get('vencimento'):
                    pagamento_item["vencimento"] = pagamento.get('vencimento')
            elif pagamento.get('tipo') == 'PIX':
                pagamento_item["chavePix"] = pagamento.get('chave_pix', '')
            elif pagamento.get('tipo') == 'TED':
                pagamento_item["agenciaDestino"] = pagamento.get('agencia_destino', '')
                pagamento_item["contaDestino"] = pagamento.get('conta_destino', '')
                pagamento_item["bancoDestino"] = pagamento.get('banco_destino', '001')  # BB = 001
            
            if pagamento.get('beneficiario'):
                pagamento_item["beneficiario"] = pagamento.get('beneficiario')
            
            payload["pagamentos"].append(pagamento_item)
        
        return self._fazer_requisicao("POST", "/lotes", json_data=payload)
    
    def consultar_lote(self, id_lote: str) -> Dict[str, Any]:
        """
        Consulta status de um lote de pagamentos.
        
        Args:
            id_lote: ID do lote
        
        Returns:
            Dict com informações do lote
        """
        return self._fazer_requisicao("GET", f"/lotes/{id_lote}")
    
    def listar_lotes(
        self,
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista lotes de pagamentos.
        
        Args:
            agencia: Agência (opcional)
            conta: Conta (opcional)
            data_inicio: Data inicial YYYY-MM-DD (opcional)
            data_fim: Data final YYYY-MM-DD (opcional)
        
        Returns:
            Dict com lista de lotes
        """
        params = {}
        if agencia:
            params["agencia"] = agencia.zfill(4)
        if conta:
            params["conta"] = conta.zfill(12)
        if data_inicio:
            params["dataInicio"] = data_inicio
        if data_fim:
            params["dataFim"] = data_fim
        
        endpoint = "/lotes"
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            endpoint = f"{endpoint}?{query_string}"
        
        return self._fazer_requisicao("GET", endpoint)
