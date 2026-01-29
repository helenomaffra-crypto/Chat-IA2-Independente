# 📧 Análise Completa do Fluxo de Email - V1

**Data:** 26/01/2026  
**Status:** 📋 **ANÁLISE COMPLETA** - Mapeamento detalhado antes de qualquer modificação

---

## 🎯 Objetivo

Mapear **COMPLETAMENTE** o fluxo de email atual antes de sugerir melhorias. O sistema de email é complexo e tem múltiplos pontos críticos que foram desenvolvidos ao longo do tempo para controlar o contexto.

---

## 📊 Tipos de Email Identificados

### 1. **Email de Classificação NCM + Alíquotas**
- **Detecção:** `_precheck_envio_email_ncm()`
- **Prioridade:** 1 (após emails pessoais)
- **Contexto:** `ultima_classificacao_ncm` do `context_service`
- **Montagem:** `EmailBuilderService.montar_email_classificacao_ncm()`
- **Use Case:** `EnviarEmailClassificacaoNcmUseCase`
- **Características:**
  - Requer contexto de NCM salvo no banco
  - Usa `EmailBuilderService` para montar email completo
  - Inclui NCM, alíquotas, NESH, justificativa
  - Sempre mostra preview primeiro

### 2. **Email de Relatório Genérico**
- **Detecção:** `_precheck_envio_email_relatorio_generico()`
- **Prioridade:** 2
- **Contexto:** Último relatório salvo no `report_service`
- **Montagem:** Usa `enviar_relatorio_email` tool
- **Características:**
  - Dashboards padrão ("O que temos pra hoje", "Fechamento do dia")
  - Usa `last_visible_report_id` para identificar relatório correto
  - Suporta filtros por categoria
  - Mensagens curtas ("envia para X") quando há relatório recente

### 3. **Email de Relatório Ad Hoc**
- **Detecção:** `_precheck_envio_email_relatorio_adhoc()`
- **Prioridade:** 2 (mesma hierarquia do genérico, mas processado antes)
- **Contexto:** Última resposta do histórico OU relatório salvo
- **Montagem:** Usa `enviar_email_personalizado` com texto EXATO da última resposta
- **Características:**
  - Detecta "manda esse relatório"
  - Usa `last_visible_report_id` como fonte da verdade
  - NÃO re-gera o relatório, apenas envia o que foi exibido
  - Remove `[REPORT_META:...]` do texto antes de enviar

### 4. **Email de Resumo/Briefing**
- **Detecção:** `_precheck_envio_email()`
- **Prioridade:** 3
- **Contexto:** Histórico + categoria mencionada
- **Montagem:** Gera relatório específico por categoria
- **Características:**
  - Padrões: "resumo MV5 por email", "briefing DMD"
  - Extrai categoria da mensagem ou do histórico
  - Gera relatório sob demanda

### 5. **Email de Processo Específico**
- **Detecção:** `_precheck_envio_email_processo()`
- **Prioridade:** 5 (último na hierarquia)
- **Contexto:** Última resposta do histórico que contém informações de processo
- **Montagem:** Usa `enviar_email_personalizado` com conteúdo extraído do histórico
- **Características:**
  - Detecta informações de processo na última resposta
  - Extrai conteúdo automaticamente do histórico
  - Assunto: "Informações do Processo [NÚMERO]"
  - **PONTO CRÍTICO:** Depende de extração correta do histórico

### 6. **Email Livre (Personalizado)**
- **Detecção:** `_precheck_envio_email_livre()`
- **Prioridade:** 4
- **Contexto:** Texto ditado pelo usuário (sem contexto de processo/NCM)
- **Montagem:** Usa `enviar_email_personalizado` com texto do usuário
- **Características:**
  - Padrões: "manda um email para X dizendo que Y"
  - IGNORA contexto anterior
  - Texto livre do usuário

### 7. **Email Pessoal/Amoroso/Informal**
- **Detecção:** `tentar_precheck_email()` (primeiro check)
- **Prioridade:** 0 (máxima - processado ANTES de tudo)
- **Contexto:** IGNORA TODO contexto anterior
- **Montagem:** Deixa IA processar normalmente
- **Características:**
  - Palavras-chave: "amoroso", "convite", "jantar", "pessoal"
  - Retorna `None` para deixar IA processar sem contexto

---

## 🔄 Fluxo de Decisão (Hierarquia)

```
tentar_precheck_email()
│
├─ 1. Email pessoal? → IGNORA contexto, deixa IA processar
│
├─ 2. "Esse relatório" + relatório visível? → _precheck_envio_email_relatorio_adhoc()
│
├─ 3. Email NCM + contexto NCM? → _precheck_envio_email_ncm()
│
├─ 4. Email relatório genérico? → _precheck_envio_email_relatorio_generico()
│
├─ 5. Email resumo/briefing? → _precheck_envio_email()
│
├─ 6. Email livre? → _precheck_envio_email_livre()
│
└─ 7. Email processo? → _precheck_envio_email_processo()
```

---

## 🔍 Pontos Críticos de Extração de Contexto

