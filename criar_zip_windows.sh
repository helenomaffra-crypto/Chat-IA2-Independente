#!/bin/bash
# Script para criar ZIP da aplicação para criar executável no Windows

echo "📦 Criando ZIP para Windows..."
echo "=" * 60

# Nome do arquivo ZIP
ZIP_NAME="Chat-IA-Independente-Windows.zip"

# Remover ZIP anterior se existir
if [ -f "$ZIP_NAME" ]; then
    rm "$ZIP_NAME"
    echo "✅ ZIP anterior removido"
fi

# ✅ IMPORTANTE: Incluir arquivos JSON necessários e utilitários
# - nesh_chunks.json: necessário para lookup de NESH
# - utils/iata_to_country.py: tabela de conversão IATA → país (já incluído por padrão, mas garantindo)

# Criar ZIP excluindo arquivos desnecessários
# NOTA: nesh_chunks.json e utils/iata_to_country.py serão incluídos automaticamente
zip -r "$ZIP_NAME" . \
    -x "*.pyc" \
    -x "*__pycache__*" \
    -x "node_modules/*" \
    -x ".git/*" \
    -x "dist/*" \
    -x "build/*" \
    -x "*.db" \
    -x ".env" \
    -x "*.log" \
    -x "*.pdf" \
    -x "downloads/*" \
    -x "certs/*" \
    -x "test_*.py" \
    -x "corrigir_*.py" \
    -x "auditar_*.py" \
    -x "*.sh" \
    -x "package*.json" \
    -x ".cursor*" \
    -x ".vscode/*" \
    -x ".idea/*" \
    -x ".DS_Store" \
    -x "*.pfx" \
    -x "*.p12" \
    -x "relatorio_*.txt" \
    -x "resultados_*.json" \
    -x "*.token_cache.json" \
    -x ".integracomex_token_cache.json" \
    -x ".duimp_token_cache.json" \
    -x "debug_log.txt" \
    -x "COMO_ABRIR.md" \
    -x "ESTRUTURA_CODIGO.md" \
    -x "INDICE_ARQUIVOS.md" \
    -x "SOLUCAO_*.md" \
    -x "CORRECOES_*.md" \
    -x "README.md" \
    -x "RESUMO_*.md" \
    -x "docs/ANALISE_*.md" \
    -x "docs/DEPLOY_*.md" \
    -x "docs/DOCUMENTACAO_*.md" \
    -x "docs/ESTRATEGIA_*.md" \
    -x "docs/FLUXO_*.md" \
    -x "docs/IMPLEMENTACAO_*.md" \
    -x "docs/INCOMPATIBILIDADE_*.md" \
    -x "docs/LEVANTAMENTO_*.md" \
    -x "docs/PAPEL_*.md" \
    -x "docs/PERGUNTAS_*.md" \
    -x "docs/PLANO_*.md" \
    -x "docs/PROBLEMA_*.md" \
    -x "docs/README_*.md" \
    -x "docs/REGRA_*.md" \
    -x "docs/RESUMO_*.md" \
    -x "docs/STATUS_*.md" \
    -x "docs/TESTE_*.md" \
    -x "docs/VIABILIDADE_*.md" \
    -x "docs/INDICE_*.md" \
    -x "docs/Projeto-*.code-workspace"

# ✅ Verificar se arquivos críticos foram incluídos
echo ""
echo "🔍 Verificando arquivos críticos no ZIP..."
if unzip -l "$ZIP_NAME" | grep -q "nesh_chunks.json"; then
    echo "✅ nesh_chunks.json incluído"
else
    echo "⚠️ ATENÇÃO: nesh_chunks.json NÃO encontrado no ZIP!"
fi

if unzip -l "$ZIP_NAME" | grep -q "utils/iata_to_country.py"; then
    echo "✅ utils/iata_to_country.py incluído"
else
    echo "⚠️ ATENÇÃO: utils/iata_to_country.py NÃO encontrado no ZIP!"
fi

echo ""
echo "✅ ZIP criado: $ZIP_NAME"
echo ""
echo "📋 Próximos passos no Windows:"
echo "   1. Extrair o ZIP"
echo "   2. Instalar Python 3.9+ (se não tiver)"
echo "   3. Abrir PowerShell na pasta extraída"
echo "   4. Executar: pip install -r requirements.txt"
echo "   5. Executar: pip install pyinstaller"
echo "   6. Executar: python build_windows.py"
echo "   7. Encontrar o .exe em: dist\\Chat-IA-DUIMP.exe"
echo ""

