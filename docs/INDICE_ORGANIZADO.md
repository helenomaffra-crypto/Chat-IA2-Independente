# 📚 Índice Organizado de Documentações - mAIke Assistente

**Última atualização:** 12/01/2026  
**Estrutura:** Organizada por categorias para facilitar navegação

---

## 🎯 Estrutura de Pastas

```
Chat-IA-Independente/
├── README.md                    # 🔴 CRÍTICA - Visão geral
├── AGENTS.md                    # 🔴 CRÍTICA - Instruções para agentes
├── PROMPT_AMANHA.md            # 🔴 CRÍTICA - Tarefas diárias
│
└── docs/
    ├── essencial/              # 📌 Documentações essenciais (MAIS IMPORTANTES)
    │   ├── README.md           # Guia desta pasta
    │   ├── API_DOCUMENTATION.md
    │   ├── MANUAL_COMPLETO.md
    │   ├── MAPEAMENTO_SQL_SERVER.md
    │   └── REGRAS_NEGOCIO.md
    │
    ├── integracoes/            # 🔌 Integrações com APIs externas
    │   ├── INTEGRACAO_SANTANDER.md
    │   ├── INTEGRACAO_BANCO_BRASIL.md
    │   └── ASSISTANTS_API_LEGISLACAO.md
    │
    ├── funcionalidades/         # ⚙️ Funcionalidades específicas
    │   ├── NORMALIZACAO_TERMOS_CLIENTE.md
    │   ├── CATALOGO_DESPESAS_PADRAO.md
    │   ├── CODE_INTERPRETER_CALCULO_IMPOSTOS.md
    │   └── COMO_ACIONAR_CODE_INTERPRETER.md
    │
    ├── planejamento/            # 📋 Planejamentos e roadmaps
    │   ├── PLANEJAMENTO_BANCO_DADOS_MAIKE.md
    │   ├── ROADMAP_IMPLEMENTACAO_BANCO_DADOS.md
    │   └── RASTREAMENTO_ORIGEM_RECURSOS_COMEX.md
    │
    ├── explicacoes/            # 📖 Explicações e tutoriais
    │   ├── COMO_IA_DETECTA_MAPEAMENTO.md
    │   ├── COMO_PEDIR_REGRAS_CLIENTE_CATEGORIA.md
    │   ├── COMO_REGRAS_APARECEM_NO_PROMPT.md
    │   └── DIFERENCA_HISTORICO_VS_RELATORIO_TELA.md  # ✅ NOVO (12/01/2026): Diferença entre último histórico e último relatório em tela
    │
    ├── resumos/                # 📝 Resumos e executivos
    │   └── [vários resumos...]
    │
    └── arquivados/             # 🗄️ Documentos antigos/obsoletos
        └── [documentos arquivados...]
```

---

## 🔴 Documentações CRÍTICAS (Raiz do Projeto)

| Documento | Localização | Status | Descrição |
|-----------|-------------|--------|-----------|
| `README.md` | Raiz | ✅ | Documentação principal do projeto |
| `AGENTS.md` | Raiz | ✅ | Instruções para agentes de IA |
| `PROMPT_AMANHA.md` | Raiz | ✅ | Prompt de revisão diária |

**💡 Comece por aqui se você é novo no projeto!**

---

## 📌 Documentações ESSENCIAIS (`docs/essencial/`)

**Esta pasta contém apenas as documentações mais importantes para desenvolver e manter o sistema.**

### Para Desenvolvedores:

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `API_DOCUMENTATION.md` | ✅ | Documentação completa da API (todos os endpoints) |
| `MANUAL_COMPLETO.md` | ⚠️ | Manual completo do sistema (precisa revisar) |
| `MAPEAMENTO_SQL_SERVER.md` | ⚠️ | Estrutura completa do banco de dados |
| `REGRAS_NEGOCIO.md` | ✅ | Todas as regras de negócio do sistema |
| `ANALISE_COMPLETUDE_DOCUMENTACAO.md` | ✅ | Análise se documentação permite desenvolver do zero |
| `SISTEMA_CONTEXTO_PERSISTENTE.md` | ✅ | Sistema de contexto persistente entre mensagens |

**💡 Leia estas documentações para entender o sistema completamente.**

### 📋 Documentações de Refatoramento:

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `../BENEFICIOS_REFATORAMENTO_PASSO_3_5.md` | ✅ **NOVO (12/01/2026)** | Análise completa dos benefícios do Passo 3.5 |
| `../O_QUE_FALTA_PASSO_3_5.md` | ✅ | O que falta para finalizar o Passo 3.5 |
| `../PASSO_3_5_PLANO_IMPLEMENTACAO.md` | ✅ | Plano detalhado do Passo 3.5 |
| `../REFATORACAO_RESUMO_COMPLETO.md` | ✅ | Resumo completo do progresso de refatoração |

**💡 Consulte para entender a arquitetura refatorada e os benefícios obtidos.**

---

## 🔌 Integrações (`docs/integracoes/`)

