# 📅 Especificação: "O QUE TEMOS PRA HOJE"

**Data de Criação:** 2025-01-XX  
**Status:** 📋 Planejamento  
**Prioridade:** 🔥 Alta

---

## 🎯 Objetivo

Criar uma funcionalidade que consolide e apresente todas as informações relevantes para a continuidade do despacho aduaneiro no dia atual, fornecendo uma visão executiva e acionável do que precisa ser feito hoje.

---

## 📋 Funcionalidades Principais

### 1. Dashboard Consolidado do Dia

Agrupar informações críticas em um único resumo visual e estruturado.

#### 1.1 Processos que Chegam Hoje
- **Critérios:**
  - `dataDestinoFinal = hoje`
  - `ETA = hoje` (se disponível)
  - Status: chegando/descarregando
  - Excluir: processos já entregues (`situacao_ce = 'ENTREGUE'`)
  - Excluir: processos já transbordados

- **Informações a exibir:**
  - Referência do processo (ex: VDM.0004/25)
  - Categoria (ALH, VDM, GYM, etc.)
  - Porto de destino
  - ETA (se disponível)
  - Status atual do CE/CCT
  - Modal (Marítimo/Aéreo)

#### 1.2 Processos Prontos para Registro DI/DUIMP
- **Critérios:**
  - `dataDestinoFinal <= hoje`
  - Sem DI/DUIMP registrado
  - Sem pendências bloqueantes
  - Status CE/CCT: DESCARREGADA, RECEPCIONADA, ou similar
  - Excluir: processos já entregues

- **Informações a exibir:**
  - Referência do processo
  - Categoria
  - Data de chegada
  - Tipo de documento necessário (DI ou DUIMP)
  - Status do CE/CCT
  - Motivo da prontidão

#### 1.3 Pendências que Precisam de Ação Hoje
- **Critérios:**
  - ICMS pendente (pode ser resolvido hoje)
  - AFRMM pendente
  - LPCO com exigência
  - Bloqueios ativos no CE/CCT
  - Outras pendências não bloqueantes mas que podem ser resolvidas

- **Informações a exibir:**
  - Referência do processo
  - Tipo de pendência (ICMS, AFRMM, LPCO, Bloqueio)
  - Descrição da pendência
  - Tempo desde que ficou pendente
  - Ação sugerida

#### 1.4 DUIMPs/DI com Status Crítico
- **Critérios:**
  - DUIMP em análise (aguardando resposta)
  - DI com pendência de desembaraço
  - Documentos próximos de expirar
  - DUIMP/DI com bloqueios

- **Informações a exibir:**
  - Número do documento (DUIMP/DI)
  - Processo vinculado
  - Status atual
  - Data de criação/registro
  - Tempo em análise (se aplicável)

#### 1.5 Processos com ETA Antecipado/Atrasado
- **Critérios:**
  - ETA mudou para hoje (antecipação)
  - ETA era hoje e foi adiado (atraso)
  - Comparar ETA atual vs. ETA anterior (se disponível no histórico)

- **Informações a exibir:**
  - Referência do processo
  - ETA original vs. ETA atual
  - Tipo de mudança (antecipação/atraso)
  - Impacto (dias de diferença)

---

### 2. Priorização Inteligente

Ordenar informações por urgência e impacto no despacho.

#### 2.1 Níveis de Prioridade

**🔥 Alta Prioridade:**
- Processos chegando hoje sem DI/DUIMP
- Pendências bloqueantes (bloqueios, LPCO com exigência crítica)
- Documentos expirando hoje
- DUIMPs/DI com bloqueios ativos

**⚠️ Média Prioridade:**
- Processos chegando amanhã (preparar documentação)
- Pendências não bloqueantes (ICMS, AFRMM)
- DUIMPs em análise (aguardando resposta)
- Processos prontos para registro (mas não chegando hoje)

**ℹ️ Baixa Prioridade:**
- Processos em trânsito (sem ação imediata)
- Processos já entregues (apenas monitoramento)
- Informações de contexto (tendências, estatísticas)

#### 2.2 Algoritmo de Priorização

```
PRIORIDADE = f(urgência, impacto, tempo_pendente)

Urgência:
- Chegando hoje: 10
- Chegando amanhã: 7
- Chegando esta semana: 5
- Outros: 3

Impacto:
- Bloqueante: 10
- Não bloqueante mas crítico: 7
- Informativo: 3

Tempo Pendente:
- Hoje: 10
- 1-2 dias: 7
- 3-5 dias: 5
- Mais de 5 dias: 3
```

