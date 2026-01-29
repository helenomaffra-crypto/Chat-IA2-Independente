# 🔍 Análise: Problema com Consultas "quais dmd foram registrados?" e "quais dmd está em análise?"

**Data:** 16/01/2026  
**Problema:** Consultas diretas não encontram processos que aparecem no dashboard

---

## 📊 Situação Observada

### **Dashboard "o que temos pra hoje?" - FUNCIONA ✅**

Mostra corretamente:
```
📋 DIs EM ANÁLISE (2 DI(s)):
• 2601093918 - Processo: DMD.0074/25 - Status: AGUARDANDO_PARAMETRIZACAO
• 2601092962 - Processo: DMD.0073/25 - Status: AGUARDANDO_PARAMETRIZACAO
```

### **Consultas Diretas - NÃO FUNCIONAM ❌**

**Pergunta 1:** "quais dmd foram registrados?"
- **Resposta:** "⚠️ Nenhum processo DMD com situação 'registrado' encontrado."
- **Problema:** IA está chamando `listar_processos_por_situacao(categoria='DMD', situacao='registrado')`
- **Causa:** "registrado" não é uma situação válida na função `listar_processos_por_categoria_e_situacao`

**Pergunta 2:** "quais dmd está em análise?"
- **Resposta:** "⚠️ Nenhum processo DMD com situação 'todas' encontrado."
- **Problema:** IA está chamando `listar_processos_por_situacao(categoria='DMD', situacao='todas')` ou algo incorreto
- **Causa:** "em análise" não é uma situação válida na função `listar_processos_por_categoria_e_situacao`

---

## 🔍 Análise Técnica

### **1. Como o Dashboard Funciona**

O dashboard usa funções específicas que **não são expostas como tools** para a IA:

```python
# services/agents/processo_agent.py - _obter_dashboard_hoje()
dis_analise = obter_dis_em_analise(categoria)  # ✅ Busca DIs em análise
duimps_analise = obter_duimps_em_analise(categoria)  # ✅ Busca DUIMPs em análise
```

**Função `obter_dis_em_analise()`:**
- Busca processos com DI registrada
- Filtra por status específicos (AGUARDANDO_PARAMETRIZACAO, INTERROMPIDA, etc.)
- Exclui DIs desembaraçadas ou com entrega autorizada
- **Retorna:** Lista de DIs em análise com status detalhado

**Função `obter_duimps_em_analise()`:**
- Busca DUIMPs com status: EM_ANALISE, AGUARDANDO_RESPOSTA, PENDENTE, rascunho
- **Retorna:** Lista de DUIMPs em análise

---

### **2. Como a IA Processa as Perguntas**

**Pergunta:** "quais dmd foram registrados?"

**Tool chamada:** `listar_processos_por_situacao(categoria='DMD', situacao='registrado')`

**Função `listar_processos_por_categoria_e_situacao()`:**
- Busca processos da categoria
- Filtra por situação de DI/DUIMP
- **Situações válidas:** "desembaracada", "di_desembaracada", "entregue", etc.
- **Situações NÃO válidas:** "registrado", "em análise", "todas"

**Problema:**
- A função não entende "registrado" como situação válida
- Ela busca por situações de DI/DUIMP (desembaracada, entregue, etc.)
- "Registrado" não é uma situação de DI/DUIMP - é um **estado** (tem DI/DUIMP registrada)

---

### **3. Mapeamento de Conceitos**

| Conceito do Usuário | O que Significa | Tool/Função Correta | Tool Atual (Incorreta) |
|---------------------|-----------------|---------------------|------------------------|
| "foram registrados" | Processos com DI/DUIMP registrada HOJE | `listar_processos_registrados_hoje(categoria='DMD')` | `listar_processos_por_situacao(situacao='registrado')` ❌ |
| "está em análise" | Processos com DI/DUIMP em análise (não desembaraçada) | `obter_dis_em_analise(categoria='DMD')` ou `obter_duimps_em_analise(categoria='DMD')` | `listar_processos_por_situacao(situacao='todas')` ❌ |
| "estão desembaraçados" | Processos com DI/DUIMP desembaraçada | `listar_processos_por_situacao(situacao='di_desembaracada')` ✅ | - |
| "estão entregues" | Processos com carga entregue | `listar_processos_por_situacao(situacao='entregue')` ✅ | - |

---

## 🎯 Soluções Possíveis

### **Opção 1: Melhorar Detecção de Intenção (RECOMENDADO)** ✅

**Problema:** IA não está interpretando corretamente as perguntas

**Solução:** Adicionar detecção proativa no `PrecheckService` ou `MessageIntentService`:

```python
# Detectar "foram registrados" → chamar listar_processos_registrados_hoje
if re.search(r'foram\s+registrados|foi\s+registrado|registramos', mensagem_lower):
    categoria = extrair_categoria(mensagem)
    return tool_call('listar_processos_registrados_hoje', {'categoria': categoria})

# Detectar "está em análise" → chamar obter_dis_em_analise + obter_duimps_em_analise
if re.search(r'est[áa]\s+em\s+an[áa]lise|em\s+an[áa]lise|an[áa]lise', mensagem_lower):
    categoria = extrair_categoria(mensagem)
    # Buscar DIs e DUIMPs em análise
    dis = obter_dis_em_analise(categoria)
    duimps = obter_duimps_em_analise(categoria)
    return formatar_resposta(dis, duimps)
```

