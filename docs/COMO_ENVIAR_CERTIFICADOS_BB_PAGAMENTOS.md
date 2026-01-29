# 🔐 Como Enviar Certificados para API de Pagamentos em Lote - Banco do Brasil

**Data:** 13/01/2026  
**Aplicação:** ID 246367 - Pagamentos em Lote  
**Status:** ⚠️ **OBRIGATÓRIO** - A API de Pagamentos requer mTLS (mutual TLS)

---

## 📋 Visão Geral

A API de Pagamentos em Lote do Banco do Brasil **requer certificados mTLS** para funcionar. Você precisa enviar a **cadeia completa de certificados** no portal do BB.

---

## ✅ Passo 1: Verificar se os Certificados Já Foram Extraídos

Os certificados já foram extraídos anteriormente para a API de Extratos. Verifique se existem:

```bash
cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb
ls -la *.pem
```

Você deve ver:
- ✅ `certificado_empresa.pem` - Certificado da empresa
- ✅ `ac_safeweb_rfb_v5.pem` - Certificado intermediário
- ✅ `ac_raiz_brasileira_v5.pem` - Certificado raiz
- ✅ `cadeia_completa_para_importacao.pem` - **Cadeia completa pronta para importar**

---

## 📤 Passo 2: Enviar Certificados no Portal do BB

### 2.1 Acessar o Portal

1. Acesse: https://developers.bb.com.br/
2. Faça login
3. Selecione a aplicação **ID 246367** (Pagamentos em Lote)
4. Vá na aba **"Certificado"** (menu lateral)

### 2.2 Importar Cadeia Completa (Recomendado)

**Opção mais fácil:**

1. Clique em **"Importar cadeia completa"**
2. Selecione o arquivo: `/Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb/cadeia_completa_para_importacao.pem`
3. Clique em **"Enviar"**

### 2.3 Enviar Individualmente (Alternativa)

Se preferir enviar separadamente:

1. **Certificado Raiz:**
   - Clique em "Certificado Raiz"
   - Selecione: `ac_raiz_brasileira_v5.pem`
   - Clique em "Enviar"

2. **Certificado Intermediário:**
   - Clique em "Certificado Intermediário"
   - Selecione: `ac_safeweb_rfb_v5.pem`
   - Clique em "Enviar"

3. **Certificado Empresa:**
   - Clique em "Certificado Empresa"
   - Selecione: `certificado_empresa.pem`
   - Clique em "Enviar"

---

## ⚙️ Passo 3: Configurar no Código (Opcional - para uso local)

Se você quiser usar os certificados localmente também (para testes), configure no `.env`:

```env
# Banco do Brasil - Pagamentos em Lote - Certificado mTLS
BB_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ 4PL (valid 23-03-26) senha001.pfx
BB_PAYMENTS_PFX_PASSWORD=senha001
```

**Nota:** O código suporta `.pfx` diretamente e extrai automaticamente o certificado com chave privada.

---

## ✅ Passo 4: Verificar Envio

Após enviar, você deve ver no portal:

- ✅ **Certificado Raiz**: Carregado
- ✅ **Certificado Intermediário**: Carregado
- ✅ **Certificado Empresa**: Carregado

**⚠️ IMPORTANTE:** Aguarde até **3 dias úteis** para aprovação dos certificados.

---

## 🔍 Verificar Formato da Cadeia

Antes de enviar, você pode verificar se a cadeia está no formato correto:

```bash
cd /Users/helenomaffra/Chat-IA-Independente/.secure/certificados_bb

# Verificar quantos certificados tem
grep -c "BEGIN CERTIFICATE" cadeia_completa_para_importacao.pem
# Deve retornar: 3

# Verificar formato (deve ter apenas blocos BEGIN/END CERTIFICATE)
head -20 cadeia_completa_para_importacao.pem
```

O arquivo deve conter apenas blocos como:
```
-----BEGIN CERTIFICATE-----
[conteúdo base64]
-----END CERTIFICATE-----
```

**Sem metadados** como "Bag Attributes" ou outras informações.

---

## 📚 Documentação Relacionada

- **Guia de Extração**: `EXTRAIR_CERTIFICADO_BB.md`
- **Integração BB**: `docs/integracoes/INTEGRACAO_BANCO_BRASIL.md` (seção "Cadeia Completa de Certificados")
- **Portal BB**: https://developers.bb.com.br/

---

## ⚠️ Troubleshooting

### Erro: "Certificado inválido"

- Verifique se o arquivo está em formato PEM (Base 64)
- Verifique se não há metadados extras (apenas blocos BEGIN/END CERTIFICATE)
- Verifique se a cadeia está completa (3 certificados)

### Erro: "Certificado não encontrado"

- Verifique se os arquivos existem em `.secure/certificados_bb/`
- Se não existirem, execute os comandos em `EXTRAIR_CERTIFICADO_BB.md`

### Erro: "Aguardando aprovação"

- Normal! Aguarde até 3 dias úteis após o envio
- Verifique o status no portal do BB

---

**Última atualização:** 13/01/2026
