# 🤖 Code Interpreter - Responses API (Nova API da OpenAI)

**Data:** 05/01/2026  
**Status:** ⚠️ **IMPORTANTE** - Assistants API está deprecated (desligamento: 26/08/2026)

---

## 📋 Visão Geral

A OpenAI lançou a **Responses API** como sucessora do Assistants API. O Code Interpreter agora é uma **tool** dentro desta nova API, permitindo que o modelo escreva e execute Python em um container sandbox.

### ⚠️ Mudança Crítica

- **Assistants API**: ⚠️ **DEPRECATED** - Desligamento anunciado para **26 de agosto de 2026**
- **Responses API**: ✅ **NOVA API RECOMENDADA** - Substitui Assistants API
- **Code Interpreter**: Agora é uma **tool** dentro da Responses API

---

## 🔄 Como Funciona o Fluxo

### 1. Chamada da API

```python
from openai import OpenAI
client = OpenAI()

resp = client.responses.create(
    model="gpt-4.1",
    tools=[{
        "type": "code_interpreter",
        "container": {"type": "auto", "memory_limit": "4g"}
    }],
    instructions="Quando precisar, use o python tool para calcular e checar resultados.",
    input="Calcule a solução de 3x + 11 = 14 e mostre os passos."
)

print(resp.output_text)
```

### 2. Processamento

1. **Modelo decide** (ou você força) usar o Code Interpreter
2. **Executa código** no container sandbox
3. **Pode iterar** (rodar, ver erro, corrigir e rodar novamente)
4. **Retorna resultado** com saídas (texto e referências a arquivos gerados)

### 3. Observação Importante

- Apesar de ver "Code Interpreter", o modelo geralmente "conhece" como **"python tool"**
- Nas instruções/prompt, mencione **"use the python tool"** para ser explícito

---

## 🐳 Containers: Auto vs Explícito

### Auto Mode (Recomendado)

```python
container = {
    "type": "auto",
    "memory_limit": "4g",  # 1g (padrão), 4g, 16g, 64g
    "file_ids": [...]  # Opcional: arquivos para o container
}
```

**Vantagens:**
- ✅ Plataforma cria (ou reutiliza) container automaticamente
- ✅ Associado ao contexto da conversa
- ✅ Mais simples de usar

### Modo Explícito

```python
# 1. Criar container antes
container = client.containers.create(
    memory_limit="4g"
)

# 2. Referenciar na tool config
tools=[{
    "type": "code_interpreter",
    "container": {"id": container.id}
}]
```

**Quando usar:**
- Quando precisa de controle mais fino
- Quando quer reutilizar container entre múltiplas chamadas
- Quando precisa gerenciar estado do container manualmente

---

## 📁 Arquivos: Entrada e Saída

### Entrada (Inputs)

**Opção 1: Via container (auto mode)**
```python
container = {
    "type": "auto",
    "file_ids": ["file-abc123", "file-xyz789"]
}
```

**Opção 2: Como model input**
```python
resp = client.responses.create(
    model="gpt-4.1",
    input="Analise este arquivo CSV",
    input_files=["file-abc123"]  # Automaticamente enviado para container
)
```

**Upload de arquivos globais:**
```python
# POST /v1/files (até 512 MB)
file = client.files.create(
    file=open("dados.csv", "rb"),
    purpose="code_interpreter"
)
```

### Saída (Outputs)

**Arquivos/imagens gerados:**
- Voltam como **anotações** (`container_file_citation`) na mensagem
- Para baixar: usar endpoint `retrieve container file content`

```python
# Exemplo de como acessar arquivo gerado
for annotation in resp.output_items:
    if annotation.type == "container_file_citation":
        file_content = client.containers.files.retrieve_content(
            container_id=annotation.container_id,
            file_id=annotation.file_id
        )
```

---

## 💰 Preço e Sessão

### Custo

- **Code Interpreter**: **US$ 0,03 por sessão**
- **Tokens do modelo**: Pago normalmente (o tool não substitui o custo do modelo)

### Sessão

- **Duração**: 1 hora (padrão) dentro do mesmo thread/fluxo
- **Threads diferentes**: Criam sessões separadas
- **Reutilização**: Container pode ser reutilizado dentro da mesma sessão

---

## 🎯 Uso para mAIke

### Casos de Uso Potenciais

1. **Cálculo de Impostos Complexos**
   - ✅ Já implementado via `CalculoImpostosService` (local)
   - 💡 Poderia usar Code Interpreter para cálculos mais complexos ou validações

2. **Análise de Dados de Importação**
   - Gerar gráficos de processos por categoria
   - Análise estatística de atrasos
   - Relatórios visuais

3. **Validação de Regras de Negócio**
   - Validar cálculos de impostos
   - Verificar consistência de dados
   - Gerar relatórios de auditoria

4. **Processamento de Arquivos**
   - Analisar planilhas Excel de importação
   - Processar PDFs de documentos
   - Gerar relatórios em múltiplos formatos

### Comparação: Code Interpreter vs Implementação Atual

| Funcionalidade | Implementação Atual | Code Interpreter |
|---------------|---------------------|------------------|
| Cálculo de Impostos | ✅ `CalculoImpostosService` (local) | 💡 Poderia usar para validação |
| Análise de Dados | ✅ SQL queries + formatação | 💡 Poderia gerar gráficos |
| Processamento de Arquivos | ⚠️ Limitado | ✅ Excelente suporte |
| Custo | ✅ Gratuito (local) | ⚠️ US$ 0,03/sessão |
| Performance | ✅ Rápido (local) | ⚠️ Pode ser mais lento |
| Flexibilidade | ⚠️ Código fixo | ✅ Código dinâmico |

---

## ⚠️ Migração de Assistants API para Responses API

