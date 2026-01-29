# 🔄 Instruções de Continuidade - Para Novos Agentes

**Data:** 07/01/2026  
**Objetivo:** Garantir que qualquer agente possa continuar o trabalho sem contexto anterior

---

## 🎯 COMO CONTINUAR O TRABALHO

Se você é um **novo agente** continuando este projeto:

### Passo 1: Ler Documentos Essenciais (ORDEM IMPORTANTE)

1. **`PROMPT_AMANHA.md`** ⭐ **LEIA PRIMEIRO**
   - Contém TODO o contexto necessário
   - Checklist completo de tarefas
   - Status de todas as documentações

2. **`README.md`** ⭐ **SEGUNDO**
   - Visão geral do projeto
   - Estrutura do projeto
   - Funcionalidades principais
   - Como usar

3. **`docs/INDICE_DOCUMENTACOES.md`** ⭐ **TERCEIRO**
   - Lista TODAS as documentações
   - Status de cada uma
   - Última data de atualização

### Passo 2: Entender o Contexto Atual

**Sobre o Projeto:**
- **Nome:** Chat IA Independente - mAIke Assistente
- **Tipo:** Sistema de chat conversacional com IA especializado em COMEX
- **Status:** ✅ Funcionando (versão 1.7.1)
- **Tecnologias:** Python, Flask, SQL Server, SQLite, OpenAI API

**O que foi feito hoje (07/01/2026):**
- ✅ Planejamento completo de banco de dados SQL Server
- ✅ Sistema de notificações humanizadas e proativas
- ✅ Sistema de backup local
- ✅ Índice de documentações
- ✅ Prompt de continuidade (este documento)

**Tarefas Pendentes:**
- ⏳ Revisar documentações criadas hoje
- ⏳ Verificar documentações antigas que podem estar desatualizadas
- ⏳ Implementar planejamento de banco de dados (futuro)
- ⏳ Implementar sistema de notificações humanizadas (futuro)

### Passo 3: Seguir o Checklist

**Ver `PROMPT_AMANHA.md` para checklist completo**

---

## 📚 DOCUMENTAÇÕES MAIS IMPORTANTES

### Para Entender o Projeto:
- `README.md` - Documentação principal
- `AGENTS.md` - Como funciona a arquitetura de agents

### Para Trabalhos Específicos:

**Banco de Dados:**
- `docs/PLANEJAMENTO_BANCO_DADOS_MAIKE.md` - Planejamento completo (CRIADO HOJE)
- `docs/MAPEAMENTO_SQL_SERVER.md` - Mapeamento de tabelas existentes

**Notificações:**
- `docs/SISTEMA_NOTIFICACOES_HUMANIZADAS.md` - Sistema de notificações (CRIADO HOJE)

**APIs:**
- `docs/API_DOCUMENTATION.md` - Documentação completa da API
- `docs/INTEGRACAO_SANTANDER.md` - Integração Santander
- `docs/INTEGRACAO_BANCO_BRASIL.md` - Integração Banco do Brasil

**Índice Completo:**
- `docs/INDICE_DOCUMENTACOES.md` - Lista TODAS as documentações

---

## 🔍 ESTRUTURA DO PROJETO (Resumo)

```
Chat-IA-Independente/
├── app.py                          # Aplicação Flask principal
├── ai_service.py                   # Serviço de IA
├── db_manager.py                   # Gerenciador SQLite
├── services/                       # Serviços do sistema
│   ├── agents/                     # Agents especializados
│   ├── chat_service.py             # Serviço principal do chat
│   └── ...
├── utils/                          # Utilitários
├── templates/                      # Templates HTML
├── docs/                           # Documentações
├── scripts/                        # Scripts utilitários
│   └── fazer_backup.sh            # Script de backup
├── backups/                        # Backups locais
├── README.md                       # Documentação principal
├── PROMPT_AMANHA.md                # Prompt de revisão diária
├── INSTRUCOES_CONTINUIDADE.md      # Este documento
└── ...
```

---

## 💡 DICAS IMPORTANTES

### Ao Fazer Mudanças:

1. **Sempre ler primeiro** o código/documentação antes de modificar
2. **Testar mudanças** antes de considerar concluído
3. **Atualizar documentações** quando fizer mudanças importantes
4. **Atualizar `PROMPT_AMANHA.md`** quando completar tarefas
5. **Atualizar `docs/INDICE_DOCUMENTACOES.md`** quando criar/atualizar docs

### Ao Criar Novas Funcionalidades:

1. Documentar no `README.md`
2. Adicionar ao `docs/INDICE_DOCUMENTACOES.md`
3. Atualizar `PROMPT_AMANHA.md` com o que foi feito
4. Criar backup antes de mudanças grandes

### Ao Encontrar Problemas:

1. Verificar logs
2. Consultar documentações relacionadas
3. Verificar se há documentação de troubleshooting
4. Se resolver, documentar a solução

---

## 🔄 FLUXO DE TRABALHO RECOMENDADO

```
1. Ler PROMPT_AMANHA.md
   ↓
2. Ler README.md (seção relevante)
   ↓
3. Ler documentação específica (se necessário)
   ↓
4. Seguir checklist do PROMPT_AMANHA.md
   ↓
5. Fazer mudanças
   ↓
6. Testar mudanças
   ↓
7. Atualizar documentações
   ↓
8. Atualizar PROMPT_AMANHA.md
   ↓
9. Criar backup (se mudanças grandes)
```

---

## 📝 NOTAS FINAIS

- Este documento foi criado para garantir **continuidade entre sessões/agentes**
- Sempre atualize este documento quando melhorar o processo
- Sempre atualize `PROMPT_AMANHA.md` quando completar tarefas
- Mantenha documentações sempre atualizadas

---

**Última atualização:** 07/01/2026  
**Versão:** 1.0

