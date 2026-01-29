#!/bin/bash
# Script simplificado para consultar NCM no TECwin (modo headless)

# Verificar se o NCM foi fornecido
if [ -z "$1" ]; then
    echo "❌ Uso: ./consultar_ncm.sh <CODIGO_NCM>"
    echo ""
    echo "Exemplo:"
    echo "  ./consultar_ncm.sh 96170010"
    exit 1
fi

NCM="$1"

# Buscar credenciais de variáveis de ambiente ou usar padrão
EMAIL="${TECWIN_EMAIL:-jalbuquerque@makeconsultores.com.br}"
SENHA="${TECWIN_SENHA:-bigmac}"

echo "🔍 Consultando NCM $NCM no TECwin..."
echo ""

# Executar consulta em modo headless (sem abrir navegador)
python3 tecwin_scraper.py \
    --ncm "$NCM" \
    --email "$EMAIL" \
    --senha "$SENHA" \
    --headless












