# ✅ Certificado Aprovado - Próximos Passos

**Data:** 13/01/2026  
**Status:** ✅ Certificado aprovado no ambiente TESTE

---

## 📋 Informações do Certificado

- **Ambiente:** TESTE (Sandbox)
- **Nome:** 4PL APOIO ADMINISTRATIVO E COBRANCA EXTRA JUDICIA
- **CNPJ:** 19558226000130
- **Data de envio:** 13/01/2026 17:55:59
- **Vencimento:** 24/03/2026
- **Situação:** ✅ Aprovado

---

## 🎯 Próximos Passos

### 1. Verificar se o Scope está Autorizado

O certificado está aprovado, mas você ainda precisa verificar se o **scope** está autorizado:

1. Acesse: https://developers.bb.com.br/
2. Selecione a aplicação **ID 246367** (Pagamentos em Lote)
3. Vá na aba **"APIs"** ou **"Scopes"**
4. Verifique se o scope `pagamento-lote` está **autorizado**

**Se o scope NÃO estiver autorizado:**
- Clique em **"Solicitar Acesso"** ou **"Adicionar API"**
- Selecione **"Pagamentos em Lote"**
- Solicite o scope necessário
- Aguarde aprovação (geralmente imediata para sandbox)

---

### 2. Testar a API de Pagamentos

Após verificar/autorizar o scope, teste a API:

```bash
python3 testes/test_bb_pagamento_lote_uso.py
```

Este teste vai:
- ✅ Listar lotes existentes
- ✅ Verificar se a autenticação funciona
- ✅ Testar se o scope está autorizado

**Se der erro `invalid_scope`:**
- O scope ainda não está autorizado
- Siga o passo 1 acima para autorizar

**Se funcionar:**
- ✅ Certificado OK
- ✅ Scope OK
- ✅ API pronta para uso!

---

### 3. Testar no Chat (Opcional)

Após confirmar que os testes passam, você pode testar no chat:

```
maike listar lotes de pagamento bb
```

---

## ⚠️ Troubleshooting

### Erro: `invalid_scope`

**Causa:** Scope `pagamento-lote` não está autorizado para a aplicação.

**Solução:**
1. Acesse o portal do BB
2. Vá em "APIs" ou "Scopes"
3. Autorize o scope `pagamento-lote`
4. Aguarde aprovação
5. Teste novamente

### Erro: `401 Unauthorized`

**Causa:** Credenciais incorretas ou não configuradas.

**Solução:**
1. Verifique se `BB_PAYMENTS_CLIENT_ID`, `BB_PAYMENTS_CLIENT_SECRET`, `BB_PAYMENTS_DEV_APP_KEY` estão no `.env`
2. Verifique se as credenciais são da aplicação **correta** (ID 246367)
3. Verifique se não está usando credenciais da API de Extratos por engano

### Erro: `403 Forbidden`

**Causa:** Certificado não está aprovado ou aplicação não tem permissão.

**Solução:**
1. Verifique se o certificado está aprovado (já está ✅)
2. Verifique se está usando a aplicação correta
3. Aguarde alguns minutos após aprovação (pode levar tempo para propagar)

---

## 📚 Documentação Relacionada

- **Credenciais:** `docs/CREDENCIAIS_BB_PAGAMENTOS.md`
- **Como Testar:** `docs/COMO_TESTAR_BB_PAGAMENTOS.md`
- **Troubleshooting:** `docs/TROUBLESHOOTING_BB_PAGAMENTOS.md`
- **Verificar Scope:** `docs/COMO_VERIFICAR_SCOPE_BB_PAGAMENTOS.md`

---

**Última atualização:** 13/01/2026

