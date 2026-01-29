# Exemplos de Uso do Code Interpreter

## 🎯 Como o Usuário Usa

### Exemplo 1: Cálculo de Impostos com Explicação

```
👤 Usuário: "calcule os impostos explicando passo a passo para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283"

🤖 IA detecta: "calcular impostos" + "explicando passo a passo"
   → chama tool: calcular_com_code_interpreter(
       tipo_calculo="impostos",
       dados={
           "custo_usd": 10000,
           "frete_usd": 1500,
           "seguro_usd": 200,
           "cotacao_ptax": 5.5283,
           "aliquotas": {"ii": 18, "ipi": 10, "pis": 1.65, "cofins": 7.6}
       },
       pergunta_usuario="calcule os impostos explicando passo a passo..."
   )

🔧 CalculoAgent._calcular_com_code_interpreter()
   → ResponsesService.buscar_legislacao_com_calculo()
   → OpenAI Responses API com Code Interpreter

📊 Resposta:
   "💰 CÁLCULO DE IMPOSTOS
   
    1️⃣ CIF = 10,000 + 1,500 + 200 = USD 11,700
       CIF BRL = 11,700 × 5.5283 = R$ 64,681.11
   
    2️⃣ II (18%):
       Base: CIF = R$ 64,681.11
       Fórmula: II = CIF × 18%
       Cálculo: 64,681.11 × 0.18 = R$ 11,642.60
       ..."
```

---

### Exemplo 2: Cálculo Genérico

```
👤 Usuário: "calcule quanto fica de imposto se eu importar 50.000 dólares de mercadoria com frete de 5.000 e alíquota II de 14%? mostre as fórmulas"

🤖 IA detecta: "calcular" + "mostre as fórmulas"
   → chama tool: executar_calculo_python(
       descricao_calculo="calcular imposto de importação",
       valores={
           "custo_usd": 50000,
           "frete_usd": 5000,
           "aliquota_ii": 14
       },
       instrucoes_especificas="mostre as fórmulas"
   )

🔧 CalculoAgent._executar_calculo_python()
   → Code Interpreter executa cálculo
   → Retorna explicação com fórmulas
```

---

### Exemplo 3: Cálculo de CIF Detalhado

```
👤 Usuário: "calcule o CIF e explique cada etapa para custo 10.000, frete 1.500, seguro 200, cotação 5.5283"

🤖 IA detecta: "calcular CIF" + "explique cada etapa"
   → chama tool: calcular_com_code_interpreter(
       tipo_calculo="cif",
       dados={
           "custo_usd": 10000,
           "frete_usd": 1500,
           "seguro_usd": 200,
           "cotacao_ptax": 5.5283
       },
       pergunta_usuario="calcule o CIF e explique cada etapa..."
   )
```

---

## 🔄 Fluxo Completo

```
1. 👤 Usuário digita mensagem
   ↓
2. 📨 ChatService.processar_mensagem()
   ↓
3. 🧠 IA (GPT-4o) analisa mensagem
   - Detecta intenção: "calcular" + "explicar"
   - Escolhe tool: calcular_com_code_interpreter()
   ↓
4. 🔧 ToolRouter.route()
   - Mapeia tool → CalculoAgent
   ↓
5. 🐍 CalculoAgent.execute()
   - Chama _calcular_com_code_interpreter()
   ↓
6. 📡 ResponsesService.buscar_legislacao_com_calculo()
   - Monta prompt
   - Chama OpenAI Responses API
   ↓
7. 🤖 OpenAI Code Interpreter
   - Entende prompt
   - Gera código Python
   - Executa em sandbox
   - Retorna resultado + explicação
   ↓
8. 📊 Resposta formatada volta para o usuário
```

---

## 🆚 Comparação: Quando Usar Cada Tool

| Situação | Tool Recomendada | Por quê? |
|----------|------------------|----------|
| "calcule os impostos" | `calcular_impostos_ncm` | Rápido, sem custo |
| "calcule os impostos explicando" | `calcular_com_code_interpreter` | Com explicação |
| "calcule os impostos mostrando fórmulas" | `calcular_com_code_interpreter` | Com fórmulas |
| "calcule X usando Python" | `executar_calculo_python` | Cálculo genérico |
| "quanto é Y explicando" | `executar_calculo_python` | Explicação genérica |

---

## 💡 Dicas para o Usuário

### Para cálculos rápidos (sem explicação):
```
"calcule os impostos para carga de 10.000 dólares"
→ Usa calcular_impostos_ncm (Python local, rápido)
```

### Para cálculos com explicação:
```
"calcule os impostos explicando passo a passo"
"calcule os impostos mostrando as fórmulas"
"quanto fica de imposto detalhando cada etapa"
→ Usa calcular_com_code_interpreter (Code Interpreter)
```

### Para cálculos genéricos:
```
"calcule o juros compostos de 10.000 a 5% ao mês por 12 meses"
"calcule a média ponderada de [valores]"
→ Usa executar_calculo_python (Code Interpreter genérico)
```

---

## 🧪 Teste Você Mesmo

1. **Teste rápido (Python local):**
   ```
   "calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283"
   ```

2. **Teste com explicação (Code Interpreter):**
   ```
   "calcule os impostos explicando passo a passo para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283"
   ```

3. **Teste genérico:**
   ```
   "calcule o CIF usando Python para custo 10.000, frete 1.500, seguro 200, cotação 5.5283"
   ```



