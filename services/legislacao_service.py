"""
Serviço para gerenciamento de legislação (IN, Lei, Decreto, Portaria, etc.).

Responsabilidades:
- Importação de atos normativos (por URL ou texto)
- Parsing de artigos, parágrafos, incisos e alíneas
- Consulta de legislação e trechos
- Preservação de hierarquia e contexto
"""
import re
import json
import logging
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Imports condicionais para dependências opcionais
try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

try:
    import PyPDF2
    from io import BytesIO
except ImportError:
    PyPDF2 = None
    BytesIO = None

from db_manager import get_db_connection

# Importar AIService para buscar URL com IA
try:
    from ai_service import get_ai_service
    AI_SERVICE_AVAILABLE = True
except ImportError:
    AI_SERVICE_AVAILABLE = False
    get_ai_service = None

logger = logging.getLogger(__name__)

# ✅ NOVO: Domínios que usam SPA/carregamento dinâmico e não devem ser tentados via scraping
# Para esses domínios, o sistema orienta o usuário a usar importação manual (copiar/colar)
DOMINIOS_SOMENTE_COPIA_COLA = {
    "normasinternet2.receita.fazenda.gov.br",
    # Adicionar outros domínios problemáticos aqui conforme necessário
}

# Avisos sobre dependências opcionais
if not requests:
    logger.warning("[LEGISLACAO] Biblioteca 'requests' não instalada. Funcionalidade de importação por URL não disponível.")
if not BeautifulSoup:
    logger.warning("[LEGISLACAO] Biblioteca 'beautifulsoup4' não instalada. Funcionalidade de extração HTML não disponível.")
if not PyPDF2:
    logger.warning("[LEGISLACAO] Biblioteca 'PyPDF2' não instalada. Funcionalidade de extração PDF não disponível.")


