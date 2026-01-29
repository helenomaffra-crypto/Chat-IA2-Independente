# 🛡️ Testes Seguros: TED Santander (Sem Risco Financeiro)

**Data:** 12/01/2026  
**Objetivo:** Explicar como testar TED sem risco de movimentar dinheiro real

---

## 🎯 Resumo: Como Testar Sem Risco

### ✅ Solução: Ambiente Sandbox

O Santander fornece um **ambiente de sandbox (teste)** onde você pode:
- ✅ Testar todas as funcionalidades
- ✅ Simular TEDs completas
- ✅ Validar integração
- ✅ **ZERO risco financeiro** (não movimenta dinheiro real)

---

## 🔧 Configuração para Sandbox

### Passo 1: Criar Aplicação no Portal do Desenvolvedor

1. Acesse: https://developer.santander.com.br/
2. Crie uma conta ou faça login
3. Crie uma **nova aplicação** para Pagamentos
4. Durante a criação, escolha **"Sandbox"** ou **"Homologação"**
5. Faça upload do certificado mTLS (parte pública)
6. Obtenha as credenciais:
   - `Client ID` (sandbox)
   - `Client Secret` (sandbox)

### Passo 2: Configurar no `.env`

```env
# ==========================================
# SANTANDER - PAGAMENTOS (SANDBOX/TESTE)
# ==========================================
# ⚠️ IMPORTANTE: URLs de SANDBOX (não produção!)
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token

# Credenciais de SANDBOX (obtidas no portal)
SANTANDER_PAYMENTS_CLIENT_ID=client_id_sandbox_pagamentos
SANTANDER_PAYMENTS_CLIENT_SECRET=secret_sandbox_pagamentos

# Certificados (pode usar os mesmos ou diferentes)
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.key

# Workspace (será criado no sandbox)
SANTANDER_WORKSPACE_ID=workspace_id_sandbox
```

### Passo 3: Verificar Ambiente

O código já detecta automaticamente se está em sandbox:

```python
# utils/santander_payments_api.py
if "sandbox" in self.base_url.lower():
    self.token_url = "https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token"
else:
    self.token_url = "https://trust-open.api.santander.com.br/auth/oauth/v2/token"
```

**Se `SANTANDER_PAYMENTS_BASE_URL` contém "sandbox", usa ambiente de teste automaticamente.**

---

## 🧪 Como Testar

### Teste 1: Listar Workspaces (Sandbox)

```
👤 "listar workspaces do santander"

🤖 mAIke:
🏦 Workspaces Disponíveis no Santander (SANDBOX):

1. PAYMENTS (ID: sandbox_workspace_123)
   - Descrição: Workspace de teste
   - Ambiente: SANDBOX ✅
```

### Teste 2: Criar Workspace (Sandbox)

```
👤 "criar workspace santander agencia 3003 conta 000130827180"

🤖 mAIke:
✅ Workspace criado com sucesso! (SANDBOX)

ID: sandbox_workspace_456
Tipo: PAYMENTS
Conta Principal: Ag. 3003 / C/C 000130827180
Ambiente: SANDBOX ✅

💡 Este workspace é de TESTE - não movimenta dinheiro real.
```

### Teste 3: Iniciar TED (Sandbox)

```
👤 "fazer ted de 1000 reais para conta 1234 agencia 5678 banco 001 nome joão silva cpf 12345678901"

🤖 mAIke:
✅ TED Iniciada com Sucesso! (SANDBOX)

ID da Transferência: ted_sandbox_789
Valor: R$ 1.000,00
Destinatário: João Silva
Status: PENDING_VALIDATION

⚠️ AMBIENTE DE TESTE: Esta TED não movimenta dinheiro real.
```

### Teste 4: Efetivar TED (Sandbox)

```
👤 "efetivar ted ted_sandbox_789"

🤖 mAIke:
✅ TED Efetivada com Sucesso! (SANDBOX)

ID: ted_sandbox_789
Status: AUTHORIZED

⚠️ AMBIENTE DE TESTE: Esta TED foi simulada - nenhum dinheiro foi transferido.
```

---

## 🔒 Garantias de Segurança

### 1. **Ambiente Sandbox é Isolado**

- ✅ Sandbox usa URLs diferentes (`trust-sandbox.api.santander.com.br`)
- ✅ Sandbox usa credenciais diferentes (Client ID/Secret de sandbox)
- ✅ **Nenhuma conexão com ambiente de produção**
- ✅ **Nenhum dinheiro real é movimentado**

### 2. **Validações no Código**

O código já tem validações que ajudam a prevenir erros:

