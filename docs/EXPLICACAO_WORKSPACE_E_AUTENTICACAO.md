# 📚 Explicação: Workspace e Autenticação - Santander API

**Data:** 12/01/2026  
**Objetivo:** Explicar o que é workspace e como funciona a autenticação pela API vs Web

---

## 🎯 O Que É Workspace?

### Conceito Simples

**Workspace = "Ambiente de Pagamentos"** configurado dentro da sua aplicação de Pagamentos do Santander.

É como se fosse uma **"caixa de ferramentas"** que você cria uma vez e depois usa para fazer todos os pagamentos (TED, PIX, Boleto, etc.).

### Analogia

Imagine que você tem:
- **Aplicação "Extratos"** → Para consultar extratos (não precisa de workspace)
- **Aplicação "Pagamentos"** → Para fazer pagamentos (precisa de workspace)

Dentro da aplicação "Pagamentos", você cria um **workspace** que define:
- Qual conta vai ser usada para débito (conta principal)
- Quais tipos de pagamento estão ativos (PIX, TED, Boleto, etc.)
- Configurações específicas do ambiente

### Estrutura

```
Aplicação "Pagamentos" (no Developer Portal)
  └── Workspace 1 (ID: abc123)
      ├── Conta Principal: Ag. 3003 / C/C 000130827180
      ├── TED: ✅ Ativo
      ├── PIX: ❌ Inativo
      └── Boleto: ✅ Ativo
  
  └── Workspace 2 (ID: xyz789)  ← Pode ter múltiplos!
      ├── Conta Principal: Ag. 3003 / C/C 000130827180
      ├── TED: ✅ Ativo
      └── PIX: ✅ Ativo
```

### Por Que Precisa de Workspace?

1. **Segurança:** Isola pagamentos em ambientes separados
2. **Organização:** Pode ter múltiplos workspaces para diferentes propósitos
3. **Controle:** Define qual conta será usada para débito
4. **Configuração:** Ativa/desativa tipos de pagamento (PIX, TED, Boleto)

---

## 🔐 Autenticação: Web vs API

### 🌐 Autenticação Web (QR Code)

**Como funciona na web (site/app do Santander):**

```
1. Você acessa o site/app do Santander
2. Faz login com usuário/senha
3. Quando vai fazer uma operação sensível (ex: TED):
   → Sistema pede autenticação adicional
   → Gera um QR Code na tela
   → Você escaneia com app do banco
   → App valida e gera token temporário
   → Token é usado para autorizar a operação
4. Operação é executada
```

**Características:**
- ✅ Interação humana necessária (escanear QR)
- ✅ Mais seguro (validação em 2 fatores)
- ❌ Não pode automatizar (precisa de pessoa)
- ❌ Não funciona para integrações automáticas

---

### 🔌 Autenticação API (OAuth2 mTLS)

**Como funciona pela API (nossa aplicação):**

```
1. Aplicação tem credenciais pré-configuradas:
   - Client ID
   - Client Secret
   - Certificado mTLS (ICP-Brasil)

2. Aplicação faz requisição para obter token:
   POST /auth/oauth/v2/token
   Headers: Certificado mTLS
   Body: client_id, client_secret, grant_type=client_credentials

3. API valida:
   ✅ Certificado mTLS (autenticação mútua)
   ✅ Client ID/Secret (credenciais)
   ✅ Retorna token JWT (válido por 15 minutos)

4. Aplicação usa token para fazer operações:
   POST /workspaces/{workspace_id}/transfer
   Headers: Authorization: Bearer {token}, X-Application-Key: {client_id}
   Body: dados da TED

5. Operação é executada AUTOMATICAMENTE
```

**Características:**
- ✅ **100% automatizado** (sem interação humana)
- ✅ **Sem QR Code** (não precisa escanear nada)
- ✅ **Direto** (TED vai direto, sem confirmação manual)
- ✅ **Seguro** (certificado mTLS + OAuth2)
- ⚠️ **Requer certificado ICP-Brasil** (configuração inicial)

---

## 🚀 Fluxo Completo: TED pela API

### Passo a Passo

#### 1. **Configuração Inicial (Uma Vez)**

```env
# Credenciais da Aplicação "Pagamentos"
SANTANDER_PAYMENTS_CLIENT_ID=seu_client_id_pagamentos
SANTANDER_PAYMENTS_CLIENT_SECRET=seu_secret_pagamentos
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.key
```

#### 2. **Criar Workspace (Uma Vez)**

