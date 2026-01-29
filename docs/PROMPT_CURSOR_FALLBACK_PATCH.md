# Prompt para Cursor: Patch de Fallback de Tools

## 1. Prompt Principal (copiar e colar)

```
Quero um patch (diff) para eliminar loop de fallback e padronizar o fluxo de tools.

Contexto: existem 2 tipos de fallback e hoje estão misturados:

1. fallback de roteamento (ToolExecutionService → ToolRouter) quando NÃO existe handler
2. fallback interno (ToolExecutionService → ChatService legado) quando EXISTE handler mas quer delegar (ex.: preview email)

BUG atual: enviar_relatorio_email tem handler no ToolExecutionService, mas no modo preview ele retorna "FALLBACK_REQUIRED" e isso faz o ChatService ir pro ToolRouter (que não tem essa tool), causando loop/erro.

Objetivo:
- Diferenciar fallback por destino: fallback_to="TOOL_ROUTER" vs fallback_to="CHAT_SERVICE"
- No ChatService, se fallback_to="CHAT_SERVICE", chamar o fallback legado específico (ex.: _enviar_relatorio_email_fallback_legacy) e NÃO ToolRouter
- ToolRouter só deve ser usado quando não existe handler no ToolExecutionService (ou quando fallback_to="TOOL_ROUTER" explicitamente)

Tarefas:

A) ToolExecutionService
- No executar_tool() quando NÃO encontrar handler: retornar dict padronizado com:
  use_fallback: True, fallback_to: "TOOL_ROUTER", error: "HANDLER_NOT_FOUND", tool: <nome>
- No handler _handler_enviar_relatorio_email em modo preview: retornar dict padronizado com:
  use_fallback: True, fallback_to: "CHAT_SERVICE", error: "PREVIEW_HANDOFF" (ou equivalente), tool: "enviar_relatorio_email"
- NÃO retornar None

B) ChatService
- No método que executa tools (ex.: _executar_funcao_tool / executar_funcao_tool), ajustar a lógica:
  - Se resultado do ToolExecutionService tiver use_fallback=True:
    - se fallback_to=="CHAT_SERVICE" → chamar fallback legado no ChatService (sem ToolRouter)
    - se fallback_to=="TOOL_ROUTER" → continuar fluxo para ToolRouter
  - Se erro real (não fallback) → retornar normalmente
- Implementar um dispatcher interno (map) para fallback legado por tool (mínimo: enviar_relatorio_email)

C) normalize_tool_result
- Garantir que preserve campos de fallback (use_fallback, fallback_to, error) sem converter em "erro final" indevido

Entrega:
- Me entregue um diff com arquivos e trechos exatos alterados
- Inclua logs claros para cada decisão:
  - "fallback_to=CHAT_SERVICE: usando handler legado"
  - "fallback_to=TOOL_ROUTER: encaminhando ao ToolRouter"

Para localizar:
- services/tool_execution_service.py (executar_tool e handler enviar_relatorio_email)
- services/chat_service.py (função que chama ToolExecutionService e depois ToolRouter)
- services/tool_result.py (normalize_tool_result)

Observação: não quero que o preview de email passe pelo ToolRouter. Ele deve ficar no ChatService.
```

---

## 2. Trechos de Código para Anexar

### A) ChatService - Trecho onde processa resultado do ToolExecutionService

**Arquivo:** `services/chat_service.py`  
**Linhas:** ~615-680

