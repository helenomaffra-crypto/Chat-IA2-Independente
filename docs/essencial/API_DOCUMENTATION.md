# 📚 Documentação da API - Chat IA Independente

**Versão:** 1.11  
**Data:** 08/01/2026  
**Base URL:** `http://localhost:5001` (desenvolvimento) / `https://seu-dominio.com` (produção)

**✅ Última atualização:** 08/01/2026 - Adicionados endpoints de sincronização bancária, conciliação e streaming de chat

---

## 📋 Índice

1. [Endpoints Públicos](#endpoints-públicos)
2. [Endpoints de Chat](#endpoints-de-chat)
3. [Endpoints de Notificações](#endpoints-de-notificações)
4. [Endpoints de Sistema](#endpoints-de-sistema)
5. [Endpoints de Banco](#-endpoints-de-banco-novo---07012026-atualizado-08012026) ⭐ **NOVO**
6. [Endpoints de Download](#-endpoints-de-download)
7. [Endpoints Internos](#endpoints-internos)
8. [APIs Externas Utilizadas](#apis-externas-utilizadas)
9. [Códigos de Erro](#códigos-de-erro)
10. [Arquitetura e Serviços](#arquitetura-e-serviços)
11. [Sistema de Aprendizado e Contexto Persistente](#-sistema-de-aprendizado-e-contexto-persistente)

---

## 🌐 Endpoints Públicos

### `GET /`
**Descrição:** Página inicial - redireciona para a interface de chat.

**Resposta:**
- **Tipo:** HTML
- **Status:** 200 OK
- **Body:** Template `chat-ia-isolado.html`

---

### `GET /chat-ia`
**Descrição:** Interface do Chat IA - interface isolada estilo WhatsApp.

**Resposta:**
- **Tipo:** HTML
- **Status:** 200 OK
- **Body:** Template `chat-ia-isolado.html`

---

## 💬 Endpoints de Chat

### `POST /api/chat`
**Descrição:** Endpoint principal para chat com IA - processa comandos em linguagem natural (resposta completa).

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "mensagem": "string (obrigatório)",
  "historico": [
    {
      "mensagem": "string",
      "resposta": "string",
      "session_id": "string (opcional, adicionado automaticamente)"
    }
  ],
  "executar_acao": boolean (opcional, default: false),
  "model": "string (opcional)",
  "temperature": number (opcional, 0.0-2.0),
  "session_id": "string (opcional, padrão: IP do cliente)"
}
```

**⚠️ IMPORTANTE - Session ID:**
- O `session_id` é usado para manter contexto persistente entre mensagens
- Se não fornecido, usa `request.remote_addr` (IP do cliente)
- Contexto salvo inclui: processos mencionados, categorias em foco, últimas consultas
- Contexto persiste até você limpar ou iniciar nova sessão

**Exemplo de Requisição:**
```json
{
  "mensagem": "qual a situação do processo ALH.0165/25?",
  "historico": [],
  "executar_acao": true
}
```

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "resposta": "string (resposta da IA)",
  "tool_calling": [
    {
      "nome": "string",
      "argumentos": {}
    }
  ],
  "nome_usuario": "string (opcional)",
  "contexto": {}
}
```

**Resposta de Erro (400 Bad Request):**
```json
{
  "sucesso": false,
  "erro": "MENSAGEM_VAZIA",
  "mensagem": "Mensagem não pode ser vazia"
}
```

**Resposta de Erro (500 Internal Server Error):**
```json
{
  "sucesso": false,
  "erro": "SERVICO_INDISPONIVEL",
  "mensagem": "Serviço de chat não disponível: [detalhes do erro]"
}
```

**Funcionalidades:**
- Processa mensagens em linguagem natural
- Suporta consultas sobre processos, CEs, CCTs, DIs, DUIMPs
- Criação de DUIMPs
- Aprendizado de nomes de usuários
- Aprendizado dinâmico de categorias de processos
- Tool calling para execução de ações

**APIs Externas Chamadas:**
- **Integra Comex (SERPRO):** Consultas de CE, DI, ETA
- **Portal Único:** Criação/consulta de DUIMP, consulta de CCT
- **API Kanban:** Consulta de processos de importação
- **OpenAI Assistants API:** ✅ NOVO (05/01/2026) - Busca semântica de legislação (RAG)

---

### `POST /api/chat/stream` ⭐ **NOVO (05/01/2026)**
**Descrição:** Endpoint para chat com IA usando streaming (Server-Sent Events) - envia respostas em tempo real conforme são geradas.

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "mensagem": "string (obrigatório)",
  "historico": [
    {
      "mensagem": "string",
      "resposta": "string",
      "session_id": "string (opcional)"
    }
  ],
  "model": "string (opcional)",
  "temperature": number (opcional, 0.0-2.0),
  "session_id": "string (opcional, padrão: IP do cliente)"
}
```

**Resposta:**
- **Tipo:** `text/event-stream` (Server-Sent Events)
- **Status:** 200 OK (streaming)
- **Formato:** Cada evento é uma linha JSON com prefixo `data: `

**Exemplo de Eventos:**
```
data: {"tipo": "inicio", "mensagem": "Iniciando processamento..."}

data: {"tipo": "chunk", "conteudo": "O processo"}

data: {"tipo": "chunk", "conteudo": " ALH.0165/25"}

data: {"tipo": "chunk", "conteudo": " está"}

data: {"tipo": "chunk", "conteudo": " em"}

data: {"tipo": "chunk", "conteudo": " desembaraço."}

data: {"tipo": "fim", "resposta_completa": "O processo ALH.0165/25 está em desembaraço.", "tool_calling": [...]}
```

**Tipos de Eventos:**
- `inicio`: Processamento iniciado
- `chunk`: Fragmento da resposta (texto incremental)
- `fim`: Processamento concluído (resposta completa + tool_calling)
- `erro`: Erro durante processamento

**Vantagens:**
- ✅ Resposta em tempo real (melhor UX)
- ✅ Usuário vê resposta sendo gerada
- ✅ Reduz percepção de latência
- ✅ Mesma funcionalidade do endpoint `/api/chat` normal

**⚠️ Configuração de Ambiente para DUIMP:**

A criação de DUIMP suporta dois ambientes:

1. **Validação (padrão):**
   - Base URL: `https://val.portalunico.siscomex.gov.br`
   - **Ajuste de CE:** Últimos 2 dígitos substituídos por "02" (ex: `132505371482300` → `132505371482302`)
   - **Motivo:** API de validação só aceita CEs terminados em 01-09 (modelos de teste)
   - **Uso:** Recomendado para testes

2. **Produção:**
   - Base URL: `https://portalunico.siscomex.gov.br`
   - **Ajuste de CE:** CE completo de 15 dígitos sem alteração (ex: `132505371482300` → `132505371482300`)
   - **Habilitação:** Requer variável de ambiente `DUIMP_ALLOW_WRITE_PROD=1` no `.env`
   - **Uso:** Apenas para casos específicos com autorização

**Variável de Ambiente:**
```env
DUIMP_ALLOW_WRITE_PROD=1  # Habilita criação em produção (padrão: bloqueado)
```

**Comportamento:**
- Se `DUIMP_ALLOW_WRITE_PROD` não estiver definido ou for `0`: criação em produção é bloqueada
- Se `DUIMP_ALLOW_WRITE_PROD=1`: criação em produção é permitida
- O ajuste do CE é automático conforme o ambiente selecionado

---

### `POST /api/chat/stream`
**Descrição:** Endpoint para chat com IA usando streaming (Server-Sent Events) - respostas em tempo real.

**⚠️ NOVO (05/01/2026):** Este endpoint envia respostas da IA conforme são geradas, melhorando significativamente a experiência do usuário.

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "mensagem": "string (obrigatório)",
  "historico": [
    {
      "mensagem": "string",
      "resposta": "string",
      "session_id": "string (opcional)"
    }
  ],
  "model": "string (opcional)",
  "temperature": number (opcional, 0.0-2.0),
  "session_id": "string (opcional, padrão: IP do cliente)",
  "nome_usuario": "string (opcional)"
}
```

**Resposta (Server-Sent Events - SSE):**
```
data: {"type": "chunk", "chunk": "texto parcial da resposta", "index": 1}
data: {"type": "chunk", "chunk": "mais texto...", "index": 2}
data: {"type": "done", "resposta_final": "resposta completa", "tool_calling": [...]}
```

**Exemplo de Requisição:**
```bash
curl -X POST http://localhost:5001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "mensagem": "qual a situação do processo ALH.0165/25?",
    "historico": []
  }'
```

**Funcionalidades:**
- ✅ Respostas em tempo real (streaming)
- ✅ Suporta tool calling (ferramentas são executadas após streaming)
- ✅ Melhor experiência do usuário (não precisa aguardar resposta completa)
- ✅ Compatível com todas as funcionalidades do endpoint `/api/chat`

**Diferenças do `/api/chat`:**
- **Resposta:** Streaming (SSE) vs JSON completo
- **UX:** Resposta incremental vs resposta única
- **Performance:** Percepção de velocidade melhorada

**Nota:** O frontend (`templates/chat-ia-isolado.html`) usa automaticamente este endpoint quando disponível, com fallback para `/api/chat` se necessário.

---

### `GET /api/chat/status`
**Descrição:** Verifica o status do serviço de chat e disponibilidade da IA.

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "ia_habilitada": true,
  "provedor": "openai",
  "chat_disponivel": true
}
```

**Resposta de Erro (500 Internal Server Error):**
```json
{
  "sucesso": false,
  "erro": "string (mensagem de erro)"
}
```

---

## 🔔 Endpoints de Notificações

### `GET /api/notificacoes`
**Descrição:** Busca notificações do sistema (polling).

**Query Parameters:**
- `apenas_nao_lidas` (opcional, default: `true`): `true` ou `false`
- `limite` (opcional, default: `50`): número máximo de notificações a retornar

**Exemplo de Requisição:**
```
GET /api/notificacoes?apenas_nao_lidas=true&limite=20
```

**Resposta de Sucesso (200 OK):**
```json
{
  "success": true,
  "notificacoes": [
    {
      "id": 1,
      "processo_referencia": "ALH.0165/25",
      "tipo_notificacao": "chegada_confirmada",
      "titulo": "Processo chegou",
      "mensagem": "O processo ALH.0165/25 chegou ao porto.",
      "dados_extras": {},
      "criado_em": "2025-12-09T18:00:00",
      "lida": false
    }
  ],
  "total": 1
}
```

**Resposta de Erro (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "string (mensagem de erro)",
  "notificacoes": []
}
```

**Tipos de Notificação:**
- `chegada_confirmada`: Processo chegou ao porto
- `di_registrada`: DI foi registrada
- `duimp_registrada`: DUIMP foi registrada
- `ce_situacao_mudou`: Situação do CE mudou
- `cct_situacao_mudou`: Situação do CCT mudou
- `pendencia_resolvida`: Pendência foi resolvida
- `eta_mudou`: ETA do processo mudou

---

### `POST /api/notificacoes/<notificacao_id>/marcar-lida`
**Descrição:** Marca uma notificação como lida.

**Path Parameters:**
- `notificacao_id` (obrigatório): ID da notificação

**Exemplo de Requisição:**
```
POST /api/notificacoes/1/marcar-lida
```

**Resposta de Sucesso (200 OK):**
```json
{
  "success": true
}
```

**Resposta de Erro (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "string (mensagem de erro)"
}
```

---

## ⚙️ Endpoints de Sistema

### `GET /health`
**Descrição:** Health check endpoint para monitoramento.

**Resposta (200 OK):**
```json
{
  "status": "healthy",
  "service": "chat-ia-independente"
}
```

---

### `GET /api/config`
**Descrição:** Retorna configurações do sistema (modelo de IA atual, etc).

**Resposta de Sucesso (200 OK):**
```json
{
  "model": "gpt-3.5-turbo",
  "success": true
}
```

**Resposta de Erro (500 Internal Server Error):**
```json
{
  "error": "string (mensagem de erro)",
  "model": "gpt-3.5-turbo"
}
```

---

## 📥 Endpoints de Download

### `GET /api/download/<filename>`
**Descrição:** Download de arquivos (PDFs de extratos, etc).

**Path Parameters:**
- `filename` (obrigatório): Nome do arquivo (ex: `Extrato-DI-2527284816.pdf`)

**Exemplo de Requisição:**
```
GET /api/download/Extrato-DI-2527284816.pdf
```

---

## 🏦 Endpoints de Banco (NOVO - 07/01/2026, ATUALIZADO 08/01/2026)

### `POST /api/banco/sincronizar`
**Descrição:** Sincroniza extratos bancários do Banco do Brasil ou Santander para SQL Server.

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "banco": "BB",                    // Opcional (default: "BB") - "BB" ou "SANTANDER"
  "agencia": "1251",                // Obrigatório para BB, opcional para Santander
  "conta": "50483",                 // Obrigatório para BB, opcional para Santander
  "data_inicio": "2026-01-01",     // Opcional (default: 7 dias atrás)
  "data_fim": "2026-01-07",        // Opcional (default: hoje)
  "dias_retroativos": 7            // Opcional (usado se datas não fornecidas)
}
```

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "total": 50,
  "novos": 47,
  "duplicados": 1,
  "erros": 2,
  "processos_detectados": ["BGR.0070/25", "BGR.0069/25"],
  "resposta": "📊 Importação de Extrato Bancário\n\nConta: SANTANDER Ag. 3003 C/C 000130827180\nTotal processado: 50 lançamentos\n\nResultado:\n• ✅ Novos inseridos: 47\n• ⏭️ Duplicados (pulados): 1\n• ❌ Erros: 2"
}
```

**Resposta de Erro (400/500):**
```json
{
  "sucesso": false,
  "erro": "BANCO_INVALIDO" | "PARAMETROS_FALTANDO" | "ERRO_INTERNO",
  "mensagem": "Descrição do erro"
}
```

**Funcionalidades:**
- ✅ Detecção automática de duplicatas usando hash SHA-256
- ✅ Detecção automática de processos nas descrições de transações
- ✅ Suporte a Banco do Brasil e **Santander** (08/01/2026)
- ✅ Para Santander: Detecção automática de conta quando não especificada
- ✅ Descrição completa de lançamentos (transactionName + historicComplement) para Santander
- ✅ Suporte a múltiplos formatos de data do Santander (YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY)

**⚠️ Tratamento de Erros:**
- Se ocorrer erro de timeout durante sincronização, o usuário deve sincronizar novamente quando o SQL Server estiver acessível
- Duplicatas são detectadas automaticamente (não há problema em sincronizar novamente)

---

### `GET /api/banco/lancamentos-nao-classificados`
**Descrição:** Lista lançamentos bancários que não estão classificados (sem tipo de despesa vinculado).

**Query Parameters:**
- `limite` (opcional, default: `50`): Número máximo de lançamentos a retornar

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "lancamentos": [
    {
      "id_movimentacao": 123,
      "banco_origem": "SANTANDER",
      "agencia_origem": "3003",
      "conta_origem": "000130827180",
      "data_movimentacao": "2026-01-08",
      "valor": 17465.73,
      "sinal": "-",
      "descricao": "PIX ENVIADO - RIO BRASIL TERMINAL",
      "processo_vinculado": null,
      "eh_possivel_imposto_importacao": false,
      "requer_confirmacao": false
    }
  ]
}
```

**✅ NOVO (08/01/2026):** Descrição completa inclui `transactionName + historicComplement` para lançamentos do Santander.

---

### `GET /api/banco/lancamentos-classificados`
**Descrição:** Lista lançamentos bancários que já estão classificados (para permitir edição).

**Query Parameters:**
- `limite` (opcional, default: `50`): Número máximo de lançamentos a retornar

**Resposta:** Similar a `/api/banco/lancamentos-nao-classificados`, mas apenas lançamentos já classificados.

---

### `GET /api/banco/tipos-despesa`
**Descrição:** Lista todos os tipos de despesa disponíveis no catálogo.

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "tipos": [
    {
      "id_tipo_despesa": 1,
      "nome_despesa": "Frete Internacional",
      "descricao": "Frete marítimo ou aéreo internacional",
      "categoria_despesa": "FRETE",
      "ativo": true
    }
  ]
}
```

---

### `GET /api/banco/impostos-processo/<processo_referencia>`
**Descrição:** Busca impostos sugeridos de um processo (da DI/DUIMP) para preencher automaticamente na conciliação.

**Path Parameters:**
- `processo_referencia` (obrigatório): Referência do processo (ex: `GLT.0045/25`)

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "processo_referencia": "GLT.0045/25",
  "impostos_sugeridos": [
    {
      "tipo": "II",
      "nome": "Imposto de Importação",
      "valor": 23094.63,
      "codigo_receita": "0086"
    },
    {
      "tipo": "IPI",
      "nome": "Imposto sobre Produtos Industrializados",
      "valor": 0.0,
      "codigo_receita": "1038"
    }
  ],
  "total_impostos": 23094.63
}
```

---

### `POST /api/banco/classificar-lancamento`
**Descrição:** Classifica um lançamento bancário vinculando-o a tipos de despesa e processos.

**Body (JSON):**
```json
{
  "id_movimentacao": 123,
  "classificacoes": [
    {
      "id_tipo_despesa": 1,
      "processo_referencia": "BGR.0070/25",
      "valor": 5000.00
    }
  ],
  "distribuicao_impostos": {
    "processo_referencia": "GLT.0045/25",
    "impostos": {
      "II": 23094.63,
      "IPI": 0.0,
      "PIS": 0.0,
      "COFINS": 0.0
    }
  }
}
```

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "resposta": "✅ Lançamento classificado com sucesso"
}
```

---

### `GET /api/banco/lancamentos-nao-vinculados`
**Descrição:** Lista lançamentos bancários que não estão vinculados a nenhum processo.

**Query Parameters:**
- `limite` (opcional, default: `50`): Número máximo de lançamentos a retornar
- `data_inicio` (opcional, formato: `YYYY-MM-DD`): Data inicial do filtro
- `data_fim` (opcional, formato: `YYYY-MM-DD`): Data final do filtro

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "lancamentos": [
    {
      "id_movimentacao": 123,
      "banco_origem": "BB",
      "agencia_origem": "1251",
      "conta_origem": "50483",
      "data_movimentacao": "2026-01-08",
      "valor": 5000.00,
      "sinal": "-",
      "descricao": "PIX ENVIADO - MASSY DO BRASIL COMERCIO",
      "processo_vinculado": null
    }
  ],
  "total": 15
}
```

---

### `POST /api/banco/vincular`
**Descrição:** Vincula um lançamento bancário a um processo de importação.

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "id_movimentacao": 12345,
  "processo_referencia": "DMD.0083/25",
  "tipo_relacionamento": "PAGAMENTO_FRETE"  // Opcional
}
```

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "resposta": "✅ Lançamento vinculado ao processo DMD.0083/25 com sucesso"
}
```

**Resposta de Erro (400/500):**
```json
{
  "sucesso": false,
  "erro": "PARAMETROS_FALTANDO" | "ERRO_INTERNO",
  "mensagem": "Descrição do erro"
}
```

---

### `GET /api/banco/resumo-processo/<processo_referencia>`
**Descrição:** Obtém resumo de movimentações bancárias vinculadas a um processo específico.

**Path Parameters:**
- `processo_referencia` (obrigatório): Referência do processo (ex: `DMD.0083/25`)

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "processo_referencia": "DMD.0083/25",
  "total_lancamentos": 5,
  "total_credito": 100000.00,
  "total_debito": 50000.00,
  "saldo_liquido": 50000.00,
  "lancamentos": [
    {
      "id_movimentacao": 123,
      "data_movimentacao": "2026-01-08",
      "valor": 5000.00,
      "sinal": "-",
      "descricao": "PIX ENVIADO - MASSY DO BRASIL COMERCIO"
    }
  ]
}
```

---

### `GET /api/banco/lancamento/<id_movimentacao>/classificacoes`
**Descrição:** Obtém um lançamento bancário com todas as suas classificações (para edição).

**Path Parameters:**
- `id_movimentacao` (obrigatório): ID do lançamento

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "lancamento": {
    "id_movimentacao": 123,
    "descricao": "PIX ENVIADO - RIO BRASIL TERMINAL",
    "valor": 17465.73,
    "classificacoes": [
      {
        "id_classificacao": 1,
        "id_tipo_despesa": 1,
        "processo_referencia": "BGR.0070/25",
        "valor": 5000.00
      }
    ]
  }
}
```

---

### `GET /api/banco/classificacoes/<id_movimentacao>`
**Descrição:** Obtém todas as classificações de um lançamento (alias para `/api/banco/lancamento/<id_movimentacao>/classificacoes`).

**Path Parameters:**
- `id_movimentacao` (obrigatório): ID do lançamento

**Resposta:** Mesma estrutura de `/api/banco/lancamento/<id_movimentacao>/classificacoes`

---

### `GET /api/config/contas-bancarias`
**Descrição:** Lista contas bancárias configuradas (Banco do Brasil e Santander) para sincronização.

**Resposta de Sucesso (200 OK):**
```json
{
  "sucesso": true,
  "contas": [
    {
      "banco": "BB",
      "nome": "BB - Ag. 1251 - C/C 50483",
      "agencia": "1251",
      "conta": "50483",
      "id": "bb_conta1"
    },
    {
      "banco": "BB",
      "nome": "BB - Ag. 1251 - C/C 43344",
      "agencia": "1251",
      "conta": "43344",
      "id": "bb_conta2"
    },
    {
      "banco": "SANTANDER",
      "nome": "SANTANDER - Ag. 3003 - C/C 000130827180",
      "agencia": "3003",
      "conta": "000130827180",
      "id": "santander_conta1"
    }
  ]
}
```

---

**Resposta de Sucesso (200 OK):**
- **Tipo:** `application/pdf`
- **Body:** Arquivo PDF

**Resposta de Erro (403 Forbidden):**
```json
{
  "sucesso": false,
  "erro": "Acesso negado"
}
```

**Resposta de Erro (404 Not Found):**
```json
{
  "sucesso": false,
  "erro": "Arquivo não encontrado"
}
```

**Segurança:**
- Apenas arquivos do diretório `downloads/` são permitidos
- Proteção contra path traversal (../)

---

## 🔧 Endpoints Internos

### `POST /api/int/classif/baixar-nomenclatura`
**Descrição:** Baixa o arquivo JSON da nomenclatura do Portal Único e processa no cache local.

**Body (JSON):**
```json
{
  "forcar_download": false
}
```

**Resposta de Sucesso (200 OK):**
```json
{
  "success": true,
  "mensagem": "Nomenclatura processada com sucesso",
  "estatisticas": {
    "total_ncms": 12345,
    "ncms_processados": 12345,
    "tempo_processamento": "2.5s"
  }
}
```

**Resposta de Erro (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "string (mensagem de erro)"
}
```

**Funcionalidade:**
- Faz download do arquivo JSON da nomenclatura do Portal Único
- Processa e extrai informações de NCM (código, descrição)
- Salva no cache local (SQLite) - tabela `classif_cache`
- Retorna estatísticas do processamento

**API Externa Chamada:**
- **Portal Único:** `GET /nomenclatura/nomenclatura.json`

---

## 🌐 APIs Externas Utilizadas

A aplicação integra com várias APIs externas oficiais do governo brasileiro. Esta seção documenta quais APIs são chamadas por cada endpoint da aplicação.

### 🔗 Integra Comex (SERPRO)

**Base URL:** Configurável via `.env` (padrão: ambiente de validação/produção do SERPRO)  
**Autenticação:** OAuth2 + mTLS (certificado PKCS#12)  
**⚠️ IMPORTANTE:** API BILHETADA (paga por consulta)

#### Endpoints Utilizados:

| Endpoint Integra Comex | Chamado Por | Descrição |
|------------------------|-------------|-----------|
| `GET /carga/conhecimento-embarque/{numeroCE}` | `POST /api/chat` (consultas de CE) | Consulta CE marítimo |
| `GET /declaracao-importacao/{numeroDI}` | `POST /api/chat` (consultas de DI) | Consulta Declaração de Importação |
| `GET /carga/conhecimento-embarque/{numeroCE}/previsao-atracacao` | `POST /api/chat` (consultas de ETA) | Consulta previsão de atracação do CE |

**Exemplo de Fluxo:**
```
Usuário: "extrato CE 132505371482300"
  ↓
POST /api/chat
  ↓
services/agents/ce_agent.py
  ↓
utils/integracomex_proxy.py → call_integracomex()
  ↓
GET https://api.integracomex.gov.br/carga/conhecimento-embarque/132505371482300
  ↓
Resposta → Usuário
```

---

### 🔗 Portal Único Siscomex

**Base URL:** `https://portalunico.siscomex.gov.br` (configurável via `PUCOMEX_BASE_URL`)  
**Autenticação:** mTLS (certificado PKCS#12) + CSRF Token  
**Ambientes:** Validação e Produção

#### Endpoints Utilizados:

| Endpoint Portal Único | Chamado Por | Descrição |
|----------------------|-------------|-----------|
| `POST /duimp-api/api/ext/duimp` | `POST /api/chat` (criação de DUIMP) | Cria capa da DUIMP |
| `GET /duimp-api/api/ext/duimp/{numero}/{versao}` | `POST /api/chat` (consultas de DUIMP) | Consulta DUIMP |
| `PUT /duimp-api/api/ext/duimp/{numero}/{versao}` | `POST /api/chat` (atualização de DUIMP) | Atualiza DUIMP |
| `GET /duimp-api/api/ext/ccta/{awb}` | `POST /api/chat` (consultas de CCT) | Consulta CCT (Conhecimento de Carga Aérea) |
| `GET /nomenclatura/nomenclatura.json` | `POST /api/int/classif/baixar-nomenclatura` | Download da nomenclatura fiscal (NCM) |

**Exemplo de Fluxo:**
```
Usuário: "criar duimp do vdm.0004/25"
  ↓
POST /api/chat
  ↓
services/agents/duimp_agent.py
  ↓
utils/portal_proxy.py → call_portal()
  ↓
POST https://portalunico.siscomex.gov.br/duimp-api/api/ext/duimp
  ↓
Resposta → Usuário
```

---

### 🔗 API Kanban (Interna)

**Base URL:** `http://172.16.10.211:5000/api/kanban/pedidos`  
**Autenticação:** Nenhuma (API interna)  
**Descrição:** API interna da empresa para consulta de processos de importação

#### Endpoints Utilizados:

| Endpoint Kanban | Chamado Por | Descrição |
|----------------|-------------|-----------|
| `GET /api/kanban/pedidos` | `services/processo_kanban_service.py` | Sincronização de processos |
| `GET /api/kanban/pedidos?processo={ref}` | `POST /api/chat` (consultas de processos) | Consulta processo específico |

**Exemplo de Fluxo:**
```
Sincronização automática (background)
  ↓
services/processo_kanban_service.py
  ↓
GET http://172.16.10.211:5000/api/kanban/pedidos
  ↓
Salva em SQLite local (processos_kanban)
```

---

### 🔗 OpenAI Assistants API ✅ **NOVO (05/01/2026)**

**Base URL:** `https://api.openai.com/v1`  
**Autenticação:** API Key (Bearer Token)  
**Descrição:** API da OpenAI para busca semântica de legislação usando File Search (RAG)

#### Endpoints Utilizados:

| Endpoint OpenAI | Chamado Por | Descrição |
|----------------|-------------|-----------|
| `POST /assistants` | `scripts/configurar_assistants_legislacao.py` | Cria assistente com File Search |
| `POST /vector_stores` | `scripts/configurar_assistants_legislacao.py` | Cria vector store para arquivos |
| `POST /files` | `scripts/configurar_assistants_legislacao.py` | Upload de arquivos de legislação |
| `POST /threads` | `POST /api/chat` (busca de legislação) | Cria thread para busca |
| `POST /threads/{thread_id}/runs` | `POST /api/chat` (busca de legislação) | Executa busca no assistente |

**Exemplo de Fluxo:**
```
Usuário: "o que fala sobre perdimento em importação?"
  ↓
POST /api/chat
  ↓
services/agents/legislacao_agent.py
  ↓
services/assistants_service.py → buscar_legislacao()
  ↓
OpenAI Assistants API → File Search (RAG)
  ↓
Resposta contextualizada → Usuário
```

**Configuração:**
- Requer `OPENAI_ASSISTANT_ID` e `OPENAI_VECTOR_STORE_ID` no `.env`
- Script de configuração: `scripts/configurar_assistants_legislacao.py`
- Documentação completa: `docs/ASSISTANTS_API_LEGISLACAO.md`

**Custos:**
- File Search pode ter custos adicionais dependendo do plano OpenAI
- Upload e indexação são gratuitos, mas podem levar tempo

---

### 🔗 Santander Open Banking ✅ **NOVO (06/01/2026)**

**Base URL:** `https://trust-open.api.santander.com.br`  
**Autenticação:** OAuth2 mTLS (certificado ICP-Brasil tipo A1)  
**Descrição:** API do Santander Open Banking para consulta de extratos, saldos e contas bancárias

#### Endpoints Utilizados:

| Endpoint Santander | Chamado Por | Descrição |
|-------------------|-------------|-----------|
| `GET /bank_account_information/v1/banks/{bank_id}/accounts` | `POST /api/chat` (listar contas) | Lista todas as contas disponíveis |
| `GET /bank_account_information/v1/banks/{bank_id}/statements/{statement_id}` | `POST /api/chat` (consultar extrato) | Consulta extrato bancário |
| `GET /bank_account_information/v1/banks/{bank_id}/balances/{balance_id}` | `POST /api/chat` (consultar saldo) | Consulta saldo real da conta |
| `POST /auth/oauth/v2/token` | `utils/santander_api.py` | Obter token OAuth2 |

**Exemplo de Fluxo:**
```
Usuário: "extrato santander"
  ↓
POST /api/chat
  ↓
services/agents/santander_agent.py
  ↓
services/santander_service.py → consultar_extrato()
  ↓
utils/santander_api.py → Santander Open Banking API
  ↓
Resposta → Usuário
```

**Configuração:**
- Requer certificado ICP-Brasil tipo A1 (`.pem` e `.key`)
- Variáveis de ambiente: `SANTANDER_CLIENT_ID`, `SANTANDER_CLIENT_SECRET`, `SANTANDER_CERT_FILE`, `SANTANDER_KEY_FILE`
- Documentação completa: `docs/INTEGRACAO_SANTANDER.md`

---

### 🔗 Banco do Brasil Extratos API ✅ **NOVO (06/01/2026)**

**Base URL:** `https://api-extratos.bb.com.br/extratos/v1`  
**Autenticação:** OAuth 2.0 Client Credentials (JWT token)  
**Ambientes:** Sandbox e Produção  
**Descrição:** API do Banco do Brasil para consulta de extratos bancários

#### Endpoints Utilizados:

| Endpoint Banco do Brasil | Chamado Por | Descrição |
|-------------------------|-------------|-----------|
| `GET /conta-corrente/agencia/{agencia}/conta/{conta}` | `POST /api/chat` (consultar extrato) | Consulta extrato bancário |
| `POST /oauth/token` | `utils/banco_brasil_api.py` | Obter token OAuth2 (via `https://oauth.bb.com.br/oauth/token`) |

**Exemplo de Fluxo:**
```
Usuário: "extrato bb"
  ↓
POST /api/chat
  ↓
Precheck detecta "extrato bb" → chama diretamente
  ↓
services/agents/banco_brasil_agent.py
  ↓
services/banco_brasil_service.py → consultar_extrato()
  ↓
utils/banco_brasil_api.py → Banco do Brasil Extratos API
  ↓
Resposta → Usuário
```

**Configuração:**
- Variáveis de ambiente: `BB_CLIENT_ID`, `BB_CLIENT_SECRET`, `BB_DEV_APP_KEY`, `BB_ENVIRONMENT`
- Valores padrão opcionais: `BB_TEST_AGENCIA`, `BB_TEST_CONTA`
- mTLS opcional: `BB_CERT_PATH` (apenas para APIs que requerem, como Pagamentos)
- Documentação completa: `docs/INTEGRACAO_BANCO_BRASIL.md`

**Características:**
- ✅ **OAuth 2.0 Client Credentials**: Autenticação mais simples que mTLS
- ✅ **Normalização Automática**: Remove zeros à esquerda de agência/conta
- ✅ **Precheck Automático**: Detecta pedidos de extrato BB antes da IA processar
- ✅ **Cadeia de Certificados**: Suporte para APIs mTLS quando necessário

---

### 📊 Mapa de Integração por Endpoint da Aplicação

#### `POST /api/chat`

**APIs Externas Chamadas (dependendo da mensagem):**

| Tipo de Consulta | API Externa | Endpoint |
|------------------|-------------|----------|
| Consulta de CE | Integra Comex | `GET /carga/conhecimento-embarque/{numeroCE}` |
| Consulta de DI | Integra Comex | `GET /declaracao-importacao/{numeroDI}` |
| Consulta de ETA | Integra Comex | `GET /carga/conhecimento-embarque/{numeroCE}/previsao-atracacao` |
| Criar DUIMP | Portal Único | `POST /duimp-api/api/ext/duimp` |
| Consultar DUIMP | Portal Único | `GET /duimp-api/api/ext/duimp/{numero}/{versao}` |
| Consultar CCT | Portal Único | `GET /duimp-api/api/ext/ccta/{awb}` |
| Consultar Extrato Santander | Santander Open Banking | `GET /bank_account_information/v1/banks/{bank_id}/statements/{statement_id}` |
| Consultar Saldo Santander | Santander Open Banking | `GET /bank_account_information/v1/banks/{bank_id}/balances/{balance_id}` |
| Consultar Extrato BB | Banco do Brasil | `GET /conta-corrente/agencia/{agencia}/conta/{conta}` |
| Consultar Processo | API Kanban | `GET /api/kanban/pedidos?processo={ref}` |
| Buscar Legislação (semântica) | OpenAI Assistants API | ✅ NOVO (05/01/2026) - Busca via File Search (RAG) |
| Consultar TECwin NCM | TECwin (Selenium) | Consulta via scraper - salva alíquotas no contexto |
| Calcular Impostos | CalculoImpostosService | ✅ NOVO (05/01/2026) - Usa alíquotas do contexto TECwin |

#### `POST /api/int/classif/baixar-nomenclatura`

**APIs Externas Chamadas:**

| API Externa | Endpoint |
|------------|----------|
| Portal Único | `GET /nomenclatura/nomenclatura.json` |

---

### 🔐 Autenticação

#### Integra Comex
- **Método:** OAuth2 + mTLS
- **Certificado:** PKCS#12 (.pfx)
- **Token:** OAuth2 access_token (renovado automaticamente)
- **Configuração:** Via `.env` (certificado, senha, client_id, client_secret)

#### Portal Único
- **Método:** mTLS + CSRF Token
- **Certificado:** PKCS#12 (.pfx)
- **Tokens:** SET Token + CSRF Token (renovados automaticamente)
- **Configuração:** Via `.env` (certificado, senha, ambiente)
- **Variáveis de Ambiente:**
  - `DUIMP_ALLOW_WRITE_PROD=1`: Habilita criação de DUIMP em produção (padrão: bloqueado)
  - `PUCOMEX_BASE_URL`: URL base do Portal Único (padrão: `https://portalunico.siscomex.gov.br`)
- **Ambientes:**
  - **Validação:** `https://val.portalunico.siscomex.gov.br` (padrão)
  - **Produção:** `https://portalunico.siscomex.gov.br` (requer `DUIMP_ALLOW_WRITE_PROD=1`)
- **Ajuste de CE por Ambiente:**
  - **Validação:** CE ajustado (últimos 2 dígitos → "02") - ex: `132505371482300` → `132505371482302`
  - **Produção:** CE completo (15 dígitos sem alteração) - ex: `132505371482300` → `132505371482300`

#### API Kanban
- **Método:** Nenhuma (API interna)
- **Configuração:** IP fixo (172.16.10.211:5000)

---

### ⚠️ Custos e Limitações

#### Integra Comex
- **Custo:** BILHETADA (paga por consulta)
- **Limitação:** Verificação de duplicata (não consulta mesmo CE/DI nos últimos 5 minutos)
- **Recomendação:** Sempre verificar API pública antes de consultar API bilhetada

#### Portal Único
- **Custo:** Gratuita (mas requer certificado válido)
- **Limitação:** Rate limiting não documentado (usar com moderação)
- **Ambientes:** Validação (testes) e Produção
- **Proteção de Produção:** Criação em produção é bloqueada por padrão (requer `DUIMP_ALLOW_WRITE_PROD=1`)
- **Ajuste Automático de CE:**
  - **Validação:** CE ajustado automaticamente (termina em "02") - ex: `132505371482300` → `132505371482302`
  - **Produção:** CE completo (15 dígitos) sem alteração - ex: `132505371482300` → `132505371482300`

#### API Kanban
- **Custo:** Nenhum (API interna)
- **Limitação:** Apenas acessível na rede interna da empresa

#### OpenAI Assistants API ✅ **NOVO (05/01/2026)**
- **Custo:** File Search pode ter custos adicionais dependendo do plano OpenAI
- **Limitação:** Upload e indexação podem levar tempo (processamento em background)
- **Vantagem:** Busca semântica inteligente que entende contexto e significado

---

## ❌ Códigos de Erro

### Erros Comuns

| Código HTTP | Código de Erro | Descrição |
|------------|----------------|-----------|
| 400 | `MENSAGEM_VAZIA` | Mensagem não pode ser vazia |
| 403 | `ACESSO_NEGADO` | Acesso negado ao arquivo |
| 404 | `ARQUIVO_NAO_ENCONTRADO` | Arquivo não encontrado |
| 500 | `SERVICO_INDISPONIVEL` | Serviço de chat não disponível |
| 500 | `ERRO_AO_ADICIONAR_CATEGORIA` | Erro ao adicionar categoria de processo |
| 500 | `TIMEOUT` | Timeout na requisição |
| 500 | `ERRO_GERAL` | Erro genérico do servidor |

---

## 📝 Exemplos de Uso

### Exemplo 1: Consultar Status de Processo
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "mensagem": "qual a situação do processo ALH.0165/25?",
    "historico": [],
    "executar_acao": true
  }'
```

### Exemplo 2: Criar DUIMP
```bash
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "mensagem": "criar duimp do vdm.0004/25",
    "historico": [],
    "executar_acao": true
  }'
```

### Exemplo 3: Buscar Notificações
```bash
curl -X GET "http://localhost:5001/api/notificacoes?apenas_nao_lidas=true&limite=10"
```

### Exemplo 4: Marcar Notificação como Lida
```bash
curl -X POST http://localhost:5001/api/notificacoes/1/marcar-lida
```

### Exemplo 5: Consultar TECwin e Calcular Impostos ✅ **NOVO (05/01/2026)**
```bash
# 1. Consultar NCM no TECwin (salva alíquotas no contexto)
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "mensagem": "tecwin 84145110",
    "historico": [],
    "session_id": "test-session-123"
  }'

