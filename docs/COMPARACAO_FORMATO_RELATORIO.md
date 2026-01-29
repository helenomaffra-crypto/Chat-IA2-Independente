# 📊 Comparação: Formato Antigo vs. Novo

**Data:** 10/01/2026  
**Status:** ✅ Documentação de comparação

---

## 🎯 Objetivo

Comparar o formato do relatório "O QUE TEMOS PRA HOJE" usando:
1. **Formato Antigo:** Função `_formatar_dashboard_hoje()` (~700 linhas de código)
2. **Formato Novo:** Sistema JSON + IA (quando disponível) + Fallback Simples

---

## 📝 Exemplo de Dados de Entrada

Para este exemplo, vamos usar dados fictícios mas realistas:

```json
{
  "tipo_relatorio": "o_que_tem_hoje",
  "data": "2026-01-10",
  "categoria": null,
  "secoes": {
    "processos_chegando": [
      {
        "processo_referencia": "DMD.0090/25",
        "porto_nome": "Rio de Janeiro",
        "eta_iso": "2026-01-10T00:00:00Z",
        "situacao_ce": "ENTREGUE",
        "modal": "Marítimo",
        "numero_ce": "132505325389009"
      },
      {
        "processo_referencia": "ALH.0003/25",
        "porto_nome": "Santos",
        "eta_iso": "2026-01-10T00:00:00Z",
        "situacao_ce": "ENTREGUE",
        "modal": "Marítimo",
        "numero_ce": "132505052711417"
      }
    ],
    "processos_prontos": [
      {
        "processo_referencia": "BND.0083/25",
        "data_destino_final": "2026-01-05",
        "dias_atraso": 5,
        "categoria": "BND"
      },
      {
        "processo_referencia": "BND.0084/25",
        "data_destino_final": "2026-01-08",
        "dias_atraso": 2,
        "categoria": "BND"
      }
    ],
    "pendencias": [
      {
        "processo_referencia": "VDM.0003/25",
        "tipo_pendencia": "ICMS",
        "descricao_pendencia": "ICMS pendente de aprovação",
        "tempo_pendente": "3 dias",
        "acao_sugerida": "Verificar status no Portal Único"
      }
    ],
    "duimps_analise": [
      {
        "numero_duimp": "25BR00001928777",
        "versao": "1",
        "processo_referencia": "VDM.0003/25",
        "canal_duimp": "VERDE",
        "status": "EM_ANALISE",
        "tempo_analise": "2 dias"
      }
    ],
    "dis_analise": [],
    "processos_em_dta": [],
    "eta_alterado": [],
    "alertas": [
      {
        "processo_referencia": "DMD.0090/25",
        "titulo": "CE entregue",
        "tipo": "status_ce",
        "status_atual": "ENTREGUE"
      }
    ]
  },
  "resumo": {
    "total_chegando": 2,
    "total_prontos": 2,
    "total_pendencias": 1,
    "total_em_dta": 0,
    "total_duimps": 1,
    "total_dis": 0,
    "total_eta_alterado": 0,
    "total_alertas": 1
  }
}
```

---

## 🔴 FORMATO ANTIGO (função `_formatar_dashboard_hoje`)

### Resultado:

```
📅 **O QUE TEMOS PRA HOJE - 10/01/2026**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚢 **CHEGANDO HOJE** (2 processo(s))

   **ALH** (1 processo(s)):
      • **ALH.0003/25** - Porto: Santos - ETA: 10/01/2026 (confirmado) - Status: ENTREGUE - Modal: Marítimo

   **DMD** (1 processo(s)):
      • **DMD.0090/25** - Porto: Rio de Janeiro - ETA: 10/01/2026 (confirmado) - Status: ENTREGUE - Modal: Marítimo


✅ **PRONTOS PARA REGISTRO** (2 processo(s))

   ⚠️ **ATRASO MODERADO** (1 processo(s) - 3 a 7 dias):

      **BND** (1 processo(s)):
         • **BND.0083/25** - Chegou em 05/01/2026 (5 dia(s) de atraso), sem DI/DUIMP - Tipo: DUIMP - Status CE: ENTREGUE

   ✅ **RECENTES** (1 processo(s) - menos de 3 dias):

      **BND** (1 processo(s)):
         • **BND.0084/25** - Chegou em 08/01/2026, sem DI/DUIMP - Tipo: DUIMP - Status CE: ENTREGUE


⚠️ **PENDÊNCIAS ATIVAS** (1 processo(s))

   **ICMS** (1 processo(s)):
      *VDM* (1 processo(s)):
         • **VDM.0003/25** - ICMS pendente de aprovação (há 3 dias) - Ação: Verificar status no Portal Único


📋 **DIs EM ANÁLISE** (0 DI(s))

   ✅ Nenhuma DI em análise.


📋 **DUIMPs EM ANÁLISE** (1 DUIMP(s))

   **VDM** (1 DUIMP(s)):
      • **25BR00001928777** v1 - Processo: VDM.0003/25 - Canal: VERDE - Status DUIMP: Em Analise (há 2 dias)


🔔 **ALERTAS RECENTES**

   ✅ 📦 DMD.0090/25: CE - ENTREGUE


💡 **AÇÕES SUGERIDAS**

   1. 🔥 Criar DUIMP para BND.0083/25 (urgente - chegou hoje)
   2. ⚠️ Criar DUIMP para BND.0083/25 (5 dia(s) de atraso)
   3. ⚠️ Verificar ICMS de VDM.0003/25 (pendente há 3 dias)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **RESUMO:** 2 chegando | 2 prontos | 0 em DTA | 1 pendências | 0 DIs | 1 DUIMPs
```

