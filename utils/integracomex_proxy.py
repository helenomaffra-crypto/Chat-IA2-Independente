# -*- coding: utf-8 -*-
"""
Utils - Integra Comex Proxy
============================
Funções para fazer requisições HTTP à API Integra Comex (SERPRO).

⚠️ ATENÇÃO: A API Integra Comex é BILHETADA (paga por consulta).
Use a API pública gratuita (siscarga_publica.py) para verificar
data da última alteração antes de consultar esta API.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

import requests

# Importar módulos com tratamento de erro (podem não estar disponíveis)
try:
    import integracomex_auth
    from duimp_request import build_session
    import duimp_auth
except ImportError:
    # Se não conseguir importar, tentar importar do diretório raiz
    import importlib.util
    import sys
    from pathlib import Path
    
    root_dir = Path(__file__).parent.parent
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    
    # Tentar carregar integracomex_auth.py do diretório raiz
    integracomex_auth_path = root_dir / 'integracomex_auth.py'
    if integracomex_auth_path.exists():
        spec = importlib.util.spec_from_file_location("integracomex_auth", integracomex_auth_path)
        integracomex_auth = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(integracomex_auth)
    else:
        # Se não encontrar, definir como None e deixar o erro ser tratado na função call_integracomex
        integracomex_auth = None
    
    # Tentar carregar duimp_auth.py do diretório raiz
    duimp_auth_path = root_dir / 'duimp_auth.py'
    if duimp_auth_path.exists():
        spec = importlib.util.spec_from_file_location("duimp_auth", duimp_auth_path)
        duimp_auth = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(duimp_auth)
    else:
        # Se não encontrar, definir como None e deixar o erro ser tratado na função call_integracomex
        duimp_auth = None
    
    # Tentar carregar duimp_request também
    duimp_request_path = root_dir / 'duimp_request.py'
    if duimp_request_path.exists():
        spec = importlib.util.spec_from_file_location("duimp_request", duimp_request_path)
        duimp_request = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(duimp_request)
        build_session = duimp_request.build_session
    else:
        # Se não encontrar, definir como None e deixar o erro ser tratado na função call_integracomex
        build_session = None


def call_integracomex(
    path: str,
    query: Optional[Dict[str, Any]] = None,
    accept: str = 'application/json',
    method: str = 'GET',
    body: Optional[Dict[str, Any]] = None,
    base_url_override: Optional[str] = None,
    usou_api_publica_antes: bool = False,
    processo_referencia: Optional[str] = None,
    return_headers: bool = False,
) -> Tuple[int, Any]:
    """
    Função auxiliar para fazer requisições HTTP à API Integra Comex.
    Gerencia automaticamente autenticação OAuth2 e tokens.
    
    ⚠️ ATENÇÃO: Esta API é BILHETADA (paga por consulta).
    Antes de usar, SEMPRE verifique a data da última alteração
    usando a API pública gratuita (utils.siscarga_publica).
    
    ✅ SIMPLIFICADO: Verificação simples de duplicata (últimos 5 minutos)
    Se já foi consultado recentemente, retorna RuntimeError com prefixo 'DUPLICATA:'
    
    Args:
        path: Caminho da API (ex: '/carga/conhecimento-embarque')
        query: Query parameters (opcional)
        accept: Content-Type aceito (padrão: 'application/json')
        method: Método HTTP (GET, POST, PUT, PATCH, DELETE)
        body: Body da requisição (para POST/PUT/PATCH)
        base_url_override: Base URL alternativa (opcional, usado para DI que tem base URL diferente)
        usou_api_publica_antes: Se True, indica que a API pública foi verificada antes desta consulta bilhetada
    
    Returns:
        Tuple[int, Any]: (status_code, response_body)
        
    Raises:
        RuntimeError: Se já foi consultado nos últimos 5 minutos (prefixo 'DUPLICATA:')
    """
    # Verificar se integracomex_auth está disponível
    if integracomex_auth is None:
        raise RuntimeError("integracomex_auth não está disponível. Verifique se integracomex_auth.py existe no diretório raiz do projeto.")
    
    settings = integracomex_auth.load_integracomex_settings()
    
    # ✅ Se base_url_override foi fornecido, usar ele (para DI que usa base URL diferente)
    if base_url_override:
        settings.base_url = base_url_override
    
    # ✅ Obter token OAuth2 conforme documentação oficial
    token_data = integracomex_auth.obtain_integracomex_token(settings)
    
    access_token = token_data.get('access_token', '')
    token_type = token_data.get('token_type', 'Bearer')
    jwt_token = token_data.get('jwt_token') or access_token  # Fallback para access_token
    
    if not access_token:
        raise RuntimeError('Não foi possível obter access_token do Integra Comex.')
    
    # Preparar certificado para mTLS (mesmo da DUIMP)
    if duimp_auth is None:
        raise ImportError("duimp_auth não está disponível. Verifique se duimp_auth.py existe no diretório raiz do projeto.")
    
    if build_session is None:
        raise ImportError("build_session não está disponível. Verifique se duimp_request.py existe no diretório raiz do projeto.")
    
    duimp_settings = duimp_auth.load_settings()
    duimp_settings.pfx_path = settings.cert_pfx
    duimp_settings.pfx_password = settings.cert_password
    
    # Usar build_session da DUIMP para manter consistência
    session = build_session(duimp_settings)
    
    # ✅ Headers conforme documentação oficial
    headers = {
        'Authorization': f'{token_type} {access_token}',
        'jwt_token': jwt_token,
        'Accept': accept or 'application/json',
    }
    
    # Se for POST/PUT, adicionar Content-Type para JSON
    if method in ('POST', 'PUT', 'PATCH') and body is not None:
        headers['Content-Type'] = 'application/json'
    
    # Construir URL completa
    url = urljoin(settings.base_url.rstrip('/') + '/', path.lstrip('/'))
    
    # ✅ SIMPLIFICADO: Verificação simples de duplicata (apenas para CE/DI)
    tipo_consulta = 'Outro'
    numero_documento = None
    
    # Detectar tipo e número do documento
    # ✅ CORREÇÃO: Diferenciar entre CE (resumo) e CE_ITENS (detalhes)
    if '/conhecimentos-embarque' in path or '/conhecimento-embarque' in path or '/carga/conhecimento-embarque' in path:
        import re
        # Verificar se é consulta de itens (detalhes) ou resumo
        if '/itens/' in path or path.endswith('/itens'):
            tipo_consulta = 'CE_ITENS'  # Consulta de itens (detalhes)
        else:
            tipo_consulta = 'CE'  # Consulta de resumo
        
        # ✅ CORREÇÃO: Melhorar regex para capturar número do CE corretamente
        # Tentar primeiro padrão mais específico: /conhecimentos-embarque/{numero}
        match = re.search(r'conhecimentos?-embarque[^/]*/(\d+)', path)
        if not match:
            # Tentar padrão mais genérico: qualquer número no final do path após conhecimentos-embarque
            match = re.search(r'conhecimentos?-embarque.*?/(\d+)(?:/|$)', path)
        if not match:
            # Último recurso: buscar qualquer número no path após conhecimentos-embarque
            parts = path.split('conhecimentos-embarque')
            if len(parts) > 1:
                match = re.search(r'/(\d+)(?:/|$)', parts[-1])
            else:
                # Tentar padrão genérico: último número no path
                match = re.search(r'/(\d+)(?:/|$)', path)
        if match:
            numero_documento = match.group(1)
    elif '/declaracao-importacao' in path or '/di/' in path:
        tipo_consulta = 'DI'
        import re
        match = re.search(r'/(\d+)(?:/|$)', path)
        if match:
            numero_documento = match.group(1)
    
    # ✅ Verificação simples: se já consultou nos últimos 5 minutos, retornar erro
    # ✅ CORREÇÃO: CE_ITENS (consulta de itens) não é bloqueada - permite consultas repetidas
    # ✅ CE (resumo) e DI continuam bloqueados para evitar custos desnecessários
    if tipo_consulta in ('CE', 'DI') and numero_documento:
        try:
            from db_manager import get_db_connection
            import sqlite3
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM consultas_bilhetadas
                WHERE tipo_consulta = ?
                AND numero_documento = ?
                AND data_consulta >= datetime('now', '-5 minutes')
                AND sucesso = 1
            ''', (tipo_consulta, numero_documento))
            count = cursor.fetchone()[0]
            conn.close()
            
            if count > 0:
                import logging
                logging.info(f'⚠️ {tipo_consulta} {numero_documento} já foi consultado bilhetado nos últimos 5 minutos. Retornando erro DUPLICATA.')
                raise RuntimeError(f'DUPLICATA: {tipo_consulta} {numero_documento} já foi consultado nos últimos 5 minutos')
        except RuntimeError:
            raise  # Re-raise DUPLICATA
        except Exception as e:
            import logging
            logging.warning(f'Erro ao verificar duplicata para {tipo_consulta} {numero_documento}: {e}. Continuando...')
            # Continuar mesmo com erro na verificação
    
    # Fazer requisição HTTP
    try:
        if method in ('POST', 'PUT', 'PATCH'):
            response = session.request(
                method, url, params=query, headers=headers, json=body, timeout=60
            )
        else:
            response = session.request(
                method, url, params=query, headers=headers, timeout=60
            )
    except requests.exceptions.RequestException as e:
        # Log erro
        log_path = Path('debug_log.txt')
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"ERROR: {str(e)}\n--- END REQUEST ---\n\n")
        except:
            pass
        raise RuntimeError(f"Erro na requisição Integra Comex: {e}")
    
    # Processar resposta
    status_code = response.status_code
    
    # Tentar parsear JSON
    try:
        if response.text:
            body_data = response.json()
        else:
            body_data = None
    except json.JSONDecodeError:
        body_data = response.text
    
    # ✅ Registrar consulta bilhetada no banco de dados
    try:
        from db_manager import registrar_consulta_bilhetada
        
        # Detectar tipo se não detectou antes
        if tipo_consulta == 'Outro':
            if '/manifestos/' in path:
                tipo_consulta = 'Manifesto'
                import re
                match = re.search(r'/manifestos/(\d+)', path)
                if match:
                    numero_documento = match.group(1)
            elif '/escalas/' in path:
                tipo_consulta = 'Escala'
                import re
                match = re.search(r'/escalas/(\d+)', path)
                if match:
                    numero_documento = match.group(1)
            elif '/carga-aerea' in path or '/cct' in path or '/conhecimento-carga-aerea' in path:
                tipo_consulta = 'CCT'
                import re
                match = re.search(r'/(\d+)(?:/|$)', path)
                if match:
                    numero_documento = match.group(1)
        
        # Registrar consulta (usou_api_publica_antes e processo_referencia vêm do parâmetro passado pelo chamador)
        registrar_consulta_bilhetada(
            tipo_consulta=tipo_consulta,
            endpoint=path,
            metodo=method,
            status_code=status_code,
            sucesso=(status_code == 200),
            numero_documento=numero_documento,
            processo_referencia=processo_referencia,  # ✅ Passar processo_referencia se fornecido
            usou_api_publica_antes=usou_api_publica_antes  # ✅ Usar valor passado pelo chamador
        )
    except Exception as e:
        # Não falhar a requisição se o registro falhar
        import logging
        logging.warning(f'Erro ao registrar consulta bilhetada: {e}')
    
    # ✅ NOVO: Gravar histórico de mudanças se resposta for de documento aduaneiro
    if status_code == 200 and body_data and isinstance(body_data, dict):
        try:
            _gravar_historico_se_documento(
                path=path,
                response_body=body_data,
                processo_referencia=processo_referencia,
                fonte_dados='INTEGRACOMEX',
                api_endpoint=path
            )
        except Exception as e:
            # Não bloquear se houver erro no histórico
            import logging
            logging.warning(f'⚠️ Erro ao gravar histórico de documento: {e}')
    
    if return_headers:
        try:
            return status_code, body_data, dict(response.headers)
        except Exception:
            return status_code, body_data, {}

    return status_code, body_data


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
        
        # CE (Conhecimento de Embarque)
        if '/conhecimento-embarque' in path or '/conhecimentos-embarque' in path:
            tipo_documento = 'CE'
            import re
            # Extrair número do CE do path
            match = re.search(r'conhecimentos?-embarque[^/]*/(\d+)', path)
            if not match:
                match = re.search(r'/(\d+)(?:/|$)', path)
            if match:
                numero_documento = match.group(1)
            # Se não encontrou no path, tentar no response_body
            if not numero_documento:
                numero_documento = response_body.get('numeroCE') or response_body.get('numero_ce')
        
        # DI (Declaração de Importação)
        elif '/declaracao-importacao' in path or '/di/' in path:
            tipo_documento = 'DI'
            import re
            # Extrair número da DI do path
            match = re.search(r'/(\d+)(?:/|$)', path)
            if match:
                numero_documento = match.group(1)
            # Se não encontrou no path, tentar no response_body
            if not numero_documento:
                numero_documento = response_body.get('numeroDI') or response_body.get('numero_di')
        
        # CCT (Conhecimento de Carga Aérea)
        elif '/conhecimento-carga-aerea' in path or '/carga-aerea' in path or '/cct' in path:
            tipo_documento = 'CCT'
            import re
            # Extrair número do CCT do path
            match = re.search(r'/(\d+)(?:/|$)', path)
            if match:
                numero_documento = match.group(1)
            # Se não encontrou no path, tentar no response_body
            if not numero_documento:
                numero_documento = response_body.get('numeroCCT') or response_body.get('numero_cct') or response_body.get('awb')
        
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