```python
# ✅ NOVO (09/01/2026): Tentar usar ToolExecutionService primeiro (handlers extraídos)
if hasattr(self, "tool_execution_service") and self.tool_execution_service is not None:
    try:
        # Atualizar contexto com session_id e mensagem_original
        if self.tool_execution_service.tool_context:
            self.tool_execution_service.tool_context.session_id = session_id or (hasattr(self, 'session_id_atual') and self.session_id_atual)
            self.tool_execution_service.tool_context.mensagem_original = mensagem_original
        
        resultado_service = self.tool_execution_service.executar_tool(
            nome_funcao=nome_funcao,
            argumentos=argumentos
        )
        
        # ✅✅✅ CRÍTICO (14/01/2026): Roteamento explícito baseado em fallback_to
        # Regra de ouro:
        # - HANDLER_NOT_FOUND (fallback_to="TOOL_ROUTER") → vai para ToolRouter
        # - PREVIEW_MODE (fallback_to="CHAT_SERVICE") → vai para handler legado do ChatService
        # - Sem fallback → resultado válido, retornar
        if isinstance(resultado_service, dict) and resultado_service.get("use_fallback"):
            destino = resultado_service.get("fallback_to")
            
            if destino == "CHAT_SERVICE":
                # ✅ Handler pediu fallback para ChatService legado (ex: preview de enviar_relatorio_email)
                logger.debug(f'🔄 Tool {nome_funcao} pediu fallback para CHAT_SERVICE - chamando handler legado')
                return self._fallback_chat_service(nome_funcao, argumentos, mensagem_original=mensagem_original, session_id=session_id)
            
            elif destino == "TOOL_ROUTER":
                # ✅ Handler não existe - continuar para ToolRouter
                logger.debug(f'🔄 Tool {nome_funcao} não tem handler - seguindo para ToolRouter')
                _fallback_attempted = True
                # NÃO retorna - continua fluxo para ToolRouter abaixo
            
            else:
                # ⚠️ Fallback sem destino explícito - tratar como erro controlado
                logger.warning(f'⚠️ Tool {nome_funcao} pediu fallback sem destino explícito (fallback_to={destino})')
                from services.tool_result import normalize_tool_result
                return normalize_tool_result(nome_funcao, {
                    "sucesso": False,
                    "error": "FALLBACK_DESTINATION_MISSING",
                    "resposta": f"❌ Tool {nome_funcao} pediu fallback sem destino explícito."
                })
        
        elif isinstance(resultado_service, dict):
            # ✅ Resultado válido do ToolExecutionService - usar
            logger.info(f'✅ Tool {nome_funcao} executada via ToolExecutionService')
            return resultado_service
        
        elif resultado_service is not None:
            # Caso legado / eventual (não dict mas não None)
            return resultado_service
    except Exception as e:
        logger.warning(f'⚠️ Erro no ToolExecutionService para {nome_funcao}: {e}. Usando fallback.', exc_info=True)

# 🆕 Tentar usar ToolExecutor/ToolRouter (arquitetura nova)
# ✅ Só chega aqui se não foi fallback para CHAT_SERVICE ou se ToolExecutionService não foi chamado
if hasattr(self, "tool_executor") and self.tool_executor is not None:
    resultado_router = self.tool_executor.executar(
        chat_service=self,
        nome_funcao=nome_funcao,
        argumentos=argumentos,
        mensagem_original=mensagem_original,
    )
```

---

### B) ToolExecutionService - Caso "handler não encontrado"

**Arquivo:** `services/tool_execution_service.py`  
**Linhas:** ~107-122

```python
# Fallback: handler não existe - sinalizar para continuar no próximo nível (ToolRouter)
# ✅ CRÍTICO (14/01/2026): Retornar dict padronizado com fallback_to explícito
return {
    "sucesso": False,
    "ok": False,
    "tool": nome_funcao,
    "error": "HANDLER_NOT_FOUND",
    "erro": "HANDLER_NOT_FOUND",  # Compatibilidade
    "use_fallback": True,  # ✅ Flag explícita para ChatService continuar fluxo
    "fallback_to": "TOOL_ROUTER",  # ✅✅✅ CRÍTICO: Destino explícito do fallback
    "resposta": "",  # Vazio - não é erro final, apenas sinal de fallback
    "text": "",  # Compatibilidade
    "dados_json": None,
    "precisa_formatar": False,
    "kind": "tool_result"  # Não é erro final, é sinal de fallback
}
```

