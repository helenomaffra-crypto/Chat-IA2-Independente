# 📊 Estrutura do Banco de Dados - Exemplo: BGR.0070/25

**Data:** 08/01/2026  
**Objetivo:** Mostrar visualmente o que será gravado no banco `mAIke_assistente` para cada processo

---

## 🎯 Visão Geral

Para cada processo (ex: **BGR.0070/25**), o sistema grava dados em **múltiplas tabelas relacionadas**:

```
BGR.0070/25
├── PROCESSO_IMPORTACAO (1 registro)
├── DOCUMENTO_ADUANEIRO (múltiplos: CE, DI, DUIMP, CCT)
├── HISTORICO_DOCUMENTO_ADUANEIRO (múltiplos: mudanças ao longo do tempo)
├── IMPOSTO_IMPORTACAO (múltiplos: II, IPI, PIS, COFINS, Taxa)
├── VALOR_MERCADORIA (múltiplos: Descarga BRL/USD, Embarque BRL/USD)
├── LANCAMENTO_TIPO_DESPESA (múltiplos: despesas conciliadas)
└── TIMELINE_PROCESSO (múltiplos: eventos do processo)
```

---

## 📋 Tabela 1: PROCESSO_IMPORTACAO

**Descrição:** Registro principal do processo (1 registro por processo)

### **Exemplo: BGR.0070/25**

```sql
INSERT INTO [dbo].[PROCESSO_IMPORTACAO] (
    processo_referencia,           -- 'BGR.0070/25'
    categoria_processo,            -- 'BGR'
    numero_processo,               -- '0070'
    ano_processo,                  -- '25'
    
    -- Status
    status_atual,                   -- 'PARAMETRIZADA_AGUARDANDO_ANALISE_FISCAL'
    etapa_kanban,                   -- 'PARAMETRIZADA_AGUARDANDO_ANALISE_FISCAL'
    situacao_ce,                    -- 'VINCULADA_A_DOCUMENTO_DE_DESPACHO'
    situacao_di,                    -- 'PARAMETRIZADA_AGUARDANDO_ANALISE_FISCAL'
    situacao_entrega,               -- 'ENTREGA NAO AUTORIZADA'
    
    -- Datas
    data_criacao_processo,          -- '2025-01-06'
    data_embarque,                  -- NULL (se não disponível)
    data_desembaraco,               -- '2026-01-06'
    data_entrega,                   -- '2026-01-06'
    
    -- Transporte
    modal_transporte,               -- 'Marítimo'
    porto_origem_codigo,            -- 'CNNGB'
    porto_origem_nome,              -- 'NINGBO'
    porto_destino_codigo,           -- 'BRIOA'
    porto_destino_nome,             -- 'RIO DE JANEIRO'
    
    -- Documentos
    numero_ce,                      -- '172505417636125'
    numero_di,                      -- '2600362869'
    numero_duimp,                   -- NULL (se não houver)
    
    -- Valores (resumo)
    valor_fob_usd,                  -- 36458.38
    valor_fob_brl,                  -- 201514.78
    valor_frete_brl,                -- 1777.89
    valor_cif_brl,                  -- 203292.67
    
    -- Fonte
    fonte_dados,                    -- 'KANBAN' ou 'SQL_SERVER'
    json_dados_completos,           -- JSON completo do Kanban/SQL Server
    ultima_sincronizacao,           -- '2026-01-08 09:20:00'
    criado_em,                      -- '2026-01-08 09:20:00'
    atualizado_em                   -- '2026-01-08 09:20:00'
)
```

**Quando é gravado:**
- ✅ Sincronização automática do Kanban (a cada 5 min)
- ✅ Quando consulta processo via `ProcessoRepository`
- ✅ Quando cria/atualiza processo manualmente

---

## 📋 Tabela 2: DOCUMENTO_ADUANEIRO

**Descrição:** Documentos aduaneiros vinculados ao processo (múltiplos registros)

### **Exemplo: BGR.0070/25**

#### **2.1. CE (Conhecimento de Embarque)**

