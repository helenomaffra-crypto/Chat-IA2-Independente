# 📧 Melhorias de Fluidez: Sistema de Emails

**Data:** 09/01/2026  
**Status:** ✅ **IMPLEMENTADO** - Regras de perguntar quando não tem certeza adicionadas

---

## 🎯 Objetivo

Melhorar a fluidez do sistema de emails fazendo com que a IA **pergunte quando não tem certeza** ao invés de enviar algo errado.

---

## ✅ O que foi implementado

### 1. Regras no Prompt Builder (`services/prompt_builder.py`)

Adicionada seção crítica sobre perguntar quando não tem certeza:

```
🚨🚨🚨 CRÍTICO - PERGUNTAR QUANDO NÃO TEM CERTEZA:
* Se não tiver certeza sobre qual relatório/email enviar → PERGUNTE ao usuário
* Se houver ambiguidade sobre destinatário → PERGUNTE ao usuário
* Se não souber qual conteúdo incluir → PERGUNTE ao usuário
* É MELHOR PERGUNTAR do que enviar algo errado
* Exemplos de perguntas:
  - "Qual relatório você gostaria de enviar? O resumo do dia ou o fechamento?"
  - "Para qual email devo enviar? Você mencionou [email1] ou [email2]?"
  - "Qual conteúdo você gostaria que eu incluísse no email?"
  - "Não encontrei um relatório recente. Você gostaria que eu gere um novo ou há um específico que você tem em mente?"
```

### 2. Regras nas Tool Definitions (`services/tool_definitions.py`)

#### `enviar_email_personalizado`:
- Adicionada regra: **"🚨🚨🚨 CRÍTICO - PERGUNTAR QUANDO NÃO TEM CERTEZA: Se não tiver certeza sobre destinatário, assunto ou conteúdo → PERGUNTE ao usuário ANTES de chamar a função. É MELHOR PERGUNTAR do que enviar algo errado."**

#### `enviar_relatorio_email`:
- Adicionada regra: **"🚨🚨🚨 CRÍTICO - PERGUNTAR QUANDO NÃO TEM CERTEZA: Se não tiver certeza sobre qual relatório enviar, destinatário ou categoria → PERGUNTE ao usuário ANTES de chamar a função. É MELHOR PERGUNTAR do que enviar algo errado."**
- Campo `destinatario` atualizado: **"Se não fornecido e não houver email padrão, PERGUNTE ao usuário antes de chamar a função. É MELHOR PERGUNTAR do que enviar para email errado."**

---

## 📋 Casos de Uso

### Caso 1: Destinatário Ambíguo
**Antes:**
```
Usuário: "envie um email para heleno"
mAIke: [Tenta adivinhar qual email e pode enviar errado]
```

**Agora:**
```
Usuário: "envie um email para heleno"
mAIke: "Para qual email devo enviar? Você tem helenomaffra@gmail.com ou outro email?"
```

### Caso 2: Relatório Não Claro
**Antes:**
```
Usuário: "mande esse relatorio"
mAIke: [Tenta adivinhar qual relatório e pode enviar errado]
```

**Agora:**
```
Usuário: "mande esse relatorio"
mAIke: "Qual relatório você gostaria de enviar? O resumo do dia ou o fechamento?"
```

### Caso 3: Conteúdo Não Claro
**Antes:**
```
Usuário: "envie um email"
mAIke: [Tenta adivinhar conteúdo e pode enviar errado]
```

**Agora:**
```
Usuário: "envie um email"
mAIke: "Qual conteúdo você gostaria que eu incluísse no email? Sobre qual assunto?"
```

---

## 🔧 Arquivos Modificados

1. **`services/prompt_builder.py`**:
   - Adicionada seção "PERGUNTAR QUANDO NÃO TEM CERTEZA" no system prompt
   - Linha ~399-410

2. **`services/tool_definitions.py`**:
   - Atualizada descrição de `enviar_email_personalizado` com regra de perguntar
   - Atualizada descrição de `enviar_relatorio_email` com regra de perguntar
   - Atualizado campo `destinatario` de `enviar_relatorio_email`

---

## ✅ Status

- ✅ Regras adicionadas ao prompt builder
- ✅ Regras adicionadas às tool definitions
- ✅ Campo de destinatário atualizado
- ✅ **Validação de extração: se não extrair, perguntar ao usuário** (implementado em `chat_service.py`)
- ⏳ **Aguardando validação em uso real**

### Validação de Extração Implementada

Quando o sistema não consegue extrair o email melhorado:
- ✅ Se tem `draft_id`: deixa a IA processar novamente (pode usar `melhorar_email_draft`)
- ✅ Se não tem `draft_id`: **pergunta ao usuário** para reescrever ou especificar o que melhorar

---

## 🎯 Próximos Passos (Opcional)

1. **Monitorar uso**: Verificar se a IA está perguntando quando deveria
2. **Ajustar exemplos**: Adicionar mais exemplos de perguntas se necessário
3. **Melhorar detecção**: Adicionar lógica de detecção de ambiguidade no código (além do prompt)

---

**Última atualização:** 09/01/2026
