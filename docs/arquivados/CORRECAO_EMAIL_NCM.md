# Correção do Fluxo de Email com Classificação NCM e Alíquotas

## 📋 Resumo das Mudanças

Este documento descreve as correções implementadas para o fluxo de envio de email com classificação NCM e alíquotas, resolvendo o problema onde a mAIke gerava emails genéricos ("Mensagem" com "o porque da classificacao do oculos") em vez de emails técnicos completos.

---

## 🔍 Problema Identificado

**Cenário Real:**
1. Usuário: "qual a ncm de oculos?"
2. mAIke responde corretamente: NCM 9004.10.00, NESH completa, etc.
3. Usuário: "tecwin 90041000"
4. mAIke responde com alíquotas: II: 18%, IPI: 9,75%, PIS: 2,1%, COFINS: 9,65%, ICMS: TN
5. Usuário: "envie email com alíquotas para helenomaffra@gmail.com explicando o porque da classificacao do oculos"
6. **PROBLEMA:** mAIke gerava email genérico:
   - Assunto: "Mensagem"
   - Corpo: "Olá, o porque da classificacao do oculos"

**Causa Raiz:**
- Contexto de NCM/alíquotas não estava sendo salvo de forma estruturada
- Precheck não estava formatando corretamente o email quando detectava NCM/alíquotas
- IA não estava usando o contexto completo do histórico

---

## ✅ Solução Implementada

### 1. Novo Serviço: `email_builder_service.py`

**Arquivo:** `services/email_builder_service.py`

**Responsabilidades:**
- Montar emails técnicos completos de classificação NCM
- Extrair contexto de NCM/alíquotas do histórico
- Formatar email com todas as informações (NCM, NESH, alíquotas, justificativa)

**Principais Métodos:**
- `montar_email_classificacao_ncm()`: Monta email completo
- `extrair_contexto_ncm_do_historico()`: Extrai contexto do histórico/banco
- `_extrair_ncm_da_resposta()`: Extrai informações de uma resposta formatada

**Exemplo de Email Gerado:**
```
Para: helenomaffra@gmail.com
Assunto: Classificação NCM 9004.10.00 – Óculos de sol e alíquotas de importação

Corpo:
Olá, Heleno,

Segue abaixo a classificação fiscal e as alíquotas do produto:

• NCM: 9004.10.00 – Óculos de sol
• Confiança: 60%

Estrutura da Classificação:
• Capítulo 90 – Instrumentos e aparelhos de óptica...
• Posição 90.04 – Óculos para correção, proteção ou outros fins...
• Subposição 9004.10 – Óculos de sol

Nota Explicativa NESH:
[texto completo da NESH]

Alíquotas de Importação (segundo TECwin):
• II (Imposto de Importação): 18.00%
• IPI (Imposto sobre Produtos Industrializados): 9.75%
• PIS/PASEP-Importação: 2.10%
• COFINS-Importação: 9.65%
• ICMS: TN (verificar alíquota estadual aplicável)

Unidade de Medida: Unidade

Justificativa da Classificação:
[explicação detalhada baseada na NESH]

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores
```

### 2. Modificação: `context_service.py`

**Mudança:** Agora suporta salvar contexto de NCM/alíquotas

**Tipo de Contexto:** `ultima_classificacao_ncm`

**Estrutura Salva:**
```python
{
    'ncm': '90041000',
    'descricao': 'Óculos de sol',
    'confianca': 0.6,
    'nota_nesh': '...',
    'aliquotas': {
        'ii': 18.0,
        'ipi': 9.75,
        'pis': 2.1,
        'cofins': 9.65,
        'icms': 'TN'
    },
    'unidade_medida': 'Unidade',
    'fonte': 'TECwin',
    'explicacao': '...'
}
```

### 3. Modificação: `precheck_service.py`

**Mudanças:**
1. **Detecção de Email com NCM/Alíquotas:**
   - Detecta quando usuário pede email com informações de NCM/alíquotas
   - Usa `email_builder_service` para montar email completo

