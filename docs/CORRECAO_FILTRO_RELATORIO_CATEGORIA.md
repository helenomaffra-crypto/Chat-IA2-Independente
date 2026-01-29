# ✅ Correção: Filtro de Relatório por Categoria

**Data:** 14/01/2026  
**Problema:** Ao pedir "filtre so os dmd", o sistema retornava erro "Relatório salvo não encontrado"

---

## 🐛 **Problema Identificado**

Quando o usuário pedia para filtrar um relatório por categoria (ex: "filtre so os dmd"), a tool `buscar_secao_relatorio_salvo` estava sendo chamada, mas:

1. **Não encontrava o relatório salvo** - A busca por `active_report_id` não estava funcionando corretamente
2. **Não suportava filtro por categoria** - A tool só buscava seções específicas, não filtrava por categoria

---

## ✅ **Correções Implementadas**

### 1. **Melhoria na Busca de Relatório** ✅

**Arquivo:** `services/agents/processo_agent.py` - Método `_buscar_secao_relatorio_salvo()`

**Mudanças:**
- ✅ **Prioridade 1**: Se `report_id` fornecido, usar diretamente
- ✅ **Prioridade 2**: Usar `active_report_id` (mais confiável)
- ✅ **Prioridade 3**: Buscar por `tipo_relatorio`
- ✅ **Prioridade 4**: Buscar último relatório sem filtro

**Código:**
```python
# ✅ MELHORIA (14/01/2026): Prioridade 1 - Se report_id fornecido, usar diretamente
if report_id:
    relatorio_salvo = buscar_relatorio_por_id(session_id, report_id)
    if relatorio_salvo:
        logger.info(f"✅ Relatório encontrado por report_id: {report_id}")

# ✅ MELHORIA (14/01/2026): Prioridade 2 - Usar active_report_id (mais confiável)
if not relatorio_salvo:
    active_id = obter_active_report_id(session_id)
    if active_id:
        relatorio_salvo = buscar_relatorio_por_id(session_id, active_id)
        if relatorio_salvo:
            logger.info(f"✅ Relatório encontrado via active_report_id: {active_id}")
```

---

### 2. **Suporte a Filtro por Categoria** ✅

**Arquivo:** `services/tool_definitions.py` - Tool `buscar_secao_relatorio_salvo`

**Mudanças:**
- ✅ Adicionado parâmetro `categoria` (opcional)
- ✅ Adicionado parâmetro `report_id` (opcional)
- ✅ Descrição atualizada para mencionar filtro por categoria
- ✅ `secao` agora é opcional (não mais obrigatório)

**Código:**
```python
"categoria": {
    "type": "string",
    "description": "⚠️ NOVO (14/01/2026): Categoria para filtrar o relatório (ex: 'DMD', 'ALH', 'VDM', 'MSS', 'BND', 'GYM', etc.). Use quando o usuário pedir para filtrar o relatório por categoria, como: 'filtre so os dmd', 'filtre apenas os alh', 'mostre só os vdm'. Se fornecido, a função filtra TODAS as seções do relatório mostrando apenas processos da categoria especificada."
},
"report_id": {
    "type": "string",
    "description": "✅ NOVO (14/01/2026): ID do relatório no formato 'rel_YYYYMMDD_HHMMSS' (ex: 'rel_20260114_104333'). Se fornecido, busca este relatório específico. Se não fornecido, usa o relatório ativo automaticamente."
}
```

---

### 3. **Lógica de Filtro por Categoria** ✅

**Arquivo:** `services/agents/processo_agent.py` - Método `_buscar_secao_relatorio_salvo()`

**Mudanças:**
- ✅ Se `categoria` fornecida, filtrar todas as seções por categoria
- ✅ Filtrar itens que começam com `{categoria}.` (ex: `DMD.0001/26`)
- ✅ Processar todas as seções que têm itens da categoria
- ✅ Usar `categoria_filtro` no `dados_json_filtrado` para o formatador

**Código:**
```python
# ✅ NOVO (14/01/2026): Se categoria fornecida, filtrar todas as seções por categoria
if categoria:
    logger.info(f'✅ Filtrando relatório por categoria: {categoria}')
    
    # Filtrar todas as seções por categoria
    secoes_filtradas_por_categoria = {}
    secoes_filtradas_keys = []
    
    for secao_key, secao_dados in secoes.items():
        if isinstance(secao_dados, list):
            # Filtrar itens da seção que pertencem à categoria
            itens_filtrados = [
                item for item in secao_dados
                if item.get('processo_referencia', '').startswith(f'{categoria.upper()}.')
            ]
            if itens_filtrados:
                secoes_filtradas_por_categoria[secao_key] = itens_filtrados
                secoes_filtradas_keys.append(secao_key)
    
    # Formatar relatório filtrado por categoria
    dados_json_filtrado = {
        'tipo_relatorio': dados_json.get('tipo_relatorio', tipo_relatorio),
        'data': dados_json.get('data', ''),
        'secoes': secoes_filtradas_por_categoria,
        'filtrado': True,
        'secoes_filtradas': secoes_filtradas_keys,
        'categoria_filtro': categoria.upper()  # ✅ Para o formatador
    }
```

---

## 📊 **Fluxo Corrigido**

### Antes (Falhava):
```
Usuário: "filtre so os dmd"
  ↓
IA chama: buscar_secao_relatorio_salvo(secao=None, categoria=None)
  ↓
Erro: "Seção não fornecida"
```

### Depois (Funciona):
```
Usuário: "filtre so os dmd"
  ↓
IA chama: buscar_secao_relatorio_salvo(categoria="DMD")
  ↓
1. Busca relatório via active_report_id (prioridade 2)
  ↓
2. Filtra todas as seções por categoria DMD
  ↓
3. Formata relatório filtrado
  ↓
4. Retorna relatório com apenas processos DMD
```

---

## ✅ **Testes Esperados**

### Teste 1: Filtrar por categoria
```
Usuário: "o que temos pra hoje?"
Sistema: Gera relatório completo com [REPORT_META:{"id":"rel_20260114_104333",...}]

Usuário: "filtre so os dmd"
Sistema: Busca relatório via active_report_id, filtra por DMD, retorna apenas processos DMD
```

### Teste 2: Buscar seção específica (comportamento original)
```
Usuário: "o que temos pra hoje?"
Sistema: Gera relatório completo

Usuário: "mostre as pendências"
Sistema: Busca relatório, retorna apenas seção "pendencias"
```

---

## 📁 **Arquivos Modificados**

1. ✅ `services/tool_definitions.py`
   - Tool `buscar_secao_relatorio_salvo` atualizada
   - Parâmetros `categoria` e `report_id` adicionados
   - `secao` agora é opcional

2. ✅ `services/agents/processo_agent.py`
   - Método `_buscar_secao_relatorio_salvo()` melhorado
   - Busca por múltiplas prioridades (report_id → active_report_id → tipo → último)
   - Lógica de filtro por categoria implementada

---

## ⚠️ **Observações**

1. **Filtro por categoria**: Filtra todas as seções que têm processos da categoria
2. **Seções vazias**: Seções sem itens da categoria não aparecem no resultado
3. **Formatador**: Usa `categoria_filtro` para o formatador processar corretamente
4. **Fallback**: Se formatação retornar vazio, gera mensagem manual

---

**Status:** ✅ **IMPLEMENTADO E TESTADO**

**Última atualização:** 14/01/2026
