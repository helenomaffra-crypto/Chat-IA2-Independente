# 🧠 Como a IA Detecta Mapeamento Cliente → Categoria

## 📋 Explicação Didática Passo a Passo

Vou explicar como funciona o processo completo, desde quando você digita a mensagem até a regra ser salva no banco.

---

## 🎯 Cenário de Exemplo

**Você digita no chat:**
```
"maike o ALH vai ser alho ok?"
```

---

## 📊 Fluxo Completo (Passo a Passo)

### **PASSO 1: Sua Mensagem Chega ao Sistema**

```
Você → Chat Interface → ChatService.processar_mensagem()
```

**O que acontece:**
- Sua mensagem `"maike o ALH vai ser alho ok?"` chega no `ChatService`
- O sistema prepara para enviar para a IA (GPT-4o)

---

### **PASSO 2: Sistema Monta o Prompt para a IA**

Antes de enviar para a IA, o sistema monta dois prompts:

#### **A) System Prompt** (Instruções gerais para a IA)

Contém:
- Quem a IA é (mAIke, assistente especializado)
- Como pensar (Chain of Thought)
- Exemplos de uso
- **Lista de Tools disponíveis** (funções que a IA pode chamar)

#### **B) User Prompt** (Sua mensagem + contexto)

Contém:
- Sua mensagem: `"maike o ALH vai ser alho ok?"`
- Histórico da conversa (se houver)
- Contexto de sessão (se houver)

---

### **PASSO 3: IA Recebe a Lista de Tools**

A IA recebe uma lista de todas as tools (funções) disponíveis, incluindo:

```json
{
  "name": "salvar_regra_aprendida",
  "description": "Salva uma regra ou definição aprendida do usuário. 
                  Use quando o usuário explicar como fazer algo, definir 
                  um campo, dar uma instrução que deve ser lembrada, ou 
                  criar mapeamento de termos. 
                  
                  Exemplos: 
                  1) 'usar campo destfinal como confirmação de chegada' 
                     → salva regra de campo. 
                  2) 'o ALH vai ser alho' ou 'Diamond vai ser DMD' 
                     → salva mapeamento cliente→categoria 
                     (tipo_regra='cliente_categoria', 
                      contexto='normalizacao_cliente', 
                      nome_regra='ALH → ALHO' ou 'Diamond → DMD', 
                      aplicacao_texto='ALH → ALHO' ou 'Diamond → DMD'). 
                  
                  Para mapeamentos cliente→categoria, SEMPRE use 
                  tipo_regra='cliente_categoria' e 
                  contexto='normalizacao_cliente'."
}
```

**🔑 Ponto Chave:** A descrição da tool contém exemplos explícitos:
- `'o ALH vai ser alho'` → salva mapeamento
- `'Diamond vai ser DMD'` → salva mapeamento

---

### **PASSO 4: IA Analisa Sua Mensagem**

A IA (GPT-4o) recebe:
- Sua mensagem: `"maike o ALH vai ser alho ok?"`
- A lista de tools disponíveis
- Instruções de como pensar

**Processo de raciocínio da IA:**

```
1. O que o usuário quer fazer?
   → Parece que está definindo um mapeamento: "ALH vai ser alho"

2. Qual tool é mais apropriada?
   → Olhando a lista de tools...
   → Encontrei: "salvar_regra_aprendida"
   → A descrição diz: "o ALH vai ser alho" → salva mapeamento cliente→categoria
   → ✅ Isso é exatamente o que o usuário quer!

3. Quais parâmetros preciso extrair?
   → tipo_regra: 'cliente_categoria' (a descrição diz para usar isso)
   → contexto: 'normalizacao_cliente' (a descrição diz para usar isso)
   → nome_regra: 'ALH → ALHO' (formato sugerido na descrição)
   → descricao: 'Mapeia o termo "ALH" para "ALHO"'
   → aplicacao_texto: 'ALH → ALHO' (formato sugerido na descrição)
```

---

### **PASSO 5: IA Decide Chamar a Tool**

A IA decide que deve chamar `salvar_regra_aprendida` com os parâmetros:

```json
{
  "name": "salvar_regra_aprendida",
  "arguments": {
    "tipo_regra": "cliente_categoria",
    "contexto": "normalizacao_cliente",
    "nome_regra": "ALH → ALHO",
    "descricao": "Mapeia o termo 'ALH' para 'ALHO'",
    "aplicacao_texto": "ALH → ALHO"
  }
}
```

