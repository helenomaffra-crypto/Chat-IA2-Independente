# 📰 Análise: Integração de Feeds RSS do Siscomex

**Data:** 17/01/2026  
**Status:** 📋 **ANÁLISE** - Viabilidade técnica e proposta de implementação

---

## 🎯 Objetivo

Integrar feeds RSS do Siscomex para que o Maike receba notícias automaticamente e notifique o usuário sobre atualizações importantes.

**Feeds disponíveis:**
- Notícias Siscomex Importação: https://www.gov.br/siscomex/pt-br/noticias/noticias-siscomex-importacao/noticias-siscomex-importacao/RSS
- Notícias Siscomex Sistemas: https://www.gov.br/siscomex/pt-br/noticias/noticias-siscomex-sistemas/noticias-siscomex-sistemas/RSS

---

## ✅ **VIABILIDADE: POSITIVA**

### **1. Infraestrutura Existente**

✅ **Sistema de Notificações:**
- Tabela `notificacoes_processos` no SQLite
- `NotificacaoService` para criar notificações
- Endpoint `/api/notificacoes` para buscar notificações
- Frontend faz polling a cada 30 segundos
- Sistema de TTS (Text-to-Speech) já implementado

✅ **Sistema de Agendamento:**
- `ScheduledNotificationsService` usando `APScheduler`
- Já tem jobs agendados (resumos diários, lembretes)
- Usa `BackgroundScheduler` com `CronTrigger`

✅ **Sincronização Automática:**
- `ProcessoKanbanService` já tem sincronização em background
- Usa threads para rodar periodicamente

### **2. Bibliotecas Necessárias**

✅ **feedparser** (não está no `requirements.txt`, mas é leve e confiável):
- Biblioteca Python padrão para parsing de RSS/Atom
- Suporta RSS 2.0, Atom, e outros formatos
- Tratamento de encoding automático
- Extração de título, descrição, link, data de publicação

✅ **requests** (já está no `requirements.txt`):
- Para fazer HTTP GET nos feeds RSS

---

## 📊 **COMPLEXIDADE: BAIXA-MÉDIA**

### **Complexidade Técnica: ⭐⭐☆☆☆ (2/5)**

**Fatores que facilitam:**
- ✅ Infraestrutura de notificações já existe
- ✅ Sistema de agendamento já existe
- ✅ Biblioteca `feedparser` é simples de usar
- ✅ RSS é um formato padronizado

**Fatores que complicam:**
- ⚠️ Detecção de duplicatas (evitar notificar a mesma notícia)
- ⚠️ Filtragem inteligente (quais notícias são relevantes?)
- ⚠️ Tratamento de erros (feed indisponível, timeout, etc.)
- ⚠️ Armazenamento de histórico (quais notícias já foram processadas?)

### **Complexidade de Negócio: ⭐⭐☆☆☆ (2/5)**

**Decisões necessárias:**
1. **Frequência de verificação:** A cada 1h? 2h? 4h?
2. **Filtragem:** Notificar todas as notícias ou apenas as relevantes?
3. **Priorização:** Algumas notícias são mais importantes que outras?
4. **Histórico:** Quanto tempo manter histórico de notícias processadas?

---

## 🏗️ **ARQUITETURA PROPOSTA**

### **Componentes Necessários**

#### **1. `services/rss_siscomex_service.py`** (NOVO)
**Responsabilidade:** Buscar e processar feeds RSS do Siscomex

**Funcionalidades:**
- `buscar_feed_rss(url)`: Faz HTTP GET e parseia RSS
- `extrair_noticias(feed)`: Extrai lista de notícias do feed
- `filtrar_noticias_relevantes(noticias)`: Filtra notícias relevantes (opcional)
- `verificar_duplicata(noticia)`: Verifica se notícia já foi processada
- `processar_novas_noticias()`: Método principal que busca, filtra e cria notificações

**Estrutura de dados:**
```python
{
    'titulo': str,
    'descricao': str,
    'link': str,
    'data_publicacao': datetime,
    'fonte': str,  # 'siscomex_importacao' ou 'siscomex_sistemas'
    'guid': str,  # ID único da notícia (para detecção de duplicatas)
}
```

