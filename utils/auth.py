# -*- coding: utf-8 -*-
"""
Utils - Autenticação
====================
Funções relacionadas à autenticação no Portal Único Siscomex.
"""

import os
import sys
from pathlib import Path
from typing import Tuple

# Adicionar diretório raiz ao path para importar duimp_auth
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    import duimp_auth
except ImportError:
    # Se não conseguir importar, tentar importar do diretório raiz
    import importlib.util
    duimp_auth_path = root_dir / 'duimp_auth.py'
    if duimp_auth_path.exists():
        spec = importlib.util.spec_from_file_location("duimp_auth", duimp_auth_path)
        duimp_auth = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(duimp_auth)
    else:
        raise ImportError("duimp_auth.py não encontrado no diretório raiz")


def ensure_tokens(settings) -> Tuple[str, str]:
    """
    Obtém tokens de autenticação (Set-Token e X-CSRF-Token) necessários para
    fazer requisições à API do Portal Único Siscomex.
    
    ⚠️ CRÍTICO: Esta função é chamada automaticamente por todas as outras funções
    que fazem requisições ao Portal Único.
    
    Args:
        settings: Configurações de autenticação (duimp_auth.Settings)
    
    Returns:
        Tuple[str, str]: (set_token, csrf_token)
    
    Raises:
        RuntimeError: Se não conseguir obter tokens após refresh
    """
    def _get():
        tp = duimp_auth.obtain_tokens(settings)
        return tp.get('setToken'), tp.get('csrfToken')

    set_token, csrf_token = _get()
    if set_token and csrf_token:
        return set_token, csrf_token

    old = os.environ.get('DUIMP_FORCE_REFRESH')
    os.environ['DUIMP_FORCE_REFRESH'] = 'true'
    try:
        set_token, csrf_token = _get()
    finally:
        if old is None:
            os.environ.pop('DUIMP_FORCE_REFRESH', None)
        else:
            os.environ['DUIMP_FORCE_REFRESH'] = old

    if not set_token or not csrf_token:
        raise RuntimeError('Tokens não encontrados após refresh.')
    return set_token, csrf_token


def get_effective_base_url() -> str:
    """
    Obtém a URL base efetiva do Portal Único.
    
    Returns:
        str: URL base (padrão: https://portalunico.siscomex.gov.br)
    """
    return os.environ.get('PUCOMEX_BASE_URL', 'https://portalunico.siscomex.gov.br').strip()

