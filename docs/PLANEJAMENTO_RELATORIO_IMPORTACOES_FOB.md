# Planejamento: Relatório de Importações Normalizado por FOB

## Objetivo
Criar um relatório que mostre quanto foi importado por categoria (DMD, VDM, etc.) em um mês específico, com valores normalizados para FOB (Free On Board) para evitar distorções causadas por diferentes INCOTERMs.

---

## 1. Entendimento sobre INCOTERMs

### 1.1. INCOTERMs Principais

**FOB (Free On Board):**
- Valor da mercadoria no porto de embarque
- **NÃO inclui:** frete, seguro
- **Fórmula:** FOB = valor da mercadoria (sem frete, sem seguro)

**CIF (Cost, Insurance and Freight):**
- Valor da mercadoria + seguro + frete até o porto de destino
- **Inclui:** valor da mercadoria + seguro + frete
- **Fórmula:** CIF = FOB + Seguro + Frete
- **Para obter FOB:** FOB = CIF - Seguro - Frete

**EXW (Ex Works):**
- Valor da mercadoria na origem (sem transporte)
- **NÃO inclui:** frete, seguro
- **Fórmula:** FOB ≈ EXW (mas pode ter diferenças de localização)

**DDP (Delivered Duty Paid):**
- Valor total incluindo todos os custos até entrega final
- **Inclui:** valor da mercadoria + frete + seguro + impostos + taxas
- **Para obter FOB:** FOB = DDP - Frete - Seguro - Impostos - Taxas (complexo)

**CFR (Cost and Freight):**
- Valor da mercadoria + frete (sem seguro)
- **Inclui:** valor da mercadoria + frete
- **Fórmula:** CFR = FOB + Frete
- **Para obter FOB:** FOB = CFR - Frete

**FCA (Free Carrier):**
- Similar ao FOB, mas para transporte multimodal
- **NÃO inclui:** frete, seguro

### 1.2. Regras de Normalização

**Para DI (Declaração de Importação):**
- **Campo:** `valorMercadoriaEmbarque` (VMLE)
- **INCOTERM:** `condicaoVenda.incoterm.codigo`
- **Frete:** `Di_Frete.valorTotalDolares` / `valorTotalReais`
- **Seguro:** `Di_Seguro.valorTotalDolares` / `valorTotalReais`

**Para DUIMP:**
- **Campo FOB:** `tributos.mercadoria.valorTotalLocalEmbarqueUSD` / `valorTotalLocalEmbarqueBRL`
- **INCOTERM:** (verificar onde está armazenado)
- **Frete:** `carga.frete.valorMoedaNegociada`
- **Seguro:** `carga.seguro.valorMoedaNegociada`

### 1.3. Lógica de Normalização

```
SE INCOTERM = "FOB" OU "EXW" OU "FCA":
    FOB_NORMALIZADO = VMLE (DI) ou valorTotalLocalEmbarque (DUIMP)

SE INCOTERM = "CIF":
    FOB_NORMALIZADO = VMLE - Frete - Seguro

SE INCOTERM = "CFR":
    FOB_NORMALIZADO = VMLE - Frete

SE INCOTERM = "DDP":
    FOB_NORMALIZADO = VMLE - Frete - Seguro - Impostos (complexo, pode não ser preciso)

SE INCOTERM = "OUTROS" OU NÃO INFORMADO:
    FOB_NORMALIZADO = VMLE (assumir que já é FOB ou usar valor como está)
```

---

## 2. Estrutura de Dados

### 2.1. DI (Declaração de Importação)

**Fonte SQL Server:**
- `Serpro.dbo.Di_Dados_Gerais` → `numeroDi`
- `Serpro.dbo.Di_Valor_Mercadoria_Embarque` → `totalDolares`, `totalReais` (VMLE)
- `Serpro.dbo.Di_Frete` → `valorTotalDolares`, `valorTotalReais`
- `Serpro.dbo.Di_Seguro` → `valorTotalDolares`, `valorTotalReais`
- `Serpro.dbo.Di_Dados_Gerais` → `condicaoVenda` (JSON) → `incoterm.codigo`

