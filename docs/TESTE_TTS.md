# 🎤 Guia de Teste TTS (Text-to-Speech)

Este guia explica como testar a funcionalidade TTS de forma isolada antes de integrar na aplicação.

---

## 📋 Pré-requisitos

1. **Configurar variáveis de ambiente no `.env`:**
   ```bash
   OPENAI_TTS_ENABLED=true
   DUIMP_AI_API_KEY=sua_chave_openai_aqui
   OPENAI_TTS_VOICE=nova          # Opcional (padrão: nova)
   OPENAI_TTS_MODEL=tts-1         # Opcional (padrão: tts-1)
   OPENAI_TTS_CACHE_ENABLED=true  # Opcional (padrão: true)
   OPENAI_TTS_CACHE_DAYS=7        # Opcional (padrão: 7)
   ```

2. **Biblioteca OpenAI instalada:**
   ```bash
   pip install openai
   ```

---

## 🧪 Opção 1: Teste via Script Python (Terminal)

Execute o script de teste isolado:

```bash
python test_tts.py
```

Este script executa 4 testes:
1. ✅ **Teste Básico**: Gera um áudio de uma frase simples
2. ✅ **Múltiplas Frases**: Gera áudios de 5 notificações mockadas
3. ✅ **Diferentes Vozes**: Testa todas as vozes disponíveis
4. ✅ **Sistema de Cache**: Verifica se o cache está funcionando

**Resultado esperado:**
```
🎤 TESTE ISOLADO DE TTS (Text-to-Speech)
============================================================
...
✅ PASSOU - Teste Básico
✅ PASSOU - Múltiplas Frases
✅ PASSOU - Diferentes Vozes
✅ PASSOU - Sistema de Cache

📈 Total: 4/4 testes passaram
🎉 Todos os testes passaram! TTS está funcionando corretamente.
```

---

## 🌐 Opção 2: Teste via Interface Web

1. **Iniciar o servidor Flask:**
   ```bash
   python app.py
   ```

2. **Abrir no navegador:**
   ```
   http://localhost:5001/teste-tts
   ```

3. **Testar funcionalidades:**
   - **Teste de Frase Única**: Digite um texto e gere o áudio
   - **Teste de Múltiplas Frases**: Gere 5 áudios simultaneamente (simulando notificações)

---

## 🧪 Opção 3: Teste via API (cURL/Postman)

### Teste de Frase Única:
```bash
curl -X POST http://localhost:5001/api/teste/tts \
  -H "Content-Type: application/json" \
  -d '{
    "texto": "ALH ponto zero um seis seis barra vinte e cinco chegou ao destino.",
    "voz": "nova"
  }'
```

**Resposta esperada:**
```json
{
  "success": true,
  "audio_url": "/api/download/tts/abc123.mp3",
  "texto": "ALH ponto zero um seis seis barra vinte e cinco chegou ao destino.",
  "voz": "nova"
}
```

### Teste de Múltiplas Frases:
```bash
curl -X POST http://localhost:5001/api/teste/tts/multiplas \
  -H "Content-Type: application/json" \
  -d '{
    "frases": [
      "ALH ponto zero um seis seis barra vinte e cinco chegou ao destino.",
      "VDM ponto zero zero zero quatro barra vinte e cinco. AFRMM pago com sucesso."
    ],
    "voz": "nova"
  }'
```

---

## 📁 Estrutura de Arquivos Criados

```
Chat-IA-Independente/
├── services/
│   └── tts_service.py          # Serviço TTS principal
├── test_tts.py                 # Script de teste isolado
├── test_tts_html.html          # Interface web de teste
├── downloads/
│   └── tts/                    # Cache de áudios gerados
│       └── {hash}.mp3
└── TESTE_TTS.md                # Este arquivo
```

---

## ✅ Verificações

### 1. Verificar se TTS está habilitado:
```python
from services.tts_service import TTSService
tts = TTSService()
print(f"TTS habilitado: {tts.enabled}")
```

### 2. Verificar diretório de cache:
```bash
ls -la downloads/tts/
```

### 3. Ouvir um áudio gerado:
Acesse no navegador:
```
http://localhost:5001/api/download/tts/{hash}.mp3
```

---

## 🐛 Troubleshooting

### Erro: "TTS desabilitado"
- ✅ Verifique se `OPENAI_TTS_ENABLED=true` no `.env`
- ✅ Verifique se `DUIMP_AI_API_KEY` está configurada

### Erro: "Biblioteca 'openai' não instalada"
```bash
pip install openai
```

### Erro: "Falha ao gerar áudio"
- ✅ Verifique se a chave da API está válida
- ✅ Verifique se há créditos na conta OpenAI
- ✅ Verifique os logs do servidor para mais detalhes

### Áudio não toca no navegador
- ✅ Verifique se o arquivo foi gerado: `ls downloads/tts/`
- ✅ Verifique se o endpoint `/api/download/tts/` está funcionando
- ✅ Verifique o console do navegador para erros

---

## 🎯 Próximos Passos

Após confirmar que os testes estão funcionando:

1. ✅ Integrar TTS com `NotificacaoService`
2. ✅ Adicionar fila de reprodução no frontend
3. ✅ Implementar agrupamento de notificações
4. ✅ Adicionar controles de usuário (mute, volume)

---

**Última atualização:** 10/12/2025

