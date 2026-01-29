# 📋 Contexto: Processos Ativos vs Arquivados

**Data:** 08/01/2026  
**Status:** 📋 Documentação de Contexto  
**Prioridade:** ⭐ **CRÍTICA** - Base para toda a arquitetura

---

## 🎯 Conceito Central

**A empresa vive em torno dos processos.** Processos são o centro de tudo.

### Processos "Ativos"

**Definição:** Processos que a empresa **cuida desde o embarque no exterior até a entrega no Brasil**.

**Características:**
- ✅ **Monitorados online** - mudanças de status, registros, etc.
- ✅ **Fonte primária:** API Kanban (`http://172.16.10.211:5000/api/kanban/pedidos`)
- ✅ **Armazenamento:** Tabela `processos_kanban` no SQLite (cache local)
- ✅ **Sincronização:** Automática a cada 5 minutos
- ✅ **Ciclo de vida:** Desde embarque → chegada → desembaraço → entrega

**Exemplo de uso:**
- Quando pergunta "o que temos pra hoje", o mAIke só mostra corretamente os **ativos**
- Processos ativos aparecem no dashboard "O QUE TEMOS PRA HOJE"
- Processos ativos são monitorados para mudanças de status, ETA, etc.

### Processos "Arquivados"

**Definição:** Processos que **já foram finalizados** (entregues) e saíram do Kanban.

**Características:**
- ✅ **Fonte primária:** SQL Server (banco antigo)
- ✅ **Armazenamento:** Tabela `PROCESSO_IMPORTACAO` no SQL Server
- ✅ **Propósito:** Consulta histórica, relatórios, auditoria
- ✅ **Não são mais monitorados** online (já finalizados)

**Exemplo de uso:**
- Consultas históricas: "quais processos tivemos em 2024?"
- Relatórios de compliance
- Auditoria de processos antigos

---

## 🔄 Fluxo Completo de um Processo

### 1. **Criação (Embarque no Exterior)**
- Processo aparece no Kanban
- Sincronizado automaticamente para SQLite (`processos_kanban`)
- Status: **ATIVO**

### 2. **Monitoramento Online**
- **ETA tracking:** Todas as mudanças de ETA são registradas
- **Status tracking:** Mudanças de status são monitoradas
- **Documentos:** CE, CCT, DI, DUIMP são rastreados
- **Pendências:** ICMS, AFRMM, LPCO são monitoradas
- Fonte: API Kanban (atualizada a cada 5 minutos)

### 3. **Chegada e Desembaraço**
- Processo chega ao porto/aeroporto
- DI/DUIMP é registrada
- Desembaraço acontece
- Status: Ainda **ATIVO** (no Kanban)

### 4. **Entrega Final**
- Carga é entregue ao cliente
- Processo sai do Kanban
- Status: **ARQUIVADO**

### 5. **Arquivamento**
- Processo migrado para SQL Server (banco antigo)
- Mantido para consulta histórica
- Status: **ARQUIVADO**

---

## 📊 Estrutura de Dados Atual

### SQLite (Cache Local - Processos Ativos)

**Tabela:** `processos_kanban`

**Campos principais:**
- `processo_referencia` (PK) - Ex: "ALH.0168/25"
- `etapa_kanban` - Etapa atual no Kanban
- `modal` - Marítimo, Aéreo, etc.
- `numero_ce`, `numero_di`, `numero_duimp`
- `situacao_ce`, `situacao_di`, `situacao_entrega`
- `data_embarque`, `data_desembaraco`, `data_entrega`
- `data_destino_final` - Chegada confirmada
- `eta_iso` - ETA previsto
- `dados_completos_json` - JSON completo do Kanban
- `atualizado_em` - Última sincronização

**Tabela:** `processos_kanban_historico`

**Campos principais:**
- `processo_referencia`
- `campo_mudado` - Ex: 'eta_iso', 'situacao_ce'
- `valor_anterior`
- `valor_novo`
- `criado_em` - Data/hora da mudança

**Uso:**
- Rastrear mudanças de ETA (primeiro ETA vs último ETA)
- Rastrear mudanças de status
- Detectar atrasos/antecipações

### SQL Server (Banco Antigo - Processos Arquivados)

**Tabela:** `PROCESSO_IMPORTACAO` (já existe, versão simplificada)

**Campos principais:**
- `id_processo_importacao`
- `numero_processo`
- `numero_ce`, `numero_di`, `numero_duimp`
- `data_embarque`, `data_desembaraco`
- `status_processo`

