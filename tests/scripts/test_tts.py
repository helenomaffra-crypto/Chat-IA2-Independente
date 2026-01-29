#!/usr/bin/env python3
"""
Script de teste isolado para TTS (Text-to-Speech).

Este script testa a funcionalidade TTS com frases mockadas antes de integrar
na aplicação principal.

Uso:
    python test_tts.py
"""
import os
import sys
from pathlib import Path

# ✅ CORREÇÃO: Adicionar diretório raiz ao path (subir 2 níveis: tests/scripts/ -> raiz)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Carregar .env antes de importar o serviço
def load_env_from_file(filepath: str = '.env') -> None:
    """Carrega variáveis de ambiente do arquivo .env"""
    # ✅ CORREÇÃO: Tentar vários caminhos possíveis (incluindo raiz do projeto)
    possible_paths = [
        Path(filepath),
        project_root / filepath,  # Raiz do projeto
        Path(__file__).parent / filepath,
        Path(os.getcwd()) / filepath,
    ]
    
    for path in possible_paths:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as env_file:
                    for line in env_file:
                        s = line.strip()
                        if not s or s.startswith('#') or '=' not in s:
                            continue
                        k, v = s.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
                print(f"✅ Carregado .env de: {path.absolute()}")
                return
            except OSError as e:
                print(f"⚠️ Erro ao ler .env de {path}: {e}")
                continue
    print("⚠️ Arquivo .env não encontrado")

# Carregar .env
load_env_from_file()

