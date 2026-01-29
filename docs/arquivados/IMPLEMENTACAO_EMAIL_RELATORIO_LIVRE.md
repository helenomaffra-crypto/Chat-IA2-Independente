# Implementação: Email de Relatório Diário e Email Livre

## 📋 Resumo das Mudanças

Este documento descreve a implementação de duas novas capacidades de email:
1. **Enviar o relatório "O QUE TEMOS PRA HOJE" por email**
2. **Enviar email livre (texto ditado pelo usuário)**

---

## ✅ Arquivos Modificados/Criados

### 1. `services/agents/processo_agent.py` (MODIFICADO)

**Mudança:** Salvar relatório no contexto após gerar

**Localização:** Função `_obter_dashboard_hoje` (linha ~4199)

**Código Adicionado:**
```python
# ✅ NOVO: Salvar relatório no contexto para uso em emails
try:
    from services.context_service import salvar_contexto_sessao
    from datetime import datetime
    session_id_para_salvar = context.get('session_id') if context else None
    if session_id_para_salvar:
        data_referencia = datetime.now().strftime('%Y-%m-%d')
        salvar_contexto_sessao(
            session_id=session_id_para_salvar,
            tipo_contexto='relatorio_diario',
            chave='o_que_tem_hoje',
            valor=resposta,  # Texto completo do relatório
            dados_adicionais={
                'data_referencia': data_referencia,
                'categoria': categoria,
                'modal': modal
            }
        )
        logger.info(f"✅ Relatório 'O QUE TEMOS PRA HOJE' salvo no contexto para sessão {session_id_para_salvar}")
except Exception as e:
    logger.debug(f'Erro ao salvar relatório no contexto: {e}')
```

**Quando Executa:**
- Após gerar o relatório "O QUE TEMOS PRA HOJE"
- Salva o texto completo do relatório no contexto da sessão

---

### 2. `services/email_builder_service.py` (MODIFICADO)

**Mudanças:** Adicionadas duas novas funções

#### 2.1 `montar_email_relatorio_diario()`

**Função:**
```python
def montar_email_relatorio_diario(
    self,
    destinatario: str,
    relatorio_texto: str,
    data_referencia: Optional[str] = None,
    nome_usuario: Optional[str] = None
) -> Dict[str, Any]
```

**Responsabilidades:**
- Monta email com o relatório diário completo
- Extrai data do relatório se não fornecida
- Formata assunto: "Resumo diário – O que temos pra hoje - DD/MM/YYYY"
- Chama `_construir_corpo_email_relatorio_diario()` para montar o corpo

**Estrutura do Email Gerado:**
```
Assunto: "Resumo diário – O que temos pra hoje - 19/12/2025"

Corpo:
Olá, [Nome],

Segue o resumo diário de processos de importação para hoje (19/12/2025):

[RELATÓRIO COMPLETO AQUI - texto já formatado]

Qualquer dúvida, estamos à disposição.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores
```

#### 2.2 `montar_email_livre()`

**Função:**
```python
def montar_email_livre(
    self,
    destinatario: str,
    texto_mensagem: str,
    nome_usuario: Optional[str] = None,
    assunto_personalizado: Optional[str] = None
) -> Dict[str, Any]
```

**Responsabilidades:**
- Monta email livre com texto ditado pelo usuário
- Assunto padrão: "Mensagem de [nome] via mAIke" (ou "Mensagem via mAIke" se não tiver nome)
- Chama `_construir_corpo_email_livre()` para montar o corpo

**Estrutura do Email Gerado:**
```
Assunto: "Mensagem de Heleno via mAIke" (ou "Mensagem via mAIke")

Corpo:
Olá,

[texto ditado pelo usuário]

Enviado por mAIke – Assistente de COMEX (Make Consultores).
```

---

### 3. `services/precheck_service.py` (MODIFICADO)

**Mudanças:** Adicionadas duas novas funções de precheck e integradas no fluxo

#### 3.1 Integração no Fluxo Principal

**Localização:** Função `tentar_responder_sem_ia` (linha ~75)

