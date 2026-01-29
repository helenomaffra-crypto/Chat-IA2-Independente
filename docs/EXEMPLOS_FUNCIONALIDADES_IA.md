# 📚 Exemplos de Funcionalidades de IA

**Data:** 19/12/2025  
**Última atualização:** 19/12/2025

Este documento contém exemplos práticos de uso das funcionalidades de IA integradas no sistema.

---

## 1. 📖 Aprendizado de Regras (`learned_rules_service`)

### O que é?
O sistema pode aprender regras e definições do usuário e aplicá-las automaticamente em consultas futuras.

### Exemplos de Uso

#### Exemplo 1: Definir campo como confirmação de chegada
**Usuário:**
```
"O campo data_destino_final deve ser usado como confirmação de que o processo chegou ao destino final"
```

**O que acontece:**
- A IA detecta que é uma definição/regra
- Salva a regra usando `salvar_regra_aprendida`
- Em consultas futuras sobre "processos que chegaram", a IA automaticamente usa `WHERE data_destino_final IS NOT NULL`

**Resultado:**
- Regra salva: `destfinal como confirmação de chegada`
- Contexto: `chegada_processos`
- SQL aplicado: `WHERE data_destino_final IS NOT NULL`

---

#### Exemplo 2: Definir regra de negócio
**Usuário:**
```
"Processos com pendência de ICMS devem ser considerados bloqueados para registro de DI"
```

**O que acontece:**
- Regra salva com tipo `regra_negocio`
- Contexto: `registro_di`
- Em consultas sobre processos "prontos para registro", a IA automaticamente exclui processos com pendência de ICMS

---

#### Exemplo 3: Preferência de usuário
**Usuário:**
```
"Quando eu perguntar sobre 'processos chegando', sempre inclua também os que estão em trânsito (status 'em_transito')"
```

**O que acontece:**
- Regra salva com tipo `preferencia_usuario`
- Contexto: `listagem_processos`
- Sempre que você perguntar "quais processos estão chegando", a IA incluirá processos em trânsito

---

### Como a IA usa as regras

As regras aprendidas são automaticamente incluídas no `system_prompt` da IA em formato compacto:

```
📚 **REGRAS APRENDIDAS:**
- **destfinal como confirmação de chegada**: O campo data_destino_final deve ser usado como confirmação de que o processo chegou ao destino final (SQL: WHERE data_destino_final IS NOT NULL)
- **ICMS bloqueia registro**: Processos com pendência de ICMS devem ser considerados bloqueados para registro de DI
💡 Aplique essas regras quando fizer sentido.
```

---

## 2. 📌 Contexto Persistente de Sessão (`context_service`)

### O que é?
O sistema mantém contexto entre mensagens, como processos mencionados, categorias em foco, etc. O contexto mais importante é o **`processo_atual`**, que permite fazer follow-ups sem repetir o número do processo.

### ⚠️ Regras Importantes

**NUNCA assume processo padrão fixo:**
- O sistema NUNCA assume um processo padrão (ex: "MV5.0009/25")
- `processo_atual` só é definido quando:
  - Você menciona um processo EXPLÍCITO na mensagem (ex: "ALH.0165/25")
  - OU o sistema salva explicitamente via contexto após uma consulta

**Perguntas de Painel NÃO usam processo_atual:**
- Perguntas de visão geral como "como estão os MV5?" ou "o que temos pra hoje?" são **perguntas de painel**
- Essas perguntas NUNCA usam `processo_atual` do contexto
- Elas sempre retornam listas/visões gerais, não informações de um processo específico

### Exemplos de Uso

#### Exemplo 1: Follow-up de Processo usando Contexto
**Mensagem 1:**
```
Usuário: "Como está o processo ALH.0165/25?"
IA: [Resposta completa sobre o processo]
```
**O que acontece:**
- Sistema salva `processo_atual = "ALH.0165/25"` no contexto da sessão

**Mensagem 2 (Follow-up):**
```
Usuário: "e a DI?"
IA: [Automaticamente entende que se refere ao ALH.0165/25 e consulta a DI desse processo]
```
**O que acontece:**
- Sistema detecta que é follow-up (mensagem curta, menciona documento, não menciona processo)
- Sistema verifica que NÃO é pergunta de painel
- Sistema usa `processo_atual = "ALH.0165/25"` do contexto
- Retorna informações da DI do processo ALH.0165/25

