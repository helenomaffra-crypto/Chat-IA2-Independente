# Análise: JSON Inline em Strings de Relatórios

## 🎯 Proposta

Adicionar um JSON simples **inline** no final de cada string concatenada de relatório que indique:
- A que se refere (tipo de relatório, seção, etc.)
- Um ID único do relatório/seção
- Quando solicitado, a IA pode usar esse ID para buscar o contexto completo e gerar

**Objetivo:** Deixar o mAIke mais humanizado e sabendo de tudo que está acontecendo, sem pesar demais.

---

## 📊 Análise de Viabilidade

### ✅ **Viável? SIM**

**Razões:**
1. ✅ JSON simples é leve (~200-500 bytes por relatório)
2. ✅ Pode ser colocado em comentário HTML (não aparece na tela)
3. ✅ IA pode ler e usar quando necessário
4. ✅ Não quebra compatibilidade (strings continuam funcionando)

### ⚠️ **Performance: Precisa Cuidado**

**Impacto:**
- **Tamanho das mensagens:** +200-500 bytes por relatório (aceitável)
- **Processamento da IA:** Mínimo (IA ignora comentários HTML se não precisar)
- **Busca de contexto:** Mais rápido (IA sabe exatamente qual ID buscar)

**Otimizações possíveis:**
- Usar formato compacto (sem espaços)
- Incluir apenas metadados essenciais
- Não incluir dados completos (apenas referências)

---

## 💡 Proposta de Implementação

### Formato Sugerido

```html
<!--REPORT_META:{"tipo":"o_que_tem_hoje","id":"rel_20250112_143022","data":"2025-01-12","secoes":["alertas","dis_analise","processos_prontos"]}-->
```

**Vantagens:**
- ✅ Comentário HTML (não aparece na tela do usuário)
- ✅ Formato compacto (sem espaços)
- ✅ Apenas metadados (não dados completos)
- ✅ IA pode ler quando necessário

### Estrutura do JSON

```json
{
  "tipo": "o_que_tem_hoje" | "fechamento_dia" | "resumo_categoria",
  "id": "rel_20250112_143022",  // ID único do relatório
  "data": "2025-01-12",
  "secoes": ["alertas", "dis_analise", "processos_prontos"],  // Seções disponíveis
  "categoria": "DMD" | null,  // Se aplicável
  "filtrado": false,  // Se é relatório filtrado
  "secoes_filtradas": []  // Seções filtradas (se filtrado=true)
}
```

**Tamanho estimado:** ~150-300 bytes (compacto)

---

## 🎯 Benefícios

### 1. **IA Sabe o Que Está na Tela**
- ✅ IA pode ver que há um relatório "o_que_tem_hoje" com seções específicas
- ✅ IA pode referenciar seções específicas sem precisar buscar
- ✅ IA entende contexto visual do usuário

### 2. **Busca Mais Rápida**
- ✅ IA sabe exatamente qual ID buscar
- ✅ Não precisa fazer busca genérica no histórico
- ✅ Reduz chamadas desnecessárias ao banco

### 3. **Mais Humanizado**
- ✅ IA pode dizer "vi que você tem um relatório com X seções"
- ✅ IA pode sugerir ações baseadas no que está na tela
- ✅ IA entende melhor o contexto da conversa

### 4. **Filtros Mais Inteligentes**
- ✅ IA sabe quais seções estão disponíveis
- ✅ IA pode filtrar diretamente sem buscar JSON completo
- ✅ Reduz processamento desnecessário

---

## ⚠️ Custos e Riscos

### 1. **Tamanho das Mensagens**
- **Risco:** Aumento de ~200-500 bytes por relatório
- **Mitigação:** Formato compacto, apenas metadados essenciais
- **Impacto:** Mínimo (mensagens já são grandes)

### 2. **Complexidade do Código**
- **Risco:** Mais lógica para gerar/parsear JSON inline
- **Mitigação:** Função helper simples
- **Impacto:** Baixo (código isolado)

### 3. **IA Pode Ignorar**
- **Risco:** IA pode não usar o JSON inline
- **Mitigação:** Instruções claras no prompt + tool para buscar por ID
- **Impacto:** Médio (precisa treinar IA)

---

## 🚀 Implementação Sugerida

### Fase 1: Adicionar JSON Inline (Leve)

**Arquivo:** `services/agents/processo_agent.py`

