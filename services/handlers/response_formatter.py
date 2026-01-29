"""
ResponseFormatter - Formatação de respostas finais.

Centraliza a lógica de formatação de respostas, combinação de resultados de tools
e adição de contexto adicional.
"""
import logging
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Handler para formatação de respostas finais."""
    
    def __init__(self, limpar_frases_callback: Optional[Callable[[str], str]] = None):
        """
        Inicializa o formatter.
        
        Args:
            limpar_frases_callback: Função opcional para limpar frases problemáticas
                                    (ex: lambda texto: EmailUtils.limpar_frases_problematicas(texto))
        """
        self.limpar_frases_callback = limpar_frases_callback
    
    def combinar_resultados_tools(
        self, 
        resultados_tools: List[Dict], 
        resposta_ia_texto: str = ''
    ) -> str:
        """
        Combina resultados de múltiplas tools em uma resposta final.
        
        ✅ REFATORADO (10/01/2026): Extraído do ChatService.
        ✅ PASSO 6 - FASE 2 (10/01/2026): Suporte a formatação com IA quando há dados_json.
        
        Preserva indicadores de fonte dos resultados das tools.
        
        Args:
            resultados_tools: Lista de resultados de tools executadas
            resposta_ia_texto: Texto da resposta da IA (se houver)
        
        Returns:
            String com resposta final combinada e formatada
        """
        # ✅ CRÍTICO (14/01/2026): Filtrar resultados inválidos (None, não-dict) antes de processar
        resultados_tools = resultados_tools or []
        safe_results = []
        for idx, resultado in enumerate(resultados_tools):
            if not isinstance(resultado, dict):
                # NÃO quebra — só ignora e loga
                try:
                    logger.error(f"[FORMATTER] resultado_tools[{idx}] não é dict: {type(resultado)}={resultado}")
                except Exception:
                    pass
                continue
            safe_results.append(resultado)
        
        if not safe_results:
            # Limpar frases problemáticas mesmo quando não há tool calls válidas
            if self.limpar_frases_callback:
                return self.limpar_frases_callback(resposta_ia_texto)
            return resposta_ia_texto
        
        # ✅ PASSO 6 - FASE 2: Se tem apenas uma tool e ela retornou dados_json com precisa_formatar=True,
        # usar fallback simples diretamente (rápido para chat)
        # ✅ HÍBRIDO (12/01/2026): IA será usada apenas para emails (via EmailSendCoordinator)
        if len(safe_results) == 1:
            resultado = safe_results[0]
            
            # Verificar se tem dados_json e precisa_formatar=True
            dados_json = resultado.get('dados_json')
            precisa_formatar = resultado.get('precisa_formatar', False)
            
            if dados_json and precisa_formatar:
                # ✅ HÍBRIDO: Para chat, usar fallback simples diretamente (rápido)
                # IA será usada apenas quando explicitamente solicitado (emails, melhorias)
                try:
                    from services.agents.processo_agent import RelatorioFormatterService
                    resposta_fallback = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)
                    
                    if resposta_fallback:
                        logger.info(f'✅ Relatório formatado com fallback simples (tipo: {dados_json.get("tipo_relatorio", "desconhecido")}) - rápido para chat')
                        if self.limpar_frases_callback:
                            return self.limpar_frases_callback(resposta_fallback)
                        return resposta_fallback
                    else:
                        logger.warning('⚠️ Fallback simples retornou None/vazio. Tentando usar resposta manual.')
                        # Fallback: usar resposta manual
                        resposta_final = resultado.get('resposta') or resultado.get('mensagem') or ''
                        if resposta_final:
                            if self.limpar_frases_callback:
                                return self.limpar_frases_callback(resposta_final)
                            return resposta_final
                        # Se ainda não tem resposta, retornar mensagem de erro
                        logger.error('❌ [FORMATTER] Fallback simples falhou E resposta está vazia')
                        return 'Desculpe, não consegui formatar o relatório. Tente novamente.'
                except Exception as e:
                    logger.error(f'❌ Erro ao formatar relatório com fallback simples: {e}', exc_info=True)
                    # Fallback: usar resposta manual
                    resposta_final = resultado.get('resposta') or resultado.get('mensagem') or ''
                    if resposta_final:
                        if self.limpar_frases_callback:
                            return self.limpar_frases_callback(resposta_final)
                        return resposta_final
                    # Se ainda não tem resposta, retornar mensagem de erro
                    logger.error('❌ [FORMATTER] Erro ao formatar E resposta está vazia')
                    return 'Desculpe, ocorreu um erro ao formatar o relatório. Tente novamente.'
            
            # Sem dados_json ou precisa_formatar=False: usar resposta normal
            if resultado.get('resposta'):
                resposta_final = resultado.get('resposta')
                # Limpar frases problemáticas
                if self.limpar_frases_callback:
                    return self.limpar_frases_callback(resposta_final)
                return resposta_final
        
        # Combinar múltiplas respostas (caso com múltiplas tools)
        resposta_combinada = resposta_ia_texto + "\n\n" if resposta_ia_texto else ""
        
        for i, resultado in enumerate(safe_results, 1):
            # ✅ Já validado acima que resultado é dict válido
            resposta_item = resultado.get('resposta') or resultado.get('mensagem') or resultado.get('text') or ''
            if resposta_item:
                resposta_combinada += resposta_item
                if i < len(safe_results):
                    resposta_combinada += "\n\n"
        
        # ✅ CRÍTICO: Garantir que sempre retorna algo
        resposta_combinada = resposta_combinada.strip() or resposta_ia_texto or 'Desculpe, não consegui processar sua mensagem. Tente reformular ou verifique se o processo existe.'
        
        # Limpar frases problemáticas
        if self.limpar_frases_callback:
            return self.limpar_frases_callback(resposta_combinada)
        return resposta_combinada
    
    def formatar_resposta_com_erro(
        self,
        erro: str,
        mensagem_original: Optional[str] = None
    ) -> str:
        """
        Formata resposta de erro de forma amigável.
        
        Args:
            erro: Mensagem de erro
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            String formatada com mensagem de erro
        """
        resposta = f"❌ Erro: {erro}"
        
        if mensagem_original:
            resposta += f"\n\n💡 Mensagem original: {mensagem_original}"
        
        return resposta
    
    def formatar_resposta_com_contexto(
        self,
        resposta_base: str,
        contexto_adicional: Optional[str] = None,
        incluir_fonte: bool = True,
        fonte: Optional[str] = None
    ) -> str:
        """
        Adiciona contexto adicional e informações de fonte à resposta.
        
        Args:
            resposta_base: Resposta base a ser formatada
            contexto_adicional: Contexto adicional a ser incluído (opcional)
            incluir_fonte: Se True, inclui indicador de fonte
            fonte: Nome da fonte (ex: "Tool: listar_processos", "Conhecimento do Modelo")
        
        Returns:
            String formatada com contexto e fonte
        """
        resposta = resposta_base
        
        # Adicionar contexto adicional
        if contexto_adicional:
            resposta += f"\n\n{contexto_adicional}"
        
        # Adicionar indicador de fonte
        if incluir_fonte and fonte:
            resposta += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            resposta += f"\n🔍 FONTE: {fonte}"
            resposta += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        return resposta
    
    def formatar_resposta_tool(
        self,
        resultado_tool: Dict[str, Any],
        incluir_fonte: bool = True
    ) -> str:
        """
        Formata resposta de uma tool específica.
        
        Args:
            resultado_tool: Resultado da tool (dict com 'resposta', 'sucesso', 'erro', etc.)
            incluir_fonte: Se True, inclui indicador de fonte da tool
        
        Returns:
            String formatada com resposta da tool
        """
        if not resultado_tool.get('sucesso', True):
            # Tool retornou erro
            erro = resultado_tool.get('erro', 'Erro desconhecido')
            resposta = resultado_tool.get('resposta', f'❌ Erro: {erro}')
            
            if incluir_fonte:
                tool_name = resultado_tool.get('tool_name', 'Tool')
                resposta = self.formatar_resposta_com_contexto(
                    resposta,
                    incluir_fonte=True,
                    fonte=f"Tool: {tool_name}"
                )
            
            return resposta
        
        # Tool retornou sucesso
        resposta = resultado_tool.get('resposta', '')
        
        if incluir_fonte:
            tool_name = resultado_tool.get('tool_name', 'Tool')
            resposta = self.formatar_resposta_com_contexto(
                resposta,
                incluir_fonte=True,
                fonte=f"Tool: {tool_name}"
            )
        
        return resposta
