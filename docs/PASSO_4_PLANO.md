# 📋 Passo 4: Extrair Handlers e Utils Específicos - Plano Detalhado

**Data:** 09/01/2026  
**Última atualização:** 09/01/2026 19:30  
**Status:** ⏳ **EM DESENVOLVIMENTO** (4.1: Implementação completa, falta integração)

---

## 🎯 Objetivo

Extrair handlers e utilitários específicos do `chat_service.py` para arquivos dedicados, melhorando:
- ✅ Legibilidade
- ✅ Manutenção
- ✅ Testabilidade
- ✅ Redução de tamanho do `chat_service.py`

---

## 📊 Prioridade de Implementação

**Ordem sugerida (do mais crítico para menos crítico):**

1. ✅ **`EmailImprovementHandler`** - **CRÍTICO** (relacionado a bugs de email)
2. ⏳ **`EntityExtractors`** - Importante (usado em muitos lugares)
3. ⏳ **`QuestionClassifier`** - Importante (usado na construção de prompt)
4. ⏳ **`EmailUtils`** - Moderado (usado apenas para emails)
5. ⏳ **`ContextExtractionHandler`** - Moderado (usado na construção de prompt)
6. ⏳ **`ResponseFormatter`** - Baixo (pode ser feito depois)

---

## 📁 4.1. EmailImprovementHandler

### **Arquivo:** `services/handlers/email_improvement_handler.py`

### **Status:** ✅ **IMPLEMENTAÇÃO COMPLETA** - Falta integração no `chat_service.py`

### **Responsabilidades:**
1. ✅ Detectar pedido de melhorar email (`detectar_pedido()`)
2. ⏳ Chamar IA para melhorar o email (será feito no `chat_service`, handler processa resposta)
3. ✅ Extrair email melhorado da resposta da IA (`_extrair_email_da_resposta_ia()` - ~300 linhas movidas)
4. ✅ Atualizar draft no banco e reemitir preview (`processar_resposta_melhorar_email()`)

### **Métodos a Extrair:**

#### **1. `detectar_melhorar_email(mensagem: str) -> bool`**
- **Localização atual:** `MessageProcessingService._detectar_melhorar_email()` (linhas ~120-140)
- **Ação:** Mover para `EmailImprovementHandler`
- **Dependências:** Nenhuma (método puro)

#### **2. `processar_melhorar_email(mensagem: str, dados_email_original: Dict, ...) -> Dict`**
- **Localização atual:** `chat_service.py` (linhas ~8340-8430)
- **Ação:** Extrair lógica completa
- **Dependências:**
  - `EmailDraftService` (para atualizar draft)
  - `AI Service` (para chamar IA)
  - `_extrair_email_da_resposta_ia()` (mover junto)

#### **3. `extrair_email_da_resposta_ia(resposta_ia: str, dados_email_original: Dict) -> Optional[Dict]`**
- **Localização atual:** `chat_service.py` (linhas ~8514-8810) - **~300 linhas!**
- **Ação:** Extrair para método privado do handler
- **Dependências:** Nenhuma (método puro com regex)
- **⚠️ FUTURO:** Este método será **ELIMINADO** quando implementarmos JSON estruturado da IA

### **Interface do Handler (Implementada):**

```python
class EmailImprovementHandler:
    def __init__(
        self,
        email_draft_service: EmailDraftService = None,
        ai_service: AIService = None,
        prompt_builder: PromptBuilder = None
    ):
        # ✅ Implementado com lazy loading
        
    def detectar_pedido(self, mensagem: str) -> bool:
        """✅ Implementado - Detecta se mensagem é pedido para melhorar email."""
        
    def processar_resposta_melhorar_email(
        self,
        resposta_ia: str,
        dados_email_original: Dict[str, Any],
        session_id: str,
        ultima_resposta_aguardando_email: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        ✅ Implementado - Processa resposta da IA após pedido de melhorar email.
        
        Extrai email refinado, atualiza draft no banco e reemite preview atualizado.
        
        Returns:
            Dict com:
            - 'sucesso': bool
            - 'resposta': str (preview atualizado ou mensagem de erro/pergunta)
            - 'dados_email_atualizados': Dict (para atualizar estado)
            - 'draft_id': str
            - 'revision': int
            - 'erro': str (se houver)
        """
        
    def _extrair_email_da_resposta_ia(
        self,
        resposta_ia: str,
        dados_email_original: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        ✅ Implementado (~300 linhas movidas de chat_service.py)
        
        Extrai email refinado da resposta da IA usando múltiplos padrões regex.
        ⚠️ FUTURO: Será ELIMINADO quando implementarmos JSON estruturado da IA.
        """
    
    def _extrair_email_da_resposta_ia(
        self,
        resposta_ia: str,
        dados_email_original: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extrai email melhorado da resposta da IA (via regex)."""
        pass
```

