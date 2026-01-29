"""
Serviço para buscar e processar feeds RSS do Siscomex.
Notifica o usuário sobre novas notícias relacionadas a importação e sistemas.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import feedparser
import requests

logger = logging.getLogger(__name__)


class RssSiscomexService:
    """Serviço para buscar e processar feeds RSS do Siscomex"""
    
    # URLs dos feeds RSS
    FEED_IMPORTACAO = "https://www.gov.br/siscomex/pt-br/noticias/noticias-siscomex-importacao/noticias-siscomex-importacao/RSS"
    FEED_SISTEMAS = "https://www.gov.br/siscomex/pt-br/noticias/noticias-siscomex-sistemas/noticias-siscomex-sistemas/RSS"
    
    def __init__(self):
        """Inicializa o serviço de RSS"""
        self.feeds = {
            'siscomex_importacao': self.FEED_IMPORTACAO,
            'siscomex_sistemas': self.FEED_SISTEMAS
        }
    
    def buscar_feed_rss(self, url: str) -> Optional[Dict]:
        """
        Busca feed RSS com tratamento de erros.
        
        Args:
            url: URL do feed RSS
            
        Returns:
            Dict com dados do feed ou None se houver erro
        """
        try:
            # Timeout de 10 segundos
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parsear feed RSS
            feed = feedparser.parse(response.content)
            
            # Verificar se houve erro de parsing
            if feed.bozo:
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
    
    def extrair_noticias(self, feed: Dict, fonte: str) -> List[Dict[str, Any]]:
        """
        Extrai lista de notícias do feed RSS.
        
        Args:
            feed: Feed RSS parseado
            fonte: Nome da fonte ('siscomex_importacao' ou 'siscomex_sistemas')
            
        Returns:
            Lista de notícias com estrutura padronizada
        """
        noticias = []
        
        if not feed or 'entries' not in feed:
            logger.warning(f"⚠️ Feed vazio ou sem entries: {fonte}")
            return noticias
        
        for entry in feed.entries:
            try:
                # Extrair GUID (ID único da notícia)
                guid = entry.get('id') or entry.get('link') or entry.get('title', '')
                
                # Extrair título
                titulo = entry.get('title', 'Sem título')
                
                # Extrair descrição
                descricao = entry.get('summary', '') or entry.get('description', '')
                
                # Extrair link
                link = entry.get('link', '')
                
                # Extrair data de publicação
                data_publicacao = None
                if 'published_parsed' in entry and entry.published_parsed:
                    try:
                        # published_parsed / updated_parsed vêm como struct_time em UTC (feeds usam 'Z').
                        # Usar timegm (UTC) em vez de mktime (local) para evitar deslocamentos.
                        from calendar import timegm
                        data_publicacao = datetime.fromtimestamp(timegm(entry.published_parsed))
                    except:
                        pass
                elif 'updated_parsed' in entry and entry.updated_parsed:
                    try:
                        from calendar import timegm
                        data_publicacao = datetime.fromtimestamp(timegm(entry.updated_parsed))
                    except:
                        pass
                elif 'published' in entry and entry.get('published'):
                    try:
                        from dateutil import parser
                        data_publicacao = parser.parse(entry.published)
                    except:
                        pass
                elif 'updated' in entry and entry.get('updated'):
                    try:
                        from dateutil import parser
                        data_publicacao = parser.parse(entry.updated)
                    except:
                        pass
                
                noticia = {
                    'guid': guid,
                    'titulo': titulo,
                    'descricao': descricao,
                    'link': link,
                    'data_publicacao': data_publicacao,
                    'fonte': fonte
                }
                
                noticias.append(noticia)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair notícia do feed {fonte}: {e}")
                continue
        
        logger.info(f"✅ Extraídas {len(noticias)} notícias do feed {fonte}")
        return noticias
    
    def verificar_duplicata(self, guid: str) -> bool:
        """
        Verifica se notícia já foi processada (duplicata).
        
        Args:
            guid: GUID único da notícia
            
        Returns:
            True se já existe, False caso contrário
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM noticias_siscomex WHERE guid = ?', (guid,))
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
        except Exception as e:
            logger.error(f"❌ Erro ao verificar duplicata: {e}", exc_info=True)
            # Em caso de erro, assumir que não é duplicata para não perder notícias
            return False
    
    def _salvar_noticia(self, noticia: Dict[str, Any]) -> bool:
        """
        Salva notícia no banco de dados.
        
        Args:
            noticia: Dict com dados da notícia
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Converter data_publicacao para string ISO
            data_publicacao_str = None
            if noticia.get('data_publicacao'):
                if isinstance(noticia['data_publicacao'], datetime):
                    data_publicacao_str = noticia['data_publicacao'].isoformat()
                else:
                    data_publicacao_str = str(noticia['data_publicacao'])
            
            # ✅ Upsert: se a notícia já existe, atualizar campos e preencher data_publicacao se estiver vazia.
            # Mantém o flag `notificada` existente (não volta para 0).
            cursor.execute(
                '''
                INSERT INTO noticias_siscomex
                (guid, titulo, descricao, link, data_publicacao, fonte, notificada)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(guid) DO UPDATE SET
                    titulo = excluded.titulo,
                    descricao = excluded.descricao,
                    link = excluded.link,
                    fonte = excluded.fonte,
                    data_publicacao = COALESCE(noticias_siscomex.data_publicacao, excluded.data_publicacao)
                ''',
                (
                    noticia['guid'],
                    noticia['titulo'],
                    noticia.get('descricao', ''),
                    noticia['link'],
                    data_publicacao_str,
                    noticia['fonte'],
                ),
            )
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar notícia: {e}", exc_info=True)
            return False
    
    def _criar_notificacao(self, noticia: Dict[str, Any]) -> bool:
        """
        Cria notificação para uma nova notícia.
        
        Args:
            noticia: Dict com dados da notícia
            
        Returns:
            True se criou com sucesso, False caso contrário
        """
        try:
            from services.notificacao_service import NotificacaoService
            
            # Formatar mensagem
            mensagem = noticia.get('descricao', '')
            if not mensagem:
                mensagem = f"Nova notícia do Siscomex: {noticia.get('titulo', '')}"
            
            # Adicionar link se disponível
            if noticia.get('link'):
                mensagem += f"\n\n🔗 Link: {noticia['link']}"
            
            # Criar notificação
            notificacao = {
                'processo_referencia': 'SISCOMEX',
                'tipo_notificacao': 'noticia_siscomex',
                'titulo': f"📰 {noticia.get('titulo', 'Nova Notícia Siscomex')}",
                'mensagem': mensagem,
                'dados_extras': {
                    'link': noticia.get('link', ''),
                    'fonte': noticia.get('fonte', ''),
                    'guid': noticia.get('guid', '')
                }
            }
            
            notif_service = NotificacaoService()
            sucesso = notif_service._salvar_notificacao(notificacao)
            
            if sucesso:
                # Marcar notícia como notificada
                self._marcar_como_notificada(noticia['guid'])
                logger.info(f"✅ Notificação criada para notícia: {noticia.get('titulo', '')[:50]}...")
            
            return sucesso
        except Exception as e:
            logger.error(f"❌ Erro ao criar notificação: {e}", exc_info=True)
            return False
    
    def _marcar_como_notificada(self, guid: str) -> bool:
        """
        Marca notícia como notificada no banco.
        
        Args:
            guid: GUID único da notícia
            
        Returns:
            True se marcou com sucesso, False caso contrário
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE noticias_siscomex SET notificada = 1 WHERE guid = ?',
                (guid,)
            )
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao marcar como notificada: {e}", exc_info=True)
            return False
    
    def processar_novas_noticias(self) -> Dict[str, Any]:
        """
        Processa feeds RSS e cria notificações para novas notícias.
        
        Returns:
            Dict com estatísticas do processamento
        """
        estatisticas = {
            'feeds_processados': 0,
            'noticias_encontradas': 0,
            'noticias_novas': 0,
            'notificacoes_criadas': 0,
            'erros': 0
        }
        
        logger.info("📰 Iniciando processamento de feeds RSS do Siscomex...")
        
        for fonte_nome, url in self.feeds.items():
            try:
                logger.info(f"📡 Buscando feed: {fonte_nome} ({url})")
                
                # Buscar feed
                feed = self.buscar_feed_rss(url)
                if not feed:
                    estatisticas['erros'] += 1
                    continue
                
                estatisticas['feeds_processados'] += 1
                
                # Extrair notícias
                noticias = self.extrair_noticias(feed, fonte_nome)
                estatisticas['noticias_encontradas'] += len(noticias)
                
                # Processar cada notícia
                for noticia in noticias:
                    try:
                        # ✅ Importante: sempre fazer UPSERT para backfill (ex: preencher data_publicacao)
                        # Mesmo se já existir, salvamos de novo para atualizar campos faltantes.
                        ja_existe = self.verificar_duplicata(noticia['guid'])

                        # Salvar notícia no banco (upsert)
                        if not self._salvar_noticia(noticia):
                            continue

                        # Se já existia, não cria notificação novamente
                        if ja_existe:
                            continue

                        estatisticas['noticias_novas'] += 1

                        # Criar notificação apenas para notícias realmente novas
                        if self._criar_notificacao(noticia):
                            estatisticas['notificacoes_criadas'] += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Erro ao processar notícia: {e}", exc_info=True)
                        estatisticas['erros'] += 1
                        continue
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar feed {fonte_nome}: {e}", exc_info=True)
                estatisticas['erros'] += 1
                continue
        
        logger.info(
            f"✅ Processamento concluído: "
            f"{estatisticas['feeds_processados']} feeds, "
            f"{estatisticas['noticias_encontradas']} notícias encontradas, "
            f"{estatisticas['noticias_novas']} novas, "
            f"{estatisticas['notificacoes_criadas']} notificações criadas"
        )
        
        return estatisticas
    
    def limpar_noticias_antigas(self, dias_retencao: int = 90) -> int:
        """
        Remove notícias mais antigas que X dias.
        
        Args:
            dias_retencao: Número de dias para manter histórico (padrão: 90)
            
        Returns:
            Número de notícias removidas
        """
        try:
            from db_manager import get_db_connection
            from datetime import timedelta
            
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
            return removidas
        except Exception as e:
            logger.error(f"❌ Erro ao limpar notícias antigas: {e}", exc_info=True)
            return 0
