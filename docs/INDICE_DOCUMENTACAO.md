# 📚 Índice da Documentação

**Última atualização:** 19/12/2025

**💾 Cópia de Segurança:** `Chat-IA-Independente -V1012` (backup completo de 10/12/2025)

---

## 🎯 Documentos Principais

### 📋 Documentação Técnica
- **`MANUAL_COMPLETO.md`** ⭐⭐⭐ - **MANUAL COMPLETO DO SISTEMA** (versão 1.6, 19/12/2025) - Guia completo de todas as funcionalidades, funções disponíveis, exemplos de uso e regras importantes
- **`API_DOCUMENTATION.md`** ⭐ - Documentação completa da API (endpoints, autenticação, APIs externas)
- **`integracoes/MERCANTE_AFRMM.md`** 🚢 - Automação de pagamento AFRMM no Mercante (RPA + comprovante/print)
- **`FLUXO_DESPACHO_ADUANEIRO.md`** - Fluxo completo de despacho aduaneiro e significado das datas
- **`REFATORACAO_PRODUCAO.md`** - Recomendações de refatoração para produção
- **`ESPECIFICACAO_O_QUE_TEMOS_PRA_HOJE.md`** 📅 - Especificação da funcionalidade "O QUE TEMOS PRA HOJE" (dashboard consolidado do dia)
- **`REGRAS_NEGOCIO.md`** 📋 - Documentação completa de todas as regras de negócio da aplicação
- **`MAPEAMENTO_SQL_SERVER.md`** 📊 - Mapeamento completo das tabelas SQL Server e como buscar dados
- **`SUGESTOES_MELHORIAS_SQL_SERVER.md`** 🚀 - Sugestões de melhorias no SQL Server para refatoração (21/12/2025)
- **`ANALISE_DOCUMENTOS.md`** 📋 - Análise dos documentos do projeto (obsoletos, desatualizados, úteis)

---

## 🔧 Documentação de Desenvolvimento

### 📖 Documentação de API
- **`API_DOCUMENTATION.md`** ⭐ - Documentação completa da API REST
  - Endpoints públicos e internos
  - Autenticação e segurança
  - APIs externas utilizadas (Integra Comex, Portal Único, Kanban)
  - Configuração de ambiente (validação/produção)
  - Ajuste automático de CE por ambiente
  - Variáveis de ambiente necessárias
  - Exemplos de uso

### 🔄 Fluxos e Processos
- **`FLUXO_DESPACHO_ADUANEIRO.md`** - Fluxo completo de despacho aduaneiro
  - Significado de cada data (ETA, chegada, armazenamento, desembaraço)
  - Diferença entre datas de chegada e entrega
  - Situações de CE (DESCARREGADA, CARREGADA, ENTREGUE)
  - Processo de registro de DI/DUIMP

### 🚀 Preparação para Produção
- **`REFATORACAO_PRODUCAO.md`** - Guia de refatoração para produção
  - Itens críticos (segurança, credenciais)
  - Itens importantes (validação, logging, rate limiting)
  - Melhorias opcionais (monitoramento, testes)
  - Checklist de deploy

### 📅 Funcionalidades Futuras
- **`ESPECIFICACAO_O_QUE_TEMOS_PRA_HOJE.md`** - Especificação da funcionalidade "O QUE TEMOS PRA HOJE"
  - Dashboard consolidado do dia
  - Processos chegando hoje, prontos para registro, pendências
  - Alertas proativos e sugestões de ações
  - Priorização inteligente
  - Queries SQL e estrutura de implementação
  - Checklist completo de implementação

### 📚 Exemplos e Tutoriais
- **`EXEMPLOS_FUNCIONALIDADES_IA.md`** ⭐ - Exemplos práticos de uso das funcionalidades de IA
  - Aprendizado de regras (learned_rules_service)
  - Contexto persistente de sessão (context_service)
  - Consultas analíticas SQL (analytical_query_service)
  - Consultas salvas (saved_queries_service)
  - Casos de uso reais e fluxos completos
  - Dicas de uso e boas práticas

