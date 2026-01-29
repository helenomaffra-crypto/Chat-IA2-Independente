"""
Script Python simples para executar a deleção de todos os lançamentos do Santander.
"""
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from dotenv import load_dotenv
load_dotenv(root_dir / '.env')

from utils.sql_server_adapter import get_sql_adapter

def executar_delecao():
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server não disponível")
        return
    
    database = 'mAIke_assistente'
    
    # Contar antes
    query_count = "SELECT COUNT(*) as total FROM dbo.MOVIMENTACAO_BANCARIA WHERE banco_origem = 'SANTANDER'"
    resultado_count = adapter.execute_query(query_count, database=database)
    
    total = 0
    if resultado_count.get('success') and resultado_count.get('data'):
        row = resultado_count['data'][0]
        total = row.get('total', 0) if isinstance(row, dict) else (row[0] if len(row) > 0 else 0)
    
    if total == 0:
        print("✅ Nenhum lançamento do Santander encontrado.")
        return
    
    print(f"🔍 Encontrados {total} lançamento(s) do Santander.")
    resposta = input("❓ Deletar TODOS? (digite 'DELETAR'): ").strip()
    
    if resposta != 'DELETAR':
        print("❌ Cancelado.")
        return
    
    print("\n🗑️ Deletando...")
    
    # 1. Classificações
    query1 = """
        DELETE ltd
        FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
        INNER JOIN dbo.MOVIMENTACAO_BANCARIA mb ON ltd.id_movimentacao_bancaria = mb.id_movimentacao
        WHERE mb.banco_origem = 'SANTANDER'
    """
    adapter.execute_query(query1, database=database)
    print("  ✅ Classificações deletadas")
    
    # 2. Lançamentos
    query2 = "DELETE FROM dbo.MOVIMENTACAO_BANCARIA WHERE banco_origem = 'SANTANDER'"
    resultado = adapter.execute_query(query2, database=database)
    
    if resultado.get('success'):
        print(f"✅ {total} lançamento(s) deletado(s)!")
        print("\n💡 Agora sincronize novamente os extratos do Santander.")
    else:
        print(f"❌ Erro: {resultado.get('error')}")

if __name__ == '__main__':
    executar_delecao()


