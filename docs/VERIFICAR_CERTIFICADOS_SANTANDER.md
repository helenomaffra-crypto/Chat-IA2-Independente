# 🔐 Como Verificar Certificados Santander

## 📋 Verificação Rápida

**Comando para verificar no terminal:**
```bash
cd /Users/helenomaffra/Chat-IA-Independente
grep -E "SANTANDER.*CERT|SANTANDER.*PFX" .env
```

---

## 🔍 O que Verificar

### **1. Certificado do Extrato**
```env
SANTANDER_CERT_PATH=/caminho/para/certificado.pfx
# ou
SANTANDER_CERT_FILE=/caminho/para/cert.pem
SANTANDER_KEY_FILE=/caminho/para/key.key
```

### **2. Certificado do TED**
```env
SANTANDER_PAYMENTS_CERT_PATH=/caminho/para/certificado.pfx
# ou (fallback para SANTANDER_CERT_PATH)
# Se não configurado, usa SANTANDER_CERT_PATH automaticamente
```

### **3. Senha do .pfx**
```env
SANTANDER_PFX_PASSWORD=senha001
```

---

## ✅ Configuração Recomendada (Usar Mesmo Certificado)

**Para usar o mesmo certificado em ambos (RECOMENDADO):**

```env
# Certificado compartilhado (Extrato e TED)
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_PFX_PASSWORD=senha001

# TED usará automaticamente o mesmo certificado (fallback)
# Não precisa configurar SANTANDER_PAYMENTS_CERT_PATH
```

**Vantagens:**
- ✅ Um único certificado para gerenciar
- ✅ Ambos os serviços usam o mesmo certificado
- ✅ Mais simples de manter

---

## 🔍 Verificar nos Logs

**Após reiniciar a aplicação, você deve ver:**

### **Extrato:**
```
🔍 [EXTRATO] Certificado configurado: /path/to/cert.pfx
✅ Certificado .pfx convertido automaticamente para uso em mTLS - Extrato: /path/to/cert.pfx
```

### **TED:**
```
✅ Certificado .pfx convertido automaticamente para uso em mTLS - Pagamentos: /path/to/cert.pfx
```

**Se ambos mostrarem o mesmo caminho:** ✅ Estão usando o mesmo certificado!

**Se mostrarem caminhos diferentes:** ⚠️ Estão usando certificados diferentes

---

## 🛠️ Como Corrigir

**Se o Extrato não estiver usando o mesmo certificado:**

1. **Editar o `.env`** e configurar:
   ```env
   SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
   SANTANDER_PFX_PASSWORD=senha001
   ```

2. **Remover configurações antigas** (se houver):
   ```env
   # Comentar ou remover estas linhas se existirem:
   # SANTANDER_CERT_FILE=/outro/caminho/cert.pem
   # SANTANDER_KEY_FILE=/outro/caminho/key.key
   ```

3. **Reiniciar a aplicação** para carregar as novas configurações

4. **Verificar os logs** para confirmar que ambos estão usando o mesmo certificado

---

## 📊 Comparação: Antes vs Depois

### **Antes (Problema):**
- ❌ Extrato: Certificado `.pem` ou `.crt` + `.key` (outro diretório)
- ✅ TED: Certificado `.pfx` (diretório `.secure/`)
- ⚠️ Certificados diferentes

### **Depois (Corrigido):**
- ✅ Extrato: Certificado `.pfx` (diretório `.secure/`) - **NOVO**
- ✅ TED: Certificado `.pfx` (diretório `.secure/`)
- ✅ **Mesmo certificado para ambos**

---

**Última atualização:** 13/01/2026
