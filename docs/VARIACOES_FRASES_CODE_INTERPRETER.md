# Variações de Frases que Acionam Code Interpreter

## 🎯 Resposta Rápida

**NÃO**, você não precisa falar exatamente "explicando passo a passo". A IA entende várias formas de pedir explicação detalhada.

---

## 📝 Como a IA Decide Qual Tool Usar

A IA analisa a **descrição da tool** e compara com sua mensagem. Se detectar palavras-chave relacionadas a "explicação", "detalhamento", "fórmulas", etc., ela escolhe a tool do Code Interpreter.

### Descrição da Tool (o que a IA lê):

```
"Use esta função quando o usuário pedir para calcular algo COM explicação 
detalhada, passo a passo, ou mostrando fórmulas..."
```

### Palavras-chave que a IA detecta:

- ✅ "explicando"
- ✅ "explicar"
- ✅ "detalhado"
- ✅ "detalhamento"
- ✅ "passo a passo"
- ✅ "mostrando fórmulas"
- ✅ "mostrar fórmulas"
- ✅ "como chegou"
- ✅ "como calculou"
- ✅ "mostre o cálculo"
- ✅ "com explicação"
- ✅ "detalhe"
- ✅ "detalhar"

---

## 💬 Exemplos de Frases que Funcionam

### ✅ Acionam Code Interpreter (com explicação):

```
"calcule os impostos explicando passo a passo"
"calcule os impostos explicando"
"calcule os impostos com explicação"
"calcule os impostos mostrando as fórmulas"
"calcule os impostos detalhando cada etapa"
"quanto fica de imposto explicando como chegou nesse valor"
"calcule os impostos e mostre como calculou"
"calcule os impostos detalhado"
"calcule os impostos com detalhamento"
"calcule os impostos passo a passo"
"calcule os impostos mostrando o cálculo"
"calcule os impostos e explique"
"calcule os impostos detalhe"
```

### ❌ Acionam Python Local (sem explicação):

```
"calcule os impostos"
"quanto fica de imposto"
"calcular impostos para carga de 10.000 dólares"
"calcule II e IPI"
```

---

## 🧠 Como a IA Decide

A IA usa **semântica** (significado), não apenas palavras exatas. Ela entende que:

- "explicando" = "com explicação" = "detalhando" = "mostrando como"
- "fórmulas" = "cálculo" = "como chegou" = "passo a passo"

### Exemplo:

```
👤 "calcule os impostos e me mostre como você chegou nesse valor"

🤖 IA analisa:
   - "calcule os impostos" → detecta cálculo
   - "mostre como você chegou" → detecta explicação
   → Escolhe: calcular_com_code_interpreter ✅
```

---

## 📊 Tabela de Decisão

| Sua Frase | Tool Escolhida | Por quê? |
|-----------|----------------|----------|
| "calcule os impostos" | `calcular_impostos_ncm` | Sem palavra de explicação |
| "calcule os impostos explicando" | `calcular_com_code_interpreter` | Tem "explicando" |
| "calcule os impostos detalhado" | `calcular_com_code_interpreter` | Tem "detalhado" |
| "calcule os impostos mostrando fórmulas" | `calcular_com_code_interpreter` | Tem "mostrando fórmulas" |
| "quanto fica de imposto" | `calcular_impostos_ncm` | Sem explicação |
| "quanto fica de imposto explicando" | `calcular_com_code_interpreter` | Tem "explicando" |

---

## 🎯 Dica Prática

**Para acionar Code Interpreter, use qualquer uma dessas palavras:**

- "explicando"
- "explicar"
- "detalhado"
- "detalhar"
- "mostrando"
- "mostrar"
- "fórmulas"
- "passo a passo"
- "como chegou"
- "como calculou"

**Exemplos práticos:**

```
✅ "calcule os impostos explicando"
✅ "calcule os impostos detalhado"
✅ "calcule os impostos mostrando as fórmulas"
✅ "calcule os impostos passo a passo"
✅ "quanto fica de imposto explicando como chegou"
```

---

## 🔍 Teste Você Mesmo

Experimente estas variações:

1. **Sem explicação (rápido):**
   ```
   "calcule os impostos para carga de 10.000 dólares"
   → Usa Python local (rápido)
   ```

2. **Com explicação (Code Interpreter):**
   ```
   "calcule os impostos explicando para carga de 10.000 dólares"
   → Usa Code Interpreter (com explicação)
   ```

3. **Variações que funcionam:**
   ```
   "calcule os impostos detalhado"
   "calcule os impostos mostrando fórmulas"
   "calcule os impostos passo a passo"
   "calcule os impostos com explicação"
   → Todas usam Code Interpreter ✅
   ```

---

## 💡 Resumo

**Você NÃO precisa falar exatamente "explicando passo a passo".**

Qualquer frase que indique que você quer **explicação, detalhamento ou fórmulas** vai acionar o Code Interpreter automaticamente.

A IA é inteligente e entende o **significado** da sua mensagem, não apenas palavras exatas.



