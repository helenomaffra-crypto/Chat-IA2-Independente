# 🔄 Migração: Assistants API → Responses API

**Data:** 05/01/2026  
**Status:** ✅ **RECOMENDADO MIGRAR AGORA** (projeto ainda não está em produção)

---

## 📊 Comparação: Assistants API vs Responses API

### **Assistants API (Atual - Deprecated)**

**Como funciona:**
```python
# 1. Criar assistente
assistant = client.beta.assistants.create(
    name="mAIke Legislação",
    instructions="...",
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vs_id]}}
)

# 2. Criar thread
thread = client.beta.threads.create()

# 3. Adicionar mensagem
client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="O que fala sobre perdimento?"
)

# 4. Criar run
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# 5. Aguardar conclusão
while run.status != "completed":
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

# 6. Buscar mensagens
messages = client.beta.threads.messages.list(thread_id=thread.id)
```

**Características:**
- ✅ Threads persistentes (histórico automático)
- ✅ File Search (RAG) integrado
- ✅ Code Interpreter como tool
- ❌ **Deprecated** - Desligamento: 26/08/2026
- ❌ Fluxo mais complexo (threads, runs, messages)
- ❌ Mais verboso (múltiplas chamadas)

---

### **Responses API (Nova - Recomendada)**

**Como funciona:**
```python
# 1. Chamada direta (tudo em uma requisição)
resp = client.responses.create(
    model="gpt-4o",
    tools=[{
        "type": "code_interpreter",
        "container": {"type": "auto", "memory_limit": "4g"}
    }],
    instructions="Você é um assistente especializado em legislação...",
    input="O que fala sobre perdimento em importação?"
)

# 2. Resposta direta
print(resp.output_text)
```

**Características:**
- ✅ **API mais simples** (uma chamada vs múltiplas)
- ✅ **Melhor performance** (menos overhead)
- ✅ Code Interpreter como tool
- ✅ File Search (quando disponível)
- ✅ **API ativa e suportada**
- ⚠️ Gerenciamento de histórico manual (se necessário)

---

## 🔍 Diferenças Principais

| Aspecto | Assistants API | Responses API |
|---------|---------------|---------------|
| **Complexidade** | ⚠️ Alta (threads, runs, messages) | ✅ Baixa (uma chamada) |
| **Performance** | ⚠️ Múltiplas requisições | ✅ Requisição única |
| **Threads Persistentes** | ✅ Automático | ⚠️ Manual (se necessário) |
| **File Search/RAG** | ✅ Integrado | ✅ Integrado (quando disponível) |
| **Code Interpreter** | ✅ Tool | ✅ Tool |
| **Status** | ❌ Deprecated (08/2026) | ✅ Ativa e suportada |
| **Custo** | Mesmo (tokens + tools) | Mesmo (tokens + tools) |
| **Documentação** | ⚠️ Limitada (deprecated) | ✅ Completa e atualizada |

---

## ⚠️ Limitações Conhecidas

### **Responses API**

1. **File Search/RAG:**
   - ⚠️ Pode não estar totalmente disponível ainda
   - ⚠️ Sintaxe pode ser diferente de Assistants API
   - ✅ Mas está sendo desenvolvido ativamente

2. **Threads Persistentes:**
   - ⚠️ Não há threads automáticas
   - ✅ Mas você pode gerenciar histórico manualmente
   - ✅ Para mAIke, isso não é problema (já gerencia histórico no SQLite)

3. **Containers Explícitos:**
   - ⚠️ Pode não estar totalmente suportado na versão atual
   - ✅ Modo auto funciona perfeitamente
   - ✅ Para mAIke, modo auto é suficiente

### **Assistants API**

1. **Deprecated:**
   - ❌ Será desligado em 26/08/2026
   - ❌ Não receberá novas features
   - ❌ Documentação limitada

2. **Complexidade:**
   - ⚠️ Fluxo mais verboso
   - ⚠️ Mais pontos de falha

---

## 💡 Por Que Migrar Agora?

### ✅ **Vantagens de Migrar Agora (Antes de Produção)**

1. **Sem Dívida Técnica:**
   - ✅ Não precisa migrar depois quando estiver em produção
   - ✅ Evita retrabalho futuro
   - ✅ Código mais limpo desde o início

2. **API Mais Simples:**
   - ✅ Menos código para manter
   - ✅ Menos pontos de falha
   - ✅ Mais fácil de debugar

3. **Melhor Performance:**
   - ✅ Requisição única vs múltiplas
   - ✅ Menos latência
   - ✅ Menos overhead

4. **Suporte Ativo:**
   - ✅ Documentação completa
   - ✅ Novas features sendo adicionadas
   - ✅ Comunidade focada nesta API

5. **Projeto Não Está em Produção:**
   - ✅ Sem usuários afetados
   - ✅ Sem dados históricos para migrar
   - ✅ Tempo ideal para mudança

