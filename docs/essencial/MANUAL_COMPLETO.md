# 📚 Manual Completo - Chat IA Independente

**Versão:** 1.8  
**Data:** 06/01/2026  
**Sistema:** Chat IA Independente - Assistente Inteligente para COMEX

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Funcionalidades Principais](#funcionalidades-principais)
3. [Consultas de Processos](#consultas-de-processos)
4. [Gerenciamento de DUIMP](#gerenciamento-de-duimp)
5. [Consultas de CE (Conhecimento de Embarque)](#consultas-de-ce-conhecimento-de-embarque)
6. [Consultas de CCT (Conhecimento de Carga Aérea)](#consultas-de-cct-conhecimento-de-carga-aérea)
7. [Consultas de DI (Declaração de Importação)](#consultas-de-di-declaração-de-importação)
8. [NCM e NESH](#ncm-e-nesh)
9. [Email](#email)
10. [Santander Open Banking](#-santander-open-banking-novo)
11. [Banco do Brasil](#-banco-do-brasil-novo---06012026)
12. [Consultas Bilhetadas](#consultas-bilhetadas)
13. [Relatórios e Dashboards](#relatórios-e-dashboards)
14. [Aprendizado e Contexto](#aprendizado-e-contexto)
15. [Configurações e Observabilidade](#configurações-e-observabilidade)
16. [Exemplos de Uso Prático](#exemplos-de-uso-prático)
17. [APIs Externas Utilizadas](#apis-externas-utilizadas)
18. [Arquitetura e Serviços](#arquitetura-e-serviços)

---

## 🎯 Visão Geral

O **Chat IA Independente** é um assistente inteligente especializado em operações de COMEX (Comércio Exterior) que permite interagir com processos de importação, DUIMPs, CEs, CCTs, DIs e outros documentos através de linguagem natural.

### Principais Características

- ✅ **Interface Conversacional**: Interação em português natural
- ✅ **Processamento Inteligente**: Usa IA (GPT) para entender intenções
- ✅ **Múltiplas Fontes de Dados**: SQLite, SQL Server, APIs externas
- ✅ **Cache Inteligente**: Reduz custos de APIs bilhetadas
- ✅ **Aprendizado Contínuo**: Aprende regras e preferências do usuário
- ✅ **Contexto Persistente**: Mantém contexto entre mensagens
- ✅ **Envio de Emails**: Envio e recebimento de emails com processos
- ✅ **Relatórios Automáticos**: Geração de dashboards e resumos

---

## 📦 Funcionalidades Principais

### Categorias de Funcionalidades

1. **Processos de Importação** - Consultas, listagens, filtros
2. **DUIMP** - Criação, consulta, extratos
3. **CE (Conhecimento de Embarque)** - Consultas, extratos, situação
4. **CCT (Conhecimento de Carga Aérea)** - Consultas, extratos
5. **DI (Declaração de Importação)** - Consultas, extratos, vinculação
6. **NCM e NESH** - Busca, sugestão com IA, notas explicativas
7. **Email** - Verificação, leitura, resposta automática
8. **Consultas Bilhetadas** - Aprovação, rejeição, execução
9. **Relatórios** - Dashboards, resumos, fechamentos
10. **Aprendizado** - Regras personalizadas, consultas salvas

---

## 🔍 Consultas de Processos

### Consultar Status de Processo Específico

**Função:** `consultar_status_processo`

**Quando usar:** Quando o usuário mencionar um número de processo específico (ex: ALH.0145/25)

**Exemplos de uso no chat:**
- "como está o processo ALH.0145/25?"
- "status do VDM.0003/25"
- "detalhes do processo MSS.0018/25"
- "como está ALH.0145/25"

**⚠️ IMPORTANTE - Contexto:**
- Esta função salva automaticamente o processo no contexto (`processo_atual`) se a consulta for bem-sucedida
- Após consultar um processo, você pode fazer follow-ups como "e a DI?" ou "e a DUIMP?" sem repetir o número
- Se a mensagem for uma pergunta de painel (ex: "como estão os MV5?"), esta função NÃO é chamada - use `listar_processos_por_categoria` nesse caso

**O que retorna:**
- Informações completas do processo
- CEs vinculados com situação
- CCTs vinculados
- DI vinculada (número, situação, canal, desembaraço)
- DUIMP vinculada (número, situação, canal, versão)
- Bloqueios (se houver)
- Pendências (frete, AFRMM, ICMS)
- Valores (FOB, frete, seguro, CIF)
- ETA e informações de navio
- Documentos enviados na DUIMP (tipo 30, 73, 49)

**⚠️ Exceção:** Se a mensagem contém "averbacao" ou "averbação", use `consultar_averbacao_processo` ao invés desta função.

---

### Consultar Dados de Averbação

**Função:** `consultar_averbacao_processo`

**Quando usar:** Quando o usuário mencionar "averbacao", "averbação", "averbar" ou "dados de averbação" + número de processo

**Exemplos de uso no chat:**
- "averbacao processo BND.0030/25"
- "averbação BND.0030/25"
- "dados de averbação para ALH.0166/25"
- "mostre averbação do processo VDM.0003/25"

**O que retorna:**
- **CE**: Porto origem, país, porto destino, data emissão, tipo, mercadoria
- **DI**: Número, navio, retificação
- **Valores USD**: Custo/VMLE, frete, seguro, despesas 10%, lucros 10%
- **Valores BRL**: Frete, seguro, VMLD
- **Impostos detalhados**: II, IPI, PIS, COFINS, Antidumping, Taxa SISCOMEX (em BRL e USD com PTAX)

**Requisito:** O processo deve ter DI registrada.

---

### Listar Processos

**Função:** `listar_processos`

**Quando usar:** Quando o usuário pedir uma lista geral de processos SEM mencionar categoria específica

**Exemplos de uso no chat:**
- "listar processos"
- "mostrar processos pendentes"
- "ver processos"

**Parâmetros:**
- `status`: Filtrar por status (pendente, processando, sucesso, erro, todos)
- `limite`: Número máximo de processos (padrão: 20)

**⚠️ Não use:** Se o usuário mencionar categoria específica (ALH, VDM, etc.) - use `listar_processos_por_categoria` nesse caso.

---

### Listar Processos por Categoria

**Função:** `listar_processos_por_categoria`

**Quando usar:** Para perguntas genéricas sobre uma categoria específica

**Exemplos de uso no chat:**
- "como estão os processos ALH?"
- "mostre os processos VDM"
- "listar processos MSS"
- "quando chegam os VDM?" (sem período específico)

**⚠️ IMPORTANTE - Perguntas de Painel:**
- Esta função é usada para **perguntas de painel/visão geral** sobre uma categoria
- Perguntas de painel NUNCA usam `processo_atual` do contexto
- Elas sempre retornam listas/visões gerais, não informações de um processo específico
- Se você mencionar um processo específico (ex: "ALH.0145/25"), use `consultar_status_processo` ao invés desta função

**Parâmetros:**
- `categoria`: Categoria do processo (ALH, VDM, MSS, MV5, GYM, etc.)
- `limite`: Número máximo de processos (padrão: 200)

**O que retorna:**
- Lista de processos da categoria
- Situação de DI/DUIMP/CCT/CE quando disponível
- ETA, Porto, Navio, Status do Kanban

**⚠️ Exceções:**
- Se a pergunta for "quais os embarques [CATEGORIA] chegaram?" → use `listar_processos_liberados_registro`
- Se mencionar período específico (hoje, amanhã, semana) → use `listar_processos_por_eta`

---

### Listar Processos por Situação

**Função:** `listar_processos_por_situacao`

**Quando usar:** Quando o usuário perguntar sobre processos de uma categoria específica com situação específica (desembaraçados, registrados, entregues)

**Exemplos de uso no chat:**
- "quais ALH estão desembaraçados?"
- "quais processos GYM estão entregues?"
- "mostre processos VDM registrados"
- "listar ALH desembaraçados"

**Parâmetros:**
- `categoria`: Categoria do processo (obrigatório)
- `situacao`: Situação a filtrar (desembaraçado, registrado, entregue, di_desembaracada)
- `limite`: Número máximo de processos (padrão: 200)

**⚠️ Importante:** "embarques [CATEGORIA] chegaram" → use `listar_processos_liberados_registro` ao invés desta função.

---

### Listar Todos os Processos por Situação

**Função:** `listar_todos_processos_por_situacao`

**Quando usar:** Quando o usuário perguntar de forma genérica SEM mencionar categoria específica

**Exemplos de uso no chat:**
- "quais processos estão desembaraçados?" (sem mencionar categoria)
- "quais processos estão armazenados?"
- "quais processos estão com bloqueio?"
- "quais processos estão com pendência?"

**Parâmetros:**
- `situacao`: Situação a filtrar (opcional)
- `filtro_pendencias`: Se true, filtra apenas processos com pendências
- `filtro_bloqueio`: Se true, filtra apenas processos com bloqueios
- `limite`: Número máximo de processos (padrão: 500)

**⚠️ Não use:** Se o usuário mencionar categoria específica - use `listar_processos_por_situacao` nesse caso.

---

### Listar Processos com Pendências

**Função:** `listar_processos_com_pendencias`

**Quando usar:** Quando o usuário perguntar sobre processos com pendências (frete não pago, AFRMM não pago)

**Exemplos de uso no chat:**
- "quais processos têm pendência?"
- "quais processos estão com pendência?"
- "quais ALH estão com pendências?"
- "quais processos de ALH têm pendência de frete?"

**Parâmetros:**
- `categoria`: Categoria do processo (opcional - se não fornecido, retorna todas as categorias)
- `limite`: Número máximo de processos (padrão: 200)

**O que retorna:** Apenas processos que têm pelo menos uma das seguintes pendências:
- Pendência de frete
- Pendência de AFRMM (CE marítimo apenas)

**⚠️ Diferença:** BLOQUEIOS são diferentes de PENDÊNCIAS. Bloqueios são bloqueios físicos/administrativos da carga. Pendências são valores não pagos.

---

### Listar Processos por ETA

**Função:** `listar_processos_por_eta`

**Quando usar:** Quando o usuário mencionar período específico (hoje, amanhã, esta semana, próximo mês, data específica)

**Exemplos de uso no chat:**
- "quais processos chegam amanhã?"
- "quais chegam hoje?"
- "quais chegam na próxima semana?"
- "quais processos chegam neste mês?"
- "quais chegam em 22/11/2025?"
- "o que tem pra chegar?" (genérico)

**Parâmetros:**
- `filtro_data`: Período (hoje, amanha, semana, proxima_semana, mes, proximo_mes, futuro, data_especifica)
- `data_especifica`: Data específica no formato DD/MM/AAAA (quando filtro_data='data_especifica')
- `categoria`: Categoria do processo (opcional - só use se o usuário mencionar explicitamente)
- `limite`: Número máximo de processos (padrão: 200)

**⚠️ Não use:** Se a pergunta for "quando chegam os [CATEGORIA]?" SEM período específico - use `listar_processos_por_categoria` nesse caso.

---

### Listar Processos por Navio

**Função:** `listar_processos_por_navio`

**Quando usar:** Quando o usuário perguntar sobre processos em um navio específico

**Exemplos de uso no chat:**
- "quais processos estão no navio CMA CGM BAHIA?"
- "quais processos mv5 estão no navio X?"
- "mostre processos do navio Y"

**Parâmetros:**
- `nome_navio`: Nome do navio (busca parcial, case-insensitive)
- `categoria`: Categoria do processo (opcional - use se o usuário mencionar categoria junto com navio)
- `limite`: Número máximo de processos (padrão: 200)

---

### Listar Processos em DTA

**Função:** `listar_processos_em_dta`

**Quando usar:** Quando o usuário perguntar sobre processos que estão em DTA (Declaração de Trânsito Aduaneiro)

**Exemplos de uso no chat:**
- "quais processos estão em DTA?"
- "quais processos têm DTA?"
- "quais MV5 estão em DTA?"
- "quais processos estão em trânsito?"

**Parâmetros:**
- `categoria`: Categoria do processo (opcional - só use se o usuário mencionar categoria específica)
- `limite`: Número máximo de processos (padrão: 200)

**O que retorna:** Processos que têm número de DTA preenchido (indicando que estão em trânsito para outro recinto alfandegado)

**⚠️ Importante:** "em DTA" NÃO é uma categoria! É uma situação do processo.

---

### Listar Processos Liberados para Registro

**Função:** `listar_processos_liberados_registro`

**Quando usar:** Quando o usuário perguntar "quais os embarques [CATEGORIA] chegaram?" ou sobre processos que chegaram sem despacho

**Exemplos de uso no chat:**
- "quais os embarques GYM chegaram?"
- "quais os embarques ALH chegaram?"
- "quais processos chegaram sem despacho?"
- "quais processos estão liberados para registro?"
- "quais ALH chegaram sem DI?"

**Parâmetros:**
- `categoria`: Categoria do processo (opcional)
- `dias_retroativos`: Número de dias para buscar retroativamente (padrão: 30)
- `data_inicio`: Data início do período (formato YYYY-MM-DD ou DD/MM/YYYY)
- `data_fim`: Data fim do período (formato YYYY-MM-DD ou DD/MM/YYYY)
- `limite`: Número máximo de processos (padrão: 200)

**O que retorna:** Processos que:
- Já chegaram (data de chegada <= hoje)
- NÃO têm DI registrada
- NÃO têm DUIMP desembaraçada

**⚠️ Regra de Ouro:** Se a pergunta contém "embarques" E "chegaram", SEMPRE use esta função.

---

### Listar Processos Registrados Hoje

**Função:** `listar_processos_registrados_hoje`

**Quando usar:** Quando o usuário perguntar sobre processos que tiveram DI ou DUIMP registrada hoje

**Exemplos de uso no chat:**
- "o que registramos hoje?"
- "quais processos foram registrados hoje?"
- "o que foi registrado hoje?"
- "o que registramos hoje de MSS?"

**Parâmetros:**
- `categoria`: Categoria do processo (opcional)
- `limite`: Número máximo de processos (padrão: 200)

**O que retorna:** Processos com DI/DUIMP vinculada HOJE (usando data de `atualizado_em` da tabela `processo_documentos`)

---

### Listar Processos com DUIMP

**Função:** `listar_processos_com_duimp`

**Quando usar:** Quando o usuário perguntar quais processos têm DUIMP registrada

**Exemplos de uso no chat:**
- "quais processos têm duimp registrada?"
- "quais processos já têm duimp?"
- "mostre processos com duimp"

**Parâmetros:**
- `limite`: Número máximo de processos (padrão: 50)

---

### Consultar Processo Consolidado

**Função:** `consultar_processo_consolidado`

**Quando usar:** Quando o usuário quiser uma visão completa e enriquecida com todos os dados de um processo

**Exemplos de uso no chat:**
- "me mostre tudo sobre o processo ALH.0165/25"
- "consulte o processo VDM.0003/25"

**Parâmetros:**
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA

**O que retorna:** JSON consolidado completo incluindo:
- Todos os documentos (CE, CCT, DI, DUIMP)
- Valores
- Tributos
- Timeline
- Semântica
- Pendências
- Situação da DUIMP/DI
- Canal
- Pendências de frete e AFRMM
- CEs vinculados
- Valores (FOB, frete, seguro, CIF)
- Tributos

---

## 📝 Gerenciamento de DUIMP

### Criar DUIMP

**Função:** `criar_duimp`

**Quando usar:** Quando o usuário pedir para "registrar", "criar", "gerar" ou "fazer" uma DUIMP

**Exemplos de uso no chat:**
- "registre a duimp do MSS.0018/25"
- "crie duimp para VDM.0003/25"
- "gerar duimp do processo X"

**Parâmetros:**
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA (obrigatório)
- `ambiente`: Ambiente onde criar (validacao ou producao) - padrão: validacao

**Ambientes:**
- **Validação** (padrão): Para testes, ajusta CE automaticamente
- **Produção**: Requer `DUIMP_ALLOW_WRITE_PROD=1` no `.env`

**O que faz:**
1. Busca dados do processo
2. Busca CE ou CCT vinculado
3. Cria DUIMP no Portal Único
4. Vincula ao processo no banco local
5. Retorna número e versão da DUIMP criada

**⚠️ Não use:** `verificar_duimp_registrada` quando o usuário pedir para REGISTRAR - use `criar_duimp` diretamente.

---

### Verificar DUIMP Registrada

**Função:** `verificar_duimp_registrada`

**Quando usar:** Quando o usuário PERGUNTAR sobre DUIMP de um processo específico

**Exemplos de uso no chat:**
- "tem DUIMP registrada para ALH.0145/25?"
- "tem duimp para ALH.0145/25?"
- "a duimp foi registrada?"
- "já tem duimp?"
- "foi criada?"

**Parâmetros:**
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA (obrigatório)

**O que retorna:**
- Se existe DUIMP de PRODUÇÃO ou VALIDAÇÃO vinculada ao processo
- Número da DUIMP
- Versão
- Situação

**⚠️ Importante:** A palavra "registrada" aqui NÃO é uma situação - é apenas uma forma de perguntar se EXISTE uma DUIMP.

**⚠️ Não use:** Quando o usuário PEDIR para registrar/criar - use `criar_duimp` nesse caso.

---

### Obter Dados de DUIMP

**Função:** `obter_dados_duimp`

**Quando usar:** Quando o usuário perguntar sobre uma DUIMP específica

**Exemplos de uso no chat:**
- "qual a situação da DUIMP 25BR00000250599?"
- "como está a DUIMP 25BR00001928777?"
- "qual o canal da DUIMP Y?"

**Parâmetros:**
- `numero_duimp`: Número da DUIMP (formato: 25BR00001928777 ou 25BR00001928777-1)
- `versao_duimp`: Versão da DUIMP (opcional - se não informada, busca versão vigente)

**O que retorna:**
- Situação
- Canal
- Data de registro
- Versão
- Processo vinculado

---

### Obter Extrato PDF da DUIMP

**Função:** `obter_extrato_pdf_duimp`

**Quando usar:** Quando o usuário pedir explicitamente "extrato" ou "pdf" da DUIMP

**Exemplos de uso no chat:**
- "extrato da duimp do vdm.0003/25"
- "extrato da duimp 25BR00002284997"
- "pdf da duimp do processo X"

**Parâmetros:**
- `processo_referencia`: Número do processo (busca DUIMP vinculada)
- `numero_duimp`: Número da DUIMP diretamente

**O que faz:**
1. Busca número e versão da DUIMP no banco pelo processo OU pelo numero_duimp diretamente
2. Autentica no Portal Único (mTLS)
3. Consulta capa completa da DUIMP
4. Consulta todos os itens da DUIMP
5. Retorna dados detalhados do extrato formatados

**⚠️ Não use:** `consultar_status_processo` quando o usuário pedir "extrato" ou "pdf" - use esta função!

---

### Vincular DUIMP a Processo

**Função:** `vincular_processo_duimp`

**Quando usar:** Quando o usuário pedir para incluir/vincular um número de DUIMP ou DI a um processo

**Exemplos de uso no chat:**
- "inclua o numero duimp 25BR0000194844-1 no processo GLT.0034/25"
- "vincular duimp 25BR0000194844 ao processo X"
- "incluir di 25/2535383-7 no processo Y"

**Parâmetros:**
- `numero_duimp`: Número da DUIMP ou DI
  - DUIMP: 25BR0000194844 ou 25BR0000194844-1
  - DI: 25/2535383-7
- `versao_duimp`: Versão da DUIMP (opcional - busca automaticamente se não informada)
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA

**Funcionalidade:** A função reconhece automaticamente se é DUIMP ou DI pelo formato do número.

---

## 🚢 Consultas de CE (Conhecimento de Embarque)

### Consultar CE Marítimo

**Função:** `consultar_ce_maritimo`

**Quando usar:** Quando o usuário pedir para consultar, buscar ou verificar um CE específico

**Exemplos de uso no chat:**
- "consulte o CE 132505317461600"
- "qual a situação do CE 132505284200462?"

**Parâmetros:**
- `numero_ce`: Número do CE (15 dígitos) - obrigatório se processo_referencia não fornecido
- `processo_referencia`: Número do processo - busca CE vinculado - obrigatório se numero_ce não fornecido
- `usar_cache_apenas`: Se true, busca apenas no cache SEM consultar API (padrão: false)
- `forcar_consulta_api`: Se true, força consulta API mesmo sem alterações (padrão: false)

**⚠️ API BILHETADA:** Esta função consulta a API Integra Comex (Serpro) que é BILHETADA (paga por consulta - R$ 0,942 por consulta).

**Decisão Inteligente:**
- A função AUTOMATICAMENTE consulta a API pública (gratuita) antes de bilhetar
- Se não houver alterações, retorna do cache (SEM bilhetar)
- Se houver alterações ou não estiver no cache, consulta API bilhetada

**⚠️ Quando usar `usar_cache_apenas=True`:**
- O usuário perguntar sobre situação/status sem pedir para "consultar"
- Você quer SEMPRE evitar custos de API bilhetada

**⚠️ Quando usar `forcar_consulta_api=True`:**
- O usuário pedir explicitamente para "consultar"
- Você precisa garantir dados atualizados mesmo sem alterações

---

### Verificar Atualização de CE

**Função:** `verificar_atualizacao_ce`

**Quando usar:** ANTES de `consultar_ce_maritimo` para tomar uma decisão inteligente sobre se precisa bilhetar

**Exemplos de uso no chat:**
- Usado automaticamente pelo sistema

**Parâmetros:**
- `numero_ce`: Número do CE (15 dígitos)

**O que faz:**
- Consulta a API pública (gratuita)
- Compara com o cache
- Retorna se precisa atualizar (bilhetar) ou se pode usar cache (sem custo)

**⚠️ API PÚBLICA GRATUITA:** Esta função NÃO bilheta, apenas verifica se há alterações.

---

### Listar Processos com Situação de CE

**Função:** `listar_processos_com_situacao_ce`

**Quando usar:** Quando o usuário perguntar sobre processos em geral com situação de CE

**Exemplos de uso no chat:**
- "quais processos estão armazenados?"
- "quais processos têm CE entregue?"
- "mostre processos com situação X"

**Parâmetros:**
- `situacao_filtro`: Situação do CE (ARMAZENADA, ENTREGUE, EM_TRANSITO, DESCARREGADA, BLOQUEADA, todas)
- `limite`: Número máximo de processos (padrão: 50)

**⚠️ SEM CUSTO:** Esta função NUNCA consulta API bilhetada, apenas usa dados do cache, então é GRATUITA.

---

### Obter Extrato do CE

**Função:** `obter_extrato_ce`

**Quando usar:** Quando o usuário pedir explicitamente "extrato" do CE

**Exemplos de uso no chat:**
- "extrato do ce do vdm.0003/25"
- "extrato do ce 132505317461600"
- "pdf do ce do processo X"

**Parâmetros:**
- `processo_referencia`: Número do processo (busca CE vinculado)
- `numero_ce`: Número do CE diretamente

**O que faz:**
1. Busca número do CE no banco pelo processo OU pelo numero_ce diretamente
2. Consulta cache local primeiro (sem custo)
3. Se não encontrar no cache ou precisar atualizar, consulta API Integra Comex (Serpro) - BILHETADA
4. Retorna dados formatados do extrato

**⚠️ API BILHETADA:** A consulta só será feita se necessário.

**⚠️ Não use:** `consultar_ce_maritimo` quando o usuário pedir "extrato do ce" - use esta função!

---

## ✈️ Consultas de CCT (Conhecimento de Carga Aérea)

### Consultar CCT

**Função:** `consultar_cct`

**Quando usar:** Quando o usuário pedir para consultar, buscar ou verificar um CCT específico

**Exemplos de uso no chat:**
- "como está o cct CWL25100012"
- "consulte o CCT MIA-4673"
- "qual a situação do CCT Y?"

**Parâmetros:**
- `numero_cct`: Número do CCT - obrigatório se processo_referencia não fornecido
- `processo_referencia`: Número do processo - busca CCT vinculado - obrigatório se numero_cct não fornecido
- `usar_cache_apenas`: Se true, busca apenas no cache (padrão: false)

**⚠️ API GRATUITA:** A API de CCT é GRATUITA (não é bilhetada), então pode ser consultada sem custo.

**O que faz:**
- Consulta a API gratuita
- Salva no cache automaticamente
- Retorna dados do CCT incluindo situação, datas, origem, destino

---

### Obter Extrato do CCT

**Função:** `obter_extrato_cct`

**Quando usar:** Quando o usuário pedir explicitamente "extrato" do CCT

**Exemplos de uso no chat:**
- "extrato do cct do vdm.0003/25"
- "extrato do cct CWL25100012"
- "pdf do cct do processo X"

**Parâmetros:**
- `processo_referencia`: Número do processo (busca CCT vinculado)
- `numero_cct`: Número do CCT diretamente

**O que faz:**
1. Busca número do CCT no banco pelo processo OU pelo numero_cct diretamente
2. Consulta cache local primeiro (sem custo)
3. Se não encontrar no cache ou precisar atualizar, consulta API CCTA - GRATUITA
4. Retorna dados formatados do extrato

**⚠️ API GRATUITA:** A API CCTA é GRATUITA (não bilhetada).

**⚠️ Não use:** `consultar_cct` quando o usuário pedir "extrato do cct" - use esta função!

---

### Vincular CCT a Processo

**Função:** `vincular_processo_cct`

**Quando usar:** Quando o usuário informar qual processo vincular a um CCT

**Exemplos de uso no chat:**
- "vincule ao processo MSS.0018/25" (após consultar CCT)
- Usado automaticamente quando o usuário responde a pergunta sobre vinculação

**Parâmetros:**
- `numero_cct`: Número do CCT
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA

**O que faz:**
- Atualiza o cache do CCT
- Deixa pronto para gerar DUIMP
- Cada processo deve ter apenas um CCT - CCTs antigos são automaticamente desvinculados

---

## 📄 Consultas de DI (Declaração de Importação)

### Obter Dados de DI

**Função:** `obter_dados_di`

**Quando usar:** Quando o usuário perguntar sobre uma DI específica

**Exemplos de uso no chat:**
- "qual a situação da DI 2521440840?"
- "qual canal da DI 2521440840?"
- "quando foi o desembaraço da DI 2521440840?"

**Parâmetros:**
- `numero_di`: Número da DI sem barras (ex: 2521440840)

**O que retorna:**
- Situação
- Canal
- Data de desembaraço
- Data de registro
- Situação de entrega
- Processo vinculado

---

### Obter Extrato PDF da DI

**Função:** `obter_extrato_pdf_di`

**Quando usar:** Quando o usuário pedir explicitamente "extrato" ou "pdf" da DI

**Exemplos de uso no chat:**
- "extrato da di do vdm.0003/25"
- "pdf da di do alh.0010/25"
- "extrato da di 2524635120"

**Parâmetros:**
- `processo_referencia`: Número do processo (busca DI vinculada)
- `numero_di`: Número da DI diretamente

**O que faz:**
1. Busca número da DI no banco pelo processo OU pelo numero_di diretamente
2. Consulta cache local primeiro (sem custo)
3. Se não encontrar no cache, consulta API Integra Comex (Serpro) - BILHETADA
4. Gera PDF do extrato

**⚠️ API BILHETADA:** A consulta só será feita se a DI não estiver no cache.

**⚠️ Não use:** `obter_dados_di` quando o usuário pedir "extrato" ou "pdf" da DI - use esta função!

---

### Vincular DI a Processo

**Função:** `vincular_processo_di`

**Quando usar:** Quando o usuário informar qual processo vincular a uma DI

**Parâmetros:**
- `numero_di`: Número da DI (ex: 2524635120)
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA

**O que faz:**
- Atualiza o cache da DI
- Uma DI pode estar vinculada a múltiplos processos se necessário

---

## 🏷️ NCM e NESH

### Buscar NCMs por Descrição

**Função:** `buscar_ncms_por_descricao`

**Quando usar:** Quando o usuário perguntar sobre NCMs de um produto

**Exemplos de uso no chat:**
- "qual o NCM de alho?"
- "buscar NCM para celular"
- "encontrar NCM de medicamento"
- "quais NCMs têm alho na descrição?"

**Parâmetros:**
- `termo`: Termo de busca para descrição do produto (ex: "alho", "celular") - obrigatório
- `limite`: Número máximo de resultados (padrão: 50, máximo: 200)
- `incluir_relacionados`: Se true, inclui NCMs relacionados na hierarquia (padrão: true)

**O que retorna:** Lista de NCMs que contêm o termo de busca na descrição, agrupados por hierarquia

---

### Sugerir NCM com IA

**Função:** `sugerir_ncm_com_ia`

**Quando usar:** Quando o usuário perguntar sobre NCM de um produto usando IA

**Exemplos de uso no chat:**
- "qual o ncm do gv50?"
- "qual o ncm do gps?"
- "qual o ncm de alho?"
- "IA sugerir NCM para X"
- "recomendar NCM para produto Y"

**Parâmetros:**
- `descricao`: Descrição do produto (ex: "alho para tempero", "celular smartphone") - obrigatório
- `contexto`: Contexto adicional opcional (país de origem, tipo de produto, etc.)
- `usar_cache`: Se true, usa RAG com cache local para maior precisão (padrão: true)
- `validar_sugestao`: Se true, valida se NCM sugerido existe no cache (padrão: true)

**O que faz:**
- Usa IA para analisar a descrição
- Sugere o NCM mais adequado
- Valida se o NCM sugerido existe no cache
- Sugere alternativas similares se necessário

**⚠️ Não use:** Para categorias de processos (ALH, VDM, etc.) - use para produtos!

---

### Detalhar NCM

**Função:** `detalhar_ncm`

**Quando usar:** Quando o usuário pedir para detalhar a hierarquia completa de um NCM

**Exemplos de uso no chat:**
- "detalhar NCM 841451"
- "mostrar hierarquia do NCM Y"
- "quais são todos os NCMs de 8 dígitos do grupo 8415?"

**Parâmetros:**
- `ncm`: NCM a detalhar (4, 6 ou 8 dígitos) - ex: "8414", "841451", "84145100"

**O que retorna:**
1. A hierarquia completa (4, 6 e 8 dígitos)
2. Todos os NCMs de 8 dígitos que pertencem àquele grupo

---

### Buscar Nota Explicativa NESH

**Função:** `buscar_nota_explicativa_nesh`

**Quando usar:** Quando o usuário perguntar sobre regras de classificação ou quiser entender melhor como classificar um produto

**Exemplos de uso no chat:**
- "qual a nota explicativa do NCM 841451?"
- "quais são os critérios para classificar ventilador?"
- "o que diz a NESH sobre o NCM 84.14.51?"
- "buscar na nesh alho" (busca direta)
- "consultar nesh para ventilador"

**Parâmetros:**
- `ncm`: Código NCM (4, 6 ou 8 dígitos) - opcional
- `descricao_produto`: Descrição do produto para busca semântica - opcional
- `limite`: Número máximo de notas explicativas (padrão: 3)

**O que retorna:** Notas Explicativas oficiais da Receita Federal que detalham como classificar produtos na NCM

**⚠️ Busca Direta:** Se o usuário pedir explicitamente "buscar na NESH", "consultar NESH", "pesquisar NESH" ou "NESH de [produto]", use ESTA função diretamente (busca direta, sem passar por IA).

---

### Baixar Nomenclatura NCM

**Função:** `baixar_nomenclatura_ncm`

**Quando usar:** Quando o usuário pedir para baixar ou atualizar a tabela de NCMs

**Exemplos de uso no chat:**
- "baixar nomenclatura NCM"
- "atualizar tabela NCM"
- "sincronizar NCM"
- "popular NCM"

**Parâmetros:**
- `forcar_atualizacao`: Se true, força atualização mesmo se já foi atualizada recentemente (padrão: false)

**O que faz:**
- Faz download do arquivo JSON oficial do Portal Único
- Popula a tabela `classif_cache` local

**⚠️ IMPORTANTE:** Esta operação pode levar vários minutos (o arquivo é grande). A tabela NCM raramente muda, então esta operação não precisa ser feita frequentemente (mensalmente é suficiente).

---

## 📧 Email

### Verificar Emails com Processos

**Função:** `verificar_emails_processos`

**Quando usar:** Quando o usuário pedir para verificar emails ou caixa de entrada

**Exemplos de uso no chat:**
- "verificar emails"
- "verificar email"
- "verificar caixa de entrada"
- "tem emails com processos?"
- "quais processos foram mencionados por email?"

**Parâmetros:**
- `limit`: Número máximo de emails para verificar (padrão: 10)
- `filter_read`: Se true, verifica apenas emails não lidos (padrão: false)
- `max_days`: Número máximo de dias para buscar emails (padrão: 7)

**O que faz:**
- Busca os emails mais recentes da caixa de entrada
- Identifica automaticamente quais mencionam números de processos
- Retorna lista dos processos encontrados e informações sobre os emails

**Padrão de Detecção de Processos:**
- Formato: `[CATEGORIA].[NUMERO]/[ANO]`
- Exemplos: `ALH.0001/25`, `MV5.0014/25`, `VDM.0030/25`
- Busca no assunto e corpo do email

---

### Ler Email

**Função:** `ler_email`

**Quando usar:** Quando o usuário pedir para ver, ler ou mostrar o conteúdo de um email específico

**Exemplos de uso no chat:**
- "ler email 2"
- "ver email 1"
- "mostrar email 3"
- "ler email com assunto Teste"

**Parâmetros:**
- `email_index`: Índice numérico do email na lista de emails com processos (começando em 1)
- `message_id`: ID da mensagem do email
- `email_subject`: Assunto do email para buscar (busca parcial)

**O que retorna:**
- Conteúdo completo do email formatado
- Informações: assunto, remetente, data/hora, se foi lido, processos mencionados
- Corpo do email processado (remove HTML, preserva formatação)

**Notas:**
- O índice se refere à lista de emails com processos mostrada por `verificar_emails_processos`
- O corpo do email é processado para remover tags HTML e melhorar a legibilidade
- Quebras de linha, listas e formatação são preservadas

---

### Responder Email

**Função:** `responder_email`

**Quando usar:** Quando o usuário pedir para responder um email

**Exemplos de uso no chat:**
- "responder email 2"
- "responder 1"
- "responder email 2 com: sua resposta aqui"
- "responder email [ID] com: sua resposta"

**Parâmetros:**
- `email_index`: Índice numérico do email (começando em 1)
- `message_id`: ID da mensagem do email
- `email_subject`: Assunto do email para buscar
- `resposta`: Conteúdo da resposta (opcional - se não fornecido, a IA gera automaticamente)
- `gerar_resposta_automatica`: Se true e resposta não fornecida, a IA gera resposta automaticamente (padrão: true)

**Funcionalidades:**
- **Geração automática de resposta:** Se você não fornecer o conteúdo da resposta, a IA analisa o email original e processos mencionados para gerar uma resposta profissional automaticamente
- **Resposta contextual:** A IA pode consultar informações sobre processos mencionados no email para gerar respostas mais informativas
- O email original é automaticamente incluído na resposta (padrão do Microsoft Graph)

**Notas:**
- O índice se refere à lista de emails com processos
- Se você fornecer o conteúdo da resposta, ele será usado diretamente
- Se não fornecer, a IA gerará uma resposta apropriada baseada no contexto do email

---

## 🏦 Santander Open Banking

### Listar Contas do Santander

**Função:** `listar_contas_santander`

**Quando usar:** Quando o usuário pedir para listar contas bancárias do Santander ou ver quais contas estão disponíveis

**Exemplos de uso no chat:**
- "listar contas do santander"
- "quais contas tenho no santander"
- "mostrar contas disponíveis"
- "contas do banco"

**Parâmetros:**
- Nenhum (função não requer parâmetros)

**O que retorna:**
- Lista de todas as contas disponíveis no Santander Open Banking vinculadas ao certificado digital
- Agência e número de conta de cada conta
- Código COMPE (033 para Santander)

**⚠️ IMPORTANTE:** Esta função lista todas as contas disponíveis. Se o usuário não especificar conta, o sistema usa automaticamente a primeira conta encontrada.

---

### Consultar Extrato do Santander

**Função:** `consultar_extrato_santander`

**Quando usar:** Quando o usuário pedir para ver extrato bancário, movimentações ou transações do Santander

**Exemplos de uso no chat:**
- "extrato do santander"
- "extrato dos últimos 7 dias"
- "extrato de janeiro"
- "movimentações da conta"
- "transações do banco"
- "extrato de hoje"
- "mostrar extrato da conta X"

**Parâmetros:**
- `agencia`: Código da agência (4 dígitos, ex: '3003') - opcional (usa primeira conta se não fornecido)
- `conta`: Número da conta (12 dígitos, ex: '000130827180') - opcional (usa primeira conta se não fornecido)
- `statement_id`: ID da conta no formato AGENCIA.CONTA (ex: '3003.000130827180') - opcional
- `data_inicio`: Data inicial no formato YYYY-MM-DD ou DD/MM/YYYY - opcional
- `data_fim`: Data final no formato YYYY-MM-DD ou DD/MM/YYYY - opcional
- `dias`: Número de dias para trás (ex: 7, 30) - opcional (padrão: 7 dias)

**O que retorna:**
- **Saldo Real da Conta**: Saldo disponível, bloqueado e investido automaticamente (consultado via API)
- **Movimentações do Período**: Créditos, débitos e saldo líquido calculados das transações
- **Lista de Transações**: Últimas 20 transações com data, descrição e valor
- **Totais**: Resumo de créditos, débitos e saldo líquido do período

**⚠️ IMPORTANTE:** 
- Se o usuário não fornecer agência/conta, o sistema lista automaticamente as contas e usa a primeira disponível
- Se não fornecer datas, usa últimos 7 dias como padrão
- O saldo real é consultado diretamente da API do Santander (não é calculado das transações)

---

### Consultar Saldo do Santander

**Função:** `consultar_saldo_santander`

**Quando usar:** Quando o usuário pedir para ver saldo da conta do Santander

**Exemplos de uso no chat:**
- "saldo do santander"
- "saldo da conta"
- "quanto tenho na conta"
- "saldo disponível"

**Parâmetros:**
- `agencia`: Código da agência (4 dígitos) - opcional (usa primeira conta se não fornecido)
- `conta`: Número da conta (12 dígitos) - opcional (usa primeira conta se não fornecido)
- `statement_id`: ID da conta no formato AGENCIA.CONTA - opcional

**O que retorna:**
- **Saldo Disponível**: Saldo disponível para uso
- **Saldo Bloqueado**: Saldo bloqueado (se houver)
- **Saldo Investido Automaticamente**: Saldo investido automaticamente (se houver)

**⚠️ IMPORTANTE:** 
- Se o usuário não fornecer agência/conta, o sistema lista automaticamente as contas e usa a primeira disponível
- O saldo é consultado diretamente da API do Santander (dados em tempo real)

---

## 🏦 Banco do Brasil (NOVO - 06/01/2026)

### Consultar Extrato do Banco do Brasil

**Função:** `consultar_extrato_bb`

**Quando usar:** Quando o usuário pedir para ver extrato bancário, movimentações ou transações do Banco do Brasil

**Exemplos de uso no chat:**
- "extrato bb" ou "extrato banco do brasil"
- "extrato bb de 30/12/25" - Extrato de um dia específico
- "extrato bb de 01/12/25 a 31/12/25" - Extrato de um período
- "extrato bb agência 1251 conta 50483" - Extrato com agência e conta específicas

**Parâmetros:**
- `agencia`: Número da agência sem dígito verificador (ex: "1251")
- `conta`: Número da conta sem dígito verificador (ex: "50483")
- `data_inicio`: Data inicial (formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave como "hoje")
- `data_fim`: Data final (formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave como "hoje")

**O que retorna:**
- **Total de transações**: Número total de transações no período
- **Movimentações do Período**:
  - Créditos: Total de créditos no período
  - Débitos: Total de débitos no período
  - Saldo líquido: Diferença entre créditos e débitos
- **Lista de Transações** (ordenadas da mais recente para a mais antiga):
  - Data do lançamento (DD/MM/YYYY)
  - Descrição do lançamento
  - Valor (com sinal + para crédito, - para débito)
  - Limite de 20 transações por página (mostra "... e mais N transações" se houver mais)

**⚠️ IMPORTANTE:** 
- Se o usuário não fornecer agência/conta, o sistema usa valores padrão do `.env` (`BB_TEST_AGENCIA` e `BB_TEST_CONTA`)
- Se não fornecer datas, retorna últimos 30 dias (padrão da API)
- Agência e conta são normalizadas automaticamente (zeros à esquerda removidos)
- Transações são ordenadas da mais recente para a mais antiga (do presente para o passado)
- Sistema detecta automaticamente pedidos de extrato BB antes da IA processar (precheck)

**Características especiais:**
- ✅ **Precheck Automático**: Detecta pedidos de extrato BB e chama a função diretamente
- ✅ **Normalização Automática**: Remove zeros à esquerda de agência/conta (conforme especificação API)
- ✅ **Valores Padrão**: Usa `BB_TEST_AGENCIA` e `BB_TEST_CONTA` do `.env` quando não fornecidos
- ✅ **Ordenação Inteligente**: Transações ordenadas da mais recente para a mais antiga
- ✅ **OAuth 2.0**: Autenticação mais simples que mTLS (não requer certificado para API de Extratos)

**Configuração necessária:**
- `BB_CLIENT_ID`: Client ID OAuth (JWT token)
- `BB_CLIENT_SECRET`: Client Secret OAuth (JWT token)
- `BB_DEV_APP_KEY`: Chave de acesso do aplicativo (gw-dev-app-key)
- `BB_ENVIRONMENT`: `production` ou `sandbox` (padrão: `sandbox`)
- `BB_TEST_AGENCIA`: (Opcional) Agência padrão para testes
- `BB_TEST_CONTA`: (Opcional) Conta padrão para testes

**Documentação completa:** `docs/INTEGRACAO_BANCO_BRASIL.md`

---

## 💰 Consultas Bilhetadas

### Listar Consultas Bilhetadas Pendentes

**Função:** `listar_consultas_bilhetadas_pendentes`

**Quando usar:** Quando o usuário perguntar sobre consultas pendentes ou quiser ver quais consultas precisam ser aprovadas

**Exemplos de uso no chat:**
- "quais consultas estão pendentes?"
- "mostrar consultas pendentes"
- "listar consultas de CE pendentes"

**Parâmetros:**
- `status`: Status das consultas (pendente, aprovado, rejeitado, executado) - padrão: pendente
- `tipo_consulta`: Tipo de consulta (CE, DI, Manifesto, Escala, CCT)
- `limite`: Número máximo de consultas (padrão: 50)

**O que retorna:** Detalhes de cada consulta (tipo, documento, processo, motivo, custo estimado)

**⚠️ IMPORTANTE:** Por padrão, mostra apenas consultas com status 'pendente'. Consultas já aprovadas, rejeitadas ou executadas NÃO aparecem nesta lista.

---

### Aprovar Consultas Bilhetadas

**Função:** `aprovar_consultas_bilhetadas`

**Quando usar:** Quando o usuário pedir para aprovar consultas ou autorizar consultas

**Exemplos de uso no chat:**
- "aprovar consulta 1"
- "aprovar todas as consultas de CE"
- "autorizar consultas pendentes"

**Parâmetros:**
- `ids`: Array de IDs das consultas (pode usar números da lista 1-100, função converte automaticamente)
- `tipo_consulta`: Tipo de consulta para aprovar todas (opcional)
- `aprovar_todas`: Se true, aprova todas as consultas pendentes (padrão: false)

**O que faz:**
- Aprova as consultas
- Tenta executá-las imediatamente

**⚠️ CUSTO:** Consultas aprovadas serão bilhetadas (R$ 0,942 por consulta).

**⚠️ CRÍTICO:** Quando o usuário diz "consulta X" e X é um número pequeno (1-100), SEMPRE use o número da lista mostrada, NÃO o ID real. A função converte automaticamente.

---

### Rejeitar Consultas Bilhetadas

**Função:** `rejeitar_consultas_bilhetadas`

**Quando usar:** Quando o usuário pedir para rejeitar consultas ou cancelar consultas

**Exemplos de uso no chat:**
- "rejeitar consulta 1"
- "rejeitar todas as consultas de DI"
- "cancelar consultas pendentes"

**Parâmetros:**
- `ids`: Array de IDs das consultas (pode usar números da lista 1-100, função converte automaticamente)
- `tipo_consulta`: Tipo de consulta para rejeitar todas (opcional)
- `rejeitar_todas`: Se true, rejeita todas as consultas pendentes (padrão: false)
- `motivo`: Motivo da rejeição (opcional)

**O que faz:**
- Rejeita as consultas
- Elas não serão executadas (economia de custo)

**⚠️ CRÍTICO:** Quando o usuário diz "consulta X" e X é um número pequeno (1-100), SEMPRE use o número da lista mostrada, NÃO o ID real. A função converte automaticamente.

---

### Ver Status de Consultas Bilhetadas

**Função:** `ver_status_consultas_bilhetadas`

**Quando usar:** Quando o usuário perguntar sobre o status de uma consulta específica ou quiser ver estatísticas gerais

**Exemplos de uso no chat:**
- "status da consulta 123"
- "como está a consulta 1?"
- "estatísticas de consultas"

**Parâmetros:**
- `consulta_id`: ID da consulta específica (opcional - se não fornecido, retorna estatísticas gerais)

---

### Listar Consultas Aprovadas Não Executadas

**Função:** `listar_consultas_aprovadas_nao_executadas`

**Quando usar:** Quando o usuário perguntar sobre consultas aprovadas que estão aguardando execução

**Exemplos de uso no chat:**
- "quais consultas foram aprovadas mas não executadas?"
- "mostrar consultas aprovadas"
- "listar consultas aprovadas de CE"

**Parâmetros:**
- `tipo_consulta`: Tipo de consulta (CE, DI, Manifesto, Escala, CCT)
- `limite`: Número máximo de consultas (padrão: 50)

---

### Executar Consultas Aprovadas

**Função:** `executar_consultas_aprovadas`

**Quando usar:** Quando o usuário pedir para executar consultas aprovadas ou processar consultas aprovadas

**Exemplos de uso no chat:**
- "executar consulta 1"
- "executar todas as consultas aprovadas de CE"
- "processar consultas aprovadas"

**Parâmetros:**
- `ids`: Array de IDs das consultas (pode usar números da lista 1-100, função converte automaticamente)
- `tipo_consulta`: Tipo de consulta para executar todas (opcional)
- `executar_todas`: Se true, executa todas as consultas aprovadas (padrão: false)

**O que faz:**
- Executa as consultas bilhetadas imediatamente

**⚠️ CUSTO:** Consultas executadas serão bilhetadas (R$ 0,942 por consulta).

**⚠️ CRÍTICO:** Quando o usuário diz "consulta X" e X é um número pequeno (1-100), SEMPRE use o número da lista mostrada, NÃO o ID real. A função converte automaticamente.

---

## 📊 Relatórios e Dashboards

### Dashboard do Dia

**Função:** `obter_dashboard_hoje`

**Quando usar:** Quando o usuário perguntar sobre o que temos para hoje

**Exemplos de uso no chat:**
- "o que temos pra hoje?"
- "o que temos para hoje?"
- "dashboard de hoje"
- "resumo do dia"
- "o que precisa ser feito hoje?"

**Parâmetros:**
- `categoria`: Filtro opcional por categoria (ex: ALH, VDM, GYM)
- `modal`: Filtro opcional por modal (Marítimo, Aéreo)
- `apenas_pendencias`: Se true, mostra apenas pendências (padrão: false)

**O que retorna:**
- Processos chegando hoje
- Processos prontos para registro DI/DUIMP
- Pendências ativas (ICMS, AFRMM, LPCO, bloqueios)
- DUIMPs em análise
- Processos com ETA alterado
- Alertas recentes
- Sugestões de ações priorizadas

**⚠️ CRÍTICO:** NUNCA USE esta função quando o usuário pedir para ENVIAR por email - use `enviar_relatorio_email` nesse caso.

---

### Enviar Relatório por Email

**Função:** `enviar_relatorio_email`

**Quando usar:** Quando o usuário pedir para ENVIAR, MANDAR ou ENVIAR POR EMAIL qualquer relatório

**Exemplos de uso no chat:**
- "envie o resumo do dia por email para email@exemplo.com"
- "envie o resumo ALH por email"
- "mandar o dashboard por email"

**Parâmetros:**
- `destinatarios`: Lista de emails dos destinatários (obrigatório)
- `tipo_relatorio`: Tipo de relatório (briefing_dia, dashboard_hoje, resumo_reuniao, fechamento_dia) - padrão: briefing_dia
- `categoria`: Filtro por categoria (opcional - só use se o usuário mencionar explicitamente)
- `modal`: Filtro por modal (Marítimo, Aéreo) - opcional
- `cc`: Lista de emails em cópia - opcional
- `bcc`: Lista de emails em cópia oculta - opcional
- `assunto_personalizado`: Assunto personalizado - opcional
- `confirmar_envio`: Se false, mostra preview e pede confirmação (padrão: false)

**FLUXO EM 2 ETAPAS OBRIGATÓRIO:**
1. **PRIMEIRA CHAMADA:** Sempre use `confirmar_envio=false` (ou omita). Isso mostra o preview do relatório completo no chat e pergunta se o usuário confirma o envio.
2. **SEGUNDA CHAMADA (SE CONFIRMADO):** Se o usuário responder "sim", "enviar", "confirma", etc., chame a função NOVAMENTE com os EXATAMENTE MESMOS parâmetros mas com `confirmar_envio=true`.

**⚠️ CRÍTICO SOBRE CATEGORIA:** Só passe a categoria se o usuário MENCIONAR EXPLICITAMENTE uma categoria na mensagem atual. Se não mencionar categoria, passe `categoria=None` (isso retorna todas as categorias, que é o comportamento esperado).

**⚠️ NUNCA pergunte ao usuário sobre categoria** - chame a função diretamente com os parâmetros que conseguir extrair da mensagem.

---

### Fechamento do Dia

**Função:** `fechar_dia`

**Quando usar:** Quando o usuário perguntar sobre fechamento do dia ou movimentações de hoje

**Exemplos de uso no chat:**
- "fechar o dia"
- "fechamento do dia"
- "o que movimentou hoje?"
- "quais movimentações tivemos hoje?"
- "fechar o dia ALH" (com categoria)

**Parâmetros:**
- `categoria`: Filtro por categoria (opcional - só use se o usuário mencionar explicitamente)
- `modal`: Filtro por modal (Marítimo, Aéreo) - opcional

**O que retorna:**
- Processos que chegaram hoje
- Processos desembaraçados hoje
- DUIMPs criadas hoje
- Mudanças de status CE/DI/DUIMP hoje

**⚠️ DIFERENÇA:** Esta função mostra o que JÁ ACONTECEU hoje (fechamento), enquanto o dashboard mostra o que TEMOS PRA HOJE (planejamento).

**⚠️ CRÍTICO:** Se o usuário digitar apenas "fechar o dia" SEM mencionar categoria, NÃO use categoria do contexto anterior. Deixe `categoria=None` para retornar movimentações de TODAS as categorias.

---

### Resumo de Reunião

**Função:** `gerar_resumo_reuniao`

**Quando usar:** Quando o usuário pedir para preparar resumo para reunião

**Exemplos de uso no chat:**
- "prepara resumo para reunião do cliente X"
- "resumo executivo para reunião"
- "prepara apresentação para cliente Y"
- "resumo para reunião da categoria Z"

**Parâmetros:**
- `categoria`: Categoria do cliente (ex: GYM, ALH, VDM)
- `periodo`: Período do resumo (hoje, semana, mes, periodo_especifico) - padrão: semana
- `data_inicio`: Data de início se periodo='periodo_especifico'
- `data_fim`: Data de fim se periodo='periodo_especifico'

**O que retorna:**
- Resumo Executivo
- Pontos de Atenção
- Próximos Passos

**⚠️ IMPORTANTE:** Esta função usa modo analítico (modelo mais forte) para gerar análises complexas e texto executivo.

---

### Gerar Relatório de Importações Normalizado por FOB

**Função:** `gerar_relatorio_importacoes_fob`

**Quando usar:** Quando o usuário perguntar sobre quanto foi importado em um mês/categoria, com valores normalizados para FOB

**Exemplos de uso no chat:**
- "quanto importou o dmd em dezembro?"
- "relatorio fob dmd dezembro"
- "quanto importou vdm em novembro em fob?"
- "relatorio importacoes fob dmd dezembro 2025"

**Parâmetros:**
- `mes`: Mês (1-12) - obrigatório
- `ano`: Ano (ex: 2025) - obrigatório
- `categoria`: Categoria do processo (DMD, VDM, etc.) - opcional

**O que faz:**
1. Busca processos desembaraçados no mês/ano especificado
2. Para DI: Normaliza valores para FOB usando VMLD - Frete - Seguro
3. Para DUIMP: Usa FOB direto (já está normalizado)
4. Considera INCOTERMs (FOB, CIF, CFR) para normalização correta
5. Gera relatório com valores em USD e BRL, incluindo porcentagem de frete sobre FOB

**⚠️ IMPORTANTE:**
- Valores são buscados diretamente do SQL Server (não do cache SQLite)
- Cache SQLite só contém processos ativos, relatório precisa de dados históricos
- Para DI: FOB = VMLD - Frete - Seguro (VMLD sempre inclui frete e seguro)
- Para DUIMP: FOB já está disponível diretamente no campo `valor_total_local_embarque`

**⚠️ PENDÊNCIA URGENTE (23/12/2025):**
- Valores de frete podem estar incorretos (ex: DMD.0090/25)
- Necessário validar query de frete quando há múltiplos registros (retificações)
- Conferir valores em dólar antes de conversão

---

### Gerar Relatório de Averbações

**Função:** `gerar_relatorio_averbacoes`

**Quando usar:** Quando o usuário perguntar sobre averbações de processos com DI registrada em um mês/categoria

**Exemplos de uso no chat:**
- "averbacao dmd dezembro"
- "relatorio averbacao dmd novembro"
- "averbacao vdm dezembro 2025"

**Parâmetros:**
- `mes`: Mês (1-12) - obrigatório
- `ano`: Ano (ex: 2025) - obrigatório
- `categoria`: Categoria do processo (DMD, VDM, etc.) - opcional

**O que faz:**
1. Busca processos com DI registrada no mês/ano especificado
2. Extrai dados completos de averbação (CE, DI, valores, impostos)
3. Gera arquivo Excel com todas as informações necessárias para averbação

**⚠️ IMPORTANTE:**
- Busca processos diretamente do SQL Server
- Prioridade de busca de dados: Cache → SQL Server → API (API é bilhetada)
- Inclui cálculos de despesas (10%) e lucros (10%)
- Conversão de impostos BRL→USD usando PTAX

**⚠️ PENDÊNCIA URGENTE (23/12/2025):**
- Query SQL não está encontrando processos corretamente para alguns meses/categorias
- Filtros de data podem estar incorretos
- Necessário validar se a query está alinhada com o relatório FOB que funciona

---

## 🎓 Aprendizado e Contexto

### Contexto de Processo (processo_atual)

O sistema mantém contexto persistente entre mensagens para facilitar a interação. Uma das funcionalidades mais importantes é o **contexto de processo atual** (`processo_atual`).

#### Como Funciona

O sistema salva automaticamente o processo mencionado quando você faz uma pergunta específica sobre ele. Nas mensagens seguintes, você pode fazer perguntas de follow-up sem precisar repetir o número do processo.

**Exemplos de uso:**
1. **Primeira mensagem:** "como está o processo ALH.0165/25?"
   - Sistema salva `processo_atual = "ALH.0165/25"`
   - Retorna informações completas do processo

2. **Follow-up (sem mencionar processo):** "e a DI?"
   - Sistema usa `processo_atual` automaticamente
   - Retorna informações da DI do processo ALH.0165/25

3. **Outro follow-up:** "e a DUIMP?"
   - Sistema continua usando o mesmo processo
   - Retorna informações da DUIMP do processo ALH.0165/25

#### Regras Importantes

⚠️ **NUNCA assume processo padrão fixo:**
- O sistema NUNCA assume um processo padrão (ex: "MV5.0009/25")
- `processo_atual` só é definido quando:
  - Você menciona um processo EXPLÍCITO na mensagem (ex: "ALH.0165/25")
  - OU o sistema salva explicitamente via contexto após uma consulta

⚠️ **Perguntas de Painel NÃO usam processo_atual:**
- Perguntas de visão geral como "como estão os MV5?" ou "o que temos pra hoje?" são **perguntas de painel**
- Essas perguntas NUNCA usam `processo_atual` do contexto
- Elas sempre retornam listas/visões gerais, não informações de um processo específico

**Exemplos de perguntas de painel:**
- "como estão os MV5?"
- "o que temos pra hoje?"
- "fechamento do dia"
- "quais processos chegam amanhã?"
- "painel de chegadas"

**Exemplos que NÃO são painel (usam processo_atual se disponível):**
- "e a DI?" (follow-up)
- "e a DUIMP?" (follow-up)
- "situação dele?" (follow-up)
- "como está esse processo?" (follow-up)

#### Follow-up de Processo

Follow-ups são perguntas curtas que dependem do contexto de `processo_atual`. O sistema detecta automaticamente quando você está fazendo um follow-up.

**Quando o sistema usa processo_atual em follow-up:**
- ✅ Tem `session_id` (sessão ativa)
- ✅ NÃO é pergunta de painel
- ✅ A mensagem NÃO tem processo explícito
- ✅ A mensagem NÃO menciona categoria explícita (MV5, VDM, ALH, etc.)
- ✅ A mensagem parece follow-up (ex: "e a DI?", "e a DUIMP?", "situação dele?")

**Exemplos de follow-ups que DEVEM usar contexto:**
- "e a DI?"
- "e a DUIMP?"
- "e o CE?"
- "e a CCT?"
- "e a DI, como está?"
- "situação dele?"
- "como está esse processo?"

**Exemplos que NÃO devem usar contexto:**
- "situacao vdm.0005/25" (novo processo explícito)
- "como estão os mv5?" (pergunta de painel)
- "o que temos pra hoje?" (pergunta de painel)
- "qual a ncm?" (pergunta de NCM, não follow-up)

#### Quando o Contexto é Salvo

O sistema salva `processo_atual` APENAS quando:
1. Você menciona um processo EXPLÍCITO na mensagem (ex: "ALH.0165/25")
2. A mensagem NÃO é pergunta de painel
3. A consulta é bem-sucedida

**Exemplo de fluxo:**
```
Usuário: "como está o processo ALH.0165/25?"
Sistema: [Consulta processo] → Salva processo_atual = "ALH.0165/25" → Retorna informações

Usuário: "e a DI?"
Sistema: [Usa processo_atual] → Retorna DI do ALH.0165/25

Usuário: "como estão os MV5?"
Sistema: [NÃO usa processo_atual - é painel] → Retorna lista de MV5
```

#### Limpar Contexto

Para limpar o contexto de processo:
- Inicie uma nova conversa/sessão
- Mencione um processo diferente (o sistema substitui automaticamente)
- Faça uma pergunta de painel (não usa contexto, mas não limpa)

---

### Obter Resumo de Aprendizado

**Função:** `obter_resumo_aprendizado`

**Quando usar:** Quando o usuário perguntar o que a mAIke aprendeu

**Exemplos de uso no chat:**
- "o que você aprendeu comigo?"
- "o que você aprendeu nesta sessão?"
- "resumo de aprendizado"

**Parâmetros:**
- `session_id`: ID da sessão (opcional - usa sessão atual se não fornecido)

**O que retorna:**
- Regras aprendidas na sessão
- Consultas salvas criadas na sessão

---

### Salvar Regra Aprendida

**Função:** `salvar_regra_aprendida`

**Quando usar:** Quando o usuário explicar como fazer algo, definir um campo, ou dar uma instrução que deve ser lembrada

**Exemplos de uso no chat:**
- "usar campo destfinal como confirmação de chegada"
- "quando eu disser X, você deve fazer Y"
- "sempre que mencionar Z, considere A"

**Parâmetros:**
- `tipo_regra`: Tipo da regra (ex: "campo_definicao", "regra_negocio", "preferencia_usuario") - obrigatório
- `contexto`: Contexto onde a regra se aplica (ex: "chegada_processos", "analise_vdm", "filtros_gerais") - obrigatório
- `nome_regra`: Nome amigável da regra (ex: "destfinal como confirmação de chegada") - obrigatório
- `descricao`: Descrição completa da regra - obrigatório
- `aplicacao_sql`: Como aplicar em SQL (ex: "WHERE data_destino_final IS NOT NULL") - opcional
- `aplicacao_texto`: Como aplicar em texto/linguagem natural - opcional
- `exemplo_uso`: Exemplo de quando usar essa regra - opcional

**O que faz:**
- Salva a regra na tabela `regras_aprendidas`
- A regra será incluída no prompt nas próximas mensagens relevantes
- A IA aplica automaticamente a regra quando fizer sentido

---

### Listar Categorias Disponíveis

**Função:** `listar_categorias_disponiveis`

**Quando usar:** Quando o usuário perguntar quais categorias estão disponíveis

**Exemplos de uso no chat:**
- "quais categorias temos?"
- "quais categorias estão disponíveis?"
- "listar categorias"

**O que retorna:** Todas as categorias cadastradas no banco de dados, incluindo categorias confirmadas pelo usuário e categorias detectadas automaticamente

---

### Adicionar Categoria de Processo

**Função:** `adicionar_categoria_processo`

**Quando usar:** APENAS quando o usuário CONFIRMAR explicitamente que uma categoria é válida

**Exemplos de uso no chat:**
- Usado quando o usuário responde "sim" ou "é" quando perguntado se algo é categoria

**Parâmetros:**
- `categoria`: Categoria de processo a adicionar (ex: MV5, ALH, VDM) - deve ter 2-4 caracteres

**⚠️ IMPORTANTE:** Esta função deve ser usada APENAS quando o usuário confirmar que uma categoria desconhecida é realmente uma categoria de processo. NÃO use para adicionar categorias sem confirmação do usuário.

---

### Obter Relatório de Observabilidade

**Função:** `obter_relatorio_observabilidade`

**Quando usar:** Quando o usuário perguntar sobre uso do sistema ou custos

**Exemplos de uso no chat:**
- "relatório de uso"
- "quanto custou?"
- "quais consultas são mais usadas?"
- "relatório de custos"

**Parâmetros:**
- `data_inicio`: Data de início (YYYY-MM-DD) ou None para últimos 30 dias
- `data_fim`: Data de fim (YYYY-MM-DD) ou None para hoje

**O que retorna:**
- Estatísticas de uso
- Custos de consultas bilhetadas
- Identificação de consultas/regras não utilizadas

---

### Verificar Fontes de Dados

**Função:** `verificar_fontes_dados`

**Quando usar:** Quando o usuário perguntar sobre disponibilidade de dados ou conexão

**Exemplos de uso no chat:**
- "quais fontes de dados estão disponíveis?"
- "verificar fontes de dados"
- "estou conectado ao SQL Server?"

**O que retorna:** Status de cada fonte de dados:
- SQLite (Local/Offline) - sempre disponível se o arquivo `chat_ia.db` existir
- SQL Server (Rede do Escritório) - disponível apenas quando conectado à rede
- API Kanban - dados atualizados em tempo real
- API Portal Único - dados de DUIMP, DI em tempo real

---

## 📊 Consultas Analíticas SQL

### Executar Consulta Analítica

**Função:** `executar_consulta_analitica`

**Quando usar:** Quando o usuário pedir análises, rankings, agregações ou relatórios que precisem de SQL

**Exemplos de uso no chat:**
- "quais clientes têm mais processos em atraso?"
- "mostre ranking de processos por categoria"
- "quantos processos temos por situação?"

**Parâmetros:**
- `sql`: Query SQL a executar (deve ser SELECT) - obrigatório
- `limit`: Limite de resultados (opcional, padrão: 100, máximo: 1000)

**O que faz:**
- Valida que a query é SELECT (somente leitura)
- Executa a query de forma segura
- Retorna resultados formatados

**⚠️ SEGURANÇA:** Apenas queries SELECT são permitidas. Queries de escrita (INSERT, UPDATE, DELETE) são bloqueadas.

---

### Salvar Consulta Personalizada

**Função:** `salvar_consulta_personalizada`

**Quando usar:** Quando o usuário pedir para salvar uma consulta que funcionou bem

**Exemplos de uso no chat:**
- "salva essa consulta como Atrasos críticos por cliente"
- "guarda essa query como relatório de processos"

**Parâmetros:**
- `nome_exibicao`: Nome amigável do relatório (ex: "Atrasos críticos por cliente no ano") - obrigatório
- `slug`: Identificador único em snake_case (ex: "atrasos_criticos_cliente_ano") - obrigatório
- `descricao`: Descrição do que o relatório faz - obrigatório
- `sql`: Query SQL da consulta - obrigatório
- `parametros`: Lista de parâmetros esperados (opcional) - ex: [{'nome': 'ano', 'tipo': 'int'}]
- `exemplos_pergunta`: Exemplos de como pedir (opcional)

**O que faz:**
- Salva a consulta como relatório reutilizável na tabela `consultas_salvas`
- Permite que o usuário execute a consulta novamente usando o nome amigável

---

### Buscar Consulta Personalizada

**Função:** `buscar_consulta_personalizada`

**Quando usar:** Quando o usuário pedir para "rodar aquele relatório" ou mencionar um relatório salvo anteriormente

**Exemplos de uso no chat:**
- "Roda aquele relatório de atrasos críticos por cliente em 2025"
- "executa o relatório de processos por categoria"

**Parâmetros:**
- `texto_pedido_usuario`: Texto da pergunta do usuário - obrigatório

**O que faz:**
- Busca consultas salvas que correspondem ao pedido do usuário
- Executa a consulta salva com os parâmetros fornecidos

---

## 🔧 Configurações e Observabilidade

### Obter Ajuda

**Função:** `obter_ajuda`

**Quando usar:** Quando o usuário pedir ajuda ou quiser ver um guia de funcionalidades

**Exemplos de uso no chat:**
- "ajuda"
- "help"
- "como usar"
- "o que posso fazer"
- "quais comandos"
- "guia"
- "manual"

**O que retorna:** Guia completo formatado em markdown com todas as palavras-chave principais e exemplos de uso

---

## 🔗 Desvinculação de Documentos

### Desvincular Documento de Processo

**Função:** `desvincular_documento_processo`

**Quando usar:** Quando o usuário pedir para desvincular, remover ou deletar um documento de um processo

**Exemplos de uso no chat:**
- "desvincule o CE 132505317461600 do DMD.0068/25"
- "remova o CE do processo X"
- "desvincule a DI do processo Y"
- "delete essa vinculação"

**Parâmetros:**
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA (obrigatório)
- `tipo_documento`: Tipo do documento (CE, CCT, DI, DUIMP, RODOVIARIO) (obrigatório)
- `numero_documento`: Número do documento (obrigatório)

**⚠️ DIFERENÇA CRÍTICA:** 
- Se o usuário diz "desvincule" ou "remova" → use esta função
- Se o usuário diz "vincule" ou "associe" → use as funções de vinculação correspondentes

**⚠️ IMPORTANTE:** Cada processo deve ter apenas um CE e um CCT. Esta função é essencial para corrigir erros de vinculação.

---

### Obter Valores de Processo

**Função:** `obter_valores_processo`

**Quando usar:** Quando o usuário perguntar sobre valores monetários de um processo

**Exemplos de uso no chat:**
- "qual o valor do frete do processo ALH.0145/25?"
- "quanto é o frete do processo X?"
- "qual o valor FOB do processo Y?"
- "qual o CIF do processo W?"

**Parâmetros:**
- `processo_referencia`: Número do processo no formato XXX.NNNN/AA (obrigatório)
- `tipo_valor`: Tipo de valor (frete, seguro, fob, cif, todos) - padrão: todos

**O que retorna:** Valores encontrados no CE vinculado ao processo, incluindo frete, seguro, FOB, CIF e suas respectivas moedas

---

### Obter Valores de CE

**Função:** `obter_valores_ce`

**Quando usar:** Quando o usuário perguntar sobre valores de um CE específico

**Exemplos de uso no chat:**
- "quanto é o frete do CE 132505284200462?"
- "qual o valor do frete do CE X?"
- "qual a moeda do frete do CE Y?"

**Parâmetros:**
- `numero_ce`: Número do CE (15 dígitos) (obrigatório)
- `tipo_valor`: Tipo de valor (frete, seguro, fob, cif, todos) - padrão: todos

**O que retorna:** Valores encontrados no CE, incluindo frete, seguro, FOB, CIF e suas respectivas moedas

---

## 📋 Exemplos de Uso Prático

### Cenário 1: Consulta de Processo

**Usuário:** "como está o processo ALH.0165/25?"

**O que acontece:**
1. Sistema detecta número de processo específico
2. Chama `consultar_status_processo`
3. Retorna informações completas: CEs, DIs, DUIMPs, pendências, valores, etc.

---

### Cenário 2: Criar DUIMP

**Usuário:** "crie duimp para VDM.0003/25"

**O que acontece:**
1. Sistema detecta comando de criação de DUIMP
2. Chama `criar_duimp` com processo_referencia='VDM.0003/25'
3. Busca dados do processo e CE/CCT vinculado
4. Cria DUIMP no Portal Único (ambiente validação)
5. Vincula ao processo no banco
6. Retorna número e versão da DUIMP criada

---

### Cenário 3: Listar Processos de Categoria

**Usuário:** "como estão os processos ALH?"

**O que acontece:**
1. Sistema detecta categoria ALH
2. Chama `listar_processos_por_categoria` com categoria='ALH'
3. Retorna lista de processos ALH com situação de DI/DUIMP/CE

---

### Cenário 4: Dashboard do Dia

**Usuário:** "o que temos pra hoje?"

**O que acontece:**
1. Sistema detecta pergunta sobre "hoje"
2. Chama `obter_dashboard_hoje`
3. Retorna resumo consolidado: chegadas, prontos para registro, pendências, alertas, ações sugeridas

---

### Cenário 5: Enviar Resumo por Email

**Usuário:** "envie o resumo do dia por email para helenomaffra@gmail.com"

**O que acontece:**
1. Sistema detecta pedido de envio por email
2. Chama `enviar_relatorio_email` com `confirmar_envio=false`
3. Mostra preview do relatório no chat
4. Pergunta se o usuário confirma o envio
5. Se usuário responder "sim", chama novamente com `confirmar_envio=true`
6. Envia email formatado via Microsoft Graph API

---

### Cenário 6: Verificar Emails e Responder

**Usuário:** "verificar emails"

**O que acontece:**
1. Sistema chama `verificar_emails_processos`
2. Busca emails recentes
3. Identifica processos mencionados nos emails
4. Retorna lista de emails com processos encontrados

**Usuário:** "ler email 2"

**O que acontece:**
1. Sistema chama `ler_email` com email_index=2
2. Busca email da lista (índice 2)
3. Retorna conteúdo completo formatado

**Usuário:** "responder email 2"

**O que acontece:**
1. Sistema chama `responder_email` com email_index=2 (sem resposta fornecida)
2. Busca email da lista
3. IA analisa email original e processos mencionados
4. Gera resposta profissional automaticamente
5. Envia resposta via Microsoft Graph API

---

### Cenário 7: Consulta de NCM com IA

**Usuário:** "qual o ncm de alho?"

**O que acontece:**
1. Sistema chama `sugerir_ncm_com_ia` com descricao='alho'
2. IA analisa descrição usando RAG com cache local
3. Sugere NCM mais adequado (ex: 0703.20.00)
4. Valida se NCM existe no cache
5. Retorna sugestão com alternativas similares se necessário

---

### Cenário 8: Follow-up de Processo usando Contexto

**Usuário:** "como está o processo ALH.0165/25?"

**O que acontece:**
1. Sistema detecta número de processo específico
2. Chama `consultar_status_processo` com processo_referencia='ALH.0165/25'
3. Salva `processo_atual = "ALH.0165/25"` no contexto da sessão
4. Retorna informações completas: CEs, DIs, DUIMPs, pendências, valores, etc.

**Usuário:** "e a DI?"

**O que acontece:**
1. Sistema detecta que é follow-up (mensagem curta, menciona documento, não menciona processo)
2. Sistema verifica que NÃO é pergunta de painel
3. Sistema usa `processo_atual = "ALH.0165/25"` do contexto
4. Chama função apropriada para consultar DI do processo ALH.0165/25
5. Retorna informações da DI sem precisar mencionar o processo novamente

**Usuário:** "como estão os MV5?"

**O que acontece:**
1. Sistema detecta que é pergunta de painel (visão geral de categoria)
2. Sistema NÃO usa `processo_atual` (perguntas de painel nunca usam contexto)
3. Chama `listar_processos_por_categoria` com categoria='MV5'
4. Retorna lista de processos MV5 (não informações de um processo específico)

---

## 🌐 APIs Externas Utilizadas

### Integra Comex (SERPRO)

**Função:** Consulta de CE e DI  
**Custo:** BILHETADA (R$ 0,942 por consulta)  
**Autenticação:** OAuth2 + mTLS (certificado PKCS#12)  
**Limitação:** Verificação de duplicata (não consulta mesmo CE/DI nos últimos 5 minutos)

**Estratégia de Uso:**
- Sempre consulta API pública (gratuita) antes de bilhetar
- Só bilheta se houver alterações ou não estiver no cache
- Usa cache local para evitar bilhetes desnecessários

---

### Portal Único Siscomex

**Função:** Criação/consulta de DUIMP, consulta de CCT  
**Custo:** Gratuita (mas requer certificado válido)  
**Autenticação:** mTLS + CSRF Token (certificado PKCS#12)

**Ambientes:**
- **Validação:** `https://val.portalunico.siscomex.gov.br` (padrão)
- **Produção:** `https://portalunico.siscomex.gov.br` (requer `DUIMP_ALLOW_WRITE_PROD=1`)

**Ajuste Automático de CE:**
- **Validação:** CE ajustado (últimos 2 dígitos → "02")
- **Produção:** CE completo (15 dígitos) sem alteração

---

### Microsoft Graph API

**Função:** Envio e recebimento de emails (Outlook/Office 365)  
**Custo:** Gratuita (requer credenciais Azure AD)  
**Autenticação:** OAuth2 Client Credentials (Tenant ID, Client ID, Client Secret)

**Permissões Necessárias:**
- `Mail.Read` ou `Mail.ReadWrite` (para leitura)
- `Mail.Send` (para envio)

**Endpoints Utilizados:**
- `GET /users/{mailbox}/messages` - Listar emails
- `POST /users/{mailbox}/messages/{message-id}/reply` - Responder email
- `POST /users/{mailbox}/sendMail` - Enviar email

---

### API Kanban

**Função:** Consulta de processos de importação  
**Custo:** Nenhum (API interna)  
**Configuração:** IP fixo (172.16.10.211:5000)  
**Limitação:** Apenas acessível na rede interna da empresa

---

## 🏗️ Arquitetura e Serviços

### Agents (Agentes)

O sistema usa uma arquitetura baseada em agents, onde cada agent é responsável por um domínio específico:

- **ProcessoAgent**: Processos, dashboards, relatórios, emails
- **DuimpAgent**: Criação, consulta e gestão de DUIMPs
- **CeAgent**: Consultas e extratos de CEs
- **CctAgent**: Consultas e extratos de CCTs
- **DiAgent**: Consultas e extratos de DIs

### Serviços Principais

- **ChatService**: Lógica principal de processamento de mensagens
- **PrecheckService**: Orquestra prechecks determinísticos antes de chamar a IA
  - **EmailPrecheckService**: Prechecks especializados em comandos de email
  - **ProcessoPrecheckService**: Prechecks especializados em consultas de processo (situação, follow-up)
  - **NcmPrecheckService**: Prechecks especializados em consultas de NCM (TECwin, perguntas)
- **EmailService**: Envio e recebimento de emails via Microsoft Graph
- **NCMService**: Busca e sugestão de NCMs
- **ConsultaService**: Consultas bilhetadas (aprovação, execução)
- **ContextService**: Gerenciamento de contexto persistente (processo_atual, categoria_atual, etc.)
- **LearnedRulesService**: Aprendizado de regras personalizadas
- **ObservabilityService**: Relatórios de uso e custos

### Fontes de Dados

- **SQLite (chat_ia.db)**: Cache local, processos recentes, configurações
- **SQL Server**: Processos históricos/antigos (quando conectado à rede)
- **API Kanban**: Processos ativos em tempo real
- **API Portal Único**: Dados de DUIMP, DI, CCT
- **API Integra Comex**: Dados de CE, DI (bilhetada)

---

## ⚠️ Regras e Boas Práticas

### Quando Consultar API Bilhetada

✅ **CONSULTE quando:**
- Usuário pedir explicitamente para "consultar"
- Dados não estão no cache
- Há alterações detectadas pela API pública

❌ **NÃO CONSULTE quando:**
- Dados estão no cache e API pública indica que não há alterações
- Usuário só quer saber situação/status (use `listar_processos_com_situacao_ce` que usa cache)

### Uso de Categoria

⚠️ **CRÍTICO:** Só use categoria se o usuário MENCIONAR EXPLICITAMENTE na mensagem atual. NÃO extraia categoria do histórico de mensagens anteriores.

**Exemplos corretos:**
- "envie o resumo do dia por email" → `categoria=None`
- "envie o resumo ALH por email" → `categoria='ALH'`

### Processos Prontos para Registro vs Registrados

- **"PRONTO PARA REGISTRO"**: Processos que chegaram mas AINDA NÃO têm DI/DUIMP → use `listar_processos_liberados_registro`
- **"REGISTRADO"**: Processos que JÁ têm DI/DUIMP → use `listar_processos_por_situacao` com `situacao='registrado'`

### Pendências vs Bloqueios

- **PENDÊNCIAS**: Valores não pagos (frete, AFRMM) → use `listar_processos_com_pendencias`
- **BLOQUEIOS**: Bloqueios físicos/administrativos da carga → use `listar_todos_processos_por_situacao` com `filtro_bloqueio=True`

### Envio de Email

⚠️ **FLUXO EM 2 ETAPAS OBRIGATÓRIO:**
1. Primeira chamada: `confirmar_envio=false` → mostra preview
2. Segunda chamada (se confirmado): `confirmar_envio=true` → envia email

NUNCA defina `confirmar_envio=true` na primeira chamada.

---

## 📝 Notas Finais

Este manual documenta todas as funcionalidades disponíveis no Chat IA Independente. O sistema foi projetado para ser intuitivo e usar linguagem natural, então você pode fazer perguntas de diversas formas e o sistema entenderá sua intenção.

Para ajuda rápida, digite "ajuda" ou "help" no chat para ver um guia resumido de funcionalidades.

---

## 📱 Endpoints da API

### Endpoints Principais

- `POST /api/chat` - Endpoint principal para chat com IA
- `GET /api/config` - Retorna configurações do sistema
- `GET /api/config/email` - Obtém configurações de email
- `POST /api/config/email` - Salva configurações de email
- `GET /api/email/check` - Verifica emails e identifica processos
- `GET /api/notificacoes` - Busca notificações do sistema
- `POST /api/notificacoes/<id>/marcar-lida` - Marca notificação como lida
- `GET /api/download/<filename>` - Download de arquivos (PDFs)
- `GET /health` - Health check

Para documentação completa dos endpoints, consulte `docs/API_DOCUMENTATION.md`.

---

## 🎯 Resumo de Todas as Funções Disponíveis

### Processos (15 funções)
1. `consultar_status_processo` - Consulta status detalhado de um processo
2. `consultar_averbacao_processo` - Dados de averbação de um processo
3. `consultar_processo_consolidado` - JSON consolidado completo
4. `listar_processos` - Lista geral de processos
5. `listar_processos_por_categoria` - Lista por categoria
6. `listar_processos_por_situacao` - Lista por situação (com categoria)
7. `listar_todos_processos_por_situacao` - Lista por situação (todas categorias)
8. `listar_processos_com_pendencias` - Lista processos com pendências
9. `listar_processos_por_eta` - Lista por ETA/período
10. `listar_processos_por_navio` - Lista por navio
11. `listar_processos_em_dta` - Lista processos em DTA
12. `listar_processos_liberados_registro` - Processos que chegaram sem despacho
13. `listar_processos_registrados_hoje` - Processos registrados hoje
14. `listar_processos_com_duimp` - Processos com DUIMP registrada
15. `obter_valores_processo` - Valores monetários de um processo

### DUIMP (5 funções)
16. `criar_duimp` - Cria uma DUIMP para um processo
17. `verificar_duimp_registrada` - Verifica se existe DUIMP para um processo
18. `obter_dados_duimp` - Informações detalhadas de uma DUIMP
19. `obter_extrato_pdf_duimp` - Extrato completo da DUIMP
20. `vincular_processo_duimp` - Vincula DUIMP/DI a um processo

### CE - Conhecimento de Embarque (4 funções)
21. `consultar_ce_maritimo` - Consulta um CE marítimo
22. `verificar_atualizacao_ce` - Verifica se CE precisa ser atualizado
23. `listar_processos_com_situacao_ce` - Lista processos com situação de CE (cache)
24. `obter_extrato_ce` - Extrato completo do CE

### CCT - Conhecimento de Carga Aérea (3 funções)
25. `consultar_cct` - Consulta um CCT
26. `obter_extrato_cct` - Extrato completo do CCT
27. `vincular_processo_cct` - Vincula CCT a um processo

### DI - Declaração de Importação (3 funções)
28. `obter_dados_di` - Informações detalhadas de uma DI
29. `obter_extrato_pdf_di` - Extrato PDF da DI
30. `vincular_processo_di` - Vincula DI a um processo

### NCM e NESH (5 funções)
31. `buscar_ncms_por_descricao` - Busca NCMs por descrição
32. `sugerir_ncm_com_ia` - Sugere NCM usando IA
33. `detalhar_ncm` - Detalha hierarquia completa de um NCM
34. `buscar_nota_explicativa_nesh` - Busca notas explicativas NESH
35. `baixar_nomenclatura_ncm` - Baixa e atualiza tabela de NCMs

### Email (3 funções)
36. `verificar_emails_processos` - Verifica emails e identifica processos
37. `ler_email` - Lê conteúdo completo de um email
38. `responder_email` - Responde um email (com geração automática pela IA)

### Consultas Bilhetadas (6 funções)
39. `listar_consultas_bilhetadas_pendentes` - Lista consultas pendentes
40. `aprovar_consultas_bilhetadas` - Aprova consultas para execução
41. `rejeitar_consultas_bilhetadas` - Rejeita consultas
42. `ver_status_consultas_bilhetadas` - Verifica status de consultas
43. `listar_consultas_aprovadas_nao_executadas` - Lista consultas aprovadas
44. `executar_consultas_aprovadas` - Executa consultas aprovadas

### Relatórios e Dashboards (4 funções)
45. `obter_dashboard_hoje` - Dashboard consolidado do dia
46. `enviar_relatorio_email` - Envia relatório por email
47. `fechar_dia` - Fechamento do dia (movimentações)
48. `gerar_resumo_reuniao` - Resumo executivo para reunião

### Aprendizado e Contexto (4 funções)
49. `obter_resumo_aprendizado` - Resumo do que foi aprendido
50. `listar_categorias_disponiveis` - Lista categorias disponíveis
51. `adicionar_categoria_processo` - Adiciona nova categoria
52. `obter_relatorio_observabilidade` - Relatório de uso e custos

### Outros (4 funções)
53. `desvincular_documento_processo` - Desvincula documento de processo
54. `obter_valores_ce` - Valores monetários de um CE
55. `obter_ajuda` - Guia de ajuda completo
56. `verificar_fontes_dados` - Verifica fontes de dados disponíveis
57. `executar_consulta_analitica` - Executa consulta SQL analítica
58. `salvar_consulta_personalizada` - Salva consulta como relatório reutilizável
59. `buscar_consulta_personalizada` - Busca e executa consulta salva
60. `salvar_regra_aprendida` - Salva regra ou definição aprendida do usuário

**Total: 62 funções disponíveis**

---

## 📖 Glossário de Termos Técnicos

### Processos de Importação

- **Processo de Importação**: Identificado por formato `CATEGORIA.NUMERO/ANO` (ex: ALH.0001/25)
- **Categoria**: Prefixo do processo (ALH, VDM, MSS, MV5, GYM, BND, DMD, etc.)
- **ETA**: Estimated Time of Arrival - Previsão de chegada
- **DTA**: Declaração de Trânsito Aduaneiro - Processos em trânsito para outro recinto

### Documentos

- **DUIMP**: Declaração Única de Importação - Formato: 25BR00001928777
- **DI**: Declaração de Importação - Formato: número sem barras (ex: 2524635120)
- **CE**: Conhecimento de Embarque (marítimo) - 15 dígitos (ex: 132505317461600)
- **CCT**: Conhecimento de Carga Aérea - Formato variável (ex: CWL25100012)

### Situações e Status

- **Desembaraçado/Desembaracado**: DI/DUIMP foi desembaraçada
- **Registrado**: Processo tem DI ou DUIMP registrada
- **Entregue**: Carga foi entregue ao destinatário
- **Armazenada**: Carga está armazenada no recinto
- **Pendências**: Valores não pagos (frete, AFRMM, ICMS)
- **Bloqueios**: Bloqueios físicos/administrativos da carga

### APIs e Custos

- **API Bilhetada**: API paga por consulta (R$ 0,942 por consulta - Integra Comex)
- **API Pública**: API gratuita (usada para verificar alterações antes de bilhetar)
- **Cache**: Armazenamento local para evitar consultas desnecessárias

---

## 🎯 Dicas de Uso

### Como Formular Perguntas

✅ **Bom:**
- "como está o processo ALH.0165/25?"
- "quais processos ALH têm pendência?"
- "envie o resumo do dia por email para helenomaffra@gmail.com"

❌ **Evite:**
- Perguntas muito genéricas sem contexto
- Múltiplas perguntas em uma única mensagem (faça uma de cada vez)

### Economizando Custos de API Bilhetada

- Use funções que consultam apenas cache quando possível
- O sistema automaticamente consulta API pública antes de bilhetar
- Funções como `listar_processos_com_situacao_ce` usam apenas cache (sem custo)

### Trabalhando com Contexto

O sistema mantém contexto persistente entre mensagens para facilitar a interação. Veja a seção [Contexto de Processo (processo_atual)](#contexto-de-processo-processo_atual) acima para entender as regras detalhadas.

**Resumo rápido:**
- ✅ Se você mencionar um processo específico, pode fazer follow-ups sem repetir o número
- ✅ Exemplos de follow-up: "e a DI?", "e a DUIMP?", "situação dele?"
- ❌ Perguntas de painel (ex: "como estão os MV5?") NÃO usam contexto de processo
- ❌ O sistema NUNCA assume um processo padrão fixo

**Para limpar contexto:**
- Inicie uma nova conversa/sessão
- Mencione um processo diferente (substitui automaticamente)

---

**Última atualização:** 06/01/2026  
**Versão do Sistema:** 1.7  
**Manual criado com base na análise completa do código fonte**

---

## 🚨 PENDÊNCIAS URGENTES - PRÓXIMA SEÇÃO

### ⚠️ Revisão e Validação de Relatórios (23/12/2025)

**Status:** 🔴 **URGENTE** - Requer revisão completa e validação de dados

#### 1. Relatório de Averbações (`gerar_relatorio_averbacoes`)

**Problemas identificados:**
- ⚠️ Query SQL não está encontrando processos corretamente para alguns meses/categorias
- ⚠️ Filtros de data podem estar incorretos (dataHoraDesembaraco vs dataHoraSituacaoDi vs dataHoraRegistro)
- ⚠️ Necessário validar se a query está alinhada com o relatório FOB que funciona

**O que revisar:**
- ✅ Query `_buscar_processos_com_di_no_mes` em `services/relatorio_averbacoes_service.py`
- ✅ Validação de filtros de data (prioridade: dataHoraDesembaraco → dataHoraSituacaoDi → dataHoraRegistro)
- ✅ Testes com diferentes meses e categorias (DMD, VDM, etc.)
- ✅ Comparação com query do relatório FOB que funciona corretamente

#### 2. Relatório FOB (`gerar_relatorio_importacoes_fob`)

**Problemas identificados:**
- ⚠️ Valores de frete podem estar incorretos (ex: DMD.0090/25 mostra USD 3,000.00 mas deveria ser USD 4,500.00)
- ⚠️ Query de frete pode estar pegando valor errado quando há múltiplos registros (retificações)
- ⚠️ Necessário validar valores em dólar antes de conversão (taxa de câmbio pode estar incorreta)

**O que revisar:**
- ✅ Query de frete da DI (subquery correlacionada pode estar pegando registro errado)
- ✅ Validação de valores em USD vs BRL (conferir taxa de câmbio implícita)
- ✅ Lógica de seleção de frete quando há múltiplos registros (usar `valorFreteBasico` do CE?)
- ✅ Testes com processos específicos (ex: DMD.0090/25) para validar valores

**Notas importantes:**
- O usuário reportou que o frete correto para DMD.0090/25 é USD 4,500.00 (não USD 3,000.00)
- Taxa de câmbio oficial na época era R$ 5.5283 por USD
- Valores devem ser conferidos primeiro em dólar, depois na conversão
- O CE tem `valorFreteTotal` e `valorFreteBasico` - verificar qual deve ser usado para DI

---

## 🔄 Changelog

### Versão 1.6.1 (23/12/2025)
- ✅ Adicionadas funções `gerar_relatorio_importacoes_fob` e `gerar_relatorio_averbacoes`
- ✅ Documentação completa dos novos relatórios na seção "Relatórios e Dashboards"
- ✅ Adicionada seção de pendências urgentes para revisão e validação dos relatórios
- ✅ Integração via `MessageIntentService` para detecção automática de intenções

### Versão 1.6 (19/12/2025)
- ✅ Adicionada seção detalhada sobre **Contexto de Processo (processo_atual)**
- ✅ Documentadas regras sobre **Follow-up de Processo**
- ✅ Documentadas regras sobre **Perguntas de Painel**
- ✅ Esclarecidas regras sobre quando o contexto é salvo e usado
- ✅ Atualizada seção "Trabalhando com Contexto" com informações mais precisas

### Versão 1.5 (17/12/2025)
- Documentação inicial completa do sistema