from services.tts_service import TTSService
import logging
import subprocess
import platform
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def reproduzir_audio(caminho_arquivo: str) -> bool:
    """
    Reproduz um arquivo de áudio usando o player padrão do sistema.
    
    Args:
        caminho_arquivo: Caminho completo do arquivo de áudio
        
    Returns:
        True se conseguiu reproduzir, False caso contrário
    """
    try:
        sistema = platform.system()
        
        if sistema == 'Darwin':  # macOS
            # Usar 'afplay' (player nativo do macOS)
            subprocess.Popen(['afplay', caminho_arquivo], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return True
        elif sistema == 'Linux':
            # Tentar vários players comuns no Linux
            players = ['aplay', 'paplay', 'mpg123', 'mpg321']
            for player in players:
                try:
                    subprocess.Popen([player, caminho_arquivo],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    return True
                except FileNotFoundError:
                    continue
        elif sistema == 'Windows':
            # Windows: usar 'start' para abrir com player padrão
            subprocess.Popen(['start', caminho_arquivo], shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            return True
        
        return False
    except Exception as e:
        logger.warning(f"⚠️ Erro ao reproduzir áudio: {e}")
        return False


def testar_tts_basico():
    """Teste básico de geração de áudio"""
    print("\n" + "="*60)
    print("🎤 TESTE 1: Geração Básica de Áudio")
    print("="*60)
    
    tts = TTSService()
    
    if not tts.enabled:
        print("❌ TTS desabilitado. Configure OPENAI_TTS_ENABLED=true no .env")
        return False
    
    # Frase de teste
    texto_teste = "Olá! Esta é uma notificação de teste do sistema de importação."
    
    print(f"📝 Texto: '{texto_teste}'")
    print(f"🎤 Voz: {tts.voice}")
    print(f"🤖 Modelo: {tts.model}")
    print("\n⏳ Gerando áudio...")
    
    audio_url = tts.gerar_audio(texto_teste)
    
    if audio_url:
        print(f"✅ Áudio gerado com sucesso!")
        print(f"📁 URL: {audio_url}")
        
        # Tentar reproduzir automaticamente
        caminho_completo = Path('downloads') / 'tts' / Path(audio_url).name
        if caminho_completo.exists():
            print(f"🔊 Reproduzindo áudio...")
            if reproduzir_audio(str(caminho_completo.absolute())):
                print(f"✅ Áudio sendo reproduzido no player padrão")
                time.sleep(2)  # Dar tempo para o áudio começar
            else:
                print(f"💡 Para ouvir, acesse: http://localhost:5001{audio_url}")
                print(f"   Ou abra manualmente: {caminho_completo.absolute()}")
        else:
            print(f"💡 Para ouvir, acesse: http://localhost:5001{audio_url}")
        
        return True
    else:
        print("❌ Falha ao gerar áudio")
        return False


def testar_multiplas_frases():
    """Teste com múltiplas frases (simulando notificações)"""
    print("\n" + "="*60)
    print("🎤 TESTE 2: Múltiplas Frases (Simulando Notificações)")
    print("="*60)
    
    tts = TTSService()
    
    if not tts.enabled:
        print("❌ TTS desabilitado")
        return False
    
    # Frases mockadas de notificações
    frases_teste = [
        "ALH ponto zero um seis seis barra vinte e cinco chegou ao destino. Status CE: ARMAZENADA.",
        "VDM ponto zero zero zero quatro barra vinte e cinco. AFRMM pago com sucesso.",
        "BND ponto zero zero nove três barra vinte e cinco. Pendência de ICMS resolvida.",
        "MV5 ponto zero zero dois dois barra vinte e cinco. Status DUIMP alterado para PARAMETRIZADA.",
        "GYM ponto zero zero dois oito barra vinte e cinco. Processo chegando hoje com ETA confirmado."
    ]
    
    print(f"📝 Gerando {len(frases_teste)} áudios...\n")
    
    sucessos = 0
    falhas = 0
    
    for i, frase in enumerate(frases_teste, 1):
        print(f"[{i}/{len(frases_teste)}] Gerando: '{frase[:50]}...'")
        audio_url = tts.gerar_audio(frase)
        
        if audio_url:
            print(f"      ✅ Sucesso: {audio_url}")
            sucessos += 1
            
            # Reproduzir apenas a primeira frase automaticamente
            if i == 1:
                caminho_completo = Path('downloads') / 'tts' / Path(audio_url).name
                if caminho_completo.exists():
                    print(f"      🔊 Reproduzindo primeira notificação...")
                    reproduzir_audio(str(caminho_completo.absolute()))
                    time.sleep(4)  # Aguardar áudio tocar
        else:
            print(f"      ❌ Falha")
            falhas += 1
    
    print(f"\n📊 Resultado: {sucessos} sucesso(s), {falhas} falha(s)")
    return sucessos > 0


def testar_diferentes_vozes():
    """Teste com diferentes vozes disponíveis"""
    print("\n" + "="*60)
    print("🎤 TESTE 3: Diferentes Vozes")
    print("="*60)
    
    tts = TTSService()
    
    if not tts.enabled:
        print("❌ TTS desabilitado")
        return False
    
    vozes = ['nova', 'alloy', 'echo', 'fable', 'onyx', 'shimmer']
    texto_teste = "Esta é uma notificação de teste do sistema."
    
    print(f"📝 Texto: '{texto_teste}'")
    print(f"🎤 Testando {len(vozes)} vozes diferentes...\n")
    
    sucessos = 0
    
    for i, voz in enumerate(vozes):
        print(f"🎤 Testando voz '{voz}'...")
        audio_url = tts.gerar_audio(texto_teste, voz=voz, usar_cache=False)
        
        if audio_url:
            print(f"      ✅ Sucesso: {audio_url}")
            sucessos += 1
            
            # Reproduzir apenas a primeira voz automaticamente
            if i == 0:
                caminho_completo = Path('downloads') / 'tts' / Path(audio_url).name
                if caminho_completo.exists():
                    print(f"      🔊 Reproduzindo voz '{voz}'...")
                    reproduzir_audio(str(caminho_completo.absolute()))
                    time.sleep(3)  # Aguardar áudio tocar
        else:
            print(f"      ❌ Falha")
    
    print(f"\n📊 Resultado: {sucessos}/{len(vozes)} vozes funcionaram")
    return sucessos > 0


def testar_cache():
    """Teste do sistema de cache"""
    print("\n" + "="*60)
    print("🎤 TESTE 4: Sistema de Cache")
    print("="*60)
    
    tts = TTSService()
    
    if not tts.enabled:
        print("❌ TTS desabilitado")
        return False
    
    texto_teste = "Esta é uma notificação para testar o cache do sistema."
    
    print("📝 Primeira geração (deve criar arquivo)...")
    audio_url_1 = tts.gerar_audio(texto_teste, usar_cache=False)
    
    if not audio_url_1:
        print("❌ Falha na primeira geração")
        return False
    
    print(f"✅ Primeira geração: {audio_url_1}")
    
    print("\n📝 Segunda geração (deve usar cache)...")
    audio_url_2 = tts.gerar_audio(texto_teste, usar_cache=True)
    
    if audio_url_2 == audio_url_1:
        print(f"✅ Cache funcionando! Mesma URL: {audio_url_2}")
        return True
    else:
        print(f"⚠️ URLs diferentes (pode ser normal se cache desabilitado)")
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🎤 TESTE ISOLADO DE TTS (Text-to-Speech)")
    print("="*60)
    print("\nEste script testa a funcionalidade TTS antes de integrar na aplicação.")
    print("Certifique-se de ter configurado no .env:")
    print("  - OPENAI_TTS_ENABLED=true")
    print("  - DUIMP_AI_API_KEY=sua_chave_aqui")
    print("  - OPENAI_TTS_VOICE=nova (opcional)")
    print("  - OPENAI_TTS_MODEL=tts-1 (opcional)")
    print()
    
    # Verificar variáveis de ambiente
    if not os.getenv('OPENAI_TTS_ENABLED', 'false').lower() == 'true':
        print("⚠️ AVISO: OPENAI_TTS_ENABLED não está 'true' no .env")
        print("   Os testes podem falhar.\n")
    
    if not os.getenv('DUIMP_AI_API_KEY'):
        print("⚠️ AVISO: DUIMP_AI_API_KEY não configurada no .env")
        print("   Os testes vão falhar.\n")
    
    resultados = []
    
    # Executar testes
    resultados.append(("Teste Básico", testar_tts_basico()))
    resultados.append(("Múltiplas Frases", testar_multiplas_frases()))
    resultados.append(("Diferentes Vozes", testar_diferentes_vozes()))
    resultados.append(("Sistema de Cache", testar_cache()))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    total_sucessos = sum(1 for _, s in resultados if s)
    total_testes = len(resultados)
    
    print(f"\n📈 Total: {total_sucessos}/{total_testes} testes passaram")
    
    if total_sucessos == total_testes:
        print("\n🎉 Todos os testes passaram! TTS está funcionando corretamente.")
        print("💡 Próximo passo: Integrar na aplicação principal.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique a configuração e tente novamente.")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()

