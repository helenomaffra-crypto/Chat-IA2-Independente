# 💾 Estratégia de Cache SQLite Após Migração

**Data:** 08/01/2026  
**Status:** 📋 Estratégia Definida

---

## 🎯 Decisão: Manter SQLite como Cache Opcional

**Resposta:** ✅ **SIM, mas de forma opcional e inteligente**

---

## 📊 Situação Atual (Antes da Migração)

### SQLite Hoje Usado Para:

1. **Cache de Processos** (`processos_kanban`)
   - Processos ativos do Kanban
   - Sincronização automática (5 min)

2. **Cache de Documentos**
   - `ces_cache` - CEs consultados
   - `dis_cache` - DIs consultadas
   - `duimps` - DUIMPs criadas/consultadas

3. **Cache de Dados Auxiliares**
   - `classif_cache` - NCMs
   - `conversas_chat` - Histórico de conversas
   - `consultas_bilhetadas` - Consultas pendentes

4. **Performance/Offline**
   - Evita consultas repetidas
   - Funciona offline (se dados já estiverem em cache)

---

## 🚀 Estratégia Futura (Após Migração)

### Arquitetura Híbrida

```
┌─────────────────────────────────────────────────────────┐
│  FONTE PRIMÁRIA: mAIke_assistente (SQL Server)          │
├─────────────────────────────────────────────────────────┤
│  ✅ Sempre consultado primeiro                           │
│  ✅ Dados sempre atualizados                             │
│  ✅ Fonte única da verdade                               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  CACHE OPCIONAL: SQLite (chat_ia.db)                    │
├─────────────────────────────────────────────────────────┤
│  ⚠️ Cache inteligente (opcional)                         │
│  ⚠️ Apenas para performance/offline                      │
│  ⚠️ NÃO é fonte primária                                │
└─────────────────────────────────────────────────────────┘
```

### Regras de Cache

1. **Consulta Primária:**
   - mAIke consulta **sempre** o SQL Server primeiro
   - Se encontrar, retorna imediatamente
   - **Opcionalmente** salva no SQLite para próxima vez

2. **Cache SQLite (Opcional):**
   - Usado apenas se SQL Server estiver offline/lento
   - Usado apenas para performance (evitar latência)
   - **NUNCA** é fonte primária

3. **Sincronização:**
   - SQLite é atualizado quando SQL Server retorna dados
   - Cache expira após X horas (configurável)
   - Cache pode ser invalidado manualmente

---

## 🔄 Fluxo de Consulta Futuro

### Cenário 1: SQL Server Disponível (Normal)

```
Usuário: "situação do ALH.0168/25"
    ↓
1. Consulta mAIke_assistente (SQL Server)
    ↓
2. Se encontrou:
   - Retorna dados imediatamente
   - [Opcional] Salva no SQLite para cache
    ↓
3. Resposta rápida (< 1 segundo)
```

### Cenário 2: SQL Server Offline/Lento

```
Usuário: "situação do ALH.0168/25"
    ↓
1. Tenta consultar mAIke_assistente (SQL Server)
    ↓
2. Se timeout/offline:
   - Tenta SQLite (cache)
   - Se encontrou e não expirou:
     → Retorna cache
     → Avisa que são dados em cache
   - Se não encontrou ou expirou:
     → Erro: "Banco de dados indisponível"
    ↓
3. Resposta com aviso de cache
```

### Cenário 3: Cache Inteligente

```
Usuário: "situação do ALH.0168/25"
    ↓
1. Verifica SQLite primeiro (rápido, < 10ms)
    ↓
2. Se encontrou e não expirou (< 1 hora):
   - Retorna cache imediatamente
   - [Background] Atualiza do SQL Server
   - [Background] Atualiza cache se mudou
    ↓
3. Resposta instantânea (cache) + atualização em background
```

---

## 📋 Tabelas SQLite que Continuam Úteis

### 1. **Dados de Conversa** (Sempre SQLite)

