#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script rápido para verificar lançamentos com um valor específico.

Uso:
    python3 scripts/verificar_lancamentos_valor.py --valor 13337.88
    python3 scripts/verificar_lancamentos_valor.py --valor 13337.88 --banco BB
"""

import sys
import os
import argparse
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter

def formatar_valor(valor: float) -> str:
    """Formata valor monetário."""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_data(data_str: str) -> str:
    """Formata data para exibição."""
    try:
        if isinstance(data_str, str):
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(data_str.split()[0], fmt)
                    return dt.strftime('%d/%m/%Y')
                except:
                    continue
        return str(data_str)
    except:
        return str(data_str)

def main():
    parser = argparse.ArgumentParser(description='Verificar lançamentos com valor específico')
    parser.add_argument('--valor', type=float, required=True, help='Valor a buscar (ex: 13337.88)')
    parser.add_argument('--banco', type=str, choices=['BB', 'SANTANDER'], help='Filtrar por banco')
    parser.add_argument('--database', type=str, default='mAIke_assistente', help='Database a usar')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"🔍 VERIFICANDO LANÇAMENTOS COM VALOR: {formatar_valor(args.valor)}")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ Erro: Não foi possível conectar ao SQL Server")
        return 1
    
    # Construir query
    where_clauses = [
        f"ABS(valor_movimentacao - {args.valor}) < 0.01"  # Tolerância de 1 centavo
    ]
    
    if args.banco:
        where_clauses.append(f"banco_origem = '{args.banco}'")
    
    where_sql = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            id_movimentacao,
            banco_origem,
            agencia_origem,
            conta_origem,
            CAST(data_movimentacao AS DATE) as data_movimentacao_date,
            valor_movimentacao,
            sinal_movimentacao,
            CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao,
            hash_dados,
            criado_em,
            fonte_dados,
            CAST(json_dados_originais AS VARCHAR(MAX)) as json_original
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE {where_sql}
        ORDER BY CAST(data_movimentacao AS DATE) DESC, criado_em DESC
    """
    
    resultado = adapter.execute_query(query, database=args.database)
    if not resultado.get('success'):
        print(f"❌ Erro ao buscar lançamentos: {resultado.get('error', 'Erro desconhecido')}")
        return 1
    
    lancamentos = resultado.get('data', [])
    
    if not lancamentos:
        print(f"❌ Nenhum lançamento encontrado com valor {formatar_valor(args.valor)}")
        if args.banco:
            print(f"   (filtrado por banco: {args.banco})")
        return 0
    
    print(f"📊 Encontrados {len(lancamentos)} lançamento(s):\n")
    
    for i, lanc in enumerate(lancamentos, 1):
        print(f"{'=' * 80}")
        print(f"📦 LANÇAMENTO {i}")
        print(f"{'=' * 80}")
        print(f"   ID: {lanc.get('id_movimentacao')}")
        print(f"   Banco: {lanc.get('banco_origem')}")
        print(f"   Agência: {lanc.get('agencia_origem')}")
        print(f"   Conta: {lanc.get('conta_origem')}")
        print(f"   Data: {formatar_data(str(lanc.get('data_movimentacao_date', 'N/A')))}")
        print(f"   Valor: {formatar_valor(float(lanc.get('valor_movimentacao', 0)))} ({lanc.get('sinal_movimentacao', 'N/A')})")
        print(f"   Descrição: {lanc.get('descricao_movimentacao', 'N/A')[:100]}...")
        print(f"   Hash: {lanc.get('hash_dados', 'N/A')[:32]}...")
        print(f"   Criado em: {formatar_data(str(lanc.get('criado_em', 'N/A')))}")
        print(f"   Fonte: {lanc.get('fonte_dados', 'N/A')}")
        
        # Tentar extrair identificador único do JSON
        json_original = lanc.get('json_original', '')
        if json_original:
            try:
                json_data = json.loads(json_original)
                banco = lanc.get('banco_origem', '')
                if banco == 'BB':
                    num_doc = json_data.get('numeroDocumento') or json_data.get('numeroLote')
                    if num_doc:
                        print(f"   ✅ Número Documento: {num_doc}")
                elif banco == 'SANTANDER':
                    trans_id = json_data.get('transactionId')
                    if trans_id:
                        print(f"   ✅ Transaction ID: {trans_id}")
            except Exception as e:
                print(f"   ⚠️  Erro ao parsear JSON: {e}")
        
        print()
    
    # Verificar se há duplicatas (mesmo hash)
    hashes = {}
    for lanc in lancamentos:
        hash_val = lanc.get('hash_dados', '')
        if hash_val:
            if hash_val not in hashes:
                hashes[hash_val] = []
            hashes[hash_val].append(lanc.get('id_movimentacao'))
    
    duplicatas = {h: ids for h, ids in hashes.items() if len(ids) > 1}
    if duplicatas:
        print(f"\n⚠️  ATENÇÃO: {len(duplicatas)} hash(es) duplicado(s) encontrado(s):")
        for hash_val, ids in duplicatas.items():
            print(f"   Hash {hash_val[:16]}... aparece em {len(ids)} lançamento(s): IDs {ids}")
    else:
        print(f"\n✅ Todos os lançamentos têm hashes únicos (não são duplicatas)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
