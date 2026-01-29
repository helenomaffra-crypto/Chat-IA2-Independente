"""
Agente responsável por operações relacionadas a CE (Conhecimento de Embarque).
"""
import logging
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from ..utils.extractors import extract_processo_referencia

logger = logging.getLogger(__name__)


class CeAgent(BaseAgent):
    """
    Agente responsável por operações relacionadas a CE (Conhecimento de Embarque).
    
    Tools suportadas:
    - consultar_ce_maritimo: Consulta CE marítimo (com cache e API bilhetada)
    - verificar_atualizacao_ce: Verifica se CE precisa ser atualizado (API pública)
    - listar_processos_com_situacao_ce: Lista processos com situação de CE (usando apenas cache - sem custo)
    - obter_extrato_ce: Obtém extrato completo do CE
    
    ✅ IMPORTANTE: Nesta aplicação NÃO vinculamos manualmente. O sistema busca automaticamente o processo vinculado.
    """
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            'consultar_ce_maritimo': self._consultar_ce_maritimo,
            # 'vincular_processo_ce': self._vincular_processo_ce,  # ✅ DESABILITADO: Nesta aplicação não vinculamos manualmente
            'verificar_atualizacao_ce': self._verificar_atualizacao_ce,
            'listar_processos_com_situacao_ce': self._listar_processos_com_situacao_ce,
            'obter_extrato_ce': self._obter_extrato_ce,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada neste agente',
                'resposta': f'❌ Tool "{tool_name}" não está disponível no CeAgent.'
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
    
    def _consultar_ce_maritimo(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta CE marítimo.
        
        ✅ IMPORTANTE: Quando o usuário pede para "consultar", SEMPRE forçar consulta à API bilhetada.
        Suporta consulta via cache ou forçar atualização via API.
        """
        numero_ce = arguments.get('numero_ce', '').strip()
        processo_ref = arguments.get('processo_referencia', '').strip()
        usar_cache_apenas = arguments.get('usar_cache_apenas', False)
        forcar_consulta_api = arguments.get('forcar_consulta_api', False)
        mensagem_original = context.get('mensagem_original') if context else None
        
        # ✅ IMPORTANTE: Quando o usuário pede para "consultar", SEMPRE forçar consulta à API bilhetada
        if not usar_cache_apenas:
            forcar_consulta_api = True
        
        # ✅ NOVO: Se processo_referencia foi fornecido, buscar CE vinculado ao processo
        resposta_info = ""
        if processo_ref and not numero_ce:
            processo_completo = extract_processo_referencia(processo_ref)
            if not processo_completo:
                processo_completo = processo_ref
            
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
                
                # Usar o primeiro CE encontrado
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
                logger.error(f'Erro ao buscar CE do processo {processo_completo}: {e}')
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
        
        # Validar formato do CE
        if numero_ce and (not numero_ce.isdigit() or len(numero_ce) < 10):
            return {
                'sucesso': False,
                'erro': 'FORMATO_INVALIDO',
                'resposta': f'❌ Número de CE inválido: {numero_ce}. O CE deve ser numérico e ter pelo menos 10 dígitos.'
            }
        
        try:
            # Consultar CE via função do db_manager ou endpoint
            if usar_cache_apenas:
                from db_manager import buscar_ce_cache, obter_processo_por_documento, get_db_connection
                import sqlite3
                ce_cache = buscar_ce_cache(numero_ce)
                if ce_cache:
                    processo_vinculado_cache = ce_cache.get('processo_referencia')
                    processo_vinculado_final = processo_vinculado_cache
                    
                    # ✅ BUSCAR PROCESSO VINCULADO EM MÚLTIPLAS FONTES (automático)
                    # Prioridade 1: Tabela processo_documentos
                    if not processo_vinculado_final:
                        try:
                            processo_encontrado = obter_processo_por_documento('CE', numero_ce)
                            if processo_encontrado:
                                processo_vinculado_final = processo_encontrado
                                logger.info(f'✅ Processo {processo_encontrado} encontrado na tabela processo_documentos para CE {numero_ce}')
                        except Exception as e:
                            logger.warning(f'Erro ao buscar processo por documento no cache: {e}')
                    
                    # Prioridade 2: Campo numero_ce do processos_kanban
                    if not processo_vinculado_final:
                        try:
                            conn = get_db_connection()
                            conn.row_factory = sqlite3.Row
                            cursor = conn.cursor()
                            cursor.execute('''
                                SELECT processo_referencia
                                FROM processos_kanban
                                WHERE numero_ce = ?
                                LIMIT 1
                            ''', (numero_ce,))
                            row = cursor.fetchone()
                            conn.close()
                            
                            if row and row[0]:
                                processo_vinculado_final = row[0]
                                logger.info(f'✅ Processo {processo_vinculado_final} encontrado no campo numero_ce do processos_kanban para CE {numero_ce}')
                        except Exception as e:
                            logger.warning(f'Erro ao buscar processo no processos_kanban: {e}')
                    
                    # ✅ NOVO: Gravar histórico mesmo quando vem do cache (primeira vez)
                    try:
                        from services.documento_historico_service import DocumentoHistoricoService
                        historico_service = DocumentoHistoricoService()
                        historico_service.detectar_e_gravar_mudancas(
                            numero_documento=numero_ce,
                            tipo_documento='CE',
                            dados_novos=ce_cache['json_completo'],
                            fonte_dados='CACHE',
                            api_endpoint='/cache',
                            processo_referencia=processo_vinculado_final or processo_ref
                        )
                        logger.info(f'✅ Histórico do CE {numero_ce} gravado no SQL Server (do cache)')
                    except Exception as e:
                        logger.error(f'❌ Erro ao gravar histórico do CE {numero_ce} (cache): {e}', exc_info=True)
                        # Não bloquear se houver erro no histórico
                    
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
                # Consultar CE diretamente usando call_integracomex (mesma autenticação da DI)
                from db_manager import buscar_ce_cache, salvar_ce_cache, obter_processo_por_documento
                from utils.integracomex_proxy import call_integracomex
                import json
                
                # 1. Tentar buscar do cache primeiro
                ce_cache = buscar_ce_cache(numero_ce)
                
                # ✅ BUSCAR PROCESSO VINCULADO EM MÚLTIPLAS FONTES (automático)
                processo_vinculado = None
                
                # Prioridade 1: Tabela processo_documentos (fonte de verdade)
                try:
                    processo_vinculado = obter_processo_por_documento('CE', numero_ce)
                    if processo_vinculado:
                        logger.info(f'✅ Processo {processo_vinculado} encontrado na tabela processo_documentos para CE {numero_ce}')
                    else:
                        logger.debug(f'🔍 Nenhum processo encontrado na tabela processo_documentos para CE {numero_ce}')
                except Exception as e:
                    logger.warning(f'Erro ao buscar processo por documento: {e}')
                
                # Prioridade 2: Campo numero_ce do processos_kanban
                if not processo_vinculado:
                    try:
                        from db_manager import get_db_connection
                        import sqlite3
                        conn = get_db_connection()
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT processo_referencia
                            FROM processos_kanban
                            WHERE numero_ce = ?
                            LIMIT 1
                        ''', (numero_ce,))
                        row = cursor.fetchone()
                        conn.close()
                        
                        if row and row[0]:
                            processo_vinculado = row[0]
                            logger.info(f'✅ Processo {processo_vinculado} encontrado no campo numero_ce do processos_kanban para CE {numero_ce}')
                        else:
                            logger.debug(f'🔍 Nenhum processo encontrado no campo numero_ce do processos_kanban para CE {numero_ce}')
                    except Exception as e:
                        logger.warning(f'Erro ao buscar processo no processos_kanban: {e}')
                
                # Prioridade 3: Cache do CE
                if not processo_vinculado and ce_cache:
                    processo_vinculado = ce_cache.get('processo_referencia')
                    if processo_vinculado:
                        logger.info(f'✅ Processo {processo_vinculado} encontrado no cache do CE {numero_ce}')
                
                # 2. Consultar API diretamente usando call_integracomex (com autenticação OAuth2 + mTLS)
                # ✅ USA MESMA AUTENTICAÇÃO DA DI: OAuth2 (key/secret) + mTLS (certificado)
                logger.info(f'🔍 Consultando CE {numero_ce} diretamente na API Integra Comex (com autenticação OAuth2 + mTLS)...')
                
                # ✅ Path correto da API Integra Comex para consultar CE
                # Formato: /conhecimentos-embarque/{numero} (PLURAL, SEM /carga/)
                path = f'/conhecimentos-embarque/{numero_ce}'
                
                try:
                    status_code, response_body = call_integracomex(
                        path=path,
                        method='GET',
                        processo_referencia=processo_ref if processo_ref else None
                    )
                    
                    if status_code == 200:
                        # Salvar no cache
                        if isinstance(response_body, dict):
                            ce_json = response_body
                        else:
                            ce_json = json.loads(response_body) if isinstance(response_body, str) else response_body
                        
                        # Salvar no cache
                        salvar_ce_cache(numero_ce, ce_json, processo_referencia=processo_vinculado)
                        
                        # ✅ NOVO: Gravar histórico no SQL Server
                        try:
                            from services.documento_historico_service import DocumentoHistoricoService
                            historico_service = DocumentoHistoricoService()
                            historico_service.detectar_e_gravar_mudancas(
                                numero_documento=numero_ce,
                                tipo_documento='CE',
                                dados_novos=ce_json,
                                fonte_dados='INTEGRACOMEX',
                                api_endpoint=f'/conhecimentos-embarque/{numero_ce}',
                                processo_referencia=processo_vinculado or processo_ref
                            )
                            logger.info(f'✅ Histórico do CE {numero_ce} gravado no SQL Server')
                        except Exception as e:
                            logger.error(f'❌ Erro ao gravar histórico do CE {numero_ce}: {e}', exc_info=True)
                            # Não bloquear se houver erro no histórico
                        
                        ce_dados = ce_json
                        fonte = 'api_bilhetada'
                        aviso = '⚠️ Consulta BILHETADA realizada (dados atualizados da API Integra Comex)'
                        logger.info(f'✅ CE {numero_ce} consultado com sucesso na API Integra Comex')
                    elif status_code == 404:
                        # CE não encontrado - tentar usar cache se disponível
                        logger.warning(f'⚠️ CE {numero_ce} não encontrado na API (404). Tentando usar cache...')
                        if ce_cache:
                            logger.info(f'✅ Usando dados do cache para CE {numero_ce} (API retornou 404)')
                            ce_dados = ce_cache.get('json_completo', {})
                            fonte = 'cache'
                            aviso = '✅ Dados retornados do cache (sem custo)'
                        else:
                            return {
                                'sucesso': False,
                                'erro': 'CE_NAO_ENCONTRADO',
                                'resposta': f"❌ **CE {numero_ce} não encontrado na API Integra Comex (404).**\n\n💡 **Possíveis causas:**\n- O CE não existe na API\n- O número do CE está incorreto\n- O CE ainda não foi registrado no sistema"
                            }
                    else:
                        # Outro erro da API
                        error_msg = response_body if isinstance(response_body, str) else (response_body.get('mensagem', '') if isinstance(response_body, dict) else str(response_body))
                        logger.error(f'❌ Erro ao consultar CE {numero_ce}: Status {status_code}, Mensagem: {error_msg}')
                        
                        # Se API falhou, tentar usar cache
                        if ce_cache:
                            logger.warning(f'⚠️ API retornou status {status_code}, usando cache para CE {numero_ce}')
                            ce_dados = ce_cache.get('json_completo', {})
                            fonte = 'cache'
                            aviso = '✅ Dados retornados do cache (sem custo)'
                        else:
                            return {
                                'sucesso': False,
                                'erro': 'ERRO_API',
                                'resposta': f"❌ **Erro ao consultar CE na API Integra Comex:** Status {status_code}\n\n**Detalhes:** {error_msg}\n\n💡 **Dica:** Verifique se o número do CE está correto e se a autenticação está configurada."
                            }
                except RuntimeError as e:
                    # Erro de duplicata (já consultado recentemente)
                    if 'DUPLICATA' in str(e):
                        logger.warning(f'⚠️ CE {numero_ce} já foi consultado recentemente, usando cache...')
                        if ce_cache:
                            ce_dados = ce_cache.get('json_completo', {})
                            fonte = 'cache'
                            aviso = '✅ Dados retornados do cache (sem custo) - consulta duplicada evitada'
                        else:
                            return {
                                'sucesso': False,
                                'erro': 'DUPLICATA',
                                'resposta': f"⚠️ **CE {numero_ce} já foi consultado nos últimos 5 minutos.**\n\n💡 **Dica:** Aguarde alguns minutos antes de consultar novamente ou use os dados do cache."
                            }
                    else:
                        raise
                except Exception as e:
                    logger.error(f'Erro ao consultar CE {numero_ce}: {e}', exc_info=True)
                    # Tentar cache como último recurso
                    if ce_cache:
                        ce_dados = ce_cache.get('json_completo', {})
                        fonte = 'cache'
                        aviso = '✅ Dados retornados do cache (sem custo)'
                        processo_vinculado = ce_cache.get('processo_referencia')
                        logger.info(f'✅ Usando dados do cache (fallback) para CE {numero_ce}')
                    else:
                        return {
                            'sucesso': False,
                            'erro': 'ERRO_INTERNO',
                            'resposta': f'❌ Erro ao consultar CE: {str(e)}'
                        }
                
                # Preparar dados no formato esperado
                data = {
                    'sucesso': True,
                    'dados': ce_dados,
                    'fonte': fonte,
                    'aviso': aviso,
                    'processo_vinculado': processo_vinculado
                }
            
            # Formatar resposta com dados do CE
            ce_dados = data.get('dados', {})
            fonte = data.get('fonte', 'api')
            aviso = data.get('aviso', '')
            
            resposta = ""
            if processo_ref and resposta_info:
                resposta += resposta_info
            
            resposta += f"📦 **CE {numero_ce}**\n\n"
            
            # ✅ PRIORIDADE: Sempre mostrar dados básicos do CE primeiro
            situacao_encontrada = False
            
            # Tentar extrair situação de várias estruturas possíveis
            if ce_dados.get('situacao'):
                situacao = ce_dados.get('situacao', {})
                if isinstance(situacao, dict):
                    situacao_desc = situacao.get('descricao') or situacao.get('situacao') or situacao.get('codigo', 'N/A')
                    situacao_data = situacao.get('data') or situacao.get('dataSituacao') or situacao.get('dataHoraSituacao', '')
                else:
                    situacao_desc = str(situacao)
                    situacao_data = ''
                
                if situacao_desc and situacao_desc != 'N/A':
                    resposta += f"**Situação:** {situacao_desc}\n"
                    situacao_encontrada = True
                    if situacao_data:
                        resposta += f"**Data da Situação:** {situacao_data}\n"
                    resposta += "\n"
            
            # Fallback: tentar outras estruturas
            if not situacao_encontrada:
                if ce_dados.get('situacaoCarga'):
                    resposta += f"**Situação:** {ce_dados.get('situacaoCarga')}\n"
                    if ce_dados.get('dataSituacaoCarga'):
                        resposta += f"**Data da Situação:** {ce_dados.get('dataSituacaoCarga')}\n"
                    resposta += "\n"
                    situacao_encontrada = True
            
            # Verificar containerDetailsCe para situação
            if not situacao_encontrada:
                container_details = ce_dados.get('containerDetailsCe', [])
                if container_details and isinstance(container_details, list) and len(container_details) > 0:
                    primeiro_container = container_details[0]
                    situacao_container = primeiro_container.get('situacaoCarga', '')
                    if situacao_container:
                        resposta += f"**Situação:** {situacao_container}\n"
                        data_situacao_container = primeiro_container.get('dataSituacaoCarga', '')
                        if data_situacao_container:
                            resposta += f"**Data da Situação:** {data_situacao_container}\n"
                        resposta += "\n"
                        situacao_encontrada = True
            
            if not situacao_encontrada:
                resposta += "⚠️ **Situação:** Não disponível\n\n"
            
            # Informações principais do CE
            if ce_dados.get('numeroBlConhecimento'):
                resposta += f"**Número BL:** {ce_dados.get('numeroBlConhecimento')}\n"
            
            if ce_dados.get('navioPrimTransporte'):
                resposta += f"**Navio:** {ce_dados.get('navioPrimTransporte')}\n"
            
            if ce_dados.get('portoOrigem'):
                resposta += f"**Porto de Origem:** {ce_dados.get('portoOrigem')}\n"
            
            if ce_dados.get('portoDestino'):
                resposta += f"**Porto de Destino:** {ce_dados.get('portoDestino')}\n"
            
            if ce_dados.get('ulDestinoFinal'):
                resposta += f"**UL Destino Final:** {ce_dados.get('ulDestinoFinal')}\n"
            
            if ce_dados.get('paisProcedencia'):
                resposta += f"**País de Procedência:** {ce_dados.get('paisProcedencia')}\n"
            
            if ce_dados.get('cpfCnpjConsignatario'):
                resposta += f"**CNPJ/CPF Consignatário:** {ce_dados.get('cpfCnpjConsignatario')}\n"
            
            if ce_dados.get('dataEmissao'):
                resposta += f"**Data de Emissão:** {ce_dados.get('dataEmissao')}\n"
            
            # Bloqueios
            bloqueios_ativos = ce_dados.get('bloqueiosAtivos', [])
            bloqueios_baixados = ce_dados.get('bloqueiosBaixados', [])
            if bloqueios_ativos:
                resposta += f"\n⚠️ **Bloqueios Ativos:** {len(bloqueios_ativos)}\n"
                for bloqueio in bloqueios_ativos[:3]:  # Mostrar até 3
                    if isinstance(bloqueio, dict):
                        motivo = bloqueio.get('motivo') or bloqueio.get('descricao', 'N/A')
                        resposta += f"   - {motivo}\n"
            elif bloqueios_baixados:
                resposta += f"\n✅ **Bloqueios:** Todos baixados\n"
            else:
                resposta += f"\n✅ **Bloqueios:** Nenhum bloqueio\n"
            
            # Fonte e avisos
            if fonte == 'api':
                resposta += f"\n⚠️ **Consulta BILHETADA realizada** (dados atualizados da API)\n"
            
            # Processo vinculado (buscar novamente para garantir que temos o mais atualizado)
            processo_vinculado_final = data.get('processo_vinculado')
            
            # ✅ BUSCAR NOVAMENTE para garantir que temos o processo vinculado mais atualizado
            if not processo_vinculado_final:
                try:
                    processo_vinculado_final = obter_processo_por_documento('CE', numero_ce)
                except:
                    pass
            
            if not processo_vinculado_final:
                try:
                    from db_manager import get_db_connection
                    import sqlite3
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT processo_referencia
                        FROM processos_kanban
                        WHERE numero_ce = ?
                        LIMIT 1
                    ''', (numero_ce,))
                    row = cursor.fetchone()
                    conn.close()
                    if row and row[0]:
                        processo_vinculado_final = row[0]
                except:
                    pass
            
            if processo_vinculado_final:
                resposta += f"\n✅ **Processo Vinculado:** {processo_vinculado_final}\n"
            # ✅ REMOVIDO: Não mostrar mensagem de "processo não vinculado" - sistema busca automaticamente
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': ce_dados,
                'fonte': fonte,
                'processo_vinculado': processo_vinculado,
                'precisa_vincular_processo': not processo_vinculado
            }
            
        except Exception as e:
            logger.error(f'Erro ao consultar CE {numero_ce}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro ao consultar CE: {str(e)}'
            }
    
    def _vincular_processo_ce(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Vincula CE a um processo.
        
        ✅ IMPORTANTE: Cada processo deve ter apenas um CE.
        Desvincula CEs existentes antes de vincular o novo.
        """
        numero_ce = arguments.get('numero_ce', '').strip()
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        if not numero_ce:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Número do CE é obrigatório.'
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
        
        # ✅ IMPORTANTE: Cada processo deve ter apenas um CE
        # Desvincular todos os CEs existentes do processo antes de vincular o novo
        try:
            from db_manager import desvincular_todos_documentos_tipo, listar_documentos_processo, buscar_ce_cache, atualizar_processo_ce_cache, vincular_documento_processo
            
            ces_existentes = [doc for doc in listar_documentos_processo(processo_completo) if doc.get('tipo_documento') == 'CE']
            if ces_existentes:
                desvinculados = desvincular_todos_documentos_tipo(processo_completo, 'CE')
                if desvinculados > 0:
                    logger.info(f'✅ {desvinculados} CE(s) antigo(s) desvinculado(s) do processo {processo_completo} antes de vincular o novo')
            
            # Verificar se o CE existe no cache
            ce_cache = buscar_ce_cache(numero_ce)
            if not ce_cache:
                return {
                    'sucesso': False,
                    'erro': 'CE_NAO_ENCONTRADO_CACHE',
                    'resposta': f"⚠️ **CE {numero_ce} não encontrado no cache.**\n\n💡 **Dica:** É necessário consultar o CE primeiro antes de vincular a um processo."
                }
            
            # Vincular processo ao CE
            vincular_documento_processo(processo_completo, 'CE', numero_ce)
            
            # Atualizar também o cache do CE
            sucesso = atualizar_processo_ce_cache(numero_ce, processo_completo)
            
            if sucesso:
                resposta = f"✅ **Processo vinculado com sucesso!**\n\n"
                resposta += f"**CE:** {numero_ce}\n"
                resposta += f"**Processo:** {processo_completo}\n\n"
                resposta += f"🎯 **Pronto para gerar DUIMP!** O CE está vinculado ao processo e pode ser usado para criar a Declaração Única de Importação."
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'numero_ce': numero_ce,
                    'processo_referencia': processo_completo
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_VINCULACAO',
                    'resposta': f"❌ **Erro ao vincular processo {processo_completo} ao CE {numero_ce}.**"
                }
                
        except Exception as e:
            logger.error(f'Erro ao vincular processo ao CE: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro interno ao vincular processo: {str(e)}'
            }
    
    def _verificar_atualizacao_ce(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Verifica se um CE precisa ser atualizado usando API pública (gratuita).
        
        Retorna informações sobre se o CE precisa ser atualizado e recomendações.
        """
        numero_ce = arguments.get('numero_ce', '').strip()
        
        if not numero_ce:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Número do CE é obrigatório.'
            }
        
        try:
            from db_manager import buscar_ce_cache
            # ⚠️ DESABILITADO: Módulo utils.siscarga_publica não existe
            # from utils.siscarga_publica import consultar_data_ultima_atualizacao
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
                }
            
            # 2. Obter data do cache
            ultima_alteracao_cache = None
            if ce_cache.get('atualizado_em'):
                try:
                    ultima_alteracao_cache = datetime.fromisoformat(ce_cache['atualizado_em'].replace('Z', '+00:00'))
                except:
                    pass
            
            # 3. Consultar API pública para verificar última atualização
            # ⚠️ DESABILITADO: consultar_data_ultima_atualizacao não está disponível
            data_atualizacao_publica = None  # Placeholder
            try:
                # data_atualizacao_publica = consultar_data_ultima_atualizacao(numero_ce)
                
                if data_atualizacao_publica:
                    # Comparar datas
                    if not ultima_alteracao_cache:
                        # Cache sem data, precisa atualizar
                        return {
                            'sucesso': True,
                            'precisa_atualizar': True,
                            'motivo': 'Cache sem data de atualização',
                            'resposta': f"🔄 **CE {numero_ce} precisa ser atualizado.**\n\n💡 **Recomendação:** Consultar API bilhetada para obter dados atualizados.",
                            'acao_recomendada': 'consultar_ce_maritimo',
                            'data_publica': data_atualizacao_publica.isoformat()
                        }
                    
                    if data_atualizacao_publica > ultima_alteracao_cache:
                        # API pública tem data mais recente, precisa atualizar
                        return {
                            'sucesso': True,
                            'precisa_atualizar': True,
                            'motivo': f'API pública tem atualização mais recente ({data_atualizacao_publica.isoformat()} vs {ultima_alteracao_cache.isoformat()})',
                            'resposta': f"🔄 **CE {numero_ce} precisa ser atualizado.**\n\n💡 **Recomendação:** Consultar API bilhetada para obter dados atualizados.",
                            'acao_recomendada': 'consultar_ce_maritimo',
                            'data_cache': ultima_alteracao_cache.isoformat(),
                            'data_publica': data_atualizacao_publica.isoformat()
                        }
                    else:
                        # Cache está atualizado
                        return {
                            'sucesso': True,
                            'precisa_atualizar': False,
                            'motivo': 'Cache está atualizado',
                            'resposta': f"✅ **CE {numero_ce} está atualizado no cache.**\n\n💡 **Dica:** Não é necessário consultar API bilhetada no momento.",
                            'data_cache': ultima_alteracao_cache.isoformat(),
                            'data_publica': data_atualizacao_publica.isoformat()
                        }
                else:
                    # Não conseguiu consultar API pública
                    return {
                        'sucesso': True,
                        'precisa_atualizar': None,
                        'motivo': 'Não foi possível verificar atualização via API pública',
                        'resposta': f"⚠️ **Não foi possível verificar se o CE {numero_ce} precisa ser atualizado.**\n\n💡 **Recomendação:** Consultar API bilhetada para garantir dados atualizados.",
                        'acao_recomendada': 'consultar_ce_maritimo',
                    }
            except Exception as e:
                logger.error(f'Erro ao verificar atualização do CE {numero_ce}: {e}')
                return {
                    'sucesso': True,
                    'precisa_atualizar': None,
                    'motivo': f'Erro ao consultar API pública: {str(e)}',
                    'resposta': f"⚠️ **Erro ao verificar atualização do CE {numero_ce}.**\n\n💡 **Recomendação:** Consultar API bilhetada para garantir dados atualizados.",
                    'acao_recomendada': 'consultar_ce_maritimo',
                }
                
        except Exception as e:
            logger.error(f'Erro ao verificar atualização do CE {numero_ce}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro ao verificar atualização do CE: {str(e)}'
            }
    
    def _listar_processos_com_situacao_ce(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Lista processos com situação de CE usando apenas cache (SEM bilhetar).
        
        ✅ IMPORTANTE: Esta função usa apenas cache, não consulta API bilhetada.
        Use quando precisar listar processos por situação de CE sem custo.
        """
        situacao_filtro = arguments.get('situacao_filtro', '').strip().upper() or None
        limite = arguments.get('limite', 50)
        
        try:
            from db_manager import listar_processos, obter_dados_documentos_processo
            
            # Listar processos
            processos = listar_processos(limit=limite)
            
            resposta = f"📋 **Processos com Situação de CE** (Cache - Sem custo)\n\n"
            
            if situacao_filtro and situacao_filtro != 'TODAS':
                resposta += f"🔍 **Filtro:** {situacao_filtro}\n\n"
            
            processos_com_ce = []
            for proc in processos:
                proc_ref = proc.get('processo_referencia', '')
                dados_docs = obter_dados_documentos_processo(proc_ref)
                ces = dados_docs.get('ces', [])
                
                if ces:
                    for ce in ces:
                        situacao_ce = ce.get('situacao', '')
                        if situacao_ce:
                            # Aplicar filtro se fornecido
                            if not situacao_filtro or situacao_filtro == 'TODAS' or situacao_ce.upper() == situacao_filtro:
                                processos_com_ce.append({
                                    'processo': proc_ref,
                                    'ce': ce.get('numero', 'N/A'),
                                    'situacao': situacao_ce,
                                    'data_situacao': ce.get('data_situacao', ''),
                                    'carga_bloqueada': ce.get('carga_bloqueada', False),
                                    'ul_destino': ce.get('ul_destino_final', ''),
                                    'pais_procedencia': ce.get('pais_procedencia', '')
                                })
            
            if not processos_com_ce:
                resposta += "⚠️ Nenhum processo encontrado"
                if situacao_filtro and situacao_filtro != 'TODAS':
                    resposta += f" com situação '{situacao_filtro}'"
                resposta += ".\n\n"
                resposta += "💡 **Dica:** Os processos podem não ter CE vinculado ou os CEs podem não estar no cache."
            else:
                # Agrupar por situação para facilitar leitura
                situacoes_agrupadas = {}
                for proc_ce in processos_com_ce:
                    situacao = proc_ce['situacao']
                    if situacao not in situacoes_agrupadas:
                        situacoes_agrupadas[situacao] = []
                    situacoes_agrupadas[situacao].append(proc_ce)
                
                for situacao, processos_situacao in situacoes_agrupadas.items():
                    resposta += f"**📦 {situacao}** ({len(processos_situacao)} processo(s))\n\n"
                    for proc_ce in processos_situacao[:limite]:
                        resposta += f"  • **{proc_ce['processo']}**\n"
                        resposta += f"    - CE: {proc_ce['ce']}\n"
                        if proc_ce.get('data_situacao'):
                            resposta += f"    - Data: {proc_ce['data_situacao']}\n"
                        if proc_ce.get('carga_bloqueada'):
                            resposta += f"    - ⚠️ Carga bloqueada\n"
                        resposta += "\n"
                
                resposta += f"\n✅ **Total:** {len(processos_com_ce)} processo(s) encontrado(s)\n"
                resposta += "💰 **Custo:** R$ 0,00 (dados do cache, sem consulta à API bilhetada)"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'processos': processos_com_ce,
                'total': len(processos_com_ce),
                'fonte': 'cache'
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos com situação de CE: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro ao listar processos com situação de CE: {str(e)}'
            }
    
    def _obter_extrato_ce(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Obtém extrato completo do CE, consultando diretamente a API do Integra Comex.
        
        ✅ IMPORTANTE: Esta função consulta a API bilhetada para obter dados atualizados.
        Use quando o usuário pedir explicitamente "extrato CE" ou "extrato do CE".
        """
        numero_ce = arguments.get('numero_ce', '').strip()
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        # Se processo_referencia foi fornecido, buscar CE vinculado ao processo
        if processo_ref and not numero_ce:
            processo_completo = extract_processo_referencia(processo_ref)
            if not processo_completo:
                processo_completo = processo_ref
            
            try:
                from db_manager import obter_dados_documentos_processo, get_db_connection
                import sqlite3
                
                # ✅ PRIORIDADE 1: Buscar dos documentos vinculados (cache rápido)
                dados_processo = obter_dados_documentos_processo(processo_completo)
                ces = dados_processo.get('ces', []) if dados_processo else []
                
                if ces:
                    numero_ce = ces[0].get('numero', '')
                    logger.info(f'✅ CE encontrado em documentos vinculados: {numero_ce}')
                
                # ✅ PRIORIDADE 2: Buscar do campo numero_ce do processos_kanban (cache)
                if not numero_ce:
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT numero_ce
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                        LIMIT 1
                    ''', (processo_completo,))
                    row = cursor.fetchone()
                    conn.close()
                    
                    if row and row[0]:
                        numero_ce = row[0]
                        logger.info(f'✅ CE encontrado no campo numero_ce do processo {processo_completo}: {numero_ce}')
                
                # ✅ PRIORIDADE 3: Buscar do ProcessoRepository (SQL Server - fonte completa)
                # ✅ CRÍTICO (10/01/2026): Processos antigos podem ter CE apenas no SQL Server
                if not numero_ce:
                    logger.info(f'⚠️ CE não encontrado no cache, buscando do ProcessoRepository (SQL Server)...')
                    try:
                        from services.processo_repository import ProcessoRepository
                        repositorio = ProcessoRepository()
                        processo_dto = repositorio.buscar_por_referencia(processo_completo)
                        
                        if processo_dto:
                            # Verificar se tem CE no DTO
                            if processo_dto.numero_ce:
                                numero_ce = processo_dto.numero_ce
                                logger.info(f'✅ CE encontrado no ProcessoRepository: {numero_ce}')
                            elif processo_dto.dados_completos and isinstance(processo_dto.dados_completos, dict):
                                # Verificar em dados_completos
                                ce_data = processo_dto.dados_completos.get('ce', {})
                                if ce_data and ce_data.get('numero'):
                                    numero_ce = ce_data['numero']
                                    logger.info(f'✅ CE encontrado em dados_completos do ProcessoRepository: {numero_ce}')
                    except Exception as e:
                        logger.warning(f'⚠️ Erro ao buscar do ProcessoRepository (não crítico): {e}')
                
                if not numero_ce:
                    return {
                        'sucesso': False,
                        'erro': 'CE_NAO_ENCONTRADO_PROCESSO',
                        'resposta': f"⚠️ **Nenhum CE encontrado para o processo {processo_completo}.**\n\n💡 **Dica:** O processo pode não ter CE vinculado ou o CE ainda não foi consultado."
                    }
            except Exception as e:
                logger.error(f'Erro ao buscar CE do processo {processo_completo}: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': 'ERRO_BUSCA_PROCESSO',
                    'resposta': f"❌ **Erro ao buscar CE do processo {processo_completo}:** {str(e)}"
                }
        
        if not numero_ce:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ É necessário fornecer numero_ce OU processo_referencia.'
            }
        
        # Consultar CE diretamente usando call_integracomex (mesma autenticação da DI)
        # Inicializar variáveis
        ce_dados = {}
        fonte = 'cache'
        processo_vinculado = None
        
        try:
            from db_manager import buscar_ce_cache, salvar_ce_cache, obter_processo_por_documento
            from utils.integracomex_proxy import call_integracomex
            import json
            
            # 1. Tentar buscar do cache primeiro
            ce_cache = buscar_ce_cache(numero_ce)
            
            # ✅ BUSCAR PROCESSO VINCULADO EM MÚLTIPLAS FONTES (automático)
            processo_vinculado = None
            
            # Prioridade 1: Tabela processo_documentos (fonte de verdade)
            try:
                processo_vinculado = obter_processo_por_documento('CE', numero_ce)
                if processo_vinculado:
                    logger.info(f'✅ Processo {processo_vinculado} encontrado na tabela processo_documentos para CE {numero_ce}')
            except Exception as e:
                logger.warning(f'Erro ao buscar processo por documento: {e}')
            
            # Prioridade 2: Campo numero_ce do processos_kanban
            if not processo_vinculado:
                try:
                    from db_manager import get_db_connection
                    import sqlite3
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT processo_referencia
                        FROM processos_kanban
                        WHERE numero_ce = ?
                        LIMIT 1
                    ''', (numero_ce,))
                    row = cursor.fetchone()
                    conn.close()
                    
                    if row and row[0]:
                        processo_vinculado = row[0]
                        logger.info(f'✅ Processo {processo_vinculado} encontrado no campo numero_ce do processos_kanban para CE {numero_ce}')
                except Exception as e:
                    logger.warning(f'Erro ao buscar processo no processos_kanban: {e}')
            
            # Prioridade 3: Cache do CE
            if not processo_vinculado and ce_cache:
                processo_vinculado = ce_cache.get('processo_referencia')
                if processo_vinculado:
                    logger.info(f'✅ Processo {processo_vinculado} encontrado no cache do CE {numero_ce}')
            
            # 2. Consultar API diretamente usando call_integracomex (com autenticação OAuth2 + mTLS)
            # ✅ USA MESMA AUTENTICAÇÃO DA DI: OAuth2 (key/secret) + mTLS (certificado)
            logger.info(f'🔍 Consultando CE {numero_ce} diretamente na API Integra Comex (com autenticação OAuth2 + mTLS)...')
            
            # ✅ Path correto da API Integra Comex para consultar CE
            # Formato: /conhecimentos-embarque/{numero} (PLURAL, SEM /carga/)
            # Conforme implementação do Projeto-DUIMP que funciona corretamente
            # Documentação oficial: GET /conhecimentos-embarque/{nr}
            path = f'/conhecimentos-embarque/{numero_ce}'
            
            logger.info(f'🔍 Consultando CE {numero_ce} no path: {path}')
            
            status_code, response_body = call_integracomex(
                path=path,
                method='GET',
                processo_referencia=processo_ref if processo_ref else None
            )
            
            logger.info(f'📡 Resposta da API: status={status_code}, tipo={type(response_body)}')
            
            if status_code == 200:
                # Salvar no cache
                if isinstance(response_body, dict):
                    ce_json = response_body
                else:
                    ce_json = json.loads(response_body) if isinstance(response_body, str) else response_body
                
                # Salvar no cache
                salvar_ce_cache(numero_ce, ce_json, processo_referencia=processo_vinculado)
                
                ce_dados = ce_json
                fonte = 'api_bilhetada'
                logger.info(f'✅ CE {numero_ce} consultado com sucesso na API Integra Comex')
            elif status_code == 404:
                # CE não encontrado - pode ser que não exista ou o número esteja errado
                logger.warning(f'⚠️ CE {numero_ce} não encontrado na API (404). Tentando usar cache...')
                
                # Tentar usar cache se disponível
                if ce_cache:
                    logger.info(f'✅ Usando dados do cache para CE {numero_ce} (API retornou 404)')
                    ce_dados = ce_cache.get('json_completo', {})
                    fonte = 'cache'
                else:
                    # Verificar se o número do CE está no formato correto (15 dígitos)
                    if len(numero_ce) != 15 or not numero_ce.isdigit():
                        return {
                            'sucesso': False,
                            'erro': 'CE_FORMATO_INVALIDO',
                            'resposta': f"❌ **Número do CE inválido:** {numero_ce}\n\n💡 **Dica:** O número do CE deve ter 15 dígitos numéricos.\n\n**Número encontrado:** {numero_ce} ({len(numero_ce)} caracteres)"
                        }
                    
                    return {
                        'sucesso': False,
                        'erro': 'CE_NAO_ENCONTRADO',
                        'resposta': f"❌ **CE {numero_ce} não encontrado na API Integra Comex (404).**\n\n💡 **Possíveis causas:**\n- O CE não existe na API\n- O número do CE está incorreto\n- O CE ainda não foi registrado no sistema\n\n**Número consultado:** {numero_ce}\n\n💡 **Dica:** Verifique se o número do CE está correto no processo {processo_ref if processo_ref else 'N/A'}."
                    }
            else:
                # Outro erro da API
                error_msg = response_body if isinstance(response_body, str) else (response_body.get('mensagem', '') if isinstance(response_body, dict) else str(response_body))
                logger.error(f'❌ Erro ao consultar CE {numero_ce}: Status {status_code}, Mensagem: {error_msg}')
                
                # Se API falhou, tentar usar cache
                if ce_cache:
                    logger.warning(f'⚠️ API retornou status {status_code}, usando cache para CE {numero_ce}')
                    ce_dados = ce_cache.get('json_completo', {})
                    fonte = 'cache'
                else:
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_API',
                        'resposta': f"❌ **Erro ao consultar CE na API Integra Comex:** Status {status_code}\n\n**Detalhes:** {error_msg}\n\n💡 **Dica:** Verifique se o número do CE está correto e se a autenticação está configurada."
                    }
        except RuntimeError as e:
            # Erro de duplicata (já consultado recentemente)
            if 'DUPLICATA' in str(e):
                logger.warning(f'⚠️ CE {numero_ce} já foi consultado recentemente, usando cache...')
                from db_manager import buscar_ce_cache
                ce_cache = buscar_ce_cache(numero_ce)
                if ce_cache:
                    ce_dados = ce_cache.get('json_completo', {})
                    fonte = 'cache'
                    processo_vinculado = ce_cache.get('processo_referencia')
                else:
                    return {
                        'sucesso': False,
                        'erro': 'DUPLICATA',
                        'resposta': f"⚠️ **CE {numero_ce} já foi consultado nos últimos 5 minutos.**\n\n💡 **Dica:** Aguarde alguns minutos antes de consultar novamente ou use os dados do cache."
                    }
            else:
                raise
        except Exception as e:
            logger.error(f'Erro ao consultar CE {numero_ce}: {e}', exc_info=True)
            # Tentar cache como último recurso
            try:
                from db_manager import buscar_ce_cache
                ce_cache = buscar_ce_cache(numero_ce)
                if ce_cache:
                    ce_dados = ce_cache.get('json_completo', {})
                    fonte = 'cache'
                    processo_vinculado = ce_cache.get('processo_referencia')
                    logger.info(f'✅ Usando dados do cache (fallback) para CE {numero_ce}')
                else:
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_INTERNO',
                        'resposta': f'❌ Erro ao obter extrato do CE: {str(e)}'
                    }
            except Exception as e2:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_INTERNO',
                    'resposta': f'❌ Erro ao obter extrato do CE: {str(e)}'
                }
        
        # Verificar se temos dados do CE
        if not ce_dados:
            return {
                'sucesso': False,
                'erro': 'CE_SEM_DADOS',
                'resposta': f'❌ Não foi possível obter dados do CE {numero_ce}.'
            }
        
        # Formatar resposta com informações básicas do CE
        resposta = f"📋 **EXTRATO DO CE {numero_ce}**\n\n"
        resposta += "=" * 50 + "\n\n"
        
        # Informações principais
        if ce_dados.get('numeroBlConhecimento'):
            resposta += f"**Número BL:** {ce_dados.get('numeroBlConhecimento')}\n"
        
        if ce_dados.get('situacao'):
            situacao = ce_dados.get('situacao', {})
            if isinstance(situacao, dict):
                situacao_desc = situacao.get('descricao') or situacao.get('situacao') or situacao.get('codigo', 'N/A')
                situacao_data = situacao.get('data') or situacao.get('dataSituacao') or ''
                resposta += f"**Situação:** {situacao_desc}\n"
                if situacao_data:
                    resposta += f"**Data da Situação:** {situacao_data}\n"
            else:
                resposta += f"**Situação:** {situacao}\n"
        
        # Navio e transporte
        if ce_dados.get('navioPrimTransporte'):
            resposta += f"**Navio:** {ce_dados.get('navioPrimTransporte')}\n"
        
        if ce_dados.get('dataEmissao'):
            resposta += f"**Data de Emissão:** {ce_dados.get('dataEmissao')}\n"
        
        # Porto e destino
        if ce_dados.get('portoOrigem'):
            resposta += f"**Porto de Origem:** {ce_dados.get('portoOrigem')}\n"
        
        if ce_dados.get('portoDestino'):
            resposta += f"**Porto de Destino:** {ce_dados.get('portoDestino')}\n"
        
        if ce_dados.get('ulDestinoFinal'):
            resposta += f"**UL Destino Final:** {ce_dados.get('ulDestinoFinal')}\n"
        
        # País
        if ce_dados.get('paisProcedencia'):
            resposta += f"**País de Procedência:** {ce_dados.get('paisProcedencia')}\n"
        
        # Consignatário
        if ce_dados.get('cpfCnpjConsignatario'):
            resposta += f"**CNPJ/CPF Consignatário:** {ce_dados.get('cpfCnpjConsignatario')}\n"
        
        if ce_dados.get('nomeConsignatario'):
            resposta += f"**Nome Consignatário:** {ce_dados.get('nomeConsignatario')}\n"
        
        # Bloqueios
        bloqueios_ativos = ce_dados.get('bloqueiosAtivos', [])
        bloqueios_baixados = ce_dados.get('bloqueiosBaixados', [])
        if bloqueios_ativos:
            resposta += f"\n⚠️ **Bloqueios Ativos:** {len(bloqueios_ativos)}\n"
            for bloqueio in bloqueios_ativos[:3]:  # Mostrar até 3
                if isinstance(bloqueio, dict):
                    motivo = bloqueio.get('motivo') or bloqueio.get('descricao', 'N/A')
                    resposta += f"   - {motivo}\n"
        elif bloqueios_baixados:
            resposta += f"\n✅ **Bloqueios:** Todos baixados\n"
        else:
            resposta += f"\n✅ **Bloqueios:** Nenhum bloqueio\n"
        
        # ✅ BUSCAR PROCESSO VINCULADO NOVAMENTE para garantir que temos o mais atualizado
        if not processo_vinculado:
            try:
                processo_vinculado = obter_processo_por_documento('CE', numero_ce)
            except:
                pass
        
        if not processo_vinculado:
            try:
                from db_manager import get_db_connection
                import sqlite3
                conn = get_db_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT processo_referencia
                    FROM processos_kanban
                    WHERE numero_ce = ?
                    LIMIT 1
                ''', (numero_ce,))
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    processo_vinculado = row[0]
            except:
                pass
        
        # Processo vinculado
        if processo_vinculado:
            resposta += f"\n**Processo Vinculado:** {processo_vinculado}\n"
        
        # Fonte
        fonte_texto = ""
        if fonte == 'api_bilhetada':
            fonte_texto = "\n⚠️ **Consulta BILHETADA realizada** (dados atualizados da API Integra Comex)\n"
        elif fonte == 'api':
            fonte_texto = "\n⚠️ **Consulta BILHETADA realizada** (dados atualizados da API Integra Comex)\n"
        else:
            fonte_texto = "\n✅ **Dados do cache** (sem custo)\n"
        
        resposta += fonte_texto
        
        # ✅ NOVO (10/01/2026): Gerar PDF do extrato CE (similar ao DI e DUIMP)
        pdf_link = None
        resposta_pdf = ""
        
        try:
            # Gerar PDF usando método similar ao DI
            from pathlib import Path
            import io
            from datetime import datetime
            import json
            
            downloads_dir = Path(__file__).parent.parent / 'downloads'
            downloads_dir.mkdir(exist_ok=True)
            
            # Tentar gerar PDF usando xhtml2pdf
            try:
                from xhtml2pdf import pisa
                from flask import render_template
                from app import app
                
                # ✅ Criar HTML básico para PDF (sem template específico por enquanto)
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Extrato CE {numero_ce}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ color: #666; margin-top: 20px; }}
        p {{ margin: 5px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .bloqueio {{ color: red; }}
        .ok {{ color: green; }}
    </style>
</head>
<body>
    <h1>Extrato do CE {numero_ce}</h1>
    
    <h2>Informações Principais</h2>
    <table>
        <tr><th>Campo</th><th>Valor</th></tr>
"""
                
                # Adicionar campos principais
                if ce_dados.get('numeroBlConhecimento'):
                    html_content += f"        <tr><td>Número BL</td><td>{ce_dados.get('numeroBlConhecimento')}</td></tr>\n"
                
                if ce_dados.get('navioPrimTransporte'):
                    html_content += f"        <tr><td>Navio</td><td>{ce_dados.get('navioPrimTransporte')}</td></tr>\n"
                
                if ce_dados.get('dataEmissao'):
                    html_content += f"        <tr><td>Data de Emissão</td><td>{ce_dados.get('dataEmissao')}</td></tr>\n"
                
                # Situação
                if ce_dados.get('situacao'):
                    situacao = ce_dados.get('situacao', {})
                    if isinstance(situacao, dict):
                        situacao_desc = situacao.get('descricao') or situacao.get('situacao') or situacao.get('codigo', 'N/A')
                        situacao_data = situacao.get('data') or situacao.get('dataSituacao') or ''
                        html_content += f"        <tr><td>Situação</td><td>{situacao_desc}</td></tr>\n"
                        if situacao_data:
                            html_content += f"        <tr><td>Data da Situação</td><td>{situacao_data}</td></tr>\n"
                    else:
                        html_content += f"        <tr><td>Situação</td><td>{situacao}</td></tr>\n"
                
                # Porto e destino
                if ce_dados.get('portoOrigem'):
                    html_content += f"        <tr><td>Porto de Origem</td><td>{ce_dados.get('portoOrigem')}</td></tr>\n"
                
                if ce_dados.get('portoDestino'):
                    html_content += f"        <tr><td>Porto de Destino</td><td>{ce_dados.get('portoDestino')}</td></tr>\n"
                
                if ce_dados.get('ulDestinoFinal'):
                    html_content += f"        <tr><td>UL Destino Final</td><td>{ce_dados.get('ulDestinoFinal')}</td></tr>\n"
                
                if ce_dados.get('paisProcedencia'):
                    html_content += f"        <tr><td>País de Procedência</td><td>{ce_dados.get('paisProcedencia')}</td></tr>\n"
                
                if ce_dados.get('cpfCnpjConsignatario'):
                    html_content += f"        <tr><td>CNPJ/CPF Consignatário</td><td>{ce_dados.get('cpfCnpjConsignatario')}</td></tr>\n"
                
                if ce_dados.get('nomeConsignatario'):
                    html_content += f"        <tr><td>Nome Consignatário</td><td>{ce_dados.get('nomeConsignatario')}</td></tr>\n"
                
                if processo_vinculado:
                    html_content += f"        <tr><td>Processo Vinculado</td><td>{processo_vinculado}</td></tr>\n"
                
                html_content += "    </table>\n"
                
                # Bloqueios
                bloqueios_ativos = ce_dados.get('bloqueiosAtivos', [])
                bloqueios_baixados = ce_dados.get('bloqueiosBaixados', [])
                if bloqueios_ativos:
                    html_content += f"""
    <h2>Bloqueios Ativos ({len(bloqueios_ativos)})</h2>
    <table>
        <tr><th>Motivo/Descrição</th></tr>
"""
                    for bloqueio in bloqueios_ativos:
                        if isinstance(bloqueio, dict):
                            motivo = bloqueio.get('motivo') or bloqueio.get('descricao', 'N/A')
                            html_content += f"        <tr><td class='bloqueio'>{motivo}</td></tr>\n"
                    html_content += "    </table>\n"
                elif bloqueios_baixados:
                    html_content += "<p class='ok'>Todos os bloqueios foram baixados.</p>\n"
                else:
                    html_content += "<p class='ok'>Nenhum bloqueio ativo.</p>\n"
                
                html_content += f"""
    <hr>
    <p><small>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</small></p>
    <p><small>Fonte: {'API Integra Comex (BILHETADA)' if fonte == 'api_bilhetada' else 'Cache local (sem custo)'}</small></p>
</body>
</html>
"""
                
                # Nome do arquivo
                nome_arquivo = f'Extrato-CE-{numero_ce}.pdf'
                caminho_arquivo = downloads_dir / nome_arquivo
                
                # Gerar PDF
                with open(caminho_arquivo, 'wb') as arquivo_pdf:
                    status_pdf = pisa.CreatePDF(io.StringIO(html_content), dest=arquivo_pdf, encoding='utf-8')
                    
                    if status_pdf.err:
                        logger.warning(f'⚠️ Erro ao gerar PDF do CE: {status_pdf.err}')
                        # Não é crítico - apenas logar e continuar
                        if caminho_arquivo.exists():
                            try:
                                caminho_arquivo.unlink()
                            except:
                                pass
                    else:
                        # PDF gerado com sucesso
                        pdf_link = f"/api/download/{nome_arquivo}"
                        resposta_pdf = f"\n\n📄 **PDF Gerado:** [Clique aqui para baixar o PDF]({pdf_link})"
                        logger.info(f'✅ PDF do CE gerado com sucesso: {nome_arquivo}')
            except ImportError:
                logger.debug('⚠️ Biblioteca xhtml2pdf não está instalada. PDF não será gerado.')
            except Exception as e:
                logger.warning(f'⚠️ Erro ao gerar PDF do CE (não crítico): {e}')
        except Exception as e:
            logger.warning(f'⚠️ Erro ao tentar gerar PDF do CE (não crítico): {e}')
        
        resposta += resposta_pdf
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'dados': ce_dados,
            'fonte': fonte,
            'processo_vinculado': processo_vinculado,
            'pdf_link': pdf_link
        }

