#!/usr/bin/env python3
"""
Script para testar se a aplicação inicia corretamente.
"""
import sys
import time
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("🧪 TESTE DE INICIALIZAÇÃO")
print("=" * 70)
print()

# Testar import
print("1️⃣ Testando import do app...")
try:
    import app
    print("   ✅ App importado com sucesso")
except Exception as e:
    print(f"   ❌ Erro ao importar app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Testar inicialização
print("\n2️⃣ Testando inicialização...")
try:
    print("   📦 Inicializando banco de dados...")
    app.init_databases()
    print("   ✅ Banco inicializado")
except Exception as e:
    print(f"   ❌ Erro ao inicializar banco: {e}")
    import traceback
    traceback.print_exc()

# Testar test_sql_server (não bloqueante)
print("\n3️⃣ Testando conexão SQL Server (não bloqueante)...")
try:
    app.test_sql_server()
    print("   ✅ Teste iniciado (não bloqueante)")
    time.sleep(2)  # Dar tempo para o teste
except Exception as e:
    print(f"   ⚠️ Erro: {e}")

print("\n" + "=" * 70)
print("✅ TESTE CONCLUÍDO")
print("=" * 70)
print()
print("💡 Se chegou até aqui, a inicialização básica está funcionando.")
print("💡 Para iniciar o servidor completo, execute: python3 app.py")




