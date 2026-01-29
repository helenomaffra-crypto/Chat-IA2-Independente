# 📋 Passo 3.5: Extrair Construção de Prompt e Tool Calls - Plano de Implementação

**Data:** 10/01/2026  
**Status:** 🔄 **EM PROGRESSO**

---

## 🎯 Objetivo

Extrair a lógica de construção de prompt e processamento de tool calls do `chat_service.py` para o `MessageProcessingService`, completando a refatoração do método `processar_mensagem()`.

---

## 📊 Análise do Código Atual

### **O que precisa ser extraído:**

#### **1. Construção de Prompt** (~600-800 linhas)
**Localização:** `chat_service.py`, linhas ~4612-5223

**Componentes:**
- Construção de `saudacao_personalizada` (linhas ~4613-4629)
- Busca de `regras_aprendidas` (linhas ~4631-4639)
- Construção de `system_prompt` via `PromptBuilder` (linhas ~4641-4645)
- Construção de `contexto_str` (linhas ~4647-4969)
  - Contexto de processo
  - Contexto de categoria
  - Contexto de CE/CCT
  - Instruções de vinculação
  - Avisos de pergunta genérica
- Construção de `historico_str` (linhas ~4747-4867)
  - Filtragem de histórico por processo
  - Tratamento especial para emails/relatórios
- Busca de `contexto_sessao` (linhas ~4971-5073)
- Construção de `user_prompt` via `PromptBuilder` (linhas ~5075-5146)
- Modo legislação estrita (linhas ~5148-5213)
- Prompts adicionais para melhorar email (linhas ~5084-5134)

**Complexidade:** 🔴 **ALTA** - Muitas variáveis e lógica condicional complexa

#### **2. Processamento de Tool Calls** (~400-600 linhas)
**Localização:** `chat_service.py`, linhas ~5225-6418+

**Componentes:**
- Preparação de `tools` para tool calling (linhas ~5226-5227)
- Verificação de `pular_tool_calling` (linhas ~5229-5318)
- Detecção de busca direta NESH (linhas ~5323-5398)
- Chamada da IA com tools (linhas ~6405-6406)
- Processamento de tool calls retornados (linhas ~6411-6418+)
- Execução de tools via `ToolExecutionService`
- Combinação de resultados via `ResponseFormatter`

**Complexidade:** 🔴 **ALTA** - Muitas condicionais e casos especiais

---

## 🏗️ Arquitetura Proposta

### **Estrutura do MessageProcessingService (após Passo 3.5):**

```python
class MessageProcessingService:
    # ✅ Já existem (Fase 1-3):
    - _detectar_comando_interface()
    - _detectar_melhorar_email()
    - processar_core()  # Fase 1-3
    
    # ✅ NOVO (Fase 3.5):
    - construir_prompt_completo()  # Extraído do chat_service
    - processar_tool_calls()  # Extraído do chat_service
```

### **Fluxo após Passo 3.5:**

```
processar_mensagem() (chat_service.py)
  ↓
processar_core() (MessageProcessingService)
  ├─ Detecções (comandos, confirmações, precheck)
  ├─ construir_prompt_completo() ← NOVO (Fase 3.5)
  │   ├─ Preparar saudação personalizada
  │   ├─ Buscar regras aprendidas
  │   ├─ Construir system_prompt
  │   ├─ Construir contexto_str (processo, categoria, CE/CCT, etc.)
  │   ├─ Construir historico_str (filtrado)
  │   ├─ Buscar contexto_sessao
  │   ├─ Construir user_prompt
  │   └─ Modo legislação estrita (se aplicável)
  ├─ Chamar IA (via ai_service)
  └─ processar_tool_calls() ← NOVO (Fase 3.5)
      ├─ Preparar tools
      ├─ Verificar casos especiais (pular tool calling, busca direta NESH)
      ├─ Executar tools via ToolExecutionService
      └─ Combinar resultados via ResponseFormatter
```

---

## 📝 Plano de Implementação

### **Fase 3.5.1: Extrair Construção de Prompt** 🔴 ALTA PRIORIDADE

**Objetivo:** Mover toda a lógica de construção de prompt para `MessageProcessingService`.

**Método a criar:**
```python
def construir_prompt_completo(
    self,
    mensagem: str,
    historico: List[Dict],
    session_id: Optional[str],
    nome_usuario: Optional[str],
    processo_ref: Optional[str],
    categoria_atual: Optional[str],
    numero_ce_contexto: Optional[str],
    numero_cct: Optional[str],
    contexto_processo: Optional[Dict],
    acao_info: Dict,
    resposta_base_precheck: Optional[str],
    eh_pedido_melhorar_email: bool,
    email_para_melhorar_contexto: Optional[Dict],
    # ... outras variáveis necessárias
) -> Dict[str, str]:
    """
    Constrói prompt completo (system_prompt + user_prompt) para a IA.
    
    Returns:
        Dict com:
        - 'system_prompt': str
        - 'user_prompt': str
        - 'usar_tool_calling': bool (pode ser False no modo legislação estrita)
    """
```