---

### 3. Alertas e Notificações Proativas

Incluir alertas relevantes baseados em mudanças recentes e ações necessárias.

#### 3.1 Tipos de Alertas

**🚨 Ações Necessárias:**
- "VDM.0004/25 chegou hoje - precisa criar DUIMP"
- "ALH.0174/25 tem ICMS pendente - pode pagar agora"
- "CE 132505371482302 foi manifestado - verificar status"

**✅ Mudanças Recentes:**
- "CE 132505371482302 foi manifestado"
- "DUIMP 25BR00001928777 foi liberada"
- "ICMS de BGR.0057/25 foi resolvido"

**💡 Oportunidades:**
- "GLT.0043/25 está pronto para registro"
- "3 processos chegam amanhã - preparar documentação"
- "5 processos têm ETA antecipado - revisar planejamento"

#### 3.2 Fonte de Alertas

- Sistema de notificações existente (já implementado)
- Mudanças detectadas no último dia
- Comparação com estado anterior

---

### 4. Resumo Estatístico

Métricas rápidas para visão geral do dia.

#### 4.1 Totais do Dia

- **Processos chegando hoje:** X
- **Processos prontos para registro:** Y
- **Pendências ativas:** Z
- **DUIMPs em análise:** W
- **Processos com ETA alterado:** V

#### 4.2 Status por Categoria

- **ALH:** 5 chegando, 2 prontos, 3 pendências
- **VDM:** 3 chegando, 1 pronto, 1 pendência
- **GYM:** 2 chegando, 0 prontos, 2 pendências
- etc.

#### 4.3 Status por Modal

- **Marítimo:** X processos
- **Aéreo:** Y processos

---

### 5. Sugestões de Ações

Recomendações práticas e acionáveis baseadas nos dados consolidados.

#### 5.1 Formato das Sugestões

```
💡 AÇÕES SUGERIDAS
   1. Criar DUIMP para VDM.0004/25 (urgente - chegou hoje)
   2. Verificar ICMS de ALH.0174/25 (pendente há 2 dias)
   3. Aguardar manifestação do CE 132505371482302
   4. Preparar documentação para 3 processos que chegam amanhã
```

#### 5.2 Critérios para Sugestões

- Priorizar ações que desbloqueiam processos
- Considerar urgência (hoje > amanhã > semana)
- Considerar impacto (bloqueante > não bloqueante)
- Limitar a 5-7 sugestões principais

---

### 6. Integração com Histórico

Contexto temporal e comparações para identificar tendências.

#### 6.1 Comparações Temporais

- "Hoje: 5 processos chegando vs. ontem: 3"
- "Pendências: 8 hoje vs. 10 ontem"
- "DUIMPs em análise: 3 hoje vs. 5 ontem"

#### 6.2 Tendências

- "3 processos com ETA antecipado esta semana"
- "Taxa de registro: 80% dos processos que chegaram"
- "Tempo médio de resolução de pendências: 2.5 dias"

---

### 7. Filtros Opcionais

Permitir que o usuário refine a visualização.

#### 7.1 Filtros Disponíveis

- **Por categoria:** "O que temos pra hoje ALH?"
- **Por situação:** "O que temos pra hoje com pendências?"
- **Por modal:** "O que temos pra hoje aéreo?"
- **Por porto:** "O que temos pra hoje no Rio?"
- **Por prioridade:** "O que temos pra hoje urgente?"

#### 7.2 Implementação de Filtros

- Detectar filtros na mensagem do usuário
- Aplicar filtros nas queries
- Manter estrutura de resposta, apenas filtrando conteúdo

---

## 📊 Estrutura da Resposta

### Formato Visual Sugerido

