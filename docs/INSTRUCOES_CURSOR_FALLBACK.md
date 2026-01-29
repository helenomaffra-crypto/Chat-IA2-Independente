# Instruções para Cursor: Patch de Fallback

## 📋 Resumo Executivo

**Problema:** `enviar_relatorio_email` tem handler no `ToolExecutionService`, mas no modo preview retorna fallback que faz o sistema ir para `ToolRouter` (que não tem essa tool), causando loop/erro.

**Solução:** Diferenciar dois tipos de fallback:
1. **Roteamento** (`fallback_to="TOOL_ROUTER"`) → quando handler não existe
2. **Interno** (`fallback_to="CHAT_SERVICE"`) → quando handler existe mas quer delegar

---

## 🚀 Passo a Passo

### 1. Abrir o Prompt Principal

Abra o arquivo: `docs/PROMPT_CURSOR_FALLBACK_PATCH.md`

Copie a seção **"1. Prompt Principal (copiar e colar)"** e cole no Cursor.

### 2. Anexar Trechos de Código

Abra o arquivo: `docs/TRECHOS_CODIGO_PARA_CURSOR.md`

Cole os trechos **1, 2, 3 e 4** no prompt do Cursor, após o prompt principal.

### 3. Adicionar Regra de Validação

No final do prompt, adicione:

```
REGRA CRÍTICA: enviar_relatorio_email NUNCA deve ir pro ToolRouter (porque não existe lá).
Se o handler do ToolExecutionService quiser delegar, delega para CHAT_SERVICE.
Se você mandar exatamente esse prompt pro Cursor, ele consegue gerar um diff fechado sem precisar ficar adivinhando intenção.
```

---

## ✅ Checklist de Validação

Após o Cursor gerar o patch, verifique:

- [ ] `ToolExecutionService.executar_tool()` retorna `fallback_to="TOOL_ROUTER"` quando handler não existe
- [ ] `_handler_enviar_relatorio_email` retorna `fallback_to="CHAT_SERVICE"` no modo preview
- [ ] `ChatService._executar_funcao_tool()` roteia baseado em `fallback_to`:
  - `CHAT_SERVICE` → chama `_fallback_chat_service()`
  - `TOOL_ROUTER` → continua para ToolRouter
- [ ] `normalize_tool_result()` preserva `fallback_to` e `use_fallback`
- [ ] Logs claros em cada decisão de roteamento
- [ ] `enviar_relatorio_email` NUNCA vai para ToolRouter quando tem handler

---

## 🧪 Teste Após Aplicar

1. **Tool com handler direto:**
   ```
   "envie um email para teste@exemplo.com"
   ```
   → Deve funcionar normalmente

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

4. **enviar_relatorio_email (confirmação):**
   ```
   "sim"
   ```
   → Deve enviar email corretamente

---

## 📝 Notas Finais

- O patch já foi parcialmente implementado, mas precisa ser revisado e validado
- O Cursor deve gerar um diff limpo baseado nos trechos fornecidos
- Se houver dúvidas, o Cursor pode consultar os arquivos mencionados no prompt
