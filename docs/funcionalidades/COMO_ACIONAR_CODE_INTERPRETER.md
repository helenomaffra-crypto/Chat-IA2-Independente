# Como Acionar Code Interpreter

## 🔄 Fluxo Atual

### 1. Como o Usuário Usa uma Tool

**Exemplo: Cálculo de Impostos**

```
👤 Usuário: "calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283"
   ↓
🤖 IA detecta: "calcular impostos" → chama tool `calcular_impostos_ncm`
   ↓
🔧 Sistema executa: `CalculoImpostosService.calcular_impostos()` (Python local)
   ↓
📊 Retorna: Resultado formatado
```

**Código atual:**
```python
# services/tool_definitions.py
{
    "name": "calcular_impostos_ncm",
    "description": "💰💰💰 CALCULAR IMPOSTOS DE IMPORTAÇÃO...",
    "parameters": {
        "custo_usd": {"type": "number"},
        "frete_usd": {"type": "number"},
        # ...
    }
}

# services/chat_service.py
# IA detecta "calcular impostos" → chama calcular_impostos_ncm()
# → Executa CalculoImpostosService.calcular_impostos() (Python local)
```

---

## 🆕 Como Funcionaria com Code Interpreter

### Opção 1: Tool Específica para Cálculos com Code Interpreter

**Criar uma tool genérica que usa Code Interpreter:**

```python
# services/tool_definitions.py
{
    "name": "calcular_com_code_interpreter",
    "description": "🧮 CALCULAR COM CODE INTERPRETER - Use esta função quando o usuário pedir para calcular algo complexo que requer explicação passo a passo. Esta função usa Code Interpreter da OpenAI para executar cálculos em Python e retornar explicações detalhadas. Exemplos: 'calcule os impostos explicando passo a passo', 'quanto fica de imposto mostrando as fórmulas', 'calcule o CIF e explique cada etapa', 'calcule impostos com explicação detalhada'.",
    "parameters": {
        "tipo_calculo": {
            "type": "string",
            "enum": ["impostos", "cif", "frete", "outro"],
            "description": "Tipo de cálculo a realizar"
        },
        "dados": {
            "type": "object",
            "description": "Dados para o cálculo (valores, alíquotas, etc.)"
        },
        "pergunta_usuario": {
            "type": "string",
            "description": "Pergunta original do usuário para contexto"
        }
    }
}
```

**Implementação:**

```python
# services/agents/calculo_agent.py
class CalculoAgent(BaseAgent):
    def _calcular_com_code_interpreter(self, arguments, context):
        """Calcula usando Code Interpreter."""
        from services.responses_service import ResponsesService
        
        tipo_calculo = arguments.get('tipo_calculo', 'outro')
        dados = arguments.get('dados', {})
        pergunta = arguments.get('pergunta_usuario', '')
        
        # Montar prompt específico baseado no tipo
        if tipo_calculo == 'impostos':
            prompt = f"""
Calcule os impostos de importação com explicação detalhada:

Valores:
- Custo: USD {dados.get('custo_usd', 0):,.2f}
- Frete: USD {dados.get('frete_usd', 0):,.2f}
- Seguro: USD {dados.get('seguro_usd', 0):,.2f}
- Cotação PTAX: R$ {dados.get('cotacao_ptax', 0):,.4f}

Alíquotas:
- II: {dados.get('aliquotas', {}).get('ii', 0)}%
- IPI: {dados.get('aliquotas', {}).get('ipi', 0)}%
- PIS: {dados.get('aliquotas', {}).get('pis', 0)}%
- COFINS: {dados.get('aliquotas', {}).get('cofins', 0)}%

Mostre cada etapa do cálculo com fórmulas e explicações.
"""
        else:
            # Cálculo genérico
            prompt = pergunta
        
        # Chamar Code Interpreter
        responses_service = ResponsesService()
        resultado = responses_service.buscar_legislacao_com_calculo(
            pergunta=prompt,
            dados_calculo=dados
        )
        
        return {
            'sucesso': True,
            'resposta': resultado.get('resposta', ''),
            'dados': resultado
        }
```

**Como o usuário usaria:**

