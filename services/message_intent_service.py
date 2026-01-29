"""
MessageIntentService - Serviço para detecção e correção de intenções em mensagens

Este serviço centraliza a lógica de detecção de intenções, correção de tool calls
incorretos e validação de ações antes do processamento pela IA.

Migrado do chat_service.py em 16/12/2025 para reduzir complexidade da função processar_mensagem.
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class MessageIntentService:
    """Serviço para detecção e correção de intenções em mensagens"""
    
    def __init__(self, chat_service=None):
        """
        Inicializa o MessageIntentService
        
        Args:
            chat_service: Instância opcional do ChatService (para métodos auxiliares se necessário)
        """
        self.chat_service = chat_service
    
    def detectar_comando_limpar_contexto(self, mensagem: str) -> bool:
        """
        Detecta se a mensagem é um comando para limpar contexto.
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            True se é comando de limpar contexto, False caso contrário
        """
        mensagem_lower = mensagem.lower().strip()
        comandos_limpar_contexto = [
            r'^limpar\s+contexto',
            r'^resetar\s+contexto',
            r'^limpar\s+hist[óo]rico',
            r'^resetar\s+hist[óo]rico',
            r'^come[çc]ar\s+do\s+zero',
            r'^come[çc]ar\s+novo',
            r'^nova\s+conversa',
            r'^esquecer\s+tudo',
            r'^limpar\s+tudo',
            r'^reset',
            r'^clear'
        ]
        
        for padrao in comandos_limpar_contexto:
            if re.search(padrao, mensagem_lower):
                return True
        return False
    
    def detectar_comando_interface(self, mensagem: str) -> Optional[Dict[str, Any]]:
        """
        Detecta comandos para abrir interfaces do sistema (menu, conciliação, etc.).
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            Dict com tipo de comando e ação, ou None se não for comando de interface
            Exemplo: {'tipo': 'menu', 'acao': 'abrir_menu'}
                     {'tipo': 'conciliação', 'acao': 'abrir_conciliação'}
        """
        mensagem_lower = mensagem.lower().strip()
        
        # Comandos para abrir menu
        # Melhorado: aceita "maike menu", "maike  menu" (com espaços), ou apenas "menu"
        comandos_menu = [
            r'^maike\s+menu\s*$',  # Exatamente "maike menu"
            r'^maike\s+menu\b',    # "maike menu" no início
            r'\bmaike\s+menu\b',   # "maike menu" em qualquer lugar
            r'(?:^|\s)maike\s+(?:abre?|abrir|mostrar|mostre|exibir|exiba)\s+(?:o\s+)?menu\b',
            r'(?:^|\s)menu\s*$',   # Apenas "menu" sozinho
            r'(?:^|\s)maike\s+op[çc][õo]es\b',
            r'(?:^|\s)maike\s+(?:mostrar|mostre)\s+op[çc][õo]es\b'
        ]
        
        for padrao in comandos_menu:
            if re.search(padrao, mensagem_lower):
                logger.info(f"🎯 [INTENT] Comando de menu detectado! Padrão: {padrao}, Mensagem: {mensagem}")
                return {'tipo': 'menu', 'acao': 'abrir_menu'}
        
        # Comandos para conciliação bancária
        comandos_conciliação = [
            r'(?:m?aike|maike\s+)?(?:quero|preciso|vou|vamos)\s+(?:fazer|faz|realizar|realiza)?\s+(?:a\s+)?(?:concilia[çc][ãa]o|conciliar)',
            r'(?:m?aike|maike\s+)?(?:quero|preciso|vou|vamos)\s+conciliar\s+banco',  # ✅ Typos: "aike", "maike"
            r'(?:m?aike|maike\s+)?(?:abre?|abrir|mostrar|mostre|exibir|exiba)\s+(?:a\s+)?(?:concilia[çc][ãa]o|concilia[çc][ãa]o\s+banc[áa]ria)',
            r'(?:m?aike|maike\s+)?(?:quero|preciso)\s+classificar\s+lan[çc]amentos',
            r'(?:m?aike|maike\s+)?concilia[çc][ãa]o',
            r'(?:m?aike|maike\s+)?classificar\s+banco'
        ]
        
        for padrao in comandos_conciliação:
            if re.search(padrao, mensagem_lower):
                return {'tipo': 'conciliação', 'acao': 'abrir_conciliação'}
        
        # Comandos para sincronização bancária
        comandos_sincronização = [
            r'(?:maike|maike\s+)?(?:quero|preciso|vou|vamos)\s+(?:fazer|faz|realizar|realiza)?\s+(?:a\s+)?(?:sincroniza[çc][ãa]o|sincronizar)',
            r'(?:maike|maike\s+)?(?:abre?|abrir|mostrar|mostre|exibir|exiba)\s+(?:a\s+)?(?:sincroniza[çc][ãa]o|sincroniza[çc][ãa]o\s+banc[áa]ria)',
            r'(?:maike|maike\s+)?(?:quero|preciso)\s+sincronizar\s+(?:extrato|extratos|banco)',
            r'(?:maike|maike\s+)?sincronizar\s+banco',
            r'(?:maike|maike\s+)?sincroniza[çc][ãa]o'
        ]
        
        for padrao in comandos_sincronização:
            if re.search(padrao, mensagem_lower):
                return {'tipo': 'sincronização', 'acao': 'abrir_sincronização'}
        
        # Comandos para importar legislação
        comandos_legislação = [
            r'(?:maike|maike\s+)?(?:quero|preciso|vou|vamos)\s+(?:fazer|faz|realizar|realiza)?\s+(?:a\s+)?(?:importa[çc][ãa]o|importar)\s+(?:de\s+)?legisla[çc][ãa]o',
            r'(?:maike|maike\s+)?(?:abre?|abrir|mostrar|mostre|exibir|exiba)\s+(?:a\s+)?(?:importa[çc][ãa]o|importar)\s+legisla[çc][ãa]o',
            r'(?:maike|maike\s+)?importar\s+legisla[çc][ãa]o'
        ]
        
        for padrao in comandos_legislação:
            if re.search(padrao, mensagem_lower):
                return {'tipo': 'legislação', 'acao': 'abrir_legislação'}
        
        # Comandos para configurações
        comandos_config = [
            r'(?:maike|maike\s+)?(?:abre?|abrir|mostrar|mostre|exibir|exiba)\s+(?:as\s+)?(?:configura[çc][õo]es|config)',
            r'(?:maike|maike\s+)?configura[çc][õo]es',
            r'(?:maike|maike\s+)?config'
        ]
        
        for padrao in comandos_config:
            if re.search(padrao, mensagem_lower):
                return {'tipo': 'config', 'acao': 'abrir_config'}
        
        return None
    
    def detectar_pergunta_ncm_produto(self, mensagem: str) -> Tuple[bool, Optional[str]]:
        """
        Detecta se a mensagem é uma pergunta sobre NCM de produto e extrai o nome do produto.
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            Tupla (é_pergunta_ncm, nome_produto)
        """
        mensagem_lower = mensagem.lower()
        
        # Padrões de pergunta sobre NCM de produto
        eh_pergunta_ncm_produto = bool(re.search(
            r'(?:qual|quais)\s+(?:o|os|a|as)?\s*ncm\s+(?:do|da|de|para|d[eo]?\s+produto?|de\s+)?|ncm\s+(?:do|da|de|para)|^ncm\s+[a-z0-9]|^qual\s+(?:a|o)\s+ncm',
            mensagem_lower
        )) and not bool(re.search(
            r'processo|processos|categoria|ALH|VDM|MSS|BND|DMD|GYM|SLL',
            mensagem_lower
        ))  # Excluir se for sobre processos/categorias
        
        produto_detectado = None
        if eh_pergunta_ncm_produto:
            # Tentar extrair o produto em diferentes padrões
            match_produto = (
                re.search(
                    r'(?:qual|quais)\s+(?:o|os|a|as)?\s*ncm\s+(?:do|da|de|para|d[eo]?\s+produto?|de\s+)?\s*([^?\.]+)',
                    mensagem_lower
                ) or re.search(
                    r'ncm\s+(?:do|da|de|para|d[eo]?\s+produto?)\s+([^?\.]+)',
                    mensagem_lower
                ) or re.search(
                    r'^ncm\s+([a-z0-9]+(?:\s+[a-z0-9]+)*)',
                    mensagem_lower
                ) or re.search(
                    r'^qual\s+(?:a|o)\s+ncm\s+(?:para|de|do|da)\s+([^?\.]+)',
                    mensagem_lower
                )
            )
            if match_produto:
                produto_detectado = match_produto.group(1).strip()
                # Limpar espaços e caracteres especiais no início/fim
                produto_detectado = re.sub(r'^[^\w]+|[^\w]+$', '', produto_detectado)
                # Se ainda está vazio ou muito curto, tentar pegar tudo após "ncm"
                if not produto_detectado or len(produto_detectado) < 2:
                    match_simples = re.search(r'^ncm\s+(.+)', mensagem_lower)
                    if match_simples:
                        produto_detectado = match_simples.group(1).strip()
                        produto_detectado = re.sub(r'[?\.]+$', '', produto_detectado)  # Remover ? e . no final
        
        return eh_pergunta_ncm_produto, produto_detectado
    
    def detectar_pergunta_pronto_registro(self, mensagem: str) -> bool:
        """
        Detecta se a mensagem é uma pergunta sobre processos prontos para registro.
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            True se é pergunta sobre pronto para registro, False caso contrário
        """
        mensagem_lower = mensagem.lower()
        return bool(
            re.search(r'pronto[s]?\s+(?:para|pra)\s+registro|precisam\s+de\s+registro|precisam\s+registrar|precisam\s+de\s+di|precisam\s+de\s+duimp|chegaram\s+sem\s+despacho|est[ao]\s+pronto[s]?\s+(?:para|pra)\s+registro|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+(?:pra|para|de)\s+registrar|temos\s+(?:pra|para|de)\s+registrar|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+pra\s+registro|(?:o\s+que|quais?)\s+(?:temos|tem|há|ha)\s+para\s+registro', mensagem_lower)
        )
    
    # ✅ REMOVIDO (14/01/2026): Métodos de detecção de intenções via regex removidos
    # Agora o modelo gerencia essas intenções via tool calling, permitindo sinônimos e variações naturais
    # Métodos removidos:
    # - detectar_intencao_averbacao
    # - detectar_intencao_criar_duimp
    # - detectar_intencao_relatorio_fob
    # - _extrair_mes_ano
    # - _extrair_categoria_relatorio
    # - detectar_intencao_relatorio_averbacoes
    
    def verificar_tool_calls_incorretos(
        self,
        mensagem: str,
        tool_calls: List[Dict[str, Any]],
        categoria_atual: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifica se a IA chamou funções incorretas e retorna correções necessárias.
        
        Args:
            mensagem: Mensagem do usuário
            tool_calls: Lista de tool calls retornados pela IA
            categoria_atual: Categoria atual do contexto (opcional)
            
        Returns:
            Dict com:
            - 'precisa_correcao': True se precisa corrigir
            - 'correcoes': Lista de correções a aplicar
            - 'tool_calls_corrigidos': Lista de tool calls corrigidos
        """
        mensagem_lower = mensagem.lower()
        correcoes = []
        tool_calls_corrigidos = []
        
        # Verificar se há tool calls
        if not tool_calls:
            return {
                'precisa_correcao': False,
                'correcoes': [],
                'tool_calls_corrigidos': []
            }
        
        # 1. Verificar se pergunta sobre NCM de produto mas chamou buscar_ncms_por_descricao
        eh_pergunta_ncm, produto = self.detectar_pergunta_ncm_produto(mensagem)
        if eh_pergunta_ncm and produto:
            tem_sugerir_ncm = any(
                tc.get('function', {}).get('name') == 'sugerir_ncm_com_ia'
                for tc in tool_calls
            )
            tem_buscar_ncm = any(
                tc.get('function', {}).get('name') == 'buscar_ncms_por_descricao'
                for tc in tool_calls
            )
            
            if not tem_sugerir_ncm and tem_buscar_ncm:
                correcoes.append({
                    'tipo': 'substituir_ncm',
                    'motivo': f'Pergunta sobre NCM de produto "{produto}" detectada, mas IA chamou buscar_ncms_por_descricao em vez de sugerir_ncm_com_ia',
                    'acao': 'forcar_sugerir_ncm',
                    'produto': produto
                })
        
        # 2. Verificar se pergunta sobre "pronto para registro" mas chamou função errada
        eh_pronto_registro = self.detectar_pergunta_pronto_registro(mensagem)
        if eh_pronto_registro:
            tem_listar_liberados = any(
                tc.get('function', {}).get('name') == 'listar_processos_liberados_registro'
                for tc in tool_calls
            )
            tem_listar_situacao_registrado = any(
                tc.get('function', {}).get('name') == 'listar_processos_por_situacao' and
                'registrado' in str(tc.get('function', {}).get('arguments', '')).lower()
                for tc in tool_calls
            )
            tem_criar_duimp = any(
                tc.get('function', {}).get('name') == 'criar_duimp'
                for tc in tool_calls
            )
            
            if not tem_listar_liberados and (tem_listar_situacao_registrado or tem_criar_duimp):
                correcoes.append({
                    'tipo': 'substituir_pronto_registro',
                    'motivo': 'Pergunta sobre "pronto para registro" detectada, mas IA chamou função incorreta',
                    'acao': 'forcar_listar_liberados',
                    'categoria': categoria_atual
                })
        
        # ✅ REMOVIDO (14/01/2026): Verificação de averbação via regex removida
        # Agora o modelo gerencia essa intenção via tool calling
        # 3. Verificar se detectou averbação mas não chamou consultar_averbacao_processo
        processo_ref = self.chat_service._extrair_processo_referencia(mensagem) if self.chat_service else None
        # ✅ REMOVIDO: intencao_averbacao = self.detectar_intencao_averbacao(mensagem)
        # Agora o modelo detecta naturalmente via tool calling
        if False:  # Desabilitado - modelo gerencia via tool calling
            tem_consultar_averbacao = any(
                tc.get('function', {}).get('name') == 'consultar_averbacao_processo'
                for tc in tool_calls
            )
            
            if not tem_consultar_averbacao:
                correcoes.append({
                    'tipo': 'forcar_averbacao',
                    'motivo': f'Averbacao detectada para processo {processo_ref}, mas IA não chamou consultar_averbacao_processo',
                    'acao': 'forcar_consultar_averbacao',
                    'processo': processo_ref
                })
        
        return {
            'precisa_correcao': len(correcoes) > 0,
            'correcoes': correcoes,
            'tool_calls_corrigidos': tool_calls_corrigidos
        }
    
    def detectar_pergunta_consultas_pendentes(self, mensagem: str) -> bool:
        """
        Detecta se a mensagem é uma pergunta sobre consultas bilhetadas pendentes.
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            True se é pergunta sobre consultas pendentes, False caso contrário
        """
        mensagem_lower = mensagem.lower()
        return bool(re.search(r'consultas?\s+pendentes?|consultas?\s+aguardando|consultas?\s+estão|quais\s+consultas?', mensagem_lower))
    
    def detectar_pergunta_valores(self, mensagem: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Detecta se a mensagem é uma pergunta sobre valores (frete, seguro, FOB, CIF) e extrai informações.
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            Tupla (tipo_valor, processo_valor, ce_valor)
        """
        mensagem_lower = mensagem.lower()
        
        valores_keywords = {
            'frete': 'frete',
            'seguro': 'seguro',
            'fob': 'fob',
            'cif': 'cif',
            'valor': 'todos',
            'valores': 'todos',
            'quanto': 'todos',
            'moeda': 'todos'
        }
        
        valor_detectado = None
        for keyword, tipo in valores_keywords.items():
            if keyword in mensagem_lower:
                valor_detectado = tipo
                break
        
        # Detectar número de processo
        padrao_processo = r'([A-Z]{3}\.\d{4}/\d{2})'
        match_processo = re.search(padrao_processo, mensagem, re.IGNORECASE)
        processo_valor = match_processo.group(1).upper() if match_processo else None
        
        # Detectar número de CE
        padrao_ce = r'CE\s+(\d{10,15})'
        match_ce = re.search(padrao_ce, mensagem, re.IGNORECASE)
        ce_valor = match_ce.group(1) if match_ce else None
        
        return valor_detectado, processo_valor, ce_valor
    
    def detectar_categoria_e_situacao(self, mensagem: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detecta categoria e situação na mensagem.
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            Tupla (categoria, situacao)
        """
        mensagem_lower = mensagem.lower()
        
        # Detectar situação
        situacoes_comuns = {
            'desembaraçado': 'desembaraçado',
            'desembaracado': 'desembaraçado',
            'desembaraçada': 'desembaraçado',
            'desembaracada': 'desembaraçado',
            'desembaraco': 'desembaraçado',
            'registrada': 'registrado',
            'entregue': 'entregue',
            'armazenado': 'armazenado',
            'armazenada': 'armazenado',
            'manifestado': 'manifestado',
            'manifestada': 'manifestado'
        }
        
        situacao_detectada = None
        eh_pergunta_duimp_registrada = bool(re.search(r'tem\s+duimp\s+registrada\s+para|tem\s+duimp\s+para', mensagem_lower))
        
        if not eh_pergunta_duimp_registrada:
            for palavra, situacao in situacoes_comuns.items():
                if palavra in mensagem_lower:
                    if (palavra == 'registrado' or palavra == 'registrada') and ('tem duimp' in mensagem_lower or 'duimp registrada' in mensagem_lower):
                        continue
                    situacao_detectada = situacao
                    break
        
        # Detectar categoria (usar função do chat_service se disponível)
        categoria_detectada = None
        if self.chat_service:
            try:
                categoria_detectada = self.chat_service._extrair_categoria_da_mensagem(mensagem)
            except:
                pass
        
        return categoria_detectada, situacao_detectada
    
    def detectar_pergunta_pendencias(self, mensagem: str) -> bool:
        """
        Detecta se a mensagem é uma pergunta sobre pendências de processos.
        
        Args:
            mensagem: Mensagem do usuário
            
        Returns:
            True se é pergunta sobre pendências, False caso contrário
        """
        mensagem_lower = mensagem.lower()
        return bool(re.search(r'pend[êe]ncia|pendente', mensagem_lower)) and not self.detectar_pergunta_consultas_pendentes(mensagem)
    
    def aplicar_correcoes_tool_calls(
        self,
        correcoes: List[Dict[str, Any]],
        resultados_tools: List[Dict[str, Any]],
        tool_calls: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Aplica correções aos tool calls e resultados.
        
        Args:
            correcoes: Lista de correções a aplicar
            resultados_tools: Lista atual de resultados das tools
            tool_calls: Lista atual de tool calls
            
        Returns:
            Tupla (resultados_tools_corrigidos, tool_calls_corrigidos)
        """
        resultados_corrigidos = resultados_tools.copy()
        tool_calls_corrigidos = tool_calls.copy()
        
        for correcao in correcoes:
            tipo = correcao.get('tipo')
            
            if tipo == 'substituir_ncm':
                # Forçar sugerir_ncm_com_ia
                produto = correcao.get('produto')
                if produto and self.chat_service:
                    try:
                        resultado_forcado = self.chat_service._executar_funcao_tool(
                            'sugerir_ncm_com_ia',
                            {
                                'descricao': produto,
                                'usar_cache': True,
                                'validar_sugestao': True
                            },
                            mensagem_original=f'ncm {produto}'
                        )
                        if resultado_forcado.get('resposta') or resultado_forcado.get('mensagem'):
                            resultado_forcado['_forcado'] = True
                            resultados_corrigidos.insert(0, resultado_forcado)
                            # Remover resultados de buscar_ncms_por_descricao
                            resultados_corrigidos = [
                                r for r in resultados_corrigidos
                                if r.get('_forcado') == True or not (
                                    'buscar_ncms_por_descricao' in str(r.get('nome_funcao', '')) or
                                    'Nenhum NCM encontrado' in str(r.get('resposta', '')) or
                                    'NCMs encontrados para' in str(r.get('resposta', ''))
                                )
                            ]
                            logger.info(f'✅ Correção aplicada: sugerir_ncm_com_ia forçado para produto "{produto}"')
                    except Exception as e:
                        logger.error(f'❌ Erro ao aplicar correção de NCM: {e}', exc_info=True)
            
            elif tipo == 'substituir_pronto_registro':
                # Forçar listar_processos_liberados_registro
                categoria = correcao.get('categoria')
                if self.chat_service:
                    try:
                        resultado_corrigido = self.chat_service._executar_funcao_tool(
                            'listar_processos_liberados_registro',
                            {
                                'categoria': categoria.upper() if categoria else None,
                                'dias_retroativos': 30,
                                'limit': 200
                            },
                            mensagem_original='pronto para registro'
                        )
                        if resultado_corrigido and resultado_corrigido.get('resposta'):
                            # Remover resultados incorretos
                            resultados_corrigidos = [
                                r for r in resultados_corrigidos
                                if 'listar_processos_por_situacao' not in str(r.get('nome_funcao', ''))
                                and 'criar_duimp' not in str(r.get('nome_funcao', ''))
                            ]
                            resultados_corrigidos.insert(0, resultado_corrigido)
                            logger.info(f'✅ Correção aplicada: listar_processos_liberados_registro forçado')
                    except Exception as e:
                        logger.error(f'❌ Erro ao aplicar correção de pronto para registro: {e}', exc_info=True)
            
            elif tipo == 'forcar_averbacao':
                # Forçar consultar_averbacao_processo
                processo = correcao.get('processo')
                if processo and self.chat_service:
                    try:
                        resultado_averbacao = self.chat_service._executar_funcao_tool(
                            'consultar_averbacao_processo',
                            {
                                'processo_referencia': processo
                            },
                            mensagem_original=f'averbacao {processo}'
                        )
                        if resultado_averbacao and resultado_averbacao.get('resposta'):
                            # Remover outros resultados se necessário
                            resultados_corrigidos.insert(0, resultado_averbacao)
                            logger.info(f'✅ Correção aplicada: consultar_averbacao_processo forçado para {processo}')
                    except Exception as e:
                        logger.error(f'❌ Erro ao aplicar correção de averbação: {e}', exc_info=True)
        
        return resultados_corrigidos, tool_calls_corrigidos










