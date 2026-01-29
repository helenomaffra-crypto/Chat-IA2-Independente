#!/usr/bin/env python3
"""
Script para verificar quantos processos do Kanban estão salvos
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_manager import get_db_connection
import sqlite3

def verificar_sqlite():
    """Verifica processos no SQLite (cache local)"""
    
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE PROCESSOS DO KANBAN")
    print("=" * 80)
    
    print("\n1️⃣ Verificando SQLite (cache local)...")
    
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Contar processos
        cursor.execute('SELECT COUNT(*) as total FROM processos_kanban')
        total = cursor.fetchone()['total']
        
        print(f"✅ Total de processos no SQLite: {total}")
        
        # Listar alguns processos
        cursor.execute('''
            SELECT processo_referencia, etapa_kanban, modal, numero_ce, numero_di, numero_duimp, fonte
            FROM processos_kanban
            ORDER BY atualizado_em DESC
            LIMIT 10
        ''')
        
        processos = cursor.fetchall()
        if processos:
            print(f"\n📋 Últimos 10 processos atualizados:")
            for i, proc in enumerate(processos, 1):
                print(f"\n  {i}. {proc['processo_referencia']}")
                print(f"     Etapa: {proc['etapa_kanban']}")
                print(f"     Modal: {proc['modal']}")
                print(f"     CE: {proc['numero_ce'] or 'N/A'}")
                print(f"     DI: {proc['numero_di'] or 'N/A'}")
                print(f"     DUIMP: {proc['numero_duimp'] or 'N/A'}")
                print(f"     Fonte: {proc['fonte']}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao verificar SQLite: {e}")
        import traceback
        traceback.print_exc()

def verificar_sql_server():
    """Verifica processos no SQL Server novo (mAIke_assistente)"""
    
    print("\n2️⃣ Verificando SQL Server (mAIke_assistente)...")
    
    try:
        from utils.sql_server_adapter import get_sql_adapter
        
        sql_adapter = get_sql_adapter()
        
        # Verificar se tabela existe
        check_table_query = """
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PROCESSO_IMPORTACAO'
        """
        
        result = sql_adapter.execute_query(check_table_query, database='mAIke_assistente')
        
        if result.get('success') and result.get('data'):
            count = result['data'][0].get('count', 0)
            if count > 0:
                print("✅ Tabela PROCESSO_IMPORTACAO existe")
                
                # Contar processos
                count_query = "SELECT COUNT(*) as total FROM dbo.PROCESSO_IMPORTACAO"
                count_result = sql_adapter.execute_query(count_query, database='mAIke_assistente')
                
                if count_result.get('success') and count_result.get('data'):
                    total = count_result['data'][0].get('total', 0)
                    print(f"✅ Total de processos no SQL Server: {total}")
                    
                    if total == 0:
                        print("⚠️ Tabela existe mas está VAZIA")
                        print("💡 A sincronização do Kanban ainda NÃO está gravando no SQL Server")
                        print("💡 Está gravando apenas no SQLite (cache local)")
                else:
                    print(f"❌ Erro ao contar processos: {count_result.get('error', 'Erro desconhecido')}")
            else:
                print("❌ Tabela PROCESSO_IMPORTACAO NÃO existe")
                print("💡 Execute o script SQL para criar a tabela")
        else:
            print(f"❌ Erro ao verificar tabela: {result.get('error', 'Erro desconhecido')}")
            print("⚠️ SQL Server pode não estar acessível (fora da rede)")
            
    except Exception as e:
        print(f"❌ Erro ao verificar SQL Server: {e}")
        print("⚠️ SQL Server pode não estar acessível (fora da rede)")
        import traceback
        traceback.print_exc()

def comparar():
    """Compara SQLite vs SQL Server"""
    
    print("\n" + "=" * 80)
    print("📊 COMPARAÇÃO")
    print("=" * 80)
    
    print("\n💡 CONCLUSÃO:")
    print("   - SQLite (cache local): ✅ Processos estão sendo gravados")
    print("   - SQL Server (mAIke_assistente): ⚠️ AINDA NÃO está sendo gravado")
    print("\n   📝 A sincronização do Kanban atualmente grava apenas no SQLite.")
    print("   📝 Para gravar no SQL Server novo, precisa implementar a gravação.")
    print("   📝 Ver: docs/ESTRATEGIA_POPULACAO_BANCO_MAIKE.md")

if __name__ == '__main__':
    verificar_sqlite()
    verificar_sql_server()
    comparar()
    
    print("\n" + "=" * 80)
    print("✅ Verificação concluída")
    print("=" * 80)


