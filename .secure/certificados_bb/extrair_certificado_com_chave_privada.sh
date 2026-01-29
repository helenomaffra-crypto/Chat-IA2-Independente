#!/bin/bash

# Script para extrair certificado COM chave privada do .pfx para uso em mTLS
# Este certificado será usado nas requisições à API de Extratos do BB

echo "=========================================="
echo "EXTRAINDO CERTIFICADO COM CHAVE PRIVADA"
echo "=========================================="
echo ""

# Caminho do arquivo .pfx
PFX_FILE="../eCNPJ 4PL (valid 23-03-26) senha001.pfx"
OUTPUT_FILE="certificado_com_chave_privada.pem"
SENHA="senha001"

# Verificar se o arquivo .pfx existe
if [ ! -f "$PFX_FILE" ]; then
    echo "❌ Erro: Arquivo .pfx não encontrado: $PFX_FILE"
    exit 1
fi

echo "📁 Arquivo .pfx: $PFX_FILE"
echo "📄 Arquivo de saída: $OUTPUT_FILE"
echo ""

# Extrair certificado COM chave privada (flag -nodes remove a senha da chave privada)
echo "🔐 Extraindo certificado com chave privada..."
openssl pkcs12 -in "$PFX_FILE" \
  -nodes \
  -out "$OUTPUT_FILE" \
  -passin pass:"$SENHA" \
  -legacy

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Certificado extraído com sucesso!"
    echo ""
    
    # Verificar se tem chave privada
    if grep -q "BEGIN PRIVATE KEY\|BEGIN RSA PRIVATE KEY\|BEGIN EC PRIVATE KEY" "$OUTPUT_FILE"; then
        echo "✅ Certificado contém chave privada (OK para mTLS)"
    else
        echo "⚠️ Aviso: Certificado pode não conter chave privada"
    fi
    
    # Verificar tamanho
    TAMANHO=$(du -h "$OUTPUT_FILE" | cut -f1)
    echo "📊 Tamanho: $TAMANHO"
    echo ""
    echo "📁 Arquivo criado: $(pwd)/$OUTPUT_FILE"
    echo ""
    echo "=========================================="
    echo "✅✅✅ CERTIFICADO PRONTO! ✅✅✅"
    echo "=========================================="
    echo ""
    echo "📝 Próximos passos:"
    echo "1. Configure no .env:"
    echo "   BB_CERT_PATH=$(pwd)/$OUTPUT_FILE"
    echo ""
    echo "2. Teste novamente:"
    echo "   python3 teste_bb_api.py"
    echo ""
else
    echo ""
    echo "❌ Erro ao extrair certificado"
    exit 1
fi



