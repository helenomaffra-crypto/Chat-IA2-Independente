# 📚 Especificação: Banco de Legislações com Busca Inteligente

**Data:** 19/12/2025  
**Objetivo:** Criar um sistema de busca e consulta de legislações (IN RFB, Decretos, Leis) integrado à Maike

---

## 🎯 PROBLEMA

Legislações têm características complexas:
- **Estrutura hierárquica:** Artigos → Parágrafos → Incisos → Alíneas
- **Referências cruzadas:** Artigos referenciam outros artigos (ex: "nos termos do art. 16 da Lei n° 9.779")
- **Alterações históricas:** Normas são alteradas por outras normas (ex: "Alterado(a) pelo(a) Instrução Normativa RFB n° 1937")
- **Contexto necessário:** Para entender um artigo, pode ser necessário ler outros artigos relacionados

**Chunks simples não funcionam bem porque:**
- Quebram referências entre artigos
- Perdem contexto hierárquico
- Não mantêm histórico de alterações

---

## 🏗️ ARQUITETURA PROPOSTA

### 1. **Estrutura de Dados Hierárquica**

```
Legislacao (IN RFB nº 1861-2018)
├── Metadados
│   ├── numero: "1861"
│   ├── tipo: "IN RFB"
│   ├── data_publicacao: "2018-12-28"
│   ├── data_vigencia: "2018-12-28"
│   └── alteracoes: [
│       {numero: "1937", data: "2020-04-15", tipo: "IN RFB"},
│       {numero: "2101", data: "2022-09-09", tipo: "IN RFB"}
│   ]
├── Capitulo I
│   ├── titulo: "DA IMPORTAÇÃO POR CONTA E ORDEM DE TERCEIRO"
│   └── Artigos
│       ├── Art. 2º
│       │   ├── texto_original: "..."
│       │   ├── texto_vigente: "..." (com alterações aplicadas)
│       │   ├── paragrafos: [
│       │       {numero: "1", texto: "...", referencias: ["art. 4º da IN RFB 1984"]},
│       │       {numero: "2", texto: "...", referencias: []},
│       │       {numero: "3", texto: "...", referencias: []},
│       │       {numero: "4", texto: "...", referencias: ["art. 689 do Decreto 6759"]}
│       │   ]
│       │   └── incisos: []
│       └── ...
└── Capitulo II
    └── ...
```

### 2. **Banco de Dados SQLite**

