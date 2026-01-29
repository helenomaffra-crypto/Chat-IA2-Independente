# 🏦 Integração de Extratos Bancários no Banco mAIke_assistente

**Data:** 07/01/2026  
**Objetivo:** Alimentar extratos bancários no novo banco SQL Server e evitar duplicatas

---

## 📋 Visão Geral

### Situação Atual

- ✅ **API Banco do Brasil:** Integrada e funcionando (`utils/banco_brasil_api.py`, `services/banco_brasil_service.py`)
- ✅ **Consulta de extratos:** Funcional (últimos 30 dias por padrão)
- ❌ **Armazenamento:** Não há persistência no banco de dados (apenas consulta em tempo real)
- ❌ **Detecção de duplicatas:** Não implementada

### Objetivo da Integração

1. **Armazenar lançamentos bancários** no SQL Server (`MOVIMENTACAO_BANCARIA`)
2. **Evitar duplicatas** ao importar extratos no dia seguinte
3. **Rastrear origem dos recursos** (compliance COAF/Receita Federal)
4. **Vincular lançamentos a processos** de importação

---

## 🗄️ Estrutura da Tabela `MOVIMENTACAO_BANCARIA`

### Campos Principais

```sql
CREATE TABLE [dbo].[MOVIMENTACAO_BANCARIA] (
    id_movimentacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Origem
    banco_origem VARCHAR(50) NOT NULL,
    agencia_origem VARCHAR(20),
    conta_origem VARCHAR(50),
    tipo_conta_origem VARCHAR(20),
    
    -- Dados da Movimentação
    data_movimentacao DATETIME NOT NULL,
    data_lancamento DATETIME,
    tipo_movimentacao VARCHAR(50),
    sinal_movimentacao VARCHAR(1) NOT NULL,  -- 'C' (crédito) ou 'D' (débito)
    valor_movimentacao DECIMAL(18,2) NOT NULL,
    moeda VARCHAR(3) DEFAULT 'BRL',
    
    -- Contrapartida (CRÍTICO PARA COMPLIANCE)
    cpf_cnpj_contrapartida VARCHAR(18),
    nome_contrapartida VARCHAR(255),
    tipo_pessoa_contrapartida VARCHAR(20),
    banco_contrapartida VARCHAR(50),
    agencia_contrapartida VARCHAR(20),
    conta_contrapartida VARCHAR(50),
    
    -- Validação da Contrapartida (CRÍTICO)
    contrapartida_validada BIT DEFAULT 0,
    data_validacao_contrapartida DATETIME,
    fonte_validacao_contrapartida VARCHAR(50),
    nome_validado_contrapartida VARCHAR(255),
    
    -- Descrição
    descricao_movimentacao TEXT,
    historico_codigo VARCHAR(20),
    historico_descricao VARCHAR(255),
    informacoes_complementares TEXT,
    
    -- Relacionamento com Processo
    processo_referencia VARCHAR(50),
    tipo_relacionamento VARCHAR(50),
    
    -- Controle de Duplicatas (CRÍTICO)
    fonte_dados VARCHAR(50),  -- 'BB_API', 'MANUAL', 'IMPORTACAO_PDF', etc.
    ultima_sincronizacao DATETIME,
    versao_dados INT DEFAULT 1,
    hash_dados VARCHAR(64),  -- ✅ CHAVE PARA DETECTAR DUPLICATAS
    json_dados_originais NVARCHAR(MAX),
    
    -- Auditoria
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE()
);
```

### Índices para Performance

```sql
CREATE INDEX idx_banco_origem ON MOVIMENTACAO_BANCARIA(banco_origem, data_movimentacao);
CREATE INDEX idx_data_movimentacao ON MOVIMENTACAO_BANCARIA(data_movimentacao);
CREATE INDEX idx_hash_dados ON MOVIMENTACAO_BANCARIA(hash_dados);  -- ✅ CRÍTICO PARA DUPLICATAS
CREATE INDEX idx_fonte_dados ON MOVIMENTACAO_BANCARIA(fonte_dados, ultima_sincronizacao);
```

