# 💬 Sistema de Notificações Humanizadas e Proativas - mAIke

**Data:** 07/01/2026  
**Objetivo:** Transformar notificações técnicas em conversas humanas e proativas

---

## 🎯 Visão Geral

O mAIke deve ser **proativo** e **humano**, avisando sobre coisas importantes de forma natural, como um colega de trabalho que te dá um toque importante.

### ❌ Problema Atual

**Notificações Frias:**
```
🔔 Notificação: Status da DI alterado
Processo: ALH.0010/25
Status anterior: DI_EM_ANALISE
Status novo: DI_DESEMBARACADA
```

**Problemas:**
- Muito técnica
- Não contextualiza a importância
- Não sugere ação
- Usuário ignora (parece spam)

### ✅ Solução Proposta

**Notificações Humanas:**
```
👋 Oi! Só um toque: a DI do ALH.0010/25 foi desembaraçada agora há pouco. 
Tá tudo certo pra seguir com a entrega! 🚚
```

**Ou para algo mais urgente:**
```
⚠️ Atenção! Tem um navio chegando amanhã com 3 processos:
• ALH.0010/25
• VDM.0025/25  
• DMD.0018/25

Quer que eu prepare um resumo do que precisa ser feito?
```

---

## 🏗️ Arquitetura do Sistema

### 1. Tipos de Notificações Humanizadas

#### 1.1. **Insights Proativos** (Prioridade Alta)
**Quando:** Acontecimentos importantes que precisam de atenção

**Exemplos:**
- Navio chegando amanhã/hoje
- Processo com atraso crítico (>7 dias)
- Pendência que bloqueia desembaraço
- Mudança importante de status

**Formato:**
```
👋 [Saudação contextual] + [O que aconteceu] + [Por que importa] + [Sugestão de ação]
```

#### 1.2. **Lembretes Amigáveis** (Prioridade Média)
**Quando:** Coisas que precisam ser feitas, mas não são urgentes

**Exemplos:**
- Processo pronto para registro há 2 dias
- Pendência que pode ser resolvida
- ETA alterado (adiantado/atrasado)

**Formato:**
```
💡 [Lembrete amigável] + [Contexto] + [Sugestão opcional]
```

#### 1.3. **Atualizações Informativas** (Prioridade Baixa)
**Quando:** Mudanças que são boas notícias ou informativas

**Exemplos:**
- Status mudou para algo positivo
- Pagamento confirmado
- Documento registrado

**Formato:**
```
✅ [Boas notícias] + [Contexto breve]
```

---

## 📝 Sistema de Formatação de Mensagens

### 2.1. Template de Mensagens Humanizadas

```python
class MensagemHumanizada:
    """Gera mensagens humanas e contextuais"""
    
    def gerar_mensagem_navio_chegando(self, processos: List[Dict]) -> str:
        """
        Gera mensagem quando navio está chegando.
        
        Exemplo:
        "👋 Oi! Só um toque: tem um navio chegando amanhã com 3 processos:
        • ALH.0010/25
        • VDM.0025/25
        • DMD.0018/25
        
        Quer que eu prepare um resumo do que precisa ser feito?"
        """
        if len(processos) == 1:
            proc = processos[0]
            return f"""👋 Oi! Só um toque: o navio do {proc['processo_referencia']} está chegando amanhã.
            
Já tá tudo certo pra receber? Quer que eu verifique se tem alguma pendência?"""
        
        processos_lista = "\n".join([f"• {p['processo_referencia']}" for p in processos])
        return f"""👋 Oi! Só um toque: tem um navio chegando amanhã com {len(processos)} processos:

{processos_lista}

Quer que eu prepare um resumo do que precisa ser feito?"""
    
    def gerar_mensagem_atraso_critico(self, processo: Dict, dias_atraso: int) -> str:
        """
        Gera mensagem para processo com atraso crítico.
        
        Exemplo:
        "⚠️ Atenção! O ALH.0010/25 está com {dias_atraso} dias de atraso para registro.
        Ainda não tem DI/DUIMP registrada. Quer que eu verifique o que está faltando?"
        """
        return f"""⚠️ Atenção! O {processo['processo_referencia']} está com {dias_atraso} dias de atraso para registro.

Ainda não tem DI/DUIMP registrada. Quer que eu verifique o que está faltando?"""
    
    def gerar_mensagem_status_mudou(self, processo: Dict, status_anterior: str, status_novo: str, tipo_doc: str) -> str:
        """
        Gera mensagem quando status muda.
        
        Exemplo:
        "✅ Boa notícia! A DI do ALH.0010/25 foi desembaraçada agora há pouco.
        Tá tudo certo pra seguir com a entrega! 🚚"
        """
        # Mapear status para mensagens humanas
        status_mensagens = {
            'DI_DESEMBARACADA': "foi desembaraçada agora há pouco. Tá tudo certo pra seguir com a entrega! 🚚",
            'DUIMP_DESEMBARACADA': "foi desembaraçada agora há pouco. Tá tudo certo pra seguir com a entrega! 🚚",
            'DI_EM_ANALISE': "entrou em análise. Vou acompanhar e te aviso quando sair! 👀",
            'DUIMP_EM_ANALISE': "entrou em análise. Vou acompanhar e te aviso quando sair! 👀",
            'CE_MANIFESTADO': "foi manifestado. Agora é só aguardar o desembaraço! ⏳",
            'CE_DESCARREGADO': "foi descarregado. Já pode seguir com o desembaraço! 🚢",
        }
        
        mensagem_status = status_mensagens.get(status_novo, f"mudou de '{status_anterior}' para '{status_novo}'")
        
        return f"""✅ Boa notícia! A {tipo_doc} do {processo['processo_referencia']} {mensagem_status}"""
    
    def gerar_mensagem_pendencia_bloqueio(self, processo: Dict, tipo_pendencia: str) -> str:
        """
        Gera mensagem para pendência que bloqueia.
        
        Exemplo:
        "⚠️ Atenção! O ALH.0010/25 tem uma pendência de {tipo_pendencia} que está bloqueando o desembaraço.
        Quer que eu mostre os detalhes?"
        """
        return f"""⚠️ Atenção! O {processo['processo_referencia']} tem uma pendência de {tipo_pendencia} que está bloqueando o desembaraço.

Quer que eu mostre os detalhes?"""
```