**Ordem de Prioridade:**
1. Prechecks críticos (situação de processo, etc.)
2. **✅ NOVO:** `_precheck_envio_email_relatorio_diario` (PRIORIDADE ALTA)
3. Precheck de envio de resumo/briefing por email
4. **✅ NOVO:** `_precheck_envio_email_livre`
5. Precheck de envio de informações de processo por email

#### 3.2 `_precheck_envio_email_relatorio_diario()`

**Detecta Padrões:**
- "envia esse relatório para fulano@empresa.com"
- "manda esse resumo pra helenomaffra@gmail.com"
- "envia por email o que temos pra hoje para X"

**Fluxo:**
1. Detecta padrões de envio de relatório
2. Extrai email do destinatário
3. Busca relatório no contexto (`relatorio_diario` / `o_que_tem_hoje`)
4. Se encontrou:
   - Usa `email_builder_service.montar_email_relatorio_diario()`
   - Chama `enviar_email_personalizado` com preview
5. Se não encontrou:
   - Retorna mensagem amigável pedindo para gerar o relatório primeiro

**Mensagem de Erro:**
```
⚠️ Não encontrei nenhum relatório "O que temos pra hoje" recente nesta conversa.

💡 Para enviar o relatório por email, você precisa:
1. Pedir primeiro "o que temos pra hoje"
2. Depois que eu mostrar o resumo, pedir para eu enviar por email
```

#### 3.3 `_precheck_envio_email_livre()`

**Detecta Padrões:**
- "manda um email para fulano@empresa.com dizendo que não vou poder ir para a reunião"
- "envia um email para helenomaffra@gmail.com avisando que a carga atrasou"
- "manda um email para cliente@empresa.com dizendo: boa tarde, segue em anexo o extrato da DI."

**Fluxo:**
1. Verifica se NÃO é relatório diário (prioridade)
2. Detecta padrões de email livre
3. Extrai email do destinatário
4. Extrai texto da mensagem (após "dizendo", "avisando", "que", "com", ":", etc.)
5. Se encontrou texto:
   - Usa `email_builder_service.montar_email_livre()`
   - Chama `enviar_email_personalizado` com preview
6. Se não encontrou texto:
   - Retorna mensagem pedindo esclarecimento

**Mensagem de Erro:**
```
⚠️ Você quer que eu envie qual mensagem nesse e-mail?

💡 Exemplo: "manda um email para fulano@empresa.com dizendo que não vou poder ir para a reunião"
```

---

### 4. `services/tool_executor.py` (MODIFICADO)

**Mudança:** Incluir `session_id` no context

**Código Adicionado:**
```python
# ✅ NOVO: Incluir session_id no context se disponível
context_dict = {
    "mensagem_original": mensagem_original,
    "chat_service": chat_service,
}
if hasattr(chat_service, 'session_id_atual') and chat_service.session_id_atual:
    context_dict["session_id"] = chat_service.session_id_atual

resultado_router = self.tool_router.route(
    nome_funcao,
    argumentos,
    context=context_dict,
)
```

**Motivo:** Garantir que o `session_id` seja passado para os agents, permitindo salvar o relatório no contexto.

---

## 🔍 Lógica de Detecção de Intenção

### Prioridade de Detecção

1. **Email de Relatório Diário** (PRIORIDADE ALTA)
   - Detecta: "relatorio", "relatório", "resumo", "o que temos pra hoje"
   - Busca no contexto: `relatorio_diario` / `o_que_tem_hoje`

2. **Email Livre**
   - Detecta: "manda um email", "envia um email" + destinatário + texto
   - NÃO detecta se mencionar "relatorio", "resumo", etc. (deixa para relatório diário)

3. **Email de Processo/NCM** (já existente)
   - Detecta: informações de processo ou NCM no histórico

### Heurística de Extração de Texto (Email Livre)

**Padrões (em ordem de prioridade):**
1. `(?:dizendo|avisando|informando|que|com|:)\s+(.+)`
2. `[email]\s+(?:dizendo|avisando|informando|que|com|:)\s+(.+)`
3. `[email]\s+(.+)` (fallback: tudo após o email)

