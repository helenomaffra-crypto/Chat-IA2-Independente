"""
Service dedicado para operações de consulta de documentos e processos.

Este service centraliza a lógica de consulta de CE, verificação de atualização
e consulta de processo consolidado, removendo essa responsabilidade do ChatService.
"""

import logging
import requests
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConsultaService:
    """
    Serviço para operações de consulta de documentos e processos.
    
    Responsabilidades:
    - Consultar CE marítimo
    - Verificar atualização de CE (API pública)
    - Consultar processo consolidado
    """

    def __init__(self, chat_service=None):
        """
        Args:
            chat_service: Referência opcional ao ChatService para acessar métodos auxiliares
        """
        self.chat_service = chat_service

    def verificar_atualizacao_ce(self, numero_ce: str) -> Dict[str, Any]:
        """
        Verifica se um CE precisa ser atualizado usando API pública (gratuita).
        
        Args:
            numero_ce: Número do CE
        
        Returns:
            Dict com resultado da verificação
        """
        numero_ce = (numero_ce or "").strip()
        
        if not numero_ce:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_ce é obrigatório'
            }
        
        try:
            from db_manager import buscar_ce_cache
            from datetime import datetime
            
            # 1. Buscar no cache
            ce_cache = buscar_ce_cache(numero_ce)
            
            if not ce_cache:
                # Não está no cache, precisa atualizar (bilhetar)
                return {
                    'sucesso': True,
                    'precisa_atualizar': True,
                    'motivo': 'CE não encontrado no cache',
                    'resposta': f"🔄 **CE {numero_ce} não está no cache.**\n\n💡 **Recomendação:** Precisa consultar API bilhetada para obter dados do CE.",
                    'acao_recomendada': 'consultar_ce_maritimo',
                    'custo_estimado': 'R$ 0,XX (consulta bilhetada necessária)'
                }
            
            # 2. Obter data do cache
            ultima_alteracao_cache = None
            if ce_cache.get('ultima_alteracao_api'):
                try:
                    ultima_alteracao_cache = datetime.fromisoformat(ce_cache['ultima_alteracao_api'])
                except (ValueError, TypeError):
                    pass
            
            # 3. Consultar API pública (gratuita) para verificar se há alteração
            try:
                # ⚠️ DESABILITADO: Módulo utils.siscarga_publica não existe
                # from utils.siscarga_publica import consultar_data_ultima_atualizacao
                # resultado_publica = consultar_data_ultima_atualizacao([numero_ce])
                # data_atualizacao_publica = resultado_publica.get(numero_ce)
                
                # Por enquanto, retornar que precisa atualizar se não tem data no cache
                if ultima_alteracao_cache is None:
                    return {
                        'sucesso': True,
                        'precisa_atualizar': True,
                        'motivo': 'Cache não tem data de última alteração',
                        'resposta': f"🔄 **CE {numero_ce} precisa ser atualizado.**\n\n💡 **Recomendação:** Consultar API bilhetada para obter dados atualizados.",
                        'acao_recomendada': 'consultar_ce_maritimo',
                        'custo_estimado': 'R$ 0,XX (consulta bilhetada necessária)',
                        'data_cache': None,
                        'data_publica': None
                    }
                
                # Se tem data no cache, assumir que está atualizado (já que API pública não está disponível)
                return {
                    'sucesso': True,
                    'precisa_atualizar': False,
                    'motivo': 'CE está no cache (API pública não disponível para verificação)',
                    'resposta': f"✅ **CE {numero_ce} está no cache.**\n\n📅 **Última alteração:** {ultima_alteracao_cache.isoformat()}\n\n💡 **Recomendação:** Usar dados do cache (SEM custo).",
                    'acao_recomendada': 'usar_cache',
                    'custo_estimado': 'R$ 0,00 (usar cache, sem consulta bilhetada)',
                    'data_cache': ultima_alteracao_cache.isoformat(),
                    'data_publica': None
                }
                
            except Exception as e:
                logger.warning(f'Erro ao verificar atualização via API pública para CE {numero_ce}: {e}')
                # Em caso de erro, recomendar atualizar para garantir dados atualizados
                return {
                    'sucesso': True,
                    'precisa_atualizar': True,
                    'motivo': f'Erro ao verificar na API pública: {str(e)}',
                    'resposta': f"⚠️ **Erro ao verificar atualização do CE {numero_ce}.**\n\n💡 **Recomendação:** Consultar API bilhetada para garantir dados atualizados.",
                    'acao_recomendada': 'consultar_ce_maritimo',
                    'custo_estimado': 'R$ 0,XX (consulta bilhetada necessária)'
                }
                
        except Exception as e:
            logger.error(f'Erro ao verificar atualização do CE {numero_ce}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f"❌ **Erro ao verificar atualização do CE {numero_ce}:** {str(e)}"
            }

    def consultar_ce_maritimo(
        self,
        numero_ce: Optional[str] = None,
        processo_referencia: Optional[str] = None,
        usar_cache_apenas: bool = False,
        forcar_consulta_api: bool = False,
        mensagem_original: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Consulta CE marítimo.
        
        ✅ IMPORTANTE: Quando o usuário pede para "consultar", SEMPRE forçar consulta à API bilhetada.
        Suporta consulta via cache ou forçar atualização via API.
        
        Args:
            numero_ce: Número do CE (opcional se processo_referencia for fornecido)
            processo_referencia: Referência do processo (opcional se numero_ce for fornecido)
            usar_cache_apenas: Se True, usa apenas cache (sem bilhetar)
            forcar_consulta_api: Se True, força consulta à API bilhetada
            mensagem_original: Mensagem original do usuário (para contexto)
        
        Returns:
            Dict com resultado da consulta
        """
        numero_ce = (numero_ce or "").strip()
        processo_ref = (processo_referencia or "").strip()
        
        # ✅ IMPORTANTE: Quando o usuário pede para "consultar", SEMPRE forçar consulta à API bilhetada
        if not usar_cache_apenas:
            forcar_consulta_api = True
        
        # ✅ CORREÇÃO CRÍTICA: Se numero_ce foi fornecido explicitamente, IGNORAR processo_ref
        if numero_ce:
            processo_ref = ""  # Limpar processo_ref quando há CE específico
            logger.info(f'✅ CE específico {numero_ce} detectado - ignorando contexto de processo anterior')
        
        resposta_info = ""  # Inicializar variável
        if processo_ref and not numero_ce:
            # Expandir processo se necessário
            processo_completo = processo_ref
            if self.chat_service and hasattr(self.chat_service, '_extrair_processo_referencia'):
                processo_completo = self.chat_service._extrair_processo_referencia(processo_ref) or processo_ref
            
            # Buscar CEs vinculados ao processo
            try:
                from db_manager import obter_dados_documentos_processo
                dados_processo = obter_dados_documentos_processo(processo_completo)
                
                ces = dados_processo.get('ces', [])
                if not ces:
                    return {
                        'sucesso': False,
                        'erro': 'CE_NAO_ENCONTRADO_PROCESSO',
                        'resposta': f"⚠️ **Nenhum CE encontrado vinculado ao processo {processo_completo}.**\n\n💡 **Dica:** O processo pode não ter CE vinculado ou o CE ainda não foi consultado."
                    }
                
                # Usar o primeiro CE encontrado (geralmente há apenas um por processo)
                if len(ces) > 1:
                    numeros_ces = [ce.get('numero', 'N/A') for ce in ces]
                    resposta_info = f"ℹ️ **Processo {processo_completo} tem {len(ces)} CE(s) vinculado(s):** {', '.join(numeros_ces)}\n\n"
                    resposta_info += f"Consultando o primeiro CE: {numeros_ces[0]}\n\n"
                else:
                    resposta_info = f"ℹ️ **CE do processo {processo_completo}:**\n\n"
                
                numero_ce = ces[0].get('numero', '')
                if not numero_ce:
                    return {
                        'sucesso': False,
                        'erro': 'CE_SEM_NUMERO',
                        'resposta': f"⚠️ **CE encontrado no processo {processo_completo}, mas sem número válido.**"
                    }
            except Exception as e:
                logger.error(f'Erro ao buscar CE do processo {processo_completo}: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': 'ERRO_BUSCA_PROCESSO',
                    'resposta': f"❌ **Erro ao buscar CE do processo {processo_completo}:** {str(e)}"
                }
        elif not numero_ce and not processo_ref:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ É necessário fornecer numero_ce OU processo_referencia.'
            }
        
        # Validar formato do CE (CE é sempre numérico, geralmente 15 dígitos)
        if numero_ce:
            numero_ce_limpo = str(numero_ce).strip()
            # CE deve ser totalmente numérico e ter pelo menos 10 dígitos
            if not numero_ce_limpo.isdigit():
                return {
                    'sucesso': False,
                    'erro': 'FORMATO_INVALIDO',
                    'resposta': f'❌ Número de CE inválido: {numero_ce}. O CE deve ser numérico (apenas dígitos).'
                }
            if len(numero_ce_limpo) < 10 or len(numero_ce_limpo) > 15:
                return {
                    'sucesso': False,
                    'erro': 'FORMATO_INVALIDO',
                    'resposta': f'❌ Número de CE inválido: {numero_ce}. O CE deve ter entre 10 e 15 dígitos.'
                }
            # Usar número limpo (sem espaços)
            numero_ce = numero_ce_limpo
        
        try:
            # Consultar CE via endpoint (que já tem lógica de cache + API pública + API bilhetada)
            base_url = os.getenv('FLASK_BASE_URL', 'http://localhost:5500')
            url = f'{base_url}/api/int/integracomex/ce/{numero_ce}'
            
            # ✅ Se forçar consulta API, adicionar parâmetro para ignorar cache
            params = {}
            if forcar_consulta_api:
                params['forcar_atualizacao'] = 'true'
            
            if usar_cache_apenas:
                # Tentar usar cache primeiro
                from db_manager import buscar_ce_cache, obter_processo_por_documento
                ce_cache = buscar_ce_cache(numero_ce)
                if ce_cache:
                    processo_vinculado_cache = ce_cache.get('processo_referencia')
                    processo_vinculado_final = processo_vinculado_cache
                    
                    # Se não encontrou no cache, buscar na tabela processo_documentos
                    if not processo_vinculado_final:
                        try:
                            processo_encontrado = obter_processo_por_documento('CE', numero_ce)
                            if processo_encontrado:
                                processo_vinculado_final = processo_encontrado
                                logger.info(f'✅ Processo {processo_encontrado} encontrado na tabela processo_documentos para CE {numero_ce}')
                        except Exception as e:
                            logger.warning(f'Erro ao buscar processo por documento no cache: {e}')
                    
                    data = {
                        'sucesso': True,
                        'fonte': 'cache',
                        'dados': ce_cache['json_completo'],
                        'cache_info': {
                            'consultado_em': ce_cache.get('consultado_em'),
                            'atualizado_em': ce_cache.get('atualizado_em'),
                        },
                        'processo_vinculado': processo_vinculado_final,
                        'aviso': '✅ Dados retornados do cache (sem custo)'
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': 'CE_NAO_ENCONTRADO_CACHE',
                        'resposta': f"⚠️ **CE {numero_ce} não encontrado no cache local.**\n\n💡 **Dica:** O CE pode não estar no cache. Use `usar_cache_apenas: false` para consultar a API bilhetada (paga por consulta)."
                    }
            else:
                # Consultar via endpoint
                response = requests.get(url, params=params, timeout=30)
                data = response.json()
            
            if not data.get('sucesso'):
                erro = data.get('error', 'ERRO_DESCONHECIDO')
                mensagem = data.get('message', 'Erro ao consultar CE')
                
                if erro == 'CE_NAO_ENCONTRADO_CACHE':
                    resposta = f"⚠️ **CE {numero_ce} não encontrado no cache local.**\n\n"
                    if usar_cache_apenas:
                        resposta += "💡 **Dica:** Use `usar_cache_apenas: false` para consultar a API bilhetada (paga por consulta)."
                    else:
                        resposta += "💡 **Dica:** O CE pode não existir ou não estar no cache. Verifique o número do CE."
                else:
                    resposta = f"❌ **Erro ao consultar CE {numero_ce}:** {mensagem}"
                
                return {
                    'sucesso': False,
                    'resposta': resposta,
                    'erro': erro
                }
            
            # Formatar resposta com dados do CE
            ce_dados = data.get('dados', {})
            fonte = data.get('fonte', 'api')
            aviso = data.get('aviso', '')
            economia = data.get('economia', '')
            
            # ✅ Se foi consultado via processo, incluir informação
            resposta = ""
            if processo_ref and resposta_info:
                resposta += resposta_info
            
            resposta += f"📦 **CE {numero_ce}**\n\n"
            
            # ✅ PRIORIDADE: Situação e data da situação primeiro (informação principal)
            situacao_encontrada = False
            
            # Tentar diferentes estruturas possíveis para situação
            situacao = ce_dados.get('situacaoCarga') or ce_dados.get('situacao') or ce_dados.get('status', {}).get('situacao', '')
            if situacao:
                resposta += f"**Situação:** {situacao}\n"
                situacao_encontrada = True
            
            # Data da situação
            data_situacao = ce_dados.get('dataSituacaoCarga') or ce_dados.get('data_situacao') or ce_dados.get('status', {}).get('data', '')
            if data_situacao:
                try:
                    from datetime import datetime
                    if isinstance(data_situacao, str):
                        dt = datetime.fromisoformat(data_situacao.replace('Z', '+00:00'))
                        data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                    else:
                        data_formatada = str(data_situacao)
                    resposta += f"**Data da Situação:** {data_formatada}\n"
                except:
                    resposta += f"**Data da Situação:** {data_situacao}\n"
            
            # Porto de destino
            porto_destino = ce_dados.get('portoDestino') or ce_dados.get('porto_destino', '')
            if porto_destino:
                resposta += f"**Porto de Destino:** {porto_destino}\n"
            
            # Porto de origem
            porto_origem = ce_dados.get('portoOrigem') or ce_dados.get('porto_origem', '')
            if porto_origem:
                resposta += f"**Porto de Origem:** {porto_origem}\n"
            
            # Pendências
            pendencia_frete = ce_dados.get('indicadorPendenciaFrete') or ce_dados.get('pendencia_frete', False)
            pendencia_afrmm = ce_dados.get('pendenciaAFRMM') or ce_dados.get('pendencia_afrmm', False)
            
            if pendencia_frete or pendencia_afrmm:
                resposta += "\n⚠️ **Pendências:**\n"
                if pendencia_frete:
                    resposta += "  - Frete: Pendente\n"
                if pendencia_afrmm:
                    resposta += "  - AFRMM: Pendente\n"
            
            # Adicionar informações de fonte e economia
            if aviso:
                resposta += f"\n{aviso}\n"
            if economia:
                resposta += f"\n💰 {economia}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': ce_dados,
                'fonte': fonte,
                'numero_ce': numero_ce,
                'processo_vinculado': data.get('processo_vinculado')
            }
            
        except Exception as e:
            logger.error(f'Erro ao consultar CE {numero_ce}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f"❌ **Erro ao consultar CE {numero_ce}:** {str(e)}"
            }

    def consultar_processo_consolidado(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Consulta processo consolidado com todos os dados (DI, DUIMP, CE, CCT, pendências, valores).
        
        Args:
            processo_referencia: Referência do processo
        
        Returns:
            Dict com resultado da consulta formatado
        """
        processo_ref = (processo_referencia or "").strip()
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'processo_referencia é obrigatório'
            }
        
        # Expandir processo se necessário
        processo_completo = processo_ref
        if self.chat_service and hasattr(self.chat_service, '_extrair_processo_referencia'):
            processo_completo = self.chat_service._extrair_processo_referencia(processo_ref) or processo_ref
        
        try:
            # ✅ CORREÇÃO: Chamar função diretamente em vez de fazer requisição HTTP
            from db_manager import gerar_json_consolidado_processo
            
            json_consolidado = gerar_json_consolidado_processo(processo_completo)
            
            # Verificar se há erro no JSON consolidado
            if 'erro' in json_consolidado:
                logger.error(f'Erro ao gerar JSON consolidado: {json_consolidado.get("erro")}')
                return {
                    'sucesso': False,
                    'erro': 'ERRO_GERAR_CONSOLIDADO',
                    'mensagem': json_consolidado.get('erro', 'Erro ao gerar JSON consolidado')
                }
            
            # Se não houver erro, continuar com o processamento
            if json_consolidado:
                # Construir resposta formatada para a IA
                resposta = f"📋 **Processo {processo_completo}**\n\n"
                
                # ✅ CORREÇÃO: Mostrar todas as declarações (DI e DUIMP)
                declaracoes = json_consolidado.get('declaracoes', [])
                if not isinstance(declaracoes, list):
                    declaracao = json_consolidado.get('declaracao')
                    if isinstance(declaracao, dict):
                        declaracoes = [declaracao]
                    else:
                        declaracoes = []
                
                if not declaracoes:
                    declaracao = json_consolidado.get('declaracao')
                    if isinstance(declaracao, dict):
                        declaracoes = [declaracao]
                
                # Mostrar DI primeiro (se houver)
                di_encontrada = None
                duimp_encontrada = None
                for decl in declaracoes:
                    if not isinstance(decl, dict):
                        continue
                    if decl.get('tipo') == 'DI':
                        di_encontrada = decl
                    elif decl.get('tipo') == 'DUIMP':
                        duimp_encontrada = decl
                
                # Mostrar DI se houver
                if di_encontrada:
                    situacao_di = di_encontrada.get('situacao', '')
                    canal_di = di_encontrada.get('canal', '')
                    numero_protocolo = di_encontrada.get('numero_protocolo', '')
                    situacao_entrega = di_encontrada.get('situacao_entrega_carga', '')
                    modalidade = di_encontrada.get('modalidade', '')
                    datas_di = di_encontrada.get('datas', {})
                    
                    di_numero = json_consolidado.get('chaves', {}).get('di', '')
                    if di_numero:
                        resposta += f"📄 **DI {di_numero}:** {situacao_di.lower() if situacao_di else 'N/A'}\n"
                    else:
                        resposta += f"📄 **DI:** {situacao_di.lower() if situacao_di else 'N/A'}\n"
                    
                    if canal_di:
                        resposta += f"   - Canal: {canal_di}\n"
                    if numero_protocolo:
                        resposta += f"   - Protocolo: {numero_protocolo}\n"
                    if situacao_entrega:
                        resposta += f"   - Situação de Entrega: {situacao_entrega}\n"
                    if modalidade and modalidade != 'NORMAL':
                        resposta += f"   - Modalidade: {modalidade}\n"
                    
                    # Datas importantes
                    if isinstance(datas_di, dict):
                        for data_key, data_value in datas_di.items():
                            if data_value:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(data_value.replace('Z', '+00:00'))
                                    data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                                    label = {
                                        'registro': 'Data de Registro',
                                        'desembaraco': 'Data de Desembaraço',
                                        'autorizacao_entrega': 'Data de Autorização de Entrega',
                                        'situacao_atualizada_em': 'Situação Atualizada em'
                                    }.get(data_key, data_key)
                                    resposta += f"   - {label}: {data_formatada}\n"
                                except:
                                    resposta += f"   - {data_key}: {data_value}\n"
                    
                    resposta += "\n"
                
                # Mostrar DUIMP se houver
                if duimp_encontrada:
                    situacao_duimp = duimp_encontrada.get('situacao', '')
                    canal_duimp = duimp_encontrada.get('canal', '')
                    duimp_numero = json_consolidado.get('chaves', {}).get('duimp_num', '')
                    if duimp_numero:
                        resposta += f"⚠️ **DUIMP {duimp_numero}:** {situacao_duimp.lower() if situacao_duimp else 'N/A'}\n"
                    else:
                        resposta += f"⚠️ **DUIMP:** {situacao_duimp.lower() if situacao_duimp else 'N/A'}\n"
                    if canal_duimp:
                        resposta += f"Canal {canal_duimp}\n"
                    resposta += "\n"
                
                # Pendências
                pendencias = json_consolidado.get('pendencias', {})
                if pendencias.get('frete'):
                    resposta += f"esta com pendencia de frete\n"
                else:
                    resposta += f"nao tem pendencia de frete\n"
                
                if pendencias.get('afrmm'):
                    resposta += f"tem pendencia de afrmm\n"
                else:
                    resposta += f"nao tem pendencia de afrmm\n"
                
                # CEs
                ces = json_consolidado.get('chaves', {}).get('ce_house') or json_consolidado.get('chaves', {}).get('ce_master')
                if ces:
                    resposta += f"\n📦 **Conhecimentos de Embarque (CE):**\n"
                    if json_consolidado.get('chaves', {}).get('ce_house'):
                        ce_num = json_consolidado['chaves']['ce_house']
                        # Buscar situação do CE
                        for leg in json_consolidado.get('movimentacao', {}).get('legs', []):
                            if leg.get('fonte') == 'CE':
                                situacao = leg.get('status', {}).get('situacao', '')
                                resposta += f"CE {ce_num}\n"
                                resposta += f"- Situação: {situacao}\n"
                                break
                
                # CCTs
                legs = json_consolidado.get('movimentacao', {}).get('legs', [])
                ccts_legs = [leg for leg in legs if leg.get('fonte') == 'CCT']
                if ccts_legs:
                    resposta += f"\n📦 **Conhecimentos de Carga Aérea (CCT):**\n"
                    try:
                        from db_manager import listar_documentos_processo
                        documentos = listar_documentos_processo(processo_completo)
                        ccts = [doc for doc in documentos if doc.get('tipo_documento') == 'CCT']
                        for i, leg in enumerate(ccts_legs):
                            situacao = leg.get('status', {}).get('situacao', '')
                            if i < len(ccts):
                                cct_num = ccts[i].get('numero_documento', '')
                                resposta += f"CCT {cct_num}\n"
                            else:
                                resposta += f"CCT\n"
                            resposta += f"- Situação: {situacao}\n"
                    except Exception as e:
                        logger.warning(f'Erro ao buscar CCTs do processo {processo_completo}: {e}')
                        for leg in ccts_legs:
                            situacao = leg.get('status', {}).get('situacao', '')
                            resposta += f"CCT\n"
                            resposta += f"- Situação: {situacao}\n"
                
                # ✅ Adicionar valores (CIF, FOB, frete, seguro) e tributos
                valores = json_consolidado.get('valores', {})
                if valores:
                    cif = valores.get('cif', {})
                    fob = valores.get('fob', {})
                    frete = valores.get('frete', {})
                    seguro = valores.get('seguro', {})
                    
                    cif_brl = cif.get('brl', 0) if cif else 0
                    fob_brl = fob.get('brl', 0) if fob else 0
                    frete_brl = frete.get('brl', 0) if frete else 0
                    seguro_brl = seguro.get('brl', 0) if seguro else 0
                    
                    # Se temos valores separados (FOB, frete, seguro)
                    if fob_brl > 0 or frete_brl > 0 or seguro_brl > 0:
                        if cif_brl > 0:
                            resposta += f"\n💰 **Valor CIF:** R$ {cif_brl:,.2f}\n"
                            fob_calculado = valores.get('fob', {}).get('calculado', False)
                            if fob_calculado:
                                resposta += f"   (CIF = FOB + Frete + Seguro)\n"
                        else:
                            cif_calculado = fob_brl + frete_brl + seguro_brl
                            if cif_calculado > 0:
                                resposta += f"\n💰 **Valor CIF:** R$ {cif_calculado:,.2f}\n"
                                resposta += f"   (CIF = FOB + Frete + Seguro)\n"
                        
                        if fob_brl > 0:
                            fob_info = valores.get('fob', {})
                            fob_calculado = fob_info.get('calculado', False) if fob_info else False
                            if fob_calculado:
                                resposta += f"   - FOB: R$ {fob_brl:,.2f} (calculado: CIF - frete - seguro)\n"
                            else:
                                resposta += f"   - FOB: R$ {fob_brl:,.2f}\n"
                        if frete_brl > 0:
                            resposta += f"   - Frete: R$ {frete_brl:,.2f}\n"
                        if seguro_brl > 0:
                            resposta += f"   - Seguro: R$ {seguro_brl:,.2f}\n"
                    elif cif_brl > 0:
                        # Só temos CIF (sem componentes separados)
                        resposta += f"\n💰 **Valor CIF:** R$ {cif_brl:,.2f}\n"
                
                # Tributos
                tributos = json_consolidado.get('tributos', [])
                if tributos:
                    resposta += f"\n💳 **Tributos:**\n"
                    for tributo in tributos:
                        # ✅ CORREÇÃO: Verificar se tributo é um dicionário antes de usar .get()
                        if isinstance(tributo, dict):
                            tipo = tributo.get('tipo', '')
                            valor = tributo.get('valor', 0)
                            if tipo and valor > 0:
                                resposta += f"   - {tipo}: R$ {valor:,.2f}\n"
                        elif isinstance(tributo, str):
                            # Se for string, apenas exibir
                            resposta += f"   - {tributo}\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': json_consolidado,
                    'processo_referencia': processo_completo
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'PROCESSO_NAO_ENCONTRADO',
                    'mensagem': f'Processo {processo_completo} não encontrado'
                }
                
        except Exception as e:
            logger.error(f'Erro ao consultar processo consolidado {processo_completo}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro ao consultar processo consolidado: {str(e)}'
            }












