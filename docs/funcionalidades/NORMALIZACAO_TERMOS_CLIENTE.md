# Normalização de Termos de Cliente

## 📋 Visão Geral

Sistema de normalização automática de termos de cliente para categorias de processo, permitindo que o usuário use nomes de clientes (ex: "Diamond", "Bandimar") em vez de códigos de categoria (ex: "DMD", "BND").

**Exemplo:**
- Usuário: "como estão os processos do Diamond?"
- Sistema: Normaliza "Diamond" → "DMD" e chama `listar_processos_por_categoria(categoria="DMD")`

## 🎯 Funcionalidades

- ✅ Normalização automática de termos de cliente para categorias
- ✅ Prioridade sobre contexto anterior (regras aprendidas têm precedência)
- ✅ Proteção contra interferência com comandos específicos (email, extrato, etc.)
- ✅ Feature flag para habilitar/desabilitar (`ENABLE_CLIENTE_NORMALIZER`)
- ✅ Suporte a múltiplos formatos de regras aprendidas

## 🔧 Como Funciona

### 1. Ordem de Execução

A normalização é executada **no final do PrecheckService**, **antes** de passar para a IA:

```
PrecheckService.tentar_responder_sem_ia():
  0) Ver emails
  1) Legislação
  2) Importação legislação
  3) Relatório FOB
  4) Relatório averbações
  5) Extrato BB
  6) TECwin NCM
  7) Follow-up processo
  8) Situação processo
  9) Email
  10) Perguntas NCM
  11) ✅ NOVO: Normalização de termos de cliente
  → return None (se nada encontrado)
```

### 2. Proteções Implementadas

#### ✅ Proteção 1: Não interfere com comandos específicos

A normalização **NÃO** é executada se a mensagem contém comandos específicos:
- `ver email`, `detalhe email`
- `extrato do banco`, `extrato do santander`, `extrato do BB`
- `fechar dia`, `fechamento`
- `o que temos pra hoje`, `dashboard`
- `tecwin`, `legislacao`, `importar legislacao`
- `relatorio fob`, `relatorio averbacoes`
- `gerar pdf`, `pdf do extrato`
- `calcular impostos`, `calcule os impostos`
- `criar duimp`, `montar duimp`
- `consultar ncm`, `sugerir ncm`

#### ✅ Proteção 2: Não normaliza se já tem categoria explícita

Se a mensagem já contém uma categoria explícita (ex: "como estão os DMD?"), a normalização **NÃO** é executada.

#### ✅ Proteção 3: Só normaliza perguntas sobre processos

A normalização **SÓ** é executada se a mensagem parece ser uma pergunta sobre processos:
- `como estão`
- `quais processos`
- `mostre processos`
- `listar processos`
- `processos do`
- `processos de`
- `status dos processos`
- `situacao dos processos`

## 📝 Como Criar Regras Aprendidas

### ✅ Método 1: Via Chat (Recomendado - Mais Fácil!)

Você pode criar regras diretamente no chat de forma natural:

**Exemplos:**
- "maike o ALH vai ser alho ok?"
- "maike Diamond vai ser DMD"
- "maike Bandimar vai ser BND"
- "maike quando eu falar diamonds, use DMD"

A IA automaticamente detecta que é um mapeamento cliente→categoria e cria a regra aprendida.

### Método 2: Via Script Python

#### Formato 1: Seta ou Igual (Recomendado)

```python
from services.learned_rules_service import salvar_regra_aprendida

salvar_regra_aprendida(
    tipo_regra='cliente_categoria',
    contexto='normalizacao_cliente',
    nome_regra='Diamond → DMD',
    descricao='Mapeia o termo "Diamond" para a categoria DMD',
    aplicacao_texto='Diamond → DMD'
)
```

### Formato 2: Igual ou Dois Pontos

```python
salvar_regra_aprendida(
    tipo_regra='cliente_categoria',
    contexto='normalizacao_cliente',
    nome_regra='Bandimar=BND',
    descricao='Mapeia o termo "Bandimar" para a categoria BND',
    aplicacao_texto='Bandimar=BND'
)
```

### Formato 3: Nome Simples

```python
salvar_regra_aprendida(
    tipo_regra='cliente_categoria',
    contexto='normalizacao_cliente',
    nome_regra='Diamond',
    descricao='Mapeia Diamond para categoria DMD',
    aplicacao_texto='DMD'
)
```

### Exemplos de Regras

```python
# Diamond → DMD
salvar_regra_aprendida(
    tipo_regra='cliente_categoria',
    contexto='normalizacao_cliente',
    nome_regra='Diamond → DMD',
    descricao='Mapeia "Diamond" e "diamonds" para categoria DMD',
    aplicacao_texto='Diamond → DMD'
)

# Bandimar → BND
salvar_regra_aprendida(
    tipo_regra='cliente_categoria',
    contexto='normalizacao_cliente',
    nome_regra='Bandimar → BND',
    descricao='Mapeia "Bandimar" para categoria BND',
    aplicacao_texto='Bandimar → BND'
)
```

