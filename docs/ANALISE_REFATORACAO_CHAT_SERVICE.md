# 🔍 Análise de Refatoração: ChatService

**Data:** 09/01/2026  
**Status:** ⚠️ **URGENTE** - Arquivo muito grande (8961 linhas)

---

## 📊 Situação Atual

### Tamanho do Arquivo
- **Total de linhas:** 8961
- **Total de métodos:** 25
- **Classe principal:** `ChatService`

### Métodos Gigantes (Top 3)
1. **`processar_mensagem()`**: 4887 linhas (54% do arquivo!)
2. **`_executar_funcao_tool()`**: 2162 linhas (24% do arquivo!)
3. **`processar_mensagem_stream()`**: 457 linhas (5% do arquivo!)

**Total dos 3 métodos:** 7506 linhas (84% do arquivo!)

---

## 🎯 Problemas Identificados

### 1. **Violação do Princípio de Responsabilidade Única (SRP)**
O `ChatService` está fazendo **muitas coisas**:
- ✅ Processamento de mensagens
- ✅ Execução de tools (2162 linhas!)
- ✅ Extração de entidades (processo, CE, CCT, DI, DUIMP)
- ✅ Gerenciamento de contexto
- ✅ Gerenciamento de email drafts
- ✅ Gerenciamento de confirmações
- ✅ Formatação de respostas
- ✅ Streaming de mensagens
- ✅ Validação de perguntas (analítica, conhecimento geral)

### 2. **Métodos Gigantes**
- `processar_mensagem()` com 4887 linhas é **impossível de manter**
- `_executar_funcao_tool()` com 2162 linhas tem **muitas responsabilidades**

### 3. **Código Duplicado**
- Lógica de confirmação duplicada entre `processar_mensagem()` e `processar_mensagem_stream()`
- Lógica de email duplicada em vários lugares

### 4. **Dificuldade de Teste**
- Métodos gigantes são **impossíveis de testar unitariamente**
- Dependências acopladas dificultam mocks

### 5. **Dificuldade de Manutenção**
- Mudanças em uma funcionalidade podem quebrar outras
- Difícil encontrar onde está o código relevante
- Difícil adicionar novas funcionalidades sem aumentar ainda mais o arquivo

---

## ✅ O Que Já Foi Extraído (Bom Exemplo)

O projeto já tem uma **boa arquitetura de serviços separados**:

### Serviços Existentes:
- ✅ `email_service.py` - Envio de emails
- ✅ `email_draft_service.py` - Gerenciamento de drafts
- ✅ `email_precheck_service.py` - Detecção de intenções de email
- ✅ `precheck_service.py` - Detecção proativa de intenções
- ✅ `tool_router.py` - Roteamento de tools
- ✅ `tool_executor.py` - Execução de tools
- ✅ `prompt_builder.py` - Construção de prompts
- ✅ `context_service.py` - Gerenciamento de contexto
- ✅ `processo_status_service.py` - Status de processos
- ✅ `duimp_service.py` - Operações com DUIMP
- ✅ `ncm_service.py` - Operações com NCM
- ✅ `legislacao_service.py` - Operações com legislação
- ✅ E muitos outros...

**Padrão:** Cada serviço tem uma responsabilidade clara e bem definida.

---

## 🎯 Plano de Refatoração

### **Fase 1: Extrair Execução de Tools** (Prioridade: ALTA)

**Problema:** `_executar_funcao_tool()` tem 2162 linhas e faz muitas coisas.

**Solução:** Criar `services/tool_execution_service.py` (ou melhorar o existente)

**O que extrair:**
- ✅ Lógica de execução de cada tool individual
- ✅ Lógica de confirmação de DUIMP
- ✅ Lógica de preview de email
- ✅ Lógica de relatórios

**Estrutura proposta:**
```python
# services/tool_execution_service.py
class ToolExecutionService:
    def executar_tool(self, nome_funcao: str, argumentos: Dict, chat_service: ChatService) -> Dict:
        # Roteia para handler específico
        handlers = {
            'enviar_email_personalizado': self._executar_enviar_email_personalizado,
            'enviar_relatorio_email': self._executar_enviar_relatorio_email,
            'criar_duimp': self._executar_criar_duimp,
            # ... outros handlers
        }
        handler = handlers.get(nome_funcao)
        if handler:
            return handler(argumentos, chat_service)
        # Fallback para tool_router
        return self._executar_via_router(nome_funcao, argumentos, chat_service)
```