class LegislacaoService:
    """Serviço para gerenciamento de legislação."""
    
    def __init__(self):
        """Inicializa o serviço de legislação."""
        pass
    
    def _extrair_dominio_da_url(self, url: str) -> Optional[str]:
        """
        Extrai o domínio de uma URL.
        
        Args:
            url: URL completa
            
        Returns:
            Domínio extraído ou None se não conseguir
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            dominio = parsed.netloc.lower()
            # Remover porta se houver
            if ':' in dominio:
                dominio = dominio.split(':')[0]
            return dominio
        except Exception as e:
            logger.warning(f"[LEGISLACAO] Erro ao extrair domínio de {url}: {e}")
            return None
    
    def buscar_legislacao_preview(
        self,
        tipo_ato: str,
        numero: str,
        ano: int,
        sigla_orgao: Optional[str] = None,
        titulo_oficial: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca uma legislação na internet e retorna preview sem salvar.
        
        Processo:
        1. Busca URL oficial usando IA
        2. Baixa e extrai conteúdo
        3. Parseia em trechos
        4. Retorna preview (NÃO salva no banco)
        
        Args:
            tipo_ato: Tipo do ato ('IN', 'Lei', 'Decreto', etc.)
            numero: Número do ato
            ano: Ano do ato
            sigla_orgao: Sigla do órgão (opcional)
            titulo_oficial: Título oficial (opcional)
            
        Returns:
            Dict com preview ou erro
        """
        try:
            # 1. Buscar URL com IA
            url_encontrada = self.buscar_url_com_ia(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao or ''
            )
            
            if not url_encontrada:
                return {
                    'sucesso': False,
                    'erro': 'URL_NAO_ENCONTRADA',
                    'mensagem': f'Não foi possível encontrar a URL oficial da {tipo_ato} {numero}/{ano} automaticamente usando IA.',
                    'detalhes': {
                        'tipo_ato': tipo_ato,
                        'numero': numero,
                        'ano': ano,
                        'sigla_orgao': sigla_orgao
                    }
                }
            
            # 2. Tentar importar em modo preview
            resultado = self.importar_ato_por_url(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao or '',
                url=url_encontrada,
                titulo_oficial=titulo_oficial,
                modo_preview=True
            )
            
            if resultado.get('sucesso') and resultado.get('modo_preview'):
                preview = resultado.get('preview', {})
                preview['url'] = url_encontrada
                resultado['preview'] = preview
                return resultado
            else:
                return resultado
                
        except Exception as e:
            logger.error(f"[LEGISLACAO] Erro ao buscar preview: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'Erro ao buscar legislação: {str(e)}'
            }
    
    def buscar_url_com_ia(
        self,
        tipo_ato: str,
        numero: str,
        ano: int,
        sigla_orgao: str
    ) -> Optional[str]:
        """
        Usa IA para buscar a URL oficial da legislação.
        
        Args:
            tipo_ato: Tipo do ato ('IN', 'Lei', 'Decreto', 'Portaria', etc.)
            numero: Número do ato ('680', '12345', etc.)
            ano: Ano do ato (2006, 2024, etc.)
            sigla_orgao: Sigla do órgão ('RFB', 'MF', 'MDIC', etc.)
            
        Returns:
            URL encontrada ou None se não conseguir encontrar
        """
        if not AI_SERVICE_AVAILABLE:
            logger.warning("[LEGISLACAO] AIService não disponível. Não é possível buscar URL com IA.")
            return None
        
        try:
            ai_service = get_ai_service()
            if not ai_service or not ai_service.enabled:
                logger.warning("[LEGISLACAO] AIService não habilitado. Não é possível buscar URL com IA.")
                return None
            
            # Montar prompt para a IA
            # ✅ MELHORADO: Prompt mais específico para INs da RFB
            prompt = f"""Você precisa encontrar a URL oficial da seguinte legislação brasileira:

- Tipo: {tipo_ato}
- Número: {numero}
- Ano: {ano}
- Órgão: {sigla_orgao}

Por favor, forneça APENAS a URL oficial onde essa legislação pode ser encontrada.

SITES OFICIAIS COMUNS:
- INs da RFB: normasinternet2.receita.fazenda.gov.br (mas essa é SPA - prefira outras fontes)
- INs da RFB: www.gov.br/receitafederal/legislacao/
- Decretos: www.planalto.gov.br/ccivil_03/_ato...
- Leis: www.planalto.gov.br/ccivil_03/_ato...
- DOU: www.in.gov.br/web/dou

Para INs da RFB (Receita Federal):
- Tente primeiro: www.gov.br/receitafederal/legislacao/in-rfb-{numero}-{ano}
- Ou: www.gov.br/receitafederal/pt-br/legislacao/in-rfb-{numero}-{ano}
- Ou: www.receita.fazenda.gov.br/legislacao/in/{ano}/in{numero}.htm

Se você não tiver certeza da URL exata, retorne APENAS a palavra "NAO_ENCONTREI" (sem aspas, sem espaços).

Formato da resposta esperada:
- Se encontrar: apenas a URL (ex: https://www.gov.br/receitafederal/...)
- Se não encontrar: apenas "NAO_ENCONTREI"

IMPORTANTE: Retorne APENAS a URL ou "NAO_ENCONTREI", sem explicações, sem markdown, sem aspas."""
            
            system_prompt = """Você é um assistente especializado em encontrar URLs de legislação brasileira.
Você conhece os sites oficiais do governo brasileiro e sabe como formatar URLs de legislação.

Para INs da RFB, você conhece os padrões de URL comuns:
- www.gov.br/receitafederal/legislacao/in-rfb-[numero]-[ano]
- www.receita.fazenda.gov.br/legislacao/in/[ano]/in[numero].htm

Sua resposta deve ser APENAS a URL ou "NAO_ENCONTREI", sem nenhum texto adicional."""
            
            logger.info(f"[LEGISLACAO] Buscando URL com IA para {tipo_ato} {numero}/{ano} ({sigla_orgao})...")
            
            resposta = ai_service._call_llm_api(
                prompt=prompt,
                system_prompt=system_prompt,
                model=None,  # Usar modelo padrão
                temperature=0.3  # Baixa temperatura para resposta mais precisa
            )
            
            if not resposta:
                logger.warning("[LEGISLACAO] IA não retornou resposta.")
                return None
            
            # Extrair URL da resposta
            url_encontrada = None
            content = None
            
            # A resposta pode vir em diferentes formatos dependendo do provider
            if isinstance(resposta, dict):
                # OpenAI pode retornar: {'content': '...'} ou {'text': '...'}
                # Anthropic pode retornar: {'content': [{'type': 'text', 'text': '...'}]}
                if 'content' in resposta:
                    content_value = resposta['content']
                    if isinstance(content_value, list) and len(content_value) > 0:
                        # Anthropic retorna lista de blocos
                        content = content_value[0].get('text', '') if isinstance(content_value[0], dict) else str(content_value[0])
                    else:
                        content = str(content_value)
                elif 'text' in resposta:
                    content = str(resposta['text'])
                else:
                    # Tentar pegar qualquer string no dict
                    for key, value in resposta.items():
                        if isinstance(value, str) and value.strip():
                            content = value
                            break
                    if not content:
                        content = str(resposta)
            elif isinstance(resposta, str):
                content = resposta
            else:
                content = str(resposta)
            
            # Limpar a resposta
            content = content.strip()
            
            # Verificar se encontrou
            if content.upper() == "NAO_ENCONTREI" or "não encontrei" in content.lower() or "não sei" in content.lower():
                logger.info("[LEGISLACAO] IA não conseguiu encontrar a URL.")
                return None
            
            # Tentar extrair URL
            # Procurar por padrões de URL
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            matches = re.findall(url_pattern, content)
            
            if matches:
                url_encontrada = matches[0].rstrip('.,;:!?)')
                # Verificar se é URL de site oficial
                if any(dominio in url_encontrada.lower() for dominio in ['gov.br', 'in.gov.br', 'receitafederal', 'planalto.gov.br']):
                    logger.info(f"[LEGISLACAO] ✅ URL encontrada pela IA: {url_encontrada}")
                    return url_encontrada
                else:
                    logger.warning(f"[LEGISLACAO] URL encontrada não parece ser de site oficial: {url_encontrada}")
                    return None
            else:
                # Se não encontrou padrão de URL, verificar se a resposta inteira é uma URL
                if content.startswith('http://') or content.startswith('https://'):
                    url_encontrada = content.rstrip('.,;:!?)')
                    if any(dominio in url_encontrada.lower() for dominio in ['gov.br', 'in.gov.br', 'receitafederal', 'planalto.gov.br']):
                        logger.info(f"[LEGISLACAO] ✅ URL encontrada pela IA: {url_encontrada}")
                        return url_encontrada
                
                logger.warning(f"[LEGISLACAO] Não foi possível extrair URL válida da resposta da IA: {content[:100]}")
                return None
                
        except Exception as e:
            logger.error(f"[LEGISLACAO] Erro ao buscar URL com IA: {e}", exc_info=True)
            return None
    
    def importar_ato_por_url(
        self,
        tipo_ato: str,
        numero: str,
        ano: int,
        sigla_orgao: str,
        url: str,
        titulo_oficial: Optional[str] = None,
        modo_preview: bool = False
    ) -> Dict[str, Any]:
        """
        Importa um ato normativo a partir de uma URL.
        
        ✅ MELHORADO: Agora usa headers de navegador, múltiplas estratégias de extração
        e melhor detecção de conteúdo principal.
        
        Args:
            tipo_ato: Tipo do ato ('IN', 'Lei', 'Decreto', 'Portaria', etc.)
            numero: Número do ato ('680', '12345', etc.)
            ano: Ano do ato (2006, 2024, etc.)
            sigla_orgao: Sigla do órgão ('RFB', 'MF', 'MDIC', etc.)
            url: URL oficial de onde baixar o ato
            titulo_oficial: Título ou ementa do ato (opcional)
            
        Returns:
            Dict com resultado da importação:
            - sucesso: bool
            - legislacao_id: int (ID do ato importado)
            - trechos_importados: int (quantidade de trechos)
            - erro: str (se houver erro)
        """
        try:
            logger.info(f"[LEGISLACAO] Iniciando importação de {tipo_ato} {numero}/{ano} ({sigla_orgao}) de {url}")
            
            # ✅ NOVO: 1. Verificar se o domínio está na lista de "somente copiar/colar"
            dominio = self._extrair_dominio_da_url(url)
            if dominio and dominio in DOMINIOS_SOMENTE_COPIA_COLA:
                logger.warning(f"[LEGISLACAO] Domínio {dominio} está na lista de sites que requerem copiar/colar")
                return {
                    'sucesso': False,
                    'erro': 'SITE_SOMENTE_COPIA_COLA',
                    'mensagem': (
                        "Este site usa carregamento dinâmico (SPA) e o texto da legislação "
                        "não pode ser extraído diretamente pela URL. "
                        "Use a importação manual: copie o texto da página oficial e importe "
                        "via importar_ato_de_texto."
                    ),
                    'detalhes': {
                        'dominio': dominio,
                        'url': url,
                    }
                }
            
            # 2. Baixar conteúdo da URL
            if not requests:
                return {
                    'sucesso': False,
                    'erro': 'Biblioteca "requests" não instalada. Execute: pip install requests',
                    'mensagem': 'Biblioteca "requests" não está instalada. Execute: pip install requests'
                }
            
            # ✅ MELHORIA: Headers de navegador realista para evitar bloqueios
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            logger.info(f"[LEGISLACAO] Fazendo requisição para {url}...")
            response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
            response.raise_for_status()
            
            logger.info(f"[LEGISLACAO] ✅ Conteúdo baixado: {len(response.content)} bytes, Content-Type: {response.headers.get('Content-Type', 'desconhecido')}")
            
            # 2. Detectar tipo de conteúdo (HTML ou PDF)
            content_type = response.headers.get('Content-Type', '').lower()
            texto_bruto = None
            
            # ✅ MELHORIA: Detecção mais robusta de PDF
            is_pdf = (
                'pdf' in content_type or 
                url.lower().endswith('.pdf') or
                response.content[:4] == b'%PDF'  # Verificar magic bytes
            )
            
            if is_pdf:
                # Extrair texto de PDF
                if not PyPDF2:
                    return {
                        'sucesso': False,
                        'erro': 'Biblioteca "PyPDF2" não instalada. Execute: pip install PyPDF2'
                    }
                logger.info("[LEGISLACAO] Detectado PDF, extraindo texto...")
                texto_bruto = self._extrair_texto_pdf(response.content)
            else:
                # Extrair texto de HTML
                if not BeautifulSoup:
                    return {
                        'sucesso': False,
                        'erro': 'Biblioteca "beautifulsoup4" não instalada. Execute: pip install beautifulsoup4'
                    }
                logger.info("[LEGISLACAO] Detectado HTML, extraindo texto...")
                texto_bruto = self._extrair_texto_html(response.content, url=url)
            
            if not texto_bruto or not texto_bruto.strip():
                return {
                    'sucesso': False,
                    'erro': 'CONTEUDO_INSUFICIENTE_URL',
                    'mensagem': (
                        "Não foi possível extrair o texto completo da legislação a partir da URL. "
                        "Use a importação manual: copie o texto da página oficial e importe via "
                        "importar_ato_de_texto."
                    ),
                    'detalhes': {
                        'url': url,
                        'tamanho_texto': 0,
                    }
                }
            
            # ✅ NOVO: Validar se extraiu conteúdo suficiente (pelo menos 500 caracteres)
            texto_limpo = texto_bruto.strip()
            tamanho_texto = len(texto_limpo)
            
            if tamanho_texto < 500:
                logger.warning(f"[LEGISLACAO] ⚠️ Texto extraído muito curto ({tamanho_texto} caracteres). Provavelmente é SPA vazio.")
                return {
                    'sucesso': False,
                    'erro': 'CONTEUDO_INSUFICIENTE_URL',
                    'mensagem': (
                        "Não foi possível extrair o texto completo da legislação a partir da URL. "
                        "O conteúdo extraído é muito curto, indicando que o site usa carregamento dinâmico. "
                        "Use a importação manual: copie o texto da página oficial e importe via "
                        "importar_ato_de_texto."
                    ),
                    'detalhes': {
                        'url': url,
                        'tamanho_texto': tamanho_texto,
                    }
                }
            
            # ✅ NOVO: Verificar se tem artigos (validação obrigatória)
            tem_artigos = bool(re.search(r'Art\.\s*\d+', texto_limpo, re.IGNORECASE))
            if not tem_artigos:
                logger.warning("[LEGISLACAO] ⚠️ Texto extraído não contém artigos de legislação. Provavelmente é SPA vazio.")
                return {
                    'sucesso': False,
                    'erro': 'CONTEUDO_INSUFICIENTE_URL',
                    'mensagem': (
                        "Não foi possível extrair o texto completo da legislação a partir da URL. "
                        "O conteúdo extraído não contém artigos, indicando que o site usa carregamento dinâmico. "
                        "Use a importação manual: copie o texto da página oficial e importe via "
                        "importar_ato_de_texto."
                    ),
                    'detalhes': {
                        'url': url,
                        'tamanho_texto': tamanho_texto,
                        'tem_artigos': False,
                    }
                }
            
            logger.info(f"[LEGISLACAO] ✅ Texto extraído: {tamanho_texto} caracteres, contém artigos: {tem_artigos}")
            
            # 3. Importar usando o texto extraído
            return self.importar_ato_de_texto(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao,
                texto_bruto=texto_bruto,
                titulo_oficial=titulo_oficial,
                fonte_url=url,
                modo_preview=modo_preview
            )
            
        except requests.exceptions.Timeout:
            logger.error(f"[LEGISLACAO] ⏱️ Timeout ao baixar conteúdo de {url}")
            return {
                'sucesso': False,
                'erro': 'TIMEOUT',
                'mensagem': 'Timeout ao baixar conteúdo. O site pode estar lento ou indisponível.',
                'detalhes': {
                    'url': url,
                }
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"[LEGISLACAO] ❌ Erro HTTP {e.response.status_code} ao baixar conteúdo de {url}")
            return {
                'sucesso': False,
                'erro': f'HTTP_ERROR_{e.response.status_code}',
                'mensagem': f'Erro HTTP {e.response.status_code} ao acessar a URL.',
                'detalhes': {
                    'url': url,
                    'status_code': e.response.status_code,
                }
            }
        except requests.RequestException as e:
            logger.error(f"[LEGISLACAO] ❌ Erro de rede ao baixar conteúdo de {url}: {e}")
            return {
                'sucesso': False,
                'erro': 'ERRO_REDE',
                'mensagem': f'Erro de rede ao acessar a URL: {str(e)}',
                'detalhes': {
                    'url': url,
                }
            }
        except Exception as e:
            logger.error(f"[LEGISLACAO] ❌ Erro inesperado ao importar ato por URL: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INESPERADO',
                'mensagem': f'Erro inesperado ao processar a URL: {str(e)}',
                'detalhes': {
                    'url': url,
                }
            }
    
    def importar_ato_de_texto(
        self,
        tipo_ato: str,
        numero: str,
        ano: int,
        sigla_orgao: str,
        texto_bruto: str,
        titulo_oficial: Optional[str] = None,
        fonte_url: Optional[str] = None,
        modo_preview: bool = False
    ) -> Dict[str, Any]:
        """
        Importa um ato normativo a partir de texto bruto.
        
        Args:
            tipo_ato: Tipo do ato ('IN', 'Lei', 'Decreto', 'Portaria', etc.)
            numero: Número do ato ('680', '12345', etc.)
            ano: Ano do ato (2006, 2024, etc.)
            sigla_orgao: Sigla do órgão ('RFB', 'MF', 'MDIC', etc.)
            texto_bruto: Texto completo do ato
            titulo_oficial: Título ou ementa do ato (opcional)
            fonte_url: URL de origem (opcional)
            modo_preview: Se True, não salva no banco, apenas retorna preview
            
        Returns:
            Dict com resultado da importação:
            - sucesso: bool
            - legislacao_id: int (ID do ato importado, None se preview)
            - trechos_importados: int (quantidade de trechos)
            - preview: dict (se modo_preview=True, contém dados do preview)
            - erro: str (se houver erro)
        """
        try:
            # 3. Parsear texto em trechos (sempre fazemos isso)
            trechos = self._parsear_texto_legislacao(texto_bruto)
            trechos_importados = len(trechos)
            
            # Se modo preview, retornar apenas os dados sem salvar
            if modo_preview:
                # Pegar amostra dos primeiros trechos
                amostra_trechos = trechos[:5] if len(trechos) > 5 else trechos
                
                # Pegar primeiro artigo completo como exemplo
                primeiro_artigo = None
                for trecho in trechos:
                    if trecho.get('tipo_trecho') == 'caput':
                        primeiro_artigo = trecho
                        break
                
                preview = {
                    'tipo_ato': tipo_ato,
                    'numero': numero,
                    'ano': ano,
                    'sigla_orgao': sigla_orgao,
                    'titulo_oficial': titulo_oficial,
                    'fonte_url': fonte_url,
                    'total_trechos': trechos_importados,
                    'total_artigos': len(set(t.get('numero_artigo') for t in trechos if t.get('numero_artigo'))),
                    'primeiro_artigo': primeiro_artigo,
                    'amostra_trechos': amostra_trechos,
                    'texto_preview': texto_bruto[:500] + ('...' if len(texto_bruto) > 500 else '')
                }
                
                logger.info(f"[LEGISLACAO] Preview gerado: {trechos_importados} trechos, {preview['total_artigos']} artigos")
                
                return {
                    'sucesso': True,
                    'legislacao_id': None,
                    'trechos_importados': trechos_importados,
                    'preview': preview,
                    'modo_preview': True
                }
            
            # Modo normal: salvar no banco
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 1. Verificar se já existe
            cursor.execute('''
                SELECT id FROM legislacao
                WHERE tipo_ato = ? AND numero = ? AND ano = ? AND sigla_orgao = ?
            ''', (tipo_ato, numero, ano, sigla_orgao))
            
            existing = cursor.fetchone()
            if existing:
                legislacao_id = existing[0]
                logger.info(f"[LEGISLACAO] Ato {tipo_ato} {numero}/{ano} já existe (ID: {legislacao_id}). Atualizando...")
                
                # Atualizar dados existentes
                cursor.execute('''
                    UPDATE legislacao
                    SET titulo_oficial = COALESCE(?, titulo_oficial),
                        fonte_url = COALESCE(?, fonte_url),
                        texto_integral = ?,
                        data_importacao = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (titulo_oficial, fonte_url, texto_bruto, legislacao_id))
                
                # Remover trechos antigos
                cursor.execute('DELETE FROM legislacao_trecho WHERE legislacao_id = ?', (legislacao_id,))
            else:
                # 2. Inserir na tabela legislacao
                cursor.execute('''
                    INSERT INTO legislacao (tipo_ato, numero, ano, sigla_orgao, titulo_oficial, fonte_url, texto_integral, em_vigor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ''', (tipo_ato, numero, ano, sigla_orgao, titulo_oficial, fonte_url, texto_bruto))
                
                legislacao_id = cursor.lastrowid
                logger.info(f"[LEGISLACAO] Ato {tipo_ato} {numero}/{ano} criado (ID: {legislacao_id})")
            
            # 4. Inserir trechos na tabela legislacao_trecho
            for ordem, trecho in enumerate(trechos, start=1):
                cursor.execute('''
                    INSERT INTO legislacao_trecho (
                        legislacao_id, referencia, tipo_trecho, texto, texto_com_artigo,
                        ordem, numero_artigo, hierarquia_json, revogado
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    legislacao_id,
                    trecho['referencia'],
                    trecho['tipo_trecho'],
                    trecho['texto'],
                    trecho['texto_com_artigo'],
                    ordem,
                    trecho.get('numero_artigo'),
                    json.dumps(trecho.get('hierarquia', {})),
                    trecho.get('revogado', False)
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"[LEGISLACAO] Importação concluída: {trechos_importados} trechos importados")
            
            return {
                'sucesso': True,
                'legislacao_id': legislacao_id,
                'trechos_importados': trechos_importados
            }
            
        except Exception as e:
            logger.error(f"[LEGISLACAO] Erro ao importar ato de texto: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': f'Erro ao importar: {str(e)}'
            }
    
    def buscar_ato(
        self,
        tipo_ato: str,
        numero: str,
        ano: Optional[int] = None,
        sigla_orgao: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca um ato normativo.
        
        Args:
            tipo_ato: Tipo do ato ('IN', 'Lei', 'Decreto', etc.)
            numero: Número do ato
            ano: Ano do ato (opcional)
            sigla_orgao: Sigla do órgão (opcional)
            
        Returns:
            Dict com dados do ato ou None se não encontrado
        """
        try:
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT * FROM legislacao WHERE tipo_ato = ? AND numero = ?'
            params = [tipo_ato, numero]
            
            if ano is not None:
                query += ' AND ano = ?'
                params.append(ano)
            
            if sigla_orgao:
                query += ' AND sigla_orgao = ?'
                params.append(sigla_orgao)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"[LEGISLACAO] Erro ao buscar ato: {e}", exc_info=True)
            return None
    
    def buscar_trechos_por_palavra_chave(
        self,
        tipo_ato: str,
        numero: str,
        termos: List[str],
        ano: Optional[int] = None,
        sigla_orgao: Optional[str] = None,
        limit: int = 10,
        incluir_revogados: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Busca trechos de um ato por palavras-chave.
        
        Args:
            tipo_ato: Tipo do ato ('IN', 'Lei', 'Decreto', etc.)
            numero: Número do ato
            termos: Lista de termos para buscar
            ano: Ano do ato (opcional)
            sigla_orgao: Sigla do órgão (opcional)
            limit: Limite de resultados (padrão: 10)
            
        Returns:
            Lista de dicts com trechos encontrados
        """
        try:
            # 1. Buscar ID do ato
            ato = self.buscar_ato(tipo_ato, numero, ano, sigla_orgao)
            if not ato:
                return []
            
            legislacao_id = ato['id']
            
            # 2. Construir query de busca
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # ✅ MELHORADO: Expandir termos (plural/singular, variações)
            termos_expandidos = self._expandir_termos_busca(termos)
            
            # ✅ MELHORADO: Buscar case-insensitive usando LOWER() para garantir que funciona
            # Buscar em texto, texto_com_artigo E referencia (para encontrar títulos/capítulos)
            conditions = []
            params = [legislacao_id]
            
            for termo in termos_expandidos:
                # Normalizar termo para minúsculas para busca case-insensitive
                termo_lower = termo.lower()
                # ✅ NOVO: Buscar também em referencia (onde podem estar títulos como "TÍTULO III - DAS MULTAS")
                conditions.append('(LOWER(texto) LIKE ? OR LOWER(texto_com_artigo) LIKE ? OR LOWER(referencia) LIKE ?)')
                params.extend([f'%{termo_lower}%', f'%{termo_lower}%', f'%{termo_lower}%'])
            
            # ✅ NOVO: Filtrar revogados se não quiser incluí-los
            filtro_revogado = ''
            if not incluir_revogados:
                filtro_revogado = 'AND revogado = 0'
            
            # ✅ MELHORADO: Ordenar por relevância (títulos/capítulos primeiro, depois artigos)
            # Títulos que contêm o termo têm prioridade
            # ✅ CORREÇÃO: Parâmetros devem estar na ordem correta conforme a query SQL
            # Na query, o CASE vem ANTES do WHERE, então os parâmetros do CASE vêm primeiro
            # Ordem: CASE (3 params) -> WHERE (legislacao_id + conditions) -> LIMIT
            primeiro_termo = termos[0].lower() if termos else ''
            # ✅ CORREÇÃO: O CASE precisa de 7 parâmetros (termo usado várias vezes)
            params_ordenacao = [
                f'%{primeiro_termo}%',  # Prioridade 1: referencia
                f'%{primeiro_termo}%',  # Prioridade 2: aplicam-se
                f'%{primeiro_termo}%',  # Prioridade 3: título/capítulo com termo (primeira verificação)
                f'%{primeiro_termo}%',  # Prioridade 3: título com termo
                f'%{primeiro_termo}%',  # Prioridade 3: capítulo com termo
                f'%{primeiro_termo}%',  # Prioridade 3: seção com termo
                f'%{primeiro_termo}%',  # Prioridade 4: título/capítulo sem termo
                f'%{primeiro_termo}%',  # Prioridade 5: início do texto
            ]
            
            query = f'''
                SELECT referencia, tipo_trecho, texto, texto_com_artigo, ordem, numero_artigo, revogado,
                       CASE 
                           -- Prioridade 1: Termo na referência (títulos/capítulos)
                           WHEN LOWER(referencia) LIKE ? THEN 1
                           -- Prioridade 2: Texto começa com "Aplicam-se" + termo (indica que é SOBRE o assunto)
                           WHEN LOWER(texto) LIKE ? AND LOWER(SUBSTR(texto, 1, 50)) LIKE '%aplicam-se%' THEN 2
                           -- Prioridade 3: Texto contém termo E tem título/capítulo com o termo no contexto (ex: "TÍTULO III - DAS MULTAS")
                           WHEN LOWER(texto) LIKE ? AND (
                               (LOWER(texto) LIKE '%título%' AND LOWER(texto) LIKE ?) OR 
                               (LOWER(texto) LIKE '%capítulo%' AND LOWER(texto) LIKE ?) OR
                               (LOWER(texto) LIKE '%seção%' AND LOWER(texto) LIKE ?)
                           ) THEN 3
                           -- Prioridade 4: Texto contém termo E tem título/capítulo no contexto (sem o termo no título)
                           WHEN LOWER(texto) LIKE ? AND (
                               LOWER(texto) LIKE '%título%' OR 
                               LOWER(texto) LIKE '%capítulo%' OR
                               LOWER(texto) LIKE '%seção%'
                           ) THEN 4
                           -- Prioridade 5: Termo aparece no início do texto (primeiros 200 chars) - mais relevante
                           WHEN LOWER(texto) LIKE ? AND LENGTH(texto) > 0 THEN 5
                           -- Prioridade 6: Termo aparece no meio/fim do texto - menos relevante
                           ELSE 6
                       END as relevancia
                FROM legislacao_trecho
                WHERE legislacao_id = ? AND ({' OR '.join(conditions)}) {filtro_revogado}
                ORDER BY relevancia, ordem
                LIMIT ?
            '''
            # Montar parâmetros na ordem correta: CASE primeiro, depois WHERE, depois LIMIT
            params_final = params_ordenacao + params + [limit]
            
            cursor.execute(query, params_final)
            rows = cursor.fetchall()
            conn.close()
            
            # ✅ NOVO: Remover campo 'relevancia' do resultado (é apenas para ordenação)
            resultado = []
            for row in rows:
                trecho_dict = dict(row)
                if 'relevancia' in trecho_dict:
                    del trecho_dict['relevancia']
                resultado.append(trecho_dict)
            
            return resultado
            
        except Exception as e:
            logger.error(f"[LEGISLACAO] Erro ao buscar trechos por palavra-chave: {e}", exc_info=True)
            return []
    
    def buscar_artigo_completo(
        self,
        tipo_ato: str,
        numero: str,
        numero_artigo: int,
        ano: Optional[int] = None,
        sigla_orgao: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca um artigo completo com todos os seus trechos (caput, parágrafos, incisos, alíneas).
        
        Args:
            tipo_ato: Tipo do ato ('IN', 'Lei', 'Decreto', etc.)
            numero: Número do ato
            numero_artigo: Número do artigo a buscar
            ano: Ano do ato (opcional)
            sigla_orgao: Sigla do órgão (opcional)
            
        Returns:
            Dict com:
            - sucesso: bool
            - artigo: dict com referencia, caput, paragrafos, etc.
            - erro: str (se houver)
        """
        try:
            # 1. Buscar ID do ato
            ato = self.buscar_ato(tipo_ato, numero, ano, sigla_orgao)
            if not ato:
                return {
                    'sucesso': False,
                    'erro': f'Ato {tipo_ato} {numero}{f"/{ano}" if ano else ""} não encontrado'
                }
            
            legislacao_id = ato['id']
            
            # 2. Primeiro, tentar buscar do texto integral (mais completo)
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Buscar texto integral
            cursor.execute('SELECT texto_integral FROM legislacao WHERE id = ?', (legislacao_id,))
            row_texto = cursor.fetchone()
            texto_integral = row_texto[0] if row_texto else None
            
            artigo_completo_texto = None
            if texto_integral:
                # Extrair artigo completo do texto integral usando regex
                import re
                # Padrão para encontrar o artigo (ex: "Art. 702" até o próximo "Art. 703" ou fim)
                # Usar lookahead negativo para garantir que não pare em "Art." dentro do próprio artigo
                # Buscar até encontrar "Art. " seguido de número maior que o atual
                padrao = re.compile(
                    rf'Art\.\s*{numero_artigo}[º°]?\s*(.*?)(?=Art\.\s*(?:{numero_artigo + 1}|\d{{3,}})[º°]?|$)',
                    re.IGNORECASE | re.DOTALL
                )
                match = padrao.search(texto_integral)
                if match:
                    artigo_completo_texto = match.group(1).strip()
                    # Se o texto está muito curto, pode ter parado cedo demais - tentar padrão mais amplo
                    if len(artigo_completo_texto) < 500:
                        # Tentar padrão alternativo: até próximo "Art. " seguido de número
                        padrao_alt = re.compile(
                            rf'Art\.\s*{numero_artigo}[º°]?\s*(.*?)(?=Art\.\s+\d+[º°]?\s|$)',
                            re.IGNORECASE | re.DOTALL
                        )
                        match_alt = padrao_alt.search(texto_integral)
                        if match_alt and len(match_alt.group(1).strip()) > len(artigo_completo_texto):
                            artigo_completo_texto = match_alt.group(1).strip()
            
            # 3. Buscar todos os trechos parseados do artigo (para ter estrutura)
            conn.row_factory = sqlite3.Row
            cursor.execute('''
                SELECT referencia, tipo_trecho, texto, texto_com_artigo, ordem, numero_artigo, revogado
                FROM legislacao_trecho
                WHERE legislacao_id = ? AND numero_artigo = ?
                ORDER BY ordem
            ''', (legislacao_id, numero_artigo))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Se temos texto completo do texto integral, usar ele
            if artigo_completo_texto:
                return {
                    'sucesso': True,
                    'artigo': {
                        'referencia': f'Art. {numero_artigo}º',
                        'numero_artigo': numero_artigo,
                        'texto_completo': artigo_completo_texto,
                        'fonte': 'texto_integral'
                    }
                }
            
            if not rows:
                return {
                    'sucesso': False,
                    'erro': f'Artigo {numero_artigo} não encontrado na {tipo_ato} {numero}{f"/{ano}" if ano else ""}'
                }
            
            # 3. Organizar trechos - usar texto_com_artigo quando disponível para ter contexto completo
            artigo = {
                'referencia': f'Art. {numero_artigo}º',
                'numero_artigo': numero_artigo,
                'caput': None,
                'paragrafos': [],
                'incisos': [],
                'alineas': [],
                'revogado': False,
                'texto_completo': None  # Para ter o artigo completo em um só lugar
            }
            
            # Primeiro, tentar encontrar o caput completo (pode estar em texto_com_artigo)
            caput_completo = None
            for row in rows:
                trecho = dict(row)
                tipo = trecho.get('tipo_trecho', '')
                referencia = trecho.get('referencia', '')
                texto = trecho.get('texto', '')
                texto_com_artigo = trecho.get('texto_com_artigo', '')
                
                if tipo == 'caput' or referencia == f'Art. {numero_artigo}º':
                    # Usar texto_com_artigo se tiver mais conteúdo, senão usar texto
                    if texto_com_artigo and len(texto_com_artigo) > len(texto):
                        caput_completo = texto_com_artigo
                        artigo['caput'] = texto  # Caput isolado
                    else:
                        caput_completo = texto
                        artigo['caput'] = texto
                    artigo['revogado'] = trecho.get('revogado', False)
                    break
            
            # Se não encontrou caput, usar o primeiro trecho
            if not caput_completo and rows:
                primeiro = dict(rows[0])
                caput_completo = primeiro.get('texto_com_artigo') or primeiro.get('texto', '')
                artigo['caput'] = primeiro.get('texto', '')
            
            # Agrupar todos os trechos do artigo
            for row in rows:
                trecho = dict(row)
                tipo = trecho.get('tipo_trecho', '')
                referencia = trecho.get('referencia', '')
                texto = trecho.get('texto', '')
                texto_com_artigo = trecho.get('texto_com_artigo', '')
                
                # Usar texto_com_artigo se tiver mais conteúdo
                texto_final = texto_com_artigo if texto_com_artigo and len(texto_com_artigo) > len(texto) else texto
                
                if tipo == 'paragrafo' or '§' in referencia:
                    artigo['paragrafos'].append({
                        'referencia': referencia,
                        'texto': texto_final,
                        'revogado': trecho.get('revogado', False)
                    })
                elif tipo == 'inciso' or ('I -' in texto[:10] and 'I -' not in str(caput_completo or '')[:500]):
                    artigo['incisos'].append({
                        'referencia': referencia,
                        'texto': texto_final,
                        'revogado': trecho.get('revogado', False)
                    })
                elif tipo == 'alinea' or ('a)' in texto[:10] and 'a)' not in str(caput_completo or '')[:500]):
                    artigo['alineas'].append({
                        'referencia': referencia,
                        'texto': texto_final,
                        'revogado': trecho.get('revogado', False)
                    })
            
            # Se o caput completo contém incisos/alíneas, extrair de lá
            if caput_completo and ('I -' in caput_completo or 'a)' in caput_completo):
                artigo['texto_completo'] = caput_completo
            
            return {
                'sucesso': True,
                'artigo': artigo
            }
            
        except Exception as e:
            logger.error(f"[LEGISLACAO] Erro ao buscar artigo completo: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def _expandir_termos_busca(self, termos: List[str]) -> List[str]:
        """
        Expande termos de busca para incluir variações (plural/singular, conjugações, sinônimos).
        
        ✅ MELHORADO: Agora inclui sinônimos jurídicos comuns.
        
        Exemplos:
        - "multa" → ["multa", "multas", "multar", "multado", "multados", "penalidade", "penalidades", "sanção"]
        - "penalidade" → ["penalidade", "penalidades", "multa", "multas", "sanção"]
        - "artigo" → ["artigo", "artigos", "art.", "art", "dispositivo"]
        
        Args:
            termos: Lista de termos originais
            
        Returns:
            Lista expandida com variações e sinônimos
        """
        termos_expandidos = []
        
        # ✅ NOVO: Dicionário de sinônimos jurídicos
        sinonimos_juridicos = {
            'multa': ['penalidade', 'penalidades', 'sanção', 'sanções', 'sanção pecuniária'],
            'penalidade': ['multa', 'multas', 'sanção', 'sanções'],
            'sanção': ['multa', 'multas', 'penalidade', 'penalidades'],
            'artigo': ['art.', 'art', 'dispositivo', 'dispositivos', 'norma'],
            'paragrafo': ['parágrafo', 'paragrafos', 'parágrafos', '§'],
            'inciso': ['inc.', 'inc'],
            'alinea': ['alínea', 'alineas', 'alíneas'],
            'capitulo': ['capítulo', 'capitulos', 'capítulos'],
            'titulo': ['título', 'titulos', 'títulos'],
            'secao': ['seção', 'secoes', 'seções'],
        }
        
        for termo in termos:
            termo_lower = termo.lower().strip()
            termos_expandidos.append(termo_lower)  # Termo original
            
            # ✅ NOVO: Adicionar sinônimos jurídicos
            if termo_lower in sinonimos_juridicos:
                termos_expandidos.extend(sinonimos_juridicos[termo_lower])
            
            # Regras de plural/singular comuns em português
            if termo_lower.endswith('a'):
                # Singular feminino → plural
                termos_expandidos.append(termo_lower + 's')  # multa → multas
            elif termo_lower.endswith('o'):
                # Singular masculino → plural
                termos_expandidos.append(termo_lower + 's')  # artigo → artigos
            elif termo_lower.endswith('s'):
                # Plural → singular
                if len(termo_lower) > 1:
                    termos_expandidos.append(termo_lower[:-1])  # multas → multa
            
            # Variações comuns de verbos
            if termo_lower.endswith('ar'):
                # Infinitivo → particípio
                termos_expandidos.append(termo_lower[:-2] + 'ado')  # multar → multado
                termos_expandidos.append(termo_lower[:-2] + 'ados')  # multar → multados
            elif termo_lower.endswith('ado'):
                # Particípio → infinitivo
                termos_expandidos.append(termo_lower[:-2] + 'ar')  # multado → multar
            
            # Abreviações comuns
            if termo_lower == 'artigo' or termo_lower == 'art':
                termos_expandidos.extend(['art.', 'art', 'artigo', 'artigos'])
            elif termo_lower == 'paragrafo' or termo_lower == 'parágrafo':
                termos_expandidos.extend(['paragrafo', 'parágrafo', 'paragrafos', 'parágrafos', '§'])
            elif termo_lower == 'inciso':
                termos_expandidos.extend(['inciso', 'incisos', 'inc.', 'inc'])
            elif termo_lower == 'alinea' or termo_lower == 'alínea':
                termos_expandidos.extend(['alinea', 'alínea', 'alineas', 'alíneas'])
        
        # Remover duplicatas mantendo ordem
        termos_unicos = []
        for termo in termos_expandidos:
            if termo not in termos_unicos:
                termos_unicos.append(termo)
        
        return termos_unicos
    
    def buscar_em_todas_legislacoes(
        self,
        termos: List[str],
        limit: int = 20,
        incluir_revogados: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Busca trechos em TODAS as legislações do banco por palavra-chave.
        
        ✅ MELHORADO: Agora expande termos automaticamente (plural/singular, variações).
        ✅ MELHORADO: Busca direta no banco para melhor performance.
        
        Args:
            termos: Lista de termos para buscar
            limit: Limite de resultados por legislação (padrão: 20)
            incluir_revogados: Se True, inclui trechos revogados
            
        Returns:
            Lista de dicts com trechos encontrados, cada um contendo:
            - legislacao_info: dict com tipo_ato, numero, ano, sigla_orgao
            - referencia: str (ex: "Art. 5º")
            - tipo_trecho: str
            - texto: str
            - texto_com_artigo: str
            - numero_artigo: int
            - revogado: bool
        """
        try:
            # ✅ MELHORADO: Expandir termos (plural/singular, variações)
            termos_expandidos = self._expandir_termos_busca(termos)
            logger.info(f"[LEGISLACAO] Termos originais: {termos} → Expandidos: {termos_expandidos}")
            
            # 1. Buscar todas as legislações do banco
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, tipo_ato, numero, ano, sigla_orgao, titulo_oficial
                FROM legislacao
                ORDER BY tipo_ato, numero, ano
            ''')
            
            legislacoes = cursor.fetchall()
            
            if not legislacoes:
                conn.close()
                logger.info("[LEGISLACAO] Nenhuma legislação encontrada no banco")
                return []
            
            logger.info(f"[LEGISLACAO] Buscando '{', '.join(termos)}' (expandido: '{', '.join(termos_expandidos)}') em {len(legislacoes)} legislação(ões)")
            
            # ✅ MELHORADO: Busca hierárquica contextual
            # 1. Buscar trechos que contêm o termo diretamente
            # 2. Identificar títulos/capítulos/seções que contêm o termo
            # 3. Incluir TODOS os artigos abaixo desses títulos/capítulos (contexto hierárquico)
            
            todos_trechos = []
            ordens_titulos_capitulos_encontrados = {}  # {legislacao_id: [ordens dos títulos/capítulos]}
            
            # Construir condições de busca para todos os termos expandidos
            conditions = []
            params = []
            
            for termo in termos_expandidos:
                termo_lower = termo.lower()
                # Buscar em texto, texto_com_artigo E referencia
                conditions.append('(LOWER(texto) LIKE ? OR LOWER(texto_com_artigo) LIKE ? OR LOWER(referencia) LIKE ?)')
                params.extend([f'%{termo_lower}%', f'%{termo_lower}%', f'%{termo_lower}%'])
            
            # Filtro de revogados
            filtro_revogado = '' if incluir_revogados else 'AND revogado = 0'
            
            # ETAPA 1: Buscar trechos que contêm o termo diretamente
            query_direta = f'''
                SELECT 
                    lt.referencia, 
                    lt.tipo_trecho, 
                    lt.texto, 
                    lt.texto_com_artigo, 
                    lt.ordem, 
                    lt.numero_artigo, 
                    lt.revogado,
                    lt.legislacao_id,
                    l.tipo_ato,
                    l.numero,
                    l.ano,
                    l.sigla_orgao,
                    l.titulo_oficial
                FROM legislacao_trecho lt
                JOIN legislacao l ON lt.legislacao_id = l.id
                WHERE ({' OR '.join(conditions)}) {filtro_revogado}
                ORDER BY l.tipo_ato, l.numero, l.ano, lt.ordem
            '''
            
            cursor.execute(query_direta, params)
            rows_diretos = cursor.fetchall()
            
            # ETAPA 2: Identificar artigos que mencionam títulos/capítulos sobre o assunto
            # Estratégia: Artigos que mencionam "neste Título", "neste Capítulo" + o termo
            # indicam que estão dentro de um contexto hierárquico sobre o assunto
            
            artigos_em_contexto_hierarquico = {}  # {legislacao_id: [ordens]}
            
            for termo in termos_expandidos:
                termo_lower = termo.lower()
                
                # Buscar artigos que mencionam "neste Título/Capítulo" E o termo
                # Isso indica que o artigo está dentro de um título/capítulo sobre o assunto
                query_contexto = f'''
                    SELECT 
                        lt.legislacao_id,
                        lt.ordem,
                        lt.referencia,
                        lt.numero_artigo
                    FROM legislacao_trecho lt
                    JOIN legislacao l ON lt.legislacao_id = l.id
                    WHERE (
                        LOWER(lt.texto) LIKE ?  -- Contém o termo
                        AND (
                            LOWER(lt.texto) LIKE '%neste título%' OR
                            LOWER(lt.texto) LIKE '%neste capítulo%' OR
                            LOWER(lt.texto) LIKE '%neste capitulo%' OR
                            LOWER(lt.texto) LIKE '%deste título%' OR
                            LOWER(lt.texto) LIKE '%deste capítulo%' OR
                            LOWER(lt.texto) LIKE '%deste capitulo%' OR
                            LOWER(lt.texto) LIKE '%do título%' OR
                            LOWER(lt.texto) LIKE '%do capítulo%' OR
                            LOWER(lt.texto) LIKE '%do capitulo%'
                        )
                    ) {filtro_revogado}
                    ORDER BY lt.legislacao_id, lt.ordem
                '''
                
                cursor.execute(query_contexto, [f'%{termo_lower}%'])
                rows_contexto = cursor.fetchall()
                
                for row_ctx in rows_contexto:
                    leg_id = row_ctx['legislacao_id']
                    ordem = row_ctx['ordem']
                    numero_artigo = row_ctx['numero_artigo']
                    
                    if leg_id not in artigos_em_contexto_hierarquico:
                        artigos_em_contexto_hierarquico[leg_id] = []
                    
                    # Agrupar por artigo (não por ordem individual)
                    if numero_artigo and numero_artigo not in [a.get('artigo') for a in artigos_em_contexto_hierarquico[leg_id] if isinstance(a, dict)]:
                        artigos_em_contexto_hierarquico[leg_id].append({
                            'artigo': numero_artigo,
                            'ordem_inicio': ordem,
                            'referencia': row_ctx['referencia']
                        })
                        logger.info(f"[LEGISLACAO] ✅ Artigo em contexto hierárquico: {row_ctx['referencia']} (artigo {numero_artigo}, ordem: {ordem})")
            
            # Converter para formato compatível com a lógica existente
            for leg_id, artigos in artigos_em_contexto_hierarquico.items():
                if leg_id not in ordens_titulos_capitulos_encontrados:
                    ordens_titulos_capitulos_encontrados[leg_id] = []
                for artigo_info in artigos:
                    if isinstance(artigo_info, dict):
                        # Buscar todos os trechos deste artigo (caput + parágrafos)
                        cursor.execute('''
                            SELECT ordem FROM legislacao_trecho
                            WHERE legislacao_id = ? AND numero_artigo = ?
                            ORDER BY ordem
                        ''', (leg_id, artigo_info['artigo']))
                        ordens_artigo = [row[0] for row in cursor.fetchall()]
                        ordens_titulos_capitulos_encontrados[leg_id].extend(ordens_artigo)
            
            # ETAPA 3: Para cada título/capítulo encontrado, buscar TODOS os artigos abaixo dele
            artigos_contextuais = []
            
            for leg_id, ordens_titulos in ordens_titulos_capitulos_encontrados.items():
                for ordem_titulo in ordens_titulos:
                    # Buscar o próximo título/capítulo (ou fim da legislação) para delimitar o escopo
                    cursor.execute('''
                        SELECT ordem FROM legislacao_trecho
                        WHERE legislacao_id = ? 
                          AND ordem > ?
                          AND (
                              LOWER(referencia) LIKE '%título%' OR
                              LOWER(referencia) LIKE '%capítulo%' OR
                              LOWER(referencia) LIKE '%capitulo%' OR
                              LOWER(referencia) LIKE '%seção%' OR
                              LOWER(referencia) LIKE '%secao%'
                          )
                        ORDER BY ordem ASC
                        LIMIT 1
                    ''', (leg_id, ordem_titulo))
                    
                    proximo_titulo = cursor.fetchone()
                    ordem_fim = proximo_titulo[0] if proximo_titulo else 999999  # Se não tem próximo, pegar até o fim
                    
                    # Buscar TODOS os artigos entre este título e o próximo
                    cursor.execute('''
                        SELECT 
                            lt.referencia, 
                            lt.tipo_trecho, 
                            lt.texto, 
                            lt.texto_com_artigo, 
                            lt.ordem, 
                            lt.numero_artigo, 
                            lt.revogado,
                            lt.legislacao_id,
                            l.tipo_ato,
                            l.numero,
                            l.ano,
                            l.sigla_orgao,
                            l.titulo_oficial
                        FROM legislacao_trecho lt
                        JOIN legislacao l ON lt.legislacao_id = l.id
                        WHERE lt.legislacao_id = ?
                          AND lt.ordem > ?
                          AND lt.ordem < ?
                          {filtro_revogado}
                        ORDER BY lt.ordem
                    '''.format(filtro_revogado=filtro_revogado), (leg_id, ordem_titulo, ordem_fim))
                    
                    rows_contextuais = cursor.fetchall()
                    
                    for row_ctx in rows_contextuais:
                        # Marcar como contextual (não contém o termo diretamente, mas está no contexto)
                        artigos_contextuais.append({
                            'row': row_ctx,
                            'contextual': True,
                            'titulo_origem': ordem_titulo
                        })
                    
                    logger.info(f"[LEGISLACAO] ✅ Adicionados {len(rows_contextuais)} artigos contextuais do título/capítulo (ordem {ordem_titulo})")
            
            conn.close()
            
            # ETAPA 4: Combinar resultados diretos + contextuais
            # Usar set para evitar duplicatas (mesmo trecho pode aparecer em ambos)
            trechos_unicos = {}
            
            # Adicionar trechos diretos
            for row in rows_diretos:
                leg_id = row['legislacao_id']
                ordem = row['ordem']
                chave = f"{leg_id}_{ordem}"
                trechos_unicos[chave] = {
                    'row': row,
                    'contextual': False
                }
            
            # Adicionar trechos contextuais (se não estiverem já nos diretos)
            for artigo_ctx in artigos_contextuais:
                row = artigo_ctx['row']
                leg_id = row['legislacao_id']
                ordem = row['ordem']
                chave = f"{leg_id}_{ordem}"
                
                if chave not in trechos_unicos:
                    trechos_unicos[chave] = artigo_ctx
            
            # ETAPA 5: Formatar resultados
            for chave, dados in trechos_unicos.items():
                row = dados['row']
                trecho_completo = {
                    'legislacao_info': {
                        'tipo_ato': row['tipo_ato'],
                        'numero': row['numero'],
                        'ano': row['ano'],
                        'sigla_orgao': row['sigla_orgao'],
                        'titulo_oficial': row['titulo_oficial']
                    },
                    'referencia': row['referencia'],
                    'tipo_trecho': row['tipo_trecho'],
                    'texto': row['texto'],
                    'texto_com_artigo': row['texto_com_artigo'],
                    'ordem': row['ordem'],
                    'numero_artigo': row['numero_artigo'],
                    'revogado': bool(row['revogado']),
                    'contextual': dados.get('contextual', False)  # ✅ NOVO: Flag indicando se é contextual
                }
                todos_trechos.append(trecho_completo)
            
            # Ordenar por legislação e ordem, priorizando diretos sobre contextuais
            todos_trechos.sort(key=lambda x: (
                x['legislacao_info']['tipo_ato'],
                x['legislacao_info']['numero'],
                x['legislacao_info']['ano'],
                x.get('contextual', False),  # Diretos primeiro (False < True)
                x['ordem']
            ))
            
            # Aplicar limite se especificado
            # ✅ MELHORADO: Aplicar limite de forma inteligente
            # - Se há muitos contextuais, aumentar o limite para incluir alguns
            # - Priorizar diretos, mas incluir alguns contextuais relevantes
            if limit:
                # Contar diretos e contextuais
                diretos_count = sum(1 for t in todos_trechos if not t.get('contextual', False))
                contextuais_count = sum(1 for t in todos_trechos if t.get('contextual', False))
                
                # Se há muitos contextuais, aumentar o limite para incluir alguns
                if contextuais_count > 0 and diretos_count > 0:
                    # Limite mínimo: incluir todos os diretos + até 30% de contextuais
                    limit_minimo = diretos_count + int(contextuais_count * 0.3)
                    limit_total = max(limit * len(legislacoes) if legislacoes else limit * 10, limit_minimo)
                else:
                    limit_total = limit * len(legislacoes) if legislacoes else limit * 10
                
                todos_trechos = todos_trechos[:limit_total]
            
            logger.info(f"[LEGISLACAO] ✅ Encontrados {len(todos_trechos)} trechos (diretos + contextuais) em {len(legislacoes)} legislação(ões)")
            
            return todos_trechos
            
        except Exception as e:
            logger.error(f"[LEGISLACAO] Erro ao buscar em todas as legislações: {e}", exc_info=True)
            return []
    
    # ========== Métodos privados ==========
    
    def _extrair_texto_html(self, content: bytes, url: Optional[str] = None) -> str:
        """
        Extrai texto de conteúdo HTML, tratando texto riscado (revogado).
        
        ✅ MELHORADO: Agora tenta identificar e extrair apenas o conteúdo principal,
        removendo navegação, rodapé, anúncios, etc.
        """
        try:
            # Tentar detectar encoding
            encoding = None
            try:
                soup_temp = BeautifulSoup(content, 'html.parser')
                meta_charset = soup_temp.find('meta', charset=True)
                if meta_charset:
                    encoding = meta_charset.get('charset')
                else:
                    meta_content = soup_temp.find('meta', attrs={'http-equiv': re.compile(r'content-type', re.I)})
                    if meta_content:
                        content_attr = meta_content.get('content', '')
                        match = re.search(r'charset=([^;]+)', content_attr, re.I)
                        if match:
                            encoding = match.group(1).strip()
            except:
                pass
            
            # Parsear HTML
            if encoding:
                try:
                    soup = BeautifulSoup(content.decode(encoding), 'html.parser')
                except:
                    soup = BeautifulSoup(content, 'html.parser')
            else:
                soup = BeautifulSoup(content, 'html.parser')
            
            # Remover scripts, styles, e elementos não relevantes
            for element in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
                element.decompose()
            
            # ✅ MELHORIA: Remover elementos com classes/ids comuns de navegação/rodapé
            for element in soup.find_all(class_=re.compile(r'nav|menu|footer|header|sidebar|ad|advertisement|banner', re.I)):
                element.decompose()
            
            for element in soup.find_all(id=re.compile(r'nav|menu|footer|header|sidebar|ad|advertisement|banner', re.I)):
                element.decompose()
            
            # ✅ MELHORIA: Tentar encontrar conteúdo principal
            # Estratégia 1: Procurar por tags semânticas comuns
            conteudo_principal = None
            for tag_name in ['main', 'article', 'section', 'div']:
                for tag in soup.find_all(tag_name, class_=re.compile(r'content|main|article|text|legislacao|ato', re.I)):
                    texto_tag = tag.get_text(strip=True)
                    # Se tem "Art." e tem tamanho razoável, provavelmente é o conteúdo
                    if 'Art.' in texto_tag and len(texto_tag) > 500:
                        conteudo_principal = tag
                        logger.info(f"[LEGISLACAO] ✅ Conteúdo principal encontrado em <{tag_name}>")
                        break
                if conteudo_principal:
                    break
            
            # Estratégia 2: Se não encontrou, procurar por divs grandes com "Art."
            if not conteudo_principal:
                for div in soup.find_all('div'):
                    texto_div = div.get_text(strip=True)
                    if 'Art.' in texto_div and len(texto_div) > 1000:
                        # Verificar se não é navegação (menos links, mais texto)
                        links = div.find_all('a')
                        if len(links) < len(texto_div) / 100:  # Menos de 1 link por 100 caracteres
                            conteudo_principal = div
                            logger.info("[LEGISLACAO] ✅ Conteúdo principal encontrado em <div> grande")
                            break
            
            # Se encontrou conteúdo principal, usar apenas ele
            if conteudo_principal:
                soup = conteudo_principal
            
            # ✅ NOVO: Tratar texto riscado (strikethrough)
            # Tags comuns: <s>, <strike>, <del>, style="text-decoration: line-through"
            for tag in soup.find_all(['s', 'strike', 'del']):
                # Marcar texto riscado com prefixo especial para identificação
                if tag.string:
                    tag.string = f"[REVOGADO] {tag.string}"
                else:
                    tag.string = f"[REVOGADO] {tag.get_text()}"
            
            # Tratar elementos com style de riscado
            for tag in soup.find_all(style=lambda x: x and 'line-through' in str(x).lower()):
                texto_original = tag.get_text()
                tag.string = f"[REVOGADO] {texto_original}"
            
            # Extrair texto
            texto = soup.get_text(separator='\n', strip=True)
            
            # ✅ MELHORIA: Limpar linhas vazias excessivas e espaços
            linhas = []
            linhas_vazias_consecutivas = 0
            for linha in texto.split('\n'):
                linha_limpa = linha.strip()
                if linha_limpa:
                    linhas.append(linha_limpa)
                    linhas_vazias_consecutivas = 0
                else:
                    linhas_vazias_consecutivas += 1
                    if linhas_vazias_consecutivas < 2:  # Máximo 1 linha vazia consecutiva
                        linhas.append('')
            
            texto_limpo = '\n'.join(linhas)
            
            logger.info(f"[LEGISLACAO] ✅ Texto HTML extraído: {len(texto_limpo)} caracteres")
            return texto_limpo
            
        except Exception as e:
            logger.warning(f"[LEGISLACAO] ⚠️ Erro ao extrair texto HTML: {e}", exc_info=True)
            return ""
    
    def _extrair_texto_pdf(self, content: bytes) -> str:
        """
        Extrai texto de conteúdo PDF.
        
        ✅ MELHORADO: Agora trata PDFs com múltiplas páginas e limpa melhor o texto.
        """
        try:
            pdf_file = BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            logger.info(f"[LEGISLACAO] PDF tem {len(pdf_reader.pages)} páginas")
            
            texto = ""
            for i, page in enumerate(pdf_reader.pages, start=1):
                try:
                    texto_pagina = page.extract_text()
                    if texto_pagina:
                        texto += texto_pagina + "\n"
                    else:
                        logger.warning(f"[LEGISLACAO] ⚠️ Página {i} não retornou texto (pode ser escaneada)")
                except Exception as e:
                    logger.warning(f"[LEGISLACAO] ⚠️ Erro ao extrair texto da página {i}: {e}")
                    continue
            
            # ✅ MELHORIA: Limpar texto extraído
            # Remover quebras de linha excessivas
            texto = re.sub(r'\n{3,}', '\n\n', texto)
            # Remover espaços múltiplos
            texto = re.sub(r' {2,}', ' ', texto)
            
            logger.info(f"[LEGISLACAO] ✅ Texto PDF extraído: {len(texto)} caracteres de {len(pdf_reader.pages)} páginas")
            
            if not texto.strip():
                logger.warning("[LEGISLACAO] ⚠️ PDF não retornou texto. Pode ser um PDF escaneado (imagem) que requer OCR.")
            
            return texto.strip()
            
        except Exception as e:
            logger.warning(f"[LEGISLACAO] ⚠️ Erro ao extrair texto PDF: {e}", exc_info=True)
            return ""
    
    def _parsear_texto_legislacao(self, texto: str) -> List[Dict[str, Any]]:
        """
        Parseia texto de legislação em trechos hierárquicos.
        
        Retorna lista de dicts com:
        - referencia: str (ex: "Art. 5º", "Art. 5º, § 2º")
        - tipo_trecho: str ('artigo', 'caput', 'paragrafo', 'inciso', 'alinea')
        - texto: str (texto do trecho)
        - texto_com_artigo: str (texto com contexto do artigo completo)
        - numero_artigo: int (número do artigo)
        - hierarquia: dict (estrutura hierárquica)
        - revogado: bool (se o trecho está revogado)
        """
        trechos = []
        
        # Padrão para detectar artigos
        padrao_artigo = re.compile(
            r'Art\.\s*(\d+)[º°]?\s*(.*?)(?=Art\.\s*\d+[º°]?|$)',
            re.IGNORECASE | re.DOTALL
        )
        
        matches = list(padrao_artigo.finditer(texto))
        
        for match in matches:
            numero_artigo = int(match.group(1))
            conteudo_artigo = match.group(2).strip()
            
            # ✅ NOVO: Detectar se o artigo está revogado
            # Verificar se tem [REVOGADO] no início ou se todo o conteúdo está marcado
            artigo_revogado = False
            if '[REVOGADO]' in conteudo_artigo.upper() or conteudo_artigo.startswith('[REVOGADO]'):
                artigo_revogado = True
                # Remover marcação [REVOGADO] do texto
                conteudo_artigo = re.sub(r'\[REVOGADO\]\s*', '', conteudo_artigo, flags=re.IGNORECASE)
            
            # Separar caput de parágrafos/incisos
            partes = self._separar_caput_paragrafos(conteudo_artigo)
            
            caput = partes.get('caput', '')
            
            # ✅ NOVO: Verificar se caput está revogado
            caput_revogado = artigo_revogado or '[REVOGADO]' in caput.upper()
            if caput_revogado:
                caput = re.sub(r'\[REVOGADO\]\s*', '', caput, flags=re.IGNORECASE)
            
            # Adicionar caput
            if caput:
                trechos.append({
                    'referencia': f'Art. {numero_artigo}º',
                    'tipo_trecho': 'caput',
                    'texto': caput,
                    'texto_com_artigo': caput,
                    'numero_artigo': numero_artigo,
                    'hierarquia': {'artigo': numero_artigo},
                    'revogado': caput_revogado
                })
            
            # Adicionar parágrafos
            for i, paragrafo in enumerate(partes.get('paragrafos', []), start=1):
                # ✅ NOVO: Verificar se parágrafo está revogado
                paragrafo_revogado = artigo_revogado or '[REVOGADO]' in paragrafo['texto'].upper()
                texto_paragrafo = paragrafo['texto']
                if paragrafo_revogado:
                    texto_paragrafo = re.sub(r'\[REVOGADO\]\s*', '', texto_paragrafo, flags=re.IGNORECASE)
                
                texto_completo = f"{caput}\n\n{texto_paragrafo}"
                trechos.append({
                    'referencia': f'Art. {numero_artigo}º, § {i}º',
                    'tipo_trecho': 'paragrafo',
                    'texto': texto_paragrafo,
                    'texto_com_artigo': texto_completo,
                    'numero_artigo': numero_artigo,
                    'hierarquia': {'artigo': numero_artigo, 'paragrafo': i},
                    'revogado': paragrafo_revogado
                })
            
            # TODO: Adicionar incisos e alíneas
        
        return trechos
    
    def _separar_caput_paragrafos(self, conteudo: str) -> Dict[str, Any]:
        """
        Separa caput de parágrafos em um artigo.
        
        Returns:
            Dict com 'caput' e 'paragrafos'
        """
        # Padrão para parágrafos: § seguido de número
        padrao_paragrafo = re.compile(r'§\s*(\d+)[º°]?\s*(.*?)(?=§\s*\d+[º°]?|$)', re.IGNORECASE | re.DOTALL)
        
        # Encontrar todos os parágrafos
        paragrafos = []
        ultimo_fim = 0
        
        for match in padrao_paragrafo.finditer(conteudo):
            # Texto antes do primeiro parágrafo é o caput
            if ultimo_fim == 0:
                caput = conteudo[:match.start()].strip()
            else:
                # Parágrafos intermediários
                pass
            
            paragrafos.append({
                'numero': int(match.group(1)),
                'texto': match.group(2).strip()
            })
            ultimo_fim = match.end()
        
        # Se não encontrou parágrafos, todo o conteúdo é caput
        if not paragrafos:
            return {
                'caput': conteudo.strip(),
                'paragrafos': []
            }
        
        # Caput é tudo antes do primeiro parágrafo
        primeiro_paragrafo = padrao_paragrafo.search(conteudo)
        caput = conteudo[:primeiro_paragrafo.start()].strip() if primeiro_paragrafo else conteudo.strip()
        
        return {
            'caput': caput,
            'paragrafos': paragrafos
        }

