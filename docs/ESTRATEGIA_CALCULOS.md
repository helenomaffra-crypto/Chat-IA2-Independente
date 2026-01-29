# Estratégia de Cálculos: Python Local vs Code Interpreter

## 🎯 Princípio Geral

**Use Python local para cálculos simples e rápidos.**
**Use Code Interpreter apenas quando o usuário pedir explicação detalhada OU quando for um cálculo complexo que não está no código.**

---

## 📊 Quando Usar Cada Abordagem

### ✅ Python Local (`calcular_impostos_ncm`)

**Use quando:**
- Cálculo simples de impostos (II, IPI, PIS, COFINS)
- Cálculo de percentuais simples (ex: 1,5% do CIF)
- Cálculo de CIF, FOB, conversão de moedas
- **Usuário NÃO pediu explicação detalhada**

**Vantagens:**
- ⚡ Rápido (execução instantânea)
- 💰 Sem custo de API
- 🎯 Previsível e testável
- 🔒 Controle total sobre a lógica

**Exemplos:**
```
"calcule os impostos para CIF de 30.000 dólares, câmbio 5,10, II de 30%"
→ calcular_impostos_ncm (Python local)
```

```
"quanto é 1,5% do CIF de 30.000 dólares?"
→ calcular_impostos_ncm ou cálculo direto (Python local)
```

---

### 🧮 Code Interpreter (`calcular_com_code_interpreter`)

**Use quando:**
- **Usuário pediu explicação detalhada** ("explicando", "detalhado", "mostrando fórmulas", "passo a passo")
- Cálculo complexo que não está no código (ex: juros compostos, cálculos estatísticos, análises financeiras)
- Cálculo que requer validação de fórmulas ou múltiplas abordagens
- Cálculo que precisa de visualizações ou gráficos

**Vantagens:**
- 📚 Explicações detalhadas automáticas
- 🔍 Validação de fórmulas
- 📊 Suporte a visualizações
- 🧠 Adapta-se a novos cálculos sem alterar código

**Desvantagens:**
- ⏱️ Mais lento (requer chamada à API)
- 💰 Custo de API
- 🎲 Menos previsível (pode variar a explicação)

**Exemplos:**
```
"calcule explicando o imposto de importação de 30% para um cif de 30000 dólares"
→ calcular_com_code_interpreter (Code Interpreter)
```

```
"calcule os impostos mostrando as fórmulas passo a passo"
→ calcular_com_code_interpreter (Code Interpreter)
```

---

## 🔧 Implementação Atual

### Cálculos Disponíveis em Python Local

**Arquivo:** `services/calculo_impostos_service.py`

**Cálculos implementados:**
1. ✅ CIF (Custo + Frete + Seguro)
2. ✅ II (Imposto de Importação) - base: CIF
3. ✅ IPI (Imposto sobre Produtos Industrializados) - base: CIF + II
4. ✅ PIS/PASEP - base: CIF
5. ✅ COFINS - base: CIF
6. ✅ Conversão USD ↔ BRL (usando PTAX)
7. ✅ Total de impostos (soma de todos)

**Cálculos que PODEM ser adicionados:**
- ✅ Percentual simples (ex: 1,5% do CIF)
- ✅ Cálculo de FOB (CIF - Frete - Seguro)
- ✅ Cálculo de AFRMM (percentual sobre frete)
- ✅ Cálculo de ICMS (se necessário)
- ✅ Cálculo de juros simples
- ✅ Cálculo de multas (percentual sobre valor)

---

## 💡 Recomendações

### 1. Expandir Python Local para Cálculos Comuns

**Adicionar métodos para:**
```python
def calcular_percentual(valor: float, percentual: float) -> float:
    """Calcula percentual de um valor."""
    return valor * (percentual / 100.0)

def calcular_afrmm(frete_usd: float, aliquota_afrmm: float, cotacao_ptax: float) -> Dict[str, float]:
    """Calcula AFRMM sobre frete."""
    afrmm_usd = frete_usd * (aliquota_afrmm / 100.0)
    afrmm_brl = afrmm_usd * cotacao_ptax
    return {'usd': afrmm_usd, 'brl': afrmm_brl}

def calcular_fob(cif_usd: float, frete_usd: float, seguro_usd: float) -> float:
    """Calcula FOB a partir de CIF."""
    return cif_usd - frete_usd - seguro_usd
```

### 2. Usar Code Interpreter Apenas Quando Necessário

**Critérios para usar Code Interpreter:**
1. ✅ Usuário pediu explicitamente explicação ("explicando", "detalhado", "mostrando fórmulas")
2. ✅ Cálculo complexo que não está no código (ex: juros compostos, análises estatísticas)
3. ✅ Cálculo que requer validação de múltiplas fórmulas
4. ✅ Cálculo que precisa de visualizações ou gráficos

**NÃO usar Code Interpreter para:**
- ❌ Cálculos simples de impostos (mesmo que o usuário forneça CIF direto)
- ❌ Cálculos de percentuais simples
- ❌ Conversões de moeda
- ❌ Cálculos que já estão implementados em Python local

### 3. Melhorar Detecção de Intenção

**Atualizar prompt para detectar:**
- "explicando", "detalhado", "mostrando fórmulas", "passo a passo" → Code Interpreter
- Cálculo simples sem explicação → Python local

---

## 📝 Exemplos Práticos

### Exemplo 1: Cálculo Simples (Python Local)

**Usuário:** "calcule os impostos para CIF de 30.000 dólares, câmbio 5,10, II de 30%"

**Resposta:** Usar `calcular_impostos_ncm` (Python local)
- Rápido
- Sem custo
- Resultado direto

---

### Exemplo 2: Cálculo com Explicação (Code Interpreter)

**Usuário:** "calcule explicando o imposto de importação de 30% para um cif de 30000 dólares a um cambio de 5,10"

**Resposta:** Usar `calcular_com_code_interpreter` (Code Interpreter)
- Explicação detalhada
- Fórmulas passo a passo
- Validação automática

---

### Exemplo 3: Cálculo de Percentual Simples (Python Local)

**Usuário:** "quanto é 1,5% do CIF de 30.000 dólares?"

**Resposta:** Usar Python local (cálculo direto ou método `calcular_percentual`)
- Rápido
- Simples
- Não precisa de explicação

---

### Exemplo 4: Cálculo Complexo (Code Interpreter)

**Usuário:** "calcule o valor presente líquido de um investimento de 100.000 dólares com taxa de 5% ao ano por 3 anos"

**Resposta:** Usar `calcular_com_code_interpreter` (Code Interpreter)
- Cálculo complexo não está no código
- Requer fórmula específica
- Pode precisar de explicação

---

## 🎯 Conclusão

**Estratégia Híbrida:**
1. **Python local** para cálculos comuns e rápidos (impostos, percentuais, conversões)
2. **Code Interpreter** apenas quando:
   - Usuário pedir explicação detalhada
   - Cálculo complexo que não está no código
   - Cálculo que requer validação ou visualizações

**Próximos Passos:**
1. ✅ Expandir Python local com cálculos comuns (percentuais, AFRMM, FOB, etc.)
2. ✅ Melhorar detecção de intenção (explicação vs cálculo simples)
3. ✅ Documentar quando usar cada abordagem



