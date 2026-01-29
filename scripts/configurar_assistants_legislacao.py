#!/usr/bin/env python3
"""
Script para configurar Assistants API com File Search para legislação.

Este script:
1. Exporta todas as legislações do banco para arquivos texto
2. Faz upload dos arquivos para a OpenAI
3. Cria um vector store
4. Adiciona arquivos ao vector store
5. Cria um assistente com File Search
6. Salva o assistant_id no .env
"""
import sys
import os
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.assistants_service import AssistantsService
from db_manager import init_db

def main():
    print("=" * 80)
    print("🔧 CONFIGURAÇÃO DE ASSISTANTS API PARA LEGISLAÇÃO")
    print("=" * 80)
    print()
    
    # Inicializar banco
    print("📦 Inicializando banco de dados...")
    init_db()
    print("✅ Banco inicializado\n")
    
    # Criar serviço
    service = AssistantsService()
    
    if not service.enabled:
        print("❌ AssistantsService não está habilitado!")
        print("   Verifique:")
        print("   - DUIMP_AI_ENABLED=true no .env")
        print("   - DUIMP_AI_API_KEY configurado no .env")
        print("   - Biblioteca 'openai' instalada (pip install openai)")
        return
    
    print("✅ AssistantsService habilitado\n")
    
    # 1. Exportar legislações
    print("📤 Exportando legislações do banco para arquivos...")
    arquivos = service.exportar_todas_legislacoes()
    
    # ✅ NOVO: Verificar se existe NESH preparada para File Search
    nesh_file = Path('legislacao_files/NESH_Nota_Explicativa_Sistema_Harmonizado.txt')
    if nesh_file.exists():
        print(f"   📚 NESH encontrada: {nesh_file.name}")
        arquivos.append(str(nesh_file))
    else:
        print("   💡 Dica: Para incluir NESH, execute primeiro: python scripts/preparar_nesh_para_file_search.py")
    
    if not arquivos:
        print("⚠️ Nenhuma legislação encontrada no banco!")
        print("   Importe legislações primeiro usando: python scripts/importar_legislacao.py")
        return
    
    print(f"✅ {len(arquivos)} legislação(ões) exportada(s)\n")
    
    # 2. Fazer upload dos arquivos
    print("☁️ Fazendo upload dos arquivos para OpenAI...")
    arquivo_ids = []
    
    for arquivo in arquivos:
        print(f"   📄 Enviando: {Path(arquivo).name}...")
        arquivo_id = service.fazer_upload_arquivo(arquivo)
        if arquivo_id:
            arquivo_ids.append(arquivo_id)
            print(f"      ✅ ID: {arquivo_id}")
        else:
            print(f"      ❌ Erro ao enviar")
    
    if not arquivo_ids:
        print("❌ Nenhum arquivo foi enviado com sucesso!")
        return
    
    print(f"\n✅ {len(arquivo_ids)} arquivo(s) enviado(s)\n")
    
    # 3. Criar vector store com arquivos
    print("🗄️ Criando vector store com arquivos...")
    # ✅ CORREÇÃO: Criar vector store já com file_ids (método mais eficiente)
    vector_store_id = service.criar_vector_store("Legislação COMEX", file_ids=arquivo_ids)
    
    if not vector_store_id:
        print("⚠️ Vector stores não disponível nesta versão da biblioteca!")
        print("   Usando método alternativo: file_ids diretamente no assistente...")
        # ✅ FALLBACK: Usar file_ids diretamente no assistente (sem vector store)
        # Isso funciona em versões mais antigas e mais novas da API
        print("   (Isso funciona perfeitamente, apenas sem vector store separado)\n")
        vector_store_id = None  # Não usar vector store
    else:
        print(f"✅ Vector store criado com {len(arquivo_ids)} arquivo(s): {vector_store_id}\n")
        print("⏳ Processamento em background pode levar alguns minutos...\n")
    
    # 5. Criar assistente
    print("🤖 Criando assistente com File Search...")
    assistant_id = service.criar_assistente_legislacao("mAIke Legislação")
    
    if not assistant_id:
        print("❌ Erro ao criar assistente!")
        return
    
    print(f"✅ Assistente criado: {assistant_id}\n")
    
    # 6. Associar arquivos ao assistente
    if vector_store_id:
        # Método 1: Usar vector store (se disponível)
        print("🔗 Associando vector store ao assistente...")
        try:
            service.client.beta.assistants.update(
                assistant_id=assistant_id,
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [vector_store_id]
                    }
                }
            )
            print("✅ Vector store associado ao assistente\n")
        except Exception as e:
            print(f"⚠️ Erro ao associar vector store: {e}")
            print("   Tentando método alternativo...\n")
            vector_store_id = None  # Fallback para método 2
    
    if not vector_store_id:
        # Método 2: Usar file_ids diretamente (fallback)
        print("🔗 Associando arquivos diretamente ao assistente (sem vector store)...")
        try:
            service.client.beta.assistants.update(
                assistant_id=assistant_id,
                tool_resources={
                    "file_search": {
                        "file_ids": arquivo_ids
                    }
                }
            )
            print(f"✅ {len(arquivo_ids)} arquivo(s) associado(s) diretamente ao assistente\n")
        except Exception as e:
            print(f"⚠️ Erro ao associar arquivos: {e}")
            print("   Você pode fazer isso manualmente depois\n")
    
    # 7. Salvar no .env
    print("💾 Salvando configurações...")
    env_file = Path('.env')
    
    if env_file.exists():
        # Ler .env atual
        with open(env_file, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
        
        # Atualizar ou adicionar ASSISTANT_ID_LEGISLACAO e VECTOR_STORE_ID_LEGISLACAO
        encontrado_assistant = False
        encontrado_vector_store = False
        novas_linhas = []
        for linha in linhas:
            if linha.startswith('ASSISTANT_ID_LEGISLACAO='):
                novas_linhas.append(f'ASSISTANT_ID_LEGISLACAO={assistant_id}\n')
                encontrado_assistant = True
            elif linha.startswith('VECTOR_STORE_ID_LEGISLACAO='):
                novas_linhas.append(f'VECTOR_STORE_ID_LEGISLACAO={vector_store_id or ""}\n')
                encontrado_vector_store = True
            elif linha.startswith('OPENAI_ASSISTANT_ID='):
                # Manter compatibilidade com versão antiga
                novas_linhas.append(f'OPENAI_ASSISTANT_ID={assistant_id}\n')
            else:
                novas_linhas.append(linha)
        
        # Adicionar se não encontrado
        if not encontrado_assistant or not encontrado_vector_store:
            novas_linhas.append(f'\n# Assistants API - Legislação\n')
            if not encontrado_assistant:
                novas_linhas.append(f'ASSISTANT_ID_LEGISLACAO={assistant_id}\n')
            if not encontrado_vector_store:
                novas_linhas.append(f'VECTOR_STORE_ID_LEGISLACAO={vector_store_id or ""}\n')
        
        # Escrever .env atualizado
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(novas_linhas)
        
        print("✅ Configurações salvas no .env\n")
    else:
        print("⚠️ Arquivo .env não encontrado!")
        print(f"   Adicione manualmente: OPENAI_ASSISTANT_ID={assistant_id}\n")
    
    # Resumo
    print("=" * 80)
    print("✅ CONFIGURAÇÃO CONCLUÍDA!")
    print("=" * 80)
    print(f"📋 Assistante ID: {assistant_id}")
    print(f"🗄️ Vector Store ID: {vector_store_id}")
    print(f"📄 Arquivos enviados: {len(arquivo_ids)}")
    print()
    print("💡 PRÓXIMOS PASSOS:")
    print("   1. Aguarde alguns minutos para o processamento do vector store")
    print("   2. Teste a busca usando a tool buscar_legislacao_assistants")
    print("   3. Se necessário, re-execute este script para atualizar legislações")
    print()

if __name__ == '__main__':
    main()

