# 🏗️ Arquitetura de Tools e Refatoração do `db_manager.py`

**Data:** 17/01/2026  
**Status:** 📋 **DOCUMENTAÇÃO** - Explicação da arquitetura atual e migração

---

## 🎯 **ESCLARECIMENTO IMPORTANTE: Tools vs Implementações**

**⚠️ CONFUSÃO COMUM:** "As tools estão no `db_manager.py`?"

**✅ RESPOSTA:** **NÃO!** As tools (definições/schemas) estão em `tool_definitions.py`. O `db_manager.py` contém as **funções de implementação** que as tools chamam.

### **Diferença Crucial:**

| Item | Onde Está | O Que Faz |
|------|-----------|-----------|
| **Tools (definições)** | `tool_definitions.py` | Define schemas (nome, parâmetros, descrição) |
| **Handlers das tools** | `services/agents/*.py` | Processa argumentos e formata resposta |
| **Funções reais (SQL)** | `db_manager.py` | Faz queries SQL e lógica de negócio |

### **Exemplo Prático:**

**1. Tool Definition (schema):**
```python
# tool_definitions.py
{
    "name": "listar_processos_registrados_hoje",
    "description": "Lista processos registrados hoje...",
    "parameters": {...}
}
```

**2. Handler no Agent:**
```python
# services/agents/processo_agent.py
def _listar_registrados_hoje(self, arguments, context):
    # Processa argumentos
    categoria = arguments.get('categoria')
    # Chama função real do db_manager
    from db_manager import listar_processos_registrados_hoje
    processos = listar_processos_registrados_hoje(categoria)
    # Formata resposta
    return {'resposta': f"Encontrados {len(processos)} processos"}
```

**3. Função Real (SQL):**
```python
# db_manager.py
def listar_processos_registrados_hoje(categoria=None, limit=200):
    # Query SQL real aqui
    conn = get_db_connection()
    cursor.execute("SELECT ... FROM processos_kanban ...")
    return processos
```

**✅ Conclusão:** O problema não é que as "tools" estão no `db_manager.py`, mas sim que as **104 funções de implementação** estão todas misturadas em um único arquivo gigante (14.145 linhas).

---

## 📊 **ARQUITETURA ATUAL (ANTES DA REFATORAÇÃO COMPLETA)**

### **Fluxo de Execução de uma Tool**

```
1. Usuário pergunta: "quais DMD foram registrados?"
   ↓
2. IA decide chamar tool: `listar_processos_registrados_hoje`
   ↓
3. tool_definitions.py → Define o SCHEMA da tool (parâmetros, descrição)
   ↓
4. tool_router.py → Mapeia tool_name → agent_name
   Exemplo: 'listar_processos_registrados_hoje' → 'processo'
   ↓
5. ProcessoAgent.execute() → Recebe a tool e chama handler correspondente
   ↓
6. ProcessoAgent._listar_registrados_hoje() → Handler que implementa a lógica
   ↓
7. db_manager.listar_processos_registrados_hoje() → Função REAL que faz query SQL
   ↓
8. Retorna resultado formatado para o usuário
```

---

## 🧭 **Policy determinística (antes do modelo) — IntentPolicyService (18/01/2026)**

Algumas intenções precisam ser **determinísticas** (compliance/auditoria), sem depender do modelo escolher “conhecimento do modelo” vs tool:

- **NESH direto**: quando o usuário pede “nesh …” ou “nota explicativa …”, o sistema deve **forçar** a tool `buscar_nota_explicativa_nesh`.
- **Legislação/base legal**: quando o usuário pede “pela legislação”, “base legal”, “artigo”, etc., o sistema deve **forçar** `buscar_legislacao_responses` e manter um **TTL curto** por sessão para follow-ups (ex.: “quanto tempo…”).

Isso foi centralizado em:
- `services/intent_policy_service.py` (camada policy-as-code)
- `config/intent_policy_rules.json` (regras/padrões/TTL configuráveis)
- Integração no `PrecheckService` (`services/precheck_service.py`)

### **Arquivos e Responsabilidades**

#### 1. **`services/tool_definitions.py`** (3.219 linhas)
**Responsabilidade:** **DEFINE** quais tools existem e seus schemas (parâmetros)

