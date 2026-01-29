# 🗄️ Estratégia de População do Banco mAIke_assistente

**Data:** 08/01/2026  
**Status:** 📋 **PLANEJAMENTO** - Aguardando implementação  
**Objetivo:** Definir como popular o banco `mAIke_assistente` no SQL Server com processos, documentos, despesas e impostos

---

## 🎯 Objetivos

1. **Popular banco com processos do Kanban** (fonte primária)
2. **Gravar documentos aduaneiros** (CE, DI, DUIMP, CCT) com histórico
3. **Gravar impostos e valores** da mercadoria (DI/DUIMP)
4. **Gravar despesas conciliadas** (já implementado)
5. **Manter sincronização** entre Kanban → SQL Server

---

## 📊 Estrutura de Dados Necessária

### 1. **PROCESSO_IMPORTACAO** (Tabela Principal)

**Fonte:** Kanban API (`http://172.16.10.211:5000/api/kanban/pedidos`)

**Campos principais:**
- `processo_referencia` (ex: BGR.0070/25)
- `categoria` (BGR, ALH, VDM, etc.)
- `id_processo_importacao` (do Kanban)
- `id_importacao` (do SQL Server Make)
- `etapa_kanban`
- `modal` (Marítimo, Aéreo)
- `data_criacao`, `data_embarque`, `data_desembaraco`, `data_entrega`
- `eta_iso`, `porto_codigo`, `porto_nome`, `nome_navio`
- `json_dados_completos` (JSON completo do Kanban)

**Quando gravar:**
- ✅ Sincronização automática do Kanban (já existe em `ProcessoKanbanService`)
- ✅ Quando consultar processo via `ProcessoRepository`
- ✅ Quando criar/atualizar processo manualmente

---

### 2. **DOCUMENTO_ADUANEIRO** (CE, DI, DUIMP, CCT)

**Fontes:**
- **CE/DI/CCT:** Integra Comex (via `integracomex_proxy.py`)
- **DUIMP:** Portal Único (via `portal_proxy.py`)
- **Kanban:** Dados consolidados do processo

**Campos principais:**
- `numero_documento` (ex: 172505417636125, 2600362869)
- `tipo_documento` (CE, DI, DUIMP, CCT)
- `processo_referencia` (FK)
- `situacao_documento` (status atual)
- `canal_documento` (VERDE, AMARELO, VERMELHO)
- `data_registro`, `data_situacao`, `data_desembaraco`
- `json_dados_originais` (JSON completo da API)

**Quando gravar:**
- ✅ Quando consultar documento via API (já implementado em `integracomex_proxy.py` e `portal_proxy.py`)
- ✅ Quando sincronizar processo do Kanban (já implementado em `ProcessoKanbanService._gravar_historico_documentos()`)
- ✅ Quando detectar mudanças (via `DocumentoHistoricoService`)

---

### 3. **HISTORICO_DOCUMENTO_ADUANEIRO** (Mudanças)

**Fonte:** Comparação entre versão anterior vs nova

**Campos principais:**
- `numero_documento`, `tipo_documento`
- `processo_referencia`
- `tipo_evento` (MUDANCA_STATUS, MUDANCA_CANAL, etc.)
- `campo_alterado`, `valor_anterior`, `valor_novo`
- `fonte_dados` (INTEGRACOMEX, PORTAL_UNICO, KANBAN)

**Quando gravar:**
- ✅ Quando consultar documento via API (já implementado)
- ✅ Quando sincronizar processo do Kanban (já implementado)

**Status:** ✅ **IMPLEMENTADO** - Ver `docs/RESUMO_IMPLEMENTACAO_COMPLETA.md`

---

### 4. **IMPOSTO_IMPORTACAO** ⭐ **NOVO - PRECISA IMPLEMENTAR**

**Descrição:** Impostos pagos da DI/DUIMP (II, IPI, PIS, COFINS, Taxa SISCOMEX)

**Fonte:** SQL Server Make (`Di_Pagamento`, `Di_pagamentos_cod_receitas`) ou Portal Único (DUIMP)

