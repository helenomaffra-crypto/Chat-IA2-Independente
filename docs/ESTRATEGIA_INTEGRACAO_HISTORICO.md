# 🎯 Estratégia de Integração de Histórico de Documentos

**Data:** 08/01/2026  
**Status:** 📋 Estratégia Definida  
**Baseado em:** `docs/MAPEAMENTO_COMPLETO_APIS.md`

---

## 📊 Análise do Mapeamento

### APIs que Retornam Documentos Aduaneiros

| API | Documentos | Proxy | Chamadas/Dia | Prioridade |
|-----|-----------|-------|--------------|------------|
| **Integra Comex** | CE, DI, CCT | `utils/integracomex_proxy.py` | Alta | ⭐⭐⭐ CRÍTICA |
| **Portal Único** | DUIMP, CCT | `utils/portal_proxy.py` | Alta | ⭐⭐⭐ CRÍTICA |
| **API Kanban** | CE, DI, DUIMP, CCT (consolidado) | `services/processo_kanban_service.py` | Média | ⭐⭐ ALTA |

### APIs que NÃO Retornam Documentos Aduaneiros

| API | Tipo | Integrar Histórico? |
|-----|------|---------------------|
| Banco do Brasil | Extratos bancários | ❌ NÃO |
| Santander | Extratos bancários | ❌ NÃO |
| ShipsGo | ETA/Tracking | ⚠️ PARCIAL (já rastreado em TIMELINE_PROCESSO) |
| OpenAI | Legislação | ❌ NÃO |
| TECwin | Alíquotas NCM | ❌ NÃO |

---

## 🎯 Estratégia Recomendada: Abordagem Híbrida

### Fase 1: Integração Centralizada nos Proxies ⭐ **PRIORIDADE MÁXIMA**

**Vantagens:**
- ✅ **Um único ponto de integração** por API
- ✅ **Cobre todas as chamadas** automaticamente
- ✅ **Menos código duplicado**
- ✅ **Mais fácil de manter**
- ✅ **Não precisa modificar múltiplos serviços**

**Onde integrar:**

#### 1.1. `utils/integracomex_proxy.py` → `call_integracomex()`

**Documentos cobertos:** CE, DI, CCT

**Implementação:**
```python
def call_integracomex(
    path: str,
    query: Optional[Dict[str, Any]] = None,
    # ... outros parâmetros ...
    processo_referencia: Optional[str] = None
) -> Tuple[int, Any]:
    """Função auxiliar para fazer requisições HTTP à API Integra Comex."""
    
    # ... código existente de autenticação e requisição ...
    
    # Após obter resposta
    if status == 200 and response_body:
        # Detectar tipo de documento e gravar histórico
        _gravar_historico_se_documento(
            path=path,
            response_body=response_body,
            processo_referencia=processo_referencia,
            fonte_dados='INTEGRACOMEX',
            api_endpoint=path
        )
    
    return status, response_body

def _gravar_historico_se_documento(
    path: str,
    response_body: Dict[str, Any],
    processo_referencia: Optional[str],
    fonte_dados: str,
    api_endpoint: str
):
    """Grava histórico se a resposta for de um documento aduaneiro"""
    try:
        from services.documento_historico_service import DocumentoHistoricoService
        
        # Detectar tipo de documento pelo path
        tipo_documento = None
        numero_documento = None
        
        if '/conhecimento-embarque/' in path:
            tipo_documento = 'CE'
            # Extrair número do CE do path ou response_body
            numero_documento = _extrair_numero_ce(path, response_body)
        elif '/declaracao-importacao/' in path:
            tipo_documento = 'DI'
            numero_documento = _extrair_numero_di(path, response_body)
        elif '/conhecimento-carga-aerea/' in path:
            tipo_documento = 'CCT'
            numero_documento = _extrair_numero_cct(path, response_body)
        
        if tipo_documento and numero_documento:
            historico_service = DocumentoHistoricoService()
            historico_service.detectar_e_gravar_mudancas(
                numero_documento=numero_documento,
                tipo_documento=tipo_documento,
                dados_novos=response_body,
                fonte_dados=fonte_dados,
                api_endpoint=api_endpoint,
                processo_referencia=processo_referencia
            )
    except Exception as e:
        # Não bloquear se houver erro
        logger.warning(f"⚠️ Erro ao gravar histórico: {e}")
```

#### 1.2. `utils/portal_proxy.py` → `call_portal()`

**Documentos cobertos:** DUIMP, CCT

