"""
Script para verificar se os lançamentos do dia 08/01/2026 estão no banco de dados.
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
from datetime import datetime

def verificar_lancamentos_dia_08():
    """Verifica se há lançamentos do dia 08/01/2026 no banco."""
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server não disponível")
        return
    
    database = 'mAIke_assistente'
    
    # Query para verificar lançamentos do dia 08/01/2026
    query = f"""
        SELECT TOP 50
            id_movimentacao,
            banco_origem,
            agencia_origem,
            conta_origem,
            data_movimentacao,
            data_lancamento,
            valor_movimentacao,
            sinal_movimentacao,
            descricao_movimentacao,
            criado_em
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'SANTANDER'
          AND CAST(data_movimentacao AS DATE) = '2026-01-08'
        ORDER BY data_movimentacao DESC, criado_em DESC
    """
    
    print("🔍 Verificando lançamentos do Santander do dia 08/01/2026...")
    resultado = adapter.execute_query(query, database=database)
    
    if not resultado.get('success'):
        error_msg = resultado.get('error', 'Erro desconhecido')
        print(f"❌ Erro ao consultar: {error_msg}")
        return
    
    rows = resultado.get('data', [])
    
    if not rows:
        print("❌ Nenhum lançamento encontrado para o dia 08/01/2026")
        
        # Verificar se há lançamentos próximos (07 ou 09)
        query_proximos = f"""
            SELECT TOP 10
                CAST(data_movimentacao AS DATE) as data,
                COUNT(*) as total
            FROM dbo.MOVIMENTACAO_BANCARIA
            WHERE banco_origem = 'SANTANDER'
              AND CAST(data_movimentacao AS DATE) >= '2026-01-06'
              AND CAST(data_movimentacao AS DATE) <= '2026-01-10'
            GROUP BY CAST(data_movimentacao AS DATE)
            ORDER BY data DESC
        """
        resultado_proximos = adapter.execute_query(query_proximos, database=database)
        if resultado_proximos.get('success') and resultado_proximos.get('data'):
            print("\n📊 Lançamentos por data (Santander):")
            for row in resultado_proximos['data']:
                if isinstance(row, dict):
                    data = row.get('data', '')
                    total = row.get('total', 0)
                else:
                    data = row[0] if len(row) > 0 else ''
                    total = row[1] if len(row) > 1 else 0
                print(f"  {data}: {total} lançamento(s)")
        return
    
    print(f"✅ Encontrados {len(rows)} lançamento(s) do dia 08/01/2026:\n")
    
    for i, row in enumerate(rows[:20], 1):  # Mostrar apenas os primeiros 20
        if isinstance(row, dict):
            id_mov = row.get('id_movimentacao', '')
            data_mov = row.get('data_movimentacao', '')
            data_lanc = row.get('data_lancamento', '')
            valor = row.get('valor_movimentacao', 0)
            sinal = row.get('sinal_movimentacao', '')
            descricao = row.get('descricao_movimentacao', '')[:50]
            criado_em = row.get('criado_em', '')
        else:
            id_mov = row[0] if len(row) > 0 else ''
            data_mov = row[4] if len(row) > 4 else ''
            data_lanc = row[5] if len(row) > 5 else ''
            valor = row[6] if len(row) > 6 else 0
            sinal = row[7] if len(row) > 7 else ''
            descricao = (row[8] if len(row) > 8 else '')[:50]
            criado_em = row[9] if len(row) > 9 else ''
        
        sinal_exibicao = '-' if sinal == 'D' else '+'
        print(f"{i}. ID: {id_mov}")
        print(f"   Data movimentação: {data_mov}")
        print(f"   Data lançamento: {data_lanc}")
        print(f"   Valor: {sinal_exibicao}R$ {valor:,.2f}")
        print(f"   Descrição: {descricao}")
        print(f"   Criado em: {criado_em}")
        print()
    
    if len(rows) > 20:
        print(f"... e mais {len(rows) - 20} lançamento(s)")

if __name__ == '__main__':
    verificar_lancamentos_dia_08()


