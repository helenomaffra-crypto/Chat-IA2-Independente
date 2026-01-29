# Troubleshooting - API de Pagamentos em Lote do Banco do Brasil

## ❌ Erro: "Failed to resolve 'oauth.bb.com.br'"

**Causa:** O ambiente está configurado como `production` quando deveria ser `sandbox`.

**Solução:**
1. Verifique o `.env`:
```env
# ✅ RECOMENDADO: Use variável específica para Pagamentos
BB_PAYMENTS_ENVIRONMENT=sandbox  # Para API de Pagamentos

# OU use fallback genérico (se não configurar BB_PAYMENTS_ENVIRONMENT)
BB_ENVIRONMENT=sandbox  # Fallback (usado também pela API de Extratos)
```

2. **⚠️ IMPORTANTE:** 
   - `BB_PAYMENTS_ENVIRONMENT` tem prioridade sobre `BB_ENVIRONMENT`
   - Isso permite ter Extratos em produção e Pagamentos em sandbox simultaneamente
   - Exemplo:
     ```env
     BB_ENVIRONMENT=production  # Para Extratos
     BB_PAYMENTS_ENVIRONMENT=sandbox  # Para Pagamentos
     ```

3. Se não configurar nenhum, o padrão é `sandbox` ✅

## ❌ Erro: "invalid_scope" - "Cliente nao possui autorizacao para nenhum dos escopos solicitados"

**Causa:** O scope `pagamento-lote` não está autorizado para esta aplicação no portal do BB.

**Soluções:**

### 1. Verificar Scope no Portal do BB

1. Acesse: https://developers.bb.com.br/
2. Faça login e selecione sua aplicação
3. Vá em **"APIs"** ou **"Scopes"** no menu lateral
4. Verifique se o scope `pagamento-lote` está **autorizado**
5. Se não estiver, solicite a autorização do scope

### 2. Verificar se está usando a aplicação correta

⚠️ **IMPORTANTE:** Cada API do BB requer uma aplicação separada:
- **API de Extratos** → Aplicação com scope `extrato-info`
- **API de Pagamentos em Lote** → Aplicação com scope `pagamento-lote`

**Verifique:**
- As credenciais (`BB_PAYMENTS_CLIENT_ID` e `BB_PAYMENTS_CLIENT_SECRET`) são da aplicação de **Pagamentos**, não de Extratos
- A aplicação está cadastrada para a API de **Pagamentos em Lote**

### 3. Verificar nome do scope

O scope pode ter um nome diferente. Verifique na documentação da API:
- Documentação oficial: https://apoio.developers.bb.com.br/sandbox/spec/61bc753bd9b75d00121497a1
- Procure na seção "securitySchemes" → "scopes" do OpenAPI

**Possíveis nomes de scope:**
- `pagamento-lote` (mais comum)
- `pagamentos-lote` (com "s")
- `cobrancas.pagamento-lote` (com prefixo)
- Outro nome conforme documentação

### 4. Solicitar autorização do scope

Se o scope não estiver autorizado:

1. Acesse o portal do BB: https://developers.bb.com.br/
2. Selecione sua aplicação
3. Vá em **"APIs"** ou **"Solicitar Acesso"**
4. Selecione **"API de Pagamentos em Lote"**
5. Solicite acesso ao scope necessário
6. Aguarde aprovação (pode levar alguns dias)

### 5. Verificar logs

Os logs devem mostrar:
```
🔑 Scope solicitado: pagamento-lote
❌ Resposta JSON (dict): {'error': 'invalid_scope', 'error_description': 'Cliente nao possui autorizacao para nenhum dos escopos solicitados'}
```

Se o erro persistir após verificar os itens acima, o problema é que:
- A aplicação não tem o scope autorizado no portal do BB
- As credenciais são de uma aplicação diferente (Extratos vs Pagamentos)

## ❌ Erro: "Software não cadastrado" (400 Bad Request)

**Causa:** As credenciais não estão corretas ou a aplicação não está cadastrada no portal do BB.

**Soluções:**

### 1. Verificar Credenciais

Certifique-se de que as credenciais no `.env` estão corretas:

```env
BB_PAYMENTS_CLIENT_ID=eyJpZCI6IjVmYWYwM2MtMzFkNC00Ii...
BB_PAYMENTS_CLIENT_SECRET=eyJpZCI6IjhmNDQ3NGEtZDA0NC00YS...
BB_PAYMENTS_DEV_APP_KEY=1f8386d110934639a2790912c5bba906
```

**⚠️ IMPORTANTE:** 
- Use credenciais de **SANDBOX** (não produção)
- Cada API tem credenciais **SEPARADAS** (Extrato ≠ Pagamento)

### 2. Verificar Portal do BB

1. Acesse: https://developers.bb.com.br/
2. Verifique se a aplicação está cadastrada
3. Verifique se o scope `pagamento-lote` está **autorizado**
4. Verifique se está usando a aplicação correta (não a de Extratos)

### 3. Verificar Ambiente

O erro pode ocorrer se:
- Estiver usando credenciais de produção em sandbox
- Estiver usando credenciais de sandbox em produção
- A URL do token estiver incorreta

**Verifique os logs:**
```
🔍 Ambiente BB Pagamentos: sandbox (BB_PAYMENTS_ENVIRONMENT=sandbox)
🔍 BB Pagamentos - Token URL: https://oauth.sandbox.bb.com.br/oauth/token
🔍 BB Pagamentos - Base URL: https://homologa-api-ip.bb.com.br:7144/pagamentos-lote/v1
```

**URLs corretas (sandbox):**
- Token: `https://oauth.sandbox.bb.com.br/oauth/token` ✅
- Base: `https://homologa-api-ip.bb.com.br:7144/pagamentos-lote/v1` ✅

Se aparecer URLs diferentes, verifique a configuração.

### 4. Verificar Scope

O scope deve ser exatamente `pagamento-lote` (sem espaços extras ou maiúsculas).

## ✅ Checklist de Verificação

Antes de testar, verifique:

- [ ] `BB_ENVIRONMENT=sandbox` (ou não configurado)
- [ ] `BB_PAYMENTS_CLIENT_ID` configurado (credenciais de SANDBOX)
- [ ] `BB_PAYMENTS_CLIENT_SECRET` configurado (credenciais de SANDBOX)
- [ ] `BB_PAYMENTS_DEV_APP_KEY` configurado
- [ ] Aplicação cadastrada no portal do BB
- [ ] Scope `pagamento-lote` autorizado
- [ ] Token URL: `https://oauth.hm.bb.com.br/oauth/token` (sandbox)

## 🔍 Logs de Debug

Para ver logs detalhados, o debug já está habilitado por padrão. Os logs mostrarão:

```
🔍 BB Pagamentos - Ambiente: sandbox, Token URL: https://oauth.hm.bb.com.br/oauth/token
🔑 Tentando obter token OAuth de: https://oauth.hm.bb.com.br/oauth/token
```

Se aparecer `oauth.bb.com.br` (sem `.hm`), configure `BB_PAYMENTS_ENVIRONMENT=sandbox` (ou `BB_ENVIRONMENT=sandbox` como fallback).

## 📚 Documentação Adicional

- **Credenciais**: `docs/CREDENCIAIS_BB_PAGAMENTOS.md`
- **Como Testar**: `docs/COMO_TESTAR_BB_PAGAMENTOS.md`
- **API Oficial**: https://apoio.developers.bb.com.br/sandbox/spec/61bc753bd9b75d00121497a1
