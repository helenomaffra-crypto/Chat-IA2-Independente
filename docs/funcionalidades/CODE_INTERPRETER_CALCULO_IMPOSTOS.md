# Code Interpreter para Cálculo de Impostos

## 📊 Comparação: Método Atual vs Code Interpreter

### Método Atual (Python Local)

**Localização:** `services/calculo_impostos_service.py`

**Como funciona:**
```python
# Cálculo direto em Python
def calcular_impostos(custo_usd, frete_usd, seguro_usd, cotacao_ptax, aliquotas):
    # 1. CIF
    cif_usd = custo_usd + frete_usd + seguro_usd
    cif_brl = cif_usd * cotacao_ptax
    
    # 2. II (base: CIF)
    ii_brl = cif_brl * (aliquotas['ii'] / 100.0)
    
    # 3. IPI (base: CIF + II)
    ipi_brl = (cif_brl + ii_brl) * (aliquotas['ipi'] / 100.0)
    
    # 4. PIS (base: CIF)
    pis_brl = cif_brl * (aliquotas['pis'] / 100.0)
    
    # 5. COFINS (base: CIF)
    cofins_brl = cif_brl * (aliquotas['cofins'] / 100.0)
    
    return {
        'cif': {'usd': cif_usd, 'brl': cif_brl},
        'impostos': {
            'ii': {'brl': ii_brl, 'usd': ii_brl / cotacao_ptax},
            'ipi': {'brl': ipi_brl, 'usd': ipi_brl / cotacao_ptax},
            'pis': {'brl': pis_brl, 'usd': pis_brl / cotacao_ptax},
            'cofins': {'brl': cofins_brl, 'usd': cofins_brl / cotacao_ptax}
        }
    }
```

**Vantagens:**
- ✅ Rápido (execução instantânea)
- ✅ Sem custo de API
- ✅ Controle total sobre a lógica
- ✅ Previsível e testável

**Desvantagens:**
- ❌ Lógica fixa (difícil adicionar novos tipos de cálculo)
- ❌ Não explica os passos automaticamente
- ❌ Não valida fórmulas automaticamente

---

### Método com Code Interpreter (Responses API)

**Como funcionaria:**

```python
from services.responses_service import ResponsesService

def calcular_impostos_com_code_interpreter(
    custo_usd: float,
    frete_usd: float,
    seguro_usd: float,
    cotacao_ptax: float,
    aliquotas: Dict[str, float]
) -> Dict[str, Any]:
    """
    Calcula impostos usando Code Interpreter da OpenAI.
    
    O Code Interpreter recebe uma instrução em linguagem natural
    e executa código Python em um ambiente sandbox.
    """
    
    responses_service = ResponsesService()
    
    # Montar prompt com os dados
    prompt = f"""
Calcule os impostos de importação para os seguintes valores:

**Valores de Entrada:**
- Custo (VMLE): USD {custo_usd:,.2f}
- Frete: USD {frete_usd:,.2f}
- Seguro: USD {seguro_usd:,.2f}
- Cotação PTAX: R$ {cotacao_ptax:,.4f} / USD

**Alíquotas:**
- II (Imposto de Importação): {aliquotas.get('ii', 0):.2f}%
- IPI (Imposto sobre Produtos Industrializados): {aliquotas.get('ipi', 0):.2f}%
- PIS/PASEP: {aliquotas.get('pis', 0):.2f}%
- COFINS: {aliquotas.get('cofins', 0):.2f}%

**Instruções:**
1. Calcule o CIF (Custo + Frete + Seguro) em USD e converta para BRL usando a cotação PTAX
2. Calcule cada imposto seguindo as regras:
   - II: Base de cálculo = CIF, Fórmula = CIF × alíquota II
   - IPI: Base de cálculo = CIF + II, Fórmula = (CIF + II) × alíquota IPI
   - PIS: Base de cálculo = CIF, Fórmula = CIF × alíquota PIS
   - COFINS: Base de cálculo = CIF, Fórmula = CIF × alíquota COFINS
3. Converta todos os valores para USD usando a cotação PTAX
4. Apresente os resultados de forma clara e organizada
5. Mostre os cálculos passo a passo

**Formato de Resposta Esperado:**
- Mostre cada etapa do cálculo
- Apresente valores em BRL e USD
- Inclua fórmulas e explicações
"""
    
    # Chamar Code Interpreter via Responses API
    resultado = responses_service.buscar_legislacao_com_calculo(
        pergunta=prompt,
        dados_calculo={
            'custo_usd': custo_usd,
            'frete_usd': frete_usd,
            'seguro_usd': seguro_usd,
            'cotacao_ptax': cotacao_ptax,
            'aliquotas': aliquotas
        }
    )
    
    return resultado
```

**O que o Code Interpreter faria internamente:**

1. **Recebe o prompt** em linguagem natural
2. **Gera código Python** automaticamente:
```python
# Código gerado automaticamente pelo Code Interpreter
custo_usd = 10000.00
frete_usd = 1500.00
seguro_usd = 200.00
cotacao_ptax = 5.5283

# Calcular CIF
cif_usd = custo_usd + frete_usd + seguro_usd
cif_brl = cif_usd * cotacao_ptax

print(f"CIF USD: ${cif_usd:,.2f}")
print(f"CIF BRL: R$ {cif_brl:,.2f}")

# Calcular II
aliquota_ii = 18.0 / 100
ii_brl = cif_brl * aliquota_ii
ii_usd = ii_brl / cotacao_ptax

print(f"\nII (18%):")
print(f"  Base: CIF = R$ {cif_brl:,.2f}")
print(f"  Cálculo: R$ {cif_brl:,.2f} × 0.18 = R$ {ii_brl:,.2f}")
print(f"  II BRL: R$ {ii_brl:,.2f}")
print(f"  II USD: ${ii_usd:,.2f}")

# ... e assim por diante para IPI, PIS, COFINS
```

