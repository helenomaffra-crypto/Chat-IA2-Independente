# 🧪 Testes Golden Tests - Passo 0

**Data:** 09/01/2026  
**Status:** ⏳ **PENDENTE** - Criar antes de continuar refatoração

---

## 🎯 Objetivo

Criar testes de "caminho feliz" (golden tests) que servem como **airbag** durante a refatoração. Esses testes garantem que funcionalidades críticas não quebram quando extraímos código.

---

## 📋 Testes Sugeridos

### **Categoria 1: Fluxos de Email (CRÍTICO)**

#### **Teste 1.1: Criar Email → Preview → Confirmar → Enviado**
**Descrição:** Fluxo completo de criação e envio de email personalizado.

**Cenário:**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião de hoje"
2. Sistema: Gera preview do email
3. Usuário: "sim"
4. Sistema: Envia email com sucesso

**Validações:**
- ✅ Preview é gerado corretamente
- ✅ Draft é criado no banco (`draft_id` existe)
- ✅ Confirmação detectada corretamente
- ✅ Email enviado usando `EmailSendCoordinator.send_from_draft()`
- ✅ Draft marcado como `sent` após envio
- ✅ Resposta indica sucesso

**Arquivo:** `tests/test_email_flows.py::test_criar_email_preview_confirmar_enviado`

---

#### **Teste 1.2: Criar Email → Melhorar → Confirmar → Enviar Melhorado**
**Descrição:** Fluxo de melhoria de email antes do envio.

**Cenário:**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
2. Sistema: Gera preview do email
3. Usuário: "melhore o email"
4. Sistema: Gera email melhorado e reemite preview
5. Usuário: "sim"
6. Sistema: Envia email melhorado (não o original)

**Validações:**
- ✅ Preview inicial gerado
- ✅ Draft criado (revision 1)
- ✅ Melhoria detectada corretamente
- ✅ Novo draft criado (revision 2) com conteúdo melhorado
- ✅ Preview reemitido com conteúdo melhorado
- ✅ Confirmação envia revision 2 (não revision 1)
- ✅ Email enviado contém conteúdo melhorado

**Arquivo:** `tests/test_email_flows.py::test_criar_email_melhorar_confirmar_enviar_melhorado`

---

#### **Teste 1.3: Criar Email → Corrigir Destinatário → Confirmar → Enviar**
**Descrição:** Correção de destinatário sem perder contexto.

**Cenário:**
1. Usuário: "mande um email para helenomaffra@gmail sobre a reunião"
2. Sistema: Gera preview do email
3. Usuário: "mande para helenomaffra@gmail.com" (corrige email)
4. Sistema: Reemite preview com email corrigido
5. Usuário: "sim"
6. Sistema: Envia email para email correto

**Validações:**
- ✅ Preview inicial gerado
- ✅ Correção de destinatário detectada
- ✅ Preview reemitido com email corrigido
- ✅ Assunto e conteúdo mantidos (não perde contexto)
- ✅ Email enviado para destinatário correto
- ✅ Não gera email sobre outro assunto (ex: Santander/BND)

**Arquivo:** `tests/test_email_flows.py::test_criar_email_corrigir_destinatario_confirmar_enviar`

---

#### **Teste 1.4: Enviar Relatório → Preview → Confirmar → Enviado**
**Descrição:** Fluxo de envio de relatório por email.

**Cenário:**
1. Usuário: "como estão os DMD?"
2. Sistema: Gera relatório
3. Usuário: "mande esse relatório para helenomaffra@gmail.com"
4. Sistema: Gera preview do email com relatório
5. Usuário: "sim"
6. Sistema: Envia email com relatório completo

**Validações:**
- ✅ Relatório gerado corretamente
- ✅ Preview gerado com relatório completo (não truncado)
- ✅ `resumo_texto` salvo em `ultima_resposta_aguardando_email`
- ✅ Confirmação usa `resumo_texto` salvo (não gera novo)
- ✅ Email enviado contém relatório completo
- ✅ Usa `EmailSendCoordinator.send_report_email()`

**Arquivo:** `tests/test_email_flows.py::test_enviar_relatorio_preview_confirmar_enviado`

---

#### **Teste 1.5: Idempotência - Confirmar Duas Vezes Não Duplica Envio**
**Descrição:** Proteção contra envio duplicado.