- **`PLANO_TTS_NOTIFICACOES.md`** 🎤 - Plano de implementação de TTS (Text-to-Speech) para notificações
  - Análise de viabilidade técnica
  - Integração com OpenAI TTS API
  - Estratégias para múltiplas notificações simultâneas
  - Arquitetura proposta e roadmap de implementação
  - Análise de custos e considerações técnicas

- **`REGRAS_NEGOCIO.md`** 📋 - Documentação completa de regras de negócio
  - Regras de chegada de processos
  - Regras de pendências (ICMS, AFRMM, LPCO, Frete)
  - Regras de status/situação (DI, DUIMP, CE)
  - Regras de notificações
  - Regras de ETA
  - Regras de categorização
  - Regras de processos prontos para registro
  - Checklist de validação

---

## 📝 Changelog

### Versão 1.2.0 - 10/12/2025

#### 🆕 Novas Funcionalidades
- ✅ **Dashboard "O QUE TEMOS PRA HOJE"**: Dashboard consolidado com processos chegando hoje, prontos para registro, pendências ativas, DUIMPs em análise, ETA alterado, alertas recentes e sugestões de ações
- ✅ **Sistema de Ajuda**: Comando "ajuda" ou "help" mostra guia completo de funcionalidades
- ✅ **Histórico de ETA**: Detecta mudanças de ETA comparando primeiro e último evento ARRV do porto de destino

#### 🔧 Melhorias
- ✅ **Agrupamento Inteligente**: Processos agrupados por categoria e tipo de pendência para melhor legibilidade
- ✅ **Controle de Atraso de Registro**: Calcula e destaca processos com atraso crítico (>7 dias) ou moderado (3-7 dias)
- ✅ **Priorização de ETA**: Prioriza eventos DISC (Discharge) no porto de destino, depois dataPrevisaoChegada, depois ARRV
- ✅ **Suporte a Categorias Alfanuméricas**: Aceita categorias como "MV5" (não apenas letras)
- ✅ **Precheck de Comandos**: Detecção prioritária de comandos críticos antes do processamento da IA

#### 🐛 Correções
- ✅ **Correção de Cálculo de Atraso de ETA**: Compara corretamente ETA original vs atual do porto de destino final (ignora escalas intermediárias)
- ✅ **Correção de Interpretação de Comandos**: "registrar duimp" não é mais interpretado como busca por processos "registrados"
- ✅ **Correção de Confirmação de DUIMP**: Sistema sempre mostra resumo antes de criar DUIMP
- ✅ **Correção de Filtro de Pendências**: Pendências agora são filtradas corretamente
- ✅ **Correção de Alertas Recentes**: Mostra status atual em vez de apenas "Status alterado"
- ✅ **Validação de LPCO**: Processos com LPCO não deferido não aparecem em "prontos para registro"
- ✅ **Regra Legal ICMS**: ICMS só é considerado pendente após desembaraço da DI/DUIMP

#### 📚 Documentação
- ✅ **Atualização de README**: Versão atualizada para 1.2.0 com todas as funcionalidades de hoje
- ✅ **Referência de Backup**: Documentada cópia de segurança `Chat-IA-Independente -V1012`

**💾 Cópia de Segurança:** `Chat-IA-Independente -V1012` (backup completo de 10/12/2025)

---

## 📁 Estrutura de Arquivos

