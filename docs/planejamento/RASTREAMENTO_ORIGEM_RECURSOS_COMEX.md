# 🔍 Rastreamento de Origem dos Recursos - Comércio Exterior Brasil

**Data:** 08/01/2026  
**Versão:** 1.0  
**Status:** 📋 Documentação de Compliance e Segurança

---

## 🎯 Objetivo Principal

**Foco da aplicação:** Responder com segurança e precisão a **qualquer intimação da Receita Federal** sobre a origem dos recursos aplicados em operações de comércio exterior.

**Contexto crítico:**
- **Interposição fraudulenta** é crime fiscal grave
- Receita Federal pode intimar sobre origem de recursos em qualquer momento
- Documentação completa e rastreável é obrigatória
- Sistema deve permitir rastreamento completo desde a origem até a aplicação

---

## ⚖️ Contexto Legal e Regulatório

### 1. Interposição Fraudulenta

**Definição:** Uso de pessoa física ou jurídica interposta para ocultar a verdadeira origem dos recursos ou beneficiário real da operação.

**Riscos:**
- Crime fiscal (Lei 8.137/90)
- Penalidades administrativas e criminais
- Bloqueio de operações
- Responsabilização dos envolvidos

**Como prevenir:**
- Rastreamento completo da origem dos recursos
- Identificação clara de todas as partes envolvidas
- Documentação de toda a cadeia de pagamentos
- Validação de contrapartidas (CPF/CNPJ)

### 2. Requisitos da Receita Federal

**Documentação obrigatória:**
- Comprovante de origem dos recursos
- Identificação completa do pagador (CPF/CNPJ, nome, endereço)
- Identificação completa do recebedor
- Finalidade da transação
- Vínculo com operação de comércio exterior
- Histórico completo da movimentação

**Em caso de intimação:**
- Resposta deve ser completa e precisa
- Documentação deve estar organizada e acessível
- Rastreamento deve ser claro e verificável
- Não pode haver lacunas na cadeia de recursos

### 3. COAF (Conselho de Controle de Atividades Financeiras)

**Relatórios de Inteligência Financeira (RIF):**
- Devem ser gerados quando houver operações suspeitas
- Sistema deve facilitar geração de RIFs
- Dados devem estar prontos para análise

**Operações suspeitas em comércio exterior:**
- Valores incompatíveis com atividade
- Múltiplas operações fragmentadas
- Contrapartidas não identificadas
- Operações com países de alto risco

---

## 📊 Estrutura de Rastreamento Necessária

### 1. Origem dos Recursos

**Campos obrigatórios para cada recurso:**

```sql
-- Tabela RASTREAMENTO_RECURSO (já planejada)
origem_recurso VARCHAR(50) NOT NULL,              -- Ex: "CLIENTE", "FORNECEDOR", "BANCO", "PROPRIO"
origem_recurso_descricao VARCHAR(255),            -- Descrição detalhada
tipo_recurso VARCHAR(50),                          -- Ex: "PAGAMENTO_FOB", "PAGAMENTO_FRETE", "FINANCIAMENTO"

-- Identificação completa da origem
cpf_cnpj_origem VARCHAR(18),                       -- CPF/CNPJ de quem forneceu o recurso
nome_origem VARCHAR(255),                          -- Nome completo
endereco_origem TEXT,                              -- Endereço completo
banco_origem VARCHAR(50),                         -- Banco de origem
agencia_origem VARCHAR(20),
conta_origem VARCHAR(50),

-- Documentação
documento_comprovante VARCHAR(255),                -- Número do documento comprovante
data_origem DATETIME,                             -- Data de origem do recurso
valor_origem_usd DECIMAL(18,2),
valor_origem_brl DECIMAL(18,2),
moeda VARCHAR(3),
taxa_cambio DECIMAL(10,6),

-- Vínculo com movimentação bancária
id_movimentacao_bancaria BIGINT,                  -- FK para MOVIMENTACAO_BANCARIA
```

### 2. Aplicação dos Recursos

**Cada recurso deve ser rastreado até sua aplicação:**

```sql
-- Tabela RASTREAMENTO_RECURSO (continuação)
processo_referencia VARCHAR(50),                   -- Processo onde foi aplicado
categoria_processo VARCHAR(10),                    -- Categoria do processo
tipo_aplicacao VARCHAR(50),                       -- Ex: "PAGAMENTO_FRETE", "PAGAMENTO_IMPOSTO"
data_aplicacao DATETIME,                          -- Data de aplicação
valor_aplicado_usd DECIMAL(18,2),
valor_aplicado_brl DECIMAL(18,2),

-- Vínculo com despesa
id_despesa_processo BIGINT,                       -- FK para DESPESA_PROCESSO
```

