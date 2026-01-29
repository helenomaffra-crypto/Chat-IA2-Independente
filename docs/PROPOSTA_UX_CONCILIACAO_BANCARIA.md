# 🎨 Proposta de UX/UI: Visualização de Conciliações Bancárias

**Data:** 08/01/2026  
**Contexto:** Sistema mAIke - Assistente COMEX com interface de chat  
**Objetivo:** Permitir visualização clara do que foi conciliado ou não, mantendo a experiência natural do chat

---

## 🎯 Objetivos da Conciliação

1. **Marcar origem do dinheiro** (Compliance - Receita Federal/COAF)
2. **Vincular despesas a processos** (ex: BGR.0070/25 - pagamento AFRMM)

---

## 💡 Princípios de Design

### 1. **"Sistema Escondido no Chat"**
- ✅ Menu drawer já funciona bem (mantém essa abordagem)
- ✅ Experiência natural: usuário conversa com mAIke, não com formulários
- ✅ Funcionalidades avançadas acessíveis via comandos de voz/texto

### 2. **Visualização Contextual**
- Mostrar informações quando relevante
- Integrar ao fluxo natural de consulta de processos
- Não sobrecarregar a interface principal

### 3. **Transparência e Rastreabilidade**
- Sempre claro o que foi conciliado e o que não foi
- Fácil identificar pendências
- Rastreamento completo para compliance

---

## 🎨 Soluções Propostas

### **SOLUÇÃO 1: Integração no Chat - Respostas Contextuais** ⭐ **RECOMENDADA**

**Conceito:** Quando o usuário consulta um processo, o mAIke automaticamente mostra o status de conciliação das despesas relacionadas.

#### Como Funciona:

**Exemplo 1: Consulta de Processo**
```
👤 "status do BGR.0070/25"

🤖 mAIke:
📋 BGR.0070/25 - Status Geral
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Situação: DI Desembaraçada
📅 Chegada: 15/12/2025
🚢 Navio: MSC OSCAR

💰 DESPESAS CONCILIADAS:
  ✅ AFRMM: R$ 1.250,00 (07/01/2026 - BB Ag. 1505)
  ✅ Frete Internacional: R$ 4.500,00 (05/01/2026 - BB Ag. 1505)
  ⚠️ Seguro: R$ 200,00 - PENDENTE CONCILIAÇÃO

📊 Total Conciliado: R$ 5.750,00 de R$ 5.950,00 (96,6%)

[🔍 Ver detalhes da conciliação] [➕ Conciliação pendente]
```

**Exemplo 2: Comando Específico**
```
👤 "despesas do BGR.0070/25"

🤖 mAIke:
💰 DESPESAS - BGR.0070/25
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ CONCILIADAS (2):
  1. AFRMM - R$ 1.250,00
     📅 Data: 07/01/2026
     🏦 Banco: BB - Ag. 1505 C/C 1348
     📝 Lançamento: "Pagamento AFRMM BGR.0070/25"
     ✅ Origem: Cliente (CPF/CNPJ: 12.345.678/0001-90)

  2. Frete Internacional - R$ 4.500,00
     📅 Data: 05/01/2026
     🏦 Banco: BB - Ag. 1505 C/C 1348
     📝 Lançamento: "Frete MSC OSCAR"
     ✅ Origem: Fornecedor (CNPJ: 98.765.432/0001-10)

⚠️ PENDENTES (1):
  1. Seguro - R$ 200,00 (estimado)
     💡 Sugestão: Buscar lançamento no período 01-10/01/2026

[➕ Conciliação pendente] [📊 Relatório completo]
```

#### Implementação:

1. **Tool no mAIke:** `consultar_despesas_processo`
   - Busca despesas vinculadas ao processo
   - Mostra status de conciliação
   - Indica pendências

2. **Integração no ProcessoAgent:**
   - Ao consultar processo, automaticamente inclui despesas conciliadas
   - Formatação contextual e clara

3. **Botões de Ação:**
   - Links clicáveis que abrem modais específicos
   - Mantém experiência do chat

---

### **SOLUÇÃO 2: Dashboard de Conciliação no Menu** ⭐ **COMPLEMENTAR**

**Conceito:** Menu drawer com seção dedicada para visualização consolidada.

