"""
ConsultasBilhetadasService - Serviço para operações relacionadas a consultas bilhetadas

Este serviço centraliza operações de listagem e estatísticas de consultas bilhetadas.

⚠️ IMPORTANTE: Este sistema NÃO usa aprovação manual de consultas.
Consultas são executadas diretamente quando solicitadas (ex: ao pedir extrato de DI/CE).
As funções de aprovação/rejeição são mantidas apenas para compatibilidade, mas retornam
informação de que o sistema não usa aprovação manual.

Migrado do chat_service.py em 15/12/2025 para reduzir complexidade.
Simplificado em 15/12/2025 - removido código de aprovação não utilizado.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ConsultasBilhetadasService:
    """Serviço para operações relacionadas a consultas bilhetadas"""
    
    def __init__(self, chat_service=None):
        """
        Inicializa o ConsultasBilhetadasService
        
        Args:
            chat_service: Instância opcional do ChatService (para métodos auxiliares se necessário)
        """
        self.chat_service = chat_service
        self.custo_por_consulta = 0.942  # R$ 0,942 por consulta bilhetada
    
    def listar_consultas_bilhetadas_pendentes(
        self,
        status_filtro: Optional[str] = None,
        limite: int = 50,
        tipo_consulta: Optional[str] = None,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista consultas bilhetadas pendentes
        
        Args:
            status_filtro: Status para filtrar (padrão: 'pendente')
            limite: Limite de resultados
            tipo_consulta: Tipo de consulta para filtrar (opcional)
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict com sucesso, resposta, total, contagem e consultas
        """
        try:
            from db_manager import listar_consultas_pendentes, contar_consultas_pendentes
            
            # ✅ CRÍTICO: Se não especificou status, mostrar apenas PENDENTES
            # (consultas aprovadas/executadas não devem aparecer na lista de "pendentes")
            if status_filtro is None:
                status_filtro = 'pendente'
            
            consultas = listar_consultas_pendentes(status=status_filtro, limit=limite)
            contagem = contar_consultas_pendentes()
            
            # ✅ CRÍTICO: Filtrar novamente por status para garantir (caso a função não tenha filtrado corretamente)
            consultas = [c for c in consultas if c.get('status', '').lower() == status_filtro.lower()]
            
            # Filtrar por tipo se fornecido
            if tipo_consulta:
                consultas = [c for c in consultas if c.get('tipo_consulta', '').upper() == tipo_consulta.upper()]
            
            # ✅ CRÍTICO: Garantir ordem consistente (ORDER BY criado_em DESC)
            # A mesma ordem usada na listagem deve ser usada na conversão de números
            consultas = sorted(consultas, key=lambda x: x.get('criado_em', ''), reverse=True)
            
            if not consultas:
                resposta = f"✅ **Nenhuma consulta pendente encontrada.**\n\n"
                if status_filtro:
                    resposta += f"Filtro aplicado: status = '{status_filtro}'\n"
                if tipo_consulta:
                    resposta += f"Filtro aplicado: tipo = '{tipo_consulta}'\n"
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'total': 0,
                    'consultas': []
                }
            
            # Formatar resposta
            resposta = f"📋 **Consultas Bilhetadas Pendentes** ({len(consultas)} de {contagem.get('pendente', 0)} pendentes)\n\n"
            
            # Calcular custo estimado
            custo_total = len(consultas) * self.custo_por_consulta
            
            resposta += f"💰 **Custo estimado:** R$ {custo_total:.2f} ({len(consultas)} consultas × R$ {self.custo_por_consulta:.2f})\n\n"
            
            # Listar consultas
            for idx, consulta in enumerate(consultas[:limite], 1):
                consulta_id = consulta.get('id')
                tipo = consulta.get('tipo_consulta', 'N/A')
                numero_doc = consulta.get('numero_documento', 'N/A')
                processo = consulta.get('processo_referencia', 'N/A')
                motivo = consulta.get('motivo', 'N/A')
                status_atual = consulta.get('status', 'pendente')
                criado_em = consulta.get('criado_em', '')
                
                resposta += f"**{idx}. Consulta #{consulta_id}**\n"
                resposta += f"   - Tipo: {tipo}\n"
                resposta += f"   - Documento: {numero_doc}\n"
                if processo != 'N/A':
                    resposta += f"   - Processo: {processo}\n"
                resposta += f"   - Motivo: {motivo}\n"
                resposta += f"   - Status: {status_atual}\n"
                if criado_em:
                    try:
                        dt = datetime.fromisoformat(criado_em.replace('Z', '+00:00'))
                        data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                        resposta += f"   - Criada em: {data_formatada}\n"
                    except:
                        resposta += f"   - Criada em: {criado_em}\n"
                resposta += "\n"
            
            resposta += f"\n💡 **Nota:** Este sistema não usa aprovação manual. Consultas são executadas diretamente quando solicitadas."
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(consultas),
                'contagem': contagem,
                'consultas': consultas  # ✅ Incluir lista completa para mapeamento
            }
        except Exception as e:
            logger.error(f'Erro ao listar consultas pendentes: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro ao listar consultas: {str(e)}'
            }
    
    def _converter_ids_lista_para_reais(
        self,
        ids_raw: List[Any],
        consultas_disponiveis: List[Dict],
        tipo_operacao: str = "operação"
    ) -> tuple[List[int], List[str]]:
        """
        Converte números da lista (1, 2, 3) para IDs reais das consultas
        
        Args:
            ids_raw: Lista de IDs brutos (podem ser números da lista ou IDs reais)
            consultas_disponiveis: Lista de consultas disponíveis (na mesma ordem da listagem)
            tipo_operacao: Tipo de operação para mensagens de erro
        
        Returns:
            Tuple (ids_finais, erros_conversao)
        """
        ids = []
        erros_conversao = []
        
        for id_raw in ids_raw:
            id_int = int(id_raw) if isinstance(id_raw, (int, str)) and str(id_raw).isdigit() else None
            
            if id_int is None:
                ids.append(id_raw)  # Manter como está (pode ser string)
                continue
            
            # ✅ CRÍTICO: Se o número é pequeno (1-100), SEMPRE tratar como número da lista
            # Apenas números > 100 podem ser IDs reais
            if id_int <= 100:
                # ✅ SEMPRE tentar como número da lista primeiro
                if id_int > 0 and id_int <= len(consultas_disponiveis):
                    consulta_idx = consultas_disponiveis[id_int - 1]  # -1 porque lista começa em 0
                    consulta_id_real = consulta_idx['id']
                    ids.append(consulta_id_real)
                    logger.info(f'✅ Número da lista {id_int} convertido para ID {consulta_id_real} (Tipo: {consulta_idx.get("tipo_consulta")}, Doc: {consulta_idx.get("numero_documento")})')
                else:
                    # ✅ CRÍTICO: Se não encontrou na lista, a consulta pode ter sido processada
                    erro_msg = f'Consulta número {id_int} não encontrada na lista. A lista atual tem apenas {len(consultas_disponiveis)} consulta(s). A consulta pode ter sido processada anteriormente.'
                    erros_conversao.append(erro_msg)
                    logger.warning(f'⚠️ Número {id_int} não encontrado na lista (lista tem {len(consultas_disponiveis)} itens). Consulta pode ter sido processada.')
                    continue  # Pular este ID, não adicionar à lista
            else:
                # Número grande (>100), usar como ID direto
                ids.append(id_int)
                logger.info(f'✅ Número {id_int} tratado como ID real (não é número da lista)')
        
        return ids, erros_conversao
    
    def aprovar_consultas_bilhetadas(
        self,
        ids_raw: List[Any],
        tipo_consulta: Optional[str] = None,
        aprovar_todas: bool = False,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aprova consultas bilhetadas pendentes
        
        ⚠️ NOTA: Este sistema NÃO usa aprovação manual de consultas.
        Consultas são executadas diretamente quando solicitadas.
        Esta função é mantida apenas para compatibilidade.
        
        Args:
            ids_raw: Lista de IDs (não utilizado - mantido para compatibilidade)
            tipo_consulta: Tipo de consulta (não utilizado - mantido para compatibilidade)
            aprovar_todas: Se True, aprova todas (não utilizado - mantido para compatibilidade)
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict informando que o sistema não usa aprovação manual
        """
        resposta = "ℹ️ **Informação sobre Consultas Bilhetadas**\n\n"
        resposta += "Este sistema **NÃO usa aprovação manual** de consultas bilhetadas.\n\n"
        resposta += "**Como funciona:**\n"
        resposta += "- Quando você solicita um extrato de DI ou CE, a consulta é executada diretamente\n"
        resposta += "- Não há fila de aprovação - as consultas são bilhetadas imediatamente\n"
        resposta += "- O custo é de R$ 0,942 por consulta bilhetada\n\n"
        resposta += "💡 **Dica:** Use 'ver status consultas bilhetadas' para ver estatísticas de consultas já executadas."
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'resultado': {'aprovadas': 0, 'erros': []},
            'executadas_automaticamente': 0
        }
    
    def rejeitar_consultas_bilhetadas(
        self,
        ids_raw: List[Any],
        tipo_consulta: Optional[str] = None,
        rejeitar_todas: bool = False,
        motivo: Optional[str] = None,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rejeita consultas bilhetadas pendentes
        
        ⚠️ NOTA: Este sistema NÃO usa aprovação manual de consultas.
        Consultas são executadas diretamente quando solicitadas.
        Esta função é mantida apenas para compatibilidade.
        
        Args:
            ids_raw: Lista de IDs (não utilizado - mantido para compatibilidade)
            tipo_consulta: Tipo de consulta (não utilizado - mantido para compatibilidade)
            rejeitar_todas: Se True, rejeita todas (não utilizado - mantido para compatibilidade)
            motivo: Motivo da rejeição (não utilizado - mantido para compatibilidade)
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict informando que o sistema não usa aprovação manual
        """
        resposta = "ℹ️ **Informação sobre Consultas Bilhetadas**\n\n"
        resposta += "Este sistema **NÃO usa aprovação manual** de consultas bilhetadas.\n\n"
        resposta += "**Como funciona:**\n"
        resposta += "- Quando você solicita um extrato de DI ou CE, a consulta é executada diretamente\n"
        resposta += "- Não há fila de aprovação - as consultas são bilhetadas imediatamente\n"
        resposta += "- Não é possível rejeitar consultas, pois elas são executadas automaticamente\n\n"
        resposta += "💡 **Dica:** Se não quiser bilhetar, não solicite o extrato. Use apenas consultas de cache quando disponível."
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'resultado': {'rejeitadas': 0, 'erros': []}
        }
    
    def ver_status_consultas_bilhetadas(
        self,
        consulta_id: Optional[int] = None,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verifica status de consultas bilhetadas (específica ou estatísticas gerais)
        
        Args:
            consulta_id: ID da consulta específica (opcional, se None mostra estatísticas)
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict com sucesso, resposta e consulta/contagem
        """
        try:
            from db_manager import listar_consultas_pendentes, contar_consultas_pendentes
            
            if consulta_id:
                # Buscar consulta específica
                consultas = listar_consultas_pendentes(status=None, limit=10000)
                consulta = next((c for c in consultas if c.get('id') == consulta_id), None)
                
                if not consulta:
                    return {
                        'sucesso': False,
                        'erro': 'CONSULTA_NAO_ENCONTRADA',
                        'resposta': f'⚠️ **Consulta #{consulta_id} não encontrada.**'
                    }
                
                # Formatar resposta detalhada
                resposta = f"📋 **Consulta #{consulta_id}**\n\n"
                resposta += f"**Tipo:** {consulta.get('tipo_consulta', 'N/A')}\n"
                resposta += f"**Documento:** {consulta.get('numero_documento', 'N/A')}\n"
                resposta += f"**Processo:** {consulta.get('processo_referencia', 'N/A')}\n"
                resposta += f"**Status:** {consulta.get('status', 'N/A')}\n"
                resposta += f"**Motivo:** {consulta.get('motivo', 'N/A')}\n"
                
                if consulta.get('aprovado_em'):
                    try:
                        dt = datetime.fromisoformat(consulta.get('aprovado_em').replace('Z', '+00:00'))
                        resposta += f"**Aprovada em:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                    except:
                        resposta += f"**Aprovada em:** {consulta.get('aprovado_em')}\n"
                
                if consulta.get('aprovado_por'):
                    resposta += f"**Aprovada por:** {consulta.get('aprovado_por')}\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'consulta': consulta
                }
            else:
                # Mostrar estatísticas gerais
                contagem = contar_consultas_pendentes()
                
                resposta = f"📊 **Estatísticas de Consultas Bilhetadas**\n\n"
                resposta += f"**Pendentes:** {contagem.get('pendente', 0)}\n"
                resposta += f"**Aprovadas:** {contagem.get('aprovado', 0)}\n"
                resposta += f"**Rejeitadas:** {contagem.get('rejeitado', 0)}\n"
                resposta += f"**Executadas:** {contagem.get('executado', 0)}\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'contagem': contagem
                }
        except Exception as e:
            logger.error(f'Erro ao ver status de consultas: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro ao ver status: {str(e)}'
            }
    
    def listar_consultas_aprovadas_nao_executadas(
        self,
        tipo_consulta: Optional[str] = None,
        limite: int = 50,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista consultas aprovadas que ainda não foram executadas
        
        ⚠️ NOTA: Este sistema NÃO usa aprovação manual de consultas.
        Consultas são executadas diretamente quando solicitadas.
        Esta função é mantida apenas para compatibilidade.
        
        Args:
            tipo_consulta: Tipo de consulta (não utilizado - mantido para compatibilidade)
            limite: Limite de resultados (não utilizado - mantido para compatibilidade)
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict informando que não há consultas aprovadas aguardando execução
        """
        resposta = "✅ **Nenhuma consulta aprovada aguardando execução.**\n\n"
        resposta += "ℹ️ **Informação:** Este sistema **NÃO usa aprovação manual** de consultas.\n\n"
        resposta += "**Como funciona:**\n"
        resposta += "- Consultas são executadas diretamente quando você solicita extratos de DI ou CE\n"
        resposta += "- Não há fila de aprovação\n"
        resposta += "- Todas as consultas são bilhetadas imediatamente (custo: R$ 0,942 por consulta)\n\n"
        resposta += "💡 **Dica:** Use 'ver status consultas bilhetadas' para ver estatísticas de consultas já executadas."
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'total': 0,
            'consultas': []
        }
    
    def executar_consultas_aprovadas(
        self,
        ids_raw: List[Any],
        tipo_consulta: Optional[str] = None,
        executar_todas: bool = False,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executa consultas aprovadas
        
        ⚠️ NOTA: Este sistema NÃO usa aprovação manual de consultas.
        Consultas são executadas diretamente quando solicitadas.
        Esta função é mantida apenas para compatibilidade.
        
        Args:
            ids_raw: Lista de IDs (não utilizado - mantido para compatibilidade)
            tipo_consulta: Tipo de consulta (não utilizado - mantido para compatibilidade)
            executar_todas: Se True, executa todas (não utilizado - mantido para compatibilidade)
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict informando que o sistema não usa aprovação manual
        """
        resposta = "ℹ️ **Informação sobre Consultas Bilhetadas**\n\n"
        resposta += "Este sistema **NÃO usa aprovação manual** de consultas.\n\n"
        resposta += "**Como funciona:**\n"
        resposta += "- Quando você solicita um extrato de DI ou CE, a consulta é executada diretamente\n"
        resposta += "- Não há fila de aprovação - as consultas são bilhetadas imediatamente\n"
        resposta += "- O custo é de R$ 0,942 por consulta bilhetada\n\n"
        resposta += "💡 **Dica:** Para executar uma consulta, simplesmente solicite o extrato do documento desejado.\n"
        resposta += "   Exemplo: 'me mostre o extrato da DI 25BR12345678901' ou 'extrato do CE 123456789012345'"
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'resultado': {'executadas': 0, 'erros': []}
        }












