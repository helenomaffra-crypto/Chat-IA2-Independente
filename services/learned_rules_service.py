"""
Service para gerenciar regras e definições aprendidas do usuário.

Permite que a mAIke aprenda com exemplos do usuário e aplique essas regras
automaticamente em consultas futuras.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import sqlite3
from db_manager import get_db_connection

logger = logging.getLogger(__name__)


def salvar_regra_aprendida(
    tipo_regra: str,
    contexto: str,
    nome_regra: str,
    descricao: str,
    aplicacao_sql: Optional[str] = None,
    aplicacao_texto: Optional[str] = None,
    exemplo_uso: Optional[str] = None,
    criado_por: Optional[str] = None
) -> Dict[str, Any]:
    """
    Salva uma regra aprendida do usuário.
    
    Exemplo:
        salvar_regra_aprendida(
            tipo_regra='campo_definicao',
            contexto='chegada_processos',
            nome_regra='destfinal como confirmação de chegada',
            descricao='O campo data_destino_final deve ser usado como confirmação de que o processo chegou ao destino final',
            aplicacao_sql='WHERE data_destino_final IS NOT NULL',
            aplicacao_texto='Processos que têm data_destino_final preenchida são considerados como tendo chegado',
            exemplo_uso='Quando perguntar "quais VDM chegaram", usar data_destino_final IS NOT NULL'
        )
    
    Args:
        tipo_regra: Tipo da regra ('campo_definicao', 'regra_negocio', 'preferencia_usuario', etc.)
        contexto: Contexto onde se aplica ('chegada_processos', 'analise_vdm', etc.)
        nome_regra: Nome amigável da regra
        descricao: Descrição completa
        aplicacao_sql: Como aplicar em SQL (opcional)
        aplicacao_texto: Como aplicar em texto (opcional)
        exemplo_uso: Exemplo de quando usar (opcional)
        criado_por: user_id ou session_id (opcional)
        
    Returns:
        Dict com sucesso e id da regra salva
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se já existe regra similar (mesmo tipo, contexto e nome)
        cursor.execute('''
            SELECT id FROM regras_aprendidas 
            WHERE tipo_regra = ? AND contexto = ? AND nome_regra = ?
        ''', (tipo_regra, contexto, nome_regra))
        
        existing = cursor.fetchone()
        
        if existing:
            # Atualizar regra existente
            cursor.execute('''
                UPDATE regras_aprendidas 
                SET descricao = ?,
                    aplicacao_sql = ?,
                    aplicacao_texto = ?,
                    exemplo_uso = ?,
                    atualizado_em = ?,
                    ativa = 1
                WHERE id = ?
            ''', (descricao, aplicacao_sql, aplicacao_texto, exemplo_uso, datetime.now(), existing[0]))
            regra_id = existing[0]
            logger.info(f"✅ Regra atualizada: {nome_regra} (ID: {regra_id})")
        else:
            # Inserir nova regra
            cursor.execute('''
                INSERT INTO regras_aprendidas 
                (tipo_regra, contexto, nome_regra, descricao, aplicacao_sql, 
                 aplicacao_texto, exemplo_uso, criado_por, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                tipo_regra, contexto, nome_regra, descricao, aplicacao_sql,
                aplicacao_texto, exemplo_uso, criado_por, datetime.now(), datetime.now()
            ))
            regra_id = cursor.lastrowid
            logger.info(f"✅ Regra salva: {nome_regra} (ID: {regra_id})")
        
        conn.commit()
        conn.close()
        
        return {
            'sucesso': True,
            'id': regra_id,
            'erro': None
        }
        
    except sqlite3.Error as e:
        logger.error(f"❌ Erro ao salvar regra: {e}")
        return {
            'sucesso': False,
            'id': None,
            'erro': f"Erro ao salvar regra: {str(e)}"
        }
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao salvar regra: {e}", exc_info=True)
        return {
            'sucesso': False,
            'id': None,
            'erro': f"Erro inesperado: {str(e)}"
        }


def buscar_regras_aprendidas(
    contexto: Optional[str] = None,
    tipo_regra: Optional[str] = None,
    ativas: bool = True
) -> List[Dict[str, Any]]:
    """
    Busca regras aprendidas aplicáveis a um contexto.
    
    Args:
        contexto: Contexto específico (ex: 'chegada_processos')
        tipo_regra: Tipo específico de regra (opcional)
        ativas: Se True, retorna apenas regras ativas
        
    Returns:
        Lista de regras aprendidas
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM regras_aprendidas WHERE 1=1'
        params = []
        
        if ativas:
            query += ' AND ativa = 1'
        
        if contexto:
            query += ' AND contexto = ?'
            params.append(contexto)
        
        if tipo_regra:
            query += ' AND tipo_regra = ?'
            params.append(tipo_regra)
        
        query += ' ORDER BY vezes_usado DESC, ultimo_usado_em DESC, criado_em DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar regras: {e}", exc_info=True)
        return []


def incrementar_uso_regra(regra_id: int) -> None:
    """Incrementa contador de uso de uma regra."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE regras_aprendidas 
            SET vezes_usado = vezes_usado + 1,
                ultimo_usado_em = ?
            WHERE id = ?
        ''', (datetime.now(), regra_id))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"⚠️ Erro ao incrementar uso da regra {regra_id}: {e}")


def formatar_regras_para_prompt(regras: List[Dict[str, Any]]) -> str:
    """
    Formata regras aprendidas para incluir no prompt da mAIke.
    
    ⚠️ OTIMIZAÇÃO: Formato compacto para não sobrecarregar o prompt e interferir nos tool calls.
    
    Args:
        regras: Lista de regras aprendidas
        
    Returns:
        String formatada para incluir no prompt
    """
    if not regras:
        return ""
    
    # ✅ OTIMIZAÇÃO: Formato mais compacto para não interferir nos tool calls existentes
    texto = "\n\n📚 **REGRAS APRENDIDAS:**\n"
    
    for regra in regras[:5]:  # Limitar a 5 regras
        texto += f"- **{regra['nome_regra']}**: {regra['descricao']}"
        if regra.get('aplicacao_sql'):
            texto += f" (SQL: {regra['aplicacao_sql']})"
        texto += "\n"
    
    texto += "💡 Aplique essas regras quando fizer sentido.\n"
    
    return texto













