#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar lançamentos do Banco do Brasil no banco de dados.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_server_adapter import get_sql_adapter

def formatar_brl(valor):
    """Formata valor como moeda brasileira."""
    if valor is None:
        return "—"
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return str(valor)

def formatar_data(data):
    """Formata data para exibição."""
    if data is None:
        return "—"
    try:
        if isinstance(data, str):
            return data[:19]  # Truncar se for string longa
        return data.strftime("%d/%m/%Y %H:%M:%S")
    except:
        return str(data)

def verificar_lancamentos():
    """Verifica lançamentos do Banco do Brasil no banco de dados."""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE LANÇAMENTOS - BANCO DO BRASIL")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    
    # Mostrar configuração do adapter
    print(f"🔧 Configuração:")
    print(f"   Servidor: {adapter.server}")
    print(f"   Instância: {adapter.instance or '(nenhuma)'}")
    print(f"   Banco de dados: {adapter.database}")
    print(f"   Usuário: {adapter.username}")
    print()
    
    # Verificar se SQL Server está disponível
    if not adapter.test_connection():
        print("❌ SQL Server não está acessível. Verifique a conexão.")
        return
    
    print("✅ Conectado ao SQL Server")
    print()
    
    # Verificar se o banco existe e se a tabela existe
    print("🔍 Verificando banco de dados e tabela...")
    query_check = """
    SELECT 
        DB_NAME() as banco_atual,
        CASE 
            WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'MOVIMENTACAO_BANCARIA')
            THEN 'SIM'
            ELSE 'NÃO'
        END as tabela_existe
    """
    
    try:
        result_check = adapter.execute_query(query_check)
        if result_check.get('success') and result_check.get('data'):
            row = result_check['data'][0] if len(result_check['data']) > 0 else {}
            banco = row.get('banco_atual', 'desconhecido')
            tabela_existe = row.get('tabela_existe', 'NÃO')
            print(f"   Banco atual: {banco}")
            print(f"   Tabela MOVIMENTACAO_BANCARIA existe: {tabela_existe}")
            if tabela_existe == 'NÃO':
                print()
                print("⚠️ ATENÇÃO: A tabela MOVIMENTACAO_BANCARIA não existe neste banco!")
                print("   Certifique-se de que está usando o banco 'mAIke_assistente'")
                print("   Execute o script: scripts/criar_banco_maike_completo.sql")
                print()
                return
            print()
        else:
            print(f"   ⚠️ Erro ao verificar banco: {result_check.get('error', 'Erro desconhecido')}")
            print()
    except Exception as e:
        print(f"   ⚠️ Erro ao verificar banco: {e}")
        print()
    
    try:
        # 1. Total de lançamentos do Banco do Brasil
        print("📊 1. ESTATÍSTICAS GERAIS")
        print("-" * 80)
        
        query_total = """
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT banco_origem) as bancos_distintos,
            COUNT(DISTINCT CONCAT(agencia_origem, '-', conta_origem)) as contas_distintas,
            MIN(data_movimentacao) as primeira_movimentacao,
            MAX(data_movimentacao) as ultima_movimentacao,
            MIN(criado_em) as primeiro_insert,
            MAX(criado_em) as ultimo_insert
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'BB'
        """
        
        result_total = adapter.execute_query(query_total, database=adapter.database)
        if result_total.get('success') and result_total.get('data'):
            rows = result_total['data']
            if len(rows) > 0:
                row = rows[0]
                print(f"   Total de lançamentos BB: {row.get('total', 0)}")
                print(f"   Bancos distintos: {row.get('bancos_distintos', 0)}")
                print(f"   Contas distintas: {row.get('contas_distintas', 0)}")
                print(f"   Primeira movimentação: {formatar_data(row.get('primeira_movimentacao'))}")
                print(f"   Última movimentação: {formatar_data(row.get('ultima_movimentacao'))}")
                print(f"   Primeiro insert: {formatar_data(row.get('primeiro_insert'))}")
                print(f"   Último insert: {formatar_data(row.get('ultimo_insert'))}")
            else:
                print("   Nenhum lançamento encontrado")
        else:
            error_msg = result_total.get('error', 'Erro desconhecido')
            print(f"   ❌ Erro na query: {error_msg}")
            if 'database' in str(error_msg).lower() or 'banco' in str(error_msg).lower():
                print(f"   💡 Dica: Verifique se o banco '{adapter.database}' existe e contém a tabela MOVIMENTACAO_BANCARIA")
        print()
        
        # 2. Lançamentos por conta
        print("📊 2. LANÇAMENTOS POR CONTA")
        print("-" * 80)
        
        query_contas = """
        SELECT 
            agencia_origem,
            conta_origem,
            COUNT(*) as total,
            SUM(CASE WHEN sinal_movimentacao = '+' THEN valor_movimentacao ELSE 0 END) as total_credito,
            SUM(CASE WHEN sinal_movimentacao = '-' THEN valor_movimentacao ELSE 0 END) as total_debito,
            MIN(data_movimentacao) as primeira,
            MAX(data_movimentacao) as ultima
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'BB'
        GROUP BY agencia_origem, conta_origem
        ORDER BY total DESC
        """
        
        result_contas = adapter.execute_query(query_contas, database=adapter.database)
        if result_contas.get('success') and result_contas.get('data'):
            rows = result_contas['data']
            for row in rows:
                ag = row.get('agencia_origem', '—')
                ct = row.get('conta_origem', '—')
                total = row.get('total', 0)
                credito = formatar_brl(row.get('total_credito', 0))
                debito = formatar_brl(row.get('total_debito', 0))
                primeira = formatar_data(row.get('primeira'))
                ultima = formatar_data(row.get('ultima'))
                
                print(f"   Ag. {ag} / C/C {ct}:")
                print(f"      Total: {total} lançamentos")
                print(f"      Crédito: {credito}")
                print(f"      Débito: {debito}")
                print(f"      Período: {primeira} até {ultima}")
                print()
        else:
            print("   Nenhuma conta encontrada")
        print()
        
        # 3. Últimos 10 lançamentos inseridos
        print("📊 3. ÚLTIMOS 10 LANÇAMENTOS INSERIDOS")
        print("-" * 80)
        
        query_recentes = """
        SELECT TOP 10
            id_movimentacao,
            agencia_origem,
            conta_origem,
            data_movimentacao,
            sinal_movimentacao,
            valor_movimentacao,
            tipo_movimentacao,
            LEFT(descricao_movimentacao, 60) as descricao_resumida,
            processo_referencia,
            hash_dados,
            criado_em
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'BB'
        ORDER BY criado_em DESC
        """
        
        result_recentes = adapter.execute_query(query_recentes, database=adapter.database)
        if result_recentes.get('success') and result_recentes.get('data'):
            rows = result_recentes['data']
            for i, row in enumerate(rows, 1):
                id_mov = row.get('id_movimentacao', '—')
                ag = row.get('agencia_origem', '—')
                ct = row.get('conta_origem', '—')
                data = formatar_data(row.get('data_movimentacao'))
                sinal = row.get('sinal_movimentacao', '')
                valor = formatar_brl(row.get('valor_movimentacao'))
                tipo = row.get('tipo_movimentacao', '—')
                desc = row.get('descricao_resumida', '—') or '—'
                proc = row.get('processo_referencia', '—') or '—'
                hash_val = row.get('hash_dados', '—') or '—'
                criado = formatar_data(row.get('criado_em'))
                
                print(f"   {i}. ID: {id_mov} | {ag}/{ct}")
                print(f"      Data: {data} | {sinal}{valor} | {tipo}")
                print(f"      Descrição: {desc}")
                if proc != '—':
                    print(f"      Processo: {proc}")
                print(f"      Hash: {hash_val[:16]}...")
                print(f"      Inserido em: {criado}")
                print()
        else:
            print("   Nenhum lançamento encontrado")
        print()
        
        # 4. Verificar duplicatas (hash duplicado)
        print("📊 4. VERIFICAÇÃO DE DUPLICATAS (HASH)")
        print("-" * 80)
        
        query_duplicatas = """
        SELECT 
            hash_dados,
            COUNT(*) as quantidade
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'BB' AND hash_dados IS NOT NULL
        GROUP BY hash_dados
        HAVING COUNT(*) > 1
        ORDER BY quantidade DESC
        """
        
        result_duplicatas = adapter.execute_query(query_duplicatas, database=adapter.database)
        if result_duplicatas.get('success') and result_duplicatas.get('data'):
            rows = result_duplicatas['data']
            if len(rows) > 0:
                print(f"   ⚠️ Encontrados {len(rows)} hashes duplicados:")
                for row in rows[:5]:  # Mostrar apenas 5 primeiros
                    hash_val = row.get('hash_dados', '—')
                    qtd = row.get('quantidade', 0)
                    print(f"      Hash {hash_val[:16]}...: {qtd} ocorrências")
                if len(rows) > 5:
                    print(f"      ... e mais {len(rows) - 5} hashes duplicados")
        else:
            print("   ✅ Nenhuma duplicata encontrada (sistema funcionando corretamente)")
        print()
        
        # 5. Lançamentos com processo detectado
        print("📊 5. LANÇAMENTOS COM PROCESSO DETECTADO")
        print("-" * 80)
        
        query_processos = """
        SELECT 
            processo_referencia,
            COUNT(*) as total,
            SUM(valor_movimentacao) as total_valor
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'BB' AND processo_referencia IS NOT NULL
        GROUP BY processo_referencia
        ORDER BY total DESC
        """
        
        result_processos = adapter.execute_query(query_processos, database=adapter.database)
        if result_processos.get('success') and result_processos.get('data'):
            rows = result_processos['data']
            if len(rows) > 0:
                print(f"   Total de processos vinculados: {len(rows)}")
                for row in rows[:10]:  # Mostrar apenas 10 primeiros
                    proc = row.get('processo_referencia', '—')
                    total = row.get('total', 0)
                    valor = formatar_brl(row.get('total_valor', 0))
                    print(f"      {proc}: {total} lançamento(s) | {valor}")
                if len(rows) > 10:
                    print(f"      ... e mais {len(rows) - 10} processos")
        else:
            print("   Nenhum processo vinculado ainda")
        print()
        
        # 6. Resumo dos últimos 7 dias
        print("📊 6. RESUMO DOS ÚLTIMOS 7 DIAS")
        print("-" * 80)
        
        query_7dias = """
        SELECT 
            CAST(data_movimentacao AS DATE) as data,
            COUNT(*) as total,
            SUM(CASE WHEN sinal_movimentacao = '+' THEN valor_movimentacao ELSE 0 END) as credito,
            SUM(CASE WHEN sinal_movimentacao = '-' THEN valor_movimentacao ELSE 0 END) as debito
        FROM dbo.MOVIMENTACAO_BANCARIA
        WHERE banco_origem = 'BB' 
          AND data_movimentacao >= DATEADD(DAY, -7, GETDATE())
        GROUP BY CAST(data_movimentacao AS DATE)
        ORDER BY data DESC
        """
        
        result_7dias = adapter.execute_query(query_7dias, database=adapter.database)
        if result_7dias.get('success') and result_7dias.get('data'):
            rows = result_7dias['data']
            if len(rows) > 0:
                for row in rows:
                    data = formatar_data(row.get('data'))
                    total = row.get('total', 0)
                    credito = formatar_brl(row.get('credito', 0))
                    debito = formatar_brl(row.get('debito', 0))
                    print(f"   {data}: {total} lançamento(s) | Crédito: {credito} | Débito: {debito}")
            else:
                print("   Nenhum lançamento nos últimos 7 dias")
        else:
            print("   ❌ Erro na query ou nenhum lançamento encontrado")
        print()
        
        print("=" * 80)
        print("✅ Verificação concluída!")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Erro ao consultar banco de dados: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verificar_lancamentos()