---

## 🧠 Sistema de Priorização Inteligente

### 3.1. Níveis de Prioridade

```python
class PrioridadeNotificacao:
    CRITICA = "critica"      # Precisa de ação imediata
    ALTA = "alta"            # Importante, mas não urgente
    MEDIA = "media"          # Informativo, mas relevante
    BAIXA = "baixa"          # Apenas informativo
```

### 3.2. Regras de Priorização

```python
def calcular_prioridade(tipo_evento: str, contexto: Dict) -> str:
    """
    Calcula prioridade baseado no tipo de evento e contexto.
    """
    # CRÍTICA: Navio chegando hoje/amanhã
    if tipo_evento == "navio_chegando":
        dias_ate_chegada = contexto.get('dias_ate_chegada', 999)
        if dias_ate_chegada <= 1:
            return PrioridadeNotificacao.CRITICA
    
    # CRÍTICA: Atraso crítico (>7 dias)
    if tipo_evento == "atraso_registro":
        dias_atraso = contexto.get('dias_atraso', 0)
        if dias_atraso > 7:
            return PrioridadeNotificacao.CRITICA
    
    # ALTA: Pendência que bloqueia
    if tipo_evento == "pendencia_bloqueio":
        return PrioridadeNotificacao.ALTA
    
    # ALTA: Status mudou para algo importante
    if tipo_evento == "status_mudou":
        status_novo = contexto.get('status_novo', '')
        if status_novo in ['DI_DESEMBARACADA', 'DUIMP_DESEMBARACADA']:
            return PrioridadeNotificacao.ALTA
    
    # MÉDIA: ETA alterado
    if tipo_evento == "eta_alterado":
        return PrioridadeNotificacao.MEDIA
    
    # BAIXA: Outras mudanças
    return PrioridadeNotificacao.BAIXA
```

---

## ⏰ Sistema de Timing Inteligente

### 4.1. Agrupamento de Notificações

**Problema:** Muitas notificações separadas = spam

**Solução:** Agrupar notificações relacionadas

```python
def agrupar_notificacoes(notificacoes: List[Dict]) -> List[Dict]:
    """
    Agrupa notificações relacionadas em uma única mensagem.
    """
    # Agrupar por tipo e tempo (últimas 5 minutos)
    grupos = {}
    
    for notif in notificacoes:
        chave = f"{notif['tipo']}_{notif['processo_referencia']}"
        if chave not in grupos:
            grupos[chave] = []
        grupos[chave].append(notif)
    
    # Gerar mensagens agrupadas
    mensagens_agrupadas = []
    for chave, grupo in grupos.items():
        if len(grupo) == 1:
            mensagens_agrupadas.append(grupo[0])
        else:
            # Agrupar em uma mensagem única
            mensagem_agrupada = gerar_mensagem_agrupada(grupo)
            mensagens_agrupadas.append(mensagem_agrupada)
    
    return mensagens_agrupadas
```

### 4.2. Horários Inteligentes

