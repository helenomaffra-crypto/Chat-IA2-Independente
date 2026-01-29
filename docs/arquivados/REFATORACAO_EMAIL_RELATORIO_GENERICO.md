# Refatoração: Fluxo Genérico de Email para Relatórios

## 📋 Resumo Executivo

Esta refatoração generaliza o fluxo de envio de email para **qualquer relatório** gerado pela mAIke, eliminando a necessidade de criar funções específicas para cada tipo de relatório.

**Antes:** Cada relatório tinha sua própria lógica de salvamento e envio por email.  
**Depois:** Todos os relatórios usam o mesmo fluxo genérico baseado em `RelatorioGerado` DTO.

---

## 🏗️ Arquitetura da Solução

### 1. Modelo de Dados: `RelatorioGerado` (DTO)

**Arquivo:** `services/report_service.py`

**Responsabilidade:** Representar qualquer relatório de forma padronizada e serializável.

**Estrutura:**
```python
@dataclass
class RelatorioGerado:
    tipo_relatorio: str  # "o_que_tem_hoje", "como_estao_categoria", "fechamento_dia", etc.
    categoria: Optional[str]  # "MV5", "ALH", etc.
    texto_chat: str  # Texto exatamente como foi enviado para o usuário
    filtros: Optional[Dict[str, Any]]  # {"data_ref": "2025-12-19", "modal": "Marítimo"}
    meta_json: Optional[Dict[str, Any]]  # {"total_chegando": 5, "total_pendencias": 10}
    criado_em: Optional[str]  # Timestamp ISO
```

**Métodos:**
- `to_dict()` / `from_dict()`: Serialização/deserialização
- `to_json()` / `from_json()`: JSON string
- `gerar_chave_contexto()`: Gera chave única para salvar no contexto

**Por que `services/report_service.py`?**
- Centraliza lógica de relatórios
- Fácil de estender para novos tipos
- Separação clara de responsabilidades (dados vs. formatação vs. email)

### 2. Serviço de Gerenciamento: `report_service.py`

**Funções Principais:**

1. **`salvar_ultimo_relatorio(session_id, relatorio)`**
   - Salva relatório no contexto usando `context_service`
   - Tipo: `ultimo_relatorio`
   - Chave: gerada automaticamente (ex: `o_que_tem_hoje_MV5_2025-12-19`)

2. **`buscar_ultimo_relatorio(session_id, tipo_relatorio=None)`**
   - Busca último relatório da sessão
   - Se `tipo_relatorio` fornecido, busca específico; senão, busca o mais recente

3. **`criar_relatorio_gerado(...)`**
   - Helper para criar `RelatorioGerado` com valores padrão
   - Preenche `data_ref` automaticamente se não fornecido

### 3. Email Builder Genérico: `email_builder_service.py`

**Nova Função:** `montar_email_relatorio(relatorio, destinatario, nome_usuario)`

**Responsabilidades:**
- Gera assunto baseado no tipo de relatório (templates configuráveis)
- Monta corpo do email com saudação, introdução, relatório completo, encerramento
- Reutiliza estrutura existente (mesmo padrão de `montar_email_classificacao_ncm`)

**Templates de Assunto:**
```python
'o_que_tem_hoje': "Resumo diário – O que temos pra hoje - {categoria} - {data}"
'como_estao_categoria': "Status geral – {categoria}"
'fechamento_dia': "Fechamento do dia - {categoria} - {data}"
'relatorio_averbacoes': "Relatório de averbações - {categoria} - {periodo}"
```

**Estrutura do Email Gerado:**
```
Olá, [Nome],

[Introdução baseada no tipo]

[RELATÓRIO COMPLETO - texto_chat]

Qualquer dúvida, estamos à disposição.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores
```

### 4. Precheck Genérico: `precheck_service.py`

**Nova Função:** `_precheck_envio_email_relatorio_generico()`

**Detecta Padrões:**
- "envia esse relatório para X"
- "manda esse resumo para X"
- "envia esse dashboard para X"
- "manda esse fechamento para X"

