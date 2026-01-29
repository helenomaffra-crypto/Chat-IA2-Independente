# 🐛 Bugs de Email - Pendentes de Correção (Após Refatoramento)

**Data:** 09/01/2026  
**Status:** 📋 **DOCUMENTADO** - Será corrigido após completar Passos 3.5 e 4 do refatoramento

---

## 📋 Estratégia

**Decisão:** Completar refatoramento (Passos 3.5 e 4) **ANTES** de corrigir bugs de email.

**Motivo:**
- Passo 4 vai extrair `email_improvement_handler.py` que vai mexer diretamente na lógica de email
- Corrigir agora = retrabalho depois (ter que corrigir de novo após extração)
- Melhor: corrigir uma vez na arquitetura final

**Próximos passos:**
1. ✅ Documentar bugs conhecidos (este documento)
2. ⏳ Completar Passo 3.5 (construção de prompt e tool calls)
3. ⏳ Completar Passo 4 (extrair `email_improvement_handler.py`)
4. 🔧 Revisar sistema de email na nova arquitetura
5. 🔧 Corrigir todos os bugs de uma vez

---

## 🐛 Bugs Conhecidos

### **Bug #1: Email Original Enviado Após Melhorar Email**

**Status:** ⚠️ **PENDENTE** (parcialmente corrigido, mas ainda ocorre)

**Sintoma:**
1. Usuário pede: "mande um email para X sobre Y"
2. Sistema gera preview (draft revision 1 criado ✅)
3. Usuário pede: "melhore esse email"
4. Sistema mostra versão melhorada no chat
5. Usuário confirma: "pode enviar"
6. **❌ Sistema envia email ORIGINAL (revision 1), não o melhorado**

**Análise dos Logs (09/01/2026 18:20):**
```
✅ Draft criado: email_1767993584684 (revision 1)
✅ Preview detectado
❌ NÃO há logs de:
   - Extração do email melhorado
   - Atualização do draft no banco (nova revision)
   - Criação de revision 2
✅ Confirmação usa revision 1 (original)
```

**Causa Raiz Identificada:**
- `processar_mensagem_stream()` **NÃO estava processando melhorias de email**
- ✅ **CORRIGIDO PARCIALMENTE (09/01/2026):** Adicionada lógica de melhorar email no streaming
- ⚠️ **MAS:** Ainda pode não estar funcionando porque:
  - Extração do email melhorado pode estar falhando (`_extrair_email_da_resposta_ia`)
  - Draft não está sendo atualizado corretamente
  - Estado não está sendo salvo após melhoria

**Arquivos Afetados:**
- `services/chat_service.py` - Método `processar_mensagem_stream()` (linhas ~9356-9376)
- `services/chat_service.py` - Método `_extrair_email_da_resposta_ia()` (linhas ~8477-8800)
- `services/email_draft_service.py` - Método `revisar_draft()` (linhas ~105-150)

**Correção Aplicada (Parcial):**
- ✅ Detecção de "melhorar email" adicionada no streaming
- ✅ Processamento após streaming terminar
- ✅ Tentativa de criar novo draft se não existe
- ⚠️ **MAS:** Pode não estar funcionando porque extração está falhando

**Correção Planejada (Após Refatoramento):**
- Extrair lógica de melhorar email para `EmailImprovementHandler`
- Usar JSON estruturado da IA em vez de regex frágil
- Garantir que draft sempre seja atualizado antes de reemitir preview

---

### **Bug #2: Draft Não Criado Quando Email é Gerado Via Precheck**

**Status:** ✅ **CORRIGIDO** (mas pode voltar após refatoramento)

**Sintoma:**
- Email criado via `EmailPrecheckService._precheck_envio_email_livre`
- Preview é mostrado, mas `draft_id` não é criado
- Confirmação usa fallback antigo (sem draft)

**Correção Aplicada:**
- ✅ `EmailPrecheckService._precheck_envio_email_livre` agora cria draft (linhas ~1139-1159)
- ✅ `ChatService` processa `_resultado_interno` do precheck (linhas ~4150-4159)

**Risco de Regressão:**
- ⚠️ Passo 3.5 pode mudar como precheck retorna resultados
- ⚠️ Passo 4 pode extrair lógica de precheck para outro lugar

---

### **Bug #3: Email Melhorado Não Extraído Corretamente da Resposta da IA**

**Status:** ⚠️ **PENDENTE** (regex pode falhar em alguns casos)

**Sintoma:**
- IA retorna email melhorado, mas em formato não padronizado
- `_extrair_email_da_resposta_ia()` falha em extrair
- Sistema não consegue atualizar draft

**Casos Conhecidos Onde Falha:**
1. IA usa "Corpo do email:" mas "Se quiser" está na mesma linha
2. IA adiciona texto introdutório longo antes do email
3. IA não segue padrão estruturado (sem "Assunto:", sem "Corpo:")

**Correção Aplicada (Parcial):**
- ✅ Regex melhorado para detectar múltiplos padrões
- ✅ Detecção de "Assunto sugerido:" e "Corpo do email:"
- ✅ Limpeza de texto introdutório
- ⚠️ **MAS:** Regex ainda pode falhar em casos edge

**Correção Planejada (Após Refatoramento):**
- Pedir para IA retornar JSON estruturado: `{"assunto": "...", "conteudo": "..."}`
- Eliminar necessidade de regex completamente
- Implementar em `EmailImprovementHandler`

---

### **Bug #4: Estado Não Sincronizado Entre Memória e Banco**

**Status:** ⚠️ **PARCIALMENTE CORRIGIDO**

**Sintoma:**
- Draft atualizado no banco (revision 2)
- Mas `ultima_resposta_aguardando_email` em memória ainda tem revision 1
- Confirmação pode usar memória em vez de banco (se não passar por `_obter_email_para_enviar`)

