# 🔐 Certificados mTLS - Santander (Extratos e Pagamentos)

**Data:** 12/01/2026  
**Objetivo:** Explicar como configurar certificados mTLS para Santander Extratos e Pagamentos

---

## 🎯 Resumo: Certificados Podem Ser os Mesmos

✅ **SIM, você pode usar os MESMOS certificados** para Extratos e Pagamentos do Santander.

O código já está configurado para fazer **fallback automático**:
- Se `SANTANDER_PAYMENTS_CERT_FILE` não estiver configurado
- O sistema usa automaticamente `SANTANDER_CERT_FILE` (do extrato)

---

## 📋 Tipos de Certificados

### Certificado ICP-Brasil Tipo A1

O Santander exige certificado **ICP-Brasil tipo A1** para autenticação mTLS (mutual TLS).

**Características:**
- ✅ Certificado digital brasileiro (ICP-Brasil)
- ✅ Tipo A1 (arquivo, não token físico)
- ✅ Formato: `.pem`, `.crt`, `.cer` (certificado)
- ✅ Formato: `.key`, `.pem` (chave privada)

---

## 🔧 Configuração no `.env`

### Opção 1: Usar os Mesmos Certificados (Recomendado)

Se você já tem certificados configurados para **Extratos**, pode usar os mesmos para **Pagamentos**:

```env
# ==========================================
# SANTANDER - EXTRATOS (já configurado)
# ==========================================
SANTANDER_CERT_FILE=/path/to/cert.pem
SANTANDER_KEY_FILE=/path/to/key.key

# ==========================================
# SANTANDER - PAGAMENTOS (usa os mesmos)
# ==========================================
# Não precisa configurar - usa automaticamente SANTANDER_CERT_FILE e SANTANDER_KEY_FILE
SANTANDER_PAYMENTS_CLIENT_ID=4zhVGn73MqPUSSvKhARMurKm13Dqt4BX
SANTANDER_PAYMENTS_CLIENT_SECRET=a05tNBQ6m1zU1qo5
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
```

**Como funciona:**
- O código tenta primeiro `SANTANDER_PAYMENTS_CERT_FILE`
- Se não encontrar, usa `SANTANDER_CERT_FILE` como fallback
- Mesma lógica para `SANTANDER_PAYMENTS_KEY_FILE` → `SANTANDER_KEY_FILE`

### Opção 2: Certificados Separados (Opcional)

Se quiser usar certificados diferentes para Pagamentos:

```env
# ==========================================
# SANTANDER - EXTRATOS
# ==========================================
SANTANDER_CERT_FILE=/path/to/cert_extratos.pem
SANTANDER_KEY_FILE=/path/to/key_extratos.key

# ==========================================
# SANTANDER - PAGAMENTOS (certificados separados)
# ==========================================
SANTANDER_PAYMENTS_CERT_FILE=/path/to/cert_pagamentos.pem
SANTANDER_PAYMENTS_KEY_FILE=/path/to/key_pagamentos.key
SANTANDER_PAYMENTS_CLIENT_ID=4zhVGn73MqPUSSvKhARMurKm13Dqt4BX
SANTANDER_PAYMENTS_CLIENT_SECRET=a05tNBQ6m1zU1qo5
```

**Quando usar certificados separados:**
- ⚠️ Aplicações diferentes no Portal do Desenvolvedor
- ⚠️ Certificados diferentes registrados em cada aplicação
- ⚠️ Necessidade de isolamento completo

---

## 🔍 Como o Código Funciona

### Fallback Automático

O código em `utils/santander_payments_api.py` implementa fallback:

```python
# Certificados (pode usar os mesmos ou diferentes)
if self.cert_file is None:
    # Tentar certificados específicos de pagamentos primeiro, depois fallback para genérico
    self.cert_file = os.getenv("SANTANDER_PAYMENTS_CERT_FILE") or os.getenv("SANTANDER_CERT_FILE")
if self.key_file is None:
    self.key_file = os.getenv("SANTANDER_PAYMENTS_KEY_FILE") or os.getenv("SANTANDER_KEY_FILE")
if self.cert_path is None:
    self.cert_path = os.getenv("SANTANDER_PAYMENTS_CERT_PATH") or os.getenv("SANTANDER_CERT_PATH")
```

**Ordem de prioridade:**
1. `SANTANDER_PAYMENTS_CERT_FILE` (específico para pagamentos)
2. `SANTANDER_CERT_FILE` (fallback - extrato)
3. `SANTANDER_PAYMENTS_CERT_PATH` (combinado - pagamentos)
4. `SANTANDER_CERT_PATH` (combinado - extrato)

---

## 📝 Formatos Suportados

### Certificado e Chave Separados

```env
SANTANDER_CERT_FILE=/path/to/cert.pem
SANTANDER_KEY_FILE=/path/to/key.key
```

**Formatos aceitos:**
- Certificado: `.pem`, `.crt`, `.cer`
- Chave: `.key`, `.pem`

### Certificado Combinado (Cert + Key)

```env
SANTANDER_CERT_PATH=/path/to/cert_combinado.pem
```

**Formato:**
- Arquivo único contendo certificado + chave privada
- Formato PEM (texto)

---

## 🔐 Onde Obter Certificados

### Portal do Desenvolvedor Santander

1. Acesse: https://developer.santander.com.br/
2. Crie uma aplicação (Extratos ou Pagamentos)
3. Faça upload do certificado (parte pública)
4. O certificado deve ser **ICP-Brasil tipo A1**

### Extrair Certificado do Navegador

Se você tem o certificado instalado no navegador:

