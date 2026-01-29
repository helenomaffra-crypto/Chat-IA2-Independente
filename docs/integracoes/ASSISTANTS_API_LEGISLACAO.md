# 🤖 Assistants API com File Search para Legislação

**⚠️ ATENÇÃO:** Assistants API está **DEPRECATED** e será desligado em **26 de agosto de 2026**.  
A OpenAI recomenda migrar para **Responses API**. Veja `docs/CODE_INTERPRETER_RESPONSES_API.md` para detalhes sobre a migração.

## 📋 Visão Geral

Este sistema integra **Assistants API da OpenAI** com **File Search** para buscar legislação usando **RAG (Retrieval-Augmented Generation)**. Isso permite buscas semânticas inteligentes em todas as legislações importadas, encontrando informações mesmo quando não há palavras-chave exatas.

**⚠️ Status Atual:** Sistema funciona, mas precisa ser migrado para Responses API antes de agosto de 2026.

## 🎯 Benefícios

### ✅ Vantagens sobre busca tradicional:
- **Busca semântica**: Encontra informações mesmo sem palavras-chave exatas
- **Contexto inteligente**: Entende o significado da pergunta, não apenas palavras
- **Múltiplas legislações**: Busca automaticamente em TODAS as legislações importadas
- **Respostas contextualizadas**: A IA combina informações de diferentes legislações quando relevante

### 📊 Comparação:

| Característica | Busca Tradicional | Assistants API (RAG) |
|---------------|-------------------|---------------------|
| Busca por palavras-chave | ✅ | ✅ |
| Busca semântica | ❌ | ✅ |
| Entende contexto | ❌ | ✅ |
| Combina múltiplas legislações | Manual | Automático |
| Respostas explicativas | ❌ | ✅ |

## 🚀 Configuração Inicial

### 1. Pré-requisitos

- ✅ OpenAI API Key configurada (`DUIMP_AI_API_KEY` no `.env`)
- ✅ IA habilitada (`DUIMP_AI_ENABLED=true` no `.env`)
- ✅ Legislações importadas no banco de dados

### 2. Executar Script de Configuração

```bash
python scripts/configurar_assistants_legislacao.py
```

Este script:
1. ✅ Exporta todas as legislações do banco para arquivos texto
2. ✅ Faz upload dos arquivos para a OpenAI
3. ✅ Cria um vector store
4. ✅ Adiciona arquivos ao vector store
5. ✅ Cria um assistente com File Search
6. ✅ Salva `OPENAI_ASSISTANT_ID` no `.env`

**⏱️ Tempo estimado:** 5-15 minutos (dependendo do número de legislações)

### 3. Verificar Configuração

Após executar o script, verifique se o `.env` contém:

```env
OPENAI_ASSISTANT_ID=asst_xxxxx
```

## 📖 Como Usar

### Para o Usuário

A busca via Assistants API é **automática** quando:
- Você faz perguntas conceituais sobre legislação
- A busca tradicional não encontra resultados satisfatórios
- Você pede explicações detalhadas sobre temas legais

**Exemplos de perguntas que usam Assistants API:**
- "o que fala sobre perdimento?"
- "explique sobre multas em importação"
- "qual a base legal para penalidades?"
- "o que diz sobre canal de conferência?"

### Para Desenvolvedores

A tool `buscar_legislacao_assistants` é chamada automaticamente pela IA quando apropriado. Você também pode chamá-la diretamente:

```python
from services.assistants_service import get_assistants_service

service = get_assistants_service()
resultado = service.buscar_legislacao("o que fala sobre perdimento?")
```

## 📚 Incluir NESH (Nota Explicativa do Sistema Harmonizado)

### ✅ Recomendado para File Search

A NESH é um complemento valioso para o File Search, permitindo:
- **Busca semântica** de informações sobre classificação NCM
- **Perguntas conceituais** sem precisar do código NCM exato
- **Integração** com outras legislações já indexadas

### Como Preparar NESH para File Search

1. **Preparar arquivo NESH:**
   ```bash
   python scripts/preparar_nesh_para_file_search.py
   ```
   
   Este script:
   - Converte `nesh_chunks.json` (37MB, 7.370 chunks) em arquivo texto formatado
   - Organiza por seção, capítulo, posição e subposição
   - Cria `legislacao_files/NESH_Nota_Explicativa_Sistema_Harmonizado.txt`

