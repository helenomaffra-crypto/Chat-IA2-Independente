# 🧪 Guia de Testes - Banco mAIke_assistente

**Data:** 08/01/2026  
**Versão:** 1.0

---

## 📋 Visão Geral

Este guia descreve como testar o novo banco de dados SQL Server `mAIke_assistente` e suas funcionalidades.

---

## 🚀 Testes Rápidos

### 1. Teste de Conexão Básica

```bash
python3 testes/test_conexao_sql_server.py
```

**Resultado esperado:**
```
✅ Conexão SQL Server: ✅ OK
✅ Tabela HISTORICO_DOCUMENTO_ADUANEIRO: ✅ EXISTE
```

---

### 2. Teste Completo do Banco

```bash
python3 testes/test_banco_maike_completo.py
```

**O que testa:**
- ✅ Conexão com SQL Server
- ✅ Estrutura do banco (tabelas principais)
- ✅ Tabela de histórico (colunas, índices)
- ✅ Consultas básicas (SELECT, COUNT, ORDER BY)
- ✅ Integração com serviços (DocumentoHistoricoService, singleton)

**Resultado esperado:**
```
🎉 TODOS OS TESTES PASSARAM!
```

---

### 3. Teste de Histórico de Documentos

```bash
python3 testes/test_historico_documentos.py
```

**O que testa:**
- ✅ Documento novo (primeira consulta)
- ✅ Mudança de status
- ✅ Mudança de canal
- ✅ Sem mudanças (consulta repetida)
- ✅ Validação de dados gravados

**Resultado esperado:**
```
🎉 TODOS OS TESTES PASSARAM!
```

---

## 🔍 Testes Manuais

### 1. Verificar Tabelas Criadas

**Via SQL Server Management Studio:**

```sql
USE [mAIke_assistente];
GO

-- Listar todas as tabelas
SELECT 
    TABLE_SCHEMA,
    TABLE_NAME,
    (SELECT COUNT(*) 
     FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE TABLE_NAME = t.TABLE_NAME) as COLUNAS
FROM INFORMATION_SCHEMA.TABLES t
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;
```

**Resultado esperado:** Lista de todas as tabelas criadas.

---

### 2. Verificar Tabela de Histórico

```sql
-- Verificar estrutura
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo' 
  AND TABLE_NAME = 'HISTORICO_DOCUMENTO_ADUANEIRO'
ORDER BY ORDINAL_POSITION;
```

**Resultado esperado:** 24 colunas listadas.

---

### 3. Verificar Índices

```sql
-- Verificar índices da tabela de histórico
SELECT 
    i.name AS INDEX_NAME,
    i.type_desc AS INDEX_TYPE,
    STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) AS COLUMNS
FROM sys.indexes i
INNER JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.object_id = OBJECT_ID(N'[dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]')
  AND i.index_id > 0
GROUP BY i.name, i.type_desc
ORDER BY i.name;
```

**Resultado esperado:** 6 índices listados.

---

### 4. Consultar Histórico de Documentos

```sql
-- Ver últimos históricos
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
ORDER BY data_evento DESC;
```

**Resultado esperado:** Lista dos últimos 10 registros de histórico.

---

### 5. Histórico de um Documento Específico

```sql
-- Histórico de um CE específico
SELECT 
    tipo_evento,
    campo_alterado,
    valor_anterior,
    valor_novo,
    data_evento,
    fonte_dados
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
WHERE numero_documento = '132505371482300'
  AND tipo_documento = 'CE'
ORDER BY data_evento DESC;
```

**Resultado esperado:** Histórico completo do documento.

---

### 6. Histórico de um Processo

```sql
-- Histórico de todos os documentos de um processo
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
ORDER BY data_evento DESC;
```

**Resultado esperado:** Histórico de todos os documentos do processo.

---

## 🧪 Testes de Integração

### 1. Testar Consulta de Documento via mAIke

**Via Interface Web:**

1. Acesse: `http://localhost:5001`
2. Digite: "consultar CE 132505371482300"
3. Verifique se o histórico foi gravado:

```sql
SELECT * 
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
WHERE numero_documento = '132505371482300'
  AND tipo_documento = 'CE'
ORDER BY data_evento DESC;
```

**Resultado esperado:** Registro de histórico criado.

---

### 2. Testar Mudança de Status

**Simulação:**

1. Consultar um documento via API
2. Aguardar mudança de status (ou simular)
3. Consultar novamente
4. Verificar se mudança foi detectada:

```sql
SELECT 
    tipo_evento,
    campo_alterado,
    valor_anterior,
    valor_novo,
    data_evento
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
WHERE numero_documento = 'NUMERO_DOCUMENTO'
  AND tipo_documento = 'CE'
  AND tipo_evento = 'MUDANCA_STATUS'
ORDER BY data_evento DESC;
```

