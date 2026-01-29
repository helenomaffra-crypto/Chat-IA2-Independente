#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para limpar duplicatas na tabela IMPOSTO_IMPORTACAO.
Mantém apenas o registro mais recente de cada tipo de imposto por processo/documento.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.sql_server_adapter import get_sql_adapter

def limpar_duplicatas_impostos():
    """Remove duplicatas da tabela IMPOSTO_IMPORTACAO, mantendo apenas o mais recente."""
    
    print("=" * 80)
    print("🧹 LIMPEZA DE DUPLICATAS - IMPOSTO_IMPORTACAO")
    print("=" * 80)
    print()
    
    adapter = get_sql_adapter()
    
    if not adapter.test_connection():
        print("❌ SQL Server não está acessível.")
        return False
    
    print(f"✅ Conectado ao banco: {adapter.database}")
    print()
    
    try:
        # 1. Verificar quantas duplicatas existem
        print("🔍 Verificando duplicatas...")
        query_verificar = """
            WITH ImpostosRanked AS (
                SELECT 
                    id_imposto,
                    processo_referencia,
                    numero_documento,
                    tipo_imposto,
                    criado_em,
                    ROW_NUMBER() OVER (
                        PARTITION BY processo_referencia, numero_documento, tipo_imposto 
                        ORDER BY criado_em DESC, id_imposto DESC
                    ) as rn
                FROM dbo.IMPOSTO_IMPORTACAO
            )
            SELECT COUNT(*) as total_duplicatas
            FROM ImpostosRanked
            WHERE rn > 1
        """
        
        resultado_verificar = adapter.execute_query(query_verificar, database=adapter.database)
        
        if not resultado_verificar.get('success'):
            error_msg = resultado_verificar.get('error', 'Erro desconhecido')
            print(f"❌ Erro ao verificar duplicatas: {error_msg}")
            return False
        
        total_duplicatas = 0
        if resultado_verificar.get('data'):
            row = resultado_verificar['data'][0]
            if isinstance(row, dict):
                total_duplicatas = row.get('total_duplicatas', 0)
            else:
                total_duplicatas = row[0] if len(row) > 0 else 0
        
        print(f"📊 Total de duplicatas encontradas: {total_duplicatas}")
        print()
        
        if total_duplicatas == 0:
            print("✅ Nenhuma duplicata encontrada. Tabela está limpa!")
            return True
        
        # 2. Mostrar exemplos de duplicatas
        print("📋 Exemplos de duplicatas:")
        query_exemplos = """
            WITH ImpostosRanked AS (
                SELECT 
                    id_imposto,
                    processo_referencia,
                    numero_documento,
                    tipo_imposto,
                    valor_brl,
                    criado_em,
                    ROW_NUMBER() OVER (
                        PARTITION BY processo_referencia, numero_documento, tipo_imposto 
                        ORDER BY criado_em DESC, id_imposto DESC
                    ) as rn
                FROM dbo.IMPOSTO_IMPORTACAO
            )
            SELECT TOP 10
                processo_referencia,
                numero_documento,
                tipo_imposto,
                valor_brl,
                criado_em,
                rn
            FROM ImpostosRanked
            WHERE rn > 1
            ORDER BY criado_em DESC
        """
        
        resultado_exemplos = adapter.execute_query(query_exemplos, database=adapter.database)
        if resultado_exemplos.get('success') and resultado_exemplos.get('data'):
            for idx, row in enumerate(resultado_exemplos.get('data', [])[:5], 1):
                if isinstance(row, dict):
                    proc = row.get('processo_referencia', 'N/A')
                    doc = row.get('numero_documento', 'N/A')
                    tipo = row.get('tipo_imposto', 'N/A')
                    valor = row.get('valor_brl', 0)
                    criado = str(row.get('criado_em', ''))[:19]
                else:
                    proc = row[0] if len(row) > 0 else 'N/A'
                    doc = row[1] if len(row) > 1 else 'N/A'
                    tipo = row[2] if len(row) > 2 else 'N/A'
                    valor = row[3] if len(row) > 3 else 0
                    criado = str(row[4])[:19] if len(row) > 4 else ''
                
                print(f"  {idx}. {proc} | {doc} | {tipo} | R$ {valor:,.2f} | {criado}")
        
        print()
        
        # 3. Confirmar antes de deletar
        resposta = input(f"⚠️ Deseja remover {total_duplicatas} duplicata(s)? (s/N): ").strip().lower()
        if resposta != 's':
            print("❌ Operação cancelada.")
            return False
        
        # 4. Deletar duplicatas (manter apenas o mais recente)
        print("🗑️ Removendo duplicatas...")
        query_deletar = """
            WITH ImpostosRanked AS (
                SELECT 
                    id_imposto,
                    ROW_NUMBER() OVER (
                        PARTITION BY processo_referencia, numero_documento, tipo_imposto 
                        ORDER BY criado_em DESC, id_imposto DESC
                    ) as rn
                FROM dbo.IMPOSTO_IMPORTACAO
            )
            DELETE FROM dbo.IMPOSTO_IMPORTACAO
            WHERE id_imposto IN (
                SELECT id_imposto
                FROM ImpostosRanked
                WHERE rn > 1
            )
        """
        
        resultado_deletar = adapter.execute_query(query_deletar, database=adapter.database)
        
        if not resultado_deletar.get('success'):
            error_msg = resultado_deletar.get('error', 'Erro desconhecido')
            print(f"❌ Erro ao remover duplicatas: {error_msg}")
            return False
        
        print(f"✅ {total_duplicatas} duplicata(s) removida(s) com sucesso!")
        print()
        
        # 5. Verificar resultado final
        resultado_final = adapter.execute_query(query_verificar, database=adapter.database)
        if resultado_final.get('success') and resultado_final.get('data'):
            row = resultado_final['data'][0]
            if isinstance(row, dict):
                duplicatas_restantes = row.get('total_duplicatas', 0)
            else:
                duplicatas_restantes = row[0] if len(row) > 0 else 0
            
            if duplicatas_restantes == 0:
                print("✅ Tabela limpa! Nenhuma duplicata restante.")
            else:
                print(f"⚠️ Ainda há {duplicatas_restantes} duplicata(s) restante(s).")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = limpar_duplicatas_impostos()
    sys.exit(0 if sucesso else 1)


