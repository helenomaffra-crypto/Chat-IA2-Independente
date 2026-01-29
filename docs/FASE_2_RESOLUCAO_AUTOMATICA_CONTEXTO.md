# 🎯 Fase 2: Resolução Automática de Contexto

**Data:** 14/01/2026  
**Status:** 📋 **PLANEJADO** - Aguardando aprovação para implementação

---

## 📋 O Que É a Fase 2?

**Resolução Automática de Contexto** = Sistema que **injeta automaticamente** valores faltantes nos argumentos das tools baseado no contexto da sessão, **antes** de executar.

### Problema que Resolve

**Cenário Real:**
```
Usuário: "o que temos pra hoje?"
IA: [Gera relatório completo com report_id="rel_20260114_095826"]

Usuário: "filtre só os DMD"
IA: [Gera tool call: buscar_secao_relatorio_salvo(secao="processos_chegando", categoria="DMD")]
     ❌ PROBLEMA: Não passou report_id!
     
Sistema: ❌ Erro "Nenhum relatório ativo encontrado"
```

**Com Fase 2:**
```
Usuário: "filtre só os DMD"
IA: [Gera tool call: buscar_secao_relatorio_salvo(secao="processos_chegando", categoria="DMD")]
     ❌ PROBLEMA: Não passou report_id!

Gate: ✅ Detecta que falta report_id
Gate: ✅ Busca active_report_id na sessão
Gate: ✅ Injeta automaticamente: report_id="rel_20260114_095826"
     
Sistema: ✅ Executa com sucesso usando o relatório ativo
```

---

## 🏗️ Arquitetura Proposta

### 1. **Criar `ToolGateService`**

**Arquivo:** `services/tool_gate_service.py`

**Responsabilidades:**
- Validar contrato de tool (campos obrigatórios, tipos)
- Resolver contexto automaticamente (injetar valores faltantes)
- Decidir se precisa preview/confirmação (ações sensíveis)

### 2. **Método Principal: `resolver_contexto_tool()`**

```python
def resolver_contexto_tool(
    nome_tool: str,
    args: Dict[str, Any],
    session_id: str
) -> Dict[str, Any]:
    """
    Resolve contexto automaticamente para uma tool.
    
    Injeta valores faltantes baseado no contexto da sessão:
    - report_id → active_report_id
    - processo_referencia → processo_atual (se não mencionado)
    - etc.
    
    Returns:
        {
            'args_resolvidos': Dict,  # Argumentos com valores injetados
            'erro': str (opcional)     # Se não conseguir resolver
        }
    """
```

### 3. **Regras de Resolução**

#### Regra 1: `report_id` para Tools de Relatório
```python
# Tools que precisam de report_id:
TOOLS_RELATORIO = [
    'buscar_secao_relatorio_salvo',
    'filtrar_relatorio',
    'melhorar_relatorio',
    'enviar_relatorio_email'
]

# Se tool precisa report_id e não foi fornecido:
if nome_tool in TOOLS_RELATORIO:
    if 'report_id' not in args or not args['report_id']:
        active_id = obter_active_report_id(session_id)
        if active_id:
            args['report_id'] = active_id
            logger.info(f"✅ report_id injetado: {active_id}")
        else:
            return {
                'erro': 'Nenhum relatório ativo. Gere um relatório primeiro (ex: "o que temos pra hoje?")'
            }
```

#### Regra 2: `processo_referencia` para Tools de Processo
```python
# Tools que precisam de processo_referencia:
TOOLS_PROCESSO = [
    'consultar_status_processo',
    'consultar_di_processo',
    'consultar_duimp_processo',
    'criar_duimp'
]

# Se tool precisa processo e não foi fornecido:
if nome_tool in TOOLS_PROCESSO:
    if 'processo_referencia' not in args or not args['processo_referencia']:
        processo_atual = obter_processo_atual(session_id)
        if processo_atual:
            args['processo_referencia'] = processo_atual
            logger.info(f"✅ processo_referencia injetado: {processo_atual}")
        else:
            return {
                'erro': 'Nenhum processo mencionado. Especifique o processo (ex: "DMD.0001/26")'
            }
```

#### Regra 3: Valores Padrão
```python
# Valores padrão para argumentos opcionais
DEFAULTS = {
    'criar_duimp': {'ambiente': 'Validacao'},
    'consultar_status_processo': {'incluir_documentos': True},
    # etc.
}

# Aplicar defaults se não especificado
if nome_tool in DEFAULTS:
    for key, default_value in DEFAULTS[nome_tool].items():
        if key not in args or args[key] is None:
            args[key] = default_value
```

---

## 🔄 Fluxo Completo

