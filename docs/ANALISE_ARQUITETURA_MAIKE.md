# Análise da Arquitetura mAIke - Separação de Fontes

**Data:** 10/01/2026  
**Análise:** Arquitetura proposta vs. Implementação atual

---

## 🎯 Objetivo da Separação

**Objetivo:** mAIke ficar independente, e quando mudar algo externo, só trocar a camada de adaptação (DTO).

**Separação proposta:**
- **mAIke (próprio):** SQLite `processos_kanban` + BD `maike_assistente` novo
- **Fontes externas:** Kanban API, SQL Server antigo (Make) → Adaptadas via `ProcessoRepository` e DTOs

---

## ✅ Pontos Positivos

1. **Separação conceitual clara** - Facilita entender o que é interno vs externo
2. **Camada de abstração (DTO)** - Protege contra mudanças em fontes externas
3. **Independência** - mAIke pode evoluir sem depender de fontes externas

---

## ⚠️ Problemas Identificados

### 1. **`processos_kanban` é CACHE, não fonte de verdade**

**Problema:**
- `processos_kanban` (SQLite) é um **cache local** populado pela API Kanban a cada 5 minutos
- A **fonte de verdade** deveria ser o BD `maike_assistente` (SQL Server)
- Buscar apenas no SQLite pode retornar dados desatualizados

**Evidência:**
```python
# services/processo_kanban_service.py
# Sincroniza da API Kanban para SQLite a cada 5 minutos
def sincronizar(self) -> bool:
    processos_json = self._buscar_api()  # ← API externa
    # ... salva em processos_kanban (SQLite)
```

**Impacto:**
- Se sincronização atrasar, dados podem estar desatualizados
- Processos novos podem não aparecer imediatamente
- Processos arquivados podem continuar no cache

---

### 2. **Duplicação de Dados e Inconsistências**

**Problema:**
- Dados estão em **dois lugares**: SQLite (`processos_kanban`) e SQL Server (`maike_assistente`)
- Se sincronização falhar, dados ficam inconsistentes

**Evidência:**
```
processos_kanban (SQLite) ← Cache local (sincronizado a cada 5 min)
     ↓ (deveria sincronizar)
maike_assistente (SQL Server) ← Fonte de verdade?
```

**Pergunta crítica:** Qual é a fonte de verdade real?
- Se for `maike_assistente`, então `processos_kanban` é apenas cache
- Se for `processos_kanban`, então não há necessidade do `maike_assistente`

---

### 3. **Busca Incompleta no `buscar_processo_por_variacao`**

**Problema:**
- Com `buscar_externamente=False` (padrão), método não encontra processos que:
  - Estão apenas no BD `maike_assistente` (não sincronizados para SQLite ainda)
  - São históricos (arquivados, não estão no Kanban)
  - Foram buscados recentemente via `ProcessoRepository` mas cache ainda não atualizou

**Cenário de falha:**
```python
# Usuário digita: "vdm.003"
EntityExtractors.buscar_processo_por_variacao('VDM', '003', buscar_externamente=False)
# → Busca apenas em processos_kanban (SQLite)
# → Não encontra (processo não está no cache ainda)
# → Retorna None
# → Usuário não consegue encontrar processo que existe no sistema
```

---

## 🔧 Proposta de Arquitetura Corrigida

### **Opção 1: BD maike_assistente como Fonte de Verdade** (RECOMENDADO)

```
┌─────────────────────────────────────────────────────────────┐
│                     FONTES EXTERNAS                          │
│  (Kanban API, SQL Server Make)                              │
│           ↓ Adaptação via DTO                                │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              BD maike_assistente (SQL Server)                │
│              ← FONTE DE VERDADE                              │
│  - PROCESSO_IMPORTACAO                                       │
│  - DOCUMENTO_ADUANEIRO                                       │
│  - IMPOSTO_IMPORTACAO                                        │
│  - VALOR_MERCADORIA                                          │
└─────────────────────────────────────────────────────────────┘
                       ↓ (cache opcional)
┌─────────────────────────────────────────────────────────────┐
│              processos_kanban (SQLite)                       │
│              ← CACHE LOCAL (opcional, para performance)      │
└─────────────────────────────────────────────────────────────┘
```

**Fluxo correto:**
1. **`buscar_processo_por_variacao`** sempre busca no BD `maike_assistente` primeiro
2. SQLite (`processos_kanban`) é apenas **cache de leitura** para performance
3. Se não encontrar no cache, busca no BD `maike_assistente`
4. Se não encontrar no BD `maike_assistente`, aí sim usa `ProcessoRepository` para buscar externamente