```python
def _gerar_meta_json_inline(tipo_relatorio: str, relatorio_id: str, dados_json: Dict) -> str:
    """
    Gera JSON inline compacto para incluir no final da string do relatório.
    
    Formato: <!--REPORT_META:{"tipo":"...","id":"...","secoes":[...]}-->
    """
    meta = {
        "tipo": tipo_relatorio,
        "id": relatorio_id,
        "data": dados_json.get("data"),
        "secoes": list(dados_json.get("secoes", {}).keys()),
    }
    
    # Adicionar categoria se aplicável
    if dados_json.get("categoria"):
        meta["categoria"] = dados_json["categoria"]
    
    # Adicionar flags de filtro se aplicável
    if dados_json.get("filtrado"):
        meta["filtrado"] = True
        meta["secoes_filtradas"] = dados_json.get("secoes_filtradas", [])
    
    # Formato compacto (sem espaços)
    json_str = json.dumps(meta, separators=(',', ':'))
    return f'<!--REPORT_META:{json_str}-->'
```

**Uso:**
```python
resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)
relatorio_id = f"rel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
meta_json_inline = _gerar_meta_json_inline('o_que_tem_hoje', relatorio_id, dados_json)
resposta_com_meta = resposta + "\n" + meta_json_inline
```

### Fase 2: Tool para Buscar por ID

**Arquivo:** `services/tool_definitions.py`

```python
{
    "type": "function",
    "function": {
        "name": "buscar_relatorio_por_id",
        "description": "Busca um relatório completo por ID (obtido do JSON inline na última resposta). Use quando precisar acessar dados completos de um relatório que foi exibido anteriormente.",
        "parameters": {
            "type": "object",
            "properties": {
                "relatorio_id": {
                    "type": "string",
                    "description": "ID do relatório (ex: 'rel_20250112_143022')"
                }
            },
            "required": ["relatorio_id"]
        }
    }
}
```

### Fase 3: Instruções no Prompt

**Arquivo:** `services/prompt_builder.py`

```python
📊 RELATÓRIOS E METADADOS INLINE:
Quando um relatório é exibido, ele contém um JSON inline no final (formato: <!--REPORT_META:{...}-->).
Este JSON contém metadados sobre o relatório:
- tipo: Tipo do relatório (ex: "o_que_tem_hoje", "fechamento_dia")
- id: ID único do relatório (ex: "rel_20250112_143022")
- secoes: Lista de seções disponíveis (ex: ["alertas", "dis_analise"])
- categoria: Categoria do relatório (se aplicável)

Você pode:
1. Ler o JSON inline para entender o que está na tela
2. Usar buscar_relatorio_por_id para acessar dados completos quando necessário
3. Referenciar seções específicas sem precisar buscar o relatório completo
```

---

## 📈 Métricas de Sucesso

### Antes (Atual)
- IA não sabe o que está na tela
- Precisa buscar no histórico/banco para entender contexto
- Pode gerar relatórios duplicados

### Depois (Com JSON Inline)
- ✅ IA sabe exatamente o que está na tela
- ✅ Busca mais rápida (sabe qual ID buscar)
- ✅ Menos chamadas desnecessárias ao banco
- ✅ Respostas mais contextuais

---

## 🎯 Recomendação Final

### ✅ **IMPLEMENTAR (Fase 1 apenas)**

**Razões:**
1. ✅ Benefício alto (IA mais humanizada)
2. ✅ Custo baixo (apenas metadados, ~200 bytes)
3. ✅ Implementação simples (função helper)
4. ✅ Não quebra compatibilidade

**Fases:**
- **Fase 1 (Agora):** Adicionar JSON inline nos relatórios
- **Fase 2 (Depois):** Tool para buscar por ID (se necessário)
- **Fase 3 (Opcional):** Instruções mais detalhadas no prompt

**Não implementar:**
- ❌ Incluir dados completos no JSON inline (muito pesado)
- ❌ Fazer parse automático em todas as mensagens (desnecessário)
- ❌ Substituir sistema atual (JSON inline é complemento)

---

## 🔍 Alternativas Consideradas

### Alternativa 1: JSON Completo Inline
- ❌ **Rejeitado:** Muito pesado (5-10KB por relatório)
- ❌ **Impacto:** Aumentaria muito o tamanho das mensagens

### Alternativa 2: Apenas ID
- ⚠️ **Considerado:** Mais leve, mas menos útil
- ⚠️ **Problema:** IA não sabe quais seções estão disponíveis

### Alternativa 3: Sem JSON Inline (Atual)
- ✅ **Funciona:** Mas IA não sabe o que está na tela
- ⚠️ **Problema:** Menos humanizado, mais chamadas ao banco

---

## 📝 Conclusão

**A proposta é VIÁVEL e BENÉFICA**, desde que:
1. ✅ Use apenas metadados (não dados completos)
2. ✅ Formato compacto (sem espaços)
3. ✅ Comentário HTML (não aparece na tela)
4. ✅ Implementação incremental (Fase 1 primeiro)

**Impacto na performance:** Mínimo (~200 bytes por relatório)
**Benefício:** Alto (IA mais humanizada e contextual)

---

**Última atualização:** 12/01/2026