---

## 🚀 Plano de Migração

### **Fase 1: Preparação (1-2 dias)**

1. ✅ Criar `ResponsesService` (similar ao `AssistantsService`)
2. ✅ Implementar método `buscar_legislacao_responses()` 
3. ✅ Testar com dados reais

### **Fase 2: Implementação (2-3 dias)**

1. ✅ Substituir `AssistantsService` por `ResponsesService` em `legislacao_agent.py`
2. ✅ Atualizar tool `buscar_legislacao_assistants` → `buscar_legislacao_responses`
3. ✅ Testar busca de legislação

### **Fase 3: File Search (se necessário) (1-2 dias)**

1. ✅ Verificar se File Search está disponível na Responses API
2. ✅ Se sim, implementar upload de arquivos
3. ✅ Se não, manter busca local (SQLite) como fallback

### **Fase 4: Testes e Validação (1-2 dias)**

1. ✅ Testar todas as funcionalidades
2. ✅ Validar resultados
3. ✅ Documentar mudanças

**Total estimado: 5-9 dias**

---

## 📝 Implementação Sugerida

### **1. Criar ResponsesService**

```python
# services/responses_service.py
class ResponsesService:
    """Serviço para Responses API da OpenAI."""
    
    def buscar_legislacao(self, pergunta: str) -> Dict[str, Any]:
        """Busca legislação usando Responses API."""
        resp = self.client.responses.create(
            model="gpt-4o",
            tools=[{
                "type": "code_interpreter",  # Para cálculos se necessário
                "container": {"type": "auto", "memory_limit": "1g"}
            }],
            instructions="""Você é um assistente especializado em legislação brasileira de importação.
            Use os arquivos de legislação disponíveis para responder perguntas.
            Sempre cite as fontes.""",
            input=pergunta
        )
        return {
            'sucesso': True,
            'resposta': resp.output_text
        }
```

### **2. Atualizar LegislacaoAgent**

```python
# services/agents/legislacao_agent.py
def _buscar_legislacao_responses(self, arguments, context):
    """Busca legislação usando Responses API."""
    from ..responses_service import get_responses_service
    service = get_responses_service()
    return service.buscar_legislacao(arguments['pergunta'])
```

### **3. Atualizar Tool Definition**

```python
# services/tool_definitions.py
{
    "name": "buscar_legislacao_responses",  # Novo nome
    "description": "Busca legislação usando Responses API (RAG)..."
}
```

---

## ⚠️ Considerações Importantes

### **1. File Search na Responses API**

**Status atual:**
- ⚠️ Pode não estar totalmente disponível ainda
- ✅ Mas está sendo desenvolvido ativamente
- ✅ OpenAI está focando nesta API

**Solução:**
- ✅ Manter busca local (SQLite) como fallback
- ✅ Quando File Search estiver disponível, adicionar
- ✅ Transição gradual

### **2. Histórico de Conversas**

**Assistants API:**
- ✅ Threads persistentes automáticas

**Responses API:**
- ⚠️ Não há threads automáticas
- ✅ Mas mAIke já gerencia histórico no SQLite
- ✅ Não é problema para o sistema atual

### **3. Custo**

**Ambas as APIs:**
- ✅ Mesmo custo (tokens + tools)
- ✅ Code Interpreter: US$ 0,03/sessão
- ✅ File Search: Gratuito (upload), pode ter custo de uso

---

## 🎯 Recomendação Final

### ✅ **SIM, VALE A PENA MIGRAR AGORA**

**Razões:**
1. ✅ Projeto não está em produção
2. ✅ API mais simples e performática
3. ✅ Evita dívida técnica futura
4. ✅ Suporte ativo da OpenAI
5. ✅ Código mais limpo desde o início

**Riscos:**
- ⚠️ File Search pode não estar totalmente disponível
- ✅ Mas busca local (SQLite) funciona como fallback
- ✅ Quando File Search estiver disponível, adicionar é simples

**Tempo estimado:**
- ✅ 5-9 dias de trabalho
- ✅ Sem impacto em produção (não está em produção)

---

## 📋 Checklist de Migração

- [ ] Criar `ResponsesService`
- [ ] Implementar `buscar_legislacao_responses()`
- [ ] Testar com dados reais
- [ ] Atualizar `LegislacaoAgent`
- [ ] Atualizar tool definition
- [ ] Atualizar `ToolRouter`
- [ ] Testar todas as funcionalidades
- [ ] Documentar mudanças
- [ ] Remover `AssistantsService` (ou manter como fallback)
- [ ] Atualizar documentação

---

## 🔗 Referências

- [Responses API Documentation](https://platform.openai.com/docs/api-reference/responses)
- [Assistants API Migration Guide](https://platform.openai.com/docs/assistants/migration)
- [Code Interpreter Guide](https://platform.openai.com/docs/guides/code-interpreter)

---

**Última atualização:** 05/01/2026





