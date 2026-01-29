#!/bin/bash

# Script FINAL para criar cadeia completa
# Autor: mAIke

cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb

echo "=========================================="
echo "CRIAR CADEIA COMPLETA - VERSÃO FINAL"
echo "=========================================="
echo ""

# Verificar arquivos existentes
echo "📁 Verificando arquivos..."
FILES_OK=true

if [ ! -f certificado_empresa.pem ]; then
  echo "❌ certificado_empresa.pem não encontrado"
  FILES_OK=false
else
  echo "✅ certificado_empresa.pem encontrado"
fi

# Verificar se temos os certificados intermediários (qualquer nome)
SAFEWEB_FILE=""
RAIZ_FILE=""

for file in *.pem *.crt *.cer 2>/dev/null; do
  if [ -f "$file" ] && [ "$file" != "certificado_empresa.pem" ] && [ "$file" != "cadeia_completa_para_importacao.pem" ]; then
    # Verificar subject do certificado
    SUBJECT=$(openssl x509 -in "$file" -noout -subject 2>/dev/null | tr '[:upper:]' '[:lower:]')
    if echo "$SUBJECT" | grep -qi "safeweb.*rfb\|rfb.*safeweb"; then
      SAFEWEB_FILE="$file"
      echo "✅ Encontrado AC SAFEWEB RFB v5: $file"
    elif echo "$SUBJECT" | grep -qi "raiz.*brasileira\|brasileira.*raiz\|ac raiz"; then
      RAIZ_FILE="$file"
      echo "✅ Encontrado AC Raiz Brasileira v5: $file"
    fi
  fi
done

if [ -z "$SAFEWEB_FILE" ]; then
  echo "❌ AC SAFEWEB RFB v5 não encontrado"
  FILES_OK=false
fi

if [ -z "$RAIZ_FILE" ]; then
  echo "❌ AC Raiz Brasileira v5 não encontrado"
  FILES_OK=false
fi

echo ""

if [ "$FILES_OK" = false ]; then
  echo "=========================================="
  echo "❌ FALTAM ARQUIVOS"
  echo "=========================================="
  echo ""
  echo "Você precisa baixar os certificados intermediários:"
  echo ""
  echo "1. Acesse: https://www.gov.br/iti/pt-br/assuntos/repositorio/certificados-digital"
  echo "2. Baixe:"
  echo "   - AC SAFEWEB RFB v5"
  echo "   - AC Raiz Brasileira v5"
  echo "3. Salve em: $(pwd)/"
  echo "4. Execute este script novamente: ./criar_cadeia_final.sh"
  echo ""
  exit 1
fi

# Criar arquivos temporários com nomes corretos
echo "📝 Preparando certificados..."
if [ "$SAFEWEB_FILE" != "ac_safeweb_rfb_v5.pem" ]; then
  openssl x509 -in "$SAFEWEB_FILE" -out ac_safeweb_rfb_v5.pem -outform PEM 2>/dev/null || \
  cp "$SAFEWEB_FILE" ac_safeweb_rfb_v5.pem
fi

if [ "$RAIZ_FILE" != "ac_raiz_brasileira_v5.pem" ]; then
  openssl x509 -in "$RAIZ_FILE" -out ac_raiz_brasileira_v5.pem -outform PEM 2>/dev/null || \
  cp "$RAIZ_FILE" ac_raiz_brasileira_v5.pem
fi

# Criar cadeia completa
echo ""
echo "🔗 Criando cadeia completa..."
cat certificado_empresa.pem \
    ac_safeweb_rfb_v5.pem \
    ac_raiz_brasileira_v5.pem \
    > cadeia_completa_para_importacao.pem

# Verificar
NUM_CERTS=$(grep -c "BEGIN CERTIFICATE" cadeia_completa_para_importacao.pem || echo "0")
echo ""
echo "=========================================="
echo "RESULTADO"
echo "=========================================="
echo "Total de certificados na cadeia: $NUM_CERTS"
echo ""

if [ "$NUM_CERTS" -ge 3 ]; then
  echo "✅✅✅ SUCESSO! CADEIA COMPLETA CRIADA! ✅✅✅"
  echo ""
  echo "📋 Estrutura:"
  echo "   1. Certificado da Empresa (4PL)"
  echo "   2. AC SAFEWEB RFB v5 (Intermediário)"
  echo "   3. AC Raiz Brasileira v5 (Raiz)"
  echo ""
  echo "📁 Arquivo pronto:"
  echo "   $(pwd)/cadeia_completa_para_importacao.pem"
  echo ""
  echo "📤 Envie este arquivo ao Portal BB!"
elif [ "$NUM_CERTS" -eq 2 ]; then
  echo "⚠️  Cadeia tem 2 certificados (pode funcionar)"
  echo "   Arquivo: $(pwd)/cadeia_completa_para_importacao.pem"
else
  echo "❌ Cadeia incompleta (apenas $NUM_CERTS certificado)"
fi

echo ""



