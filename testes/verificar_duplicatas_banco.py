#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar se há lançamentos no banco e de quais contas são.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_server_adapter import get_sql_adapter

def verificar_duplicatas():
    """Verifica lançamentos no banco de dados."""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE LANÇAMENTOS NO BANCO")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    
    if not adapter.test_connection():
        print("❌ SQL Server não está acessível.")
        return
    
    print(f"✅ Conectado ao banco: {adapter.database}")
    print()
    
    # 1. Total de lançamentos
    query_total = """
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT CONCAT(agencia_origem, '-', conta_origem)) as contas_distintas
    FROM dbo.MOVIMENTACAO_BANCARIA
    WHERE banco_origem = 'BB'
    """
    
    result = adapter.execute_query(query_total, database=adapter.database)
    if result.get('success') and result.get('data'):
        row = result['data'][0]
        total = row.get('total', 0)
        contas = row.get('contas_distintas', 0)
        print(f"📊 Total de lançamentos BB: {total}")
        print(f"📊 Contas distintas: {contas}")
        print()
        
        if total == 0:
            print("✅ Banco está VAZIO - Não há duplicatas!")
            return
    
    # 2. Lançamentos por conta
    query_contas = """
    SELECT 
        agencia_origem,
        conta_origem,
        COUNT(*) as total,
        MIN(data_movimentacao) as primeira,
        MAX(data_movimentacao) as ultima
    FROM dbo.MOVIMENTACAO_BANCARIA
    WHERE banco_origem = 'BB'
    GROUP BY agencia_origem, conta_origem
    ORDER BY total DESC
    """
    
    result = adapter.execute_query(query_contas, database=adapter.database)
    if result.get('success') and result.get('data'):
        rows = result['data']
        print("📊 LANÇAMENTOS POR CONTA:")
        print("-" * 80)
        for row in rows:
            ag = row.get('agencia_origem', '—')
            ct = row.get('conta_origem', '—')
            total = row.get('total', 0)
            primeira = row.get('primeira', '—')
            ultima = row.get('ultima', '—')
            print(f"   Ag. {ag} / C/C {ct}: {total} lançamentos")
            print(f"      Período: {primeira} até {ultima}")
            print()
    
    # 3. Exemplo de hashes duplicados (se houver)
    query_hashes = """
    SELECT TOP 5
        hash_dados,
        COUNT(*) as quantidade,
        MIN(CONCAT(agencia_origem, '-', conta_origem)) as contas_afetadas
    FROM dbo.MOVIMENTACAO_BANCARIA
    WHERE banco_origem = 'BB' AND hash_dados IS NOT NULL
    GROUP BY hash_dados
    HAVING COUNT(*) > 1
    ORDER BY quantidade DESC
    """
    
    result = adapter.execute_query(query_hashes, database=adapter.database)
    if result.get('success') and result.get('data'):
        rows = result['data']
        if len(rows) > 0:
            print("⚠️ HAShes DUPLICADOS ENCONTRADOS:")
            print("-" * 80)
            for row in rows:
                hash_val = row.get('hash_dados', '—')
                qtd = row.get('quantidade', 0)
                contas = row.get('contas_afetadas', '—')
                print(f"   Hash {hash_val[:20]}...: {qtd} ocorrências")
                print(f"      Contas: {contas}")
                print()
        else:
            print("✅ Nenhum hash duplicado encontrado")
    
    print("=" * 80)

if __name__ == '__main__':
    verificar_duplicatas()

