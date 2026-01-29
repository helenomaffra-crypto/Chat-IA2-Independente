# 📚 Guia de Uso - Sistema de Legislação

## Como Funciona

O sistema de legislação permite importar e consultar atos normativos (IN, Lei, Decreto, Portaria, etc.) de forma estruturada, preservando hierarquia e contexto.

## ⚙️ Dois Modos de Importação

### 1. Importação Automática por URL (Tentativa)
O sistema **tenta** baixar direto do site oficial:

```python
service.importar_ato_por_url(
    tipo_ato='IN',
    numero='680',
    ano=2006,
    sigla_orgao='RFB',
    url='https://www.gov.br/receitafederal/...'
)
```

**Como funciona:**
- ✅ Baixa HTML/PDF da URL automaticamente
- ✅ Extrai texto automaticamente
- ✅ Parseia e salva no banco

**Limitações:**
- ⚠️ Pode não funcionar se o site exigir autenticação
- ⚠️ PDF pode não preservar formatação de texto riscado
- ⚠️ HTML pode ter estrutura complexa que precisa ajustes

### 2. Importação Manual (Copiar e Colar) - Mais Confiável
Se a URL não funcionar, você **copia o texto** do site e cola:

```python
# 1. Você copia o texto do site oficial
texto_copiado = """
Art. 1º Esta Instrução Normativa...
Art. 2º Para os efeitos...
"""

# 2. Importa o texto colado
service.importar_ato_de_texto(
    tipo_ato='IN',
    numero='680',
    ano=2006,
    sigla_orgao='RFB',
    texto_bruto=texto_copiado
)
```

**Vantagens:**
- ✅ Sempre funciona (não depende de URL)
- ✅ Você controla o que está importando
- ✅ Pode limpar/ajustar o texto antes de importar

---

## 🎯 Fluxo Recomendado

### Passo 1: Importação (Uma Vez - ETL Manual)
**Opção A - Tentar URL primeiro:**
```python
resultado = service.importar_ato_por_url(...)
if not resultado['sucesso']:
    # Se falhar, usar opção B
```

**Opção B - Copiar e Colar (Mais Confiável):**
1. Abrir site oficial da legislação
2. Selecionar todo o texto (Ctrl+A / Cmd+A)
3. Copiar (Ctrl+C / Cmd+C)
4. Colar no código Python ou em um arquivo
5. Chamar `importar_ato_de_texto()` com o texto

### Passo 2: Consultas (Múltiplas Vezes - Sem Internet)
Depois de importar, todas as consultas são **locais** (SQLite):

```python
# Buscar trechos - NÃO precisa de internet
trechos = service.buscar_trechos_por_palavra_chave(
    'IN', '680', termos=['canal']
)
```

---

## 💡 Resposta Direta à Sua Pergunta

**"A aplicação vai pegar direto do site ou vou ter que copiar e colar?"**

**Resposta:** Você tem **ambas as opções**, mas recomendo:

1. **Primeiro, tentar URL** (pode funcionar automaticamente)
2. **Se não funcionar, copiar e colar** (sempre funciona)

**Por quê?**
- Sites governamentais podem ter proteções/estruturas complexas
- Copiar e colar é mais confiável e você tem controle total
- Você só precisa fazer isso **UMA VEZ** por legislação
- Depois, todas as consultas são locais (rápidas, sem internet)

---

## 📝 Exemplo Prático Completo

---

## 🚀 Uso Básico

### 1. Importar Legislação por URL

```python
from services.legislacao_service import LegislacaoService

service = LegislacaoService()

# Exemplo: Importar IN RFB 680/06
resultado = service.importar_ato_por_url(
    tipo_ato='IN',
    numero='680',
    ano=2006,
    sigla_orgao='RFB',
    url='https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/legislacao/instrucoes-normativas/in680-2006.pdf',
    titulo_oficial='IN RFB 680/06 - Dispõe sobre...'  # Opcional
)

if resultado['sucesso']:
    print(f"✅ Importado: {resultado['trechos_importados']} trechos")
    print(f"ID do ato: {resultado['legislacao_id']}")
else:
    print(f"❌ Erro: {resultado['erro']}")
```

### 2. Importar Legislação de Texto (já copiado)

```python
# Texto copiado do DOU ou site oficial
texto_bruto = """
Art. 1º Esta Instrução Normativa dispõe sobre...

Art. 2º Para os efeitos desta Instrução Normativa, considera-se:

I - conceito 1;

II - conceito 2.

Art. 3º O procedimento será realizado...

§ 1º No caso do disposto no caput...

§ 2º A documentação deverá...
"""

resultado = service.importar_ato_de_texto(
    tipo_ato='IN',
    numero='680',
    ano=2006,
    sigla_orgao='RFB',
    texto_bruto=texto_bruto,
    titulo_oficial='IN RFB 680/06 - Dispõe sobre...'
)
```

### 3. Buscar Ato

```python
# Buscar ato completo
ato = service.buscar_ato('IN', '680', ano=2006, sigla_orgao='RFB')

if ato:
    print(f"Título: {ato['titulo_oficial']}")
    print(f"Fonte: {ato['fonte_url']}")
    print(f"Em vigor: {ato['em_vigor']}")
```

