# 🔒 Fluxo de Validação/Gate para Tool Calling

**Data:** 14/01/2026  
**Objetivo:** Camada de validação antes de executar tools, seguindo sugestões do ChatGPT

---

## 📋 Pseudocódigo do Fluxo

```python
# 1. CLASSIFICAÇÃO LEVE (antes de chamar IA)
intent = classificar_intencao(mensagem)
# Retorna: UI_COMMAND | TOOL_QUERY | TOOL_ACTION | CHAT_ONLY

if intent == UI_COMMAND:
    return executar_comando_interface(mensagem)  # Resposta instantânea

# 2. IA GERA TOOL CALLS (com sinônimos: parecer, análise, visão geral, etc.)
tool_calls = ai_service.chat_completion(mensagem, tools=available_tools)

# 3. GATE DE VALIDAÇÃO (antes de executar cada tool)
for tool_call in tool_calls:
    nome_tool = tool_call['function']['name']
    argumentos = tool_call['function']['arguments']
    
    # 3.1. Validar contrato (enums, tipos, obrigatórios)
    erro_validacao = validar_contrato_tool(nome_tool, argumentos)
    if erro_validacao:
        return f"❌ Preciso de: {erro_validacao}"
    
    # 3.2. Validar contexto (report_id, processo, etc.)
    erro_contexto = validar_contexto_tool(nome_tool, argumentos, session_id)
    if erro_contexto:
        return f"❌ {erro_contexto}"
    
    # 3.3. Validar ações sensíveis (exigir confirmação)
    if eh_acao_sensivel(nome_tool):  # pagar, enviar, criar_duimp
        if not tem_confirmacao_pendente(session_id, nome_tool):
            return mostrar_preview_e_aguardar_confirmacao(tool_call)
    
    # 3.4. EXECUTAR (só chega aqui se passou todas validações)
    resultado = executar_tool(nome_tool, argumentos)
```

---

## 🎯 Pontos-Chave

1. **Classificação leve** → Evita chamar IA desnecessariamente
2. **IA gera tool calls** → Modelo entende sinônimos naturalmente
3. **Gate de validação** → Valida ANTES de executar (não depois)
4. **Contrato rígido** → Enums, tipos, obrigatórios
5. **Contexto validado** → report_id, processo, etc.
6. **Ações sensíveis** → Sempre exigem confirmação

---

## 📝 Exemplo Prático

```
Usuário: "me dê um parecer do dia"
  ↓
1. classificar_intencao() → TOOL_QUERY
  ↓
2. IA gera: obter_dashboard_hoje()
  ↓
3. Gate valida:
   - ✅ Contrato OK (sem argumentos obrigatórios)
   - ✅ Contexto OK (não precisa report_id)
   - ✅ Não é ação sensível
  ↓
4. Executa: obter_dashboard_hoje()
  ↓
5. Retorna resultado
```

---

## ⚠️ Casos de Erro

```
Usuário: "filtre os DMD"
  ↓
IA gera: buscar_secao_relatorio_salvo(secao="processos_chegando", categoria="DMD")
  ↓
Gate valida:
   - ✅ Contrato OK
   - ❌ Contexto: "Nenhum relatório ativo encontrado"
  ↓
Retorna: "❌ Não há relatório ativo. Gere um relatório primeiro (ex: 'o que temos pra hoje?')"
```
