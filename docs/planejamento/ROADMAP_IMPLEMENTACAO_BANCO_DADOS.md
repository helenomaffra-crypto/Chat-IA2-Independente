# 🗺️ Roadmap de Implementação - Banco de Dados mAIke_assistente

**Data:** 08/01/2026  
**Versão:** 1.0  
**Status:** 📋 Planejamento de Implementação

---

## 🎯 Objetivo

Implementar o banco de dados `mAIke_assistente` de forma **priorizada e incremental**, focando primeiro nas funcionalidades críticas para **rastreamento de origem dos recursos** e **compliance com Receita Federal**.

### 🧩 Motivação adicional (performance e simplificação das tools)

Além de compliance, um dos motivadores centrais da criação do `mAIke_assistente` foi **facilitar e acelerar** as consultas usadas pelas tools.

**Dor atual (antes da consolidação):**
- As queries das tools acabam buscando dados em **múltiplos lugares** (ex.: **BD Serpro/Integra Comex**, **BD Portal Único/DUIMP**, **ShipsGo** / tracking, **JSON do Kanban**, cache **SQLite**), com regras de merge/fallback.
- Isso aumenta complexidade, risco de inconsistência (campos vazios em uma fonte “sobrescrevendo” outra), e custo de manutenção (cada mudança de API impacta várias queries).

**Tese do `mAIke_assistente`:**
- Centralizar os dados “prontos para consulta” em uma base interna **consolidada**, reduzindo o número de joins/consultas externas por tool.
- Manter a camada **DTO/adapters** como ponto de acoplamento com APIs, para que mudanças nas APIs não “explodam” o restante do sistema.

**Resultado esperado (quando o roadmap estiver concluído):**
- Tools consultam **um caminho dominante** (preferencialmente `mAIke_assistente` e/ou views materializadas), usando SQLite/Kanban como cache/contexto de “ativos” quando fizer sentido.
- Menos consultas bilhetadas e menos dependência do “JSON cru” do Kanban para relatórios e status.

---

## 📊 Situação Atual

**Banco criado:** `mAIke_assistente` (08/01/2026)  
**Tabelas existentes:** 2 (estrutura básica)
- `PROCESSO_IMPORTACAO` (versão simplificada)
- `TRANSPORTE` (versão simplificada)

**Planejamento completo:** 27 tabelas + 4 views materializadas  
**Documentação:** `docs/PLANEJAMENTO_BANCO_DADOS_MAIKE.md` (v1.4)

---

## 🚨 Priorização Baseada em Criticidade

### ⭐ **PRIORIDADE CRÍTICA** - Compliance e Rastreamento de Recursos

**Objetivo:** Permitir responder intimações da Receita Federal sobre origem dos recursos.

**Tabelas necessárias:**
1. ✅ `MOVIMENTACAO_BANCARIA` - Lançamentos bancários individuais
2. ✅ `MOVIMENTACAO_BANCARIA_PROCESSO` - Divisão de lançamentos entre processos/categorias
3. ✅ `RASTREAMENTO_RECURSO` - Rastreamento completo da origem
4. ✅ `DESPESA_PROCESSO` - Despesas por processo/categoria
5. ✅ `CONCILIACAO_BANCARIA` - Conciliação automática
6. ✅ `COMPROVANTE_RECURSO` - Arquivo de comprovantes (NOVO)
7. ✅ `VALIDACAO_ORIGEM_RECURSO` - Validações de origem (NOVO)
8. ✅ `FORNECEDOR_CLIENTE` - CPF/CNPJ validados

**Por que crítico:**
- Foco principal da aplicação: origem do dinheiro
- Necessário para responder intimações da Receita Federal
- Previne interposição fraudulenta
- Base para todas as outras funcionalidades financeiras

---

### 🔴 **PRIORIDADE ALTA** - Estrutura Base de Processos

**Objetivo:** Consolidar dados de processos de todas as fontes.

**Tabelas necessárias:**
1. ✅ `PROCESSO_IMPORTACAO` (versão completa) - Tabela central
2. ✅ `DOCUMENTO_ADUANEIRO` - CE, CCT, DI, DUIMP consolidados
3. ✅ `TIMELINE_PROCESSO` - Histórico de mudanças
4. ✅ `SHIPSGO_TRACKING` - ETA e tracking

