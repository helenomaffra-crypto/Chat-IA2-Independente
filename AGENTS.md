# AGENTS.md - V1

Este documento fornece instruções estruturadas para agentes de IA trabalharem com o projeto **Chat IA Independente V1** - um sistema de chat conversacional com IA especializado em DUIMP (Declaração Única de Importação) e processos de importação no Brasil.

**⚠️ IMPORTANTE:** Este é o **AGENTS.md da V1**. A V2 foi migrada e separada em 25-26/01/2026.

**Localização V1:** `/Users/helenomaffra/Chat-IA2-Independente/` (este diretório)  
**Localização V2:** `/Volumes/KINGSTON/PYTHON/v2_langchain`  
**Porta V1:** `5001`  
**Porta V2:** `5002`

**Para trabalhar na V2:** Use `/Volumes/KINGSTON/PYTHON/v2_langchain/AGENTS.md` e `/Volumes/KINGSTON/PYTHON/v2_langchain/CONTINUAR_TRABALHO.md`.

---

## 🔄 Separação V1/V2

| Aspecto | V1 (este diretório) | V2 (separada) |
|---------|---------------------|---------------|
| **Localização** | `/Users/helenomaffra/Chat-IA2-Independente/` | `/Volumes/KINGSTON/PYTHON/v2_langchain` |
| **Porta** | `5001` | `5002` |
| **Framework** | Flask + ToolRouter + Agents customizados | LangChain + LangGraph |
| **Docker** | ✅ Sim (docker-compose.yml) | ❌ Não (roda localmente) |
| **Documentação** | `README.md`, `AGENTS.md` (este arquivo) | `README.md`, `AGENTS.md`, `PROMPT_V2.md`, `CONTINUAR_TRABALHO.md` |

**⚠️ IMPORTANTE:** Este `AGENTS.md` é **específico para a V1**. Não confundir com a V2 que está em outro diretório.

---

## 📋 Visão Geral do Projeto

**Chat IA Independente** é uma aplicação Flask que fornece:
- Interface de chat conversacional com IA (GPT-4o, GPT-4o-mini)
- Integração com SQL Server (processos históricos e ativos)
- Integração com APIs oficiais (Portal Único, Integra Comex, Serpro)
- Sistema de tool calling com LLMs
- Gestão de processos de importação (ALH, VDM, MSS, BND, DMD, GYM, SLL, MV5)
- Criação automática de DUIMPs
- Consulta de documentos aduaneiros (CE, CCT, DI, DUIMP)
- Sugestão inteligente de NCM (Nomenclatura Comum do Mercosul)
- Sistema de email personalizado
- Notificações agendadas

**Tecnologias Principais:**
- Python 3.9+
- Flask 3.0+
- SQLite (cache local)
- SQL Server (dados de produção)
- OpenAI API / Anthropic API
- Node.js adapter (opcional, para SQL Server)

---

## 🚨 REGRA CRÍTICA: VALIDAÇÃO OBRIGATÓRIA APÓS QUALQUER EDIÇÃO — obrigatório para agentes

**⚠️ CRÍTICO:** **SEMPRE** validar código após editar qualquer arquivo Python. Erros de sintaxe, imports quebrados e variáveis inexistentes **NÃO SÃO ACEITÁVEIS** e causam falhas em produção.

**⚠️ NUNCA assuma que está correto sem executar estes testes!**

### ✅ Checklist Obrigatório (SEMPRE executar após editar código)

**1. Compilação de Sintaxe (OBRIGATÓRIO - PRIMEIRO PASSO):**
```bash
python3 -m py_compile <arquivo_editado>.py
```
**Se falhar:** Corrigir sintaxe ANTES de continuar. Não assuma que está correto.

**2. Teste de Import (OBRIGATÓRIO - SEGUNDO PASSO):**
```bash
python3 -c "from <modulo> import <classe/funcao>; print('✅ OK')"
```
**Se falhar:** Corrigir imports ANTES de continuar.

**3. Teste de Inicialização (se aplicável - TERCEIRO PASSO):**
```bash
python3 -c "from <modulo> import <classe>; obj = <classe>(); print('✅ OK')"
```
**Se falhar:** Corrigir inicialização ANTES de continuar.

### 📋 Exemplos Reais de Erros Evitados (26/01/2026)

- ❌ `NameError: name 'dv_contra_contra' is not defined` em `banco_sincronizacao_service.py:878`
  - **Causa:** Erro de digitação (`dv_contra_contra` em vez de `dv_conta_contra`)
  - **Impacto:** Sincronização de extratos falhava completamente
  - **Solução:** Corrigido para `dv_conta_contra` e validado com `py_compile`

- ❌ `SyntaxError: invalid syntax` em `tts_service.py:226`
  - **Causa:** Linhas coladas sem quebra (`return 0        if not...`)
  - **Impacto:** TTS não funcionava (import falhava)
  - **Solução:** Quebras de linha adicionadas e validado com `py_compile`

**Regra de ouro:** Se você editou um arquivo Python, **SEMPRE** rode `python3 -m py_compile <arquivo>.py` e teste os imports antes de finalizar. **NÃO PULE ESTA ETAPA.**

**Localização dos testes completos:** Ver seção "🧪 Testes" abaixo para lista completa de testes obrigatórios.

---

## ✅ REGRA DO PROJETO (ANTI-MONÓLITO) — obrigatório para agentes

**Problema recorrente:** arquivos “crescem sem controle” (`chat_service.py`, `db_manager.py`, `processo_agent.py`, `app.py`) e depois viram refatoração dolorosa.

**Regra:** qualquer mudança nova **deve evitar criar/expandir monólitos**. O padrão aqui é **crescer por módulos** (services/handlers/repositories), mantendo compatibilidade via wrappers quando necessário.

### Limites práticos (guardrails)

- **Não criar arquivo novo gigante**: se um arquivo novo passar de ~300–500 linhas, *pare e extraia* em submódulos por domínio.
- **Não adicionar >200 linhas líquidas em um arquivo “crítico”** (`services/chat_service.py`, `db_manager.py`, `services/agents/processo_agent.py`, `app.py`) em uma única mudança.
- **Preferir extração incremental**: 1 feature/1 handler por patch, com testes obrigatórios.
- **Separação por responsabilidade**:
  - **Agents**: só “router + validação leve”; lógica pesada vai para `services/*_service.py`.
  - **ChatService**: só orquestra fluxo (precheck → IA → tools → resposta); lógica de tool vai para `ToolExecutionService`/agents/handlers.
  - **app.py**: rotas devem ser separadas por domínio quando mexer (ex.: `routes/chat.py`, `routes/banco.py`, etc.) — evitar “mais endpoints no arquivo gigante”.
  - **db_manager.py**: sem “mais um helper gigante”; extrair para `services/*_schema.py` e `services/*_repository.py`.

### Checklist antes de finalizar mudança

- **Extração aplicada** quando a lógica começa a “engordar”.
- **Wrappers mantêm compatibilidade** (se for refactor).
- **Testes obrigatórios do AGENTS.md rodados** (imports/compile/init).
- **Docs atualizadas** (README/PROMPT_AMANHA) quando mudar arquitetura ou fallback.

## ✅ FLUXO OBRIGATÓRIO — Auditoria de fontes e mudanças de query (SELECT / JOIN / WHERE)

**Sempre que mexer em qualquer query (SELECT), filtros, JOINs, fonte de dados, ou “onde buscar X”: siga este fluxo.**  
Baseado no plano `auditoria_de_fontes_e_fluxo_de_dados_c0cf6520.plan.md` (Cursor).

### Regras de ouro (fonte → cache → persistência)

- **Leitura rápida operacional** (status/ETA/canal): **priorizar SQLite** (snapshot Kanban + ShipsGo) quando existir.
- **Enriquecimento e persistência durável** (documentos, histórico, valores, impostos): **`SQL Server mAIke_assistente`**.
- **Legado (`Make`)**: **só como fallback controlado** (migração/auto-heal) — nunca “default silencioso”.

### Checklist obrigatório antes de alterar query

- **Definir domínio e “fonte da verdade”**: é dado operacional (cache) ou durável (SQL)?
- **Checar política central de DB**: usar `services/db_policy_service.py` (primário vs legado) e **evitar hardcode de `Make`**.
- **Se usar fallback para `Make`**:
  - **logar explicitamente** (quem chamou, por quê, processo/escopo) — nada de fallback invisível.
  - **auto-heal quando fizer sentido**: trazer do legado e persistir no `mAIke_assistente` para próximas consultas.