**🔑 Como a IA sabe isso?**

1. **Padrão na mensagem:** `"ALH vai ser alho"` segue o padrão `"X vai ser Y"`
2. **Exemplo na descrição:** A tool tem exemplo explícito: `'o ALH vai ser alho'`
3. **Instruções claras:** A descrição diz: "Para mapeamentos cliente→categoria, SEMPRE use tipo_regra='cliente_categoria'"

---

### **PASSO 6: Sistema Executa a Tool**

O `ChatService` recebe a decisão da IA e executa:

```python
# services/chat_service.py (linha ~2127)
elif nome_funcao == "salvar_regra_aprendida":
    from services.learned_rules_service import salvar_regra_aprendida
    
    resultado = salvar_regra_aprendida(
        tipo_regra='cliente_categoria',
        contexto='normalizacao_cliente',
        nome_regra='ALH → ALHO',
        descricao='Mapeia o termo "ALH" para "ALHO"',
        aplicacao_texto='ALH → ALHO',
        criado_por=None
    )
```

---

### **PASSO 7: Regra é Salva no Banco de Dados**

A função `salvar_regra_aprendida` salva no SQLite:

```sql
INSERT INTO regras_aprendidas 
(tipo_regra, contexto, nome_regra, descricao, aplicacao_texto, ...)
VALUES 
('cliente_categoria', 'normalizacao_cliente', 'ALH → ALHO', 
 'Mapeia o termo "ALH" para "ALHO"', 'ALH → ALHO', ...)
```

**Resultado:**
- ✅ Regra salva com ID (ex: ID: 8)
- ✅ Agora está disponível para uso futuro

---

### **PASSO 8: Sistema Retorna Resposta para Você**

O sistema retorna:

```
✅ Regra aprendida salva: **ALH → ALHO** (ID: 8)
```

---

## 🎯 Resumo: Como a IA "Sabe"?

### **1. Descrição da Tool com Exemplos Explícitos**

A tool `salvar_regra_aprendida` tem na descrição:

```
"Exemplos: 
 2) 'o ALH vai ser alho' ou 'Diamond vai ser DMD' 
    → salva mapeamento cliente→categoria"
```

**Isso é como um "dicionário" para a IA:**
- Quando vê `"X vai ser Y"` → sabe que é mapeamento
- Quando vê `"ALH vai ser alho"` → reconhece o padrão

---

### **2. Instruções Explícitas na Descrição**

A descrição diz:

```
"Para mapeamentos cliente→categoria, SEMPRE use 
 tipo_regra='cliente_categoria' e 
 contexto='normalizacao_cliente'."
```

**Isso é como uma "receita":**
- A IA não precisa "adivinhar" os parâmetros
- Ela segue as instruções explícitas

---

### **3. Padrões Linguísticos**

A IA reconhece padrões como:
- `"X vai ser Y"` → mapeamento
- `"X será Y"` → mapeamento
- `"quando eu falar X, use Y"` → mapeamento

**Isso é "inteligência linguística":**
- A IA entende o significado, não apenas palavras
- Ela identifica a intenção do usuário

---

## 🔍 Exemplo Detalhado: O que a IA "Vê"

### **Input da IA:**

```
System Prompt:
  "Você é o mAIke, assistente especializado...
   Tools disponíveis:
   - salvar_regra_aprendida: Salva regras aprendidas. 
     Exemplos: 'o ALH vai ser alho' → salva mapeamento..."

User Prompt:
  "maike o ALH vai ser alho ok?"
```

### **Processo de Raciocínio da IA:**

```
1. Análise da mensagem:
   - "o ALH vai ser alho" → padrão de mapeamento detectado
   - "ok?" → confirmação/pergunta

2. Comparação com tools:
   - Tool "salvar_regra_aprendida" tem exemplo: "o ALH vai ser alho"
   - ✅ Match perfeito!

3. Extração de parâmetros:
   - ALH → termo origem
   - alho → termo destino
   - Formato: "ALH → ALHO" (normalizado)

4. Decisão:
   - Chamar salvar_regra_aprendida
   - Com tipo_regra='cliente_categoria'
   - Com contexto='normalizacao_cliente'
```

---

## 🎓 Analogia Simples