```sql
-- Tabela principal de legislações
CREATE TABLE legislacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    tipo TEXT NOT NULL,  -- "IN RFB", "Decreto", "Lei", etc.
    titulo_completo TEXT,
    data_publicacao DATE,
    data_vigencia DATE,
    texto_completo TEXT,  -- Texto completo da legislação
    metadata_json TEXT,  -- JSON com alterações, revogações, etc.
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(numero, tipo)
);

-- Tabela de artigos (unidade básica de busca)
CREATE TABLE artigos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    legislacao_id INTEGER NOT NULL,
    numero_artigo TEXT NOT NULL,  -- "2", "3", "10", etc.
    capitulo TEXT,  -- "CAPÍTULO I", "CAPÍTULO II", etc.
    titulo_capitulo TEXT,  -- "DA IMPORTAÇÃO POR CONTA E ORDEM DE TERCEIRO"
    texto_original TEXT NOT NULL,
    texto_vigente TEXT NOT NULL,  -- Com alterações aplicadas
    ordem INTEGER,  -- Ordem de aparição na legislação
    FOREIGN KEY (legislacao_id) REFERENCES legislacoes(id),
    UNIQUE(legislacao_id, numero_artigo)
);

-- Tabela de parágrafos/incisos (subunidades)
CREATE TABLE subunidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artigo_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,  -- "paragrafo", "inciso", "alinea"
    numero TEXT,  -- "1", "2", "I", "II", "a", "b", etc.
    texto TEXT NOT NULL,
    ordem INTEGER,
    FOREIGN KEY (artigo_id) REFERENCES artigos(id)
);

-- Tabela de referências cruzadas (artigo X referencia artigo Y)
CREATE TABLE referencias_artigos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artigo_origem_id INTEGER NOT NULL,
    artigo_destino_id INTEGER,  -- NULL se referência externa
    legislacao_destino_id INTEGER,  -- NULL se referência externa
    referencia_texto TEXT NOT NULL,  -- Texto exato da referência
    tipo_referencia TEXT,  -- "artigo", "paragrafo", "inciso", "lei", "decreto", etc.
    FOREIGN KEY (artigo_origem_id) REFERENCES artigos(id),
    FOREIGN KEY (artigo_destino_id) REFERENCES artigos(id),
    FOREIGN KEY (legislacao_destino_id) REFERENCES legislacoes(id)
);

-- Tabela de embeddings (para busca semântica)
CREATE TABLE embeddings_artigos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artigo_id INTEGER NOT NULL,
    texto_embedding TEXT NOT NULL,  -- Texto usado para gerar embedding
    embedding_vector BLOB,  -- Embedding vetorizado (JSON ou pickle)
    modelo_embedding TEXT DEFAULT 'text-embedding-3-small',  -- Modelo usado
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artigo_id) REFERENCES artigos(id),
    UNIQUE(artigo_id)
);

-- Índices para performance
CREATE INDEX idx_legislacoes_numero_tipo ON legislacoes(numero, tipo);
CREATE INDEX idx_artigos_legislacao ON artigos(legislacao_id);
CREATE INDEX idx_artigos_numero ON artigos(numero_artigo);
CREATE INDEX idx_subunidades_artigo ON subunidades(artigo_id);
CREATE INDEX idx_referencias_origem ON referencias_artigos(artigo_origem_id);
CREATE INDEX idx_referencias_destino ON referencias_artigos(artigo_destino_id);
```

### 3. **Sistema de Busca Híbrida**

#### 3.1. **Busca por Referência (Exata)**
Quando o usuário menciona um artigo específico:
- "o que diz o art. 2º da IN 1861?"
- "artigo 3º parágrafo 1º"

**Estratégia:**
1. Extrair número do artigo/parágrafo/inciso da pergunta
2. Buscar diretamente no banco por `numero_artigo`
3. Incluir automaticamente artigos referenciados
4. Retornar contexto completo (artigo + referências)

#### 3.2. **Busca Semântica (Embeddings)**
Quando o usuário faz pergunta conceitual:
- "o que define a operação por encomenda?"
- "quais são os requisitos para importação por conta e ordem?"

**Estratégia:**
1. Gerar embedding da pergunta usando OpenAI `text-embedding-3-small`
2. Buscar artigos similares usando cosine similarity
3. Retornar top N artigos mais relevantes
4. Incluir artigos referenciados para contexto completo

#### 3.3. **Busca Híbrida (Recomendada)**
Combinar ambas as estratégias:
1. Tentar busca exata primeiro (se detectar referência)
2. Se não encontrar, usar busca semântica
3. Sempre incluir artigos referenciados no resultado

---

## 🔧 IMPLEMENTAÇÃO

### 1. **Serviço de Legislações** (`services/legislacao_service.py`)

```python
class LegislacaoService:
    """
    Serviço para gerenciar e buscar legislações.
    """
    
    def __init__(self):
        self.db = get_db_connection()
        self.embedding_model = "text-embedding-3-small"
    
    def importar_legislacao_pdf(self, pdf_path: str, tipo: str, numero: str) -> Dict[str, Any]:
        """
        Importa uma legislação de um PDF.
        
        Processo:
        1. Extrair texto do PDF
        2. Parsear estrutura (artigos, parágrafos, incisos)
        3. Identificar referências cruzadas
        4. Salvar no banco
        5. Gerar embeddings para cada artigo
        """
        pass
    
    def buscar_por_referencia(
        self, 
        tipo: str, 
        numero: str, 
        artigo: Optional[str] = None,
        paragrafo: Optional[str] = None,
        inciso: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca exata por referência (artigo, parágrafo, inciso).
        
        Retorna:
        - Artigo encontrado
        - Parágrafos/incisos relacionados
        - Artigos referenciados (para contexto)
        """
        pass
    
    def buscar_semantica(self, pergunta: str, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Busca semântica usando embeddings.
        
        Processo:
        1. Gerar embedding da pergunta
        2. Calcular similaridade com embeddings dos artigos
        3. Retornar top N artigos mais relevantes
        4. Incluir artigos referenciados
        """
        pass
    
    def buscar_hibrida(
        self, 
        pergunta: str, 
        incluir_referencias: bool = True
    ) -> Dict[str, Any]:
        """
        Busca híbrida: tenta exata primeiro, depois semântica.
        
        Sempre inclui artigos referenciados para contexto completo.
        """
        pass
```

