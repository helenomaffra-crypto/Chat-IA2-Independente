# 🧪 Guia de Teste - Sugestões de Vinculação Bancária Automática

## 📋 Visão Geral

Este documento descreve como testar a nova funcionalidade de **sugestões automáticas de vinculação bancária** que detecta quando uma DI/DUIMP é desembaraçada e sugere automaticamente a vinculação com lançamentos bancários compatíveis.

---

## 🐳 Instruções Docker

### 1. Reiniciar o Container

Como o código está montado via volume, geralmente basta reiniciar o container:

```bash
# Parar o container
docker-compose stop web

# Iniciar novamente
docker-compose start web

# OU reiniciar diretamente
docker-compose restart web
```

### 2. Verificar Logs

Após reiniciar, verifique se não há erros:

```bash
# Ver logs em tempo real
docker-compose logs -f web

# Ver últimas 50 linhas
docker-compose logs --tail=50 web
```

### 3. Se Precisar Reconstruir (apenas se houver mudanças em requirements.txt ou Dockerfile)

```bash
# Reconstruir imagem
docker-compose build web

# Reiniciar
docker-compose up -d web
```

### 4. Verificar se o Banco de Dados foi Criado Corretamente

```bash
# Entrar no container
docker-compose exec web bash

# Dentro do container, verificar se a tabela existe
sqlite3 chat_ia.db "SELECT name FROM sqlite_master WHERE type='table' AND name='sugestoes_vinculacao_bancaria';"

# Sair do container
exit
```

---

## 🧪 Como Testar

### Teste 1: Verificar se a Tabela Foi Criada

**Objetivo:** Confirmar que a estrutura do banco está correta.

**Passos:**
1. Acesse o chat: `http://localhost:5001`
2. Abra o console do navegador (F12)
3. Execute no console:
   ```javascript
   fetch('/api/banco/sugestoes-vinculacao?limite=10')
     .then(r => r.json())
     .then(d => console.log('Sugestões:', d))
   ```

**Resultado Esperado:**
```json
{
  "sucesso": true,
  "total": 0,
  "sugestoes": []
}
```

**Se der erro:** Verifique os logs do Docker e confirme que a tabela foi criada.

---

### Teste 2: Criar Sugestão Manualmente (Teste Rápido)

**Objetivo:** Testar a interface sem esperar uma DI desembaraçar.

**Passos:**
1. Acesse o chat: `http://localhost:5001`
2. Abra o console do navegador (F12)
3. Execute no console para criar uma sugestão de teste:
   ```javascript
   // Primeiro, precisamos de um lançamento bancário real
   // Vamos buscar um lançamento não classificado
   fetch('/api/banco/lancamentos-nao-classificados?limite=1')
     .then(r => r.json())
     .then(d => {
       if (d.lancamentos && d.lancamentos.length > 0) {
         const lanc = d.lancamentos[0];
         console.log('Lançamento encontrado:', lanc);
         
         // Agora criar sugestão manualmente via SQL (via Python)
         // Isso precisa ser feito no backend
         fetch('/api/teste/criar-sugestao-manual', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             processo_referencia: 'TEST.0001/26',
             tipo_documento: 'DI',
             numero_documento: '123456789',
             data_desembaraco: '2026-01-23',
             total_impostos: lanc.valor,
             id_movimentacao: lanc.id_movimentacao,
             score_confianca: 95
           })
         })
         .then(r => r.json())
         .then(d => console.log('Sugestão criada:', d));
       }
     });
   ```

**⚠️ Nota:** O endpoint `/api/teste/criar-sugestao-manual` precisa ser criado. Por enquanto, use o método direto abaixo.

**Método Alternativo (via Python no container):**
```bash
# Entrar no container
docker-compose exec web bash

# Executar Python interativo
python3

# No Python:
from db_manager import get_db_connection
from datetime import datetime

conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO sugestoes_vinculacao_bancaria (
        processo_referencia,
        tipo_documento,
        numero_documento,
        data_desembaraco,
        total_impostos,
        id_movimentacao_sugerida,
        score_confianca,
        status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente')
""", (
    'TEST.0001/26',
    'DI',
    '123456789',
    '2026-01-23',
    13337.88,  # Valor de exemplo
    777,  # ID de lançamento (ajustar conforme necessário)
    95
))

conn.commit()
conn.close()
print("✅ Sugestão criada!")

# Sair do Python
exit()

# Sair do container
exit
```

---

### Teste 3: Verificar Interface de Sugestões

**Objetivo:** Confirmar que a aba "💡 Sugestões" aparece e funciona.