**Resultado esperado:** Registro de mudança de status.

---

## 📊 Testes de Performance

### 1. Contar Registros

```sql
-- Contar total de registros
SELECT COUNT(*) as total
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO];
```

**Resultado esperado:** Número total de registros.

---

### 2. Testar Performance de Consultas

```sql
-- Teste de performance: consulta por documento
SET STATISTICS TIME ON;

SELECT *
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
WHERE numero_documento = '132505371482300'
  AND tipo_documento = 'CE'
ORDER BY data_evento DESC;

SET STATISTICS TIME OFF;
```

**Resultado esperado:** Consulta rápida (< 1 segundo).

---

### 3. Verificar Uso de Índices

```sql
-- Verificar se índices estão sendo usados
SET SHOWPLAN_ALL ON;

SELECT *
FROM [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO]
WHERE numero_documento = '132505371482300'
  AND tipo_documento = 'CE'
ORDER BY data_evento DESC;

SET SHOWPLAN_ALL OFF;
```

**Resultado esperado:** Índices sendo usados na consulta.

---

## 🔧 Testes de Funcionalidades Específicas

### 1. Testar DocumentoHistoricoService

```python
from services.documento_historico_service import DocumentoHistoricoService

service = DocumentoHistoricoService()

# Simular dados de um CE
dados = {
    'numeroCE': '132505371482300',
    'situacaoCarga': 'DESCARREGADA',
    'canal': 'VERDE',
    # ... outros campos
}

# Registrar histórico
service.registrar_historico(
    numero_documento='132505371482300',
    tipo_documento='CE',
    dados_atual=dados,
    fonte_dados='INTEGRACOMEX',
    api_endpoint='/api/ce/consultar'
)
```

**Resultado esperado:** Histórico gravado no banco.

---

### 2. Testar Singleton do Adapter

```python
from utils.sql_server_adapter import get_sql_adapter

adapter1 = get_sql_adapter()
adapter2 = get_sql_adapter()
adapter3 = get_sql_adapter()

# Verificar se é a mesma instância
assert adapter1 is adapter2 is adapter3
print("✅ Singleton funcionando!")
```

**Resultado esperado:** Mesma instância reutilizada.

---

## 📝 Checklist de Testes

### Testes Básicos
- [ ] Conexão com SQL Server funciona
- [ ] Banco `mAIke_assistente` existe
- [ ] Tabela `HISTORICO_DOCUMENTO_ADUANEIRO` existe
- [ ] Todas as colunas principais existem
- [ ] Índices foram criados

### Testes de Funcionalidade
- [ ] Consultas básicas funcionam (SELECT, COUNT, ORDER BY)
- [ ] Histórico de documentos é gravado
- [ ] Mudanças são detectadas corretamente
- [ ] Consultas por documento funcionam
- [ ] Consultas por processo funcionam

### Testes de Integração
- [ ] DocumentoHistoricoService funciona
- [ ] Integração com Integra Comex funciona
- [ ] Integração com Portal Único funciona
- [ ] Integração com Kanban funciona
- [ ] Singleton do adapter funciona

### Testes de Performance
- [ ] Consultas são rápidas (< 1 segundo)
- [ ] Índices estão sendo usados
- [ ] Não há queries lentas

---

## 🐛 Troubleshooting

### Problema: "Tabela não encontrada"

**Solução:**
```bash
# Executar script SQL para criar tabela
# No SQL Server Management Studio:
# Abrir: scripts/criar_tabela_historico_documentos.sql
# Executar (F5)
```

---

### Problema: "Conexão falhou"

**Solução:**
1. Verificar se SQL Server está online
2. Verificar credenciais no `.env`
3. Testar conexão manualmente:

```bash
python3 testes/test_conexao_sql_server.py
```

---

### Problema: "Índices não encontrados"

**Solução:**
```sql
-- Recriar índices manualmente
CREATE INDEX idx_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](id_documento, data_evento DESC);
CREATE INDEX idx_numero_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](numero_documento, tipo_documento, data_evento DESC);
-- ... outros índices
```

---

## 📚 Arquivos Relacionados

- **Teste de Conexão:** `testes/test_conexao_sql_server.py`
- **Teste Completo:** `testes/test_banco_maike_completo.py`
- **Teste de Histórico:** `testes/test_historico_documentos.py`
- **Script SQL:** `scripts/criar_tabela_historico_documentos.sql`
- **Documentação:** `docs/RESUMO_EXECUTIVO_08_01_2026.md`

---

**Última atualização:** 08/01/2026

