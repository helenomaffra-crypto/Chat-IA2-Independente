"""
Service para gerenciar contexto persistente de sessão.

Permite que a mAIke mantenha contexto entre mensagens, como processos mencionados,
categorias em foco, etc.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import sqlite3
from db_manager import get_db_connection

logger = logging.getLogger(__name__)


def salvar_contexto_sessao(
    session_id: str,
    tipo_contexto: str,
    chave: str,
    valor: str,
    dados_adicionais: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Salva contexto de sessão (ex: processo mencionado, categoria em foco).
    
    Args:
        session_id: ID da sessão
        tipo_contexto: Tipo ('processo_atual', 'categoria_atual', 'ultima_consulta', etc.)
        chave: Chave do contexto
        valor: Valor do contexto
        dados_adicionais: Dados adicionais em dict (opcional)
        
    Returns:
        True se salvou com sucesso
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        dados_json = json.dumps(dados_adicionais) if dados_adicionais else None
        
        # Usar INSERT OR REPLACE para atualizar se já existe
        cursor.execute('''
            INSERT OR REPLACE INTO contexto_sessao 
            (session_id, tipo_contexto, chave, valor, dados_json, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, tipo_contexto, chave, valor, dados_json, datetime.now()))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar contexto: {e}", exc_info=True)
        return False


def buscar_contexto_sessao(
    session_id: str,
    tipo_contexto: Optional[str] = None,
    chave: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Busca contexto de sessão.
    
    Args:
        session_id: ID da sessão
        tipo_contexto: Tipo específico (opcional)
        chave: Chave específica (opcional)
        
    Returns:
        Lista de contextos encontrados
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM contexto_sessao WHERE session_id = ?'
        params = [session_id]
        
        if tipo_contexto:
            query += ' AND tipo_contexto = ?'
            params.append(tipo_contexto)
        
        if chave:
            query += ' AND chave = ?'
            params.append(chave)
        
        query += ' ORDER BY atualizado_em DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        contextos = []
        for row in rows:
            ctx = dict(row)
            # Parse dados_json
            if ctx.get('dados_json'):
                try:
                    ctx['dados'] = json.loads(ctx['dados_json'])
                except json.JSONDecodeError:
                    ctx['dados'] = {}
            else:
                ctx['dados'] = {}
            contextos.append(ctx)
        
        return contextos
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar contexto: {e}", exc_info=True)
        return []


def limpar_contexto_sessao(session_id: str, tipo_contexto: Optional[str] = None) -> bool:
    """
    Limpa contexto de sessão.
    
    Args:
        session_id: ID da sessão
        tipo_contexto: Tipo específico para limpar (opcional, se None limpa tudo)
        
    Returns:
        True se limpou com sucesso
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if tipo_contexto:
            cursor.execute('DELETE FROM contexto_sessao WHERE session_id = ? AND tipo_contexto = ?', 
                         (session_id, tipo_contexto))
        else:
            cursor.execute('DELETE FROM contexto_sessao WHERE session_id = ?', (session_id,))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao limpar contexto: {e}", exc_info=True)
        return False


def obter_contexto_formatado_para_usuario(session_id: str) -> str:
    """
    Obtém contexto formatado para exibir ao usuário quando ele pergunta sobre o contexto.
    
    ⚠️ IMPORTANTE: Esta função retorna APENAS o que está realmente salvo no contexto de sessão,
    sem inferir ou inventar informações detalhadas.
    
    Args:
        session_id: ID da sessão
        
    Returns:
        String formatada com o contexto real
    """
    contextos = buscar_contexto_sessao(session_id)
    if not contextos:
        return "Nenhum contexto salvo no momento."
    
    partes = []
    for ctx in contextos:
        tipo = ctx.get('tipo_contexto', '')
        valor = ctx.get('valor', '')
        dados = ctx.get('dados', {})
        
        if tipo == 'processo_atual':
            partes.append(f"Processo: {valor}")
        elif tipo == 'categoria_atual':
            partes.append(f"Categoria: {valor}")
        elif tipo == 'ultima_consulta':
            chave = ctx.get('chave', '')
            if chave == 'extrato_bancario':
                banco = dados.get('banco', '')
                total_transacoes = dados.get('total_transacoes', 0)
                partes.append(f"Última consulta: Extrato {banco} ({total_transacoes} transações)")
            else:
                partes.append(f"Última consulta: {valor}")
    
    if partes:
        return "\n".join(partes)
    return "Nenhum contexto salvo no momento."


def formatar_contexto_para_prompt(contextos: List[Dict[str, Any]]) -> str:
    """
    Formata contexto de sessão para incluir no prompt da mAIke.
    
    ⚠️ OTIMIZAÇÃO: Formato compacto para não sobrecarregar o prompt e interferir nos tool calls.
    
    Args:
        contextos: Lista de contextos
        
    Returns:
        String formatada para incluir no prompt
    """
    if not contextos:
        return ""
    
    # ✅ OTIMIZAÇÃO: Formato mais compacto para não interferir nos tool calls existentes
    texto = "\n\n📌 **CONTEXTO:** "
    
    # Agrupar por tipo_contexto
    contextos_por_tipo = {}
    for ctx in contextos:
        tipo = ctx['tipo_contexto']
        if tipo not in contextos_por_tipo:
            contextos_por_tipo[tipo] = []
        contextos_por_tipo[tipo].append(ctx)
    
    partes = []
    for tipo, lista in contextos_por_tipo.items():
        if tipo == 'processo_atual':
            for ctx in lista:
                partes.append(f"Processo: {ctx['valor']}")
        elif tipo == 'categoria_atual':
            for ctx in lista:
                partes.append(f"Categoria: {ctx['valor']}")
        elif tipo == 'ultima_consulta':
            for ctx in lista:
                chave = ctx.get('chave', '')
                valor = ctx.get('valor', '')
                dados = ctx.get('dados', {})
                
                # ✅ NOVO: Formatação específica para extratos bancários
                if chave == 'extrato_bancario':
                    banco = dados.get('banco', '')
                    total_transacoes = dados.get('total_transacoes', 0)
                    partes.append(f"Última consulta: Extrato {banco} ({total_transacoes} transações)")
                else:
                    partes.append(f"Última: {valor}")
    
    if partes:
        texto += ", ".join(partes) + "\n"
        texto += "💡 Use esse contexto APENAS se a mensagem do usuário for relacionada ao processo/categoria mencionado.\n"
        texto += "⚠️ Se o usuário mencionar outro processo ou fizer pergunta genérica (ex: 'teste', 'oi'), IGNORE este contexto.\n"
        texto += "⚠️ Se o usuário fizer pergunta conceitual (ex: 'o que é uma DI?', 'vc sabe o que é um CE?'), IGNORE este contexto e responda de forma genérica.\n"
    
    return texto













