# 📋 EntityExtractors - Arquitetura e Uso

**Data:** 10/01/2026  
**Status:** ✅ Implementado com contexto de busca

---

## 🎯 Arquitetura de Busca

O `EntityExtractors.buscar_processo_por_variacao()` implementa busca em **camadas**, respeitando a separação entre processos ativos e históricos:

### **Fluxo de Busca**

```
┌─────────────────────────────────────────────────────────────┐
│  buscar_processo_por_variacao(prefixo, numero,              │
│                                apenas_ativos,                │
│                                buscar_externamente)          │
└─────────────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────┴───────────────┐
        │                               │
apenas_ativos=True            apenas_ativos=False
(Relatórios do dia)          (Consulta geral)
        │                               │
        ↓                               ↓
┌───────────────────┐     ┌────────────────────────────────────┐
│ 1. processos_kanban│     │ 1. processos_kanban (cache)       │
│    (ativos apenas) │     │    ↓ (se não encontrar)           │
│    ↓               │     │ 2. BD maike_assistente            │
│ Retorna ou None    │     │    (fonte completa)               │
└───────────────────┘     │    ↓ (se não encontrar)           │
                          │ 3. Fontes externas                 │
                          │    (se buscar_externamente=True)   │
                          │    - ProcessoRepository            │
                          │    - Grava automaticamente no mAIke│
                          └────────────────────────────────────┘
```

---

## 📝 Parâmetros

### `apenas_ativos: bool = False`

**Quando usar `apenas_ativos=True`:**
- ✅ Relatórios do dia: "O QUE TEMOS PRA HOJE", "FECHAMENTO DO DIA"
- ✅ Quando precisa filtrar apenas processos ativos (filtro natural do Kanban)
- ✅ Quando não quer trazer processos encerrados/históricos

**Quando usar `apenas_ativos=False` (padrão):**
- ✅ Consulta geral de processo: "Como está o VDM.003?"
- ✅ Extração de processo de mensagem genérica
- ✅ Quando pode ser processo histórico ou ativo

### `buscar_externamente: bool = False`

**Quando usar `buscar_externamente=True`:**
- ✅ Quando quer que o sistema busque em fontes externas se não encontrar no mAIke
- ✅ Fontes externas: SQL Server Make antigo, API Kanban
- ✅ ProcessoRepository grava automaticamente no mAIke após encontrar

**Quando usar `buscar_externamente=False` (padrão):**
- ✅ Busca apenas no mAIke (processos_kanban + BD maike_assistente)
- ✅ Não consulta fontes externas (mais rápido, sem custo de API)

---

## 🔄 Exemplos de Uso

### **Exemplo 1: Relatório do Dia (apenas ativos)**

```python
# Em serviços de relatório ("O QUE TEMOS PRA HOJE")
processo = EntityExtractors.buscar_processo_por_variacao(
    'VDM', '003',
    apenas_ativos=True,  # ← Busca apenas processos ativos
    buscar_externamente=False
)
# Retorna: 'VDM.0003/25' se estiver no Kanban, None se não estiver
```

### **Exemplo 2: Consulta Geral (ativos + históricos)**

```python
# Em extração de processo de mensagem genérica
processo = EntityExtractors.buscar_processo_por_variacao(
    'ALH', '0176',
    apenas_ativos=False,  # ← Busca completo (ativos + históricos)
    buscar_externamente=False  # ← Não busca externamente por padrão
)
# Retorna: processo se estiver em processos_kanban OU BD maike_assistente
```

### **Exemplo 3: Busca Completa com Fallback Externo**

```python
# Quando quer garantir que encontra o processo mesmo se não estiver no mAIke
processo = EntityExtractors.buscar_processo_por_variacao(
    'BND', '0093',
    apenas_ativos=False,  # ← Busca completo
    buscar_externamente=True  # ← Busca externamente se não encontrar
)
# Fluxo: processos_kanban → BD maike_assistente → SQL Server Make → API Kanban
# Se encontrar externamente, grava automaticamente no mAIke
```