#### Estrutura do Menu:

```
☰ Menu
├── Financeiro
│   ├── Sincronizar Extratos
│   ├── Conciliação Bancária
│   └── 📊 Dashboard de Conciliações  ← NOVO
├── Documentos
├── Sistema
└── Ajuda
```

#### Dashboard de Conciliações:

**Tela 1: Visão Geral**
```
📊 CONCILIAÇÃO BANCÁRIA - RESUMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Período: Janeiro 2026

📈 ESTATÍSTICAS:
  • Total de lançamentos: 145
  • Conciliados: 132 (91%)
  • Pendentes: 13 (9%)
  • Valor total: R$ 2.450.000,00
  • Valor conciliado: R$ 2.380.000,00

🔍 FILTROS:
  [Todos] [Pendentes] [Por Processo] [Por Tipo Despesa]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 PROCESSOS COM DESPESAS CONCILIADAS (15):
  • BGR.0070/25 - R$ 5.750,00 (3 despesas) ✅
  • ALH.0123/25 - R$ 12.300,00 (5 despesas) ✅
  • VDM.0045/25 - R$ 8.900,00 (2 despesas) ⚠️ 1 pendente
  ...

⚠️ PENDÊNCIAS (13 lançamentos):
  • R$ 1.250,00 - 07/01/2026 - "Pagamento AFRMM" [Conciliação pendente]
  • R$ 3.500,00 - 05/01/2026 - "Frete internacional" [Conciliação pendente]
  ...
```

**Tela 2: Detalhes por Processo**
```
💰 DESPESAS - BGR.0070/25
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ CONCILIADAS (2):
  [Lista detalhada com origem, data, banco, etc.]

⚠️ PENDENTES (1):
  [Lista de despesas esperadas mas não conciliadas]

📊 ORIGEM DOS RECURSOS:
  • Cliente: R$ 1.250,00 (21,7%)
  • Fornecedor: R$ 4.500,00 (78,3%)
  • Total: R$ 5.750,00

[➕ Adicionar despesa] [📄 Relatório compliance] [🔍 Rastreamento]
```

#### Implementação:

1. **Novo endpoint:** `/api/banco/dashboard-conciliacao`
2. **Componente React/Vanilla JS:** Dashboard interativo
3. **Filtros e busca:** Por processo, tipo despesa, período, status

---

### **SOLUÇÃO 3: Indicadores Visuais no Chat** ⭐ **SUTIL**

**Conceito:** Badges e indicadores sutis que aparecem naturalmente nas respostas.

#### Exemplos:

**Badge de Status:**
```
👤 "como estão os BGR?"

🤖 mAIke:
📋 PROCESSOS BGR - STATUS GERAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• BGR.0070/25 - DI Desembaraçada
  💰 Despesas: ✅ 2/3 conciliadas | ⚠️ R$ 200,00 pendente

• BGR.0071/25 - Aguardando Desembaraço
  💰 Despesas: ⚠️ Nenhuma conciliada ainda
```

**Comando Específico:**
```
👤 "quais processos têm despesas pendentes?"

🤖 mAIke:
⚠️ PROCESSOS COM DESPESAS PENDENTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. BGR.0070/25
   ⚠️ Seguro: R$ 200,00 - Sem lançamento bancário encontrado
   💡 Sugestão: Verificar período 01-10/01/2026

2. VDM.0045/25
   ⚠️ AFRMM: R$ 1.500,00 - Lançamento não classificado
   💡 Ação: [Conciliação pendente]

[➕ Abrir conciliação] [📊 Ver todos]
```

---

### **SOLUÇÃO 4: Relatório de Compliance Integrado** ⭐ **CRÍTICO**

**Conceito:** Relatório completo de rastreamento de origem dos recursos, acessível via chat.

