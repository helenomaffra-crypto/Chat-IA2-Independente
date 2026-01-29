#!/usr/bin/env python3
"""
Script de diagnóstico para verificar configuração de certificados do Santander Extrato.
"""
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Carregar .env
load_dotenv()

print("=" * 80)
print("🔍 DIAGNÓSTICO: Certificados Santander Extrato")
print("=" * 80)
print()

# Verificar variáveis de ambiente
cert_file = os.getenv("SANTANDER_CERT_FILE")
key_file = os.getenv("SANTANDER_KEY_FILE")
cert_path = os.getenv("SANTANDER_CERT_PATH")
client_id = os.getenv("SANTANDER_CLIENT_ID")
client_secret = os.getenv("SANTANDER_CLIENT_SECRET")

print("📋 Variáveis de Ambiente:")
print(f"   SANTANDER_CERT_FILE: {cert_file}")
print(f"   SANTANDER_KEY_FILE: {key_file}")
print(f"   SANTANDER_CERT_PATH: {cert_path}")
print(f"   SANTANDER_CLIENT_ID: {client_id[:20] + '...' if client_id and len(client_id) > 20 else client_id}")
print(f"   SANTANDER_CLIENT_SECRET: {'***' if client_secret else None}")
print()

# Verificar existência dos arquivos
print("📁 Verificação de Arquivos:")
if cert_file:
    exists = os.path.exists(cert_file)
    print(f"   ✅ SANTANDER_CERT_FILE existe: {exists} - {cert_file}")
else:
    print(f"   ⚠️  SANTANDER_CERT_FILE não configurado")

if key_file:
    exists = os.path.exists(key_file)
    print(f"   ✅ SANTANDER_KEY_FILE existe: {exists} - {key_file}")
else:
    print(f"   ⚠️  SANTANDER_KEY_FILE não configurado")

if cert_path:
    exists = os.path.exists(cert_path)
    print(f"   ✅ SANTANDER_CERT_PATH existe: {exists} - {cert_path}")
    if exists:
        is_pfx = cert_path.lower().endswith('.pfx') or cert_path.lower().endswith('.p12')
        print(f"      Tipo: {'PFX/P12' if is_pfx else 'PEM/CRT'}")
else:
    print(f"   ⚠️  SANTANDER_CERT_PATH não configurado")
print()

# Determinar qual será usado (mesma lógica do código)
print("🎯 Qual Certificado Será Usado (Ordem de Prioridade):")
if cert_file and key_file:
    cert_exists = os.path.exists(cert_file) if cert_file else False
    key_exists = os.path.exists(key_file) if key_file else False
    
    if cert_exists and key_exists:
        print(f"   ✅ PRIORIDADE 1: cert_file + key_file (será usado)")
        print(f"      cert={cert_file}")
        print(f"      key={key_file}")
    else:
        print(f"   ⚠️  PRIORIDADE 1: cert_file + key_file (não será usado - arquivos não existem)")
        if cert_path and os.path.exists(cert_path):
            print(f"   ✅ PRIORIDADE 2: cert_path (será usado como fallback)")
            print(f"      path={cert_path}")
        else:
            print(f"   ❌ PRIORIDADE 2: cert_path (não será usado - não configurado ou não existe)")
elif cert_path:
    if os.path.exists(cert_path):
        print(f"   ✅ PRIORIDADE 2: cert_path (será usado)")
        print(f"      path={cert_path}")
    else:
        print(f"   ❌ cert_path configurado mas arquivo não existe: {cert_path}")
else:
    print(f"   ❌ NENHUM certificado configurado!")
print()

# Verificar credenciais
print("🔑 Credenciais:")
if client_id and client_secret:
    print(f"   ✅ Client ID e Client Secret configurados")
else:
    print(f"   ❌ Client ID ou Client Secret não configurados!")
print()

# Recomendações
print("💡 Recomendações:")
if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
    print("   ✅ Configuração correta: cert_file + key_file (configuração original)")
    print("   ✅ Esta configuração será usada (prioridade 1)")
elif cert_path and os.path.exists(cert_path):
    print("   ⚠️  Usando cert_path (cert_file/key_file não configurados ou não existem)")
    print("   💡 Se você tinha cert_file/key_file funcionando antes, verifique se os arquivos existem")
else:
    print("   ❌ Nenhum certificado válido encontrado!")
    print("   💡 Configure SANTANDER_CERT_FILE e SANTANDER_KEY_FILE no .env")
print()

print("=" * 80)