### 2. **Parser de PDF** (`utils/legislacao_parser.py`)

```python
class LegislacaoParser:
    """
    Parser para extrair estrutura de legislações de PDFs.
    """
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrai estrutura hierárquica do PDF:
        - Metadados (número, tipo, data)
        - Capítulos
        - Artigos
        - Parágrafos, incisos, alíneas
        - Referências cruzadas
        """
        pass
    
    def identificar_referencias(self, texto: str) -> List[Dict[str, Any]]:
        """
        Identifica referências a outros artigos/leis/decretos.
        
        Padrões:
        - "art. 16 da Lei n° 9.779"
        - "inciso III do art. 327"
        - "Decreto nº 6.759, de 5 de fevereiro de 2009"
        """
        pass
```

### 3. **Tool para Maike** (`services/tool_definitions.py`)

```python
{
    "type": "function",
    "function": {
        "name": "consultar_legislacao",
        "description": "Consulta legislações (IN RFB, Decretos, Leis) para responder perguntas sobre normas e regulamentações. Use quando o usuário perguntar sobre definições legais, requisitos, procedimentos estabelecidos em legislações, ou quando mencionar artigos específicos.",
        "parameters": {
            "type": "object",
            "properties": {
                "pergunta": {
                    "type": "string",
                    "description": "A pergunta do usuário sobre a legislação. Pode ser uma pergunta conceitual (ex: 'o que define a operação por encomenda?') ou uma referência específica (ex: 'o que diz o art. 2º da IN 1861?')."
                },
                "tipo_legislacao": {
                    "type": "string",
                    "description": "Tipo da legislação (ex: 'IN RFB', 'Decreto', 'Lei'). Opcional, será inferido se não fornecido.",
                    "enum": ["IN RFB", "Decreto", "Lei", "Portaria", "Outro"]
                },
                "numero_legislacao": {
                    "type": "string",
                    "description": "Número da legislação (ex: '1861', '6759'). Opcional, será inferido se não fornecido."
                },
                "artigo": {
                    "type": "string",
                    "description": "Número do artigo específico (ex: '2', '3', '10'). Opcional."
                }
            },
            "required": ["pergunta"]
        }
    }
}
```

### 4. **Agent de Legislação** (`services/agents/legislacao_agent.py`)

```python
class LegislacaoAgent(BaseAgent):
    """
    Agent especializado em consultas de legislação.
    """
    
    def execute(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executa consulta de legislação.
        
        Handlers:
        - consultar_legislacao: Busca híbrida (exata + semântica)
        """
        handlers = {
            'consultar_legislacao': self._consultar_legislacao,
        }
        # ... implementação
```

---

## 📊 FLUXO DE USO

### Exemplo 1: Pergunta Conceitual
```
Usuário: "o que define a operação por encomenda?"

1. Maike detecta pergunta sobre legislação
2. Chama tool `consultar_legislacao` com pergunta="o que define a operação por encomenda?"
3. LegislacaoService.buscar_hibrida():
   a. Tenta busca exata (não encontra referência específica)
   b. Usa busca semântica:
      - Gera embedding da pergunta
      - Encontra Art. 3º da IN 1861 (mais relevante)
      - Inclui parágrafos relacionados
      - Inclui artigos referenciados (se houver)
4. Retorna resposta formatada:
   "A operação de importação por encomenda é definida no Art. 3º da IN RFB nº 1861/2018:
   
   [Texto do artigo]
   
   [Parágrafos relacionados]
   
   [Referências a outros artigos, se necessário]"
```

