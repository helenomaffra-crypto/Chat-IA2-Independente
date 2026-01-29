# ✅ Fase 2B: ToolGateService — Fallback por REPORT_META + TTL

**Data:** 14/01/2026  
**Status:** ✅ **IMPLEMENTADO** (escopo pequeno, sem aumentar inferências)

---

## 🎯 Objetivo

Adicionar uma terceira fonte confiável para resolver `report_id` quando a IA não envia o campo:

1. `active_report_id` (por domínio)
2. `last_visible_report_id` (por domínio)
3. **`REPORT_META`** (persistido) ✅ **Fase 2B**

Tudo com as mesmas proteções da Fase 2A:
- **Não sobrescrever valores explícitos**
- **Domínio determinístico**
- **TTL/staleness guard**
- **Validação de existência no banco**

---

## ✅ Regra de ouro (Fase 2B)

`REPORT_META` só é considerado quando:
- a tool está na **allowlist** de relatório
- `report_id` **não veio** nos args
- `active_report_id` e `last_visible_report_id` **não resolveram**
- o meta é **válido**, do **domínio correto** e **não está stale**
- o `report_id` **existe no banco/contexto** (`buscar_relatorio_por_id`)

---

## 🧠 Onde buscamos o REPORT_META (rota segura)

**Fonte usada:** histórico persistido de relatórios (não “texto visível” em memória)

- `services.report_service.obter_report_history(session_id, limite=10)`  
  Retorna lista dos últimos relatórios com `id`, `tipo`, `created_at` extraídos de `[REPORT_META:{...}]` persistido em `ultimo_relatorio.texto_chat`.

**Validação de existência:**
- `services.report_service.buscar_relatorio_por_id(session_id, report_id)`  
  Se não existir, descartamos o candidato.

---

## 🔒 Validações mínimas (não-negociáveis)

Antes de aceitar `REPORT_META`:
- `id` presente e string
- `created_at` parseável (ISO ou formato SQLite) — senão descarta
- **TTL:** idade ≤ `TOOL_GATE_REPORT_MAX_AGE_MIN` (default 60)
- **Domínio:** validado por `tipo` do relatório (e redundante por `tipo_relatorio` real do relatório encontrado)

---

## ⚙️ Configuração

Feature flag:
- `TOOL_GATE_ENABLED` (default: `true`)

TTL do report:
- `TOOL_GATE_REPORT_MAX_AGE_MIN` (default: `60`)

---

## 🧪 Testes adicionados (Fase 2B)

Arquivo: `tests/test_tool_gate_service.py`

Cobertura incluída:
- REPORT_META válido injeta quando active/last_visible não existem
- REPORT_META stale é ignorado e resulta em erro controlado
- REPORT_META com timestamp inválido é ignorado sem quebrar
- REPORT_META com id inexistente no banco é ignorado
- REPORT_META não sobrescreve `report_id` explícito
- Tool fora da allowlist não sofre interferência (já coberto na suíte 2A)

---

## 📍 Arquivos alterados

- `services/tool_gate_service.py` (implementação REPORT_META + TTL + domínio)
- `services/report_service.py` (novo helper `obter_active_report_info`)
- `tests/test_tool_gate_service.py` (novos testes Fase 2B)

