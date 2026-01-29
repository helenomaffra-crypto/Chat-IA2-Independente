#!/bin/bash

# Script para limpar espaço em disco
# Foca em backups do Cursor e recursos do Docker

set -e

echo "🔍 Verificando espaço em disco antes da limpeza..."
df -h / | tail -1

echo ""
echo "📦 Limpando backups do Cursor..."

# Verificar tamanho antes
CURSOR_BACKUP1="$HOME/Library/Application Support/CursorBackup"
CURSOR_BACKUP2="$HOME/Library/Application Support/Cursorbackup2"

if [ -d "$CURSOR_BACKUP1" ]; then
    SIZE1=$(du -sh "$CURSOR_BACKUP1" 2>/dev/null | cut -f1)
    echo "  📁 CursorBackup: $SIZE1"
    read -p "  ❓ Deseja limpar CursorBackup (65GB)? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "  🗑️  Removendo CursorBackup..."
        rm -rf "$CURSOR_BACKUP1"
        echo "  ✅ CursorBackup removido!"
    fi
fi

if [ -d "$CURSOR_BACKUP2" ]; then
    SIZE2=$(du -sh "$CURSOR_BACKUP2" 2>/dev/null | cut -f1)
    echo "  📁 Cursorbackup2: $SIZE2"
    read -p "  ❓ Deseja limpar Cursorbackup2 (6.6GB)? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        echo "  🗑️  Removendo Cursorbackup2..."
        rm -rf "$CURSOR_BACKUP2"
        echo "  ✅ Cursorbackup2 removido!"
    fi
fi

echo ""
echo "🐳 Limpando recursos do Docker..."

# Tentar limpar Docker se estiver rodando
if docker info >/dev/null 2>&1; then
    echo "  🧹 Limpando imagens não utilizadas..."
    docker image prune -af --filter "until=168h" 2>/dev/null || true
    
    echo "  🧹 Limpando containers parados..."
    docker container prune -f 2>/dev/null || true
    
    echo "  🧹 Limpando volumes não utilizados..."
    docker volume prune -f 2>/dev/null || true
    
    echo "  🧹 Limpando build cache..."
    docker builder prune -af 2>/dev/null || true
    
    echo "  📊 Espaço liberado pelo Docker:"
    docker system df 2>/dev/null || true
else
    echo "  ⚠️  Docker não está rodando. Limpeza manual necessária."
    echo "  💡 Quando o Docker estiver rodando, execute:"
    echo "     docker system prune -af --volumes"
fi

echo ""
echo "🧹 Limpando cache do sistema..."

# Limpar cache do sistema (seguro)
CACHE_DIR="$HOME/Library/Caches"
if [ -d "$CACHE_DIR" ]; then
    echo "  📁 Cache total: $(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)"
    read -p "  ❓ Deseja limpar caches antigos? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        # Limpar caches de apps específicos (seguro)
        find "$CACHE_DIR" -type f -atime +30 -delete 2>/dev/null || true
        echo "  ✅ Caches antigos (>30 dias) removidos!"
    fi
fi

echo ""
echo "🗑️  Limpando lixeira..."
if [ -d "$HOME/.Trash" ]; then
    TRASH_SIZE=$(du -sh "$HOME/.Trash" 2>/dev/null | cut -f1)
    echo "  📁 Lixeira: $TRASH_SIZE"
    read -p "  ❓ Deseja esvaziar a lixeira? (s/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf "$HOME/.Trash"/*
        echo "  ✅ Lixeira esvaziada!"
    fi
fi

echo ""
echo "✅ Limpeza concluída!"
echo ""
echo "🔍 Verificando espaço em disco após a limpeza..."
df -h / | tail -1

echo ""
echo "💡 Dica: Se ainda precisar de mais espaço, verifique:"
echo "   - ~/Downloads (1.3GB)"
echo "   - ~/Library/Application Support/Google (7.1GB)"
echo "   - Outros arquivos grandes: find ~ -type f -size +1G 2>/dev/null"
