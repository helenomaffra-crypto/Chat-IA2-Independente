# 🔍 Assistants API vs Embeddings - Comparação Técnica

## 📋 Visão Geral

Este documento explica as diferenças entre **Assistants API (File Search/RAG)** e **Embeddings**, e como cada um pode ser usado no contexto do mAIke.

---

## 🆚 Diferença Principal: Assistants API vs Embeddings

### **Assistants API (File Search/RAG)**

**O que é:**
- Sistema **completo e gerenciado** pela OpenAI
- Inclui: vector store, busca semântica, geração de respostas, threads persistentes
- **Tudo é feito automaticamente** pela OpenAI

**Como funciona:**
```
1. Você faz upload de arquivos → OpenAI cria embeddings automaticamente
2. Você faz uma pergunta → OpenAI busca semanticamente nos arquivos
3. OpenAI combina resultados → Gera resposta contextualizada
4. Thread persiste → Histórico automático mantido
```

**Vantagens:**
- ✅ **Zero configuração**: OpenAI gerencia tudo (embeddings, busca, indexação)
- ✅ **Threads persistentes**: Histórico automático sem você gerenciar
- ✅ **Busca automática**: OpenAI decide quais trechos são relevantes
- ✅ **Respostas contextualizadas**: OpenAI combina informações de múltiplos documentos
- ✅ **Code Interpreter**: Pode executar Python para cálculos complexos

**Desvantagens:**
- ⚠️ **Custo**: Pode ter custos adicionais (File Search + tokens)
- ⚠️ **Menos controle**: Você não controla como os embeddings são criados
- ⚠️ **Dependência**: Depende da API da OpenAI estar disponível

---

### **Embeddings (Manual)**

**O que é:**
- Você cria embeddings **manualmente** usando a API de Embeddings
- Você gerencia: criação de embeddings, armazenamento, busca, ranking
- Você implementa: lógica de busca, combinação de resultados, geração de respostas

**Como funciona:**
```
1. Você cria embeddings dos documentos → Usa OpenAI Embeddings API
2. Você armazena embeddings → No seu banco (SQLite, PostgreSQL, etc.)
3. Você faz uma pergunta → Cria embedding da pergunta
4. Você busca similaridade → Compara embedding da pergunta com embeddings dos documentos
5. Você rankeia resultados → Escolhe os mais relevantes
6. Você gera resposta → Passa trechos relevantes para o LLM
```

**Vantagens:**
- ✅ **Controle total**: Você decide como criar, armazenar e buscar embeddings
- ✅ **Custo previsível**: Apenas custo de embeddings (mais barato)
- ✅ **Offline possível**: Pode armazenar embeddings localmente
- ✅ **Customização**: Pode ajustar algoritmo de busca, ranking, etc.

**Desvantagens:**
- ⚠️ **Complexidade**: Você precisa implementar toda a lógica
- ⚠️ **Manutenção**: Você gerencia vector store, atualizações, etc.
- ⚠️ **Sem threads**: Precisa implementar histórico manualmente
- ⚠️ **Sem Code Interpreter**: Não tem execução de Python automática

---

## 📊 Comparação Detalhada

| Característica | Assistants API (File Search) | Embeddings (Manual) |
|---------------|------------------------------|---------------------|
| **Criação de Embeddings** | Automática (OpenAI) | Manual (você chama API) |
| **Armazenamento** | OpenAI (vector store) | Seu banco (SQLite, PostgreSQL, etc.) |
| **Busca Semântica** | Automática | Você implementa |
| **Ranking de Resultados** | Automático | Você implementa |
| **Geração de Resposta** | Automática | Você passa contexto para LLM |
| **Threads Persistentes** | ✅ Automático | ❌ Você implementa |
| **Code Interpreter** | ✅ Incluído | ❌ Não disponível |
| **Custo** | File Search + tokens | Apenas embeddings + tokens |
| **Controle** | Baixo (OpenAI gerencia) | Alto (você gerencia tudo) |
| **Complexidade** | Baixa (zero configuração) | Alta (implementação completa) |
| **Offline** | ❌ Precisa de API | ✅ Possível (embeddings locais) |