```sql
INSERT INTO [dbo].[DOCUMENTO_ADUANEIRO] (
    numero_documento,               -- '172505417636125'
    tipo_documento,                 -- 'CE'
    processo_referencia,            -- 'BGR.0070/25'
    
    -- Status
    situacao_documento,             -- 'VINCULADA_A_DOCUMENTO_DE_DESPACHO'
    canal_documento,                 -- NULL (CE não tem canal)
    
    -- Datas
    data_registro,                  -- Data de registro do CE
    data_situacao,                  -- Data da situação atual
    data_desembaraco,               -- Data de desembaraço
    
    -- Valores
    valor_frete_total,              -- 1777.89
    valor_frete_moeda,              -- 'BRL'
    
    -- Fonte
    fonte_dados,                    -- 'INTEGRACOMEX' ou 'KANBAN'
    json_dados_originais,           -- JSON completo da API
    criado_em,                      -- '2026-01-08 09:20:00'
    atualizado_em                   -- '2026-01-08 09:20:00'
)
```

#### **2.2. DI (Declaração de Importação)**

```sql
INSERT INTO [dbo].[DOCUMENTO_ADUANEIRO] (
    numero_documento,               -- '2600362869'
    tipo_documento,                 -- 'DI'
    processo_referencia,            -- 'BGR.0070/25'
    
    -- Status
    situacao_documento,             -- 'PARAMETRIZADA_AGUARDANDO_ANALISE_FISCAL'
    canal_documento,                -- NULL (se não disponível)
    situacao_entrega,               -- 'ENTREGA NAO AUTORIZADA'
    
    -- Datas
    data_registro,                  -- Data de registro da DI
    data_situacao,                  -- Data da situação atual
    data_desembaraco,               -- '2026-01-06'
    
    -- Importador
    nome_importador,                -- 'MASSY DO BRASIL COMERCIO EXTERIOR LTDA'
    
    -- Fonte
    fonte_dados,                    -- 'INTEGRACOMEX' ou 'SQL_SERVER'
    json_dados_originais,           -- JSON completo da API
    criado_em,                      -- '2026-01-08 09:20:00'
    atualizado_em                   -- '2026-01-08 09:20:00'
)
```

**Quando é gravado:**
- ✅ Quando consulta documento via API (`call_integracomex`, `call_portal`)
- ✅ Quando sincroniza processo do Kanban
- ✅ Quando detecta mudanças (via `DocumentoHistoricoService`)

---

## 📋 Tabela 3: HISTORICO_DOCUMENTO_ADUANEIRO

**Descrição:** Histórico de mudanças em documentos (múltiplos registros por documento)

### **Exemplo: BGR.0070/25 - DI 2600362869**

```sql
INSERT INTO [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO] (
    numero_documento,               -- '2600362869'
    tipo_documento,                 -- 'DI'
    processo_referencia,            -- 'BGR.0070/25'
    
    -- Evento
    tipo_evento,                    -- 'MUDANCA_STATUS'
    tipo_evento_descricao,         -- 'Status da DI mudou'
    campo_alterado,                 -- 'situacao_di'
    valor_anterior,                  -- 'DI Registrada'
    valor_novo,                     -- 'PARAMETRIZADA_AGUARDANDO_ANALISE_FISCAL'
    
    -- Status atual
    status_documento,                -- 'PARAMETRIZADA_AGUARDANDO_ANALISE_FISCAL'
    canal_documento,                 -- NULL
    
    -- Datas
    data_evento,                    -- '2026-01-07 10:30:00'
    data_registro,                  -- '2026-01-06'
    data_situacao,                  -- '2026-01-07'
    
    -- Fonte
    fonte_dados,                    -- 'INTEGRACOMEX' ou 'KANBAN'
    api_endpoint,                   -- '/carga/declaracao-importacao'
    json_dados_originais,           -- JSON completo da API
    criado_em                       -- '2026-01-08 09:20:00'
)
```

**Tipos de eventos:**
- `MUDANCA_STATUS` - Status/situação mudou
- `MUDANCA_CANAL` - Canal mudou (VERDE → AMARELO)
- `MUDANCA_DATA` - Datas importantes mudaram
- `MUDANCA_VALOR` - Valores financeiros mudaram
- `MUDANCA_OUTROS` - Outras mudanças relevantes