**Fluxo:**
1. Detecta padrão + extrai email
2. Busca último relatório via `buscar_ultimo_relatorio()`
3. Se encontrou: monta email via `email_builder_service.montar_email_relatorio()`
4. Chama `enviar_email_personalizado` com preview (`confirmar_envio=false`)
5. Se não encontrou: retorna mensagem amigável

**Prioridade:** Alta (antes de outros prechecks de email)

### 5. Integração nos Pontos de Geração

**Arquivo:** `services/agents/processo_agent.py`

**Pontos Modificados:**

1. **`_obter_dashboard_hoje()`** (linha ~4199)
   - Após gerar resposta, salva via `salvar_ultimo_relatorio()`
   - Tipo: `o_que_tem_hoje`

2. **`_listar_por_categoria()`** (linha ~951)
   - Após gerar resposta, salva via `salvar_ultimo_relatorio()`
   - Tipo: `como_estao_categoria`

3. **`_fechar_dia()`** (linha ~5204)
   - Após gerar resposta, salva via `salvar_ultimo_relatorio()`
   - Tipo: `fechamento_dia`

**Padrão de Uso:**
```python
# Após gerar resposta
try:
    from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
    from datetime import datetime
    session_id_para_salvar = context.get('session_id') if context else None
    if session_id_para_salvar:
        relatorio = criar_relatorio_gerado(
            tipo_relatorio='tipo_aqui',
            texto_chat=resposta,
            categoria=categoria,
            filtros={'data_ref': datetime.now().strftime('%Y-%m-%d')},
            meta_json={'total': len(dados)}
        )
        salvar_ultimo_relatorio(session_id_para_salvar, relatorio)
except Exception as e:
    logger.debug(f'Erro ao salvar relatório no contexto: {e}')
```

### 6. Integração com Fluxo de Confirmação

**Reutiliza:** Mecanismo existente de `ultima_resposta_aguardando_email`

**Fluxo:**
1. Precheck detecta "envia esse relatório"
2. Monta email e chama `enviar_email_personalizado` com `confirmar_envio=false`
3. `enviar_email_personalizado` salva estado em `ultima_resposta_aguardando_email`
4. Usuário digita "sim" ou "enviar"
5. `chat_service.py` detecta confirmação no início de `processar_mensagem()`
6. Recupera email salvo e chama novamente com `confirmar_envio=true`
7. Email é enviado via SMTP

**Nenhuma mudança necessária** no fluxo de confirmação existente.

---

## 📁 Arquivos Criados/Modificados

### Criados:
1. **`services/report_service.py`** (NOVO)
   - DTO `RelatorioGerado`
   - Funções `salvar_ultimo_relatorio()`, `buscar_ultimo_relatorio()`, `criar_relatorio_gerado()`

### Modificados:
1. **`services/email_builder_service.py`**
   - Adicionada `montar_email_relatorio()` (genérico)
   - Adicionadas funções auxiliares: `_gerar_assunto_relatorio()`, `_construir_corpo_email_relatorio()`, `_gerar_introducao_relatorio()`, `_limpar_texto_relatorio()`, `_extrair_data_formatada()`, `_extrair_periodo()`

2. **`services/precheck_service.py`**
   - Substituída `_precheck_envio_email_relatorio_diario()` por `_precheck_envio_email_relatorio_generico()`
   - Integrada no fluxo principal (prioridade alta)

3. **`services/agents/processo_agent.py`**
   - `_obter_dashboard_hoje()`: salva relatório após gerar
   - `_listar_por_categoria()`: salva relatório após gerar
   - `_fechar_dia()`: salva relatório após gerar

4. **`services/tool_executor.py`**
   - Inclui `session_id` no context passado para agents

---

## 🔍 Lógica de Detecção e Prioridade

### Ordem de Prioridade no Precheck:

1. **Email de Relatório Genérico** (PRIORIDADE ALTA)
   - Detecta: "envia esse relatório", "manda esse resumo", "envia esse dashboard"
   - Busca: último relatório (qualquer tipo) via `buscar_ultimo_relatorio()`

2. **Email de Resumo/Briefing** (já existente)
   - Detecta: "envia resumo X por email"

