# 🔧 Corrigir Formatação do .env

**Data:** 13/01/2026  
**Problema:** Linhas com espaços no início não são lidas corretamente

---

## 🐛 Problema Identificado

No seu `.env`, as últimas linhas têm **espaços no início**:

```env
   SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
   SANTANDER_PFX_PASSWORD=senha001
   SANTANDER_WORKSPACE_ID=1f625459-b4d1-4a1f-9e61-2ff5a75eb665
```

**Isso pode causar problemas** porque alguns parsers ignoram linhas com espaços no início.

---

## ✅ Solução

### Opção 1: Remover Espaços Manualmente (Recomendado)

Edite o `.env` e remova os espaços no início dessas linhas:

```env
# ANTES (com espaços):
   SANTANDER_PAYMENTS_CERT_PATH=...
   SANTANDER_PFX_PASSWORD=...
   SANTANDER_WORKSPACE_ID=...

# DEPOIS (sem espaços):
SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_PFX_PASSWORD=senha001
SANTANDER_WORKSPACE_ID=1f625459-b4d1-4a1f-9e61-2ff5a75eb665
```

### Opção 2: Usar Comando sed (Automático)

```bash
# No terminal do Mac
cd /Users/helenomaffra/Chat-IA-Independente

# Remover espaços no início das linhas que começam com espaços + SANTANDER
sed -i '' 's/^[[:space:]]*SANTANDER/SANTANDER/g' .env

# Verificar resultado
grep "^[[:space:]]*SANTANDER" .env
# Não deve retornar nada (todas as linhas devem começar sem espaços)
```

---

## 🔍 Verificar se Funcionou

Após corrigir, rode o script novamente:

```bash
python3 scripts/teste_pagamento_boleto_sandbox.py --dados 34191093216412992293280145580009313510000090000 900.00 2026-01-13
```

**Deve mostrar:**
```
✅ Variáveis de ambiente carregadas do .env: /Users/helenomaffra/Chat-IA-Independente/.env
   ✅ Carregado: SANTANDER_PAYMENTS_CLIENT_ID=4zhVGn73MqP...
   ✅ Carregado: SANTANDER_PAYMENTS_CLIENT_SECRET=a05tNBQ6m1z...
   ✅ Carregado: SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/...
   ✅ Carregado: SANTANDER_WORKSPACE_ID=1f625459-b4d1-4a1f-9e61-2ff5a75eb665
🔍 Diagnóstico de Variáveis de Ambiente:
------------------------------------------------------------
   SANTANDER_PAYMENTS_CLIENT_ID: ✅ Configurado
   SANTANDER_PAYMENTS_CLIENT_SECRET: ✅ Configurado
   SANTANDER_WORKSPACE_ID: ✅ Configurado (1f625459-b4d1-4a1f-9e61-2ff5a75eb665)
   Certificado mTLS: ✅ Configurado
```

---

## 📝 Formato Correto do .env

**Regras:**
- ✅ Linhas devem começar **sem espaços** (exceto comentários com `#`)
- ✅ Formato: `CHAVE=valor` (sem espaços ao redor do `=`)
- ✅ Valores com espaços podem ter aspas: `CHAVE="valor com espaços"`
- ✅ Comentários começam com `#`

**Exemplo correto:**
```env
# Comentário (pode ter espaços antes do #)
SANTANDER_PAYMENTS_CLIENT_ID=4zhVGn73MqPUSSvKhARMurKm13Dqt4BX
SANTANDER_PAYMENTS_CLIENT_SECRET=a05tNBQ6m1zU1qo5
SANTANDER_PAYMENTS_CERT_PATH=/Users/helenomaffra/Chat-IA-Independente/.secure/eCNPJ MASSY MATRIZ 0001-27 - (valid 16-07-26) - senha001.pfx
SANTANDER_WORKSPACE_ID=1f625459-b4d1-4a1f-9e61-2ff5a75eb665
```

---

## ⚠️ Sobre Permissões do .env

**Se o `.env` estiver protegido:**

```bash
# Dar permissão de leitura
chmod 644 .env

# Verificar permissões
ls -la .env
# Deve mostrar: -rw-r--r-- (644)
```

**Permissões 644 são seguras:**
- Dono pode ler/escrever
- Outros podem apenas ler (scripts Python precisam ler)

---

**Última atualização:** 13/01/2026