# 2. Calcular impostos usando alíquotas do contexto
curl -X POST http://localhost:5001/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "mensagem": "calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283",
    "historico": [],
    "session_id": "test-session-123"
  }'
```

**Resultado esperado:**
- Sistema busca alíquotas do contexto (salvas na consulta TECwin anterior)
- Calcula automaticamente II, IPI, PIS, COFINS
- Retorna cálculo completo com explicação passo a passo (CIF, bases de cálculo, fórmulas)

---

## 🔒 Segurança

### Autenticação
- Atualmente não há autenticação implementada
- **Recomendação:** Implementar autenticação JWT ou sessão para produção

### Rate Limiting
- Atualmente não há rate limiting implementado
- **Recomendação:** Implementar rate limiting para evitar abuso

### Validação de Inputs
- Mensagens são validadas (não podem ser vazias)
- Arquivos são validados (apenas do diretório `downloads/`)
- **Recomendação:** Adicionar validação mais rigorosa de inputs

---

## 📊 Limites e Restrições

- **Tamanho máximo de mensagem:** Sem limite definido (recomendado: 10.000 caracteres)
- **Limite de histórico:** Sem limite definido (recomendado: 50 mensagens)
- **Timeout de requisição:** 120 segundos para `/api/chat`
- **Limite de notificações:** 50 por padrão (configurável via query parameter)

---

## 🏗️ Arquitetura e Serviços

Esta seção documenta os principais serviços, agentes e utilitários da aplicação, explicando o que cada um faz e suas responsabilidades.

### 🗺️ Mapa do Sistema

#### Fluxo de Processamento de Mensagens

```
┌─────────────────────────────────────────────────────────────┐
│                    POST /api/chat                            │
│                    (app.py)                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              ChatService.processar_mensagem()                │
│              (services/chat_service.py)                      │
│                                                              │
│  - Busca regras aprendidas                                  │
│  - Busca contexto de sessão                                 │
│  - Monta prompt com PromptBuilder                           │
│  - Chama PrecheckService                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              PrecheckService.tentar_responder_sem_ia()       │
│              (services/precheck_service.py)                  │
│                                                              │
│  Ordem de execução:                                         │
│  1. TECwin NCM → responder diretamente                     │
│  2. Follow-up contextual de processo                       │
│  3. Situação/detalhe de processo                            │
│  4. Email (delegado para EmailPrecheckService)             │
│  5. Perguntas de NCM                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         EmailPrecheckService.tentar_precheck_email()         │
│         (services/email_precheck_service.py)                │
│                                                              │
│  Hierarquia de decisão (ordem de prioridade):               │
│  1. Email de classificação NCM + alíquotas                  │
│  2. Email de relatório genérico                             │
│  3. Email de resumo/briefing                                │
│  4. Email livre (texto ditado)                              │
│  5. Email com informações de processo/NCM                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Se nenhum precheck processar:                   │
│              → IA (OpenAI/Anthropic)                        │
│              → Tool Calling                                 │
│              → ToolRouter → ToolExecutor → Agents            │
└─────────────────────────────────────────────────────────────┘
```

#### Camadas da Arquitetura

**Camada de Apresentação:**
- `app.py`: Endpoints Flask
- `templates/chat-ia-isolado.html`: Interface do usuário

**Camada de Orquestração:**
- `ChatService`: Orquestra todo o fluxo
- `PrecheckService`: Prechecks determinísticos (orquestrador)
- `EmailPrecheckService`: Prechecks de email
- `ProcessoPrecheckService`: Prechecks de processo
- `NcmPrecheckService`: Prechecks de NCM
- `ToolRouter`: Roteia tool calls
- `ToolExecutor`: Executa tools

**Camada de Negócio (Agents):**
- `ProcessoAgent`: Processos de importação
- `DuimpAgent`: DUIMP
- `CeAgent`: CE (Conhecimento de Embarque)
- `DiAgent`: DI (Declaração de Importação)
- `CctAgent`: CCT (Conhecimento de Carga Aérea)

**Camada de Serviços:**
- `ProcessoRepository`: Repositório unificado
- `ProcessoStatusService`: Status de processos
- `DuimpService`: Gestão de DUIMPs
- `EmailBuilderService`: Montagem de emails
- `EmailService`: Envio de emails
- `NCMService`: Operações com NCM
- `CalculoImpostosService`: ✅ NOVO (05/01/2026) - Cálculo automático de impostos após TECwin
- `ConsultaService`: Consultas de documentos
- `ConsultasBilhetadasService`: Gestão de consultas bilhetadas

**Camada de Infraestrutura:**
- `db_manager.py`: SQLite
- `sql_server_adapter.py`: SQL Server
- `portal_proxy.py`: Portal Único
- `integracomex_proxy.py`: Integra Comex
- `ai_service.py`: Serviço de IA

### 🤖 Agentes (Agents)

Os agentes são classes especializadas que implementam operações específicas de um domínio. Todos herdam de `BaseAgent` e são gerenciados pelo `ToolRouter`.

#### `ProcessoAgent` (`services/agents/processo_agent.py`)
**Responsabilidade:** Operações relacionadas a processos de importação.

**Tools suportadas:**
- `listar_processos`: Lista processos de importação
- `consultar_status_processo`: Consulta status detalhado de um processo
- `listar_processos_por_categoria`: Lista processos filtrados por categoria (ex: ALH, VDM, MV5)
- `listar_processos_por_situacao`: Lista processos filtrados por situação (ex: di_desembaracada, registrado)
- `listar_processos_por_eta`: Lista processos filtrados por ETA (previsão de chegada)
- `listar_processos_por_navio`: Lista processos filtrados por navio
- `listar_processos_liberados_registro`: Lista processos prontos para registro de DI/DUIMP
- `listar_processos_com_pendencias`: Lista processos com pendências (ICMS, frete, etc.)
- `listar_todos_processos_por_situacao`: Lista todos os processos por situação
- `consultar_processo_consolidado`: Consulta processo com dados consolidados de múltiplas fontes
- `listar_processos_com_duimp`: Lista processos que têm DUIMP

**APIs utilizadas:**
- API Kanban (interna): `http://172.16.10.211:5000/api/kanban/pedidos`
- SQLite (cache local): Tabela `processos_kanban`
- SQL Server (processos antigos): Via `sql_server_adapter.py`

