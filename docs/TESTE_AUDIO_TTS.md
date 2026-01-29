# 🔊 Guia de Teste de Áudio TTS

## ✅ Status: Áudios estão sendo gerados corretamente!

Os arquivos MP3 estão sendo criados em `downloads/tts/`. O problema pode ser na reprodução.

---

## 🧪 Teste Rápido

### Opção 1: Script Automático
```bash
python ouvir_audio_tts.py "Teste de áudio TTS"
```

### Opção 2: Abrir Manualmente
```bash
# Listar arquivos gerados
ls downloads/tts/*.mp3

# Abrir um arquivo específico no player padrão
open downloads/tts/c4c61f5118c0bbabb3d94215db628a94.mp3
```

### Opção 3: Interface Web (Recomendado)
1. Inicie o servidor: `python app.py`
2. Acesse: `http://localhost:5001/teste-tts`
3. Use o player de áudio integrado na página

---

## 🔍 Troubleshooting

### Se não ouvir som:

#### 1. Verificar Volume do Sistema
- Pressione **F12** (aumentar volume) várias vezes
- Verifique se não está mudo (ícone de alto-falante no menu bar)
- Teste com outro áudio (YouTube, Spotify) para confirmar que o som funciona

#### 2. Verificar Alto-falantes
- Se usar fones de ouvido, verifique se estão conectados
- Se usar Bluetooth, verifique se está conectado
- Teste com outro aplicativo de áudio

#### 3. Testar Arquivo Manualmente
```bash
# Abrir no Finder
open downloads/tts/

# Ou abrir diretamente
open downloads/tts/c4c61f5118c0bbabb3d94215db628a94.mp3
```

#### 4. Verificar se o arquivo está correto
```bash
# Verificar tamanho (deve ser > 0)
ls -lh downloads/tts/*.mp3

# Tentar reproduzir com afplay diretamente
afplay downloads/tts/c4c61f5118c0bbabb3d94215db628a94.mp3
```

#### 5. Testar com QuickTime
```bash
# Abrir no QuickTime Player
open -a "QuickTime Player" downloads/tts/c4c61f5118c0bbabb3d94215db628a94.mp3
```

---

## 🎯 Solução Recomendada: Interface Web

A interface web (`http://localhost:5001/teste-tts`) tem um player de áudio integrado que funciona melhor:

1. **Inicie o servidor:**
   ```bash
   python app.py
   ```

2. **Acesse no navegador:**
   ```
   http://localhost:5001/teste-tts
   ```

3. **Use o player HTML5:**
   - Clique em "Gerar Áudio"
   - O player aparecerá automaticamente
   - Clique no botão play para ouvir

---

## 📊 Verificação de Status

Execute para verificar se tudo está funcionando:

```bash
python3 << 'EOF'
import os
from pathlib import Path

# Verificar arquivos gerados
tts_dir = Path('downloads/tts')
mp3_files = list(tts_dir.glob('*.mp3'))

print(f"📁 Arquivos MP3 encontrados: {len(mp3_files)}")
if mp3_files:
    print(f"✅ Último arquivo: {mp3_files[-1].name}")
    print(f"📊 Tamanho: {mp3_files[-1].stat().st_size} bytes")
    print(f"💡 Para ouvir: open {mp3_files[-1].absolute()}")
else:
    print("❌ Nenhum arquivo encontrado")
EOF
```

---

## 🎤 Próximos Passos

Após confirmar que consegue ouvir os áudios:

1. ✅ Integrar TTS com notificações
2. ✅ Adicionar fila de reprodução no frontend
3. ✅ Implementar agrupamento de múltiplas notificações

---

**Última atualização:** 11/12/2025

