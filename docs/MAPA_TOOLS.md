## 🧰 Mapa de Tools (V1) — com critério (2026-01-29)

Este documento existe para você **avaliar rapidamente**:

- **quais tools são “core”** (alto impacto / uso diário / risco alto)
- **quais são “edge”** (baixo uso provável / alto custo de manter / risco de estourar o limite de tools)
- **onde cada tool executa** (Precheck determinístico vs ToolExecutionService vs ToolRouter/Agents)

---

## ⚠️ Ponto crítico: limite de 128 tools (OpenAI)

A OpenAI limita o array `tools` para **no máximo 128**. No projeto, `services/tool_definitions.py` tem um guardrail que:

1) deduplica por `function.name`  
2) **remove “nice-to-have”** se necessário  
3) e por fim **trunca** para 128

**Efeito prático:** tool-calling pode ficar **intermitente** quando uma tool “cai para fora” do array em certas condições.

### Tools que já vimos “saírem” para caber no limite

- **Removidas como nice-to-have** (antes de truncar):  
  - `listar_noticias_siscomex`  
  - `verificar_fontes_dados`
- **Truncadas quando ainda excede 128** (amostra/observado):  
  - `listar_tax_by_fields_payments_santander`  
  - `executar_pagamento_afrmm`

**Mitigação recomendada (padrão do projeto):** comandos críticos devem ter **roteamento determinístico no Precheck** (ex.: “pagar AFRMM”), para não depender da IA “enxergar” a tool.

---

## ✅ Como avaliar “principal” vs “quase não uso”

Use este checklist (ordem de prioridade):

1) **Ação sensível / risco operacional**  
   - pagamentos, DUIMP, email, ações que mudam estado
2) **Uso diário** (operacional)  
   - status de processo, listas por categoria, pendências, extratos
3) **Custo por chamada**  
   - APIs bilhetadas / automações / SQL pesado
4) **Cobertura por rotas determinísticas**  
   - se já existe precheck/policy, a tool pode ser menos exposta ao modelo
5) **Redundância**  
   - “listar + consultar + efetivar” para APIs pouco usadas costuma ser candidato a “edge”

### Dica para medir “uso real” (sem achismo)

Use a tool de observabilidade:

- `obter_relatorio_observabilidade`

(Ela ajuda a identificar **consultas bilhetadas**, regras e padrões pouco usados; quando algo virar recorrente, dá para promover a tool para “core” e mover outras para “edge”.)

---

## 📌 Execução: onde a tool roda

- **Precheck determinístico**: `services/precheck_service.py` (comandos críticos, mais estável)
- **ToolExecutionService (handlers extraídos)**: `services/tool_execution_service.py` (preferível; evita fallback)
- **ToolRouter → Agents**: `services/tool_router.py` + `services/agents/*.py` (domínios)

---

## 📦 Snapshot atual das tools expostas (128) — agrupadas por agent

> Este snapshot foi gerado via `get_available_tools(compact=False)` + `ToolRouter.tool_to_agent`.
> **Importante:** isto mostra as tools **que efetivamente entram no array** (depois de dedupe/remoções/truncagem).

### banco_brasil (6)
`consultar_extrato_bb`, `consultar_lote_bb`, `consultar_movimentacoes_bb_bd`, `gerar_pdf_extrato_bb`, `iniciar_pagamento_lote_bb`, `listar_lotes_bb`

### calculo (2)
`calcular_impostos_ncm`, `calcular_percentual`

### cct (2)
`consultar_cct`, `obter_extrato_cct`

### ce (4)
`consultar_ce_maritimo`, `listar_processos_com_situacao_ce`, `obter_extrato_ce`, `verificar_atualizacao_ce`

### di (4)
`consultar_adicoes_di`, `obter_dados_di`, `obter_extrato_pdf_di`, `vincular_processo_di`

### duimp (5)
`criar_duimp`, `obter_dados_duimp`, `obter_extrato_pdf_duimp`, `verificar_duimp_registrada`, `vincular_processo_duimp`

