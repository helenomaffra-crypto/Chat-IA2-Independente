# Como Testar a API de Pagamentos em Lote do Banco do Brasil

## 📋 Pré-requisitos

1. **Configure as credenciais no `.env`**:
```env
BB_PAYMENTS_CLIENT_ID=eyJpZCI6IjVmYWYwM2MtMzFkNC00Ii...
BB_PAYMENTS_CLIENT_SECRET=eyJpZCI6IjhmNDQ3NGEtZDA0NC00YS...
BB_PAYMENTS_DEV_APP_KEY=1f8386d110934639a2790912c5bba906
BB_PAYMENTS_BASIC_AUTH=ZXlKcFpDSTZJalZtWVdZd00yTXRNekZrTkMwMElpd2lZMjlrYVdkdlVIVmliR2xqWVdSdmNpSTZNQ3dpWTI5a2FXZHZVMjltZEhkaGNtVWlPakUyT0RFeU1Dd2ljMlZ4ZFdWdVkybGhiRWx1YzNSaGJHRmpZVzhpT2pGOTpleUpwWkNJNklqaG1ORFEzTkdFdFpEQTBOQzAwWVNJc0ltTnZaR2xuYjFCMVlteHBZMkZrYjNJaU9qQXNJbU52WkdsbmIxTnZablIzWVhKbElqb3hOamd4TWpBc0luTmxjWFZsYm1OcFlXeEpibk4wWVd4aFkyRnZJam94TENKelpYRjFaVzVqYVdGc1EzSmxaR1Z1WTJsaGJDSTZNU3dpWVcxaWFXVnVkR1VpT2lKb2IyMXZiRzluWVdOaGJ5SXNJbWxoZENJNk1UYzJPRE14TmpZM01Ua3lObjA=
```

2. **Verifique se o scope `pagamento-lote` está autorizado** no portal do BB

## 🧪 Métodos de Teste

### Método 1: Teste Unitário (Estrutural)

Testa se os módulos estão corretos, sem fazer chamadas reais à API:

```bash
python3 testes/test_bb_pagamento_lote.py
```

**O que testa:**
- ✅ Importação dos módulos
- ✅ Configuração da API
- ✅ Inicialização do Serviço
- ✅ Inicialização do Agent
- ✅ Definições de Tools
- ✅ Tool Router

### Método 2: Teste Prático (Com Chamadas Reais)

Testa com chamadas reais à API do BB (sandbox):

```bash
python3 testes/test_bb_pagamento_lote_uso.py
```

**O que testa:**
- 📋 Listar lotes existentes
- 💰 Criar lote de pagamento (exemplo - comentado)
- 🔍 Consultar lote específico
- 🤖 Uso via Agent (simulação do chat)

**⚠️ ATENÇÃO:** Este teste faz requisições REAIS à API do BB (sandbox).

### Método 3: Teste via Chat (Recomendado)

Use o chat do mAIke para testar de forma interativa:

#### 3.1. Listar Lotes

```
maike lista os lotes de pagamento do banco do brasil
```

ou

```
maike quais lotes de pagamento temos no BB?
```

#### 3.2. Consultar Lote Específico

```
maike consulta o lote 12345 do banco do brasil
```

ou

```
maike qual o status do lote 12345?
```

#### 3.3. Criar Lote de Pagamento

```
maike cria um lote de pagamento no banco do brasil com:
- agencia: 1505
- conta: 1348
- pagamentos:
  - boleto: 34191093216412992293280145580009313510000090000, valor: 900.00
```

## 🔍 Verificando se Funcionou

### 1. Verificar Logs

Os logs devem mostrar:
```
✅ Token OAuth obtido com sucesso
✅ Lote criado/consultado com sucesso
```

### 2. Verificar Resposta

A resposta deve conter:
- `sucesso: true`
- `resposta`: Mensagem descritiva
- `dados`: Dados do lote (se aplicável)

### 3. Erros Comuns

#### ❌ "Credenciais não configuradas"
**Solução:** Configure `BB_PAYMENTS_CLIENT_ID`, `BB_PAYMENTS_CLIENT_SECRET`, `BB_PAYMENTS_DEV_APP_KEY` no `.env`

#### ❌ "Token inválido" ou "401 Unauthorized"
**Solução:** 
- Verifique se as credenciais estão corretas
- Verifique se o scope `pagamento-lote` está autorizado
- Verifique se está usando o ambiente correto (sandbox vs produção)

#### ❌ "403 Forbidden"
**Solução:** 
- Verifique se a aplicação tem permissão para a API de pagamentos
- Verifique se o `gw-dev-app-key` está correto

#### ❌ "404 Not Found"
**Solução:** 
- Verifique se a URL da API está correta
- Verifique se o ambiente está configurado corretamente (`BB_ENVIRONMENT`)

## 📝 Exemplo de Uso Completo

### Via Python (Direto)

```python
from services.banco_brasil_payments_service import BancoBrasilPaymentsService

# Inicializar serviço
service = BancoBrasilPaymentsService()

# Listar lotes
resultado = service.listar_lotes()
print(resultado)

# Criar lote
pagamentos = [
    {
        "tipo": "BOLETO",
        "codigo_barras": "34191093216412992293280145580009313510000090000",
        "valor": 900.00,
        "beneficiario": "PLUXEE BENEFICIOS BRASIL S.A",
        "vencimento": "2026-02-08"
    }
]

resultado = service.iniciar_pagamento_lote(
    agencia="1505",
    conta="1348",
    pagamentos=pagamentos
)
print(resultado)

# Consultar lote
resultado = service.consultar_lote("ID_DO_LOTE")
print(resultado)
```

### Via Agent (Como o Chat Usa)

```python
from services.agents.banco_brasil_agent import BancoBrasilAgent

agent = BancoBrasilAgent()

# Listar lotes
resultado = agent.execute(
    tool_name='listar_lotes_bb',
    arguments={},
    context={}
)
print(resultado)
```

## 🎯 Próximos Passos

1. **Teste básico**: Execute `test_bb_pagamento_lote.py` para verificar estrutura
2. **Teste real**: Configure credenciais e execute `test_bb_pagamento_lote_uso.py`
3. **Teste via chat**: Use o chat do mAIke para testar interativamente
4. **Integração**: Integre com o fluxo de boleto (similar ao Santander)

## 📚 Documentação Adicional

- **Credenciais**: `docs/CREDENCIAIS_BB_PAGAMENTOS.md`
- **API Oficial**: https://apoio.developers.bb.com.br/sandbox/spec/61bc753bd9b75d00121497a1
- **Portal BB**: https://developers.bb.com.br/