**Implementação:**
```python
def call_portal(
    path: str,
    query: Optional[Dict[str, Any]] = None,
    # ... outros parâmetros ...
) -> Tuple[int, Any]:
    """Função auxiliar centralizada para fazer requisições HTTP ao Portal Único."""
    
    # ... código existente de autenticação e requisição ...
    
    # Após obter resposta
    if status == 200 and response_body:
        # Detectar tipo de documento e gravar histórico
        _gravar_historico_se_documento(
            path=path,
            response_body=response_body,
            processo_referencia=None,  # Portal não passa processo_referencia
            fonte_dados='PORTAL_UNICO',
            api_endpoint=path
        )
    
    return status, response_body

def _gravar_historico_se_documento(
    path: str,
    response_body: Dict[str, Any],
    processo_referencia: Optional[str],
    fonte_dados: str,
    api_endpoint: str
):
    """Grava histórico se a resposta for de um documento aduaneiro"""
    try:
        from services.documento_historico_service import DocumentoHistoricoService
        
        # Detectar tipo de documento pelo path
        tipo_documento = None
        numero_documento = None
        
        if '/duimp' in path:
            tipo_documento = 'DUIMP'
            # Extrair número e versão do path ou response_body
            numero_documento = _extrair_numero_duimp(path, response_body)
        elif '/ccta/' in path:
            tipo_documento = 'CCT'
            numero_documento = _extrair_numero_cct(path, response_body)
        
        if tipo_documento and numero_documento:
            historico_service = DocumentoHistoricoService()
            historico_service.detectar_e_gravar_mudancas(
                numero_documento=numero_documento,
                tipo_documento=tipo_documento,
                dados_novos=response_body,
                fonte_dados=fonte_dados,
                api_endpoint=api_endpoint,
                processo_referencia=processo_referencia
            )
    except Exception as e:
        # Não bloquear se houver erro
        logger.warning(f"⚠️ Erro ao gravar histórico: {e}")
```

---

### Fase 2: Integração no Kanban (Complementar)

**Onde:** `services/processo_kanban_service.py`

**Situação atual:**
- ✅ Já detecta mudanças via `NotificacaoService`
- ✅ Já compara versão anterior vs nova
- ⚠️ **Falta:** Gravar histórico de documentos específicos

**Implementação:**
```python
def _salvar_processo(self, processo_json: Dict[str, Any]) -> bool:
    """Salva processo no SQLite e detecta mudanças"""
    
    # ... código existente ...
    
    # Após detectar mudanças via NotificacaoService
    # Adicionar: Gravar histórico de documentos
    
    try:
        from services.documento_historico_service import DocumentoHistoricoService
        historico_service = DocumentoHistoricoService()
        
        # Extrair documentos do JSON
        ce = processo_json.get('ce', {})
        di = processo_json.get('di', {})
        duimp = processo_json.get('duimp', {})
        cct = processo_json.get('cct', {})
        
        processo_ref = processo_json.get('numeroPedido')
        
        # Gravar histórico de CE
        if ce and ce.get('numero'):
            historico_service.detectar_e_gravar_mudancas(
                numero_documento=ce.get('numero'),
                tipo_documento='CE',
                dados_novos=ce,
                fonte_dados='KANBAN_API',
                api_endpoint='/api/kanban/pedidos',
                processo_referencia=processo_ref
            )
        
        # Gravar histórico de DI
        if di and di.get('numero'):
            historico_service.detectar_e_gravar_mudancas(
                numero_documento=di.get('numero'),
                tipo_documento='DI',
                dados_novos=di,
                fonte_dados='KANBAN_API',
                api_endpoint='/api/kanban/pedidos',
                processo_referencia=processo_ref
            )
        
        # Gravar histórico de DUIMP
        if duimp and duimp.get('numero'):
            historico_service.detectar_e_gravar_mudancas(
                numero_documento=duimp.get('numero'),
                tipo_documento='DUIMP',
                dados_novos=duimp,
                fonte_dados='KANBAN_API',
                api_endpoint='/api/kanban/pedidos',
                processo_referencia=processo_ref
            )
        
        # Gravar histórico de CCT
        if cct and cct.get('numero'):
            historico_service.detectar_e_gravar_mudancas(
                numero_documento=cct.get('numero'),
                tipo_documento='CCT',
                dados_novos=cct,
                fonte_dados='KANBAN_API',
                api_endpoint='/api/kanban/pedidos',
                processo_referencia=processo_ref
            )
    except Exception as e:
        logger.warning(f"⚠️ Erro ao gravar histórico de documentos do Kanban: {e}")
    
    return True
```

---

## 📋 Plano de Implementação

### Fase 1: Integração Centralizada (Prioridade Máxima)

**Objetivo:** Cobrir 80% das consultas automaticamente