```
👤 Usuário: "calcule os impostos explicando passo a passo para carga de 10.000 dólares"
   ↓
🤖 IA detecta: "calcular impostos" + "explicando passo a passo" 
   → chama `calcular_com_code_interpreter`
   ↓
🔧 Sistema executa: Code Interpreter via Responses API
   ↓
📊 Retorna: Explicação detalhada com fórmulas
```

---

### Opção 2: Tool Genérica para Qualquer Cálculo

**Criar uma tool universal que aceita qualquer cálculo:**

```python
# services/tool_definitions.py
{
    "name": "executar_calculo_python",
    "description": "🐍 EXECUTAR CÁLCULO EM PYTHON - Use esta função quando o usuário pedir para calcular algo que requer código Python ou explicação detalhada. Esta função usa Code Interpreter para executar cálculos complexos e retornar explicações passo a passo. Exemplos: 'calcule X usando Python', 'quanto é Y explicando a fórmula', 'calcule Z mostrando os passos', 'faça o cálculo de W com explicação'.",
    "parameters": {
        "descricao_calculo": {
            "type": "string",
            "description": "Descrição do que o usuário quer calcular (ex: 'calcular impostos de importação', 'calcular CIF', 'calcular frete')"
        },
        "valores": {
            "type": "object",
            "description": "Valores fornecidos pelo usuário (ex: {'custo': 10000, 'frete': 1500})"
        },
        "instrucoes_especificas": {
            "type": "string",
            "description": "Instruções específicas do usuário (ex: 'mostre as fórmulas', 'explique cada passo')"
        }
    }
}
```

**Implementação:**

```python
# services/agents/calculo_agent.py
class CalculoAgent(BaseAgent):
    def _executar_calculo_python(self, arguments, context):
        """Executa cálculo genérico usando Code Interpreter."""
        from services.responses_service import ResponsesService
        
        descricao = arguments.get('descricao_calculo', '')
        valores = arguments.get('valores', {})
        instrucoes = arguments.get('instrucoes_especificas', '')
        
        # Montar prompt
        prompt = f"""
{descricao}

Valores fornecidos:
"""
        for chave, valor in valores.items():
            prompt += f"- {chave}: {valor}\n"
        
        if instrucoes:
            prompt += f"\nInstruções: {instrucoes}\n"
        
        prompt += """
Por favor:
1. Execute o cálculo usando Python
2. Mostre cada etapa do cálculo
3. Explique as fórmulas usadas
4. Apresente o resultado final de forma clara
"""
        
        # Chamar Code Interpreter
        responses_service = ResponsesService()
        resultado = responses_service.buscar_legislacao_com_calculo(
            pergunta=prompt,
            dados_calculo=valores
        )
        
        return {
            'sucesso': True,
            'resposta': resultado.get('resposta', ''),
            'dados': resultado
        }
```

**Exemplos de uso pelo usuário:**

```
👤 "calcule os impostos de importação para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283, alíquota II 18%, IPI 10%"
   → executa_calculo_python(
       descricao_calculo="calcular impostos de importação",
       valores={
           "custo_usd": 10000,
           "frete_usd": 1500,
           "seguro_usd": 200,
           "cotacao_ptax": 5.5283,
           "aliquota_ii": 18,
           "aliquota_ipi": 10
       }
   )

👤 "calcule o CIF explicando cada etapa"
   → executa_calculo_python(
       descricao_calculo="calcular CIF (Custo + Frete + Seguro)",
       valores={"custo": 10000, "frete": 1500, "seguro": 200},
       instrucoes_especificas="explique cada etapa"
   )

👤 "quanto fica de imposto se eu importar 50.000 dólares de mercadoria com frete de 5.000 e alíquota II de 14%?"
   → executa_calculo_python(
       descricao_calculo="calcular imposto de importação",
       valores={
           "custo_usd": 50000,
           "frete_usd": 5000,
           "aliquota_ii": 14
       }
   )
```

---

## 🔧 Como Acionar Code Interpreter Internamente

### Método 1: Via ResponsesService (Atual)