```python
# services/santander_payments_service.py
def iniciar_ted(...):
    # Validações antes de chamar API
    if not valor or valor <= 0:
        return {'erro': 'Valor inválido'}
    
    if not nome_destinatario or not cpf_cnpj_destinatario:
        return {'erro': 'Dados do destinatário são obrigatórios'}
```

### 3. **Diferenciação Visual**

Podemos adicionar indicadores visuais no chat para mostrar quando está em sandbox:

```
✅ TED Iniciada! (SANDBOX)  ← Indica ambiente de teste
⚠️ AMBIENTE DE TESTE        ← Aviso claro
```

---

## 📋 Checklist de Testes Seguros

### Antes de Testar

- [ ] ✅ Configurar `SANTANDER_PAYMENTS_BASE_URL` com "sandbox"
- [ ] ✅ Usar credenciais de sandbox (não produção)
- [ ] ✅ Verificar que certificados estão configurados
- [ ] ✅ Confirmar que workspace será criado no sandbox

### Durante os Testes

- [ ] ✅ Testar criação de workspace
- [ ] ✅ Testar iniciar TED
- [ ] ✅ Testar efetivar TED
- [ ] ✅ Testar consultar TED
- [ ] ✅ Testar listar TEDs
- [ ] ✅ Verificar que respostas indicam "SANDBOX"

### Validações

- [ ] ✅ Nenhum dinheiro real foi movimentado
- [ ] ✅ Todas as operações funcionaram
- [ ] ✅ Erros são tratados corretamente
- [ ] ✅ Mensagens são claras

---

## ⚠️ Diferenças: Sandbox vs Produção

| Aspecto | Sandbox (Teste) | Produção |
|---------|-----------------|----------|
| **URL Base** | `trust-sandbox.api.santander.com.br` | `trust-open.api.santander.com.br` |
| **Credenciais** | Client ID/Secret de sandbox | Client ID/Secret de produção |
| **Dinheiro Real** | ❌ Não movimenta | ✅ Movimenta dinheiro real |
| **Workspace** | Workspace de teste | Workspace de produção |
| **Validações** | Mais permissivo (para testes) | Validações completas |
| **Uso** | Desenvolvimento e testes | Operação real |

---

## 🚀 Migração: Sandbox → Produção

### Quando Estiver Pronto para Produção

1. **Criar Aplicação de Produção:**
   - No Portal do Desenvolvedor
   - Criar nova aplicação para **Produção**
   - Obter credenciais de produção

2. **Atualizar `.env`:**
   ```env
   # Mudar de sandbox para produção
   SANTANDER_PAYMENTS_BASE_URL=https://trust-open.api.santander.com.br
   SANTANDER_PAYMENTS_TOKEN_URL=https://trust-open.api.santander.com.br/auth/oauth/v2/token
   SANTANDER_PAYMENTS_CLIENT_ID=client_id_producao
   SANTANDER_PAYMENTS_CLIENT_SECRET=secret_producao
   ```

3. **Criar Workspace de Produção:**
   - Usar conta real
   - Configurar workspace de produção

4. **Testar com Valores Pequenos:**
   - Começar com TEDs de valores baixos
   - Validar que tudo funciona
   - Aumentar gradualmente

---

## 🛡️ Salvaguardas Adicionais (Opcional)

### 1. Validação de Ambiente no Código

Podemos adicionar validação para garantir que está em sandbox durante desenvolvimento:

```python
# services/santander_payments_service.py
def iniciar_ted(...):
    # Verificar se está em sandbox
    if "sandbox" in self.api.config.base_url.lower():
        logger.warning("⚠️ AMBIENTE DE TESTE: TED será simulada, não movimenta dinheiro real.")
    
    # Continuar com a lógica...
```

### 2. Confirmação Explícita (Opcional)

Para produção, podemos adicionar confirmação explícita:

```python
# Se estiver em produção, pedir confirmação
if not "sandbox" in self.api.config.base_url.lower():
    # Em produção, pode pedir confirmação explícita
    # (implementar se necessário)
    pass
```

### 3. Limite de Valor (Opcional)

Podemos adicionar limite máximo para testes:

```python
# Limite máximo para sandbox (opcional)
MAX_VALUE_SANDBOX = 10000.00  # R$ 10.000,00

if "sandbox" in self.api.config.base_url.lower():
    if valor > MAX_VALUE_SANDBOX:
        return {
            'erro': f'Valor máximo para sandbox é R$ {MAX_VALUE_SANDBOX:,.2f}'
        }
```

---

## 📝 Exemplo de Configuração Completa

### `.env` para Testes (Sandbox)