---

## 📊 Fluxo Detalhado

### **Cenário 1: Busca Apenas Ativos (`apenas_ativos=True`)**

```
1. Busca em processos_kanban (SQLite)
   ↓
   ✅ Encontrou → Retorna processo
   ❌ Não encontrou → Retorna None (processo não está mais ativo)
```

**Uso:** Relatórios do dia, "O QUE TEMOS PRA HOJE"

---

### **Cenário 2: Busca Completa (`apenas_ativos=False`)**

```
1. Busca em processos_kanban (SQLite) - cache rápido
   ↓
   ✅ Encontrou → Retorna processo
   ❌ Não encontrou
   ↓
2. Busca no BD maike_assistente (SQL Server) - fonte completa
   ↓
   ✅ Encontrou → Retorna processo
   ❌ Não encontrou
   ↓
3. Se buscar_externamente=True:
   Busca via ProcessoRepository (fontes externas)
   - SQL Server maike novo
   - SQL Server Make antigo
   - API Kanban
   ↓
   ✅ Encontrou → Grava no mAIke + Retorna processo
   ❌ Não encontrou → Retorna None
```

**Uso:** Consulta geral de processo, extração de mensagens

---

## ⚙️ Implementação Técnica

### **Busca em processos_kanban (SQLite)**

```sql
SELECT processo_referencia 
FROM processos_kanban
WHERE processo_referencia LIKE 'VDM.0003%'
ORDER BY processo_referencia DESC
LIMIT 1
```

- ✅ Rápido (cache local)
- ✅ Contém apenas processos ativos (filtro natural do Kanban)
- ⚠️ Pode não ter processos históricos

---

### **Busca em BD maike_assistente (SQL Server)**

```sql
SELECT TOP 1 numero_processo
FROM mAIke_assistente.dbo.PROCESSO_IMPORTACAO
WHERE numero_processo LIKE 'VDM.0003%'
ORDER BY numero_processo DESC
```

- ✅ Fonte completa (ativos + históricos)
- ✅ Dados sempre atualizados
- ⚠️ Requer conexão SQL Server (mas já é necessária)

---

### **Busca Externa (ProcessoRepository)**

```python
repositorio = ProcessoRepository()
processo_dto = repositorio.buscar_por_referencia(processo_completo)
# Busca em: processos_kanban → BD maike_assistente → SQL Server Make → API Kanban
# Grava automaticamente no mAIke após encontrar
```

- ✅ Encontra processos históricos do banco antigo
- ✅ Encontra processos ativos da API Kanban
- ✅ Grava automaticamente no mAIke (evita busca futura)
- ⚠️ Mais lento (múltiplas consultas)
- ⚠️ Pode consultar APIs externas (custo)

---

## 🎯 Recomendações de Uso

### **Para Relatórios do Dia:**
```python
# ✅ CORRETO: apenas_ativos=True
processo = EntityExtractors.buscar_processo_por_variacao(
    prefixo, numero, apenas_ativos=True
)
```

### **Para Extração de Mensagem:**
```python
# ✅ CORRETO: apenas_ativos=False (padrão)
# Deixa busca completa, filtro de ativos deve ser feito na query final
processo = EntityExtractors.buscar_processo_por_variacao(
    prefixo, numero  # apenas_ativos=False por padrão
)
```

### **Para Garantir Encontrar:**
```python
# ✅ CORRETO: buscar_externamente=True (se realmente necessário)
processo = EntityExtractors.buscar_processo_por_variacao(
    prefixo, numero,
    apenas_ativos=False,
    buscar_externamente=True  # Busca externamente se não encontrar
)
```

---

## 📋 Checklist de Uso

- [ ] **Relatório do dia?** → `apenas_ativos=True`
- [ ] **Consulta geral?** → `apenas_ativos=False` (padrão)
- [ ] **Precisa garantir encontrar?** → `buscar_externamente=True`
- [ ] **Busca rápida suficiente?** → `buscar_externamente=False` (padrão)

---

**Última atualização:** 10/01/2026
