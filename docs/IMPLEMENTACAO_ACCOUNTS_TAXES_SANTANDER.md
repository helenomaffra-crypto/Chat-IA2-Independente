# 🏦 Implementação Accounts and Taxes Santander - Documentação

**Data:** 13/01/2026  
**Status:** ✅ **EXTENDENDO API EXISTENTE**

---

## 📋 Resumo Executivo

Extensão da API de Pagamentos do Santander (`SantanderPaymentsAPI`) para incluir funcionalidades de **Accounts and Taxes** (Contas e Tributos). 

**✅ IMPORTANTE:** Esta implementação **reutiliza a mesma API base** que já usamos para TED. Não é uma API separada!

**Funcionalidades Adicionadas:**
- ✅ Bank Slip Payments (Boleto)
- ✅ Barcode Payments (Código de Barras)
- ✅ Pix Payments (PIX)
- ✅ Vehicle Taxes Payments (IPVA)
- ✅ Taxes by Fields Payments (GARE ICMS, GARE ITCMD, DARF, GPS)

---

## 🎯 Arquitetura

### Reutilização da API Existente

A implementação **estende** a `SantanderPaymentsAPI` existente, não cria uma nova:

**Estrutura:**
```
utils/santander_payments_api.py
├── Métodos TED (já existentes)
│   ├── iniciar_ted()
│   ├── efetivar_ted()
│   ├── consultar_ted()
│   └── listar_teds()
│
└── Métodos Accounts and Taxes (NOVOS)
    ├── Métodos genéricos (_iniciar_pagamento_generico, etc.)
    ├── Bank Slip Payments
    ├── Barcode Payments
    ├── Pix Payments
    ├── Vehicle Taxes Payments
    └── Taxes by Fields Payments
```

**Mesma Base:**
- ✅ Mesmo workspace (`SANTANDER_WORKSPACE_ID`)
- ✅ Mesma autenticação (OAuth2 + mTLS)
- ✅ Mesmas credenciais (`SANTANDER_PAYMENTS_CLIENT_ID`, `SANTANDER_PAYMENTS_CLIENT_SECRET`)
- ✅ Mesmos certificados (`SANTANDER_PAYMENTS_CERT_FILE`, `SANTANDER_PAYMENTS_KEY_FILE`)

**Endpoints da API:**
- TED: `/management_payments_partners/v1/workspaces/{workspace_id}/transfer`
- Bank Slip: `/management_payments_partners/v1/workspaces/{workspace_id}/bank_slip_payments`
- Barcode: `/management_payments_partners/v1/workspaces/{workspace_id}/barcode_payments`
- PIX: `/management_payments_partners/v1/workspaces/{workspace_id}/pix_payments`
- Vehicle Taxes: `/management_payments_partners/v1/workspaces/{workspace_id}/vehicle_taxes_payments`
- Taxes by Fields: `/management_payments_partners/v1/workspaces/{workspace_id}/taxes_by_fields_payments`

---

## 📚 Funcionalidades Implementadas

### 1. Bank Slip Payments (Boleto)

**Métodos:**
- `iniciar_bank_slip_payment()` - Inicia pagamento de boleto
- `efetivar_bank_slip_payment()` - Efetiva pagamento de boleto
- `consultar_bank_slip_payment()` - Consulta pagamento por ID
- `listar_bank_slip_payments()` - Lista pagamentos paginados

**Exemplo de uso:**
```python
# Iniciar
payment = api.iniciar_bank_slip_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    code="03398936800250000009514112500000000037010101",
    payment_date="2026-01-13"
)

# Efetivar
api.efetivar_bank_slip_payment(
    workspace_id="...",
    payment_id=payment["id"],
    payment_value=2500.00,
    debit_account={"branch": "1", "number": "130392838"},
    final_payer={
        "name": "EMPRESA LTDA",
        "documentType": "CNPJ",
        "documentNumber": "12345678000190"
    }
)
```

---

### 2. Barcode Payments (Código de Barras)

**Métodos:**
- `iniciar_barcode_payment()` - Inicia pagamento por código de barras
- `efetivar_barcode_payment()` - Efetiva pagamento
- `consultar_barcode_payment()` - Consulta por ID
- `listar_barcode_payments()` - Lista pagamentos paginados

