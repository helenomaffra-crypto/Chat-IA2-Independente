# 🔧 Correção de Duplicatas Incorretas - Lançamentos Bancários

**Data:** 23/01/2026  
**Problema:** Dois lançamentos com mesmo valor, mesma data e mesma descrição foram marcados incorretamente como duplicados

---

## 📋 Problema Identificado

### Situação

Dois lançamentos bancários com:
- Mesmo valor (ex: -R$ 13.337,88)
- Mesma data
- Mesmo banco
- Mesma descrição (ou descrição vazia/nula)

foram tratados como duplicados e apenas um foi salvo, quando na verdade eram lançamentos diferentes.

### Causa Raiz

O hash SHA-256 usado para detectar duplicatas **não incluía** o identificador único do lançamento:
- **Banco do Brasil:** `numeroDocumento` (ou `numeroLote`)
- **Santander:** `transactionId`

Isso fazia com que lançamentos diferentes com mesmo valor/data/descrição gerassem o mesmo hash.

---

## ✅ Solução Implementada

### 1. Correção do Hash (23/01/2026)

**Arquivo:** `services/banco_sincronizacao_service.py`

**Mudança:** Método `gerar_hash_lancamento()` agora inclui:
- **Banco do Brasil:** `numeroDocumento` (ou `numeroLote` como fallback)
- **Santander:** `transactionId`

**Resultado:** Lançamentos diferentes agora geram hashes diferentes, mesmo com mesmo valor/data/descrição.

### 2. Script de Correção

**Arquivo:** `scripts/corrigir_duplicatas_incorretas_banco.py`

Script para identificar e corrigir duplicatas incorretas já salvas no banco.

---

## 🚀 Como Usar o Script

### 1. Análise (Dry-Run)

Primeiro, analise quais grupos suspeitos existem:

```bash
# Apenas análise (não faz alterações)
python3 scripts/corrigir_duplicatas_incorretas_banco.py --analise

# Ou com dry-run explícito
python3 scripts/corrigir_duplicatas_incorretas_banco.py --dry-run
```

**O que faz:**
- Identifica grupos de lançamentos suspeitos (mesmo valor, data, banco, descrição)
- Mostra detalhes de cada grupo
- Exibe identificadores únicos (numeroDocumento/transactionId) quando disponíveis
- **Não faz alterações no banco**

### 2. Correção Real

Após analisar, se quiser corrigir:

```bash
# Aplicar correções (requer confirmação)
python3 scripts/corrigir_duplicatas_incorretas_banco.py --corrigir
```

**⚠️ IMPORTANTE:** O script pedirá confirmação digitando `SIM` antes de aplicar qualquer alteração.

**O que faz:**
- Analisa cada grupo suspeito
- Verifica se são realmente lançamentos diferentes (baseado em identificadores únicos)
- Se forem diferentes: mantém todos
- Se forem duplicatas reais: mantém apenas o mais antigo (deleta os outros)

### 3. Database Específico

Por padrão, o script usa `mAIke_assistente`. Para usar outro database:

```bash
python3 scripts/corrigir_duplicatas_incorretas_banco.py --analise --database Make
```

---

## 📊 Critérios de Identificação

O script identifica grupos suspeitos baseado em:

1. **Mesmo banco** (BB ou SANTANDER)
2. **Mesma agência**
3. **Mesma conta**
4. **Mesma data** (apenas data, ignorando hora)
5. **Mesmo valor absoluto**
6. **Mesmo sinal** (C ou D)
7. **Descrição similar** (primeiros 50 caracteres)
8. **Hash diferente** OU múltiplos IDs com mesmo hash

---

## 🔍 Estratégia de Correção

### Caso 1: Lançamentos Diferentes (Manter Todos)

Se todos os lançamentos do grupo têm:
- **Identificadores únicos diferentes** (numeroDocumento/transactionId)
- **Hashes diferentes**

→ São lançamentos distintos → **Manter todos**

### Caso 2: Duplicatas Reais (Manter Apenas o Mais Antigo)

Se os lançamentos têm:
- **Mesmo identificador único** (ou não têm identificador)
- **Mesmo hash**

→ São duplicatas reais → **Manter apenas o mais antigo** (deletar os outros)

---

## ⚠️ Observações Importantes

1. **Backup:** Sempre faça backup antes de corrigir:
   ```bash
   # Usar script de backup existente
   ./scripts/fazer_backup.sh
   ```

2. **Teste Primeiro:** Sempre execute `--analise` ou `--dry-run` antes de `--corrigir`

3. **Hash Antigo vs Novo:**
   - Lançamentos já sincronizados com hash antigo continuam válidos
   - Novos lançamentos usarão o novo hash (com identificador único)
   - Isso não afeta lançamentos já salvos

4. **Re-sincronização:**
   - Se identificar duplicatas incorretas, pode ser necessário re-sincronizar o período afetado
   - O novo hash garantirá que não sejam marcados como duplicados novamente

---

## 📝 Exemplo de Saída

```
================================================================================
🔍 ANÁLISE: 2 grupo(s) suspeito(s) encontrado(s)
================================================================================

================================================================================
📦 GRUPO 1: 2 lançamento(s) suspeito(s)
================================================================================
   Banco: BB
   Agência: 1251
   Conta: 50483
   Data: 23/01/2026
   Valor: R$ 13.337,88 (D)
   Descrição: PIX ENVIADO - FORNECEDOR XYZ...
   Hashes diferentes: 2

   1. ID: 12345
      Hash: a7f3c9d2e8b1f4c6...
      Criado em: 23/01/2026
      Fonte: BB_API
      Número Documento: 607984000004010

   2. ID: 12346
      Hash: b8e4d0e3f9c2g5d7...
      Criado em: 23/01/2026
      Fonte: BB_API
      Número Documento: 607984000004011
```

---

## 🔗 Arquivos Relacionados

- `services/banco_sincronizacao_service.py` - Serviço de sincronização (hash corrigido)
- `scripts/corrigir_duplicatas_incorretas_banco.py` - Script de correção
- `docs/INTEGRACAO_EXTRATOS_BANCARIOS.md` - Documentação da integração

---

**Última atualização:** 23/01/2026