```
docs/
├── MANUAL_COMPLETO.md                # ⭐⭐⭐ Manual completo do sistema (v1.6)
├── API_DOCUMENTATION.md              # 📚 Documentação completa da API
├── integracoes/
│   ├── MERCANTE_AFRMM.md              # 🚢 Mercante - Pagamento AFRMM (RPA + comprovante)
├── FLUXO_DESPACHO_ADUANEIRO.md       # 🔄 Fluxo de despacho aduaneiro
├── REFATORACAO_PRODUCAO.md           # 🚀 Guia de refatoração para produção
├── ESPECIFICACAO_O_QUE_TEMOS_PRA_HOJE.md  # 📅 Especificação "O QUE TEMOS PRA HOJE"
├── PLANO_TTS_NOTIFICACOES.md         # 🎤 Plano de implementação de TTS
├── REGRAS_NEGOCIO.md                 # 📋 Regras de negócio completas
├── MAPEAMENTO_SQL_SERVER.md         # 📊 Mapeamento de tabelas SQL Server
├── SUGESTOES_MELHORIAS_SQL_SERVER.md # 🚀 Sugestões de melhorias no SQL Server
├── ANALISE_DOCUMENTOS.md            # 📋 Análise dos documentos do projeto
├── EXEMPLOS_FUNCIONALIDADES_IA.md   # 📚 Exemplos práticos de uso
├── ESPECIFICACAO_BANCO_LEGISLACOES.md # 📚 Especificação de banco de legislações
├── ESPECIFICACAO_UPLOAD_LEGISLACOES.md # 📚 Especificação de upload de legislações
├── arquivados/                       # 📦 Documentos obsoletos arquivados
└── INDICE_DOCUMENTACAO.md            # 📚 Este arquivo (índice)
```

---

## 🔍 Busca Rápida

### Quer saber sobre...

- **Documentação da API?** → `API_DOCUMENTATION.md`
- **Endpoints disponíveis?** → `API_DOCUMENTATION.md` (seção "Endpoints")
- **APIs externas utilizadas?** → `API_DOCUMENTATION.md` (seção "APIs Externas Utilizadas")
- **Configuração de ambiente (validação/produção)?** → `API_DOCUMENTATION.md` (seção "Configuração de Ambiente para DUIMP")
- **Ajuste automático de CE?** → `API_DOCUMENTATION.md` (seção "Ajuste de CE por Ambiente")
- **Fluxo de despacho aduaneiro?** → `FLUXO_DESPACHO_ADUANEIRO.md`
- **Significado das datas?** → `FLUXO_DESPACHO_ADUANEIRO.md`
- **Preparação para produção?** → `REFATORACAO_PRODUCAO.md`
- **Itens críticos de segurança?** → `REFATORACAO_PRODUCAO.md` (seção "CRÍTICO")
- **Checklist de deploy?** → `REFATORACAO_PRODUCAO.md` (seção "Checklist de Deploy")
- **Regras de negócio?** → `REGRAS_NEGOCIO.md`
- **Quando ICMS é pendente?** → `REGRAS_NEGOCIO.md` (seção "2.1. Pendência de ICMS")
- **Como detectar chegada?** → `REGRAS_NEGOCIO.md` (seção "1. Regras de Chegada de Processos")
- **Quando criar notificações?** → `REGRAS_NEGOCIO.md` (seção "4. Regras de Notificações")

---

## 📊 Documentos por Categoria

### 🔌 Integração e APIs
- **`API_DOCUMENTATION.md`**
  - Endpoints da aplicação
  - Integração com Integra Comex (SERPRO)
  - Integração com Portal Único Siscomex
  - Integração com API Kanban (interna)
  - Autenticação e configuração

### 🔄 Processos e Fluxos
- **`FLUXO_DESPACHO_ADUANEIRO.md`**
  - Fluxo completo de importação
  - Significado de cada etapa
  - Datas e situações importantes

### 🛠️ Desenvolvimento e Manutenção
- **`REFATORACAO_PRODUCAO.md`**
  - Melhorias de segurança
  - Otimizações de performance
  - Boas práticas

---

## 🔑 Informações Importantes

### Variáveis de Ambiente Críticas

#### DUIMP (Portal Único)
- `DUIMP_ALLOW_WRITE_PROD=1` - Habilita criação de DUIMP em produção (padrão: bloqueado)
- `PUCOMEX_BASE_URL` - URL base do Portal Único (padrão: produção)

#### Segurança
- `SECRET_KEY` - Chave secreta do Flask (obrigatória em produção)
- `FLASK_DEBUG=false` - Desabilita modo debug em produção

#### Integra Comex
- Certificado PKCS#12 (.pfx)
- Client ID e Client Secret OAuth2

### Ajuste Automático de CE