**Vantagens:**
- ✅ Dados sempre atualizados (BD é fonte de verdade)
- ✅ Cache melhora performance sem comprometer consistência
- ✅ Busca completa (encontra processos históricos também)

**Desvantagens:**
- ⚠️ Requer conexão SQL Server (mas já é necessária para outras funcionalidades)

---

### **Opção 2: SQLite como Fonte de Verdade (Atual, com correções)**

**Se `processos_kanban` for a fonte de verdade**, então:

```
┌─────────────────────────────────────────────────────────────┐
│                     FONTES EXTERNAS                          │
│  (Kanban API, SQL Server Make)                              │
│           ↓ Adaptação via DTO                                │
└─────────────────────────────────────────────────────────────┘
                       ↓ (grava sempre)
┌─────────────────────────────────────────────────────────────┐
│              processos_kanban (SQLite)                       │
│              ← FONTE DE VERDADE                              │
└─────────────────────────────────────────────────────────────┘
                       ↓ (backup/sincronização)
┌─────────────────────────────────────────────────────────────┐
│              BD maike_assistente (SQL Server)                │
│              ← BACKUP/SINCRONIZAÇÃO                          │
└─────────────────────────────────────────────────────────────┘
```

**Correções necessárias:**
1. **`buscar_processo_por_variacao`** deve sempre permitir busca externa quando necessário
2. Garantir que `ProcessoRepository` **sempre** grava no SQLite quando busca externamente
3. BD `maike_assistente` vira apenas backup/sincronização (não fonte primária)

**Problema:** Se SQLite for fonte de verdade, qual o propósito do BD `maike_assistente`?

---

## 💡 Recomendação Final

**RECOMENDO Opção 1: BD maike_assistente como Fonte de Verdade**

**Justificativa:**
1. **Escalabilidade:** BD SQL Server suporta mais dados e usuários simultâneos
2. **Consistência:** Uma única fonte de verdade evita inconsistências
3. **Histórico:** Processos históricos/arquivados ficam no BD, não no cache
4. **Sincronização:** Não precisa sincronizar bidirecionalmente (apenas gravar no BD)

**Implementação:**
```python
def buscar_processo_por_variacao(prefixo: str, numero: str) -> Optional[str]:
    """
    Busca processo no mAIke (BD maike_assistente) primeiro,
    depois em fontes externas se necessário.
    """
    # 1. Buscar no BD maike_assistente (fonte de verdade)
    processo = buscar_em_maike_assistente(prefixo, numero)
    if processo:
        return processo
    
    # 2. Se não encontrou, buscar em fontes externas via ProcessoRepository
    # (que vai gravar no BD maike_assistente automaticamente)
    processo_dto = ProcessoRepository().buscar_por_referencia(...)
    if processo_dto:
        # ProcessoRepository já gravou no BD maike_assistente
        return processo_dto.processo_referencia
    
    return None
```

**SQLite (`processos_kanban`):**
- Usar apenas como **cache de leitura** para processos mais consultados
- Atualizar cache de forma assíncrona (não bloqueia busca)
- Cache pode expirar/estar desatualizado (não é crítico)

---

## 📋 Perguntas para Decisão

1. **Qual é a fonte de verdade atual?**
   - SQLite `processos_kanban`?
   - BD `maike_assistente`?
   - Ambos (perigoso)?

2. **Qual é o propósito do BD `maike_assistente`?**
   - Backup?
   - Fonte de verdade?
   - Integração com outros sistemas?

3. **O que acontece quando processo é arquivado?**
   - Sai do SQLite?
   - Fica apenas no BD?
   - Como é buscado depois?

4. **Qual a prioridade: Performance ou Consistência?**
   - Se performance: usar SQLite como cache
   - Se consistência: usar BD como fonte de verdade

---

## ✅ Conclusão

A **separação conceitual** está correta e bem pensada. O problema está na **implementação prática**:

1. **Não está claro qual é a fonte de verdade** (SQLite vs BD)
2. **Busca pode ser incompleta** (não encontra processos que deveria)
3. **Risco de inconsistências** (dados em dois lugares)

**Recomendação:** Definir claramente que o **BD `maike_assistente` é a fonte de verdade**, e o SQLite é apenas cache opcional para performance.
