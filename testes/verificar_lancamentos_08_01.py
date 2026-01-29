#!/usr/bin/env python3
"""
Script para verificar se os lançamentos do dia 08/01/2026 do Santander foram sincronizados.
"""

import sys
import os
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utils.sql_server_adapter import get_sql_adapter

def verificar_lancamentos_08_01():
    """Verifica se há lançamentos do dia 08/01/2026 do Santander no banco."""
    
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server adapter não disponível")
        return
    
    # Query para buscar lançamentos do dia 08/01/2026 do Santander
    query = """
        SELECT 
            id_movimentacao,
            banco_origem,
            data_movimentacao,
            descricao_movimentacao,
            valor_movimentacao,
            sinal_movimentacao,
            criado_em
        FROM mAIke_assistente.dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'SANTANDER'
            AND CAST(data_movimentacao AS DATE) = '2026-01-08'
        ORDER BY data_movimentacao DESC, criado_em DESC
    """
    
    print("🔍 Buscando lançamentos do Santander do dia 08/01/2026...")
    resultado = adapter.execute_query(query, database='mAIke_assistente')
    
    if not resultado.get('success'):
        print(f"❌ Erro ao consultar: {resultado.get('error', 'Erro desconhecido')}")
        return
    
    rows = resultado.get('data', [])
    
    if not rows:
        print("⚠️ Nenhum lançamento do dia 08/01/2026 encontrado no banco!")
        print("\n💡 Isso significa que os lançamentos ainda não foram sincronizados.")
        print("   Solução: Sincronize novamente os extratos do Santander via UI.")
        
        # Verificar lançamentos mais recentes
        query_recentes = """
            SELECT TOP 5
                CAST(data_movimentacao AS DATE) as data,
                COUNT(*) as total
            FROM mAIke_assistente.dbo.MOVIMENTACAO_BANCARIA
            WHERE banco_origem = 'SANTANDER'
            GROUP BY CAST(data_movimentacao AS DATE)
            ORDER BY data DESC
        """
        
        resultado_recentes = adapter.execute_query(query_recentes, database='mAIke_assistente')
        if resultado_recentes.get('success'):
            rows_recentes = resultado_recentes.get('data', [])
            if rows_recentes:
                print("\n📊 Datas mais recentes de lançamentos do Santander no banco:")
                for row in rows_recentes:
                    data = row.get('data') if isinstance(row, dict) else row[0]
                    total = row.get('total') if isinstance(row, dict) else row[1]
                    print(f"   • {data}: {total} lançamento(s)")
    else:
        print(f"✅ Encontrados {len(rows)} lançamento(s) do dia 08/01/2026:")
        for i, row in enumerate(rows[:10], 1):
            if isinstance(row, dict):
                id_mov = row.get('id_movimentacao')
                data = row.get('data_movimentacao')
                desc = row.get('descricao_movimentacao', '')[:50]
                valor = row.get('valor_movimentacao', 0)
                sinal = row.get('sinal_movimentacao', 'C')
                print(f"   {i}. [{id_mov}] {data} - {sinal}R$ {valor:,.2f} - {desc}...")
            else:
                print(f"   {i}. {row}")
        
        if len(rows) > 10:
            print(f"   ... e mais {len(rows) - 10} lançamento(s)")

if __name__ == '__main__':
    verificar_lancamentos_08_01()


