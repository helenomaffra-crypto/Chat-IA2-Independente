# 🏗️ Arquitetura Futura do mAIke Assistente

**Data:** 08/01/2026  
**Status:** 📋 Arquitetura Futura  
**Objetivo:** Explicar como o mAIke funcionará após migração para banco único

---

## 🎯 Visão Geral

**Hoje:** mAIke consulta múltiplas fontes (SQLite, SQL Server antigo, Kanban API, etc.)  
**Depois:** mAIke consulta apenas **um banco único** (`mAIke_assistente`) que consolida tudo

---

## 📊 Como Funciona HOJE

### Estratégia de Busca Atual (Múltiplas Fontes)

```
Usuário pergunta: "situação do ALH.0168/25"
    ↓
mAIke busca em ORDEM:
    1. SQL Server antigo (se disponível)
    2. SQLite (cache do Kanban)
    3. API Kanban (processos ativos)
    4. APIs externas (Integra Comex, Portal Único)
```

**Problemas:**
- ⚠️ Consultas lentas (múltiplas fontes)
- ⚠️ Dados fragmentados (cada fonte tem parte dos dados)
- ⚠️ Dependência de rede (SQL Server, APIs)
- ⚠️ Cache inconsistente (SQLite pode estar desatualizado)
- ⚠️ Difícil fazer pesquisas complexas (dados em lugares diferentes)

---

## 🚀 Como Funcionará DEPOIS

### Estratégia de Busca Futura (Banco Único)

```
Usuário pergunta: "situação do ALH.0168/25"
    ↓
mAIke busca APENAS em:
    → Banco mAIke_assistente (SQL Server)
        ├── PROCESSO_IMPORTACAO (dados consolidados)
        ├── DOCUMENTO_ADUANEIRO (CE, DI, DUIMP, CCT)
        ├── TIMELINE_PROCESSO (histórico completo)
        ├── HISTORICO_DOCUMENTO_ADUANEIRO (mudanças de documentos)
        └── ... (todas as tabelas consolidadas)
```

**Vantagens:**
- ✅ **Consultas rápidas** (um único banco)
- ✅ **Dados consolidados** (tudo em um lugar)
- ✅ **Pesquisas complexas** (SQL direto)
- ✅ **Histórico completo** (todas as mudanças)
- ✅ **Offline possível** (se banco estiver local)

---

## 🔄 Fluxo de Dados Futuro

### 1. **Alimentação do Banco Novo**

**Fontes antigas alimentam o banco novo:**

```
┌─────────────────────────────────────────────────────────┐
│  FONTES ANTIGAS (Alimentam o banco novo)                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  SQL Server Antigo (Make)                               │
│    └─→ Migração inicial                                 │
│    └─→ Processos arquivados                             │
│                                                          │
│  API Kanban                                             │
│    └─→ Sincronização automática (5 min)                 │
│    └─→ Processos ativos                                 │
│                                                          │
│  Integra Comex                                          │
│    └─→ Consultas diretas → Grava histórico             │
│    └─→ CE, DI, CCT                                      │
│                                                          │
│  Portal Único                                           │
│    └─→ Consultas diretas → Grava histórico             │
│    └─→ DUIMP, CCT                                       │
│                                                          │
│  Banco do Brasil / Santander                            │
│    └─→ Extratos → MOVIMENTACAO_BANCARIA                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  BANCO NOVO: mAIke_assistente (SQL Server)              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ✅ PROCESSO_IMPORTACAO (consolidado)                   │
│  ✅ DOCUMENTO_ADUANEIRO (CE, DI, DUIMP, CCT)            │
│  ✅ TIMELINE_PROCESSO (histórico)                       │
│  ✅ HISTORICO_DOCUMENTO_ADUANEIRO (mudanças)            │
│  ✅ MOVIMENTACAO_BANCARIA (extratos)                    │
│  ✅ RASTREAMENTO_RECURSO (origem dos recursos)          │
│  ✅ ... (todas as 30 tabelas)                           │
│                                                          │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  mAIke Assistente (Consulta apenas o banco novo)        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ✅ Consultas rápidas e diretas                          │
│  ✅ Dados sempre atualizados                             │
│  ✅ Pesquisas complexas (SQL)                           │
│  ✅ Histórico completo disponível                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Benefícios para o mAIke

### 1. **Consultas Mais Rápidas**

**Antes:**
```
Buscar processo:
  1. Tentar SQL Server antigo (pode demorar 15s se offline)
  2. Tentar SQLite (cache pode estar desatualizado)
  3. Tentar API Kanban (requer rede)
  → Total: 5-20 segundos
```

**Depois:**
```
Buscar processo:
  1. Consultar mAIke_assistente (banco único)
  → Total: < 1 segundo
