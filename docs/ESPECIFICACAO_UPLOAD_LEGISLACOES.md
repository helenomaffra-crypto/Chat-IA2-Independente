# 📤 Especificação: Upload de Legislações via Chat (Estilo WhatsApp)

**Data:** 19/12/2025  
**Objetivo:** Permitir upload de PDFs de legislações diretamente no chat, com processamento automático e criação de índice

---

## 🎯 CONCEITO

Similar ao WhatsApp, o usuário pode:
1. Clicar em botão de anexo (📎) no chat
2. Selecionar PDF de legislação
3. Enviar no chat
4. Maike processa automaticamente:
   - Extrai estrutura (artigos, parágrafos, incisos)
   - Identifica metadados (número, tipo, data)
   - Cria índice no banco de dados
   - Gera embeddings para busca semântica
5. Retorna feedback em tempo real no chat

---

## 🏗️ ARQUITETURA

### 1. **Frontend (Chat UI)**

#### 1.1. Botão de Anexo
- Ícone 📎 ao lado do campo de texto
- Abre seletor de arquivo (apenas PDFs)
- Preview do arquivo antes de enviar

#### 1.2. Mensagem de Upload
- Mostra arquivo anexado (nome, tamanho)
- Indicador de progresso
- Status: "Processando...", "Indexando...", "Concluído!"

#### 1.3. Feedback da Maike
- Mensagens automáticas durante processamento
- Resumo do que foi indexado
- Link para consultar a legislação

### 2. **Backend (API)**

#### 2.1. Endpoint de Upload
```
POST /api/legislacoes/upload
Content-Type: multipart/form-data

Body:
- file: PDF file
- session_id: string (opcional)
```

#### 2.2. Processamento Assíncrono
- Upload → Validação → Parse → Indexação → Embeddings
- Feedback via WebSocket ou polling

#### 2.3. Integração com Chat
- Detecta upload de PDF no chat
- Chama automaticamente processamento
- Retorna mensagem formatada

---

## 🔧 IMPLEMENTAÇÃO

### 1. **Frontend: Botão de Upload**

```html
<!-- templates/chat-ia-isolado.html -->
<div class="chat-input-container">
    <button class="btn-anexo" id="btnAnexo" title="Anexar arquivo">
        📎
    </button>
    <input type="file" id="fileInput" accept=".pdf" style="display: none;">
    <input type="text" id="mensagemInput" placeholder="Digite sua mensagem...">
    <button class="btn-enviar" id="btnEnviar">➤</button>
</div>
```

```javascript
// JavaScript para upload
document.getElementById('btnAnexo').addEventListener('click', () => {
    document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.pdf')) {
        alert('Apenas arquivos PDF são permitidos');
        return;
    }
    
    // Mostrar preview no chat
    adicionarMensagemUpload(file);
    
    // Enviar para processamento
    await enviarArquivoParaProcessamento(file);
});

async function enviarArquivoParaProcessamento(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    
    // Mostrar status "Processando..."
    atualizarStatusUpload('Processando PDF...');
    
    try {
        const response = await fetch('/api/legislacoes/upload', {
            method: 'POST',
            body: formData
        });
        
        const resultado = await response.json();
        
        if (resultado.sucesso) {
            atualizarStatusUpload('✅ Indexado com sucesso!');
            // Adicionar mensagem da Maike com resumo
            adicionarMensagemMaike(resultado.resumo);
        } else {
            atualizarStatusUpload('❌ Erro: ' + resultado.erro);
        }
    } catch (error) {
        atualizarStatusUpload('❌ Erro ao processar: ' + error.message);
    }
}
```

### 2. **Backend: Endpoint de Upload**

