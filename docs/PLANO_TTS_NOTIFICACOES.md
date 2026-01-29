# 🎤 Plano de Implementação: TTS (Text-to-Speech) para Notificações

**Data:** 10/12/2025  
**Objetivo:** Implementar síntese de voz para notificações usando GPT-4o mini TTS (OpenAI TTS API)

---

## 📋 Contexto Atual

### Sistema de Notificações Existente

#### **Arquitetura Atual:**
1. **Backend (`services/notificacao_service.py`):**
   - Detecta mudanças em processos (chegada, status DI/DUIMP/CE, pagamentos, pendências)
   - Cria notificações no banco SQLite (`notificacoes_processos`)
   - Tipos de notificações:
     - Chegada confirmada
     - Mudança de status DI/DUIMP/CE
     - AFRMM pago
     - ICMS pago
     - Pendências resolvidas
     - Frete pago

2. **Frontend (`templates/chat-ia-isolado.html`):**
   - **Polling a cada 30 segundos** (`/api/notificacoes`)
   - Exibe notificações não lidas
   - Marca como lida ao clicar (`/api/notificacoes/<id>/marcar-lida`)

3. **Endpoint Backend (`app.py`):**
   - `GET /api/notificacoes` - Retorna notificações não lidas
   - `POST /api/notificacoes/<id>/marcar-lida` - Marca como lida

#### **Estrutura de Dados:**
```sql
notificacoes_processos:
  - id
  - processo_referencia
  - tipo_notificacao
  - titulo
  - mensagem
  - dados_extras (JSON)
  - criado_em
  - lida
  - lida_em
```

---

## 🎯 Objetivo: TTS para Notificações

### **Funcionalidade Desejada:**
- Quando uma notificação é criada, **gerar áudio** usando OpenAI TTS
- **Reproduzir automaticamente** no navegador quando a notificação chegar
- **Suportar múltiplas notificações simultâneas** (5-10 ao mesmo tempo)

---

## 🔍 Análise de Viabilidade

### ✅ **VIABILIDADE: POSITIVA**

#### **1. OpenAI TTS API - Disponibilidade**
- ✅ **API TTS disponível** desde 2023
- ✅ **Modelos disponíveis:**
  - `tts-1` - Padrão, mais rápido
  - `tts-1-hd` - Alta qualidade, mais lento
- ✅ **Vozes disponíveis:**
  - `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
  - Suporte a português brasileiro
- ✅ **Formatos de saída:**
  - MP3, Opus, AAC, FLAC
  - Recomendado: **MP3** (compatibilidade universal)

#### **2. Integração Técnica**
- ✅ **Biblioteca Python:** `openai` (já usada no projeto)
- ✅ **Endpoint:** `POST https://api.openai.com/v1/audio/speech`
- ✅ **Custo:** ~$15 por 1 milhão de caracteres (tts-1)
- ✅ **Latência:** ~1-3 segundos por notificação (depende do tamanho do texto)

#### **3. Compatibilidade com Arquitetura Atual**
- ✅ **Backend Flask:** Pode gerar áudio e servir via endpoint
- ✅ **Frontend JavaScript:** Pode reproduzir áudio via `Audio API`
- ✅ **Polling existente:** Pode detectar novas notificações e tocar áudio

---

## 💰 Análise de Custos

### **Cenário de Uso Estimado:**

#### **Notificação Média:**
- **Tamanho:** ~100-200 caracteres
- **Exemplo:** "ALH.0166/25 chegou ao destino. Status CE: ARMAZENADA"

#### **Volume Diário Estimado:**
- **Cenário Conservador:** 50 notificações/dia
- **Cenário Médio:** 100 notificações/dia
- **Cenário Alto:** 200 notificações/dia

