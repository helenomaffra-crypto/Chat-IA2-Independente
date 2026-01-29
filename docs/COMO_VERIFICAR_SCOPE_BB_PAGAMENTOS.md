# 🔍 Como Verificar o Scope Correto da API de Pagamentos em Lote do BB

## 📋 Visão Geral

O erro `invalid_scope` indica que o scope solicitado não está autorizado para sua aplicação. Este guia ajuda a identificar e corrigir o problema.

---

## 🔑 Passo 1: Verificar o Scope na Documentação da API

### 1.1 Acessar a Documentação OpenAPI

1. Acesse: https://apoio.developers.bb.com.br/sandbox/spec/61bc753bd9b75d00121497a1
2. Procure pela seção **"securitySchemes"** ou **"security"**
3. Dentro dessa seção, procure por **"scopes"**
4. Anote o nome exato do scope (é case-sensitive!)

### 1.2 Exemplo de onde encontrar

Na documentação OpenAPI, o scope geralmente aparece assim:

```yaml
securitySchemes:
  OAuth2:
    type: oauth2
    flows:
      clientCredentials:
        scopes:
          pagamento-lote: Descrição do scope
          # OU
          pagamentos-lote: Descrição do scope
          # OU outro nome
```

---

## 🔍 Passo 2: Verificar no Portal do BB

### 2.1 Acessar o Portal

1. Acesse: https://developers.bb.com.br/
2. Faça login com suas credenciais
3. Selecione sua aplicação

### 2.2 Verificar Scopes Autorizados

1. No menu lateral, procure por:
   - **"APIs"**
   - **"Scopes"**
   - **"Autorizações"**
   - **"Permissões"**

2. Verifique se o scope `pagamento-lote` (ou o nome encontrado na documentação) está listado como **autorizado**

3. Se não estiver:
   - Clique em **"Solicitar Acesso"** ou **"Adicionar API"**
   - Selecione **"API de Pagamentos em Lote"**
   - Solicite o scope necessário
   - Aguarde aprovação

### 2.3 Verificar Aplicação Correta

⚠️ **IMPORTANTE:** Certifique-se de que está verificando a aplicação **correta**:

- **API de Extratos** → Aplicação com scope `extrato-info`
- **API de Pagamentos em Lote** → Aplicação com scope `pagamento-lote`

**Verifique:**
- O `Client ID` no portal corresponde ao `BB_PAYMENTS_CLIENT_ID` no `.env`
- A aplicação está cadastrada para a API de **Pagamentos em Lote** (não Extratos)

---

## 🔧 Passo 3: Verificar Credenciais no .env

### 3.1 Verificar se as credenciais estão corretas

```env
# ✅ Credenciais da API de Pagamentos em Lote
BB_PAYMENTS_CLIENT_ID=eyJpZCI6IjVmYWYwM2MtMzFkNC00Ii...
BB_PAYMENTS_CLIENT_SECRET=eyJpZCI6IjhmNDQ3NGEtZDA0NC00YS...
BB_PAYMENTS_DEV_APP_KEY=1f8386d110934639a2790912c5bba906
BB_PAYMENTS_ENVIRONMENT=sandbox
```

### 3.2 Verificar se não está usando credenciais de Extratos

❌ **ERRADO:**
```env
# Estas são credenciais de Extratos, não de Pagamentos!
BB_CLIENT_ID=...  # ❌ Não usar para Pagamentos
BB_CLIENT_SECRET=...  # ❌ Não usar para Pagamentos
```

✅ **CORRETO:**
```env
# Credenciais específicas para Pagamentos
BB_PAYMENTS_CLIENT_ID=...  # ✅ Correto
BB_PAYMENTS_CLIENT_SECRET=...  # ✅ Correto
```

---

## 🧪 Passo 4: Testar com Scope Diferente (se necessário)

Se o scope `pagamento-lote` não funcionar, tente variações:

### 4.1 Possíveis nomes de scope

1. `pagamento-lote` (sem "s")
2. `pagamentos-lote` (com "s")
3. `cobrancas.pagamento-lote` (com prefixo)
4. Outro nome conforme documentação OpenAPI

### 4.2 Como testar

Você pode temporariamente modificar o scope no código para testar:

```python
# Em utils/banco_brasil_payments_api.py, linha ~237
data = {
    "grant_type": "client_credentials",
    "scope": "pagamentos-lote"  # Tentar com "s"
    # OU
    "scope": "cobrancas.pagamento-lote"  # Tentar com prefixo
}
```

⚠️ **ATENÇÃO:** Volte para o scope correto após identificar qual funciona!

---

## ✅ Checklist de Verificação

Antes de testar novamente, verifique:

- [ ] ✅ Scope verificado na documentação OpenAPI da API de Pagamentos em Lote
- [ ] ✅ Scope autorizado no portal do BB para sua aplicação
- [ ] ✅ Aplicação correta selecionada (Pagamentos, não Extratos)
- [ ] ✅ `BB_PAYMENTS_CLIENT_ID` corresponde ao Client ID no portal
- [ ] ✅ `BB_PAYMENTS_CLIENT_SECRET` corresponde ao Client Secret no portal
- [ ] ✅ `BB_PAYMENTS_DEV_APP_KEY` configurado corretamente
- [ ] ✅ Ambiente configurado como `sandbox` (ou `BB_PAYMENTS_ENVIRONMENT=sandbox`)
- [ ] ✅ Token URL correto: `https://oauth.sandbox.bb.com.br/oauth/token` (sandbox - conforme documentação da API de Pagamentos)

---

## 📞 Próximos Passos

Se após verificar todos os itens acima o erro persistir:

1. **Contatar suporte do BB:**
   - Portal: https://developers.bb.com.br/
   - Fórum: Área logada do portal → Fórum
   - Solicitar autorização do scope `pagamento-lote` para sua aplicação

2. **Verificar se a aplicação está aprovada:**
   - Algumas APIs requerem aprovação prévia
   - Verifique o status da aplicação no portal

3. **Verificar se está usando ambiente correto:**
   - Sandbox: `https://oauth.sandbox.bb.com.br/oauth/token` (conforme documentação da API de Pagamentos)
   - Produção: `https://oauth.bb.com.br/oauth/token`
   - Certifique-se de usar credenciais do ambiente correto

---

## 📚 Documentação Relacionada

- **Troubleshooting**: `docs/TROUBLESHOOTING_BB_PAGAMENTOS.md`
- **Credenciais**: `docs/CREDENCIAIS_BB_PAGAMENTOS.md`
- **Como Testar**: `docs/COMO_TESTAR_BB_PAGAMENTOS.md`
- **API Oficial**: https://apoio.developers.bb.com.br/sandbox/spec/61bc753bd9b75d00121497a1
