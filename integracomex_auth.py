#!/usr/bin/env python3
"""
Autenticação OAuth2 do Integra Comex (SERPRO) para consulta de CE marítimo.

Requisitos:
  - Python 3.9+
  - Certificado digital e-CPF (mesmo .pfx usado na DUIMP)
  - Consumer Key e Consumer Secret do SERPRO

Variáveis de ambiente aceitas:
  INTEGRACOMEX_CONSUMER_KEY      -> Consumer Key (obrigatório)
  INTEGRACOMEX_CONSUMER_SECRET    -> Consumer Secret (obrigatório)
  INTEGRACOMEX_BASE_URL           -> base da API (padrão: https://api-sapi.estaleiro.serpro.gov.br/integracomex)
  INTEGRACOMEX_CERT_PFX           -> caminho do certificado .pfx (padrão: mesmo da DUIMP)
  INTEGRACOMEX_CERT_PASSWORD      -> senha do .pfx (padrão: mesma da DUIMP)
  INTEGRACOMEX_TOKEN_CACHE        -> caminho do cache JSON (padrão: .integracomex_token_cache.json)
  INTEGRACOMEX_FORCE_REFRESH      -> "true" para ignorar cache e renovar token
"""

from __future__ import annotations

import json
import os
import base64
import time
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
import duimp_auth

# Carregar variáveis de ambiente do .env
duimp_auth.load_env_from_file()


@dataclass
class IntegraComexSettings:
    """Configurações para autenticação Integra Comex."""
    base_url: str  # URL base da API (ex: https://gateway.apiserpro.serpro.gov.br/integra-comex/api)
    auth_base_url: str  # URL base de autenticação (ex: https://siscomex-sapi.estaleiro.serpro.gov.br)
    consumer_key: str
    consumer_secret: str
    cert_pfx: Path
    cert_password: str
    cache_path: Path
    force_refresh: bool


def load_integracomex_settings() -> IntegraComexSettings:
    """Carrega configurações do Integra Comex a partir de variáveis de ambiente.
    
    URLs oficiais conforme documentação:
    - Autenticação Validação: https://hom-siscomex-sapi.estaleiro.serpro.gov.br/authenticate
    - Autenticação Produção: https://siscomex-sapi.estaleiro.serpro.gov.br/authenticate
    - API Validação: https://gateway.apiserpro.serpro.gov.br/integra-comex-carga-hom/v1
    - API Produção: https://gateway.apiserpro.serpro.gov.br/integra-comex/api
    
    Variáveis de ambiente:
    - INTEGRACOMEX_BASE_URL: URL base da API (padrão: produção)
    - INTEGRACOMEX_AUTH_BASE_URL: URL base de autenticação (padrão: produção)
    - INTEGRACOMEX_ENV: "val" ou "prod" para selecionar ambiente (opcional)
    """
    # ✅ PADRÃO: Usar PRODUÇÃO (não validação)
    # Detectar ambiente (validação ou produção)
    env = os.getenv('INTEGRACOMEX_ENV', '').lower().strip()
    # ✅ Só usar validação se explicitamente configurado
    is_validacao = env == 'val' or env == 'validacao' or env == 'homologacao'
    
    # URL base da API (não da autenticação)
    # ✅ PADRÃO: PRODUÇÃO
    if is_validacao:
        base_url_default = 'https://gateway.apiserpro.serpro.gov.br/integra-comex-carga-hom/v1'
    else:
        # ✅ PRODUÇÃO por padrão
        base_url_default = 'https://gateway.apiserpro.serpro.gov.br/integra-comex/api'
    
    base_url = os.getenv('INTEGRACOMEX_BASE_URL', base_url_default).strip()
    
    # URL base de autenticação (separada)
    if is_validacao:
        auth_base_url_default = 'https://hom-siscomex-sapi.estaleiro.serpro.gov.br'
    else:
        auth_base_url_default = 'https://siscomex-sapi.estaleiro.serpro.gov.br'
    
    auth_base_url = os.getenv('INTEGRACOMEX_AUTH_BASE_URL', auth_base_url_default).strip()
    
    consumer_key = os.getenv('INTEGRACOMEX_CONSUMER_KEY', '').strip()
    consumer_secret = os.getenv('INTEGRACOMEX_CONSUMER_SECRET', '').strip()
    
    # Usar mesmo certificado da DUIMP por padrão
    cert_pfx = Path(os.getenv(
        'INTEGRACOMEX_CERT_PFX',
        os.getenv('DUIMP_CERT_PFX', './cert.pfx')
    )).expanduser()
    
    cert_password = os.getenv(
        'INTEGRACOMEX_CERT_PASSWORD',
        os.getenv('DUIMP_CERT_PASSWORD', '')
    )
    
    cache_path = Path(os.getenv(
        'INTEGRACOMEX_TOKEN_CACHE',
        '.integracomex_token_cache.json'
    )).expanduser()
    
    force_refresh = os.getenv('INTEGRACOMEX_FORCE_REFRESH', '').lower() == 'true'
    
    # Validações
    if not consumer_key:
        raise SystemExit('Erro: defina INTEGRACOMEX_CONSUMER_KEY.')
    if not consumer_secret:
        raise SystemExit('Erro: defina INTEGRACOMEX_CONSUMER_SECRET.')
    if not cert_password:
        raise SystemExit('Erro: defina INTEGRACOMEX_CERT_PASSWORD ou DUIMP_CERT_PASSWORD.')
    if not cert_pfx.exists():
        raise SystemExit(f"Erro: arquivo .pfx não encontrado em '{cert_pfx}'.")
    
    return IntegraComexSettings(
        base_url=base_url,
        auth_base_url=auth_base_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        cert_pfx=cert_pfx,
        cert_password=cert_password,
        cache_path=cache_path,
        force_refresh=force_refresh,
    )


