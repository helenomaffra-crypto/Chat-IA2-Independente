# 🧠 Sistema de Contexto Persistente - mAIke

**Data:** 08/01/2026  
**Versão:** 1.0  
**Objetivo:** Manter contexto entre mensagens de forma escalável e automática

---

## 🎯 Visão Geral

O sistema de contexto persistente permite que o mAIke mantenha informações sobre consultas anteriores (extratos bancários, processos, relatórios) entre mensagens, permitindo follow-ups naturais sem precisar especificar todos os detalhes novamente.

### ❌ Problema Antigo

**Solução Não Escalável:**
- Adicionar exemplos no prompt para cada tipo de consulta
- Prompt fica muito longo e difícil de manter
- Cada nova funcionalidade precisa de exemplos específicos
- Não escalável para muitas funcionalidades

**Exemplo do problema:**
```
Usuário: "detalhe o extrato do santander"
mAIke: [mostra extrato com 20 transações]

Usuário: "detalhe os 20 lançamentos"
mAIke: ❌ Perde contexto → busca processo BND.0083/25 (errado!)
```

### ✅ Solução Atual (Contexto Persistente)

**Solução Escalável:**
- Sistema de contexto persistente no SQLite
- Salva contexto automaticamente quando tools retornam dados
- Detecta follow-ups usando contexto salvo
- Funciona para qualquer tipo de consulta (extrato, processo, relatório, etc.)

**Exemplo da solução:**
```
Usuário: "detalhe o extrato do santander"
mAIke: [mostra extrato] → ✅ Salva contexto automaticamente

Usuário: "detalhe os 20 lançamentos"
mAIke: ✅ Detecta follow-up → Usa contexto salvo → Consulta extrato novamente
```

---

## 🏗️ Arquitetura do Sistema

### 1. Salvamento Automático de Contexto

**Quando:** Automaticamente quando tools retornam dados com sucesso

**Onde:** No agent específico (ex: `SantanderAgent._consultar_extrato()`)

**O que salva:**
- Tipo de consulta (extrato_bancario, processo, relatorio, etc.)
- Parâmetros da consulta (banco, agência, conta, datas, etc.)
- Metadados (total de transações, período, etc.)

**Exemplo de implementação:**
```python
# Em SantanderAgent._consultar_extrato()
resultado = self.santander_service.consultar_extrato(...)

# ✅ Salvar contexto quando sucesso
if resultado.get('sucesso') and context:
    session_id = context.get('session_id')
    if session_id:
        from services.context_service import salvar_contexto_sessao
        
        salvar_contexto_sessao(
            session_id=session_id,
            tipo_contexto='ultima_consulta',
            chave='extrato_bancario',
            valor='extrato_santander',
            dados_adicionais={
                'banco': 'SANTANDER',
                'agencia': agencia,
                'conta': conta,
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'dias': dias,
                'total_transacoes': len(resultado.get('dados', [])),
                'timestamp': datetime.now().isoformat()
            }
        )
```

### 2. Detecção de Follow-ups

**Quando:** No `PrecheckService` antes de chamar a IA

**Onde:** `PrecheckService.tentar_responder_sem_ia()`

**Como detecta:**
- Padrões de follow-up: "melhorar relatório", "detalhar lançamentos", "enviar por email"
- Busca contexto salvo da sessão
- Retorna tool call com parâmetros do contexto salvo

**Exemplo de implementação:**
```python
# Padrões de follow-up
padroes_followup_extrato = [
    r'melhor[ae]r?\s+(?:esse|o)?\s*relat[oó]rio',
    r'detalh[ae]r?\s+(?:os|as)?\s*\d+\s+lan[çc]amentos',
    r'detalh[ae]r?\s+(?:os|as)?\s*lan[çc]amentos',
    r'envie?\s+(?:esse|o)?\s*relat[oó]rio',
]

eh_followup_extrato = any(re.search(p, mensagem_lower) for p in padroes_followup_extrato)
if eh_followup_extrato and session_id:
    contextos = buscar_contexto_sessao(session_id, tipo_contexto='ultima_consulta', chave='extrato_bancario')
    
    if contextos:
        ctx_extrato = contextos[0]
        dados_extrato = ctx_extrato.get('dados', {})
        banco = dados_extrato.get('banco', '')
        
        if banco == 'SANTANDER':
            return {
                'tool_calls': [{
                    'function': {
                        'name': 'consultar_extrato_santander',
                        'arguments': {
                            'agencia': dados_extrato.get('agencia'),
                            'conta': dados_extrato.get('conta'),
                            'data_inicio': dados_extrato.get('data_inicio'),
                            'data_fim': dados_extrato.get('data_fim'),
                            'dias': dados_extrato.get('dias', 7)
                        }
                    }
                }],
                '_contexto_extrato': dados_extrato  # Flag para indicar follow-up
            }
```

