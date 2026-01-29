# 📊 ANÁLISE DO SISTEMA DE CONSULTAS BILHETADAS

**Data:** 15/12/2025  
**Contexto:** Análise solicitada pelo usuário sobre a rotina de consultas aprovadas e condições relacionadas.

---

## 🔍 RESUMO EXECUTIVO

O sistema atual **NÃO está usando** a funcionalidade de aprovação de consultas bilhetadas pendentes. A infraestrutura existe (tabela, funções), mas **não está sendo utilizada**. O sistema executa consultas diretamente quando solicitado.

---

## 📋 SITUAÇÃO ATUAL

### ✅ O que EXISTE no código:

1. **Tabela `consultas_bilhetadas_pendentes`** (db_manager.py, linha 70-86)
   - Estrutura completa com campos: `status`, `aprovado_em`, `aprovado_por`, etc.
   - Status possíveis: `'pendente'`, `'aprovado'`, `'rejeitado'`, `'executado'`

2. **Função `adicionar_consulta_pendente()`** (db_manager.py, linha 9271)
   - Função pronta para criar consultas pendentes
   - Verifica duplicatas antes de inserir

3. **Funções de gerenciamento** (db_manager.py):
   - `listar_consultas_pendentes()` - Lista consultas por status
   - `aprovar_consultas_pendentes()` - Aprova consultas
   - `rejeitar_consultas_pendentes()` - Rejeita consultas
   - `contar_consultas_pendentes()` - Estatísticas

4. **ConsultasBilhetadasService** (services/consultas_bilhetadas_service.py)
   - Serviço completo com 6 funções para gerenciar consultas pendentes
   - **PROBLEMA:** Tenta chamar endpoint que não existe

### ❌ O que NÃO EXISTE ou NÃO está sendo usado:

1. **Chamadas para `adicionar_consulta_pendente()`**
   - ❌ Nenhuma chamada encontrada no código
   - A função existe mas nunca é executada

2. **Endpoint `/api/int/consultas-bilhetadas/pendentes/aprovar`**
   - ❌ Não existe no `app.py`
   - ConsultasBilhetadasService tenta chamar este endpoint (linha 711)
   - **Isso causará erro quando tentar executar consultas aprovadas**

3. **Lógica de criação de consultas pendentes**
   - ❌ Não há código que crie consultas pendentes automaticamente
   - ❌ Não há verificação de "precisa aprovação" antes de consultar

---

## 🔄 FLUXO ATUAL (Como funciona AGORA)

### Quando o usuário pede para "consultar CE" ou "consultar DI":

1. **ChatService** detecta a intenção
2. Chama **ConsultaService.consultar_ce_maritimo()** ou similar
3. ConsultaService verifica:
   - `usar_cache_apenas=True` → Retorna do cache (sem bilhetar)
   - `forcar_consulta_api=True` → Chama API bilhetada diretamente
4. **API é chamada diretamente** via `call_integracomex()` (utils/integracomex_proxy.py)
5. Consulta é **registrada diretamente** em `consultas_bilhetadas` (não pendentes)
6. **NÃO passa pela fila de aprovação**

### Controle atual:

- **`usar_cache_apenas`**: Se True, usa cache (sem custo)
- **`forcar_consulta_api`**: Se True, força consulta bilhetada (com custo)
- **Padrão**: Se usuário pede "consultar", `forcar_consulta_api=True` automaticamente

---

## 🚨 PROBLEMAS IDENTIFICADOS

### 1. **ConsultasBilhetadasService tenta chamar endpoint inexistente**

**Arquivo:** `services/consultas_bilhetadas_service.py`, linha 711

```python
response = requests.post(
    'http://127.0.0.1:5500/api/int/consultas-bilhetadas/pendentes/aprovar',
    json={'ids': ids, 'aprovado_por': 'chat_ia'},
    timeout=300
)
```

**Problema:** Este endpoint não existe no `app.py`. Quando `executar_consultas_aprovadas()` for chamado, vai falhar.

### 2. **Sistema de aprovação não está sendo usado**

- A infraestrutura existe (tabela, funções)
- Mas nenhum código cria consultas pendentes
- Consultas são executadas diretamente

### 3. **Código legado do "duimp-processo"**

- A estrutura sugere que no "duimp-processo" havia aprovação manual
- No "maike" atual, isso não está implementado
- Usuário mencionou "palavra-chave para autorizar" - não encontrada no código atual

---

## 💡 RECOMENDAÇÕES