### 4. Buscar Trechos por Palavra-chave

```python
# Buscar trechos que mencionam "canal de conferência"
trechos = service.buscar_trechos_por_palavra_chave(
    tipo_ato='IN',
    numero='680',
    termos=['canal', 'conferência'],
    ano=2006,
    sigla_orgao='RFB',
    limit=10
)

for trecho in trechos:
    print(f"\n{trecho['referencia']}")
    print(f"Tipo: {trecho['tipo_trecho']}")
    print(f"Texto com contexto:\n{trecho['texto_com_artigo']}")
```

---

## 📊 Estrutura dos Dados

### Tabela `legislacao`
Armazena informações do ato normativo:
- `tipo_ato`: 'IN', 'Lei', 'Decreto', 'Portaria', etc.
- `numero`: '680', '12345', etc.
- `ano`: 2006, 2024, etc.
- `sigla_orgao`: 'RFB', 'MF', 'MDIC', etc.
- `titulo_oficial`: Título ou ementa
- `fonte_url`: URL de origem
- `texto_integral`: Texto completo (opcional)

### Tabela `legislacao_trecho`
Armazena trechos hierárquicos:
- `referencia`: 'Art. 5º', 'Art. 5º, § 2º', etc.
- `tipo_trecho`: 'artigo', 'caput', 'paragrafo', 'inciso', 'alinea'
- `texto`: Texto do trecho isolado
- `texto_com_artigo`: Texto com contexto do artigo completo
- `numero_artigo`: Número do artigo (5, 7, etc.)
- `hierarquia_json`: `{"artigo": 5, "paragrafo": 2, "inciso": "III"}`

---

## 🔍 Exemplo Completo

```python
from services.legislacao_service import LegislacaoService

service = LegislacaoService()

# 1. Importar
resultado = service.importar_ato_por_url(
    tipo_ato='IN',
    numero='680',
    ano=2006,
    sigla_orgao='RFB',
    url='https://...'
)

# 2. Buscar trechos sobre um tema
trechos = service.buscar_trechos_por_palavra_chave(
    tipo_ato='IN',
    numero='680',
    termos=['base de cálculo', 'II'],
    limit=5
)

# 3. Exibir resultados
for trecho in trechos:
    print(f"\n{'='*60}")
    print(f"Referência: {trecho['referencia']}")
    print(f"Tipo: {trecho['tipo_trecho']}")
    print(f"\nTexto com contexto do artigo:")
    print(trecho['texto_com_artigo'])
    print(f"{'='*60}")
```

---

## ⚙️ Como o Parser Funciona

### 1. Detecção de Artigos
O parser identifica artigos usando regex:
- Padrão: `Art. Xº` ou `Art. X`
- Exemplo: `Art. 5º`, `Art. 7`

### 2. Separação Caput/Parágrafos
- **Caput**: Texto antes do primeiro parágrafo
- **Parágrafos**: Identificados por `§ Xº`

### 3. Preservação de Contexto
- **Caput**: `texto_com_artigo` = apenas o caput
- **Parágrafo**: `texto_com_artigo` = caput + parágrafo completo

Isso garante que ao consultar um parágrafo, você sempre tenha o contexto do artigo.

---

## 🎯 Casos de Uso

### Caso 1: "O que a IN 680/06 fala sobre canal de conferência?"
```python
trechos = service.buscar_trechos_por_palavra_chave(
    tipo_ato='IN',
    numero='680',
    termos=['canal', 'conferência']
)
# Retorna trechos com contexto completo do artigo
```

### Caso 2: "Qual artigo trata da base de cálculo do II?"
```python
trechos = service.buscar_trechos_por_palavra_chave(
    tipo_ato='IN',
    numero='680',
    termos=['base de cálculo', 'II', 'imposto importação']
)
# Retorna artigos que mencionam base de cálculo e II
```

### Caso 3: Consultar artigo específico
```python
# Buscar todos os trechos de um artigo
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('''
    SELECT referencia, texto_com_artigo
    FROM legislacao_trecho
    WHERE legislacao_id = ? AND numero_artigo = ?
    ORDER BY ordem
''', (legislacao_id, 5))

trechos_artigo_5 = cursor.fetchall()
```

---

## 📝 Notas Importantes

1. **Importação Idempotente**: Se o ato já existe, ele é atualizado (trechos antigos são removidos)

2. **Contexto Preservado**: Sempre que consultar um parágrafo/inciso, você recebe o contexto do artigo completo

3. **Dependências Opcionais**: 
   - `beautifulsoup4` para HTML
   - `PyPDF2` para PDF
   - Se não instaladas, o sistema avisa mas continua funcionando para importação de texto

4. **Parser Atual**: 
   - ✅ Artigos e caput
   - ✅ Parágrafos
   - ⏳ Incisos e alíneas (em desenvolvimento)

---

## 🔧 Próximos Passos

1. **Melhorar Parser**: Adicionar suporte a incisos e alíneas
2. **Integração com Chat**: Criar tools para o mAIke consultar legislação
3. **Interface Web**: Endpoint para importar/consultar via API

