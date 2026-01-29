#!/usr/bin/env python3
"""
Script para verificar se os documentos do BGR.0070/25 estão gravados no SQL Server
"""
import sys
import os
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# ✅ FORÇAR CARREGAMENTO DO .env ANTES DE IMPORTAR ADAPTER
env_path = Path(root_dir) / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

from utils.sql_server_adapter import get_sql_adapter

def verificar_documentos():
    """Verifica se os documentos do BGR.0070/25 estão gravados"""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE DOCUMENTOS - BGR.0070/25")
    print("=" * 80)
    
    # ✅ Verificar qual database será usado
    database_para_usar = os.getenv('SQL_DATABASE', 'mAIke_assistente')
    print(f"\n💡 Database configurado: {database_para_usar}")
    print(f"   SQL_SERVER: {os.getenv('SQL_SERVER', 'NÃO DEFINIDO')}")
    
    sql_adapter = get_sql_adapter()
    
    # ✅ Usar database do .env ou mAIke_assistente como fallback
    if not database_para_usar or database_para_usar == 'Make':
        database_para_usar = 'mAIke_assistente'
        print(f"   ⚠️ Ajustando para usar: {database_para_usar}")
    
    # Verificar se tabela existe
    print("\n1️⃣ Verificando se tabela DOCUMENTO_ADUANEIRO existe...")
    check_table_query = """
        SELECT COUNT(*) as count
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'DOCUMENTO_ADUANEIRO'
    """
    
    result = sql_adapter.execute_query(check_table_query, database=database_para_usar)
    if result.get('success') and result.get('data'):
        count = result['data'][0].get('count', 0)
        if count > 0:
            print("✅ Tabela DOCUMENTO_ADUANEIRO existe")
        else:
            print("❌ Tabela DOCUMENTO_ADUANEIRO NÃO existe")
            print("💡 Execute o script SQL para criar a tabela")
            return
    else:
        error_msg = result.get('error', 'Erro desconhecido')
        print(f"❌ Erro ao verificar tabela: {error_msg}")
        print(f"\n💡 Detalhes do erro:")
        print(f"   - Mensagem completa: {error_msg}")
        print(f"   - Database tentado: {database_para_usar}")
        print(f"   - Servidor: {os.getenv('SQL_SERVER', 'NÃO DEFINIDO')}")
        print(f"\n💡 Para diagnosticar melhor, execute:")
        print(f"   python3 testes/testar_conexao_sql_detalhado.py")
        return
    
    # Buscar documentos do BGR.0070/25
    print("\n2️⃣ Buscando documentos do BGR.0070/25...")
    query = """
        SELECT 
            numero_documento,
            tipo_documento,
            processo_referencia,
            situacao_documento,
            canal_documento,
            situacao_entrega,
            data_registro,
            data_situacao,
            data_desembaraco,
            nome_importador,
            valor_frete_usd,
            valor_frete_brl,
            moeda_codigo,
            fonte_dados,
            criado_em,
            atualizado_em
        FROM dbo.DOCUMENTO_ADUANEIRO
        WHERE processo_referencia = 'BGR.0070/25'
        ORDER BY tipo_documento, criado_em DESC
    """
    
    result = sql_adapter.execute_query(query, database=database_para_usar)
    
    if result.get('success'):
        data = result.get('data', [])
        if data:
            print(f"✅ Encontrados {len(data)} documento(s) para BGR.0070/25")
            print("\n📋 Detalhes dos documentos:")
            
            for i, doc in enumerate(data, 1):
                print(f"\n  {i}. {doc.get('tipo_documento')} {doc.get('numero_documento')}")
                print(f"     Situação: {doc.get('situacao_documento', 'N/A')}")
                if doc.get('canal_documento'):
                    print(f"     Canal: {doc.get('canal_documento')}")
                if doc.get('situacao_entrega'):
                    print(f"     Situação Entrega: {doc.get('situacao_entrega')}")
                if doc.get('nome_importador'):
                    print(f"     Importador: {doc.get('nome_importador')}")
                if doc.get('valor_frete_usd') or doc.get('valor_frete_brl'):
                    if doc.get('valor_frete_usd'):
                        print(f"     Frete USD: ${doc.get('valor_frete_usd', 0):,.2f}")
                    if doc.get('valor_frete_brl'):
                        print(f"     Frete BRL: R$ {doc.get('valor_frete_brl', 0):,.2f}")
                    if doc.get('moeda_codigo'):
                        print(f"     Moeda: {doc.get('moeda_codigo')}")
                print(f"     Data Registro: {doc.get('data_registro', 'N/A')}")
                print(f"     Data Situação: {doc.get('data_situacao', 'N/A')}")
                print(f"     Data Desembaraço: {doc.get('data_desembaraco', 'N/A')}")
                print(f"     Fonte: {doc.get('fonte_dados', 'N/A')}")
                print(f"     Criado em: {doc.get('criado_em', 'N/A')}")
                print(f"     Atualizado em: {doc.get('atualizado_em', 'N/A')}")
            
            # Verificar documentos esperados
            print("\n3️⃣ Verificando documentos esperados...")
            documentos_esperados = {
                'CE': '172505417636125',
                'DI': '2600362869'
            }
            
            documentos_encontrados = {}
            for doc in data:
                tipo = doc.get('tipo_documento')
                numero = doc.get('numero_documento')
                documentos_encontrados[tipo] = numero
            
            print("\n📊 Comparação:")
            for tipo, numero_esperado in documentos_esperados.items():
                numero_encontrado = documentos_encontrados.get(tipo)
                if numero_encontrado:
                    if numero_encontrado == numero_esperado:
                        print(f"  ✅ {tipo} {numero_esperado}: Encontrado e correto")
                    else:
                        print(f"  ⚠️ {tipo} {numero_esperado}: Encontrado mas número diferente ({numero_encontrado})")
                else:
                    print(f"  ❌ {tipo} {numero_esperado}: NÃO encontrado")
        else:
            print("⚠️ Nenhum documento encontrado para BGR.0070/25")
            print("\n💡 Possíveis causas:")
            print("   - Documentos ainda não foram gravados no SQL Server")
            print("   - Documentos foram gravados apenas no SQLite (cache local)")
            print("   - Processo não foi sincronizado do Kanban ainda")
            print("   - Documentos não foram consultados via API")
    else:
        error_msg = result.get('error', 'Erro desconhecido')
        print(f"❌ Erro ao buscar documentos: {error_msg}")
        
        # ✅ Mostrar detalhes do erro se for apenas mensagem de log
        if '[SQL Server Node] Conectando a:' in error_msg:
            print(f"\n💡 Este é apenas um log de conexão, não o erro real.")
            print(f"   O erro real pode estar sendo suprimido.")
            print(f"   Database tentado: {database_para_usar}")
            print(f"   Servidor: {os.getenv('SQL_SERVER', 'NÃO DEFINIDO')}")
            print(f"\n💡 Para ver o erro completo, verifique os logs do Node.js")
            print(f"   ou execute uma consulta via chat: 'maike consulte o CE 172505417636125'")
    
    # Verificar histórico de documentos
    print("\n4️⃣ Verificando histórico de mudanças...")
    query_historico = """
        SELECT TOP 10
            numero_documento,
            tipo_documento,
            tipo_evento,
            campo_alterado,
            valor_anterior,
            valor_novo,
            data_evento,
            fonte_dados
        FROM dbo.HISTORICO_DOCUMENTO_ADUANEIRO
        WHERE processo_referencia = 'BGR.0070/25'
        ORDER BY data_evento DESC
    """
    
    result_historico = sql_adapter.execute_query(query_historico, database=database_para_usar)
    
    if result_historico.get('success'):
        historico = result_historico.get('data', [])
        if historico:
            print(f"✅ Encontrados {len(historico)} registro(s) de histórico")
            print("\n📋 Últimas mudanças:")
            for i, mudanca in enumerate(historico[:5], 1):
                print(f"\n  {i}. {mudanca.get('tipo_documento')} {mudanca.get('numero_documento')}")
                print(f"     Evento: {mudanca.get('tipo_evento')}")
                print(f"     Campo: {mudanca.get('campo_alterado')}")
                print(f"     Anterior: {mudanca.get('valor_anterior', 'N/A')}")
                print(f"     Novo: {mudanca.get('valor_novo', 'N/A')}")
                print(f"     Data: {mudanca.get('data_evento', 'N/A')}")
                print(f"     Fonte: {mudanca.get('fonte_dados', 'N/A')}")
        else:
            print("⚠️ Nenhum histórico encontrado para BGR.0070/25")
            print("💡 Histórico só é gravado quando detecta mudanças")
    else:
        print(f"❌ Erro ao buscar histórico: {result_historico.get('error', 'Erro desconhecido')}")
    
    # Verificar também no SQLite para comparar
    print("\n5️⃣ Verificando também no SQLite (cache local)...")
    try:
        from db_manager import get_db_connection
        import sqlite3
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Verificar processos_kanban (tem números dos documentos)
        cursor.execute("""
            SELECT numero_ce, numero_di, numero_duimp
            FROM processos_kanban
            WHERE processo_referencia = 'BGR.0070/25'
        """)
        
        row = cursor.fetchone()
        if row:
            print("✅ SQLite: Processo encontrado")
            print(f"   CE: {row['numero_ce'] or 'N/A'}")
            print(f"   DI: {row['numero_di'] or 'N/A'}")
            print(f"   DUIMP: {row['numero_duimp'] or 'N/A'}")
        else:
            print("⚠️ SQLite: Processo não encontrado")
        
        conn.close()
    except Exception as e:
        print(f"⚠️ Erro ao verificar SQLite: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída")
    print("=" * 80)
    print("\n💡 CONCLUSÃO:")
    print("   - Se documentos estão no SQL Server: ✅ Sistema funcionando")
    print("   - Se documentos NÃO estão no SQL Server: ⚠️ Precisa sincronizar ou consultar API")
    print("   - Se histórico está vazio: ⚠️ Pode ser normal (sem mudanças detectadas)")

if __name__ == '__main__':
    verificar_documentos()