---

#### `DuimpAgent` (`services/agents/duimp_agent.py`)
**Responsabilidade:** Operações relacionadas a DUIMP (Declaração Única de Importação).

**Tools suportadas:**
- `criar_duimp`: Cria uma DUIMP para um processo (extrai dados automaticamente do CE/CCT)
- `verificar_duimp_registrada`: Verifica se há DUIMP registrada para um processo
- `obter_dados_duimp`: Obtém dados completos de uma DUIMP
- `vincular_processo_duimp`: Vincula uma DUIMP a um processo
- `obter_extrato_pdf_duimp`: Obtém extrato PDF da DUIMP

**Funcionalidades especiais:**
- **Extração automática de dados:** Extrai CNPJ, CE/CCT, UL, país de procedência automaticamente
- **Ajuste de CE por ambiente:**
  - **Validação:** Ajusta últimos 2 dígitos do CE para "02" (API só aceita 01-09)
  - **Produção:** Usa CE completo de 15 dígitos sem alteração
- **Suporte a CE e CCT:** Funciona tanto para processos marítimos (CE) quanto aéreos (CCT)
- **Conversão IATA → ISO:** Converte código IATA de aeroporto para código de país ISO 3166-1 alpha-2

**APIs utilizadas:**
- Portal Único: `POST /duimp-api/api/ext/duimp` (criação)
- Portal Único: `GET /duimp-api/api/ext/duimp/{numero}/{versao}` (consulta)
- Integra Comex: `GET /carga/conhecimento-embarque/{numeroCE}` (dados do CE)
- Portal Único: `GET /duimp-api/api/ext/ccta/{awb}` (dados do CCT)

