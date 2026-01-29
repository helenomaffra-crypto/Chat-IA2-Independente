# Abordagem Híbrida de Detecção de Intenções

**Data:** 14/01/2026  
**Status:** ✅ Implementado

## 🎯 Princípio Fundamental

**Regex/regras para comandos críticos e de confirmação**  
**Modelo escolhe para pedidos "fuzzy"**

---

## 📋 Categorias de Comandos

### 1. ✅ Regex/Regras (Precheck) - Comandos Críticos

**Quando usar:** Comandos que precisam ser detectados com 100% de precisão e rapidez, sem ambiguidade.

#### 1.1 Confirmações Simples
- **"sim"**, **"enviar"**, **"cancelar"**, **"ok"**, **"confirmar"**
- **Localização:** `ConfirmationHandler.processar_confirmacao_email()`
- **Razão:** Respostas curtas e determinísticas que não devem passar pela IA

#### 1.2 Comandos de Pagamento
- **"continue o pagamento"**, **"confirmar pagamento"**, **"efetivar boleto"**
- **Localização:** `PrecheckService.tentar_responder_sem_ia()` (linhas 52-107)
- **Razão:** Ações críticas que precisam ser executadas imediatamente com contexto salvo

#### 1.3 Comandos de Banco (Extratos)
- **"extrato do banco do brasil"**, **"extrato do santander"**
- **Localização:** `PrecheckService.tentar_responder_sem_ia()` (linhas 192-280)
- **Razão:** Comandos explícitos e determinísticos que não precisam de interpretação semântica

#### 1.4 Comandos de Interface
- **"maike menu"**, **"maike quero conciliar banco"**
- **Localização:** `MessageIntentService.detectar_comando_interface()`
- **Razão:** Comandos de UI que precisam de resposta instantânea

#### 1.5 Comandos de Email (Listagem)
- **"ver email"**, **"ler emails"**, **"detalhe email 3"**
- **Localização:** `PrecheckService.tentar_responder_sem_ia()` (linhas 109-159)
- **Razão:** Comandos explícitos de listagem que não precisam de interpretação

---

### 2. 🤖 Modelo (IA) - Pedidos "Fuzzy"

**Quando usar:** Pedidos que requerem interpretação semântica, contexto, ou podem ter variações de linguagem.

#### 2.1 Relatórios e Dashboards
- **"o que temos pra hoje?"**
- **"filtra DMD"**
- **"me mostra pendências"**
- **"envie esse relatorio"** (mesmo com erro de digitação: "ralatorio")
- **Localização:** IA detecta via tool calling → `obter_dashboard_hoje`, `buscar_secao_relatorio_salvo`, `enviar_relatorio_email`
- **Razão:** Requer interpretação semântica e contexto (entende sinônimos, erros de digitação, contexto anterior)

#### 2.2 Consultas de Processos
- **"como estão os DMD?"**
- **"status do processo BND.0084/25"**
- **"quais processos chegam semana que vem?"**
- **Localização:** IA detecta via tool calling → `listar_processos_por_categoria`, `consultar_processo`, `listar_processos_por_eta`
- **Razão:** Requer interpretação de categoria, período temporal, contexto

#### 2.3 Consultas de Documentos
- **"extrato do CE do processo X"**
- **"mostra a DI do processo Y"**
- **Localização:** IA detecta via tool calling → `consultar_ce`, `consultar_di`, `consultar_duimp`
- **Razão:** Requer extração de referência de processo e tipo de documento

#### 2.4 Emails Personalizados
- **"envie um email para X sobre Y"**
- **"mande um email amoroso"**
- **Localização:** IA detecta via tool calling → `enviar_email_personalizado`
- **Razão:** Requer interpretação de tom, conteúdo, destinatário

---

## 🔄 Fluxo de Decisão

```
Mensagem do Usuário
    ↓
Precheck (Regex/Regras)
    ├─ É comando crítico? → Executar diretamente (sem IA)
    └─ Não é comando crítico? → Passar para IA
        ↓
IA (Tool Calling)
    ├─ Detecta intenção semanticamente
    ├─ Escolhe tool apropriada
    └─ Executa ação
```

---

## ✅ Exemplos Práticos

### Exemplo 1: Confirmação Simples
```
Usuário: "sim"
Precheck: Detecta "sim" → ConfirmationHandler.processar_confirmacao_email()
Resultado: Executa email pendente diretamente (sem IA)
```

### Exemplo 2: Relatório com Erro de Digitação
```
Usuário: "envie esse ralatorio para helenomaffra@gmail.com"
Precheck: Não detecta (não é comando crítico)
IA: Entende semanticamente "ralatorio" = "relatorio" → chama enviar_relatorio_email
Resultado: Usa last_visible_report_id automaticamente
```

### Exemplo 3: Comando de Banco
```
Usuário: "extrato do banco do brasil"
Precheck: Detecta padrão → chama consultar_extrato_bb diretamente
Resultado: Executa sem IA (rápido e determinístico)
```

### Exemplo 4: Pedido Fuzzy
```
Usuário: "o que temos pra hoje?"
Precheck: Não detecta (não é comando crítico)
IA: Entende intenção → chama obter_dashboard_hoje
Resultado: Gera relatório completo
```

---

## 📊 Benefícios da Abordagem Híbrida

1. **Rapidez:** Comandos críticos executam instantaneamente (sem chamada à IA)
2. **Precisão:** Regex garante 100% de precisão em comandos determinísticos
3. **Flexibilidade:** IA entende variações, sinônimos, erros de digitação
4. **Eficiência:** Reduz chamadas desnecessárias à IA para comandos simples
5. **Custo:** Economiza tokens da API em comandos que não precisam de interpretação

---

## 🚨 Regras de Ouro

1. **NUNCA usar regex para pedidos "fuzzy"** (ex: "envie esse relatorio")
2. **SEMPRE usar regex para confirmações simples** (ex: "sim", "enviar", "cancelar")
3. **SEMPRE usar regex para comandos críticos** (ex: pagamentos, extratos bancários)
4. **SEMPRE deixar IA interpretar pedidos com contexto** (ex: "filtra DMD", "o que temos pra hoje?")
5. **SEMPRE usar last_visible_report_id quando IA chama enviar_relatorio_email** (não depender de regex)

---

## 📝 Checklist para Adicionar Novo Comando

- [ ] É um comando crítico que precisa de 100% de precisão? → **Regex no Precheck**
- [ ] É uma confirmação simples? → **Regex no ConfirmationHandler**
- [ ] Requer interpretação semântica ou contexto? → **Deixar IA detectar**
- [ ] Pode ter variações de linguagem ou erros de digitação? → **Deixar IA detectar**
- [ ] Precisa de resposta instantânea? → **Regex no Precheck**

---

## 🔗 Arquivos Relacionados

- `services/precheck_service.py` - Regex/regras para comandos críticos
- `services/handlers/confirmation_handler.py` - Detecção de confirmações
- `services/message_intent_service.py` - Comandos de interface
- `services/chat_service.py` - Integração com IA para pedidos fuzzy
- `services/tool_definitions.py` - Tools disponíveis para IA

---

**Última atualização:** 14/01/2026