**Passos:**
1. Criar método `construir_prompt_completo()` no `MessageProcessingService`
2. Mover lógica de construção de prompt (~600-800 linhas)
3. Receber todas as variáveis necessárias como parâmetros
4. Retornar dict com prompts prontos
5. Atualizar `processar_mensagem()` para usar o novo método

**Dependências necessárias:**
- `PromptBuilder` (já existe)
- Helpers de `chat_service` (via parâmetros ou callback)
- `buscar_regras_aprendidas()` (via import)
- `buscar_contexto_sessao()` (via import)
- `formatar_contexto_para_prompt()` (via import)

---

### **Fase 3.5.2: Extrair Processamento de Tool Calls** 🔴 ALTA PRIORIDADE

**Objetivo:** Mover toda a lógica de processamento de tool calls para `MessageProcessingService`.

**Método a criar:**
```python
def processar_tool_calls(
    self,
    resposta_ia_raw: Any,
    mensagem: str,
    usar_tool_calling: bool,
    tools: Optional[List[Dict]],
    # ... outras variáveis necessárias
) -> Dict[str, Any]:
    """
    Processa tool calls retornados pela IA.
    
    Args:
        resposta_ia_raw: Resposta raw da IA (pode ter tool_calls)
        mensagem: Mensagem original do usuário
        usar_tool_calling: Se deve processar tool calls
        tools: Lista de tools disponíveis
    
    Returns:
        Dict com:
        - 'resposta_final': str
        - 'tool_calls_executados': List[Dict]
        - 'ultima_resposta_aguardando_email': Optional[Dict]
        - 'ultima_resposta_aguardando_duimp': Optional[Dict]
    """
```

**Passos:**
1. Criar método `processar_tool_calls()` no `MessageProcessingService`
2. Mover lógica de processamento (~400-600 linhas)
3. Integrar com `ToolExecutionService` para execução
4. Integrar com `ResponseFormatter` para combinação
5. Atualizar `processar_mensagem()` para usar o novo método

**Dependências necessárias:**
- `ToolExecutionService` (já existe)
- `ResponseFormatter` (já existe)
- Helpers de `chat_service` (via parâmetros ou callback)

---

## 🔧 Estratégia de Implementação

### **Abordagem Incremental:**

1. **Criar métodos vazios primeiro** (interface)
2. **Mover código gradualmente** (testando após cada parte)
3. **Manter compatibilidade** (chat_service ainda funciona)
4. **Testar cada etapa** antes de avançar

### **Riscos e Mitigações:**

**Risco 1: Muitas dependências do chat_service**
- **Mitigação:** Passar dependências como parâmetros ou callbacks
- **Mitigação:** Criar helpers/interfaces para abstrair dependências

**Risco 2: Código muito complexo e acoplado**
- **Mitigação:** Extrair em partes menores (sub-métodos)
- **Mitigação:** Manter comentários explicando lógica

**Risco 3: Quebrar funcionalidades existentes**
- **Mitigação:** Testar cada extração isoladamente
- **Mitigação:** Manter código antigo como fallback temporário

---

## 📋 Checklist de Implementação

### **Fase 3.5.1: Construção de Prompt**
- [ ] Criar método `construir_prompt_completo()` no `MessageProcessingService`
- [ ] Mover lógica de saudação personalizada
- [ ] Mover lógica de regras aprendidas
- [ ] Mover construção de `system_prompt`
- [ ] Mover construção de `contexto_str`
- [ ] Mover construção de `historico_str`
- [ ] Mover busca de `contexto_sessao`
- [ ] Mover construção de `user_prompt`
- [ ] Mover modo legislação estrita
- [ ] Mover prompts adicionais (melhorar email, etc.)
- [ ] Integrar no `processar_core()`
- [ ] Testar que prompts estão corretos

### **Fase 3.5.2: Processamento de Tool Calls**
- [ ] Criar método `processar_tool_calls()` no `MessageProcessingService`
- [ ] Mover preparação de tools
- [ ] Mover verificação de casos especiais
- [ ] Mover chamada da IA
- [ ] Mover processamento de tool calls retornados
- [ ] Integrar com `ToolExecutionService`
- [ ] Integrar com `ResponseFormatter`
- [ ] Integrar no `processar_core()`
- [ ] Testar que tool calls são processados corretamente

### **Validação Final**
- [ ] Testar `processar_mensagem()` funciona
- [ ] Testar `processar_mensagem_stream()` funciona
- [ ] Testar todos os fluxos críticos
- [ ] Verificar que não há regressões

---

## 🎯 Resultado Esperado

**Após Passo 3.5:**
- ✅ `MessageProcessingService` completo e funcional
- ✅ `processar_mensagem()` reduzido de ~3000 linhas para ~500-800 linhas
- ✅ Construção de prompt isolada e testável
- ✅ Processamento de tool calls isolado e testável
- ✅ Redução total de ~500-800 linhas do `chat_service.py`

**Estimativa de redução final:**
- Antes Passo 3.5: `chat_service.py` ~9.115 linhas
- Depois Passo 3.5: `chat_service.py` ~8.315-8.615 linhas
- Redução adicional: ~500-800 linhas

---

**Última atualização:** 10/01/2026  
**Status:** 🔄 **PRONTO PARA IMPLEMENTAR**