2. **Salvamento de Contexto após TECwin:**
   - Após consulta TECwin, salva contexto completo (NCM + alíquotas)
   - Mescla com contexto anterior (NESH, confiança) se disponível

3. **Tratamento de Erro:**
   - Se não encontrar contexto NCM, retorna mensagem amigável:
     "Não encontrei nenhuma classificação de NCM recente nesta conversa..."

**Fluxo:**
```
Usuário: "envie email com alíquotas para X explicando classificação"
  ↓
Precheck detecta NCM/alíquotas
  ↓
email_builder_service.extrair_contexto_ncm_do_historico()
  ↓
Se encontrou contexto:
  → email_builder_service.montar_email_classificacao_ncm()
  → enviar_email_personalizado() com email completo
Se não encontrou:
  → Retorna mensagem amigável pedindo para consultar NCM primeiro
```

### 4. Modificação: `chat_service.py`

**Mudança:** Salva contexto de NCM após `sugerir_ncm_com_ia`

**Quando Salva:**
- Após sucesso de `sugerir_ncm_com_ia`
- Salva: NCM, descrição, confiança, NESH, explicação

**Código Adicionado:**
```python
# Após resultado de sugerir_ncm_com_ia
if resultado.get('sucesso') and resultado.get('ncm_sugerido'):
    salvar_contexto_sessao(
        session_id=session_id_para_salvar,
        tipo_contexto='ultima_classificacao_ncm',
        chave='ncm',
        valor=resultado.get('ncm_sugerido', ''),
        dados_adicionais=contexto_ncm
    )
```

---

## 📁 Arquivos Modificados

1. **`services/email_builder_service.py`** (NOVO)
   - Serviço completo para montar emails de classificação NCM

2. **`services/precheck_service.py`**
   - Adicionada lógica para usar `email_builder_service` quando detecta email com NCM
   - Adicionado salvamento de contexto após consulta TECwin

3. **`services/chat_service.py`**
   - Adicionado salvamento de contexto após `sugerir_ncm_com_ia`

4. **`services/context_service.py`**
   - Já suportava salvar contexto (não precisou modificação)

---

## 🧪 Exemplo de Fluxo Completo

### Entrada do Usuário:
```
1. "qual a ncm de oculos?"
2. "tecwin 90041000"
3. "envie email com alíquotas para helenomaffra@gmail.com explicando o porque da classificacao do oculos"
```

### Resposta Esperada (Preview do Email):

**Para:** helenomaffra@gmail.com  
**Assunto:** Classificação NCM 9004.10.00 – Óculos de sol e alíquotas de importação

**Corpo:**
```
Olá, Heleno,

Segue abaixo a classificação fiscal e as alíquotas do produto:

• NCM: 9004.10.00 – Óculos de sol
• Confiança: 60%

Estrutura da Classificação:
• Capítulo 90 – Instrumentos e aparelhos de óptica, fotografia, cinematografia, medida, controle ou precisão; instrumentos e aparelhos médico-cirúrgicos; suas partes e acessórios
• Posição 90.04 – Óculos para correção, proteção ou outros fins, e artigos semelhantes
• Subposição 9004.10 – Óculos de sol

Nota Explicativa NESH (Posição 90.04):
Óculos para correção, proteção ou outros fins, e artigos semelhantes.
9004.10 - Óculos de sol
A presente posição agrupa um conjunto de artigos que consistem habitualmente numa armação provida de vidro ou de outras matérias...

Alíquotas de Importação (segundo TECwin):
• II (Imposto de Importação): 18.00%
• IPI (Imposto sobre Produtos Industrializados): 9.75%
• PIS/PASEP-Importação: 2.10%
• COFINS-Importação: 9.65%
• ICMS: TN (verificar alíquota estadual aplicável)

Unidade de Medida: Unidade

Justificativa da Classificação:
O produto foi classificado na NCM 9004.10.00 por se tratar de óculos de sol, enquadrando-se na subposição 9004.10 (posição 90.04), conforme texto da NCM e estrutura do Capítulo 90. Caso o produto seja de outro tipo específico ou tenha características diferentes, a NCM pode variar e seria necessário reavaliar a descrição técnica e o uso.

Atenciosamente,
mAIke – Assistente de COMEX
Make Consultores
```