```python
# app.py

@app.route('/api/legislacoes/upload', methods=['POST'])
def upload_legislacao():
    """
    Endpoint para upload de PDFs de legislações.
    
    Processo:
    1. Recebe PDF
    2. Valida formato
    3. Processa assincronamente
    4. Retorna status inicial
    """
    from flask import request
    from services.legislacao_service import LegislacaoService
    import os
    import uuid
    
    try:
        if 'file' not in request.files:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        session_id = request.form.get('session_id', 'default')
        
        if file.filename == '':
            return jsonify({
                'sucesso': False,
                'erro': 'Nome de arquivo vazio'
            }), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                'sucesso': False,
                'erro': 'Apenas arquivos PDF são permitidos'
            }), 400
        
        # Salvar arquivo temporariamente
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'legislacoes')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_id = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f'{file_id}.pdf')
        file.save(file_path)
        
        # Processar assincronamente (ou sincronamente se rápido)
        legislacao_service = LegislacaoService()
        resultado = legislacao_service.processar_pdf(
            file_path=file_path,
            nome_original=file.filename,
            session_id=session_id
        )
        
        # Limpar arquivo temporário
        try:
            os.remove(file_path)
        except:
            pass
        
        if resultado.get('sucesso'):
            return jsonify({
                'sucesso': True,
                'legislacao_id': resultado.get('legislacao_id'),
                'resumo': resultado.get('resumo'),
                'mensagem': resultado.get('mensagem')
            }), 200
        else:
            return jsonify({
                'sucesso': False,
                'erro': resultado.get('erro', 'Erro desconhecido')
            }), 500
            
    except Exception as e:
        logger.error(f'Erro ao processar upload de legislação: {e}', exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': f'Erro interno: {str(e)}'
        }), 500
```

### 3. **Serviço de Processamento**

```python
# services/legislacao_service.py

class LegislacaoService:
    """
    Serviço para processar e indexar legislações.
    """
    
    def processar_pdf(
        self,
        file_path: str,
        nome_original: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processa PDF de legislação e cria índice.
        
        Processo:
        1. Extrair texto do PDF
        2. Parsear estrutura (artigos, parágrafos, incisos)
        3. Identificar metadados (número, tipo, data)
        4. Salvar no banco
        5. Gerar embeddings (opcional, pode ser assíncrono)
        
        Returns:
            Dict com sucesso, legislacao_id, resumo, mensagem
        """
        try:
            from utils.legislacao_parser import LegislacaoParser
            
            # 1. Parsear PDF
            parser = LegislacaoParser()
            dados_legislacao = parser.parse_pdf(file_path)
            
            if not dados_legislacao:
                return {
                    'sucesso': False,
                    'erro': 'Não foi possível extrair dados do PDF'
                }
            
            # 2. Salvar no banco
            legislacao_id = self._salvar_legislacao(dados_legislacao)
            
            # 3. Gerar embeddings (pode ser assíncrono)
            self._gerar_embeddings_artigos(legislacao_id)
            
            # 4. Formatar resumo
            resumo = self._formatar_resumo_indexacao(dados_legislacao)
            
            return {
                'sucesso': True,
                'legislacao_id': legislacao_id,
                'resumo': resumo,
                'mensagem': f'✅ Legislação indexada com sucesso!\n\n{resumo}'
            }
            
        except Exception as e:
            logger.error(f'Erro ao processar PDF: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def _formatar_resumo_indexacao(self, dados: Dict[str, Any]) -> str:
        """Formata resumo da indexação para exibir no chat."""
        tipo = dados.get('tipo', 'Legislação')
        numero = dados.get('numero', 'N/A')
        data = dados.get('data_publicacao', 'N/A')
        total_artigos = len(dados.get('artigos', []))
        
        return f"""📚 **{tipo} nº {numero}**

📅 Publicada em: {data}
📄 Total de artigos indexados: {total_artigos}

✅ Agora você pode perguntar sobre esta legislação!
Exemplos:
- "o que define a operação por encomenda na IN {numero}?"
- "artigo 2º da IN {numero}"
- "quais são os requisitos da IN {numero}?""""
```

### 4. **Integração com Chat (Precheck)**

```python
# services/precheck_service.py

def _precheck_upload_legislacao(
    self,
    mensagem: str,
    mensagem_lower: str,
    session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Detecta se há upload de legislação pendente.
    
    Nota: Upload é processado via endpoint separado,
    mas podemos detectar mensagens relacionadas.
    """
    # Se houver arquivo anexado, já foi processado pelo endpoint
    # Este precheck pode ser usado para perguntas sobre uploads recentes
    pass
```

