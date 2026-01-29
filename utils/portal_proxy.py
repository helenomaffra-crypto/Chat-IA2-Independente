# -*- coding: utf-8 -*-
"""
Utils - Portal Proxy
====================
Funções para fazer requisições HTTP ao Portal Único Siscomex.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

import requests

# Importar duimp_auth com tratamento de erro (pode não estar disponível)
try:
    import duimp_auth
    from duimp_request import build_session
except ImportError:
    # Se não conseguir importar, tentar importar do diretório raiz
    import importlib.util
    import sys
    from pathlib import Path
    
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    
    # Tentar carregar duimp_auth.py do diretório raiz
    duimp_auth_path = root_dir / 'duimp_auth.py'
    if duimp_auth_path.exists():
        spec = importlib.util.spec_from_file_location("duimp_auth", duimp_auth_path)
        duimp_auth = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(duimp_auth)
        
        # Tentar carregar duimp_request também
        duimp_request_path = root_dir / 'duimp_request.py'
        if duimp_request_path.exists():
            spec = importlib.util.spec_from_file_location("duimp_request", duimp_request_path)
            duimp_request = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(duimp_request)
            build_session = duimp_request.build_session
        else:
            build_session = None
    else:
        duimp_auth = None
        build_session = None

from utils.auth import ensure_tokens, get_effective_base_url


def normalize_duimp_path(path: str) -> str:
    """
    Normaliza links RELATIVOS vindos no JSON (ex.: 'ext/duimp/...') para o basePath correto da API:
    '/duimp-api/api/ext/...'. Mantém outros caminhos como estão.
    
    Args:
        path: Caminho a normalizar
    
    Returns:
        str: Caminho normalizado
    """
    if not path:
        return path
    p = path.strip()
    # Se for absoluto (http/https), mantenha
    if p.startswith('http://') or p.startswith('https://'):
        return p
    # Já está no basePath certo?
    if p.startswith('/duimp-api/api/'):
        return p
    # Links relativos que começam com ext/... (padrão do payload da Duimp)
    if p.startswith('ext/'):
        return '/duimp-api/api/' + p
    if p.startswith('/ext/'):
        return '/duimp-api/api' + p
    # Alguns payloads podem vir como 'duimp/...'
    if p.startswith('duimp/'):
        return '/duimp-api/api/ext/' + p
    if p.startswith('/duimp/'):
        return '/duimp-api/api' + p
    # Default: retorna como veio
    return p


def call_portal(path: str, query: Optional[Dict[str, Any]] = None, accept: str = 'application/json', method: str = 'GET', body: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    """
    Função auxiliar centralizada para fazer requisições HTTP ao Portal Único Siscomex.
    Gerencia automaticamente autenticação, tokens, sessão e normalização de URLs.
    
    ⚠️ CRÍTICO: Esta função é usada por TODOS os endpoints do fluxo DUIMP.
    
    Args:
        path: Caminho da API (será normalizado automaticamente)
        query: Query parameters (opcional)
        accept: Content-Type aceito (padrão: 'application/json')
        method: Método HTTP (GET, POST, PUT, PATCH, DELETE)
        body: Body da requisição (para POST/PUT/PATCH)
    
    Returns:
        Tuple[int, Any]: (status_code, response_body)
    """
    if duimp_auth is None:
        raise ImportError("duimp_auth não está disponível. Verifique se o módulo duimp_auth.py existe no diretório raiz do projeto.")
    
    settings = duimp_auth.load_settings()
    settings.base_url = get_effective_base_url()

    set_token, csrf_token = ensure_tokens(settings)
    
    if build_session is None:
        raise ImportError("duimp_request não está disponível. Verifique se o módulo duimp_request.py existe no diretório raiz do projeto.")
    
    session = build_session(settings)
    headers = {'Authorization': set_token, 'X-CSRF-Token': csrf_token, 'Accept': accept or 'application/json'}
    
    # Se for POST/PUT, adicionar Content-Type para JSON
    if method in ('POST', 'PUT', 'PATCH') and body is not None:
        headers['Content-Type'] = 'application/json'

    # >>> AJUSTE CRÍTICO: normalizar caminho relativo de itens da Duimp <<<
    path = normalize_duimp_path(path)

    url = urljoin(settings.base_url.rstrip('/') + '/', path.lstrip('/'))
    response: Optional[requests.Response] = None

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'debug_log.txt')
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- NEW REQUEST ---\nMETHOD: {method}\nURL: {url}\n")
            f.write(f"HEADERS: {json.dumps(headers, indent=2)}\n")

        # Fazer requisição com método especificado
        if method in ('POST', 'PUT', 'PATCH'):
            response = session.request(method, url, params=query, headers=headers, json=body, timeout=60)
        else:
            response = session.request(method, url, params=query, headers=headers, timeout=60)

        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- RESPONSE ---\nSTATUS: {response.status_code}\nCT: {response.headers.get('Content-Type')}\nBODY:\n{response.text[:2000]}\n\n")

        content_type = (response.headers.get('Content-Type') or '').lower()
        is_json_expected = 'application/json' in (accept or '').lower()
        is_html_response = 'text/html' in content_type

        if is_json_expected and is_html_response:
            body = {'error': 'ERRO_API_EXTERNA', 'message': 'API retornou HTML, não JSON.', 'details': response.text[:1000]}
            status_code = 502 if 200 <= response.status_code < 300 else response.status_code
            return status_code, body

        if 'application/json' in content_type:
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
        elif 'application/zip' in content_type or 'application/octet-stream' in content_type:
            downloads_dir = Path('downloads')
            downloads_dir.mkdir(exist_ok=True)
            # Usar extensão .zip para arquivos ZIP
            filename = downloads_dir / f'download_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
            filename.write_bytes(response.content)
            body = f'<arquivo salvo em {filename.resolve()} ({len(response.content)} bytes)>\n<br>Caminho completo: <code>{filename.resolve()}</code>'
        else:
            body = response.text

        status_code = response.status_code
        
        # ✅ NOVO: Gravar histórico de mudanças se resposta for de documento aduaneiro
        if status_code == 200 and body and isinstance(body, dict):
            try:
                _gravar_historico_se_documento(
                    path=path,
                    response_body=body,
                    processo_referencia=None,  # Portal não passa processo_referencia
                    fonte_dados='PORTAL_UNICO',
                    api_endpoint=path
                )
            except Exception as e:
                # Não bloquear se houver erro no histórico
                import logging
                logging.warning(f'⚠️ Erro ao gravar histórico de documento: {e}')

        return status_code, body
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        session.close()


def _gravar_historico_se_documento(
    path: str,
    response_body: Dict[str, Any],
    processo_referencia: Optional[str],
    fonte_dados: str,
    api_endpoint: str
) -> None:
    """
    Grava histórico de mudanças se a resposta for de um documento aduaneiro.
    
    Detecta automaticamente o tipo de documento pelo path e extrai o número.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Detectar tipo de documento pelo path
        tipo_documento = None
        numero_documento = None
        
        # DUIMP
        if '/duimp' in path or '/duimp-api' in path:
            tipo_documento = 'DUIMP'
            import re
            # Extrair número e versão do path (ex: /duimp-api/api/ext/duimp/25BR00001928777/1)
            match = re.search(r'/duimp[^/]*/([^/]+)(?:/(\d+))?', path)
            if match:
                numero_documento = match.group(1)
            # Se não encontrou no path, tentar no response_body
            if not numero_documento:
                identificacao = response_body.get('identificacao', {})
                numero_documento = identificacao.get('numero') if isinstance(identificacao, dict) else None
                if not numero_documento:
                    numero_documento = response_body.get('numero')
        
        # CCT (Conhecimento de Carga Aérea)
        elif '/ccta/' in path or '/cct/' in path:
            tipo_documento = 'CCT'
            import re
            # Extrair número do CCT do path (ex: /duimp-api/api/ext/ccta/1234567890)
            match = re.search(r'/ccta?[^/]*/([^/]+)', path)
            if match:
                numero_documento = match.group(1)
            # Se não encontrou no path, tentar no response_body
            if not numero_documento:
                numero_documento = response_body.get('awb') or response_body.get('numeroCCT') or response_body.get('numero_cct')
        
        # Se detectou tipo e número, gravar histórico
        if tipo_documento and numero_documento:
            from services.documento_historico_service import DocumentoHistoricoService
            
            historico_service = DocumentoHistoricoService()
            mudancas = historico_service.detectar_e_gravar_mudancas(
                numero_documento=str(numero_documento),
                tipo_documento=tipo_documento,
                dados_novos=response_body,
                fonte_dados=fonte_dados,
                api_endpoint=api_endpoint,
                processo_referencia=processo_referencia
            )
            
            if mudancas:
                logger.info(f"✅ {len(mudancas)} mudança(ões) detectada(s) e gravada(s) para {tipo_documento} {numero_documento}")
        else:
            logger.debug(f"ℹ️ Resposta não é de documento aduaneiro ou não foi possível detectar tipo/número (path: {path})")
            
    except Exception as e:
        logger.warning(f"⚠️ Erro ao gravar histórico de documento: {e}", exc_info=True)


