# 📚 Melhorias na Importação de Legislação por URL

## 🎯 Objetivo

Melhorar o tratamento de URLs problemáticas (SPAs) e conteúdo insuficiente na importação de legislação, orientando o usuário a usar importação manual (copiar/colar) quando necessário.

## 📝 Mudanças Implementadas

### 1. Arquivo: `services/legislacao_service.py`

#### ✅ Constante de Domínios Problemáticos

**Linha ~48:** Adicionada constante `DOMINIOS_SOMENTE_COPIA_COLA`:
```python
DOMINIOS_SOMENTE_COPIA_COLA = {
    "normasinternet2.receita.fazenda.gov.br",
    # Adicionar outros domínios problemáticos aqui conforme necessário
}
```

#### ✅ Método Auxiliar para Extrair Domínio

**Linha ~62:** Novo método `_extrair_dominio_da_url()`:
- Extrai o domínio de uma URL
- Remove porta se houver
- Retorna domínio em minúsculas

#### ✅ Validação de Domínio Antes de Baixar

**Linha ~299:** Em `importar_ato_por_url()`, adicionada verificação ANTES de fazer `requests.get()`:
- Extrai domínio da URL
- Se domínio está em `DOMINIOS_SOMENTE_COPIA_COLA`, retorna erro estruturado imediatamente
- **NÃO tenta baixar** conteúdo de sites problemáticos

**Retorno quando domínio é problemático:**
```python
{
    'sucesso': False,
    'erro': 'SITE_SOMENTE_COPIA_COLA',
    'mensagem': 'Este site usa carregamento dinâmico (SPA)...',
    'detalhes': {
        'dominio': 'normasinternet2.receita.fazenda.gov.br',
        'url': url
    }
}
```

#### ✅ Validação de Conteúdo Extraído

**Linha ~360:** Validações após extrair texto:

1. **Tamanho mínimo:** Pelo menos 500 caracteres (antes era 100)
   - Se menor, retorna `CONTEUDO_INSUFICIENTE_URL`

2. **Presença de artigos:** Deve conter padrão `Art. \d+`
   - Se não tiver, retorna `CONTEUDO_INSUFICIENTE_URL`

**Retorno quando conteúdo é insuficiente:**
```python
{
    'sucesso': False,
    'erro': 'CONTEUDO_INSUFICIENTE_URL',
    'mensagem': 'Não foi possível extrair o texto completo...',
    'detalhes': {
        'url': url,
        'tamanho_texto': len(texto_extraido),
        'tem_artigos': False  # se aplicável
    }
}
```

#### ✅ Retornos Estruturados em Todos os Erros

Todos os `except` blocks agora retornam dict estruturado com:
- `sucesso`: False
- `erro`: Código do erro (ex: `SITE_SOMENTE_COPIA_COLA`, `CONTEUDO_INSUFICIENTE_URL`, `TIMEOUT`, etc.)
- `mensagem`: Mensagem amigável para o usuário
- `detalhes`: Dict com informações adicionais (opcional)

### 2. Arquivo: `services/agents/legislacao_agent.py`

#### ✅ Uso de Mensagens Amigáveis

**Linha ~340, ~510, ~645:** Handlers ajustados para:
- Usar `mensagem` do resultado quando disponível
- Adicionar orientações específicas baseadas no tipo de erro
- Orientar usuário a usar copiar/colar quando for erro de SPA ou conteúdo insuficiente

## 🧪 Comportamento nos 3 Cenários

### Caso 1: URL de site "normal" (funciona)

**Chamada:**
```python
service.importar_ato_por_url(
    tipo_ato="IN",
    numero="680",
    ano=2006,
    sigla_orgao="RFB",
    url="https://www.algum-site-normal.gov.br/in680-2006"
)
```

**Comportamento:**
1. ✅ Domínio não está na lista problemática → continua
2. ✅ Baixa HTML com `requests.get()`
3. ✅ Extrai texto (ex: 5000 caracteres)
4. ✅ Texto contém "Art. 1º", "Art. 2º", etc.
5. ✅ Parseia e grava no SQLite
6. ✅ Retorna `sucesso=True`

### Caso 2: URL da Receita (normasinternet2) - SPA

**Chamada:**
```python
service.importar_ato_por_url(
    tipo_ato="IN",
    numero="1984",
    ano=2020,
    sigla_orgao="RFB",
    url="https://normasinternet2.receita.fazenda.gov.br/#/consulta/externa/113361/visao/multivigente"
)
```