#### **Cálculo de Custo:**
```
Cenário Conservador:
  50 notificações × 150 caracteres = 7.500 caracteres/dia
  7.500 × 30 dias = 225.000 caracteres/mês
  Custo: $0.003/mês (praticamente grátis)

Cenário Médio:
  100 notificações × 150 caracteres = 15.000 caracteres/dia
  15.000 × 30 dias = 450.000 caracteres/mês
  Custo: $0.007/mês (praticamente grátis)

Cenário Alto:
  200 notificações × 150 caracteres = 30.000 caracteres/dia
  30.000 × 30 dias = 900.000 caracteres/mês
  Custo: $0.014/mês (praticamente grátis)
```

**✅ CONCLUSÃO:** Custo **extremamente baixo** (menos de $0.02/mês mesmo em cenário alto)

---

## 🏗️ Arquitetura Proposta

### **Fluxo de Implementação:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. NOTIFICAÇÃO CRIADA (Backend)                              │
│    services/notificacao_service.py                           │
│    ↓                                                          │
│ 2. GERAR ÁUDIO TTS (Backend)                                 │
│    Novo: services/tts_service.py                             │
│    - Chama OpenAI TTS API                                    │
│    - Salva MP3 em cache (downloads/tts/)                     │
│    - Retorna URL do áudio                                    │
│    ↓                                                          │
│ 3. SALVAR URL DO ÁUDIO (Backend)                             │
│    - Adicionar campo 'audio_url' em notificacoes_processos   │
│    - Ou salvar em dados_extras['audio_url']                  │
│    ↓                                                          │
│ 4. POLLING DETECTA NOVA NOTIFICAÇÃO (Frontend)               │
│    - Busca /api/notificacoes (a cada 30s)                    │
│    - Detecta notificações com audio_url                      │
│    ↓                                                          │
│ 5. REPRODUZIR ÁUDIO (Frontend)                               │
│    - Criar Audio() object                                    │
│    - Adicionar à fila de reprodução                          │
│    - Reproduzir sequencialmente                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Plano de Implementação

### **Fase 1: Backend - Serviço TTS**

#### **1.1. Criar `services/tts_service.py`**
```python
class TTSService:
    def gerar_audio(self, texto: str, voz: str = "nova") -> Optional[str]:
        """
        Gera áudio TTS usando OpenAI API.
        
        Args:
            texto: Texto a ser convertido em voz
            voz: Voz a usar (nova, alloy, echo, etc.)
            
        Returns:
            URL do arquivo de áudio gerado ou None se erro
        """
        # 1. Chamar OpenAI TTS API
        # 2. Salvar MP3 em downloads/tts/{hash}.mp3
        # 3. Retornar URL relativa: /api/download/tts/{hash}.mp3
```

#### **1.2. Integrar com `NotificacaoService`**
- Modificar `_salvar_notificacao()` para gerar áudio automaticamente
- Salvar `audio_url` em `dados_extras` ou campo dedicado

#### **1.3. Endpoint para Download de Áudio**
- Usar endpoint existente `/api/download/<filename>`
- Ou criar `/api/tts/<notificacao_id>` para gerar sob demanda

#### **1.4. Cache de Áudio**
- **Estratégia:** Gerar hash do texto + voz
- **Armazenamento:** `downloads/tts/{hash}.mp3`
- **Limpeza:** Limpar arquivos > 7 dias (similar a PDFs)

---

### **Fase 2: Frontend - Reprodução de Áudio**

#### **2.1. Fila de Reprodução**
```javascript
class AudioQueue {
  constructor() {
    this.queue = [];
    this.isPlaying = false;
  }
  
  add(audioUrl) {
    this.queue.push(audioUrl);
    this.playNext();
  }
  
  async playNext() {
    if (this.isPlaying || this.queue.length === 0) return;
    
    this.isPlaying = true;
    const audio = new Audio(this.queue.shift());
    
    audio.onended = () => {
      this.isPlaying = false;
      this.playNext(); // Próximo da fila
    };
    
    audio.onerror = () => {
      this.isPlaying = false;
      this.playNext(); // Pula se erro
    };
    
    await audio.play();
  }
}
```

