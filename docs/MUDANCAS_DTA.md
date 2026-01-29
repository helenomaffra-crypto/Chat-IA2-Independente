# 📋 MUDANÇAS NECESSÁRIAS PARA SUPORTE A DTA

**Data:** 11/12/2025

## ⚠️ PROBLEMA CRÍTICO

O arquivo `db_manager.py` foi sobrescrito incorretamente e precisa ser **restaurado do backup ou controle de versão**.

---

## ✅ MUDANÇAS JÁ APLICADAS

### 1. DTO ProcessoKanbanDTO (`services/models/processo_kanban_dto.py`)
- ✅ Adicionados campos: `numero_dta`, `documento_despacho`, `numero_documento_despacho`
- ✅ Extração automática de `documentoDespacho` e `numeroDocumentoDespacho` do JSON do Kanban
- ✅ Lógica para extrair `numero_dta` quando `documentoDespacho = "DTA"`

### 2. ProcessoKanbanService (`services/processo_kanban_service.py`)
- ✅ Atualizado `_salvar_processo` para incluir `numero_dta`, `documento_despacho`, `numero_documento_despacho` no INSERT

### 3. Dashboard (`services/agents/processo_agent.py`)
- ✅ Adicionada importação de `listar_processos_em_dta`
- ✅ Adicionado parâmetro `processos_em_dta` em `_formatar_dashboard_hoje`
- ✅ Adicionada seção "PROCESSOS EM DTA" no dashboard

---

## 🔧 MUDANÇAS QUE PRECISAM SER APLICADAS NO `db_manager.py`

### 1. Adicionar colunas na tabela `processos_kanban`

**Localização:** Função `init_db()`, após as outras migrações de colunas

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

**Justificativa:** Processos com DTA já estão em trânsito para outro recinto e não devem aparecer como "prontos para registro".

### 3. Adicionar função `listar_processos_em_dta`

**Localização:** Após a função `listar_processos_liberados_registro()`

```python
def listar_processos_em_dta(categoria: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Lista processos que estão em DTA (Declaração de Trânsito Aduaneiro).
    
    DTA significa que a carga já chegou e está sendo removida para outro recinto
    alfandegado, onde será registrada uma DI ou DUIMP posteriormente.
    
    Args:
        categoria: Categoria do processo (opcional, ex: "MV5", "ALH")
        limit: Limite máximo de processos a retornar
    
    Returns:
        Lista de dicts com dados dos processos em DTA
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        
        query = '''
            SELECT pk.processo_referencia, pk.dados_completos_json,
                   pk.numero_ce, pk.situacao_ce, pk.etapa_kanban, pk.modal,
                   pk.numero_dta, pk.documento_despacho, pk.numero_documento_despacho,
                   pk.data_destino_final, pk.atualizado_em
            FROM processos_kanban pk
            WHERE pk.numero_dta IS NOT NULL 
            AND pk.numero_dta != ''
            AND pk.dados_completos_json IS NOT NULL
            AND pk.dados_completos_json != ''
        '''
        
        params = []
        
        # Filtro por categoria
        if categoria:
            query += ' AND pk.processo_referencia LIKE ?'
            params.append(f'{categoria.upper()}.%')
        
        query += ' ORDER BY pk.atualizado_em DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        processos = []
        for row in rows:
            try:
                import json
                dados_json = json.loads(row['dados_completos_json'])
                
                processo_info = {
                    'processo_referencia': row['processo_referencia'],
                    'numero_ce': row['numero_ce'],
                    'situacao_ce': row['situacao_ce'],
                    'etapa_kanban': row['etapa_kanban'],
                    'modal': row['modal'],
                    'numero_dta': row['numero_dta'],
                    'documento_despacho': row['documento_despacho'],
                    'numero_documento_despacho': row['numero_documento_despacho'],
                    'data_destino_final': row['data_destino_final'],
                    'atualizado_em': row['atualizado_em']
                }
                
                processos.append(processo_info)
            except Exception as e:
                logging.warning(f'Erro ao processar processo {row["processo_referencia"]}: {e}')
                continue
        
        return processos
    except Exception as e:
        logging.error(f'Erro ao listar processos em DTA: {e}')
        return []
```

---

## 📝 RESUMO DAS MUDANÇAS

1. ✅ **DTO atualizado** - Campos DTA adicionados e extração funcionando
2. ✅ **Service atualizado** - Salva DTA no banco
3. ✅ **Dashboard atualizado** - Mostra processos em DTA
4. ⚠️ **db_manager.py precisa ser restaurado** e ter as 3 mudanças acima aplicadas

---

## 🧪 TESTE

Após restaurar `db_manager.py` e aplicar as mudanças:

```python
from db_manager import listar_processos_em_dta

# Listar todos os processos em DTA
processos_dta = listar_processos_em_dta()
print(f"Processos em DTA: {len(processos_dta)}")

# Listar processos MV5 em DTA
processos_mv5_dta = listar_processos_em_dta(categoria="MV5")
print(f"Processos MV5 em DTA: {len(processos_mv5_dta)}")
```

---

## 📚 CONTEXTO

**DTA (Declaração de Trânsito Aduaneiro):**
- Documento opcional usado quando o cliente decide remover uma carga importada do porto do Rio para outro recinto alfandegado
- Fluxo: DTA → DI ou DUIMP (após chegar no outro recinto)
- Processos com DTA já chegaram e estão sendo removidos para registro em outro local
- Não devem aparecer como "prontos para registro" (já estão em trânsito)