**Passos:**
1. Acesse o chat: `http://localhost:5001`
2. Abra o modal de conciliação bancária:
   - Digite no chat: "maike quero conciliar banco"
   - OU clique no menu (☰) → "Conciliação Bancária"
3. Verifique se aparece a aba "💡 Sugestões" ao lado de "⚪ Não Classificados" e "✅ Classificados"
4. Clique na aba "💡 Sugestões"
5. Se houver sugestões criadas (Teste 2), você deve ver:
   - Lista de sugestões com processo, valor, lançamento e score
   - Botões "✅ Vincular" e "Ignorar" em cada sugestão
   - Badge com número de sugestões pendentes no topo da aba

**Resultado Esperado:**
- Aba "💡 Sugestões" visível
- Se houver sugestões, elas aparecem formatadas
- Badge mostra o número correto

---

### Teste 4: Aplicar uma Sugestão

**Objetivo:** Testar o fluxo completo de vinculação.

**Pré-requisito:** Ter uma sugestão criada (Teste 2).

**Passos:**
1. Na aba "💡 Sugestões", clique em "✅ Vincular" em uma sugestão
2. Verifique se:
   - A sugestão desaparece da lista
   - O lançamento aparece na aba "✅ Classificados"
   - O lançamento desaparece da aba "⚪ Não Classificados" (se estava lá)

**Resultado Esperado:**
- Sugestão aplicada com sucesso
- Lançamento vinculado ao processo
- Status da sugestão mudado para "aplicada" no banco

**Verificação no Banco:**
```bash
docker-compose exec web bash
sqlite3 chat_ia.db "SELECT id, processo_referencia, status, aplicado_em FROM sugestoes_vinculacao_bancaria WHERE id = 1;"
exit
```

---

### Teste 5: Teste Automático (Quando DI Desembaraça)

**Objetivo:** Verificar se a detecção automática funciona quando uma DI desembaraça.

**Como Funciona:**
- O sistema monitora mudanças de status de DI/DUIMP
- Quando detecta que uma DI/DUIMP desembaraçou, automaticamente:
  1. Extrai valores de impostos (II, IPI, PIS, COFINS, TAXA_UTILIZACAO)
  2. Busca lançamentos bancários compatíveis
  3. Cria sugestão no banco

**Passos para Testar:**
1. **Opção A - Simular DI desembaraçada:**
   - Use um processo que já tem DI registrada mas não desembaraçada
   - Simule a mudança de status (via API ou manualmente no banco)
   - Verifique se a sugestão foi criada

2. **Opção B - Aguardar DI real desembaraçar:**
   - Monitore um processo com DI registrada
   - Quando a DI desembaraçar naturalmente, verifique se a sugestão aparece

**Verificação:**
```bash
# Verificar logs do sistema quando DI desembaraça
docker-compose logs -f web | grep -i "sugestão\|vinculação\|desembaraç"

# Verificar sugestões criadas
docker-compose exec web bash
sqlite3 chat_ia.db "SELECT * FROM sugestoes_vinculacao_bancaria ORDER BY criado_em DESC LIMIT 5;"
exit
```

---

### Teste 6: Ignorar Sugestão

**Objetivo:** Testar o fluxo de ignorar sugestão.

**Passos:**
1. Crie uma sugestão de teste (Teste 2)
2. Na aba "💡 Sugestões", clique em "Ignorar"
3. Confirme a ação
4. Verifique se a sugestão desaparece da lista

**Resultado Esperado:**
- Sugestão marcada como "ignorada" no banco
- Sugestão não aparece mais na lista de pendentes

**Verificação:**
```bash
docker-compose exec web bash
sqlite3 chat_ia.db "SELECT id, status FROM sugestoes_vinculacao_bancaria WHERE id = [ID_DA_SUGESTAO];"
exit
```

---

### Teste 7: Desvincular Lançamento (Correção)

**Objetivo:** Testar a funcionalidade de desvincular lançamento.

**Passos:**
1. Aplique uma sugestão (Teste 4) para ter um lançamento classificado
2. Na aba "✅ Classificados", encontre o lançamento vinculado
3. **⚠️ Nota:** A interface de desvincular ainda precisa ser implementada no frontend
4. Por enquanto, teste via API:
   ```javascript
   // No console do navegador
   fetch('/api/banco/desvincular-lancamento', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       id_movimentacao: 777  // ID do lançamento
     })
   })
   .then(r => r.json())
   .then(d => console.log('Resultado:', d));
   ```

**Resultado Esperado:**
- Lançamento desvinculado do processo
- Classificações removidas
- Lançamento volta para "Não Classificados"

---

## 🔍 Verificações de Debug

### Verificar se o Serviço está Funcionando

