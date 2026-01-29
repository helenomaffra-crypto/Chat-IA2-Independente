#!/bin/bash
# Script para copiar certificados do Santander para o diretório .secure

echo "📋 Copiando certificados do Santander..."
echo ""

# Criar diretório .secure se não existir
mkdir -p .secure

# Copiar arquivos
echo "📤 Copiando cert.pem..."
cp /Users/helenomaffra/SANTANDER/cert.pem .secure/santander_extrato_cert.pem

echo "📤 Copiando key.pem..."
cp /Users/helenomaffra/SANTANDER/key.pem .secure/santander_extrato_key.pem

echo "📤 Copiando certificado.pem (combinado)..."
cp /Users/helenomaffra/SANTANDER/certificado.pem .secure/santander_extrato_certificado.pem

echo ""
echo "✅ Certificados copiados com sucesso!"
echo ""
echo "📁 Arquivos copiados:"
ls -la .secure/santander_extrato*.pem
echo ""
echo "💡 Configure no .env:"
echo "   SANTANDER_CERT_FILE=$(pwd)/.secure/santander_extrato_cert.pem"
echo "   SANTANDER_KEY_FILE=$(pwd)/.secure/santander_extrato_key.pem"
echo ""