- ✅ **O QUE FAZ:** Lista todas as tools disponíveis para a IA
- ✅ **EXEMPLO:**
  ```python
  {
      "type": "function",
      "function": {
          "name": "listar_processos_registrados_hoje",
          "description": "Lista processos que tiveram DI ou DUIMP registrada HOJE...",
          "parameters": {
              "type": "object",
              "properties": {
                  "categoria": {"type": "string", "description": "Categoria do processo (ex: DMD, ALH)"},
                  "limite": {"type": "integer", "description": "Limite de resultados"}
              }
          }
      }
  }
  ```
- ✅ **NÃO CONTÉM:** A implementação real (só o schema/contrato)

---

#### 2. **`services/tool_router.py`** (330 linhas)
**Responsabilidade:** **MAPEIA** tool_name → agent_name

- ✅ **O QUE FAZ:** Diz qual agent é responsável por cada tool
- ✅ **EXEMPLO:**
  ```python
  tool_to_agent = {
      'listar_processos_registrados_hoje': 'processo',  # ← ProcessoAgent
      'criar_duimp': 'duimp',  # ← DuimpAgent
      'consultar_ce_maritimo': 'ce',  # ← CeAgent
      # ...
  }
  ```
- ✅ **NÃO CONTÉM:** A implementação real (só o roteamento)

---

#### 3. **`services/agents/processo_agent.py`** (8.014 linhas)
**Responsabilidade:** **IMPLEMENTA** handlers de tools de processos

- ✅ **O QUE FAZ:** Contém os handlers que processam as tools de processos
- ✅ **EXEMPLO:**
  ```python
  def _listar_registrados_hoje(self, arguments, context):
      categoria = arguments.get('categoria')
      limite = arguments.get('limite', 200)
      
      # ⚠️ AINDA IMPORTA DO db_manager.py
      from db_manager import listar_processos_registrados_hoje
      
      processos = listar_processos_registrados_hoje(
          categoria=categoria.upper() if categoria else None,
          limit=limite
      )
      
      # Formata resposta
      return {
          'sucesso': True,
          'resposta': f"📋 Processos registrados hoje: {len(processos)}"
      }
  ```
- ⚠️ **PROBLEMA ATUAL:** Agents ainda **importam** funções do `db_manager.py`
- ⚠️ **DEPENDÊNCIA:** `db_manager.py` ainda contém toda a lógica de negócio

---

#### 4. **`db_manager.py`** (14.145 linhas) ⚠️ **MONOLÍTICO**
**Responsabilidade:** **IMPLEMENTA** queries SQL e lógica de negócio

- ✅ **O QUE FAZ:** Contém TODAS as funções que fazem queries reais
- ✅ **EXEMPLO:**
  ```python
  def listar_processos_registrados_hoje(categoria: Optional[str] = None, limit: int = 200):
      """
      Lista processos que tiveram DI ou DUIMP registrada HOJE.
      """
      conn = get_db_connection()
      cursor = conn.cursor()
      
      # Query SQL complexa aqui...
      query = """
          SELECT ...
          FROM processos_kanban p
          JOIN processo_documentos pd ON ...
          WHERE DATE(pd.atualizado_em) = DATE('now')
          AND pd.tipo_documento IN ('DI', 'DUIMP')
          ...
      """
      cursor.execute(query, ...)
      # Processa resultados...
      return processos
  ```
- ⚠️ **PROBLEMA:** Arquivo gigante com 104 funções misturadas
- ⚠️ **IMPACTO:** Difícil manter, testar, e pode causar regressões

---

## 🔄 **REFATORAÇÃO EM ANDAMENTO**

### **Estratégia: Extração Incremental com Wrappers**

**Princípio:** Extrair código do `db_manager.py` para módulos menores, mas **manter compatibilidade** via wrappers.

### **O Que Já Foi Extraído (16/01/2026)**

#### ✅ **1. Repositórios SQLite (CRUD simples)**
- `services/processos_sqlite_repository.py` → Wrapper em `db_manager.listar_processos`
- `services/processo_documentos_sqlite_repository.py` → Wrapper em `db_manager.listar_documentos_processo`

**Como funciona:**
```python
# services/processos_sqlite_repository.py
class ProcessosSqliteRepository:
    def listar_processos(self, ...):
        # Nova implementação limpa
        ...

# db_manager.py (mantém compatibilidade)
def listar_processos(...):
    # Wrapper que chama o repository
    from services.processos_sqlite_repository import ProcessosSqliteRepository
    repo = ProcessosSqliteRepository()
    return repo.listar_processos(...)
```

**✅ Vantagem:** Agents continuam funcionando sem mudança!

---

