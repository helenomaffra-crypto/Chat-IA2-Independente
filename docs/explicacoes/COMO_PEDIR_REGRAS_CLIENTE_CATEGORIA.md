# 💬 Como Pedir Regras de Mapeamento Cliente → Categoria

## 🎯 Resumo: Formas que Funcionam vs. Não Funcionam

### ✅ **FORMAS QUE FUNCIONAM BEM:**

1. **"maike o ALH vai ser alho ok?"**
   - ✅ Padrão claro: "X vai ser Y"
   - ✅ IA reconhece como mapeamento
   - ✅ Cria com `tipo_regra='cliente_categoria'`

2. **"maike Diamond vai ser DMD"**
   - ✅ Padrão direto: "X vai ser Y"
   - ✅ IA reconhece como mapeamento
   - ✅ Cria com tipo correto

3. **"maike quando eu falar alho, use ALH"**
   - ✅ Padrão claro: "quando falar X, use Y"
   - ✅ IA entende como mapeamento
   - ✅ Cria com tipo correto

4. **"maike alho será ALH"**
   - ✅ Padrão: "X será Y"
   - ✅ IA reconhece como mapeamento
   - ✅ Cria com tipo correto

---

### ❌ **FORMAS QUE PODEM NÃO FUNCIONAR:**

1. **"maike coloca como regra que o alh tambem pode ser chamado de alho"**
   - ❌ Muito verboso
   - ❌ IA pode interpretar como "preferência do usuário"
   - ❌ Pode criar com `tipo_regra='preferencia_usuario'` (errado!)

2. **"maike lembre que ALH também é conhecido como alho"**
   - ❌ Linguagem muito natural/descritiva
   - ❌ IA pode não reconhecer como mapeamento
   - ❌ Pode criar com tipo genérico

3. **"maike quando mencionar alho, entenda que é ALH"**
   - ⚠️ Pode funcionar, mas menos claro
   - ⚠️ IA pode interpretar como preferência

---

## 🔍 Por Que Algumas Formas Funcionam Melhor?

### **1. Padrões Explícitos na Descrição da Tool**

A tool `salvar_regra_aprendida` tem na descrição:

```
"Exemplos: 
 2) 'o ALH vai ser alho' ou 'Diamond vai ser DMD' 
    → salva mapeamento cliente→categoria"
```

**O que isso significa:**
- A IA compara sua mensagem com os exemplos
- Se sua mensagem for **similar** aos exemplos → cria com tipo correto
- Se sua mensagem for **diferente** → pode criar com tipo errado

---

### **2. Padrões Linguísticos que a IA Reconhece**

A IA reconhece melhor padrões como:

✅ **"X vai ser Y"**
- "ALH vai ser alho"
- "Diamond vai ser DMD"

✅ **"X será Y"**
- "alho será ALH"
- "Bandimar será BND"

✅ **"quando falar X, use Y"**
- "quando falar alho, use ALH"
- "quando falar Diamond, use DMD"

✅ **"X = Y"** ou **"X → Y"**
- "alho = ALH"
- "Diamond → DMD"

---

### **3. Por Que "coloca como regra que..." Não Funciona Bem?**

**Sua mensagem original:**
```
"maike coloca como regra que o alh tambem pode ser chamado de alho"
```

**O que a IA "vê":**
- "coloca como regra" → genérico (pode ser qualquer tipo de regra)
- "tambem pode ser chamado" → descritivo, não mapeamento direto
- Não segue o padrão "X vai ser Y"

**O que a IA faz:**
- Compara com exemplos na tool
- Não encontra padrão similar a "o ALH vai ser alho"
- Interpreta como "preferência do usuário" (tipo genérico)
- Cria com `tipo_regra='preferencia_usuario'` ❌

---

## 📝 Formas Recomendadas (Do Melhor para o Menos Bom)

### **🥇 MELHOR: Padrão "X vai ser Y"**

```
"maike o ALH vai ser alho ok?"
"maike Diamond vai ser DMD"
"maike Bandimar vai ser BND"
```

**Por quê?**
- ✅ Idêntico ao exemplo na descrição da tool
- ✅ Padrão claro e direto
- ✅ IA reconhece imediatamente

---

### **🥈 BOM: Padrão "quando falar X, use Y"**

```
"maike quando eu falar alho, use ALH"
"maike quando falar Diamond, use DMD"
"maike quando mencionar Bandimar, use BND"
```

**Por quê?**
- ✅ Padrão claro de mapeamento
- ✅ IA entende a intenção
- ⚠️ Pode precisar de mais contexto

---

### **🥉 ACEITÁVEL: Padrão "X será Y"**

