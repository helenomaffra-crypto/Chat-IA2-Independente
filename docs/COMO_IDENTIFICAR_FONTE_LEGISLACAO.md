# 🔍 Como Identificar Qual Fonte Está Sendo Usada

**Data:** 05/01/2026

---

## 📊 Fontes Disponíveis

O sistema usa **3 fontes diferentes** para buscar legislação:

1. **Responses API** (Nova API - Recomendada)
2. **Assistants API** (Legado - Deprecated)
3. **Busca Local (SQLite)** (Fallback)

---

## 🔍 Como Identificar a Fonte na Resposta

### **1. Responses API (Nova API)**

**Indicadores visuais:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **FONTE: Responses API (Nova API da OpenAI)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Resposta da IA]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Fonte:** Busca realizada via **Responses API** (modelo: gpt-4o)
💡 Esta resposta usa o conhecimento do modelo GPT-4o sobre legislação brasileira.
⚠️ **Nota:** File Search/RAG ainda não está totalmente disponível na Responses API.
   Quando disponível, a busca incluirá os arquivos de legislação importados.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Características:**
- ✅ Indicador no **início** e no **final** da resposta
- ✅ Menção explícita: "Responses API"
- ✅ Modelo usado: gpt-4o
- ✅ Resposta contextualizada e explicativa

**Quando é usada:**
- Perguntas conceituais (ex: "O que fala sobre perdimento?")
- Quando a IA decide usar a tool `buscar_legislacao_responses`

---

### **2. Assistants API (Legado - Deprecated)**

**Indicadores visuais:**
```
[Resposta da IA]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Fonte:** Busca realizada via **Assistants API com File Search (RAG)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 Esta busca usa inteligência semântica (RAG) em todas as legislações importadas.
⚠️ **Nota:** Assistants API será desligado em 26/08/2026. Migração para Responses API em andamento.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Características:**
- ✅ Indicador no **final** da resposta
- ✅ Menção explícita: "Assistants API com File Search (RAG)"
- ✅ Usa arquivos de legislação importados (Vector Store)
- ⚠️ **Deprecated** - será desligado em 08/2026

**Quando é usada:**
- Quando a IA decide usar a tool `buscar_legislacao_assistants`
- Quando Responses API não está disponível (fallback)

---

### **3. Busca Local (SQLite)**

**Indicadores visuais:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **FONTE: Busca Local (SQLite)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 **Termos buscados:** multas, importação
📚 **Legislacoes encontradas:** 2
📄 **Total de trechos:** 45

[Trechos encontrados...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Fonte:** Busca Local (SQLite) - 45 trecho(s) encontrado(s)
💡 Esta busca usa palavras-chave exatas no banco local.
⚠️ Para perguntas conceituais, use buscar_legislacao_responses (RAG semântico).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Características:**
- ✅ Indicador no **início** e no **final** da resposta
- ✅ Mostra estatísticas (termos buscados, legislações encontradas, total de trechos)
- ✅ Lista trechos específicos encontrados
- ✅ Busca por palavras-chave exatas (não semântica)

**Quando é usada:**
- Quando usuário menciona legislação específica (ex: "IN 680")
- Quando usuário pede artigo específico (ex: "art 725")
- Como fallback quando Responses/Assistants API não estão disponíveis

---

## 🔍 Como Verificar nos Logs

### **1. Verificar qual tool foi chamada**

Nos logs do servidor, procure por:
```
✅ Tool calls detectados: 1 chamada(s)
🔄 Roteando tool 'buscar_legislacao_responses' para agent 'legislacao'
```

### **2. Verificar qual método foi usado**

Nos logs, procure por:
```
📤 Buscando legislação via Responses API: ...
✅ Resposta recebida via Responses API (1823 caracteres)
```

ou

```
📤 Buscando legislação via Assistants API: ...
✅ Resposta recebida via Assistants API
```

ou

```
🔍 Busca em todas as legislações (SQLite local)
```

---

## 🎯 Resumo: Como Identificar

| Fonte | Indicador no Início | Indicador no Final | Estatísticas | Características |
|-------|-------------------|-------------------|--------------|----------------|
| **Responses API** | ✅ Sim | ✅ Sim | ❌ Não | Resposta contextualizada, modelo GPT-4o |
| **Assistants API** | ❌ Não | ✅ Sim | ❌ Não | RAG com arquivos importados, deprecated |
| **SQLite Local** | ✅ Sim | ✅ Sim | ✅ Sim | Lista de trechos, palavras-chave exatas |

---

## ⚠️ Casos Especiais

### **IA Responde Diretamente (Sem Tool)**

Se a IA responder diretamente sem usar tools, **não haverá indicador de fonte**.

**Como identificar:**
- Resposta não tem indicadores de fonte
- Resposta é mais genérica/conceitual
- Não menciona legislações específicas

**O que fazer:**
- Verificar logs para ver se tool foi chamada
- Se não foi chamada, a IA está usando apenas seu conhecimento base

---

## 💡 Dicas

1. **Sempre verifique o início e o final da resposta** - os indicadores estão lá
2. **Se não houver indicador**, a IA respondeu diretamente (sem tool)
3. **Verifique os logs** para confirmação técnica
4. **Responses API** é a fonte recomendada (nova API)
5. **SQLite Local** mostra estatísticas detalhadas

---

**Última atualização:** 05/01/2026





