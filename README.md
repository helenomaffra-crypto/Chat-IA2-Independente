
# 🤖 Chat IA Independente - V1

Sistema de Chat IA conversacional extraído do projeto DUIMP-PDF para funcionar de forma completamente independente.

**⚠️ SEPARAÇÃO V1/V2 (26/01/2026):** Este diretório contém **APENAS a V1**. A V2 foi migrada para `/Volumes/KINGSTON/PYTHON/v2_langchain` e está completamente separada. Para trabalhar na V2, use o diretório separado.

**Localização V1:** `/Users/helenomaffra/Chat-IA2-Independente/` (este diretório)  
**Localização V2:** `/Volumes/KINGSTON/PYTHON/v2_langchain`  
**Porta V1:** `5001`  
**Porta V2:** `5002`

---

## 📋 Índice

- [Status do Projeto](#-status-do-projeto)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Configuração](#-configuração)
- [Como Usar](#-como-usar)
- [Como Testar](#-como-testar)
- [Quais Processos a IA Acessa?](#-quais-processos-a-ia-acessa)
- [Sistema de Verificação de Fontes de Dados](#-sistema-de-verificação-de-fontes-de-dados-novo)
- [Sistema de Aprendizado e Contexto Persistente](#-sistema-de-aprendizado-e-contexto-persistente-novo)
- [Sistema de Consultas Analíticas SQL](#-sistema-de-consultas-analíticas-sql-novo)
- [Troubleshooting](#-troubleshooting)
- [Documentação Adicional](#-documentação-adicional)
- [Mapeamento de Códigos de Receita da DI (Impostos)](#-mapeamento-de-códigos-de-receita-da-di-impostos)
- [Sistema de Envio de Email com Confirmação](#-sistema-de-envio-de-email-com-confirmação)
- [Code Interpreter para Cálculos com Explicação](#-code-interpreter-para-cálculos-com-explicação-novo)
- [Integração com Santander Open Banking](#-integração-com-santander-open-banking-novo)
- [Transferências TED via Santander](#-transferências-ted-via-santander-novo---12012026)
- [Accounts and Taxes - Pagamentos Santander](#-accounts-and-taxes---pagamentos-santander-novo---13012026)
- [Integração com Banco do Brasil](#-integração-com-banco-do-brasil-novo)
- [Mercante / AFRMM (RPA)](#-mercante--afrmm-rpa-novo)
- [UI/UX - Menu Drawer e Comandos de Voz/Texto](#-uiux---menu-drawer-e-comandos-de-voztexto-novo---07012026)
- [Docker (subir com persistência e menos dor)](#-docker-subir-com-persistência-e-menos-dor)

---

## ✅ Status do Projeto

**Status:** ✅ **FUNCIONANDO!** - App testado e operacional na porta 5001

**⚠️ SEPARAÇÃO V1/V2 (26/01/2026):** A V2 foi migrada para `/Volumes/KINGSTON/PYTHON/v2_langchain` e está separada da V1. Este diretório contém **APENAS a V1**. Para trabalhar na V2, use o diretório separado.

**💾 Cópia de Segurança:** `Chat-IA-Independente -V1012` (backup completo de 10/12/2025)

### ✅ O que está completo:

- ✅ Estrutura de diretórios criada
- ✅ Arquivos core copiados e adaptados:
  - `app.py` - Aplicação Flask independente
  - `ai_service.py` - Serviço de IA
  - `db_manager.py` - Gerenciador de banco de dados (adaptado)
  - `services/` - Todos os serviços do chat
  - `services/agents/` - Todos os agents
  - `templates/chat-ia-isolado.html` - Interface do chat
  - `utils/` - Utilitários (portal_proxy, integracomex_proxy, sql_server_adapter)
- ✅ `requirements.txt` - Dependências Python
- ✅ Adaptador SQL Server criado
- ✅ Documentação completa

### 📊 Fechamento do dia (o que significa “movimentações”)

No relatório **FECHAMENTO DO DIA**, “movimentações” é a soma de eventos COMEX do dia, incluindo:
- chegadas (processo chegou/armazenado no dia)
- desembaraços
- DIs registradas
- DUIMPs registradas/criadas
- mudanças de status (CE/DI/DUIMP)
- pendências resolvidas

Se o usuário pedir “**quais foram essas X movimentações**”, o sistema deve abrir a lista detalhada (seção `movimentacoes`) do relatório salvo da sessão.

---

## 🐳 Docker (subir com persistência e menos dor)

Este projeto inclui `Dockerfile` e `docker-compose.yml` prontos para facilitar a vida do time.

- **SQLite no Docker**: funciona normalmente. O ponto importante é **persistir o arquivo** via volume e evitar muitos workers escrevendo no mesmo arquivo.
- **SQL Server**: o container inclui Node.js + dependências (`mssql`) para o adapter Node funcionar; conectividade depende da rede/DNS/VPN do host.

### Requisitos

- Docker + Docker Compose
- Arquivo `.env` (não é versionado)

### Subir

```bash
docker compose up --build
```

### Comandos rápidos (dia a dia) ✅

> Se você é novato no Docker: **use `http://localhost`** (Nginx) e rode os comandos abaixo na raiz do projeto (onde está o `docker-compose.yml`).

```bash
# Ver status dos containers
docker compose ps

# Subir em background (recomendado)
docker compose up -d --build

# Ver logs do backend (web)
docker compose logs -f web

# Reiniciar só o backend (quando mudou código Python)
docker compose restart web

# Recriar containers (quando mudou .env / variáveis de ambiente)
docker compose down
docker compose up -d

# Entrar e rodar um comando dentro do container web
docker compose exec web bash
docker compose exec web python -c "import os; print(os.getenv('USE_POSTGRES'))"

# Healthcheck correto (no Docker, não use localhost:5001)
curl -s http://localhost/health
```

**Dica importante (evitar confusão):**

- Se você estiver usando Docker (`http://localhost`), **não rode `python app.py` no Mac ao mesmo tempo**.

### Persistência

- O SQLite fica em `maike_data` (volume montado em `/app/data` no container).
- O arquivo padrão no container é `DB_PATH=/app/data/chat_ia.db`.
- Certificados ficam em `./.secure` (montado em `/app/.secure` como somente leitura).

### Limpeza automática de áudios TTS (mp3)

Os áudios gerados pelo mAIke ficam em `downloads/tts/*.mp3`. Para evitar lotar o disco, existe limpeza automática:

- **Por idade**: `OPENAI_TTS_CACHE_DAYS` (padrão: 7)
- **Por quantidade**: `OPENAI_TTS_CACHE_MAX_FILES` (padrão: 500)
- **Intervalo de limpeza**: `TTS_CLEANUP_INTERVAL_HOURS` (padrão: 6)

Depois de alterar `.env`, use:

```bash
docker compose down
docker compose up -d
```

### Dicas de produção

- O container roda com **1 worker** por padrão (Gunicorn) para evitar `database is locked` no SQLite.
- Para habilitar sync do ShipsGo automaticamente dentro do container:
  - set `SHIPSGO_SYNC_ENABLED=true` e ajuste `SHIPSGO_SYNC_TTL_MIN`.

### ✅ Melhorias recentes (rodadas atuais)

- ✅ **Processos históricos + ativos unificados**: `ProcessoRepository` e `sql_server_processo_schema` consolidados, permitindo consultar processos antigos (SQL Server) e ativos (Kanban) pelo mesmo caminho.
- ✅ **Situação de processo determinística**: serviço dedicado (`processo_status_service`) e uso obrigatório via `consultar_status_processo`, evitando “chutes” da IA.
- ✅ **Extratos DI/DUIMP/CE/CCT funcionando**: pré-checks detectam pedidos de extrato e chamam as tools corretas (Integra Comex / Serpro) de forma determinística.
- ✅ **Blindagem de NCM e categorias**: `_extrair_categoria_da_mensagem` e `PrecheckService` ajustados para não confundir NCM, palavras comuns ou “alho/EM/TOP/MAIS” com categorias de processo.
- ✅ **Modelos separados (operacional x analítico)**: roteamento automático entre `AI_MODEL_DEFAULT` (operacional) e `AI_MODEL_ANALITICO` (BI/relatórios) conforme o tipo de pergunta.
- ✅ **Camada analítica determinística inicial**: `analytics_service` com agregação de chegadas por ETA **agrupadas por categoria** (ex.: “quantos processos estão chegando nesta semana? agrupe por categoria”).
- ✅ **Refatoração do prompt**: criação do `PromptBuilder` (`services/prompt_builder.py`) para montar `system_prompt` e `user_prompt` fora do `chat_service.py`.
- ✅ **Precheck centralizado**: `PrecheckService` (`services/precheck_service.py`) para tratar antes da IA perguntas de situação de processo, NCM, extratos e chegadas.
- ✅ **Policy determinística (sem regex espalhado) - IntentPolicyService (18/01/2026)**:
  - Centraliza regras críticas “policy-as-code” (antes do modelo) em `services/intent_policy_service.py`
  - Força tool calls em casos sensíveis (auditoria/compliance), com prioridade clara:
    - **NESH direto** (mensagens com “nesh” / “nota explicativa”) → força `buscar_nota_explicativa_nesh`
    - **Modo legislação (TTL por sessão)** (mensagens com “pela legislação / base legal / artigo…”) → força `buscar_legislacao_responses` e mantém follow-ups por alguns minutos
  - Regras configuráveis em `config/intent_policy_rules.json`
  - (Opcional) path via ENV: `INTENT_POLICY_RULES_PATH`
  - **Mini manual (editar sem patch em Python)**:
    - **Onde editar**: `config/intent_policy_rules.json`
    - **Ajustar TTL do “modo legislação”**:
      - Opção A (global): altere `default_ttl_minutes`
      - Opção B (só na policy): altere `policies[].ttl_minutes` dentro de `"id": "legislacao_rag"`
      - Exemplo: trocar 15 → 5 minutos:
        - `default_ttl_minutes: 5` (ou `ttl_minutes: 5` na policy)
    - **Remover um gatilho (ex: “lei”)**:
      - No bloco `"id": "legislacao_rag"`, remova o regex correspondente dentro de `match_any`
      - Exemplo: remova `\\blei\\b` para não ativar modo-legislação só porque a frase contém “lei”
    - **Ajustar gatilhos de NESH**:
      - No bloco `"id": "nesh_direto"`, edite `match_any` (ex: adicionar sinônimos)
    - **Trocar o arquivo de regras via ENV**:
      - Defina `INTENT_POLICY_RULES_PATH=/caminho/para/outro_rules.json`
    - **Dica**: os padrões são regex; lembre que em JSON precisa escapar barra (`\\b`, `\\s`, etc.)
- ✅ **Refatoração do PrecheckService (19/12/2025)**: Lógica extraída para serviços modulares especializados:
  - `EmailPrecheckService` (`services/email_precheck_service.py`) - Prechecks de email
  - `ProcessoPrecheckService` (`services/processo_precheck_service.py`) - Prechecks de processos (situação, follow-up)
  - `NcmPrecheckService` (`services/ncm_precheck_service.py`) - Prechecks de NCM
  - `processo_helpers.py` (`services/utils/processo_helpers.py`) - Helpers para detectar perguntas de painel e follow-ups
  - Código mais modular e testável, mantendo a mesma ordem de prioridade e comportamento
- ✅ **Regras de Contexto de Processo (19/12/2025)**: Sistema agora segue regras claras sobre `processo_atual`:
  - NUNCA assume processo padrão fixo
  - `processo_atual` só é salvo quando processo é mencionado explicitamente
  - Perguntas de painel (ex: "como estão os MV5?") NUNCA usam `processo_atual`
  - Follow-ups (ex: "e a DI?") usam `processo_atual` apenas se não for painel e não houver processo explícito
  - Documentado em `docs/MANUAL_COMPLETO.md` (versão 1.6)
- ✅ **Executor de tools dedicado**: `ToolExecutor` (`services/tool_executor.py`) como camada fina sobre o `ToolRouter`, removendo essa responsabilidade direta do `ChatService`.
- ✅ **DUIMP detalhada completa (SQL Server)**: `_buscar_duimp_completo` em `sql_server_processo_schema.py` agora busca corretamente situação, canal consolidado, impostos pagos e histórico de situações diretamente do SQL Server (database `Make`, schema `Duimp.dbo.*`). Mapeamento documentado em `docs/MAPEAMENTO_SQL_SERVER.md`.
- ✅ **Contexto de sessão melhorado**: `PrecheckService` agora só usa contexto quando a mensagem não tem processo/categoria explícito e não é palavra-chave especial (NCM, extrato, criar DUIMP). Comando `reset` limpa contexto persistente corretamente.
- ✅ **PTAX no cabeçalho da UI**: Exibição em tempo real da PTAX de venda para registro hoje vs amanhã (dia útil anterior), ajudando na decisão de quando registrar.
- ✅ **Análise cambial em "prontos para registro"**: `listar_processos_liberados_registro` agora inclui análise de impacto cambial (PTAX hoje vs amanhã) para ajudar na decisão de registro.
- ✅ **Correção: Nome do navio no relatório de averbação (17/12/2025)**: Relatório de averbação agora busca o nome do navio corretamente do SQL Server (tabela `Di_Transporte`, campo `nomeVeiculo`) antes de consultar a API bilhetada. Prioridade de busca: SQL Server → API (evita custos desnecessários). Documentação atualizada em `docs/MAPEAMENTO_SQL_SERVER.md`.
- ✅ **Recuperação de contexto**: Script `recuperar_contexto.py` criado para recuperar histórico de conversas e contexto de sessão do banco de dados, útil para restaurar estado do agente após falhas.
- ✅ **Correção: Relatório "como estão os X?" (19/12/2025)**: Relatório agora mostra corretamente processos que chegaram sem DI/DUIMP usando `listar_processos_liberados_registro` (todos os processos, não apenas hoje). Formatação completa documentada no README.md.
- ✅ **Relatório de Importações Normalizado por FOB (23/12/2025)**: Novo serviço `RelatorioFobService` para gerar relatórios de importações com valores normalizados para FOB (Free On Board), considerando INCOTERMs (FOB, CIF, CFR). Suporta DI (via VMLD - Frete - Seguro) e DUIMP (FOB direto). Integrado via `MessageIntentService` e `PrecheckService` para detecção automática de intenções.
- ✅ **Relatório de Averbações melhorado (23/12/2025)**: Query SQL refatorada para alinhar com relatório FOB, usando `make.dbo.PROCESSO_IMPORTACAO` como ponto de partida. Filtros de data expandidos (dataHoraDesembaraco → dataHoraSituacaoDi → dataHoraRegistro). Integrado via `MessageIntentService` para detecção automática de intenções.
- ✅ **Streaming de Respostas (05/01/2026)**: Novo endpoint `/api/chat/stream` que envia respostas da IA em tempo real usando Server-Sent Events (SSE). Melhora significativamente a experiência do usuário, mostrando respostas conforme são geradas, em vez de aguardar a resposta completa.
- ✅ **Notícias Siscomex via RSS + Notificações Automáticas (18/01/2026)**:
  - ✅ **Coleta automática** de notícias dos dois feeds oficiais (Importação + Sistemas) e armazenamento no SQLite (`noticias_siscomex`)
  - ✅ **Notificação automática** na UI (com TTS) quando surgem notícias novas (tipo `noticia_siscomex`, processo `SISCOMEX`)
  - ✅ **Agendamento** via `APScheduler` (job a cada 2 horas) em `services/scheduled_notifications_service.py`
  - ✅ **Tool nova**: `listar_noticias_siscomex` (retorna Importação + Sistemas em seções separadas, com título/data/link)
  - ✅ **Dependência**: `feedparser` (ver `requirements.txt`)
  - ✅ **Refatoração alinhada**: schema em `services/noticias_siscomex_schema.py` + acesso via `services/repositories/noticia_repository.py` + `services/agents/sistema_agent.py`
- ✅ **UX: Links clicáveis + SSE robusto (18/01/2026)**:
  - ✅ URLs diretas (`https://...`) viram links clicáveis no chat (frontend)
  - ✅ Parser SSE do frontend reforçado para suportar eventos longos (evita “Pensando…” infinito / mensagem vazia em respostas grandes)
- ✅ **Assistants API com File Search para Legislação (05/01/2026)**: Integração com OpenAI Assistants API para busca semântica de legislação usando RAG (Retrieval-Augmented Generation). Permite buscas inteligentes que entendem contexto e significado, não apenas palavras-chave. Documentação completa em `docs/ASSISTANTS_API_LEGISLACAO.md`.
- ✅ **Notificações de Erros do SQL Server (05/01/2026)**: Sistema agora notifica automaticamente o usuário quando há problemas de conexão com o SQL Server (timeout, DNS, falha de conexão). Notificações aparecem na UI e são deduplicadas para evitar spam.
- ✅ **Cálculo Automático de Impostos após TECwin (05/01/2026)**: Novo serviço `CalculoImpostosService` que permite calcular impostos de importação (II, IPI, PIS, COFINS) automaticamente após consulta de NCM no TECwin. As alíquotas são salvas no contexto da sessão e podem ser usadas para cálculos posteriores. Suporta cálculo completo com CIF, bases de cálculo corretas e formatação educativa passo a passo.
- ✅ **Code Interpreter para Cálculos com Explicação (06/01/2026)**: Integração com Code Interpreter da OpenAI (via Responses API) para cálculos de impostos e outros cálculos complexos com explicação detalhada passo a passo. Permite ao usuário pedir cálculos com explicação usando linguagem natural (ex: "calcule os impostos explicando", "calcule os impostos mostrando as fórmulas"). Sistema híbrido: cálculos rápidos usam Python local, cálculos com explicação usam Code Interpreter. Documentação completa em `docs/CODE_INTERPRETER_CALCULO_IMPOSTOS.md` e `docs/COMO_ACIONAR_CODE_INTERPRETER.md`.
- ✅ **Integração com Santander Open Banking (06/01/2026)**: Integração completa e independente com API do Santander Open Banking para consulta de extratos bancários, saldos e listagem de contas. Sistema detecta automaticamente a primeira conta disponível quando não especificada. Consulta saldo real da conta via API e exibe junto com movimentações do período. Versão 100% independente - código integrado ao projeto, não depende de diretório externo. Documentação completa em `docs/INTEGRACAO_SANTANDER.md`.
- ✅ **Transferências TED via Santander (12/01/2026)**: Implementação completa de transferências TED via API de Pagamentos do Santander, totalmente isolada da API de Extratos. Inclui: criação de workspaces, iniciar/efetivar/consultar/listar TEDs, suporte a certificados .pfx para mTLS, validações completas (CPF/CNPJ, descrição, workspace). **⚠️ IMPORTANTE:** Testado com sucesso no sandbox. Para produção, configure credenciais e certificados de produção. **Erros comuns evitados:** Descrição limitada a 30 caracteres, CPF válido obrigatório, workspace PAYMENTS com TED ativado. Documentação completa em `docs/IMPLEMENTACAO_TED_SANTANDER_FINAL.md`.
- ✅ **Integração com Banco do Brasil (06/01/2026)**: Integração completa com API de Extratos do Banco do Brasil. Suporta consulta de extratos bancários, saldos e movimentações. Sistema de criação de cadeia completa de certificados para APIs mTLS (quando necessário). Documentação completa em `docs/INTEGRACAO_BANCO_BRASIL.md` incluindo processo passo a passo para criar cadeia de certificados.
- ✅ **Sincronização de Extratos Bancários para SQL Server (07/01/2026)**: Sistema completo de sincronização de extratos bancários do Banco do Brasil e **Santander** (08/01/2026) para o banco de dados SQL Server (`mAIke_assistente`). Inclui: tabela `MOVIMENTACAO_BANCARIA`, detecção automática de duplicatas usando hash SHA-256, detecção automática de processos nas descrições, endpoints de API para sincronização manual, e UI para sincronização bancária. Suporta múltiplas contas configuradas via variáveis de ambiente. **Santander:** Detecção automática de conta, suporte a múltiplos formatos de data, descrição completa (transactionName + historicComplement).
- ✅ **Catálogo de Despesas Padrão (07/01/2026)**: Sistema completo de catalogação de despesas padrão com 23 tipos de despesa pré-cadastrados (Frete Internacional, Seguro, AFRMM, Multas, Taxas Siscomex, etc.). Inclui tabelas `TIPO_DESPESA`, `LANCAMENTO_TIPO_DESPESA` (relacionamento N:N), e `PLANO_CONTAS` (preparada para integração futura). Script SQL disponível em `scripts/criar_catalogo_despesas.sql`.
- ✅ **Sistema de Conciliação Bancária (07/01/2026)**: Sistema completo de conciliação bancária que permite classificar lançamentos vinculando-os a tipos de despesa e processos. Suporta múltiplas classificações por lançamento (ex: um único pagamento pode cobrir várias despesas de processos diferentes). Inclui endpoints de API e UI com modais para conciliação. Documentação completa em `docs/CATALOGO_DESPESAS_PADRAO.md`.
- ✅ **Acesso Direto do mAIke ao Banco de Dados (07/01/2026)**: O mAIke agora pode consultar movimentações bancárias diretamente do SQL Server através da nova tool `consultar_movimentacoes_bb_bd`. Permite consultas filtradas por agência, conta, período, processo, tipo de movimentação e valor. Integrado com `BancoBrasilAgent` para consultas inteligentes.
- ✅ **UI/UX Redesign - Menu Drawer (07/01/2026)**: Redesign completo da interface substituindo múltiplos botões no header por um menu drawer lateral elegante. Sistema permite que o mAIke abra menus e modais específicos via comandos de voz/texto (ex: "maike menu", "maike quero conciliar banco"). Interface mais limpa e humanizada.
  - **Menu lateral (drawer)**: Menu deslizante da direita com animação suave, overlay escuro, fecha com ESC ou clicando no overlay
  - **Detecção de comandos de voz/texto**: Comandos como "maike menu", "maike quero conciliar banco", "maike quero sincronizar banco", "maike quero importar legislação", "maike configurações" são detectados antes do processamento pela IA para resposta rápida
  - **Header simplificado**: Um único botão de menu (☰) substitui todos os outros, interface focada no chat
  - **Menu organizado por categorias**: Financeiro (Sincronizar Extratos, Conciliação Bancária), Documentos (Importar Legislação), Sistema (Configurações, Consultas Pendentes), Ajuda (O que posso fazer?)
- ✅ **Sistema de Fallback de Tools (14/01/2026)**: Sistema robusto de fallback em camadas para execução de tools, com dois tipos de fallback (roteamento vs interno) e proteções contra loops infinitos. Implementa 4 regras críticas: inicialização de `_fallback_attempted`, roteamento explícito baseado em `fallback_to`, prevenção de recursão em handlers legados, e detecção de loop compatível com múltiplos formatos. **⚠️ IMPORTANTE:** Ver seção "🔄 Sistema de Fallback de Tools" no README para regras críticas. Documentação completa em `AGENTS.md`.
  - ✅ **Estabilização (14/01/2026)**: `ToolExecutionService.executar_tool()` retorna `None` quando não há handler, evitando “dict vazio de fallback” e reduzindo regressões quando trechos do `ChatService` são alterados.
  - **Design responsivo**: Transições suaves, hover effects, gradiente no header, max-width: 90vw em mobile

- ✅ **Refatoração adicional do ChatService (15/01/2026)**:
- ✅ **`services/chat_service.py` caiu para ~4.999 linhas** (19/01/2026) — removidos blocos grandes de legado dentro do `_executar_funcao_tool` e **fallback legado desabilitado** (agora retorna erro controlado se for atingido)
  - ✅ Extração do bloco “detecção proativa quando não há tool_calls / resposta string” para `services/chat_service_no_toolcalls_proactive_detection.py`
  - ✅ Streaming “sem flash”: limpeza de frases problemáticas aplicada **durante** o streaming em `services/chat_service_streaming_mixin.py` (o texto indesejado não aparece nem momentaneamente)
  - ✅ Confirmação de email mais resiliente: quando o preview existe em memória/histórico, mas não há PendingIntent, o sistema reidrata/cria o PendingIntent e confirma no mesmo “enviar/sim” (`services/handlers/confirmation_handler.py`)
  - ✅ Estabilidade do Cursor: desabilitada análise/indexação Python no workspace em `.vscode/settings.json` para evitar crash (code 5)

### 🔜 Próximos passos planejados (atualizado 15/01/2026)

**🎯 PRIORIDADE 1 - Continuar Refatoração do `chat_service.py`:**

### 📊 Status do Refatoramento (Atualizado 15/01/2026)

**Progresso:** ✅ grande redução já feita; ainda há legado/remanescentes, mas o arquivo já está bem menor e mais estável.

#### ✅ **Concluído:**
- ✅ **Passo 1:** ConfirmationHandler + EmailSendCoordinator
- ✅ **Passo 2:** ToolExecutionService
- ✅ **Passo 4:** Todos os handlers e utils (6 sub-passos)
- ✅ **Passo 6:** Relatórios JSON - **TODAS AS 4 FASES COMPLETAS** (10/01/2026)
  - ✅ Fase 1: Estrutura JSON
  - ✅ Fase 2: Formatação com IA
  - ✅ Fase 3: JSON como fonte da verdade
  - ✅ Fase 4: Remoção de formatação manual (~725 linhas removidas)
- ✅ **Passo 3.5:** Construção de prompt e tool calls - **FASE 3.5.1 E 3.5.2 COMPLETAS** (12/01/2026)
  - ✅ Fase 3.5.1: Construção de prompt completo (~600-800 linhas extraídas)
  - ✅ Fase 3.5.2: Processamento de tool calls (~400-600 linhas extraídas)
  - ✅ Integração completa no `chat_service.py`
  - ✅ 14 métodos especializados criados no `MessageProcessingService`
  - ✅ 8 testes automatizados passando
 - ✅ **Extrações adicionais (15/01/2026)**:
   - `services/chat_service_no_toolcalls_proactive_detection.py` (detecção proativa quando a IA retorna string)
   - Streaming “sem flash” (limpeza incremental) em `services/chat_service_streaming_mixin.py`

#### ⏳ **Pendente:**
- ⏳ **Limpeza final:** remover apenas o que ainda sobrou de legado **quando houver confiança total** (mantendo fallback seguro).
- ⏳ **Testes:** Completar testes de integração end-to-end

#### 📈 **Estatísticas:**
- **Arquivo atual:** `services/chat_service.py` com **~4.999 linhas** (19/01/2026)
- **Novo arquivo:** `message_processing_service.py` com **~1.636 linhas** (lógica organizada)
- **Meta:** < 5.000 linhas (falta ~790 linhas — idealmente removendo mais legado, mas sempre com estabilidade)
- **Benefícios:** Modularidade, testabilidade, reutilização, manutenibilidade (ver `docs/BENEFICIOS_REFATORAMENTO_PASSO_3_5.md`)

#### 📋 **Documentações:**
- `docs/BENEFICIOS_REFATORAMENTO_PASSO_3_5.md` ⭐ **NOVO (12/01/2026)** - Análise completa dos benefícios do Passo 3.5
- `docs/O_QUE_FALTA_PASSO_3_5.md` - O que falta para finalizar o Passo 3.5 (inclui seção sobre remoção de código antigo)
- `docs/PASSO_3_5_PLANO_IMPLEMENTACAO.md` - Plano detalhado do Passo 3.5
- `docs/REFATORACAO_RESUMO_COMPLETO.md` - Resumo completo do progresso
- `docs/PASSO_6_FASE4_COMPLETO.md` - Documentação da conclusão do Passo 6
- `PROMPT_AMANHA.md` ⭐ **ATUALIZADO (12/01/2026)** - Seção "🗑️ Código Antigo a Remover" adicionada
- Ver mais em `docs/REFATORACAO_PROGRESSO.md`

#### 🎯 **Próximos Passos:**
1. **Documentação:** manter `README.md`, `AGENTS.md` e `PROMPT_AMANHA.md` sempre batendo com o código (principalmente mapa do sistema)
2. **Testes:** completar testes de integração end-to-end
3. **Limpeza:** remover legado restante (com backup + testes obrigatórios)

#### ✅ Já Migrado:
- ✅ `DuimpService` - Criação e gestão de DUIMPs
- ✅ `VinculacaoService` - Vinculação de documentos a processos
- ✅ `ProcessoListService` - Listagem de processos (completo)
  - `listar_processos_por_categoria` ✅
  - `listar_processos_por_eta` ✅
  - `listar_processos_por_situacao` ✅
  - `listar_processos_com_pendencias` ✅
  - `listar_todos_processos_por_situacao` ✅
- ✅ `ConsultaService` - Operações de consulta
  - `consultar_ce_maritimo` ✅
  - `verificar_atualizacao_ce` ✅
  - `consultar_processo_consolidado` ✅
- ✅ `DocumentoService` - Consulta de documentos
- ✅ `ProcessoRepository` - Repositório unificado
- ✅ `ProcessoStatusService` - Consulta de status
- ✅ `ConsultasBilhetadasService` - Gestão de consultas bilhetadas
  - `listar_consultas_bilhetadas_pendentes` ✅
  - `aprovar_consultas_bilhetadas` ✅
  - `rejeitar_consultas_bilhetadas` ✅
  - `executar_consultas_aprovadas` ✅
- ✅ `NCMService` - Operações com NCM
  - `buscar_ncms_por_descricao` ✅
  - `sugerir_ncm_com_ia` ✅
  - `detalhar_ncm` ✅
  - `buscar_nota_explicativa_nesh` ✅
  - `baixar_nomenclatura_ncm` ✅
- ✅ `EmailPrecheckService` - Prechecks especializados em email (19/12/2025)

**Progresso (atualizado 19/01/2026):** `services/chat_service.py` está em **~4.999 linhas** ✅ (meta: <5.000)

#### 🔄 Próximas Migrações:
1. **Migrar funções restantes do `chat_service.py`**:
   - Focar em orquestração, não em lógica de negócio
   - Manter apenas coordenação entre serviços e agents

3. **Reduzir `chat_service.py`**:
  - Meta: Reduzir de ~5.790 linhas para <5.000 linhas (**atingido em 19/01/2026: ~4.999 linhas**)
   - Focar em orquestração, não em lógica de negócio
   - Manter apenas coordenação entre serviços e agents

#### 📊 Ampliar a camada analítica
- Novos relatórios determinísticos simples:
  - Processos desembaraçados por mês/categoria
  - Pendências por categoria
  - Atrasos por navio/fornecedor
  - Taxa de conversão (chegada → registro → desembaraço)
- Conectar essas consultas ao sistema de consultas salvas/`saved_queries_service`.
- Expandir o `analytics_service` com mais agregações e métricas de negócio.

**🎯 PRIORIDADE 2 - Continuar refatoração do `db_manager.py` (anti-monólito):**
- ✅ **Atualização (19/01/2026):** `db_manager.py` está em **~9.956 linhas** (antes: ~14k) com extrações incrementais mantendo compatibilidade por wrappers.
- ✅ `obter_dados_documentos_processo` começou a ser desmontado em handlers por domínio:
  - `services/documentos_processo_prep.py` (prep/ordenação + fallback SQL Server)
  - `services/ce_documento_handler.py` + `services/ce_pendencias.py` (CE)
  - `services/cct_documento_handler.py` (CCT)
  - `services/di_documento_handler.py` (DI)
- ✅ **Atualização (19/01/2026):** DUIMP também foi extraído para `services/duimp_documento_handler.py`.
- ✅ `gerar_json_consolidado_processo` foi fatiado em builders por domínio:
  - `services/processo_consolidado_init.py` / `services/processo_consolidado_ce.py` / `services/processo_consolidado_cct.py`
  - `services/processo_consolidado_di.py` / `services/processo_consolidado_duimp.py` / `services/processo_consolidado_finalize.py`

---


```
Chat-IA-Independente/
├── app.py                          # Flask app independente
├── ai_service.py                   # Serviço de IA
├── db_manager.py                   # SQLite local (tabelas/migrações). ⚠️ Refatoração incremental em andamento: façade + handlers extraídos (meta: reduzir monólito)
├── duimp_auth.py                   # Autenticação Portal Único
├── duimp_request.py                # Requisições HTTP para Portal Único (mTLS)
├── integracomex_auth.py            # Autenticação Integra Comex
├── requirements.txt                # Dependências Python
├── .env                            # Variáveis de ambiente (você cria)
├── README.md                       # Esta documentação
├── PROMPT_AMANHA.md                # Prompt para continuidade do trabalho
├── services/
│   ├── chat_service.py             # Orquestração principal (modo normal). ✅ Hoje ~4.999 linhas (19/01/2026)
│   ├── chat_service_streaming_mixin.py # Streaming SSE (/api/chat/stream) - inclui sanitização DURANTE streaming (sem “flash”)
│   ├── chat_service_no_toolcalls_proactive_detection.py # Detecção proativa quando IA retorna string (sem tool_calls)
│   ├── chat_service_email_extraction_fallback.py # Fallback legado: extração de email a partir de texto livre da IA
│   ├── chat_service_forced_prechecks_toolcalling.py # Prechecks forçados (modo tool-calling) extraídos do ChatService
│   ├── chat_service_forced_precheck_extrato_processo.py # Precheck: “extrato do processo” (inferir DI vs DUIMP)
│   ├── chat_service_toolcalling_legacy_fallback.py # Fallback legado: tool-calling sem MessageProcessingService
│   ├── chat_service_legacy_toolcalls_proactive_fixes.py # Correções/deteções pós tool-calls (fluxo legado)
│   ├── consulta_service.py          # Consultas de documentos/processos
│   ├── processo_list_service.py     # Listagem de processos
│   ├── vinculacao_service.py        # Vinculação de documentos
│   ├── documento_service.py         # Consulta de documentos
│   ├── processo_status_service.py   # Consulta de status
│   ├── duimp_service.py            # Criação e gestão de DUIMPs
│   ├── consultas_bilhetadas_service.py # Gestão de consultas bilhetadas
│   ├── precheck_service.py         # Prechecks determinísticos (orquestração)
│   ├── email_precheck_service.py   # Prechecks especializados em email
│   ├── processo_precheck_service.py # Prechecks especializados em processos
│   ├── ncm_precheck_service.py     # Prechecks especializados em NCM
│   ├── email_builder_service.py    # Montagem de emails estruturados
│   ├── email_service.py            # Serviço de envio de email
│   ├── email_send_coordinator.py   # ✅ NOVO (09/01/2026): Coordenador de envio de emails (ponto único)
│   ├── message_processing_service.py # ✅ NOVO (12/01/2026): Processamento completo de mensagens - construção de prompt e tool calls (Passo 3.5 completo)
│   ├── tool_execution_service.py   # ✅ NOVO (09/01/2026): Execução centralizada de tools
│   ├── documentos_processo_prep.py # ✅ NOVO (19/01/2026): Prep do `obter_dados_documentos_processo` (base docs + ordenação + DI prioritária do CE)
│   ├── ce_documento_handler.py     # ✅ NOVO (19/01/2026): Handler de CE (cache/Kanban/DUIMP do documentoDespacho/itens/alertas)
│   ├── ce_pendencias.py            # ✅ NOVO (19/01/2026): Regras de pendência CE (AFRMM/frete)
│   ├── cct_documento_handler.py    # ✅ NOVO (19/01/2026): Handler de CCT (país por IATA + pendências + alertas)
│   ├── di_documento_handler.py     # ✅ NOVO (19/01/2026): Handler de DI (cache + SQL Server + id_importacao)
│   ├── relatorio_fob_service.py    # Relatório de importações normalizado por FOB
│   ├── relatorio_averbacoes_service.py # Relatório de averbações
│   ├── message_intent_service.py   # Detecção de intenções de mensagens
│   ├── assistants_service.py       # Assistants API com File Search para legislação
│   ├── calculo_impostos_service.py # Cálculo automático de impostos após TECwin
│   ├── responses_service.py        # Responses API com Code Interpreter
│   ├── santander_service.py        # Integração com Santander Open Banking (Extratos)
│   ├── santander_payments_service.py # ✅ NOVO (12/01/2026): Integração com Santander Payments (TED, Boletos, PIX)
│   ├── banco_brasil_service.py     # Integração com Banco do Brasil (Extratos)
│   ├── banco_brasil_payments_service.py # ✅ NOVO (13/01/2026): Integração com Banco do Brasil Payments (Pagamentos em Lote)
│   ├── banco_sincronizacao_service.py # ✅ NOVO (07/01/2026): Sincronização de extratos bancários (BB + Santander)
│   ├── banco_concilacao_service.py # ✅ NOVO (07/01/2026): Conciliação bancária
│   ├── banco_concilacao_service_v2.py # ✅ NOVO (13/01/2026): Conciliação bancária V2 (em validação) - NOTA: Este é um serviço da V1, não confundir com a V2 separada
│   ├── extrato_bancario_pdf_service.py # Geração de PDF de extratos bancários (formato contábil)
│   ├── boleto_parser.py            # ✅ NOVO (13/01/2026): Parser de boletos (extração de dados de PDF)
│   ├── boleto_parser_vision.py     # ✅ NOVO (13/01/2026): Parser de boletos usando OpenAI Vision API
│   ├── notificacao_service.py      # Notificações de erros do sistema
│   ├── tool_router.py              # Roteador de tools
│   ├── tool_definitions.py         # Definições das tools
│   ├── tool_executor.py            # Executor de tools (legado - manter compatibilidade)
│   ├── prompt_builder.py           # Construtor de prompts
│   ├── learned_rules_service.py    # Gerenciamento de regras aprendidas
│   ├── context_service.py          # Gerenciamento de contexto de sessão
│   ├── analytical_query_service.py # Execução segura de consultas SQL
│   ├── saved_queries_service.py    # Gerenciamento de consultas salvas
│   ├── ncm_service.py              # Operações com NCM
│   ├── handlers/                   # ✅ NOVO (09/01/2026): Handlers especializados (refatoração)
│   │   ├── confirmation_handler.py # Handler de confirmações (email, DUIMP)
│   │   ├── email_improvement_handler.py # Handler de melhorias de email
│   │   ├── context_extraction_handler.py # Handler de extração de contexto
│   │   └── response_formatter.py   # Formatter de respostas
│   ├── utils/                      # ✅ NOVO (09/01/2026): Utilitários extraídos
│   │   ├── entity_extractors.py    # Extração de entidades (processo, CE, CCT, DI, DUIMP)
│   │   ├── question_classifier.py  # Classificação de perguntas
│   │   ├── email_utils.py          # Utilitários de email
│   │   ├── data_sources_checker.py # Verificador de fontes de dados
│   │   ├── extractors.py           # Extração de dados (legado)
│   │   ├── validators.py           # Validação de parâmetros
│   │   └── formatters.py           # Formatação de respostas (legado)
│   ├── use_cases/                  # Casos de uso
│   │   └── enviar_email_classificacao_ncm_use_case.py
│   └── agents/                     # Agents especializados
│       ├── base_agent.py
│       ├── processo_agent.py
│       ├── duimp_agent.py
│       ├── ce_agent.py
│       ├── di_agent.py
│       ├── cct_agent.py
│       ├── legislacao_agent.py     # Busca semântica de legislação
│       ├── calculo_agent.py        # Cálculos com Code Interpreter
│       ├── santander_agent.py      # Operações bancárias do Santander (Extratos + Pagamentos)
│       └── banco_brasil_agent.py   # Operações bancárias do Banco do Brasil (Extratos + Pagamentos)
├── templates/
│   └── chat-ia-isolado.html        # Interface do chat
├── tests/                          # Testes automatizados
│   ├── test_email_flows_golden.py  # ✅ NOVO (09/01/2026): Testes golden para fluxos de email
│   ├── test_message_processing_service_fase2.py # ✅ NOVO (09/01/2026): Testes do MessageProcessingService
│   ├── test_email_precheck_smoke.py # Testes de fumaça para EmailPrecheckService
│   ├── test_question_classifier.py # ✅ NOVO (09/01/2026): Testes do QuestionClassifier
│   ├── test_email_utils.py         # ✅ NOVO (09/01/2026): Testes do EmailUtils
│   ├── scripts/
│   │   ├── test_consulta_service.py
│   │   ├── test_processo_list_service.py
│   │   └── test_servicos_migrados.py
│   └── README.md
├── utils/                          # Utilitários e integrações
│   ├── banco_brasil_api.py         # Cliente API Banco do Brasil (Extratos)
│   ├── banco_brasil_payments_api.py # ✅ NOVO (13/01/2026): Cliente API Banco do Brasil (Pagamentos em Lote)
│   ├── santander_api.py            # Cliente API Santander (Extratos)
│   ├── santander_payments_api.py   # ✅ NOVO (12/01/2026): Cliente API Santander (Pagamentos)
│   ├── sql_server_adapter.py       # Adaptador SQL Server
│   ├── portal_proxy.py             # Proxy Portal Único
│   ├── integracomex_proxy.py       # Proxy Integra Comex
│   └── [outros utilitários...]
├── docs/                           # Documentação
│   ├── API_DOCUMENTATION.md        # Documentação completa da API
│   ├── ASSISTANTS_API_LEGISLACAO.md # Documentação Assistants API
│   ├── REFATORACAO_RESUMO_COMPLETO.md # ✅ NOVO (10/01/2026): Resumo completo do refatoramento
│   ├── REFATORACAO_PROGRESSO.md    # ✅ NOVO (09/01/2026): Progresso detalhado do refatoramento
│   ├── REFATORACAO_PONTO_PARADA.md # ✅ NOVO (09/01/2026): Ponto de parada do refatoramento
│   ├── PASSO_3_PLANO.md            # ✅ NOVO (09/01/2026): Plano do Passo 3 (MessageProcessingService)
│   ├── PASSO_3_PROGRESSO.md        # ✅ NOVO (09/01/2026): Progresso do Passo 3
│   ├── PASSO_4_PLANO.md            # ✅ NOVO (09/01/2026): Plano do Passo 4 (Handlers/Utils)
│   ├── PROBLEMA_RELATORIOS_STRING_JSON.md # ✅ NOVO (10/01/2026): Análise do problema de relatórios
│   ├── MELHORIA_RELATORIOS_JSON.md # ✅ NOVO (09/01/2026): Proposta de melhoria (JSON + IA)
│   ├── EMAIL_SEND_COORDINATOR.md   # ✅ NOVO (09/01/2026): Documentação do EmailSendCoordinator
│   ├── TESTES_GOLDEN_TESTS.md      # ✅ NOVO (09/01/2026): Documentação dos testes golden
│   ├── COMO_TESTAR_QUESTION_CLASSIFIER.md # ✅ NOVO (09/01/2026): Como testar QuestionClassifier
│   ├── COMO_TESTAR_EMAIL_UTILS.md  # ✅ NOVO (09/01/2026): Como testar EmailUtils
│   ├── ENTITY_EXTRACTORS_ARQUITETURA.md # ✅ NOVO (10/01/2026): Arquitetura do EntityExtractors
│   ├── ARQUITETURA_MAIKE_CORRIGIDA.md # ✅ NOVO (10/01/2026): Arquitetura corrigida (ativos/históricos)
│   ├── BUGS_EMAIL_PENDENTES.md     # ✅ NOVO (09/01/2026): Bugs conhecidos de email (para correção após refatoramento)
│   ├── EMAIL_DRAFTS_ANALISE.md     # ✅ NOVO (09/01/2026): Análise do sistema de drafts de email
│   ├── PAYLOAD_EMAIL_AZURE.md      # ✅ NOVO (09/01/2026): Estrutura do payload de email Azure
│   ├── MELHORIAS_FLUIDEZ_EMAIL.md  # ✅ NOVO (09/01/2026): Melhorias de fluidez do sistema de email
│   └── [mais documentações...]     # Veja seção "Documentação Adicional" abaixo
```

---

## 🗺️ Mapa do Sistema

### Arquitetura de Processamento de Mensagens

```
┌─────────────────────────────────────────────────────────────┐
│                    POST /api/chat                            │
│                    (app.py)                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              ChatService.processar_mensagem()                │
│              (services/chat_service.py)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  1) Comandos de interface (antes de tudo)                    │
│     MessageIntentService.detectar_comando_interface()        │
│     (services/message_intent_service.py)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  2) Confirmações (antes de qualquer outro precheck)          │
│     ConfirmationHandler.processar_confirmacao_*              │
│     + PendingIntentService (SQLite é fonte da verdade)       │
│     (services/handlers/confirmation_handler.py)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  3) Prechecks determinísticos                                │
│     PrecheckService.tentar_responder_sem_ia()                │
│     (services/precheck_service.py)                           │
│     - inclui EmailPrecheckService / ProcessoPrecheck / NCM   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  4) IA + tool-calling (quando necessário)                    │
│     MessageProcessingService                                 │
│     (services/message_processing_service.py)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  5) Execução de tools (camadas)                              │
│     ToolExecutionService (handlers extraídos)                │
│       → ToolRouter → Agents                                  │
│       → Fallback legado do ChatService (quando aplicável)    │
└─────────────────────────────────────────────────────────────┘
```

### Serviços Principais

#### Camada de Orquestração
- **`ChatService`**: Serviço principal que orquestra todo o fluxo
- **`PrecheckService`**: Prechecks determinísticos antes da IA (orquestrador)
- **`EmailPrecheckService`**: Prechecks especializados em email
- **`ProcessoPrecheckService`**: Prechecks especializados em processos (situação, follow-up)
- **`NcmPrecheckService`**: Prechecks especializados em NCM
- **`ToolRouter`**: Roteia tool calls para agents
- **`ToolExecutor`**: Executa tools através do router

#### Helpers e Utilitários
- **`processo_helpers.py`**: Helpers para detecção de tipos de perguntas
  - `eh_pergunta_painel()`: Detecta perguntas de painel/visão geral (ex: "como estão os MV5?")
  - `eh_followup_processo()`: Detecta follow-ups de processo (ex: "e a DI?", "e a DUIMP?")
  - Separa claramente perguntas de painel vs processo específico vs follow-up

#### Camada de Negócio
- **`ProcessoAgent`**: Operações com processos
- **`DuimpAgent`**: Operações com DUIMP
- **`CeAgent`**: Operações com CE
- **`DiAgent`**: Operações com DI
- **`CctAgent`**: Operações com CCT
- **`SantanderAgent`**: ✅ NOVO (06/01/2026): Operações bancárias do Santander (extratos, saldos, contas)

#### Camada de Serviços
- **`ProcessoRepository`**: Repositório unificado de processos
- **`ProcessoStatusService`**: Consulta de status
- **`DuimpService`**: Criação e gestão de DUIMPs
- **`EmailBuilderService`**: Montagem de emails
- **`EmailService`**: Envio de emails
- **`NCMService`**: Operações com NCM
- **`ConsultaService`**: Consultas de documentos
- **`ConsultasBilhetadasService`**: Gestão de consultas bilhetadas
- **`RelatorioFobService`**: ✅ NOVO (23/12/2025): Relatório de importações normalizado por FOB (DI/DUIMP)
- **`RelatorioAverbacoesService`**: ✅ NOVO (16/12/2025): Relatório de averbações (processos com DI registrada)
- **`MessageIntentService`**: ✅ NOVO (23/12/2025): Detecção centralizada de intenções de mensagens
- **`SantanderService`**: ✅ NOVO (06/01/2026): Integração com API do Santander Open Banking

#### Camada de Infraestrutura
- **`db_manager.py`**: Gerenciamento SQLite
- **`sql_server_adapter.py`**: Adaptador SQL Server
- **`portal_proxy.py`**: Proxy Portal Único
- **`integracomex_proxy.py`**: Proxy Integra Comex
- **`santander_api.py`**: ✅ NOVO (06/01/2026): Cliente API do Santander Open Banking (independente)

### 🧩 Mapa de Serviços (visão curta)

| Serviço | Responsabilidade | Arquivos principais | Tools/Integrações relacionadas |
|---|---|---|---|
| `ChatService` | Orquestra o fluxo do chat (precheck → IA → tools → resposta) | `services/chat_service.py` | chama `PrecheckService`, `MessageProcessingService`, `ToolExecutionService`, `ToolRouter` |
| `PrecheckService` | Regras determinísticas antes da IA (comandos críticos) | `services/precheck_service.py` | email, pagamentos (“continue o pagamento”), extratos, etc. |
| `MessageProcessingService` | Construção de prompt + tool-calling (refactor do ChatService) | `services/message_processing_service.py` | usa `PromptBuilder` e chama tool-calling |
| `ToolExecutionService` | Execução centralizada de tools + handlers extraídos (evita fallback legado) | `services/tool_execution_service.py` | email, NCM/NESH, valores, consultas salvas/analíticas, consultas bilhetadas, `calcular_impostos_ncm` |
| `ConfirmationHandler` | Confirmações “sim/enviar/pagar” de forma consistente | `services/handlers/confirmation_handler.py` | usa `PendingIntentService` |
| `PendingIntentService` | Persistência de ações pendentes (fonte da verdade) | `services/pending_intent_service.py`, `db_manager.py` | email/DUIMP/pagamentos (TTL, idempotência) |
| `ToolRouter` | Mapeia `tool_name → agent` | `services/tool_router.py` | encaminha para `services/agents/*` |
| Agents | Implementação por domínio | `services/agents/*.py` | processos, DI/DUIMP/CE/CCT, legislação, bancos |
| `EmailPrecheckService` | Detecta comandos de email e gera previews | `services/email_precheck_service.py` | cria pending intent via `ConfirmationHandler` |
| `EmailDraftService`/`EmailSendCoordinator` | Drafts e envio idempotente | `services/email_draft_service.py`, `services/email_send_coordinator.py` | Microsoft Graph (Email) |
| `SantanderService` / `SantanderPaymentsService` | Extratos e Pagamentos Santander (separados) | `services/santander_service.py`, `services/santander_payments_service.py` | `utils/santander_api.py`, `utils/santander_payments_api.py` |
| `BancoBrasilService` / `BancoBrasilPaymentsService` | Extratos e Pagamentos BB (separados) | `services/banco_brasil_service.py`, `services/banco_brasil_payments_service.py` | `utils/banco_brasil_api.py`, `utils/banco_brasil_payments_api.py` |
| Banco (sync/conc.) | Sincronização + conciliação no SQL Server | `services/banco_sincronizacao_service.py`, `services/banco_concilacao_service*.py` | tabelas `MOVIMENTACAO_BANCARIA`, etc. |
| Legislação | Busca/Importação/RAG | `services/legislacao_service.py`, `services/assistants_service.py`, `services/responses_service.py` | Assistants API / Responses API |

### 🧰 Mapa de Tools (o “que existe” e onde roda)

**📌 Objetivo desta seção:** te dar um mapa **com critério** para você decidir quais tools são **core** (uso diário / risco alto) e quais são **edge** (baixo uso provável / candidatas a sair do tool-calling).

**⚠️ Importante (intermitência):** a OpenAI limita `tools` a **128**. Quando o projeto passa disso, `services/tool_definitions.py` **deduplica + remove “nice-to-have” + trunca**. Isso pode fazer tool-calling ficar intermitente (uma tool “some” do array em certas chamadas).

- **Mapa completo (com critérios + snapshot por agent)**: `docs/MAPA_TOOLS.md`

**Visão rápida (ordem de execução):**

- **Precheck determinístico (comandos críticos)**: `services/precheck_service.py`
  - Ex.: pagar AFRMM / continuar pagamento / extratos / emails “ver/ler” etc.
- **Definições de tools (LLM)**: `services/tool_definitions.py` (dedupe/truncagem para respeitar 128)
- **Execução centralizada (handlers extraídos / evita fallback)**: `services/tool_execution_service.py`
  - Para lista completa: ver `_initialize_handlers()` e `docs/MAPA_TOOLS.md`
  - **Confirmação persistente (SQLite)**: `services/pending_intent_service.py` + `services/handlers/confirmation_handler.py`
- **Roteamento por agent**: `services/tool_router.py` (mapa `tool_name → agent`)
- **Implementação por domínio**: `services/agents/*.py`

#### Tools por Agent (ToolRouter)

- **`processo`** (`services/agents/processo_agent.py`)
  - `listar_processos`, `listar_processos_por_categoria`, `listar_processos_por_situacao`, `listar_todos_processos_por_situacao`
  - `listar_processos_por_eta`, `listar_processos_por_navio`, `listar_processos_em_dta`, `listar_processos_liberados_registro`
  - `listar_processos_com_pendencias`, `listar_processos_com_duimp`, `consultar_status_processo`, `consultar_processo_consolidado`, `consultar_despesas_processo`
  - `obter_dashboard_hoje`, `fechar_dia`
  - `gerar_relatorio_importacoes_fob`, `gerar_relatorio_averbacoes`
  - `consultar_contexto_sessao`, `buscar_secao_relatorio_salvo`, `buscar_relatorio_por_id`
  - `obter_ajuda`

- **`duimp`** (`services/agents/duimp_agent.py`)
  - `criar_duimp`, `verificar_duimp_registrada`, `obter_dados_duimp`, `obter_extrato_pdf_duimp`, `vincular_processo_duimp`

- **`ce`** (`services/agents/ce_agent.py`)
  - `consultar_ce_maritimo`, `verificar_atualizacao_ce`, `listar_processos_com_situacao_ce`, `obter_extrato_ce`

- **`di`** (`services/agents/di_agent.py`)
  - `obter_dados_di`, `obter_extrato_pdf_di`, `vincular_processo_di`

- **`cct`** (`services/agents/cct_agent.py`)
  - `consultar_cct`, `obter_extrato_cct`

- **`legislacao`** (`services/agents/legislacao_agent.py`)
  - `buscar_legislacao`, `buscar_trechos_legislacao`, `buscar_em_todas_legislacoes`
  - `buscar_legislacao_responses`, `buscar_legislacao_assistants`
  - `importar_legislacao_preview`, `confirmar_importacao_legislacao`, `buscar_e_importar_legislacao`

- **`calculo`** (`services/agents/calculo_agent.py`)
  - `calcular_percentual`

- **`santander`** (`services/agents/santander_agent.py`)
  - **Extratos**: `listar_contas_santander`, `consultar_extrato_santander`, `consultar_saldo_santander`, `gerar_pdf_extrato_santander`
  - **Workspaces/Pagamentos**: `listar_workspaces_santander`, `criar_workspace_santander`
  - **TED**: `iniciar_ted_santander`, `efetivar_ted_santander`, `consultar_ted_santander`, `listar_teds_santander`
  - **Boletos**: `processar_boleto_upload`, `iniciar_bank_slip_payment_santander`, `efetivar_bank_slip_payment_santander`, `consultar_bank_slip_payment_santander`, `listar_bank_slip_payments_santander`
  - **Barcode**: `iniciar_barcode_payment_santander`, `efetivar_barcode_payment_santander`, `consultar_barcode_payment_santander`, `listar_barcode_payments_santander`
  - **PIX**: `iniciar_pix_payment_santander`, `efetivar_pix_payment_santander`, `consultar_pix_payment_santander`, `listar_pix_payments_santander`
  - **IPVA**: `consultar_debitos_renavam_santander`, `iniciar_vehicle_tax_payment_santander`, `efetivar_vehicle_tax_payment_santander`, `consultar_vehicle_tax_payment_santander`, `listar_vehicle_tax_payments_santander`
  - **Impostos por campos**: `iniciar_tax_by_fields_payment_santander`, `efetivar_tax_by_fields_payment_santander`, `consultar_tax_by_fields_payment_santander`, `listar_tax_by_fields_payments_santander`

- **`banco_brasil`** (`services/agents/banco_brasil_agent.py`)
  - **Extratos**: `consultar_movimentacoes_bb_bd`, `consultar_extrato_bb`, `gerar_pdf_extrato_bb`
  - **Pagamentos em lote**: `iniciar_pagamento_lote_bb`, `consultar_lote_bb`, `listar_lotes_bb`

- **`mercante`** (`services/agents/mercante_agent.py`)
  - `executar_pagamento_afrmm`
  - ⚠️ Observação: como existe limite de 128 tools, o pagamento AFRMM **não deve depender** de “IA escolher a tool”; por isso existe rota determinística no `PrecheckService` para comandos como “pague a afrmm do XXX.0001/26”.

#### Tools não migradas (fallback no ChatService)

Estas tools aparecem no `tool_definitions.py`, mas **não estão mapeadas no `ToolRouter`** (agent `None`) e ainda dependem do **fallback do `ChatService`**:

- ✅ **Atualização (19/01/2026):** As tools que já têm handler no `ToolExecutionService` foram mapeadas no `ToolRouter` para o agent `sistema` (delegação), eliminando o “`None` enganoso”.

**Fallback real atual:** **0 tools** ✅

- ✅ **Atualização (19/01/2026 - Fase 2):** `adicionar_categoria_processo`, `listar_categorias_disponiveis`, `gerar_resumo_reuniao`, `vincular_processo_cct` e `desvincular_documento_processo` agora têm handlers no `ToolExecutionService` e estão mapeadas no `ToolRouter` para o agent `sistema` (delegação via `SistemaAgent`).

---

## ⚙️ Configuração

### **1. Criar arquivo `.env`**

O arquivo `.env` precisa ser criado na raiz do projeto com todas as variáveis de ambiente.

**Opção 1: Copiar do Projeto Original (Recomendado)**

```bash
# Copiar estrutura do .env do projeto original
cp /Users/helenomaffra/Documents/GitHub/Projeto-DUIMP/.env /Users/helenomaffra/Documents/GitHub/Chat-IA-Independente/.env

# Depois editar e adicionar variáveis do SQL Server no final
```

**Opção 2: Criar Manualmente**

Crie o arquivo `.env` na raiz do projeto com o template abaixo:

### **Template Completo do `.env`:**

```bash
# =============================================================================
# CHAT IA INDEPENDENTE - CONFIGURAÇÃO
# =============================================================================

# -----------------------------------------------------------------------------
# 1. IA (OpenAI/Anthropic)
# -----------------------------------------------------------------------------
DUIMP_AI_ENABLED=true
DUIMP_AI_PROVIDER=openai
DUIMP_AI_API_KEY=sk-...                    # ⚠️ COPIAR DO PROJETO ORIGINAL
DUIMP_AI_MODEL=gpt-3.5-turbo          # Padrão: gpt-3.5-turbo (pode usar gpt-4o-mini)
DUIMP_AI_TIMEOUT=60.0

# -----------------------------------------------------------------------------
# 2. SQL SERVER (Do Protótipo "CHAT IA")
# -----------------------------------------------------------------------------
SQL_SERVER=172.16.10.8\SQLEXPRESS          # ⚠️ COPIAR DO PROJETO ORIGINAL
SQL_USERNAME=sa                             # ⚠️ COPIAR DO PROJETO ORIGINAL
SQL_PASSWORD=Z1mb@bu3BD                    # ⚠️ COPIAR DO PROJETO ORIGINAL
SQL_DATABASE=Make                           # ⚠️ COPIAR DO PROJETO ORIGINAL (ou Serpro, Comex, Pedidos)

# 🧠 Nota importante (DUIMP: canal + impostos)
# - O adapter SQL Server (`utils/sql_server_adapter.py`) usa por padrão o database do .env (`SQL_DATABASE`).
# - Para DUIMP detalhada (situação, canal e impostos), o código usa SEMPRE o database **Make**
#   nas queries de `_buscar_duimp_completo` em `services/sql_server_processo_schema.py`,
#   acessando o schema `Duimp.dbo.*`.
# - Se mudar o database padrão no .env, mantenha `Make` explicitamente nas chamadas de DUIMP
#   ou ajuste com muito cuidado todas as queries de DUIMP.
# - Sempre que alterar queries de DUIMP, TESTE direto em Python, por exemplo:
#   ```bash
#   cd Chat-IA-Independente
#   python3 - << 'EOF'
#   from utils.sql_server_adapter import get_sql_adapter
#   from services.sql_server_processo_schema import _buscar_duimp_completo
#   sql = get_sql_adapter()
#   res = _buscar_duimp_completo(sql, "25BR00002369283", "VDM.0004/25")
#   print(res)
#   EOF
#   ```
#   Assim você garante que a função está trazendo:
#   - Situação correta da DUIMP (`DESEMBARACADA_AGUARDANDO_ENTREGA_CARGA`, etc.)
#   - Canal correto (`VERDE`, `AMARELO`, `VERMELHO`, …)
#   - Lista de impostos pagos (II, IPI, PIS, COFINS, TAXA_UTILIZACAO) com valores e datas,
#   antes de depender da IA para formatar a resposta.

# -----------------------------------------------------------------------------
# 3. PORTAL ÚNICO (DUIMP, CCT, CATP)
# -----------------------------------------------------------------------------
DUIMP_CERT_PFX=./certs/cert.pfx            # ⚠️ COPIAR CERTIFICADO DO ORIGINAL
DUIMP_CERT_PASSWORD=sua_senha_certificado  # ⚠️ COPIAR DO PROJETO ORIGINAL
DUIMP_ROLE_TYPE=IMPORTADOR                 # ⚠️ COPIAR DO PROJETO ORIGINAL
DUIMP_AMBIENTE=validacao                   # validacao ou producao
PUCOMEX_BASE_URL=https://portalunico.siscomex.gov.br/portal

# Cache de tokens Portal Único
DUIMP_CACHE_PATH=.duimp_token_cache.json
DUIMP_FORCE_REFRESH=false

# -----------------------------------------------------------------------------
# 4. INTEGRA COMEX (CE, DI) - API BILHETADA
# -----------------------------------------------------------------------------
INTEGRACOMEX_CONSUMER_KEY=...              # ⚠️ COPIAR DO ORIGINAL
INTEGRACOMEX_CONSUMER_SECRET=...           # ⚠️ COPIAR DO ORIGINAL
INTEGRACOMEX_ENV=prod                      # val ou prod
INTEGRACOMEX_CERT_PFX=./certs/cert.pfx     # Usa mesmo da DUIMP
INTEGRACOMEX_CERT_PASSWORD=...             # Mesma da DUIMP

# Cache de tokens Integra Comex
INTEGRACOMEX_TOKEN_CACHE=.integracomex_token_cache.json
INTEGRACOMEX_FORCE_REFRESH=false

# -----------------------------------------------------------------------------
# 5. BANCO DE DADOS SQLITE (Cache de APIs)
# -----------------------------------------------------------------------------
DB_PATH=chat_ia.db

# -----------------------------------------------------------------------------
# 6. FLASK (Servidor Web)
# -----------------------------------------------------------------------------
PORT=5001
FLASK_DEBUG=false
FLASK_ENV=production

# -----------------------------------------------------------------------------
# 7. EMAIL (Envio de Resumos/Briefings)
# -----------------------------------------------------------------------------
EMAIL_SMTP_SERVER=smtp.gmail.com              # Servidor SMTP (Gmail, Outlook, etc.)
EMAIL_SMTP_PORT=587                           # Porta SMTP (587 para TLS, 465 para SSL)
EMAIL_SENDER=seu-email@gmail.com              # Email remetente
EMAIL_PASSWORD=sua-senha-app                  # Senha do email ou senha de app (Gmail requer senha de app)
# ⚠️ IMPORTANTE: Para Gmail, use "Senha de App" (não a senha normal)
# Como criar: https://support.google.com/accounts/answer/185833

# -----------------------------------------------------------------------------
# 8. OUTRAS CONFIGURAÇÕES
# -----------------------------------------------------------------------------
FLASK_BASE_URL=http://localhost:5001
```

### **🔑 Onde Copiar Cada Valor:**

#### **Do Projeto Original (`Projeto-DUIMP`):**
- `DUIMP_AI_API_KEY` - Chave OpenAI
- `DUIMP_CERT_PASSWORD` - Senha do certificado
- `DUIMP_ROLE_TYPE` - Tipo de papel (geralmente IMPORTADOR)
- `INTEGRACOMEX_CONSUMER_KEY` - Chave Integra Comex
- `INTEGRACOMEX_CONSUMER_SECRET` - Secret Integra Comex

#### **Do Protótipo "CHAT IA":**
- `SQL_SERVER` - Servidor SQL Server
- `SQL_USERNAME` - Usuário SQL Server
- `SQL_PASSWORD` - Senha SQL Server
- `SQL_DATABASE` - Nome do banco (Make, Comex, Serpro, Pedidos)

**Arquivo de referência:** `/Users/helenomaffra/CHAT IA/backend/shared/config.py`

### **2. Instalar Node.js e Dependências**

**⚠️ IMPORTANTE:** O projeto usa Node.js para conectar ao SQL Server (solução para compatibilidade com Mac).

```bash
# Verificar se Node.js está instalado
node --version

# Se não estiver, instalar:
# macOS: brew install node
# Ou baixar de: https://nodejs.org/

# Instalar dependências Node.js
cd Chat-IA-Independente
npm install
```

Isso instalará a biblioteca `mssql` necessária para conexão SQL Server.

### **3. Copiar Certificado**

```bash
# Criar pasta certs (se não existir)
mkdir -p /Users/helenomaffra/Documents/GitHub/Chat-IA-Independente/certs

# Copiar certificado do projeto original
cp /Users/helenomaffra/Documents/GitHub/Projeto-DUIMP/certs/cert.pfx \
   /Users/helenomaffra/Documents/GitHub/Chat-IA-Independente/certs/cert.pfx
```

---

## 🚀 Como Usar

### **1. Instalar Dependências Python**

```bash
cd Chat-IA-Independente
pip install -r requirements.txt
```

### **2. Instalar Dependências Node.js**

```bash
npm install
```

Isso instala a biblioteca `mssql` necessária para conexão SQL Server (solução para Mac).

### **3. Configurar `.env`**

Crie o arquivo `.env` conforme instruções acima e preencha todas as senhas.

### **4. Copiar Certificado**

Copie o certificado conforme instruções acima.

### **5. Testar Conexão SQL Server (Opcional)**

```bash
# Testar via Node.js
npm run test-sql

# Ou diretamente
node utils/sql_server_node.js test
```

### **4. Iniciar Servidor**

```bash
python app.py
```

Você deve ver:
```
🚀 Iniciando Chat IA Independente na porta 5001...
✅ Banco de dados SQLite inicializado
✅ ChatService inicializado
 * Running on http://0.0.0.0:5001
```

### **5. Acessar Interface**

Abra no navegador:
```
http://localhost:5001/chat-ia
```

---

## 🧪 Como Testar

### **1. Iniciar o App**

```bash
cd Chat-IA-Independente
python app.py
```

### **2. Acessar Interface**

Abra no navegador:
```
http://localhost:5001/chat-ia
```

### **3. Testes de Serviços Migrados**

```bash
# Testar ConsultaService
python tests/scripts/test_consulta_service.py

# Testar ProcessoListService
python tests/scripts/test_processo_list_service.py

# Testar todos os serviços migrados
python tests/scripts/test_servicos_migrados.py
```

**⚠️ IMPORTANTE:** Antes de executar, ajuste os valores nos scripts (CEs, processos, categorias) para valores que existem no seu sistema. Veja `tests/README.md` para mais detalhes.

### **4. Testes Básicos no Chat**

#### **A. Testar Interface:**
- Verifique se a interface carrega corretamente
- Teste enviar uma mensagem simples

#### **B. Testar Chat Básico:**
- "Olá, como você pode me ajudar?"
- "O que você faz?"
- "Liste os processos de importação"

#### **C. Testar Funcionalidades:**

##### **Sobre Fontes de Dados (NOVO):**
- "Quais fontes de dados estão disponíveis?"
- "Verificar fontes de dados"
- "Estou conectado ao SQL Server?"
- "Quais processos históricos temos?" (mAIke informa se SQL Server não estiver disponível)

##### **Sobre Vendas (Make/Spalla) (NOVO):**
**Relatório por NF (lista de documentos):**
- "vendas vdm em janeiro 2026"
- "vendas rastreador janeiro 26"
- "vendas por nf de hikvision em janeiro/2026"
- "vendas alho chines em janeiro 2025"

**Total agregado (sem listar NFs):**
- "quanto vendeu de rastreador em janeiro 2026?"
- "total de vendas de vdm em janeiro 2026"

**Refino iterativo (sem reconsultar SQL legado):**  
Depois de rodar um relatório por NF, você pode mandar follow-ups como:
- "agora filtra só o cliente AC BARBEITO"
- "só devolução"
- "só ICMS"
- "só dia 22/01/2026"
- "ordena por valor e top 10"

**Curva ABC (em cima do relatório por NF da tela):**
- "faz curva abc por cliente"
- "curva abc por centro"
- "curva abc por empresa"
- "curva abc por operação"

##### **Sobre Processos:**
- "Liste os processos de importação"
- "Quais processos têm DUIMP?"
- "Mostre o status do processo ALH.0174/25" (se tiver processo no banco)
- "Liste processos ALH"
- "Processos com pendências"

##### **Sobre DUIMP:**
- "Criar duimp do VDM.0004/25" - Cria DUIMP automaticamente (com confirmação)
- "Qual a situação da DUIMP 25BR00001928777?"
- "Liste as DUIMPs criadas"
- Suporta criação para processos com CE (marítimo) e CCT (aéreo)

##### **Sobre CE (Conhecimento de Embarque):**
- "Extrato CE VDM.0004/25" - Gera extrato completo do CE
- "Como está o CE 132505284200462?"
- "CEs com bloqueios"
- Busca automática de processo vinculado ao CE

##### **Sobre DI (Declaração de Importação):**
- "Extrato DI ALH.0174/25" - Gera PDF do extrato da DI
- "Consulte a DI 2521440840"
- "Qual o status da DI 2521440840?"

##### **Sobre NCM:**
- "Qual o NCM para alho fresco?"
- "Sugira NCM para produtos agrícolas"
- "classifique relogio de pulso" (exemplo de busca híbrida completa)

**🔍 Busca Híbrida de NCM (Restaurada - 14/01/2026):**

O sistema usa uma **busca híbrida** em camadas para classificar produtos:

**Exemplo: "classifique relogio de pulso"**

1. **Cache Local** (`buscar_ncms_por_descricao`)
   - Busca direta no banco SQLite local
   - Se encontrar resultados suficientes, retorna imediatamente ✅

2. **DuckDuckGo** (`_buscar_web_para_produto`)
   - Se cache não retornou resultados, busca na web
   - Identifica categoria genérica (ex: "iPhone" → "telefone celular")
   - Valida NCMs mencionados na web contra cache oficial
   - Extrai informações contextuais do produto
   - ✅ **Híbrido aplicado na NESH**: quando a web identifica uma categoria genérica, o sistema usa essa categoria (ex: "telefone celular") para buscar na NESH por descrição (melhora muito para termos modernos que não aparecem literalmente na NESH)

3. **Top 5 NCMs do Cache** (baseado na categoria identificada)
   - Lista priorizada de NCMs similares do cache local
   - Prioriza NCMs com feedbacks históricos corretos
   - Limita a 5-10 candidatos mais relevantes

4. **Modelo de IA** (`ai_service.sugerir_ncm_por_descricao`)
   - Classifica entre os top 5 NCMs do cache
   - **NUNCA inventa NCMs** - só escolhe entre os candidatos válidos
   - Usa contexto da web (DuckDuckGo) para melhor precisão

5. **Match na NESH** (`buscar_notas_explicativas_nesh_por_descricao`)
   - Busca nota explicativa NESH por descrição do produto
   - Busca nota explicativa NESH por NCM sugerido
   - Valida se NCM sugerido faz sentido com a NESH encontrada
   - Se houver divergência, ajusta confiança e adiciona aviso
   - ✅ **Fonte atual da NESH**: SQLite (`chat_ia.db`, tabela `nesh_chunks`) – mais leve e rápido do que carregar JSON gigante em memória
   - ✅ **Fallback seguro**: se o SQLite não estiver populado, o sistema ainda consegue cair para `nesh_chunks.json` (quando existir)
   - ✅ **Opcional (28/01/2026): busca semântica HF/FAISS na NESH**
     - Se habilitado, a busca por descrição prioriza um índice FAISS (embeddings) e cai automaticamente no SQLite se não estiver pronto.
     - Arquivos:
       - `services/nesh_hf_service.py`
       - `scripts/build_nesh_hf_index.py` (gera `/app/data/nesh_hf_index/index.faiss` + `meta.jsonl`)

6. **Resposta Formatada**
   - NCM sugerido com confiança
   - Top 5 alternativos do cache
   - Nota explicativa NESH (quando disponível)
   - Validação cruzada (NCM ↔ NESH)
   - Informações da web (quando usadas)

**⚠️ IMPORTANTE:** Se der problema novamente, verificar:
- `services/ncm_precheck_service.py` → método `precheck_pergunta_ncm()`
- `services/ncm_service.py` → método `sugerir_ncm_com_ia()`
- Garantir que DuckDuckGo está disponível (`DDG_AVAILABLE = True`)
- Verificar se busca de NESH está sendo executada (logs devem mostrar "📚 Buscando NESH")
- ✅ Verificar se a NESH foi importada para SQLite:
  - `python3 scripts/importar_nesh_sqlite.py --json /Users/helenomaffra/CHAT-IA-BIG/nesh_chunks.json`
  - `sqlite3 chat_ia.db "select count(1) from nesh_chunks;"`
- ✅ (Opcional) Gerar índice HF/FAISS da NESH (no Docker):
  - `docker compose exec web python3 scripts/build_nesh_hf_index.py`
- Busca inteligente com contexto web e validação

##### **Sobre Cálculo de Impostos (NOVO - 05/01/2026):**
- "tecwin 84145110" → Consulta alíquotas no TECwin
- "calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283" → Calcula automaticamente II, IPI, PIS, COFINS
- As alíquotas são salvas automaticamente no contexto após consulta TECwin
- Cálculo completo com explicação passo a passo (CIF, bases de cálculo, fórmulas)

##### **Sobre CCT (Conhecimento de Transporte Aéreo):**
- "Extrato CCT GLT.0043/25" - Gera extrato do CCT
- "Como está o CCT MIA4683?" - Consulta por AWB
- Suporta processos aéreos (modal "Aéreo")

##### **Sobre Santander Open Banking (NOVO - 06/01/2026):**
- "extrato santander" - Consulta extrato bancário (detecta conta automaticamente)
- "extrato santander de 30/12/25" - Extrato de um dia específico
- "extrato santander de 01/12/25 a 31/12/25" - Extrato de um período
- "saldo santander" - Consulta saldo atual da conta
- "saldo santander de 30/12/25" - Saldo em uma data específica
- "listar contas santander" - Lista todas as contas disponíveis
- **Gerar PDF:** "gerar pdf do extrato santander" ou "pdf do extrato" - Gera PDF no formato contábil padrão (Data, Histórico, Crédito, Débito, Saldo)
- **Sincronizar para SQL Server:** Via UI "Sincronizar Extratos" → Selecionar Santander → Sincronizar
- Sistema detecta automaticamente a primeira conta quando não especificada
- Exibe saldo real da conta junto com movimentações do período
- **✅ NOVO (08/01/2026):** Descrição completa de lançamentos (transactionName + historicComplement) na tela de conciliação
- **✅ NOVO (08/01/2026):** Suporte a múltiplos formatos de data (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY)

##### **Sobre Banco do Brasil (NOVO - 06/01/2026):**
- "extrato bb" ou "extrato banco do brasil" - Consulta extrato bancário
- "extrato bb de 30/12/25" - Extrato de um dia específico
- "extrato bb de 01/12/25 a 31/12/25" - Extrato de um período
- "extrato bb conta 2" - Consulta segunda conta configurada
- "extrato bb conta 43344" - Consulta conta específica
- "saldo bb" - Consulta saldo atual da conta
- **Gerar PDF:** "gerar pdf do extrato bb" ou "pdf do extrato banco do brasil" - Gera PDF no formato contábil padrão (Data, Histórico, Crédito, Débito, Saldo)
- Sistema usa OAuth 2.0 Client Credentials (mais simples que mTLS)
- **Múltiplas Contas:** ✅ Para adicionar novas contas do BB na mesma agência, **NÃO é necessária nova autorização**. Basta configurar `BB_TEST_CONTA_2` no `.env` e usar "conta 2" ou o número da conta diretamente.
- **Cadeia de Certificados:** Para APIs mTLS (ex: Pagamentos), veja `docs/INTEGRACAO_BANCO_BRASIL.md` - seção "Cadeia Completa de Certificados"

##### **Sobre Fontes de Dados (NOVO - Versão 1.3.0):**
- "Quais fontes de dados estão disponíveis?" - Mostra status de todas as fontes
- "Verificar fontes de dados" - Verifica e mostra status atualizado
- "Estou conectado ao SQL Server?" - Verifica conexão SQL Server
- "Quais processos históricos temos?" - mAIke informa se SQL Server não estiver disponível e oferece alternativas

##### **Sobre Legislação (NOVO - Versão 1.7.0):**
- "O que fala sobre perdimento em importação?" - Busca semântica usando Assistants API (RAG)
- "Explique sobre multas em importação" - Busca contextualizada em todas as legislações
- "Qual a base legal para penalidades?" - Busca inteligente que combina múltiplas legislações
- Suporta busca tradicional (SQLite) e busca semântica (Assistants API) - a IA escolhe automaticamente
- **Atualização de legislações:** Re-executar `python scripts/configurar_assistants_legislacao.py` após importar novas legislações
- **Custos:** Upload de arquivos é GRATUITO, apenas o uso do File Search pode ter custo
- Documentação completa: `docs/ASSISTANTS_API_LEGISLACAO.md`

### **4. Verificar Logs**

No terminal, você verá logs de:
- ✅ Conexões ao banco
- ✅ Consultas às APIs
- ✅ Erros (se houver)
- ⚠️ Erro de SQL Server (não é crítico)

---

## 📊 Quais Processos a IA Acessa?

### **⚠️ SITUAÇÃO ATUAL:**

A IA atualmente busca processos de **múltiplas fontes possíveis:**

#### **🆕 Sistema de Verificação de Fontes de Dados (Versão 1.3.0)**

O sistema agora verifica automaticamente quais fontes de dados estão disponíveis:

- **SQLite (Local/Offline)** ✅
  - Sempre disponível se o arquivo `chat_ia.db` existir
  - Funciona OFFLINE (não precisa de rede do escritório)
  - Contém processos recentes do Kanban, cache de CEs/CCTs

- **SQL Server (Rede do Escritório)** ⚠️
  - Disponível apenas quando conectado à rede do escritório (VPN ou presencial)
  - Contém processos históricos/antigos
  - Precisa estar na rede do escritório para funcionar

- **API Kanban** 🌐
  - Dados atualizados em tempo real
  - Funciona se a URL estiver configurada no `.env`

- **API Portal Único** 🌐
  - Dados de DUIMP, DI em tempo real
  - Funciona se as credenciais estiverem configuradas no `.env`

**Como a mAIke se comporta:**
- Quando você pergunta sobre "processos históricos", ela verifica se SQL Server está disponível
- Se não estiver, ela informa claramente e oferece alternativas (SQLite ou APIs)
- Use o comando "verificar fontes de dados" ou "quais fontes estão disponíveis?" para ver status completo

### **Fontes de Dados Disponíveis:**

#### **1. SQLite Local (`chat_ia.db`)** ✅ **RECOMENDADO PARA OFFLINE**

**Tabelas usadas:**
- `processos` - Lista de processos
- `processo_documentos` - Vínculos entre processos e documentos (CE, DI, DUIMP, CCT)
- `processos_importacao` - Dados completos dos processos

**Status:** 
- ⚠️ **VAZIO inicialmente** (projeto novo)
- Precisa ser populado antes de usar

**Como funciona:**
- O `ProcessoAgent` busca processos através de funções do `db_manager.py`:
  - `listar_processos()` - Busca da tabela `processos`
  - `listar_processos_por_categoria()` - Busca processos por categoria (ALH, VDM, etc.)
  - `obter_dados_documentos_processo()` - Busca dados consolidados (CE, DI, DUIMP, CCT)

**Como popula:**
- Via API externa (se existir): `POST /api/int/processos-importacao`
- Via importação manual no SQLite
- Via sincronização com SQL Server (futuro - quando adaptado)

#### **2. SQL Server (Protótipo "CHAT IA")** ⚠️ **REQUER REDE DO ESCRITÓRIO**

**Status:**
- ✅ **Sistema de verificação implementado** - detecta automaticamente se está disponível
- ⚠️ **Disponível apenas quando conectado à rede do escritório** (VPN ou presencial)
- ⚠️ Se você estiver offline, o sistema informa claramente e oferece alternativas

**Conteúdo:**
- Todos os processos reais (ALH.0174/25, VDM.0003/25, etc.)
- Vínculos entre processos e documentos (CE, DI, DUIMP)
- Processos históricos/antigos

**Como funciona:**
- O sistema verifica automaticamente na inicialização se SQL Server está disponível
- Se não estiver, a mAIke informa ao usuário e oferece usar SQLite (processos recentes) ou APIs
- Adaptador criado (`utils/sql_server_adapter.py`) e integrado ao sistema de verificação

### **🔍 Como Verificar Quais Processos Estão Disponíveis:**

#### **Opção 1: Perguntar ao Chat**
```
"Liste os processos de importação"
```

**Resultado esperado (se SQLite estiver vazio e SQL Server offline):**
```
⚠️ SQL Server não está disponível (você está fora da rede do escritório). 
Processos históricos/antigos estão no SQL Server e não estão acessíveis no momento.

Posso consultar processos recentes usando SQLite (dados locais, funciona offline) 
ou buscar via APIs externas. Quer que eu mostre os processos disponíveis no SQLite?
```

**O que isso significa:**
- ✅ O chat IA está funcionando corretamente
- ✅ A mAIke detectou que SQL Server não está disponível
- ✅ A mAIke informou claramente a limitação e ofereceu alternativas
- ⚠️ Processos históricos não estão acessíveis offline (normal)

#### **Opção 2: Verificar Diretamente no Banco SQLite**

```bash
cd Chat-IA-Independente

# Abrir SQLite
sqlite3 chat_ia.db

# Dentro do SQLite, verificar:
.tables                           # Lista todas as tabelas
SELECT COUNT(*) FROM processos;   # Contar processos
SELECT COUNT(*) FROM processo_documentos;  # Contar vínculos
SELECT * FROM processos LIMIT 5;  # Ver primeiros processos
.exit                             # Sair
```

### **💡 Como Ter Acesso aos Processos:**

#### **Opção A: Resolver Conexão SQL Server (Recomendado)**

1. **Verificar configuração no `.env`:**
   ```bash
   SQL_SERVER=172.16.10.8\SQLEXPRESS
   SQL_USERNAME=sa
   SQL_PASSWORD=Z1mb@bu3BD
   SQL_DATABASE=Make
   ```

2. **Testar conexão:**
   - O app já tenta conectar na inicialização
   - Se der erro, verificar se o SQL Server está acessível na rede

3. **Adaptar ProcessoAgent:**
   - Modificar `ProcessoAgent` para usar `sql_server_adapter` quando SQL Server estiver disponível
   - Manter fallback para SQLite

#### **Opção B: Popular SQLite Manualmente**

Criar script para copiar processos do SQL Server para SQLite:
```python
# scripts/sync_processos.py
from utils.sql_server_adapter import SQLServerAdapter
from db_manager import salvar_processo, vincular_documento_processo

# 1. Buscar processos do SQL Server
adapter = SQLServerAdapter()
processos = adapter.execute_query("SELECT * FROM processos", "Make")

# 2. Copiar para SQLite
for proc in processos:
    salvar_processo(proc)
    # Vincular documentos...
```

#### **Opção C: Importar Via API Externa**

Se você tiver uma API que envia processos:
```
POST /api/int/processos-importacao
{
  "processo_referencia": "ALH.0174/25",
  "categoria": "ALH",
  ...
}
```

### **📋 O Que Funciona SEM Processos no Banco:**

Mesmo sem processos no SQLite, você pode testar:

1. ✅ **Chat básico** - Perguntas gerais sobre o sistema
2. ✅ **Consultas diretas a APIs** - CE, DI, DUIMP (se autenticado)
   - "Consulte o CE 132505284200462"
   - "Consulte a DI 2521440840"
3. ✅ **Sugestão de NCM** - Busca por descrição de produto
   - "Qual o NCM para alho fresco?"
4. ✅ **Tool calling** - Sistema de ferramentas funcionando
5. ✅ **Interface e formatação** - UI e Markdown

### **⚠️ O Que NÃO Funciona Sem Processos:**

- ❌ "Liste os processos de importação" → Retornará vazio
- ❌ "Mostre o status do processo ALH.0174/25" → Processo não encontrado
- ❌ "Processos com pendências" → Nenhum processo
- ❌ "Quais processos têm DUIMP?" → Nenhum processo

**Nota:** Você pode consultar CE/DI diretamente pelo número, mas não conseguirá buscar processos pela referência (ALH.0174/25) se não estiverem no banco.

---

## 🔍 Sistema de Verificação de Fontes de Dados (NOVO)

### **O que é?**

Sistema implementado na **Versão 1.3.0** que verifica automaticamente quais fontes de dados estão disponíveis e informa ao usuário quando uma fonte não está acessível.

### **Fontes Verificadas:**

1. **SQLite (Local/Offline)** 💾
   - Verifica se o arquivo `chat_ia.db` existe
   - Conta quantas tabelas estão disponíveis
   - Funciona OFFLINE (não precisa de rede)

2. **SQL Server (Rede do Escritório)** 🗄️
   - Testa conexão com query simples (`SELECT 1`)
   - Detecta se você está na rede do escritório
   - Informa se está offline ou se há erro de conexão

3. **API Kanban** 🌐
   - Verifica se variável `KANBAN_API_URL` está configurada no `.env`

4. **API Portal Único** 🌐
   - Verifica se variáveis `PORTAL_UNICO_API_URL` e `PORTAL_UNICO_API_TOKEN` estão configuradas

### **Como Usar:**

#### **1. Verificar Status Manualmente:**

No chat, digite:
```
"verificar fontes de dados"
```
ou
```
"quais fontes de dados estão disponíveis?"
```

A mAIke mostrará:
- ✅ Fontes disponíveis
- ❌ Fontes indisponíveis (com motivo)
- 💡 Recomendações baseadas no status

#### **2. Comportamento Automático:**

A mAIke detecta automaticamente quando você pede algo que requer SQL Server:

**Exemplo:**
```
Usuário: "Quais processos históricos temos?"

mAIke: "⚠️ SQL Server não está disponível (você está fora da rede do escritório). 
Processos históricos/antigos estão no SQL Server e não estão acessíveis no momento.

Posso consultar processos recentes usando SQLite (dados locais, funciona offline) 
ou buscar via APIs externas. Quer que eu mostre os processos disponíveis no SQLite?"
```

### **Arquivos Relacionados:**

- **`services/utils/data_sources_checker.py`** - Módulo de verificação
  - `verificar_fontes_dados_disponiveis()` - Função principal
  - `formatar_status_fontes_dados()` - Formatação de mensagens

- **`services/chat_service.py`** - Integração
  - Verificação automática na inicialização (`__init__`)
  - Status incluído no contexto do prompt
  - Tool `verificar_fontes_dados` disponível para a mAIke

- **`services/tool_definitions.py`** - Definição da tool
  - Tool `verificar_fontes_dados` adicionada à lista de tools disponíveis

### **Benefícios:**

✅ **Transparência**: Usuário sempre sabe quais fontes estão disponíveis  
✅ **Inteligência**: mAIke oferece alternativas automaticamente  
✅ **Offline-Friendly**: Funciona bem quando você está fora da rede  
✅ **Diagnóstico**: Fácil identificar problemas de conexão  

---

## 🎓 Sistema de Aprendizado e Contexto Persistente (NOVO)

### **O que é?**

Sistema implementado na **Versão 1.4.0** que permite à mAIke aprender com o usuário e manter contexto entre mensagens, tornando a interação mais natural e eficiente.

### **Funcionalidades:**

#### **1. Aprendizado de Regras**

A mAIke pode aprender regras e definições que você ensina:

**Exemplo de Uso:**
```
Você: "usar campo destfinal como confirmação de chegada"
mAIke: [Salva a regra automaticamente]
Você: "quais VDM chegaram?"
mAIke: [Aplica automaticamente: WHERE data_destino_final IS NOT NULL]
```

**Como Funciona:**
- Quando você explica como fazer algo, a mAIke detecta e salva a regra
- Padrões que indicam ensino: "usar campo X como Y", "sempre que fizer Z, use W"
- Regras são salvas no banco SQLite na tabela `regras_aprendidas`
- Regras aparecem automaticamente no prompt da mAIke para aplicação futura

**Arquivos Relacionados:**
- **`services/learned_rules_service.py`** - Módulo principal
  - `salvar_regra_aprendida()` - Salva uma nova regra
  - `buscar_regras_aprendidas()` - Busca regras aplicáveis a um contexto
  - `formatar_regras_para_prompt()` - Formata regras para incluir no prompt
- **`db_manager.py`** - Tabela `regras_aprendidas` criada no `init_db()`
- **`services/tool_definitions.py`** - Tool `salvar_regra_aprendida` adicionada
- **`services/chat_service.py`** - Integração no `_executar_funcao_tool()` e no prompt

**Estrutura da Tabela `regras_aprendidas`:**
```sql
CREATE TABLE regras_aprendidas (
    id INTEGER PRIMARY KEY,
    tipo_regra TEXT NOT NULL,        -- 'campo_definicao', 'regra_negocio', etc.
    contexto TEXT,                    -- 'chegada_processos', 'analise_vdm', etc.
    nome_regra TEXT NOT NULL,        -- Nome amigável da regra
    descricao TEXT NOT NULL,         -- Descrição completa
    aplicacao_sql TEXT,               -- Como aplicar em SQL
    aplicacao_texto TEXT,             -- Como aplicar em texto
    exemplo_uso TEXT,                 -- Exemplo de quando usar
    criado_por TEXT,                  -- user_id ou session_id
    criado_em TIMESTAMP,
    atualizado_em TIMESTAMP,
    vezes_usado INTEGER DEFAULT 0,   -- Contador de uso
    ultimo_usado_em TIMESTAMP,
    ativa BOOLEAN DEFAULT 1           -- Se a regra está ativa
)
```

**Como Debugar/Consertar:**
1. **Ver regras salvas:**
   ```bash
   sqlite3 chat_ia.db
   SELECT * FROM regras_aprendidas WHERE ativa = 1;
   ```
2. **Testar salvar regra manualmente:**
   ```python
   from services.learned_rules_service import salvar_regra_aprendida
   resultado = salvar_regra_aprendida(
       tipo_regra='campo_definicao',
       contexto='chegada_processos',
       nome_regra='destfinal como confirmação',
       descricao='Campo data_destino_final indica chegada',
       aplicacao_sql='WHERE data_destino_final IS NOT NULL'
   )
   ```
3. **Verificar se regras aparecem no prompt:**
   - Ver logs do chat_service.py quando processa mensagem
   - Regras são incluídas automaticamente se houver regras ativas

#### **2. Contexto Persistente de Sessão**

A mAIke mantém contexto entre mensagens da mesma sessão:

**Exemplo de Uso:**
```
Você: "buscar vdm.0004/25"
mAIke: [Busca e mostra dados do processo]
Você: "trazer todos os dados"
mAIke: [Já sabe que é VDM.0004/25 e traz todos os dados]
```

**Como Funciona:**
- Quando você menciona um processo, categoria ou consulta, a mAIke salva esse contexto
- Contexto é salvo por `session_id` (identificador único da sessão)
- Contexto é incluído automaticamente no prompt das próximas mensagens
- Contexto persiste até você limpar ou iniciar nova sessão

**Arquivos Relacionados:**
- **`services/context_service.py`** - Módulo principal
  - `salvar_contexto_sessao()` - Salva contexto de sessão
  - `buscar_contexto_sessao()` - Busca contexto de sessão
  - `formatar_contexto_para_prompt()` - Formata contexto para incluir no prompt
- **`db_manager.py`** - Tabela `contexto_sessao` criada no `init_db()`
- **`services/chat_service.py`** - Integração no `processar_mensagem()` e no prompt
- **`app.py`** - `session_id` é passado do endpoint para o chat_service

**Estrutura da Tabela `contexto_sessao`:**
```sql
CREATE TABLE contexto_sessao (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,         -- ID da sessão (IP ou ID customizado)
    tipo_contexto TEXT NOT NULL,     -- 'processo_atual', 'categoria_atual', etc.
    chave TEXT NOT NULL,              -- Chave do contexto
    valor TEXT NOT NULL,              -- Valor do contexto
    dados_json TEXT,                  -- Dados adicionais em JSON
    criado_em TIMESTAMP,
    atualizado_em TIMESTAMP,
    UNIQUE(session_id, tipo_contexto, chave)
)
```

**Tipos de Contexto:**
- `processo_atual` - Processo mencionado (ex: "VDM.0004/25")
- `categoria_atual` - Categoria em foco (ex: "VDM", "ALH")
- `ultima_consulta` - Última consulta realizada

**Como Debugar/Consertar:**
1. **Ver contexto salvo:**
   ```bash
   sqlite3 chat_ia.db
   SELECT * FROM contexto_sessao WHERE session_id = 'SEU_SESSION_ID';
   ```
2. **Limpar contexto de uma sessão:**
   ```python
   from services.context_service import limpar_contexto_sessao
   limpar_contexto_sessao(session_id='SEU_SESSION_ID')
   ```
3. **Verificar se contexto aparece no prompt:**
   - Ver logs do chat_service.py quando processa mensagem
   - Contexto é incluído automaticamente se houver contexto salvo

#### **3. Melhorias na Comunicação Natural**

A mAIke agora responde de forma mais direta e contextual:

**Melhorias:**
- Respostas mais curtas e naturais (não verbosas)
- Entende contexto implícito das perguntas
- Detecta quando você está testando e responde adequadamente
- Evita repetir informações que você já sabe

**Exemplo:**
```
Antes: "Olá, Heleno! Sim, eu entendo você! Estamos falando sobre os processos da categoria VC, e estou aqui para ajudar com qualquer informação ou análise que você precise sobre eles. Se tiver alguma pergunta específica ou algo que gostaria de consultar, é só me avisar! Estou à disposição. Precisa de mais alguma coisa, Heleno?"

Agora: "Sim, entendo! Estou aqui para ajudar com processos, análises, consultas... O que precisa?"
```

**Arquivos Relacionados:**
- **`services/chat_service.py`** - Instruções melhoradas no `system_prompt` e `user_prompt`
  - Detecção automática de perguntas de teste
  - Instruções para respostas curtas e diretas
  - Exemplos de respostas BOM vs RUIM

**Como Debugar/Consertar:**
1. **Ver instruções no prompt:**
   - Ver `system_prompt` em `chat_service.py` (linha ~7555)
   - Ver `user_prompt` em `chat_service.py` (linha ~8312)
2. **Ajustar instruções:**
   - Modificar seção "COMUNICAÇÃO NATURAL E CONTEXTUAL" no `system_prompt`
   - Modificar seção "INSTRUÇÕES CRÍTICAS DE RESPOSTA" no `user_prompt`
3. **Testar respostas:**
   - Enviar mensagem de teste: "vc me entende?"
   - Verificar se resposta é curta e direta
   - Se não estiver, ajustar instruções no prompt

---

## 📊 Sistema de Consultas Analíticas SQL (NOVO)

### **O que é?**

Sistema implementado na **Versão 1.4.0** que permite à mAIke gerar e executar consultas SQL analíticas baseadas em perguntas em linguagem natural, transformando a mAIke em uma assistente analítica de dados.

### **Funcionalidades:**

#### **1. Consultas Analíticas SQL**

A mAIke pode gerar e executar consultas SQL baseadas em perguntas:

**Exemplo de Uso:**
```
Você: "Quais clientes têm mais processos em atraso em 2025?"
mAIke: [Gera SQL, executa e mostra resultados]
```

**Como Funciona:**
- Você faz uma pergunta em linguagem natural sobre dados
- A mAIke gera uma consulta SQL apropriada
- A consulta é validada (apenas SELECT, sem DDL/DML)
- A consulta é executada no SQL Server (se disponível) ou SQLite (fallback)
- Resultados são formatados e apresentados

**Arquivos Relacionados:**
- **`services/analytical_query_service.py`** - Módulo principal
  - `executar_consulta_analitica()` - Executa consulta SQL de forma segura
  - `validar_sql_seguro()` - Valida se SQL é seguro (apenas SELECT)
  - `aplicar_limit_seguro()` - Aplica LIMIT automaticamente
  - `_executar_no_sql_server()` - Executa no SQL Server
  - `_executar_no_sqlite()` - Executa no SQLite (fallback)
- **`services/tool_definitions.py`** - Tool `executar_consulta_analitica` adicionada
- **`services/chat_service.py`** - Integração no `_executar_funcao_tool()`

**Validações de Segurança:**
- ✅ Apenas comandos SELECT são permitidos
- ✅ DDL (CREATE, DROP, ALTER) são bloqueados
- ✅ DML (INSERT, UPDATE, DELETE) são bloqueados
- ✅ Apenas tabelas permitidas podem ser consultadas
- ✅ LIMIT é aplicado automaticamente (padrão: 100 linhas)
- ✅ Subqueries são permitidas (mas também validadas)

**Tabelas Permitidas (configurável em `analytical_query_service.py`):**
```python
TABELAS_PERMITIDAS = {
    'processos_kanban',
    'duimps',
    'ces_cache',
    'ccts_cache',
    'processos_importacao',
    # ... outras tabelas
}
```

**Como Debugar/Consertar:**
1. **Testar validação SQL:**
   ```python
   from services.analytical_query_service import validar_sql_seguro
   valido, erro = validar_sql_seguro("SELECT * FROM processos")
   print(f"Válido: {valido}, Erro: {erro}")
   ```
2. **Testar execução:**
   ```python
   from services.analytical_query_service import executar_consulta_analitica
   resultado = executar_consulta_analitica("SELECT COUNT(*) FROM processos", limit=10)
   print(resultado)
   ```
3. **Ver logs:**
   - Logs mostram qual fonte foi usada (SQL Server ou SQLite)
   - Logs mostram erros de validação ou execução

#### **2. Consultas Salvas (Relatórios Reutilizáveis)**

A mAIke pode salvar consultas SQL ajustadas como relatórios reutilizáveis:

**Exemplo de Uso:**
```
Você: "Quais clientes têm mais processos em atraso em 2025?"
mAIke: [Gera e executa SQL, mostra resultados]
Você: "Salva essa consulta como 'Atrasos por cliente 2025'"
mAIke: [Salva a consulta]
Você: "Roda aquele relatório de atrasos"
mAIke: [Encontra e executa a consulta salva]
```

**Como Funciona:**
- Você pede para salvar uma consulta que funcionou bem
- A mAIke salva a consulta SQL com nome, descrição e exemplos
- Depois você pode pedir para "rodar aquele relatório" e a mAIke encontra e executa
- Consultas salvas podem ter parâmetros (futuro)

**Arquivos Relacionados:**
- **`services/saved_queries_service.py`** - Módulo principal
  - `salvar_consulta_personalizada()` - Salva uma consulta SQL
  - `buscar_consulta_personalizada()` - Busca consulta salva por texto
  - `listar_consultas_salvas()` - Lista todas as consultas salvas
- **`db_manager.py`** - Tabela `consultas_salvas` criada no `init_db()`
- **`services/tool_definitions.py`** - Tools `salvar_consulta_personalizada` e `buscar_consulta_personalizada` adicionadas
- **`services/chat_service.py`** - Integração no `_executar_funcao_tool()`

**Estrutura da Tabela `consultas_salvas`:**
```sql
CREATE TABLE consultas_salvas (
    id INTEGER PRIMARY KEY,
    nome_exibicao TEXT NOT NULL,     -- Nome amigável do relatório
    slug TEXT NOT NULL UNIQUE,        -- Identificador único
    descricao TEXT,                   -- Descrição do relatório
    sql_base TEXT NOT NULL,           -- SQL da consulta
    parametros_json TEXT,              -- Parâmetros (futuro)
    exemplos_pergunta TEXT,           -- Exemplos de como pedir
    criado_por TEXT,                  -- user_id ou session_id
    criado_em TIMESTAMP,
    atualizado_em TIMESTAMP,
    vezes_usado INTEGER DEFAULT 0,    -- Contador de uso
    ultimo_usado_em TIMESTAMP
)
```

**Como Debugar/Consertar:**
1. **Ver consultas salvas:**
   ```bash
   sqlite3 chat_ia.db
   SELECT * FROM consultas_salvas;
   ```
2. **Testar salvar consulta:**
   ```python
   from services.saved_queries_service import salvar_consulta_personalizada
   resultado = salvar_consulta_personalizada(
       nome_exibicao='Atrasos por cliente',
       slug='atrasos_cliente',
       descricao='Mostra clientes com mais processos em atraso',
       sql='SELECT cliente, COUNT(*) as atrasos FROM processos WHERE atraso > 0 GROUP BY cliente'
   )
   ```
3. **Testar buscar consulta:**
   ```python
   from services.saved_queries_service import buscar_consulta_personalizada
   resultado = buscar_consulta_personalizada('atrasos por cliente')
   print(resultado)
   ```

### **Fluxo Completo de uma Consulta Analítica:**

```
1. Usuário pergunta: "Quais clientes têm mais processos em atraso?"
   ↓
2. mAIke gera SQL: "SELECT cliente, COUNT(*) FROM processos WHERE atraso > 0 GROUP BY cliente"
   ↓
3. Validação: validar_sql_seguro() verifica se é seguro
   ↓
4. Aplicação de LIMIT: aplicar_limit_seguro() adiciona LIMIT 100
   ↓
5. Execução:
   - Tenta SQL Server primeiro (se disponível)
   - Se falhar, usa SQLite (fallback)
   ↓
6. Formatação: Resultados são formatados e apresentados
   ↓
7. (Opcional) Salvar: Usuário pode pedir para salvar como relatório
```

### **Como Adicionar Novas Tabelas Permitidas:**

1. Abrir `services/analytical_query_service.py`
2. Encontrar `TABELAS_PERMITIDAS` (linha ~20)
3. Adicionar nome da tabela ao conjunto:
   ```python
   TABELAS_PERMITIDAS = {
       'processos_kanban',
       'duimps',
       'sua_nova_tabela',  # Adicionar aqui
   }
   ```

### **Como Ajustar Limite Padrão:**

1. Abrir `services/analytical_query_service.py`
2. Encontrar função `executar_consulta_analitica()` (linha ~100)
3. Modificar parâmetro `limit` padrão:
   ```python
   def executar_consulta_analitica(sql: str, limit: Optional[int] = 200, ...):
       # Mudar de 100 para 200, por exemplo
   ```

---

## 🔧 Troubleshooting

### **Erro: "Module not found"**
```bash
# Instalar dependências
pip install -r requirements.txt
```

### **Erro: "Certificate not found"**
```bash
# Copiar certificado
cp ../Projeto-DUIMP/certs/cert.pfx certs/
```

### **Erro: "SQL Server connection failed"**
- **NÃO É CRÍTICO** - O app funciona normalmente sem SQL Server
- O erro aparece mas não impede o chat IA de funcionar
- Para resolver (opcional):
  - Verifique as variáveis SQL no `.env`:
    - `SQL_SERVER`
    - `SQL_USERNAME`
    - `SQL_PASSWORD`
    - `SQL_DATABASE`
  - Verifique se o SQL Server está acessível na rede

### **Erro: "Address already in use" ou "Port 5000 is in use"**
- A porta 5000 é usada pelo AirPlay no macOS
- **Solução:** O app já está configurado para usar porta **5001** por padrão
- Se quiser usar outra porta, configure no `.env`: `PORT=8080`
- **Alternativa:** Desabilitar AirPlay Receiver: System Preferences → General → AirDrop & Handoff

### **Erro: "AI API Key invalid"**
- Verifique se `DUIMP_AI_API_KEY` está correto no `.env`
- Verifique se a chave não expirou

### **Erro: "Database is locked"**
- Este erro pode ocorrer com SQLite se houver múltiplas conexões simultâneas
- O sistema já tem timeout e retry configurados
- Se persistir, feche outras conexões ao banco

### **Erro: "db_manager.py not found"**
- Verifique se o arquivo está na raiz do projeto
- Se não estiver, copie: `cp ../Projeto-DUIMP/db_manager.py .`

### **"Nenhum processo encontrado" ou "SQL Server não disponível"**
- **Normal se:** Você está offline e SQLite está vazio
- **O que fazer:**
  1. Se estiver offline: Use SQLite (processos recentes) - funciona offline
  2. Se estiver na rede: Verifique conexão SQL Server no `.env`
  3. Use o comando: "verificar fontes de dados" para ver status completo
  4. Veja seção "Quais Processos a IA Acessa?" para mais detalhes

### **Regras aprendidas não estão sendo aplicadas**
- **Verificar:**
  1. Ver se regras estão salvas: `sqlite3 chat_ia.db "SELECT * FROM regras_aprendidas WHERE ativa = 1;"`
  2. Verificar logs do chat_service.py quando processa mensagem
  3. Ver se regras aparecem no contexto do prompt
- **Consertar:** Ver seção "Sistema de Aprendizado e Contexto Persistente" para detalhes

### **Contexto não está sendo mantido entre mensagens**
- **Verificar:**
  1. Ver se contexto está salvo: `sqlite3 chat_ia.db "SELECT * FROM contexto_sessao;"`
  2. Verificar se session_id está sendo passado corretamente
  3. Verificar logs do chat_service.py
- **Consertar:** Ver seção "Sistema de Aprendizado e Contexto Persistente" para detalhes

### **Consulta SQL analítica não está funcionando**
- **Verificar:**
  1. Ver se SQL é válido (apenas SELECT)
  2. Ver se tabela está na lista de permitidas
  3. Ver logs de execução (qual fonte foi usada)
- **Consertar:** Ver seção "Sistema de Consultas Analíticas SQL" para detalhes

---

## 📋 Relatório "Como Estão os X?" - Formato e Lógica

**⚠️ CRÍTICO:** Este documento descreve o formato e a lógica do relatório "como estão os X?" (ex: "como estão os MV5?", "como estão os BND?"). Se o relatório quebrar ou precisar ser refeito, use este documento como referência.

### 📊 Estrutura do Relatório

O relatório segue uma estrutura fixa com as seguintes seções (na ordem exata):

```
📋 PROCESSOS [CATEGORIA] - STATUS GERAL
📊 Data: DD/MM/YYYY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ✅ CHEGARAM (SEM DI/DUIMP)
2. 📅 COM ETA (SEM CHEGADA AINDA) [opcional - só aparece se houver]
3. 🚚 PROCESSOS EM DTA
4. ⚠️ PENDÊNCIAS ATIVAS
5. 📋 DIs EM ANÁLISE
6. 📋 DUIMPs EM ANÁLISE
7. 🔄 ETA ALTERADO [opcional - só aparece se houver]
8. 🔔 ALERTAS RECENTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ RESUMO
```

### 🔍 Fontes de Dados

O relatório usa as seguintes funções do `db_manager.py`:

1. **`listar_processos_liberados_registro(categoria, dias_retroativos=None, limit=200)`**
   - **Uso:** Seção "CHEGARAM (SEM DI/DUIMP)"
   - **O que busca:** Processos que chegaram (data_chegada <= hoje) e NÃO têm DI nem DUIMP registrada
   - **Parâmetros:** `dias_retroativos=None` busca TODOS os processos (não apenas hoje)
   - **Retorna:** Lista de processos com: `processo_referencia`, `data_chegada`, `porto_nome`, `modal`, `situacao_ce`, `numero_ce`, `numero_lpco`, `situacao_lpco`

2. **`obter_processos_prontos_registro(categoria)`**
   - **Uso:** Seção "COM ETA (SEM CHEGADA AINDA)" (filtrado para processos com ETA futuro)
   - **O que busca:** Processos prontos para registro (mas filtrado para apenas os com ETA futuro)
   - **Filtro aplicado:** Apenas processos com `eta` e sem `data_chegada`

3. **`listar_processos_em_dta(categoria)`**
   - **Uso:** Seção "PROCESSOS EM DTA"
   - **O que busca:** Processos que têm DTA (Documento de Transporte Aduaneiro)

4. **`obter_pendencias_ativas(categoria)`**
   - **Uso:** Seção "PENDÊNCIAS ATIVAS"
   - **O que busca:** Pendências ativas (ICMS, Frete, AFRMM, LPCO, bloqueios)
   - **Retorna:** Lista com: `processo_referencia`, `tipo_pendencia`, `descricao_pendencia`, `tempo_pendente`, `acao_sugerida`

5. **`obter_dis_em_analise(categoria)`**
   - **Uso:** Seção "DIs EM ANÁLISE"
   - **O que busca:** DIs em análise (com status diferente de "Sem status")
   - **Retorna:** Lista com: `numero_di`, `processo_referencia`, `canal`, `situacao_di`, `data_desembaraco`, `situacao_entrega`

6. **`obter_duimps_em_analise(categoria)`**
   - **Uso:** Seção "DUIMPs EM ANÁLISE"
   - **O que busca:** DUIMPs em análise (com status diferente de "Sem status")
   - **Retorna:** Lista com: `numero_duimp`, `versao`, `processo_referencia`, `canal`, `situacao_duimp`

7. **`obter_processos_eta_alterado(categoria)`**
   - **Uso:** Seção "ETA ALTERADO"
   - **O que busca:** Processos com ETA alterado (atraso/adiantado)
   - **Retorna:** Lista com: `processo_referencia`, `eta_anterior`, `eta_novo`

8. **`obter_alertas_recentes(limite=10, categoria)`**
   - **Uso:** Seção "ALERTAS RECENTES"
   - **O que busca:** Alertas recentes (mudanças de status, pendências, etc.)
   - **Retorna:** Lista com: `tipo`, `processo_referencia`, `mensagem`, `data`

### 📝 Formatação de Cada Seção

#### 1. CHEGARAM (SEM DI/DUIMP)

**Formato:**
```
✅ **CHEGARAM (SEM DI/DUIMP)** (N processo(s)):

  • **PROCESSO.XXXX/YY** - Porto: PORTO - Modal: MODAL - Chegou: DD/MM/YYYY - Status CE: STATUS - CE: NUMERO_CE - LPCO: NUMERO_LPCO (deferida) - ⚠️ Sem DI/DUIMP
```

**Campos exibidos (na ordem):**
- `processo_referencia` (obrigatório, em negrito)
- `porto_nome` (se disponível)
- `modal` (se disponível)
- `data_chegada` (formatada como DD/MM/YYYY, se disponível)
- `situacao_ce` (se disponível)
- `numero_ce` (se disponível)
- `numero_lpco` (se disponível, com "(deferida)" se `situacao_lpco` contém "deferid")
- "⚠️ Sem DI/DUIMP" (sempre presente)

**Limite:** Máximo 20 processos, com "... e mais N processo(s)" se houver mais

**Mensagem quando vazio:**
```
✅ **CHEGARAM (SEM DI/DUIMP):** Nenhum processo chegou sem DI/DUIMP.
```

#### 2. COM ETA (SEM CHEGADA AINDA)

**Formato:**
```
📅 **COM ETA (SEM CHEGADA AINDA)** (N processo(s)):

  • **PROCESSO.XXXX/YY** - Porto: PORTO - Modal: MODAL - Navio: NOME_NAVIO - ETA: DD/MM/YYYY
```

**Campos exibidos:**
- `processo_referencia` (obrigatório, em negrito)
- `porto_nome` (se disponível)
- `modal` (se disponível)
- `nome_navio` (se disponível)
- `eta` (se disponível)

**Limite:** Máximo 20 processos

**Nota:** Esta seção só aparece se houver processos com ETA futuro (sem chegada confirmada)

#### 3. PROCESSOS EM DTA

**Formato:**
```
🚚 **PROCESSOS EM DTA** (N processo(s)):

  • **PROCESSO.XXXX/YY** - DTA: NUMERO_DTA - Chegou: DD/MM/YYYY - Status CE: STATUS
```

**Campos exibidos:**
- `processo_referencia` (obrigatório, em negrito)
- `numero_dta` (se disponível)
- `data_chegada` (se disponível)
- `situacao_ce` (se disponível)

**Limite:** Máximo 10 processos

#### 4. PENDÊNCIAS ATIVAS

**Formato:**
```
⚠️ **PENDÊNCIAS ATIVAS** (N processo(s)):

  • **PROCESSO.XXXX/YY** - TIPO_PENDENCIA: DESCRICAO (há TEMPO) - Ação: ACAO_SUGERIDA
```

**Campos exibidos:**
- `processo_referencia` (obrigatório, em negrito)
- `tipo_pendencia` (se disponível)
- `descricao_pendencia` (se disponível)
- `tempo_pendente` (se disponível, formatado como "há TEMPO")
- `acao_sugerida` (se disponível)

**Limite:** Máximo 10 processos

**Mensagem quando vazio:**
```
✅ **PENDÊNCIAS ATIVAS:** Nenhuma pendência ativa.
```

#### 5. DIs EM ANÁLISE

**Formato:**
```
📋 **DIs EM ANÁLISE** (N DI(s)):

  • **NUMERO_DI** - Processo: PROCESSO.XXXX/YY - Canal: CANAL - Status: STATUS - Desembaraço: DD/MM/YYYY HH:MM:SS - Entrega: STATUS_ENTREGA
```

**Campos exibidos:**
- `numero_di` (obrigatório, em negrito)
- `processo_referencia` (se disponível)
- `canal` (se disponível)
- `situacao_di` (se disponível)
- `data_desembaraco` (se disponível, formatada como DD/MM/YYYY HH:MM:SS)
- `situacao_entrega` (se disponível)

**Limite:** Máximo 10 DIs

**Mensagem quando vazio:**
```
✅ **DIs EM ANÁLISE:** Nenhuma DI em análise.
```

#### 6. DUIMPs EM ANÁLISE

**Formato:**
```
📋 **DUIMPs EM ANÁLISE** (N DUIMP(s)):

  • **NUMERO_DUIMP** vVERSAO - Processo: PROCESSO.XXXX/YY - Canal: CANAL - Status: STATUS
```

**Campos exibidos:**
- `numero_duimp` (obrigatório, em negrito)
- `versao` (se disponível, formatado como "vVERSAO")
- `processo_referencia` (se disponível)
- `canal` (se disponível)
- `situacao_duimp` (se disponível)

**Limite:** Máximo 10 DUIMPs

**Mensagem quando vazio:**
```
✅ **DUIMPs EM ANÁLISE:** Nenhuma DUIMP em análise.
```

#### 7. ETA ALTERADO

**Formato:**
```
🔄 **ETA ALTERADO** (N processo(s)):

  • **PROCESSO.XXXX/YY** - ETA: ETA_ANTERIOR → ETA_NOVO
  • **PROCESSO.XXXX/YY** - Novo ETA: ETA_NOVO
```

**Campos exibidos:**
- `processo_referencia` (obrigatório, em negrito)
- `eta_anterior` e `eta_novo` (se ambos disponíveis, formato: "ETA_ANTERIOR → ETA_NOVO")
- `eta_novo` (se apenas novo disponível, formato: "Novo ETA: ETA_NOVO")

**Limite:** Máximo 10 processos

**Nota:** Esta seção só aparece se houver processos com ETA alterado

#### 8. ALERTAS RECENTES

**Formato:**
```
🔔 **ALERTAS RECENTES** (N alerta(s)):

  • **PROCESSO.XXXX/YY** - tipo: MENSAGEM (DD/MM/YYYY HH:MM:SS)
  • **PROCESSO.XXXX/YY** - tipo: MENSAGEM_MULTILINHA
   ANTES: STATUS_ANTERIOR
   AGORA: STATUS_NOVO (DD/MM/YYYY HH:MM:SS)
```

**Campos exibidos:**
- `processo_referencia` (obrigatório, em negrito)
- `tipo` (se disponível)
- `mensagem` (se disponível, pode ser multilinha)
- `data` (se disponível, formatada como DD/MM/YYYY HH:MM:SS)

**Limite:** Máximo 5 alertas, com "... e mais N alerta(s)" se houver mais

**Nota:** Alertas podem ter mensagens complexas (multilinha) para casos como mudanças de status

#### 9. RESUMO

**Formato:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **RESUMO:**
  • N processo(s) chegaram (sem DI/DUIMP)
  • N processo(s) com ETA (sem chegada ainda)
  • N processo(s) em DTA
  • N pendência(s) ativa(s)
  • N DI(s) em análise
  • N DUIMP(s) em análise
```

**Contadores:**
- Processos que chegaram (sem DI/DUIMP): `len(processos_chegando)`
- Processos com ETA (sem chegada ainda): `len(processos_com_eta)` (filtrado de `processos_prontos`)
- Processos em DTA: `len(processos_em_dta)`
- Pendências ativas: `len(pendencias)`
- DIs em análise: `len(dis_analise)`
- DUIMPs em análise: `len(duimps_analise)`

### 🔧 Implementação

**Arquivo:** `services/agents/processo_agent.py`

**Função principal:** `_listar_por_categoria()` (linha ~4580)

**Função de formatação:** `_formatar_relatorio_geral_categoria()` (linha ~4676)

**Fluxo:**
1. `_listar_por_categoria()` detecta pergunta "como estão os X?"
2. Busca dados usando funções do `db_manager.py` (listadas acima)
3. Chama `_formatar_relatorio_geral_categoria()` com os dados
4. `_formatar_relatorio_geral_categoria()` formata cada seção na ordem definida
5. Retorna relatório completo formatado

**Correções aplicadas (19/12/2025):**
- ✅ Uso de `listar_processos_liberados_registro` com `dias_retroativos=None` para buscar TODOS os processos que chegaram sem DI/DUIMP (não apenas hoje)
- ✅ Formatação de data de chegada corrigida para suportar formato ISO
- ✅ Seção "CHEGARAM (SEM DI/DUIMP)" agora mostra corretamente processos que chegaram sem documentos

### ⚠️ Notas Importantes

1. **Diferença entre "como estão os X?" e "o que temos pra hoje":**
   - "Como estão os X?" → Relatório geral da categoria (todos os processos, não apenas hoje)
   - "O que temos pra hoje" → Dashboard do dia (apenas processos relevantes para hoje)

2. **Processos que chegaram sem DI/DUIMP:**
   - Usa `listar_processos_liberados_registro` com `dias_retroativos=None` para buscar TODOS
   - Não filtra por data (mostra todos que chegaram, independente de quando)

3. **Processos com ETA futuro:**
   - Filtrado de `obter_processos_prontos_registro` para apenas processos com `eta` e sem `data_chegada`
   - Só aparece se houver processos nessa condição

4. **Limites de exibição:**
   - CHEGARAM: 20 processos
   - COM ETA: 20 processos
   - DTA: 10 processos
   - PENDÊNCIAS: 10 processos
   - DIs: 10 DIs
   - DUIMPs: 10 DUIMPs
   - ETA ALTERADO: 10 processos
   - ALERTAS: 5 alertas

5. **Formatação de datas:**
   - Data de chegada: DD/MM/YYYY
   - Data de desembaraço: DD/MM/YYYY HH:MM:SS
   - Data de alerta: DD/MM/YYYY HH:MM:SS

### 🐛 Troubleshooting

**Problema:** Relatório não mostra processos que chegaram sem DI/DUIMP
- **Solução:** Verificar se `listar_processos_liberados_registro` está sendo chamado com `dias_retroativos=None`
- **Solução:** Verificar se função está retornando dados corretos (testar diretamente)

**Problema:** Formato de data incorreto
- **Solução:** Verificar formatação de data em `_formatar_relatorio_geral_categoria()` (linha ~4715-4731)
- **Solução:** Verificar se `data_chegada` vem em formato ISO e está sendo parseado corretamente

**Problema:** Seção não aparece quando deveria
- **Solução:** Verificar se função correspondente está retornando dados (ex: `obter_processos_eta_alterado`)
- **Solução:** Verificar se filtros estão corretos (ex: processos com ETA futuro)

---

## 📅 Relatório "O Que Temos Pra Hoje" - Formato e Lógica

**⚠️ CRÍTICO:** Este documento descreve o formato e a lógica do relatório "o que temos pra hoje" (ex: "o que temos hoje de MV5?", "o que temos pra hoje?"). Se o relatório quebrar ou precisar ser refeito, use este documento como referência.

### 📊 Estrutura do Relatório

O relatório segue uma estrutura fixa com as seguintes seções (na ordem exata):

```
📅 O QUE TEMOS PRA HOJE - [CATEGORIA] - DD/MM/YYYY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 🚢 CHEGANDO HOJE
2. 🚚 PROCESSOS EM DTA [opcional - só aparece se houver]
3. ✅ PRONTOS PARA REGISTRO (com classificação de atraso)
   - 🚨 ATRASO CRÍTICO (mais de 7 dias)
   - ⚠️ ATRASO MODERADO (3 a 7 dias)
   - ✅ RECENTES (menos de 3 dias)
4. ⚠️ PENDÊNCIAS ATIVAS (agrupadas por tipo e categoria)
5. 📋 DIs EM ANÁLISE (agrupadas por categoria)
6. 📋 DUIMPs EM ANÁLISE (agrupadas por categoria)
7. 🔄 ETA ALTERADO [opcional - só aparece se houver]
8. 🔔 ALERTAS RECENTES
9. 💡 AÇÕES SUGERIDAS [opcional - só aparece se houver]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 RESUMO
```

### 🔍 Fontes de Dados

O relatório usa as seguintes funções do `db_manager.py`:

1. **`obter_processos_chegando_hoje(categoria, modal)`**
   - **Uso:** Seção "CHEGANDO HOJE"
   - **O que busca:** Processos que chegam HOJE (ETA = hoje OU dataDestinoFinal = hoje)
   - **Retorna:** Lista de processos com: `processo_referencia`, `porto_nome`, `eta_iso`, `tem_apenas_eta`, `tem_chegada_confirmada`, `situacao_ce`, `modal`

2. **`listar_processos_em_dta(categoria)`**
   - **Uso:** Seção "PROCESSOS EM DTA"
   - **O que busca:** Processos que têm DTA (Documento de Transporte Aduaneiro)
   - **Retorna:** Lista de processos com: `processo_referencia`, `numero_dta`, `data_destino_final`, `situacao_ce`

3. **`obter_processos_prontos_registro(categoria, modal)`**
   - **Uso:** Seção "PRONTOS PARA REGISTRO"
   - **O que busca:** Processos que chegaram e não têm DI/DUIMP registrada
   - **Classificação:** Processos são classificados por atraso:
     - **Crítico:** Mais de 7 dias desde a chegada
     - **Moderado:** 3 a 7 dias desde a chegada
     - **Recentes:** Menos de 3 dias desde a chegada
   - **Retorna:** Lista de processos com: `processo_referencia`, `data_destino_final`, `tipo_documento`, `situacao_ce`, `numero_duimp`, `situacao_duimp`, `tem_lpco`, `lpco_deferido`, `numero_lpco`

4. **`obter_pendencias_ativas(categoria, modal)`**
   - **Uso:** Seção "PENDÊNCIAS ATIVAS"
   - **O que busca:** Pendências ativas (ICMS, Frete, AFRMM, LPCO, bloqueios)
   - **Agrupamento:** Por tipo de pendência (ICMS, Frete, AFRMM, LPCO, Bloqueio CE) e depois por categoria
   - **Retorna:** Lista com: `processo_referencia`, `tipo_pendencia`, `descricao_pendencia`, `tempo_pendente`, `acao_sugerida`

5. **`obter_dis_em_analise(categoria)`**
   - **Uso:** Seção "DIs EM ANÁLISE"
   - **O que busca:** DIs em análise (com status diferente de "Sem status")
   - **Agrupamento:** Por categoria do processo
   - **Retorna:** Lista com: `numero_di`, `processo_referencia`, `canal_di`, `situacao_di`, `data_desembaraco`, `situacao_entrega_carga`, `situacao_entrega_tabela`, `tempo_analise`

6. **`obter_duimps_em_analise(categoria)`**
   - **Uso:** Seção "DUIMPs EM ANÁLISE"
   - **O que busca:** DUIMPs em análise (com status diferente de "Sem status")
   - **Agrupamento:** Por categoria do processo
   - **Retorna:** Lista com: `numero_duimp`, `versao`, `processo_referencia`, `canal_duimp`, `status`, `data_desembaraco`, `situacao_entrega_carga`, `situacao_entrega_tabela`, `tempo_analise`

7. **`obter_processos_eta_alterado(categoria)`**
   - **Uso:** Seção "ETA ALTERADO"
   - **O que busca:** Processos com ETA alterado (atraso/adiantado)
   - **Agrupamento:** Por tipo de mudança (ATRASO, ADIANTADO) e depois por categoria
   - **Retorna:** Lista com: `processo_referencia`, `tipo_mudanca`, `ultimo_eta_formatado`, `primeiro_eta_formatado`, `dias_diferenca`

8. **`obter_alertas_recentes(limite=10, categoria)`**
   - **Uso:** Seção "ALERTAS RECENTES"
   - **O que busca:** Alertas recentes (mudanças de status, pendências, etc.)
   - **Retorna:** Lista com: `tipo`, `processo_referencia`, `titulo`, `mensagem`, `status_atual`

### 📝 Formatação de Cada Seção

#### 1. CHEGANDO HOJE

**Formato:**
```
🚢 **CHEGANDO HOJE** (N processo(s))

   **CATEGORIA** (N processo(s)):
      • **PROCESSO.XXXX/YY** - Porto: PORTO - ETA: DD/MM/YYYY (previsto/confirmado) - Status: STATUS - Modal: MODAL
```

**Campos exibidos:**
- Agrupado por categoria
- `processo_referencia` (obrigatório, em negrito)
- `porto_nome` (se disponível)
- `eta_iso` (formatado como DD/MM/YYYY, se disponível)
- `tem_apenas_eta` → "(previsto)" ou `tem_chegada_confirmada` → "(confirmado)"
- `situacao_ce` (se disponível)
- `modal` (se disponível)

**Mensagem quando vazio:**
```
   ℹ️ Nenhum processo chegando hoje.
```

#### 2. PROCESSOS EM DTA

**Formato:**
```
🚚 **PROCESSOS EM DTA** (N processo(s))

   *Cargas em trânsito para outro recinto alfandegado*

   **CATEGORIA** (N processo(s)):
      • **PROCESSO.XXXX/YY** - DTA: NUMERO_DTA - Chegou em DD/MM/YYYY - Status CE: STATUS
```

**Campos exibidos:**
- Agrupado por categoria
- `processo_referencia` (obrigatório, em negrito)
- `numero_dta` (se disponível)
- `data_destino_final` (formatado como "Chegou em DD/MM/YYYY", se disponível)
- `situacao_ce` (se disponível)

**Nota:** Esta seção só aparece se houver processos em DTA

#### 3. PRONTOS PARA REGISTRO

**Formato (com classificação de atraso):**
```
✅ **PRONTOS PARA REGISTRO** (N processo(s))

   🚨 **ATRASO CRÍTICO** (N processo(s) - mais de 7 dias):

      **CATEGORIA** (N processo(s)):
         • **PROCESSO.XXXX/YY** - Chegou em DD/MM/YYYY ⚠️ **N dia(s) de atraso**, sem DI/DUIMP - Tipo: TIPO - Status CE: STATUS - LPCO NUMERO deferido

   ⚠️ **ATRASO MODERADO** (N processo(s) - 3 a 7 dias):

      **CATEGORIA** (N processo(s)):
         • **PROCESSO.XXXX/YY** - Chegou em DD/MM/YYYY (N dia(s) de atraso), sem DI/DUIMP - Tipo: TIPO - Status CE: STATUS

   ✅ **RECENTES** (N processo(s) - menos de 3 dias):

      **CATEGORIA** (N processo(s)):
         • **PROCESSO.XXXX/YY** - Chegou em DD/MM/YYYY, sem DI/DUIMP - Tipo: TIPO - Status CE: STATUS
```

**Classificação de atraso:**
- **Crítico:** Mais de 7 dias desde a chegada → `dias_atraso > 7`
- **Moderado:** 3 a 7 dias desde a chegada → `3 <= dias_atraso <= 7`
- **Recentes:** Menos de 3 dias desde a chegada → `dias_atraso < 3` ou sem data

**Campos exibidos:**
- Agrupado por categoria dentro de cada nível de atraso
- `processo_referencia` (obrigatório, em negrito)
- `data_destino_final` (formatado como "Chegou em DD/MM/YYYY", se disponível)
- `dias_atraso` (calculado, formatado como "⚠️ **N dia(s) de atraso**" para crítico, "(N dia(s) de atraso)" para moderado)
- `numero_duimp` e `situacao_duimp` (se disponível, mostra "DUIMP NUMERO registrada (STATUS)")
- `tipo_documento` (se não tem DUIMP, mostra "sem DI/DUIMP - Tipo: TIPO")
- `situacao_ce` (se disponível)
- `tem_lpco` e `lpco_deferido` (se disponível, mostra "LPCO NUMERO deferido")

**Mensagem quando vazio:**
```
   ℹ️ Nenhum processo pronto para registro.
```

#### 4. PENDÊNCIAS ATIVAS

**Formato:**
```
⚠️ **PENDÊNCIAS ATIVAS** (N processo(s))

   **TIPO_PENDENCIA** (N processo(s)):
      *CATEGORIA* (N processo(s)):
         • **PROCESSO.XXXX/YY** - DESCRICAO (há TEMPO) - Ação: ACAO_SUGERIDA
```

**Agrupamento:**
- Primeiro por tipo de pendência (ordem: ICMS, Frete, AFRMM, LPCO, Bloqueio CE)
- Depois por categoria dentro de cada tipo

**Campos exibidos:**
- `processo_referencia` (obrigatório, em negrito)
- `descricao_pendencia` (se disponível)
- `tempo_pendente` (se disponível, formatado como "há TEMPO")
- `acao_sugerida` (se disponível)

**Mensagem quando vazio:**
```
   ✅ Nenhuma pendência ativa.
```

#### 5. DIs EM ANÁLISE

**Formato:**
```
📋 **DIs EM ANÁLISE** (N DI(s))

   **CATEGORIA** (N DI(s)):
      • **NUMERO_DI** - Processo: PROCESSO.XXXX/YY - Canal: CANAL - Status DI: STATUS_FORMATADO - Desembaraço: DD/MM/YY HH:MM - Entrega: STATUS_ENTREGA_FORMATADO
```

**Agrupamento:** Por categoria do processo

**Campos exibidos:**
- `numero_di` (obrigatório, em negrito)
- `processo_referencia` (se disponível)
- `canal_di` (se disponível)
- `situacao_di` (formatado: substitui `_` por espaços e capitaliza, se disponível)
- `data_desembaraco` (formatado como DD/MM/YY HH:MM, se disponível)
- `situacao_entrega_carga` ou `situacao_entrega_tabela` (formatado: substitui `_` por espaços e capitaliza, se disponível)
- `tempo_analise` (se disponível, formatado como "há TEMPO")

**Mensagem quando vazio:**
```
   ✅ Nenhuma DI em análise.
```

#### 6. DUIMPs EM ANÁLISE

**Formato:**
```
📋 **DUIMPs EM ANÁLISE** (N DUIMP(s))

   **CATEGORIA** (N DUIMP(s)):
      • **NUMERO_DUIMP** vVERSAO - Processo: PROCESSO.XXXX/YY - Canal: CANAL - Status DUIMP: STATUS_FORMATADO - Desembaraço: DD/MM/YY HH:MM - Entrega: STATUS_ENTREGA_FORMATADO
```

**Agrupamento:** Por categoria do processo

**Campos exibidos:**
- `numero_duimp` (obrigatório, em negrito)
- `versao` (formatado como "vVERSAO", se disponível)
- `processo_referencia` (se disponível)
- `canal_duimp` (se disponível)
- `status` (formatado: substitui `_` por espaços e capitaliza, se disponível)
- `data_desembaraco` (formatado como DD/MM/YY HH:MM, se disponível)
- `situacao_entrega_carga` ou `situacao_entrega_tabela` (formatado: substitui `_` por espaços e capitaliza, se disponível)
- `tempo_analise` (se disponível, formatado como "há TEMPO")

**Mensagem quando vazio:**
```
   ✅ Nenhuma DUIMP em análise.
```

#### 7. ETA ALTERADO

**Formato:**
```
🔄 **ETA ALTERADO** (N processo(s))

   📅 **ATRASO** (N processo(s)):
      *CATEGORIA* (N processo(s)):
         • **PROCESSO.XXXX/YY** - ETA: DD/MM/YYYY (atraso de N dia(s))

   ⚡ **ADIANTADO** (N processo(s)):
      *CATEGORIA* (N processo(s)):
         • **PROCESSO.XXXX/YY** - ETA: DD/MM/YYYY (adiantado em N dia(s))
```

**Agrupamento:**
- Primeiro por tipo de mudança (ATRASO primeiro, depois ADIANTADO)
- Depois por categoria dentro de cada tipo

**Campos exibidos:**
- `processo_referencia` (obrigatório, em negrito)
- `ultimo_eta_formatado` ou `primeiro_eta_formatado` (se disponível)
- `dias_diferenca` (se disponível, formatado como "atraso de N dia(s)" ou "adiantado em N dia(s)")

**Nota:** Esta seção só aparece se houver processos com ETA alterado

#### 8. ALERTAS RECENTES

**Formato:**
```
🔔 **ALERTAS RECENTES**

   ✅ 📦 PROCESSO.XXXX/YY: CE - STATUS_ATUAL
   ✅ 📋 PROCESSO.XXXX/YY: DI - STATUS_ATUAL
   ✅ 📄 PROCESSO.XXXX/YY: DUIMP - STATUS_ATUAL
   ⚠️ TITULO - PROCESSO.XXXX/YY
```

**Formatação especial:**
- Para alertas de status (status_ce, status_di, status_duimp): Mostra apenas processo e status atual (formato limpo)
- Para outros alertas: Mostra título completo e processo
- Emoji: ⚠️ para pendentes/bloqueios, ✅ para outros

**Limite:** Máximo 5 alertas

**Nota:** Esta seção só aparece se houver alertas

#### 9. AÇÕES SUGERIDAS

**Formato:**
```
💡 **AÇÕES SUGERIDAS**

   1. 🚨 URGENTE: Criar DUIMP para PROCESSO.XXXX/YY (N dia(s) de atraso!)
   2. Verificar pagamento de ICMS para PROCESSO.XXXX/YY
   ...
```

**Geração:** Função `_gerar_sugestoes_acoes()` gera sugestões priorizadas baseadas em:
- Processos com atraso crítico
- Pendências ativas
- DUIMPs em análise

**Limite:** Máximo 7 sugestões

**Nota:** Esta seção só aparece se houver sugestões

#### 10. RESUMO

**Formato:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **RESUMO:** N chegando | N prontos | N em DTA | N pendências | N DIs | N DUIMPs | N ETA alterado
```

**Contadores:**
- Chegando: `len(processos_chegando)`
- Prontos: `len(processos_prontos)`
- Em DTA: `len(processos_em_dta)`
- Pendências: `len(pendencias)`
- DIs: `len(dis_analise)`
- DUIMPs: `len(duimps_analise)`
- ETA alterado: `len(eta_alterado)` (só aparece se houver)

### 🔧 Implementação

**Arquivo:** `services/agents/processo_agent.py`

**Função principal:** `_obter_dashboard_hoje()` (linha ~4023)

**Função de formatação:** `_formatar_dashboard_hoje()` (linha ~4090)

**Fluxo:**
1. `_obter_dashboard_hoje()` detecta pergunta "o que temos pra hoje?"
2. Busca dados usando funções do `db_manager.py` (listadas acima)
3. Chama `_formatar_dashboard_hoje()` com os dados
4. `_formatar_dashboard_hoje()` formata cada seção na ordem definida
5. Retorna dashboard completo formatado

**Parâmetros especiais:**
- `apenas_pendencias`: Se `True`, mostra apenas seção de pendências
- `categoria`: Filtra por categoria específica
- `modal`: Filtra por modal (Aéreo/Marítimo)

### ⚠️ Notas Importantes

1. **Diferença entre "o que temos pra hoje" e "como estão os X?":**
   - "O que temos pra hoje" → Dashboard do dia (apenas processos relevantes para HOJE)
   - "Como estão os X?" → Relatório geral da categoria (todos os processos, não apenas hoje)

2. **Processos chegando hoje:**
   - Usa `obter_processos_chegando_hoje` que busca apenas processos com ETA = hoje OU dataDestinoFinal = hoje
   - Diferente de "como estão os X?" que busca TODOS os processos que chegaram sem DI/DUIMP

3. **Classificação de atraso:**
   - Calculado baseado em `data_destino_final` vs data atual
   - Processos são agrupados por nível de atraso (crítico, moderado, recentes)
   - Atraso crítico aparece primeiro (prioridade)

4. **Agrupamento:**
   - Processos são sempre agrupados por categoria
   - Pendências são agrupadas por tipo E depois por categoria
   - ETA alterado é agrupado por tipo de mudança E depois por categoria

5. **Formatação de status:**
   - Status de DI/DUIMP/Entrega: Substitui `_` por espaços e capitaliza (ex: `DI_DESEMBARACADA` → `Di Desembaracada`)
   - Data de desembaraço: Formato DD/MM/YY HH:MM

6. **Limites de exibição:**
   - Alertas: 5 alertas
   - Ações sugeridas: 7 sugestões
   - Outras seções: Sem limite (mostra todos)

### 🐛 Troubleshooting

**Problema:** Dashboard não mostra processos chegando hoje
- **Solução:** Verificar se `obter_processos_chegando_hoje` está retornando dados (testar diretamente)
- **Solução:** Verificar se ETA ou dataDestinoFinal está correta (deve ser hoje)

**Problema:** Classificação de atraso incorreta
- **Solução:** Verificar cálculo de `dias_atraso` em `_formatar_dashboard_hoje()` (linha ~4233-4250)
- **Solução:** Verificar se `data_destino_final` está sendo parseado corretamente

**Problema:** Agrupamento não está funcionando
- **Solução:** Verificar se categoria está sendo extraída corretamente (linha ~4143, 4190, etc.)
- **Solução:** Verificar se processos têm `processo_referencia` no formato correto (CATEGORIA.NUMERO/ANO)

**Problema:** Status não está formatado corretamente
- **Solução:** Verificar formatação de status (linha ~4483, 4507, 4544, 4568)
- **Solução:** Verificar se está substituindo `_` por espaços e capitalizando

---

## 🔄 Sistema de Fallback de Tools (14/01/2026)

### ⚠️ **Arquitetura e Complicações**

O sistema de execução de tools usa uma arquitetura em camadas com **dois tipos de fallback**:

1. **Fallback de Roteamento**: Quando handler não existe no `ToolExecutionService`, o fluxo segue para `ToolRouter` (agents especializados)
2. **Fallback Interno** (`fallback_to="CHAT_SERVICE"`): Quando handler existe mas quer delegar para código legado (ex: `enviar_relatorio_email` em modo preview)

### ⚠️ **Regras Críticas**

1. **`_fallback_attempted` SEMPRE inicializa como `False`** no início do método
2. **`enviar_relatorio_email` NUNCA vai para ToolRouter** quando `fallback_to="CHAT_SERVICE"` (retorna imediatamente)
3. **`_fallback_chat_service()` não pode causar recursão** (desabilita ToolExecutionService/ToolExecutor temporariamente)
4. **Loop detection aceita `_use_fallback` OU `use_fallback`** para compatibilidade

**📚 Documentação completa:** `AGENTS.md` seção "🔄 Sistema de Fallback de Tools"

---

## 📚 Documentação Adicional

### 📌 **Documentações Essenciais** (Comece Por Aqui!)

As documentações mais importantes estão organizadas em **`docs/essencial/`**:

- **`docs/essencial/API_DOCUMENTATION.md`** - Documentação completa da API
- **`docs/essencial/MANUAL_COMPLETO.md`** - Manual completo do sistema
- **`docs/essencial/MAPEAMENTO_SQL_SERVER.md`** - Estrutura do banco de dados
- **`docs/essencial/REGRAS_NEGOCIO.md`** - Regras de negócio do sistema

**💡 Leia `docs/essencial/README.md` para guia completo das documentações essenciais.**

### 🤖 **V2 (LangChain / LangGraph) - SEPARADA**

**⚠️ IMPORTANTE:** A V2 foi **migrada e separada** da V1 em 25-26/01/2026.

**Localização V2:** `/Volumes/KINGSTON/PYTHON/v2_langchain`  
**Porta V2:** `5002` (ou `PORT`)  
**Status:** V2 roda localmente, **não está mais neste diretório**.

**Documentação V2:**
- **`/Volumes/KINGSTON/PYTHON/v2_langchain/README.md`** - Visão geral, uso, migração
- **`/Volumes/KINGSTON/PYTHON/v2_langchain/AGENTS.md`** - Instruções para agentes IA
- **`/Volumes/KINGSTON/PYTHON/v2_langchain/PROMPT_V2.md`** - Contexto técnico detalhado
- **`/Volumes/KINGSTON/PYTHON/v2_langchain/CONTINUAR_TRABALHO.md`** - Estado atual e como continuar

**Este diretório (`Chat-IA2-Independente/`) contém APENAS a V1.**

**README e AGENTS** continuam como referência para o **projeto geral** (V1, app principal, regras globais).

### 📁 **Estrutura Organizada**

Documentações organizadas por categoria:
- **`docs/essencial/`** - Documentações críticas e essenciais
- **`docs/integracoes/`** - Integrações com APIs externas
- **`docs/funcionalidades/`** - Funcionalidades específicas
- **`docs/planejamento/`** - Planejamentos e roadmaps
- **`docs/explicacoes/`** - Explicações e tutoriais
- **`docs/resumos/`** - Resumos executivos

**💡 Consulte `docs/INDICE_ORGANIZADO.md` para navegação completa.**

### 📋 Documentos Principais:

#### 🆕 Documentações Criadas Recentemente:

##### **Passo 6 - Relatórios JSON (10/01/2026):**

- **`docs/PASSO_6_PLANO_IMPLEMENTACAO.md`** ⭐ **NOVO (10/01/2026)**
  - Plano detalhado de implementação em 4 fases incrementais
  - Fase 1: Preparar estrutura JSON (SEGURA)
  - Fase 2: Integrar com IA (TESTE)
  - Fase 3: Usar JSON como fonte da verdade (CONSOLIDAÇÃO)
  - Fase 4: Remover formatação manual (LIMPEZA)
  - Status: ✅ **FASE 1 CONCLUÍDA** - Próximo: Fase 2

- **`docs/PASSO_6_PROGRESSO.md`** ⭐ **NOVO (10/01/2026)**
  - Progresso detalhado do Passo 6
  - Fase 1 CONCLUÍDA: JSON estruturado criado com tipo explícito
  - Estrutura JSON documentada para ambos os relatórios
  - Próximos passos documentados
  - Status: ✅ **ATUALIZADO** - Fase 1 concluída

- **`docs/PROBLEMA_RELATORIOS_STRING_JSON.md`** ⭐ **NOVO (10/01/2026)**
  - Análise completa do problema de relatórios em string vs JSON
  - Por que regex para detectar tipo é frágil
  - Solução proposta (JSON + IA humaniza)
  - Status: ✅ **ANÁLISE COMPLETA** - Fase 1 implementada

- **`docs/MELHORIA_RELATORIOS_JSON.md`** ⭐ **NOVO (09/01/2026)**
  - Proposta de converter relatórios para JSON
  - Deixar IA humanizar/formatar (similar ao email)
  - Benefícios e considerações
  - Status: ✅ **PROPOSTA DOCUMENTADA** - Fase 1 implementada

##### **Documentações Anteriores (07/01/2026):**

- **`docs/PLANEJAMENTO_BANCO_DADOS_MAIKE.md`** ⭐ **NOVO (07/01/2026)**
  - Planejamento completo do banco de dados `mAIke_assistente` no SQL Server
  - 26 tabelas organizadas em 5 schemas (dbo, comunicacao, ia, legislacao, auditoria)
  - Cobre: processos, documentos, despesas, conciliação bancária, rastreamento de recursos, validação automática
  - Status: ✅ **COMPLETO** - Pronto para revisão e implementação

- **`docs/SISTEMA_NOTIFICACOES_HUMANIZADAS.md`** ⭐ **NOVO (07/01/2026)**
  - Sistema de notificações proativas e humanizadas
  - Transforma notificações técnicas em conversas humanas
  - Priorização inteligente, agrupamento, timing inteligente
  - Status: ✅ **COMPLETO** - Pronto para revisão e implementação

##### 📋 Documentos Clássicos:

- **`docs/FLUXO_DESPACHO_ADUANEIRO.md`** ⭐ **IMPORTANTE**
  - Explica o fluxo completo da importação (do carregamento até entrega)
  - Define o significado de cada data no sistema
  - Regras para determinar se carga chegou ao destino final
  - **Use este documento para entender o contexto de negócio**

- **`docs/API_DOCUMENTATION.md`**
  - Documentação completa de todos os endpoints da aplicação
  - Detalhes sobre APIs externas (Integra Comex, Portal Único, API Kanban)
  - Autenticação, custos, limitações e comportamentos específicos por ambiente

- **`docs/REFATORACAO_PRODUCAO.md`**
  - Recomendações críticas para produção (segurança, validação, logging)
  - Melhorias opcionais (monitoramento, testes, documentação)
  - Análise de código duplicado e refatorações sugeridas

### 🔧 Documentação Técnica:

- **Tool Calling System:** Ver `services/tool_definitions.py`
- **Agents:** Ver `services/agents/`
- **APIs Oficiais:** Ver `utils/portal_proxy.py` e `utils/integracomex_proxy.py`
- **Criação de Executável Windows:** Ver `INSTRUCOES_WINDOWS.txt`

---

## 💰 Mapeamento de Códigos de Receita da DI (Impostos)

**⚠️ CRÍTICO:** Este mapeamento é essencial para exibir impostos pagos da DI corretamente. Se perdermos essa informação, use este documento para recuperar rapidamente.

### 📋 Tabela de Mapeamento

A tabela `Serpro.dbo.Di_Pagamento` armazena pagamentos usando códigos numéricos. O sistema mapeia esses códigos para nomes amigáveis de impostos:

| Código de Receita | Tipo de Imposto | Descrição |
|-------------------|-----------------|-----------|
| `0086` ou `86` | **II** | Imposto de Importação |
| `1038` ou `38` | **IPI** | Imposto sobre Produtos Industrializados |
| `5602` ou `602` | **PIS** | PIS/PASEP Importação |
| `5629` ou `629` | **COFINS** | COFINS Importação |
| `5529` ou `529` | **ANTIDUMPING** | Antidumping |
| `7811` ou `811` | **TAXA_UTILIZACAO** | Taxa de Utilização do SISCOMEX |

### 🔍 Como Buscar Pagamentos da DI

**Query SQL:**
```sql
SELECT 
    dp.codigoReceita,
    dp.numeroRetificacao,
    dp.valorTotal,
    dp.dataPagamento,
    dpcr.descricao_receita
FROM Serpro.dbo.Di_Pagamento dp
LEFT JOIN Serpro.dbo.Di_pagamentos_cod_receitas dpcr 
    ON dpcr.cod_receita = dp.codigoReceita
WHERE dp.rootDiId = {dadosDiId}
```

**⚠️ IMPORTANTE:**
- A coluna `dataHoraPagamento` **NÃO EXISTE** - usar apenas `dataPagamento`
- O `dadosDiId` vem de `Di_Root_Declaracao_Importacao.dadosDiId`
- Para obter `dadosDiId`, incluir na query principal: `SELECT ... diRoot.dadosDiId ...`

### 📍 Onde Está Implementado

**Arquivo:** `services/sql_server_processo_schema.py`
- Função: `_buscar_di_completo()`
- Linha do mapeamento: ~365-378
- Query de pagamentos: ~349-361

**Arquivo:** `services/agents/processo_agent.py`
- Função: `_formatar_resposta_processo_dto()`
- Exibição de impostos: ~3254-3285

### 🔧 Correções Aplicadas (18/12/2025)

1. ✅ **Removida coluna inexistente**: `dataHoraPagamento` não existe, usar apenas `dataPagamento`
2. ✅ **Adicionado `dadosDiId` ao retorno**: Incluído no dict retornado por `_buscar_di_completo()`
3. ✅ **Mapeamento de códigos**: Implementado mapeamento completo de códigos para tipos de imposto
4. ✅ **Fallback por descrição**: Se código não estiver no mapeamento, usa `descricao_receita` da tabela `Di_pagamentos_cod_receitas`

### 📝 Exemplo de Uso

```python
# Buscar pagamentos da DI
from utils.sql_server_adapter import get_sql_adapter
from services.sql_server_processo_schema import _buscar_di_completo

sql_adapter = get_sql_adapter()
di_data = _buscar_di_completo(sql_adapter, '2507275811', None)

if di_data and di_data.get('pagamentos'):
    for pagamento in di_data['pagamentos']:
        print(f"{pagamento['tipo']}: R$ {pagamento['valor']:,.2f}")
```

### ⚠️ Notas Importantes

- **DUIMP e DI são equivalentes**: Um processo tem OU DUIMP OU DI, nunca ambos
- **Prioridade de busca**: SQL Server → Cache → API (API é bilhetada)
- **Todos os impostos estão no SQL Server**: Não é necessário consultar API para obter pagamentos
- **Taxa SISCOMEX**: É uma taxa, não um imposto (pode ser exibida separadamente do total de impostos)

---

## 📧 Sistema de Envio de Email com Confirmação

**⚠️ CRÍTICO:** Este sistema garante que TODOS os emails sejam confirmados pelo usuário antes do envio. Se perdermos essa informação, use este documento para recuperar rapidamente.

### 📋 Regra Obrigatória

**NUNCA enviar email sem confirmação do usuário.** Todas as funções de email (`enviar_email`, `enviar_email_personalizado`, `enviar_relatorio_email`) **SEMPRE** devem:
1. Mostrar preview do email primeiro
2. Pedir confirmação (sim/enviar)
3. Só enviar após confirmação explícita

### 🔍 Padrões de Detecção

O sistema detecta automaticamente quando o usuário pede para enviar informações por email. Padrões suportados:

#### Padrões com "esse/essa":
- "envia esse informacao para o email [email]"
- "envia essa informação para o email [email]"
- "envie esse informacao para o email [email]"
- "envie essa informação para o email [email]"
- "manda esse informacao para o email [email]"
- "mande essa informação para o email [email]"

#### Padrões sem "esse/essa":
- "enviar informacoes para email [email]"
- "enviar informações para email [email]"
- "enviar informacao para email [email]"
- "enviar informação para email [email]"
- "envia informacoes para o email [email]"
- "envia informações para o email [email]"

#### Padrões genéricos:
- "monte um email para [email]"
- "crie um email para [email]"
- "prepare um email para [email]"
- "envie um email para [email]"
- "mande um email para [email]"

### 🔄 Fluxo de Confirmação

```
1. Usuário pede: "envia esse informacao para o email helenomaffra@gmail.com"
   ↓
2. Sistema detecta padrão (precheck ou IA)
   ↓
3. Sistema busca informações completas do processo no histórico
   ↓
4. Sistema chama enviar_email_personalizado com confirmar_envio=false
   ↓
5. Sistema mostra preview do email ao usuário
   ↓
6. Sistema aguarda confirmação e **cria PendingIntent no SQLite** (`pending_intents`) como fonte da verdade
   ↓
7. Usuário confirma: "sim" ou "enviar"
   ↓
8. Sistema detecta confirmação e usa o PendingIntent do SQLite para chamar enviar_email_personalizado com confirmar_envio=true
   ↓
9. Email é enviado
```

### 📍 Onde Está Implementado

#### 1. EmailPrecheckService (`services/email_precheck_service.py`) ✅ **REFATORADO (19/12/2025)**

**Função:** `_precheck_envio_email_processo()`
- **Responsabilidade:** Detecta padrões de envio de email com informações de processo e tenta chamar a função diretamente
- **Padrões regex:** Detecta comandos como "envia essa informação para o email X"
- **Busca de conteúdo:** Busca última resposta com informações do processo no histórico
- **Chamada direta:** Tenta executar `enviar_email_personalizado` via `chat_service._executar_funcao_tool()`

**Outras funções principais:**
- `_precheck_envio_email_ncm()`: Email de classificação NCM + alíquotas
- `_precheck_envio_email_relatorio_generico()`: Email de relatório genérico
- `_precheck_envio_email()`: Email de resumo/briefing
- `_precheck_envio_email_livre()`: Email livre (texto ditado)

#### 2. Chat Service (`services/chat_service.py`)

**Função:** `processar_mensagem()`
- **Linha:** ~200-400 (aproximadamente)
- **Responsabilidade:** Gerencia fluxo de confirmação de email
- **Detecção de confirmação:** Verifica se última resposta foi preview de email
- **Estado persistente:** Fonte da verdade é `pending_intents` (SQLite). `ultima_resposta_aguardando_email` é apenas um fallback/estado em memória (pode se perder em refresh/reload).

### ⚠️ Nota Importante (múltiplos dispositivos/abas)

- Se você gerar o preview no PC e responder **“sim” no iPhone** (ou em outra aba), pode cair em **sessões diferentes (`session_id`)**.
- Nesse caso, o PendingIntent fica salvo para a sessão que gerou o preview, e a confirmação na outra sessão pode retornar: **“Nenhum email pendente encontrado”**.
- Regra prática: **preview e confirmação devem acontecer no mesmo chat/aba/dispositivo**.

#### 3. Tool Definitions (`services/tool_definitions.py`)

**Função:** `enviar_email_personalizado`
- **Linha:** ~1584-1625
- **Responsabilidade:** Define a tool para a IA
- **Descrição:** Inclui todos os padrões de detecção e regra obrigatória de confirmação
- **Parâmetro `confirmar_envio`:** Se `false`, mostra preview. Se `true`, envia email.

#### 4. Prompt Builder (`services/prompt_builder.py`)

**Função:** `system_prompt`
- **Linha:** ~101-108
- **Responsabilidade:** Instrui a IA sobre regras de email
- **Regra crítica:** Inclui instruções explícitas sobre confirmação obrigatória

### 🔧 Correções Aplicadas (18/12/2025)

1. ✅ **Padrões adicionados**: Adicionados padrões sem "esse/essa" ("enviar informacoes para email", "enviar informações para email", etc.)
2. ✅ **Precheck melhorado**: Precheck agora tenta chamar a função diretamente quando detecta padrão
3. ✅ **Fallback robusto**: Sistema extrai email, assunto e conteúdo do texto da IA se ela não chamar a função
4. ✅ **Busca de histórico**: Sistema busca informações completas do processo no histórico da conversa
5. ✅ **Estado persistente**: Estado de email aguardando confirmação é salvo em `_resultado_interno` para persistir entre mensagens
6. ✅ **Detecção de confirmação**: Sistema detecta confirmações como "sim", "enviar", "pode enviar", "ok", etc.

### 📝 Exemplo de Uso

```python
# 1. Usuário pede situação do processo
# Resposta: Mostra informações completas do processo ALH.0010/25

# 2. Usuário pede: "enviar informacoes para email helenomaffra@gmail.com"
# Sistema detecta padrão via precheck
# Sistema busca informações do processo no histórico
# Sistema chama enviar_email_personalizado com confirmar_envio=false
# Resposta: Mostra preview do email e pede confirmação

# 3. Usuário confirma: "sim"
# Sistema detecta confirmação
# Sistema chama enviar_email_personalizado com confirmar_envio=true
# Resposta: "Email enviado com sucesso"
```

### ⚠️ Notas Importantes

- **SEMPRE usar `confirmar_envio=false` na primeira chamada**: Isso garante que o preview seja mostrado antes do envio
- **Conteúdo completo obrigatório**: Quando enviar informações de processo, incluir TODOS os detalhes (CE, DI, valores, impostos, pendências, datas)
- **Estado persistente**: O estado de email aguardando confirmação é salvo em `_resultado_interno` para persistir entre mensagens
- **Fallback é crítico**: Mesmo se a IA não chamar a função, o sistema tenta extrair informações do texto e do histórico
- **Precheck tem prioridade**: O precheck tenta chamar a função diretamente antes de deixar a IA processar

## 🧮 Code Interpreter para Cálculos com Explicação (NOVO)

**✅ Implementado em:** 06/01/2026

### 📋 O que é?

Sistema híbrido que permite calcular impostos e outros valores usando **Code Interpreter da OpenAI** quando o usuário pede explicação detalhada, ou **Python local** para cálculos rápidos.

### 🎯 Como Funciona

O sistema detecta automaticamente se o usuário quer explicação detalhada:

- **Sem explicação** → Usa Python local (rápido, sem custo)
- **Com explicação** → Usa Code Interpreter (explicação passo a passo)

### 💬 Como Usar

#### Cálculo Rápido (Python Local):
```
👤 "calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283"
→ Resultado rápido, sem explicação
```

#### Cálculo com Explicação (Code Interpreter):
```
👤 "calcule os impostos explicando passo a passo"
👤 "calcule os impostos mostrando as fórmulas"
👤 "calcule os impostos detalhado"
👤 "quanto fica de imposto explicando como chegou"
→ Resultado com explicação detalhada passo a passo
```

### 🔑 Palavras-chave que Acionam Code Interpreter

Você **NÃO precisa** falar exatamente "explicando passo a passo". Qualquer uma dessas palavras aciona o Code Interpreter:

- ✅ "explicando" / "explicar"
- ✅ "detalhado" / "detalhar"
- ✅ "mostrando" / "mostrar"
- ✅ "fórmulas"
- ✅ "passo a passo"
- ✅ "como chegou" / "como calculou"
- ✅ "com explicação"

**Exemplos que funcionam:**
```
✅ "calcule os impostos explicando"
✅ "calcule os impostos detalhado"
✅ "calcule os impostos mostrando as fórmulas"
✅ "calcule os impostos passo a passo"
✅ "quanto fica de imposto explicando como chegou"
```

### ⚖️ Comparação: Python Local vs Code Interpreter

| Aspecto | Python Local | Code Interpreter |
|---------|--------------|------------------|
| **Velocidade** | ⚡ Instantâneo | 🐢 ~2-5 segundos |
| **Custo** | 💰 Grátis | 💸 ~$0.01-0.03 por cálculo |
| **Explicação** | ❌ Manual | ✅ Automática |
| **Flexibilidade** | ❌ Código fixo | ✅ Adapta-se ao prompt |
| **Validação** | ❌ Manual | ✅ Automática |

### 📊 Exemplo de Resposta do Code Interpreter

```
💰 CÁLCULO DE IMPOSTOS

1️⃣ CIF = 10,000 + 1,500 + 200 = USD 11,700
   CIF BRL = 11,700 × 5.5283 = R$ 64,681.11

2️⃣ II (18%):
   Base: CIF = R$ 64,681.11
   Fórmula: II = CIF × 18%
   Cálculo: 64,681.11 × 0.18 = R$ 11,642.60
   II BRL: R$ 11,642.60
   II USD: $ 2,105.11

... e assim por diante para IPI, PIS, COFINS
```

### 🔧 Arquivos Relacionados

- **`services/calculo_impostos_service.py`**: Cálculo Python local (rápido)
- **`services/agents/calculo_agent.py`**: Agent para Code Interpreter (explicação)
- **`services/responses_service.py`**: Integração com Responses API
- **`services/tool_definitions.py`**: Definições das tools
  - `calcular_impostos_ncm`: Cálculo rápido (Python local)
  - `calcular_com_code_interpreter`: Cálculo com explicação (Code Interpreter)
  - `executar_calculo_python`: Cálculo genérico com Python

### 📚 Documentação Detalhada

- **`docs/CODE_INTERPRETER_CALCULO_IMPOSTOS.md`**: Comparação detalhada e exemplos
- **`docs/COMO_ACIONAR_CODE_INTERPRETER.md`**: Como funciona internamente
- **`docs/VARIACOES_FRASES_CODE_INTERPRETER.md`**: Todas as variações de frases que funcionam
- **`docs/EXEMPLOS_USO_CODE_INTERPRETER.md`**: Exemplos práticos de uso

### 🧪 Teste Prático

Execute o script de teste para ver ambos os métodos em ação:

```bash
python3 scripts/test_code_interpreter_calculo_impostos.py
```

---

### 🔍 Extração de Categoria do Relatório Anterior

**⚠️ CRÍTICO:** Este documento descreve como o sistema extrai a categoria do relatório anterior quando o usuário diz "envia esse relatorio". Se o sistema usar categoria errada ou contexto antigo, use este documento como referência.

#### 📊 Como Funciona

Quando o usuário diz "envia esse relatorio para o email X", o sistema:

1. **Busca a última resposta do banco de dados:**
   - Query: `SELECT resposta FROM conversas_chat WHERE session_id = ? ORDER BY criado_em DESC LIMIT 1`
   - Obtém o texto completo da última resposta gerada

2. **Extrai a categoria do relatório anterior:**
   - **Padrão 1 (Título):** Busca no título do relatório
     - Padrão regex: `r'(?:PROCESSOS|O QUE TEMOS PRA HOJE|STATUS GERAL)[\s-]+([A-Z]{2,4})'`
     - Exemplos que funcionam:
       - "📋 PROCESSOS MV5 - STATUS GERAL" → Extrai "MV5"
       - "📅 O QUE TEMOS PRA HOJE - MV5 - 19/12/2025" → Extrai "MV5"
       - "📋 PROCESSOS BND - STATUS GERAL" → Extrai "BND"
   - **Padrão 2 (Conteúdo):** Se não encontrar no título, busca no conteúdo
     - Padrão regex: `r'\b([A-Z]{2,4})\s*\(\d+\s+processo\(s\)\)'`
     - Exemplos que funcionam:
       - "MV5 (5 processo(s))" → Extrai "MV5"
       - "BND (2 processo(s))" → Extrai "BND"

3. **Valida a categoria extraída:**
   - Chama `verificar_categoria_processo(categoria_extraida)` do `db_manager.py`
   - Só usa a categoria se for válida (existe no banco)

4. **Limpa contexto antigo:**
   - Limpa contexto de processo antigo: `limpar_contexto_sessao(session_id, tipo_contexto="processo_atual")`
   - Limpa contexto de categoria antigo: `limpar_contexto_sessao(session_id, tipo_contexto="categoria_atual")`
   - Isso evita usar contexto de conversas anteriores (ex: ALH.0011/25)

5. **Gera relatório com categoria correta:**
   - Usa a categoria extraída para chamar `obter_dashboard_hoje` ou `listar_processos_por_categoria`
   - Gera preview do email com o relatório correto

#### 🔧 Implementação

**Arquivo:** `services/chat_service.py`

**Função:** `_executar_funcao_tool()` → `enviar_relatorio_email` (linha ~1922)

**Código relevante:**
```python
# Detectar "envia esse relatorio"
if 'esse relatorio' in mensagem_lower or 'esse relatório' in mensagem_lower or 'envia esse' in mensagem_lower:
    # Buscar última resposta do banco
    cursor.execute('''
        SELECT resposta FROM conversas_chat 
        WHERE session_id = ? 
        ORDER BY criado_em DESC 
        LIMIT 1
    ''', (session_id_para_buscar,))
    
    # Extrair categoria do título
    padrao_categoria_titulo = r'(?:PROCESSOS|O QUE TEMOS PRA HOJE|STATUS GERAL)[\s-]+([A-Z]{2,4})'
    match_categoria = re.search(padrao_categoria_titulo, ultima_resposta_texto, re.IGNORECASE)
    
    # Se não encontrou, buscar no conteúdo
    if not categoria:
        padrao_categoria_conteudo = r'\b([A-Z]{2,4})\s*\(\d+\s+processo\(s\)\)'
        match_categoria_conteudo = re.search(padrao_categoria_conteudo, ultima_resposta_texto, re.IGNORECASE)
    
    # Validar categoria
    if verificar_categoria_processo(categoria_extraida):
        categoria = categoria_extraida
```

**Limpeza de contexto:**
```python
# Limpar contexto antigo quando detectar comando de relatório
eh_comando_relatorio = any(palavra in mensagem_lower_check for palavra in [
    'enviar relatorio', 'enviar relatório', 'enviar resumo', 
    'enviar briefing', 'enviar dashboard', 'envia esse relatorio', 
    'envia esse relatório'
])

if eh_comando_relatorio:
    limpar_contexto_sessao(session_id, tipo_contexto="categoria_atual")
    limpar_contexto_sessao(session_id, tipo_contexto="processo_atual")
```

#### ⚠️ Notas Importantes

1. **Ordem de extração:**
   - Primeiro tenta extrair do título (mais confiável)
   - Se não encontrar, tenta do conteúdo
   - Se não encontrar, deixa a IA decidir (pode usar categoria mencionada na mensagem)

2. **Validação obrigatória:**
   - Sempre valida a categoria extraída com `verificar_categoria_processo()`
   - Só usa se for categoria válida (evita usar "DO", "EM", "TOP", etc.)

3. **Limpeza de contexto:**
   - Sempre limpa contexto de processo e categoria antigos
   - Isso evita usar contexto de conversas anteriores (ex: ALH.0011/25 quando o relatório é sobre MV5)

4. **Logging:**
   - Registra quando categoria é extraída: `logger.info(f"✅ Categoria {categoria} extraída do relatório anterior")`
   - Facilita debug se houver problemas

#### 🐛 Troubleshooting

**Problema:** Sistema está usando categoria errada (ex: ALH quando deveria ser MV5)
- **Solução 1:** Verificar se a última resposta no banco contém o relatório correto
  ```sql
  SELECT resposta FROM conversas_chat 
  WHERE session_id = 'SESSION_ID' 
  ORDER BY criado_em DESC LIMIT 1;
  ```
- **Solução 2:** Verificar se os padrões regex estão corretos (linha ~1963-1975 em `chat_service.py`)
- **Solução 3:** Verificar se `verificar_categoria_processo()` está validando corretamente
- **Solução 4:** Verificar se o contexto antigo está sendo limpo (linha ~3885-3889)

**Problema:** Categoria não está sendo extraída
- **Solução 1:** Verificar se o formato do relatório está correto (deve ter "PROCESSOS [CATEGORIA]" ou "[CATEGORIA] (N processo(s))")
- **Solução 2:** Verificar se a categoria está em maiúsculas no relatório
- **Solução 3:** Verificar logs para ver se a extração está sendo tentada

**Problema:** Sistema está usando contexto antigo (ex: ALH.0011/25)
- **Solução:** Verificar se `limpar_contexto_sessao()` está sendo chamado corretamente (linha ~3887-3888)
- **Solução:** Verificar se o contexto está sendo limpo antes de gerar o relatório

**Problema:** IA não está chamando `enviar_relatorio_email`
- **Solução:** Verificar se padrões estão na descrição da tool (`services/tool_definitions.py`)
- **Solução:** Verificar se o prompt está instruindo a IA a usar a função (linha ~95-100 em `prompt_builder.py`)

### 🐛 Troubleshooting

**Problema:** IA não está chamando a função `enviar_email_personalizado`
- **Solução:** Verificar se padrões estão na descrição da tool (`services/tool_definitions.py`)
- **Solução:** Verificar se regra está no prompt (`services/prompt_builder.py`)
- **Solução:** EmailPrecheckService deve detectar e chamar diretamente (`services/email_precheck_service.py`)

**Problema:** Email sendo enviado sem confirmação
- **Solução:** Verificar se `confirmar_envio=false` está sendo usado na primeira chamada
- **Solução:** Verificar se fluxo de confirmação está funcionando (`services/chat_service.py`)

**Problema:** Email não contém informações completas do processo
- **Solução:** Verificar se busca de histórico está funcionando (`services/email_precheck_service.py`, método `_precheck_envio_email_processo()`)
- **Solução:** Verificar se descrição da tool instrui a incluir TODOS os detalhes (`services/tool_definitions.py`)

---

## 📋 Checklist de Instalação

- [ ] Projeto clonado/criado
- [ ] Dependências Python instaladas (`pip install -r requirements.txt`)
- [ ] Node.js instalado (`node --version`)
- [ ] Dependências Node.js instaladas (`npm install`)
- [ ] Arquivo `.env` criado e preenchido
- [ ] Certificado copiado para `certs/cert.pfx`
- [ ] Variáveis SQL Server adicionadas ao `.env`
- [ ] Conexão SQL Server testada (`npm run test-sql`) - opcional
- [ ] App testado (`python app.py`)
- [ ] Interface acessível em `http://localhost:5001/chat-ia`

---

## 🎯 Próximos Passos

Após a instalação básica:

1. **Testar verificação de fontes de dados** - Use "verificar fontes de dados" no chat
2. **Testar aprendizado de regras** - Ensine uma regra e veja se é aplicada depois
3. **Testar contexto persistente** - Mencione um processo e depois peça "trazer todos os dados"
4. **Testar consultas analíticas** - Faça perguntas sobre dados e veja SQL gerado
5. **Testar consultas salvas** - Salve uma consulta e depois peça para "rodar aquele relatório"
6. **Testar conexão SQL Server** - Verificar se processos são carregados (requer rede do escritório)
7. **Testar comportamento offline** - Desconecte da rede e veja como mAIke informa limitações
8. **Testar autenticações** - Portal Único e Integra Comex
9. **Testar Chat IA** - Fazer perguntas e verificar respostas
10. **Configurar produção** - Ajustar variáveis para ambiente de produção

### 📝 Notas Importantes:

- **Trabalhando Offline?** O SQLite funciona offline e contém processos recentes do Kanban
- **Precisa de Processos Históricos?** Conecte-se à rede do escritório para acessar SQL Server
- **Não sabe se está conectado?** Use "verificar fontes de dados" no chat

---

## 🚀 Deploy em Produção

### 📋 Análise de Produção

Antes de colocar em produção para múltiplos usuários, consulte:

- **`docs/ANALISE_PRODUCAO.md`** - Análise completa da aplicação
  - ✅ Pontos fortes (não precisam refatoração)
  - ⚠️ Pontos que precisam atenção
  - 🔧 Ajustes recomendados
  - 📊 Capacidade vs. Recomendações

### 🚀 Guia de Deploy

Para deploy em servidor, siga:

- **`docs/DEPLOY_PRODUCAO.md`** - Guia completo de deploy
  - Pré-requisitos
  - Instalação passo a passo
  - Configuração WSGI (Gunicorn/Waitress)
  - Configuração Nginx
  - Sistema de serviço (systemd)
  - Monitoramento e backup

### 📚 Documentação Completa

- **`docs/DOCUMENTACAO_COMPLETA.md`** - Documentação técnica completa
  - Arquitetura detalhada
  - Funcionalidades
  - Manutenção
  - Troubleshooting

---

## ✅ Status Atual

**Funcionalidades Implementadas:**
- ✅ Chat conversacional com IA
- ✅ Consulta de processos (Kanban + SQL Server)
- ✅ Consulta de documentos (DUIMP, CE, DI, CCT)
- ✅ Criação automática de DUIMP (CE e CCT)
- ✅ Geração de PDF de extrato DUIMP/CE/DI
- ✅ Geração de PDF de extratos bancários (BB e Santander) no formato contábil padrão (07/01/2026)
- ✅ Limpeza automática de PDFs
- ✅ Cache inteligente de APIs
- ✅ Sincronização automática do Kanban
- ✅ Sistema de notificações ativas (mudanças de status)
- ✅ Aprendizado dinâmico de categorias de processos
- ✅ Conversão IATA → ISO (aeroporto → país)

**Pronto para Produção:**
- ✅ Funcionalmente completo
- ⚠️ Recomendado: usar servidor WSGI (Gunicorn/Waitress)
- ⚠️ Recomendado: rate limiting
- ⚠️ Recomendado: HTTPS (Nginx)

---

**Última atualização:** 07/01/2026  
**Versão:** 1.7.1

### 📝 Status das Documentações

**✅ Documentações Atualizadas Recentemente:**
- `README.md` - Atualizado em 08/01/2026 (sincronização Santander, descrição completa)
- `PROMPT_AMANHA.md` - Atualizado em 08/01/2026 (mudanças de hoje)
- `docs/API_DOCUMENTATION.md` - Atualizado em 08/01/2026 (endpoints de banco)
- `AGENTS.md` - Atualizado em 08/01/2026 (serviços de banco)
- `docs/PLANEJAMENTO_BANCO_DADOS_MAIKE.md` - Criado em 07/01/2026
- `docs/SISTEMA_NOTIFICACOES_HUMANIZADAS.md` - Criado em 07/01/2026
- `docs/INDICE_DOCUMENTACOES.md` - Criado em 07/01/2026

**⚠️ Documentações que Podem Precisar de Atualização:**
- `AGENTS.md` - Verificar se todos os agents estão documentados
- `docs/API_DOCUMENTATION.md` - Verificar se todas as APIs estão documentadas
- `docs/MANUAL_COMPLETO.md` - Verificar se funcionalidades estão atualizadas

**📋 Para Revisão:**
- Ver `PROMPT_AMANHA.md` para checklist de revisão completa

### 💾 Backup da Aplicação

**✅ Último Backup:** 07/01/2026 às 21:55:10  
**📁 Localização:** `backups/mAIke_assistente_backup_20260106_215510/`  
**📄 Script:** `scripts/fazer_backup.sh`

**💡 Próximo Backup Recomendado:** Antes de fazer mudanças grandes ou após implementações importantes

### 🔄 Continuidade Entre Agentes

**Para novos agentes continuando este projeto:**
- Leia `PROMPT_AMANHA.md` primeiro (contém TODO o contexto)
- Leia `INSTRUCOES_CONTINUIDADE.md` para instruções completas
- Consulte `docs/INDICE_DOCUMENTACOES.md` para ver todas as documentações

**Documentos essenciais:**
1. `PROMPT_AMANHA.md` ⭐ **LEIA PRIMEIRO** - Contexto completo e checklist
2. `INSTRUCOES_CONTINUIDADE.md` ⭐ **SEGUNDO** - Instruções para novos agentes
3. `README.md` ⭐ **TERCEIRO** - Visão geral do projeto
4. `docs/INDICE_DOCUMENTACOES.md` ⭐ **QUARTO** - Índice de todas as documentações

**Como fazer backup:**
```bash
bash scripts/fazer_backup.sh
```

**Frequência sugerida:** Semanal ou antes de mudanças grandes

**Conteúdo do backup:**
- ✅ Código-fonte completo (app.py, services/, utils/, etc.)
- ✅ Templates HTML
- ✅ Documentações (docs/)
- ✅ Scripts utilitários
- ✅ Requirements.txt
- ✅ Arquivos de configuração (.env, se existir)
- ✅ Legislações importadas (legislacao_files/)

**Excluído do backup:**
- ❌ Arquivos temporários (__pycache__, *.pyc, etc.)
- ❌ Banco de dados SQLite (*.db)
- ❌ Logs (*.log)
- ❌ node_modules/
- ❌ Arquivos PDF temporários (downloads/)

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

## 📋 PENDÊNCIAS PARA 17/12/2025

### 🎯 Relatório de Averbacoes - Finalização

**Status:** ⚠️ **PENDENTE** - Funcionalidade parcialmente implementada, aguardando validação completa

**O que já foi feito (16/12/2025):**
- ✅ Serviço `RelatorioAverbacoesService` criado (`services/relatorio_averbacoes_service.py`)
- ✅ Endpoint `POST /api/relatorio/averbacoes` implementado
- ✅ Busca de processos por mês e categoria
- ✅ Extração de dados da DI com prioridade: Cache → SQL Server → API (API é bilhetada)
- ✅ Busca de dados do CE do SQL Server (todos os campos necessários: `paisProcedencia`, `dataEmissao`, `tipo`, `descricaoMercadoria`)
- ✅ Busca de pagamentos/impostos da DI do SQL Server (`Di_Pagamento` e `Di_pagamentos_cod_receitas`)
- ✅ Busca de frete da DI do SQL Server (`Di_Frete` - `valorTotalDolares`, `totalReais`)
- ✅ Busca de seguro da DI do SQL Server (`Di_Seguro` - `valorTotalDolares`, `valorTotalReais`)
- ✅ Cálculos de Despesas (10% de Custo + Frete) e Lucros (10% de Custo + Frete + Despesas)
- ✅ Conversão de Impostos BRL→USD usando PTAX
- ✅ Geração de arquivo Excel no formato correto
- ✅ Função `consultar_averbacao_processo` para exibir averbação no chat (processo a processo)
- ✅ Correção: Total de impostos exclui Taxa SISCOMEX (é uma taxa, não um imposto)
- ✅ Correção: Frete e seguro sendo buscados e exibidos corretamente no chat
- ✅ Correção: Complementação automática do cache quando dados vêm do SQL Server
- ✅ Documentação atualizada: `docs/MAPEAMENTO_SQL_SERVER.md` com todas as descobertas (CE, DI pagamentos, frete, seguro)

**O que falta fazer:**
- ⚠️ **Validação completa do relatório Excel**: Testar o relatório completo com múltiplos processos de diferentes categorias
- ⚠️ **Validação de cálculos**: Conferir se os cálculos estão corretos comparando com relatórios anteriores/externos
- ⚠️ **Testes de borda**: Testar com processos sem frete, sem seguro, sem impostos, sem CE
- ⚠️ **Otimização**: Verificar performance com muitos processos (pode precisar de paginação ou processamento assíncrono)
- ⚠️ **Limpeza de código**: Verificar se há código comentado ou não utilizado após todas as mudanças
- ⚠️ **Remover arquivos de debug**: `debug_calculos_bnd0030.py` e `debug_calculos_bnd0030_v2.py` podem ser removidos após validação (NOTA: `_v2.py` aqui é apenas nomenclatura, não se refere à V2 separada)

**Correções recentes (17/12/2025):**
- ✅ **Nome do navio no relatório de averbação**: Corrigido para buscar do SQL Server (`Di_Transporte.nomeVeiculo`) antes de consultar API bilhetada. Prioridade: SQL Server → API.
- ✅ **Busca de pagamentos/impostos**: Relatório agora busca pagamentos da DI do SQL Server (`Di_Pagamento`) antes de usar API.
- ✅ **Busca de frete e seguro**: Relatório busca frete e seguro do SQL Server (`Di_Frete`, `Di_Seguro`) antes de usar API.

**Arquivos relacionados:**
- `services/relatorio_averbacoes_service.py` - Serviço principal do relatório (corrigido para buscar nome do navio do SQL Server)
- `services/agents/processo_agent.py` - Função `_consultar_averbacao_processo` e `_formatar_averbacao_chat`
- `app.py` - Endpoint `/api/relatorio/averbacoes` (linha ~1287)
- `docs/MAPEAMENTO_SQL_SERVER.md` - Documentação completa do SQL Server (atualizada com CE, pagamentos, frete, seguro, transporte/navio)
- `recuperar_contexto.py` - Script para recuperar contexto anterior do agente (novo)

**Notas importantes:**
- A funcionalidade de averbação no chat está funcionando corretamente e validada
- O relatório Excel foi testado parcialmente (BND.0030/25)
- Prioridade de busca implementada: Cache → SQL Server → API (API é bilhetada, usar por último)
- Todos os dados necessários estão disponíveis no SQL Server (não precisa consultar API para frete, seguro, impostos, **nome do navio**)
- Taxa SISCOMEX é exibida separadamente mas não entra no total de impostos (correto)
- **Correção 17/12/2025**: Nome do navio agora é buscado do SQL Server (`Di_Transporte.nomeVeiculo`) antes de consultar API

---

### 🔧 Refatorações Pendentes

**Status:** ⚠️ **PENDENTE** - Melhorias de código identificadas, aguardando implementação

**Pendências identificadas:**

1. **`services/agents/processo_agent.py` (linha ~3506)**
   - ⚠️ **TODO**: Buscar bloqueios do cache do CE
   - **Contexto**: Função que busca dados do CE pode melhorar buscando bloqueios do cache local
   - **Prioridade**: Baixa (funcionalidade já funciona, é uma otimização)

2. **`services/relatorio_averbacoes_service.py` (linha ~973)**
   - ⚠️ **TODO**: Expandir mapeamento ou buscar de tabela/API
   - **Contexto**: Mapeamento de dados pode ser expandido para cobrir mais casos
   - **Prioridade**: Média (pode melhorar cobertura de dados)

3. **`services/tool_router.py` (linha ~124)**
   - ⚠️ **TODO**: Migrar `obter_valores_ce` quando necessário
   - **Contexto**: Função marcada para migração futura
   - **Prioridade**: Baixa (não está sendo usada atualmente)

4. **`db_manager.py` - Função `obter_movimentacoes_hoje`**
   - ⚠️ **Otimização**: Função muito grande (~1.100 linhas) com múltiplas responsabilidades
   - **Sugestão**: Considerar dividir em funções menores:
     - `_buscar_dis_registradas_hoje()`
     - `_buscar_duimps_registradas_hoje()`
     - `_buscar_mudancas_status_hoje()`
     - `_atualizar_status_dis_final()`
   - **Prioridade**: Média (funciona, mas pode melhorar manutenibilidade)

**Notas:**
- Todas as pendências são melhorias opcionais, não bloqueiam funcionalidades
- Código está funcional e testado
- Refatorações podem ser feitas gradualmente conforme necessidade

---

### 📝 Notas de Desenvolvimento (16/12/2025)

#### ✅ Sistema de Averbacao - Implementação Completa
**Data:** 16/12/2025  
**Status:** ✅ Funcional no chat, ⚠️ Relatório Excel aguardando validação completa

**Funcionalidades implementadas:**
- ✅ Consulta de averbação por processo no chat (`averbacao processo BND.0030/25`)
- ✅ Exibição completa de dados do CE (Porto Origem, País, Porto Destino, Data Emissão, Tipo, Descrição)
- ✅ Exibição completa de dados da DI (Número, Navio, Retificação)
- ✅ Exibição de valores (Custo, Frete, Seguro, Despesas, Lucros) em USD e BRL
- ✅ Exibição detalhada de impostos (II, IPI, PIS, COFINS, Antidumping, Taxa SISCOMEX) em BRL e USD
- ✅ Total de impostos excluindo Taxa SISCOMEX (correto - é uma taxa, não um imposto)
- ✅ Exibição de cotação PTAX usada para conversão

**Descobertas e correções:**
- ✅ Descoberto que todos os campos do CE estão no SQL Server (`Ce_Root_Conhecimento_Embarque`)
- ✅ Descoberto que pagamentos/impostos da DI estão no SQL Server (`Di_Pagamento`)
- ✅ Descoberto que frete da DI está no SQL Server (`Di_Frete`)
- ✅ Descoberto que seguro da DI está no SQL Server (`Di_Seguro`)
- ✅ Implementada complementação automática do cache quando dados vêm do SQL Server
- ✅ Corrigido cálculo do total de impostos para excluir Taxa SISCOMEX

**Arquivos modificados:**
- `services/relatorio_averbacoes_service.py` - Serviço principal
- `services/agents/processo_agent.py` - Função de averbação no chat
- `services/sql_server_processo_schema.py` - Busca de frete e seguro
- `docs/MAPEAMENTO_SQL_SERVER.md` - Documentação atualizada

#### 🔧 Correção: Fechamento do Dia - DIs/DUIMPs Registradas Hoje
**Data:** 16/12/2025  
**Problema:** Relatório de fechamento do dia mostrava "DIs/DUIMPs REGISTRADAS HOJE: Nenhuma" mesmo quando havia DIs/DUIMPs registradas. Além disso, o status exibido era o status do momento do registro, não o status atualizado.

**Correções implementadas:**
- ✅ **Conexão SQL Server no Mac**: Substituído uso direto de `pyodbc` pelo adapter Node.js (`SQLServerAdapter`), que funciona no Mac
- ✅ **Query de DIs registradas**: Ajustada para usar vínculo correto via `id_importacao` conforme mapeamento do SQL Server (`docs/MAPEAMENTO_SQL_SERVER.md`)
- ✅ **Status atualizado**: Implementada busca do status atual da DI em três pontos:
  - Ao buscar DIs do SQL Server
  - Ao buscar DIs do cache SQLite
  - Na passagem final após remover duplicatas
- ✅ **Ordenação melhorada**: Queries priorizam registros com data de desembaraço e ordenam por data de desembaraço DESC para garantir status mais atualizado
- ✅ **Remoção de duplicatas**: Mantém apenas a DI mais recente por número
- ✅ **Formatação**: DIs e DUIMPs aparecem juntas na seção "DIs/DUIMPs REGISTRADAS HOJE"

**Resultado:**
- DIs/DUIMPs registradas hoje são encontradas corretamente
- Status exibido é o status atualizado (ex: `DI_DESEMBARACADA`), não o status do momento do registro
- Alinhamento entre "PROCESSOS DESEMBARAÇADOS HOJE" e "DIs/DUIMPs REGISTRADAS HOJE"

**Arquivos modificados:**
- `db_manager.py` - Função `obter_movimentacoes_hoje` (busca de DIs/DUIMPs registradas hoje)
- `services/agents/processo_agent.py` - Função `_formatar_fechamento_dia` (formatação do relatório)

#### 🔧 Correção: Contexto de Categoria no Fechamento do Dia
**Data:** 16/12/2025  
**Problema:** Comando "finaliza o dia" estava mantendo categoria do contexto anterior mesmo após "reset"

**Solução:**
- ✅ Atualizada descrição da função `fechar_dia` para não usar categoria do contexto quando não mencionada
- ✅ Adicionada regra explícita no prompt do sistema sobre exceção para fechamento do dia

**Arquivos modificados:**
- `services/tool_definitions.py` - Descrição da função `fechar_dia`
- `services/prompt_builder.py` - Regra explícita no prompt

### 📝 Notas de Desenvolvimento (15/12/2025)

#### 🔧 Refatoração do `chat_service.py`
**Status:** Em andamento (~40% completo)

**Objetivo:** Reduzir complexidade do `chat_service.py` movendo lógica de negócio para serviços especializados.

**Progresso:**
- ✅ Serviços criados: `DuimpService`, `VinculacaoService`, `ProcessoListService`, `DocumentoService`, `ProcessoRepository`, `ProcessoStatusService`
- 🔄 Próximo: Migrar funções de vinculação complexas e consultas específicas
- 📊 Meta: Reduzir de ~8.000 linhas para <5.000 linhas

**Arquivos de referência:**
- `services/duimp_service.py` - Exemplo de serviço migrado
- `services/vinculacao_service.py` - Exemplo de serviço migrado
- `docs/MAPEAMENTO_SQL_SERVER.md` - Documentação completa do SQL Server (inclui correção da busca de DI)

#### 🐛 Correção Crítica: Busca de DI
**Data:** 15/12/2025  
**Tempo investido:** ~7.5 horas  
**Problema:** Processos não exibiam DI na UI mesmo quando `numero_di` estava preenchido.

**Causa raiz:**
- Formato diferente do `numero_di` entre tabelas:
  - `PROCESSO_IMPORTACAO.numero_di`: `25/0340890-6` (com `/` e `-`)
  - `Di_Dados_Gerais.numeroDi`: `2503408906` (sem `/` e `-`)

**Solução:**
- Normalização automática do `numero_di` antes de buscar
- Fallback para busca via `id_importacao` quando necessário
- Documentação completa em `docs/MAPEAMENTO_SQL_SERVER.md`

**Arquivos modificados:**
- `services/sql_server_processo_schema.py`:
  - `_buscar_di_completo()` - Normalização do `numero_di`
  - `buscar_processo_consolidado_sql_server()` - Fallback via `id_importacao`

### 💾 Cópia de Segurança

**⚠️ IMPORTANTE:** Uma cópia de segurança completa desta aplicação foi criada em:
- **Nome da cópia:** `Chat-IA-Independente -V1012`
- **Data do backup:** 10/12/2025
- **Conteúdo:** Versão completa e funcional da aplicação antes das atualizações do dia 10/12/2025

Esta cópia contém todas as funcionalidades implementadas até a data do backup e pode ser usada como referência ou para rollback se necessário.

### 🆕 Funcionalidades Recentes (Versão 1.5.0 - 15/12/2025):

#### 🧠 Estratégia de Modelos Inteligente
- ✅ **Seleção Automática de Modelo**: Sistema detecta automaticamente se é pergunta analítica ou operacional
  - **Modo Operacional** (gpt-4o-mini): Respostas sobre processos, CE, DI, DUIMP, "o que temos pra hoje", notificações
  - **Modo Analítico** (gpt-5.1): Consultas analíticas SQL, consultas salvas, regras aprendidas, análises complexas
  - Configuração via `.env`: `OPENAI_MODEL_DEFAULT` e `OPENAI_MODEL_ANALITICO`
- ✅ **Detecção Automática**: Sistema identifica perguntas analíticas por padrões (ranking, média, relatório, etc.)

#### 🔗 Link entre Regras Aprendidas e Consultas Salvas
- ✅ **Rastreamento de Uso**: Quando uma consulta salva é executada, incrementa uso da regra aprendida relacionada
- ✅ **Contexto de Regras**: Consultas salvas podem ser vinculadas a regras aprendidas (`regra_aprendida_id`)
- ✅ **Métricas de Uso**: Sistema rastreia `vezes_usado` e `ultimo_usado_em` para regras e consultas

#### 📚 Resumo de Aprendizado por Sessão
- ✅ **Função `obter_resumo_aprendizado`**: Mostra o que a mAIke aprendeu em uma sessão
- ✅ **Endpoint `/api/chat/resumo-aprendizado`**: Retorna regras aprendidas e consultas salvas da sessão
- ✅ **Formatação Automática**: Resumo formatado em texto legível com estatísticas

#### 📊 Modo Reunião
- ✅ **Função `gerar_resumo_reuniao`**: Gera resumo executivo completo para reunião
- ✅ **Análises Combinadas**: Combina atrasos, pendências, DUIMPs registradas, ETA alterado
- ✅ **Texto Executivo**: Gera texto formatado com Resumo Executivo, Pontos de Atenção, Próximos Passos
- ✅ **Uso de Modo Analítico**: Automaticamente usa modelo mais forte para gerar análises

#### 🎙️ Briefing do Dia com TTS
- ✅ **Endpoint `/api/chat/briefing-dia`**: Gera briefing do dia com áudio TTS integrado
- ✅ **TTS Automático**: Gera arquivo MP3 usando OpenAI TTS
- ✅ **Retorno Completo**: Retorna texto + URL do áudio + base64 do áudio
- ✅ **Configurável**: Usa `OPENAI_TTS_MODEL` e `OPENAI_TTS_VOICE` do `.env`

#### 📈 Observabilidade
- ✅ **Relatórios de Uso**: Função `obter_relatorio_observabilidade` gera relatórios completos
- ✅ **Consultas Bilhetadas**: Mostra custo total, quantidade, por tipo, por período
- ✅ **Consultas Salvas**: Mostra quais são mais usadas, quais nunca foram usadas
- ✅ **Regras Aprendidas**: Mostra quais são mais aplicadas, quais nunca foram usadas
- ✅ **Identificação de Oportunidades**: Facilita identificar o que pode ser removido ou otimizado

### 🆕 Funcionalidades Anteriores (Versão 1.4.0 - 14/12/2025):

#### 🎓 Sistema de Aprendizado de Regras e Contexto Persistente
- ✅ **Aprendizado de Regras do Usuário**: A mAIke pode aprender regras e definições que você ensina
  - Quando você diz "usar campo destfinal como confirmação de chegada", a mAIke salva essa regra
  - Regras são aplicadas automaticamente em consultas futuras
  - Exemplo: Se você ensina "destfinal = confirmação de chegada", depois quando perguntar "quais VDM chegaram?", a mAIke usa `WHERE data_destino_final IS NOT NULL` automaticamente
- ✅ **Contexto Persistente de Sessão**: A mAIke mantém contexto entre mensagens
  - Se você menciona um processo (ex: "buscar vdm.0004/25"), ela salva esse contexto
  - Quando você diz "trazer todos os dados", ela já sabe qual processo está em foco
  - Contexto é salvo por sessão (session_id)
- ✅ **Melhorias na Comunicação Natural**: Respostas mais diretas e contextuais
  - Respostas mais curtas e naturais (não verbosas)
  - Entende contexto implícito das perguntas
  - Detecta quando você está testando e responde adequadamente
- ✅ **Consultas Analíticas SQL**: A mAIke pode gerar e executar consultas SQL analíticas
  - Gera consultas SQL baseadas em perguntas em linguagem natural
  - Executa consultas de forma segura (apenas SELECT, com validação)
  - Suporta SQL Server (quando disponível) e SQLite (fallback)
  - Limita resultados automaticamente para evitar sobrecarga
- ✅ **Consultas Salvas (Relatórios Reutilizáveis)**: Salva consultas SQL ajustadas como relatórios
  - Você pode pedir para salvar uma consulta que funcionou bem
  - Depois pode pedir para "rodar aquele relatório" e a mAIke encontra e executa
  - Consultas salvas são reutilizáveis e podem ter parâmetros

#### 🔧 Arquitetura e Código
- ✅ **Novo Módulo `learned_rules_service.py`**: Gerencia regras aprendidas do usuário
  - Localização: `services/learned_rules_service.py`
  - Funções: `salvar_regra_aprendida()`, `buscar_regras_aprendidas()`, `formatar_regras_para_prompt()`
  - Tabela: `regras_aprendidas` no SQLite
- ✅ **Novo Módulo `context_service.py`**: Gerencia contexto persistente de sessão
  - Localização: `services/context_service.py`
  - Funções: `salvar_contexto_sessao()`, `buscar_contexto_sessao()`, `formatar_contexto_para_prompt()`
  - Tabela: `contexto_sessao` no SQLite
- ✅ **Novo Módulo `analytical_query_service.py`**: Executa consultas SQL analíticas de forma segura
  - Localização: `services/analytical_query_service.py`
  - Funções: `executar_consulta_analitica()`, `validar_sql_seguro()`, `aplicar_limit_seguro()`
  - Validação: Apenas SELECT, sem DDL/DML, apenas tabelas permitidas
- ✅ **Novo Módulo `saved_queries_service.py`**: Gerencia consultas SQL salvas
  - Localização: `services/saved_queries_service.py`
  - Funções: `salvar_consulta_personalizada()`, `buscar_consulta_personalizada()`, `listar_consultas_salvas()`
  - Tabela: `consultas_salvas` no SQLite
- ✅ **Integração no ChatService**: Todos os novos serviços integrados
  - Regras aprendidas são incluídas automaticamente no prompt
  - Contexto de sessão é incluído automaticamente no prompt
  - Novas tools adicionadas: `salvar_regra_aprendida`, `executar_consulta_analitica`, `salvar_consulta_personalizada`, `buscar_consulta_personalizada`
- ✅ **Melhorias no Prompt**: Instruções mais claras sobre comunicação natural
  - Detecção automática de perguntas de teste
  - Instruções para respostas curtas e diretas
  - Exemplos de respostas BOM vs RUIM

### 🆕 Funcionalidades Anteriores (Versão 1.3.0 - 12/12/2025):

#### 📊 Sistema de Verificação de Fontes de Dados
- ✅ **Verificação Automática de Disponibilidade**: Sistema verifica automaticamente quais fontes de dados estão disponíveis na inicialização
  - SQLite (Local/Offline) - sempre disponível se o arquivo existir
  - SQL Server (Rede do Escritório) - disponível apenas quando conectado à rede
  - API Kanban - verifica se URL está configurada
  - API Portal Único - verifica se credenciais estão configuradas
- ✅ **Tool `verificar_fontes_dados`**: Nova tool disponível para a mAIke verificar status das fontes de dados
  - Retorna status detalhado de cada fonte
  - Inclui recomendações baseadas na disponibilidade
  - Pode ser chamada pelo usuário ou automaticamente pela mAIke
- ✅ **Comportamento Inteligente da mAIke**: A mAIke agora detecta quando SQL Server não está disponível
  - Quando usuário pede "processos históricos", "processos antigos" ou "todos os processos"
  - Informa claramente que SQL Server não está disponível (fora da rede do escritório)
  - Oferece alternativas automaticamente (SQLite para processos recentes, APIs externas)
  - NUNCA retorna apenas "nenhum processo encontrado" sem explicar a limitação
- ✅ **Contexto Automático no Prompt**: Status das fontes de dados é incluído automaticamente no contexto da mAIke
  - A mAIke sabe quais fontes estão disponíveis antes de processar
  - Pode tomar decisões inteligentes sobre qual fonte usar
  - Informa ao usuário sobre limitações quando necessário

#### 🔧 Arquitetura e Código
- ✅ **Novo Módulo `data_sources_checker.py`**: Utilitário centralizado para verificação de fontes de dados
  - Localização: `services/utils/data_sources_checker.py`
  - Funções: `verificar_fontes_dados_disponiveis()`, `formatar_status_fontes_dados()`
  - Testa conexão SQL Server com query simples
  - Verifica configuração de APIs via variáveis de ambiente
- ✅ **Integração no ChatService**: Verificação automática na inicialização
  - Status armazenado em `self.fontes_dados`
  - Disponível para todas as funções do chat
  - Logging automático do status na inicialização

### 🆕 Funcionalidades Anteriores (Versão 1.2.0 - 10/12/2025):

#### 📅 Dashboard "O QUE TEMOS PRA HOJE"
- ✅ **Dashboard Consolidado do Dia**: Resumo completo de informações relevantes para o dia atual
  - Processos chegando hoje (com ETA confirmado ou previsto)
  - Processos prontos para registro DI/DUIMP (com classificação de atraso: crítico, moderado, recentes)
  - Pendências ativas (ICMS, Frete, AFRMM, LPCO, Bloqueio CE) - agrupadas por tipo e categoria
  - DUIMPs em análise
  - Processos com ETA alterado (atraso/adiantado) - apenas processos ativos
  - Alertas recentes (com status atual de DI/CE/DUIMP)
  - Sugestões de ações priorizadas
- ✅ **Filtros**: Por categoria, modal (aéreo/marítimo), apenas pendências
- ✅ **Agrupamento Inteligente**: Processos agrupados por categoria e tipo de pendência para melhor legibilidade
- ✅ **Controle de Atraso de Registro**: Calcula e destaca processos com atraso crítico (>7 dias) ou moderado (3-7 dias)
- ✅ **Validação de LPCO**: Processos com LPCO não deferido não aparecem em "prontos para registro" e são listados em pendências
- ✅ **Regra Legal ICMS**: ICMS só é considerado pendente após desembaraço da DI/DUIMP
- ✅ **Histórico de ETA (POD-first)**: Detecta mudanças de ETA usando eventos do porto de destino (POD), priorizando `DISC`/`ARRV` no destino (ignora escalas intermediárias). Detalhes em `docs/EXPLICACAO_HISTORICO_ETA.md`.
- ✅ **Filtro de Processos Ativos**: ETA alterado mostra apenas processos ativos/relevantes (não processos antigos)

#### 🔧 Melhorias e Correções
- ✅ **Correção de Cálculo de Atraso de ETA**: Agora compara corretamente ETA original vs atual do porto de destino final (ignora escalas intermediárias)
- ✅ **Suporte a Categorias Alfanuméricas**: Aceita categorias como "MV5" (não apenas letras)
- ✅ **Melhoria na Extração de Categoria**: Melhor detecção de categoria em frases como "o que temos de mv5 pra hoje?"
- ✅ **Priorização de ETA**: Prioriza eventos DISC (Discharge) no porto de destino, depois dataPrevisaoChegada, depois ARRV
  - ✅ Manutenção: se o cache do SQLite ficar inconsistente (navio do primeiro trecho em vez do POD), rode `python3 scripts/rebuild_shipgov2_cache.py` (dry-run) e `--apply` para aplicar.
- ✅ **Sistema de Ajuda**: Comando "ajuda" ou "help" mostra guia completo de funcionalidades e palavras-chave
- ✅ **Precheck de Comandos**: Detecção prioritária de comandos críticos ("o que temos pra hoje", "ajuda", "criar duimp") antes do processamento da IA

#### 🐛 Correções de Bugs
- ✅ **Correção de Interpretação de Comandos**: "registrar duimp" não é mais interpretado como busca por processos "registrados"
- ✅ **Correção de Confirmação de DUIMP**: Sistema sempre mostra resumo antes de criar DUIMP (não cria diretamente)
- ✅ **Correção de Extração de Categoria**: "DO" não é mais extraído como categoria em "registrar duimp do mv5.0022/25"
- ✅ **Correção de Filtro de Pendências**: Pendências agora são filtradas corretamente (não mostra tudo)
- ✅ **Correção de Alertas Recentes**: Mostra status atual em vez de apenas "Status alterado"
- ✅ **Correção de ETA em "CHEGANDO HOJE"**: Considera processos com ETA de hoje mesmo sem dataDestinoFinal confirmada

### 🆕 Funcionalidades Anteriores (Versão 1.1.0):

- ✅ **Criação Automática de DUIMP**: Suporte completo para CE (marítimo) e CCT (aéreo)
- ✅ **Sistema de Notificações Ativas**: Notifica mudanças de status, pendências, ETA, etc.
- ✅ **Aprendizado Dinâmico**: Sistema aprende novas categorias de processos automaticamente
- ✅ **Sincronização de Modelo**: Frontend sincroniza automaticamente com modelo do backend (.env)
- ✅ **Conversão IATA → ISO**: Conversão automática de códigos de aeroporto para países
- ✅ **Refatoração de Código**: Utilitários centralizados (JSON, DB helpers)
- ✅ **Documentação Completa**: API documentation e guias de refatoração para produção

---

## 💳 Accounts and Taxes - Pagamentos Santander (NOVO - 13/01/2026)

**Data:** 13/01/2026  
**Status:** ✅ **IMPLEMENTADO** (Aguardando testes no sandbox)

### 📋 Visão Geral

Implementação completa de **Accounts and Taxes** via API de Pagamentos do Santander, estendendo a mesma base da API de TED. Inclui suporte para:

- **Bank Slip Payments** (Boletos)
- **Barcode Payments** (Códigos de Barras)
- **Pix Payments** (PIX - DICT, QR Code, Beneficiário)
- **Vehicle Taxes Payments** (IPVA)
- **Taxes by Fields Payments** (GARE ICMS, GARE ITCMD, DARF, GPS)

### 🎯 Funcionalidades

**Cada tipo de pagamento suporta:**
- ✅ **Iniciar**: Criar pagamento em estado `PENDING_VALIDATION`
- ✅ **Efetivar**: Confirmar e autorizar pagamento
- ✅ **Consultar**: Verificar status e detalhes
- ✅ **Listar**: Listar pagamentos realizados (com filtros)

**Funcionalidades Especiais:**
- ✅ **PIX com 3 modos**: DICT (chave PIX), QR Code, Beneficiário
- ✅ **Consulta de débitos Renavam**: Para IPVA e multas veiculares
- ✅ **Impostos por campos**: GARE, DARF, GPS com campos customizados

### 🏗️ Arquitetura

**Reutilização da API Existente:**
- Mesma base da API de TED (`utils/santander_payments_api.py`)
- Mesmo workspace e credenciais
- Mesmos certificados mTLS
- Isolado da API de Extratos

**Arquivos Criados/Modificados:**
- `utils/santander_payments_api.py` - Métodos estendidos
- `services/santander_payments_service.py` - Serviço de negócio
- `services/tool_definitions.py` - Tool definitions
- `services/agents/santander_agent.py` - Handlers
- `services/tool_router.py` - Mapeamento

### ⚙️ Configuração

**Mesma configuração do TED:**

```env
# ==========================================
# SANTANDER - PAGAMENTOS (Accounts and Taxes usa a mesma API)
# ==========================================
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token

# Credenciais (mesmas do TED)
SANTANDER_PAYMENTS_CLIENT_ID=seu_client_id
SANTANDER_PAYMENTS_CLIENT_SECRET=seu_client_secret

# Certificados (mesmos do TED)
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.pem
# OU
SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado.pfx
SANTANDER_PAYMENTS_PFX_PASSWORD=senha001

# Workspace (mesmo do TED)
SANTANDER_WORKSPACE_ID=workspace_id
```

**⚠️ IMPORTANTE:** O workspace precisa ter os tipos de pagamento ativados:
- `bankSlipPaymentsActive: true` - Para boletos
- `barCodePaymentsActive: true` - Para códigos de barras
- `pixPaymentsActive: true` - Para PIX
- `vehicleTaxesPaymentsActive: true` - Para IPVA
- `taxesByFieldPaymentsActive: true` - Para GARE, DARF, GPS

### 📝 Como Usar

**Exemplos de comandos:**

```
# Pagar boleto
"pagar boleto código 34191090000012345678901234567890123456789012"

# Pagar PIX
"fazer pix de 100 reais para chave pix@exemplo.com"

# Pagar IPVA
"pagar IPVA renavam 12345678901 estado SP ano 2026"

# Pagar GARE
"pagar GARE ICMS campo01 123 campo02 456"
```

### 📚 Documentação

- **Documentação completa:** `docs/IMPLEMENTACAO_ACCOUNTS_TAXES_SANTANDER.md`
- **Documentação TED:** `docs/IMPLEMENTACAO_TED_SANTANDER_FINAL.md`

---

## 💾 Sistema de Pending Intents Persistentes (NOVO - 14/01/2026)

**Status:** ✅ **IMPLEMENTADO**

### 📋 Visão Geral

Sistema de **pending intents** (intenções pendentes) que permite persistir ações pendentes de confirmação (email, DUIMP, etc.) no banco de dados, garantindo que o estado não se perda em refresh ou interrupções.

**Problema resolvido:**
- ❌ **Antes:** Estado em memória (`ultima_resposta_aguardando_email`, `ultima_resposta_aguardando_duimp`) se perdia em refresh
- ✅ **Depois:** Estado persistido no banco com TTL (2h), sobrevive a refresh e interrupções

### 🎯 Funcionalidades

**Persistência:**
- ✅ Ações pendentes são salvas no banco SQLite (`pending_intents`)
- ✅ TTL de 2 horas (configurável)
- ✅ Limpeza automática de intents expiradas

**Recuperação:**
- ✅ Sistema busca pending intent automaticamente quando usuário confirma ação
- ✅ Funciona mesmo após refresh ou interrupção
- ✅ Suporta múltiplos tipos de ação (email, DUIMP, etc.)

**Validação:**
- ✅ Detecção de duplicatas via hash SHA-256
- ✅ Status tracking (pending, executed, cancelled, expired)

### 🏗️ Arquitetura

**Tabela SQLite:**
```sql
CREATE TABLE pending_intents (
    intent_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    action_type TEXT NOT NULL,  -- 'send_email', 'create_duimp', etc.
    tool_name TEXT NOT NULL,
    args_normalizados TEXT,  -- JSON
    payload_hash TEXT,  -- Hash SHA-256 para detecção de duplicatas
    preview_text TEXT,
    status TEXT DEFAULT 'pending',  -- 'pending', 'executed', 'cancelled', 'expired'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    executed_at TIMESTAMP,
    observacoes TEXT
)
```

**Serviços:**
- `services/pending_intent_service.py` - CRUD completo de pending intents
- `services/handlers/confirmation_handler.py` - Integração com sistema de confirmação

**📚 Documentação (Fase 1 + Fase 2A/2B):**
- `docs/CORRECAO_MARCAR_COMO_EXECUTANDO.md` - Correção do método `marcar_como_executando()` com lock atômico
- `docs/REFINAMENTOS_FINAIS_FASE_1.md` - Refinamentos finais da Fase 1 (transações, status, recovery)
- `docs/CORRECOES_PEGADINHAS_FASE_1.md` - Correções de "pegadinhas" críticas (timestamp, SQL, formato)
- `docs/ANALISE_FASE_2_IMPLEMENTACAO.md` - Análise para implementar Fase 2 (resolução automática de contexto)
- `docs/FASE_2A_IMPLEMENTACAO.md` - Implementação da Fase 2A (ToolGateService: allowlist + feature flag + injeção de report_id)
- `docs/FASE_2B_IMPLEMENTACAO.md` - Implementação da Fase 2B (REPORT_META fallback + TTL + validações)

**Integração:**
- `ChatService` cria pending intent quando gera preview de email/DUIMP
- `ConfirmationHandler` busca pending intent quando usuário confirma ação
- Pending intent é marcado como `executed` após sucesso

### 📝 Como Funciona

**Fluxo de Email:**
1. Usuário pede: "envie email para cliente@exemplo.com"
2. Sistema gera preview e cria pending intent no banco
3. Estado também salvo em memória (compatibilidade)
4. Usuário confirma: "sim, pode enviar"
5. Sistema busca pending intent do banco (se memória perdida)
6. Email enviado e pending intent marcado como `executed`

**Fluxo de DUIMP:**
1. Usuário pede: "crie DUIMP do BND.0084/25"
2. Sistema gera preview e cria pending intent no banco
3. Estado também salvo em memória (compatibilidade)
4. Usuário confirma: "sim, pode criar"
5. Sistema busca pending intent do banco (se memória perdida)
6. DUIMP criada e pending intent marcado como `executed`

### ⚙️ Configuração

**TTL padrão:** 2 horas (configurável em `services/pending_intent_service.py`)

```python
DEFAULT_TTL_HOURS = 2  # Pode ser ajustado conforme necessário
```

**Limpeza automática:**
- Intents expiradas são marcadas como `expired` automaticamente
- Método `limpar_intents_expiradas()` pode ser chamado periodicamente

### 📚 Documentação

- **Análise completa:** `docs/ANALISE_GATE_VALIDACAO.md`
- **Fluxo de validação:** `docs/FLUXO_VALIDACAO_GATE.md`
- **Problema resolvido:** `docs/ANALISE_PROBLEMA_CONTEXTO_PERDIDO.md`

---

## 🏦 Integração com Banco do Brasil (NOVO)

**Data:** 06/01/2026  
**Status:** ✅ Integração completa implementada

### 📋 Visão Geral

O sistema integra com as **APIs do Banco do Brasil**:
- ✅ **API de Extratos**: Consulta de extratos bancários, saldos e movimentações
- ✅ **API de Pagamentos em Lote**: Pagamentos em lote (boletos, TED, PIX, etc.)

A integração usa **OAuth 2.0 Client Credentials** e suporta criação de cadeia completa de certificados para APIs que requerem mTLS (como Pagamentos).

---

## 🚢 Mercante / AFRMM (RPA) (NOVO)

Automação do **pagamento AFRMM** no Mercante via RPA (`scripts/mercante_bot.py`) com:

- **pending intent** (confirmação “sim”)
- Clique automático em **Pagar AFRMM** + **OK** do popup
- Detecção de sucesso pela tela: **“Débito efetuado com sucesso”**
- Geração de **comprovante (print PNG)** em `downloads/mercante/` e link via `/api/download/mercante/...`

📚 Documentação: `docs/integracoes/MERCANTE_AFRMM.md`

### 📋 **GUIA COMPLETO: Como Configurar APIs do Banco do Brasil**

**⚠️ IMPORTANTE:** Cada API do BB requer uma aplicação **SEPARADA** no portal. Siga este processo para cada API que você quiser usar.

#### **Passo 1: Criar Aplicação no Portal do BB**

1. Acesse: https://developers.bb.com.br/
2. Faça login com suas credenciais
3. Clique em **"Criar Aplicação"** ou **"Nova Aplicação"**
4. Preencha os dados:
   - **Nome da Aplicação**: Ex: "Chat IA - Extratos" ou "Chat IA - Pagamentos"
   - **Descrição**: Descrição da aplicação
   - **Ambiente**: Selecione **"Teste"** inicialmente
5. Clique em **"Criar"**

**✅ Resultado:** Aplicação criada com status **"Em teste"** e um **ID de aplicação** (ex: 246367)

---

#### **Passo 2: Gerar Credenciais OAuth**

1. Na aplicação criada, vá na aba **"Credenciais"**
2. Clique em **"Gerar Credenciais OAuth"** ou **"Criar Credenciais"**
3. Anote as credenciais geradas:
   - **Client ID**: JWT token longo (ex: `eyJpZCI6...`)
   - **Client Secret**: JWT token longo (ex: `eyJpZCI6...`)
   - **App Key**: Chave curta (ex: `1f8386d110934639a2790912c5bba906`)

**⚠️ IMPORTANTE:** O Client Secret é exibido **apenas uma vez**. Salve imediatamente!

---

#### **Passo 3: Autorizar no Sandbox**

1. Ainda na aplicação, vá na aba **"APIs"** ou **"Sandbox"**
2. Procure pela API desejada (ex: "Extratos" ou "Pagamentos em Lote")
3. Clique no botão **"Autorizar"** ou **"Solicitar Acesso"**
4. Aguarde aprovação (geralmente imediata para sandbox)

**✅ Resultado:** API autorizada para a aplicação

---

#### **Passo 4: Configurar Credenciais no .env**

Adicione as credenciais no arquivo `.env` na raiz do projeto:

**Para API de Extratos:**
```env
# Banco do Brasil - Extratos API
BB_CLIENT_ID=eyJpZCI6...  # Client ID gerado no passo 2
BB_CLIENT_SECRET=eyJpZCI6...  # Client Secret gerado no passo 2
BB_DEV_APP_KEY=1f8386d110934639a2790912c5bba906  # App Key gerado no passo 2
BB_ENVIRONMENT=sandbox  # ou production
BB_TEST_AGENCIA=1505  # Agência padrão (sem dígito verificador)
BB_TEST_CONTA=1348  # Conta padrão (sem dígito verificador)
```

**Para API de Pagamentos em Lote:**
```env
# Banco do Brasil - Pagamentos em Lote API (CREDENCIAIS SEPARADAS!)
BB_PAYMENTS_CLIENT_ID=eyJpZCI6...  # Client ID da aplicação de Pagamentos
BB_PAYMENTS_CLIENT_SECRET=eyJpZCI6...  # Client Secret da aplicação de Pagamentos
BB_PAYMENTS_DEV_APP_KEY=1f8386d110934639a2790912c5bba906  # App Key da aplicação de Pagamentos
BB_PAYMENTS_ENVIRONMENT=sandbox  # ou production
```

**⚠️ IMPORTANTE:** 
- Cada API tem credenciais **SEPARADAS** (não há fallback)
- A API de Extratos usa `BB_CLIENT_ID`, `BB_CLIENT_SECRET`, `BB_DEV_APP_KEY`
- A API de Pagamentos usa `BB_PAYMENTS_CLIENT_ID`, `BB_PAYMENTS_CLIENT_SECRET`, `BB_PAYMENTS_DEV_APP_KEY`

---

#### **Passo 5: Enviar Certificados (Obrigatório para APIs mTLS)**

**⚠️ IMPORTANTE:** A API de **Pagamentos em Lote** requer certificados mTLS. A API de **Extratos** não requer certificados.

**5.1 Verificar se os Certificados Já Foram Extraídos**

Os certificados já foram extraídos anteriormente. Verifique:

```bash
cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb
ls -la cadeia_completa_para_importacao.pem
```

Se o arquivo existir, pule para o passo 5.3.

**5.2 Extrair Certificados (Se Necessário)**

Se os certificados não foram extraídos, siga o guia completo:
- **Documentação:** `EXTRAIR_CERTIFICADO_BB.md`
- **Resumo:** `docs/COMO_ENVIAR_CERTIFICADOS_BB_PAGAMENTOS.md`

**5.3 Enviar Certificados no Portal do BB**

1. Acesse: https://developers.bb.com.br/
2. Selecione a aplicação **correta** (ex: ID 246367 para Pagamentos)
3. Vá na aba **"Certificado"** (menu lateral)
4. Clique em **"Importar cadeia completa"**
5. Selecione o arquivo:
   ```
   /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb/cadeia_completa_para_importacao.pem
   ```
6. Clique em **"Enviar"**

**✅ Resultado:** Certificados enviados e aguardando aprovação (até 3 dias úteis)

**⚠️ IMPORTANTE:** 
- Os certificados são os **MESMOS** para todas as APIs do BB
- Você só precisa enviá-los **UMA VEZ** no portal
- Mas envie para a aplicação **CORRETA** (cada API tem sua própria aplicação)

---

#### **Passo 6: Verificar Configuração**

Após configurar tudo, teste a integração:

```bash
# Testar API de Extratos
python3 -c "from utils.banco_brasil_api import BancoBrasilExtratoAPI, BancoBrasilConfig; config = BancoBrasilConfig(); api = BancoBrasilExtratoAPI(config); print('✅ Extratos OK')"

# Testar API de Pagamentos
python3 testes/test_bb_pagamento_lote.py
```

---

### 🎯 **Resumo Rápido**

**Para cada API do BB que você quiser usar:**

1. ✅ Criar aplicação no portal (status "Em teste")
2. ✅ Gerar credenciais OAuth (Client ID, Secret, App Key)
3. ✅ Autorizar API no sandbox (botão "Autorizar")
4. ✅ Configurar credenciais no `.env` (variáveis específicas por API)
5. ✅ Enviar certificados (se API requerer mTLS - apenas Pagamentos)

**⚠️ Lembre-se:** Cada API = Aplicação separada = Credenciais separadas!

---

### 🔑 Funcionalidades

- ✅ Consulta de extratos bancários por período
- ✅ Consulta de saldo atual da conta
- ✅ **Geração de PDF de extratos no formato contábil padrão** (07/01/2026)
  - Colunas: Data, Histórico (com quebra de linha), Crédito, Débito, Saldo acumulado
  - Layout em paisagem (A4 landscape) para melhor visualização
  - Suporta múltiplas contas do BB
- ✅ Suporte a OAuth 2.0 Client Credentials
- ✅ Sistema de criação de cadeia completa de certificados (para APIs mTLS)

### 📝 Como Usar

**No chat:**
- `"extrato bb"` ou `"extrato banco do brasil"` - Consulta extrato bancário
- `"extrato bb de 30/12/25"` - Extrato de um dia específico
- `"extrato bb de 01/12/25 a 31/12/25"` - Extrato de um período
- `"extrato bb conta 2"` - Consulta segunda conta configurada
- `"extrato bb conta 43344"` - Consulta conta específica
- `"saldo bb"` - Consulta saldo atual da conta

**💡 Múltiplas Contas:** Para adicionar novas contas do BB na mesma agência, **NÃO é necessária nova autorização**. Basta configurar `BB_TEST_CONTA_2` no `.env` e usar "conta 2" ou o número da conta diretamente nas consultas.

### 🔐 Cadeia Completa de Certificados

**⚠️ IMPORTANTE:** Algumas APIs do Banco do Brasil (como Pagamentos) requerem **mTLS (mutual TLS)** com cadeia completa de certificados.

#### Processo Completo

1. **Extrair Certificado da Empresa**
   ```bash
   cd .secure/certificados_bb
   openssl pkcs12 -in "../eCNPJ 4PL (valid 23-03-26) senha001.pfx" \
     -clcerts -nokeys -out certificado_empresa.pem \
     -passin pass:senha001 -legacy
   ```

2. **Baixar Certificados Intermediários e Raiz**
   - Sites: https://www.gov.br/iti/pt-br/assuntos/repositorio ou https://www.safeweb.com.br/repositorio
   - Certificados necessários:
     - **AC SAFEWEB RFB v5** (intermediário)
     - **AC Raiz Brasileira v5** (raiz)

3. **Criar Cadeia Completa (Automático)**
   ```bash
   cd .secure/certificados_bb
   ./criar_cadeia_com_arquivos_encontrados.sh
   ```

4. **Enviar ao Portal BB**
   - Acesse: https://app.developers.bb.com.br/#/aplicacoes/[ID]/certificado/enviar
   - Clique em "Importar cadeia completa"
   - Selecione: `cadeia_completa_para_importacao.pem`

#### Estrutura da Cadeia

A cadeia completa deve conter **3 certificados** na ordem:

1. **Certificado da Empresa** (4PL)
2. **AC SAFEWEB RFB v5** (Intermediário)
3. **AC Raiz Brasileira v5** (Raiz)

**Formato:** Apenas blocos `-----BEGIN CERTIFICATE-----` e `-----END CERTIFICATE-----` (sem metadados)

### 📚 Documentação Completa

Para mais detalhes, consulte:
- **`docs/integracoes/INTEGRACAO_BANCO_BRASIL.md`** - Documentação completa da integração (Extratos)
  - O que a API exige
  - O que você precisa solicitar
  - Configuração e credenciais
  - Autenticação OAuth 2.0
  - **Seção completa sobre cadeia de certificados** (passo a passo)
  - Troubleshooting e problemas comuns
- **`docs/CREDENCIAIS_BB_PAGAMENTOS.md`** - Guia de credenciais para API de Pagamentos em Lote
- **`docs/COMO_ENVIAR_CERTIFICADOS_BB_PAGAMENTOS.md`** - Guia passo a passo para enviar certificados ao portal
- **`docs/COMO_TESTAR_BB_PAGAMENTOS.md`** - Como testar a API de Pagamentos em Lote
- **`docs/TROUBLESHOOTING_BB_PAGAMENTOS.md`** - Troubleshooting de problemas comuns
- **`docs/COMO_VERIFICAR_SCOPE_BB_PAGAMENTOS.md`** - Como verificar e autorizar scopes no portal
- **`EXTRAIR_CERTIFICADO_BB.md`** - Guia completo para extrair certificados do arquivo .pfx

### ⚠️ **Lições Aprendidas - Troubleshooting Final (13/01/2026)**

**⚠️ IMPORTANTE:** Ao integrar novas APIs do Banco do Brasil, lembre-se destes pontos críticos:

#### **1. Status HTTP 201 é Válido para Token OAuth**
- ✅ **Aceitar status 200 E 201** para criação de token OAuth
- ❌ **NÃO tratar 201 como erro** - `201 Created` é um status válido para criação de token
- **Código correto:**
  ```python
  if response.status_code not in [200, 201]:
      # Tratar como erro
  ```

#### **2. Verificação SSL em Ambiente Sandbox**
- ✅ **Desabilitar verificação SSL apenas em sandbox** (certificado auto-assinado)
- ✅ **Manter verificação SSL ativa em produção** (segurança)
- **Código correto:**
  ```python
  verify_ssl = self.config.environment != "sandbox"
  response = requests.get(url, headers=headers, cert=cert, timeout=30, verify=verify_ssl)
  ```
- **Suprimir aviso SSL:**
  ```python
  import urllib3
  urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
  ```

#### **3. Scopes Corretos para API de Pagamentos**
- ✅ **Usar scopes específicos** com prefixo `pagamentos-lote.*` (com "s")
- ❌ **NÃO usar** `pagamento-lote` (sem "s" - incorreto)
- **Scopes corretos:**
  - `pagamentos-lote.lotes-requisicao`
  - `pagamentos-lote.lotes-info`
  - `pagamentos-lote.boletos-requisicao`
  - `pagamentos-lote.boletos-info`
  - `pagamentos-lote.transferencias-requisicao`
  - `pagamentos-lote.transferencias-info`
  - `pagamentos-lote.transferencias-pix-requisicao`
  - `pagamentos-lote.transferencias-pix-info`
  - `pagamentos-lote.pix-info`
  - `pagamentos-lote.guias-codigo-barras-requisicao`
  - `pagamentos-lote.guias-codigo-barras-info`
  - `pagamentos-lote.pagamentos-guias-sem-codigo-barras-requisicao`
  - `pagamentos-lote.pagamentos-guias-sem-codigo-barras-info`
  - `pagamentos-lote.pagamentos-info`
  - `pagamentos-lote.pagamentos-codigo-barras-info`
  - `pagamentos-lote.cancelar-requisicao`
  - `pagamentos-lote.devolvidos-info`
  - `pagamentos-lote.lancamentos-info`

#### **4. Verificar Scopes no Portal**
- ✅ **Sempre verificar** se os scopes estão autorizados no portal do BB
- ✅ **Autorizar todos os scopes necessários** antes de testar
- **Como verificar:** `docs/COMO_VERIFICAR_SCOPE_BB_PAGAMENTOS.md`

#### **5. Certificados mTLS**
- ✅ **Certificados são os mesmos** para todas as APIs do BB
- ✅ **Enviar apenas uma vez** no portal (mas para a aplicação correta)
- ✅ **Aguardar aprovação** (até 3 dias úteis)
- **Como enviar:** `docs/COMO_ENVIAR_CERTIFICADOS_BB_PAGAMENTOS.md`

#### **6. Credenciais Separadas por API**
- ✅ **Cada API = Aplicação separada = Credenciais separadas**
- ❌ **NÃO há fallback** entre APIs (Extratos vs Pagamentos)
- **Variáveis corretas:**
  - Extratos: `BB_CLIENT_ID`, `BB_CLIENT_SECRET`, `BB_DEV_APP_KEY`
  - Pagamentos: `BB_PAYMENTS_CLIENT_ID`, `BB_PAYMENTS_CLIENT_SECRET`, `BB_PAYMENTS_DEV_APP_KEY`

### ⚙️ Configuração

**Variáveis de ambiente necessárias:**
```env
BB_DEV_APP_KEY=sua_gw_dev_app_key_aqui
BB_CLIENT_ID=seu_client_id_oauth
BB_CLIENT_SECRET=seu_client_secret_oauth
BB_BASE_URL=https://api-extratos.bb.com.br/extratos/v1
BB_TOKEN_URL=https://oauth.hm.bb.com.br/oauth/token
BB_ENVIRONMENT=production  # ou sandbox

# Contas Padrão (Opcional - para facilitar consultas)
BB_TEST_AGENCIA=1505      # Agência padrão (sem dígito verificador)
BB_TEST_CONTA=1348        # Conta padrão (sem dígito verificador)
BB_TEST_CONTA_2=43344     # Segunda conta (opcional - mesma agência)
# ✅ IMPORTANTE: Para adicionar novas contas do BB na mesma agência, 
#    NÃO é necessária nova autorização. Basta configurar BB_TEST_CONTA_2 
#    e usar "conta 2" ou o número da conta diretamente nas consultas.
```

### ✅ Checklist de Implementação

- [ ] Criar conta no Portal do Desenvolvedor BB (https://developers.bb.com.br)
- [ ] Registrar aplicativo
- [ ] Solicitar acesso à API de Extratos
- [ ] Obter `gw-dev-app-key`, Client ID e Client Secret
- [ ] Configurar variáveis de ambiente
- [ ] Testar em ambiente de homologação
- [ ] (Opcional) Criar cadeia de certificados para APIs mTLS
- [ ] Solicitar acesso à produção
- [ ] Testar em produção

---

## 🎨 UI/UX - Menu Drawer e Comandos de Voz/Texto (NOVO - 07/01/2026)

**Status:** ✅ **IMPLEMENTADO E FUNCIONANDO**

### 📋 O que foi implementado

#### 1. **Menu Lateral (Drawer)**
- ✅ Menu lateral deslizante da direita
- ✅ Animação suave de abertura/fechamento
- ✅ Overlay escuro ao abrir
- ✅ Fecha com ESC ou clicando no overlay
- ✅ Design responsivo (max-width: 90vw em mobile)
- ✅ Gradiente no header do menu
- ✅ Ícones e descrições claras
- ✅ Hover effects nos itens
- ✅ Transições suaves

#### 2. **Detecção de Comandos de Voz/Texto**
- ✅ `"maike menu"` → abre o menu
- ✅ `"maike quero conciliar banco"` → abre conciliação bancária
- ✅ `"maike quero sincronizar banco"` → abre sincronização de extratos
- ✅ `"maike quero importar legislação"` → abre importação de legislação
- ✅ `"maike configurações"` → abre configurações
- ✅ Comandos detectados **antes** do processamento pela IA
- ✅ Resposta rápida sem passar pela IA
- ✅ Mantém a experiência natural de chat

#### 3. **Header Simplificado**
- ✅ Um único botão de menu (☰) substitui todos os outros botões
- ✅ Interface mais limpa e focada no chat
- ✅ Badge de consultas pendentes (se houver) também abre o menu

#### 4. **Menu Organizado por Categorias**
- **Financeiro:**
  - Sincronizar Extratos
  - Conciliação Bancária
- **Documentos:**
  - Importar Legislação
- **Sistema:**
  - Configurações
  - Consultas Pendentes
- **Ajuda:**
  - O que posso fazer?

#### 5. **Integração com mAIke**
- ✅ Comandos detectados antes do processamento pela IA
- ✅ Resposta rápida sem passar pela IA
- ✅ Mantém a experiência de chat natural
- ✅ Sistema de detecção de intenções via `MessageIntentService`

### 📝 Como Usar

#### Via Comando de Voz/Texto:
- `"maike menu"` - Abre o menu lateral
- `"maike quero conciliar banco"` - Abre modal de conciliação bancária
- `"maike quero sincronizar banco"` - Abre modal de sincronização de extratos
- `"maike quero importar legislação"` - Abre modal de importação de legislação
- `"maike configurações"` - Abre modal de configurações

#### Via Botão:
- Clique no botão **☰** no header para abrir o menu

#### Atalhos:
- **ESC** - Fecha o menu quando aberto
- **Click no overlay** - Fecha o menu clicando fora dele

### 🎨 Design

- Menu lateral com animação suave de deslizamento
- Gradiente no header do menu para destaque visual
- Ícones e descrições claras para cada opção
- Hover effects nos itens do menu para feedback visual
- Responsivo: adapta-se a diferentes tamanhos de tela (max-width: 90vw em mobile)
- Transições suaves em todas as interações

### 🔜 Próximos Passos (Opcional)

- Adicionar mais comandos de voz (ex: "maike mostrar processos")
- Adicionar atalhos de teclado (ex: Ctrl+M para menu)
- Personalizar cores do menu
- Adicionar animações mais elaboradas

---

## 💸 Transferências TED via Santander (NOVO - 12/01/2026)

**Data:** 12/01/2026  
**Status:** ✅ **IMPLEMENTADO E TESTADO NO SANDBOX**

### 📋 Visão Geral

Implementação completa de transferências TED via **API de Pagamentos do Santander**, totalmente isolada da API de Extratos existente. A implementação foi testada com sucesso no ambiente sandbox e está pronta para produção após configuração adequada.

### 🎯 Funcionalidades

- ✅ **Criação de Workspaces**: Criar e gerenciar workspaces de pagamentos
- ✅ **Iniciar TED**: Criar transferência TED em estado `READY_TO_PAY`
- ✅ **Efetivar TED**: Confirmar e autorizar transferência TED
- ✅ **Consultar TED**: Verificar status e detalhes de uma TED específica
- ✅ **Listar TEDs**: Listar todas as TEDs realizadas (com filtros)
- ✅ **Suporte a certificados .pfx**: Extração automática para mTLS
- ✅ **Validações completas**: CPF/CNPJ, descrição, workspace

### 🏗️ Arquitetura

**Isolamento Completo:**
- API de Extratos: `utils/santander_api.py` (existente)
- API de Pagamentos: `utils/santander_payments_api.py` (NOVO)
- Credenciais separadas: `SANTANDER_*` vs `SANTANDER_PAYMENTS_*`
- Tokens OAuth2 separados (não interferem entre si)

### 🐛 Erros Encontrados e Soluções

#### 1. ❌ Descrição do Workspace > 30 caracteres

**Erro:**
```
400 Bad Request
"_message": "A Descrição deve ter no máximo 30 caracteres"
```

**Causa:** Descrição padrão tinha 36 caracteres, mas API limita a 30.

**Solução:**
- Limitar descrição a 30 caracteres automaticamente
- Truncar se exceder o limite

**Arquivo:** `services/santander_payments_service.py` (linha ~218)

**Lição:** ⚠️ **SEMPRE validar limites da API antes de enviar dados.**

---

#### 2. ❌ CPF Inválido

**Erro:**
```
400 Bad Request
"_message": "Número de documento do recebedor inválido"
```

**Causa:** CPF de teste `12345678901` não passa na validação da API (todos dígitos diferentes).

**Solução:**
- Validar formato básico de CPF (não pode ser todos iguais)
- Rejeitar CPFs inválidos antes de enviar à API

**Arquivo:** `services/santander_payments_service.py` (linha ~403)

**CPF válido para teste:** `00993804713` ✅

**Lição:** ⚠️ **CPF precisa ser válido, não apenas ter 11 dígitos. Use CPFs válidos para teste.**

---

#### 3. ❌ Workspace Errado Sendo Usado

**Problema:**
- Workspace criado: `1f625459-b4d1-4a1f-9e61-2ff5a75eb665` (PAYMENTS)
- Workspace usado: `d8bb7199-aaba-49ac-bb59-3f8bd5582ad0` (DIGITAL_CORBAN)

**Causa:** `_verificar_workspace()` pegava o primeiro workspace da lista, não priorizava PAYMENTS.

**Solução:**
- Priorizar workspaces PAYMENTS com `bankTransferPaymentsActive=true`
- Configurar `SANTANDER_WORKSPACE_ID` no `.env` para garantir uso correto

**Arquivo:** `services/santander_payments_service.py` (linha ~82)

**Lição:** ⚠️ **NÃO usar primeiro workspace da lista. Priorizar workspace correto ou configurar explicitamente.**

---

#### 4. ❌ Certificados mTLS Não Configurados

**Erro:**
```
403 Forbidden
SSL: CERTIFICATE_VERIFY_FAILED
```

**Causa:** Certificados não encontrados nos caminhos configurados ou formato incorreto.

**Solução:**
- Adicionado suporte a arquivos `.pfx` (igual ao Banco do Brasil)
- Fallback automático: `SANTANDER_PAYMENTS_CERT_FILE` → `SANTANDER_CERT_FILE`

**Arquivo:** `utils/santander_payments_api.py` (método `_extrair_pfx_para_pem`)

**Lição:** ⚠️ **Sempre suportar múltiplos formatos de certificado (.pfx, .pem + .key).**

---

#### 5. ❌ Logs Insuficientes para Debug

**Problema:**
- Erros 400/403 sem detalhes da resposta da API
- Difícil identificar o problema

**Solução:**
- Logar body completo antes de enviar
- Logar resposta completa em caso de erro
- Formatar erros de validação de forma legível

**Arquivo:** `utils/santander_payments_api.py` (métodos `criar_workspace` e `iniciar_ted`)

**Lição:** ⚠️ **SEMPRE logar request e response completos para facilitar debug.**

---

### 📝 Como Usar

#### No Chat:

**Workspaces:**
- `"listar workspaces do santander"` - Lista todos os workspaces
- `"criar workspace santander agencia 0001 conta 130392838 tipo PAYMENTS"` - Cria workspace

**TED:**
- `"fazer ted de 100 reais para conta 1234 agencia 5678 banco 001 nome joão silva cpf 00993804713"` - Inicia TED
- `"efetivar ted 4ef8791d-415a-4987-9206-4553a8f1d609"` - Efetiva TED iniciada
- `"consultar ted 4ef8791d-415a-4987-9206-4553a8f1d609"` - Consulta status de TED
- `"listar teds do santander"` - Lista TEDs realizadas

### ⚙️ Configuração

**Variáveis de ambiente necessárias (SANDBOX):**
```env
# ==========================================
# SANTANDER - PAGAMENTOS (SANDBOX/TESTE)
# ==========================================
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token

# Credenciais de SANDBOX
SANTANDER_PAYMENTS_CLIENT_ID=seu_client_id_sandbox
SANTANDER_PAYMENTS_CLIENT_SECRET=seu_client_secret_sandbox

# Certificados (usar os mesmos do extrato ou configurar separadamente)
SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado.pfx
SANTANDER_PFX_PASSWORD=senha001

# Workspace (opcional - será criado automaticamente se não configurado)
SANTANDER_WORKSPACE_ID=workspace_id_sandbox
```

### 🚀 Passos para Produção

**⚠️ IMPORTANTE: Em produção, TEDs movimentam dinheiro real!**

#### 1. Credenciais de Produção

**No Portal de Desenvolvedor do Santander:**
1. Acesse: https://developer.santander.com.br
2. Crie uma nova aplicação para **Pagamentos** (separada da de Extratos)
3. Obtenha:
   - `Client ID` de produção
   - `Client Secret` de produção

**Configure no `.env`:**
```env
SANTANDER_PAYMENTS_BASE_URL=https://trust-open.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-open.api.santander.com.br/auth/oauth/v2/token
SANTANDER_PAYMENTS_CLIENT_ID=client_id_producao
SANTANDER_PAYMENTS_CLIENT_SECRET=client_secret_producao
```

#### 2. Certificados mTLS de Produção

**Requisitos:**
- Certificado ICP-Brasil tipo A1
- Válido e não expirado
- Com chave privada

**Opções:**
1. **Arquivo .pfx** (RECOMENDADO):
   ```env
   SANTANDER_PAYMENTS_CERT_PATH=/path/to/certificado_producao.pfx
   SANTANDER_PFX_PASSWORD=senha_do_certificado
   ```

2. **Certificado e chave separados**:
   ```env
   SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert_producao.pem
   SANTANDER_PAYMENTS_KEY_FILE=/path/to/key_producao.pem
   ```

**⚠️ IMPORTANTE:**
- Certificados de produção são diferentes dos de sandbox
- Mantenha certificados seguros (não commitar no git)
- Configure permissões adequadas (chmod 600)

#### 3. Criar Workspace de Produção

**Via Chat:**
```
"criar workspace santander agencia 0001 conta 130392838 tipo PAYMENTS"
```

**Configure no `.env`:**
```env
SANTANDER_WORKSPACE_ID=workspace_id_producao
```

#### 4. Testar em Produção (Cuidado!)

**⚠️ ATENÇÃO: Em produção, TEDs movimentam dinheiro real!**

**Recomendações:**
1. **Teste com valores mínimos primeiro**
   - Ex: R$ 0,01 ou R$ 1,00
   - Para conta de teste própria

2. **Valide todos os dados antes**
   - CPF/CNPJ válidos
   - Conta destino correta
   - Valor correto

3. **Use em horário comercial**
   - TEDs podem ter horário de processamento
   - Verifique horários da API

4. **Monitore logs cuidadosamente**
   - Verifique status de cada TED
   - Confirme com extrato bancário

#### 5. Checklist de Produção

**Antes de ativar em produção:**

- [ ] Credenciais de produção configuradas no `.env`
- [ ] Certificados mTLS de produção configurados e válidos
- [ ] Workspace de produção criado e configurado
- [ ] `SANTANDER_WORKSPACE_ID` configurado no `.env`
- [ ] Testado com valor mínimo (R$ 0,01)
- [ ] Validado extrato bancário após teste
- [ ] Logs configurados e monitorados
- [ ] Backup de certificados e credenciais
- [ ] Documentação atualizada
- [ ] Equipe treinada no uso

### 📚 Documentação Completa

Para mais detalhes, consulte:
- **`docs/IMPLEMENTACAO_TED_SANTANDER_FINAL.md`** - Documentação completa da implementação
  - Erros encontrados e soluções detalhadas
  - Lições aprendidas
  - Passos para produção
  - Troubleshooting completo
- **`docs/EXPLICACAO_WORKSPACE_E_AUTENTICACAO.md`** - Workspaces e autenticação
- **`docs/TESTES_SEGUROS_TED_SANTANDER.md`** - Testes no sandbox
- **`docs/UX_TED_SANTANDER.md`** - Experiência do usuário

### ✅ Checklist de Implementação

- [x] API de Pagamentos isolada
- [x] Suporte a certificados .pfx
- [x] Criação de workspaces
- [x] Iniciar TED
- [x] Efetivar TED
- [x] Consultar TED
- [x] Listar TEDs
- [x] Validações completas
- [x] Logs detalhados
- [x] Mensagens de erro claras
- [x] Testes no sandbox
- [ ] Configuração de produção
- [ ] Testes em produção

---

**Última atualização:** 12/01/2026