### Antes (Sem Fase 2)

```
Usuário: "filtre só os DMD"
  ↓
IA: buscar_secao_relatorio_salvo(secao="processos_chegando", categoria="DMD")
  ↓
Tool Executor: Executa diretamente
  ↓
Tool: ❌ Erro "report_id não fornecido"
  ↓
Resposta: "❌ Nenhum relatório ativo encontrado"
```

### Depois (Com Fase 2)

```
Usuário: "filtre só os DMD"
  ↓
IA: buscar_secao_relatorio_salvo(secao="processos_chegando", categoria="DMD")
  ↓
Tool Gate: resolver_contexto_tool()
  - Detecta: falta report_id
  - Busca: active_report_id = "rel_20260114_095826"
  - Injeta: args['report_id'] = "rel_20260114_095826"
  ↓
Tool Executor: Executa com args resolvidos
  ↓
Tool: ✅ Busca seção do relatório ativo
  ↓
Resposta: "📊 DMDs que chegam hoje: ..."
```

---

## 📝 Exemplos de Uso

### Exemplo 1: Filtrar Relatório sem report_id

**Input:**
```python
nome_tool = "buscar_secao_relatorio_salvo"
args = {
    "secao": "processos_chegando",
    "categoria": "DMD"
}
session_id = "session_123"
```

**Processamento:**
```python
# Gate detecta que falta report_id
# Busca active_report_id na sessão
active_id = obter_active_report_id("session_123")
# Retorna: "rel_20260114_095826"

# Injeta automaticamente
args['report_id'] = "rel_20260114_095826"
```

**Output:**
```python
{
    'args_resolvidos': {
        'secao': 'processos_chegando',
        'categoria': 'DMD',
        'report_id': 'rel_20260114_095826'  # ✅ Injetado automaticamente
    }
}
```

### Exemplo 2: Consultar Processo sem processo_referencia

**Input:**
```python
nome_tool = "consultar_status_processo"
args = {}  # Vazio
session_id = "session_123"
```

**Processamento:**
```python
# Gate detecta que falta processo_referencia
# Busca processo_atual na sessão
processo_atual = obter_processo_atual("session_123")
# Retorna: "DMD.0001/26"

# Injeta automaticamente
args['processo_referencia'] = "DMD.0001/26"
```

**Output:**
```python
{
    'args_resolvidos': {
        'processo_referencia': 'DMD.0001/26',  # ✅ Injetado automaticamente
        'incluir_documentos': True  # ✅ Default aplicado
    }
}
```

### Exemplo 3: Sem Contexto Disponível

**Input:**
```python
nome_tool = "buscar_secao_relatorio_salvo"
args = {"secao": "processos_chegando"}
session_id = "session_123"
# active_report_id = None (não há relatório ativo)
```

**Output:**
```python
{
    'erro': 'Nenhum relatório ativo. Gere um relatório primeiro (ex: "o que temos pra hoje?")'
}
```

---

## 🔧 Integração com Sistema Atual

### Onde Integrar?

**Arquivo:** `services/tool_executor.py` ou `services/chat_service.py`

**Ponto de Integração:**
```python
# ANTES de executar tool
def executar_tool(nome_tool, args, session_id):
    # ✅ NOVO: Resolver contexto antes de executar
    gate_service = get_tool_gate_service()
    resultado_resolucao = gate_service.resolver_contexto_tool(
        nome_tool=nome_tool,
        args=args,
        session_id=session_id
    )
    
    if resultado_resolucao.get('erro'):
        return {
            'sucesso': False,
            'resposta': resultado_resolucao['erro']
        }
    
    # Usar args resolvidos
    args_resolvidos = resultado_resolucao['args_resolvidos']
    
    # Executar tool com args resolvidos
    resultado = tool_router.route(nome_tool, args_resolvidos)
    return resultado
```

---

## 📊 Mapeamento de Tools

### Tools que Precisam `report_id`

| Tool | Quando Precisa |
|------|----------------|
| `buscar_secao_relatorio_salvo` | Sempre (obrigatório) |
| `filtrar_relatorio` | Sempre (obrigatório) |
| `melhorar_relatorio` | Sempre (obrigatório) |
| `enviar_relatorio_email` | Se não especificar relatório específico |

### Tools que Precisam `processo_referencia`

| Tool | Quando Precisa |
|------|----------------|
| `consultar_status_processo` | Se não mencionado na mensagem |
| `consultar_di_processo` | Se não mencionado na mensagem |
| `consultar_duimp_processo` | Se não mencionado na mensagem |
| `criar_duimp` | Sempre (obrigatório) |

### Tools com Valores Padrão

