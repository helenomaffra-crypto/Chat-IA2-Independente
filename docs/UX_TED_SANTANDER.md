# 🎨 UX/UI: Como TED Funciona na Interface

**Data:** 12/01/2026  
**Objetivo:** Explicar como o usuário vai interagir com TED na interface de chat

---

## 🎯 Princípio: Conversação Natural

A funcionalidade de TED funciona **100% via chat**, seguindo o mesmo padrão das outras funcionalidades (extratos, saldos, etc.).

**Não há formulários, não há botões especiais** - apenas conversação natural com o mAIke.

---

## 💬 Fluxo Completo na UI

### Cenário 1: Fazer TED Simples

```
👤 Usuário digita:
"fazer ted de 100 reais para conta 1234 agencia 5678 banco 001"

🤖 mAIke processa:
1. IA detecta intenção de fazer TED
2. Chama tool: iniciar_ted_santander
3. Sistema valida dados e inicia TED
4. Retorna transfer_id

🤖 mAIke responde:
✅ TED Iniciada com Sucesso!

ID da Transferência: ted_123456
Valor: R$ 100,00
Destinatário: [nome se disponível]
Status: PENDING_VALIDATION

💡 Próximo passo: Use 'efetivar ted ted_123456' para confirmar e autorizar a transferência.
```

**Usuário confirma:**
```
👤 Usuário digita:
"efetivar ted ted_123456"

🤖 mAIke processa:
1. IA detecta intenção de efetivar
2. Chama tool: efetivar_ted_santander
3. Sistema confirma e autoriza TED
4. TED é executada automaticamente

🤖 mAIke responde:
✅ TED Efetivada com Sucesso!

ID da Transferência: ted_123456
Status: AUTHORIZED

💡 A transferência foi autorizada e será processada.
```

---

### Cenário 2: TED com Mais Detalhes

```
👤 Usuário digita:
"transferir 500 reais para joão silva cpf 12345678901 conta 1234 agencia 5678 banco 001"

🤖 mAIke processa:
1. IA extrai informações:
   - Valor: 500
   - Nome: João Silva
   - CPF: 12345678901
   - Conta destino: 1234
   - Agência destino: 5678
   - Banco: 001 (Banco do Brasil)

2. Se faltar informação, IA pergunta:
   "Preciso da agência e conta origem. Qual agência e conta você quer usar?"

3. Chama tool: iniciar_ted_santander
4. Retorna transfer_id

🤖 mAIke responde:
✅ TED Iniciada com Sucesso!

ID da Transferência: ted_789012
Valor: R$ 500,00
Destinatário: João Silva
CPF: 123.456.789-01
Banco Destino: Banco do Brasil (001)
Ag. 5678 / C/C 1234
Status: PENDING_VALIDATION

💡 Próximo passo: Use 'efetivar ted ted_789012' para confirmar.
```

---

### Cenário 3: Fluxo Automático (Iniciar + Efetivar)

```
👤 Usuário digita:
"fazer ted de 200 reais para conta 9999 agencia 1111 banco 033 e já confirmar"

🤖 mAIke processa:
1. IA detecta "fazer ted" + "já confirmar"
2. Chama tool: iniciar_ted_santander
3. Obtém transfer_id
4. Automaticamente chama: efetivar_ted_santander
5. TED é executada completamente

🤖 mAIke responde:
✅ TED Executada com Sucesso!

ID da Transferência: ted_345678
Valor: R$ 200,00
Status: AUTHORIZED

💡 A transferência foi autorizada e será processada.
```

---

## 🎨 Visualização na UI

### Interface de Chat (Estilo WhatsApp)

