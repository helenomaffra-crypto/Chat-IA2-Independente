#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para adicionar tipo de despesa "IMPOSTOS_IMPORTACAO" ao catálogo.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_server_adapter import get_sql_adapter

def adicionar_tipo_impostos():
    """Adiciona tipo de despesa para impostos de importação."""
    
    print("=" * 80)
    print("📋 ADICIONANDO TIPO DE DESPESA - IMPOSTOS DE IMPORTAÇÃO")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    
    if not adapter.test_connection():
        print("❌ SQL Server não está acessível.")
        return False
    
    print(f"✅ Conectado ao banco: {adapter.database}")
    print()
    
    try:
        # Verificar se já existe
        query_check = """
            SELECT id_tipo_despesa, codigo_tipo_despesa, nome_despesa
            FROM dbo.TIPO_DESPESA
            WHERE codigo_tipo_despesa = 'IMPOSTOS_IMPORTACAO' OR nome_despesa = 'Impostos de Importação'
        """
        resultado_check = adapter.execute_query(query_check, database=adapter.database)
        
        if resultado_check.get('success') and resultado_check.get('data') and len(resultado_check['data']) > 0:
            row = resultado_check['data'][0]
            if isinstance(row, dict):
                id_existente = row.get('id_tipo_despesa')
                nome_existente = row.get('nome_despesa', 'N/A')
            else:
                id_existente = row[0] if len(row) > 0 else None
                nome_existente = row[2] if len(row) > 2 else 'N/A'
            
            print(f"ℹ️ Tipo de despesa 'IMPOSTOS_IMPORTACAO' já existe:")
            print(f"   - ID: {id_existente}")
            print(f"   - Nome: {nome_existente}")
            print()
            print("✅ Nenhuma alteração necessária.")
            return True
        
        # Criar o tipo de despesa
        print("🔨 Criando tipo de despesa 'IMPOSTOS_IMPORTACAO'...")
        
        query_insert = """
            INSERT INTO dbo.TIPO_DESPESA (
                codigo_tipo_despesa,
                nome_despesa,
                descricao_despesa,
                categoria_despesa,
                tipo_custo,
                ativo,
                ordem_exibicao
            ) VALUES (
                'IMPOSTOS_IMPORTACAO',
                'Impostos de Importação',
                'Impostos de importação (II, IPI, PIS, COFINS, Taxa SISCOMEX, etc.) pagos via conciliação bancária',
                'IMPOSTO',
                'NACIONAL',
                1,
                24
            );
        """
        
        resultado = adapter.execute_query(query_insert, database=adapter.database)
        
        if not resultado.get('success'):
            error_msg = resultado.get('error', 'Erro desconhecido')
            print(f"❌ Erro ao criar tipo de despesa: {error_msg}")
            return False
        
        print("✅ Tipo de despesa 'IMPOSTOS_IMPORTACAO' criado com sucesso!")
        print()
        
        # Verificar se foi criado
        resultado_verificacao = adapter.execute_query(query_check, database=adapter.database)
        if resultado_verificacao.get('success') and resultado_verificacao.get('data'):
            row = resultado_verificacao['data'][0]
            if isinstance(row, dict):
                id_criado = row.get('id_tipo_despesa')
                nome_criado = row.get('nome_despesa', 'N/A')
            else:
                id_criado = row[0] if len(row) > 0 else None
                nome_criado = row[2] if len(row) > 2 else 'N/A'
            
            print(f"✅ Confirmação:")
            print(f"   - ID: {id_criado}")
            print(f"   - Nome: {nome_criado}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = adicionar_tipo_impostos()
    sys.exit(0 if sucesso else 1)