- `conversas_chat` - Histórico de conversas
- `regras_aprendidas` - Regras aprendidas pelo mAIke
- `contexto_sessao` - Contexto de sessão do usuário

**Motivo:** Dados locais, não precisam estar no SQL Server

### 2. **Cache de Performance** (Opcional)

- `processos_kanban` - Cache de processos (opcional)
- `ces_cache` - Cache de CEs (opcional)
- `dis_cache` - Cache de DIs (opcional)
- `duimps` - Cache de DUIMPs (opcional)

**Motivo:** Performance/offline, mas não é fonte primária

### 3. **Dados Auxiliares** (Sempre SQLite)

- `classif_cache` - NCMs (não muda frequentemente)
- `consultas_bilhetadas` - Consultas pendentes (dados locais)

**Motivo:** Dados auxiliares, não precisam estar no SQL Server

---

## ✅ Recomendação Final

### Estratégia: Cache Inteligente Opcional

1. **Fonte Primária:** SQL Server (`mAIke_assistente`)
   - Sempre consultado primeiro
   - Dados sempre atualizados
   - Fonte única da verdade

2. **Cache SQLite:** Opcional para Performance
   - Usado apenas se SQL Server estiver lento/offline
   - Cache expira após X horas
   - Pode ser desabilitado via configuração

3. **Dados Locais:** Sempre SQLite
   - `conversas_chat` - Histórico de conversas
   - `regras_aprendidas` - Regras aprendidas
   - `contexto_sessao` - Contexto de sessão
   - `classif_cache` - NCMs

### Implementação

```python
# services/processo_repository.py (futuro)

def buscar_por_referencia(self, processo_referencia: str):
    # 1. PRIORIDADE: SQL Server (mAIke_assistente)
    processo = self._buscar_maike_assistente(processo_referencia)
    if processo:
        # [Opcional] Salvar no SQLite para cache
        if self._cache_habilitado():
            self._salvar_sqlite_cache(processo)
        return processo
    
    # 2. FALLBACK: SQLite (apenas se SQL Server offline)
    if self._sql_server_offline():
        processo = self._buscar_sqlite_cache(processo_referencia)
        if processo and not self._cache_expirado(processo):
            return processo
    
    return None
```

---

## 🎯 Benefícios da Estratégia

1. ✅ **Performance:** Cache local rápido quando disponível
2. ✅ **Offline:** Funciona mesmo se SQL Server offline (com cache)
3. ✅ **Atualização:** Dados sempre atualizados (SQL Server é fonte primária)
4. ✅ **Flexibilidade:** Cache pode ser desabilitado se não necessário
5. ✅ **Simplicidade:** SQL Server é fonte única da verdade

---

## 📊 Comparação: Com vs Sem Cache

### Com Cache SQLite (Recomendado)

**Vantagens:**
- ✅ Performance melhor (cache local)
- ✅ Funciona offline (se cache disponível)
- ✅ Menos carga no SQL Server

**Desvantagens:**
- ⚠️ Complexidade adicional (manter sincronizado)
- ⚠️ Dados podem ficar desatualizados (se cache expirar)

### Sem Cache SQLite (Mais Simples)

**Vantagens:**
- ✅ Simplicidade (apenas SQL Server)
- ✅ Dados sempre atualizados
- ✅ Sem complexidade de sincronização

**Desvantagens:**
- ⚠️ Dependência total do SQL Server
- ⚠️ Não funciona offline
- ⚠️ Pode ser mais lento (latência de rede)

---

## 🎯 Decisão Final

**Recomendação:** ✅ **Manter SQLite como cache opcional**

**Motivos:**
1. Performance melhor (cache local)
2. Funciona offline (se cache disponível)
3. Flexibilidade (pode ser desabilitado)
4. Dados locais (conversas, regras) sempre SQLite

**Implementação:**
- SQL Server = Fonte primária (sempre consultado primeiro)
- SQLite = Cache opcional (apenas para performance/offline)
- Dados locais = Sempre SQLite (conversas, regras, etc.)

---

**Última atualização:** 08/01/2026