### 3. Formatação de Contexto no Prompt

**Quando:** Quando constrói o prompt para a IA

**Onde:** `formatar_contexto_para_prompt()` em `context_service.py`

**O que inclui:**
- Contexto formatado de forma compacta
- Informações relevantes (banco, total de transações, etc.)
- Instruções para a IA usar o contexto apenas se relevante

**Exemplo:**
```python
# Contexto formatado no prompt:
"""
📌 **CONTEXTO:** Última consulta: Extrato SANTANDER (50 transações)

💡 Use esse contexto APENAS se a mensagem do usuário for relacionada ao extrato mencionado.
⚠️ Se o usuário mencionar outro banco ou fizer pergunta genérica, IGNORE este contexto.
"""
```

---

## 📊 Estrutura de Dados

### Tabela `contexto_sessao` (SQLite)

```sql
CREATE TABLE IF NOT EXISTS contexto_sessao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(100) NOT NULL,
    tipo_contexto VARCHAR(50) NOT NULL,      -- 'ultima_consulta', 'processo_atual', etc.
    chave VARCHAR(100) NOT NULL,              -- 'extrato_bancario', 'processo', etc.
    valor VARCHAR(255),                       -- Valor simples (ex: 'extrato_santander')
    dados_json TEXT,                          -- JSON com dados adicionais
    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(session_id, tipo_contexto, chave)
);
```

### Tipos de Contexto

1. **`ultima_consulta`** - Última consulta realizada (extrato, processo, relatório)
   - **`extrato_bancario`** - Extrato bancário consultado
   - **`processo`** - Processo consultado (futuro)
   - **`relatorio`** - Relatório gerado (futuro)

2. **`processo_atual`** - Processo em foco atual (já implementado)

3. **`categoria_atual`** - Categoria em foco atual (já implementado)

---

## 🔧 Implementação

### 1. Adicionar Salvamento de Contexto em Nova Tool

**Quando:** Após uma tool retornar dados com sucesso

**Onde:** No agent específico (ex: `MeuAgent._minha_tool()`)

**Como fazer:**
```python
def _minha_tool(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Executar tool
    resultado = self.service.minha_tool(...)
    
    # ✅ NOVO: Salvar contexto quando sucesso
    if resultado.get('sucesso') and context:
        try:
            session_id = context.get('session_id')
            if session_id:
                from services.context_service import salvar_contexto_sessao
                from datetime import datetime
                
                # Extrair dados relevantes para contexto
                dados_contexto = {
                    'parametro1': arguments.get('parametro1'),
                    'parametro2': arguments.get('parametro2'),
                    'total_itens': len(resultado.get('dados', [])),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Salvar contexto
                salvar_contexto_sessao(
                    session_id=session_id,
                    tipo_contexto='ultima_consulta',  # ou outro tipo apropriado
                    chave='minha_consulta',  # Chave única para este tipo
                    valor='minha_tool',  # Valor identificador
                    dados_adicionais=dados_contexto
                )
                logger.debug(f"[CONTEXTO] Contexto de minha_tool salvo")
        except Exception as e:
            logger.debug(f"[CONTEXTO] Erro ao salvar contexto: {e}")
    
    return resultado
```

### 2. Adicionar Detecção de Follow-up

**Quando:** No `PrecheckService` para detectar follow-ups antes da IA

**Onde:** `PrecheckService.tentar_responder_sem_ia()`

