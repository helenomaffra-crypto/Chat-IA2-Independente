#!/usr/bin/env python3
"""
Cliente simples para consumir endpoints DUIMP utilizando mTLS e os tokens
já obtidos via duimp_auth.py.

Exemplo:
  python3 duimp_request.py /ext/duimp/20BR00000000198/0/diagnosticos

Opções úteis:
  -X POST --json-body '{"campo":"valor"}'
  --header "Accept: application/json"
  --timeout 60
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urljoin

import requests

import duimp_auth


def parse_headers(header_list: Optional[list[str]]) -> Dict[str, str]:
  headers: Dict[str, str] = {}
  if not header_list:
    return headers
  for item in header_list:
    if ':' not in item:
      raise SystemExit(f'Header inválido (use Nome: Valor): {item}')
    name, value = item.split(':', 1)
    headers[name.strip()] = value.strip()
  return headers


def build_session(settings: duimp_auth.Settings) -> requests.Session:
  # Persistir os PEMs em diretório estável para evitar remoção durante redirects
  cache_dir = Path('.mtls_cache')
  cache_dir.mkdir(exist_ok=True)

  # Extrair sempre para um tmp e depois mover para o cache estável
  tmp_dir = Path(tempfile.mkdtemp())
  pem_paths = duimp_auth.extract_cert_and_key(settings, tmp_dir)

  cert_dest = cache_dir / 'cert.pem'
  key_dest = cache_dir / 'key.pem'
  try:
    cert_dest.write_bytes(pem_paths['cert'].read_bytes())
    key_dest.write_bytes(pem_paths['key'].read_bytes())
  finally:
    # Limpar diretório temporário sem afetar o cache estável
    try:
      pem_paths['cert'].unlink(missing_ok=True)
      pem_paths['key'].unlink(missing_ok=True)
      tmp_dir.rmdir()
    except OSError:
      pass

  session = requests.Session()
  session.cert = (str(cert_dest), str(key_dest))
  session.verify = str(settings.ca_bundle) if settings.ca_bundle else True
  session.max_redirects = settings.max_redirects if hasattr(settings, 'max_redirects') else 5
  return session


def main() -> None:
  parser = argparse.ArgumentParser(description='Consumir endpoint DUIMP com mTLS.')
  parser.add_argument('path', nargs='?', help='Caminho relativo (ex.: /ext/duimp/<numero>/<versao>/diagnosticos)')
  parser.add_argument('--duimp-number', help='Número da DUIMP (15 caracteres).')
  parser.add_argument('--duimp-version', type=int, help='Versão da DUIMP (inteiro >= 1).')
  parser.add_argument('-X', '--method', default='GET', help='Método HTTP (padrão: GET)')
  parser.add_argument('--json-body', help='Conteúdo JSON para enviar no corpo.')
  parser.add_argument('--data-file', help='Arquivo cujo conteúdo será enviado no corpo.')
  parser.add_argument('--header', action='append', help='Header adicional (Nome: Valor). Pode repetir.')
  parser.add_argument('--query', action='append', help='Parâmetro de query no formato chave=valor. Pode repetir.')
  parser.add_argument('--timeout', type=int, default=30, help='Timeout em segundos (padrão: 30).')
  parser.add_argument('--output', choices=['text', 'json'], default='text', help='Formato da saída.')

  args = parser.parse_args()

  if args.json_body and args.data_file:
    raise SystemExit('Use apenas --json-body ou --data-file, não ambos.')

  if args.duimp_number and args.duimp_version:
    if args.duimp_version < 1:
      raise SystemExit('A versão da DUIMP deve ser >= 1.')
    path = f'/duimp-api/api/ext/duimp/{args.duimp_number}/{args.duimp_version}'
  else:
    path = args.path

  if not path:
    raise SystemExit('Informe o caminho (path) ou --duimp-number/--duimp-version.')

  settings = duimp_auth.load_settings()
  token_payload = duimp_auth.obtain_tokens(settings)

  set_token = token_payload.get('setToken')
  csrf_token = token_payload.get('csrfToken')
  if not set_token or not csrf_token:
    raise SystemExit('Tokens não encontrados. Execute duimp_auth primeiro e verifique se a autenticação ocorreu.')

  url = urljoin(settings.base_url.rstrip('/') + '/', path.lstrip('/'))

  session = build_session(settings)
  headers = parse_headers(args.header)
  headers.setdefault('Authorization', set_token)
  headers.setdefault('X-CSRF-Token', csrf_token)

  method = args.method.upper()
  request_kwargs: Dict[str, object] = {'headers': headers, 'timeout': args.timeout}

  if args.query:
    query_params: Dict[str, str] = {}
    for item in args.query:
      if '=' not in item:
        raise SystemExit(f'Parâmetro de query inválido (use chave=valor): {item}')
      key, value = item.split('=', 1)
      query_params[key.strip()] = value.strip()
    request_kwargs['params'] = query_params

  if args.json_body:
    try:
      request_kwargs['json'] = json.loads(args.json_body)
    except json.JSONDecodeError as exc:
      raise SystemExit(f'JSON inválido em --json-body: {exc}') from exc
  elif args.data_file:
    request_kwargs['data'] = Path(args.data_file).read_bytes()

  try:
    response = session.request(method, url, **request_kwargs)
  except requests.exceptions.SSLError as exc:
    raise SystemExit(f'Erro SSL: {exc}') from exc
  except requests.exceptions.RequestException as exc:
    raise SystemExit(f'Erro na requisição: {exc}') from exc

  if args.output == 'json':
    payload = {
      'statusCode': response.status_code,
      'headers': dict(response.headers),
      'body': None,
    }
    try:
      payload['body'] = response.json()
    except ValueError:
      payload['body'] = response.text
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return

  print(f'Status HTTP: {response.status_code}')
  for name, value in response.headers.items():
    print(f'{name}: {value}')

  print()
  try:
    parsed = response.json()
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
  except ValueError:
    print(response.text)


if __name__ == '__main__':
  main()