def call_portal_catp(path: str, query: Optional[Dict[str, Any]] = None, accept: str = 'application/json', method: str = 'GET', body: Optional[Dict[str, Any]] = None, ambiente: str = 'validacao') -> Tuple[int, Any]:
    """
    Função auxiliar para chamadas CATP que usa ambiente de validação por padrão.
    Produtos CATP são criados no ambiente de validação, então faz sentido consultar lá primeiro.
    
    Args:
        path: Caminho da API CATP
        query: Query parameters (opcional)
        accept: Content-Type aceito (padrão: 'application/json')
        method: Método HTTP (GET, POST, PUT, PATCH, DELETE)
        body: Body da requisição (para POST/PUT/PATCH)
        ambiente: 'validacao' ou 'producao' (padrão: 'validacao')
    
    Returns:
        Tuple[int, Any]: (status_code, response_body)
    """
    settings = duimp_auth.load_settings()
    
    # Determinar URL base conforme ambiente
    # ✅ CRÍTICO: O ambiente usado para buscar atributos DEVE ser o mesmo usado para cadastrar o produto
    if ambiente == 'validacao':
        settings.base_url = 'https://val.portalunico.siscomex.gov.br'
    elif ambiente == 'producao':
        settings.base_url = 'https://portalunico.siscomex.gov.br'
    else:  # homologacao ou outros
        settings.base_url = 'https://hom.pucomex.serpro.gov.br'
    
    set_token, csrf_token = ensure_tokens(settings)
    
    if build_session is None:
        raise ImportError("duimp_request não está disponível. Verifique se o módulo duimp_request.py existe no diretório raiz do projeto.")
    
    session = build_session(settings)
    headers = {'Authorization': set_token, 'X-CSRF-Token': csrf_token, 'Accept': accept or 'application/json'}
    
    # Se for POST/PUT, adicionar Content-Type para JSON
    if method in ('POST', 'PUT', 'PATCH') and body is not None:
        headers['Content-Type'] = 'application/json'
    
    url = urljoin(settings.base_url.rstrip('/') + '/', path.lstrip('/'))
    response: Optional[requests.Response] = None
    
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'debug_log.txt')
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"--- NEW CATP REQUEST (ambiente: {ambiente}) ---\nMETHOD: {method}\nURL: {url}\n")
            f.write(f"HEADERS: {json.dumps(headers, indent=2)}\n")
        
        # Fazer requisição com método especificado
        if method in ('POST', 'PUT', 'PATCH'):
            response = session.request(method, url, params=query, headers=headers, json=body, timeout=60)
        else:
            response = session.request(method, url, params=query, headers=headers, timeout=60)
        
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"STATUS: {response.status_code}\n")
            if response.text:
                f.write(f"RESPONSE: {response.text[:500]}\n")
        
        status = response.status_code
        try:
            body_data = response.json() if response.text else {}
        except:
            body_data = response.text if response.text else {}
        
        return (status, body_data)
    except Exception as e:
        import logging
        logging.error(f'Erro ao chamar CATP API: {str(e)}')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"ERROR: {str(e)}\n")
        return (500, {'error': str(e)})
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        session.close()

