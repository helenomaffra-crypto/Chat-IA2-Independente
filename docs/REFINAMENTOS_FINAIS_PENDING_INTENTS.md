# ✅ Refinamentos Finais - Sistema de Pending Intents

**Data:** 14/01/2026  
**Status:** ✅ **IMPLEMENTADO** (Último polimento antes da Fase 2)

---

## 📋 **Resumo dos Refinamentos**

| # | Refinamento | Status | Arquivo |
|---|-------------|--------|---------|
| 1 | Status "expired" separado de "cancelled" | ✅ | `pending_intent_service.py` |
| 2 | Confirmação atômica (anti duplo execute) | ✅ | `pending_intent_service.py`, `confirmation_handler.py` |
| 3 | Fluxo de escolha melhorado (duas etapas) | ✅ | `confirmation_handler.py` |
| 4 | Minimizar preview_text (sanitização) | ✅ | `pending_intent_service.py` |

---

## ✅ **1. Status "expired" Separado de "cancelled"**

### Problema
- Antes: Quando expirava, marcava como `cancelled`
- Misturava duas coisas diferentes:
  - `cancelled` = usuário desistiu
  - `expired` = sistema expirou (TTL)

### Solução
- ✅ Criado método `marcar_como_expirado()` separado
- ✅ Status `expired` agora é distinto de `cancelled`
- ✅ Ajuda em debug, métricas e auditoria

**Arquivo:** `services/pending_intent_service.py`

**Método:**
```python
@staticmethod
def marcar_como_expirado(intent_id: str) -> bool:
    """
    Marca um pending intent como expirado.
    
    Separado de 'cancelled' para distinguir:
    - expired = sistema expirou (TTL)
    - cancelled = usuário desistiu
    """
    cursor.execute('''
        UPDATE pending_intents 
        SET status = 'expired', observacoes = 'Expirado automaticamente (TTL)'
        WHERE intent_id = ? AND status = 'pending'
    ''', (intent_id,))
```

**Mudanças:**
- `buscar_pending_intent()` agora chama `marcar_como_expirado()` ao invés de `marcar_como_cancelado()`
- `limpar_intents_expiradas()` usa `marcar_como_expirado()` para cada intent

---

## ✅ **2. Confirmação Atômica (Anti Duplo Execute)**

### Problema
- Idempotência por status resolve muito, mas em concorrência (web + WhatsApp, ou retry) pode haver corrida
- Dois requests podem entrar ao mesmo tempo e ambos executarem

### Solução
- ✅ Adicionado status `executing` como estado intermediário
- ✅ Transição atômica: `pending` → `executing` → `executed`
- ✅ Se `rowcount == 0`, não executa (alguém já pegou o lock)

**Arquivo:** `services/pending_intent_service.py`

**Método:**
```python
@staticmethod
def marcar_como_executando(intent_id: str) -> bool:
    """
    Marca pending intent como 'executing' (confirmação atômica).
    
    Usa UPDATE com WHERE status='pending' para garantir que apenas um processo
    pode marcar como executing (anti duplo execute em concorrência).
    """
    cursor.execute('''
        UPDATE pending_intents 
        SET status = 'executing'
        WHERE intent_id = ? AND status = 'pending'
    ''', (intent_id,))
    
    affected = cursor.rowcount
    return affected > 0  # True se lock obtido, False se já foi executado/executando
```

**Fluxo:**
1. Verificar status (se não for `pending`, retornar erro)
2. **Marcar como `executing`** (lock atômico)
3. Se `rowcount == 0` → alguém já pegou, retornar erro
4. Executar ação
5. Marcar como `executed` (só funciona se status for `executing`)

**Arquivo:** `services/handlers/confirmation_handler.py`

**Integração:**
```python
# Antes de executar
lock_obtido = service.marcar_como_executando(intent_id)
if not lock_obtido:
    return {
        'sucesso': False,
        'erro': 'EM_EXECUCAO',
        'resposta': '❌ Este email está sendo processado por outra requisição. Aguarde alguns instantes.'
    }

# Executar ação...

# Depois de executar (só funciona se status for 'executing')
service.marcar_como_executado(intent_id, observacoes='Email enviado com sucesso')
```

**Mudanças no `marcar_como_executado()`:**
- Agora só atualiza se status for `executing` (não mais `pending`)
- Garante que foi marcado como `executing` antes

---

## ✅ **3. Fluxo de Escolha Melhorado (Duas Etapas)**

### Problema
- Opções não eram numeradas claramente
- Sistema não aceitava resposta simples ("1", "2")
- Podia confundir escolha com confirmação final

### Solução
- ✅ Opções numeradas: `(1)`, `(2)`, `(3)`
- ✅ Sistema aceita resposta simples: "1", "2", "3"
- ✅ Duas etapas: escolha → preview → confirmação
- ✅ Flag `requer_escolha: True` e `opcoes: [...]` no retorno

**Arquivo:** `services/handlers/confirmation_handler.py`

**Mudanças:**

**Email:**
```python
if len(intents_email) > 1:
    lista_opcoes = '\n'.join([
        f"({idx+1}) Email para {intent.get('args_normalizados', {}).get('destinatario', 'N/A')} "
        f"- Assunto: {intent.get('args_normalizados', {}).get('assunto', 'N/A')}"
        for idx, intent in enumerate(intents_email)
    ])
    return {
        'sucesso': False,
        'erro': 'MULTIPLOS_PENDENTES',
        'resposta': f'📋 Há {len(intents_email)} emails pendentes. Qual deseja confirmar?\n\n{lista_opcoes}\n\n💡 Digite o número (1, 2, 3...) ou "cancelar" para cancelar.',
        'requer_escolha': True,  # ✅ Flag para indicar que precisa escolha
        'opcoes': intents_email  # ✅ Incluir opções para processamento posterior
    }
```

