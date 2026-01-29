#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar lançamentos bancários no banco de dados.

Verifica:
1. Total de lançamentos na tabela MOVIMENTACAO_BANCARIA
2. Lançamentos do Santander
3. Lançamentos não classificados
4. Lançamentos classificados
5. Compara com o que a conciliação está retornando
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter
import json

def main():
    print("=" * 80)
    print("🔍 DIAGNÓSTICO DE LANÇAMENTOS BANCÁRIOS NO BANCO DE DADOS")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    database_padrao = adapter.database
    print(f"📊 Banco de dados padrão (do .env): {database_padrao}")
    print()
    
    # ✅ NOVO: Testar ambos os bancos (Make e mAIke_assistente)
    bancos_para_testar = [database_padrao, 'mAIke_assistente', 'Make']
    bancos_para_testar = list(dict.fromkeys(bancos_para_testar))  # Remove duplicatas mantendo ordem
    
    print(f"🔍 Testando bancos: {', '.join(bancos_para_testar)}")
    print()
    
    # 1. Total de lançamentos (testar em todos os bancos)
    print("1️⃣ TOTAL DE LANÇAMENTOS POR BANCO")
    print("-" * 80)
    query_total = """
        SELECT COUNT(*) as total
        FROM dbo.MOVIMENTACAO_BANCARIA
    """
    for db_name in bancos_para_testar:
        resultado_total = adapter.execute_query(query_total, database=db_name)
        if resultado_total.get('success') and resultado_total.get('data'):
            total = resultado_total['data'][0].get('total', 0) if resultado_total['data'] else 0
            print(f"   📊 {db_name}: {total} lançamento(s)")
        else:
            error_msg = resultado_total.get('error', 'Erro desconhecido')
            print(f"   ❌ {db_name}: Erro - {error_msg}")
    print()
    
    # Determinar qual banco tem dados
    banco_com_dados = None
    for db_name in bancos_para_testar:
        resultado_total = adapter.execute_query(query_total, database=db_name)
        if resultado_total.get('success') and resultado_total.get('data'):
            total = resultado_total['data'][0].get('total', 0) if resultado_total['data'] else 0
            if total > 0:
                banco_com_dados = db_name
                break
    
    if not banco_com_dados:
        print("⚠️ Nenhum banco encontrado com lançamentos!")
        return
    
    print(f"✅ Usando banco: {banco_com_dados} (tem lançamentos)")
    database = banco_com_dados
    print()
    
    # 2. Lançamentos por banco
    print("2️⃣ LANÇAMENTOS POR BANCO")
    print("-" * 80)
    query_por_banco = """
        SELECT 
            banco_origem,
            COUNT(*) as total
        FROM dbo.MOVIMENTACAO_BANCARIA
        GROUP BY banco_origem
        ORDER BY banco_origem
    """
    resultado_banco = adapter.execute_query(query_por_banco, database=database)
    if resultado_banco.get('success') and resultado_banco.get('data'):
        for row in resultado_banco['data']:
            banco = row.get('banco_origem', 'N/A')
            total = row.get('total', 0)
            print(f"   • {banco}: {total} lançamento(s)")
    else:
        print(f"   ❌ Erro: {resultado_banco.get('error')}")
    print()
    
    # 3. Lançamentos do Santander
    print("3️⃣ LANÇAMENTOS DO SANTANDER (ÚLTIMOS 10)")
    print("-" * 80)
    query_santander = """
        SELECT TOP 10
            id_movimentacao,
            banco_origem,
            agencia_origem,
            conta_origem,
            data_movimentacao,
            valor_movimentacao,
            sinal_movimentacao,
            descricao_movimentacao,
            processo_referencia,
            criado_em
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'SANTANDER'
        ORDER BY data_movimentacao DESC, criado_em DESC
    """
    resultado_santander = adapter.execute_query(query_santander, database=database)
    if resultado_santander.get('success') and resultado_santander.get('data'):
        lancamentos = resultado_santander['data']
        print(f"   ✅ Encontrados {len(lancamentos)} lançamento(s) do Santander")
        for i, lanc in enumerate(lancamentos, 1):
            print(f"   {i}. ID: {lanc.get('id_movimentacao')}")
            print(f"      Data: {lanc.get('data_movimentacao')}")
            print(f"      Valor: R$ {lanc.get('valor_movimentacao', 0):.2f} ({lanc.get('sinal_movimentacao', 'N/A')})")
            print(f"      Descrição: {lanc.get('descricao_movimentacao', 'N/A')[:60]}...")
            print(f"      Processo: {lanc.get('processo_referencia', 'N/A')}")
            print()
    else:
        print(f"   ❌ Erro: {resultado_santander.get('error')}")
    print()
    
    # 4. Total de lançamentos não classificados
    print("4️⃣ LANÇAMENTOS NÃO CLASSIFICADOS")
    print("-" * 80)
    query_nao_classificados = """
        SELECT COUNT(*) as total
        FROM dbo.MOVIMENTACAO_BANCARIA mb
        WHERE NOT EXISTS (
            SELECT 1
            FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
            WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao
        )
    """
    resultado_nao_class = adapter.execute_query(query_nao_classificados, database=database)
    if resultado_nao_class.get('success') and resultado_nao_class.get('data'):
        total_nao_class = resultado_nao_class['data'][0].get('total', 0) if resultado_nao_class['data'] else 0
        print(f"   ✅ Total de lançamentos NÃO classificados: {total_nao_class}")
    else:
        print(f"   ❌ Erro: {resultado_nao_class.get('error')}")
    print()
    
    # 5. Lançamentos não classificados do Santander (últimos 10)
    print("5️⃣ LANÇAMENTOS NÃO CLASSIFICADOS DO SANTANDER (ÚLTIMOS 10)")
    print("-" * 80)
    query_nao_class_santander = """
        SELECT TOP 10
            mb.id_movimentacao,
            mb.banco_origem,
            mb.agencia_origem,
            mb.conta_origem,
            mb.data_movimentacao,
            mb.valor_movimentacao,
            mb.sinal_movimentacao,
            mb.descricao_movimentacao,
            mb.processo_referencia,
            mb.criado_em
        FROM dbo.MOVIMENTACAO_BANCARIA mb
        WHERE mb.banco_origem = 'SANTANDER'
        AND NOT EXISTS (
            SELECT 1
            FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
            WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao
        )
        ORDER BY mb.data_movimentacao DESC, mb.criado_em DESC
    """
    resultado_nao_class_sant = adapter.execute_query(query_nao_class_santander, database=database)
    if resultado_nao_class_sant.get('success') and resultado_nao_class_sant.get('data'):
        lancamentos = resultado_nao_class_sant['data']
        print(f"   ✅ Encontrados {len(lancamentos)} lançamento(s) não classificados do Santander")
        for i, lanc in enumerate(lancamentos, 1):
            print(f"   {i}. ID: {lanc.get('id_movimentacao')}")
            print(f"      Data: {lanc.get('data_movimentacao')}")
            print(f"      Valor: R$ {lanc.get('valor_movimentacao', 0):.2f} ({lanc.get('sinal_movimentacao', 'N/A')})")
            print(f"      Descrição: {lanc.get('descricao_movimentacao', 'N/A')[:60]}...")
            print()
    else:
        print(f"   ❌ Erro: {resultado_nao_class_sant.get('error')}")
        if resultado_nao_class_sant.get('error'):
            print(f"      Mensagem: {resultado_nao_class_sant.get('error')}")
    print()
    
    # 6. Verificar se tabela LANCAMENTO_TIPO_DESPESA existe e tem dados
    print("6️⃣ VERIFICAR TABELA LANCAMENTO_TIPO_DESPESA")
    print("-" * 80)
    query_tabela = """
        SELECT COUNT(*) as total
        FROM dbo.LANCAMENTO_TIPO_DESPESA
    """
    resultado_tabela = adapter.execute_query(query_tabela, database=database)
    if resultado_tabela.get('success') and resultado_tabela.get('data'):
        total_class = resultado_tabela['data'][0].get('total', 0) if resultado_tabela['data'] else 0
        print(f"   ✅ Total de classificações na tabela: {total_class}")
    else:
        error_msg = resultado_tabela.get('error', 'Erro desconhecido')
        print(f"   ⚠️ Erro ao consultar tabela: {error_msg}")
        print(f"      (Pode ser que a tabela não exista ou esteja em outro banco)")
    print()
    
    # 7. Verificar estrutura da query que a conciliação usa (testar em todos os bancos)
    print("7️⃣ TESTAR QUERY EXATA DA CONCILIAÇÃO (TODOS OS BANCOS)")
    print("-" * 80)
    query_concil = """
        SELECT
            mb.id_movimentacao,
            mb.banco_origem,
            mb.agencia_origem,
            mb.conta_origem,
            mb.data_movimentacao,
            mb.data_lancamento,
            mb.valor_movimentacao,
            mb.sinal_movimentacao,
            mb.tipo_movimentacao,
            mb.descricao_movimentacao,
            mb.cpf_cnpj_contrapartida,
            mb.nome_contrapartida,
            mb.processo_referencia,
            mb.criado_em
        FROM dbo.MOVIMENTACAO_BANCARIA mb
        WHERE NOT EXISTS (
            SELECT 1
            FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
            WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao
        )
        ORDER BY mb.data_movimentacao DESC, mb.criado_em DESC
    """
    for db_name in bancos_para_testar:
        print(f"   🔍 Testando banco: {db_name}")
        resultado_concil = adapter.execute_query(query_concil, database=db_name)
        if resultado_concil.get('success') and resultado_concil.get('data'):
            lancamentos = resultado_concil['data']
            print(f"      ✅ Query retornou {len(lancamentos)} lançamento(s) não classificados")
            if len(lancamentos) > 0:
                print(f"      📋 Primeiros 3 lançamentos:")
                for i, lanc in enumerate(lancamentos[:3], 1):
                    print(f"         {i}. ID: {lanc.get('id_movimentacao')} | {lanc.get('banco_origem')} | {lanc.get('data_movimentacao')} | R$ {lanc.get('valor_movimentacao', 0):.2f}")
        else:
            error_msg = resultado_concil.get('error', 'Erro desconhecido')
            print(f"      ❌ Erro: {error_msg}")
        print()
    
    print("=" * 80)
    print("✅ DIAGNÓSTICO CONCLUÍDO")
    print("=" * 80)

if __name__ == '__main__':
    main()
