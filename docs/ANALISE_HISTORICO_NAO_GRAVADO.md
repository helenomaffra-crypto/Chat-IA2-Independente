# 🔍 Análise: Por Que o Histórico Não Foi Gravado?

**Data:** 08/01/2026  
**Processo:** BGR.0070/25  
**Problema:** Histórico não foi gravado quando consultou "situacao do bgr.0070/25"

---

## 🎯 Situação Atual

### ✅ O Que Funciona

1. **Tool `consultar_despesas_processo` está funcionando!**
   - ✅ IA agora usa a tool correta
   - ✅ Mostra despesas conciliadas (AFRMM R$ 785.16)

2. **Histórico é gravado quando:**
   - ✅ API Integra Comex é consultada diretamente (`call_integracomex`)
   - ✅ API Portal Único é consultada diretamente (`call_portal`)
   - ✅ Processo é sincronizado do Kanban (`ProcessoKanbanService._salvar_processo`)

### ⚠️ O Problema

**Histórico NÃO é gravado quando:**
- ⚠️ Sistema usa apenas cache (SQLite) sem consultar API
- ⚠️ Processo é consultado via `ProcessoRepository` que busca do cache
- ⚠️ `obter_dados_documentos_processo` retorna dados do cache sem consultar API

---

## 🔄 Fluxo Atual de Consulta

### **Cenário: "situacao do bgr.0070/25"**

```
1. Usuário: "situacao do bgr.0070/25"
   ↓
2. ProcessoAgent._consultar_status_processo()
   ↓
3. ProcessoRepository.buscar_por_referencia()
   - Busca do Kanban (cache SQLite) ✅
   - Busca do SQL Server Make (cache) ✅
   - ⚠️ NÃO consulta API se dados estão no cache
   ↓
4. Retorna dados do cache
   - ⚠️ Histórico NÃO é gravado (API não foi consultada)
```

### **Cenário: Consulta Direta de Documento**

```
1. Usuário: "consulte o CE 172505417636125"
   ↓
2. CeAgent._consultar_ce_maritimo()
   ↓
3. Verifica cache primeiro
   - Se tem no cache → retorna cache ⚠️ (histórico NÃO gravado)
   - Se NÃO tem no cache → consulta API ✅ (histórico gravado)
   ↓
4. call_integracomex() → _gravar_historico_se_documento()
   - ✅ Histórico gravado apenas se API foi consultada
```

---

## 📊 Onde o Histórico É Gravado

### **1. `utils/integracomex_proxy.py` (linha 294)**

```python
# ✅ Grava histórico após consulta bem-sucedida
if status_code == 200 and body_data and isinstance(body_data, dict):
    _gravar_historico_se_documento(
        path=path,
        response_body=body_data,
        processo_referencia=processo_referencia,
        fonte_dados='INTEGRACOMEX',
        api_endpoint=path
    )
```

**Quando é chamado:**
- ✅ Quando `call_integracomex()` é chamado diretamente
- ✅ Quando API retorna status 200
- ⚠️ NÃO é chamado se sistema usa cache

### **2. `utils/portal_proxy.py`**

**Similar ao integracomex_proxy.py**

### **3. `services/processo_kanban_service.py`**

```python
# ✅ Grava histórico ao sincronizar processo do Kanban
_gravar_historico_documentos(processo_json)
```

**Quando é chamado:**
- ✅ Quando processo é sincronizado do Kanban (a cada 5 min)
- ✅ Extrai documentos do JSON e grava histórico

---

## 💡 Soluções Propostas

### **Solução 1: Forçar Consulta de API (Não Recomendado)**

**Problema:** Aumenta custo (API bilhetada)

**Implementação:**
- Adicionar flag `forcar_consulta_api: true` em `_consultar_status_processo`
- Sempre consultar API mesmo se tem cache

**Desvantagens:**
- ❌ Aumenta custo (cada consulta é paga)
- ❌ Piora performance (consulta API é mais lenta)

---

### **Solução 2: Gravar Histórico ao Usar Cache (Recomendado)** ⭐