**Uso:**
- Consulta histórica
- Relatórios
- Auditoria

---

## 🎯 ETA Tracking - Crítico para o Negócio

### Por que é Importante?

**O controle de todas as gravações de ETA é crítico** para saber se o navio:
- ✅ **Atrasou** - ETA foi adiado
- ✅ **Adiantou** - ETA foi antecipado

### Como Funciona Hoje

1. **Fonte de ETA:**
   - **ShipsGo (POD):** Tracking de navios via API ShipsGo
   - **Kanban:** ETA do JSON do processo
   - **ICTSI:** ETA do porto

2. **Priorização de Fontes:**
   ```
   1. PRIORIDADE MÁXIMA: Evento DISC (Discharge) no porto de destino
   2. Eventos ARRV (Arrival) do porto de destino
   3. shipgov2.destino_data_chegada
   4. eta_iso da tabela (fallback)
   ```

3. **Histórico de Mudanças:**
   - Tabela `processos_kanban_historico` registra todas as mudanças
   - Compara primeiro ETA vs último ETA
   - Detecta atrasos/antecipações

4. **Relatório "ETA ALTERADO":**
   - Mostra processos com ETA que mudou
   - Compara primeiro vs último ETA
   - Indica se atrasou ou adiantou

---

## ⚠️ Particularidades Importantes

### 1. **Distinção Ativo vs Arquivado**

**Regra crítica:**
- Processos **ativos** = estão no Kanban (API retorna)
- Processos **arquivados** = não estão mais no Kanban (só no SQL Server)

**Como o sistema sabe:**
- Se processo está no Kanban → **ATIVO**
- Se processo não está no Kanban mas existe no SQL Server → **ARQUIVADO**

### 2. **Sincronização Automática**

**ProcessoKanbanService:**
- Sincroniza a cada 5 minutos
- Remove processos que não estão mais no Kanban
- Atualiza processos existentes
- Registra mudanças no histórico

### 3. **"O Que Temos Pra Hoje"**

**Critérios:**
- Mostra apenas processos **ativos** (do Kanban)
- Filtra por:
  - ETA = hoje
  - Data de chegada = hoje
  - Processos prontos para registro
  - Pendências que precisam de ação

**Não mostra:**
- Processos arquivados (já finalizados)
- Processos entregues (`situacao_ce = 'ENTREGUE'`)

### 4. **Monitoramento Online**

**O que é monitorado:**
- ✅ Mudanças de status (CE, DI, DUIMP)
- ✅ Mudanças de ETA (atrasos/antecipações)
- ✅ Registro de documentos (DI, DUIMP)
- ✅ Pendências (ICMS, AFRMM, LPCO)
- ✅ Chegadas confirmadas (`dataDestinoFinal`)

**Como é monitorado:**
- Sincronização automática a cada 5 minutos
- Comparação de versões (anterior vs nova)
- Registro de mudanças no histórico
- Notificações quando há mudanças importantes

---

## 🔄 Migração para SQL Server (Novo Banco)

### Estratégia de Migração

**Fase 1: Processos Ativos**
1. Migrar processos do Kanban para `PROCESSO_IMPORTACAO` (SQL Server)
2. Manter sincronização automática
3. Marcar como `status_atual = 'ATIVO'`

**Fase 2: Processos Arquivados**
1. Migrar processos do SQL Server antigo
2. Marcar como `status_atual = 'ARQUIVADO'`
3. Manter histórico completo

**Fase 3: Consolidação**
1. Unificar processos ativos e arquivados
2. Usar `status_atual` para distinguir
3. Manter sincronização apenas para ativos

### Campos Necessários no Novo Banco

**Tabela `PROCESSO_IMPORTACAO` (SQL Server):**