**Cenário:**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
2. Sistema: Gera preview
3. Usuário: "sim"
4. Sistema: Envia email (draft marcado como `sent`)
5. Usuário: "sim" (novamente)
6. Sistema: Retorna "já foi enviado" (não envia novamente)

**Validações:**
- ✅ Primeira confirmação envia email
- ✅ Draft marcado como `sent`
- ✅ Segunda confirmação detecta que já foi enviado
- ✅ Não chama `EmailSendCoordinator.send_from_draft()` novamente
- ✅ Retorna mensagem de idempotência
- ✅ Email não é enviado duas vezes

**Arquivo:** `tests/test_email_flows.py::test_idempotencia_confirmar_duas_vezes_nao_duplica`

---

### **Categoria 2: Fluxos de DUIMP (CRÍTICO)**

#### **Teste 2.1: Criar DUIMP → Preview → Confirmar → DUIMP Criada**
**Descrição:** Fluxo completo de criação de DUIMP.

**Cenário:**
1. Usuário: "crie uma DUIMP para o processo DMD.0001/25"
2. Sistema: Gera capa da DUIMP e mostra preview
3. Usuário: "sim"
4. Sistema: Cria DUIMP no Portal Único

**Validações:**
- ✅ Capa da DUIMP gerada corretamente
- ✅ Estado `ultima_resposta_aguardando_duimp` salvo
- ✅ Confirmação detectada corretamente
- ✅ DUIMP criada com sucesso
- ✅ Estado limpo após criação

**Arquivo:** `tests/test_duimp_flows.py::test_criar_duimp_preview_confirmar_criada`

---

#### **Teste 2.2: Criar DUIMP → Cancelar → Nova DUIMP**
**Descrição:** Cancelamento e nova criação de DUIMP.

**Cenário:**
1. Usuário: "crie uma DUIMP para o processo DMD.0001/25"
2. Sistema: Gera capa da DUIMP
3. Usuário: "não" ou "cancela"
4. Sistema: Limpa estado
5. Usuário: "crie uma DUIMP para o processo DMD.0002/25"
6. Sistema: Gera nova capa (não usa processo anterior)

**Validações:**
- ✅ Estado limpo após cancelamento
- ✅ Nova DUIMP não usa processo anterior
- ✅ Preview gerado corretamente para novo processo

**Arquivo:** `tests/test_duimp_flows.py::test_criar_duimp_cancelar_nova_duimp`

---

### **Categoria 3: Fluxos de Streaming vs Não-Streaming (CRÍTICO)**

#### **Teste 3.1: Confirmação Funciona Igual em Streaming e Normal**
**Descrição:** Garantir que confirmação funciona igual nos dois modos.

**Cenário (Normal):**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
2. Sistema: Gera preview (via `processar_mensagem()`)
3. Usuário: "sim"
4. Sistema: Envia email

**Cenário (Streaming):**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
2. Sistema: Gera preview (via `processar_mensagem_stream()`)
3. Usuário: "sim"
4. Sistema: Envia email

**Validações:**
- ✅ Preview gerado igual nos dois modos
- ✅ Confirmação detectada igual nos dois modos
- ✅ Email enviado igual nos dois modos
- ✅ Usa `ConfirmationHandler` nos dois modos
- ✅ Usa `EmailSendCoordinator` nos dois modos

**Arquivo:** `tests/test_email_flows.py::test_confirmacao_funciona_igual_streaming_e_normal`

---

### **Categoria 4: Fluxos de Melhoria de Email (CRÍTICO)**

#### **Teste 4.1: Melhorar Email Depois de Enviado**
**Descrição:** Regra clara para melhorar email após envio.

**Cenário:**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
2. Sistema: Gera preview
3. Usuário: "sim"
4. Sistema: Envia email (draft marcado como `sent`)
5. Usuário: "melhore o email"
6. Sistema: Cria nova revisão e exige nova confirmação

**Validações:**
- ✅ Email enviado corretamente
- ✅ Draft marcado como `sent`
- ✅ Melhoria cria nova revisão (não sobrescreve enviado)
- ✅ Nova confirmação necessária
- ✅ Email melhorado enviado como nova revisão

**Arquivo:** `tests/test_email_flows.py::test_melhorar_email_depois_de_enviado`

---

