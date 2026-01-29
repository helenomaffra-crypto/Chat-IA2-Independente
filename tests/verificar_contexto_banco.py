#!/usr/bin/env python3
"""
Script para verificar contexto salvo no banco de dados.

Uso:
    python tests/verificar_contexto_banco.py [session_id]
    
Se não fornecer session_id, lista todos os contextos.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.context_service import buscar_contexto_sessao, limpar_contexto_sessao
from db_manager import get_db_connection
import sqlite3

def listar_todos_contextos():
    """Lista todos os contextos salvos no banco."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM contexto_sessao ORDER BY atualizado_em DESC')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("✅ Nenhum contexto encontrado no banco.")
            return
        
        print(f"\n📊 Total de contextos no banco: {len(rows)}")
        print("=" * 80)
        
        # Agrupar por session_id
        contextos_por_sessao = {}
        for row in rows:
            session_id = row['session_id']
            if session_id not in contextos_por_sessao:
                contextos_por_sessao[session_id] = []
            contextos_por_sessao[session_id].append(dict(row))
        
        for session_id, contextos in contextos_por_sessao.items():
            print(f"\n🔑 Session ID: {session_id}")
            print(f"   Total de contextos: {len(contextos)}")
            for ctx in contextos:
                print(f"   - {ctx.get('tipo_contexto')}: {ctx.get('valor')} (atualizado: {ctx.get('atualizado_em')})")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

def verificar_contexto_sessao(session_id: str):
    """Verifica contexto de uma sessão específica."""
    print(f"\n🔍 Verificando contexto para session_id: {session_id}")
    print("=" * 80)
    
    contextos = buscar_contexto_sessao(session_id)
    
    if not contextos:
        print("✅ Nenhum contexto encontrado para esta sessão.")
        return
    
    print(f"📊 Total de contextos: {len(contextos)}")
    for ctx in contextos:
        print(f"\n- Tipo: {ctx.get('tipo_contexto')}")
        print(f"  Chave: {ctx.get('chave')}")
        print(f"  Valor: {ctx.get('valor')}")
        print(f"  Atualizado: {ctx.get('atualizado_em')}")
        if ctx.get('dados'):
            print(f"  Dados: {ctx.get('dados')}")
    
    print("\n" + "=" * 80)

def limpar_contexto_sessao_manual(session_id: str):
    """Limpa contexto de uma sessão específica."""
    print(f"\n🗑️  Limpando contexto para session_id: {session_id}")
    print("=" * 80)
    
    sucesso = limpar_contexto_sessao(session_id)
    
    if sucesso:
        print("✅ Contexto limpo com sucesso!")
        
        # Verificar se foi limpo
        contextos = buscar_contexto_sessao(session_id)
        if not contextos:
            print("✅ Confirmado: Nenhum contexto restante.")
        else:
            print(f"⚠️  Ainda há {len(contextos)} contexto(s) restante(s).")
    else:
        print("❌ Erro ao limpar contexto.")
    
    print("=" * 80)

def main():
    """Executa verificação de contexto."""
    import sys
    
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        
        if session_id == '--limpar' and len(sys.argv) > 2:
            # Limpar contexto de uma sessão específica
            limpar_contexto_sessao_manual(sys.argv[2])
        elif session_id == '--limpar-todos':
            # Limpar TODOS os contextos
            print("\n⚠️  ATENÇÃO: Isso vai limpar TODOS os contextos de TODAS as sessões!")
            resposta = input("Tem certeza? (digite 'sim' para confirmar): ")
            if resposta.lower() == 'sim':
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('DELETE FROM contexto_sessao')
                    linhas = cursor.rowcount
                    conn.commit()
                    conn.close()
                    print(f"✅ {linhas} contexto(s) deletado(s).")
                except Exception as e:
                    print(f"❌ Erro: {e}")
            else:
                print("❌ Operação cancelada.")
        else:
            # Verificar contexto de uma sessão específica
            verificar_contexto_sessao(session_id)
    else:
        # Listar todos os contextos
        listar_todos_contextos()
        
        print("\n💡 Uso:")
        print("   python tests/verificar_contexto_banco.py [session_id]")
        print("   python tests/verificar_contexto_banco.py --limpar [session_id]")
        print("   python tests/verificar_contexto_banco.py --limpar-todos")

if __name__ == '__main__':
    main()
