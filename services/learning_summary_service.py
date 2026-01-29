"""
Service para gerar resumo de aprendizado por sessão.

Permite que a mAIke mostre o que aprendeu em uma sessão específica,
incluindo regras aprendidas e consultas salvas criadas.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from db_manager import get_db_connection
import sqlite3

logger = logging.getLogger(__name__)


def obter_resumo_aprendizado_sessao(session_id: str) -> Dict[str, Any]:
    """
    Obtém resumo do que foi aprendido em uma sessão específica.
    
    Args:
        session_id: ID da sessão
    
    Returns:
        Dict com:
        - regras_aprendidas: Lista de regras aprendidas na sessão
        - consultas_salvas: Lista de consultas salvas criadas na sessão
        - total_regras: Número total de regras aprendidas
        - total_consultas: Número total de consultas salvas
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Buscar regras aprendidas da sessão
        cursor.execute('''
            SELECT id, tipo_regra, contexto, nome_regra, descricao, 
                   vezes_usado, criado_em
            FROM regras_aprendidas
            WHERE criado_por = ?
            ORDER BY criado_em DESC
        ''', (session_id,))
        
        regras = [dict(row) for row in cursor.fetchall()]
        
        # Buscar consultas salvas da sessão
        cursor.execute('''
            SELECT id, nome_exibicao, slug, descricao, 
                   vezes_usado, criado_em, regra_aprendida_id
            FROM consultas_salvas
            WHERE criado_por = ?
            ORDER BY criado_em DESC
        ''', (session_id,))
        
        consultas = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'sucesso': True,
            'session_id': session_id,
            'regras_aprendidas': regras,
            'consultas_salvas': consultas,
            'total_regras': len(regras),
            'total_consultas': len(consultas)
        }
        
    except Exception as e:
        logger.error(f'Erro ao obter resumo de aprendizado: {e}', exc_info=True)
        return {
            'sucesso': False,
            'erro': str(e),
            'regras_aprendidas': [],
            'consultas_salvas': [],
            'total_regras': 0,
            'total_consultas': 0
        }


def formatar_resumo_aprendizado(resumo: Dict[str, Any]) -> str:
    """
    Formata resumo de aprendizado em texto legível.
    
    Args:
        resumo: Resultado de obter_resumo_aprendizado_sessao()
    
    Returns:
        Texto formatado do resumo
    """
    if not resumo.get('sucesso'):
        return f"❌ Erro ao obter resumo: {resumo.get('erro', 'Erro desconhecido')}"
    
    texto = f"📚 **Resumo de Aprendizado da Sessão**\n\n"
    
    # Regras aprendidas
    regras = resumo.get('regras_aprendidas', [])
    if regras:
        texto += f"✅ **{len(regras)} Regra(s) Aprendida(s):**\n\n"
        for regra in regras:
            texto += f"• **{regra.get('nome_regra', 'N/A')}**\n"
            texto += f"  - Tipo: {regra.get('tipo_regra', 'N/A')}\n"
            texto += f"  - Contexto: {regra.get('contexto', 'N/A')}\n"
            if regra.get('vezes_usado', 0) > 0:
                texto += f"  - Usada {regra.get('vezes_usado')} vez(es)\n"
            texto += "\n"
    else:
        texto += "ℹ️ Nenhuma regra nova aprendida nesta sessão.\n\n"
    
    # Consultas salvas
    consultas = resumo.get('consultas_salvas', [])
    if consultas:
        texto += f"📊 **{len(consultas)} Consulta(s) Salva(s):**\n\n"
        for consulta in consultas:
            texto += f"• **{consulta.get('nome_exibicao', 'N/A')}**\n"
            texto += f"  - Slug: {consulta.get('slug', 'N/A')}\n"
            if consulta.get('vezes_usado', 0) > 0:
                texto += f"  - Usada {consulta.get('vezes_usado')} vez(es)\n"
            texto += "\n"
    else:
        texto += "ℹ️ Nenhuma consulta nova salva nesta sessão.\n\n"
    
    texto += f"💡 **Total:** {resumo.get('total_regras', 0)} regras e {resumo.get('total_consultas', 0)} consultas aprendidas."
    
    return texto


def incrementar_uso_regra(regra_id: int) -> None:
    """
    Incrementa contador de uso de uma regra aprendida.
    
    Args:
        regra_id: ID da regra aprendida
    """
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
        
        logger.debug(f"✅ Uso da regra {regra_id} incrementado")
        
    except Exception as e:
        logger.warning(f"⚠️ Erro ao incrementar uso da regra {regra_id}: {e}")
