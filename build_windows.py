#!/usr/bin/env python3
"""
Script para criar executável Windows da aplicação Chat IA.
Usa PyInstaller para gerar um .exe standalone.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    print("🔨 Criando executável Windows...")
    print("=" * 60)
    
    # Verificar se PyInstaller está instalado
    try:
        import PyInstaller
        print("✅ PyInstaller encontrado")
    except ImportError:
        print("❌ PyInstaller não encontrado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller instalado")
    
    # Diretório base
    base_dir = Path(__file__).parent
    os.chdir(base_dir)
    
    # Limpar builds anteriores
    print("\n🧹 Limpando builds anteriores...")
    for dir_name in ['build', 'dist', '__pycache__']:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"   ✅ Removido: {dir_name}/")
    
    # Arquivos e pastas a incluir
    datas = [
        ('templates', 'templates'),
        ('nesh_chunks.json', '.'),  # ✅ NESH necessário para busca de notas explicativas
    ]
    
    # Arquivos ocultos (hidden files) a incluir
    hiddenimports = [
        'flask',
        'werkzeug',
        'sqlite3',
        'requests',
        'openai',
        'duckduckgo_search',
        'xhtml2pdf',
        'pyodbc',
    ]
    
    # Detectar sistema operacional
    is_windows = sys.platform == 'win32'
    separator = ';' if is_windows else ':'
    
    # Comando PyInstaller
    cmd = [
        'pyinstaller',
        '--name=Chat-IA-DUIMP',
        '--onefile',  # Um único arquivo .exe
        '--console',  # Com console para ver logs (mudar para --windowed se não quiser)
        f'--add-data=templates{separator}templates',  # Separador correto por OS
        f'--add-data=nesh_chunks.json{separator}.',  # NESH necessário para busca
        '--hidden-import=flask',
        '--hidden-import=werkzeug',
        '--hidden-import=sqlite3',
        '--hidden-import=requests',
        '--hidden-import=openai',
        '--hidden-import=duckduckgo_search',
        '--hidden-import=xhtml2pdf',
        '--hidden-import=pyodbc',
        '--hidden-import=services',
        '--hidden-import=services.agents',
        '--hidden-import=services.chat_service',
        '--hidden-import=services.notificacao_service',
        '--hidden-import=services.processo_kanban_service',
        '--hidden-import=db_manager',
        '--collect-all=flask',
        '--collect-all=werkzeug',
        '--icon=NONE',  # Adicionar ícone se tiver
        '--clean',
        'app.py'
    ]
    
    print("\n🔨 Executando PyInstaller...")
    print(f"   Comando: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\n✅ Executável criado com sucesso!")
        print(f"   📦 Arquivo: dist/Chat-IA-DUIMP.exe")
        print("\n📋 Próximos passos:")
        print("   1. Copiar o .exe para a máquina Windows")
        print("   2. Criar arquivo .env com as configurações")
        print("   3. Executar o .exe")
        print("\n⚠️  IMPORTANTE:")
        print("   - O .exe precisa estar na mesma pasta que o .env")
        print("   - O banco SQLite será criado na pasta do .exe")
        print("   - Certifique-se de ter acesso à rede (IPs e portas)")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao criar executável: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

