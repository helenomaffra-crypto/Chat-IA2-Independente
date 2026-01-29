# 🚀 Sugestões de Melhorias no SQL Server

**Data:** 21/12/2025  
**Contexto:** Refatoração do banco de dados SQL Server para o projeto mAIke

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Problemas Identificados](#problemas-identificados)
3. [Melhorias Prioritárias](#melhorias-prioritárias)
4. [Melhorias de Performance](#melhorias-de-performance)
5. [Melhorias de Estrutura](#melhorias-de-estrutura)
6. [Melhorias de Consistência](#melhorias-de-consistência)
7. [Roadmap de Implementação](#roadmap-de-implementação)

---

## 🎯 Visão Geral

Este documento apresenta sugestões de melhorias no banco de dados SQL Server baseadas em:
- Análise do documento `MAPEAMENTO_SQL_SERVER.md`
- Padrões de uso do mAIke (queries frequentes, problemas encontrados)
- Boas práticas de banco de dados para sistemas de COMEX
- Necessidades de performance e escalabilidade

**Objetivo:** Criar um banco de dados mais robusto, performático e fácil de manter.

---

## ⚠️ Problemas Identificados

### 1. **Formato Inconsistente de Dados**
- **Problema:** `numero_di` pode estar como `25/0340890-6` em uma tabela e `2503408906` em outra
- **Impacto:** Requer normalização em runtime, múltiplas tentativas de busca, performance degradada
- **Frequência:** Alto (afeta todas as buscas de DI)

### 2. **Relacionamentos Indiretos Complexos**
- **Problema:** Vínculo DI-Processo via `id_importacao` → `comex.dbo.Importacoes` → `Hi_Historico_Di`
- **Impacto:** Queries com múltiplos JOINs, difícil de entender, propenso a erros
- **Frequência:** Alto (busca de DI é operação crítica)

### 3. **Campos NULL que Quebram Relacionamentos**
- **Problema:** `numero_di` pode estar NULL mesmo quando a DI existe
- **Impacto:** Requer fallback complexo, código duplicado, manutenção difícil
- **Frequência:** Médio (afeta alguns processos)

### 4. **Falta de Índices em Campos de Busca Frequente**
- **Problema:** Queries com múltiplos JOINs sem índices adequados
- **Impacto:** Performance lenta, especialmente em tabelas grandes
- **Frequência:** Alto (todas as queries)

### 5. **Dados Duplicados entre Tabelas**
- **Problema:** DUIMP tem múltiplas tabelas (`duimp`, `duimp_diagnostico`, `duimp_situacao`) com dados sobrepostos
- **Impacto:** Queries complexas, possível inconsistência
- **Frequência:** Médio (afeta queries de DUIMP)

### 6. **Falta de Campos Calculados/Denormalizados**
- **Problema:** Valores calculados (ex: total de impostos) precisam ser calculados em runtime
- **Impacto:** Performance degradada, código duplicado
- **Frequência:** Médio (afeta relatórios e dashboards)

### 7. **Ausência de Triggers para Sincronização**
- **Problema:** Dados podem ficar desatualizados entre tabelas relacionadas
- **Impacto:** Inconsistência de dados, necessidade de sincronização manual
- **Frequência:** Baixo (mas crítico quando acontece)

---

## 🔥 Melhorias Prioritárias

### **PRIORIDADE 1: Normalização de Campos Críticos**

#### 1.1. Campo `numero_di_normalizado` em `PROCESSO_IMPORTACAO`
**Problema:** `numero_di` pode ter formatos diferentes (`25/0340890-6` vs `2503408906`)

**Solução:**
```sql
-- Adicionar coluna calculada persistida
ALTER TABLE make.dbo.PROCESSO_IMPORTACAO
ADD numero_di_normalizado AS (
    REPLACE(REPLACE(numero_di, '/', ''), '-', '')
) PERSISTED;

-- Criar índice para busca rápida
CREATE NONCLUSTERED INDEX IX_PROCESSO_IMPORTACAO_numero_di_normalizado
ON make.dbo.PROCESSO_IMPORTACAO(numero_di_normalizado)
WHERE numero_di_normalizado IS NOT NULL;
```

**Benefícios:**
- ✅ Busca direta sem normalização em runtime
- ✅ Performance melhorada (índice)
- ✅ Código simplificado (não precisa normalizar em Python)

**Impacto:** Alto - Resolve o problema mais frequente

---

#### 1.2. Campo `numero_ce_normalizado` em `PROCESSO_IMPORTACAO`
**Mesma lógica para CE:**
```sql
ALTER TABLE make.dbo.PROCESSO_IMPORTACAO
ADD numero_ce_normalizado AS (
    REPLACE(REPLACE(numero_ce, '/', ''), '-', '')
) PERSISTED;

CREATE NONCLUSTERED INDEX IX_PROCESSO_IMPORTACAO_numero_ce_normalizado
ON make.dbo.PROCESSO_IMPORTACAO(numero_ce_normalizado)
WHERE numero_ce_normalizado IS NOT NULL;
```

---

### **PRIORIDADE 2: Índices Estratégicos**

#### 2.1. Índices em Campos de JOIN Frequente
**Problema:** JOINs em `id_importacao` sem índices adequados

**Solução:**
```sql
-- Índice em Hi_Historico_Di.idImportacao (CRÍTICO - usado em todas as buscas de DI)
CREATE NONCLUSTERED INDEX IX_Hi_Historico_Di_idImportacao
ON Serpro.dbo.Hi_Historico_Di(idImportacao)
INCLUDE (diId, updatedAt);

-- Índice em Hi_Historico_Ce.idImportacao (para busca de CE relacionado)
CREATE NONCLUSTERED INDEX IX_Hi_Historico_Ce_idImportacao
ON Serpro.dbo.Hi_Historico_Ce(idImportacao)
INCLUDE (ceId, updatedAt);

-- Índice em PROCESSO_IMPORTACAO.id_importacao
CREATE NONCLUSTERED INDEX IX_PROCESSO_IMPORTACAO_id_importacao
ON make.dbo.PROCESSO_IMPORTACAO(id_importacao)
WHERE id_importacao IS NOT NULL;

-- Índice em Importacoes.id (tabela de vínculo)
CREATE NONCLUSTERED INDEX IX_Importacoes_id
ON comex.dbo.Importacoes(id);
```

**Benefícios:**
- ✅ JOINs muito mais rápidos
- ✅ Queries de busca de DI/CE relacionadas otimizadas
- ✅ Redução significativa de tempo de resposta

**Impacto:** Alto - Afeta todas as queries de processo

---

#### 2.2. Índices em Campos de Busca Direta
```sql
-- Índice em Di_Dados_Gerais.numeroDi (busca direta de DI)
CREATE NONCLUSTERED INDEX IX_Di_Dados_Gerais_numeroDi
ON Serpro.dbo.Di_Dados_Gerais(numeroDi)
INCLUDE (situacaoDi, canalSelecaoParametrizada, dataHoraSituacaoDi);

-- Índice em Ce_Root_Conhecimento_Embarque.numero
CREATE NONCLUSTERED INDEX IX_Ce_Root_numero
ON Serpro.dbo.Ce_Root_Conhecimento_Embarque(numero)
INCLUDE (situacaoCarga, portoOrigem, portoDestino, paisProcedencia);

-- Índice em duimp.numero e numero_processo
CREATE NONCLUSTERED INDEX IX_duimp_numero
ON Duimp.dbo.duimp(numero)
INCLUDE (numero_processo, id_processo_importacao, ultima_situacao);

CREATE NONCLUSTERED INDEX IX_duimp_numero_processo
ON Duimp.dbo.duimp(numero_processo)
WHERE numero_processo IS NOT NULL;
```

---

### **PRIORIDADE 3: Views Materializadas para Queries Complexas**

#### 3.1. View `vw_Processo_Completo`
**Problema:** Query de processo completo tem múltiplos JOINs complexos

**Solução:**
```sql
-- View materializada com dados consolidados do processo
CREATE VIEW make.dbo.vw_Processo_Completo
WITH SCHEMABINDING
AS
SELECT 
    pi.id_processo_importacao,
    pi.numero_processo,
    pi.numero_di,
    pi.numero_di_normalizado,
    pi.numero_ce,
    pi.numero_ce_normalizado,
    pi.numero_duimp,
    pi.id_importacao,
    
    -- Dados de DI (se existir)
    ddg.numeroDi AS di_numero,
    ddg.situacaoDi AS di_situacao,
    diDesp.canalSelecaoParametrizada AS di_canal,
    diDesp.dataHoraDesembaraco AS di_data_desembaraco,
    DVMD.totalReais AS di_vlmd_real,
    DVME.totalReais AS di_vlme_real,
    
    -- Dados de CE (se existir)
    ceRoot.numero AS ce_numero,
    ceRoot.situacaoCarga AS ce_situacao,
    ceRoot.portoOrigem AS ce_porto_origem,
    ceRoot.portoDestino AS ce_porto_destino,
    
    -- Dados de DUIMP (se existir)
    d.numero AS duimp_numero,
    dd.situacao_duimp AS duimp_situacao,
    drar.canal_consolidado AS duimp_canal,
    d.data_ultimo_evento AS duimp_data_ultimo_evento
    
FROM make.dbo.PROCESSO_IMPORTACAO pi
LEFT JOIN comex.dbo.Importacoes i ON i.id = pi.id_importacao
LEFT JOIN Serpro.dbo.Hi_Historico_Di diH ON diH.idImportacao = i.id
LEFT JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON diH.diId = diRoot.dadosDiId
LEFT JOIN Serpro.dbo.Di_Dados_Gerais ddg ON diRoot.dadosGeraisId = ddg.dadosGeraisId
LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
LEFT JOIN Serpro.dbo.Hi_Historico_Ce ceH ON ceH.idImportacao = i.id
LEFT JOIN Serpro.dbo.Ce_Root_Conhecimento_Embarque ceRoot ON ceH.ceId = ceRoot.rootConsultaEmbarqueId
LEFT JOIN Duimp.dbo.duimp d ON d.numero_processo = pi.numero_processo
LEFT JOIN Duimp.dbo.duimp_diagnostico dd ON dd.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar ON drar.duimp_id = d.duimp_id;

-- Criar índice único na view materializada
CREATE UNIQUE CLUSTERED INDEX IX_vw_Processo_Completo_id_processo
ON make.dbo.vw_Processo_Completo(id_processo_importacao);
```

**Benefícios:**
- ✅ Query única e simples: `SELECT * FROM vw_Processo_Completo WHERE numero_processo = ?`
- ✅ Performance otimizada (índice clusterizado)
- ✅ Código Python simplificado (não precisa fazer múltiplos JOINs)

**Uso no código:**
```python
# ANTES (complexo):
query = """
    SELECT ... FROM PROCESSO_IMPORTACAO pi
    LEFT JOIN ... (múltiplos JOINs)
    WHERE pi.numero_processo = ?
"""

# DEPOIS (simples):
query = """
    SELECT * FROM vw_Processo_Completo
    WHERE numero_processo = ?
"""
```

---

#### 3.2. View `vw_DI_Completa`
**Problema:** Query de DI completa tem múltiplos JOINs

**Solução:**
```sql
CREATE VIEW Serpro.dbo.vw_DI_Completa
WITH SCHEMABINDING
AS
SELECT 
    ddg.numeroDi,
    ddg.situacaoDi,
    diDesp.canalSelecaoParametrizada,
    diDesp.dataHoraDesembaraco,
    diDesp.dataHoraRegistro,
    diDesp.modalidadeDespacho,
    DVMD.totalDolares AS vlmd_dolar,
    DVMD.totalReais AS vlmd_real,
    DVME.totalDolares AS vlme_dolar,
    DVME.totalReais AS vlme_real,
    DI.nomeImportador,
    DA.nomeAdquirente,
    DICM.tipoRecolhimento AS icms_tipo_recolhimento,
    DICM.dataPagamento AS icms_data_pagamento,
    diH.idImportacao,
    diRoot.dadosDiId
FROM Serpro.dbo.Di_Dados_Gerais ddg
INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON ddg.dadosGeraisId = diRoot.dadosGeraisId
INNER JOIN Serpro.dbo.Di_Dados_Despacho diDesp ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
INNER JOIN Serpro.dbo.Hi_Historico_Di diH ON diH.diId = diRoot.dadosDiId
LEFT JOIN Serpro.dbo.Di_Icms DICM ON diRoot.dadosDiId = DICM.rootDiId
LEFT JOIN Serpro.dbo.Di_Adquirente DA ON diRoot.dadosDiId = DA.adquirenteId
LEFT JOIN Serpro.dbo.Di_Importador DI ON diRoot.importadorId = DI.importadorId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId;

CREATE UNIQUE CLUSTERED INDEX IX_vw_DI_Completa_numeroDi
ON Serpro.dbo.vw_DI_Completa(numeroDi);
```

---

### **PRIORIDADE 4: Campos Denormalizados para Performance**

#### 4.1. Tabela `PROCESSO_IMPORTACAO` - Campos Calculados
**Problema:** Valores calculados (ex: total de impostos) precisam ser calculados em runtime

**Solução:**
```sql
-- Adicionar campos denormalizados para evitar JOINs frequentes
ALTER TABLE make.dbo.PROCESSO_IMPORTACAO
ADD 
    -- Status consolidado (atualizado via trigger)
    status_consolidado VARCHAR(50) NULL,  -- 'ATIVO', 'DESEMBARACADO', 'ENTREGUE', etc.
    
    -- Flags de documentos (atualizado via trigger)
    tem_di BIT DEFAULT 0,
    tem_duimp BIT DEFAULT 0,
    tem_ce BIT DEFAULT 0,
    
    -- Datas importantes (atualizado via trigger)
    data_desembaraco_di DATETIME NULL,
    data_registro_duimp DATETIME NULL,
    data_chegada_ce DATETIME NULL,
    
    -- Valores consolidados (atualizado via trigger)
    valor_total_impostos DECIMAL(18,2) NULL,
    valor_total_mercadoria_brl DECIMAL(18,2) NULL,
    
    -- Última atualização
    data_ultima_atualizacao DATETIME DEFAULT GETDATE();

-- Índices para busca rápida
CREATE NONCLUSTERED INDEX IX_PROCESSO_IMPORTACAO_status_consolidado
ON make.dbo.PROCESSO_IMPORTACAO(status_consolidado)
WHERE status_consolidado IS NOT NULL;

CREATE NONCLUSTERED INDEX IX_PROCESSO_IMPORTACAO_tem_di
ON make.dbo.PROCESSO_IMPORTACAO(tem_di)
WHERE tem_di = 1;
```

**Benefícios:**
- ✅ Queries de listagem muito mais rápidas (ex: "processos com DI")
- ✅ Não precisa fazer JOINs para saber se tem documento
- ✅ Dashboards e relatórios mais rápidos

---

## 🚀 Melhorias de Performance

### 5.1. Particionamento de Tabelas Grandes
**Problema:** Tabelas como `Hi_Historico_Di` podem crescer muito

**Solução:**
```sql
-- Particionar Hi_Historico_Di por ano (exemplo)
-- (Implementação depende do volume de dados)
```

**Benefícios:**
- ✅ Queries mais rápidas em dados recentes
- ✅ Manutenção mais fácil (arquivar dados antigos)

---

### 5.2. Cache de Queries Frequentes
**Problema:** Mesmas queries executadas repetidamente

**Solução:**
```sql
-- Usar planos de execução em cache
-- Habilitar statistics para otimização automática
ALTER DATABASE Make SET AUTO_UPDATE_STATISTICS ON;
ALTER DATABASE Make SET AUTO_CREATE_STATISTICS ON;
```

---

### 5.3. Otimização de Queries com Hints
**Problema:** SQL Server pode escolher planos subótimos

**Solução:**
```sql
-- Adicionar hints em queries críticas (se necessário)
-- Exemplo: FORCE ORDER em JOINs complexos
```

---

## 🏗️ Melhorias de Estrutura

### 6.1. Tabela de Vínculo Centralizada
**Problema:** Relacionamentos espalhados entre múltiplas tabelas

**Solução:**
```sql
-- Criar tabela centralizada de vínculos
CREATE TABLE make.dbo.PROCESSO_DOCUMENTOS (
    id_processo_importacao INT NOT NULL,
    id_importacao INT NULL,
    
    -- Documentos relacionados (denormalizado para performance)
    numero_di VARCHAR(20) NULL,
    numero_di_normalizado VARCHAR(20) NULL,
    id_di INT NULL,  -- FK para Di_Root_Declaracao_Importacao.dadosDiId
    
    numero_ce VARCHAR(20) NULL,
    numero_ce_normalizado VARCHAR(20) NULL,
    id_ce INT NULL,  -- FK para Ce_Root_Conhecimento_Embarque.rootConsultaEmbarqueId
    
    numero_duimp VARCHAR(20) NULL,
    id_duimp INT NULL,  -- FK para duimp.duimp_id
    
    -- Flags de sincronização
    di_atualizado BIT DEFAULT 0,
    ce_atualizado BIT DEFAULT 0,
    duimp_atualizado BIT DEFAULT 0,
    
    -- Timestamps
    data_criacao DATETIME DEFAULT GETDATE(),
    data_atualizacao DATETIME DEFAULT GETDATE(),
    
    PRIMARY KEY (id_processo_importacao),
    FOREIGN KEY (id_processo_importacao) REFERENCES make.dbo.PROCESSO_IMPORTACAO(id_processo_importacao)
);

-- Índices
CREATE NONCLUSTERED INDEX IX_PROCESSO_DOCUMENTOS_numero_di_normalizado
ON make.dbo.PROCESSO_DOCUMENTOS(numero_di_normalizado)
WHERE numero_di_normalizado IS NOT NULL;

CREATE NONCLUSTERED INDEX IX_PROCESSO_DOCUMENTOS_id_importacao
ON make.dbo.PROCESSO_DOCUMENTOS(id_importacao)
WHERE id_importacao IS NOT NULL;
```

**Benefícios:**
- ✅ Um único lugar para buscar todos os documentos relacionados
- ✅ Performance melhorada (menos JOINs)
- ✅ Facilita manutenção e sincronização

---

### 6.2. Tabela de Histórico de Situações
**Problema:** Histórico de situações espalhado em múltiplas tabelas

**Solução:**
```sql
-- Tabela unificada de histórico de situações
CREATE TABLE make.dbo.PROCESSO_HISTORICO_SITUACOES (
    id_historico BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_processo_importacao INT NOT NULL,
    tipo_documento VARCHAR(10) NOT NULL,  -- 'DI', 'DUIMP', 'CE', 'CCT'
    numero_documento VARCHAR(50) NULL,
    situacao_anterior VARCHAR(100) NULL,
    situacao_nova VARCHAR(100) NOT NULL,
    data_mudanca DATETIME NOT NULL DEFAULT GETDATE(),
    origem VARCHAR(50) NULL,  -- 'API', 'KANBAN', 'MANUAL'
    
    FOREIGN KEY (id_processo_importacao) REFERENCES make.dbo.PROCESSO_IMPORTACAO(id_processo_importacao)
);

CREATE NONCLUSTERED INDEX IX_PROCESSO_HISTORICO_id_processo_data
ON make.dbo.PROCESSO_HISTORICO_SITUACOES(id_processo_importacao, data_mudanca DESC);
```

**Benefícios:**
- ✅ Histórico completo e auditável
- ✅ Facilita queries de "última mudança"
- ✅ Permite análises temporais

---

## 🔒 Melhorias de Consistência

### 7.1. Triggers para Sincronização Automática
**Problema:** Dados podem ficar desatualizados entre tabelas

**Solução:**
```sql
-- Trigger para atualizar campos denormalizados quando DI é atualizada
CREATE TRIGGER trg_Di_Dados_Gerais_Update_Processo
ON Serpro.dbo.Di_Dados_Gerais
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    
    -- Atualizar PROCESSO_DOCUMENTOS quando DI muda
    UPDATE pd
    SET 
        numero_di = i.numeroDi,
        numero_di_normalizado = REPLACE(REPLACE(i.numeroDi, '/', ''), '-', ''),
        di_atualizado = 1,
        data_atualizacao = GETDATE()
    FROM make.dbo.PROCESSO_DOCUMENTOS pd
    INNER JOIN inserted i ON pd.numero_di_normalizado = REPLACE(REPLACE(i.numeroDi, '/', ''), '-', '')
    WHERE pd.numero_di IS NULL OR pd.numero_di != i.numeroDi;
    
    -- Atualizar status_consolidado em PROCESSO_IMPORTACAO
    UPDATE pi
    SET 
        status_consolidado = CASE 
            WHEN i.situacaoDi LIKE '%DESEMBARACAD%' THEN 'DESEMBARACADO'
            WHEN i.situacaoDi LIKE '%REGISTRAD%' THEN 'REGISTRADO'
            ELSE 'ATIVO'
        END,
        data_desembaraco_di = diDesp.dataHoraDesembaraco,
        data_ultima_atualizacao = GETDATE()
    FROM make.dbo.PROCESSO_IMPORTACAO pi
    INNER JOIN make.dbo.PROCESSO_DOCUMENTOS pd ON pd.id_processo_importacao = pi.id_processo_importacao
    INNER JOIN inserted i ON pd.numero_di_normalizado = REPLACE(REPLACE(i.numeroDi, '/', ''), '-', '')
    INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON diRoot.dadosGeraisId = i.dadosGeraisId
    INNER JOIN Serpro.dbo.Di_Dados_Despacho diDesp ON diRoot.dadosDespachoId = diDesp.dadosDespachoId;
END;
```

**Benefícios:**
- ✅ Sincronização automática de dados
- ✅ Consistência garantida
- ✅ Reduz necessidade de sincronização manual

---

### 7.2. Constraints de Integridade Referencial
**Problema:** Falta de FKs pode causar dados órfãos

**Solução:**
```sql
-- Adicionar FKs onde faltam (se aplicável)
-- CUIDADO: Verificar dados existentes antes de adicionar
```

---

### 7.3. Campos de Auditoria
**Problema:** Difícil rastrear mudanças

**Solução:**
```sql
-- Adicionar campos de auditoria em tabelas críticas
ALTER TABLE make.dbo.PROCESSO_IMPORTACAO
ADD 
    criado_por VARCHAR(100) NULL,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_por VARCHAR(100) NULL,
    atualizado_em DATETIME DEFAULT GETDATE();
```

---

## 📊 Melhorias Adicionais

### 8.1. Tabela de Cache de Totais
**Problema:** Cálculos agregados (ex: total de impostos) são lentos

**Solução:**
```sql
-- Tabela de cache para totais calculados
CREATE TABLE make.dbo.PROCESSO_TOTAIS_CACHE (
    id_processo_importacao INT PRIMARY KEY,
    total_impostos_di DECIMAL(18,2) NULL,
    total_impostos_duimp DECIMAL(18,2) NULL,
    total_frete DECIMAL(18,2) NULL,
    total_seguro DECIMAL(18,2) NULL,
    data_calculo DATETIME DEFAULT GETDATE(),
    
    FOREIGN KEY (id_processo_importacao) REFERENCES make.dbo.PROCESSO_IMPORTACAO(id_processo_importacao)
);
```

**Atualização via trigger ou job agendado**

---

### 8.2. Índices Filtrados para Dados Ativos
**Problema:** Queries frequentemente filtram apenas processos ativos

**Solução:**
```sql
-- Índices filtrados para processos ativos
CREATE NONCLUSTERED INDEX IX_PROCESSO_IMPORTACAO_ativo_numero_processo
ON make.dbo.PROCESSO_IMPORTACAO(numero_processo)
WHERE status_consolidado = 'ATIVO' OR status_consolidado IS NULL;
```

---

## 🗺️ Roadmap de Implementação

### **Fase 1: Crítico (1-2 semanas)**
1. ✅ Adicionar campos `numero_di_normalizado` e `numero_ce_normalizado`
2. ✅ Criar índices prioritários (id_importacao, numeroDi, numero)
3. ✅ Criar view `vw_Processo_Completo`

**Impacto esperado:** Redução de 50-70% no tempo de queries de processo

---

### **Fase 2: Importante (2-4 semanas)**
1. ✅ Criar tabela `PROCESSO_DOCUMENTOS`
2. ✅ Migrar dados existentes
3. ✅ Criar triggers de sincronização
4. ✅ Adicionar campos denormalizados em `PROCESSO_IMPORTACAO`

**Impacto esperado:** Queries de listagem 3-5x mais rápidas

---

### **Fase 3: Otimização (1-2 meses)**
1. ✅ Criar views materializadas adicionais
2. ✅ Implementar cache de totais
3. ✅ Adicionar campos de auditoria
4. ✅ Otimizar queries existentes

**Impacto esperado:** Sistema 2-3x mais rápido no geral

---

## ⚠️ Considerações Importantes

### **Antes de Implementar:**
1. **Backup completo** do banco de dados
2. **Testar em ambiente de desenvolvimento** primeiro
3. **Verificar impacto em outras aplicações** que usam o mesmo banco
4. **Monitorar performance** após cada mudança
5. **Documentar mudanças** para a equipe

### **Riscos:**
- **Downtime:** Algumas mudanças podem requerer locks (ex: adicionar colunas)
- **Compatibilidade:** Outras aplicações podem depender da estrutura atual
- **Volume de dados:** Migrações podem ser lentas em tabelas grandes

### **Mitigações:**
- Implementar em horários de baixo uso
- Fazer mudanças incrementais
- Manter rollback plan pronto
- Comunicar mudanças para equipe

---

## 📝 Resumo Executivo

### **Problemas Principais:**
1. Formato inconsistente de `numero_di` (requer normalização)
2. Relacionamentos indiretos complexos (múltiplos JOINs)
3. Falta de índices em campos de busca frequente
4. Dados duplicados entre tabelas

### **Soluções Prioritárias:**
1. **Campos normalizados** (`numero_di_normalizado`) - Resolve problema #1
2. **Índices estratégicos** - Resolve problema #3
3. **Views materializadas** - Resolve problema #2
4. **Tabela de vínculo centralizada** - Resolve problema #4

### **Impacto Esperado:**
- **Performance:** 50-70% mais rápido em queries de processo
- **Código:** 30-40% menos código Python (queries mais simples)
- **Manutenção:** Muito mais fácil (estrutura mais clara)
- **Confiabilidade:** Menos erros (dados mais consistentes)

---

**Última atualização:** 21/12/2025