---

#### `CeAgent` (`services/agents/ce_agent.py`)
**Responsabilidade:** Operações relacionadas a CE (Conhecimento de Embarque marítimo).

**Tools suportadas:**
- `consultar_ce_maritimo`: Consulta CE marítimo (com cache e API bilhetada)
- `verificar_atualizacao_ce`: Verifica se CE precisa ser atualizado (API pública)
- `listar_processos_com_situacao_ce`: Lista processos com situação de CE (usando apenas cache - sem custo)
- `obter_extrato_ce`: Obtém extrato completo do CE

**⚠️ IMPORTANTE:** Nesta aplicação NÃO vinculamos manualmente. O sistema busca automaticamente o processo vinculado.

**APIs utilizadas:**
- Integra Comex: `GET /carga/conhecimento-embarque/{numeroCE}` (API bilhetada)
- Integra Comex: `GET /carga/conhecimento-embarque/{numeroCE}/previsao-atracacao` (ETA)

---

#### `CctAgent` (`services/agents/cct_agent.py`)
**Responsabilidade:** Operações relacionadas a CCT (Conhecimento de Carga Aérea).

**Tools suportadas:**
- `consultar_cct`: Consulta CCT (Conhecimento de Carga Aérea) via AWB
- `obter_extrato_cct`: Obtém extrato completo do CCT

**⚠️ IMPORTANTE:** Nesta aplicação NÃO vinculamos manualmente. O sistema busca automaticamente o processo vinculado.

**APIs utilizadas:**
- Portal Único: `GET /duimp-api/api/ext/ccta/{awb}` (consulta CCT via AWB)

---

#### `DiAgent` (`services/agents/di_agent.py`)
**Responsabilidade:** Operações relacionadas a DI (Declaração de Importação).

**Tools suportadas:**
- `obter_dados_di`: Obtém dados completos de uma DI
- `vincular_processo_di`: Vincula DI a um processo
- `obter_extrato_pdf_di`: Obtém extrato PDF da DI

**APIs utilizadas:**
- Integra Comex: `GET /declaracao-importacao/{numeroDI}` (API bilhetada)

---

#### `LegislacaoAgent` (`services/agents/legislacao_agent.py`) ✅ **NOVO (05/01/2026)**
**Responsabilidade:** Operações relacionadas a legislação (busca semântica e tradicional).

**Tools suportadas:**
- `buscar_legislacao_assistants`: ✅ NOVO - Busca legislação usando Assistants API com File Search (RAG)
  - Prioridade alta para perguntas conceituais (ex: "o que fala sobre perdimento?")
  - Busca semântica em todas as legislações importadas
  - Respostas contextualizadas combinando informações relevantes
- `buscar_em_todas_legislacoes`: Busca tradicional em SQLite por palavra-chave
  - Prioridade baixa para perguntas conceituais
  - Usado quando Assistants API não é adequada ou para buscas específicas

**Características:**
- ✅ Seleção automática de método de busca (IA escolhe o mais apropriado)
- ✅ Busca semântica entende contexto e significado
- ✅ Busca tradicional para palavras-chave específicas
- ✅ Indicadores claros na resposta mostrando qual método foi usado

**APIs utilizadas:**
- OpenAI Assistants API: Busca semântica com File Search
- SQLite: Busca tradicional por palavra-chave

---

#### `SantanderAgent` (`services/agents/santander_agent.py`) ✅ **NOVO (06/01/2026)**
**Responsabilidade:** Operações relacionadas a contas bancárias do Santander Open Banking.

**Tools suportadas:**
- `listar_contas_santander`: Lista todas as contas disponíveis no Santander Open Banking
- `consultar_extrato_santander`: Consulta extrato bancário com movimentações e saldo real
- `consultar_saldo_santander`: Consulta saldo real da conta (disponível, bloqueado, investido)

**Características:**
- ✅ **Detecção Automática**: Se o usuário não fornecer agência/conta, lista automaticamente as contas e usa a primeira disponível
- ✅ **Saldo Real**: Consulta saldo real via API (não apenas cálculo das transações)
- ✅ **Versão Independente**: Código integrado ao projeto, não depende de diretório externo
- ✅ **Autenticação mTLS**: OAuth2 com certificado ICP-Brasil tipo A1

**APIs utilizadas:**
- Santander Open Banking API: `https://trust-open.api.santander.com.br`
  - `GET /bank_account_information/v1/banks/{bank_id}/accounts` - Listar contas
  - `GET /bank_account_information/v1/banks/{bank_id}/statements/{statement_id}` - Consultar extrato
  - `GET /bank_account_information/v1/banks/{bank_id}/balances/{balance_id}` - Consultar saldo
  - `POST /auth/oauth/v2/token` - Obter token OAuth2

**Autenticação:**
- **Método:** OAuth2 mTLS (mutual TLS)
- **Certificado:** ICP-Brasil tipo A1
- **Token:** JWT renovado automaticamente (válido por 15 minutos)
- **Headers:** `Authorization: Bearer {token}`, `X-Application-Key: {client_id}`

**Configuração:**
- Variáveis de ambiente no `.env`:
  - `SANTANDER_CLIENT_ID`: Client ID do Portal do Desenvolvedor
  - `SANTANDER_CLIENT_SECRET`: Client Secret
  - `SANTANDER_CERT_FILE`: Caminho para certificado .pem
  - `SANTANDER_KEY_FILE`: Caminho para chave privada .key
  - `SANTANDER_BASE_URL`: URL base da API (padrão: produção)
  - `SANTANDER_BANK_ID`: CNPJ do banco (padrão: 90400888000142)

**Arquivos relacionados:**
- `utils/santander_api.py`: Cliente API do Santander (independente)
- `services/santander_service.py`: Wrapper para integração com mAIke
- `services/agents/santander_agent.py`: Agent para operações bancárias

**Documentação completa:** `docs/INTEGRACAO_SANTANDER.md`

