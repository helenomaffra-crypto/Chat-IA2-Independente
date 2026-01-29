#!/bin/bash

# Script para criar cadeia completa no formato correto do Banco do Brasil
# Autor: mAIke

cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb

echo "=========================================="
echo "CORRIGINDO CADEIA PARA FORMATO BB"
echo "=========================================="
echo ""

# Verificar arquivos
if [ ! -f certificado_empresa.pem ]; then
  echo "❌ certificado_empresa.pem não encontrado"
  exit 1
fi

if [ ! -f ac_safeweb_rfb_v5.pem ]; then
  echo "❌ ac_safeweb_rfb_v5.pem não encontrado"
  exit 1
fi

if [ ! -f ac_raiz_brasileira_v5.pem ]; then
  echo "❌ ac_raiz_brasileira_v5.pem não encontrado"
  exit 1
fi

echo "✅ Todos os arquivos encontrados"
echo ""

# Verificar se cada arquivo contém um certificado válido
echo "Verificando certificados individuais..."
CERT_EMPRESA=$(grep -c "BEGIN CERTIFICATE" certificado_empresa.pem)
CERT_SAFEWEB=$(grep -c "BEGIN CERTIFICATE" ac_safeweb_rfb_v5.pem)
CERT_RAIZ=$(grep -c "BEGIN CERTIFICATE" ac_raiz_brasileira_v5.pem)

echo "  Certificado Empresa: $CERT_EMPRESA certificado(s)"
echo "  AC SAFEWEB RFB v5: $CERT_SAFEWEB certificado(s)"
echo "  AC Raiz Brasileira v5: $CERT_RAIZ certificado(s)"
echo ""

# Criar arquivo temporário limpo
rm -f cadeia_completa_para_importacao.pem

# Adicionar certificados na ordem correta (empresa -> intermediário -> raiz)
# Garantir que cada certificado está em formato PEM correto
echo "Criando cadeia completa..."

# Certificado da empresa
echo "-----BEGIN CERTIFICATE-----" >> cadeia_completa_para_importacao.pem
grep -A 1000 "BEGIN CERTIFICATE" certificado_empresa.pem | grep -B 1000 "END CERTIFICATE" | grep -v "^--" >> cadeia_completa_para_importacao.pem
echo "" >> cadeia_completa_para_importacao.pem

# AC SAFEWEB RFB v5
echo "-----BEGIN CERTIFICATE-----" >> cadeia_completa_para_importacao.pem
grep -A 1000 "BEGIN CERTIFICATE" ac_safeweb_rfb_v5.pem | grep -B 1000 "END CERTIFICATE" | grep -v "^--" >> cadeia_completa_para_importacao.pem
echo "" >> cadeia_completa_para_importacao.pem

# AC Raiz Brasileira v5
echo "-----BEGIN CERTIFICATE-----" >> cadeia_completa_para_importacao.pem
grep -A 1000 "BEGIN CERTIFICATE" ac_raiz_brasileira_v5.pem | grep -B 1000 "END CERTIFICATE" | grep -v "^--" >> cadeia_completa_para_importacao.pem

# Método alternativo mais simples - apenas concatenar
echo ""
echo "Tentando método alternativo (concatenação simples)..."
cat certificado_empresa.pem > cadeia_completa_para_importacao.pem
echo "" >> cadeia_completa_para_importacao.pem
cat ac_safeweb_rfb_v5.pem >> cadeia_completa_para_importacao.pem
echo "" >> cadeia_completa_para_importacao.pem
cat ac_raiz_brasileira_v5.pem >> cadeia_completa_para_importacao.pem

# Verificar
NUM_CERTS=$(grep -c "BEGIN CERTIFICATE" cadeia_completa_para_importacao.pem)
echo ""
echo "=========================================="
echo "RESULTADO"
echo "=========================================="
echo "Total de certificados na cadeia: $NUM_CERTS"
echo ""

if [ "$NUM_CERTS" -ge 3 ]; then
  echo "✅ Cadeia criada com $NUM_CERTS certificados"
  echo ""
  echo "📋 Estrutura da cadeia:"
  openssl crl2pkcs7 -nocrl -certfile cadeia_completa_para_importacao.pem 2>/dev/null | \
    openssl pkcs7 -print_certs -noout -text 2>/dev/null | \
    grep -E "Subject:|Issuer:" | head -6 || echo "  (não foi possível ler)"
  echo ""
  echo "📁 Arquivo: $(pwd)/cadeia_completa_para_importacao.pem"
  echo "📊 Tamanho: $(ls -lh cadeia_completa_para_importacao.pem | awk '{print $5}')"
else
  echo "❌ Cadeia incompleta (apenas $NUM_CERTS certificado(s))"
  echo ""
  echo "Verificando arquivos individuais..."
  echo "Certificado empresa tem: $(grep -c 'BEGIN CERTIFICATE' certificado_empresa.pem) certificado(s)"
  echo "AC SAFEWEB tem: $(grep -c 'BEGIN CERTIFICATE' ac_safeweb_rfb_v5.pem) certificado(s)"
  echo "AC Raiz tem: $(grep -c 'BEGIN CERTIFICATE' ac_raiz_brasileira_v5.pem) certificado(s)"
fi

echo ""



