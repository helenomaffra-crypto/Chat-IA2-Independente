#!/usr/bin/env python3
"""
Script para corrigir problemas de edição do arquivo .env

Este script:
1. Remove atributos estendidos problemáticos
2. Ajusta permissões
3. Garante que o arquivo está em UTF-8
4. Remove caracteres invisíveis que podem causar problemas
"""
import os
import sys
from pathlib import Path

def corrigir_env():
    """Corrige problemas com o arquivo .env"""
    env_path = Path('.env')
    
    if not env_path.exists():
        print("❌ Arquivo .env não encontrado!")
        return False
    
    print("🔧 Corrigindo arquivo .env...")
    
    # 1. Ler conteúdo atual
    try:
        with open(env_path, 'rb') as f:
            content = f.read()
        
        # Remover BOM se existir
        if content.startswith(b'\xef\xbb\xbf'):
            content = content[3:]
            print("   ✅ BOM removido")
        
        # Decodificar para string
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            # Tentar latin-1 como fallback
            text = content.decode('latin-1')
            print("   ⚠️ Encoding convertido de latin-1 para UTF-8")
        
        # Remover caracteres de controle problemáticos (exceto \n, \r, \t)
        lines = text.splitlines()
        cleaned_lines = []
        for i, line in enumerate(lines, 1):
            # Remover caracteres de controle invisíveis
            cleaned_line = ''.join(c for c in line if ord(c) >= 32 or c in '\n\r\t')
            cleaned_lines.append(cleaned_line)
        
        # 2. Fazer backup
        backup_path = env_path.with_suffix('.env.backup')
        with open(backup_path, 'wb') as f:
            f.write(content)
        print(f"   ✅ Backup criado: {backup_path}")
        
        # 3. Reescrever arquivo limpo
        with open(env_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(cleaned_lines))
            if not cleaned_lines[-1].endswith('\n'):
                f.write('\n')  # Garantir que termina com newline
        
        print("   ✅ Arquivo reescrito em UTF-8")
        
        # 4. Ajustar permissões
        os.chmod(env_path, 0o644)
        print("   ✅ Permissões ajustadas (644)")
        
        # 5. Tentar remover atributos estendidos (macOS)
        if sys.platform == 'darwin':
            try:
                import subprocess
                # Remover todos os atributos estendidos
                subprocess.run(['xattr', '-c', str(env_path)], 
                             capture_output=True, check=False)
                print("   ✅ Atributos estendidos removidos")
            except Exception as e:
                print(f"   ⚠️ Não foi possível remover atributos estendidos: {e}")
        
        print("\n✅✅✅ Arquivo .env corrigido com sucesso!")
        print(f"\n📋 Estatísticas:")
        print(f"   - Linhas: {len(cleaned_lines)}")
        print(f"   - Tamanho: {env_path.stat().st_size} bytes")
        print(f"   - Encoding: UTF-8")
        print(f"   - Permissões: {oct(env_path.stat().st_mode)[-3:]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir arquivo .env: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("="*60)
    print("🔧 Script de Correção do Arquivo .env")
    print("="*60)
    print()
    
    # Mudar para diretório do projeto
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    
    sucesso = corrigir_env()
    
    if sucesso:
        print("\n💡 Dica: Se o problema persistir, tente:")
        print("   1. Fechar e reabrir o editor (Cursor)")
        print("   2. Verificar se há outros processos usando o arquivo")
        print("   3. Reiniciar o editor completamente")
        sys.exit(0)
    else:
        print("\n❌ Falha ao corrigir arquivo .env")
        sys.exit(1)