**Como fazer:**
```python
# ✅ NOVO: Detectar follow-ups de minha_consulta
padroes_followup_minha = [
    r'melhor[ae]r?\s+(?:esse|o)?\s*relat[oó]rio',
    r'detalh[ae]r?\s+(?:os|as)?\s*\d+\s+itens',
    r'envie?\s+(?:esse|o)?\s*relat[oó]rio',
]

eh_followup_minha = any(re.search(p, mensagem_lower) for p in padroes_followup_minha)
if eh_followup_minha and session_id:
    try:
        from services.context_service import buscar_contexto_sessao
        contextos = buscar_contexto_sessao(
            session_id, 
            tipo_contexto='ultima_consulta', 
            chave='minha_consulta'
        )
        
        if contextos:
            ctx_minha = contextos[0]
            dados = ctx_minha.get('dados', {})
            
            logger.info(f"[PRECHECK] Follow-up de minha_consulta detectado")
            
            # Retornar tool call com parâmetros do contexto
            return {
                'tool_calls': [{
                    'function': {
                        'name': 'minha_tool',
                        'arguments': {
                            'parametro1': dados.get('parametro1'),
                            'parametro2': dados.get('parametro2'),
                            # Incluir todos os parâmetros salvos
                        }
                    }
                }],
                '_contexto_minha': dados  # Flag para indicar follow-up
            }
    except Exception as e:
        logger.debug(f"[PRECHECK] Erro ao detectar follow-up: {e}")
```

### 3. Melhorar Formatação de Contexto

**Quando:** Quando precisa incluir novo tipo de contexto no prompt

**Onde:** `formatar_contexto_para_prompt()` em `context_service.py`

**Como fazer:**
```python
elif tipo == 'ultima_consulta':
    for ctx in lista:
        chave = ctx.get('chave', '')
        valor = ctx.get('valor', '')
        dados = ctx.get('dados', {})
        
        # ✅ Formatação específica para cada tipo
        if chave == 'extrato_bancario':
            banco = dados.get('banco', '')
            total_transacoes = dados.get('total_transacoes', 0)
            partes.append(f"Última consulta: Extrato {banco} ({total_transacoes} transações)")
        elif chave == 'minha_consulta':
            total_itens = dados.get('total_itens', 0)
            partes.append(f"Última consulta: Minha Tool ({total_itens} itens)")
        else:
            partes.append(f"Última: {valor}")
```

---

## 📝 Exemplos de Uso

### Exemplo 1: Extrato Bancário Santander

**Fluxo completo:**
```
1. Usuário: "detalhe o extrato do santander"
   → PrecheckService detecta comando de extrato
   → SantanderAgent._consultar_extrato() é chamado
   → Extrato é retornado com sucesso
   → ✅ Contexto é salvo automaticamente:
      {
        tipo_contexto: 'ultima_consulta',
        chave: 'extrato_bancario',
        valor: 'extrato_santander',
        dados: {
          banco: 'SANTANDER',
          agencia: '3003',
          conta: '000130827180',
          dias: 7,
          total_transacoes: 50
        }
      }

2. Usuário: "vc consegue melhorar esse relatorio?"
   → PrecheckService detecta padrão "melhorar esse relatorio"
   → Busca contexto salvo (ultima_consulta, extrato_bancario)
   → ✅ Encontra contexto do extrato Santander
   → Retorna tool call: consultar_extrato_santander(agencia='3003', conta='000130827180', dias=7)
   → Extrato é consultado novamente e formatado de forma melhorada

3. Usuário: "detalhe os 20 lançamentos"
   → PrecheckService detecta padrão "detalhar lançamentos"
   → Busca contexto salvo novamente
   → ✅ Encontra contexto do extrato
   → Retorna tool call com mesmos parâmetros
   → Extrato é detalhado com todos os 20 lançamentos

4. Usuário: "envie esse relatorio melhorado por email para helenomaffra@gmail.com"
   → PrecheckService detecta padrão "envie esse relatorio"
   → Busca contexto salvo
   → ✅ Encontra contexto do extrato
   → EmailPrecheckService detecta envio de email
   → Consulta extrato novamente e envia por email
```

### Exemplo 2: Extrato Banco do Brasil

**Fluxo:**
```
1. Usuário: "extrato do BB"
   → BancoBrasilAgent._consultar_extrato() é chamado
   → ✅ Contexto salvo automaticamente:
      {
        tipo_contexto: 'ultima_consulta',
        chave: 'extrato_bancario',
        valor: 'extrato_bb',
        dados: {
          banco: 'BB',
          agencia: '1251',
          conta: '50483',
          data_inicio: '2026-01-01',
          data_fim: '2026-01-08',
          total_transacoes: 30
        }
      }

2. Usuário: "melhore esse relatorio"
   → PrecheckService detecta follow-up
   → ✅ Usa contexto salvo do BB
   → Consulta extrato BB novamente com mesmos parâmetros
```