**Estrutura proposta:**
```sql
CREATE TABLE [dbo].[IMPOSTO_IMPORTACAO] (
    id_imposto BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Vínculo
    processo_referencia VARCHAR(50) NOT NULL,
    numero_documento VARCHAR(50) NOT NULL,  -- DI ou DUIMP
    tipo_documento VARCHAR(10) NOT NULL,     -- 'DI' ou 'DUIMP'
    
    -- Tipo de Imposto
    tipo_imposto VARCHAR(50) NOT NULL,        -- 'II', 'IPI', 'PIS', 'COFINS', 'TAXA_UTILIZACAO', 'ANTIDUMPING'
    codigo_receita VARCHAR(10),               -- Código da receita (0086, 1038, etc.)
    
    -- Valores
    valor_brl DECIMAL(18,2) NOT NULL,        -- Valor em BRL
    valor_usd DECIMAL(18,2),                  -- Valor em USD (se disponível)
    taxa_cambio DECIMAL(10,6),                -- Taxa de câmbio usada
    
    -- Datas
    data_pagamento DATETIME,                 -- Data do pagamento
    data_vencimento DATETIME,                 -- Data de vencimento (se disponível)
    
    -- Status
    pago BIT DEFAULT 1,                       -- Se foi pago
    numero_retificacao INT,                   -- Número da retificação (se aplicável)
    
    -- Fonte
    fonte_dados VARCHAR(50) NOT NULL,        -- 'SQL_SERVER', 'PORTAL_UNICO', 'INTEGRACOMEX'
    json_dados_originais NVARCHAR(MAX),      -- JSON completo da fonte
    
    -- Metadados
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_processo (processo_referencia, tipo_documento),
    INDEX idx_documento (numero_documento, tipo_documento),
    INDEX idx_tipo_imposto (tipo_imposto, data_pagamento DESC),
    INDEX idx_data_pagamento (data_pagamento DESC)
);
```

**Quando gravar:**
- ✅ Quando consultar DI/DUIMP e houver impostos pagos
- ✅ Quando sincronizar processo do Kanban e houver DI/DUIMP
- ✅ Quando detectar mudanças em impostos (via histórico)

---

### 5. **VALOR_MERCADORIA** ⭐ **NOVO - PRECISA IMPLEMENTAR**

**Descrição:** Valores da mercadoria (Descarga, Embarque) em BRL e USD

**Fonte:** SQL Server Make (`Di_Dados_Gerais`) ou Portal Único (DUIMP)

**Estrutura proposta:**
```sql
CREATE TABLE [dbo].[VALOR_MERCADORIA] (
    id_valor BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Vínculo
    processo_referencia VARCHAR(50) NOT NULL,
    numero_documento VARCHAR(50) NOT NULL,  -- DI ou DUIMP
    tipo_documento VARCHAR(10) NOT NULL,     -- 'DI' ou 'DUIMP'
    
    -- Tipo de Valor
    tipo_valor VARCHAR(50) NOT NULL,         -- 'DESCARGA', 'EMBARQUE', 'FOB', 'CIF'
    moeda VARCHAR(3) NOT NULL,                -- 'BRL', 'USD', 'EUR'
    
    -- Valores
    valor DECIMAL(18,2) NOT NULL,
    taxa_cambio DECIMAL(10,6),                -- Taxa de câmbio usada (se conversão)
    
    -- Datas
    data_valor DATETIME,                      -- Data de referência do valor
    data_atualizacao DATETIME DEFAULT GETDATE(),
    
    -- Fonte
    fonte_dados VARCHAR(50) NOT NULL,        -- 'SQL_SERVER', 'PORTAL_UNICO'
    json_dados_originais NVARCHAR(MAX),      -- JSON completo da fonte
    
    -- Metadados
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_processo (processo_referencia, tipo_documento),
    INDEX idx_documento (numero_documento, tipo_documento),
    INDEX idx_tipo_valor (tipo_valor, moeda)
);
```

