# 🔒 Isolamento de TED Transfers - Santander API

**Data:** 12/01/2026  
**Objetivo:** Documentar a estrutura isolada de TED para evitar conflitos com API de Extratos.

---

## 🎯 Princípio de Isolamento

### ⚠️ Problema Identificado

No Developer Portal do Santander, **cada tipo de API pode precisar de uma aplicação separada**:
- **Aplicação 1:** Extratos (Bank Account Information API)
- **Aplicação 2:** Pagamentos (Payments Partners API) ← **TED usa esta**

Cada aplicação tem suas próprias credenciais:
- `Client ID` diferente
- `Client Secret` diferente
- Mesmos certificados mTLS (ou podem ser diferentes)

### ✅ Solução: Estrutura Completamente Isolada

Criamos uma estrutura **100% separada** da API de Extratos:

```
utils/
├── santander_api.py              ← API de Extratos (EXISTENTE)
└── santander_payments_api.py     ← API de Pagamentos (NOVO - ISOLADO)

services/
├── santander_service.py          ← Service de Extratos (EXISTENTE)
└── santander_payments_service.py ← Service de Pagamentos (NOVO - ISOLADO)

services/agents/
└── santander_agent.py            ← Agent (pode ter ambos ou separar)
```

---

## 📁 Arquivos Criados

### 1. `utils/santander_payments_api.py`

**Classe Principal:** `SantanderPaymentsAPI`

**Características:**
- ✅ **100% isolado** de `SantanderExtratoAPI`
- ✅ **Configuração separada:** `SantanderPaymentsConfig`
- ✅ **Token separado:** Cache de token independente
- ✅ **Session separada:** `requests.Session()` próprio
- ✅ **Certificados próprios:** Pode usar certificados diferentes

**Variáveis de Ambiente (Prioridade):**
```env
# ⚠️ ESPECÍFICAS PARA PAGAMENTOS (prioridade)
SANTANDER_PAYMENTS_CLIENT_ID=...
SANTANDER_PAYMENTS_CLIENT_SECRET=...
SANTANDER_PAYMENTS_BASE_URL=https://trust-open.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-open.api.santander.com.br/auth/oauth/v2/token
SANTANDER_WORKSPACE_ID=...  # ID do workspace (pode ser criado automaticamente)
SANTANDER_PAYMENTS_CERT_FILE=...
SANTANDER_PAYMENTS_KEY_FILE=...
SANTANDER_PAYMENTS_CERT_PATH=...

# Fallback: Se não configurar as específicas, usa as genéricas
# SANTANDER_CLIENT_ID=...  (fallback)
# SANTANDER_CLIENT_SECRET=...  (fallback)
# SANTANDER_CERT_FILE=...  (fallback)
```

**Métodos Implementados:**

#### Workspace:
- `criar_workspace()` - Cria workspace para pagamentos
- `listar_workspaces()` - Lista workspaces disponíveis
- `consultar_workspace()` - Consulta workspace por ID

#### TED Transfers:
- `iniciar_ted()` - Inicia uma transferência TED
- `efetivar_ted()` - Efetiva uma TED iniciada
- `consultar_ted()` - Consulta TED por ID
- `listar_teds()` - Lista TEDs paginado (conciliação)

---

## 🔧 Configuração no `.env`

### Opção 1: Aplicações Separadas (Recomendado)

Se você criou aplicações separadas no Developer Portal:

```env
# ==========================================
# SANTANDER - EXTRATOS (Aplicação 1)
# ==========================================
SANTANDER_CLIENT_ID=client_id_extratos
SANTANDER_CLIENT_SECRET=secret_extratos
SANTANDER_CERT_FILE=/path/to/cert_extratos.pem
SANTANDER_KEY_FILE=/path/to/key_extratos.key

# ==========================================
# SANTANDER - PAGAMENTOS (Aplicação 2)
# ==========================================
SANTANDER_PAYMENTS_CLIENT_ID=client_id_pagamentos
SANTANDER_PAYMENTS_CLIENT_SECRET=secret_pagamentos
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert_pagamentos.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key_pagamentos.key
SANTANDER_WORKSPACE_ID=workspace_id_ou_vazio_para_criar_automatico
```

### Opção 2: Mesma Aplicação (Fallback)

Se você usa a mesma aplicação para ambos:

```env
# Mesmas credenciais para ambos
SANTANDER_CLIENT_ID=client_id_unico
SANTANDER_CLIENT_SECRET=secret_unico
SANTANDER_CERT_FILE=/path/to/cert.pem
SANTANDER_KEY_FILE=/path/to/key.key

# Pagamentos usa as mesmas (fallback automático)
# SANTANDER_PAYMENTS_CLIENT_ID não precisa ser configurado
# SANTANDER_PAYMENTS_CLIENT_SECRET não precisa ser configurado
```

---

## 🏗️ Estrutura de Código

### Fluxo de Chamadas

