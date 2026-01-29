# 🔧 Como Alterar Certificado do Extrato Santander

## 📋 Situação Atual

**Extrato:**
- ❌ `SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem` (certificado diferente)

**TED:**
- ✅ `SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx` (certificado correto)

---

## ✅ Solução: Usar o Mesmo Certificado

### **Passo 1: Editar o `.env`**

Abra o arquivo `.env` e faça as seguintes alterações:

**1. Comentar ou remover a linha do certificado antigo:**
```env
# SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem
# SANTANDER_KEY_FILE=/Users/helenomaffra/SANTANDER/key.key  # (se existir)
```

**2. Adicionar ou atualizar para usar o mesmo certificado do TED:**
```env
# Certificado compartilhado (Extrato e TED)
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_PFX_PASSWORD=senha001
```

**3. Verificar se a senha está configurada:**
```env
SANTANDER_PFX_PASSWORD=senha001
```

---

## 📝 Exemplo Completo do `.env`

**Antes:**
```env
# Extrato (certificado diferente)
SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem
SANTANDER_KEY_FILE=/Users/helenomaffra/SANTANDER/key.key

# TED (certificado correto)
SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_PFX_PASSWORD=senha001
```

**Depois:**
```env
# Certificado compartilhado (Extrato e TED)
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_PFX_PASSWORD=senha001

# TED (usará automaticamente o SANTANDER_CERT_PATH acima)
# SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
# (pode manter ou remover - o TED usará o fallback)
```

---

## ✅ Verificação Após Alteração

**1. Reiniciar a aplicação**

**2. Verificar os logs na inicialização:**

**Extrato deve mostrar:**
```
🔍 [EXTRATO] Certificado configurado: /Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
✅ Certificado .pfx convertido automaticamente para uso em mTLS - Extrato: /Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

**TED deve mostrar:**
```
✅ Certificado .pfx convertido automaticamente para uso em mTLS - Pagamentos: /Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

**3. Se ambos mostrarem o mesmo caminho:** ✅ Problema resolvido!

---

## 🎯 Resultado Esperado

**Antes:**
- ❌ Extrato: Certificado `.pem` em `/Users/helenomaffra/SANTANDER/`
- ✅ TED: Certificado `.pfx` em `.secure/`
- ⚠️ Certificados diferentes

**Depois:**
- ✅ Extrato: Certificado `.pfx` em `.secure/` (mesmo do TED)
- ✅ TED: Certificado `.pfx` em `.secure/`
- ✅ **Mesmo certificado para ambos**

---

**Última atualização:** 13/01/2026
