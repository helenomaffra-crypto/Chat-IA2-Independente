# 🔄 Fluxo de Dados - Conciliação Bancária

## 📊 Fluxo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. SINCRONIZAÇÃO (Gravação no Banco)                           │
└─────────────────────────────────────────────────────────────────┘

API Banco (BB/Santander)
    ↓
    [JSON da API]
    ↓
Python (BancoSincronizacaoService)
    ↓
    [Dict Python]
    ↓
SQL Server (INSERT INTO MOVIMENTACAO_BANCARIA)
    ↓
    ✅ DADOS GRAVADOS NO BANCO


┌─────────────────────────────────────────────────────────────────┐
│ 2. LEITURA (Consulta do Banco para UI)                         │
└─────────────────────────────────────────────────────────────────┘

UI (Frontend)
    ↓
    [GET /api/banco/lancamentos-nao-classificados]
    ↓
Python (BancoConcilacaoService)
    ↓
    [Query SQL: SELECT ... FROM MOVIMENTACAO_BANCARIA ...]
    ↓
SQL Server
    ↓
    [Resultado da Query]
    ↓
Node.js Adapter (sql_server_node.js)
    ↓
    [JSON - AQUI ESTÁ O PROBLEMA!]
    ↓
    ⚠️ JSON pode ser corrompido/truncado (65KB+)
    ↓
Python (sql_server_adapter.py)
    ↓
    [Reparação automática de JSON]
    ↓
    [Dict Python]
    ↓
Flask (app.py)
    ↓
    [JSON para UI]
    ↓
UI (Frontend)
    ↓
    ✅ EXIBE LANÇAMENTOS
```

## 🔍 Onde Cada JSON é Usado

### 1. **JSON da API do Banco** (Sincronização)
- **Origem**: API do Banco do Brasil ou Santander
- **Formato**: JSON da API bancária
- **Uso**: Python lê e converte para dict
- **Destino**: SQL Server (INSERT)
- **Status**: ✅ Funciona bem

### 2. **JSON do Node.js Adapter** (Leitura) ⚠️ PROBLEMA AQUI
- **Origem**: Node.js adapter (`sql_server_node.js`)
- **Formato**: JSON com resultado da query SQL
- **Tamanho**: Pode ser muito grande (65KB+)
- **Problema**: JSON pode ser truncado/corrompido
- **Solução**: Reparação automática implementada
- **Uso**: Python lê, repara se necessário, converte para dict
- **Destino**: Flask retorna para UI

### 3. **JSON para UI** (Resposta da API)
- **Origem**: Flask (app.py)
- **Formato**: JSON com lista de lançamentos
- **Uso**: Frontend exibe na tela
- **Status**: ✅ Funciona bem

## 🐛 O Problema do JSON Corrompido

### Onde acontece:
```
SQL Server → Node.js Adapter → JSON (65KB) → Python
                                    ↑
                            AQUI PODE SER CORROMPIDO
```

### Por quê?
1. **Node.js adapter** retorna JSON muito grande (65KB+)
2. **Buffer do subprocess** pode truncar
3. **JSON incompleto** causa erro de parse

### Solução implementada:
1. ✅ **Limite reduzido**: `TOP 500` em vez de `TOP 10000`
2. ✅ **Reparação automática**: Detecta e repara JSON corrompido
3. ✅ **Logs detalhados**: Mostra quando repara

## 📝 Exemplo Prático

### Sincronização (Gravação):
```python
# 1. API retorna JSON
api_response = {
    "dataLancamento": "2026-01-13",
    "valorLancamento": 1000.50,
    "descricao": "PGT CARTAO"
}

# 2. Python converte para dict e grava
service.importar_lancamento(api_response, agencia="1251", conta="50483")
# → INSERT INTO MOVIMENTACAO_BANCARIA ...

# 3. Dados gravados no SQL Server ✅
```

### Leitura (Consulta):
```python
# 1. UI pede lançamentos
GET /api/banco/lancamentos-nao-classificados

# 2. Python faz query
SELECT TOP 500 ... FROM MOVIMENTACAO_BANCARIA ...

# 3. Node.js adapter retorna JSON
{
  "success": true,
  "data": [
    {"id_movimentacao": "377", "valor_movimentacao": 13543.73, ...},
    {"id_movimentacao": "362", "valor_movimentacao": 13543.73, ...},
    ...
    // ⚠️ JSON pode ser truncado aqui (65KB+)
  ]
}

# 4. Python repara se necessário
if json_corrompido:
    reparar_json()  # Remove último registro incompleto

# 5. Retorna para UI
return jsonify({"sucesso": True, "lancamentos": [...]})
```

## ✅ Resumo

| Etapa | Origem | Formato | Problema | Solução |
|-------|--------|---------|----------|---------|
| **Sincronização** | API Banco | JSON → Dict | Nenhum | ✅ Funciona |
| **Gravação** | Python | Dict → SQL | Nenhum | ✅ Funciona |
| **Leitura** | SQL Server | Query → JSON | JSON corrompido | ✅ Reparação automática |
| **UI** | Flask | JSON | Nenhum | ✅ Funciona |

## 🎯 Conclusão

- **Sincronização**: Funciona perfeitamente (API → Banco)
- **Leitura**: Funciona com reparação automática (Banco → UI)
- **JSON corrompido**: Acontece na leitura (Node.js adapter), não na sincronização
- **Solução**: Limite reduzido + reparação automática

---

**Última atualização:** 13/01/2026