---

## 📊 FLUXO COMPLETO

### Exemplo de Uso:

```
1. Usuário clica em 📎 no chat
2. Seleciona "IN RFB nº 1861-2018.pdf"
3. Chat mostra: "📎 IN RFB nº 1861-2018.pdf (2.3 MB)"
4. Status: "⏳ Processando PDF..."
5. Maike responde: "📚 Recebi o PDF! Estou processando e criando o índice..."
6. Status: "⏳ Indexando artigos..."
7. Maike responde: "✅ Legislação indexada com sucesso!

📚 **IN RFB nº 1861**

📅 Publicada em: 28/12/2018
📄 Total de artigos indexados: 13

✅ Agora você pode perguntar sobre esta legislação!
Exemplos:
- "o que define a operação por encomenda na IN 1861?"
- "artigo 2º da IN 1861"
- "quais são os requisitos da IN 1861?""

8. Usuário: "o que define a operação por encomenda?"
9. Maike: [Busca semântica e retorna Art. 3º com contexto completo]
```

---

## 🎨 UI/UX (Estilo WhatsApp)

### Mensagem de Upload:
```
┌─────────────────────────────────────┐
│ 📎 IN RFB nº 1861-2018.pdf          │
│    2.3 MB                           │
│    ⏳ Processando...                 │
└─────────────────────────────────────┘
```

### Mensagem da Maike (Resumo):
```
┌─────────────────────────────────────┐
│ 🤖 mAIke                            │
│                                     │
│ ✅ Legislação indexada!            │
│                                     │
│ 📚 IN RFB nº 1861                   │
│ 📅 Publicada em: 28/12/2018        │
│ 📄 13 artigos indexados            │
│                                     │
│ Agora você pode perguntar sobre     │
│ esta legislação!                    │
└─────────────────────────────────────┘
```

---

## ⚡ OTIMIZAÇÕES

### 1. **Processamento Assíncrono**
- Para PDFs grandes, processar em background
- Usar WebSocket ou polling para feedback em tempo real
- Mostrar progresso: "Extraindo texto...", "Parseando artigos...", "Gerando embeddings..."

### 2. **Cache de Embeddings**
- Gerar embeddings apenas uma vez por artigo
- Armazenar em banco para reutilização
- Atualizar apenas se artigo for alterado

### 3. **Validação Inteligente**
- Detectar automaticamente tipo de legislação (IN RFB, Decreto, Lei)
- Extrair número e data automaticamente
- Validar estrutura antes de indexar

---

## 🚀 FASEAMENTO

### **Fase 1: MVP** (2-3 dias)
- [ ] Botão de upload no frontend
- [ ] Endpoint básico de upload
- [ ] Parser simples de PDF (extrair texto, identificar artigos)
- [ ] Salvar no banco (estrutura básica)
- [ ] Feedback no chat

### **Fase 2: Melhorias** (1 semana)
- [ ] Processamento assíncrono
- [ ] Identificação automática de metadados
- [ ] Referências cruzadas
- [ ] Embeddings para busca semântica

### **Fase 3: Avançado** (futuro)
- [ ] Histórico de alterações
- [ ] Validação de estrutura
- [ ] Preview do PDF no chat
- [ ] Edição de artigos indexados

---

## 💡 VANTAGENS

1. **UX Familiar:** Similar ao WhatsApp, intuitivo
2. **Automático:** Zero configuração, apenas upload
3. **Integrado:** Funciona dentro do fluxo de trabalho existente
4. **Feedback Imediato:** Usuário vê progresso em tempo real
5. **Escalável:** Fácil adicionar novas legislações

---

## ⚠️ CONSIDERAÇÕES

### **Limites:**
- Tamanho máximo de arquivo: 10 MB (configurável)
- Apenas PDFs (por enquanto)
- Processamento pode levar alguns segundos para PDFs grandes

### **Segurança:**
- Validar tipo de arquivo (apenas PDF)
- Limitar tamanho
- Sanitizar nomes de arquivo
- Validar estrutura antes de indexar

---

**Próximo passo:** Implementar Fase 1 (MVP) com upload básico e parser simples.



