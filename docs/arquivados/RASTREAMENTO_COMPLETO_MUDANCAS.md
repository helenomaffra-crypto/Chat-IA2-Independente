# 📋 RASTREAMENTO COMPLETO DE MUDANÇAS

**Data:** 18/12/2025  
**Objetivo:** Documentar TODAS as mudanças implementadas na conversa para não perder trabalho

---

## ✅ 1. MESSAGE INTENT SERVICE (Migração de Regex para Serviço Centralizado)

### Arquivo: `services/message_intent_service.py`

**Status:** ✅ Implementado e migrado do `chat_service.py`

**Funcionalidades:**
- ✅ `detectar_comando_limpar_contexto()` - Detecta comandos para limpar contexto
- ✅ `detectar_pergunta_ncm_produto()` - Detecta perguntas sobre NCM e extrai produto
- ✅ `detectar_pergunta_pronto_registro()` - Detecta perguntas sobre processos prontos para registro
- ✅ `detectar_intencao_averbacao()` - Detecta intenção de averbação
- ✅ `detectar_intencao_criar_duimp()` - Detecta intenção de criar DUIMP
- ✅ `verificar_tool_calls_incorretos()` - Verifica e corrige tool calls incorretos da IA
- ✅ `aplicar_correcoes_tool_calls()` - Aplica correções aos tool calls
- ✅ `detectar_pergunta_consultas_pendentes()` - Detecta perguntas sobre consultas bilhetadas
- ✅ `detectar_pergunta_valores()` - Detecta perguntas sobre valores (frete, seguro, FOB, CIF)
- ✅ `detectar_categoria_e_situacao()` - Detecta categoria e situação na mensagem
- ✅ `detectar_pergunta_pendencias()` - Detecta perguntas sobre pendências

**Nota:** Este serviço ainda usa regex, mas centraliza a lógica de detecção de intenções que antes estava espalhada no `chat_service.py`.

---

## ✅ 2. CORREÇÕES DE ETA (Cálculo de Datas)

### Arquivo: `db_manager.py` - Função `listar_processos_por_eta()`

**Status:** ✅ Corrigido

**Correções Implementadas:**

1. **Semana no Brasil começa no DOMINGO (ABNT):**
   - ✅ Semana = Domingo até Sábado
   - ✅ "esta semana" = de hoje (domingo) até sábado que vem
   - ✅ FUTURO: ETA >= hoje (domingo) até sábado que vem
   - ✅ PASSADO (incluir_passado=True): Domingo até sábado (processos que chegaram)

2. **Filtro "este mês":**
   - ✅ "este mês" = ETA >= hoje até o último dia do mês atual
   - ✅ Não mostra processos que já chegaram no passado (ETA < hoje)
   - ✅ SEMPRE começar de hoje (ETA >= hoje), não do primeiro dia do mês

3. **Filtro "mês que vem":**
   - ✅ "mês que vem" = do primeiro dia do próximo mês até o último dia do próximo mês
   - ✅ Exemplo: se hoje é 15/11/2025, retorna 01/12/2025 até 31/12/2025

4. **Filtro "semana que vem":**
   - ✅ "semana que vem" = da próxima segunda-feira até o próximo domingo
   - ✅ Sempre começa na próxima segunda (não em hoje)

5. **Filtro "futuro" ou "todos_futuros":**
   - ✅ incluir_passado=False: ETA >= hoje, SEM limite de data final
   - ✅ incluir_passado=True: janela ampliada para incluir chegados (ETA <= hoje) até 1 ano atrás

6. **Data específica:**
   - ✅ Se a data é o primeiro dia do mês (01/MM/AAAA), buscar todo o mês
   - ✅ Permite buscar por mês inteiro quando o usuário menciona apenas o mês

**Linhas relevantes:** `db_manager.py` linhas 1027-1220

---

## ✅ 3. OBSERVABILITY SERVICE (Relatórios)

### Arquivo: `services/observability_service.py`

**Status:** ✅ Implementado

**Funcionalidades:**

1. **Relatório de Consultas Bilhetadas:**
   - ✅ `obter_relatorio_consultas_bilhetadas()` - Gera relatório de uso de consultas bilhetadas
   - ✅ Agrupa por dia, semana ou mês
   - ✅ Calcula custo total (R$ 0,942 por consulta)
   - ✅ Estatísticas por tipo de consulta

2. **Relatório de Consultas Salvas:**
   - ✅ `obter_relatorio_uso_consultas_salvas()` - Gera relatório de uso de consultas salvas
   - ✅ Lista consultas mais usadas
   - ✅ Estatísticas gerais (total, nunca usadas, já usadas)

3. **Relatório de Regras Aprendidas:**
   - ✅ `obter_relatorio_uso_regras_aprendidas()` - Gera relatório de uso de regras aprendidas
   - ✅ Lista regras mais usadas
   - ✅ Lista regras nunca usadas
   - ✅ Estatísticas gerais