2. **Configurar Assistants (inclui NESH automaticamente):**
   ```bash
   python scripts/configurar_assistants_legislacao.py
   ```
   
   O script detecta automaticamente o arquivo NESH e o inclui no upload.

### ⚠️ Considerações

- **Tamanho**: 37MB pode levar alguns minutos para processar
- **Custo**: Upload é GRATUITO, apenas o uso do File Search pode ter custo
- **Abordagem Híbrida**: Sistema mantém busca local (rápida) + File Search (semântica)
- **Uso Atual**: NESH já funciona localmente via `buscar_nota_explicativa_nesh`

### 💡 Quando Usar File Search vs Busca Local

| Tipo de Pergunta | Método Recomendado |
|------------------|-------------------|
| "Qual o NCM para X?" | Busca Local (rápida, sem custo) |
| "O que é considerado cavalo de raça pura?" | File Search (semântica, contextualizada) |
| "Explique a classificação de animais vivos" | File Search (conceitual, múltiplas fontes) |
| "NESH do NCM 0101.21" | Busca Local (direta, precisa) |

---

## 🔄 Atualizar Legislações

### ⚠️ Processo Manual (Não Automático)

**Quando você importar novas legislações no banco, precisa re-executar o script de configuração:**

```bash
python scripts/configurar_assistants_legislacao.py
```

### Como Funciona a Atualização

O script `exportar_todas_legislacoes()` busca **TODAS** as legislações do banco (`SELECT id FROM legislacao`), então:

1. ✅ **Exporta todas as legislações** (incluindo as novas)
2. ✅ **Faz upload de TODOS os arquivos** (novos e antigos)
3. ✅ **Cria novo vector store** ou atualiza o existente
4. ✅ **Atualiza o assistente** com os novos arquivos

**⚠️ IMPORTANTE:**
- **Não há detecção automática** de legislação nova
- **Precisa executar manualmente** após importar legislações
- O script sempre exporta **TODAS** as legislações (não apenas as novas)
- Arquivos antigos são re-enviados (mas isso não gera custo adicional - ver seção de custos abaixo)

**⏱️ Tempo estimado:** 5-15 minutos (dependendo do número de legislações)

### 💡 Otimização Futura (Sugestão)

Para evitar re-enviar arquivos antigos, poderia ser implementado:
- Cache de arquivos já enviados (comparar hash MD5)
- Detecção de legislações novas (comparar timestamps)
- Atualização incremental (adicionar apenas arquivos novos ao vector store)

**Status atual:** Não implementado - sempre re-envia todos os arquivos.

## 📁 Estrutura de Arquivos

```
Chat-IA-Independente/
├── services/
│   ├── assistants_service.py          # Serviço principal
│   └── agents/
│       └── legislacao_agent.py       # Handler da tool
├── scripts/
│   └── configurar_assistants_legislacao.py  # Script de configuração
├── legislacao_files/                 # Arquivos exportados (criado automaticamente)
│   ├── IN_680_2006_RFB.txt
│   ├── Decreto_6759_2009.txt
│   └── ...
└── docs/
    └── ASSISTANTS_API_LEGISLACAO.md  # Esta documentação
```

## 🛠️ API do Serviço

### `AssistantsService`

#### Métodos Principais:

**`buscar_legislacao(pergunta: str, thread_id: Optional[str] = None)`**
- Busca legislação usando Assistants API
- Retorna resposta contextualizada

**`exportar_legislacao_para_arquivo(legislacao_id: int)`**
- Exporta uma legislação do banco para arquivo texto
- Retorna caminho do arquivo criado

**`exportar_todas_legislacoes()`**
- Exporta todas as legislações do banco
- Retorna lista de caminhos dos arquivos

**`fazer_upload_arquivo(caminho_arquivo: str)`**
- Faz upload de arquivo para OpenAI
- Retorna ID do arquivo

**`criar_assistante_legislacao(nome: str)`**
- Cria assistente com File Search habilitado
- Retorna ID do assistente

**`criar_vector_store(nome: str)`**
- Cria vector store para armazenar arquivos
- Retorna ID do vector store

## 🔍 Como Funciona