**Implementação:**
- Ao retornar dados do cache, verificar se documento existe no banco
- Se não existe, gravar histórico usando dados do cache
- Se existe, comparar e gravar mudanças

**Vantagens:**
- ✅ Não aumenta custo (usa dados já consultados)
- ✅ Mantém histórico completo
- ✅ Funciona mesmo quando usa cache

**Arquivo:** `services/documento_historico_service.py`

**Modificar:**
```python
def gravar_historico_do_cache(
    self,
    numero_documento: str,
    tipo_documento: str,
    dados_cache: Dict[str, Any],
    processo_referencia: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Grava histórico usando dados do cache (sem consultar API).
    
    Útil quando sistema retorna dados do cache mas histórico não foi gravado.
    """
    return self.detectar_e_gravar_mudancas(
        numero_documento=numero_documento,
        tipo_documento=tipo_documento,
        dados_novos=dados_cache,
        fonte_dados='CACHE',
        api_endpoint='cache',
        processo_referencia=processo_referencia
    )
```

**Integrar em:**
- `ProcessoAgent._consultar_status_processo` (após buscar do cache)
- `CeAgent._consultar_ce_maritimo` (quando retorna cache)
- `DiAgent._obter_dados_di` (quando retorna cache)

---

### **Solução 3: Gravar Histórico na Sincronização Kanban (Já Implementado Parcialmente)** ✅

**Status:** ✅ Já implementado em `ProcessoKanbanService._salvar_processo`

**O que falta:**
- ⚠️ Verificar se está funcionando corretamente
- ⚠️ Validar se histórico está sendo gravado

**Teste:**
```python
# Verificar se histórico foi gravado na última sincronização
python3 testes/verificar_historico_bgr_0070.py
```

---

## 🧪 Testes Necessários

### **Teste 1: Verificar Se Histórico É Gravado na Sincronização**

```bash
# 1. Aguardar próxima sincronização do Kanban (5 min)
# 2. Executar:
python3 testes/verificar_historico_bgr_0070.py
```

**Esperado:**
- ✅ Histórico gravado após sincronização
- ✅ Documentos gravados em `DOCUMENTO_ADUANEIRO`

### **Teste 2: Forçar Consulta de API**

```python
# Consultar processo forçando API
# (modificar código temporariamente para forçar consulta)
```

**Esperado:**
- ✅ Histórico gravado após consulta API

### **Teste 3: Gravar Histórico do Cache**

```python
# Implementar Solução 2
# Consultar processo (usando cache)
# Verificar se histórico foi gravado
```

**Esperado:**
- ✅ Histórico gravado mesmo usando cache

---

## 📋 Checklist de Implementação

### **Fase 1: Diagnóstico** ✅
- [x] Identificar onde histórico é gravado
- [x] Identificar por que não foi gravado para BGR.0070/25
- [x] Documentar fluxo atual

### **Fase 2: Implementação** ⏳
- [ ] Implementar Solução 2 (gravar histórico do cache)
- [ ] Integrar em `ProcessoAgent._consultar_status_processo`
- [ ] Integrar em `CeAgent._consultar_ce_maritimo`
- [ ] Integrar em `DiAgent._obter_dados_di`

### **Fase 3: Testes** ⏳
- [ ] Testar gravação de histórico do cache
- [ ] Validar dados gravados no banco
- [ ] Verificar se não aumenta custo

### **Fase 4: Validação** ⏳
- [ ] Executar `verificar_historico_bgr_0070.py` após implementação
- [ ] Confirmar que histórico está sendo gravado
- [ ] Validar que não há duplicatas

---

## 🎯 Recomendação

**Implementar Solução 2** (gravar histórico do cache) porque:

1. ✅ Não aumenta custo (usa dados já consultados)
2. ✅ Mantém histórico completo mesmo quando usa cache
3. ✅ Funciona para todos os cenários (cache + API)
4. ✅ Não impacta performance

**Próximo passo:** Implementar `gravar_historico_do_cache()` e integrar nos agents.

---

**Última atualização:** 08/01/2026  
**Status:** 📋 Análise completa - Aguardando implementação


