# 📋 Seções por Tipo de Relatório

Cada tipo de relatório tem suas próprias seções específicas no JSON. Este documento lista todas as seções disponíveis para cada tipo.

---

## 1. `o_que_tem_hoje` (O que temos pra hoje?)

**Seções disponíveis:**

```json
{
  "secoes": {
    "processos_chegando": [...],      // Processos que chegam HOJE
    "processos_prontos": [...],       // Processos prontos para registro (chegaram sem DI/DUIMP)
    "processos_em_dta": [...],        // Processos em DTA (Declaração de Trânsito Aduaneiro)
    "pendencias": [...],              // Pendências ativas
    "duimps_analise": [...],          // DUIMPs em análise
    "dis_analise": [...],             // DIs em análise
    "eta_alterado": [...],            // Processos com ETA alterado
    "alertas": [...]                  // Alertas recentes
  }
}
```

**Filtros disponíveis:**
- `"filtre os PRONTOS PARA REGISTRO"` → filtra `processos_prontos`
- `"filtre os que estão CHEGANDO HOJE"` → filtra `processos_chegando`
- `"filtre as PENDÊNCIAS"` → filtra `pendencias`
- `"filtre os DUIMPs EM ANÁLISE"` → filtra `duimps_analise`
- `"filtre as DIs EM ANÁLISE"` → filtra `dis_analise`
- `"filtre os ETA ALTERADO"` → filtra `eta_alterado`
- `"filtre so os mda"` → filtra por categoria em qualquer seção

---

## 2. `fechamento_dia` (Fechamento do dia)

**Seções disponíveis:**

```json
{
  "secoes": {
    "processos_chegaram": [...],           // Processos que chegaram hoje
    "processos_desembaracados": [...],     // Processos desembaraçados hoje
    "duimps_criadas": [...],               // DUIMPs criadas hoje
    "dis_registradas": [...]               // DIs registradas hoje
  }
}
```

**Filtros disponíveis:**
- `"filtre os que CHEGARAM"` → filtra `processos_chegaram`
- `"filtre os DESEMBARAÇADOS"` → filtra `processos_desembaracados`
- `"filtre as DUIMPs CRIADAS"` → filtra `duimps_criadas`
- `"filtre as DIs REGISTRADAS"` → filtra `dis_registradas`
- `"filtre so os mda"` → filtra por categoria em qualquer seção

---

## 3. `relatorio_averbacoes` (Relatório de Averbações)

**Seções disponíveis:**

```json
{
  "secoes": {
    "processos_com_di": [...],        // Processos com DI no período
    "processos_sem_di": [...],       // Processos sem DI no período
    "resumo_por_categoria": {...},   // Resumo agrupado por categoria
    "resumo_por_mes": {...}          // Resumo agrupado por mês
  }
}
```

**Filtros disponíveis:**
- `"filtre os COM DI"` → filtra `processos_com_di`
- `"filtre os SEM DI"` → filtra `processos_sem_di`
- `"filtre so os mda"` → filtra por categoria em qualquer seção

---

## 📊 Estrutura de Cada Item nas Seções

### Processos (processos_chegando, processos_prontos, etc.)

```json
{
  "processo_referencia": "MDA.0092/25",
  "categoria": "MDA",
  "modal": "Marítimo",
  "data_destino_final": "2026-01-11T00:00:00",
  "numero_ce": "172505415558828",
  "situacao_ce": "ARMAZENADA",
  "tipo_documento": "DUIMP",
  "motivo_prontidao": "Chegou em 2026-01-11T00:00:00, sem DUIMP",
  "tem_lpco": false,
  "lpco_deferido": false,
  "numero_lpco": null,
  "situacao_lpco": null,
  "dias_atraso": 1
}
```

### Pendências (pendencias)

```json
{
  "processo_referencia": "DMD.0089/25",
  "tipo_pendencia": "Frete",
  "descricao": "Pendente de pagamento",
  "data_pendencia": "2026-01-12",
  "acao": "Verificar pagamento"
}
```

### DUIMPs (duimps_analise)

```json
{
  "numero": "26BR00000003906",
  "versao": "0",
  "processo_referencia": "DMD.0083/25",
  "situacao": "Rascunho",
  "canal": null,
  "dias_em_analise": 4
}
```

### DIs (dis_analise)

```json
{
  "numero": "2528357639",
  "processo_referencia": "ARG.0020/25",
  "canal": "Verde",
  "situacao": "Di Desembaracada"
}
```

---

## 🔍 Como Funciona o Filtro

### Filtro por Seção

Quando você pede `"filtre os PRONTOS PARA REGISTRO"`:

1. Sistema busca o JSON salvo do último relatório
2. Identifica a seção `processos_prontos`
3. Cria novo JSON apenas com essa seção
4. Gera STRING formatada apenas dessa seção
5. Salva novo JSON filtrado no contexto

### Filtro por Categoria

Quando você pede `"filtre so os mda"`:

1. Sistema busca o JSON salvo (pode ser já filtrado)
2. Identifica a categoria `MDA`
3. Filtra processos com `categoria: "MDA"` em todas as seções disponíveis
4. Cria novo JSON apenas com processos MDA
5. Gera STRING formatada
6. Salva novo JSON filtrado no contexto

### Filtro Combinado

Exemplo: `"filtre os PRONTOS PARA REGISTRO"` → depois `"filtre so os mda"`

1. Primeiro filtro: deixa apenas `processos_prontos` (11 processos)
2. Segundo filtro: filtra por `MDA` dentro de `processos_prontos` (4 processos)
3. Resultado final: apenas processos MDA que estão prontos para registro

---

## 📝 Notas Importantes

1. **Cada relatório tem suas próprias seções**: Não tente filtrar `processos_prontos` em um relatório de `fechamento_dia` (ele não tem essa seção).

2. **Filtros são cumulativos**: Se você filtrar por seção e depois por categoria, o sistema mantém ambos os filtros.

3. **JSON é a fonte da verdade**: Todos os filtros operam no JSON salvo, não na STRING formatada.

4. **Seções podem estar vazias**: Se uma seção não tiver itens, ela pode não aparecer no JSON ou aparecer como array vazio `[]`.

---

**Última atualização:** 12/01/2026
