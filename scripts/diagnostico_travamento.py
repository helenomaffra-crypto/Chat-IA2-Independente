#!/usr/bin/env python3
"""
Script de diagnóstico para identificar travamentos na aplicação.
"""
import sys
import time
import traceback
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("🔍 DIAGNÓSTICO DE TRAVAMENTO")
print("=" * 70)
print()

# 1. Testar imports básicos
print("1️⃣ Testando imports básicos...")
try:
    from db_manager import init_db, get_db_connection
    print("   ✅ db_manager importado")
except Exception as e:
    print(f"   ❌ Erro ao importar db_manager: {e}")
    traceback.print_exc()
    sys.exit(1)

# 2. Testar inicialização do banco
print("\n2️⃣ Testando inicialização do banco SQLite...")
try:
    start = time.time()
    init_db()
    elapsed = time.time() - start
    print(f"   ✅ Banco inicializado em {elapsed:.2f}s")
    if elapsed > 5:
        print(f"   ⚠️ ATENÇÃO: Inicialização demorou mais de 5 segundos!")
except Exception as e:
    print(f"   ❌ Erro ao inicializar banco: {e}")
    traceback.print_exc()
    sys.exit(1)

# 3. Testar conexão SQL Server
print("\n3️⃣ Testando conexão SQL Server (com timeout)...")
try:
    from utils.sql_server_adapter import get_sql_adapter
    adapter = get_sql_adapter()
    
    start = time.time()
    # Usar timeout curto para não travar
    result = adapter.test_connection()
    elapsed = time.time() - start
    
    if result.get('success'):
        print(f"   ✅ SQL Server OK (tempo: {elapsed:.2f}s)")
    else:
        print(f"   ⚠️ SQL Server não disponível: {result.get('error')} (tempo: {elapsed:.2f}s)")
    
    if elapsed > 10:
        print(f"   ⚠️ ATENÇÃO: Teste de conexão demorou mais de 10 segundos!")
except Exception as e:
    print(f"   ⚠️ Erro ao testar SQL Server: {e}")
    # Não é crítico, continuar

# 4. Testar sincronização Kanban
print("\n4️⃣ Testando importação de sincronização Kanban...")
try:
    from services.processo_kanban_service import iniciar_sincronizacao_background
    print("   ✅ Sincronização Kanban importada")
except Exception as e:
    print(f"   ⚠️ Erro ao importar sincronização Kanban: {e}")
    traceback.print_exc()

# 5. Testar notificações agendadas
print("\n5️⃣ Testando importação de notificações agendadas...")
try:
    from services.scheduled_notifications_service import ScheduledNotificationsService
    print("   ✅ Notificações agendadas importadas")
except Exception as e:
    print(f"   ⚠️ Erro ao importar notificações agendadas: {e}")
    traceback.print_exc()

# 6. Testar ChatService
print("\n6️⃣ Testando importação de ChatService...")
try:
    from services.chat_service import ChatService
    print("   ✅ ChatService importado")
except Exception as e:
    print(f"   ❌ Erro ao importar ChatService: {e}")
    traceback.print_exc()
    sys.exit(1)

# 7. Verificar se há processos travados
print("\n7️⃣ Verificando locks no banco de dados...")
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar se há locks
    cursor.execute("PRAGMA busy_timeout")
    timeout = cursor.fetchone()
    print(f"   ℹ️ SQLite busy_timeout: {timeout[0] if timeout else 'N/A'}ms")
    
    # Tentar uma query simples
    start = time.time()
    cursor.execute("SELECT 1")
    elapsed = time.time() - start
    print(f"   ✅ Query simples executada em {elapsed:.4f}s")
    
    conn.close()
except Exception as e:
    print(f"   ❌ Erro ao verificar locks: {e}")
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ DIAGNÓSTICO CONCLUÍDO")
print("=" * 70)
print()
print("💡 Se algum teste demorou muito (>5s), isso pode indicar o problema.")
print("💡 Verifique os logs acima para identificar qual etapa está travando.")




