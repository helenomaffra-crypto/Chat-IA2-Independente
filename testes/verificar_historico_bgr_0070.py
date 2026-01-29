#!/usr/bin/env python3
"""
Script para verificar se o histórico foi gravado para BGR.0070/25
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import get_sql_adapter

def verificar_historico():
    """Verifica se histórico foi gravado para BGR.0070/25"""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE HISTÓRICO - BGR.0070/25")
    print("=" * 80)
    
    sql_adapter = get_sql_adapter()
    
    # Verificar se tabela existe
    print("\n1️⃣ Verificando se tabela HISTORICO_DOCUMENTO_ADUANEIRO existe...")
    check_table_query = """
        SELECT COUNT(*) as count
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
    """
    
    result = sql_adapter.execute_query(check_table_query, database='mAIke_assistente')
    if result.get('success') and result.get('data'):
        count = result['data'][0].get('count', 0)
        if count > 0:
            print("✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO existe")
        else:
            print("❌ Tabela HISTORICO_DOCUMENTO_ADUANEIRO NÃO existe")
            print("⚠️ Execute o script SQL para criar a tabela")
            return
    else:
        print(f"❌ Erro ao verificar tabela: {result.get('error', 'Erro desconhecido')}")
        return
    
    # Verificar histórico para BGR.0070/25
    print("\n2️⃣ Buscando histórico para BGR.0070/25...")
    query = """
        SELECT TOP 20
            numero_documento,
            tipo_documento,
            tipo_evento,
            campo_alterado,
            valor_anterior,
            valor_novo,
            data_evento,
            fonte_dados,
            processo_referencia
        FROM dbo.HISTORICO_DOCUMENTO_ADUANEIRO
        WHERE processo_referencia = 'BGR.0070/25'
        ORDER BY data_evento DESC
    """
    
    result = sql_adapter.execute_query(query, database='mAIke_assistente')
    
    if result.get('success'):
        data = result.get('data', [])
        if data:
            print(f"✅ Encontrados {len(data)} registros de histórico")
            print("\n📋 Últimos registros:")
            for i, row in enumerate(data[:5], 1):
                print(f"\n  {i}. Documento: {row.get('numero_documento')} ({row.get('tipo_documento')})")
                print(f"     Evento: {row.get('tipo_evento')}")
                print(f"     Campo: {row.get('campo_alterado')}")
                print(f"     Anterior: {row.get('valor_anterior', 'N/A')}")
                print(f"     Novo: {row.get('valor_novo', 'N/A')}")
                print(f"     Data: {row.get('data_evento')}")
                print(f"     Fonte: {row.get('fonte_dados')}")
        else:
            print("⚠️ Nenhum histórico encontrado para BGR.0070/25")
            print("\n💡 Possíveis causas:")
            print("   - Histórico ainda não foi gravado")
            print("   - Processo não foi consultado ainda")
            print("   - DocumentoHistoricoService não está sendo chamado")
    else:
        print(f"❌ Erro ao buscar histórico: {result.get('error', 'Erro desconhecido')}")
    
    # Verificar documentos do processo
    print("\n3️⃣ Verificando documentos do processo...")
    query_docs = """
        SELECT TOP 10
            numero_documento,
            tipo_documento,
            situacao_documento,
            canal_documento,
            data_registro,
            data_situacao,
            processo_referencia
        FROM dbo.DOCUMENTO_ADUANEIRO
        WHERE processo_referencia = 'BGR.0070/25'
        ORDER BY data_registro DESC
    """
    
    result_docs = sql_adapter.execute_query(query_docs, database='mAIke_assistente')
    
    if result_docs.get('success'):
        data_docs = result_docs.get('data', [])
        if data_docs:
            print(f"✅ Encontrados {len(data_docs)} documentos")
            for i, doc in enumerate(data_docs, 1):
                print(f"\n  {i}. {doc.get('tipo_documento')} {doc.get('numero_documento')}")
                print(f"     Situação: {doc.get('situacao_documento', 'N/A')}")
                print(f"     Canal: {doc.get('canal_documento', 'N/A')}")
                print(f"     Data Registro: {doc.get('data_registro', 'N/A')}")
        else:
            print("⚠️ Nenhum documento encontrado para BGR.0070/25")
            print("💡 Documentos podem não ter sido gravados ainda")
    else:
        print(f"❌ Erro ao buscar documentos: {result_docs.get('error', 'Erro desconhecido')}")
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída")
    print("=" * 80)

if __name__ == '__main__':
    verificar_historico()