---

## 💡 Quando Usar Cada Um?

### **Use Assistants API (File Search) quando:**
- ✅ Você quer **zero configuração** e **zero manutenção**
- ✅ Você precisa de **threads persistentes** (histórico automático)
- ✅ Você precisa de **Code Interpreter** (cálculos complexos)
- ✅ Você não se importa com custos adicionais
- ✅ Você quer **respostas contextualizadas** automáticas

**Exemplo no mAIke:**
- Busca de legislação (já implementado)
- Cálculos fiscais complexos (futuro)
- Análises que precisam de contexto histórico

---

### **Use Embeddings (Manual) quando:**
- ✅ Você precisa de **controle total** sobre o processo
- ✅ Você quer **custos mais baixos** (apenas embeddings)
- ✅ Você precisa de **busca offline** (embeddings locais)
- ✅ Você quer **customizar** algoritmo de busca/ranking
- ✅ Você já tem infraestrutura de vector store

**Exemplo no mAIke:**
- Busca de NCM com embeddings locais (futuro)
- Busca de processos históricos com embeddings (futuro)
- Sistema híbrido (cache local + API quando necessário)

---

## 🧮 Code Interpreter - O Que É e Exemplos Práticos

### **O Que É Code Interpreter?**

**Code Interpreter** é uma funcionalidade da Assistants API que permite ao assistente **executar código Python** em um ambiente sandbox para:
- Fazer cálculos complexos
- Processar dados
- Gerar visualizações
- Analisar informações

**Como funciona:**
```
1. Usuário pergunta algo que requer cálculo
2. Assistente gera código Python automaticamente
3. OpenAI executa código em sandbox seguro
4. Assistente usa resultado para responder
5. Código é DESCARTADO (não é salvo)
```

**⚠️ IMPORTANTE:** O código gerado pelo Code Interpreter **não é salvo**. Ele é executado, o resultado é usado para responder, e então o código é descartado. Cada execução gera código novo, mesmo que a pergunta seja similar.

Para entender melhor a diferença entre Code Interpreter e um assistente de programação (como o Cursor), consulte: **`docs/CODE_INTERPRETER_VS_ASSISTENTE.md`**

---

### **Exemplos Práticos para mAIke**

#### **1. Cálculo de Impostos Complexos**

**Pergunta do usuário:**
```
"Calcule o total de impostos para uma importação de USD 10.000,00 com:
- II: 18%
- IPI: 10%
- PIS: 2,1%
- COFINS: 9,65%
- Taxa SISCOMEX: R$ 200,00
- PTAX: R$ 5,50"
```

**O que Code Interpreter faria:**
```python
# Código gerado automaticamente pelo assistente
valor_fob_usd = 10000.00
ptax = 5.50
valor_fob_brl = valor_fob_usd * ptax

ii = valor_fob_brl * 0.18
ipi = (valor_fob_brl + ii) * 0.10
pis = valor_fob_brl * 0.021
cofins = valor_fob_brl * 0.0965
taxa_siscomex = 200.00

total_impostos = ii + ipi + pis + cofins + taxa_siscomex
total_importacao = valor_fob_brl + total_impostos

print(f"Valor FOB: R$ {valor_fob_brl:,.2f}")
print(f"II (18%): R$ {ii:,.2f}")
print(f"IPI (10%): R$ {ipi:,.2f}")
print(f"PIS (2,1%): R$ {pis:,.2f}")
print(f"COFINS (9,65%): R$ {cofins:,.2f}")
print(f"Taxa SISCOMEX: R$ {taxa_siscomex:,.2f}")
print(f"Total Impostos: R$ {total_impostos:,.2f}")
print(f"Total Importação: R$ {total_importacao:,.2f}")
```

