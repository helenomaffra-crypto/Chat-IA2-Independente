# 📋 REGRAS DE NEGÓCIO - Documentação Completa

**Última atualização:** 23/12/2025

Este documento descreve todas as regras de negócio da aplicação, incluindo quando e como elas são aplicadas, condições específicas e exceções.

---

## 📑 Índice

1. [Regras de Chegada de Processos](#1-regras-de-chegada-de-processos)
2. [Regras de Pendências](#2-regras-de-pendências)
   - [2.1. Pendência de ICMS](#21-pendência-de-icms)
   - [2.2. Pendência de AFRMM](#22-pendência-de-afrmm)
   - [2.3. Pendência de LPCO](#23-pendência-de-lpco)
   - [2.4. Pendência de Frete](#24-pendência-de-frete)
3. [Regras de Status/Situação](#3-regras-de-statussituação)
   - [3.1. Status da DI](#31-status-da-di)
   - [3.2. Status da DUIMP](#32-status-da-duimp)
   - [3.3. Status do CE](#33-status-do-ce)
4. [Regras de Notificações](#4-regras-de-notificações)
   - [4.4. Text-to-Speech (TTS)](#44-text-to-speech-tts)
   - [4.5. Regras de DTA (Declaração de Trânsito Aduaneiro)](#45-regras-de-dta-declaração-de-trânsito-aduaneiro)
5. [Regras de ETA (Estimated Time of Arrival)](#5-regras-de-eta-estimated-time-of-arrival)
6. [Regras de Categorização](#6-regras-de-categorização)
7. [Regras de Processos Prontos para Registro](#7-regras-de-processos-prontos-para-registro)
8. [Regras de Fechamento do Dia](#8-regras-de-fechamento-do-dia)
9. [Regras de ETA Alterado no Dashboard](#9-regras-de-eta-alterado-no-dashboard)
10. [Regras de Detecção de DUIMP Registrada](#10-regras-de-detecção-de-duimp-registrada)
11. [Regras de Detecção de Perguntas sobre Chegada](#11-regras-de-detecção-de-perguntas-sobre-chegada)
12. [Regras de Consulta TECwin NCM](#12-regras-de-consulta-tecwin-ncm)
13. [Regras de Averbacao](#13-regras-de-averbacao)
14. [Regras de Atraso Crítico](#14-regras-de-atraso-crítico)
15. [Regras de Bloqueios CE](#15-regras-de-bloqueios-ce)
16. [Regras de Formatação de Processos para TTS](#16-regras-de-formatação-de-processos-para-tts)
17. [Checklist de Validação](#17-checklist-de-validação)
18. [Histórico de Mudanças](#18-histórico-de-mudanças)
19. [Referências](#19-referências)

---

## 1. Regras de Chegada de Processos

### 1.1. Definição de Chegada

**Chegada** = carga chegou ao **DESTINO FINAL** (porto/aeroporto de destino).

⚠️ **IMPORTANTE:** Chegada NÃO é:
- Entrega ao cliente (isso é `dataEntrega`)
- ETA (previsão de chegada)
- Atracação do navio (pode ser porto intermediário)
- Situação "DESCARREGADA" (pode ser porto intermediário para transbordo)

### 1.2. Campos que Indicam Chegada Real

#### Para CE Marítimo:
- **Campo principal:** `dataDestinoFinal` (vem da API do CE)
- **Campo secundário:** `dataArmazenamento` (confirma que chegou e foi armazenada)

#### Para CCT Aéreo:
- **Campo principal:** `dataHoraChegadaEfetiva` (vem da API do CCT)
- **Locais possíveis:**
  - Raiz do JSON: `dataHoraChegadaEfetiva`
  - `Shipsgo_air.dataHoraChegadaEfetiva`
  - `viagem.dataHoraChegadaEfetiva`

### 1.3. Campos que NÃO Devem Ser Usados

❌ **NUNCA usar:**
- `dataEntrega` (é entrega ao cliente, não chegada ao porto)
- `dataPrevisaoChegada` (é ETA, não chegada confirmada)
- `shipgov2.destino_data_chegada` (é ETA, não chegada confirmada)
- `dataAtracamento` (pode ser apenas atracação do navio, não chegada da carga)
- `dataSituacaoCargaCe` (é mudança de status, não chegada)
- `containerDetailsCe[].operacaoData` (pode ser operação em porto intermediário)

### 1.4. Quando uma Chegada é Confirmada

Uma chegada é confirmada quando:
1. **Antes:** `dataDestinoFinal` (ou `dataHoraChegadaEfetiva` para aéreo) era `None` ou vazio
2. **Agora:** `dataDestinoFinal` (ou `dataHoraChegadaEfetiva` para aéreo) tem um valor válido

### 1.5. Notificação de Chegada

Quando uma chegada é confirmada, o sistema cria uma notificação:
- **Tipo:** `chegada`
- **Título:** "Chegada confirmada"
- **Mensagem:** Inclui o processo de referência

---

## 2. Regras de Pendências

### 2.1. Pendência de ICMS

#### 2.1.1. Regra Legal

**ICMS só pode ser cobrado APÓS desembaraço.** O ato gerador do ICMS é o desembaraço da carga.

#### 2.1.2. Lógica Diferenciada: DI vs DUIMP

##### Para DI (Declaração de Importação):

ICMS é considerado pendente quando:
- ✅ DI está **desembaraçada** E
- ✅ Campo `pendencia_icms` não é `None`, vazio, "OK" ou "PAGO"

**Situações que indicam desembaraço para DI:**
- `situacao_di` contém "DESEMBARACADA" ou "DESEMBARACADO"
- `situacao_entrega` contém "DESEMBARACADA" ou "DESEMBARACADO"
- `situacao_entrega` contém "ENTREGUE"
- `situacao_entrega` contém "ENTREGA AUTORIZADA SEM PROSSEGUIMENTO DO DESPACHO"
- `situacao_entrega` contém "ENTREGA AUTORIZADA"
- `data_hora_desembaraco` está preenchida

##### Para DUIMP (Declaração Única de Importação):

ICMS é considerado pendente **APENAS** quando a situação da DUIMP for uma destas:
- ✅ `DESEMBARACADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS`
- ✅ `ENTREGA_ANTECIPADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS`

**IMPORTANTE:** Para DUIMP, outras situações como `DESEMBARACADA_CARGA_ENTREGUE` **NÃO** indicam pendência de ICMS.

#### 2.1.3. Valores que NÃO Indicam Pendência

⚠️ **CRÍTICO:** O sistema aplica validação rigorosa para garantir que apenas valores que realmente indicam pendência ativa sejam considerados.

**Valores excluídos (não são considerados pendência):**
- `None` ou vazio
- "OK" (em qualquer case)
- "PAGO" (em qualquer case)
- "RESOLVID" ou "RESOLVIDO" (em qualquer case)
- "LIQUIDAD" ou "LIQUIDADO" (em qualquer case)
- "QUITAD" ou "QUITADO" (em qualquer case)
- "FINALIZAD" ou "FINALIZADO" (em qualquer case)
- "N/A" (em qualquer case)
- "NULL" (em qualquer case)
- "NONE" (em qualquer case)

**Validação aplicada:**
- O sistema verifica se o campo `pendencia_icms` contém qualquer um dos valores acima (case-insensitive)
- Se contiver, o processo **NÃO** é considerado como tendo pendência de ICMS
- Esta validação é aplicada tanto na query SQL quanto na lógica Python para garantir consistência

#### 2.1.4. Quando a Aplicação Avisa sobre ICMS

A aplicação **avisa sobre pendência de ICMS** quando:

1. **Condições obrigatórias (todas devem ser verdadeiras):**
   - ✅ Campo `pendencia_icms` existe e não é `None` nem vazio
   - ✅ Campo `pendencia_icms` **passa na validação rigorosa** (não contém valores que indicam resolução/pagamento - ver seção 2.1.3)
   - ✅ Processo tem DI ou DUIMP registrada (`numero_di` ou `numero_duimp` não vazios)

2. **Condição adicional para DI:**
   - ✅ DI está desembaraçada (ver seção 2.1.2)

3. **Condição adicional para DUIMP:**
   - ✅ Situação da DUIMP é `DESEMBARACADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS` OU
   - ✅ Situação da DUIMP é `ENTREGA_ANTECIPADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS`

⚠️ **IMPORTANTE:** A validação é aplicada em duas etapas:
1. **Query SQL:** Filtra processos com `pendencia_icms` que não contém valores excluídos
2. **Lógica Python:** Valida novamente antes de incluir na lista de pendências

Isso garante que processos com valores históricos ou informativos (ex: "RESOLVIDO", "LIQUIDADO") não apareçam como pendentes, mesmo que o campo esteja preenchido no banco de dados.

**Onde aparece:**
- Dashboard "O que temos pra hoje?" → Seção "⚠️ PENDÊNCIAS ATIVAS"
- Função `obter_pendencias_ativas()` → Retorna processos com pendência de ICMS
- Consulta "quais processos têm pendência?" → Lista processos com ICMS pendente

**Ação sugerida:** "Verificar pagamento"

#### 2.1.5. Notificação de ICMS Pago

Quando uma pendência de ICMS é resolvida:
- **Antes:** `pendencia_icms` era "PENDENTE", "TRUE", "1", "SIM"
- **Agora:** `pendencia_icms` é `None`, vazio, "OK", "PAGO", etc.

**Tipo de notificação:** `pendencia_icms_resolvida`
**Título:** "Pendência de ICMS removida"

---

### 2.2. Pendência de AFRMM

#### 2.2.1. Definição

AFRMM (Adicional ao Frete para Renovação da Marinha Mercante) é uma pendência quando:
- Campo `pendencia_afrmm` no JSON do CE é `True`, `1`, ou string `"true"`

#### 2.2.2. Localização no JSON

- `dados_completos_json.ce[].pendencia_afrmm`
- Pode estar em `ce` (objeto) ou `ce` (array com primeiro elemento)

#### 2.2.3. Quando a Aplicação Avisa sobre AFRMM

A aplicação **avisa sobre pendência de AFRMM** quando:

1. **Condições obrigatórias (todas devem ser verdadeiras):**
   - ✅ Processo tem CE (campo `ce` existe no JSON)
   - ✅ Campo `pendencia_afrmm` no JSON do CE é:
     - `True` (boolean) OU
     - `1` (integer) OU
     - `"true"` (string, case-insensitive)

**Onde aparece:**
- Dashboard "O que temos pra hoje?" → Seção "⚠️ PENDÊNCIAS ATIVAS"
- Função `obter_pendencias_ativas()` → Retorna processos com pendência de AFRMM
- Consulta "quais processos têm pendência?" → Lista processos com AFRMM pendente

**Ação sugerida:** "Verificar pagamento"

**IMPORTANTE:** AFRMM só se aplica a processos **marítimos** (que têm CE).

#### 2.2.4. Notificação de AFRMM Pago

Quando AFRMM é pago:
- **Antes:** `pendencia_afrmm` era `True`, `1`, ou `"true"`
- **Agora:** `pendencia_afrmm` é `False`, `0`, `None`, ou `"false"`

**Tipo de notificação:** `afrmm_pago`
**Título:** "AFRMM pago"

---

### 2.3. Pendência de LPCO

#### 2.3.1. Definição

LPCO (Licença de Processamento de Carga no Exterior) é considerado pendente quando:

1. **LPCO não está deferido:**
   - `situacao_lpco` não contém "DEFERIDO" (em qualquer case)
   - Mesmo sem exigência, se não está deferido, é pendência bloqueante

2. **LPCO tem exigência:**
   - Campo `exigencia` está preenchido

#### 2.3.2. Localização no JSON

- `dados_completos_json.lpco[].situacao` ou `dados_completos_json.lpco[].situacao_lpco`
- `dados_completos_json.lpcoDetails[].situacao` ou `dados_completos_json.lpcoDetails[].situacao_lpco`
- `dados_completos_json.lpco[].exigencia` ou `dados_completos_json.lpcoDetails[].exigencia`

#### 2.3.3. Quando a Aplicação Avisa sobre LPCO

A aplicação **avisa sobre pendência de LPCO** quando:

1. **Condições obrigatórias (pelo menos uma deve ser verdadeira):**
   - ✅ LPCO não está deferido:
     - Campo `situacao` ou `situacao_lpco` existe E
     - Campo `situacao` ou `situacao_lpco` **NÃO** contém "deferido" (case-insensitive)
     - **Mesmo sem exigência**, se não está deferido, é considerado pendência bloqueante
   - ✅ OU LPCO tem exigência:
     - Campo `exigencia` está preenchido (não é `None`, vazio, ou string vazia)

**Onde aparece:**
- Dashboard "O que temos pra hoje?" → Seção "⚠️ PENDÊNCIAS ATIVAS" (prioridade alta)
- Função `obter_pendencias_ativas()` → Retorna processos com pendência de LPCO
- Consulta "quais processos têm pendência?" → Lista processos com LPCO pendente

**Ação sugerida:** "Verificar documentação"

**IMPORTANTE:** 
- LPCO não deferido é **bloqueante** - impede registro de DI/DUIMP
- Se LPCO tem exigência, a descrição da pendência mostra o texto da exigência
- Se LPCO não está deferido mas não tem exigência, a descrição mostra: "LPCO [número] não deferido - Situação: [situação]"

#### 2.3.4. Notificação de Mudança de Status do LPCO

Quando status do LPCO muda:
- **Antes:** `situacao_lpco` era diferente
- **Agora:** `situacao_lpco` tem um novo valor válido (não `None` ou vazio)

**Tipo de notificação:** `status_lpco_mudou`
**Título:** "Status do LPCO alterado"

---

### 2.4. Pendência de Frete

#### 2.4.1. Definição

Frete é considerado pendente quando:
- Campo `pendencia_frete` na tabela `processos_kanban` é `1` (True/Boolean)

#### 2.4.2. Origem dos Dados

A pendência de frete pode vir de **múltiplas fontes**, na seguinte ordem de prioridade:

1. **JSON do Kanban (fonte primária):**
   - Campo: `pendenciaFrete` (camelCase) na raiz do JSON
   - Localização: `json_data.get('pendenciaFrete')`
   - Tipo: Boolean (`True`/`False`) ou pode ser `1`/`0` (integer)

2. **Dados do CE (Conhecimento de Embarque - marítimo):**
   - Campo: `ce[].pendencia_frete` no JSON completo
   - Localização: `dados_completos_json.ce[].pendencia_frete`
   - Tipo: Boolean, integer ou string
   - ⚠️ **LIMITAÇÃO CRÍTICA:** Apenas CEs do tipo **"BL"** podem ter pendência de frete
   - ⚠️ CEs do tipo **"HBL"** sempre retornam `pendenciaFrete: []` (array vazio) e **NÃO são considerados** para verificação de pendência

3. **Dados do CCT (Conhecimento de Carga Aérea - aéreo):**
   - Campo: `cct[].pendencia_frete` no JSON completo
   - Localização: `dados_completos_json.cct[].pendencia_frete`
   - Tipo: Boolean, integer ou string

**Normalização:**
- O sistema normaliza o valor para boolean (`True`/`False`) antes de salvar
- Valores aceitos como `True`: `True`, `1`, `"true"`, `"1"`, `"sim"`, `"yes"`
- Valores aceitos como `False`: `False`, `0`, `"false"`, `"0"`, `None`, `""`

**Validação de Tipo do CE:**
- Antes de processar `pendenciaFrete`, o sistema verifica o campo `tipo` do CE
- Se `tipo == "BL"` → Processa pendência de frete normalmente
- Se `tipo == "HBL"` → **Ignora** `pendenciaFrete` (sempre retorna `False`, não processa)
- Se `tipo` não informado ou diferente → **Ignora** `pendenciaFrete` (assume `False`)

#### 2.4.3. Quando a Aplicação Avisa sobre Frete

A aplicação **avisa sobre pendência de frete** quando:

1. **Condição obrigatória:**
   - ✅ Campo `pendencia_frete` na tabela `processos_kanban` é `1` (True)

**Validação aplicada:**
- **Query SQL:** `pendencia_frete = 1` (busca direta na tabela)
- **Lógica Python:** Verifica se `row['pendencia_frete']` é `True` ou `1`

**Onde aparece:**
- Dashboard "O que temos pra hoje?" → Seção "⚠️ PENDÊNCIAS ATIVAS"
- Função `obter_pendencias_ativas()` → Retorna processos com pendência de frete
- Consulta "quais processos têm pendência?" → Lista processos com frete pendente
- Consulta específica do processo → Exibe "Frete: Pendente" se `tem_pendencias` é `True` e `pendencia_frete` é `True`

**Ação sugerida:** "Verificar pagamento"

**IMPORTANTE:** 
- Pendência de frete pode ocorrer em qualquer modal (marítimo, aéreo, rodoviário)
- Para processos marítimos, a pendência vem do CE
- ⚠️ **LIMITAÇÃO:** Apenas CEs do tipo **"BL"** podem ter pendência de frete
- ⚠️ CEs do tipo **"HBL"** não suportam verificação de pendência de frete (sempre retornam array vazio)
- Para processos aéreos, a pendência vem do CCT
- O campo é salvo como BOOLEAN na tabela (`0` = False, `1` = True)

#### 2.4.3. Notificação de Frete Pago

Quando pendência de frete é resolvida:
- **Antes:** `pendencia_frete` era `1` (True)
- **Agora:** `pendencia_frete` é `0` (False) ou `None`

**Tipo de notificação:** `frete_pago`
**Título:** "Pendência de frete removida"

---

## 3. Regras de Status/Situação

### 3.1. Status da DI

#### 3.1.1. Detecção de Mudança

Status da DI muda quando:
- `situacao_di` (anterior) ≠ `situacao_di` (novo) E
- `situacao_di` (novo) não é `None`

#### 3.1.2. Notificação de Mudança de Status da DI

**Tipo de notificação:** `status_di_mudou`
**Título:** "Status da DI alterado"
**Mensagem:** Inclui situação anterior e nova

---

### 3.2. Status da DUIMP

#### 3.2.1. Detecção de Mudança

Status da DUIMP muda quando:
- Status extraído de `dados_completos_json.duimp[].situacao` (anterior) ≠ (novo) E
- Status (novo) não é `None`

**IMPORTANTE:** Apenas DUIMPs de **produção** são consideradas:
- `duimp[].vinda_do_ce == True` OU
- `duimp[].ambiente == 'producao'`

#### 3.2.2. Notificação de Mudança de Status da DUIMP

**Tipo de notificação:** `status_duimp_mudou`
**Título:** "Status da DUIMP alterado"
**Mensagem:** Inclui situação anterior e nova

---

### 3.3. Status do CE

#### 3.3.1. Detecção de Mudança

Status do CE muda quando:
- Status extraído (anterior) ≠ Status extraído (novo) E
- Status (novo) não é vazio

#### 3.3.2. Locais Onde Buscar Status do CE

1. **DTO:** `dto.situacao_ce`
2. **Dados completos:** `dados_completos_json.situacaoCargaCe` ou `dados_completos_json.situacao_ce`
3. **Container details:** `dados_completos_json.containerDetailsCe[0].situacao` ou `dados_completos_json.containerDetailsCe[0].operacao`

#### 3.3.3. Notificação de Mudança de Status do CE

**Tipo de notificação:** `status_ce_mudou`
**Título:** "Status do CE alterado"
**Mensagem:** Inclui situação anterior e nova

**Exemplos de status:**
- `MANIFESTADA`
- `ARMAZENADA`
- `DESCARREGADA`
- `VINCULADA_A_DOCUMENTO_DE_DESPACHO`
- etc.

---

## 4. Regras de Notificações

### 4.1. Tipos de Notificações

1. `chegada` - Chegada confirmada
2. `status_di` - Mudança de status da DI
3. `status_duimp` - Mudança de status da DUIMP
4. `status_ce` - Mudança de status do CE
5. `status_lpco` - Mudança de status do LPCO
6. `pagamento_afrmm` - AFRMM pago
7. `pendencia_icms_resolvida` - Pendência de ICMS removida
8. `pendencia_frete_resolvida` - Pendência de frete removida
9. `pendencia_resolvida` - Pendências gerais resolvidas
10. `eta_alterado` - ETA alterado
11. `pagamentos_necessarios` - DI/DUIMP desembaraçada - verificar pagamentos (ICMS, AFRMM, Frete)

### 4.2. Quando Notificações São Criadas

Notificações são criadas quando:
1. Há uma mudança detectada entre versão anterior e nova do processo
2. A mudança atende aos critérios específicos de cada tipo de notificação
3. O processo não é novo (processos novos não geram notificações na primeira vez)

### 4.3. Processo Entregue

Um processo é considerado **ENTREGUE** quando:
- `situacao_ce` contém "ENTREGUE" OU
- `situacao_entrega` contém "ENTREGUE" OU
- `dados_completos_json.situacaoCargaCe` contém "ENTREGUE" OU
- `dados_completos_json.situacaoEntregaCarga` contém "ENTREGUE"

**IMPORTANTE:** Mesmo processos entregues podem receber notificações de pendências resolvidas (usuário quer saber quando pendências são resolvidas, mesmo em processos finalizados).

### 4.4. Notificação de Pagamentos Necessários (DI/DUIMP Desembaraçada)

#### 4.4.1. Quando é Criada

Esta notificação é criada **automaticamente** quando:
1. ✅ DI ou DUIMP **mudou de status** para desembaraçada OU
2. ✅ DI ou DUIMP mudou para **"ENTREGA AUTORIZADA SEM PROSSEGUIMENTO DO DESPACHO"**

⚠️ **CRÍTICO:** A notificação só é criada se o status **mudou** (não estava desembaraçada antes e agora está).

#### 4.4.2. Verificações Realizadas

Quando DI/DUIMP desembaraça, a aplicação verifica automaticamente:

1. **ICMS:**
   - ✅ **Pago/Exonerado:** Se `pendencia_icms` é `"OK"`, `"PAGO"`, `"EXONERADO"` ou `"EXONERADA"`
   - ⚠️ **Pendente:** Se `pendencia_icms` tem outro valor (ex: `"Pendente"`, `"Aguardando pagamento"`)
   - ⚠️ **Sem informação:** Se `pendencia_icms` é `None` ou vazio

2. **AFRMM (apenas marítimo):**
   - ✅ **Pago:** Se extraído dos dados do CE como pago
   - ⚠️ **Pendente:** Se não está pago (obrigatório para retirada em modal marítimo)

3. **Frete:**
   - ✅ **Pago:** Se `pendencia_frete` é `0` (False) ou `None`
   - ⚠️ **Pendente:** Se `pendencia_frete` é `1` (True)
   - ℹ️ **Sem informação:** Se `pendencia_frete` é `None` (não verificado)

#### 4.4.3. Conteúdo da Notificação

**Tipo de notificação:** `pagamentos_necessarios`
**Título:** `💰 {processo_referencia}: {DI/DUIMP} Desembaraçada - Verificar Pagamentos`

**Mensagem inclui:**
- Número da DI/DUIMP desembaraçada
- Status de cada pagamento (ICMS, AFRMM, Frete)
- Ações necessárias para cada pendência
- Resumo final:
  - ✅ **"TODOS OS PAGAMENTOS OK - CARGA PODE SER RETIRADA"** (se tudo está pago)
  - ⚠️ **"PENDÊNCIAS: [lista]"** (se há pendências)

#### 4.4.4. Regra de Negócio: Retirada da Carga

⚠️ **CRÍTICO:** A carga **só pode sair do porto** quando **TODOS** os seguintes estão OK:

1. **ICMS:** ✅ Pago ou exonerado
2. **AFRMM:** ✅ Pago (quando aplicável - apenas marítimo)
3. **Frete:** ✅ Pago (quando há informação de pendência)

**Exemplo de mensagem:**
```
💰 ALH.0168/25: DI Desembaraçada - Verificar Pagamentos

**DI Desembaraçada:** 25BR12345678901234567890123456789012345678901234

💰 **PAGAMENTOS NECESSÁRIOS PARA RETIRADA DA CARGA:**

📋 **ICMS:**
   ⚠️ **PENDENTE:** Pendente
   💡 **AÇÃO:** Solicitar pagamento ou exoneração do ICMS

🚢 **AFRMM:**
   ⚠️ **PENDENTE** - Obrigatório para retirada
   💡 **AÇÃO:** Solicitar pagamento do AFRMM

🚚 **Frete:**
   ✅ Pago - OK para retirada

⚠️ **PENDÊNCIAS:** ICMS, AFRMM
💡 Resolva as pendências acima para liberar a retirada da carga.
```

#### 4.4.5. Quando ICMS Pode Ser Pago/Exonerado

⚠️ **REGRA CRÍTICA:** ICMS **só pode ser pago ou exonerado** quando:
- DI ou DUIMP está com situação **"desembaraçada"** OU
- DI ou DUIMP está com situação **"ENTREGA AUTORIZADA SEM PROSSEGUIMENTO DO DESPACHO"**

❌ **NÃO pode ser pago antes** desses status.

#### 4.4.6. Detecção de Desembaraço

**Para DI:**
- Verifica `situacao_di` e `situacao_entrega`
- Status considerados desembaraçados:
  - Contém `"DESEMBARAC"` (case-insensitive)
  - Contém `"ENTREGA AUTORIZADA"` (case-insensitive)

**Para DUIMP:**
- Verifica `dados_completos_json.duimp[].situacao`
- Status considerados desembaraçados:
  - Contém `"DESEMBARAC"` (case-insensitive)
  - Contém `"ENTREGA AUTORIZADA"` (case-insensitive)

**Lógica de detecção:**
- Compara status anterior vs. novo
- Só cria notificação se **não estava desembaraçada antes** e **agora está**

---

### 4.5. Text-to-Speech (TTS)

#### 4.4.1. Geração de Áudio

Todas as notificações podem ter áudio TTS gerado automaticamente:
- **Serviço:** OpenAI TTS API
- **Modelo padrão:** `tts-1` (rápido) ou `tts-1-hd` (qualidade)
- **Voz padrão:** `nova` (configurável via `OPENAI_TTS_VOICE`)
- **Formato:** MP3

#### 4.4.2. Formatação de Texto

Texto é formatado para pronúncia natural:
- **Processos:** `ALH.0166/25` → "ALH zero um seis seis"
- **Ano:** Só é mencionado se for anterior ao vigente (ex: `/24` → "barra vinte e quatro")
- **Números:** Convertidos para extenso (ex: `0166` → "zero um seis seis")
- **Texto combinado:** Título + mensagem são processados juntos

#### 4.4.3. Cache de Áudio

- **Ativado por padrão:** `OPENAI_TTS_CACHE_ENABLED=true`
- **Localização:** `downloads/tts/`
- **Duração:** 7 dias (configurável via `OPENAI_TTS_CACHE_DAYS`)
- **Hash:** Baseado em texto + voz para evitar duplicatas
- **Limpeza automática:** Arquivos antigos são removidos automaticamente

#### 4.4.4. Reprodução de Áudio

- **Fila de áudio:** Sistema `AudioQueue` gerencia reprodução sequencial
- **Autoplay:** Requer interação do usuário (política do navegador)
- **Desbloqueio:** Primeira interação (click, keydown, touchstart) desbloqueia áudio
- **Retry:** Tentativa automática após 100ms se autoplay falhar
- **Mute:** Respeita preferência do usuário (botão de mute)

#### 4.4.5. Configuração

Variáveis de ambiente:
- `OPENAI_TTS_ENABLED`: `true` ou `false` (padrão: `false`)
- `OPENAI_TTS_VOICE`: `nova`, `alloy`, `echo`, `fable`, `onyx`, `shimmer` (padrão: `nova`)
- `OPENAI_TTS_MODEL`: `tts-1` ou `tts-1-hd` (padrão: `tts-1`)
- `OPENAI_TTS_CACHE_ENABLED`: `true` ou `false` (padrão: `true`)
- `OPENAI_TTS_CACHE_DAYS`: Número de dias (padrão: `7`)
- `DUIMP_AI_API_KEY`: Chave da API OpenAI (mesma usada para chat)

#### 4.4.6. Fluxo de Notificação com Áudio

1. Notificação é criada
2. Texto é formatado para TTS
3. Hash é gerado (texto + voz)
4. Cache é verificado
5. Se não existe, áudio é gerado via API
6. Áudio é salvo em `downloads/tts/`
7. URL é retornada (`/api/download/tts/{hash}.mp3`)
8. Frontend adiciona à fila de áudio
9. Áudio é reproduzido quando disponível

---

## 4.6. Regras de DTA (Declaração de Trânsito Aduaneiro)

### 4.6.1. Definição

**DTA (Declaração de Trânsito Aduaneiro)** = Documento que indica que a carga já chegou e está sendo removida para outro recinto alfandegado, onde será registrada uma DI ou DUIMP posteriormente.

⚠️ **IMPORTANTE:** DTA é **opcional** - o cliente decide se deseja remover a carga do porto do Rio para outro recinto alfandegado.

### 4.6.2. Campos no JSON Kanban

Campos que indicam DTA:
- `documentoDespacho` = `"DTA"` (tipo de documento)
- `numeroDocumentoDespacho` = número da DTA (ex: `"2406081715"`)

⚠️ **IMPORTANTE:** O JSON mantém histórico - quando um processo registra DI ou DUIMP, os campos `documentoDespacho` e `numeroDocumentoDespacho` são atualizados, mas **não apagam** os dados da DTA. O JSON pode conter ambos simultaneamente.

### 4.6.3. Regra Crítica: Prioridade DI/DUIMP sobre DTA

⚠️ **REGRA DE NEGÓCIO CRÍTICA:** Na extração dos dados do JSON, **DI/DUIMP sempre prevalece sobre DTA**.

**Lógica de extração no DTO (`ProcessoKanbanDTO`):**

1. **Se `documentoDespacho = "DI"`:**
   - ✅ Preenche `numero_di` com `numeroDocumentoDespacho`
   - ❌ **NÃO** preenche `numero_dta` (DI prevalece)

2. **Se `documentoDespacho = "DUIMP"`:**
   - ✅ Preenche `numero_duimp` com `numeroDocumentoDespacho`
   - ❌ **NÃO** preenche `numero_dta` (DUIMP prevalece)

3. **Se `documentoDespacho = "DTA"`:**
   - ✅ Preenche `numero_dta` com `numeroDocumentoDespacho` **APENAS SE** não tiver DI nem DUIMP
   - ⚠️ Se já tiver DI ou DUIMP, **NÃO** preenche `numero_dta`

**Exemplo prático:**
- JSON tem `documentoDespacho = "DI"` e `numeroDocumentoDespacho = "25BR12345678901234567890123456789012345678901234"`
- Mesmo que o JSON tenha histórico com DTA, o DTO **NÃO** preenche `numero_dta`
- O processo **NÃO** aparece como "em DTA"
- O processo aparece com DI registrada

**Quando um processo ganha DI/DUIMP:**
1. `numero_di` ou `numero_duimp` é preenchido no banco
2. O processo **sai** da lista "em DTA" (filtro SQL exclui processos com DI/DUIMP)
3. A DTA **não aparece** mais na exibição (DI/DUIMP prevalece)
4. O processo passa a ter status de "registrado" (com DI/DUIMP)

### 4.6.4. Regra Crítica: Processo "em DTA"

Um processo só está **"em DTA"** quando:
1. ✅ Tem DTA (`numero_dta` não é `None` nem vazio) E
2. ✅ **NÃO tem** DI (`numero_di` é `None`, vazio ou `'/       -'`) E
3. ✅ **NÃO tem** DUIMP (`numero_duimp` é `None` ou vazio)

**Exemplo:**
- `MV5.0002/25` tem DTA `2505722794` **E** DI `25BR12345678901234567890123456789012345678901234`
- ❌ **NÃO** aparece como "em DTA" (prevalece a DI)

### 4.6.5. Fluxo de DTA

1. **Carga chega** ao porto do Rio
2. **Cliente decide** remover para outro recinto (opcional)
3. **DTA é registrada** → processo aparece como "em DTA"
4. **Carga é removida** para outro recinto
5. **DI ou DUIMP é registrada** → processo **sai** da lista "em DTA"
6. **Processo aparece** como "pronto para registro" ou "registrado"

### 4.6.6. Listagem de Processos em DTA

Função: `listar_processos_em_dta(categoria, limit)`

**Filtros aplicados:**
- `numero_dta IS NOT NULL AND numero_dta != ''`
- `numero_di IS NULL OR numero_di = '' OR numero_di = '/       -'`
- `numero_duimp IS NULL OR numero_duimp = ''`
- `dados_completos_json IS NOT NULL AND dados_completos_json != ''`

**Ordenação:** Por `atualizado_em` (mais recente primeiro)

**Limite padrão:** 200 processos

### 4.6.7. Exibição no Dashboard

Processos em DTA aparecem em seção separada:
- **Título:** "🚚 PROCESSOS EM DTA"
- **Descrição:** "Cargas em trânsito para outro recinto alfandegado"
- **Informações exibidas:**
  - Número do processo
  - Número da DTA
  - Data de chegada
  - Status do CE
  - Modal (com emoji: 🚚 Rodoviário, ✈️ Aéreo, 🚢 Marítimo)
  - **CE:** Só exibido se modal for "Marítimo" (rodoviário não tem CE)

---

## 5. Regras de ETA (Estimated Time of Arrival)

### 5.1. Definição

**ETA (Estimated Time of Arrival)** = Previsão de chegada da carga ao porto/aeroporto de destino.

⚠️ **IMPORTANTE:** ETA é uma **previsão**, não uma confirmação. A chegada confirmada é indicada por `dataDestinoFinal` (ou `dataHoraChegadaEfetiva` para aéreo).

### 5.2. Fontes de ETA e Priorização

O sistema possui **duas fontes principais** de ETA:

1. **ShipsGo (POD - Port of Discharge):**
   - Fonte: Tracking de navios via API ShipsGo
   - Armazenamento: Tabela `shipsgo_tracking` (campo `eta_iso`)
   - Características: Mais atualizado, reflete posição real do navio
   - Prioridade: **ALTA** (usar quando disponível)

2. **ICTSI (Kanban):**
   - Fonte: JSON do Kanban (sistema interno)
   - Armazenamento: Tabela `processos_kanban` (campo `eta_iso`)
   - Características: Pode estar desatualizado, vem do sistema interno
   - Prioridade: **BAIXA** (usar apenas como fallback)

#### 5.2.1. Regra de Priorização

⚠️ **CRÍTICO:** Sempre priorizar ETA do ShipsGo (POD) sobre ETA do ICTSI (Kanban).

**Ordem de prioridade:**
1. ✅ **ETA do ShipsGo (POD)** - se disponível na tabela `shipsgo_tracking`
2. ✅ **ETA do ICTSI (Kanban)** - apenas se ShipsGo não tiver dados

**Implementação:**
- Função `listar_processos_por_eta` busca dados do ShipsGo via `shipsgo_get_tracking_map()`
- Campo `fonte_eta` indica origem: `'shipsgo'` ou `'kanban'`
- Mantém compatibilidade com formato antigo (`shipsgo` dict)

**Exemplo:**
```
Processo UPI.0003/25:
- ETA ICTSI (Kanban): 17/12/2025 às 12:00
- ETA ShipsGo (POD): 22/12/2025 às 12:00
- Resultado: Usar ETA ShipsGo (22/12) - mais atualizado
```

### 5.3. Determinação do ETA do JSON (Prioridade de Fontes)

Quando o filtro é `'hoje'`, o sistema usa a **mesma lógica** de `obter_processos_chegando_hoje` para determinar o ETA mais atualizado do JSON:

**Ordem de prioridade (do JSON):**
1. ✅ **Evento DISC (Discharge/Descarga)** do ShipsGo no porto de destino (POD)
   - Localização: `shipgov2.eventos[]` onde `atual_evento == 'DISC'`
   - Campo: `atual_data_evento` do último evento DISC no porto de destino
   - **Motivo:** DISC indica quando a carga foi descarregada no porto de destino

2. ✅ **dataPrevisaoChegada**
   - Localização: Raiz do JSON (`dataPrevisaoChegada`)
   - **Motivo:** Previsão oficial de chegada

3. ✅ **Último evento ARRV (Arrival)** do ShipsGo
   - Localização: `shipgov2.eventos[]` onde `atual_evento == 'ARRV'`
   - Campo: `atual_data_evento` do último evento ARRV
   - **Motivo:** Indica chegada do navio ao porto

4. ✅ **shipgov2.destino_data_chegada**
   - Localização: `shipgov2.destino_data_chegada`
   - **Motivo:** Pode ser histórico antigo, usar apenas como fallback

5. ✅ **eta_iso da tabela** (último fallback)
   - Localização: Tabela `processos_kanban`, campo `eta_iso`
   - **Motivo:** Pode estar desatualizado ou ser do ICTSI

### 5.4. Regra de "Chegando Hoje"

#### 5.4.1. Critério de Inclusão

Um processo aparece em **"chegando hoje"** quando:

✅ **Condições obrigatórias (TODAS devem ser verdadeiras):**
1. ETA = hoje (usando lógica de priorização acima)
2. **NÃO** tem `dataDestinoFinal = hoje` (já chegou, deve aparecer em "PRONTOS PARA REGISTRO")
3. **NÃO** tem `situacao_ce == 'ENTREGUE'`
4. **NÃO** tem `situacao_entrega == 'ENTREGUE'`
5. **NÃO** tem DI registrada (`numero_di` está NULL/vazio)
6. **NÃO** tem DUIMP registrada (`numero_duimp` está NULL/vazio)

#### 5.4.2. Verificação de Chegada Confirmada

Para verificar se um processo **já chegou hoje**, o sistema verifica:

1. **Campo da tabela:** `data_destino_final` da tabela `processos_kanban`
2. **Campo do JSON:** `dataDestinoFinal` do JSON completo
3. **Modal Aéreo:** Se modal é "Aéreo", verifica também `dataHoraChegadaEfetiva`

**Regra:** Se `dataDestinoFinal = hoje`, o processo **já chegou** e **NÃO** deve aparecer em "chegando hoje".

#### 5.4.3. Alinhamento entre Funções

⚠️ **CRÍTICO:** As funções `listar_processos_por_eta` (com filtro `'hoje'`) e `obter_processos_chegando_hoje` **DEVEM retornar o mesmo resultado**.

**Garantia de consistência:**
- Ambas usam a mesma lógica de determinação de ETA (prioridade de fontes do JSON)
- Ambas verificam `dataDestinoFinal` da mesma forma
- Ambas aplicam os mesmos critérios de inclusão/exclusão

**Exemplo:**
```
Processo MSS.0029/25:
- ETA da tabela: 17/12/2025
- ETA do JSON (DISC): 22/12/2025
- dataDestinoFinal: NULL
- Resultado: NÃO incluir em "chegando hoje" (ETA do JSON = 22/12, não é hoje)
```

### 5.5. Exibição do ETA

Quando o ETA é exibido ao usuário:
- ✅ **Formato:** `DD/MM/AAAA às HH:MM` (ex: "17/12/2025 às 12:00")
- ✅ **Fonte indicada:** Campo `fonte_eta` indica se veio do ShipsGo ou Kanban (para debug/logs)
- ✅ **Porto e Navio:** Sempre exibidos junto com o ETA quando disponíveis
- ✅ **Status:** Status do navio (ex: "SAILING") é exibido quando disponível

### 5.6. Atualização do ETA

O ETA é atualizado:
- ✅ **Automaticamente:** Via sincronização do Kanban (atualiza `eta_iso` da tabela)
- ✅ **Via ShipsGo:** Quando dados do ShipsGo são consultados (atualiza `shipsgo_tracking`)
- ✅ **Priorização:** Sistema sempre usa o ETA mais atualizado disponível

### 5.7. Detecção de Mudança de ETA

ETA muda quando:
1. **Antes:** `eta_iso` era `None` e **Agora:** `eta_iso` tem valor OU
2. **Antes:** `eta_iso` tinha valor e **Agora:** `eta_iso` é `None` OU
3. **Ambos existem:** Diferença entre datas é **maior que 1 hora**

⚠️ **IMPORTANTE:** Mudanças menores que 1 hora não geram notificação (para evitar notificações por pequenas variações).

### 5.8. Notificação de ETA Alterado

**Tipo de notificação:** `eta_alterado`
**Título:** "ETA alterado"
**Mensagem:** Inclui ETA anterior e novo

### 5.9. Cálculo de Atraso

Atraso é calculado quando:
- ETA novo > ETA anterior
- Diferença em dias = (ETA novo - ETA anterior).days

---

## 6. Regras de Categorização

### 6.1. Definição de Categoria

Categoria = Prefixo do processo de referência (ex: `ALH.0166/25` → categoria `ALH`).

### 6.2. Categorias Padrão

Categorias conhecidas são armazenadas na tabela `categorias_processo`:
- `ALH`, `BND`, `DMD`, `GYM`, `MV5`, `SLL`, `GLT`, `BDM`, `NTM`, `VDM`, `MSS`, etc.

### 6.3. Aprendizado Dinâmico

Novas categorias são aprendidas automaticamente quando um processo com categoria desconhecida é processado.

---

## 7. Regras de Processos Prontos para Registro

### 7.1. Definição

Processo está **pronto para registro** quando:
1. ✅ Carga **chegou** ao destino final (tem `dataDestinoFinal` ou `dataHoraChegadaEfetiva`) E
2. ✅ **NÃO tem** DI registrada (`numero_di` é `None`, vazio, ou `'/       -'`) E
3. ✅ **NÃO tem** DUIMP registrada (ver seção 10 para detalhes) E
4. ✅ **NÃO está em DTA** (processos em DTA são listados separadamente) E
5. ✅ Tem `dados_completos_json` preenchido

⚠️ **IMPORTANTE:** 
- Processos em DTA **NÃO** aparecem como "prontos para registro", pois estão em trânsito para outro recinto onde será registrada a DI/DUIMP.
- Apenas verificar se tem número de DUIMP **NÃO é suficiente**. É necessário verificar se a DUIMP está **registrada** (situação indica registro). Ver seção 10 para detalhes.

### 7.2. Filtros Adicionais

- **Por categoria:** Filtrar processos que começam com prefixo específico (ex: `ALH.%`)
- **Por data:** Filtrar por data de chegada (dias retroativos ou intervalo de datas)
- **Limite:** Máximo de processos retornados (padrão: 200)

### 7.3. Ordenação

Processos são ordenados por:
- Data de chegada (mais recente primeiro)

---

## 8. Regras de Fechamento do Dia

### 8.1. Definição

**Fechamento do dia** = Resumo de todas as movimentações que aconteceram no dia atual (não é planejamento, é histórico do que já aconteceu).

⚠️ **IMPORTANTE:** Fechamento do dia é diferente de "O que temos pra hoje" (dashboard):
- **Fechamento do dia:** Mostra o que **JÁ ACONTECEU** hoje (histórico)
- **Dashboard "O que temos pra hoje":** Mostra o que **TEMOS PRA HOJE** (planejamento)

### 8.2. O que é Incluído no Fechamento do Dia

O fechamento do dia lista **apenas** movimentações que aconteceram **hoje**:

1. **Processos que chegaram hoje:**
   - `data_destino_final = hoje` OU
   - `data_armazenamento = hoje` (processos armazenados hoje)

2. **Processos desembaraçados hoje:**
   - `data_desembaraco = hoje` E
   - Situação contém "DESEMBARAC" ou "ENTREGUE"

3. **DIs/DUIMPs registradas hoje:**
   - **DI:** `data_hora_registro = hoje` (tabela `dis_cache`)
   - **DUIMP:** 
     - `criado_em = hoje` (tabela `duimps`) OU
     - `data_registro_mais_recente = hoje` (JSON do Kanban) OU
     - `identificacao.dataRegistro = hoje` (payload da DUIMP)

4. **Mudanças de status hoje:**
   - **CE:** Notificações criadas hoje com tipo `status_ce` ou `chegada` ou `armazenamento`
   - **DI:** Notificações criadas hoje com tipo `status_di`
   - **DUIMP:** 
     - Notificações criadas hoje com tipo `status_duimp` OU
     - `atualizado_em = hoje` na tabela `duimps` OU
     - Processo atualizado hoje com DUIMP e situação indica "REGISTRADA" ou "AGUARDANDO CANAL"

5. **Pendências resolvidas hoje:**
   - Notificações criadas hoje indicando resolução de pendências

### 8.3. Campos Utilizados para Detecção

#### Para DI Registrada:
- **SQL Server (fonte primária):**
  - Tabela: `Serpro.dbo.Di_Dados_Despacho`
  - Campo: `dataHoraRegistro`
  - Condição: `CAST(dataHoraRegistro AS DATE) = CAST(GETDATE() AS DATE)`
  - Ordenação: Por `dataHoraDesembaraco DESC` e `dataHoraRegistro DESC` (para obter status mais atual)
  
- **Cache SQLite (fallback):**
  - Tabela: `dis_cache`
  - Campo: `data_hora_registro`
  - Condição: `DATE(data_hora_registro) = DATE('now')`
  
- **JSON do Kanban:**
  - `dados_completos_json.ce[].documentoDespacho[].identificacao.dataRegistro` (para DIs de produção)
  - `dados_completos_json.di[].data_registro_mais_recente`

⚠️ **IMPORTANTE:** Para DIs registradas hoje, o sistema busca o **status mais atual** consultando novamente o SQL Server, ordenando por `dataHoraDesembaraco DESC` e `dataHoraRegistro DESC` para garantir que o status exibido no fechamento do dia seja o atual, não o status que a DI tinha no momento do registro.

#### Para DUIMP Registrada:
- **Tabela `duimps`:** `criado_em`, `atualizado_em`, `payload_completo.identificacao.dataRegistro`
- **JSON do Kanban:** `duimp[0].data_registro_mais_recente`, `duimp[0].situacao_duimp`
- **DocumentoDespacho:** `ce[].documentoDespacho[].identificacao.dataRegistro` (para DUIMPs de produção)
- **SQL Server (duimp.dbo.duimp_diagnostico):**
  - Campo: `data_geracao`
  - Condição: `CAST(data_geracao AS DATE) = CAST(GETDATE() AS DATE)`
  - Situação: `REGISTRADA_AGUARDANDO_CANAL` ou `CARGA REGISTRADA`

#### Para Mudança de Status DUIMP:
- **Tabela `duimps`:** `atualizado_em = hoje` E `status != 'rascunho'`
- **Kanban:** `atualizado_em = hoje` E `numero_duimp IS NOT NULL` E situação indica "REGISTRADA" ou "AGUARDANDO CANAL"
- **Notificações:** `criado_em = hoje` E `tipo_notificacao LIKE '%status_duimp%'`

### 8.4. Remoção de Duplicatas

- Processos que chegaram e foram armazenados no mesmo dia aparecem apenas uma vez
- DUIMPs criadas e registradas no mesmo dia aparecem apenas uma vez
- Mudanças de status são consolidadas por processo

### 8.5. Filtros Opcionais

- **Por categoria:** Filtrar movimentações de uma categoria específica (ex: `VDM`, `ALH`)
- **Por modal:** Filtrar apenas marítimo ou aéreo

---

## 9. Regras de ETA Alterado no Dashboard

### 9.1. Definição

**ETA alterado** = Mudança na previsão de chegada de um processo que ainda não chegou ao destino final.

⚠️ **IMPORTANTE:** Apenas processos que **AINDA NÃO CHEGARAM** aparecem nesta seção.

### 9.2. Quando um Processo Aparece como ETA Alterado

Um processo aparece como "ETA alterado" quando:

1. ✅ **Ainda não chegou:**
   - `data_destino_final IS NULL` (não tem data de chegada confirmada) E
   - Último ETA é futuro (>= hoje)

2. ✅ **Houve mudança significativa:**
   - Diferença entre primeiro ETA e último ETA é **maior que 1 dia**
   - Pode ser atraso (ETA novo > ETA anterior) ou adiantamento (ETA novo < ETA anterior)

3. ✅ **Processo é ativo/relevante:**
   - Está no cache do Kanban (`processos_kanban`)
   - Tem dados completos JSON com eventos do shipgov2

### 9.3. Processos que NÃO Aparecem

❌ **NÃO aparecem:**
- Processos que **já chegaram** (`data_destino_final IS NOT NULL`)
- Processos com mudança de ETA menor que 1 dia
- Processos sem eventos ARRV do porto de destino

### 9.4. Cálculo de Diferença

```
diferenca_dias = (ultimo_eta - primeiro_eta).days
```

- **Atraso:** `diferenca_dias > 0` → "atraso de X dia(s)"
- **Adiantamento:** `diferenca_dias < 0` → "adiantado X dia(s)"

### 9.5. Fontes de ETA

1. **Primeiro ETA:**
   - `shipgov2.destino_data_chegada` OU
   - `dataPrevisaoChegada` OU
   - Primeiro evento ARRV do porto de destino

2. **Último ETA:**
   - Último evento ARRV do porto de destino OU
   - Evento ARRV mais recente (se não houver do porto de destino)

### 9.6. Objetivo

Mostrar processos que estão **atrasados ou adiantados para chegar**, permitindo ao usuário:
- Acompanhar mudanças na previsão de chegada
- Planejar ações baseadas em atrasos/adiantamentos
- Identificar processos que precisam de atenção

⚠️ **Processos que já chegaram** não aparecem aqui, pois não faz sentido mostrar ETA alterado para processos já finalizados.

---

## 10. Regras de Detecção de DUIMP Registrada

### 10.1. Definição

**DUIMP registrada** = DUIMP que foi registrada no Portal Único e tem situação indicando registro (ex: "REGISTRADA", "REGISTRADA AGUARDANDO CANAL").

⚠️ **IMPORTANTE:** Apenas verificar se tem número de DUIMP **NÃO é suficiente**. É necessário verificar se a DUIMP está **registrada** (tem situação de registro).

### 10.2. Quando uma DUIMP é Considerada Registrada

Uma DUIMP é considerada registrada quando **pelo menos uma** das seguintes condições é verdadeira:

1. **Situação da DUIMP indica registro:**
   - `duimp[0].situacao_duimp` contém "REGISTRADA" ou "AGUARDANDO" (case-insensitive) OU
   - `duimp[0].ultima_situacao` contém "REGISTRADA" ou "AGUARDANDO" (case-insensitive) OU
   - `duimp[0].situacao_duimp_agr` contém "REGISTRADA" ou "AGUARDANDO" (case-insensitive)

2. **DocumentoDespacho indica DUIMP registrada:**
   - `ce[].documentoDespacho[].tipo = 'DUIMP'` E
   - `ce[].documentoDespacho[].situacao` contém "REGISTRADA" ou "AGUARDANDO" (case-insensitive)

3. **Data de registro está preenchida:**
   - `duimp[0].data_registro_mais_recente IS NOT NULL` OU
   - `identificacao.dataRegistro IS NOT NULL` (no payload da DUIMP)

### 10.3. Locais Onde Buscar

#### No JSON do Kanban:
- `dados_completos_json.duimp[0].situacao_duimp`
- `dados_completos_json.duimp[0].ultima_situacao`
- `dados_completos_json.duimp[0].situacao_duimp_agr`
- `dados_completos_json.duimp[0].data_registro_mais_recente`
- `dados_completos_json.ce[].documentoDespacho[].situacao` (para DUIMPs de produção)

#### Na Tabela `duimps`:
- `payload_completo.identificacao.dataRegistro`
- `status` (se contém "REGISTRADA" ou "AGUARDANDO")

### 10.4. Quando um Processo NÃO Aparece como "Pronto para Registro"

Um processo **NÃO aparece** como "pronto para registro" quando:

1. ✅ Tem DUIMP registrada (situação indica registro) OU
2. ✅ Tem DI registrada OU
3. ✅ Está em DTA (sem DI/DUIMP) OU
4. ✅ Já foi desembaraçado

⚠️ **CRÍTICO:** Apenas verificar `numero_duimp IS NOT NULL` **NÃO é suficiente**. É necessário verificar se a situação indica que está registrada.

### 10.5. Exemplo Prático

**Cenário:** VDM.0004/25 tem DUIMP `25BR00002369283` com situação `REGISTRADA_AGUARDANDO_CANAL`

**Comportamento:**
- ✅ Processo **NÃO aparece** em "prontos para registro"
- ✅ Processo aparece no "fechamento do dia" como DUIMP registrada hoje (se foi registrada hoje)
- ✅ Processo aparece no "fechamento do dia" como mudança de status DUIMP hoje (se status mudou hoje)

---

## 11. Regras de Detecção de Perguntas sobre Chegada

### 11.1. Definição

**Perguntas sobre chegada** = Consultas do usuário sobre processos que chegam em um período específico (hoje, amanhã, esta semana, este mês, etc.).

⚠️ **IMPORTANTE:** O sistema diferencia entre:
- **Perguntas genéricas** (sem período específico): "quais processos estão chegando?" → usa filtro `futuro` ou `mes`
- **Perguntas com período específico**: "o que tem pra chegar essa semana?" → usa filtro `semana`

### 11.1.1. Regra Crítica: Alinhamento entre `listar_processos_por_eta` e `obter_processos_chegando_hoje`

⚠️ **CRÍTICO:** Quando o filtro é `'hoje'`, a função `listar_processos_por_eta` **DEVE usar exatamente a mesma lógica** de `obter_processos_chegando_hoje` para garantir consistência.

**Regras aplicadas:**

1. **Determinação do ETA (prioridade de fontes):**
   - ✅ **1ª Prioridade:** Evento DISC (Discharge/Descarga) do ShipsGo no porto de destino (POD) - mais atualizado
   - ✅ **2ª Prioridade:** `dataPrevisaoChegada` do JSON
   - ✅ **3ª Prioridade:** Último evento ARRV (Arrival) do ShipsGo
   - ✅ **4ª Prioridade:** `shipgov2.destino_data_chegada` do JSON
   - ✅ **5ª Prioridade (fallback):** `eta_iso` da tabela `processos_kanban` (pode estar desatualizado)

2. **Verificação de chegada confirmada:**
   - ✅ Verificar `data_destino_final` da tabela
   - ✅ Se não encontrado, verificar `dataDestinoFinal` do JSON
   - ✅ Se modal é "Aéreo", verificar também `dataHoraChegadaEfetiva`

3. **Critério de inclusão em "chegando hoje":**
   - ✅ **Incluir APENAS se:** ETA = hoje **E** NÃO tem `dataDestinoFinal = hoje`
   - ❌ **NÃO incluir se:** Tem `dataDestinoFinal = hoje` (já chegou, deve aparecer em "PRONTOS PARA REGISTRO")

**Exemplo:**
- Processo tem ETA da tabela = 17/12/2025, mas ETA do JSON (DISC) = 22/12/2025
- Resultado: **NÃO incluir** em "chegando hoje" (usa ETA do JSON = 22/12, não é hoje)

### 11.1.2. Regra de Priorização do ETA: ShipsGo (POD) vs ICTSI

⚠️ **CRÍTICO:** O sistema possui duas fontes de ETA:
- **ShipsGo (POD):** ETA mais atualizado, vem do tracking de navios (tabela `shipsgo_tracking`)
- **ICTSI:** ETA do Kanban, pode estar desatualizado (tabela `processos_kanban`, campo `eta_iso`)

**Regra de priorização:**
1. ✅ **Sempre usar ETA do ShipsGo (POD)** quando disponível
2. ✅ **Fallback para ETA do ICTSI (Kanban)** apenas se ShipsGo não tiver dados
3. ✅ **Indicar fonte do ETA** no campo `fonte_eta` ('shipsgo' ou 'kanban')

**Implementação:**
- Função `listar_processos_por_eta` busca dados do ShipsGo via `shipsgo_get_tracking_map()`
- Prioriza `shipsgo_eta` sobre `kanban_eta`
- Mantém compatibilidade com formato antigo (`shipsgo` dict)

**Exemplo:**
- Processo UPI.0003/25:
  - ETA ICTSI (Kanban): 17/12/2025 às 12:00
  - ETA ShipsGo (POD): 22/12/2025 às 12:00
  - **Resultado:** Usar ETA ShipsGo (22/12) - mais atualizado e confiável

### 11.2. Padrões de Detecção

#### 11.2.1. Perguntas com Período Temporal Específico

O sistema detecta automaticamente quando o usuário menciona um período específico:

**Padrões detectados:**
- `"o que tem pra chegar essa semana?"` → `filtro_data='semana'`
- `"o que tem pra chegar hoje?"` → `filtro_data='hoje'`
- `"o que tem pra chegar amanhã?"` → `filtro_data='amanha'`
- `"o que tem pra chegar este mês?"` → `filtro_data='mes'`
- `"quais processos chegam essa semana?"` → `filtro_data='semana'`
- `"quais processos chegam esta semana?"` → `filtro_data='semana'`

**Função utilizada:** `listar_processos_por_eta(filtro_data, categoria=None, limite=500)`

#### 11.2.2. Detecção de Período Temporal

O sistema detecta automaticamente qual período foi mencionado:

1. **"Esta semana" / "Essa semana":**
   - Padrão: `r'\b(?:essa|esta|nessa|nesta)\s+semana\b'`
   - Filtro: `'semana'` (segunda-feira desta semana até domingo)

2. **"Hoje":**
   - Padrão: `r'\bhoje\b'`
   - Filtro: `'hoje'` (processos com ETA = hoje)

3. **"Amanhã":**
   - Padrão: `r'\b(?:amanhã|amanha)\b'`
   - Filtro: `'amanha'` (processos com ETA = amanhã)

4. **"Este mês" / "Neste mês":**
   - Padrão: `r'\b(?:este|neste)\s+m[êe]s\b'`
   - Filtro: `'mes'` (primeiro dia do mês até último dia do mês)

### 11.3. Regra Crítica: Não Usar Categoria do Contexto Anterior

⚠️ **CRÍTICO:** Quando o usuário pergunta sobre chegada **sem mencionar categoria específica**, o sistema **NÃO deve usar** categoria do contexto anterior.

**Exemplos:**
- ❌ **ERRADO:** Usuário pergunta "quais processos ALH temos?" → depois pergunta "o que tem pra chegar essa semana?" → sistema usa `categoria='ALH'` (herdado do contexto)
- ✅ **CORRETO:** Usuário pergunta "o que tem pra chegar essa semana?" → sistema usa `categoria=None` (retorna processos de TODAS as categorias)

**Implementação:**
- Pre-check específico detecta perguntas sobre chegada com período temporal
- Força uso de `listar_processos_por_eta` com `categoria=None` quando não mencionada explicitamente
- Retorna diretamente sem chamar IA (evita herdar contexto)

### 11.4. Quando Categoria É Usada

Categoria é usada **APENAS** quando o usuário menciona explicitamente na mensagem atual:

**Exemplos:**
- ✅ "o que tem pra chegar essa semana ALH?" → `categoria='ALH'`
- ✅ "quais processos BND chegam hoje?" → `categoria='BND'`
- ❌ "o que tem pra chegar essa semana?" (sem categoria) → `categoria=None`

### 11.5. Função de Ajuda

A função `obter_ajuda` inclui exemplos de perguntas sobre chegada:

**Seção "📊 DASHBOARD":**
- "O que temos pra hoje?"
- "Quais processos estão chegando hoje?"

**Seção "📋 AVERBAÇÃO":**
- "Averbacao processo BND.0030/25"
- "Averbação processo DMD.0045/25"

**Seção "📊 FECHAMENTO DO DIA":**
- "Finaliza o dia"
- "Fechamento do dia"
- "Finaliza o dia ALH" (filtra por categoria)

### 11.6. Fluxo de Processamento

1. **Pre-check:** Sistema detecta padrão de pergunta sobre chegada com período temporal
2. **Detecção de período:** Identifica qual período foi mencionado (semana, hoje, amanhã, mês)
3. **Detecção de categoria:** Extrai categoria apenas se mencionada explicitamente
4. **Chamada da função:** `listar_processos_por_eta(filtro_data, categoria, limite)`
5. **Retorno direto:** Resposta é retornada sem chamar IA (evita herdar contexto)

### 11.7. Exemplos Práticos

**Exemplo 1: Pergunta genérica sem categoria**
```
Usuário: "o que tem pra chegar essa semana?"
Sistema: Detecta período "essa semana" → filtro_data='semana'
         Detecta que não há categoria → categoria=None
         Chama: listar_processos_por_eta(filtro_data='semana', categoria=None, limite=500)
         Retorna: Todos os processos que chegam esta semana (todas as categorias)
```

**Exemplo 2: Pergunta com categoria**
```
Usuário: "quais processos BND chegam essa semana?"
Sistema: Detecta período "essa semana" → filtro_data='semana'
         Detecta categoria "BND" → categoria='BND'
         Chama: listar_processos_por_eta(filtro_data='semana', categoria='BND', limite=500)
         Retorna: Apenas processos BND que chegam esta semana
```

**Exemplo 3: Pergunta genérica após contexto de categoria**
```
Usuário: "quais processos ALH temos?"
Sistema: [Responde sobre processos ALH]
Usuário: "o que tem pra chegar essa semana?"
Sistema: Detecta período "essa semana" → filtro_data='semana'
         Detecta que não há categoria na mensagem atual → categoria=None (NÃO usa 'ALH' do contexto)
         Chama: listar_processos_por_eta(filtro_data='semana', categoria=None, limite=500)
         Retorna: Todos os processos que chegam esta semana (todas as categorias)
```

---

## 12. Regras de Consulta TECwin NCM

### 12.1. Definição

**TECwin** = Sistema da Aduaneiras para consulta de NCM (Nomenclatura Comum do Mercosul) com informações de alíquotas de impostos.

⚠️ **IMPORTANTE:** A consulta TECwin é feita via automação de navegador (Selenium) e requer credenciais de acesso.

### 12.2. Quando Usar

A consulta TECwin é acionada automaticamente quando o usuário digita:
- `"tecwin ncm 07032090"`
- `"tecwin ncm 96170010"`
- `"consulta tecwin ncm XXXX"`

### 12.3. Detecção de Comando

O sistema detecta o padrão:
- Palavra-chave: `"tecwin"` + `"ncm"` + código NCM (4-8 dígitos)
- Processamento: Antes de enviar para a IA (precheck determinístico)
- Retorno: Resposta direta sem chamar IA

### 12.4. Processo de Consulta

1. **Login automático:**
   - Email: `TECWIN_EMAIL` (variável de ambiente) ou padrão configurado
   - Senha: `TECWIN_SENHA` (variável de ambiente) ou padrão configurado
   - Modo: Headless (sem abrir navegador visível)

2. **Consulta do NCM:**
   - Navega para: `https://tecwinweb.aduaneiras.com.br/Modulos/CodigoNcm/CodigoNcm.aspx?codigoNcm={codigo}`
   - Extrai dados do HTML da página

3. **Extração de dados:**
   - Descrição do NCM
   - Alíquotas de impostos:
     - II (Imposto de Importação) - %
     - IPI (Imposto sobre Produtos Industrializados) - %
     - PIS/PASEP - %
     - COFINS - %
     - ICMS (tributação normal ou específica)
   - Unidade de medida
   - Subposições relacionadas (se houver)

### 12.5. Formatação da Resposta

A resposta é formatada em markdown:

```
📋 NCM 96170010 - TECwin

Descrição: Garrafas térmicas e outros recipientes isotérmicos

Alíquotas:
• II (Imposto de Importação): 16,2%
• IPI (Imposto sobre Produtos Industrializados): 9,75%
• PIS/PASEP: 2,1%
• COFINS: 9,65%
• ICMS: TN

Unidade de Medida: Kg Líquido

🔗 Fonte: TECwin
```

### 12.6. Fontes de Dados

- **HTML da página:** Extração via regex dos atributos da tag `<tr>` com o NCM
- **Atributos extraídos:**
  - `ncm`: Código NCM
  - `descricao`: Descrição do produto
  - `ii`: Alíquota de II
  - `ipi`: Alíquota de IPI
  - `pis`: Alíquota de PIS/PASEP
  - `cofins`: Alíquota de COFINS
  - `icms`: Tipo de tributação ICMS
  - `unidmedida`: Unidade de medida

### 12.7. Tratamento de Erros

- **Login falhou:** Retorna erro "Erro ao fazer login no TECwin. Verifique as credenciais."
- **NCM não encontrado:** Retorna erro "NCM {codigo} não encontrado no TECwin."
- **Erro de conexão:** Retorna erro com detalhes da exceção

### 12.8. Configuração

Variáveis de ambiente (opcional):
- `TECWIN_EMAIL`: Email do usuário TECwin
- `TECWIN_SENHA`: Senha do usuário TECwin

Se não configuradas, usa credenciais padrão configuradas no código.

### 12.9. Dependências

- **Selenium:** Automação de navegador
- **webdriver-manager:** Gerenciamento automático do ChromeDriver
- **Chrome/Chromium:** Navegador necessário para automação

### 12.10. Limitações

- **Depende da estrutura HTML:** Se o site TECwin mudar, pode precisar ajustar seletores
- **Requer ChromeDriver:** Instalado automaticamente via webdriver-manager
- **Tempo de resposta:** ~10-15 segundos (login + consulta + extração)
- **Modo headless:** Executa em segundo plano (não abre navegador visível)

---

## 13. Regras de Averbacao

### 12.1. Definição

**Averbacao** = Consulta de dados de averbação para um processo específico, mostrando informações necessárias para preenchimento do formulário de averbação.

⚠️ **IMPORTANTE:** Averbacao é diferente de "situação do processo":
- **Situação do processo:** Mostra status geral (DI, CE, DUIMP, pendências)
- **Averbacao:** Mostra dados específicos para preenchimento de formulário (valores, impostos, CE, DI)

### 12.2. Quando Usar

A função `consultar_averbacao_processo` é chamada quando o usuário pergunta:
- `"averbacao processo BND.0030/25"`
- `"averbação processo DMD.0045/25"`
- `"averbacao BND.0030/25"`

### 12.3. Dados Retornados

A averbação retorna os seguintes dados formatados para chat:

#### 12.3.1. Conhecimento de Embarque (CE)
- Porto Origem
- País de Procedência
- Porto Destino
- Data Emissão
- Tipo (HBL, MBL, etc.)
- Descrição Mercadoria

#### 12.3.2. Declaração de Importação (DI)
- Número da DI
- Nome Navio
- Número Retificação

#### 12.3.3. Valores (USD)
- Custo (VMLE)
- Frete
- Seguro
- Despesas (10%)
- Lucros (10%)

#### 12.3.4. Valores (BRL)
- Frete
- Seguro
- VMLD

#### 12.3.5. Impostos da DI
- II (Imposto de Importação) - BRL e USD
- IPI (Imposto sobre Produtos Industrializados) - BRL e USD
- PIS/PASEP - BRL e USD
- COFINS - BRL e USD
- Antidumping - BRL e USD
- Taxa SISCOMEX - BRL e USD (excluída do total de impostos)

**Total Impostos:** Soma de todos os impostos **EXCLUINDO Taxa SISCOMEX** (é uma taxa, não um imposto)

#### 12.3.6. Cotação PTAX
- Data da cotação
- Cotação (R$ / USD)

### 12.4. Prioridade de Fontes de Dados

A averbação busca dados na seguinte ordem de prioridade:

1. **Cache SQLite** (`dis_cache`, `ces_cache`)
2. **SQL Server** (tabelas `Di_Root_Declaracao_Importacao`, `Ce_Root_Conhecimento_Embarque`, etc.)
3. **API Integra Comex** (apenas se não encontrado em cache ou SQL Server)

⚠️ **IMPORTANTE:** A API Integra Comex é **bilhetada** (paga por consulta), então o sistema prioriza cache e SQL Server.

### 12.5. Complementação de Dados

Se dados do CE estão incompletos no cache, o sistema:
1. Busca dados do CE do SQL Server (`Ce_Root_Conhecimento_Embarque`)
2. Se ainda faltam campos, busca do cache do CE (`ces_cache`)
3. Preenche campos faltantes automaticamente

**Campos do CE buscados:**
- `paisProcedencia` → mapeado para nome do país
- `dataEmissao` → formatada de ISO para YYYY-MM-DD
- `tipo` → tipo do CE (HBL, MBL, etc.)
- `descricaoMercadoria` → descrição completa

### 12.6. Regra Crítica: Taxa SISCOMEX Não É Imposto

⚠️ **CRÍTICO:** Taxa SISCOMEX **NÃO é incluída** no total de impostos.

**Motivo:** Taxa SISCOMEX é uma **taxa de utilização**, não um imposto.

**Códigos de receita excluídos:**
- `7811` (Taxa SISCOMEX)
- `811` (Taxa SISCOMEX - código alternativo)

**Cálculo do total de impostos:**
```
total_impostos = II + IPI + PIS + COFINS + Antidumping
(NÃO inclui Taxa SISCOMEX)
```

### 12.7. Formatação para Chat

A averbação é formatada em markdown para exibição no chat:

```
📋 **AVERBAÇÃO - BND.0030/25**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 CONHECIMENTO DE EMBARQUE (CE):
  - Porto Origem: CNTAO
  - País de Procedência: CHINA
  ...

💵 IMPOSTOS DA DI:
  - II (Imposto de Importação):
    • BRL: R$ 6,789.22
    • USD: $ 1,258.99
  ...

  **Total Impostos:**
    • BRL: R$ 18,023.08
    • USD: $ 3,342.19

💡 Dados prontos para preenchimento do formulário de averbação.
```

### 12.8. Integração com Relatório de Averbacoes

A função `consultar_averbacao_processo` usa a mesma lógica do serviço `RelatorioAverbacoesService`:
- Mesma extração de dados da DI
- Mesmos cálculos (Despesas 10%, Lucros 10%)
- Mesma conversão BRL→USD usando PTAX
- Mesma exclusão de Taxa SISCOMEX do total

**Diferença:** A averbação formata para chat, enquanto o relatório gera Excel.

---

## 14. Regras de Atraso Crítico

### 13.1. Definição

Processo tem **atraso crítico** quando:
- Chegou há **mais de 7 dias** E
- **NÃO tem** DI nem DUIMP registrada

### 8.2. Cálculo de Dias de Atraso

```
dias_atraso = (hoje - data_chegada).days
```

### 8.3. Classificação

- **Atraso crítico:** > 7 dias
- **Recente:** < 3 dias
- **Normal:** 3-7 dias

---

## 15. Regras de Bloqueios CE

### 14.1. Definição

Bloqueio CE é detectado quando:
- `dados_completos_json.ce[].bloqueios` está preenchido OU
- `dados_completos_json.ce[].bloqueios_baixados` está preenchido

### 14.2. Quando a Aplicação Avisa sobre Bloqueio

A aplicação **avisa sobre bloqueio de CE** quando:

1. **Condições obrigatórias (pelo menos uma deve ser verdadeira):**
   - ✅ Campo `bloqueios` no JSON do CE está preenchido (não é `None`, vazio, ou lista vazia) OU
   - ✅ Campo `bloqueios_baixados` no JSON do CE está preenchido (não é `None`, vazio, ou lista vazia)

**Onde aparece:**
- Dashboard "O que temos pra hoje?" → Seção "⚠️ PENDÊNCIAS ATIVAS" (com prioridade máxima)
- Função `obter_pendencias_ativas()` → Retorna processos com bloqueio de CE
- Consulta "quais processos têm pendência?" → Lista processos com bloqueio de CE

**Ação sugerida:** "Verificar motivo do bloqueio"

**IMPORTANTE:** 
- Bloqueios têm **prioridade máxima** na exibição de pendências
- Bloqueios podem impedir o despacho da carga
- Bloqueios baixados ainda são considerados para histórico

### 14.3. Prioridade de Pendências

Ordem de prioridade para exibição de pendências:
1. **Bloqueio CE** (mais crítico - impede despacho)
2. **LPCO** (bloqueante - impede registro de DI/DUIMP)
3. **ICMS** (se pode ser cobrado - após desembaraço)
4. **AFRMM** (pagamento pendente)
5. **Frete** (pagamento pendente)

---

## 16. Regras de Formatação de Processos para TTS

### 15.1. Formatação de Referência de Processo

Exemplo: `ALH.0166/25` → "ALH zero um seis seis"

**Regras:**
1. **Remove ponto:** `ALH.0166` → `ALH0166`
2. **Remove barra (se ano atual):** Se ano é 2025 e processo é `/25`, remove `/25`
3. **Mantém barra (se ano anterior):** Se processo é `/24`, mantém como "barra vinte e quatro"
4. **Converte números para extenso:** `0166` → "zero um seis seis"

### 15.2. Formatação de Texto de Notificação

Texto é formatado para pronúncia natural:
- Processos são detectados e formatados automaticamente
- Texto combinado (título + mensagem) é processado
- Caracteres especiais são removidos ou convertidos
- Abreviações são expandidas quando necessário

---

## 17. Checklist de Validação

Ao implementar ou modificar regras, verificar:

- [ ] Regra está documentada neste arquivo?
- [ ] Condições específicas estão claras?
- [ ] Exceções estão documentadas?
- [ ] Exemplos estão incluídos?
- [ ] Regra foi testada com casos reais?
- [ ] Notificações são criadas corretamente?
- [ ] Lógica diferencia DI vs DUIMP quando necessário?

---

## 18. Histórico de Mudanças

### 16/12/2025 (Continuação)
- ✅ Adicionadas regras de Consulta TECwin NCM
  - Definição e quando usar
  - Detecção de comando (precheck determinístico)
  - Processo de consulta (login automático, extração de dados)
  - Formatação da resposta com alíquotas
  - Fontes de dados (HTML, atributos da tag `<tr>`)
  - Tratamento de erros e configuração
  - Limitações e dependências
- ✅ Expandidas regras de Fechamento do Dia
  - Detalhamento de campos utilizados para detecção de DI registrada
  - SQL Server como fonte primária (dataHoraRegistro)
  - Cache SQLite como fallback
  - Regra crítica: busca status mais atual após registro (ordenação por dataHoraDesembaraco DESC)
  - Detalhamento de campos para DUIMP registrada (incluindo SQL Server)

### 16/12/2025
- ✅ Adicionadas regras de Detecção de Perguntas sobre Chegada
  - Detecção automática de período temporal (semana, hoje, amanhã, mês)
  - Regra crítica: não usar categoria do contexto anterior quando não mencionada
  - Padrões de detecção para "o que tem pra chegar essa semana?"
  - Fluxo de processamento e exemplos práticos
- ✅ Adicionadas regras de Averbacao
  - Definição e diferença de "situação do processo"
  - Dados retornados (CE, DI, Valores, Impostos, PTAX)
  - Prioridade de fontes de dados (cache → SQL Server → API)
  - Complementação automática de dados do CE
  - Regra crítica: Taxa SISCOMEX não é imposto (excluída do total)
  - Formatação para chat e integração com relatório Excel
- ✅ Atualizada função de ajuda
  - Incluídas seções de AVERBAÇÃO e FECHAMENTO DO DIA
  - Exemplos de uso para cada funcionalidade

### 12/12/2025
- ✅ Adicionadas regras de Fechamento do Dia
  - Definição e diferença do dashboard "O que temos pra hoje"
  - O que é incluído no fechamento (processos que chegaram, desembaraçados, DIs/DUIMPs registradas, mudanças de status)
  - Campos utilizados para detecção de DUIMP registrada
  - Remoção de duplicatas
- ✅ Adicionadas regras de ETA Alterado no Dashboard
  - Apenas processos que ainda não chegaram aparecem
  - Cálculo de diferença e classificação (atraso/adiantamento)
  - Fontes de ETA (primeiro e último)
  - Objetivo da seção
- ✅ Adicionadas regras de Detecção de DUIMP Registrada
  - Quando uma DUIMP é considerada registrada (situação, documentoDespacho, data de registro)
  - Locais onde buscar (JSON do Kanban, tabela duimps)
  - Quando um processo NÃO aparece como "pronto para registro"
  - Exemplo prático (VDM.0004/25)

### 17/12/2025
- ✅ Alinhamento de lógica "chegando hoje" entre `listar_processos_por_eta` e `obter_processos_chegando_hoje`
  - Ambas as funções agora usam a mesma lógica para determinar ETA e verificar chegada confirmada
  - Priorização do ETA do ShipsGo (POD) sobre ETA do ICTSI (Kanban)
  - Verificação de `dataDestinoFinal` para excluir processos que já chegaram
  - Busca de ETA do JSON primeiro (eventos DISC, dataPrevisaoChegada, ARRV) antes de usar `eta_iso` da tabela
  - Garantia de consistência: ambas retornam o mesmo resultado para "chegando hoje"
- ✅ Priorização do ETA do ShipsGo (POD) sobre ETA do ICTSI
  - ETA do ShipsGo tem prioridade quando disponível (mais atualizado)
  - Fallback para ETA do Kanban apenas se ShipsGo não tiver dados
  - Campo `fonte_eta` indica origem do ETA usado ('shipsgo' ou 'kanban')

### 23/12/2025
- ✅ Implementada validação rigorosa de pendência de ICMS
  - Validação antecipada do campo `pendencia_icms` antes de processar
  - Exclusão de valores que não indicam pendência ativa: "RESOLVID", "LIQUIDAD", "QUITAD", "FINALIZAD", "N/A", "NULL", "NONE"
  - Validação aplicada tanto na query SQL quanto na lógica Python para garantir consistência
  - Resolve inconsistência onde processos apareciam como pendentes no dashboard mas não na consulta específica
  - Garante que apenas valores que realmente indicam pendência ativa sejam considerados

### 11/12/2025
- ✅ Ajustada lógica de pendência de ICMS para DUIMP
  - Agora só considera pendente quando situação é `DESEMBARACADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS` ou `ENTREGA_ANTECIPADA_AGUARDANDO_PENDENCIA_TRIBUTOS_ESTADUAIS`
  - Processos SLL com situação `DESEMBARACADA_CARGA_ENTREGUE` não aparecem mais como pendentes
- ✅ Implementado suporte para DTA (Declaração de Trânsito Aduaneiro)
  - Processos em DTA são listados separadamente no dashboard
  - Regra crítica: processo só está "em DTA" se tem DTA E não tem DI nem DUIMP
  - Processos em DTA não aparecem como "prontos para registro"
- ✅ Documentação de TTS expandida
  - Detalhes sobre geração de áudio, cache, reprodução e configuração
  - Fluxo completo de notificação com áudio
  - Regras de formatação de texto para pronúncia natural
- ✅ Documentação de condições de aviso sobre pendências expandida
  - Condições específicas para quando a aplicação avisa sobre ICMS, AFRMM, Frete, LPCO e Bloqueios
  - Onde cada tipo de pendência aparece no sistema
  - Ações sugeridas para cada tipo de pendência
  - Prioridade de exibição de pendências

---

## 19. Referências

- **Código principal:** `db_manager.py` (função `obter_pendencias_ativas`, `listar_processos_em_dta`)
- **Notificações:** `services/notificacao_service.py`
- **DTOs:** `services/models/processo_kanban_dto.py`
- **Formatação TTS:** `utils/tts_text_formatter.py`
- **Serviço TTS:** `services/tts_service.py`
- **Frontend TTS:** `templates/chat-ia-isolado.html` (classe `AudioQueue`)
- **TECwin Scraper:** `tecwin_scraper.py`
- **Precheck TECwin:** `services/precheck_service.py` (método `_precheck_tecwin_ncm`)
- **Listagem por ETA:** `db_manager.py` (função `listar_processos_por_eta`)
- **Processos chegando hoje:** `db_manager.py` (função `obter_processos_chegando_hoje`)
- **ShipsGo Tracking:** `db_manager.py` (função `shipsgo_get_tracking_map`)

---

**💡 Dica:** Sempre consulte este documento antes de modificar regras de negócio. Se encontrar uma regra não documentada, adicione-a aqui.