---

## 🔧 Detalhes Técnicos

### Extração de Contexto

O `email_builder_service` busca contexto em 3 níveis (em ordem de prioridade):

1. **Contexto Persistente** (`contexto_sessao`):
   - Busca por `tipo_contexto='ultima_classificacao_ncm'`
   - Mais confiável (salvo após cada consulta)

2. **Histórico da Conversa**:
   - Procura nas últimas 10 respostas
   - Extrai NCM, alíquotas, NESH usando regex

3. **Banco de Dados** (`conversas_chat`):
   - Busca últimas 5 respostas da sessão que contenham "NCM", "TECwin" ou "Alíquotas"
   - Fallback final

### Formatação do Email

O email é formatado com:
- **Assunto específico:** "Classificação NCM {ncm} – {descrição} e alíquotas de importação"
- **Estrutura completa:** NCM, Capítulo, Posição, Subposição, Item
- **NESH completa:** Nota explicativa (truncada se > 500 palavras)
- **Alíquotas em formato tabular:** Todas as alíquotas do TECwin
- **Justificativa:** Explicação detalhada ou gerada automaticamente
- **Assinatura profissional:** mAIke – Assistente de COMEX

### Tratamento de Erros

**Cenário 1: Sem Contexto NCM**
```
Resposta: "⚠️ Não encontrei nenhuma classificação de NCM recente nesta conversa.
Para enviar um email com classificação fiscal e alíquotas, você precisa:
1. Perguntar sobre a NCM de um produto (ex: 'qual a ncm de oculos?')
2. Consultar as alíquotas no TECwin (ex: 'tecwin 90041000')
3. Depois pedir para enviar o email"
```

**Cenário 2: Contexto Incompleto**
- Se tem NCM mas não tem alíquotas: Email é gerado sem alíquotas (com aviso)
- Se tem alíquotas mas não tem NESH: Email é gerado sem NESH (com justificativa básica)

---

## ✅ Checklist de Validação

- [x] Serviço `email_builder_service.py` criado
- [x] Contexto de NCM salvo após `sugerir_ncm_com_ia`
- [x] Contexto de NCM/alíquotas salvo após consulta TECwin
- [x] Precheck detecta email com NCM/alíquotas
- [x] Precheck usa `email_builder_service` para montar email
- [x] Email gerado com todas as informações (NCM, NESH, alíquotas, justificativa)
- [x] Tratamento de erro quando não há contexto
- [x] Assunto específico e profissional
- [x] Formatação profissional do corpo do email

---

## 🚀 Próximos Passos (Opcional)

1. **Melhorar Extração de NESH:**
   - Extrair NESH completa do histórico (atualmente pode estar truncada)

2. **Suporte a Múltiplos NCMs:**
   - Permitir email com múltiplas classificações

3. **Template HTML:**
   - Gerar email em HTML formatado (atualmente é texto)

4. **Cache de Emails:**
   - Salvar emails gerados para referência futura

---

## 📝 Notas Importantes

- O sistema **NÃO inventa** NCM ou alíquotas se não tiver contexto
- O sistema **NÃO envia** email sem confirmação do usuário (sempre mostra preview primeiro)
- O contexto é **salvo por sessão** (não persiste entre sessões diferentes)
- O contexto é **atualizado** a cada nova consulta de NCM/TECwin

---

**Data da Implementação:** 19/12/2025  
**Autor:** Assistente de Desenvolvimento (baseado em análise do GPT-5)



