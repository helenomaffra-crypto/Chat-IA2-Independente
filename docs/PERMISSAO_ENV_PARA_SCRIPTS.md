# 🔓 Como Dar Permissão de Leitura ao .env para Scripts

**Data:** 13/01/2026  
**Problema:** Scripts não conseguem ler o `.env` porque está protegido

---

## 🎯 Solução Rápida

### Opção 1: Alterar Permissões do Arquivo (Recomendado)

```bash
# No terminal do Mac
cd /Users/helenomaffra/Chat-IA-Independente
chmod 644 .env
```

**O que faz:**
- `644` = Leitura e escrita para o dono, apenas leitura para grupo e outros
- Permite que scripts Python leiam o arquivo
- Mantém segurança (apenas leitura para outros)

**Verificar permissões:**
```bash
ls -la .env
# Deve mostrar: -rw-r--r-- (644)
```

### Opção 2: Exportar Variáveis Manualmente (Temporário)

Se não quiser alterar permissões, exporte as variáveis no terminal antes de rodar o script:

```bash
# No terminal do Mac
export SANTANDER_PAYMENTS_CLIENT_ID="seu_client_id"
export SANTANDER_PAYMENTS_CLIENT_SECRET="seu_client_secret"
export SANTANDER_WORKSPACE_ID="seu_workspace_id"
export SANTANDER_PAYMENTS_CERT_FILE="/path/to/cert.pem"
export SANTANDER_PAYMENTS_KEY_FILE="/path/to/key.pem"

# Depois rode o script
python3 scripts/teste_pagamento_boleto_sandbox.py --dados ...
```

### Opção 3: Usar python-dotenv (Mais Robusto)

Se `python-dotenv` estiver instalado, o script pode usar:

```bash
pip install python-dotenv
```

O script já tenta usar `python-dotenv` se disponível (via fallback nos serviços).

---

## 🔍 Verificar se Funcionou

Após alterar permissões, rode o script novamente:

```bash
python3 scripts/teste_pagamento_boleto_sandbox.py --dados 34191093216412992293280145580009313510000090000 900.00 2026-01-13
```

**Deve mostrar:**
```
✅ Variáveis de ambiente carregadas do .env: /Users/helenomaffra/Chat-IA-Independente/.env
🔍 Diagnóstico de Variáveis de Ambiente:
------------------------------------------------------------
   SANTANDER_PAYMENTS_CLIENT_ID: ✅ Configurado
   SANTANDER_PAYMENTS_CLIENT_SECRET: ✅ Configurado
   SANTANDER_WORKSPACE_ID: ✅ Configurado (1f625459-b4d1-4a1f-9e61-2ff5a75eb665)
   Certificado mTLS: ✅ Configurado
```

---

## ⚠️ Segurança

**Permissões 644 são seguras porque:**
- Apenas o dono (você) pode escrever
- Outros usuários só podem ler (não modificar)
- Scripts Python podem ler (necessário para funcionar)

**Se quiser mais segurança:**
- Use `600` (apenas dono pode ler/escrever)
- Mas scripts de outros usuários não funcionarão

---

## 🐛 Problema Específico: Data Futura

**Erro encontrado:**
```
"_message": "Data de pagamento não pode ser posterior a data de hoje"
```

**Solução:** ✅ **JÁ CORRIGIDO**
- Script agora usa data de hoje quando vencimento é futuro
- Sandbox não permite pagar boletos com data futura

---

**Última atualização:** 13/01/2026