### Status Atual do Sistema

O sistema atual usa **Assistants API** para:
- ✅ Busca de legislação com File Search (RAG)
- ✅ Vector stores para documentos

### Plano de Migração (Futuro)

**⚠️ IMPORTANTE:** Assistants API será desligado em **26 de agosto de 2026**

**O que precisa ser migrado:**
1. **File Search para legislação**
   - Atualmente: `AssistantsService` usa `client.beta.assistants`
   - Futuro: Migrar para Responses API com File Search tool

2. **Vector Stores**
   - Atualmente: Criados via `client.vector_stores`
   - Futuro: Verificar como funciona na Responses API

**Arquivos afetados:**
- `services/assistants_service.py` - Serviço principal
- `scripts/configurar_assistants_legislacao.py` - Script de configuração
- `services/agents/legislacao_agent.py` - Handler da tool

### Recomendação

- ✅ **Manter Assistants API** por enquanto (funciona até 08/2026)
- ⚠️ **Planejar migração** para Responses API em 2026
- 💡 **Monitorar atualizações** da OpenAI sobre migração

---

## 📝 Exemplo Prático: Cálculo de Impostos com Code Interpreter

### Implementação Atual (Local)

```python
# services/calculo_impostos_service.py
def calcular_impostos(self, custo_usd, frete_usd, seguro_usd, cotacao_ptax, aliquotas):
    # Cálculo local, rápido, sem custo
    cif_usd = custo_usd + frete_usd + seguro_usd
    ii_brl = cif_brl * (aliquotas['ii'] / 100.0)
    # ...
```

### Possível Implementação com Code Interpreter

```python
# Exemplo conceitual (não implementado)
resp = client.responses.create(
    model="gpt-4.1",
    tools=[{
        "type": "code_interpreter",
        "container": {"type": "auto", "memory_limit": "1g"}
    }],
    instructions="""Você é um especialista em cálculo de impostos de importação.
    Use o python tool para calcular impostos quando necessário.
    Sempre valide os cálculos e mostre os passos.""",
    input=f"""
    Calcule os impostos de importação:
    - Custo: USD {custo_usd}
    - Frete: USD {frete_usd}
    - Seguro: USD {seguro_usd}
    - Cotação PTAX: {cotacao_ptax}
    - Alíquotas: II={aliquotas['ii']}%, IPI={aliquotas['ipi']}%, PIS={aliquotas['pis']}%, COFINS={aliquotas['cofins']}%
    
    Mostre todos os passos e valide os resultados.
    """
)
```

**Vantagens:**
- ✅ Validação automática
- ✅ Explicação passo a passo
- ✅ Flexível para casos complexos

**Desvantagens:**
- ⚠️ Custo: US$ 0,03 por sessão
- ⚠️ Latência: Mais lento que cálculo local
- ⚠️ Dependência: Requer conexão com OpenAI

---

## 🔍 Quando Usar Code Interpreter vs Implementação Local

### Use Code Interpreter quando:

- ✅ Precisa de **validação complexa** de cálculos
- ✅ Precisa **gerar gráficos** ou visualizações
- ✅ Precisa **processar arquivos** grandes (CSV, Excel)
- ✅ Precisa de **análise estatística** avançada
- ✅ Precisa de **código dinâmico** (regras variam)

### Use Implementação Local quando:

- ✅ Cálculos são **simples e diretos** (como impostos básicos)
- ✅ Precisa de **performance máxima** (sem latência de API)
- ✅ Precisa **evitar custos** (cálculos frequentes)
- ✅ Regras são **fixas e bem definidas** (como bases de cálculo)

---

## 📚 Referências

- [OpenAI Responses API Documentation](https://platform.openai.com/docs/api-reference/responses)
- [Code Interpreter Guide](https://platform.openai.com/docs/guides/code-interpreter)
- [Assistants API Deprecation Notice](https://platform.openai.com/docs/assistants/migration)

---

## 🧪 Testar Responses API

### Script de Teste

Execute o script de teste para validar a Responses API:

```bash
python scripts/test_responses_api.py
```

**O script testa:**
1. ✅ Cálculo básico (equação simples)
2. ✅ Cálculo de impostos (exemplo prático para mAIke)
3. ⏭️ Processamento de arquivo (opcional)
4. ⏭️ Container explícito (reutilização)
5. ✅ Tratamento de erros e iteração

**Requisitos:**
- `DUIMP_AI_API_KEY` ou `OPENAI_API_KEY` configurado no `.env`
- Biblioteca `openai` instalada (`pip install openai`)

**Exemplo de saída:**
```
================================================================================
  TESTE DE RESPONSES API (Nova API da OpenAI)
================================================================================

✅ API Key configurada: sk-proj-...
✅ Cliente OpenAI inicializado

🚀 Iniciando testes...

================================================================================
  TESTE 1: Cálculo Básico
================================================================================

📝 Testando: Resolver equação 3x + 11 = 14
...
```

---

## ⚠️ Ações Recomendadas

1. **Curto Prazo (2025):**
   - ✅ Manter Assistants API funcionando
   - ✅ Monitorar atualizações da OpenAI
   - ✅ Documentar dependências do Assistants API
   - ✅ **Testar Responses API** com `scripts/test_responses_api.py`

2. **Médio Prazo (2026 - antes de 08/2026):**
   - ⚠️ Planejar migração para Responses API
   - ⚠️ Testar File Search na nova API
   - ⚠️ Avaliar custos e performance
   - ⚠️ Implementar migração gradual

3. **Longo Prazo:**
   - 💡 Considerar Code Interpreter para casos específicos
   - 💡 Manter implementação local para casos simples
   - 💡 Abordagem híbrida (local + Code Interpreter quando necessário)

---

**Última atualização:** 05/01/2026