```

### 2. **Dados Sempre Consolidados**

**Antes:**
- Dados fragmentados em múltiplas fontes
- Precisa "juntar" dados de diferentes lugares
- Pode faltar informações

**Depois:**
- Tudo em um lugar só
- Dados sempre completos
- Histórico completo disponível

### 3. **Pesquisas Mais Poderosas**

**Antes:**
- Pesquisas limitadas (cada fonte tem limitações)
- Difícil fazer queries complexas
- Precisa consultar múltiplas fontes

**Depois:**
- SQL direto no banco consolidado
- Queries complexas possíveis
- Joins entre tabelas relacionadas
- Agregações e análises

**Exemplos de pesquisas que ficarão mais fáceis:**

```sql
-- Processos com DI desembaraçada nos últimos 30 dias
SELECT p.*, d.*
FROM PROCESSO_IMPORTACAO p
INNER JOIN DOCUMENTO_ADUANEIRO d ON p.processo_referencia = d.processo_referencia
WHERE d.tipo_documento = 'DI'
  AND d.status_documento = 'DESEMBARACADA'
  AND d.data_desembaraco >= DATEADD(day, -30, GETDATE())
ORDER BY d.data_desembaraco DESC

-- Processos com mudanças de status hoje
SELECT p.processo_referencia, t.*
FROM PROCESSO_IMPORTACAO p
INNER JOIN TIMELINE_PROCESSO t ON p.processo_referencia = t.processo_referencia
WHERE t.tipo_evento = 'MUDANCA_STATUS'
  AND CAST(t.data_evento AS DATE) = CAST(GETDATE() AS DATE)

-- Rastreamento completo de recursos
SELECT p.processo_referencia, r.*, m.*
FROM PROCESSO_IMPORTACAO p
INNER JOIN RASTREAMENTO_RECURSO r ON p.processo_referencia = r.processo_referencia
LEFT JOIN MOVIMENTACAO_BANCARIA m ON r.id_movimentacao_bancaria = m.id_movimentacao
WHERE p.categoria_processo = 'DMD'
ORDER BY r.data_aplicacao DESC
```

### 4. **Histórico Completo Disponível**

**Antes:**
- Histórico fragmentado
- Difícil rastrear mudanças
- Precisa consultar múltiplas fontes

**Depois:**
- Histórico completo em `TIMELINE_PROCESSO`
- Histórico de documentos em `HISTORICO_DOCUMENTO_ADUANEIRO`
- Todas as mudanças rastreadas

**Exemplos de perguntas que ficarão mais fáceis:**

- "Quando o status da DI mudou para DESEMBARACADA?"
- "Quais processos tiveram ETA alterado esta semana?"
- "Mostre histórico completo do processo ALH.0168/25"
- "Quais documentos mudaram de canal (VERDE → AMARELO) hoje?"

### 5. **Rastreamento de Origem dos Recursos**

**Antes:**
- Dados financeiros fragmentados
- Difícil rastrear origem dos recursos
- Precisa consultar múltiplas fontes

**Depois:**
- Tudo em `RASTREAMENTO_RECURSO`
- `MOVIMENTACAO_BANCARIA` vinculada
- Rastreamento completo disponível

**Exemplos de perguntas que ficarão possíveis:**

- "De onde veio o dinheiro do processo DMD.0090/25?"
- "Mostre todos os recursos aplicados em processos ALH este mês"
- "Quais processos receberam recursos do cliente XYZ?"

---

## 🔄 Migração Gradual

### Fase 1: Banco Novo Criado ✅

**Status:** Banco `mAIke_assistente` criado (estrutura básica)

**O que tem:**
- 2 tabelas básicas (PROCESSO_IMPORTACAO, TRANSPORTE)

**O que falta:**
- 28 tabelas adicionais
- Dados migrados
- Sincronização automática

---

### Fase 2: Estrutura Completa ⏳

**Objetivo:** Criar todas as 30 tabelas

**Ação:**
- Executar script SQL completo (`scripts/criar_banco_maike_completo.sql`)

**Resultado:**
- Todas as tabelas criadas
- Estrutura pronta para receber dados

---

### Fase 3: Migração de Dados ⏳

**Objetivo:** Migrar dados das fontes antigas

**Estratégia:**
1. **Processos Arquivados:**
   - Migrar do SQL Server antigo
   - Marcar como `status_atual = 'ARQUIVADO'`
   - `fonte_dados = 'SQL_SERVER'`

2. **Processos Ativos:**
   - Sincronizar do Kanban
   - Marcar como `status_atual = 'ATIVO'`
   - `fonte_dados = 'KANBAN_API'`
   - Sincronização automática a cada 5 minutos

3. **Documentos:**
   - Migrar do SQLite (ces_cache, dis_cache, etc.)
   - Sincronizar de APIs (Integra Comex, Portal Único)
   - Gravar histórico de mudanças

4. **Extratos Bancários:**
   - Migrar extratos existentes
   - Sincronizar novos extratos automaticamente

---

### Fase 4: mAIke Usa Banco Novo ⏳

**Objetivo:** mAIke consulta apenas o banco novo

**Mudanças necessárias:**

#### 4.1. Atualizar ProcessoRepository

**Arquivo:** `services/processo_repository.py`

**Antes:**
```python
def buscar_por_referencia(self, processo_referencia: str):
    # Busca em: SQL Server antigo → SQLite → API Kanban
    if sql_server_disponivel:
        processo = self._buscar_sql_server(processo_ref_upper)  # SQL Server antigo
    processo = self._buscar_sqlite(processo_ref_upper)  # SQLite
    processo = self._buscar_api_kanban(processo_ref_upper)  # API Kanban
