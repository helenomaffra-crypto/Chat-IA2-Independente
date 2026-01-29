# 📊 Mapeamento Completo de APIs Utilizadas

**Data:** 08/01/2026  
**Status:** 📋 Mapeamento Completo  
**Objetivo:** Mapear todas as APIs para definir estratégia de integração de histórico

---

## 🎯 Objetivo

Mapear **todas as APIs** utilizadas no sistema para:
1. Entender onde cada API é chamada
2. Identificar que tipo de dados retornam
3. Decidir melhor estratégia de integração de histórico
4. Garantir que todas as mudanças sejam rastreadas

---

## 📋 APIs Mapeadas

### 1. 🔵 **Integra Comex (SERPRO)**

**Base URL:** Configurável via `.env`  
**Autenticação:** OAuth2 + mTLS (certificado PKCS#12)  
**⚠️ IMPORTANTE:** API BILHETADA (paga por consulta)  
**Proxy:** `utils/integracomex_proxy.py` → `call_integracomex()`

#### Endpoints Utilizados:

| Endpoint | Chamado Por | Tipo Documento | Retorna Mudanças? | Estrutura Resposta |
|----------|-------------|----------------|-------------------|-------------------|
| `GET /carga/conhecimento-embarque/{numeroCE}` | `services/consulta_service.py`<br>`services/agents/ce_agent.py` | CE | ✅ SIM | `situacaoCarga`, `dataSituacaoCarga`, `dataDesembaraco`, `dataRegistro` |
| `GET /carga/conhecimento-embarque/{numeroCE}/previsao-atracacao` | `services/consulta_service.py` | CE (ETA) | ✅ SIM | `dataPrevisaoAtracacao`, `portoAtracacao` |
| `GET /declaracao-importacao/{numeroDI}` | `services/consulta_service.py`<br>`services/agents/di_agent.py` | DI | ✅ SIM | `situacaoDi`, `canal`, `dataHoraRegistro`, `dataHoraDesembaraco` |
| `GET /carga/conhecimento-carga-aerea/{numeroCCT}` | `services/agents/cct_agent.py` | CCT | ✅ SIM | `situacaoAtual`, `dataHoraSituacaoAtual`, `dataChegadaEfetiva` |

#### Campos Relevantes para Histórico:

**CE:**
- `situacaoCarga` / `situacao_carga` → Status do CE
- `dataSituacaoCarga` / `data_situacao_carga` → Data da situação
- `dataDesembaraco` / `data_desembaraco` → Data de desembaraço
- `dataRegistro` / `data_registro` → Data de registro

**DI:**
- `situacaoDi` / `situacao_di` → Status da DI
- `canal` / `canalDi` → Canal (VERDE, AMARELO, VERMELHO)
- `dataHoraRegistro` / `data_hora_registro` → Data de registro
- `dataHoraDesembaraco` / `data_hora_desembaraco` → Data de desembaraço
- `valorIiBrl` / `valor_ii_brl` → Valor II em BRL
- `valorIpiBrl` / `valor_ipi_brl` → Valor IPI em BRL

**CCT:**
- `situacaoAtual` / `situacao_atual` → Status do CCT
- `dataHoraSituacaoAtual` / `data_hora_situacao_atual` → Data da situação
- `dataChegadaEfetiva` / `data_chegada_efetiva` → Data de chegada

**ETA:**
- `dataPrevisaoAtracacao` → Data prevista de atracação
- `portoAtracacao` → Porto de atracação

---

### 2. 🟢 **Portal Único Siscomex**

**Base URL:** `https://portalunico.siscomex.gov.br` (configurável)  
**Autenticação:** mTLS (certificado PKCS#12) + CSRF Token  
**Ambientes:** Validação e Produção  
**Proxy:** `utils/portal_proxy.py` → `call_portal()`

#### Endpoints Utilizados:

| Endpoint | Chamado Por | Tipo Documento | Retorna Mudanças? | Estrutura Resposta |
|----------|-------------|----------------|-------------------|-------------------|
| `POST /duimp-api/api/ext/duimp` | `services/agents/duimp_agent.py` | DUIMP (criação) | ✅ SIM | `identificacao.numero`, `identificacao.versao`, `situacao`, `canal` |
| `GET /duimp-api/api/ext/duimp/{numero}/{versao}` | `services/agents/duimp_agent.py`<br>`services/duimp_service.py` | DUIMP (consulta) | ✅ SIM | `identificacao.situacao`, `identificacao.canal`, `identificacao.dataRegistro` |
| `PUT /duimp-api/api/ext/duimp/{numero}/{versao}` | `services/agents/duimp_agent.py` | DUIMP (atualização) | ✅ SIM | Mesma estrutura de consulta |
| `GET /duimp-api/api/ext/ccta/{awb}` | `services/agents/cct_agent.py` | CCT | ✅ SIM | `situacao`, `dataSituacao`, `dataChegadaEfetiva` |
| `GET /nomenclatura/nomenclatura.json` | `services/ncm_service.py` | NCM (nomenclatura) | ❌ NÃO | Lista de NCMs (não é documento aduaneiro) |

#### Campos Relevantes para Histórico:

**DUIMP:**
- `identificacao.situacao` / `situacao` → Status da DUIMP
- `identificacao.canal` / `canal` → Canal (VERDE, AMARELO, VERMELHO)
- `identificacao.dataRegistro` / `dataRegistro` → Data de registro
- `identificacao.ultimaSituacao` / `ultimaSituacao` → Última situação
- `identificacao.ultimaSituacaoData` / `ultimaSituacaoData` → Data da última situação
- Valores financeiros (se disponíveis)

**CCT (Portal Único):**
- `situacao` → Status do CCT
- `dataSituacao` → Data da situação
- `dataChegadaEfetiva` → Data de chegada efetiva

---

### 3. 🟡 **API Kanban (Interna)**

**Base URL:** `http://172.16.10.211:5000/api/kanban/pedidos`  
**Autenticação:** Nenhuma (API interna)  
**Descrição:** API interna da empresa para consulta de processos de importação  
**Serviço:** `services/processo_kanban_service.py`

#### Endpoints Utilizados:

| Endpoint | Chamado Por | Tipo Documento | Retorna Mudanças? | Estrutura Resposta |
|----------|-------------|----------------|-------------------|-------------------|
| `GET /api/kanban/pedidos` | `services/processo_kanban_service.py` | Processo (completo) | ✅ SIM | JSON completo com CE, DI, DUIMP, CCT, ETA, status, etc. |

#### Campos Relevantes para Histórico:

**Processo (via Kanban):**
- `ce[].situacao` → Status do CE
- `ce[].dataSituacaoCarga` → Data da situação do CE
- `di[].situacao` → Status da DI
- `di[].canal` → Canal da DI
- `duimp[].situacao` → Status da DUIMP
- `duimp[].canal` → Canal da DUIMP
- `cct[].situacao` → Status do CCT
- `shipgov2.eventos[]` → Eventos de tracking (ETA, chegadas, etc.)

**⚠️ IMPORTANTE:** O Kanban retorna **dados consolidados** de processos, incluindo documentos vinculados. Mudanças em documentos podem vir através do Kanban também.

---

### 4. 🔴 **Banco do Brasil API**

**Base URL:** Configurável via `.env`  
**Autenticação:** OAuth2 + mTLS (certificado)  
**Proxy:** `utils/banco_brasil_api.py`

#### Endpoints Utilizados:

| Endpoint | Chamado Por | Tipo Documento | Retorna Mudanças? | Estrutura Resposta |
|----------|-------------|----------------|-------------------|-------------------|
| `GET /conta-corrente/agencia/{agencia}/conta/{conta}` | `services/banco_brasil_service.py` | Extrato bancário | ❌ NÃO | Movimentações bancárias (não é documento aduaneiro) |

**⚠️ NOTA:** Extratos bancários não são documentos aduaneiros, mas podem ter histórico de mudanças (valores, datas, etc.). **Não precisa integrar histórico de documentos aqui.**

---

### 5. 🟣 **Santander Open Banking**

**Base URL:** Configurável via `.env`  
**Autenticação:** OAuth2  
**Proxy:** `utils/santander_api.py`

#### Endpoints Utilizados:

| Endpoint | Chamado Por | Tipo Documento | Retorna Mudanças? | Estrutura Resposta |
|----------|-------------|----------------|-------------------|-------------------|
| `GET /bank_account_information/v1/banks/{bank_id}/statements/{statement_id}` | `services/santander_service.py` | Extrato bancário | ❌ NÃO | Movimentações bancárias (não é documento aduaneiro) |
| `GET /bank_account_information/v1/banks/{bank_id}/balances/{balance_id}` | `services/santander_service.py` | Saldo bancário | ❌ NÃO | Saldo da conta (não é documento aduaneiro) |

**⚠️ NOTA:** Extratos bancários não são documentos aduaneiros. **Não precisa integrar histórico de documentos aqui.**

---

### 6. 🟠 **ShipsGo (Tracking de Navios)**

**Base URL:** Configurável via `.env`  
**Autenticação:** API Key  
**Descrição:** Tracking de navios para ETA e portos

#### Endpoints Utilizados:

| Endpoint | Chamado Por | Tipo Documento | Retorna Mudanças? | Estrutura Resposta |
|----------|-------------|----------------|-------------------|-------------------|
| `GET /tracking/{processo}` | `services/processo_kanban_service.py` | ETA/Processo | ✅ SIM | `eta_iso`, `porto_codigo`, `porto_nome`, `status` |

**⚠️ NOTA:** ShipsGo retorna dados de **ETA e tracking**, não documentos aduaneiros diretamente. Mas mudanças de ETA são relevantes e já são rastreadas na `TIMELINE_PROCESSO`.

---

### 7. ⚪ **Outras APIs**

#### OpenAI Assistants API
- **Uso:** Busca semântica de legislação (RAG)
- **Retorna mudanças?** ❌ NÃO (legislação, não documentos)

#### TECwin (Scraper)
- **Uso:** Consulta de alíquotas de NCM
- **Retorna mudanças?** ❌ NÃO (alíquotas, não documentos)

#### PTAX BCB
- **Uso:** Taxa de câmbio
- **Retorna mudanças?** ❌ NÃO (taxa de câmbio, não documentos)

---

## 📊 Resumo por Tipo de Documento

### CE (Conhecimento de Embarque)

**APIs que retornam CE:**
1. ✅ **Integra Comex** → `GET /carga/conhecimento-embarque/{numeroCE}`
2. ✅ **API Kanban** → `GET /api/kanban/pedidos` (dados consolidados)

**Campos de mudança:**
- `situacaoCarga` / `situacao_carga`
- `dataSituacaoCarga` / `data_situacao_carga`
- `dataDesembaraco` / `data_desembaraco`
- `dataRegistro` / `data_registro`

**Onde integrar:**
- `services/consulta_service.py` → `consultar_ce_maritimo()`
- `services/agents/ce_agent.py` → Métodos que consultam CE
- `services/processo_kanban_service.py` → Sincronização de processos (já detecta mudanças via NotificacaoService)

---

### CCT (Conhecimento de Carga Aérea)

**APIs que retornam CCT:**
1. ✅ **Integra Comex** → `GET /carga/conhecimento-carga-aerea/{numeroCCT}`
2. ✅ **Portal Único** → `GET /duimp-api/api/ext/ccta/{awb}`
3. ✅ **API Kanban** → `GET /api/kanban/pedidos` (dados consolidados)

**Campos de mudança:**
- `situacaoAtual` / `situacao_atual`
- `dataHoraSituacaoAtual` / `data_hora_situacao_atual`
- `dataChegadaEfetiva` / `data_chegada_efetiva`

**Onde integrar:**
- `services/agents/cct_agent.py` → Métodos que consultam CCT
- `services/processo_kanban_service.py` → Sincronização de processos

---

### DI (Declaração de Importação)

**APIs que retornam DI:**
1. ✅ **Integra Comex** → `GET /declaracao-importacao/{numeroDI}`
2. ✅ **API Kanban** → `GET /api/kanban/pedidos` (dados consolidados)

**Campos de mudança:**
- `situacaoDi` / `situacao_di`
- `canal` / `canalDi`
- `dataHoraRegistro` / `data_hora_registro`
- `dataHoraDesembaraco` / `data_hora_desembaraco`
- `valorIiBrl` / `valor_ii_brl`
- `valorIpiBrl` / `valor_ipi_brl`

**Onde integrar:**
- `services/consulta_service.py` → Métodos que consultam DI
- `services/agents/di_agent.py` → Métodos que consultam DI
- `services/processo_kanban_service.py` → Sincronização de processos (já detecta mudanças via NotificacaoService)

---

### DUIMP (Declaração Única de Importação)

**APIs que retornam DUIMP:**
1. ✅ **Portal Único** → `GET /duimp-api/api/ext/duimp/{numero}/{versao}`
2. ✅ **Portal Único** → `POST /duimp-api/api/ext/duimp` (criação)
3. ✅ **Portal Único** → `PUT /duimp-api/api/ext/duimp/{numero}/{versao}` (atualização)
4. ✅ **API Kanban** → `GET /api/kanban/pedidos` (dados consolidados)

**Campos de mudança:**
- `identificacao.situacao` / `situacao`
- `identificacao.canal` / `canal`
- `identificacao.dataRegistro` / `dataRegistro`
- `identificacao.ultimaSituacao` / `ultimaSituacao`
- `identificacao.ultimaSituacaoData` / `ultimaSituacaoData`
- Valores financeiros (se disponíveis)

**Onde integrar:**
- `services/agents/duimp_agent.py` → Métodos que consultam/criam/atualizam DUIMP
- `services/duimp_service.py` → Métodos que consultam DUIMP
- `services/processo_kanban_service.py` → Sincronização de processos (já detecta mudanças via NotificacaoService)

---

## 🎯 Estratégia de Integração Recomendada

### Abordagem 1: Integração Centralizada nos Proxies ⭐ **RECOMENDADA**

**Vantagens:**
- ✅ **Um único ponto de integração** por API
- ✅ **Cobre todas as chamadas** automaticamente
- ✅ **Menos código duplicado**
- ✅ **Mais fácil de manter**

**Onde integrar:**
1. `utils/integracomex_proxy.py` → `call_integracomex()`
2. `utils/portal_proxy.py` → `call_portal()`
3. `services/processo_kanban_service.py` → `sincronizar()` (já detecta mudanças, só precisa gravar histórico)

**Implementação:**
```python
# Em utils/integracomex_proxy.py
def call_integracomex(...):
    # ... código existente ...
    
    # Após obter resposta
    if status == 200 and response_body:
        # Detectar tipo de documento e gravar histórico
        _gravar_historico_se_documento(path, response_body, processo_referencia)
    
    return status, response_body
```

### Abordagem 2: Integração nos Serviços Específicos

**Vantagens:**
- ✅ Mais controle sobre quando gravar histórico
- ✅ Pode filtrar consultas desnecessárias

**Desvantagens:**
- ❌ Mais pontos de integração
- ❌ Pode esquecer algum ponto
- ❌ Mais código duplicado

**Onde integrar:**
- `services/consulta_service.py` → `consultar_ce_maritimo()`
- `services/agents/ce_agent.py` → Métodos de consulta
- `services/agents/di_agent.py` → Métodos de consulta
- `services/agents/cct_agent.py` → Métodos de consulta
- `services/agents/duimp_agent.py` → Métodos de consulta/criação/atualização
- `services/duimp_service.py` → Métodos de consulta

---

## ✅ Recomendação Final

**Abordagem Híbrida:**

1. **Integração Centralizada nos Proxies** (Abordagem 1)
   - `utils/integracomex_proxy.py` → Para CE, DI, CCT
   - `utils/portal_proxy.py` → Para DUIMP, CCT

2. **Integração Específica no Kanban** (já existe parcialmente)
   - `services/processo_kanban_service.py` → Já detecta mudanças via `NotificacaoService`
   - **Adicionar:** Gravar histórico de documentos quando detectar mudanças

3. **Validação nos Serviços** (opcional)
   - Serviços podem validar se histórico foi gravado
   - Logs adicionais se necessário

---

## 📋 Checklist de Implementação

### Fase 1: Integração Centralizada ⭐ **PRIORIDADE**
- [ ] Integrar em `utils/integracomex_proxy.py` → `call_integracomex()`
- [ ] Integrar em `utils/portal_proxy.py` → `call_portal()`
- [ ] Testar com consultas de CE, DI, CCT, DUIMP

### Fase 2: Integração no Kanban
- [ ] Adicionar gravação de histórico em `services/processo_kanban_service.py`
- [ ] Integrar com `NotificacaoService` (já detecta mudanças)
- [ ] Testar sincronização de processos

### Fase 3: Validação e Testes
- [ ] Testar com documento novo
- [ ] Testar com mudança de status
- [ ] Testar com mudança de canal
- [ ] Testar sem mudanças
- [ ] Validar dados gravados no banco

---

## 📊 Tabela de Decisão

| API | Proxy | Integrar Aqui? | Motivo |
|-----|-------|----------------|--------|
| Integra Comex (CE) | `utils/integracomex_proxy.py` | ✅ SIM | Todas as consultas de CE passam por aqui |
| Integra Comex (DI) | `utils/integracomex_proxy.py` | ✅ SIM | Todas as consultas de DI passam por aqui |
| Integra Comex (CCT) | `utils/integracomex_proxy.py` | ✅ SIM | Todas as consultas de CCT passam por aqui |
| Portal Único (DUIMP) | `utils/portal_proxy.py` | ✅ SIM | Todas as consultas/criações/atualizações de DUIMP passam por aqui |
| Portal Único (CCT) | `utils/portal_proxy.py` | ✅ SIM | Consultas de CCT passam por aqui |
| API Kanban | `services/processo_kanban_service.py` | ✅ SIM | Já detecta mudanças, só precisa gravar histórico |
| Banco do Brasil | `utils/banco_brasil_api.py` | ❌ NÃO | Extratos bancários (não são documentos aduaneiros) |
| Santander | `utils/santander_api.py` | ❌ NÃO | Extratos bancários (não são documentos aduaneiros) |
| ShipsGo | `services/processo_kanban_service.py` | ⚠️ PARCIAL | ETA já é rastreado em TIMELINE_PROCESSO |

---

**Última atualização:** 08/01/2026

