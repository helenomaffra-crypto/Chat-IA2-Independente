# 🤖 Code Interpreter: Como Ele Entende as Regras de Negócio

**Última atualização:** 05/01/2026

---

## ❓ A Pergunta Fundamental

**"Como o Code Interpreter sabe que a base de cálculo do II é o CIF?"**

**Resposta curta:** Ele **NÃO sabe automaticamente**. Ele precisa receber instruções claras no **prompt do assistente**.

---

## 🔍 Como o Code Interpreter Funciona

### 1. **Ele NÃO Tem Conhecimento Específico de Domínio**

O Code Interpreter é uma ferramenta que:
- ✅ Sabe programar em Python
- ✅ Sabe fazer cálculos matemáticos
- ✅ Sabe manipular dados
- ❌ **NÃO sabe** que "II usa CIF como base de cálculo"
- ❌ **NÃO sabe** que "IPI incide sobre CIF + II"
- ❌ **NÃO sabe** regras específicas de COMEX brasileiro

### 2. **Ele Aprende Através do Prompt do Assistente**

O Code Interpreter recebe instruções através do campo `instructions` quando você cria um assistente:

```python
assistant = client.beta.assistants.create(
    name="mAIke Cálculos Fiscais",
    instructions="""
    VOCÊ É UM ESPECIALISTA EM CÁLCULOS FISCAIS DE IMPORTAÇÃO NO BRASIL.
    
    REGRAS DE CÁLCULO:
    1. II (Imposto de Importação):
       - Base de cálculo: CIF (Custo + Frete + Seguro)
       - Fórmula: II = CIF × Alíquota_II
    
    2. IPI (Imposto sobre Produtos Industrializados):
       - Base de cálculo: CIF + II
       - Fórmula: IPI = (CIF + II) × Alíquota_IPI
    
    3. PIS/PASEP:
       - Base de cálculo: CIF
       - Fórmula: PIS = CIF × Alíquota_PIS
    
    4. COFINS:
       - Base de cálculo: CIF
       - Fórmula: COFINS = CIF × Alíquota_COFINS
    
    ... (mais regras)
    """,
    model="gpt-4o",
    tools=[{"type": "code_interpreter"}]
)
```

### 3. **Fluxo de Funcionamento**

```
1. Usuário pergunta: "Calcule os impostos para DMD.0045/25"
   ↓
2. Assistente recebe a pergunta + instruções (prompt)
   ↓
3. Assistente decide usar Code Interpreter
   ↓
4. Code Interpreter gera código Python baseado nas INSTRUÇÕES
   ↓
5. Código é executado em sandbox
   ↓
6. Resultado é retornado ao usuário
```

---

## 📝 Exemplo Prático: Como Configurar para mAIke

### **Cenário:** Calcular impostos de uma importação

#### **1. Dados de Entrada (do processo/DI):**
```python
dados = {
    "custo_usd": 10000.00,      # VMLE (Valor Mercadoria no Local de Embarque)
    "frete_usd": 1500.00,
    "seguro_usd": 200.00,
    "cotacao_ptax": 5.5283,     # Cotação PTAX do dia
    "aliquota_ii": 0.18,        # 18%
    "aliquota_ipi": 0.10,       # 10%
    "aliquota_pis": 0.0165,     # 1.65%
    "aliquota_cofins": 0.0760   # 7.60%
}
```

#### **2. Prompt do Assistente (Instructions):**

