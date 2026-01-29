# 📊 Fluxo de Geração e Filtragem de Relatórios JSON

## 🎯 Resposta Direta

**SIM!** O fluxo é exatamente isso:

1. **JSON COMPLETO é gerado PRIMEIRO** (com todas as seções)
2. **Seções são montadas quando solicitado** (filtros operam no JSON completo)

---

## 📋 Fluxo Detalhado

### 1. Geração Inicial: "o que temos pra hoje?"

```
Usuário: "o que temos pra hoje?"
  ↓
┌─────────────────────────────────────────────────────────┐
│ 1. Buscar TODAS as seções de uma vez:                  │
│    ├─ processos_chegando = obter_processos_chegando()  │
│    ├─ processos_prontos = obter_processos_prontos()    │
│    ├─ processos_em_dta = listar_processos_em_dta()     │
│    ├─ pendencias = obter_pendencias_ativas()           │
│    ├─ duimps_analise = obter_duimps_em_analise()       │
│    ├─ dis_analise = obter_dis_em_analise()             │
│    ├─ eta_alterado = obter_processos_eta_alterado()   │
│    └─ alertas = obter_alertas_recentes()              │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Criar JSON COMPLETO com TODAS as seções:            │
│                                                         │
│    dados_json = {                                       │
│      'tipo_relatorio': 'o_que_tem_hoje',               │
│      'secoes': {                                        │
│        'processos_chegando': [...],  ← TODAS as 8       │
│        'processos_prontos': [...],   ← seções são       │
│        'processos_em_dta': [...],    ← geradas           │
│        'pendencias': [...],         ← de uma vez       │
│        'duimps_analise': [...],     ←                  │
│        'dis_analise': [...],        ←                  │
│        'eta_alterado': [...],       ←                  │
│        'alertas': [...]             ←                  │
│      }                                                  │
│    }                                                    │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Gerar STRING formatada do JSON completo:            │
│    resposta = formatar_relatorio_fallback_simples(      │
│        dados_json  ← JSON completo com 8 seções         │
│    )                                                    │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Salvar JSON COMPLETO no contexto:                    │
│    salvar_ultimo_relatorio(session_id, {                 │
│        'dados_json': dados_json  ← JSON completo       │
│    })                                                    │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Retornar STRING ao usuário:                         │
│    return {                                             │
│        'resposta': resposta,      ← STRING formatada   │
│        'dados_json': dados_json   ← JSON completo      │
│    }                                                    │
└─────────────────────────────────────────────────────────┘
```

### 2. Filtragem: "filtre os PRONTOS PARA REGISTRO"

```
Usuário: "filtre os PRONTOS PARA REGISTRO"
  ↓
┌─────────────────────────────────────────────────────────┐
│ 1. Buscar JSON COMPLETO salvo:                        │
│    relatorio_salvo = buscar_ultimo_relatorio()          │
│    dados_json = relatorio_salvo.meta_json              │
│                        .get('dados_json')              │
│                        ← JSON COMPLETO (8 seções)      │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Filtrar seções no JSON completo:                   │
│                                                         │
│    secoes_originais = dados_json.get('secoes')          │
│    # secoes_originais = {                              │
│    #   'processos_chegando': [...],  ← 8 seções         │
│    #   'processos_prontos': [...],                      │
│    #   'processos_em_dta': [...],                       │
│    #   'pendencias': [...],                             │
│    #   'duimps_analise': [...],                         │
│    #   'dis_analise': [...],                            │
│    #   'eta_alterado': [...],                           │
│    #   'alertas': [...]                                 │
│    # }                                                  │
│                                                         │
│    secoes_filtradas = {                                │
│        'processos_prontos': secoes_originais            │
│                          ['processos_prontos']          │
│    }  ← Apenas 1 seção (filtrada)                     │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Criar NOVO JSON apenas com seção filtrada:         │
│                                                         │
│    dados_json_filtrado = dados_json.copy()             │
│    dados_json_filtrado['secoes'] = secoes_filtradas    │
│    dados_json_filtrado['filtrado'] = True              │
│    dados_json_filtrado['secoes_filtradas'] = [        │
│        'processos_prontos'                             │
│    ]                                                    │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Preservar JSON original completo:                   │
│                                                         │
│    meta_json_filtrado = {                               │
│        'dados_json': dados_json_filtrado,  ← Filtrado  │
│        'dados_json_original': dados_json    ← Original  │
│    }                                                    │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Gerar STRING formatada do JSON filtrado:            │
│    resposta_filtrada = formatar_relatorio_              │
│        fallback_simples(dados_json_filtrado)            │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Salvar JSON filtrado (com original preservado):     │
│    salvar_ultimo_relatorio(session_id, {                │
│        'dados_json': dados_json_filtrado,              │
│        'dados_json_original': dados_json  ← Preservado  │
│    })                                                    │
└─────────────────────────────────────────────────────────┘
```