**Campos necessários:**
- `numeroDi`
- `dataHoraDesembaraco` (para filtrar por mês)
- `dollar_VLME` (VMLE em USD)
- `real_VLME` (VMLE em BRL)
- `frete_usd` (frete em USD)
- `frete_brl` (frete em BRL)
- `seguro_usd` (seguro em USD)
- `seguro_brl` (seguro em BRL)
- `incoterm_codigo` (código do INCOTERM)

### 2.2. DUIMP

**Fonte SQL Server:**
- `duimp.dbo.duimp_tributos_mercadoria` → `valor_total_local_embarque_usd`, `valor_total_local_embarque_brl` (FOB)
- `duimp.dbo.duimp` → `numero_duimp`, `data_desembaraco` (para filtrar por mês)
- `duimp.dbo.duimp_carga` → `frete`, `seguro` (verificar estrutura)

**Campos necessários:**
- `numero_duimp`
- `data_desembaraco` (para filtrar por mês)
- `valor_total_local_embarque_usd` (FOB em USD)
- `valor_total_local_embarque_brl` (FOB em BRL)
- `frete_usd` (se disponível)
- `frete_brl` (se disponível)
- `seguro_usd` (se disponível)
- `seguro_brl` (se disponível)
- `incoterm_codigo` (verificar onde está armazenado)

### 2.3. Vínculo com Processo

**Tabela:** `make.dbo.PROCESSO_IMPORTACAO`
- `numero_processo` (ex: "DMD.0085/25")
- `numero_di` (FK para DI)
- `numero_duimp` (FK para DUIMP)
- `categoria` (ex: "DMD", "VDM", "ALH", etc.)

---

## 3. Estrutura do Relatório

### 3.1. Parâmetros de Entrada

- `categoria`: Categoria do processo (ex: "DMD", "VDM", "ALH", etc.) - opcional
- `mes`: Mês (1-12) - obrigatório
- `ano`: Ano (ex: 2025) - obrigatório
- `moeda`: "USD" ou "BRL" - padrão: "BRL"

### 3.2. Estrutura de Saída

```json
{
  "categoria": "DMD",
  "mes": 12,
  "ano": 2025,
  "moeda": "BRL",
  "total_fob_normalizado": 1234567.89,
  "total_processos": 15,
  "processos": [
    {
      "numero_processo": "DMD.0085/25",
      "numero_di": "2528165179",
      "numero_duimp": null,
      "data_desembaraco": "2025-12-19",
      "incoterm": "CIF",
      "vmle_original_usd": 41206.51,
      "vmle_original_brl": 227801.94,
      "frete_usd": 3500.00,
      "frete_brl": 19350.00,
      "seguro_usd": 200.00,
      "seguro_brl": 1106.00,
      "fob_normalizado_usd": 37506.51,
      "fob_normalizado_brl": 207345.94,
      "moeda_relatorio": "BRL",
      "fob_normalizado": 207345.94
    },
    {
      "numero_processo": "VDM.0003/25",
      "numero_di": null,
      "numero_duimp": "25BR00001928777",
      "data_desembaraco": "2025-10-22",
      "incoterm": "FOB",
      "fob_original_usd": 15000.00,
      "fob_original_brl": 83000.00,
      "frete_usd": null,
      "frete_brl": null,
      "seguro_usd": null,
      "seguro_brl": null,
      "fob_normalizado_usd": 15000.00,
      "fob_normalizado_brl": 83000.00,
      "moeda_relatorio": "BRL",
      "fob_normalizado": 83000.00
    }
  ],
  "resumo_por_incoterm": {
    "FOB": {
      "total_processos": 5,
      "total_fob": 500000.00
    },
    "CIF": {
      "total_processos": 10,
      "total_fob": 734567.89
    }
  }
}
```

---

## 4. Validações Necessárias

### 4.1. Validação de Dados

1. **Verificar se processo tem DI ou DUIMP:**
   - Se não tiver nenhum, não incluir no relatório (ou marcar como "sem documento")

2. **Verificar se INCOTERM está presente:**
   - Se não estiver, assumir FOB (ou usar valor como está)

3. **Verificar se valores estão presentes:**
   - Se VMLE/FOB não estiver presente, não incluir no relatório
   - Se INCOTERM for CIF/CFR e frete/seguro não estiverem presentes, usar VMLE como FOB (com aviso)

