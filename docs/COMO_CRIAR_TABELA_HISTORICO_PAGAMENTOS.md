# 📋 Como Criar a Tabela HISTORICO_PAGAMENTOS

**Data:** 13/01/2026  
**Status:** ✅ Script Pronto

---

## 🎯 Objetivo

Criar a tabela `HISTORICO_PAGAMENTOS` no banco `mAIke_assistente` para armazenar o histórico completo de pagamentos (BOLETO, PIX, TED, BARCODE).

---

## 🚀 Opção 1: SQL Server Management Studio (Recomendado)

### Passo a Passo

1. **Abrir SQL Server Management Studio (SSMS)**
   - Conectar ao servidor: `172.16.10.241\SQLEXPRESS`
   - Usuário: `sa` (ou seu usuário)
   - Senha: (sua senha)

2. **Selecionar o Banco de Dados**
   ```sql
   USE [mAIke_assistente];
   GO
   ```

3. **Abrir o Script SQL**
   - Abrir arquivo: `docs/queries/criar_tabela_historico_pagamentos.sql`
   - Ou copiar/colar o conteúdo do arquivo

4. **Executar o Script**
   - Pressionar `F5` ou clicar em "Execute"
   - Aguardar mensagens de sucesso

**Resultado esperado:**
```
✅ Tabela HISTORICO_PAGAMENTOS criada com sucesso!
✅ Índice idx_historico_pagamentos_payment_id criado.
✅ Índice idx_historico_pagamentos_status criado.
✅ Índice idx_historico_pagamentos_tipo criado.
✅ Índice idx_historico_pagamentos_data criado.
✅ Índice idx_historico_pagamentos_banco_ambiente criado.
✅ Script de criação da tabela HISTORICO_PAGAMENTOS concluído!
```

---

## 🚀 Opção 2: Azure Data Studio

1. **Conectar ao SQL Server**
   - Server: `172.16.10.241\SQLEXPRESS`
   - Database: `mAIke_assistente`

2. **Abrir Nova Query**
   - `Ctrl+N` ou `Cmd+N`

3. **Executar Script**
   - Abrir arquivo: `docs/queries/criar_tabela_historico_pagamentos.sql`
   - Executar (`F5`)

---

## 🚀 Opção 3: Via Linha de Comando (sqlcmd)

```bash
# No terminal (se tiver sqlcmd instalado)
sqlcmd -S 172.16.10.241\SQLEXPRESS \
       -d mAIke_assistente \
       -U sa \
       -P "sua_senha" \
       -i docs/queries/criar_tabela_historico_pagamentos.sql
```

---

## ✅ Verificar se Foi Criada

### Via SQL Server Management Studio

```sql
USE [mAIke_assistente];
GO

-- Verificar se tabela existe
SELECT 
    TABLE_NAME,
    TABLE_SCHEMA
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME = 'HISTORICO_PAGAMENTOS';
```

**Resultado esperado:**
```
TABLE_NAME              TABLE_SCHEMA
HISTORICO_PAGAMENTOS    dbo
```

### Via Script Python

```bash
# Executar verificação
python3 testes/verificar_tabela_historico_pagamentos.py
```

**Resultado esperado:**
```
✅ Tabela HISTORICO_PAGAMENTOS existe no SQL Server
✅ Encontrados 22 campos na tabela
✅ Todos os 22 campos esperados estão presentes
✅ Encontrados 5 índices na tabela
🎉 Tabela HISTORICO_PAGAMENTOS está OK!
```

---

## 📊 Estrutura da Tabela

A tabela `HISTORICO_PAGAMENTOS` contém:

### Campos Principais

- `id_historico_pagamento` - ID único (IDENTITY, PRIMARY KEY)
- `payment_id` - ID único do pagamento (UNIQUE, NOT NULL)
- `tipo_pagamento` - Tipo: 'BOLETO', 'PIX', 'TED', 'BARCODE'
- `banco` - Banco: 'SANTANDER', 'BANCO_DO_BRASIL'
- `ambiente` - Ambiente: 'SANDBOX', 'PRODUCAO'
- `status` - Status: 'READY_TO_PAY', 'PENDING_VALIDATION', 'PAYED', 'CANCELLED', 'FAILED'
- `valor` - Valor do pagamento (DECIMAL(18,2))
- `codigo_barras` - Código de barras (para boletos)
- `beneficiario` - Nome do beneficiário
- `vencimento` - Data de vencimento
- `agencia_origem` - Agência de origem
- `conta_origem` - Conta de origem
- `saldo_disponivel_antes` - Saldo antes do pagamento
- `saldo_apos_pagamento` - Saldo após pagamento
- `workspace_id` - ID do workspace
- `payment_date` - Data do pagamento
- `data_inicio` - Quando foi iniciado
- `data_efetivacao` - Quando foi efetivado
- `dados_completos` - JSON com todos os dados retornados pela API (NVARCHAR(MAX))
- `observacoes` - Observações adicionais
- `criado_em` - Data de criação (DEFAULT GETDATE())
- `atualizado_em` - Data de atualização (DEFAULT GETDATE())

### Índices Criados

1. `idx_historico_pagamentos_payment_id` - Busca rápida por payment_id
2. `idx_historico_pagamentos_status` - Filtro por status e data
3. `idx_historico_pagamentos_tipo` - Filtro por tipo, banco e ambiente
4. `idx_historico_pagamentos_data` - Ordenação por data de efetivação
5. `idx_historico_pagamentos_banco_ambiente` - Filtro por banco e ambiente

---

## ⚠️ Notas Importantes

1. **Script Idempotente**: O script usa `IF NOT EXISTS`, então pode ser executado várias vezes sem problemas. Se a tabela já existir, apenas os índices faltantes serão criados.

2. **Backup**: Antes de executar em produção, faça backup do banco de dados.

3. **Permissões**: Certifique-se de ter permissões para criar tabelas no banco `mAIke_assistente`.

---

## 🔍 Troubleshooting

### Erro: "Cannot find the object 'dbo.HISTORICO_PAGAMENTOS'"

**Causa**: Tabela não existe ainda.  
**Solução**: Execute o script SQL completo.

### Erro: "There is already an object named 'HISTORICO_PAGAMENTOS'"

**Causa**: Tabela já existe.  
**Solução**: Isso é normal. O script verifica antes de criar. Se quiser recriar, primeiro faça `DROP TABLE dbo.HISTORICO_PAGAMENTOS;`

### Erro: "Incorrect syntax near 'GO'"

**Causa**: Executando em ferramenta que não suporta `GO`.  
**Solução**: Remover comandos `GO` ou executar em SSMS/Azure Data Studio.

---

## 📝 Próximos Passos

Após criar a tabela:

1. ✅ **Verificar** se foi criada corretamente
2. ✅ **Testar** gravação de pagamentos (processar um boleto)
3. ✅ **Verificar** se dados aparecem na UI (menu → Histórico de Pagamentos)

---

**Última atualização:** 13/01/2026
