"""
LegislacaoPrecheckService - Precheck para detecção de intenção de importação de legislação
"""
import re
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from services.chat_service import ChatService

logger = logging.getLogger(__name__)


class LegislacaoPrecheckService:
    """Precheck para detectar intenção de importação de legislação e busca de artigos específicos."""
    
    def __init__(self, chat_service: "ChatService"):
        self.chat_service = chat_service
    
    def precheck_buscar_artigo_especifico(
        self,
        mensagem: str,
        mensagem_lower: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta se o usuário quer buscar um artigo específico de uma legislação.
        
        Padrões detectados:
        - "detalhe o art 725 do decreto 6759"
        - "mostre o artigo 64 do decreto 6759"
        - "artigo 702 do decreto 6759"
        - "art 725 decreto 6759"
        
        Returns:
            Dict com tool_call para buscar_trechos_legislacao ou None
        """
        # Padrões para detectar pedido de artigo específico
        # Formato: "art[igo] [número] [do/de] [tipo] [número]"
        padroes_artigo = [
            # "art 725 do decreto 6759"
            r'(?:detalhe|mostre|mostrar|exiba|exibir|busque|buscar|qual|quais|o|a)\s+(?:o\s+)?(?:art\.?\s*|artigo\s*)?(\d{1,4})[º°]?\s+(?:do|da|de|d[ao]s)?\s*(?:o\s+)?(IN|Lei\s+Complementar|LC|Lei|Decreto|Portaria)\s+(\d+)(?:\s*/\s*(\d{4}))?',
            # "artigo 725 decreto 6759" (sem preposição)
            r'(?:detalhe|mostre|mostrar|exiba|exibir|busque|buscar|qual|quais|o|a)\s+(?:o\s+)?(?:art\.?\s*|artigo\s*)?(\d{1,4})[º°]?\s+(IN|Lei\s+Complementar|LC|Lei|Decreto|Portaria)\s+(\d+)(?:\s*/\s*(\d{4}))?',
            # "art 725 do decreto 6759/2009"
            r'(?:art\.?\s*|artigo\s*)?(\d{1,4})[º°]?\s+(?:do|da|de|d[ao]s)?\s*(?:o\s+)?(IN|Lei\s+Complementar|LC|Lei|Decreto|Portaria)\s+(\d+)(?:\s*/\s*(\d{4}))?',
        ]
        
        for padrao in padroes_artigo:
            match = re.search(padrao, mensagem_lower, re.IGNORECASE)
            if match:
                numero_artigo = match.group(1)
                tipo_ato = match.group(2)
                numero = match.group(3)
                ano_str = match.group(4) if len(match.groups()) >= 4 and match.group(4) else None
                
                # Validar número do artigo (1-9999)
                try:
                    num_art = int(numero_artigo)
                    if not (1 <= num_art <= 9999):
                        continue
                except:
                    continue
                
                ano = None
                if ano_str:
                    try:
                        ano = int(ano_str)
                    except:
                        pass
                
                # Tentar detectar sigla do órgão
                sigla_orgao = None
                if 'rfb' in mensagem_lower or 'receita' in mensagem_lower:
                    sigla_orgao = 'RFB'
                elif 'mf' in mensagem_lower or 'fazenda' in mensagem_lower:
                    sigla_orgao = 'MF'
                elif 'pr' in mensagem_lower or 'presidência' in mensagem_lower:
                    sigla_orgao = 'PR'
                
                # Normalizar tipo_ato
                tipo_raw = (tipo_ato or '').strip()
                tipo_up = tipo_raw.upper()
                if tipo_up == 'IN':
                    tipo_ato_normalizado = 'IN'
                elif tipo_up in ('LC', 'L.C', 'L.C.'):
                    tipo_ato_normalizado = 'Lei Complementar'
                elif tipo_raw.lower().startswith('lei complementar'):
                    tipo_ato_normalizado = 'Lei Complementar'
                else:
                    # primeira letra maiúscula
                    tipo_ato_normalizado = tipo_raw.capitalize()
                
                logger.info(f"[LEGISLACAO_PRECHECK] Pedido de artigo específico detectado: {tipo_ato_normalizado} {numero}/{ano} - Art. {numero_artigo}")
                
                # Montar argumentos para a tool
                argumentos = {
                    'tipo_ato': tipo_ato_normalizado,
                    'numero': numero,
                    'termos': [numero_artigo]  # Número do artigo como único termo
                }
                
                if ano:
                    argumentos['ano'] = ano
                
                if sigla_orgao:
                    argumentos['sigla_orgao'] = sigla_orgao
                
                return {
                    'resposta': None,  # A tool vai gerar a resposta
                    'tool_calls': [{
                        'function': {
                            'name': 'buscar_trechos_legislacao',
                            'arguments': argumentos
                        }
                    }]
                }
        
        return None
    
    def precheck_importar_legislacao(
        self,
        mensagem: str,
        mensagem_lower: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta se o usuário quer importar uma legislação.
        
        Padrões detectados:
        - "importar IN 680/2006"
        - "baixar legislação da IN 680"
        - "busque o Decreto 6759/2009"
        - "trazer IN 1984 2020"
        - URLs de legislação fornecidas
        
        Returns:
            Dict com tool_call para importar_legislacao_preview ou None
        """
        # Padrões de intenção de importação
        # ✅ MELHORADO: Ordem de prioridade - padrões mais específicos primeiro
        padroes_importacao = [
            # Padrão 1: "IN 1984/2020" (com barra explícita) - MAIS ESPECÍFICO
            r'(?:importar|baixar|buscar|trazer|carregar|adicionar|busque)\s+(?:a\s+)?(?:legisla[çc][ãa]o\s+)?(?:da\s+)?(IN|Lei\s+Complementar|LC|Lei|Decreto|Portaria)\s+(\d+)\s*/\s*(\d{4})',
            # Padrão 2: "IN 1984 2020" (dois números separados por espaço) - ESPECÍFICO
            r'(?:importar|baixar|buscar|trazer|carregar|adicionar|busque)\s+(?:a\s+)?(?:legisla[çc][ãa]o\s+)?(?:da\s+)?(IN|Lei\s+Complementar|LC|Lei|Decreto|Portaria)\s+(\d+)\s+(\d{4})',
            # Padrão 3: "IN 1984" (sem ano) - FALLBACK
            r'(?:importar|baixar|buscar|trazer|carregar|adicionar|busque)\s+(?:a\s+)?(?:legisla[çc][ãa]o\s+)?(?:da\s+)?(IN|Lei\s+Complementar|LC|Lei|Decreto|Portaria)\s+(\d+)',
        ]
        
        # Tentar extrair tipo, número e ano
        tipo_ato = None
        numero = None
        ano = None
        sigla_orgao = None
        
        for padrao in padroes_importacao:
            match = re.search(padrao, mensagem_lower, re.IGNORECASE)
            if match:
                tipo_ato = match.group(1)
                numero = match.group(2)
                ano_str = match.group(3) if len(match.groups()) >= 3 else None
                
                if ano_str:
                    try:
                        ano = int(ano_str)
                    except:
                        pass
                
                # Tentar detectar sigla do órgão
                if 'rfb' in mensagem_lower or 'receita' in mensagem_lower:
                    sigla_orgao = 'RFB'
                elif 'mf' in mensagem_lower or 'fazenda' in mensagem_lower:
                    sigla_orgao = 'MF'
                elif 'pr' in mensagem_lower or 'presidência' in mensagem_lower:
                    sigla_orgao = 'PR'
                elif 'mdic' in mensagem_lower:
                    sigla_orgao = 'MDIC'
                
                break
        
        # Se não encontrou padrão, verificar se tem URL de legislação
        url_fornecida = None
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, mensagem)
        
        if urls:
            url_fornecida = urls[0]
            # Tentar extrair dados da URL
            # Exemplo: normasinternet2.receita.fazenda.gov.br/#/consulta/externa/113361
            match_id = re.search(r'/externa/(\d+)', url_fornecida)
            if match_id:
                # ID encontrado na URL - pode ser útil
                logger.info(f"[LEGISLACAO_PRECHECK] URL fornecida com ID: {match_id.group(1)}")
            
            # Se não tinha tipo/numero/ano antes, tentar inferir da URL ou contexto anterior
            if not tipo_ato or not numero:
                # Verificar se há contexto de legislação na mensagem
                if 'in' in mensagem_lower and not tipo_ato:
                    tipo_ato = 'IN'
                elif 'decreto' in mensagem_lower and not tipo_ato:
                    tipo_ato = 'Decreto'
                elif 'lei' in mensagem_lower and not tipo_ato:
                    tipo_ato = 'Lei'
        
        # Se encontrou dados suficientes, retornar tool_call
        if tipo_ato and numero:
            # Normalizar tipo_ato (inclui Lei Complementar)
            tipo_raw = (tipo_ato or '').strip()
            tipo_up = tipo_raw.upper()
            if tipo_up == 'IN':
                tipo_ato = 'IN'
            elif tipo_up in ('LC', 'L.C', 'L.C.'):
                tipo_ato = 'Lei Complementar'
            elif tipo_raw.lower().startswith('lei complementar'):
                tipo_ato = 'Lei Complementar'
            else:
                tipo_cap = tipo_raw.capitalize()
                tipo_ato = 'IN' if tipo_cap == 'In' else tipo_cap

            # Se não tem ano, tentar inferir do contexto
            if not ano:
                # ✅ MELHORADO: Tentar encontrar o SEGUNDO número de 4 dígitos após o número da legislação
                # Exemplo: "IN 1984 2020" -> numero=1984, queremos pegar 2020 (não 1984 novamente)
                
                # Primeiro, encontrar a posição do número da legislação na mensagem
                numero_pos = mensagem_lower.find(f'{tipo_ato.lower()} {numero}')
                if numero_pos >= 0:
                    # Procurar números de 4 dígitos APÓS a posição do número
                    texto_apos_numero = mensagem[numero_pos + len(f'{tipo_ato} {numero}'):]
                    # Procurar todos os números de 4 dígitos no texto restante
                    anos_encontrados = re.findall(r'\b(\d{4})\b', texto_apos_numero)
                    
                    # Pegar o primeiro número de 4 dígitos que seja um ano válido
                    for ano_str in anos_encontrados:
                        try:
                            ano_candidato = int(ano_str)
                            # Validar se é um ano razoável (1900-2100)
                            if 1900 <= ano_candidato <= 2100:
                                ano = ano_candidato
                                logger.info(f"[LEGISLACAO_PRECHECK] Ano extraído do contexto: {ano}")
                                break
                        except:
                            continue
                
                # Fallback: se ainda não encontrou, tentar qualquer número de 4 dígitos na mensagem
                if not ano:
                    todos_anos = re.findall(r'\b(\d{4})\b', mensagem)
                    # Filtrar anos válidos e pegar o último (mais provável de ser o ano)
                    anos_validos = []
                    for ano_str in todos_anos:
                        try:
                            ano_candidato = int(ano_str)
                            if 1900 <= ano_candidato <= 2100:
                                anos_validos.append(ano_candidato)
                        except:
                            continue
                    
                    if anos_validos:
                        # Se tem mais de um ano válido, pegar o último (mais provável)
                        ano = anos_validos[-1]
                        logger.info(f"[LEGISLACAO_PRECHECK] Ano extraído (fallback): {ano}")
            
            logger.info(f"[LEGISLACAO_PRECHECK] Intenção de importação detectada: {tipo_ato} {numero}/{ano}")
            
            # Montar argumentos para a tool
            argumentos = {
                'tipo_ato': tipo_ato,
                'numero': numero,
            }
            
            if ano:
                argumentos['ano'] = ano
            else:
                # Se não tem ano, não podemos chamar a tool (ano é obrigatório)
                # Mas podemos retornar uma resposta sugerindo que o usuário forneça o ano
                return {
                    'resposta': f'🔍 Detectei que você quer importar a {tipo_ato} {numero}, mas preciso do ano também.\n\n💡 **Por favor, informe:**\n- "{tipo_ato} {numero}/[ano]" (ex: "{tipo_ato} {numero}/2020")\n- Ou forneça a URL completa da legislação',
                    'tool_calls': None
                }
            
            if sigla_orgao:
                argumentos['sigla_orgao'] = sigla_orgao
            
            # Se tem URL fornecida, adicionar aos dados (para usar depois na confirmação)
            if url_fornecida:
                argumentos['url_fornecida'] = url_fornecida
            
            return {
                'resposta': None,  # A tool vai gerar a resposta
                'tool_calls': [{
                    'function': {
                        'name': 'importar_legislacao_preview',
                        'arguments': argumentos
                    }
                }]
            }
        
        # Se tem URL mas não conseguiu extrair tipo/numero/ano, tentar inferir do contexto
        if url_fornecida and not tipo_ato:
            # Tentar extrair informações da URL ou contexto
            # URLs da Receita: normasinternet2.receita.fazenda.gov.br
            if 'receita' in url_fornecida.lower() or 'fazenda' in url_fornecida.lower():
                # Provavelmente é IN da RFB
                if not tipo_ato:
                    tipo_ato = 'IN'
                if not sigla_orgao:
                    sigla_orgao = 'RFB'
            
            # URLs do Planalto: planalto.gov.br
            if 'planalto' in url_fornecida.lower():
                if not tipo_ato:
                    # Pode ser Decreto ou Lei
                    if 'decreto' in mensagem_lower:
                        tipo_ato = 'Decreto'
                    elif 'lei' in mensagem_lower:
                        tipo_ato = 'Lei'
                if not sigla_orgao:
                    sigla_orgao = 'PR'
            
            # Se ainda não tem tipo/numero/ano, não podemos chamar a tool
            if not tipo_ato or not numero:
                logger.info(f"[LEGISLACAO_PRECHECK] URL fornecida mas sem tipo/numero/ano suficiente: {url_fornecida}")
                return {
                    'resposta': f'🔗 Recebi a URL: {url_fornecida}\n\n💡 Para importar, preciso que você informe:\n- Tipo (IN, Lei, Decreto, etc.)\n- Número\n- Ano\n\n**Exemplo:** "importar IN 1984/2020 usando essa URL"',
                    'tool_calls': None
                }
        
        return None

