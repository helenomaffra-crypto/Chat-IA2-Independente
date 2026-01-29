# ✅ Botão de Sincronização Bancária na UI

**Data:** 07/01/2026  
**Status:** ✅ **IMPLEMENTADO**

---

## 🎯 O Que Foi Feito

### 1. Botão na UI (💰)

Adicionado botão de sincronização bancária na barra superior do chat, junto aos outros botões:

- ⚙️ Configurações
- 🔊 TTS (notificações por voz)
- 📚 Importar legislação
- **💰 Sincronizar extratos bancários** ← NOVO

### 2. Modal de Sincronização

Modal com opções para:

- **Seleção de Conta:**
  - Conta 1: Ag. 1251 - C/C 50483 (pré-configurada)
  - Conta 2: Ag. [configurar] - C/C [configurar] (precisa configurar)
  - Conta Personalizada (permite digitar agência e conta manualmente)

- **Período:**
  - Últimos N dias (padrão: 7 dias)
  - Range: 1 a 90 dias

### 3. Integração com Backend

Chama o endpoint `/api/banco/sincronizar` que:

- Consulta extrato da API do Banco do Brasil
- Gera hash único para cada lançamento
- Detecta duplicatas automaticamente
- Insere apenas lançamentos novos no SQL Server
- Detecta processos automaticamente pela descrição
- Retorna resumo (novos, duplicados, erros)

---

## 📋 Como Funciona

### Fluxo do Usuário

1. **Clicar no botão 💰** na barra superior
2. **Modal abre** com opções de conta e período
3. **Selecionar conta** (Conta 1, Conta 2 ou Personalizada)
4. **Ajustar período** se necessário (padrão: 7 dias)
5. **Clicar em "🔄 Sincronizar"**
6. **Sistema sincroniza** e mostra resultado:
   - ✅ Novos inseridos
   - ⏭️ Duplicados pulados
   - 🔗 Processos detectados automaticamente

### Resultado Mostrado

```
✅ Sincronização concluída!
📊 Total processado: 51 lançamentos
✅ Novos inseridos: 1
⏭️ Duplicados (pulados): 50

🔗 Processos detectados automaticamente:
• DMD.0083/25
• ALH.0168/25
```

---

## 🔧 Configurar Segunda Conta do BB

### Opção 1: Editar HTML (Recomendado)

Editar `templates/chat-ia-isolado.html`, linha ~658:

```html
<option value="1251|50483">Conta 1: Ag. 1251 - C/C 50483</option>
<option value="AGENCIA2|CONTA2">Conta 2: Ag. [configurar] - C/C [configurar]</option>
```

Substituir `AGENCIA2|CONTA2` pelos valores reais, exemplo:

```html
<option value="1251|50484">Conta 2: Ag. 1251 - C/C 50484</option>
```

### Opção 2: Usar Conta Personalizada

1. Selecionar "Conta Personalizada" no dropdown
2. Digitar agência e conta manualmente
3. Clicar em "🔄 Sincronizar"

---

## 📊 Suporte a Múltiplas Contas

### Banco do Brasil

✅ **Suporta múltiplas contas** - O serviço aceita `agencia` e `conta` como parâmetros

**Configuração:**
- Conta 1: Ag. 1251 - C/C 50483 (pré-configurada)
- Conta 2: Precisa configurar (ver acima)

### Outros Bancos

❌ **Por enquanto apenas Banco do Brasil** - O serviço está preparado para outros bancos, mas a API atual (`BancoBrasilService`) é específica para BB.

**Para adicionar outros bancos no futuro:**
1. Criar serviço similar (ex: `SantanderService`, `ItauService`)
2. Atualizar `BancoSincronizacaoService` para suportar múltiplos bancos
3. Adicionar opções no dropdown do modal

---

## 🎨 Arquivos Modificados

| Arquivo | Ação | Descrição |
|---------|------|-----------|
| `templates/chat-ia-isolado.html` | ✅ MODIFICADO | Botão 💰 + Modal de sincronização + JavaScript |

---

## 📝 Exemplo de Uso

### Via UI

1. Clicar no botão 💰
2. Selecionar "Conta 1: Ag. 1251 - C/C 50483"
3. Ajustar para "Últimos 7 dias" (ou outro valor)
4. Clicar em "🔄 Sincronizar"
5. Aguardar resultado (1-5 segundos dependendo do número de lançamentos)

### Via API (Alternativa)

```bash
curl -X POST http://localhost:5001/api/banco/sincronizar \
  -H "Content-Type: application/json" \
  -d '{
    "agencia": "1251",
    "conta": "50483",
    "dias_retroativos": 7
  }'
```

---

## ✅ Status Final

| Funcionalidade | Status |
|----------------|--------|
| Botão na UI | ✅ Implementado |
| Modal de sincronização | ✅ Implementado |
| Seleção de conta | ✅ Implementado (Conta 1 + Personalizada) |
| Conta 2 pré-configurada | ⏳ Aguardando dados (placeholder criado) |
| Integração com backend | ✅ Funcionando |
| Detecção de duplicatas | ✅ Automática |
| Detecção de processos | ✅ Automática |

---

## ⚠️ Próximo Passo

**Configurar Conta 2 do BB:**

Editar `templates/chat-ia-isolado.html` na linha ~658 e substituir:

```html
<option value="AGENCIA2|CONTA2">Conta 2: Ag. [configurar] - C/C [configurar]</option>
```

Por (exemplo):

```html
<option value="1251|50484">Conta 2: Ag. 1251 - C/C 50484</option>
```

---

**Última atualização:** 07/01/2026 às 16:30