**Mensagem 3 (Outro follow-up):**
```
Usuário: "e a DUIMP?"
IA: [Retorna informações da DUIMP do mesmo processo]
```

**Mensagem 4 (Pergunta de Painel - NÃO usa contexto):**
```
Usuário: "como estão os MV5?"
IA: [Retorna lista de processos MV5 - NÃO usa processo_atual]
```
**O que acontece:**
- Sistema detecta que é pergunta de painel (visão geral de categoria)
- Sistema NÃO usa `processo_atual` (perguntas de painel nunca usam contexto)
- Retorna lista de processos MV5

#### Exemplo 2: Quando o Contexto é Salvo
**Cenário:**
```
Usuário: "situação do VDM.0003/25"
```
**O que acontece:**
- Sistema detecta processo explícito: `VDM.0003/25`
- Sistema verifica que NÃO é pergunta de painel
- Sistema consulta o processo
- Sistema salva `processo_atual = "VDM.0003/25"` no contexto

**Follow-ups que DEVEM usar contexto:**
- "e a DI?" ✅
- "e a DUIMP?" ✅
- "e o CE?" ✅
- "situação dele?" ✅
- "como está esse processo?" ✅

**Perguntas que NÃO devem usar contexto:**
- "situacao vdm.0005/25" ❌ (novo processo explícito)
- "como estão os mv5?" ❌ (pergunta de painel)
- "o que temos pra hoje?" ❌ (pergunta de painel)
- "qual a ncm?" ❌ (pergunta de NCM, não follow-up)

#### Exemplo 3: Diferença entre Painel e Processo Específico
**Pergunta de Painel (NÃO usa processo_atual):**
```
Usuário: "como estão os processos ALH?"
IA: [Retorna lista de processos ALH - visão geral]
```
- Sistema detecta: pergunta de painel
- Sistema NÃO usa `processo_atual`
- Retorna: lista formatada de processos ALH

**Pergunta de Processo Específico (usa processo_atual se disponível):**
```
Usuário: "como está o processo ALH.0165/25?"
IA: [Retorna informações detalhadas do processo específico]
```
- Sistema detecta: processo explícito
- Sistema salva `processo_atual = "ALH.0165/25"`
- Retorna: informações completas do processo

**Follow-up após processo específico:**
```
Usuário: "e a DI?"
IA: [Usa processo_atual para consultar DI do ALH.0165/25]
```
- Sistema detecta: follow-up (não menciona processo, não é painel)
- Sistema usa `processo_atual = "ALH.0165/25"`
- Retorna: informações da DI do processo

---

#### Exemplo 2: Foco em categoria
**Mensagem 1:**
```
Usuário: "Como estão os MV5?"
IA: [Lista processos MV5]
```

**Mensagem 2:**
```
Usuário: "Quais têm pendência?"
IA: [Automaticamente filtra apenas MV5 com pendências, não todos os processos]
```

**O que acontece:**
- Contexto salvo: `categoria_atual = MV5`
- Na segunda mensagem, o contexto é incluído: `📌 **CONTEXTO:** Categoria: MV5`
- A IA preserva o filtro de categoria

---

#### Exemplo 3: Última consulta
**Mensagem 1:**
```
Usuário: "Mostre processos desembaraçados por mês"
IA: [Executa consulta analítica]
```

**Mensagem 2:**
```
Usuário: "Agora agrupa por categoria também"
IA: [Modifica a consulta anterior para incluir categoria no GROUP BY]
```

**O que acontece:**
- Contexto salvo: `ultima_consulta = processos desembaraçados por mês`
- A IA usa esse contexto para entender "agora" e "também"

---

### Como o contexto é incluído

O contexto de sessão é automaticamente incluído no `user_prompt`:

```
📌 **CONTEXTO:** Processo: VDM.0004/25, Categoria: MV5
💡 Use esse contexto quando o usuário fizer perguntas relacionadas.
```

---

## 3. 🔍 Consultas Analíticas SQL (`analytical_query_service`)

### O que é?
O sistema permite executar consultas SQL analíticas de forma segura (somente leitura) para análises, rankings e relatórios.

### Exemplos de Uso