**Resultado:**
- Assistente executa código e retorna cálculo completo
- Usuário recebe resposta formatada com todos os valores

---

#### **2. Análise de Múltiplos Processos**

**Pergunta do usuário:**
```
"Analise os processos DMD.0090/25, DMD.0089/25 e DMD.0088/25:
- Qual o valor total em USD?
- Qual o valor total em BRL (usando PTAX de hoje)?
- Qual a média de impostos por processo?
- Qual processo tem maior valor de frete?"
```

**O que Code Interpreter faria:**
```python
# Código gerado automaticamente
import pandas as pd

processos = [
    {'ref': 'DMD.0090/25', 'fob_usd': 50000, 'frete_usd': 4500, 'impostos_brl': 15000},
    {'ref': 'DMD.0089/25', 'fob_usd': 30000, 'frete_usd': 3000, 'impostos_brl': 9000},
    {'ref': 'DMD.0088/25', 'fob_usd': 40000, 'frete_usd': 3500, 'impostos_brl': 12000},
]

df = pd.DataFrame(processos)
ptax = 5.50

# Cálculos
df['fob_brl'] = df['fob_usd'] * ptax
df['frete_brl'] = df['frete_usd'] * ptax
df['total_usd'] = df['fob_usd'] + df['frete_usd']
df['total_brl'] = df['fob_brl'] + df['frete_brl'] + df['impostos_brl']

# Análises
total_usd = df['total_usd'].sum()
total_brl = df['total_brl'].sum()
media_impostos = df['impostos_brl'].mean()
processo_maior_frete = df.loc[df['frete_usd'].idxmax(), 'ref']

print(f"Total USD: ${total_usd:,.2f}")
print(f"Total BRL: R$ {total_brl:,.2f}")
print(f"Média Impostos: R$ {media_impostos:,.2f}")
print(f"Processo com maior frete: {processo_maior_frete}")
```

**Resultado:**
- Assistente executa análise e retorna estatísticas completas
- Usuário recebe resposta com todos os cálculos e análises

---

#### **3. Cálculo de Impacto Cambial**

**Pergunta do usuário:**
```
"Se eu registrar a DUIMP hoje com PTAX de R$ 5,50 vs amanhã com PTAX de R$ 5,52,
qual a diferença em impostos para um FOB de USD 50.000,00 com II de 18%?"
```

**O que Code Interpreter faria:**
```python
# Código gerado automaticamente
fob_usd = 50000.00
ii_rate = 0.18

ptax_hoje = 5.50
ptax_amanha = 5.52

fob_brl_hoje = fob_usd * ptax_hoje
fob_brl_amanha = fob_usd * ptax_amanha

ii_hoje = fob_brl_hoje * ii_rate
ii_amanha = fob_brl_amanha * ii_rate

diferenca_ii = ii_amanha - ii_hoje
diferenca_percentual = (diferenca_ii / ii_hoje) * 100

print(f"FOB hoje (PTAX {ptax_hoje}): R$ {fob_brl_hoje:,.2f}")
print(f"II hoje: R$ {ii_hoje:,.2f}")
print(f"FOB amanhã (PTAX {ptax_amanha}): R$ {fob_brl_amanha:,.2f}")
print(f"II amanhã: R$ {ii_amanha:,.2f}")
print(f"Diferença: R$ {diferenca_ii:,.2f} ({diferenca_percentual:.2f}%)")
```

**Resultado:**
- Assistente calcula impacto cambial e mostra diferença
- Usuário recebe análise clara para tomar decisão

---

#### **4. Análise de Tendências**

**Pergunta do usuário:**
```
"Analise os últimos 10 processos DMD:
- Qual a média de dias entre chegada e desembaraço?
- Qual a taxa de processos com pendência de ICMS?
- Qual o valor médio de frete em USD?"
```

