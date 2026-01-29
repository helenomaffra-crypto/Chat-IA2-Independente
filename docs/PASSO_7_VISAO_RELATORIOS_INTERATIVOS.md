# Passo 7 - Visão: Relatórios Interativos com IA

**Data:** 10/01/2026  
**Status:** 📋 **PLANEJAMENTO**

---

## 🎯 Visão Completa

### **Objetivo Principal**

Transformar relatórios em **sistemas interativos** onde o usuário pode:
1. **Gerar relatório inicial** (com JSON estruturado)
2. **Manipular/filtrar via IA** (ex: "filtra só DMD", "mostra só processos prontos")
3. **Ajustar/refinar** (ex: "melhore esse relatorio", "adicione mais detalhes")
4. **Enviar por email** (trabalhar com relatório final)
5. **Workflow padronizado** (similar ao sistema de emails com ajustes)

### **Analogia com Sistema de Email**

**Email atual (já implementado):**
```
1. Usuário: "envia email para X sobre Y"
   ↓
2. Sistema: Gera preview do email
   ↓
3. Usuário: "melhore esse email" / "adicione Z" / "torne mais formal"
   ↓
4. Sistema: Atualiza preview com ajustes
   ↓
5. Usuário: "pode enviar"
   ↓
6. Sistema: Envia email final
```

**Relatórios (visão futura):**
```
1. Usuário: "o que temos pra hoje?"
   ↓
2. Sistema: Gera relatório completo (JSON + formatação IA)
   ↓
3. Usuário: "filtra só DMD" / "mostra só processos prontos" / "exclui pendências"
   ↓
4. Sistema: Manipula JSON, re-formata com IA, atualiza preview
   ↓
5. Usuário: "melhore esse relatorio" / "adicione mais detalhes sobre X"
   ↓
6. Sistema: Refina formatação (mantém filtros), atualiza preview
   ↓
7. Usuário: "envia esse relatorio para helenomaffra@gmail.com"
   ↓
8. Sistema: Envia relatório final (com filtros e ajustes aplicados)
```

---

## 🔧 Arquitetura Proposta

### **Fase 7.1: Manipulação de JSON via IA**

**Objetivo:** Permitir que IA manipule o JSON baseado em comandos do usuário.

**Exemplos de comandos:**
- "filtra só DMD" → Filtrar `dados_json.secoes` por categoria DMD
- "mostra só processos prontos" → Filtrar `processos_prontos` apenas
- "exclui pendências" → Remover seção `pendencias`
- "adiciona mais detalhes sobre CE" → Expandir informações de CE
- "agrupa por modal" → Reorganizar por modal (Aéreo/Marítimo)

**Implementação:**
```python
# Novo serviço: RelatorioManipulationService
class RelatorioManipulationService:
    @staticmethod
    def aplicar_filtro(dados_json: Dict, comando: str) -> Dict:
        """
        Aplica filtro/manipulação ao JSON baseado em comando natural.
        
        Usa IA para interpretar comando e modificar JSON.
        Retorna JSON modificado (mantendo estrutura).
        """
        # 1. Interpretar comando com IA
        # 2. Modificar JSON conforme interpretação
        # 3. Validar estrutura mantida
        # 4. Retornar JSON modificado
```

**Fluxo:**
1. Usuário pede filtro/manipulação
2. Sistema busca `dados_json` do relatório atual (salvo no contexto)
3. `RelatorioManipulationService` aplica filtro via IA
4. `RelatorioFormatterService` re-formata JSON modificado
5. Atualiza preview e salva estado no contexto

### **Fase 7.2: Estado de Relatório (Draft System)**

**Objetivo:** Manter estado do relatório durante interações (similar a email drafts).

**Estrutura:**
```python
@dataclass
class RelatorioDraft:
    """Estado de relatório em edição."""
    draft_id: str
    tipo_relatorio: str
    dados_json_original: Dict  # JSON original (sem filtros)
    dados_json_atual: Dict  # JSON atual (com filtros/ajustes)
    texto_formatado: str  # Versão formatada atual
    filtros_aplicados: List[str]  # Histórico de filtros
    ajustes_aplicados: List[str]  # Histórico de ajustes
    criado_em: str
    atualizado_em: str
```

**Uso:**
- Quando usuário pede "filtra só DMD", cria/atualiza draft
- Todas as manipulações modificam o draft
- Preview sempre mostra estado atual do draft
- Envio por email usa draft atual

### **Fase 7.3: IA Gerencia Emojis Automaticamente**

**Objetivo:** IA escolhe e organiza emojis de forma inteligente para separar seções.

