# 📊 RESUMO - Integração de Extratos Bancários

**Data:** 07/01/2026  
**Pergunta:** Como alimentar extratos bancários e evitar duplicatas no dia seguinte?

---

## 🎯 Resposta Rápida

### Como Evitar Duplicatas?

**Solução: Hash Único por Lançamento**

Cada lançamento bancário recebe um **hash SHA-256** calculado a partir de:

```
Hash = SHA256(
    banco + agencia + conta + 
    data_lancamento + 
    valor + 
    tipo + 
    sinal + 
    descricao
)
```

**Exemplo:**
- Lançamento: BB, Ag 1251, Cc 50483, 07/01/2026, R$ 1.500,00, Débito, "PAG FRETE"
- Hash: `a7f3c9d2e8b1...` (64 caracteres)

### Fluxo de Importação

```
Dia 1 (07/01):
├─ Importar extrato 01/01 a 07/01
├─ 50 lançamentos encontrados
├─ Calcular hash de cada um
├─ Verificar se hash existe no banco
├─ Resultado: 50 novos, 0 duplicados ✅

Dia 2 (08/01):
├─ Importar extrato 01/01 a 08/01 (mesmo período + 1 dia)
├─ 51 lançamentos encontrados
├─ Calcular hash de cada um
├─ Verificar se hash existe no banco
├─ Resultado: 1 novo (08/01), 50 duplicados (pulados) ✅
```

---

## 🗄️ Tabela: `MOVIMENTACAO_BANCARIA`

### Campos Críticos para Duplicatas

```sql
CREATE TABLE MOVIMENTACAO_BANCARIA (
    id_movimentacao BIGINT PRIMARY KEY,
    
    -- Dados do lançamento
    banco_origem VARCHAR(50) NOT NULL,
    agencia_origem VARCHAR(20),
    conta_origem VARCHAR(50),
    data_movimentacao DATETIME NOT NULL,
    valor_movimentacao DECIMAL(18,2) NOT NULL,
    sinal_movimentacao VARCHAR(1) NOT NULL,  -- 'C' ou 'D'
    descricao_movimentacao TEXT,
    
    -- CRÍTICO: Hash para detectar duplicatas
    hash_dados VARCHAR(64),  -- ✅ CHAVE ÚNICA
    
    -- Vinculação com processo
    processo_referencia VARCHAR(50),
    tipo_relacionamento VARCHAR(50),
    
    -- Compliance (COAF/Receita Federal)
    cpf_cnpj_contrapartida VARCHAR(18),
    nome_contrapartida VARCHAR(255),
    contrapartida_validada BIT DEFAULT 0,
    
    -- Auditoria
    fonte_dados VARCHAR(50),  -- 'BB_API'
    json_dados_originais NVARCHAR(MAX),
    criado_em DATETIME DEFAULT GETDATE()
);

-- Índice CRÍTICO para performance
CREATE INDEX idx_hash_dados ON MOVIMENTACAO_BANCARIA(hash_dados);
```

---

## 🔧 Implementação

### 1. Função de Hash

```python
import hashlib
import json

def gerar_hash_lancamento(lancamento: Dict) -> str:
    """Gera hash único para detectar duplicatas."""
    dados_hash = {
        'banco': 'BB',
        'agencia': lancamento['agencia'],
        'conta': lancamento['conta'],
        'data_lancamento': lancamento['dataLancamento'],  # AAAAMMDD
        'valor': lancamento['valorLancamento'],
        'tipo': lancamento['tipoLancamento'],
        'indicador': lancamento['indicadorLancamento'],  # 'C' ou 'D'
        'descricao': lancamento['textoDescricaoLancamento'][:100]
    }
    
    dados_json = json.dumps(dados_hash, sort_keys=True)
    return hashlib.sha256(dados_json.encode('utf-8')).hexdigest()
```

### 2. Importação com Detecção de Duplicatas

