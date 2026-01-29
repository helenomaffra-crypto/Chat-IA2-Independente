"""
Service para gerenciar consultas analíticas salvas (use cases dinâmicos).

Permite salvar consultas SQL ajustadas como "relatórios" reutilizáveis
que podem ser chamados depois por linguagem natural.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import sqlite3
from db_manager import get_db_connection

logger = logging.getLogger(__name__)


def _consulta_existente(slug: str) -> bool:
    """Verifica se já existe uma consulta salva com o slug informado."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM consultas_salvas WHERE slug = ? LIMIT 1', (slug,))
        existe = cursor.fetchone() is not None
        conn.close()
        return existe
    except Exception as e:
        logger.warning(f"⚠️ Erro ao verificar existência de consulta '{slug}': {e}")
        return False


def salvar_consulta_personalizada(
    nome_exibicao: str,
    slug: str,
    descricao: str,
    sql: str,
    parametros: Optional[List[Dict[str, str]]] = None,
    exemplos_pergunta: Optional[str] = None,
    criado_por: Optional[str] = None,
    regra_aprendida_id: Optional[int] = None,  # ✅ NOVO: ID da regra aprendida que influenciou
    contexto_regra: Optional[str] = None  # ✅ NOVO: Contexto da regra
) -> Dict[str, Any]:
    """
    Salva uma consulta analítica como relatório reutilizável.
    
    Args:
        nome_exibicao: Nome amigável (ex: "Atrasos críticos por cliente no ano")
        slug: Identificador único em snake_case (ex: "atrasos_criticos_cliente_ano")
        descricao: Descrição do que o relatório faz
        sql: Query SQL (pode conter placeholders como :ano, :min_dias)
        parametros: Lista de parâmetros esperados [{"nome": "ano", "tipo": "int"}, ...]
        exemplos_pergunta: Frases de exemplo em linguagem natural
        criado_por: user_id ou session_id (opcional)
        
    Returns:
        Dict com:
        - sucesso: bool
        - id: int (ID da consulta salva, se sucesso=True)
        - erro: str (mensagem de erro, se sucesso=False)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validar slug único
        cursor.execute('SELECT id FROM consultas_salvas WHERE slug = ?', (slug,))
        if cursor.fetchone():
            conn.close()
            return {
                'sucesso': False,
                'erro': f"Já existe uma consulta salva com o slug '{slug}'. Use outro nome."
            }
        
        # Preparar dados
        parametros_json = json.dumps(parametros) if parametros else None
        
        # Inserir
        cursor.execute('''
            INSERT INTO consultas_salvas 
            (nome_exibicao, slug, descricao, sql_base, parametros_json, 
             exemplos_pergunta, criado_por, criado_em, atualizado_em,
             regra_aprendida_id, contexto_regra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            nome_exibicao,
            slug,
            descricao,
            sql,
            parametros_json,
            exemplos_pergunta,
            criado_por,
            datetime.now(),
            datetime.now(),
            regra_aprendida_id,  # ✅ NOVO
            contexto_regra  # ✅ NOVO
        ))
        
        consulta_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Consulta salva criada: {slug} (ID: {consulta_id})")
        
        return {
            'sucesso': True,
            'id': consulta_id,
            'erro': None
        }
        
    except sqlite3.Error as e:
        logger.error(f"❌ Erro ao salvar consulta: {e}")
        return {
            'sucesso': False,
            'erro': f"Erro ao salvar consulta: {str(e)}"
        }
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao salvar consulta: {e}", exc_info=True)
        return {
            'sucesso': False,
            'erro': f"Erro inesperado: {str(e)}"
        }


def buscar_consulta_personalizada(texto_pedido_usuario: str) -> Dict[str, Any]:
    """
    Busca uma consulta salva baseada no texto do pedido do usuário.
    
    Tenta encontrar por:
    - slug (se o usuário mencionar um nome similar)
    - nome_exibicao (busca parcial)
    - exemplos_pergunta (busca parcial)
    
    Args:
        texto_pedido_usuario: Texto da pergunta do usuário
        
    Returns:
        Dict com:
        - sucesso: bool
        - consulta: Dict com dados da consulta (se encontrada)
        - erro: str (se não encontrada ou erro)
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        texto_lower = texto_pedido_usuario.lower()
        
        # 1. Buscar por slug (exato ou parcial)
        cursor.execute('''
            SELECT * FROM consultas_salvas 
            WHERE slug LIKE ?
            ORDER BY vezes_usado DESC, criado_em DESC
            LIMIT 1
        ''', (f'%{texto_lower.replace(" ", "_")}%',))
        
        row = cursor.fetchone()
        
        # 2. Se não encontrou, buscar por nome_exibicao
        if not row:
            cursor.execute('''
                SELECT * FROM consultas_salvas 
                WHERE LOWER(nome_exibicao) LIKE ?
                ORDER BY vezes_usado DESC, criado_em DESC
                LIMIT 1
            ''', (f'%{texto_lower}%',))
            row = cursor.fetchone()
        
        # 3. Se ainda não encontrou, buscar por exemplos_pergunta
        if not row:
            cursor.execute('''
                SELECT * FROM consultas_salvas 
                WHERE LOWER(exemplos_pergunta) LIKE ?
                ORDER BY vezes_usado DESC, criado_em DESC
                LIMIT 1
            ''', (f'%{texto_lower}%',))
            row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return {
                'sucesso': False,
                'consulta': None,
                'erro': f"Nenhuma consulta salva encontrada para: '{texto_pedido_usuario}'"
            }
        
        # Converter row para dict
        consulta = dict(row)
        
        # Parse parametros_json
        if consulta.get('parametros_json'):
            try:
                consulta['parametros'] = json.loads(consulta['parametros_json'])
            except json.JSONDecodeError:
                consulta['parametros'] = []
        else:
            consulta['parametros'] = []
        
        # Incrementar contador de uso
        _incrementar_uso_consulta(consulta['id'])
        
        return {
            'sucesso': True,
            'consulta': consulta,
            'erro': None
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar consulta salva: {e}", exc_info=True)
        return {
            'sucesso': False,
            'consulta': None,
            'erro': f"Erro ao buscar consulta: {str(e)}"
        }


def _incrementar_uso_consulta(consulta_id: int) -> None:
    """
    Incrementa contador de uso de uma consulta salva.
    ✅ NOVO: Também incrementa uso da regra aprendida relacionada (se houver).
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Buscar regra_aprendida_id da consulta
        cursor.execute('SELECT regra_aprendida_id FROM consultas_salvas WHERE id = ?', (consulta_id,))
        row = cursor.fetchone()
        regra_id = row[0] if row and row[0] else None
        
        cursor.execute('''
            UPDATE consultas_salvas 
            SET vezes_usado = vezes_usado + 1,
                ultimo_usado_em = ?
            WHERE id = ?
        ''', (datetime.now(), consulta_id))
        
        # ✅ NOVO: Incrementar uso da regra aprendida relacionada (se houver)
        if regra_id:
            try:
                cursor.execute('''
                    UPDATE regras_aprendidas 
                    SET vezes_usado = vezes_usado + 1,
                        ultimo_usado_em = ?
                    WHERE id = ?
                ''', (datetime.now(), regra_id))
                logger.info(f"✅ Uso da regra aprendida {regra_id} incrementado (via consulta {consulta_id})")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao incrementar uso da regra {regra_id}: {e}")
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"⚠️ Erro ao incrementar uso da consulta {consulta_id}: {e}")


def listar_consultas_salvas(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Lista todas as consultas salvas.
    
    Args:
        limit: Limite de resultados
        
    Returns:
        Lista de dicts com dados das consultas salvas
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM consultas_salvas 
            ORDER BY vezes_usado DESC, ultimo_usado_em DESC, criado_em DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        consultas = []
        for row in rows:
            consulta = dict(row)
            # Parse parametros_json
            if consulta.get('parametros_json'):
                try:
                    consulta['parametros'] = json.loads(consulta['parametros_json'])
                except json.JSONDecodeError:
                    consulta['parametros'] = []
            else:
                consulta['parametros'] = []
            consultas.append(consulta)
        
        return consultas
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar consultas salvas: {e}", exc_info=True)
        return []


def ensure_consultas_padrao() -> None:
    """
    Garante que algumas consultas analíticas padrão estejam cadastradas.

    Estas consultas são determinísticas e servem como relatórios iniciais:
    - Processos desembaraçados por mês/categoria
    - Pendências por categoria
    - Atrasos por navio
    """
    consultas_definicoes = [
        {
            "nome_exibicao": "Processos desembaraçados por mês e categoria",
            "slug": "processos_desembaracados_por_mes_categoria",
            "descricao": "Mostra quantidade de processos desembaraçados agrupados por mês e categoria.",
            "sql": (
                "SELECT "
                "strftime('%Y-%m', data_desembaraco) AS mes, "
                "categoria, "
                "COUNT(*) AS qtd_processos "
                "FROM processos "
                "WHERE data_desembaraco IS NOT NULL "
                "GROUP BY mes, categoria "
                "ORDER BY mes DESC, categoria"
            ),
            "exemplos_pergunta": (
                "processos desembaraçados por mês; "
                "quantos processos foram desembaraçados por categoria por mês; "
                "relatório de desembaraço por mês"
            ),
        },
        {
            "nome_exibicao": "Pendências por categoria",
            "slug": "pendencias_por_categoria",
            "descricao": "Agrupa pendências ativas por categoria de processo e tipo de pendência.",
            "sql": (
                "SELECT "
                "categoria, "
                "tipo_pendencia, "
                "COUNT(*) AS qtd_processos "
                "FROM notificacoes_processos "
                "GROUP BY categoria, tipo_pendencia "
                "ORDER BY qtd_processos DESC"
            ),
            "exemplos_pergunta": (
                "pendências por categoria; "
                "quais categorias têm mais pendências; "
                "relatório de pendências por categoria"
            ),
        },
        {
            "nome_exibicao": "Atrasos por navio",
            "slug": "atrasos_por_navio",
            "descricao": "Mostra quantidade de processos e atraso médio em dias por navio.",
            "sql": (
                "SELECT "
                "navio, "
                "COUNT(*) AS qtd_processos, "
                "AVG(dias_atraso) AS media_atraso "
                "FROM processos_kanban "
                "WHERE dias_atraso IS NOT NULL AND dias_atraso > 0 "
                "GROUP BY navio "
                "ORDER BY media_atraso DESC "
                "LIMIT 100"
            ),
            "exemplos_pergunta": (
                "quais navios mais atrasam; "
                "atrasos por navio; "
                "relatório de atraso médio por navio"
            ),
        },
    ]

    for definicao in consultas_definicoes:
        slug = definicao["slug"]
        if _consulta_existente(slug):
            continue

        try:
            resultado = salvar_consulta_personalizada(
                nome_exibicao=definicao["nome_exibicao"],
                slug=slug,
                descricao=definicao["descricao"],
                sql=definicao["sql"],
                parametros=None,
                exemplos_pergunta=definicao["exemplos_pergunta"],
                criado_por="system_seed",
            )
            if resultado.get("sucesso"):
                logger.info(
                    f"✅ Consulta analítica padrão criada: {slug} (ID: {resultado.get('id')})"
                )
            else:
                logger.warning(
                    f"⚠️ Não foi possível criar consulta padrão '{slug}': {resultado.get('erro')}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Erro ao garantir consulta padrão '{slug}': {e}")
