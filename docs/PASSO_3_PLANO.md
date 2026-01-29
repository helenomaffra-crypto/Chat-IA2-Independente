# 📋 Passo 3: Extrair processar_mensagem() - Plano de Implementação

**Data:** 09/01/2026  
**Status:** ⏳ **EM DESENVOLVIMENTO**

---

## 🎯 Objetivo

Extrair a lógica comum entre `processar_mensagem()` e `processar_mensagem_stream()` para um serviço centralizado (`MessageProcessingService`), tratando streaming e não-streaming como duas "views" do mesmo core.

---

## 📊 Situação Atual

### **Problema:**
- `processar_mensagem()` tem ~5000 linhas
- `processar_mensagem_stream()` tem ~500 linhas
- **Duplicação:** Muita lógica repetida entre os dois métodos
- **Manutenção difícil:** Corrigir bug = corrigir em dois lugares

### **Exemplos de Duplicação:**
1. ✅ Detecção de comandos de interface (já unificado parcialmente)
2. ✅ Detecção de confirmação de email (já unificado via ConfirmationHandler)
3. ⚠️ Detecção de melhorar email (só em `processar_mensagem()`, não em `processar_mensagem_stream()`)
4. ⚠️ Lógica de precheck
5. ⚠️ Construção de prompt
6. ⚠️ Processamento de tool calls
7. ⚠️ Formatação de resposta

---

## 🏗️ Estrutura Proposta

### **MessageProcessingService**

```python
class MessageProcessingService:
    def processar_core(...) -> ProcessingResult:
        """
        Core que produz resultado estruturado.
        Não se preocupa com streaming vs não-streaming.
        """
        # 1. Detectar comandos de interface
        # 2. Detectar confirmações (email, DUIMP)
        # 3. Detectar melhorias de email
        # 4. Precheck (detecção proativa)
        # 5. Construir prompt
        # 6. Chamar IA
        # 7. Processar tool calls
        # 8. Formatar resposta
        return ProcessingResult(...)
```

### **ProcessingResult (DTO)**

```python
@dataclass
class ProcessingResult:
    resposta: str
    sucesso: bool = True
    tool_calls: Optional[List[Dict]] = None
    aguardando_confirmacao: bool = False
    ultima_resposta_aguardando_email: Optional[Dict] = None
    ultima_resposta_aguardando_duimp: Optional[Dict] = None
    comando_interface: Optional[Dict] = None
    acao: Optional[str] = None
    erro: Optional[str] = None
    _resultado_interno: Optional[Dict] = None
```

### **Uso no ChatService**

```python
# Modo não-streaming
def processar_mensagem(self, ...):
    resultado = self.message_processing_service.processar_core(...)
    return resultado.to_dict()  # Converte ProcessingResult para dict

# Modo streaming
def processar_mensagem_stream(self, ...):
    resultado = self.message_processing_service.processar_core(...)
    # Transforma resultado em chunks
    yield from self._transformar_em_stream(resultado)
```

---

## 🚀 Estratégia de Implementação (Incremental)

### **Fase 1: Estrutura Básica (HOJE)**
- ✅ Criar `MessageProcessingService` com estrutura básica
- ✅ Criar `ProcessingResult` DTO
- ✅ Documentar plano

### **Fase 2: Extrair Detecções (✅ CONCLUÍDA)**
- ✅ Extrair detecção de comandos de interface
- ✅ Extrair detecção de melhorar email
- ✅ Integrar com ConfirmationHandler (já existe, será usado na Fase 3)

### **Fase 3: Extrair Core (Depois)**
- Extrair lógica de precheck
- Extrair construção de prompt
- Extrair processamento de tool calls
- Extrair formatação de resposta

### **Fase 4: Integração (Final)**
- Integrar `processar_mensagem()` com `MessageProcessingService`
- Integrar `processar_mensagem_stream()` com `MessageProcessingService`
- Criar helper `_transformar_em_stream()` para streaming

---

## ⚠️ Riscos e Mitigações

### **Risco 1: Quebrar Funcionalidades**
**Mitigação:**
- ✅ Testes golden criados (Passo 0)
- ✅ Manter compatibilidade durante transição
- ✅ Testar cada fase isoladamente

### **Risco 2: Complexidade de Streaming**
**Mitigação:**
- ✅ Separar lógica de streaming da lógica de processamento
- ✅ Core produz resultado estruturado, streaming apenas formata

### **Risco 3: Dependências Circulares**
**Mitigação:**
- ✅ Passar apenas dependências necessárias (não `chat_service` inteiro)
- ✅ Usar funções auxiliares como callbacks

---

## 📝 Checklist de Implementação

### **Fase 1: Estrutura Básica**
- [x] Criar `MessageProcessingService` com estrutura básica
- [x] Criar `ProcessingResult` DTO
- [x] Documentar plano
- [ ] Adicionar imports necessários

### **Fase 2: Extrair Detecções**
- [x] Extrair detecção de comandos de interface (`_detectar_comando_interface`)
- [x] Extrair detecção de melhorar email (`_detectar_melhorar_email`)
- [x] Adicionar flag `eh_pedido_melhorar_email` ao `ProcessingResult`
- [x] Adicionar método `to_dict()` ao `ProcessingResult` para compatibilidade
- [x] Integrar com ConfirmationHandler (já existe, será usado na Fase 3)

### **Fase 3: Extrair Core (✅ PARCIALMENTE CONCLUÍDA)**
- [x] Extrair detecção de confirmações (via ConfirmationHandler)
- [x] Extrair detecção de correção de email destinatário
- [x] Integrar lógica de precheck (retorna flag se precisa continuar)
- [ ] Extrair construção de prompt (sub-fase 3.5 - complexo, requer muitas variáveis)
- [ ] Extrair processamento de tool calls (sub-fase 3.5 - complexo, requer muitas variáveis)
- [ ] Extrair formatação de resposta (sub-fase 3.5)

### **Fase 4: Integração**
- [ ] Integrar `processar_mensagem()` com core
- [ ] Integrar `processar_mensagem_stream()` com core
- [ ] Criar helper `_transformar_em_stream()`
- [ ] Testar ambos os modos
- [ ] Validar que testes golden passam

---

## 🎯 Benefícios Esperados

1. ✅ **Reduz duplicação:** Uma lógica, dois usos
2. ✅ **Facilita manutenção:** Corrige uma vez, funciona nos dois
3. ✅ **Reduz bugs:** Não precisa corrigir em dois lugares
4. ✅ **Facilita testes:** Core pode ser testado isoladamente
5. ✅ **Reduz tamanho:** `processar_mensagem()` de ~5000 para ~200 linhas

---

**Próximo passo:** Fase 2 - Extrair detecções
