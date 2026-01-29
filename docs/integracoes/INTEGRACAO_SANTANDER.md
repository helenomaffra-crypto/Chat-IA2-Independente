# Integração Santander Open Banking com mAIke

## 📋 Visão Geral

A integração permite que o mAIke consulte extratos bancários, saldos e listar contas do Santander Open Banking através de comandos em linguagem natural.

---

## 🏗️ Arquitetura

### Componentes Criados

1. **`services/santander_service.py`** - Wrapper para API do Santander
   - Gerencia conexão com a API
   - Formata respostas para o chat
   - Trata erros e validações

2. **`services/agents/santander_agent.py`** - Agent para operações bancárias
   - Implementa handlers para cada tool
   - Segue padrão BaseAgent

3. **Tools adicionadas em `tool_definitions.py`**:
   - `listar_contas_santander` - Lista contas disponíveis
   - `consultar_extrato_santander` - Consulta extrato bancário
   - `consultar_saldo_santander` - Consulta saldo da conta

4. **Mapeamento em `tool_router.py`**:
   - Todas as tools do Santander mapeadas para `santander` agent

---

## 🔧 Configuração

### ✅ Versão Independente

A integração é **100% independente** - não depende de diretório externo. Todo o código está dentro do projeto `Chat-IA-Independente`.

### Pré-requisitos

1. **Certificado mTLS** (ICP-Brasil tipo A1)
2. **Credenciais** do Portal do Desenvolvedor Santander:
   - Client ID
   - Client Secret
3. **Certificado mTLS registrado** no Portal do Desenvolvedor

### Estrutura do Projeto

```
Chat-IA-Independente/
├── utils/
│   └── santander_api.py        # Cliente API do Santander (independente)
├── services/
│   ├── santander_service.py    # Wrapper para integração
│   └── agents/
│       └── santander_agent.py  # Agent para operações bancárias
└── .env                        # Credenciais e certificados (aqui mesmo!)
```

### Variáveis de Ambiente Necessárias

No arquivo `.env` do projeto `Chat-IA-Independente`:

```env
SANTANDER_CLIENT_ID=seu_client_id
SANTANDER_CLIENT_SECRET=seu_client_secret
SANTANDER_BASE_URL=https://trust-open.api.santander.com.br
SANTANDER_TOKEN_URL=https://trust-open.api.santander.com.br/auth/oauth/v2/token
SANTANDER_BANK_ID=90400888000142
SANTANDER_CERT_FILE=/caminho/para/cert.pem
SANTANDER_KEY_FILE=/caminho/para/key.pem
```

---

## 💬 Como Usar

### Exemplos de Comandos

**Listar contas:**
```
"listar contas do santander"
"quais contas tenho no santander"
"mostrar contas disponíveis"
```

**Consultar extrato:**
```
"extrato do santander"
"movimentações da conta"
"extrato de hoje"
"extrato dos últimos 7 dias"
"extrato dos últimos 30 dias"
"extrato de janeiro"
"extrato de 01/01/2026 a 06/01/2026"
"extrato do dia 30/12/2025"
"extrato de 30/12/25"
"extrato de ontem"
```

**Consultar saldo (atual):**
```
"saldo do santander"
"quanto tem na conta"
"saldo disponível"
"saldo da conta 3003"
```

**Consultar saldo histórico (de um dia/período específico):**
```
"saldo em 05/01/2026"
"saldo de ontem"
"saldo do dia 10 de janeiro"
"saldo em 2026-01-05"
"qual era o saldo em 05/01"
"saldo de semana passada"
```

---

## 🔄 Fluxo de Execução

### 1. Usuário Solicita Extrato

```
Usuário: "extrato do santander"
```

### 2. IA Detecta Intenção

A IA identifica que é uma consulta bancária e chama `consultar_extrato_santander`.

### 3. Tool Router

O `ToolRouter` roteia para `SantanderAgent`.

### 4. Santander Agent

O `SantanderAgent` executa `_consultar_extrato` que chama `SantanderService.consultar_extrato`.

### 5. Santander Service

O `SantanderService`:
- Verifica se API está disponível
- Determina datas (padrão: últimos 7 dias se não fornecido)
- Chama `SantanderExtratoAPI.get_extrato_paginado`
- Formata resposta para o chat

### 6. Resposta Formatada

```
📋 Extrato Bancário Santander

Período: 2026-01-01 a 2026-01-06
Total de transações: 15

Totais:
• Créditos: R$ 10.000,00
• Débitos: R$ 5.000,00
• Saldo líquido: R$ 5.000,00

Transações:
1. 06/01/2026 - PIX ENVIADO
   FUTURO FERTIL
   - R$ 1.502,60
...
```

---

## 🎯 Funcionalidades Implementadas

### ✅ Listar Contas

- Lista todas as contas disponíveis no Santander Open Banking
- Formata resposta com agência e número da conta
- Mostra total de contas disponíveis

### ✅ Consultar Extrato

