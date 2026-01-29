# Coerência "o que registramos" com o dashboard

**Data:** 27/01/2026  
**Problema:** "O que registramos ontem?" retornava "Nenhum processo registrado ontem" mesmo quando o dashboard "o que temos pra hoje" mostrava DIs com **Registro: 26/01/2026** (ontem).

---

## Causa

- **Dashboard** ("o que temos pra hoje" / DIs em análise): usa **dataHoraRegistro** / **data_registro** da DI/DUIMP (critério oficial de “quando foi registrado”).
- **"O que registramos ontem"** (antes): usava `listar_processos_registrados_hoje(dias_atras=1)` → `notificacoes_processos.criado_em` = data em que a **notificação** foi criada no sistema, não a data de registro da DI/DUIMP. Com isso, DIs registradas ontem mas “vistas” pelo sistema hoje não apareciam.

---

## Alterações

1. **"O que registramos ontem"**  
   No `chat_service`, quando a mensagem é tipo "o que registramos ontem" (ou similar), passa a forçar **`listar_processos_registrados_periodo`** com `periodo='ontem'`.  
   Fonte: `DOCUMENTO_ADUANEIRO.data_registro` (via `RegistrosPeriodoService`), alinhada ao dashboard.

2. **"O que registramos hoje"**  
   Também passou a usar **`listar_processos_registrados_periodo`** com `periodo='hoje'`, em vez de `listar_processos_registrados_hoje`, para manter a mesma regra de data que "ontem" e o dashboard.

3. **Tool**  
   Em `tool_definitions`, a descrição de `listar_processos_registrados_periodo` foi atualizada para incluir exemplos “o que registramos ontem?” e “o que registramos hoje?” e deixar claro que o critério é o mesmo do dashboard (Registro = `data_registro` da DI/DUIMP).

---

## Fluxo atual

- **"o que registramos ontem"** → detecção no chat_service → `listar_processos_registrados_periodo(periodo='ontem')` → `RegistrosPeriodoService` → `DOCUMENTO_ADUANEIRO.data_registro` no dia anterior.
- **"o que registramos hoje"** → detecção no chat_service → `listar_processos_registrados_periodo(periodo='hoje')` → mesma fonte, dia atual.

Assim, "o que registramos" fica coerente com a coluna **Registro** exibida no relatório "o que temos pra hoje".

---

## Arquivos alterados

- `services/chat_service.py`: detecção de "ontem" e "hoje" e chamada forçada a `listar_processos_registrados_periodo` com `periodo='ontem'` ou `periodo='hoje'`.
- `services/tool_definitions.py`: descrição de `listar_processos_registrados_periodo` atualizada.
