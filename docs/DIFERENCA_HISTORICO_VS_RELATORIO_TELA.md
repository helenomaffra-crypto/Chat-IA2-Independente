# Diferença: Último Histórico vs. Último Relatório em Tela

## 📊 Conceitos

### 1. **Último Histórico** (Última Mensagem do Histórico)

**O que é:**
- Última mensagem/resposta do histórico de conversas armazenado no banco (`conversas_chat`)
- Pode ser **qualquer tipo de resposta**: notificação, resposta de processo, consulta de NCM, etc.

**Características:**
- ❌ **Não é confiável** para identificar o que está na tela
- ❌ Pode ser uma notificação curta (ex: "✅ Processo ALH.0166/25 atualizado")
- ❌ Pode ser uma resposta de consulta (ex: "O processo ALH.0166/25 está...")
- ❌ Pode ser uma resposta de NCM (ex: "A alíquota do NCM 1234.56.78 é...")
- ❌ **Não representa necessariamente o que está visível na tela**

**Exemplo:**
```
Histórico de conversas:
1. Usuário: "o que temos pra hoje?"
   IA: [RELATÓRIO COMPLETO - 5000 caracteres]
   
2. Usuário: "como está o ALH.0166/25?"
   IA: "O processo ALH.0166/25 está em análise..." [ÚLTIMA MENSAGEM DO HISTÓRICO]
   
3. Usuário: "envie esse relatorio por email"
   ❌ PROBLEMA: Se usar último histórico, vai enviar a resposta do processo, não o relatório!
```

---

### 2. **Último Relatório em Tela** (Relatório Salvo)

**O que é:**
- Relatório que foi **gerado e exibido na tela** e **salvo no contexto da sessão**
- Armazenado em `contexto_sessao` com `tipo_contexto='ultimo_relatorio'`
- Representa o que **realmente está visível** na tela do usuário

**Características:**
- ✅ **É confiável** para identificar o que está na tela
- ✅ Sempre é um relatório completo (ex: "O QUE TEMOS PRA HOJE?", "FECHAMENTO DO DIA")
- ✅ Tem estrutura JSON completa com todas as seções
- ✅ Tem texto formatado para exibição
- ✅ **Representa exatamente o que está visível na tela**

**Exemplo:**
```
1. Usuário: "o que temos pra hoje?"
   IA: [RELATÓRIO COMPLETO - 5000 caracteres]
   ✅ Sistema salva: tipo_relatorio='o_que_tem_hoje', texto_chat=[relatório completo]
   
2. Usuário: "como está o ALH.0166/25?"
   IA: "O processo ALH.0166/25 está em análise..."
   ⚠️ Sistema NÃO salva isso como relatório (é apenas uma resposta)
   
3. Usuário: "envie esse relatorio por email"
   ✅ Sistema busca: último relatório salvo (o que está na tela)
   ✅ Sistema envia: o relatório completo que foi exibido
```

---

## 🔍 Validação de Coerência

### Regra: **Sempre verificar se o que foi solicitado tem coerência antes de executar**

O sistema agora valida **3 aspectos** antes de enviar um relatório por email:

#### 1. **Validação de Recência**
- ✅ Relatório deve ter sido criado nas últimas **2 horas**
- ✅ Se o relatório for mais antigo, pode não ser o que está na tela
- ⚠️ Se não conseguir validar data, assume que é recente (melhor enviar do que não enviar)

#### 2. **Validação de Conteúdo**
- ✅ Texto deve ter características de relatório:
  - Título de relatório (ex: "O QUE TEMOS PRA HOJE", "FECHAMENTO DO DIA")
  - Conteúdo suficiente (mínimo de 200 caracteres)
- ❌ Se for apenas uma notificação curta ou resposta de processo, não é um relatório válido

#### 3. **Validação de Tipo**
- ✅ Tipo do relatório salvo deve ser reconhecível:
  - `o_que_tem_hoje` → mapeia para `resumo`
  - `fechamento_dia` → mapeia para `fechamento`
- ✅ Se não conseguir identificar tipo, usa fallback para `resumo`

---

## 🎯 Fluxo de Decisão

