#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para identificar e corrigir duplicatas incorretas de lançamentos bancários.

PROBLEMA:
Dois lançamentos com mesmo valor, mesma data, mesmo banco e mesma descrição
podem ter sido marcados incorretamente como duplicados se o hash antigo não
incluía o identificador único (numeroDocumento/transactionId).

SOLUÇÃO:
1. Identifica grupos de lançamentos suspeitos (mesmo valor, data, banco, descrição)
2. Verifica se têm hash diferente (indicando que são lançamentos diferentes)
3. Permite re-sincronizar ou corrigir manualmente

USO:
    # Dry-run (apenas análise)
    python3 scripts/corrigir_duplicatas_incorretas_banco.py --dry-run

    # Análise completa
    python3 scripts/corrigir_duplicatas_incorretas_banco.py --analise

    # Corrigir (requer confirmação)
    python3 scripts/corrigir_duplicatas_incorretas_banco.py --corrigir
"""

import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter
from services.banco_sincronizacao_service import BancoSincronizacaoService

def formatar_valor(valor: float) -> str:
    """Formata valor monetário."""
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def formatar_data(data_str: str) -> str:
    """Formata data para exibição."""
    try:
        if isinstance(data_str, str):
            # Tentar parsear diferentes formatos
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(data_str.split()[0], fmt)
                    return dt.strftime('%d/%m/%Y')
                except:
                    continue
        return str(data_str)
    except:
        return str(data_str)

def identificar_grupos_suspeitos(adapter, database: str = 'mAIke_assistente') -> List[Dict[str, Any]]:
    """
    Identifica grupos de lançamentos que podem ser duplicatas incorretas.
    
    Critérios:
    - Mesmo banco, agência, conta
    - Mesma data (apenas data, ignorando hora)
    - Mesmo valor absoluto
    - Mesmo sinal (C ou D)
    - Descrição similar (primeiros 50 caracteres)
    - Hash diferente OU múltiplos IDs com mesmo hash
    """
    query = f"""
        SELECT 
            id_movimentacao,
            banco_origem,
            agencia_origem,
            conta_origem,
            CAST(data_movimentacao AS DATE) as data_movimentacao_date,
            valor_movimentacao,
            sinal_movimentacao,
            LEFT(CAST(descricao_movimentacao AS VARCHAR(MAX)), 50) as descricao_resumida,
            CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao,
            hash_dados,
            criado_em,
            fonte_dados,
            CAST(json_dados_originais AS VARCHAR(MAX)) as json_original
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem IN ('BB', 'SANTANDER')
        ORDER BY banco_origem, CAST(data_movimentacao AS DATE), ABS(valor_movimentacao), sinal_movimentacao
    """
    
    resultado = adapter.execute_query(query, database=database)
    if not resultado.get('success') or not resultado.get('data'):
        print(f"❌ Erro ao buscar lançamentos: {resultado.get('error', 'Erro desconhecido')}")
        return []
    
    lancamentos = resultado['data']
    print(f"📊 Total de lançamentos encontrados: {len(lancamentos)}")
    
    # Agrupar por: banco + agencia + conta + data + valor_abs + sinal + descricao_resumida
    grupos = defaultdict(list)
    
    for lanc in lancamentos:
        chave = (
            lanc.get('banco_origem', ''),
            lanc.get('agencia_origem', ''),
            lanc.get('conta_origem', ''),
            str(lanc.get('data_movimentacao_date', '')),
            abs(float(lanc.get('valor_movimentacao', 0))),
            lanc.get('sinal_movimentacao', ''),
            lanc.get('descricao_resumida', '')[:50].strip()
        )
        grupos[chave].append(lanc)
    
    # Filtrar apenas grupos com mais de 1 lançamento (suspeitos)
    grupos_suspeitos = []
    for chave, grupo in grupos.items():
        if len(grupo) > 1:
            # Verificar se têm hash diferente (indicando que são lançamentos diferentes)
            hashes = set(l.get('hash_dados', '') for l in grupo)
            if len(hashes) > 1:
                # Múltiplos hashes diferentes = possível duplicata incorreta
                grupos_suspeitos.append({
                    'chave': chave,
                    'lançamentos': grupo,
                    'hashes_diferentes': len(hashes),
                    'total': len(grupo)
                })
            elif len(grupo) > 1:
                # Mesmo hash mas múltiplos IDs = possível duplicata incorreta também
                grupos_suspeitos.append({
                    'chave': chave,
                    'lançamentos': grupo,
                    'hashes_diferentes': 1,
                    'total': len(grupo)
                })
    
    return grupos_suspeitos

def analisar_grupos_suspeitos(grupos: List[Dict[str, Any]]) -> None:
    """Analisa e exibe grupos suspeitos."""
    print("\n" + "=" * 80)
    print(f"🔍 ANÁLISE: {len(grupos)} grupo(s) suspeito(s) encontrado(s)")
    print("=" * 80)
    
    if not grupos:
        print("✅ Nenhum grupo suspeito encontrado!")
        return
    
    for idx, grupo_info in enumerate(grupos, 1):
        chave = grupo_info['chave']
        lancamentos = grupo_info['lançamentos']
        hashes_diferentes = grupo_info['hashes_diferentes']
        
        banco, agencia, conta, data, valor_abs, sinal, descricao = chave
        
        print(f"\n{'=' * 80}")
        print(f"📦 GRUPO {idx}: {len(lancamentos)} lançamento(s) suspeito(s)")
        print(f"{'=' * 80}")
        print(f"   Banco: {banco}")
        print(f"   Agência: {agencia}")
        print(f"   Conta: {conta}")
        print(f"   Data: {formatar_data(data)}")
        print(f"   Valor: {formatar_valor(valor_abs)} ({sinal})")
        print(f"   Descrição: {descricao[:50]}...")
        print(f"   Hashes diferentes: {hashes_diferentes}")
        print()
        
        for i, lanc in enumerate(lancamentos, 1):
            print(f"   {i}. ID: {lanc.get('id_movimentacao')}")
            print(f"      Hash: {lanc.get('hash_dados', 'N/A')[:16]}...")
            print(f"      Criado em: {formatar_data(str(lanc.get('criado_em', 'N/A')))}")
            print(f"      Fonte: {lanc.get('fonte_dados', 'N/A')}")
            
            # Tentar extrair numeroDocumento/transactionId do JSON original
            json_original = lanc.get('json_original', '')
            if json_original:
                try:
                    import json
                    json_data = json.loads(json_original)
                    if banco == 'BB':
                        num_doc = json_data.get('numeroDocumento') or json_data.get('numeroLote')
                        if num_doc:
                            print(f"      Número Documento: {num_doc}")
                    elif banco == 'SANTANDER':
                        trans_id = json_data.get('transactionId')
                        if trans_id:
                            print(f"      Transaction ID: {trans_id}")
                except:
                    pass
            
            print()

def corrigir_duplicatas_incorretas(adapter, grupos: List[Dict[str, Any]], database: str = 'mAIke_assistente', dry_run: bool = True) -> None:
    """
    Corrige duplicatas incorretas.
    
    Estratégia:
    1. Para cada grupo suspeito, verificar se realmente são lançamentos diferentes
    2. Se forem diferentes (baseado no JSON original), manter todos
    3. Se forem realmente duplicados, manter apenas o mais antigo
    """
    if not grupos:
        print("✅ Nenhum grupo suspeito para corrigir.")
        return
    
    print("\n" + "=" * 80)
    print(f"🔧 CORREÇÃO DE DUPLICATAS INCORRETAS")
    print("=" * 80)
    
    if dry_run:
        print("⚠️  MODO DRY-RUN: Nenhuma alteração será feita no banco de dados.")
    else:
        print("⚠️  MODO REAL: Alterações serão aplicadas no banco de dados!")
        resposta = input("\n❓ Confirma que deseja continuar? (digite 'SIM' para confirmar): ")
        if resposta != 'SIM':
            print("❌ Operação cancelada pelo usuário.")
            return
    
    import json
    
    total_corrigidos = 0
    total_mantidos = 0
    
    for grupo_info in grupos:
        chave = grupo_info['chave']
        lancamentos = grupo_info['lançamentos']
        banco = chave[0]
        
        print(f"\n📦 Processando grupo: {banco} - {formatar_data(chave[3])} - {formatar_valor(chave[4])}")
        
        # Verificar se são realmente diferentes baseado no JSON original
        identificadores = []
        for lanc in lancamentos:
            json_original = lanc.get('json_original', '')
            identificador = None
            
            if json_original:
                try:
                    json_data = json.loads(json_original)
                    if banco == 'BB':
                        identificador = json_data.get('numeroDocumento') or json_data.get('numeroLote')
                    elif banco == 'SANTANDER':
                        identificador = json_data.get('transactionId')
                except:
                    pass
            
            identificadores.append({
                'id_movimentacao': lanc.get('id_movimentacao'),
                'identificador': identificador,
                'criado_em': lanc.get('criado_em'),
                'hash': lanc.get('hash_dados', '')
            })
        
        # Se todos têm identificadores diferentes, são lançamentos diferentes (manter todos)
        ids_unicos = set(i['identificador'] for i in identificadores if i['identificador'])
        if len(ids_unicos) == len(identificadores) and len(ids_unicos) > 1:
            print(f"   ✅ Todos os {len(identificadores)} lançamentos têm identificadores únicos diferentes - são lançamentos distintos (manter todos)")
            total_mantidos += len(identificadores)
            continue
        
        # Se têm mesmo identificador ou não têm identificador, verificar hash
        # Se hash diferente, são lançamentos diferentes (manter todos)
        hashes = set(i['hash'] for i in identificadores if i['hash'])
        if len(hashes) == len(identificadores) and len(hashes) > 1:
            print(f"   ✅ Todos os {len(identificadores)} lançamentos têm hashes diferentes - são lançamentos distintos (manter todos)")
            total_mantidos += len(identificadores)
            continue
        
        # Se chegou aqui, provavelmente são duplicatas reais
        # Manter apenas o mais antigo
        identificadores_ordenados = sorted(identificadores, key=lambda x: x['criado_em'] or '')
        manter = identificadores_ordenados[0]
        deletar = identificadores_ordenados[1:]
        
        print(f"   ⚠️  {len(identificadores)} lançamento(s) com mesmo identificador/hash")
        print(f"   ✅ Manter: ID {manter['id_movimentacao']} (mais antigo)")
        
        for del_item in deletar:
            print(f"   🗑️  Deletar: ID {del_item['id_movimentacao']}")
            
            if not dry_run:
                query_delete = f"""
                    DELETE FROM dbo.MOVIMENTACAO_BANCARIA
                    WHERE id_movimentacao = {del_item['id_movimentacao']}
                """
                resultado = adapter.execute_query(query_delete, database=database)
                if resultado.get('success'):
                    print(f"      ✅ Deletado com sucesso")
                    total_corrigidos += 1
                else:
                    print(f"      ❌ Erro ao deletar: {resultado.get('error', 'Erro desconhecido')}")
            else:
                total_corrigidos += 1
    
    print("\n" + "=" * 80)
    print("📊 RESUMO DA CORREÇÃO")
    print("=" * 80)
    print(f"   ✅ Lançamentos mantidos (distintos): {total_mantidos}")
    print(f"   🗑️  Lançamentos {'que seriam deletados' if dry_run else 'deletados'}: {total_corrigidos}")
    
    if dry_run:
        print("\n💡 Para aplicar as correções, execute novamente sem --dry-run")

def main():
    parser = argparse.ArgumentParser(description='Identificar e corrigir duplicatas incorretas de lançamentos bancários')
    parser.add_argument('--dry-run', action='store_true', help='Apenas análise, não aplica correções')
    parser.add_argument('--analise', action='store_true', help='Apenas análise detalhada')
    parser.add_argument('--corrigir', action='store_true', help='Aplicar correções (requer confirmação)')
    parser.add_argument('--database', type=str, default='mAIke_assistente', help='Database a usar (padrão: mAIke_assistente)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🔍 CORREÇÃO DE DUPLICATAS INCORRETAS - LANÇAMENTOS BANCÁRIOS")
    print("=" * 80)
    print()
    
    # Inicializar adapter
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ Erro: Não foi possível conectar ao SQL Server")
        return 1
    
    database = args.database
    print(f"📊 Database: {database}")
    print()
    
    # Identificar grupos suspeitos
    print("🔍 Identificando grupos suspeitos...")
    grupos = identificar_grupos_suspeitos(adapter, database=database)
    
    if not grupos:
        print("✅ Nenhum grupo suspeito encontrado!")
        return 0
    
    # Análise
    analisar_grupos_suspeitos(grupos)
    
    # Correção (se solicitado)
    if args.corrigir:
        corrigir_duplicatas_incorretas(adapter, grupos, database=database, dry_run=False)
    elif args.analise or args.dry_run:
        print("\n💡 Para aplicar correções, execute com --corrigir")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