**Documentações específicas de integrações com APIs externas.**

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `INTEGRACAO_SANTANDER.md` | ✅ | Integração com Santander Open Banking |
| `INTEGRACAO_BANCO_BRASIL.md` | ✅ | Integração com Banco do Brasil |
| `ASSISTANTS_API_LEGISLACAO.md` | ✅ | Assistants API para legislação (RAG) |

**💡 Consulte quando precisar implementar ou manter integrações.**

---

## ⚙️ Funcionalidades (`docs/funcionalidades/`)

**Documentações de funcionalidades específicas do sistema.**

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `NORMALIZACAO_TERMOS_CLIENTE.md` | ✅ | Sistema de normalização cliente→categoria |
| `CATALOGO_DESPESAS_PADRAO.md` | ✅ | Catálogo de despesas padrão (23 tipos) |
| `CODE_INTERPRETER_CALCULO_IMPOSTOS.md` | ✅ | Code Interpreter para cálculos |
| `COMO_ACIONAR_CODE_INTERPRETER.md` | ✅ | Como acionar Code Interpreter |

**💡 Consulte quando precisar entender ou modificar funcionalidades específicas.**

---

## 📋 Planejamento (`docs/planejamento/`)

**Planejamentos, roadmaps e estratégias futuras.**

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `PLANEJAMENTO_BANCO_DADOS_MAIKE.md` | ✅ | Planejamento completo do banco SQL Server |
| `ROADMAP_IMPLEMENTACAO_BANCO_DADOS.md` | ✅ | Roadmap de implementação por fases |
| `RASTREAMENTO_ORIGEM_RECURSOS_COMEX.md` | ✅ | Rastreamento de recursos (compliance) |

**💡 Consulte para entender o planejamento futuro do sistema.**

---

## 📖 Explicações (`docs/explicacoes/`)

**Explicações didáticas e tutoriais sobre como as coisas funcionam.**

| Documento | Status | Descrição |
|-----------|--------|-----------|
| `COMO_IA_DETECTA_MAPEAMENTO.md` | ✅ | Como a IA detecta mapeamentos cliente→categoria |
| `COMO_PEDIR_REGRAS_CLIENTE_CATEGORIA.md` | ✅ | Como pedir regras corretamente no chat |
| `COMO_REGRAS_APARECEM_NO_PROMPT.md` | ✅ | Como regras aparecem no prompt da IA |

**💡 Consulte para entender como as coisas funcionam internamente.**

---

## 📝 Resumos (`docs/resumos/`)

**Resumos executivos e resumos de implementações.**

**💡 Consulte para ter uma visão rápida de implementações passadas.**

---

## 🗄️ Arquivados (`docs/arquivados/`)

**Documentos antigos, obsoletos ou que não são mais relevantes.**

**💡 Mantidos apenas para referência histórica.**

---

## 🎯 Como Navegar

### Para Desenvolvedores Novos:

1. **Comece por:**
   - `README.md` (raiz)
   - `AGENTS.md` (raiz)
   - `docs/essencial/API_DOCUMENTATION.md`

2. **Depois leia:**
   - `docs/essencial/MANUAL_COMPLETO.md`
   - `docs/essencial/MAPEAMENTO_SQL_SERVER.md`
   - `docs/essencial/REGRAS_NEGOCIO.md`

3. **Consulte quando precisar:**
   - `docs/integracoes/` - Para integrações
   - `docs/funcionalidades/` - Para funcionalidades específicas
   - `docs/explicacoes/` - Para entender como funciona

### Para Usuários:

1. **Comece por:**
   - `README.md` (raiz)
   - `docs/essencial/MANUAL_COMPLETO.md`

2. **Consulte quando precisar:**
   - `docs/funcionalidades/NORMALIZACAO_TERMOS_CLIENTE.md` - Como criar regras
   - `docs/funcionalidades/CATALOGO_DESPESAS_PADRAO.md` - Como usar despesas

---

## 📊 Estatísticas

- **Documentações críticas (raiz):** 3
- **Documentações essenciais:** ~12
- **Documentações de refatoramento:** ~4
- **Integrações:** ~3
- **Funcionalidades:** ~4
- **Planejamentos:** ~3
- **Explicações:** ~3
- **Total organizado:** ~32 documentações principais

---

## 🔄 Manutenção

### Quando Adicionar Nova Documentação:

1. **Se for crítica/essencial:**
   - Adicione em `docs/essencial/`
   - Atualize este índice

2. **Se for integração:**
   - Adicione em `docs/integracoes/`
   - Atualize este índice

3. **Se for funcionalidade específica:**
   - Adicione em `docs/funcionalidades/`
   - Atualize este índice

4. **Se for explicação/tutorial:**
   - Adicione em `docs/explicacoes/`
   - Atualize este índice

5. **Se for resumo:**
   - Adicione em `docs/resumos/`
   - Atualize este índice

### Quando Arquivar Documentação:

- Documento obsoleto ou não mais relevante
- Documento substituído por versão mais nova
- Documento de teste/debug que não é mais necessário

---

**Última atualização:** 12/01/2026

