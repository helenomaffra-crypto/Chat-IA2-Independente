# 📋 Catálogo de Despesas Padrão

## Visão Geral

Sistema de classificação de despesas padrão para processos de importação, permitindo vincular lançamentos bancários a tipos específicos de despesas e múltiplos processos.

---

## 🎯 Objetivos

1. **Classificação Padronizada**: 23 tipos de despesas padrão pré-cadastradas
2. **Flexibilidade**: Um lançamento bancário pode ter múltiplas despesas de múltiplos processos
3. **Preparação para Contabilidade**: Estrutura pronta para integração com plano de contas
4. **Rastreabilidade**: Classificação manual ou automática com níveis de confiança

---

## 📊 Estrutura de Tabelas

### 1. `TIPO_DESPESA` (Catálogo)

**Campos principais:**
- `id_tipo_despesa` (PK)
- `codigo_tipo_despesa` (único, ex: 'FRETE_INTERNACIONAL')
- `nome_despesa` (ex: 'Frete Internacional')
- `categoria_despesa` (FRETE, IMPOSTO, TAXA, SERVICO, etc.)
- `tipo_custo` (INTERNACIONAL, NACIONAL, BUROCRATICO)
- `plano_contas_codigo` (preparado para futuro)
- `ordem_exibicao` (ordem na UI)

**Despesas Padrão Cadastradas (23):**

1. **Frete Internacional** - `FRETE_INTERNACIONAL`
2. **Seguro** - `SEGURO`
3. **AFRMM** - `AFRMM`
4. **Multas** - `MULTAS`
5. **Tx Siscomex (D.I.)** - `TAXA_SISCOMEX_DI`
6. **Tx Siscomex (D.A.)** - `TAXA_SISCOMEX_DA`
7. **Outros Custos Internac.** - `OUTROS_CUSTOS_INTERNAC`
8. **Liberação B/L** - `LIBERACAO_BL`
9. **Inspeção de Mercadoria** - `INSPECAO_MERCADORIA`
10. **Armazenagem DTA** - `ARMAZENAGEM_DTA`
11. **Frete DTA** - `FRETE_DTA`
12. **Armazenagem** - `ARMAZENAGEM`
13. **GRU / Tx LI** - `GRU_TAXA_LI`
14. **Despachante** - `DESPACHANTE`
15. **SDA** - `SDA`
16. **Carreto** - `CARRETO`
17. **Escolta** - `ESCOLTA`
18. **Lavagem CTNR** - `LAVAGEM_CTNR`
19. **Demurrage** - `DEMURRAGE`
20. **Antidumping** - `ANTIDUMPING`
21. **Contrato de Câmbio** - `CONTRATO_CAMBIO`
22. **Tarifas Bancárias** - `TARIFAS_BANCARIAS`
23. **Outros** - `OUTROS`

---

### 2. `LANCAMENTO_TIPO_DESPESA` (N:N)

**Relação many-to-many entre:**
- `MOVIMENTACAO_BANCARIA` ↔ `TIPO_DESPESA` ↔ `PROCESSO`

**Campos principais:**
- `id_lancamento_tipo_despesa` (PK)
- `id_movimentacao_bancaria` (FK → MOVIMENTACAO_BANCARIA)
- `id_tipo_despesa` (FK → TIPO_DESPESA)
- `processo_referencia` (ex: 'DMD.0083/25')
- `valor_despesa` (valor específico desta despesa neste lançamento)
- `percentual_valor` (percentual do valor total do lançamento)
- `origem_classificacao` (MANUAL, AUTOMATICA, IA, REGRA)
- `nivel_confianca` (0.00 a 1.00, para classificação automática)
- `classificacao_validada` (bit)
- `data_validacao` (quando foi validado)

**Uso:**
- Permite que um lançamento seja dividido em múltiplas despesas
- Permite que cada despesa esteja vinculada a um processo diferente
- Suporta classificação automática com nível de confiança

---

### 3. `MOVIMENTACAO_BANCARIA_PROCESSO` (Atualizada)

**Campos adicionados:**
- `id_tipo_despesa` (FK → TIPO_DESPESA) - opcional
- `valor_despesa` (valor específico desta despesa)

**Uso:**
- Manter compatibilidade com estrutura existente
- Permitir vinculação direta de processo + tipo de despesa em um único registro

---

### 4. `PLANO_CONTAS` (Preparado para futuro)

**Campos principais:**
- `id_plano_contas` (PK)
- `codigo_contabil` (ex: '3.1.01.001')
- `descricao_contabil` (ex: 'Despesas com Frete Internacional')
- `tipo_conta` (ATIVO, PASSIVO, RECEITA, DESPESA)
- `id_tipo_despesa` (FK → TIPO_DESPESA)

**Uso futuro:**
- Integração com sistema contábil
- Geração de relatórios contábeis
- Classificação automática de lançamentos

---

## 🔄 Fluxo de Uso

### Cenário 1: Classificação Manual

1. Usuário visualiza lançamento bancário não classificado
2. Usuário seleciona tipo(s) de despesa(s)
3. Usuário vincula a processo(s)
4. Sistema cria registro(s) em `LANCAMENTO_TIPO_DESPESA`

