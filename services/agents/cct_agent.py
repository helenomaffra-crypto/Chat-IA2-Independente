"""
Agente responsável por operações relacionadas a CCT (Conhecimento de Carga Aérea).
"""
import logging
import json
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from ..utils.extractors import extract_processo_referencia

logger = logging.getLogger(__name__)


class CctAgent(BaseAgent):
    """
    Agente responsável por operações relacionadas a CCT (Conhecimento de Carga Aérea).
    
    Tools suportadas:
    - consultar_cct: Consulta CCT (Conhecimento de Carga Aérea)
    - obter_extrato_cct: Obtém extrato completo do CCT
    
    ✅ IMPORTANTE: Nesta aplicação NÃO vinculamos manualmente. O sistema busca automaticamente o processo vinculado.
    """
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            'consultar_cct': self._consultar_cct,
            # 'vincular_processo_cct': self._vincular_processo_cct,  # ✅ DESABILITADO: Nesta aplicação não vinculamos manualmente
            'obter_extrato_cct': self._obter_extrato_cct,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada neste agente',
                'resposta': f'❌ Tool "{tool_name}" não está disponível no CctAgent.'
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
    
    def _consultar_cct(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta CCT (Conhecimento de Carga Aérea).
        
        ✅ IMPORTANTE: 
        - A API de CCT NÃO é bilhetada (é gratuita).
        - CCT não tem número próprio - o identificador é o RUC (vem da resposta da API).
        - Para consultar o CCT, usa-se o AWB (Air Waybill).
        - No Kanban, o AWB está no campo bl_house quando modal é "Aéreo".
        - Na DUIMP, o AWB entra como número do conhecimento de embarque (código 30).
        
        Suporta consulta via cache ou atualização via API.
        """
        numero_cct = arguments.get('numero_cct', '').strip()
        processo_ref = arguments.get('processo_referencia', '').strip()
        usar_cache_apenas = arguments.get('usar_cache_apenas', False)
        mensagem_original = context.get('mensagem_original') if context else None
        
        # ✅ NOVO: Se processo_referencia foi fornecido, buscar CCT vinculado ao processo
        resposta_info = ""
        if processo_ref and not numero_cct:
            processo_completo = extract_processo_referencia(processo_ref)
            if not processo_completo:
                processo_completo = processo_ref
            
            # ✅ CORREÇÃO: Se o processo não foi encontrado com o ano fornecido, tentar buscar sem o ano
            # ou com o ano atual (pode ser que o usuário digitou o ano errado)
            processo_original = processo_completo
            
            # Buscar CCTs vinculados ao processo
            try:
                from db_manager import obter_dados_documentos_processo, get_db_connection
                import sqlite3
                
                dados_processo = obter_dados_documentos_processo(processo_completo)
                
                ccts = dados_processo.get('ccts', [])
                
                # ✅ NOVO: Se não encontrou CCT vinculado, buscar AWB do processo (para processos aéreos)
                # IMPORTANTE: No Kanban, bl_house contém AWB quando modal é "Aéreo"
                # O AWB é usado para consultar o CCT na API (o CCT não tem número próprio, usa RUC)
                if not ccts:
                    # Buscar processo no Kanban para pegar o AWB
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # ✅ CORREÇÃO: Tentar buscar primeiro com o processo exato, depois com variações (ano errado)
                    cursor.execute('''
                        SELECT modal, bl_house, dados_completos_json, processo_referencia
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                        LIMIT 1
                    ''', (processo_completo,))
                    row = cursor.fetchone()
                    
                    # Se não encontrou, tentar buscar sem o ano ou com variações (pode ser que o usuário digitou o ano errado)
                    if not row:
                        # Tentar buscar pelo prefixo e número (ignorando o ano)
                        prefixo_numero = processo_completo.split('/')[0] if '/' in processo_completo else processo_completo
                        cursor.execute('''
                            SELECT modal, bl_house, dados_completos_json, processo_referencia
                            FROM processos_kanban
                            WHERE processo_referencia LIKE ?
                            ORDER BY processo_referencia DESC
                            LIMIT 1
                        ''', (f'{prefixo_numero}%',))
                        row = cursor.fetchone()
                        if row:
                            processo_completo = row['processo_referencia']  # Usar o processo encontrado
                            logger.info(f'✅ Processo encontrado com variação de ano: {processo_ref} -> {processo_completo}')
                    
                    conn.close()
                    
                    if row:
                        modal = row['modal'] or ''
                        bl_house = row['bl_house']
                        
                        # Se o processo é aéreo, bl_house contém o AWB (não BL)
                        if ('AÉREO' in modal.upper() or 'AEREO' in modal.upper()):
                            if bl_house:
                                # Para processos aéreos, bl_house é o AWB
                                numero_cct = bl_house
                                logger.info(f'✅ AWB encontrado no campo bl_house do processo {processo_completo} (modal aéreo): {numero_cct}')
                            else:
                                # Tentar extrair do JSON completo como fallback
                                try:
                                    dados_json = json.loads(row['dados_completos_json']) if row['dados_completos_json'] else {}
                                    numero_cct = dados_json.get('awbBl') or dados_json.get('awb') or dados_json.get('blHouseNovo')
                                    if numero_cct:
                                        logger.info(f'✅ AWB encontrado no JSON do processo {processo_completo}: {numero_cct}')
                                except:
                                    pass
                
                # Se ainda não encontrou, usar CCTs vinculados
                if not numero_cct and ccts:
                    # Usar o primeiro CCT encontrado
                    if len(ccts) > 1:
                        numeros_ccts = [cct.get('numero', 'N/A') for cct in ccts]
                        resposta_info = f"ℹ️ **Processo {processo_completo} tem {len(ccts)} CCT(s) vinculado(s):** {', '.join(numeros_ccts)}\n\n"
                        resposta_info += f"Consultando o primeiro CCT: {numeros_ccts[0]}\n\n"
                    else:
                        resposta_info = f"ℹ️ **CCT do processo {processo_completo}:**\n\n"
                    
                    numero_cct = ccts[0].get('numero', '')
                
                if not numero_cct:
                    return {
                        'sucesso': False,
                        'erro': 'CCT_NAO_ENCONTRADO_PROCESSO',
                        'resposta': f"⚠️ **Nenhum CCT (AWB) encontrado para o processo {processo_completo}.**\n\n💡 **Dica:** O processo pode não ter AWB informado ou não é um processo aéreo."
                    }
            except Exception as e:
                logger.error(f'Erro ao buscar CCT do processo {processo_completo}: {e}')
                return {
                    'sucesso': False,
                    'erro': 'ERRO_BUSCA_PROCESSO',
                    'resposta': f"❌ **Erro ao buscar CCT do processo {processo_completo}:** {str(e)}"
                }
        elif not numero_cct and not processo_ref:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ É necessário fornecer numero_cct OU processo_referencia.'
            }
        
        try:
            # Consultar CCT via função do db_manager ou endpoint
            if usar_cache_apenas:
                from db_manager import buscar_cct_cache, obter_processo_por_documento
                cct_cache = buscar_cct_cache(numero_cct)
                if cct_cache:
                    processo_vinculado_cache = cct_cache.get('processo_referencia')
                    processo_vinculado_final = processo_vinculado_cache
                    
                    if not processo_vinculado_final:
                        try:
                            processo_encontrado = obter_processo_por_documento('CCT', numero_cct)
                            if processo_encontrado:
                                processo_vinculado_final = processo_encontrado
                                logger.info(f'✅ Processo {processo_encontrado} encontrado na tabela processo_documentos para CCT {numero_cct}')
                        except Exception as e:
                            logger.warning(f'Erro ao buscar processo por documento no cache: {e}')
                    
                    data = {
                        'sucesso': True,
                        'fonte': 'cache',
                        'dados': cct_cache['json_completo'],
                        'cache_info': {
                            'consultado_em': cct_cache.get('consultado_em'),
                            'atualizado_em': cct_cache.get('atualizado_em'),
                        },
                        'processo_vinculado': processo_vinculado_final,
                        'aviso': '✅ Dados retornados do cache (sem custo)'
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': 'CCT_NAO_ENCONTRADO_CACHE',
                        'resposta': f"⚠️ **CCT {numero_cct} não encontrado no cache local.**\n\n💡 **Dica:** O CCT pode não estar no cache. A API de CCT é gratuita, então pode ser consultado sem custo."
                    }
            else:
                # ✅ Consultar via call_portal (mesma API da DUIMP)
                # A API CCTA usa o mesmo sistema de autenticação da DUIMP
                from utils.portal_proxy import call_portal
                
                # Path correto da API CCTA no Portal Único (confirmado no projeto DUIMP)
                path = '/ccta/api/ext/conhecimentos'
                params = {'numeroConhecimento': numero_cct}
                
                logger.info(f'🔍 Consultando CCT {numero_cct} via API Portal Único (CCTA)...')
                status_code, response_data = call_portal(path, query=params)
                
                # Processar resposta da API
                if status_code == 200:
                    # Verificar se é uma lista (resposta direta da API)
                    if isinstance(response_data, list):
                        # API retornou lista diretamente - tratar como sucesso
                        data = {
                            'sucesso': True,
                            'dados': response_data,
                            'fonte': 'api'
                        }
                    elif isinstance(response_data, dict):
                        # É um dict - pode ter estrutura {'sucesso': True, 'dados': [...]} ou {'error': ...}
                        data = response_data
                    else:
                        # Tipo inesperado
                        return {
                            'sucesso': False,
                            'erro': 'FORMATO_INESPERADO',
                            'resposta': f'❌ **Erro:** Resposta da API em formato inesperado.'
                        }
                elif status_code == 404:
                    # CCT não encontrado
                    return {
                        'sucesso': False,
                        'erro': 'CCT_NAO_ENCONTRADO',
                        'resposta': f"⚠️ **CCT {numero_cct} não encontrado na API.**\n\n💡 **Dica:** Verifique se o número do AWB está correto."
                    }
                else:
                    # Outro erro da API
                    error_msg = response_data if isinstance(response_data, str) else (response_data.get('mensagem', '') if isinstance(response_data, dict) else str(response_data))
                    logger.error(f'❌ Erro ao consultar CCT {numero_cct}: Status {status_code}, Mensagem: {error_msg}')
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_API',
                        'resposta': f"❌ **Erro ao consultar CCT na API:** Status {status_code}\n\n**Detalhes:** {error_msg}"
                    }
            
            # Verificar se houve erro
            if not data.get('sucesso', True):  # Default True se não tiver campo 'sucesso'
                erro = data.get('error', 'ERRO_DESCONHECIDO')
                mensagem = data.get('message', 'Erro ao consultar CCT')
                
                if erro == 'CCT_NAO_ENCONTRADO_CACHE':
                    resposta = f"⚠️ **CCT {numero_cct} não encontrado no cache local.**\n\n"
                    if usar_cache_apenas:
                        resposta += "💡 **Dica:** A API de CCT é gratuita, então pode ser consultado sem custo."
                    else:
                        resposta += "💡 **Dica:** O CCT pode não existir ou não estar no cache. Verifique o número do CCT."
                else:
                    resposta = f"❌ **Erro ao consultar CCT {numero_cct}:** {mensagem}"
                
                return {
                    'sucesso': False,
                    'resposta': resposta,
                    'erro': erro
                }
            
            # Formatar resposta com dados do CCT
            cct_dados_raw = data.get('dados', data if isinstance(data, (list, dict)) else {})
            
            # ✅ CORREÇÃO: CCT pode vir como array (primeiro item) ou objeto único
            if isinstance(cct_dados_raw, list):
                if len(cct_dados_raw) > 0:
                    cct_dados = cct_dados_raw[0] if isinstance(cct_dados_raw[0], dict) else {}
                else:
                    return {
                        'sucesso': False,
                        'erro': 'CCT_NAO_ENCONTRADO',
                        'resposta': f'❌ **CCT {numero_cct} não encontrado.**'
                    }
            elif isinstance(cct_dados_raw, dict):
                cct_dados = cct_dados_raw
            else:
                return {
                    'sucesso': False,
                    'erro': 'FORMATO_INVALIDO',
                    'resposta': f'❌ **Erro:** Dados do CCT em formato inválido.'
                }
            
            fonte = data.get('fonte', 'api')
            aviso = data.get('aviso', '')
            
            resposta = ""
            if processo_ref and resposta_info:
                resposta += resposta_info
            
            # Extrair identificação do CCT
            identificacao = cct_dados.get('identificacao', numero_cct)
            ruc = cct_dados.get('ruc', '')
            
            resposta += f"✈️ **CCT {identificacao}**\n"
            if ruc:
                resposta += f"**RUC:** {ruc}\n"
            resposta += "\n"
            
            # ✅ PRIORIDADE: Situação e data da situação primeiro
            situacao_encontrada = False
            
            # Situação pode estar em várias estruturas
            # 1. partesEstoque[0].situacaoAtual (mais atual)
            partes_estoque = cct_dados.get('partesEstoque', [])
            if partes_estoque and isinstance(partes_estoque, list) and len(partes_estoque) > 0:
                parte_estoque = partes_estoque[0]
                situacao_atual = parte_estoque.get('situacaoAtual', '')
                data_hora_situacao = parte_estoque.get('dataHoraSituacaoAtual', '')
                
                if situacao_atual:
                    resposta += f"**Situação:** {situacao_atual}\n"
                    situacao_encontrada = True
                    if data_hora_situacao:
                        resposta += f"**Data/Hora da Situação:** {data_hora_situacao}\n"
                    resposta += "\n"
            
            # 2. situacao direto no objeto (código)
            if not situacao_encontrada:
                situacao_codigo = cct_dados.get('situacao', '')
                if situacao_codigo:
                    # Converter código para descrição
                    situacoes_map = {
                        'A': 'Ativo',
                        'C': 'Cancelado',
                        'F': 'Finalizado'
                    }
                    situacao_desc = situacoes_map.get(situacao_codigo, situacao_codigo)
                    resposta += f"**Situação:** {situacao_desc}\n"
                    situacao_encontrada = True
            
            if not situacao_encontrada:
                resposta += "⚠️ **Situação:** Não disponível\n\n"
            
            # Informações secundárias
            if cct_dados.get('codigoAeroportoOrigemConhecimento'):
                resposta += f"**Aeroporto Origem:** {cct_dados.get('codigoAeroportoOrigemConhecimento')}\n"
            if cct_dados.get('codigoAeroportoDestinoConhecimento'):
                resposta += f"**Aeroporto Destino:** {cct_dados.get('codigoAeroportoDestinoConhecimento')}\n"
            if cct_dados.get('dataEmissao'):
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(cct_dados['dataEmissao'].replace('Z', '+00:00'))
                    resposta += f"**Data de Emissão:** {dt.strftime('%d/%m/%Y')}\n"
                except:
                    resposta += f"**Data de Emissão:** {cct_dados.get('dataEmissao')}\n"
            
            # Viagens associadas
            viagens_associadas = cct_dados.get('viagensAssociadas', [])
            if viagens_associadas:
                viagem = viagens_associadas[0] if len(viagens_associadas) > 0 else None
                if viagem:
                    identificacao_viagem = viagem.get('identificacaoViagem', '')
                    data_chegada = viagem.get('dataHoraChegadaEfetiva', '')
                    aeroporto_chegada = viagem.get('aeroportoChegada', '')
                    
                    if identificacao_viagem:
                        resposta += f"\n**✈️ Viagem:** {identificacao_viagem}\n"
                    if data_chegada:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(data_chegada.replace('Z', '+00:00'))
                            resposta += f"**Data/Hora Chegada:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                        except:
                            resposta += f"**Data/Hora Chegada:** {data_chegada}\n"
                    if aeroporto_chegada:
                        resposta += f"**Aeroporto Chegada:** {aeroporto_chegada}\n"
            
            # Documentos de saída (DI/DUIMP vinculados)
            documentos_saida = cct_dados.get('documentosSaida', [])
            if documentos_saida:
                resposta += f"\n**📄 Documentos Vinculados:**\n"
                for doc_saida in documentos_saida:
                    tipo_doc = doc_saida.get('tipo', '')
                    numero_doc = doc_saida.get('numero', '')
                    situacao_duimp = doc_saida.get('situacaoDuimp', '')
                    
                    if tipo_doc == '10':
                        tipo_nome = 'DI'
                    elif tipo_doc == '30':
                        tipo_nome = 'DTA'
                    else:
                        tipo_nome = f'Tipo {tipo_doc}'
                    
                    resposta += f"   - {tipo_nome} {numero_doc}"
                    if situacao_duimp:
                        resposta += f" (Situação DUIMP: {situacao_duimp})"
                    resposta += "\n"
            
            # Bloqueios
            bloqueios_ativos = cct_dados.get('bloqueiosAtivos', [])
            bloqueios_baixados = cct_dados.get('bloqueiosBaixados', [])
            if bloqueios_ativos:
                resposta += f"\n⚠️ **Bloqueios Ativos:** {len(bloqueios_ativos)}\n"
                for bloqueio in bloqueios_ativos[:3]:  # Mostrar até 3
                    tipo_bloqueio = bloqueio.get('tipoBloqueio', '')
                    if tipo_bloqueio:
                        resposta += f"   - {tipo_bloqueio}\n"
            if bloqueios_baixados:
                resposta += f"✅ **Bloqueios Baixados:** {len(bloqueios_baixados)}\n"
            
            # Frete (se disponível)
            frete = cct_dados.get('frete', {})
            if frete:
                somatorio_frete = frete.get('somatorioFretePorItemCarga', {})
                if somatorio_frete:
                    valor_frete = somatorio_frete.get('valor', 0)
                    moeda = somatorio_frete.get('moeda', {})
                    moeda_codigo = moeda.get('codigo', 'USD') if isinstance(moeda, dict) else 'USD'
                    if valor_frete:
                        resposta += f"\n💰 **Frete:** {moeda_codigo} {valor_frete:,.2f}\n"
            
            # Fonte e avisos
            if fonte == 'api':
                resposta += f"\n✅ **Consulta realizada** (API gratuita - dados atualizados)\n"
            elif fonte == 'cache':
                resposta += f"\n💾 **Dados do cache** (consulte novamente para atualizar)\n"
            
            # Processo vinculado
            processo_vinculado = data.get('processo_vinculado')
            if processo_vinculado:
                resposta += f"\n✅ **Processo Vinculado:** {processo_vinculado}\n"
            # ✅ REMOVIDO: Não mostrar mensagem de "processo não vinculado" - sistema busca automaticamente
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': cct_dados,
                'fonte': fonte,
                'processo_vinculado': processo_vinculado
            }
            
        except Exception as e:
            logger.error(f'Erro ao consultar CCT {numero_cct}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro ao consultar CCT: {str(e)}'
            }
    
    def _vincular_processo_cct(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Vincula CCT a um processo.
        
        ✅ IMPORTANTE: Cada processo deve ter apenas um CCT.
        Desvincula CCTs existentes antes de vincular o novo.
        """
        numero_cct = arguments.get('numero_cct', '').strip()
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        if not numero_cct:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Número do CCT é obrigatório.'
            }
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = extract_processo_referencia(processo_ref)
        if not processo_completo:
            processo_completo = processo_ref
        
        # ✅ IMPORTANTE: Cada processo deve ter apenas um CCT
        # Desvincular todos os CCTs existentes do processo antes de vincular o novo
        try:
            from db_manager import desvincular_todos_documentos_tipo, listar_documentos_processo, atualizar_processo_cct_cache, buscar_cct_cache, vincular_documento_processo
            
            ccts_existentes = [doc for doc in listar_documentos_processo(processo_completo) if doc.get('tipo_documento') == 'CCT']
            if ccts_existentes:
                desvinculados = desvincular_todos_documentos_tipo(processo_completo, 'CCT')
                if desvinculados > 0:
                    logger.info(f'✅ {desvinculados} CCT(s) antigo(s) desvinculado(s) do processo {processo_completo} antes de vincular o novo')
            
            # ✅ CORREÇÃO: Normalizar número do CCT (aceitar com ou sem hífen)
            # Tentar buscar com o formato fornecido primeiro
            cct_cache = buscar_cct_cache(numero_cct)
            
            # Se não encontrou, tentar formatos alternativos
            if not cct_cache:
                # Tentar sem hífen (se tinha hífen)
                numero_cct_alternativo = numero_cct.replace('-', '')
                if numero_cct_alternativo != numero_cct:
                    cct_cache = buscar_cct_cache(numero_cct_alternativo)
                    if cct_cache:
                        numero_cct = numero_cct_alternativo  # Usar formato encontrado
                        logger.info(f'✅ CCT encontrado no formato alternativo (sem hífen): {numero_cct}')
            
            # Se ainda não encontrou, tentar com hífen (se não tinha)
            if not cct_cache:
                # Tentar adicionar hífen após 3 letras (ex: MIA4673 -> MIA-4673)
                if len(numero_cct) > 3 and numero_cct[3] != '-':
                    numero_cct_alternativo = f"{numero_cct[:3]}-{numero_cct[3:]}"
                    cct_cache = buscar_cct_cache(numero_cct_alternativo)
                    if cct_cache:
                        numero_cct = numero_cct_alternativo  # Usar formato encontrado
                        logger.info(f'✅ CCT encontrado no formato alternativo (com hífen): {numero_cct}')
            
            if not cct_cache:
                return {
                    'sucesso': False,
                    'erro': 'CCT_NAO_ENCONTRADO_CACHE',
                    'resposta': f"⚠️ **CCT {numero_cct} não encontrado no cache.**\n\n💡 **Dica:** É necessário consultar o CCT primeiro antes de vincular a um processo."
                }
            
            # Vincular processo ao CCT
            vincular_documento_processo(processo_completo, 'CCT', numero_cct)
            
            # Atualizar também o cache do CCT
            sucesso = atualizar_processo_cct_cache(numero_cct, processo_completo)
            
            if sucesso:
                resposta = f"✅ **Processo vinculado com sucesso!**\n\n"
                resposta += f"**CCT:** {numero_cct}\n"
                resposta += f"**Processo:** {processo_completo}\n\n"
                resposta += f"🎯 **Pronto para gerar DUIMP!** O CCT está vinculado ao processo e pode ser usado para criar a Declaração Única de Importação."
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'processo': processo_completo,
                    'cct': numero_cct
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_VINCULACAO',
                    'resposta': f"❌ **Erro ao vincular processo {processo_completo} ao CCT {numero_cct}.**"
                }
                
        except Exception as e:
            logger.error(f'Erro ao vincular processo ao CCT: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro interno ao vincular processo: {str(e)}'
            }
    
    def _obter_extrato_cct(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Obtém extrato completo do CCT, consultando diretamente a API CCTA.
        
        ✅ IMPORTANTE: A API de CCT é GRATUITA (não bilhetada).
        Use quando o usuário pedir explicitamente "extrato CCT" ou "extrato do CCT".
        """
        numero_cct = arguments.get('numero_cct', '').strip()
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        # Se processo_referencia foi fornecido, buscar CCT vinculado ao processo
        if processo_ref and not numero_cct:
            processo_completo = extract_processo_referencia(processo_ref)
            if not processo_completo:
                processo_completo = processo_ref
            
            try:
                from db_manager import obter_dados_documentos_processo, get_db_connection
                import sqlite3
                
                # Primeiro tentar buscar dos documentos vinculados
                dados_processo = obter_dados_documentos_processo(processo_completo)
                ccts = dados_processo.get('ccts', [])
                
                if ccts:
                    numero_cct = ccts[0].get('numero', '')
                else:
                    # ✅ NOVO: Se não encontrou CCT vinculado, buscar AWB do processo (para processos aéreos)
                    # IMPORTANTE: No Kanban, bl_house contém AWB quando modal é "Aéreo"
                    # O AWB é usado para consultar o CCT na API (o CCT não tem número próprio, usa RUC)
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # ✅ CORREÇÃO: Tentar buscar primeiro com o processo exato, depois com variações (ano errado)
                    cursor.execute('''
                        SELECT modal, bl_house, dados_completos_json, processo_referencia
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                        LIMIT 1
                    ''', (processo_completo,))
                    row = cursor.fetchone()
                    
                    # Se não encontrou, tentar buscar sem o ano ou com variações (pode ser que o usuário digitou o ano errado)
                    if not row:
                        # Tentar buscar pelo prefixo e número (ignorando o ano)
                        prefixo_numero = processo_completo.split('/')[0] if '/' in processo_completo else processo_completo
                        cursor.execute('''
                            SELECT modal, bl_house, dados_completos_json, processo_referencia
                            FROM processos_kanban
                            WHERE processo_referencia LIKE ?
                            ORDER BY processo_referencia DESC
                            LIMIT 1
                        ''', (f'{prefixo_numero}%',))
                        row = cursor.fetchone()
                        if row:
                            processo_completo = row['processo_referencia']  # Usar o processo encontrado
                            logger.info(f'✅ Processo encontrado com variação de ano: {processo_ref} -> {processo_completo}')
                    
                    conn.close()
                    
                    if row:
                        modal = row['modal'] or ''
                        bl_house = row['bl_house']
                        
                        # Se o processo é aéreo, bl_house contém o AWB (não BL)
                        if ('AÉREO' in modal.upper() or 'AEREO' in modal.upper()):
                            if bl_house:
                                # Para processos aéreos, bl_house é o AWB
                                numero_cct = bl_house
                                logger.info(f'✅ AWB encontrado no campo bl_house do processo {processo_completo} (modal aéreo): {numero_cct}')
                            else:
                                # Tentar extrair do JSON completo como fallback
                                try:
                                    dados_json = json.loads(row['dados_completos_json']) if row['dados_completos_json'] else {}
                                    numero_cct = dados_json.get('awbBl') or dados_json.get('awb') or dados_json.get('blHouseNovo')
                                    if numero_cct:
                                        logger.info(f'✅ AWB encontrado no JSON do processo {processo_completo}: {numero_cct}')
                                except:
                                    pass
                
                if not numero_cct:
                    return {
                        'sucesso': False,
                        'erro': 'CCT_NAO_ENCONTRADO_PROCESSO',
                        'resposta': f"⚠️ **Nenhum CCT (AWB) encontrado para o processo {processo_completo}.**\n\n💡 **Dica:** O processo pode não ter AWB informado ou não é um processo aéreo."
                    }
            except Exception as e:
                logger.error(f'Erro ao buscar CCT do processo {processo_completo}: {e}')
                return {
                    'sucesso': False,
                    'erro': 'ERRO_BUSCA_PROCESSO',
                    'resposta': f"❌ **Erro ao buscar CCT do processo {processo_completo}:** {str(e)}"
                }
        
        if not numero_cct:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ É necessário fornecer numero_cct OU processo_referencia.'
            }
        
        # Consultar CCT diretamente usando a API CCTA (API GRATUITA)
        # Inicializar variáveis
        cct_dados = {}
        fonte = 'cache'
        processo_vinculado = None
        
        try:
            from db_manager import buscar_cct_cache, salvar_cct_cache, obter_processo_por_documento
            import json
            
            # 1. Tentar buscar do cache primeiro
            cct_cache = buscar_cct_cache(numero_cct)
            
            if cct_cache:
                processo_vinculado = cct_cache.get('processo_referencia')
                if not processo_vinculado:
                    processo_vinculado = obter_processo_por_documento('CCT', numero_cct)
            
            # 2. Consultar API CCTA diretamente via call_portal (mesma API da DUIMP)
            logger.info(f'🔍 Consultando CCT {numero_cct} diretamente na API Portal Único (CCTA - API GRATUITA)...')
            
            from utils.portal_proxy import call_portal
            
            # Path correto da API CCTA no Portal Único (confirmado no projeto DUIMP)
            path = '/ccta/api/ext/conhecimentos'
            params = {'numeroConhecimento': numero_cct}
            
            try:
                status_code, response_data = call_portal(path, query=params)
                
                if status_code == 200:
                    # Processar resposta (pode ser lista ou dict)
                    if isinstance(response_data, list) and len(response_data) > 0:
                        cct_json = response_data[0] if isinstance(response_data[0], dict) else {}
                    elif isinstance(response_data, dict):
                        cct_json = response_data.get('dados', response_data) if 'dados' in response_data else response_data
                    else:
                        cct_json = {}
                    
                    if cct_json:
                        # Salvar no cache
                        salvar_cct_cache(numero_cct, cct_json, processo_referencia=processo_vinculado)
                        
                        cct_dados = cct_json
                        fonte = 'api'
                        logger.info(f'✅ CCT {numero_cct} consultado com sucesso na API Portal Único (CCTA)')
                    else:
                        # Se API retornou vazio, tentar usar cache
                        if cct_cache:
                            logger.warning(f'⚠️ API retornou vazio, usando cache para CCT {numero_cct}')
                            cct_dados = cct_cache.get('json_completo', {})
                            fonte = 'cache'
                        else:
                            return {
                                'sucesso': False,
                                'erro': 'CCT_NAO_ENCONTRADO',
                                'resposta': f"❌ **CCT {numero_cct} não encontrado na API.**\n\n💡 **Dica:** Verifique se o número do AWB está correto."
                            }
                elif status_code == 404:
                    return {
                        'sucesso': False,
                        'erro': 'CCT_NAO_ENCONTRADO',
                        'resposta': f"❌ **CCT {numero_cct} não encontrado na API.**\n\n💡 **Dica:** Verifique se o número do AWB está correto."
                    }
                else:
                    # Outro erro da API
                    error_msg = response_data if isinstance(response_data, str) else (response_data.get('mensagem', '') if isinstance(response_data, dict) else str(response_data))
                    logger.error(f'❌ Erro ao consultar CCT {numero_cct}: Status {status_code}, Mensagem: {error_msg}')
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_API',
                        'resposta': f"❌ **Erro ao consultar CCT na API:** Status {status_code}\n\n**Detalhes:** {error_msg}"
                    }
            except Exception as e:
                logger.error(f'Erro ao consultar API CCTA: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': 'ERRO_API',
                    'resposta': f"❌ **Erro ao consultar CCT na API:** {str(e)}"
                }
        except Exception as e:
            logger.error(f'Erro ao consultar CCT {numero_cct}: {e}', exc_info=True)
            # Tentar cache como último recurso
            try:
                from db_manager import buscar_cct_cache
                cct_cache = buscar_cct_cache(numero_cct)
                if cct_cache:
                    cct_dados = cct_cache.get('json_completo', {})
                    fonte = 'cache'
                    processo_vinculado = cct_cache.get('processo_referencia')
                    logger.info(f'✅ Usando dados do cache (fallback) para CCT {numero_cct}')
                else:
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'resposta': f'❌ Erro ao obter extrato do CCT: {str(e)}'
                    }
            except Exception as e2:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_INTERNO',
                    'resposta': f'❌ Erro ao obter extrato do CCT: {str(e)}'
                }
        
        # Verificar se temos dados do CCT
        if not cct_dados:
            return {
                'sucesso': False,
                'erro': 'CCT_SEM_DADOS',
                'resposta': f'❌ Não foi possível obter dados do CCT {numero_cct}.'
            }
        
        # Formatar resposta com informações básicas do CCT
        resposta = f"📋 **EXTRATO DO CCT {numero_cct}**\n\n"
        resposta += "=" * 50 + "\n\n"
        
        # Identificação
        identificacao = cct_dados.get('identificacao', numero_cct)
        ruc = cct_dados.get('ruc', '')
        resposta += f"**Identificação:** {identificacao}\n"
        if ruc:
            resposta += f"**RUC:** {ruc}\n"
        resposta += "\n"
        
        # Situação
        situacao_encontrada = False
        partes_estoque = cct_dados.get('partesEstoque', [])
        if partes_estoque and isinstance(partes_estoque, list) and len(partes_estoque) > 0:
            parte_estoque = partes_estoque[0]
            situacao_atual = parte_estoque.get('situacaoAtual', '')
            data_hora_situacao = parte_estoque.get('dataHoraSituacaoAtual', '')
            
            if situacao_atual:
                resposta += f"**Situação:** {situacao_atual}\n"
                situacao_encontrada = True
                if data_hora_situacao:
                    resposta += f"**Data/Hora da Situação:** {data_hora_situacao}\n"
        
        if not situacao_encontrada:
            situacao_codigo = cct_dados.get('situacao', '')
            if situacao_codigo:
                situacoes_map = {'A': 'Ativo', 'C': 'Cancelado', 'F': 'Finalizado'}
                situacao_desc = situacoes_map.get(situacao_codigo, situacao_codigo)
                resposta += f"**Situação:** {situacao_desc}\n"
        
        # Aeroportos
        if cct_dados.get('codigoAeroportoOrigemConhecimento'):
            resposta += f"**Aeroporto Origem:** {cct_dados.get('codigoAeroportoOrigemConhecimento')}\n"
        if cct_dados.get('codigoAeroportoDestinoConhecimento'):
            resposta += f"**Aeroporto Destino:** {cct_dados.get('codigoAeroportoDestinoConhecimento')}\n"
        
        # Data de Emissão
        if cct_dados.get('dataEmissao'):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(cct_dados['dataEmissao'].replace('Z', '+00:00'))
                resposta += f"**Data de Emissão:** {dt.strftime('%d/%m/%Y')}\n"
            except:
                resposta += f"**Data de Emissão:** {cct_dados.get('dataEmissao')}\n"
        
        # Viagens associadas
        viagens_associadas = cct_dados.get('viagensAssociadas', [])
        if viagens_associadas:
            viagem = viagens_associadas[0] if len(viagens_associadas) > 0 else None
            if viagem:
                identificacao_viagem = viagem.get('identificacaoViagem', '')
                data_chegada = viagem.get('dataHoraChegadaEfetiva', '')
                aeroporto_chegada = viagem.get('aeroportoChegada', '')
                
                if identificacao_viagem:
                    resposta += f"\n**✈️ Viagem:** {identificacao_viagem}\n"
                if data_chegada:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(data_chegada.replace('Z', '+00:00'))
                        resposta += f"**Data/Hora Chegada:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                    except:
                        resposta += f"**Data/Hora Chegada:** {data_chegada}\n"
                if aeroporto_chegada:
                    resposta += f"**Aeroporto Chegada:** {aeroporto_chegada}\n"
        
        # Bloqueios
        bloqueios_ativos = cct_dados.get('bloqueiosAtivos', [])
        bloqueios_baixados = cct_dados.get('bloqueiosBaixados', [])
        if bloqueios_ativos:
            resposta += f"\n⚠️ **Bloqueios Ativos:** {len(bloqueios_ativos)}\n"
            for bloqueio in bloqueios_ativos[:3]:
                tipo_bloqueio = bloqueio.get('tipoBloqueio', '')
                if tipo_bloqueio:
                    resposta += f"   - {tipo_bloqueio}\n"
        elif bloqueios_baixados:
            resposta += f"\n✅ **Bloqueios:** Todos baixados\n"
        else:
            resposta += f"\n✅ **Bloqueios:** Nenhum bloqueio\n"
        
        # Processo vinculado
        if processo_vinculado:
            resposta += f"\n**Processo Vinculado:** {processo_vinculado}\n"
        
        # Fonte
        if fonte == 'api':
            resposta += f"\n✅ **Consulta realizada** (API gratuita - dados atualizados)\n"
        else:
            resposta += f"\n💾 **Dados do cache** (consulte novamente para atualizar)\n"
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'dados': cct_dados,
            'fonte': fonte,
            'processo_vinculado': processo_vinculado
        }

