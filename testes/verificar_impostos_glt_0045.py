#!/usr/bin/env python3
"""
Script para verificar impostos gravados para GLT.0045/25
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utils.sql_server_adapter import get_sql_adapter

def main():
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE IMPOSTOS - GLT.0045/25")
    print("=" * 80)
    
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ Não foi possível conectar ao SQL Server")
        return
    
    processo_ref = "GLT.0045/25"
    
    # Testar diferentes formatos
    formatos = [
        ("Original", processo_ref),
        ("Uppercase", processo_ref.upper()),
        ("Lowercase", processo_ref.lower()),
        ("Trim", processo_ref.strip()),
        ("Uppercase + Trim", processo_ref.strip().upper()),
    ]
    
    print(f"\n1️⃣ Verificando impostos para diferentes formatos de '{processo_ref}':\n")
    
    for nome, formato in formatos:
        query = f"""
            SELECT 
                id_imposto,
                processo_referencia,
                tipo_imposto,
                valor_brl,
                numero_documento,
                tipo_documento,
                criado_em
            FROM dbo.IMPOSTO_IMPORTACAO
            WHERE processo_referencia = '{formato.replace("'", "''")}'
            ORDER BY criado_em DESC
        """
        
        result = adapter.execute_query(query, database=adapter.database)
        if result.get('success'):
            data = result.get('data', [])
            if data:
                print(f"✅ {nome} ('{formato}'): {len(data)} imposto(s) encontrado(s)")
                for imp in data:
                    if isinstance(imp, dict):
                        print(f"   - {imp.get('tipo_imposto', 'N/A')}: R$ {imp.get('valor_brl', 0):,.2f} (processo: '{imp.get('processo_referencia', 'N/A')}')")
            else:
                print(f"⚠️ {nome} ('{formato}'): Nenhum imposto encontrado")
        else:
            print(f"❌ {nome} ('{formato}'): Erro na query: {result.get('error', 'Erro desconhecido')}")
    
    # Buscar todos os impostos para ver exemplos
    print(f"\n2️⃣ Verificando todos os impostos na tabela:\n")
    
    query_all = """
        SELECT TOP 10
            processo_referencia,
            tipo_imposto,
            valor_brl,
            criado_em
        FROM dbo.IMPOSTO_IMPORTACAO
        ORDER BY criado_em DESC
    """
    
    result_all = adapter.execute_query(query_all, database=adapter.database)
    if result_all.get('success'):
        data_all = result_all.get('data', [])
        print(f"📊 Total de impostos na tabela: {len(data_all)}")
        if data_all:
            print("\n📋 Últimos impostos gravados:")
            for imp in data_all:
                if isinstance(imp, dict):
                    proc = imp.get('processo_referencia', 'N/A')
                    tipo = imp.get('tipo_imposto', 'N/A')
                    valor = imp.get('valor_brl', 0)
                    criado = imp.get('criado_em', 'N/A')
                    print(f"   - Processo: '{proc}' | Tipo: {tipo} | Valor: R$ {valor:,.2f} | Criado: {criado}")
        else:
            print("⚠️ Nenhum imposto encontrado na tabela")
    else:
        print(f"❌ Erro ao buscar todos os impostos: {result_all.get('error', 'Erro desconhecido')}")
    
    # Buscar com normalização (como a query real)
    print(f"\n3️⃣ Verificando com query normalizada (como no código):\n")
    
    processo_ref_upper = processo_ref.strip().upper()
    processo_ref_original = processo_ref.strip()
    processo_ref_escaped = processo_ref.replace("'", "''")
    
    query_normalizada = f"""
        SELECT 
            id_imposto,
            processo_referencia,
            tipo_imposto,
            valor_brl,
            numero_documento,
            tipo_documento,
            criado_em
        FROM dbo.IMPOSTO_IMPORTACAO
        WHERE UPPER(LTRIM(RTRIM(processo_referencia))) = '{processo_ref_upper}'
           OR LTRIM(RTRIM(processo_referencia)) = '{processo_ref_original.replace("'", "''")}'
           OR processo_referencia = '{processo_ref_escaped}'
        ORDER BY criado_em DESC
    """
    
    result_normalizada = adapter.execute_query(query_normalizada, database=adapter.database)
    if result_normalizada.get('success'):
        data_normalizada = result_normalizada.get('data', [])
        print(f"✅ Query normalizada: {len(data_normalizada)} imposto(s) encontrado(s)")
        if data_normalizada:
            for imp in data_normalizada:
                if isinstance(imp, dict):
                    print(f"   - {imp.get('tipo_imposto', 'N/A')}: R$ {imp.get('valor_brl', 0):,.2f} (processo: '{imp.get('processo_referencia', 'N/A')}')")
        else:
            print("⚠️ Nenhum imposto encontrado com query normalizada")
    else:
        print(f"❌ Erro na query normalizada: {result_normalizada.get('error', 'Erro desconhecido')}")
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída")
    print("=" * 80)

if __name__ == "__main__":
    main()


