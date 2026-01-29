"""
ContextExtractionHandler - Extração e preparação de contexto para prompts.

Centraliza a lógica de extração de contexto de processos, categorias e documentos,
e preparação de contexto formatado para incluir em prompts da IA.
"""
import logging
import re
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)


class ContextExtractionHandler:
    """Handler para extração e preparação de contexto."""
    
    def __init__(self, chat_service=None):
        """
        Inicializa o handler.
        
        Args:
            chat_service: Instância opcional do ChatService (para métodos auxiliares se necessário)
        """
        self.chat_service = chat_service
    
    def obter_contexto_processo(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Obtém contexto completo de um processo, incluindo DUIMP se houver.
        
        ✅ REFATORADO (10/01/2026): Extraído do ChatService.
        
        Args:
            processo_referencia: Referência do processo (ex: 'ALH.0001/25')
        
        Returns:
            Dict com contexto do processo:
            {
                'encontrado': bool,
                'processo_referencia': str,
                'ces': List[Dict],
                'ccts': List[Dict],
                'resumo': Dict,
                'duimp': Dict
            }
        """
        try:
            from db_manager import obter_dados_documentos_processo
            
            dados = obter_dados_documentos_processo(processo_referencia)
            if not dados:
                return {'encontrado': False}
            
            # ✅ MELHORIA: Verificar se há DUIMP registrada para este processo
            duimp_info = None
            if self.chat_service and hasattr(self.chat_service, '_verificar_duimp_processo'):
                duimp_info = self.chat_service._verificar_duimp_processo(processo_referencia)
            
            # Formatar contexto para a IA
            contexto = {
                'encontrado': True,
                'processo_referencia': processo_referencia,
                'ces': [],
                'ccts': [],
                'resumo': {},
                'duimp': duimp_info  # ✅ Adicionar informação de DUIMP
            }
            
            # Processar CEs
            for ce in dados.get('ces', []):
                # Buscar situação do cache ou do JSON completo
                situacao = ce.get('situacao', '') or ce.get('situacao_carga', '')
                dados_completos = ce.get('dados_completos', {})
                if not situacao and isinstance(dados_completos, dict):
                    # Tentar buscar do JSON completo
                    situacao = dados_completos.get('situacaoCarga', '') or dados_completos.get('situacao', '')
                
                # Buscar data da situação
                data_situacao = ce.get('data_situacao', '') or ce.get('ultima_alteracao_api', '')
                if not data_situacao and isinstance(dados_completos, dict):
                    data_situacao = dados_completos.get('dataSituacaoCarga', '') or dados_completos.get('dataHoraSituacaoAtual', '')
                
                # Contar bloqueios
                bloqueios_ativos = ce.get('bloqueios_ativos', 0)
                bloqueios_baixados = ce.get('bloqueios_baixados', 0)
                if isinstance(dados_completos, dict):
                    # Tentar contar bloqueios do JSON se não estiver no cache
                    if bloqueios_ativos == 0:
                        bloqueios_json = dados_completos.get('bloqueios', [])
                        if isinstance(bloqueios_json, list):
                            bloqueios_ativos = len([b for b in bloqueios_json if b.get('situacao', '').upper() == 'ATIVO'])
                
                contexto['ces'].append({
                    'numero': ce.get('numero', ''),
                    'situacao': situacao,
                    'data_situacao': data_situacao,
                    'bloqueios_ativos': bloqueios_ativos,
                    'bloqueios_baixados': bloqueios_baixados,
                    'pais_procedencia': ce.get('pais_procedencia', ''),
                    'ul_destino_final': ce.get('ul_destino_final', ''),
                    'carga_bloqueada': ce.get('carga_bloqueada', False)
                })
            
            # Processar CCTs
            for cct in dados.get('ccts', []):
                contexto['ccts'].append({
                    'numero': cct.get('numero', ''),
                    'ruc': cct.get('ruc', ''),
                    'situacao': cct.get('situacao_atual', ''),
                    'data_situacao': cct.get('data_hora_situacao_atual', ''),
                    'bloqueios_ativos': cct.get('bloqueios_ativos', 0),
                    'bloqueios_baixados': cct.get('bloqueios_baixados', 0),
                    'aeroporto_origem': cct.get('aeroporto_origem', ''),
                    'pais_procedencia': cct.get('pais_procedencia', '')
                })
            
            # Resumo
            contexto['resumo'] = {
                'total_ces': len(contexto['ces']),
                'total_ccts': len(contexto['ccts']),
                'tem_ce': len(contexto['ces']) > 0,
                'tem_cct': len(contexto['ccts']) > 0
            }
            
            return contexto
        except Exception as e:
            logger.error(f'Erro ao obter contexto do processo {processo_referencia}: {e}', exc_info=True)
            return {'encontrado': False, 'erro': str(e)}
    
    def extrair_categoria_do_historico(
        self, 
        mensagem: str, 
        historico: Optional[List[Dict]] = None,
        extrair_categoria_callback: Optional[Callable[[str], Optional[str]]] = None
    ) -> Optional[str]:
        """
        Extrai categoria (ALH, VDM, DMD, etc.) do histórico da conversa.
        
        ✅ REFATORADO (10/01/2026): Extraído do ChatService.
        
        Útil quando o usuário faz perguntas sobre uma categoria sem mencioná-la explicitamente.
        
        Exemplo:
        - Usuário: "como estão os ALH?"
        - IA: [resposta sobre ALH]
        - Usuário: "quais estão bloqueados?"  ← Não menciona ALH, mas o contexto está no histórico
        
        ⚠️ IMPORTANTE: Se a categoria foi mencionada mas descartada/negada, NÃO retorna (limpa contexto).
        
        Args:
            mensagem: Mensagem atual do usuário
            historico: Histórico de mensagens anteriores
            extrair_categoria_callback: Função opcional para extrair categoria da mensagem
                                        (ex: lambda msg: chat_service._extrair_categoria_da_mensagem(msg))
        
        Returns:
            Categoria encontrada no histórico ou None
        """
        if not historico:
            return None
        
        # ✅ NOVO: Verificar se a mensagem atual descarta/nega uma categoria mencionada anteriormente
        mensagem_lower = mensagem.lower()
        palavras_descarte = ['não', 'nao', 'nunca', 'jamais', 'nada', 'nenhum', 'nenhuma', 'sem', 'não é', 'nao é', 'não tem', 'nao tem']
        categoria_descartada = None
        
        # Verificar se há negação/descarte na mensagem atual
        for palavra in palavras_descarte:
            if palavra in mensagem_lower:
                # Tentar extrair categoria que está sendo descartada
                categoria_na_mensagem = None
                if extrair_categoria_callback:
                    try:
                        categoria_na_mensagem = extrair_categoria_callback(mensagem)
                    except Exception as e:
                        logger.debug(f'Erro ao extrair categoria da mensagem: {e}')
                
                if categoria_na_mensagem:
                    categoria_descartada = categoria_na_mensagem
                    logger.info(f'⚠️ Categoria {categoria_descartada} foi descartada/negada na mensagem atual - não usar do histórico')
                    break
        
        # Verificar últimas 6 mensagens do histórico
        for item in reversed(historico[-6:]):
            item_msg = item.get('mensagem', '') or item.get('resposta', '')
            if not item_msg:
                continue
            
            # ✅ NOVO: Verificar se a categoria foi mencionada mas descartada/negada
            item_msg_lower = item_msg.lower()
            categoria_do_item = None
            if extrair_categoria_callback:
                try:
                    categoria_do_item = extrair_categoria_callback(item_msg)
                except Exception as e:
                    logger.debug(f'Erro ao extrair categoria do item do histórico: {e}')
            
            if categoria_do_item:
                # Verificar se há palavras de descarte/negação próximas à categoria
                # Padrão: "não ALH", "sem ALH", "não tem ALH", "não é ALH", etc.
                padrao_descarte = rf'(?:não|nao|sem|nunca|jamais|nada|nenhum|nenhuma)\s+{categoria_do_item.lower()}|{categoria_do_item.lower()}\s+(?:não|nao|nunca|jamais)'
                if re.search(padrao_descarte, item_msg_lower):
                    logger.info(f'⚠️ Categoria {categoria_do_item} foi descartada/negada no histórico - não usar')
                    continue
                
                # Se a categoria foi descartada na mensagem atual, não retornar ela do histórico
                if categoria_descartada and categoria_do_item.upper() == categoria_descartada.upper():
                    logger.info(f'⚠️ Categoria {categoria_do_item} do histórico foi descartada na mensagem atual - não usar')
                    continue
                
                return categoria_do_item
        
        return None
    
    def preparar_contexto_para_prompt(
        self,
        contexto_processo: Optional[Dict[str, Any]] = None,
        categoria: Optional[str] = None,
        categoria_do_historico: Optional[str] = None,
        documentos: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Prepara contexto formatado para incluir no prompt da IA.
        
        Args:
            contexto_processo: Contexto do processo (retornado por obter_contexto_processo)
            categoria: Categoria extraída da mensagem atual
            categoria_do_historico: Categoria extraída do histórico
            documentos: Documentos extraídos (CE, CCT, DI, DUIMP)
        
        Returns:
            String formatada com contexto para incluir no prompt
        """
        contexto_str = ""
        
        # Contexto de processo
        if contexto_processo and contexto_processo.get('encontrado'):
            processo_ref = contexto_processo.get('processo_referencia', '')
            contexto_str += f"\n\n📋 **CONTEXTO DE PROCESSO:** {processo_ref}\n"
            
            # CEs
            if contexto_processo.get('ces'):
                ces = contexto_processo['ces']
                contexto_str += f"CEs: {len(ces)} encontrado(s)\n"
                for ce in ces[:3]:  # Limitar a 3 para não sobrecarregar
                    contexto_str += f"  - CE {ce.get('numero', '')}: {ce.get('situacao', 'N/A')}"
                    if ce.get('bloqueios_ativos', 0) > 0:
                        contexto_str += f" ({ce.get('bloqueios_ativos')} bloqueio(s) ativo(s))"
                    contexto_str += "\n"
            
            # CCTs
            if contexto_processo.get('ccts'):
                ccts = contexto_processo['ccts']
                contexto_str += f"CCTs: {len(ccts)} encontrado(s)\n"
                for cct in ccts[:3]:  # Limitar a 3
                    contexto_str += f"  - CCT {cct.get('numero', '')}: {cct.get('situacao', 'N/A')}\n"
            
            # DUIMP
            if contexto_processo.get('duimp') and contexto_processo['duimp'].get('encontrado'):
                duimp = contexto_processo['duimp']
                contexto_str += f"DUIMP: {duimp.get('numero', 'N/A')} - {duimp.get('situacao', 'N/A')}\n"
        
        # Contexto de categoria
        categoria_para_usar = categoria or categoria_do_historico
        if categoria_para_usar:
            contexto_str += f"\n\n📋 **CONTEXTO DE CATEGORIA:** {categoria_para_usar}\n"
            if categoria:
                contexto_str += f"⚠️ CRÍTICO: Esta categoria foi extraída da mensagem atual. Use {categoria_para_usar} para filtrar os resultados.\n"
            elif categoria_do_historico:
                contexto_str += f"⚠️ IMPORTANTE: Esta categoria foi extraída do histórico da conversa. Use {categoria_para_usar} para filtrar os resultados.\n"
        
        # Contexto de documentos
        if documentos:
            if documentos.get('ce'):
                contexto_str += f"\n📄 **CE:** {documentos['ce']}\n"
            if documentos.get('cct'):
                contexto_str += f"\n📄 **CCT:** {documentos['cct']}\n"
            if documentos.get('di'):
                contexto_str += f"\n📄 **DI:** {documentos['di']}\n"
            if documentos.get('duimp'):
                contexto_str += f"\n📄 **DUIMP:** {documentos['duimp']}\n"
        
        return contexto_str