**Quando é gravado:**
- ✅ Quando consulta documento via API e detecta mudanças
- ✅ Quando sincroniza processo do Kanban e detecta mudanças
- ⚠️ **PROBLEMA ATUAL:** Não é gravado quando usa apenas cache

---

## 📋 Tabela 4: IMPOSTO_IMPORTACAO ⭐ **NOVO - PRECISA IMPLEMENTAR**

**Descrição:** Impostos pagos da DI/DUIMP (múltiplos registros por documento)

### **Exemplo: BGR.0070/25 - DI 2600362869**

#### **4.1. Imposto de Importação (II)**

```sql
INSERT INTO [dbo].[IMPOSTO_IMPORTACAO] (
    processo_referencia,            -- 'BGR.0070/25'
    numero_documento,               -- '2600362869'
    tipo_documento,                 -- 'DI'
    
    -- Tipo de Imposto
    tipo_imposto,                   -- 'II'
    codigo_receita,                 -- '0086' (código da receita)
    
    -- Valores
    valor_brl,                      -- 52393.86
    valor_usd,                      -- NULL (se não disponível)
    taxa_cambio,                    -- 5.5283 (se conversão)
    
    -- Datas
    data_pagamento,                 -- '2026-01-07'
    data_vencimento,                -- NULL (se não disponível)
    
    -- Status
    pago,                           -- 1 (true)
    numero_retificacao,             -- NULL (se não houver retificação)
    
    -- Fonte
    fonte_dados,                    -- 'SQL_SERVER' ou 'PORTAL_UNICO'
    json_dados_originais,           -- JSON completo da fonte
    criado_em,                      -- '2026-01-08 09:20:00'
    atualizado_em                   -- '2026-01-08 09:20:00'
)
```

#### **4.2. Taxa de Utilização (TAXA_UTILIZACAO)**

```sql
INSERT INTO [dbo].[IMPOSTO_IMPORTACAO] (
    processo_referencia,            -- 'BGR.0070/25'
    numero_documento,               -- '2600362869'
    tipo_documento,                 -- 'DI'
    tipo_imposto,                   -- 'TAXA_UTILIZACAO'
    valor_brl,                      -- 192.79
    data_pagamento,                 -- '2026-01-07'
    pago,                           -- 1
    fonte_dados,                    -- 'SQL_SERVER'
    ...
)
```

#### **4.3. PIS**

```sql
INSERT INTO [dbo].[IMPOSTO_IMPORTACAO] (
    ...
    tipo_imposto,                   -- 'PIS'
    valor_brl,                      -- 4231.81
    data_pagamento,                 -- '2026-01-07'
    ...
)
```

#### **4.4. COFINS**

```sql
INSERT INTO [dbo].[IMPOSTO_IMPORTACAO] (
    ...
    tipo_imposto,                   -- 'COFINS'
    valor_brl,                      -- 20655.27
    data_pagamento,                 -- '2026-01-07'
    ...
)
```

**Total de impostos para BGR.0070/25:**
- II: R$ 52,393.86
- Taxa: R$ 192.79
- PIS: R$ 4,231.81
- COFINS: R$ 20,655.27
- **Total: R$ 77,473.73**

**Quando será gravado:**
- ⚠️ **AINDA NÃO IMPLEMENTADO**
- ✅ Quando consultar DI/DUIMP e houver impostos pagos
- ✅ Quando sincronizar processo do Kanban e houver DI/DUIMP
- ✅ Quando detectar mudanças em impostos (via histórico)

---

## 📋 Tabela 5: VALOR_MERCADORIA ⭐ **NOVO - PRECISA IMPLEMENTAR**

**Descrição:** Valores da mercadoria (Descarga, Embarque) em BRL e USD

### **Exemplo: BGR.0070/25 - DI 2600362869**

#### **5.1. Valor Mercadoria Descarga (BRL)**

