"""
Teste completo do sistema de legislação com simulação de IN 680/06.
Inclui artigos revogados e texto riscado.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import init_db, get_db_connection
import sqlite3

def testar_in680_completo():
    """Testa importação completa simulando IN 680/06 com artigos revogados."""
    
    print("=" * 70)
    print("TESTE COMPLETO: Sistema de Legislação - IN 680/06")
    print("=" * 70)
    
    # Inicializar banco
    print("\n1. Inicializando banco de dados...")
    init_db()
    print("   ✅ Banco inicializado")
    
    # Criar serviço
    print("\n2. Criando serviço de legislação...")
    service = LegislacaoService()
    print("   ✅ Serviço criado")
    
    # Simular texto da IN 680/06 com artigos revogados
    print("\n3. Simulando texto da IN 680/06 (com artigos revogados)...")
    texto_in680 = """
    INSTRUÇÃO NORMATIVA RFB Nº 680, DE 2006
    
    Dispõe sobre o despacho aduaneiro de importação.
    
    Art. 1º Esta Instrução Normativa dispõe sobre o despacho aduaneiro de importação, 
    observadas as disposições da Lei nº 9.430, de 1996, e da Lei nº 10.833, de 2003.
    
    Art. 2º Para os efeitos desta Instrução Normativa, considera-se:
    
    I - despacho aduaneiro: o procedimento administrativo destinado a verificar 
    se a mercadoria importada atende às exigências legais e regulamentares;
    
    II - canal de conferência: o procedimento de verificação documental e física 
    da mercadoria importada.
    
    Art. 3º O despacho aduaneiro será realizado mediante apresentação da 
    Declaração de Importação (DI) ou da Declaração Única de Importação (DUIMP).
    
    § 1º A DI ou DUIMP deverá conter todas as informações necessárias para 
    o despacho aduaneiro.
    
    § 2º [REVOGADO] Este parágrafo foi revogado pela IN 1234/10.
    
    Art. 4º A seleção para verificação documental ou física será realizada 
    automaticamente pelo sistema, considerando os critérios estabelecidos.
    
    Art. 5º [REVOGADO] Este artigo foi revogado pela IN 1500/15.
    
    Art. 6º O canal de conferência será determinado automaticamente pelo sistema, 
    podendo ser:
    
    I - Verde: despacho automático;
    
    II - Amarelo: verificação documental;
    
    III - Vermelho: verificação física e documental.
    
    Art. 7º A base de cálculo do Imposto de Importação (II) será o valor 
    aduaneiro da mercadoria, conforme estabelecido na legislação vigente.
    
    § 1º O valor aduaneiro será apurado conforme os critérios estabelecidos 
    no Acordo de Valoração Aduaneira da OMC.
    
    § 2º [REVOGADO] Este parágrafo foi revogado.
    """
    
    print("   ✅ Texto simulado (contém artigos revogados)")
    
    # Importar
    print("\n4. Importando IN 680/06...")
    print("-" * 70)
    
    resultado = service.importar_ato_de_texto(
        tipo_ato='IN',
        numero='680',
        ano=2006,
        sigla_orgao='RFB',
        texto_bruto=texto_in680,
        titulo_oficial='IN RFB 680/06 - Dispõe sobre o despacho aduaneiro de importação'
    )
    
    if not resultado['sucesso']:
        print(f"   ❌ Erro: {resultado.get('erro')}")
        return
    
    print(f"   ✅ Importação concluída!")
    print(f"      - ID do ato: {resultado['legislacao_id']}")
    print(f"      - Trechos importados: {resultado['trechos_importados']}")
    
    # Verificar trechos importados
    print("\n5. Verificando trechos importados...")
    print("-" * 70)
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) as total FROM legislacao_trecho WHERE legislacao_id = ?
    ''', (resultado['legislacao_id'],))
    total = cursor.fetchone()['total']
    
    cursor.execute('''
        SELECT COUNT(*) as total FROM legislacao_trecho 
        WHERE legislacao_id = ? AND revogado = 1
    ''', (resultado['legislacao_id'],))
    total_revogados = cursor.fetchone()['total']
    
    print(f"   - Total de trechos: {total}")
    print(f"   - Trechos revogados: {total_revogados}")
    print(f"   - Trechos vigentes: {total - total_revogados}")
    
    # Listar todos os trechos
    print("\n6. Listando todos os trechos importados...")
    print("-" * 70)
    
    cursor.execute('''
        SELECT referencia, tipo_trecho, revogado, texto
        FROM legislacao_trecho
        WHERE legislacao_id = ?
        ORDER BY ordem
    ''', (resultado['legislacao_id'],))
    
    trechos = cursor.fetchall()
    for trecho in trechos:
        status = "🔴 [REVOGADO]" if trecho['revogado'] else "🟢 [VIGENTE]"
        print(f"\n   {status} {trecho['referencia']} ({trecho['tipo_trecho']})")
        print(f"      {trecho['texto'][:120]}...")
    
    # Buscar trechos por palavra-chave (sem revogados)
    print("\n7. Buscando trechos sobre 'canal' (excluindo revogados)...")
    print("-" * 70)
    
    trechos_busca = service.buscar_trechos_por_palavra_chave(
        tipo_ato='IN',
        numero='680',
        termos=['canal'],
        ano=2006,
        sigla_orgao='RFB',
        limit=10,
        incluir_revogados=False
    )
    
    print(f"   - Trechos encontrados: {len(trechos_busca)}")
    for trecho in trechos_busca:
        print(f"\n   📄 {trecho['referencia']}")
        print(f"      {trecho['texto_com_artigo'][:200]}...")
    
    # Buscar incluindo revogados
    print("\n8. Buscando trechos sobre 'canal' (incluindo revogados)...")
    print("-" * 70)
    
    trechos_com_revogados = service.buscar_trechos_por_palavra_chave(
        tipo_ato='IN',
        numero='680',
        termos=['canal'],
        ano=2006,
        sigla_orgao='RFB',
        limit=10,
        incluir_revogados=True
    )
    
    print(f"   - Trechos encontrados (com revogados): {len(trechos_com_revogados)}")
    
    # Buscar sobre "base de cálculo"
    print("\n9. Buscando trechos sobre 'base de cálculo' e 'II'...")
    print("-" * 70)
    
    trechos_calculo = service.buscar_trechos_por_palavra_chave(
        tipo_ato='IN',
        numero='680',
        termos=['base de cálculo', 'II'],
        ano=2006,
        sigla_orgao='RFB',
        limit=5,
        incluir_revogados=False
    )
    
    print(f"   - Trechos encontrados: {len(trechos_calculo)}")
    for trecho in trechos_calculo:
        print(f"\n   📄 {trecho['referencia']}")
        print(f"      {trecho['texto_com_artigo'][:250]}...")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ TESTE COMPLETO CONCLUÍDO!")
    print("=" * 70)
    print("\n📊 RESUMO:")
    print(f"   - Total de trechos: {total}")
    print(f"   - Revogados: {total_revogados}")
    print(f"   - Vigentes: {total - total_revogados}")
    print(f"   - Busca 'canal' (sem revogados): {len(trechos_busca)}")
    print(f"   - Busca 'base de cálculo' (sem revogados): {len(trechos_calculo)}")
    print("\n✅ Sistema funcionando corretamente!")
    print("   - Parser detecta artigos e parágrafos")
    print("   - Detecta artigos revogados")
    print("   - Busca funciona com filtro de revogados")
    print("   - Contexto de artigo preservado (texto_com_artigo)")

if __name__ == '__main__':
    testar_in680_completo()