### 3. Filtro por Categoria: "filtre so os mda"

```
Usuário: "filtre so os mda"
  ↓
┌─────────────────────────────────────────────────────────┐
│ 1. Buscar JSON salvo (pode ser já filtrado):          │
│    relatorio_salvo = buscar_ultimo_relatorio()         │
│                                                         │
│    # Se tem dados_json_original, usar ele (completo)   │
│    # Se não tem, usar dados_json (pode ser filtrado)   │
│    dados_json = relatorio_salvo.meta_json              │
│                        .get('dados_json_original')     │
│                        or relatorio_salvo.meta_json    │
│                        .get('dados_json')              │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Filtrar por categoria em TODAS as seções:           │
│                                                         │
│    secoes_para_filtrar = dados_json.get('secoes')      │
│    # Pode ter 1 seção (se já filtrado) ou 8 seções    │
│                                                         │
│    secoes_filtradas_por_categoria = {}                 │
│    for secao, itens in secoes_para_filtrar.items():    │
│        itens_mda = [                                   │
│            item for item in itens                       │
│            if item.get('categoria') == 'MDA'          │
│        ]                                                │
│        if itens_mda:                                   │
│            secoes_filtradas_por_categoria[secao] =     │
│                itens_mda                               │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Criar NOVO JSON com processos MDA:                  │
│    dados_json_filtrado = {                             │
│        'secoes': {                                      │
│            'processos_prontos': [                       │
│                # Apenas processos MDA                  │
│            ]                                            │
│        },                                               │
│        'categoria_filtro': 'MDA'                        │
│    }                                                    │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Vantagens Deste Fluxo

### 1. **Eficiência**
- Todas as seções são buscadas de uma vez (menos chamadas ao banco)
- Filtros operam em memória (rápido)
- Não precisa buscar dados novamente para filtrar

### 2. **Consistência**
- JSON completo é a fonte da verdade
- Filtros sempre usam os mesmos dados
- Não há risco de dados desatualizados entre filtros

### 3. **Flexibilidade**
- Pode filtrar por seção
- Pode filtrar por categoria
- Pode combinar filtros (seção + categoria)
- JSON original sempre preservado para novos filtros

---

## 🔍 Exemplo Prático

### Cenário 1: Relatório Completo

```
Usuário: "o que temos pra hoje?"
  ↓
Sistema gera JSON com 8 seções:
  - processos_chegando: 3 processos
  - processos_prontos: 11 processos
  - processos_em_dta: 0 processos
  - pendencias: 9 processos
  - duimps_analise: 3 DUIMPs
  - dis_analise: 6 DIs
  - eta_alterado: 17 processos
  - alertas: 10 alertas
  ↓
Salva JSON completo (8 seções)
Retorna STRING formatada com todas as seções
```

### Cenário 2: Filtrar por Seção

```
Usuário: "filtre os PRONTOS PARA REGISTRO"
  ↓
Sistema busca JSON completo salvo
Filtra apenas seção 'processos_prontos'
  ↓
Cria novo JSON com 1 seção:
  - processos_prontos: 11 processos
  ↓
Salva JSON filtrado (preservando original)
Retorna STRING formatada apenas com processos_prontos
```

### Cenário 3: Filtrar por Categoria

```
Usuário: "filtre so os mda"
  ↓
Sistema busca JSON salvo (completo ou filtrado)
Se tem dados_json_original, usa ele (8 seções)
Se não tem, usa dados_json (pode ter 1 seção)
  ↓
Filtra processos MDA em todas as seções disponíveis
  ↓
Cria novo JSON com processos MDA:
  - processos_prontos: 4 processos MDA
  ↓
Salva JSON filtrado (preservando original)
Retorna STRING formatada apenas com MDA
```

---

## 📝 Resumo

| Etapa | O que acontece | Resultado |
|-------|----------------|-----------|
| **1. Geração** | Busca TODAS as seções de uma vez | JSON completo (8 seções) |
| **2. Salvamento** | Salva JSON completo no contexto | Disponível para filtros |
| **3. Formatação** | Gera STRING do JSON completo | Resposta ao usuário |
| **4. Filtro** | Busca JSON completo, filtra seções | Novo JSON filtrado |
| **5. Preservação** | Salva JSON filtrado + original | Ambos disponíveis |

---

## 🎯 Conclusão

**SIM, o fluxo é exatamente isso:**

1. ✅ **JSON completo é gerado PRIMEIRO** (todas as seções de uma vez)
2. ✅ **Seções são montadas quando solicitado** (filtros operam no JSON completo)
3. ✅ **JSON original é preservado** (para novos filtros)
4. ✅ **Filtros são cumulativos** (pode filtrar seção + categoria)

---

**Última atualização:** 12/01/2026
