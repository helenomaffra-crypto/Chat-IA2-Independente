#!/usr/bin/env python3
"""
Script para verificar se uma legislação foi importada corretamente.
"""
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import init_db, get_db_connection

def verificar_legislacao(tipo_ato: str, numero: str, ano: int, sigla_orgao: str = ''):
    """Verifica se uma legislação foi importada."""
    
    print("=" * 70)
    print("🔍 VERIFICADOR DE LEGISLAÇÃO - mAIke")
    print("=" * 70)
    print()
    
    # Inicializar banco
    init_db()
    
    # Buscar no banco
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"🔍 Buscando: {tipo_ato} {numero}/{ano} ({sigla_orgao or 'sem órgão'})")
    print()
    
    # Buscar legislação
    if sigla_orgao:
        cursor.execute('''
            SELECT id, tipo_ato, numero, ano, sigla_orgao, titulo_oficial, 
                   fonte_url, data_importacao, em_vigor
            FROM legislacao
            WHERE tipo_ato = ? AND numero = ? AND ano = ? AND sigla_orgao = ?
        ''', (tipo_ato, numero, ano, sigla_orgao))
    else:
        cursor.execute('''
            SELECT id, tipo_ato, numero, ano, sigla_orgao, titulo_oficial, 
                   fonte_url, data_importacao, em_vigor
            FROM legislacao
            WHERE tipo_ato = ? AND numero = ? AND ano = ?
        ''', (tipo_ato, numero, ano))
    
    legislacao = cursor.fetchone()
    
    if not legislacao:
        print("❌ Legislação NÃO encontrada no banco de dados.")
        print()
        print("💡 Isso significa que a importação não foi concluída.")
        print("   Tente importar novamente.")
        conn.close()
        return
    
    legislacao_id = legislacao[0]
    print("✅ Legislação encontrada no banco!")
    print()
    print("=" * 70)
    print("📊 DADOS DA LEGISLAÇÃO")
    print("=" * 70)
    print(f"   ID: {legislacao_id}")
    print(f"   Tipo: {legislacao[1]}")
    print(f"   Número: {legislacao[2]}")
    print(f"   Ano: {legislacao[3]}")
    print(f"   Órgão: {legislacao[4] or 'Não informado'}")
    print(f"   Título: {legislacao[5] or 'Não informado'}")
    print(f"   Fonte URL: {legislacao[6] or 'Não informado'}")
    print(f"   Data de importação: {legislacao[7]}")
    print(f"   Em vigor: {'Sim' if legislacao[8] else 'Não'}")
    print()
    
    # Contar trechos
    cursor.execute('''
        SELECT COUNT(*) FROM legislacao_trecho
        WHERE legislacao_id = ?
    ''', (legislacao_id,))
    
    total_trechos = cursor.fetchone()[0]
    print("=" * 70)
    print("📄 TRECHOS IMPORTADOS")
    print("=" * 70)
    print(f"   Total de trechos: {total_trechos}")
    print()
    
    if total_trechos == 0:
        print("⚠️ ATENÇÃO: Nenhum trecho foi importado!")
        print("   Isso pode indicar um problema no parsing do texto.")
        print()
    else:
        # Mostrar alguns exemplos
        cursor.execute('''
            SELECT referencia, tipo_trecho, SUBSTR(texto, 1, 100)
            FROM legislacao_trecho
            WHERE legislacao_id = ?
            ORDER BY ordem
            LIMIT 5
        ''', (legislacao_id,))
        
        exemplos = cursor.fetchall()
        print("📋 Primeiros trechos importados:")
        print()
        for ref, tipo, texto_preview in exemplos:
            print(f"   {ref} ({tipo}): {texto_preview}...")
        print()
        
        if total_trechos > 5:
            print(f"   ... e mais {total_trechos - 5} trechos")
            print()
    
    conn.close()
    
    print("=" * 70)
    print("✅ Verificação concluída!")
    print("=" * 70)
    print()
    print("💡 Se a legislação foi encontrada, a importação foi bem-sucedida!")
    print("   Você pode consultar usando:")
    print(f"   from services.legislacao_service import LegislacaoService")
    print(f"   service = LegislacaoService()")
    print(f"   ato = service.buscar_ato('{tipo_ato}', '{numero}', {ano}, '{sigla_orgao or ''}')")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Uso: python3 scripts/verificar_legislacao.py <tipo> <numero> <ano> [sigla_orgao]")
        print()
        print("Exemplo:")
        print("  python3 scripts/verificar_legislacao.py IN 680 2006 RFB")
        sys.exit(1)
    
    tipo_ato = sys.argv[1]
    numero = sys.argv[2]
    ano = int(sys.argv[3])
    sigla_orgao = sys.argv[4] if len(sys.argv) > 4 else ''
    
    try:
        verificar_legislacao(tipo_ato, numero, ano, sigla_orgao)
    except Exception as e:
        print(f"\n❌ Erro ao verificar: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

