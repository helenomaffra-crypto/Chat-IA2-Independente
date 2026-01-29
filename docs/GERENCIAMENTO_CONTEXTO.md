# Gerenciamento de Contexto na Aplicação

## 📋 Visão Geral

A aplicação gerencia contexto de **duas formas principais**:

1. **Histórico de Conversas** (`conversas_chat`) - Armazena mensagens e respostas
2. **Contexto de Sessão** (`contexto_sessao`) - Armazena informações contextuais específicas (processos, categorias, alíquotas)

Ambos são armazenados em **SQLite** (banco local `chat_ia.db`) e identificados por **`session_id`**.

---

## 🗄️ Estrutura de Armazenamento

### 1. Tabela `conversas_chat`

**Localização:** SQLite (`chat_ia.db`)

**Estrutura:**
```sql
CREATE TABLE conversas_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,           -- ID da sessão (identificador único)
    mensagem_usuario TEXT NOT NULL,     -- Mensagem do usuário
    resposta_ia TEXT NOT NULL,          -- Resposta da IA
    tipo_conversa TEXT,                 -- 'consulta', 'acao', 'geral', etc.
    processo_referencia TEXT,           -- Processo mencionado (se houver)
    importante BOOLEAN DEFAULT 0,       -- Se é uma conversa importante
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Índices:**
- `idx_conversas_session` - Busca rápida por `session_id` e data
- `idx_conversas_importante` - Busca conversas importantes

**Como funciona:**
- Cada mensagem/resposta é salva automaticamente
- Identificada por `session_id` (geralmente IP do cliente ou ID do navegador)
- Permite recuperar histórico completo da conversa

**Uso:**
- Recuperar últimas respostas para contexto
- Detectar qual relatório enviar quando usuário diz "envie esse relatorio"
- Manter histórico entre sessões (se `session_id` persistir)

---

### 2. Tabela `contexto_sessao`

**Localização:** SQLite (`chat_ia.db`)

**Estrutura:**
```sql
CREATE TABLE contexto_sessao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,           -- ID da sessão
    tipo_contexto TEXT NOT NULL,        -- 'processo_atual', 'categoria_atual', 'ncm_aliquotas', etc.
    chave TEXT NOT NULL,                -- Chave do contexto (ex: 'processo_referencia', 'categoria')
    valor TEXT NOT NULL,                -- Valor do contexto (ex: 'VDM.0004/25', 'VDM')
    dados_json TEXT,                    -- Dados adicionais em JSON
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, tipo_contexto, chave)
)
```

**Índices:**
- `idx_contexto_sessao` - Busca rápida por `session_id` e `tipo_contexto`

**Tipos de Contexto:**
- `processo_atual` - Processo mencionado na conversa
- `categoria_atual` - Categoria em foco (ex: 'VDM', 'ALH')
- `ncm_aliquotas` - NCM e alíquotas da última consulta TECwin
- `ultima_consulta` - Última consulta realizada

**Como funciona:**
- Salva informações contextuais específicas (não toda a conversa)
- Atualiza automaticamente quando há nova informação
- Permite recuperar contexto específico rapidamente

**Uso:**
- Buscar alíquotas do TECwin para cálculo de impostos
- Lembrar qual processo está sendo consultado
- Manter categoria em foco durante a conversa

---

## 🔑 Identificação: `session_id`

### Como é Gerado

**No `app.py`:**
```python
session_id = data.get('session_id') or request.remote_addr
```

**Ordem de prioridade:**
1. `session_id` fornecido pelo cliente (frontend)
2. Se não fornecido, usa `request.remote_addr` (IP do cliente)

### Persistência

- **Se o frontend fornece `session_id`:** Contexto persiste entre sessões
- **Se usa IP:** Contexto pode mudar se IP mudar (ex: VPN, rede diferente)

**Recomendação:** Frontend deve gerar e persistir `session_id` (ex: localStorage, cookie)

---

## 📊 Fluxo de Gerenciamento de Contexto

### 1. Salvamento Automático

**Conversas:**
```python
# Em app.py, após processar mensagem:
# A conversa é salva automaticamente em conversas_chat
```

**Contexto:**
```python
# Em services/context_service.py:
from services.context_service import salvar_contexto_sessao

# Salvar processo mencionado
salvar_contexto_sessao(
    session_id='abc123',
    tipo_contexto='processo_atual',
    chave='processo_referencia',
    valor='VDM.0004/25'
)

# Salvar alíquotas do TECwin
salvar_contexto_sessao(
    session_id='abc123',
    tipo_contexto='ncm_aliquotas',
    chave='ncm',
    valor='90041000',
    dados_adicionais={
        'aliquotas': {
            'ii': 18.0,
            'ipi': 9.75,
            'pis': 2.1,
            'cofins': 7.6
        }
    }
)
```

### 2. Recuperação de Contexto

**Buscar contexto:**
```python
from services.context_service import buscar_contexto_sessao

# Buscar todos os contextos da sessão
contextos = buscar_contexto_sessao(session_id='abc123')