```
"maike alho será ALH"
"maike Diamond será DMD"
```

**Por quê?**
- ✅ Similar ao padrão "vai ser"
- ✅ IA reconhece como mapeamento
- ⚠️ Menos comum nos exemplos

---

### **⚠️ EVITAR: Linguagem Muito Natural**

```
❌ "maike coloca como regra que o alh tambem pode ser chamado de alho"
❌ "maike lembre que ALH também é conhecido como alho"
❌ "maike quando mencionar alho, entenda que é ALH"
```

**Por quê?**
- ❌ Muito verboso
- ❌ Não segue padrões explícitos
- ❌ IA pode interpretar como preferência genérica
- ❌ Pode criar com tipo errado

---

## 🎓 Exemplos Práticos

### **Exemplo 1: Funciona Perfeitamente**

**Você:** "maike o ALH vai ser alho ok?"

**O que a IA faz:**
1. Compara com exemplos: "o ALH vai ser alho" ✅ Match perfeito!
2. Reconhece padrão: "X vai ser Y" ✅
3. Identifica como mapeamento cliente→categoria ✅
4. Cria regra com:
   - `tipo_regra='cliente_categoria'` ✅
   - `contexto='normalizacao_cliente'` ✅
   - `nome_regra='ALH → ALHO'` ✅

**Resultado:** ✅ Funciona perfeitamente!

---

### **Exemplo 2: Funciona, Mas Menos Claro**

**Você:** "maike quando eu falar alho, use ALH"

**O que a IA faz:**
1. Compara com exemplos: Não é idêntico, mas similar
2. Reconhece padrão: "quando falar X, use Y" ✅
3. Identifica como mapeamento ✅
4. Cria regra com tipo correto ✅

**Resultado:** ✅ Funciona, mas pode precisar de mais contexto

---

### **Exemplo 3: Pode Não Funcionar**

**Você:** "maike coloca como regra que o alh tambem pode ser chamado de alho"

**O que a IA faz:**
1. Compara com exemplos: Não encontra padrão similar ❌
2. Não reconhece padrão claro de mapeamento ❌
3. Interpreta como "preferência do usuário" ❌
4. Cria regra com:
   - `tipo_regra='preferencia_usuario'` ❌
   - `contexto='filtros_gerais'` ❌

**Resultado:** ❌ Não funciona na normalização!

---

## 💡 Dica: Use Frases Curtas e Diretas

### **✅ BOM:**
- "maike o ALH vai ser alho ok?"
- "maike Diamond vai ser DMD"
- "maike alho será ALH"

### **❌ EVITAR:**
- "maike coloca como regra que..."
- "maike lembre que..."
- "maike quando mencionar... entenda que..."

---

## 🔧 Como a IA Decide o Tipo?

A IA analisa:

1. **Padrão da mensagem:**
   - "X vai ser Y" → mapeamento ✅
   - "quando falar X, use Y" → mapeamento ✅
   - "coloca como regra que..." → genérico ❌

2. **Comparação com exemplos:**
   - Similar aos exemplos → tipo correto ✅
   - Diferente dos exemplos → tipo genérico ❌

3. **Instruções na descrição:**
   - "Para mapeamentos cliente→categoria, SEMPRE use tipo_regra='cliente_categoria'"
   - Mas só funciona se a IA reconhecer como mapeamento!

---

## 📋 Checklist: Como Pedir Corretamente

### ✅ **Use:**
- [ ] Frases curtas e diretas
- [ ] Padrão "X vai ser Y" ou "X será Y"
- [ ] Padrão "quando falar X, use Y"
- [ ] Nomes claros (ALH, DMD, BND, etc.)

### ❌ **Evite:**
- [ ] Frases muito verbosas
- [ ] "coloca como regra que..."
- [ ] "lembre que..."
- [ ] "também pode ser chamado de..."

---

## 🎯 Resumo Final

**Para criar regras de mapeamento cliente→categoria, use:**

```
"maike o [TERMO] vai ser [CATEGORIA] ok?"
```

**Exemplos:**
- "maike o ALH vai ser alho ok?"
- "maike Diamond vai ser DMD"
- "maike Bandimar vai ser BND"

**Por quê?**
- ✅ Padrão idêntico aos exemplos na tool
- ✅ IA reconhece imediatamente
- ✅ Cria com tipo e contexto corretos
- ✅ Funciona na normalização de termos

---

## 🔗 Referências

- `services/tool_definitions.py` - Descrição da tool `salvar_regra_aprendida`
- `services/precheck_service.py` - Normalização de termos
- `docs/COMO_IA_DETECTA_MAPEAMENTO.md` - Como a IA detecta mapeamentos

