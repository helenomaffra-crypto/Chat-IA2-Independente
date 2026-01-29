#!/usr/bin/env python3
"""
Script para verificar configurações de certificados do Santander.
"""
import os
from pathlib import Path

# Tentar carregar .env
env_path = Path('.env')
if env_path.exists():
    print("📋 Configurações de Certificados Santander no .env:\n")
    print("=" * 70)
    
    with open(env_path, 'r', encoding='utf-8') as f:
        linhas = f.readlines()
    
    # Buscar linhas relacionadas a certificados
    cert_extrato = None
    cert_ted = None
    pfx_password = None
    
    for linha in linhas:
        linha_limpa = linha.strip()
        if linha_limpa.startswith('#') or not linha_limpa:
            continue
        
        if 'SANTANDER_CERT_PATH' in linha and 'PAYMENTS' not in linha:
            cert_extrato = linha.strip()
        elif 'SANTANDER_PAYMENTS_CERT_PATH' in linha:
            cert_ted = linha.strip()
        elif 'SANTANDER_CERT_FILE' in linha and 'PAYMENTS' not in linha:
            if not cert_extrato:
                cert_extrato = linha.strip()
        elif 'SANTANDER_PAYMENTS_CERT_FILE' in linha:
            if not cert_ted:
                cert_ted = linha.strip()
        elif 'SANTANDER_PFX_PASSWORD' in linha:
            pfx_password = linha.strip()
    
    print("🔐 EXTRATO SANTANDER:")
    if cert_extrato:
        print(f"   {cert_extrato}")
        # Verificar se é .pfx
        if '.pfx' in cert_extrato.lower() or '.p12' in cert_extrato.lower():
            print("   ✅ Formato: .pfx (será extraído automaticamente)")
        elif '.pem' in cert_extrato.lower() or '.crt' in cert_extrato.lower():
            print("   ⚠️  Formato: .pem/.crt (não é .pfx)")
    else:
        print("   ⚠️  Nenhum certificado configurado para Extrato")
    
    print("\n💸 TED SANTANDER:")
    if cert_ted:
        print(f"   {cert_ted}")
        # Verificar se é .pfx
        if '.pfx' in cert_ted.lower() or '.p12' in cert_ted.lower():
            print("   ✅ Formato: .pfx (será extraído automaticamente)")
        elif '.pem' in cert_ted.lower() or '.crt' in cert_ted.lower():
            print("   ⚠️  Formato: .pem/.crt (não é .pfx)")
    else:
        print("   ℹ️  Usará fallback para SANTANDER_CERT_PATH (se configurado)")
    
    print("\n🔑 Senha do .pfx:")
    if pfx_password:
        # Não mostrar a senha completa por segurança
        senha_valor = pfx_password.split('=')[1] if '=' in pfx_password else 'N/A'
        if senha_valor and senha_valor != 'N/A':
            print(f"   ✅ Configurada: {senha_valor[:3]}*** (ocultada)")
        else:
            print(f"   {pfx_password}")
    else:
        print("   ⚠️  Não configurada (usará padrão: senha001)")
    
    print("\n" + "=" * 70)
    print("\n💡 RECOMENDAÇÃO:")
    
    if cert_extrato and cert_ted:
        if cert_extrato == cert_ted:
            print("   ✅ Ambos estão usando o mesmo certificado (ideal!)")
        else:
            print("   ⚠️  Certificados diferentes configurados")
            print("   💡 Considere usar o mesmo certificado para ambos")
    elif cert_extrato and not cert_ted:
        print("   ✅ TED usará o mesmo certificado do Extrato (fallback automático)")
    elif not cert_extrato and cert_ted:
        print("   ⚠️  Apenas TED tem certificado configurado")
        print("   💡 Configure SANTANDER_CERT_PATH para o Extrato também")
    else:
        print("   ❌ Nenhum certificado configurado!")
        print("   💡 Configure SANTANDER_CERT_PATH no .env")
    
    # Verificar se os arquivos existem
    print("\n📁 Verificação de Arquivos:")
    if cert_extrato:
        caminho = cert_extrato.split('=')[1].strip() if '=' in cert_extrato else None
        if caminho:
            caminho = caminho.strip('"').strip("'")
            if os.path.exists(caminho):
                print(f"   ✅ Extrato: {caminho} (existe)")
            else:
                print(f"   ❌ Extrato: {caminho} (NÃO encontrado!)")
    
    if cert_ted:
        caminho = cert_ted.split('=')[1].strip() if '=' in cert_ted else None
        if caminho:
            caminho = caminho.strip('"').strip("'")
            if os.path.exists(caminho):
                print(f"   ✅ TED: {caminho} (existe)")
            else:
                print(f"   ❌ TED: {caminho} (NÃO encontrado!)")
    
else:
    print("❌ Arquivo .env não encontrado no diretório atual")
    print(f"   Procurando em: {os.getcwd()}")