**Benefícios:**
- ✅ Reduz `_executar_funcao_tool()` de 2162 para ~100 linhas
- ✅ Cada tool handler pode ser testado isoladamente
- ✅ Fácil adicionar novos tools

---

### **Fase 2: Extrair Processamento de Mensagens** (Prioridade: ALTA)

**Problema:** `processar_mensagem()` tem 4887 linhas e faz tudo.

**Solução:** Criar `services/message_processing_service.py`

**O que extrair:**
- ✅ Lógica de detecção de confirmações
- ✅ Lógica de detecção de melhorias de email
- ✅ Lógica de construção de prompt
- ✅ Lógica de processamento de tool calls
- ✅ Lógica de formatação de resposta

**Estrutura proposta:**
```python
# services/message_processing_service.py
class MessageProcessingService:
    def __init__(self, chat_service: ChatService):
        self.chat_service = chat_service
        self.confirmation_handler = ConfirmationHandler(chat_service)
        self.email_improvement_handler = EmailImprovementHandler(chat_service)
        self.prompt_builder = PromptBuilder()
        self.tool_processor = ToolProcessor(chat_service)
    
    def processar(self, mensagem: str, historico: List, ...) -> Dict:
        # 1. Detectar confirmações
        if self.confirmation_handler.is_confirmation(mensagem):
            return self.confirmation_handler.handle()
        
        # 2. Detectar melhorias de email
        if self.email_improvement_handler.is_improvement_request(mensagem):
            return self.email_improvement_handler.handle()
        
        # 3. Construir prompt
        prompt = self.prompt_builder.build(...)
        
        # 4. Chamar IA
        resposta_ia = self.chat_service.ai_service.chat_completion(...)
        
        # 5. Processar tool calls
        if resposta_ia.tool_calls:
            return self.tool_processor.process(resposta_ia.tool_calls)
        
        # 6. Formatar resposta
        return self._formatar_resposta(resposta_ia)
```

**Benefícios:**
- ✅ Reduz `processar_mensagem()` de 4887 para ~200 linhas
- ✅ Cada handler pode ser testado isoladamente
- ✅ Fácil adicionar novos tipos de processamento

---

### **Fase 3: Extrair Handlers Específicos** (Prioridade: MÉDIA)

**Criar handlers especializados:**

#### 3.1. `services/handlers/confirmation_handler.py`
- ✅ Detecção de confirmações (DUIMP, email, etc.)
- ✅ Execução de ações pendentes

#### 3.2. `services/handlers/email_improvement_handler.py`
- ✅ Detecção de pedidos de melhoria
- ✅ Extração de email melhorado
- ✅ Atualização de draft

#### 3.3. `services/handlers/context_extraction_handler.py`
- ✅ Extração de processo, categoria, documento
- ✅ Extração de contexto do histórico

#### 3.4. `services/handlers/response_formatter.py`
- ✅ Formatação de respostas
- ✅ Combinação de resultados de tools
- ✅ Adição de indicadores de fonte

---

### **Fase 4: Extrair Utilitários** (Prioridade: BAIXA)

**Criar utilitários reutilizáveis:**

#### 4.1. `services/utils/entity_extractors.py`
- ✅ `_extrair_processo_referencia()`
- ✅ `_extrair_numero_ce()`
- ✅ `_extrair_numero_cct()`
- ✅ `_extrair_numero_duimp_ou_di()`
- ✅ `_buscar_processo_por_variacao()`

#### 4.2. `services/utils/question_classifier.py`
- ✅ `_eh_pergunta_analitica()`
- ✅ `_eh_pergunta_conhecimento_geral()`
- ✅ `_eh_pergunta_generica()`
- ✅ `_identificar_se_precisa_contexto()`