#### Comando:
```
👤 "rastreamento de recursos do BGR.0070/25"

🤖 mAIke:
🔍 RASTREAMENTO DE RECURSOS - BGR.0070/25
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 ORIGEM DOS RECURSOS:

1. AFRMM - R$ 1.250,00
   👤 Origem: Cliente
   📄 CPF/CNPJ: 12.345.678/0001-90
   🏦 Banco: BB - Ag. 1505 C/C 1348
   📅 Data: 07/01/2026
   📝 Comprovante: [Ver extrato bancário]
   ✅ Validado: Sim
   📊 Rastreamento: Cliente → BB → AFRMM → BGR.0070/25

2. Frete Internacional - R$ 4.500,00
   👤 Origem: Fornecedor
   📄 CNPJ: 98.765.432/0001-10
   🏦 Banco: BB - Ag. 1505 C/C 1348
   📅 Data: 05/01/2026
   📝 Comprovante: [Ver extrato bancário]
   ✅ Validado: Sim
   📊 Rastreamento: Fornecedor → BB → Frete → BGR.0070/25

⚠️ PENDENTE:
   • Seguro - R$ 200,00 (sem rastreamento)

[📄 Gerar relatório PDF] [📊 Exportar Excel] [🔍 Ver detalhes]
```

---

## 🎯 Recomendação Final: Abordagem Híbrida

### **Fase 1: Integração no Chat (Prioritária)**
- ✅ Solução 1: Respostas contextuais automáticas
- ✅ Solução 3: Indicadores visuais sutis
- ✅ Solução 4: Relatório de compliance via chat

**Vantagens:**
- Mantém experiência natural do chat
- Não quebra o fluxo de trabalho
- Acessível via comandos de voz (futuro)
- Integrado ao assistente COMEX

### **Fase 2: Dashboard Complementar (Opcional)**
- ✅ Solução 2: Dashboard no menu drawer

**Vantagens:**
- Visão consolidada para análise
- Útil para relatórios e auditoria
- Complementa a experiência do chat

---

## 📋 Implementação Técnica

### **1. Tool para Consulta de Despesas**

```python
# services/tool_definitions.py
{
    "type": "function",
    "function": {
        "name": "consultar_despesas_processo",
        "description": "Consulta despesas vinculadas a um processo, mostrando status de conciliação, origem dos recursos e pendências. Use quando usuário perguntar sobre despesas, pagamentos ou conciliação de um processo específico.",
        "parameters": {
            "type": "object",
            "properties": {
                "processo_referencia": {
                    "type": "string",
                    "description": "Referência do processo (ex: BGR.0070/25)"
                },
                "incluir_pendentes": {
                    "type": "boolean",
                    "description": "Incluir despesas pendentes de conciliação (default: true)"
                },
                "incluir_rastreamento": {
                    "type": "boolean",
                    "description": "Incluir rastreamento completo de origem dos recursos (default: false)"
                }
            },
            "required": ["processo_referencia"]
        }
    }
}
```

### **2. Serviço de Consulta**

```python
# services/banco_concilacao_service.py
def consultar_despesas_processo(
    self,
    processo_referencia: str,
    incluir_pendentes: bool = True,
    incluir_rastreamento: bool = False
) -> Dict[str, Any]:
    """
    Consulta despesas vinculadas a um processo.
    
    Retorna:
    {
        'processo_referencia': 'BGR.0070/25',
        'despesas_conciliadas': [
            {
                'tipo_despesa': 'AFRMM',
                'valor': 1250.00,
                'data_pagamento': '2026-01-07',
                'banco': 'BB',
                'agencia': '1505',
                'conta': '1348',
                'origem_recurso': 'Cliente',
                'cpf_cnpj_origem': '12.345.678/0001-90',
                'validado': True
            },
            ...
        ],
        'despesas_pendentes': [
            {
                'tipo_despesa': 'Seguro',
                'valor_estimado': 200.00,
                'sugestao_periodo': '01-10/01/2026'
            },
            ...
        ],
        'total_conciliado': 5750.00,
        'total_pendente': 200.00,
        'percentual_conciliado': 96.6
    }
    """
```

### **3. Integração no ProcessoAgent**

```python
# services/agents/processo_agent.py
def _consultar_processo(self, arguments, context):
    # ... busca dados do processo ...
    
    # ✅ NOVO: Incluir despesas automaticamente
    from services.banco_concilacao_service import get_banco_concilacao_service
    conciliacao_service = get_banco_concilacao_service()
    despesas = conciliacao_service.consultar_despesas_processo(
        processo_referencia=processo_referencia,
        incluir_pendentes=True,
        incluir_rastreamento=False
    )
    
    # Formatar resposta incluindo despesas
    resposta += _formatar_despesas_processo(despesas)
    
    return resposta
```

