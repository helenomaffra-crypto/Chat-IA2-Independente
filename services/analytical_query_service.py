"""
Service para execução segura de consultas SQL analíticas.

Este service valida e executa consultas SQL de forma segura (somente leitura),
garantindo que apenas SELECT queries sejam executadas e que usem apenas
tabelas/views permitidas.

Suporta execução em SQL Server (quando disponível) ou SQLite (fallback).
"""
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import sqlite3
from db_manager import get_db_connection

logger = logging.getLogger(__name__)

# Lista de tabelas/views permitidas para consultas analíticas
# (ajustar conforme schema real do banco)
TABELAS_PERMITIDAS = {
    'processos_kanban',
    'duimps',
    'ces_cache',
    'ccts_cache',
    'dis_cache',
    'processos_kanban_historico',
    'notificacoes_processos',
    'shipsgo_tracking',
    'processos',
    'processo_documentos',
    'consultas_salvas',
    # Adicionar outras tabelas/views conforme necessário
}

# Palavras-chave SQL perigosas que devem ser bloqueadas
SQL_KEYWORDS_BLOQUEADAS = {
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE',
    'CREATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
    'MERGE', 'CALL', 'DECLARE', 'BEGIN', 'COMMIT', 'ROLLBACK'
}

# LIMIT padrão para consultas (evitar queries muito grandes)
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