```python
def deve_enviar_notificacao(prioridade: str, hora_atual: int) -> bool:
    """
    Decide se deve enviar notificação baseado na hora.
    """
    # CRÍTICA: Sempre envia
    if prioridade == PrioridadeNotificacao.CRITICA:
        return True
    
    # ALTA: Envia entre 8h e 20h
    if prioridade == PrioridadeNotificacao.ALTA:
        return 8 <= hora_atual <= 20
    
    # MÉDIA: Envia entre 9h e 18h
    if prioridade == PrioridadeNotificacao.MEDIA:
        return 9 <= hora_atual <= 18
    
    # BAIXA: Envia entre 10h e 17h
    return 10 <= hora_atual <= 17
```

---

## 🎨 Personalização e Contexto

### 5.1. Saudação Contextual

```python
def gerar_saudacao(hora_atual: int, ultima_interacao: Optional[datetime]) -> str:
    """
    Gera saudação baseada na hora e última interação.
    """
    # Primeira interação do dia
    if ultima_interacao and (datetime.now() - ultima_interacao).days >= 1:
        return "👋 Oi! Bom dia! Só um toque:"
    
    # Manhã
    if 6 <= hora_atual < 12:
        return "👋 Bom dia! Só um toque:"
    
    # Tarde
    if 12 <= hora_atual < 18:
        return "👋 Boa tarde! Só um toque:"
    
    # Noite
    return "👋 Boa noite! Só um toque:"
```

### 5.2. Sugestões de Ação Contextuais

```python
def gerar_sugestao_acao(tipo_evento: str, contexto: Dict) -> Optional[str]:
    """
    Gera sugestão de ação baseada no tipo de evento.
    """
    sugestoes = {
        "navio_chegando": "Quer que eu prepare um resumo do que precisa ser feito?",
        "atraso_critico": "Quer que eu verifique o que está faltando?",
        "pendencia_bloqueio": "Quer que eu mostre os detalhes?",
        "status_mudou": "Quer que eu mostre mais informações?",
        "eta_alterado": "Quer que eu atualize o planejamento?",
    }
    
    return sugestoes.get(tipo_evento)
```

---

## 🔔 Sistema de Notificações Proativas

### 6.1. Verificações Periódicas

```python
class NotificacoesProativasService:
    """Serviço para notificações proativas e humanizadas"""
    
    def verificar_navios_chegando(self) -> List[Dict]:
        """
        Verifica navios chegando hoje/amanhã e gera notificações.
        """
        processos_chegando = self._buscar_processos_chegando_hoje_amanha()
        
        if not processos_chegando:
            return []
        
        # Agrupar por navio
        navios = {}
        for proc in processos_chegando:
            navio = proc.get('nome_navio', 'Desconhecido')
            if navio not in navios:
                navios[navio] = []
            navios[navio].append(proc)
        
        notificacoes = []
        for navio, processos in navios.items():
            mensagem = self._gerar_mensagem_navio_chegando(navio, processos)
            notificacoes.append({
                'tipo': 'navio_chegando',
                'prioridade': PrioridadeNotificacao.CRITICA,
                'mensagem': mensagem,
                'processos': processos,
                'acao_sugerida': 'preparar_resumo'
            })
        
        return notificacoes
    
    def verificar_atrasos_criticos(self) -> List[Dict]:
        """
        Verifica processos com atraso crítico.
        """
        processos_atrasados = self._buscar_processos_atrasados_criticos()
        
        notificacoes = []
        for proc in processos_atrasados:
            dias_atraso = self._calcular_dias_atraso(proc)
            mensagem = self._gerar_mensagem_atraso_critico(proc, dias_atraso)
            notificacoes.append({
                'tipo': 'atraso_critico',
                'prioridade': PrioridadeNotificacao.CRITICA,
                'mensagem': mensagem,
                'processo': proc,
                'acao_sugerida': 'verificar_pendencias'
            })
        
        return notificacoes
    
    def verificar_pendencias_bloqueio(self) -> List[Dict]:
        """
        Verifica pendências que estão bloqueando desembaraço.
        """
        pendencias = self._buscar_pendencias_bloqueio()
        
        notificacoes = []
        for pendencia in pendencias:
            mensagem = self._gerar_mensagem_pendencia_bloqueio(pendencia)
            notificacoes.append({
                'tipo': 'pendencia_bloqueio',
                'prioridade': PrioridadeNotificacao.ALTA,
                'mensagem': mensagem,
                'pendencia': pendencia,
                'acao_sugerida': 'mostrar_detalhes'
            })
        
        return notificacoes
```

---

## 🎤 Integração com TTS (Opcional)

### 7.1. TTS para Notificações Críticas

```python
def gerar_audio_notificacao(notificacao: Dict) -> Optional[str]:
    """
    Gera áudio TTS para notificações críticas.
    """
    if notificacao['prioridade'] != PrioridadeNotificacao.CRITICA:
        return None
    
    # Gerar texto simplificado para TTS
    texto_tts = simplificar_texto_para_tts(notificacao['mensagem'])
    
    # Gerar áudio usando OpenAI TTS
    audio_url = tts_service.gerar_audio(texto_tts, voice='nova')
    
    return audio_url
```