### 3. Cadeia Completa de Rastreamento

**Exemplo de rastreamento completo:**

```
ORIGEM DO RECURSO:
├── Cliente: Empresa XYZ Ltda (CNPJ: 12.345.678/0001-90)
├── Banco: Banco do Brasil
├── Conta: 1251-50483
├── Valor: R$ 100.000,00
├── Data: 15/01/2026
├── Documento: TED 123456789
└── Finalidade: Pagamento FOB processo ALH.0001/25

APLICAÇÃO DO RECURSO:
├── Processo: ALH.0001/25
├── Categoria: ALH
├── Tipo: PAGAMENTO_FOB
├── Valor: R$ 100.000,00
├── Data: 15/01/2026
└── Despesa: id_despesa = 123

MOVIMENTAÇÃO BANCÁRIA:
├── Banco: Banco do Brasil
├── Conta: 1251-50483
├── Data: 15/01/2026
├── Valor: R$ 100.000,00
├── Tipo: CRÉDITO
└── Contrapartida: Empresa XYZ Ltda (CNPJ: 12.345.678/0001-90)
```

---

## 🔐 Campos Críticos para Compliance

### 1. Identificação Completa de Contrapartidas

**Tabela MOVIMENTACAO_BANCARIA deve ter:**

```sql
-- Contrapartida (já planejado)
cpf_cnpj_contrapartida VARCHAR(18),               -- OBRIGATÓRIO
nome_contrapartida VARCHAR(255),                  -- OBRIGATÓRIO
tipo_pessoa_contrapartida VARCHAR(20),            -- OBRIGATÓRIO
banco_contrapartida VARCHAR(50),
agencia_contrapartida VARCHAR(20),
conta_contrapartida VARCHAR(50),
dv_conta_contrapartida VARCHAR(5),

-- Validação
contrapartida_validada BIT DEFAULT 0,             -- Se foi validada (ReceitaWS, etc.)
data_validacao_contrapartida DATETIME,
fonte_validacao VARCHAR(50),                      -- Ex: "RECEITAWS", "SERPRO"
```

### 2. Documentação de Comprovantes

**Tabela adicional para comprovantes:**

```sql
CREATE TABLE [dbo].[COMPROVANTE_RECURSO] (
    id_comprovante BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Vínculo
    id_rastreamento_recurso BIGINT,               -- FK para RASTREAMENTO_RECURSO
    id_movimentacao_bancaria BIGINT,              -- FK para MOVIMENTACAO_BANCARIA
    
    -- Documento
    tipo_comprovante VARCHAR(50),                 -- Ex: "TED", "DOC", "PIX", "BOLETO", "NOTA_FISCAL"
    numero_comprovante VARCHAR(100),              -- Número do documento
    data_comprovante DATETIME,
    valor_comprovante DECIMAL(18,2),
    
    -- Arquivo
    caminho_arquivo VARCHAR(500),                 -- Caminho do arquivo PDF/imagem
    hash_arquivo VARCHAR(64),                     -- Hash para integridade
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE()
);
```

### 3. Histórico de Validações

**Tabela para registrar validações:**

```sql
CREATE TABLE [dbo].[VALIDACAO_ORIGEM_RECURSO] (
    id_validacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Vínculo
    id_rastreamento_recurso BIGINT,               -- FK para RASTREAMENTO_RECURSO
    id_movimentacao_bancaria BIGINT,              -- FK para MOVIMENTACAO_BANCARIA
    
    -- Validação
    tipo_validacao VARCHAR(50),                   -- Ex: "CPF_CNPJ", "CONTRAPARTIDA", "ORIGEM", "DOCUMENTACAO"
    status_validacao VARCHAR(20),                 -- 'pendente', 'validado', 'divergencia', 'erro'
    resultado_validacao TEXT,
    fonte_validacao VARCHAR(50),                  -- Ex: "RECEITAWS", "SERPRO", "MANUAL"
    
    -- Detalhes
    dados_validados NVARCHAR(MAX),                -- JSON com dados validados
    observacoes TEXT,
    
    -- Metadados
    validado_por VARCHAR(100),
    data_validacao DATETIME DEFAULT GETDATE()
);
```

