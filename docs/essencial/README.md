# 📚 Documentações Essenciais - mAIke Assistente

**Última atualização:** 08/01/2026

Esta pasta contém **apenas as documentações mais importantes e críticas** para desenvolver, manter e usar o sistema mAIke.

---

## 🎯 Para Quem é Esta Pasta?

### ✅ **Desenvolvedores Novos no Projeto**
- Comece por aqui para entender o sistema
- Documentações essenciais para implementar funcionalidades
- Guias passo a passo

### ✅ **Desenvolvedores Mantendo o Sistema**
- Referência rápida das funcionalidades principais
- Arquitetura e estrutura
- APIs e integrações

### ✅ **Usuários Avançados**
- Manual completo de uso
- Como criar regras e personalizar
- Funcionalidades avançadas

---

## 📋 Documentações Essenciais

### 🔴 **CRÍTICAS (Comece Por Aqui)**

1. **`../README.md`** (raiz do projeto)
   - Visão geral do projeto
   - Setup e instalação
   - Funcionalidades principais

2. **`../AGENTS.md`** (raiz do projeto)
   - Arquitetura completa
   - Como criar agents
   - Convenções de código

3. **`../PROMPT_AMANHA.md`** (raiz do projeto)
   - Tarefas diárias
   - Status do projeto
   - Próximos passos

### 📌 **IMPORTANTES (Leia Depois)**

4. **`API_DOCUMENTATION.md`**
   - Todos os endpoints da API
   - Exemplos de requisição/resposta
   - Integrações externas

5. **`MANUAL_COMPLETO.md`**
   - Manual completo de uso
   - Todas as funcionalidades
   - Exemplos práticos

6. **`MAPEAMENTO_SQL_SERVER.md`**
   - Estrutura completa do banco de dados
   - Tabelas e relacionamentos
   - Queries de referência

7. **`REGRAS_NEGOCIO.md`**
   - Todas as regras de negócio
   - Quando e como aplicar
   - Exceções e casos especiais

8. **`SISTEMA_CONTEXTO_PERSISTENTE.md`** ⭐ **NOVO (08/01/2026)**
   - Sistema de contexto persistente entre mensagens
   - Como manter contexto automaticamente
   - Como adicionar novos tipos de contexto
   - Boas práticas e troubleshooting
   - Manual completo para implementações futuras

9. **`ANALISE_COMPLETUDE_DOCUMENTACAO.md`**
   - Análise da documentação
   - O que está completo
   - O que falta

### 📋 Documentações de Refatoramento (Em `docs/`)

10. **`../BENEFICIOS_REFATORAMENTO_PASSO_3_5.md`** ⭐ **NOVO (12/01/2026)**
    - Análise completa dos benefícios do Passo 3.5
    - Métricas de melhoria (modularidade, testabilidade, reutilização)
    - Comparação antes vs. depois
    - Benefícios práticos imediatos
    - **Status:** ✅ Fase 3.5.1 e 3.5.2 completas

11. **`../O_QUE_FALTA_PASSO_3_5.md`**
    - O que falta para finalizar o Passo 3.5
    - Status de cada fase
    - Próximos passos recomendados

12. **`../PASSO_3_5_PLANO_IMPLEMENTACAO.md`**
    - Plano detalhado do Passo 3.5
    - Arquitetura proposta
    - Fases de implementação

### 🔗 **Documentações Relacionadas (Em Outras Pastas)**

**Integrações:** `../integracoes/`
- `INTEGRACAO_SANTANDER.md`
- `INTEGRACAO_BANCO_BRASIL.md`
- `ASSISTANTS_API_LEGISLACAO.md`

**Funcionalidades:** `../funcionalidades/`
- `NORMALIZACAO_TERMOS_CLIENTE.md`
- `CATALOGO_DESPESAS_PADRAO.md`
- `CODE_INTERPRETER_CALCULO_IMPOSTOS.md`

**Planejamento:** `../planejamento/`
- `PLANEJAMENTO_BANCO_DADOS_MAIKE.md`
- `ROADMAP_IMPLEMENTACAO_BANCO_DADOS.md`
- `RASTREAMENTO_ORIGEM_RECURSOS_COMEX.md`

---

## 📁 Estrutura de Documentações

```
Chat-IA-Independente/
├── README.md                    # 🔴 CRÍTICA (raiz)
├── AGENTS.md                    # 🔴 CRÍTICA (raiz)
├── PROMPT_AMANHA.md            # 🔴 CRÍTICA (raiz)
├── docs/
│   ├── essencial/              # 📌 Documentações essenciais (ESTA PASTA)
│   │   ├── README.md           # Este arquivo
│   │   ├── API_DOCUMENTATION.md
│   │   ├── MANUAL_COMPLETO.md
│   │   ├── MAPEAMENTO_SQL_SERVER.md
│   │   ├── REGRAS_NEGOCIO.md
│   │   └── [outras essenciais...]
│   │
│   ├── integracoes/            # 🔌 Integrações específicas
│   │   ├── INTEGRACAO_SANTANDER.md
│   │   ├── INTEGRACAO_BANCO_BRASIL.md
│   │   └── ASSISTANTS_API_LEGISLACAO.md
│   │
│   ├── funcionalidades/        # ⚙️ Funcionalidades específicas
│   │   ├── NORMALIZACAO_TERMOS_CLIENTE.md
│   │   ├── CATALOGO_DESPESAS_PADRAO.md
│   │   ├── CODE_INTERPRETER_CALCULO_IMPOSTOS.md
│   │   └── [outras funcionalidades...]
│   │
│   ├── planejamento/            # 📋 Planejamentos e roadmaps
│   │   ├── PLANEJAMENTO_BANCO_DADOS_MAIKE.md
│   │   ├── ROADMAP_IMPLEMENTACAO_BANCO_DADOS.md
│   │   └── [outros planejamentos...]
│   │
│   ├── explicacoes/            # 📖 Explicações e tutoriais
│   │   ├── COMO_IA_DETECTA_MAPEAMENTO.md
│   │   ├── COMO_PEDIR_REGRAS_CLIENTE_CATEGORIA.md
│   │   ├── COMO_REGRAS_APARECEM_NO_PROMPT.md
│   │   └── [outras explicações...]
│   │
│   ├── resumos/                # 📝 Resumos e executivos
│   │   └── [resumos diversos...]
│   │
│   └── arquivados/             # 🗄️ Documentos antigos/obsoletos
│       └── [documentos arquivados...]
```

---

## 🎯 Como Usar Esta Pasta

### Para Desenvolvedores Novos:

1. **Comece por:**
   - `../README.md` (raiz)
   - `../AGENTS.md` (raiz)
   - `API_DOCUMENTATION.md`

2. **Depois leia:**
   - `MANUAL_COMPLETO.md`
   - `MAPEAMENTO_SQL_SERVER.md`
   - `REGRAS_NEGOCIO.md`

3. **Consulte quando precisar:**
   - Documentações específicas de integrações
   - Documentações de funcionalidades específicas

### Para Usuários:

1. **Comece por:**
   - `../README.md` (raiz)
   - `MANUAL_COMPLETO.md`

2. **Consulte quando precisar:**
   - `NORMALIZACAO_TERMOS_CLIENTE.md` - Como criar regras
   - `CATALOGO_DESPESAS_PADRAO.md` - Como usar despesas

---

## 📊 Estatísticas

- **Total de documentações essenciais:** ~19
- **Documentações críticas:** 3 (README, AGENTS, PROMPT_AMANHA)
- **Documentações importantes:** ~13
- **Documentações de refatoramento:** ~3

---

**Última atualização:** 12/01/2026