### Características do Formato Antigo:
- ✅ **Detalhado:** Mostra muitos detalhes de cada item
- ✅ **Agrupado:** Agrupa por categoria dentro de cada seção
- ✅ **Hierarquizado:** Separa por nível de atraso (crítico, moderado, recentes)
- ✅ **Consistente:** Formato sempre igual
- ❌ **Rígido:** Não se adapta ao contexto
- ❌ **Verboso:** Pode ser muito longo com muitos processos
- ❌ **Código complexo:** ~700 linhas difíceis de manter

---

## 🟢 FORMATO NOVO - Fallback Simples

### Resultado (quando `FORMATAR_RELATORIOS_COM_IA=false`):

```
📅 **O QUE TEMOS PRA HOJE - 10/01/2026**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **RESUMO:** 2 chegando hoje, 2 prontos, 1 pendências, 0 em DTA, 1 DUIMPs em análise, 0 DIs em análise, 0 ETAs alterados, 1 alertas

🚢 **CHEGANDO HOJE** (2 processo(s))

   • **DMD.0090/25** - Porto: Rio de Janeiro - CE: 132505325389009
   • **ALH.0003/25** - Porto: Santos - CE: 132505052711417

✅ **PRONTOS PARA REGISTRO** (2 processo(s))

   • **BND.0083/25** (BND)
   • **BND.0084/25** (BND)

⚠️ **PENDÊNCIAS ATIVAS** (1 pendência(s))

   • **VDM.0003/25** - ICMS: ICMS pendente de aprovação

📋 **EM DTA** (0 processo(s))

🔍 **DUIMPs EM ANÁLISE** (1 DUIMP(s))

🔄 **ETA ALTERADO** (0 processo(s))

🔔 **ALERTAS** (1 alerta(s))
```

### Características do Fallback Simples:
- ✅ **Simples:** Formato básico e direto
- ✅ **Rápido:** Não requer IA
- ✅ **Funcional:** Mostra informações essenciais
- ✅ **Código limpo:** ~100 linhas vs ~700 linhas
- ⚠️ **Menos detalhado:** Não agrupa por categoria nem hierarquiza
- ⚠️ **Menos visual:** Não destaca prioridades

---

## 🟣 FORMATO NOVO - Com IA (quando `FORMATAR_RELATORIOS_COM_IA=true`)

### Resultado (formatação pela IA):

```
📅 **O QUE TEMOS PRA HOJE - 10 de Janeiro de 2026**

Olá! Aqui está o resumo do que temos para hoje:

## 📊 Visão Geral
- **2 processos** chegando hoje
- **2 processos** prontos para registro (1 com atraso moderado)
- **1 pendência** ativa que precisa atenção
- **1 DUIMP** em análise

---

## 🚢 Processos Chegando Hoje

Temos 2 processos que chegaram hoje e precisam de atenção:

1. **DMD.0090/25** - Porto: Rio de Janeiro
   - CE: 132505325389009 já entregue ✅
   - Modal: Marítimo

2. **ALH.0003/25** - Porto: Santos  
   - CE: 132505052711417 já entregue ✅
   - Modal: Marítimo

---

## ✅ Processos Prontos para Registro

Identifiquei 2 processos que estão prontos para ter DUIMP registrada:

1. **BND.0083/25** ⚠️
   - Chegou em 05/01/2026
   - **5 dias de atraso** - precisa de atenção urgente!
   - Categoria: BND

2. **BND.0084/25**
   - Chegou em 08/01/2026
   - 2 dias desde a chegada
   - Categoria: BND

💡 **Ação sugerida:** Criar DUIMP para BND.0083/25 com prioridade, pois já está com 5 dias de atraso.

---

## ⚠️ Pendências Ativas

Há 1 pendência que precisa ser resolvida:

- **VDM.0003/25** - Pendência de ICMS
  - Descrição: ICMS pendente de aprovação
  - Pendente há: 3 dias
  - Ação: Verificar status no Portal Único

---

## 📋 DUIMPs em Análise

1 processo tem DUIMP em análise:

- **DUIMP 25BR00001928777** (versão 1) - Processo VDM.0003/25
  - Canal: VERDE
  - Status: Em análise há 2 dias

---

## 🔔 Alertas Recentes

- CE do processo **DMD.0090/25** foi entregue ✅

---

## 💡 Resumo Executivo

**Prioridades para hoje:**
1. 🔴 URGENTE: Criar DUIMP para BND.0083/25 (5 dias de atraso)
2. 🟡 MÉDIO: Verificar pendência de ICMS do VDM.0003/25
3. 🟢 BAIXO: Acompanhar DUIMP 25BR00001928777 em análise

Total de movimentações: **6 itens** para acompanhar hoje.
```