#### ✅ **2. Schemas (DDL/índices)**
- `services/contexto_sessao_schema.py`
- `services/processo_documentos_schema.py`
- `services/usuarios_chat_schema.py`
- `services/conversas_chat_schema.py`
- `services/categorias_processo_schema.py`
- `services/processos_kanban_historico_schema.py`
- `services/temporizador_monitoramento_schema.py`
- `services/sqlite_indexes_schema.py`
- `services/email_drafts_schema.py`
- `services/consultas_salvas_schema.py`
- `services/regras_aprendidas_schema.py`

**Como funciona:**
```python
# services/contexto_sessao_schema.py
def criar_tabela_contexto_sessao(conn):
    """Cria tabela contexto_sessao."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contexto_sessao (
            session_id TEXT PRIMARY KEY,
            ...
        )
    """)

# db_manager.py (mantém compatibilidade)
def init_db():
    from services.contexto_sessao_schema import criar_tabela_contexto_sessao
    criar_tabela_contexto_sessao(conn)
    # ... outras tabelas
```

**✅ Vantagem:** DDL isolado, mais fácil de manter!

---

### **O Que Ainda Precisa Ser Extraído**

#### 🔴 **PRIORIDADE ALTA: Funções de Consulta Complexas**

**Exemplos:**
- `listar_processos_registrados_hoje()` → Ainda no `db_manager.py`
- `obter_dis_em_analise()` → Ainda no `db_manager.py`
- `obter_duimps_em_analise()` → Ainda no `db_manager.py`
- `listar_processos_liberados_registro()` → Ainda no `db_manager.py`
- `listar_processos_por_categoria_e_situacao()` → Ainda no `db_manager.py`
- ... (mais ~90 funções)

**Plano de Migração:**
```
db_manager.py (14.145 linhas)
├── repositories/
│   ├── processo_repository.py        # Queries de processos
│   ├── documento_repository.py       # Queries de documentos (CE, DI, DUIMP, CCT)
│   ├── notificacao_repository.py     # Queries de notificações
│   ├── consulta_repository.py        # Queries bilhetadas
│   └── ...
├── cache/
│   ├── ce_cache.py                   # Cache de CE
│   ├── di_cache.py                   # Cache de DI
│   └── processo_cache.py             # Cache de processos
└── migrations/
    └── migrations.py                 # Migrações de schema
```

**Estratégia:**
1. Extrair função para `repositories/processo_repository.py`
2. Manter wrapper em `db_manager.py` que chama o repository
3. Agents continuam importando de `db_manager.py` (sem quebrar)
4. Gradualmente, agents podem migrar para importar direto do repository

---

## 🎯 **ESTRUTURA IDEAL: Como Fica Depois da Refatoração**

### **Estrutura de Diretórios (Ideal)**

**ANTES (atual):**
```
db_manager.py (14.145 linhas, 104 funções misturadas)
├── Funções de processos
├── Funções de documentos (CE, DI, DUIMP, CCT)
├── Funções de notificações
├── Funções de consultas bilhetadas
├── Funções de cache
├── Funções de migração
└── ... tudo misturado
```

**DEPOIS (ideal):**
```
services/
├── repositories/                    # ✅ NOVO: Funções de consulta organizadas
│   ├── processo_repository.py      # listar_processos_registrados_hoje, etc.
│   ├── documento_repository.py     # obter_dis_em_analise, obter_duimps_em_analise, etc.
│   ├── notificacao_repository.py  # Funções de notificações
│   └── consulta_repository.py     # Funções de consultas bilhetadas
├── cache/                          # ✅ NOVO: Lógica de cache isolada
│   ├── ce_cache.py
│   ├── di_cache.py
│   └── processo_cache.py
├── migrations/                     # ✅ NOVO: Migrações de schema
│   └── migrations.py
└── agents/                         # ✅ JÁ EXISTE: Handlers das tools
    ├── processo_agent.py
    ├── duimp_agent.py
    └── ...

db_manager.py (muito menor, só wrappers)
└── Wrappers que chamam os repositories (compatibilidade)
```

**✅ Vantagens:**
- Cada arquivo tem uma responsabilidade clara
- Mais fácil de encontrar e modificar código
- Mais fácil de testar (testes isolados por módulo)
- Menos risco de regressões (mudanças isoladas)

---

### **Fluxo Futuro (Ideal)**

