"""
Agent para cálculos usando Code Interpreter.

Permite ao usuário fazer cálculos complexos com explicações detalhadas
usando Code Interpreter da OpenAI.
"""
import logging
from typing import Dict, Any, Optional
from services.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CalculoAgent(BaseAgent):
    """
    Agent responsável por cálculos simples.
    
    Tools suportadas:
    - calcular_percentual: Calcula percentual simples de um valor
    """
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], 
                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            'calcular_percentual': self._calcular_percentual,
            'calcular_impostos_ncm': self._calcular_impostos_ncm,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada',
                'resposta': f'❌ Tool "{tool_name}" não disponível.'
            }
        
        try:
            return handler(arguments, context)
        except Exception as e:
            logger.error(f'Erro ao executar {tool_name}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro: {str(e)}'
            }

    def _calcular_impostos_ncm(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calcula impostos de importação (II, IPI, PIS, COFINS) usando alíquotas do TECwin no contexto da sessão
        (ou alíquotas fornecidas pelo usuário).
        """
        from services.calculo_impostos_service import CalculoImpostosService
        from services.context_service import buscar_contexto_sessao

        session_id = (context or {}).get('session_id') if isinstance(context, dict) else None
        mensagem_original = (context or {}).get('mensagem_original') if isinstance(context, dict) else None
        if not session_id:
            return {
                'sucesso': False,
                'erro': 'SESSION_ID_REQUIRED',
                'resposta': '❌ **Erro:** Não foi possível identificar a sessão para buscar alíquotas do TECwin.'
            }

        calculo_service = CalculoImpostosService()

        # Alíquotas: usuário tem prioridade
        aliquotas_ii_usuario = arguments.get('aliquotas_ii')
        aliquotas_ipi_usuario = arguments.get('aliquotas_ipi')
        aliquotas_pis_usuario = arguments.get('aliquotas_pis')
        aliquotas_cofins_usuario = arguments.get('aliquotas_cofins')

        aliquotas: Dict[str, float] = {}
        if any(v is not None for v in [aliquotas_ii_usuario, aliquotas_ipi_usuario, aliquotas_pis_usuario, aliquotas_cofins_usuario]):
            try:
                if aliquotas_ii_usuario is not None:
                    aliquotas['ii'] = float(aliquotas_ii_usuario)
                if aliquotas_ipi_usuario is not None:
                    aliquotas['ipi'] = float(aliquotas_ipi_usuario)
                if aliquotas_pis_usuario is not None:
                    aliquotas['pis'] = float(aliquotas_pis_usuario)
                if aliquotas_cofins_usuario is not None:
                    aliquotas['cofins'] = float(aliquotas_cofins_usuario)
            except Exception:
                return {
                    'sucesso': False,
                    'erro': 'ALIQUOTAS_INVALIDAS',
                    'resposta': '❌ **Alíquotas inválidas.** Verifique se você informou percentuais numéricos (ex: 18, 9.75).'
                }
        else:
            aliquotas = calculo_service.extrair_aliquotas_do_contexto(session_id) or {}

        if not aliquotas:
            return {
                'sucesso': False,
                'erro': 'ALIQUOTAS_NAO_ENCONTRADAS',
                'resposta': (
                    '❌ **Alíquotas não encontradas!**\n\n'
                    'Para calcular impostos, primeiro consulte o NCM no TECwin (ex: `tecwin 07129020`).\n'
                    'Depois, peça: “calcule os impostos…”'
                )
            }

        cif_usd = arguments.get('cif_usd')
        custo_usd = arguments.get('custo_usd')
        frete_usd = arguments.get('frete_usd')
        seguro_usd = arguments.get('seguro_usd', 0.0)
        cotacao_ptax = arguments.get('cotacao_ptax')

        if cif_usd is not None:
            if cotacao_ptax is None:
                return {
                    'sucesso': False,
                    'erro': 'COTACAO_FALTANDO',
                    'resposta': '❌ **Cotação PTAX faltando.** Informe a cotação (R$/USD) para calcular com CIF direto.'
                }
        else:
            faltando = []
            if custo_usd is None:
                faltando.append('custo_usd (USD) ou cif_usd (USD)')
            if frete_usd is None:
                faltando.append('frete_usd (USD) ou cif_usd (USD)')
            if cotacao_ptax is None:
                faltando.append('cotacao_ptax (R$/USD)')
            if faltando:
                return {
                    'sucesso': False,
                    'erro': 'VALORES_FALTANDO',
                    'resposta': (
                        '❌ **Valores faltando:**\n\n' +
                        '\n'.join([f'• {v}' for v in faltando]) +
                        '\n\n💡 Você também pode informar **CIF direto** usando `cif_usd`.'
                    )
                }

        # Buscar NCM do contexto (se houver)
        contextos_ncm = buscar_contexto_sessao(session_id, tipo_contexto='ncm_aliquotas')
        ncm = contextos_ncm[0].get('valor') if contextos_ncm else None

        resultado = calculo_service.calcular_impostos(
            custo_usd=custo_usd,
            frete_usd=frete_usd,
            seguro_usd=seguro_usd,
            cotacao_ptax=cotacao_ptax,
            aliquotas=aliquotas,
            ncm=ncm,
            cif_usd=cif_usd,
        )

        if not resultado.get('sucesso'):
            return {
                'sucesso': False,
                'erro': resultado.get('erro', 'ERRO_DESCONHECIDO'),
                'resposta': f'❌ **Erro ao calcular impostos:** {resultado.get("erro", "Erro desconhecido")}'
            }

        msg_lower = (mensagem_original or '').lower()
        incluir_explicacao = any(k in msg_lower for k in [
            'explicando', 'explicar', 'detalhado', 'detalhada', 'mostrando',
            'mostrar', 'fórmulas', 'formulas', 'passo a passo', 'como chegou'
        ])

        resposta_formatada = calculo_service.formatar_resposta_calculo(
            resultado,
            incluir_explicacao=incluir_explicacao
        )
        return {
            'sucesso': True,
            'resposta': resposta_formatada,
            'dados': resultado
        }
    
    def _calcular_percentual(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calcula percentual simples de um valor.
        
        Args:
            arguments: {
                'valor': float - Valor base
                'percentual': float - Percentual a calcular (ex: 1.5 para 1,5%)
            }
        """
        try:
            from services.calculo_impostos_service import CalculoImpostosService
            
            valor = arguments.get('valor')
            percentual = arguments.get('percentual')
            
            if valor is None or percentual is None:
                return {
                    'sucesso': False,
                    'erro': 'VALORES_FALTANDO',
                    'resposta': '❌ **Valores faltando:**\n\nPara calcular o percentual, preciso de:\n• Valor base\n• Percentual a calcular\n\nPor favor, forneça ambos os valores e tente novamente.'
                }
            
            calculo_service = CalculoImpostosService()
            resultado = calculo_service.calcular_percentual(valor, percentual)
            
            if resultado.get('sucesso'):
                resposta = f"📊 **CÁLCULO DE PERCENTUAL**\n\n"
                resposta += f"**Valor base:** {resultado['valor_base']:,.2f}\n"
                resposta += f"**Percentual:** {resultado['percentual']:.2f}%\n\n"
                resposta += f"**Resultado:**\n"
                resposta += f"• {resultado['percentual']:.2f}% de {resultado['valor_base']:,.2f} = **{resultado['resultado']:,.2f}**\n\n"
                resposta += f"**Fórmula:**\n"
                resposta += f"• Resultado = Valor × (Percentual ÷ 100)\n"
                resposta += f"• Resultado = {resultado['valor_base']:,.2f} × ({resultado['percentual']:.2f} ÷ 100)\n"
                resposta += f"• Resultado = {resultado['valor_base']:,.2f} × {resultado['percentual']/100:.4f}\n"
                resposta += f"• Resultado = **{resultado['resultado']:,.2f}**\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': resultado
                }
            else:
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'Erro desconhecido'),
                    'resposta': f'❌ Erro ao calcular percentual: {resultado.get("erro", "Erro desconhecido")}'
                }
                
        except Exception as e:
            logger.error(f'Erro ao calcular percentual: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao calcular percentual: {str(e)}'
            }
    

