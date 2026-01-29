# 🎯 Estratégia de Migração dos Vetores de Legislação

**Data:** 07/01/2026  
**Status:** 📋 **PLANEJAMENTO** - Preparação para migração em 08/2026

---

## ❓ PERGUNTA: Os Vetores Perdem Utilidade?

### Resposta Curta: **DEPENDE!**

- ❌ **Vector Stores da OpenAI (Assistants API)**: Sim, perderão utilidade quando Assistants API parar (26/08/2026), **SE** Responses API não suportar eles
- ✅ **Arquivos Originais**: NÃO perdem utilidade! Podem ser re-vetorizados
- ✅ **Preparação Antecipada**: Podemos migrar antes

---

## 📊 SITUAÇÃO ATUAL

### O que temos agora:

1. **Vector Store na OpenAI**
   - ID: `VECTOR_STORE_ID_LEGISLACAO` (salvo no `.env`)
   - Arquivos de legislação vetorizados e armazenados na OpenAI
   - Usado pelo Assistants API para File Search/RAG

2. **Arquivos Originais**
   - Armazenados em `legislacao_files/` (local)
   - Pode exportar do banco usando `exportar_legislacao_para_arquivo()`
   - Formato: arquivos `.txt` com texto completo das legislações

3. **Banco de Dados Local**
   - SQLite: `chat_ia.db`
   - Tabela `legislacao`: metadados das legislações
   - Tabela `legislacao_trecho`: trechos parseados (artigos, parágrafos, etc.)

---

## 🎯 CENÁRIOS POSSÍVEIS (26/08/2026)

### ✅ CENÁRIO 1: Responses API Ganha File Search (Melhor Caso)

**O que acontece:**
- OpenAI adiciona suporte a File Search na Responses API
- Vector Stores podem ser migrados ou reutilizados
- **Vetores continuam funcionando!**

**O que fazer:**
1. Migrar código para usar Responses API com File Search
2. Associar Vector Store existente à Responses API
3. **Nenhuma perda de dados**

**Probabilidade:** 🔵 **Média-Alta** (OpenAI está trabalhando nisso)

---

### ⚠️ CENÁRIO 2: Responses API NÃO Ganha File Search (Pior Caso)

**O que acontece:**
- Vector Stores da Assistants API ficam inacessíveis
- Responses API não tem File Search ainda
- **Vetores perdem utilidade temporariamente**

**O que fazer:**
1. ✅ **MANTER arquivos originais** (em `legislacao_files/`)
2. ✅ **MANTER banco de dados local** (SQLite)
3. ✅ Usar busca local (SQLite) como fallback
4. ⏳ **Aguardar** Responses API ganhar File Search
5. 🔄 Quando ganhar, **re-vetorizar** os arquivos

**Probabilidade:** 🔴 **Baixa** (OpenAI provavelmente vai adicionar)

---

### 🔄 CENÁRIO 3: Migração Manual dos Vector Stores

**O que acontece:**
- OpenAI permite exportar vector stores antes do desligamento
- Podemos fazer backup dos embeddings

**O que fazer:**
1. Exportar vector stores antes de 08/2026
2. Fazer backup dos arquivos
3. Quando Responses API ganhar File Search, re-importar

**Probabilidade:** 🟡 **Média** (pode ser possível)

---

## ✅ ESTRATÉGIA RECOMENDADA (Preparação Antecipada)

### Fase 1: Preparação (Até Julho 2026)

1. **✅ MANTER arquivos originais atualizados**
   ```bash
   # Exportar todas as legislações regularmente
   python -c "from services.assistants_service import get_assistants_service; \
              service = get_assistants_service(); \
              service.exportar_todas_legislacoes()"
   ```

2. **✅ FAZER BACKUP do Vector Store**
   - Anotar `VECTOR_STORE_ID_LEGISLACAO`
   - Listar arquivos no vector store
   - Documentar estrutura

3. **✅ MONITORAR atualizações da Responses API**
   - Verificar se File Search está disponível
   - Testar quando estiver disponível

### Fase 2: Migração (Julho-Agosto 2026)

1. **Testar Responses API com File Search** (quando disponível)
   ```python
   # Se Responses API tiver File Search:
   # - Criar novo vector store na Responses API
   # - Re-importar arquivos de legislação
   # - Migrar código para usar Responses API
   ```

2. **Migrar código gradualmente**
   - Manter Assistants API até último momento (26/08/2026)
   - Testar Responses API em paralelo
   - Fazer switch quando estiver pronto

### Fase 3: Pós-Migração (Após 26/08/2026)

