"""
Script de teste para importar IN RFB 680/06 e verificar tratamento de artigos revogados.
"""
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import get_db_connection
import sqlite3

def testar_in680():
    """Testa importação da IN 680/06."""
    service = LegislacaoService()
    
    print("=" * 60)
    print("TESTE: Importação IN RFB 680/06")
    print("=" * 60)
    
    # URL da IN 680/06 - tentar diferentes formatos
    urls_possiveis = [
        "https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/legislacao/instrucoes-normativas/in680-2006",
        "https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/legislacao/instrucoes-normativas/in-680-de-2006",
        "https://normas.receita.fazenda.gov.br/sijut2consulta/link.action?idAto=12345",  # Exemplo - ajustar
    ]
    
    url_in680 = urls_possiveis[0]  # Tentar primeira URL
    
    print(f"\n1. Importando IN 680/06 de: {url_in680}")
    print("-" * 60)
    
    resultado = service.importar_ato_por_url(
        tipo_ato='IN',
        numero='680',
        ano=2006,
        sigla_orgao='RFB',
        url=url_in680,
        titulo_oficial='IN RFB 680/06 - Dispõe sobre...'
    )
    
    if not resultado['sucesso']:
        print(f"❌ Erro na importação: {resultado.get('erro')}")
        print("\n💡 Dica: Se a URL não funcionar, você pode:")
        print("   1. Copiar o texto da IN 680/06")
        print("   2. Usar service.importar_ato_de_texto() com o texto colado")
        return
    
    print(f"✅ Importação concluída!")
    print(f"   - ID do ato: {resultado['legislacao_id']}")
    print(f"   - Trechos importados: {resultado['trechos_importados']}")
    
    # 2. Verificar artigos revogados
    print(f"\n2. Verificando artigos revogados")
    print("-" * 60)
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Contar trechos revogados
    cursor.execute('''
        SELECT COUNT(*) as total_revogados
        FROM legislacao_trecho
        WHERE legislacao_id = ? AND revogado = 1
    ''', (resultado['legislacao_id'],))
    
    total_revogados = cursor.fetchone()['total_revogados']
    print(f"   - Total de trechos revogados: {total_revogados}")
    
    # Listar alguns trechos revogados
    cursor.execute('''
        SELECT referencia, tipo_trecho, texto
        FROM legislacao_trecho
        WHERE legislacao_id = ? AND revogado = 1
        ORDER BY ordem
        LIMIT 5
    ''', (resultado['legislacao_id'],))
    
    revogados = cursor.fetchall()
    if revogados:
        print(f"\n   Exemplos de trechos revogados:")
        for trecho in revogados:
            print(f"   - {trecho['referencia']} ({trecho['tipo_trecho']})")
            print(f"     Texto: {trecho['texto'][:100]}...")
    
    # 3. Buscar trechos (sem revogados)
    print(f"\n3. Buscando trechos sobre 'canal' (excluindo revogados)")
    print("-" * 60)
    
    trechos = service.buscar_trechos_por_palavra_chave(
        tipo_ato='IN',
        numero='680',
        termos=['canal'],
        ano=2006,
        sigla_orgao='RFB',
        limit=5,
        incluir_revogados=False
    )
    
    print(f"   - Trechos encontrados: {len(trechos)}")
    for trecho in trechos:
        print(f"\n   {trecho['referencia']} {'[REVOGADO]' if trecho.get('revogado') else ''}")
        print(f"   {trecho['texto_com_artigo'][:200]}...")
    
    # 4. Buscar incluindo revogados
    print(f"\n4. Buscando trechos sobre 'canal' (incluindo revogados)")
    print("-" * 60)
    
    trechos_com_revogados = service.buscar_trechos_por_palavra_chave(
        tipo_ato='IN',
        numero='680',
        termos=['canal'],
        ano=2006,
        sigla_orgao='RFB',
        limit=5,
        incluir_revogados=True
    )
    
    print(f"   - Trechos encontrados (com revogados): {len(trechos_com_revogados)}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Teste concluído!")
    print("=" * 60)

if __name__ == '__main__':
    testar_in680()

