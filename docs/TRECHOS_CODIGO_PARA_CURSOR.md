# Trechos de Código para Anexar ao Cursor

## ⚠️ IMPORTANTE: Cole estes trechos EXATOS no prompt do Cursor

---

## 1. ChatService - Processamento de resultado do ToolExecutionService

**Arquivo:** `services/chat_service.py`  
**Localização:** Método `_executar_funcao_tool`, linhas ~615-680

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
            
            # ✅ CRÍTICO (09/01/2026): Processar _resultado_interno para salvar draft_id no estado
            resultado_interno = resultado_service.get('_resultado_interno', {})
            if resultado_interno and 'ultima_resposta_aguardando_email' in resultado_interno:
                self.ultima_resposta_aguardando_email = resultado_interno['ultima_resposta_aguardando_email']
                draft_id_salvo = self.ultima_resposta_aguardando_email.get('draft_id') if self.ultima_resposta_aguardando_email else None
                if draft_id_salvo:
                    logger.info(f'✅✅✅ [TOOL_EXECUTION] draft_id {draft_id_salvo} salvo no estado após execução via ToolExecutionService')
                else:
                    logger.warning(f'⚠️ [TOOL_EXECUTION] ToolExecutionService retornou resultado mas sem draft_id')
            
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
    # ✅ CRÍTICO (14/01/2026): Verificar se ToolRouter também pediu fallback
    # Se já tentou fallback uma vez e ToolRouter também pede, retornar erro final
    if _fallback_attempted and resultado_router and resultado_router.get("_use_fallback", False):
        logger.warning(f'⚠️ ToolRouter também pediu fallback para {nome_funcao} após ToolExecutionService - retornando erro final')
        from services.tool_result import err_result
        return err_result(
            tool=nome_funcao,
            error='FALLBACK_LOOP_DETECTED',
            text=f'❌ Tool {nome_funcao} não encontrada em nenhum handler disponível.'
        )
```

---

## 2. ToolExecutionService - Handler não encontrado

**Arquivo:** `services/tool_execution_service.py`  
**Localização:** Método `executar_tool`, linhas ~107-122

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

## 3. ToolExecutionService - Handler enviar_relatorio_email (modo preview)

**Arquivo:** `services/tool_execution_service.py`  
**Localização:** Método `_handler_enviar_relatorio_email`, linhas ~403-420

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

## 4. normalize_tool_result - Função completa

**Arquivo:** `services/tool_result.py`  
**Localização:** Função `normalize_tool_result`, linhas ~121-189

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

## 5. Stack Trace do Erro Atual (para referência)

```
⚠️ ToolRouter também pediu fallback para enviar_relatorio_email após ToolExecutionService - retornando erro final
❌ Tool enviar_relatorio_email não encontrada em nenhum handler disponível.
```

**Causa raiz:** O handler `_handler_enviar_relatorio_email` retorna `fallback_to="CHAT_SERVICE"`, mas o código atual não está tratando isso corretamente e está indo para o ToolRouter.

---

## 6. Log Esperado Após Correção

**Quando funcionar corretamente:**

```
🔄 Tool enviar_relatorio_email pediu fallback para CHAT_SERVICE - chamando handler legado
✅ fallback_to=CHAT_SERVICE: usando handler legado para enviar_relatorio_email
```

**NUNCA deve aparecer:**

```
⚠️ ToolRouter também pediu fallback para enviar_relatorio_email após ToolExecutionService - retornando erro final
```
