# 📋 Instruções - Criar Tabelas de Impostos e Valores

**Data:** 08/01/2026  
**Objetivo:** Criar tabelas `IMPOSTO_IMPORTACAO` e `VALOR_MERCADORIA` no SQL Server

---

## 🎯 O que será criado

### 1. **IMPOSTO_IMPORTACAO**
Tabela para armazenar impostos pagos da DI/DUIMP:
- II (Imposto de Importação)
- IPI (Imposto sobre Produtos Industrializados)
- PIS
- COFINS
- Taxa de Utilização SISCOMEX
- Antidumping
- ICMS

### 2. **VALOR_MERCADORIA**
Tabela para armazenar valores da mercadoria:
- Valor Mercadoria Descarga (BRL/USD)
- Valor Mercadoria Embarque (BRL/USD)
- FOB, CIF, VMLE, VMLD

---

## 📋 Pré-requisitos

1. ✅ Banco `mAIke_assistente` deve existir
2. ✅ Tabela `PROCESSO_IMPORTACAO` deve existir (para Foreign Key)
3. ✅ Acesso ao SQL Server com permissões de DBA
4. ✅ Python 3.9+ instalado
5. ✅ Dependências Python instaladas (`python-dotenv`, `pyodbc` ou Node.js)

---

## 🚀 Método 1: Via Python (Recomendado)

### Passo 1: Verificar conexão

```bash
# Verificar se .env está configurado
cat .env | grep SQL_SERVER
```

### Passo 2: Executar script Python

```bash
cd /Users/helenomaffra/Chat-IA-Independente
python3 scripts/executar_criar_impostos_valores.py
```

### Passo 3: Verificar resultado

O script mostrará:
- ✅ Tabelas criadas com sucesso
- 📊 Número de registros (deve ser 0 inicialmente)
- ❌ Erros, se houver

---

## 🚀 Método 2: Via SQL Server Management Studio (SSMS)

### Passo 1: Abrir SSMS

1. Conectar ao servidor SQL Server
2. Selecionar banco `mAIke_assistente`

### Passo 2: Executar script SQL

1. Abrir arquivo: `scripts/criar_tabelas_impostos_valores.sql`
2. Executar script completo (F5)
3. Verificar mensagens de sucesso

### Passo 3: Verificar tabelas

```sql
-- Verificar se tabelas existem
SELECT 
    TABLE_NAME,
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_NAME = t.TABLE_NAME) as num_colunas
FROM INFORMATION_SCHEMA.TABLES t
WHERE TABLE_SCHEMA = 'dbo' 
  AND TABLE_NAME IN ('IMPOSTO_IMPORTACAO', 'VALOR_MERCADORIA')
ORDER BY TABLE_NAME;
```

---

## 📊 Estrutura das Tabelas

### IMPOSTO_IMPORTACAO

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id_imposto` | BIGINT | PK, Identity |
| `processo_referencia` | VARCHAR(50) | FK → PROCESSO_IMPORTACAO |
| `numero_documento` | VARCHAR(50) | DI ou DUIMP |
| `tipo_documento` | VARCHAR(10) | 'DI' ou 'DUIMP' |
| `tipo_imposto` | VARCHAR(50) | 'II', 'IPI', 'PIS', 'COFINS', etc. |
| `codigo_receita` | VARCHAR(10) | Código da receita |
| `valor_brl` | DECIMAL(18,2) | Valor em BRL |
| `valor_usd` | DECIMAL(18,2) | Valor em USD |
| `data_pagamento` | DATETIME | Data do pagamento |
| `pago` | BIT | Se foi pago |
| `fonte_dados` | VARCHAR(50) | 'SQL_SERVER', 'PORTAL_UNICO', etc. |

### VALOR_MERCADORIA

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id_valor` | BIGINT | PK, Identity |
| `processo_referencia` | VARCHAR(50) | FK → PROCESSO_IMPORTACAO |
| `numero_documento` | VARCHAR(50) | DI ou DUIMP |
| `tipo_documento` | VARCHAR(10) | 'DI' ou 'DUIMP' |
| `tipo_valor` | VARCHAR(50) | 'DESCARGA', 'EMBARQUE', 'FOB', etc. |
| `moeda` | VARCHAR(3) | 'BRL', 'USD', 'EUR' |
| `valor` | DECIMAL(18,2) | Valor |
| `taxa_cambio` | DECIMAL(10,6) | Taxa de câmbio |
| `data_valor` | DATETIME | Data de referência |
| `fonte_dados` | VARCHAR(50) | 'SQL_SERVER', 'PORTAL_UNICO', etc. |

