# ⚠️ Situação: Legislações Vetorizadas e Migração para Responses API

**Data:** 07/01/2026  
**Status:** ✅ **COMPREENDIDO** - Migração proposital, mas podemos usar Assistants API até 08/2026

---

## 🎯 SITUAÇÃO ATUAL

O sistema está usando **Responses API** (que **NÃO tem File Search/RAG ainda**) ao invés de **Assistants API** (que **TEM File Search** e as legislações **ESTÃO vetorizadas**).

### ⚠️ IMPORTANTE: Migração foi PROPOSITAL

**A mudança para Responses API foi intencional** porque:
- ✅ **Assistants API será desligado em 26/08/2026** (7 meses ainda)
- ✅ **Responses API é a nova API recomendada** pela OpenAI
- ✅ **Preparação para o futuro** (quando Responses API tiver File Search)

**MAS:**
- ⚠️ **Assistants API ainda funciona até 08/2026** (7 meses!)
- ⚠️ **Responses API ainda não tem File Search/RAG**
- ⚠️ **Legislações vetorizadas não estão sendo usadas**

### O que está acontecendo:

1. **As legislações ESTÃO vetorizadas** ✅
   - Script `scripts/configurar_assistants_legislacao.py` cria vector stores
   - Arquivos estão no Vector Store da OpenAI
   - IDs salvos no `.env`: `ASSISTANT_ID_LEGISLACAO` e `VECTOR_STORE_ID_LEGISLACAO`

2. **MAS o código está usando Responses API** ❌
   - `legislacao_agent.py` → `_buscar_legislacao_responses()` (usado por padrão)
   - Responses API **NÃO tem File Search/RAG ainda**
   - Então busca apenas no conhecimento do modelo GPT-4o (não nas legislações vetorizadas)

3. **Assistants API está disponível mas não usado** ⚠️
   - `_buscar_legislacao_assistants()` existe mas está marcado como DEPRECATED
   - Este método **TEM File Search** e acessa as legislações vetorizadas

---

## 🔍 ONDE ESTÁ O PROBLEMA

### Arquivo: `services/agents/legislacao_agent.py`

**Linha ~591:** `_buscar_legislacao_responses()` está sendo usado por padrão
```python
def _buscar_legislacao_responses(self, arguments: Dict[str, Any], ...):
    """
    Busca legislação usando Responses API (nova API recomendada).
    ⚠️ PROBLEMA: Responses API NÃO tem File Search ainda!
    """
```

**Linha ~663:** `_buscar_legislacao_assistants()` existe mas está marcado como DEPRECATED
```python
def _buscar_legislacao_assistants(self, arguments: Dict[str, Any], ...):
    """
    Busca legislação usando Assistants API (DEPRECATED - será desligado em 08/2026).
    ⚠️ MAS: Assistants API TEM File Search e acessa legislações vetorizadas!
    """
```

---

## ✅ SOLUÇÃO RECOMENDADA

### Usar Assistants API enquanto disponível (TEM File Search)

**Prioridade:** Assistants API (até 08/2026) → Responses API (fallback) → Busca Local

**Estratégia:**
1. ✅ **Usar Assistants API primeiro** (se configurado e disponível)
   - TEM File Search/RAG ✅
   - Legislações vetorizadas são usadas ✅
   - Funciona até 26/08/2026 ✅

2. ⚠️ **Fallback para Responses API** (se Assistants API não disponível)
   - NÃO tem File Search ainda ❌
   - Usa apenas conhecimento do modelo GPT-4o

3. 🔄 **Migrar para Responses API** quando tiver File Search (futuro)

```python
def _buscar_legislacao_responses(self, arguments: Dict[str, Any], ...):
    """
    Busca legislação usando Assistants API (com File Search) ou Responses API (fallback).
    """
    # 1. TENTAR Assistants API primeiro (TEM File Search)
    assistants_service = get_assistants_service()
    if assistants_service.enabled and assistants_service.assistant_id:
        resultado = assistants_service.buscar_legislacao(pergunta)
        if resultado and resultado.get('sucesso'):
            return {
                'sucesso': True,
                'resposta': resultado.get('resposta'),
                'metodo': 'assistants_api_file_search',  # ✅ USA LEGISLAÇÕES VETORIZADAS
                ...
            }
    
    # 2. FALLBACK: Responses API (NÃO tem File Search)
    responses_service = get_responses_service()
    if responses_service.enabled:
        # ... código atual
```

### Opção 2: Verificar se Vector Store está configurado

**Antes de usar Responses API, verificar se Assistants API está disponível:**

```python
# Verificar se Assistants API está configurado
assistants_service = get_assistants_service()
if assistants_service.enabled and assistants_service.vector_store_id:
    # ✅ TEM VETORIZAÇÃO - usar Assistants API
    return self._buscar_legislacao_assistants(arguments, context)
else:
    # ❌ NÃO TEM VETORIZAÇÃO - usar Responses API
    return self._buscar_legislacao_responses(arguments, context)
```

---

## 🔧 COMO VERIFICAR SE ESTÁ CONFIGURADO

### Verificar `.env`:

```bash
# Verificar se tem:
ASSISTANT_ID_LEGISLACAO=asst_...
VECTOR_STORE_ID_LEGISLACAO=vs_...
```

### Verificar se vector store tem arquivos:

```python
from services.assistants_service import get_assistants_service

service = get_assistants_service()
if service.enabled and service.vector_store_id:
    # Listar arquivos no vector store
    arquivos = service.listar_arquivos_vector_store(service.vector_store_id)
    print(f"✅ Vector Store tem {len(arquivos)} arquivo(s)")
```

---

## 📋 CHECKLIST DE CORREÇÃO

- [ ] Verificar se `ASSISTANT_ID_LEGISLACAO` está no `.env`
- [ ] Verificar se `VECTOR_STORE_ID_LEGISLACAO` está no `.env`
- [ ] Verificar se vector store tem arquivos de legislação
- [ ] Modificar `legislacao_agent.py` para usar Assistants API primeiro
- [ ] Testar busca de legislação (deve usar File Search)
- [ ] Verificar se resposta menciona "Assistants API com File Search"

---

## 🚨 URGÊNCIA

**Status:** 🔴 **URGENTE** - As legislações estão vetorizadas mas não estão sendo usadas!

**Impacto:**
- ❌ Buscas de legislação não usam arquivos importados
- ❌ Apenas conhecimento do modelo GPT-4o (pode estar desatualizado)
- ❌ Não aproveita vetorização já feita

**Solução:**
- ✅ Modificar para usar Assistants API quando disponível
- ✅ Manter Responses API como fallback

---

## 📝 NOTAS IMPORTANTES

- ✅ **Assistants API ainda funciona até 26/08/2026** (7 meses ainda!)
- ✅ **File Search está funcionando** no Assistants API
- ❌ **Responses API ainda não tem File Search** (futuro)
- ✅ **Migração foi proposital** (preparação para 08/2026)
- 🔄 **Solução híbrida:** Usar Assistants API enquanto disponível, depois migrar para Responses API quando tiver File Search

---

**Última atualização:** 07/01/2026  
**Status:** ✅ **COMPREENDIDO** - Solução híbrida recomendada

