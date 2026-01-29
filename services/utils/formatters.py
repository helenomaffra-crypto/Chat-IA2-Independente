"""
Funções para formatação de dados para exibição.
"""
from typing import List, Dict, Any, Optional


def format_lista_processos(processos: List[Dict[str, Any]], limite: Optional[int] = None) -> str:
    """
    Formata lista de processos para exibição.
    
    Args:
        processos: Lista de processos
        limite: Limite de processos a exibir (opcional)
    
    Returns:
        String formatada com lista de processos
    """
    if not processos:
        return "❌ Nenhum processo encontrado."
    
    if limite:
        processos = processos[:limite]
    
    resposta = f"📋 **Processos de Importação** ({len(processos)} processo(s))\n\n"
    
    for proc in processos:
        proc_ref = proc.get('processo_referencia', 'N/A')
        status = proc.get('status', 'N/A')
        categoria = proc.get('categoria', '')
        duimp_num = proc.get('duimp_numero', '')
        
        resposta += f"**{proc_ref}**"
        if categoria:
            resposta += f" ({categoria})"
        resposta += "\n"
        resposta += f"   - Status: {status}\n"
        
        if duimp_num:
            resposta += f"   - DUIMP: {duimp_num} v{proc.get('duimp_versao', 'N/A')}\n"
        
        resposta += "\n"
    
    return resposta
