#### Exemplo 1: Análise simples
**Usuário:**
```
"Quantos processos temos por categoria?"
```

**O que a IA faz:**
1. Detecta que é uma pergunta analítica
2. Chama `executar_consulta_analitica` com SQL:
   ```sql
   SELECT categoria, COUNT(*) as total 
   FROM processos_kanban 
   GROUP BY categoria 
   ORDER BY total DESC
   LIMIT 100
   ```
3. Retorna resultados formatados como tabela

**Resposta:**
```
✅ Consulta executada com sucesso (5 linhas, fonte: sqlite)

| categoria | total |
|-----------|-------|
| ALH       | 45    |
| VDM       | 32    |
| MV5       | 18    |
| BND       | 12    |
| DMD       | 8     |
```

---

#### Exemplo 2: Ranking com agregação
**Usuário:**
```
"Quais navios têm mais processos e qual o atraso médio?"
```

**O que a IA faz:**
1. Chama `executar_consulta_analitica` com SQL:
   ```sql
   SELECT 
     navio, 
     COUNT(*) as qtd_processos,
     AVG(dias_atraso) as media_atraso
   FROM processos_kanban
   WHERE navio IS NOT NULL
   GROUP BY navio
   ORDER BY qtd_processos DESC
   LIMIT 100
   ```

**Resposta:**
```
✅ Consulta executada com sucesso (10 linhas, fonte: sqlite)

| navio          | qtd_processos | media_atraso |
|----------------|---------------|--------------|
| MSC GENEVA     | 15            | 3.2          |
| MAERSK HAMBURG | 12            | 2.8          |
| COSCO SHIPPING | 8             | 4.1          |
...
```

---

#### Exemplo 3: Análise temporal
**Usuário:**
```
"Mostre processos desembaraçados por mês e categoria"
```

**O que a IA faz:**
1. Chama `executar_consulta_analitica` com SQL:
   ```sql
   SELECT 
     strftime('%Y-%m', data_desembaraco) AS mes,
     categoria,
     COUNT(*) AS qtd_processos
   FROM processos
   WHERE data_desembaraco IS NOT NULL
   GROUP BY mes, categoria
   ORDER BY mes DESC, categoria
   LIMIT 100
   ```

**Resposta:**
```
✅ Consulta executada com sucesso (15 linhas, fonte: sqlite)

| mes     | categoria | qtd_processos |
|---------|-----------|---------------|
| 2025-12 | ALH       | 8             |
| 2025-12 | VDM       | 5             |
| 2025-11 | ALH       | 12            |
...
```

---

### Segurança

- ✅ Apenas consultas `SELECT` são permitidas
- ✅ Palavras-chave perigosas são bloqueadas (INSERT, UPDATE, DELETE, DROP, etc.)
- ✅ LIMIT automático (padrão: 100, máximo: 1000)
- ✅ Tenta SQL Server primeiro, fallback para SQLite

---

## 4. 💾 Consultas Salvas (`saved_queries_service`)

### O que é?
O sistema permite salvar consultas SQL como relatórios reutilizáveis que podem ser chamados depois por linguagem natural.

### Exemplos de Uso

#### Exemplo 1: Salvar consulta personalizada
**Usuário:**
```
"Salva essa consulta como 'Atrasos críticos por cliente'"
```

**O que a IA faz:**
1. Detecta que é um comando para salvar consulta
2. Extrai a consulta SQL do contexto (se houver)
3. Chama `salvar_consulta_personalizada` com:
   - `nome_exibicao`: "Atrasos críticos por cliente"
   - `slug`: "atrasos_criticos_cliente" (gerado automaticamente)
   - `sql`: SQL da consulta atual
   - `descricao`: Gerada automaticamente

**Resposta:**
```
✅ Consulta salva com sucesso: **Atrasos críticos por cliente** (ID: 5)
```

---

#### Exemplo 2: Buscar e executar consulta salva
**Usuário:**
```
"Roda aquele relatório de atrasos críticos por cliente"
```

**O que a IA faz:**
1. Chama `buscar_consulta_personalizada` com texto: "atrasos críticos por cliente"
2. Encontra a consulta salva
3. Executa a consulta usando `executar_consulta_analitica`
4. Retorna resultados formatados

