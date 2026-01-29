#!/usr/bin/env python3
"""
Script simples para gerar e reproduzir um áudio TTS imediatamente.

Uso:
    python ouvir_audio_tts.py "Texto a ser convertido em voz"
    python ouvir_audio_tts.py  # Usa texto padrão
"""
import os
import sys
import subprocess
from pathlib import Path

# Carregar .env
def load_env_from_file(filepath: str = '.env') -> None:
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, 'r', encoding='utf-8') as env_file:
            for line in env_file:
                s = line.strip()
                if not s or s.startswith('#') or '=' not in s:
                    continue
                k, v = s.split('=', 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass

load_env_from_file()
sys.path.insert(0, str(Path(__file__).parent))

from services.tts_service import TTSService

def main():
    # Texto a ser convertido
    if len(sys.argv) > 1:
        texto = ' '.join(sys.argv[1:])
    else:
        texto = "ALH ponto zero um seis seis barra vinte e cinco chegou ao destino. Status CE: ARMAZENADA."
    
    print(f"🎤 Gerando áudio TTS...")
    print(f"📝 Texto: '{texto}'")
    
    tts = TTSService()
    
    if not tts.enabled:
        print("❌ TTS desabilitado. Configure OPENAI_TTS_ENABLED=true no .env")
        return
    
    # Gerar áudio
    audio_url = tts.gerar_audio(texto)
    
    if not audio_url:
        print("❌ Falha ao gerar áudio")
        return
    
    # Caminho completo do arquivo
    caminho = Path('downloads') / 'tts' / Path(audio_url).name
    
    if not caminho.exists():
        print(f"❌ Arquivo não encontrado: {caminho}")
        return
    
    print(f"✅ Áudio gerado: {caminho.name}")
    print(f"🔊 Reproduzindo agora...")
    
    # Reproduzir no macOS
    try:
        # Tentar afplay primeiro
        proc = subprocess.Popen(['afplay', str(caminho.absolute())],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        print(f"✅ Áudio sendo reproduzido com afplay!")
        
        # Também tentar abrir no player padrão (backup)
        import time
        time.sleep(0.5)  # Dar tempo para afplay iniciar
        subprocess.Popen(['open', str(caminho.absolute())],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        print(f"✅ Também aberto no player padrão!")
        
        print(f"\n💡 Se não ouvir, verifique:")
        print(f"   - Volume do sistema (pressione F12 para aumentar)")
        print(f"   - Alto-falantes conectados")
        print(f"   - Arquivo: {caminho.absolute()}")
        print(f"\n💡 Para ouvir novamente, execute:")
        print(f"   open {caminho.absolute()}")
        
    except Exception as e:
        print(f"❌ Erro ao reproduzir: {e}")
        print(f"💡 Abra manualmente:")
        print(f"   open {caminho.absolute()}")

if __name__ == "__main__":
    main()