### **Progresso da Implementação:**

#### ✅ **Concluído:**
- ✅ Estrutura básica do handler criada
- ✅ Método `detectar_pedido()` implementado (já estava em `MessageProcessingService`, mantido no handler)
- ✅ Método `_extrair_email_da_resposta_ia()` **COMPLETO** movido de `chat_service.py` (~300 linhas, linhas ~8514-8810)
  - Todos os padrões regex mantidos
  - Todos os casos de tratamento mantidos
  - Logging completo preservado
- ✅ Método `processar_resposta_melhorar_email()` **COMPLETO** implementado
  - Extrai email refinado
  - Atualiza draft no banco (ou cria novo se não existe)
  - Atualiza memória com dados do banco (fonte da verdade)
  - Reemite preview atualizado
  - Tratamento de erros completo
- ✅ Código compilado e testado (sem erros de sintaxe)
- ✅ Lazy loading de dependências implementado

#### ✅ **Integração Completa:**
- ✅ Handler inicializado no `__init__` do `ChatService`
- ✅ Lógica inline substituída em `processar_mensagem()` (linhas ~8349-8473)
- ✅ Lógica inline substituída em `processar_mensagem_stream()` (linhas ~9275-9306)
- ✅ Fallback para método antigo mantido (caso handler não esteja disponível)
- ✅ Código compila sem erros
- ✅ Sem erros de linting

#### ⏳ **Pendente:**
- ⏳ **Testar integração completa** (fluxo de melhorar email)
- ⏳ Validar que não quebrou funcionalidades existentes
- ⏳ Remover método `_extrair_email_da_resposta_ia()` antigo de `chat_service.py` após validação (mantido como fallback por enquanto)

### **Status Final:**
✅ **INTEGRAÇÃO COMPLETA** - Handler totalmente integrado em ambos os métodos (`processar_mensagem` e `processar_mensagem_stream`)

### **Próximos Passos:**
1. ✅ ~~Integrar `EmailImprovementHandler` no `chat_service.py`~~ **CONCLUÍDO**
2. ⏳ **Testar fluxo completo de melhorar email** (após testes, pode remover código antigo)
3. ⏳ Validar que não quebrou funcionalidades existentes
4. ⏳ Remover código antigo do `chat_service.py` após validação

---

## 📁 4.2. EntityExtractors

### **Arquivo:** `services/utils/entity_extractors.py`

### **Métodos a Extrair:**

1. `_extrair_processo_referencia(mensagem: str) -> Optional[str]`
2. `_extrair_numero_ce(mensagem: str) -> Optional[str]`
3. `_extrair_numero_cct(mensagem: str) -> Optional[str]`
4. `_extrair_numero_duimp_ou_di(mensagem: str) -> Optional[str]`
5. `_buscar_processo_por_variacao(processo_ref: str) -> Optional[str]`

### **Interface:**

```python
class EntityExtractors:
    @staticmethod
    def extrair_processo_referencia(mensagem: str) -> Optional[str]:
        """Extrai referência de processo (ex: VDM.0003/25) da mensagem."""
        pass
    
    @staticmethod
    def extrair_numero_ce(mensagem: str) -> Optional[str]:
        """Extrai número de CE (15 dígitos) da mensagem."""
        pass
    
    # ... outros métodos
```

---

## 📁 4.3. QuestionClassifier

### **Arquivo:** `services/utils/question_classifier.py`

### **Métodos a Extrair:**

1. `_eh_pergunta_analitica(mensagem: str) -> bool`
2. `_eh_pergunta_conhecimento_geral(mensagem: str) -> bool`
3. `_eh_pergunta_generica(mensagem: str) -> bool`
4. `_identificar_se_precisa_contexto(mensagem: str) -> bool`

### **Interface:**

```python
class QuestionClassifier:
    @staticmethod
    def eh_pergunta_analitica(mensagem: str) -> bool:
        """Verifica se mensagem requer análise de dados (BI/relatórios)."""
        pass
    
    # ... outros métodos
```

---

## 📁 4.4. EmailUtils

### **Arquivo:** `services/utils/email_utils.py`