**Resposta:**
```
✅ **Atrasos críticos por cliente** (8 linhas)

| cliente        | qtd_processos | media_atraso |
|----------------|---------------|--------------|
| Cliente A      | 5             | 12.5         |
| Cliente B      | 3             | 8.2          |
...
```

---

#### Exemplo 3: Consultas padrão automáticas

O sistema já vem com algumas consultas padrão pré-cadastradas:

**Usuário:**
```
"Processos desembaraçados por mês e categoria"
```

**O que a IA faz:**
1. Busca consulta salva com slug `processos_desembaracados_por_mes_categoria`
2. Encontra a consulta padrão
3. Executa automaticamente

**Consultas padrão disponíveis:**
- `processos_desembaracados_por_mes_categoria` - Processos desembaraçados por mês e categoria
- `pendencias_por_categoria` - Pendências por categoria
- `atrasos_por_navio` - Atrasos por navio

---

### Como salvar consultas

**Formato manual:**
```
"Salva essa consulta como 'Nome do Relatório' com SQL: SELECT ..."
```

**Formato automático:**
```
"Salva essa consulta como 'Nome do Relatório'"
```
(A IA usa a última consulta executada)

---

## 5. 🔄 Fluxo Completo: Combinando Funcionalidades

### Exemplo: Análise personalizada com aprendizado

**Cenário:** Você quer criar um relatório personalizado que será usado frequentemente.

**Passo 1: Definir regra de negócio**
```
Usuário: "Processos com mais de 5 dias de atraso são considerados críticos"
IA: ✅ Regra aprendida salva: **Processos críticos** (ID: 3)
```

**Passo 2: Criar consulta analítica**
```
Usuário: "Mostre processos críticos agrupados por cliente"
IA: [Executa consulta SQL usando a regra aprendida]
    SELECT cliente, COUNT(*) as qtd
    FROM processos_kanban
    WHERE dias_atraso > 5
    GROUP BY cliente
    ORDER BY qtd DESC
```

**Passo 3: Salvar consulta**
```
Usuário: "Salva essa consulta como 'Processos críticos por cliente'"
IA: ✅ Consulta salva com sucesso: **Processos críticos por cliente** (ID: 6)
```

**Passo 4: Usar consulta salva (futuro)**
```
Usuário: "Roda o relatório de processos críticos por cliente"
IA: [Busca e executa a consulta salva automaticamente]
```

**Passo 5: Contexto preservado**
```
Usuário: "Agora mostra só os do Cliente A"
IA: [Usa contexto da consulta anterior e filtra por Cliente A]
```

---

## 6. 🎯 Casos de Uso Reais

### Caso 1: Análise de Performance Mensal

**Objetivo:** Entender performance de desembaraço por mês

**Passos:**
1. **Definir regra:**
   ```
   "Processos desembaraçados são aqueles com data_desembaraco preenchida"
   ```

2. **Criar consulta:**
   ```
   "Mostre processos desembaraçados por mês, categoria e tempo médio de desembaraço"
   ```

3. **Salvar consulta:**
   ```
   "Salva como 'Performance mensal de desembaraço'"
   ```

4. **Usar mensalmente:**
   ```
   "Roda o relatório de performance mensal"
   ```

---

### Caso 2: Monitoramento de Pendências

**Objetivo:** Acompanhar pendências por categoria

**Passos:**
1. **Usar consulta padrão:**
   ```
   "Pendências por categoria"
   ```
   (Já está salva como padrão)

2. **Personalizar:**
   ```
   "Agora mostra só pendências críticas (ICMS ou AFRMM)"
   ```

3. **Salvar versão personalizada:**
   ```
   "Salva como 'Pendências críticas por categoria'"
   ```

---

### Caso 3: Análise de Fornecedores

**Objetivo:** Identificar fornecedores com mais atrasos

**Passos:**
1. **Criar consulta:**
   ```
   "Quais fornecedores têm mais processos atrasados?"
   ```

2. **Refinar:**
   ```
   "Agora mostra o valor total também"
   ```

3. **Salvar:**
   ```
   "Salva como 'Ranking de fornecedores por atraso'"
   ```

4. **Agendar uso:**
   ```
   "Lembra de me mostrar esse relatório toda semana"
   ```
   (Futuro: notificações agendadas)

---

## 7. 📊 Exemplos Práticos de Perguntas Analíticas

### Perguntas que a IA pode responder com consultas SQL