**Comportamento:**
1. ✅ Extrai domínio: `normasinternet2.receita.fazenda.gov.br`
2. ✅ Domínio está em `DOMINIOS_SOMENTE_COPIA_COLA`
3. ✅ **NÃO faz `requests.get()`** (early return)
4. ✅ Retorna imediatamente:
   ```python
   {
       'sucesso': False,
       'erro': 'SITE_SOMENTE_COPIA_COLA',
       'mensagem': 'Este site usa carregamento dinâmico (SPA)...',
       'detalhes': {
           'dominio': 'normasinternet2.receita.fazenda.gov.br',
           'url': url
       }
   }
   ```

### Caso 3: Site não está na lista, mas não vem texto (SPA vazio)

**Chamada:**
```python
service.importar_ato_por_url(
    tipo_ato="IN",
    numero="1984",
    ano=2020,
    sigla_orgao="RFB",
    url="https://algum-site-spa.gov.br/in1984"
)
```

**Comportamento:**
1. ✅ Domínio não está na lista → continua
2. ✅ Baixa HTML com `requests.get()`
3. ✅ Extrai texto (ex: 200 caracteres - só HTML vazio da SPA)
4. ❌ Texto tem menos de 500 caracteres
5. ✅ Retorna:
   ```python
   {
       'sucesso': False,
       'erro': 'CONTEUDO_INSUFICIENTE_URL',
       'mensagem': 'Não foi possível extrair o texto completo...',
       'detalhes': {
           'url': url,
           'tamanho_texto': 200
       }
   }
   ```

**OU:**

1. ✅ Domínio não está na lista → continua
2. ✅ Baixa HTML
3. ✅ Extrai texto (ex: 1000 caracteres, mas só HTML/navegação)
4. ❌ Texto não contém "Art. \d+"
5. ✅ Retorna:
   ```python
   {
       'sucesso': False,
       'erro': 'CONTEUDO_INSUFICIENTE_URL',
       'mensagem': 'Não foi possível extrair o texto completo...',
       'detalhes': {
           'url': url,
           'tamanho_texto': 1000,
           'tem_artigos': False
       }
   }
   ```

## 🔧 Integração com Chat (mAIke)

### Como o Chat Usa os Retornos

**Exemplo no `LegislacaoAgent`:**
```python
resultado = self.legislacao_service.importar_ato_por_url(...)

if not resultado.get('sucesso'):
    erro = resultado.get('erro')
    mensagem_amigavel = resultado.get('mensagem', f'Erro: {erro}')
    
    # Usa mensagem amigável do serviço
    resposta = f'❌ {mensagem_amigavel}\n\n'
    
    # Adiciona orientações específicas
    if erro == 'SITE_SOMENTE_COPIA_COLA':
        resposta += '💡 Use a importação manual (copiar/colar)...'
```

### Resposta do mAIke ao Usuário

**Quando domínio é problemático:**
```
❌ Este site usa carregamento dinâmico (SPA) e o texto da legislação 
não pode ser extraído diretamente pela URL. Use a importação manual: 
copie o texto da página oficial e importe via importar_ato_de_texto.

💡 Use a importação manual (copiar/colar):
1. Abra a URL no seu navegador
2. Copie TODO o texto da legislação
3. Cole aqui e diga "importar este texto como IN 1984/2020"
   Ou execute: python3 scripts/importar_legislacao.py
```

## ✅ Garantias

1. **Não quebra código existente:**
   - `importar_ato_de_texto()` não foi alterado (continua 100% confiável)
   - Retornos mantêm compatibilidade (campos antigos ainda funcionam)
   - Novos campos são opcionais

2. **Não tenta soluções complexas:**
   - ❌ Sem Selenium/Playwright
   - ❌ Sem headless browser
   - ❌ Sem JavaScript execution
   - ✅ Apenas detecta e orienta para copiar/colar

3. **Retornos sempre estruturados:**
   - Todos os erros têm `mensagem` amigável
   - Códigos de erro padronizados
   - Detalhes opcionais para debug

## 📊 Resumo das Mudanças

| Arquivo | Mudança | Linha Aprox. |
|---------|---------|--------------|
| `legislacao_service.py` | Constante `DOMINIOS_SOMENTE_COPIA_COLA` | ~48 |
| `legislacao_service.py` | Método `_extrair_dominio_da_url()` | ~62 |
| `legislacao_service.py` | Validação de domínio (early return) | ~299 |
| `legislacao_service.py` | Validação de conteúdo (tamanho + artigos) | ~360 |
| `legislacao_service.py` | Retornos estruturados em todos os erros | ~405-440 |
| `legislacao_agent.py` | Uso de mensagens amigáveis | ~340, ~510, ~645 |

## 🚀 Próximos Passos (Opcional)

1. **Adicionar mais domínios problemáticos** conforme necessário
2. **Ajustar threshold de tamanho mínimo** se necessário (atualmente 500 caracteres)
3. **Melhorar detecção de artigos** (padrão regex pode ser refinado)
4. **Adicionar métricas/logging** para monitorar taxa de sucesso por domínio