---

## 🔑 Estratégia de Detecção de Duplicatas

### Problema

**Cenário:**
- Dia 1: Importar extrato de 01/01 a 07/01 → 50 lançamentos
- Dia 2: Importar extrato de 01/01 a 08/01 → 51 lançamentos (50 antigos + 1 novo)

**Pergunta:** Como saber se o lançamento já foi importado?

### Solução: Hash Único por Lançamento

Cada lançamento bancário terá um **hash único** calculado a partir de:

1. **Banco + Agência + Conta** (origem)
2. **Data do lançamento** (data_lancamento)
3. **Valor** (valor_movimentacao)
4. **Tipo/Sinal** (sinal_movimentacao: C ou D)
5. **Descrição** (descricao_movimentacao)

**Algoritmo:**

```python
import hashlib
import json

def gerar_hash_lancamento(lancamento: Dict[str, Any]) -> str:
    """
    Gera hash único para um lançamento bancário.
    
    Args:
        lancamento: Dict com dados do lançamento da API do BB
    
    Returns:
        Hash SHA-256 (64 caracteres hex)
    """
    # Campos críticos para identificar lançamento único
    dados_hash = {
        'banco': 'BB',  # Fixo para Banco do Brasil
        'agencia': lancamento.get('agencia', ''),
        'conta': lancamento.get('conta', ''),
        'data_lancamento': lancamento.get('dataLancamento', 0),  # Formato AAAAMMDD
        'valor': lancamento.get('valorLancamento', 0.0),
        'tipo': lancamento.get('tipoLancamento', ''),
        'indicador': lancamento.get('indicadorLancamento', ''),  # 'C' ou 'D'
        'descricao': lancamento.get('textoDescricaoLancamento', '')[:100]  # Primeiros 100 chars
    }
    
    # Serializar de forma determinística (sempre mesma ordem)
    dados_json = json.dumps(dados_hash, sort_keys=True, ensure_ascii=False)
    
    # Calcular SHA-256
    hash_obj = hashlib.sha256(dados_json.encode('utf-8'))
    return hash_obj.hexdigest()
```

### Fluxo de Importação com Detecção de Duplicatas

```python
def importar_lancamentos_bb(lancamentos: List[Dict], agencia: str, conta: str):
    """
    Importa lançamentos do Banco do Brasil evitando duplicatas.
    
    Args:
        lancamentos: Lista de lançamentos da API do BB
        agencia: Agência da conta
        conta: Número da conta
    """
    from utils.sql_server_adapter import get_sql_adapter
    adapter = get_sql_adapter()
    
    novos = 0
    duplicados = 0
    erros = 0
    
    for lanc in lancamentos:
        try:
            # 1. Gerar hash do lançamento
            hash_lanc = gerar_hash_lancamento({
                'agencia': agencia,
                'conta': conta,
                **lanc
            })
            
            # 2. Verificar se já existe (busca por hash)
            query_check = """
                SELECT id_movimentacao 
                FROM MOVIMENTACAO_BANCARIA 
                WHERE hash_dados = ?
            """
            resultado = adapter.execute_query(query_check, (hash_lanc,))
            
            if resultado and len(resultado) > 0:
                # ✅ Lançamento já existe - pular
                duplicados += 1
                logger.debug(f"⏭️ Lançamento duplicado (hash: {hash_lanc[:8]}...)")
                continue
            
            # 3. Inserir novo lançamento
            query_insert = """
                INSERT INTO MOVIMENTACAO_BANCARIA (
                    banco_origem, agencia_origem, conta_origem,
                    data_movimentacao, data_lancamento,
                    tipo_movimentacao, sinal_movimentacao,
                    valor_movimentacao, moeda,
                    descricao_movimentacao, historico_codigo,
                    fonte_dados, hash_dados, json_dados_originais,
                    criado_em, atualizado_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
            """
            
            # Extrair dados do lançamento
            data_lanc = _converter_data_bb(lanc.get('dataLancamento', 0))
            valor = lanc.get('valorLancamento', 0.0)
            sinal = lanc.get('indicadorLancamento', 'C')  # 'C' ou 'D'
            descricao = lanc.get('textoDescricaoLancamento', '')
            tipo = lanc.get('tipoLancamento', '')
            historico = lanc.get('codigoHistoricoBanco', '')
            
            params = (
                'BB',  # banco_origem
                agencia,
                conta,
                data_lanc,  # data_movimentacao
                data_lanc,  # data_lancamento
                tipo,
                sinal,
                valor,
                'BRL',
                descricao,
                historico,
                'BB_API',  # fonte_dados
                hash_lanc,
                json.dumps(lanc, ensure_ascii=False)  # json_dados_originais
            )
            
            adapter.execute_non_query(query_insert, params)
            novos += 1
            logger.info(f"✅ Novo lançamento importado: {descricao[:50]}... (R$ {valor})")
            
        except Exception as e:
            erros += 1
            logger.error(f"❌ Erro ao importar lançamento: {e}", exc_info=True)
    
    logger.info(f"📊 Importação concluída: {novos} novos, {duplicados} duplicados, {erros} erros")
    return {
        'sucesso': True,
        'novos': novos,
        'duplicados': duplicados,
        'erros': erros
    }
```