```sql
-- Status do Processo
status_atual VARCHAR(100),              -- 'ATIVO', 'ARQUIVADO', 'ENTREGUE', etc.
status_anterior VARCHAR(100),            -- Status anterior
situacao_processo VARCHAR(100),          -- Situação técnica

-- Origem dos Dados (CRÍTICO)
fonte_dados VARCHAR(50),                  -- 'KANBAN_API', 'SQL_SERVER', 'SHIPSGO'
ultima_sincronizacao DATETIME,           -- Última vez que foi sincronizado
versao_dados INT DEFAULT 1,              -- Controle de versões
hash_dados VARCHAR(64),                  -- Hash para detectar mudanças
json_dados_originais NVARCHAR(MAX),     -- Backup dos dados brutos

-- ETA Tracking (CRÍTICO)
eta_iso DATETIME,                        -- ETA atual
eta_shipsgo DATETIME,                   -- ETA do ShipsGo
porto_shipsgo_codigo VARCHAR(10),
porto_shipsgo_nome VARCHAR(255),
status_shipsgo VARCHAR(100),
shipsgo_ultima_atualizacao DATETIME,

-- Datas Importantes
data_criacao_processo DATETIME,
data_ultima_atualizacao DATETIME,
data_chegada DATETIME,                   -- Chegada confirmada
data_eta DATETIME,                       -- ETA previsto
data_desembaraco DATETIME,
data_destino_final DATETIME,             -- Entrega final
```

**Tabela `TIMELINE_PROCESSO` (SQL Server):**

```sql
-- Histórico completo de mudanças
processo_referencia VARCHAR(50) NOT NULL,
data_evento DATETIME NOT NULL,
tipo_evento VARCHAR(50) NOT NULL,         -- 'MUDANCA_ETA', 'MUDANCA_STATUS', etc.
tipo_evento_descricao VARCHAR(255),
valor_anterior VARCHAR(255),
valor_novo VARCHAR(255),
campo_alterado VARCHAR(100),
usuario_ou_sistema VARCHAR(100),
fonte_dados VARCHAR(50),
json_dados_originais NVARCHAR(MAX),
```

---

## ✅ Verificação: O Planejamento Cobre Tudo?

### ✅ **Coberto no Planejamento:**

1. ✅ **Processos Ativos vs Arquivados**
   - Campo `status_atual` na tabela `PROCESSO_IMPORTACAO`
   - Campo `fonte_dados` para distinguir origem
   - Campo `ultima_sincronizacao` para processos ativos

2. ✅ **ETA Tracking**
   - Campos `eta_iso`, `eta_shipsgo` na tabela `PROCESSO_IMPORTACAO`
   - Tabela `SHIPSGO_TRACKING` para tracking de navios
   - Tabela `TIMELINE_PROCESSO` para histórico de mudanças

3. ✅ **Monitoramento Online**
   - Tabela `TIMELINE_PROCESSO` para todas as mudanças
   - Campo `json_dados_originais` para backup dos dados brutos
   - Campo `hash_dados` para detectar mudanças

4. ✅ **Histórico Completo**
   - Tabela `TIMELINE_PROCESSO` para histórico de mudanças
   - Campos `valor_anterior` e `valor_novo` para rastreamento

### ⚠️ **Ajustes Necessários:**

1. **Campo `status_atual` precisa ter valores específicos:**
   - `'ATIVO'` - Processo no Kanban (monitorado)
   - `'ARQUIVADO'` - Processo finalizado (só consulta)
   - `'ENTREGUE'` - Processo entregue ao cliente
   - `'CANCELADO'` - Processo cancelado

2. **Campo `fonte_dados` precisa ter valores específicos:**
   - `'KANBAN_API'` - Processo ativo (do Kanban)
   - `'SQL_SERVER'` - Processo arquivado (do SQL Server antigo)
   - `'SHIPSGO'` - Dados de tracking de navios
   - `'PORTAL_UNICO'` - Dados do Portal Único
   - `'INTEGRACOMEX'` - Dados do Integra Comex

3. **Sincronização Automática:**
   - Processos com `fonte_dados = 'KANBAN_API'` devem ser sincronizados automaticamente
   - Processos com `fonte_dados = 'SQL_SERVER'` não são sincronizados (só consulta)

---

## 🎯 Próximos Passos

1. ✅ **Atualizar script SQL** com valores específicos de `status_atual` e `fonte_dados`
2. ✅ **Criar serviço de sincronização** que:
   - Sincroniza processos do Kanban para SQL Server
   - Marca como `status_atual = 'ATIVO'` e `fonte_dados = 'KANBAN_API'`
   - Registra mudanças na `TIMELINE_PROCESSO`
3. ✅ **Criar serviço de arquivamento** que:
   - Marca processos finalizados como `status_atual = 'ARQUIVADO'`
   - Remove do Kanban (ou mantém apenas para consulta)
4. ✅ **Atualizar queries** para distinguir ativos vs arquivados
5. ✅ **Implementar ETA tracking** completo na `TIMELINE_PROCESSO`

---

**Última atualização:** 08/01/2026