```
📅 O QUE TEMOS PRA HOJE - 15/01/2025

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚢 CHEGANDO HOJE (3 processos)
   • VDM.0004/25 - Porto: BRRIO - ETA: 15/01 - Status: Descarregando
   • ALH.0176/25 - Porto: BRRIO - ETA: 15/01 - Status: Descarregando
   • GYM.0044/25 - Porto: BRRIO - ETA: 15/01 - Status: Descarregando

✅ PRONTOS PARA REGISTRO (2 processos)
   • VDM.0004/25 - Chegou ontem, sem DI/DUIMP - Tipo: DUIMP
   • GLT.0043/25 - CCT recepcionado, sem DUIMP - Tipo: DUIMP

⚠️ PENDÊNCIAS ATIVAS (5 processos)
   • ALH.0174/25 - ICMS pendente (há 2 dias) - Ação: Verificar pagamento
   • DMD.0085/25 - AFRMM pendente (há 1 dia) - Ação: Verificar pagamento
   • BGR.0057/25 - LPCO com exigência - Ação: Verificar documentação

📋 DUIMPs EM ANÁLISE (3)
   • 25BR00001928777 - Em análise desde 13/01 - Processo: ALH.0174/25
   • 25BR00001928778 - Aguardando resposta - Processo: VDM.0004/25

🔄 ETA ALTERADO (2 processos)
   • GYM.0044/25 - ETA antecipado: 16/01 → 15/01 (1 dia antes)
   • DMD.0086/25 - ETA atrasado: 14/01 → 16/01 (2 dias depois)

🔔 ALERTAS
   • ⚠️ CE 132505371482302 foi manifestado - Verificar status
   • ✅ DUIMP 25BR00001928777 foi liberada - Processo: ALH.0174/25
   • 💡 3 processos chegam amanhã - Preparar documentação

💡 AÇÕES SUGERIDAS
   1. Criar DUIMP para VDM.0004/25 (urgente - chegou hoje)
   2. Verificar ICMS de ALH.0174/25 (pendente há 2 dias)
   3. Aguardar manifestação do CE 132505371482302
   4. Preparar documentação para 3 processos que chegam amanhã

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 RESUMO: 3 chegando | 2 prontos | 5 pendências | 3 DUIMPs | 2 ETA alterado

📈 COMPARAÇÃO COM ONTEM:
   • Processos chegando: 3 hoje vs. 2 ontem (+1)
   • Pendências: 5 hoje vs. 7 ontem (-2)
   • DUIMPs em análise: 3 hoje vs. 5 ontem (-2)
```

---

## 🔧 Implementação Técnica

### 1. Funções a Criar/Modificar

#### 1.1 Nova Função: `obter_dashboard_hoje()`

**Localização:** `db_manager.py` ou `services/agents/processo_agent.py`

**Responsabilidade:** Consolidar todas as informações do dia

**Retorno:**
```python
{
    "data": "2025-01-15",
    "processos_chegando_hoje": [...],
    "processos_prontos_registro": [...],
    "pendencias_ativas": [...],
    "duimps_em_analise": [...],
    "processos_eta_alterado": [...],
    "alertas": [...],
    "resumo": {
        "total_chegando": 3,
        "total_prontos": 2,
        "total_pendencias": 5,
        "total_duimps_analise": 3,
        "total_eta_alterado": 2
    },
    "estatisticas_por_categoria": {...},
    "sugestoes_acoes": [...]
}
```

#### 1.2 Funções Auxiliares

**`obter_processos_chegando_hoje()`**
- Query: `SELECT * FROM processos_kanban WHERE dataDestinoFinal = DATE('now') AND situacao_ce != 'ENTREGUE'`

**`obter_processos_prontos_registro()`**
- Query: `SELECT * FROM processos_kanban WHERE dataDestinoFinal <= DATE('now') AND (numero_di IS NULL OR numero_di = '') AND (numero_duimp IS NULL OR numero_duimp = '') AND situacao_ce != 'ENTREGUE'`

**`obter_pendencias_ativas()`**
- Verificar campos: `pendencia_icms`, `pendencia_afrmm`, `lpco_exigencia`, `bloqueios_ce`

**`obter_duimps_em_analise()`**
- Query: `SELECT * FROM duimps WHERE status IN ('EM_ANALISE', 'AGUARDANDO_RESPOSTA')`

**`obter_processos_eta_alterado()`**
- Comparar ETA atual com ETA do histórico (se disponível)

#### 1.3 Modificar: `ProcessoAgent`

Adicionar método para processar a intenção "O QUE TEMOS PRA HOJE":

```python
def processar_dashboard_hoje(self, filtros=None):
    """
    Processa a intenção 'O QUE TEMOS PRA HOJE'
    
    Args:
        filtros: dict com filtros opcionais (categoria, modal, porto, etc.)
    
    Returns:
        str: Resposta formatada com dashboard consolidado
    """
```

### 2. Queries SQL Necessárias

#### 2.1 Processos Chegando Hoje

