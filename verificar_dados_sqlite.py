#!/usr/bin/env python3
"""
Script para verificar se os dados estão no SQLite e por que não aparecem no dashboard.
"""
import sys
from datetime import date, datetime

print("=" * 60)
print("VERIFICAÇÃO DE DADOS NO SQLITE")
print("=" * 60)
print()

try:
    from db_manager import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Contar processos
    cursor.execute("SELECT COUNT(*) FROM processos_kanban")
    total = cursor.fetchone()[0]
    print(f"1️⃣  Total de processos no SQLite: {total}")
    
    if total == 0:
        print("   ❌ NENHUM processo no banco!")
        print("   💡 Execute: 'sincronizar processos ativos' no chat")
        sys.exit(0)
    
    # 2. Verificar processos com data de hoje
    hoje = date.today().strftime('%Y-%m-%d')
    print(f"\n2️⃣  Verificando processos chegando HOJE ({hoje})...")
    
    # Query similar à do obter_processos_chegando_hoje
    cursor.execute("""
        SELECT 
            processo_referencia,
            data_destino_final,
            eta_iso,
            modal,
            situacao_ce,
            numero_di,
            numero_duimp
        FROM processos_kanban
        WHERE 
            (
                DATE(data_destino_final) = DATE('now')
                OR (eta_iso IS NOT NULL AND DATE(eta_iso) = DATE('now'))
            )
        LIMIT 10
    """)
    
    processos_hoje = cursor.fetchall()
    print(f"   📅 Processos com data_destino_final ou eta_iso = hoje: {len(processos_hoje)}")
    
    if processos_hoje:
        print("   📋 Exemplos:")
        for proc in processos_hoje[:5]:
            print(f"      - {proc[0]}: chegada={proc[1]}, eta={proc[2]}, modal={proc[3]}")
    else:
        print("   ⚠️  Nenhum processo chegando hoje")
        print("   💡 Verificando processos com datas próximas...")
        
        # Verificar processos com data nos próximos 7 dias
        cursor.execute("""
            SELECT 
                processo_referencia,
                data_destino_final,
                eta_iso,
                modal
            FROM processos_kanban
            WHERE 
                (data_destino_final IS NOT NULL AND DATE(data_destino_final) BETWEEN DATE('now') AND DATE('now', '+7 days'))
                OR (eta_iso IS NOT NULL AND DATE(eta_iso) BETWEEN DATE('now') AND DATE('now', '+7 days'))
            ORDER BY data_destino_final ASC, eta_iso ASC
            LIMIT 10
        """)
        
        processos_proximos = cursor.fetchall()
        if processos_proximos:
            print(f"   📅 Processos chegando nos próximos 7 dias: {len(processos_proximos)}")
            for proc in processos_proximos[:5]:
                print(f"      - {proc[0]}: chegada={proc[1]}, eta={proc[2]}, modal={proc[3]}")
        else:
            print("   ⚠️  Nenhum processo chegando nos próximos 7 dias")
    
    # 3. Verificar processos prontos para registro
    print(f"\n3️⃣  Verificando processos PRONTOS PARA REGISTRO...")
    cursor.execute("""
        SELECT COUNT(*) FROM processos_kanban
        WHERE 
            DATE(data_destino_final) <= DATE('now')
            AND (numero_di IS NULL OR numero_di = '' OR numero_di = '/       -')
            AND (numero_duimp IS NULL OR numero_duimp = '')
            AND (situacao_ce IS NULL OR situacao_ce != 'ENTREGUE')
            AND (situacao_entrega IS NULL OR situacao_entrega != 'ENTREGUE')
    """)
    
    prontos = cursor.fetchone()[0]
    print(f"   ✅ Processos prontos para registro: {prontos}")
    
    # 4. Verificar formato das datas
    print(f"\n4️⃣  Verificando formato das datas...")
    cursor.execute("""
        SELECT 
            processo_referencia,
            data_destino_final,
            eta_iso,
            typeof(data_destino_final) as tipo_data_destino,
            typeof(eta_iso) as tipo_eta
        FROM processos_kanban
        WHERE data_destino_final IS NOT NULL OR eta_iso IS NOT NULL
        LIMIT 5
    """)
    
    exemplos_datas = cursor.fetchall()
    print(f"   📋 Exemplos de formatos de data:")
    for ex in exemplos_datas:
        print(f"      - {ex[0]}: data_destino_final={ex[1]} ({ex[3]}), eta_iso={ex[2]} ({ex[4]})")
    
    # 5. Verificar se há dados_completos_json (pode ter ETA lá)
    print(f"\n5️⃣  Verificando dados_completos_json...")
    cursor.execute("""
        SELECT COUNT(*) FROM processos_kanban
        WHERE dados_completos_json IS NOT NULL
    """)
    
    com_json = cursor.fetchone()[0]
    print(f"   📦 Processos com dados_completos_json: {com_json}")
    
    if com_json > 0:
        import json
        cursor.execute("""
            SELECT processo_referencia, dados_completos_json
            FROM processos_kanban
            WHERE dados_completos_json IS NOT NULL
            LIMIT 1
        """)
        
        exemplo = cursor.fetchone()
        if exemplo:
            try:
                dados = json.loads(exemplo[1])
                # Verificar se tem shipgov2 ou dataPrevisaoChegada
                tem_shipgov2 = 'shipgov2' in dados
                tem_data_prevista = 'dataPrevisaoChegada' in dados
                print(f"   📋 Exemplo {exemplo[0]}:")
                print(f"      - Tem shipgov2: {tem_shipgov2}")
                print(f"      - Tem dataPrevisaoChegada: {tem_data_prevista}")
                if tem_shipgov2:
                    shipgov2 = dados.get('shipgov2', {})
                    destino = shipgov2.get('destino_data_chegada')
                    print(f"      - shipgov2.destino_data_chegada: {destino}")
            except:
                print(f"   ⚠️  Erro ao parsear JSON")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("CONCLUSÃO")
    print("=" * 60)
    print()
    if total > 0 and len(processos_hoje) == 0:
        print("💡 Os processos estão no banco, mas NENHUM tem data de chegada = hoje.")
        print("   Isso é NORMAL se não há processos chegando hoje.")
        print("   O dashboard está funcionando corretamente!")
    elif total == 0:
        print("💡 Execute a sincronização de processos primeiro.")
    else:
        print("✅ Dados encontrados! O dashboard deve funcionar.")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
