"""
Service para observabilidade - relatórios de uso de IA, bilhetadas e aprendizado.

Permite gerar relatórios sobre:
- Uso de consultas bilhetadas (custo, quantidade)
- Uso de consultas salvas
- Uso de regras aprendidas
- Chamadas de IA por modelo
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from db_manager import get_db_connection
import sqlite3

logger = logging.getLogger(__name__)


def obter_relatorio_consultas_bilhetadas(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    agrupar_por: str = 'dia'  # 'dia', 'semana', 'mes'
) -> Dict[str, Any]:
    """
    Gera relatório de uso de consultas bilhetadas.
    
    Args:
        data_inicio: Data de início (YYYY-MM-DD) ou None para últimos 30 dias
        data_fim: Data de fim (YYYY-MM-DD) ou None para hoje
        agrupar_por: Como agrupar ('dia', 'semana', 'mes')
    
    Returns:
        Dict com estatísticas de consultas bilhetadas
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Calcular datas se não fornecidas
        if not data_fim:
            data_fim = datetime.now().strftime('%Y-%m-%d')
        if not data_inicio:
            data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Query base
        if agrupar_por == 'dia':
            group_by = "DATE(data_consulta)"
            date_format = "%d/%m/%Y"
        elif agrupar_por == 'semana':
            group_by = "strftime('%Y-W%W', data_consulta)"
            date_format = "Semana %W/%Y"
        else:  # mes
            group_by = "strftime('%Y-%m', data_consulta)"
            date_format = "%m/%Y"
        
        cursor.execute(f'''
            SELECT 
                {group_by} as periodo,
                COUNT(*) as total_consultas,
                SUM(CASE WHEN sucesso = 1 THEN 1 ELSE 0 END) as consultas_sucesso,
                SUM(CASE WHEN usou_api_publica_antes = 1 THEN 1 ELSE 0 END) as consultas_com_verificacao,
                tipo_consulta,
                COUNT(DISTINCT processo_referencia) as processos_unicos
            FROM consultas_bilhetadas
            WHERE DATE(data_consulta) BETWEEN ? AND ?
            GROUP BY {group_by}, tipo_consulta
            ORDER BY periodo DESC, tipo_consulta
        ''', (data_inicio, data_fim))
        
        resultados = [dict(row) for row in cursor.fetchall()]
        
        # Calcular custo total (R$ 0,942 por consulta)
        custo_por_consulta = 0.942
        total_consultas = sum(r['total_consultas'] for r in resultados)
        custo_total = total_consultas * custo_por_consulta
        
        # Estatísticas por tipo
        por_tipo = {}
        for row in resultados:
            tipo = row['tipo_consulta']
            if tipo not in por_tipo:
                por_tipo[tipo] = {
                    'total': 0,
                    'sucesso': 0,
                    'com_verificacao': 0
                }
            por_tipo[tipo]['total'] += row['total_consultas']
            por_tipo[tipo]['sucesso'] += row['consultas_sucesso']
            por_tipo[tipo]['com_verificacao'] += row['consultas_com_verificacao']
        
        conn.close()
        
        return {
            'sucesso': True,
            'periodo': {
                'inicio': data_inicio,
                'fim': data_fim,
                'agrupar_por': agrupar_por
            },
            'total_consultas': total_consultas,
            'custo_total': custo_total,
            'custo_por_consulta': custo_por_consulta,
            'por_periodo': resultados,
            'por_tipo': por_tipo
        }
        
    except Exception as e:
        logger.error(f'Erro ao gerar relatório de consultas bilhetadas: {e}', exc_info=True)
        return {
            'sucesso': False,
            'erro': str(e)
        }


