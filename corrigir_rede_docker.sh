#!/bin/bash
# Script para diagnosticar e corrigir problema de rede Docker

echo "🔍 DIAGNÓSTICO DE REDE DOCKER"
echo "=============================="
echo ""

# 1. Verificar se os containers estão rodando
echo "1️⃣  Verificando containers..."
docker compose ps

echo ""
echo "2️⃣  Verificando rede Docker..."
docker network inspect chat-ia2-independente_maike-network 2>/dev/null || echo "⚠️  Rede não encontrada"

echo ""
echo "3️⃣  Verificando conectividade do container web..."
docker compose exec web ping -c 2 db 2>&1 || echo "⚠️  Container web não consegue alcançar 'db'"

echo ""
echo "4️⃣  Verificando se o container db está acessível..."
docker compose exec db psql -U postgres -c "SELECT 1;" 2>&1 | head -5

echo ""
echo "=============================="
echo "💡 SOLUÇÃO:"
echo ""
echo "Se os containers não estão na mesma rede, execute:"
echo ""
echo "  docker compose down"
echo "  docker compose up -d"
echo ""
echo "Isso vai recriar a rede e reconectar os containers."