- **Validar 3 cenários** (mínimo):
  - (1) dado só no snapshot (SQLite)
  - (2) dado já no `mAIke_assistente`
  - (3) dado só no `Make` (fallback/migração)
- **Rodar testes obrigatórios do projeto** (imports/compile/init) antes de assumir que está correto.

### Anti-regressão (obrigatório)

- **Nunca trocar a fonte sem atualizar o fluxo completo** (ex.: query muda e a persistência/auto-heal fica para trás).
- **Quando houver divergência** (snapshot vs SQL), preferir: “status atual (snapshot)” + “histórico/detalhe (SQL)” e registrar alerta/log.
## ✅ MIGRAÇÃO DE DOCUMENTOS HISTÓRICOS — População de DOCUMENTO_ADUANEIRO

**Contexto:** O sistema só popula `mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO` automaticamente quando:
1. Consulta documento via API diretamente
2. Sincroniza processo do Kanban (extrai documentos do JSON)

**Problema:** Processos antigos (ex: 2025) que não estão no Kanban atual não têm seus documentos gravados em `DOCUMENTO_ADUANEIRO`, causando:
- Queries "o que registramos" retornando resultados incompletos
- Dependência de queries híbridas (Serpro/Duimp DB) que são mais lentas

**Solução:** Script de migração `scripts/migrar_documentos_2025_para_documento_aduaneiro.py`

### Quando Executar Migração

- ✅ **Após identificar lacunas** em queries "o que registramos" para períodos passados
- ✅ **Antes de depender apenas de DOCUMENTO_ADUANEIRO** para relatórios históricos
- ✅ **Quando sistema está em desenvolvimento** e rotinas novas não existiam antes

### Como Executar

```bash
# Teste primeiro (dry-run)
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --dry-run --limit 100

# Migração completa de 2025
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py

# Outro ano
python3 scripts/migrar_documentos_2025_para_documento_aduaneiro.py --ano 2024
```

### Estratégia de Dados

- **DI:** Busca de `Serpro.dbo` (tabelas históricas) → constrói payload mínimo → grava via `DocumentoHistoricoService`
- **DUIMP:** Busca de `Duimp.dbo` → constrói payload mínimo → grava via `DocumentoHistoricoService`
- **Idempotência:** Verifica se documento já existe antes de gravar (pode executar múltiplas vezes)

### Validação

Após migração, validar:
1. Contagens em `DOCUMENTO_ADUANEIRO` vs fonte original (Serpro/Duimp DB)
2. Query "o que registramos" retorna resultados completos
3. `data_registro` está preenchido (necessário para queries por período)

**Documentação completa:** `docs/MIGRACAO_DOCUMENTOS_2025.md`


## 🏗️ Arquitetura do Projeto

### Estrutura de Diretórios

```
Chat-IA-Independente/
├── app.py                          # Aplicação Flask principal
├── ai_service.py                   # Serviço de IA (OpenAI/Anthropic)
├── db_manager.py                   # Gerenciador de banco SQLite
├── services/
│   ├── agents/                    # Agentes especializados
│   │   ├── base_agent.py         # Classe base para todos os agents
│   │   ├── processo_agent.py     # Operações com processos
│   │   ├── ce_agent.py           # Conhecimentos de Embarque
│   │   ├── cct_agent.py          # Conhecimentos de Carga Aérea
│   │   ├── di_agent.py           # Declarações de Importação
│   │   └── duimp_agent.py        # DUIMPs
│   ├── chat_service.py            # Serviço principal de chat
│   ├── prompt_builder.py          # Construtor de prompts
│   ├── tool_definitions.py        # Definições de tools para IA
│   ├── tool_router.py             # Roteador de tools
│   ├── tool_executor.py           # Executor de tools
│   ├── precheck_service.py        # Pré-checks antes da IA
│   ├── relatorio_fob_service.py  # ✅ NOVO (23/12/2025): Relatório de importações normalizado por FOB
│   ├── relatorio_averbacoes_service.py # ✅ NOVO (16/12/2025): Relatório de averbações
│   ├── message_intent_service.py  # ✅ NOVO (23/12/2025): Detecção de intenções de mensagens e comandos de interface
│   └── [outros serviços...]
├── utils/                          # Utilitários
│   ├── sql_server_adapter.py     # Adaptador SQL Server
│   ├── portal_proxy.py           # Proxy Portal Único
│   └── integracomex_proxy.py     # Proxy Integra Comex
├── templates/                      # Templates HTML
└── docs/                          # Documentação

```

### Arquitetura de Agentes

O projeto usa uma arquitetura baseada em **agents especializados**:

1. **BaseAgent** (`services/agents/base_agent.py`): Classe abstrata base
   - Todos os agents herdam desta classe
   - Implementa `execute(tool_name, arguments, context)`
   - Fornece logging e validação de argumentos

2. **Agents Especializados:**
   - **ProcessoAgent**: Operações com processos de importação
   - **CeAgent**: Conhecimentos de Embarque marítimos
   - **CctAgent**: Conhecimentos de Carga Aérea
   - **DiAgent**: Declarações de Importação
   - **DuimpAgent**: DUIMPs (Declaração Única de Importação)
   - **BancoBrasilAgent**: ✅ NOVO (06/01/2026): Operações bancárias do Banco do Brasil (extratos e pagamentos)
   - **SantanderAgent**: ✅ NOVO (06/01/2026): Operações bancárias do Santander (extratos e pagamentos)
   - **LegislacaoAgent**: ✅ NOVO (05/01/2026): Operações relacionadas a legislação (busca semântica e tradicional)
   - **CalculoAgent**: ✅ NOVO (06/01/2026): Cálculos de impostos e outros cálculos complexos com Code Interpreter

3. **Tool Router** (`services/tool_router.py`):
   - Roteia chamadas de tools para o agent apropriado
   - Mapeamento: `tool_name → agent_name`

4. **Tool Executor** (`services/tool_executor.py`):
   - Executa tools através do router
   - Gerencia contexto e resultados

---

## 🚀 Setup do Ambiente de Desenvolvimento

### Pré-requisitos

1. **Python 3.9 ou superior**
   ```bash
   python3 --version  # Deve ser >= 3.9
   ```

2. **Node.js** (opcional, apenas se usar Node.js adapter para SQL Server)
   ```bash
   node --version
   ```

3. **ODBC Driver 17 ou 18 for SQL Server** (se usar pyodbc)
   - Windows: https://aka.ms/downloadmsodbcsql
   - Linux: https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server
   - macOS: `brew install msodbcsql18`

4. **OpenSSL** (para autenticação mTLS)
   - Windows: https://slproweb.com/products/Win32OpenSSL.html
   - Linux: `sudo apt-get install openssl`
   - macOS: `brew install openssl`

### Instalação

1. **Clonar o repositório** (se aplicável)

2. **Criar ambiente virtual** (recomendado):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # ou
   venv\Scripts\activate  # Windows
   ```

3. **Instalar dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variáveis de ambiente**:
   - Copiar `.env.example` para `.env`
   - Preencher variáveis necessárias (ver seção "Configuração")

### Variáveis de Ambiente Essenciais

Criar arquivo `.env` na raiz do projeto:

```env
# IA
DUIMP_AI_ENABLED=true
DUIMP_AI_PROVIDER=openai  # ou anthropic
DUIMP_AI_API_KEY=sk-...
OPENAI_MODEL_INTELIGENTE=gpt-4o
OPENAI_MODEL_ANALITICO=gpt-4o-mini

# SQL Server
SQL_SERVER_HOST=...
SQL_SERVER_DATABASE=...
SQL_SERVER_USER=...
SQL_SERVER_PASSWORD=...
SQL_SERVER_USE_NODE_ADAPTER=false  # true para usar Node.js adapter

# Email
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=...
EMAIL_PASSWORD=...

# Portal Único / Integra Comex
PORTAL_UNICO_TOKEN=...
INTEGRACOMEX_TOKEN=...
```

---

## 🛠️ Comandos de Build e Teste

### Executar Aplicação

**Desenvolvimento:**
```bash
python app.py
```

A aplicação inicia na porta **5001** por padrão (configurável via `PORT` no `.env`).

**Produção (Gunicorn - Linux):**
```bash
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

**Produção (Waitress - Multiplataforma):**
```bash
waitress-serve --host=0.0.0.0 --port=5001 app:app
```