---

### C) ToolExecutionService - Handler enviar_relatorio_email (modo preview)

**Arquivo:** `services/tool_execution_service.py`  
**Linhas:** ~403-420

```python
# ⚠️ Para preview ou geração de relatório, usar fallback antigo do ChatService
# A lógica é muito complexa (histórico, fechamento, categoria, etc.)
# e será extraída em uma etapa futura
# ✅✅✅ CRÍTICO (14/01/2026): Sinalizar fallback explícito para ChatService legado
return {
    "sucesso": False,
    "ok": False,
    "tool": "enviar_relatorio_email",
    "use_fallback": True,
    "fallback_to": "CHAT_SERVICE",  # ✅✅✅ CRÍTICO: Destino explícito - handler legado do ChatService
    "reason": "PREVIEW_MODE",  # Motivo do fallback
    "resposta": "",  # Vazio - não é erro final
    "text": "",  # Compatibilidade
    "dados_json": None,
    "precisa_formatar": False,
    "kind": "tool_result"
}
```

---

### D) normalize_tool_result - Preservação de fallback

**Arquivo:** `services/tool_result.py`  
**Linhas:** ~121-189

```python
def normalize_tool_result(tool: str, raw: Any) -> ToolResult:
    """
    Garante que tool nunca 'vaza' None para pipeline.
    
    Normaliza qualquer retorno de tool para ToolResult padronizado.
    
    Args:
        tool: Nome da tool executada
        raw: Retorno bruto da tool (pode ser None, dict, str, etc.)
    
    Returns:
        ToolResult sempre válido (nunca None)
    """
    if raw is None:
        return err_result(tool, "Tool retornou None")
    
    if isinstance(raw, dict):
        # Normaliza campos mínimos
        normalized = ToolResult(raw)
        normalized.setdefault("tool", tool)
        normalized.setdefault("kind", "tool_result")
        
        # ✅ CRÍTICO (14/01/2026): Preservar sinal de fallback ANTES de normalizar
        # Se error="FALLBACK_REQUIRED" ou use_fallback=True, preservar esses campos
        is_fallback = (
            normalized.get("error") == "FALLBACK_REQUIRED" or
            normalized.get("erro") == "FALLBACK_REQUIRED" or
            normalized.get("use_fallback") is True
        )
        
        # ✅ CRÍTICO: Preservar fallback_to se presente
        fallback_to = normalized.get("fallback_to")
        
        # Garantir campos obrigatórios
        if "ok" not in normalized and "sucesso" in normalized:
            normalized["ok"] = normalized["sucesso"]
        elif "ok" not in normalized:
            # ✅ Se é fallback, ok=False (mas não é erro final)
            normalized["ok"] = False if is_fallback else True
        
        if "sucesso" not in normalized:
            normalized["sucesso"] = normalized.get("ok", True)
        
        # Normalizar text/resposta
        if "text" not in normalized and "resposta" in normalized:
            normalized["text"] = normalized["resposta"]
        elif "resposta" not in normalized and "text" in normalized:
            normalized["resposta"] = normalized["text"]
        
        # Normalizar error/erro
        if "error" not in normalized and "erro" in normalized:
            normalized["error"] = normalized["erro"]
        elif "erro" not in normalized and "error" in normalized:
            normalized["erro"] = normalized["error"]
        
        # ✅ Garantir que use_fallback está presente se é fallback
        if is_fallback:
            normalized["use_fallback"] = True
            if "error" not in normalized:
                normalized["error"] = "FALLBACK_REQUIRED"
            if "erro" not in normalized:
                normalized["erro"] = "FALLBACK_REQUIRED"
            # ✅ CRÍTICO (14/01/2026): Marcar como não-sucesso mas não erro final
            # Isso evita que seja tratado como sucesso em métricas/log
            normalized["ok"] = False
            normalized["sucesso"] = False
        
        # ✅ CRÍTICO: Preservar fallback_to se presente (não sobrescrever)
        if fallback_to:
            normalized["fallback_to"] = fallback_to
        
        return normalized
    
    # Se devolveu string ou outra coisa, encapsula
    return ok_result(tool, kind="generic", text=str(raw))
```