### legislacao (7)
`buscar_e_importar_legislacao`, `buscar_em_todas_legislacoes`, `buscar_legislacao`, `buscar_legislacao_responses`, `buscar_trechos_legislacao`, `confirmar_importacao_legislacao`, `importar_legislacao_preview`

### processo (31)
`buscar_relatorio_por_id`, `buscar_secao_relatorio_salvo`, `consultar_contexto_sessao`, `consultar_despesas_processo`, `consultar_processo_consolidado`, `consultar_status_processo`, `fechar_dia`, `filtrar_relatorio_fuzzy`, `gerar_relatorio_averbacoes`, `gerar_relatorio_importacoes_fob`, `listar_alertas_recentes`, `listar_dis_por_canal`, `listar_duimps_em_analise`, `listar_eta_alterado`, `listar_pendencias_ativas`, `listar_processos`, `listar_processos_com_pendencias`, `listar_processos_desembaracados_hoje`, `listar_processos_em_dta`, `listar_processos_liberados_registro`, `listar_processos_por_categoria`, `listar_processos_por_eta`, `listar_processos_por_navio`, `listar_processos_por_situacao`, `listar_processos_prontos_registro`, `listar_processos_registrados_hoje`, `listar_processos_registrados_periodo`, `listar_todos_processos_por_situacao`, `obter_dashboard_hoje`, `obter_snapshot_processo`, `sincronizar_processos_ativos_maike`

### santander (31)
`consultar_bank_slip_payment_santander`, `consultar_barcode_payment_santander`, `consultar_debitos_renavam_santander`, `consultar_extrato_santander`, `consultar_pix_payment_santander`, `consultar_saldo_santander`, `consultar_tax_by_fields_payment_santander`, `consultar_ted_santander`, `consultar_vehicle_tax_payment_santander`, `criar_workspace_santander`, `efetivar_bank_slip_payment_santander`, `efetivar_barcode_payment_santander`, `efetivar_pix_payment_santander`, `efetivar_tax_by_fields_payment_santander`, `efetivar_ted_santander`, `efetivar_vehicle_tax_payment_santander`, `gerar_pdf_extrato_santander`, `iniciar_bank_slip_payment_santander`, `iniciar_barcode_payment_santander`, `iniciar_pix_payment_santander`, `iniciar_tax_by_fields_payment_santander`, `iniciar_ted_santander`, `iniciar_vehicle_tax_payment_santander`, `listar_bank_slip_payments_santander`, `listar_barcode_payments_santander`, `listar_contas_santander`, `listar_pix_payments_santander`, `listar_teds_santander`, `listar_vehicle_tax_payments_santander`, `listar_workspaces_santander`, `processar_boleto_upload`

### sistema (36)
`adicionar_categoria_processo`, `aprovar_consultas_bilhetadas`, `baixar_nomenclatura_ncm`, `buscar_consulta_personalizada`, `buscar_ncms_por_descricao`, `buscar_nota_explicativa_nesh`, `consultar_vendas_make`, `consultar_vendas_nf_make`, `curva_abc_vendas`, `desvincular_documento_processo`, `detalhar_ncm`, `enviar_email`, `enviar_email_personalizado`, `enviar_relatorio_email`, `executar_consulta_analitica`, `executar_consultas_aprovadas`, `filtrar_relatorio_vendas`, `gerar_resumo_reuniao`, `inspecionar_schema_nf_make`, `ler_emails`, `listar_categorias_disponiveis`, `listar_consultas_aprovadas_nao_executadas`, `listar_consultas_bilhetadas_pendentes`, `melhorar_email_draft`, `obter_detalhes_email`, `obter_relatorio_observabilidade`, `obter_resumo_aprendizado`, `obter_valores_ce`, `obter_valores_processo`, `rejeitar_consultas_bilhetadas`, `responder_email`, `salvar_consulta_personalizada`, `salvar_regra_aprendida`, `sugerir_ncm_com_ia`, `ver_status_consultas_bilhetadas`, `vincular_processo_cct`