```
┌─────────────────────────────────────┐
│ 🤖 mAIke                    ⚙️      │
├─────────────────────────────────────┤
│                                     │
│  👤 Você                            │
│  fazer ted de 100 reais para...     │
│  14:30                              │
│                                     │
│              🤖 mAIke               │
│  ✅ TED Iniciada com Sucesso!      │
│                                     │
│  ID: ted_123456                    │
│  Valor: R$ 100,00                  │
│  Status: PENDING_VALIDATION         │
│                                     │
│  💡 Próximo passo: Use 'efetivar   │
│  ted ted_123456' para confirmar.   │
│  14:31                              │
│                                     │
│  👤 Você                            │
│  efetivar ted ted_123456           │
│  14:32                              │
│                                     │
│              🤖 mAIke               │
│  ✅ TED Efetivada com Sucesso!     │
│                                     │
│  ID: ted_123456                    │
│  Status: AUTHORIZED                │
│                                     │
│  💡 A transferência foi autorizada │
│  e será processada.                │
│  14:32                              │
│                                     │
├─────────────────────────────────────┤
│ Digite sua mensagem...        [➤]  │
└─────────────────────────────────────┘
```

---

## 🔄 Fluxo Técnico Detalhado

### 1. Usuário Digita Mensagem

```
Frontend (chat-ia-isolado.html)
  ↓
enviarMensagemChat()
  ↓
POST /api/chat
  Body: { mensagem: "fazer ted de 100 reais..." }
```

### 2. Backend Processa

```
app.py → /api/chat
  ↓
ChatService.processar_mensagem()
  ↓
PrecheckService (detecta intenção?)
  ↓
MessageProcessingService
  ↓
IA (GPT-4o) analisa mensagem
  ↓
IA decide: chamar iniciar_ted_santander
  ↓
ToolRouter → SantanderAgent
  ↓
SantanderAgent._iniciar_ted()
  ↓
SantanderPaymentsService.iniciar_ted()
  ↓
SantanderPaymentsAPI.iniciar_ted()
  ↓
POST /management_payments_partners/v1/workspaces/{id}/transfer
```

### 3. Resposta Formatada

```
SantanderPaymentsService retorna:
{
  'sucesso': True,
  'resposta': '✅ TED Iniciada com Sucesso!\n\nID: ted_123456\n...',
  'dados': {
    'transfer_id': 'ted_123456',
    'ted': {...}
  }
}
  ↓
ChatService formata resposta
  ↓
Retorna JSON para frontend
```

### 4. Frontend Exibe

```
Frontend recebe JSON
  ↓
adicionarMensagemChat('mAIke', resposta)
  ↓
Exibe no chat (estilo WhatsApp)
```

---

## 🎯 Exemplos de Comandos que Funcionam

### Comandos Simples

```
✅ "fazer ted de 100 reais para conta 1234 agencia 5678 banco 001"
✅ "transferir 500 para joão silva cpf 12345678901 conta 1234 agencia 5678"
✅ "ted de 200 reais para conta 9999 banco 033"
✅ "enviar 1000 reais via ted para conta 1111 agencia 2222 banco 001"
```

### Comandos com Confirmação

```
✅ "fazer ted de 100 reais para conta 1234 e já confirmar"
✅ "transferir 500 para joão e efetivar"
✅ "ted de 200 reais para conta 9999 e autorizar"
```

### Comandos de Consulta

```
✅ "consultar ted ted_123456"
✅ "status da ted ted_123456"
✅ "como está a transferência ted_123456"
```

### Comandos de Listagem

```
✅ "listar teds de janeiro"
✅ "conciliação de pagamentos"
✅ "todas as teds do mês"
✅ "teds pagas hoje"
```

### Comandos de Workspace

```
✅ "listar workspaces"
✅ "criar workspace agencia 3003 conta 000130827180"
✅ "ver workspaces disponíveis"
```

---

## ⚠️ Tratamento de Erros na UI

### Erro: Workspace Não Configurado

```
👤 "fazer ted de 100 reais para conta 1234"

🤖 mAIke:
❌ Workspace não encontrado.

💡 Configure SANTANDER_WORKSPACE_ID no .env ou crie um workspace primeiro.

Você pode criar um workspace com:
"criar workspace santander agencia 3003 conta 000130827180"
```

### Erro: Dados Faltando