---

## 3. Regra de Validação (para conferir)

**REGRA CRÍTICA:** `enviar_relatorio_email` NUNCA deve ir pro ToolRouter (porque não existe lá).

- ✅ Se o handler do ToolExecutionService quiser delegar, delega para `CHAT_SERVICE`
- ✅ Se o handler não existe, aí sim vai para `TOOL_ROUTER`
- ❌ NUNCA deve acontecer: `enviar_relatorio_email` com handler existente indo para `TOOL_ROUTER`

**Checklist de validação:**
- [ ] `enviar_relatorio_email` com handler retorna `fallback_to="CHAT_SERVICE"` no modo preview
- [ ] `enviar_relatorio_email` com handler NÃO vai para ToolRouter
- [ ] Tool sem handler retorna `fallback_to="TOOL_ROUTER"` e vai para ToolRouter
- [ ] `normalize_tool_result` preserva `fallback_to` e `use_fallback`
- [ ] Logs claros em cada decisão de roteamento

---

## 4. Logs Esperados (para debug)

Quando funcionar corretamente, você deve ver logs como:

```
🔄 Tool enviar_relatorio_email pediu fallback para CHAT_SERVICE - chamando handler legado
```

OU

```
🔄 Tool obter_dashboard_hoje não tem handler - seguindo para ToolRouter
```

E NUNCA:

```
⚠️ ToolRouter também pediu fallback para enviar_relatorio_email após ToolExecutionService - retornando erro final
```

---

## 5. Estrutura do _fallback_chat_service (exemplo)

```python
def _fallback_chat_service(
    self,
    nome_funcao: str,
    argumentos: Dict[str, Any],
    mensagem_original: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fallback para handlers legados do ChatService.
    
    ✅✅✅ CRÍTICO (14/01/2026): Mapeamento explícito de tools para handlers legados.
    Usado quando ToolExecutionService retorna fallback_to="CHAT_SERVICE".
    """
    # ✅ Mapeamento explícito de tools para handlers legados
    if nome_funcao == "enviar_relatorio_email":
        logger.info(f'✅ fallback_to=CHAT_SERVICE: usando handler legado para {nome_funcao}')
        return self._executar_funcao_tool_legacy_enviar_relatorio_email(
            argumentos, 
            mensagem_original=mensagem_original, 
            session_id=session_id
        )
    
    # Se tool não tem handler legado mapeado, retornar erro
    from services.tool_result import err_result
    return err_result(
        tool=nome_funcao,
        error='FALLBACK_NOT_IMPLEMENTED',
        text=f'❌ Tool {nome_funcao} pediu fallback para CHAT_SERVICE mas não tem handler legado implementado.'
    )
```

---

## 6. Notas Importantes

1. **NÃO duplicar código**: O `_executar_funcao_tool_legacy_enviar_relatorio_email` deve reutilizar o código existente do fallback antigo (linha ~2217+ do chat_service.py), não copiar tudo.

2. **Preservar compatibilidade**: Manter campos `error` e `erro` para compatibilidade, mas priorizar `fallback_to` para decisão de roteamento.

3. **Logs obrigatórios**: Cada decisão de roteamento deve ter log claro para facilitar debug futuro.

4. **Teste de regressão**: Após aplicar o patch, testar:
   - Tool com handler direto → deve funcionar
   - Tool sem handler → deve ir para ToolRouter
   - `enviar_relatorio_email` preview → deve ir para handler legado (NÃO ToolRouter)
   - `enviar_relatorio_email` confirmação → deve funcionar normalmente
