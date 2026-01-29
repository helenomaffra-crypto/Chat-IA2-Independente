# 📊 Melhoria: Relatórios em JSON (Deixar IA Humanizar)

**Data:** 09/01/2026  
**Status:** 💡 **PROPOSTA** - Aguardando implementação após refatoração do `chat_service`

---

## 🎯 Problema Atual

### **Situação:**
Os relatórios "O QUE TEMOS PRA HOJE" e "FECHAMENTO DO DIA" são formatados usando **concatenação de strings** manual (`resposta += f"..."`).

### **Exemplo do Código Atual:**

```python
# services/agents/processo_agent.py (linhas ~5132-5500+)
def _formatar_dashboard_hoje(...) -> str:
    resposta = f"📅 **O QUE TEMOS PRA HOJE"
    if categoria:
        resposta += f" - {categoria.upper()}"
    resposta += f" - {hoje}**\n\n"
    resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Processos chegando hoje
    resposta += f"🚢 **CHEGANDO HOJE** ({len(processos_chegando)} processo(s))\n\n"
    for proc in processos_chegando:
        resposta += f"   • **{proc['processo_referencia']}**"
        if proc.get('porto_nome'):
            resposta += f" - Porto: {proc['porto_nome']}"
        # ... mais 700+ linhas de formatação manual
```

### **Problemas:**
1. ❌ **~700+ linhas** só de formatação (difícil manter)
2. ❌ **Formato fixo** (não se adapta ao contexto)
3. ❌ **Não usa IA** para humanizar/naturalizar
4. ❌ **Dados já vêm estruturados** (dicionários/listas) mas são "achatados" em texto

---

## ✅ Proposta: JSON + IA Humaniza

### **Nova Abordagem:**

1. **Queries SQL → Dados Estruturados (JSON)**
   - ✅ Dados já vêm estruturados do banco (isso já está correto)
   - ✅ Retornar JSON em vez de formatar em string

2. **Passar JSON para IA**
   - ✅ IA recebe dados estruturados
   - ✅ IA formata/humaniza conforme contexto

3. **Resultado:**
   - ✅ Mais natural e conversacional
   - ✅ Formato adaptável (pode variar conforme necessidade)
   - ✅ Código mais simples (elimina ~700 linhas de formatação)

### **Exemplo Proposto:**

#### **Antes (Atual):**
```python
def _obter_dashboard_hoje(...) -> Dict[str, Any]:
    # Buscar dados
    processos_chegando = [...]
    processos_prontos = [...]
    # ...
    
    # ❌ Formatar manualmente (700+ linhas)
    resposta_formatada = self._formatar_dashboard_hoje(
        processos_chegando, processos_prontos, ...
    )
    
    return {
        'resposta': resposta_formatada,  # String já formatada
        'sucesso': True
    }
```

#### **Depois (Proposto):**
```python
def _obter_dashboard_hoje(...) -> Dict[str, Any]:
    # Buscar dados (igual)
    processos_chegando = [...]
    processos_prontos = [...]
    # ...
    
    # ✅ Retornar JSON estruturado
    dados_estruturados = {
        'tipo_relatorio': 'dashboard_hoje',
        'data': '2026-01-09',
        'categoria': categoria,
        'secoes': {
            'processos_chegando': processos_chegando,
            'processos_prontos': processos_prontos,
            'pendencias': pendencias,
            # ...
        },
        'resumo': {
            'total_chegando': len(processos_chegando),
            'total_prontos': len(processos_prontos),
            # ...
        }
    }
    
    return {
        'dados_estruturados': dados_estruturados,  # ✅ JSON
        'precisa_formatar': True,  # Flag para IA formatar
        'sucesso': True
    }
```

#### **IA Recebe e Formata:**
```python
# No chat_service ou MessageProcessingService
if resultado.get('precisa_formatar'):
    # Passar JSON para IA formatar
    prompt_formatacao = f"""
    Formate o seguinte relatório de forma natural e conversacional:
    
    {json.dumps(dados_estruturados, indent=2, ensure_ascii=False)}
    
    Use emojis quando apropriado, organize por seções claras,
    e humanize a linguagem (não seja robótico).
    """
    
    resposta_formatada = ai_service.chat_completion(...)
```

---

## 🎯 Benefícios

### **1. Código Mais Simples**
- ✅ Elimina ~700 linhas de formatação manual
- ✅ Menos código = menos bugs
- ✅ Mais fácil de manter

### **2. Mais Flexível**
- ✅ IA pode adaptar formato conforme contexto
- ✅ Pode variar estilo (formal, informal, resumido, detalhado)
- ✅ Pode priorizar informações importantes

