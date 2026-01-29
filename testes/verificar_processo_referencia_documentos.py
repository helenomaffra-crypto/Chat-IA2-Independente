#!/usr/bin/env python3
"""
Script para verificar se processo_referencia está sendo gravado nos documentos
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utils.sql_server_adapter import get_sql_adapter

def verificar_processo_referencia():
    """Verifica se processo_referencia está sendo gravado"""
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE processo_referencia EM DOCUMENTOS")
    print("=" * 80)
    
    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server adapter não disponível")
        return
    
    # Verificar alguns documentos recentes
    query = """
        SELECT TOP 20
            id_documento,
            numero_documento,
            tipo_documento,
            processo_referencia,
            fonte_dados,
            criado_em,
            atualizado_em
        FROM DOCUMENTO_ADUANEIRO
        ORDER BY atualizado_em DESC
    """
    
    result = adapter.execute_query(query, database=adapter.database)
    
    if not result or not result.get('success'):
        print(f"❌ Erro ao buscar documentos: {result.get('error', 'Erro desconhecido')}")
        return
    
    data = result.get('data', [])
    if not data:
        print("⚠️ Nenhum documento encontrado")
        return
    
    print(f"\n📊 Total de documentos encontrados: {len(data)}\n")
    
    # Estatísticas
    com_processo = 0
    sem_processo = 0
    
    print("📋 Documentos recentes:")
    print("-" * 80)
    for doc in data:
        processo = doc.get('processo_referencia') or 'NULL'
        if processo and processo != 'NULL':
            com_processo += 1
            status = "✅"
        else:
            sem_processo += 1
            status = "❌"
        
        print(f"{status} {doc.get('tipo_documento')} {doc.get('numero_documento')}")
        print(f"   Processo: {processo}")
        print(f"   Fonte: {doc.get('fonte_dados')}")
        print(f"   Atualizado: {doc.get('atualizado_em')}")
        print()
    
    print("=" * 80)
    print("📊 ESTATÍSTICAS:")
    print(f"   ✅ Com processo_referencia: {com_processo}")
    print(f"   ❌ Sem processo_referencia: {sem_processo}")
    print(f"   📈 Percentual com processo: {(com_processo / len(data) * 100):.1f}%")
    print("=" * 80)
    
    # Verificar documentos específicos mencionados no log
    print("\n🔍 Verificando documentos específicos do log:")
    print("-" * 80)
    documentos_log = [
        ('DI', '2500416215'),
        ('CE', '132405378472866'),
        ('DI', '2428217916'),
        ('CE', '152505031629023'),
        ('DI', '2504026314'),
    ]
    
    for tipo, numero in documentos_log:
        query_doc = f"""
            SELECT 
                numero_documento,
                tipo_documento,
                processo_referencia,
                fonte_dados,
                atualizado_em
            FROM DOCUMENTO_ADUANEIRO
            WHERE numero_documento = '{numero}' AND tipo_documento = '{tipo}'
            ORDER BY atualizado_em DESC
        """
        
        result_doc = adapter.execute_query(query_doc, database=adapter.database)
        if result_doc and result_doc.get('success'):
            data_doc = result_doc.get('data', [])
            if data_doc:
                doc = data_doc[0]
                processo = doc.get('processo_referencia') or 'NULL'
                status = "✅" if processo and processo != 'NULL' else "❌"
                print(f"{status} {tipo} {numero}: processo_referencia = {processo}")
            else:
                print(f"⚠️ {tipo} {numero}: Não encontrado")
        else:
            print(f"❌ {tipo} {numero}: Erro ao buscar")

if __name__ == '__main__':
    verificar_processo_referencia()