---

## 🔄 Fluxo de Sincronização Diária

### Estratégia Recomendada

**Opção 1: Sincronização Automática (Recomendada)**

```python
# Executar diariamente às 06:00 (antes do expediente)
# Usar agendador (cron, Windows Task Scheduler, ou Celery)

def sincronizar_extratos_diario():
    """
    Sincroniza extratos bancários diariamente.
    Busca últimos 7 dias para garantir que não perca nenhum lançamento.
    """
    from datetime import datetime, timedelta
    from services.banco_brasil_service import BancoBrasilService
    
    bb_service = BancoBrasilService()
    
    # Buscar últimos 7 dias (margem de segurança)
    hoje = datetime.now()
    data_inicio = hoje - timedelta(days=7)
    
    # Contas a sincronizar (configurar no .env ou banco)
    contas = [
        {'agencia': '1251', 'conta': '50483'},  # Conta principal
        # Adicionar outras contas aqui
    ]
    
    for conta_info in contas:
        logger.info(f"🔄 Sincronizando conta {conta_info['agencia']}-{conta_info['conta']}")
        
        resultado = bb_service.consultar_extrato(
            agencia=conta_info['agencia'],
            conta=conta_info['conta'],
            data_inicio=data_inicio,
            data_fim=hoje
        )
        
        if resultado.get('sucesso'):
            lancamentos = resultado.get('dados', {}).get('lancamentos', [])
            importar_lancamentos_bb(lancamentos, conta_info['agencia'], conta_info['conta'])
        else:
            logger.error(f"❌ Erro ao consultar extrato: {resultado.get('erro')}")
```

**Opção 2: Sincronização Manual (Alternativa)**

```python
# Via endpoint da API Flask

@app.route('/api/banco/sincronizar', methods=['POST'])
def sincronizar_extratos():
    """
    Endpoint para sincronizar extratos manualmente.
    
    Body:
    {
        "agencia": "1251",
        "conta": "50483",
        "data_inicio": "2026-01-01",  # opcional
        "data_fim": "2026-01-07"      # opcional
    }
    """
    data = request.get_json()
    agencia = data.get('agencia')
    conta = data.get('conta')
    
    # ... implementar lógica de sincronização ...
    
    return jsonify({
        'sucesso': True,
        'novos': 10,
        'duplicados': 40,
        'mensagem': '✅ Sincronização concluída'
    })
```

---

## 🔗 Vinculação de Lançamentos a Processos

### Estratégia de Vinculação

