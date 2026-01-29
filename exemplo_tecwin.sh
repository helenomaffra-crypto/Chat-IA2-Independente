#!/bin/bash
# Exemplo de uso do TECwin Scraper

# Exemplo 1: Consulta simples
# python3 tecwin_scraper.py --ncm 96170010 --email seu_email@exemplo.com --senha sua_senha

# Exemplo 2: Usando variáveis de ambiente (mais seguro)
# export TECWIN_EMAIL="seu_email@exemplo.com"
# export TECWIN_SENHA="sua_senha"
# python3 tecwin_scraper.py --ncm 96170010

# Exemplo 3: Modo headless + salvar HTML
# python3 tecwin_scraper.py --ncm 96170010 --email seu_email@exemplo.com --senha sua_senha --headless --salvar-html resultado.html

# Exemplo 4: Apenas testar login
# python3 tecwin_scraper.py --email seu_email@exemplo.com --senha sua_senha --apenas-login

echo "📋 Exemplos de uso do TECwin Scraper"
echo ""
echo "1. Consulta simples:"
echo "   python3 tecwin_scraper.py --ncm 96170010 --email seu_email@exemplo.com --senha sua_senha"
echo ""
echo "2. Usando variáveis de ambiente:"
echo "   export TECWIN_EMAIL='seu_email@exemplo.com'"
echo "   export TECWIN_SENHA='sua_senha'"
echo "   python3 tecwin_scraper.py --ncm 96170010"
echo ""
echo "3. Modo headless + salvar HTML:"
echo "   python3 tecwin_scraper.py --ncm 96170010 --email seu_email@exemplo.com --senha sua_senha --headless --salvar-html resultado.html"
echo ""
echo "4. Apenas testar login:"
echo "   python3 tecwin_scraper.py --email seu_email@exemplo.com --senha sua_senha --apenas-login"