4. **Formatação de Relatórios:**
   - ✅ `formatar_relatorio_observabilidade()` - Formata relatórios em texto legível

---

## ✅ 4. EMAIL PERSONALIZADO (Preview/Confirmação)

### Arquivos: `services/chat_service.py`, `services/tool_definitions.py`, `app.py`

**Status:** ✅ Corrigido e implementado

**Funcionalidades:**
- ✅ Tool `enviar_email_personalizado` restaurada
- ✅ Preview antes de enviar
- ✅ Detecção de confirmação ("sim", "enviar", "ok")
- ✅ Estado salvo em `_resultado_interno` para recuperação via histórico
- ✅ Descrições ajustadas para IA usar tool correta

**Ver:** `CORRECOES_FINAIS_EMAIL_PTAX.md` para detalhes completos

---

## ✅ 5. PTAX (Duas Cotações)

### Arquivo: `templates/chat-ia-isolado.html`

**Status:** ✅ Corrigido

**Funcionalidades:**
- ✅ Mostra duas cotações: HOJE | AMANHÃ
- ✅ Formato: `PTAX: R$ X.XXXX | R$ Y.YYYY`
- ✅ Tooltip com detalhes
- ✅ Fallback para mercado_hoje se necessário

**Ver:** `CORRECOES_FINAIS_EMAIL_PTAX.md` para detalhes completos

---

## ✅ 6. MIGRAÇÕES DE SERVIÇOS

### Arquivos Migrados do `chat_service.py`:

1. **ProcessoListService:**
   - ✅ `listar_processos_por_eta` migrado
   - ✅ `listar_processos_por_situacao` migrado

2. **NCMService:**
   - ✅ `detalhar_ncm` migrado
   - ✅ `baixar_nomenclatura_ncm` migrado
   - ✅ `buscar_nota_explicativa_nesh` migrado

3. **ConsultasBilhetadasService:**
   - ✅ `listar_consultas_bilhetadas_pendentes` migrado
   - ✅ `aprovar_consultas_bilhetadas` migrado
   - ✅ `rejeitar_consultas_bilhetadas` migrado
   - ✅ `listar_consultas_aprovadas_nao_executadas` migrado
   - ✅ `executar_consultas_aprovadas` migrado

**Linhas relevantes:** `chat_service.py` linhas 905-1609

---

## ⚠️ 7. PENDÊNCIAS / A VERIFICAR

### Funcionalidades que podem ter sido implementadas mas não encontradas:

1. **MessageIntentService NÃO está sendo usado:**
   - ⚠️ `MessageIntentService` foi criado mas NÃO está sendo importado/usado no `chat_service.py`
   - ⚠️ Precisa ser integrado no `chat_service.py` para funcionar
   - 📝 **AÇÃO NECESSÁRIA:** Importar e usar `MessageIntentService` no `chat_service.py`

2. **Relatório de Intents de IA:**
   - ❓ Não encontrado código específico
   - ❓ Pode estar no `observability_service.py` ou em outro lugar
   - ❓ Pode ser que "relatório de intents" seja o `MessageIntentService` + `ObservabilityService`
   - 📝 **NOTA:** O `ObservabilityService` tem relatórios de consultas bilhetadas, consultas salvas e regras aprendidas, mas não especificamente de "intents de IA"

3. **Remoção de Regex:**
   - ⚠️ `MessageIntentService` ainda usa regex (centralização, não remoção)
   - ⚠️ `precheck_service.py` ainda usa regex
   - ❓ Pode ser que a "remoção de regex" seja a centralização no `MessageIntentService`
   - ❓ Ou pode ser que regex tenha sido removido de outros lugares e substituído por IA
   - 📝 **NOTA:** A centralização no `MessageIntentService` é um passo na direção certa, mas regex ainda é usado

4. **Detecção de Intents com IA:**
   - ❓ Não encontrado código que use IA para detectar intents (sem regex)
   - ❓ Pode estar em `precheck_service.py` ou em outro lugar
   - ❓ Pode ser que a IA faça detecção via tool calling (não precisa de regex)
   - 📝 **NOTA:** A IA faz detecção via tool calling, mas isso não substitui completamente a necessidade de regex para alguns casos

---

## 📝 PRÓXIMOS PASSOS

1. ✅ Verificar se `MessageIntentService` está sendo usado no `chat_service.py`
2. ✅ Verificar se há código de relatório de intents de IA
3. ✅ Verificar se há remoção de regex em outros lugares
4. ✅ Verificar se há detecção de intents com IA (sem regex)

---

## 🔍 ARQUIVOS PARA VERIFICAR

- `services/precheck_service.py` - Pode ter lógica de detecção de intents
- `services/analytics_service.py` - Pode ter relatórios de intents
- `services/analytical_query_service.py` - Pode ter análise de intents
- Qualquer arquivo com "intent" no nome

---

**Última atualização:** 18/12/2025

