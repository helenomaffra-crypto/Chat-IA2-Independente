# 📋 Histórico de Mudanças de Documentos (DI, DUIMP, CE, CCT)

**Data:** 08/01/2026  
**Status:** 📋 Documentação de Requisitos  
**Prioridade:** ⭐ **CRÍTICA** - Histórico relevante para auditoria

---

## 🎯 Contexto

**Todas as APIs (Integra Comex e DUIMP) trazem mudanças de DI, DUIMP, CE e CCT.**

Essas mudanças incluem:
- ✅ **Situações (status)** - Ex: "REGISTRADA", "DESEMBARACADA", "CANCELADA"
- ✅ **Datas importantes** - Ex: data de registro, data de desembaraço
- ✅ **Valores** - Ex: valores de impostos, valores de frete
- ✅ **Canal** - Ex: "VERDE", "AMARELO", "VERMELHO"
- ✅ **Outros campos relevantes**

**Esses históricos são relevantes e devem ser gravados também.**

---

## 📊 Estrutura Necessária

### Tabela: `HISTORICO_DOCUMENTO_ADUANEIRO`

**Descrição:** Histórico completo de todas as mudanças em documentos aduaneiros (DI, DUIMP, CE, CCT).

**Campos principais:**
```sql
CREATE TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO] (
    -- Identificação
    id_historico BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_documento BIGINT NOT NULL,                    -- FK para DOCUMENTO_ADUANEIRO
    numero_documento VARCHAR(50) NOT NULL,           -- Ex: "123456789", "25BR00002369283"
    tipo_documento VARCHAR(50) NOT NULL,             -- Ex: "CE", "CCT", "DI", "DUIMP"
    
    -- Vínculo com Processo
    processo_referencia VARCHAR(50),                 -- FK para PROCESSO_IMPORTACAO
    
    -- Mudança Registrada
    data_evento DATETIME NOT NULL,                   -- Data/hora da mudança (da API)
    tipo_evento VARCHAR(50) NOT NULL,                -- Ex: 'MUDANCA_STATUS', 'MUDANCA_CANAL', 'MUDANCA_VALOR'
    tipo_evento_descricao VARCHAR(255),              -- Descrição do tipo de evento
    
    -- Campos Alterados
    campo_alterado VARCHAR(100) NOT NULL,             -- Ex: 'status_documento', 'situacao_documento', 'canal_documento'
    valor_anterior VARCHAR(500),                     -- Valor anterior do campo
    valor_novo VARCHAR(500),                          -- Valor novo do campo
    
    -- Status Detalhado (snapshot no momento da mudança)
    status_documento VARCHAR(100),                   -- Status no momento da mudança
    status_documento_codigo VARCHAR(20),
    canal_documento VARCHAR(20),
    situacao_documento VARCHAR(100),
    
    -- Datas (snapshot no momento da mudança)
    data_registro DATETIME,
    data_situacao DATETIME,
    data_desembaraco DATETIME,
    
    -- Origem da Mudança
    fonte_dados VARCHAR(50) NOT NULL,                -- Ex: "INTEGRACOMEX", "DUIMP_API", "PORTAL_UNICO"
    api_endpoint VARCHAR(500),                       -- Endpoint da API que retornou a mudança
    json_dados_originais NVARCHAR(MAX),              -- JSON completo retornado pela API
    
    -- Metadados
    usuario_ou_sistema VARCHAR(100),                 -- Quem/sistema que detectou a mudança
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE()             -- Data/hora que foi gravado no banco
);
```

**Índices:**
```sql
CREATE INDEX idx_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](id_documento, data_evento DESC);
CREATE INDEX idx_numero_documento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](numero_documento, tipo_documento, data_evento DESC);
CREATE INDEX idx_processo ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](processo_referencia, data_evento DESC);
CREATE INDEX idx_tipo_evento ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](tipo_evento, data_evento DESC);
CREATE INDEX idx_campo_alterado ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](campo_alterado, data_evento DESC);
CREATE INDEX idx_fonte_dados ON [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO](fonte_dados, data_evento DESC);
```

---

## 🔄 Como Funciona

### 1. **Detecção de Mudanças**

Quando uma API (Integra Comex, DUIMP) retorna dados de um documento:

1. **Buscar versão anterior** do documento no banco
2. **Comparar campos relevantes:**
   - `status_documento` / `situacao_documento`
   - `canal_documento`
   - `data_registro`, `data_situacao`, `data_desembaraco`
   - Valores financeiros (se mudaram)
3. **Se houver mudança:**
   - Gravar na tabela `HISTORICO_DOCUMENTO_ADUANEIRO`
   - Atualizar tabela `DOCUMENTO_ADUANEIRO` com valores novos
   - Opcionalmente: Criar notificação (se mudança importante)