```sql
INSERT INTO [dbo].[VALOR_MERCADORIA] (
    processo_referencia,            -- 'BGR.0070/25'
    numero_documento,               -- '2600362869'
    tipo_documento,                 -- 'DI'
    
    -- Tipo de Valor
    tipo_valor,                     -- 'DESCARGA'
    moeda,                          -- 'BRL'
    
    -- Valores
    valor,                          -- 201514.78
    taxa_cambio,                    -- NULL (já está em BRL)
    
    -- Datas
    data_valor,                     -- '2026-01-06'
    data_atualizacao,               -- '2026-01-08 09:20:00'
    
    -- Fonte
    fonte_dados,                    -- 'SQL_SERVER'
    json_dados_originais,           -- JSON completo da fonte
    criado_em,                      -- '2026-01-08 09:20:00'
    atualizado_em                   -- '2026-01-08 09:20:00'
)
```

#### **5.2. Valor Mercadoria Descarga (USD)**

```sql
INSERT INTO [dbo].[VALOR_MERCADORIA] (
    ...
    tipo_valor,                     -- 'DESCARGA'
    moeda,                          -- 'USD'
    valor,                          -- 37458.37
    taxa_cambio,                    -- 5.5283
    ...
)
```

#### **5.3. Valor Mercadoria Embarque (BRL)**

```sql
INSERT INTO [dbo].[VALOR_MERCADORIA] (
    ...
    tipo_valor,                     -- 'EMBARQUE'
    moeda,                          -- 'BRL'
    valor,                          -- 198825.00
    ...
)
```

#### **5.4. Valor Mercadoria Embarque (USD)**

```sql
INSERT INTO [dbo].[VALOR_MERCADORIA] (
    ...
    tipo_valor,                     -- 'EMBARQUE'
    moeda,                          -- 'USD'
    valor,                          -- 36958.38
    taxa_cambio,                    -- 5.5283
    ...
)
```

**Valores para BGR.0070/25:**
- Descarga BRL: R$ 201,514.78
- Descarga USD: $37,458.37
- Embarque BRL: R$ 198,825.00
- Embarque USD: $36,958.38

**Quando será gravado:**
- ⚠️ **AINDA NÃO IMPLEMENTADO**
- ✅ Quando consultar DI/DUIMP e houver valores
- ✅ Quando sincronizar processo do Kanban e houver DI/DUIMP
- ✅ Quando detectar mudanças em valores (via histórico)

---

## 📋 Tabela 6: LANCAMENTO_TIPO_DESPESA

**Descrição:** Despesas conciliadas (vinculadas a lançamentos bancários)

### **Exemplo: BGR.0070/25 - AFRMM**

```sql
INSERT INTO [dbo].[LANCAMENTO_TIPO_DESPESA] (
    id_movimentacao_bancaria,       -- FK para MOVIMENTACAO_BANCARIA
    id_tipo_despesa,                -- FK para TIPO_DESPESA (AFRMM)
    processo_referencia,            -- 'BGR.0070/25'
    categoria_processo,             -- 'BGR'
    
    -- Valores
    valor_despesa,                  -- 785.16
    percentual_valor,               -- 100.0 (se dividido, seria menor)
    
    -- Rastreamento (Compliance)
    origem_recurso,                 -- 'CONTA_CORRENTE_BB_50483'
    banco_origem,                   -- 'BB'
    agencia_origem,                 -- '1251'
    conta_origem,                   -- '50483'
    data_pagamento,                 -- '2026-01-07'
    
    -- Metadados
    criado_em,                      -- '2026-01-08 09:20:00'
    atualizado_em                   -- '2026-01-08 09:20:00'
)
```

**Despesas conciliadas para BGR.0070/25:**
- AFRMM: R$ 785.16 (pago em 07/01/2026, BB Ag. 1251 C/C 50483)

**Quando é gravado:**
- ✅ Quando usuário concilia lançamento bancário com processo
- ✅ Quando usuário classifica despesa e vincula a processo

---

## 📋 Tabela 7: TIMELINE_PROCESSO

**Descrição:** Timeline de eventos do processo (múltiplos registros)

### **Exemplo: BGR.0070/25**