```

**Depois:**
```python
def buscar_por_referencia(self, processo_referencia: str):
    # Busca APENAS em: mAIke_assistente (banco novo)
    processo = self._buscar_maike_assistente(processo_ref_upper)
    return processo
```

#### 4.2. Atualizar db_manager.py

**Arquivo:** `db_manager.py`

**Mudanças:**
- Funções que consultam SQLite → Consultam `mAIke_assistente`
- Funções que consultam SQL Server antigo → Consultam `mAIke_assistente`
- Funções que consultam API Kanban → Consultam `mAIke_assistente` (já sincronizado)

**Exemplo:**

**Antes:**
```python
def obter_dados_documentos_processo(processo_referencia: str):
    # Busca em múltiplas fontes
    ce = buscar_ce_cache(numero_ce)  # SQLite
    di = buscar_di_sql_server(numero_di)  # SQL Server antigo
    duimp = buscar_duimp_cache(numero_duimp)  # SQLite
```

**Depois:**
```python
def obter_dados_documentos_processo(processo_referencia: str):
    # Busca APENAS no banco novo
    query = """
        SELECT d.*
        FROM DOCUMENTO_ADUANEIRO d
        WHERE d.processo_referencia = ?
        ORDER BY d.tipo_documento
    """
    documentos = adapter.execute_query(query, (processo_referencia,))
    return documentos