Aqui estão **15 exemplos práticos** de perguntas analíticas que você pode fazer e como a IA responde:

#### Análises de Processos

**Pergunta 1:**
```
"Quantos processos temos por categoria?"
```

**IA gera e executa:**
```sql
SELECT categoria, COUNT(*) as total 
FROM processos_kanban 
GROUP BY categoria 
ORDER BY total DESC
LIMIT 100
```

**Resposta:**
```
✅ Consulta executada com sucesso (5 linhas, fonte: sqlite)

| categoria | total |
|-----------|-------|
| ALH       | 45    |
| VDM       | 32    |
| MV5       | 18    |
| BND       | 12    |
| DMD       | 8     |
```

---

**Pergunta 2:**
```
"Quais navios têm mais processos e qual o atraso médio?"
```

**IA gera e executa:**
```sql
SELECT 
  navio, 
  COUNT(*) as qtd_processos,
  AVG(dias_atraso) as media_atraso
FROM processos_kanban
WHERE navio IS NOT NULL
GROUP BY navio
ORDER BY qtd_processos DESC
LIMIT 100
```

**Resposta:**
```
✅ Consulta executada com sucesso (10 linhas, fonte: sqlite)

| navio          | qtd_processos | media_atraso |
|----------------|---------------|--------------|
| MSC GENEVA     | 15            | 3.2          |
| MAERSK HAMBURG | 12            | 2.8          |
| COSCO SHIPPING | 8             | 4.1          |
...
```

---

**Pergunta 3:**
```
"Mostre processos desembaraçados por mês e categoria"
```

**IA gera e executa:**
```sql
SELECT 
  strftime('%Y-%m', data_desembaraco) AS mes,
  categoria,
  COUNT(*) AS qtd_processos
FROM processos
WHERE data_desembaraco IS NOT NULL
GROUP BY mes, categoria
ORDER BY mes DESC, categoria
LIMIT 100
```

**Resposta:**
```
✅ Consulta executada com sucesso (15 linhas, fonte: sqlite)

| mes     | categoria | qtd_processos |
|---------|-----------|---------------|
| 2025-12 | ALH       | 8             |
| 2025-12 | VDM       | 5             |
| 2025-11 | ALH       | 12            |
...
```

---

#### Análises de Atrasos

**Pergunta 4:**
```
"Quais clientes têm mais processos em atraso?"
```

**IA gera e executa:**
```sql
SELECT 
  cliente,
  COUNT(*) as qtd_processos,
  AVG(dias_atraso) as media_atraso,
  MAX(dias_atraso) as max_atraso
FROM processos_kanban
WHERE dias_atraso > 0
GROUP BY cliente
ORDER BY qtd_processos DESC
LIMIT 100
```

---

**Pergunta 5:**
```
"Mostre processos com atraso crítico (>7 dias) agrupados por categoria"
```

**IA gera e executa:**
```sql
SELECT 
  categoria,
  COUNT(*) as qtd_criticos,
  AVG(dias_atraso) as media_atraso
FROM processos_kanban
WHERE dias_atraso > 7
GROUP BY categoria
ORDER BY qtd_criticos DESC
LIMIT 100
```

---

#### Análises de Pendências

**Pergunta 6:**
```
"Quais categorias têm mais pendências de frete?"
```

**IA gera e executa:**
```sql
SELECT 
  categoria,
  COUNT(*) as qtd_pendencias_frete
FROM notificacoes_processos
WHERE tipo_pendencia LIKE '%frete%'
GROUP BY categoria
ORDER BY qtd_pendencias_frete DESC
LIMIT 100
```

---

**Pergunta 7:**
```
"Mostre processos com pendência de ICMS por mês de chegada"
```

**IA gera e executa:**
```sql
SELECT 
  strftime('%Y-%m', data_chegada) AS mes,
  COUNT(*) as qtd_pendencias_icms
FROM notificacoes_processos
WHERE tipo_pendencia LIKE '%ICMS%'
GROUP BY mes
ORDER BY mes DESC
LIMIT 100
```

---

#### Análises de DUIMP

**Pergunta 8:**
```
"Quantas DUIMPs foram criadas por mês?"
```