---

## 🎯 Boas Práticas

### 1. Quando Salvar Contexto

**✅ Salve contexto quando:**
- Tool retorna dados que o usuário pode querer melhorar/detalhar/enviar
- Consulta retorna múltiplos itens (extratos, processos, relatórios)
- Usuário pode fazer follow-ups naturais ("melhore", "detalhe", "envie")

**❌ NÃO salve contexto quando:**
- Tool retorna erro (não há dados para seguir)
- Consulta retorna resultado único e específico (não precisa de follow-up)
- Tool não é consulta (ex: criar, atualizar, deletar)

### 2. Que Dados Salvar

**✅ Salve:**
- Parâmetros necessários para refazer a consulta
- Metadados úteis (total de itens, período, etc.)
- Informações de identificação (banco, conta, processo, etc.)

**❌ NÃO salve:**
- Dados completos dos resultados (podem ser grandes)
- Informações sensíveis (senhas, tokens)
- Dados que mudam rapidamente (timestamps precisos)

### 3. Padrões de Follow-up

**Padrões recomendados:**
```python
# Melhorar/formatar
r'melhor[ae]r?\s+(?:esse|o)?\s*relat[oó]rio'
r'melhor[ae]r?\s+(?:esse|o)?\s*extrato'
r'format[ae]r?\s+(?:esse|o)?\s*relat[oó]rio'

# Detalhar
r'detalh[ae]r?\s+(?:os|as)?\s*\d+\s+(?:lan[çc]amentos|transa[çc][õo]es|itens)'
r'detalh[ae]r?\s+(?:os|as)?\s*(?:lan[çc]amentos|transa[çc][õo]es|itens)'
r'mostr[ae]r?\s+todos\s+os?\s*(?:lan[çc]amentos|transa[çc][õo]es|itens)'

# Enviar
r'envie?\s+(?:esse|o)?\s*relat[oó]rio'
r'envi[ae]r?\s+(?:esse|o)?\s*relat[oó]rio'
r'mande\s+(?:esse|o)?\s*relat[oó]rio'
r'envi[ae]r?\s+(?:esse|o)?\s*por\s+email'
```

### 4. Limpeza de Contexto

**Quando limpar:**
- Quando usuário muda de assunto completamente (detectado automaticamente)
- Quando contexto expira (opcional, implementar TTL)
- Quando sessão termina (limpar ao criar nova sessão)

**Como limpar:**
```python
from services.context_service import limpar_contexto_sessao

# Limpar contexto específico
limpar_contexto_sessao(session_id, tipo_contexto='ultima_consulta')

# Limpar todo contexto da sessão
limpar_contexto_sessao(session_id)
```

---

## 🔍 Troubleshooting

### Problema: Contexto não está sendo salvo

**Causas possíveis:**
1. `session_id` não está sendo passado no `context`
2. Tool não está retornando `sucesso: True`
3. Erro ao salvar (ver logs)

**Solução:**
```python
# Verificar se session_id está no context
logger.debug(f"[CONTEXTO] session_id: {context.get('session_id') if context else None}")

# Verificar se resultado tem sucesso
logger.debug(f"[CONTEXTO] sucesso: {resultado.get('sucesso')}")

# Verificar erro ao salvar
try:
    salvar_contexto_sessao(...)
except Exception as e:
    logger.error(f"[CONTEXTO] Erro ao salvar: {e}", exc_info=True)
```

### Problema: Follow-up não está sendo detectado

**Causas possíveis:**
1. Padrão regex não está capturando a mensagem
2. Contexto não foi salvo anteriormente
3. `session_id` diferente entre mensagens

**Solução:**
```python
# Testar padrão regex
import re
mensagem = "melhore esse relatorio"
padrao = r'melhor[ae]r?\s+(?:esse|o)?\s*relat[oó]rio'
match = re.search(padrao, mensagem.lower())
logger.debug(f"[PRECHECK] Padrão match: {bool(match)}")

# Verificar contexto salvo
contextos = buscar_contexto_sessao(session_id, tipo_contexto='ultima_consulta')
logger.debug(f"[PRECHECK] Contextos encontrados: {len(contextos)}")

# Verificar session_id
logger.debug(f"[PRECHECK] session_id: {session_id}")
```