#### 4.3. `services/utils/email_utils.py`
- ✅ `_extrair_email_da_resposta_ia()`
- ✅ `_obter_email_para_enviar()`
- ✅ `_limpar_frases_problematicas()`

---

## 📋 Estrutura Proposta Após Refatoração

```
services/
├── chat_service.py                    # ~500 linhas (orquestrador principal)
├── message_processing_service.py      # ~300 linhas (processamento de mensagens)
├── tool_execution_service.py          # ~400 linhas (execução de tools)
├── handlers/
│   ├── confirmation_handler.py        # ~200 linhas
│   ├── email_improvement_handler.py   # ~150 linhas
│   ├── context_extraction_handler.py  # ~200 linhas
│   └── response_formatter.py         # ~150 linhas
├── utils/
│   ├── entity_extractors.py          # ~300 linhas
│   ├── question_classifier.py        # ~200 linhas
│   └── email_utils.py                # ~200 linhas
└── [outros serviços existentes...]
```

**Total estimado:** ~2600 linhas distribuídas em 11 arquivos (vs 8961 em 1 arquivo)

---

## 🚀 Estratégia de Implementação (ATUALIZADA - 09/01/2026)

### **Abordagem Incremental (Recomendada)**

1. **Não refatorar tudo de uma vez**
2. **Extrair uma funcionalidade por vez**
3. **Manter compatibilidade durante a transição**
4. **Testar cada extração antes de continuar**

### **Ordem de Prioridade (NOVA - Baseada em Análise ChatGPT):**

**🎯 Objetivo:** Mais retorno em menos risco - corrigir bugs críticos primeiro, depois refatorar

#### **Passo 0 — Testes de Segurança (1 dia)**
**Status:** 🔴 **URGENTE** - Fazer ANTES de qualquer refatoração

**O que fazer:**
- Criar 5-10 testes de "caminho feliz" (golden tests)
- Exemplos de fluxos críticos:
  - ✅ Gerar relatório → preview → confirmar → enviado
  - ✅ Criar e-mail → melhorar → confirmar → enviar melhorado
  - ✅ Criar e-mail → corrigir destinatário → confirmar → enviar
  - ✅ Criar DUIMP → confirmar → DUIMP criada

**Por que:**
- Esses testes viram o "airbag" durante a refatoração
- Garantem que funcionalidades críticas não quebram
- Permitem refatorar com confiança

**Arquivos:**
- `tests/test_email_flows.py` - Testes de fluxos de email
- `tests/test_duimp_flows.py` - Testes de fluxos de DUIMP

---

#### **Passo 0.5 — Correção Imediata do Bug de Email (URGENTE)**
**Status:** ✅ **VERIFICADO** - Código já implementado corretamente (09/01/2026)

**Problema atual:**
- Sistema envia email antigo após "melhore o email" e confirmação
- Memória e banco podem estar dessincronizados

**Solução (ajuste mínimo com maior impacto):**

1. **Na confirmação, se existir `draft_id`, buscar SEMPRE a última revisão no banco e ignorar conteúdo em memória:**
   - ✅ **VERIFICADO:** `_obter_email_para_enviar()` prioriza banco quando tem `draft_id` (linha ~3220)
   - ✅ **VERIFICADO:** `processar_mensagem()` usa `_obter_email_para_enviar()` na confirmação (linha ~3524)
   - ✅ **VERIFICADO:** `processar_mensagem_stream()` usa `_obter_email_para_enviar()` na confirmação (linha ~8624)
   - ✅ **STATUS:** Implementado corretamente em ambos os métodos

2. **Em "melhorar e-mail", sempre: atualizar draft + atualizar `ultima_resposta_aguardando_email` + reemitir Preview:**
   - ✅ **VERIFICADO:** Código em `processar_mensagem()` linha ~8187 atualiza banco + memória
   - ✅ **VERIFICADO:** Preview é reemitido após melhorar email (linha ~8239)
   - ✅ **VERIFICADO:** `revision` é atualizado na memória (linha ~8200)
   - ⚠️ **PENDENTE:** Verificar se `processar_mensagem_stream()` também tem lógica de melhorar email (parece que não tem - pode ser problema futuro)

