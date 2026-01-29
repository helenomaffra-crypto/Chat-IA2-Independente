# ✅ Checklist: Verificar Certificados Santander

## 🔍 Verificação Manual

**Execute no terminal:**
```bash
cd /Users/helenomaffra/Chat-IA-Independente
grep -E "SANTANDER.*CERT|SANTANDER.*PFX" .env
```

---

## 📋 O que Você Deve Ver

### **✅ Configuração Correta (Recomendada):**

```env
# Certificado compartilhado (Extrato e TED)
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_PFX_PASSWORD=senha001

# TED usará automaticamente o mesmo certificado (fallback)
# Não precisa configurar SANTANDER_PAYMENTS_CERT_PATH
```

**Ou se quiser ser explícito:**
```env
# Extrato
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_PFX_PASSWORD=senha001

# TED (mesmo certificado)
SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

---

## ⚠️ O que Pode Estar Errado

### **Cenário 1: Extrato usando .pem ou .crt + .key**
```env
# ❌ ERRADO (certificado diferente)
SANTANDER_CERT_FILE=/outro/diretorio/cert.pem
SANTANDER_KEY_FILE=/outro/diretorio/key.key

# ✅ CORRETO (mesmo .pfx do TED)
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

### **Cenário 2: Extrato sem certificado configurado**
```env
# ❌ ERRADO (sem certificado)
# (nenhuma linha SANTANDER_CERT_*)

# ✅ CORRETO
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
```

---

## 🔧 Como Corrigir

1. **Editar o `.env`** e garantir que tem:
   ```env
   SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
   SANTANDER_PFX_PASSWORD=senha001
   ```

2. **Remover ou comentar** linhas antigas (se existirem):
   ```env
   # SANTANDER_CERT_FILE=/outro/caminho/cert.pem
   # SANTANDER_KEY_FILE=/outro/caminho/key.key
   ```

3. **Reiniciar a aplicação**

4. **Verificar os logs** - deve aparecer:
   ```
   🔍 [EXTRATO] Certificado configurado: /Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
   ✅ Certificado .pfx convertido automaticamente para uso em mTLS - Extrato: /Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
   ✅ Certificado .pfx convertido automaticamente para uso em mTLS - Pagamentos: /Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
   ```

**Se ambos mostrarem o mesmo caminho:** ✅ Problema resolvido!

---

**Última atualização:** 13/01/2026