---

## 📋 Checklist de Compliance

### Para cada recurso aplicado em comércio exterior:

- [ ] **Origem identificada:**
  - [ ] CPF/CNPJ do pagador
  - [ ] Nome completo do pagador
  - [ ] Endereço do pagador
  - [ ] Banco e conta de origem
  - [ ] Documento comprovante (TED, DOC, PIX, etc.)

- [ ] **Aplicação rastreada:**
  - [ ] Processo vinculado
  - [ ] Categoria do processo
  - [ ] Tipo de despesa
  - [ ] Valor aplicado
  - [ ] Data de aplicação

- [ ] **Movimentação bancária:**
  - [ ] Contrapartida identificada
  - [ ] Contrapartida validada
  - [ ] Descrição clara
  - [ ] Histórico completo

- [ ] **Documentação:**
  - [ ] Comprovante arquivado
  - [ ] Hash do arquivo
  - [ ] Validações registradas
  - [ ] Histórico de alterações

---

## 🚨 Red Flags (Sinais de Alerta)

**Sistema deve alertar sobre:**

1. **Contrapartida não identificada:**
   - CPF/CNPJ ausente ou inválido
   - Nome não encontrado em bases oficiais

2. **Valores incompatíveis:**
   - Valor muito alto para atividade
   - Múltiplas operações fragmentadas (possível evasão)

3. **Origem suspeita:**
   - Recursos de origem não identificada
   - Múltiplas origens para mesmo processo

4. **Lacunas no rastreamento:**
   - Recurso sem origem identificada
   - Aplicação sem vínculo com processo
   - Movimentação sem contrapartida

5. **Documentação incompleta:**
   - Comprovante ausente
   - Validação pendente há muito tempo

---

## 📊 Relatórios para Intimações

### 1. Relatório de Origem de Recursos por Processo

**Query exemplo:**
```sql
SELECT 
    p.processo_referencia,
    p.categoria_processo,
    rr.origem_recurso,
    rr.cpf_cnpj_origem,
    rr.nome_origem,
    rr.valor_origem_brl,
    rr.data_origem,
    rr.tipo_recurso,
    m.banco_origem,
    m.conta_origem,
    m.numero_comprovante,
    m.data_movimentacao
FROM PROCESSO_IMPORTACAO p
INNER JOIN RASTREAMENTO_RECURSO rr ON p.processo_referencia = rr.processo_referencia
LEFT JOIN MOVIMENTACAO_BANCARIA m ON rr.id_movimentacao_bancaria = m.id_movimentacao
WHERE p.processo_referencia = 'ALH.0001/25'
ORDER BY rr.data_origem;
```

### 2. Relatório de Aplicação de Recursos

**Query exemplo:**
```sql
SELECT 
    rr.origem_recurso,
    rr.cpf_cnpj_origem,
    rr.nome_origem,
    rr.valor_origem_brl,
    p.processo_referencia,
    dp.tipo_despesa,
    dp.valor_realizado_brl,
    dp.data_real_pagamento,
    m.descricao_movimentacao,
    m.data_movimentacao
FROM RASTREAMENTO_RECURSO rr
INNER JOIN PROCESSO_IMPORTACAO p ON rr.processo_referencia = p.processo_referencia
LEFT JOIN DESPESA_PROCESSO dp ON rr.id_despesa_processo = dp.id_despesa
LEFT JOIN MOVIMENTACAO_BANCARIA m ON rr.id_movimentacao_bancaria = m.id_movimentacao
WHERE rr.origem_recurso = 'CLIENTE'
ORDER BY rr.data_origem;
```

### 3. Relatório de Cadeia Completa