```sql
INSERT INTO [dbo].[TIMELINE_PROCESSO] (
    processo_referencia,            -- 'BGR.0070/25'
    
    -- Evento
    tipo_evento,                   -- 'DI_REGISTRADA', 'CE_VINCULADO', 'IMPOSTO_PAGO', etc.
    descricao_evento,              -- 'DI 2600362869 registrada'
    data_evento,                   -- '2026-01-06'
    
    -- Documento relacionado
    numero_documento,              -- '2600362869'
    tipo_documento,                -- 'DI'
    
    -- Fonte
    fonte_dados,                   -- 'KANBAN', 'SQL_SERVER', 'INTEGRACOMEX'
    criado_em                      -- '2026-01-08 09:20:00'
)
```

**Eventos para BGR.0070/25:**
- CE 172505417636125 vinculado
- DI 2600362869 registrada
- DI 2600362869 parametrizada
- Impostos pagos (II, Taxa, PIS, COFINS)
- AFRMM paga (R$ 785.16)

**Quando é gravado:**
- ✅ Quando detecta mudanças no processo
- ✅ Quando sincroniza processo do Kanban
- ✅ Quando consulta documentos e detecta novos eventos

---

## 🔗 Relacionamentos Entre Tabelas

```
PROCESSO_IMPORTACAO (BGR.0070/25)
    │
    ├── DOCUMENTO_ADUANEIRO (CE 172505417636125)
    │   └── HISTORICO_DOCUMENTO_ADUANEIRO (mudanças do CE)
    │
    ├── DOCUMENTO_ADUANEIRO (DI 2600362869)
    │   ├── HISTORICO_DOCUMENTO_ADUANEIRO (mudanças da DI)
    │   ├── IMPOSTO_IMPORTACAO (II, Taxa, PIS, COFINS)
    │   └── VALOR_MERCADORIA (Descarga BRL/USD, Embarque BRL/USD)
    │
    ├── LANCAMENTO_TIPO_DESPESA (AFRMM R$ 785.16)
    │   └── MOVIMENTACAO_BANCARIA (lançamento bancário)
    │
    └── TIMELINE_PROCESSO (eventos do processo)
```

---

## 📊 Resumo: O Que É Gravado para BGR.0070/25

### ✅ **Já Implementado:**

1. **PROCESSO_IMPORTACAO** (1 registro)
   - Dados principais do processo
   - Status, datas, documentos vinculados
   - Valores resumidos (FOB, frete, CIF)

2. **DOCUMENTO_ADUANEIRO** (2 registros: CE + DI)
   - CE 172505417636125
   - DI 2600362869

3. **HISTORICO_DOCUMENTO_ADUANEIRO** (múltiplos)
   - Mudanças no CE
   - Mudanças na DI
   - ⚠️ **PROBLEMA:** Não é gravado quando usa apenas cache

4. **LANCAMENTO_TIPO_DESPESA** (1 registro)
   - AFRMM R$ 785.16 conciliada

### ⚠️ **Ainda Não Implementado:**

5. **IMPOSTO_IMPORTACAO** (4 registros)
   - II: R$ 52,393.86
   - Taxa: R$ 192.79
   - PIS: R$ 4,231.81
   - COFINS: R$ 20,655.27

6. **VALOR_MERCADORIA** (4 registros)
   - Descarga BRL: R$ 201,514.78
   - Descarga USD: $37,458.37
   - Embarque BRL: R$ 198,825.00
   - Embarque USD: $36,958.38

7. **TIMELINE_PROCESSO** (múltiplos)
   - Eventos do processo ao longo do tempo

---

## 🎯 Próximos Passos

1. ✅ **Criar tabelas** `IMPOSTO_IMPORTACAO` e `VALOR_MERCADORIA`
2. ✅ **Criar serviço** `ImpostoValorService`
3. ✅ **Integrar gravação** no `ProcessoAgent`
4. ✅ **Implementar gravação de histórico do cache**
5. ✅ **Criar script de backfill** para popular banco inicial

---

**Última atualização:** 08/01/2026  
**Status:** 📋 Documentação completa - Aguardando implementação

