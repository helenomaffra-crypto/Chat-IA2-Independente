# ✅ Validação de Fontes de Dados

**Data:** 22/01/2026  
**Status:** 📋 Plano de Validação

---

## 🎯 Objetivo

Validar que o sistema funciona corretamente com os 3 cenários principais de fontes de dados:

1. **Dado só no snapshot** (SQLite/Kanban)
2. **Dado só no mAIke_assistente** (SQL Server primário)
3. **Dado só no Make** (migração/fallback controlado)

---

## 📋 Cenários de Teste

### Cenário 1: Dado só no Snapshot (SQLite)

**Objetivo**: Validar que processos ativos do Kanban são encontrados mesmo sem estar no SQL Server.

**Teste**:
1. Processo ativo no Kanban (ex: `VDM.0006/25`)
2. Processo **não existe** no `mAIke_assistente` nem no `Make`
3. Consultar: `situacao vdm.0006/25`

**Resultado esperado**:
- ✅ Processo encontrado no SQLite
- ✅ Resposta mostra dados do snapshot
- ✅ Log indica fonte: SQLite

**Arquivos relacionados**:
- `services/processo_repository.py` → `_buscar_sqlite`
- `services/processos_kanban_repository.py`

---

### Cenário 2: Dado só no mAIke_assistente

**Objetivo**: Validar que processos migrados/arquivados são encontrados no banco primário.

**Teste**:
1. Processo **não existe** no SQLite (não está mais no Kanban)
2. Processo **existe** no `mAIke_assistente`
3. Consultar: `situacao ALH.0168/25` (processo arquivado)

**Resultado esperado**:
- ✅ Processo encontrado no `mAIke_assistente`
- ✅ Resposta mostra dados completos (com histórico/impostos)
- ✅ Log indica fonte: `mAIke_assistente`
- ✅ **NÃO** tenta fallback para `Make` (se processo existe no primário)

**Arquivos relacionados**:
- `services/processo_repository.py` → `_buscar_sql_server`
- `services/sql_server_processo_schema.py`

---

### Cenário 3: Dado só no Make (Fallback Controlado)

**Objetivo**: Validar que processos antigos fazem fallback para `Make` apenas quando necessário e com log explícito.

**Teste**:
1. Processo **não existe** no SQLite
2. Processo **não existe** no `mAIke_assistente`
3. Processo **existe** no `Make` (banco legado)
4. Consultar: `situacao PROCESSO_ANTIGO/20` (processo de 2020)

**Resultado esperado**:
- ✅ Processo encontrado no `Make` (fallback)
- ✅ **Log explícito** de fallback:
  ```
  ⚠️ [FALLBACK_MAKE] Processo PROCESSO_ANTIGO/20 não encontrado no mAIke_assistente
     → Consultando banco legado (Make) para migração/auto-heal
     → Tool/Serviço: consultar_status_processo
     → Chamador: ProcessoRepository._buscar_sql_server
     → Motivo: Processo não encontrado no banco primário, tentando migração
     → Timestamp: 2026-01-22T...
  ```
- ✅ Processo migrado para `mAIke_assistente` (auto-heal)
- ✅ Próxima consulta usa `mAIke_assistente` (sem fallback)

**Arquivos relacionados**:
- `services/processo_repository.py` → `_buscar_sql_server` (fallback)
- `services/db_policy_service.py` → `log_legacy_fallback`

---

## 🔍 Testes de Relatórios

### Relatório FOB

**Teste**: `gerar_relatorio_fob` para mês/ano específico

**Resultado esperado**:
- ✅ Query usa `mAIke_assistente` como primário
- ✅ Se processo não existe no primário, **não** tenta fallback (relatórios devem usar dados consolidados)
- ✅ Log indica banco usado: `mAIke_assistente`

**Arquivos relacionados**:
- `services/relatorio_fob_service.py` → `buscar_processos_di_por_mes`
- `services/relatorio_fob_service.py` → `buscar_processos_duimp_por_mes`

---

### Relatório de Averbações

**Teste**: `gerar_relatorio_averbacoes` para mês/ano específico

**Resultado esperado**:
- ✅ Query usa `mAIke_assistente` como primário
- ✅ Log indica banco usado: `mAIke_assistente`

**Arquivos relacionados**:
- `services/relatorio_averbacoes_service.py` → `_buscar_processos_com_di_no_mes`

---

## ✅ Checklist de Validação

### Fase 0: Inventário ✅
- [x] Documentação de fontes criada (`docs/FONTES_E_FLUXO_DADOS.md`)
- [x] Mapeamento de fontes por tool/serviço completo
- [x] Pontos de uso do banco legado identificados

### Fase 1: Política Central ✅
- [x] `services/db_policy_service.py` criado
- [x] Funções de política implementadas
- [x] Feature flag `ALLOW_LEGACY_FALLBACK` configurável

### Fase 2: Remoção de Hardcodes ✅
- [x] `services/sql_server_processo_schema.py` atualizado
- [x] `services/relatorio_fob_service.py` atualizado (4 queries)
- [x] `services/relatorio_averbacoes_service.py` atualizado
- [x] `services/di_documento_handler.py` atualizado
- [x] `services/processo_repository.py` atualizado (já tinha log, agora usa política)
- [x] `services/processo_snapshot_service.py` atualizado
- [x] `services/agents/processo_agent.py` atualizado

### Fase 3: Logs de Fallback ✅
- [x] Função `log_legacy_fallback()` implementada
- [x] Logs adicionados em todos os pontos de fallback
- [x] Logs incluem: processo, tool, chamador, motivo, query, timestamp

### Fase 4: Validação (Testes Manuais Necessários)
- [ ] **Cenário 1**: Testar processo só no snapshot
- [ ] **Cenário 2**: Testar processo só no mAIke_assistente
- [ ] **Cenário 3**: Testar processo só no Make (fallback)
- [ ] **Relatório FOB**: Validar que usa mAIke_assistente
- [ ] **Relatório Averbações**: Validar que usa mAIke_assistente
- [ ] **Logs de Fallback**: Verificar que aparecem corretamente

---

## 🧪 Como Executar Testes

### Teste Manual 1: Processo só no Snapshot

```bash
# No chat:
"situacao vdm.0006/25"

# Verificar logs:
docker compose logs web | grep -i "vdm.0006"
# Deve mostrar: "Processo encontrado no SQLite" ou similar
```

### Teste Manual 2: Processo só no mAIke_assistente

```bash
# No chat:
"situacao ALH.0168/25"

# Verificar logs:
docker compose logs web | grep -i "ALH.0168"
# Deve mostrar: "Processo encontrado no mAIke_assistente"
# NÃO deve mostrar: "[FALLBACK_MAKE]"
```

### Teste Manual 3: Processo só no Make (Fallback)

```bash
# No chat:
"situacao PROCESSO_ANTIGO/20"  # Substituir por processo real antigo

# Verificar logs:
docker compose logs web | grep -i "FALLBACK_MAKE"
# Deve mostrar log completo de fallback com todos os campos
```

### Teste Manual 4: Relatório FOB

```bash
# No chat:
"relatorio fob janeiro 2025"

# Verificar logs:
docker compose logs web | grep -i "relatorio.*fob"
# Deve mostrar: "banco: mAIke_assistente"
```

---

## 📊 Métricas de Sucesso

- ✅ **0 hardcodes de `Make`** sem política central
- ✅ **100% dos fallbacks** têm log explícito
- ✅ **Relatórios críticos** usam `mAIke_assistente` como primário
- ✅ **Feature flag** funciona (pode desabilitar fallback)

---

**Última atualização**: 22/01/2026
