# 🔧 Correções: Sistema de Email Draft (Sugestão ChatGPT)

**Data:** 09/01/2026  
**Status:** ✅ **IMPLEMENTADO**

---

## 🎯 Problema Identificado

O sistema estava enviando a versão **antiga** do email após o usuário pedir para melhorar, porque:

1. **Memória era considerada fonte da verdade** mesmo quando tinha `draft_id`
2. **Preview não era reemitido** após melhorar o email
3. **Regex frágil** para extrair email melhorado da resposta da IA
4. **Revision não era validada** entre memória e banco

---

## ✅ Correções Implementadas

### 1. **Função `_obter_email_para_enviar()` - Banco é Fonte da Verdade**

**Regra implementada:**
- ✅ Se tem `draft_id` → **banco é fonte da verdade** (sempre busca última revisão)
- ✅ Se não tem `draft_id` → usa memória

**Código:**
```python
def _obter_email_para_enviar(self, dados_email_para_enviar: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Obtém dados do email para envio, priorizando banco de dados quando tem draft_id.
    
    Regra: Se tem draft_id → banco é fonte da verdade
           Se não tem draft_id → usa memória
    """
    if not dados_email_para_enviar:
        return None
    
    draft_id = dados_email_para_enviar.get('draft_id')
    if draft_id:
        # ✅ Banco é fonte da verdade quando tem draft_id
        draft = draft_service.obter_draft(draft_id)
        if draft:
            # Validar consistência (opcional, mas útil para debug)
            revision_memoria = dados_email_para_enviar.get('revision')
            if revision_memoria and revision_memoria != draft.revision:
                logger.warning(f'⚠️ Inconsistência: memória tem revision {revision_memoria}, banco tem {draft.revision}. Usando banco.')
            
            return {
                'destinatarios': draft.destinatarios,
                'cc': draft.cc or [],
                'bcc': draft.bcc or [],
                'assunto': draft.assunto,
                'conteudo': draft.conteudo,
                'funcao': draft.funcao_email,
                'draft_id': draft_id,
                'revision': draft.revision
            }
    
    # Sem draft_id: usar memória
    return dados_email_para_enviar
```

**Onde é usado:**
- ✅ Na confirmação de email (`processar_mensagem`)
- ✅ Na confirmação de email via stream (`processar_mensagem_stream`)

---

### 2. **Melhorar Email: Sempre Atualizar Banco + Memória + Reemitir Preview**

**Fluxo implementado:**
1. ✅ Extrair email refinado da resposta da IA
2. ✅ **Atualizar banco** (criar nova revisão no draft)
3. ✅ **Atualizar memória** com dados do banco (sempre última versão)
4. ✅ **Reemitir preview atualizado** (OBRIGATÓRIO)

**Código:**
```python
# 1. Atualizar banco (se tem draft_id)
if draft_id:
    nova_revision = draft_service.revisar_draft(
        draft_id=draft_id,
        assunto=email_refinado.get('assunto'),
        conteudo=email_refinado.get('conteudo')
    )
    if nova_revision:
        # 2. Obter draft atualizado do banco (fonte da verdade)
        draft_atualizado = draft_service.obter_draft(draft_id)
        if draft_atualizado:
            # 3. Atualizar memória com dados do banco
            dados_email_para_enviar['assunto'] = draft_atualizado.assunto
            dados_email_para_enviar['conteudo'] = draft_atualizado.conteudo
            dados_email_para_enviar['revision'] = draft_atualizado.revision  # ✅ NOVO

# 4. Atualizar instância (memória)
self.ultima_resposta_aguardando_email = dados_email_para_enviar

# 5. Reemitir preview atualizado (OBRIGATÓRIO)
preview = f"📧 **Preview do Email (Atualizado):**\n\n..."
resposta_ia = preview
```

**Benefícios:**
- ✅ Preview sempre mostra a versão mais recente
- ✅ Usuário não pode confirmar com preview desatualizado
- ✅ Memória e banco sempre sincronizados

