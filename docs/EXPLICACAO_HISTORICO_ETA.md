# 📊 Como Funciona o Histórico de ETA no SQLite

## 🔍 **Como o Sistema Guarda o Primeiro ETA e Atualiza o Último**

### **1. Tabela de Histórico (`processos_kanban_historico`)**

O sistema usa uma tabela especial para guardar **todas as mudanças** de campos importantes:

```sql
CREATE TABLE processos_kanban_historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    processo_referencia TEXT NOT NULL,
    campo_mudado TEXT NOT NULL,  -- 'eta_iso', 'situacao_ce', etc.
    valor_anterior TEXT,
    valor_novo TEXT,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### **2. Como Funciona na Prática**

#### **Quando um Processo é Salvo pela Primeira Vez:**
1. O processo vem do Kanban (API externa) com seu JSON completo
2. O JSON contém `shipgov2.eventos[]` com todos os eventos ARRV (chegadas)
3. O sistema salva o processo no SQLite com `dados_completos_json` (JSON completo)
4. **NÃO há histórico ainda** porque não existe versão anterior

#### **Quando o ETA Muda:**
1. O sistema sincroniza o processo novamente do Kanban
2. Compara a versão **anterior** (salva no SQLite) com a versão **nova** (do Kanban)
3. Se `eta_iso` mudou, salva no histórico:
   - `valor_anterior`: ETA da versão anterior
   - `valor_novo`: ETA da versão nova
   - `criado_em`: Data/hora da mudança

### **3. Como o Sistema Detecta "Primeiro ETA" vs "Último ETA"**

Para o relatório de **"ETA ALTERADO"**, o sistema usa uma estratégia diferente:

#### **Estratégia: Usar Eventos do POD (ARRV/DISC) do JSON**

O sistema **NÃO depende do histórico do SQLite** para detectar mudanças de ETA. Em vez disso:

1. **Busca no JSON** (`dados_completos_json`) o campo `shipgov2.eventos[]`
2. **Foca no porto de destino (POD)**: `shipgov2.destino_codigo`
3. **Prioriza evento de descarga no POD**:
   - **Último ETA real do destino**: `DISC` no POD (se existir) → senão `ARRV` no POD → senão `shipgov2.destino_data_chegada`
4. **Importante (escala/transbordo)**:
   - O processo pode ter **múltiplos navios** ao longo do caminho
   - Para o painel (“o que chega esta semana”), o correto é mostrar **o navio do trecho final do POD** (evento `DISC/ARRV` no POD), não o primeiro navio do histórico

```python
# Regra atual (POD-first):
# ETA(POD) = DISC no destino > ARRV no destino > destino_data_chegada
#
# Navio exibido = navio do evento DISC/ARRV no destino (quando existir)
# (evita bug em escala/transbordo: primeiro navio != navio do trecho final)
```

### 🛠️ Manutenção: rebuild do cache de ETA/Navio/Status (shipgov2)

Se campos denormalizados no SQLite ficarem inconsistentes (ex.: navio do primeiro trecho em vez do navio do POD),
use o script:

- Dry-run (não altera nada):
  - `python3 scripts/rebuild_shipgov2_cache.py`
- Aplicar mudanças:
  - `python3 scripts/rebuild_shipgov2_cache.py --apply`

✅ **Política conservadora:** o rebuild **não apaga** ETA/navio/status (não troca por `None`) e **não faz downgrade** de status.

## ⚠️ **O Que Acontece Quando Você Abre o ZIP em Outro Lugar?**

### **Cenário: Banco SQLite Criado do Zero**

1. **O banco SQLite será criado vazio** (sem dados históricos)
2. **Os processos serão sincronizados do Kanban** (API externa)
3. **O JSON completo será salvo** em `dados_completos_json`
4. **O histórico de ETA funcionará assim:**

#### ✅ **Vai Funcionar:**
- O relatório "ETA ALTERADO" **VAI FUNCIONAR** porque:
  - Usa os eventos ARRV dentro do JSON (`shipgov2.eventos[]`)
  - Compara primeiro vs último evento ARRV
  - **NÃO depende do histórico do SQLite**

#### ❌ **Não Vai Funcionar:**
- O histórico detalhado de mudanças (`processos_kanban_historico`) estará vazio
- Não haverá registro de quando cada mudança aconteceu
- O sistema só saberá sobre mudanças **a partir de agora**

### **Exemplo Prático:**

**Processo BND.0094/25:**
- **No banco atual:** Tem histórico completo de todas as mudanças de ETA
- **No banco novo (do ZIP):**
  - Primeira sincronização: Salva o processo com JSON completo
  - O JSON tem `shipgov2.eventos[]` com todos os eventos ARRV
  - O relatório "ETA ALTERADO" **VAI FUNCIONAR** porque compara eventos dentro do JSON
  - Mas o histórico detalhado (`processos_kanban_historico`) só terá mudanças futuras

## 📋 **Resumo**

| Aspecto | Como Funciona | Depende do SQLite? |
|---------|---------------|-------------------|
| **Relatório "ETA ALTERADO"** | Compara eventos ARRV do JSON | ❌ Não |
| **Histórico de Mudanças** | Tabela `processos_kanban_historico` | ✅ Sim |
| **Primeiro ETA** | Primeiro evento ARRV ou `destino_data_chegada` | ❌ Não (vem do JSON) |
| **Último ETA** | Último evento ARRV | ❌ Não (vem do JSON) |

## 🔑 **Conclusão**

O sistema é **inteligente**: mesmo que o banco SQLite seja criado do zero, o relatório de "ETA ALTERADO" **VAI FUNCIONAR** porque usa os eventos ARRV que estão salvos dentro do JSON do processo (`dados_completos_json`).

O histórico detalhado (`processos_kanban_historico`) é apenas um **complemento** para rastrear quando cada mudança aconteceu, mas **não é essencial** para detectar mudanças de ETA.