**Tarefas:**
1. ✅ Criar função auxiliar `_gravar_historico_se_documento()` em `utils/integracomex_proxy.py`
2. ✅ Criar função auxiliar `_gravar_historico_se_documento()` em `utils/portal_proxy.py`
3. ✅ Criar funções auxiliares para extrair número de documento do path/response
4. ✅ Integrar após obter resposta da API
5. ✅ Testar com consultas de CE, DI, CCT, DUIMP

**Estimativa:** 2-3 horas

**Cobertura esperada:**
- ✅ 100% das consultas diretas de CE (Integra Comex)
- ✅ 100% das consultas diretas de DI (Integra Comex)
- ✅ 100% das consultas diretas de CCT (Integra Comex)
- ✅ 100% das consultas/criações/atualizações de DUIMP (Portal Único)
- ✅ 100% das consultas de CCT (Portal Único)

---

### Fase 2: Integração no Kanban (Complementar)

**Objetivo:** Cobrir consultas via Kanban (dados consolidados)

**Tarefas:**
1. ✅ Adicionar gravação de histórico em `services/processo_kanban_service.py`
2. ✅ Extrair documentos do JSON do Kanban
3. ✅ Gravar histórico para cada documento encontrado
4. ✅ Testar sincronização de processos

**Estimativa:** 1-2 horas

**Cobertura esperada:**
- ✅ 100% das sincronizações de processos do Kanban
- ✅ Histórico de documentos via dados consolidados

---

### Fase 3: Validação e Testes

**Tarefas:**
1. ✅ Testar com documento novo
2. ✅ Testar com mudança de status
3. ✅ Testar com mudança de canal
4. ✅ Testar sem mudanças
5. ✅ Validar dados gravados no banco
6. ✅ Verificar performance (não deve impactar consultas)

**Estimativa:** 1-2 horas

---

## 🎯 Decisões de Design

### 1. **Detecção de Tipo de Documento**

**Estratégia:** Detectar pelo path da API

**Exemplos:**
- `/carga/conhecimento-embarque/{numero}` → CE
- `/declaracao-importacao/{numero}` → DI
- `/carga/conhecimento-carga-aerea/{numero}` → CCT
- `/duimp-api/api/ext/duimp/{numero}/{versao}` → DUIMP
- `/duimp-api/api/ext/ccta/{awb}` → CCT

### 2. **Extração de Número de Documento**

**Estratégia:** Extrair do path primeiro, depois do response_body

**Exemplos:**
- Path: `/carga/conhecimento-embarque/132505371482300` → `132505371482300`
- Path: `/declaracao-importacao/2521440840` → `2521440840`
- Response: `{"identificacao": {"numero": "25BR00001928777"}}` → `25BR00001928777`

### 3. **Processo de Referência**

**Estratégia:** Passar quando disponível, buscar quando não disponível

**Fontes:**
- Parâmetro `processo_referencia` (quando disponível)
- Response body (algumas APIs retornam)
- Buscar no banco por número do documento (fallback)

### 4. **Tratamento de Erros**

**Estratégia:** Não bloquear consultas principais

**Implementação:**
- Try/except em todas as chamadas
- Log warning se houver erro
- Continuar normalmente se falhar

---

## ✅ Vantagens da Abordagem Híbrida

1. ✅ **Cobertura Completa:** Proxies cobrem consultas diretas, Kanban cobre dados consolidados
2. ✅ **Manutenibilidade:** Poucos pontos de integração
3. ✅ **Performance:** Não bloqueia consultas principais
4. ✅ **Robustez:** Erros não afetam funcionalidade principal
5. ✅ **Rastreabilidade:** Todas as mudanças são gravadas automaticamente

---

## 📊 Comparação de Abordagens

| Abordagem | Pontos de Integração | Cobertura | Manutenibilidade | Performance |
|-----------|---------------------|-----------|-------------------|-------------|
| **Centralizada (Proxies)** | 2 pontos | 80% | ⭐⭐⭐ Excelente | ⭐⭐⭐ Excelente |
| **Específica (Serviços)** | 10+ pontos | 100% | ⭐⭐ Boa | ⭐⭐⭐ Excelente |
| **Híbrida (Recomendada)** | 3 pontos | 100% | ⭐⭐⭐ Excelente | ⭐⭐⭐ Excelente |

---

## 🚀 Próximos Passos

1. ✅ **Implementar Fase 1** (Integração Centralizada)
   - Modificar `utils/integracomex_proxy.py`
   - Modificar `utils/portal_proxy.py`
   - Criar funções auxiliares de extração

2. ✅ **Implementar Fase 2** (Integração no Kanban)
   - Modificar `services/processo_kanban_service.py`
   - Extrair documentos do JSON

3. ✅ **Testar e Validar**
   - Testar todas as APIs
   - Validar dados gravados
   - Verificar performance

---

**Última atualização:** 08/01/2026