```sql
SELECT 
    processo_referencia,
    categoria,
    dataDestinoFinal,
    porto_destino,
    situacao_ce,
    modal,
    numero_ce,
    numero_cct
FROM processos_kanban
WHERE 
    DATE(dataDestinoFinal) = DATE('now')
    AND situacao_ce != 'ENTREGUE'
    AND (transbordo IS NULL OR transbordo = '')
ORDER BY dataDestinoFinal ASC, categoria ASC;
```

#### 2.2 Processos Prontos para Registro

```sql
SELECT 
    processo_referencia,
    categoria,
    dataDestinoFinal,
    modal,
    numero_ce,
    numero_cct,
    situacao_ce,
    CASE 
        WHEN modal = 'Aéreo' THEN 'DUIMP'
        WHEN modal = 'Marítimo' AND numero_ce IS NOT NULL THEN 'DUIMP'
        ELSE 'DI'
    END as tipo_documento
FROM processos_kanban
WHERE 
    DATE(dataDestinoFinal) <= DATE('now')
    AND (numero_di IS NULL OR numero_di = '')
    AND (numero_duimp IS NULL OR numero_duimp = '')
    AND situacao_ce != 'ENTREGUE'
    AND (transbordo IS NULL OR transbordo = '')
    AND (
        situacao_ce IN ('DESCARREGADA', 'RECEPCIONADA', 'ARMAZENADA')
        OR situacao_cct IN ('RECEPCIONADA', 'ARMAZENADA')
    )
ORDER BY dataDestinoFinal DESC, categoria ASC;
```

#### 2.3 Pendências Ativas

```sql
SELECT 
    processo_referencia,
    categoria,
    CASE 
        WHEN pendencia_icms = 1 THEN 'ICMS'
        WHEN pendencia_afrmm = 1 THEN 'AFRMM'
        WHEN lpco_exigencia IS NOT NULL AND lpco_exigencia != '' THEN 'LPCO'
        WHEN bloqueios_ce IS NOT NULL AND bloqueios_ce != '' THEN 'Bloqueio CE'
        ELSE 'Outra'
    END as tipo_pendencia,
    pendencia_icms,
    pendencia_afrmm,
    lpco_exigencia,
    bloqueios_ce,
    data_ultima_atualizacao
FROM processos_kanban
WHERE 
    pendencia_icms = 1 
    OR pendencia_afrmm = 1
    OR (lpco_exigencia IS NOT NULL AND lpco_exigencia != '')
    OR (bloqueios_ce IS NOT NULL AND bloqueios_ce != '')
ORDER BY 
    CASE 
        WHEN bloqueios_ce IS NOT NULL THEN 1
        WHEN lpco_exigencia IS NOT NULL THEN 2
        WHEN pendencia_icms = 1 THEN 3
        WHEN pendencia_afrmm = 1 THEN 4
        ELSE 5
    END,
    data_ultima_atualizacao ASC;
```

#### 2.4 DUIMPs em Análise

```sql
SELECT 
    d.numero as numero_duimp,
    d.versao,
    d.status,
    d.data_criacao,
    pd.processo_referencia
FROM duimps d
LEFT JOIN processo_documentos pd ON d.numero = pd.numero_duimp
WHERE 
    d.status IN ('EM_ANALISE', 'AGUARDANDO_RESPOSTA', 'PENDENTE')
ORDER BY d.data_criacao ASC;
```

#### 2.5 Processos com ETA Alterado

```sql
-- Requer tabela de histórico de mudanças (se disponível)
-- Ou comparar com dados do Kanban JSON anterior
SELECT 
    processo_referencia,
    categoria,
    eta_atual,
    eta_anterior,
    CASE 
        WHEN DATE(eta_atual) < DATE(eta_anterior) THEN 'ANTECIPADO'
        WHEN DATE(eta_atual) > DATE(eta_anterior) THEN 'ATRASADO'
    END as tipo_mudanca,
    ABS(JULIANDAY(eta_atual) - JULIANDAY(eta_anterior)) as dias_diferenca
FROM processos_kanban
WHERE 
    eta_atual IS NOT NULL
    AND eta_anterior IS NOT NULL
    AND DATE(eta_atual) != DATE(eta_anterior)
    AND DATE(eta_atual) = DATE('now')
ORDER BY dias_diferenca DESC;
```

### 3. Integração com Sistema de Notificações

- Reutilizar lógica de detecção de mudanças
- Buscar notificações do último dia
- Filtrar notificações relevantes para o dashboard

### 4. Formatação da Resposta

- Usar `formatarRespostaChat()` existente
- Criar função específica: `formatar_dashboard_hoje()`
- Manter estilo visual consistente com outras respostas