#### **2.2. Integrar com Polling**
- Modificar `buscarNotificacoes()` para:
  - Detectar notificações novas (comparar IDs)
  - Verificar se tem `audio_url`
  - Adicionar à fila de reprodução

#### **2.3. Controles de Usuário**
- **Botão de mutar/desmutar** notificações por voz
- **Volume ajustável**
- **Indicador visual** quando áudio está tocando

---

### **Fase 3: Tratamento de Múltiplas Notificações**

#### **Problema: 5-10 Notificações Simultâneas**

#### **Solução 1: Fila Sequencial (Recomendada)**
- ✅ **Implementação:** Fila FIFO (First In, First Out)
- ✅ **Vantagens:**
  - Não sobrecarrega o navegador
  - Usuário ouve todas as notificações em ordem
  - Controle total sobre reprodução
- ⚠️ **Desvantagem:** Pode demorar se muitas notificações
- **Tempo estimado:** 5 notificações × 3s = 15s total

#### **Solução 2: Agrupamento Inteligente**
- ✅ **Implementação:** Agrupar notificações similares
- ✅ **Exemplo:**
  - "3 processos chegaram: ALH.0166/25, VDM.0004/25, BND.0093/25"
  - Em vez de 3 notificações separadas
- ✅ **Vantagens:**
  - Reduz tempo de reprodução
  - Mais eficiente
- ⚠️ **Desvantagem:** Pode perder detalhes

#### **Solução 3: Priorização**
- ✅ **Implementação:** Ordenar por prioridade
- ✅ **Prioridades:**
  1. **Crítica:** Pendências bloqueantes, atrasos críticos
  2. **Alta:** Chegadas, mudanças de status importantes
  3. **Média:** Pagamentos, pendências resolvidas
  4. **Baixa:** Mudanças menores
- ✅ **Vantagens:**
  - Usuário ouve o mais importante primeiro
- ⚠️ **Desvantagem:** Pode não ouvir todas se muitas

#### **Solução 4: Híbrida (Recomendada para Produção)**
```
1. Agrupar notificações similares (mesmo tipo, mesmo processo)
2. Priorizar por criticidade
3. Reproduzir sequencialmente com pausa entre grupos
4. Permitir usuário pular/próxima notificação
```

---

## 🎯 Estratégia Recomendada: Fila Sequencial + Agrupamento

### **Implementação Detalhada:**

#### **1. Agrupamento no Backend**
```python
def agrupar_notificacoes(notificacoes: List[Dict]) -> List[Dict]:
    """
    Agrupa notificações similares para reduzir volume de TTS.
    
    Exemplo:
    - 3 notificações de "chegada" → 1 notificação agrupada
    - 2 notificações de "AFRMM pago" → 1 notificação agrupada
    """
    grupos = {}
    
    for notif in notificacoes:
        chave = f"{notif['tipo_notificacao']}_{notif['processo_referencia']}"
        
        if chave not in grupos:
            grupos[chave] = []
        grupos[chave].append(notif)
    
    # Gerar notificações agrupadas
    notificacoes_agrupadas = []
    for chave, grupo in grupos.items():
        if len(grupo) == 1:
            notificacoes_agrupadas.append(grupo[0])
        else:
            # Criar notificação agrupada
            texto_agrupado = f"{len(grupo)} processos: {', '.join([n['processo_referencia'] for n in grupo])}"
            notificacoes_agrupadas.append({
                'tipo_notificacao': grupo[0]['tipo_notificacao'],
                'titulo': grupo[0]['titulo'],
                'mensagem': texto_agrupado,
                'processos': [n['processo_referencia'] for n in grupo]
            })
    
    return notificacoes_agrupadas
```