3. **Email Livre** (já existente)
   - Detecta: "manda um email para X dizendo que Y"

4. **Email de Processo/NCM** (já existente)
   - Detecta: informações de processo ou NCM no histórico

### Heurística de Detecção:

**Padrões Regex:**
```python
r'\b(envia|envie|manda|mandar|enviar)\s+(esse|essa|este|esta)\s+(relatorio|relatório|resumo|dashboard|fechamento)'
r'\b(envia|envie|manda|mandar|enviar)\s+(relatorio|relatório|resumo|dashboard|fechamento)\s+(para|por|via|pra)'
```

**Extração de Email:**
```python
r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
```

---

## 🧪 Guia de Testes

### Teste 1: Salvamento do Último Relatório

**Objetivo:** Verificar se o relatório é salvo no contexto após ser gerado.

**Passos:**
1. Abrir uma sessão nova no chat
2. Pedir: "o que temos pra hoje?"
3. Verificar no banco SQLite:
   ```sql
   SELECT * FROM contexto_sessao 
   WHERE tipo_contexto = 'ultimo_relatorio' 
   ORDER BY atualizado_em DESC 
   LIMIT 1;
   ```
4. Verificar se `dados_json` contém:
   - `tipo_relatorio`: "o_que_tem_hoje"
   - `texto_chat`: texto completo do relatório
   - `categoria`: null ou categoria se filtrado
   - `filtros`: {"data_ref": "2025-12-19", ...}

**Resultado Esperado:**
- Registro encontrado no banco
- `dados_json` contém todos os campos do `RelatorioGerado`

**Teste Similar para:**
- "como estão os MV5?" → tipo: "como_estao_categoria", categoria: "MV5"
- "fechamento do dia" → tipo: "fechamento_dia"

### Teste 2: Detecção de "Envia Esse Relatório"

**Objetivo:** Verificar se o precheck detecta corretamente o comando.

**Passos:**
1. Gerar um relatório primeiro: "o que temos pra hoje?"
2. Depois pedir: "envia esse relatório para helenomaffra@gmail.com"
3. Verificar logs:
   ```
   [PRECHECK] 🎯 Comando de envio de relatório genérico por email detectado. Email: helenomaffra@gmail.com
   [PRECHECK] ✅ Relatório encontrado no contexto: o_que_tem_hoje (categoria: None)
   ```

**Resultado Esperado:**
- Precheck detecta o comando
- Busca e encontra o relatório no contexto
- Monta email e mostra preview

**Teste com Erro (sem relatório):**
1. Em sessão nova (sem gerar relatório), pedir: "envia esse relatório para helenomaffra@gmail.com"
2. Verificar resposta:
   ```
   ⚠️ Não encontrei nenhum relatório recente nesta conversa para enviar.
   💡 Para enviar um relatório por email, você precisa:
   1. Pedir primeiro um relatório (ex: "o que temos pra hoje?", "como estão os MV5?", "fechamento do dia")
   2. Depois que eu mostrar o relatório, pedir para eu enviar por email
   ```

### Teste 3: Preview de Email Correto

**Objetivo:** Verificar se o preview do email está formatado corretamente.

**Passos:**
1. Gerar relatório: "o que temos pra hoje?"
2. Pedir: "envia esse relatório para helenomaffra@gmail.com"
3. Verificar preview gerado:

**Resultado Esperado:**
```
📧 Preview do Email:
Para: helenomaffra@gmail.com
Assunto: Resumo diário – O que temos pra hoje - 19/12/2025

Conteúdo:
Olá, Heleno,

Segue o resumo diário de processos de importação para hoje (19/12/2025):

📅 O QUE TEMOS PRA HOJE - 19/12/2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚢 CHEGANDO HOJE (0 processo(s))
...
[RELATÓRIO COMPLETO AQUI]
...

Qualquer dúvida, estamos à disposição.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores

💡 Confirme para enviar (digite 'sim' ou 'enviar')
```

**Verificações:**
- ✅ Assunto específico e formatado
- ✅ Saudação personalizada
- ✅ Introdução apropriada
- ✅ Relatório completo incluído
- ✅ Encerramento e assinatura