**Exemplo de uso:**
```python
payment = api.iniciar_barcode_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    code="846400000002873500240304015034903342708040406124",
    payment_date="2026-01-13"
)
```

---

### 3. Pix Payments (PIX)

**Métodos:**
- `iniciar_pix_payment()` - Inicia pagamento PIX (suporta 3 modos: DICT, QR Code, Beneficiário)
- `efetivar_pix_payment()` - Efetiva pagamento PIX
- `consultar_pix_payment()` - Consulta por ID
- `listar_pix_payments()` - Lista pagamentos paginados

**Modos de pagamento PIX:**

**1. DICT (Chave PIX):**
```python
api.iniciar_pix_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    payment_value="100.50",
    dict_code="chavepix@email.com",
    dict_code_type="EMAIL"
)
```

**2. QR Code:**
```python
api.iniciar_pix_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    payment_value="100.99",
    qr_code="00020126990014br.gov.bcb.pix...",
    ibge_town_code=3550308,
    payment_date="2026-01-13"
)
```

**3. Beneficiário:**
```python
api.iniciar_pix_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    payment_value="100.99",
    beneficiary={
        "branch": 1000,
        "number": 10301293232123458000,
        "type": "CONTA_CORRENTE",
        "documentType": "CPF",
        "documentNumber": 12345678909,
        "name": "João Silva",
        "bankCode": 1234,
        "ispb": 123456
    }
)
```

---

### 4. Vehicle Taxes Payments (IPVA)

**Métodos:**
- `consultar_debitos_renavam()` - Consulta débitos do Renavam
- `iniciar_vehicle_tax_payment()` - Inicia pagamento de IPVA
- `efetivar_vehicle_tax_payment()` - Efetiva pagamento
- `consultar_vehicle_tax_payment()` - Consulta por ID
- `listar_vehicle_tax_payments()` - Lista pagamentos paginados

**Exemplo de uso:**
```python
# Consultar débitos
debitos = api.consultar_debitos_renavam(
    workspace_id="...",
    renavam=3271927,
    state_abbreviation="SP"
)

# Iniciar pagamento
payment = api.iniciar_vehicle_tax_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    renavam=3271927,
    tax_type="IPVA",
    exercise_year=2026,
    state_abbreviation="SP",
    doc_type="CPF",
    document_number=12345678909,
    type_quota="SINGLE",
    payment_date="2026-01-13"
)
```

---

### 5. Taxes by Fields Payments (GARE, DARF, GPS)

**Métodos:**
- `iniciar_tax_by_fields_payment()` - Inicia pagamento de imposto por campos
- `efetivar_tax_by_fields_payment()` - Efetiva pagamento
- `consultar_tax_by_fields_payment()` - Consulta por ID
- `listar_tax_by_fields_payments()` - Lista pagamentos paginados

**Tipos de imposto suportados:**
- `GARE ICMS`
- `GARE ITCMD`
- `DARF`
- `GPS`

**Exemplo GARE ICMS:**
```python
payment = api.iniciar_tax_by_fields_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    tax_type="GARE ICMS",
    payment_date="2026-01-13",
    city="São Paulo",
    state_abbreviation="SP",
    fields={
        "field02": "2026-01-01",
        "field03": 1234,
        "field04": 183659182736,
        "field05": 73928427380,
        "field06": 8374618273764,
        "field07": "01-2026",
        "field08": 848293745,
        "field09": 38273645829384,
        "field10": 832736457283732,
        "field11": 376323456612432,
        "field12": 274829182736457,
        "field13": 983726437283747,
        "field15": "EMPRESA LTDA",
        "field16": "Av Interlagos, 3501",
        "field17": "(11) 12345-6789",
        "field18": 82736457,
        "field19": "string"
    }
)
```

**Exemplo DARF:**
```python
payment = api.iniciar_tax_by_fields_payment(
    workspace_id="...",
    payment_id="uuid-gerado",
    tax_type="DARF",
    payment_date="2026-01-13",
    city="São Paulo",
    state_abbreviation="SP",
    fields={
        "field01": "Empresa - (11) 5578-3821",
        "field02": "2026-01-14",
        "field03": 46692833721,
        "field04": 8285,
        "field05": 273981240192888,
        "field06": "2026-01-02",
        "field07": 3245,
        "field08": 399.99,
        "field09": 989.93
    }
)
```

