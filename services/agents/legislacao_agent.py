"""
Agente responsável por operações relacionadas a legislação (IN, Lei, Decreto, etc.).
"""
import logging
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class LegislacaoAgent(BaseAgent):
    """
    Agente responsável por operações relacionadas a legislação.
    
    Tools suportadas:
    - buscar_legislacao: Busca um ato normativo específico
    - buscar_trechos_legislacao: Busca trechos de legislação por palavra-chave
    """
    
    def __init__(self):
        """Inicializa o agent de legislação."""
        super().__init__()
        try:
            from ..legislacao_service import LegislacaoService
            self.legislacao_service = LegislacaoService()
        except ImportError as e:
            logger.warning(f"⚠️ LegislacaoService não disponível: {e}")
            self.legislacao_service = None
    
    def _formatar_tipo_ato(self, tipo_ato: str) -> str:
        """
        Formata o tipo de ato para exibição (IN em maiúsculo, outros capitalizados).
        
        Args:
            tipo_ato: Tipo do ato (ex: 'in', 'IN', 'Decreto', 'Lei')
            
        Returns:
            Tipo formatado (ex: 'IN', 'Decreto', 'Lei')
        """
        if not tipo_ato:
            return tipo_ato
        if tipo_ato.lower() == 'in':
            return 'IN'
        return tipo_ato.capitalize()
    
    def _normalizar_tipo_ato(self, tipo_ato: str) -> str:
        """
        Normaliza tipo de ato para busca no banco.
        
        Converte variações como 'DEC', 'dec', 'DECRETO' para 'Decreto'.
        
        Args:
            tipo_ato: Tipo do ato (ex: 'DEC', 'dec', 'Decreto', 'IN', 'in')
        
        Returns:
            Tipo normalizado (ex: 'Decreto', 'IN')
        """
        if not tipo_ato:
            return tipo_ato
        
        tipo_lower = tipo_ato.lower().strip()
        
        # Mapear variações comuns
        mapeamento = {
            'in': 'IN',
            'instrução normativa': 'IN',
            'decreto': 'Decreto',
            'dec': 'Decreto',
            'lei': 'Lei',
            'portaria': 'Portaria',
            'resolução': 'Resolução',
        }
        
        # Buscar no mapeamento
        if tipo_lower in mapeamento:
            return mapeamento[tipo_lower]
        
        # Se não encontrou, capitalizar primeira letra
        return tipo_ato.capitalize()
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            'buscar_legislacao': self._buscar_legislacao,
            'buscar_trechos_legislacao': self._buscar_trechos_legislacao,
            'buscar_em_todas_legislacoes': self._buscar_em_todas_legislacoes,
            'buscar_legislacao_responses': self._buscar_legislacao_responses,  # ✅ NOVO: Responses API (recomendado)
            'buscar_legislacao_assistants': self._buscar_legislacao_assistants,  # ⚠️ LEGADO: Assistants API (deprecated)
            'buscar_e_importar_legislacao': self._buscar_e_importar_legislacao,
            'importar_legislacao_preview': self._importar_legislacao_preview,
            'confirmar_importacao_legislacao': self._confirmar_importacao_legislacao,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada neste agente',
                'resposta': f'❌ Tool "{tool_name}" não está disponível no LegislacaoAgent.'
            }
        
        if not self.legislacao_service:
            return {
                'sucesso': False,
                'erro': 'LegislacaoService não disponível',
                'resposta': '❌ Serviço de legislação não está disponível. Verifique se o sistema foi configurado corretamente.'
            }
        
        try:
            resultado = handler(arguments, context)
            self.log_execution(tool_name, arguments, resultado.get('sucesso', False))
            return resultado
        except Exception as e:
            logger.error(f'Erro ao executar {tool_name}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao executar {tool_name}: {str(e)}'
            }
    
    def _buscar_legislacao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Busca um ato normativo específico.
        
        Args:
            arguments: Deve conter:
                - tipo_ato: str (ex: 'IN', 'Lei', 'Decreto')
                - numero: str (ex: '680', '12345')
                - ano: int (opcional)
                - sigla_orgao: str (opcional, ex: 'RFB', 'MF')
                - pergunta: str (opcional, pergunta do usuário para detectar se quer saber sobre conteúdo)
        """
        tipo_ato = arguments.get('tipo_ato')
        numero = arguments.get('numero')
        ano = arguments.get('ano')
        sigla_orgao = arguments.get('sigla_orgao')
        # ✅ NOVO: Pegar pergunta do argumento ou do context (mensagem original do usuário)
        pergunta = arguments.get('pergunta', '')
        if not pergunta and context:
            pergunta = context.get('mensagem_original', '')
        
        # ✅ NOVO: Normalizar tipo_ato para garantir compatibilidade
        if tipo_ato:
            tipo_ato = self._normalizar_tipo_ato(tipo_ato)
        
        if not tipo_ato or not numero:
            return {
                'sucesso': False,
                'erro': 'tipo_ato e numero são obrigatórios',
                'resposta': '❌ É necessário informar o tipo do ato (ex: IN, Lei) e o número.'
            }
        
        try:
            ato = self.legislacao_service.buscar_ato(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao
            )
            
            if not ato:
                return {
                    'sucesso': False,
                    'erro': 'Ato não encontrado',
                    'resposta': f'❌ Não foi encontrada a legislação {tipo_ato} {numero}{f"/{ano}" if ano else ""}{f" ({sigla_orgao})" if sigla_orgao else ""}. Verifique se ela foi importada anteriormente.'
                }
            
            # ✅ NOVO: Detectar se usuário quer saber sobre o conteúdo
            pergunta_lower = pergunta.lower() if pergunta else ''
            quer_saber_conteudo = any(termo in pergunta_lower for termo in [
                'do que fala', 'do que trata', 'sobre o que', 'o que é', 'o que diz',
                'fala sobre', 'trata de', 'disponível', 'conteúdo', 'assunto'
            ])
            
            # Formatar resposta
            tipo_ato_formatado = self._formatar_tipo_ato(tipo_ato)
            resposta = f"📚 **{tipo_ato_formatado} {ato['numero']}/{ato['ano']}**"
            if ato.get('sigla_orgao'):
                resposta += f" ({ato['sigla_orgao']})"
            resposta += "\n\n"
            
            # Se tem título oficial, mostrar como resumo
            if ato.get('titulo_oficial'):
                resposta += f"**📋 Título/Ementa:** {ato['titulo_oficial']}\n\n"
            
            # Se usuário quer saber sobre conteúdo, buscar trechos relevantes
            if quer_saber_conteudo:
                try:
                    # Buscar primeiros artigos para dar uma ideia do conteúdo
                    trechos = self.legislacao_service.buscar_trechos_por_palavra_chave(
                        tipo_ato=tipo_ato,
                        numero=numero,
                        ano=ano,
                        sigla_orgao=sigla_orgao,
                        termos=['Art'],  # Buscar artigos
                        limit=5
                    )
                    
                    if trechos:
                        resposta += "**📄 Resumo do conteúdo:**\n\n"
                        # Agrupar por artigo
                        artigos_vistos = set()
                        for trecho in trechos[:5]:
                            num_art = trecho.get('numero_artigo')
                            if num_art and num_art not in artigos_vistos:
                                artigos_vistos.add(num_art)
                                ref = trecho.get('referencia', f'Art. {num_art}')
                                texto = trecho.get('texto', '')[:200]  # Limitar tamanho
                                resposta += f"**{ref}:** {texto}...\n\n"
                                if len(artigos_vistos) >= 3:  # Mostrar no máximo 3 artigos
                                    break
                        
                        resposta += "\n💡 **Para ver mais detalhes:**\n"
                        resposta += f"- 'buscar trechos sobre [termo] na {tipo_ato_formatado} {numero}'\n"
                        resposta += f"- 'mostre o artigo X da {tipo_ato_formatado} {numero}'\n\n"
                except Exception as e:
                    logger.warning(f"Erro ao buscar trechos para resumo: {e}")
                    # Continuar sem trechos se houver erro
            
            resposta += f"✅ Legislação encontrada no banco de dados.\n"
            resposta += f"📅 Data de importação: {ato.get('data_importacao', 'N/A')}\n"
            resposta += f"📄 Status: {'Em vigor' if ato.get('em_vigor', True) else 'Revogada'}\n"
            
            if ato.get('fonte_url'):
                resposta += f"🔗 Fonte: {ato['fonte_url']}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': ato
            }
            
        except Exception as e:
            logger.error(f'Erro ao buscar legislação: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar legislação: {str(e)}'
            }
    
    def _buscar_trechos_legislacao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Busca trechos de legislação por palavra-chave.
        
        Args:
            arguments: Deve conter:
                - tipo_ato: str (ex: 'IN', 'Lei')
                - numero: str (ex: '680')
                - termos: List[str] (palavras-chave para buscar)
                - ano: int (opcional)
                - sigla_orgao: str (opcional)
                - limit: int (opcional, padrão: 10)
        """
        tipo_ato = arguments.get('tipo_ato')
        numero = arguments.get('numero')
        termos = arguments.get('termos', [])
        ano = arguments.get('ano')
        sigla_orgao = arguments.get('sigla_orgao')
        limit = arguments.get('limit', 10)
        
        # ✅ NOVO: Normalizar tipo_ato para garantir compatibilidade
        if tipo_ato:
            tipo_ato = self._normalizar_tipo_ato(tipo_ato)
        
        if not tipo_ato or not numero:
            return {
                'sucesso': False,
                'erro': 'tipo_ato e numero são obrigatórios',
                'resposta': '❌ É necessário informar o tipo do ato (ex: IN, Lei) e o número.'
            }
        
        if not termos or not isinstance(termos, list) or len(termos) == 0:
            return {
                'sucesso': False,
                'erro': 'termos é obrigatório e deve ser uma lista',
                'resposta': '❌ É necessário informar pelo menos um termo para buscar (ex: ["canal", "conferência"]).'
            }
        
        # ✅ MELHORADO: Detectar se usuário está pedindo um artigo específico
        # Se termos contém apenas um número (ex: ["702"], ["725"]), buscar artigo completo
        import re
        pedido_artigo_especifico = False
        numero_artigo = None
        
        if len(termos) == 1:
            termo = termos[0].strip()
            # Verificar se é apenas um número (ex: "702", "725", "64")
            # Aceitar números de 1 a 9999 (artigos geralmente são até 4 dígitos)
            if termo.isdigit() and 1 <= int(termo) <= 9999:
                numero_artigo = int(termo)
                pedido_artigo_especifico = True
            else:
                # Tentar extrair número mesmo se tiver texto (ex: "art 702", "artigo 725")
                match_numero = re.search(r'(\d{1,4})', termo)
                if match_numero:
                    num = int(match_numero.group(1))
                    if 1 <= num <= 9999:
                        numero_artigo = num
                        pedido_artigo_especifico = True
        
        try:
            # Se pediu artigo específico, buscar artigo completo
            if pedido_artigo_especifico:
                resultado_artigo = self.legislacao_service.buscar_artigo_completo(
                    tipo_ato=tipo_ato,
                    numero=numero,
                    numero_artigo=numero_artigo,
                    ano=ano,
                    sigla_orgao=sigla_orgao
                )
                
                if not resultado_artigo.get('sucesso'):
                    return {
                        'sucesso': False,
                        'erro': resultado_artigo.get('erro', 'Artigo não encontrado'),
                        'resposta': f'❌ {resultado_artigo.get("erro", "Artigo não encontrado")}.'
                    }
                
                artigo = resultado_artigo['artigo']
                
                # Formatar artigo completo de forma organizada
                tipo_ato_formatado = self._formatar_tipo_ato(tipo_ato)
                ano_str = f"/{ano}" if ano else ""
                resposta = f"📖 **{tipo_ato_formatado} {numero}{ano_str} - {artigo['referencia']}**\n\n"
                
                if artigo.get('revogado'):
                    resposta += "⚠️ **Este artigo está revogado.**\n\n"
                
                # Se temos texto_completo do texto integral (mais completo), usar ele
                if artigo.get('texto_completo') and artigo.get('fonte') == 'texto_integral':
                    resposta += f"**{artigo['referencia']}** {artigo['texto_completo']}\n\n"
                elif artigo.get('texto_completo'):
                    # Texto completo de trechos parseados
                    resposta += f"**{artigo['referencia']}** {artigo['texto_completo']}\n\n"
                else:
                    # Caput
                    if artigo.get('caput'):
                        resposta += f"**{artigo['referencia']}** {artigo['caput']}\n\n"
                    
                    # Incisos e alíneas (se estiverem no caput, já foram incluídos)
                    if artigo.get('incisos'):
                        for inciso in artigo['incisos']:
                            resposta += f"{inciso['texto']}\n\n"
                    
                    if artigo.get('alineas'):
                        for alinea in artigo['alineas']:
                            resposta += f"{alinea['texto']}\n\n"
                
                # Parágrafos (sempre após o caput)
                if artigo.get('paragrafos'):
                    for paragrafo in artigo['paragrafos']:
                        if paragrafo.get('revogado'):
                            resposta += f"~~{paragrafo['referencia']}~~ *(revogado)*\n\n"
                        else:
                            resposta += f"**{paragrafo['referencia']}** {paragrafo['texto']}\n\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': {
                        'artigo': artigo,
                        'tipo': 'artigo_completo'
                    }
                }
            
            # Busca normal por palavra-chave
            trechos = self.legislacao_service.buscar_trechos_por_palavra_chave(
                tipo_ato=tipo_ato,
                numero=numero,
                termos=termos,
                ano=ano,
                sigla_orgao=sigla_orgao,
                limit=limit
            )
            
            if not trechos:
                termos_str = ', '.join(termos)
                ano_str = f"/{ano}" if ano else ""
                return {
                    'sucesso': False,
                    'erro': 'Nenhum trecho encontrado',
                    'resposta': f'❌ Não foram encontrados trechos na {tipo_ato} {numero}{ano_str} contendo os termos: {termos_str}.'
                }
            
            # Formatar resposta
            ano_str = f"/{ano}" if ano else ""
            resposta = f"🔍 **Trechos encontrados na {tipo_ato} {numero}{ano_str}**\n\n"
            resposta += f"📋 **Termos buscados:** {', '.join(termos)}\n"
            resposta += f"📄 **Total encontrado:** {len(trechos)} trecho(s)\n\n"
            resposta += "---\n\n"
            
            for i, trecho in enumerate(trechos, 1):
                resposta += f"**{i}. {trecho['referencia']}**\n\n"
                resposta += f"{trecho['texto_com_artigo']}\n\n"
                resposta += "---\n\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'total': len(trechos),
                    'trechos': trechos
                }
            }
            
        except Exception as e:
            logger.error(f'Erro ao buscar trechos: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar trechos: {str(e)}'
            }
    
    def _buscar_e_importar_legislacao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Busca e importa uma legislação automaticamente da internet.
        
        Processo:
        1. Busca URL oficial usando IA
        2. Tenta baixar e extrair conteúdo automaticamente
        3. Retorna resumo para usuário confirmar antes de gravar
        
        Args:
            arguments: Deve conter:
                - tipo_ato: str (ex: 'IN', 'Lei', 'Decreto')
                - numero: str (ex: '680', '6759')
                - ano: int (obrigatório)
                - sigla_orgao: str (opcional)
                - titulo_oficial: str (opcional)
        """
        tipo_ato = arguments.get('tipo_ato')
        numero = arguments.get('numero')
        ano = arguments.get('ano')
        sigla_orgao = arguments.get('sigla_orgao')
        titulo_oficial = arguments.get('titulo_oficial')
        
        if not tipo_ato or not numero or not ano:
            return {
                'sucesso': False,
                'erro': 'tipo_ato, numero e ano são obrigatórios',
                'resposta': '❌ É necessário informar o tipo do ato (ex: IN, Lei, Decreto), o número e o ano.'
            }
        
        try:
            # 1. Verificar se já existe no banco
            ato_existente = self.legislacao_service.buscar_ato(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao
            )
            
            if ato_existente:
                resposta = f"📚 **{tipo_ato} {numero}/{ano}** já está importada no sistema!\n\n"
                resposta += f"📅 Data de importação: {ato_existente.get('data_importacao', 'N/A')}\n"
                if ato_existente.get('fonte_url'):
                    resposta += f"🔗 Fonte: {ato_existente['fonte_url']}\n"
                resposta += "\n💡 Você pode buscar trechos usando: 'buscar trechos sobre [termo] na {tipo_ato} {numero}'"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': {
                        'ja_importada': True,
                        'ato': ato_existente
                    }
                }
            
            # 2. Buscar URL com IA
            logger.info(f"[LEGISLACAO] Buscando URL com IA para {tipo_ato} {numero}/{ano}...")
            url_encontrada = self.legislacao_service.buscar_url_com_ia(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao or ''
            )
            
            if not url_encontrada:
                return {
                    'sucesso': False,
                    'erro': 'URL não encontrada pela IA',
                    'resposta': f'❌ Não foi possível encontrar a URL oficial da {tipo_ato} {numero}/{ano} automaticamente.\n\n💡 **Alternativas:**\n1. **📚 Use o botão de importação na UI:** Clique no botão 📚 no cabeçalho do chat para abrir o modal de importação\n2. **Copie e cole diretamente:** Abra a URL no navegador, copie o texto completo e cole no modal de importação\n3. Execute o script manual: `python3 scripts/importar_legislacao.py`\n4. Forneça a URL manualmente (preferencialmente URL direta de PDF/HTML)'
                }
            
            # 3. Tentar importar automaticamente
            logger.info(f"[LEGISLACAO] Tentando importar de {url_encontrada}...")
            resultado_importacao = self.legislacao_service.importar_ato_por_url(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao or '',
                url=url_encontrada,
                titulo_oficial=titulo_oficial
            )
            
            if resultado_importacao.get('sucesso'):
                # ✅ Importação automática bem-sucedida!
                legislacao_id = resultado_importacao.get('legislacao_id')
                trechos_importados = resultado_importacao.get('trechos_importados', 0)
                
                # Buscar alguns trechos para mostrar resumo
                trechos_amostra = []
                try:
                    # Buscar primeiros 3 artigos como amostra
                    trechos_amostra = self.legislacao_service.buscar_trechos_por_palavra_chave(
                        tipo_ato=tipo_ato,
                        numero=numero,
                        ano=ano,
                        sigla_orgao=sigla_orgao,
                        termos=['Art'],  # Buscar qualquer coisa com "Art"
                        limit=3
                    )
                except:
                    pass
                
                resposta = f"✅✅✅ **{tipo_ato} {numero}/{ano} encontrada e importada!**\n\n"
                resposta += f"📊 **Resumo da importação:**\n"
                resposta += f"- **ID no banco:** {legislacao_id}\n"
                resposta += f"- **Trechos importados:** {trechos_importados}\n"
                resposta += f"- **Fonte:** {url_encontrada}\n\n"
                
                if trechos_amostra:
                    resposta += "📋 **Amostra dos trechos importados:**\n\n"
                    for i, trecho in enumerate(trechos_amostra[:3], 1):
                        # Mostrar apenas início do texto (primeiras 150 caracteres)
                        texto_preview = trecho['texto'][:150] + ('...' if len(trecho['texto']) > 150 else '')
                        resposta += f"**{i}. {trecho['referencia']}**\n{texto_preview}\n\n"
                
                resposta += "💾 **✅ A legislação foi gravada no banco de dados!**\n\n"
                resposta += "💡 **Agora você pode:**\n"
                resposta += f"- Buscar trechos específicos: 'o que a {tipo_ato} {numero} fala sobre [termo]?'\n"
                resposta += f"- Consultar a legislação: 'mostre a {tipo_ato} {numero}'\n"
                resposta += f"- Verificar se está correta: 'buscar trechos sobre [termo] na {tipo_ato} {numero}'"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': {
                        'importada': True,
                        'legislacao_id': legislacao_id,
                        'trechos_importados': trechos_importados,
                        'url': url_encontrada,
                        'amostra_trechos': len(trechos_amostra)
                    }
                }
            else:
                # ⚠️ Importação automática falhou, mas temos a URL
                erro = resultado_importacao.get('erro', 'Erro desconhecido')
                mensagem_amigavel = resultado_importacao.get('mensagem', f'Erro: {erro}')
                detalhes = resultado_importacao.get('detalhes', {})
                
                resposta = f"⚠️ **Importação automática não funcionou**\n\n"
                resposta += f"📚 **{tipo_ato} {numero}/{ano}**\n"
                resposta += f"🔗 **URL encontrada:** {url_encontrada}\n\n"
                resposta += f"❌ **{mensagem_amigavel}**\n\n"
                
                # Se for erro específico de SPA, orientar melhor
                if erro == 'SITE_SOMENTE_COPIA_COLA':
                    resposta += "💡 **Este site requer importação manual (copiar/colar):**\n"
                    resposta += "1. Abra a URL no seu navegador\n"
                    resposta += "2. Copie TODO o texto da legislação (Ctrl+A / Cmd+A, depois Ctrl+C / Cmd+C)\n"
                    resposta += "3. Cole aqui e diga 'importar este texto como IN 1984/2020'\n"
                    resposta += "   Ou execute: `python3 scripts/importar_legislacao.py`"
                elif erro == 'CONTEUDO_INSUFICIENTE_URL':
                    resposta += "💡 **O conteúdo extraído é insuficiente (site usa carregamento dinâmico):**\n"
                    resposta += "1. Abra a URL no seu navegador\n"
                    resposta += "2. Copie TODO o texto da legislação\n"
                    resposta += "3. Cole aqui e diga 'importar este texto como IN 1984/2020'\n"
                    resposta += "   Ou execute: `python3 scripts/importar_legislacao.py`"
                else:
                    resposta += "💡 **Opções:**\n"
                    resposta += "1. **Copiar/colar manualmente:** Execute `python3 scripts/importar_legislacao.py`\n"
                    resposta += "2. **Tentar novamente:** Alguns sites têm proteções que impedem acesso automático\n"
                    resposta += "3. **Fornecer URL alternativa:** Se você tiver outra URL, posso tentar novamente"
                
                return {
                    'sucesso': False,
                    'resposta': resposta,
                    'dados': {
                        'url_encontrada': url_encontrada,
                        'erro_importacao': erro,
                        'pode_tentar_manual': True
                    }
                }
                
        except Exception as e:
            logger.error(f'Erro ao buscar e importar legislação: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar e importar legislação: {str(e)}'
            }
    
    def _buscar_legislacao_responses(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Busca legislação usando Assistants API (com File Search) ou Responses API (fallback).
        
        Estratégia híbrida:
        1. Tenta Assistants API primeiro (TEM File Search/RAG até 08/2026)
        2. Fallback para Responses API (não tem File Search ainda)
        3. Fallback final para busca local
        
        Nota: Assistants API será desligado em 26/08/2026, mas funciona até lá.
        """
        pergunta = arguments.get('pergunta', '').strip()
        
        if not pergunta:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ É necessário fornecer uma pergunta sobre legislação.'
            }
        
        try:
            # ✅ 1. TENTAR Assistants API primeiro (TEM File Search/RAG)
            from ..assistants_service import get_assistants_service
            
            assistants_service = get_assistants_service()
            if assistants_service.enabled and assistants_service.assistant_id:
                logger.info(f"🔍 Tentando Assistants API (com File Search): {pergunta[:100]}...")
                resultado_assistants = assistants_service.buscar_legislacao(pergunta)
                
                if resultado_assistants and resultado_assistants.get('sucesso'):
                    resposta = resultado_assistants.get('resposta', '')
                    resposta_completa = f"""{resposta}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Fonte:** Assistants API com File Search (RAG) - {len(resposta)} caracteres
💡 Esta busca usa as legislações vetorizadas e busca semântica.
⚠️ **Nota:** Assistants API será desligado em 26/08/2026 (migração para Responses API em andamento).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
                    
                    return {
                        'sucesso': True,
                        'resposta': resposta_completa,
                        'metodo': 'assistants_api_file_search',
                        'dados': {
                            'pergunta': pergunta,
                            'thread_id': resultado_assistants.get('thread_id'),
                            'fonte': 'Assistants API com File Search (RAG)'
                        }
                    }
                else:
                    logger.warning("⚠️ Assistants API não retornou resultado. Tentando Responses API...")
            
            # ✅ 2. FALLBACK: Responses API (não tem File Search ainda)
            from ..responses_service import get_responses_service
            
            responses_service = get_responses_service()
            
            if not responses_service.enabled:
                logger.warning("⚠️ ResponsesService não habilitado. Tentando fallback para busca local...")
                # Fallback para busca local
                return self._buscar_em_todas_legislacoes(arguments, context)
            
            logger.info(f"📤 Usando Responses API (sem File Search): {pergunta[:100]}...")
            resultado = responses_service.buscar_legislacao(pergunta)
            
            if resultado and resultado.get('sucesso'):
                resposta = resultado.get('resposta', '')
                
                # Adicionar indicador de fonte (mais visível)
                resposta_completa = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **FONTE: Responses API (Nova API da OpenAI)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{resposta}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Fonte:** Busca realizada via **Responses API** (modelo: {resultado.get('modelo', 'gpt-4o')})
💡 Esta resposta usa o conhecimento do modelo GPT-4o sobre legislação brasileira.
⚠️ **Nota:** File Search/RAG ainda não está totalmente disponível na Responses API.
   Quando disponível, a busca incluirá os arquivos de legislação importados.
   Por enquanto, Assistants API (com File Search) está sendo usado quando disponível.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
                
                return {
                    'sucesso': True,
                    'resposta': resposta_completa,
                    'metodo': 'responses_api',
                    'dados': {
                        'pergunta': pergunta,
                        'modelo': resultado.get('modelo', 'gpt-4o'),
                        'fonte': 'Responses API (GPT-4o)'
                    }
                }
            else:
                erro = resultado.get('erro', 'Erro desconhecido') if resultado else 'Erro ao buscar legislação'
                logger.warning(f"⚠️ Erro na Responses API: {erro}. Tentando fallback...")
                # Fallback para busca local
                return self._buscar_em_todas_legislacoes(arguments, context)
                
        except ImportError:
            logger.warning("⚠️ ResponsesService não disponível. Usando fallback...")
            return self._buscar_em_todas_legislacoes(arguments, context)
        except Exception as e:
            logger.error(f"❌ Erro ao buscar legislação via Responses API: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar legislação: {str(e)}'
            }
    
    def _buscar_legislacao_assistants(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Busca legislação usando Assistants API (DEPRECATED - será desligado em 08/2026).
        
        ⚠️ MÉTODO LEGADO: Este método está deprecated.
        Use _buscar_legislacao_responses() que usa a nova Responses API.
        """
        """
        Busca legislação usando Assistants API com File Search (RAG avançado).
        
        Esta função usa RAG (Retrieval-Augmented Generation) que busca semanticamente
        em TODAS as legislações importadas, encontrando informações mesmo quando não há
        palavras-chave exatas.
        
        Args:
            arguments: Dict com 'pergunta' (pergunta do usuário)
            context: Contexto adicional (opcional)
        
        Returns:
            Dict com resposta da busca
        """
        try:
            from ..assistants_service import get_assistants_service
            
            pergunta = arguments.get('pergunta', '')
            if not pergunta:
                return {
                    'sucesso': False,
                    'erro': 'Pergunta não fornecida',
                    'resposta': '❌ Por favor, forneça uma pergunta sobre legislação.'
                }
            
            logger.info(f'🔍 Buscando legislação via Assistants API: "{pergunta}"')
            
            # Obter serviço de Assistants
            assistants_service = get_assistants_service()
            
            if not assistants_service.enabled:
                return {
                    'sucesso': False,
                    'erro': 'AssistantsService não habilitado',
                    'resposta': '❌ Assistants API não está configurada. Execute o script de configuração primeiro:\n\n`python scripts/configurar_assistants_legislacao.py`'
                }
            
            # Buscar legislação
            resultado = assistants_service.buscar_legislacao(pergunta)
            
            if not resultado or not resultado.get('sucesso'):
                erro = resultado.get('erro', 'Erro desconhecido') if resultado else 'Erro ao buscar legislação'
                return {
                    'sucesso': False,
                    'erro': erro,
                    'resposta': f'❌ Erro ao buscar legislação via Assistants API: {erro}\n\n💡 Verifique se o assistente está configurado corretamente.'
                }
            
            resposta = resultado.get('resposta', '')
            
            if not resposta:
                return {
                    'sucesso': False,
                    'erro': 'Resposta vazia',
                    'resposta': '❌ Nenhuma resposta encontrada. Tente reformular sua pergunta.'
                }
            
            # Adicionar nota sobre a fonte
            resposta_completa = f"{resposta}\n\n---\n\n✅ **Fonte:** Busca realizada via **Assistants API com File Search (RAG)** em todas as legislações importadas. Esta busca usa inteligência semântica, não apenas palavras-chave."
            
            logger.info(f'✅ Legislação encontrada via Assistants API')
            
            return {
                'sucesso': True,
                'resposta': resposta_completa,
                'dados': {
                    'metodo': 'assistants_api',
                    'thread_id': resultado.get('thread_id'),
                    'run_id': resultado.get('run_id')
                }
            }
            
        except ImportError:
            return {
                'sucesso': False,
                'erro': 'AssistantsService não disponível',
                'resposta': '❌ AssistantsService não está disponível. Verifique se o serviço está instalado e configurado.'
            }
        except Exception as e:
            logger.error(f'Erro ao buscar legislação via Assistants API: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar legislação via Assistants API: {str(e)}'
            }
    
    def _importar_legislacao_preview(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Busca e mostra preview de uma legislação sem salvar no banco.
        
        Use quando o usuário pedir para 'importar', 'baixar', 'buscar' legislação.
        Retorna preview para o usuário confirmar antes de gravar.
        
        Args:
            arguments: Deve conter:
                - tipo_ato: str (ex: 'IN', 'Lei', 'Decreto')
                - numero: str (ex: '680', '6759')
                - ano: int (obrigatório)
                - sigla_orgao: str (opcional)
                - titulo_oficial: str (opcional)
        """
        tipo_ato = arguments.get('tipo_ato')
        numero = arguments.get('numero')
        ano = arguments.get('ano')
        sigla_orgao = arguments.get('sigla_orgao')
        titulo_oficial = arguments.get('titulo_oficial')
        
        if not tipo_ato or not numero or not ano:
            return {
                'sucesso': False,
                'erro': 'tipo_ato, numero e ano são obrigatórios',
                'resposta': '❌ É necessário informar o tipo do ato (ex: IN, Lei, Decreto), o número e o ano.'
            }
        
        try:
            # Verificar se já existe
            ato_existente = self.legislacao_service.buscar_ato(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao
            )
            
            if ato_existente:
                resposta = f"📚 **{tipo_ato} {numero}/{ano}** já está importada no sistema!\n\n"
                resposta += f"📅 Data de importação: {ato_existente.get('data_importacao', 'N/A')}\n"
                if ato_existente.get('fonte_url'):
                    resposta += f"🔗 Fonte: {ato_existente['fonte_url']}\n"
                resposta += "\n💡 Você pode buscar trechos usando: 'buscar trechos sobre [termo] na {tipo_ato} {numero}'"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': {
                        'ja_importada': True,
                        'ato': ato_existente
                    }
                }
            
            # Verificar se tem URL fornecida pelo usuário
            url_fornecida = arguments.get('url_fornecida')
            
            # Buscar preview
            logger.info(f"[LEGISLACAO] Buscando preview para {tipo_ato} {numero}/{ano}...")
            
            # Se tem URL fornecida, tentar usar ela primeiro
            if url_fornecida:
                logger.info(f"[LEGISLACAO] URL fornecida pelo usuário: {url_fornecida}")
                # Tentar importar usando a URL fornecida em modo preview
                resultado = self.legislacao_service.importar_ato_por_url(
                    tipo_ato=tipo_ato,
                    numero=numero,
                    ano=ano,
                    sigla_orgao=sigla_orgao or '',
                    url=url_fornecida,
                    titulo_oficial=titulo_oficial,
                    modo_preview=True
                )
                
                if resultado.get('sucesso') and resultado.get('modo_preview'):
                    preview = resultado.get('preview', {})
                    preview['url'] = url_fornecida
                    resultado['preview'] = preview
                # Se falhou, continuar com busca normal
                elif not resultado.get('sucesso'):
                    logger.warning(f"[LEGISLACAO] Falha ao usar URL fornecida, tentando buscar URL com IA...")
                    resultado = self.legislacao_service.buscar_legislacao_preview(
                        tipo_ato=tipo_ato,
                        numero=numero,
                        ano=ano,
                        sigla_orgao=sigla_orgao,
                        titulo_oficial=titulo_oficial
                    )
            else:
                # Buscar URL com IA e importar
                resultado = self.legislacao_service.buscar_legislacao_preview(
                    tipo_ato=tipo_ato,
                    numero=numero,
                    ano=ano,
                    sigla_orgao=sigla_orgao,
                    titulo_oficial=titulo_oficial
                )
            
            if not resultado.get('sucesso'):
                erro = resultado.get('erro', 'Erro desconhecido')
                mensagem_amigavel = resultado.get('mensagem', f'Erro: {erro}')
                detalhes = resultado.get('detalhes', {})
                
                # ✅ CORREÇÃO: Formatar referência da legislação corretamente (capitalizar tipo_ato)
                tipo_ato_formatado = self._formatar_tipo_ato(tipo_ato)
                ref_legislacao = f'{tipo_ato_formatado} {numero}'
                if ano:
                    ref_legislacao += f'/{ano}'
                
                # Usar mensagem amigável do serviço quando disponível
                if mensagem_amigavel and mensagem_amigavel != f'Erro: {erro}':
                    # Mensagem já vem formatada do serviço
                    resposta_erro = f'❌ Não foi possível buscar a {ref_legislacao}.\n\n'
                    resposta_erro += f'**{mensagem_amigavel}**\n\n'
                    
                    # Adicionar orientações específicas baseadas no tipo de erro
                    if erro == 'SITE_SOMENTE_COPIA_COLA' or erro == 'CONTEUDO_INSUFICIENTE_URL':
                        resposta_erro += '💡 **Use a importação manual (copiar/colar):**\n'
                        resposta_erro += '1. **📚 Clique no botão 📚 no cabeçalho do chat** para abrir o modal de importação\n'
                        resposta_erro += '2. Abra a URL no seu navegador e copie TODO o texto da legislação\n'
                        resposta_erro += f'3. Cole o texto no modal, preencha os campos (Tipo: IN, Número: {numero}, Ano: {ano}) e clique em "Importar"\n'
                        resposta_erro += '   Ou execute: `python3 scripts/importar_legislacao.py`'
                    else:
                        resposta_erro += '💡 **Alternativas:**\n'
                        resposta_erro += '1. **📚 Use o botão de importação na UI:** Clique no botão 📚 no cabeçalho do chat para abrir o modal de importação\n'
                        resposta_erro += '2. **Copie e cole diretamente:** Abra a URL no navegador, copie o texto completo e cole no modal de importação\n'
                        resposta_erro += '3. Execute o script manual: `python3 scripts/importar_legislacao.py`\n'
                        resposta_erro += '4. Forneça a URL manualmente (preferencialmente URL direta de PDF/HTML)'
                else:
                    # Fallback para mensagem genérica se não tiver mensagem amigável
                    resposta_erro = f'❌ Não foi possível buscar a {ref_legislacao}.\n\n'
                    resposta_erro += f'**Motivo:** {erro}\n\n'
                    resposta_erro += '💡 **Alternativas:**\n'
                    resposta_erro += '1. **📚 Use o botão de importação na UI:** Clique no botão 📚 no cabeçalho do chat para abrir o modal de importação\n'
                    resposta_erro += '2. **Copie e cole diretamente:** Abra a URL no navegador, copie o texto completo e cole no modal de importação\n'
                    resposta_erro += '3. Execute o script manual: `python3 scripts/importar_legislacao.py`\n'
                    resposta_erro += '4. Forneça a URL manualmente (preferencialmente URL direta de PDF/HTML)'
                
                return {
                    'sucesso': False,
                    'resposta': resposta_erro
                }
            
            preview = resultado.get('preview', {})
            
            # ✅ CORREÇÃO: Capitalizar tipo_ato na resposta
            tipo_ato_formatado = self._formatar_tipo_ato(tipo_ato)
            
            # Montar resposta de preview
            resposta = f"🔍 **Encontrei {tipo_ato_formatado} {numero}/{ano}**\n\n"
            
            if preview.get('titulo_oficial'):
                resposta += f"📋 **Título:** {preview['titulo_oficial']}\n"
            if preview.get('sigla_orgao'):
                resposta += f"🏛️ **Órgão:** {preview['sigla_orgao']}\n"
            resposta += f"📄 **Total de trechos:** {preview.get('total_trechos', 0)}\n"
            resposta += f"📚 **Total de artigos:** {preview.get('total_artigos', 0)}\n"
            if preview.get('url'):
                resposta += f"🔗 **Fonte:** {preview['url']}\n"
            resposta += "\n"
            
            # Mostrar exemplo do primeiro artigo
            primeiro_artigo = preview.get('primeiro_artigo')
            if primeiro_artigo:
                texto_preview = primeiro_artigo.get('texto', '')[:200] + ('...' if len(primeiro_artigo.get('texto', '')) > 200 else '')
                resposta += f"📖 **Exemplo - {primeiro_artigo.get('referencia', 'Art. 1º')}:**\n"
                resposta += f"{texto_preview}\n\n"
            
            resposta += "💡 **Quer salvar esta legislação no banco para consultas futuras?**\n"
            resposta += "   Digite: 'sim, salvar' ou 'confirmar importação' para gravar.\n"
            resposta += "   Ou: 'não' ou 'descartar' para cancelar."
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'preview': preview,
                    'aguardando_confirmacao': True
                }
            }
            
        except Exception as e:
            logger.error(f'Erro ao buscar preview: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar preview: {str(e)}'
            }
    
    def _confirmar_importacao_legislacao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Confirma e salva uma legislação que foi visualizada em preview.
        
        Use quando o usuário confirmar que quer gravar após ver o preview.
        
        Args:
            arguments: Deve conter:
                - tipo_ato: str
                - numero: str
                - ano: int
                - sigla_orgao: str (opcional)
                - titulo_oficial: str (opcional)
                - url: str (URL encontrada no preview, opcional mas recomendado)
        """
        tipo_ato = arguments.get('tipo_ato')
        numero = arguments.get('numero')
        ano = arguments.get('ano')
        sigla_orgao = arguments.get('sigla_orgao')
        titulo_oficial = arguments.get('titulo_oficial')
        url = arguments.get('url')
        
        if not tipo_ato or not numero or not ano:
            return {
                'sucesso': False,
                'erro': 'tipo_ato, numero e ano são obrigatórios',
                'resposta': '❌ É necessário informar o tipo do ato, número e ano.'
            }
        
        try:
            # Se não tem URL, tentar buscar novamente
            if not url:
                url = self.legislacao_service.buscar_url_com_ia(
                    tipo_ato=tipo_ato,
                    numero=numero,
                    ano=ano,
                    sigla_orgao=sigla_orgao or ''
                )
            
            if not url:
                return {
                    'sucesso': False,
                    'erro': 'URL não encontrada',
                    'resposta': '❌ Não foi possível encontrar a URL. Tente buscar novamente.'
                }
            
            # Importar de verdade (sem modo_preview)
            resultado = self.legislacao_service.importar_ato_por_url(
                tipo_ato=tipo_ato,
                numero=numero,
                ano=ano,
                sigla_orgao=sigla_orgao or '',
                url=url,
                titulo_oficial=titulo_oficial,
                modo_preview=False
            )
            
            if resultado.get('sucesso'):
                legislacao_id = resultado.get('legislacao_id')
                trechos_importados = resultado.get('trechos_importados', 0)
                
                resposta = f"✅✅✅ **{tipo_ato} {numero}/{ano} gravada com sucesso!**\n\n"
                resposta += f"📊 **ID no banco:** {legislacao_id}\n"
                resposta += f"📄 **Trechos importados:** {trechos_importados}\n"
                resposta += f"🔗 **Fonte:** {url}\n\n"
                resposta += "💡 **Agora você pode:**\n"
                resposta += f"- Buscar trechos: 'o que a {tipo_ato} {numero} fala sobre [termo]?'\n"
                resposta += f"- Consultar: 'mostre a {tipo_ato} {numero}'"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': {
                        'importada': True,
                        'legislacao_id': legislacao_id,
                        'trechos_importados': trechos_importados
                    }
                }
            else:
                erro = resultado.get('erro', 'Erro desconhecido')
                mensagem_amigavel = resultado.get('mensagem', f'Erro ao gravar: {erro}')
                detalhes = resultado.get('detalhes', {})
                
                resposta_erro = f'❌ Erro ao gravar: {mensagem_amigavel}\n\n'
                
                # Se for erro específico de SPA ou conteúdo insuficiente, orientar melhor
                if erro == 'SITE_SOMENTE_COPIA_COLA' or erro == 'CONTEUDO_INSUFICIENTE_URL':
                    tipo_ato_formatado = self._formatar_tipo_ato(tipo_ato)
                    resposta_erro += '💡 **Use a importação manual (copiar/colar):**\n'
                    resposta_erro += '1. **📚 Clique no botão 📚 no cabeçalho do chat** para abrir o modal de importação\n'
                    resposta_erro += '2. Abra a URL no seu navegador e copie TODO o texto da legislação\n'
                    resposta_erro += f'3. Cole o texto no modal, preencha os campos (Tipo: {tipo_ato_formatado}, Número: {numero}, Ano: {ano}) e clique em "Importar"\n'
                    resposta_erro += '   Ou execute: `python3 scripts/importar_legislacao.py`'
                
                return {
                    'sucesso': False,
                    'erro': erro,
                    'resposta': resposta_erro
                }
                
        except Exception as e:
            logger.error(f'Erro ao confirmar importação: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao confirmar importação: {str(e)}'
            }
    
    def _buscar_em_todas_legislacoes(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Busca trechos em TODAS as legislações do banco por palavra-chave.
        
        Use quando o usuário perguntar sobre um tópico sem especificar qual legislação,
        ou quando quiser buscar em todas as legislações disponíveis.
        
        Args:
            arguments: Deve conter:
                - termos: List[str] (palavras-chave para buscar)
                - limit: int (opcional, padrão: 50)
                - incluir_revogados: bool (opcional, padrão: False)
        """
        termos = arguments.get('termos', [])
        # ✅ MELHORADO: Aumentar limite padrão para incluir mais contextuais
        # Limite padrão de 50 permite ver diretos + alguns contextuais
        limit = arguments.get('limit', 50)
        incluir_revogados = arguments.get('incluir_revogados', False)
        
        if not termos or not isinstance(termos, list) or len(termos) == 0:
            return {
                'sucesso': False,
                'erro': 'termos é obrigatório e deve ser uma lista',
                'resposta': '❌ É necessário informar pelo menos um termo para buscar (ex: ["multas", "penalidades"]).'
            }
        
        try:
            # Buscar em todas as legislações
            todos_trechos = self.legislacao_service.buscar_em_todas_legislacoes(
                termos=termos,
                limit=limit,
                incluir_revogados=incluir_revogados
            )
            
            if not todos_trechos:
                termos_str = ', '.join(termos)
                return {
                    'sucesso': False,
                    'erro': 'Nenhum trecho encontrado',
                    'resposta': f'❌ Não foram encontrados trechos contendo os termos "{termos_str}" em nenhuma legislação do banco de dados.'
                }
            
            # Agrupar por legislação para melhor apresentação
            legislacoes_encontradas = {}
            for trecho in todos_trechos:
                leg_info = trecho['legislacao_info']
                leg_key = f"{leg_info['tipo_ato']} {leg_info['numero']}/{leg_info['ano']}"
                
                if leg_key not in legislacoes_encontradas:
                    legislacoes_encontradas[leg_key] = {
                        'legislacao': leg_info,
                        'trechos': []
                    }
                
                legislacoes_encontradas[leg_key]['trechos'].append(trecho)
            
            # ✅ NOVO: Separar trechos diretos de contextuais
            trechos_diretos = [t for t in todos_trechos if not t.get('contextual', False)]
            trechos_contextuais = [t for t in todos_trechos if t.get('contextual', False)]
            
            # ✅ NOVO: Se houver muitos resultados contextuais, avisar o usuário
            total_trechos = len(todos_trechos)
            tem_muitos_contextuais = len(trechos_contextuais) > 30
            tem_muitos_resultados = total_trechos > 100
            
            # Formatar resposta
            resposta = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 **FONTE: Busca Local (SQLite)**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            resposta += f"📋 **Termos buscados:** {', '.join(termos)}\n"
            resposta += f"📚 **Legislações encontradas:** {len(legislacoes_encontradas)}\n"
            resposta += f"📄 **Total de trechos:** {total_trechos}"
            
            if trechos_contextuais:
                resposta += f" ({len(trechos_diretos)} diretos + {len(trechos_contextuais)} contextuais)"
            resposta += "\n\n"
            
            # ✅ NOVO: Aviso se houver muitos resultados
            if tem_muitos_resultados or tem_muitos_contextuais:
                resposta += "⚠️ **Muitos resultados encontrados!**\n\n"
                
                if tem_muitos_contextuais:
                    resposta += f"📚 Encontrei **{len(trechos_contextuais)} artigos contextuais** que estão dentro de títulos/capítulos sobre '{', '.join(termos)}'.\n"
                    resposta += "Esses artigos se referem ao assunto mesmo sem mencionar explicitamente o termo (ex: artigos que mencionam 'neste Título' ou 'neste Capítulo').\n\n"
                
                if tem_muitos_resultados:
                    resposta += f"📄 Total de **{total_trechos} trechos** encontrados.\n\n"
                
                resposta += "💡 **Opções:**\n"
                resposta += "- Ver apenas os trechos que mencionam diretamente o termo (mais relevantes)\n"
                resposta += "- Ver todos os resultados (pode ser muito extenso)\n"
                resposta += "- Buscar em uma legislação específica (ex: 'buscar sobre multas na IN 680')\n"
                resposta += "- Limitar a busca (ex: 'buscar sobre multas, mostrar apenas 20 resultados')\n\n"
            
            resposta += "---\n\n"
            
            # Mostrar resultados agrupados por legislação
            for leg_key, dados in legislacoes_encontradas.items():
                leg_info = dados['legislacao']
                trechos_leg = dados['trechos']
                
                # Separar diretos e contextuais nesta legislação
                trechos_diretos_leg = [t for t in trechos_leg if not t.get('contextual', False)]
                trechos_contextuais_leg = [t for t in trechos_leg if t.get('contextual', False)]
                
                tipo_ato_formatado = self._formatar_tipo_ato(leg_info['tipo_ato'])
                resposta += f"📚 **{tipo_ato_formatado} {leg_info['numero']}/{leg_info['ano']}**"
                if leg_info.get('sigla_orgao'):
                    resposta += f" ({leg_info['sigla_orgao']})"
                resposta += f"\n"
                
                if trechos_contextuais_leg:
                    resposta += f"📄 {len(trechos_diretos_leg)} trecho(s) diretos + {len(trechos_contextuais_leg)} trecho(s) contextuais\n\n"
                else:
                    resposta += f"📄 {len(trechos_leg)} trecho(s) encontrado(s)\n\n"
                
                # Mostrar primeiro os trechos diretos (mais relevantes)
                if trechos_diretos_leg:
                    resposta += "**📌 Trechos que mencionam diretamente:**\n\n"
                    for i, trecho in enumerate(trechos_diretos_leg[:5], 1):
                        resposta += f"**{i}. {trecho['referencia']}**\n\n"
                        resposta += f"{trecho['texto_com_artigo']}\n\n"
                    
                    if len(trechos_diretos_leg) > 5:
                        resposta += f"*... e mais {len(trechos_diretos_leg) - 5} trecho(s) direto(s) nesta legislação*\n\n"
                
                # Mostrar trechos contextuais (se não for muitos)
                if trechos_contextuais_leg and len(trechos_contextuais_leg) <= 20:
                    resposta += "**📚 Artigos dentro de títulos/capítulos sobre o assunto:**\n\n"
                    for i, trecho in enumerate(trechos_contextuais_leg[:10], 1):
                        resposta += f"**{i}. {trecho['referencia']}** *(contextual)*\n\n"
                        resposta += f"{trecho['texto_com_artigo'][:200]}...\n\n"
                    
                    if len(trechos_contextuais_leg) > 10:
                        resposta += f"*... e mais {len(trechos_contextuais_leg) - 10} artigo(s) contextual(is) nesta legislação*\n\n"
                elif trechos_contextuais_leg:
                    resposta += f"**📚 + {len(trechos_contextuais_leg)} artigos contextuais** (dentro de títulos/capítulos sobre o assunto)\n"
                    resposta += "*Para ver todos, peça explicitamente: 'mostrar todos os resultados sobre multas'*\n\n"
                
                resposta += "---\n\n"
            
            # Adicionar dica para busca específica
            resposta += "💡 **Dica:** Para buscar apenas em uma legislação específica, mencione o nome (ex: 'buscar sobre multas na IN 680').\n"
            
            # Adicionar indicador de fonte no final
            resposta += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **Fonte:** Busca Local (SQLite) - {len(todos_trechos)} trecho(s) encontrado(s)
💡 Esta busca usa palavras-chave exatas no banco local.
⚠️ Para perguntas conceituais, use buscar_legislacao_responses (RAG semântico).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'metodo': 'sqlite_local',
                'fonte': 'Busca Local (SQLite)',
                'dados': {
                    'total_trechos': len(todos_trechos),
                    'legislacoes_encontradas': len(legislacoes_encontradas),
                    'trechos': todos_trechos,
                    'agrupado_por_legislacao': legislacoes_encontradas
                }
            }
            
        except Exception as e:
            logger.error(f'Erro ao buscar em todas as legislações: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar em todas as legislações: {str(e)}'
            }




