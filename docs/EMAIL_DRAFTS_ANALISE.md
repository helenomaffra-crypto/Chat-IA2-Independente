# 📧 Análise: Sistema de Drafts de Email vs Solução Atual

**Data:** 09/01/2026  
**Status:** ✅ **IMPLEMENTADO E TESTADO** - Sistema de drafts funcionando corretamente

---

## 🐛 Problema Identificado

### Sintoma
Quando o usuário pede para "melhorar este email":
1. ✅ A IA mostra uma versão melhorada no chat
2. ❌ O sistema **NÃO atualiza** o estado `ultima_resposta_aguardando_email`
3. ❌ Quando o usuário confirma ("pode enviar"), o sistema envia o **email antigo** (não o melhorado)

### Exemplo Real
```
Usuário: "mande um email pra helenomaffra@gmail.com avisando que não vou poder ir na reunião hoje das 16:00"
mAIke: [Preview do Email - versão 1, simples]
Usuário: "melhore este email"
mAIke: [Mostra versão melhorada, formal, assinada "Guilherme"]
Usuário: "pode enviar"
mAIke: [❌ ENVIA A VERSÃO 1, NÃO A MELHORADA]
```

### Causa Raiz (Análise ChatGPT)
O sistema tem **dois "mundos" separados**:
- **Chat (texto)**: O que a IA escreve e mostra ao usuário
- **Estado (variáveis)**: `ultima_resposta_aguardando_email` usado pela tool de envio

Quando o usuário pede "melhore este email":
- ✅ O **chat** é atualizado (mostra versão melhorada)
- ❌ O **estado** NÃO é atualizado (continua com versão antiga)
- ❌ Na confirmação, a tool usa o **estado antigo**

---

## 🔧 Solução Atual (Implementada - Temporária)

### O que foi feito
1. **Detecção de pedido de melhoria**: Sistema detecta "melhore", "elabore", etc.
2. **Extração via regex**: Tenta extrair email melhorado da resposta da IA usando regex
3. **Atualização do estado**: Se conseguir extrair, atualiza `ultima_resposta_aguardando_email`

### Código
```python
# services/chat_service.py (linhas ~7855-7889)
if ultima_resposta_aguardando_email and dados_email_para_enviar and eh_pedido_melhorar_email:
    email_refinado = self._extrair_email_da_resposta_ia(resposta_ia, dados_email_para_enviar)
    if email_refinado:
        dados_email_para_enviar['assunto'] = email_refinado.get('assunto')
        dados_email_para_enviar['conteudo'] = email_refinado.get('conteudo')
        self.ultima_resposta_aguardando_email = dados_email_para_enviar
```

### Limitações
- ⚠️ **Frágil**: Depende de regex para extrair email da resposta da IA
- ⚠️ **Pode falhar**: Se a IA formatar diferente, não extrai corretamente
- ⚠️ **Sem histórico**: Não guarda versões anteriores
- ⚠️ **Sem rastreabilidade**: Não sabe qual versão está enviando

---

## 🎯 Solução Robusta: Sistema de Drafts (Proposta)

### Conceito
Tratar email como um **objeto versionado** com ID único:

```python
EmailDraft:
    draft_id: str          # "email_1739"
    to: List[str]          # ["helenomaffra@gmail.com"]
    subject: str           # "Ausência na reunião..."
    body: str              # "Prezado Heleno..."
    revision: int          # 1, 2, 3...
    status: str            # "draft" | "ready_to_send" | "sent"
    created_at: datetime
    updated_at: datetime
    session_id: str
```

### Fluxo Proposto

```
1. Usuário: "mande um email..."
   → Sistema: create_draft(...) → draft_id = "email_1739", revision = 1
   → IA: Preview (rev 1) + "confirme"

2. Usuário: "melhore"
   → Sistema: revise_draft(draft_id="email_1739", instruction="mais formal")
   → IA: Gera nova versão
   → Sistema: Salva como revision = 2
   → IA: Preview (rev 2) + "confirme"

3. Usuário: "pode enviar"
   → Sistema: send_email_draft(draft_id="email_1739")
   → Sistema: SEMPRE envia a última revisão (rev 2)
```

### Vantagens
- ✅ **Robusto**: Não depende de regex - estado sempre atualizado
- ✅ **Rastreável**: Histórico completo de versões
- ✅ **Confiável**: Sempre envia a última versão
- ✅ **Extensível**: Pode adicionar mais funcionalidades (comparar versões, restaurar, etc.)
- ✅ **Resolve outros problemas**: Referenciar emails por ID, não por texto

### Desvantagens
- ⚠️ **Mais complexo**: Requer nova tabela, novas funções
- ⚠️ **Mudanças maiores**: Pode afetar código existente
- ⚠️ **Mais tempo**: Implementação mais demorada

---

## 📊 Comparação

| Aspecto | Solução Atual (Regex) | Sistema de Drafts |
|---------|----------------------|-------------------|
| **Confiabilidade** | ⚠️ 70-80% (depende de regex) | ✅ 100% (estado sempre correto) |
| **Complexidade** | ✅ Baixa (já implementado) | ⚠️ Média (requer nova estrutura) |
| **Rastreabilidade** | ❌ Nenhuma | ✅ Histórico completo |
| **Manutenibilidade** | ⚠️ Frágil (regex pode quebrar) | ✅ Robusto (estado estruturado) |
| **Tempo de implementação** | ✅ Já feito | ⚠️ 2-3 horas |
| **Risco de quebrar** | ✅ Baixo (já está funcionando) | ⚠️ Médio (mudanças maiores) |

