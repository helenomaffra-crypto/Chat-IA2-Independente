# Correções Aplicadas: Fallback de Tools

## ✅ Correções Implementadas

### 1. ✅ `_fallback_attempted = False` no início do `_executar_funcao_tool`

**Localização:** `services/chat_service.py`, linha ~604-608

**Correção aplicada:**
```python
# ✅✅✅ CRÍTICO (14/01/2026): Inicializar _fallback_attempted como False no início
# Isso garante que cada chamada começa com estado limpo
# NOTA: O parâmetro _fallback_attempted tem valor padrão False na assinatura,
# mas garantimos que está False aqui para clareza e segurança
# (garantir que sempre começa como False, mesmo se alguém passar True por engano)
_fallback_attempted = False
```

**Status:** ✅ CORRIGIDO

---

### 2. ✅ `_fallback_chat_service()` não chama `_executar_funcao_tool` (sem recursão)

**Localização:** `services/chat_service.py`, linha ~789-840

**Correção aplicada:**
- `_executar_funcao_tool_legacy_enviar_relatorio_email` agora desabilita temporariamente `tool_execution_service` e `tool_executor` antes de chamar `_executar_funcao_tool`
- Isso garante que o código vai direto para o bloco "Fallback: Implementação antiga" sem tentar ToolExecutionService/ToolRouter novamente
- Restaura o estado original no `finally`

**Status:** ✅ CORRIGIDO (evita recursão desabilitando ToolExecutionService/ToolExecutor temporariamente)

---

### 3. ✅ Loop detection aceita `_use_fallback` OU `use_fallback`

**Localização:** `services/chat_service.py`, linha ~696-707

**Correção aplicada:**
```python
# ✅✅✅ CRÍTICO: Aceitar tanto "_use_fallback" quanto "use_fallback" para compatibilidade
router_pediu_fallback = (
    resultado_router and (
        resultado_router.get("_use_fallback", False) or 
        resultado_router.get("use_fallback", False)
    )
)
if _fallback_attempted and router_pediu_fallback:
    logger.warning(f'⚠️ ToolRouter também pediu fallback para {nome_funcao} após ToolExecutionService - retornando erro final')
    # ... retorna erro
```

**Status:** ✅ CORRIGIDO

---

### 4. ✅ `enviar_relatorio_email` nunca roteia para ToolRouter (somente CHAT_SERVICE no preview)

**Localização:** `services/chat_service.py`, linha ~643-646

**Correção aplicada:**
```python
if destino == "CHAT_SERVICE":
    # ✅✅✅ REGRA CRÍTICA: Handler pediu fallback para ChatService legado (ex: preview de enviar_relatorio_email)
    # A execução DEVE parar aqui e NÃO continuar para ToolRouter
    logger.info(f'✅ fallback_to=CHAT_SERVICE: usando handler legado para {nome_funcao} (execução para aqui, NÃO vai para ToolRouter)')
    resultado_legado = self._fallback_chat_service(nome_funcao, argumentos, mensagem_original=mensagem_original, session_id=session_id)
    # ✅✅✅ CRÍTICO: Retornar imediatamente - NÃO continuar para ToolRouter
    return resultado_legado
```

**Status:** ✅ CORRIGIDO (retorna imediatamente quando `fallback_to="CHAT_SERVICE"`)

---

## 📋 Resumo das Garantias

| Garantia | Status | Localização |
|----------|--------|-------------|
| `_fallback_attempted = False` no início | ✅ | Linha ~608 |
| `_fallback_chat_service()` sem recursão | ✅ | Linha ~789-840 (desabilita ToolExecutionService/ToolExecutor) |
| Loop detection aceita `_use_fallback` OU `use_fallback` | ✅ | Linha ~696-707 |
| `enviar_relatorio_email` nunca vai para ToolRouter | ✅ | Linha ~643-646 (retorna imediatamente) |

---

## 🔍 Verificações Adicionais

### ToolExecutionService

**Arquivo:** `services/tool_execution_service.py`

- ✅ `executar_tool()` retorna `fallback_to="TOOL_ROUTER"` quando handler não existe (linha ~109-122)
- ✅ `_handler_enviar_relatorio_email()` retorna `fallback_to="CHAT_SERVICE"` no modo preview (linha ~407-420)

### normalize_tool_result

**Arquivo:** `services/tool_result.py`

- ✅ Preserva `fallback_to` e `use_fallback` (linha ~143-184)

---

## ✅ Todas as Garantias Implementadas

1. ✅ `_fallback_attempted = False` no início do `_executar_funcao_tool`
2. ✅ `_fallback_chat_service()` não chama `_executar_funcao_tool` recursivamente (desabilita ToolExecutionService/ToolExecutor temporariamente)
3. ✅ Loop detection aceita `_use_fallback` OU `use_fallback`
4. ✅ `enviar_relatorio_email` nunca roteia para ToolRouter quando `fallback_to="CHAT_SERVICE"` (retorna imediatamente)

---

## 🧪 Testes Recomendados

1. **Tool com handler direto:**
   ```
   "envie um email para teste@exemplo.com"
   ```
   → Deve funcionar normalmente via ToolExecutionService

2. **Tool sem handler (ex: obter_dashboard_hoje):**
   ```
   "o que temos pra hoje?"
   ```
   → Deve ir para ToolRouter e funcionar

3. **enviar_relatorio_email (preview):**
   ```
   "filtre os dmd"
   "envie esse relatorio para helenomaffra@gmail.com"
   ```
   → Deve ir para handler legado (NÃO ToolRouter)
   → Deve mostrar preview corretamente
   → Log deve mostrar: `✅ fallback_to=CHAT_SERVICE: usando handler legado para enviar_relatorio_email`

4. **enviar_relatorio_email (confirmação):**
   ```
   "sim"
   ```
   → Deve enviar email corretamente

---

## 📝 Notas Finais

- Todas as 4 garantias foram implementadas
- O código está protegido contra loops infinitos
- `enviar_relatorio_email` nunca vai para ToolRouter quando em modo preview
- Logs claros foram adicionados para facilitar debug
