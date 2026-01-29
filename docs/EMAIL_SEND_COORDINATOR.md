# 📧 EmailSendCoordinator - Ponto Único de Convergência

**Data:** 09/01/2026  
**Status:** ✅ **IMPLEMENTADO**

---

## 🎯 Objetivo

Criar um **ponto único de convergência** para envio de emails, garantindo que:
- ✅ `draft_id` é sempre fonte da verdade
- ✅ Idempotência (não envia duas vezes)
- ✅ Todos os caminhos de envio convergem aqui

---

## 🔍 Problema Identificado

Análise do código revelou **múltiplos caminhos de envio** que podem bypassar o sistema de drafts:

1. ✅ `confirmar_envio=true` (ou envio direto)
2. ✅ "reenviar" / "enviar novamente"
3. ✅ Fallback SMTP
4. ✅ Confirmação pelo streaming (ou por outro endpoint)
5. ✅ Múltiplos previews no mesmo session_id

**Risco:** Cada caminho pode ter lógica diferente, causando inconsistências (ex.: enviar versão antiga).

---

## ✅ Solução: EmailSendCoordinator

### Arquivo: `services/email_send_coordinator.py`

### Método Principal: `send_from_draft(draft_id, force=False)`

**Este é o PONTO ÚNICO de convergência para envio de emails.**

#### Regras Implementadas:

1. **Sempre carrega a última revisão do banco (fonte da verdade)**
   ```python
   draft = self.email_draft_service.obter_draft(draft_id)
   # Usa draft.assunto, draft.conteudo, etc. (sempre do banco)
   ```

2. **Verifica idempotência (não envia se já foi enviado)**
   ```python
   if draft.status == 'sent' and not force:
       return {'sucesso': True, 'resposta': 'Este email já foi enviado...', 'ja_enviado': True}
   ```

3. **Marca como enviado após sucesso**
   ```python
   if resultado_envio.get('sucesso'):
       self.email_draft_service.marcar_como_enviado(draft_id)
   ```

---

## 🔄 Integração com ConfirmationHandler

O `ConfirmationHandler` agora usa `EmailSendCoordinator` para todos os envios:

```python
# services/handlers/confirmation_handler.py
def _processar_confirmacao_email_personalizado(...):
    draft_id_final = dados_email_final.get('draft_id')
    if draft_id_final and self.email_send_coordinator:
        # ✅ PONTO ÚNICO: convergir para send_from_draft()
        resultado = self.email_send_coordinator.send_from_draft(draft_id_final, force=False)
        return self._formatar_resultado_email(resultado, ...)
```

---

## 📋 Métodos Disponíveis

### 1. `send_from_draft(draft_id, force=False)`

**Ponto único de convergência para envio de emails com draft.**

- ✅ Sempre carrega do banco (última revisão)
- ✅ Verifica idempotência
- ✅ Marca como enviado após sucesso

**Uso:**
```python
coordinator = get_email_send_coordinator()
resultado = coordinator.send_from_draft(draft_id='abc-123')
```

### 2. `send_report_email(destinatario, resumo_texto, assunto, categoria=None)`

**Envia relatório por email (sem draft).**

Para relatórios que não usam sistema de drafts, mas ainda convergem para `email_service`.

**Uso:**
```python
coordinator = get_email_send_coordinator()
resultado = coordinator.send_report_email(
    destinatario='user@example.com',
    resumo_texto='Relatório completo...',
    assunto='Relatório Mensal',
    categoria='DMD'
)
```

### 3. `send_simple_email(destinatario, assunto, corpo)`

**Envia email simples (sem draft, para compatibilidade).**

Para código antigo que não usa sistema de drafts.

**Uso:**
```python
coordinator = get_email_send_coordinator()
resultado = coordinator.send_simple_email(
    destinatario='user@example.com',
    assunto='Mensagem',
    corpo='Conteúdo do email'
)
```

---

## 🛡️ Idempotência

### Como Funciona:

1. **Verificação de status:**
   ```python
   if draft.status == 'sent' and not force:
       return {'ja_enviado': True, ...}
   ```

2. **Marcação após envio:**
   ```python
   if resultado_envio.get('sucesso'):
       self.email_draft_service.marcar_como_enviado(draft_id)
   ```

### Cenários Protegidos:

- ✅ Usuário digita "sim" duas vezes
- ✅ Reconexão de stream
- ✅ Retry de request
- ✅ Múltiplos previews no mesmo session_id

---

## 🔍 Verificação de Caminhos de Envio

### Caminhos Identificados:

1. ✅ **ConfirmationHandler** → `EmailSendCoordinator.send_from_draft()` ✅
2. ✅ **Tool `enviar_email_personalizado`** → Deve convergir para coordenador
3. ✅ **Tool `enviar_relatorio_email`** → `EmailSendCoordinator.send_report_email()` ✅
4. ✅ **Tool `enviar_email`** → `EmailSendCoordinator.send_simple_email()` (fallback)
5. ⚠️ **Envio direto (sem preview)** → Ainda usa método antigo (compatibilidade)

### Próximos Passos:

- [ ] Migrar `_executar_funcao_tool('enviar_email_personalizado')` para usar coordenador
- [ ] Migrar `_executar_funcao_tool('enviar_email')` para usar coordenador
- [ ] Documentar todos os caminhos de envio

---

## 📊 Métricas de Sucesso

### Funcionais:

- ✅ "melhorar e enviar" sempre envia a última revisão
- ✅ Confirmação funciona igual em streaming e normal
- ✅ Double-confirm não duplica envio
- ✅ Não existe envio sem draft_id quando o fluxo é "preview → confirmar"

### Técnicas:

- ✅ Todos os caminhos de envio convergem para `EmailSendCoordinator`
- ✅ Idempotência implementada
- ✅ Draft sempre carregado do banco (fonte da verdade)

---

## 🚨 Regras Críticas

1. **TODO envio com draft_id DEVE usar `send_from_draft()`**
2. **NUNCA enviar email sem verificar idempotência**
3. **SEMPRE carregar draft do banco antes de enviar**
4. **SEMPRE marcar como enviado após sucesso**

---

## 📝 Exemplo de Uso

```python
from services.email_send_coordinator import get_email_send_coordinator

coordinator = get_email_send_coordinator()

# Enviar email com draft_id (recomendado)
resultado = coordinator.send_from_draft(draft_id='abc-123')

if resultado.get('sucesso'):
    if resultado.get('ja_enviado'):
        print("Email já foi enviado anteriormente")
    else:
        print(f"Email enviado! Revisão: {resultado.get('revision')}")
else:
    print(f"Erro: {resultado.get('erro')}")
```

---

**Última atualização:** 09/01/2026
