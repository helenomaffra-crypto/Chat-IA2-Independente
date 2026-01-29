# 💬 Respondendo Dúvidas sobre TED Santander

**Data:** 12/01/2026

---

## 1️⃣ "Recebendo as chaves de produção, o resto da implementação vai ser mais fácil?"

### ✅ **SIM! Muito mais fácil!**

**Por quê?**

1. **Código já está pronto:**
   - ✅ API de Pagamentos implementada (`utils/santander_payments_api.py`)
   - ✅ Serviço de negócio implementado (`services/santander_payments_service.py`)
   - ✅ Agent integrado (`services/agents/santander_agent.py`)
   - ✅ Tools definidas (`services/tool_definitions.py`)
   - ✅ Roteamento configurado (`services/tool_router.py`)

2. **Já testado no sandbox:**
   - ✅ Criação de workspace funcionando
   - ✅ Iniciar TED funcionando
   - ✅ Efetivar TED funcionando
   - ✅ Consultar TED funcionando
   - ✅ Listar TEDs funcionando

3. **O que você precisa fazer:**
   - ⚙️ **Apenas configurar o `.env`** com as credenciais de produção
   - ⚙️ **Trocar URLs** de sandbox para produção
   - ⚙️ **Configurar certificados** de produção (se diferentes)
   - ⚙️ **Criar workspace** de produção (uma vez)

### 📝 Passos Simples:

**1. Adicionar credenciais no `.env`:**
```env
# Trocar de sandbox para produção
SANTANDER_PAYMENTS_BASE_URL=https://trust-open.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-open.api.santander.com.br/auth/oauth/v2/token

# Credenciais de PRODUÇÃO (que você vai receber)
SANTANDER_PAYMENTS_CLIENT_ID=client_id_producao
SANTANDER_PAYMENTS_CLIENT_SECRET=client_secret_producao
```

**2. Configurar certificados (se necessário):**
```env
SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado_producao.pfx
SANTANDER_PFX_PASSWORD=senha_do_certificado
```

**3. Criar workspace de produção:**
```
"criar workspace santander agencia 0001 conta 130392838 tipo PAYMENTS"
```

**4. Configurar workspace no `.env`:**
```env
SANTANDER_WORKSPACE_ID=workspace_id_producao
```

**5. Testar com valor mínimo:**
```
"fazer ted de 0.01 reais para conta 1234 agencia 5678 banco 001 nome teste cpf 00993804713"
```

**Pronto!** 🎉

---

## 2️⃣ "Esse ID de transferência tem validade? Será gerado todo dia?"

### 📋 **Resposta:**

**O ID de transferência (`transfer_id`) é único e permanente, mas a TED tem um ciclo de vida:**

### 🔄 Ciclo de Vida de uma TED:

1. **`PENDING_VALIDATION`** (Iniciada)
   - TED foi criada, mas ainda não validada
   - **Ação:** Aguardar validação automática

2. **`READY_TO_PAY`** (Pronta para pagar)
   - TED validada e pronta para ser efetivada
   - **Ação:** Usuário deve efetivar com `efetivar_ted_santander`

3. **`PENDING_CONFIRMATION`** (Pendente de confirmação)
   - TED foi efetivada, aguardando confirmação do banco
   - **Ação:** Aguardar processamento

4. **`AUTHORIZED`** (Autorizada)
   - TED autorizada pelo banco
   - **Ação:** Será processada

5. **`SETTLED`** (Liquidada) / **`PAYED`** (Paga)
   - TED processada e dinheiro transferido
   - **Ação:** Concluída ✅

6. **`REJECTED`** (Rejeitada)
   - TED rejeitada (saldo insuficiente, dados incorretos, etc.)
   - **Ação:** Verificar motivo e corrigir

### ⏰ Validade e Expiração:

**❌ O ID não expira:**
- O `transfer_id` é único e permanente
- Você pode consultar uma TED antiga usando o mesmo ID
- O ID não é gerado todo dia - é gerado **a cada TED criada**

**✅ Mas a TED pode expirar:**
- TEDs em estado `READY_TO_PAY` podem expirar se não forem efetivadas
- Prazo típico: **24 horas** (verificar documentação do Santander)
- Após expirar, a TED não pode mais ser efetivada

### 📊 Exemplo Prático:

```
Dia 1, 10:00 - Criar TED
  → transfer_id: "4ef8791d-415a-4987-9206-4553a8f1d609"
  → Status: READY_TO_PAY

Dia 1, 10:05 - Efetivar TED
  → Mesmo transfer_id: "4ef8791d-415a-4987-9206-4553a8f1d609"
  → Status: PENDING_CONFIRMATION

Dia 1, 10:10 - Consultar TED
  → Mesmo transfer_id: "4ef8791d-415a-4987-9206-4553a8f1d609"
  → Status: AUTHORIZED

Dia 2, 08:00 - Consultar TED novamente
  → Mesmo transfer_id: "4ef8791d-415a-4987-9206-4553a8f1d609"
  → Status: SETTLED (concluída)
```

### 💡 Recomendações:

1. **Efetivar TEDs rapidamente:**
   - TEDs em `READY_TO_PAY` devem ser efetivadas em até 24 horas
   - Não deixe TEDs pendentes por muito tempo

2. **Salvar transfer_id:**
   - Salve o `transfer_id` para consultas futuras
   - Use para rastrear status da TED

3. **Consultar status regularmente:**
   - Use `consultar_ted_santander` para verificar status
   - TEDs podem mudar de status automaticamente

4. **Listar TEDs para histórico:**
   - Use `listar_teds_santander` para ver todas as TEDs
   - Filtre por data ou status conforme necessário

### 🔍 Como Consultar Status:

**No chat:**
```
"consultar ted 4ef8791d-415a-4987-9206-4553a8f1d609"
```

**Listar todas as TEDs:**
```
"listar teds do santander"
"listar teds do santander de 01/01/26 a 31/01/26"
"listar teds do santander status PENDING"
```

---

## 📚 Referências

- **Documentação completa:** `docs/IMPLEMENTACAO_TED_SANTANDER_FINAL.md`
- **Passos para produção:** Seção "🚀 Passos para Produção"
- **Troubleshooting:** Seção "🔧 Troubleshooting"

---

**Última atualização:** 12/01/2026