---

#### `BancoBrasilAgent` (`services/agents/banco_brasil_agent.py`) ✅ **NOVO (06/01/2026)**
**Responsabilidade:** Operações relacionadas a contas bancárias do Banco do Brasil.

**Tools suportadas:**
- `consultar_extrato_bb`: Consulta extrato bancário com movimentações e saldo
  - Suporta período específico ou últimos 30 dias (padrão)
  - Ordenação automática: mais recentes primeiro (do presente para o passado)
  - Normalização automática: remove zeros à esquerda de agência/conta
  - Usa valores padrão do `.env` (`BB_TEST_AGENCIA`, `BB_TEST_CONTA`) se não fornecidos

**Características:**
- ✅ **OAuth 2.0 Client Credentials**: Autenticação mais simples que mTLS
- ✅ **Normalização Automática**: Remove zeros à esquerda de agência/conta (conforme especificação API)
- ✅ **Valores Padrão**: Usa `BB_TEST_AGENCIA` e `BB_TEST_CONTA` do `.env` quando não fornecidos
- ✅ **Ordenação Inteligente**: Transações ordenadas da mais recente para a mais antiga
- ✅ **Precheck Automático**: Detecta pedidos de extrato BB antes da IA processar
- ✅ **Cadeia de Certificados**: Suporte para APIs mTLS quando necessário (ex: Pagamentos)

**APIs utilizadas:**
- Banco do Brasil Extratos API: `https://api-extratos.bb.com.br/extratos/v1`
  - `GET /conta-corrente/agencia/{agencia}/conta/{conta}` - Consultar extrato
  - `POST /oauth/token` - Obter token OAuth2 (via `https://oauth.bb.com.br/oauth/token`)

**Autenticação:**
- **Método:** OAuth 2.0 Client Credentials
- **Token:** JWT renovado automaticamente (válido por 1 hora)
- **Headers:** `Authorization: Bearer {token}`, `gw-dev-app-key: {app_key}`
- **mTLS:** Opcional para API de Extratos (obrigatório para outras APIs como Pagamentos)

**Configuração:**
- Variáveis de ambiente no `.env`:
  - `BB_CLIENT_ID`: Client ID OAuth (JWT token)
  - `BB_CLIENT_SECRET`: Client Secret OAuth (JWT token)
  - `BB_DEV_APP_KEY`: Chave de acesso do aplicativo (gw-dev-app-key)
  - `BB_BASIC_AUTH`: (Opcional) Basic Auth pré-codificado
  - `BB_ENVIRONMENT`: `production` ou `sandbox` (padrão: `sandbox`)
  - `BB_TEST_AGENCIA`: (Opcional) Agência padrão para testes
  - `BB_TEST_CONTA`: (Opcional) Conta padrão para testes
  - `BB_CERT_PATH`: (Opcional) Caminho para certificado mTLS (para APIs que requerem)
  - `BB_CERT_FILE` / `BB_KEY_FILE`: (Opcional) Certificado e chave separados
  - `BB_PFX_PASSWORD`: (Opcional) Senha do certificado .pfx

**Arquivos relacionados:**
- `utils/banco_brasil_api.py`: Cliente API do Banco do Brasil (independente)
- `services/banco_brasil_service.py`: Wrapper para integração com mAIke
- `services/agents/banco_brasil_agent.py`: Agent para operações bancárias
- `.secure/certificados_bb/`: Scripts para criação de cadeia de certificados

**Documentação completa:** `docs/INTEGRACAO_BANCO_BRASIL.md`

---

#### `BaseAgent` (`services/agents/base_agent.py`)
**Responsabilidade:** Classe base abstrata para todos os agentes.

**Funcionalidades:**
- Define interface comum (`execute()`)
- Validação de argumentos
- Formatação de respostas
- Logging de execuções

---

### 🔧 Serviços Principais

#### `ChatService` (`services/chat_service.py`)
**Responsabilidade:** Serviço principal de chat com IA - processa mensagens em linguagem natural.

**Principais funcionalidades:**
1. **Processamento de mensagens em linguagem natural:**
   - Interpreta comandos e perguntas em português
   - Identifica intenções do usuário automaticamente
   - Executa ações baseadas no contexto da conversa
   - Suporta múltiplos modelos de IA (GPT-3.5, GPT-4, etc.)

2. **Gestão de processos de importação:**
   - Consulta de status de processos (ALH, VDM, MSS, BND, DMD, GYM, SLL, MV5, etc.)
   - Listagem por categoria, situação, ETA, pendências, bloqueios
   - Extração automática de referências de processo da mensagem
   - Contexto inteligente entre mensagens

3. **Criação automática de DUIMP:**
   - Detecta quando usuário quer criar DUIMP para um processo
   - Extrai dados do processo automaticamente
   - Cria DUIMP via API do Portal Único
   - Confirmação inteligente de ações

4. **Sugestão inteligente de NCM:**
   - Busca NCM por descrição de produto
   - Integração com busca web (DuckDuckGo) para contexto
   - Validação genérica baseada em tipo de produto
   - Notas explicativas NESH para contexto adicional
   - Sistema de cache para otimização

5. **Vinculação de documentos:**
   - Vinculação de CE, CCT, DI, DUIMP a processos
   - Desvinculação de documentos
   - Detecção automática de documentos na mensagem

6. **Precheck Logic:**
   - Detecção proativa de intenções antes da IA processar
   - Acelera respostas para consultas comuns
   - Reduz custos de API bilhetada
   - **Refatorado (19/12/2025)**: Lógica de email extraída para `EmailPrecheckService` para melhor modularidade

**Arquitetura:**
- ToolRouter: Sistema de roteamento de funções (arquitetura escalável)
- Tool Calling: Execução de funções baseada em intenções da IA
- Context Management: Gerenciamento inteligente de contexto entre mensagens

---

#### `NotificacaoService` (`services/notificacao_service.py`) ✅ **MELHORADO (05/01/2026)**
**Responsabilidade:** Detecta mudanças em processos e cria notificações proativas. Agora também notifica erros do sistema (ex: falhas de conexão SQL Server).

**Funcionalidades:**
- `notificar_erro_sistema(tipo_erro, mensagem, detalhes)`: ✅ NOVO - Cria notificações de erros do sistema
- `criar_notificacao()`: Cria notificações de mudanças em processos
- `buscar_notificacoes()`: Busca notificações do sistema

**Tipos de notificações detectadas:**
1. **Chegada confirmada:** Quando `dataDestinoFinal` é preenchida
2. **Mudança de status da DI:** Quando situação da DI muda (ex: desembaracada)
3. **Mudança de status da DUIMP:** Quando situação da DUIMP muda
4. **Mudança de status do CE:** Quando situação do CE muda (ex: MANIFESTADO, ARMAZENADO)
5. **Pagamento AFRMM:** Quando AFRMM é pago
6. **Pendência de ICMS resolvida:** Quando pendência de ICMS é removida
7. **Pendência de frete resolvida:** Quando pendência de frete é removida
8. **Pendência geral resolvida:** Quando qualquer pendência é resolvida
9. **Mudança de ETA:** Quando ETA do processo muda (antecipa ou atrasa)
10. **Mudança de LPCO:** Quando status, canal ou exigência de LPCO muda

**Funcionalidades:**
- Comparação inteligente entre versões anterior e nova do processo
- Histórico compacto de mudanças (últimos 30 dias)
- Limpeza automática de histórico antigo
- Notificações salvas no SQLite (tabela `notificacoes`)
- ✅ NOVO (05/01/2026): Deduplicação de notificações de erro (evita spam - mesma notificação não aparece novamente por 10 minutos)
- ✅ NOVO (05/01/2026): Notificações de erros do sistema aparecem automaticamente na UI quando há problemas de conexão

---

#### `ProcessoKanbanService` (`services/processo_kanban_service.py`)
**Responsabilidade:** Sincroniza processos do Kanban com SQLite local.

**Funcionalidades:**
- Sincronização automática a cada 5 minutos (configurável)
- Busca processos da API Kanban interna
- Salva processos no SQLite local (tabela `processos_kanban`)
- Limpa processos antigos (que não estão mais no Kanban)
- Limpa histórico antigo de mudanças (> 30 dias)

**APIs utilizadas:**
- API Kanban: `GET http://172.16.10.211:5000/api/kanban/pedidos`

**Inicialização:**
- Executado automaticamente em background quando a aplicação inicia
- Pode ser executado manualmente via `sincronizar()`

---

#### `NCMService` (`services/ncm_service.py`)
**Responsabilidade:** Operações relacionadas a NCM (Nomenclatura Comum do Mercosul).

**Funcionalidades:**
- `buscar_ncms_por_descricao()`: Busca NCMs por descrição de produto
- `sugerir_ncm_com_ia()`: Sugestão inteligente de NCM usando IA
- `detalhar_ncm()`: Detalhamento completo de um NCM
- `buscar_nota_explicativa_nesh()`: Busca nota explicativa NESH
- `baixar_nomenclatura_ncm()`: Download da nomenclatura do Portal Único

**Características:**
- Integração com busca web (DuckDuckGo) para contexto
- Cache inteligente de buscas
- Validação genérica baseada em tipo de produto
- Sistema de cache para otimização

---

#### `CalculoImpostosService` (`services/calculo_impostos_service.py`) ✅ **NOVO (05/01/2026)**
**Responsabilidade:** Cálculo automático de impostos de importação baseado em alíquotas do TECwin.

**Funcionalidades:**
- `extrair_aliquotas_do_contexto()`: Extrai alíquotas da última consulta TECwin do contexto da sessão
- `calcular_impostos()`: Calcula impostos (II, IPI, PIS, COFINS) com bases de cálculo corretas
- `formatar_resposta_calculo()`: Formata resultado do cálculo com explicação passo a passo

**Características:**
- ✅ **Integração com TECwin**: Alíquotas são salvas automaticamente no contexto após consulta TECwin
- ✅ **Cálculo Correto**: Usa bases de cálculo corretas (II base: CIF, IPI base: CIF + II, PIS/COFINS base: CIF)
- ✅ **Formatação Educativa**: Explica cada passo do cálculo com fórmulas e valores intermediários
- ✅ **Suporte a USD e BRL**: Calcula valores em ambas as moedas
- ✅ **Contexto Persistente**: Alíquotas ficam disponíveis na sessão para cálculos posteriores

**Fluxo de Uso:**
```
1. Usuário: "tecwin 84145110"
   ↓
2. Sistema consulta TECwin e salva alíquotas no contexto (tipo: 'ncm_aliquotas')
   ↓
3. Usuário: "calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283"
   ↓
4. Sistema busca alíquotas do contexto e calcula impostos automaticamente
   ↓
5. Sistema retorna cálculo completo com explicação passo a passo
```

**Tool relacionada:**
- `calcular_impostos_ncm`: Tool disponível para a IA chamar automaticamente quando usuário pedir cálculo de impostos

---

#### `SantanderService` (`services/santander_service.py`) ✅ **NOVO (06/01/2026)**
**Responsabilidade:** Wrapper para integração com API do Santander Open Banking.

**Funcionalidades:**
- `listar_contas()`: Lista todas as contas disponíveis
- `consultar_extrato()`: Consulta extrato bancário com movimentações e saldo
- `consultar_saldo()`: Consulta saldo real da conta (disponível, bloqueado, investido)

**Características:**
- ✅ **Detecção Automática**: Se não fornecer agência/conta, usa primeira conta disponível
- ✅ **Saldo Real**: Consulta saldo via API (não apenas cálculo das transações)
- ✅ **Versão Independente**: Código integrado ao projeto, não depende de diretório externo
- ✅ **Autenticação mTLS**: OAuth2 com certificado ICP-Brasil tipo A1

**Arquivos relacionados:**
- `utils/santander_api.py`: Cliente API do Santander (independente)
- `services/agents/santander_agent.py`: Agent para operações bancárias

**Documentação completa:** `docs/INTEGRACAO_SANTANDER.md`

---

#### `BancoBrasilService` (`services/banco_brasil_service.py`) ✅ **NOVO (06/01/2026)**
**Responsabilidade:** Wrapper para integração com API de Extratos do Banco do Brasil.

**Funcionalidades:**
- `consultar_extrato()`: Consulta extrato bancário com movimentações e saldo
  - Suporta período específico ou últimos 30 dias (padrão)
  - Ordenação automática: mais recentes primeiro
  - Normalização automática: remove zeros à esquerda de agência/conta
  - Usa valores padrão do `.env` se não fornecidos

**Características:**
- ✅ **OAuth 2.0 Client Credentials**: Autenticação mais simples que mTLS
- ✅ **Normalização Automática**: Remove zeros à esquerda de agência/conta (conforme especificação API)
- ✅ **Valores Padrão**: Usa `BB_TEST_AGENCIA` e `BB_TEST_CONTA` do `.env` quando não fornecidos
- ✅ **Ordenação Inteligente**: Transações ordenadas da mais recente para a mais antiga
- ✅ **Precheck Automático**: Detecta pedidos de extrato BB antes da IA processar
- ✅ **Cadeia de Certificados**: Suporte para APIs mTLS quando necessário (ex: Pagamentos)