**Correção Aplicada:**
- ✅ `_obter_email_para_enviar()` prioriza banco quando tem `draft_id`
- ✅ Estado atualizado após melhorar email
- ⚠️ **MAS:** Pode haver caminhos que bypassam `_obter_email_para_enviar`

**Correção Planejada (Após Refatoramento):**
- Garantir que **TODOS** os caminhos de envio usem `EmailSendCoordinator.send_from_draft()`
- Eliminar fallbacks que não passam pelo coordenador
- Validar na arquitetura final que não há caminhos paralelos

---

### **Bug #5: Email Truncado no Preview (Mas Enviado Completo)**

**Status:** ✅ **CORRIGIDO** (mas pode voltar após refatoramento)

**Sintoma:**
- Preview mostra email cortado (`[:200]...`)
- Mas email enviado está completo

**Correção Aplicada:**
- ✅ Removido truncamento de `[:200]` em `EmailSendCoordinator` (linha ~156)
- ✅ Removido truncamento em `chat_service.py` (linha ~2679)

**Risco de Regressão:**
- ⚠️ Passo 4 pode extrair formatação para `ResponseFormatter`
- ⚠️ Pode reintroduzir truncamento sem querer

---

### **Bug #6: Relatório Errado Enviado Quando Usuário Pede "envia esse relatorio"**

**Status:** ✅ **CORRIGIDO** (mas pode voltar após refatoramento)

**Sintoma:**
- Usuário pede: "fechamento do dia"
- Sistema mostra relatório de fechamento
- Usuário pede: "envia esse relatorio para X@gmail.com"
- **❌ Sistema envia relatório ERRADO (ex: "O QUE TEMOS PRA HOJE" em vez de "FECHAMENTO DO DIA")**

**Correção Aplicada:**
- ✅ `enviar_relatorio_email` detecta "esse relatorio" e busca relatório salvo
- ✅ `buscar_ultimo_relatorio` corrigido para filtrar por `tipo_relatorio` usando campo `valor`

**Risco de Regressão:**
- ⚠️ Passo 3.5 pode mudar como relatórios são gerados
- ⚠️ Passo 4 pode extrair lógica para `ReportHandler`

---

## 📍 Localizações de Código

### Arquivos Críticos para Correção (Após Refatoramento):

1. **`services/chat_service.py`**
   - Linhas ~8340-8430: Lógica de melhorar email (será movida para `EmailImprovementHandler`)
   - Linhas ~8477-8800: `_extrair_email_da_resposta_ia()` (será movida para `email_utils.py` ou eliminada)
   - Linhas ~9356-9376: Lógica de melhorar email no streaming (será unificada)

2. **`services/email_precheck_service.py`**
   - Linhas ~1139-1199: Criação de draft no precheck (verificar após Passo 3.5)

3. **`services/email_draft_service.py`**
   - Método `revisar_draft()` - Verificar se está funcionando corretamente

4. **`services/handlers/confirmation_handler.py`**
   - Linhas ~302-360: Processamento de confirmação (já usa `EmailSendCoordinator` ✅)

5. **`services/email_send_coordinator.py`**
   - Método `send_from_draft()` - Ponto único de convergência (já correto ✅)

---

## 🔧 Correções Planejadas (Após Passo 4)

### **1. Extrair EmailImprovementHandler**

**Arquivo:** `services/handlers/email_improvement_handler.py`

**Responsabilidades:**
- Detectar pedido de melhorar email
- Chamar IA para melhorar
- Extrair email melhorado (via JSON estruturado)
- Atualizar draft no banco
- Reemitir preview atualizado

**Benefícios:**
- Lógica isolada e testável
- Fácil de corrigir bugs
- Elimina duplicação entre streaming e não-streaming

---

### **2. Usar JSON Estruturado em Vez de Regex**

**Problema atual:**
- Regex frágil pode falhar em casos edge
- IA pode formatar resposta de forma não padronizada

**Solução:**
- Modificar prompt para IA retornar JSON:
  ```json
  {
    "assunto": "...",
    "conteudo": "...",
    "assinatura": "..." (opcional)
  }
  ```
- Eliminar necessidade de `_extrair_email_da_resposta_ia()` completamente

**Arquivo afetado:**
- `services/prompt_builder.py` - Adicionar regra para retornar JSON

---

### **3. Garantir Convergência Total**

**Objetivo:**
- **TODOS** os caminhos de envio devem passar por `EmailSendCoordinator.send_from_draft()`
- Eliminar qualquer fallback que bypassa o coordenador

**Verificações:**
- ✅ Confirmação via `ConfirmationHandler` → usa `EmailSendCoordinator` ✅
- ⚠️ Envio direto (se existir) → verificar se também usa coordenador
- ⚠️ Reenvio → verificar se também usa coordenador
- ⚠️ Qualquer outro caminho → mapear e garantir convergência

---

## 📝 Notas para Futura Correção

1. **Testes Golden Já Existem:**
   - `tests/test_email_flows_golden.py` - Teste `test_criar_email_melhorar_confirmar_enviar_melhorado`
   - Usar como base para validar correções

2. **Logs Importantes:**
   - Verificar logs de `[MELHORAR EMAIL]` para rastrear fluxo
   - Verificar logs de `[CONFIRMACAO]` para ver qual draft está sendo usado
   - Verificar logs de `[EMAIL_COORDINATOR]` para ver se está passando pelo coordenador

3. **Validação:**
   - Após Passo 4, executar testes golden
   - Testar fluxo completo manualmente
   - Verificar logs para garantir que draft está sendo atualizado

---

**Última atualização:** 09/01/2026 18:30