| Tool | Default |
|------|---------|
| `criar_duimp` | `ambiente: 'Validacao'` |
| `consultar_status_processo` | `incluir_documentos: True` |

---

## ⚠️ Considerações Importantes

### 1. **Não Sobrescrever Valores Explícitos**

```python
# Se usuário especificou explicitamente, NÃO sobrescrever
if 'report_id' in args and args['report_id']:
    # Usuário especificou explicitamente - não injetar
    return {'args_resolvidos': args}
```

### 2. **Prioridade de Resolução**

1. **Valor explícito na tool call** (maior prioridade)
2. **Contexto da sessão** (active_report_id, processo_atual)
3. **Valor padrão** (defaults)

### 3. **Mensagens de Erro Claras**

```python
# ❌ Ruim
return {'erro': 'report_id não encontrado'}

# ✅ Bom
return {
    'erro': 'Nenhum relatório ativo. Gere um relatório primeiro (ex: "o que temos pra hoje?")'
}
```

### 4. **Logging Detalhado**

```python
logger.info(f"✅ Contexto resolvido para {nome_tool}: {args_resolvidos}")
logger.warning(f"⚠️ Não foi possível resolver contexto para {nome_tool}: {erro}")
```

---

## 🧪 Testes Necessários

### Teste 1: Injeção de report_id
```
1. Gerar relatório → active_report_id salvo
2. Pedir "filtre só os DMD" (sem report_id)
3. Verificar: report_id foi injetado automaticamente
4. Verificar: tool executou com sucesso
```

### Teste 2: Injeção de processo_referencia
```
1. Consultar processo DMD.0001/26 → processo_atual salvo
2. Pedir "e a DI?" (sem processo_referencia)
3. Verificar: processo_referencia foi injetado automaticamente
4. Verificar: tool executou com sucesso
```

### Teste 3: Sem Contexto Disponível
```
1. Pedir "filtre só os DMD" (sem relatório ativo)
2. Verificar: retorna erro claro pedindo para gerar relatório
3. Verificar: não tenta executar tool
```

### Teste 4: Valor Explícito Não Sobrescrito
```
1. Gerar relatório → active_report_id = "rel_123"
2. Pedir "filtre rel_456" (report_id explícito)
3. Verificar: usa rel_456 (não sobrescreve com rel_123)
```

---

## 📈 Benefícios Esperados

### 1. **Redução de Erros**
- ❌ **Antes:** ~30-40% de falhas por falta de contexto
- ✅ **Depois:** ~5-10% de falhas (apenas casos muito específicos)

### 2. **Melhor UX**
- Usuário não precisa mencionar `report_id` toda vez
- Sistema "lembra" do contexto automaticamente
- Conversas mais naturais

### 3. **Menos Dependência da IA**
- Sistema resolve contexto determinísticamente
- Não depende da IA "lembrar" de passar argumentos
- Mais robusto e previsível

---

## 🚀 Plano de Implementação

### Passo 1: Criar `ToolGateService`
- Arquivo: `services/tool_gate_service.py`
- Método: `resolver_contexto_tool()`
- Método: `validar_contrato_tool()` (básico, para Fase 3)

### Passo 2: Mapear Tools
- Lista de tools que precisam `report_id`
- Lista de tools que precisam `processo_referencia`
- Valores padrão por tool

### Passo 3: Integrar no Fluxo
- Integrar em `ToolExecutor` ou `ChatService`
- Chamar `resolver_contexto_tool()` antes de executar

### Passo 4: Testes
- Testes unitários para cada regra de resolução
- Testes de integração com cenários reais

### Passo 5: Documentação
- Atualizar README
- Documentar regras de resolução

---

## ⚠️ Riscos e Mitigações

### Risco 1: Injetar Valor Errado
**Mitigação:** 
- Sempre verificar se valor explícito foi fornecido
- Não sobrescrever valores explícitos
- Logging detalhado de todas as injeções

### Risco 2: Performance (Queries ao Banco)
**Mitigação:**
- Cache em memória para `active_report_id` e `processo_atual`
- Buscar apenas quando necessário

### Risco 3: Contexto Desatualizado
**Mitigação:**
- TTL para contexto (ex: active_report_id válido por 1h)
- Verificar se contexto ainda é válido antes de usar

---

## 📝 Conclusão

**Fase 2 resolve um problema real:** Usuários perdem contexto quando pedem para filtrar/melhorar relatórios ou fazer follow-ups de processos.

**Implementação:** Relativamente simples, mas precisa de cuidado para não sobrescrever valores explícitos.

**Recomendação:** ✅ **Vale a pena implementar** - Melhora significativamente a UX e reduz falhas.

---

**Próximo passo:** Aguardar aprovação para implementação.