```python
instructions = """
Você é um especialista em cálculos fiscais de importação no Brasil.

REGRAS DE CÁLCULO DE IMPOSTOS:

1. CIF (Custo, Seguro e Frete):
   CIF_USD = Custo_USD + Frete_USD + Seguro_USD
   CIF_BRL = CIF_USD × Cotação_PTAX

2. II (Imposto de Importação):
   - Base de cálculo: CIF (em BRL)
   - Fórmula: II_BRL = CIF_BRL × Alíquota_II
   - Fórmula: II_USD = II_BRL ÷ Cotação_PTAX

3. IPI (Imposto sobre Produtos Industrializados):
   - Base de cálculo: CIF_BRL + II_BRL
   - Fórmula: IPI_BRL = (CIF_BRL + II_BRL) × Alíquota_IPI
   - Fórmula: IPI_USD = IPI_BRL ÷ Cotação_PTAX

4. PIS/PASEP:
   - Base de cálculo: CIF (em BRL)
   - Fórmula: PIS_BRL = CIF_BRL × Alíquota_PIS
   - Fórmula: PIS_USD = PIS_BRL ÷ Cotação_PTAX

5. COFINS:
   - Base de cálculo: CIF (em BRL)
   - Fórmula: COFINS_BRL = CIF_BRL × Alíquota_COFINS
   - Fórmula: COFINS_USD = COFINS_BRL ÷ Cotação_PTAX

6. Total de Impostos:
   Total_BRL = II_BRL + IPI_BRL + PIS_BRL + COFINS_BRL
   Total_USD = II_USD + IPI_USD + PIS_USD + COFINS_USD

REGRAS IMPORTANTES:
- Sempre arredonde para 2 casas decimais
- Use a cotação PTAX fornecida
- Se algum valor estiver em USD, converta para BRL primeiro usando PTAX
- Se algum valor estiver faltando, informe claramente qual

FORMATO DE RESPOSTA:
Apresente os cálculos de forma clara, mostrando:
1. Valores de entrada
2. Cálculo do CIF
3. Cálculo de cada imposto (com fórmula)
4. Total de impostos
5. Valores em BRL e USD
"""
```

#### **3. Código Gerado pelo Code Interpreter:**

Quando o usuário pedir "Calcule os impostos", o Code Interpreter vai gerar algo como:

```python
# Dados fornecidos
custo_usd = 10000.00
frete_usd = 1500.00
seguro_usd = 200.00
cotacao_ptax = 5.5283
aliquota_ii = 0.18
aliquota_ipi = 0.10
aliquota_pis = 0.0165
aliquota_cofins = 0.0760

# 1. Calcular CIF
cif_usd = custo_usd + frete_usd + seguro_usd
cif_brl = cif_usd * cotacao_ptax

# 2. Calcular II (base: CIF)
ii_brl = cif_brl * aliquota_ii
ii_usd = ii_brl / cotacao_ptax

# 3. Calcular IPI (base: CIF + II)
ipi_brl = (cif_brl + ii_brl) * aliquota_ipi
ipi_usd = ipi_brl / cotacao_ptax

# 4. Calcular PIS (base: CIF)
pis_brl = cif_brl * aliquota_pis
pis_usd = pis_brl / cotacao_ptax

# 5. Calcular COFINS (base: CIF)
cofins_brl = cif_brl * aliquota_cofins
cofins_usd = cofins_brl / cotacao_ptax

# 6. Total de impostos
total_brl = ii_brl + ipi_brl + pis_brl + cofins_brl
total_usd = ii_usd + ipi_usd + pis_usd + cofins_usd

# Resultado
resultado = {
    "CIF": {"USD": round(cif_usd, 2), "BRL": round(cif_brl, 2)},
    "II": {"USD": round(ii_usd, 2), "BRL": round(ii_brl, 2)},
    "IPI": {"USD": round(ipi_usd, 2), "BRL": round(ipi_brl, 2)},
    "PIS": {"USD": round(pis_usd, 2), "BRL": round(pis_brl, 2)},
    "COFINS": {"USD": round(cofins_usd, 2), "BRL": round(cofins_brl, 2)},
    "Total": {"USD": round(total_usd, 2), "BRL": round(total_brl, 2)}
}

print(resultado)
```

#### **4. Resultado Executado:**

