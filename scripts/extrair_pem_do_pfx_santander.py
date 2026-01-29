#!/usr/bin/env python3
"""
Script para extrair certificado .pem e chave .key do .pfx do Santander
de forma permanente, garantindo que seja o mesmo certificado cadastrado no Developer Portal.
"""
import subprocess
import os
import sys
from pathlib import Path

# Caminhos
pfx_path = "/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx"
senha = "senha001"
output_dir = "/Users/helenomaffra/SANTANDER"

# Arquivos de saída
cert_pem = os.path.join(output_dir, "cert.pem")
key_pem = os.path.join(output_dir, "key.pem")
certificado_combinado = os.path.join(output_dir, "certificado.pem")

print("=" * 80)
print("🔧 Extraindo Certificado .pem do .pfx do Santander")
print("=" * 80)
print()

# Verificar se o .pfx existe
if not os.path.exists(pfx_path):
    print(f"❌ Arquivo .pfx não encontrado: {pfx_path}")
    sys.exit(1)

print(f"✅ Arquivo .pfx encontrado: {pfx_path}")
print()

# Criar diretório de saída se não existir
os.makedirs(output_dir, exist_ok=True)

# Extrair certificado (.pem)
print("📤 Extraindo certificado...")
try:
    result = subprocess.run(
        ['openssl', 'pkcs12', '-in', pfx_path, '-clcerts', '-nokeys', '-out', cert_pem, '-passin', f'pass:{senha}'],
        capture_output=True,
        text=True,
        check=True
    )
    print(f"✅ Certificado extraído: {cert_pem}")
except subprocess.CalledProcessError as e:
    print(f"❌ Erro ao extrair certificado: {e}")
    print(f"   stderr: {e.stderr}")
    sys.exit(1)

# Extrair chave privada (.key)
print("📤 Extraindo chave privada...")
try:
    result = subprocess.run(
        ['openssl', 'pkcs12', '-in', pfx_path, '-nocerts', '-nodes', '-out', key_pem, '-passin', f'pass:{senha}'],
        capture_output=True,
        text=True,
        check=True
    )
    print(f"✅ Chave privada extraída: {key_pem}")
except subprocess.CalledProcessError as e:
    print(f"❌ Erro ao extrair chave privada: {e}")
    print(f"   stderr: {e.stderr}")
    sys.exit(1)

# Criar arquivo combinado (cert + key) - opcional
print("📤 Criando arquivo combinado (cert + key)...")
try:
    with open(certificado_combinado, 'w') as outfile:
        # Ler e escrever certificado
        with open(cert_pem, 'r') as cert_file:
            outfile.write(cert_file.read())
        # Ler e escrever chave
        with open(key_pem, 'r') as key_file:
            outfile.write(key_file.read())
    print(f"✅ Arquivo combinado criado: {certificado_combinado}")
except Exception as e:
    print(f"⚠️  Erro ao criar arquivo combinado: {e}")

print()
print("=" * 80)
print("✅ Extração concluída!")
print("=" * 80)
print()
print("📋 Arquivos criados:")
print(f"   1. Certificado: {cert_pem}")
print(f"   2. Chave privada: {key_pem}")
print(f"   3. Arquivo combinado: {certificado_combinado}")
print()
print("💡 Próximos passos:")
print("   1. Configure no .env:")
print(f"      SANTANDER_CERT_FILE={cert_pem}")
print(f"      SANTANDER_KEY_FILE={key_pem}")
print()
print("   2. OU use o arquivo combinado:")
print(f"      SANTANDER_CERT_PATH={certificado_combinado}")
print()
print("   3. Reinicie o Flask para carregar as mudanças")
print()