**Quando gravar:**
- ✅ Quando consultar DI/DUIMP e houver valores
- ✅ Quando sincronizar processo do Kanban e houver DI/DUIMP
- ✅ Quando detectar mudanças em valores (via histórico)

---

## 🔄 Estratégia de População

### **Fase 1: População Inicial (Backfill)** ⭐ **PRIORIDADE ALTA**

**Objetivo:** Popular banco com dados existentes

#### 1.1. Processos do Kanban

**Script:** `scripts/popular_processos_kanban.py`

**Estratégia:**
1. Buscar todos os processos do Kanban (API)
2. Para cada processo:
   - Gravar em `PROCESSO_IMPORTACAO`
   - Extrair documentos (CE, DI, DUIMP, CCT) e gravar em `DOCUMENTO_ADUANEIRO`
   - Extrair impostos (se houver DI/DUIMP) e gravar em `IMPOSTO_IMPORTACAO`
   - Extrair valores (se houver DI/DUIMP) e gravar em `VALOR_MERCADORIA`

**Frequência:** Uma vez (backfill inicial)

#### 1.2. Processos do SQL Server Make (Históricos)

**Script:** `scripts/popular_processos_sql_server.py`

**Estratégia:**
1. Buscar processos do SQL Server Make (`make.dbo.PROCESSO_IMPORTACAO`)
2. Para cada processo:
   - Gravar em `PROCESSO_IMPORTACAO` (se não existir)
   - Buscar DI completa e gravar impostos/valores
   - Buscar CE completo e gravar dados

**Frequência:** Uma vez (backfill inicial)

---

### **Fase 2: Sincronização Contínua** ⭐ **JÁ IMPLEMENTADO PARCIALMENTE**

#### 2.1. Sincronização Automática do Kanban

**Arquivo:** `services/processo_kanban_service.py`

**Status:** ✅ **JÁ IMPLEMENTADO** - Sincroniza para SQLite

**O que falta:**
- ⚠️ Gravar também no SQL Server `mAIke_assistente` (não apenas SQLite)
- ⚠️ Gravar documentos em `DOCUMENTO_ADUANEIRO`
- ⚠️ Gravar impostos em `IMPOSTO_IMPORTACAO`
- ⚠️ Gravar valores em `VALOR_MERCADORIA`

#### 2.2. Gravação ao Consultar Processo

**Arquivo:** `services/processo_repository.py`

**Status:** ✅ **JÁ IMPLEMENTADO** - Busca de múltiplas fontes

**O que falta:**
- ⚠️ Gravar processo no SQL Server quando consultado (se não existir)
- ⚠️ Gravar documentos/impostos/valores quando consultados

#### 2.3. Gravação ao Consultar Documento

**Arquivos:** `utils/integracomex_proxy.py`, `utils/portal_proxy.py`

**Status:** ✅ **JÁ IMPLEMENTADO** - Histórico de documentos

**O que falta:**
- ⚠️ Gravar impostos quando consultar DI/DUIMP
- ⚠️ Gravar valores quando consultar DI/DUIMP

---

## 📋 Implementação Proposta

### **PASSO 1: Criar Tabelas** ⭐ **URGENTE**

**Arquivo:** `scripts/criar_banco_maike_completo.sql`

**Tabelas a adicionar:**
1. ✅ `IMPOSTO_IMPORTACAO` (ver estrutura acima)
2. ✅ `VALOR_MERCADORIA` (ver estrutura acima)

**Ação:** Adicionar ao script SQL existente

---

### **PASSO 2: Serviço de Gravação de Impostos/Valores** ⭐ **URGENTE**

**Arquivo:** `services/imposto_valor_service.py` (NOVO)

