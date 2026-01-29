# 🏗️ Arquitetura mAIke - Versão Corrigida com Contexto

**Data:** 10/01/2026  
**Status:** ✅ Arquitetura Final Validada

---

## 🎯 Problema que a Arquitetura Resolve

**Separação de Processos Ativos vs Encerrados:**

- **Processos ATIVOS:** Em viagem, aguardando desembaraço, aguardando entrega
  - Aparecem no Kanban (escritório)
  - Devem aparecer em "O QUE TEMOS PRA HOJE" e "FECHAMENTO DO DIA"
  
- **Processos ENCERRADOS:** Já desembarcados e entregues
  - **NÃO** aparecem no Kanban (já saíram)
  - **NÃO** devem aparecer em relatórios do dia (seria informação excessiva)

**Exemplo do problema:**
```
❌ SEM separação:
"O QUE TEMOS PRA HOJE" mostra:
- VDM.003/25 (chegando hoje) ← correto
- ALH.0176/24 (entregue em dezembro/2024) ← excessivo!
- DMD.0089/23 (entregue em 2023) ← excessivo!

✅ COM separação (Kanban filtra):
"O QUE TEMOS PRA HOJE" mostra apenas:
- VDM.003/25 (chegando hoje) ← correto
```

### 🧩 Motivação adicional (simplificar queries e acelerar tools)

Além do recorte “ativos vs encerrados”, a arquitetura (com o banco `mAIke_assistente`) resolve um problema operacional importante:

- **Hoje** muitas tools acabam montando respostas consultando **múltiplas fontes** (Kanban/SQLite, SQL Server antigo, APIs oficiais de documentos, tracking ShipsGo), com regras de merge/fallback.
- Isso aumenta custo de manutenção (mudanças de API impactam várias queries), risco de inconsistência e degrada performance.

**Objetivo do `mAIke_assistente`:**
- Ser a **base interna consolidada** para consultas das tools (um caminho dominante), reduzindo o número de consultas “espalhadas” e acelerando relatórios.
- Manter o acoplamento com fontes externas concentrado na camada **DTO/adapters**, preservando o restante do sistema.

---

## 📊 Arquitetura Final

```
┌─────────────────────────────────────────────────────────────┐
│                    FONTES EXTERNAS                           │
│  - Kanban API (processos ativos)                            │
│  - SQL Server Make (processos históricos)                   │
└─────────────────────────────────────────────────────────────┘
           ↓ Adaptação via DTO (ProcessoRepository)
           ↓
┌─────────────────────────────────────────────────────────────┐
│          SQLite: processos_kanban                            │
│          ← CACHE de PROCESSOS ATIVOS                        │
│          (apenas processos que estão no Kanban)             │
│                                                              │
│          Populado por:                                       │
│          - ProcessoKanbanService (sync a cada 5min)         │
│          - ProcessoRepository (quando busca processo)       │
│                                                              │
│          Propósito:                                          │
│          ✅ Relatórios do dia ("O QUE TEMOS PRA HOJE")      │
│          ✅ Filtro natural de processos ativos               │
└─────────────────────────────────────────────────────────────┘
           ↓ (grava também quando encontra processo ativo)
           ↓
┌─────────────────────────────────────────────────────────────┐
│     BD maike_assistente (SQL Server)                        │
│     ← FONTE DE VERDADE COMPLETA                             │
│                                                              │
│     Contém:                                                  │
│     - TODOS os processos (ativos + históricos)              │
│     - Documentos (CE, DI, DUIMP, CCT)                       │
│     - Impostos e valores                                     │
│     - Despesas conciliadas                                   │
│                                                              │
│     Populado por:                                            │
│     - ProcessoKanbanService (processos ativos)              │
│     - ProcessoRepository (quando busca externamente)        │
│     - Scripts de backfill (históricos)                      │
│                                                              │
│     Propósito:                                               │
│     ✅ Consultas gerais de processo                          │
│     ✅ Busca histórica                                       │
│     ✅ Dados completos e consolidados                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Fluxos de Busca por Contexto

### **Contexto 1: Relatórios do Dia (Ativos apenas)**

**Casos de uso:**
- "O QUE TEMOS PRA HOJE"
- "FECHAMENTO DO DIA"
- "Quais processos chegaram hoje?"

**Fluxo:**
```
1. Buscar em processos_kanban (SQLite)
   ↓ (contém apenas processos ativos, filtrados pelo Kanban)
2. Retornar resultados
```

**✅ Vantagem:** Rápido, não traz processos encerrados

---

### **Contexto 2: Consulta Geral de Processo**

**Casos de uso:**
- "Como está o VDM.003/25?" (processo específico)
- "Buscar processo ALH.0176/24" (pode ser histórico)
- `buscar_processo_por_variacao()` para expandir "vdm.003"

**Fluxo:**
```
1. Buscar em processos_kanban (SQLite) - rápido primeiro
   ↓ (se não encontrar)
2. Buscar no BD maike_assistente (SQL Server) - fonte completa
   ↓ (se não encontrar)
3. Buscar externamente via ProcessoRepository
   - SQL Server maike novo → SQL Server Make antigo → API Kanban
   - Grava automaticamente no BD maike_assistente e processos_kanban
```

**✅ Vantagem:** Encontra processos ativos e históricos

---

### **Contexto 3: Busca Histórica**

**Casos de uso:**
- "Quais processos tivemos em 2024?"
- "Processos entregues em dezembro"
- Relatórios de compliance/auditoria

**Fluxo:**
```
1. Buscar diretamente no BD maike_assistente (SQL Server)
   ↓ (pode filtrar por data, situação, etc.)