```env
# ==========================================
# SANTANDER - EXTRATOS (Produção)
# ==========================================
SANTANDER_CLIENT_ID=client_id_extratos_producao
SANTANDER_CLIENT_SECRET=secret_extratos_producao
SANTANDER_BASE_URL=https://trust-open.api.santander.com.br
SANTANDER_CERT_FILE=/path/to/cert_producao.pem
SANTANDER_KEY_FILE=/path/to/key_producao.key

# ==========================================
# SANTANDER - PAGAMENTOS (SANDBOX - TESTE)
# ==========================================
# ⚠️ URLs de SANDBOX (não produção!)
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token

# Credenciais de SANDBOX (obtidas no portal de desenvolvedor)
SANTANDER_PAYMENTS_CLIENT_ID=client_id_sandbox_pagamentos
SANTANDER_PAYMENTS_CLIENT_SECRET=secret_sandbox_pagamentos

# Certificados (pode usar os mesmos ou diferentes)
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.key

# Workspace será criado no sandbox
# SANTANDER_WORKSPACE_ID= (deixar vazio para criar automaticamente)
```

---

## 🧪 Script de Teste (Opcional)

Podemos criar um script de teste para validar tudo:

```python
# scripts/teste_ted_sandbox.py
"""
Script para testar TED no ambiente sandbox.
"""
import os
from dotenv import load_dotenv
from services.santander_payments_service import SantanderPaymentsService

def main():
    load_dotenv()
    
    # Verificar ambiente
    base_url = os.getenv("SANTANDER_PAYMENTS_BASE_URL", "")
    if "sandbox" not in base_url.lower():
        print("⚠️ AVISO: Não está configurado para SANDBOX!")
        print("   Configure SANTANDER_PAYMENTS_BASE_URL com 'sandbox'")
        resposta = input("Continuar mesmo assim? (s/N): ")
        if resposta.lower() != 's':
            return
    
    service = SantanderPaymentsService()
    
    # Teste 1: Listar workspaces
    print("\n🧪 Teste 1: Listar workspaces...")
    resultado = service.listar_workspaces()
    print(resultado.get('resposta', 'Erro'))
    
    # Teste 2: Criar workspace (se não existir)
    # ...
    
    print("\n✅ Testes concluídos!")
    print("⚠️ Lembre-se: Você está em SANDBOX - nenhum dinheiro real foi movimentado.")

if __name__ == "__main__":
    main()
```

---

## ⚠️ Avisos Importantes

### 1. **Sempre Use Sandbox para Desenvolvimento**

- ✅ Desenvolva e teste primeiro no sandbox
- ✅ Valide todas as funcionalidades
- ✅ Só migre para produção quando estiver 100% seguro

### 2. **Verifique URLs Antes de Usar**

- ✅ Sandbox: `trust-sandbox.api.santander.com.br`
- ✅ Produção: `trust-open.api.santander.com.br`
- ⚠️ **Nunca misture credenciais** (sandbox com produção ou vice-versa)

### 3. **Certificados**

- ✅ Certificados podem ser os mesmos para sandbox e produção
- ✅ Ou podem ser diferentes (depende da configuração no portal)
- ⚠️ Verifique no portal do desenvolvedor qual certificado usar

### 4. **Workspace**

- ✅ Workspace de sandbox é separado do de produção
- ✅ Precisa criar workspace em cada ambiente
- ✅ Workspace ID é diferente entre sandbox e produção

---

## 🎯 Resumo: Como Testar Sem Risco

### ✅ Passo a Passo

1. **Configurar Sandbox:**
   ```env
   SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
   SANTANDER_PAYMENTS_CLIENT_ID=client_id_sandbox
   SANTANDER_PAYMENTS_CLIENT_SECRET=secret_sandbox
   ```

2. **Testar no Chat:**
   ```
   "criar workspace santander agencia 3003 conta 000130827180"
   "fazer ted de 100 reais para conta 1234 agencia 5678 banco 001 nome joão cpf 12345678901"
   "efetivar ted ted_123456"
   ```

3. **Verificar:**
   - ✅ Respostas indicam "SANDBOX" ou "TESTE"
   - ✅ Nenhum dinheiro real foi movimentado
   - ✅ Todas as operações funcionaram

4. **Quando Estiver Pronto:**
   - Mudar URLs para produção
   - Usar credenciais de produção
   - Testar com valores pequenos primeiro

---

## 🔒 Garantias

### ✅ O Que Garante Segurança

1. **Ambiente Isolado:**
   - Sandbox usa URLs diferentes
   - Sandbox usa credenciais diferentes
   - **Nenhuma conexão com produção**

2. **Validações:**
   - Código valida dados antes de enviar
   - API valida estrutura e regras
   - Erros são tratados adequadamente

3. **Indicadores Visuais:**
   - Respostas indicam ambiente (sandbox/produção)
   - Avisos claros quando em teste

---

**Última atualização:** 12/01/2026