- Consulta extrato por período (data inicial e final)
- Suporta consulta por número de dias (ex: últimos 7 dias)
- Busca todas as páginas automaticamente
- Calcula totais (créditos, débitos, saldo líquido)
- Formata transações de forma legível
- Mostra até 20 transações (com aviso se houver mais)

### ✅ Consultar Saldo

- **Saldo Atual**: Consulta saldo disponível, bloqueado e investido automaticamente
- **Saldo Histórico**: ✅ NOVO (06/01/2026) - Calcula saldo de um dia/período específico retroativamente
  - Usa saldo atual e subtrai transações posteriores à data de referência
  - Suporta formatos: YYYY-MM-DD, DD/MM/YYYY, "ontem", "hoje", "dia X", etc.
  - Mostra saldo histórico, saldo atual e diferença
- Formata valores em R$

---

## ⚠️ Tratamento de Erros

### API Não Disponível

Se o diretório SANTANDER não existir ou a API não puder ser importada:

```
❌ API do Santander não está disponível.

Verifique se:
- O diretório SANTANDER existe
- As dependências estão instaladas
- As credenciais estão configuradas no .env
```

### Credenciais Inválidas

Se as credenciais estiverem incorretas:

```
❌ Erro ao listar contas: Access Denied

💡 Verifique se:
- As credenciais estão corretas no .env
- O certificado mTLS está configurado
- Você tem permissão para acessar as contas
```

### Certificado Não Configurado

Se o certificado mTLS não estiver configurado:

```
⚠️ AVISO: Certificados mTLS não configurados.
A API do Santander EXIGE certificados mTLS para autenticação.
```

---

## 🔍 Detalhes Técnicos

### ✅ Versão Independente

O código do Santander está **dentro do projeto** em `utils/santander_api.py`:

```python
from utils.santander_api import SantanderExtratoAPI, SantanderConfig
```

**Não há dependência externa** - tudo está no projeto `Chat-IA-Independente`.

### Cache de Token

A API do Santander implementa cache automático de token:
- Token válido por 15 minutos
- Renovação automática quando expira
- Reutilização entre requisições

### Paginação Automática

O método `get_extrato_paginado` busca todas as páginas automaticamente:
- Limite de 50 registros por página
- Continua até não haver mais registros
- Retorna lista completa de transações

---

## 📝 Exemplos de Uso no Chat

### Exemplo 1: Extrato Simples

```
Usuário: "extrato do santander"

mAIke: 📋 Extrato Bancário Santander

Período: 2025-12-30 a 2026-01-06
Total de transações: 15

Totais:
• Créditos: R$ 10.000,00
• Débitos: R$ 5.000,00
• Saldo líquido: R$ 5.000,00

Transações:
1. 06/01/2026 - PIX ENVIADO
   FUTURO FERTIL
   - R$ 1.502,60
...
```

### Exemplo 2: Extrato por Período

```
Usuário: "extrato de janeiro"

mAIke: 📋 Extrato Bancário Santander

Período: 2026-01-01 a 2026-01-31
Total de transações: 45
...
```

### Exemplo 3: Saldo Atual

```
Usuário: "saldo do santander"

mAIke: 💰 Saldo da Conta Santander

Disponível: R$ 200.566,30
Bloqueado: R$ 0,00
Investido automaticamente: R$ -1.521,42
```

### Exemplo 4: Saldo Histórico ✅ NOVO

```
Usuário: "saldo em 05/01/2026"

mAIke: 💰 Saldo da Conta Santander em 2026-01-05

Saldo Disponível (calculado): R$ 195.123,45
Saldo Atual (hoje): R$ 200.566,30
Diferença: R$ 5.442,85

💡 Saldo calculado retroativamente usando o saldo atual e as transações após 2026-01-05.
```

**Como funciona:**
1. Consulta o saldo atual da conta
2. Consulta o extrato da data de referência até hoje
3. Calcula: `saldo_atual - transações_após_a_data = saldo_na_data`
4. Mostra saldo histórico, saldo atual e diferença

---

## 🚀 Próximos Passos (Opcional)

### Melhorias Futuras

1. **Cache de Extratos**
   - Cachear extratos recentes para evitar consultas repetidas
   - Invalidar cache após X minutos

2. **Filtros Avançados**
   - Filtrar por tipo de transação (PIX, TED, etc.)
   - Filtrar por valor mínimo/máximo
   - Filtrar por descrição

3. **Análises**
   - Calcular médias de gastos
   - Identificar padrões de transações
   - Alertas de movimentações grandes

4. **Múltiplas Contas**
   - Seleção de conta específica
   - Comparação entre contas
   - Saldo consolidado

---

## 📚 Referências

- **Documentação do Santander**: `/Users/helenomaffra/SANTANDER/README.md`
- **API do Santander**: `santander_api.py`
- **Agent**: `services/agents/santander_agent.py`
- **Service**: `services/santander_service.py`

---

**Integração criada em:** 06/01/2026