```

#### 4.3. Atualizar Agents

**Arquivos:** `services/agents/*.py`

**Mudanças:**
- Agents consultam `mAIke_assistente` diretamente
- Não precisam mais fazer fallback para múltiplas fontes
- Consultas mais simples e rápidas

---

## 📊 Comparação: Antes vs Depois

### Consulta de Processo

**ANTES:**
```
Usuário: "situação do ALH.0168/25"
    ↓
mAIke:
  1. Verifica SQL Server antigo (15s timeout se offline)
  2. Busca SQLite (cache pode estar desatualizado)
  3. Busca API Kanban (requer rede)
  4. Junta dados de múltiplas fontes
  5. Retorna resposta
  → Tempo: 5-20 segundos
```

**DEPOIS:**
```
Usuário: "situação do ALH.0168/25"
    ↓
mAIke:
  1. Consulta mAIke_assistente (banco único)
  2. Retorna dados consolidados
  → Tempo: < 1 segundo
```

### Pesquisa Complexa

**ANTES:**
```
Usuário: "processos ALH com DI desembaraçada este mês"
    ↓
mAIke:
  1. Busca processos ALH no SQLite
  2. Busca DIs no SQL Server antigo
  3. Junta dados manualmente
  4. Filtra por data
  → Complexo, lento, pode faltar dados
```

**DEPOIS:**
```
Usuário: "processos ALH com DI desembaraçada este mês"
    ↓
mAIke:
  1. Executa SQL direto no banco:
     SELECT p.*, d.*
     FROM PROCESSO_IMPORTACAO p
     INNER JOIN DOCUMENTO_ADUANEIRO d ON ...
     WHERE p.categoria_processo = 'ALH'
       AND d.tipo_documento = 'DI'
       AND d.status_documento = 'DESEMBARACADA'
       AND d.data_desembaraco >= ...
  → Simples, rápido, dados completos
```

### Histórico de Mudanças

**ANTES:**
```
Usuário: "quando o status da DI mudou para DESEMBARACADA?"
    ↓
mAIke:
  1. Busca DI no SQL Server antigo
  2. Busca histórico no SQLite (pode não ter)
  3. Tenta API (pode não ter histórico)
  → Histórico incompleto ou ausente
```

**DEPOIS:**
```
Usuário: "quando o status da DI mudou para DESEMBARACADA?"
    ↓
mAIke:
  1. Consulta HISTORICO_DOCUMENTO_ADUANEIRO:
     SELECT *
     FROM HISTORICO_DOCUMENTO_ADUANEIRO
     WHERE numero_documento = '2521440840'
       AND tipo_documento = 'DI'
       AND campo_alterado = 'status_documento'
       AND valor_novo = 'DESEMBARACADA'
  → Histórico completo e preciso
```

---

## 🎯 Benefícios Específicos para o mAIke

### 1. **Mais Liberdade de Pesquisa**

**Antes:**
- Limitado pelas APIs disponíveis
- Queries complexas difíceis
- Dados fragmentados

**Depois:**
- SQL direto no banco consolidado
- Queries complexas possíveis
- Dados sempre completos

**Exemplos de pesquisas que ficarão possíveis:**

- "Processos que tiveram ETA alterado mais de 3 vezes"
- "Processos com mudança de canal (VERDE → AMARELO) esta semana"
- "Processos que receberam recursos do cliente XYZ"
- "Processos com DI desembaraçada mas sem pagamento de impostos"
- "Ranking de processos por valor FOB"
- "Processos com pendências não resolvidas há mais de 30 dias"

### 2. **Respostas Mais Completas**

**Antes:**
- Dados podem estar incompletos
- Precisa consultar múltiplas fontes
- Pode faltar informações

**Depois:**
- Dados sempre completos
- Histórico disponível
- Informações consolidadas

**Exemplo:**

**Antes:**
```
Usuário: "situação do ALH.0168/25"
Resposta: "Processo ALH.0168/25
- Status: Aguardando Documentos
- CE: 132505371482300
- DI: Não encontrada (pode estar no SQL Server antigo)"
```

**Depois:**
```
Usuário: "situação do ALH.0168/25"
Resposta: "Processo ALH.0168/25
- Status: Aguardando Documentos
- CE: 132505371482300 (Status: DESCARREGADA, Data: 15/01/2026)
- DI: 2521440840 (Status: DESEMBARACADA, Canal: VERDE, Data: 10/01/2026)
- Histórico: 
  * 10/01/2026: DI registrada
  * 12/01/2026: DI mudou de canal (VERDE → AMARELO)
  * 15/01/2026: DI desembaraçada
- Valores: FOB USD 100.000, Frete USD 5.000, Impostos R$ 50.000"
```

### 3. **Performance Melhorada**

**Antes:**
- Múltiplas consultas
- Timeouts possíveis
- Cache inconsistente

**Depois:**
- Consulta única
- Sem timeouts
- Dados sempre atualizados

### 4. **Rastreamento Completo**

**Antes:**
- Histórico fragmentado
- Difícil rastrear mudanças
- Dados financeiros separados

**Depois:**
- Histórico completo
- Todas as mudanças rastreadas
- Rastreamento de recursos completo

---

## 🔄 Sincronização Automática

### Como Funciona

**Fontes antigas continuam alimentando o banco novo:**

1. **API Kanban:**
   - Sincronização automática a cada 5 minutos
   - Processos ativos → `PROCESSO_IMPORTACAO` (status_atual = 'ATIVO')
   - Detecta mudanças → Grava em `TIMELINE_PROCESSO`

2. **Integra Comex / Portal Único:**
   - Quando mAIke consulta → Grava histórico automaticamente
   - Documentos → `DOCUMENTO_ADUANEIRO`
   - Mudanças → `HISTORICO_DOCUMENTO_ADUANEIRO`

3. **Extratos Bancários:**
   - Sincronização automática
   - Movimentações → `MOVIMENTACAO_BANCARIA`
   - Rastreamento → `RASTREAMENTO_RECURSO`

**Resultado:**
- Banco novo sempre atualizado
- mAIke sempre tem dados frescos
- Histórico completo disponível

---

## 📋 Resumo: Arquitetura Futura

### Fluxo de Dados

```
FONTES ANTIGAS (Alimentam)
    ↓
BANCO NOVO (mAIke_assistente)
    ↓
mAIke (Consulta apenas o banco novo)
```

### Benefícios

1. ✅ **Consultas mais rápidas** (< 1 segundo vs 5-20 segundos)
2. ✅ **Dados sempre consolidados** (tudo em um lugar)
3. ✅ **Pesquisas mais poderosas** (SQL direto)
4. ✅ **Histórico completo** (todas as mudanças rastreadas)
5. ✅ **Rastreamento de recursos** (origem completa)
6. ✅ **Mais liberdade** (queries complexas possíveis)
7. ✅ **Performance melhorada** (sem timeouts, sem cache inconsistente)

---

## 🎯 Próximos Passos

1. ✅ **Estrutura criada** (script SQL completo)
2. ⏳ **Executar script SQL** (criar todas as tabelas)
3. ⏳ **Migrar dados** (processos arquivados, documentos)
4. ⏳ **Configurar sincronização** (Kanban, APIs)
5. ⏳ **Atualizar mAIke** (consultar apenas banco novo)
6. ⏳ **Testar e validar** (garantir que tudo funciona)

---

**Última atualização:** 08/01/2026

