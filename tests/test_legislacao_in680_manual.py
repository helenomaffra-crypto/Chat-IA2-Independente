"""
Script de teste MANUAL para importar IN RFB 680/06.
Permite colar o texto diretamente se a URL não funcionar.
"""
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import get_db_connection, init_db
import sqlite3

def testar_importacao_texto():
    """Testa importação com texto colado manualmente."""
    print("=" * 60)
    print("TESTE: Importação IN RFB 680/06 (TEXTO MANUAL)")
    print("=" * 60)
    print("\n💡 Cole o texto da IN 680/06 abaixo (ou deixe vazio para pular):")
    print("-" * 60)
    
    # Inicializar banco
    init_db()
    
    service = LegislacaoService()
    
    # Exemplo de texto (substituir pelo texto real)
    texto_exemplo = """
    Art. 1º Esta Instrução Normativa dispõe sobre...
    
    Art. 2º Para os efeitos desta Instrução Normativa, considera-se:
    
    I - conceito 1;
    
    II - conceito 2.
    
    Art. 3º O procedimento será realizado...
    
    § 1º No caso do disposto no caput...
    
    § 2º A documentação deverá...
    """
    
    print("\n📝 Usando texto de exemplo (substitua pelo texto real da IN 680/06)")
    print("=" * 60)
    
    resultado = service.importar_ato_de_texto(
        tipo_ato='IN',
        numero='680',
        ano=2006,
        sigla_orgao='RFB',
        texto_bruto=texto_exemplo,
        titulo_oficial='IN RFB 680/06 - Dispõe sobre procedimentos...'
    )
    
    if not resultado['sucesso']:
        print(f"❌ Erro na importação: {resultado.get('erro')}")
        return
    
    print(f"✅ Importação concluída!")
    print(f"   - ID do ato: {resultado['legislacao_id']}")
    print(f"   - Trechos importados: {resultado['trechos_importados']}")
    
    # Verificar trechos importados
    print(f"\n2. Verificando trechos importados")
    print("-" * 60)
    
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT referencia, tipo_trecho, revogado, texto
        FROM legislacao_trecho
        WHERE legislacao_id = ?
        ORDER BY ordem
        LIMIT 10
    ''', (resultado['legislacao_id'],))
    
    trechos = cursor.fetchall()
    print(f"   - Total de trechos: {len(trechos)}")
    
    for trecho in trechos:
        status = "[REVOGADO]" if trecho['revogado'] else "[VIGENTE]"
        print(f"\n   {status} {trecho['referencia']} ({trecho['tipo_trecho']})")
        print(f"   {trecho['texto'][:150]}...")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Teste concluído!")
    print("=" * 60)
    print("\n💡 Para testar com texto real:")
    print("   1. Copie o texto completo da IN 680/06")
    print("   2. Substitua 'texto_exemplo' no código")
    print("   3. Execute novamente")

if __name__ == '__main__':
    testar_importacao_texto()