---

### 3. **Validação de Revision (Consistência)**

**Implementado:**
- ✅ Guardar `revision` na memória quando draft é criado
- ✅ Guardar `revision` na memória quando draft é revisado
- ✅ Validar consistência entre memória e banco antes de enviar
- ✅ Log de aviso se houver inconsistência (mas sempre usar banco)

**Código:**
```python
# Na criação do draft
revision_inicial = 1
if draft_id:
    draft_temp = draft_service.obter_draft(draft_id)
    if draft_temp:
        revision_inicial = draft_temp.revision

self.ultima_resposta_aguardando_email = {
    ...
    'revision': revision_inicial  # ✅ Guardar revision na memória
}

# Na validação antes de enviar
revision_memoria = dados_email_para_enviar.get('revision')
if revision_memoria and revision_memoria != draft.revision:
    logger.warning(f'⚠️ Inconsistência: memória tem revision {revision_memoria}, banco tem {draft.revision}. Usando banco.')
```

---

## 📊 Fluxo Completo Atualizado

### 1. **Criação do Preview**
```
Usuário: "mande um email para X dizendo Y"
→ Tool: enviar_email_personalizado(confirmar_envio=false)
→ Sistema:
  1. Cria draft no banco (revision 1)
  2. Salva estado na memória (com draft_id e revision=1)
  3. Mostra preview
```

### 2. **Melhoria do Email**
```
Usuário: "melhore esse email"
→ Sistema:
  1. Detecta pedido de melhoria
  2. IA gera email melhorado
  3. Extrai email da resposta da IA
  4. ✅ Atualiza banco (cria revision 2)
  5. ✅ Atualiza memória com dados do banco (revision 2)
  6. ✅ Reemite preview atualizado
```

### 3. **Confirmação e Envio**
```
Usuário: "pode enviar"
→ Sistema:
  1. Detecta confirmação
  2. ✅ Chama _obter_email_para_enviar()
  3. ✅ Se tem draft_id: busca do banco (fonte da verdade)
  4. ✅ Se não tem draft_id: usa memória
  5. ✅ Valida consistência (revision memória vs banco)
  6. Envia email com dados corretos
  7. Marca draft como enviado
```

---

## 🔍 Arquivos Modificados

1. **`services/chat_service.py`**:
   - ✅ Nova função `_obter_email_para_enviar()`
   - ✅ Atualizado `processar_mensagem()` (confirmação)
   - ✅ Atualizado `processar_mensagem_stream()` (confirmação)
   - ✅ Atualizado lógica de "melhorar email" (banco + memória + preview)
   - ✅ Guardar `revision` na memória

---

## ⚠️ Notas Importantes

1. **Banco é Fonte da Verdade**: Quando tem `draft_id`, o sistema **sempre** busca do banco, ignorando memória desatualizada
2. **Preview Sempre Atualizado**: Após melhorar email, o preview é **sempre** reemitido com a versão mais recente
3. **Fallback Seguro**: Se banco falhar, usa memória como fallback (não quebra o sistema)
4. **Validação Opcional**: A validação de revision é apenas para debug - o sistema sempre usa banco quando tem `draft_id`

---

## 🎯 Regra de Ouro Implementada

> **"Texto do chat" não pode ser a fonte da verdade para envio.**
> 
> **A fonte da verdade é um objeto (draft_id + revision), e a confirmação sempre envia a última revisão desse objeto.**

---

## ✅ Resultado

- ✅ **Problema resolvido**: Sistema sempre envia a versão mais recente do email
- ✅ **Preview sempre atualizado**: Usuário vê a versão correta antes de confirmar
- ✅ **Banco é fonte da verdade**: Memória desatualizada não causa problemas
- ✅ **Validação de consistência**: Logs ajudam a identificar problemas

---

**Última atualização:** 09/01/2026