**IA gera e executa:**
```sql
SELECT 
  strftime('%Y-%m', criado_em) AS mes,
  COUNT(*) as qtd_duimps
FROM duimps
GROUP BY mes
ORDER BY mes DESC
LIMIT 100
```

---

**Pergunta 9:**
```
"Quais processos têm DUIMP desembaraçada mas ainda não entregue?"
```

**IA gera e executa:**
```sql
SELECT 
  processo_referencia,
  numero as duimp_numero,
  status
FROM duimps
WHERE status LIKE '%DESEMBARACADA%'
  AND status NOT LIKE '%ENTREGUE%'
LIMIT 100
```

---

#### Análises Temporais

**Pergunta 10:**
```
"Qual o tempo médio entre chegada e desembaraço por categoria?"
```

**IA gera e executa:**
```sql
SELECT 
  categoria,
  AVG(julianday(data_desembaraco) - julianday(data_chegada)) as dias_medio
FROM processos
WHERE data_chegada IS NOT NULL 
  AND data_desembaraco IS NOT NULL
GROUP BY categoria
ORDER BY dias_medio DESC
LIMIT 100
```

---

**Pergunta 11:**
```
"Mostre processos que chegaram mas ainda não foram desembaraçados, agrupados por dias de espera"
```

**IA gera e executa:**
```sql
SELECT 
  CASE 
    WHEN (julianday('now') - julianday(data_chegada)) <= 3 THEN '0-3 dias'
    WHEN (julianday('now') - julianday(data_chegada)) <= 7 THEN '4-7 dias'
    WHEN (julianday('now') - julianday(data_chegada)) <= 15 THEN '8-15 dias'
    ELSE 'Mais de 15 dias'
  END as faixa_dias,
  COUNT(*) as qtd_processos
FROM processos
WHERE data_chegada IS NOT NULL
  AND data_desembaraco IS NULL
GROUP BY faixa_dias
ORDER BY faixa_dias
LIMIT 100
```

---

#### Análises de Valores

**Pergunta 12:**
```
"Qual o valor total de frete por navio?"
```

**IA gera e executa:**
```sql
SELECT 
  navio,
  COUNT(*) as qtd_processos,
  SUM(valor_frete) as total_frete
FROM processos_kanban
WHERE navio IS NOT NULL AND valor_frete IS NOT NULL
GROUP BY navio
ORDER BY total_frete DESC
LIMIT 100
```

---

**Pergunta 13:**
```
"Mostre processos com maior valor FOB por categoria"
```

**IA gera e executa:**
```sql
SELECT 
  categoria,
  COUNT(*) as qtd_processos,
  AVG(valor_fob) as media_fob,
  MAX(valor_fob) as max_fob
FROM processos_kanban
WHERE valor_fob IS NOT NULL
GROUP BY categoria
ORDER BY media_fob DESC
LIMIT 100
```

---

#### Análises Combinadas

**Pergunta 14:**
```
"Quais processos têm atraso E pendência de frete?"
```

**IA gera e executa:**
```sql
SELECT 
  p.processo_referencia,
  p.categoria,
  p.dias_atraso,
  n.tipo_pendencia
FROM processos_kanban p
JOIN notificacoes_processos n ON p.processo_referencia = n.processo_referencia
WHERE p.dias_atraso > 0
  AND n.tipo_pendencia LIKE '%frete%'
LIMIT 100
```

---

**Pergunta 15:**
```
"Ranking de fornecedores por quantidade de processos e valor total"
```

**IA gera e executa:**
```sql
SELECT 
  fornecedor,
  COUNT(*) as qtd_processos,
  SUM(valor_fob) as total_fob,
  AVG(dias_atraso) as media_atraso
FROM processos_kanban
WHERE fornecedor IS NOT NULL
GROUP BY fornecedor
ORDER BY qtd_processos DESC
LIMIT 100
```

---

### Como a IA decide gerar SQL

A IA detecta automaticamente quando uma pergunta requer análise de dados e gera SQL quando você usa palavras como:

- **Agregações:** "quantos", "total", "soma", "média", "máximo", "mínimo"
- **Agrupamentos:** "por categoria", "por mês", "agrupado por", "por navio"
- **Rankings:** "mais", "menos", "top", "ranking", "maior", "menor"
- **Análises:** "análise", "relatório", "estatística", "distribuição"
- **Comparações:** "comparar", "diferença", "entre", "versus"