### Exemplo 2: Referência Específica
```
Usuário: "o que diz o art. 2º da IN 1861?"

1. Maike detecta referência específica
2. Chama tool `consultar_legislacao` com:
   - pergunta="o que diz o art. 2º da IN 1861?"
   - tipo_legislacao="IN RFB"
   - numero_legislacao="1861"
   - artigo="2"
3. LegislacaoService.buscar_por_referencia():
   a. Busca exata por artigo
   b. Inclui parágrafos e incisos
   c. Inclui artigos referenciados (ex: art. 4º da IN 1984, art. 689 do Decreto 6759)
4. Retorna resposta completa com contexto
```

---

## 🚀 FASEAMENTO DE IMPLEMENTAÇÃO

### **Fase 1: Estrutura Básica** (MVP)
- [ ] Criar tabelas SQLite
- [ ] Implementar `LegislacaoService` básico
- [ ] Parser simples de PDF (extrair texto, identificar artigos)
- [ ] Tool `consultar_legislacao` básico (busca por texto simples)
- [ ] Agent `LegislacaoAgent`

### **Fase 2: Busca Semântica**
- [ ] Integração com OpenAI Embeddings
- [ ] Geração de embeddings para artigos
- [ ] Busca por similaridade (cosine similarity)
- [ ] Otimização de performance (cache de embeddings)

### **Fase 3: Referências Cruzadas**
- [ ] Parser avançado para identificar referências
- [ ] Tabela de referências cruzadas
- [ ] Inclusão automática de artigos referenciados
- [ ] Resolução de referências externas (outras legislações)

### **Fase 4: Histórico de Alterações**
- [ ] Parsear alterações históricas
- [ ] Aplicar alterações ao texto original
- [ ] Manter versões (original vs vigente)
- [ ] Exibir histórico de alterações na resposta

---

## 💡 VANTAGENS DESTA ABORDAGEM

1. **Estrutura Hierárquica:** Mantém relacionamento entre artigos, parágrafos, incisos
2. **Referências Cruzadas:** Resolve automaticamente referências entre artigos
3. **Busca Híbrida:** Combina precisão (busca exata) com flexibilidade (semântica)
4. **Contexto Completo:** Sempre inclui artigos relacionados para resposta completa
5. **Escalável:** Fácil adicionar novas legislações
6. **Integrado:** Usa mesma arquitetura de tools/agents do sistema existente

---

## ⚠️ DESAFIOS E SOLUÇÕES

### **Desafio 1: Parsing de PDF**
**Problema:** PDFs podem ter formatação inconsistente  
**Solução:** Usar bibliotecas robustas (PyPDF2, pdfplumber) + regex para padrões conhecidos

### **Desafio 2: Identificação de Referências**
**Problema:** Referências podem ter formatos variados  
**Solução:** Regex + IA para identificar padrões, validação manual inicial

### **Desafio 3: Performance de Embeddings**
**Problema:** Gerar embeddings para muitos artigos pode ser lento/caro  
**Solução:** Cache de embeddings, gerar apenas uma vez por artigo

### **Desafio 4: Referências Externas**
**Problema:** Artigo pode referenciar legislação não importada  
**Solução:** Marcar referência como "externa", oferecer importar se necessário

---

## 📝 PRÓXIMOS PASSOS

1. **Validar estrutura proposta** com o usuário
2. **Implementar Fase 1 (MVP)** com IN RFB 1861/2018 como teste
3. **Testar busca básica** com perguntas reais
4. **Iterar e melhorar** baseado no feedback

---

**Referências:**
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [SQLite Full-Text Search](https://www.sqlite.org/fts5.html)
- [Cosine Similarity](https://en.wikipedia.org/wiki/Cosine_similarity)