**Teste para Outros Tipos:**
- "como estão os MV5?" → Assunto: "Status geral – MV5"
- "fechamento do dia" → Assunto: "Fechamento do dia - 19/12/2025"

### Teste 4: Confirmação e Envio Real

**Objetivo:** Verificar se a confirmação realmente dispara o envio.

**Passos:**
1. Gerar relatório: "o que temos pra hoje?"
2. Pedir: "envia esse relatório para helenomaffra@gmail.com"
3. Verificar preview (deve aparecer)
4. Digitar: "sim" ou "enviar"
5. Verificar logs:
   ```
   ✅ Email enviado com sucesso para helenomaffra@gmail.com
   ```
6. Verificar se email foi realmente enviado (caixa de entrada)

**Resultado Esperado:**
- Preview aparece
- Após "sim", email é enviado
- Resposta confirma envio
- Email chega na caixa de entrada

**Verificações no Código:**
- `ultima_resposta_aguardando_email` é salvo após preview
- `processar_mensagem()` detecta "sim" no início
- `enviar_email_personalizado` é chamado com `confirmar_envio=true`
- Email é enviado via SMTP

### Teste 5: Compatibilidade com NCM

**Objetivo:** Verificar se o fluxo de NCM continua funcionando.

**Passos:**
1. "qual a ncm de oculos?"
2. "tecwin 90041000"
3. "envie email com alíquotas para helenomaffra@gmail.com explicando a classificação"

**Resultado Esperado:**
- Fluxo de NCM funciona normalmente
- Email de NCM é gerado (não relatório genérico)
- Preview mostra informações de NCM/alíquotas

**Verificação:**
- Precheck de NCM tem prioridade sobre relatório genérico quando detecta NCM/alíquotas

### Teste 6: Múltiplos Relatórios na Mesma Sessão

**Objetivo:** Verificar se o último relatório é sempre o usado.

**Passos:**
1. "o que temos pra hoje?" → Relatório A
2. "como estão os MV5?" → Relatório B
3. "envia esse relatório para helenomaffra@gmail.com"

**Resultado Esperado:**
- Email contém Relatório B (último gerado)
- `buscar_ultimo_relatorio()` retorna o mais recente

---

## 🔧 Scripts de Sanity Check

Execute os seguintes comandos para validar que nada quebrou:

### 1. Teste de Imports
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from services.report_service import RelatorioGerado, salvar_ultimo_relatorio, buscar_ultimo_relatorio, criar_relatorio_gerado
from services.email_builder_service import EmailBuilderService
from services.precheck_service import PrecheckService
print('✅ Todos os imports OK')
"
```

### 2. Teste de Compilação
```bash
python3 -m py_compile services/report_service.py services/email_builder_service.py services/precheck_service.py services/agents/processo_agent.py
echo "✅ Compilação OK"
```

### 3. Teste de Serialização
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from services.report_service import criar_relatorio_gerado, RelatorioGerado

rel = criar_relatorio_gerado('o_que_tem_hoje', 'Teste', categoria='MV5')
json_str = rel.to_json()
rel2 = RelatorioGerado.from_json(json_str)

assert rel.tipo_relatorio == rel2.tipo_relatorio
assert rel.categoria == rel2.categoria
print('✅ Serialização/Deserialização OK')
"
```

### 4. Teste de Email Builder
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from services.email_builder_service import EmailBuilderService
from services.report_service import criar_relatorio_gerado

builder = EmailBuilderService()
rel = criar_relatorio_gerado('o_que_tem_hoje', '📅 O QUE TEMOS PRA HOJE - 19/12/2025\n\nTeste', categoria='MV5')

resultado = builder.montar_email_relatorio(rel, 'teste@exemplo.com')
assert resultado.get('sucesso') == True
assert 'assunto' in resultado
assert 'conteudo' in resultado
print('✅ Email builder genérico OK')
"
```

---

## 📊 Exemplos de Uso Real

### Exemplo 1: Dashboard "O Que Temos Pra Hoje"

**Entrada:**
```
Usuário: "o que temos pra hoje?"
mAIke: [mostra relatório completo]