```
Usuário: "envie esse relatorio por email para fulano@email.com"

1. ✅ Buscar último relatório SALVO (prioridade máxima)
   └─ Se encontrado → Validar coerência
      ├─ ✅ Recente (< 2 horas)?
      ├─ ✅ Tem título de relatório?
      ├─ ✅ Tem conteúdo suficiente (> 200 chars)?
      └─ ✅ Tipo reconhecível?
         └─ ✅ SIM → Usar enviar_relatorio_email
         └─ ❌ NÃO → Deixar IA processar (perguntar ao usuário)

2. ⚠️ Fallback: Buscar do histórico (não ideal)
   └─ Se não encontrou relatório salvo
      └─ Tentar última resposta do histórico
         └─ ⚠️ Pode não ser o que está na tela!
```

---

## 📝 Implementação

### Arquivo: `services/email_precheck_service.py`

**Método:** `_precheck_envio_email_relatorio_adhoc()`

**Lógica:**
```python
# ✅ PRIORIDADE MÁXIMA: Buscar último relatório salvo (o que foi exibido na tela)
relatorio_salvo = buscar_ultimo_relatorio(session_id, tipo_relatorio=None)

# ✅ VALIDAÇÃO 1: Verificar se é recente (< 2 horas)
relatorio_recente = validar_recencia(relatorio_salvo)

# ✅ VALIDAÇÃO 2: Verificar se tem características de relatório
texto_valido = validar_conteudo(ultima_resposta_texto)

# ✅ VALIDAÇÃO 3: Verificar tipo reconhecível
tipo_relatorio = mapear_tipo(relatorio_salvo.tipo_relatorio)

# ✅ DECISÃO: Só enviar se passar todas as validações
if relatorio_recente and texto_valido and tipo_relatorio:
    usar_enviar_relatorio_email()
else:
    deixar_ia_processar()  # Perguntar ao usuário
```

---

## ✅ Benefícios

1. **Precisão**: Sempre envia o relatório que está na tela, não outras mensagens
2. **Confiabilidade**: Validações garantem que o conteúdo é coerente
3. **Segurança**: Não envia conteúdo antigo ou inválido por engano
4. **Experiência do Usuário**: Usuário recebe exatamente o que vê na tela

---

## 🚨 Casos de Uso

### ✅ Caso 1: Relatório Recente e Válido
```
1. Usuário: "o que temos pra hoje?"
   → Sistema salva relatório (tipo: o_que_tem_hoje, criado: agora)

2. Usuário: "envie esse relatorio por email"
   → ✅ Sistema encontra relatório salvo
   → ✅ Relatório é recente (< 2 horas)
   → ✅ Texto tem título e conteúdo suficiente
   → ✅ Tipo reconhecível (o_que_tem_hoje → resumo)
   → ✅ ENVIA o relatório correto
```

### ❌ Caso 2: Relatório Antigo
```
1. Usuário: "o que temos pra hoje?" (3 horas atrás)
   → Sistema salvou relatório (criado: 3 horas atrás)

2. Usuário: "envie esse relatorio por email"
   → ✅ Sistema encontra relatório salvo
   → ❌ Relatório é ANTIGO (> 2 horas)
   → ⚠️ Sistema deixa IA processar (pergunta ao usuário se quer enviar mesmo assim)
```

### ❌ Caso 3: Última Mensagem Não é Relatório
```
1. Usuário: "o que temos pra hoje?"
   → Sistema salva relatório

2. Usuário: "como está o ALH.0166/25?"
   → Sistema responde (não salva como relatório)

3. Usuário: "envie esse relatorio por email"
   → ✅ Sistema encontra relatório salvo (do passo 1)
   → ✅ Relatório é recente
   → ✅ Texto tem título e conteúdo suficiente
   → ✅ ENVIA o relatório correto (não a resposta do processo)
```

---

## 📚 Referências

- `services/email_precheck_service.py` - Validação de coerência
- `services/report_service.py` - Gerenciamento de relatórios salvos
- `services/context_service.py` - Armazenamento de contexto da sessão

---

**Última atualização:** 12/01/2026