### Opção 1: **Remover código não utilizado** (Simplificar)

Se o sistema atual não precisa de aprovação manual:

1. **Remover ou simplificar ConsultasBilhetadasService**
   - Remover funções de aprovação/rejeição que não são usadas
   - Manter apenas listagem e estatísticas (se necessário)

2. **Remover tabela `consultas_bilhetadas_pendentes`** (ou deixar para uso futuro)
   - Se não está sendo usada, pode ser removida
   - Ou manter para implementação futura

3. **Corrigir `executar_consultas_aprovadas()`**
   - Remover chamada ao endpoint inexistente
   - Ou implementar o endpoint se realmente necessário

### Opção 2: **Implementar sistema de aprovação** (Se necessário)

Se realmente precisa de aprovação manual:

1. **Criar endpoint no app.py:**
   ```python
   @app.route('/api/int/consultas-bilhetadas/pendentes/aprovar', methods=['POST'])
   def aprovar_consultas_pendentes_endpoint():
       # Implementar lógica de aprovação
   ```

2. **Modificar fluxo de consultas:**
   - Quando `forcar_consulta_api=True`, criar consulta pendente
   - Aguardar aprovação antes de executar
   - Usuário aprova via chat: "aprovar consulta X"

3. **Adicionar palavras-chave para autorizar:**
   - Detectar palavras como "autorizar", "pode consultar", "pode bilhetar"
   - Quando detectado, criar consulta pendente ao invés de executar diretamente

### Opção 3: **Híbrido - Aprovação opcional**

1. **Manter execução direta como padrão**
2. **Adicionar modo "aprovacao_obrigatoria"** (configurável)
3. **Quando ativo, criar consultas pendentes**
4. **Quando inativo, executar diretamente (comportamento atual)**

---

## 🔧 CÓDIGO PROBLEMÁTICO IDENTIFICADO

### 1. ConsultasBilhetadasService.executar_consultas_aprovadas()

**Problema:** Tenta chamar endpoint que não existe

**Localização:** `services/consultas_bilhetadas_service.py`, linha 710-714

**Solução:** 
- Remover chamada ao endpoint
- Ou implementar endpoint no app.py
- Ou executar diretamente via db_manager

### 2. Função `adicionar_consulta_pendente()` nunca é chamada

**Problema:** Função existe mas não é usada

**Localização:** `db_manager.py`, linha 9271

**Solução:**
- Se não será usada, documentar como "legado" ou remover
- Se será usada, implementar chamadas nos pontos corretos

---

## 📊 COMPARAÇÃO: DUIMP-PROCESSO vs MAIKE

| Aspecto | DUIMP-PROCESSO (original) | MAIKE (atual) |
|---------|---------------------------|---------------|
| **Aprovação manual** | ✅ Sim, havia etapa de aprovação | ❌ Não, executa diretamente |
| **Fila de pendentes** | ✅ Usava `consultas_bilhetadas_pendentes` | ❌ Não usa (tabela existe mas vazia) |
| **Palavra-chave autorizar** | ✅ Provavelmente existia | ❌ Não encontrada no código |
| **Controle de custos** | ✅ Aprovação antes de bilhetar | ❌ Executa diretamente quando solicitado |
| **Fluxo** | Criar pendente → Aprovar → Executar | Executar diretamente |

---

## ✅ CONCLUSÃO

O sistema atual **não implementa aprovação manual de consultas bilhetadas**. A infraestrutura existe (tabela, funções, serviço), mas:

1. ❌ Nenhum código cria consultas pendentes
2. ❌ Consultas são executadas diretamente
3. ❌ Endpoint de aprovação não existe
4. ❌ ConsultasBilhetadasService tem código que não funciona (endpoint inexistente)

**Recomendação:** Decidir se precisa de aprovação manual:
- **Se NÃO precisa:** Simplificar código, remover/simplificar ConsultasBilhetadasService
- **Se PRECISA:** Implementar criação de consultas pendentes e endpoint de aprovação

---

## 🎯 PRÓXIMOS PASSOS SUGERIDOS

1. **Decisão:** Sistema precisa de aprovação manual ou não?
2. **Se não precisa:**
   - Simplificar ConsultasBilhetadasService
   - Remover código de aprovação não utilizado
   - Corrigir `executar_consultas_aprovadas()` para não chamar endpoint inexistente
3. **Se precisa:**
   - Implementar criação de consultas pendentes
   - Criar endpoint de aprovação no app.py
   - Adicionar detecção de palavras-chave para "autorizar"