4. **Verificar se data de desembaraço está no mês/ano especificado:**
   - Filtrar apenas processos desembaraçados no mês/ano

### 4.2. Validação de Cálculos

1. **FOB não pode ser negativo:**
   - Se FOB calculado for negativo (CIF - Frete - Seguro < 0), usar VMLE como FOB (com aviso)

2. **FOB não pode ser maior que CIF:**
   - Se FOB calculado for maior que CIF, usar VMLE como FOB (com aviso)

3. **Verificar consistência de moedas:**
   - Se valores estiverem em moedas diferentes, converter para moeda do relatório usando taxa de câmbio

### 4.3. Validação de Regras de Negócio

1. **Processos desembaraçados apenas:**
   - Incluir apenas processos com `situacaoDi` = "DI_DESEMBARACADA" ou `situacaoDuimp` = "DESEMBARACADA_CARGA_ENTREGUE"

2. **Categoria do processo:**
   - Se categoria for especificada, filtrar apenas processos dessa categoria

---

## 5. Implementação

### 5.1. Arquivos a Criar/Modificar

1. **Novo arquivo:** `services/relatorio_importacoes_fob_service.py`
   - Classe `RelatorioImportacoesFOBService`
   - Método `gerar_relatorio(categoria, mes, ano, moeda='BRL')`

2. **Modificar:** `services/tool_definitions.py`
   - Adicionar tool `gerar_relatorio_importacoes_fob`

3. **Modificar:** `services/tool_router.py`
   - Mapear tool para agent apropriado

4. **Modificar:** `services/agents/processo_agent.py` (ou criar novo agent)
   - Adicionar handler `_gerar_relatorio_importacoes_fob`

### 5.2. Queries SQL

**Query para DI:**
```sql
SELECT 
    p.numero_processo,
    p.categoria,
    di.numeroDi,
    di.dataHoraDesembaraco,
    di.dollar_VLME,
    di.real_VLME,
    di.frete_usd,
    di.frete_brl,
    di.seguro_usd,
    di.seguro_brl,
    di.incoterm_codigo
FROM make.dbo.PROCESSO_IMPORTACAO p
INNER JOIN Serpro.dbo.Di_Dados_Gerais di ON p.numero_di = di.numeroDi
WHERE p.categoria = ? -- se especificado
  AND YEAR(di.dataHoraDesembaraco) = ?
  AND MONTH(di.dataHoraDesembaraco) = ?
  AND di.situacaoDi = 'DI_DESEMBARACADA'
```

**Query para DUIMP:**
```sql
SELECT 
    p.numero_processo,
    p.categoria,
    d.numero_duimp,
    d.data_desembaraco,
    tm.valor_total_local_embarque_usd,
    tm.valor_total_local_embarque_brl,
    -- frete e seguro (verificar estrutura)
    d.incoterm_codigo -- verificar onde está
FROM make.dbo.PROCESSO_IMPORTACAO p
INNER JOIN duimp.dbo.duimp d ON p.numero_duimp = d.numero_duimp
INNER JOIN duimp.dbo.duimp_tributos_mercadoria tm ON d.duimp_id = tm.duimp_id
WHERE p.categoria = ? -- se especificado
  AND YEAR(d.data_desembaraco) = ?
  AND MONTH(d.data_desembaraco) = ?
  AND d.situacao_duimp = 'DESEMBARACADA_CARGA_ENTREGUE'
```

### 5.3. Função de Normalização