3. **Eliminar regex frágil para extração de email melhorado:**
   - ⚠️ **FUTURO:** Pedir para IA retornar JSON estruturado: `{"assunto": "...", "conteudo": "..."}`
   - ✅ Por enquanto: regex atual está robusto (linha ~8288, método `_extrair_email_da_resposta_ia`)

**Arquivos verificados:**
- ✅ `services/chat_service.py` - Linha ~3220 (`_obter_email_para_enviar`) - ✅ OK
- ✅ `services/chat_service.py` - Linha ~3524 (confirmação em `processar_mensagem`) - ✅ OK
- ✅ `services/chat_service.py` - Linha ~8624 (confirmação em `processar_mensagem_stream`) - ✅ OK
- ✅ `services/chat_service.py` - Linha ~8187 (melhorar email em `processar_mensagem`) - ✅ OK
- ⚠️ `services/chat_service.py` - `processar_mensagem_stream()` - **NÃO TEM** lógica de melhorar email (duplicação incompleta)

**Regra de ouro:**
> "Texto do chat" não pode ser a fonte da verdade para envio. A fonte da verdade tem que ser um objeto (`draft_id + revision`), e a confirmação deve sempre enviar a última revisão desse objeto.

**Conclusão:**
- ✅ Código está correto para confirmação (usa banco como fonte da verdade)
- ✅ Código está correto para melhorar email em `processar_mensagem()`
- ⚠️ **PROBLEMA FUTURO:** `processar_mensagem_stream()` não tem lógica de melhorar email (será resolvido no Passo 3 - unificar streaming e não-streaming)

---

#### **Passo 1 — ConfirmationHandler + EmailSendCoordinator (Impacto Imediato)**
**Status:** ✅ **CONCLUÍDO** - Handler criado, coordenador implementado, integração completa (09/01/2026)

**Por que primeiro:**
- Centraliza lógica de confirmação (hoje está duplicada)
- Resolve inconsistências entre streaming e não-streaming
- Facilita corrigir bugs de confirmação
- **✅ NOVO:** Cria ponto único de convergência para envio de emails

**O que foi feito:**
- ✅ Criado `services/handlers/confirmation_handler.py`
- ✅ Criado `services/email_send_coordinator.py` (ponto único de convergência)
- ✅ Centralizada TODA lógica de confirmação:
  - ✅ Detecção de confirmações (email, DUIMP, etc.)
  - ✅ Execução de ações pendentes
  - ✅ Unificar lógica entre `processar_mensagem()` e `processar_mensagem_stream()`
- ✅ Implementada idempotência (não envia duas vezes)
- ✅ Integração completa com `EmailSendCoordinator`

**Regra:**
- Confirmação sempre resolve para um objeto (ex.: draft no DB), não para "texto do chat"
- **✅ NOVO:** Todo envio com `draft_id` converge para `EmailSendCoordinator.send_from_draft()`

**Estrutura proposta:**
```python
# services/handlers/confirmation_handler.py
class ConfirmationHandler:
    def __init__(self, email_draft_service, duimp_service, ...):
        # Passar apenas serviços necessários, não chat_service inteiro
        self.email_draft_service = email_draft_service
        self.duimp_service = duimp_service
    
    def detectar_confirmacao(self, mensagem: str, estado_pendente: Dict) -> bool:
        # Detectar se mensagem é confirmação
    
    def processar_confirmacao(self, mensagem: str, estado_pendente: Dict) -> Dict:
        # Processar confirmação e retornar resultado
        # Se tem draft_id → buscar do banco (fonte da verdade)
        # Se não tem → usar memória
```

**Benefícios:**
- ✅ Elimina duplicação entre streaming e não-streaming
- ✅ Fácil testar isoladamente
- ✅ Fácil corrigir bugs de confirmação

---

#### **Passo 1.5 — EmailSendCoordinator (Ponto Único de Convergência)**
**Status:** ✅ **CONCLUÍDO** - Implementado e integrado (09/01/2026)

**Problema identificado:**
- Múltiplos caminhos de envio podem bypassar o sistema de drafts
- Risco de enviar versão antiga ou duplicar envio
- Falta de idempotência

