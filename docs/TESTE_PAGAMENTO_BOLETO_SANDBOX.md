# 🧪 Teste de Pagamento de Boleto no Sandbox

**Data:** 13/01/2026  
**Status:** ✅ **SCRIPT CRIADO** - Pronto para teste

---

## 📋 Visão Geral

Script de teste completo para simular pagamento de boleto no sandbox Santander **antes** de implementar toda a infraestrutura de upload e aprovação.

**Arquivo:** `scripts/teste_pagamento_boleto_sandbox.py`

---

## 🚀 Como Usar

### Opção 1: Com PDF (se conseguir extrair texto)

```bash
python3 scripts/teste_pagamento_boleto_sandbox.py downloads/60608-Cobranca.pdf
```

### Opção 2: Com Dados Manuais (quando PDF é escaneado)

```bash
python3 scripts/teste_pagamento_boleto_sandbox.py --dados <codigo_barras> <valor> [vencimento]
```

**Exemplo com dados do boleto fornecido:**
```bash
python3 scripts/teste_pagamento_boleto_sandbox.py --dados 34191093216412992293280145580009313510000090000 900.00 2026-02-08
```

### Opção 3: Modo Interativo

```bash
python3 scripts/teste_pagamento_boleto_sandbox.py --manual
```

O script pedirá:
- Código de barras (44 ou 47 dígitos)
- Valor (ex: 900.00)
- Vencimento (YYYY-MM-DD, opcional)

---

## ⚙️ Pré-requisitos

### 1. Credenciais Configuradas no `.env`

O script precisa das seguintes variáveis:

```env
# Santander Payments (Sandbox)
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token
SANTANDER_PAYMENTS_CLIENT_ID=seu_client_id_sandbox
SANTANDER_PAYMENTS_CLIENT_SECRET=seu_client_secret_sandbox

# Certificados mTLS
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.pem
# OU
SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado.pfx
SANTANDER_PAYMENTS_PFX_PASSWORD=senha001

# Workspace (opcional - pode criar automaticamente)
SANTANDER_WORKSPACE_ID=workspace_id
```

### 2. Dependências Python

```bash
pip install PyPDF2
```

---

## 📊 O Que o Script Faz

### Fase 1: Extração de Dados

**Com PDF:**
- Extrai texto do PDF usando PyPDF2
- Busca código de barras (múltiplos padrões)
- Extrai valor do documento
- Extrai data de vencimento
- Extrai beneficiário (opcional)

**Com dados manuais:**
- Usa dados fornecidos diretamente
- Valida formato

### Fase 2: Consulta de Saldo

- Consulta saldo disponível no Santander
- Valida se tem saldo suficiente
- Calcula saldo após pagamento

### Fase 3: Iniciar Pagamento

- Gera `payment_id` único (UUID)
- Define data de pagamento (hoje ou vencimento)
- Chama `iniciar_bank_slip_payment_santander`
- Retorna status `PENDING_VALIDATION`

### Fase 4: Efetivar Pagamento

- Chama `efetivar_bank_slip_payment_santander`
- Confirma e autoriza pagamento
- Retorna status `AUTHORIZED` ou `PAYED`

### Fase 5: Consultar Status

- Consulta status final do pagamento
- Mostra detalhes completos

---

## 📝 Exemplo de Saída

```
============================================================
🧪 TESTE DE PAGAMENTO DE BOLETO - SANDBOX SANTANDER (DADOS MANUAIS)
============================================================

📋 FASE 1: Dados do Boleto (Fornecidos Manualmente)
------------------------------------------------------------
✅ Código de barras: 34191093216412992293280145580009313510000090000
✅ Valor: R$ 900.00
✅ Vencimento: 2026-02-08

💰 FASE 2: Consulta de Saldo
------------------------------------------------------------
✅ Saldo disponível: R$ 10.000,00
✅ Saldo após pagamento: R$ 9.100,00

🚀 FASE 3: Iniciar Pagamento no Sandbox
------------------------------------------------------------
📝 Payment ID gerado: 4ef8791d-415a-4987-9206-4553a8f1d609
📅 Data de pagamento: 2026-02-08
✅ Pagamento iniciado com sucesso!
   Status: PENDING_VALIDATION

✅ FASE 4: Efetivar Pagamento no Sandbox
------------------------------------------------------------
✅ Pagamento efetivado com sucesso!
   Status: AUTHORIZED

🔍 FASE 5: Consultar Status do Pagamento
------------------------------------------------------------
✅ Status do pagamento consultado!
   Resposta: 📋 Consulta de Pagamento de Boleto
   ID: 4ef8791d-415a-4987-9206-4553a8f1d609
   Status: AUTHORIZED

============================================================
✅ TESTE CONCLUÍDO COM SUCESSO!
============================================================

📊 Resumo:
   • Código de barras: 34191093216412992293280145580009313510000090000
   • Valor: R$ 900,00
   • Vencimento: 2026-02-08
   • Beneficiário: N/A
   • Payment ID: 4ef8791d-415a-4987-9206-4553a8f1d609
   • Status final: AUTHORIZED

⚠️ LEMBRE-SE: Este é um teste no SANDBOX - nenhum dinheiro foi movimentado!
```

---

## ⚠️ Problemas Comuns

### 1. `.env` Protegido

**Sintoma:**
```
⚠️ Erro ao carregar .env: [Errno 1] Operation not permitted
```

**Solução:**
- O `.env` está protegido (normal)
- Se estiver rodando via Flask, as variáveis já estão carregadas
- Se estiver rodando diretamente, exporte as variáveis no terminal:
  ```bash
  export SANTANDER_PAYMENTS_CLIENT_ID=seu_client_id
  export SANTANDER_PAYMENTS_CLIENT_SECRET=seu_client_secret
  # ... outras variáveis
  ```

### 2. PDF Escaneado (Imagem)

**Sintoma:**
```
⚠️ Página 1: Nenhum texto extraído (pode ser escaneada/imagem)
```

**Solução:**
- Use modo manual: `--dados` ou `--manual`
- Ou implemente OCR (futuro)

### 3. Workspace Não Encontrado

**Sintoma:**
```
❌ Nenhum workspace configurado. Configure SANTANDER_WORKSPACE_ID no .env
```

**Solução:**
- Configure `SANTANDER_WORKSPACE_ID` no `.env`
- Ou crie um workspace primeiro via chat: `"criar workspace santander agencia 0001 conta 130392838 tipo PAYMENTS"`

### 4. Credenciais Não Configuradas

**Sintoma:**
```
❌ Client ID e Client Secret não configurados
```

**Solução:**
- Configure `SANTANDER_PAYMENTS_CLIENT_ID` e `SANTANDER_PAYMENTS_CLIENT_SECRET` no `.env`
- Ou use fallback: `SANTANDER_CLIENT_ID` e `SANTANDER_CLIENT_SECRET` (se forem as mesmas)

---

## ✅ Validações do Script

O script valida:
- ✅ Código de barras (44 ou 47 dígitos)
- ✅ Valor (maior que zero)
- ✅ Vencimento (formato YYYY-MM-DD)
- ✅ Saldo suficiente (se conseguir consultar)
- ✅ Workspace configurado
- ✅ Credenciais configuradas

---

## 🎯 Próximos Passos

Após validar o teste no sandbox:

1. ✅ **Parser de boleto** - Melhorar extração (OCR para PDFs escaneados)
2. ✅ **Tool de processamento** - `processar_boleto_upload`
3. ✅ **Workflow de aprovação** - Modal similar ao de email
4. ✅ **Histórico de pagamentos** - Tabela SQL Server

---

**Última atualização:** 13/01/2026