2. Retornar resultados
```

**✅ Vantagem:** Não busca no cache (que só tem ativos)

---

## 🔧 Correção no `buscar_processo_por_variacao()`

### **Problema Atual:**
```python
# Busca apenas em processos_kanban (pode não encontrar históricos)
buscar_processo_por_variacao('VDM', '003', buscar_externamente=False)
# → Não encontra se processo estiver apenas no BD maike_assistente
```

### **Solução: Busca em Camadas**

```python
def buscar_processo_por_variacao(prefixo: str, numero: str, apenas_ativos: bool = False) -> Optional[str]:
    """
    Busca processo por variação parcial.
    
    Args:
        apenas_ativos: Se True, busca apenas em processos_kanban (relatórios do dia)
                      Se False, busca completo (processos_kanban → BD maike_assistente → externo)
    """
    numero_formatado = numero.zfill(4)
    padrao_like = f"{prefixo}.{numero_formatado}%"
    
    # 1. Sempre buscar em processos_kanban primeiro (rápido)
    processo = buscar_em_processos_kanban(padrao_like)
    if processo:
        return processo
    
    # 2. Se não encontrou e não é busca apenas ativos, buscar no BD maike_assistente
    if not apenas_ativos:
        processo = buscar_em_maike_assistente(padrao_like)
        if processo:
            return processo
        
        # 3. Se não encontrou, buscar externamente (grava automaticamente)
        processo_dto = ProcessoRepository().buscar_por_referencia(...)
        if processo_dto:
            return processo_dto.processo_referencia
    
    return None
```

---

## ✅ Vantagens desta Arquitetura

1. **Separação clara:**
   - `processos_kanban` = ativos apenas (filtro natural)
   - BD `mAIke_assistente` = base interna consolidada (persistência/relatórios/financeiro)

2. **Fonte da verdade (externa / oficial):**
   - **Serpro / Integra Comex (API oficial)** → CE / DI / CCT
   - **Portal Único (API oficial)** → DUIMP
   - **ShipsGo (API oficial)** → Tracking/ETA/POD e eventos logísticos
   - **Kanban** é um sistema derivado (alimentado por essas 3 APIs + inserções manuais), então pode ter ruído.

3. **Performance:**
   - Relatórios do dia são rápidos (cache SQLite de ativos)
   - Consultas gerais encontram tudo (BD completo)

3. **Sem informação excessiva:**
   - "O QUE TEMOS PRA HOJE" mostra apenas ativos (via processos_kanban)
   - Não traz processos encerrados de meses/anos atrás

5. **Independência (DTO-first):**
   - mAIke continua funcionando mesmo se uma API mudar
   - O acoplamento fica concentrado na **camada de DTO/adapters**, reduzindo impacto no restante do sistema

5. **Graduação de busca:**
   - Busca rápida primeiro (SQLite)
   - Busca completa depois (BD maike_assistente)
   - Busca externa último recurso (grava automaticamente)

---

## 📋 Implementação Recomendada

### **1. Métodos de Busca por Contexto**

```python
# Para relatórios do dia (apenas ativos)
def buscar_processo_por_variacao_ativos(prefixo, numero):
    return buscar_processo_por_variacao(prefixo, numero, apenas_ativos=True)

# Para consulta geral (ativos + históricos)
def buscar_processo_por_variacao_completo(prefixo, numero):
    return buscar_processo_por_variacao(prefixo, numero, apenas_ativos=False)
```

### **2. Chamadas Corretas por Contexto**

```python
# Em extrair_processo_referencia() para relatórios:
if contexto == 'relatorio_dia':
    processo = buscar_processo_por_variacao(prefixo, numero, apenas_ativos=True)
else:
    processo = buscar_processo_por_variacao(prefixo, numero, apenas_ativos=False)
```

### **3. ProcessoRepository mantém lógica atual**

```python
# ProcessoRepository já faz busca em camadas:
# 1. processos_kanban (SQLite) - ativos
# 2. BD maike_assistente (SQL Server) - completo
# 3. SQL Server Make (antigo) - histórico
# 4. API Kanban - último recurso
# E grava automaticamente no BD maike_assistente
```

---

## 🎯 Conclusão

**A arquitetura proposta está CORRETA!** ✅

O Kanban serve como **filtro natural** de processos ativos, e isso é crítico para:
- Relatórios do dia não trazerem processos encerrados
- Performance (cache rápido de ativos)
- Separação clara de responsabilidades

**Ajuste necessário:** O método `buscar_processo_por_variacao()` precisa entender o **contexto de busca**:
- Se for para relatório do dia → `apenas_ativos=True`
- Se for para consulta geral → `apenas_ativos=False` (busca completa)

---

## 💡 Alternativa Considerada (mas descartada)

**Separar por campo `status_ativo` no BD:**
- Adicionar campo `status_ativo BOOLEAN` em `PROCESSO_IMPORTACAO`
- Manter sincronização manual

**Por que descartado:**
- ❌ Requer sincronização manual (mais complexo)
- ❌ Pode ficar desatualizado (processo entregue mas flag não atualizada)
- ❌ Kanban já faz esse filtro naturalmente (fonte confiável)

**Vantagem do Kanban:**
- ✅ Filtro natural (processo sai do Kanban quando entregue)
- ✅ Sem necessidade de flag manual
- ✅ Fonte confiável (escritório usa o Kanban)