```
Usuário: "fazer ted de 100 reais para conta X"
  ↓
SantanderAgent (services/agents/santander_agent.py)
  ↓
SantanderPaymentsService (services/santander_payments_service.py) ← NOVO
  ↓
SantanderPaymentsAPI (utils/santander_payments_api.py) ← NOVO
  ↓
Santander Payments API (trust-open.api.santander.com.br)
```

### Comparação: Extratos vs Pagamentos

| Aspecto | Extratos | Pagamentos |
|---------|----------|------------|
| **Arquivo API** | `santander_api.py` | `santander_payments_api.py` |
| **Classe API** | `SantanderExtratoAPI` | `SantanderPaymentsAPI` |
| **Classe Config** | `SantanderConfig` | `SantanderPaymentsConfig` |
| **Service** | `SantanderService` | `SantanderPaymentsService` |
| **Token Cache** | Próprio | Próprio (isolado) |
| **Session HTTP** | Própria | Própria (isolada) |
| **Variáveis ENV** | `SANTANDER_*` | `SANTANDER_PAYMENTS_*` (com fallback) |

---

## ✅ Garantias de Isolamento

### 1. **Sem Conflito de Tokens**
- ✅ Cada API tem seu próprio cache de token
- ✅ Tokens são independentes
- ✅ Renovação automática separada

### 2. **Sem Conflito de Configuração**
- ✅ Classes de configuração separadas
- ✅ Variáveis de ambiente com prefixo diferente
- ✅ Fallback inteligente (se não configurar específicas, usa genéricas)

### 3. **Sem Conflito de Código**
- ✅ Arquivos completamente separados
- ✅ Nenhuma dependência entre eles
- ✅ Pode desabilitar/remover TED sem afetar Extratos

### 4. **Sem Conflito de Certificados**
- ✅ Pode usar certificados diferentes
- ✅ Ou usar os mesmos (configuração flexível)

---

## 🚀 Próximos Passos

### 1. Criar Service (Próximo)
```python
# services/santander_payments_service.py
class SantanderPaymentsService:
    """Service wrapper para API de Pagamentos"""
    def __init__(self):
        config = SantanderPaymentsConfig()
        self.api = SantanderPaymentsAPI(config)
    
    def iniciar_ted(...):
        """Wrapper com validações e formatação"""
    
    def efetivar_ted(...):
        """Wrapper com validações e formatação"""
```

### 2. Estender Agent (Próximo)
```python
# services/agents/santander_agent.py
class SantanderAgent(BaseAgent):
    def __init__(self):
        self.santander_service = SantanderService()  # Extratos
        self.payments_service = SantanderPaymentsService()  # Pagamentos (NOVO)
    
    def execute(self, tool_name, arguments, context):
        handlers = {
            # Extratos (existentes)
            'consultar_extrato_santander': self._consultar_extrato,
            'consultar_saldo_santander': self._consultar_saldo,
            
            # Pagamentos (novos - isolados)
            'iniciar_ted_santander': self._iniciar_ted,
            'efetivar_ted_santander': self._efetivar_ted,
            'consultar_ted_santander': self._consultar_ted,
        }
```

### 3. Adicionar Tool Definitions
```python
# services/tool_definitions.py
tools.append({
    "type": "function",
    "function": {
        "name": "iniciar_ted_santander",
        "description": "Inicia uma transferência TED no Santander...",
        ...
    }
})
```

---

## 📋 Checklist de Isolamento

- [x] ✅ Arquivo API separado (`santander_payments_api.py`)
- [x] ✅ Classe de configuração separada (`SantanderPaymentsConfig`)
- [x] ✅ Variáveis de ambiente com prefixo diferente (`SANTANDER_PAYMENTS_*`)
- [x] ✅ Token cache isolado
- [x] ✅ Session HTTP isolada
- [ ] ⏳ Service wrapper separado (próximo)
- [ ] ⏳ Handlers no Agent (próximo)
- [ ] ⏳ Tool definitions (próximo)
- [ ] ⏳ Testes isolados (futuro)

---

## ⚠️ Notas Importantes

### Sobre Aplicações no Developer Portal

1. **Cada tipo de API = Aplicação separada:**
   - Extratos → Aplicação "Extratos"
   - Pagamentos → Aplicação "Pagamentos"

2. **Cada aplicação tem:**
   - Client ID único
   - Client Secret único
   - Mesmos certificados (ou diferentes, dependendo da configuração)

3. **Workspace:**
   - Workspace é criado **dentro** da aplicação de Pagamentos
   - Cada workspace pode ter múltiplas contas
   - Workspace ID é necessário para todas as operações de pagamento

### Sobre Fallback

O código implementa **fallback inteligente**:
- Se `SANTANDER_PAYMENTS_CLIENT_ID` não estiver configurado
- Usa `SANTANDER_CLIENT_ID` automaticamente
- Isso permite usar a mesma aplicação para ambos (se desejado)

---

**Última atualização:** 12/01/2026