### Características do Formato com IA:
- ✅ **Natural:** Linguagem mais conversacional e humanizada
- ✅ **Adaptável:** A IA pode ajustar o formato conforme o contexto
- ✅ **Priorizado:** Destaca o que é mais importante
- ✅ **Organizado:** Usa seções e hierarquia visual melhor
- ✅ **Informativo:** Inclui contexto e explicações
- ✅ **Flexível:** Pode variar o estilo conforme necessário
- ⚠️ **Depende da IA:** Requer API disponível e tokens

---

## 📊 Comparação Visual

| Aspecto | Formato Antigo | Fallback Simples | Formato com IA |
|---------|---------------|------------------|----------------|
| **Linhas de código** | ~700 | ~100 | ~200 (prompt) |
| **Detalhamento** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Naturalidade** | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Agrupamento** | ✅ Por categoria | ❌ Lista simples | ✅ Inteligente |
| **Priorização** | ✅ Por atraso | ❌ Sem priorização | ✅ Contextual |
| **Manutenibilidade** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Velocidade** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Custo** | Grátis | Grátis | Tokens (baixo) |
| **Adaptabilidade** | ❌ Fixo | ❌ Fixo | ✅ Flexível |

---

## 🎯 Quando Usar Cada Formato?

### Formato Antigo (função `_formatar_dashboard_hoje`)
- ❌ **NÃO usar mais** - foi substituído
- ✅ Mantido apenas como referência/backup

### Fallback Simples
- ✅ Quando `FORMATAR_RELATORIOS_COM_IA=false`
- ✅ Quando a IA não está disponível
- ✅ Quando há muitos dados (para ser mais rápido)
- ✅ Para debug/testes

### Formato com IA
- ✅ Quando `FORMATAR_RELATORIOS_COM_IA=true` (padrão)
- ✅ Para usuários finais (experiência melhor)
- ✅ Quando você quer formatação mais natural
- ✅ Quando precisa priorizar informações importantes

---

## 🔄 Fluxo de Decisão

```
1. Buscar dados do banco
   ↓
2. Criar JSON estruturado
   ↓
3. FORMATAR_RELATORIOS_COM_IA=true?
   ├─ SIM → Tentar formatar com IA
   │        ├─ IA disponível e funcionou? → Usar formato IA ✅
   │        └─ IA falhou? → Fallback simples ⚠️
   │
   └─ NÃO → Usar fallback simples diretamente ⚠️
```

---

## ✅ Vantagens do Novo Sistema

1. **Manutenibilidade:** Código muito mais simples (~100 linhas vs ~700)
2. **Flexibilidade:** IA pode adaptar formato conforme contexto
3. **Naturalidade:** Texto mais conversacional e fácil de ler
4. **Modularidade:** Separação clara entre busca de dados, estruturação JSON e formatação
5. **Testabilidade:** Mais fácil testar cada parte separadamente
6. **Escalabilidade:** Fácil adicionar novos tipos de relatórios
7. **Fallback seguro:** Sempre tem uma resposta mesmo se IA falhar

---

## 📝 Notas Finais

- O formato antigo ainda existe no código mas **não é mais usado**
- O novo sistema prioriza **JSON como fonte da verdade**
- A IA apenas **formata/apresenta** os dados, não os busca
- O fallback simples garante que o sistema **sempre funcione**
- Você pode ativar/desativar IA via variável de ambiente `FORMATAR_RELATORIOS_COM_IA`

---

**Última atualização:** 10/01/2026
