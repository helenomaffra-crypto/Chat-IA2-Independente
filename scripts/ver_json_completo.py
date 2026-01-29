#!/usr/bin/env python3
"""
Script para visualizar o JSON COMPLETO original (não filtrado) do último relatório.
Busca todos os relatórios salvos e mostra o mais completo (não filtrado).
"""
import sys
import json
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.context_service import buscar_contexto_sessao

def main():
    # Tentar obter session_id do argumento ou usar padrão
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not session_id:
        # Buscar todas as sessões e mostrar a mais recente
        print("🔍 Buscando relatórios de todas as sessões (session_id)...\n")
        print("💡 'Sessões' = identificadores de usuário diferentes")
        print("   'Seções' = partes do relatório JSON (processos_chegando, pendencias, etc.)\n")
        
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
        
        print(f"📋 Sessões de usuário encontradas: {len(sessions)}")
        print("   (Cada sessão pode ter múltiplos relatórios salvos)\n")
        for i, sess in enumerate(sessions, 1):
            print(f"  {i}. {sess['session_id']}")
        
        if len(sessions) == 1:
            session_id = sessions[0]['session_id']
            print(f"\n✅ Usando sessão: {session_id}\n")
        else:
            print("\n💡 Use: python scripts/ver_json_completo.py <session_id>")
            print(f"   Exemplo: python scripts/ver_json_completo.py {sessions[0]['session_id']}")
            return
    else:
        print(f"🔍 Buscando relatórios da sessão: {session_id}\n")
    
    # Buscar TODOS os relatórios da sessão
    contextos = buscar_contexto_sessao(
        session_id=session_id,
        tipo_contexto='ultimo_relatorio',
        chave=None  # Buscar todos
    )
    
    if not contextos:
        print(f"❌ Nenhum relatório encontrado para sessão: {session_id}")
        return
    
    print(f"📊 Total de relatórios salvos: {len(contextos)}\n")
    print("💡 Nota: 'Sessões' = identificadores de usuário (session_id)")
    print("   'Seções' = partes do relatório (processos_chegando, pendencias, etc.)\n")
    
    # Buscar o relatório COMPLETO (não filtrado)
    relatorio_completo = None
    relatorios_filtrados = []
    
    for ctx in contextos:
        dados = ctx.get('dados', {})
        if not dados:
            continue
        
        # Verificar se tem dados_json
        meta_json = dados.get('meta_json', {})
        dados_json = meta_json.get('dados_json', {}) if meta_json else {}
        
        # Verificar se está filtrado
        if dados_json.get('filtrado'):
            relatorios_filtrados.append({
                'contexto': ctx,
                'dados': dados,
                'dados_json': dados_json,
                'atualizado_em': ctx.get('atualizado_em', '')
            })
        else:
            # Este é o relatório completo (não filtrado)
            if not relatorio_completo or ctx.get('atualizado_em', '') > relatorio_completo.get('atualizado_em', ''):
                relatorio_completo = {
                    'contexto': ctx,
                    'dados': dados,
                    'dados_json': dados_json,
                    'atualizado_em': ctx.get('atualizado_em', '')
                }
    
    # Mostrar relatório completo
    if relatorio_completo:
        print("=" * 80)
        print("✅ JSON COMPLETO ORIGINAL (não filtrado)")
        print("=" * 80)
        print(f"Tipo: {relatorio_completo['dados'].get('tipo_relatorio', 'N/A')}")
        print(f"Criado em: {relatorio_completo['atualizado_em']}")
        print()
        
        json_str = json.dumps(relatorio_completo['dados_json'], indent=2, ensure_ascii=False)
        print(json_str)
        print()
        
        # Estatísticas
        secoes = relatorio_completo['dados_json'].get('secoes', {})
        print("=" * 80)
        print("📊 ESTATÍSTICAS DO JSON COMPLETO")
        print("=" * 80)
        print(f"Seções disponíveis: {len(secoes)}")
        for secao, itens in secoes.items():
            if isinstance(itens, list):
                print(f"  • {secao}: {len(itens)} item(ns)")
            else:
                print(f"  • {secao}: {type(itens).__name__}")
        print()
    else:
        print("⚠️ Nenhum relatório COMPLETO (não filtrado) encontrado.")
        print("   Todos os relatórios salvos estão filtrados.\n")
    
    # Mostrar relatórios filtrados se houver
    if relatorios_filtrados:
        print("=" * 80)
        print(f"📋 RELATÓRIOS FILTRADOS ({len(relatorios_filtrados)})")
        print("=" * 80)
        for i, rel_filtrado in enumerate(relatorios_filtrados, 1):
            dados_json_filtrado = rel_filtrado['dados_json']
            secoes_filtradas = dados_json_filtrado.get('secoes_filtradas', [])
            categoria_filtro = dados_json_filtrado.get('categoria_filtro')
            
            print(f"\n{i}. Filtrado em: {rel_filtrado['atualizado_em']}")
            print(f"   Seções filtradas: {', '.join(secoes_filtradas) if secoes_filtradas else 'N/A'}")
            if categoria_filtro:
                print(f"   Categoria filtrada: {categoria_filtro}")
            
            # Verificar se tem JSON original preservado
            dados_originais = rel_filtrado['dados'].get('meta_json', {}).get('dados_json_original')
            if dados_originais:
                print(f"   ✅ JSON original preservado ({len(dados_originais.get('secoes', {}))} seções)")
            else:
                print(f"   ⚠️ JSON original NÃO preservado")
        print()
    
    print("=" * 80)

if __name__ == '__main__':
    main()
