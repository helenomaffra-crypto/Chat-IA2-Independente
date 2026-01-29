# 📥 Guia de Importação - Sistema de Legislação

## Como Importar Legislação

### 🎯 Resumo Rápido

**Você tem 2 opções:**
1. **Automática (URL)** - Sistema tenta baixar do site
2. **Manual (Copiar/Colar)** - Você copia o texto e cola

**Recomendação:** Tente a URL primeiro. Se não funcionar, use copiar/colar.

---

## Opção 1: Importação Automática por URL

### Como Funciona
O sistema baixa o conteúdo da URL (HTML ou PDF) e extrai o texto automaticamente.

### Exemplo
```python
from services.legislacao_service import LegislacaoService

service = LegislacaoService()

resultado = service.importar_ato_por_url(
    tipo_ato='IN',
    numero='680',
    ano=2006,
    sigla_orgao='RFB',
    url='https://www.gov.br/receitafederal/...',
    titulo_oficial='IN RFB 680/06 - Dispõe sobre...'  # Opcional
)

if resultado['sucesso']:
    print(f"✅ Importado: {resultado['trechos_importados']} trechos")
else:
    print(f"❌ Erro: {resultado['erro']}")
    # Se falhar, use Opção 2 (copiar/colar)
```

### Quando Funciona
- ✅ Site permite acesso direto (sem autenticação)
- ✅ HTML bem formatado
- ✅ PDF com texto extraível

### Quando Pode Falhar
- ❌ Site exige autenticação/login
- ❌ HTML com estrutura muito complexa
- ❌ PDF com texto em imagem (não extraível)
- ❌ Proteções anti-bot

---

## Opção 2: Importação Manual (Copiar e Colar)

### Como Funciona
Você copia o texto do site oficial e cola no código. O sistema parseia e salva.

### Passo a Passo

**1. Abrir o site oficial da legislação**
- Exemplo: Site da Receita Federal com IN 680/06

**2. Selecionar todo o texto**
- Windows/Linux: `Ctrl + A`
- Mac: `Cmd + A`

**3. Copiar o texto**
- Windows/Linux: `Ctrl + C`
- Mac: `Cmd + C`

**4. Colar no código Python**
```python
from services.legislacao_service import LegislacaoService

service = LegislacaoService()

# Cole o texto aqui (entre as aspas triplas)
texto_in680 = """
Art. 1º Esta Instrução Normativa dispõe sobre...

Art. 2º Para os efeitos desta Instrução Normativa...

Art. 3º O procedimento será realizado...
"""

# Importar
resultado = service.importar_ato_de_texto(
    tipo_ato='IN',
    numero='680',
    ano=2006,
    sigla_orgao='RFB',
    texto_bruto=texto_in680,
    titulo_oficial='IN RFB 680/06 - Dispõe sobre...'  # Opcional
)

if resultado['sucesso']:
    print(f"✅ Importado: {resultado['trechos_importados']} trechos")
```

### Vantagens
- ✅ Sempre funciona (não depende de URL)
- ✅ Você controla o que está importando
- ✅ Pode limpar/ajustar o texto antes
- ✅ Funciona mesmo com sites protegidos

---

## 🔄 Fluxo Recomendado

### 1. Primeira Tentativa: URL Automática
```python
resultado = service.importar_ato_por_url(...)
```

### 2. Se Falhar: Copiar e Colar
```python
# Copie o texto do site e cole aqui
texto = """..."""
resultado = service.importar_ato_de_texto(..., texto_bruto=texto)
```

### 3. Depois: Consultas Locais (Sem Internet)
```python
# Todas as consultas são locais (SQLite)
trechos = service.buscar_trechos_por_palavra_chave(...)
```

---

## 📋 Checklist de Importação

- [ ] Identificar tipo de ato (IN, Lei, Decreto, etc.)
- [ ] Anotar número e ano
- [ ] Anotar sigla do órgão (RFB, MF, MDIC, etc.)
- [ ] Tentar importação por URL primeiro
- [ ] Se falhar, copiar texto do site oficial
- [ ] Colar texto e usar `importar_ato_de_texto()`
- [ ] Verificar quantidade de trechos importados
- [ ] Testar busca para validar importação

---

## 💡 Dicas Importantes

1. **Importação é Uma Vez**: Depois de importar, todas as consultas são locais
2. **Texto Riscado**: Se o texto vier riscado no site, o sistema detecta automaticamente
3. **Artigos Revogados**: São marcados como `revogado=True` no banco
4. **Atualização**: Se importar novamente o mesmo ato, ele é atualizado (trechos antigos removidos)

---

## 🎯 Exemplo Real: IN 680/06

### Tentativa 1: URL (Pode Funcionar)
```python
url = "https://www.gov.br/receitafederal/.../in680-2006"
resultado = service.importar_ato_por_url('IN', '680', 2006, 'RFB', url)
```

### Tentativa 2: Manual (Sempre Funciona)
```python
# 1. Abrir: https://www.gov.br/receitafederal/.../in680-2006
# 2. Selecionar tudo (Ctrl+A / Cmd+A)
# 3. Copiar (Ctrl+C / Cmd+C)
# 4. Colar aqui:

texto = """
INSTRUÇÃO NORMATIVA RFB Nº 680, DE 2006
...
Art. 1º ...
Art. 2º ...
"""

resultado = service.importar_ato_de_texto('IN', '680', 2006, 'RFB', texto)
```

---

## ❓ Perguntas Frequentes

**P: Preciso fazer isso toda vez que consultar?**
R: Não! Importe uma vez. Depois, todas as consultas são locais (rápidas).

**P: E se a legislação for atualizada?**
R: Importe novamente. O sistema atualiza automaticamente (remove trechos antigos).

**P: Posso importar várias legislações?**
R: Sim! Cada legislação é independente (IN 680, IN 1234, Lei 9430, etc.).

**P: O texto precisa estar formatado perfeitamente?**
R: Não. O parser é robusto e tenta identificar artigos mesmo com formatação imperfeita.

