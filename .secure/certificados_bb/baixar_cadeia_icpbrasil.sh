#!/bin/bash

# Script para baixar cadeia completa ICP-Brasil (AC SAFEWEB RFB v5)
# Autor: mAIke
# Data: 2025-01-06

set -e

OUTPUT_DIR="/Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb"
cd "$OUTPUT_DIR"

echo "=========================================="
echo "BAIXANDO CADEIA ICP-BRASIL (AC SAFEWEB RFB v5)"
echo "=========================================="
echo ""

# URLs dos certificados ICP-Brasil
# AC SAFEWEB RFB v5 é uma AC intermediária da ICP-Brasil
# Precisamos: AC SAFEWEB RFB v5 + AC Raiz ICP-Brasil

echo "1️⃣ Baixando certificado intermediário AC SAFEWEB RFB v5..."

# Tentar baixar da URL oficial da ICP-Brasil
# URL pode variar, vamos tentar algumas opções

# Opção 1: Diretório oficial ICP-Brasil
URL_AC_SAFEWEB="https://www.gov.br/iti/pt-br/assuntos/repositorio/certificados-digital/arquivos-certificados/AC-SAFEWEB-RFB-v5.crt"
URL_AC_RAIZ="https://www.gov.br/iti/pt-br/assuntos/repositorio/certificados-digital/arquivos-certificados/AC-Raiz-Brasileira-v5.crt"

# Tentar baixar
echo "   Tentando baixar AC SAFEWEB RFB v5..."
curl -s -L "$URL_AC_SAFEWEB" -o ac_safeweb_rfb_v5.crt 2>/dev/null || {
  echo "   ⚠️  Não foi possível baixar automaticamente"
  echo "   📋 Você precisará baixar manualmente:"
  echo "      1. Acesse: https://www.gov.br/iti/pt-br/assuntos/repositorio/certificados-digital"
  echo "      2. Baixe: AC SAFEWEB RFB v5"
  echo "      3. Baixe: AC Raiz Brasileira v5"
  exit 1
}

echo "   ✅ AC SAFEWEB RFB v5 baixado"

echo ""
echo "2️⃣ Baixando certificado raiz AC Raiz Brasileira v5..."
curl -s -L "$URL_AC_RAIZ" -o ac_raiz_brasileira_v5.crt 2>/dev/null || {
  echo "   ⚠️  Não foi possível baixar automaticamente"
  echo "   📋 Baixe manualmente de: https://www.gov.br/iti/pt-br/assuntos/repositorio/certificados-digital"
  exit 1
}

echo "   ✅ AC Raiz Brasileira v5 baixado"

# Converter .crt para .pem se necessário
echo ""
echo "3️⃣ Convertendo certificados para formato PEM..."

if [ -f ac_safeweb_rfb_v5.crt ]; then
  openssl x509 -in ac_safeweb_rfb_v5.crt -out ac_safeweb_rfb_v5.pem -outform PEM 2>/dev/null || \
  cp ac_safeweb_rfb_v5.crt ac_safeweb_rfb_v5.pem
fi

if [ -f ac_raiz_brasileira_v5.crt ]; then
  openssl x509 -in ac_raiz_brasileira_v5.crt -out ac_raiz_brasileira_v5.pem -outform PEM 2>/dev/null || \
  cp ac_raiz_brasileira_v5.crt ac_raiz_brasileira_v5.pem
fi

# Criar cadeia completa
echo ""
echo "4️⃣ Criando cadeia completa..."
cat certificado_empresa.pem \
    ac_safeweb_rfb_v5.pem \
    ac_raiz_brasileira_v5.pem \
    > cadeia_completa_para_importacao.pem

# Verificar
NUM_CERTS=$(grep -c "BEGIN CERTIFICATE" cadeia_completa_para_importacao.pem || echo "0")
echo "   Total de certificados na cadeia: $NUM_CERTS"

if [ "$NUM_CERTS" -ge 3 ]; then
  echo "   ✅ Cadeia completa criada com sucesso!"
else
  echo "   ⚠️  A cadeia ainda não está completa"
fi

echo ""
echo "=========================================="
echo "✅ Processo concluído!"
echo "=========================================="
echo ""
echo "📁 Arquivo para importar no Portal BB:"
echo "   $OUTPUT_DIR/cadeia_completa_para_importacao.pem"
echo ""