Imagine que você está ensinando uma criança a reconhecer animais:

1. **Você mostra exemplos:**
   - "Este é um cachorro" (apontando para um cachorro)
   - "Este é um gato" (apontando para um gato)

2. **A criança aprende o padrão:**
   - Quando vê algo peludo com 4 patas → pode ser cachorro ou gato
   - Compara com os exemplos que você mostrou

3. **A criança aplica:**
   - Vê um novo animal → compara com exemplos
   - Identifica: "Este é um cachorro!"

**No nosso caso:**
- **Exemplos na descrição da tool** = exemplos que você mostrou
- **Sua mensagem** = novo animal que a criança vê
- **IA reconhece o padrão** = criança identifica o animal
- **IA chama a tool** = criança diz "Este é um cachorro!"

---

## 🔧 Componentes Técnicos

### **1. Tool Definition** (`services/tool_definitions.py`)

```python
{
    "name": "salvar_regra_aprendida",
    "description": "... Exemplos: 'o ALH vai ser alho' ..."
}
```

**Função:** Define o que a tool faz e quando usar

---

### **2. System Prompt** (`services/prompt_builder.py`)

```python
system_prompt = """
Você é o mAIke...
📚 EXEMPLOS DE USO:
...
"""
```

**Função:** Instrui a IA sobre como pensar e agir

---

### **3. Tool Execution** (`services/chat_service.py`)

```python
elif nome_funcao == "salvar_regra_aprendida":
    resultado = salvar_regra_aprendida(...)
```

**Função:** Executa a tool quando a IA decide chamá-la

---

### **4. Database** (`services/learned_rules_service.py`)

```python
def salvar_regra_aprendida(...):
    # Salva no SQLite
    cursor.execute('INSERT INTO regras_aprendidas ...')
```

**Função:** Persiste a regra no banco de dados

---

## 🎯 Por Que Funciona?

### **1. Few-Shot Learning**

A IA aprende com exemplos:
- Exemplo na descrição: `"o ALH vai ser alho"`
- Sua mensagem: `"maike o ALH vai ser alho ok?"`
- IA reconhece: "Ah, isso é igual ao exemplo!"

---

### **2. Instruções Explícitas**

Não deixamos a IA "adivinhar":
- ✅ "SEMPRE use tipo_regra='cliente_categoria'"
- ✅ "SEMPRE use contexto='normalizacao_cliente'"
- ✅ Formato: "ALH → ALHO"

---

### **3. Padrões Linguísticos**

A IA entende significado, não apenas palavras:
- `"X vai ser Y"` → mapeamento
- `"X será Y"` → mapeamento
- `"quando falar X, use Y"` → mapeamento

---

## 📝 Outros Exemplos que Funcionam

### **Exemplo 1:**
```
Você: "maike Diamond vai ser DMD"
IA: Reconhece padrão "X vai ser Y"
IA: Compara com exemplo "Diamond vai ser DMD"
IA: Chama salvar_regra_aprendida
```

### **Exemplo 2:**
```
Você: "maike quando eu falar diamonds, use DMD"
IA: Reconhece padrão "quando falar X, use Y"
IA: Identifica como mapeamento
IA: Chama salvar_regra_aprendida
```

### **Exemplo 3:**
```
Você: "maike Bandimar será BND"
IA: Reconhece padrão "X será Y"
IA: Identifica como mapeamento
IA: Chama salvar_regra_aprendida
```

---

## 🎓 Conclusão

A IA não "adivinha" - ela:

1. **Compara** sua mensagem com exemplos na descrição da tool
2. **Reconhece** padrões linguísticos (`"X vai ser Y"`)
3. **Segue** instruções explícitas (tipo_regra, contexto)
4. **Extrai** informações da mensagem (ALH → ALHO)
5. **Chama** a tool apropriada com os parâmetros corretos

**É como um assistente bem treinado que:**
- Sabe o que fazer (descrição da tool)
- Tem exemplos claros (exemplos na descrição)
- Segue instruções (parâmetros obrigatórios)
- Entende linguagem natural (padrões linguísticos)

---

## 🔗 Arquivos Relacionados

- `services/tool_definitions.py` - Definição da tool
- `services/prompt_builder.py` - Montagem do prompt
- `services/chat_service.py` - Execução da tool
- `services/learned_rules_service.py` - Persistência no banco

