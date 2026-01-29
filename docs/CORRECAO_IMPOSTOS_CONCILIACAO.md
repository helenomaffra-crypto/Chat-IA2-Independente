# Correção: Impostos não vinham na conciliação

**Data:** 26/01/2026  
**Problema:** Na conciliação bancária, ao distribuir impostos de importação, os valores sugeridos da DI/DUIMP vinham todos zerados ("Nenhum imposto encontrado na DI/DUIMP"), mesmo com processo que tem II, PIS, COFINS, Taxa SISCOMEX etc. (ex.: BND.0101/25).

---

## Causa

O endpoint `/api/banco/impostos-processo/<processo_referencia>` buscava pagamentos da DI só em:

1. **`obter_dados_documentos_processo`** → `dis` → `dados_completos.pagamentos` ou `di.pagamentos`
2. **DUIMP** (Kanban / documentos)

Em parte dos fluxos, `obter_dados_documentos_processo` não devolvia `pagamentos` (ex.: cache sem enriquecimento SQL, estrutura diferente). Além disso, só se lia `dados_completos.pagamentos`; não havia fallback para `di.pagamentos`. O chat que mostra "Impostos (pagos / registrados)" usa **processo consolidado** (SQL Server); o endpoint de impostos priorizava `obter_dados`, que usa outra fonte.

---

## Alterações feitas (26/01/2026 – refinamento)

### 1. Normalização do processo

- `processo_ref = (processo_referencia or '').strip().upper()` no início do endpoint.
- Todas as chamadas (IMPOSTO_IMPORTACAO, consolidado, obter_dados, Kanban) usam `processo_ref`.

### 2. Prioridade 1: processo consolidado (SQL Server)

- **Primeiro** chama `buscar_processo_consolidado_sql_server(processo_ref)`.
- Se não encontrar no primário e `should_use_legacy_database(processo_ref)`, tenta Make (`database=get_legacy_database()`).
- Se houver `di` e `di['pagamentos']`, usa esses pagamentos (mesma fonte do status/chat que mostra impostos).

### 3. Loop único para mapear pagamentos → impostos

- O loop que monta `impostos_sugeridos` a partir de `pagamentos` ficou **único** e roda sempre que houver `pagamentos`, seja de `obter_dados_documentos_processo` ou do fallback consolidado.
- Antes, esse loop estava só no ramo “tem pagamentos em dados_docs”; com o fallback, às vezes os pagamentos vinham só do consolidado e o loop não rodava.

---

## Fluxo atual

1. Normalizar `processo_ref` (strip, upper). Buscar impostos já gravados em `IMPOSTO_IMPORTACAO`; se `total > 0`, retornar cedo com `impostos_gravados`.
2. **Prioridade 1:** `buscar_processo_consolidado_sql_server(processo_ref)`. Se não achar, tentar Make quando `should_use_legacy_database`. Se houver `di['pagamentos']`, usar.
3. **Prioridade 2:** `obter_dados_documentos_processo(processo_ref)`. Se ainda não houver `pagamentos`, extrair de `dis` → `dados_completos` ou `di`.
4. Mapear `pagamentos` → `impostos_sugeridos` (II, IPI, PIS, COFINS, ANTIDUMPING, TAXA_UTILIZACAO).
5. DUIMP (Kanban/documentos) como antes.

---

## Como validar

1. Abrir conciliação, lançamento tipo “PAGAMENTO DE SISCOMEX...” etc.
2. Marcar “Confirmar que são impostos de importação”.
3. Informar o processo (ex.: **BND.0101/25**) e clicar em **Buscar**.
4. Conferir se II, PIS, COFINS, Taxa SISCOMEX (e demais) vêm preenchidos com os valores da DI, e se o total bate com o lançamento.

---

## Arquivos modificados

- `app.py`: endpoint `GET /api/banco/impostos-processo/<processo_referencia>` (normalização, prioridade consolidado, fallback legado, obter_dados, loop único, logs).
