# 📋 Explicação: Tabela 2 - DOCUMENTO_ADUANEIRO

**Data:** 08/01/2026  
**Objetivo:** Explicar como funciona a gravação de documentos aduaneiros no banco de dados

---

## 🎯 O Que É Gravado

A tabela `DOCUMENTO_ADUANEIRO` armazena **todos os documentos aduaneiros** vinculados aos processos:

- **CE** (Conhecimento de Embarque) - Ex: 172505417636125
- **DI** (Declaração de Importação) - Ex: 2600362869
- **DUIMP** (Declaração Única de Importação) - Ex: 25BR00002284997
- **CCT** (Conhecimento de Carga Aérea) - Ex: 1234567890

**Para cada documento, grava:**
- Número do documento
- Tipo (CE, DI, DUIMP, CCT)
- Processo vinculado (ex: BGR.0070/25)
- Status/situação atual
- Canal (VERDE, AMARELO, VERMELHO) - apenas DI/DUIMP
- Datas importantes (registro, situação, desembaraço)
- JSON completo da API (dados originais)

---

## 🔄 Quando É Gravado

A gravação acontece em **3 momentos diferentes**:

### **1. Quando Consulta Documento via API** ✅ **FUNCIONANDO**

**Arquivo:** `utils/integracomex_proxy.py` (linha 294)

**Fluxo:**
```
1. Usuário consulta: "consulte o CE 172505417636125"
   ↓
2. call_integracomex('/carga/conhecimento-embarque/172505417636125')
   ↓
3. API retorna dados do CE (status 200)
   ↓
4. _gravar_historico_se_documento() é chamado automaticamente
   ↓
5. DocumentoHistoricoService.detectar_e_gravar_mudancas()
   ↓
6. Grava em DOCUMENTO_ADUANEIRO (se documento não existe)
   ↓
7. Grava em HISTORICO_DOCUMENTO_ADUANEIRO (se detectou mudanças)
```

**Código:**
```python
# utils/integracomex_proxy.py (linha 291-299)
if status_code == 200 and body_data and isinstance(body_data, dict):
    _gravar_historico_se_documento(
        path=path,
        response_body=body_data,
        processo_referencia=processo_referencia,
        fonte_dados='INTEGRACOMEX',
        api_endpoint=path
    )
```

**Status:** ✅ **FUNCIONANDO** - Grava quando consulta API diretamente

---

### **2. Quando Sincroniza Processo do Kanban** ✅ **FUNCIONANDO PARCIALMENTE**

**Arquivo:** `services/processo_kanban_service.py` (linha 285-290)

**Fluxo:**
```
1. Sincronização automática do Kanban (a cada 5 min)
   ↓
2. ProcessoKanbanService.sincronizar()
   ↓
3. Para cada processo, chama _salvar_processo()
   ↓
4. Após salvar no SQLite, chama _gravar_historico_documentos()
   ↓
5. Extrai documentos do JSON do Kanban (CE, DI, DUIMP, CCT)
   ↓
6. Para cada documento, chama DocumentoHistoricoService
   ↓
7. Grava em DOCUMENTO_ADUANEIRO (se documento não existe)
   ↓
8. Grava em HISTORICO_DOCUMENTO_ADUANEIRO (se detectou mudanças)
```

**Código:**
```python
# services/processo_kanban_service.py (linha 285-290)
# ✅ NOVO: Gravar histórico de documentos após salvar processo
try:
    self._gravar_historico_documentos(dto, processo_json)
except Exception as e:
    logger.warning(f"⚠️ Erro ao gravar histórico de documentos: {e}")
```

**Status:** ✅ **FUNCIONANDO** - Grava quando sincroniza Kanban

**O que grava:**
- Extrai CE, DI, DUIMP, CCT do JSON do Kanban
- Grava cada documento encontrado
- Detecta mudanças e grava histórico

---

### **3. Quando Consulta Processo (Usando Cache)** ⚠️ **NÃO ESTÁ GRAVANDO**

**Problema:** Quando você consulta "situacao do bgr.0070/25", o sistema:
1. Busca do cache (SQLite) - **NÃO consulta API**
2. Retorna dados do cache
3. **NÃO grava em DOCUMENTO_ADUANEIRO** (porque não consultou API)

**Fluxo atual (problemático):**
```
1. Usuário: "situacao do bgr.0070/25"
   ↓
2. ProcessoAgent._consultar_status_processo()
   ↓
3. ProcessoRepository.buscar_por_referencia()
   ↓
4. Busca do SQLite (cache) - ✅ Encontrou
   ↓
5. Retorna dados do cache
   ↓
6. ⚠️ NÃO consulta API
   ↓
7. ⚠️ NÃO grava em DOCUMENTO_ADUANEIRO
```

