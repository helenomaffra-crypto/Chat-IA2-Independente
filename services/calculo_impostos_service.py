"""
Serviço para cálculo de impostos de importação baseado em alíquotas do TECwin.

Permite calcular impostos (II, IPI, PIS, COFINS) após consulta de NCM no TECwin,
usando as alíquotas do contexto da última consulta.
"""
import logging
import re
from typing import Dict, Any, Optional
from services.context_service import buscar_contexto_sessao

logger = logging.getLogger(__name__)


class CalculoImpostosService:
    """Serviço para cálculo de impostos de importação."""
    
    def __init__(self):
        pass
    
    def extrair_aliquotas_do_contexto(self, session_id: str) -> Optional[Dict[str, float]]:
        """
        Extrai alíquotas da última consulta TECwin do contexto da sessão.
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dict com alíquotas (ii, ipi, pis, cofins) ou None se não encontrar
        """
        try:
            # Buscar contexto de NCM/alíquotas
            contextos = buscar_contexto_sessao(
                session_id=session_id,
                tipo_contexto='ncm_aliquotas'
            )
            
            if not contextos:
                return None
            
            # Pegar o mais recente
            contexto = contextos[0]
            dados = contexto.get('dados', {})
            
            # Extrair alíquotas dos dados
            aliquotas = {}
            
            # ✅ CORREÇÃO: As alíquotas estão em dados['aliquotas'], não diretamente em dados
            if isinstance(dados, dict):
                # Formato esperado: {'aliquotas': {'ii': 18, 'ipi': 9.75, ...}, ...}
                if 'aliquotas' in dados and isinstance(dados['aliquotas'], dict):
                    aliquotas_dict = dados['aliquotas']
                    if 'ii' in aliquotas_dict:
                        aliquotas['ii'] = self._parse_aliquota(aliquotas_dict.get('ii'))
                    if 'ipi' in aliquotas_dict:
                        aliquotas['ipi'] = self._parse_aliquota(aliquotas_dict.get('ipi'))
                    if 'pis' in aliquotas_dict:
                        aliquotas['pis'] = self._parse_aliquota(aliquotas_dict.get('pis'))
                    if 'cofins' in aliquotas_dict:
                        aliquotas['cofins'] = self._parse_aliquota(aliquotas_dict.get('cofins'))
                # Fallback: Formato direto (caso antigo): {'ii': 18, 'ipi': 9.75, ...}
                elif 'ii' in dados or 'ipi' in dados or 'pis' in dados or 'cofins' in dados:
                    if 'ii' in dados:
                        aliquotas['ii'] = self._parse_aliquota(dados.get('ii'))
                    if 'ipi' in dados:
                        aliquotas['ipi'] = self._parse_aliquota(dados.get('ipi'))
                    if 'pis' in dados:
                        aliquotas['pis'] = self._parse_aliquota(dados.get('pis'))
                    if 'cofins' in dados:
                        aliquotas['cofins'] = self._parse_aliquota(dados.get('cofins'))
            
            # Se não encontrou, tentar extrair do valor (texto formatado)
            if not aliquotas:
                valor_texto = contexto.get('valor', '')
                aliquotas = self._extrair_aliquotas_do_texto(valor_texto)
            
            # Se ainda não encontrou, tentar extrair de dados_json como string
            if not aliquotas and isinstance(dados, str):
                aliquotas = self._extrair_aliquotas_do_texto(dados)
            
            return aliquotas if aliquotas else None
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair alíquotas do contexto: {e}", exc_info=True)
            return None
    
    def _parse_aliquota(self, valor: Any) -> Optional[float]:
        """Converte valor de alíquota para float."""
        if valor is None:
            return None
        
        if isinstance(valor, (int, float)):
            return float(valor)
        
        if isinstance(valor, str):
            # Remover % e espaços
            valor_limpo = valor.replace('%', '').replace(',', '.').strip()
            try:
                return float(valor_limpo)
            except ValueError:
                return None
        
        return None
    
    def _extrair_aliquotas_do_texto(self, texto: str) -> Dict[str, float]:
        """Extrai alíquotas de um texto formatado."""
        aliquotas = {}
        
        if not texto:
            return aliquotas
        
        # Padrões para extrair alíquotas
        padroes = {
            'ii': [
                r'II[^:]*:[\s]*([\d,\.]+)%?',
                r'Imposto de Importação[^:]*:[\s]*([\d,\.]+)%?',
                r'ii["\']?\s*=\s*["\']?([\d,\.]+)',
            ],
            'ipi': [
                r'IPI[^:]*:[\s]*([\d,\.]+)%?',
                r'Imposto sobre Produtos Industrializados[^:]*:[\s]*([\d,\.]+)%?',
                r'ipi["\']?\s*=\s*["\']?([\d,\.]+)',
            ],
            'pis': [
                r'PIS[^:]*:[\s]*([\d,\.]+)%?',
                r'PIS/PASEP[^:]*:[\s]*([\d,\.]+)%?',
                r'pis["\']?\s*=\s*["\']?([\d,\.]+)',
            ],
            'cofins': [
                r'COFINS[^:]*:[\s]*([\d,\.]+)%?',
                r'cofins["\']?\s*=\s*["\']?([\d,\.]+)',
            ],
        }
        
        for imposto, padroes_imposto in padroes.items():
            for padrao in padroes_imposto:
                match = re.search(padrao, texto, re.IGNORECASE)
                if match:
                    valor_str = match.group(1)
                    valor_float = self._parse_aliquota(valor_str)
                    if valor_float is not None:
                        aliquotas[imposto] = valor_float
                        break
        
        return aliquotas
    
    def calcular_impostos(
        self,
        custo_usd: Optional[float] = None,
        frete_usd: Optional[float] = None,
        seguro_usd: Optional[float] = None,
        cotacao_ptax: Optional[float] = None,
        aliquotas: Optional[Dict[str, float]] = None,
        ncm: Optional[str] = None,
        cif_usd: Optional[float] = None  # ✅ NOVO: Aceita CIF direto
    ) -> Dict[str, Any]:
        """
        Calcula impostos de importação.
        
        Args:
            custo_usd: Valor da mercadoria em USD (VMLE) - opcional se cif_usd for fornecido
            frete_usd: Valor do frete em USD - opcional se cif_usd for fornecido
            seguro_usd: Valor do seguro em USD - opcional se cif_usd for fornecido
            cotacao_ptax: Cotação PTAX (R$ / USD) - obrigatório
            aliquotas: Dict com alíquotas {'ii': 18.0, 'ipi': 9.75, 'pis': 2.1, 'cofins': 7.6} - obrigatório
            ncm: Código NCM (opcional, para referência)
            cif_usd: ✅ NOVO: CIF direto em USD - se fornecido, ignora custo_usd + frete_usd + seguro_usd
            
        Returns:
            Dict com resultados do cálculo
        """
        try:
            # ✅ NOVO: Se CIF direto foi fornecido, usar ele; senão, calcular
            if cif_usd is not None:
                cif_usd_final = cif_usd
            else:
                # Validar que temos os valores necessários
                if custo_usd is None or frete_usd is None:
                    return {
                        'sucesso': False,
                        'erro': 'VALORES_FALTANDO',
                        'resposta': '❌ **Valores faltando:** É necessário fornecer CIF direto (cif_usd) ou custo_usd + frete_usd.'
                    }
                seguro_usd_final = seguro_usd if seguro_usd is not None else 0.0
                cif_usd_final = custo_usd + frete_usd + seguro_usd_final
            
            if cotacao_ptax is None:
                return {
                    'sucesso': False,
                    'erro': 'COTACAO_FALTANDO',
                    'resposta': '❌ **Cotação PTAX é obrigatória.**'
                }
            
            if not aliquotas:
                return {
                    'sucesso': False,
                    'erro': 'ALIQUOTAS_FALTANDO',
                    'resposta': '❌ **Alíquotas são obrigatórias.**'
                }
            
            # 1. Calcular CIF
            cif_brl = cif_usd_final * cotacao_ptax
            
            # 2. Calcular II (base: CIF)
            ii_brl = 0.0
            ii_usd = 0.0
            if aliquotas.get('ii'):
                aliquota_ii = aliquotas['ii'] / 100.0  # Converter % para decimal
                ii_brl = cif_brl * aliquota_ii
                ii_usd = ii_brl / cotacao_ptax
            
            # 3. Calcular IPI (base: CIF + II)
            ipi_brl = 0.0
            ipi_usd = 0.0
            if aliquotas.get('ipi'):
                aliquota_ipi = aliquotas['ipi'] / 100.0
                ipi_brl = (cif_brl + ii_brl) * aliquota_ipi
                ipi_usd = ipi_brl / cotacao_ptax
            
            # 4. Calcular PIS (base: CIF)
            pis_brl = 0.0
            pis_usd = 0.0
            if aliquotas.get('pis'):
                aliquota_pis = aliquotas['pis'] / 100.0
                pis_brl = cif_brl * aliquota_pis
                pis_usd = pis_brl / cotacao_ptax
            
            # 5. Calcular COFINS (base: CIF)
            cofins_brl = 0.0
            cofins_usd = 0.0
            if aliquotas.get('cofins'):
                aliquota_cofins = aliquotas['cofins'] / 100.0
                cofins_brl = cif_brl * aliquota_cofins
                cofins_usd = cofins_brl / cotacao_ptax
            
            # 6. Total de impostos
            total_brl = ii_brl + ipi_brl + pis_brl + cofins_brl
            total_usd = ii_usd + ipi_usd + pis_usd + cofins_usd
            
            # Formatar resposta
            resultado = {
                'sucesso': True,
                'ncm': ncm,
                'valores_entrada': {
                    'custo_usd': round(custo_usd, 2) if custo_usd is not None else None,
                    'frete_usd': round(frete_usd, 2) if frete_usd is not None else None,
                    'seguro_usd': round(seguro_usd, 2) if seguro_usd is not None else None,
                    'cif_usd': round(cif_usd_final, 2) if cif_usd is not None else None,
                    'cotacao_ptax': round(cotacao_ptax, 4),
                },
                'cif': {
                    'usd': round(cif_usd_final, 2),
                    'brl': round(cif_brl, 2)
                },
                'impostos': {
                    'ii': {
                        'aliquota': aliquotas.get('ii', 0),
                        'brl': round(ii_brl, 2),
                        'usd': round(ii_usd, 2)
                    },
                    'ipi': {
                        'aliquota': aliquotas.get('ipi', 0),
                        'brl': round(ipi_brl, 2),
                        'usd': round(ipi_usd, 2)
                    },
                    'pis': {
                        'aliquota': aliquotas.get('pis', 0),
                        'brl': round(pis_brl, 2),
                        'usd': round(pis_usd, 2)
                    },
                    'cofins': {
                        'aliquota': aliquotas.get('cofins', 0),
                        'brl': round(cofins_brl, 2),
                        'usd': round(cofins_usd, 2)
                    }
                },
                'total_impostos': {
                    'brl': round(total_brl, 2),
                    'usd': round(total_usd, 2)
                }
            }
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro ao calcular impostos: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def formatar_resposta_calculo(self, resultado: Dict[str, Any], incluir_explicacao: bool = True) -> str:
        """
        Formata resultado do cálculo para exibição no chat.
        
        Args:
            resultado: Resultado do cálculo
            incluir_explicacao: Se True, inclui explicação passo a passo (padrão: True)
        """
        if not resultado.get('sucesso'):
            return f"❌ **Erro ao calcular impostos:** {resultado.get('erro', 'Erro desconhecido')}"
        
        resposta = "💰 **CÁLCULO DE IMPOSTOS**\n\n"
        
        if incluir_explicacao:
            resposta += "📊 **Cálculo passo a passo:**\n\n"
        
        # NCM (se disponível)
        if resultado.get('ncm'):
            resposta += f"📋 **NCM:** {resultado['ncm']}\n\n"
        
        # Valores de entrada
        valores = resultado['valores_entrada']
        resposta += "**1️⃣ Valores de Entrada:**\n"
        
        # ✅ CORREÇÃO: Verificar se valores são None antes de formatar
        if valores.get('cif_usd') is not None:
            resposta += f"• CIF (direto): USD {valores['cif_usd']:,.2f}\n"
        else:
            custo = valores.get('custo_usd') or 0
            frete = valores.get('frete_usd') or 0
            seguro = valores.get('seguro_usd') or 0
            resposta += f"• Custo (VMLE): USD {custo:,.2f}\n"
            resposta += f"• Frete: USD {frete:,.2f}\n"
            resposta += f"• Seguro: USD {seguro:,.2f}\n"
        
        cotacao = valores.get('cotacao_ptax')
        if cotacao is not None:
            resposta += f"• Cotação PTAX: R$ {cotacao:,.4f} / USD\n\n"
        else:
            resposta += f"• Cotação PTAX: Não informada\n\n"
        
        # CIF
        cif = resultado['cif']
        resposta += f"**2️⃣ CIF (Custo + Frete + Seguro):**\n"
        
        if valores.get('cif_usd') is not None:
            resposta += f"• CIF USD = {valores['cif_usd']:,.2f} (fornecido diretamente)\n"
        else:
            custo = valores.get('custo_usd') or 0
            frete = valores.get('frete_usd') or 0
            seguro = valores.get('seguro_usd') or 0
            resposta += f"• CIF USD = {custo:,.2f} + {frete:,.2f} + {seguro:,.2f} = USD {cif['usd']:,.2f}\n"
        
        cotacao = valores.get('cotacao_ptax')
        if cotacao is not None:
            resposta += f"• CIF BRL = USD {cif['usd']:,.2f} × {cotacao:,.4f} = R$ {cif['brl']:,.2f}\n\n"
        else:
            resposta += f"• CIF BRL = Não calculado (cotação PTAX não informada)\n\n"
        
        # Impostos
        resposta += "**3️⃣ Impostos Calculados:**\n\n"
        
        impostos = resultado['impostos']
        
        # II
        if impostos['ii']['aliquota'] > 0:
            resposta += f"**II (Imposto de Importação) - {impostos['ii']['aliquota']:.2f}%:**\n"
            resposta += f"• Base de cálculo: CIF = R$ {cif['brl']:,.2f}\n"
            resposta += f"• Fórmula: II = CIF × {impostos['ii']['aliquota']:.2f}%\n"
            resposta += f"• Cálculo: R$ {cif['brl']:,.2f} × {impostos['ii']['aliquota']/100:.4f} = R$ {impostos['ii']['brl']:,.2f}\n"
            resposta += f"• Valor: R$ {impostos['ii']['brl']:,.2f} (USD {impostos['ii']['usd']:,.2f})\n\n"
        
        # IPI
        if impostos['ipi']['aliquota'] > 0:
            base_ipi = cif['brl'] + impostos['ii']['brl']
            resposta += f"**IPI (Imposto sobre Produtos Industrializados) - {impostos['ipi']['aliquota']:.2f}%:**\n"
            resposta += f"• Base de cálculo: CIF + II = R$ {cif['brl']:,.2f} + R$ {impostos['ii']['brl']:,.2f} = R$ {base_ipi:,.2f}\n"
            resposta += f"• Fórmula: IPI = (CIF + II) × {impostos['ipi']['aliquota']:.2f}%\n"
            resposta += f"• Cálculo: R$ {base_ipi:,.2f} × {impostos['ipi']['aliquota']/100:.4f} = R$ {impostos['ipi']['brl']:,.2f}\n"
            resposta += f"• Valor: R$ {impostos['ipi']['brl']:,.2f} (USD {impostos['ipi']['usd']:,.2f})\n\n"
        
        # PIS
        if impostos['pis']['aliquota'] > 0:
            resposta += f"**PIS/PASEP - {impostos['pis']['aliquota']:.2f}%:**\n"
            resposta += f"• Base de cálculo: CIF = R$ {cif['brl']:,.2f}\n"
            resposta += f"• Fórmula: PIS = CIF × {impostos['pis']['aliquota']:.2f}%\n"
            resposta += f"• Cálculo: R$ {cif['brl']:,.2f} × {impostos['pis']['aliquota']/100:.4f} = R$ {impostos['pis']['brl']:,.2f}\n"
            resposta += f"• Valor: R$ {impostos['pis']['brl']:,.2f} (USD {impostos['pis']['usd']:,.2f})\n\n"
        
        # COFINS
        if impostos['cofins']['aliquota'] > 0:
            resposta += f"**COFINS - {impostos['cofins']['aliquota']:.2f}%:**\n"
            resposta += f"• Base de cálculo: CIF = R$ {cif['brl']:,.2f}\n"
            resposta += f"• Fórmula: COFINS = CIF × {impostos['cofins']['aliquota']:.2f}%\n"
            resposta += f"• Cálculo: R$ {cif['brl']:,.2f} × {impostos['cofins']['aliquota']/100:.4f} = R$ {impostos['cofins']['brl']:,.2f}\n"
            resposta += f"• Valor: R$ {impostos['cofins']['brl']:,.2f} (USD {impostos['cofins']['usd']:,.2f})\n\n"
        
        # Total
        total = resultado['total_impostos']
        cotacao = valores.get('cotacao_ptax')
        resposta += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        resposta += f"**💰 TOTAL DE IMPOSTOS:**\n"
        resposta += f"• Total BRL = II + IPI + PIS + COFINS\n"
        resposta += f"• Total BRL = R$ {impostos['ii']['brl']:,.2f} + R$ {impostos['ipi']['brl']:,.2f} + R$ {impostos['pis']['brl']:,.2f} + R$ {impostos['cofins']['brl']:,.2f} = R$ {total['brl']:,.2f}\n"
        
        if cotacao is not None:
            resposta += f"• Total USD = R$ {total['brl']:,.2f} ÷ {cotacao:,.4f} = USD {total['usd']:,.2f}\n\n"
        else:
            resposta += f"• Total USD = Não calculado (cotação PTAX não informada)\n\n"
        
        resposta += f"**📋 Resumo Final:**\n"
        if cotacao is not None:
            resposta += f"• CIF: R$ {cif['brl']:,.2f} (USD {cif['usd']:,.2f})\n"
            resposta += f"• Total de Impostos: R$ {total['brl']:,.2f} (USD {total['usd']:,.2f})\n"
        else:
            resposta += f"• CIF: USD {cif['usd']:,.2f} (BRL não calculado - cotação não informada)\n"
            resposta += f"• Total de Impostos: BRL não calculado (cotação PTAX não informada)\n"
        
        return resposta
    
    def calcular_percentual(self, valor: float, percentual: float) -> Dict[str, Any]:
        """
        Calcula percentual de um valor.
        
        Args:
            valor: Valor base
            percentual: Percentual a calcular (ex: 1.5 para 1,5%)
            
        Returns:
            Dict com resultado do cálculo
        """
        try:
            resultado_valor = valor * (percentual / 100.0)
            
            return {
                'sucesso': True,
                'valor_base': round(valor, 2),
                'percentual': round(percentual, 2),
                'resultado': round(resultado_valor, 2),
                'explicacao': f"{percentual}% de {valor:,.2f} = {resultado_valor:,.2f}"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao calcular percentual: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def calcular_afrmm(
        self,
        frete_usd: float,
        aliquota_afrmm: float,
        cotacao_ptax: float
    ) -> Dict[str, Any]:
        """
        Calcula AFRMM (Adicional ao Frete para Renovação da Marinha Mercante).
        
        Args:
            frete_usd: Valor do frete em USD
            aliquota_afrmm: Alíquota de AFRMM em percentual (ex: 10.0 para 10%)
            cotacao_ptax: Cotação PTAX (R$ / USD)
            
        Returns:
            Dict com resultado do cálculo
        """
        try:
            afrmm_usd = frete_usd * (aliquota_afrmm / 100.0)
            afrmm_brl = afrmm_usd * cotacao_ptax
            
            return {
                'sucesso': True,
                'frete_usd': round(frete_usd, 2),
                'aliquota_afrmm': round(aliquota_afrmm, 2),
                'afrmm': {
                    'usd': round(afrmm_usd, 2),
                    'brl': round(afrmm_brl, 2)
                },
                'explicacao': f"AFRMM = Frete USD {frete_usd:,.2f} × {aliquota_afrmm}% = USD {afrmm_usd:,.2f} (R$ {afrmm_brl:,.2f})"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao calcular AFRMM: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }
    
    def calcular_fob(
        self,
        cif_usd: float,
        frete_usd: float,
        seguro_usd: float
    ) -> Dict[str, Any]:
        """
        Calcula FOB (Free On Board) a partir de CIF.
        
        FOB = CIF - Frete - Seguro
        
        Args:
            cif_usd: Valor CIF em USD
            frete_usd: Valor do frete em USD
            seguro_usd: Valor do seguro em USD
            
        Returns:
            Dict com resultado do cálculo
        """
        try:
            fob_usd = cif_usd - frete_usd - seguro_usd
            
            return {
                'sucesso': True,
                'cif_usd': round(cif_usd, 2),
                'frete_usd': round(frete_usd, 2),
                'seguro_usd': round(seguro_usd, 2),
                'fob_usd': round(fob_usd, 2),
                'explicacao': f"FOB = CIF - Frete - Seguro = {cif_usd:,.2f} - {frete_usd:,.2f} - {seguro_usd:,.2f} = USD {fob_usd:,.2f}"
            }
        except Exception as e:
            logger.error(f"❌ Erro ao calcular FOB: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }

