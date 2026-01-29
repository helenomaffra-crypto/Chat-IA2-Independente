#!/usr/bin/env python3
"""
Script para diagnosticar por que o dashboard está vazio.
"""
import sys
import sqlite3
from datetime import date, datetime

print("=" * 60)
print("DIAGNÓSTICO DE DADOS DO DASHBOARD")
print("=" * 60)
print()

# 1. Verificar se o banco existe e tem dados
print("1️⃣  Verificando banco de dados...")
try:
    from db_manager import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Contar processos no kanban
    cursor.execute("SELECT COUNT(*) FROM processos_kanban")
    total_processos = cursor.fetchone()[0]
    print(f"   📊 Total de processos no kanban: {total_processos}")
    
    if total_processos == 0:
        print("   ⚠️  NENHUM processo no banco! O cache está vazio.")
        print("   💡 Execute a sincronização de processos primeiro:")
        print("      - 'sincronizar processos ativos'")
        print("      - Ou use a tool: sincronizar_processos_ativos_maike")
    else:
        print(f"   ✅ Há {total_processos} processos no banco")
        
        # Verificar processos com data de hoje
        hoje = date.today().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) FROM processos_kanban
            WHERE DATE(data_destino_final) = DATE('now')
               OR (eta_iso IS NOT NULL AND DATE(eta_iso) = DATE('now'))
        """)
        chegando_hoje = cursor.fetchone()[0]
        print(f"   📅 Processos chegando hoje (por data): {chegando_hoje}")
        
        # Verificar processos prontos para registro
        cursor.execute("""
            SELECT COUNT(*) FROM processos_kanban
            WHERE DATE(data_destino_final) <= DATE('now')
               AND (numero_di IS NULL OR numero_di = '' OR numero_di = '/       -')
               AND (numero_duimp IS NULL OR numero_duimp = '')
        """)
        prontos = cursor.fetchone()[0]
        print(f"   ✅ Processos prontos para registro: {prontos}")
        
        # Mostrar alguns exemplos
        print()
        print("   📋 Exemplos de processos no banco:")
        cursor.execute("SELECT processo_referencia, data_destino_final, eta_iso, numero_di, numero_duimp FROM processos_kanban LIMIT 5")
        exemplos = cursor.fetchall()
        for proc in exemplos:
            print(f"      - {proc[0]}: chegada={proc[1]}, eta={proc[2]}, di={proc[3]}, duimp={proc[4]}")
    
    conn.close()
    
except Exception as e:
    print(f"   ❌ Erro ao verificar banco: {e}")
    import traceback
    traceback.print_exc()

print()

# 2. Testar as funções do db_manager
print("2️⃣  Testando funções do db_manager...")
try:
    from db_manager import (
        obter_processos_chegando_hoje,
        obter_processos_prontos_registro,
        obter_pendencias_ativas,
        obter_duimps_em_analise
    )
    
    processos_chegando = obter_processos_chegando_hoje()
    print(f"   📅 obter_processos_chegando_hoje(): {len(processos_chegando)} processos")
    
    processos_prontos = obter_processos_prontos_registro()
    print(f"   ✅ obter_processos_prontos_registro(): {len(processos_prontos)} processos")
    
    pendencias = obter_pendencias_ativas()
    print(f"   ⚠️  obter_pendencias_ativas(): {len(pendencias)} pendências")
    
    duimps = obter_duimps_em_analise()
    print(f"   📋 obter_duimps_em_analise(): {len(duimps)} DUIMPs")
    
except Exception as e:
    print(f"   ❌ Erro ao testar funções: {e}")
    import traceback
    traceback.print_exc()

print()

# 3. Verificar SQL Server (se disponível)
print("3️⃣  Verificando SQL Server...")
try:
    from utils.sql_server_adapter import get_sql_adapter
    
    sql_adapter = get_sql_adapter()
    if sql_adapter:
        result = sql_adapter.execute_query("SELECT 1 AS test", notificar_erro=False)
        if result and result.get('success'):
            print("   ✅ SQL Server está disponível")
            
            # Contar processos no SQL Server
            result = sql_adapter.execute_query("""
                SELECT COUNT(*) as total
                FROM PROCESSO_IMPORTACAO
                WHERE situacao != 'CANCELADO'
            """, notificar_erro=False)
            
            if result and result.get('success') and result.get('data'):
                total_sql = result['data'][0]['total'] if result['data'] else 0
                print(f"   📊 Total de processos no SQL Server: {total_sql}")
            else:
                print("   ⚠️  Não foi possível contar processos no SQL Server")
        else:
            print("   ⚠️  SQL Server não está respondendo")
    else:
        print("   ⚠️  SQL Server não configurado")
        
except Exception as e:
    print(f"   ⚠️  SQL Server não disponível: {e}")

print()
print("=" * 60)
print("DIAGNÓSTICO CONCLUÍDO")
print("=" * 60)
print()
print("💡 PRÓXIMOS PASSOS:")
print("   1. Se o cache está vazio, sincronize os processos:")
print("      - 'sincronizar processos ativos'")
print("   2. Se há processos mas não aparecem, verifique as datas:")
print("      - data_destino_final deve ser hoje")
print("      - ou eta_iso deve ser hoje")
print("   3. Verifique se os processos têm DI/DUIMP (não aparecem como 'prontos')")
