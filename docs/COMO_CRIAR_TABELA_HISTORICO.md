# 📋 Como Criar a Tabela HISTORICO_DOCUMENTO_ADUANEIRO

**Data:** 08/01/2026  
**Status:** ✅ Script Pronto

---

## 🎯 Objetivo

Criar a tabela `HISTORICO_DOCUMENTO_ADUANEIRO` no banco `mAIke_assistente` para armazenar o histórico de mudanças em documentos aduaneiros.

---

## 🚀 Opção 1: Script Simples (Recomendado)

### Executar Script Simples

```sql
-- No SQL Server Management Studio ou Azure Data Studio:
-- 1. Conectar ao servidor: 172.16.10.241\SQLEXPRESS
-- 2. Abrir arquivo: scripts/criar_tabela_historico_documentos.sql
-- 3. Executar (F5)
```

**Ou via linha de comando:**

```bash
# Via sqlcmd (se tiver instalado)
sqlcmd -S 172.16.10.241\SQLEXPRESS -d mAIke_assistente -U sa -P "sua_senha" -i scripts/criar_tabela_historico_documentos.sql
```

---

## 🚀 Opção 2: Script Completo (Todas as Tabelas)

Se quiser criar todas as 30 tabelas do banco completo:

```sql
-- No SQL Server Management Studio:
-- 1. Abrir arquivo: scripts/criar_banco_maike_completo.sql
-- 2. Executar (F5)
```

**⚠️ ATENÇÃO:** Este script cria TODAS as tabelas. Se já tiver algumas tabelas, ele apenas cria as que faltam.

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
WHERE TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO';
```

**Resultado esperado:**
```
TABLE_NAME                      TABLE_SCHEMA
HISTORICO_DOCUMENTO_ADUANEIRO  dbo
```

### Via Script Python

```bash
# Executar diagnóstico
python3 testes/test_conexao_sql_server.py
```

**Resultado esperado:**
```
✅ Conexão SQL Server: ✅ OK
✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO: ✅ EXISTE
```

---

## 📊 Estrutura da Tabela

A tabela `HISTORICO_DOCUMENTO_ADUANEIRO` contém:

### Campos Principais

- `id_historico` - ID único do registro
- `numero_documento` - Número do documento (CE, DI, DUIMP, CCT)
- `tipo_documento` - Tipo ('CE', 'DI', 'DUIMP', 'CCT')
- `processo_referencia` - Referência do processo (ex: 'ALH.0168/25')
- `data_evento` - Data/hora do evento
- `tipo_evento` - Tipo do evento ('MUDANCA_STATUS', 'MUDANCA_CANAL', etc.)
- `campo_alterado` - Campo que mudou
- `valor_anterior` - Valor anterior
- `valor_novo` - Valor novo
- `fonte_dados` - Fonte ('INTEGRACOMEX', 'PORTAL_UNICO', 'KANBAN_API')
- `json_dados_originais` - JSON completo da API no momento do evento

### Índices Criados

- `idx_documento` - Por id_documento e data_evento
- `idx_numero_documento` - Por numero_documento, tipo_documento e data_evento
- `idx_processo` - Por processo_referencia e data_evento
- `idx_tipo_evento` - Por tipo_evento e data_evento
- `idx_campo_alterado` - Por campo_alterado e data_evento
- `idx_fonte_dados` - Por fonte_dados e data_evento

---

## 🔍 Consultas Úteis

### Ver Últimos Históricos

```sql
SELECT TOP 10
    numero_documento,
    tipo_documento,
    tipo_evento,
    campo_alterado,
    valor_anterior,
    valor_novo,
    data_evento,
    fonte_dados
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
ORDER BY data_evento DESC
```

### Histórico de um Documento Específico

```sql
SELECT 
    tipo_evento,
    campo_alterado,
    valor_anterior,
    valor_novo,
    data_evento
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
WHERE numero_documento = '132505371482300'
  AND tipo_documento = 'CE'
ORDER BY data_evento DESC
```

### Histórico de um Processo

```sql
SELECT 
    numero_documento,
    tipo_documento,
    tipo_evento,
    campo_alterado,
    valor_anterior,
    valor_novo,
    data_evento
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
WHERE processo_referencia = 'ALH.0168/25'
ORDER BY data_evento DESC
```

---

## ⚠️ Troubleshooting

### Erro: "Tabela já existe"

**Solução:** A tabela já foi criada. Isso é OK! O script verifica e não recria.

### Erro: "Permissão negada"

**Solução:** Execute como usuário com permissões de DBA (sa ou equivalente).

### Erro: "Banco não existe"

**Solução:** Certifique-se de que o banco `mAIke_assistente` existe. Se não existir, execute o script completo primeiro.

---

## ✅ Próximos Passos

Após criar a tabela:

1. ✅ Verificar criação:
   ```bash
   python3 testes/test_conexao_sql_server.py
   ```

2. ✅ Executar testes completos:
   ```bash
   python3 testes/test_historico_documentos.py
   ```

3. ✅ Validar em produção:
   - Consultar um documento via mAIke
   - Verificar se histórico foi gravado
   - Verificar se mudanças são detectadas

---

**Última atualização:** 08/01/2026

