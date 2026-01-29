#!/usr/bin/env python3
"""
Autenticação mTLS do Portal Único Siscomex (DUIMP) utilizando certificado PKCS#12.

Requisitos:
  - Python 3.9+
  - OpenSSL disponível no PATH (usado para extrair o par cert/chave do .pfx)

Variáveis de ambiente aceitas:
  DUIMP_CERT_PFX        -> caminho do arquivo .pfx (padrão: ./cert.pfx)
  DUIMP_CERT_PASSWORD   -> senha do .pfx (obrigatória)
  DUIMP_ROLE_TYPE       -> Role-Type desejado (obrigatório)
  PUCOMEX_BASE_URL      -> base da API (padrão produção: https://portalunico.siscomex.gov.br/portal)
  DUIMP_CA_BUNDLE       -> bundle de CA para validar o servidor (opcional)
  DUIMP_CACHE_PATH      -> caminho do cache JSON (padrão: .duimp_token_cache.json na pasta atual)
  DUIMP_FORCE_REFRESH   -> "true" para ignorar cache e renovar token
  DUIMP_MAX_REDIRECTS   -> máximo de redirecionamentos (padrão 5)
  DUIMP_OUTPUT          -> "json" para saída estruturada, padrão "text"
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin
import time

import requests


def load_env_from_file(filepath: str = '.env') -> None:
  """Carrega variáveis de ambiente a partir de um arquivo .env simples."""
  path = Path(filepath)
  if not path.exists():
    return
  try:
    for line in path.read_text(encoding='utf-8').splitlines():
      stripped = line.strip()
      if not stripped or stripped.startswith('#') or '=' not in stripped:
        continue
      key, value = stripped.split('=', 1)
      key = key.strip()
      value = value.strip().strip('"').strip("'")
      if key:
        os.environ[key] = value
  except OSError:
    pass


load_env_from_file()

def find_openssl() -> str:
  """Resolve o caminho do executável do OpenSSL de forma portátil.

  Ordem de resolução:
    1. Variável de ambiente DUIMP_OPENSSL_BIN (ou DUIMP_OPENSSL)
    2. PATH do sistema (shutil.which)
    3. Locais comuns no Windows (ShiningLight, Git for Windows)
  """
  env_candidates = [
    os.getenv('DUIMP_OPENSSL_BIN', '').strip(),
    os.getenv('DUIMP_OPENSSL', '').strip(),
  ]
  for candidate in env_candidates:
    if candidate:
      p = Path(candidate)
      if p.exists():
        return str(p)

  which_path = shutil.which('openssl')
  if which_path:
    return which_path

  common_candidates = [
    "C:/Program Files/OpenSSL-Win64/bin/openssl.exe",
    "C:/Program Files (x86)/OpenSSL-Win32/bin/openssl.exe",
    "C:/Program Files/Git/usr/bin/openssl.exe",
    "C:/Program Files/Git/mingw64/bin/openssl.exe",
  ]
  for path_str in common_candidates:
    if Path(path_str).exists():
      return path_str

  raise SystemExit(
    'Erro: OpenSSL não encontrado. Defina DUIMP_OPENSSL_BIN com o caminho do openssl, '
    'ou adicione o OpenSSL ao PATH. Ex.: C:/Program Files/OpenSSL-Win64/bin/openssl.exe'
  )


@dataclass
class Settings:
  base_url: str
  role_type: str
  pfx_path: Path
  pfx_password: str
  ca_bundle: Optional[Path]
  cache_path: Path
  force_refresh: bool
  max_redirects: int
  output_mode: str


def load_settings() -> Settings:
  base_url = os.getenv('PUCOMEX_BASE_URL', 'https://portalunico.siscomex.gov.br/portal').strip()
  role_type = os.getenv('DUIMP_ROLE_TYPE', '').strip()
  pfx_path = Path(os.getenv('DUIMP_CERT_PFX', './cert.pfx')).expanduser()
  pfx_password = os.getenv('DUIMP_CERT_PASSWORD', '')
  ca_bundle_raw = os.getenv('DUIMP_CA_BUNDLE', '').strip()
  cache_path = Path(os.getenv('DUIMP_CACHE_PATH', '.duimp_token_cache.json')).expanduser()
  force_refresh = os.getenv('DUIMP_FORCE_REFRESH', '').lower() == 'true'
  max_redirects = int(os.getenv('DUIMP_MAX_REDIRECTS', '5'))
  output_mode = os.getenv('DUIMP_OUTPUT', 'text').lower()

  if not role_type:
    raise SystemExit('Erro: defina DUIMP_ROLE_TYPE.')
  if not pfx_password:
    raise SystemExit('Erro: defina DUIMP_CERT_PASSWORD.')
  if not pfx_path.exists():
    raise SystemExit(f"Erro: arquivo .pfx não encontrado em '{pfx_path}'.")

  ca_bundle = Path(ca_bundle_raw).expanduser() if ca_bundle_raw else None
  if ca_bundle and not ca_bundle.exists():
    raise SystemExit(f"Erro: CA bundle informado em DUIMP_CA_BUNDLE não encontrado: '{ca_bundle}'.")

  return Settings(
    base_url=base_url,
    role_type=role_type,
    pfx_path=pfx_path,
    pfx_password=pfx_password,
    ca_bundle=ca_bundle,
    cache_path=cache_path,
    force_refresh=force_refresh,
    max_redirects=max_redirects,
    output_mode=output_mode,
  )


def load_cache(cache_path: Path) -> Dict[str, Any]:
  if not cache_path.exists():
    return {}
  try:
    return json.loads(cache_path.read_text(encoding='utf-8'))
  except Exception as exc:
    print(f"Aviso: falha ao ler cache em {cache_path}: {exc}", file=sys.stderr)
    return {}


def save_cache(cache_path: Path, data: Dict[str, Any]) -> None:
  try:
    cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
  except Exception as exc:
    print(f"Aviso: não foi possível salvar o cache em {cache_path}: {exc}", file=sys.stderr)


def build_cache_key(settings: Settings) -> str:
  fingerprint = sha256(settings.pfx_path.read_bytes()).hexdigest()
  return sha256(f"{settings.base_url}|{settings.role_type}|{fingerprint}".encode()).hexdigest()


def resolve_expiration(expiration_header: Optional[str]) -> int:
  if expiration_header:
    try:
      parsed = int(expiration_header)
      if parsed > 0:
        return parsed
    except ValueError:
      pass
  return int(time.time() * 1000 + 55 * 60 * 1000)  # fallback ~55 min


def maybe_use_cache(settings: Settings, cache: Dict[str, Any], cache_key: str) -> Optional[Dict[str, Any]]:
  if settings.force_refresh:
    return None
  entry = cache.get(cache_key)
  if not entry:
    return None
  expires_at = entry.get('expiresAt', 0)
  if expires_at > int(time.time() * 1000 + 30_000):
    return entry
  return None


def ensure_openssl_available() -> None:
  if shutil.which('openssl'):
    return
  raise SystemExit('Erro: comando "openssl" não encontrado no PATH. Instale o OpenSSL para prosseguir.')


def extract_cert_and_key(settings: Settings, tmp_dir: Path) -> Dict[str, Path]:
  openssl_bin = find_openssl()
  cert_path = tmp_dir / 'cert.pem'
  key_path = tmp_dir / 'key.pem'

  cmd_base = [openssl_bin, 'pkcs12', '-in', str(settings.pfx_path), '-passin', f'pass:{settings.pfx_password}']

  # Export certificate (without private key)
  cmd_cert = cmd_base + ['-clcerts', '-nokeys', '-out', str(cert_path)]
  result_cert = subprocess.run(cmd_cert, capture_output=True, text=True)
  if result_cert.returncode != 0:
    raise SystemExit(f"Erro ao extrair certificado com OpenSSL: {result_cert.stderr.strip()}")

  # Export private key (unencrypted)
  cmd_key = cmd_base + ['-nocerts', '-nodes', '-out', str(key_path)]
  result_key = subprocess.run(cmd_key, capture_output=True, text=True)
  if result_key.returncode != 0:
    raise SystemExit(f"Erro ao extrair chave privada com OpenSSL: {result_key.stderr.strip()}")

  return {'cert': cert_path, 'key': key_path}


def perform_request(settings: Settings) -> Dict[str, Any]:
  with tempfile.TemporaryDirectory() as tmp_str:
    tmp_dir = Path(tmp_str)
    pem_paths = extract_cert_and_key(settings, tmp_dir)

    session = requests.Session()
    session.cert = (str(pem_paths['cert']), str(pem_paths['key']))
    session.verify = str(settings.ca_bundle) if settings.ca_bundle else True
    session.max_redirects = settings.max_redirects

    base = settings.base_url.rstrip('/') + '/'
    auth_path = 'api/autenticar'
    if not settings.base_url.rstrip('/').endswith('/portal'):
      auth_path = 'portal/' + auth_path
    url = urljoin(base, auth_path)
    response = session.post(url, headers={'Role-Type': settings.role_type}, data=b'')

  body_text = response.text
  try:
    body_json = response.json()
  except ValueError:
    body_json = None

  return {
    'statusCode': response.status_code,
    'headers': {k.lower(): v for k, v in response.headers.items()},
    'bodyText': body_text,
    'bodyJson': body_json,
  }


def print_output(settings: Settings, payload: Dict[str, Any]) -> None:
  data = {
    'statusCode': payload['statusCode'],
    'setToken': payload['setToken'],
    'csrfToken': payload['csrfToken'],
    'csrfExpiration': payload.get('csrfExpiration'),
    'body': payload['bodyJson'] if payload['bodyJson'] is not None else payload['bodyText'],
  }

  if settings.output_mode == 'json':
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return

  print(f"Status HTTP: {data['statusCode']}")
  if data['setToken']:
    print(f"Set-Token: {data['setToken']}")
  else:
    print('Aviso: cabeçalho Set-Token não retornado.', file=sys.stderr)

  if data['csrfToken']:
    print(f"X-CSRF-Token: {data['csrfToken']}")
  else:
    print('Aviso: cabeçalho X-CSRF-Token não retornado.', file=sys.stderr)

  if data['csrfExpiration']:
    print(f"X-CSRF-Expiration: {data['csrfExpiration']}")

  body = data['body']
  if body:
    if isinstance(body, dict):
      print('Corpo da resposta:', json.dumps(body, indent=2, ensure_ascii=False))
    else:
      print('Corpo da resposta (texto):', body)
  else:
    print('Corpo da resposta vazio.')


def obtain_tokens(settings: Settings) -> Dict[str, Any]:
  cache = load_cache(settings.cache_path)
  cache_key = build_cache_key(settings)

  cached_entry = maybe_use_cache(settings, cache, cache_key)
  if cached_entry:
    return {
      'statusCode': cached_entry.get('statusCode', 200),
      'setToken': cached_entry.get('setToken'),
      'csrfToken': cached_entry.get('csrfToken'),
      'csrfExpiration': cached_entry.get('expirationHeader'),
      'bodyJson': cached_entry.get('bodyJson'),
      'bodyText': cached_entry.get('body'),
    }

  result = perform_request(settings)
  headers = result['headers']
  set_token = headers.get('set-token')
  csrf_token = headers.get('x-csrf-token')
  csrf_expiration = headers.get('x-csrf-expiration')

  payload = {
    'statusCode': result['statusCode'],
    'setToken': set_token,
    'csrfToken': csrf_token,
    'csrfExpiration': csrf_expiration,
    'bodyJson': result['bodyJson'],
    'bodyText': result['bodyText'],
  }

  if set_token and csrf_token:
    cache_entry = {
      'statusCode': result['statusCode'],
      'setToken': set_token,
      'csrfToken': csrf_token,
      'expirationHeader': csrf_expiration,
      'body': result['bodyText'],
      'bodyJson': result['bodyJson'],
      'cachedAt': int(time.time() * 1000),
      'expiresAt': resolve_expiration(csrf_expiration),
    }
    cache[cache_key] = cache_entry
    save_cache(settings.cache_path, cache)

  return payload


def main() -> None:
  settings = load_settings()
  payload = obtain_tokens(settings)
  print_output(settings, payload)


if __name__ == '__main__':
  try:
    main()
  except requests.exceptions.SSLError as exc:
    raise SystemExit(f'Erro SSL: {exc}') from exc
  except requests.exceptions.RequestException as exc:
    raise SystemExit(f'Erro na requisição: {exc}') from exc