### **1. Extração de Conteúdo do Histórico (Email de Processo)**

**Localização:** `_precheck_envio_email_processo()` (linhas 1917-1947)

**Como funciona:**
1. Busca na última resposta do histórico por padrões:
   - Informações de processo: "Processo", "CE", "DI", "DUIMP", "Categoria:", formato `ALH.0166/25`
   - Informações de NCM: "NCM", "NESH", "Alíquotas", "II:", "IPI:", "TECwin"
   - Informações técnicas: "Confiança", "Explicação", "Nota Explicativa"

2. Se encontrar, usa a resposta completa como conteúdo do email

**Pontos críticos:**
- ⚠️ Depende do formato da resposta estar correto
- ⚠️ Se a resposta tiver múltiplos processos, pode pegar o errado
- ⚠️ Se a resposta for muito longa, pode incluir informações irrelevantes
- ⚠️ Se não encontrar padrões, tenta extrair da mensagem atual (pode falhar)

**Código crítico:**
```python
# Linha 1917-1947
if not conteudo_email and historico and len(historico) > 0:
    for i in range(len(historico) - 1, -1, -1):
        resposta_anterior = historico[i].get('resposta', '')
        if resposta_anterior:
            tem_processo = (
                'Processo' in resposta_anterior or 
                'CE' in resposta_anterior or 
                # ... mais padrões
            )
            if tem_processo or tem_ncm or tem_info_tecnica:
                conteudo_email = resposta_anterior  # ⚠️ USA RESPOSTA COMPLETA
                break
```

### **2. Extração de Contexto NCM**

**Localização:** `EmailBuilderService.extrair_contexto_ncm_do_historico()`

**Como funciona:**
1. Busca no `context_service` por `ultima_classificacao_ncm`
2. Se não encontrar, tenta extrair do histórico usando padrões
3. Monta contexto completo com NCM, alíquotas, NESH

**Pontos críticos:**
- ⚠️ Depende de contexto estar salvo no banco
- ⚠️ Se contexto estiver desatualizado, usa dados antigos
- ⚠️ Extração do histórico é frágil (padrões podem mudar)

### **3. Identificação de Relatório Visível**

**Localização:** `_precheck_envio_email_relatorio_adhoc()` (linhas 1166-1202)

**Como funciona:**
1. Usa `last_visible_report_id` como fonte da verdade
2. Busca relatório salvo no `report_service`
3. Se não encontrar, usa última resposta do histórico como fallback

**Pontos críticos:**
- ⚠️ `last_visible_report_id` pode estar desatualizado
- ⚠️ Fallback para histórico pode pegar mensagem errada (notificação, resposta de processo)
- ⚠️ Depende de relatório estar salvo corretamente

**Código crítico:**
```python
# Linha 1173-1202
last_visible = obter_last_visible_report_id(session_id, dominio=dominio_detectado)
if last_visible and last_visible.get('id'):
    relatorio_salvo = buscar_relatorio_por_id(session_id, last_visible['id'])
    if relatorio_salvo:
        ultima_resposta_texto = relatorio_salvo.texto_chat  # ✅ Fonte da verdade
else:
    # ⚠️ FALLBACK: Usa histórico (pode pegar mensagem errada)
    if historico and len(historico) > 0:
        ultima_resposta = historico[-1].get('resposta', '')
        ultima_resposta_texto = ultima_resposta  # ⚠️ Pode ser notificação/processo
```

### **4. Detecção de Referência ao Anterior**

**Localização:** `_precheck_envio_email_processo()` (linhas 1864-1874)

**Como funciona:**
1. Detecta palavras-chave: "esse", "essa", "este", "esta", "relatorio", "acima", "anterior"
2. Se detectar, busca conteúdo no histórico
3. Se não detectar, tenta extrair da mensagem atual

**Pontos críticos:**
- ⚠️ Detecção é baseada em palavras-chave (pode falhar com variações)
- ⚠️ Se não detectar referência, pode usar conteúdo errado
- ⚠️ Diferença entre "referência" e "conteúdo próprio" é sutil

---

## ⚠️ Problemas Identificados

### **1. Extração Frágil do Histórico**

**Problema:** A extração de conteúdo do histórico depende de padrões de texto que podem mudar.

**Exemplo:**
- Se a resposta mudar de formato (ex: remover emojis), a detecção pode falhar
- Se a resposta tiver múltiplos processos, pode pegar o errado
- Se a resposta for muito longa, pode incluir informações irrelevantes

**Impacto:** Email pode ter conteúdo errado ou incompleto.

### **2. Dependência de `last_visible_report_id`**

**Problema:** Se `last_visible_report_id` estiver desatualizado ou incorreto, o email pode usar relatório errado.

**Exemplo:**
- Usuário gera relatório A
- Usuário gera relatório B (deveria atualizar `last_visible`)
- Usuário pede "envie esse relatório"
- Sistema usa relatório A (antigo)

**Impacto:** Email envia relatório errado.

### **3. Conflito entre Tipos de Email**

**Problema:** A hierarquia de decisão pode escolher o tipo errado de email.

