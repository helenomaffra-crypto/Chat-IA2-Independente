#!/bin/bash

# Script de Backup da Aplicação mAIke Assistente
# Data: 07/01/2026

set -e  # Parar em caso de erro

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Diretório raiz do projeto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# Data e hora para o backup
BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="$PROJECT_DIR/backups"
BACKUP_NAME="mAIke_assistente_backup_${BACKUP_DATE}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

echo -e "${GREEN}🗄️  Iniciando backup da aplicação mAIke Assistente...${NC}"
echo ""

# Criar diretório de backups se não existir
mkdir -p "$BACKUP_DIR"

# Lista de diretórios/arquivos para incluir no backup
INCLUDES=(
    "app.py"
    "ai_service.py"
    "db_manager.py"
    "requirements.txt"
    "services/"
    "utils/"
    "templates/"
    "docs/"
    "scripts/"
    ".env"
    "*.md"
    "*.txt"
    "*.json"
    "*.py"
    "legislacao_files/"
    # ✅ Comprovantes/prints do Mercante (AFRMM)
    "downloads/mercante/"
)

# Lista de diretórios/arquivos para excluir do backup
EXCLUDES=(
    "__pycache__/"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".pytest_cache/"
    "*.db"
    "*.db-shm"
    "*.db-wal"
    "*.log"
    "node_modules/"
    ".git/"
    ".venv/"
    "venv/"
    "downloads/"
    "*.pdf"
    ".secure/"
    "backups/"
    "*.cache"
)

echo -e "${YELLOW}📦 Copiando arquivos...${NC}"

# Criar diretório do backup
mkdir -p "$BACKUP_PATH"

# Copiar arquivos e diretórios
for item in "${INCLUDES[@]}"; do
    if [ -e "$item" ] || [ -d "$item" ]; then
        echo "  ✓ Copiando: $item"
        cp -r "$item" "$BACKUP_PATH/" 2>/dev/null || true
    fi
done

# Remover arquivos excluídos
echo -e "${YELLOW}🧹 Removendo arquivos temporários...${NC}"
find "$BACKUP_PATH" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$BACKUP_PATH" -name "*.pyc" -delete 2>/dev/null || true
find "$BACKUP_PATH" -name "*.pyo" -delete 2>/dev/null || true
find "$BACKUP_PATH" -name "*.pyd" -delete 2>/dev/null || true
find "$BACKUP_PATH" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find "$BACKUP_PATH" -name "*.db" -delete 2>/dev/null || true
find "$BACKUP_PATH" -name "*.db-shm" -delete 2>/dev/null || true
find "$BACKUP_PATH" -name "*.db-wal" -delete 2>/dev/null || true
find "$BACKUP_PATH" -name "*.log" -delete 2>/dev/null || true

# Criar arquivo de informações do backup
INFO_FILE="$BACKUP_PATH/BACKUP_INFO.txt"
cat > "$INFO_FILE" << EOF
# Informações do Backup

**Data do Backup:** $(date +"%d/%m/%Y %H:%M:%S")
**Versão da Aplicação:** 1.7.1
**Diretório Original:** $PROJECT_DIR
**Diretório do Backup:** $BACKUP_PATH

## Conteúdo do Backup

Este backup contém:
- ✅ Código-fonte completo (app.py, services/, utils/, etc.)
- ✅ Templates HTML
- ✅ Documentações (docs/)
- ✅ Scripts utilitários
- ✅ Requirements.txt
- ✅ Arquivos de configuração (.env, se existir)
- ✅ Legislações importadas (legislacao_files/)
- ✅ Comprovantes/prints do Mercante (downloads/mercante/)

## Excluído do Backup

- ❌ Arquivos temporários (__pycache__, *.pyc, etc.)
- ❌ Banco de dados SQLite (*.db, *.db-shm, *.db-wal)
- ❌ Logs (*.log)
- ❌ node_modules/
- ❌ Arquivos PDF temporários (downloads/)
- ❌ Outros downloads temporários (exceto downloads/mercante/)
- ❌ Arquivos sensíveis (.secure/)
- ❌ Backups anteriores (backups/)

## Como Restaurar

1. Extrair este backup para um diretório
2. Criar ambiente virtual: \`python3 -m venv venv\`
3. Ativar ambiente virtual: \`source venv/bin/activate\`
4. Instalar dependências: \`pip install -r requirements.txt\`
5. Copiar .env do backup ou criar novo
6. Executar: \`python app.py\`

## Observações

- Este backup foi criado automaticamente
- Para restaurar, siga as instruções acima
- Mantenha backups regulares para segurança

EOF

echo ""
echo -e "${GREEN}✅ Backup concluído com sucesso!${NC}"
echo ""
echo "📁 Localização: $BACKUP_PATH"
echo "📄 Informações: $INFO_FILE"
echo ""
echo -e "${YELLOW}💡 Dica: Mantenha backups regulares para segurança${NC}"
echo ""

# Criar link simbólico para último backup
LAST_BACKUP_LINK="$BACKUP_DIR/last_backup"
rm -f "$LAST_BACKUP_LINK"
ln -s "$BACKUP_NAME" "$LAST_BACKUP_LINK"
echo "🔗 Link criado: $LAST_BACKUP_LINK -> $BACKUP_NAME"

