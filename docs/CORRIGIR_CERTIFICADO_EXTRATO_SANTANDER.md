# 🔧 Como Corrigir o Erro 403 no Extrato Santander

## 📋 Problema Identificado

O erro 403 Forbidden está ocorrendo porque o sistema está usando o certificado `.pfx` (`SANTANDER_CERT_PATH`) que pode não estar vinculado à aplicação de **Extrato** no Developer Portal do Santander.

O certificado original (`.pem` + `.key`) que funcionava antes estava vinculado à aplicação de Extrato.

## ✅ Solução

### 1. Editar o arquivo `.env`

Descomente as linhas dos certificados originais:

```env
# ANTES (comentado):
#SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem
#SANTANDER_KEY_FILE=/Users/helenomaffra/SANTANDER/key.pem

# DEPOIS (descomentado):
SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem
SANTANDER_KEY_FILE=/Users/helenomaffra/SANTANDER/key.pem
```

### 2. Comentar ou remover `SANTANDER_CERT_PATH` (opcional)

Se você quiser garantir que o sistema use apenas `cert_file` + `key_file`, comente a linha:

```env
# SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

**OU** deixe como está - o código agora prioriza `cert_file` + `key_file` se ambos existirem.

### 3. Verificar se os arquivos existem

Certifique-se de que os arquivos existem:

```bash
ls -la /Users/helenomaffra/SANTANDER/cert.pem
ls -la /Users/helenomaffra/SANTANDER/key.pem
```

Se os arquivos não existirem, você precisará:
- Extrair do `.pfx` original, ou
- Usar o certificado `.pfx` mas vinculá-lo à aplicação de Extrato no Developer Portal

### 4. Reiniciar o Flask

Após editar o `.env`, **REINICIE o Flask** para carregar as mudanças:

```bash
# Pare o Flask (Ctrl+C) e reinicie:
python3 app.py
```

### 5. Verificar os logs

Ao reiniciar, procure nos logs:

```
🔍 [EXTRATO] Configurando mTLS - cert_file=..., key_file=..., cert_path=...
🔍 [EXTRATO] Verificando cert_file/key_file: cert existe=True, key existe=True
✅ Certificado mTLS configurado (cert + key separados) - Extrato: cert=..., key=...
```

Se aparecer essa mensagem, o sistema está usando os certificados corretos.

## 🔍 Ordem de Prioridade (Código)

O código agora prioriza na seguinte ordem:

1. **PRIORIDADE 1**: `SANTANDER_CERT_FILE` + `SANTANDER_KEY_FILE` (se ambos existirem)
2. **PRIORIDADE 2**: `SANTANDER_CERT_PATH` (usado apenas se `cert_file`/`key_file` não existirem)

## ⚠️ Importante

- **Extrato Santander**: Usa `SANTANDER_CERT_FILE` + `SANTANDER_KEY_FILE` (ou `SANTANDER_CERT_PATH` como fallback)
- **TED Santander**: Usa `SANTANDER_PAYMENTS_CERT_PATH` (separado, não interfere)

Os dois podem usar certificados diferentes sem conflito.

## 🐛 Se Ainda Der Erro 403

Se mesmo com os certificados originais ainda der erro 403:

1. **Verifique no Developer Portal do Santander:**
   - A aplicação de Extrato está ativa?
   - O certificado está vinculado à aplicação?
   - As permissões estão corretas?

2. **Verifique as credenciais:**
   - `SANTANDER_CLIENT_ID` está correto?
   - `SANTANDER_CLIENT_SECRET` está correto?

3. **Verifique o ambiente:**
   - Está usando produção (`trust-open.api.santander.com.br`) ou sandbox?
   - As credenciais correspondem ao ambiente correto?

## 📝 Exemplo de .env Correto

```env
# Certificados mTLS para Extrato (PRIORIDADE 1)
SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem
SANTANDER_KEY_FILE=/Users/helenomaffra/SANTANDER/key.pem

# Certificado .pfx (fallback - PRIORIDADE 2)
# SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
# SANTANDER_PFX_PASSWORD=senha001

# Certificados para TED (separado, não interfere)
SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

---

**Última atualização:** 13/01/2026