Usuário: "envia esse relatório para helenomaffra@gmail.com"
```

**Preview Gerado:**
```
📧 Preview do Email:
Para: helenomaffra@gmail.com
Assunto: Resumo diário – O que temos pra hoje - 19/12/2025

Conteúdo:
Olá, Heleno,

Segue o resumo diário de processos de importação para hoje (19/12/2025):

📅 O QUE TEMOS PRA HOJE - 19/12/2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚢 CHEGANDO HOJE (0 processo(s))
...
[RELATÓRIO COMPLETO]
...

Qualquer dúvida, estamos à disposição.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores
```

### Exemplo 2: Relatório "Como Estão os MV5?"

**Entrada:**
```
Usuário: "como estão os MV5?"
mAIke: [mostra relatório completo]

Usuário: "envia esse relatório para cliente@empresa.com"
```

**Preview Gerado:**
```
📧 Preview do Email:
Para: cliente@empresa.com
Assunto: Status geral – MV5

Conteúdo:
Olá, Cliente,

Segue o status geral dos processos MV5:

📋 PROCESSOS MV5 - STATUS GERAL
...
[RELATÓRIO COMPLETO]
...

Qualquer dúvida, estamos à disposição.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores
```

### Exemplo 3: Fechamento do Dia

**Entrada:**
```
Usuário: "fechamento do dia"
mAIke: [mostra relatório completo]

Usuário: "manda esse relatório para gerencia@empresa.com"
```

**Preview Gerado:**
```
📧 Preview do Email:
Para: gerencia@empresa.com
Assunto: Fechamento do dia - 19/12/2025

Conteúdo:
Olá, Gerencia,

Segue o fechamento do dia (19/12/2025):

📊 FECHAMENTO DO DIA - 19/12/2025
...
[RELATÓRIO COMPLETO]
...

Qualquer dúvida, estamos à disposição.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores
```

---

## ✅ Checklist de Validação

- [x] `RelatorioGerado` DTO criado e serializável
- [x] `report_service.py` com funções de salvar/buscar
- [x] `montar_email_relatorio()` genérico implementado
- [x] Templates de assunto para cada tipo de relatório
- [x] Precheck genérico detectando "envia esse relatório"
- [x] Salvamento automático após gerar relatórios
- [x] Integração com fluxo de confirmação existente
- [x] Compatibilidade com fluxo de NCM mantida
- [x] Mensagens de erro amigáveis quando não há relatório
- [x] `session_id` passado para agents via `tool_executor`

---

## 🚀 Extensibilidade

### Adicionar Novo Tipo de Relatório

**Passo 1:** Gerar o relatório normalmente (ex: `_gerar_relatorio_x()`)

**Passo 2:** Após gerar resposta, salvar:
```python
from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
from datetime import datetime

relatorio = criar_relatorio_gerado(
    tipo_relatorio='novo_tipo',
    texto_chat=resposta,
    categoria=categoria,
    filtros={'data_ref': datetime.now().strftime('%Y-%m-%d')},
    meta_json={'total': len(dados)}
)
salvar_ultimo_relatorio(session_id, relatorio)
```

**Passo 3:** (Opcional) Adicionar template de assunto em `_gerar_assunto_relatorio()`:
```python
templates_assunto = {
    # ... existentes ...
    'novo_tipo': lambda r: f"Novo Relatório - {r.categoria or 'Geral'}",
}
```

**Pronto!** O fluxo de "envia esse relatório" funcionará automaticamente.

---

## 🔒 Garantias de Compatibilidade

1. **Fluxo de NCM:** Continua funcionando (precheck de NCM tem prioridade quando detecta NCM/alíquotas)
2. **Fluxo de Confirmação:** Reutiliza `ultima_resposta_aguardando_email` (sem mudanças)
3. **Relatórios Existentes:** Continuam funcionando (apenas adicionado salvamento)
4. **Testes de Sanity:** Todos os imports e compilações devem passar

---

**Data da Implementação:** 19/12/2025  
**Autor:** Assistente de Desenvolvimento (Dev Sênior)

