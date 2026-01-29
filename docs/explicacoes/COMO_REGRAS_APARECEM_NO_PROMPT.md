# 📚 Como as Regras Aprendidas Aparecem no Prompt

## 🎯 Resumo Visual

```
┌─────────────────────────────────────────────────────────────┐
│ 1. VOCÊ CRIA REGRA NO CHAT                                   │
│    "maike o ALH vai ser alho ok?"                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. REGRA SALVA NO SQLITE                                     │
│    chat_ia.db → tabela regras_aprendidas                    │
│    - tipo_regra: 'cliente_categoria'                        │
│    - nome_regra: 'ALH → ALHO'                               │
│    - descricao: 'Mapeia ALH para ALHO'                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. VOCÊ ENVIA MENSAGEM                                       │
│    "como estão os processos do ALHO?"                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. SISTEMA BUSCA REGRAS NO SQLITE                           │
│    buscar_regras_aprendidas(ativas=True)                    │
│    → Retorna lista de regras                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. SISTEMA FORMATA AS REGRAS                                │
│    formatar_regras_para_prompt(regras)                      │
│    → Gera texto formatado                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. SISTEMA MONTA PROMPT COMPLETO                            │
│    PromptBuilder.build_system_prompt(                        │
│      regras_aprendidas=texto_formatado                      │
│    )                                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. IA RECEBE PROMPT COM REGRAS                              │
│    System Prompt:                                            │
│    "Você é o mAIke..."                                       │
│    [instruções]                                              │
│    [tools]                                                   │
│    📚 **REGRAS APRENDIDAS:**                                │
│    - **ALH → ALHO**: Mapeia...                              │
│    💡 Aplique essas regras...                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. IA USA AS REGRAS                                          │
│    - Lê: "ALH → ALHO"                                        │
│    - Aplica quando você pergunta sobre ALHO                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Exemplo Real do Prompt

### **System Prompt Completo (exemplo):**

```
Você é o mAIke, um assistente inteligente e conversacional 
especializado em DUIMP (Declaração Única de Importação) e 
processos de importação no Brasil.

🧠 CHAIN OF THOUGHT (SEMPRE PENSE ANTES DE AGIR):
ANTES de escolher uma tool, SEMPRE pense passo a passo:
1. O que o usuário quer fazer?
2. Qual é o contexto da conversa anterior?
3. Qual tool é mais apropriada?
...

📚 EXEMPLOS DE USO (Few-Shot Learning):
[exemplos de uso das tools]
...

[lista de tools disponíveis]
...

📚 **REGRAS APRENDIDAS:**
- **destfinal como confirmação de chegada**: O campo data_destino_final deve ser usado como confirmação de que o processo chegou ao destino final (SQL: WHERE data_destino_final IS NOT NULL)
- **diamonds → DMD**: Mapeia o termo "diamonds" (plural) para a categoria DMD
- **Bandimar → BND**: Mapeia o termo "Bandimar" para a categoria BND
- **Diamond → DMD**: Mapeia o termo "Diamond" e "diamonds" para a categoria DMD
- **dmd sera diamond**: Quando o usuário se referir à categoria DMD, entender que o cliente é Diamond.
💡 Aplique essas regras quando fizer sentido.
```

---

## 🔍 Detalhes Técnicos

### **1. Busca no SQLite**

```python
# services/chat_service.py (linha ~4410)
regras = buscar_regras_aprendidas(ativas=True)
```

**SQL executado:**
```sql
SELECT * FROM regras_aprendidas
WHERE ativa = 1
ORDER BY vezes_usado DESC, ultimo_usado_em DESC, criado_em DESC
```

**Resultado:** Lista de regras ordenadas por relevância

---

### **2. Formatação para o Prompt**

```python
# services/learned_rules_service.py (linha ~186)
def formatar_regras_para_prompt(regras):
    if not regras:
        return ""
    
    texto = "\n\n📚 **REGRAS APRENDIDAS:**\n"
    
    for regra in regras[:5]:  # Limita a 5 regras
        texto += f"- **{regra['nome_regra']}**: {regra['descricao']}"
        if regra.get('aplicacao_sql'):
            texto += f" (SQL: {regra['aplicacao_sql']})"
        texto += "\n"
    
    texto += "💡 Aplique essas regras quando fizer sentido.\n"
    
    return texto
```

**Características:**
- ✅ Limita a 5 regras (otimização)
- ✅ Ordena por relevância (vezes_usado DESC)
- ✅ Formato compacto
- ✅ Inclui SQL se disponível

---

### **3. Adição ao System Prompt**

```python
# services/prompt_builder.py (linha ~506)
def build_system_prompt(self, saudacao_personalizada, regras_aprendidas=None):
    system_prompt = """Você é o mAIke...
    [instruções gerais]
    [exemplos]
    [tools]
    """
    
    # ✅ NOVO: Adicionar regras aprendidas se disponíveis
    if regras_aprendidas:
        system_prompt += regras_aprendidas  # ← AQUI!
    
    return system_prompt
