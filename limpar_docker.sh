#!/bin/bash

# Script para limpar recursos do Docker após liberar espaço em disco

echo "🐳 Verificando se Docker está rodando..."

if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker não está rodando."
    echo "💡 Por favor, inicie o Docker Desktop manualmente e execute este script novamente."
    exit 1
fi

echo "✅ Docker está rodando!"
echo ""
echo "📊 Espaço usado pelo Docker ANTES da limpeza:"
docker system df

echo ""
echo "🧹 Limpando recursos do Docker..."

echo "  - Removendo imagens não utilizadas (mais de 7 dias)..."
docker image prune -af --filter "until=168h" 2>/dev/null || true

echo "  - Removendo containers parados..."
docker container prune -f 2>/dev/null || true

echo "  - Removendo volumes não utilizados..."
docker volume prune -f 2>/dev/null || true

echo "  - Removendo build cache..."
docker builder prune -af 2>/dev/null || true

echo ""
echo "📊 Espaço usado pelo Docker DEPOIS da limpeza:"
docker system df

echo ""
echo "✅ Limpeza do Docker concluída!"
