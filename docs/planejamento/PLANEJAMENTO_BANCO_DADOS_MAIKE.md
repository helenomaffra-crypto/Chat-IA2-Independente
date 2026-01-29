# 🗄️ Planejamento Completo - Banco de Dados mAIke_assistente (SQL Server)

**Data:** 07/01/2026  
**Versão:** 1.4  
**Status:** 📋 Planejamento Completo

**Última atualização:** 08/01/2026

**Mudanças v1.1:**
- ✅ Adicionados campos de **plano de contas** e **histórico interno** na tabela `MOVIMENTACAO_BANCARIA`
- ✅ Clarificado que a tabela armazena **lançamentos individuais** (não PDFs de extratos)
- ✅ Objetivo: permitir vincular cada lançamento a processo, plano de contas e histórico interno

**Mudanças v1.2:**
- ✅ Adicionada tabela `MOVIMENTACAO_BANCARIA_PROCESSO` para relacionamento N:N
- ✅ Permite dividir um lançamento bancário entre vários processos
- ✅ Cada processo tem seu valor específico (parcela)
- ✅ Exemplo: Armazenagem R$ 10.000 dividida em ALH.0001 (R$ 3.000), BGR.0005 (R$ 2.000), DMD.0050 (R$ 5.000)

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Banco de Dados](#arquitetura-do-banco-de-dados)
3. [Tabelas Principais](#tabelas-principais)
4. [Tabelas de Integração](#tabelas-de-integração)
5. [Tabelas de Despesas e Financeiro](#tabelas-de-despesas-e-financeiro) ⭐ **NOVO**
6. [Tabelas de Validação e Verificação](#tabelas-de-validação-e-verificação) ⭐ **NOVO**
7. [Tabelas de Comunicação](#tabelas-de-comunicação)
8. [Tabelas de IA e Aprendizado](#tabelas-de-ia-e-aprendizado)
9. [Tabelas de Vetorização](#tabelas-de-vetorização)
10. [Tabelas de Auditoria e Logs](#tabelas-de-auditoria-e-logs)
11. [Índices e Performance](#índices-e-performance)
12. [Estratégia de Migração](#estratégia-de-migração)
13. [DTOs e Normalização](#dtos-e-normalização)
14. [Funcionalidades Especiais - mAIke Assistente COMEX](#funcionalidades-especiais---maike-assistente-comex) ⭐ **NOVO**

---

## 🎯 Visão Geral

Este documento define a estrutura completa do banco de dados **`mAIke_assistente`** no SQL Server, consolidando dados de **todas as fontes** identificadas na aplicação:

### 📊 Fontes de Dados Identificadas

1. **Processos de Importação**
   - API Kanban (processos ativos)
   - SQL Server Make (processos históricos)
   - ShipsGo (tracking ETA/porto)

2. **Documentos Aduaneiros**
   - Portal Único (DUIMP, CCT, CATP)
   - Integra Comex (CE, DI)
   - SQL Server Serpro (CE, DI históricos)

3. **Bancos**
   - Banco do Brasil (extratos, saldos)
   - Santander Open Banking (extratos, saldos)

4. **Fornecedores/Clientes**
   - ReceitaWS (CPF/CNPJ)
   - Conecta gov.br (CPF/CNPJ - futuro)

5. **Legislação**
   - Assistants API (vetorização)
   - Arquivos locais (legislacao_files/)

6. **Comunicação**
   - Email (SMTP)
   - WhatsApp (preparação futura)

7. **IA e Aprendizado**
   - Conversas do chat
   - Regras aprendidas
   - Contexto de sessão
   - Consultas salvas

8. **Outros**
   - PTAX (câmbio)
   - TECwin (NCM)
   - Consultas bilhetadas

---

## 🏗️ Arquitetura do Banco de Dados

### Princípios de Design

1. **Campos Verbosos**: Todos os campos têm nomes descritivos e claros
2. **Rastreabilidade**: Toda tabela tem `fonte_dados`, `ultima_sincronizacao`, `json_dados_originais`
3. **Versionamento**: Campos `versao_dados` e `hash_dados` para controle de mudanças
4. **Normalização**: DTOs para abstrair diferenças entre APIs
5. **Performance**: Índices estratégicos para consultas rápidas
6. **Escalabilidade**: Preparado para crescimento futuro

### Estrutura de Schemas

```sql
mAIke_assistente/
├── dbo/                    -- Schema principal
│   ├── PROCESSO_IMPORTACAO
│   ├── DOCUMENTO_ADUANEIRO
│   ├── FORNECEDOR_CLIENTE
│   ├── MOVIMENTACAO_BANCARIA
│   ├── TIMELINE_PROCESSO
│   └── ...
├── comunicacao/            -- Schema de comunicação
│   ├── EMAIL_ENVIADO
│   ├── EMAIL_AGENDADO
│   ├── WHATSAPP_MENSAGEM
│   └── ...
├── ia/                     -- Schema de IA e aprendizado
│   ├── CONVERSA_CHAT
│   ├── REGRA_APRENDIDA
│   ├── CONTEXTO_SESSAO
│   ├── CONSULTA_SALVA
│   └── ...
├── legislacao/             -- Schema de legislação
│   ├── LEGISLACAO_IMPORTADA
│   ├── LEGISLACAO_VETORIZACAO
│   ├── LEGISLACAO_CHUNK
│   └── ...
└── auditoria/              -- Schema de auditoria
    ├── LOG_SINCRONIZACAO
    ├── LOG_CONSULTA_API
    ├── LOG_ERRO
    └── ...
```

---

## 📊 Tabelas Principais

### 1. PROCESSO_IMPORTACAO

**Descrição:** Tabela central consolidada de processos de importação de todas as fontes.

```sql
CREATE TABLE [dbo].[PROCESSO_IMPORTACAO] (
    -- Identificação
    id_processo BIGINT IDENTITY(1,1) PRIMARY KEY,
    processo_referencia VARCHAR(50) NOT NULL UNIQUE,  -- Ex: "DMD.0018/25"
    categoria_processo VARCHAR(10) NOT NULL,          -- Ex: "DMD", "VDM", "ALH"
    numero_processo VARCHAR(20),                     -- Número sem categoria
    ano_processo VARCHAR(4),                         -- Ano do processo
    
    -- Status e Situação
    status_atual VARCHAR(100),                       -- Ex: "Aguardando Documentos"
    status_anterior VARCHAR(100),                    -- Status anterior
    situacao_processo VARCHAR(100),                  -- Situação técnica
    situacao_ce VARCHAR(100),                        -- Status do CE
    situacao_di VARCHAR(100),                        -- Status da DI
    situacao_duimp VARCHAR(100),                     -- Status da DUIMP
    
    -- Datas Importantes
    data_criacao_processo DATETIME,
    data_ultima_atualizacao DATETIME,
    data_chegada DATETIME,                           -- Data de chegada confirmada
    data_eta DATETIME,                               -- ETA (Estimated Time of Arrival)
    data_desembaraco DATETIME,                       -- Data de desembaraço
    data_prevista_desembaraco DATETIME,              -- Data prevista de desembaraço
    data_destino_final DATETIME,                     -- Data de destino final (confirmação de chegada)
    
    -- Transporte
    modal_transporte VARCHAR(20),                    -- "Marítimo", "Aéreo", "Rodoviário"
    porto_origem_codigo VARCHAR(10),
    porto_origem_nome VARCHAR(255),
    porto_destino_codigo VARCHAR(10),
    porto_destino_nome VARCHAR(255),
    nome_navio VARCHAR(255),
    numero_viagem VARCHAR(50),
    
    -- ETA e Tracking (ShipsGo)
    eta_shipsgo DATETIME,                           -- ETA do ShipsGo (Data POD - mais confiável)
    porto_shipsgo_codigo VARCHAR(10),
    porto_shipsgo_nome VARCHAR(255),
    status_shipsgo VARCHAR(100),
    shipsgo_ultima_atualizacao DATETIME,
    
    -- Documentos Vinculados
    numero_ce VARCHAR(50),                           -- Conhecimento de Embarque
    numero_cct VARCHAR(50),                          -- Conhecimento de Carga Aérea
    numero_di VARCHAR(50),                            -- Declaração de Importação
    numero_duimp VARCHAR(50),                         -- DUIMP
    numero_dta VARCHAR(50),                           -- Documento de Transporte Aduaneiro
    numero_lpco VARCHAR(50),                         -- Licença de Importação
    situacao_lpco VARCHAR(100),                      -- Status do LPCO (deferido, indeferido, etc.)
    
    -- Valores Financeiros
    valor_fob_usd DECIMAL(18,2),
    valor_fob_brl DECIMAL(18,2),
    valor_frete_usd DECIMAL(18,2),
    valor_frete_brl DECIMAL(18,2),
    valor_seguro_usd DECIMAL(18,2),
    valor_seguro_brl DECIMAL(18,2),
    valor_cif_usd DECIMAL(18,2),
    valor_cif_brl DECIMAL(18,2),
    moeda_codigo VARCHAR(3) DEFAULT 'USD',           -- Ex: "USD", "BRL"
    taxa_cambio DECIMAL(10,6),                       -- Taxa de câmbio usada
    
    -- Fornecedor/Cliente
    fornecedor_cnpj VARCHAR(18),
    fornecedor_razao_social VARCHAR(255),
    cliente_cnpj VARCHAR(18),
    cliente_razao_social VARCHAR(255),
    
    -- Pendências
    tem_pendencia_icms BIT DEFAULT 0,
    tem_pendencia_frete BIT DEFAULT 0,
    tem_pendencia_afrmm BIT DEFAULT 0,
    tem_pendencia_lpco BIT DEFAULT 0,
    tem_bloqueio_ce BIT DEFAULT 0,
    descricao_pendencias TEXT,
    
    -- Origem dos Dados (Rastreabilidade)
    fonte_dados VARCHAR(50),                        -- Ex: "KANBAN_API", "SQL_SERVER", "SHIPSGO"
    ultima_sincronizacao DATETIME,
    versao_dados INT DEFAULT 1,                      -- Controle de versões
    hash_dados VARCHAR(64),                          -- Hash para detectar mudanças
    json_dados_originais NVARCHAR(MAX),             -- Backup dos dados brutos da API
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_processo_referencia (processo_referencia),
    INDEX idx_categoria (categoria_processo),
    INDEX idx_status (status_atual),
    INDEX idx_data_chegada (data_chegada),
    INDEX idx_eta (data_eta),
    INDEX idx_desembaraco (data_desembaraco),
    INDEX idx_fonte_dados (fonte_dados, ultima_sincronizacao),
    INDEX idx_fornecedor (fornecedor_cnpj),
    INDEX idx_cliente (cliente_cnpj)
);
```

### 2. DOCUMENTO_ADUANEIRO

**Descrição:** Tabela consolidada de todos os documentos aduaneiros (CE, CCT, DI, DUIMP).

```sql
CREATE TABLE [dbo].[DOCUMENTO_ADUANEIRO] (
    -- Identificação
    id_documento BIGINT IDENTITY(1,1) PRIMARY KEY,
    numero_documento VARCHAR(50) NOT NULL,           -- Ex: "123456789", "25BR00002369283"
    tipo_documento VARCHAR(50) NOT NULL,             -- Ex: "CE", "CCT", "DI", "DUIMP"
    tipo_documento_descricao VARCHAR(100),          -- Ex: "Conhecimento de Embarque"
    versao_documento VARCHAR(10),                    -- Versão (para DUIMP)
    
    -- Vínculo com Processo
    processo_referencia VARCHAR(50),                 -- FK para PROCESSO_IMPORTACAO
    id_importacao BIGINT,                           -- ID do SQL Server (compatibilidade)
    
    -- Status Detalhado
    status_documento VARCHAR(100),                  -- Ex: "Registrado", "Pendente", "Cancelado"
    status_documento_codigo VARCHAR(20),           -- Código da API (para compatibilidade)
    canal_documento VARCHAR(20),                    -- Ex: "VERDE", "AMARELO", "VERMELHO"
    situacao_documento VARCHAR(100),                -- Situação técnica detalhada
    
    -- Datas
    data_registro DATETIME,
    data_situacao DATETIME,
    data_desembaraco DATETIME,
    data_prevista_desembaraco DATETIME,
    data_entrega_carga DATETIME,
    
    -- Valores Financeiros
    valor_fob_usd DECIMAL(18,2),
    valor_fob_brl DECIMAL(18,2),
    valor_frete_usd DECIMAL(18,2),
    valor_frete_brl DECIMAL(18,2),
    valor_seguro_usd DECIMAL(18,2),
    valor_seguro_brl DECIMAL(18,2),
    valor_cif_usd DECIMAL(18,2),
    valor_cif_brl DECIMAL(18,2),
    moeda_codigo VARCHAR(3) DEFAULT 'USD',
    taxa_cambio DECIMAL(10,6),
    
    -- Impostos (para DI/DUIMP)
    valor_ii_usd DECIMAL(18,2),
    valor_ii_brl DECIMAL(18,2),
    valor_ipi_usd DECIMAL(18,2),
    valor_ipi_brl DECIMAL(18,2),
    valor_pis_usd DECIMAL(18,2),
    valor_pis_brl DECIMAL(18,2),
    valor_cofins_usd DECIMAL(18,2),
    valor_cofins_brl DECIMAL(18,2),
    valor_antidumping_usd DECIMAL(18,2),
    valor_antidumping_brl DECIMAL(18,2),
    valor_taxa_siscomex_usd DECIMAL(18,2),
    valor_taxa_siscomex_brl DECIMAL(18,2),
    total_impostos_usd DECIMAL(18,2),
    total_impostos_brl DECIMAL(18,2),
    
    -- Transporte (para CE/CCT)
    porto_origem_codigo VARCHAR(10),
    porto_origem_nome VARCHAR(255),
    porto_destino_codigo VARCHAR(10),
    porto_destino_nome VARCHAR(255),
    pais_procedencia VARCHAR(3),                    -- Código ISO
    pais_procedencia_nome VARCHAR(255),
    nome_navio VARCHAR(255),
    numero_viagem VARCHAR(50),
    tipo_transporte VARCHAR(20),                    -- "Marítimo", "Aéreo"
    
    -- Informações Adicionais
    descricao_mercadoria TEXT,
    quantidade_itens INT,
    peso_bruto DECIMAL(18,3),
    peso_liquido DECIMAL(18,3),
    volume DECIMAL(18,3),
    
    -- Origem
    fonte_dados VARCHAR(50),                        -- Ex: "PORTAL_UNICO", "INTEGRACOMEX", "SQL_SERVER"
    ultima_sincronizacao DATETIME,
    versao_dados INT DEFAULT 1,
    hash_dados VARCHAR(64),
    json_dados_originais NVARCHAR(MAX),
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_numero_documento (numero_documento),
    INDEX idx_tipo_documento (tipo_documento),
    INDEX idx_processo (processo_referencia),
    INDEX idx_status (status_documento),
    INDEX idx_canal (canal_documento),
    INDEX idx_data_desembaraco (data_desembaraco),
    INDEX idx_fonte_dados (fonte_dados, ultima_sincronizacao)
);
```

### 3. FORNECEDOR_CLIENTE

**Descrição:** Tabela consolidada de fornecedores e clientes (CPF/CNPJ).

```sql
CREATE TABLE [dbo].[FORNECEDOR_CLIENTE] (
    -- Identificação
    id_fornecedor_cliente BIGINT IDENTITY(1,1) PRIMARY KEY,
    cpf_cnpj VARCHAR(18) NOT NULL UNIQUE,           -- Limpo e formatado
    tipo_pessoa VARCHAR(20) NOT NULL,               -- Ex: "PESSOA_FISICA", "PESSOA_JURIDICA"
    
    -- Dados Principais
    razao_social VARCHAR(255),
    nome_fantasia VARCHAR(255),
    nome_completo VARCHAR(255),                     -- Para PF
    
    -- Endereço Completo
    endereco_logradouro VARCHAR(255),
    endereco_numero VARCHAR(20),
    endereco_complemento VARCHAR(100),
    endereco_bairro VARCHAR(100),
    endereco_cidade VARCHAR(100),
    endereco_estado VARCHAR(2),
    endereco_cep VARCHAR(10),
    endereco_pais VARCHAR(3) DEFAULT 'BRA',
    
    -- Contatos
    telefone_principal VARCHAR(20),
    telefone_secundario VARCHAR(20),
    email_principal VARCHAR(255),
    email_secundario VARCHAR(255),
    site VARCHAR(255),
    
    -- Informações Adicionais
    inscricao_estadual VARCHAR(50),
    inscricao_municipal VARCHAR(50),
    situacao_cadastral VARCHAR(50),                -- Ex: "ATIVA", "SUSPENSA"
    data_abertura DATE,
    capital_social DECIMAL(18,2),
    porte_empresa VARCHAR(50),                     -- Ex: "MICRO", "PEQUENA", "MEDIA", "GRANDE"
    
    -- Origem
    fonte_dados VARCHAR(50),                       -- Ex: "RECEITAWS", "SERPRO", "CONECTA_GOV"
    ultima_consulta DATETIME,
    ultima_atualizacao DATETIME,
    versao_dados INT DEFAULT 1,
    hash_dados VARCHAR(64),
    json_dados_originais NVARCHAR(MAX),
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_cpf_cnpj (cpf_cnpj),
    INDEX idx_tipo_pessoa (tipo_pessoa),
    INDEX idx_razao_social (razao_social),
    INDEX idx_fonte_dados (fonte_dados, ultima_atualizacao)
);
```

### 4. MOVIMENTACAO_BANCARIA

**Descrição:** Tabela consolidada de movimentações bancárias (BB e Santander).

**⚠️ IMPORTANTE:** Esta tabela armazena **lançamentos individuais** (não PDFs de extratos). Cada linha representa uma movimentação bancária que pode ser vinculada a:
- **Processo de importação** (`processo_referencia`) - Ex: ALH.0001/25
- **Plano de contas** (`plano_contas_codigo`) - Ex: 1.1.01.001
- **Histórico interno** (`historico_interno`) - Histórico personalizado para contabilidade

**Objetivo:** Permitir conciliação bancária e classificação contábil de cada movimentação individualmente.

```sql
CREATE TABLE [dbo].[MOVIMENTACAO_BANCARIA] (
    -- Identificação
    id_movimentacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Banco de Origem
    banco_origem VARCHAR(50) NOT NULL,             -- Ex: "BANCO_DO_BRASIL", "SANTANDER"
    agencia_origem VARCHAR(20),
    conta_origem VARCHAR(50),
    tipo_conta_origem VARCHAR(20),                 -- Ex: "CORRENTE", "POUPANCA"
    
    -- Banco de Destino (se transferência)
    agencia_destino VARCHAR(20),
    conta_destino VARCHAR(50),
    tipo_conta_destino VARCHAR(20),
    
    -- Transação
    data_movimentacao DATETIME NOT NULL,
    data_lancamento DATETIME,
    tipo_movimentacao VARCHAR(50),                 -- Ex: "TRANSFERENCIA", "PIX", "TED", "DOC"
    sinal_movimentacao VARCHAR(1) NOT NULL,        -- Ex: "C" (Crédito), "D" (Débito)
    valor_movimentacao DECIMAL(18,2) NOT NULL,
    moeda VARCHAR(3) DEFAULT 'BRL',
    
    -- Contrapartida (CRÍTICO PARA COMPLIANCE - Receita Federal)
    cpf_cnpj_contrapartida VARCHAR(18),             -- CPF/CNPJ da contrapartida (OBRIGATÓRIO para compliance)
    nome_contrapartida VARCHAR(255),                -- Nome completo da contrapartida (OBRIGATÓRIO)
    tipo_pessoa_contrapartida VARCHAR(20),         -- "PESSOA_FISICA" ou "PESSOA_JURIDICA"
    banco_contrapartida VARCHAR(50),
    agencia_contrapartida VARCHAR(20),
    conta_contrapartida VARCHAR(50),
    dv_conta_contrapartida VARCHAR(5),
    
    -- Validação da Contrapartida (CRÍTICO)
    contrapartida_validada BIT DEFAULT 0,           -- Se CPF/CNPJ foi validado em bases oficiais
    data_validacao_contrapartida DATETIME,          -- Data da validação
    fonte_validacao_contrapartida VARCHAR(50),      -- Fonte da validação (ex: "RECEITAWS", "SERPRO")
    nome_validado_contrapartida VARCHAR(255),       -- Nome retornado pela validação (para comparar)
    
    -- Descrição
    descricao_movimentacao TEXT,
    historico_codigo VARCHAR(20),
    historico_descricao VARCHAR(255),
    informacoes_complementares TEXT,
    
    -- ⚠️ NOTA: Para relacionar um lançamento a múltiplos processos, usar tabela MOVIMENTACAO_BANCARIA_PROCESSO
    -- Este campo é mantido apenas para compatibilidade com lançamentos simples (1:1)
    processo_referencia VARCHAR(50),               -- FK opcional para PROCESSO_IMPORTACAO (apenas se for 1 processo)
    tipo_relacionamento VARCHAR(50),               -- Ex: "PAGAMENTO_FRETE", "PAGAMENTO_FOB", "PAGAMENTO_IMPOSTO"
    
    -- Classificação Contábil e Histórico
    plano_contas_codigo VARCHAR(50),               -- Código do plano de contas (ex: "1.1.01.001")
    plano_contas_descricao VARCHAR(255),          -- Descrição do plano de contas
    historico_interno VARCHAR(255),                -- Histórico interno personalizado
    centro_custo VARCHAR(100),                     -- Centro de custo (opcional)
    
    -- Rastreabilidade
    fonte_dados VARCHAR(50),                       -- Ex: "BB_API", "SANTANDER_OPEN_BANKING"
    ultima_sincronizacao DATETIME,
    versao_dados INT DEFAULT 1,
    hash_dados VARCHAR(64),
    json_dados_originais NVARCHAR(MAX),
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_banco_origem (banco_origem, data_movimentacao),
    INDEX idx_data_movimentacao (data_movimentacao),
    INDEX idx_tipo_movimentacao (tipo_movimentacao),
    INDEX idx_processo (processo_referencia),
    INDEX idx_contrapartida (cpf_cnpj_contrapartida),
    INDEX idx_fonte_dados (fonte_dados, ultima_sincronizacao),
    INDEX idx_plano_contas (plano_contas_codigo),
    INDEX idx_historico_interno (historico_interno),
    INDEX idx_centro_custo (centro_custo)
);
```

### 5. MOVIMENTACAO_BANCARIA_PROCESSO ⭐ **NOVO**

**Descrição:** Tabela de relacionamento N:N entre movimentações bancárias e processos. Permite que **um lançamento seja dividido entre vários processos**, cada um com seu valor específico.

**Exemplo de uso:**
- Lançamento: Armazenagem R$ 10.000,00
- Dividido em:
  - ALH.0001/25: R$ 3.000,00
  - BGR.0005/25: R$ 2.000,00
  - DMD.0050/25: R$ 5.000,00

```sql
CREATE TABLE [dbo].[MOVIMENTACAO_BANCARIA_PROCESSO] (
    -- Identificação
    id_relacionamento BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Vínculos (pode ser processo OU categoria)
    id_movimentacao_bancaria BIGINT NOT NULL,       -- FK para MOVIMENTACAO_BANCARIA
    processo_referencia VARCHAR(50),                -- FK opcional para PROCESSO_IMPORTACAO (se for despesa específica)
    categoria_processo VARCHAR(10),                 -- Categoria (ex: "ALH", "BGR") - se for despesa por categoria
    
    -- Valor específico para este processo/categoria
    valor_parcela DECIMAL(18,2) NOT NULL,          -- Valor desta parcela do lançamento
    moeda VARCHAR(3) DEFAULT 'BRL',
    percentual_parcela DECIMAL(5,2),                 -- Percentual do valor total (opcional, para validação)
    
    -- Tipo de relacionamento
    tipo_relacionamento VARCHAR(50),                 -- Ex: "PAGAMENTO_FRETE", "PAGAMENTO_ARMAZENAGEM", "PAGAMENTO_IMPOSTO", "PAGAMENTO_FOB", "PAGAMENTO_CONSULTORIA"
    tipo_relacionamento_descricao VARCHAR(255),     -- Descrição amigável
    
    -- Nível de vinculação
    nivel_vinculo VARCHAR(20),                      -- "PROCESSO" ou "CATEGORIA" - define se é vinculação específica ou por categoria
    
    -- Vínculo com despesa (opcional)
    id_despesa_processo BIGINT,                    -- FK opcional para DESPESA_PROCESSO
    
    -- Status
    status_vinculo VARCHAR(20) DEFAULT 'ativo',     -- 'ativo', 'cancelado', 'ajustado'
    
    -- Validação
    validado_por VARCHAR(100),                      -- Usuário que validou a divisão
    data_validacao DATETIME,
    observacoes_validacao TEXT,
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Constraint: garantir que a soma das parcelas não exceda o valor total
    -- (será validado na aplicação, não no banco)
    
    -- Índices
    INDEX idx_movimentacao (id_movimentacao_bancaria),
    INDEX idx_processo (processo_referencia),
    INDEX idx_categoria (categoria_processo),
    INDEX idx_nivel_vinculo (nivel_vinculo, categoria_processo),
    INDEX idx_tipo_relacionamento (tipo_relacionamento),
    INDEX idx_status (status_vinculo),
    INDEX idx_despesa (id_despesa_processo),
    
    -- Constraint única: uma movimentação não pode ter a mesma parcela duplicada
    -- Se nivel_vinculo = 'PROCESSO', usa processo_referencia
    -- Se nivel_vinculo = 'CATEGORIA', usa categoria_processo
    -- Validado na aplicação
);
```

**Validações importantes:**
- A soma de todas as parcelas (`valor_parcela`) de uma movimentação deve ser igual ao `valor_movimentacao` da `MOVIMENTACAO_BANCARIA`
- Validação será feita na aplicação (não no banco) para permitir flexibilidade

### 6. TIMELINE_PROCESSO

**Descrição:** Histórico completo de mudanças em processos (nível de processo).

**⚠️ NOTA:** Para histórico de mudanças em documentos específicos (DI, DUIMP, CE, CCT), ver tabela `HISTORICO_DOCUMENTO_ADUANEIRO`.

```sql
CREATE TABLE [dbo].[TIMELINE_PROCESSO] (
    -- Identificação
    id_timeline BIGINT IDENTITY(1,1) PRIMARY KEY,
    processo_referencia VARCHAR(50) NOT NULL,      -- FK para PROCESSO_IMPORTACAO
    
    -- Evento
    data_evento DATETIME NOT NULL,
    tipo_evento VARCHAR(50) NOT NULL,               -- Ex: "STATUS_ALTERADO", "DOCUMENTO_REGISTRADO", "ETA_ALTERADO"
    tipo_evento_descricao VARCHAR(255),            -- Ex: "Status alterado de 'Em Análise' para 'Aguardando Documentos'"
    
    -- Valores
    valor_anterior VARCHAR(255),
    valor_novo VARCHAR(255),
    campo_alterado VARCHAR(100),                   -- Ex: "status_atual", "data_chegada"
    
    -- Origem
    usuario_ou_sistema VARCHAR(100),              -- Ex: "SISCOMEX", "mAIke", "Usuario: João"
    fonte_dados VARCHAR(50),                       -- Ex: "KANBAN_API", "SQL_SERVER", "PORTAL_UNICO"
    
    -- Detalhes
    observacoes TEXT,
    json_dados_originais NVARCHAR(MAX),
    
    -- Metadados
    criado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_processo (processo_referencia, data_evento DESC),
    INDEX idx_tipo_evento (tipo_evento, data_evento DESC),
    INDEX idx_campo_alterado (campo_alterado, data_evento DESC)
);
```

### 6.1. HISTORICO_DOCUMENTO_ADUANEIRO ⭐ **NOVO**

**Descrição:** Histórico completo de todas as mudanças em documentos aduaneiros (DI, DUIMP, CE, CCT).

**⚠️ IMPORTANTE:** Todas as APIs (Integra Comex, DUIMP) trazem mudanças de documentos. Esses históricos são relevantes e devem ser gravados.

**Campos principais:**
- `id_documento` - FK para DOCUMENTO_ADUANEIRO
- `numero_documento` - Número do documento (CE, DI, DUIMP, CCT)
- `tipo_documento` - Tipo do documento
- `data_evento` - Data/hora da mudança (da API)
- `tipo_evento` - Tipo de evento (MUDANCA_STATUS, MUDANCA_CANAL, etc.)
- `campo_alterado` - Campo que mudou (status_documento, canal_documento, etc.)
- `valor_anterior` / `valor_novo` - Valores antes e depois
- `fonte_dados` - Fonte da mudança (INTEGRACOMEX, DUIMP_API, PORTAL_UNICO)
- `json_dados_originais` - JSON completo retornado pela API

```sql
CREATE TABLE [dbo].[HISTORICO_DOCUMENTO_ADUANEIRO] (
    id_historico BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_documento BIGINT,
    numero_documento VARCHAR(50) NOT NULL,
    tipo_documento VARCHAR(50) NOT NULL,
    
    processo_referencia VARCHAR(50),
    
    data_evento DATETIME NOT NULL,
    tipo_evento VARCHAR(50) NOT NULL,
    tipo_evento_descricao VARCHAR(255),
    
    campo_alterado VARCHAR(100) NOT NULL,
    valor_anterior VARCHAR(500),
    valor_novo VARCHAR(500),
    
    status_documento VARCHAR(100),
    status_documento_codigo VARCHAR(20),
    canal_documento VARCHAR(20),
    situacao_documento VARCHAR(100),
    
    data_registro DATETIME,
    data_situacao DATETIME,
    data_desembaraco DATETIME,
    
    fonte_dados VARCHAR(50) NOT NULL,
    api_endpoint VARCHAR(500),
    json_dados_originais NVARCHAR(MAX),
    
    usuario_ou_sistema VARCHAR(100),
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    
    INDEX idx_documento (id_documento, data_evento DESC),
    INDEX idx_numero_documento (numero_documento, tipo_documento, data_evento DESC),
    INDEX idx_processo (processo_referencia, data_evento DESC),
    INDEX idx_tipo_evento (tipo_evento, data_evento DESC),
    INDEX idx_campo_alterado (campo_alterado, data_evento DESC),
    INDEX idx_fonte_dados (fonte_dados, data_evento DESC)
);
```

**Tipos de eventos:**
- `MUDANCA_STATUS` - Status/situação mudou
- `MUDANCA_CANAL` - Canal mudou (VERDE → AMARELO)
- `MUDANCA_DATA` - Datas importantes mudaram
- `MUDANCA_VALOR` - Valores financeiros mudaram
- `MUDANCA_OUTROS` - Outras mudanças relevantes

---

## 🔌 Tabelas de Integração

### 7. SHIPSGO_TRACKING

**Descrição:** Dados de tracking do ShipsGo (ETA, porto, status).

```sql
CREATE TABLE [dbo].[SHIPSGO_TRACKING] (
    -- Identificação
    id_tracking BIGINT IDENTITY(1,1) PRIMARY KEY,
    processo_referencia VARCHAR(50) NOT NULL UNIQUE, -- FK para PROCESSO_IMPORTACAO
    
    -- ETA e Porto
    eta_iso DATETIME,                               -- ETA do ShipsGo (Data POD - mais confiável)
    porto_codigo VARCHAR(10),
    porto_nome VARCHAR(255),
    status VARCHAR(100),
    
    -- Dados Brutos
    payload_raw NVARCHAR(MAX),                      -- JSON completo da API
    
    -- Metadados
    ultima_sincronizacao DATETIME,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_processo (processo_referencia),
    INDEX idx_eta (eta_iso),
    INDEX idx_porto (porto_codigo)
);
```

### 8. CONSULTA_BILHETADA

**Descrição:** Rastreamento de consultas bilhetadas (Integra Comex).

```sql
CREATE TABLE [dbo].[CONSULTA_BILHETADA] (
    -- Identificação
    id_consulta BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Detalhes da Consulta
    tipo_consulta VARCHAR(50) NOT NULL,             -- Ex: "CE", "DI", "Manifesto", "Escala", "CCT"
    numero_documento VARCHAR(50),
    endpoint VARCHAR(500) NOT NULL,
    metodo VARCHAR(10) DEFAULT 'GET',
    
    -- Resultado
    status_code INT,
    sucesso BIT DEFAULT 1,
    data_consulta DATETIME DEFAULT GETDATE(),
    
    -- Vínculo
    processo_referencia VARCHAR(50),               -- FK opcional para PROCESSO_IMPORTACAO
    
    -- Verificação Prévia
    usou_api_publica_antes BIT DEFAULT 0,           -- Se verificou API pública antes
    data_verificacao_publica DATETIME,
    
    -- Observações
    observacoes TEXT,
    
    -- Índices
    INDEX idx_tipo_consulta (tipo_consulta, data_consulta),
    INDEX idx_processo (processo_referencia),
    INDEX idx_data_consulta (data_consulta)
);
```

### 9. CONSULTA_BILHETADA_PENDENTE

**Descrição:** Fila de consultas bilhetadas pendentes de aprovação.

```sql
CREATE TABLE [dbo].[CONSULTA_BILHETADA_PENDENTE] (
    -- Identificação
    id_pendente BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Detalhes da Consulta
    tipo_consulta VARCHAR(50) NOT NULL,
    numero_documento VARCHAR(50) NOT NULL,
    endpoint VARCHAR(500) NOT NULL,
    metodo VARCHAR(10) DEFAULT 'GET',
    
    -- Vínculo
    processo_referencia VARCHAR(50),
    
    -- Motivo
    motivo TEXT,                                    -- Por que precisa consultar
    data_publica_verificada DATETIME,               -- Data da última verificação na API pública
    data_ultima_alteracao_cache DATETIME,            -- Data da última alteração no cache
    
    -- Aprovação
    status VARCHAR(20) DEFAULT 'pendente',          -- 'pendente', 'aprovado', 'rejeitado', 'executado'
    aprovado_em DATETIME,
    aprovado_por VARCHAR(100),                      -- Usuário que aprovou
    processando_aprovacao DATETIME,
    
    -- Observações
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_status (status, criado_em),
    INDEX idx_tipo_consulta (tipo_consulta, numero_documento)
);
```

---

## 📧 Tabelas de Comunicação

### 10. EMAIL_ENVIADO

**Descrição:** Histórico completo de emails enviados.

```sql
CREATE TABLE [comunicacao].[EMAIL_ENVIADO] (
    -- Identificação
    id_email BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Destinatário
    email_destinatario VARCHAR(255) NOT NULL,
    nome_destinatario VARCHAR(255),
    
    -- Conteúdo
    assunto VARCHAR(500) NOT NULL,
    corpo_email TEXT NOT NULL,
    corpo_html TEXT,                                 -- Versão HTML se disponível
    
    -- Tipo de Email
    tipo_email VARCHAR(50),                          -- Ex: "CLASSIFICACAO_NCM", "RELATORIO", "BRIEFING", "PERSONALIZADO"
    template_usado VARCHAR(100),                    -- Template usado (se aplicável)
    
    -- Vínculo
    processo_referencia VARCHAR(50),                -- FK opcional para PROCESSO_IMPORTACAO
    session_id VARCHAR(100),                         -- Sessão que gerou o email
    
    -- Status
    status_envio VARCHAR(20) DEFAULT 'enviado',     -- 'enviado', 'falhou', 'pendente'
    data_envio DATETIME DEFAULT GETDATE(),
    mensagem_erro TEXT,
    
    -- Confirmação
    confirmado_antes_envio BIT DEFAULT 1,          -- Se foi confirmado pelo usuário antes de enviar
    data_confirmacao DATETIME,
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_destinatario (email_destinatario, data_envio DESC),
    INDEX idx_tipo_email (tipo_email, data_envio DESC),
    INDEX idx_processo (processo_referencia),
    INDEX idx_status (status_envio)
);
```

### 11. EMAIL_AGENDADO

**Descrição:** Emails agendados para envio futuro.

```sql
CREATE TABLE [comunicacao].[EMAIL_AGENDADO] (
    -- Identificação
    id_agendamento BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Destinatário
    email_destinatario VARCHAR(255) NOT NULL,
    nome_destinatario VARCHAR(255),
    
    -- Conteúdo
    assunto VARCHAR(500) NOT NULL,
    corpo_email TEXT NOT NULL,
    corpo_html TEXT,
    
    -- Agendamento
    data_agendamento DATETIME NOT NULL,
    tipo_agendamento VARCHAR(50),                   -- Ex: "DIARIO", "SEMANAL", "MENSAL", "PERSONALIZADO"
    recorrente BIT DEFAULT 0,
    proxima_execucao DATETIME,
    
    -- Status
    status VARCHAR(20) DEFAULT 'agendado',          -- 'agendado', 'enviado', 'cancelado', 'falhou'
    tentativas INT DEFAULT 0,
    ultima_tentativa DATETIME,
    mensagem_erro TEXT,
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_data_agendamento (data_agendamento),
    INDEX idx_status (status),
    INDEX idx_proxima_execucao (proxima_execucao)
);
```

### 12. WHATSAPP_MENSAGEM

**Descrição:** Preparação futura para integração WhatsApp.

```sql
CREATE TABLE [comunicacao].[WHATSAPP_MENSAGEM] (
    -- Identificação
    id_mensagem BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Destinatário
    numero_whatsapp VARCHAR(20) NOT NULL,           -- Número com código do país
    nome_contato VARCHAR(255),
    
    -- Conteúdo
    tipo_mensagem VARCHAR(20) DEFAULT 'texto',      -- 'texto', 'imagem', 'documento', 'audio'
    conteudo_mensagem TEXT,
    url_anexo VARCHAR(500),                          -- URL de anexo (imagem, PDF, etc.)
    
    -- Vínculo
    processo_referencia VARCHAR(50),                -- FK opcional para PROCESSO_IMPORTACAO
    session_id VARCHAR(100),
    
    -- Status
    status_envio VARCHAR(20) DEFAULT 'pendente',    -- 'pendente', 'enviado', 'entregue', 'lido', 'falhou'
    data_envio DATETIME,
    data_entrega DATETIME,
    data_leitura DATETIME,
    mensagem_erro TEXT,
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_numero (numero_whatsapp, data_envio DESC),
    INDEX idx_status (status_envio),
    INDEX idx_processo (processo_referencia)
);
```

---

## 🤖 Tabelas de IA e Aprendizado

### 13. CONVERSA_CHAT

**Descrição:** Histórico completo de conversas do chat.

```sql
CREATE TABLE [ia].[CONVERSA_CHAT] (
    -- Identificação
    id_conversa BIGINT IDENTITY(1,1) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    
    -- Mensagens
    mensagem_usuario TEXT NOT NULL,
    resposta_ia TEXT NOT NULL,
    
    -- Classificação
    tipo_conversa VARCHAR(50),                      -- Ex: 'consulta', 'acao', 'geral', 'calculo', 'relatorio'
    processo_referencia VARCHAR(50),                 -- FK opcional para PROCESSO_IMPORTACAO
    categoria_processo VARCHAR(10),                 -- Categoria mencionada
    
    -- Importância
    importante BIT DEFAULT 0,                        -- Se é uma conversa importante
    tags VARCHAR(500),                               -- Tags separadas por vírgula
    
    -- Metadados
    modelo_ia_usado VARCHAR(50),                    -- Ex: "gpt-4o", "gpt-4o-mini"
    tempo_resposta_ms INT,                          -- Tempo de resposta em milissegundos
    tokens_usados INT,                              -- Tokens consumidos
    custo_estimado DECIMAL(10,6),                  -- Custo estimado em USD
    
    -- Timestamps
    criado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_session (session_id, criado_em DESC),
    INDEX idx_tipo_conversa (tipo_conversa),
    INDEX idx_processo (processo_referencia),
    INDEX idx_importante (importante, criado_em DESC)
);
```

### 14. REGRA_APRENDIDA

**Descrição:** Regras aprendidas pelo sistema.

```sql
CREATE TABLE [ia].[REGRA_APRENDIDA] (
    -- Identificação
    id_regra BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Classificação
    tipo_regra VARCHAR(50) NOT NULL,                -- Ex: 'campo_definicao', 'regra_negocio', 'preferencia_usuario'
    contexto VARCHAR(100),                          -- Ex: 'chegada_processos', 'analise_vdm', 'calculo_impostos'
    nome_regra VARCHAR(255) NOT NULL,                -- Nome amigável da regra
    
    -- Descrição
    descricao TEXT NOT NULL,                        -- Descrição completa
    aplicacao_sql TEXT,                              -- Como aplicar em SQL
    aplicacao_texto TEXT,                           -- Como aplicar em texto
    exemplo_uso TEXT,                               -- Exemplo de quando usar
    
    -- Origem
    criado_por VARCHAR(100),                        -- user_id ou session_id
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Uso
    vezes_usado INT DEFAULT 0,                      -- Contador de uso
    ultimo_usado_em DATETIME,
    ativa BIT DEFAULT 1,                            -- Se a regra está ativa
    
    -- Índices
    INDEX idx_tipo_regra (tipo_regra, contexto),
    INDEX idx_ativa (ativa, vezes_usado DESC),
    INDEX idx_ultimo_usado (ultimo_usado_em DESC)
);
```

### 15. CONTEXTO_SESSAO

**Descrição:** Contexto persistente de sessão.

```sql
CREATE TABLE [ia].[CONTEXTO_SESSAO] (
    -- Identificação
    id_contexto BIGINT IDENTITY(1,1) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    
    -- Tipo de Contexto
    tipo_contexto VARCHAR(50) NOT NULL,             -- Ex: 'processo_atual', 'categoria_atual', 'ultima_consulta'
    chave VARCHAR(100) NOT NULL,                     -- Chave do contexto
    valor TEXT NOT NULL,                            -- Valor do contexto
    
    -- Dados Adicionais
    dados_json NVARCHAR(MAX),                       -- Dados adicionais em JSON
    
    -- Timestamps
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Constraint
    UNIQUE(session_id, tipo_contexto, chave),
    
    -- Índices
    INDEX idx_session (session_id, tipo_contexto),
    INDEX idx_atualizado (atualizado_em DESC)
);
```

### 16. CONSULTA_SALVA

**Descrição:** Consultas SQL salvas como relatórios reutilizáveis.

```sql
CREATE TABLE [ia].[CONSULTA_SALVA] (
    -- Identificação
    id_consulta BIGINT IDENTITY(1,1) PRIMARY KEY,
    slug VARCHAR(100) NOT NULL UNIQUE,              -- Identificador único
    nome_exibicao VARCHAR(255) NOT NULL,            -- Nome amigável do relatório
    
    -- Descrição
    descricao TEXT,
    sql_base TEXT NOT NULL,                          -- SQL da consulta
    parametros_json NVARCHAR(MAX),                   -- Parâmetros (futuro)
    exemplos_pergunta TEXT,                         -- Exemplos de como pedir
    
    -- Origem
    criado_por VARCHAR(100),                         -- user_id ou session_id
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Uso
    vezes_usado INT DEFAULT 0,                       -- Contador de uso
    ultimo_usado_em DATETIME,
    
    -- Vínculo com Regras
    regra_aprendida_id BIGINT,                       -- FK opcional para REGRA_APRENDIDA
    
    -- Índices
    INDEX idx_slug (slug),
    INDEX idx_vezes_usado (vezes_usado DESC),
    INDEX idx_ultimo_usado (ultimo_usado_em DESC)
);
```

---

## 📚 Tabelas de Vetorização

### 17. LEGISLACAO_IMPORTADA

**Descrição:** Legislações importadas no sistema.

```sql
CREATE TABLE [legislacao].[LEGISLACAO_IMPORTADA] (
    -- Identificação
    id_legislacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Tipo e Número
    tipo_ato VARCHAR(50) NOT NULL,                  -- Ex: "IN", "Lei", "Decreto", "Portaria"
    numero_ato VARCHAR(50) NOT NULL,
    ano_ato INT NOT NULL,
    sigla_orgao VARCHAR(50),                        -- Ex: "RFB", "MDIC"
    titulo_oficial VARCHAR(500),
    
    -- Conteúdo
    texto_completo TEXT NOT NULL,
    url_origem VARCHAR(500),                        -- URL de onde foi importada
    arquivo_local VARCHAR(500),                      -- Caminho do arquivo local
    
    -- Metadados
    data_publicacao DATE,
    data_vigencia DATE,
    data_revogacao DATE,
    ato_revogador VARCHAR(255),
    
    -- Status
    status VARCHAR(20) DEFAULT 'ativa',              -- 'ativa', 'revogada', 'suspensa'
    vetorizada BIT DEFAULT 0,                        -- Se já foi vetorizada
    
    -- Timestamps
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Constraint
    UNIQUE(tipo_ato, numero_ato, ano_ato, sigla_orgao),
    
    -- Índices
    INDEX idx_tipo_numero (tipo_ato, numero_ato, ano_ato),
    INDEX idx_status (status),
    INDEX idx_vetorizada (vetorizada)
);
```

### 18. LEGISLACAO_VETORIZACAO

**Descrição:** Controle de vetorização de legislações.

```sql
CREATE TABLE [legislacao].[LEGISLACAO_VETORIZACAO] (
    -- Identificação
    id_vetorizacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_legislacao BIGINT NOT NULL,                  -- FK para LEGISLACAO_IMPORTADA
    
    -- Vetorização
    vector_store_id VARCHAR(100),                   -- ID do Vector Store (OpenAI)
    file_id VARCHAR(100),                          -- ID do arquivo no OpenAI
    assistant_id VARCHAR(100),                      -- ID do assistente associado
    
    -- Status
    status VARCHAR(20) DEFAULT 'pendente',          -- 'pendente', 'processando', 'concluida', 'erro'
    data_inicio DATETIME,
    data_conclusao DATETIME,
    mensagem_erro TEXT,
    
    -- Estatísticas
    total_chunks INT,                               -- Total de chunks criados
    total_tokens INT,                               -- Total de tokens processados
    custo_estimado DECIMAL(10,6),                  -- Custo estimado em USD
    
    -- Timestamps
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_legislacao (id_legislacao),
    INDEX idx_status (status),
    INDEX idx_vector_store (vector_store_id)
);
```

### 19. LEGISLACAO_CHUNK

**Descrição:** Chunks de legislação para busca semântica.

```sql
CREATE TABLE [legislacao].[LEGISLACAO_CHUNK] (
    -- Identificação
    id_chunk BIGINT IDENTITY(1,1) PRIMARY KEY,
    id_legislacao BIGINT NOT NULL,                  -- FK para LEGISLACAO_IMPORTADA
    id_vetorizacao BIGINT,                          -- FK para LEGISLACAO_VETORIZACAO
    
    -- Conteúdo
    numero_chunk INT NOT NULL,                      -- Número sequencial do chunk
    texto_chunk TEXT NOT NULL,                      -- Texto do chunk
    contexto_antes TEXT,                            -- Contexto antes do chunk
    contexto_depois TEXT,                           -- Contexto depois do chunk
    
    -- Estrutura
    artigo VARCHAR(50),                             -- Artigo do chunk
    paragrafo VARCHAR(50),                          -- Parágrafo do chunk
    inciso VARCHAR(50),                             -- Inciso do chunk
    alinea VARCHAR(50),                             -- Alínea do chunk
    
    -- Metadados
    posicao_inicio INT,                             -- Posição inicial no texto completo
    posicao_fim INT,                                -- Posição final no texto completo
    tamanho_chunk INT,                              -- Tamanho do chunk em caracteres
    
    -- Timestamps
    criado_em DATETIME DEFAULT GETDATE(),
    
    -- Constraint
    UNIQUE(id_legislacao, numero_chunk),
    
    -- Índices
    INDEX idx_legislacao (id_legislacao, numero_chunk),
    INDEX idx_artigo (artigo, paragrafo)
);
```

---

## 💰 Tabelas de Despesas e Financeiro

### 20. DESPESA_PROCESSO

**Descrição:** Despesas previstas e realizadas por processo ou categoria.

**⚠️ IMPORTANTE:** Despesas podem ser vinculadas a:
- **Processo específico** (ex: armazenagem para ALH.0001/25)
- **Categoria** (ex: consultoria para categoria ALH)
- Todo processo tem uma categoria (suas iniciais: ALH.0001/25 → categoria ALH)

**Exemplos:**
- Consultoria: categoria ALH (sem processo específico)
- Armazenagem: processo ALH.0001/25 (processo específico)

```sql
CREATE TABLE [dbo].[DESPESA_PROCESSO] (
    -- Identificação
    id_despesa BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Vínculo (pode ser processo OU categoria)
    processo_referencia VARCHAR(50),                -- FK opcional para PROCESSO_IMPORTACAO (se for despesa específica)
    categoria_processo VARCHAR(10),                -- Categoria (ex: "ALH", "BGR", "DMD") - obrigatório se não tiver processo
    
    -- Tipo de Despesa
    tipo_despesa VARCHAR(50) NOT NULL,             -- Ex: "FRETE", "SEGURO", "IMPOSTO_II", "IMPOSTO_IPI", "IMPOSTO_PIS", "IMPOSTO_COFINS", "ICMS", "AFRMM", "TAXA_SISCOMEX", "DESPACHANTE", "ARMAZENAGEM", "CONSULTORIA", "OUTRAS"
    tipo_despesa_descricao VARCHAR(255),          -- Descrição amigável
    categoria_despesa VARCHAR(50),                 -- Ex: "TRANSPORTE", "IMPOSTO", "TAXA", "SERVICO", "CONSULTORIA"
    
    -- Nível de vinculação
    nivel_vinculo VARCHAR(20) NOT NULL,            -- "PROCESSO" ou "CATEGORIA" - define se é despesa específica ou por categoria
    
    -- Valores
    valor_previsto_usd DECIMAL(18,2),              -- Valor previsto em USD
    valor_previsto_brl DECIMAL(18,2),              -- Valor previsto em BRL
    valor_realizado_usd DECIMAL(18,2),             -- Valor realizado em USD
    valor_realizado_brl DECIMAL(18,2),             -- Valor realizado em BRL
    moeda VARCHAR(3) DEFAULT 'USD',
    taxa_cambio DECIMAL(10,6),                     -- Taxa de câmbio usada
    
    -- Status
    status_despesa VARCHAR(20) DEFAULT 'prevista', -- 'prevista', 'paga', 'pendente', 'cancelada'
    data_prevista_pagamento DATE,
    data_real_pagamento DATE,
    
    -- Vínculo com Movimentação Bancária
    id_movimentacao_bancaria BIGINT,                -- FK opcional para MOVIMENTACAO_BANCARIA
    conciliado BIT DEFAULT 0,                       -- Se foi conciliado com extrato bancário
    
    -- Origem
    fonte_dados VARCHAR(50),                       -- Ex: "DI_OFICIAL", "DUIMP_OFICIAL", "MANUAL", "CALCULADO"
    observacoes TEXT,
    
    -- Metadados
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Validação
    -- CONSTRAINT: Deve ter processo_referencia OU categoria_processo (não ambos obrigatórios)
    -- Validado na aplicação: se nivel_vinculo = 'PROCESSO', processo_referencia é obrigatório
    --                        se nivel_vinculo = 'CATEGORIA', categoria_processo é obrigatório
    
    -- Índices
    INDEX idx_processo (processo_referencia, tipo_despesa),
    INDEX idx_categoria (categoria_processo, tipo_despesa),
    INDEX idx_nivel_vinculo (nivel_vinculo, categoria_processo),
    INDEX idx_status (status_despesa),
    INDEX idx_data_pagamento (data_real_pagamento),
    INDEX idx_conciliado (conciliado)
);
```

### 21. CONCILIACAO_BANCARIA

**Descrição:** Conciliação automática de movimentações bancárias com despesas de processo.

```sql
CREATE TABLE [dbo].[CONCILIACAO_BANCARIA] (
    -- Identificação
    id_conciliacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Vínculos (pode ser processo OU categoria)
    id_movimentacao_bancaria BIGINT NOT NULL,       -- FK para MOVIMENTACAO_BANCARIA
    processo_referencia VARCHAR(50),                -- FK opcional para PROCESSO_IMPORTACAO (se for despesa específica)
    categoria_processo VARCHAR(10),                -- Categoria (ex: "ALH", "BGR") - se for despesa por categoria
    id_despesa_processo BIGINT,                    -- FK opcional para DESPESA_PROCESSO
    
    -- Tipo de Conciliação
    tipo_conciliacao VARCHAR(50),                   -- Ex: "AUTOMATICA", "MANUAL", "SUGESTAO"
    tipo_relacionamento VARCHAR(50),                -- Ex: "PAGAMENTO_FRETE", "PAGAMENTO_FOB", "PAGAMENTO_IMPOSTO", "PAGAMENTO_ICMS", "PAGAMENTO_AFRMM", "PAGAMENTO_CONSULTORIA"
    
    -- Nível de vinculação
    nivel_vinculo VARCHAR(20),                      -- "PROCESSO" ou "CATEGORIA" - define se é conciliação específica ou por categoria
    
    -- Valores
    valor_movimentacao DECIMAL(18,2) NOT NULL,
    valor_despesa DECIMAL(18,2),
    diferenca_valor DECIMAL(18,2),                  -- Diferença entre movimentação e despesa
    percentual_diferenca DECIMAL(5,2),              -- Percentual de diferença
    
    -- Status
    status_conciliacao VARCHAR(20) DEFAULT 'pendente', -- 'pendente', 'conciliado', 'rejeitado', 'duvida'
    confianca_conciliacao DECIMAL(5,2),             -- Nível de confiança (0-100)
    
    -- Critérios de Match
    match_valor BIT DEFAULT 0,                      -- Se o valor corresponde
    match_contrapartida BIT DEFAULT 0,             -- Se a contrapartida corresponde
    match_data BIT DEFAULT 0,                       -- Se a data corresponde
    match_descricao BIT DEFAULT 0,                  -- Se a descrição corresponde
    
    -- Validação
    validado_por VARCHAR(100),                      -- Usuário que validou
    data_validacao DATETIME,
    observacoes_validacao TEXT,
    
    -- Metadados
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_movimentacao (id_movimentacao_bancaria),
    INDEX idx_processo (processo_referencia),
    INDEX idx_categoria (categoria_processo),
    INDEX idx_nivel_vinculo (nivel_vinculo, categoria_processo),
    INDEX idx_status (status_conciliacao),
    INDEX idx_data_validacao (data_validacao)
);
```

### 22. RASTREAMENTO_RECURSO

**Descrição:** Rastreamento completo da origem dos recursos para cada processo.

**⚠️ CRÍTICO PARA COMPLIANCE:** Esta tabela é fundamental para responder intimações da Receita Federal sobre origem dos recursos. Deve conter **identificação completa** de quem forneceu o recurso (CPF/CNPJ, nome, endereço, banco, conta) e **documentação comprobatória** (comprovantes, validações).

**Contexto legal:**
- Interposição fraudulenta é crime fiscal grave
- Receita Federal pode intimar sobre origem de recursos
- Documentação completa e rastreável é obrigatória
- Ver `docs/RASTREAMENTO_ORIGEM_RECURSOS_COMEX.md` para detalhes completos

```sql
CREATE TABLE [dbo].[RASTREAMENTO_RECURSO] (
    -- Identificação
    id_rastreamento BIGINT IDENTITY(1,1) PRIMARY KEY,
    processo_referencia VARCHAR(50) NOT NULL,      -- FK para PROCESSO_IMPORTACAO
    
    -- Origem do Recurso
    origem_recurso VARCHAR(50) NOT NULL,           -- Ex: "CLIENTE", "FORNECEDOR", "BANCO", "PROPRIO"
    origem_recurso_descricao VARCHAR(255),          -- Descrição detalhada
    
    -- ⚠️ IDENTIFICAÇÃO COMPLETA DA ORIGEM (CRÍTICO PARA COMPLIANCE)
    cpf_cnpj_origem VARCHAR(18),                    -- CPF/CNPJ de quem forneceu o recurso (OBRIGATÓRIO)
    nome_origem VARCHAR(255),                       -- Nome completo de quem forneceu o recurso (OBRIGATÓRIO)
    endereco_origem TEXT,                           -- Endereço completo (OBRIGATÓRIO)
    banco_origem VARCHAR(50),                      -- Banco de origem do recurso
    agencia_origem VARCHAR(20),                     -- Agência de origem
    conta_origem VARCHAR(50),                       -- Conta de origem
    documento_comprovante VARCHAR(255),             -- Número do documento comprovante (TED, DOC, PIX, etc.)
    
    -- Tipo de Recurso
    tipo_recurso VARCHAR(50),                       -- Ex: "PAGAMENTO_FOB", "PAGAMENTO_FRETE", "PAGAMENTO_IMPOSTO", "ADVANCIA", "FINANCIAMENTO"
    
    -- Valores
    valor_recurso_usd DECIMAL(18,2),
    valor_recurso_brl DECIMAL(18,2),
    moeda VARCHAR(3) DEFAULT 'USD',
    taxa_cambio DECIMAL(10,6),
    
    -- Vínculo com Movimentação
    id_movimentacao_bancaria BIGINT,                -- FK opcional para MOVIMENTACAO_BANCARIA
    id_despesa_processo BIGINT,                    -- FK opcional para DESPESA_PROCESSO
    
    -- Datas
    data_origem DATETIME,                         -- Data de origem do recurso
    data_aplicacao DATETIME,                       -- Data de aplicação no processo
    
    -- Status
    status_rastreamento VARCHAR(20) DEFAULT 'ativo', -- 'ativo', 'finalizado', 'cancelado'
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Validação
    origem_validada BIT DEFAULT 0,                  -- Se a origem foi validada (CPF/CNPJ, nome, etc.)
    data_validacao_origem DATETIME,                 -- Data da validação
    fonte_validacao VARCHAR(50),                    -- Fonte da validação (ex: "RECEITAWS", "SERPRO", "MANUAL")
    
    -- Índices
    INDEX idx_processo (processo_referencia),
    INDEX idx_origem (origem_recurso),
    INDEX idx_tipo (tipo_recurso),
    INDEX idx_data_aplicacao (data_aplicacao),
    INDEX idx_cpf_cnpj_origem (cpf_cnpj_origem),
    INDEX idx_origem_validada (origem_validada, data_validacao_origem)
);
```

---

## ✅ Tabelas de Validação e Verificação

### 23. VALIDACAO_DADOS_OFICIAIS

**Descrição:** Validação automática de dados armazenados com APIs oficiais.

```sql
CREATE TABLE [dbo].[VALIDACAO_DADOS_OFICIAIS] (
    -- Identificação
    id_validacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Entidade Validada
    tipo_entidade VARCHAR(50) NOT NULL,             -- Ex: "PROCESSO", "DI", "DUIMP", "CE", "CCT"
    id_entidade VARCHAR(100) NOT NULL,              -- ID da entidade (ex: processo_referencia, numero_di)
    
    -- API Oficial
    api_oficial VARCHAR(50) NOT NULL,               -- Ex: "PORTAL_UNICO", "INTEGRACOMEX", "SERPRO"
    endpoint_consulta VARCHAR(500),                 -- Endpoint usado para consulta
    data_consulta DATETIME DEFAULT GETDATE(),
    
    -- Comparação
    campo_validado VARCHAR(100) NOT NULL,           -- Ex: "status_documento", "valor_fob", "data_desembaraco"
    valor_armazenado VARCHAR(500),                  -- Valor que está armazenado
    valor_oficial VARCHAR(500),                     -- Valor retornado pela API oficial
    valores_iguais BIT,                              -- Se os valores são iguais
    diferenca_valor VARCHAR(500),                   -- Diferença entre valores (se houver)
    
    -- Status
    status_validacao VARCHAR(20) DEFAULT 'pendente', -- 'pendente', 'validado', 'divergencia', 'erro'
    acao_tomada VARCHAR(100),                       -- Ex: "ATUALIZADO", "MANTIDO", "REQUER_ATENCAO"
    
    -- Detalhes
    observacoes TEXT,
    json_resposta_oficial NVARCHAR(MAX),            -- Resposta completa da API oficial
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_entidade (tipo_entidade, id_entidade),
    INDEX idx_api_oficial (api_oficial, data_consulta DESC),
    INDEX idx_status (status_validacao),
    INDEX idx_campo (campo_validado)
);
```

### 24. VERIFICACAO_AUTOMATICA

**Descrição:** Agendamento e histórico de verificações automáticas.

```sql
CREATE TABLE [dbo].[VERIFICACAO_AUTOMATICA] (
    -- Identificação
    id_verificacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Configuração
    tipo_verificacao VARCHAR(50) NOT NULL,          -- Ex: "DI_STATUS", "DUIMP_STATUS", "CE_STATUS", "VALORES_DI", "VALORES_DUIMP"
    entidade_tipo VARCHAR(50) NOT NULL,             -- Ex: "PROCESSO", "DI", "DUIMP"
    filtro_entidades NVARCHAR(MAX),                 -- JSON com filtros (ex: {"status": "em_analise", "data_ultima_verificacao": "> 7 dias"})
    
    -- Agendamento
    frequencia_verificacao VARCHAR(50),             -- Ex: "DIARIA", "SEMANAL", "MENSAL", "PERSONALIZADA"
    proxima_execucao DATETIME,
    ultima_execucao DATETIME,
    
    -- Resultados
    total_entidades_verificadas INT DEFAULT 0,
    total_divergencias_encontradas INT DEFAULT 0,
    total_atualizacoes_realizadas INT DEFAULT 0,
    total_erros INT DEFAULT 0,
    
    -- Status
    status_verificacao VARCHAR(20) DEFAULT 'ativa', -- 'ativa', 'pausada', 'finalizada'
    ultima_execucao_status VARCHAR(20),             -- 'sucesso', 'erro', 'parcial'
    mensagem_erro TEXT,
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_tipo_verificacao (tipo_verificacao),
    INDEX idx_proxima_execucao (proxima_execucao),
    INDEX idx_status (status_verificacao)
);
```

---

## 📊 Tabelas de Auditoria e Logs

### 25. LOG_SINCRONIZACAO

**Descrição:** Logs de sincronização de dados.

```sql
CREATE TABLE [auditoria].[LOG_SINCRONIZACAO] (
    -- Identificação
    id_log BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Sincronização
    fonte_dados VARCHAR(50) NOT NULL,              -- Ex: "KANBAN_API", "BB_API", "SANTANDER"
    tipo_sincronizacao VARCHAR(50),                 -- Ex: "FULL", "INCREMENTAL"
    
    -- Execução
    data_inicio DATETIME NOT NULL,
    data_fim DATETIME,
    status VARCHAR(20) DEFAULT 'em_andamento',      -- 'em_andamento', 'sucesso', 'erro'
    tempo_execucao_segundos INT,
    
    -- Resultados
    registros_processados INT DEFAULT 0,
    registros_inseridos INT DEFAULT 0,
    registros_atualizados INT DEFAULT 0,
    registros_com_erro INT DEFAULT 0,
    
    -- Erro
    mensagem_erro TEXT,
    stack_trace TEXT,
    
    -- Metadados
    observacoes TEXT,
    criado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_fonte_dados (fonte_dados, data_inicio DESC),
    INDEX idx_status (status),
    INDEX idx_data_inicio (data_inicio DESC)
);
```

### 26. LOG_CONSULTA_API

**Descrição:** Logs de consultas a APIs externas.

```sql
CREATE TABLE [auditoria].[LOG_CONSULTA_API] (
    -- Identificação
    id_log BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- API
    api_nome VARCHAR(50) NOT NULL,                  -- Ex: "PORTAL_UNICO", "INTEGRACOMEX", "BB_API"
    endpoint VARCHAR(500) NOT NULL,
    metodo VARCHAR(10) DEFAULT 'GET',
    
    -- Requisição
    parametros_requisicao NVARCHAR(MAX),            -- JSON com parâmetros
    headers_requisicao NVARCHAR(MAX),               -- JSON com headers
    
    -- Resposta
    status_code INT,
    tempo_resposta_ms INT,
    tamanho_resposta_bytes INT,
    sucesso BIT DEFAULT 1,
    
    -- Erro
    mensagem_erro TEXT,
    
    -- Vínculo
    processo_referencia VARCHAR(50),
    session_id VARCHAR(100),
    
    -- Timestamps
    data_consulta DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_api_nome (api_nome, data_consulta DESC),
    INDEX idx_status_code (status_code),
    INDEX idx_processo (processo_referencia),
    INDEX idx_data_consulta (data_consulta DESC)
);
```

### 27. LOG_ERRO

**Descrição:** Logs de erros do sistema.

```sql
CREATE TABLE [auditoria].[LOG_ERRO] (
    -- Identificação
    id_log BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Erro
    nivel VARCHAR(20) NOT NULL,                      -- 'ERROR', 'WARNING', 'CRITICAL'
    mensagem_erro TEXT NOT NULL,
    stack_trace TEXT,
    tipo_erro VARCHAR(100),                          -- Tipo da exceção (ex: "ValueError", "ConnectionError")
    
    -- Contexto
    modulo_origem VARCHAR(255),                     -- Módulo onde ocorreu o erro
    funcao_origem VARCHAR(255),                      -- Função onde ocorreu o erro
    linha_erro INT,
    
    -- Vínculo
    processo_referencia VARCHAR(50),
    session_id VARCHAR(100),
    api_nome VARCHAR(50),
    
    -- Timestamps
    data_erro DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_nivel (nivel, data_erro DESC),
    INDEX idx_tipo_erro (tipo_erro),
    INDEX idx_processo (processo_referencia),
    INDEX idx_data_erro (data_erro DESC)
);
```

---

## ⚡ Índices e Performance

### Índices Estratégicos

```sql
-- Índices compostos para consultas frequentes
CREATE INDEX idx_processo_categoria_status 
ON PROCESSO_IMPORTACAO(categoria_processo, status_atual, data_chegada);

CREATE INDEX idx_documento_tipo_status 
ON DOCUMENTO_ADUANEIRO(tipo_documento, status_documento, data_desembaraco);

CREATE INDEX idx_movimentacao_banco_data 
ON MOVIMENTACAO_BANCARIA(banco_origem, data_movimentacao DESC, sinal_movimentacao);

CREATE INDEX idx_conversa_session_tipo 
ON CONVERSA_CHAT(session_id, tipo_conversa, criado_em DESC);

-- Índices para full-text search (futuro)
CREATE FULLTEXT INDEX ON PROCESSO_IMPORTACAO(observacoes);
CREATE FULLTEXT INDEX ON DOCUMENTO_ADUANEIRO(descricao_mercadoria);
CREATE FULLTEXT INDEX ON CONVERSA_CHAT(mensagem_usuario, resposta_ia);
```

### Views Materializadas (Futuro)

```sql
-- View consolidada de processos com todos os dados
CREATE VIEW vw_processo_consolidado AS
SELECT 
    p.*,
    d.numero_documento as documento_principal,
    d.tipo_documento as tipo_documento_principal,
    d.status_documento as status_documento_principal,
    f.razao_social as fornecedor_nome,
    c.razao_social as cliente_nome
FROM PROCESSO_IMPORTACAO p
LEFT JOIN DOCUMENTO_ADUANEIRO d ON p.processo_referencia = d.processo_referencia
LEFT JOIN FORNECEDOR_CLIENTE f ON p.fornecedor_cnpj = f.cpf_cnpj
LEFT JOIN FORNECEDOR_CLIENTE c ON p.cliente_cnpj = c.cpf_cnpj;

-- View de financeiro consolidado
CREATE VIEW vw_financeiro_consolidado AS
SELECT 
    p.processo_referencia,
    p.valor_fob_usd,
    p.valor_frete_usd,
    p.valor_seguro_usd,
    p.valor_cif_usd,
    d.total_impostos_usd,
    SUM(m.valor_movimentacao) as total_pagamentos_brl
FROM PROCESSO_IMPORTACAO p
LEFT JOIN DOCUMENTO_ADUANEIRO d ON p.processo_referencia = d.processo_referencia
LEFT JOIN MOVIMENTACAO_BANCARIA m ON p.processo_referencia = m.processo_referencia
WHERE m.sinal_movimentacao = 'D'
GROUP BY p.processo_referencia, p.valor_fob_usd, p.valor_frete_usd, 
         p.valor_seguro_usd, p.valor_cif_usd, d.total_impostos_usd;

-- View de despesas por processo
CREATE VIEW vw_despesas_processo AS
SELECT 
    p.processo_referencia,
    dp.tipo_despesa,
    dp.tipo_despesa_descricao,
    dp.valor_previsto_usd,
    dp.valor_realizado_usd,
    dp.status_despesa,
    dp.data_real_pagamento,
    dp.conciliado,
    cb.id_conciliacao,
    cb.status_conciliacao
FROM PROCESSO_IMPORTACAO p
INNER JOIN DESPESA_PROCESSO dp ON p.processo_referencia = dp.processo_referencia
LEFT JOIN CONCILIACAO_BANCARIA cb ON dp.id_despesa = cb.id_despesa_processo;

-- View de rastreamento de recursos por processo
CREATE VIEW vw_rastreamento_recursos_processo AS
SELECT 
    p.processo_referencia,
    rr.origem_recurso,
    rr.tipo_recurso,
    rr.valor_recurso_usd,
    rr.valor_recurso_brl,
    rr.data_aplicacao,
    m.banco_origem,
    m.data_movimentacao,
    m.descricao_movimentacao
FROM PROCESSO_IMPORTACAO p
INNER JOIN RASTREAMENTO_RECURSO rr ON p.processo_referencia = rr.processo_referencia
LEFT JOIN MOVIMENTACAO_BANCARIA m ON rr.id_movimentacao_bancaria = m.id_movimentacao;

-- View de validações pendentes
CREATE VIEW vw_validacoes_pendentes AS
SELECT 
    vdo.tipo_entidade,
    vdo.id_entidade,
    vdo.api_oficial,
    vdo.campo_validado,
    vdo.valor_armazenado,
    vdo.valor_oficial,
    vdo.status_validacao,
    vdo.data_consulta,
    COUNT(*) as total_divergencias
FROM VALIDACAO_DADOS_OFICIAIS vdo
WHERE vdo.status_validacao IN ('pendente', 'divergencia')
GROUP BY vdo.tipo_entidade, vdo.id_entidade, vdo.api_oficial, 
         vdo.campo_validado, vdo.valor_armazenado, vdo.valor_oficial, 
         vdo.status_validacao, vdo.data_consulta;
```

---

## 🔄 Estratégia de Migração

### Fase 1: Estrutura Base (Semana 1)
1. Criar banco `mAIke_assistente`
2. Criar schemas (`dbo`, `comunicacao`, `ia`, `legislacao`, `auditoria`)
3. Criar tabelas principais:
   - `PROCESSO_IMPORTACAO`
   - `DOCUMENTO_ADUANEIRO`
   - `FORNECEDOR_CLIENTE`
   - `MOVIMENTACAO_BANCARIA`
   - `TIMELINE_PROCESSO`

### Fase 2: Integrações (Semana 2)
4. Criar tabelas de integração:
   - `SHIPSGO_TRACKING`
   - `CONSULTA_BILHETADA`
   - `CONSULTA_BILHETADA_PENDENTE`
5. Implementar DTOs de conversão
6. Criar serviço de sincronização

### Fase 2.5: Despesas e Financeiro (Semana 2.5)
7. Criar tabelas de despesas e financeiro:
   - `DESPESA_PROCESSO`
   - `CONCILIACAO_BANCARIA`
   - `RASTREAMENTO_RECURSO`
8. Implementar lógica de conciliação automática
9. Criar serviço de rastreamento de recursos

### Fase 2.6: Validação e Verificação (Semana 2.6)
10. Criar tabelas de validação:
    - `VALIDACAO_DADOS_OFICIAIS`
    - `VERIFICACAO_AUTOMATICA`
11. Implementar lógica de validação automática
12. Criar serviço de verificação periódica

### Fase 3: Comunicação (Semana 3)
13. Criar tabelas de comunicação:
   - `EMAIL_ENVIADO`
   - `EMAIL_AGENDADO`
   - `WHATSAPP_MENSAGEM`
8. Migrar dados de email do SQLite

### Fase 4: IA e Aprendizado (Semana 4)
14. Criar tabelas de IA:
   - `CONVERSA_CHAT`
   - `REGRA_APRENDIDA`
   - `CONTEXTO_SESSAO`
   - `CONSULTA_SALVA`
10. Migrar dados do SQLite

### Fase 5: Vetorização (Semana 5)
15. Criar tabelas de legislação:
    - `LEGISLACAO_IMPORTADA`
    - `LEGISLACAO_VETORIZACAO`
    - `LEGISLACAO_CHUNK`
12. Migrar legislações existentes

### Fase 6: Auditoria (Semana 6)
16. Criar tabelas de auditoria:
    - `LOG_SINCRONIZACAO`
    - `LOG_CONSULTA_API`
    - `LOG_ERRO`
14. Implementar logging

### Fase 7: Otimização (Semana 7)
17. Criar índices estratégicos
16. Criar views materializadas
17. Otimizar queries
18. Testes de performance

---

## 📦 DTOs e Normalização

### Exemplo: ProcessoImportacaoDTO

```python
@dataclass
class ProcessoImportacaoDTO:
    # Identificação
    processo_referencia: str
    categoria_processo: str
    
    # Status
    status_atual: str
    status_anterior: str
    
    # Datas
    data_criacao_processo: Optional[datetime]
    data_ultima_atualizacao: Optional[datetime]
    data_chegada: Optional[datetime]
    data_eta: Optional[datetime]
    
    # Origem
    fonte_dados: str
    ultima_sincronizacao: datetime
    json_dados_originais: Optional[dict]
    
    # Métodos de conversão
    @classmethod
    def from_kanban_api(cls, data: dict) -> 'ProcessoImportacaoDTO':
        """Converte dados da API Kanban para DTO."""
        return cls(
            processo_referencia=data.get('processo_referencia'),
            categoria_processo=data.get('categoria'),
            status_atual=data.get('status'),
            # ... mapear todos os campos
            fonte_dados='KANBAN_API',
            ultima_sincronizacao=datetime.now(),
            json_dados_originais=data
        )
    
    @classmethod
    def from_sql_server(cls, data: dict) -> 'ProcessoImportacaoDTO':
        """Converte dados do SQL Server para DTO."""
        # ... mapeamento específico do SQL Server
    
    @classmethod
    def from_shipsgo(cls, data: dict) -> 'ProcessoImportacaoDTO':
        """Converte dados do ShipsGo para DTO."""
        # ... mapeamento específico do ShipsGo
    
    def to_dict(self) -> dict:
        """Converte DTO para dict (para salvar no BD)."""
        return {
            'processo_referencia': self.processo_referencia,
            'categoria_processo': self.categoria_processo,
            # ... todos os campos
        }
```

---

## ✅ Checklist de Implementação

- [ ] Criar banco `mAIke_assistente`
- [ ] Criar schemas
- [ ] Criar tabelas principais
- [ ] Criar tabelas de integração
- [ ] Criar tabelas de despesas e financeiro
- [ ] Criar tabelas de validação e verificação
- [ ] Criar tabelas de comunicação
- [ ] Criar tabelas de IA
- [ ] Criar tabelas de vetorização
- [ ] Criar tabelas de auditoria
- [ ] Criar índices
- [ ] Criar views materializadas
- [ ] Implementar DTOs
- [ ] Criar serviço de sincronização
- [ ] Criar serviço de conciliação bancária
- [ ] Criar serviço de validação automática
- [ ] Migrar dados do SQLite
- [ ] Testes de performance
- [ ] Documentação final

---

## 🎯 Funcionalidades Especiais - mAIke Assistente COMEX

### 💰 Rastreamento Completo de Recursos

**Objetivo:** Saber toda a origem dos recursos para cada processo (ex: ALH.0001/25).

**Como funciona:**
1. **Despesas Previstas**: Sistema registra todas as despesas previstas do processo (frete, seguro, impostos, etc.)
2. **Despesas Realizadas**: Quando há pagamento, sistema registra despesa realizada
3. **Conciliação Automática**: Sistema tenta conciliar automaticamente movimentações bancárias com despesas
4. **Rastreamento de Origem**: Sistema rastreia de onde veio cada recurso aplicado no processo

**Exemplo de uso:**
```
Usuário: "mostre a origem dos recursos do ALH.0001/25"
mAIke: 
📊 ORIGEM DOS RECURSOS - ALH.0001/25

💰 DESPESAS PREVISTAS:
  • Frete: USD 1,500.00 (previsto)
  • Seguro: USD 200.00 (previsto)
  • II: USD 2,000.00 (previsto)
  • IPI: USD 500.00 (previsto)

💳 DESPESAS REALIZADAS:
  • Frete: USD 1,500.00 ✅ PAGO (BB - 15/01/2026)
  • Seguro: USD 200.00 ✅ PAGO (Santander - 16/01/2026)
  • II: USD 2,000.00 ⚠️ PENDENTE

🔗 CONCILIAÇÃO:
  • 2 de 3 despesas conciliadas
  • 1 pendência de conciliação

📈 ORIGEM DOS RECURSOS:
  • Cliente: USD 10,000.00 (FOB) - Recebido em 10/01/2026
  • Banco: USD 3,700.00 (Financiamento) - Recebido em 12/01/2026
```

### ✅ Validação Automática com APIs Oficiais

**Objetivo:** Verificar que o que está armazenado está correto, já que as fontes são oficiais.

**Como funciona:**
1. **Consulta Automática**: Sistema consulta APIs oficiais (Portal Único, Integra Comex, Serpro)
2. **Comparação**: Compara valores armazenados com valores oficiais
3. **Detecção de Divergências**: Identifica quando há diferenças
4. **Atualização Automática**: Atualiza dados quando há divergência (ou solicita confirmação)

**Exemplo de uso:**
```
Usuário: "verificar se os dados da DI 2527284816 estão corretos"
mAIke: 
✅ VALIDAÇÃO DE DADOS OFICIAIS - DI 2527284816

🔍 Verificando com Integra Comex...
  • Status: ✅ CORRETO (armazenado: "DI_DESEMBARACADA" = oficial: "DI_DESEMBARACADA")
  • Valor FOB: ✅ CORRETO (armazenado: USD 10,000.00 = oficial: USD 10,000.00)
  • Data Desembaraço: ⚠️ DIVERGÊNCIA (armazenado: 15/01/2026 ≠ oficial: 16/01/2026)
  • Valor Frete: ✅ CORRETO (armazenado: USD 1,500.00 = oficial: USD 1,500.00)

📝 AÇÕES TOMADAS:
  • Data de desembaraço atualizada automaticamente para 16/01/2026
  • Validação registrada em VALIDACAO_DADOS_OFICIAIS
```

**Verificações Automáticas:**
- **DI**: Status, valores (FOB, frete, seguro), data de desembaraço, impostos
- **DUIMP**: Status, valores, canal, data de desembaraço
- **CE**: Status, ETA, porto, valores
- **CCT**: Status, valores, data de chegada

**Agendamento:**
- Verificações diárias para DIs/DUIMPs em análise
- Verificações semanais para processos ativos
- Verificações mensais para processos históricos

### 🔄 Conciliação Bancária Inteligente

**Objetivo:** Vincular automaticamente pagamentos bancários com despesas de processo.

**Como funciona:**
1. **Match por Valor**: Tenta encontrar despesa com valor correspondente
2. **Match por Contrapartida**: Verifica se CNPJ/CPF da contrapartida corresponde ao fornecedor
3. **Match por Data**: Verifica se data do pagamento está próxima da data prevista
4. **Match por Descrição**: Analisa descrição da movimentação para identificar tipo de despesa
5. **Sugestões**: Apresenta sugestões de conciliação para validação manual quando necessário

**Exemplo de uso:**
```
Usuário: "conciliar pagamentos do ALH.0001/25"
mAIke: 
🔄 CONCILIAÇÃO BANCÁRIA - ALH.0001/25

✅ CONCILIADAS AUTOMATICAMENTE:
  • Frete: USD 1,500.00 → Pagamento BB (15/01/2026) - Confiança: 95%
  • Seguro: USD 200.00 → Pagamento Santander (16/01/2026) - Confiança: 90%

⚠️ SUGESTÕES DE CONCILIAÇÃO:
  • Pagamento BB (20/01/2026) - R$ 11,000.00 → Possível: II (USD 2,000.00)
    - Valor corresponde: ✅
    - Contrapartida corresponde: ✅
    - Data próxima: ✅
    - Confiança: 85%
    - [Confirmar] [Rejeitar] [Marcar como dúvida]

📊 RESUMO:
  • 2 despesas conciliadas automaticamente
  • 1 sugestão aguardando confirmação
  • 0 despesas sem correspondência
```

### 📊 Dashboard Financeiro por Processo

**Objetivo:** Visão completa financeira de cada processo.

**Exemplo de uso:**
```
Usuário: "dashboard financeiro ALH.0001/25"
mAIke: 
📊 DASHBOARD FINANCEIRO - ALH.0001/25

💰 VALORES PREVISTOS:
  • FOB: USD 10,000.00
  • Frete: USD 1,500.00
  • Seguro: USD 200.00
  • CIF: USD 11,700.00
  • Impostos: USD 3,000.00
  • Total Previsto: USD 14,700.00

💳 VALORES REALIZADOS:
  • FOB: USD 10,000.00 ✅ RECEBIDO
  • Frete: USD 1,500.00 ✅ PAGO
  • Seguro: USD 200.00 ✅ PAGO
  • Impostos: USD 2,000.00 ⚠️ PARCIAL (faltam USD 1,000.00)
  • Total Realizado: USD 13,700.00

📈 ORIGEM DOS RECURSOS:
  • Cliente: USD 10,000.00 (70%)
  • Banco: USD 3,700.00 (30%)

🔗 CONCILIAÇÃO:
  • 3 de 4 despesas conciliadas
  • 1 pendência de conciliação

⏰ PRÓXIMOS PAGAMENTOS:
  • II (restante): USD 1,000.00 - Previsto: 25/01/2026
```

---

**Última atualização:** 08/01/2026  
**Versão:** 1.4

**Mudanças v1.2:**
- ✅ Adicionada tabela `MOVIMENTACAO_BANCARIA_PROCESSO` para relacionamento N:N
- ✅ Permite dividir um lançamento bancário entre vários processos
- ✅ Cada processo tem seu valor específico (parcela)
- ✅ Exemplo: Armazenagem R$ 10.000 dividida em ALH.0001 (R$ 3.000), BGR.0005 (R$ 2.000), DMD.0050 (R$ 5.000)