---

## 📊 Estrutura de Dados

### 8.1. Tabela de Notificações Humanizadas

```sql
CREATE TABLE [ia].[NOTIFICACAO_HUMANIZADA] (
    -- Identificação
    id_notificacao BIGINT IDENTITY(1,1) PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    
    -- Conteúdo
    tipo_notificacao VARCHAR(50) NOT NULL,          -- Ex: "navio_chegando", "atraso_critico", "status_mudou"
    prioridade VARCHAR(20) NOT NULL,                -- "critica", "alta", "media", "baixa"
    mensagem_humana TEXT NOT NULL,                  -- Mensagem formatada de forma humana
    mensagem_tecnica TEXT,                          -- Mensagem técnica (para logs)
    
    -- Contexto
    processo_referencia VARCHAR(50),                -- FK opcional
    dados_contexto NVARCHAR(MAX),                   -- JSON com dados adicionais
    acao_sugerida VARCHAR(100),                     -- Ex: "preparar_resumo", "verificar_pendencias"
    
    -- Status
    status VARCHAR(20) DEFAULT 'pendente',          -- 'pendente', 'enviada', 'lida', 'acao_tomada'
    enviada_em DATETIME,
    lida_em DATETIME,
    acao_tomada_em DATETIME,
    
    -- TTS
    audio_url VARCHAR(500),                         -- URL do áudio TTS (se gerado)
    audio_gerado BIT DEFAULT 0,
    
    -- Metadados
    criado_em DATETIME DEFAULT GETDATE(),
    atualizado_em DATETIME DEFAULT GETDATE(),
    
    -- Índices
    INDEX idx_session (session_id, status, criado_em DESC),
    INDEX idx_prioridade (prioridade, status),
    INDEX idx_processo (processo_referencia)
);
```

---

## 🚀 Implementação

### 9.1. Fase 1: Formatação de Mensagens (Semana 1)
- [ ] Criar `MensagemHumanizada` service
- [ ] Implementar templates de mensagens
- [ ] Testar formatação de diferentes tipos de eventos

### 9.2. Fase 2: Priorização e Timing (Semana 2)
- [ ] Implementar sistema de priorização
- [ ] Implementar agrupamento de notificações
- [ ] Implementar horários inteligentes

### 9.3. Fase 3: Notificações Proativas (Semana 3)
- [ ] Criar `NotificacoesProativasService`
- [ ] Implementar verificações periódicas
- [ ] Integrar com sistema de notificações existente

### 9.4. Fase 4: TTS e Personalização (Semana 4)
- [ ] Integrar TTS para notificações críticas
- [ ] Implementar personalização baseada em contexto
- [ ] Testes finais e ajustes

---

## 💡 Exemplos de Mensagens

### Exemplo 1: Navio Chegando

**Antes (Frio):**
```
🔔 Notificação: Navio chegando
Processo: ALH.0010/25
Data chegada: 08/01/2026
```

**Depois (Humano):**
```
👋 Oi! Só um toque: tem um navio chegando amanhã com 3 processos:
• ALH.0010/25
• VDM.0025/25
• DMD.0018/25

Quer que eu prepare um resumo do que precisa ser feito?
```

### Exemplo 2: Atraso Crítico

**Antes (Frio):**
```
🔔 Notificação: Processo com atraso
Processo: ALH.0010/25
Dias de atraso: 8
```

**Depois (Humano):**
```
⚠️ Atenção! O ALH.0010/25 está com 8 dias de atraso para registro.

Ainda não tem DI/DUIMP registrada. Quer que eu verifique o que está faltando?
```

### Exemplo 3: Status Mudou

**Antes (Frio):**
```
🔔 Notificação: Status da DI alterado
Processo: ALH.0010/25
Status anterior: DI_EM_ANALISE
Status novo: DI_DESEMBARACADA
```

**Depois (Humano):**
```
✅ Boa notícia! A DI do ALH.0010/25 foi desembaraçada agora há pouco.

Tá tudo certo pra seguir com a entrega! 🚚
```

---

## 🎯 Objetivos Finais

1. ✅ **Notificações que parecem conversas humanas**
2. ✅ **Proatividade inteligente** (avisar sobre o que realmente importa)
3. ✅ **Menos spam** (agrupamento e priorização)
4. ✅ **Sugestões de ação** (não apenas informar, mas ajudar)
5. ✅ **Timing inteligente** (não incomodar fora de horário)
6. ✅ **Personalização** (contexto e histórico)

---

**Última atualização:** 07/01/2026  
**Versão:** 1.0