**Vantagens:**
- ✅ Não quebra código existente
- ✅ Resolve o problema diretamente
- ✅ Usa as mesmas funções do dashboard (consistência)

**Desvantagens:**
- ⚠️ Adiciona mais lógica de detecção

---

### **Opção 2: Expor Funções como Tools** ✅

**Problema:** Funções `obter_dis_em_analise` e `obter_duimps_em_analise` não são tools

**Solução:** Criar tools específicas:

```python
# tool_definitions.py
{
    "name": "listar_dis_em_analise",
    "description": "Lista DIs em análise (registradas mas não desembaraçadas). Use quando usuário perguntar 'quais [CATEGORIA] está em análise?' ou 'quais DIs estão em análise?'",
    "parameters": {
        "categoria": {"type": "string", "description": "Categoria do processo (ex: DMD, ALH)"}
    }
}

{
    "name": "listar_duimps_em_analise",
    "description": "Lista DUIMPs em análise (rascunho, em análise, aguardando resposta). Use quando usuário perguntar 'quais [CATEGORIA] está em análise?' ou 'quais DUIMPs estão em análise?'",
    "parameters": {
        "categoria": {"type": "string", "description": "Categoria do processo (ex: DMD, ALH)"}
    }
}
```

**Vantagens:**
- ✅ IA pode chamar diretamente
- ✅ Consistente com outras tools
- ✅ Reutiliza funções existentes

**Desvantagens:**
- ⚠️ Precisa criar handlers nos agents
- ⚠️ Precisa atualizar documentação das tools

---

### **Opção 3: Melhorar Tool `listar_processos_por_situacao`** ⚠️

**Problema:** Tool não entende "registrado" e "em análise"

**Solução:** Adicionar mapeamento de situações:

```python
# Mapear "registrado" → buscar processos com DI/DUIMP registrada
# Mapear "em análise" → buscar processos com DI/DUIMP em análise
```

**Vantagens:**
- ✅ Usa tool existente

**Desvantagens:**
- ❌ Tool ficaria muito complexa
- ❌ Mistura conceitos diferentes (situação vs estado)
- ❌ Não recomendado

---

## 📋 Recomendação Final

### **Solução Híbrida (Opção 1 + Opção 2)** ✅

1. **Adicionar detecção proativa** para "foram registrados" → `listar_processos_registrados_hoje`
2. **Adicionar detecção proativa** para "está em análise" → `obter_dis_em_analise` + `obter_duimps_em_analise`
3. **Expor funções como tools** (opcional, para casos que não forem detectados)

**Ordem de Implementação:**
1. ✅ **Fase 1:** Adicionar detecção proativa (rápido, resolve 80% dos casos)
2. ⏳ **Fase 2:** Expor funções como tools (se necessário, para casos edge)

---

## 🔧 Implementação Sugerida (Fase 1)

### **Localização:** `services/precheck_service.py` ou `services/chat_service.py`

### **Detecção de "foram registrados":**

```python
# Padrões: "quais dmd foram registrados?", "quais processos foram registrados hoje?"
eh_pergunta_registrados = bool(
    re.search(r'foram\s+registrados|foi\s+registrado|registramos', mensagem_lower)
)

if eh_pergunta_registrados:
    categoria = extrair_categoria(mensagem)
    resultado = executar_tool('listar_processos_registrados_hoje', {
        'categoria': categoria,
        'limite': 200
    })
    return resultado
```

### **Detecção de "está em análise":**

```python
# Padrões: "quais dmd está em análise?", "quais processos estão em análise?"
eh_pergunta_em_analise = bool(
    re.search(r'est[áa]\s+em\s+an[áa]lise|em\s+an[áa]lise|an[áa]lise', mensagem_lower)
)

if eh_pergunta_em_analise:
    categoria = extrair_categoria(mensagem)
    # Buscar DIs e DUIMPs em análise (mesma lógica do dashboard)
    from db_manager import obter_dis_em_analise, obter_duimps_em_analise
    dis = obter_dis_em_analise(categoria)
    duimps = obter_duimps_em_analise(categoria)
    # Formatar resposta similar ao dashboard
    return formatar_resposta_dis_duimps_analise(dis, duimps, categoria)
```

---

## ✅ Checklist de Validação

Após implementar, testar:

- [ ] "quais dmd foram registrados?" → Retorna processos com DI/DUIMP registrada hoje
- [ ] "quais dmd está em análise?" → Retorna DIs e DUIMPs em análise
- [ ] "quais alh foram registrados?" → Funciona com outras categorias
- [ ] "quais processos estão em análise?" → Funciona sem categoria (todas)
- [ ] Dashboard continua funcionando normalmente
- [ ] Outras consultas não são afetadas

---

**Última atualização:** 16/01/2026