**Chrome/Edge:**
1. Configurações → Privacidade e segurança → Gerenciar certificados
2. Exportar certificado (formato `.pem` ou `.p12`)
3. Extrair chave privada (se necessário)

**Firefox:**
1. Preferências → Privacidade e Segurança → Certificados → Ver Certificados
2. Exportar certificado

### Gerar Certificado A1

Se você precisa gerar um novo certificado A1:

1. **AC Certificadora** (ex: Serasa, Certisign, etc.)
2. **Tipo:** A1 (arquivo)
3. **Formato:** `.pem` ou `.p12`
4. **Validade:** Geralmente 1 ano

---

## ✅ Verificação

### Verificar se Certificados Estão Configurados

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Verificar certificados de Extratos
cert_extrato = os.getenv("SANTANDER_CERT_FILE")
key_extrato = os.getenv("SANTANDER_KEY_FILE")

# Verificar certificados de Pagamentos
cert_pagamentos = os.getenv("SANTANDER_PAYMENTS_CERT_FILE")
key_pagamentos = os.getenv("SANTANDER_PAYMENTS_KEY_FILE")

print(f"Certificado Extrato: {cert_extrato}")
print(f"Chave Extrato: {key_extrato}")
print(f"Certificado Pagamentos: {cert_pagamentos}")
print(f"Chave Pagamentos: {key_pagamentos}")

# Verificar se arquivos existem
if cert_extrato and os.path.exists(cert_extrato):
    print("✅ Certificado Extrato encontrado")
else:
    print("❌ Certificado Extrato não encontrado")

if cert_pagamentos and os.path.exists(cert_pagamentos):
    print("✅ Certificado Pagamentos encontrado")
elif cert_extrato and os.path.exists(cert_extrato):
    print("✅ Certificado Pagamentos usará fallback (Extrato)")
else:
    print("❌ Certificado Pagamentos não encontrado")
```

### Testar Conexão

Após configurar, teste no chat:

```
👤 "listar contas do santander"
👤 "listar workspaces do santander"
```

Se os certificados estiverem corretos:
- ✅ Conexão bem-sucedida
- ✅ Resposta da API

Se houver erro:
- ❌ Verifique caminho dos certificados
- ❌ Verifique formato (deve ser PEM)
- ❌ Verifique permissões do arquivo

---

## ⚠️ Problemas Comuns

### Erro: "Certificado não encontrado"

**Causa:** Caminho do certificado está incorreto ou arquivo não existe.

**Solução:**
```bash
# Verificar se arquivo existe
ls -la /path/to/cert.pem

# Verificar permissões
chmod 600 /path/to/cert.pem
chmod 600 /path/to/key.key
```

### Erro: "SSL/TLS handshake failed"

**Causa:** Certificado inválido ou formato incorreto.

**Solução:**
- Verificar se certificado é ICP-Brasil tipo A1
- Verificar se formato é PEM (texto)
- Verificar se certificado não expirou

### Erro: "Access Denied"

**Causa:** Certificado não está registrado no Portal do Desenvolvedor.

**Solução:**
1. Acesse Portal do Desenvolvedor
2. Verifique se certificado foi feito upload
3. Verifique se aplicação está ativa

---

## 🔒 Segurança

### Boas Práticas

1. **Permissões Restritas:**
   ```bash
   chmod 600 /path/to/cert.pem
   chmod 600 /path/to/key.key
   ```

2. **Não Commitar no Git:**
   - Certificados devem estar no `.gitignore`
   - Usar apenas variáveis de ambiente

3. **Backup Seguro:**
   - Fazer backup dos certificados
   - Armazenar em local seguro
   - Não compartilhar por email/chat

4. **Renovação:**
   - Certificados A1 geralmente expiram em 1 ano
   - Renovar antes do vencimento
   - Atualizar no Portal do Desenvolvedor

---

## 📚 Referências

### Documentação Relacionada

- `docs/integracoes/INTEGRACAO_SANTANDER.md` - Integração de Extratos
- `docs/EXPLICACAO_WORKSPACE_E_AUTENTICACAO.md` - Autenticação e Workspace
- `docs/CONFIGURAR_SANDBOX_SANTANDER.md` - Configuração do Sandbox
- `docs/TESTES_SEGUROS_TED_SANTANDER.md` - Testes Seguros

### Código

- `utils/santander_api.py` - Cliente API Extratos (linhas 74-81)
- `utils/santander_payments_api.py` - Cliente API Pagamentos (linhas 74-81)

---

## 🎯 Resumo

### ✅ Pode Usar os Mesmos Certificados

**Configuração mínima:**
```env
# Certificados (usados por Extratos e Pagamentos)
SANTANDER_CERT_FILE=/path/to/cert.pem
SANTANDER_KEY_FILE=/path/to/key.key

# Pagamentos (usa certificados acima automaticamente)
SANTANDER_PAYMENTS_CLIENT_ID=...
SANTANDER_PAYMENTS_CLIENT_SECRET=...
SANTANDER_PAYMENTS_BASE_URL=https://trust-sandbox.api.santander.com.br
```

### 🔄 Fallback Automático

O código faz fallback automaticamente:
- `SANTANDER_PAYMENTS_CERT_FILE` → `SANTANDER_CERT_FILE`
- `SANTANDER_PAYMENTS_KEY_FILE` → `SANTANDER_KEY_FILE`

### ⚠️ Quando Usar Certificados Separados

Apenas se:
- Aplicações diferentes no Portal
- Certificados diferentes registrados
- Necessidade de isolamento

---

**Última atualização:** 12/01/2026
