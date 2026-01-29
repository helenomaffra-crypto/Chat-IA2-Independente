# 📋 O Que Falta para Finalizar o Passo 3.5

**Data:** 12/01/2026  
**Status:** 🔄 **FASE 3.5.1 COMPLETA** - Fase 3.5.2 pendente

---

## ✅ O Que Já Foi Feito (Fase 3.5.1)

### **Sub-etapas Completas:**
1. ✅ **Sub-etapa 1:** Construção de `saudacao_personalizada` e `regras_aprendidas` (~30 linhas)
2. ✅ **Sub-etapa 2:** Construção de `system_prompt` via PromptBuilder (~10 linhas)
3. ✅ **Sub-etapa 3:** Construção de `contexto_str` (processo, categoria, CE/CCT) (~200-300 linhas)
4. ✅ **Sub-etapa 4:** Construção de `historico_str` (~100-150 linhas)
5. ✅ **Sub-etapa 5:** Busca de `contexto_sessao` (~100 linhas)
6. ✅ **Sub-etapa 6:** Construção de `user_prompt` e modo legislação estrita (~200-300 linhas)

### **Resultado:**
- ✅ Método `construir_prompt_completo()` **100% implementado** no `MessageProcessingService`
- ✅ Todos os métodos auxiliares criados (`_construir_contexto_str`, `_construir_historico_str`, `_buscar_contexto_sessao`, `_construir_user_prompt`)
- ✅ Testes automatizados criados e **passando** (8/8 testes)
- ✅ Código compila sem erros
- ✅ Sem erros de lint

**Arquivo:** `services/message_processing_service.py` (1.218 linhas)

---

## ⏳ O Que Falta (Fase 3.5.2)

### **1. Fase 3.5.2: Extrair Processamento de Tool Calls** 🔴 **PRIORIDADE ALTA**

**Status:** ⏳ **NÃO INICIADO**

**O que fazer:**
- Criar método `processar_tool_calls()` no `MessageProcessingService`
- Mover lógica de processamento de tool calls do `chat_service.py` (~400-600 linhas)
- Integrar com `ToolExecutionService` para execução
- Integrar com `ResponseFormatter` para combinação

**Localização no código:**
- `chat_service.py`, linhas ~5225-6418+ (processamento de tool calls)

**Componentes a mover:**
1. Preparação de `tools` para tool calling
2. Verificação de `pular_tool_calling` (casos especiais)
3. Detecção de busca direta NESH
4. Chamada da IA com tools
5. Processamento de tool calls retornados
6. Execução de tools via `ToolExecutionService`
7. Combinação de resultados via `ResponseFormatter`

**Complexidade:** 🔴 **ALTA** - Muitas condicionais e casos especiais

**Tempo estimado:** 2-3 sessões de trabalho

---

### **2. Integração no chat_service.py** 🔴 **PRIORIDADE ALTA**

**Status:** ⏳ **NÃO INICIADO**

**O que fazer:**
- Atualizar `processar_mensagem()` para usar `MessageProcessingService.construir_prompt_completo()`
- Atualizar `processar_mensagem()` para usar `MessageProcessingService.processar_tool_calls()` (após Fase 3.5.2)
- Remover código antigo de construção de prompt do `chat_service.py`
- Remover código antigo de processamento de tool calls do `chat_service.py` (após Fase 3.5.2)

**Localização no código:**
- `chat_service.py`, método `processar_mensagem()` (linhas ~3149+)

**Passos:**
1. Inicializar `MessageProcessingService` no `ChatService.__init__()`
2. Substituir construção de prompt por chamada a `construir_prompt_completo()`
3. Substituir processamento de tool calls por chamada a `processar_tool_calls()` (após Fase 3.5.2)
4. Testar que tudo funciona
5. Remover código antigo

**Complexidade:** 🟡 **MÉDIA** - Requer cuidado para não quebrar funcionalidades

**Tempo estimado:** 1-2 sessões de trabalho

---

### **3. Testes de Integração** 🟡 **PRIORIDADE MÉDIA**

**Status:** ⏳ **PENDENTE**

**O que fazer:**
- Criar testes de integração end-to-end
- Testar que `processar_mensagem()` funciona com `MessageProcessingService`
- Testar que `processar_mensagem_stream()` funciona (se aplicável)
- Validar que prompts gerados são equivalentes aos originais
- Validar que tool calls são processados corretamente

