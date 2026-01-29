#!/usr/bin/env python3
"""
Script para visualizar o JSON do último relatório salvo.
"""
import sys
import json
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.report_service import buscar_ultimo_relatorio
from services.context_service import buscar_contexto_sessao

def main():
    # Tentar obter session_id do argumento ou usar padrão
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not session_id:
        # Buscar todas as sessões e mostrar a mais recente
        print("🔍 Buscando último relatório de todas as sessões...\n")
        
        # Buscar todos os contextos de relatório
        from db_manager import get_db_connection
        conn = get_db_connection()
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT session_id 
            FROM contexto_sessao 
            WHERE tipo_contexto = 'ultimo_relatorio'
            ORDER BY atualizado_em DESC
            LIMIT 5
        """)
        
        sessions = cursor.fetchall()
        conn.close()
        
        if not sessions:
            print("❌ Nenhum relatório encontrado no banco.")
            return
        
        print(f"📋 Sessões encontradas: {len(sessions)}\n")
        for i, sess in enumerate(sessions, 1):
            print(f"  {i}. {sess['session_id']}")
        
        if len(sessions) == 1:
            session_id = sessions[0]['session_id']
            print(f"\n✅ Usando sessão: {session_id}\n")
        else:
            print("\n💡 Use: python scripts/ver_ultimo_json.py <session_id>")
            print(f"   Exemplo: python scripts/ver_ultimo_json.py {sessions[0]['session_id']}")
            return
    else:
        print(f"🔍 Buscando último relatório da sessão: {session_id}\n")
    
    # Buscar último relatório
    relatorio = buscar_ultimo_relatorio(session_id, tipo_relatorio=None)
    
    if not relatorio:
        print(f"❌ Nenhum relatório encontrado para sessão: {session_id}")
        return
    
    print("=" * 80)
    print("📊 INFORMAÇÕES DO RELATÓRIO")
    print("=" * 80)
    print(f"Tipo: {relatorio.tipo_relatorio}")
    print(f"Categoria: {relatorio.categoria or 'Todas'}")
    print(f"Criado em: {relatorio.criado_em}")
    if relatorio.filtros:
        print(f"Filtros: {relatorio.filtros}")
    print()
    
    # Extrair JSON
    if not relatorio.meta_json:
        print("❌ Relatório não tem meta_json")
        return
    
    dados_json = relatorio.meta_json.get('dados_json')
    dados_json_original = relatorio.meta_json.get('dados_json_original')  # ✅ NOVO: JSON original completo
    
    # ✅ NOVO: Verificar se tem JSON original preservado
    if dados_json_original:
        print("=" * 80)
        print("📋 JSON ORIGINAL COMPLETO (dados_json_original)")
        print("=" * 80)
        print("⚠️ Este relatório foi filtrado. Abaixo está o JSON ORIGINAL completo:")
        print()
        json_str_original = json.dumps(dados_json_original, indent=2, ensure_ascii=False)
        print(json_str_original)
        print()
        print("=" * 80)
        print("📋 JSON FILTRADO (dados_json)")
        print("=" * 80)
        print("Este é o JSON atual (após filtros):")
        print()
    elif dados_json:
        print("=" * 80)
        print("📋 JSON ESTRUTURADO (dados_json)")
        print("=" * 80)
        print()
    
    if not dados_json:
        print("❌ Relatório não tem dados_json no meta_json")
        print(f"\nMeta JSON disponível: {list(relatorio.meta_json.keys())}")
        return
    
    # Mostrar JSON formatado (filtrado ou completo)
    json_str = json.dumps(dados_json, indent=2, ensure_ascii=False)
    print(json_str)
    print()
    
    # Estatísticas
    print("=" * 80)
    print("📊 ESTATÍSTICAS")
    print("=" * 80)
    
    secoes = dados_json.get('secoes', {})
    resumo = dados_json.get('resumo', {})
    
    print(f"Seções disponíveis: {len(secoes)}")
    for secao, itens in secoes.items():
        if isinstance(itens, list):
            print(f"  • {secao}: {len(itens)} item(ns)")
        else:
            print(f"  • {secao}: {type(itens).__name__}")
    
    if resumo:
        print(f"\nResumo:")
        for chave, valor in resumo.items():
            print(f"  • {chave}: {valor}")
    
    # Verificar se está filtrado
    if dados_json.get('filtrado'):
        print(f"\n⚠️ Este relatório está FILTRADO")
        secoes_filtradas = dados_json.get('secoes_filtradas', [])
        if secoes_filtradas:
            print(f"  Seções filtradas: {', '.join(secoes_filtradas)}")
        categoria_filtro = dados_json.get('categoria_filtro')
        if categoria_filtro:
            print(f"  Categoria filtrada: {categoria_filtro}")
    
    print()
    print("=" * 80)

if __name__ == '__main__':
    main()