```
1. Usuário pergunta: "quais DMD foram registrados?"
   ↓
2. IA decide chamar tool: `listar_processos_registrados_hoje`
   ↓
3. tool_definitions.py → Define o SCHEMA da tool (sem mudança)
   ↓
4. tool_router.py → Mapeia tool_name → agent_name (sem mudança)
   ↓
5. ProcessoAgent.execute() → Recebe a tool e chama handler (sem mudança)
   ↓
6. ProcessoAgent._listar_registrados_hoje() → Handler (sem mudança)
   ↓
7. ProcessoRepository.listar_registrados_hoje() → ✅ NOVO: Repository limpo
   ↓
8. Retorna resultado formatado para o usuário
```

### **Mudanças nos Agents (Futuro)**

**ANTES (atual):**
```python
# services/agents/processo_agent.py
def _listar_registrados_hoje(self, arguments, context):
    from db_manager import listar_processos_registrados_hoje  # ⚠️ Monolítico
    processos = listar_processos_registrados_hoje(...)
    ...
```

**DEPOIS (futuro):**
```python
# services/agents/processo_agent.py
def _listar_registrados_hoje(self, arguments, context):
    from services.repositories.processo_repository import ProcessoRepository  # ✅ Limpo
    repo = ProcessoRepository()
    processos = repo.listar_registrados_hoje(...)
    ...
```

**OU (compatibilidade mantida):**
```python
# services/agents/processo_agent.py
def _listar_registrados_hoje(self, arguments, context):
    from db_manager import listar_processos_registrados_hoje  # ✅ Ainda funciona (wrapper)
    processos = listar_processos_registrados_hoje(...)
    ...
```

---

## 📋 **RESUMO: O QUE MUDA E O QUE NÃO MUDA**

### ✅ **NÃO MUDA (Estável)**

1. **`tool_definitions.py`**
   - Continua definindo schemas de tools
   - Não precisa mudar durante a refatoração

2. **`tool_router.py`**
   - Continua mapeando tool_name → agent_name
   - Não precisa mudar durante a refatoração

3. **Agents (estrutura)**
   - Continuam implementando handlers
   - Podem continuar importando de `db_manager.py` (wrappers mantêm compatibilidade)

### 🔄 **MUDA (Refatoração)**

1. **`db_manager.py`**
   - **ANTES:** 14.145 linhas, 104 funções misturadas
   - **DEPOIS:** Arquivo menor, só com wrappers e inicialização
   - **BENEFÍCIO:** Mais fácil de manter, testar, e evitar regressões

2. **Novos Módulos**
   - `repositories/` → Queries SQL organizadas por domínio
   - `cache/` → Lógica de cache isolada
   - `migrations/` → Migrações de schema isoladas

3. **Agents (opcional, futuro)**
   - Podem migrar gradualmente para importar direto dos repositories
   - Mas não é obrigatório (wrappers mantêm compatibilidade)

---

## 🚨 **IMPORTANTE: Compatibilidade Garantida**

**✅ Regra de Ouro da Refatoração:**

> **Nunca quebrar código existente durante a refatoração.**

**Como garantir:**
1. Extrair função para novo módulo
2. Criar wrapper em `db_manager.py` que chama o novo módulo
3. Agents continuam importando de `db_manager.py` (sem mudança)
4. Testar que tudo continua funcionando
5. Gradualmente, agents podem migrar para importar direto (opcional)

**Exemplo prático:**
```python
# ✅ PASSO 1: Extrair para repository
# services/repositories/processo_repository.py
class ProcessoRepository:
    def listar_registrados_hoje(self, categoria, limit):
        # Nova implementação limpa
        ...

# ✅ PASSO 2: Criar wrapper em db_manager.py
# db_manager.py
def listar_processos_registrados_hoje(categoria=None, limit=200):
    """Wrapper para manter compatibilidade."""
    from services.repositories.processo_repository import ProcessoRepository
    repo = ProcessoRepository()
    return repo.listar_registrados_hoje(categoria, limit)

# ✅ PASSO 3: Agents continuam funcionando sem mudança
# services/agents/processo_agent.py
from db_manager import listar_processos_registrados_hoje  # ✅ Ainda funciona!
```

---

## 📚 **DOCUMENTAÇÃO RELACIONADA**

- `PROMPT_AMANHA.md` - Status da refatoração em andamento
- `docs/ANALISE_REFATORACAO_FINAL.md` - Análise completa dos arquivos monolíticos
- `AGENTS.md` - Guia de como criar/atualizar agents
- `README.md` - Visão geral do projeto

---

**Última atualização:** 17/01/2026
