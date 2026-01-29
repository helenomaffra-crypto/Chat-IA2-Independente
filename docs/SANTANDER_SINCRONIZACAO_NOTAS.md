# 🏦 Notas Importantes - Sincronização Santander

**Data:** 07/01/2026  
**Status:** 📝 Documentado para implementação futura

---

## ⚠️ Diferenças Críticas: Santander vs Banco do Brasil

### Banco do Brasil

- ✅ **Precisa de agência + conta** como parâmetros
- ✅ **Múltiplas contas** na mesma API (usa agência/conta diferentes)
- ✅ **Uma única API** pode consultar várias contas

**Exemplo:**
```python
# BB: Precisa passar agência e conta
bb_service.consultar_extrato(
    agencia='1251',
    conta='50483',
    data_inicio=datetime(2026, 1, 1)
)
```

---

### Santander

- ❌ **NÃO precisa de agência + conta** como parâmetros
- ✅ **API 1:1 por conta** (cada credencial/cliente ID = uma conta)
- ✅ **A conta já está definida** nas credenciais/configuração

**Exemplo:**
```python
# Santander: NÃO precisa passar agência/conta
# A API já sabe qual conta consultar (via credenciais)
santander_service.consultar_extrato(
    data_inicio='2026-01-01',
    data_fim='2026-01-07'
)
```

---

## 🔧 Como Funciona o Santander

### Configuração (`.env`)

```env
# Cada conjunto de credenciais = 1 conta
SANTANDER_CLIENT_ID=seu_client_id_1    # Conta 1
SANTANDER_CLIENT_SECRET=seu_secret_1   # Conta 1
SANTANDER_BANK_ID=90400888000142       # ID do banco (único)

# Se tiver Conta 2, precisa de OUTRO Client ID/Secret:
SANTANDER_CLIENT_ID_2=seu_client_id_2  # Conta 2 (se houver)
SANTANDER_CLIENT_SECRET_2=seu_secret_2 # Conta 2 (se houver)
```

### Consulta de Extrato

```python
# Santander NÃO precisa de agência/conta
resultado = santander_service.consultar_extrato(
    dias=7  # Últimos 7 dias
    # NÃO passa agencia/conta - a API já sabe qual conta é!
)
```

---

## 📋 Impacto na Implementação da Sincronização

### Para Banco do Brasil (✅ Já Implementado)

```python
def sincronizar_extrato_bb(agencia, conta):
    # Consulta API com agência/conta
    lancamentos = bb_service.consultar_extrato(agencia, conta)
    # Importa para SQL Server
    importar_lancamentos(lancamentos, agencia, conta, banco='BB')
```

### Para Santander (⏳ A Implementar)

```python
def sincronizar_extrato_santander():
    # NÃO precisa de agência/conta
    # A API já sabe qual conta consultar (via credenciais)
    lancamentos = santander_service.consultar_extrato(dias=7)
    # Importa para SQL Server
    # banco='SANTANDER', agencia/conta vêm das credenciais
    importar_lancamentos(lancamentos, banco='SANTANDER')
```

---

## 🔑 Diferenças no Hash de Duplicatas

### Banco do Brasil

```python
# Hash inclui banco + agência + conta + dados do lançamento
hash = SHA256({
    'banco': 'BB',
    'agencia': '1251',  # ← Precisa
    'conta': '50483',   # ← Precisa
    'data_lancamento': ...,
    'valor': ...,
    ...
})
```

### Santander

```python
# Hash inclui banco + bank_id + dados do lançamento
# NÃO precisa de agência/conta (já está no bank_id/credenciais)
hash = SHA256({
    'banco': 'SANTANDER',
    'bank_id': '90400888000142',  # ← Identifica a conta
    'data_lancamento': ...,
    'valor': ...,
    ...
})
```

---

## 📊 Modal de Sincronização (UI)

### Banco do Brasil

```
[Dropdown]
- BB - Ag. 1251 - C/C 50483        ← Precisa selecionar
- BB - Ag. 1251 - C/C 50484        ← Precisa selecionar
- Conta Personalizada              ← Permite digitar
```

### Santander (Futuro)

```
[Dropdown]
- Santander - Conta 1              ← API já sabe qual conta é
- Santander - Conta 2              ← Se tiver segunda API/config
```

**Nota:** Para múltiplas contas do Santander, cada uma precisa de:
- Client ID diferente
- Client Secret diferente
- Certificado mTLS específico (se aplicável)

---

## ✅ Implementação Futura

Quando implementar sincronização do Santander:

1. **Atualizar `BancoSincronizacaoService`:**
   - Método `sincronizar_extrato_santander()` (sem parâmetros agência/conta)
   - Hash específico para Santander (usa `bank_id` em vez de agência/conta)

2. **Atualizar Modal UI:**
   - Mostrar "Santander - Conta 1" (sem agência/conta visível)
   - Se houver múltiplas contas, mostrar "Santander - Conta 1", "Santander - Conta 2"

3. **Atualizar Endpoint `/api/banco/sincronizar`:**
   - Aceitar `banco='SANTANDER'` sem `agencia`/`conta`
   - Validar que Santander não precisa de agência/conta

---

## 📝 Resumo

| Aspecto | Banco do Brasil | Santander |
|---------|-----------------|-----------|
| **Parâmetros obrigatórios** | ✅ Agência + Conta | ❌ Nenhum (API já sabe) |
| **Múltiplas contas** | ✅ Uma API, várias contas | ❌ Uma API = Uma conta |
| **Identificação no hash** | Agência + Conta | Bank ID + Credenciais |
| **Configuração** | `.env`: `BB_TEST_AGENCIA`, `BB_TEST_CONTA` | `.env`: `SANTANDER_BANK_ID` (identifica conta) |

---

**Última atualização:** 07/01/2026 às 17:00

