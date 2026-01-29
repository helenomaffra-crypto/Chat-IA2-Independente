#!/bin/bash

# Script para resetar completamente o Docker Desktop no macOS

set -e

echo "🔄 Resetando Docker Desktop..."
echo ""

# 1. Fechar Docker completamente
echo "1️⃣  Fechando processos do Docker..."
killall -9 Docker 2>/dev/null || true
killall -9 com.docker.backend 2>/dev/null || true
killall -9 com.docker.supervisor 2>/dev/null || true
killall -9 com.docker.hyperkit 2>/dev/null || true
sleep 2

# 2. Limpar locks e arquivos temporários problemáticos
echo "2️⃣  Limpando locks e arquivos temporários..."
rm -rf ~/Library/Containers/com.docker.docker/Data/vm/init.log 2>/dev/null || true
rm -rf ~/Library/Containers/com.docker.docker/Data/vm/*.lock 2>/dev/null || true
rm -rf ~/Library/Containers/com.docker.docker/Data/vm/*.pid 2>/dev/null || true

# 3. Verificar espaço em disco
echo "3️⃣  Verificando espaço em disco..."
df -h / | tail -1
SPACE_AVAIL=$(df -h / | tail -1 | awk '{print $4}' | sed 's/Gi//')
if (( $(echo "$SPACE_AVAIL < 5" | bc -l 2>/dev/null || echo "0") )); then
    echo "⚠️  Aviso: Pouco espaço em disco ($SPACE_AVAIL GB). Docker precisa de pelo menos 5GB."
else
    echo "✅ Espaço suficiente disponível ($SPACE_AVAIL GB)"
fi

# 4. Limpar cache do Docker (se possível)
echo "4️⃣  Tentando limpar cache do Docker..."
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    docker system prune -af --volumes 2>/dev/null || true
    echo "✅ Cache limpo"
else
    echo "⏭️  Docker não está rodando, pulando limpeza de cache"
fi

# 5. Limpar logs grandes
echo "5️⃣  Limpando logs grandes..."
find ~/Library/Containers/com.docker.docker/Data/log -type f -size +100M -delete 2>/dev/null || true
echo "✅ Logs limpos"

# 6. Tentar iniciar Docker
echo ""
echo "6️⃣  Tentando iniciar Docker Desktop..."
echo "💡 Se o Docker não abrir automaticamente, tente:"
echo "   - Abrir manualmente via Spotlight (Cmd+Space, digite 'Docker')"
echo "   - Ou via Applications > Docker"
echo ""

# Tentar abrir Docker
if [ -d "/Applications/Docker.app" ]; then
    open -a Docker 2>/dev/null && echo "✅ Comando para abrir Docker enviado" || echo "⚠️  Não foi possível abrir automaticamente"
else
    echo "⚠️  Docker.app não encontrado em /Applications"
    echo "💡 Verifique se o Docker Desktop está instalado"
fi

echo ""
echo "✅ Reset concluído!"
echo ""
echo "📋 Próximos passos:"
echo "   1. Aguarde o Docker Desktop iniciar (pode levar 1-2 minutos)"
echo "   2. Se não abrir, tente abrir manualmente"
echo "   3. Se ainda não funcionar, pode ser necessário reinstalar o Docker Desktop"
echo ""
echo "🔍 Para verificar se está funcionando:"
echo "   docker info"