**Problema:** Como saber que um lançamento bancário está relacionado a um processo de importação?

**Soluções:**

#### 1. Vinculação Manual (Imediata)

```python
def vincular_lancamento_processo(id_movimentacao: int, processo_referencia: str, tipo_relacionamento: str):
    """
    Vincula um lançamento bancário a um processo.
    
    Args:
        id_movimentacao: ID do lançamento na tabela MOVIMENTACAO_BANCARIA
        processo_referencia: Ex: 'DMD.0083/25'
        tipo_relacionamento: Ex: 'PAGAMENTO_FRETE', 'PAGAMENTO_IMPOSTOS', 'RECEBIMENTO_CLIENTE'
    """
    query = """
        UPDATE MOVIMENTACAO_BANCARIA
        SET processo_referencia = ?,
            tipo_relacionamento = ?,
            atualizado_em = GETDATE()
        WHERE id_movimentacao = ?
    """
    adapter.execute_non_query(query, (processo_referencia, tipo_relacionamento, id_movimentacao))
```

#### 2. Vinculação Automática por IA (Futura)

```python
def sugerir_vinculacao_ia(lancamento: Dict) -> Optional[str]:
    """
    Usa IA para sugerir vinculação de lançamento a processo.
    
    Analisa:
    - Descrição do lançamento
    - Valor (comparar com valores de frete/impostos de processos)
    - Data (processos próximos da data do lançamento)
    - CPF/CNPJ da contrapartida (fornecedores conhecidos)
    """
    # Implementar lógica de IA aqui
    pass
```

#### 3. Vinculação por Padrão de Descrição

```python
def detectar_processo_por_descricao(descricao: str) -> Optional[str]:
    """
    Detecta processo pela descrição do lançamento.
    
    Exemplos:
    - "PAG FRETE DMD 0083/25" → DMD.0083/25
    - "IMPOSTOS ALH.0168/25" → ALH.0168/25
    """
    import re
    
    # Padrão: 2-4 letras + ponto + 4 dígitos + barra + 2 dígitos
    match = re.search(r'\b([A-Z]{2,4})\.?(\d{4})/(\d{2})\b', descricao.upper())
    if match:
        categoria = match.group(1)
        numero = match.group(2)
        ano = match.group(3)
        return f"{categoria}.{numero}/{ano}"
    
    return None
```

---

## 📊 Relatórios e Consultas

### Consultas Úteis

#### 1. Lançamentos Não Vinculados

```sql
-- Lançamentos sem processo associado
SELECT 
    id_movimentacao,
    data_movimentacao,
    valor_movimentacao,
    sinal_movimentacao,
    descricao_movimentacao,
    nome_contrapartida
FROM MOVIMENTACAO_BANCARIA
WHERE processo_referencia IS NULL
ORDER BY data_movimentacao DESC;
```

#### 2. Movimentações por Processo

```sql
-- Total de movimentações por processo
SELECT 
    processo_referencia,
    COUNT(*) as total_lancamentos,
    SUM(CASE WHEN sinal_movimentacao = 'D' THEN valor_movimentacao ELSE 0 END) as total_debitos,
    SUM(CASE WHEN sinal_movimentacao = 'C' THEN valor_movimentacao ELSE 0 END) as total_creditos
FROM MOVIMENTACAO_BANCARIA
WHERE processo_referencia IS NOT NULL
GROUP BY processo_referencia
ORDER BY processo_referencia;
```

#### 3. Contrapartidas Não Validadas (COMPLIANCE)

```sql
-- Lançamentos com contrapartida não validada (CRÍTICO PARA COAF)
SELECT 
    id_movimentacao,
    data_movimentacao,
    valor_movimentacao,
    cpf_cnpj_contrapartida,
    nome_contrapartida,
    descricao_movimentacao
FROM MOVIMENTACAO_BANCARIA
WHERE cpf_cnpj_contrapartida IS NOT NULL
  AND contrapartida_validada = 0
ORDER BY data_movimentacao DESC;
```