3. **Executa o código** em um ambiente sandbox
4. **Retorna a resposta** formatada com explicações

---

## 🔍 Exemplo Prático

### Entrada:
```python
custo_usd = 10000.00
frete_usd = 1500.00
seguro_usd = 200.00
cotacao_ptax = 5.5283
aliquotas = {
    'ii': 18.0,
    'ipi': 10.0,
    'pis': 1.65,
    'cofins': 7.6
}
```

### Saída do Code Interpreter:

```
💰 CÁLCULO DE IMPOSTOS DE IMPORTAÇÃO

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Valores de Entrada:
• Custo (VMLE): USD 10,000.00
• Frete: USD 1,500.00
• Seguro: USD 200.00
• Cotação PTAX: R$ 5.5283 / USD

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ CÁLCULO DO CIF (Custo + Frete + Seguro)

CIF USD = 10,000.00 + 1,500.00 + 200.00 = USD 11,700.00
CIF BRL = USD 11,700.00 × 5.5283 = R$ 64,681.11

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ CÁLCULO DO II (Imposto de Importação) - 18.00%

Base de Cálculo: CIF = R$ 64,681.11
Fórmula: II = CIF × 18.00%
Cálculo: R$ 64,681.11 × 0.18 = R$ 11,642.60

Resultado:
• II BRL: R$ 11,642.60
• II USD: $ 2,105.11

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ CÁLCULO DO IPI (Imposto sobre Produtos Industrializados) - 10.00%

Base de Cálculo: CIF + II = R$ 64,681.11 + R$ 11,642.60 = R$ 76,323.71
Fórmula: IPI = (CIF + II) × 10.00%
Cálculo: R$ 76,323.71 × 0.10 = R$ 7,632.37

Resultado:
• IPI BRL: R$ 7,632.37
• IPI USD: $ 1,380.59

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ CÁLCULO DO PIS/PASEP - 1.65%

Base de Cálculo: CIF = R$ 64,681.11
Fórmula: PIS = CIF × 1.65%
Cálculo: R$ 64,681.11 × 0.0165 = R$ 1,067.24

Resultado:
• PIS BRL: R$ 1,067.24
• PIS USD: $ 193.05

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5️⃣ CÁLCULO DO COFINS - 7.60%

Base de Cálculo: CIF = R$ 64,681.11
Fórmula: COFINS = CIF × 7.60%
Cálculo: R$ 64,681.11 × 0.076 = R$ 4,915.76

Resultado:
• COFINS BRL: R$ 4,915.76
• COFINS USD: $ 889.35

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 RESUMO FINAL

Total de Impostos:
• Total BRL = II + IPI + PIS + COFINS
• Total BRL = R$ 11,642.60 + R$ 7,632.37 + R$ 1,067.24 + R$ 4,915.76
• Total BRL = R$ 25,257.97
• Total USD = R$ 25,257.97 ÷ 5.5283 = USD 4,568.10

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Valores Consolidados:
• CIF: R$ 64,681.11 (USD 11,700.00)
• Total de Impostos: R$ 25,257.97 (USD 4,568.10)
• Valor Total (CIF + Impostos): R$ 89,939.08 (USD 16,268.10)
```

---

## ⚖️ Comparação Detalhada

| Aspecto | Python Local | Code Interpreter |
|---------|--------------|------------------|
| **Velocidade** | ⚡ Instantâneo | 🐢 ~2-5 segundos |
| **Custo** | 💰 Grátis | 💸 ~$0.01-0.03 por cálculo |
| **Explicação** | ❌ Manual | ✅ Automática |
| **Flexibilidade** | ❌ Código fixo | ✅ Adapta-se ao prompt |
| **Validação** | ❌ Manual | ✅ Automática |
| **Debug** | ✅ Fácil | ⚠️ Mais difícil |
| **Manutenção** | ✅ Controle total | ⚠️ Depende da API |
| **Casos Complexos** | ❌ Precisa codificar | ✅ Resolve automaticamente |

---

## 🎯 Quando Usar Cada Método

### Use Python Local quando:
- ✅ Cálculos simples e previsíveis
- ✅ Performance é crítica
- ✅ Quer controle total
- ✅ Não precisa de explicações detalhadas

### Use Code Interpreter quando:
- ✅ Precisa de explicações passo a passo
- ✅ Cálculos complexos ou variáveis
- ✅ Quer validação automática
- ✅ Precisa de flexibilidade para novos tipos de cálculo
- ✅ Quer que o usuário entenda o processo

---

## 💡 Recomendação Híbrida

**Melhor dos dois mundos:**

1. **Cálculo rápido** → Python Local (para performance)
2. **Explicação detalhada** → Code Interpreter (quando solicitado)

```python
def calcular_impostos_hibrido(
    custo_usd, frete_usd, seguro_usd, cotacao_ptax, aliquotas,
    incluir_explicacao_detalhada: bool = False
):
    # Sempre calcular localmente (rápido)
    resultado = CalculoImpostosService().calcular_impostos(
        custo_usd, frete_usd, seguro_usd, cotacao_ptax, aliquotas
    )
    
    # Se pedir explicação detalhada, usar Code Interpreter
    if incluir_explicacao_detalhada:
        explicacao = ResponsesService().buscar_legislacao_com_calculo(
            pergunta=f"Explique detalhadamente como foram calculados estes impostos: {resultado}"
        )
        resultado['explicacao_detalhada'] = explicacao
    
    return resultado
```

---

## 🧪 Teste Prático

Veja `scripts/test_code_interpreter_calculo_impostos.py` para um exemplo funcional.

