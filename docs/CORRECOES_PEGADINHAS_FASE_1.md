# ✅ Correções de "Pegadinhas" - Fase 1

**Data:** 14/01/2026  
**Status:** ✅ **CORRIGIDO** - 3 problemas críticos identificados e resolvidos

---

## 🐛 Problemas Identificados

### 1. ✅ **created_at vs "quando virou executing"**

**Problema:**
```python
# ❌ ERRADO: Usava created_at
WHERE status = 'executing'
AND created_at < ?
```

**Cenário problemático:**
- Intent criado há 1 hora (`created_at` = 1h atrás)
- Usuário confirma agora → vira `executing` (agora)
- Recovery roda → expira intent porque `created_at` é antigo
- **Resultado:** Intent recém-confirmado é expirado incorretamente

**Solução:**
- ✅ Adicionar coluna `executing_at TIMESTAMP` ao schema
- ✅ Setar `executing_at = CURRENT_TIMESTAMP` em `marcar_como_executando()`
- ✅ Usar `executing_at` (não `created_at`) no recovery

**Código corrigido:**
```python
# ✅ CORRETO: Usa executing_at
UPDATE pending_intents
SET status = 'executing', executing_at = CURRENT_TIMESTAMP
WHERE intent_id = ? AND status = 'pending'

# Recovery:
WHERE status = 'executing'
AND executing_at IS NOT NULL
AND executing_at < datetime('now', '-10 minutes')
```

---

### 2. ✅ **Formato do Timestamp: isoformat() vs CURRENT_TIMESTAMP**

**Problema:**
```python
# ❌ ERRADO: Python gera ISO format
limite_timestamp = (datetime.now() - timedelta(minutes=10)).isoformat()
# Resultado: "2026-01-14T15:10:00"

# SQLite CURRENT_TIMESTAMP gera:
# Resultado: "2026-01-14 15:10:00" (com espaço, sem T)

# Comparação pode falhar:
WHERE executing_at < '2026-01-14T15:10:00'  # ❌ Formato diferente
```

**Solução:**
- ✅ Usar SQLite `datetime('now', '-X minutes')` para comparação
- ✅ Evita problema de formato (SQLite compara internamente)
- ✅ Mais eficiente (não precisa calcular em Python)

**Código corrigido:**
```python
# ✅ CORRETO: Usa SQLite datetime functions
WHERE executing_at < datetime('now', '-10 minutes')
```

---

### 3. ✅ **Interpolação de String no SQL**

**Problema:**
```python
# ❌ ERRADO: ? dentro de string literal não funciona
observacoes = 'Executando travado (timeout de ? minutos)'
# Resultado: "Executando travado (timeout de ? minutos)" (literal ?)
```

**Solução:**
- ✅ Construir string em Python antes de passar para SQL
- ✅ OU usar concatenação SQL (`||`) se necessário
- ✅ Usar parâmetros apenas para valores, não para strings literais

**Código corrigido:**
```python
# ✅ CORRETO: Construir string em Python
observacao_texto = f'Executando travado (timeout de {timeout_minutos} minutos)'
cursor.execute('''
    UPDATE pending_intents
    SET status = 'expired', 
        observacoes = ?
    WHERE ...
''', (observacao_texto, ...))
```

---

## 📊 Resumo das Correções

| # | Problema | Solução | Status |
|---|----------|---------|--------|
| 1 | `created_at` vs `executing_at` | Adicionar coluna `executing_at`, usar no recovery | ✅ Corrigido |
| 2 | Formato timestamp | Usar SQLite `datetime('now', '-X minutes')` | ✅ Corrigido |
| 3 | Interpolação de string | Construir string em Python antes de SQL | ✅ Corrigido |

---

## 🔧 Mudanças no Schema

**Nova coluna adicionada:**
```sql
executing_at TIMESTAMP  -- Timestamp de quando virou 'executing'
```

**Migration automática:**
```python
# db_manager.py
try:
    cursor.execute('ALTER TABLE pending_intents ADD COLUMN executing_at TIMESTAMP')
    logger.info('✅ Coluna executing_at adicionada à tabela pending_intents')
except sqlite3.OperationalError:
    # Coluna já existe, ignorar
    pass
```

---

## 🧪 Testes Recomendados

### Teste 1: Recovery com executing_at
```
1. Criar intent (created_at = agora - 1h)
2. Confirmar agora (executing_at = agora)
3. Aguardar 10 minutos
4. Chamar recuperar_intents_travados()
5. Verificar: Intent NÃO é expirado (executing_at é recente)
```

### Teste 2: Recovery com intent travado
```
1. Marcar intent como executing (executing_at = agora - 15 min)
2. Chamar recuperar_intents_travados(timeout_minutos=10)
3. Verificar: Intent É expirado (executing_at é antigo)
```

### Teste 3: Formato de timestamp
```
1. Verificar que SQLite datetime('now', '-10 minutes') funciona
2. Comparar com executing_at (ambos em formato SQLite)
3. Verificar que comparação funciona corretamente
```

---

## 📝 Notas Finais

- ✅ **executing_at adicionado:** Coluna nova no schema com migration automática
- ✅ **Formato timestamp:** Usa SQLite datetime functions (evita problema de formato)
- ✅ **Interpolação corrigida:** String construída em Python antes de SQL
- ✅ **Backward compatible:** Migration não quebra intents existentes (executing_at pode ser NULL)

**Status:** ✅ **TODAS AS PEGADINHAS CORRIGIDAS**

---

**Última atualização:** 14/01/2026
