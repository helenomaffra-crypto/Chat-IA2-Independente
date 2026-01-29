# 🔧 Configurar Sandbox Santander - Credenciais

**Data:** 12/01/2026  
**Credenciais fornecidas:** Sandbox Santander Payments

---

## 📋 Credenciais do Sandbox

```
Client ID: 4zhVGn73MqPUSSvKhARMurKm13Dqt4BX
Client Secret: a05tNBQ6m1zU1qo5
```

---

## 🔧 Como Adicionar ao `.env`

Abra o arquivo `.env` na raiz do projeto e adicione as seguintes linhas:

```env
# ==========================================
# SANTANDER - PAGAMENTOS (SANDBOX/TESTE)
# ==========================================
# ⚠️ URLs de SANDBOX (não produção!)
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
SANTANDER_PAYMENTS_TOKEN_URL=https://trust-sandbox.api.santander.com.br/auth/oauth/v2/token

# Credenciais de SANDBOX (obtidas no portal de desenvolvedor)
SANTANDER_PAYMENTS_CLIENT_ID=4zhVGn73MqPUSSvKhARMurKm13Dqt4BX
SANTANDER_PAYMENTS_CLIENT_SECRET=a05tNBQ6m1zU1qo5

# Certificados (usar os mesmos do extrato ou configurar separadamente)
# SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
# SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.key

# Workspace será criado automaticamente no sandbox
# SANTANDER_WORKSPACE_ID=
```

---

## ✅ Verificação

Após adicionar, verifique se está correto:

```bash
# Verificar se as variáveis foram adicionadas
grep SANTANDER_PAYMENTS .env
```

Você deve ver:
- `SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br`
- `SANTANDER_PAYMENTS_CLIENT_ID=4zhVGn73MqPUSSvKhARMurKm13Dqt4BX`
- `SANTANDER_PAYMENTS_CLIENT_SECRET=a05tNBQ6m1zU1qo5`

---

## 🧪 Testar Configuração

Após adicionar as credenciais, teste no chat:

```
👤 "listar workspaces do santander"
```

Se estiver configurado corretamente, o mAIke deve:
- ✅ Conectar ao sandbox
- ✅ Listar workspaces (ou criar um se não existir)
- ✅ Mostrar aviso "(SANDBOX - TESTE)"

---

## ⚠️ Importante

### Certificados mTLS

✅ **SIM, você pode usar os MESMOS certificados** do Santander Extratos para Pagamentos.

O código já está configurado para fazer **fallback automático**:
- Se `SANTANDER_PAYMENTS_CERT_FILE` não estiver configurado
- O sistema usa automaticamente `SANTANDER_CERT_FILE` (do extrato)

**Opção 1: Usar os mesmos (Recomendado)**
```env
# Se já tem SANTANDER_CERT_FILE e SANTANDER_KEY_FILE configurados,
# o sistema vai usar automaticamente como fallback.
# Não precisa configurar nada adicional!
```

**Opção 2: Certificados separados (Opcional)**
```env
# Apenas se quiser usar certificados diferentes:
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key.key
```

📚 **Documentação completa:** Veja `docs/CERTIFICADOS_MTLS_SANTANDER.md` para detalhes.

### Workspace

O workspace será criado automaticamente quando você usar pela primeira vez:

```
👤 "criar workspace santander agencia 3003 conta 000130827180"
```

Ou configure manualmente no `.env` se já tiver um workspace ID:

```env
SANTANDER_WORKSPACE_ID=workspace_id_aqui
```

---

## 🔒 Segurança

⚠️ **NUNCA commite o arquivo `.env` no git!**

O arquivo `.env` já deve estar no `.gitignore`. Verifique:

```bash
grep "\.env" .gitignore
```

Se não estiver, adicione:

```
.env
*.env
```

---

## 📝 Próximos Passos

1. ✅ Adicionar credenciais ao `.env`
2. ✅ Configurar certificados (se necessário)
3. ✅ Testar no chat: "listar workspaces do santander"
4. ✅ Criar workspace: "criar workspace santander agencia X conta Y"
5. ✅ Testar TED: "fazer ted de 100 reais para conta 1234..."

---

**Última atualização:** 12/01/2026