# Buscar contexto específico
aliquotas = buscar_contexto_sessao(
    session_id='abc123',
    tipo_contexto='ncm_aliquotas'
)
```

**Buscar histórico:**
```python
# Em services/chat_service.py:
# O histórico é recuperado do banco quando necessário
cursor.execute('''
    SELECT resposta FROM conversas_chat 
    WHERE session_id = ? 
    ORDER BY criado_em DESC 
    LIMIT 5
''', (session_id,))
```

### 3. Uso no Prompt da IA

**Formatação para prompt:**
```python
from services.context_service import formatar_contexto_para_prompt

contextos = buscar_contexto_sessao(session_id)
contexto_formatado = formatar_contexto_para_prompt(contextos)

# Adiciona ao prompt:
# "📌 CONTEXTO: Processo: VDM.0004/25, Categoria: VDM"
```

---

## 💾 Cache vs Persistência

### O que é Cache?

**Cache em memória:**
- Dados temporários durante execução
- Perdidos quando aplicação reinicia
- Exemplo: `self._cache_web_search` em `NCMService`

**Cache em SQLite:**
- Dados persistentes entre execuções
- Exemplo: `classif_cache` (NCMs), `processos_kanban` (processos)

### O que é Contexto?

**Contexto de Sessão:**
- Informações específicas da conversa atual
- Identificado por `session_id`
- Persistente em SQLite
- Exemplo: processo mencionado, alíquotas do TECwin

**Histórico de Conversas:**
- Todas as mensagens e respostas
- Identificado por `session_id`
- Persistente em SQLite
- Usado para recuperar últimas respostas

---

## 🔍 Exemplos Práticos

### Exemplo 1: Consulta de Processo

```
Usuário: "situacao do vdm.0004/25"
→ Sistema salva em contexto_sessao:
   - tipo_contexto: 'processo_atual'
   - valor: 'VDM.0004/25'
→ Sistema salva em conversas_chat:
   - mensagem_usuario: "situacao do vdm.0004/25"
   - resposta_ia: "📋 Processo VDM.0004/25..."
```

### Exemplo 2: Consulta TECwin + Cálculo de Impostos

```
Usuário: "tecwin 90041000"
→ Sistema salva em contexto_sessao:
   - tipo_contexto: 'ncm_aliquotas'
   - chave: 'ncm'
   - valor: '90041000'
   - dados_json: {'aliquotas': {'ii': 18, 'ipi': 9.75, ...}}

Usuário: "calcule os impostos para 10.000 dólares"
→ Sistema busca contexto:
   - Busca alíquotas do contexto_sessao (tipo: 'ncm_aliquotas')
   - Usa alíquotas para calcular impostos
```

### Exemplo 3: Envio de Relatório

```
Usuário: "o que temos pra hoje?"
→ Sistema salva em conversas_chat:
   - resposta_ia: "🚢 11 Processo(s) Chegando Hoje..."

Usuário: "envie esse relatorio para email@exemplo.com"
→ Sistema busca última resposta:
   - SELECT resposta FROM conversas_chat WHERE session_id = ? ORDER BY criado_em DESC LIMIT 1
   - Detecta que é relatório de "CHEGANDO HOJE"
   - Usa enviar_relatorio_email com tipo_relatorio='resumo'
```

---

## 🎯 Vantagens do Sistema Atual

### ✅ Persistência
- Contexto persiste entre sessões (se `session_id` persistir)
- Histórico completo disponível

### ✅ Performance
- Índices otimizados para buscas rápidas
- Cache local (SQLite) - sem dependência de rede

### ✅ Flexibilidade
- Múltiplos tipos de contexto
- Dados adicionais em JSON
- Fácil adicionar novos tipos de contexto

### ✅ Escalabilidade
- SQLite suporta milhões de registros
- Índices garantem performance mesmo com muito histórico

---

## ⚠️ Limitações e Considerações

### 1. Session ID

**Problema:** Se `session_id` mudar, contexto é perdido

**Solução:** Frontend deve gerar e persistir `session_id` (localStorage, cookie)

### 2. Limpeza de Contexto

**Atual:** Contexto não é limpo automaticamente

**Recomendação:** Implementar limpeza periódica de contextos antigos (> 30 dias)

### 3. Múltiplos Usuários

**Atual:** Cada `session_id` tem seu próprio contexto

**Funciona bem para:** Aplicações single-user ou multi-user com sessões separadas

---

## 📝 Resumo

**A aplicação gerencia contexto em SQLite por `session_id`:**

1. **`conversas_chat`** - Histórico completo de mensagens/respostas
2. **`contexto_sessao`** - Informações contextuais específicas (processos, alíquotas, etc.)

**Ambos são:**
- ✅ Persistidos em SQLite (banco local)
- ✅ Identificados por `session_id`
- ✅ Recuperados automaticamente quando necessário
- ✅ Usados para enriquecer prompts da IA

**Não é cache temporário** - é **persistência de contexto** para manter continuidade entre mensagens e sessões.