### Testar Endpoints

**Chat IA:**
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"mensagem": "como estão os mv5?", "session_id": "test"}'
```

**Health Check:**
```bash
curl http://localhost:5001/api/health
```

### Testes de Banco de Dados

**SQLite (cache local):**
```bash
sqlite3 chat_ia.db
```

**SQL Server:**
```bash
# Testar conexão via Python
python -c "from utils.sql_server_adapter import get_sql_adapter; adapter = get_sql_adapter(); print(adapter.test_connection())"
```

---

## 📝 Convenções de Código

### Estrutura de Agents

Todos os agents devem:
1. Herdar de `BaseAgent`
2. Implementar `execute(tool_name, arguments, context)`
3. Retornar dict com estrutura:
   ```python
   {
       'sucesso': bool,
       'resposta': str,  # Mensagem para o usuário
       'erro': str,      # Se houver erro
       'dados': Any      # Dados adicionais (opcional)
   }
   ```

**Exemplo:**
```python
from services.agents.base_agent import BaseAgent

class MeuAgent(BaseAgent):
    def execute(self, tool_name: str, arguments: Dict[str, Any], 
                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        handlers = {
            'minha_tool': self._minha_tool,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada',
                'resposta': f'❌ Tool "{tool_name}" não disponível.'
            }
        try:
            return handler(arguments, context)
        except Exception as e:
            logger.error(f'Erro ao executar {tool_name}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro: {str(e)}'
            }
```

### Nomenclatura

- **Classes**: PascalCase (`ProcessoAgent`, `BaseAgent`)
- **Funções/Métodos**: snake_case (`listar_processos`, `_consultar_ce`)
- **Variáveis**: snake_case (`processo_referencia`, `numero_ce`)
- **Constantes**: UPPER_SNAKE_CASE (`SQL_SERVER_HOST`, `DUIMP_AI_ENABLED`)

### Logging

Sempre usar o logger do módulo:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("✅ Operação realizada com sucesso")
logger.warning("⚠️ Aviso importante")
logger.error("❌ Erro ocorreu", exc_info=True)
```

### Tratamento de Erros

- Sempre capturar exceções específicas
- Retornar dict com `sucesso: False` e mensagem clara
- Logar erros com `exc_info=True` para stack trace completo

### Documentação

- Docstrings em todas as classes e métodos públicos
- Usar formato Google Style:
  ```python
  def minha_funcao(arg1: str, arg2: int) -> Dict[str, Any]:
      """
      Descrição breve.
      
      Args:
          arg1: Descrição do arg1
          arg2: Descrição do arg2
      
      Returns:
          Dict com resultado contendo:
          - sucesso: bool
          - resposta: str
      """
  ```

---

## 🔧 Estrutura de Tools

### Adicionar Nova Tool

1. **Definir tool em `services/tool_definitions.py`**:
   ```python
   {
       "type": "function",
       "function": {
           "name": "minha_nova_tool",
           "description": "Descrição clara do que a tool faz...",
           "parameters": {
               "type": "object",
               "properties": {
                   "param1": {
                       "type": "string",
                       "description": "Descrição do parâmetro"
                   }
               },
               "required": ["param1"]
           }
       }
   }
   ```

2. **Mapear tool no `services/tool_router.py`**:
   ```python
   tool_to_agent = {
       'minha_nova_tool': 'processo',  # ou outro agent
       # ...
   }
   ```

3. **Implementar handler no agent apropriado**:
   ```python
   def _minha_nova_tool(self, arguments: Dict[str, Any], 
                        context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
       # Implementação
       return {
           'sucesso': True,
           'resposta': 'Resultado da operação'
       }
   ```

4. **Adicionar ao handler mapping no `execute()` do agent**:
   ```python
   handlers = {
       'minha_nova_tool': self._minha_nova_tool,
       # ...
   }
   ```

---

## 🏦 Serviços de Banco (NOVO - 07/01/2026, ATUALIZADO 08/01/2026)

### BancoSincronizacaoService (`services/banco_sincronizacao_service.py`)

**Responsabilidade:** Sincronização de extratos bancários (Banco do Brasil e Santander) para SQL Server.

**Funcionalidades Principais:**
- ✅ Sincronização de extratos do Banco do Brasil
- ✅ **Sincronização de extratos do Santander** (08/01/2026)
- ✅ Detecção automática de duplicatas usando hash SHA-256
- ✅ Detecção automática de processos nas descrições de transações
- ✅ Suporte a múltiplos formatos de data do Santander (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY)
- ✅ Descrição completa de lançamentos (transactionName + historicComplement) para Santander
- ✅ Detecção automática de conta Santander quando não especificada

**Métodos Principais:**
- `sincronizar_extrato(banco, agencia, conta, data_inicio, data_fim, dias_retroativos)`: Sincroniza extrato completo
- `importar_lancamento(lancamento, agencia, conta, banco)`: Importa um único lançamento
- `importar_lancamentos(lancamentos, agencia, conta, banco)`: Importa múltiplos lançamentos
- `verificar_duplicata(hash_lancamento)`: Verifica se lançamento já existe
- `gerar_hash_lancamento(lancamento, agencia, conta, banco)`: Gera hash único para detecção de duplicatas
- `detectar_processo_por_descricao(descricao)`: Detecta referência de processo na descrição

**Tratamento de Erros:**
- Erros de timeout são tratados com mensagens claras ao usuário
- Orientação: "Sincronize novamente quando o SQL Server estiver acessível"
- Duplicatas são detectadas automaticamente (não há problema em sincronizar novamente)

---

### BancoConcilacaoService (`services/banco_concilacao_service.py`)

**Responsabilidade:** Conciliação bancária e classificação de lançamentos.

**Funcionalidades Principais:**
- ✅ Listagem de lançamentos não classificados
- ✅ Listagem de lançamentos classificados (para edição)
- ✅ Classificação de lançamentos vinculando a tipos de despesa e processos
- ✅ Suporte a múltiplas classificações por lançamento (split)
- ✅ Distribuição de impostos de importação (II, IPI, PIS, COFINS, etc.)
- ✅ Validação de valores (soma não pode exceder valor total)
- ✅ Detecção automática de lançamentos de impostos de importação

**Métodos Principais:**
- `listar_lancamentos_nao_classificados(limite)`: Lista lançamentos sem classificação
- `listar_lancamentos_classificados(limite)`: Lista lançamentos já classificados
- `classificar_lancamento(id_movimentacao, classificacoes, distribuicao_impostos)`: Classifica um lançamento
- `consultar_despesas_processo(processo_referencia)`: Consulta despesas de um processo
- `obter_lancamento_com_classificacoes(id_movimentacao)`: Obtém lançamento com todas as classificações
- `_eh_lancamento_impostos(descricao, processo_vinculado)`: Detecta se lançamento é de impostos

**✅ NOVO (08/01/2026):** Descrição completa de lançamentos (transactionName + historicComplement) aparece na lista e no modal.

---

## 💳 APIs de Pagamentos (NOVO - 13/01/2026)

### Banco do Brasil - API de Pagamentos em Lote

**Responsabilidade:** Pagamento de boletos, PIX e TED em lote via Banco do Brasil.

**Funcionalidades Principais:**
- ✅ Pagamento em lote (múltiplos boletos/PIX/TED de uma vez)
- ✅ Consulta de status de lote
- ✅ Listagem de lotes de pagamentos
- ✅ Suporte a BOLETO, PIX e TED

**Tools Disponíveis:**
- `iniciar_pagamento_lote_bb`: Inicia pagamento em lote
  - Parâmetros: `agencia`, `conta`, `pagamentos[]` (tipo, valor, dados específicos)
  - Tipos suportados: `BOLETO`, `PIX`, `TED`
- `consultar_lote_pagamentos_bb`: Consulta status de um lote específico
- `listar_lotes_pagamentos_bb`: Lista todos os lotes (com filtros opcionais)

**Arquivos Relacionados:**
- `services/agents/banco_brasil_agent.py` - Agent que processa as tools
- `utils/banco_brasil_api.py` - Cliente API do Banco do Brasil
- `docs/API_DOCUMENTATION.md` - Documentação completa da API

**Autenticação:**
- OAuth 2.0 Client Credentials (JWT token)
- Requer certificado mTLS para API de Pagamentos (diferente de Extratos)
- Base URL: `https://api-pagamentos.bb.com.br/pagamentos/v1` (verificar no portal)

**⚠️ Importante:**
- Pagamentos são ações sensíveis e requerem confirmação (pending intents)
- Sistema cria preview antes de executar
- Usuário deve confirmar explicitamente antes do pagamento

---

### Santander - API de Accounts and Taxes

**Responsabilidade:** Pagamentos via Santander (Boletos, PIX, TED, Impostos).

**Funcionalidades Principais:**
- ✅ Bank Slip Payments (Boletos)
- ✅ Barcode Payments (Códigos de Barras)
- ✅ PIX Payments (DICT, QR Code, Beneficiário)
- ✅ Vehicle Taxes Payments (IPVA)
- ✅ Taxes by Fields Payments (GARE ICMS, GARE ITCMD, DARF, GPS)

**Tools Disponíveis:**
- `listar_workspaces_santander`: Lista workspaces disponíveis
- `criar_workspace_santander`: Cria novo workspace (necessário para pagamentos)
- Tools de pagamento específicas (ver `docs/API_DOCUMENTATION.md`)

**Arquivos Relacionados:**
- `services/agents/santander_agent.py` - Agent que processa as tools
- `utils/santander_api.py` - Cliente API do Santander
- `docs/API_DOCUMENTATION.md` - Documentação completa

**Autenticação:**
- OAuth2 mTLS (certificado ICP-Brasil tipo A1)
- Requer certificado `.pem` e `.key`

**⚠️ Importante:**
- Pagamentos são ações sensíveis e requerem confirmação (pending intents)
- Workspace é necessário para fazer pagamentos
- Sistema cria preview antes de executar

---

## 🗄️ Banco de Dados

### SQLite (Cache Local)

**Localização:** `chat_ia.db` (criado automaticamente)

**Tabelas Principais:**
- `conversas_chat`: Histórico de conversas
- `classif_cache`: Cache de NCMs
- `processos_kanban`: Cache de processos ativos
- `processo_documentos`: Documentos vinculados a processos

### SQL Server (Produção - Banco mAIke_assistente)

**Tabelas de Banco (NOVO - 07/01/2026):**
- `MOVIMENTACAO_BANCARIA`: Lançamentos bancários sincronizados (Banco do Brasil e Santander)
- `TIPO_DESPESA`: Catálogo de tipos de despesa (23 tipos pré-cadastrados)
- `LANCAMENTO_TIPO_DESPESA`: Relacionamento N:N (lançamento ↔ despesa ↔ processo)
- `IMPOSTO_IMPORTACAO`: ✅ NOVO (07/01/2026): Impostos de importação distribuídos por lançamento
- `VALOR_MERCADORIA`: ✅ NOVO (07/01/2026): Valores de mercadoria (VMLE, VMLD, FOB, CIF)

**Inicialização:**
```python
from db_manager import init_db
init_db()
```

### SQL Server (Produção)

**Configuração via `.env`:**
- `SQL_SERVER_HOST`
- `SQL_SERVER_DATABASE`
- `SQL_SERVER_USER`
- `SQL_SERVER_PASSWORD`

**Uso:**
```python
from utils.sql_server_adapter import get_sql_adapter
adapter = get_sql_adapter()
result = adapter.execute_query("SELECT * FROM ...")
```

---

## 🔌 APIs e Integrações

### Portal Único (Siscomex)

**Autenticação:** Token via `PORTAL_UNICO_TOKEN`

**Uso:**
```python
from utils.portal_proxy import call_portal
status, data = call_portal('/api/endpoint', method='GET')
```

### Integra Comex

**Autenticação:** Token via `INTEGRACOMEX_TOKEN` (mTLS)

**Uso:**
```python
from utils.integracomex_proxy import call_integracomex
status, data = call_integracomex('/api/endpoint', method='GET')
```

### OpenAI / Anthropic

**Configuração:** Via `DUIMP_AI_PROVIDER` e `DUIMP_AI_API_KEY`

**Uso:**
```python
from ai_service import get_ai_service
ai_service = get_ai_service()
response = ai_service.chat_completion(messages=[...])
```

---

## 🧪 Testes

### ⚠️ TESTES OBRIGATÓRIOS ANTES DE ASSUMIR QUE ESTÁ CORRETO

**CRÍTICO:** NUNCA assuma que o código está correto sem testar. Sempre execute os testes abaixo antes de considerar uma mudança completa.

#### 1. Teste de Imports Básicos

**SEMPRE teste se todos os imports funcionam antes de fazer mudanças:**

```bash
# Testar imports críticos
python3 -c "import sys; sys.path.insert(0, '.'); from services.tool_definitions import get_available_tools; print('✅ tool_definitions OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.tool_router import ToolRouter; print('✅ tool_router OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.precheck_service import PrecheckService; print('✅ precheck_service OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.prompt_builder import PromptBuilder; print('✅ prompt_builder OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.tool_executor import ToolExecutor; print('✅ tool_executor OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.saved_queries_service import ensure_consultas_padrao; print('✅ saved_queries_service OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.learned_rules_service import buscar_regras_aprendidas; print('✅ learned_rules_service OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.context_service import buscar_contexto_sessao; print('✅ context_service OK')"
```

#### 2. Teste de Agents

**SEMPRE teste se todos os agents podem ser importados:**

```bash
python3 -c "import sys; sys.path.insert(0, '.'); from services.agents.base_agent import BaseAgent; print('✅ base_agent OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.agents.processo_agent import ProcessoAgent; print('✅ processo_agent OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.agents.duimp_agent import DuimpAgent; print('✅ duimp_agent OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.agents.ce_agent import CeAgent; print('✅ ce_agent OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.agents.di_agent import DiAgent; print('✅ di_agent OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from services.agents.cct_agent import CctAgent; print('✅ cct_agent OK')"
```

#### 3. Teste de Serviços Core

**SEMPRE teste se os serviços principais funcionam:**

```bash
python3 -c "import sys; sys.path.insert(0, '.'); from ai_service import get_ai_service; print('✅ ai_service OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from db_manager import init_db; print('✅ db_manager OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from utils.sql_server_adapter import get_sql_adapter; print('✅ sql_server_adapter OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from utils.portal_proxy import call_portal; print('✅ portal_proxy OK')"
python3 -c "import sys; sys.path.insert(0, '.'); from utils.integracomex_proxy import call_integracomex; print('✅ integracomex_proxy OK')"
```

#### 4. Teste de Compilação

**SEMPRE teste se os arquivos Python compilam sem erros de sintaxe:**

```bash
python3 -m py_compile app.py services/chat_service.py db_manager.py ai_service.py
```

Se houver erros, corrija ANTES de continuar.

#### 5. Teste de Inicialização Completa

**SEMPRE teste se o ChatService pode ser inicializado:**

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from app import app, get_chat_service
    print('✅ app.py importado')
    cs = get_chat_service()
    print('✅ ChatService inicializado')
    assert hasattr(cs, 'processar_mensagem'), 'processar_mensagem não existe'
    print('✅ processar_mensagem existe')
    assert hasattr(cs, 'tool_router'), 'tool_router não existe'
    print('✅ tool_router existe')
    assert hasattr(cs, 'precheck_service'), 'precheck_service não existe'
    print('✅ precheck_service existe')
    print('\\n✅✅✅ TODOS OS TESTES PASSARAM - SISTEMA OK!')
except Exception as e:
    print(f'❌ ERRO: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
```

#### 6. Teste de Node.js Dependencies

**Se usar Node.js adapter, SEMPRE verifique se as dependências estão instaladas:**

```bash
# Verificar se node_modules existe
test -d node_modules && echo "✅ node_modules existe" || echo "❌ node_modules não existe"

# Verificar se mssql está instalado
test -f node_modules/mssql/package.json && echo "✅ mssql instalado" || echo "❌ mssql não instalado"

# Se não estiver instalado, instalar:
npm install
```

#### 7. Teste de Import do app.py

**SEMPRE teste se o app.py pode ser importado sem erros:**

```bash
python3 -c "import sys; sys.path.insert(0, '.'); import app; print('✅ app.py importado com sucesso')" 2>&1 | head -50
```

### Checklist de Testes Obrigatórios

**ANTES de considerar qualquer mudança completa, execute TODOS estes testes:**

- [ ] ✅ Imports básicos funcionam (tool_definitions, tool_router, precheck_service, etc.)
- [ ] ✅ Todos os agents podem ser importados (base_agent, processo_agent, duimp_agent, etc.)
- [ ] ✅ Serviços core funcionam (ai_service, db_manager, sql_server_adapter, etc.)
- [ ] ✅ Arquivos Python compilam sem erros de sintaxe
- [ ] ✅ ChatService pode ser inicializado completamente
- [ ] ✅ Node.js dependencies estão instaladas (se usar Node.js adapter)
- [ ] ✅ app.py pode ser importado sem erros

**⚠️ NUNCA assuma que está correto sem executar estes testes!**

### Estrutura de Testes

```
tests/
├── test_agents/
│   ├── test_processo_agent.py
│   └── test_ce_agent.py
├── test_services/
│   └── test_chat_service.py
└── test_utils/
    └── test_extractors.py
```

### Executar Testes

```bash
# Todos os testes
python -m pytest tests/

# Teste específico
python -m pytest tests/test_agents/test_processo_agent.py

# Com cobertura
python -m pytest --cov=services tests/
```

---

## 📦 Pull Request Guidelines

### Formato de Commits

**Título:** `[<tipo>] <descrição breve>`

**Tipos:**
- `[feat]`: Nova funcionalidade
- `[fix]`: Correção de bug
- `[refactor]`: Refatoração
- `[docs]`: Documentação
- `[test]`: Testes
- `[chore]`: Manutenção

**Exemplos:**
```
[feat] Adiciona suporte a consulta de CCT
[fix] Corrige detecção de confirmação de email
[refactor] Extrai lógica de pendências para PendenciaService
```

### Checklist de PR

- [ ] Código segue convenções do projeto
- [ ] Testes passam (`pytest tests/`)
- [ ] Documentação atualizada (se necessário)
- [ ] Logging adequado adicionado
- [ ] Tratamento de erros implementado
- [ ] Variáveis de ambiente documentadas (se novas)

### Branch Naming

- `feature/nome-da-feature`
- `fix/nome-do-fix`
- `refactor/nome-do-refactor`

---

## 🎯 Padrões Específicos do Projeto

### Processamento de Mensagens

1. **Detecção de Comandos de Interface** (`MessageIntentService`): Detecta comandos para abrir interfaces (menu, conciliação, etc.) **ANTES** de qualquer processamento
2. **Precheck** (`PrecheckService`): Detecta intenções antes da IA
3. **Chat Service**: Processa mensagem com IA
4. **Tool Router**: Roteia tools para agents
5. **Tool Executor**: Executa tools
6. **Response Formatter**: Formata resposta final

#### Sistema de Comandos de Interface (NOVO - 07/01/2026)

O sistema detecta comandos de voz/texto para abrir interfaces específicas **antes** de processar pela IA, permitindo respostas instantâneas:

**Comandos disponíveis:**
- `"maike menu"` → Abre o menu drawer lateral
- `"maike quero conciliar banco"` → Abre modal de conciliação bancária
- `"maike quero sincronizar banco"` → Abre modal de sincronização de extratos
- `"maike quero importar legislação"` → Abre modal de importação de legislação
- `"maike configurações"` → Abre modal de configurações

**Implementação:**
- `MessageIntentService.detectar_comando_interface()`: Detecta comandos usando regex patterns
- `ChatService.processar_mensagem()` e `ChatService.processar_mensagem_stream()`: Verificam comandos no início, antes da IA
- Retorna `comando_interface` no response para o frontend executar a ação correspondente

**Arquivos relacionados:**
- `services/message_intent_service.py` - Detecção de comandos
- `services/chat_service.py` - Integração no processamento
- `templates/chat-ia-isolado.html` - Processamento no frontend

### Contexto de Sessão

- Contexto persistido em SQLite (`conversas_chat`)
- Usado para manter histórico entre mensagens
- Limpado com comando `reset`

### Tool Calling

- IA decide quais tools chamar baseado no prompt
- Tools retornam resultados estruturados
- Resultados combinados na resposta final

---

## 📚 Documentação Adicional

- **`README.md`**: Documentação principal do projeto
- **`docs/API_DOCUMENTATION.md`**: Documentação completa da API
- **`docs/MAPEAMENTO_SQL_SERVER.md`**: Mapeamento de tabelas SQL Server
- **`docs/REGRAS_NEGOCIO.md`**: Regras de negócio do sistema

---

## 🔄 Sistema de Fallback de Tools (NOVO - 14/01/2026)

### ⚠️ **COMPLICAÇÕES CRÍTICAS E COMO TRATAR**

O sistema de execução de tools usa uma arquitetura em camadas com **dois tipos de fallback** que devem ser tratados corretamente para evitar loops infinitos e roteamento incorreto.

### Arquitetura de Fallback

**Camadas de Execução:**
1. **ToolExecutionService** → Handlers extraídos (ex: `enviar_email`, `enviar_relatorio_email`)
2. **ToolRouter** → Agents especializados (ex: `ProcessoAgent`, `DuimpAgent`)
3. **ChatService (legado)** → Implementação antiga (fallback final)

### Dois Tipos de Fallback

#### 1. **Fallback de Roteamento** (`fallback_to="TOOL_ROUTER"`)
**Quando ocorre:** Handler não existe no `ToolExecutionService`  
**Destino:** `ToolRouter` (agents especializados)  
**Exemplo:** `obter_dashboard_hoje` não tem handler no `ToolExecutionService`, então vai para `ToolRouter` → `ProcessoAgent`

**✅ Atualização (14/01/2026 - estabilidade):**
- Quando **não há handler**, `ToolExecutionService.executar_tool()` deve retornar **`None`** (não um dict “vazio”).
- Isso evita regressões onde o `ChatService` retornava um “resultado” sem `resposta` e o frontend caía na mensagem genérica.

#### 2. **Fallback Interno** (`fallback_to="CHAT_SERVICE"`)
**Quando ocorre:** Handler existe mas quer delegar para código legado  
**Destino:** `ChatService` (implementação antiga)  
**Exemplo:** `enviar_relatorio_email` em modo preview retorna `fallback_to="CHAT_SERVICE"` porque a lógica é muito complexa e ainda não foi extraída

### ⚠️ **REGRAS CRÍTICAS**

#### ✅ **REGRA 1: `_fallback_attempted` SEMPRE inicializa como `False`**

**Problema:** Se `_fallback_attempted` não for inicializado, pode causar detecção prematura de loop.

**Solução:**
```python
def _executar_funcao_tool(self, ...):
    # ✅✅✅ CRÍTICO: Sempre inicializar como False no início
    _fallback_attempted = False
    # ... resto do código
```

**Localização:** `services/chat_service.py`, linha ~608

---

#### ✅ **REGRA 2: `enviar_relatorio_email` NUNCA vai para ToolRouter**

**Problema:** `enviar_relatorio_email` tem handler no `ToolExecutionService`, mas no modo preview retorna `fallback_to="CHAT_SERVICE"`. Se o código não tratar isso corretamente, pode tentar ir para `ToolRouter` (que não tem essa tool), causando loop/erro.

**Solução:**
```python
if destino == "CHAT_SERVICE":
    # ✅✅✅ REGRA CRÍTICA: Retornar IMEDIATAMENTE - NÃO continuar para ToolRouter
    logger.info(f'✅ fallback_to=CHAT_SERVICE: usando handler legado para {nome_funcao}')
    resultado_legado = self._fallback_chat_service(nome_funcao, argumentos, ...)
    return resultado_legado  # ⚠️ CRÍTICO: Retornar aqui, não continuar
```

**Localização:** `services/chat_service.py`, linha ~643-646

**⚠️ IMPORTANTE:** Quando `fallback_to="CHAT_SERVICE"`, a execução **DEVE PARAR** e não continuar para `ToolRouter`.

---

#### ✅ **REGRA 3: `_fallback_chat_service()` não pode causar recursão**

**Problema:** Se `_fallback_chat_service()` chamar `_executar_funcao_tool()` diretamente, pode causar loop recursivo (ToolExecutionService → ChatService → ToolExecutionService → ...).

**Solução:**
```python
def _executar_funcao_tool_legacy_enviar_relatorio_email(self, ...):
    # Salvar estado atual
    tool_execution_service_original = getattr(self, 'tool_execution_service', None)
    tool_executor_original = getattr(self, 'tool_executor', None)
    
    # Temporariamente desabilitar para evitar loop
    self.tool_execution_service = None
    self.tool_executor = None
    
    try:
        # Agora vai direto para o bloco "Fallback: Implementação antiga"
        resultado = self._executar_funcao_tool(...)
        return resultado
    finally:
        # Restaurar estado original
        self.tool_execution_service = tool_execution_service_original
        self.tool_executor = tool_executor_original
```

**Localização:** `services/chat_service.py`, linha ~789-840

---

#### ✅ **REGRA 4: Loop detection aceita `_use_fallback` OU `use_fallback`**

**Problema:** Diferentes partes do código podem usar `_use_fallback` (com underscore) ou `use_fallback` (sem underscore). A detecção de loop deve aceitar ambos.

**Solução:**
```python
# ✅✅✅ CRÍTICO: Aceitar tanto "_use_fallback" quanto "use_fallback"
router_pediu_fallback = (
    resultado_router and (
        resultado_router.get("_use_fallback", False) or 
        resultado_router.get("use_fallback", False)
    )
)
if _fallback_attempted and router_pediu_fallback:
    # Loop detectado - retornar erro final
    return err_result(...)
```

**Localização:** `services/chat_service.py`, linha ~696-707

---

### 📋 **Checklist de Validação**

Ao implementar ou modificar fallback, verificar:

- [ ] `_fallback_attempted` está inicializado como `False` no início do método?
- [ ] Quando `fallback_to="CHAT_SERVICE"`, o código retorna imediatamente (não continua para ToolRouter)?
- [ ] `_fallback_chat_service()` desabilita `ToolExecutionService` e `ToolExecutor` antes de chamar código legado?
- [ ] Loop detection aceita tanto `_use_fallback` quanto `use_fallback`?
- [ ] `enviar_relatorio_email` nunca vai para ToolRouter quando em modo preview?

### 🧪 **Testes Obrigatórios**

1. **Tool com handler direto:**
   ```
   "envie um email para teste@exemplo.com"
   ```
   → Deve funcionar via ToolExecutionService (sem fallback)

2. **Tool sem handler (ex: obter_dashboard_hoje):**
   ```
   "o que temos pra hoje?"
   ```
   → Deve ir para ToolRouter e funcionar

3. **enviar_relatorio_email (preview):**
   ```
   "filtre os dmd"
   "envie esse relatorio para helenomaffra@gmail.com"
   ```
   → Deve ir para handler legado (NÃO ToolRouter)
   → Log deve mostrar: `✅ fallback_to=CHAT_SERVICE: usando handler legado`

4. **Verificar logs:**
   - Não deve aparecer: `⚠️ ToolRouter também pediu fallback para enviar_relatorio_email`
   - Deve aparecer: `✅ fallback_to=CHAT_SERVICE: usando handler legado para enviar_relatorio_email`

### 📚 **Documentação Relacionada**

- `docs/CORRECOES_FALLBACK_APLICADAS.md` - Correções implementadas
- `docs/PROMPT_CURSOR_FALLBACK_PATCH.md` - Prompt para correções futuras
- `services/tool_execution_service.py` - Implementação do ToolExecutionService
- `services/chat_service.py` - Lógica de fallback no ChatService

---

## ⚠️ NOTAS CRÍTICAS E COMPLIANCE (IN 1986/2020)

### 🔴 Risco de Interposição Fraudulenta
O sistema deve seguir rigorosamente o procedimento de **Origem de Recursos** para evitar crimes contra a ordem tributária e retenção de cargas no Canal Cinza.

**Documento de Referência:** `docs/PROCEDIMENTO_ORIGEM_RECURSOS_IN1986.md`

**Regras de Ouro para o Agente:**
1.  **Rastreabilidade:** Todo pagamento de imposto deve ter um "lastro" (entrada de dinheiro do cliente correspondente).
2.  **Alerta de Risco:** Se não houver saldo virtual suficiente do cliente para cobrir um débito de imposto, o Agente **DEVE** alertar sobre o risco de compliance.
3.  **Fonte da Verdade:** A comprovação da origem lícita do dinheiro é prioridade máxima na conciliação bancária.

---

## ⚠️ Notas Importantes

1. **SQL Server**: Priorizar cache (SQLite) antes de consultar SQL Server
2. **APIs Bilhetadas**: Sempre verificar cache antes de bilhetar
3. **IA**: Usar `AI_MODEL_INTELIGENTE` para operações, `AI_MODEL_ANALITICO` para relatórios
4. **Agents**: Sempre herdar de `BaseAgent` e implementar `execute()`
5. **Logging**: Sempre logar operações importantes e erros
6. **Erros**: Sempre retornar dict com `sucesso: bool` e mensagem clara
7. **⚠️ TESTES OBRIGATÓRIOS**: NUNCA assuma que está correto sem executar os testes obrigatórios (ver seção "🧪 Testes")
8. **🚨 VALIDAÇÃO APÓS EDIÇÃO**: SEMPRE rodar `python3 -m py_compile <arquivo>.py` e testar imports após editar qualquer arquivo Python (ver seção "🚨 REGRA CRÍTICA: VALIDAÇÃO OBRIGATÓRIA" no início)
8. **Comandos de Interface**: Detecção de comandos deve ocorrer **ANTES** de qualquer processamento pela IA para resposta instantânea
9. **Backups**: `backups/last_backup` é um “ponteiro” para o snapshot mais recente criado por `scripts/fazer_backup.sh`. Atualmente ele é um **link (symlink) para uma pasta** (não mais um arquivo texto). Para ver para onde aponta, use `ls -l backups/last_backup` (ou `readlink backups/last_backup`). Sempre confira antes de restaurar, para não reintroduzir bugs antigos.
9. **✅ NOVO (08/01/2026):** Sincronização Santander: Descrição completa combina `transactionName + historicComplement` ao salvar no banco
10. **✅ NOVO (08/01/2026):** Sincronização Santander: Suporte a múltiplos formatos de data (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY)
11. **✅ NOVO (08/01/2026):** Tratamento de erros de timeout: Orientar usuário a sincronizar novamente quando SQL Server estiver acessível
12. **✅ NOVO (08/01/2026):** Duplicatas são detectadas automaticamente pelo hash - não há problema em sincronizar novamente após erro de timeout
13. **✅ NOVO (14/01/2026):** Sistema de Pending Intents: Ações sensíveis (email, DUIMP, pagamento) são persistidas no DB e sobrevivem a refresh de página
14. **✅ NOVO (14/01/2026):** Confirmação atômica: Status `executing` previne duplo execute em concorrência
15. **✅ NOVO (14/01/2026):** Status `expired` separado de `cancelled` para melhor auditoria e debug
16. **✅ NOVO (14/01/2026):** Preview sanitizado: Dados sensíveis (email, CNPJ, CPF, valores) são mascarados antes de salvar
17. **✅ NOVO (13/01/2026):** API de Pagamentos Banco do Brasil: Pagamento em lote de boletos, PIX e TED
18. **✅ NOVO (13/01/2026):** API de Pagamentos Santander: Accounts and Taxes (Boletos, PIX, TED, Impostos)
19. **✅ NOVO (13/01/2026):** Pagamentos são ações sensíveis: Requerem confirmação via pending intents antes de executar
20. **✅ NOVO (14/01/2026):** Sistema de Fallback de Tools: Dois tipos de fallback (roteamento vs interno) com regras críticas para evitar loops infinitos

---

## 🚨 PENDÊNCIAS URGENTES - PRÓXIMA SEÇÃO

### ⚠️ Revisão e Validação de Relatórios (23/12/2025)

**Status:** 🔴 **URGENTE** - Requer revisão completa e validação de dados

#### 1. Relatório de Averbações (`RelatorioAverbacoesService`)

**Problemas identificados:**
- ⚠️ Query SQL não está encontrando processos corretamente para alguns meses/categorias
- ⚠️ Filtros de data podem estar incorretos (dataHoraDesembaraco vs dataHoraSituacaoDi vs dataHoraRegistro)
- ⚠️ Necessário validar se a query está alinhada com o relatório FOB que funciona

**O que revisar:**
- ✅ Query `_buscar_processos_com_di_no_mes` em `services/relatorio_averbacoes_service.py`
- ✅ Validação de filtros de data (prioridade: dataHoraDesembaraco → dataHoraSituacaoDi → dataHoraRegistro)
- ✅ Testes com diferentes meses e categorias (DMD, VDM, etc.)
- ✅ Comparação com query do relatório FOB que funciona corretamente

**Arquivos relacionados:**
- `services/relatorio_averbacoes_service.py` - Método `_buscar_processos_com_di_no_mes`
- `teste_averbacao_debug.py` - Script de debug criado para testar a query

#### 2. Relatório FOB (`RelatorioFobService`)

**Problemas identificados:**
- ⚠️ Valores de frete podem estar incorretos (ex: DMD.0090/25 mostra USD 3,000.00 mas deveria ser USD 4,500.00)
- ⚠️ Query de frete pode estar pegando valor errado quando há múltiplos registros (retificações)
- ⚠️ Necessário validar valores em dólar antes de conversão (taxa de câmbio pode estar incorreta)

**O que revisar:**
- ✅ Query de frete da DI (subquery correlacionada pode estar pegando registro errado)
- ✅ Validação de valores em USD vs BRL (conferir taxa de câmbio implícita)
- ✅ Lógica de seleção de frete quando há múltiplos registros (usar `valorFreteBasico` do CE?)
- ✅ Testes com processos específicos (ex: DMD.0090/25) para validar valores

**Arquivos relacionados:**
- `services/relatorio_fob_service.py` - Query de DI (subqueries de frete/seguro)
- `teste_dmd_0090_valores.py` - Script de debug criado para validar valores
- `teste_frete_dmd_0090.py` - Script específico para debugar frete

**Notas importantes:**
- O usuário reportou que o frete correto para DMD.0090/25 é USD 4,500.00 (não USD 3,000.00)
- Taxa de câmbio oficial na época era R$ 5.5283 por USD
- Valores devem ser conferidos primeiro em dólar, depois na conversão
- O CE tem `valorFreteTotal` e `valorFreteBasico` - verificar qual deve ser usado para DI

---

---

## 🧠 Normalização de Termos Cliente → Categoria (NOVO - 08/01/2026)

### Visão Geral

Sistema que permite mapear termos de cliente (ex: "Diamond", "Bandimar", "alho") para categorias de processo (ex: "DMD", "BND", "ALH") de forma automática e inteligente.

### Como Funciona

1. **Regras Aprendidas**: O usuário pode criar regras diretamente no chat:
   - "maike o ALH vai ser alho ok?" → cria regra `alho → ALH`
   - "maike Diamond vai ser DMD" → cria regra `Diamond → DMD`

2. **Normalização Automática**: `PrecheckService._normalizar_termo_cliente()`:
   - Busca regras aprendidas do tipo `cliente_categoria`
   - Aplica normalização **antes** do processamento pela IA
   - Prioriza regras aprendidas sobre contexto anterior

3. **Integração com Prompt**: Regras são incluídas automaticamente no prompt da IA:
   - Buscadas do SQLite (`chat_ia.db`)
   - Formatadas e adicionadas ao `system_prompt`
   - Limitadas às 5 regras mais usadas/recentes

### Arquivos Relacionados

- `services/precheck_service.py` - Método `_normalizar_termo_cliente()`
- `services/learned_rules_service.py` - Gerenciamento de regras aprendidas
- `services/prompt_builder.py` - Inclusão de regras no prompt
- `docs/NORMALIZACAO_TERMOS_CLIENTE.md` - Documentação completa
- `docs/COMO_IA_DETECTA_MAPEAMENTO.md` - Como a IA detecta mapeamentos
- `docs/COMO_PEDIR_REGRAS_CLIENTE_CATEGORIA.md` - Como pedir regras corretamente
- `docs/COMO_REGRAS_APARECEM_NO_PROMPT.md` - Como regras aparecem no prompt

### Exemplo de Uso

**Criar regra:**
```
Usuário: "maike o ALH vai ser alho ok?"
IA: ✅ Regra aprendida salva: alho → ALH (ID: 9)
```

**Usar regra:**
```
Usuário: "como estão os processos do alho?"
Sistema: Normaliza "alho" → "ALH"
IA: Lista processos da categoria ALH
```

---

## 🎨 UI/UX - Menu Drawer e Comandos de Voz/Texto (NOVO - 07/01/2026)

### Visão Geral

O sistema implementa um menu drawer lateral elegante e sistema de detecção de comandos de voz/texto para uma experiência mais humanizada e interativa.

### Menu Drawer

**Características:**
- Menu lateral deslizante da direita
- Animação suave de abertura/fechamento
- Overlay escuro ao abrir
- Fecha com ESC ou clicando no overlay
- Design responsivo (max-width: 90vw em mobile)
- Organizado por categorias:
  - **Financeiro**: Sincronizar Extratos, Conciliação Bancária
  - **Documentos**: Importar Legislação
  - **Sistema**: Configurações, Consultas Pendentes
  - **Ajuda**: O que posso fazer?

### Sistema de Comandos de Interface

**Como funciona:**
1. Usuário digita comando (ex: "maike menu")
2. `MessageIntentService.detectar_comando_interface()` detecta o comando **antes** do processamento pela IA
3. Sistema retorna `comando_interface` no response
4. Frontend processa e executa ação correspondente instantaneamente
5. Resposta rápida sem passar pela IA

**Comandos disponíveis:**
- `"maike menu"` → `{'tipo': 'menu', 'acao': 'abrir_menu'}`
- `"maike quero conciliar banco"` → `{'tipo': 'conciliação', 'acao': 'abrir_conciliação'}`
- `"maike quero sincronizar banco"` → `{'tipo': 'sincronização', 'acao': 'abrir_sincronização'}`
- `"maike quero importar legislação"` → `{'tipo': 'legislação', 'acao': 'abrir_legislação'}`
- `"maike configurações"` → `{'tipo': 'config', 'acao': 'abrir_config'}`

**Implementação técnica:**
- Detecção via regex patterns em `MessageIntentService`
- Integração no início de `ChatService.processar_mensagem()` e `ChatService.processar_mensagem_stream()`
- Retorno especial com `comando_interface` flag para o frontend
- Frontend processa em `templates/chat-ia-isolado.html` na função `enviarMensagemChat()`

**Arquivos relacionados:**
- `services/message_intent_service.py` - Método `detectar_comando_interface()`
- `services/chat_service.py` - Integração no processamento (modo normal)
- `services/chat_service_streaming_mixin.py` - Integração no processamento (modo streaming)
- `templates/chat-ia-isolado.html` - Processamento no frontend (função `enviarMensagemChat()` / streaming SSE)

**Exemplo de uso:**
```python
# No MessageIntentService
comando = self.detectar_comando_interface("maike menu")
# Retorna: {'tipo': 'menu', 'acao': 'abrir_menu'}

# No ChatService (antes da IA)
if comando_interface:
    return {
        'resposta': f"✅ {comando_interface.get('tipo')} detectado!",
        'comando_interface': comando_interface,
        'acao': 'comando_interface'
    }
```

**Header simplificado:**
- Um único botão de menu (☰) substitui múltiplos botões
- Interface mais limpa e focada no chat
- Badge de consultas pendentes também abre o menu

---

---

## 🔐 Sistema de Pending Intents (NOVO - 14/01/2026)

### Visão Geral

Sistema que persiste ações sensíveis (email, DUIMP, pagamento) que requerem confirmação do usuário, garantindo que o estado sobreviva a refresh de página ou interrupções.

### Arquitetura

**Tabela SQLite:** `pending_intents`
- `intent_id` (UUID): Identificador único
- `session_id`: Sessão do usuário
- `action_type`: Tipo de ação (`send_email`, `create_duimp`, `payment`)
- `tool_name`: Nome da tool que será executada
- `args_normalizados`: JSON com argumentos normalizados (fonte da verdade)
- `payload_hash`: Hash SHA-256 para detecção de duplicatas
- `preview_text`: Preview sanitizado (máx 200 chars, dados sensíveis mascarados)
- `status`: `pending`, `executing`, `executed`, `cancelled`, `expired`
- `created_at`, `expires_at`, `executed_at`, `observacoes`

**Serviços:**
- `PendingIntentService` (`services/pending_intent_service.py`): CRUD completo
- `ConfirmationHandler` (`services/handlers/confirmation_handler.py`): Processamento de confirmações

### Status dos Status

| Status | Significado | Quando Usar |
|--------|-------------|-------------|
| `pending` | Aguardando confirmação | Estado inicial |
| `executing` | Em execução (lock) | Durante confirmação atômica |
| `executed` | Executado com sucesso | Após execução bem-sucedida |
| `cancelled` | Cancelado pelo usuário | Quando usuário desiste |
| `expired` | Expirado (TTL) | Quando TTL expira (2h padrão) |

### Funcionalidades Principais

1. **SQLite como Fonte da Verdade**
   - Sistema **SEMPRE** usa SQLite na confirmação
   - Ignora memória (`ultima_resposta_aguardando_email/duimp`)
   - `args_normalizados` do DB são fonte da verdade

2. **Idempotência**
   - Verifica `status` antes de executar
   - `executed` → "já executado"
   - `expired` → "expirou, gere preview novamente"
   - `cancelled` → "cancelado"
   - `executing` → "em execução"

3. **Confirmação Atômica (Anti Duplo Execute)**
   - Status `executing` como lock intermediário
   - Fluxo: `pending` → `executing` → `executed`
   - Se `rowcount == 0`, não executa (alguém já pegou)
   - Protege contra concorrência (web + WhatsApp, retry)

4. **Ambiguidade: Múltiplos Pending Intents**
   - Detecta quando há > 1 intent pendente
   - Lista opções numeradas: `(1)`, `(2)`, `(3)`
   - Aceita resposta simples: "1", "2", "3"
   - Flag `requer_escolha: True` e `opcoes: [...]` no retorno

5. **Sanitização de Preview**
   - Método `_sanitizar_preview_text()` mascara dados sensíveis:
     - Emails: `usuario@exemplo.com` → `us***@exemplo.com`
     - CNPJ: `12.345.678/0001-90` → `12.***.***/****-**`
     - CPF: `123.456.789-00` → `123.***.***-**`
     - Valores: `R$ 1.234,56` → `R$ ***,**`
   - Trunca para 200 chars

### Fluxo de Confirmação

1. **Criação de Preview:**
   - Usuário pede ação sensível (email, DUIMP)
   - Sistema gera preview e cria `pending_intent` no DB
   - Retorna preview ao usuário: "⚠️ Confirme para executar (sim/enviar/pagar)"

2. **Confirmação:**
   - Usuário diz "sim/enviar/pagar"
   - Sistema busca `pending_intent` do DB (fonte da verdade)
   - Verifica status (se não for `pending`, retorna erro)
   - **Marca como `executing`** (lock atômico)
   - Se `rowcount == 0` → alguém já pegou, retorna erro
   - Executa ação usando `args_normalizados` do DB
   - Marca como `executed` (só funciona se status for `executing`)

3. **Múltiplos Pendentes:**
   - Se há > 1 intent pendente, lista opções numeradas
   - Usuário escolhe: "1", "2", "3"
   - Sistema processa escolha e mostra preview
   - Usuário confirma: "sim/enviar/pagar"

### Arquivos Relacionados

- `db_manager.py` - Tabela `pending_intents`
- `services/pending_intent_service.py` - CRUD completo
- `services/handlers/confirmation_handler.py` - Processamento de confirmações
- `services/chat_service.py` - Criação automática de pending intents

**📚 Documentação (Fase 1 + Fase 2A/2B):**

1. **`docs/CORRECAO_MARCAR_COMO_EXECUTANDO.md`** - Correção do método `marcar_como_executando()` com lock atômico
   - Problema: Método não existia, causando `AttributeError`
   - Solução: Implementação com compare-and-set atômico
   - Proteção contra envios duplicados em concorrência

2. **`docs/REFINAMENTOS_FINAIS_FASE_1.md`** - Refinamentos finais da Fase 1
   - Transações com context manager
   - Consistência de status strings
   - Recuperação de intents travados
   - Logging detalhado

3. **`docs/CORRECOES_PEGADINHAS_FASE_1.md`** - Correções de "pegadinhas" críticas
   - `created_at` vs `executing_at` (timestamp de transição)
   - Formato de timestamp (isoformat vs CURRENT_TIMESTAMP)
   - Interpolação de string no SQL
   - Consistência de `executed_at`

4. **`docs/ANALISE_FASE_2_IMPLEMENTACAO.md`** - Análise para implementar Fase 2
   - Resolução automática de contexto
   - Análise de impacto vs esforço
   - Recomendação: ✅ SIM, vale a pena implementar
   - Plano de implementação (4-6 horas)

5. **`docs/FASE_2A_IMPLEMENTACAO.md`** - Implementação da Fase 2A (ToolGateService escopo pequeno)
   - Allowlist de tools de relatório
   - Feature flag `TOOL_GATE_ENABLED`
   - Injeção determinística de `report_id` (active/last_visible)
   - Erro controlado quando não há relatório na sessão

6. **`docs/FASE_2B_IMPLEMENTACAO.md`** - Implementação da Fase 2B (REPORT_META + TTL)
   - REPORT_META como fonte persistida (report_history)
   - Validação de domínio + TTL/staleness
   - Validação de existência no banco (`buscar_relatorio_por_id`)

**Documentação adicional:**
- `docs/STATUS_IMPLEMENTACAO_PENDING_INTENTS.md` - Status completo
- `docs/REFINAMENTOS_FINAIS_PENDING_INTENTS.md` - Refinamentos implementados
- `docs/FASE_2_RESOLUCAO_AUTOMATICA_CONTEXTO.md` - Próxima fase (planejada)

### Exemplo de Uso

**Criar email:**
```
Usuário: "envie um email para cliente@exemplo.com sobre o processo DMD.0001/26"
Sistema: Cria pending_intent, gera preview, retorna "⚠️ Confirme para enviar (sim/enviar)"
```

**Confirmar:**
```
Usuário: "sim"
Sistema: Busca pending_intent do DB, marca como executing, envia email, marca como executed
```

**Múltiplos pendentes:**
```
Usuário: "sim"
Sistema: "📋 Há 2 emails pendentes. Qual deseja confirmar?
         (1) Email para cliente1@exemplo.com - Assunto: Processo DMD.0001/26
         (2) Email para cliente2@exemplo.com - Assunto: Processo DMD.0002/26
         💡 Digite o número (1, 2, 3...) ou 'cancelar' para cancelar."
```

---

---

## 🎯 Abordagem Híbrida de Detecção de Intenções (NOVO - 14/01/2026)

### Princípio Fundamental

**Regex/regras para comandos críticos e de confirmação**  
**Modelo escolhe para pedidos "fuzzy"**

### Categorias

#### 1. ✅ Regex/Regras (Precheck) - Comandos Críticos

**Quando usar:** Comandos que precisam ser detectados com 100% de precisão e rapidez.

- **Confirmações simples:** "sim", "enviar", "cancelar", "ok", "confirmar"
  - Localização: `ConfirmationHandler.processar_confirmacao_email()` (linha 420)
- **Comandos de pagamento:** "continue o pagamento", "confirmar pagamento", "efetivar boleto"
  - Localização: `PrecheckService.tentar_responder_sem_ia()` (linhas 52-107)
- **Comandos de banco:** "extrato do banco do brasil", "extrato do santander"
  - Localização: `PrecheckService.tentar_responder_sem_ia()` (linhas 192-280)
- **Comandos de interface:** "maike menu", "maike quero conciliar banco"
  - Localização: `MessageIntentService.detectar_comando_interface()`
- **Comandos de email (listagem):** "ver email", "ler emails", "detalhe email 3"
  - Localização: `PrecheckService.tentar_responder_sem_ia()` (linhas 109-159)

#### 2. 🤖 Modelo (IA) - Pedidos "Fuzzy"

**Quando usar:** Pedidos que requerem interpretação semântica, contexto, ou podem ter variações.

- **Relatórios e dashboards:** "o que temos pra hoje?", "filtra DMD", "envie esse relatorio" (mesmo com erro: "ralatorio")
- **Consultas de processos:** "como estão os DMD?", "status do processo BND.0084/25"
- **Consultas de documentos:** "extrato do CE do processo X", "mostra a DI do processo Y"
- **Emails personalizados:** "envie um email para X sobre Y", "mande um email amoroso"

### Regras de Ouro

1. **NUNCA usar regex para pedidos "fuzzy"** (ex: "envie esse relatorio")
2. **SEMPRE usar regex para confirmações simples** (ex: "sim", "enviar", "cancelar")
3. **SEMPRE usar regex para comandos críticos** (ex: pagamentos, extratos bancários)
4. **SEMPRE deixar IA interpretar pedidos com contexto** (ex: "filtra DMD", "o que temos pra hoje?")
5. **SEMPRE usar last_visible_report_id quando IA chama enviar_relatorio_email** (não depender de regex)

**Documentação completa:** `docs/ABORDAGEM_HIBRIDA_DETECCAO_INTENCOES.md`

---

**Última atualização:** 14/01/2026