### Cenário 2: Classificação Automática

1. Sistema analisa descrição do lançamento
2. Sistema detecta palavras-chave (ex: "AFRMM", "Frete", "Siscomex")
3. Sistema sugere tipo(s) de despesa(s) com nível de confiança
4. Usuário valida ou corrige
5. Sistema cria registro(s) com `origem_classificacao = 'AUTOMATICA'` ou `'IA'`

### Cenário 3: Lançamento com Múltiplas Despesas

**Exemplo:** Lançamento de R$ 10.000,00 contém:
- R$ 5.000,00 - Frete Internacional (DMD.0083/25)
- R$ 3.000,00 - AFRMM (DMD.0083/25)
- R$ 2.000,00 - Frete Internacional (ALH.0005/25)

**Registros criados:**
```
LANCAMENTO_TIPO_DESPESA:
1. id_movimentacao_bancaria: 123
   id_tipo_despesa: 1 (FRETE_INTERNACIONAL)
   processo_referencia: 'DMD.0083/25'
   valor_despesa: 5000.00
   percentual_valor: 50.00

2. id_movimentacao_bancaria: 123
   id_tipo_despesa: 3 (AFRMM)
   processo_referencia: 'DMD.0083/25'
   valor_despesa: 3000.00
   percentual_valor: 30.00

3. id_movimentacao_bancaria: 123
   id_tipo_despesa: 1 (FRETE_INTERNACIONAL)
   processo_referencia: 'ALH.0005/25'
   valor_despesa: 2000.00
   percentual_valor: 20.00
```

---

## 📈 Benefícios

### 1. **Rastreabilidade Completa**
- Saber exatamente qual despesa de qual processo está em cada lançamento
- Histórico de classificação (manual vs automática)

### 2. **Relatórios Detalhados**
- Despesas por tipo (ex: total de AFRMM pago em janeiro)
- Despesas por processo (ex: todas as despesas do DMD.0083/25)
- Despesas por categoria (ex: total de frete vs total de impostos)

### 3. **Preparação para Contabilidade**
- Estrutura pronta para vincular plano de contas
- Classificação automática baseada em regras contábeis

### 4. **Flexibilidade**
- Um lançamento pode ter múltiplas despesas
- Uma despesa pode estar em múltiplos processos
- Suporta divisão proporcional de valores

---

## 🚀 Próximos Passos

### Fase 1: Estrutura Base (✅ Completa)
- [x] Criar tabelas
- [x] Inserir despesas padrão
- [x] Documentar estrutura

### Fase 2: Interface de Classificação
- [ ] Tela para classificar lançamentos
- [ ] Seleção múltipla de tipos de despesa
- [ ] Distribuição de valores
- [ ] Vinculação a processos

### Fase 3: Classificação Automática
- [ ] Algoritmo de detecção de palavras-chave
- [ ] Integração com IA para classificação
- [ ] Sugestões com nível de confiança
- [ ] Validação em lote

### Fase 4: Integração com Plano de Contas
- [ ] Importar plano de contas
- [ ] Vincular tipos de despesa a códigos contábeis
- [ ] Geração de relatórios contábeis
- [ ] Exportação para sistemas contábeis

---

## 📝 Como Usar

### Criar Catálogo de Despesas

**Opção 1: Via SQL**
```bash
# Conectar ao SQL Server e executar:
sqlcmd -S servidor -d mAIke_assistente -i scripts/criar_catalogo_despesas.sql
```

**Opção 2: Via Python**
```bash
python3 scripts/criar_catalogo_despesas_via_python.py
```

### Consultar Despesas Padrão

```sql
SELECT 
    codigo_tipo_despesa,
    nome_despesa,
    categoria_despesa,
    tipo_custo,
    ordem_exibicao
FROM dbo.TIPO_DESPESA
WHERE ativo = 1
ORDER BY ordem_exibicao
```

### Consultar Lançamentos Classificados

```sql
SELECT 
    mb.id_movimentacao,
    mb.data_movimentacao,
    mb.valor_movimentacao,
    mb.descricao_movimentacao,
    td.nome_despesa,
    ltd.valor_despesa,
    ltd.processo_referencia,
    ltd.origem_classificacao,
    ltd.classificacao_validada
FROM dbo.MOVIMENTACAO_BANCARIA mb
LEFT JOIN dbo.LANCAMENTO_TIPO_DESPESA ltd 
    ON mb.id_movimentacao = ltd.id_movimentacao_bancaria
LEFT JOIN dbo.TIPO_DESPESA td 
    ON ltd.id_tipo_despesa = td.id_tipo_despesa
WHERE mb.banco_origem = 'BB'
ORDER BY mb.data_movimentacao DESC
```

---

## ⚠️ Observações Importantes

1. **Divisão de Valores**: Quando um lançamento é dividido em múltiplas despesas, a soma dos valores ou percentuais deve ser validada (≤ 100%)

2. **Validação**: Sempre validar classificação automática antes de considerar definitiva

3. **Performance**: Índices criados para otimizar consultas por processo, tipo de despesa e data

4. **Backup**: Antes de criar o catálogo, fazer backup do banco de dados

---

**Última atualização:** 07/01/2026