---

## 🔧 Padrão de Implementação

Todos os tipos de pagamento seguem o mesmo padrão:

### 1. Iniciar Pagamento (POST)
- Cria pagamento em estado `PENDING_VALIDATION`
- Retorna `payment_id` único
- Requer dados específicos do tipo de pagamento

### 2. Efetivar Pagamento (PATCH)
- Confirma e autoriza o pagamento
- Muda status para `AUTHORIZED` ou `PAYED`
- Requer conta de débito e valor (quando aplicável)

### 3. Consultar Pagamento (GET)
- Consulta status e detalhes por `payment_id`
- Retorna estado atual do pagamento

### 4. Listar Pagamentos (GET)
- Lista pagamentos paginados
- Suporta filtros por data e status
- Retorna lista paginada com metadados

---

## ⚙️ Configuração

**Mesma configuração do TED:**

```env
# ==========================================
# SANTANDER - PAGAMENTOS (Accounts and Taxes usa a mesma API)
# ==========================================
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token

# Credenciais (mesmas do TED)
SANTANDER_PAYMENTS_CLIENT_ID=seu_client_id
SANTANDER_PAYMENTS_CLIENT_SECRET=seu_client_secret

# Certificados (mesmos do TED)
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.pem
# OU
SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado.pfx
SANTANDER_PFX_PASSWORD=senha001

# Workspace (mesmo do TED)
SANTANDER_WORKSPACE_ID=workspace_id
```

**⚠️ IMPORTANTE:** O workspace precisa ter os tipos de pagamento ativados:
- `bankSlipPaymentsActive: true` - Para boletos
- `barCodePaymentsActive: true` - Para códigos de barras
- `pixPaymentsActive: true` - Para PIX
- `vehicleTaxesPaymentsActive: true` - Para IPVA
- `taxesByFieldPaymentsActive: true` - Para GARE, DARF, GPS

---

## 📝 Lições Aprendidas

### ✅ O Que Fazer

1. **Reutilizar API existente quando possível**
   - Accounts and Taxes usa a mesma base que TED
   - Evita duplicação de código
   - Facilita manutenção

2. **Criar métodos genéricos para padrões comuns**
   - `_iniciar_pagamento_generico()` evita duplicação
   - `_efetivar_pagamento_generico()` padroniza efetivação
   - Facilita adicionar novos tipos no futuro

3. **Manter mesmo padrão de autenticação e workspace**
   - Usa mesma configuração do TED
   - Não precisa criar nova aplicação no Developer Portal
   - Simplifica configuração

### ❌ O Que NÃO Fazer

1. **Não criar API separada desnecessariamente**
   - Accounts and Taxes é parte da mesma API de Payments
   - Criar API separada seria redundante

2. **Não duplicar código de autenticação**
   - Reutilizar `_get_access_token()` e `_get_headers()`
   - Manter mesmo padrão de tratamento de erros

---

## ✅ Status da Implementação

**✅ Completo:**
- [x] API estendida com métodos genéricos e específicos
- [x] Serviço de negócio com todos os métodos
- [x] Tool definitions para todos os tipos de pagamento
- [x] Handlers no SantanderAgent
- [x] Mapeamento no tool_router
- [x] Documentação completa

**🔄 Próximos Passos:**
- [ ] Testar no sandbox antes de produção
- [ ] Validar com credenciais reais quando disponíveis
- [ ] Integrar com conciliação bancária (opcional)

---

## 📚 Referências

**Documentação Oficial:**
- https://developer.santander.com.br/api/user-guide/accounts-and-taxes
- https://developer.santander.com.br/api/user-guide/pix-payments
- https://developer.santander.com.br/api/user-guide/bank-slip-payments

**Arquivos do Projeto:**
- `utils/santander_payments_api.py` - Cliente da API (estendido)
- `services/santander_payments_service.py` - Serviço de negócio (a ser atualizado)
- `services/agents/santander_agent.py` - Agent (a ser atualizado)

**Documentação Relacionada:**
- `docs/IMPLEMENTACAO_TED_SANTANDER_FINAL.md` - Implementação TED (mesma API base)

---

**Última atualização:** 13/01/2026  
**Versão:** 1.0.0
