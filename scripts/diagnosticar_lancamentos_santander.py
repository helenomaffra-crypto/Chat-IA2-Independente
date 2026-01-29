"""
Script de diagnóstico para verificar lançamentos do Santander no banco de dados.
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

def diagnosticar_lancamentos():
    """Diagnostica lançamentos do Santander nos dias 07 e 08 de janeiro."""
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server não disponível")
        return
    
    database = 'mAIke_assistente'
    
    # Verificar lançamentos do dia 07/01/2026
    print("🔍 Lançamentos do Santander - 07/01/2026:\n")
    query_07 = """
        SELECT TOP 20
            id_movimentacao,
            CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao,
            valor_movimentacao,
            sinal_movimentacao,
            CAST(data_movimentacao AS DATE) as data
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'SANTANDER'
          AND CAST(data_movimentacao AS DATE) = '2026-01-07'
        ORDER BY valor_movimentacao DESC
    """
    
    resultado_07 = adapter.execute_query(query_07, database=database)
    if resultado_07.get('success') and resultado_07.get('data'):
        rows_07 = resultado_07['data']
        print(f"📊 Total encontrado: {len(rows_07)} lançamentos\n")
        for i, row in enumerate(rows_07[:10], 1):
            if isinstance(row, dict):
                id_mov = row.get('id_movimentacao')
                desc = row.get('descricao', '')[:60]
                valor = row.get('valor_movimentacao', 0)
                sinal = row.get('sinal_movimentacao', '')
                data = row.get('data', '')
            else:
                id_mov = row[0] if len(row) > 0 else None
                desc = (row[1] if len(row) > 1 else '')[:60]
                valor = row[2] if len(row) > 2 else 0
                sinal = row[3] if len(row) > 3 else ''
                data = row[4] if len(row) > 4 else ''
            
            sinal_exib = '-' if sinal == 'D' else '+'
            print(f"{i}. ID {id_mov} | {sinal_exib}R$ {valor:,.2f} | {desc}")
    else:
        print("❌ Nenhum lançamento encontrado para 07/01/2026")
    
    print("\n" + "="*80 + "\n")
    
    # Verificar lançamentos do dia 08/01/2026
    print("🔍 Lançamentos do Santander - 08/01/2026:\n")
    query_08 = """
        SELECT TOP 20
            id_movimentacao,
            CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao,
            valor_movimentacao,
            sinal_movimentacao,
            CAST(data_movimentacao AS DATE) as data
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'SANTANDER'
          AND CAST(data_movimentacao AS DATE) = '2026-01-08'
        ORDER BY valor_movimentacao DESC
    """
    
    resultado_08 = adapter.execute_query(query_08, database=database)
    if resultado_08.get('success') and resultado_08.get('data'):
        rows_08 = resultado_08['data']
        print(f"📊 Total encontrado: {len(rows_08)} lançamentos\n")
        for i, row in enumerate(rows_08[:10], 1):
            if isinstance(row, dict):
                id_mov = row.get('id_movimentacao')
                desc = row.get('descricao', '')[:60]
                valor = row.get('valor_movimentacao', 0)
                sinal = row.get('sinal_movimentacao', '')
                data = row.get('data', '')
            else:
                id_mov = row[0] if len(row) > 0 else None
                desc = (row[1] if len(row) > 1 else '')[:60]
                valor = row[2] if len(row) > 2 else 0
                sinal = row[3] if len(row) > 3 else ''
                data = row[4] if len(row) > 4 else ''
            
            sinal_exib = '-' if sinal == 'D' else '+'
            print(f"{i}. ID {id_mov} | {sinal_exib}R$ {valor:,.2f} | {desc}")
    else:
        print("❌ Nenhum lançamento encontrado para 08/01/2026")
    
    print("\n" + "="*80 + "\n")
    
    # Verificar valores específicos do dia 08 (do chat)
    valores_dia_08 = [7880.48, 272902.70, 17465.73, 498.00, 81166.63, 58471.06, 69009.44, 64255.57, 7885.55, 786.22, 5989.90, 2000.00, 2800.00, 8202.79, 573.00]
    
    print("🔍 Verificando valores específicos do dia 08/01/2026 (do chat):\n")
    for valor in valores_dia_08:
        query_valor = f"""
            SELECT 
                id_movimentacao,
                CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao,
                valor_movimentacao,
                sinal_movimentacao,
                CAST(data_movimentacao AS DATE) as data
            FROM dbo.MOVIMENTACAO_BANCARIA
            WHERE banco_origem = 'SANTANDER'
              AND ABS(valor_movimentacao - {valor}) < 0.01
              AND CAST(data_movimentacao AS DATE) IN ('2026-01-07', '2026-01-08')
            ORDER BY data DESC, id_movimentacao DESC
        """
        
        resultado_valor = adapter.execute_query(query_valor, database=database)
        if resultado_valor.get('success') and resultado_valor.get('data'):
            rows = resultado_valor['data']
            for row in rows:
                if isinstance(row, dict):
                    id_mov = row.get('id_movimentacao')
                    desc = row.get('descricao', '')[:60]
                    data = str(row.get('data', ''))[:10]
                else:
                    id_mov = row[0] if len(row) > 0 else None
                    desc = (row[1] if len(row) > 1 else '')[:60]
                    data = str(row[4] if len(row) > 4 else '')[:10]
                
                print(f"  💰 R$ {valor:,.2f} → ID {id_mov} | Data: {data} | {desc}")
                break  # Mostrar apenas o primeiro encontrado

if __name__ == '__main__':
    diagnosticar_lancamentos()


