"""
Cliente Python para API de Extrato do Santander Open Banking.

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
from pathlib import Path

logger = logging.getLogger(__name__)

def _resolver_caminho_certificado(
    caminho_atual: Optional[str],
    *,
    candidatos: List[Path],
    label: str,
) -> Optional[str]:
    """
    Resolve caminho de certificado/chave quando o .env aponta para um path antigo (ex.: pasta do projeto renomeada).
    Regra: se o caminho atual existe, mantém; se não existe, tenta candidatos (ex.: .secure/ do projeto atual).
    """
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
class SantanderConfig:
    """Configuração da API Santander"""
    client_id: str = None
    client_secret: str = None
    base_url: str = None
    bank_id: str = None
    token_url: str = None
    # Certificados para mTLS (mutual TLS)
    cert_file: str = None  # Caminho para o certificado .pem ou .crt
    key_file: str = None   # Caminho para a chave privada .key
    cert_path: str = None  # Caminho para certificado combinado (cert + key)
    
    def __post_init__(self):
        """Carrega valores do .env se não fornecidos"""
        if self.client_id is None:
            self.client_id = os.getenv("SANTANDER_CLIENT_ID", "")
        if self.client_secret is None:
            self.client_secret = os.getenv("SANTANDER_CLIENT_SECRET", "")
        if self.base_url is None:
            self.base_url = os.getenv("SANTANDER_BASE_URL", "https://trust-open.api.santander.com.br")
        if self.bank_id is None:
            self.bank_id = os.getenv("SANTANDER_BANK_ID", "90400888000142")
        if self.token_url is None:
            # URLs conforme documentação oficial:
            # Sandbox: https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token
            # Produção: https://trust-open.api.santander.com.br/auth/oauth/v2/token
            token_url_env = os.getenv("SANTANDER_TOKEN_URL")
            if token_url_env:
                self.token_url = token_url_env
            else:
                # Determinar URL baseado no base_url
                if "sandbox" in self.base_url.lower():
                    self.token_url = "https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token"
                else:
                    self.token_url = "https://trust-open.api.santander.com.br/auth/oauth/v2/token"
        
        # Carregar certificados do .env se não fornecidos
        if self.cert_file is None:
            self.cert_file = os.getenv("SANTANDER_CERT_FILE")
        if self.key_file is None:
            self.key_file = os.getenv("SANTANDER_KEY_FILE")
        if self.cert_path is None:
            self.cert_path = os.getenv("SANTANDER_CERT_PATH")

        # ✅ Robustez: se o .env apontar para pasta antiga, tentar .secure/ do projeto atual
        project_root = Path(__file__).resolve().parents[1]
        secure_dir = project_root / ".secure"
        # Se veio um caminho, tentar o basename dentro do .secure atual
        cert_basename = Path(self.cert_file).name if self.cert_file else "santander_extrato_cert.pem"
        key_basename = Path(self.key_file).name if self.key_file else "santander_extrato_key.pem"
        cert_path_basename = Path(self.cert_path).name if self.cert_path else None

        self.cert_file = _resolver_caminho_certificado(
            self.cert_file,
            candidatos=[
                secure_dir / cert_basename,
                secure_dir / "santander_extrato_cert.pem",
            ],
            label="SANTANDER_CERT_FILE",
        )
        self.key_file = _resolver_caminho_certificado(
            self.key_file,
            candidatos=[
                secure_dir / key_basename,
                secure_dir / "santander_extrato_key.pem",
            ],
            label="SANTANDER_KEY_FILE",
        )
        if cert_path_basename:
            self.cert_path = _resolver_caminho_certificado(
                self.cert_path,
                candidatos=[secure_dir / cert_path_basename],
                label="SANTANDER_CERT_PATH",
            )
        
        # Validar credenciais obrigatórias
        if not self.client_id or not self.client_secret:
            logger.warning(
                "Client ID e Client Secret não configurados. "
                "Configure no arquivo .env ou passe como parâmetro."
            )
        
        # Aviso sobre certificados mTLS
        if not self.cert_file and not self.cert_path:
            logger.warning("Certificados mTLS não configurados. A API do Santander EXIGE certificados mTLS.")


class SantanderExtratoAPI:
    """Cliente Python para API de Extrato do Santander Open Banking"""
    
    def __init__(self, config: SantanderConfig, debug: bool = False):
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
        
        ✅ Igual ao TED Santander e Banco do Brasil - suporta .pfx automaticamente.
        
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
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pem', prefix='santander_extrato_')
            os.close(temp_fd)
            
            # Extrair certificado e chave privada do .pfx
            result = subprocess.run(
                ['openssl', 'pkcs12',
                 '-in', pfx_path,
                 '-out', temp_path,
                 '-nodes',  # Sem criptografia na chave privada
                 '-passin', f'pass:{senha}'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(temp_path):
                # Verificar se o arquivo tem conteúdo válido
                with open(temp_path, 'r') as f:
                    content = f.read()
                    if 'BEGIN CERTIFICATE' in content and 'BEGIN PRIVATE KEY' in content:
                        logger.debug(f"✅ Certificado .pfx extraído com sucesso para: {temp_path}")
                        return temp_path
                    else:
                        logger.warning(f"⚠️ Arquivo .pem gerado não contém certificado e chave válidos")
                        os.unlink(temp_path)
                        return None
            else:
                logger.error(f"❌ Erro ao extrair .pfx: {result.stderr}")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout ao extrair certificado .pfx")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao extrair certificado .pfx: {e}", exc_info=True)
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    
    def _setup_mtls(self):
        """Configura certificados mTLS para autenticação mútua"""
        # ✅ CORRIGIDO (13/01/2026): Priorizar cert_file/key_file se ambos existirem (compatibilidade com configuração anterior)
        # Ordem de prioridade:
        # 1. cert_file + key_file (se ambos existirem) - configuração original que funcionava
        # 2. cert_path (se existir e for válido) - nova configuração com .pfx
        # 3. Nenhum certificado configurado
        
        logger.info(f"🔍 [EXTRATO] Configurando mTLS - cert_file={self.config.cert_file}, key_file={self.config.key_file}, cert_path={self.config.cert_path}")
        
        if self.config.cert_file and self.config.key_file:
            # ✅ PRIORIDADE 1: Certificado e chave separados (configuração original)
            cert_exists = os.path.exists(self.config.cert_file) if self.config.cert_file else False
            key_exists = os.path.exists(self.config.key_file) if self.config.key_file else False
            
            logger.info(f"🔍 [EXTRATO] Verificando cert_file/key_file: cert existe={cert_exists}, key existe={key_exists}")
            
            if cert_exists and key_exists:
                self.session.cert = (self.config.cert_file, self.config.key_file)
                logger.info(f"✅ Certificado mTLS configurado (cert + key separados) - Extrato: cert={self.config.cert_file}, key={self.config.key_file}")
            else:
                logger.warning(f"⚠️ Certificados não encontrados: cert={self.config.cert_file} (existe={cert_exists}), key={self.config.key_file} (existe={key_exists})")
                # Tentar fallback para cert_path se cert_file/key_file não existirem
                if self.config.cert_path:
                    logger.info(f"🔄 Tentando fallback para cert_path: {self.config.cert_path}")
                    self._setup_mtls_from_cert_path()
        elif self.config.cert_path:
            # ✅ PRIORIDADE 2: Certificado combinado ou .pfx
            logger.info(f"🔍 [EXTRATO] Usando cert_path (cert_file/key_file não configurados): {self.config.cert_path}")
            self._setup_mtls_from_cert_path()
        else:
            logger.warning(f"⚠️ [EXTRATO] Nenhum certificado configurado (cert_path, cert_file ou key_file)")
    
    def _setup_mtls_from_cert_path(self):
        """Configura mTLS a partir de cert_path (suporta .pfx e .pem combinado)"""
        cert_path = self.config.cert_path
        logger.info(f"🔍 [EXTRATO] Certificado configurado: {cert_path}")
        
        # ✅ NOVO: Se for arquivo .pfx, extrair automaticamente
        if cert_path.lower().endswith('.pfx') or cert_path.lower().endswith('.p12'):
            if os.path.exists(cert_path):
                # Tentar senha do .env ou padrão
                senha_pfx = os.getenv("SANTANDER_PFX_PASSWORD", "senha001")
                logger.info(f"🔍 [EXTRATO] Extraindo certificado .pfx: {cert_path}")
                temp_pem = self._extrair_pfx_para_pem(cert_path, senha_pfx)
                if temp_pem:
                    self.session.cert = temp_pem
                    self._temp_cert_file = temp_pem  # Guardar para limpar depois
                    logger.info(f"✅ Certificado .pfx convertido automaticamente para uso em mTLS - Extrato: {cert_path}")
                else:
                    logger.error(f"❌ Não foi possível extrair certificado do .pfx: {cert_path}")
                    logger.error(f"💡 Verifique se a senha está correta. Configure SANTANDER_PFX_PASSWORD no .env se necessário.")
            else:
                logger.warning(f"⚠️ Arquivo .pfx não encontrado: {cert_path}")
        elif os.path.exists(cert_path):
            # Certificado combinado (cert + key no mesmo arquivo)
            self.session.cert = cert_path
            logger.info(f"✅ Certificado mTLS configurado (arquivo combinado) - Extrato: {cert_path}")
        else:
            logger.warning(f"⚠️ Certificado não encontrado: {cert_path}")
    
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
            logger.debug(message)
        
    def _get_access_token(self, force_refresh: bool = False) -> str:
        """
        Obtém token de acesso (JWT) conforme documentação oficial do Santander
        
        Implementa cache do token (válido por 15 minutos conforme documentação)
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
                    
                    return self._access_token
                else:
                    continue
                        
            except requests.HTTPError as e:
                self._log(f"❌ Erro HTTP {e.response.status_code}: {e.response.text[:200]}")
                last_error = e
                if e.response.status_code in [401, 400, 403, 404]:
                    continue
                if e.response.status_code == 401:
                    raise ValueError(f"Credenciais inválidas. Verifique Client ID e Client Secret.")
                raise Exception(f"Erro ao obter token: {e.response.text}")
            except requests.Timeout:
                self._log(f"⏱️ Timeout na URL {token_url}")
                last_error = Exception(f"Timeout ao conectar em {token_url}")
                continue
            except requests.RequestException as e:
                self._log(f"❌ Erro de conexão: {type(e).__name__}: {str(e)[:100]}")
                last_error = e
                continue
        
        # Se chegou aqui, nenhuma URL funcionou
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
        """Retorna headers necessários para as requisições"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if use_token:
            try:
                token = self._get_access_token()
                headers["Authorization"] = f"Bearer {token}"
                headers["X-Application-Key"] = self.config.client_id
            except Exception as e:
                self._log(f"⚠️ Não foi possível obter token OAuth2: {e}")
        
        return headers
    
    def get_extrato(
        self,
        agencia: str = None,
        conta: str = None,
        statement_id: str = None,
        initial_date: str = None,
        final_date: str = None,
        offset: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Busca extrato bancário"""
        # Validações
        if not initial_date:
            raise ValueError("initialDate é obrigatório (formato: YYYY-MM-DD)")
        if not final_date:
            raise ValueError("finalDate é obrigatório (formato: YYYY-MM-DD)")
        
        if not statement_id:
            if not agencia or not conta:
                raise ValueError("Forneça statement_id OU agencia e conta")
            if len(agencia) != 4 or not agencia.isdigit():
                raise ValueError("Agência deve ter 4 dígitos numéricos")
            if len(conta) != 12 or not conta.isdigit():
                raise ValueError("Conta deve ter 12 dígitos numéricos")
            statement_id = f"{agencia}.{conta}"
        
        # Validar formato de data
        try:
            initial_dt = datetime.strptime(initial_date, "%Y-%m-%d")
            final_dt = datetime.strptime(final_date, "%Y-%m-%d")
            if initial_dt > final_dt:
                raise ValueError("Data inicial deve ser anterior à data final")
        except ValueError as e:
            if "time data" in str(e):
                raise ValueError("Datas devem estar no formato YYYY-MM-DD")
            raise
        
        if limit < 1 or limit > 50:
            raise ValueError("_limit deve estar entre 1 e 50")
        if offset < 1:
            raise ValueError("_offset deve ser maior ou igual a 1")
        
        # Construir URL
        url = (
            f"{self.config.base_url}/bank_account_information/v1/"
            f"banks/{self.config.bank_id}/statements/{statement_id}"
        )
        
        params = {
            "initialDate": initial_date,
            "finalDate": final_date,
            "_offset": offset,
            "_limit": limit
        }
        
        headers = self._get_headers()
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 401:
                # Token pode ter expirado, tentar renovar
                self._get_access_token(force_refresh=True)
                headers = self._get_headers()
                response = self.session.get(url, params=params, headers=headers, timeout=30)
                
            if response.status_code == 404:
                raise requests.HTTPError(f"Conta não encontrada: {statement_id}")
            elif response.status_code == 400:
                error_msg = response.text
                try:
                    error_json = response.json()
                    error_msg = error_json.get("message", error_msg)
                except:
                    pass
                raise requests.HTTPError(f"Parâmetros inválidos: {error_msg}")
            elif response.status_code == 403:
                # ✅ MELHORADO (13/01/2026): Tratamento detalhado de erro 403
                error_msg = "Acesso negado (403 Forbidden)"
                error_details = []
                
                # Tentar extrair mensagem de erro da resposta
                try:
                    error_json = response.json()
                    if isinstance(error_json, dict):
                        if 'message' in error_json:
                            error_msg = error_json['message']
                        elif 'error' in error_json:
                            error_msg = error_json['error']
                        elif 'erros' in error_json:
                            erros = error_json.get('erros', [])
                            if erros and isinstance(erros, list) and len(erros) > 0:
                                primeiro_erro = erros[0]
                                error_msg = primeiro_erro.get('mensagem', error_msg)
                except:
                    pass
                
                # Adicionar detalhes diagnósticos
                error_details.append(f"❌ Erro 403: {error_msg}")
                error_details.append("💡 Possíveis causas:")
                
                # Verificar certificados
                if not self.config.cert_file and not self.config.cert_path:
                    error_details.append("   1. ⚠️ Certificados mTLS NÃO configurados!")
                else:
                    if self.config.cert_file and os.path.exists(self.config.cert_file):
                        error_details.append(f"   1. ✅ Certificado encontrado: {self.config.cert_file}")
                    elif self.config.cert_file:
                        error_details.append(f"   1. ❌ Certificado NÃO encontrado: {self.config.cert_file}")
                    
                    if self.config.key_file and os.path.exists(self.config.key_file):
                        error_details.append(f"   2. ✅ Chave encontrada: {self.config.key_file}")
                    elif self.config.key_file:
                        error_details.append(f"   2. ❌ Chave NÃO encontrada: {self.config.key_file}")
                    
                    if self.config.cert_path and os.path.exists(self.config.cert_path):
                        error_details.append(f"   3. ✅ cert_path encontrado: {self.config.cert_path}")
                    elif self.config.cert_path:
                        error_details.append(f"   3. ❌ cert_path NÃO encontrado: {self.config.cert_path}")
                
                # Verificar credenciais
                if not self.config.client_id or not self.config.client_secret:
                    error_details.append("   4. ⚠️ Client ID ou Client Secret não configurados!")
                else:
                    error_details.append("   4. ✅ Credenciais configuradas")
                
                error_details.append("   5. Verifique se o certificado está vinculado à aplicação no Developer Portal")
                error_details.append("   6. Verifique se a aplicação tem permissão para acessar contas")
                
                logger.error("\n".join(error_details))
                raise requests.HTTPError("\n".join(error_details))
            
            response.raise_for_status()
            return response.json()
            
        except requests.Timeout:
            raise Exception("Timeout na requisição. Tente novamente.")
        except requests.ConnectionError:
            raise Exception("Erro de conexão. Verifique sua internet.")
    
    def get_extrato_paginado(
        self,
        agencia: str = None,
        conta: str = None,
        statement_id: str = None,
        initial_date: str = None,
        final_date: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Busca extrato completo com paginação automática"""
        all_records = []
        offset = 1
        
        while True:
            response = self.get_extrato(
                agencia=agencia,
                conta=conta,
                statement_id=statement_id,
                initial_date=initial_date,
                final_date=final_date,
                offset=offset,
                limit=limit
            )
            
            records = []
            if isinstance(response, dict):
                records = response.get("_content", [])
                if not records:
                    records = (
                        response.get("data", []) or 
                        response.get("statements", []) or 
                        response.get("transactions", []) or
                        response.get("items", [])
                    )
            
            if not records:
                break
                
            all_records.extend(records)
            
            # Verificar se há mais páginas
            total = response.get("total", 0)
            has_more = response.get("hasMore", False)
            
            if len(records) < limit or (total > 0 and len(all_records) >= total) or not has_more:
                break
                
            offset += 1
        
        return all_records
    
    def listar_contas(self, offset: int = 1, limit: int = 50) -> Dict[str, Any]:
        """Lista todas as contas disponíveis"""
        url = (
            f"{self.config.base_url}/bank_account_information/v1/"
            f"banks/{self.config.bank_id}/accounts"
        )
        
        params = {
            "_offset": offset,
            "_limit": limit
        }
        
        headers = self._get_headers()
        response = self.session.get(url, params=params, headers=headers, timeout=30)
        
        # ✅ MELHORADO (13/01/2026): Tratamento de erro 403 antes de raise_for_status()
        if response.status_code == 403:
            # ✅ Tratamento detalhado de erro 403
            error_msg = "Acesso negado (403 Forbidden)"
            error_details = []
            
            # Tentar extrair mensagem de erro da resposta
            try:
                error_json = response.json()
                if isinstance(error_json, dict):
                    if 'message' in error_json:
                        error_msg = error_json['message']
                    elif 'error' in error_json:
                        error_msg = error_json['error']
                    elif 'erros' in error_json:
                        erros = error_json.get('erros', [])
                        if erros and isinstance(erros, list) and len(erros) > 0:
                            primeiro_erro = erros[0]
                            error_msg = primeiro_erro.get('mensagem', error_msg)
            except:
                pass
            
            # Adicionar detalhes diagnósticos
            error_details.append(f"❌ Erro 403: {error_msg}")
            error_details.append("💡 Possíveis causas:")
            
            # Verificar certificados
            if not self.config.cert_file and not self.config.cert_path:
                error_details.append("   1. ⚠️ Certificados mTLS NÃO configurados!")
            else:
                if self.config.cert_file and os.path.exists(self.config.cert_file):
                    error_details.append(f"   1. ✅ Certificado encontrado: {self.config.cert_file}")
                elif self.config.cert_file:
                    error_details.append(f"   1. ❌ Certificado NÃO encontrado: {self.config.cert_file}")
                
                if self.config.key_file and os.path.exists(self.config.key_file):
                    error_details.append(f"   2. ✅ Chave encontrada: {self.config.key_file}")
                elif self.config.key_file:
                    error_details.append(f"   2. ❌ Chave NÃO encontrada: {self.config.key_file}")
                
                if self.config.cert_path and os.path.exists(self.config.cert_path):
                    error_details.append(f"   3. ✅ cert_path encontrado: {self.config.cert_path}")
                elif self.config.cert_path:
                    error_details.append(f"   3. ❌ cert_path NÃO encontrado: {self.config.cert_path}")
            
            # Verificar credenciais
            if not self.config.client_id or not self.config.client_secret:
                error_details.append("   4. ⚠️ Client ID ou Client Secret não configurados!")
            else:
                error_details.append("   4. ✅ Credenciais configuradas")
            
            error_details.append("   5. Verifique se o certificado está vinculado à aplicação no Developer Portal")
            error_details.append("   6. Verifique se a aplicação tem permissão para acessar contas")
            error_details.append("   7. ⚠️ IMPORTANTE: Se você alterou o .env, REINICIE o Flask para carregar as mudanças")
            
            logger.error("\n".join(error_details))
            raise requests.HTTPError("\n".join(error_details))
        
        response.raise_for_status()
        return response.json()
    
    def get_saldo(
        self, 
        agencia: str = None, 
        conta: str = None, 
        balance_id: str = None
    ) -> Dict[str, Any]:
        """Consulta saldo da conta"""
        if not balance_id:
            if not agencia or not conta:
                raise ValueError("Forneça agencia e conta OU balance_id")
            if len(agencia) != 4 or not agencia.isdigit():
                raise ValueError("Agência deve ter 4 dígitos numéricos")
            if len(conta) != 12 or not conta.isdigit():
                raise ValueError("Conta deve ter 12 dígitos numéricos")
            balance_id = f"{agencia}.{conta}"
        
        statement_id = balance_id
        url = (
            f"{self.config.base_url}/bank_account_information/v1/"
            f"banks/{self.config.bank_id}/balances/{statement_id}"
        )
        
        headers = self._get_headers()
        response = self.session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()



