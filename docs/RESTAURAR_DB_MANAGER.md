# 🔧 GUIA DE RESTAURAÇÃO DO db_manager.py

**Data:** 11/12/2025

## ⚠️ PROBLEMA

O arquivo `db_manager.py` foi sobrescrito incorretamente e está corrompido (apenas 2.9KB quando deveria ter ~10.000+ linhas).

---

## 📋 OPÇÕES DE RESTAURAÇÃO

### Opção 1: Restaurar do Backup/Controle de Versão (RECOMENDADO)

Se você tem:
- **Git:** `git checkout HEAD -- db_manager.py` ou `git restore db_manager.py`
- **Backup manual:** Copiar arquivo do backup
- **Time Machine (macOS):** Restaurar do backup do sistema

### Opção 2: Recriar a partir do código existente

Se não tiver backup, o arquivo precisa ser recriado. O arquivo original tinha:
- ~10.000+ linhas
- Funções principais: `init_db()`, `get_db_connection()`, `listar_processos_liberados_registro()`, etc.
- Todas as funções de gerenciamento de banco de dados

---

## ✅ MUDANÇAS QUE PRECISAM SER APLICADAS APÓS RESTAURAÇÃO

### 1. Adicionar colunas DTA na tabela `processos_kanban`

**Localização:** Função `init_db()`, após outras migrações de colunas

```python
# ✅ NOVO: Adicionar coluna para DTA
try:
    cursor.execute('ALTER TABLE processos_kanban ADD COLUMN numero_dta TEXT')
except sqlite3.OperationalError:
    pass  # Coluna já existe
try:
    cursor.execute('ALTER TABLE processos_kanban ADD COLUMN documento_despacho TEXT')
except sqlite3.OperationalError:
    pass  # Coluna já existe
try:
    cursor.execute('ALTER TABLE processos_kanban ADD COLUMN numero_documento_despacho TEXT')
except sqlite3.OperationalError:
    pass  # Coluna já existe
```

### 2. Atualizar `listar_processos_liberados_registro`

**Localização:** Função `listar_processos_liberados_registro()`, na query SQL

**Mudança:** Adicionar condição para excluir processos com DTA:

```python
# ANTES:
WHERE (pk.numero_di IS NULL OR pk.numero_di = '' OR pk.numero_di = '/       -')
AND (pk.numero_duimp IS NULL OR pk.numero_duimp = '')

# DEPOIS:
WHERE (pk.numero_di IS NULL OR pk.numero_di = '' OR pk.numero_di = '/       -')
AND (pk.numero_duimp IS NULL OR pk.numero_duimp = '')
AND (pk.numero_dta IS NULL OR pk.numero_dta = '')  # ✅ NOVO: Excluir processos com DTA
```

### 3. Adicionar função `listar_processos_em_dta`

**Localização:** Após a função `listar_processos_liberados_registro()`

Ver código completo em `MUDANCAS_DTA.md` ou no arquivo `db_manager.py` atual (que tem a função, mas precisa ser integrada ao arquivo completo).

---

## 🔒 PROTEÇÕES IMPLEMENTADAS

### Backup Automático

- Backups automáticos criados em `backups/chat_ia_YYYYMMDD_HHMMSS.db`
- Mantém últimos 5 backups
- Verificação de integridade antes de fazer backup

### WAL Mode

- WAL mode habilitado automaticamente (mais seguro para concorrência)
- Reduz risco de corrupção em escritas simultâneas

### Verificação de Integridade

- Verificação automática na inicialização
- Restauração automática do backup se corrompido

---

## 🧪 TESTE APÓS RESTAURAÇÃO

```python
from db_manager import (
    init_db,
    listar_processos_liberados_registro,
    listar_processos_em_dta
)

# Inicializar
init_db()

# Testar listar processos em DTA
processos_dta = listar_processos_em_dta()
print(f"Processos em DTA: {len(processos_dta)}")

# Verificar que processos com DTA não aparecem em "prontos para registro"
processos_prontos = listar_processos_liberados_registro()
print(f"Processos prontos (sem DTA): {len(processos_prontos)}")
```

---

## 📞 PRÓXIMOS PASSOS

1. **Restaurar `db_manager.py`** do backup/controle de versão
2. **Aplicar as 3 mudanças** documentadas acima
3. **Testar** as funções
4. **Verificar dashboard:** "o que temos pra hoje" deve mostrar processos em DTA

---

**💡 Dica:** Se não tiver backup, me avise e posso ajudar a recriar as funções principais baseado no que vi no código.