**Solução:**
- ✅ Criado `services/email_send_coordinator.py`
- ✅ Método `send_from_draft(draft_id)` como ponto único de convergência
- ✅ Idempotência implementada (verifica `status == 'sent'`)
- ✅ Sempre carrega última revisão do banco (fonte da verdade)
- ✅ Integrado com `ConfirmationHandler`

**Regras implementadas:**
1. Todo envio com `draft_id` DEVE usar `send_from_draft()`
2. NUNCA enviar email sem verificar idempotência
3. SEMPRE carregar draft do banco antes de enviar
4. SEMPRE marcar como enviado após sucesso

**Documentação:** Ver `docs/EMAIL_SEND_COORDINATOR.md`

---

#### **Passo 2 — ToolExecutionService (Sua Fase 1 Original)**
**Status:** 🔄 **EM PROGRESSO** - Estrutura criada, handler de enviar_email_personalizado implementado (09/01/2026)

**O que fazer:**
- Extrair `_executar_funcao_tool()` para `services/tool_execution_service.py`
- **CRÍTICO:** Passar contexto enxuto, NÃO `chat_service` inteiro

**Estrutura proposta:**
```python
# services/tool_execution_service.py
@dataclass
class ToolContext:
    """Contexto enxuto para execução de tools"""
    email_service: Any
    draft_service: Any
    processo_service: Any
    context_service: Any
    logger: Any
    # ... apenas o que precisa

class ToolExecutionService:
    def executar_tool(self, nome_funcao: str, argumentos: Dict, contexto: ToolContext) -> Dict:
        # Roteia para handler específico
        handlers = {
            'enviar_email_personalizado': self._executar_enviar_email_personalizado,
            'enviar_relatorio_email': self._executar_enviar_relatorio_email,
            'criar_duimp': self._executar_criar_duimp,
            # ... outros handlers
        }
        handler = handlers.get(nome_funcao)
        if handler:
            return handler(argumentos, contexto)
        # Fallback para tool_router
        return self._executar_via_router(nome_funcao, argumentos, contexto)
```

**Por que contexto enxuto:**
- ✅ Evita acoplamento: não precisa instanciar `ChatService` inteiro para testar
- ✅ Mais testável: passa só o que precisa
- ✅ Reduz dependências circulares

**Benefícios:**
- ✅ Reduz `_executar_funcao_tool()` de 2162 para ~100 linhas
- ✅ Cada tool handler pode ser testado isoladamente
- ✅ Fácil adicionar novos tools

---

#### **Passo 3 — Extrair processar_mensagem() (Sua Fase 2 Original)**
**Status:** ⏳ **PENDENTE** - Fazer DEPOIS do Passo 2

**O que fazer:**
- Extrair `processar_mensagem()` para `services/message_processing_service.py`
- **CRÍTICO:** Tratar streaming e não-streaming como "duas views do mesmo core"

**Estrutura proposta:**
```python
# services/message_processing_service.py
class MessageProcessingService:
    def __init__(self, confirmation_handler, tool_execution_service, ...):
        self.confirmation_handler = confirmation_handler
        self.tool_execution_service = tool_execution_service
    
    def processar_core(self, mensagem: str, historico: List, ...) -> Dict:
        """
        Core que produz resultado estruturado (eventos/ações/mensagens).
        Não se preocupa com streaming vs não-streaming.
        """
        # 1. Detectar confirmações
        if self.confirmation_handler.detectar_confirmacao(...):
            return self.confirmation_handler.processar_confirmacao(...)
        
        # 2. Detectar melhorias de email
        # 3. Construir prompt
        # 4. Chamar IA
        # 5. Processar tool calls
        # 6. Formatar resposta
        return resultado_estruturado

# No chat_service.py:
def processar_mensagem(self, ...):
    resultado = self.message_processing_service.processar_core(...)
    return resultado  # Retorna resultado final

def processar_mensagem_stream(self, ...):
    resultado = self.message_processing_service.processar_core(...)
    # Transforma resultado em stream
    yield from self._transformar_em_stream(resultado)
```

