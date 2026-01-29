#!/usr/bin/env python3
"""
Script para listar todas as legislações importadas.
"""
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_manager import init_db, get_db_connection

def listar_legislacoes():
    """Lista todas as legislações importadas."""
    
    print("=" * 70)
    print("📚 LISTA DE LEGISLAÇÕES IMPORTADAS - mAIke")
    print("=" * 70)
    print()
    
    # Inicializar banco
    init_db()
    
    # Buscar no banco
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar todas as legislações
    cursor.execute('''
        SELECT id, tipo_ato, numero, ano, sigla_orgao, titulo_oficial, 
               data_importacao, em_vigor
        FROM legislacao
        ORDER BY data_importacao DESC
    ''')
    
    legislacoes = cursor.fetchall()
    
    if not legislacoes:
        print("❌ Nenhuma legislação encontrada no banco de dados.")
        print()
        print("💡 Isso significa que nenhuma importação foi concluída ainda.")
        conn.close()
        return
    
    print(f"✅ Encontradas {len(legislacoes)} legislação(ões) importada(s):")
    print()
    print("=" * 70)
    
    for leg in legislacoes:
        leg_id, tipo, numero, ano, orgao, titulo, data_imp, em_vigor = leg
        print(f"📄 {tipo} {numero}/{ano} ({orgao or 'sem órgão'})")
        print(f"   ID: {leg_id}")
        if titulo:
            print(f"   Título: {titulo[:60]}...")
        print(f"   Importado em: {data_imp}")
        print(f"   Em vigor: {'Sim' if em_vigor else 'Não'}")
        
        # Contar trechos
        cursor.execute('SELECT COUNT(*) FROM legislacao_trecho WHERE legislacao_id = ?', (leg_id,))
        total_trechos = cursor.fetchone()[0]
        print(f"   Trechos: {total_trechos}")
        print()
    
    print("=" * 70)
    print()
    print("💡 Para verificar uma legislação específica, use:")
    print("   python3 scripts/verificar_legislacao.py <tipo> <numero> <ano> [sigla_orgao]")
    print()
    print("💡 Exemplo:")
    if legislacoes:
        primeira = legislacoes[0]
        print(f"   python3 scripts/verificar_legislacao.py {primeira[1]} {primeira[2]} {primeira[3]} {primeira[4] or ''}")
    
    conn.close()

if __name__ == '__main__':
    try:
        listar_legislacoes()
    except Exception as e:
        print(f"\n❌ Erro ao listar legislações: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




