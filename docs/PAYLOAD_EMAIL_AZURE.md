# 📧 Payload de Email Azure (Microsoft Graph API) e Armazenamento de Preview

**Data:** 09/01/2026  
**Status:** ✅ Documentação atual

---

## 🎯 Payload da Microsoft Graph API

### Endpoint
```
POST https://graph.microsoft.com/v1.0/users/{from_email}/sendMail
```

### Headers
```json
{
  "Authorization": "Bearer {access_token}",
  "Content-Type": "application/json"
}
```

### Payload Completo (com todos os campos opcionais)

```json
{
  "message": {
    "subject": "Assunto do Email",
    "body": {
      "contentType": "HTML",  // ou "Text"
      "content": "<html><body>Conteúdo do email em HTML</body></html>"
    },
    "toRecipients": [
      {
        "emailAddress": {
          "address": "destinatario@example.com"
        }
      }
    ],
    "ccRecipients": [  // Opcional
      {
        "emailAddress": {
          "address": "cc@example.com"
        }
      }
    ],
    "bccRecipients": [  // Opcional
      {
        "emailAddress": {
          "address": "bcc@example.com"
        }
      }
    ],
    "attachments": [  // Opcional
      {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "arquivo.pdf",
        "contentType": "application/pdf",
        "contentBytes": "base64_encoded_content"
      }
    ]
  }
}
```

### Payload Mínimo (apenas campos obrigatórios)

```json
{
  "message": {
    "subject": "Assunto do Email",
    "body": {
      "contentType": "Text",  // ou "HTML"
      "content": "Conteúdo do email em texto"
    },
    "toRecipients": [
      {
        "emailAddress": {
          "address": "destinatario@example.com"
        }
      }
    ]
  }
}
```

### Campos Esperados

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `message.subject` | string | ✅ Sim | Assunto do email |
| `message.body.contentType` | string | ✅ Sim | "HTML" ou "Text" |
| `message.body.content` | string | ✅ Sim | Conteúdo do email (HTML ou texto) |
| `message.toRecipients` | array | ✅ Sim | Lista de destinatários |
| `message.toRecipients[].emailAddress.address` | string | ✅ Sim | Email do destinatário |
| `message.ccRecipients` | array | ❌ Não | Lista de cópias |
| `message.bccRecipients` | array | ❌ Não | Lista de cópias ocultas |
| `message.attachments` | array | ❌ Não | Lista de anexos |

### Resposta de Sucesso

**Status Code:** `200` ou `202`

```json
{
  "sucesso": true,
  "mensagem_id": "Location header value (opcional)",
  "destinatarios": ["destinatario@example.com"]
}
```

### Resposta de Erro

**Status Code:** `400`, `401`, `403`, `500`, etc.

```json
{
  "sucesso": false,
  "erro": "Erro ao enviar email: {status_code} - {response_text}"
}
```

---

## 💾 Armazenamento de Preview Pendente

### Estrutura de Dados

O preview pendente é armazenado em **duas camadas**:

#### 1. **Instância do ChatService** (memória)
```python
self.ultima_resposta_aguardando_email = {
    'funcao': 'enviar_email_personalizado',  # ou 'enviar_relatorio_email' ou 'enviar_email'
    'tipo': 'email_personalizado',  # opcional
    'destinatarios': ['helenomaffra@gmail.com'],  # lista de emails
    'assunto': 'Assunto do Email',
    'conteudo': 'Conteúdo do email...',
    'cc': [],  # opcional
    'bcc': [],  # opcional
    'draft_id': 'uuid-do-draft',  # ✅ NOVO (09/01/2026): ID do draft (se criado)
    # Para enviar_relatorio_email:
    'argumentos': {...},  # argumentos originais da tool
    'resumo_texto': '...',  # texto do relatório gerado
    'destinatario': 'helenomaffra@gmail.com'  # email do destinatário
}
```

#### 2. **Resultado Interno** (retornado no response)
```python
{
    'resposta': '📧 Preview do Email...',
    'aguardando_confirmacao': True,
    'tool_calling': {
        'name': 'enviar_email_personalizado',
        'arguments': {...}
    },
    '_resultado_interno': {
        'ultima_resposta_aguardando_email': {
            # Mesma estrutura acima
        }
    }
}
```

### Tipos de Email e Estruturas

#### **enviar_email_personalizado**
```python
{
    'funcao': 'enviar_email_personalizado',
    'tipo': 'email_personalizado',
    'destinatarios': ['email1@example.com', 'email2@example.com'],
    'assunto': 'Assunto',
    'conteudo': 'Conteúdo do email...',
    'cc': ['cc@example.com'],  # opcional
    'bcc': ['bcc@example.com'],  # opcional
    'draft_id': 'uuid'  # ✅ NOVO: ID do draft (se criado)
}
```

#### **enviar_relatorio_email**
```python
{
    'funcao': 'enviar_relatorio_email',
    'argumentos': {
        'destinatario': 'helenomaffra@gmail.com',
        'tipo_relatorio': 'resumo',  # ou 'fechamento'
        'categoria': 'DMD',  # opcional
        'assunto': 'Resumo Resumo - DMD - 09/01/2026'  # gerado automaticamente
    },
    'resumo_texto': 'Texto completo do relatório gerado...',
    'destinatario': 'helenomaffra@gmail.com'
}
```

#### **enviar_email** (simples)
```python
{
    'funcao': 'enviar_email',
    'destinatario': 'helenomaffra@gmail.com',
    'assunto': 'Assunto',
    'corpo': 'Corpo do email...'
}
```

