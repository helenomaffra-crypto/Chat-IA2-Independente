# 🔐 Correção: Certificados Santander - Extrato e TED

## 📋 Problema Identificado (13/01/2026)

**Situação:**
- ✅ **TED Santander**: Funcionando corretamente com certificado `.pfx` no diretório
- ⚠️ **Extrato Santander**: Funcionando mas usando certificado de outro diretório (não tinha suporte para `.pfx`)

**Causa:**
- O serviço de **Extrato** (`SantanderExtratoAPI`) não tinha suporte para arquivos `.pfx`
- O serviço de **TED** (`SantanderPaymentsAPI`) já tinha suporte para `.pfx` (extração automática)
- Isso fazia com que ambos usassem certificados diferentes quando o certificado estava em formato `.pfx`

---

## ✅ Correção Implementada

### **Adicionado Suporte para .pfx no Extrato**

**Arquivo Modificado:** `utils/santander_api.py`

**Mudanças:**
1. ✅ Adicionado método `_extrair_pfx_para_pem()` (igual ao TED)
2. ✅ Modificado `_setup_mtls()` para detectar e extrair `.pfx` automaticamente
3. ✅ Adicionado `__del__()` para limpar arquivos temporários
4. ✅ Adicionado atributo `_temp_cert_file` para rastrear arquivos temporários

**Comportamento Agora:**
- Se `SANTANDER_CERT_PATH` apontar para um arquivo `.pfx`, o sistema extrai automaticamente
- Usa a mesma senha do TED: `SANTANDER_PFX_PASSWORD` (ou padrão "senha001")
- Cria arquivo temporário `.pem` que é limpo automaticamente

---

## 🔧 Configuração Recomendada

### **Opção 1: Usar o Mesmo Certificado para Ambos (RECOMENDADO)**

```env
# Certificado compartilhado (Extrato e TED)
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/certificado.pfx
SANTANDER_PFX_PASSWORD=senha001

# TED usará o mesmo certificado (fallback automático)
# SANTANDER_PAYMENTS_CERT_PATH=  # Não precisa configurar - usa SANTANDER_CERT_PATH
```

**Vantagens:**
- ✅ Um único certificado para gerenciar
- ✅ Ambos os serviços usam o mesmo certificado
- ✅ Mais simples de manter

### **Opção 2: Certificados Separados (Se Necessário)**

```env
# Certificado para Extrato
SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/certificado_extrato.pfx
SANTANDER_PFX_PASSWORD=senha001

# Certificado para TED (separado)
SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/certificado_ted.pfx
SANTANDER_PAYMENTS_PFX_PASSWORD=senha001
```

**Quando usar:**
- Se você criou aplicações separadas no Developer Portal do Santander
- Se cada aplicação requer certificado diferente

---

## 📊 Ordem de Prioridade dos Certificados

### **Extrato Santander:**
1. `SANTANDER_CERT_PATH` (arquivo `.pfx` ou `.pem`)
2. `SANTANDER_CERT_FILE` + `SANTANDER_KEY_FILE` (separados)

### **TED Santander:**
1. `SANTANDER_PAYMENTS_CERT_PATH` (específico para pagamentos)
2. Se não encontrar, usa `SANTANDER_CERT_PATH` (fallback)
3. `SANTANDER_PAYMENTS_CERT_FILE` + `SANTANDER_PAYMENTS_KEY_FILE`
4. Se não encontrar, usa `SANTANDER_CERT_FILE` + `SANTANDER_KEY_FILE` (fallback)

**Senha do .pfx:**
- Extrato: `SANTANDER_PFX_PASSWORD` (padrão: "senha001")
- TED: `SANTANDER_PAYMENTS_PFX_PASSWORD` ou `SANTANDER_PFX_PASSWORD` (fallback)

---

## ✅ Verificação

**Como verificar se ambos estão usando o mesmo certificado:**

1. **Verificar logs na inicialização:**
   ```
   ✅ Certificado .pfx convertido automaticamente para uso em mTLS - Extrato: /path/to/cert.pfx
   ✅ Certificado .pfx convertido automaticamente para uso em mTLS - Pagamentos: /path/to/cert.pfx
   ```

2. **Verificar variáveis de ambiente:**
   ```bash
   grep SANTANDER.*CERT .env
   grep SANTANDER.*PFX .env
   ```

3. **Testar ambos os serviços:**
   - Extrato: "listar contas do santander"
   - TED: "listar workspaces do santander"

---

## 🎯 Resultado Esperado

**Agora:**
- ✅ Ambos os serviços suportam `.pfx` automaticamente
- ✅ Ambos podem usar o mesmo certificado (configuração recomendada)
- ✅ Logs mostram qual certificado está sendo usado
- ✅ Arquivos temporários são limpos automaticamente

**Antes:**
- ❌ Extrato não suportava `.pfx` (só `.pem` ou `.crt` + `.key`)
- ❌ TED suportava `.pfx` mas Extrato não
- ⚠️ Podiam usar certificados diferentes

---

**Última atualização:** 13/01/2026