```python
def normalizar_fob_para_incoterm(
    incoterm: str,
    vmle_usd: float,
    vmle_brl: float,
    frete_usd: Optional[float] = None,
    frete_brl: Optional[float] = None,
    seguro_usd: Optional[float] = None,
    seguro_brl: Optional[float] = None
) -> Dict[str, float]:
    """
    Normaliza valor para FOB baseado no INCOTERM.
    
    Returns:
        {
            'fob_usd': float,
            'fob_brl': float,
            'aviso': str (opcional)
        }
    """
    incoterm_upper = (incoterm or '').upper().strip()
    
    # INCOTERMs que já são FOB (não precisam ajuste)
    if incoterm_upper in ['FOB', 'EXW', 'FCA']:
        return {
            'fob_usd': vmle_usd,
            'fob_brl': vmle_brl
        }
    
    # CIF: CIF = FOB + Frete + Seguro
    if incoterm_upper == 'CIF':
        frete_usd = frete_usd or 0.0
        frete_brl = frete_brl or 0.0
        seguro_usd = seguro_usd or 0.0
        seguro_brl = seguro_brl or 0.0
        
        fob_usd = vmle_usd - frete_usd - seguro_usd
        fob_brl = vmle_brl - frete_brl - seguro_brl
        
        # Validação: FOB não pode ser negativo
        if fob_usd < 0 or fob_brl < 0:
            return {
                'fob_usd': vmle_usd,
                'fob_brl': vmle_brl,
                'aviso': 'FOB calculado foi negativo, usando VMLE original'
            }
        
        return {
            'fob_usd': fob_usd,
            'fob_brl': fob_brl
        }
    
    # CFR: CFR = FOB + Frete
    if incoterm_upper == 'CFR':
        frete_usd = frete_usd or 0.0
        frete_brl = frete_brl or 0.0
        
        fob_usd = vmle_usd - frete_usd
        fob_brl = vmle_brl - frete_brl
        
        if fob_usd < 0 or fob_brl < 0:
            return {
                'fob_usd': vmle_usd,
                'fob_brl': vmle_brl,
                'aviso': 'FOB calculado foi negativo, usando VMLE original'
            }
        
        return {
            'fob_usd': fob_usd,
            'fob_brl': fob_brl
        }
    
    # Outros INCOTERMs ou não informado: assumir que já é FOB
    return {
        'fob_usd': vmle_usd,
        'fob_brl': vmle_brl,
        'aviso': f'INCOTERM {incoterm} não suportado, usando valor original'
    }
```

---

## 6. Testes

### 6.1. Casos de Teste

1. **Teste 1: DI com INCOTERM FOB**
   - Processo: DMD.0085/25
   - INCOTERM: FOB
   - VMLE: R$ 100.000,00
   - Resultado esperado: FOB = R$ 100.000,00

2. **Teste 2: DI com INCOTERM CIF**
   - Processo: DMD.XXXX/25
   - INCOTERM: CIF
   - VMLE: R$ 100.000,00
   - Frete: R$ 10.000,00
   - Seguro: R$ 1.000,00
   - Resultado esperado: FOB = R$ 89.000,00

3. **Teste 3: DUIMP com FOB direto**
   - Processo: VDM.0003/25
   - FOB: R$ 50.000,00
   - Resultado esperado: FOB = R$ 50.000,00

4. **Teste 4: Validação de FOB negativo**
   - INCOTERM: CIF
   - VMLE: R$ 100.000,00
   - Frete: R$ 80.000,00
   - Seguro: R$ 30.000,00
   - Resultado esperado: FOB = R$ 100.000,00 (com aviso)

5. **Teste 5: Relatório completo por mês**
   - Mês: 12/2025
   - Categoria: DMD
   - Resultado esperado: Lista de processos com FOB normalizado

---

## 7. Próximos Passos

1. ✅ Validar estrutura de dados no SQL Server (verificar onde está INCOTERM na DUIMP)
2. ✅ Implementar função de normalização FOB
3. ✅ Implementar queries SQL
4. ✅ Implementar serviço de relatório
5. ✅ Adicionar tool e handler
6. ✅ Testar com dados reais
7. ✅ Documentar uso

---

## 8. Observações Importantes

1. **INCOTERM na DUIMP:** Precisamos verificar onde o INCOTERM está armazenado na DUIMP. Pode estar em `duimp_carga` ou em outro lugar.

2. **Taxa de Câmbio:** Se valores estiverem em moedas diferentes, precisamos de uma fonte de taxa de câmbio (pode usar `utils/ptax_bcb.py`).

3. **Processos sem DI/DUIMP:** Processos que não têm DI nem DUIMP não podem ser incluídos no relatório (ou devem ser marcados separadamente).

4. **Processos com DI e DUIMP:** Se um processo tiver ambos, priorizar DUIMP (mais recente).

---

**Data de Criação:** 23/12/2025
**Autor:** Sistema de IA
**Status:** Planejamento - Aguardando Validação