```python
# Via chat: "criar workspace santander agencia 3003 conta 000130827180"
# Ou via código:
workspace = api.criar_workspace(
    tipo="PAYMENTS",
    main_debit_account={
        "branch": "3003",
        "number": "000130827180"
    }
)
# Retorna: workspace_id = "abc123xyz"
```

**Salvar no .env:**
```env
SANTANDER_WORKSPACE_ID=abc123xyz
```

#### 3. **Fazer TED (Automático - Sem QR Code!)**

```python
# Via chat: "fazer ted de 100 reais para conta 1234 agencia 5678 banco 001"
# Ou via código:

# Passo 1: Iniciar TED
ted = api.iniciar_ted(
    workspace_id="abc123xyz",
    source_account={"branchCode": "3003", "accountNumber": "000130827180"},
    destination_account={...},
    transfer_value="100.00"
)
# Retorna: transfer_id = "ted_123456"

# Passo 2: Efetivar TED (confirma e autoriza)
api.efetivar_ted(
    workspace_id="abc123xyz",
    transfer_id="ted_123456",
    source_account={"branchCode": "3003", "accountNumber": "000130827180"}
)
# ✅ TED EXECUTADA AUTOMATICAMENTE!
```

**Resultado:**
- ✅ TED é criada e autorizada **automaticamente**
- ✅ **Sem QR Code** (não precisa escanear nada)
- ✅ **Sem confirmação manual** (vai direto)
- ✅ Dinheiro é transferido imediatamente

---

## 🔄 Comparação: Web vs API

| Aspecto | Web (Site/App) | API (Nossa Aplicação) |
|---------|----------------|------------------------|
| **Autenticação** | Login + QR Code | OAuth2 mTLS (automático) |
| **QR Code** | ✅ Sim (obrigatório) | ❌ Não (não precisa) |
| **Interação Humana** | ✅ Sim (escanear QR) | ❌ Não (100% automático) |
| **Confirmação Manual** | ✅ Sim (confirmar no app) | ❌ Não (vai direto) |
| **Automação** | ❌ Não (precisa pessoa) | ✅ Sim (100% automático) |
| **Velocidade** | Lenta (espera pessoa) | Rápida (instantânea) |
| **Uso** | Pessoa física | Sistema/Integração |

---

## ⚠️ Importante: Segurança

### Por Que API é Segura Sem QR Code?

1. **Certificado mTLS (Mutual TLS):**
   - Certificado ICP-Brasil tipo A1
   - Autenticação mútua (servidor valida cliente E cliente valida servidor)
   - Muito mais seguro que senha

2. **OAuth2 Client Credentials:**
   - Client ID/Secret são únicos por aplicação
   - Token JWT com expiração (15 minutos)
   - Não pode ser reutilizado

3. **Workspace:**
   - Isola pagamentos em ambientes separados
   - Define conta principal (limite de segurança)
   - Pode ter múltiplos workspaces para diferentes propósitos

### ⚠️ Cuidados

- **Certificado:** Deve ser guardado com segurança (não commitar no git)
- **Client Secret:** Nunca expor publicamente
- **Workspace ID:** Pode ser salvo no .env (não é secreto, mas é importante)

---

## 📋 Resumo

### O Que É Workspace?

**Workspace = Ambiente de Pagamentos** configurado dentro da aplicação de Pagamentos.

- Define qual conta será usada para débito
- Ativa/desativa tipos de pagamento (TED, PIX, Boleto)
- É criado **uma vez** e depois reutilizado
- Pode ter múltiplos workspaces

### Autenticação Web vs API

**Web (QR Code):**
- ❌ Precisa escanear QR Code
- ❌ Precisa confirmação manual
- ❌ Não pode automatizar

**API (OAuth2 mTLS):**
- ✅ **Sem QR Code** (não precisa escanear)
- ✅ **Vai direto** (sem confirmação manual)
- ✅ **100% automático** (pode integrar em sistemas)

### TED pela API

**Fluxo:**
1. Obter token OAuth2 (automático, sem QR)
2. Iniciar TED (cria em estado PENDING_VALIDATION)
3. Efetivar TED (confirma e autoriza automaticamente)
4. ✅ **TED executada sem interação humana!**

---

## 🎯 Conclusão

**Workspace** é o "ambiente de pagamentos" que você configura uma vez e depois usa para fazer todos os pagamentos.

**Pela API, o TED vai direto** - não precisa de QR Code, não precisa de confirmação manual. É 100% automático e seguro (graças ao certificado mTLS e OAuth2).

A diferença principal:
- **Web:** Pessoa escaneia QR → Confirma → TED executa
- **API:** Sistema faz requisição → TED executa automaticamente

---

**Última atualização:** 12/01/2026
