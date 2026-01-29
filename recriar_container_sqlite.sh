#!/bin/bash
# Script para recriar o container com SQLite habilitado

echo "🔄 Recriando container para usar SQLite..."
echo ""

# 1. Parar containers
echo "1️⃣  Parando containers..."
docker compose down

# 2. Recriar containers
echo ""
echo "2️⃣  Recriando containers com novas configurações..."
docker compose up -d

# 3. Aguardar inicialização
echo ""
echo "3️⃣  Aguardando containers iniciarem..."
sleep 5

# 4. Verificar se está usando SQLite
echo ""
echo "4️⃣  Verificando se está usando SQLite..."
docker compose exec web python -c "
import os
use_postgres = os.getenv('USE_POSTGRES', 'NOT SET')
print(f'USE_POSTGRES: {use_postgres}')

if use_postgres.lower() == 'false':
    print('✅ Usando SQLite (correto)')
else:
    print('❌ Ainda usando PostgreSQL')
"

echo ""
echo "✅ Container recriado!"
echo ""
echo "💡 Agora teste:"
echo "   docker compose exec web python verificar_dados_sqlite.py"