### **Categoria 5: Fluxos de Draft ID como Fonte da Verdade (CRÍTICO)**

#### **Teste 5.1: Draft ID Sempre Fonte da Verdade na Confirmação**
**Descrição:** Garantir que confirmação sempre usa banco quando tem `draft_id`.

**Cenário:**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
2. Sistema: Gera preview, cria draft (revision 1)
3. Usuário: "melhore o email"
4. Sistema: Cria nova revisão (revision 2) no banco
5. Usuário: "sim"
6. Sistema: Envia revision 2 (não revision 1 da memória)

**Validações:**
- ✅ Draft criado no banco
- ✅ Melhoria cria nova revisão no banco
- ✅ Confirmação busca do banco (não usa memória)
- ✅ Email enviado contém revision 2
- ✅ `_obter_email_para_enviar()` prioriza banco

**Arquivo:** `tests/test_email_flows.py::test_draft_id_sempre_fonte_da_verdade`

---

#### **Teste 5.2: Múltiplos Previews no Mesmo Session ID**
**Descrição:** Garantir que múltiplos previews não interferem.

**Cenário:**
1. Usuário: "mande um email para helenomaffra@gmail.com sobre a reunião"
2. Sistema: Gera preview 1 (draft_id_1)
3. Usuário: "mande um email para outro@gmail.com sobre outra coisa"
4. Sistema: Gera preview 2 (draft_id_2)
5. Usuário: "sim"
6. Sistema: Envia preview 2 (não preview 1)

**Validações:**
- ✅ Preview 1 criado corretamente
- ✅ Preview 2 criado corretamente (não sobrescreve preview 1)
- ✅ Confirmação envia preview 2 (último preview)
- ✅ Preview 1 ainda existe no banco (não deletado)

**Arquivo:** `tests/test_email_flows.py::test_multiplos_previews_mesmo_session_id`

---

## 🏗️ Estrutura de Testes Proposta

```
tests/
├── test_email_flows.py          # Testes de fluxos de email
│   ├── test_criar_email_preview_confirmar_enviado
│   ├── test_criar_email_melhorar_confirmar_enviar_melhorado
│   ├── test_criar_email_corrigir_destinatario_confirmar_enviar
│   ├── test_enviar_relatorio_preview_confirmar_enviado
│   ├── test_idempotencia_confirmar_duas_vezes_nao_duplica
│   ├── test_confirmacao_funciona_igual_streaming_e_normal
│   ├── test_melhorar_email_depois_de_enviado
│   ├── test_draft_id_sempre_fonte_da_verdade
│   └── test_multiplos_previews_mesmo_session_id
├── test_duimp_flows.py           # Testes de fluxos de DUIMP
│   ├── test_criar_duimp_preview_confirmar_criada
│   └── test_criar_duimp_cancelar_nova_duimp
└── conftest.py                   # Fixtures compartilhadas
    ├── fixture_chat_service
    ├── fixture_email_draft_service
    ├── fixture_email_send_coordinator
    └── fixture_mock_email_service
```

---

## 🛠️ Ferramentas de Teste

### Recomendado:
- **pytest** - Framework de testes Python
- **pytest-mock** - Para mocks
- **pytest-asyncio** - Se precisar testar async (futuro)

### Estrutura de Teste:

```python
import pytest
from services.chat_service import ChatService
from services.email_draft_service import get_email_draft_service
from services.email_send_coordinator import get_email_send_coordinator

@pytest.fixture
def chat_service():
    """Fixture para ChatService limpo."""
    service = ChatService()
    # Limpar estado antes de cada teste
    service.ultima_resposta_aguardando_email = None
    return service

def test_criar_email_preview_confirmar_enviado(chat_service):
    """Teste 1.1: Criar Email → Preview → Confirmar → Enviado"""
    # 1. Criar email
    resultado1 = chat_service.processar_mensagem(
        mensagem="mande um email para helenomaffra@gmail.com sobre a reunião de hoje",
        session_id="test_session"
    )
    
    # Validar preview
    assert resultado1.get('aguardando_confirmacao') == True
    assert 'Preview do Email' in resultado1.get('resposta', '')
    assert chat_service.ultima_resposta_aguardando_email is not None
    draft_id = chat_service.ultima_resposta_aguardando_email.get('draft_id')
    assert draft_id is not None
    
    # 2. Confirmar
    resultado2 = chat_service.processar_mensagem(
        mensagem="sim",
        session_id="test_session"
    )
    
    # Validar envio
    assert resultado2.get('sucesso') == True
    assert 'enviado com sucesso' in resultado2.get('resposta', '').lower()
    
    # Validar draft marcado como enviado
    draft_service = get_email_draft_service()
    draft = draft_service.obter_draft(draft_id)
    assert draft.status == 'sent'
```