**Melhorias atuais:**
- ✅ Já implementado: IA usa emojis na formatação
- 🔄 Melhorar: IA escolhe emojis mais contextuais
- 🔄 Melhorar: Consistência de emojis entre seções relacionadas
- 🔄 Melhorar: Emojis específicos por tipo de informação (processo, pendência, alerta)

**Exemplo de melhorias:**
```python
# Prompt melhorado para IA escolher emojis:
"""
Seções do relatório:
- Processos chegando: 🚢 (embarque/transporte)
- Processos prontos: ✅ (pronto/liberado)
- Pendências: ⚠️ (atenção/urgente)
- DUIMPs em análise: 📝 (documento/processamento)
- DIs em análise: 🔍 (análise/verificação)
- ETAs alterados: ⏱️ (tempo/mudança)
- Alertas: 🔔 (notificação/importante)

Use emojis consistentes e contextuais. Não use emojis genéricos (ex: ❌ para tudo).
Organize visualmente para facilitar leitura rápida.
"""
```

---

## 📊 Comparação: Antes vs Depois

### **Antes (Atual - Passo 6 Fase 2)**

```
Usuário: "o que temos pra hoje?"
  ↓
Sistema: Gera JSON + Formata com IA
  ↓
Usuário: "melhore esse relatorio"
  ↓
Sistema: Re-formata JSON (mesmos dados)
  ↓
Usuário: "envia para X"
  ↓
Sistema: Envia relatório (sem filtros)
```

**Limitações:**
- ❌ Não permite filtrar dados
- ❌ Não permite manipular estrutura
- ❌ Não mantém estado entre interações
- ❌ Re-formata sempre com todos os dados

### **Depois (Visão - Passo 7)**

```
Usuário: "o que temos pra hoje?"
  ↓
Sistema: Gera JSON + Formata com IA + Cria Draft
  ↓
Usuário: "filtra só DMD"
  ↓
Sistema: Manipula JSON (filtra DMD) + Re-formata + Atualiza Draft
  ↓
Usuário: "melhore esse relatorio"
  ↓
Sistema: Refina formatação (mantém filtro DMD) + Atualiza Draft
  ↓
Usuário: "envia para X"
  ↓
Sistema: Envia relatório final (com filtro DMD aplicado)
```

**Benefícios:**
- ✅ Permite filtrar dados dinamicamente
- ✅ Permite manipular estrutura
- ✅ Mantém estado (draft system)
- ✅ Workflow padronizado (como emails)
- ✅ Usuário pode explorar dados interativamente

---

## 🚀 Plano de Implementação

### **Passo 7.1: RelatorioManipulationService (Básico)**

**Objetivos:**
1. Criar serviço de manipulação de JSON
2. Implementar filtros básicos (categoria, tipo processo, status)
3. Integrar com sistema de drafts

**Filtros iniciais:**
- Por categoria (DMD, ALH, VDM, etc.)
- Por tipo processo (prontos, chegando, em DTA)
- Por status (pendências, alertas, etc.)
- Excluir seções específicas

**Estimativa:** 2-3 dias

### **Passo 7.2: Sistema de Drafts para Relatórios**

**Objetivos:**
1. Criar `RelatorioDraft` (similar a `EmailDraft`)
2. Integrar com `RelatorioManipulationService`
3. Manter estado durante interações
4. Atualizar preview dinamicamente

**Estimativa:** 2-3 dias

### **Passo 7.3: Melhorias de Emojis e Formatação**

**Objetivos:**
1. Melhorar prompt de formatação para escolha inteligente de emojis
2. Adicionar mapeamento contextual de emojis
3. Garantir consistência visual

**Estimativa:** 1 dia

### **Passo 7.4: Integração com Email**

**Objetivos:**
1. Permitir enviar relatório draft por email
2. Manter filtros/ajustes no email enviado
3. Workflow completo: gerar → filtrar → ajustar → enviar

**Estimativa:** 1-2 dias

---

## 🔗 Integração com Sistema Atual

### **Compatibilidade com Passo 6**

✅ **JSON estruturado já existe:**
- `dados_json` já está sendo gerado em `_obter_dashboard_hoje()`
- Estrutura compatível com manipulação

✅ **Formatação com IA já existe:**
- `RelatorioFormatterService` já formata JSON com IA
- Pode ser reutilizado para re-formatação após filtros

✅ **Contexto de sessão já existe:**
- `report_service` já salva relatórios no contexto
- Pode ser estendido para drafts

### **Novos Componentes Necessários**

