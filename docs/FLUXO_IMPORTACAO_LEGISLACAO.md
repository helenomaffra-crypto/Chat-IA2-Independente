# 📚 Fluxo de Importação de Legislação - mAIke

## 🎯 Objetivo

Permitir que o usuário peça para importar legislação via chat, ver um preview antes de gravar, e confirmar a importação.

## 🔄 Fluxo Completo

### 1. Usuário pede importação

**Exemplos de comandos:**
- "importar IN 680/2006 da RFB"
- "baixar legislação da IN 680/06"
- "trazer IN 680 da RFB"
- "busque o Decreto 6759/2009"

### 2. mAIke detecta intenção

A IA detecta que é uma intenção de **importação** (não consulta) e chama:
- **Tool:** `importar_legislacao_preview`

### 3. Backend busca e extrai (sem salvar)

O `LegislacaoAgent` executa:
1. Busca URL oficial usando IA (`buscar_url_com_ia`)
2. Baixa HTML/PDF da URL
3. Extrai texto (com melhorias de extração)
4. Parseia em artigos/trechos
5. **NÃO salva no banco** - apenas monta preview

### 4. Preview retornado ao usuário

**Resposta do mAIke:**
```
🔍 Encontrei IN 680/2006

📋 Título: Instrução Normativa RFB nº 680
🏛️ Órgão: RFB
📄 Total de trechos: 450
📚 Total de artigos: 132
🔗 Fonte: https://www.gov.br/receitafederal/...

📖 Exemplo - Art. 1º:
Esta Instrução Normativa estabelece as normas gerais...

💡 Quer salvar esta legislação no banco para consultas futuras?
   Digite: 'sim, salvar' ou 'confirmar importação' para gravar.
   Ou: 'não' ou 'descartar' para cancelar.
```

### 5. Usuário confirma ou descarta

**Se confirmar:**
- Usuário: "sim, salvar" ou "confirmar importação"
- mAIke chama: `confirmar_importacao_legislacao`
- Backend grava no SQLite
- Resposta: "✅ IN 680/2006 gravada com sucesso!"

**Se descartar:**
- Usuário: "não" ou "descartar"
- Nada é gravado
- Preview é descartado

## 🛠️ Implementação Técnica

### Tools Disponíveis

#### 1. `importar_legislacao_preview`
- **Quando usar:** Usuário pede para importar/baixar/buscar legislação
- **O que faz:** Busca, extrai, parseia, retorna preview (NÃO salva)
- **Parâmetros:** `tipo_ato`, `numero`, `ano`, `sigla_orgao` (opcional), `titulo_oficial` (opcional)

#### 2. `confirmar_importacao_legislacao`
- **Quando usar:** Usuário confirma que quer gravar após ver preview
- **O que faz:** Grava no banco SQLite
- **Parâmetros:** `tipo_ato`, `numero`, `ano`, `sigla_orgao` (opcional), `titulo_oficial` (opcional), `url` (opcional, mas recomendado)

#### 3. `buscar_e_importar_legislacao` (LEGADO)
- **Quando usar:** Apenas se usuário pedir explicitamente para "gravar direto sem perguntar"
- **O que faz:** Busca e grava automaticamente (sem preview)
- **Status:** Mantida para compatibilidade, mas prefira usar preview + confirmar

### Métodos do LegislacaoService

#### `buscar_legislacao_preview()`
- Busca URL com IA
- Chama `importar_ato_por_url(..., modo_preview=True)`
- Retorna preview sem salvar

#### `importar_ato_por_url(..., modo_preview=False)`
- Se `modo_preview=True`: extrai e parseia, retorna preview
- Se `modo_preview=False`: extrai, parseia e salva no banco

#### `importar_ato_de_texto(..., modo_preview=False)`
- Mesma lógica: preview ou salvar

### Estrutura do Preview