### **4. Formatação Contextual**

```python
def _formatar_despesas_processo(despesas: Dict[str, Any]) -> str:
    """
    Formata despesas para exibição no chat.
    """
    if not despesas.get('despesas_conciliadas'):
        return ""
    
    texto = "\n💰 DESPESAS CONCILIADAS:\n"
    
    for despesa in despesas['despesas_conciliadas']:
        texto += f"  ✅ {despesa['tipo_despesa']}: "
        texto += f"R$ {despesa['valor']:,.2f} "
        texto += f"({despesa['data_pagamento']} - {despesa['banco']})\n"
    
    if despesas.get('despesas_pendentes'):
        texto += "\n⚠️ PENDENTES:\n"
        for pendente in despesas['despesas_pendentes']:
            texto += f"  ⚠️ {pendente['tipo_despesa']}: "
            texto += f"R$ {pendente['valor_estimado']:,.2f}\n"
    
    texto += f"\n📊 Total: R$ {despesas['total_conciliado']:,.2f} "
    texto += f"({despesas['percentual_conciliado']:.1f}% conciliado)\n"
    
    return texto
```

---

## 🎨 Elementos Visuais

### **Badges e Indicadores:**
- ✅ Verde: Conciliado e validado
- ⚠️ Amarelo: Pendente de conciliação
- ❌ Vermelho: Erro ou inconsistência
- 🔍 Azul: Detalhes disponíveis

### **Links de Ação:**
- `[➕ Conciliação pendente]` - Abre modal de conciliação
- `[📊 Relatório completo]` - Gera relatório detalhado
- `[🔍 Ver detalhes]` - Expande informações
- `[📄 Gerar PDF]` - Exporta relatório

---

## 📊 Fluxo de Uso Proposto

### **Cenário 1: Consulta Natural**
```
👤 "status do BGR.0070/25"
↓
🤖 mAIke mostra status + despesas conciliadas automaticamente
↓
👤 "quais despesas estão pendentes?"
↓
🤖 mAIke lista pendências com ações sugeridas
↓
👤 "conciliação pendente" (ou clica no link)
↓
🤖 mAIke abre modal de conciliação
```

### **Cenário 2: Comando Direto**
```
👤 "despesas do BGR.0070/25"
↓
🤖 mAIke mostra relatório completo de despesas
↓
👤 "rastreamento de recursos"
↓
🤖 mAIke mostra rastreamento completo para compliance
```

### **Cenário 3: Dashboard**
```
👤 "maike quero ver conciliações" (ou abre menu)
↓
🤖 mAIke abre dashboard de conciliações
↓
👤 Filtra por processo, período, status
↓
🤖 mAIke mostra visão consolidada
```

---

## ✅ Checklist de Implementação

### **Fase 1: Integração no Chat**
- [ ] Criar tool `consultar_despesas_processo`
- [ ] Implementar serviço `consultar_despesas_processo` no `BancoConcilacaoService`
- [ ] Integrar no `ProcessoAgent._consultar_processo`
- [ ] Criar função de formatação `_formatar_despesas_processo`
- [ ] Adicionar links de ação nas respostas
- [ ] Testar com processos reais

### **Fase 2: Relatório de Compliance**
- [ ] Criar tool `rastrear_origem_recursos`
- [ ] Implementar serviço de rastreamento
- [ ] Formatação de relatório completo
- [ ] Exportação PDF/Excel
- [ ] Validação de contrapartidas

### **Fase 3: Dashboard (Opcional)**
- [ ] Criar endpoint `/api/banco/dashboard-conciliacao`
- [ ] Criar componente de dashboard
- [ ] Implementar filtros e busca
- [ ] Adicionar ao menu drawer

---

## 🎯 Próximos Passos

1. **Validar proposta** com usuário
2. **Priorizar implementação** (Fase 1 primeiro)
3. **Definir detalhes** de formatação e visual
4. **Implementar** seguindo checklist
5. **Testar** com casos reais
6. **Iterar** baseado em feedback

---

**Última atualização:** 08/01/2026  
**Status:** 📋 Proposta - Aguardando validação