### Problema: Contexto sendo usado incorretamente

**Causas possíveis:**
1. Contexto antigo não foi limpo
2. Contexto de outro assunto está interferindo
3. Formatação de contexto no prompt está errada

**Solução:**
```python
# Limpar contexto antigo antes de salvar novo
limpar_contexto_sessao(session_id, tipo_contexto='ultima_consulta')

# Verificar contexto atual antes de usar
contextos = buscar_contexto_sessao(session_id, tipo_contexto='ultima_consulta')
for ctx in contextos:
    logger.debug(f"[CONTEXTO] Contexto atual: {ctx.get('chave')} = {ctx.get('valor')}")
    logger.debug(f"[CONTEXTO] Dados: {ctx.get('dados')}")

# Validar se contexto é relevante antes de usar
if ctx.get('chave') == 'extrato_bancario':
    # Usar contexto
    pass
else:
    # Contexto não relevante, não usar
    pass
```

---

## 📚 Tipos de Contexto Implementados

### ✅ `ultima_consulta.extrato_bancario`

**Implementado em:**
- `SantanderAgent._consultar_extrato()`
- `BancoBrasilAgent._consultar_extrato()`

**Dados salvos:**
- `banco`: 'SANTANDER' ou 'BB'
- `agencia`: Número da agência
- `conta`: Número da conta
- `data_inicio`: Data inicial (YYYY-MM-DD)
- `data_fim`: Data final (YYYY-MM-DD)
- `dias`: Número de dias (se usado)
- `total_transacoes`: Total de transações retornadas

**Follow-ups detectados:**
- "melhorar esse relatório"
- "detalhar os X lançamentos"
- "enviar esse relatório por email"

### 🔜 `ultima_consulta.processo` (Futuro)

**Quando implementar:**
- Quando usuário consulta processo específico
- Permite follow-ups: "e a DI?", "e a DUIMP?", "envie por email"

**Dados a salvar:**
- `processo_referencia`: Referência do processo
- `categoria`: Categoria do processo
- `tem_di`: Se tem DI
- `tem_duimp`: Se tem DUIMP
- `tem_ce`: Se tem CE

### 🔜 `ultima_consulta.relatorio` (Futuro)

**Quando implementar:**
- Quando usuário gera relatório (FOB, averbações, etc.)
- Permite follow-ups: "melhore", "envie por email", "gerar PDF"

**Dados a salvar:**
- `tipo_relatorio`: 'fob', 'averbacoes', etc.
- `mes`: Mês do relatório
- `ano`: Ano do relatório
- `categoria`: Categoria (se aplicável)

---

## 🚀 Adicionar Novo Tipo de Contexto

### Passo 1: Salvar Contexto no Agent

```python
# Em MeuAgent._minha_tool()
resultado = self.service.minha_tool(...)

if resultado.get('sucesso') and context:
    session_id = context.get('session_id')
    if session_id:
        from services.context_service import salvar_contexto_sessao
        from datetime import datetime
        
        salvar_contexto_sessao(
            session_id=session_id,
            tipo_contexto='ultima_consulta',  # ou outro tipo
            chave='minha_consulta',  # Chave única
            valor='minha_tool',  # Valor identificador
            dados_adicionais={
                'param1': arguments.get('param1'),
                'param2': arguments.get('param2'),
                'total': len(resultado.get('dados', [])),
                'timestamp': datetime.now().isoformat()
            }
        )
```

### Passo 2: Detectar Follow-ups no PrecheckService

```python
# Em PrecheckService.tentar_responder_sem_ia()
padroes_followup_minha = [
    r'melhor[ae]r?\s+(?:esse|o)?\s*relat[oó]rio',
    r'detalh[ae]r?\s+(?:os|as)?\s*\d+\s+itens',
]

eh_followup_minha = any(re.search(p, mensagem_lower) for p in padroes_followup_minha)
if eh_followup_minha and session_id:
    contextos = buscar_contexto_sessao(session_id, tipo_contexto='ultima_consulta', chave='minha_consulta')
    if contextos:
        ctx = contextos[0]
        dados = ctx.get('dados', {})
        
        return {
            'tool_calls': [{
                'function': {
                    'name': 'minha_tool',
                    'arguments': {
                        'param1': dados.get('param1'),
                        'param2': dados.get('param2'),
                    }
                }
            }]
        }
```

