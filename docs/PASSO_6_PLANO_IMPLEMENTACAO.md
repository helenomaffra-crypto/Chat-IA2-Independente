# 📋 Passo 6: Relatórios em JSON - Plano de Implementação

**Data:** 10/01/2026  
**Status:** 🔄 **EM PLANEJAMENTO** - Pronto para implementação

---

## 🎯 Objetivo

Converter relatórios "O QUE TEMOS PRA HOJE" e "FECHAMENTO DO DIA" de strings concatenadas para JSON estruturado, permitindo que a IA formate/humanize os relatórios de forma flexível e eliminando a necessidade de regex para detectar tipo.

**Benefícios:**
- ✅ Resolve problema de detecção de tipo (sem regex frágil)
- ✅ Elimina ~700 linhas de formatação manual
- ✅ Permite ajustar formato depois (similar ao "melhore o email")
- ✅ Tipo sempre explícito no JSON (nunca ambíguo)

---

## 📋 Plano de Implementação Incremental

### **Fase 1: Preparar Estrutura JSON (SEGURA)** ✅ **CONCLUÍDA**

**Status:** ✅ **IMPLEMENTADO E TESTADO** (10/01/2026)

**Objetivo:** Modificar métodos para retornar JSON mantendo formatação antiga como fallback.

#### 1.1 Modificar `_obter_dashboard_hoje()` ✅ **CONCLUÍDO**

**Localização:** `services/agents/processo_agent.py` (linha ~5036)

**O que foi feito:**
- ✅ Método modificado para retornar JSON estruturado além da string formatada
- ✅ JSON incluído no retorno como `dados_json` com estrutura completa
- ✅ JSON também incluído no `meta_json` ao salvar relatório
- ✅ Estrutura JSON implementada:
  ```python
  {
      'tipo_relatorio': 'o_que_tem_hoje',
      'data': '2026-01-10',
      'categoria': categoria,
      'secoes': {
          'processos_chegando': [...],
          'processos_prontos': [...],
          'processos_em_dta': [...],
          'pendencias': [...],
          'duimps_analise': [...],
          'dis_analise': [...],
          'eta_alterado': [...],
          'alertas': [...]
      },
      'resumo': {
          'total_chegando': len(processos_chegando),
          'total_prontos': len(processos_prontos),
          # ...
      }
  }
  ```
- Manter `_formatar_dashboard_hoje()` funcionando (não remover ainda)
- Retornar tanto JSON quanto string formatada no dict de resposta

#### 1.2 Modificar `_fechar_dia()` ✅ **CONCLUÍDO**

**Localização:** `services/agents/processo_agent.py` (linha ~6064)

**O que foi feito:**
- ✅ Método modificado para retornar JSON estruturado além da string formatada
- ✅ JSON incluído no retorno como `dados_json` com estrutura completa
- ✅ JSON também incluído no `meta_json` ao salvar relatório
- ✅ Estrutura JSON implementada:
  ```python
  {
      'tipo_relatorio': 'fechamento_dia',
      'data': '2026-01-10',
      'categoria': categoria,
      'secoes': {
          'processos_chegaram': [...],
          'processos_desembaracados': [...],
          'total_movimentacoes': total
      },
      'resumo': {
          'total_chegando': len(processos_chegaram),
          'total_desembaracados': len(processos_desembaracados),
          # ...
      }
  }
  ```
- Manter `_formatar_fechamento_dia()` funcionando (não remover ainda)
- Retornar tanto JSON quanto string formatada no dict de resposta

**Validação Fase 1:**
- ✅ Código compila sem erros
- ✅ JSON estruturado sendo retornado com `tipo_relatorio` explícito
- ✅ String formatada mantida para compatibilidade
- ✅ JSON incluído no `meta_json` ao salvar relatório
- ⏳ **PENDENTE:** Teste funcional completo (verificar que relatórios continuam sendo exibidos corretamente)

**Arquivos Modificados:**
- `services/agents/processo_agent.py`:
  - `_obter_dashboard_hoje()`: Adicionado `dados_json` no retorno (linha ~5110)
  - `_fechar_dia()`: Adicionado `dados_json` no retorno (linha ~6148)
  - Ambos incluem `tipo_relatorio` explícito no JSON

---

### **Fase 2: Integrar com IA (TESTE)**

**Objetivo:** Criar método para formatar relatórios com IA quando necessário.

#### 2.1 Criar `_formatar_relatorio_com_ia(dados_json)` ✅

**Localização:** Criar em `services/agents/processo_agent.py` ou novo arquivo `services/relatorio_formatter_service.py`

**O que fazer:**
- Receber JSON estruturado
- Construir prompt para IA formatar
- Passar JSON para IA com instruções de formatação
- Retornar string formatada pela IA

**Prompt sugerido:**
```python
prompt = f"""
Formate o seguinte relatório de forma natural e conversacional:

{json.dumps(dados_json, indent=2, ensure_ascii=False)}

Instruções:
- Use emojis quando apropriado (📅, 🚢, ✅, ⚠️, etc.)
- Organize por seções claras
- Humanize a linguagem (não seja robótico)
- Formate datas em português (DD/MM/YYYY)
- Mantenha informações importantes mas seja natural
- Tipo de relatório: {dados_json['tipo_relatorio']}
"""
```

#### 2.2 Modificar ChatService para detectar JSON

**Localização:** `services/chat_service.py`

**O que fazer:**
- Detectar se resultado de tool tem `dados_json` ou `precisa_formatar`
- Se sim, chamar `_formatar_relatorio_com_ia()` em vez de usar string formatada
- Manter fallback para string formatada se JSON não disponível