**Exemplos que acionam consultas analíticas:**
- ✅ "Quantos processos temos por categoria?"
- ✅ "Qual o atraso médio por navio?"
- ✅ "Mostre ranking de processos por valor"
- ✅ "Análise de desembaraços por mês"
- ✅ "Compare processos de ALH vs VDM"
- ✅ "Qual a distribuição de processos por situação?"
- ✅ "Mostre top 10 fornecedores por quantidade"
- ✅ "Análise de tempo médio de desembaraço"

**Exemplos que NÃO acionam (são consultas diretas):**
- ❌ "Como está o processo ALH.0145/25?" → `consultar_status_processo`
- ❌ "Liste processos ALH" → `listar_processos_por_categoria`
- ❌ "Quais processos têm pendência?" → `listar_processos_com_pendencias`

---

### 📋 Lista Completa de Perguntas Analíticas

#### Análises Básicas

1. **"Quantos processos temos no total?"**
2. **"Quantos processos temos por categoria?"**
3. **"Quantos processos temos por situação?"**
4. **"Quantos processos temos por navio?"**
5. **"Quantos processos temos por fornecedor?"**

#### Análises de Atrasos

6. **"Quais processos estão mais atrasados?"**
7. **"Qual o atraso médio por categoria?"**
8. **"Qual o atraso médio por navio?"**
9. **"Quais navios têm mais processos atrasados?"**
10. **"Mostre processos com atraso crítico (>7 dias) agrupados por categoria"**

#### Análises Temporais

11. **"Processos desembaraçados por mês"**
12. **"Processos desembaraçados por mês e categoria"**
13. **"Qual o tempo médio entre chegada e desembaraço?"**
14. **"Qual o tempo médio entre chegada e desembaraço por categoria?"**
15. **"Processos que chegaram mas ainda não foram desembaraçados, agrupados por dias de espera"**

#### Análises de Pendências

16. **"Pendências por categoria"**
17. **"Quais categorias têm mais pendências de frete?"**
18. **"Processos com pendência de ICMS por mês de chegada"**
19. **"Pendências de AFRMM por navio"**
20. **"Total de pendências por tipo"**

#### Análises de DUIMP

21. **"Quantas DUIMPs foram criadas por mês?"**
22. **"DUIMPs por situação"**
23. **"DUIMPs por canal (verde, amarelo, vermelho)"**
24. **"Processos com DUIMP desembaraçada mas ainda não entregue"**
25. **"Tempo médio de análise de DUIMP por categoria"**

#### Análises de Valores

26. **"Valor total de frete por navio"**
27. **"Valor total FOB por categoria"**
28. **"Processos com maior valor FOB por categoria"**
29. **"Valor médio de frete por navio"**
30. **"Total de impostos pagos por mês"**

#### Rankings e Top Lists

31. **"Top 10 navios por quantidade de processos"**
32. **"Top 10 fornecedores por quantidade de processos"**
33. **"Top 10 clientes por valor total"**
34. **"Ranking de processos por atraso"**
35. **"Ranking de categorias por quantidade de processos"**

#### Análises Combinadas

36. **"Processos com atraso E pendência de frete"**
37. **"Processos desembaraçados mas com pendência de ICMS"**
38. **"Navios com mais processos E maior atraso médio"**
39. **"Categorias com mais processos E mais pendências"**
40. **"Fornecedores com mais processos atrasados E maior valor total"**

#### Análises Comparativas

41. **"Compare quantidade de processos ALH vs VDM"**
42. **"Compare atraso médio por categoria"**
43. **"Compare desembaraços deste mês vs mês anterior"**
44. **"Compare pendências de frete vs AFRMM"**
45. **"Compare processos marítimos vs aéreos"**

#### Análises de Performance

46. **"Taxa de desembaraço por categoria (processos desembaraçados / total)"**
47. **"Taxa de processos com pendências por categoria"**
48. **"Eficiência de desembaraço (tempo médio) por navio"**
49. **"Processos que chegaram mas não foram registrados em X dias"**
50. **"Análise de conversão: chegada → registro → desembaraço"**

---

### 💡 Dicas para Fazer Perguntas Analíticas

**✅ Use palavras-chave que indicam análise:**
- "Quantos", "Qual", "Mostre", "Análise", "Ranking", "Top", "Média", "Total", "Soma", "Distribuição"