**Por que alta:**
- Base para vincular recursos a processos
- Necessário para relatórios e análises
- Integração com sistemas existentes

---

### 🟡 **PRIORIDADE MÉDIA** - Integrações e Validações

**Objetivo:** Integrar com APIs externas e validar dados.

**Tabelas necessárias:**
1. ✅ `CONSULTA_BILHETADA` - Rastreamento de consultas
2. ✅ `CONSULTA_BILHETADA_PENDENTE` - Fila de aprovações
3. ✅ `VALIDACAO_DADOS_OFICIAIS` - Validação com APIs oficiais
4. ✅ `VERIFICACAO_AUTOMATICA` - Agendamento de verificações

**Por que média:**
- Melhora qualidade dos dados
- Reduz necessidade de consultas bilhetadas
- Importante, mas não crítico para compliance

---

### 🟢 **PRIORIDADE BAIXA** - Comunicação e IA

**Objetivo:** Funcionalidades de comunicação e aprendizado.

**Tabelas necessárias:**
1. ✅ `EMAIL_ENVIADO` / `EMAIL_AGENDADO` - Comunicação
2. ✅ `CONVERSA_CHAT` - Histórico de conversas
3. ✅ `REGRA_APRENDIDA` - Regras aprendidas
4. ✅ `CONTEXTO_SESSAO` - Contexto de sessão
5. ✅ `CONSULTA_SALVA` - Consultas salvas

**Por que baixa:**
- Funcionalidades já existem no SQLite
- Não crítico para compliance
- Pode ser migrado depois

---

### ⚪ **PRIORIDADE FUTURA** - Legislação e Auditoria

**Objetivo:** Vetorização de legislação e logs completos.

**Tabelas necessárias:**
1. ✅ `LEGISLACAO_IMPORTADA` / `LEGISLACAO_VETORIZACAO` / `LEGISLACAO_CHUNK`
2. ✅ `LOG_SINCRONIZACAO` / `LOG_CONSULTA_API` / `LOG_ERRO`

**Por que futura:**
- Legislação já está no Assistants API
- Logs podem ser implementados depois
- Não crítico para funcionalidade principal

---

## 📅 Plano de Implementação por Fases

### **FASE 1: Compliance e Rastreamento (SEMANA 1)** ⭐ **CRÍTICO**

**Objetivo:** Implementar estrutura completa para rastreamento de origem dos recursos.

**Tabelas a criar:**
1. `MOVIMENTACAO_BANCARIA` (com campos de validação)
2. `MOVIMENTACAO_BANCARIA_PROCESSO` (N:N)
3. `RASTREAMENTO_RECURSO` (com campos de origem completos)
4. `DESPESA_PROCESSO` (com suporte a categoria)
5. `CONCILIACAO_BANCARIA` (com suporte a categoria)
6. `COMPROVANTE_RECURSO` (NOVO)
7. `VALIDACAO_ORIGEM_RECURSO` (NOVO)
8. `FORNECEDOR_CLIENTE` (para validação de CPF/CNPJ)

**Funcionalidades:**
- ✅ Registrar lançamentos bancários individuais
- ✅ Dividir lançamentos entre processos/categorias
- ✅ Rastrear origem completa de cada recurso
- ✅ Validar CPF/CNPJ de contrapartidas
- ✅ Arquivar comprovantes
- ✅ Gerar relatórios para intimações

**Entregável:** Sistema capaz de responder intimações da Receita Federal

---

### **FASE 2: Estrutura Base (SEMANA 2)**

**Objetivo:** Consolidar dados de processos.

**Tabelas a criar:**
1. `PROCESSO_IMPORTACAO` (versão completa - atualizar existente)
2. `DOCUMENTO_ADUANEIRO` (CE, CCT, DI, DUIMP)
3. `TIMELINE_PROCESSO` (histórico)
4. `SHIPSGO_TRACKING` (ETA)

**Funcionalidades:**
- ✅ Consolidar processos de todas as fontes
- ✅ Consolidar documentos aduaneiros
- ✅ Histórico completo de mudanças
- ✅ ETA e tracking