1. **RelatorioManipulationService** (novo)
   - Manipula JSON baseado em comandos
   - Integra com IA para interpretação de comandos

2. **RelatorioDraft** (novo)
   - Similar a `EmailDraft`
   - Mantém estado durante interações

3. **Precheck para manipulação** (novo)
   - Detecta comandos de filtro/manipulação
   - Roteia para `RelatorioManipulationService`

---

## 💡 Exemplos de Uso Futuro

### **Exemplo 1: Filtro por Categoria**

```
👤 Usuário: "o que temos pra hoje?"
🤖 mAIke: [Mostra relatório completo]

👤 Usuário: "filtra só DMD"
🤖 mAIke: [Re-formata relatório mostrando apenas processos DMD]

👤 Usuário: "envia esse relatorio para helenomaffra@gmail.com"
🤖 mAIke: [Envia email com relatório filtrado apenas DMD]
```

### **Exemplo 2: Múltiplos Filtros**

```
👤 Usuário: "o que temos pra hoje?"
🤖 mAIke: [Mostra relatório completo]

👤 Usuário: "mostra só processos prontos"
🤖 mAIke: [Filtra e mostra apenas seção "Processos Prontos"]

👤 Usuário: "adiciona também as pendências"
🤖 mAIke: [Adiciona seção de pendências ao relatório filtrado]

👤 Usuário: "exclui os alertas"
🤖 mAIke: [Remove seção de alertas, mantém prontos + pendências]

👤 Usuário: "melhore esse relatorio"
🤖 mAIke: [Refina formatação mantendo filtros aplicados]
```

### **Exemplo 3: Workflow Completo**

```
👤 Usuário: "fechamento do dia"
🤖 mAIke: [Gera fechamento completo]

👤 Usuário: "agrupa por categoria"
🤖 mAIke: [Reorganiza relatório agrupando por categoria]

👤 Usuário: "adiciona totalizadores no final"
🤖 mAIke: [Adiciona seção de totais/resumo final]

👤 Usuário: "envia para equipe"
🤖 mAIke: "Para quem devo enviar?"
👤 Usuário: "helenomaffra@gmail.com, joao@empresa.com"
🤖 mAIke: [Envia email com relatório completo, agrupado e com totalizadores]
```

---

## 🎯 Benefícios da Implementação

### **Para o Usuário:**
- ✅ Exploração interativa de dados
- ✅ Relatórios personalizados sob demanda
- ✅ Workflow natural e intuitivo
- ✅ Economia de tempo (não precisa regenerar relatório)

### **Para o Sistema:**
- ✅ Reutilização de dados (não precisa re-consultar banco)
- ✅ Flexibilidade arquitetural
- ✅ Base sólida para futuras melhorias
- ✅ Consistência com sistema de emails

---

## 📝 Notas Técnicas

### **Manipulação de JSON**

**Estratégia:**
1. IA interpreta comando → Gera instruções de manipulação
2. `RelatorioManipulationService` aplica instruções → Modifica JSON
3. Valida estrutura → Garante integridade
4. Re-formata → Usa `RelatorioFormatterService`

**Exemplo de instrução de manipulação:**
```json
{
  "acao": "filtrar",
  "tipo": "categoria",
  "valor": "DMD",
  "secoes_afetadas": ["processos_chegando", "processos_prontos", "processos_em_dta"],
  "manter_estrutura": true
}
```

### **Persistência de Drafts**

**Similar a `EmailDraft`:**
- Salvar em SQLite (`chat_ia.db`)
- Tabela: `relatorio_drafts`
- Relacionar com `session_id`
- Limpar drafts antigos (TTL)

### **Emojis Contextuais**

**Mapeamento sugerido:**
- 🚢 = Transporte/Embarque
- ✅ = Pronto/Liberado
- ⚠️ = Atenção/Urgente
- 📝 = Documento/Processamento
- 🔍 = Análise/Verificação
- ⏱️ = Tempo/Mudança
- 🔔 = Notificação/Importante
- 📊 = Estatística/Resumo
- 📋 = Lista/Catálogo
- 💰 = Financeiro/Pagamento

---

## ✅ Próximos Passos

1. **Validar visão com usuário** ← Estamos aqui
2. **Implementar Passo 7.1** (RelatorioManipulationService básico)
3. **Testar filtros básicos**
4. **Implementar Passo 7.2** (Sistema de drafts)
5. **Integrar com sistema atual**
6. **Melhorar emojis (Passo 7.3)**
7. **Integração completa com email (Passo 7.4)**

---

**Última atualização:** 10/01/2026