**O que Code Interpreter faria:**
```python
# Código gerado automaticamente
import pandas as pd
from datetime import datetime

# Dados dos processos (exemplo)
processos = [
    {'ref': 'DMD.0090/25', 'chegada': '2025-01-01', 'desembaraco': '2025-01-10', 
     'tem_icms_pendente': True, 'frete_usd': 4500},
    {'ref': 'DMD.0089/25', 'chegada': '2025-01-02', 'desembaraco': '2025-01-11',
     'tem_icms_pendente': False, 'frete_usd': 3000},
    # ... mais processos
]

df = pd.DataFrame(processos)
df['chegada'] = pd.to_datetime(df['chegada'])
df['desembaraco'] = pd.to_datetime(df['desembaraco'])
df['dias'] = (df['desembaraco'] - df['chegada']).dt.days

# Análises
media_dias = df['dias'].mean()
taxa_icms_pendente = (df['tem_icms_pendente'].sum() / len(df)) * 100
media_frete = df['frete_usd'].mean()

print(f"Média de dias (chegada → desembaraço): {media_dias:.1f} dias")
print(f"Taxa de processos com ICMS pendente: {taxa_icms_pendente:.1f}%")
print(f"Valor médio de frete: USD {media_frete:,.2f}")
```

**Resultado:**
- Assistente analisa dados e retorna estatísticas
- Usuário recebe insights sobre tendências

---

## 🔄 Comparação: Assistants API vs Embeddings para mAIke

### **Cenário 1: Busca de Legislação**

**Assistants API (atual):**
- ✅ Funciona automaticamente
- ✅ Respostas contextualizadas
- ✅ Combina múltiplas legislações
- ⚠️ Custo adicional

**Embeddings (alternativa):**
- ✅ Custo mais baixo
- ✅ Controle total
- ⚠️ Implementação complexa
- ⚠️ Sem threads persistentes

**Recomendação:** **Assistants API** (já implementado e funcionando)

---

### **Cenário 2: Cálculos Fiscais Complexos**

**Assistants API com Code Interpreter:**
- ✅ Executa Python automaticamente
- ✅ Cálculos precisos
- ✅ Pode processar múltiplos processos
- ✅ Pode gerar visualizações

**Embeddings (não aplicável):**
- ❌ Não executa código
- ❌ Apenas busca, não calcula

**Recomendação:** **Assistants API com Code Interpreter** (futuro)

---

### **Cenário 3: Busca de NCM com Cache Local**

**Assistants API:**
- ⚠️ Precisa de API sempre
- ⚠️ Custo por busca

**Embeddings (alternativa):**
- ✅ Embeddings locais (offline)
- ✅ Custo único (criação de embeddings)
- ✅ Busca rápida local

**Recomendação:** **Embeddings locais** (futuro, para cache offline)

---

## 🎯 Resumo para mAIke

### **O Que Já Temos (Assistants API):**
- ✅ Busca semântica de legislação (File Search)
- ✅ Respostas contextualizadas
- ✅ Threads persistentes (histórico automático)

### **O Que Podemos Adicionar (Code Interpreter):**
- 🚀 Cálculos fiscais complexos
- 🚀 Análises de múltiplos processos
- 🚀 Impacto cambial automatizado
- 🚀 Análises de tendências

### **O Que Podemos Adicionar (Embeddings):**
- 🚀 Cache local de NCM (offline)
- 🚀 Busca de processos históricos (offline)
- 🚀 Sistema híbrido (cache local + API)

---

## 📚 Referências

- [OpenAI Assistants API](https://platform.openai.com/docs/assistants)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [File Search (RAG) Guide](https://platform.openai.com/docs/assistants/tools/file-search)
- [Code Interpreter Guide](https://platform.openai.com/docs/assistants/tools/code-interpreter)

---

**Última atualização:** 05/01/2026

