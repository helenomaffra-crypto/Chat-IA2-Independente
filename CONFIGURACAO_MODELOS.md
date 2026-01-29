# 🧠 Configuração de Modelos GPT

## 📋 Onde Configurar Cada Modelo

### 1. **Chat Principal** (Conversas com o usuário - operações com tools)
```bash
OPENAI_MODEL_DEFAULT=gpt-4o  # ← Operações com tools (rápido e barato)
```
**Uso:** Maioria das conversas do mAIke (quando há tool calls)
**Impacto:** Operações rápidas e econômicas com processos, NCM, documentos

### 2. **Conhecimento Geral** (Respostas sem tools - conhecimento do modelo)
```bash
OPENAI_MODEL_CONHECIMENTO_GERAL=gpt-5.1  # ← Conhecimento geral (mais atualizado)
```
**Uso:** Perguntas de conhecimento geral que não usam tools
**Exemplos:**
- "qual a cotação de frete de um container de 20 da china pro brasil?"
- "explique sobre multas em importação" (sem mencionar legislação específica)
- "como funciona o processo de importação?"
- "qual a diferença entre DI e DUIMP?"

**Impacto:** Respostas mais atualizadas e precisas para conhecimento geral

### 3. **Consultas Analíticas/BI**
```bash
OPENAI_MODEL_ANALITICO=gpt-4o  # ← Análises e relatórios
```
**Uso:** Consultas complexas, relatórios, análises de dados
**Impacto:** Melhora qualidade de análises e insights

---

## 🎯 Estratégia Híbrida (Recomendada)

**✅ NOVO: Sistema detecta automaticamente o tipo de pergunta e escolhe o modelo apropriado:**

```bash
# No arquivo .env
OPENAI_MODEL_DEFAULT=gpt-4o                    # ← Operações com tools (padrão)
OPENAI_MODEL_CONHECIMENTO_GERAL=gpt-5.1        # ← Conhecimento geral (GPT-5)
OPENAI_MODEL_ANALITICO=gpt-4o                  # ← Análises (opcional)
```

### Como Funciona:

1. **Pergunta sobre processo/NCM/documento** → Usa `OPENAI_MODEL_DEFAULT` (GPT-4o)
   - Exemplo: "situacao do gym.0047/25" → Usa GPT-4o (rápido, barato)
   
2. **Pergunta de conhecimento geral** → Usa `OPENAI_MODEL_CONHECIMENTO_GERAL` (GPT-5.1)
   - Exemplo: "qual a cotação de frete?" → Usa GPT-5.1 (mais atualizado)
   
3. **Pergunta analítica/BI** → Usa `OPENAI_MODEL_ANALITICO` (GPT-4o)
   - Exemplo: "top 10 processos por valor CIF" → Usa GPT-4o

### Vantagens:

✅ **Otimização de custo:** GPT-5 só é usado quando necessário (conhecimento geral)
✅ **Performance:** GPT-4o é mais rápido para operações com tools
✅ **Atualização:** GPT-5 tem conhecimento mais recente para perguntas gerais
✅ **Automático:** Sistema detecta automaticamente o tipo de pergunta

---

## 📊 Estratégia Atual

**Configuração padrão (se não especificar no .env):**
- `OPENAI_MODEL_DEFAULT`: `gpt-4o` (operacional)
- `OPENAI_MODEL_CONHECIMENTO_GERAL`: `gpt-5.1` (conhecimento geral)
- `OPENAI_MODEL_ANALITICO`: `gpt-4o` (analítico)

**Recomendação:**
- Manter `OPENAI_MODEL_DEFAULT=gpt-4o` para operações (maioria dos casos)
- Configurar `OPENAI_MODEL_CONHECIMENTO_GERAL=gpt-5.1` para conhecimento geral
- Ajustar conforme necessidade de custo vs. qualidade

---

## 💡 Dica

O modelo mais importante para melhorar a inteligência do chat é o **`OPENAI_MODEL_DEFAULT`**, pois é ele que processa todas as conversas principais com o usuário.