1. **Desativar Assistants API**
   - Remover código legacy
   - Limpar configurações antigas

2. **Monitorar performance**
   - Verificar se busca ainda funciona bem
   - Ajustar se necessário

---

## 🔧 FERRAMENTAS PARA PREPARAÇÃO

### 1. Exportar Legislações para Arquivos

```python
from services.assistants_service import get_assistants_service

service = get_assistants_service()
arquivos = service.exportar_todas_legislacoes()
print(f"✅ Exportadas {len(arquivos)} legislações para arquivos locais")
```

**Localização:** `legislacao_files/`

### 2. Listar Arquivos no Vector Store

```python
from services.assistants_service import get_assistants_service
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv('DUIMP_AI_API_KEY'))
vector_store_id = os.getenv('VECTOR_STORE_ID_LEGISLACAO')

# Listar arquivos no vector store
try:
    files = client.vector_stores.files.list(vector_store_id=vector_store_id)
    print(f"✅ Vector Store tem {len(files.data)} arquivo(s)")
    for file in files.data:
        print(f"  - {file.id}")
except AttributeError:
    # Fallback para beta
    files = client.beta.vector_stores.files.list(vector_store_id=vector_store_id)
    print(f"✅ Vector Store tem {len(files.data)} arquivo(s)")
```

### 3. Verificar Status da Responses API

```python
from services.responses_service import get_responses_service

service = get_responses_service()
# Verificar se File Search está disponível
# (quando estiver, será adicionado aqui)
```

---

## 📋 CHECKLIST DE PREPARAÇÃO

### ✅ Antes de 26/08/2026:

- [ ] Exportar todas as legislações para arquivos locais (`legislacao_files/`)
- [ ] Fazer backup do banco de dados SQLite (`chat_ia.db`)
- [ ] Documentar `VECTOR_STORE_ID_LEGISLACAO` e `ASSISTANT_ID_LEGISLACAO`
- [ ] Listar todos os arquivos no vector store
- [ ] Monitorar atualizações da Responses API
- [ ] Testar Responses API quando File Search estiver disponível
- [ ] Preparar script de migração

### ⏳ Durante Migração (Julho-Agosto 2026):

- [ ] Testar Responses API com File Search
- [ ] Re-vetorizar arquivos na Responses API (se necessário)
- [ ] Migrar código gradualmente
- [ ] Testar busca de legislação
- [ ] Validar resultados

### ✅ Após Migração (Após 26/08/2026):

- [ ] Remover código do Assistants API
- [ ] Atualizar documentação
- [ ] Monitorar performance
- [ ] Ajustar se necessário

---

## 🚨 PLANO DE CONTINGÊNCIA

### Se Responses API NÃO ganhar File Search até 26/08/2026:

1. **Usar busca local (SQLite)** como solução temporária
   - Já implementado em `_buscar_em_todas_legislacoes()`
   - Busca por palavras-chave nos trechos
   - Menos "inteligente" mas funcional

2. **Usar Responses API sem File Search**
   - Apenas conhecimento do modelo GPT-4o
   - Não usa legislações importadas
   - Fallback para busca local quando necessário

3. **Aguardar File Search na Responses API**
   - Quando estiver disponível, re-vetorizar
   - Migrar para usar File Search

---

## 💡 CONCLUSÃO

### **Os vetores NÃO perdem utilidade completamente:**

1. ✅ **Arquivos originais estão seguros** (em `legislacao_files/`)
2. ✅ **Banco de dados local está seguro** (SQLite)
3. ✅ **Podemos re-vetorizar** quando necessário
4. ✅ **Busca local funciona** como fallback

### **Estratégia:**
- 🔵 **Cenário mais provável:** Responses API ganha File Search antes de 08/2026
- ✅ **Preparação:** Manter arquivos atualizados e fazer backup
- 🔄 **Migração:** Quando File Search estiver disponível na Responses API

### **Recomendação:**
- ✅ **Usar Assistants API até 08/2026** (funciona e tem File Search)
- ✅ **Preparar migração** gradualmente (julho-agosto 2026)
- ✅ **Manter arquivos locais** sempre atualizados (backup)

---

## 📚 RECURSOS

- **Vector Stores API:** https://platform.openai.com/docs/assistants/tools/file-search
- **Responses API:** https://platform.openai.com/docs/api-reference/responses
- **Migração Assistants → Responses:** `docs/MIGRACAO_ASSISTANTS_PARA_RESPONSES_API.md`

---

**Última atualização:** 07/01/2026  
**Status:** ✅ **PREPARAÇÃO ATIVA** - Monitorando atualizações da Responses API