### **3. Mais Natural**
- ✅ IA humaniza melhor que templates fixos
- ✅ Linguagem mais conversacional
- ✅ Pode adaptar tom conforme situação

### **4. Dados Já Estruturados**
- ✅ Não precisa "achatar" dados em strings
- ✅ Mantém estrutura original
- ✅ Facilita testes e validações

---

## 📋 Quando Implementar

### **Momento Ideal:**
**Após refatoração do `chat_service`** (Passos 3.5 e 4 completos)

### **Por quê?**
1. ✅ Refatoração do `chat_service` já vai mexer em muitos lugares
2. ✅ Melhor fazer uma mudança de cada vez
3. ✅ Depois do refatoramento, código estará mais organizado
4. ✅ Facilita implementação sem quebrar funcionalidades

### **Plano de Implementação (Futuro):**

#### **Fase 1: Preparar Estrutura JSON**
- [ ] Modificar `_obter_dashboard_hoje()` para retornar JSON em vez de string
- [ ] Modificar `_fechar_dia()` para retornar JSON em vez de string
- [ ] Manter método `_formatar_*` antigo como fallback temporário

#### **Fase 2: Integrar com IA**
- [ ] Criar método `_formatar_relatorio_com_ia(dados_json)`
- [ ] Modificar `chat_service` para detectar `precisa_formatar=True`
- [ ] Passar JSON para IA formatar quando necessário

#### **Fase 3: Remover Formatação Manual**
- [ ] Remover métodos `_formatar_dashboard_hoje()` e `_formatar_fechamento_dia()`
- [ ] Testar que tudo funciona
- [ ] Validar qualidade da formatação da IA

---

## 🎨 Exemplo de Resultado Esperado

### **Antes (Formatação Manual - Robótico):**
```
📅 **O QUE TEMOS PRA HOJE - 09/01/2026**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚢 **CHEGANDO HOJE** (1 processo(s))

   **DMD** (1 processo(s)):
      • **DMD.0089/25** - Porto: RIO DE JANEIRO - ETA: 2026-01-09 (previsto) - Status: MANIFESTADA - Modal: Marítimo
```

### **Depois (IA Humaniza - Natural):**
```
📅 O que temos pra hoje - 09/01/2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚢 Chegando hoje

Temos 1 processo chegando hoje:

**DMD (1 processo):**
• DMD.0089/25
  - Porto: Rio de Janeiro
  - ETA: 09/01/2026 (previsto)
  - Status: Manifestada
  - Modal: Marítimo

Este processo está aguardando desembaraço.
```

**Diferenças:**
- ✅ Mais natural e conversacional
- ✅ Formatação mais limpa
- ✅ Pode adaptar conforme contexto
- ✅ Pode adicionar insights (ex: "Este processo está aguardando desembaraço")

---

## ⚠️ Considerações

### **1. Consistência**
- ⚠️ IA pode formatar diferente a cada vez
- ✅ **Solução:** Usar prompt com exemplos específicos de formato desejado
- ✅ **Solução:** Validar formato mínimo (seções obrigatórias)

### **2. Custos**
- ⚠️ Usar IA para formatar custa tokens
- ✅ **Solução:** Cachear relatórios formatados
- ✅ **Solução:** Formatar apenas quando necessário (não sempre)

### **3. Testes**
- ⚠️ Formatação variável dificulta testes automatizados
- ✅ **Solução:** Testar estrutura JSON (dados corretos)
- ✅ **Solução:** Testar formato mínimo (golden tests com exemplos)

---

## 📝 Notas Técnicas

### **Não Usamos Regex Atualmente**
- ✅ Correto: Dados vêm estruturados do banco (dicionários/listas)
- ✅ Não há regex para extrair dados (só formatação manual)
- ✅ JSON já é o formato natural dos dados

### **Regex vs JSON**
- ❌ **Regex:** Extrair dados de texto não estruturado (não é nosso caso)
- ✅ **JSON:** Dados já estruturados → passar para IA → IA formata

### **Por que JSON é Melhor:**
1. Dados já vêm estruturados do SQL
2. Não precisa "achatar" em strings
3. IA pode entender melhor estrutura
4. Facilita testes e validações
5. Mais flexível para mudanças futuras

---

## 🎯 Conclusão

**Sua sugestão está 100% correta!** 🎯

Usar JSON e deixar a IA humanizar é a abordagem certa. Mas faz sentido fazer **depois** do refatoramento do `chat_service` porque:

1. ✅ Menos risco de quebrar funcionalidades
2. ✅ Código estará mais organizado
3. ✅ Facilita implementação
4. ✅ Uma mudança de cada vez

**Sugestão:** Implementar essa melhoria como **"Passo 6"** (após completar refatoração do `chat_service`).

---

**Última atualização:** 09/01/2026
