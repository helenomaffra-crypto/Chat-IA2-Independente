# 📋 Resumo: Contexto de Processos Ativos vs Arquivados

**Data:** 08/01/2026  
**Status:** ✅ Documentação Consolidada

---

## 🎯 Conceito Central

**A empresa vive em torno dos processos.** Processos são o centro de tudo.

### ✅ Processos "Ativos"
- **Definição:** Processos que cuidamos desde o embarque no exterior até a entrega no Brasil
- **Fonte:** API Kanban (`http://172.16.10.211:5000/api/kanban/pedidos`)
- **Monitoramento:** Online (mudanças de status, registros, ETA)
- **Armazenamento:** SQLite (`processos_kanban`) + SQL Server (`PROCESSO_IMPORTACAO` com `status_atual = 'ATIVO'`)
- **Sincronização:** Automática a cada 5 minutos

### ✅ Processos "Arquivados"
- **Definição:** Processos finalizados (entregues) que saíram do Kanban
- **Fonte:** SQL Server (banco antigo)
- **Monitoramento:** Não monitorados (já finalizados)
- **Armazenamento:** SQL Server (`PROCESSO_IMPORTACAO` com `status_atual = 'ARQUIVADO'`)
- **Propósito:** Consulta histórica, relatórios, auditoria

---

## 🔄 Fluxo Completo

```
1. EMBARQUE (Exterior)
   ↓
2. MONITORAMENTO ONLINE (Kanban)
   - ETA tracking (atrasos/antecipações)
   - Status tracking (CE, DI, DUIMP)
   - Pendências (ICMS, AFRMM, LPCO)
   ↓
3. CHEGADA E DESEMBARÇO
   ↓
4. ENTREGA FINAL
   ↓
5. ARQUIVAMENTO (SQL Server)
```

---

## 📊 ETA Tracking - Crítico

**Por que é importante:**
- Controlar todas as gravações de ETA
- Saber se navio atrasou ou adiantou
- Detectar mudanças de ETA (primeiro vs último)

**Como funciona:**
1. **Fontes de ETA:**
   - ShipsGo (POD) - mais confiável
   - Kanban (JSON do processo)
   - ICTSI (porto)

2. **Priorização:**
   ```
   1. Evento DISC (Discharge) no porto de destino
   2. Eventos ARRV (Arrival) do porto
   3. shipgov2.destino_data_chegada
   4. eta_iso da tabela (fallback)
   ```

3. **Histórico:**
   - Tabela `TIMELINE_PROCESSO` registra todas as mudanças
   - Compara primeiro ETA vs último ETA
   - Detecta atrasos/antecipações

---

## ✅ Verificação: Planejamento Cobre Tudo?

### ✅ **Coberto:**

1. ✅ **Processos Ativos vs Arquivados**
   - Campo `status_atual` com valores: 'ATIVO', 'ARQUIVADO', 'ENTREGUE', 'CANCELADO'
   - Campo `fonte_dados` com valores: 'KANBAN_API', 'SQL_SERVER', 'SHIPSGO', etc.
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

---

## 📝 Valores Específicos no Banco

### Campo `status_atual`:
- `'ATIVO'` - Processo no Kanban (monitorado)
- `'ARQUIVADO'` - Processo finalizado (só consulta)
- `'ENTREGUE'` - Processo entregue ao cliente
- `'CANCELADO'` - Processo cancelado

### Campo `fonte_dados`:
- `'KANBAN_API'` - Processo ativo (do Kanban)
- `'SQL_SERVER'` - Processo arquivado (do SQL Server antigo)
- `'SHIPSGO'` - Dados de tracking de navios
- `'PORTAL_UNICO'` - Dados do Portal Único
- `'INTEGRACOMEX'` - Dados do Integra Comex

---

## 🎯 Próximos Passos

1. ✅ **Script SQL atualizado** com valores específicos
2. ⏳ **Criar serviço de sincronização** (Kanban → SQL Server)
3. ⏳ **Criar serviço de arquivamento** (marcar como ARQUIVADO)
4. ⏳ **Atualizar queries** para distinguir ativos vs arquivados
5. ⏳ **Implementar ETA tracking** completo

---

**Documentação completa:** `docs/CONTEXTO_PROCESSOS_ATIVOS_ARQUIVADOS.md`