```python
from services.responses_service import ResponsesService

responses_service = ResponsesService()

# Com Code Interpreter habilitado
resultado = responses_service.buscar_legislacao_com_calculo(
    pergunta="Calcule os impostos...",
    dados_calculo={"custo_usd": 10000, "frete_usd": 1500}
)
```

**O que acontece internamente:**

```python
# services/responses_service.py
def buscar_legislacao_com_calculo(self, pergunta, dados_calculo):
    # 1. Preparar prompt
    input_text = pergunta + f"\n\nDados: {dados_calculo}"
    
    # 2. Chamar Responses API com Code Interpreter
    resp = self.client.responses.create(
        model="gpt-4o",
        tools=[{
            "type": "code_interpreter",  # ← AQUI aciona o Code Interpreter
            "container": {
                "type": "auto",
                "memory_limit": "1g"
            }
        }],
        instructions="Você é um assistente...",
        input=input_text
    )
    
    # 3. Retornar resposta
    return {
        'sucesso': True,
        'resposta': resp.output_text
    }
```

### Método 2: Diretamente via OpenAI Client

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv('DUIMP_AI_API_KEY'))

# Criar response com Code Interpreter
response = client.responses.create(
    model="gpt-4o",
    tools=[{
        "type": "code_interpreter",  # ← Code Interpreter habilitado
        "container": {
            "type": "auto"
        }
    }],
    instructions="Você é um assistente especializado em cálculos fiscais...",
    input="""
    Calcule os impostos de importação:
    - Custo: USD 10,000
    - Frete: USD 1,500
    - Alíquota II: 18%
    
    Mostre cada etapa do cálculo.
    """
)

print(response.output_text)
```

---

## 📋 Fluxo Completo: Do Usuário ao Code Interpreter

```
1. 👤 Usuário digita:
   "calcule os impostos explicando passo a passo para carga de 10.000 dólares"
   
2. 🤖 ChatService.processar_mensagem() recebe a mensagem
   
3. 🧠 IA (GPT-4o) analisa e decide:
   "O usuário quer calcular impostos COM explicação → usar Code Interpreter"
   → chama tool: calcular_com_code_interpreter()
   
4. 🔧 ToolRouter.route() roteia para:
   → CalculoAgent._calcular_com_code_interpreter()
   
5. 🐍 CalculoAgent monta prompt e chama:
   → ResponsesService.buscar_legislacao_com_calculo()
   
6. 📡 ResponsesService faz requisição para OpenAI:
   → client.responses.create(
       tools=[{"type": "code_interpreter"}],  # ← Code Interpreter acionado
       input="Calcule os impostos..."
   )
   
7. 🤖 OpenAI Code Interpreter:
   a) Entende o prompt
   b) Gera código Python automaticamente
   c) Executa o código em sandbox
   d) Retorna resultado + explicação
   
8. 📊 Resposta volta para o usuário:
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

## 🎯 Quando Usar Code Interpreter vs Python Local

### Use Code Interpreter quando:
- ✅ Usuário pede "explicando passo a passo"
- ✅ Usuário pede "mostrando as fórmulas"
- ✅ Cálculo complexo ou variável
- ✅ Precisa de validação automática
- ✅ Quer flexibilidade para novos tipos de cálculo

### Use Python Local quando:
- ✅ Cálculo simples e previsível
- ✅ Performance é crítica
- ✅ Não precisa de explicação
- ✅ Quer controle total

---

## 💡 Recomendação: Abordagem Híbrida

**Criar duas tools:**

1. **`calcular_impostos_ncm`** (atual) → Python Local
   - Rápido, sem custo
   - Para cálculos simples

2. **`calcular_impostos_detalhado`** (nova) → Code Interpreter
   - Com explicação passo a passo
   - Para quando usuário pedir "explicando" ou "detalhado"

**Ou uma tool única com flag:**

```python
{
    "name": "calcular_impostos_ncm",
    "parameters": {
        "incluir_explicacao_detalhada": {
            "type": "boolean",
            "description": "Se True, usa Code Interpreter para explicação detalhada"
        }
    }
}
```

---

## 🧪 Teste Prático

Veja `scripts/test_code_interpreter_calculo_impostos.py` para ver como funciona na prática.