**Por que duas views do mesmo core:**
- ✅ Elimina duplicação: hoje há duas lógicas para o mesmo fluxo
- ✅ Mais fácil manter: corrige uma vez, funciona nos dois
- ✅ Reduz bugs: não precisa corrigir em dois lugares

**Benefícios:**
- ✅ Reduz `processar_mensagem()` de 4887 para ~200 linhas
- ✅ Elimina duplicação com `processar_mensagem_stream()`
- ✅ Fácil adicionar novos tipos de processamento

---

#### **Passo 4 — Handlers e Utils (Sua Fase 3/4 Original)**
**Status:** ⏳ **PENDENTE** - Fazer DEPOIS do Passo 3

**O que fazer:**
- Extrair handlers específicos (email_improvement, context_extraction, response_formatter)
- Extrair utilitários (entity_extractors, question_classifier, email_utils)

**Benefícios:**
- ✅ Ganha legibilidade e manutenção
- ✅ Risco já cai bastante depois dos passos 1-3

### **Padrão de Extração:**

```python
# ANTES (no chat_service.py)
def _executar_funcao_tool(self, nome_funcao, argumentos, ...):
    if nome_funcao == "enviar_email_personalizado":
        # 200 linhas de código...
    elif nome_funcao == "criar_duimp":
        # 300 linhas de código...
    # ...

# DEPOIS (no tool_execution_service.py)
class ToolExecutionService:
    def executar(self, nome_funcao, argumentos, chat_service, ...):
        handler = self._get_handler(nome_funcao)
        return handler(argumentos, chat_service, ...)
    
    def _executar_enviar_email_personalizado(self, argumentos, chat_service, ...):
        # 200 linhas de código (movidas do chat_service)

# DEPOIS (no chat_service.py - simplificado)
def _executar_funcao_tool(self, nome_funcao, argumentos, ...):
    return self.tool_execution_service.executar(
        nome_funcao, argumentos, self, ...
    )
```

---

## ⚠️ Riscos e Mitigações (ATUALIZADO - 09/01/2026)

### **Risco 1: Quebrar Funcionalidades Existentes**
**Mitigação:**
- ✅ **Passo 0:** Criar testes de segurança (golden tests) ANTES de refatorar
- ✅ Manter testes existentes
- ✅ Testar cada extração isoladamente
- ✅ Manter compatibilidade durante transição

### **Risco 2: Aumentar Complexidade**
**Mitigação:**
- ✅ Documentar cada serviço
- ✅ Manter interfaces claras
- ✅ Usar dependency injection
- ✅ **Passo 2:** Passar contexto enxuto, não `chat_service` inteiro (reduz acoplamento)

### **Risco 3: Tempo de Implementação**
**Mitigação:**
- ✅ Fazer incrementalmente
- ✅ Priorizar métodos maiores primeiro
- ✅ Não parar desenvolvimento de features
- ✅ **Passo 0.5:** Corrigir bugs críticos primeiro (entrega valor imediato)

### **Risco 4: "Explodir" em Muitos Arquivos sem Interface Clara**
**Mitigação:**
- ✅ Usar contratos simples (entradas/saídas)
- ✅ Usar dataclasses/pydantic para payloads
- ✅ Documentar cada handler/serviço

### **Risco 5: Continuar com Parse/Regex Frágil para "Melhorar E-mail"**
**Mitigação:**
- ⚠️ **FUTURO:** Pedir para IA retornar JSON estruturado: `{"assunto": "...", "conteudo": "..."}`
- ✅ Por enquanto: melhorar regex atual (já está robusto)
- ✅ Usar draft_id como fonte da verdade (elimina necessidade de parse perfeito)

### **Risco 6: Dois Estados Competindo (Memória vs Banco)**
**Mitigação:**
- ✅ **Passo 0.5:** Quando existe `draft_id`, banco manda (fonte da verdade)
- ✅ Sempre atualizar banco + memória ao melhorar email
- ✅ Sempre buscar do banco na confirmação se tem `draft_id`

---

## 📊 Métricas de Sucesso

### **Antes da Refatoração:**
- ❌ 1 arquivo com 8961 linhas
- ❌ 3 métodos com 7506 linhas (84% do arquivo)
- ❌ Difícil de testar
- ❌ Difícil de manter