## 🧪 Testes

### Teste Manual

1. **Criar regra aprendida via chat:**
   - "maike o ALH vai ser alho ok?"
   - "maike Diamond vai ser DMD"
   - "maike Bandimar vai ser BND"

   Ou via script Python:
```python
from services.learned_rules_service import salvar_regra_aprendida

salvar_regra_aprendida(
    tipo_regra='cliente_categoria',
    contexto='normalizacao_cliente',
    nome_regra='Diamond → DMD',
    descricao='Mapeia Diamond para DMD',
    aplicacao_texto='Diamond → DMD'
)
```

2. **Testar no chat:**
- "como estão os processos do Diamond?" → deve retornar processos DMD
- "como estão os diamonds?" → deve retornar processos DMD
- "como estão os DMD?" → deve retornar processos DMD (sem normalização, já tem categoria)

3. **Verificar logs:**
```
[PRECHECK] Termo de cliente normalizado para categoria: DMD
```

### Teste de Proteções

1. **Comando específico não deve normalizar:**
- "ver email" → não deve normalizar
- "extrato do BB" → não deve normalizar
- "o que temos pra hoje" → não deve normalizar

2. **Categoria explícita não deve normalizar:**
- "como estão os DMD?" → não deve normalizar (já tem categoria)

3. **Pergunta não sobre processos não deve normalizar:**
- "qual a ncm de oculos" → não deve normalizar

## ⚙️ Configuração

### Feature Flag

A normalização pode ser habilitada/desabilitada via variável de ambiente:

```bash
# Habilitar (padrão)
ENABLE_CLIENTE_NORMALIZER=true

# Desabilitar
ENABLE_CLIENTE_NORMALIZER=false
```

### Desabilitar Temporariamente

Se houver problemas, você pode desabilitar rapidamente:

1. **Via .env:**
```bash
echo "ENABLE_CLIENTE_NORMALIZER=false" >> .env
```

2. **Via código (comentando):**
```python
# if os.getenv('ENABLE_CLIENTE_NORMALIZER', 'true').lower() == 'true':
#     categoria_normalizada = self._normalizar_termo_cliente(mensagem, mensagem_lower)
```

## 🔍 Debug

### Logs

A normalização gera logs detalhados:

```
[PRECHECK] Termo de cliente normalizado para categoria: DMD
[PRECHECK] Mapeamento encontrado (formato seta): 'diamond' → 'DMD'
[PRECHECK] ✅ Termo 'diamond' encontrado na mensagem → categoria 'DMD'
```

### Verificar Regras Aprendidas

```python
from services.learned_rules_service import buscar_regras_aprendidas

regras = buscar_regras_aprendidas(tipo_regra='cliente_categoria', ativas=True)
for regra in regras:
    print(f"{regra['nome_regra']}: {regra['descricao']}")
```

## 📊 Exemplos de Uso

### Exemplo 1: Normalização Básica

**Usuário:** "como estão os processos do Diamond?"

**Sistema:**
1. Detecta que não é comando específico
2. Detecta que não tem categoria explícita
3. Detecta que é pergunta sobre processos
4. Busca regras aprendidas
5. Encontra mapeamento "Diamond → DMD"
6. Retorna `listar_processos_por_categoria(categoria="DMD")`

### Exemplo 2: Múltiplos Termos

**Regras:**
- "Diamond" → DMD
- "diamonds" → DMD
- "Bandimar" → BND

**Usuário:** "como estão os diamonds?"

**Sistema:** Normaliza para DMD

### Exemplo 3: Proteção contra Comandos

**Usuário:** "extrato do Diamond"

**Sistema:** NÃO normaliza (é comando de extrato)

### Exemplo 4: Proteção contra Categoria Explícita

**Usuário:** "como estão os DMD?"

**Sistema:** NÃO normaliza (já tem categoria explícita)

## ⚠️ Limitações

1. **Apenas perguntas sobre processos:** A normalização só funciona para perguntas sobre processos/categorias
2. **Regras aprendidas necessárias:** É necessário criar regras aprendidas antes de usar
3. **Formato de regras:** As regras devem seguir um dos formatos suportados
4. **Case-insensitive:** A busca é case-insensitive, mas a categoria retornada é sempre UPPERCASE

## 🚀 Próximos Passos

1. **Interface para criar regras:** Criar interface no chat para criar regras aprendidas
2. **Validação de categorias:** Validar se a categoria retornada é válida
3. **Cache de mapeamentos:** Cachear mapeamentos em memória para melhor performance
4. **Suporte a múltiplas palavras:** Suporte a termos compostos (ex: "Diamond Brasil")

## 📚 Referências

- `services/precheck_service.py` - Implementação principal
- `services/learned_rules_service.py` - Gerenciamento de regras aprendidas
- `AGENTS.md` - Documentação geral do projeto

