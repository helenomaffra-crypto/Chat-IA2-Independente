# ✅ CORREÇÃO CRÍTICA: Erro max_tokens / max_completion_tokens

**Data:** 18/12/2025  
**Problema:** Todos os serviços de IA pararam de funcionar devido a erro na API da OpenAI

---

## ❌ PROBLEMA IDENTIFICADO

Erro retornado pela API da OpenAI:
```
Error code: 400 - {'error': {'message': "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.", 'type': 'invalid_request_error', 'param': 'max_tokens', 'code': 'unsupported_parameter'}}
```

**Causa:** Alguns modelos novos da OpenAI (como o1, o3, e possivelmente outros) não aceitam o parâmetro `max_tokens`, mas sim `max_completion_tokens`.

**Impacto:** Todos os serviços que usam IA pararam de funcionar:
- ❌ Sugestão de NCM
- ❌ Busca NESH
- ❌ Qualquer funcionalidade que use IA

---

## ✅ SOLUÇÃO IMPLEMENTADA

Implementado fallback inteligente em `ai_service.py`:

1. **Tentar primeiro com `max_completion_tokens`** (compatível com modelos novos)
2. **Se falhar, tentar com `max_tokens`** (compatível com modelos antigos)

### Código implementado:

```python
kwargs = {
    "model": model_selecionado,
    "messages": messages,
    "temperature": temperature_selecionada
}

# ✅ CORREÇÃO CRÍTICA: Tentar primeiro com max_completion_tokens (modelos novos)
kwargs["max_completion_tokens"] = 800

# ... código de tools ...

# ✅ CORREÇÃO CRÍTICA: Tentar com max_completion_tokens primeiro, se falhar, tentar max_tokens
try:
    response = client.chat.completions.create(**kwargs)
except Exception as e:
    error_str = str(e)
    # Se o erro for sobre max_completion_tokens não suportado, tentar com max_tokens
    if 'max_completion_tokens' in error_str.lower() or 'unsupported parameter' in error_str.lower():
        logger.warning(f"[AI_SERVICE] ⚠️ Erro com max_completion_tokens, tentando max_tokens: {e}")
        # Remover max_completion_tokens e tentar com max_tokens
        kwargs_fallback = {k: v for k, v in kwargs.items() if k != 'max_completion_tokens'}
        kwargs_fallback["max_tokens"] = 800
        response = client.chat.completions.create(**kwargs_fallback)
    # Se o erro for sobre max_tokens não suportado, tentar com max_completion_tokens
    elif 'max_tokens' in error_str.lower() and 'max_completion_tokens' in error_str.lower():
        logger.warning(f"[AI_SERVICE] ⚠️ Erro com max_tokens, tentando max_completion_tokens: {e}")
        # Remover max_tokens e tentar com max_completion_tokens
        kwargs_fallback = {k: v for k, v in kwargs.items() if k != 'max_tokens'}
        kwargs_fallback["max_completion_tokens"] = 800
        response = client.chat.completions.create(**kwargs_fallback)
    else:
        # Re-raise se for outro tipo de erro
        raise
```

---

## ✅ STATUS

- ✅ Correção aplicada em `ai_service.py`
- ✅ Teste confirmado: NCM sugerido funcionando (retornou NCM 90041000 para "oculos")
- ✅ Fallback implementado para compatibilidade com modelos antigos e novos

---

## 🧪 TESTE

Teste realizado:
```python
from services.ncm_service import NCMService
service = NCMService()
resultado = service.sugerir_ncm_com_ia('oculos', {}, True, True, 'ncm para oculos')
# ✅ Resultado: sucesso, NCM sugerido: 90041000
```

---

**Última atualização:** 18/12/2025