---

## 🎯 Detecção de Intenção

### Padrões de Mensagem

A IA deve detectar a intenção "O QUE TEMOS PRA HOJE" quando o usuário digitar:

- "O que temos pra hoje?"
- "O que temos para hoje?"
- "O que temos hoje?"
- "Dashboard de hoje"
- "Resumo do dia"
- "O que precisa ser feito hoje?"
- "O que está chegando hoje?"
- "Processos de hoje"

### Filtros Opcionais

- "O que temos pra hoje ALH?" → Filtrar por categoria ALH
- "O que temos pra hoje com pendências?" → Filtrar apenas pendências
- "O que temos pra hoje aéreo?" → Filtrar por modal aéreo
- "O que temos pra hoje no Rio?" → Filtrar por porto

---

## 📝 Checklist de Implementação

### Fase 1: Estrutura Base
- [ ] Criar função `obter_dashboard_hoje()` em `db_manager.py`
- [ ] Criar funções auxiliares (chegando hoje, prontos, pendências, etc.)
- [ ] Testar queries SQL individualmente
- [ ] Validar dados retornados

### Fase 2: Integração com Agent
- [ ] Adicionar método `processar_dashboard_hoje()` em `ProcessoAgent`
- [ ] Adicionar detecção de intenção em `chat_service.py`
- [ ] Adicionar tool definition em `tool_definitions.py`
- [ ] Testar detecção de intenção

### Fase 3: Formatação e Visual
- [ ] Criar função `formatar_dashboard_hoje()`
- [ ] Implementar formatação markdown/HTML
- [ ] Testar visualização no chat
- [ ] Ajustar layout e emojis

### Fase 4: Funcionalidades Avançadas
- [ ] Implementar priorização inteligente
- [ ] Integrar com sistema de notificações
- [ ] Adicionar comparações temporais
- [ ] Implementar filtros opcionais

### Fase 5: Testes e Refinamento
- [ ] Testar com dados reais
- [ ] Validar performance (queries otimizadas)
- [ ] Ajustar formatação baseado em feedback
- [ ] Documentar uso

---

## 🚀 Considerações de Performance

### 1. Otimização de Queries

- Usar índices nas colunas frequentemente consultadas:
  - `dataDestinoFinal`
  - `situacao_ce`
  - `processo_referencia`
  - `categoria`

- Limitar resultados quando possível
- Usar `EXPLAIN QUERY PLAN` para otimizar

### 2. Cache

- Cachear resultado do dashboard por alguns minutos (5-10 min)
- Invalidar cache quando houver mudanças significativas
- Considerar cache por categoria/modal

### 3. Agregações

- Calcular estatísticas uma vez e reutilizar
- Evitar queries repetidas para mesmos dados

---

## 📚 Referências

### Arquivos Relacionados

- `db_manager.py` - Funções de banco de dados
- `services/agents/processo_agent.py` - Agent de processos
- `services/chat_service.py` - Serviço de chat
- `services/tool_definitions.py` - Definições de tools
- `docs/FLUXO_DESPACHO_ADUANEIRO.md` - Contexto de negócio

### Funções Existentes que Podem ser Reutilizadas

- `listar_processos_por_situacao()` - Listar processos
- `listar_processos_liberados_registro()` - Processos prontos
- `obter_dados_documentos_processo()` - Dados de documentos
- Sistema de notificações - Alertas e mudanças

---

## 🎨 Exemplo de Implementação Simplificada

### Versão Mínima Viável (MVP)

Para uma primeira versão, focar em:

1. **Processos chegando hoje** ✅
2. **Processos prontos para registro** ✅
3. **Pendências ativas** ✅
4. **Resumo estatístico básico** ✅

Deixar para depois:
- ETA alterado (requer histórico)
- Comparações temporais (requer histórico)
- Filtros avançados (pode ser incremental)

---

## ✅ Critérios de Sucesso

A funcionalidade será considerada bem-sucedida quando:

1. ✅ Usuário consegue ver todas as informações relevantes do dia em um único lugar
2. ✅ Informações estão priorizadas corretamente (urgente primeiro)
3. ✅ Sugestões de ações são práticas e acionáveis
4. ✅ Performance é aceitável (< 2 segundos para carregar)
5. ✅ Visualização é clara e fácil de entender
6. ✅ Integração com sistema existente funciona sem conflitos

---

**Última atualização:** 2025-01-XX  
**Próxima revisão:** Após implementação