```python
def importar_lancamentos_bb(lancamentos: List[Dict], agencia: str, conta: str):
    """Importa lançamentos evitando duplicatas."""
    novos = 0
    duplicados = 0
    
    for lanc in lancamentos:
        # 1. Gerar hash
        hash_lanc = gerar_hash_lancamento({
            'agencia': agencia,
            'conta': conta,
            **lanc
        })
        
        # 2. Verificar se já existe
        query_check = "SELECT id_movimentacao FROM MOVIMENTACAO_BANCARIA WHERE hash_dados = ?"
        resultado = adapter.execute_query(query_check, (hash_lanc,))
        
        if resultado and len(resultado) > 0:
            # ✅ Já existe - pular
            duplicados += 1
            continue
        
        # 3. Inserir novo
        query_insert = """
            INSERT INTO MOVIMENTACAO_BANCARIA (
                banco_origem, agencia_origem, conta_origem,
                data_movimentacao, valor_movimentacao, sinal_movimentacao,
                descricao_movimentacao, hash_dados, fonte_dados,
                json_dados_originais, criado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
        """
        
        adapter.execute_non_query(query_insert, (
            'BB',
            agencia,
            conta,
            _converter_data_bb(lanc['dataLancamento']),
            lanc['valorLancamento'],
            lanc['indicadorLancamento'],
            lanc['textoDescricaoLancamento'],
            hash_lanc,
            'BB_API',
            json.dumps(lanc)
        ))
        
        novos += 1
    
    logger.info(f"📊 Importação: {novos} novos, {duplicados} duplicados")
    return {'novos': novos, 'duplicados': duplicados}
```

### 3. Sincronização Diária

```python
def sincronizar_extratos_diario():
    """Sincroniza extratos diariamente (executar às 06:00)."""
    from datetime import datetime, timedelta
    
    hoje = datetime.now()
    data_inicio = hoje - timedelta(days=7)  # Últimos 7 dias (margem de segurança)
    
    # Contas a sincronizar
    contas = [
        {'agencia': '1251', 'conta': '50483'},
    ]
    
    for conta_info in contas:
        resultado = bb_service.consultar_extrato(
            agencia=conta_info['agencia'],
            conta=conta_info['conta'],
            data_inicio=data_inicio,
            data_fim=hoje
        )
        
        if resultado['sucesso']:
            lancamentos = resultado['dados']['lancamentos']
            importar_lancamentos_bb(lancamentos, conta_info['agencia'], conta_info['conta'])
```

---

## 🔗 Vinculação com Processos

### Opções de Vinculação

#### 1. Manual (Imediata)
```python
# Atualizar lançamento com processo
UPDATE MOVIMENTACAO_BANCARIA
SET processo_referencia = 'DMD.0083/25',
    tipo_relacionamento = 'PAGAMENTO_FRETE'
WHERE id_movimentacao = 12345;
```

#### 2. Automática por Descrição
```python
def detectar_processo_por_descricao(descricao: str) -> Optional[str]:
    """
    Detecta processo na descrição.
    Ex: "PAG FRETE DMD 0083/25" → DMD.0083/25
    """
    match = re.search(r'\b([A-Z]{2,4})\.?(\d{4})/(\d{2})\b', descricao.upper())
    if match:
        return f"{match.group(1)}.{match.group(2)}/{match.group(3)}"
    return None
```

#### 3. IA (Futura)
- Analisar descrição + valor + data
- Comparar com processos ativos
- Sugerir vinculação automática

---

## 📊 Consultas Úteis

### Lançamentos Não Vinculados
```sql
SELECT 
    data_movimentacao,
    valor_movimentacao,
    descricao_movimentacao
FROM MOVIMENTACAO_BANCARIA
WHERE processo_referencia IS NULL
ORDER BY data_movimentacao DESC;
```

### Movimentações por Processo
```sql
SELECT 
    processo_referencia,
    COUNT(*) as total,
    SUM(valor_movimentacao) as total_valor
FROM MOVIMENTACAO_BANCARIA
WHERE processo_referencia IS NOT NULL
GROUP BY processo_referencia;
```

### Contrapartidas Não Validadas (COMPLIANCE)
```sql
SELECT *
FROM MOVIMENTACAO_BANCARIA
WHERE cpf_cnpj_contrapartida IS NOT NULL
  AND contrapartida_validada = 0;
```

---

## ✅ Próximos Passos

1. **Implementar função `gerar_hash_lancamento()`**
2. **Criar `services/banco_sincronizacao_service.py`**
3. **Testar importação:**
   - Importar 1 dia
   - Reimportar o mesmo dia
   - Verificar: 0 duplicados inseridos ✅
4. **Agendar sincronização diária** (cron/Task Scheduler)
5. **Implementar vinculação manual** (interface web)

---

## 📄 Documentação Completa

Ver: **`docs/INTEGRACAO_EXTRATOS_BANCARIOS.md`**

---

**Última atualização:** 07/01/2026 às 18:05

