# ⚙️ Configurar .env para Santander Extrato

## 📋 Alterações Necessárias no .env

### 1. Descomente/Adicione as linhas dos certificados:

```env
# Certificados mTLS para Extrato (PRIORIDADE 1)
SANTANDER_CERT_FILE=/Users/helenomaffra/Chat-IA-Independente/.secure/santander_extrato_cert.pem
SANTANDER_KEY_FILE=/Users/helenomaffra/Chat-IA-Independente/.secure/santander_extrato_key.pem
```

### 2. Comente a linha do cert_path (para não usar o .pfx):

```env
# SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

### 3. Mantenha as outras configurações:

```env
SANTANDER_CLIENT_ID=zmLpO9gGtIlFnVWfHH4UyklJ3gagclP0
SANTANDER_CLIENT_SECRET=H3leMusxUcRtM6XY
SANTANDER_BASE_URL=https://trust-open.api.santander.com.br
SANTANDER_TOKEN_URL=https://trust-open.api.santander.com.br/auth/oauth/v2/token
SANTANDER_BANK_ID=90400888000142
```

## ✅ Após Configurar

1. **Salve o arquivo `.env`**
2. **Reinicie o Flask** (pare com Ctrl+C e execute `python3 app.py` novamente)
3. **Teste:** Digite "listar contas do santander" no chat

## 🔍 Verificar nos Logs

Ao reiniciar, procure por:

```
🔍 [EXTRATO] Configurando mTLS - cert_file=/Users/helenomaffra/Chat-IA-Independente/.secure/santander_extrato_cert.pem, key_file=/Users/helenomaffra/Chat-IA-Independente/.secure/santander_extrato_key.pem
🔍 [EXTRATO] Verificando cert_file/key_file: cert existe=True, key existe=True
✅ Certificado mTLS configurado (cert + key separados) - Extrato: cert=..., key=...
```

Se aparecer essa mensagem, está correto!

---

**Última atualização:** 13/01/2026
