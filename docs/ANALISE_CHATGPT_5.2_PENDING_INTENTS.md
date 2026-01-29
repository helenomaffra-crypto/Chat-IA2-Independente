# 🔍 Análise: Sugestões ChatGPT 5.2 - Refinamento Pending Intents

**Data:** 14/01/2026  
**Fonte:** ChatGPT 5.2  
**Status:** ✅ Análise completa - Implementação em andamento

---

## 📊 Status Atual vs. Sugestões

### ✅ **JÁ IMPLEMENTADO**

1. ✅ **Tabela `pending_intents`** no SQLite
2. ✅ **CRUD completo** no `PendingIntentService`
3. ✅ **Criação automática** de pending intents ao gerar previews
4. ✅ **Busca automática** quando memória está vazia
5. ✅ **Marcação como executado** após sucesso
6. ✅ **TTL de 2 horas** configurável

### ⚠️ **FALTA IMPLEMENTAR (Prioridade Alta)**

#### 1. **SQLite como Fonte da Verdade na Confirmação**
**Status:** ⚠️ **PARCIAL** - Busca pending intent, mas ainda usa memória se disponível

**Problema:**
- Atualmente: Se tem dados em memória, usa memória primeiro
- Deveria: Sempre usar SQLite como fonte da verdade, ignorar memória

**Solução:**
```python
# ANTES (atual):
if not dados_email_para_enviar and session_id:
    pending_intent = self.buscar_pending_intent(...)

# DEPOIS (correto):
# Sempre buscar do SQLite primeiro, ignorar memória
if session_id:
    pending_intent = self.buscar_pending_intent(...)
    if pending_intent:
        # Usar args_normalizados do DB como fonte da verdade
        dados_email_para_enviar = pending_intent['args_normalizados']
```

#### 2. **Idempotência: Não Executar se Status != pending**
**Status:** ❌ **NÃO IMPLEMENTADO**

**Problema:**
- Sistema não verifica se intent já foi executado antes de executar novamente
- Pode executar ação duas vezes se usuário confirmar 2x

**Solução:**
```python
# Verificar status antes de executar
if pending_intent['status'] != 'pending':
    if pending_intent['status'] == 'executed':
        return {'erro': 'JA_EXECUTADO', 'resposta': 'Esta ação já foi executada anteriormente.'}
    elif pending_intent['status'] == 'expired':
        return {'erro': 'EXPIRADO', 'resposta': 'Esta ação expirou. Gere o preview novamente.'}
```

#### 3. **Ambiguidade: Múltiplos Pending Intents**
**Status:** ❌ **NÃO IMPLEMENTADO**

**Problema:**
- Se houver email E DUIMP pendentes, sistema não sabe qual executar
- Atualmente busca apenas o último (pode ser o errado)

**Solução:**
```python
# Buscar TODOS os pending intents
intents = service.listar_pending_intents(session_id=session_id, status='pending')
if len(intents) > 1:
    # Pedir escolha ao usuário
    return {
        'erro': 'MULTIPLOS_PENDENTES',
        'resposta': f'Há {len(intents)} ações pendentes. Qual deseja executar?\n' + 
                   '\n'.join([f"- {i+1}. {intent['action_type']} ({intent['tool_name']})" 
                             for i, intent in enumerate(intents)])
    }
```

#### 4. **Cancelamento e Expiração**
**Status:** ⚠️ **PARCIAL** - Métodos existem, mas não são usados na confirmação

**Problema:**
- Sistema não detecta comando "cancelar"
- Sistema não verifica expiração antes de executar

**Solução:**
- Adicionar detecção de "cancelar" no `ConfirmationHandler`
- Verificar `expires_at` antes de executar

#### 5. **Minimizar preview_text**
**Status:** ⚠️ **PARCIAL** - Salva preview completo, mas poderia regenerar

**Problema:**
- `preview_text` pode conter dados sensíveis
- Ocupa espaço desnecessário no banco

**Solução:**
- Salvar apenas primeiros 200 chars do preview
- Regenerar preview completo dos `args_normalizados` quando necessário

---

### 📋 **PRIORIDADE MÉDIA (Futuro)**

#### 6. **Generalizar para Qualquer Tool Sensível**
**Status:** ❌ **NÃO IMPLEMENTADO**

**Solução:**
- Criar lista de `acoes_sensiveis` em `tool_definitions.py`
- Auto-criar pending intent para qualquer tool marcada como sensível

#### 7. **ToolGateService Central**
**Status:** ❌ **NÃO IMPLEMENTADO** (planejado para Fase 3)

**Solução:**
- Criar `services/tool_gate_service.py`
- Centralizar validação de contrato, resolução de contexto, preview/confirm

#### 8. **Concorrência: Lock/Upsert**
**Status:** ❌ **NÃO IMPLEMENTADO**

**Solução:**
- Usar `payload_hash` + `created_at` para detectar duplicatas
- Implementar lock por `session_id` ou upsert baseado em hash

---

## 🧪 **Golden Tests Sugeridos**

### Teste 1: Email - Criar → Melhorar → Confirmar
```
1. Criar email → pending intent criado
2. Melhorar email → pending intent atualizado (mesmo intent_id ou novo?)
3. Confirmar → envia versão mais recente
```

**Status:** ❌ **NÃO IMPLEMENTADO**

### Teste 2: Confirmar 2x Não Duplica
```
1. Confirmar ação → executado
2. Confirmar novamente → retorna "já executado"
```

**Status:** ❌ **NÃO IMPLEMENTADO**

### Teste 3: Duas Pendências Exige Escolha
```
1. Criar email pendente
2. Criar DUIMP pendente
3. Confirmar → pede escolha
```

**Status:** ❌ **NÃO IMPLEMENTADO**

### Teste 4: Expirado Não Executa
```
1. Criar pending intent
2. Esperar expirar (ou forçar expires_at no passado)
3. Confirmar → retorna "expirou, gere preview novamente"
```

**Status:** ❌ **NÃO IMPLEMENTADO**

---

## 🎯 **Plano de Implementação**

### **Fase 1: Prioridade Alta (Agora)**

1. ✅ **SQLite como fonte da verdade** - Sempre usar DB, ignorar memória
2. ✅ **Idempotência** - Verificar status antes de executar
3. ✅ **Ambiguidade** - Detectar múltiplos intents e pedir escolha
4. ✅ **Cancelamento** - Detectar comando "cancelar"
5. ✅ **Expiração** - Verificar expires_at antes de executar
6. ✅ **Minimizar preview_text** - Salvar apenas primeiros 200 chars

### **Fase 2: Golden Tests**

1. ✅ Criar testes para todos os cenários sugeridos
2. ✅ Validar comportamento correto

### **Fase 3: Prioridade Média (Futuro)**

1. ⏳ Generalizar para qualquer tool sensível
2. ⏳ ToolGateService central
3. ⏳ Concorrência com lock/upsert

---

## 📝 **Conclusão**

**ChatGPT 5.2 tem razão:** O sistema atual funciona, mas precisa de refinamentos importantes para ser robusto em produção.

**Prioridade:** Implementar itens de Prioridade Alta primeiro, depois golden tests, depois prioridade média.