**Arquivos relacionados:**
- `utils/banco_brasil_api.py`: Cliente API do Banco do Brasil (independente)
- `services/agents/banco_brasil_agent.py`: Agent para operações bancárias
- `.secure/certificados_bb/`: Scripts para criação de cadeia de certificados

**Documentação completa:** `docs/INTEGRACAO_BANCO_BRASIL.md`

---

#### `ConsultasBilhetadasService` (`services/consultas_bilhetadas_service.py`)
**Responsabilidade:** Gestão de consultas bilhetadas (Integra Comex).

**Funcionalidades:**
- `listar_consultas_bilhetadas_pendentes()`: Lista consultas pendentes de aprovação
- `aprovar_consultas_bilhetadas()`: Aprova consultas para execução
- `rejeitar_consultas_bilhetadas()`: Rejeita consultas
- `executar_consultas_aprovadas()`: Executa consultas aprovadas

**Características:**
- Sistema de aprovação antes da execução
- Proteção contra consultas duplicadas
- Histórico de consultas bilhetadas

---

#### `ProcessoRepository` (`services/processo_repository.py`)
**Responsabilidade:** Repositório para consultar processos de importação (padrão Repository).

**Estratégia de busca (em ordem):**
1. **SQLite (cache do Kanban):** Rápido, sem custo
2. **API Kanban (processos ativos):** Fallback para processos não encontrados no cache
3. **SQL Server (processos antigos/históricos):** Último recurso para processos antigos

**Vantagens:**
- Abstrai a complexidade de múltiplas fontes de dados
- Prioriza cache local (rápido e sem custo)
- Fallback automático para APIs quando necessário

---

#### `PrecheckService` (`services/precheck_service.py`)
**Responsabilidade:** Prechecks determinísticos antes de chamar a IA.

**Funcionalidades:**
- Orquestra diferentes tipos de prechecks
- Delega lógica especializada para serviços modulares
- Mantém ordem de prioridade crítica

**Arquitetura:**
- Orquestra diferentes tipos de prechecks
- Delega lógica de email para `EmailPrecheckService`
- Delega lógica de processo para `ProcessoPrecheckService`
- Delega lógica de NCM para `NcmPrecheckService`
- Mantém ordem de prioridade crítica

**Ordem de execução:**
1. TECwin NCM (via `NcmPrecheckService`)
2. Follow-up contextual de processo (via `ProcessoPrecheckService`)
3. Situação/detalhe de processo (via `ProcessoPrecheckService`)
4. Comandos de envio de email (via `EmailPrecheckService`)
5. Identificação de perguntas de NCM (via `NcmPrecheckService`)

---

#### `ProcessoPrecheckService` (`services/processo_precheck_service.py`) ✅ **REFATORADO (19/12/2025)**
**Responsabilidade:** Prechecks especializados em consultas de processos.

**Funcionalidades:**
- Follow-up contextual de processo (ex.: "e a DI?", "e a DUIMP?")
- Situação/detalhe de processo com número explícito
- Detecção inteligente de referências a processos
- Uso de contexto de sessão para follow-ups

**Métodos principais:**
- `precheck_followup_processo()`: Detecta e processa follow-ups contextuais
- `precheck_situacao_processo()`: Consulta situação de processo com número explícito

**Benefícios da refatoração:**
- ✅ Código mais modular e testável
- ✅ Separação clara de responsabilidades
- ✅ Facilita manutenção e extensão

---

#### `NcmPrecheckService` (`services/ncm_precheck_service.py`) ✅ **REFATORADO (19/12/2025)**
**Responsabilidade:** Prechecks especializados em consultas de NCM.

**Funcionalidades:**
- Consulta TECwin NCM (responde diretamente)
- Identificação de perguntas de NCM
- Detecção de padrões de consulta NCM

**Métodos principais:**
- `precheck_tecwin_ncm()`: Consulta TECwin e responde diretamente
- `eh_pergunta_ncm()`: Detecta se a mensagem é uma pergunta sobre NCM

**Benefícios da refatoração:**
- ✅ Código mais modular e testável
- ✅ Separação clara de responsabilidades
- ✅ Facilita manutenção e extensão

---

#### `EmailPrecheckService` (`services/email_precheck_service.py`) ✅ **REFATORADO (19/12/2025)**
**Responsabilidade:** Prechecks especializados em comandos de envio de email.

**Hierarquia de decisão (ordem de prioridade):**
1. **Email de classificação NCM + alíquotas**: Requer contexto de NCM salvo na sessão
2. **Email de relatório genérico**: Dashboard, "o que temos pra hoje", etc.
3. **Email de resumo/briefing**: Resumos específicos por categoria
4. **Email livre**: Texto ditado pelo usuário
5. **Email com informações de processo/NCM**: Conteúdo misturado

**Funcionalidades:**
- Detecção inteligente de tipo de email
- Extração de email e conteúdo da mensagem
- Integração com `EmailBuilderService` e `EmailService`
- Suporte a confirmação antes do envio
- Logging detalhado para debug

**Métodos principais:**
- `tentar_precheck_email()`: Método principal de orquestração
- `_precheck_envio_email_ncm()`: Email de classificação NCM
- `_precheck_envio_email_relatorio_generico()`: Email de relatório
- `_precheck_envio_email()`: Email de resumo/briefing
- `_precheck_envio_email_livre()`: Email livre
- `_precheck_envio_email_processo()`: Email de processo/NCM

**Benefícios da refatoração:**
- ✅ Código mais modular e testável
- ✅ Separação clara de responsabilidades
- ✅ Facilita manutenção e extensão
- ✅ Testes automatizados criados (`tests/test_email_precheck_smoke.py`)

---

#### `ToolRouter` (`services/tool_router.py`)
**Responsabilidade:** Router que direciona tool calls para agents específicos.

**Funcionalidades:**
- Mapeia cada tool para o agent responsável
- Inicializa todos os agents disponíveis
- Roteia chamadas de funções para o agent correto
- Trata erros de inicialização de agents

**Agents gerenciados:**
- `ProcessoAgent`: Processos de importação
- `DuimpAgent`: DUIMP
- `CeAgent`: CE (Conhecimento de Embarque)
- `DiAgent`: DI (Declaração de Importação)
- `CctAgent`: CCT (Conhecimento de Carga Aérea)
- `LegislacaoAgent`: ✅ NOVO (05/01/2026) - Legislação (busca semântica e tradicional)

---

### 🛠️ Utilitários (Utils)

#### `validators.py` (`services/utils/validators.py`)
**Responsabilidade:** Funções de validação de parâmetros.

**Funções:**
- `validate_processo_referencia(processo_referencia: str)`: Valida formato de referência de processo (ex: `ALH.0001/25`, `MV5.0013/25`)
  - Aceita categorias com números (ex: MV5, GPS)
  - Padrão: `[A-Z0-9]{2,4}\.\d{1,4}/\d{2}`

---

#### `extractors.py` (`services/utils/extractors.py`)
**Responsabilidade:** Funções para extrair informações de mensagens e dados.

**Funções:**
- `extract_processo_referencia(mensagem: str)`: Extrai referência de processo da mensagem
  - Suporta formatos completos (`ALH.0001/25`) e parciais (`vdm.003`)
  - Busca no banco de dados para expandir referências parciais
  - Aceita categorias com números (ex: MV5, GPS)

---

#### `formatters.py` (`services/utils/formatters.py`)
**Responsabilidade:** Funções para formatação de respostas para o usuário.

**Funções:**
- `format_lista_processos(processos: List[Dict], titulo: str)`: Formata lista de processos para exibição
  - Gera mensagem formatada com emojis e estrutura clara
  - Inclui categoria e situação de cada processo

---

#### `iata_to_country.py` (`utils/iata_to_country.py`)
**Responsabilidade:** Converte código IATA de aeroporto para código de país ISO 3166-1 alpha-2.

**Funções:**
- `iata_to_country_code(iata_code: str)`: Converte código IATA para código de país
  - Exemplos: `MIA` → `US`, `GRU` → `BR`, `PEK` → `CN`
  - Usado na criação de DUIMP para processos aéreos (CCT)

**Mapeamento:**
- Inclui principais aeroportos internacionais
- Estados Unidos, Brasil, China, Alemanha, França, Reino Unido, etc.

---

### 💾 Gerenciamento de Banco de Dados

#### `db_manager.py` (`db_manager.py`)
**Responsabilidade:** Gerenciador de banco de dados SQLite para armazenar dados locais.

**Principais funcionalidades:**
1. **Inicialização do banco:**
   - Cria todas as tabelas necessárias
   - Habilita WAL mode para melhor concorrência
   - Executa migrações automáticas

2. **Tabelas principais:**
   - `processos_kanban`: Cache de processos do Kanban
   - `notificacoes`: Notificações do sistema
   - `duimps`: DUIMPs criadas localmente
   - `ce_cache`: Cache de consultas de CE
   - `di_cache`: Cache de consultas de DI
   - `processo_documentos`: Vinculação de documentos a processos
   - `consultas_bilhetadas`: Histórico de consultas bilhetadas
   - `consultas_bilhetadas_pendentes`: Fila de consultas pendentes de aprovação
   - `usuarios`: Perfis de usuários (nome, sessão)
   - `categorias_processo`: Categorias de processos aprendidas dinamicamente
   - `chat_conversas`: Histórico de conversas importantes
   - `historico_mudancas`: Histórico compacto de mudanças em processos

3. **Funcionalidades especiais:**
   - Timeout configurável para evitar "database is locked"
   - Retry automático em caso de lock
   - WAL mode para melhor concorrência
   - Limpeza automática de dados antigos

**Funções principais:**
- `get_db_connection()`: Cria conexão SQLite com timeout
- `init_db()`: Inicializa o banco de dados
- `obter_dados_documentos_processo()`: Obtém documentos vinculados a um processo
- `salvar_duimp()`: Salva DUIMP criada localmente
- `buscar_ce_cache()`: Busca CE no cache
- `salvar_ce_cache()`: Salva CE no cache

---

### 🔄 Fluxo de Dados e Arquitetura de Armazenamento

#### Fluxo de Dados: JSON → DTO → SQLite

A aplicação segue um padrão de arquitetura em camadas para processamento e armazenamento de dados:

```
1. API Kanban (JSON)
   ↓
2. ProcessoKanbanDTO (DTO - Data Transfer Object)
   ↓
3. SQLite (dados_completos_json + campos normalizados)
```

**Detalhamento do Fluxo:**

1. **Origem dos Dados (JSON):**
   - API Kanban retorna processos em formato JSON
   - JSON contém todos os dados do processo (CE, DI, DUIMP, CCT, LPCO, pendencias, etc.)
   - Exemplo: `{"numeroPedido": "ALH.0168/25", "ce": [...], "di": [...], ...}`

2. **Processamento via DTO:**
   - `ProcessoKanbanDTO.from_kanban_json()` converte JSON em objeto estruturado
   - DTO extrai e normaliza campos importantes:
     - Identificação: `processo_referencia`, `id_processo_importacao`
     - Documentos: `numero_ce`, `numero_di`, `numero_duimp`, `bl_house`
     - Status: `situacao_ce`, `situacao_di`, `situacao_entrega`
     - Datas: `data_criacao`, `data_embarque`, `data_desembaraco`, `data_destino_final`
     - Pendencias: `tem_pendencias`, `pendencia_icms`, `pendencia_frete`
   - DTO mantém também o JSON completo em `dados_completos` para consultas futuras

3. **Armazenamento no SQLite:**
   - Campos normalizados são salvos em colunas específicas (para queries rápidas)
   - JSON completo é salvo em `dados_completos_json` (TEXT/JSON)
   - Permite:
     - **Queries rápidas:** Buscar por `numero_ce`, `situacao_ce`, `data_destino_final` (índices)
     - **Dados completos:** Acessar qualquer campo do JSON original quando necessário

**Vantagens desta Arquitetura:**
- ✅ **Performance:** Campos normalizados permitem queries rápidas com índices
- ✅ **Flexibilidade:** JSON completo preserva todos os dados originais
- ✅ **Manutenibilidade:** DTO padroniza estrutura de dados
- ✅ **Escalabilidade:** Fácil adicionar novos campos sem quebrar código existente

---

### 🗄️ Integração com SQL Server

#### Quando a Aplicação Consulta o SQL Server?

A aplicação usa uma **estratégia de busca em cascata** (fallback) para encontrar processos:

```
1. SQLite (cache local) → Rápido, sem custo
   ↓ (se não encontrar)
2. API Kanban (processos ativos) → Fallback para processos ativos
   ↓ (se não encontrar)
3. SQL Server (processos antigos/históricos) → Último recurso
```

#### Gatilhos Específicos para Consulta ao SQL Server:

1. **Processo não encontrado no SQLite E na API Kanban:**
   - Quando um processo não está no cache local (SQLite)
   - E não está na API Kanban (processos ativos)
   - **Gatilho:** Consulta automática ao SQL Server para processos antigos/históricos
   - **Local:** `services/processo_repository.py` → `_buscar_sql_server()`

2. **Geração de PDF de DI/DUIMP:**
   - Quando o usuário solicita extrato PDF de DI ou DUIMP
   - E o processo não está no cache local
   - **Gatilho:** Consulta ao SQL Server para obter dados completos do processo
   - **Local:** 
     - `services/di_pdf_service.py` → `buscar_processo_consolidado_sql_server()`
     - `services/duimp_pdf_service.py` → `buscar_processo_consolidado_sql_server()`