**Arquivo:** `tests/test_integracao_chat_service.py` (criar)

**Tempo estimado:** 1 sessão de trabalho

---

### **4. Remoção de Código Antigo** 🟢 **PRIORIDADE BAIXA**

**Status:** ⏳ **PENDENTE** (após integração e testes)

**O que fazer:**
- Remover código antigo de construção de prompt do `chat_service.py` (~600-800 linhas)
- Remover código antigo de processamento de tool calls do `chat_service.py` (~400-600 linhas)
- Limpar imports não utilizados
- Atualizar comentários/documentação

**Tempo estimado:** 1 sessão de trabalho

---

## 📊 Resumo do Progresso

### **Fase 3.5.1: Construção de Prompt**
- ✅ **100% Completo** (todas as 6 sub-etapas)
- ✅ Testes passando
- ✅ Código pronto para uso

### **Fase 3.5.2: Processamento de Tool Calls**
- ⏳ **0% Completo** (não iniciado)
- ⏳ Método `processar_tool_calls()` não existe ainda
- ⏳ Código ainda no `chat_service.py`

### **Integração**
- ⏳ **0% Completo** (não iniciado)
- ⏳ `chat_service.py` ainda não usa `MessageProcessingService`
- ⏳ Código antigo ainda está ativo

### **Testes**
- ✅ Testes unitários do `MessageProcessingService` (8/8 passando)
- ⏳ Testes de integração pendentes

### **Limpeza**
- ⏳ Código antigo ainda não removido

---

## 🎯 Próximos Passos Recomendados

### **Passo 1: Implementar Fase 3.5.2** 🔴 **URGENTE**
1. Criar método `processar_tool_calls()` no `MessageProcessingService`
2. Mover lógica de processamento de tool calls (~400-600 linhas)
3. Testar isoladamente

**Tempo:** 2-3 sessões

### **Passo 2: Integrar no chat_service.py** 🔴 **URGENTE**
1. Atualizar `processar_mensagem()` para usar `MessageProcessingService`
2. Testar que tudo funciona
3. Validar que não há regressões

**Tempo:** 1-2 sessões

### **Passo 3: Testes de Integração** 🟡 **IMPORTANTE**
1. Criar testes end-to-end
2. Validar todos os fluxos críticos
3. Corrigir problemas encontrados

**Tempo:** 1 sessão

### **Passo 4: Limpeza Final** 🟢 **OPCIONAL**
1. Remover código antigo
2. Limpar imports
3. Atualizar documentação

**Tempo:** 1 sessão

---

## 📈 Estimativa de Redução Final

**Antes do Passo 3.5:**
- `chat_service.py`: ~8.390 linhas

**Após Fase 3.5.1 (completa):**
- Código movido: ~600-800 linhas (construção de prompt)
- `chat_service.py`: ~7.590-7.790 linhas (estimado)

**Após Fase 3.5.2 (pendente):**
- Código a mover: ~400-600 linhas (processamento de tool calls)
- `chat_service.py`: ~7.190-7.390 linhas (estimado)

**Redução total estimada:** ~1.000-1.400 linhas

**Meta original:** < 5.000 linhas  
**Progresso:** ~17% da meta (antes) → ~25-30% da meta (após Passo 3.5 completo)

---

## ⚠️ Riscos e Mitigações

### **Risco 1: Quebrar funcionalidades existentes**
- **Mitigação:** Testar cada etapa isoladamente
- **Mitigação:** Manter código antigo como fallback temporário
- **Mitigação:** Testes de integração completos

### **Risco 2: Muitas dependências do chat_service**
- **Mitigação:** Passar dependências como parâmetros ou callbacks
- **Mitigação:** Criar helpers/interfaces para abstrair dependências

### **Risco 3: Código muito complexo e acoplado**
- **Mitigação:** Extrair em partes menores (sub-métodos)
- **Mitigação:** Manter comentários explicando lógica

---

## 📝 Notas Importantes

1. **Fase 3.5.1 está 100% completa e testada** ✅
2. **Fase 3.5.2 é a próxima prioridade** 🔴
3. **Integração deve ser feita após Fase 3.5.2** ⏳
4. **Testes são críticos antes de remover código antigo** ⚠️
5. **Abordagem incremental é recomendada** 💡

---

**Última atualização:** 12/01/2026  
**Status:** 🔄 **FASE 3.5.1 COMPLETA** - Fase 3.5.2 pendente