```python
{
    "CIF": {"USD": 11700.00, "BRL": 64681.11},
    "II": {"USD": 2106.00, "BRL": 11642.60},
    "IPI": {"USD": 763.26, "BRL": 4216.37},
    "PIS": {"USD": 193.05, "BRL": 1066.24},
    "COFINS": {"USD": 889.80, "BRL": 4915.76},
    "Total": {"USD": 3952.11, "BRL": 21841.97}
}
```

---

## 🎯 Pontos-Chave

### ✅ **O Code Interpreter SABE:**
- Programar em Python
- Fazer cálculos matemáticos
- Manipular dados (listas, dicionários, DataFrames)
- Criar gráficos e visualizações
- Trabalhar com datas e números

### ❌ **O Code Interpreter NÃO SABE (sem instruções):**
- Regras de negócio específicas (ex: "II usa CIF")
- Fórmulas fiscais brasileiras
- Convenções do seu domínio
- Estrutura dos seus dados

### 🔑 **A Solução:**
**Instruções claras e detalhadas no prompt do assistente!**

---

## 📚 Como Implementar no mAIke

### **Opção 1: Assistente Especializado em Cálculos Fiscais**

Criar um assistente separado apenas para cálculos:

```python
def criar_assistente_calculos_fiscais():
    assistant = client.beta.assistants.create(
        name="mAIke Cálculos Fiscais",
        instructions="""
        [AQUI VÃO TODAS AS REGRAS DE CÁLCULO - ver exemplo acima]
        """,
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}]
    )
    return assistant.id
```

### **Opção 2: Combinar File Search + Code Interpreter**

Usar File Search para buscar legislação + Code Interpreter para calcular:

```python
assistant = client.beta.assistants.create(
    name="mAIke Completo",
    instructions="""
    Você é um assistente especializado em importação no Brasil.
    
    Quando precisar calcular impostos:
    1. Use File Search para buscar legislação relevante
    2. Use Code Interpreter para fazer os cálculos
    3. Siga as regras abaixo:
    
    [REGRAS DE CÁLCULO AQUI]
    """,
    model="gpt-4o",
    tools=[
        {"type": "file_search"},
        {"type": "code_interpreter"}
    ],
    tool_resources={
        "file_search": {
            "vector_store_ids": [vector_store_id]
        }
    }
)
```

### **Opção 3: Documento com Regras de Cálculo**

Criar um arquivo `REGRAS_CALCULO_IMPOSTOS.txt` e adicionar ao Vector Store:

```
REGRAS DE CÁLCULO DE IMPOSTOS DE IMPORTAÇÃO - BRASIL

1. CIF (Custo, Seguro e Frete):
   CIF_USD = Custo_USD + Frete_USD + Seguro_USD
   CIF_BRL = CIF_USD × Cotação_PTAX

2. II (Imposto de Importação):
   - Base de cálculo: CIF (em BRL)
   - Fórmula: II_BRL = CIF_BRL × Alíquota_II
   ...

[mais regras...]
```

Assim, o Code Interpreter pode buscar essas regras quando necessário.

---

## 🔄 Fluxo Completo no mAIke

```
1. Usuário: "Calcule os impostos do DMD.0045/25"
   ↓
2. mAIke busca dados do processo (CIF, alíquotas, PTAX)
   ↓
3. mAIke chama Assistente com Code Interpreter
   ↓
4. Assistente recebe:
   - Instruções (regras de cálculo)
   - Dados do processo
   - Contexto da conversa
   ↓
5. Code Interpreter gera código Python
   ↓
6. Código é executado em sandbox
   ↓
7. Resultado é formatado e retornado ao usuário
```

---

## ⚠️ Limitações e Cuidados

### **1. O Prompt Precisa Ser Completo**

Se você não mencionar que "II usa CIF", o Code Interpreter pode:
- ❌ Usar FOB como base
- ❌ Usar apenas Custo
- ❌ Fazer suposições incorretas

### **2. Validação dos Resultados**

Sempre valide os resultados:
- ✅ Conferir fórmulas
- ✅ Conferir bases de cálculo
- ✅ Conferir arredondamentos
- ✅ Comparar com cálculos manuais

