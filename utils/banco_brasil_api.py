"""
Cliente Python para API de Extratos do Banco do Brasil.

Baseado na documentação oficial:
- Portal: https://developers.bb.com.br
- API: Extratos API v1.0
- Autenticação: OAuth 2.0 Client Credentials
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

# ✅ Carregar .env se disponível (usando python-dotenv se instalado, senão função manual)
def _load_env_file():
    """Carrega variáveis de ambiente do arquivo .env"""
    # Tentar usar python-dotenv primeiro (mais robusto)
    try:
        from dotenv import load_dotenv
        try:
            load_dotenv()
            return
        except (PermissionError, OSError) as e:
            # ✅ CORREÇÃO: Não falhar se houver erro de permissão
            logger.warning(f"⚠️ Não foi possível carregar .env (erro de permissão): {e}. Continuando sem .env.")
            return
        except Exception as e:
            logger.debug(f"⚠️ Erro ao carregar .env com dotenv: {e}. Tentando método manual.")
    except ImportError:
        pass  # Continuar com método manual
    
    # Método manual: tentar múltiplos caminhos
    from pathlib import Path
    possible_paths = [
        Path('.env'),  # Caminho atual
        Path(__file__).parent.parent / '.env',  # Relativo ao utils/
        Path(os.getcwd()) / '.env',  # Diretório de trabalho atual
    ]
    
    for env_path in possible_paths:
        if env_path and env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # Não sobrescrever se já existe (prioridade para variáveis do sistema)
                            if key.strip() not in os.environ:
                                os.environ[key.strip()] = value.strip().strip('"').strip("'")
                logger.debug(f"✅ Variáveis de ambiente carregadas do .env: {env_path.absolute()}")
                return
            except (PermissionError, OSError) as e:
                # ✅ CORREÇÃO: Não falhar se houver erro de permissão
                logger.warning(f"⚠️ Não foi possível carregar .env de {env_path} (erro de permissão): {e}. Continuando sem .env.")
                continue
            except Exception as e:
                logger.debug(f"⚠️ Erro ao carregar .env de {env_path}: {e}")
                continue

# Carregar .env na importação do módulo (não falhar se houver erro)
try:
    _load_env_file()
except Exception as e:
    # ✅ CORREÇÃO: Não quebrar a importação do módulo se houver erro ao carregar .env
    logger.warning(f"⚠️ Erro ao carregar .env (não crítico): {e}. Continuando sem .env.")


@dataclass
class BancoBrasilConfig:
    """Configuração da API Banco do Brasil"""
    client_id: str = None
    client_secret: str = None
    gw_dev_app_key: str = None
    base_url: str = None
    token_url: str = None
    environment: str = "sandbox"  # sandbox ou production
    # Certificados para mTLS (mutual TLS) - opcional para API de Extratos
    cert_file: str = None  # Caminho para o certificado .pem ou .crt
    key_file: str = None   # Caminho para a chave privada .key
    cert_path: str = None  # Caminho para certificado combinado (cert + key)
    
    def __post_init__(self):
        """Carrega valores do .env se não fornecidos"""
        if self.client_id is None:
            self.client_id = os.getenv("BB_CLIENT_ID", "")
        if self.client_secret is None:
            self.client_secret = os.getenv("BB_CLIENT_SECRET", "")
        if self.gw_dev_app_key is None:
            self.gw_dev_app_key = os.getenv("BB_DEV_APP_KEY", "")
        # ✅ CORREÇÃO: Sempre ler do .env (o valor padrão "sandbox" é apenas para quando não há .env)
        env_from_file = os.getenv("BB_ENVIRONMENT", "").strip().lower()
        if env_from_file:
            self.environment = env_from_file
        elif self.environment is None:
            self.environment = "sandbox"
        
        # URLs por ambiente (conforme especificação OpenAPI oficial)
        # Servers disponíveis:
        # 1. https://api.sandbox.bb.com.br/extratos/v1 - Homologação (pode retornar HTML - não usar)
        # 2. https://api.hm.bb.com.br/extratos/v1 - Homologação 2 (sem mTLS) ✅ RECOMENDADO
        # 3. https://api-extratos.hm.bb.com.br/extratos/v1 - Homologação 3 (com mTLS)
        # 4. https://api-extratos.bb.com.br/extratos/v1 - Produção (com mTLS)
        if self.base_url is None:
            if self.environment == "production":
                # Produção: endpoint pode requerer mTLS
                # Se certificado configurado, usar endpoint com mTLS
                # Se não, tentar sem certificado (algumas APIs podem não requerer)
                if self.cert_path or (self.cert_file and self.key_file):
                    # Com certificado mTLS
                    self.base_url = os.getenv("BB_BASE_URL", "https://api-extratos.bb.com.br/extratos/v1")
                else:
                    # Sem certificado - tentar mesmo endpoint (pode funcionar se API não requerer mTLS)
                    # ⚠️ Se der erro, configure o certificado
                    self.base_url = os.getenv("BB_BASE_URL", "https://api-extratos.bb.com.br/extratos/v1")
                    logger.warning("⚠️ Produção sem certificado mTLS configurado. Se a API requerer mTLS, configure BB_CERT_PATH ou BB_CERT_FILE/BB_KEY_FILE")
            else:
                # Homologação: escolher endpoint baseado em mTLS
                # Se certificado configurado, usar endpoint com mTLS
                if self.cert_path or (self.cert_file and self.key_file):
                    # Homologação 3 (com mTLS)
                    self.base_url = os.getenv("BB_BASE_URL", "https://api-extratos.hm.bb.com.br/extratos/v1")
                else:
                    # Sem mTLS - usar api.hm.bb.com.br (api.sandbox.bb.com.br retorna HTML)
                    self.base_url = os.getenv("BB_BASE_URL", "https://api.hm.bb.com.br/extratos/v1")
        
        if self.token_url is None:
            if self.environment == "production":
                self.token_url = os.getenv("BB_TOKEN_URL", "https://oauth.bb.com.br/oauth/token")
            else:
                # ⚠️ IMPORTANTE: Verificar se há token URL específico no .env
                # O BB pode usar diferentes URLs de homologação
                self.token_url = os.getenv("BB_TOKEN_URL", "https://oauth.hm.bb.com.br/oauth/token")
        
        # Carregar certificados do .env se não fornecidos (opcional para API de Extratos)
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
                "Client ID, Client Secret ou gw-dev-app-key não configurados. "
                "Configure no arquivo .env ou passe como parâmetro."
            )
        
        # Aviso sobre certificados mTLS (opcional para API de Extratos)
        if self.cert_file or self.cert_path:
            logger.debug("🔐 Certificados mTLS configurados (opcional para API de Extratos)")


class BancoBrasilExtratoAPI:
    """Cliente Python para API de Extratos do Banco do Brasil"""
    
    def __init__(self, config: BancoBrasilConfig, debug: bool = False):
        self.config = config
        # ✅ IMPORTANTE: Criar sessão SEM certificado configurado
        # O certificado mTLS será passado apenas nas requisições específicas que precisam
        self.session = requests.Session()
        # Garantir que a sessão não tenha certificado configurado
        if hasattr(self.session, 'cert'):
            self.session.cert = None
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None
        self.debug = debug
        self._temp_cert_file: Optional[str] = None  # Arquivo temporário criado a partir de .pfx
        
        # ✅ IMPORTANTE: NÃO configurar certificado mTLS na sessão global
        # O certificado mTLS deve ser usado APENAS nas requisições à API de extratos
        # A requisição de token OAuth NÃO precisa de mTLS
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
        
        Args:
            pfx_path: Caminho do arquivo .pfx
            senha: Senha do arquivo .pfx
        
        Returns:
            Caminho do arquivo .pem temporário ou None se erro
        """
        try:
            # Criar arquivo temporário
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pem', prefix='bb_cert_')
            os.close(temp_fd)  # Fechar o file descriptor, vamos usar o caminho
            
            # Extrair certificado e chave privada do .pfx
            cmd = [
                'openssl', 'pkcs12',
                '-in', pfx_path,
                '-nodes',  # Não criptografar a chave privada
                '-out', temp_path,
                '-passin', f'pass:{senha}',
                '-legacy'  # Suportar .pfx antigos
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Verificar se o arquivo tem chave privada
                with open(temp_path, 'r') as f:
                    content = f.read()
                    if 'BEGIN PRIVATE KEY' in content or 'BEGIN RSA PRIVATE KEY' in content or 'BEGIN EC PRIVATE KEY' in content:
                        if self.debug:
                            logger.debug(f"✅ Certificado .pfx extraído com sucesso para: {temp_path}")
                        return temp_path
                    else:
                        logger.warning(f"⚠️ Arquivo .pfx extraído mas não contém chave privada")
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
        """Prepara certificados mTLS para uso apenas nas requisições à API de extratos (não na sessão global)"""
        if self.config.cert_path:
            cert_path = self.config.cert_path
            
            # ✅ NOVO: Se for arquivo .pfx, extrair automaticamente
            if cert_path.lower().endswith('.pfx') or cert_path.lower().endswith('.p12'):
                if os.path.exists(cert_path):
                    # Tentar senha do .env ou padrão
                    senha_pfx = os.getenv("BB_PFX_PASSWORD", "senha001")
                    temp_pem = self._extrair_pfx_para_pem(cert_path, senha_pfx)
                    if temp_pem:
                        self._mtls_cert = temp_pem
                        self._temp_cert_file = temp_pem  # Guardar para limpar depois
                        if self.debug:
                            logger.debug("✅ Certificado .pfx convertido automaticamente para uso em mTLS")
                    else:
                        logger.error(f"❌ Não foi possível extrair certificado do .pfx: {cert_path}")
                        logger.error(f"💡 Verifique se a senha está correta. Configure BB_PFX_PASSWORD no .env se necessário.")
                        self._mtls_cert = None
                else:
                    logger.warning(f"⚠️ Arquivo .pfx não encontrado: {cert_path}")
                    self._mtls_cert = None
            elif os.path.exists(cert_path):
                # Arquivo .pem ou outro formato
                # ✅ VALIDAÇÃO CRÍTICA: Verificar se o arquivo tem chave privada
                try:
                    with open(cert_path, 'r') as f:
                        content = f.read()
                        if 'BEGIN PRIVATE KEY' in content or 'BEGIN RSA PRIVATE KEY' in content or 'BEGIN EC PRIVATE KEY' in content:
                            # Tem chave privada - OK para usar
                            self._mtls_cert = cert_path
                            if self.debug:
                                logger.debug("✅ Certificado mTLS preparado (arquivo combinado com chave privada) - será usado apenas nas requisições à API")
                        else:
                            # Não tem chave privada - apenas cadeia pública (não serve para mTLS)
                            logger.warning(f"⚠️ Arquivo {cert_path} não contém chave privada (apenas certificados públicos). Não pode ser usado para mTLS.")
                            logger.warning(f"💡 Dica: Configure BB_CERT_PATH apontando para o arquivo .pfx diretamente - o código extrai automaticamente!")
                            self._mtls_cert = None
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao validar certificado {cert_path}: {e}")
                    self._mtls_cert = None
            else:
                logger.warning(f"⚠️ Certificado não encontrado: {cert_path}")
                self._mtls_cert = None
        elif self.config.cert_file and self.config.key_file:
            # Certificado e chave separados
            if os.path.exists(self.config.cert_file) and os.path.exists(self.config.key_file):
                self._mtls_cert = (self.config.cert_file, self.config.key_file)
                if self.debug:
                    logger.debug("✅ Certificado mTLS preparado (cert + key separados) - será usado apenas nas requisições à API")
            else:
                logger.warning(f"⚠️ Certificado ou chave não encontrados: cert={self.config.cert_file}, key={self.config.key_file}")
                self._mtls_cert = None
        else:
            # Nenhum certificado configurado
            self._mtls_cert = None
    
    def _obter_token(self) -> str:
        """
        Obtém token de acesso OAuth 2.0 (Client Credentials).
        
        Returns:
            Token de acesso
        """
        # Se token ainda válido, retornar
        if self._access_token and self._token_expires_at:
            import time
            if time.time() < self._token_expires_at - 60:  # Renovar 1 minuto antes
                return self._access_token
        
        # Validar credenciais
        if not self.config.client_id or not self.config.client_secret:
            raise ValueError("Client ID e Client Secret são obrigatórios")
        
        # Obter novo token
        # ✅ Verificar se há um "basic" pré-codificado no .env (BB_BASIC_AUTH)
        basic_auth = os.getenv("BB_BASIC_AUTH")
        if basic_auth:
            # Usar basic auth pré-codificado diretamente (sem codificar novamente)
            encoded_credentials = basic_auth
            if self.debug:
                logger.debug("🔑 Usando BB_BASIC_AUTH pré-codificado diretamente")
        else:
            # Codificar client_id:client_secret normalmente
            # ⚠️ IMPORTANTE: Se client_id e client_secret são JWT tokens, usar diretamente
            credentials = f"{self.config.client_id}:{self.config.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            if self.debug:
                logger.debug(f"🔑 Codificando client_id:client_secret (JWT tokens podem ser usados diretamente)")
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": "extrato-info"  # ⚠️ IMPORTANTE: Scope case-sensitive, separado por espaço se múltiplos
        }
        
        # ⚠️ IMPORTANTE: Verificar se scope está correto conforme documentação
        # O scope deve estar na chave "securitySchemes" dentro de "scopes" do OpenAPI
        # Para API de Extratos: scope = "extrato-info"
        
        if self.debug:
            logger.debug(f"🔑 Tentando obter token OAuth de: {self.config.token_url}")
            logger.debug(f"🔑 Client ID (primeiros 20 chars): {self.config.client_id[:20]}...")
            logger.debug(f"🔑 Client Secret (primeiros 20 chars): {self.config.client_secret[:20]}...")
        
        try:
            # ✅ IMPORTANTE: Requisição de token OAuth NÃO usa certificado mTLS
            # Usar requests.post diretamente (sem sessão) para garantir que não há certificado
            # NÃO usar self.session pois pode ter certificado configurado
            response = requests.post(
                self.config.token_url, 
                headers=headers, 
                data=data, 
                timeout=30,
                verify=True  # Verificar certificado do servidor (SSL normal), mas NÃO usar certificado cliente (mTLS)
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Erro ao obter token OAuth: {response.status_code}")
                logger.error(f"❌ Resposta: {response.text}")
                logger.error(f"❌ Token URL: {self.config.token_url}")
                logger.error(f"❌ Ambiente: {self.config.environment}")
                logger.error(f"❌ Headers enviados: {dict(headers)}")
                logger.error(f"❌ Data enviada: {data}")
                
                # Mensagem de erro mais clara
                if response.status_code == 401:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get('error_description', error_data.get('error', 'Credenciais inválidas'))
                    logger.error(f"❌ ERRO 401: {error_msg}")
                    logger.error(f"💡 Conforme documentação do BB, verifique:")
                    logger.error(f"   1. BB_CLIENT_ID e BB_CLIENT_SECRET estão corretos no .env")
                    logger.error(f"   2. BB_BASIC_AUTH está correto (se estiver usando)")
                    logger.error(f"   3. O ambiente está correto (sandbox vs production)")
                    logger.error(f"   4. As credenciais não expiraram")
                    logger.error(f"   5. O formato do Basic Auth está correto: base64(client_id:client_secret)")
                    logger.error(f"   6. O scope 'extrato-info' está autorizado para sua aplicação no portal do BB")
                
                response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data.get("access_token")
            
            if not self._access_token:
                raise ValueError("Token de acesso não retornado na resposta")
            
            # Calcular expiração (padrão: 3600 segundos se não informado)
            expires_in = token_data.get("expires_in", 3600)
            import time
            self._token_expires_at = time.time() + expires_in
            
            if self.debug:
                logger.debug(f"✅ Token OAuth obtido com sucesso (expira em {expires_in}s)")
            
            return self._access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao obter token OAuth: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"❌ Status: {e.response.status_code}")
                logger.error(f"❌ Resposta do servidor: {e.response.text}")
            raise
    
    def _formatar_data(self, data: datetime) -> int:
        """
        Formata data para DDMMAAAA (inteiro).
        
        Args:
            data: Objeto datetime
            
        Returns:
            Data formatada como inteiro (ex: 01122025)
        """
        return int(data.strftime("%d%m%Y"))
    
    def _normalizar_agencia_conta(self, valor: str) -> str:
        """
        Normaliza agência ou conta removendo zeros à esquerda.
        
        Conforme documentação OpenAPI:
        - "Omitir zeros à esquerda (Ex.: 0297 >> 297)"
        
        Args:
            valor: Número da agência ou conta (string)
        
        Returns:
            String normalizada sem zeros à esquerda
        """
        if not valor:
            return valor
        # Remove zeros à esquerda, mas mantém pelo menos um dígito
        valor_normalizado = valor.lstrip('0') or '0'
        return valor_normalizado
    
    def consultar_extrato(
        self,
        agencia: str,
        conta: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        pagina: int = 1,
        registros_por_pagina: int = 200
    ) -> Dict[str, Any]:
        """
        Consulta extrato de conta corrente.
        
        Conforme especificação OpenAPI:
        - Se data_inicio for preenchida, data_fim é obrigatória
        - Se data_fim for preenchida, data_inicio é obrigatória
        - Se nenhuma data for preenchida, retorna últimos 30 dias
        - Período máximo: 31 dias
        - Limite máximo para data inicial: 5 anos a partir da data atual
        
        Args:
            agencia: Número da agência (sem dígito verificador, ex: "1505")
            conta: Número da conta (sem dígito verificador, ex: "1348")
            data_inicio: Data inicial (opcional, padrão: últimos 30 dias)
            data_fim: Data final (opcional, obrigatório se data_inicio for informado)
            pagina: Número da página (padrão: 1, min: 1, max: 9999999)
            registros_por_pagina: Registros por página (padrão: 200, min: 50, max: 200)
        
        Returns:
            Dict com dados do extrato conforme especificação OpenAPI:
            - numeroPaginaAtual: int
            - quantidadeRegistroPaginaAtual: int
            - numeroPaginaAnterior: int
            - numeroPaginaProximo: int
            - quantidadeTotalPagina: int
            - quantidadeTotalRegistro: int
            - listaLancamento: object (com propriedades dos lançamentos)
        
        Raises:
            ValueError: Se data_inicio for informada sem data_fim ou vice-versa,
                       ou se registros_por_pagina estiver fora do range 50-200
        """
        # Validações conforme especificação OpenAPI
        if (data_inicio is not None) != (data_fim is not None):
            raise ValueError(
                "Se data_inicio for informada, data_fim é obrigatória e vice-versa. "
                "Conforme especificação OpenAPI da API de Extratos do BB."
            )
        
        # Validar registros por página (conforme spec: min 50, max 200)
        if registros_por_pagina < 50 or registros_por_pagina > 200:
            raise ValueError(
                f"quantidadeRegistroPaginaSolicitacao deve estar entre 50 e 200. "
                f"Valor informado: {registros_por_pagina}"
            )
        
        # ✅ IMPORTANTE: Normalizar agência e conta (remover zeros à esquerda)
        # Conforme documentação: "Omitir zeros à esquerda (Ex.: 0297 >> 297)"
        agencia_normalizada = self._normalizar_agencia_conta(str(agencia))
        conta_normalizada = self._normalizar_agencia_conta(str(conta))
        
        if self.debug:
            if agencia_normalizada != str(agencia) or conta_normalizada != str(conta):
                logger.debug(f"📝 Valores normalizados: agência {agencia} → {agencia_normalizada}, conta {conta} → {conta_normalizada}")
        
        token = self._obter_token()
        
        url = f"{self.config.base_url}/conta-corrente/agencia/{agencia_normalizada}/conta/{conta_normalizada}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Header de teste para homologação (conforme documentação)
        # x-br-com-bb-ipa-mciteste: Conforme descrito na massa de testes
        # Obs.: este atributo só deve ser utilizado no ambiente de homologação
        if self.config.environment != "production":
            teste_header = os.getenv("BB_TEST_HEADER")
            if teste_header:
                headers["x-br-com-bb-ipa-mciteste"] = teste_header
                if self.debug:
                    logger.debug(f"🧪 Header de teste adicionado: x-br-com-bb-ipa-mciteste={teste_header}")
        
        # Parâmetros conforme especificação OpenAPI
        params = {
            "gw-dev-app-key": self.config.gw_dev_app_key,  # Obrigatório
            "numeroPaginaSolicitacao": pagina,  # Opcional, default: 1
            "quantidadeRegistroPaginaSolicitacao": registros_por_pagina  # Opcional, default: 200
        }
        
        # Adicionar datas se fornecidas (formato DDMMAAAA como int32)
        # Conforme spec: minimum: 1010001, maximum: 31129999
        if data_inicio:
            data_inicio_formatada = self._formatar_data(data_inicio)
            params["dataInicioSolicitacao"] = data_inicio_formatada
            if self.debug:
                logger.debug(f"📅 Data início: {data_inicio.strftime('%d/%m/%Y')} → {data_inicio_formatada}")
        if data_fim:
            data_fim_formatada = self._formatar_data(data_fim)
            params["dataFimSolicitacao"] = data_fim_formatada
            if self.debug:
                logger.debug(f"📅 Data fim: {data_fim.strftime('%d/%m/%Y')} → {data_fim_formatada}")
        
        # ✅ RETRY: Tentar até 3 vezes para erros 500 (erro temporário do servidor)
        max_retries = 3
        retry_delay = 2  # segundos entre tentativas
        
        try:
            for tentativa in range(1, max_retries + 1):
                # ✅ IMPORTANTE: A API de Extratos em PRODUÇÃO requer certificado mTLS
                # Mas se não tivermos certificado válido, vamos tentar sem (pode dar erro, mas vamos tentar)
                # Se der erro SSL, o usuário precisa configurar o certificado
                
                # Garantir que a sessão não tenha certificado configurado globalmente
                # Criar uma nova sessão limpa para esta requisição
                api_session = requests.Session()
                
                # Preparar parâmetros da requisição
                request_kwargs = {
                    'headers': headers,
                    'params': params,
                    'timeout': 30
                }
                
                # ✅ CRÍTICO: Só usar certificado se realmente tivermos um válido COM CHAVE PRIVADA
                # Se não tiver certificado válido, NÃO passar parâmetro cert (requisição normal)
                if self._mtls_cert:
                    cert_path = None
                    if isinstance(self._mtls_cert, str):
                        cert_path = self._mtls_cert
                    elif isinstance(self._mtls_cert, tuple) and len(self._mtls_cert) == 2:
                        cert_path = self._mtls_cert[0]
                    
                    if cert_path and os.path.exists(cert_path):
                        # Verificar novamente se tem chave privada (validação dupla)
                        try:
                            with open(cert_path, 'r') as f:
                                content = f.read()
                                if 'BEGIN PRIVATE KEY' in content or 'BEGIN RSA PRIVATE KEY' in content or 'BEGIN EC PRIVATE KEY' in content:
                                    request_kwargs['cert'] = self._mtls_cert
                                    if self.debug:
                                        logger.debug(f"🔐 Usando certificado mTLS: {cert_path}")
                                else:
                                    if self.debug:
                                        logger.warning(f"⚠️ Certificado {cert_path} não tem chave privada - não pode ser usado para mTLS")
                                    # NÃO passar cert - tentar sem mTLS
                        except Exception as e:
                            if self.debug:
                                logger.warning(f"⚠️ Erro ao validar certificado: {e}")
                            # NÃO passar cert - tentar sem mTLS
                    else:
                        if self.debug:
                            logger.warning(f"⚠️ Certificado mTLS configurado mas arquivo não encontrado: {cert_path}")
                        # NÃO passar cert - tentar sem mTLS
                else:
                    if self.debug:
                        logger.debug("ℹ️ Sem certificado mTLS configurado - tentando requisição sem mTLS")
                
                # ✅ IMPORTANTE: Se não tivermos certificado válido, NÃO passar parâmetro cert
                # Isso garante que não tentaremos usar certificado inválido
                response = api_session.get(url, **request_kwargs)
                
                # Log da resposta para debug
                if self.debug:
                    logger.debug(f"📊 Resposta da API:")
                    logger.debug(f"   Status Code: {response.status_code}")
                    logger.debug(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
                    logger.debug(f"   Resposta (primeiros 500 chars): {response.text[:500]}")
                
                # Verificar status antes de fazer parse
                if response.status_code != 200:
                    logger.error(f"❌ Status Code: {response.status_code} (Tentativa {tentativa}/{max_retries})")
                    logger.error(f"❌ Resposta: {response.text[:500]}")
                    
                    # Tratamento específico para erro 500 com retry
                    if response.status_code == 500:
                        try:
                            error_data = response.json()
                            error_msg = "Erro Interno do Servidor"
                            if isinstance(error_data, dict) and 'erros' in error_data:
                                erros = error_data.get('erros', [])
                                if erros:
                                    primeiro_erro = erros[0]
                                    error_msg = primeiro_erro.get('mensagem', 'Erro Interno do Servidor')
                                    codigo = primeiro_erro.get('codigo', '')
                                    logger.warning(f"⚠️ Erro 500 - {error_msg} (Código: {codigo}) - Tentativa {tentativa}/{max_retries}")
                            
                            # ✅ RETRY: Se ainda temos tentativas, tentar novamente
                            if tentativa < max_retries:
                                logger.info(f"🔄 Tentando novamente em {retry_delay} segundos... (Tentativa {tentativa + 1}/{max_retries})")
                                import time
                                time.sleep(retry_delay)
                                continue  # Tentar novamente
                            else:
                                # Última tentativa falhou
                                logger.error(f"❌ Erro 500 após {max_retries} tentativas")
                                logger.error(f"💡 Possíveis causas:")
                                logger.error(f"   1. Erro temporário no servidor do BB (tente novamente mais tarde)")
                                logger.error(f"   2. Conta existe mas não tem dados configurados no Sandbox")
                                logger.error(f"   3. Problema com os dados de teste no Sandbox Admin")
                                raise RuntimeError(f"500 - {error_msg}. Erro após {max_retries} tentativas. Pode ser um erro temporário do servidor. Tente novamente mais tarde.")
                        except (ValueError, KeyError):
                            # Se não conseguir fazer parse do JSON, tentar retry mesmo assim
                            if tentativa < max_retries:
                                logger.warning(f"⚠️ Erro 500 (sem detalhes) - Tentativa {tentativa}/{max_retries}. Tentando novamente...")
                                import time
                                time.sleep(retry_delay)
                                continue
                            else:
                                raise RuntimeError(f"500 - Erro Interno do Servidor. Erro após {max_retries} tentativas. Tente novamente mais tarde.")
                
                # Tratamento específico para erro 404
                elif response.status_code == 404:
                    try:
                        error_data = response.json() if response.text.strip() else {}
                        error_msg = "Recurso não encontrado"
                        if isinstance(error_data, dict) and 'erros' in error_data:
                            erros = error_data.get('erros', [])
                            if erros:
                                primeiro_erro = erros[0]
                                error_msg = primeiro_erro.get('mensagem', 'Recurso não encontrado')
                                codigo = primeiro_erro.get('codigo', '')
                                logger.error(f"❌ Erro 404 - {error_msg} (Código: {codigo})")
                        else:
                            logger.error(f"❌ Erro 404 - Recurso não encontrado")
                        logger.error(f"💡 Possíveis causas:")
                        logger.error(f"   1. Agência/Conta não existe: {agencia_normalizada}/{conta_normalizada}")
                        logger.error(f"   2. Conta não está autorizada para esta aplicação no Portal BB")
                        logger.error(f"   3. Verifique no Portal do Desenvolvedor BB se a conta está cadastrada")
                        logger.error(f"   4. Em PRODUÇÃO: Certifique-se de que a conta está vinculada à sua aplicação")
                        logger.error(f"   5. Verifique se os valores estão corretos (sem dígito verificador, sem zeros à esquerda)")
                        logger.error(f"   6. Valores normalizados usados: agência={agencia_normalizada}, conta={conta_normalizada}")
                        raise ValueError(f"404 - {error_msg}. Agência/Conta: {agencia_normalizada}/{conta_normalizada}. Verifique se a conta existe e está autorizada para esta aplicação.")
                    except (ValueError, KeyError) as e:
                        # Se não conseguir fazer parse do JSON, lançar erro genérico
                        logger.error(f"❌ Erro 404 - Recurso não encontrado")
                        logger.error(f"💡 Possíveis causas:")
                        logger.error(f"   1. Agência/Conta não existe: {agencia_normalizada}/{conta_normalizada}")
                        logger.error(f"   2. Conta não está autorizada para esta aplicação no Portal BB")
                        logger.error(f"   3. Verifique no Portal do Desenvolvedor BB se a conta está cadastrada")
                        logger.error(f"   4. Em PRODUÇÃO: Certifique-se de que a conta está vinculada à sua aplicação")
                        logger.error(f"   5. Verifique se os valores estão corretos (sem dígito verificador, sem zeros à esquerda)")
                        raise ValueError(f"404 - Recurso não encontrado. Agência/Conta: {agencia_normalizada}/{conta_normalizada}. Verifique se a conta existe e está autorizada para esta aplicação.")
                
                # Tratamento específico para erro 403
                elif response.status_code == 403:
                        try:
                            error_data = response.json()
                            error_msg = "Acesso negado"
                            if isinstance(error_data, dict) and 'erros' in error_data:
                                erros = error_data.get('erros', [])
                                if erros:
                                    primeiro_erro = erros[0]
                                    error_msg = primeiro_erro.get('mensagem', 'Acesso negado')
                                    codigo = primeiro_erro.get('codigo', '')
                                    logger.error(f"❌ Erro 403 - {error_msg} (Código: {codigo})")
                                    logger.error(f"💡 Possíveis causas:")
                                    logger.error(f"   1. Conta/Agência não cadastrada no Sandbox do BB")
                                    logger.error(f"   2. Conta não associada à sua aplicação no portal")
                                    logger.error(f"   3. Precisa cadastrar dados de teste no Sandbox Admin")
                                    logger.error(f"   4. Verifique no portal do BB se a conta está disponível para testes")
                                    logger.error(f"   5. A conta pode não existir ou não ter lançamentos no período")
                            raise PermissionError(f"403 - {error_msg}. Verifique se a conta/agência está cadastrada no Sandbox do BB.")
                        except (ValueError, KeyError):
                            # Se não conseguir fazer parse do JSON, lançar erro genérico
                            pass
                
                response.raise_for_status()
                
                # Verificar se a resposta é JSON válido
                content_type = response.headers.get('Content-Type', '')
                if not response.text.strip():
                    raise ValueError("Resposta vazia do servidor")
                
                if 'application/json' not in content_type:
                    logger.warning(f"⚠️ Content-Type não é JSON: {content_type}")
                    logger.warning(f"⚠️ Resposta recebida: {response.text[:500]}")
                
                # Tentar fazer parse do JSON
                try:
                    return response.json()
                except ValueError as json_error:
                    logger.error(f"❌ Erro ao fazer parse do JSON: {json_error}")
                    logger.error(f"❌ Status Code: {response.status_code}")
                    logger.error(f"❌ Content-Type: {content_type}")
                    logger.error(f"❌ Resposta completa: {response.text}")
                    raise ValueError(f"Resposta não é JSON válido. Status: {response.status_code}, Content-Type: {content_type}, Resposta: {response.text[:200]}")
                
                # Se chegou aqui, sucesso - sair do loop de retry
                break
            
        except requests.exceptions.SSLError as ssl_error:
            # Erro SSL específico - geralmente relacionado a mTLS
            error_str = str(ssl_error)
            logger.error(f"❌ Erro SSL ao consultar extrato: {ssl_error}")
            
            if "bad certificate" in error_str.lower() or "SSLV3_ALERT_BAD_CERTIFICATE" in error_str:
                logger.error(f"❌ ERRO: Certificado mTLS não configurado ou inválido")
                logger.error(f"💡 A API de Extratos em PRODUÇÃO requer certificado mTLS")
                logger.error(f"💡 Solução:")
                logger.error(f"   1. Obtenha um certificado ICP-Brasil tipo A1 (e-CNPJ)")
                logger.error(f"   2. Envie a cadeia do certificado ao BB via Portal Developers (menu Certificados)")
                logger.error(f"   3. Aguarde até 3 dias úteis para aprovação")
                logger.error(f"   4. Configure no .env: BB_CERT_PATH=/caminho/para/certificado.pem")
                logger.error(f"   5. Ou use: BB_CERT_FILE e BB_KEY_FILE (separados)")
                raise RuntimeError(
                    "Certificado mTLS obrigatório em produção. "
                    "Configure BB_CERT_PATH ou BB_CERT_FILE/BB_KEY_FILE no .env após enviar o certificado ao BB."
                )
            else:
                logger.error(f"❌ Erro SSL: {ssl_error}")
                raise
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao consultar extrato: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"❌ Status Code: {e.response.status_code}")
                logger.error(f"❌ Resposta do servidor: {e.response.text[:500]}")
            raise
    
    def consultar_extrato_periodo(
        self,
        agencia: str,
        conta: str,
        data_inicio: datetime,
        data_fim: datetime
    ) -> List[Dict[str, Any]]:
        """
        Consulta extrato completo de um período (com paginação automática).
        
        Args:
            agencia: Número da agência
            conta: Número da conta
            data_inicio: Data inicial
            data_fim: Data final
        
        Returns:
            Lista com todos os lançamentos do período
        """
        todos_lancamentos = []
        pagina = 1
        registros_por_pagina = 200  # Máximo permitido
        
        while True:
            extrato = self.consultar_extrato(
                agencia=agencia,
                conta=conta,
                data_inicio=data_inicio,
                data_fim=data_fim,
                pagina=pagina,
                registros_por_pagina=registros_por_pagina
            )
            
            lancamentos = extrato.get("listaLancamento", [])
            todos_lancamentos.extend(lancamentos)
            
            # Verificar se há próxima página
            if extrato.get("numeroPaginaProximo", 0) == 0:
                break
            
            pagina = extrato["numeroPaginaProximo"]
        
        return todos_lancamentos