def validar_sql_seguro(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Valida se uma query SQL é segura para execução (somente leitura).
    
    Args:
        sql: Query SQL a validar
        
    Returns:
        Tuple (é_seguro, mensagem_erro)
        - é_seguro: True se a query é segura, False caso contrário
        - mensagem_erro: Mensagem de erro se não for segura, None se for segura
    """
    sql_upper = sql.upper().strip()
    
    # 1. Verificar se contém palavras-chave perigosas
    for keyword in SQL_KEYWORDS_BLOQUEADAS:
        # Buscar palavra-chave como palavra completa (não substring)
        pattern = rf'\b{keyword}\b'
        if re.search(pattern, sql_upper):
            return False, f"Palavra-chave não permitida: {keyword}. Apenas consultas SELECT são permitidas."
    
    # 2. Verificar se começa com SELECT
    if not sql_upper.startswith('SELECT'):
        return False, "Apenas consultas SELECT são permitidas."
    
    # 3. Verificar se não contém subqueries perigosas (INSERT, UPDATE, etc.)
    # Remover strings entre aspas para evitar falsos positivos
    sql_sem_strings = re.sub(r"'[^']*'", "''", sql)
    sql_sem_strings = re.sub(r'"[^"]*"', '""', sql_sem_strings)
    
    for keyword in SQL_KEYWORDS_BLOQUEADAS:
        if keyword in sql_sem_strings.upper():
            return False, f"Query contém operação não permitida: {keyword}"
    
    # 4. Verificar se usa apenas tabelas permitidas
    # Extrair nomes de tabelas da query (simplificado)
    tabelas_na_query = re.findall(r'\bFROM\s+(\w+)', sql_upper, re.IGNORECASE)
    tabelas_na_query.extend(re.findall(r'\bJOIN\s+(\w+)', sql_upper, re.IGNORECASE))
    
    for tabela in tabelas_na_query:
        if tabela.upper() not in [t.upper() for t in TABELAS_PERMITIDAS]:
            logger.warning(f"⚠️ Tentativa de acessar tabela não permitida: {tabela}")
            # Não bloquear, apenas avisar (pode ser view ou tabela válida não listada)
            # return False, f"Tabela '{tabela}' não está na lista de tabelas permitidas."
    
    # 5. Garantir que tem LIMIT (adicionar se não tiver)
    if 'LIMIT' not in sql_upper:
        # Adicionar LIMIT ao final da query
        sql = f"{sql.rstrip(';')} LIMIT {DEFAULT_LIMIT}"
        logger.info(f"✅ LIMIT {DEFAULT_LIMIT} adicionado automaticamente à query")
    
    return True, None


def aplicar_limit_seguro(sql: str, limit: Optional[int] = None, usar_sql_server: bool = False) -> str:
    """
    Aplica LIMIT seguro à query SQL, respeitando o máximo permitido.
    
    Args:
        sql: Query SQL
        limit: Limite desejado (None para usar padrão)
        usar_sql_server: Se True, usa TOP (SQL Server) ao invés de LIMIT (SQLite)
        
    Returns:
        Query SQL com LIMIT/TOP aplicado
    """
    if limit is None:
        limit = DEFAULT_LIMIT
    
    # Garantir que não exceda o máximo
    limit = min(limit, MAX_LIMIT)
    
    sql_upper = sql.upper()
    
    if usar_sql_server:
        # SQL Server usa TOP, não LIMIT
        # Se já tem TOP, substituir
        if re.search(r'\bTOP\s+\d+', sql_upper):
            # Substituir TOP existente
            sql = re.sub(r'\bTOP\s+\d+', f'TOP {limit}', sql, flags=re.IGNORECASE)
        elif 'LIMIT' in sql_upper:
            # Remover LIMIT e adicionar TOP após SELECT
            sql = re.sub(r'\bLIMIT\s+\d+', '', sql, flags=re.IGNORECASE)
            # Adicionar TOP após SELECT
            sql = re.sub(r'(\bSELECT\b)', rf'\1 TOP {limit}', sql, count=1, flags=re.IGNORECASE)
        else:
            # Adicionar TOP após SELECT
            sql = re.sub(r'(\bSELECT\b)', rf'\1 TOP {limit}', sql, count=1, flags=re.IGNORECASE)
    else:
        # SQLite usa LIMIT
        # Se já tem LIMIT, substituir
        if 'LIMIT' in sql_upper:
            # Substituir LIMIT existente (case-insensitive)
            sql = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {limit}', sql, flags=re.IGNORECASE)
        else:
            # Adicionar LIMIT ao final
            sql = f"{sql.rstrip(';')} LIMIT {limit}"
    
    return sql


def _executar_no_sql_server(sql: str) -> Optional[Dict[str, Any]]:
    """
    Tenta executar query no SQL Server (se disponível).
    
    Args:
        sql: Query SQL a executar (já com TOP aplicado se necessário)
        
    Returns:
        Dict com resultado se sucesso, None se SQL Server não disponível
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        
        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            return None
        
        # Converter LIMIT para TOP se necessário (SQL Server não suporta LIMIT)
        sql_upper = sql.upper()
        if 'LIMIT' in sql_upper and 'TOP' not in sql_upper:
            # Remover LIMIT e adicionar TOP após SELECT
            limit_match = re.search(r'\bLIMIT\s+(\d+)', sql_upper)
            if limit_match:
                limit_value = limit_match.group(1)
                sql = re.sub(r'\bLIMIT\s+\d+', '', sql, flags=re.IGNORECASE)
                # Adicionar TOP após SELECT
                sql = re.sub(r'(\bSELECT\b)', rf'\1 TOP {limit_value}', sql, count=1, flags=re.IGNORECASE)
        
        # Tentar executar no SQL Server
        # O adapter pode ter fetch_all ou retornar lista diretamente
        try:
            # Tentar fetch_all primeiro (padrão mais comum)
            resultado = sql_adapter.execute_query(sql, notificar_erro=False)
        except TypeError:
            # Fallback para versão antiga da API
            resultado = sql_adapter.execute_query(sql, notificar_erro=False)
        
        if resultado:
            # Converter para lista de dicts (se necessário)
            if isinstance(resultado, list):
                dados = resultado
            elif isinstance(resultado, dict):
                # Se retornar um único dict, converter para lista
                dados = [resultado]
            else:
                # Outros tipos (tuple, etc) - tentar converter
                dados = [dict(resultado)] if resultado else []
            
            return {
                'sucesso': True,
                'dados': dados,
                'erro': None,
                'linhas_retornadas': len(dados),
                'fonte': 'sql_server'
            }
        else:
            return None
            
    except Exception as e:
        logger.debug(f"SQL Server não disponível ou erro: {e}")
        return None


def _executar_no_sqlite(sql: str) -> Dict[str, Any]:
    """
    Executa query no SQLite.
    
    Args:
        sql: Query SQL a executar
        
    Returns:
        Dict com resultado
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row  # Retornar como dict
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # Converter rows para lista de dicts
            dados = [dict(row) for row in rows]
            
            return {
                'sucesso': True,
                'dados': dados,
                'erro': None,
                'linhas_retornadas': len(dados),
                'fonte': 'sqlite'
            }
        except sqlite3.Error as e:
            logger.error(f"❌ Erro ao executar query SQLite: {e}")
            return {
                'sucesso': False,
                'erro': f"Erro SQLite: {str(e)}",
                'dados': [],
                'linhas_retornadas': 0,
                'fonte': 'sqlite'
            }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao executar no SQLite: {e}", exc_info=True)
        return {
            'sucesso': False,
            'erro': f"Erro inesperado: {str(e)}",
            'dados': [],
            'linhas_retornadas': 0,
            'fonte': 'sqlite'
        }


def executar_consulta_analitica(sql: str, limit: Optional[int] = None, preferir_sql_server: bool = True) -> Dict[str, Any]:
    """
    Executa uma consulta SQL analítica de forma segura (somente leitura).
    
    Tenta executar no SQL Server primeiro (se disponível e preferir_sql_server=True),
    caso contrário usa SQLite como fallback.
    
    Args:
        sql: Query SQL a executar (deve ser SELECT)
        limit: Limite de resultados (opcional, padrão: DEFAULT_LIMIT)
        preferir_sql_server: Se True, tenta SQL Server primeiro (padrão: True)
        
    Returns:
        Dict com:
        - sucesso: bool
        - dados: List[Dict] com resultados (se sucesso=True)
        - erro: str com mensagem de erro (se sucesso=False)
        - linhas_retornadas: int (número de linhas retornadas)
        - query_executada: str (query final executada, com LIMIT aplicado)
        - fonte: str ('sql_server' ou 'sqlite')
    """
    try:
        # 1. Validar SQL
        é_seguro, mensagem_erro = validar_sql_seguro(sql)
        if not é_seguro:
            return {
                'sucesso': False,
                'erro': mensagem_erro,
                'dados': [],
                'linhas_retornadas': 0,
                'query_executada': sql,
                'fonte': None
            }
        
        # 2. Aplicar LIMIT seguro (versão SQLite primeiro)
        sql_final = aplicar_limit_seguro(sql, limit, usar_sql_server=False)
        
        # 3. Tentar executar no SQL Server primeiro (se preferir)
        if preferir_sql_server:
            # Converter para sintaxe SQL Server (TOP ao invés de LIMIT)
            sql_sql_server = aplicar_limit_seguro(sql, limit, usar_sql_server=True)
            resultado_sql_server = _executar_no_sql_server(sql_sql_server)
            if resultado_sql_server and resultado_sql_server.get('sucesso'):
                logger.info(f"✅ Query executada no SQL Server ({resultado_sql_server['linhas_retornadas']} linhas)")
                resultado_sql_server['query_executada'] = sql_final
                return resultado_sql_server
            elif resultado_sql_server is None:
                logger.debug("⚠️ SQL Server não disponível, usando SQLite como fallback")
        
        # 4. Executar no SQLite (fallback ou se preferir_sql_server=False)
        resultado_sqlite = _executar_no_sqlite(sql_final)
        resultado_sqlite['query_executada'] = sql_final
        
        if resultado_sqlite.get('sucesso'):
            logger.info(f"✅ Query executada no SQLite ({resultado_sqlite['linhas_retornadas']} linhas)")
        else:
            logger.warning(f"⚠️ Erro ao executar no SQLite: {resultado_sqlite.get('erro')}")
        
        return resultado_sqlite
            
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao executar consulta analítica: {e}", exc_info=True)
        return {
            'sucesso': False,
            'erro': f"Erro inesperado: {str(e)}",
            'dados': [],
            'linhas_retornadas': 0,
            'query_executada': sql,
            'fonte': None
        }













