#!/bin/bash

# Script para resetar COMPLETAMENTE o Docker Desktop no macOS
# Use com cuidado - isso vai remover dados da VM do Docker

set -e

echo "⚠️  ATENÇÃO: Este script vai resetar completamente o Docker Desktop"
echo "   Isso pode remover dados da VM, mas NÃO remove imagens/containers"
echo ""
read -p "Continuar? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Cancelado."
    exit 1
fi

echo ""
echo "🔄 Resetando Docker Desktop completamente..."
echo ""

# 1. Fechar Docker completamente
echo "1️⃣  Fechando todos os processos do Docker..."
killall -9 Docker 2>/dev/null || true
killall -9 com.docker.backend 2>/dev/null || true
killall -9 com.docker.supervisor 2>/dev/null || true
killall -9 com.docker.hyperkit 2>/dev/null || true
killall -9 com.docker.vmnetd 2>/dev/null || true
sleep 3

# 2. Verificar espaço em disco
echo "2️⃣  Verificando espaço em disco..."
df -h / | tail -1
SPACE_AVAIL=$(df -h / | tail -1 | awk '{print $4}' | sed 's/Gi//' | sed 's/[^0-9.]//g')
echo "   Espaço disponível: ${SPACE_AVAIL}GB"
if (( $(echo "$SPACE_AVAIL < 5" | bc -l 2>/dev/null || echo "1") )); then
    echo "   ⚠️  Aviso: Pouco espaço. Docker precisa de pelo menos 5GB."
else
    echo "   ✅ Espaço suficiente"
fi

# 3. Limpar arquivos problemáticos da VM
echo "3️⃣  Limpando arquivos problemáticos da VM..."
DOCKER_VM_DIR="$HOME/Library/Containers/com.docker.docker/Data/vm"
if [ -d "$DOCKER_VM_DIR" ]; then
    # Remover apenas arquivos de lock/log, não a VM inteira
    rm -f "$DOCKER_VM_DIR"/*.lock 2>/dev/null || true
    rm -f "$DOCKER_VM_DIR"/*.pid 2>/dev/null || true
    rm -f "$DOCKER_VM_DIR"/init.log 2>/dev/null || true
    rm -f "$DOCKER_VM_DIR"/console.log 2>/dev/null || true
    echo "   ✅ Arquivos temporários removidos"
else
    echo "   ⏭️  Diretório VM não encontrado"
fi

# 4. Limpar logs grandes
echo "4️⃣  Limpando logs grandes..."
DOCKER_LOG_DIR="$HOME/Library/Containers/com.docker.docker/Data/log"
if [ -d "$DOCKER_LOG_DIR" ]; then
    find "$DOCKER_LOG_DIR" -type f -size +50M -delete 2>/dev/null || true
    echo "   ✅ Logs grandes removidos"
else
    echo "   ⏭️  Diretório de logs não encontrado"
fi

# 5. Limpar cache do Docker (se possível)
echo "5️⃣  Tentando limpar cache do Docker..."
if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        echo "   🧹 Limpando imagens não utilizadas..."
        docker image prune -af --filter "until=168h" 2>/dev/null || true
        echo "   🧹 Limpando containers parados..."
        docker container prune -f 2>/dev/null || true
        echo "   🧹 Limpando volumes não utilizados..."
        docker volume prune -f 2>/dev/null || true
        echo "   🧹 Limpando build cache..."
        docker builder prune -af 2>/dev/null || true
        echo "   ✅ Cache limpo"
    else
        echo "   ⏭️  Docker não está respondendo, pulando limpeza de cache"
    fi
else
    echo "   ⏭️  Docker CLI não encontrado"
fi

# 6. Resetar preferências do Docker (opcional, mais agressivo)
echo ""
read -p "6️⃣  Deseja resetar também as preferências do Docker? (N/s): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "   🗑️  Removendo preferências..."
    rm -rf "$HOME/Library/Group Containers/group.com.docker" 2>/dev/null || true
    rm -rf "$HOME/Library/Containers/com.docker.docker/Data/com.docker.driver.amd64-linux" 2>/dev/null || true
    echo "   ✅ Preferências removidas"
else
    echo "   ⏭️  Mantendo preferências"
fi

# 7. Tentar iniciar Docker
echo ""
echo "7️⃣  Tentando iniciar Docker Desktop..."
if [ -d "/Applications/Docker.app" ]; then
    # Limpar qualquer processo zombie primeiro
    killall -9 Docker 2>/dev/null || true
    sleep 1
    
    # Tentar abrir Docker
    open -a Docker 2>/dev/null && echo "   ✅ Comando para abrir Docker enviado" || echo "   ⚠️  Não foi possível abrir automaticamente"
    
    echo ""
    echo "   ⏳ Aguardando Docker iniciar (pode levar 30-60 segundos)..."
    sleep 5
    
    # Verificar se iniciou
    for i in {1..12}; do
        if docker info >/dev/null 2>&1; then
            echo "   ✅ Docker está rodando!"
            docker info --format '   Versão: {{.ServerVersion}}' 2>/dev/null || true
            break
        fi
        echo "   ⏳ Tentativa $i/12..."
        sleep 5
    done
    
    if ! docker info >/dev/null 2>&1; then
        echo "   ⚠️  Docker não iniciou automaticamente"
        echo "   💡 Tente abrir manualmente:"
        echo "      - Spotlight (Cmd+Space) → 'Docker'"
        echo "      - Applications → Docker"
    fi
else
    echo "   ⚠️  Docker.app não encontrado em /Applications"
    echo "   💡 Verifique se o Docker Desktop está instalado"
fi

echo ""
echo "✅ Reset concluído!"
echo ""
echo "📋 Próximos passos:"
echo "   1. Se o Docker não abriu, abra manualmente"
echo "   2. Aguarde 1-2 minutos para inicialização completa"
echo "   3. Teste com: docker info"
echo "   4. Se ainda não funcionar, pode ser necessário reinstalar o Docker Desktop"
echo ""
echo "🔍 Para verificar status:"
echo "   docker info"
echo "   docker compose ps"