---

## ✅ Verificação Pós-Criação

### Verificar tabelas criadas

```sql
-- Verificar estrutura
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo' 
  AND TABLE_NAME = 'IMPOSTO_IMPORTACAO'
ORDER BY ORDINAL_POSITION;
```

### Verificar índices

```sql
-- Verificar índices criados
SELECT 
    i.name AS index_name,
    i.type_desc,
    STRING_AGG(c.name, ', ') AS columns
FROM sys.indexes i
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.object_id = OBJECT_ID('dbo.IMPOSTO_IMPORTACAO')
GROUP BY i.name, i.type_desc;
```

### Verificar Foreign Keys

```sql
-- Verificar Foreign Keys
SELECT 
    fk.name AS foreign_key_name,
    OBJECT_NAME(fk.parent_object_id) AS table_name,
    COL_NAME(fc.parent_object_id, fc.parent_column_id) AS column_name,
    OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
    COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS referenced_column
FROM sys.foreign_keys fk
INNER JOIN sys.foreign_key_columns fc ON fk.object_id = fc.constraint_object_id
WHERE OBJECT_NAME(fk.parent_object_id) IN ('IMPOSTO_IMPORTACAO', 'VALOR_MERCADORIA');
```

---

## 🔧 Troubleshooting

### Erro: "Foreign key constraint failed"

**Causa:** Tabela `PROCESSO_IMPORTACAO` não existe ou não tem registros.

**Solução:**
1. Verificar se `PROCESSO_IMPORTACAO` existe:
   ```sql
   SELECT * FROM INFORMATION_SCHEMA.TABLES 
   WHERE TABLE_NAME = 'PROCESSO_IMPORTACAO';
   ```
2. Se não existir, criar primeiro (ver `scripts/criar_banco_maike_completo.sql`)

### Erro: "Table already exists"

**Causa:** Tabela já foi criada anteriormente.

**Solução:**
- O script verifica se a tabela existe antes de criar
- Se quiser recriar, dropar primeiro:
  ```sql
  DROP TABLE IF EXISTS [dbo].[IMPOSTO_IMPORTACAO];
  DROP TABLE IF EXISTS [dbo].[VALOR_MERCADORIA];
  ```

### Erro: "Permission denied"

**Causa:** Usuário não tem permissões de DBA.

**Solução:**
- Executar como usuário com permissões `db_owner` ou `db_ddladmin`
- Ou solicitar ao DBA para executar o script

---

## 📝 Próximos Passos

Após criar as tabelas:

1. ✅ **Implementar serviço de gravação** (`ImpostoValorService`)
2. ✅ **Integrar na sincronização do Kanban** (`ProcessoKanbanService`)
3. ✅ **Integrar nas consultas diretas** (DI/DUIMP agents)
4. ✅ **Criar script de backfill** para popular dados históricos

---

## 📚 Referências

- **Documentação:** `docs/ESTRATEGIA_POPULACAO_BANCO_MAIKE.md`
- **Script SQL:** `scripts/criar_tabelas_impostos_valores.sql`
- **Script Python:** `scripts/executar_criar_impostos_valores.py`

---

**Última atualização:** 08/01/2026


