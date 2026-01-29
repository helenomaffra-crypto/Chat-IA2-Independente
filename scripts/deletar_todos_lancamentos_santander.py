"""
Script para deletar TODOS os lançamentos do Santander do banco de dados.

⚠️ ATENÇÃO: Este script DELETA TODOS os lançamentos do Santander, incluindo:
- Classificações vinculadas (LANCAMENTO_TIPO_DESPESA)
- Impostos vinculados (se houver)
- Os próprios lançamentos (MOVIMENTACAO_BANCARIA)

Use com cuidado!
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Carregar .env
from dotenv import load_dotenv
load_dotenv(root_dir / '.env')

from utils.sql_server_adapter import get_sql_adapter

def deletar_todos_santander():
    """Deleta TODOS os lançamentos do Santander do banco de dados."""
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server não disponível")
        return
    
    database = 'mAIke_assistente'
    
    # Primeiro, contar quantos lançamentos existem
    query_count = """
        SELECT COUNT(*) as total
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'SANTANDER'
    """
    
    resultado_count = adapter.execute_query(query_count, database=database)
    if not resultado_count.get('success'):
        print("❌ Erro ao contar lançamentos")
        return
    
    rows = resultado_count.get('data', [])
    total_lancamentos = 0
    if rows:
        if isinstance(rows[0], dict):
            total_lancamentos = rows[0].get('total', 0)
        else:
            total_lancamentos = rows[0][0] if len(rows[0]) > 0 else 0
    
    if total_lancamentos == 0:
        print("✅ Nenhum lançamento do Santander encontrado no banco de dados.")
        return
    
    print(f"🔍 Encontrados {total_lancamentos} lançamento(s) do Santander no banco de dados.")
    print("⚠️ ATENÇÃO: Todos serão DELETADOS, incluindo classificações vinculadas.\n")
    
    # Confirmar antes de deletar
    resposta = input("❓ Deseja continuar e deletar TODOS os lançamentos do Santander? (digite 'DELETAR' para confirmar): ").strip()
    if resposta != 'DELETAR':
        print("❌ Operação cancelada.")
        return
    
    print("\n🗑️ Deletando classificações vinculadas...")
    
    # 1. Deletar classificações (LANCAMENTO_TIPO_DESPESA)
    query_delete_classificacoes = """
        DELETE ltd
        FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
        INNER JOIN dbo.MOVIMENTACAO_BANCARIA mb ON ltd.id_movimentacao_bancaria = mb.id_movimentacao
        WHERE mb.banco_origem = 'SANTANDER'
    """
    
    resultado_class = adapter.execute_query(query_delete_classificacoes, database=database)
    if resultado_class.get('success'):
        print("  ✅ Classificações deletadas")
    else:
        print(f"  ⚠️ Aviso ao deletar classificações: {resultado_class.get('error', 'Erro desconhecido')}")
    
    # 2. Deletar impostos vinculados (se a tabela existir)
    print("\n🗑️ Verificando impostos vinculados...")
    query_check_impostos = """
        SELECT COUNT(*) as total
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'IMPOSTO_IMPORTACAO'
    """
    check_impostos = adapter.execute_query(query_check_impostos, database=database)
    
    if check_impostos.get('success') and check_impostos.get('data'):
        # Tabela existe, tentar deletar impostos vinculados
        query_delete_impostos = """
            DELETE imp
            FROM dbo.IMPOSTO_IMPORTACAO imp
            INNER JOIN dbo.MOVIMENTACAO_BANCARIA mb ON imp.id_movimentacao_bancaria = mb.id_movimentacao
            WHERE mb.banco_origem = 'SANTANDER'
        """
        resultado_imp = adapter.execute_query(query_delete_impostos, database=database)
        if resultado_imp.get('success'):
            print("  ✅ Impostos vinculados deletados (se houver)")
        else:
            print("  ⚠️ Nenhum imposto vinculado encontrado ou erro ao deletar")
    
    # 3. Deletar os lançamentos
    print("\n🗑️ Deletando lançamentos do Santander...")
    query_delete = """
        DELETE FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'SANTANDER'
    """
    
    resultado = adapter.execute_query(query_delete, database=database)
    
    if resultado.get('success'):
        print(f"✅ {total_lancamentos} lançamento(s) do Santander deletado(s) com sucesso!")
        print(f"\n💡 Agora você pode sincronizar novamente os extratos do Santander.")
        print(f"   Os lançamentos serão salvos com as datas corretas.")
    else:
        error_msg = resultado.get('error', 'Erro desconhecido')
        print(f"❌ Erro ao deletar lançamentos: {error_msg}")

if __name__ == '__main__':
    deletar_todos_santander()