---

## 📊 Priorização

### **Alta Prioridade (Fazer Primeiro):**
1. ✅ **Teste 1.1** - Criar Email → Preview → Confirmar → Enviado
2. ✅ **Teste 1.2** - Criar Email → Melhorar → Confirmar → Enviar Melhorado
3. ✅ **Teste 1.5** - Idempotência (confirmar duas vezes)
4. ✅ **Teste 5.1** - Draft ID sempre fonte da verdade

### **Média Prioridade:**
5. ✅ **Teste 1.3** - Corrigir destinatário
6. ✅ **Teste 1.4** - Enviar relatório
7. ✅ **Teste 3.1** - Streaming vs normal

### **Baixa Prioridade (Pode Fazer Depois):**
8. ✅ **Teste 2.1** - Criar DUIMP
9. ✅ **Teste 2.2** - Cancelar DUIMP
10. ✅ **Teste 4.1** - Melhorar após enviado
11. ✅ **Teste 5.2** - Múltiplos previews

---

## 🎯 Como Executar

```bash
# Executar todos os testes
pytest tests/

# Executar apenas testes de email
pytest tests/test_email_flows.py

# Executar apenas testes de DUIMP
pytest tests/test_duimp_flows.py

# Executar com verbose
pytest tests/ -v

# Executar com cobertura
pytest tests/ --cov=services --cov-report=html
```

---

## ⚠️ Notas Importantes

1. **Isolamento:** Cada teste deve ser independente (não depender de outros)
2. **Limpeza:** Limpar estado antes de cada teste (fixtures)
3. **Mocks:** Mockar serviços externos (email, Portal Único, etc.)
4. **Assertions:** Validar comportamento, não implementação
5. **Documentação:** Cada teste deve ter docstring explicando o cenário

---

## 📝 Exemplo de Teste Completo

```python
def test_criar_email_melhorar_confirmar_enviar_melhorado(chat_service, mock_email_service):
    """
    Teste 1.2: Criar Email → Melhorar → Confirmar → Enviar Melhorado
    
    Valida que:
    - Preview inicial é gerado
    - Melhoria cria nova revisão no banco
    - Confirmação envia versão melhorada (não original)
    """
    # 1. Criar email
    resultado1 = chat_service.processar_mensagem(
        mensagem="mande um email para helenomaffra@gmail.com sobre a reunião",
        session_id="test_session"
    )
    
    assert resultado1.get('aguardando_confirmacao') == True
    draft_id = chat_service.ultima_resposta_aguardando_email.get('draft_id')
    assert draft_id is not None
    
    # Obter draft original
    draft_service = get_email_draft_service()
    draft_original = draft_service.obter_draft(draft_id)
    assert draft_original.revision == 1
    conteudo_original = draft_original.conteudo
    
    # 2. Melhorar email
    resultado2 = chat_service.processar_mensagem(
        mensagem="melhore o email",
        session_id="test_session"
    )
    
    # Validar que preview foi reemitido
    assert 'Preview do Email' in resultado2.get('resposta', '')
    
    # Validar que nova revisão foi criada
    draft_melhorado = draft_service.obter_draft(draft_id)
    assert draft_melhorado.revision == 2
    assert draft_melhorado.conteudo != conteudo_original
    
    # 3. Confirmar
    resultado3 = chat_service.processar_mensagem(
        mensagem="sim",
        session_id="test_session"
    )
    
    # Validar que email melhorado foi enviado
    assert resultado3.get('sucesso') == True
    assert mock_email_service.send_email_called
    
    # Validar que conteúdo enviado é o melhorado (não original)
    email_enviado = mock_email_service.last_email_sent
    assert email_enviado['body'] == draft_melhorado.conteudo
    assert email_enviado['body'] != conteudo_original
```

---

**Última atualização:** 09/01/2026