#### **2. Fila Sequencial no Frontend**
```javascript
class NotificationAudioQueue {
  constructor() {
    this.queue = [];
    this.isPlaying = false;
    this.currentAudio = null;
    this.userMuted = false; // Configuração do usuário
  }
  
  // Adicionar notificação à fila
  addNotification(notificacao) {
    if (!notificacao.audio_url || this.userMuted) return;
    
    this.queue.push({
      id: notificacao.id,
      audioUrl: notificacao.audio_url,
      titulo: notificacao.titulo,
      prioridade: this._calcularPrioridade(notificacao)
    });
    
    // Ordenar por prioridade
    this.queue.sort((a, b) => b.prioridade - a.prioridade);
    
    // Iniciar reprodução se não estiver tocando
    if (!this.isPlaying) {
      this.playNext();
    }
  }
  
  // Reproduzir próximo da fila
  async playNext() {
    if (this.isPlaying || this.queue.length === 0) return;
    
    this.isPlaying = true;
    const item = this.queue.shift();
    
    try {
      this.currentAudio = new Audio(item.audioUrl);
      
      // Eventos
      this.currentAudio.onended = () => {
        this.isPlaying = false;
        // Pausa de 500ms entre notificações
        setTimeout(() => this.playNext(), 500);
      };
      
      this.currentAudio.onerror = () => {
        console.error('Erro ao reproduzir áudio:', item.audioUrl);
        this.isPlaying = false;
        this.playNext(); // Pula para próxima
      };
      
      await this.currentAudio.play();
      
      // Indicador visual
      this._mostrarIndicadorAudio(item.titulo);
      
    } catch (error) {
      console.error('Erro ao iniciar áudio:', error);
      this.isPlaying = false;
      this.playNext();
    }
  }
  
  // Calcular prioridade (1-10)
  _calcularPrioridade(notif) {
    const prioridades = {
      'pendencia_bloqueante': 10,
      'atraso_critico': 9,
      'chegada': 8,
      'status_di_mudou': 7,
      'status_duimp_mudou': 7,
      'afrmm_pago': 5,
      'icms_pago': 5,
      'pendencia_resolvida': 4
    };
    
    return prioridades[notif.tipo_notificacao] || 3;
  }
  
  // Pular notificação atual
  skip() {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
      this.isPlaying = false;
      this.playNext();
    }
  }
  
  // Limpar fila
  clear() {
    this.queue = [];
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
    this.isPlaying = false;
  }
}

// Instância global
const audioQueue = new NotificationAudioQueue();
```

#### **3. Integração com Polling**
```javascript
let ultimasNotificacoesIds = new Set();

async function buscarNotificacoes() {
  try {
    const response = await fetch('/api/notificacoes?apenas_nao_lidas=true&limite=10');
    const data = await response.json();
    
    if (data.success && data.notificacoes) {
      // Detectar novas notificações
      const novasNotificacoes = data.notificacoes.filter(
        n => !ultimasNotificacoesIds.has(n.id)
      );
      
      // Atualizar conjunto de IDs conhecidos
      novasNotificacoes.forEach(n => ultimasNotificacoesIds.add(n.id));
      
      // Adicionar à fila de áudio
      novasNotificacoes.forEach(notif => {
        if (notif.audio_url) {
          audioQueue.addNotification(notif);
        }
      });
      
      // Exibir notificações na UI
      exibirNotificacoes(data.notificacoes);
    }
  } catch (error) {
    console.error('Erro ao buscar notificações:', error);
  }
}
```

---

## ⚙️ Configurações Necessárias

### **1. Variáveis de Ambiente (.env)**
```bash
# TTS (OpenAI)
OPENAI_TTS_ENABLED=true
OPENAI_TTS_VOICE=nova          # Voz padrão (nova, alloy, echo, etc.)
OPENAI_TTS_MODEL=tts-1         # tts-1 (rápido) ou tts-1-hd (qualidade)
OPENAI_TTS_CACHE_ENABLED=true  # Cache de áudios gerados
OPENAI_TTS_CACHE_DAYS=7        # Dias para manter cache
```

### **2. Estrutura de Diretórios**
```
Chat-IA-Independente/
├── downloads/
│   ├── pdfs/          # PDFs (já existe)
│   └── tts/           # Áudios TTS (novo)
│       └── {hash}.mp3
```