**Query exemplo:**
```sql
-- Cadeia completa: Origem → Movimentação → Aplicação
SELECT 
    -- Origem
    rr.origem_recurso,
    rr.cpf_cnpj_origem,
    rr.nome_origem,
    rr.valor_origem_brl AS valor_origem,
    rr.data_origem,
    
    -- Movimentação
    m.banco_origem,
    m.conta_origem,
    m.cpf_cnpj_contrapartida,
    m.nome_contrapartida,
    m.valor_movimentacao,
    m.data_movimentacao,
    m.descricao_movimentacao,
    
    -- Aplicação
    p.processo_referencia,
    p.categoria_processo,
    dp.tipo_despesa,
    dp.valor_realizado_brl AS valor_aplicado,
    dp.data_real_pagamento
    
FROM RASTREAMENTO_RECURSO rr
LEFT JOIN MOVIMENTACAO_BANCARIA m ON rr.id_movimentacao_bancaria = m.id_movimentacao
LEFT JOIN PROCESSO_IMPORTACAO p ON rr.processo_referencia = p.processo_referencia
LEFT JOIN DESPESA_PROCESSO dp ON rr.id_despesa_processo = dp.id_despesa
WHERE p.processo_referencia = 'ALH.0001/25'
ORDER BY rr.data_origem, m.data_movimentacao;
```

---

## 🔄 Fluxo de Validação Recomendado

### 1. Ao receber recurso:

1. **Identificar origem:**
   - Extrair CPF/CNPJ da movimentação bancária
   - Validar CPF/CNPJ em ReceitaWS/Serpro
   - Buscar nome e endereço
   - Registrar em `RASTREAMENTO_RECURSO`

2. **Validar contrapartida:**
   - Verificar se CPF/CNPJ existe
   - Verificar se nome corresponde
   - Registrar validação em `VALIDACAO_ORIGEM_RECURSO`

3. **Arquivar comprovante:**
   - Salvar PDF/imagem do comprovante
   - Calcular hash do arquivo
   - Registrar em `COMPROVANTE_RECURSO`

### 2. Ao aplicar recurso:

1. **Vincular a processo:**
   - Identificar processo de destino
   - Identificar tipo de despesa
   - Registrar em `RASTREAMENTO_RECURSO`

2. **Conciliação:**
   - Conciliação automática com despesa
   - Validação de valores
   - Registro em `CONCILIACAO_BANCARIA`

### 3. Validações periódicas:

1. **Verificar lacunas:**
   - Recursos sem origem identificada
   - Movimentações sem contrapartida
   - Aplicações sem processo vinculado

2. **Alertas:**
   - Contrapartidas não validadas
   - Documentação incompleta
   - Valores incompatíveis

---

## 📝 Recomendações de Implementação

### 1. Campos Adicionais Necessários

**Tabela RASTREAMENTO_RECURSO:**
- ✅ `cpf_cnpj_origem` - CPF/CNPJ de quem forneceu o recurso
- ✅ `nome_origem` - Nome completo
- ✅ `endereco_origem` - Endereço completo
- ✅ `banco_origem` - Banco de origem
- ✅ `agencia_origem` - Agência de origem
- ✅ `conta_origem` - Conta de origem
- ✅ `documento_comprovante` - Número do documento comprovante

**Tabela MOVIMENTACAO_BANCARIA:**
- ✅ `contrapartida_validada` - Se foi validada
- ✅ `data_validacao_contrapartida` - Data da validação
- ✅ `fonte_validacao` - Fonte da validação (ReceitaWS, etc.)

### 2. Tabelas Adicionais

- ✅ `COMPROVANTE_RECURSO` - Para arquivar comprovantes
- ✅ `VALIDACAO_ORIGEM_RECURSO` - Para registrar validações

### 3. Funcionalidades Necessárias

- ✅ Validação automática de CPF/CNPJ (ReceitaWS)
- ✅ Busca automática de nome e endereço
- ✅ Arquivamento de comprovantes (PDF/imagem)
- ✅ Cálculo de hash para integridade
- ✅ Relatórios para intimações
- ✅ Alertas de red flags
- ✅ Validações periódicas automáticas

---

## 🎯 Próximos Passos

1. **Atualizar planejamento do banco de dados:**
   - Adicionar campos de origem em `RASTREAMENTO_RECURSO`
   - Adicionar campos de validação em `MOVIMENTACAO_BANCARIA`
   - Criar tabelas `COMPROVANTE_RECURSO` e `VALIDACAO_ORIGEM_RECURSO`

2. **Implementar validações:**
   - Integração com ReceitaWS para validação de CPF/CNPJ
   - Validação automática de contrapartidas
   - Alertas de red flags

3. **Implementar relatórios:**
   - Relatório de origem de recursos por processo
   - Relatório de aplicação de recursos
   - Relatório de cadeia completa

4. **Documentação:**
   - Manual de uso do sistema de rastreamento
   - Guia de resposta a intimações
   - Checklist de compliance

---

**Última atualização:** 08/01/2026  
**Versão:** 1.0