**✅ Seja específico sobre agrupamento:**
- "por categoria", "por mês", "por navio", "agrupado por", "por tipo"

**✅ Mencione métricas:**
- "média", "total", "soma", "máximo", "mínimo", "contagem"

**✅ Use comparações:**
- "vs", "comparar", "diferença entre", "mais que", "menos que"

**Exemplos de perguntas bem formuladas:**
- ✅ "Quantos processos temos por categoria este mês?"
- ✅ "Qual o atraso médio por navio nos últimos 30 dias?"
- ✅ "Mostre ranking dos top 10 fornecedores por quantidade de processos"
- ✅ "Análise de desembaraços: compare este mês com o mês anterior"
- ✅ "Distribuição de processos por situação e categoria"

---

## 8. 📝 Dicas de Uso

### ✅ Boas Práticas

1. **Seja específico ao definir regras:**
   - ❌ "Processos que chegaram"
   - ✅ "O campo data_destino_final indica que o processo chegou ao destino final"

2. **Nomeie consultas de forma descritiva:**
   - ❌ "Consulta 1"
   - ✅ "Processos críticos por cliente em 2025"

3. **Use contexto para refinar consultas:**
   - ✅ "Agora mostra só os MV5"
   - ✅ "Filtra por mês de dezembro"

4. **Faça perguntas analíticas claras:**
   - ✅ "Quantos processos temos por categoria?"
   - ✅ "Qual o atraso médio por navio?"
   - ✅ "Mostre ranking de processos por valor"

### ⚠️ Limitações

1. **Consultas SQL:**
   - Apenas SELECT (somente leitura)
   - LIMIT automático (máximo 1000 linhas)
   - Tabelas permitidas são validadas

2. **Regras aprendidas:**
   - Máximo de 5 regras por prompt (para não sobrecarregar)
   - Regras são aplicadas quando fazem sentido no contexto

3. **Contexto de sessão:**
   - Limpo quando sessão expira
   - Pode ser limpo manualmente com comando "reset"

---

## 8. 🔧 Comandos Úteis

### Ver consultas salvas
```
"Lista as consultas salvas"
"Quais relatórios tenho disponíveis?"
```

### Ver regras aprendidas
```
"Quais regras você aprendeu?"
"Mostra as definições que você sabe"
```

### Limpar contexto
```
"Reset"
"Limpa o contexto"
"Esquece o que estávamos falando"
```

### Executar consulta específica
```
"Roda a consulta 'Nome da Consulta'"
"Executa o relatório de processos críticos"
```

---

## 9. 🎓 Aprendizado Contínuo

O sistema aprende com o uso:

1. **Uso frequente:** Regras e consultas mais usadas aparecem primeiro
2. **Incremento automático:** Contador de uso é incrementado automaticamente
3. **Ordenação inteligente:** Mais usadas = mais relevantes

**Exemplo:**
- Você usa "Processos críticos por cliente" 10 vezes
- Você usa "Atrasos por navio" 2 vezes
- Na próxima vez que perguntar "relatório", a IA sugerirá "Processos críticos por cliente" primeiro

---

## 10. 📊 Exemplos de SQL Gerados

### Exemplo 1: Agregação simples
```sql
SELECT categoria, COUNT(*) as total
FROM processos_kanban
GROUP BY categoria
ORDER BY total DESC
LIMIT 100
```

### Exemplo 2: Análise temporal
```sql
SELECT 
  strftime('%Y-%m', data_desembaraco) AS mes,
  categoria,
  COUNT(*) AS qtd,
  AVG(dias_atraso) AS media_atraso
FROM processos
WHERE data_desembaraco IS NOT NULL
GROUP BY mes, categoria
ORDER BY mes DESC, categoria
LIMIT 100
```

### Exemplo 3: Ranking com filtros
```sql
SELECT 
  navio,
  COUNT(*) as qtd_processos,
  AVG(dias_atraso) as media_atraso,
  MAX(dias_atraso) as max_atraso
FROM processos_kanban
WHERE navio IS NOT NULL 
  AND dias_atraso > 0
GROUP BY navio
HAVING COUNT(*) >= 3
ORDER BY media_atraso DESC
LIMIT 100
```

---

**Última atualização:** 18/12/2025