**Validação Fase 2:**
- ✅ Testar formatação com IA funciona corretamente
- ✅ Validar qualidade da formatação
- ✅ Comparar com formatação manual
- ✅ Testar fallback quando IA não disponível

---

### **Fase 3: Usar JSON como Fonte da Verdade (CONSOLIDAÇÃO)**

**Objetivo:** Passar a usar JSON como fonte da verdade, eliminando regex para detectar tipo.

#### 3.1 Modificar salvamento de relatórios

**Localização:** `services/report_service.py` e `services/chat_service.py`

**O que fazer:**
- Salvar JSON estruturado no contexto quando relatório for gerado
- Usar `tipo_relatorio` do JSON diretamente (sem regex)
- Modificar detecção de "esse relatório" para buscar tipo do JSON

#### 3.2 Atualizar detecção de tipo em `chat_service.py`

**Localização:** `services/chat_service.py` (linhas ~2118-2130)

**O que fazer:**
- Remover regex: `if 'FECHAMENTO DO DIA' in texto.upper()`
- Usar tipo do JSON: `tipo = dados_json.get('tipo_relatorio')`
- Garantir que tipo sempre vem do JSON (nunca regex)

**Validação Fase 3:**
- ✅ Testar que tipo é detectado corretamente do JSON
- ✅ Validar que "esse fechamento" funciona corretamente
- ✅ Validar que "esse relatório" funciona corretamente
- ✅ Garantir que nunca confunde tipos

---

### **Fase 4: Remover Formatação Manual (LIMPEZA)**

**Objetivo:** Remover métodos de formatação manual após validação completa.

#### 4.1 Remover métodos antigos

**Localização:** `services/agents/processo_agent.py`

**O que fazer:**
- Remover `_formatar_dashboard_hoje()` (700+ linhas)
- Remover `_formatar_fechamento_dia()` (~300 linhas)
- Limpar código não utilizado

#### 4.2 Limpar regex de detecção

**Localização:** `services/chat_service.py`, `services/email_precheck_service.py`

**O que fazer:**
- Remover todas as regex de detecção de tipo
- Garantir que sempre usa tipo do JSON

**Validação Fase 4:**
- ✅ Testar que tudo funciona sem métodos antigos
- ✅ Validar que não há código morto
- ✅ Verificar que linhas foram reduzidas (~1000 linhas)

---

## 🎯 Implementação Recomendada: Fase por Fase

**Abordagem:** Implementar uma fase de cada vez, validando antes de prosseguir.

**Sequência sugerida:**
1. ✅ **Fase 1** (SEGURA) - Retornar JSON junto com string (mantém compatibilidade)
2. ⏳ **Fase 2** (TESTE) - Criar formatação com IA e testar
3. ⏳ **Fase 3** (CONSOLIDAÇÃO) - Usar JSON como fonte da verdade
4. ⏳ **Fase 4** (LIMPEZA) - Remover código antigo

**Critério para avançar:**
- Cada fase deve estar funcionando e testada antes de prosseguir
- Se houver problemas, corrigir antes de avançar
- Manter fallback sempre disponível até Fase 4

---

## 📊 Estimativa de Impacto

**Linhas reduzidas:**
- `_formatar_dashboard_hoje()`: ~700 linhas
- `_formatar_fechamento_dia()`: ~300 linhas
- Regex de detecção: ~50 linhas
- **Total: ~1050 linhas eliminadas**

**Problemas resolvidos:**
- ✅ Detecção de tipo sempre correta (sem regex)
- ✅ Nunca confunde "fechamento" com "o que temos"
- ✅ Formatação flexível (pode ajustar depois)
- ✅ Código mais simples e manutenível

---

## ⚠️ Riscos e Mitigações

### **Risco 1: IA formata diferente a cada vez**
**Mitigação:** 
- Usar prompt com exemplos específicos
- Validar formato mínimo (seções obrigatórias)
- Opcionalmente cachear formatação

### **Risco 2: Custo de tokens para formatação**
**Mitigação:**
- Cachear relatórios formatados
- Formatar apenas quando necessário (flag `precisa_formatar`)
- Usar modelo mais barato para formatação (gpt-4o-mini)

### **Risco 3: Quebra de funcionalidades existentes**
**Mitigação:**
- Implementar incremental (uma fase de cada vez)
- Manter fallback sempre disponível até Fase 4
- Testar cada fase antes de avançar

---

## ✅ Checklist de Implementação

### **Fase 1: Preparar Estrutura JSON** ✅ **CONCLUÍDA**
- [x] Modificar `_obter_dashboard_hoje()` para retornar JSON
- [x] Modificar `_fechar_dia()` para retornar JSON
- [x] Validar que JSON está sendo retornado corretamente
- [ ] Testar que relatórios continuam sendo exibidos (teste funcional pendente)

### **Fase 2: Integrar com IA**
- [ ] Criar `_formatar_relatorio_com_ia(dados_json)`
- [ ] Modificar ChatService para usar formatação com IA
- [ ] Testar formatação com IA funciona
- [ ] Validar qualidade da formatação

### **Fase 3: Usar JSON como Fonte da Verdade**
- [ ] Modificar salvamento de relatórios para usar JSON
- [ ] Atualizar detecção de tipo para usar JSON (sem regex)
- [ ] Testar detecção de tipo funciona corretamente
- [ ] Validar que nunca confunde tipos

### **Fase 4: Remover Formatação Manual**
- [ ] Remover `_formatar_dashboard_hoje()`
- [ ] Remover `_formatar_fechamento_dia()`
- [ ] Remover regex de detecção
- [ ] Validar que tudo funciona sem código antigo

---

**Última atualização:** 10/01/2026