```

**Onde é adicionado:**
- No final do system_prompt
- Antes de enviar para a IA
- Sempre que há regras ativas

---

## 📋 Regras Encontradas no Seu Banco

Com base na execução do script, você tem **7 regras** no banco:

### **Regras de Mapeamento Cliente → Categoria:**

1. **Diamond → DMD** (ID: 5)
   - Mapeia "Diamond" e "diamonds" para DMD

2. **Bandimar → BND** (ID: 6)
   - Mapeia "Bandimar" para BND

3. **diamonds → DMD** (ID: 7)
   - Mapeia "diamonds" (plural) para DMD

### **Outras Regras:**

4. **destfinal como confirmação de chegada** (ID: 1)
   - Campo SQL: `WHERE data_destino_final IS NOT NULL`
   - Usado para identificar processos que chegaram

5. **dmd sera diamond** (ID: 4)
   - Mapeia categoria DMD para cliente Diamond

6. **bnd sera bandimar** (ID: 3)
   - Mapeia categoria BND para cliente Bandimar

7. **destfinal como confirmação de chegada (teste)** (ID: 2)
   - Versão de teste da regra anterior

---

## 🎯 Como Verificar em Tempo Real

### **Opção 1: Script Python**

```bash
python3 scripts/ver_regras_no_prompt.py
```

Mostra:
- Todas as regras no banco
- Como aparecem no prompt
- Regras de mapeamento cliente→categoria

### **Opção 2: SQLite Direto**

```bash
sqlite3 chat_ia.db

# Ver todas as regras
SELECT * FROM regras_aprendidas WHERE ativa = 1;

# Ver apenas mapeamentos cliente→categoria
SELECT nome_regra, aplicacao_texto 
FROM regras_aprendidas 
WHERE tipo_regra = 'cliente_categoria' AND ativa = 1;
```

### **Opção 3: Logs do Sistema**

Quando o sistema busca regras, gera log:

```
✅ 7 regras aprendidas incluídas no prompt
```

---

## 🔄 Fluxo Completo com Exemplo

### **Cenário: Você pergunta "como estão os processos do Diamond?"**

```
1. ChatService.processar_mensagem("como estão os processos do Diamond?")
   │
   ├─> Busca regras no SQLite
   │   └─> Encontra: "Diamond → DMD"
   │
   ├─> Formata regras
   │   └─> "📚 **REGRAS APRENDIDAS:**\n- **Diamond → DMD**: ..."
   │
   ├─> Monta system_prompt
   │   └─> Inclui regras aprendidas no final
   │
   ├─> Envia para IA (GPT-4o)
   │   └─> IA recebe prompt com regras
   │
   └─> IA processa
       ├─> Lê regra: "Diamond → DMD"
       ├─> Entende: "Diamond" = categoria "DMD"
       └─> Chama: listar_processos_por_categoria(categoria="DMD")
```

---

## 💡 Importante

### **Limitações:**

1. **Apenas 5 regras no prompt:**
   - As 5 mais usadas/recentes
   - Evita sobrecarregar o prompt

2. **Ordenação por relevância:**
   - `vezes_usado DESC` (mais usadas primeiro)
   - `ultimo_usado_em DESC` (mais recentes primeiro)

3. **Formato compacto:**
   - Apenas nome e descrição
   - SQL incluído se disponível

### **Otimizações:**

- ✅ Busca rápida (SQLite local)
- ✅ Cache implícito (mesma sessão)
- ✅ Limitação inteligente (top 5)
- ✅ Formato compacto

---

## 🎓 Resumo

**SQLite (`chat_ia.db`) = Banco de conhecimento personalizado**

**Regras aprendidas = Conhecimento que você ensina à IA**

**Prompt = Instruções completas para a IA**

**Integração = Regras do SQLite são automaticamente incluídas no prompt**

**É como ter um assistente que:**
- Tem um manual básico (prompt base)
- Consulta suas anotações pessoais (SQLite)
- Combina tudo antes de responder (prompt completo)
- Aprende com você (regras aprendidas)

---

## 🔗 Arquivos Relacionados

- `services/learned_rules_service.py` - Busca e formatação de regras
- `services/prompt_builder.py` - Montagem do prompt
- `services/chat_service.py` - Integração no fluxo
- `db_manager.py` - Estrutura da tabela SQLite
- `scripts/ver_regras_no_prompt.py` - Script de visualização