---

## 🚀 Implementação Passo a Passo

### Fase 1: Estrutura Básica (Imediata)

1. ✅ Tabela `MOVIMENTACAO_BANCARIA` já criada (script SQL)
2. ✅ API Banco do Brasil já integrada
3. 🔲 Criar função `gerar_hash_lancamento()`
4. 🔲 Criar função `importar_lancamentos_bb()`
5. 🔲 Testar importação manual de 1 dia

### Fase 2: Sincronização Automática (Curto Prazo)

1. 🔲 Criar serviço de sincronização (`services/banco_sincronizacao_service.py`)
2. 🔲 Implementar agendamento diário (cron ou Task Scheduler)
3. 🔲 Adicionar endpoint `/api/banco/sincronizar` para manual
4. 🔲 Logs e notificações de sincronização

### Fase 3: Vinculação Inteligente (Médio Prazo)

1. 🔲 Implementar detecção de processo por descrição
2. 🔲 Criar interface para vinculação manual
3. 🔲 Sugestões de vinculação por IA
4. 🔲 Validação automática de contrapartidas (CPF/CNPJ)

### Fase 4: Compliance e Relatórios (Longo Prazo)

1. 🔲 Dashboard de movimentações não vinculadas
2. 🔲 Alertas de contrapartidas não validadas
3. 🔲 Relatórios para COAF/Receita Federal
4. 🔲 Integração com sistema contábil

---

## 📝 Exemplo Prático

### Cenário Real

**Dia 1 (07/01/2026):**
```python
# Importar extrato de 01/01 a 07/01
resultado = bb_service.consultar_extrato(
    agencia='1251',
    conta='50483',
    data_inicio=datetime(2026, 1, 1),
    data_fim=datetime(2026, 1, 7)
)

# Resultado: 50 lançamentos
# - 50 novos inseridos
# - 0 duplicados
# - Hash calculado para cada um
```

**Dia 2 (08/01/2026):**
```python
# Importar extrato de 01/01 a 08/01 (mesmo período + 1 dia)
resultado = bb_service.consultar_extrato(
    agencia='1251',
    conta='50483',
    data_inicio=datetime(2026, 1, 1),
    data_fim=datetime(2026, 1, 8)
)

# Resultado: 51 lançamentos
# - 1 novo inserido (08/01)
# - 50 duplicados (01/01 a 07/01) ✅ DETECTADOS PELO HASH
# - Sistema pula os 50 antigos automaticamente
```

---

## ⚠️ Considerações Importantes

### 1. Performance

- **Índice no hash_dados:** Essencial para busca rápida de duplicatas
- **Batch insert:** Considerar inserir múltiplos lançamentos de uma vez (se SQL Server suportar)

### 2. Segurança

- **Dados sensíveis:** CPF/CNPJ, valores, descrições
- **Acesso restrito:** Apenas usuários autorizados
- **Auditoria:** Registrar quem vinculou/alterou lançamentos

### 3. Compliance

- **Validação de contrapartidas:** Obrigatória para COAF
- **Rastreamento de origem:** Documentar fonte de cada recurso
- **Relatórios:** Gerar relatórios periódicos para auditoria

### 4. Manutenção

- **Limpeza de dados antigos:** Definir política de retenção (ex: 5 anos)
- **Backup:** Backup diário da tabela `MOVIMENTACAO_BANCARIA`
- **Monitoramento:** Alertas se sincronização falhar

---

## 🎯 Próximos Passos Recomendados

1. **Implementar função de hash** (`gerar_hash_lancamento`)
2. **Criar serviço de importação** (`services/banco_sincronizacao_service.py`)
3. **Testar com dados reais** (importar 1 dia, depois reimportar o mesmo dia)
4. **Validar detecção de duplicatas** (verificar se 0 duplicados são inseridos)
5. **Agendar sincronização diária** (cron ou Task Scheduler)

---

**Última atualização:** 07/01/2026 às 18:00