3. **Consulta de Processo Consolidado:**
   - Quando o usuário solicita dados consolidados de um processo (CE + DI + DUIMP + CCT)
   - E o processo não está no cache local
   - **Gatilho:** Consulta ao SQL Server para obter dados consolidados
   - **Local:** `services/sql_server_processo_schema.py` → `buscar_processo_consolidado_sql_server()`

#### O que é Buscado no SQL Server?

Quando consultado, o SQL Server retorna dados consolidados de múltiplas tabelas:

1. **Processo Principal:**
   - Tabela: `Make.dbo.PROCESSO_IMPORTACAO`
   - Dados: `numero_processo`, `id_processo_importacao`, `numero_ce`, `numero_di`, `numero_duimp`

2. **CE (Conhecimento de Embarque):**
   - Tabela: `ce.dbo.ce` + `ce.dbo.ce_situacao`
   - Dados: Situação, canal, datas, pendencias

3. **DI (Declaração de Importação):**
   - Tabela: `di.dbo.di` + `di.dbo.di_situacao`
   - Dados: Situação, canal, data de registro, data de desembaraço

4. **DUIMP (Declaração Única de Importação):**
   - Tabela: `duimp.dbo.duimp` + `duimp.dbo.duimp_situacao`
   - Dados: Situação, canal, data de registro, última situação

5. **CCT (Conhecimento de Carga Aérea):**
   - Tabela: `cct.dbo.cct` + `cct.dbo.cct_situacao`
   - Dados: Situação, canal, datas (apenas para processos aéreos)

#### Configuração do SQL Server:

**Variáveis de Ambiente (`.env`):**
```env
SQL_SERVER=172.16.10.8\SQLEXPRESS
SQL_USERNAME=sa
SQL_PASSWORD=sua_senha
SQL_DATABASE=Make
```

**Adaptadores Disponíveis:**
1. **pyodbc** (recomendado, se disponível)
2. **Node.js adapter** (fallback, especialmente no macOS)

**Arquivos Relacionados:**
- `utils/sql_server_adapter.py`: Adaptador principal para SQL Server
- `utils/sql_server_node.js`: Script Node.js para consultas (fallback)
- `services/sql_server_processo_schema.py`: Schema e queries para processos consolidados

#### Performance e Otimização:

- ✅ **Cache Local:** SQLite é sempre consultado primeiro (rápido, sem custo)
- ✅ **Fallback Inteligente:** SQL Server só é consultado quando necessário
- ✅ **Timeout Configurável:** Consultas ao SQL Server têm timeout para evitar travamentos
- ✅ **Não Bloqueante:** Consultas ao SQL Server são executadas em background quando possível

---

### 📄 Serviços de PDF

#### `DiPdfService` (`services/di_pdf_service.py`)
**Responsabilidade:** Geração de extrato PDF da DI.

**Funcionalidades:**
- Busca dados da DI no Integra Comex
- Gera PDF do extrato usando `xhtml2pdf`
- Salva PDF no diretório `downloads/`
- Limpa PDFs antigos automaticamente

---

#### `DuimpPdfService` (`services/duimp_pdf_service.py`)
**Responsabilidade:** Geração de extrato PDF da DUIMP.

**Funcionalidades:**
- Busca número e versão da DUIMP no banco
- Consulta dados da DUIMP no Portal Único
- Gera PDF do extrato (futuro)
- Salva PDF no diretório `downloads/`

---

### 🔐 Proxies de Autenticação

#### `integracomex_proxy.py` (`utils/integracomex_proxy.py`)
**Responsabilidade:** Proxy para chamadas à API Integra Comex (SERPRO).

**Funcionalidades:**
- Autenticação OAuth2 + mTLS (certificado PKCS#12)
- Renovação automática de tokens
- Tratamento de erros e retry
- Cache de tokens

**APIs utilizadas:**
- Integra Comex: Consultas de CE, DI, ETA

---

#### `portal_proxy.py` (`utils/portal_proxy.py`)
**Responsabilidade:** Proxy para chamadas à API Portal Único Siscomex.

**Funcionalidades:**
- Autenticação mTLS + CSRF Token (certificado PKCS#12)
- Renovação automática de tokens (SET Token + CSRF Token)
- Suporte a ambientes (validação e produção)
- Tratamento de erros e retry

**APIs utilizadas:**
- Portal Único: Criação/consulta de DUIMP, consulta de CCT

---

## 🎓 Sistema de Aprendizado e Contexto Persistente

### **Visão Geral**

Sistema implementado na **Versão 1.4.0** que permite à mAIke aprender com o usuário e manter contexto entre mensagens, tornando a interação mais natural e eficiente.

### **Arquitetura**

```
┌─────────────────────────────────────────────────────────┐
│                    ChatService                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  processar_mensagem()                            │  │
│  │    ↓                                              │  │
│  │  1. Buscar regras aprendidas                     │  │
│  │  2. Buscar contexto de sessão                    │  │
│  │  3. Incluir no prompt                            │  │
│  │  4. Processar mensagem                           │  │
│  │  5. Salvar contexto se necessário                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ learned_rules   │  │ context_service │  │ analytical_query│
│ _service.py     │  │ .py             │  │ _service.py     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         ↓                    ↓                    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ regras_         │  │ contexto_       │  │ consultas_      │
│ aprendidas      │  │ sessao          │  │ salvas          │
│ (SQLite)        │  │ (SQLite)        │  │ (SQLite)        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### **Endpoints e Tools Relacionados**

#### **Tool: `salvar_regra_aprendida`**

**Descrição:** Salva uma regra ou definição aprendida do usuário.

**Parâmetros:**
```json
{
  "tipo_regra": "campo_definicao",
  "contexto": "chegada_processos",
  "nome_regra": "destfinal como confirmação de chegada",
  "descricao": "O campo data_destino_final deve ser usado como confirmação de que o processo chegou",
  "aplicacao_sql": "WHERE data_destino_final IS NOT NULL",
  "aplicacao_texto": "Processos que têm data_destino_final preenchida são considerados como tendo chegado",
  "exemplo_uso": "Quando perguntar 'quais VDM chegaram', usar data_destino_final IS NOT NULL"
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "resposta": "✅ Regra aprendida e salva com sucesso!\n\n**Regra:** destfinal como confirmação de chegada\n**Contexto:** chegada_processos\n**ID:** 1\n\nA partir de agora, vou aplicar essa regra automaticamente quando fizer sentido! 🎯",
  "id": 1
}
```

**Arquivo:** `services/learned_rules_service.py`

#### **Tool: `executar_consulta_analitica`**

**Descrição:** Executa uma consulta SQL analítica de forma segura.

**Parâmetros:**
```json
{
  "sql": "SELECT cliente, COUNT(*) as total FROM processos GROUP BY cliente",
  "limit": 100
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "dados": [
    {"cliente": "Cliente A", "total": 10},
    {"cliente": "Cliente B", "total": 5}
  ],
  "total_linhas": 2,
  "fonte": "sql_server",
  "sql_executado": "SELECT cliente, COUNT(*) as total FROM processos GROUP BY cliente LIMIT 100"
}
```

**Arquivo:** `services/analytical_query_service.py`

#### **Tool: `salvar_consulta_personalizada`**

**Descrição:** Salva uma consulta SQL ajustada como relatório reutilizável.

**Parâmetros:**
```json
{
  "nome_exibicao": "Atrasos por cliente em 2025",
  "slug": "atrasos_cliente_2025",
  "descricao": "Mostra clientes com mais processos em atraso em 2025",
  "sql": "SELECT cliente, COUNT(*) as atrasos FROM processos WHERE atraso > 0 AND ano = 2025 GROUP BY cliente ORDER BY atrasos DESC",
  "parametros": [],
  "exemplos_pergunta": "atrasos por cliente, relatório de atrasos"
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "resposta": "✅ Consulta salva como relatório 'Atrasos por cliente em 2025'!\n\nAgora você pode pedir para 'rodar aquele relatório de atrasos' e eu vou executar automaticamente!",
  "id": 1
}
```

**Arquivo:** `services/saved_queries_service.py`

#### **Tool: `buscar_consulta_personalizada`**

**Descrição:** Busca uma consulta salva baseada no texto do pedido do usuário.

**Parâmetros:**
```json
{
  "texto_pedido_usuario": "rodar aquele relatório de atrasos"
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "resposta": "✅ Consulta salva encontrada!\n\n**Nome:** Atrasos por cliente em 2025\n**Descrição:** Mostra clientes com mais processos em atraso em 2025\n**SQL:**\n```sql\nSELECT cliente, COUNT(*) as atrasos FROM processos WHERE atraso > 0 AND ano = 2025 GROUP BY cliente ORDER BY atrasos DESC\n```",
  "consulta": {
    "id": 1,
    "nome_exibicao": "Atrasos por cliente em 2025",
    "sql_base": "SELECT cliente, COUNT(*) as atrasos FROM processos WHERE atraso > 0 AND ano = 2025 GROUP BY cliente ORDER BY atrasos DESC",
    ...
  }
}
```

**Arquivo:** `services/saved_queries_service.py`

---

#### **Tool: `calcular_impostos_ncm`** ✅ **NOVO (05/01/2026)**

**Descrição:** Calcula impostos de importação (II, IPI, PIS, COFINS) automaticamente baseado nas alíquotas da última consulta TECwin do contexto da sessão.

**⚠️ IMPORTANTE:** Esta tool deve ser usada SEMPRE quando o usuário pedir cálculo de impostos. A IA NÃO deve fazer cálculos manuais.

**Parâmetros:**
```json
{
  "custo_usd": 10000.0,
  "frete_usd": 1500.0,
  "seguro_usd": 200.0,
  "cotacao_ptax": 5.5283
}
```

**Parâmetros opcionais:**
- `custo_usd`: Valor da mercadoria em USD (VMLE). Se não fornecido, a função perguntará.
- `frete_usd`: Valor do frete em USD. Se não fornecido, a função perguntará.
- `seguro_usd`: Valor do seguro em USD. Se não fornecido, usa 0 como padrão.
- `cotacao_ptax`: Cotação PTAX (R$ / USD). Se não fornecido, a função perguntará ou buscará a cotação do dia.

**Resposta de Sucesso:**
```json
{
  "sucesso": true,
  "resposta": "💰 **CÁLCULO DE IMPOSTOS**\n\n📊 **Cálculo passo a passo:**\n\n📋 **NCM:** 84145110\n\n**1️⃣ Valores de Entrada:**\n• Custo (VMLE): USD 10,000.00\n• Frete: USD 1,500.00\n• Seguro: USD 200.00\n• Cotação PTAX: R$ 5.5283 / USD\n\n**2️⃣ CIF (Custo + Frete + Seguro):**\n• CIF USD = 10,000.00 + 1,500.00 + 200.00 = USD 11,700.00\n• CIF BRL = USD 11,700.00 × 5.5283 = R$ 64,678.11\n\n**3️⃣ Impostos Calculados:**\n\n**II (Imposto de Importação) - 18.00%:**\n• Base de cálculo: CIF = R$ 64,678.11\n• Fórmula: II = Base de Cálculo × Alíquota\n• Cálculo: R$ 64,678.11 × 0.1800 = R$ 11,642.06\n• Valor: R$ 11,642.06 (USD 2,105.00)\n\n[... demais impostos ...]\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n**💰 TOTAL DE IMPOSTOS:**\n• R$ 25,234.56\n• USD 4,562.34",
  "dados": {
    "ncm": "84145110",
    "valores_entrada": {
      "custo_usd": 10000.0,
      "frete_usd": 1500.0,
      "seguro_usd": 200.0,
      "cotacao_ptax": 5.5283
    },
    "cif": {
      "usd": 11700.0,
      "brl": 64678.11
    },
    "impostos": {
      "ii": {"aliquota": 18.0, "brl": 11642.06, "usd": 2105.0},
      "ipi": {"aliquota": 9.75, "brl": 7431.23, "usd": 1344.5},
      "pis": {"aliquota": 2.1, "brl": 1358.24, "usd": 245.7},
      "cofins": {"aliquota": 9.65, "brl": 6241.15, "usd": 1128.3}
    },
    "total_impostos": {
      "brl": 25234.56,
      "usd": 4562.34
    }
  }
}
```

**Resposta de Erro (alíquotas não encontradas):**
```json
{
  "sucesso": false,
  "erro": "ALIQUOTAS_NAO_ENCONTRADAS",
  "resposta": "❌ **Alíquotas não encontradas!**\n\nPara calcular impostos, você precisa primeiro consultar o NCM no TECwin usando: `tecwin ncm [código]`\n\nApós a consulta, as alíquotas ficarão disponíveis no contexto e você poderá calcular os impostos."
}
```

**Fluxo de Uso:**
1. Usuário consulta NCM no TECwin: `"tecwin 84145110"`
2. Sistema salva alíquotas no contexto da sessão (tipo: `'ncm_aliquotas'`)
3. Usuário pede cálculo: `"calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283"`
4. IA chama `calcular_impostos_ncm` automaticamente
5. Sistema busca alíquotas do contexto e calcula impostos
6. Sistema retorna cálculo completo com explicação passo a passo

**Características:**
- ✅ **Bases de Cálculo Corretas:**
  - II: Base = CIF
  - IPI: Base = CIF + II
  - PIS: Base = CIF
  - COFINS: Base = CIF
- ✅ **Formatação Educativa:** Explica cada passo do cálculo com fórmulas e valores intermediários
- ✅ **Suporte a USD e BRL:** Calcula valores em ambas as moedas
- ✅ **Contexto Persistente:** Alíquotas ficam disponíveis na sessão para cálculos posteriores

**Arquivo:** `services/calculo_impostos_service.py`

### **Estrutura de Dados**

#### **Tabela: `regras_aprendidas`**

Armazena regras e definições aprendidas do usuário.

**Schema:**
```sql
CREATE TABLE regras_aprendidas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_regra TEXT NOT NULL,           -- 'campo_definicao', 'regra_negocio', etc.
    contexto TEXT,                       -- 'chegada_processos', 'analise_vdm', etc.
    nome_regra TEXT NOT NULL,            -- Nome amigável
    descricao TEXT NOT NULL,             -- Descrição completa
    aplicacao_sql TEXT,                  -- Como aplicar em SQL
    aplicacao_texto TEXT,                 -- Como aplicar em texto
    exemplo_uso TEXT,                    -- Exemplo de quando usar
    criado_por TEXT,                     -- user_id ou session_id
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vezes_usado INTEGER DEFAULT 0,       -- Contador de uso
    ultimo_usado_em TIMESTAMP,
    ativa BOOLEAN DEFAULT 1              -- Se a regra está ativa
);
```

**Índices:**
- `idx_regras_tipo` - (tipo_regra, contexto)
- `idx_regras_ativa` - (ativa, vezes_usado DESC)

#### **Tabela: `contexto_sessao`**

Armazena contexto persistente de sessão.

**Schema:**
```sql
CREATE TABLE contexto_sessao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,            -- ID da sessão
    tipo_contexto TEXT NOT NULL,         -- 'processo_atual', 'categoria_atual', etc.
    chave TEXT NOT NULL,                 -- Chave do contexto
    valor TEXT NOT NULL,                  -- Valor do contexto
    dados_json TEXT,                     -- Dados adicionais em JSON
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, tipo_contexto, chave)
);
```

**Índices:**
- `idx_contexto_sessao` - (session_id, tipo_contexto)

#### **Tabela: `consultas_salvas`**

Armazena consultas SQL salvas como relatórios reutilizáveis.

**Schema:**
```sql
CREATE TABLE consultas_salvas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_exibicao TEXT NOT NULL,        -- Nome amigável
    slug TEXT NOT NULL UNIQUE,           -- Identificador único
    descricao TEXT,                      -- Descrição
    sql_base TEXT NOT NULL,              -- SQL da consulta
    parametros_json TEXT,                -- Parâmetros (JSON)
    exemplos_pergunta TEXT,              -- Exemplos de como pedir
    criado_por TEXT,                     -- user_id ou session_id
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    vezes_usado INTEGER DEFAULT 0,      -- Contador de uso
    ultimo_usado_em TIMESTAMP
);
```

**Índices:**
- `idx_consultas_salvas_slug` - (slug)
- `idx_consultas_salvas_nome` - (nome_exibicao)

### **Fluxo de Dados**

#### **Fluxo de Aprendizado de Regra:**

```
1. Usuário: "usar campo destfinal como confirmação de chegada"
   ↓