```bash
# Entrar no container
docker-compose exec web bash

# Testar importação do serviço
python3 -c "from services.banco_auto_vinculacao_service import BancoAutoVinculacaoService; print('✅ Serviço OK')"

# Testar listagem de sugestões
python3 -c "
from services.banco_auto_vinculacao_service import BancoAutoVinculacaoService
svc = BancoAutoVinculacaoService()
result = svc.listar_sugestoes_pendentes(limite=10)
print('Resultado:', result)
"

# Sair
exit
```

### Verificar Logs de Notificação

```bash
# Ver logs relacionados a notificações e sugestões
docker-compose logs web | grep -i "sugestão\|vinculação\|desembaraç\|notificação"
```

### Verificar Estrutura do Banco

```bash
docker-compose exec web bash
sqlite3 chat_ia.db ".schema sugestoes_vinculacao_bancaria"
exit
```

---

## ⚠️ Problemas Comuns e Soluções

### Problema 1: Tabela não existe

**Sintoma:** Erro ao listar sugestões: "no such table: sugestoes_vinculacao_bancaria"

**Solução:**
```bash
# Reiniciar o container para forçar criação da tabela
docker-compose restart web

# Verificar se foi criada
docker-compose exec web bash
sqlite3 chat_ia.db "SELECT name FROM sqlite_master WHERE type='table' AND name='sugestoes_vinculacao_bancaria';"
exit
```

### Problema 2: Sugestões não aparecem na interface

**Sintoma:** Aba "💡 Sugestões" vazia mesmo com sugestões no banco

**Solução:**
1. Verifique o console do navegador (F12) para erros JavaScript
2. Verifique se o endpoint está funcionando:
   ```javascript
   fetch('/api/banco/sugestoes-vinculacao')
     .then(r => r.json())
     .then(d => console.log(d))
   ```
3. Verifique se há sugestões no banco:
   ```bash
   docker-compose exec web bash
   sqlite3 chat_ia.db "SELECT COUNT(*) FROM sugestoes_vinculacao_bancaria WHERE status = 'pendente';"
   exit
   ```

### Problema 3: Erro ao aplicar sugestão

**Sintoma:** Erro "Tipo de despesa não encontrado" ou similar

**Solução:**
1. Verifique se o tipo de despesa "Impostos de Importação" existe:
   ```bash
   docker-compose exec web bash
   python3 -c "
   from services.banco_concilacao_service import get_banco_concilacao_service
   svc = get_banco_concilacao_service()
   tipos = svc.listar_tipos_despesa()
   print('Tipos:', tipos)
   "
   exit
   ```
2. Se não existir, execute o script de criação do catálogo:
   ```bash
   docker-compose exec web bash
   python3 scripts/criar_catalogo_despesas_via_python.py
   exit
   ```

### Problema 4: Sugestões não são criadas automaticamente

**Sintoma:** DI desembaraça mas não cria sugestão

**Solução:**
1. Verifique os logs quando a DI desembaraça:
   ```bash
   docker-compose logs -f web | grep -i "sugestão\|erro\|exception"
   ```
2. Verifique se o processo tem valores de impostos:
   - Acesse o processo no chat
   - Verifique se mostra "Impostos Pagos" com valores
3. Verifique se há lançamentos bancários compatíveis:
   - Sincronize extratos recentes
   - Verifique se há lançamentos com descrição "SISCOMEX" ou similar

---

## 📊 Checklist de Testes

- [ ] Tabela `sugestoes_vinculacao_bancaria` criada
- [ ] Endpoint `/api/banco/sugestoes-vinculacao` funciona
- [ ] Aba "💡 Sugestões" aparece na interface
- [ ] Badge mostra número correto de sugestões
- [ ] Sugestões são exibidas corretamente
- [ ] Botão "✅ Vincular" funciona
- [ ] Botão "Ignorar" funciona
- [ ] Botão "Aplicar todas" funciona (se houver múltiplas)
- [ ] Lançamento vinculado aparece em "Classificados"
- [ ] Lançamento vinculado desaparece de "Não Classificados"
- [ ] Sugestões persistem após refresh da página
- [ ] Detecção automática funciona quando DI desembaraça (teste real)

---

## 🎯 Próximos Passos Após Testes

1. **Se tudo funcionar:**
   - Monitorar sugestões em produção
   - Coletar feedback dos usuários
   - Ajustar score de confiança se necessário

2. **Se houver problemas:**
   - Verificar logs detalhados
   - Testar endpoints individualmente
   - Verificar estrutura do banco
   - Revisar código conforme necessário

---

**Última atualização:** 23/01/2026
