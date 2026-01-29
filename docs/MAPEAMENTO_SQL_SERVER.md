# Mapeamento do Banco de Dados SQL Server

**Versão:** 2.1  
**Data:** 13/01/2026  
**Última atualização:** Adicionada tabela HISTORICO_PAGAMENTOS (histórico completo de pagamentos)

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura de Bancos de Dados](#estrutura-de-bancos-de-dados)
3. [Estrutura de Tabelas e Relacionamentos](#estrutura-de-tabelas-e-relacionamentos)
4. [Tabelas do Banco mAIke_assistente](#-tabelas-do-banco-maike_assistente-novo---07012026) ⭐ **NOVO**
5. [Queries de Referência](#queries-de-referência)
6. [Problemas Críticos Resolvidos](#problemas-críticos-resolvidos)
7. [Mapeamento de Campos Críticos](#mapeamento-de-campos-críticos)
8. [Notas Importantes](#notas-importantes)

---

## 🎯 Visão Geral

Este documento descreve a estrutura completa do banco de dados SQL Server usado para armazenar dados de processos de importação, DUIMPs, DIs, CEs, CCTs e informações relacionadas.

**Público-alvo:**
- Desenvolvedores de outras aplicações que precisam acessar dados do SQL Server
- Equipe de manutenção e suporte
- Novos desenvolvedores do projeto

**Principais bancos de dados:**
- `make.dbo` - Processos de importação e transporte
- `duimp.dbo` - DUIMPs (Declaração Única de Importação)
- `Serpro.dbo` - DIs (Declaração de Importação) e CEs (Conhecimento de Embarque)
- `comex.dbo` - Importações (tabela de vínculo)
- `mAIke_assistente.dbo` ⭐ **NOVO (07/01/2026)** - Sistema de sincronização bancária, conciliação e despesas

**⚠️ NOTA IMPORTANTE:** Este documento foi atualizado após **extensa investigação (~7.5 horas de trabalho)** para resolver o problema crítico de busca de DI relacionada a processos. Foram descobertos **dois problemas principais**:
> 
> 1. **Quando `numero_di` está NULL:** Solução envolveu descobrir o vínculo correto através de `Hi_Historico_Di.idImportacao` → `comex.dbo.Importacoes.id` → `make.dbo.PROCESSO_IMPORTACAO.id_importacao`.
> 2. **Formato diferente do `numero_di`:** O campo pode estar como `25/0340890-6` na tabela `PROCESSO_IMPORTACAO` mas como `2503408906` na tabela `Di_Dados_Gerais`, causando falha na busca direta.
> 
> **Problemas originais:** 
> - Processo `ALH.0172/25` não exibia a DI `2526376792` na UI (numero_di NULL)
> - Processos `ALH.0004/25` e `ALH.0005/25` não exibiam DI mesmo com `numero_di` preenchido (formato diferente)
> 
> **Soluções:** 
> - Implementada busca via `id_importacao` usando a query `di_kanban.sql` como referência
> - Normalização do `numero_di` removendo `/` e `-` antes de buscar
> - Fallback para buscar via `id_importacao` mesmo quando `numero_di` está preenchido
> 
> **⭐ NOVAS DESCOBERTAS (Atualização 16/12/2025):**
> - **Pagamentos/Impostos da DI:** Todos os pagamentos/impostos da DI estão disponíveis no SQL Server através das tabelas `Di_Pagamento` e `Di_pagamentos_cod_receitas`. Não é necessário consultar a API Integra Comex (bilhetada) para obter esses dados.
> - **Campos Completos do CE:** ✅ **CONFIRMADO E TESTADO** - Todos os campos do CE necessários para averbação (`paisProcedencia`, `dataEmissao`, `tipo`, `descricaoMercadoria`) estão disponíveis na tabela `Ce_Root_Conhecimento_Embarque` do SQL Server. Não é necessário buscar do cache do CE quando esses dados estão no SQL Server.
> - **Prioridade de Busca:** Cache → SQL Server → API (API é bilhetada, usar por último)
> 
> **⭐ NOVAS DESCOBERTAS (Atualização 19/12/2025):**
> - **CE Relacionado à DI/DUIMP:** O CE relacionado à DI pode ser encontrado em `Di_Transporte.numeroConhecimentoEmbarque` ou via `id_importacao` usando `_buscar_ce_por_id_importacao()`. O mesmo método funciona para DUIMP: passar `id_importacao` para `_buscar_duimp_completo()` e buscar o CE relacionado automaticamente.
> - **Problema do Fallback Sobrescrevendo DUIMP:** A lógica de decisão do fallback não considerava a DUIMP ao decidir se deveria sobrescrever a resposta. Solução: verificar se a resposta já contém DUIMP formatada (`tem_duimp_na_resposta`) e, se sim, **NÃO** usar o fallback para evitar sobrescrever a resposta completa.
> 
> Veja seção "⚠️ Problema Crítico Resolvido" abaixo para todos os detalhes, problemas encontrados e lições aprendidas.

---

## 🗄️ Estrutura de Bancos de Dados

### Bancos Principais

#### 1. `make.dbo` - Processos de Importação
**Descrição:** Banco principal que gerencia processos de importação e rastreamento.

**Tabelas principais:**
- `PROCESSO_IMPORTACAO` - Tabela central de processos
- `TRANSPORTE` - Dados de rastreamento (ShipsGo)

**Uso típico:** Buscar processos por `numero_processo` (ex: "BND.0030/25") e obter dados relacionados.

#### 2. `duimp.dbo` - DUIMPs
**Descrição:** Banco que armazena todas as informações sobre DUIMPs (Declaração Única de Importação).

**Tabelas principais:**
- `duimp` - Tabela raiz de DUIMPs
- `duimp_diagnostico` - Situação e diagnóstico
- `duimp_resultado_analise_risco` - Canal consolidado
- `duimp_pagamentos` - Pagamentos e tributos
- `duimp_tributos_calculados` - Detalhamento de tributos
- `duimp_tributos_mercadoria` - Valores totais da mercadoria

**Uso típico:** Buscar DUIMP por `numero` ou `numero_processo` e obter situação, canal, impostos.

#### 3. `Serpro.dbo` - DIs e CEs
**Descrição:** Banco que armazena dados de DIs (Declaração de Importação) e CEs (Conhecimento de Embarque) sincronizados da API Integra Comex.

**Tabelas principais:**
- `Hi_Historico_Di` - Histórico de DIs (contém vínculo com `id_importacao`)
- `Di_Root_Declaracao_Importacao` - Raiz da DI (contém `dadosDiId` para buscar pagamentos, frete, seguro)
- `Di_Dados_Gerais` - Dados gerais da DI
- `Di_Pagamento` - Pagamentos/impostos da DI
- `Di_Frete` - Dados de frete da DI
- `Di_Seguro` - Dados de seguro da DI
- `Ce_Root_Conhecimento_Embarque` - Dados completos do CE

**Uso típico:** Buscar DI por `numeroDi` ou via `id_importacao` quando `numero_di` está NULL no processo.

#### 4. `comex.dbo` - Importações
**Descrição:** Tabela de vínculo entre processos e DIs/CEs.

**Tabelas principais:**
- `Importacoes` - Tabela de vínculo (campo `id` liga processos a DIs)

**Uso típico:** Usar `id` para vincular `PROCESSO_IMPORTACAO.id_importacao` com `Hi_Historico_Di.idImportacao`.

#### 5. `mAIke_assistente.dbo` ⭐ **NOVO (07/01/2026)** - Sistema Bancário e Conciliação
**Descrição:** Banco que armazena dados de sincronização bancária, conciliação de lançamentos, catálogo de despesas e impostos de importação.

**Tabelas principais:**
- `MOVIMENTACAO_BANCARIA` - Lançamentos bancários sincronizados (BB e Santander)
- `TIPO_DESPESA` - Catálogo de tipos de despesa (23 tipos pré-cadastrados)
- `LANCAMENTO_TIPO_DESPESA` - Relacionamento N:N (lançamento ↔ tipo despesa ↔ processo)
- `IMPOSTO_IMPORTACAO` ⭐ **NOVO (08/01/2026)** - Impostos de importação distribuídos por lançamento
- `VALOR_MERCADORIA` ⭐ **NOVO (08/01/2026)** - Valores de mercadoria (VMLE, VMLD, FOB, CIF)
- `HISTORICO_PAGAMENTOS` ⭐ **NOVO (13/01/2026)** - Histórico completo de pagamentos (BOLETO, PIX, TED, BARCODE)
- `PLANO_CONTAS` - Plano de contas contábil (preparada para futuro)
- `MOVIMENTACAO_BANCARIA_PROCESSO` - Vínculo entre lançamentos e processos

**Uso típico:** Sincronização de extratos, conciliação bancária, classificação de despesas e distribuição de impostos.

---

## 🔗 Como Outras Aplicações Devem se Conectar

### 1. String de Conexão
```python
# Exemplo de string de conexão (ajustar conforme ambiente)
connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=seu_servidor;DATABASE=make;UID=usuario;PWD=senha"
```

### 2. Prioridade de Busca de Dados
**⚠️ CRÍTICO:** Sempre seguir esta ordem para evitar custos desnecessários com APIs bilhetadas:

1. **Cache local (SQLite)** - Mais rápido, sem custo
2. **SQL Server** - Dados atualizados pelo Kanban, sem custo
3. **API Externa (Integra Comex)** - Bilhetada, usar apenas como último recurso

### 3. Padrões de Nomenclatura
- **Tabelas:** PascalCase (ex: `PROCESSO_IMPORTACAO`, `Di_Dados_Gerais`)
- **Campos:** camelCase (ex: `numero_processo`, `id_importacao`)
- **Bancos:** lowercase (ex: `make.dbo`, `duimp.dbo`)

### 4. Boas Práticas
- ✅ Sempre usar `WITH (NOLOCK)` em queries de leitura para evitar locks
- ✅ Usar `LEFT JOIN` para não perder dados quando relacionamentos são opcionais
- ✅ Normalizar `numero_di` removendo `/` e `-` antes de buscar
- ✅ Sempre ordenar por data mais recente primeiro (`ORDER BY ... DESC`)
- ✅ Usar `TOP 1` quando buscar apenas o registro mais recente

### 5. Exemplo de Query Básica
```sql
-- Buscar processo e DI relacionada
SELECT 
    pi.numero_processo,
    pi.numero_di,
    ddg.numeroDi,
    ddg.situacaoDi,
    ddg.canalSelecaoParametrizada
FROM make.dbo.PROCESSO_IMPORTACAO pi WITH (NOLOCK)
LEFT JOIN comex.dbo.Importacoes i WITH (NOLOCK)
    ON i.id = pi.id_importacao
LEFT JOIN Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
    ON diH.idImportacao = i.id
LEFT JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
    ON diH.diId = diRoot.dadosDiId
LEFT JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
WHERE pi.numero_processo = 'BND.0030/25'
ORDER BY ddg.dataHoraSituacaoDi DESC
```

---

## 📊 Estrutura de Tabelas e Relacionamentos

### 1. PROCESSO_IMPORTACAO (make.dbo)
**Tabela principal de processos de importação**

**Campos principais:**
- `id_processo_importacao` (PK)
- `id_importacao` (FK → comex.dbo.Importacoes)
- `numero_processo` (ex: "VDM.0004/25")
- `numero_ce`
- `numero_di`
- `numero_duimp`

**Relacionamentos:**
- `id_importacao` → `comex.dbo.Importacoes.id`
- `id_processo_importacao` → `TRANSPORTE.id_processo_importacao`
- `id_importacao` → `Serpro.dbo.Hi_Historico_Di.idImportacao` ⭐ **VÍNCULO COM DI** (quando `numero_di` está NULL)

---

### 2. DUIMP (duimp.dbo.duimp)
**Tabela principal de DUIMPs**

**Campos principais:**
- `duimp_id` (PK)
- `numero` (ex: "25BR00002369283")
- `versao`
- `numero_processo` (FK → PROCESSO_IMPORTACAO.numero_processo)
- `id_processo_importacao` (FK → PROCESSO_IMPORTACAO.id_processo_importacao)
- `data_ultimo_evento`
- `ultima_situacao`
- `ultimo_evento`

**Relacionamentos:**
- `duimp_id` → `duimp_diagnostico.duimp_id`
- `duimp_id` → `duimp_situacao.duimp_id`
- `duimp_id` → `duimp_pagamentos.duimp_id`
- `duimp_id` → `duimp_tributos_calculados.duimp_id` ⭐ **NOVO**
- `duimp_id` → `duimp_tributos_mercadoria.duimp_id` ⭐ **NOVO**
- `duimp_id` → `duimp_resultado_analise_risco.duimp_id`
- `duimp_id` → `duimp_situacao_conferencia_aduaneira.duimp_id`
- `duimp_id` → `duimp_resultado_rfb.duimp_id`

---

### 3. DUIMP_DIAGNOSTICO (duimp.dbo.duimp_diagnostico)
**Diagnóstico e situação da DUIMP**

**Campos principais:**
- `duimp_id` (FK)
- `situacao_duimp` ⭐ **CAMPO PRINCIPAL DE SITUAÇÃO**
- `situacao`
- `data_geracao`

**Uso:** Buscar situação atual da DUIMP

---

### 4. DUIMP_SITUACAO (duimp.dbo.duimp_situacao)
**Situação agregada da DUIMP**

**Campos principais:**
- `duimp_id` (FK)
- `situacao_duimp` (situação agregada)
- `situacao_analise_retificacao`
- `situacao_licenciamento`
- `controle_carga` (ex: "ATRACADA")
- `data_registro`

**Uso:** Situação agregada e controle de carga

---

### 5. DUIMP_RESULTADO_ANALISE_RISCO (duimp.dbo.duimp_resultado_analise_risco)
**Resultado da análise de risco e canal**

**Campos principais:**
- `duimp_id` (FK)
- `canal_consolidado` ⭐ **CAMPO PRINCIPAL DE CANAL** (ex: "VERDE", "VERMELHO", "AMARELO")

**Uso:** Buscar canal consolidado da DUIMP

---

### 6. DUIMP_PAGAMENTOS (duimp.dbo.duimp_pagamentos)
**Pagamentos e tributos da DUIMP**

**Campos principais:**
- `duimp_id` (FK)
- `data_pagamento`
- `tributo_tipo` (ex: "II", "IPI", "PIS", "COFINS", "TAXA_UTILIZACAO")
- `valor`

**Uso:** Buscar valores de impostos pagos

---

### 6.1. DUIMP_TRIBUTOS_CALCULADOS (duimp.dbo.duimp_tributos_calculados) ⭐ **NOVO**
**Tributos calculados com detalhamento completo**

**Campos principais:**
- `duimp_id` (FK)
- `tipo` (ex: "II", "IPI", "PIS", "COFINS", "TAXA_UTILIZACAO")
- `valor_calculado` (valor calculado do tributo)
- `valor_devido` (valor devido)
- `valor_a_recolher` (valor a recolher)
- `valor_recolhido` (valor já recolhido)
- `valor_suspenso` (valor suspenso)
- `valor_a_reduzir` (valor a reduzir)

**Uso:** Buscar detalhamento completo dos tributos (mais completo que `duimp_pagamentos`)

**Nota:** Pode ter múltiplos registros por `duimp_id` (um para cada tipo de tributo)

---

### 6.2. DUIMP_TRIBUTOS_MERCADORIA (duimp.dbo.duimp_tributos_mercadoria) ⭐ **NOVO**
**Valores totais da mercadoria**

**Campos principais:**
- `duimp_id` (FK)
- `valor_total_local_embarque_brl` (valor total em BRL)
- `valor_total_local_embarque_usd` (valor total em USD)

**Uso:** Buscar valores totais de embarque da mercadoria

---

### 7. DUIMP_SITUACAO_CONFERENCIA_ADUANEIRA (duimp.dbo.duimp_situacao_conferencia_aduaneira)
**Conferência aduaneira**

**Campos principais:**
- `duimp_id` (FK)
- `situacao` (ex: "CONCLUIDA_AUTOMATICAMENTE")
- `indicador_autorizacao_entrega`
- `indicador_desembaraco_decisao_judicial`

---

### 8. DUIMP_RESULTADO_RFB (duimp.dbo.duimp_resultado_rfb)
**Resultado da RFB**

**Campos principais:**
- `duimp_id` (FK)
- `orgao` (ex: "RFB")
- `resultado` (ex: "DESEMBARACO_AUTORIZADO")

---

### 9. TRANSPORTE (make.dbo.TRANSPORTE)
**Dados de transporte e rastreamento (ShipsGo)**

**Campos principais:**
- `id_processo_importacao` (FK)
- `id_externo_shipsgo`
- `atual_data_evento`
- `atual_evento`
- `atual_nome` (porto atual)
- `atual_codigo` (código do porto)
- `destino_data_chegada` (ETA)
- `destino_nome` (porto final)
- `evento_status`
- `status`
- `quantidade_conteineres`
- `navio` (nome do navio)
- `numero_container`
- `numero_booking`
- `numero_awb`
- `id_movimento` (sequência do movimento)

**Uso:** Dados de rastreamento e ETA

---

### 10. CE (Serpro.dbo)
**Conhecimento de Embarque**

**Tabelas principais:**
- `Hi_Historico_Ce` (histórico)
- `Ce_Root_Conhecimento_Embarque` (dados principais) ⭐ **CONTÉM TODOS OS CAMPOS DO CE NECESSÁRIOS PARA AVERBAÇÃO**
- `Ce_Pendencia_Frete` (pendências de frete)

**Campos básicos (sempre disponíveis):**
- `numero` (número do CE)
- `situacaoCarga`
- `dataDestinoFinal`
- `dataArmazenamentoCarga`
- `valorFreteTotal`
- `pendenciaAFRMM`
- `indicadorPendenciaFrete`
- `portoDestino`
- `portoOrigem`
- `portoAtracacaoAtual`
- `rootConsultaEmbarqueId` (FK para outras tabelas)
- `updatedAt` (data de atualização)

**✅ CAMPOS CONFIRMADOS NO SQL SERVER (TESTADOS):**
Os seguintes campos **EXISTEM** na tabela `Ce_Root_Conhecimento_Embarque` e foram testados e confirmados:
- `paisProcedencia` ⭐ - País de Procedência (código ISO 2 letras, ex: "CN" para China)
  - **Mapeamento:** Usar tabela `PAISES` para converter código em nome completo (ex: "CN" → "CHINA")
  - **Exemplo:** `"CN"` → `"CHINA"`
- `dataEmissao` ⭐ - Data de Emissão do CE (formato ISO: "2025-04-22T00:00:00")
  - **Formatação:** Converter para formato legível "YYYY-MM-DD" antes de exibir
  - **Exemplo:** `"2025-04-22T00:00:00"` → `"2025-04-22"`
- `tipo` ⭐ - Tipo do CE (ex: "HBL", "MBL")
  - **Exemplo:** `"HBL"` (House Bill of Lading)
- `descricaoMercadoria` ⭐ - Descrição da Mercadoria (texto completo)
  - **Exemplo:** `"ARTIFICIAL STONE SLABNCM:6810WOODEN PACKAGE: TREATED AND CERTIFIED..."`

**⚠️ Campos que NÃO existem na tabela:**
- `dataEmbarque` - Não existe (usar `dataEmissao` se disponível)
- `localEmbarque` - Não existe (usar `portoOrigem` se disponível)

**Ordem de busca recomendada:**
1. **SQL Server** (`Ce_Root_Conhecimento_Embarque`) → **TODOS os campos necessários para averbação estão aqui:**
   - Campos básicos: `portoOrigem`, `portoDestino`, `situacaoCarga`, etc.
   - Campos confirmados: `paisProcedencia`, `dataEmissao`, `tipo`, `descricaoMercadoria`
2. **Cache do CE (SQLite)** → apenas como fallback se algum campo não estiver no SQL Server
3. **API Integra Comex** (bilhetada) → apenas se cache não tiver os dados

**⚠️ IMPORTANTE:**
Todos os campos do CE necessários para averbação estão disponíveis diretamente no SQL Server através da tabela `Ce_Root_Conhecimento_Embarque`. Não é necessário buscar do cache do CE quando esses dados estão no SQL Server, seguindo a prioridade: **Cache → SQL Server → API**.

---

### 11. DI (Serpro.dbo)
**Declaração de Importação**

**Tabelas principais:**
- `Hi_Historico_Di` (histórico) ⭐ **CRÍTICO: Contém vínculo com id_importacao**
- `Di_Root_Declaracao_Importacao` (raiz) ⭐ **Contém dadosDiId para buscar pagamentos e frete**
- `Di_Dados_Despacho` (dados de despacho)
- `Di_Dados_Gerais` (dados gerais)
- `Di_Icms` (ICMS)
- `Di_Valor_Mercadoria_Descarga` (valores)
- `Di_Valor_Mercadoria_Embarque` (valores)
- `Di_Adquirente` (adquirente)
- `Di_Importador` (importador)
- `Di_Pagamento` ⭐ **NOVO: Pagamentos/Impostos da DI**
- `Di_pagamentos_cod_receitas` ⭐ **NOVO: Descrição dos códigos de receita**
- `Di_Frete` ⭐ **NOVO: Dados de frete da DI**
- `Di_Seguro` ⭐ **NOVO: Dados de seguro da DI**
- `Di_Transporte` ⭐ **NOVO: Dados de transporte - navio** (contém `nomeVeiculo`, `nomeTransportador`, `codigoViaTransporte`)
- `Di_Dados_Embarque` (dados de embarque - navio)

**Campos principais:**
- `numeroDi`
- `situacaoDi`
- `canalSelecaoParametrizada` ⭐ **CANAL DA DI**
- `dataHoraDesembaraco`
- `situacaoEntregaCarga`
- `totalDolares` (VLMD/VLME)
- `totalReais` (VLMD/VLME)

**⭐ NOVO - Pagamentos/Impostos da DI:**
A tabela `Di_Pagamento` contém todos os pagamentos/impostos da DI, incluindo:
- `rootDiId` (FK → `Di_Root_Declaracao_Importacao.dadosDiId`)
- `codigoReceita` (ex: "0086" = II, "5602" = PIS, "5629" = COFINS, "7811" = Taxa SISCOMEX)
- `numeroRetificacao` (número da retificação)
- `valorReceita` (valor base)
- `valorJurosEncargos` (juros e encargos)
- `valorMulta` (multa)
- `valorTotal` (valor total do pagamento)
- `dataPagamento` ou `dataHoraPagamento` (data do pagamento)
- `codigoTipoPagamento` (código do tipo de pagamento)
- `nomeTipoPagamento` (nome do tipo de pagamento)

A tabela `Di_pagamentos_cod_receitas` contém a descrição dos códigos de receita:
- `cod_receita` (FK → `Di_Pagamento.codigoReceita`)
- `descricao_receita` (descrição do tipo de imposto/receita)

**⭐ NOVO - Frete da DI:**
A tabela `Di_Frete` contém os dados de frete da DI, incluindo:
- `freteId` (PK, relacionado com `Di_Root_Declaracao_Importacao.dadosDiId`)
- `valorTotalDolares` ⭐ - Valor total do frete em dólares (ex: "1000.00")
- `totalReais` ⭐ - Valor total do frete em reais (ex: "5633.20")
- `valorPrepaid` - Valor prepaid (opcional)
- `valorCollect` - Valor collect (opcional)
- `totalMoeda` - Total em moeda negociada
- `codigoMoedaNegociada` - Código da moeda (ex: "220" = USD)
- `valorEmTerritorioNacional` - Valor em território nacional

**Relacionamento:**
- `Di_Root_Declaracao_Importacao.dadosDiId` = `Di_Frete.freteId`

**⭐ NOVO - Seguro da DI:**
A tabela `Di_Seguro` contém os dados de seguro da DI, incluindo:
- `seguroId` (PK, relacionado com `Di_Root_Declaracao_Importacao.dadosDiId`)
- `valorTotalDolares` ⭐ - Valor total do seguro em dólares (ex: "20.06")
- `valorTotalReais` ⭐ - Valor total do seguro em reais (ex: "113.00")
- `valorSeguroTotalMoedaNegociada` - Valor total em moeda negociada
- `codigoMoedaNegociada` - Código da moeda (ex: "220" = USD)

**Relacionamento:**
- `Di_Root_Declaracao_Importacao.dadosDiId` = `Di_Seguro.seguroId`

**⚠️ IMPORTANTE:** Todos os pagamentos/impostos, dados de frete e seguro da DI estão disponíveis no SQL Server através das tabelas `Di_Pagamento`, `Di_pagamentos_cod_receitas`, `Di_Frete` e `Di_Seguro`. Não é necessário consultar a API Integra Comex (bilhetada) para obter esses dados quando estão no SQL Server.

**⚠️ IMPORTANTE - Vínculo DI com Processo:**
A relação entre DI e Processo não está diretamente no campo `numero_di` da tabela `PROCESSO_IMPORTACAO` (que pode estar NULL). 
O vínculo correto é através de:
1. `Hi_Historico_Di.idImportacao` → `comex.dbo.Importacoes.id`
2. `comex.dbo.Importacoes.id` → `make.dbo.PROCESSO_IMPORTACAO.id_importacao`

**Query de referência (di_kanban.sql):**
```sql
SELECT
    diH.idImportacao,
    diDesp.dataHoraDesembaraco,
    diDesp.canalSelecaoParametrizada,
    ddg.situacaoDi,
    ddg.numeroDi,
    ddg.situacaoEntregaCarga,
    ddg.updatedAt AS updatedAtDiGerais,
    diDesp.dataHoraRegistro,
    ddg.dataHoraSituacaoDi,
    DICM.tipoRecolhimento AS tipoRecolhimentoIcms,
    DA.nomeAdquirente,
    DI.nomeImportador,
    DVMD.totalDolares AS dollar_VLMLD,
    DVMD.totalReais AS real_VLMD,
    DVME.totalDolares AS dollar_VLME,
    DVME.totalReais AS real_VLME,
    DICM.dataPagamento,
    diRoot.updatedAt AS updatedi,
    diH.updatedAt AS updatehistdi
FROM Serpro.dbo.Hi_Historico_Di diH
JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
    ON diH.diId = diRoot.dadosDiId
JOIN Serpro.dbo.Di_Dados_Despacho diDesp
    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
JOIN Serpro.dbo.Di_Dados_Gerais ddg 
    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Icms DICM 
    ON diRoot.dadosDiId = DICM.rootDiId
LEFT JOIN Serpro.dbo.Di_Adquirente DA 
    ON diRoot.dadosDiId = DA.adquirenteId
LEFT JOIN Serpro.dbo.Di_Importador DI
    ON diRoot.importadorId = DI.importadorId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD 
    ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME 
    ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
LEFT JOIN comex.dbo.Importacoes i 
    ON i.id = diH.idImportacao
LEFT JOIN make.dbo.PROCESSO_IMPORTACAO t 
    ON t.id_importacao = i.id
WHERE t.numero_processo = 'ALH.0172/25'
-- OU para buscar por id_importacao diretamente:
-- WHERE diH.idImportacao = ?
```

### Query DI - Frete ⭐ **NOVO**
```sql
-- Buscar dados de frete da DI
SELECT TOP 1
    diFrete.valorTotalDolares,
    diFrete.totalReais
FROM Serpro.dbo.Di_Dados_Gerais ddg
INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON ddg.dadosGeraisId = diRoot.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Frete diFrete ON diRoot.dadosDiId = diFrete.freteId
WHERE ddg.numeroDi = ? OR ddg.numeroDi = ?
ORDER BY ddg.dataHoraSituacaoDi DESC
```

**Relacionamento:**
- `Di_Root_Declaracao_Importacao.dadosDiId` = `Di_Frete.freteId`

**Campos retornados:**
- `valorTotalDolares` - Valor total do frete em dólares (string, converter para float)
- `totalReais` - Valor total do frete em reais (string, converter para float)

---

### 12. CCT (duimp.dbo)
**Conhecimento de Carga Aérea**

**Tabelas principais:**
- `CCT_Aereo_RootAereoEntity` (raiz)
- `CCT_Aereo_PartesEstoque` (estoque)
- `CCT_Aereo_BloqueiosAtivo` (bloqueios ativos)
- `CCT_Aereo_BloqueiosBaixado` (bloqueios baixados)

**Campos principais:**
- `identificacao` (AWB)
- `situacaoAtual`
- `dataHoraSituacaoAtual`
- `recintoAduaneiro`
- `codigoAeroportoDestinoConhecimento`
- `codigoAeroportoOrigemConhecimento`

---

## 💰 Tabelas do Banco mAIke_assistente (NOVO - 07/01/2026)

### 13. MOVIMENTACAO_BANCARIA (mAIke_assistente.dbo.MOVIMENTACAO_BANCARIA)

**Lançamentos bancários sincronizados do Banco do Brasil e Santander**

**Campos principais:**
- `id_movimentacao` (PK) - ID único do lançamento
- `banco_origem` - Banco de origem ("BB" ou "SANTANDER")
- `agencia_origem` - Agência de origem
- `conta_origem` - Conta de origem
- `data_movimentacao` - Data da movimentação
- `tipo_movimentacao` - Tipo (ex: "PIX ENVIADO", "TED", "DEPOSITO")
- `sinal_movimentacao` - Sinal ("+" ou "-")
- `valor_movimentacao` - Valor da movimentação
- `moeda` - Moeda (padrão: "BRL")
- `descricao_movimentacao` - Descrição completa (transactionName + historicComplement para Santander)
- `processo_referencia` - Processo detectado automaticamente na descrição (opcional)
- `hash_dados` - Hash SHA-256 para detecção de duplicatas
- `fonte_dados` - Fonte dos dados ("BB_API", "SANTANDER_API")
- `json_dados_originais` - JSON completo da API original

**Contrapartida (CRÍTICO PARA COMPLIANCE):**
- `cpf_cnpj_contrapartida` - CPF/CNPJ da contrapartida
- `nome_contrapartida` - Nome da contrapartida
- `tipo_pessoa_contrapartida` - Tipo de pessoa ("FISICA", "JURIDICA")
- `banco_contrapartida` - Banco da contrapartida
- `agencia_contrapartida` - Agência da contrapartida
- `conta_contrapartida` - Conta da contrapartida
- `contrapartida_validada` - Se contrapartida foi validada
- `data_validacao_contrapartida` - Data de validação

**Índices:**
- `idx_banco_origem` - Por banco e data
- `idx_data_movimentacao` - Por data
- `idx_processo` - Por processo
- `idx_contrapartida` - Por CPF/CNPJ da contrapartida
- `idx_hash_dados` - Para detecção de duplicatas

**Relacionamentos:**
- `id_movimentacao` → `LANCAMENTO_TIPO_DESPESA.id_movimentacao_bancaria`
- `id_movimentacao` → `MOVIMENTACAO_BANCARIA_PROCESSO.id_movimentacao_bancaria`

**Uso típico:** 
- Buscar lançamentos por período, banco, conta
- Detectar processos automaticamente nas descrições
- Evitar duplicatas usando hash

**⚠️ IMPORTANTE:**
- Hash SHA-256 é gerado com: `banco + agencia + conta + data + valor + descricao`
- Duplicatas são detectadas automaticamente na sincronização
- Processos são detectados automaticamente usando regex patterns

---

### 14. TIPO_DESPESA (mAIke_assistente.dbo.TIPO_DESPESA)

**Catálogo de tipos de despesa padrão (23 tipos pré-cadastrados)**

**Campos principais:**
- `id_tipo_despesa` (PK) - ID único do tipo de despesa
- `codigo_tipo_despesa` (UNIQUE) - Código único (ex: "FRETE_INTERNACIONAL", "AFRMM")
- `nome_despesa` - Nome da despesa (ex: "Frete Internacional", "AFRMM")
- `descricao_despesa` - Descrição detalhada
- `categoria_despesa` - Categoria (ex: "FRETE", "IMPOSTO", "TAXA", "SERVICO")
- `tipo_custo` - Tipo de custo (ex: "INTERNACIONAL", "NACIONAL", "BUROCRATICO")
- `plano_contas_codigo` - Código do plano de contas (preparado para futuro)
- `ativo` - Se está ativo (padrão: 1)
- `ordem_exibicao` - Ordem para exibição na UI

**Tipos pré-cadastrados (23):**
1. FRETE_INTERNACIONAL - Frete Internacional
2. SEGURO - Seguro
3. AFRMM - AFRMM
4. MULTAS - Multas
5. TAXA_SISCOMEX_DI - Tx Siscomex (D.I.)
6. TAXA_SISCOMEX_DA - Tx Siscomex (D.A.)
7. OUTROS_CUSTOS_INTERNAC - Outros Custos Internac.
8. LIBERACAO_BL - Liberação B/L
9. INSPECAO_MERCADORIA - Inspeção de Mercadoria
10. ARMAZENAGEM_DTA - Armazenagem DTA
11. FRETE_DTA - Frete DTA
12. ARMAZENAGEM - Armazenagem
13. GRU_TAXA_LI - GRU / Tx LI
14. DESPACHANTE - Despachante
15. SDA - SDA
16. CARRETO - Carreto
17. ESCOLTA - Escolta
18. LAVAGEM_CTNR - Lavagem CTNR
19. DEMURRAGE - Demurrage
20. ANTIDUMPING - Antidumping
21. CONTRATO_CAMBIO - Contrato de Câmbio
22. TARIFAS_BANCARIAS - Tarifas Bancárias
23. OUTROS - Outros

**Índices:**
- `idx_codigo` - Por código único
- `idx_categoria` - Por categoria
- `idx_ativo` - Por ativo e ordem de exibição

**Relacionamentos:**
- `id_tipo_despesa` → `LANCAMENTO_TIPO_DESPESA.id_tipo_despesa`
- `id_tipo_despesa` → `PLANO_CONTAS.id_tipo_despesa`

**Uso típico:** 
- Listar tipos de despesa disponíveis para classificação
- Filtrar por categoria ou tipo de custo
- Usar na conciliação bancária

---

### 15. LANCAMENTO_TIPO_DESPESA (mAIke_assistente.dbo.LANCAMENTO_TIPO_DESPESA)

**Relacionamento N:N entre lançamentos bancários e tipos de despesa**

**Permite:**
- Um lançamento ter múltiplas classificações (split)
- Uma despesa estar em múltiplos lançamentos
- Vincular despesas a processos específicos

**Campos principais:**
- `id_lancamento_tipo_despesa` (PK) - ID único da classificação
- `id_movimentacao_bancaria` (FK) - Lançamento bancário
- `id_tipo_despesa` (FK) - Tipo de despesa
- `processo_referencia` - Processo vinculado (opcional)
- `categoria_processo` - Categoria do processo (opcional)
- `valor_despesa` - Valor específico desta despesa neste lançamento
- `percentual_valor` - Percentual do valor total do lançamento (se dividido)
- `origem_classificacao` - Origem ("MANUAL", "AUTOMATICA", "IA", "REGRA")
- `nivel_confianca` - Nível de confiança (0.00 a 1.00) para classificação automática
- `classificacao_validada` - Se foi validada (padrão: 0)
- `data_validacao` - Data de validação
- `usuario_validacao` - Usuário que validou

**Índices:**
- `idx_movimentacao` - Por lançamento
- `idx_tipo_despesa` - Por tipo de despesa
- `idx_processo` - Por processo
- `idx_validado` - Por validação e origem

**Relacionamentos:**
- `id_movimentacao_bancaria` → `MOVIMENTACAO_BANCARIA.id_movimentacao`
- `id_tipo_despesa` → `TIPO_DESPESA.id_tipo_despesa`

**Uso típico:**
- Classificar lançamentos bancários
- Distribuir valores de um lançamento entre múltiplas despesas
- Vincular despesas a processos específicos

**⚠️ IMPORTANTE:**
- A soma de `valor_despesa` não pode exceder o `valor_movimentacao` do lançamento
- Um lançamento pode ter múltiplas classificações (split)
- Validação de valores é feita na aplicação

---

### 16. IMPOSTO_IMPORTACAO (mAIke_assistente.dbo.IMPOSTO_IMPORTACAO) ⭐ **NOVO (08/01/2026)**

**Impostos de importação distribuídos por lançamento bancário**

**Campos principais:**
- `id_imposto` (PK) - ID único do imposto
- `processo_referencia` - Processo vinculado
- `numero_documento` - Número da DI ou DUIMP
- `tipo_documento` - Tipo ("DI" ou "DUIMP")
- `tipo_imposto` - Tipo de imposto ("II", "IPI", "PIS", "COFINS", "TAXA_UTILIZACAO", "ANTIDUMPING", "ICMS", "OUTROS")
- `codigo_receita` - Código da receita (ex: "0086" = II, "1038" = IPI)
- `descricao_imposto` - Descrição do imposto
- `valor_brl` - Valor em BRL
- `valor_usd` - Valor em USD (se disponível)
- `taxa_cambio` - Taxa de câmbio usada
- `data_pagamento` - Data do pagamento
- `data_vencimento` - Data de vencimento (se disponível)
- `pago` - Se foi pago (padrão: 1)
- `numero_retificacao` - Número da retificação (se aplicável)
- `fonte_dados` - Fonte ("SQL_SERVER", "PORTAL_UNICO", "INTEGRACOMEX", "KANBAN_API")
- `json_dados_originais` - JSON completo da fonte

**Índices:**
- `idx_imposto_processo` - Por processo e tipo de documento
- `idx_imposto_documento` - Por documento
- `idx_imposto_tipo` - Por tipo de imposto e data
- `idx_imposto_data_pagamento` - Por data de pagamento
- `idx_imposto_codigo_receita` - Por código de receita

**Uso típico:**
- Buscar impostos de um processo para preencher na conciliação
- Distribuir impostos de importação em lançamentos bancários
- Rastrear pagamentos de impostos

**⚠️ IMPORTANTE:**
- Valores são buscados da DI/DUIMP no SQL Server
- Permite distribuir um único pagamento de impostos entre múltiplos lançamentos
- Usado na conciliação bancária para preencher automaticamente valores de impostos

---

### 17. VALOR_MERCADORIA (mAIke_assistente.dbo.VALOR_MERCADORIA) ⭐ **NOVO (08/01/2026)**

**Valores de mercadoria (VMLE, VMLD, FOB, CIF) em BRL e USD**

**Campos principais:**
- `id_valor` (PK) - ID único do valor
- `processo_referencia` - Processo vinculado
- `numero_documento` - Número da DI ou DUIMP
- `tipo_documento` - Tipo ("DI" ou "DUIMP")
- `tipo_valor` - Tipo de valor ("DESCARGA", "EMBARQUE", "FOB", "CIF", "VMLE", "VMLD", "OUTROS")
- `moeda` - Moeda ("BRL", "USD", "EUR", "OUTROS")
- `valor` - Valor
- `taxa_cambio` - Taxa de câmbio usada (se conversão)
- `data_valor` - Data de referência do valor
- `fonte_dados` - Fonte ("SQL_SERVER", "PORTAL_UNICO", "INTEGRACOMEX", "KANBAN_API")
- `json_dados_originais` - JSON completo da fonte

**Índices:**
- `idx_valor_processo` - Por processo e tipo de documento
- `idx_valor_documento` - Por documento
- `idx_valor_tipo` - Por tipo de valor e moeda
- `idx_valor_data` - Por data

**Uso típico:**
- Armazenar valores de mercadoria normalizados
- Calcular FOB, CIF e outros valores derivados
- Rastrear valores em diferentes moedas

**⚠️ IMPORTANTE:**
- Valores são buscados da DI/DUIMP no SQL Server
- Permite normalização de valores para FOB (Free On Board)
- Usado em relatórios de importações

---

### 18. PLANO_CONTAS (mAIke_assistente.dbo.PLANO_CONTAS)

**Plano de contas contábil (preparada para futuro uso)**

**Campos principais:**
- `id_plano_contas` (PK) - ID único
- `codigo_contabil` (UNIQUE) - Código contábil (ex: "3.1.01.001")
- `descricao_contabil` - Descrição contábil (ex: "Despesas com Frete Internacional")
- `tipo_conta` - Tipo de conta ("ATIVO", "PASSIVO", "RECEITA", "DESPESA")
- `categoria_conta` - Categoria ("CIRCULANTE", "NÃO_CIRCULANTE", etc.)
- `nivel_conta` - Nível hierárquico (1, 2, 3, 4)
- `id_tipo_despesa` (FK) - Referência ao tipo de despesa (opcional)
- `ativo` - Se está ativo (padrão: 1)

**Índices:**
- `idx_codigo_contabil` - Por código contábil
- `idx_tipo_despesa_plan` - Por tipo de despesa
- `idx_tipo_conta` - Por tipo e categoria de conta

**Relacionamentos:**
- `id_tipo_despesa` → `TIPO_DESPESA.id_tipo_despesa`

**Uso típico:** 
- Preparada para integração futura com sistema contábil
- Vincular despesas a contas contábeis

**⚠️ NOTA:** Esta tabela está preparada para uso futuro, mas ainda não está sendo populada.

---

### 19. HISTORICO_PAGAMENTOS (mAIke_assistente.dbo.HISTORICO_PAGAMENTOS) ⭐ **NOVO (13/01/2026)**

**Histórico completo de pagamentos realizados (BOLETO, PIX, TED, BARCODE)**

**Campos principais:**
- `id_historico_pagamento` (PK) - ID único do registro (IDENTITY)
- `payment_id` (UNIQUE, NOT NULL) - ID único do pagamento (UUID)
- `tipo_pagamento` (NOT NULL) - Tipo: 'BOLETO', 'PIX', 'TED', 'BARCODE'
- `banco` (NOT NULL) - Banco: 'SANTANDER', 'BANCO_DO_BRASIL'
- `ambiente` (NOT NULL) - Ambiente: 'SANDBOX', 'PRODUCAO'
- `status` (NOT NULL) - Status: 'READY_TO_PAY', 'PENDING_VALIDATION', 'PAYED', 'CANCELLED', 'FAILED'
- `valor` (NOT NULL) - Valor do pagamento (DECIMAL(18,2))
- `codigo_barras` - Código de barras (para boletos)
- `beneficiario` - Nome do beneficiário
- `vencimento` - Data de vencimento (DATE)
- `agencia_origem` - Agência de origem
- `conta_origem` - Conta de origem
- `saldo_disponivel_antes` - Saldo antes do pagamento (DECIMAL(18,2))
- `saldo_apos_pagamento` - Saldo após pagamento (DECIMAL(18,2))
- `workspace_id` - ID do workspace (Santander)
- `payment_date` - Data do pagamento (DATE)
- `data_inicio` - Quando foi iniciado (DATETIME)
- `data_efetivacao` - Quando foi efetivado (DATETIME)
- `dados_completos` - JSON com todos os dados retornados pela API (NVARCHAR(MAX))
- `observacoes` - Observações adicionais (NVARCHAR(MAX))
- `criado_em` - Data de criação (DATETIME, DEFAULT GETDATE())
- `atualizado_em` - Data de atualização (DATETIME, DEFAULT GETDATE())

**Índices:**
- `idx_historico_pagamentos_payment_id` - Busca rápida por payment_id
- `idx_historico_pagamentos_status` - Filtro por status e data de efetivação
- `idx_historico_pagamentos_tipo` - Filtro por tipo, banco e ambiente
- `idx_historico_pagamentos_data` - Ordenação por data de efetivação (DESC)
- `idx_historico_pagamentos_banco_ambiente` - Filtro por banco, ambiente e data

**Uso típico:**
- Rastrear todos os pagamentos realizados
- Consultar histórico por período, banco, tipo ou status
- Auditoria de transações
- Relatórios financeiros
- Verificar status de pagamentos pendentes

**⚠️ IMPORTANTE:**
- Dados são gravados tanto no SQL Server (principal) quanto no SQLite (cache)
- `payment_id` é único e serve como identificador principal
- `dados_completos` contém JSON completo da resposta da API para auditoria
- Registro é criado quando pagamento é iniciado e atualizado quando efetivado
- Ambiente (SANDBOX/PRODUCAO) é salvo para distinguir transações de teste

**Relacionamentos:**
- Não há FK direta, mas pode ser vinculado a processos via `beneficiario` ou `codigo_barras` (futuro)

**Query de exemplo:**
```sql
-- Buscar pagamentos pagos no último mês
SELECT 
    payment_id,
    tipo_pagamento,
    banco,
    ambiente,
    valor,
    beneficiario,
    data_efetivacao,
    status
FROM mAIke_assistente.dbo.HISTORICO_PAGAMENTOS
WHERE status = 'PAYED'
  AND data_efetivacao >= DATEADD(MONTH, -1, GETDATE())
ORDER BY data_efetivacao DESC
```

---

### 20. MOVIMENTACAO_BANCARIA_PROCESSO (mAIke_assistente.dbo.MOVIMENTACAO_BANCARIA_PROCESSO)

**Vínculo entre lançamentos bancários e processos**

**Campos principais:**
- `id_movimentacao_processo` (PK) - ID único do vínculo
- `id_movimentacao_bancaria` (FK) - Lançamento bancário
- `processo_referencia` - Processo vinculado
- `categoria_processo` - Categoria do processo
- `tipo_relacionamento` - Tipo de relacionamento (ex: "PAGAMENTO_FRETE")
- `nivel_vinculo` - Nível de vínculo ("ALTO", "MEDIO", "BAIXO")
- `status_vinculo` - Status ("PENDENTE", "VALIDADO", "REJEITADO")
- `id_tipo_despesa` (FK) - Referência ao tipo de despesa (opcional)
- `valor_despesa` - Valor específico desta despesa (opcional)

**Índices:**
- `idx_movimentacao_proc` - Por lançamento
- `idx_processo_proc` - Por processo
- `idx_tipo_despesa_mov_proc` - Por tipo de despesa

**Relacionamentos:**
- `id_movimentacao_bancaria` → `MOVIMENTACAO_BANCARIA.id_movimentacao`
- `id_tipo_despesa` → `TIPO_DESPESA.id_tipo_despesa`

**Uso típico:**
- Vincular lançamentos a processos
- Rastrear relacionamentos entre movimentações e processos

**⚠️ NOTA:** Esta tabela complementa `LANCAMENTO_TIPO_DESPESA` para vínculos diretos lançamento↔processo.

---

### 21. VENDAS_DOCUMENTO (mAIke_assistente.dbo.VENDAS_DOCUMENTO) ⭐ **PLANEJADO (29/01/2026)**

**Objetivo:** persistir (no `mAIke_assistente`) um *snapshot normalizado* de “vendas por NF” vindo do legado **Make/Spalla**, tratando a query do legado como “API” (fonte externa), para:
- permitir **refino iterativo** (filtros, por cliente/data/devolução) sem reconsultar o legado
- habilitar **Curva ABC** (por cliente/centro/empresa/operação)
- reduzir custo/latência e instabilidade do legado em relatórios recorrentes
- manter **auditoria** e rastreabilidade da origem (referência do documento no legado + hash + JSON bruto opcional)

**Fonte (legado):**
- `spalla.dbo.documentos` (documento base)
- joins auxiliares (best-effort): `Make.dbo.TIPOS_DOCUMENTO_SPALLA`, `spalla.dbo.centro_custo`, `spalla.dbo.empresas_filiais`, `Make.dbo.ANALISE_VENDAS_SPALLA` (cliente via `OUTER APPLY TOP 1`)

**Granularidade:** 1 linha = 1 “NF/documento” (nível documento, não itens).

**Campos propostos (MVP):**
- `id_venda_documento` (PK, IDENTITY)
- `source_system` (ex.: `'MAKE_SPALLA'`)
- `source_db` (ex.: `'spalla'`)
- `source_schema` (ex.: `'dbo'`)
- `source_document_key` (chave composta do legado, string)  
  - sugestão: `"{codigo_empresa_filial}|{tipo_movimento}|{codigo_documento}"`
- `codigo_empresa_filial` (INT)
- `empresa_vendedora` (NVARCHAR(200)) — nome já resolvido (ex.: “MASSY DO BRASIL (QUEIMADOS - RJ)”)
- `tipo_movimento` (NVARCHAR(20)) — do legado (ex.: `F`, `C`, etc.)
- `codigo_documento` (INT) — do legado (identificador interno do documento)
- `data_emissao` (DATE)
- `numero_nf` (NVARCHAR(60)) — best-effort (nem sempre é NF-e padrão)
- `cliente` (NVARCHAR(250)) — best-effort (pode vir vazio no legado)
- `total_nf` (DECIMAL(18,2))
- `codigo_centro_custo` (NVARCHAR(30))
- `descricao_centro_custo` (NVARCHAR(250))
- `codigo_tipo_operacao` (NVARCHAR(30))
- `descricao_tipo_operacao` (NVARCHAR(250)) — base para regras: devolução / ICMS / comissão
- `is_doc_icms` (BIT) — True quando operação base = ICMS (documentos “DOC” não entram em total)
- `is_devolucao` (BIT) — True quando operação contém DEVOLUÇÃO/DEVOLUCAO
- `is_excluded` (BIT) — True para operações excluídas do relatório (ex.: comissão de venda)
- `termo_consulta` (NVARCHAR(120)) — termo usado no “fetch” (ex.: `vdm`, `hikvision`) para auditoria
- `inicio_consulta` (DATE), `fim_consulta` (DATE) — recorte consultado (fim exclusivo)
- `hash_linha` (NVARCHAR(64)) — SHA-256 para idempotência/dedup (ex.: `source_document_key|numero_nf|data_emissao|total_nf`)
- `json_origem` (NVARCHAR(MAX), opcional) — payload bruto (para auditoria/compat)
- `criado_em` (DATETIME, DEFAULT GETDATE())
- `atualizado_em` (DATETIME, DEFAULT GETDATE())

**Índices sugeridos (MVP):**
- `idx_vendas_data_emissao` (`data_emissao`)
- `idx_vendas_cliente` (`cliente`)
- `idx_vendas_empresa` (`empresa_vendedora`)
- `idx_vendas_centro` (`codigo_centro_custo`)
- `idx_vendas_op` (`descricao_tipo_operacao`)
- `uq_vendas_hash` UNIQUE (`hash_linha`) — evita duplicata ao sincronizar novamente

**Regras de negócio (relatórios):**
- **DOC/ICMS**: listar, mas **não somar** (não entra em A/B/A−B).
- **Devolução**: entra em **B** (subtrair do total) usando valor absoluto.
- **Comissão de Venda**: **não listar** e **não somar/subtrair** (operação excluída).

**Status:** PLANEJADO — ainda não existe no SQL Server; será implementado com DTO + persistência idempotente.

---

## Queries de Referência

### Query DUIMP Completa (com todos os dados)
```sql
SELECT DISTINCT
    d.numero,
    d.id_processo_importacao,
    d.numero_processo,
    d.versao,
    d.data_ultimo_evento AS data_ultimo_evento_hook,
    d.ultima_situacao AS ultima_situacao_hook,
    d.ultimo_evento AS ultimo_evento_hook,
    drar.canal_consolidado AS canal_duimp,  -- ⭐ CANAL
    dd.situacao AS situacao_diagnostico,
    dd.data_geracao AS data_geracao_diagnostico,
    dd.situacao_duimp AS situacao_duimp,  -- ⭐ SITUAÇÃO
    drr.orgao AS orgao,
    drr.resultado AS resultado,
    dp.data_pagamento AS data_pagamento,
    dp.tributo_tipo AS tributo_tipo,  -- ⭐ TIPO DE TRIBUTO
    dp.valor AS valor,  -- ⭐ VALOR DO TRIBUTO
    ds.situacao_analise_retificacao AS situacao_analise_retificacao,
    ds.situacao_duimp AS situacao_duimp_agr,
    ds.situacao_licenciamento AS situacao_licenciamento,
    dsca.indicador_autorizacao_entrega AS indicador_aut_entrega,
    dsca.situacao AS situacao_conferencia_aduaneira,
    dsca.indicador_desembaraco_decisao_judicial AS indicador_des_judicial
FROM Duimp.dbo.duimp d WITH (NOLOCK)
LEFT JOIN Duimp.dbo.duimp_diagnostico dd WITH (NOLOCK)
    ON dd.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_situacao ds WITH (NOLOCK)
    ON ds.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_pagamentos dp WITH (NOLOCK)
    ON dp.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_situacao_conferencia_aduaneira dsca WITH (NOLOCK)
    ON dsca.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar WITH (NOLOCK)
    ON drar.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_resultado_rfb drr WITH (NOLOCK)
    ON drr.duimp_id = d.duimp_id
WHERE d.numero = ? OR d.numero_processo = ?
```

### Query DI por id_importacao (quando numero_di está NULL)
```sql
-- ⚠️ CRÍTICO: Use esta query quando o campo numero_di na tabela PROCESSO_IMPORTACAO estiver NULL
-- Busca DI através do vínculo: id_importacao → Hi_Historico_Di.idImportacao
SELECT TOP 1
    diH.idImportacao,
    diDesp.dataHoraDesembaraco,
    diDesp.canalSelecaoParametrizada,
    ddg.situacaoDi,
    ddg.numeroDi,
    ddg.situacaoEntregaCarga,
    ddg.updatedAt AS updatedAtDiGerais,
    diDesp.dataHoraRegistro,
    ddg.dataHoraSituacaoDi,
    DICM.tipoRecolhimento AS tipoRecolhimentoIcms,
    DA.nomeAdquirente,
    DI.nomeImportador,
    DVMD.totalDolares AS dollar_VLMLD,
    DVMD.totalReais AS real_VLMD,
    DVME.totalDolares AS dollar_VLME,
    DVME.totalReais AS real_VLME,
    DICM.dataPagamento,
    diRoot.updatedAt AS updatedi,
    diH.updatedAt AS updatehistdi,
    diDesp.modalidadeDespacho,
    diDesp.dataHoraAutorizacaoEntrega
FROM Serpro.dbo.Hi_Historico_Di diH
JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
    ON diH.diId = diRoot.dadosDiId
JOIN Serpro.dbo.Di_Dados_Despacho diDesp
    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
JOIN Serpro.dbo.Di_Dados_Gerais ddg 
    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Icms DICM 
    ON diRoot.dadosDiId = DICM.rootDiId
LEFT JOIN Serpro.dbo.Di_Adquirente DA 
    ON diRoot.dadosDiId = DA.adquirenteId
LEFT JOIN Serpro.dbo.Di_Importador DI
    ON diRoot.importadorId = DI.importadorId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD 
    ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME 
    ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
WHERE diH.idImportacao = ?  -- Substituir pelo id_importacao do processo
ORDER BY ddg.dataHoraSituacaoDi DESC
```

**Uso:**
1. Buscar `id_importacao` do processo: `SELECT id_importacao FROM make.dbo.PROCESSO_IMPORTACAO WHERE id_processo_importacao = ?`
2. Usar o `id_importacao` na query acima para encontrar a DI relacionada

**Exemplo:** Processo `ALH.0172/25` tem `id_importacao = 15462`, que retorna DI `2526376792`

---

### Query DI - Pagamentos/Impostos ⭐ **NOVO**
```sql
-- Buscar todos os pagamentos/impostos de uma DI
SELECT 
    dp.*,
    dpcr.descricao_receita
FROM Serpro.dbo.Di_Root_Declaracao_Importacao drdi 
LEFT JOIN Serpro.dbo.Di_Pagamento dp 
    ON dp.rootDiId = drdi.dadosDiId 
LEFT JOIN Serpro.dbo.Di_pagamentos_cod_receitas dpcr 
    ON dpcr.cod_receita = dp.codigoReceita
WHERE drdi.dadosDiId = ?  -- Substituir pelo dadosDiId da DI
```

**Uso:**
1. Buscar `dadosDiId` da DI: `SELECT dadosDiId FROM Serpro.dbo.Di_Root_Declaracao_Importacao diRoot JOIN Serpro.dbo.Di_Dados_Gerais ddg ON diRoot.dadosGeraisId = ddg.dadosGeraisId WHERE ddg.numeroDi = ?`
2. Usar o `dadosDiId` na query acima para encontrar todos os pagamentos da DI

**Códigos de Receita Comuns:**
- `0086` ou `86` = Imposto de Importação (II)
- `1038` ou `38` = IPI (Imposto sobre Produtos Industrializados)
- `5602` ou `602` = PIS/PASEP
- `5629` ou `629` = COFINS
- `5529` ou `529` = Antidumping
- `7811` ou `811` = Taxa de Utilização do SISCOMEX

**Exemplo:** DI `2527660095` pode ter múltiplos registros em `Di_Pagamento` (um para cada tipo de imposto)

### Query DI - Seguro ⭐ **NOVO**
```sql
-- Buscar dados de seguro da DI
SELECT TOP 1
    diSeguro.valorTotalDolares,
    diSeguro.valorTotalReais
FROM Serpro.dbo.Di_Dados_Gerais ddg
INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON ddg.dadosGeraisId = diRoot.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Seguro diSeguro ON diRoot.dadosDiId = diSeguro.seguroId
WHERE ddg.numeroDi = ? OR ddg.numeroDi = ?
ORDER BY ddg.dataHoraSituacaoDi DESC
```

**Relacionamento:**
- `Di_Root_Declaracao_Importacao.dadosDiId` = `Di_Seguro.seguroId`

**Campos retornados:**
- `valorTotalDolares` - Valor total do seguro em dólares (string, converter para float)
- `valorTotalReais` - Valor total do seguro em reais (string, converter para float)

### Query DI - Transporte/Navio ⭐ **NOVO**
```sql
-- Buscar dados de transporte/navio da DI
SELECT TOP 1
    diTransp.nomeVeiculo,
    diTransp.codigoViaTransporte,
    diTransp.nomeTransportador,
    diTransp.numeroVeiculo,
    diEmb.nomeNavio,
    diEmb.primeiroNavio AS primeiroNavioEmb,
    diEmb.navioDestino AS navioDestinoEmb
FROM Serpro.dbo.Di_Dados_Gerais ddg
INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON ddg.dadosGeraisId = diRoot.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Transporte diTransp ON diRoot.transporteId = diTransp.transporteId
LEFT JOIN Serpro.dbo.Di_Dados_Embarque diEmb ON diRoot.dadosEmbarqueId = diEmb.dadosEmbarqueId
WHERE ddg.numeroDi = ? OR ddg.numeroDi = ?
ORDER BY ddg.dataHoraSituacaoDi DESC
```

**⚠️ IMPORTANTE:**
- A tabela correta é `Di_Transporte` (NÃO `Di_Dados_Transporte`)
- O JOIN correto é: `diRoot.transporteId = diTransp.transporteId` (NÃO `dadosTransporteId`)

**Relacionamentos:**
- `Di_Root_Declaracao_Importacao.transporteId` = `Di_Transporte.transporteId`
- `Di_Root_Declaracao_Importacao.dadosEmbarqueId` = `Di_Dados_Embarque.dadosEmbarqueId`

**Campos retornados:**
- `nomeVeiculo` - Nome do navio/veículo (ex: "COPIAPO", "CMA CGM AMAZONIA")
- `codigoViaTransporte` - Código da via de transporte ("1" = marítimo, "2" = aéreo, etc.)
- `nomeTransportador` - Nome da empresa transportadora
- `numeroVeiculo` - Número do veículo (pode estar vazio)
- `nomeNavio` - Nome do navio (da tabela Di_Dados_Embarque, se disponível)

**Estrutura da tabela Di_Transporte:**
- `transporteId` (PK)
- `nomeVeiculo` ⭐
- `codigoViaTransporte`
- `nomeTransportador`
- `numeroVeiculo`
- `indicadorViaTransporteMultimodal`
- `codigoViaTransportePaisTransportador`
- `createdAt`, `updatedAt`

---

### Query TRANSPORTE (ShipsGo)
```sql
SELECT
    t2.criado_em, 
    t.numero_ce,
    t.numero_duimp,
    t.numero_processo,
    t2.id_externo_shipsgo,
    t2.atual_data_evento,
    t2.atual_evento,
    t2.atual_nome AS atual_porto,
    t2.atual_codigo AS cod_porto,
    t2.destino_data_chegada AS frist_eta,
    t2.destino_nome AS porto_final,
    t2.evento_status AS status_evento,
    t2.status,
    t2.quantidade_conteineres,
    t2.navio AS nome_navio,
    t2.numero_container,
    t2.numero_booking,
    t2.numero_awb,
    t2.id_movimento AS seq_movimento
FROM make.dbo.PROCESSO_IMPORTACAO t
LEFT JOIN make.dbo.TRANSPORTE t2 
    ON t2.id_processo_importacao = t.id_processo_importacao
WHERE t.numero_processo = ?
ORDER BY t2.id_externo_shipsgo DESC
```

---

## ⚠️ Problema Crítico Resolvido: Busca de DI via ID do Processo

### Contexto do Problema
Quando o campo `numero_di` na tabela `make.dbo.PROCESSO_IMPORTACAO` está NULL, a DI não pode ser encontrada diretamente pelo processo. 
Isso acontece porque o vínculo entre DI e Processo não está sempre no campo `numero_di`, mas sim através de uma relação indireta.

### Solução Implementada
Após extensa investigação e testes, foi descoberto que o vínculo correto é:

1. **Processo** → `make.dbo.PROCESSO_IMPORTACAO.id_importacao`
2. **Importação** → `comex.dbo.Importacoes.id` (mesmo valor)
3. **DI** → `Serpro.dbo.Hi_Historico_Di.idImportacao` (mesmo valor)

**Query de busca de DI por id_importacao:**
```sql
SELECT TOP 1
    diH.idImportacao,
    diDesp.dataHoraDesembaraco,
    diDesp.canalSelecaoParametrizada,
    ddg.situacaoDi,
    ddg.numeroDi,
    ddg.situacaoEntregaCarga,
    ddg.updatedAt AS updatedAtDiGerais,
    diDesp.dataHoraRegistro,
    ddg.dataHoraSituacaoDi,
    DICM.tipoRecolhimento AS tipoRecolhimentoIcms,
    DA.nomeAdquirente,
    DI.nomeImportador,
    DVMD.totalDolares AS dollar_VLMLD,
    DVMD.totalReais AS real_VLMD,
    DVME.totalDolares AS dollar_VLME,
    DVME.totalReais AS real_VLME,
    DICM.dataPagamento,
    diRoot.updatedAt AS updatedi,
    diH.updatedAt AS updatehistdi,
    diDesp.modalidadeDespacho,
    diDesp.dataHoraAutorizacaoEntrega
FROM Serpro.dbo.Hi_Historico_Di diH
JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
    ON diH.diId = diRoot.dadosDiId
JOIN Serpro.dbo.Di_Dados_Despacho diDesp
    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
JOIN Serpro.dbo.Di_Dados_Gerais ddg 
    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Icms DICM 
    ON diRoot.dadosDiId = DICM.rootDiId
LEFT JOIN Serpro.dbo.Di_Adquirente DA 
    ON diRoot.dadosDiId = DA.adquirenteId
LEFT JOIN Serpro.dbo.Di_Importador DI
    ON diRoot.importadorId = DI.importadorId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD 
    ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME 
    ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
WHERE diH.idImportacao = ?  -- id_importacao do processo
ORDER BY ddg.dataHoraSituacaoDi DESC
```

### Implementação no Código
A função `_buscar_di_por_id_processo()` em `services/sql_server_processo_schema.py` implementa esta lógica:

1. Busca o `id_importacao` do processo na tabela `make.dbo.PROCESSO_IMPORTACAO`
2. Se `numero_di` estiver NULL, usa `id_importacao` para buscar a DI em `Hi_Historico_Di`
3. Retorna todos os campos da query `di_kanban.sql` (valores, importador, adquirente, etc.)

### Campos Retornados pela Query Completa
- **Dados Básicos:** número, situação, canal, modalidade
- **Datas:** desembaraço, autorização entrega, situação, registro, pagamento ICMS
- **Partes:** nome do importador, nome do adquirente
- **Valores:** VLMD (dólar/real), VLME (dólar/real)
- **Outros:** situação entrega, tipo recolhimento ICMS, IDs, timestamps

---

## ⚠️ Problema Crítico Resolvido: Busca de DI via ID do Processo

> **💡 HISTÓRICO DO DESENVOLVIMENTO:** Esta solução foi desenvolvida após **extensa investigação e múltiplas tentativas** para resolver o problema onde processos não exibiam suas DIs relacionadas na UI, mesmo quando a DI existia no SQL Server. O problema foi identificado quando o usuário reportou que o processo `ALH.0172/25` não mostrava a DI `2526376792`, mesmo que a DI pudesse ser encontrada diretamente no SQL Server.

### Contexto do Problema
Foram identificados **dois problemas principais** na busca de DI relacionada a processos:

1. **Quando `numero_di` está NULL:** A DI não pode ser encontrada diretamente pelo processo. Isso acontece porque o vínculo entre DI e Processo não está sempre no campo `numero_di`, mas sim através de uma relação indireta.
   - **Exemplo:** Processo `ALH.0172/25` tem `numero_di = NULL`, mas possui DI `2526376792` relacionada.

2. **Formato diferente do `numero_di`:** O campo `numero_di` pode estar em formato diferente entre as tabelas:
   - Na tabela `make.dbo.PROCESSO_IMPORTACAO`: `25/0340890-6` (com `/` e `-`)
   - Na tabela `Serpro.dbo.Di_Dados_Gerais`: `2503408906` (sem `/` e `-`)
   - **Exemplo:** Processos `ALH.0004/25` e `ALH.0005/25` têm `numero_di` preenchido, mas a busca direta falhava por causa do formato.

**Sintoma:** Ao consultar processos, a resposta não mostrava a DI, mesmo que ela existisse no banco e o `numero_di` estivesse preenchido.

### Solução Implementada
Após extensa investigação e testes, foi descoberto que o vínculo correto é:

1. **Processo** → `make.dbo.PROCESSO_IMPORTACAO.id_importacao`
2. **Importação** → `comex.dbo.Importacoes.id` (mesmo valor)
3. **DI** → `Serpro.dbo.Hi_Historico_Di.idImportacao` (mesmo valor)

**Fluxo de busca:**
```
Processo (ALH.0172/25)
  ↓ id_processo_importacao = 118
make.dbo.PROCESSO_IMPORTACAO
  ↓ id_importacao = 15462
comex.dbo.Importacoes
  ↓ id = 15462
Serpro.dbo.Hi_Historico_Di
  ↓ idImportacao = 15462
DI encontrada: 2526376792
```

### Implementação no Código
A função `_buscar_di_por_id_processo()` em `services/sql_server_processo_schema.py` implementa esta lógica:

1. Busca o `id_importacao` do processo na tabela `make.dbo.PROCESSO_IMPORTACAO`
2. Se `numero_di` estiver NULL, usa `id_importacao` para buscar a DI em `Hi_Historico_Di`
3. Retorna todos os campos da query `di_kanban.sql` (valores, importador, adquirente, etc.)

**Código de referência:**
```python
def _buscar_di_por_id_processo(sql_adapter, id_processo_importacao: int, id_importacao: Optional[int] = None):
    # 1. Buscar id_importacao do processo
    # 2. Se numero_di está NULL, buscar via Hi_Historico_Di usando id_importacao
    # 3. Retornar todos os campos da query di_kanban.sql
```

### Campos Retornados pela Query Completa
A query retorna **TODOS** os campos da `di_kanban.sql`:

- **Dados Básicos:** número, situação, canal, modalidade
- **Datas:** desembaraço, autorização entrega, situação, registro, pagamento ICMS
- **Partes:** nome do importador, nome do adquirente
- **Valores:** VLMD (dólar/real), VLME (dólar/real)
- **Outros:** situação entrega, tipo recolhimento ICMS, IDs, timestamps

### ⚠️ Problemas Encontrados Durante Desenvolvimento

Esta seção documenta **todos os problemas encontrados e como foram resolvidos**, para evitar que outros desenvolvedores passem pelas mesmas dificuldades:

#### 0. Formato do numero_di Diferente (Descoberto em 15/12/2025)
**Problema:**
- O campo `numero_di` na tabela `make.dbo.PROCESSO_IMPORTACAO` pode estar em formato diferente do formato na tabela `Serpro.dbo.Di_Dados_Gerais`
- Exemplo: `25/0340890-6` (com `/` e `-`) na tabela PROCESSO_IMPORTACAO vs `2503408906` (sem `/` e `-`) na Di_Dados_Gerais
- **Impacto:** Busca direta falhava mesmo quando o `numero_di` estava preenchido
- **Sintoma:** Processos como `ALH.0004/25` e `ALH.0005/25` não mostravam DI na UI, mesmo tendo `numero_di` preenchido

**Solução:**
- Normalizar `numero_di` removendo `/` e `-` antes de buscar
- Buscar tanto pelo formato original quanto pelo normalizado: `WHERE ddg.numeroDi = ? OR ddg.numeroDi = ?`
- Adicionar fallback para buscar via `id_importacao` mesmo quando `numero_di` está preenchido (caso a normalização não funcione)

**Código:**
```python
# Normalizar numero_di: remover / e -
numero_di_normalizado = numero_di.replace('/', '').replace('-', '') if numero_di else None

# Buscar tanto pelo formato original quanto pelo normalizado
query_di = '''
    WHERE ddg.numeroDi = ? OR ddg.numeroDi = ?
'''
result = sql_adapter.execute_query(query_di, 'Serpro', [numero_di, numero_di_normalizado])
```

#### 1. Nome da Tabela Incorreto
**Problema:**
- ❌ Código usava: `Processos_Importacao` (com 's')
- ✅ Nome correto: `PROCESSO_IMPORTACAO` (sem 's', maiúsculas)
- **Impacto:** Query retornava `False/None` silenciosamente, sem erros aparentes
- **Tempo gasto:** ~30 minutos de debug até descobrir que a query não estava retornando dados

**Solução:**
```python
# ANTES (errado):
FROM Make.dbo.Processos_Importacao

# DEPOIS (correto):
FROM Make.dbo.PROCESSO_IMPORTACAO
```

#### 2. Tentativa de Busca via CE (Falhou)
**Problema:**
- Tentativa inicial: buscar DI relacionada ao CE do processo
- Implementada função `_buscar_di_por_ce()` que buscava em `Di_Dados_Embarque`
- **Resultado:** Não funcionou para o caso `ALH.0172/25` porque a relação CE-DI não estava clara
- **Tempo gasto:** ~1 hora implementando e testando busca via CE

**Lição aprendida:** Nem sempre a relação CE-DI está disponível ou é confiável. O vínculo via `id_importacao` é mais direto.

#### 3. Descoberta do Vínculo Correto via Hi_Historico_Di
**Problema:**
- Após ler o arquivo `querry di_kanban.sql`, descobriu-se que a query original já fazia o JOIN correto
- A query mostrava: `Hi_Historico_Di.idImportacao` → `comex.dbo.Importacoes.id` → `make.dbo.PROCESSO_IMPORTACAO.id_importacao`
- **Tempo gasto:** ~2 horas investigando o schema e testando diferentes abordagens

**Solução:**
Implementada função `_buscar_di_por_id_processo()` que:
1. Busca `id_importacao` do processo
2. Usa `id_importacao` para buscar DI em `Hi_Historico_Di`
3. Retorna todos os campos da query `di_kanban.sql`

#### 4. Query Completa com Todos os Campos
**Problema:**
- Inicialmente, a query retornava apenas campos básicos (número, situação, canal)
- Usuário solicitou "riqueza de informação" - todos os campos da `di_kanban.sql`
- **Tempo gasto:** ~30 minutos expandindo a query para incluir todos os campos

**Solução:**
Query expandida para incluir:
- Valores (VLMD/VLME em dólar e real)
- Nome do importador e adquirente
- Tipo de recolhimento ICMS
- Data de pagamento ICMS
- Timestamps de atualização

#### 5. Formatação na UI Não Mostrava DI
**Problema:**
- Função `_formatar_resposta_processo_dto()` só verificava `processo_dto.numero_di` (que estava NULL)
- Mesmo com a DI sendo encontrada nos dados consolidados, não aparecia na resposta
- **Tempo gasto:** ~1 hora debugando por que a DI não aparecia na UI

**Solução:**
Atualizado para buscar DI em `dados_completos.get('di')` mesmo quando `numero_di` está NULL:
```python
# ANTES:
if processo_dto.numero_di:
    # mostrar DI

# DEPOIS:
di_data_completo = processo_dto.dados_completos.get('di', {}) if processo_dto.dados_completos else {}
numero_di_final = processo_dto.numero_di or di_data_completo.get('numero')
if numero_di_final:
    # mostrar DI com todos os campos
```

#### 6. ProcessoRepository Não Extraía DI Corretamente
**Problema:**
- `ProcessoRepository` não extraía a DI dos dados consolidados quando `numero_di` estava NULL
- O DTO retornava `numero_di = None` mesmo com a DI presente em `dados_completos`
- **Tempo gasto:** ~45 minutos investigando por que o DTO não tinha a DI

**Solução:**
Atualizado para extrair DI dos dados consolidados:
```python
numero_di_final = processo_consolidado.get('numero_di') or di_data.get('numero') if di_data else None
```

#### 7. Logs Não Apareciam (Debug Difícil)
**Problema:**
- Função não entrava no bloco de busca via `id_importacao`
- Logs não apareciam, dificultando o debug
- **Tempo gasto:** ~1 hora adicionando logs e testando passo a passo

**Solução:**
- Adicionados logs INFO em pontos críticos
- Testes passo a passo para identificar onde a função falhava
- Descoberto que o problema era o nome da tabela (item 1)

### Resumo do Tempo Total de Desenvolvimento
- **Investigação inicial:** ~1 hora
- **Tentativa busca via CE:** ~1 hora
- **Descoberta do vínculo correto:** ~2 horas
- **Implementação da query completa:** ~30 minutos
- **Correção da UI:** ~1 hora
- **Correção do ProcessoRepository:** ~45 minutos
- **Debug e testes:** ~1 hora
- **Correção formato numero_di (15/12/2025):** ~30 minutos
- **Total aproximado:** ~7.5 horas de trabalho

### Lições Aprendidas
1. **Sempre verificar o nome exato das tabelas** - diferenças de maiúsculas/minúsculas e plurais podem causar falhas silenciosas
2. **Consultar queries existentes primeiro** - a `di_kanban.sql` já tinha a solução, mas não estava sendo usada
3. **Testar queries diretamente** - antes de implementar na função, testar a query isoladamente
4. **Logs são essenciais** - sem logs adequados, é muito difícil debugar problemas de lógica
5. **Verificar múltiplas camadas** - o problema estava em 3 lugares: busca SQL, ProcessoRepository e formatação UI
6. **⚠️ Formato de dados pode variar** - sempre normalizar campos antes de buscar (ex: `numero_di` pode ter `/` e `-` em uma tabela e não ter em outra)
7. **Implementar fallbacks** - mesmo quando um campo está preenchido, pode estar em formato incorreto, então sempre ter fallback via `id_importacao`

### Exemplo de Uso Real
Para o processo `ALH.0172/25`:
- `id_processo_importacao`: 118
- `id_importacao`: 15462
- DI encontrada: `2526376792` (via `Hi_Historico_Di.idImportacao = 15462`)
- Situação: `DI_DESEMBARACADA`
- Canal: `Amarelo`
- Valores: VLMD BRL 373.077,74, VLME BRL 349.926,12
- Importador: `MASSY DO BRASIL COMERCIO EXTERIOR LTDA`
- Adquirente: `MCD COMERCIO E DISTRIBUICAO LTDA`

### Arquivos Modificados
- `services/sql_server_processo_schema.py`: Adicionada função `_buscar_di_por_id_processo()` com query completa
- `services/agents/processo_agent.py`: Atualizado `_formatar_resposta_processo_dto()` para buscar DI em `dados_completos`
- `services/processo_repository.py`: Atualizado para extrair DI dos dados consolidados corretamente

### Exemplo de Uso
Para o processo `ALH.0172/25`:
- `id_processo_importacao`: 118
- `id_importacao`: 15462
- DI encontrada: `2526376792` (via `Hi_Historico_Di.idImportacao = 15462`)
- Situação: `DI_DESEMBARACADA`
- Canal: `Amarelo`
- Valores: VLMD BRL 373.077,74, VLME BRL 349.926,12
- Importador: `MASSY DO BRASIL COMERCIO EXTERIOR LTDA`

---

## Mapeamento de Campos Críticos

### DUIMP - Situação
- **Fonte principal:** `duimp_diagnostico.situacao_duimp`

### DI - Busca via ID do Processo
- **Quando usar:** Quando `numero_di` na tabela `PROCESSO_IMPORTACAO` estiver NULL
- **Método:** Buscar via `Hi_Historico_Di.idImportacao` usando o `id_importacao` do processo
- **Query:** Ver seção "Query DI por id_importacao" acima
- **Implementação:** Função `_buscar_di_por_id_processo()` em `services/sql_server_processo_schema.py`

### DI - Campos Disponíveis (Query Completa)
Quando buscada via `Hi_Historico_Di`, a query retorna **TODOS** os seguintes campos:

**Dados Básicos:**
- `numeroDi` - Número da DI
- `situacaoDi` - Situação da DI (ex: "DI_DESEMBARACADA")
- `canalSelecaoParametrizada` - Canal (ex: "Amarelo", "Verde", "Vermelho")
- `modalidadeDespacho` - Modalidade (ex: "NORMAL")

**Datas:**
- `dataHoraDesembaraco` - Data/hora do desembaraço
- `dataHoraAutorizacaoEntrega` - Data/hora de autorização de entrega
- `dataHoraSituacaoDi` - Data/hora da situação
- `dataHoraRegistro` - Data/hora de registro
- `dataPagamento` - Data de pagamento do ICMS

**Partes:**
- `nomeImportador` - Nome do importador
- `nomeAdquirente` - Nome do adquirente

**Valores:**
- `dollar_VLMLD` - Valor Mercadoria Local Descarga (USD)
- `real_VLMD` - Valor Mercadoria Local Descarga (BRL)
- `dollar_VLME` - Valor Mercadoria Local Embarque (USD)
- `real_VLME` - Valor Mercadoria Local Embarque (BRL)

**Outros:**
- `situacaoEntregaCarga` - Situação de entrega da carga
- `tipoRecolhimentoIcms` - Tipo de recolhimento do ICMS
- `idImportacao` - ID da importação (vínculo com processo)
- `updatedAtDiGerais`, `updatedi`, `updatehistdi` - Timestamps de atualização
- **Fallback:** `duimp.ultima_situacao`
- **Agregada:** `duimp_situacao.situacao_duimp`

### DUIMP - Canal
- **Fonte principal:** `duimp_resultado_analise_risco.canal_consolidado`
- **Valores possíveis:** "VERDE", "VERMELHO", "AMARELO"

### DUIMP - Impostos/Tributos
- **Fonte 1 (recomendado):** `duimp_tributos_calculados` ⭐
  - **Campos:** `tipo`, `valor_calculado`, `valor_devido`, `valor_a_recolher`, `valor_recolhido`, `valor_suspenso`, `valor_a_reduzir`
  - **Vantagem:** Detalhamento completo dos valores (calculado, devido, recolhido, etc.)
- **Fonte 2 (alternativa):** `duimp_pagamentos`
  - **Campos:** `tributo_tipo` (II, IPI, PIS, COFINS, TAXA_UTILIZACAO), `valor`, `data_pagamento`
  - **Vantagem:** Inclui data de pagamento

### DUIMP - Valores Totais da Mercadoria
- **Fonte:** `duimp_tributos_mercadoria` ⭐
- **Campos:** `valor_total_local_embarque_brl`, `valor_total_local_embarque_usd`

### DUIMP - Histórico de Situações
- **Fonte:** `duimp_diagnostico` (múltiplos registros por `duimp_id`)
- **Ordenar por:** `data_geracao DESC`

### DUIMP - CE Relacionado ⭐ **NOVO (19/12/2025)**
O CE relacionado à DUIMP pode ser encontrado via `id_importacao`:
- **Fonte:** Via `id_importacao` → `Hi_Historico_Ce.idImportacao` → `Ce_Root_Conhecimento_Embarque`
- **Método:** Usar função `_buscar_ce_por_id_importacao()` (mesma lógica usada para DI)
- **Relacionamento:** `make.dbo.PROCESSO_IMPORTACAO.id_importacao` → `comex.dbo.Importacoes.id` → `Serpro.dbo.Hi_Historico_Ce.idImportacao`
- **Uso:** Quando a DUIMP é buscada via `_buscar_duimp_completo()`, passar `id_importacao` como parâmetro para buscar o CE relacionado automaticamente

**⚠️ IMPORTANTE:** Processos antigos que não estão no Kanban podem ter DUIMP mas não ter o CE relacionado no JSON. Sempre usar o fallback via `id_importacao` para garantir que o CE relacionado seja encontrado.

### CE - Campos Completos ⭐ **NOVO**
Todos os campos do CE necessários para averbação estão disponíveis na tabela `Ce_Root_Conhecimento_Embarque`:
- **Fonte:** `Serpro.dbo.Ce_Root_Conhecimento_Embarque`
- **Campos principais:**
  - `numero` - Número do CE
  - `portoOrigem` - Porto de Origem
  - `portoDestino` - Porto de Destino
  - `paisProcedencia` ⭐ - País de Procedência (código ISO 2 letras, ex: "CN")
    - **Mapeamento:** Converter para nome completo usando tabela `PAISES` (ex: "CN" → "CHINA")
    - **Fonte:** `Ce_Root_Conhecimento_Embarque.paisProcedencia` ✅ **CONFIRMADO E TESTADO**
  - `dataEmissao` ⭐ - Data de Emissão do CE (formato ISO: "2025-04-22T00:00:00")
    - **Formatação:** Converter para "YYYY-MM-DD" antes de exibir
    - **Fonte:** `Ce_Root_Conhecimento_Embarque.dataEmissao` ✅ **CONFIRMADO E TESTADO**
  - `tipo` ⭐ - Tipo do CE (ex: "HBL", "MBL")
    - **Fonte:** `Ce_Root_Conhecimento_Embarque.tipo` ✅ **CONFIRMADO E TESTADO**
  - `descricaoMercadoria` ⭐ - Descrição da Mercadoria (texto completo)
    - **Fonte:** `Ce_Root_Conhecimento_Embarque.descricaoMercadoria` ✅ **CONFIRMADO E TESTADO**
  - `situacaoCarga` - Situação da carga
  - `dataSituacaoCarga` - Data da situação
  - `valorFreteTotal` - Valor total do frete
  - `pendenciaAFRMM` - Pendência AFRMM
  - `indicadorPendenciaFrete` - Indicador de pendência de frete
  - `dataArmazenamentoCarga` - Data de armazenamento
  - `dataDestinoFinal` - Data de destino final
  - `portoAtracacaoAtual` - Porto de atracação atual
  - `localEmbarque` - Local de embarque (alternativa para portoOrigem)
  - `dataEmbarque` - Data de embarque (alternativa para dataEmissao)

**⚠️ IMPORTANTE:** Todos esses campos estão disponíveis diretamente no SQL Server. Não é necessário buscar do cache do CE quando esses dados estão no SQL Server.

### DI - Pagamentos/Impostos ⭐ **NOVO**
Todos os pagamentos/impostos da DI estão disponíveis no SQL Server:
- **Fonte principal:** `Serpro.dbo.Di_Pagamento`
- **Fonte auxiliar:** `Serpro.dbo.Di_pagamentos_cod_receitas` (descrição dos códigos)
- **Relacionamento:** `Di_Pagamento.rootDiId` → `Di_Root_Declaracao_Importacao.dadosDiId`
- **Campos principais:**
  - `codigoReceita` - Código da receita (ex: "0086" = II, "5602" = PIS, "5629" = COFINS)
  - `numeroRetificacao` - Número da retificação (geralmente "00")
  - `valorReceita` - Valor base da receita
  - `valorJurosEncargos` - Juros e encargos
  - `valorMulta` - Multa
  - `valorTotal` - Valor total do pagamento (BRL)
  - `dataPagamento` ou `dataHoraPagamento` - Data do pagamento
  - `codigoTipoPagamento` - Código do tipo de pagamento
  - `nomeTipoPagamento` - Nome do tipo de pagamento (ex: "Débito em Conta")
  - `descricao_receita` (via JOIN) - Descrição do tipo de imposto/receita

**Códigos de Receita Comuns:**
- `0086` ou `86` = Imposto de Importação (II)
- `1038` ou `38` = IPI (Imposto sobre Produtos Industrializados)
- `5602` ou `602` = PIS/PASEP
- `5629` ou `629` = COFINS
- `5529` ou `529` = Antidumping
- `7811` ou `811` = Taxa de Utilização do SISCOMEX

### DI - Frete ⭐ **NOVO**
Os dados de frete da DI estão disponíveis no SQL Server:
- **Fonte:** `Serpro.dbo.Di_Frete`
- **Relacionamento:** `Di_Frete.freteId` = `Di_Root_Declaracao_Importacao.dadosDiId`
- **Campos principais:**
  - `valorTotalDolares` ⭐ - Valor total do frete em dólares (string, ex: "1000.00")
  - `totalReais` ⭐ - Valor total do frete em reais (string, ex: "5633.20")
  - `valorPrepaid` - Valor prepaid (opcional)
  - `valorCollect` - Valor collect (opcional)
  - `totalMoeda` - Total em moeda negociada
  - `codigoMoedaNegociada` - Código da moeda (ex: "220" = USD)
  - `valorEmTerritorioNacional` - Valor em território nacional

### DI - Seguro ⭐ **NOVO**
Os dados de seguro da DI estão disponíveis no SQL Server:
- **Fonte:** `Serpro.dbo.Di_Seguro`
- **Relacionamento:** `Di_Seguro.seguroId` = `Di_Root_Declaracao_Importacao.dadosDiId`
- **Campos principais:**
  - `valorTotalDolares` ⭐ - Valor total do seguro em dólares (string, ex: "20.06")
  - `valorTotalReais` ⭐ - Valor total do seguro em reais (string, ex: "113.00")
  - `valorSeguroTotalMoedaNegociada` - Valor total em moeda negociada
  - `codigoMoedaNegociada` - Código da moeda (ex: "220" = USD)

### DI - CE Relacionado ⭐ **NOVO (19/12/2025)**
O CE relacionado à DI pode ser encontrado de múltiplas formas:
- **Fonte 1:** `Di_Transporte.numeroConhecimentoEmbarque` (ou `numeroConhecimentoEmbarqueMaster`, `numeroConhecimentoEmbarqueHouse`)
- **Fonte 2:** Via `id_importacao` → `Hi_Historico_Ce.idImportacao` → `Ce_Root_Conhecimento_Embarque` (fallback para processos antigos)
- **Relacionamento:** `Di_Root_Declaracao_Importacao.dadosDiId` → `Di_Transporte.transporteId` (via `diRoot.transporteId`)
- **Fallback:** Se não encontrado no transporte, buscar via `id_importacao` usando `_buscar_ce_por_id_importacao()`

**⚠️ IMPORTANTE:** Todos os pagamentos/impostos, dados de frete, seguro e CE relacionado da DI estão disponíveis diretamente no SQL Server. Não é necessário consultar a API Integra Comex (bilhetada) para obter esses dados quando estão no SQL Server. A prioridade de busca deve ser: **Cache → SQL Server → API**.

---

## 📝 Notas Importantes

### Boas Práticas de Query

1. **NOLOCK:** As queries usam `WITH (NOLOCK)` para evitar locks em leitura
2. **LEFT JOIN:** Todos os JOINs são LEFT para não perder dados se alguma tabela não tiver registro
3. **DISTINCT:** Usar DISTINCT quando há múltiplos registros relacionados (ex: múltiplos pagamentos)
4. **Ordenação:** Sempre ordenar por data mais recente primeiro (DESC)
5. **Normalização:** Sempre normalizar `numero_di` removendo `/` e `-` antes de buscar
6. **Fallback:** Sempre implementar fallback via `id_importacao` quando `numero_di` está NULL

### Troubleshooting Comum

#### Problema: DI não encontrada mesmo com `numero_di` preenchido
**Solução:** 
1. Normalizar `numero_di` removendo `/` e `-`
2. Buscar tanto pelo formato original quanto normalizado: `WHERE ddg.numeroDi = ? OR ddg.numeroDi = ?`
3. Se ainda não encontrar, usar fallback via `id_importacao`

#### Problema: `numero_di` está NULL no processo
**Solução:**
1. Buscar `id_importacao` do processo: `SELECT id_importacao FROM make.dbo.PROCESSO_IMPORTACAO WHERE numero_processo = ?`
2. Usar `id_importacao` para buscar DI: `SELECT ... FROM Serpro.dbo.Hi_Historico_Di WHERE idImportacao = ?`

#### Problema: Campos do CE não encontrados
**Solução:**
1. Verificar se está buscando na tabela correta: `Ce_Root_Conhecimento_Embarque`
2. Campos confirmados: `paisProcedencia`, `dataEmissao`, `tipo`, `descricaoMercadoria`
3. Campos que NÃO existem: `dataEmbarque`, `localEmbarque` (usar alternativas)

#### Problema: DUIMP não aparece na resposta mesmo sendo encontrada
**Sintoma:** A DUIMP é encontrada e formatada corretamente, mas o fallback sobrescreve a resposta, removendo a DUIMP.
**Causa:** A lógica de decisão do fallback não considera a DUIMP ao decidir se deve sobrescrever a resposta.
**Solução (19/12/2025):**
1. Verificar se a resposta já contém DUIMP formatada (`tem_duimp_na_resposta`)
2. Se a resposta já tem DUIMP, **NÃO** usar o fallback (evitar sobrescrever)
3. Verificar se a DUIMP está completa (situação e canal) antes de decidir usar fallback
4. A lógica deve ser: `deve_usar_fallback_final = (deve_usar_fallback AND NOT tem_duimp_na_resposta) OR ...`

**Código de referência:**
```python
# Verificar se DUIMP está completa
tem_duimp = bool(processo_dto.numero_duimp)
tem_duimp_completa = False
if tem_duimp and processo_dto.dados_completos:
    duimp_data = processo_dto.dados_completos.get('duimp', {})
    if isinstance(duimp_data, dict):
        tem_situacao_duimp = bool(duimp_data.get('situacao') or ...)
        tem_canal_duimp = bool(duimp_data.get('canal') or ...)
        tem_duimp_completa = tem_situacao_duimp and tem_canal_duimp

# Verificar se resposta já tem DUIMP formatada
tem_duimp_na_resposta = 'DUIMP' in resposta_texto or '📝' in resposta_texto

# NÃO usar fallback se resposta já tem DUIMP
deve_usar_fallback_final = (deve_usar_fallback and not tem_duimp_na_resposta) or ...
```

#### Problema: CE relacionado à DUIMP não aparece
**Sintoma:** A DUIMP é exibida, mas o CE relacionado não aparece na resposta.
**Causa:** O CE relacionado não está sendo buscado quando a DUIMP é encontrada.
**Solução (19/12/2025):**
1. Passar `id_importacao` para `_buscar_duimp_completo()` quando disponível
2. Dentro de `_buscar_duimp_completo()`, chamar `_buscar_ce_por_id_importacao()` se `id_importacao` estiver disponível e `numero_ce` não for encontrado
3. Incluir `ce_relacionado` completo no `duimp_data` retornado
4. Na formatação, verificar `duimp_sql.get('ce_relacionado')` e `duimp_data.get('ce_relacionado')` para exibir o CE relacionado

**Código de referência:**
```python
# Em _buscar_duimp_completo():
if id_importacao and not duimp_data.get('numero_ce'):
    ce_relacionado = _buscar_ce_por_id_importacao(sql_adapter, id_importacao)
    if ce_relacionado and ce_relacionado.get('numero'):
        duimp_data['numero_ce'] = ce_relacionado.get('numero')
        duimp_data['ce_relacionado'] = ce_relacionado  # Dados completos do CE
```

### Performance

- **Índices:** As tabelas principais têm índices em campos de busca frequente (`numero_processo`, `numero_di`, `id_importacao`)
- **Cache:** Sempre verificar cache local antes de consultar SQL Server
- **Queries:** Evitar `SELECT *`, buscar apenas campos necessários

### Atualização de Dados

- **Fonte:** O Kanban atualiza o SQL Server com todos os dados das APIs externas (DI, CE, CCT, DUIMP)
- **Frequência:** Dados são atualizados em tempo real quando há eventos nos processos
- **Sincronização:** Não é necessário consultar APIs externas se os dados estão no SQL Server
