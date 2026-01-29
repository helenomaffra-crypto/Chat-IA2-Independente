#!/usr/bin/env python3
"""
Script para preparar NESH para File Search da OpenAI.

Converte nesh_chunks.json em arquivo texto formatado para upload.
"""
import json
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

def preparar_nesh_para_file_search():
    """Converte nesh_chunks.json em arquivo texto formatado."""
    
    print("=" * 80)
    print("📚 PREPARANDO NESH PARA FILE SEARCH")
    print("=" * 80)
    print()
    
    # 1. Carregar JSON
    nesh_path = Path('nesh_chunks.json')
    if not nesh_path.exists():
        print("❌ Arquivo nesh_chunks.json não encontrado!")
        return None
    
    print(f"📖 Carregando {nesh_path}...")
    with open(nesh_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"✅ {len(chunks)} chunks carregados\n")
    
    # 2. Criar diretório de saída
    output_dir = Path('legislacao_files')
    output_dir.mkdir(exist_ok=True)
    
    # 3. Converter para texto formatado
    output_file = output_dir / 'NESH_Nota_Explicativa_Sistema_Harmonizado.txt'
    
    print(f"📝 Convertendo para texto formatado...")
    print(f"   Arquivo de saída: {output_file}\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Cabeçalho
        f.write("=" * 80 + "\n")
        f.write("NOTA EXPLICATIVA DO SISTEMA HARMONIZADO (NESH)\n")
        f.write("=" * 80 + "\n\n")
        f.write("Este documento contém as notas explicativas do Sistema Harmonizado,\n")
        f.write("organizadas por seção, capítulo, posição e subposição.\n\n")
        f.write("=" * 80 + "\n\n")
        
        # Agrupar por seção/capítulo para melhor organização
        secoes = {}
        for chunk in chunks:
            section = chunk.get('section', 'Sem seção')
            chapter = chunk.get('chapter', 'Sem capítulo')
            key = f"{section} - {chapter}"
            
            if key not in secoes:
                secoes[key] = []
            secoes[key].append(chunk)
        
        # Escrever conteúdo organizado
        for key in sorted(secoes.keys()):
            chunks_secao = secoes[key]
            
            # Cabeçalho da seção
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"{key}\n")
            if chunks_secao:
                chapter_title = chunks_secao[0].get('chapter_title', '')
                if chapter_title:
                    f.write(f"{chapter_title}\n")
            f.write("=" * 80 + "\n\n")
            
            # Escrever chunks da seção
            for chunk in chunks_secao:
                position_code = chunk.get('position_code', '')
                position_title = chunk.get('position_title', '')
                subposition_code = chunk.get('subposition_code')
                subposition_title = chunk.get('subposition_title')
                text = chunk.get('text', '')
                
                if not text:
                    continue
                
                # Cabeçalho do chunk
                f.write("-" * 80 + "\n")
                if subposition_code:
                    f.write(f"Subposição: {subposition_code}")
                    if subposition_title:
                        f.write(f" - {subposition_title}")
                    f.write("\n")
                    f.write(f"Posição: {position_code}")
                    if position_title:
                        f.write(f" - {position_title}")
                    f.write("\n")
                else:
                    f.write(f"Posição: {position_code}")
                    if position_title:
                        f.write(f" - {position_title}")
                    f.write("\n")
                f.write("-" * 80 + "\n\n")
                
                # Texto
                f.write(text)
                f.write("\n\n")
    
    file_size = output_file.stat().st_size / (1024 * 1024)  # MB
    print(f"✅ Arquivo criado: {output_file}")
    print(f"   Tamanho: {file_size:.2f} MB")
    print()
    
    return str(output_file)

if __name__ == '__main__':
    arquivo = preparar_nesh_para_file_search()
    if arquivo:
        print("=" * 80)
        print("✅ PREPARAÇÃO CONCLUÍDA!")
        print("=" * 80)
        print()
        print("💡 PRÓXIMOS PASSOS:")
        print("   1. Execute: python scripts/configurar_assistants_legislacao.py")
        print("   2. O script detectará automaticamente o arquivo NESH e fará upload")
        print("   3. Aguarde alguns minutos para processamento do vector store")
        print()