### Passo 3: Melhorar Formatação no Prompt (Opcional)

```python
# Em formatar_contexto_para_prompt()
elif tipo == 'ultima_consulta':
    for ctx in lista:
        chave = ctx.get('chave', '')
        dados = ctx.get('dados', {})
        
        if chave == 'minha_consulta':
            total = dados.get('total', 0)
            partes.append(f"Última consulta: Minha Tool ({total} itens)")
```

---

## 📊 Comparação: Prompt vs Contexto Persistente

| Aspecto | Prompt (Antigo) | Contexto Persistente (Atual) |
|---------|----------------|------------------------------|
| **Escalabilidade** | ❌ Precisa adicionar exemplos para cada assunto | ✅ Funciona automaticamente para qualquer tipo |
| **Manutenibilidade** | ❌ Prompt fica muito longo | ✅ Lógica centralizada e modular |
| **Performance** | ⚠️ Prompt maior = mais tokens = mais custo | ✅ Contexto compacto = menos tokens |
| **Precisão** | ⚠️ Depende de exemplos perfeitos | ✅ Usa dados reais da última consulta |
| **Flexibilidade** | ❌ Precisa prever todos os casos | ✅ Funciona com qualquer follow-up |

---

## 🎯 Vantagens do Sistema Atual

1. **✅ Escalável:** Funciona para qualquer tipo de consulta sem adicionar exemplos
2. **✅ Automático:** Salva contexto automaticamente quando tools retornam sucesso
3. **✅ Determinístico:** Usa dados reais da última consulta, não inferências
4. **✅ Modular:** Lógica separada por agent (fácil de manter)
5. **✅ Flexível:** Pode ser estendido para outros tipos de contexto

---

## ⚠️ Limitações Conhecidas

1. **Session ID:** Requer `session_id` consistente entre mensagens
2. **Contexto Antigo:** Contexto antigo pode interferir se não limpar
3. **Follow-ups Ambíguos:** Padrões de follow-up podem capturar mensagens não relacionadas
4. **Performance:** Busca no SQLite adiciona latência (minimal)

---

## 🧪 Testes

### Teste 1: Salvamento de Contexto

```python
# Testar salvamento
from services.context_service import salvar_contexto_sessao, buscar_contexto_sessao

salvar_contexto_sessao(
    session_id='test_session',
    tipo_contexto='ultima_consulta',
    chave='extrato_bancario',
    valor='extrato_santander',
    dados_adicionais={'banco': 'SANTANDER', 'total_transacoes': 50}
)

# Buscar contexto
contextos = buscar_contexto_sessao('test_session', tipo_contexto='ultima_consulta', chave='extrato_bancario')
assert len(contextos) == 1
assert contextos[0]['dados']['banco'] == 'SANTANDER'
assert contextos[0]['dados']['total_transacoes'] == 50
```

### Teste 2: Detecção de Follow-up

```python
# Testar detecção
from services.precheck_service import PrecheckService
from services.chat_service import ChatService

precheck = PrecheckService(ChatService())
mensagem = "melhore esse relatorio"

resultado = precheck.tentar_responder_sem_ia(
    mensagem=mensagem,
    session_id='test_session'  # Mesmo session_id usado no teste 1
)

assert resultado is not None
assert resultado.get('tool_calls') is not None
assert resultado['tool_calls'][0]['function']['name'] == 'consultar_extrato_santander'
```

---

## 📝 Checklist para Nova Implementação

- [ ] Salvar contexto no agent quando tool retorna sucesso
- [ ] Adicionar padrões de follow-up no PrecheckService
- [ ] Testar salvamento de contexto
- [ ] Testar detecção de follow-up
- [ ] Testar fluxo completo (consulta → follow-up → resultado)
- [ ] Adicionar formatação no prompt (opcional)
- [ ] Documentar novo tipo de contexto neste manual

---

**Última atualização:** 08/01/2026  
**Versão:** 1.0

