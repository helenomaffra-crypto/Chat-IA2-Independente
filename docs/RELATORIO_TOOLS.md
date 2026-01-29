# Relatório de Tools (Function Calling)

Este documento lista as **tools** disponíveis no mAIke (Chat IA Independente) e suas **descrições** (as mesmas usadas no *function calling*).

- **Fonte da verdade**: `services/tool_definitions.py`
- **Geração**: via `get_available_tools(compact=True)` (descrições “compactas”)

Total de tools: **115**

## obter

- **obter_ajuda**: 📚 GUIA DE AJUDA: Retorna um guia completo com todas as funcionalidades e palavras-chave disponíveis no sistema. _(required: —)_
- **obter_dados_di**: OBTER DADOS DE DI: Obtém informações detalhadas de uma DI (Declaração de Importação) específica. Use quando o usuário perguntar sobre uma DI especí... _(required: numero_di)_
- **obter_dados_duimp**: OBTER DADOS DE DUIMP: Obtém informações detalhadas de uma DUIMP (Declaração Única de Importação) específica. _(required: numero_duimp)_
- **obter_dashboard_hoje**: 📅⚠️⚠️⚠️ PRIORIDADE ABSOLUTA - DASHBOARD DO DIA: Retorna um resumo consolidado de todas as informações relevantes para o dia atual. _(required: —)_
- **obter_detalhes_email**: 📧 Obtém detalhes completos de um email específico (via ID da listagem). _(required: —)_
- **obter_extrato_cct**: PRIORIDADE MÁXIMA - EXTRATO DO CCT: Obtém o extrato completo do CCT (Conhecimento de Carga Aérea), consultando diretamente a API CCTA - API GRATUIT... _(required: —)_
- **obter_extrato_ce**: PRIORIDADE MÁXIMA - EXTRATO DO CE: Obtém o extrato completo do CE, consultando diretamente a API do Integra Comex (Serpro) - API BILHETADA. _(required: —)_
- **obter_extrato_pdf_di**: PRIORIDADE MÁXIMA - EXTRATO PDF DA DI: Obtém o extrato completo da DI, consultando diretamente o Integra Comex (Serpro) - API BILHETADA. _(required: —)_
- **obter_extrato_pdf_duimp**: PRIORIDADE MÁXIMA - EXTRATO PDF DA DUIMP: Obtém o extrato completo da DUIMP, consultando diretamente o Portal Único Siscomex (autenticado). _(required: —)_
- **obter_relatorio_observabilidade**: 📊 Relatório de observabilidade: Gera relatórios sobre uso do sistema (consultas bilhetadas, consultas salvas, regras aprendidas). _(required: —)_
- **obter_resumo_aprendizado**: 📚 Resumo de aprendizado: Mostra o que a mAIke aprendeu em uma sessão específica. Use quando o usuário perguntar 'o que você aprendeu comigo?', 'o q... _(required: —)_
- **obter_valores_ce**: OBTER VALORES DE CE: Obtém valores monetários de um CE específico (frete, seguro, FOB, CIF). Use quando o usuário perguntar sobre valores de um CE ... _(required: numero_ce)_
- **obter_valores_processo**: OBTER VALORES: Obtém valores monetários de um processo específico (frete, seguro, FOB, CIF). Use quando o usuário perguntar sobre valores monetário... _(required: processo_referencia)_

## listar

