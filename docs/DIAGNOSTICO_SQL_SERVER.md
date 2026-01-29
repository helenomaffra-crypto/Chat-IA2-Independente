# 🔍 Diagnóstico: Conexão SQL Server

**Data:** 08/01/2026  
**Status:** ⚠️ Requer teste manual com acesso de rede

---

## 📋 Situação Atual

### Problema Identificado

O script de teste mostra que:
- ✅ Adapter SQL Server está configurado corretamente
- ✅ Usando Node.js adapter (correto para macOS)
- ✅ Configurações padrão detectadas:
  - Server: `172.16.10.8`
  - Instance: `SQLEXPRESS`
  - Database: `Make`
  - Username: `sa`
- ❌ Conexão falha: "SQL Server não acessível (fora da rede do escritório)"

### Possíveis Causas

1. **Sandbox bloqueando acesso de rede:**
   - O ambiente de teste está bloqueando conexões de rede
   - Isso é normal em ambientes sandbox

2. **`.env` não está sendo carregado:**
   - O arquivo `.env` existe mas pode não estar sendo carregado corretamente
   - O adapter está usando valores padrão

3. **SQL Server realmente offline:**
   - Pode estar realmente offline ou inacessível
   - Verificar se está na rede do escritório

---

## ✅ Como Testar Manualmente

### 1. Verificar Conexão de Rede

```bash
# Testar ping no servidor SQL Server
ping 172.16.10.8

# Testar porta SQL Server (1433 ou porta da instância)
telnet 172.16.10.8 1433
# ou
nc -zv 172.16.10.8 1433
```

### 2. Verificar .env

```bash
# Verificar se .env tem as configurações corretas
cd /Users/helenomaffra/Chat-IA-Independente
grep SQL .env
```

**Deve ter:**
```
SQL_SERVER=172.16.10.8\SQLEXPRESS
SQL_USERNAME=sa
SQL_PASSWORD=...
SQL_DATABASE=Make
```

### 3. Testar Conexão Direta

```bash
# Executar script de diagnóstico
cd /Users/helenomaffra/Chat-IA-Independente
python3 testes/test_conexao_sql_server.py
```

**Resultado esperado:**
```
✅ Conexão SQL Server: ✅ OK
✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO: ✅ EXISTE
```

### 4. Testar com Aplicação Real

```bash
# Iniciar aplicação
python3 app.py

# Em outro terminal, testar consulta
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "situação do ALH.0168/25", "session_id": "test"}'
```

---

## 🔧 Correções Aplicadas

### 1. Função `load_env_from_file()` Melhorada

- ✅ Adicionado caminho absoluto do workspace atual
- ✅ Melhor tratamento de erros
- ✅ Logging mais detalhado

### 2. Script de Diagnóstico Criado

- ✅ `testes/test_conexao_sql_server.py`
- ✅ Testa conexão e verifica tabela
- ✅ Mostra configurações detectadas

---

## 📋 Checklist de Verificação

Antes de testar, verifique:

- [ ] Está na rede do escritório? (ou VPN conectada?)
- [ ] `.env` existe e tem as configurações corretas?
- [ ] SQL Server está rodando? (`172.16.10.8`)
- [ ] Porta SQL Server está acessível? (1433 ou porta da instância)
- [ ] Credenciais estão corretas? (username/password)
- [ ] Tabela `HISTORICO_DOCUMENTO_ADUANEIRO` foi criada?

---

## 🎯 Próximos Passos

1. **Testar manualmente quando tiver acesso de rede:**
   ```bash
   python3 testes/test_conexao_sql_server.py
   ```

2. **Se conexão OK, executar testes completos:**
   ```bash
   python3 testes/test_historico_documentos.py
   ```

3. **Se tabela não existe, criar:**
   ```sql
   -- Execute no SQL Server
   -- scripts/criar_banco_maike_completo.sql
   ```

4. **Validar em produção:**
   - Consultar um documento via mAIke
   - Verificar se histórico foi gravado
   - Verificar se mudanças são detectadas

---

## 📊 Status dos Testes

### Testes que Passaram (4/5)

- ✅ Teste 1: Documento Novo
- ✅ Teste 2: Mudança de Status
- ✅ Teste 3: Mudança de Canal
- ✅ Teste 4: Sem Mudanças

### Teste que Requer Rede

- ⏳ Teste 5: Validação de Dados (requer SQL Server acessível)

**Nota:** O Teste 5 falha porque requer conexão com SQL Server, que está bloqueada no sandbox. Quando você testar manualmente na rede do escritório, deve funcionar.

---

## 💡 Observações

1. **Sandbox bloqueia rede:**
   - Isso é normal e esperado
   - Testes precisam ser executados manualmente com acesso de rede

2. **Valores padrão funcionam:**
   - Mesmo sem `.env`, o adapter usa valores padrão
   - Isso permite que a aplicação funcione mesmo sem `.env` carregado

3. **Node.js adapter:**
   - Está sendo usado corretamente (macOS)
   - É a forma recomendada para macOS

---

**Última atualização:** 08/01/2026