**Funcionalidades:**
```python
class ImpostoValorService:
    def gravar_impostos_di(
        self,
        processo_referencia: str,
        numero_di: str,
        impostos: List[Dict[str, Any]],  # Lista de impostos da DI
        fonte_dados: str = 'SQL_SERVER'
    ) -> bool
    
    def gravar_impostos_duimp(
        self,
        processo_referencia: str,
        numero_duimp: str,
        impostos: List[Dict[str, Any]],  # Lista de impostos da DUIMP
        fonte_dados: str = 'PORTAL_UNICO'
    ) -> bool
    
    def gravar_valores_di(
        self,
        processo_referencia: str,
        numero_di: str,
        valores: Dict[str, Any],  # Valores da DI (descarga, embarque, etc.)
        fonte_dados: str = 'SQL_SERVER'
    ) -> bool
    
    def gravar_valores_duimp(
        self,
        processo_referencia: str,
        numero_duimp: str,
        valores: Dict[str, Any],  # Valores da DUIMP
        fonte_dados: str = 'PORTAL_UNICO'
    ) -> bool
```

---

### **PASSO 3: Integrar Gravação de Impostos/Valores**

#### 3.1. No `ProcessoAgent._consultar_status_processo`

**Onde:** Após buscar dados da DI/DUIMP

**O que fazer:**
```python
# Após obter dados da DI/DUIMP com impostos/valores
if di_data and di_data.get('pagamentos'):
    from services.imposto_valor_service import ImpostoValorService
    imposto_service = ImpostoValorService()
    imposto_service.gravar_impostos_di(
        processo_referencia=processo_referencia,
        numero_di=numero_di,
        impostos=di_data.get('pagamentos'),
        fonte_dados='SQL_SERVER'
    )

if di_data and (di_data.get('valor_mercadoria_descarga_real') or di_data.get('valor_mercadoria_embarque_real')):
    imposto_service.gravar_valores_di(
        processo_referencia=processo_referencia,
        numero_di=numero_di,
        valores={
            'descarga_brl': di_data.get('valor_mercadoria_descarga_real'),
            'embarque_brl': di_data.get('valor_mercadoria_embarque_real'),
            'descarga_usd': di_data.get('valor_mercadoria_descarga_dolar'),
            'embarque_usd': di_data.get('valor_mercadoria_embarque_dolar')
        },
        fonte_dados='SQL_SERVER'
    )
```

#### 3.2. No `ProcessoKanbanService._salvar_processo`

**Onde:** Após salvar processo, extrair documentos e gravar impostos/valores

**O que fazer:**
```python
# Após salvar processo, extrair DI/DUIMP do JSON
if processo_json.get('di'):
    di_data = processo_json['di']
    # Gravar impostos e valores se disponíveis
```

---

### **PASSO 4: Script de Backfill**

**Arquivo:** `scripts/popular_banco_maike_backfill.py`

**Funcionalidades:**
1. Buscar processos do Kanban
2. Para cada processo:
   - Gravar em `PROCESSO_IMPORTACAO`
   - Extrair e gravar documentos
   - Extrair e gravar impostos (se DI/DUIMP)
   - Extrair e gravar valores (se DI/DUIMP)
3. Buscar processos do SQL Server Make (históricos)
4. Repetir processo acima

**Frequência:** Executar uma vez para popular banco inicial

---

## 🔍 Verificação: Histórico Foi Gravado?

### **Teste para BGR.0070/25:**

```python
# Verificar se histórico foi gravado
from utils.sql_server_adapter import get_sql_adapter

sql_adapter = get_sql_adapter()
query = """
    SELECT TOP 10 
        numero_documento,
        tipo_documento,
        tipo_evento,
        campo_alterado,
        valor_anterior,
        valor_novo,
        data_evento,
        fonte_dados
    FROM dbo.HISTORICO_DOCUMENTO_ADUANEIRO
    WHERE processo_referencia = 'BGR.0070/25'
    ORDER BY data_evento DESC
"""

result = sql_adapter.execute_query(query, database='mAIke_assistente')
print(result)
```

**Se retornar vazio:**
- ⚠️ Histórico não foi gravado
- Verificar se `DocumentoHistoricoService` está sendo chamado
- Verificar se tabela existe no banco

---

## 📊 Fluxo Completo de População

### **Cenário 1: Consulta de Processo (Primeira Vez)**

