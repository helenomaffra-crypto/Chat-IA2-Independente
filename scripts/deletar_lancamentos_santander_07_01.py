"""
Script para deletar lançamentos do Santander do dia 07/01/2026 que correspondem
aos valores do dia 08/01/2026, permitindo sincronizar novamente com a data correta.

⚠️ ATENÇÃO: Este script DELETA lançamentos do banco de dados.
Certifique-se de que não há classificações importantes vinculadas a estes lançamentos.
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

def deletar_lancamentos_07_01():
    """Deleta lançamentos do Santander do dia 07/01/2026 que correspondem ao dia 08/01/2026."""
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server não disponível")
        return
    
    database = 'mAIke_assistente'
    
    # Lista de valores do dia 08/01/2026 (valores conhecidos do chat)
    # ✅ Simplificado: buscar apenas por valor exato, sem depender da descrição
    valores_dia_08 = [
        {'valor': 7880.48, 'sinal': 'D'},
        {'valor': 272902.70, 'sinal': 'D'},
        {'valor': 17465.73, 'sinal': 'D'},
        {'valor': 498.00, 'sinal': 'C'},
        {'valor': 81166.63, 'sinal': 'C'},
        {'valor': 58471.06, 'sinal': 'C'},
        {'valor': 69009.44, 'sinal': 'C'},
        {'valor': 64255.57, 'sinal': 'C'},
        {'valor': 7885.55, 'sinal': 'D'},
        {'valor': 786.22, 'sinal': 'D'},
        {'valor': 5989.90, 'sinal': 'D'},
        {'valor': 2000.00, 'sinal': 'D'},
        {'valor': 2800.00, 'sinal': 'D'},
        {'valor': 8202.79, 'sinal': 'D'},
        {'valor': 573.00, 'sinal': 'D'},
    ]
    
    print("🔍 Buscando lançamentos do Santander do dia 07/01/2026 que correspondem aos valores do dia 08/01/2026...")
    print("⚠️ ATENÇÃO: Estes lançamentos serão DELETADOS do banco de dados.\n")
    
    total_deletados = 0
    ids_para_deletar = []
    
    for lancamento_ref in valores_dia_08:
        valor_ref = lancamento_ref['valor']
        sinal_ref = lancamento_ref['sinal']
        
        # ✅ Buscar apenas por valor exato e sinal (mais flexível)
        # Excluir se já existe um lançamento com mesmo valor no dia 08/01/2026
        query = f"""
            SELECT 
                mb.id_movimentacao,
                CAST(mb.descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao,
                mb.valor_movimentacao,
                mb.sinal_movimentacao,
                mb.data_movimentacao
            FROM dbo.MOVIMENTACAO_BANCARIA mb
            WHERE mb.banco_origem = 'SANTANDER'
              AND CAST(mb.data_movimentacao AS DATE) = '2026-01-07'
              AND ABS(mb.valor_movimentacao - {valor_ref}) < 0.01
              AND mb.sinal_movimentacao = '{sinal_ref}'
              AND NOT EXISTS (
                  -- Excluir se já existe um lançamento com mesmo valor no dia 08/01/2026
                  SELECT 1
                  FROM dbo.MOVIMENTACAO_BANCARIA mb2
                  WHERE mb2.banco_origem = 'SANTANDER'
                    AND CAST(mb2.data_movimentacao AS DATE) = '2026-01-08'
                    AND ABS(mb2.valor_movimentacao - {valor_ref}) < 0.01
                    AND mb2.sinal_movimentacao = '{sinal_ref}'
              )
            ORDER BY mb.id_movimentacao DESC
        """
        
        resultado = adapter.execute_query(query, database=database)
        
        if resultado.get('success') and resultado.get('data'):
            rows = resultado['data']
            for row in rows:
                if isinstance(row, dict):
                    id_mov = row.get('id_movimentacao')
                    descricao_atual = row.get('descricao_movimentacao', '')
                else:
                    id_mov = row[0] if len(row) > 0 else None
                    descricao_atual = row[1] if len(row) > 1 else ''
                
                if id_mov and id_mov not in ids_para_deletar:
                    ids_para_deletar.append(id_mov)
                    print(f"  📋 Encontrado: ID {id_mov} - {descricao_atual[:60]}... (R$ {valor_ref:,.2f})")
    
    if not ids_para_deletar:
        print("✅ Nenhum lançamento encontrado para deletar.")
        return
    
    print(f"\n⚠️ Total de lançamentos a serem deletados: {len(ids_para_deletar)}")
    print("⚠️ Certifique-se de que não há classificações importantes vinculadas a estes lançamentos.")
    
    # Confirmar antes de deletar
    resposta = input("\n❓ Deseja continuar e deletar estes lançamentos? (sim/não): ").strip().lower()
    if resposta not in ['sim', 's', 'yes', 'y']:
        print("❌ Operação cancelada.")
        return
    
    # Deletar classificações primeiro (se houver)
    print("\n🗑️ Deletando classificações vinculadas...")
    ids_str = ','.join(map(str, ids_para_deletar))
    query_delete_classificacoes = f"""
        DELETE FROM dbo.LANCAMENTO_TIPO_DESPESA
        WHERE id_movimentacao_bancaria IN ({ids_str})
    """
    resultado_class = adapter.execute_query(query_delete_classificacoes, database=database)
    if resultado_class.get('success'):
        print(f"  ✅ Classificações deletadas")
    else:
        print(f"  ⚠️ Aviso ao deletar classificações: {resultado_class.get('error', 'Erro desconhecido')}")
    
    # Deletar lançamentos
    print("\n🗑️ Deletando lançamentos...")
    query_delete = f"""
        DELETE FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE id_movimentacao IN ({ids_str})
    """
    
    resultado = adapter.execute_query(query_delete, database=database)
    
    if resultado.get('success'):
        print(f"✅ {len(ids_para_deletar)} lançamento(s) deletado(s) com sucesso!")
        print(f"\n💡 Agora você pode sincronizar novamente os extratos do Santander.")
        print(f"   Os lançamentos do dia 08/01/2026 serão salvos com a data correta.")
    else:
        error_msg = resultado.get('error', 'Erro desconhecido')
        print(f"❌ Erro ao deletar lançamentos: {error_msg}")

if __name__ == '__main__':
    deletar_lancamentos_07_01()