```
👤 "fazer ted de 100 reais"

🤖 mAIke:
❌ Dados do destino são obrigatórios.

Preciso de:
- Banco destino (ex: 001 para BB, 033 para Santander)
- Agência destino
- Conta destino
- Nome do destinatário
- CPF/CNPJ do destinatário

Exemplo: "fazer ted de 100 reais para joão silva cpf 12345678901 conta 1234 agencia 5678 banco 001"
```

### Erro: Saldo Insuficiente

```
👤 "fazer ted de 10000 reais para conta 1234"

🤖 mAIke:
❌ Erro ao iniciar TED: Saldo insuficiente na conta origem.

💡 Verifique o saldo disponível com "saldo santander"
```

---

## 🎨 Melhorias Futuras (Opcional)

### 1. Confirmação Visual (Opcional)

Se quiser adicionar confirmação visual antes de efetivar:

```
👤 "fazer ted de 100 reais para conta 1234"

🤖 mAIke:
✅ TED Iniciada!

ID: ted_123456
Valor: R$ 100,00
Destinatário: João Silva
Banco: Banco do Brasil (001)
Ag. 5678 / C/C 1234

[✅ Confirmar e Efetivar] [❌ Cancelar]
```

**Mas isso é opcional** - o fluxo atual já funciona bem com comandos de texto.

### 2. Histórico de TEDs

```
👤 "minhas teds de hoje"

🤖 mAIke:
📋 TEDs de Hoje (12/01/2026)

1. ted_123456 - R$ 100,00 - João Silva
   Status: AUTHORIZED ✅
   Hora: 14:30

2. ted_789012 - R$ 500,00 - Maria Santos
   Status: PAYED ✅
   Hora: 15:45

Total: R$ 600,00
```

---

## 📋 Resumo: Como Funciona na UI

### ✅ O Que o Usuário Faz

1. **Digita comando natural** no chat:
   - "fazer ted de 100 reais para conta 1234..."
   - "transferir 500 para joão..."

2. **mAIke processa automaticamente:**
   - IA entende a intenção
   - Extrai dados (valor, conta, nome, etc.)
   - Chama API do Santander
   - Retorna resposta formatada

3. **Usuário vê resultado no chat:**
   - Status da TED
   - ID da transferência
   - Próximos passos (se necessário)

### ✅ Características

- **100% via chat** (sem formulários)
- **Linguagem natural** (não precisa decorar comandos)
- **Respostas claras** (formatação amigável)
- **Tratamento de erros** (mensagens explicativas)
- **Fluxo em 2 etapas** (iniciar → efetivar) ou automático

### ⚠️ Importante

- **Não há QR Code** (vai direto pela API)
- **Não há confirmação manual** (automatizado)
- **Pode fazer tudo via chat** (workspace, iniciar, efetivar, consultar)

---

## 🎯 Exemplo Completo de Sessão

```
👤 "o que temos pra hoje?"
🤖 [Mostra dashboard do dia]

👤 "fazer ted de 1000 reais para conta 1234 agencia 5678 banco 001 nome joão silva cpf 12345678901"
🤖 ✅ TED Iniciada com Sucesso!
   ID: ted_123456
   Status: PENDING_VALIDATION
   💡 Próximo passo: Use 'efetivar ted ted_123456'

👤 "efetivar ted ted_123456"
🤖 ✅ TED Efetivada com Sucesso!
   Status: AUTHORIZED
   💡 A transferência foi autorizada e será processada.

👤 "consultar ted ted_123456"
🤖 📋 Consulta de TED
   ID: ted_123456
   Status: AUTHORIZED
   Valor: R$ 1.000,00
   Destinatário: João Silva
   Banco: Banco do Brasil (001)
   Ag. 5678 / C/C 1234

👤 "listar teds de hoje"
🤖 📋 Lista de TEDs
   Período: 12/01/2026
   Total: 1 TED(s)
   
   1. ted_123456
      Status: AUTHORIZED ✅
      Valor: R$ 1.000,00
      Destino: João Silva
```

---

**Última atualização:** 12/01/2026
