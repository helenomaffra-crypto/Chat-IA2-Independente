# 🔧 Correção: Detecção de Ano em "busque in 1984 2020"

## 🐛 Problema Identificado

Quando o usuário digita "busque in 1984 2020", o sistema estava:
- ❌ Detectando como "IN 1984/1984" (ano duplicado/incorreto)
- ❌ Mostrando erro: "Não foi possível buscar a in 1984/1984"

## ✅ Correções Implementadas

### 1. Padrões Regex Melhorados (`legislacao_precheck_service.py`)

**Antes:**
- Padrão genérico que não capturava bem "1984 2020" (com espaço)

**Agora:**
- **Padrão 1:** "IN 1984/2020" (com barra) - PRIORIDADE ALTA
- **Padrão 2:** "IN 1984 2020" (com espaço) - PRIORIDADE ALTA  
- **Padrão 3:** "IN 1984" (sem ano) - FALLBACK

**Ordem de prioridade:** Padrões mais específicos primeiro

### 2. Extração de Ano Melhorada

**Antes:**
- Pegava o primeiro número de 4 dígitos encontrado (que podia ser o número da legislação)

**Agora:**
- Procura números de 4 dígitos **APÓS** a posição do número da legislação
- Valida se é um ano válido (1900-2100)
- Se tiver múltiplos anos válidos, pega o último (mais provável)

### 3. Formatação de Mensagens de Erro

**Antes:**
- Usava `{tipo_ato} {numero}/{ano}` mesmo quando ano era None

**Agora:**
- Formata corretamente: `{tipo_ato} {numero}` se ano for None
- Só adiciona `/{ano}` se ano existir

### 4. Retornos Estruturados

Todos os erros agora retornam:
- `erro`: Código do erro (ex: `URL_NAO_ENCONTRADA`)
- `mensagem`: Mensagem amigável
- `detalhes`: Dict com informações adicionais

## 🧪 Teste de Validação

**Input:** `"busque in 1984 2020"`

**Resultado esperado:**
```python
{
    'tipo_ato': 'in',
    'numero': '1984',
    'ano': 2020  # ✅ Correto!
}
```

**Teste executado:**
```bash
python3 -c "from services.legislacao_precheck_service import ..."
# Resultado: ✅ Padrão 2 MATCHOU - Ano: 2020
```

## 📝 Arquivos Modificados

1. **`services/legislacao_precheck_service.py`**
   - Padrões regex reordenados (específicos primeiro)
   - Extração de ano melhorada (procura após número da legislação)

2. **`services/agents/legislacao_agent.py`**
   - Formatação de referência corrigida (só adiciona /ano se existir)

3. **`services/legislacao_service.py`**
   - Retorno de erro estruturado quando URL não encontrada

## 🎯 Comportamento Esperado Agora

**Input:** `"busque in 1984 2020"`

1. ✅ Precheck detecta: `IN 1984/2020`
2. ✅ Chama tool: `importar_legislacao_preview(tipo_ato='IN', numero='1984', ano=2020)`
3. ✅ Busca URL com IA para "IN 1984/2020"
4. ✅ Se encontrar URL → tenta importar
5. ✅ Se não encontrar → retorna erro estruturado com mensagem amigável

## ⚠️ Possíveis Problemas Restantes

Se ainda aparecer "1984/1984", pode ser:
1. **IA não habilitada:** Verificar `DUIMP_AI_ENABLED=true` no `.env`
2. **IA não encontrou URL:** Normal para legislações mais recentes ou específicas
3. **Cache de contexto:** Limpar histórico da sessão

## 🔍 Como Debugar

Se o problema persistir, verificar logs:
```python
# No código, adicionar:
logger.info(f"[LEGISLACAO_PRECHECK] Detectado: {tipo_ato} {numero}/{ano}")
```

Ou testar diretamente:
```python
from services.legislacao_precheck_service import LegislacaoPrecheckService
service = LegislacaoPrecheckService(chat_service)
resultado = service.precheck_importar_legislacao("busque in 1984 2020", "busque in 1984 2020")
print(resultado)
```

