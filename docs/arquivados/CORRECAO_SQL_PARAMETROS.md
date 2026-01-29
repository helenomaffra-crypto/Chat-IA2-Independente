# 🔧 Correção: Parâmetros SQL no Node.js Adapter

## ✅ Status: PARCIALMENTE CORRIGIDO

**Data**: 17/12/2025  
**Problema**: Node.js adapter não suporta parâmetros preparados `?` em funções SQL

---

## 🐛 Problema Identificado

**Erro**:
```
ERROR: "Incorrect syntax near '?'."
```

**Causa**: 
- O Node.js adapter usa `.query(sqlQuery)` diretamente
- Não prepara parâmetros com `?` quando usado dentro de funções SQL
- Exemplo problemático: `WHERE UPPER(LTRIM(RTRIM(numero_processo))) = UPPER(LTRIM(RTRIM(?)))`

---

## ✅ Correção Aplicada

### 1. ✅ `_buscar_processo_principal` (Linha ~159)

**Antes**:
```sql
WHERE UPPER(LTRIM(RTRIM(numero_processo))) = UPPER(LTRIM(RTRIM(?)))
```

**Depois**:
```python
processo_ref_upper = processo_referencia.upper().strip()
processo_ref_escaped = processo_ref_upper.replace("'", "''")
query = f"WHERE UPPER(LTRIM(RTRIM(numero_processo))) = UPPER(LTRIM(RTRIM('{processo_ref_escaped}')))"
```

**Resultado**: ✅ Processo VDM.0004/25 agora é encontrado no SQL Server!

---

## ⚠️ Queries Ainda com Problema

As seguintes queries ainda usam `?` e precisam ser corrigidas:

1. **`_buscar_ce_completo`** (Linha ~233):
   ```sql
   WHERE ceRoot.numero = ?
   ```

2. **`_buscar_di_completo`** (Linha ~393):
   ```sql
   WHERE ddg.numeroDi = ? OR ddg.numeroDi = ?
   ```

3. **`_buscar_duimp_completo`** (Linha ~962):
   ```sql
   WHERE numero = ? OR numero_processo = ?
   ```

4. **Outras queries com `?`** em:
   - `_buscar_di_por_id_processo`
   - `_buscar_di_por_ce`
   - `_buscar_cct_completo`

---

## 🔧 Solução Recomendada

**Opção 1: Formatação Direta (Atual)**
- ✅ Funciona imediatamente
- ⚠️ Requer escape manual para prevenir SQL injection
- ✅ Já implementado para `_buscar_processo_principal`

**Opção 2: Modificar Node.js Adapter**
- Adicionar suporte a parâmetros preparados
- Usar `pool.request().input('param', value).query(sql)`
- Mais seguro, mas requer mudanças no adapter

---

## 📊 Status Atual

| Query | Status | Notas |
|-------|--------|-------|
| `_buscar_processo_principal` | ✅ Corrigido | Processo encontrado |
| `_buscar_ce_completo` | ❌ Precisa correção | Erro ao buscar CE |
| `_buscar_di_completo` | ❌ Precisa correção | Erro ao buscar DI |
| `_buscar_duimp_completo` | ❌ Precisa correção | Erro ao buscar DUIMP |

---

## 🎯 Próximos Passos

1. ✅ Corrigir `_buscar_ce_completo` para usar formatação direta
2. ✅ Corrigir `_buscar_di_completo` para usar formatação direta
3. ✅ Corrigir `_buscar_duimp_completo` para usar formatação direta
4. ✅ Corrigir todas as outras queries com `?`

---

**Última atualização**: 17/12/2025  
**Status**: ✅ Processo encontrado, mas queries de CE/DI/DUIMP ainda precisam correção