- **Validação:** CE ajustado (últimos 2 dígitos → "02")
  - Exemplo: `132505371482300` → `132505371482302`
- **Produção:** CE completo (15 dígitos sem alteração)
  - Exemplo: `132505371482300` → `132505371482300`

---

## 📝 Changelog da Documentação

### 21/12/2025 - Sugestões de Melhorias SQL Server
- ✅ **Novo documento:** `SUGESTOES_MELHORIAS_SQL_SERVER.md`
  - Análise completa dos problemas identificados no SQL Server
  - Sugestões prioritárias de melhorias (normalização, índices, views)
  - Roadmap de implementação em 3 fases
  - Impacto esperado: 50-70% mais rápido em queries de processo

### 19/12/2025 - Versão 1.6
- ✅ **Manual Completo atualizado** (`MANUAL_COMPLETO.md` versão 1.6)
  - Adicionada seção detalhada sobre **Contexto de Processo (processo_atual)**
  - Documentadas regras sobre **Follow-up de Processo**
  - Documentadas regras sobre **Perguntas de Painel**
  - Esclarecidas regras sobre quando o contexto é salvo e usado
  - Novo exemplo prático de follow-up usando contexto
- ✅ **Refatoração do PrecheckService documentada**
  - `EmailPrecheckService` - Prechecks especializados em email
  - `ProcessoPrecheckService` - Prechecks especializados em processos
  - `NcmPrecheckService` - Prechecks especializados em NCM
  - Helpers: `processo_helpers.py` com `eh_pergunta_painel()` e `eh_followup_processo()`
- ✅ **Análise de Documentos** (`ANALISE_DOCUMENTOS.md`)
  - Identificação de documentos obsoletos (13 arquivados)
  - Documentos que precisam atualização
  - Documentos úteis para manter
- ✅ **Documentos obsoletos arquivados** em `docs/arquivados/`
  - 13 documentos de implementação/correção já concluídos foram movidos

### 10/12/2025 - Versão 1.2.0
- ✅ **Implementação completa do Dashboard "O QUE TEMOS PRA HOJE"**
  - Dashboard consolidado do dia com processos chegando hoje, prontos para registro, pendências ativas, DUIMPs em análise, ETA alterado, alertas recentes e sugestões de ações
  - Agrupamento inteligente por categoria e tipo de pendência
  - Controle de atraso de registro (crítico, moderado, recentes)
  - Validação de LPCO e regra legal de ICMS
  - Histórico de ETA (detecta mudanças comparando primeiro e último evento ARRV do porto de destino)
  - Filtro de processos ativos (não mostra processos antigos)
- ✅ **Sistema de Ajuda**: Comando "ajuda" ou "help" mostra guia completo
- ✅ **Melhorias e Correções**: Suporte a categorias alfanuméricas, priorização de ETA, precheck de comandos, correções de bugs
- ✅ **Atualização de README**: Versão atualizada para 1.2.0 com todas as funcionalidades
- ✅ **Referência de Backup**: Documentada cópia de segurança `Chat-IA-Independente -V1012`

**💾 Cópia de Segurança:** `Chat-IA-Independente -V1012` (backup completo de 10/12/2025)

### 15/01/2025
- ✅ Adicionada especificação "O QUE TEMOS PRA HOJE" (`ESPECIFICACAO_O_QUE_TEMOS_PRA_HOJE.md`)
  - Dashboard consolidado do dia
  - Processos chegando hoje, prontos para registro, pendências
  - Alertas proativos e sugestões de ações
  - Queries SQL e estrutura de implementação completa

### 09/12/2025
- ✅ Adicionada documentação completa da API (`API_DOCUMENTATION.md`)
- ✅ Adicionado guia de refatoração para produção (`REFATORACAO_PRODUCAO.md`)
- ✅ Mantido fluxo de despacho aduaneiro (`FLUXO_DESPACHO_ADUANEIRO.md`)
- ✅ Atualizado índice da documentação
- ✅ Removidas referências a documentos desatualizados

---

**Última atualização:** 19/12/2025