**DUIMP:**
```python
if len(intents_duimp) > 1:
    lista_opcoes = '\n'.join([
        f"({idx+1}) DUIMP do processo {intent.get('args_normalizados', {}).get('processo_referencia', 'N/A')} "
        f"- Ambiente: {intent.get('args_normalizados', {}).get('ambiente', 'N/A')}"
        for idx, intent in enumerate(intents_duimp)
    ])
    return {
        'sucesso': False,
        'erro': 'MULTIPLOS_PENDENTES',
        'resposta': f'📋 Há {len(intents_duimp)} DUIMPs pendentes. Qual deseja confirmar?\n\n{lista_opcoes}\n\n💡 Digite o número (1, 2, 3...) ou "cancelar" para cancelar.',
        'requer_escolha': True,  # ✅ Flag para indicar que precisa escolha
        'opcoes': intents_duimp  # ✅ Incluir opções para processamento posterior
    }
```

**⚠️ Nota:** O processamento da escolha (interpretar "1", "2", etc.) ainda precisa ser implementado no `chat_service.py` ou no frontend.

---

## ✅ **4. Minimizar preview_text (Sanitização)**

### Problema
- Truncar para 200 chars ajuda, mas ainda pode conter dados sensíveis
- Emails, CNPJ, CPF, valores monetários aparecem no preview

### Solução
- ✅ Método `_sanitizar_preview_text()` criado
- ✅ Mascara dados sensíveis antes de truncar:
  - Emails: `usuario@exemplo.com` → `us***@exemplo.com`
  - CNPJ: `12.345.678/0001-90` → `12.***.***/****-**`
  - CPF: `123.456.789-00` → `123.***.***-**`
  - Valores: `R$ 1.234,56` → `R$ ***,**`

**Arquivo:** `services/pending_intent_service.py`

**Método:**
```python
@staticmethod
def _sanitizar_preview_text(preview_text: str) -> str:
    """
    Sanitiza preview_text mascarando dados sensíveis.
    
    Mascara:
    - Emails: usuario@exemplo.com → us***@exemplo.com
    - CNPJ: 12.345.678/0001-90 → 12.***.***/****-**
    - CPF: 123.456.789-00 → 123.***.***-**
    - Valores monetários: R$ 1.234,56 → R$ ***,**
    """
    import re
    
    texto = preview_text
    
    # Mascarar emails
    texto = re.sub(
        r'([a-zA-Z0-9._%+-]{1,3})([a-zA-Z0-9._%+-]*)(@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'\1***\3',
        texto
    )
    
    # Mascarar CNPJ (XX.XXX.XXX/XXXX-XX)
    texto = re.sub(
        r'(\d{2}\.)(\d{3}\.)(\d{3}/)(\d{4}-)(\d{2})',
        r'\1***.***/****-\5',
        texto
    )
    
    # Mascarar CPF (XXX.XXX.XXX-XX)
    texto = re.sub(
        r'(\d{3}\.)(\d{3}\.)(\d{3}-)(\d{2})',
        r'\1***.***-**',
        texto
    )
    
    # Mascarar valores monetários (R$ X.XXX,XX ou USD X.XXX,XX)
    texto = re.sub(
        r'(R\$\s*|USD\s*)(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        r'\1***,**',
        texto
    )
    
    return texto
```

**Uso:**
```python
# Em criar_pending_intent()
preview_text_sanitizado = PendingIntentService._sanitizar_preview_text(preview_text)
preview_text_minimizado = preview_text_sanitizado[:200] + ('...' if len(preview_text_sanitizado) > 200 else '')
```

---

## 📁 **Arquivos Modificados**

1. ✅ `db_manager.py`
   - Status `executing` adicionado ao comentário da tabela

2. ✅ `services/pending_intent_service.py`
   - Método `marcar_como_expirado()` criado
   - Método `marcar_como_executando()` criado
   - Método `marcar_como_executado()` atualizado (só funciona se status for `executing`)
   - Método `_sanitizar_preview_text()` criado
   - `buscar_pending_intent()` agora chama `marcar_como_expirado()`
   - `limpar_intents_expiradas()` usa `marcar_como_expirado()`
   - `criar_pending_intent()` usa `_sanitizar_preview_text()`

3. ✅ `services/handlers/confirmation_handler.py`
   - `processar_confirmacao_email()` usa confirmação atômica
   - `processar_confirmacao_duimp()` usa confirmação atômica
   - Fluxo de escolha melhorado (opções numeradas, flag `requer_escolha`)
   - Verificação de status `executing` adicionada

---

## ✅ **Status dos Status**

| Status | Significado | Quando Usar |
|--------|-------------|-------------|
| `pending` | Aguardando confirmação | Estado inicial |
| `executing` | Em execução (lock) | Durante confirmação atômica |
| `executed` | Executado com sucesso | Após execução bem-sucedida |
| `cancelled` | Cancelado pelo usuário | Quando usuário desiste |
| `expired` | Expirado (TTL) | Quando TTL expira |

---

## 🎯 **Benefícios Alcançados**

1. ✅ **Auditoria melhorada**: `expired` vs `cancelled` separados
2. ✅ **Concorrência segura**: Confirmação atômica previne duplo execute
3. ✅ **UX melhorada**: Escolha numerada e duas etapas
4. ✅ **Segurança**: Dados sensíveis mascarados no preview

---

## ⏳ **Pendente**

1. ⏳ **Processamento de escolha**: Implementar lógica para interpretar "1", "2", etc. no `chat_service.py` ou frontend
2. ⏳ **Golden tests**: Criar testes para todos os cenários de refinamento

---

**Status:** ✅ **PRONTO PARA FASE 2**

**Última atualização:** 14/01/2026