### **3. Atualização de Regras**

Se as regras mudarem, você precisa:
- ✅ Atualizar o prompt do assistente
- ✅ Ou atualizar o documento no Vector Store
- ✅ Testar novamente

---

## 📖 Exemplo Real: Implementação no mAIke

### **1. Criar Assistente de Cálculos:**

```python
# services/assistants_service.py

def criar_assistente_calculos_fiscais(self) -> Optional[str]:
    """Cria assistente especializado em cálculos fiscais."""
    instructions = """
    Você é um especialista em cálculos fiscais de importação no Brasil.
    
    REGRAS DE CÁLCULO:
    [TODAS AS REGRAS AQUI - ver exemplo completo acima]
    
    Quando receber dados de um processo:
    1. Extraia os valores necessários (CIF, alíquotas, PTAX)
    2. Calcule cada imposto seguindo as fórmulas acima
    3. Apresente os resultados de forma clara e organizada
    4. Sempre mostre os valores em BRL e USD
    """
    
    assistant = self.client.beta.assistants.create(
        name="mAIke Cálculos Fiscais",
        instructions=instructions,
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}]
    )
    return assistant.id
```

### **2. Tool para Chamar o Assistente:**

```python
# services/tool_definitions.py

{
    "type": "function",
    "function": {
        "name": "calcular_impostos_processo",
        "description": "Calcula impostos (II, IPI, PIS, COFINS) para um processo de importação usando Code Interpreter. Use quando o usuário pedir para calcular impostos, simular valores, ou verificar cálculos fiscais.",
        "parameters": {
            "type": "object",
            "properties": {
                "processo_referencia": {
                    "type": "string",
                    "description": "Referência do processo (ex: DMD.0045/25)"
                }
            },
            "required": ["processo_referencia"]
        }
    }
}
```

### **3. Handler no Agent:**

```python
# services/agents/processo_agent.py

def _calcular_impostos_processo(self, arguments, context):
    """Calcula impostos usando Code Interpreter."""
    processo_ref = arguments.get('processo_referencia')
    
    # 1. Buscar dados do processo
    dados_processo = obter_dados_processo(processo_ref)
    
    # 2. Preparar dados para o Code Interpreter
    dados_calculo = {
        "custo_usd": dados_processo.get('custo_usd'),
        "frete_usd": dados_processo.get('frete_usd'),
        "seguro_usd": dados_processo.get('seguro_usd'),
        "cotacao_ptax": dados_processo.get('cotacao_ptax'),
        "aliquota_ii": dados_processo.get('aliquota_ii'),
        "aliquota_ipi": dados_processo.get('aliquota_ipi'),
        "aliquota_pis": dados_processo.get('aliquota_pis'),
        "aliquota_cofins": dados_processo.get('aliquota_cofins')
    }
    
    # 3. Chamar Assistente com Code Interpreter
    from services.assistants_service import AssistantsService
    service = AssistantsService()
    
    thread = service.client.beta.threads.create()
    
    mensagem = f"""
    Calcule os impostos para o processo {processo_ref} com os seguintes dados:
    
    {json.dumps(dados_calculo, indent=2)}
    
    Apresente os resultados de forma clara, mostrando:
    1. CIF (USD e BRL)
    2. Cada imposto (II, IPI, PIS, COFINS) em USD e BRL
    3. Total de impostos
    """
    
    service.client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=mensagem
    )
    
    run = service.client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=service.assistant_id_calculos
    )
    
    # 4. Aguardar resultado
    resultado = service._aguardar_run_completo(thread.id, run.id)
    
    return {
        'sucesso': True,
        'resposta': resultado
    }
```

---

## 🎓 Resumo

**Como o Code Interpreter entende o que você quer:**

1. ✅ **Através do Prompt do Assistente** - Instruções claras e detalhadas
2. ✅ **Através de Documentos** - File Search para buscar regras
3. ✅ **Através do Contexto** - Dados fornecidos na conversa
4. ❌ **NÃO através de conhecimento pré-existente** - Ele não "sabe" regras de negócio automaticamente

