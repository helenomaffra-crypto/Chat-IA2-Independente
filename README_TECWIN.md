# 🔍 TECwin Scraper - Consulta de NCM

Aplicação standalone para consultar NCM no site TECwin (Aduaneiras) usando automação de navegador.

## 📋 Pré-requisitos

1. **Python 3.7+**
2. **Chrome/Chromium instalado**
3. **ChromeDriver** (pode ser instalado automaticamente ou manualmente)

### Instalar ChromeDriver

**macOS:**
```bash
brew install chromedriver
```

**Ou baixar manualmente:**
- Acesse: https://chromedriver.chromium.org/
- Baixe a versão compatível com seu Chrome
- Coloque no PATH ou na mesma pasta do script

## 🚀 Instalação

```bash
# Instalar dependências
pip install -r requirements_tecwin.txt

# Ou instalar diretamente
pip install selenium webdriver-manager
```

## 💻 Uso

### Consultar um NCM

```bash
python3 tecwin_scraper.py \
  --ncm 96170010 \
  --email seu_email@exemplo.com \
  --senha sua_senha
```

### Modo Headless (sem interface gráfica)

```bash
python3 tecwin_scraper.py \
  --ncm 96170010 \
  --email seu_email@exemplo.com \
  --senha sua_senha \
  --headless
```

### Apenas testar login

```bash
python3 tecwin_scraper.py \
  --email seu_email@exemplo.com \
  --senha sua_senha \
  --apenas-login
```

### Salvar HTML da página

```bash
python3 tecwin_scraper.py \
  --ncm 96170010 \
  --email seu_email@exemplo.com \
  --senha sua_senha \
  --salvar-html ncm_96170010.html
```

## 📝 Exemplos

### Exemplo 1: Consulta simples
```bash
python3 tecwin_scraper.py --ncm 96170010 --email usuario@exemplo.com --senha senha123
```

### Exemplo 2: Modo headless + salvar HTML
```bash
python3 tecwin_scraper.py \
  --ncm 96170010 \
  --email usuario@exemplo.com \
  --senha senha123 \
  --headless \
  --salvar-html resultado.html
```

## ⚙️ Como Funciona

1. **Inicializa navegador**: Abre Chrome/Chromium com Selenium
2. **Faz login**: Navega até a página de login e preenche credenciais
3. **Consulta NCM**: Navega até a página de consulta do NCM
4. **Extrai dados**: Tenta extrair informações da página (tabelas, divs, etc.)
5. **Retorna resultados**: Exibe dados no console e opcionalmente salva HTML

## 🔧 Estrutura do Código

- `TecwinScraper`: Classe principal que gerencia o navegador e scraping
- `login()`: Método para fazer login no TECwin
- `consultar_ncm()`: Método para consultar um NCM específico
- `fechar()`: Método para fechar o navegador

## ⚠️ Limitações

- **Depende da estrutura HTML**: Se o site mudar, pode precisar ajustar seletores
- **Requer ChromeDriver**: Precisa estar instalado e no PATH
- **Pode precisar de ajustes**: Seletores CSS/XPath podem precisar ser ajustados conforme a estrutura real da página

## 🐛 Troubleshooting

### Erro: "ChromeDriver not found"
```bash
# macOS
brew install chromedriver

# Ou baixar manualmente e colocar no PATH
```

### Erro: "Element not found"
- A estrutura da página pode ter mudado
- Verifique os seletores CSS/XPath no código
- Use `--salvar-html` para analisar a estrutura da página

### Login não funciona
- Verifique se as credenciais estão corretas
- Tente usar `--apenas-login` para testar
- Verifique se não há captcha ou verificação adicional

## 📌 Notas Importantes

- ⚠️ **Esta aplicação é standalone** - não modifica o código do Chat-IA-Independente
- ⚠️ **Use com responsabilidade** - respeite os termos de uso do TECwin
- ⚠️ **Credenciais**: Nunca commite credenciais no código. Use variáveis de ambiente ou arquivo `.env`

## 🔐 Segurança

Para usar credenciais de forma segura:

```bash
# Criar arquivo .env_tecwin (não commitar!)
echo "TECWIN_EMAIL=seu_email@exemplo.com" > .env_tecwin
echo "TECWIN_SENHA=sua_senha" >> .env_tecwin
chmod 600 .env_tecwin

# Usar no script (precisa adicionar suporte a .env)
```

Ou usar variáveis de ambiente:
```bash
export TECWIN_EMAIL="seu_email@exemplo.com"
export TECWIN_SENHA="sua_senha"
python3 tecwin_scraper.py --ncm 96170010
```