### 2. **Tipos de Eventos**

**`MUDANCA_STATUS`:**
- Quando `status_documento` ou `situacao_documento` muda
- Ex: "REGISTRADA" → "DESEMBARACADA"

**`MUDANCA_CANAL`:**
- Quando `canal_documento` muda
- Ex: "VERDE" → "AMARELO"

**`MUDANCA_DATA`:**
- Quando datas importantes mudam
- Ex: `data_desembaraco` mudou

**`MUDANCA_VALOR`:**
- Quando valores financeiros mudam
- Ex: `valor_ii_brl` mudou

**`MUDANCA_OUTROS`:**
- Outras mudanças relevantes

### 3. **Integração com TIMELINE_PROCESSO**

A tabela `TIMELINE_PROCESSO` registra mudanças no **processo** como um todo.

A tabela `HISTORICO_DOCUMENTO_ADUANEIRO` registra mudanças em **documentos específicos** (DI, DUIMP, CE, CCT).

**Exemplo:**
- **TIMELINE_PROCESSO:** "Processo ALH.0018/25: DI registrada"
- **HISTORICO_DOCUMENTO_ADUANEIRO:** "DI 25BR123456789: Status mudou de 'PENDENTE' para 'REGISTRADA'"

---

## 📋 Campos Relevantes por Tipo de Documento

### DI (Declaração de Importação)

**Campos que devem ser rastreados:**
- `status_documento` / `situacao_documento`
- `canal_documento`
- `data_registro`
- `data_situacao`
- `data_desembaraco`
- `valor_ii_brl`, `valor_ipi_brl`, etc.

**Fontes:**
- Integra Comex API
- Portal Único
- SQL Server (cache)

### DUIMP (Declaração Única de Importação)

**Campos que devem ser rastreados:**
- `status_documento` / `situacao_documento`
- `canal_documento`
- `data_registro`
- `data_situacao`
- `data_desembaraco`
- `versao_documento`
- `valor_ii_brl`, `valor_ipi_brl`, etc.

**Fontes:**
- DUIMP API
- Integra Comex API
- Portal Único

### CE (Conhecimento de Embarque)

**Campos que devem ser rastreados:**
- `status_documento` / `situacao_documento`
- `data_registro`
- `data_situacao`
- `data_desembaraco`
- `data_entrega_carga`

**Fontes:**
- Integra Comex API
- Portal Único

### CCT (Conhecimento de Carga Aérea)

**Campos que devem ser rastreados:**
- `status_documento` / `situacao_documento`
- `data_registro`
- `data_situacao`
- `data_chegada_efetiva`
- `data_desembaraco`

**Fontes:**
- Integra Comex API
- Portal Único

---

## 🔄 Fluxo de Sincronização

### 1. **Sincronização Automática**

**Quando:** A cada consulta à API (Integra Comex, DUIMP)

**Processo:**
1. Consultar API para obter dados atualizados do documento
2. Buscar versão anterior no banco (`DOCUMENTO_ADUANEIRO`)
3. Comparar campos relevantes
4. Se houver mudança:
   - Gravar na `HISTORICO_DOCUMENTO_ADUANEIRO`
   - Atualizar `DOCUMENTO_ADUANEIRO`
   - Criar notificação (se mudança importante)

### 2. **Sincronização Manual**

**Quando:** Usuário solicita atualização de um documento específico

**Processo:**
- Mesmo processo da sincronização automática
- Pode incluir validação adicional

---

## ✅ Verificação: O Planejamento Cobre?

### ✅ **Coberto:**

1. ✅ **Tabela `DOCUMENTO_ADUANEIRO`**
   - Armazena estado atual de cada documento
   - Campos de status, datas, valores

2. ✅ **Tabela `TIMELINE_PROCESSO`**
   - Registra mudanças no processo como um todo
   - Pode incluir mudanças de documentos

### ⚠️ **Falta:**

1. ⚠️ **Tabela `HISTORICO_DOCUMENTO_ADUANEIRO`**
   - **NÃO existe no planejamento atual**
   - **NECESSÁRIA** para rastrear mudanças específicas de documentos

---

## 🎯 Próximos Passos

1. ✅ **Adicionar tabela `HISTORICO_DOCUMENTO_ADUANEIRO` ao planejamento**
2. ✅ **Atualizar script SQL** para incluir a nova tabela
3. ⏳ **Criar serviço de sincronização** que:
   - Detecta mudanças em documentos
   - Grava histórico automaticamente
4. ⏳ **Integrar com APIs existentes** (Integra Comex, DUIMP)
5. ⏳ **Criar queries** para consultar histórico de documentos

---

**Última atualização:** 08/01/2026

