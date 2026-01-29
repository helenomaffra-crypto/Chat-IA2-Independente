# 🚀 Sugestões de Ferramentas OpenAI para o mAIke

**Data:** 05/01/2026  
**Status:** Análise e recomendações

---

## 📊 O que já está implementado

✅ **Chat Completions API** (GPT-4o, GPT-5.1)  
✅ **Responses API** (Code Interpreter) - migrado recentemente  
✅ **Assistants API** (File Search/RAG) - para legislação  
✅ **TTS (Text-to-Speech)** - já implementado (`services/tts_service.py`)

---

## 🎯 Ferramentas Recomendadas (por prioridade)

### 1. 🖼️ **Vision API (GPT-4 Vision)** ⭐⭐⭐⭐⭐

**Prioridade:** 🔴 **ALTA** - Muito útil para importação

**O que faz:**
- Analisa imagens e documentos (PDFs, fotos, screenshots)
- Extrai texto de documentos escaneados (OCR)
- Identifica informações em documentos fiscais

**Casos de uso no mAIke:**
- 📄 **Análise de documentos fiscais**: DI, CE, CCT, DUIMP em PDF/imagem
- 🔍 **Extração automática de dados**: NCM, valores, alíquotas de documentos escaneados
- ✅ **Validação visual**: Verificar se documento está completo/correto
- 📊 **Análise de tabelas**: Extrair dados de tabelas em PDFs/imagens
- 🧾 **Processamento de notas fiscais**: Extrair informações de NF-e escaneadas

**Exemplo de uso:**
```python
# Usuário envia foto de uma DI
# mAIke analisa e extrai: número DI, NCM, valores, situação
# Resposta: "Vejo que a DI 2528215001 está DESEMBARACADA, com NCM 90041000..."
```

**Implementação sugerida:**
- Tool: `analisar_documento_imagem(url_imagem, tipo_documento)`
- Agent: `DocumentoAgent` (já existe, adicionar método)
- Endpoint: `/api/chat/upload-documento` (upload de imagem/PDF)

**Custo:** ~$0.01-0.03 por imagem (dependendo da resolução)

**Complexidade:** 🟢 Baixa (API simples, similar ao Chat Completions)

---

### 2. 🎤 **Whisper API (Speech-to-Text)** ⭐⭐⭐⭐

**Prioridade:** 🟡 **MÉDIA** - Melhora UX, mas não crítico

**O que faz:**
- Transcreve áudio para texto
- Suporta múltiplos idiomas (incluindo português)
- Pode processar arquivos de áudio ou streaming

**Casos de uso no mAIke:**
- 🎙️ **Comandos de voz**: Usuário fala "situação do VDM.0004/25" → transcreve → processa
- 📞 **Análise de áudios de reunião**: Extrair informações de áudios de reuniões sobre processos
- 🗣️ **Acessibilidade**: Usuários com dificuldade de digitação
- 📹 **Transcrição de vídeos**: Extrair informações de vídeos sobre importação

**Exemplo de uso:**
```python
# Usuário envia áudio: "qual a situação do processo ALH.0166/25?"
# Whisper transcreve → "qual a situação do processo ALH.0166/25?"
# mAIke processa normalmente
```

**Implementação sugerida:**
- Tool: `transcrever_audio(url_audio)` (opcional, pode ser automático)
- Endpoint: `/api/chat/audio` (upload de áudio, transcreve automaticamente)
- Integração: Automática no fluxo de chat (se mensagem for áudio, transcreve primeiro)

**Custo:** ~$0.006 por minuto de áudio

**Complexidade:** 🟢 Baixa (API simples)

---

### 3. 🔍 **Embeddings API** ⭐⭐⭐

**Prioridade:** 🟡 **MÉDIA** - Pode melhorar busca, mas já tem RAG

**O que faz:**
- Gera embeddings (vetores) de texto para busca semântica
- Permite busca por similaridade (não apenas palavras-chave)
- Mais controle que File Search da Assistants API

**Casos de uso no mAIke:**
- 🔎 **Busca semântica customizada**: Buscar processos/documentos por significado, não apenas palavras
- 📚 **Busca em cache de NCM**: Encontrar NCMs similares por descrição
- 🧠 **Busca inteligente em histórico**: Encontrar conversas anteriores por contexto
- 📖 **Busca em legislação local**: Alternativa ao File Search (mais controle)

**Exemplo de uso:**
```python
# Usuário: "processos que chegam na próxima semana"
# Embedding busca processos com ETA similar (semântica, não apenas data exata)
```

**Implementação sugerida:**
- Service: `EmbeddingService` para gerar e buscar embeddings
- Integração: Opcional, pode melhorar busca de processos/NCMs
- Cache: Armazenar embeddings no SQLite para reutilização