#### **2. Tabela SQLite: `noticias_siscomex`** (NOVO)
**Responsabilidade:** Armazenar histórico de notícias processadas

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS noticias_siscomex (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guid TEXT UNIQUE NOT NULL,  -- ID único da notícia (evita duplicatas)
    titulo TEXT NOT NULL,
    descricao TEXT,
    link TEXT NOT NULL,
    data_publicacao TIMESTAMP,
    fonte TEXT NOT NULL,  -- 'siscomex_importacao' ou 'siscomex_sistemas'
    notificada BOOLEAN DEFAULT 0,  -- Se já foi criada notificação
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_guid (guid),
    INDEX idx_fonte_data (fonte, data_publicacao DESC)
);
```

#### **3. Integração com `ScheduledNotificationsService`**
**Responsabilidade:** Agendar verificação periódica de feeds RSS

**Modificações:**
- Adicionar job no `ScheduledNotificationsService`:
  ```python
  # Verificar feeds RSS a cada 2 horas
  self.scheduler.add_job(
      func=self._verificar_feeds_rss,
      trigger=IntervalTrigger(hours=2),
      id='rss_siscomex_2h',
      name='Verificar Feeds RSS Siscomex',
      replace_existing=True
  )
  ```

#### **4. Integração com `NotificacaoService`**
**Responsabilidade:** Criar notificações para novas notícias

**Tipo de notificação:**
- `tipo_notificacao`: `'noticia_siscomex'`
- `processo_referencia`: `'SISCOMEX'`
- `titulo`: Título da notícia
- `mensagem`: Descrição da notícia + link
- `dados_extras`: `{'link': url, 'fonte': 'siscomex_importacao' ou 'siscomex_sistemas'}`

---

## 🔍 **DESAFIOS E SOLUÇÕES**

### **1. Detecção de Duplicatas**

**Problema:** Evitar notificar a mesma notícia múltiplas vezes.

**Solução:**
- Usar `guid` (ID único) do RSS como chave única
- Armazenar `guid` na tabela `noticias_siscomex` com `UNIQUE`
- Antes de criar notificação, verificar se `guid` já existe
- Se existir, pular (não criar notificação)

**Implementação:**
```python
def verificar_duplicata(self, guid: str) -> bool:
    """Verifica se notícia já foi processada"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM noticias_siscomex WHERE guid = ?', (guid,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0
```

### **2. Filtragem Inteligente (Opcional)**

**Problema:** Nem todas as notícias são relevantes para o usuário.

**Solução (Fase 1 - Simples):**
- Notificar todas as notícias (sem filtragem)
- Usuário pode marcar como "não relevante" no futuro

**Solução (Fase 2 - Avançada):**
- Usar IA para classificar relevância
- Palavras-chave: "DUIMP", "DI", "importação", "desembaraço", "AFRMM", etc.
- Score de relevância (0-1)
- Só notificar se score > 0.7

**Implementação (Fase 2):**
```python
def filtrar_noticias_relevantes(self, noticias: List[Dict]) -> List[Dict]:
    """Filtra notícias relevantes usando palavras-chave"""
    palavras_chave = ['DUIMP', 'DI', 'importação', 'desembaraço', 'AFRMM', 
                     'Siscomex', 'Portal Único', 'Integra Comex']
    
    noticias_relevantes = []
    for noticia in noticias:
        titulo = noticia.get('titulo', '').upper()
        descricao = noticia.get('descricao', '').upper()
        texto_completo = f"{titulo} {descricao}"
        
        # Contar palavras-chave encontradas
        score = sum(1 for palavra in palavras_chave if palavra.upper() in texto_completo)
        
        # Se encontrou pelo menos 1 palavra-chave, é relevante
        if score > 0:
            noticia['score_relevancia'] = score
            noticias_relevantes.append(noticia)
    
    return noticias_relevantes
```

### **3. Tratamento de Erros**

**Problema:** Feed pode estar indisponível, timeout, formato inválido, etc.

**Solução:**
- Try/except em todas as operações
- Logging detalhado de erros
- Retry com backoff exponencial (opcional)
- Não bloquear outras notificações se RSS falhar

**Implementação:**
```python
def buscar_feed_rss(self, url: str) -> Optional[Dict]:
    """Busca feed RSS com tratamento de erros"""
    try:
        import feedparser
        import requests
        
        # Timeout de 10 segundos
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        
        if feed.bozo:  # Erro de parsing
            logger.warning(f"⚠️ Erro ao parsear RSS: {feed.bozo_exception}")
            return None
        
        return feed
    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout ao buscar feed RSS: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro HTTP ao buscar feed RSS: {url} - {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao buscar feed RSS: {url} - {e}", exc_info=True)
        return None
```

### **4. Armazenamento de Histórico**

**Problema:** Quanto tempo manter histórico de notícias processadas?

**Solução:**
- Manter histórico por 90 dias (configurável)
- Limpeza automática de notícias antigas
- Job agendado para limpeza semanal

**Implementação:**
```python
def limpar_noticias_antigas(self, dias_retencao: int = 90):
    """Remove notícias mais antigas que X dias"""
    from datetime import datetime, timedelta
    from db_manager import get_db_connection
    
    limite = datetime.now() - timedelta(days=dias_retencao)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM noticias_siscomex WHERE data_publicacao < ?',
        (limite.isoformat(),)
    )
    removidas = cursor.rowcount
    conn.commit()
    conn.close()
    
    logger.info(f"🧹 Limpeza de notícias antigas: {removidas} notícias removidas")
```

---

## 📋 **PLANO DE IMPLEMENTAÇÃO**

### **Fase 1: MVP (Mínimo Viável) - 2-3 horas**

**Objetivo:** Notificar todas as notícias do Siscomex sem filtragem.

**Tarefas:**
1. ✅ Adicionar `feedparser` ao `requirements.txt`
2. ✅ Criar tabela `noticias_siscomex` no `db_manager.py`
3. ✅ Criar `services/rss_siscomex_service.py` com:
   - `buscar_feed_rss(url)`
   - `extrair_noticias(feed)`
   - `verificar_duplicata(guid)`
   - `processar_novas_noticias()`
4. ✅ Integrar com `ScheduledNotificationsService` (verificar a cada 2h)
5. ✅ Integrar com `NotificacaoService` (criar notificações)
6. ✅ Testar com feeds reais

**Critérios de sucesso:**
- ✅ Notificações aparecem no frontend quando há novas notícias
- ✅ Não cria notificações duplicadas
- ✅ Funciona mesmo se feed estiver temporariamente indisponível

### **Fase 2: Filtragem Inteligente (Opcional) - 1-2 horas**

**Objetivo:** Filtrar notícias relevantes usando palavras-chave.

**Tarefas:**
1. ✅ Implementar `filtrar_noticias_relevantes()` com palavras-chave
2. ✅ Adicionar score de relevância
3. ✅ Configurar threshold (ex: score > 0.7)
4. ✅ Testar com notícias reais

**Critérios de sucesso:**
- ✅ Notifica apenas notícias relevantes
- ✅ Score de relevância é calculado corretamente

### **Fase 3: Limpeza Automática (Opcional) - 30 minutos**

**Objetivo:** Limpar notícias antigas automaticamente.

**Tarefas:**
1. ✅ Implementar `limpar_noticias_antigas()`
2. ✅ Adicionar job agendado semanal
3. ✅ Testar limpeza

**Critérios de sucesso:**
- ✅ Notícias antigas são removidas automaticamente
- ✅ Não remove notícias recentes

---

## 🧪 **TESTES**

### **Testes Unitários**

```python
# tests/test_rss_siscomex_service.py

def test_buscar_feed_rss():
    """Testa busca de feed RSS"""
    service = RssSiscomexService()
    feed = service.buscar_feed_rss("https://www.gov.br/siscomex/.../RSS")
    assert feed is not None
    assert 'entries' in feed

def test_extrair_noticias():
    """Testa extração de notícias do feed"""
    service = RssSiscomexService()
    feed = service.buscar_feed_rss("...")
    noticias = service.extrair_noticias(feed)
    assert len(noticias) > 0
    assert 'titulo' in noticias[0]
    assert 'guid' in noticias[0]

def test_verificar_duplicata():
    """Testa detecção de duplicatas"""
    service = RssSiscomexService()
    guid = "test-guid-123"
    
    # Primeira vez: não é duplicata
    assert not service.verificar_duplicata(guid)
    
    # Salvar notícia
    service._salvar_noticia({'guid': guid, ...})
    
    # Segunda vez: é duplicata
    assert service.verificar_duplicata(guid)
```

### **Testes de Integração**

```python
# tests/test_rss_integracao.py

def test_processar_novas_noticias():
    """Testa processamento completo de novas notícias"""
    service = RssSiscomexService()
    
    # Processar feeds
    novas = service.processar_novas_noticias()
    
    # Verificar se notificações foram criadas
    from services.notificacao_service import NotificacaoService
    notif_service = NotificacaoService()
    notificacoes = notif_service.buscar_notificacoes(
        tipo='noticia_siscomex',
        limite=10
    )
    
    assert len(notificacoes) > 0
```

---

## 📊 **ESTIMATIVA DE ESFORÇO**

| Fase | Tarefas | Tempo Estimado |
|------|---------|----------------|
| **Fase 1: MVP** | Implementação básica | 2-3 horas |
| **Fase 2: Filtragem** | Filtragem inteligente | 1-2 horas |
| **Fase 3: Limpeza** | Limpeza automática | 30 minutos |
| **Total** | | **3.5-5.5 horas** |

---

## 🎯 **RECOMENDAÇÃO**

✅ **RECOMENDO IMPLEMENTAR** - Viabilidade alta, complexidade baixa-média, esforço moderado.

**Vantagens:**
- ✅ Infraestrutura já existe (notificações, agendamento)
- ✅ Biblioteca `feedparser` é confiável e simples
- ✅ Valor agregado alto (usuário fica informado sobre mudanças no Siscomex)
- ✅ Baixo risco (não afeta funcionalidades existentes)

**Riscos:**
- ⚠️ Feed pode estar indisponível temporariamente (tratado com try/except)
- ⚠️ Pode gerar muitas notificações (mitigado com filtragem opcional)
- ⚠️ Requer manutenção se estrutura do RSS mudar (baixa probabilidade)

**Próximos passos:**
1. Confirmar se usuário quer implementar
2. Decidir frequência de verificação (recomendo 2h)
3. Decidir se quer filtragem inteligente (Fase 1 ou Fase 2)
4. Implementar Fase 1 (MVP)

---

## 📚 **REFERÊNCIAS**

- **feedparser:** https://pythonhosted.org/feedparser/
- **APScheduler:** https://apscheduler.readthedocs.io/
- **RSS 2.0 Spec:** https://www.rssboard.org/rss-specification

---

**Última atualização:** 17/01/2026