2. mAIke detecta padrão de ensino
   ↓
3. mAIke chama salvar_regra_aprendida()
   ↓
4. learned_rules_service.py salva na tabela regras_aprendidas
   ↓
5. Próxima mensagem: regras são buscadas e incluídas no prompt
   ↓
6. mAIke aplica regra automaticamente quando fizer sentido
```

#### **Fluxo de Contexto Persistente:**

```
1. Usuário: "buscar vdm.0004/25"
   ↓
2. chat_service.py detecta processo mencionado
   ↓
3. context_service.py salva contexto (processo_atual = VDM.0004/25)
   ↓
4. Próxima mensagem: contexto é buscado e incluído no prompt
   ↓
5. Usuário: "trazer todos os dados"
   ↓
6. mAIke usa contexto salvo (sabe que é VDM.0004/25)
```

#### **Fluxo de Consulta Analítica:**

```
1. Usuário: "Quais clientes têm mais processos em atraso?"
   ↓
2. mAIke gera SQL: "SELECT cliente, COUNT(*) FROM processos WHERE atraso > 0 GROUP BY cliente"
   ↓
3. mAIke chama executar_consulta_analitica()
   ↓
4. analytical_query_service.py valida SQL (apenas SELECT)
   ↓
5. Aplica LIMIT automaticamente
   ↓
6. Tenta executar no SQL Server (se disponível)
   ↓
7. Se falhar, executa no SQLite (fallback)
   ↓
8. Retorna resultados formatados
```

### **Como Debugar e Consertar Problemas**

#### **Problema: Regras não estão sendo aplicadas**

1. **Verificar se regras estão salvas:**
   ```bash
   sqlite3 chat_ia.db
   SELECT * FROM regras_aprendidas WHERE ativa = 1;
   ```

2. **Verificar se regras aparecem no prompt:**
   - Adicionar log em `chat_service.py` linha ~7990:
     ```python
     logger.info(f"Regras encontradas: {len(regras)}")
     for regra in regras:
         logger.info(f"  - {regra['nome_regra']}")
     ```

3. **Verificar se mAIke está aplicando:**
   - Ver logs quando mAIke processa mensagem
   - Verificar se regras aparecem no contexto do prompt

#### **Problema: Contexto não está sendo mantido**

1. **Verificar se contexto está sendo salvo:**
   ```bash
   sqlite3 chat_ia.db
   SELECT * FROM contexto_sessao WHERE session_id = 'SEU_SESSION_ID';
   ```

2. **Verificar se session_id está sendo passado:**
   - Ver `app.py` linha ~238: `session_id = data.get('session_id') or request.remote_addr`
   - Ver `chat_service.py` linha ~471: `session_id=session_id`

3. **Verificar se contexto aparece no prompt:**
   - Adicionar log em `chat_service.py` linha ~8006:
     ```python
     logger.info(f"Contextos encontrados: {len(contextos)}")
     ```

#### **Problema: Consulta SQL não está funcionando**

1. **Verificar validação:**
   ```python
   from services.analytical_query_service import validar_sql_seguro
   valido, erro = validar_sql_seguro("SELECT * FROM processos")
   if not valido:
       print(f"Erro: {erro}")
   ```

2. **Verificar se tabela está permitida:**
   - Ver `analytical_query_service.py` linha ~20: `TABELAS_PERMITIDAS`
   - Adicionar tabela se necessário

3. **Verificar logs de execução:**
   - Logs mostram qual fonte foi usada (SQL Server ou SQLite)
   - Logs mostram erros de execução

#### **Problema: Consulta salva não está sendo encontrada**

1. **Verificar se consulta está salva:**
   ```bash
   sqlite3 chat_ia.db
   SELECT * FROM consultas_salvas;
   ```

2. **Testar busca manualmente:**
   ```python
   from services.saved_queries_service import buscar_consulta_personalizada
   resultado = buscar_consulta_personalizada('atrasos por cliente')
   print(resultado)
   ```

3. **Verificar busca por slug vs nome:**
   - A busca tenta primeiro por slug, depois por nome, depois por exemplos_pergunta
   - Verificar se o texto do pedido corresponde

### **Arquivos Principais para Manutenção**

#### **`services/learned_rules_service.py`**
- **Responsabilidade:** Gerenciar regras aprendidas
- **Funções principais:**
  - `salvar_regra_aprendida()` - Salva nova regra
  - `buscar_regras_aprendidas()` - Busca regras por contexto
  - `formatar_regras_para_prompt()` - Formata para prompt
- **Como modificar:** Adicionar novos tipos de regra ou contextos

#### **`services/context_service.py`**
- **Responsabilidade:** Gerenciar contexto de sessão
- **Funções principais:**
  - `salvar_contexto_sessao()` - Salva contexto
  - `buscar_contexto_sessao()` - Busca contexto
  - `limpar_contexto_sessao()` - Limpa contexto
  - `formatar_contexto_para_prompt()` - Formata para prompt
- **Como modificar:** Adicionar novos tipos de contexto

#### **`services/analytical_query_service.py`**
- **Responsabilidade:** Executar consultas SQL analíticas de forma segura
- **Funções principais:**
  - `executar_consulta_analitica()` - Executa consulta
  - `validar_sql_seguro()` - Valida SQL
  - `aplicar_limit_seguro()` - Aplica LIMIT
- **Como modificar:**
  - Adicionar tabelas permitidas em `TABELAS_PERMITIDAS`
  - Ajustar validações em `validar_sql_seguro()`
  - Modificar limite padrão

#### **`services/saved_queries_service.py`**
- **Responsabilidade:** Gerenciar consultas SQL salvas
- **Funções principais:**
  - `salvar_consulta_personalizada()` - Salva consulta
  - `buscar_consulta_personalizada()` - Busca consulta
  - `listar_consultas_salvas()` - Lista todas
- **Como modificar:** Melhorar algoritmo de busca por texto

#### **`services/chat_service.py`**
- **Responsabilidade:** Integrar todos os serviços no chat
- **Locais importantes:**
  - Linha ~7983: Busca regras aprendidas
  - Linha ~7995: Busca contexto de sessão
  - Linha ~7555: Instruções de aprendizado no prompt
  - Linha ~8312: Instruções de resposta no user_prompt
  - Linha ~680: `_executar_funcao_tool()` - Execução das tools
- **Como modificar:** Ajustar instruções no prompt para melhorar comportamento

---

## 🔄 Changelog

### v1.5 (19/12/2025)
- ✅ Adicionada documentação do `EmailPrecheckService`
  - Hierarquia de decisão para tipos de email
  - Métodos principais e responsabilidades
  - Benefícios da refatoração
  - Integração com outros serviços
- ✅ Adicionada documentação do `ProcessoPrecheckService`
  - Prechecks especializados em consultas de processos
  - Follow-up contextual e situação de processo
  - Benefícios da refatoração
- ✅ Adicionada documentação do `NcmPrecheckService`
  - Prechecks especializados em consultas de NCM
  - Consulta TECwin e detecção de perguntas NCM
  - Benefícios da refatoração
- ✅ Atualizada seção de Arquitetura e Serviços
  - Mapa do sistema atualizado
  - Fluxo de processamento de mensagens
  - Documentação de `PrecheckService` refatorado
  - Documentação dos novos serviços modulares

### v1.4 (14/12/2025)
- ✅ Adicionada seção completa "Sistema de Aprendizado e Contexto Persistente"
  - Documentação detalhada de regras aprendidas
  - Documentação de contexto persistente de sessão
  - Documentação de consultas analíticas SQL
  - Documentação de consultas salvas
  - Guias de debug e manutenção
  - Estrutura de dados e fluxos explicados
- ✅ Adicionada seção "Sistema de Consultas Analíticas SQL"
  - Arquitetura e fluxo de dados
  - Endpoints e tools relacionados
  - Validações de segurança
  - Como debugar e consertar problemas

### v1.3 (12/12/2025)
- ✅ Adicionada seção "Sistema de Verificação de Fontes de Dados"
  - Verificação automática de disponibilidade
  - Comportamento inteligente da mAIke
  - Tool `verificar_fontes_dados`

### v1.2 (12/12/2025)
- ✅ Adicionada seção "Fluxo de Dados e Arquitetura de Armazenamento"
  - Explicação detalhada do fluxo: JSON → DTO → SQLite
  - Vantagens da arquitetura em camadas
- ✅ Adicionada seção "Integração com SQL Server"
  - Gatilhos específicos para consulta ao SQL Server
  - Estratégia de busca em cascata (fallback)
  - O que é buscado no SQL Server
  - Configuração e performance

### v1.1 (09/12/2025)
- Adicionada seção de Arquitetura e Serviços
- Documentação completa de agentes, serviços e utilitários

### v1.0 (09/12/2025)
- Documentação inicial da API
- Endpoints principais documentados
- Exemplos de uso adicionados

---

**Última atualização:** 05/01/2026

### v1.8 (05/01/2026)
- ✅ Adicionada documentação do `CalculoImpostosService`
  - Cálculo automático de impostos após consulta TECwin
  - Integração com contexto de sessão
  - Formatação educativa passo a passo
  - Exemplos de uso
- ✅ Atualizada documentação do `NcmPrecheckService`
  - Salvamento de alíquotas no contexto após consulta TECwin
  - Integração com cálculo de impostos
- ✅ Adicionados exemplos de uso na seção "Exemplos de Uso"
  - Fluxo completo: Consulta TECwin → Cálculo de Impostos

### v1.8 (05/01/2026)
- ✅ Adicionada documentação do `CalculoImpostosService`
  - Cálculo automático de impostos após consulta TECwin
  - Integração com contexto de sessão
  - Formatação educativa passo a passo
  - Exemplos de uso
- ✅ Atualizada documentação do `NcmPrecheckService`
  - Salvamento de alíquotas no contexto após consulta TECwin
  - Integração com cálculo de impostos
- ✅ Adicionados exemplos de uso na seção "Exemplos de Uso"
  - Fluxo completo: Consulta TECwin → Cálculo de Impostos