### **3. Banco de Dados**
```sql
-- Opção 1: Adicionar campo dedicado
ALTER TABLE notificacoes_processos 
ADD COLUMN audio_url TEXT;

-- Opção 2: Usar dados_extras (já existe)
-- Salvar: dados_extras = '{"audio_url": "/api/download/tts/abc123.mp3"}'
```

---

## 🚀 Roadmap de Implementação

### **Sprint 1: Backend TTS (2-3 dias)**
- [ ] Criar `services/tts_service.py`
- [ ] Integrar com `NotificacaoService`
- [ ] Endpoint para download de áudio
- [ ] Sistema de cache e limpeza
- [ ] Testes unitários

### **Sprint 2: Frontend Básico (2-3 dias)**
- [ ] Criar `AudioQueue` class
- [ ] Integrar com polling de notificações
- [ ] Reprodução sequencial básica
- [ ] Indicador visual de áudio tocando

### **Sprint 3: Múltiplas Notificações (2-3 dias)**
- [ ] Agrupamento de notificações similares
- [ ] Sistema de priorização
- [ ] Controles de usuário (mute, skip, volume)
- [ ] Tratamento de erros e edge cases

### **Sprint 4: Polimento (1-2 dias)**
- [ ] Testes end-to-end
- [ ] Ajustes de UX
- [ ] Documentação
- [ ] Deploy

**Total Estimado:** 7-11 dias de desenvolvimento

---

## ⚠️ Considerações e Limitações

### **1. Limitações Técnicas**
- ⚠️ **Latência:** ~1-3s por notificação (geração + download)
- ⚠️ **Dependência de Internet:** Requer conexão para gerar áudio
- ⚠️ **Compatibilidade de Navegador:** Audio API suportado em todos navegadores modernos
- ⚠️ **Autoplay Policy:** Navegadores podem bloquear autoplay (requer interação do usuário primeiro)

### **2. Soluções para Autoplay Policy**
- ✅ **Solução:** Primeira interação do usuário habilita TTS
- ✅ **Implementação:** Botão "Ativar notificações por voz" na primeira vez
- ✅ **Alternativa:** Reproduzir apenas após clique do usuário

### **3. Fallback**
- ✅ **Se TTS falhar:** Notificação visual normal (já existe)
- ✅ **Se áudio não carregar:** Pula para próxima notificação
- ✅ **Se API TTS indisponível:** Continua funcionando sem áudio

---

## 📊 Métricas de Sucesso

### **KPIs a Acompanhar:**
1. **Taxa de Geração de Áudio:** % de notificações com áudio gerado
2. **Tempo de Reprodução:** Tempo médio para reproduzir todas as notificações
3. **Taxa de Erro:** % de falhas na geração/reprodução
4. **Custo Mensal:** Custo real da API TTS
5. **Satisfação do Usuário:** Feedback sobre utilidade

---

## 🎯 Conclusão

### **✅ Viabilidade: ALTA**

**Pontos Positivos:**
- ✅ API TTS disponível e estável
- ✅ Custo extremamente baixo (< $0.02/mês)
- ✅ Integração simples com arquitetura existente
- ✅ Melhora significativa na UX (notificações audíveis)

**Desafios:**
- ⚠️ Tratamento de múltiplas notificações simultâneas (solução: fila sequencial)
- ⚠️ Autoplay policy dos navegadores (solução: ativação manual)
- ⚠️ Latência de geração (solução: cache + agrupamento)

**Recomendação:** ✅ **IMPLEMENTAR**

A funcionalidade é viável, de baixo custo e traz valor significativo ao usuário. A estratégia de fila sequencial + agrupamento resolve o problema de múltiplas notificações simultâneas de forma elegante.

---

## 📚 Referências

- [OpenAI TTS API Documentation](https://platform.openai.com/docs/guides/text-to-speech)
- [Web Audio API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [Browser Autoplay Policies](https://developer.mozilla.org/en-US/docs/Web/Media/Autoplay_guide)

---

**Última atualização:** 10/12/2025