def _get_cache_key(settings: IntegraComexSettings) -> str:
    """Gera chave única para cache baseada nas configurações."""
    key_data = f"{settings.consumer_key}:{settings.auth_base_url}:{settings.base_url}"
    return sha256(key_data.encode()).hexdigest()


def _load_cached_token(settings: IntegraComexSettings) -> Optional[Dict[str, Any]]:
    """Carrega token do cache se ainda válido."""
    if settings.force_refresh or not settings.cache_path.exists():
        return None
    
    try:
        cache_data = json.loads(settings.cache_path.read_text(encoding='utf-8'))
        cache_key = _get_cache_key(settings)
        cached = cache_data.get(cache_key)
        
        if not cached:
            return None
        
        # Verificar se token ainda não expirou (com margem de 60 segundos)
        expires_at = cached.get('expires_at', 0)
        if time.time() < (expires_at - 60):
            return cached
        
        return None
    except Exception:
        return None


def _save_token_cache(settings: IntegraComexSettings, token_data: Dict[str, Any]) -> None:
    """Salva token no cache."""
    try:
        cache_key = _get_cache_key(settings)
        
        if settings.cache_path.exists():
            cache_data = json.loads(settings.cache_path.read_text(encoding='utf-8'))
        else:
            cache_data = {}
        
        # Calcular expiração
        expires_in = token_data.get('expires_in', 2000)  # Padrão: 2000 segundos
        expires_at = time.time() + expires_in
        
        # ✅ Salvar TODOS os campos do token_data (similar à DUIMP que salva bodyJson e bodyText)
        # Isso garante que jwt_token e outros campos sejam preservados
        cache_entry = {
            'access_token': token_data.get('access_token'),
            'token_type': token_data.get('token_type', 'Bearer'),
            'jwt_token': token_data.get('jwt_token'),  # Obrigatório conforme documentação
            'expires_in': expires_in,
            'expires_at': expires_at,
            'cached_at': time.time(),
            # Preservar TODOS os outros campos que possam existir (similar à DUIMP)
            'scope': token_data.get('scope'),
        }
        
        # Adicionar qualquer outro campo que possa existir no token_data
        for key, value in token_data.items():
            if key not in cache_entry:
                cache_entry[key] = value
        
        cache_data[cache_key] = cache_entry
        
        settings.cache_path.parent.mkdir(parents=True, exist_ok=True)
        settings.cache_path.write_text(
            json.dumps(cache_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível salvar cache de token: {e}")


def obtain_integracomex_token(settings: IntegraComexSettings) -> Dict[str, Any]:
    """
    Obtém token de acesso OAuth2 do Integra Comex.
    
    Fluxo:
    1. Verifica cache (se não force_refresh)
    2. Se cache válido, retorna token do cache
    3. Se não, faz requisição OAuth2 com certificado e-CPF
    4. Salva token no cache
    5. Retorna token
    
    Args:
        settings: Configurações do Integra Comex
    
    Returns:
        Dict com access_token, token_type, expires_in, etc.
    """
    # Verificar cache primeiro (similar à DUIMP)
    if not settings.force_refresh:
        cached = _load_cached_token(settings)
        if cached:
            # ✅ Retornar TODOS os campos do cache (similar à DUIMP que retorna tudo)
            # Isso garante que jwt_token e outros campos sejam preservados
            result = {
                'access_token': cached.get('access_token'),
                'token_type': cached.get('token_type', 'Bearer'),
                'jwt_token': cached.get('jwt_token'),
                'expires_in': cached.get('expires_in', 2000),
            }
            
            # Preservar TODOS os outros campos do cache (similar à DUIMP)
            for key, value in cached.items():
                if key not in result and key not in ('expires_at', 'cached_at'):
                    result[key] = value
            
            return result
    
    # ⚠️ IMPORTANTE: Verificar documentação oficial antes de assumir formato
    # Documentação: https://doc-siscomex-sapi.estaleiro.serpro.gov.br/integracomex/documentacao/
    # 
    # Por enquanto, implementação experimental baseada em:
    # - Consumer Key/Secret fornecidos (OAuth2 típico)
    # - Certificado e-CPF (mesmo da DUIMP)
    # - Tentando suportar ambos os formatos (DUIMP-style e OAuth2)
    
    # Preparar certificado (usar mesmo método da DUIMP)
    duimp_settings = duimp_auth.load_settings()
    duimp_settings.pfx_path = settings.cert_pfx
    duimp_settings.pfx_password = settings.cert_password
    
    # Extrair certificado e chave (mesmo método da DUIMP)
    try:
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp_dir = Path(tmp_str)
            pem_paths = duimp_auth.extract_cert_and_key(duimp_settings, tmp_dir)
            
            session = requests.Session()
            session.cert = (str(pem_paths['cert']), str(pem_paths['key']))
            session.max_redirects = 5  # Padrão
            
            # ✅ ENDPOINT OFICIAL conforme documentação
            # URL_BASE_AUTENTICACAO/authenticate
            # Validação: https://hom-siscomex-sapi.estaleiro.serpro.gov.br/authenticate
            # Produção: https://siscomex-sapi.estaleiro.serpro.gov.br/authenticate
            auth_url = urljoin(settings.auth_base_url.rstrip('/') + '/', 'authenticate')
            
            # ✅ HEADERS OFICIAIS conforme documentação
            # a) Certificado Digital e-CPF padrão ICP-Brasil válido (via session.cert)
            # b.1) Authorization: Basic (base64(consumerKey:consumerSecret))
            # b.2) "role-type": "IMPEXP"
            # b.3) "content-type": "application/json"
            
            # Preparar Basic Auth conforme documentação
            credentials = f"{settings.consumer_key}:{settings.consumer_secret}"
            basic_auth = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {basic_auth}',
                'role-type': 'IMPEXP',
                'content-type': 'application/json',
            }
            
            # Fazer requisição POST conforme documentação
            # Body vazio ou não especificado na documentação
            response = session.post(auth_url, headers=headers, timeout=30)
            
            # Log da resposta para debug (ANTES de processar)
            log_path = Path('debug_log.txt')
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f"--- INTEGRACOMEX AUTH REQUEST ---\n")
                    f.write(f"URL: {auth_url}\n")
                    f.write(f"Method: POST\n")
                    f.write(f"Headers: {json.dumps(dict(headers), indent=2)}\n")
                    f.write(f"Status: {response.status_code}\n")
                    f.write(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}\n")
                    f.write(f"Response Body (raw): {repr(response.text[:500])}\n")
                    f.write(f"Response Body (text): {response.text[:500]}\n")
                    f.write(f"Response Content-Type: {response.headers.get('Content-Type', 'N/A')}\n")
                    f.write("--- END AUTH REQUEST ---\n\n")
            except Exception as e:
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"Erro ao escrever log: {e}\n")
                except:
                    pass
            
            response.raise_for_status()
            
            # ✅ FORMATO DE RESPOSTA OFICIAL conforme documentação
            # {
            #   "expires_in": 2008,
            #   "scope": "am_application_scope default",
            #   "token_type": "Bearer",
            #   "access_token": "ce6112ab644f06a31b238fe9739f38a4",
            #   "jwt_token": "eyJhbGciOiJSUzI1NiJ9..."
            # }
            
            # Parsear JSON do body
            if not response.text or not response.text.strip():
                raise RuntimeError(f"Resposta vazia da API Integra Comex. Status: {response.status_code}")
            
            try:
                token_data = response.json()
            except json.JSONDecodeError as json_err:
                raise RuntimeError(
                    f"Resposta da API não é JSON válido. Status: {response.status_code}\n"
                    f"Resposta recebida: {response.text[:500]}\n"
                    f"Erro JSON: {json_err}"
                )
            
            # Validar campos obrigatórios conforme documentação
            access_token = token_data.get('access_token')
            jwt_token = token_data.get('jwt_token')
            
            if not access_token:
                raise RuntimeError(
                    f"access_token não encontrado na resposta. Status: {response.status_code}\n"
                    f"Resposta: {json.dumps(token_data, indent=2)}"
                )
            
            if not jwt_token:
                # jwt_token é obrigatório conforme documentação, mas pode não vir em alguns casos
                # Log para debug mas não falha (pode ser que a API não retorne em alguns casos)
                try:
                    log_path = Path('debug_log.txt')
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(f"⚠️ AVISO: jwt_token não encontrado na resposta de autenticação\n")
                        f.write(f"Resposta completa: {json.dumps(token_data, indent=2)}\n")
                except:
                    pass
            
            # Garantir campos padrão
            if 'token_type' not in token_data:
                token_data['token_type'] = 'Bearer'
            if 'expires_in' not in token_data:
                token_data['expires_in'] = 2008  # Padrão conforme documentação
            
            # Salvar no cache
            _save_token_cache(settings, token_data)
            
            return token_data
    except requests.exceptions.HTTPError as e:
        error_msg = f"Erro HTTP ao obter token Integra Comex: {e}"
        if e.response is not None:
            error_msg += f"\nStatus: {e.response.status_code}"
            try:
                error_msg += f"\nResposta: {e.response.text[:500]}"
            except:
                pass
        raise RuntimeError(error_msg)
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro ao obter token Integra Comex: {e}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f"\nStatus: {e.response.status_code}"
            try:
                error_msg += f"\nResposta: {e.response.text[:500]}"
            except:
                pass
        raise RuntimeError(error_msg)


def get_integracomex_token() -> str:
    """
    Função auxiliar para obter access_token do Integra Comex.
    
    Returns:
        str: access_token para usar em requisições
    """
    settings = load_integracomex_settings()
    token_data = obtain_integracomex_token(settings)
    return token_data.get('access_token', '')