def obter_relatorio_uso_consultas_salvas() -> Dict[str, Any]:
    """
    Gera relatório de uso de consultas salvas.
    
    Returns:
        Dict com estatísticas de consultas salvas
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Consultas mais usadas
        cursor.execute('''
            SELECT id, nome_exibicao, slug, vezes_usado, ultimo_usado_em, criado_em
            FROM consultas_salvas
            ORDER BY vezes_usado DESC, ultimo_usado_em DESC
            LIMIT 20
        ''')
        
        mais_usadas = [dict(row) for row in cursor.fetchall()]
        
        # Estatísticas gerais
        cursor.execute('''
            SELECT 
                COUNT(*) as total_consultas,
                SUM(vezes_usado) as total_usos,
                COUNT(CASE WHEN vezes_usado = 0 THEN 1 END) as nunca_usadas,
                COUNT(CASE WHEN ultimo_usado_em IS NOT NULL THEN 1 END) as ja_usadas
            FROM consultas_salvas
        ''')
        
        stats = dict(cursor.fetchone())
        
        conn.close()
        
        return {
            'sucesso': True,
            'estatisticas': stats,
            'mais_usadas': mais_usadas
        }
        
    except Exception as e:
        logger.error(f'Erro ao gerar relatório de consultas salvas: {e}', exc_info=True)
        return {
            'sucesso': False,
            'erro': str(e)
        }


def obter_relatorio_uso_regras_aprendidas() -> Dict[str, Any]:
    """
    Gera relatório de uso de regras aprendidas.
    
    Returns:
        Dict com estatísticas de regras aprendidas
    """
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Regras mais usadas
        cursor.execute('''
            SELECT id, nome_regra, tipo_regra, contexto, vezes_usado, ultimo_usado_em, criado_em
            FROM regras_aprendidas
            WHERE ativa = 1
            ORDER BY vezes_usado DESC, ultimo_usado_em DESC
            LIMIT 20
        ''')
        
        mais_usadas = [dict(row) for row in cursor.fetchall()]
        
        # Regras nunca usadas
        cursor.execute('''
            SELECT id, nome_regra, tipo_regra, contexto, criado_em
            FROM regras_aprendidas
            WHERE ativa = 1 AND vezes_usado = 0
            ORDER BY criado_em DESC
            LIMIT 10
        ''')
        
        nunca_usadas = [dict(row) for row in cursor.fetchall()]
        
        # Estatísticas gerais
        cursor.execute('''
            SELECT 
                COUNT(*) as total_regras,
                SUM(vezes_usado) as total_usos,
                COUNT(CASE WHEN vezes_usado = 0 THEN 1 END) as nunca_usadas_count,
                COUNT(CASE WHEN vezes_usado > 0 THEN 1 END) as ja_usadas_count
            FROM regras_aprendidas
            WHERE ativa = 1
        ''')
        
        stats = dict(cursor.fetchone())
        
        conn.close()
        
        return {
            'sucesso': True,
            'estatisticas': stats,
            'mais_usadas': mais_usadas,
            'nunca_usadas': nunca_usadas
        }
        
    except Exception as e:
        logger.error(f'Erro ao gerar relatório de regras aprendidas: {e}', exc_info=True)
        return {
            'sucesso': False,
            'erro': str(e)
        }


def formatar_relatorio_observabilidade(relatorio_bilhetadas: Dict, relatorio_consultas: Dict, relatorio_regras: Dict) -> str:
    """
    Formata relatórios de observabilidade em texto legível.
    
    Args:
        relatorio_bilhetadas: Resultado de obter_relatorio_consultas_bilhetadas()
        relatorio_consultas: Resultado de obter_relatorio_uso_consultas_salvas()
        relatorio_regras: Resultado de obter_relatorio_uso_regras_aprendidas()
    
    Returns:
        Texto formatado do relatório
    """
    texto = "📊 **RELATÓRIO DE OBSERVABILIDADE**\n\n"
    
    # Consultas Bilhetadas
    if relatorio_bilhetadas.get('sucesso'):
        bilh = relatorio_bilhetadas
        texto += f"💰 **CONSULTAS BILHETADAS**\n\n"
        texto += f"• **Total:** {bilh.get('total_consultas', 0)} consultas\n"
        texto += f"• **Custo total:** R$ {bilh.get('custo_total', 0):.2f}\n"
        texto += f"• **Custo médio:** R$ {bilh.get('custo_por_consulta', 0):.2f} por consulta\n\n"
        
        por_tipo = bilh.get('por_tipo', {})
        if por_tipo:
            texto += "**Por tipo:**\n"
            for tipo, dados in por_tipo.items():
                texto += f"  - {tipo}: {dados['total']} consultas (R$ {dados['total'] * 0.942:.2f})\n"
            texto += "\n"
    
    # Consultas Salvas
    if relatorio_consultas.get('sucesso'):
        cons = relatorio_consultas
        stats = cons.get('estatisticas', {})
        texto += f"📋 **CONSULTAS SALVAS**\n\n"
        texto += f"• **Total:** {stats.get('total_consultas', 0)} consultas\n"
        texto += f"• **Total de usos:** {stats.get('total_usos', 0)} vezes\n"
        texto += f"• **Nunca usadas:** {stats.get('nunca_usadas', 0)} consultas\n\n"
        
        mais_usadas = cons.get('mais_usadas', [])[:5]
        if mais_usadas:
            texto += "**Top 5 mais usadas:**\n"
            for consulta in mais_usadas:
                texto += f"  - {consulta.get('nome_exibicao', 'N/A')}: {consulta.get('vezes_usado', 0)} usos\n"
            texto += "\n"
    
    # Regras Aprendidas
    if relatorio_regras.get('sucesso'):
        reg = relatorio_regras
        stats = reg.get('estatisticas', {})
        texto += f"🎓 **REGRAS APRENDIDAS**\n\n"
        texto += f"• **Total:** {stats.get('total_regras', 0)} regras ativas\n"
        texto += f"• **Total de usos:** {stats.get('total_usos', 0)} vezes\n"
        texto += f"• **Nunca usadas:** {stats.get('nunca_usadas_count', 0)} regras\n\n"
        
        mais_usadas = reg.get('mais_usadas', [])[:5]
        if mais_usadas:
            texto += "**Top 5 mais usadas:**\n"
            for regra in mais_usadas:
                texto += f"  - {regra.get('nome_regra', 'N/A')}: {regra.get('vezes_usado', 0)} usos\n"
            texto += "\n"
    
    return texto