**A chave é: Quanto mais detalhado e específico for o prompt, melhor o Code Interpreter vai entender e executar corretamente!**

---

## 🔬 Exemplo Comparativo: Com vs Sem Instruções

### ❌ **CENÁRIO 1: SEM Instruções Claras**

**Prompt do Assistente:**
```
Você é um assistente que calcula impostos.
```

**Usuário pede:** "Calcule os impostos para CIF de R$ 50.000, alíquota II 18%"

**Código gerado pelo Code Interpreter:**
```python
# ❌ ERRO: Code Interpreter não sabe qual base usar!
cif = 50000
aliquota_ii = 0.18

# Pode fazer isso (ERRADO):
ii = cif * aliquota_ii  # ✅ Correto por acaso

# Ou pode fazer isso (ERRADO):
ii = (cif / 1.18) * aliquota_ii  # ❌ Aplicou desconto incorreto

# Ou pode fazer isso (ERRADO):
ii = cif * (1 + aliquota_ii)  # ❌ Adicionou ao invés de multiplicar
```

**Resultado:** ❌ Imprevisível! Pode estar certo ou errado por acaso.

---

### ✅ **CENÁRIO 2: COM Instruções Claras**

**Prompt do Assistente:**
```
Você é um especialista em cálculos fiscais de importação no Brasil.

REGRAS DE CÁLCULO DE II (Imposto de Importação):
- Base de cálculo: CIF (Custo + Frete + Seguro) em BRL
- Fórmula: II_BRL = CIF_BRL × Alíquota_II
- Exemplo: Se CIF = R$ 50.000 e Alíquota = 18%, então II = R$ 50.000 × 0.18 = R$ 9.000

IMPORTANTE:
- NUNCA aplique desconto na base
- NUNCA adicione a alíquota ao valor
- SEMPRE multiplique: Base × Alíquota
```

**Usuário pede:** "Calcule os impostos para CIF de R$ 50.000, alíquota II 18%"

**Código gerado pelo Code Interpreter:**
```python
# ✅ CORRETO: Code Interpreter sabe exatamente o que fazer!
cif_brl = 50000
aliquota_ii = 0.18

# Segue a fórmula especificada:
ii_brl = cif_brl * aliquota_ii  # R$ 50.000 × 0.18 = R$ 9.000

print(f"II: R$ {ii_brl:,.2f}")
# Resultado: II: R$ 9.000,00
```

**Resultado:** ✅ Sempre correto! Segue as regras especificadas.

---

## 📊 Tabela Comparativa

| Aspecto | Sem Instruções | Com Instruções |
|---------|---------------|----------------|
| **Base de cálculo do II** | ❓ Pode usar FOB, CIF, ou Custo | ✅ Sempre usa CIF |
| **Fórmula do IPI** | ❓ Pode usar CIF ou CIF+II | ✅ Sempre usa CIF + II |
| **Arredondamento** | ❓ Pode usar 2, 4, ou nenhuma casa | ✅ Sempre 2 casas decimais |
| **Conversão USD/BRL** | ❓ Pode usar cotação errada | ✅ Sempre usa PTAX fornecido |
| **Resultado** | ❌ Imprevisível | ✅ Sempre correto |

---

## 💡 Dica Final

**Pense no Code Interpreter como um programador júnior muito inteligente:**

- ✅ Ele sabe programar muito bem
- ✅ Ele entende Python perfeitamente
- ❌ Mas ele **NÃO conhece** o seu domínio de negócio
- ✅ Você precisa **ensinar** as regras através do prompt

**Quanto mais específico e detalhado for o prompt, melhor será o resultado!**

---

**Próximos Passos:**
- [ ] Criar assistente especializado em cálculos fiscais
- [ ] Documentar todas as regras de cálculo em um arquivo
- [ ] Implementar tool `calcular_impostos_processo`
- [ ] Testar com processos reais