### **Depois da Refatoração (Meta):**
- ✅ 11 arquivos com ~2600 linhas totais
- ✅ Nenhum método com mais de 500 linhas
- ✅ Fácil de testar (cada serviço isolado)
- ✅ Fácil de manter (responsabilidades claras)

---

## 🎯 Recomendação Final

**✅ FAZER A REFATORAÇÃO**, mas de forma **incremental**:

1. **Começar pela Fase 1** (extrair `_executar_funcao_tool`)
2. **Testar bem antes de continuar**
3. **Depois fazer Fase 2** (extrair `processar_mensagem`)
4. **Continuar com as outras fases conforme necessário**

**⚠️ NÃO fazer tudo de uma vez** - risco muito alto de quebrar o sistema.

---

## 📝 Próximos Passos (ATUALIZADO - 09/01/2026)

### **Status Atual:**
- ✅ **Passo 0:** ⏳ Em progresso - Criar testes de segurança
- ✅ **Passo 0.5:** ✅ **CONCLUÍDO** - Bug de email verificado (código já estava correto)
- ✅ **Passo 1:** ✅ **CONCLUÍDO** - ConfirmationHandler + EmailSendCoordinator criados e integrados
  - ✅ Handler centraliza lógica de confirmação
  - ✅ Coordenador cria ponto único de convergência para envio
  - ✅ Idempotência implementada
  - ✅ Integração completa em `processar_mensagem()` e `processar_mensagem_stream()`
- ✅ **Passo 2:** ✅ **CONCLUÍDO** - ToolExecutionService criado e integrado
  - ✅ Estrutura base com ToolContext (contexto enxuto)
  - ✅ Handlers implementados:
    - ✅ `enviar_email_personalizado` (completo, usa EmailSendCoordinator)
    - ✅ `enviar_email` (completo)
    - ✅ `enviar_relatorio_email` (parcial - confirmação com resumo_texto salvo)
  - ✅ Integração no ChatService (tenta usar antes do fallback)
  - ✅ Compatibilidade mantida (fallback antigo continua funcionando)
- ⏳ **Passo 2:** Pendente - Extrair ToolExecutionService
- ⏳ **Passo 3:** Pendente - Extrair processar_mensagem()
- ⏳ **Passo 4:** Pendente - Extrair handlers e utils

### **Ações Imediatas:**

1. ✅ **Passo 0.5 (URGENTE):** Verificar se `_obter_email_para_enviar()` está sendo usado em TODOS os lugares de confirmação
   - ✅ `processar_mensagem()` - linha ~3524 (já usa)
   - ⚠️ `processar_mensagem_stream()` - **VERIFICAR** se também usa
   - ⚠️ Verificar se preview é reemitido após melhorar email

2. ✅ **Passo 0:** Criar testes de segurança (golden tests)
   - Criar `tests/test_email_flows.py`
   - Criar `tests/test_duimp_flows.py`

3. ⏳ **Passo 1:** Criar `services/handlers/confirmation_handler.py`
   - Centralizar lógica de confirmação
   - Unificar streaming e não-streaming

4. ⏳ **Passo 2:** Criar `services/tool_execution_service.py`
   - Extrair `_executar_funcao_tool()`
   - Usar contexto enxuto (não `chat_service` inteiro)

5. ⏳ **Passo 3:** Criar `services/message_processing_service.py`
   - Extrair `processar_mensagem()`
   - Tratar streaming e não-streaming como duas views do mesmo core

6. ⏳ **Passo 4:** Extrair handlers e utils específicos

---

## 📚 Referências

- **Análise ChatGPT:** Sugestões de ordem prática e mitigação de riscos (09/01/2026)
- **Documentação relacionada:**
  - `docs/EMAIL_DRAFTS_ANALISE.md` - Análise do sistema de drafts
  - `docs/MELHORIAS_FLUIDEZ_EMAIL.md` - Melhorias de fluidez
  - `docs/PAYLOAD_EMAIL_AZURE.md` - Estrutura de payload de email

---

**Última atualização:** 09/01/2026
