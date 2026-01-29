# 🔄 Integração: Histórico de Mudanças em Documentos

**Data:** 08/01/2026  
**Status:** 📋 Guia de Integração  
**Prioridade:** ⭐ **ALTA** - Implementação necessária

---

## 🎯 Objetivo

Integrar o serviço de histórico de mudanças (`DocumentoHistoricoService`) com os pontos onde as APIs são consultadas, para que todas as mudanças em DI, DUIMP, CE, CCT sejam automaticamente gravadas.

---

## 📋 Onde Integrar

### 1. **Consulta de CE (Conhecimento de Embarque)**

**Arquivo:** `services/consulta_service.py`  
**Método:** `consultar_ce_maritimo()`

**Onde adicionar:**
Após obter resposta da API Integra Comex, antes de retornar resultado.

```python
# Após obter resposta da API
from services.documento_historico_service import DocumentoHistoricoService

historico_service = DocumentoHistoricoService()
historico_service.detectar_e_gravar_mudancas(
    numero_documento=numero_ce,
    tipo_documento='CE',
    dados_novos=resposta_api,  # Dados retornados pela API
    fonte_dados='INTEGRACOMEX',
    api_endpoint='/carga/conhecimento-embarque',
    processo_referencia=processo_referencia
)
```

### 2. **Consulta de CCT (Conhecimento de Carga Aérea)**

**Arquivo:** `services/consulta_service.py` ou `services/agents/cct_agent.py`

**Onde adicionar:**
Após obter resposta da API Integra Comex.

```python
from services.documento_historico_service import DocumentoHistoricoService

historico_service = DocumentoHistoricoService()
historico_service.detectar_e_gravar_mudancas(
    numero_documento=numero_cct,
    tipo_documento='CCT',
    dados_novos=resposta_api,
    fonte_dados='INTEGRACOMEX',
    api_endpoint='/carga/conhecimento-carga-aerea',
    processo_referencia=processo_referencia
)
```

### 3. **Consulta de DI (Declaração de Importação)**

**Arquivo:** `services/consulta_service.py` ou `services/agents/di_agent.py`

**Onde adicionar:**
Após obter resposta da API Integra Comex ou Portal Único.

```python
from services.documento_historico_service import DocumentoHistoricoService

historico_service = DocumentoHistoricoService()
historico_service.detectar_e_gravar_mudancas(
    numero_documento=numero_di,
    tipo_documento='DI',
    dados_novos=resposta_api,
    fonte_dados='INTEGRACOMEX',  # ou 'PORTAL_UNICO'
    api_endpoint='/despacho/declaracao-importacao',
    processo_referencia=processo_referencia
)
```

### 4. **Consulta de DUIMP (Declaração Única de Importação)**

**Arquivo:** `services/duimp_service.py` ou `services/agents/duimp_agent.py`

**Onde adicionar:**
Após obter resposta da API DUIMP.

```python
from services.documento_historico_service import DocumentoHistoricoService

historico_service = DocumentoHistoricoService()
historico_service.detectar_e_gravar_mudancas(
    numero_documento=numero_duimp,
    tipo_documento='DUIMP',
    dados_novos=resposta_api,
    fonte_dados='DUIMP_API',
    api_endpoint='/duimp/consultar',
    processo_referencia=processo_referencia
)
```

---

## 🔄 Fluxo de Integração

### Passo 1: Consultar API

```python
# Código existente
resposta_api = call_integracomex('/carga/conhecimento-embarque', query={'numero': numero_ce})
```

### Passo 2: Detectar e Gravar Mudanças

```python
# NOVO: Adicionar após obter resposta
from services.documento_historico_service import DocumentoHistoricoService

historico_service = DocumentoHistoricoService()
mudancas = historico_service.detectar_e_gravar_mudancas(
    numero_documento=numero_ce,
    tipo_documento='CE',
    dados_novos=resposta_api[1],  # response_body
    fonte_dados='INTEGRACOMEX',
    api_endpoint='/carga/conhecimento-embarque',
    processo_referencia=processo_referencia
)

if mudancas:
    logger.info(f"✅ {len(mudancas)} mudança(ões) detectada(s) e gravada(s)")
```

### Passo 3: Continuar Processamento Normal

```python
# Código existente continua normalmente
# O histórico já foi gravado automaticamente
```

---

## ⚠️ Considerações Importantes

### 1. **Performance**

- O serviço de histórico é **assíncrono** (não bloqueia)
- Se SQL Server não estiver disponível, apenas loga warning
- Não deve impactar performance das consultas

### 2. **Erros**

- Se houver erro ao gravar histórico, **não deve afetar** a consulta principal
- Erros são logados mas não interrompem o fluxo

### 3. **Duplicatas**

- O serviço verifica se documento já existe antes de criar histórico
- Mudanças duplicadas são evitadas comparando valores

### 4. **Dados Incompletos**

- Se API retornar dados incompletos, histórico ainda é gravado
- Campos não disponíveis ficam como NULL

---

## 📊 Exemplo Completo

### Exemplo: Consulta de CE

```python
def consultar_ce_maritimo(self, numero_ce: str, processo_referencia: Optional[str] = None):
    """Consulta CE marítimo e grava histórico de mudanças"""
    
    # 1. Consultar API
    status, resposta = call_integracomex(
        '/carga/conhecimento-embarque',
        query={'numero': numero_ce},
        processo_referencia=processo_referencia
    )
    
    if status != 200:
        return {'erro': 'Erro ao consultar API'}
    
    # 2. NOVO: Detectar e gravar mudanças
    from services.documento_historico_service import DocumentoHistoricoService
    
    historico_service = DocumentoHistoricoService()
    mudancas = historico_service.detectar_e_gravar_mudancas(
        numero_documento=numero_ce,
        tipo_documento='CE',
        dados_novos=resposta,
        fonte_dados='INTEGRACOMEX',
        api_endpoint='/carga/conhecimento-embarque',
        processo_referencia=processo_referencia
    )
    
    # 3. Continuar processamento normal
    # ... código existente ...
    
    return {'sucesso': True, 'dados': resposta, 'mudancas_detectadas': len(mudancas)}
```

---

## ✅ Checklist de Implementação

- [ ] Integrar em `consultar_ce_maritimo()` (ConsultaService)
- [ ] Integrar em consulta de CCT
- [ ] Integrar em consulta de DI
- [ ] Integrar em consulta de DUIMP
- [ ] Testar com documento novo (sem histórico anterior)
- [ ] Testar com documento existente (com mudanças)
- [ ] Testar com documento sem mudanças
- [ ] Verificar se histórico está sendo gravado no SQL Server
- [ ] Verificar se documento está sendo atualizado na tabela DOCUMENTO_ADUANEIRO

---

## 🧪 Testes

### Teste 1: Documento Novo

```python
# Consultar CE que nunca foi consultado antes
# Resultado esperado: Documento criado, sem histórico (não há mudanças)
```

### Teste 2: Mudança de Status

```python
# Consultar CE que mudou de status
# Resultado esperado: Histórico gravado com tipo_evento='MUDANCA_STATUS'
```

### Teste 3: Mudança de Canal

```python
# Consultar DI que mudou de canal (VERDE → AMARELO)
# Resultado esperado: Histórico gravado com tipo_evento='MUDANCA_CANAL'
```

### Teste 4: Sem Mudanças

```python
# Consultar documento que não mudou
# Resultado esperado: Nenhum histórico gravado (sem mudanças detectadas)
```

---

**Última atualização:** 08/01/2026