**Entregável:** Base consolidada de processos e documentos

---

### **FASE 3: Integrações (SEMANA 3)**

**Objetivo:** Integrar com APIs e validar dados.

**Tabelas a criar:**
1. `CONSULTA_BILHETADA`
2. `CONSULTA_BILHETADA_PENDENTE`
3. `VALIDACAO_DADOS_OFICIAIS`
4. `VERIFICACAO_AUTOMATICA`

**Funcionalidades:**
- ✅ Rastrear consultas bilhetadas
- ✅ Fila de aprovações
- ✅ Validação automática com APIs oficiais
- ✅ Verificações periódicas

**Entregável:** Sistema de validação e integração completo

---

### **FASE 4: Comunicação e IA (SEMANA 4)**

**Objetivo:** Migrar funcionalidades de comunicação e IA.

**Tabelas a criar:**
1. `EMAIL_ENVIADO` / `EMAIL_AGENDADO`
2. `CONVERSA_CHAT`
3. `REGRA_APRENDIDA`
4. `CONTEXTO_SESSAO`
5. `CONSULTA_SALVA`

**Funcionalidades:**
- ✅ Migrar dados do SQLite
- ✅ Histórico de emails
- ✅ Conversas do chat
- ✅ Regras aprendidas

**Entregável:** Sistema de comunicação e IA migrado

---

### **FASE 5: Legislação e Auditoria (SEMANA 5+)**

**Objetivo:** Vetorização e logs completos.

**Tabelas a criar:**
1. `LEGISLACAO_IMPORTADA` / `LEGISLACAO_VETORIZACAO` / `LEGISLACAO_CHUNK`
2. `LOG_SINCRONIZACAO` / `LOG_CONSULTA_API` / `LOG_ERRO`

**Funcionalidades:**
- ✅ Migrar legislações do Assistants API
- ✅ Logs completos de sincronização
- ✅ Auditoria completa

**Entregável:** Sistema completo de legislação e auditoria

---

## 🎯 Foco Imediato: FASE 1

### Por que começar pela FASE 1?

1. **Foco principal:** Rastreamento de origem dos recursos
2. **Compliance crítico:** Necessário para responder intimações
3. **Base para tudo:** Outras funcionalidades dependem disso
4. **Valor imediato:** Resolve o problema principal

### Checklist FASE 1:

- [ ] Criar schemas necessários
- [ ] Criar tabela `MOVIMENTACAO_BANCARIA` (completa)
- [ ] Criar tabela `MOVIMENTACAO_BANCARIA_PROCESSO`
- [ ] Criar tabela `RASTREAMENTO_RECURSO` (com campos de origem)
- [ ] Criar tabela `DESPESA_PROCESSO` (com suporte a categoria)
- [ ] Criar tabela `CONCILIACAO_BANCARIA` (com suporte a categoria)
- [ ] Criar tabela `COMPROVANTE_RECURSO`
- [ ] Criar tabela `VALIDACAO_ORIGEM_RECURSO`
- [ ] Criar tabela `FORNECEDOR_CLIENTE`
- [ ] Criar índices estratégicos
- [ ] Testar estrutura criada
- [ ] Documentar estrutura

---

## 📋 Ordem de Criação Recomendada

### 1. Schemas (primeiro)
```sql
CREATE SCHEMA [comunicacao];
CREATE SCHEMA [ia];
CREATE SCHEMA [legislacao];
CREATE SCHEMA [auditoria];
```

### 2. Tabelas Críticas (FASE 1)
```sql
-- Ordem sugerida:
1. FORNECEDOR_CLIENTE (base para validações)
2. MOVIMENTACAO_BANCARIA (base para tudo)
3. PROCESSO_IMPORTACAO (atualizar existente)
4. MOVIMENTACAO_BANCARIA_PROCESSO
5. RASTREAMENTO_RECURSO
6. DESPESA_PROCESSO
7. CONCILIACAO_BANCARIA
8. COMPROVANTE_RECURSO
9. VALIDACAO_ORIGEM_RECURSO
```