---

## 💡 Recomendação

### Opção 1: Implementar Drafts Agora (Recomendado)
**Por quê:**
1. ✅ ChatGPT confirmou que é a solução correta
2. ✅ Problema é crítico (envia email errado)
3. ✅ Solução atual é frágil (regex pode falhar)
4. ✅ Drafts resolvem outros problemas também

**Plano:**
1. Criar tabela `email_drafts` no SQLite
2. Criar `EmailDraftService` para gerenciar drafts
3. Adicionar `draft_id` ao estado `ultima_resposta_aguardando_email`
4. Criar tool `melhorar_email_draft(draft_id, instrucoes)`
5. Modificar `enviar_email_personalizado` para usar `draft_id`
6. Testar com casos reais

**Tempo estimado:** 2-3 horas  
**Risco:** Médio (mudanças em código crítico)

### Opção 2: Melhorar Solução Atual
**Por quê:**
- Mais rápido
- Menos risco
- Funciona para maioria dos casos

**Plano:**
1. Melhorar regex de extração
2. Adicionar validação: se não extrair, perguntar ao usuário
3. Adicionar logging para debug

**Tempo estimado:** 30 minutos  
**Risco:** Baixo (apenas melhorias incrementais)

---

## 🎯 Decisão

**Status:** ⏳ **AGUARDANDO APROVAÇÃO DO USUÁRIO**

**Recomendação:** Implementar **Sistema de Drafts (Opção 1)** porque:
- Problema é crítico (envia email errado)
- Solução atual é frágil
- Drafts são mais robustos e extensíveis
- Resolve o problema de forma definitiva

---

## 📝 Plano de Implementação (Se Aprovado)

### Fase 1: Estrutura de Dados ✅ **COMPLETO**
- [x] Criar tabela `email_drafts` no SQLite
- [x] Criar classe `EmailDraft` (dataclass)
- [x] Criar `EmailDraftService` com métodos:
  - `criar_draft(to, subject, body, session_id) → draft_id`
  - `revisar_draft(draft_id, subject, body) → nova_revision`
  - `obter_draft(draft_id) → EmailDraft`
  - `listar_drafts(session_id) → List[EmailDraft]`

### Fase 2: Integração com Tools ✅ **COMPLETO**
- [x] Modificar `enviar_email_personalizado` para criar draft
- [x] Criar tool `melhorar_email_draft(draft_id, instrucoes)`
- [x] Modificar confirmação para usar `draft_id`
- [x] Atualizar `ultima_resposta_aguardando_email` para incluir `draft_id`

### Fase 3: Fluxo de Melhoria ✅ **COMPLETO**
- [x] Quando usuário pede "melhore", criar nova revisão no draft
- [x] IA retorna novo `subject` e `body`
- [x] Sistema salva como nova revisão
- [x] Mostrar preview atualizado

### Fase 4: Testes ✅ **COMPLETO E VALIDADO**
- [x] Testar criação de draft
- [x] Testar revisão de draft
- [x] Testar envio de última versão
- [x] Testar com múltiplas revisões
- [x] Testar casos de erro
- [x] Testar fluxo antigo (relatórios) - funcionando corretamente

---

## 🔗 Arquivos Relacionados

- `services/chat_service.py` - Lógica principal de processamento
- `services/email_precheck_service.py` - Detecção de comandos de email
- `db_manager.py` - Gerenciamento de banco SQLite
- `services/tool_definitions.py` - Definições de tools para IA

---

## 📚 Referências

- Análise do ChatGPT sobre o problema
- Conversa original no chat (09/01/2026)
- Código atual em `services/chat_service.py` (linhas ~7855-7889)

---

---

## ✅ STATUS FINAL

**Implementação:** ✅ **COMPLETA**  
**Testes:** ✅ **VALIDADOS**  
**Data de conclusão:** 09/01/2026

### O que foi implementado:
- ✅ Sistema completo de drafts com versões
- ✅ Integração opcional (código antigo continua funcionando)
- ✅ Detecção melhorada de confirmação ("envie esse email", etc.)
- ✅ Fluxo completo testado: criar → melhorar → enviar
- ✅ Fluxo antigo (relatórios) validado e funcionando

### ✅ Implementação Completa (09/01/2026):

**Opção 1: Sistema de Drafts** ✅ **IMPLEMENTADO**
- ✅ Criar tabela `email_drafts` no SQLite
- ✅ Adicionar `draft_id` ao estado
- ✅ Tool `melhorar_email_draft(draft_id, instrucoes)`
- ✅ Confirmação sempre usa última versão do draft

**Opção 2: Melhorar Solução Atual** ✅ **IMPLEMENTADO**
- ✅ Extração via regex melhorada (já existia)
- ✅ **Validação: se não extrair, perguntar ao usuário** ✅ **ADICIONADO**

**Fase 2: Perguntar Quando Não Tem Certeza** ✅ **IMPLEMENTADO**
- ✅ Regras adicionadas ao prompt builder
- ✅ Regras adicionadas às tool definitions
- ✅ Campo de destinatário atualizado

### Próximos passos (opcionais):
- [ ] Adicionar funcionalidade de comparar versões
- [ ] Adicionar funcionalidade de restaurar versão anterior
- [ ] Adicionar histórico de versões na UI
- [ ] Adicionar suporte a drafts para relatórios também

---

**Última atualização:** 09/01/2026