- **listar_bank_slip_payments_santander**: 📋 LISTAR PAGAMENTOS DE BOLETO SANTANDER - Use quando o usuário pedir para listar pagamentos de boleto, ver histórico de boletos, conciliar boletos. Exemplos: 'listar boletos', 'histórico de boletos', 'todos os boletos pagos'. _(required: —)_
- **listar_barcode_payments_santander**: 📋 LISTAR PAGAMENTOS POR CÓDIGO DE BARRAS SANTANDER - Use para listar pagamentos por código de barras realizados. _(required: —)_
- **listar_categorias_disponiveis**: Lista todas as categorias de processos disponíveis no sistema. Use quando o usuário perguntar 'quais categorias temos?', _(required: —)_
- **listar_consultas_aprovadas_nao_executadas**: Lista consultas bilhetadas que foram aprovadas mas ainda não foram executadas. Use quando o usuário perguntar sobre consultas aprovadas que estão a... _(required: —)_
- **listar_consultas_bilhetadas_pendentes**: Lista consultas bilhetadas pendentes de aprovação. _(required: —)_
- **listar_contas_santander**: 🏦 Lista contas disponíveis no Santander (Open Banking). _(required: —)_
- **listar_lotes_bb**: 📋 Lista lotes de pagamentos do Banco do Brasil. _(required: —)_
- **listar_pix_payments_santander**: 📋 LISTAR PAGAMENTOS PIX SANTANDER - Use para listar PIXs realizados, ver histórico de PIX, conciliar PIX. Exemplos: 'listar pix', 'histórico de pix', 'todos os pix'. _(required: —)_
- **listar_processos**: ATENÇÃO: Use esta função APENAS quando o usuário pedir uma lista GERAL de processos SEM mencionar uma categoria específica. _(required: —)_
- **listar_processos_com_duimp**: Lista todos os processos que têm DUIMP registrada. Use quando o usuário perguntar 'quais processos têm duimp registrada?', _(required: —)_
- **listar_processos_com_pendencias**: USE ESTA FUNÇÃO quando o usuário perguntar sobre processos com PENDÊNCIAS (frete não pago, AFRMM não pago). _(required: —)_
- **listar_processos_com_situacao_ce**: SEM CUSTO (CACHE APENAS): Lista processos com situação dos CEs (Conhecimentos de Embarque) usando apenas cache local, _(required: —)_
- **listar_processos_em_dta**: 🚚⚠️⚠️⚠️ PRIORIDADE - PROCESSOS EM DTA: Lista processos que estão em DTA (Declaração de Trânsito Aduaneiro). _(required: —)_
- **listar_processos_liberados_registro**: PRIORIDADE ABSOLUTA - PROCESSOS QUE CHEGARAM SEM DESPACHO: Lista processos que chegaram (data de chegada/destino <= hoje) e NÃO têm registro de DI ... _(required: —)_
- **listar_processos_por_categoria**: Lista todos os processos de uma categoria específica (ex: ALH, VDM, MSS, MV5). Use para perguntas genéricas como: 'como estão os processos ALH?', '... _(required: categoria)_
- **listar_processos_por_eta**: CRÍTICO - USE APENAS COM PERÍODO ESPECÍFICO: Use esta função SOMENTE quando o usuário mencionar um período específico (hoje, amanhã, _(required: —)_
- **listar_processos_por_navio**: 🚢⚠️⚠️⚠️ PRIORIDADE MÁXIMA - BUSCAR PROCESSOS POR NAVIO: Lista processos filtrados por nome do navio. Use ESTA função quando o usuário perguntar sob... _(required: nome_navio)_
- **listar_processos_por_situacao**: Lista processos de uma categoria específica FILTRADOS por situação (desembaraçados, registrados, entregues). _(required: categoria, situacao)_
- **listar_processos_registrados_hoje**: Lista processos que tiveram DI ou DUIMP registrada HOJE (data de vinculação = hoje). Use quando o usuário perguntar 'o que registramos hoje?', 'qua... _(required: —)_
- **listar_tax_by_fields_payments_santander**: 📋 LISTAR PAGAMENTOS DE IMPOSTOS POR CAMPOS SANTANDER - Use para listar pagamentos de impostos (GARE, DARF, GPS) realizados. _(required: —)_
- **listar_teds_santander**: 📋 Lista TEDs do Santander (útil para conciliação). _(required: —)_
- **listar_todos_processos_por_situacao**: ATENÇÃO: Lista TODOS os processos (de TODAS as categorias) filtrados por situação, BLOQUEIO ou pendências. ⚠️⚠️⚠️ USE APENAS quando o usuário pergu... _(required: —)_
- **listar_vehicle_tax_payments_santander**: 📋 LISTAR PAGAMENTOS DE IPVA SANTANDER - Use para listar pagamentos de IPVA realizados. _(required: —)_
- **listar_workspaces_santander**: 🏦 Lista workspaces do Santander (necessário para pagamentos). _(required: —)_

## consultar

- **consultar_bank_slip_payment_santander**: 🔍 CONSULTAR PAGAMENTO DE BOLETO SANTANDER - Use quando o usuário pedir para ver status de pagamento de boleto, consultar boleto. Exemplos: 'consultar boleto X', 'status do pagamento de boleto', 'ver boleto'. _(required: payment_id)_
- **consultar_barcode_payment_santander**: 🔍 CONSULTAR PAGAMENTO POR CÓDIGO DE BARRAS SANTANDER - Use para ver status de pagamento por código de barras. _(required: payment_id)_
- **consultar_cct**: API GRATUITA: Consulta um CCT (Conhecimento de Carga Aérea). _(required: —)_
- **consultar_ce_maritimo**: API BILHETADA: Consulta um CE (Conhecimento de Embarque) marítimo. ⚠️ DECISÃO INTELIGENTE: Esta função AUTOMATICAMENTE consulta a API pública (grat... _(required: —)_
- **consultar_contexto_sessao**: 🔍 Retorna o contexto real salvo na sessão (sem inferir detalhes). _(required: —)_
- **consultar_debitos_renavam_santander**: 🚗 CONSULTAR DÉBITOS RENAVAM SANTANDER - Use quando o usuário pedir para consultar débitos do Renavam, ver IPVA, consultar multas veiculares. Exemplos: 'consultar débitos renavam', 'ver IPVA do veículo', 'consultar multas'. _(required: —)_
- **consultar_despesas_processo**: PRIORIDADE MÁXIMA - DESPESAS CONCILIADAS: Consulta despesas vinculadas a um processo que foram CONCILIADAS (classificadas e vinculadas a lançamento... _(required: processo_referencia)_
- **consultar_extrato_bb**: 🏦 CONSULTAR EXTRATO BANCO DO BRASIL: consultar/visualizar movimentações do BB (API). **Não usar para email** (para enviar, use `enviar_email_personalizado` ou `enviar_relatorio_email`). _(required: —)_
- **consultar_extrato_santander**: 📋 CONSULTAR EXTRATO SANTANDER: consultar/visualizar extrato e movimentações do Santander. _(required: —)_
- **consultar_lote_bb**: 📋 Consulta status/detalhes de um lote de pagamentos BB. _(required: id_lote)_
- **consultar_movimentacoes_bb_bd**: 📊 MOVIMENTAÇÕES BB (BD/SQL Server): consultar lançamentos já sincronizados no banco (sem chamar API do BB). _(required: —)_
- **consultar_pix_payment_santander**: 🔍 CONSULTAR PAGAMENTO PIX SANTANDER - Use para ver status de PIX, consultar pix. Exemplos: 'consultar pix X', 'status do pix', 'ver pix'. _(required: payment_id)_
- **consultar_processo_consolidado**: CONSULTA COMPLETA: Consulta JSON consolidado completo de um processo, incluindo todos os documentos (CE, CCT, DI, DUIMP), valores, tributos, _(required: processo_referencia)_
- **consultar_saldo_santander**: 💰 CONSULTAR SALDO SANTANDER: consultar saldo disponível/bloqueado da conta Santander. _(required: —)_
- **consultar_status_processo**: Consulta status e informações detalhadas de UM processo específico (formato CATEGORIA.NNNN/AA, ex: VDM.0003/25). _(required: processo_referencia)_
- **consultar_tax_by_fields_payment_santander**: 🔍 CONSULTAR PAGAMENTO DE IMPOSTO POR CAMPOS SANTANDER - Use para ver status de pagamento de imposto (GARE, DARF, GPS). _(required: payment_id)_
- **consultar_ted_santander**: 🔍 Consulta status de TED no Santander. _(required: transfer_id)_
- **consultar_vehicle_tax_payment_santander**: 🔍 CONSULTAR PAGAMENTO DE IPVA SANTANDER - Use para ver status de pagamento de IPVA. _(required: payment_id)_

## buscar

- **buscar_consulta_personalizada**: Busca uma consulta salva baseada no texto do pedido do usuário. Use quando o usuário pedir para 'rodar aquele relatório' ou mencionar um relatório salvo anteriormente. _(required: texto_pedido_usuario)_
- **buscar_e_importar_legislacao**: 🚀 [LEGADO] Busca e importa uma legislação automaticamente SEM preview. Use apenas se o usuário pedir explicitamente para 'buscar e gravar direto' ou 'importar sem perguntar'. Para fluxo normal, prefira usar importar_legislacao_preview primeiro. _(required: tipo_ato, numero, ano)_
- **buscar_em_todas_legislacoes**: 🔍 Busca por palavra-chave em TODAS as legislações no SQLite (match textual). _(required: termos)_
- **buscar_legislacao**: Busca ato normativo específico no banco (IN/Lei/Decreto etc.). _(required: tipo_ato, numero)_
- **buscar_legislacao_responses**: 🔍 Busca de legislação com RAG (Responses API) para perguntas conceituais. _(required: pergunta)_
- **buscar_ncms_por_descricao**: Busca NCMs (Nomenclatura Comum do Mercosul) por descrição do produto. Use esta função quando o usuário perguntar sobre NCMs de um produto, _(required: termo)_
- **buscar_nota_explicativa_nesh**: 📚 Busca Notas Explicativas NESH (Nomenclatura Estatística SH) da Receita Federal do Brasil. Use esta função quando o usuário perguntar sobre regras... _(required: —)_
- **buscar_relatorio_por_id**: 🔍 Busca relatório salvo pelo `relatorio_id` (rel_YYYYMMDD_HHMMSS). _(required: relatorio_id)_
- **buscar_secao_relatorio_salvo**: 📊 Busca seção específica de relatório salvo OU filtra relatório por categoria (reutiliza relatório da sessão). _(required: —)_
- **buscar_trechos_legislacao**: 🔍 Busca trechos/artigos dentro de uma legislação (por termos ou número de artigo). _(required: tipo_ato, numero, termos)_

## gerar

- **gerar_pdf_extrato_bb**: 📄 Gera PDF do extrato do Banco do Brasil (formato contábil). _(required: —)_
- **gerar_pdf_extrato_santander**: 📄 Gera PDF do extrato do Santander (formato contábil). _(required: —)_
- **gerar_relatorio_averbacoes**: 📊 Gera relatório de averbações de seguro em formato Excel. Use quando: usuário perguntar 'averbacao [categoria] [mês]', _(required: —)_
- **gerar_relatorio_importacoes_fob**: 📊 Gera relatório de importações normalizado por FOB (Free On Board). Use quando: usuário perguntar 'quanto foi importado em [mês]?', _(required: —)_
- **gerar_resumo_reuniao**: 📊 MODO REUNIÃO: Gera um resumo executivo completo para reunião com cliente/categoria. Use quando o usuário pedir: 'prepara resumo para reunião do c... _(required: —)_

## verificar

- **verificar_atualizacao_ce**: VERIFICAÇÃO INTELIGENTE (API PÚBLICA GRATUITA): Verifica se um CE precisa ser atualizado consultando a API pública gratuita antes de decidir se pre... _(required: numero_ce)_
- **verificar_duimp_registrada**: CONSULTA: Verifica se há uma DUIMP registrada para um processo específico. Use SEMPRE quando o usuário PERGUNTAR sobre DUIMP de UM processo específ... _(required: processo_referencia)_
- **verificar_fontes_dados**: Verifica quais fontes de dados estão disponíveis (SQLite, SQL Server, APIs). Use quando o usuário perguntar sobre disponibilidade de dados, conexão, ou quando uma consulta falhar por falta de acesso. Retorna status de cada fonte e informa se está offline/online. _(required: —)_

## executar

- **executar_consulta_analitica**: Executa uma consulta SQL analítica de forma segura (somente leitura). Use quando o usuário pedir análises, rankings, agregações ou relatórios que precisem de SQL. A query será validada e executada apenas se for SELECT seguro. LIMIT será aplicado automaticamente se não especificado. _(required: sql)_
- **executar_consultas_aprovadas**: 🚀 Executa consultas bilhetadas que foram aprovadas mas ainda não foram executadas. Use quando o usuário pedir para executar consultas aprovadas, pr... _(required: —)_

## salvar

- **salvar_consulta_personalizada**: Salva uma consulta SQL ajustada como relatório reutilizável. Use quando o usuário pedir para salvar uma consulta que funcionou bem. Exemplo: 'salva essa consulta como Atrasos críticos por cliente'. _(required: nome_exibicao, slug, descricao, sql)_
- **salvar_regra_aprendida**: Salva regra aprendida (ex.: mapeamento cliente→categoria, regra de negócio, preferência). _(required: tipo_regra, contexto, nome_regra, descricao)_

## criar

- **criar_duimp**: PRIORIDADE MÁXIMA - CRIAR DUIMP: Cria uma DUIMP para um processo no Portal Único Siscomex. Use QUANDO O USUÁRIO PEDIR EXPLICITAMENTE para 'registra... _(required: processo_referencia)_
- **criar_workspace_santander**: 🔧 Cria workspace no Santander para habilitar pagamentos. _(required: agencia, conta)_

## vincular

- **vincular_processo_cct**: PRIORIDADE ALTA: Vincula um processo de importação a um CCT (Conhecimento de Carga Aérea) que já foi consultado mas não tem processo vinculado. Use... _(required: numero_cct, processo_referencia)_
- **vincular_processo_di**: Vincula um processo de importação a uma DI (Declaração de Importação) que já foi consultada mas não tem processo vinculado. _(required: numero_di, processo_referencia)_
- **vincular_processo_duimp**: USE ESTA FUNÇÃO quando o usuário pedir para incluir/vincular um número de DUIMP ou DI a um processo. Aceita comandos naturais como: 'inclua o numer... _(required: numero_duimp, processo_referencia)_

## desvincular

- **desvincular_documento_processo**: PRIORIDADE MÁXIMA - DESVINCULAR: Remove/desvincula um documento (CE, CCT, DI, DUIMP, RODOVIARIO) de um processo. _(required: processo_referencia, tipo_documento, numero_documento)_

## iniciar

- **iniciar_bank_slip_payment_santander**: 💳 Inicia pagamento de boleto no Santander (gera `payment_id` e fica pendente para efetivação). _(required: payment_id, code, payment_date)_
- **iniciar_barcode_payment_santander**: 💳 Inicia pagamento por código de barras no Santander (depois efetivar). _(required: payment_id, code, payment_date)_
- **iniciar_pagamento_lote_bb**: 💰 Inicia pagamento em lote no Banco do Brasil (BOLETO/PIX/TED). _(required: agencia, conta, pagamentos)_
- **iniciar_pix_payment_santander**: 💸 Inicia PIX no Santander (depois precisa efetivar). _(required: payment_id, payment_value)_
- **iniciar_tax_by_fields_payment_santander**: 📄 Inicia pagamento de imposto por campos (GARE/DARF/GPS) no Santander. _(required: payment_id, tax_type, payment_date)_
- **iniciar_ted_santander**: 💸 Inicia TED no Santander (retorna `transfer_id`; depois precisa efetivar). _(required: banco_destino, agencia_destino, conta_destino, valor, nome_destinatario, cpf_cnpj_destinatario)_
- **iniciar_vehicle_tax_payment_santander**: 🚗 Inicia pagamento de IPVA via Santander (depois efetivar). _(required: payment_id, renavam, tax_type, exercise_year, state_abbreviation, doc_type, document_number)_

## efetivar

- **efetivar_bank_slip_payment_santander**: ✅ Efetiva/autoriza pagamento de boleto iniciado no Santander. _(required: payment_id, payment_value)_
- **efetivar_barcode_payment_santander**: ✅ EFETIVAR PAGAMENTO POR CÓDIGO DE BARRAS SANTANDER - Use para confirmar pagamento por código de barras iniciado. Exemplos: 'efetivar código de barras', 'confirmar pagamento código X'. _(required: payment_id, payment_value)_
- **efetivar_pix_payment_santander**: ✅ EFETIVAR PAGAMENTO PIX SANTANDER - Use para confirmar e efetivar PIX iniciado. Exemplos: 'efetivar pix', 'confirmar pix X', 'autorizar pix'. _(required: payment_id, payment_value)_
- **efetivar_tax_by_fields_payment_santander**: ✅ EFETIVAR PAGAMENTO DE IMPOSTO POR CAMPOS SANTANDER - Use para confirmar pagamento de imposto (GARE, DARF, GPS) iniciado. _(required: payment_id)_
- **efetivar_ted_santander**: ✅ Efetiva TED iniciada (confirma/autoriza) via `transfer_id`. _(required: transfer_id, agencia_origem, conta_origem)_
- **efetivar_vehicle_tax_payment_santander**: ✅ EFETIVAR PAGAMENTO DE IPVA SANTANDER - Use para confirmar pagamento de IPVA iniciado. _(required: payment_id)_

## processar

- **processar_boleto_upload**: 📄 Processa PDF de boleto e inicia pagamento via Santander (prévia/pendente de efetivação). _(required: file_path)_

## enviar

- **enviar_email**: 📧 Envia email simples (sempre com preview + confirmação). _(required: destinatario, assunto, corpo)_
- **enviar_email_personalizado**: 📧 Envia email personalizado (preview + confirmação; não é relatório com REPORT_META). _(required: destinatarios, assunto, conteudo)_
- **enviar_relatorio_email**: 📊 Envia relatório (quando há REPORT_META/relatório salvo). Preview + confirmação; usa report_id/last_visible/active. _(required: —)_

## melhorar

- **melhorar_email_draft**: 📧 Melhora/refina um email que está em preview (opcional). _(required: —)_

## aprovar

- **aprovar_consultas_bilhetadas**: Aprova consultas bilhetadas pendentes para execução. Use quando o usuário pedir para aprovar consultas, autorizar consultas, _(required: —)_

## rejeitar

- **rejeitar_consultas_bilhetadas**: Rejeita consultas bilhetadas pendentes. Use quando o usuário pedir para rejeitar consultas, negar aprovação, ou cancelar consultas. _(required: —)_

## adicionar

- **adicionar_categoria_processo**: USE APENAS quando o usuário CONFIRMAR explicitamente que uma categoria é válida. Adiciona uma nova categoria de processo ao sistema. _(required: categoria)_

## fechar

- **fechar_dia**: Retorna resumo de todas as movimentações do dia atual (fechamento do dia). ✅ AJUSTE (12/01/2026): 'fechamento do dia' e 'resumo do dia' são a MESMA... _(required: —)_

## confirmar

- **confirmar_importacao_legislacao**: 💾 Confirma e salva legislação mostrada em preview. _(required: tipo_ato, numero, ano)_

## outros

- **baixar_nomenclatura_ncm**: 📥 Baixa e atualiza a tabela de NCMs (Nomenclatura Comum do Mercosul) do Portal Único Siscomex. Use esta função quando o usuário pedir para 'baixar ... _(required: —)_
- **calcular_impostos_ncm**: 💰 Calcula impostos de importação (local, rápido). Para % simples use `calcular_percentual`. _(required: —)_
- **calcular_percentual**: 📊 Cálculo simples de percentual (sem PTAX/sem impostos). _(required: valor, percentual)_
- **detalhar_ncm**: Detalha a hierarquia completa de um NCM e lista todos os NCMs de 8 dígitos que pertencem ao grupo. Use esta função quando o usuário pedir para 'det... _(required: ncm)_
- **importar_legislacao_preview**: 🔍 Busca legislação e mostra preview (não salva; depois usar `confirmar_importacao_legislacao`). _(required: tipo_ato, numero, ano)_
- **ler_emails**: 📥 Lê emails da caixa de entrada (Microsoft Graph). _(required: —)_
- **responder_email**: 📧 Responde um email específico via Microsoft Graph. _(required: message_id, resposta)_
- **sugerir_ncm_com_ia**: 🤖 Sugere NCM usando IA baseado em descrição do produto com RAG (Retrieval Augmented Generation). Use esta função quando o usuário perguntar sobre N... _(required: descricao)_
- **ver_status_consultas_bilhetadas**: 📊 Verifica o status de consultas bilhetadas (individual ou estatísticas gerais). Use quando o usuário perguntar sobre o status de uma consulta espe... _(required: —)_

---

## Observação importante

As descrições acima são **compactadas** (para caber no prompt e guiar o modelo).  
Para ver o texto completo e todos os parâmetros de cada tool, consulte `services/tool_definitions.py`.