### 3. Tabelas de Suporte (FASE 2)
```sql
10. DOCUMENTO_ADUANEIRO
11. TIMELINE_PROCESSO
12. SHIPSGO_TRACKING
```

### 4. Tabelas de Integração (FASE 3)
```sql
13. CONSULTA_BILHETADA
14. CONSULTA_BILHETADA_PENDENTE
15. VALIDACAO_DADOS_OFICIAIS
16. VERIFICACAO_AUTOMATICA
```

### 5. Tabelas de Comunicação (FASE 4)
```sql
17. EMAIL_ENVIADO
18. EMAIL_AGENDADO
19. WHATSAPP_MENSAGEM
```

### 6. Tabelas de IA (FASE 4)
```sql
20. CONVERSA_CHAT
21. REGRA_APRENDIDA
22. CONTEXTO_SESSAO
23. CONSULTA_SALVA
```

### 7. Tabelas de Legislação (FASE 5)
```sql
24. LEGISLACAO_IMPORTADA
25. LEGISLACAO_VETORIZACAO
26. LEGISLACAO_CHUNK
```

### 8. Tabelas de Auditoria (FASE 5)
```sql
27. LOG_SINCRONIZACAO
28. LOG_CONSULTA_API
29. LOG_ERRO
```

---

## ⚠️ Considerações Importantes

### 1. Atualizar Tabela Existente

**PROCESSO_IMPORTACAO já existe** (versão simplificada). Será necessário:
- Adicionar campos faltantes
- Manter dados existentes
- Fazer migration script

### 2. Dependências entre Tabelas

**Ordem de criação importante:**
- `FORNECEDOR_CLIENTE` → pode ser criada primeiro (sem dependências)
- `MOVIMENTACAO_BANCARIA` → pode ser criada primeiro (sem dependências)
- `PROCESSO_IMPORTACAO` → pode ser atualizada (já existe)
- `MOVIMENTACAO_BANCARIA_PROCESSO` → depende de `MOVIMENTACAO_BANCARIA` e `PROCESSO_IMPORTACAO`
- `RASTREAMENTO_RECURSO` → depende de `MOVIMENTACAO_BANCARIA` e `PROCESSO_IMPORTACAO`
- `DESPESA_PROCESSO` → depende de `PROCESSO_IMPORTACAO`
- `CONCILIACAO_BANCARIA` → depende de `MOVIMENTACAO_BANCARIA` e `DESPESA_PROCESSO`

### 3. Validações e Constraints

**Validações na aplicação (não no banco):**
- Soma de parcelas = valor total do lançamento
- Se `nivel_vinculo = 'PROCESSO'` → `processo_referencia` obrigatório
- Se `nivel_vinculo = 'CATEGORIA'` → `categoria_processo` obrigatório

### 4. Migração de Dados

**Dados existentes no SQLite:**
- Processos (cache)
- Conversas do chat
- Emails enviados
- Consultas salvas

**Estratégia:**
- Criar estrutura primeiro
- Migrar dados depois (script separado)
- Validar dados migrados

---

## 🚀 Próximos Passos Imediatos

1. ✅ **Criar script SQL completo** (todas as 27 tabelas)
2. ✅ **Criar script de migração** (atualizar PROCESSO_IMPORTACAO existente)
3. ✅ **Testar criação** (executar script e validar)
4. ✅ **Documentar estrutura criada**
5. ✅ **Implementar validações** (CPF/CNPJ, contrapartidas)

---

## 📊 Métricas de Sucesso

### FASE 1 (Compliance):
- ✅ Sistema capaz de rastrear origem de 100% dos recursos
- ✅ Validação automática de 100% das contrapartidas
- ✅ Relatórios para intimações gerados em < 5 minutos
- ✅ Documentação completa de cada recurso

### FASE 2 (Estrutura Base):
- ✅ 100% dos processos consolidados
- ✅ 100% dos documentos aduaneiros consolidados
- ✅ Histórico completo de mudanças

### FASE 3 (Integrações):
- ✅ 100% das consultas bilhetadas rastreadas
- ✅ Validação automática de dados oficiais
- ✅ Redução de 50% em consultas bilhetadas

---

**Última atualização:** 08/01/2026  
**Versão:** 1.0