```python
{
    'tipo_ato': 'IN',
    'numero': '680',
    'ano': 2006,
    'sigla_orgao': 'RFB',
    'titulo_oficial': '...',
    'fonte_url': 'https://...',
    'total_trechos': 450,
    'total_artigos': 132,
    'primeiro_artigo': {
        'referencia': 'Art. 1º',
        'texto': '...',
        'tipo_trecho': 'caput',
        ...
    },
    'amostra_trechos': [...],
    'texto_preview': '...'
}
```

## 📊 Banco de Dados

### SQLite (Atual)

- **Tabela `legislacao`:** Dados principais do ato
- **Tabela `legislacao_trecho`:** Artigos, parágrafos, incisos parseados

### SQL Server (Futuro)

- Pode ser adicionado depois via job de sincronização
- Ou gravação direta (quando tiver acesso de escrita)

## 🎨 Melhorias de Extração

### HTML
- Headers de navegador realistas
- Detecção inteligente de conteúdo principal
- Remoção automática de navegação/rodapé/anúncios
- Busca por tags semânticas (`<main>`, `<article>`, etc.)

### PDF
- Tratamento de múltiplas páginas
- Limpeza de texto (espaços/linhas excessivas)
- Aviso quando PDF é escaneado (requer OCR)

### Validações
- Verifica se extraiu pelo menos 100 caracteres
- Detecta se tem artigos no texto
- Timeout de 60 segundos
- Melhor tratamento de erros HTTP

## 💡 Exemplos de Uso

### Exemplo 1: Importação com Preview

**Usuário:**
```
importar IN 680/2006 da RFB
```

**mAIke:**
```
🔍 Encontrei IN 680/2006
...
💡 Quer salvar esta legislação no banco para consultas futuras?
   Digite: 'sim, salvar' ou 'confirmar importação' para gravar.
```

**Usuário:**
```
sim, salvar
```

**mAIke:**
```
✅✅✅ IN 680/2006 gravada com sucesso!
...
💡 Agora você pode:
- Buscar trechos: 'o que a IN 680 fala sobre canal?'
- Consultar: 'mostre a IN 680'
```

### Exemplo 2: Legislação já importada

**Usuário:**
```
importar IN 680/2006
```

**mAIke:**
```
📚 IN 680/2006 já está importada no sistema!
📅 Data de importação: 2025-12-22 18:15:46
🔗 Fonte: https://www.gov.br/receitafederal/...

💡 Você pode buscar trechos usando: 'buscar trechos sobre [termo] na IN 680'
```

## 🔧 Arquivos Modificados

1. **`services/legislacao_service.py`**
   - Adicionado `modo_preview` em `importar_ato_por_url()` e `importar_ato_de_texto()`
   - Novo método `buscar_legislacao_preview()`

2. **`services/agents/legislacao_agent.py`**
   - Novo handler `_importar_legislacao_preview()`
   - Novo handler `_confirmar_importacao_legislacao()`

3. **`services/tool_definitions.py`**
   - Nova tool `importar_legislacao_preview`
   - Nova tool `confirmar_importacao_legislacao`
   - Tool `buscar_e_importar_legislacao` marcada como LEGADO

4. **`services/tool_router.py`**
   - Mapeamento das novas tools para `legislacao` agent

## ✅ Status

- ✅ Preview implementado
- ✅ Confirmação implementada
- ✅ Melhorias de extração aplicadas
- ✅ Tool definitions atualizadas
- ✅ Router atualizado
- ✅ Documentação criada

## 🚀 Próximos Passos (Opcional)

1. **UI com botões:** Adicionar botões [Salvar] [Descartar] na interface
2. **Cache de preview:** Manter preview em memória/sessão para confirmação
3. **Validação de preview:** Permitir editar dados antes de confirmar
4. **Sincronização SQL Server:** Job para replicar SQLite → SQL Server
5. **OCR para PDFs escaneados:** Integração com Tesseract