### Recuperação do Preview

O sistema tenta recuperar o preview pendente na seguinte ordem:

1. **Instância do ChatService** (mais confiável)
   ```python
   if hasattr(self, 'ultima_resposta_aguardando_email') and self.ultima_resposta_aguardando_email:
       dados_email_para_enviar = self.ultima_resposta_aguardando_email
   ```

2. **Resultado Interno do Histórico**
   ```python
   ultimo_resultado = historico[-1].get('_resultado_interno', {})
   if 'ultima_resposta_aguardando_email' in ultimo_resultado:
       dados_email_para_enviar = ultimo_resultado.get('ultima_resposta_aguardando_email')
   ```

3. **Fallback: Detecção por Texto**
   ```python
   if 'preview do email' in ultima_resposta.lower() or 'confirme para enviar' in ultima_resposta.lower():
       # Tentar recuperar do resultado interno
   ```

### Sistema de Drafts (NOVO - 09/01/2026)

Quando um preview é criado, o sistema **opcionalmente** cria um draft no banco de dados:

```python
# Tabela: email_drafts (SQLite)
{
    'id': 1,
    'draft_id': 'uuid-gerado',
    'session_id': 'session-123',
    'destinatarios': '["helenomaffra@gmail.com"]',  # JSON
    'cc': '[]',  # JSON
    'bcc': '[]',  # JSON
    'assunto': 'Assunto do Email',
    'conteudo': 'Conteúdo do email...',
    'funcao_email': 'enviar_email_personalizado',
    'revision': 1,
    'status': 'draft',  # 'draft', 'ready_to_send', 'sent'
    'criado_em': '2026-01-09 15:00:00',
    'atualizado_em': '2026-01-09 15:00:00'
}
```

**Vantagens:**
- ✅ Suporta múltiplas revisões (quando usuário pede "melhore")
- ✅ Rastreável (histórico de versões)
- ✅ Mais confiável que regex para extração
- ✅ Sempre envia a última versão na confirmação

**Uso na Confirmação:**
```python
# Se tem draft_id, buscar última versão do draft
if draft_id:
    draft = draft_service.obter_draft(draft_id)
    # Usar draft.assunto e draft.conteudo (sempre última revisão)
```

---

## 📝 Exemplo Completo de Fluxo

### 1. Criação do Preview

**Tool Call:**
```json
{
  "name": "enviar_email_personalizado",
  "arguments": {
    "destinatarios": ["helenomaffra@gmail.com"],
    "assunto": "Atraso na reunião",
    "conteudo": "Olá, vou chegar atrasado...",
    "confirmar_envio": false
  }
}
```

**Estado Armazenado:**
```python
self.ultima_resposta_aguardando_email = {
    'funcao': 'enviar_email_personalizado',
    'destinatarios': ['helenomaffra@gmail.com'],
    'assunto': 'Atraso na reunião',
    'conteudo': 'Olá, vou chegar atrasado...',
    'draft_id': 'abc-123-def-456'  # criado opcionalmente
}
```

### 2. Melhoria do Email

**Usuário:** "melhore esse email de uma forma mais elegante"

**Sistema:**
- Detecta `eh_pedido_melhorar_email = True`
- IA gera email melhorado
- Extrai email da resposta da IA
- **Atualiza draft** (cria nova revisão):
  ```python
  draft_service.revisar_draft(
      draft_id='abc-123-def-456',
      assunto='Ausência na reunião das 16h de hoje',
      conteudo='Prezado Heleno, ...'
  )
  ```
- **Atualiza estado:**
  ```python
  self.ultima_resposta_aguardando_email['assunto'] = 'Ausência na reunião das 16h de hoje'
  self.ultima_resposta_aguardando_email['conteudo'] = 'Prezado Heleno, ...'
  ```

### 3. Confirmação e Envio

**Usuário:** "pode enviar"

**Sistema:**
- Detecta confirmação
- **Se tem draft_id:** Busca última versão do draft
- **Se não tem draft_id:** Usa dados do estado
- Monta payload para Microsoft Graph API:
  ```json
  {
    "message": {
      "subject": "Ausência na reunião das 16h de hoje",
      "body": {
        "contentType": "Text",
        "content": "Prezado Heleno, ..."
      },
      "toRecipients": [
        {
          "emailAddress": {
            "address": "helenomaffra@gmail.com"
          }
        }
      ]
    }
  }
  ```
- Envia via `POST /users/{from_email}/sendMail`
- Marca draft como `sent` (se existir)
- Limpa estado: `self.ultima_resposta_aguardando_email = None`

---

## 🔍 Arquivos Relacionados

- `services/email_service.py` - Implementação do envio via Microsoft Graph API
- `services/chat_service.py` - Gerenciamento de preview pendente e confirmação
- `services/email_draft_service.py` - Sistema de drafts (versões de email)
- `db_manager.py` - Tabela `email_drafts` no SQLite

---

## ⚠️ Notas Importantes

1. **Token de Acesso:** O sistema usa OAuth 2.0 para obter token do Microsoft Graph API
2. **Fallback:** Se Microsoft Graph API falhar, o sistema tenta SMTP
3. **Preview Sempre Mostrado:** O sistema **sempre** mostra preview antes de enviar (exceto se `confirmar_envio=true` explicitamente)
4. **Draft Opcional:** O sistema de drafts é opcional - se falhar ao criar, continua funcionando normalmente
5. **Estado em Memória:** O preview pendente é armazenado em memória (instância do ChatService) e também no resultado interno retornado

---

**Última atualização:** 09/01/2026