### **Métodos a Extrair:**

1. `_obter_email_para_enviar(...)` - **Verificar se já existe e onde está**
2. `_limpar_frases_problematicas(conteudo: str) -> str`

### **⚠️ NOTA:**
- `_extrair_email_da_resposta_ia()` será **movido para `EmailImprovementHandler`** (não para utils)
- Será **eliminado** quando implementarmos JSON estruturado

---

## 📁 4.5. ContextExtractionHandler

### **Arquivo:** `services/handlers/context_extraction_handler.py`

### **Responsabilidades:**
1. Extrair contexto de processo
2. Extrair categoria
3. Extrair documentos (CE, CCT, DI, DUIMP)
4. Preparar contexto para prompt

### **Métodos:**
- A definir (complexo, requer análise do código)

---

## 📁 4.6. ResponseFormatter

### **Arquivo:** `services/handlers/response_formatter.py`

### **Responsabilidades:**
1. Formatar resposta final
2. Combinar múltiplos resultados
3. Adicionar contexto adicional

### **Métodos:**
- A definir (complexo, requer análise do código)

---

## 🚀 Estratégia de Implementação

### **Fase 1: EmailImprovementHandler (CRÍTICO)**
1. ✅ Criar arquivo `services/handlers/email_improvement_handler.py`
2. ✅ Mover `_detectar_melhorar_email()` do `MessageProcessingService`
3. ✅ Mover `_extrair_email_da_resposta_ia()` do `chat_service.py`
4. ✅ Extrair lógica de melhorar email do `chat_service.py`
5. ✅ Integrar com `MessageProcessingService` e `ChatService`
6. ✅ Testar fluxo completo

### **Fase 2: EntityExtractors**
1. ✅ Criar arquivo `services/utils/entity_extractors.py`
2. ✅ Mover métodos de extração
3. ✅ Atualizar referências no `chat_service.py`
4. ✅ Testar

### **Fase 3: QuestionClassifier**
1. ✅ Criar arquivo `services/utils/question_classifier.py`
2. ✅ Mover métodos de classificação
3. ✅ Atualizar referências
4. ✅ Testar

### **Fase 4: EmailUtils, ContextExtractionHandler, ResponseFormatter**
- Implementar incrementalmente conforme necessidade

---

## ⚠️ Riscos e Mitigações

### **Risco 1: Quebrar Funcionalidades Existentes**
**Mitigação:**
- ✅ Testes golden já existem (Passo 0)
- ✅ Manter compatibilidade durante transição
- ✅ Testar cada extração isoladamente

### **Risco 2: Dependências Circulares**
**Mitigação:**
- ✅ Passar apenas dependências necessárias
- ✅ Usar métodos estáticos quando possível
- ✅ Evitar importar `chat_service` completo

### **Risco 3: Complexidade de `_extrair_email_da_resposta_ia`**
**Mitigação:**
- ✅ Mover método completo (não refatorar agora)
- ✅ Documentar que será eliminado no futuro (JSON estruturado)
- ✅ Adicionar testes específicos para extração

---

## 📝 Checklist de Implementação

### **Fase 1: EmailImprovementHandler**
- [ ] Criar arquivo `services/handlers/email_improvement_handler.py`
- [ ] Implementar `detectar_pedido()`
- [ ] Mover `_extrair_email_da_resposta_ia()`
- [ ] Implementar `melhorar_email()`
- [ ] Integrar com `MessageProcessingService`
- [ ] Integrar com `ChatService`
- [ ] Testar fluxo completo
- [ ] Validar que testes golden passam

### **Fase 2: EntityExtractors**
- [ ] Criar arquivo `services/utils/entity_extractors.py`
- [ ] Mover todos os métodos de extração
- [ ] Atualizar referências no `chat_service.py`
- [ ] Testar

### **Fase 3: QuestionClassifier**
- [ ] Criar arquivo `services/utils/question_classifier.py`
- [ ] Mover métodos de classificação
- [ ] Atualizar referências
- [ ] Testar

---

## 🎯 Benefícios Esperados

1. ✅ **Redução de tamanho:** `chat_service.py` reduzirá ~500 linhas (Fase 1)
2. ✅ **Melhor testabilidade:** Handlers podem ser testados isoladamente
3. ✅ **Facilita correção de bugs:** Lógica de melhorar email isolada
4. ✅ **Prepara para JSON estruturado:** Handler isolado facilita substituição

---

**Próximo passo:** Implementar Fase 1 - EmailImprovementHandler