**Limpeza:**
- Remove email se estiver no final do texto extraído
- Remove palavras finais comuns: "para", "por", "via", "email"
- Mínimo de 3 caracteres para considerar válido

---

## 🧪 Exemplos de Uso

### Teste 1: Relatório Diário

**Entrada:**
```
Usuário: "o que temos pra hoje"
mAIke: [mostra relatório completo]

Usuário: "envia esse relatório para helenomaffra@gmail.com"
```

**Preview Gerado:**
```
📧 Preview do Email:
Para: helenomaffra@gmail.com
Assunto: Resumo diário – O que temos pra hoje - 19/12/2025

Conteúdo:
Olá, Heleno,

Segue o resumo diário de processos de importação para hoje (19/12/2025):

📅 O QUE TEMOS PRA HOJE - 19/12/2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚢 CHEGANDO HOJE (0 processo(s))
...
📊 RESUMO: 0 chegando | 2 prontos | 1 em DTA | 9 pendências | 8 DIs | 0 DUIMPs

Qualquer dúvida, estamos à disposição.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores

💡 Confirme para enviar (digite 'sim' ou 'enviar')
```

### Teste 2: Relatório Sem Contexto

**Entrada:**
```
Usuário (em sessão nova): "envia esse relatório para helenomaffra@gmail.com"
```

**Resposta:**
```
⚠️ Não encontrei nenhum relatório "O que temos pra hoje" recente nesta conversa.

💡 Para enviar o relatório por email, você precisa:
1. Pedir primeiro "o que temos pra hoje"
2. Depois que eu mostrar o resumo, pedir para eu enviar por email

Ou peça novamente "o que temos pra hoje" e depois peça para enviar por email.
```

### Teste 3: Email Livre

**Entrada:**
```
Usuário: "manda um email para helenomaffra@gmail.com dizendo que não vou poder ir pra reunião hoje"
```

**Preview Gerado:**
```
📧 Preview do Email:
Para: helenomaffra@gmail.com
Assunto: Mensagem de Heleno via mAIke

Conteúdo:
Olá,

não vou poder ir pra reunião hoje.

Enviado por mAIke – Assistente de COMEX (Make Consultores).

💡 Confirme para enviar (digite 'sim' ou 'enviar')
```

---

## 📊 Estrutura de Dados

### Contexto de Relatório Diário

**Tipo:** `relatorio_diario`  
**Chave:** `o_que_tem_hoje`  
**Valor:** Texto completo do relatório (string)  
**Dados Adicionais:**
```json
{
    "data_referencia": "2025-12-19",
    "categoria": "MV5" (ou null),
    "modal": "Marítimo" (ou null)
}
```

**Onde é Salvo:**
- Tabela: `contexto_sessao` (SQLite)
- Após: `_obter_dashboard_hoje` gerar o relatório

**Onde é Buscado:**
- `_precheck_envio_email_relatorio_diario`
- Via `buscar_contexto_sessao(session_id, tipo_contexto='relatorio_diario', chave='o_que_tem_hoje')`

---

## ✅ Checklist de Validação

- [x] Relatório diário salvo no contexto após gerar
- [x] `session_id` passado para agents via `tool_executor`
- [x] Detecção de email de relatório diário no precheck
- [x] Detecção de email livre no precheck
- [x] `montar_email_relatorio_diario()` implementado
- [x] `montar_email_livre()` implementado
- [x] Preview e confirmação funcionando
- [x] Mensagens de erro amigáveis
- [x] Prioridade correta (relatório diário antes de email livre)

---

## 🚀 Próximos Passos (Opcional)

1. **Melhorar Extração de Texto:**
   - Suportar mais variações de linguagem natural
   - Detectar assunto personalizado se mencionado

2. **Suporte a Múltiplos Destinatários:**
   - Permitir "envia para X e Y"

3. **Template HTML:**
   - Gerar email em HTML formatado (atualmente é texto)

4. **Histórico de Emails Enviados:**
   - Salvar emails enviados para referência futura

---

**Data da Implementação:** 19/12/2025  
**Autor:** Assistente de Desenvolvimento