**Custo:** ~$0.0001 por 1K tokens (muito barato)

**Complexidade:** 🟡 Média (requer armazenamento e busca de vetores)

**Nota:** Já tem RAG via Assistants API, então Embeddings seria redundante a menos que queira mais controle.

---

### 4. 🛡️ **Moderation API** ⭐⭐

**Prioridade:** 🟢 **BAIXA** - Útil para produção, mas não crítico

**O que faz:**
- Detecta conteúdo inapropriado (violência, sexual, hate speech, etc.)
- Classifica conteúdo por categoria
- Útil para filtrar inputs do usuário

**Casos de uso no mAIke:**
- 🚫 **Filtro de conteúdo**: Bloquear mensagens inapropriadas
- ✅ **Validação de inputs**: Garantir que mensagens são apropriadas para ambiente corporativo
- 📊 **Logging de segurança**: Registrar tentativas de uso inapropriado

**Implementação sugerida:**
- Middleware: Verificar mensagens antes de processar
- Integração: No `ChatService.processar_mensagem()` antes da IA

**Custo:** ~$0.0001 por mensagem (muito barato)

**Complexidade:** 🟢 Baixa (API simples)

**Nota:** Útil para produção, mas não adiciona funcionalidade ao usuário.

---

### 5. 📦 **Batch API** ⭐⭐

**Prioridade:** 🟢 **BAIXA** - Otimização de custo, não funcionalidade

**O que faz:**
- Processa múltiplas requisições em lote
- Reduz custo (50% de desconto)
- Útil para processar grandes volumes

**Casos de uso no mAIke:**
- 📊 **Processamento em lote**: Classificar múltiplos NCMs de uma vez
- 🔄 **Sincronização**: Processar histórico de conversas
- 💰 **Otimização de custo**: Reduzir custos em operações em massa

**Implementação sugerida:**
- Service: `BatchService` para criar e processar batches
- Uso: Apenas para operações em massa (não para chat em tempo real)

**Custo:** 50% de desconto vs. API normal (mas requer processamento assíncrono)

**Complexidade:** 🟡 Média (requer gerenciamento de jobs assíncronos)

**Nota:** Útil apenas se houver necessidade de processar grandes volumes.

---

### 6. 📁 **File Search na Responses API** ⭐⭐⭐⭐

**Prioridade:** 🟡 **MÉDIA** - Quando estiver disponível

**O que faz:**
- Similar ao File Search da Assistants API
- RAG (Retrieval-Augmented Generation) na Responses API
- Mais moderno que Assistants API

**Status atual:**
- ⚠️ Ainda não está totalmente disponível na Responses API
- ✅ Já migrado para Responses API (Code Interpreter)
- 🔜 File Search será adicionado em breve

**Quando implementar:**
- Quando OpenAI lançar File Search na Responses API
- Migrar legislação de Assistants API para Responses API

**Nota:** Já está na lista de pendências (`docs/MIGRACAO_STATUS.md`).

---

## 📋 Resumo de Recomendações

### 🔴 Implementar Agora (Alta Prioridade)

1. **Vision API (GPT-4 Vision)**
   - ✅ Alto valor para importação (análise de documentos)
   - ✅ Casos de uso claros e frequentes
   - ✅ Implementação simples
   - 💡 **Sugestão**: Começar com análise de DI/CE/CCT em PDF/imagem

### 🟡 Considerar Depois (Média Prioridade)

2. **Whisper API**
   - ✅ Melhora UX (comandos de voz)
   - ✅ Implementação simples
   - ⚠️ Não crítico para funcionalidade core

3. **File Search na Responses API**
   - ✅ Quando estiver disponível
   - ✅ Migrar legislação de Assistants API

### 🟢 Baixa Prioridade

4. **Embeddings API**
   - ⚠️ Já tem RAG via Assistants API
   - ✅ Útil apenas se quiser mais controle

5. **Moderation API**
   - ✅ Útil para produção
   - ⚠️ Não adiciona funcionalidade ao usuário

6. **Batch API**
   - ✅ Útil apenas para processamento em massa
   - ⚠️ Não necessário para chat em tempo real

---

## 🎯 Próximos Passos Sugeridos

1. **Implementar Vision API** para análise de documentos fiscais
2. **Aguardar File Search na Responses API** para migrar legislação
3. **Considerar Whisper API** se houver demanda por comandos de voz

---

## 📚 Referências

- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [OpenAI Moderation API](https://platform.openai.com/docs/guides/moderation)
- [OpenAI Batch API](https://platform.openai.com/docs/guides/batch)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)

---

**Última atualização:** 05/01/2026