```
1. Usuário: "situacao do BGR.0070/25"
   ↓
2. ProcessoRepository busca processo
   - Kanban → SQLite (cache)
   - SQL Server Make (histórico)
   ↓
3. ProcessoAgent._consultar_status_processo
   - Busca CE, DI, DUIMP
   - Consulta APIs se necessário
   ↓
4. integracomex_proxy / portal_proxy
   - Consulta API
   - ✅ Grava histórico (já implementado)
   - ⚠️ FALTA: Gravar impostos/valores
   ↓
5. Retorna resposta formatada
   - ⚠️ FALTA: Gravar processo no SQL Server se não existir
   - ⚠️ FALTA: Gravar impostos/valores no SQL Server
```

### **Cenário 2: Sincronização Automática Kanban**

```
1. ProcessoKanbanService.sincronizar() (a cada 5 min)
   ↓
2. Busca processos do Kanban
   ↓
3. Para cada processo:
   - ✅ Grava em SQLite (já implementado)
   - ✅ Grava histórico de documentos (já implementado)
   - ⚠️ FALTA: Gravar em SQL Server PROCESSO_IMPORTACAO
   - ⚠️ FALTA: Gravar impostos/valores se houver DI/DUIMP
```

---

## ✅ Checklist de Implementação

### **Fase 1: Estrutura**
- [ ] Criar tabela `IMPOSTO_IMPORTACAO` no script SQL
- [ ] Criar tabela `VALOR_MERCADORIA` no script SQL
- [ ] Executar script SQL no banco `mAIke_assistente`

### **Fase 2: Serviço**
- [ ] Criar `services/imposto_valor_service.py`
- [ ] Implementar `gravar_impostos_di()`
- [ ] Implementar `gravar_impostos_duimp()`
- [ ] Implementar `gravar_valores_di()`
- [ ] Implementar `gravar_valores_duimp()`

### **Fase 3: Integração**
- [ ] Integrar em `ProcessoAgent._consultar_status_processo`
- [ ] Integrar em `ProcessoKanbanService._salvar_processo`
- [ ] Integrar em `integracomex_proxy.py` (quando consultar DI)
- [ ] Integrar em `portal_proxy.py` (quando consultar DUIMP)

### **Fase 4: Backfill**
- [ ] Criar script `scripts/popular_banco_maike_backfill.py`
- [ ] Executar backfill de processos do Kanban
- [ ] Executar backfill de processos do SQL Server Make
- [ ] Validar dados gravados

### **Fase 5: Testes**
- [ ] Testar gravação de impostos ao consultar DI
- [ ] Testar gravação de valores ao consultar DI
- [ ] Testar gravação ao sincronizar Kanban
- [ ] Verificar se histórico está sendo gravado

---

## 🎯 Priorização

### **URGENTE (Fazer Agora):**
1. ✅ Corrigir prioridade da tool `consultar_despesas_processo` (já feito)
2. ⚠️ Criar tabelas `IMPOSTO_IMPORTACAO` e `VALOR_MERCADORIA`
3. ⚠️ Criar `ImpostoValorService`
4. ⚠️ Integrar gravação de impostos/valores no `ProcessoAgent`

### **IMPORTANTE (Próxima Semana):**
5. ⚠️ Integrar gravação no `ProcessoKanbanService`
6. ⚠️ Criar script de backfill
7. ⚠️ Executar backfill inicial

### **FUTURO:**
8. ⚠️ Sincronização contínua Kanban → SQL Server
9. ⚠️ Dashboard de validação de dados

---

## 📝 Notas Importantes

1. **Não bloquear consultas:** Gravação de impostos/valores deve ser não-bloqueante (try/except)
2. **Performance:** Usar transações para gravar múltiplos impostos/valores de uma vez
3. **Duplicatas:** Verificar se já existe antes de gravar (usar `numero_documento` + `tipo_imposto` como chave única)
4. **Validação:** Validar dados antes de gravar (valores não podem ser negativos, etc.)

---

**Última atualização:** 08/01/2026  
**Status:** 📋 Planejamento - Aguardando implementação


