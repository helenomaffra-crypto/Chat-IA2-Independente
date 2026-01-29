# 🧪 Como Testar o QuestionClassifier

**Data:** 10/01/2026  
**Status:** ✅ Testes criados e funcionando

---

## 📋 Opção 1: Script de Teste Simples (Recomendado)

Execute o script de teste que valida todos os métodos:

```bash
python3 test_question_classifier.py
```

**Saída esperada:**
```
============================================================
🧪 TESTES DO QuestionClassifier
============================================================
...
🎉 TODOS OS TESTES PASSARAM!
============================================================
```

---

## 📋 Opção 2: Teste Manual no Python

Teste métodos individuais diretamente:

```python
import sys
sys.path.insert(0, '.')

from services.utils.question_classifier import QuestionClassifier

# Teste 1: Pergunta Analítica
resultado = QuestionClassifier.eh_pergunta_analitica("top 10 clientes por valor CIF")
print(f"Analítica: {resultado}")  # True

# Teste 2: Conhecimento Geral
resultado = QuestionClassifier.eh_pergunta_conhecimento_geral("o que é uma DI?")
print(f"Conhecimento geral: {resultado}")  # True

# Teste 3: Pergunta Genérica (com callback)
def extrair_categoria(mensagem):
    if 'vdm' in mensagem.lower():
        return 'VDM'
    return None

resultado = QuestionClassifier.eh_pergunta_generica(
    "quais processos têm pendência?",
    extrair_categoria_callback=extrair_categoria
)
print(f"Genérica: {resultado}")  # True

# Teste 4: Precisa Contexto (com callback)
def extrair_processo(mensagem):
    import re
    match = re.search(r'([a-z]{2,4}\.\d{1,4}/\d{2})', mensagem.lower())
    return match.group(1).upper() if match else None

resultado = QuestionClassifier.identificar_se_precisa_contexto(
    "tem bloqueio?",
    extrair_processo_callback=extrair_processo
)
print(f"Precisa contexto: {resultado}")  # True
```

---

## 📋 Opção 3: Teste de Integração com ChatService

Verifique se os métodos do `ChatService` ainda funcionam corretamente após o refatoramento:

```python
import sys
sys.path.insert(0, '.')

from app import get_chat_service

chat_service = get_chat_service()

# Os métodos antigos ainda funcionam (são wrappers)
resultado = chat_service._eh_pergunta_analitica("top 10 clientes")
print(f"ChatService._eh_pergunta_analitica: {resultado}")  # True

resultado = chat_service._eh_pergunta_conhecimento_geral("o que é uma DI?")
print(f"ChatService._eh_pergunta_conhecimento_geral: {resultado}")  # True
```

---

## ✅ Casos de Teste Cobertos

### `eh_pergunta_analitica()`
- ✅ Ranking: "top 10 clientes"
- ✅ Agregação: "total de processos por mês"
- ✅ Estatística: "média de valores"
- ✅ Distribuição: "distribuição de cargas"
- ❌ Consulta específica: "como está o vdm.003?"
- ❌ Pergunta de NCM: "qual a ncm de iphone?"

### `eh_pergunta_conhecimento_geral()`
- ✅ Cotação: "qual a cotação de frete?"
- ✅ Conceito: "o que é uma DI?"
- ✅ Processo conceitual: "como funciona importação?"
- ✅ Comparação: "qual a diferença entre DI e DUIMP?"
- ❌ Processo específico: "situacao do gym.0047/25"
- ❌ Classificação fiscal: "qual a explicação para classificação..."

### `eh_pergunta_generica()`
- ✅ Genérica: "quais processos têm pendência?"
- ✅ Genérica: "mostre todos os processos"
- ❌ Específica: "como estão os vdm?"
- ❌ Sem "processos": "quais estão bloqueados?"

### `identificar_se_precisa_contexto()`
- ✅ Precisa: "tem bloqueio?"
- ✅ Precisa: "qual o frete?"
- ❌ Não precisa: "consulte o CE do processo MSS.0018/25"
- ❌ Pergunta geral: "qual processo tem bloqueio?"

---

## 🔍 Debug

Se algum teste falhar, verifique:

1. **Imports corretos:**
   ```python
   from services.utils.question_classifier import QuestionClassifier
   ```

2. **Callbacks corretos:**
   - `eh_pergunta_generica` precisa de `extrair_categoria_callback`
   - `identificar_se_precisa_contexto` precisa de `extrair_processo_callback`

3. **Código atualizado:**
   ```bash
   python3 -m py_compile services/utils/question_classifier.py
   ```

---

**Última atualização:** 10/01/2026
