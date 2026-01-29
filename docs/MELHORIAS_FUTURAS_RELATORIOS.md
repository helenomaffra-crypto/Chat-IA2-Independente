# 🚀 Melhorias Futuras - Sistema de Relatórios

**Data de Criação:** 10/01/2026  
**Status:** 📋 **BACKLOG** - Melhorias sugeridas pelo GPT-4o durante análise do sistema

---

## 📝 Contexto

Durante o processo de refatoração do sistema de relatórios, identificamos várias melhorias que podem ser implementadas para tornar o sistema ainda mais robusto e flexível. Este documento registra essas melhorias para implementação futura.

---

## 🎯 Melhorias Prioritárias

### 1. Sistema de Contexto Mais Robusto

**Problema Atual:**
- Contexto atual é identificado implicitamente via regex no texto
- Não há marcação explícita de "contexto_ativo" e "id_contexto"

**O que implementar:**
- Marcar explicitamente no banco/contexto:
  - `contexto_ativo`: tipo do contexto (ex: "dashboard_dia", "extrato_bancario", "processo_unico")
  - `id_contexto`: ID único do contexto (ex: "dashboard_2026-01-10_geral", "extrato_santander_BND.0083/25")
- Quando usuário pedir "nesse contexto monte esse relatorio de uma forma diferente":
  - Buscar pelo `contexto_ativo` e `id_contexto` explícitos
  - Não depender de regex no texto da última resposta

**Benefícios:**
- Elimina ambiguidade sobre qual contexto está ativo
- Permite múltiplos contextos simultâneos (ex: dashboard + extrato)
- Facilita manipulação de relatórios salvos

**Arquivos a modificar:**
- `services/context_service.py` - Adicionar campos `contexto_ativo` e `id_contexto`
- `services/report_service.py` - Salvar contexto explícito ao gerar relatório
- `services/precheck_service.py` - Buscar contexto por ID explícito

---

### 2. Mais Instruções Específicas de Manipulação

**Problema Atual:**
- Detecta apenas algumas instruções básicas ("por cliente", "por criticidade", etc.)
- Não detecta padrões mais complexos como "quadro to-do", "agrupar por prazo", etc.

**O que implementar:**
- Expandir detecção de instruções específicas na mensagem do usuário:
  - ✅ "agrupar por cliente" → agrupar processos por cliente/categoria
  - ✅ "por criticidade" → priorizar processos críticos
  - ✅ "por modal" → agrupar por modal (Marítimo/Aéreo)
  - ✅ "por prazo" / "por data" → organizar por prazo/ETA
  - ⚠️ "mais resumido" → ser conciso mas manter dados
  - ⚠️ "mais detalhado" → incluir todas as informações
  - 🔴 **NOVO:** "quadro to-do" / "kanban" → formatar como quadro kanban (hoje / próximos dias / crítico)
  - 🔴 **NOVO:** "agrupar por prazo" → agrupar por dias_para_destino_final (<= 0 crítico, 1-3 hoje, > 3 próximos dias)
  - 🔴 **NOVO:** "por tipo de pendência" → agrupar pendências por tipo (ICMS, AFRMM, frete, documentação)
  - 🔴 **NOVO:** "por situação" → agrupar processos por situação (chegando, pronto para registro, em análise, etc.)

**Benefícios:**
- Usuário pode solicitar formatos específicos de forma natural
- Sistema responde a mais variações de comandos
- Permite criar visualizações customizadas do mesmo relatório

**Arquivos a modificar:**
- `services/precheck_service.py` - Expandir detecção de instruções (linha ~272)
- `services/agents/processo_agent.py` - Ajustar prompt baseado em instruções detectadas

---

### 3. Snapshot Explícito vs. Recalcular

**Problema Atual:**
- Sistema sempre usa snapshot salvo quando usuário pede para "melhorar"
- Não há opção explícita de escolher entre "usar snapshot" vs. "recalcular dados"

**O que implementar:**
- Adicionar lógica para detectar intenção do usuário:
  - "nesse contexto monte esse relatorio de uma forma diferente" → usar snapshot salvo
  - "roda de novo o que temos pra hoje" / "atualizar" / "recalcular" → recalcular dados em tempo real
- Opcionalmente, adicionar parâmetro explícito:
  - `obter_dashboard_hoje(usar_snapshot=True)` vs. `obter_dashboard_hoje(usar_snapshot=False)`
- No backend, ter:
  - `GET /dashboard_hoje?snapshot=2026-01-10` → usar snapshot de data específica
  - `GET /dashboard_hoje?atualizar=true` → recalcular agora

**Benefícios:**
- Usuário pode escolher entre manipular snapshot ou atualizar dados
- Permite comparar versões diferentes do mesmo relatório
- Flexibilidade para casos de uso diferentes

**Arquivos a modificar:**
- `services/agents/processo_agent.py` - Adicionar parâmetro `usar_snapshot` em `_obter_dashboard_hoje()`
- `services/precheck_service.py` - Detectar se usuário quer snapshot ou recalcular
- `services/report_service.py` - Adicionar método para buscar snapshot por data

---

## 🔧 Implementação Sugerida

### Ordem de Prioridade:

1. **Alta Prioridade:**
   - ✅ Sistema de contexto mais robusto (melhora fundamental)
   - ✅ Mais instruções específicas (melhora UX significativa)

2. **Média Prioridade:**
   - ⚠️ Snapshot explícito vs. recalcular (melhora flexibilidade)

### Checklist de Implementação:

#### Fase 1: Sistema de Contexto Robusto
- [ ] Adicionar campos `contexto_ativo` e `id_contexto` em `context_service.py`
- [ ] Modificar `report_service.py` para salvar contexto explícito
- [ ] Atualizar `precheck_service.py` para buscar por contexto explícito
- [ ] Remover dependência de regex para detecção de contexto
- [ ] Testar com múltiplos contextos simultâneos

#### Fase 2: Mais Instruções Específicas
- [ ] Adicionar detecção de "quadro to-do" / "kanban"
- [ ] Adicionar detecção de "agrupar por prazo"
- [ ] Adicionar detecção de "por tipo de pendência"
- [ ] Adicionar detecção de "por situação"
- [ ] Atualizar prompts para incluir essas instruções
- [ ] Testar cada tipo de instrução

#### Fase 3: Snapshot Explícito
- [ ] Adicionar parâmetro `usar_snapshot` em métodos de relatório
- [ ] Detectar intenção do usuário (snapshot vs. recalcular)
- [ ] Implementar busca de snapshot por data
- [ ] Adicionar logs para diferenciar snapshot vs. live
- [ ] Testar ambos os modos

---

## 📚 Referências

- Sugestões do GPT-4o durante análise do sistema (10/01/2026)
- `docs/PASSO_6_PLANO_IMPLEMENTACAO.md` - Plano principal de implementação
- `services/agents/processo_agent.py` - Implementação atual do RelatorioFormatterService
- `services/precheck_service.py` - Detecção atual de pedidos de melhoria

---

**Última atualização:** 10/01/2026