**Solução proposta:** Ver `docs/ANALISE_HISTORICO_NAO_GRAVADO.md` - Solução 2

---

## 📊 Exemplo: BGR.0070/25

### **O Que Deveria Estar Gravado:**

#### **1. CE 172505417636125**

```sql
INSERT INTO dbo.DOCUMENTO_ADUANEIRO (
    numero_documento,           -- '172505417636125'
    tipo_documento,             -- 'CE'
    processo_referencia,        -- 'BGR.0070/25'
    
    -- Status
    situacao_documento,         -- 'VINCULADA_A_DOCUMENTO_DE_DESPACHO'
    canal_documento,            -- NULL (CE não tem canal)
    
    -- Datas
    data_registro,              -- Data de registro do CE
    data_situacao,              -- Data da situação atual
    data_desembaraco,           -- Data de desembaraço
    
    -- Valores
    valor_frete_total,         -- 1777.89
    valor_frete_moeda,          -- 'BRL'
    
    -- Fonte
    fonte_dados,                -- 'INTEGRACOMEX' ou 'KANBAN_API'
    json_dados_originais,       -- JSON completo da API
    criado_em,                  -- '2026-01-08 09:20:00'
    atualizado_em               -- '2026-01-08 09:20:00'
)
```

#### **2. DI 2600362869**

```sql
INSERT INTO dbo.DOCUMENTO_ADUANEIRO (
    numero_documento,           -- '2600362869'
    tipo_documento,             -- 'DI'
    processo_referencia,        -- 'BGR.0070/25'
    
    -- Status
    situacao_documento,         -- 'PARAMETRIZADA_AGUARDANDO_ANALISE_FISCAL'
    canal_documento,            -- NULL (se não disponível)
    situacao_entrega,           -- 'ENTREGA NAO AUTORIZADA'
    
    -- Datas
    data_registro,              -- Data de registro da DI
    data_situacao,              -- Data da situação atual
    data_desembaraco,           -- '2026-01-06'
    
    -- Importador
    nome_importador,            -- 'MASSY DO BRASIL COMERCIO EXTERIOR LTDA'
    
    -- Fonte
    fonte_dados,                -- 'INTEGRACOMEX' ou 'KANBAN_API'
    json_dados_originais,       -- JSON completo da API
    criado_em,                  -- '2026-01-08 09:20:00'
    atualizado_em               -- '2026-01-08 09:20:00'
)
```

---

## 🔍 Como Verificar Se Está Gravado

### **Script de Verificação:**

```python
# testes/verificar_documentos_bgr_0070.py
from utils.sql_server_adapter import get_sql_adapter

sql_adapter = get_sql_adapter()

# Buscar documentos do BGR.0070/25
query = """
    SELECT 
        numero_documento,
        tipo_documento,
        situacao_documento,
        canal_documento,
        data_registro,
        data_situacao,
        data_desembaraco,
        fonte_dados,
        criado_em,
        atualizado_em
    FROM dbo.DOCUMENTO_ADUANEIRO
    WHERE processo_referencia = 'BGR.0070/25'
    ORDER BY tipo_documento, criado_em DESC
"""

result = sql_adapter.execute_query(query, database='mAIke_assistente')
```

**Esperado:**
- ✅ 2 registros (CE + DI)
- ✅ Dados completos (status, datas, etc.)
- ✅ Fonte: 'KANBAN_API' ou 'INTEGRACOMEX'

---

## ⚠️ Problemas Atuais

### **Problema 1: Não Grava Quando Usa Cache**

**Cenário:**
- Consulta processo que já está no cache
- Sistema retorna dados do cache
- **NÃO grava em DOCUMENTO_ADUANEIRO**

**Solução:** Implementar gravação do cache (ver `docs/ANALISE_HISTORICO_NAO_GRAVADO.md`)

---

### **Problema 2: Dados Incompletos do Kanban**

**Cenário:**
- Kanban pode ter dados resumidos (não completos)
- Documento gravado com dados incompletos
- Faltam campos importantes (valores, impostos, etc.)

**Solução:** Quando consultar documento via API, atualizar com dados completos

---

## ✅ Resumo

| Momento | Status | O Que Grava |
|---------|--------|-------------|
| **Consulta API** | ✅ Funcionando | Grava documento completo |
| **Sincronização Kanban** | ✅ Funcionando | Grava documentos do JSON |
| **Consulta Cache** | ⚠️ Não grava | Precisa implementar |

---

## 🎯 Próximos Passos

1. ✅ **Criar script de verificação** para BGR.0070/25
2. ⚠️ **Implementar gravação do cache** (quando consulta processo)
3. ⚠️ **Validar dados gravados** no banco
4. ⚠️ **Atualizar documentos** quando consulta API (completar dados)

---

**Última atualização:** 08/01/2026