**Exemplo:**
- Usuário: "envie esse relatorio para X" (após consulta de processo)
- Sistema pode detectar como "email de processo" em vez de "relatório ad hoc"
- Resultado: Email tem conteúdo de processo, não relatório

**Impacto:** Email tem tipo/conteúdo errado.

### **4. Contexto NCM Desatualizado**

**Problema:** Se o contexto de NCM estiver desatualizado, o email usa dados antigos.

**Exemplo:**
- Usuário classifica NCM 90041000
- Usuário classifica NCM 90042000 (deveria atualizar contexto)
- Usuário pede "envie email com alíquotas"
- Sistema usa NCM 90041000 (antigo)

**Impacto:** Email tem NCM/alíquotas erradas.

### **5. Extração de Email do Histórico**

**Problema:** Se o email não estiver na mensagem atual, tenta buscar no histórico (pode pegar email errado).

**Código:**
```python
# Linha 1853-1862
if not email and historico and len(historico) > 0:
    for i in range(len(historico) - 1, -1, -1):
        msg_anterior = historico[i].get('mensagem', '')
        if msg_anterior:
            match_email_hist = re.search(padrao_email, msg_anterior.lower())
            if match_email_hist:
                email = match_email_hist.group(1)  # ⚠️ Pode pegar email antigo
```

**Impacto:** Email enviado para destinatário errado.

---

## ✅ O Que Está Funcionando Bem

### **1. Hierarquia Clara de Decisão**
- Ordem de prioridade bem definida
- Emails pessoais têm prioridade máxima (ignoram contexto)
- Relatórios têm prioridade sobre processos

### **2. Sistema de Preview**
- Todos os emails mostram preview antes de enviar
- Usuário pode confirmar ou cancelar
- Sistema de drafts com revisões

### **3. Detecção de "Esse Relatório"**
- Detecta corretamente quando usuário quer enviar relatório visível
- Usa `last_visible_report_id` como fonte da verdade
- Fallback para histórico quando necessário

### **4. Email Builder Service**
- Centraliza montagem de emails de NCM
- Formatação consistente
- Inclui todas as informações necessárias

---

## 🎯 Recomendações (SEM MEXER NO CÓDIGO AINDA)

### **1. Melhorar Extração de Contexto de Processo**

**Problema atual:** Usa resposta completa do histórico (pode incluir informações irrelevantes).

**Solução sugerida:**
- Extrair apenas seções relevantes da resposta
- Validar se o processo mencionado na resposta corresponde ao contexto atual
- Limitar tamanho do conteúdo extraído

**Risco:** Mudança pode quebrar emails que dependem da resposta completa.

### **2. Validar `last_visible_report_id`**

**Problema atual:** Não valida se `last_visible_report_id` está atualizado.

**Solução sugerida:**
- Validar timestamp do relatório (não usar se muito antigo)
- Verificar se relatório ainda existe no banco
- Adicionar fallback mais robusto

**Risco:** Validação pode rejeitar relatórios válidos.

### **3. Melhorar Detecção de Referência**

**Problema atual:** Detecção baseada em palavras-chave é frágil.

**Solução sugerida:**
- Usar análise semântica (IA) para detectar referências
- Validar se há relatório/processo visível antes de usar histórico
- Adicionar mais padrões de detecção

**Risco:** Análise semântica pode ser lenta ou imprecisa.

### **4. Cache de Contexto de Processo**

**Problema atual:** Busca contexto de processo toda vez que precisa.

**Solução sugerida:**
- Cachear contexto de processo por sessão
- Invalidar cache quando processo é atualizado
- Usar cache para emails subsequentes

**Risco:** Cache pode ficar desatualizado.

---

## 📋 Checklist Antes de Modificar

- [ ] Entender completamente o fluxo atual
- [ ] Identificar todos os pontos críticos
- [ ] Mapear dependências entre componentes
- [ ] Validar com casos de uso reais
- [ ] Criar testes antes de modificar
- [ ] Modificar incrementalmente
- [ ] Testar após cada mudança
- [ ] Documentar mudanças

---

## 🚨 AVISOS CRÍTICOS

1. **NÃO modificar a hierarquia de decisão sem testar extensivamente**
2. **NÃO remover fallbacks sem garantir que há alternativa**
3. **NÃO mudar extração de histórico sem validar com casos reais**
4. **NÃO tocar em `last_visible_report_id` sem entender impacto**
5. **SEMPRE manter compatibilidade com emails existentes**

---

## 📚 Arquivos Relacionados

- `services/email_precheck_service.py` - Lógica principal de detecção
- `services/email_builder_service.py` - Montagem de emails de NCM
- `services/email_service.py` - Envio de emails
- `services/report_service.py` - Gerenciamento de relatórios
- `services/context_service.py` - Gerenciamento de contexto
- `services/tool_execution_service.py` - Execução de tools de email
- `services/handlers/confirmation_handler.py` - Confirmação de emails

---

**Próximo passo:** Validar esta análise com casos de uso reais antes de propor melhorias específicas.
