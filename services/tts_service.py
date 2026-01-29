"""
Serviço de Text-to-Speech (TTS) usando OpenAI TTS API.
"""
import os
import hashlib
import logging
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def load_env_from_file(filepath: str = '.env') -> None:
    """Carrega variáveis de ambiente do arquivo .env"""
    # Tentar vários caminhos possíveis
    possible_paths = [
        Path(filepath),
        Path(__file__).parent.parent / filepath if '__file__' in globals() else None,
        Path(os.getcwd()) / filepath,
    ]
    
    for path in possible_paths:
        if path and path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as env_file:
                    for line in env_file:
                        s = line.strip()
                        if not s or s.startswith('#') or '=' not in s:
                            continue
                        k, v = s.split('=', 1)
                        # Remover comentários inline (tudo após #)
                        if '#' in v:
                            v = v.split('#')[0].strip()
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
                logger.debug(f"✅ TTS: .env carregado de {path.absolute()}")
                return
            except OSError:
                continue
    
    logger.warning(f"⚠️ TTS: .env não encontrado em nenhum dos caminhos")

# NÃO carregar .env no nível do módulo - será carregado no __init__


class TTSService:
    """Serviço para gerar áudio TTS usando OpenAI API"""
    
    def __init__(self):
        """Inicializa o serviço TTS"""
        # ✅ Recarregar .env sempre que criar uma instância (para pegar atualizações)
        load_env_from_file()
        
        # Debug: verificar variáveis após carregar
        tts_enabled_raw = os.getenv('OPENAI_TTS_ENABLED', 'false')
        logger.debug(f"🔍 DEBUG TTS: OPENAI_TTS_ENABLED='{tts_enabled_raw}' (tipo: {type(tts_enabled_raw)})")
        
        self.enabled = tts_enabled_raw.lower() == 'true'
        self.api_key = os.getenv('DUIMP_AI_API_KEY', '')  # Usa mesma chave da IA
        self.voice = os.getenv('OPENAI_TTS_VOICE', 'nova')  # Voz padrão
        self.model = os.getenv('OPENAI_TTS_MODEL', 'tts-1')  # tts-1 (rápido) ou tts-1-hd (qualidade)
        self.cache_enabled = os.getenv('OPENAI_TTS_CACHE_ENABLED', 'true').lower() == 'true'
        self.cache_days = int(os.getenv('OPENAI_TTS_CACHE_DAYS', '7'))
        # ✅ Limite de arquivos em cache (proteção contra diretório crescendo sem controle)
        # Mantém os mais recentes e remove os mais antigos quando passar do limite.
        self.cache_max_files = int(os.getenv('OPENAI_TTS_CACHE_MAX_FILES', '500'))
        # ✅ NOVO: Velocidade de fala (não suportado diretamente pela API, mas podemos usar formatação de texto)
        self.slow_speech = os.getenv('OPENAI_TTS_SLOW_SPEECH', 'true').lower() == 'true'  # Adicionar pausas no texto
        
        # Diretório para cache de áudios
        self.cache_dir = Path('downloads/tts')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🎤 TTSService inicializado: enabled={self.enabled}, voice={self.voice}, api_key_presente={bool(self.api_key)}")
        
        if not self.enabled:
            logger.warning(f"⚠️ TTS desabilitado (OPENAI_TTS_ENABLED='{tts_enabled_raw}' -> {self.enabled})")
        elif not self.api_key:
            logger.warning("⚠️ TTS desabilitado (DUIMP_AI_API_KEY não configurada)")
            self.enabled = False
    
    def gerar_audio(self, texto: str, voz: Optional[str] = None, usar_cache: bool = True, formatar_texto: bool = True) -> Optional[str]:
        """
        Gera áudio TTS a partir de um texto.
        
        Args:
            texto: Texto a ser convertido em voz
            voz: Voz a usar (nova, alloy, echo, fable, onyx, shimmer). Se None, usa voz padrão
            usar_cache: Se True, verifica cache antes de gerar
            formatar_texto: Se True, aplica formatação automática de siglas e processos para melhor TTS (padrão: True)
            
        Returns:
            URL relativa do arquivo de áudio (ex: /api/download/tts/abc123.mp3)
            ou None se erro
        """
        if not self.enabled:
            logger.warning("⚠️ TTS desabilitado, não foi possível gerar áudio")
            return None
        
        if not texto or not texto.strip():
            logger.warning("⚠️ Texto vazio para TTS")
            return None
        
        # Normalizar texto
        texto = texto.strip()
        
        # ✅ NOVO: Formatar texto para TTS (siglas, processos, etc.) se solicitado
        if formatar_texto:
            try:
                from utils.tts_text_formatter import preparar_texto_tts
                texto_original = texto
                texto = preparar_texto_tts(texto)
                logger.debug(f"🎤 Texto formatado para TTS: '{texto_original[:50]}...' → '{texto[:50]}...'")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao formatar texto para TTS: {e}. Usando texto original.")
                # Continuar com texto original se formatação falhar
        
        voz_usar = voz or self.voice
        
        # Gerar hash do texto + voz para cache
        cache_key = self._gerar_hash_cache(texto, voz_usar)
        arquivo_cache = self.cache_dir / f"{cache_key}.mp3"
        
        # Verificar cache
        if usar_cache and self.cache_enabled and arquivo_cache.exists():
            # Verificar se cache não expirou
            if self._cache_valido(arquivo_cache):
                logger.info(f"✅ Áudio encontrado no cache: {arquivo_cache.name}")
                return f"/api/download/tts/{arquivo_cache.name}"
            else:
                # Cache expirado, remover
                try:
                    arquivo_cache.unlink()
                    logger.debug(f"🗑️ Cache expirado removido: {arquivo_cache.name}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao remover cache expirado: {e}")
        
        # Gerar novo áudio
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key, timeout=30.0)
            
            logger.info(f"🎤 Gerando áudio TTS: '{texto[:50]}...' (voz: {voz_usar}, modelo: {self.model})")
            
            response = client.audio.speech.create(
                model=self.model,
                voice=voz_usar,
                input=texto,
                response_format="mp3"
            )
            
            # Salvar arquivo
            arquivo_cache.parent.mkdir(parents=True, exist_ok=True)
            with open(arquivo_cache, 'wb') as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
            
            logger.info(f"✅ Áudio gerado e salvo: {arquivo_cache.name}")
            return f"/api/download/tts/{arquivo_cache.name}"
            
        except ImportError:
            logger.error("❌ Biblioteca 'openai' não instalada. Execute: pip install openai")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao gerar áudio TTS: {e}", exc_info=True)
            return None
    
    def _gerar_hash_cache(self, texto: str, voz: str) -> str:
        """Gera hash para usar como nome do arquivo de cache"""
        # Hash do texto + voz + modelo
        conteudo = f"{texto}|{voz}|{self.model}"
        return hashlib.md5(conteudo.encode('utf-8')).hexdigest()
    
    def _cache_valido(self, arquivo: Path) -> bool:
        """Verifica se arquivo de cache ainda é válido (não expirou)"""
        try:
            stat = arquivo.stat()
            idade = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
            return idade < timedelta(days=self.cache_days)
        except Exception:
            return False
    
    def limpar_cache_expirado(self) -> int:
        """
        Remove arquivos de cache expirados.
        
        Returns:
            Número de arquivos removidos
        """
        if not self.cache_dir.exists():
            return 0
        
        removidos = 0
        agora = datetime.now()
        
        try:
            for arquivo in self.cache_dir.glob("*.mp3"):
                try:
                    stat = arquivo.stat()
                    idade = agora - datetime.fromtimestamp(stat.st_mtime)
                    
                    if idade > timedelta(days=self.cache_days):
                        arquivo.unlink()
                        removidos += 1
                        logger.debug(f"🗑️ Cache expirado removido: {arquivo.name}")
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao processar arquivo de cache {arquivo.name}: {e}")
            
            if removidos > 0:
                logger.info(f"✅ {removidos} arquivo(s) de cache expirado removido(s)")
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar cache: {e}", exc_info=True)
        
        return removidos

    def limpar_cache_por_tamanho(self) -> int:
        """
        Garante que o cache não passe de `cache_max_files` arquivos.

        Returns:
            Número de arquivos removidos
        """
        if not self.cache_dir.exists():
            return 0
        
        if not self.cache_max_files or self.cache_max_files <= 0:
            return 0

        try:
            arquivos = list(self.cache_dir.glob("*.mp3"))
            if len(arquivos) <= self.cache_max_files:
                return 0
            
            # Ordenar por mtime (mais novos primeiro)
            arquivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            manter = set(arquivos[: self.cache_max_files])
            remover = [p for p in arquivos if p not in manter]
            
            removidos = 0
            for arquivo in remover:
                try:
                    arquivo.unlink()
                    removidos += 1
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao remover cache antigo {arquivo.name}: {e}")
            if removidos > 0:
                logger.info(
                    f"🧹 Cache TTS: removidos {removidos} arquivo(s) para respeitar OPENAI_TTS_CACHE_MAX_FILES={self.cache_max_files}"
                )
            return removidos
        except Exception as e:
            logger.error(f"❌ Erro ao aplicar limite de cache TTS: {e}", exc_info=True)
            return 0

    def limpar_cache(self) -> dict:
        """
        Limpeza completa do cache:
        - remove expirados (cache_days)
        - aplica limite de quantidade (cache_max_files)
        """
        removidos_expirados = self.limpar_cache_expirado()
        removidos_por_tamanho = self.limpar_cache_por_tamanho()
        return {
            "removidos_expirados": removidos_expirados,
            "removidos_por_tamanho": removidos_por_tamanho,
            "cache_days": self.cache_days,
            "cache_max_files": self.cache_max_files,
        }