1. **Exportação**: Legislações do banco são exportadas para arquivos texto
2. **Upload**: Arquivos são enviados para OpenAI
3. **Vector Store**: Arquivos são indexados em um vector store (embedding)
4. **Assistente**: Assistente criado com File Search habilitado
5. **Busca**: Quando o usuário pergunta, o assistente:
   - Busca semanticamente nos arquivos (RAG)
   - Combina informações relevantes
   - Gera resposta contextualizada

## ⚠️ Limitações e Considerações

### 💰 Custos

#### ✅ Upload de Arquivos: **GRATUITO**
- **Upload de arquivos** para Assistants API é **100% gratuito**
- Não há custo por arquivo enviado
- Não há custo por tamanho do arquivo
- Pode re-enviar arquivos quantas vezes quiser sem custo adicional

#### 💵 Uso do File Search: **PODE TER CUSTO**
- **File Search durante buscas** pode ter custos dependendo do plano OpenAI
- **Plano gratuito**: Geralmente tem limites de uso
- **Planos pagos**: Custos baseados em uso (tokens processados)
- **Recomendação**: Verificar preços atualizados em [OpenAI Pricing](https://openai.com/pricing)

#### 📊 Resumo de Custos

| Operação | Custo |
|----------|-------|
| Upload de arquivos | ✅ **GRATUITO** |
| Criação de vector store | ✅ **GRATUITO** |
| Indexação (embedding) | ✅ **GRATUITO** |
| Busca no File Search | ⚠️ **Pode ter custo** (depende do plano) |
| Re-enviar arquivos (atualização) | ✅ **GRATUITO** |

**💡 Conclusão:** 
- **Atualizar legislações (upload) = GRATUITO** ✅
- **Usar File Search (buscar) = pode ter custo** ⚠️
- **Re-executar o script de configuração = GRATUITO** ✅

### Performance
- **Primeira busca**: Pode levar 10-30 segundos (processamento do vector store)
- **Buscas subsequentes**: Geralmente mais rápidas (5-15 segundos)

### Limitações
- **Legislações importadas**: Apenas legislações já importadas no banco são indexadas
- **Atualização manual**: Precisa re-executar script quando importar novas legislações
- **Tamanho de arquivos**: Arquivos muito grandes podem ser divididos automaticamente pela OpenAI

## 🐛 Troubleshooting

### Erro: "AssistantsService não está habilitado"
- ✅ Verifique `DUIMP_AI_ENABLED=true` no `.env`
- ✅ Verifique `DUIMP_AI_API_KEY` está configurado
- ✅ Verifique se biblioteca `openai` está instalada

### Erro: "Assistant ID não configurado"
- ✅ Execute o script de configuração: `python scripts/configurar_assistants_legislacao.py`
- ✅ Verifique se `OPENAI_ASSISTANT_ID` está no `.env`

### Busca não encontra resultados
- ✅ Verifique se legislações foram importadas no banco
- ✅ Re-execute o script de configuração para atualizar arquivos
- ✅ Aguarde alguns minutos após upload (processamento do vector store)

### Erro ao fazer upload
- ✅ Verifique conexão com internet
- ✅ Verifique se API key está válida
- ✅ Verifique limites de uso da API OpenAI

## 🔍 Assistants API vs Embeddings

Para entender a diferença entre Assistants API (File Search/RAG) e Embeddings, consulte:
- **`docs/ASSISTANTS_API_VS_EMBEDDINGS.md`** - Comparação técnica detalhada
- Exemplos práticos de uso de Code Interpreter para cálculos fiscais
- Quando usar cada abordagem no contexto do mAIke

## 🤖 Code Interpreter vs Assistente (Cursor)

Para entender a diferença entre Code Interpreter e um assistente de programação (como o Cursor), consulte:
- **`docs/CODE_INTERPRETER_VS_ASSISTENTE.md`** - Comparação detalhada
- O que acontece com o código gerado pelo Code Interpreter
- Quando usar Code Interpreter vs desenvolvimento de código

## 📚 Referências

- [OpenAI Assistants API Documentation](https://platform.openai.com/docs/assistants)
- [File Search (RAG) Guide](https://platform.openai.com/docs/assistants/tools/file-search)
- [Code Interpreter Guide](https://platform.openai.com/docs/assistants/tools/code-interpreter)

