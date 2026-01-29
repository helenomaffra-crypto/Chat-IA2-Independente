# 🔍 Problema: Certificado .pfx vs .pem no Developer Portal

## 📋 Situação Atual

No **Developer Portal do Santander**, você cadastrou os certificados como **`.pem`** (não `.pfx`). 

O código atual extrai o `.pfx` para um `.pem` **temporário** em tempo de execução, mas esse `.pem` extraído pode não ser exatamente o mesmo certificado que foi cadastrado no Developer Portal.

## ⚠️ Por que isso causa erro 403?

O erro 403 Forbidden ocorre porque:
1. O Developer Portal espera o certificado **`.pem`** que foi cadastrado
2. O código está extraindo o `.pfx` para um `.pem` temporário
3. Esse `.pem` temporário pode ser diferente do que foi cadastrado (mesmo que venha do mesmo `.pfx`)

## ✅ Solução: Usar os arquivos `.pem` originais

### Opção 1: Se você já tem os arquivos `.pem` originais

Se você ainda tem os arquivos `.pem` que foram cadastrados no Developer Portal:

1. **Configure no `.env`:**
   ```env
   SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem
   SANTANDER_KEY_FILE=/Users/helenomaffra/SANTANDER/key.pem
   ```

2. **Comente ou remova `SANTANDER_CERT_PATH`:**
   ```env
   # SANTANDER_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
   ```

3. **Reinicie o Flask**

### Opção 2: Extrair `.pem` permanente do `.pfx`

Se você não tem mais os arquivos `.pem` originais, extraia do `.pfx` de forma **permanente**:

1. **Execute o script:**
   ```bash
   python3 scripts/extrair_pem_do_pfx_santander.py
   ```

2. **O script criará:**
   - `/Users/helenomaffra/SANTANDER/cert.pem` (certificado)
   - `/Users/helenomaffra/SANTANDER/key.pem` (chave privada)
   - `/Users/helenomaffra/SANTANDER/certificado.pem` (combinado)

3. **Configure no `.env`:**
   ```env
   SANTANDER_CERT_FILE=/Users/helenomaffra/SANTANDER/cert.pem
   SANTANDER_KEY_FILE=/Users/helenomaffra/SANTANDER/key.pem
   ```

4. **Cadastre esses arquivos no Developer Portal:**
   - Acesse o Developer Portal do Santander
   - Faça upload do `cert.pem` e `key.pem` (ou `certificado.pem` combinado)
   - Certifique-se de que são os mesmos arquivos que você vai usar no `.env`

5. **Reinicie o Flask**

## 🔍 Como verificar se está correto

Após reiniciar o Flask, procure nos logs:

```
🔍 [EXTRATO] Configurando mTLS - cert_file=/Users/helenomaffra/SANTANDER/cert.pem, key_file=/Users/helenomaffra/SANTANDER/key.pem, cert_path=...
🔍 [EXTRATO] Verificando cert_file/key_file: cert existe=True, key existe=True
✅ Certificado mTLS configurado (cert + key separados) - Extrato: cert=..., key=...
```

Se aparecer essa mensagem, o sistema está usando os certificados corretos.

## 📝 Diferença entre Extrato e TED

- **Extrato Santander**: Deve usar os arquivos `.pem` cadastrados no Developer Portal
- **TED Santander**: Pode usar `.pfx` (extração automática) porque é uma aplicação diferente

## ⚠️ Importante

**NUNCA** use certificados diferentes entre o Developer Portal e o código. Eles devem ser **exatamente os mesmos**.

Se você extrair o `.pem` do `.pfx`:
1. Use os arquivos `.pem` extraídos **permanentemente** (não temporários)
2. Cadastre esses mesmos arquivos no Developer Portal
3. Configure no `.env` para usar esses arquivos

---

**Última atualização:** 13/01/2026
