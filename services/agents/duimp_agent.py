"""
Agente responsável por operações relacionadas a DUIMP.
"""
import logging
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from ..utils.extractors import extract_processo_referencia
from ..utils.validators import validate_processo_referencia
import sys
from pathlib import Path

# Adicionar diretório raiz ao path para importar utilitários
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from utils.iata_to_country import iata_to_country_code

logger = logging.getLogger(__name__)


class DuimpAgent(BaseAgent):
    """
    Agente responsável por operações relacionadas a DUIMP.
    
    Tools suportadas:
    - criar_duimp: Cria uma DUIMP para um processo
    - verificar_duimp_registrada: Verifica se há DUIMP registrada
    - obter_dados_duimp: Obtém dados completos de uma DUIMP
    - vincular_processo_duimp: Vincula uma DUIMP a um processo
    """
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            'criar_duimp': self._criar_duimp,
            'verificar_duimp_registrada': self._verificar_duimp_registrada,
            'obter_dados_duimp': self._obter_dados_duimp,
            'vincular_processo_duimp': self._vincular_processo_duimp,
            'obter_extrato_pdf_duimp': self._obter_extrato_pdf_duimp,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada neste agente',
                'resposta': f'❌ Tool "{tool_name}" não está disponível no DuimpAgent.'
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
    
    def _ajustar_ce_para_ambiente(self, numero_ce: str, ambiente: str) -> str:
        """
        Ajusta o número do CE conforme o ambiente.
        
        Regras:
        - VALIDAÇÃO: API só aceita CEs terminados em 01-09 (modelos de teste)
          → Mantém 13 primeiros dígitos e substitui últimos 2 por "02"
        - PRODUÇÃO: Usa CE completo de 15 dígitos sem alteração
        
        Args:
            numero_ce: Número do CE original (15 dígitos)
            ambiente: 'validacao' ou 'producao'
        
        Returns:
            Número do CE ajustado para o ambiente
        """
        if not numero_ce or len(str(numero_ce).strip()) != 15:
            return numero_ce  # Retornar como está se não for CE válido
        
        numero_ce_str = str(numero_ce).strip()
        
        if ambiente == 'validacao':
            # ✅ VALIDAÇÃO: Substituir últimos 2 dígitos por "02" (modelo de teste)
            # Manter 13 primeiros dígitos + "02"
            ce_ajustado = numero_ce_str[:13] + '02'
            logger.info(f'🔄 CE ajustado para validação: {numero_ce_str} → {ce_ajustado} (últimos 2 dígitos substituídos por "02")')
            return ce_ajustado
        else:
            # ✅ PRODUÇÃO: Usar CE completo sem alteração
            logger.info(f'✅ CE usado completo para produção: {numero_ce_str}')
            return numero_ce_str
    
    def extrair_dados_processo_para_duimp(self, processo_referencia: str, ambiente: str = 'validacao') -> Optional[Dict[str, Any]]:
        """
        Extrai dados do processo e monta payload mínimo para criar DUIMP.
        
        ✅ NOVO FLUXO:
        1. Busca CE/CCT vinculado ao processo
        2. Consulta CE/CCT DIRETAMENTE da API (não usa cache/Kanban)
        3. Extrai informações necessárias do CE/CCT da API:
           - CNPJ/CPF do importador (COMPLETO, 14 dígitos)
           - Número do CE ou RUC (CCT)
           - Unidade Local (UL) de destino final
           - País de procedência
        4. Monta documento tipo 30 (CE/CCT)
        5. Retorna JSON pronto para enviar
        
        Args:
            processo_referencia: Número do processo (ex: "ALH.0001/25")
            ambiente: 'validacao' ou 'producao' (padrão: 'validacao')
                      - VALIDAÇÃO: Ajusta CE para terminar em "02" (API só aceita 01-09)
                      - PRODUÇÃO: Usa CE completo de 15 dígitos sem alteração
        
        Returns:
            Dict com payload da DUIMP ou None se não conseguir extrair dados
        """
        try:
            # ✅ LOG: Registrar qual processo está sendo usado
            logger.info(f'🔍 [DUIMP] extrair_dados_processo_para_duimp chamado com processo: {processo_referencia}')
            
            from db_manager import obter_dados_documentos_processo, get_db_connection
            import sqlite3
            
            # 1. Buscar CE/CCT vinculado ao processo (apenas para obter o número)
            dados_processo = obter_dados_documentos_processo(processo_referencia)
            if not dados_processo:
                logger.warning(f'⚠️ Processo {processo_referencia} não encontrado')
                return None
            
            logger.info(f'🔍 Dados do processo {processo_referencia}: {list(dados_processo.keys())}')
            
            ces = dados_processo.get('ces', [])
            ccts = dados_processo.get('ccts', [])
            
            logger.info(f'🔍 CEs encontrados: {len(ces)}, CCTs encontrados: {len(ccts)}')
            
            # ✅ NOVO: Se não encontrou CE/CCT na tabela processo_documentos, buscar do processos_kanban
            if not ces and not ccts:
                logger.info(f'🔍 Não encontrou CE/CCT na tabela processo_documentos, buscando do processos_kanban...')
                try:
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT numero_ce, modal, bl_house, dados_completos_json
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                        LIMIT 1
                    ''', (processo_referencia,))
                    row = cursor.fetchone()
                    conn.close()
                    
                    if row:
                        numero_ce_kanban = row['numero_ce']
                        modal_kanban = row['modal'] or ''
                        bl_house_kanban = row['bl_house']
                        
                        # Se tem CE no campo numero_ce
                        if numero_ce_kanban:
                            # ✅ REGRA: Validar que o número do CE tem 15 dígitos
                            numero_ce_kanban_str = str(numero_ce_kanban).strip()
                            if len(numero_ce_kanban_str) == 15:
                                logger.info(f'✅ CE encontrado no campo numero_ce do processos_kanban: {numero_ce_kanban} (15 dígitos)')
                                ces = [{'numero': numero_ce_kanban_str}]
                            else:
                                logger.warning(f'⚠️ Número do CE no processos_kanban não tem 15 dígitos: {numero_ce_kanban} (tamanho: {len(numero_ce_kanban_str)})')
                                # Mesmo assim, adicionar para tentar buscar da API
                                ces = [{'numero': numero_ce_kanban_str}]
                        # Se é aéreo e tem bl_house, pode ser AWB (CCT)
                        elif ('AÉREO' in modal_kanban.upper() or 'AEREO' in modal_kanban.upper()) and bl_house_kanban:
                            logger.info(f'✅ AWB encontrado no campo bl_house do processos_kanban (modal aéreo): {bl_house_kanban}')
                            ccts = [{'numero': bl_house_kanban, 'ruc': None}]
                except Exception as e:
                    logger.warning(f'⚠️ Erro ao buscar CE/CCT do processos_kanban: {e}')
            
            # 2. Prioridade: CE > CCT
            ce_data = ces[0] if ces else None
            cct_data = ccts[0] if ccts else None
            
            if not ce_data and not cct_data:
                logger.warning(f'⚠️ Processo {processo_referencia} não tem CE nem CCT vinculado')
                return None
            
            # ✅ NOVO: Consultar CE/CCT DIRETAMENTE da API (não usar cache/Kanban)
            ce_json_api = None
            cct_json_api = None
            
            logger.info(f'🔍 Iniciando extração de dados para DUIMP - Processo: {processo_referencia}')
            logger.info(f'🔍 ce_data presente: {bool(ce_data)}, cct_data presente: {bool(cct_data)}')
            
            if ce_data:
                numero_ce = ce_data.get('numero', '')
                logger.info(f'🔍 ce_data.numero: {numero_ce} (tamanho: {len(str(numero_ce).strip()) if numero_ce else 0})')
                
                # ✅ REGRA: Todo CE tem 15 dígitos - validar antes de usar
                if numero_ce:
                    numero_ce_str = str(numero_ce).strip()
                    if len(numero_ce_str) != 15:
                        logger.warning(f'⚠️ Número do CE em ce_data não tem 15 dígitos: {numero_ce_str} (tamanho: {len(numero_ce_str)})')
                        # Tentar buscar do JSON completo
                        ce_json_temp = ce_data.get('dados_completos', {})
                        if isinstance(ce_json_temp, str):
                            import json
                            try:
                                ce_json_temp = json.loads(ce_json_temp)
                            except:
                                ce_json_temp = {}
                        # Buscar número do CE completo (15 dígitos) do JSON
                        numero_ce_completo = ce_json_temp.get('numero', '') or ce_json_temp.get('numeroConhecimento', '')
                        if numero_ce_completo and len(str(numero_ce_completo).strip()) == 15:
                            numero_ce = str(numero_ce_completo).strip()
                            logger.info(f'✅ Número do CE corrigido para 15 dígitos: {numero_ce}')
                        else:
                            logger.error(f'❌ Não foi possível encontrar número do CE com 15 dígitos no ce_data')
                    else:
                        numero_ce = numero_ce_str
                    
                    logger.info(f'🔍 Consultando CE {numero_ce} diretamente da API (15 dígitos)...')
                    try:
                        from services.agents.ce_agent import CeAgent
                        ce_agent = CeAgent()
                        resultado_ce = ce_agent._consultar_ce_maritimo({
                            'numero_ce': numero_ce,
                            'processo_referencia': processo_referencia
                        }, context={})
                        
                        if resultado_ce and resultado_ce.get('sucesso'):
                            # Extrair JSON do CE da resposta
                            # A resposta pode ter 'dados' (dict) ou 'resposta' (string formatada)
                            # Se tiver 'dados', usar diretamente; se não, tentar extrair do JSON completo
                            ce_dados_api = resultado_ce.get('dados', {})
                            
                            logger.info(f'🔍 Resultado da consulta do CE {numero_ce}: sucesso={resultado_ce.get("sucesso")}, tipo_dados={type(ce_dados_api)}, tem_dados={bool(ce_dados_api)}')
                            
                            # Se 'dados' é um dict, usar diretamente
                            if isinstance(ce_dados_api, dict) and ce_dados_api:
                                ce_json_api = ce_dados_api
                                logger.info(f'✅ CE {numero_ce} consultado diretamente da API (dados diretos) - keys: {list(ce_json_api.keys())[:10]}')
                            else:
                                # Tentar buscar do JSON completo do cache (que foi atualizado pela consulta)
                                logger.info(f'🔍 Dados da API não são dict válido, tentando buscar do cache atualizado...')
                                try:
                                    from db_manager import buscar_ce_cache
                                    ce_cache_atualizado = buscar_ce_cache(numero_ce)
                                    if ce_cache_atualizado and ce_cache_atualizado.get('json_completo'):
                                        ce_json_str = ce_cache_atualizado.get('json_completo', '')
                                        if isinstance(ce_json_str, str):
                                            import json
                                            ce_json_api = json.loads(ce_json_str)
                                            logger.info(f'✅ CE {numero_ce} consultado diretamente da API (via cache atualizado) - keys: {list(ce_json_api.keys())[:10]}')
                                        else:
                                            ce_json_api = ce_json_str
                                            logger.info(f'✅ CE {numero_ce} consultado diretamente da API (cache já é dict) - keys: {list(ce_json_api.keys())[:10] if isinstance(ce_json_api, dict) else "não é dict"}')
                                    else:
                                        logger.warning(f'⚠️ Resposta da API do CE não contém dados válidos e cache não encontrado')
                                except Exception as e:
                                    logger.error(f'❌ Erro ao buscar CE do cache após consulta: {e}', exc_info=True)
                        else:
                            logger.warning(f'⚠️ Consulta do CE {numero_ce} não retornou sucesso: {resultado_ce}')
                    except Exception as e:
                        logger.error(f'❌ Erro ao consultar CE {numero_ce} da API: {e}', exc_info=True)
            
            elif cct_data:
                numero_cct = cct_data.get('ruc', '') or cct_data.get('numero', '')
                if numero_cct:
                    logger.info(f'🔍 Consultando CCT {numero_cct} diretamente da API...')
                    try:
                        from services.agents.cct_agent import CctAgent
                        cct_agent = CctAgent()
                        resultado_cct = cct_agent._consultar_cct({
                            'numero_cct': numero_cct,
                            'processo_referencia': processo_referencia
                        }, context={})
                        
                        if resultado_cct and resultado_cct.get('sucesso'):
                            # Extrair JSON do CCT da resposta
                            cct_dados_api = resultado_cct.get('dados', {})
                            if isinstance(cct_dados_api, dict):
                                cct_json_api = cct_dados_api
                                logger.info(f'✅ CCT {numero_cct} consultado diretamente da API')
                            else:
                                logger.warning(f'⚠️ Resposta da API do CCT não contém dados válidos')
                    except Exception as e:
                        logger.error(f'❌ Erro ao consultar CCT {numero_cct} da API: {e}', exc_info=True)
            
            # ✅ Se não conseguiu consultar da API, usar dados do cache como fallback
            if not ce_json_api and not cct_json_api:
                logger.warning(f'⚠️ Não foi possível consultar CE/CCT da API, usando dados do cache como fallback')
                if ce_data:
                    ce_json_api = ce_data.get('dados_completos', {})
                    if isinstance(ce_json_api, str):
                        import json
                        try:
                            ce_json_api = json.loads(ce_json_api)
                        except:
                            ce_json_api = {}
                elif cct_data:
                    cct_json_api = cct_data.get('dados_completos', {})
                    if isinstance(cct_json_api, str):
                        import json
                        try:
                            cct_json_api = json.loads(cct_json_api)
                        except:
                            cct_json_api = {}
            
            # 3. Extrair CNPJ/CPF do importador (da API, não do cache/Kanban)
            cpf_cnpj = None
            if ce_json_api:
                # ✅ Usar dados da API do CE (consultado diretamente)
                cpf_cnpj = ce_json_api.get('cpfCnpjConsignatario', '')
                logger.info(f'🔍 CNPJ/CPF extraído da API do CE: {cpf_cnpj if cpf_cnpj else "NÃO ENCONTRADO"}')
            elif cct_json_api:
                # ✅ Usar dados da API do CCT (consultado diretamente)
                cpf_cnpj = cct_json_api.get('identificacaoDocumentoConsignatario', '')
                logger.info(f'🔍 CNPJ/CPF extraído da API do CCT: {cpf_cnpj if cpf_cnpj else "NÃO ENCONTRADO"}')
            else:
                # ✅ Fallback: Tentar do cache se API não funcionou
                if ce_data:
                    ce_json = ce_data.get('dados_completos', {})
                    if isinstance(ce_json, str):
                        import json
                        try:
                            ce_json = json.loads(ce_json)
                        except:
                            ce_json = {}
                    cpf_cnpj = ce_json.get('cpfCnpjConsignatario', '') or ce_data.get('cpf_cnpj_consignatario', '')
                elif cct_data:
                    cct_json = cct_data.get('dados_completos', {})
                    if isinstance(cct_json, str):
                        import json
                        try:
                            cct_json = json.loads(cct_json)
                        except:
                            cct_json = {}
                    cpf_cnpj = cct_json.get('identificacaoDocumentoConsignatario', '') or cct_data.get('identificacao_documento_consignatario', '')
            
            if not cpf_cnpj or not str(cpf_cnpj).strip():
                logger.warning(f'⚠️ CNPJ/CPF do importador não encontrado para processo {processo_referencia}')
                return None
            
            # Limpar CNPJ/CPF (remover pontos, traços, barras)
            # ✅ IMPORTANTE: Usar CNPJ COMPLETO (14 dígitos), não apenas raiz
            # A API da DUIMP precisa do CNPJ completo para identificar o importador corretamente
            cpf_cnpj_limpo = str(cpf_cnpj).strip().replace('.', '').replace('-', '').replace('/', '')
            tipo_importador = 'CNPJ' if len(cpf_cnpj_limpo) == 14 else 'CPF' if len(cpf_cnpj_limpo) == 11 else 'CNPJ'
            
            # 4. Extrair número do CE/CCT (da API, não do cache/Kanban)
            # ✅ IMPORTANTE: Para CE, usar o número completo de 15 dígitos (não o BL)
            numero_ce_cct_original = None
            numero_ce_cct = None
            tipo_identificacao = None
            if ce_json_api:
                # ✅ REGRA: Todo CE tem 15 dígitos - O campo 'identificacao' da carga DEVE ser o número do CE completo (15 dígitos)
                # NÃO usar numeroBlConhecimento (que é o BL, pode ter tamanho variável)
                # Prioridade: número usado para consultar a API (se tiver 15 dígitos) > numero do JSON > numeroConhecimento
                
                # ✅ REGRA: Priorizar o número do CE que foi usado para consultar a API (se tiver 15 dígitos)
                # Este é o número mais confiável, pois foi usado para buscar o CE na API
                numero_ce_consulta = None
                if ce_data:
                    numero_ce_consulta = ce_data.get('numero', '')
                    logger.info(f'🔍 ce_data.numero para extração: {numero_ce_consulta} (tamanho: {len(str(numero_ce_consulta).strip()) if numero_ce_consulta else 0})')
                    # Se não tem 15 dígitos, tentar buscar do JSON completo
                    if numero_ce_consulta and len(str(numero_ce_consulta).strip()) != 15:
                        ce_json_temp = ce_data.get('dados_completos', {})
                        if isinstance(ce_json_temp, str):
                            import json
                            try:
                                ce_json_temp = json.loads(ce_json_temp)
                            except:
                                ce_json_temp = {}
                        numero_ce_completo = ce_json_temp.get('numero', '') or ce_json_temp.get('numeroConhecimento', '')
                        if numero_ce_completo and len(str(numero_ce_completo).strip()) == 15:
                            numero_ce_consulta = str(numero_ce_completo).strip()
                            logger.info(f'✅ Número do CE corrigido do ce_data para 15 dígitos: {numero_ce_consulta}')
                
                if numero_ce_consulta and len(str(numero_ce_consulta).strip()) == 15:
                    numero_ce_cct_original = str(numero_ce_consulta).strip()
                    logger.info(f'✅ Usando número do CE da consulta (15 dígitos): {numero_ce_cct_original}')
                else:
                    # Tentar buscar do JSON do CE - NUNCA usar numeroBlConhecimento aqui
                    numero_ce_cct_original = (
                        ce_json_api.get('numero', '') or
                        ce_json_api.get('numeroConhecimento', '') or
                        ce_json_api.get('numeroCE', '')
                    )
                    numero_ce_cct_original = str(numero_ce_cct_original).strip() if numero_ce_cct_original else ''
                    logger.info(f'🔍 Número CE do JSON: {numero_ce_cct_original} (tamanho: {len(numero_ce_cct_original)})')
                
                tipo_identificacao = 'CE'
                
                # ✅ VALIDAÇÃO CRÍTICA: Deve ter exatamente 15 dígitos
                if not numero_ce_cct_original or len(numero_ce_cct_original) != 15:
                    logger.error(f'❌ ERRO CRÍTICO: Número do CE não tem 15 dígitos: "{numero_ce_cct_original}" (tamanho: {len(numero_ce_cct_original)})')
                    logger.error(f'   ce_data.numero: {ce_data.get("numero", "") if ce_data else "N/A"}')
                    logger.error(f'   ce_json_api keys: {list(ce_json_api.keys())[:30] if isinstance(ce_json_api, dict) else "não é dict"}')
                    # Tentar buscar outros campos que possam ter o número completo
                    numero_ce_alternativo = ce_json_api.get('numeroConhecimento', '') or ce_json_api.get('numeroCE', '')
                    if numero_ce_alternativo and len(str(numero_ce_alternativo).strip()) == 15:
                        numero_ce_cct_original = str(numero_ce_alternativo).strip()
                        logger.info(f'✅ Número do CE corrigido para: {numero_ce_cct_original}')
                    else:
                        logger.error(f'❌ Não foi possível encontrar número do CE com 15 dígitos')
                        return None  # Não pode continuar sem número válido
            elif cct_json_api:
                # ✅ Usar dados da API do CCT
                numero_ce_cct_original = cct_json_api.get('ruc', '') or cct_json_api.get('identificacao', '')
                tipo_identificacao = 'RUC'
                logger.info(f'🔍 Número CCT/RUC (da API): {numero_ce_cct_original}')
            else:
                # ✅ Fallback: Usar dados do cache se API não funcionou
                if ce_data:
                    ce_json = ce_data.get('dados_completos', {})
                    if isinstance(ce_json, str):
                        import json
                        try:
                            ce_json = json.loads(ce_json)
                        except:
                            ce_json = {}
                    # ✅ REGRA: Todo CE tem 15 dígitos - NUNCA usar numeroBlConhecimento (BL) aqui
                    # Priorizar número do CE completo (15 dígitos) sobre BL
                    numero_ce_cct_original = ce_data.get('numero', '') or ce_json.get('numeroConhecimento', '') or ce_json.get('numeroCE', '')
                    # ✅ Validar que tem 15 dígitos
                    if numero_ce_cct_original and len(str(numero_ce_cct_original).strip()) != 15:
                        logger.warning(f'⚠️ Número do CE do cache não tem 15 dígitos: {numero_ce_cct_original} (tamanho: {len(str(numero_ce_cct_original).strip())})')
                        # Tentar buscar outros campos
                        numero_ce_alternativo = ce_json.get('numeroCE', '')
                        if numero_ce_alternativo and len(str(numero_ce_alternativo).strip()) == 15:
                            numero_ce_cct_original = numero_ce_alternativo
                            logger.info(f'✅ Número do CE corrigido do cache: {numero_ce_cct_original}')
                        else:
                            logger.error(f'❌ Não foi possível encontrar número do CE com 15 dígitos no cache')
                    tipo_identificacao = 'CE'
                elif cct_data:
                    cct_json = cct_data.get('dados_completos', {})
                    if isinstance(cct_json, str):
                        import json
                        try:
                            cct_json = json.loads(cct_json)
                        except:
                            cct_json = {}
                    numero_ce_cct_original = cct_json.get('ruc', '') or cct_data.get('ruc', '')
                    tipo_identificacao = 'RUC'
            
            # ✅ REGRA: Ajustar CE para ambiente
            # - VALIDAÇÃO: Substituir últimos 2 dígitos por "02" (ex: 132505371482300 → 132505371482302)
            # - PRODUÇÃO: Usar número completo (15 dígitos) sem alteração
            # IMPORTANTE: Todo CE tem 15 dígitos - validar antes de ajustar
            if tipo_identificacao == 'CE':
                if not numero_ce_cct_original or len(str(numero_ce_cct_original).strip()) != 15:
                    logger.error(f'❌ ERRO CRÍTICO: Número do CE não tem 15 dígitos antes do ajuste: "{numero_ce_cct_original}" (tamanho: {len(str(numero_ce_cct_original).strip()) if numero_ce_cct_original else 0})')
                    return None
                
                # ✅ Ajustar para ambiente: validação = últimos 2 dígitos = "02", produção = completo
                numero_ce_cct = self._ajustar_ce_para_ambiente(numero_ce_cct_original, ambiente)
                logger.info(f'🔍 Número CE ajustado: {numero_ce_cct_original} → {numero_ce_cct} (ambiente: {ambiente})')
                
                # ✅ Validar que o número ajustado ainda tem 15 dígitos
                if len(str(numero_ce_cct).strip()) != 15:
                    logger.error(f'❌ ERRO CRÍTICO: Número do CE ajustado não tem 15 dígitos: "{numero_ce_cct}" (tamanho: {len(str(numero_ce_cct).strip())})')
                    return None
            else:
                # Para CCT, não precisa ajustar
                numero_ce_cct = str(numero_ce_cct_original).strip() if numero_ce_cct_original else None
            
            if not numero_ce_cct or not str(numero_ce_cct).strip():
                logger.error(f'❌ Número do CE/CCT não encontrado para processo {processo_referencia}')
                logger.error(f'   ce_json_api: {bool(ce_json_api)}, cct_json_api: {bool(cct_json_api)}')
                logger.error(f'   numero_ce_cct_original: {numero_ce_cct_original}')
                logger.error(f'   tipo_identificacao: {tipo_identificacao}')
                if ce_json_api:
                    logger.error(f'   ce_json_api keys: {list(ce_json_api.keys())[:20] if isinstance(ce_json_api, dict) else "não é dict"}')
                if cct_json_api:
                    logger.error(f'   cct_json_api keys: {list(cct_json_api.keys())[:20] if isinstance(cct_json_api, dict) else "não é dict"}')
                return None
            
            numero_ce_cct = str(numero_ce_cct).strip()
            
            # 5. Extrair UL Destino Final (da API, não do cache/Kanban)
            ul_destino_final = None
            if ce_json_api:
                # ✅ Usar dados da API do CE
                ul_destino_final = ce_json_api.get('ulDestinoFinal', '')
                logger.info(f'🔍 UL Destino Final (da API do CE): {ul_destino_final}')
            elif cct_json_api:
                # ✅ Usar dados da API do CCT
                ul_destino_final = cct_json_api.get('unidadeRfb', '') or cct_json_api.get('recintoAduaneiroDestino', '')
                logger.info(f'🔍 UL Destino Final (da API do CCT): {ul_destino_final}')
            else:
                # ✅ Fallback: Usar dados do cache se API não funcionou
                if ce_data:
                    ul_destino_final = ce_data.get('ul_destino_final', '')
                    if not ul_destino_final:
                        ce_json = ce_data.get('dados_completos', {})
                        if isinstance(ce_json, str):
                            import json
                            try:
                                ce_json = json.loads(ce_json)
                            except:
                                ce_json = {}
                        ul_destino_final = ce_json.get('ulDestinoFinal', '')
                elif cct_data:
                    cct_json = cct_data.get('dados_completos', {})
                    if isinstance(cct_json, str):
                        import json
                        try:
                            cct_json = json.loads(cct_json)
                        except:
                            cct_json = {}
                    ul_destino_final = cct_json.get('unidadeRfb', '') or cct_json.get('recintoAduaneiroDestino', '')
            
            if not ul_destino_final or not str(ul_destino_final).strip():
                logger.warning(f'⚠️ UL Destino Final não encontrada para processo {processo_referencia}')
                # Usar padrão temporário
                ul_destino_final = '0717600'
            
            ul_destino_final = str(ul_destino_final).strip()
            
            # 6. Extrair País de Procedência (da API, não do cache/Kanban)
            # ✅ IMPORTANTE: O país de procedência SEMPRE vem no CE
            pais_procedencia = None
            if ce_json_api:
                # ✅ Usar dados da API do CE - tentar múltiplos campos possíveis
                pais_procedencia = (
                    ce_json_api.get('paisProcedencia', '') or
                    ce_json_api.get('paisProcedenciaCodigo', '') or
                    (ce_json_api.get('paisProcedencia', {}).get('codigo', '') if isinstance(ce_json_api.get('paisProcedencia'), dict) else '') or
                    ce_json_api.get('paisOrigem', '') or
                    ce_json_api.get('paisOrigemCodigo', '') or
                    (ce_json_api.get('paisOrigem', {}).get('codigo', '') if isinstance(ce_json_api.get('paisOrigem'), dict) else '')
                )
                
                # ✅ Se ainda não encontrou, buscar em estruturas aninhadas
                if not pais_procedencia:
                    # Tentar em portoOrigem ou origem
                    porto_origem = ce_json_api.get('portoOrigem', {})
                    if isinstance(porto_origem, dict):
                        pais_dict = porto_origem.get('pais', {})
                        if isinstance(pais_dict, dict):
                            pais_procedencia = pais_dict.get('codigo', '')
                    
                    # Tentar em origem
                    if not pais_procedencia:
                        origem = ce_json_api.get('origem', {})
                        if isinstance(origem, dict):
                            pais_dict = origem.get('pais', {})
                            if isinstance(pais_dict, dict):
                                pais_procedencia = pais_dict.get('codigo', '')
                
                logger.info(f'🔍 País de Procedência (da API do CE): {pais_procedencia if pais_procedencia else "NÃO ENCONTRADO"}')
                if not pais_procedencia:
                    logger.warning(f'⚠️ País de procedência não encontrado no CE. Keys disponíveis: {list(ce_json_api.keys())[:30] if isinstance(ce_json_api, dict) else "não é dict"}')
            elif cct_json_api:
                # Para CCT, converter código IATA do aeroporto para país (da API)
                codigo_aeroporto = cct_json_api.get('codigoAeroportoOrigemConhecimento', '')
                if codigo_aeroporto:
                    pais_procedencia = iata_to_country_code(codigo_aeroporto)
                    if pais_procedencia:
                        logger.info(f'✅ País de procedência convertido de IATA {codigo_aeroporto} → {pais_procedencia} (da API)')
                    else:
                        logger.warning(f'⚠️ Não foi possível converter código IATA {codigo_aeroporto} para país')
            else:
                # ✅ Fallback: Usar dados do cache se API não funcionou
                if ce_data:
                    # Tentar múltiplos campos possíveis
                    ce_json = ce_data.get('dados_completos', {})
                    if isinstance(ce_json, str):
                        import json
                        try:
                            ce_json = json.loads(ce_json)
                        except:
                            ce_json = {}
                    
                    pais_procedencia = (
                        ce_data.get('pais_procedencia', '') or
                        ce_json.get('paisProcedencia', '') or
                        ce_json.get('paisProcedenciaCodigo', '') or
                        (ce_json.get('paisProcedencia', {}).get('codigo', '') if isinstance(ce_json.get('paisProcedencia'), dict) else '') or
                        ce_json.get('paisOrigem', '') or
                        ce_json.get('paisOrigemCodigo', '') or
                        (ce_json.get('paisOrigem', {}).get('codigo', '') if isinstance(ce_json.get('paisOrigem'), dict) else '')
                    )
                    
                    # Se ainda não encontrou, buscar em estruturas aninhadas
                    if not pais_procedencia and isinstance(ce_json, dict):
                        porto_origem = ce_json.get('portoOrigem', {})
                        if isinstance(porto_origem, dict):
                            pais_dict = porto_origem.get('pais', {})
                            if isinstance(pais_dict, dict):
                                pais_procedencia = pais_dict.get('codigo', '')
                        
                        if not pais_procedencia:
                            origem = ce_json.get('origem', {})
                            if isinstance(origem, dict):
                                pais_dict = origem.get('pais', {})
                                if isinstance(pais_dict, dict):
                                    pais_procedencia = pais_dict.get('codigo', '')
                    
                    logger.info(f'🔍 País de Procedência (fallback cache): {pais_procedencia if pais_procedencia else "NÃO ENCONTRADO"}')
            
            # 7. Criar documento tipo 30 (CE/CCT)
            documento_tipo_30 = None
            if ce_json_api or (ce_data and not ce_json_api):
                # ✅ Usar dados da API do CE (ou fallback do cache)
                ce_json_final = ce_json_api if ce_json_api else (ce_data.get('dados_completos', {}) if isinstance(ce_data.get('dados_completos'), dict) else {})
                
                # ✅ IMPORTANTE: 
                # - campo 'carga.identificacao' = número do CE completo (15 dígitos, ajustado para ambiente) ✅ JÁ CORRETO
                # - campo 'documentos.documentosInstrucao[0].palavrasChave[0].valor' = BL (numeroBlConhecimento) ❌ PRECISA CORRIGIR
                
                # ✅ Extrair BL (numeroBlConhecimento) para usar na palavra-chave do documento tipo 30
                # O BL é diferente do número do CE - o BL é o número do conhecimento de embarque (ex: ZSSZX25092012, SZ25101078)
                bl_conhecimento = None
                
                # Prioridade 1: Buscar do ce_json_api (dados da API) - mais confiável
                if ce_json_api and isinstance(ce_json_api, dict):
                    bl_conhecimento = (
                        ce_json_api.get('numeroBlConhecimento', '') or
                        ce_json_api.get('blConhecimento', '') or
                        ce_json_api.get('bl', '') or
                        ce_json_api.get('numeroBl', '') or
                        ce_json_api.get('blNumero', '')
                    )
                    logger.info(f'🔍 Tentando extrair BL do ce_json_api. numeroBlConhecimento: {ce_json_api.get("numeroBlConhecimento", "NÃO ENCONTRADO")}')
                
                # Prioridade 2: Se não encontrou, tentar do ce_json_final (fallback)
                if not bl_conhecimento and isinstance(ce_json_final, dict):
                    bl_conhecimento = (
                        ce_json_final.get('numeroBlConhecimento', '') or
                        ce_json_final.get('blConhecimento', '') or
                        ce_json_final.get('bl', '') or
                        ce_json_final.get('numeroBl', '') or
                        ce_json_final.get('blNumero', '')
                    )
                    logger.info(f'🔍 Tentando extrair BL do ce_json_final. numeroBlConhecimento: {ce_json_final.get("numeroBlConhecimento", "NÃO ENCONTRADO")}')
                
                # Prioridade 2: Se não encontrou, tentar do ce_data (cache)
                if not bl_conhecimento and ce_data:
                    ce_json_temp = ce_data.get('dados_completos', {})
                    if isinstance(ce_json_temp, str):
                        import json
                        try:
                            ce_json_temp = json.loads(ce_json_temp)
                        except:
                            ce_json_temp = {}
                    if isinstance(ce_json_temp, dict):
                        bl_conhecimento = (
                            ce_json_temp.get('numeroBlConhecimento', '') or
                            ce_json_temp.get('blConhecimento', '') or
                            ce_json_temp.get('bl', '') or
                            ce_json_temp.get('numeroBl', '') or
                            ce_json_temp.get('blNumero', '')
                        )
                        logger.info(f'🔍 Tentando extrair BL do ce_data (cache). numeroBlConhecimento: {ce_json_temp.get("numeroBlConhecimento", "NÃO ENCONTRADO")}')
                
                # ✅ Se não encontrou BL, usar o número do CE como fallback (mas não é ideal)
                if not bl_conhecimento or not str(bl_conhecimento).strip():
                    logger.warning(f'⚠️ BL (numeroBlConhecimento) não encontrado, usando número do CE como fallback')
                    bl_conhecimento = numero_ce_cct
                else:
                    bl_conhecimento = str(bl_conhecimento).strip()
                    logger.info(f'✅ BL (numeroBlConhecimento) encontrado: {bl_conhecimento}')
                
                documento_tipo_30 = {
                    'tipo': {
                        'codigo': '30'
                    },
                    'palavrasChave': [
                        {
                            'codigo': 1,
                            'valor': bl_conhecimento  # ✅ BL (numeroBlConhecimento), não o número do CE
                        }
                    ]
                }
            elif cct_json_api or (cct_data and not cct_json_api):
                # ✅ Usar dados da API do CCT (ou fallback do cache)
                cct_json_final = cct_json_api if cct_json_api else (cct_data.get('dados_completos', {}) if isinstance(cct_data.get('dados_completos'), dict) else {})
                
                # Para CCT, usar identificacao (AWB) como palavra-chave
                identificacao_cct = cct_json_final.get('identificacao', '') if isinstance(cct_json_final, dict) else numero_ce_cct
                if not identificacao_cct:
                    identificacao_cct = numero_ce_cct
                
                documento_tipo_30 = {
                    'tipo': {
                        'codigo': '30'
                    },
                    'palavrasChave': [
                        {
                            'codigo': 1,
                            'valor': identificacao_cct  # AWB do CCT
                        }
                    ]
                }
            
            if not documento_tipo_30:
                logger.warning(f'⚠️ Não foi possível criar documento tipo 30 para processo {processo_referencia}')
                return None
            
            # 8. Montar payload final
            payload_duimp = {
                'identificacao': {
                    'importador': {
                        'tipoImportador': tipo_importador,
                        'ni': cpf_cnpj_limpo
                    }
                },
                'carga': {
                    'tipoIdentificacaoCarga': tipo_identificacao,  # 'CE' ou 'RUC'
                    'identificacao': numero_ce_cct,
                    'unidadeDeclarada': {
                        'codigo': ul_destino_final
                    }
                },
                'documentos': {
                    'documentosInstrucao': [documento_tipo_30]
                }
            }
            
            # 9. Adicionar país de procedência (opcional mas recomendado)
            if pais_procedencia:
                payload_duimp['carga']['paisProcedencia'] = {
                    'codigo': pais_procedencia
                }
            
            logger.info(f'✅ Payload da DUIMP montado com sucesso para processo {processo_referencia}')
            return payload_duimp
            
        except Exception as e:
            logger.error(f'❌ Erro ao extrair dados do processo {processo_referencia} para DUIMP: {e}', exc_info=True)
            return None
    
    def _criar_duimp(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Cria uma DUIMP para um processo de importação.
        
        Fluxo:
        1. Extrai dados do processo e monta payload da capa
        2. Mostra informações básicas para o usuário validar
        3. Após confirmação, cria a DUIMP via POST /duimp-api/api/ext/duimp
        
        Args:
            arguments: {
                'processo_referencia': str (obrigatório),
                'ambiente': str ('validacao' ou 'producao', padrão: 'validacao'),
                'confirmar': bool (True se usuário confirmou, False para mostrar dados)
            }
            context: Contexto adicional (pode conter chat_service para acessar métodos auxiliares)
        
        Returns:
            Dict com informações do processo e confirmação para criação, ou resultado da criação
        """
        processo_ref = arguments.get('processo_referencia', '').strip()
        # ✅ PADRÃO: Usar VALIDAÇÃO por padrão (mais seguro para testes)
        ambiente = arguments.get('ambiente', 'validacao').lower().strip()
        if ambiente not in ['validacao', 'producao']:
            ambiente = 'validacao'  # Fallback para validação se ambiente inválido
        # ✅ CRÍTICO: SEMPRE mostrar resumo primeiro, a menos que explicitamente confirmado pelo usuário
        # Isso garante que o usuário veja os dados antes de criar
        confirmar = arguments.get('confirmar', False)
        # ✅ SEGURANÇA: Se confirmar não for explicitamente True (bool), forçar False
        if not isinstance(confirmar, bool):
            confirmar = False
        
        # Validar argumentos
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'processo_referencia é obrigatório',
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = extract_processo_referencia(processo_ref)
        if not processo_completo:
            processo_completo = processo_ref
        
        # Validar formato
        valido, msg_erro = validate_processo_referencia(processo_completo)
        if not valido:
            return {
                'sucesso': False,
                'erro': msg_erro,
                'resposta': f'❌ {msg_erro}'
            }
        
        # ✅ NOVO: Verificar LPCO antes de permitir criação de DUIMP
        # Se o processo TEM LPCO, ele só pode registrar DI/DUIMP se o LPCO estiver DEFERIDO
        try:
            from db_manager import get_db_connection
            import sqlite3
            import json
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT dados_completos_json
                FROM processos_kanban
                WHERE processo_referencia = ?
                LIMIT 1
            ''', (processo_completo,))
            row = cursor.fetchone()
            conn.close()
            
            if row and row['dados_completos_json']:
                dados_json = json.loads(row['dados_completos_json'])
                
                # Buscar LPCO no JSON
                lpco_data = None
                if dados_json.get('lpco') or dados_json.get('lpcoDetails'):
                    lpco_data = dados_json.get('lpco') or dados_json.get('lpcoDetails')
                    
                    # Se for lista, pegar o primeiro
                    if isinstance(lpco_data, list) and len(lpco_data) > 0:
                        lpco_data = lpco_data[0]
                
                if lpco_data:
                    numero_lpco = lpco_data.get('LPCO') or lpco_data.get('numero_lpco') or lpco_data.get('numero')
                    situacao_lpco = lpco_data.get('situacao') or lpco_data.get('situacao_lpco') or lpco_data.get('status')
                    
                    # Verificar se está deferido
                    if situacao_lpco:
                        situacao_lpco_lower = str(situacao_lpco).lower()
                        lpco_deferido = 'deferido' in situacao_lpco_lower
                        
                        if not lpco_deferido:
                            return {
                                'sucesso': False,
                                'erro': 'LPCO_NAO_DEFERIDO',
                                'resposta': f'❌ **Não é possível criar DUIMP para o processo {processo_completo}.**\n\n'
                                           f'⚠️ **O processo possui LPCO {numero_lpco} que não está deferido.**\n\n'
                                           f'**Situação atual:** {situacao_lpco}\n\n'
                                           f'💡 **Regra:** Processos com LPCO só podem registrar DI/DUIMP após o LPCO ser deferido.\n\n'
                                           f'Por favor, aguarde a deferência do LPCO antes de criar a DUIMP.'
                            }
        except Exception as e:
            logger.warning(f'Erro ao verificar LPCO do processo {processo_completo}: {e}')
            # Se houver erro ao verificar LPCO, continuar (não bloquear criação por erro técnico)
        
        # ✅ NOVO: Se usuário confirmou, criar DUIMP diretamente
        if confirmar:
            return self._executar_criacao_duimp(processo_completo, ambiente, context)
        
        # ✅ NOVO: Extrair dados e montar payload da capa (passar ambiente para ajustar CE)
        payload_duimp = self.extrair_dados_processo_para_duimp(processo_completo, ambiente=ambiente)
        
        if not payload_duimp:
            return {
                'sucesso': False,
                'erro': 'DADOS_INSUFICIENTES',
                'resposta': f'❌ **Não foi possível extrair dados do processo {processo_completo} para criar a DUIMP.**\n\n'
                           f'💡 **Verifique:**\n'
                           f'   - Se o processo tem CE ou CCT vinculado\n'
                           f'   - Se o CE/CCT tem CNPJ/CPF do importador\n'
                           f'   - Se o CE/CCT tem número válido'
            }
        
        # ✅ NOVO: Mostrar informações da capa para validação (formato mais humano)
        resposta_info = f"📋 **Capa da DUIMP - Processo {processo_completo}**\n\n"
        resposta_info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Informações do Importador
        importador = payload_duimp.get('identificacao', {}).get('importador', {})
        tipo_importador = importador.get('tipoImportador', 'CNPJ')
        ni_importador = importador.get('ni', '')
        
        # Formatar CNPJ/CPF para exibição (adicionar pontos/traços)
        ni_formatado = ni_importador
        if tipo_importador == 'CNPJ' and len(ni_importador) == 14:
            ni_formatado = f"{ni_importador[:2]}.{ni_importador[2:5]}.{ni_importador[5:8]}/{ni_importador[8:12]}-{ni_importador[12:]}"
        elif tipo_importador == 'CPF' and len(ni_importador) == 11:
            ni_formatado = f"{ni_importador[:3]}.{ni_importador[3:6]}.{ni_importador[6:9]}-{ni_importador[9:]}"
        
        resposta_info += f"**👤 Importador**\n"
        resposta_info += f"   Tipo: {tipo_importador}\n"
        resposta_info += f"   {tipo_importador}: {ni_formatado} ({ni_importador})\n\n"
        
        # Informações da Carga
        carga = payload_duimp.get('carga', {})
        tipo_identificacao = carga.get('tipoIdentificacaoCarga', '')
        identificacao_carga = carga.get('identificacao', '')
        unidade_declarada = carga.get('unidadeDeclarada', {}).get('codigo', '')
        pais_procedencia = carga.get('paisProcedencia', {}).get('codigo', '') if carga.get('paisProcedencia') else None
        
        resposta_info += f"**📦 Carga**\n"
        resposta_info += f"   Tipo de Identificação: {tipo_identificacao}\n"
        resposta_info += f"   Número: {identificacao_carga}\n"
        resposta_info += f"   Unidade Declarada (UL): {unidade_declarada}\n"
        if pais_procedencia:
            resposta_info += f"   País de Procedência: {pais_procedencia}\n"
        else:
            resposta_info += f"   País de Procedência: ⚠️ Não informado\n"
        resposta_info += "\n"
        
        # Informações dos Documentos
        documentos = payload_duimp.get('documentos', {}).get('documentosInstrucao', [])
        resposta_info += f"**📄 Documentos de Instrução**\n"
        for doc in documentos:
            tipo_doc = doc.get('tipo', {}).get('codigo', '')
            palavras_chave = doc.get('palavrasChave', [])
            numero_doc = palavras_chave[0].get('valor', '') if palavras_chave else 'N/A'
            tipo_doc_nome = "Conhecimento de Embarque" if tipo_doc == '30' else f"Tipo {tipo_doc}"
            resposta_info += f"   - {tipo_doc_nome} ({tipo_doc}): {numero_doc}\n"
        resposta_info += "\n"
        resposta_info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Verificar se já tem DUIMP/DI
        contexto_processo = self._obter_contexto_processo(processo_completo, context)
        tem_duimp = False
        tem_di = False
        
        if contexto_processo and contexto_processo.get('encontrado'):
            # CEs
            ces = contexto_processo.get('ces', [])
            if ces:
                resposta_info += "**📦 Conhecimentos de Embarque (CE):**\n"
                for ce in ces:
                    resposta_info += f"  - CE {ce.get('numero', 'N/A')}\n"
                    if ce.get('situacao'):
                        resposta_info += f"    Situação: {ce.get('situacao')}\n"
                    if ce.get('carga_bloqueada'):
                        resposta_info += f"    ⚠️ Carga bloqueada\n"
                resposta_info += "\n"
            
            # CCTs
            ccts = contexto_processo.get('ccts', [])
            if ccts:
                resposta_info += "**✈️ Conhecimentos de Carga Aérea (CCT):**\n"
                for cct in ccts:
                    resposta_info += f"  - RUC {cct.get('ruc', cct.get('numero', 'N/A'))}\n"
                    if cct.get('situacao'):
                        resposta_info += f"    Situação: {cct.get('situacao')}\n"
                resposta_info += "\n"
            
            # Verificar se já tem DUIMP
            tem_duimp, resposta_info = self._verificar_duimp_existente(processo_completo, resposta_info)
            
            # Verificar se já tem DI
            dis = contexto_processo.get('dis', [])
            if dis:
                for di in dis:
                    numero_di = di.get('numero_di', '') or di.get('numero', '')
                    if numero_di:
                        tem_di = True
                        situacao_di = di.get('situacao_di', '') or di.get('situacao', '')
                        if situacao_di and situacao_di.upper() not in ['', 'RASCUNHO', 'RASCUNHO_ANULADO']:
                            resposta_info += f"⚠️ **DI já registrada:** {numero_di}\n\n"
                        else:
                            resposta_info += f"⚠️ **DI existente (rascunho):** {numero_di}\n\n"
                        break
        else:
            resposta_info += "⚠️ Processo não encontrado ou sem documentos vinculados.\n\n"
        
        resposta_info += f"🌐 **Ambiente:** {ambiente.title()}\n\n"
        
        # REGRA: Só perguntar se NÃO tem DUIMP e NÃO tem DI
        if not tem_duimp and not tem_di:
            resposta_info += "❓ **Deseja criar a DUIMP para este processo?**\n\n"
            resposta_info += "💬 Responda 'sim', 'pode prosseguir', 'criar' ou 'confirmar' para criar a DUIMP."
        
        return {
            'sucesso': True,
            'acao': 'criar_duimp',
            'processo_referencia': processo_completo,
            'ambiente': ambiente,
            'resposta': resposta_info,
            'mostrar_antes_criar': True,
            'payload_duimp': payload_duimp  # ✅ NOVO: Incluir payload para usar na confirmação
        }
    
    def _executar_criacao_duimp(self, processo_referencia: str, ambiente: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa a criação da DUIMP via POST /duimp-api/api/ext/duimp.
        
        Args:
            processo_referencia: Número do processo
            ambiente: 'validacao' ou 'producao'
            context: Contexto adicional
        
        Returns:
            Dict com resultado da criação (número, versão, etc.)
        """
        try:
            # 1. Extrair dados e montar payload (passar ambiente para ajustar CE)
            payload_duimp = self.extrair_dados_processo_para_duimp(processo_referencia, ambiente=ambiente)
            
            if not payload_duimp:
                return {
                    'sucesso': False,
                    'erro': 'DADOS_INSUFICIENTES',
                    'resposta': f'❌ **Não foi possível extrair dados do processo {processo_referencia} para criar a DUIMP.**'
                }
            
            # 2. Determinar base URL conforme ambiente
            # ✅ PADRÃO: Usar VALIDAÇÃO por padrão (mais seguro)
            if ambiente == 'producao':
                post_base = 'https://portalunico.siscomex.gov.br'
            else:
                post_base = 'https://val.portalunico.siscomex.gov.br'
                ambiente = 'validacao'  # Garantir que seja validação se não for produção
            
            # ✅ PROTEÇÃO: Verificar bloqueio de produção
            import os
            allow_prod = os.getenv('DUIMP_ALLOW_WRITE_PROD', '0') in ('1', 'true', 'TRUE')
            
            if ambiente == 'producao' and not allow_prod:
                return {
                    'sucesso': False,
                    'erro': 'AMBIENTE_NAO_PERMITIDO',
                    'resposta': '❌ **POST bloqueado em produção.**\n\n'
                               f'⚠️ Para criar DUIMP em produção, configure a variável de ambiente:\n'
                               f'   `DUIMP_ALLOW_WRITE_PROD=1`\n\n'
                               f'💡 **Recomendação:** Use o ambiente de **VALIDAÇÃO** para testes.\n'
                               f'   O ambiente de produção deve ser usado apenas em casos específicos e com autorização.'
                }
            
            # 3. Autenticação
            import duimp_auth
            from duimp_request import build_session
            from urllib.parse import urljoin
            import requests
            
            settings = duimp_auth.load_settings()
            settings.base_url = post_base
            
            tokens = duimp_auth.obtain_tokens(settings)
            set_token = tokens.get('setToken')
            csrf_token = tokens.get('csrfToken')
            
            if not set_token or not csrf_token:
                return {
                    'sucesso': False,
                    'erro': 'AUTH',
                    'resposta': '❌ **Não foi possível obter tokens de autenticação.**'
                }
            
            # ✅ LOG: Informar ambiente usado
            ambiente_tipo = "PRODUÇÃO" if ambiente == 'producao' else "VALIDAÇÃO"
            logger.info(f'🌐 Criando DUIMP no ambiente: {ambiente_tipo} ({post_base})')
            
            # ✅ LOG: Mostrar payload que será enviado (para debug)
            import json
            payload_str = json.dumps(payload_duimp, indent=2, ensure_ascii=False)
            logger.info(f'📤 Payload da DUIMP que será enviado:\n{payload_str}')
            
            # 4. Criar sessão com certificado mTLS
            session = build_session(settings)
            
            # 5. Montar URL completa
            url = urljoin(post_base.rstrip('/') + '/', '/duimp-api/api/ext/duimp'.lstrip('/'))
            
            # 6. Fazer requisição POST
            try:
                response = session.request(
                    'POST',
                    url,
                    headers={
                        'Authorization': set_token,
                        'X-CSRF-Token': csrf_token,
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                    },
                    json=payload_duimp,
                    timeout=120
                )
                
                logger.info(f'📥 Resposta da API: Status {response.status_code}')
                
                # 7. Processar resposta
                if response.status_code in (200, 201):
                    try:
                        body = response.json()
                    except:
                        body = {'error': 'RESPOSTA_INVALIDA', 'message': response.text}
                    
                    if 'identificacao' in body and 'numero' in body['identificacao']:
                        numero_duimp = body['identificacao'].get('numero')
                        versao_duimp = body['identificacao'].get('versao', '0')
                        
                        # 8. Salvar no banco local
                        try:
                            from db_manager import salvar_duimp
                            salvar_duimp(
                                numero_duimp,
                                versao_duimp,
                                payload_duimp,
                                ambiente=ambiente,
                                processo_referencia=processo_referencia
                            )
                            logger.info(f'✅ DUIMP {numero_duimp} v{versao_duimp} salva no banco local')
                        except Exception as e:
                            logger.warning(f'⚠️ Erro ao salvar DUIMP no banco local: {e}')
                        
                        resposta = f"✅ **DUIMP criada com sucesso!**\n\n"
                        resposta += f"**Número:** {numero_duimp}\n"
                        resposta += f"**Versão:** {versao_duimp}\n"
                        resposta += f"**Ambiente:** {ambiente.title()}\n"
                        resposta += f"**Status:** Rascunho (pode editar)\n\n"
                        resposta += f"💡 **Próximos passos:**\n"
                        resposta += f"   1. Adicionar itens à DUIMP\n"
                        resposta += f"   2. Consultar valores calculados\n"
                        resposta += f"   3. Registrar a DUIMP"
                        
                        return {
                            'sucesso': True,
                            'numero': numero_duimp,
                            'versao': versao_duimp,
                            'ambiente': ambiente,
                            'resposta': resposta
                        }
                    else:
                        error_msg = body.get('message', 'Resposta da API não contém identificação')
                        return {
                            'sucesso': False,
                            'erro': 'RESPOSTA_INVALIDA',
                            'resposta': f'❌ **Erro ao criar DUIMP:** {error_msg}'
                        }
                else:
                    # ✅ LOG: Mostrar resposta completa do erro
                    try:
                        error_body = response.json()
                        error_msg = error_body.get('message', '')
                        error_details = error_body.get('details', [])
                        error_validation = error_body.get('validationErrors', [])
                        
                        logger.error(f'❌ Erro da API (Status {response.status_code}):')
                        logger.error(f'   Mensagem: {error_msg}')
                        if error_details:
                            logger.error(f'   Detalhes: {json.dumps(error_details, indent=2, ensure_ascii=False)}')
                        if error_validation:
                            logger.error(f'   Erros de validação: {json.dumps(error_validation, indent=2, ensure_ascii=False)}')
                        logger.error(f'   Resposta completa: {json.dumps(error_body, indent=2, ensure_ascii=False)}')
                        
                        # Montar mensagem de erro mais detalhada
                        resposta_erro = f'❌ **Erro ao criar DUIMP:**\n\n'
                        if error_msg:
                            resposta_erro += f'**Mensagem:** {error_msg}\n\n'
                        
                        if error_validation:
                            resposta_erro += f'**Erros de validação:**\n'
                            for val_error in error_validation:
                                campo = val_error.get('campo', 'N/A')
                                mensagem = val_error.get('mensagem', 'N/A')
                                resposta_erro += f'   - {campo}: {mensagem}\n'
                            resposta_erro += '\n'
                        
                        if error_details:
                            resposta_erro += f'**Detalhes:**\n'
                            for detail in error_details:
                                resposta_erro += f'   - {detail}\n'
                            resposta_erro += '\n'
                        
                        if not error_msg and not error_validation and not error_details:
                            resposta_erro += f'**Status HTTP:** {response.status_code}\n'
                            resposta_erro += f'**Resposta:** {response.text[:500]}\n'
                        
                        resposta_erro += '\n💡 **Dica:** Verifique os logs do servidor para mais detalhes.'
                        
                    except Exception as e:
                        error_msg = response.text or f'Erro HTTP {response.status_code}'
                        logger.error(f'❌ Erro ao processar resposta de erro: {e}')
                        logger.error(f'   Resposta bruta: {error_msg[:500]}')
                        resposta_erro = f'❌ **Erro ao criar DUIMP:** {error_msg}'
                    
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_API',
                        'resposta': resposta_erro
                    }
            except Exception as e:
                logger.error(f'❌ Erro ao fazer requisição POST para criar DUIMP: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': 'ERRO_EXECUCAO',
                    'resposta': f'❌ **Erro ao criar DUIMP:** {str(e)}'
                }
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f'❌ Erro ao executar criação da DUIMP: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ **Erro interno ao criar DUIMP:** {str(e)}'
            }
    
    def _verificar_duimp_existente(self, processo_referencia: str, resposta_info: str) -> tuple[bool, str]:
        """Verifica se já existe DUIMP para o processo e atualiza resposta_info."""
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT numero, versao, ambiente, status
                FROM duimps
                WHERE processo_referencia = ?
                LIMIT 1
            ''', (processo_referencia,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                duimp_numero = row[0]
                duimp_versao = row[1]
                duimp_ambiente = row[2] or 'producao'
                duimp_status = row[3] or ''
                
                versao_int = int(duimp_versao) if duimp_versao and duimp_versao.isdigit() else 0
                if versao_int >= 1 or (duimp_status and duimp_status.upper() not in ['', 'RASCUNHO', 'RASCUNHO_ANULADO', 'EM_ELABORACAO']):
                    resposta_info += f"⚠️ **DUIMP já registrada:** {duimp_numero} v{duimp_versao} (ambiente: {duimp_ambiente})\n\n"
                else:
                    resposta_info += f"⚠️ **DUIMP existente (rascunho):** {duimp_numero} v{duimp_versao} (ambiente: {duimp_ambiente})\n\n"
                return True, resposta_info
            else:
                resposta_info += "✅ **Pronto para criar DUIMP**\n\n"
                return False, resposta_info
        except Exception as e:
            logger.warning(f'Erro ao verificar DUIMP do processo {processo_referencia}: {e}')
            resposta_info += "✅ **Pronto para criar DUIMP**\n\n"
            return False, resposta_info
    
    def _obter_contexto_processo(self, processo_referencia: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Obtém contexto completo de um processo."""
        try:
            # Tentar usar chat_service se disponível no context
            if context and 'chat_service' in context:
                chat_service = context['chat_service']
                if hasattr(chat_service, '_obter_contexto_processo'):
                    return chat_service._obter_contexto_processo(processo_referencia)
            
            # Fallback: usar db_manager diretamente
            from db_manager import obter_dados_documentos_processo
            dados = obter_dados_documentos_processo(processo_referencia)
            if not dados:
                return {'encontrado': False}
            
            # Formatar contexto
            contexto = {
                'encontrado': True,
                'processo_referencia': processo_referencia,
                'ces': dados.get('ces', []),
                'ccts': dados.get('ccts', []),
                'dis': dados.get('dis', []),
                'resumo': dados.get('resumo', {})
            }
            
            return contexto
        except Exception as e:
            logger.error(f'Erro ao obter contexto do processo {processo_referencia}: {e}')
            return {'encontrado': False}
    
    def _verificar_duimp_registrada(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Verifica se há DUIMP registrada para um processo.
        
        ✅ CRÍTICO: 
        - SEMPRE prioriza DUIMPs de PRODUÇÃO sobre validação
        - DUIMPs de validação são apenas para testes e não devem ser consideradas como produção
        """
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'processo_referencia é obrigatório',
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = extract_processo_referencia(processo_ref)
        if not processo_completo:
            processo_completo = processo_ref
        
        # ✅ CRÍTICO: Verificar DUIMP de PRODUÇÃO primeiro
        duimp_info = self._verificar_duimp_processo(processo_completo)
        
        if duimp_info.get('existe') and duimp_info.get('eh_producao'):
            # ✅ Encontrou DUIMP de PRODUÇÃO
            resposta = f"📋 **DUIMP de PRODUÇÃO encontrada para o processo {processo_completo}:**\n\n"
            resposta += f"**Número:** {duimp_info.get('numero', 'N/A')} v{duimp_info.get('versao', 'N/A')}\n"
            resposta += f"**Situação:** {duimp_info.get('situacao', duimp_info.get('status', 'N/A'))}\n"
            resposta += f"**Ambiente:** Produção\n"
            if duimp_info.get('criado_em'):
                resposta += f"**Criada em:** {duimp_info.get('criado_em')}\n"
        else:
            # ✅ NÃO encontrou DUIMP de PRODUÇÃO - verificar se há de validação
            duimp_validacao = None
            try:
                import sqlite3
                from db_manager import get_db_connection
                
                conn = get_db_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Buscar DUIMP de validação
                cursor.execute('''
                    SELECT numero, versao, status, ambiente, criado_em, payload_completo
                    FROM duimps
                    WHERE processo_referencia = ? AND ambiente = 'validacao'
                    ORDER BY CAST(versao AS INTEGER) DESC, criado_em DESC
                    LIMIT 1
                ''', (processo_completo,))
                
                row_validacao = cursor.fetchone()
                conn.close()
                
                if row_validacao:
                    # Extrair situação do payload
                    situacao_validacao = None
                    try:
                        import json
                        payload_str = row_validacao['payload_completo']
                        if payload_str:
                            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                            if isinstance(payload, dict):
                                situacao_obj = payload.get('situacao', {})
                                if isinstance(situacao_obj, dict):
                                    situacao_validacao = situacao_obj.get('situacaoDuimp', '')
                    except:
                        pass
                    
                    duimp_validacao = {
                        'numero': row_validacao['numero'],
                        'versao': row_validacao['versao'],
                        'status': row_validacao['status'],
                        'situacao': situacao_validacao or row_validacao['status'],
                        'ambiente': 'validacao',
                        'criado_em': row_validacao['criado_em']
                    }
            except Exception as e:
                logger.debug(f'Erro ao buscar DUIMP de validação: {e}')
            
            # Formatar resposta
            resposta = f"⚠️ **DUIMP de PRODUÇÃO:** Não encontrada para o processo {processo_completo}.\n\n"
            
            if duimp_validacao:
                # ✅ Existe DUIMP de validação - informar como informação adicional
                resposta += f"ℹ️ **Informação adicional (ambiente de testes):**\n"
                resposta += f"   - DUIMP {duimp_validacao.get('numero', 'N/A')} v{duimp_validacao.get('versao', 'N/A')}\n"
                resposta += f"   - Situação: {duimp_validacao.get('situacao', 'Rascunho')}\n"
                resposta += f"   - Ambiente: Validação (apenas testes)\n"
                if duimp_validacao.get('criado_em'):
                    resposta += f"   - Criada em: {duimp_validacao.get('criado_em')}\n"
                resposta += f"\n💡 **Nota:** DUIMPs de validação são apenas para testes e não são consideradas como produção.\n"
            else:
                # ✅ Não há nem produção nem validação
                resposta += f"💡 **Nota:** Não há DUIMP de produção nem de validação para este processo.\n"
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'duimp_info': duimp_info
        }
    
    def _obter_dados_duimp(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Obtém dados completos de uma DUIMP com informações relevantes:
        - Situação
        - Data e hora do desembaraço
        - Canal
        - Impostos (II, IPI, PIS, COFINS)
        """
        numero_duimp = arguments.get('numero_duimp', '').strip()
        versao_duimp = arguments.get('versao_duimp', '').strip() or None
        
        if not numero_duimp:
            return {
                'sucesso': False,
                'erro': 'numero_duimp é obrigatório',
                'resposta': '❌ Número da DUIMP é obrigatório.'
            }
        
        try:
            import sqlite3
            import json
            from db_manager import get_db_connection
            from datetime import datetime
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar DUIMP (priorizar produção)
            if versao_duimp:
                cursor.execute('''
                    SELECT numero, versao, ambiente, payload_completo, status
                    FROM duimps
                    WHERE numero = ? AND versao = ?
                    ORDER BY CASE WHEN ambiente = 'producao' THEN 0 ELSE 1 END
                    LIMIT 1
                ''', (numero_duimp, versao_duimp))
            else:
                cursor.execute('''
                    SELECT numero, versao, ambiente, payload_completo, status
                    FROM duimps
                    WHERE numero = ?
                    ORDER BY CASE WHEN ambiente = 'producao' THEN 0 ELSE 1 END,
                             CAST(versao AS INTEGER) DESC
                    LIMIT 1
                ''', (numero_duimp,))
            
            row = cursor.fetchone()
            conn.close()
            
            # ✅ NOVO: Extrair processo_ref do contexto para gravar impostos mesmo quando DUIMP já está no banco
            processo_ref = None
            if context and isinstance(context, dict):
                processo_ref = context.get('processo_referencia') or context.get('processo_atual')
            
            # ✅ NOVO: Se DUIMP já está no banco mas faltam impostos, tentar gravar impostos do payload
            if row and processo_ref:
                try:
                    import json
                    payload_str = row.payload_completo if hasattr(row, 'payload_completo') else None
                    if payload_str:
                        payload_existente = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                        if isinstance(payload_existente, dict):
                            # Verificar se já tem impostos gravados
                            from utils.sql_server_adapter import get_sql_adapter
                            adapter = get_sql_adapter()
                            if adapter:
                                check_sql = f"""
                                    SELECT COUNT(*) as total
                                    FROM mAIke_assistente.dbo.IMPOSTO_IMPORTACAO
                                    WHERE processo_referencia = '{processo_ref.replace("'", "''")}'
                                      AND numero_documento = '{numero_duimp.replace("'", "''")}'
                                      AND tipo_documento = 'DUIMP'
                                """
                                check_result = adapter.execute_query(check_sql, database="mAIke_assistente", notificar_erro=False)
                                tem_impostos = False
                                if isinstance(check_result, dict) and check_result.get("success") and check_result.get("data"):
                                    total = (check_result.get("data") or [{}])[0].get("total", 0)
                                    tem_impostos = total > 0
                                
                                # Se não tem impostos, tentar gravar do payload
                                if not tem_impostos:
                                    logger.info(f'🔍 DUIMP {numero_duimp} encontrada no banco mas sem impostos. Tentando gravar do payload...')
                                    # Usar mesma lógica de gravação de impostos (código abaixo será reutilizado)
                                    tributos = payload_existente.get('tributos', {})
                                    if isinstance(tributos, dict):
                                        tributos_calculados = tributos.get('tributosCalculados', [])
                                    else:
                                        tributos_calculados = []
                                    
                                    if not tributos_calculados:
                                        pagamentos = payload_existente.get('pagamentos', [])
                                        if isinstance(pagamentos, list):
                                            for pagamento in pagamentos:
                                                if isinstance(pagamento, dict):
                                                    principal = pagamento.get('principal', {})
                                                    if isinstance(principal, dict):
                                                        tributo = principal.get('tributo', {})
                                                        if isinstance(tributo, dict):
                                                            tipo = tributo.get('tipo', '')
                                                            valor = principal.get('valor', 0)
                                                            if tipo and valor:
                                                                tributos_calculados.append({
                                                                    'tipo': tipo,
                                                                    'valoresBRL': {'devido': valor}
                                                                })
                                    
                                    if tributos_calculados and isinstance(tributos_calculados, list):
                                        impostos_para_gravar = []
                                        for tributo in tributos_calculados:
                                            if isinstance(tributo, dict):
                                                tipo = tributo.get('tipo', '')
                                                valores = tributo.get('valoresBRL', {})
                                                if isinstance(valores, dict):
                                                    valor_brl = valores.get('devido', 0) or valores.get('calculado', 0) or valores.get('recolhido', 0)
                                                else:
                                                    valor_brl = valores if isinstance(valores, (int, float)) else 0
                                                
                                                if tipo and valor_brl:
                                                    tipo_imposto = tipo.upper()
                                                    if 'IMPOSTO DE IMPORTAÇÃO' in tipo_imposto or tipo_imposto == 'II':
                                                        tipo_imposto = 'II'
                                                    elif 'IMPOSTO SOBRE PRODUTOS INDUSTRIALIZADOS' in tipo_imposto or tipo_imposto == 'IPI':
                                                        tipo_imposto = 'IPI'
                                                    elif 'PIS' in tipo_imposto:
                                                        tipo_imposto = 'PIS'
                                                    elif 'COFINS' in tipo_imposto:
                                                        tipo_imposto = 'COFINS'
                                                    elif 'TAXA' in tipo_imposto or 'UTILIZAÇÃO' in tipo_imposto:
                                                        tipo_imposto = 'TAXA_UTILIZACAO'
                                                    
                                                    impostos_para_gravar.append({
                                                        'tipo_imposto': tipo_imposto,
                                                        'valor_brl': float(valor_brl),
                                                        'codigo_receita': None,
                                                        'descricao_imposto': tipo,
                                                    })
                                        
                                        # Gravar impostos
                                        if impostos_para_gravar:
                                            for imp in impostos_para_gravar:
                                                try:
                                                    proc_esc = processo_ref.replace("'", "''")
                                                    duimp_esc = numero_duimp.replace("'", "''")
                                                    tipo_esc = imp['tipo_imposto'].replace("'", "''")
                                                    desc_esc = (imp.get('descricao_imposto') or '').replace("'", "''")
                                                    valor_brl = imp['valor_brl']
                                                    
                                                    query_merge = f"""
                                                        MERGE dbo.IMPOSTO_IMPORTACAO WITH (HOLDLOCK) AS tgt
                                                        USING (
                                                            SELECT
                                                                '{proc_esc}' AS processo_referencia,
                                                                '{duimp_esc}' AS numero_documento,
                                                                'DUIMP' AS tipo_documento,
                                                                '{tipo_esc}' AS tipo_imposto
                                                        ) AS src
                                                        ON tgt.processo_referencia = src.processo_referencia
                                                           AND tgt.numero_documento = src.numero_documento
                                                           AND tgt.tipo_documento = src.tipo_documento
                                                           AND tgt.tipo_imposto = src.tipo_imposto
                                                        WHEN MATCHED THEN
                                                            UPDATE SET
                                                                valor_brl = {valor_brl},
                                                                descricao_imposto = '{desc_esc}',
                                                                fonte_dados = 'DUIMP_DB',
                                                                atualizado_em = GETDATE()
                                                        WHEN NOT MATCHED THEN
                                                            INSERT (
                                                                processo_referencia,
                                                                numero_documento,
                                                                tipo_documento,
                                                                tipo_imposto,
                                                                valor_brl,
                                                                descricao_imposto,
                                                                fonte_dados,
                                                                pago,
                                                                criado_em,
                                                                atualizado_em
                                                            ) VALUES (
                                                                '{proc_esc}',
                                                                '{duimp_esc}',
                                                                'DUIMP',
                                                                '{tipo_esc}',
                                                                {valor_brl},
                                                                '{desc_esc}',
                                                                'DUIMP_DB',
                                                                1,
                                                                GETDATE(),
                                                                GETDATE()
                                                            );
                                                    """
                                                    adapter.execute_query(query_merge, database="mAIke_assistente", notificar_erro=False)
                                                    logger.info(f'✅ Imposto {tipo_esc} (R$ {valor_brl:,.2f}) gravado para DUIMP {numero_duimp} (do banco SQLite)')
                                                except Exception as e:
                                                    logger.debug(f'Erro ao gravar imposto {imp.get("tipo_imposto")} do banco SQLite: {e}')
                except Exception as e:
                    logger.debug(f'Erro ao verificar/gravar impostos da DUIMP do banco SQLite: {e}')
            
            # Se não encontrou no banco, tentar buscar da API
            if not row:
                logger.info(f'DUIMP {numero_duimp} não encontrada no banco. Buscando da API...')
                
                # Se não há versão informada, buscar versão vigente
                # ⚠️ DESABILITADO: Módulo utils.duimp_helpers não existe
                if not versao_duimp:
                    # try:
                    #     from utils.duimp_helpers import get_versao_vigente
                    #     # Tentar produção primeiro, depois validação
                    #     versao_vigente = get_versao_vigente(numero_duimp, ambiente='producao')
                    #     if not versao_vigente:
                    #         versao_vigente = get_versao_vigente(numero_duimp, ambiente='validacao')
                    #     
                    #     if versao_vigente:
                    #         versao_duimp = str(versao_vigente)
                    #         logger.info(f'Versão vigente encontrada: {versao_duimp}')
                    #     else:
                    #         # Se não encontrou versão vigente, tentar versão 1 (padrão para registradas)
                    #         versao_duimp = '1'
                    #         logger.info(f'Versão vigente não encontrada, tentando versão 1')
                    # except Exception as e:
                    #     logger.warning(f'Erro ao buscar versão vigente: {e}. Tentando versão 1.')
                    # Usar versão 1 como padrão (registradas geralmente começam na versão 1)
                    versao_duimp = '1'
                    logger.info(f'⚠️ Módulo duimp_helpers não disponível. Usando versão 1 como padrão para DUIMP {numero_duimp}.')
                
                # Buscar DUIMP da API
                try:
                    # Tentar produção primeiro, depois validação
                    payload_api = None
                    ambiente_detectado = 'producao'
                    
                    # Tentar produção
                    try:
                        from app import call_portal
                        status, body = call_portal(f'/duimp-api/api/ext/duimp/{numero_duimp}/{versao_duimp}', {}, accept='application/json')
                        if status == 200 and isinstance(body, dict):
                            payload_api = body
                            ambiente_detectado = 'producao'
                            logger.info(f'✅ DUIMP {numero_duimp} v{versao_duimp} encontrada na API (produção)')
                    except Exception as e:
                        logger.debug(f'Erro ao buscar DUIMP da API produção: {e}')
                    
                    # Se não encontrou em produção, tentar validação
                    if not payload_api:
                        try:
                            # Para validação, precisamos usar uma sessão específica
                            import duimp_auth
                            from duimp_request import build_session
                            from urllib.parse import urljoin
                            
                            settings = duimp_auth.load_settings()
                            settings.base_url = 'https://val.portalunico.siscomex.gov.br'
                            tp = duimp_auth.obtain_tokens(settings)
                            set_token, csrf_token = tp.get('setToken'), tp.get('csrfToken')
                            
                            if set_token and csrf_token:
                                session = build_session(settings)
                                url = urljoin(settings.base_url.rstrip('/') + '/', f'/duimp-api/api/ext/duimp/{numero_duimp}/{versao_duimp}')
                                response = session.request('GET', url,
                                                           headers={'Authorization': set_token, 'X-CSRF-Token': csrf_token, 'Accept': 'application/json'},
                                                           timeout=60)
                                session.close()
                                
                                if response.status_code == 200:
                                    payload_api = response.json()
                                    ambiente_detectado = 'validacao'
                                    logger.info(f'✅ DUIMP {numero_duimp} v{versao_duimp} encontrada na API (validação)')
                        except Exception as e:
                            logger.debug(f'Erro ao buscar DUIMP da API validação: {e}')
                    
                    if payload_api:
                        # Salvar no banco SQLite para próxima vez
                        try:
                            from db_manager import salvar_duimp
                            salvar_duimp(numero_duimp, versao_duimp, payload_api, ambiente=ambiente_detectado)
                            logger.info(f'✅ DUIMP {numero_duimp} v{versao_duimp} salva no banco SQLite')
                        except Exception as e:
                            logger.warning(f'Erro ao salvar DUIMP no banco SQLite: {e}')
                        
                        # ✅ NOVO: Atualizar banco SQL Server (mAIke_assistente) via DocumentoHistoricoService
                        try:
                            # Buscar processo_referencia se disponível no contexto ou payload
                            processo_ref = None
                            if context and isinstance(context, dict):
                                processo_ref = context.get('processo_referencia') or context.get('processo_atual')
                            
                            # Tentar extrair do payload também
                            if not processo_ref and isinstance(payload_api, dict):
                                # Verificar se há referência de processo no payload
                                identificacao = payload_api.get('identificacao', {})
                                if isinstance(identificacao, dict):
                                    palavras_chave = identificacao.get('palavrasChave', [])
                                    if isinstance(palavras_chave, list):
                                        for pk in palavras_chave:
                                            if isinstance(pk, dict) and pk.get('codigo') == 2:  # Código 2 = processo
                                                processo_ref = pk.get('valor', '').strip()
                                                break
                            
                            # Extrair dados relevantes do payload para atualizar banco
                            situacao_obj = payload_api.get('situacao', {}) if isinstance(payload_api, dict) else {}
                            resultado_risco = payload_api.get('resultadoAnaliseRisco', {}) if isinstance(payload_api, dict) else {}
                            
                            # Montar payload similar ao ProcessoStatusV2Service
                            payload_doc = {
                                "identificacao": {
                                    "numero": numero_duimp,
                                    "versao": versao_duimp,
                                },
                                "situacao": situacao_obj,
                                "resultadoAnaliseRisco": resultado_risco,
                            }
                            
                            # Extrair situação e canal
                            situacao = None
                            if isinstance(situacao_obj, dict):
                                situacao = situacao_obj.get('situacaoDuimp') or situacao_obj.get('situacao', '')
                            
                            canal = None
                            if isinstance(resultado_risco, dict):
                                canal = resultado_risco.get('canalConsolidado', '')
                            if not canal and isinstance(payload_api, dict):
                                canal = payload_api.get('canalConsolidado', '')
                            
                            # Atualizar banco SQL Server
                            from services.documento_historico_service import DocumentoHistoricoService
                            svc_doc = DocumentoHistoricoService()
                            svc_doc.detectar_e_gravar_mudancas(
                                numero_documento=str(numero_duimp),
                                tipo_documento="DUIMP",
                                dados_novos=payload_doc,
                                fonte_dados="DUIMP_API",
                                api_endpoint=f"/duimp-api/api/ext/duimp/{numero_duimp}/{versao_duimp}",
                                processo_referencia=processo_ref,
                            )
                            logger.info(f'✅ DUIMP {numero_duimp} v{versao_duimp} atualizada no banco SQL Server (mAIke_assistente)')
                            
                            # ✅ NOVO: Extrair e gravar impostos da DUIMP se disponíveis no payload
                            if processo_ref and isinstance(payload_api, dict):
                                try:
                                    # Extrair impostos do payload (tributosCalculados ou pagamentos)
                                    tributos = payload_api.get('tributos', {})
                                    if isinstance(tributos, dict):
                                        tributos_calculados = tributos.get('tributosCalculados', [])
                                    else:
                                        tributos_calculados = []
                                    
                                    if not tributos_calculados:
                                        # Tentar pagamentos
                                        pagamentos = payload_api.get('pagamentos', [])
                                        if isinstance(pagamentos, list):
                                            for pagamento in pagamentos:
                                                if isinstance(pagamento, dict):
                                                    principal = pagamento.get('principal', {})
                                                    if isinstance(principal, dict):
                                                        tributo = principal.get('tributo', {})
                                                        if isinstance(tributo, dict):
                                                            tipo = tributo.get('tipo', '')
                                                            valor = principal.get('valor', 0)
                                                            if tipo and valor:
                                                                tributos_calculados.append({
                                                                    'tipo': tipo,
                                                                    'valoresBRL': {'devido': valor}
                                                                })
                                    
                                    # Gravar impostos se encontrados
                                    if tributos_calculados and isinstance(tributos_calculados, list):
                                        from services.imposto_valor_service import get_imposto_valor_service
                                        svc_iv = get_imposto_valor_service()
                                        
                                        impostos_para_gravar = []
                                        for tributo in tributos_calculados:
                                            if isinstance(tributo, dict):
                                                tipo = tributo.get('tipo', '')
                                                valores = tributo.get('valoresBRL', {})
                                                if isinstance(valores, dict):
                                                    valor_brl = valores.get('devido', 0) or valores.get('calculado', 0) or valores.get('recolhido', 0)
                                                else:
                                                    valor_brl = valores if isinstance(valores, (int, float)) else 0
                                                
                                                if tipo and valor_brl:
                                                    # Mapear tipo de imposto
                                                    tipo_imposto = tipo.upper()
                                                    if 'IMPOSTO DE IMPORTAÇÃO' in tipo_imposto or tipo_imposto == 'II':
                                                        tipo_imposto = 'II'
                                                    elif 'IMPOSTO SOBRE PRODUTOS INDUSTRIALIZADOS' in tipo_imposto or tipo_imposto == 'IPI':
                                                        tipo_imposto = 'IPI'
                                                    elif 'PIS' in tipo_imposto:
                                                        tipo_imposto = 'PIS'
                                                    elif 'COFINS' in tipo_imposto:
                                                        tipo_imposto = 'COFINS'
                                                    elif 'TAXA' in tipo_imposto or 'UTILIZAÇÃO' in tipo_imposto:
                                                        tipo_imposto = 'TAXA_UTILIZACAO'
                                                    
                                                    impostos_para_gravar.append({
                                                        'tipo_imposto': tipo_imposto,
                                                        'valor_brl': float(valor_brl),
                                                        'codigo_receita': None,  # DUIMP não tem código de receita
                                                        'descricao_imposto': tipo,
                                                    })
                                        
                                        # Gravar impostos
                                        if impostos_para_gravar:
                                            for imp in impostos_para_gravar:
                                                try:
                                                    # Usar método similar ao gravar_impostos_di mas para DUIMP
                                                    proc_esc = processo_ref.replace("'", "''")
                                                    duimp_esc = numero_duimp.replace("'", "''")
                                                    tipo_esc = imp['tipo_imposto'].replace("'", "''")
                                                    desc_esc = (imp.get('descricao_imposto') or '').replace("'", "''")
                                                    valor_brl = imp['valor_brl']
                                                    
                                                    query_merge = f"""
                                                        MERGE dbo.IMPOSTO_IMPORTACAO WITH (HOLDLOCK) AS tgt
                                                        USING (
                                                            SELECT
                                                                '{proc_esc}' AS processo_referencia,
                                                                '{duimp_esc}' AS numero_documento,
                                                                'DUIMP' AS tipo_documento,
                                                                '{tipo_esc}' AS tipo_imposto
                                                        ) AS src
                                                        ON tgt.processo_referencia = src.processo_referencia
                                                           AND tgt.numero_documento = src.numero_documento
                                                           AND tgt.tipo_documento = src.tipo_documento
                                                           AND tgt.tipo_imposto = src.tipo_imposto
                                                        WHEN MATCHED THEN
                                                            UPDATE SET
                                                                valor_brl = {valor_brl},
                                                                descricao_imposto = '{desc_esc}',
                                                                fonte_dados = 'DUIMP_API',
                                                                atualizado_em = GETDATE()
                                                        WHEN NOT MATCHED THEN
                                                            INSERT (
                                                                processo_referencia,
                                                                numero_documento,
                                                                tipo_documento,
                                                                tipo_imposto,
                                                                valor_brl,
                                                                descricao_imposto,
                                                                fonte_dados,
                                                                pago,
                                                                criado_em,
                                                                atualizado_em
                                                            ) VALUES (
                                                                '{proc_esc}',
                                                                '{duimp_esc}',
                                                                'DUIMP',
                                                                '{tipo_esc}',
                                                                {valor_brl},
                                                                '{desc_esc}',
                                                                'DUIMP_API',
                                                                1,
                                                                GETDATE(),
                                                                GETDATE()
                                                            );
                                                    """
                                                    from utils.sql_server_adapter import get_sql_adapter
                                                    adapter = get_sql_adapter()
                                                    if adapter:
                                                        adapter.execute_query(query_merge, database="mAIke_assistente", notificar_erro=False)
                                                        logger.info(f'✅ Imposto {tipo_esc} (R$ {valor_brl:,.2f}) gravado para DUIMP {numero_duimp}')
                                                except Exception as e:
                                                    logger.debug(f'Erro ao gravar imposto {imp.get("tipo_imposto")}: {e}')
                                except Exception as e:
                                    logger.debug(f'Erro ao extrair/gravar impostos da DUIMP: {e}')
                        except Exception as e:
                            logger.debug(f'Erro ao atualizar DUIMP no banco SQL Server: {e}')
                        
                        # Criar row simulado para compatibilidade
                        class RowSimulado:
                            def __init__(self, numero, versao, ambiente, payload):
                                self.numero = numero
                                self.versao = versao
                                self.ambiente = ambiente
                                self.payload_completo = json.dumps(payload) if isinstance(payload, dict) else payload
                                self.status = payload.get('situacao', {}).get('situacaoDuimp', '') if isinstance(payload, dict) else ''
                        
                        row = RowSimulado(numero_duimp, versao_duimp, ambiente_detectado, payload_api)
                    else:
                        return {
                            'sucesso': False,
                            'erro': 'DUIMP_NAO_ENCONTRADA',
                            'resposta': f'❌ DUIMP {numero_duimp} não encontrada no banco nem na API.'
                        }
                except Exception as e:
                    logger.error(f'Erro ao buscar DUIMP da API: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_API',
                        'resposta': f'❌ Erro ao buscar DUIMP {numero_duimp} da API: {str(e)}'
                    }
            
            # Extrair informações do payload
            payload_str = row.payload_completo if hasattr(row, 'payload_completo') else row['payload_completo']
            payload = json.loads(payload_str) if payload_str and isinstance(payload_str, str) else (payload_str if payload_str else {})
            
            # Extrair informações relevantes
            info_duimp = self._extrair_info_duimp(payload, row)
            
            # Formatar resposta
            resposta = f"📋 **DUIMP {info_duimp['numero']}** v{info_duimp['versao']}\n\n"
            
            # Situação
            resposta += f"**Situação:** {info_duimp['situacao']}\n"
            
            # Canal
            if info_duimp['canal']:
                resposta += f"**Canal:** {info_duimp['canal']}\n"
            
            # Ambiente
            resposta += f"**Ambiente:** {info_duimp['ambiente'].title()}\n"
            
            # Data e hora do desembaraço
            if info_duimp['data_desembaraco']:
                resposta += f"\n**🕐 Desembaraço:**\n"
                resposta += f"   - Data: {info_duimp['data_desembaraco']}\n"
                if info_duimp['hora_desembaraco']:
                    resposta += f"   - Hora: {info_duimp['hora_desembaraco']}\n"
            
            # Impostos
            if info_duimp['impostos']:
                resposta += f"\n**💰 Impostos:**\n"
                for imposto in info_duimp['impostos']:
                    tipo = imposto.get('tipo', 'N/A')
                    valor = imposto.get('valor', 0)
                    resposta += f"   - {tipo}: R$ {valor:,.2f}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': info_duimp
            }
        except Exception as e:
            logger.error(f'Erro ao obter dados da DUIMP {numero_duimp}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao obter dados da DUIMP: {str(e)}'
            }
    
    def _extrair_info_duimp(self, payload: Dict[str, Any], row: Any) -> Dict[str, Any]:
        """
        Extrai informações relevantes do payload da DUIMP.
        
        Returns:
            Dict com: numero, versao, situacao, canal, ambiente, data_desembaraco, hora_desembaraco, impostos
        """
        info = {
            'numero': row['numero'],
            'versao': row['versao'],
            'ambiente': row['ambiente'],
            'situacao': row['status'] or 'N/A',
            'canal': None,
            'data_desembaraco': None,
            'hora_desembaraco': None,
            'impostos': []
        }
        
        try:
            # Extrair situação do payload - múltiplos caminhos possíveis
            situacao_obj = payload.get('situacao', {})
            if isinstance(situacao_obj, dict):
                # Prioridade 1: situacaoDuimp (mais específico)
                situacao_duimp = situacao_obj.get('situacaoDuimp', '')
                if situacao_duimp:
                    info['situacao'] = situacao_duimp
                else:
                    # Prioridade 2: situacao (geral)
                    situacao_geral = situacao_obj.get('situacao', '')
                    if situacao_geral:
                        info['situacao'] = situacao_geral
            
            # Se ainda não encontrou situação, tentar resultadoAnaliseRisco
            if not info['situacao'] or info['situacao'] == 'N/A':
                resultado_risco = payload.get('resultadoAnaliseRisco', {})
                if isinstance(resultado_risco, dict):
                    resultado_rfb = resultado_risco.get('resultadoRFB', [])
                    if isinstance(resultado_rfb, list) and len(resultado_rfb) > 0:
                        resultado = resultado_rfb[0].get('resultado', '')
                        if resultado:
                            info['situacao'] = resultado
            
            # Extrair canal - múltiplos caminhos possíveis
            # Prioridade 1: resultadoAnaliseRisco.canalConsolidado (onde geralmente está)
            resultado_risco = payload.get('resultadoAnaliseRisco', {})
            if isinstance(resultado_risco, dict):
                canal_consolidado = resultado_risco.get('canalConsolidado', '')
                if canal_consolidado and canal_consolidado.strip():
                    info['canal'] = canal_consolidado.strip()
            
            # Prioridade 2: canalConsolidado direto no payload
            if not info['canal']:
                canal_consolidado = payload.get('canalConsolidado', '')
                if canal_consolidado and canal_consolidado.strip():
                    info['canal'] = canal_consolidado.strip()
            
            # Prioridade 3: canal.codigo ou canal.nome
            if not info['canal']:
                canal_obj = payload.get('canal', {})
                if isinstance(canal_obj, dict):
                    canal_codigo = canal_obj.get('codigo', '')
                    canal_nome = canal_obj.get('nome', '')
                    if canal_codigo and canal_codigo.strip():
                        info['canal'] = canal_codigo.strip()
                    elif canal_nome and canal_nome.strip():
                        info['canal'] = canal_nome.strip()
            
            # Extrair data/hora do desembaraço
            # Tentar vários caminhos possíveis no payload
            desembaraco_paths = [
                ['situacao', 'dataDesembaraco'],
                ['situacao', 'dataHoraDesembaraco'],
                ['desembaraco', 'data'],
                ['desembaraco', 'dataHora'],
                ['dadosDesembaraco', 'data'],
                ['dadosDesembaraco', 'dataHora'],
            ]
            
            for path in desembaraco_paths:
                valor = payload
                try:
                    for key in path:
                        if isinstance(valor, dict):
                            valor = valor.get(key)
                        else:
                            valor = None
                            break
                    
                    if valor:
                        # Tentar parsear data/hora
                        try:
                            from datetime import datetime
                            if isinstance(valor, str):
                                # Tentar diferentes formatos
                                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d']:
                                    try:
                                        dt = datetime.strptime(valor[:19], fmt)
                                        info['data_desembaraco'] = dt.strftime('%d/%m/%Y')
                                        if len(valor) > 10:
                                            info['hora_desembaraco'] = dt.strftime('%H:%M:%S')
                                        break
                                    except:
                                        continue
                        except:
                            pass
                        break
                except:
                    continue
            
            # Extrair impostos (tributosCalculados ou pagamentos)
            # Tentar tributosCalculados primeiro
            tributos = payload.get('tributosCalculados', [])
            if not tributos:
                # Tentar pagamentos
                pagamentos = payload.get('pagamentos', [])
                for pagamento in pagamentos:
                    principal = pagamento.get('principal', {})
                    tributo = principal.get('tributo', {})
                    tipo = tributo.get('tipo', '')
                    valor = principal.get('valor', 0)
                    if tipo and valor:
                        tributos.append({
                            'tipo': tipo,
                            'valoresBRL': {
                                'devido': valor
                            }
                        })
            
            # Processar impostos
            for tributo in tributos:
                if isinstance(tributo, dict):
                    tipo = tributo.get('tipo', '')
                    valores = tributo.get('valoresBRL', {})
                    if isinstance(valores, dict):
                        valor_devido = valores.get('devido', 0) or valores.get('calculado', 0)
                    else:
                        valor_devido = valores if isinstance(valores, (int, float)) else 0
                    
                    if tipo and valor_devido:
                        info['impostos'].append({
                            'tipo': tipo,
                            'valor': float(valor_devido)
                        })
            
        except Exception as e:
            logger.warning(f'Erro ao extrair informações do payload: {e}')
        
        return info
    
    def formatar_info_duimp_para_resposta(self, duimp_numero: str, duimp_versao: str = None, payload: Dict[str, Any] = None) -> str:
        """
        Formata informações relevantes de uma DUIMP para exibição em consultas.
        
        Args:
            duimp_numero: Número da DUIMP
            duimp_versao: Versão da DUIMP (opcional)
            payload: Payload da DUIMP (opcional, será buscado se não fornecido)
        
        Returns:
            String formatada com informações relevantes
        """
        try:
            # Se payload não fornecido, buscar do banco
            if not payload:
                import sqlite3
                import json
                from db_manager import get_db_connection
                
                conn = get_db_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if duimp_versao:
                    cursor.execute('''
                        SELECT payload_completo, status, ambiente
                        FROM duimps
                        WHERE numero = ? AND versao = ?
                        ORDER BY CASE WHEN ambiente = 'producao' THEN 0 ELSE 1 END
                        LIMIT 1
                    ''', (duimp_numero, duimp_versao))
                else:
                    cursor.execute('''
                        SELECT payload_completo, status, ambiente
                        FROM duimps
                        WHERE numero = ?
                        ORDER BY CASE WHEN ambiente = 'producao' THEN 0 ELSE 1 END,
                                 CAST(versao AS INTEGER) DESC
                        LIMIT 1
                    ''', (duimp_numero,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    payload_str = row['payload_completo']
                    payload = json.loads(payload_str) if payload_str and isinstance(payload_str, str) else (payload_str if payload_str else {})
                else:
                    return f"📋 **DUIMP {duimp_numero}** v{duimp_versao or 'N/A'}\n   - ⚠️ DUIMP não encontrada no banco\n"
            
            # Extrair informações básicas primeiro (situação e canal) - sempre mostrar
            situacao = 'N/A'
            canal = None
            
            try:
                # Tentar extrair situação do payload - múltiplos caminhos
                if isinstance(payload, dict):
                    # Prioridade 1: situacao.situacaoDuimp
                    situacao_obj = payload.get('situacao', {})
                    if isinstance(situacao_obj, dict):
                        situacao = situacao_obj.get('situacaoDuimp', '')
                        if not situacao:
                            # Prioridade 2: situacao.situacao
                            situacao = situacao_obj.get('situacao', '')
                    
                    # Se ainda não encontrou, tentar resultadoAnaliseRisco
                    if not situacao:
                        resultado_risco = payload.get('resultadoAnaliseRisco', {})
                        if isinstance(resultado_risco, dict):
                            resultado_rfb = resultado_risco.get('resultadoRFB', [])
                            if isinstance(resultado_rfb, list) and len(resultado_rfb) > 0:
                                resultado = resultado_rfb[0].get('resultado', '')
                                if resultado:
                                    situacao = resultado
                    
                    # Se ainda não encontrou, tentar status direto
                    if not situacao:
                        situacao = payload.get('status', '')
                    
                    # Tentar extrair canal - múltiplos caminhos
                    # Prioridade 1: resultadoAnaliseRisco.canalConsolidado
                    resultado_risco = payload.get('resultadoAnaliseRisco', {})
                    if isinstance(resultado_risco, dict):
                        canal = resultado_risco.get('canalConsolidado', '')
                        if canal and canal.strip():
                            canal = canal.strip()
                    
                    # Prioridade 2: canalConsolidado direto no payload
                    if not canal or not canal.strip():
                        canal = payload.get('canalConsolidado', '')
                        if canal and canal.strip():
                            canal = canal.strip()
                    
                    # Prioridade 3: canal.codigo ou canal.nome
                    if not canal or not canal.strip():
                        canal_obj = payload.get('canal', {})
                        if isinstance(canal_obj, dict):
                            canal_codigo = canal_obj.get('codigo', '')
                            canal_nome = canal_obj.get('nome', '')
                            if canal_codigo and canal_codigo.strip():
                                canal = canal_codigo.strip()
                            elif canal_nome and canal_nome.strip():
                                canal = canal_nome.strip()
            except Exception as e:
                logger.debug(f'Erro ao extrair situação/canal básico: {e}')
            
            # Se não encontrou no payload, tentar buscar do banco
            if (situacao == 'N/A' or not situacao) or not canal:
                try:
                    import sqlite3
                    from db_manager import get_db_connection
                    import json
                    conn_status = get_db_connection()
                    conn_status.row_factory = sqlite3.Row
                    cursor_status = conn_status.cursor()
                    cursor_status.execute('''
                        SELECT status, payload_completo
                        FROM duimps
                        WHERE numero = ? AND versao = ?
                        ORDER BY CASE WHEN ambiente = 'producao' THEN 0 ELSE 1 END
                        LIMIT 1
                    ''', (duimp_numero, duimp_versao or '1'))
                    row_status = cursor_status.fetchone()
                    if row_status:
                        if not situacao or situacao == 'N/A':
                            if row_status['status']:
                                situacao = row_status['status']
                        
                        # Se não tem canal ou situação, tentar extrair do payload do banco
                        if (not canal or not situacao or situacao == 'N/A') and row_status['payload_completo']:
                            try:
                                payload_banco = json.loads(row_status['payload_completo']) if isinstance(row_status['payload_completo'], str) else row_status['payload_completo']
                                if isinstance(payload_banco, dict):
                                    # Extrair canal - múltiplos caminhos
                                    if not canal or not canal.strip():
                                        canal_temp = payload_banco.get('canalConsolidado', '')
                                        if canal_temp and canal_temp.strip():
                                            canal = canal_temp.strip()
                                        else:
                                            canal_obj = payload_banco.get('canal', {})
                                            if isinstance(canal_obj, dict):
                                                canal_codigo = canal_obj.get('codigo', '')
                                                canal_nome = canal_obj.get('nome', '')
                                                if canal_codigo and canal_codigo.strip():
                                                    canal = canal_codigo.strip()
                                                elif canal_nome and canal_nome.strip():
                                                    canal = canal_nome.strip()
                                    
                                    # Extrair situação - múltiplos caminhos
                                    if not situacao or situacao == 'N/A':
                                        situacao_obj = payload_banco.get('situacao', {})
                                        if isinstance(situacao_obj, dict):
                                            situacao = situacao_obj.get('situacaoDuimp', '') or situacao_obj.get('situacao', '') or situacao
                                        
                                        # Se ainda não encontrou, tentar resultadoAnaliseRisco
                                        if not situacao or situacao == 'N/A':
                                            resultado_risco = payload_banco.get('resultadoAnaliseRisco', {})
                                            if isinstance(resultado_risco, dict):
                                                resultado_rfb = resultado_risco.get('resultadoRFB', [])
                                                if isinstance(resultado_rfb, list) and len(resultado_rfb) > 0:
                                                    resultado = resultado_rfb[0].get('resultado', '')
                                                    if resultado:
                                                        situacao = resultado
                            except Exception as e:
                                logger.debug(f'Erro ao extrair do payload do banco: {e}')
                    conn_status.close()
                except Exception as e:
                    logger.debug(f'Erro ao buscar situação/canal do banco: {e}')
            
            # Tentar extrair informações completas (pode falhar, mas não deve quebrar a resposta)
            info = None
            try:
                info = self._extrair_info_duimp(payload, type('Row', (), {
                    'numero': duimp_numero,
                    'versao': duimp_versao or '0',
                    'ambiente': payload.get('ambiente', 'producao') if isinstance(payload, dict) else 'producao',
                    'status': situacao
                })())
                
                # Atualizar situação se encontrou melhor no payload
                if info.get('situacao') and info['situacao'] != 'N/A' and info['situacao'] != situacao:
                    situacao = info['situacao']
                
                # Atualizar canal se encontrou melhor no payload (sempre priorizar o que foi encontrado)
                if info.get('canal'):
                    canal = info['canal']
            except Exception as e:
                logger.debug(f'Erro ao extrair informações adicionais da DUIMP {duimp_numero}: {e}')
                # Continuar mesmo com erro, já temos situação e canal básicos
            
            # Formatar resposta - sempre mostrar situação e canal (se disponível)
            resposta = f"📋 **DUIMP {duimp_numero}** v{duimp_versao or '1'}\n"
            resposta += f"   - **Situação:** {situacao if situacao and situacao != 'N/A' else 'N/A'}\n"
            
            # Sempre tentar mostrar canal se encontrado (priorizar o melhor encontrado)
            canal_final = None
            if canal and canal.strip():
                canal_final = canal.strip()
            elif info and info.get('canal') and info['canal'].strip():
                canal_final = info['canal'].strip()
            
            if canal_final:
                resposta += f"   - **Canal:** {canal_final}\n"
            else:
                # Log para debug - canal não encontrado
                logger.debug(f'⚠️ Canal não encontrado para DUIMP {duimp_numero} v{duimp_versao}. Payload keys: {list(payload.keys()) if isinstance(payload, dict) else "N/A"}')
            
            # Data e hora do desembaraço (se disponível)
            if info and info.get('data_desembaraco'):
                resposta += f"   - **🕐 Desembaraço:** {info['data_desembaraco']}"
                if info.get('hora_desembaraco'):
                    resposta += f" às {info['hora_desembaraco']}"
                resposta += "\n"
            
            # Impostos (informação relevante)
            if info and info.get('impostos'):
                resposta += f"   - **💰 Impostos:**\n"
                for imposto in info['impostos']:
                    tipo = imposto.get('tipo', 'N/A')
                    valor = imposto.get('valor', 0)
                    resposta += f"      • {tipo}: R$ {valor:,.2f}\n"
            
            return resposta
        except Exception as e:
            logger.error(f'Erro crítico ao formatar informações da DUIMP {duimp_numero}: {e}', exc_info=True)
            # Mesmo em erro crítico, tentar mostrar pelo menos número e versão
            return f"📋 **DUIMP {duimp_numero}** v{duimp_versao or 'N/A'}\n   - ⚠️ Erro ao obter informações detalhadas: {str(e)}\n"
    
    def _vincular_processo_duimp(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Vincula uma DUIMP (ou DI) a um processo.
        
        ✅ NOVO: Reconhece automaticamente DUIMP vs DI pelo padrão do número.
        Para DUIMP, busca versão vigente automaticamente se não informada.
        """
        import re
        
        numero_duimp_raw = arguments.get('numero_duimp', '').strip()
        versao_duimp_param = arguments.get('versao_duimp', '').strip() if arguments.get('versao_duimp') else None
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        if not numero_duimp_raw:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Número da DUIMP/DI é obrigatório.'
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
        
        try:
            # ✅ NOVO: Reconhecer automaticamente DUIMP vs DI pelo padrão do número
            documento_info = self._extrair_numero_duimp_ou_di(numero_duimp_raw)
            
            if not documento_info:
                # Tentar padrão mais flexível
                padrao_flexivel_duimp = r'\b(25BR\d{9,11}(?:-(\d+))?)\b'
                match_flex = re.search(padrao_flexivel_duimp, numero_duimp_raw, re.IGNORECASE)
                if match_flex:
                    numero_completo = match_flex.group(1).upper()
                    versao_detectada = match_flex.group(2) if match_flex.group(2) else None
                    if '-' in numero_completo:
                        numero_base = numero_completo.split('-')[0]
                    else:
                        numero_base = numero_completo
                    documento_info = {
                        'tipo': 'DUIMP',
                        'numero': numero_base,
                        'versao': versao_detectada,
                        'numero_completo': numero_completo
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': 'FORMATO_INVALIDO',
                        'resposta': f"⚠️ **Formato inválido:** '{numero_duimp_raw}' não é um número de DUIMP válido (formato: 25BR0000194844 ou 25BR0000194844-1) nem DI válido (formato: 25/2535383-7)."
                    }
            
            tipo_documento = documento_info['tipo']
            numero_documento = documento_info['numero']
            versao_detectada = documento_info.get('versao')
            
            # ✅ NOVO: Para DUIMP, se versão não foi informada, buscar automaticamente
            versao_final = None
            if tipo_documento == 'DUIMP':
                # Prioridade: versão do parâmetro > versão detectada > buscar automaticamente
                versao_final = versao_duimp_param or versao_detectada
                
                if not versao_final:
                    # Buscar versão vigente automaticamente
                    # ⚠️ DESABILITADO: Módulo utils.duimp_helpers não existe
                    # try:
                    #     from utils.duimp_helpers import get_versao_vigente
                    #     
                    #     # Tentar ambos os ambientes (validação primeiro, depois produção)
                    #     versao_vigente = get_versao_vigente(numero_documento, ambiente='validacao')
                    #     if not versao_vigente or versao_vigente == 0:
                    #         versao_vigente = get_versao_vigente(numero_documento, ambiente='producao')
                    #     
                    #     if versao_vigente and versao_vigente > 0:
                    #         versao_final = str(versao_vigente)
                    #         logger.info(f'✅ Versão vigente detectada automaticamente para DUIMP {numero_documento}: v{versao_final}')
                    #     else:
                    #         # Se não encontrou versão vigente, usar "0" (rascunho)
                    #         versao_final = '0'
                    #         logger.info(f'⚠️ Versão vigente não encontrada para DUIMP {numero_documento}. Usando versão 0 (rascunho).')
                    # except Exception as e:
                    #     logger.warning(f'Erro ao buscar versão vigente para DUIMP {numero_documento}: {e}. Usando versão 0.')
                    # Usar versão 0 como padrão (rascunho)
                    versao_final = '0'
                    logger.info(f'⚠️ Módulo duimp_helpers não disponível. Usando versão 0 (rascunho) para DUIMP {numero_documento}.')
            elif tipo_documento == 'DI':
                # DI não tem versão
                versao_final = None
            
            # Vincular documento ao processo
            from db_manager import vincular_documento_processo
            
            if tipo_documento == 'DUIMP':
                # Para DUIMP, verificar se existe antes de vincular
                from db_manager import buscar_duimp
                duimp = buscar_duimp(numero_documento, versao_final or '0')
                
                if not duimp:
                    # Se não encontrou, ainda assim vincular (DUIMP pode não estar no banco local ainda)
                    logger.info(f'⚠️ DUIMP {numero_documento} v{versao_final} não encontrada no banco local. Vinculando mesmo assim (pode ser consultada automaticamente).')
                
                # Vincular
                vincular_documento_processo(processo_completo, 'DUIMP', f"{numero_documento}v{versao_final}")
                
                # Atualizar também o banco da DUIMP
                from db_manager import atualizar_processo_duimp_cache
                sucesso = atualizar_processo_duimp_cache(numero_documento, versao_final, processo_completo)
                
                if sucesso:
                    # ✅ NOVO: Consultar DUIMP automaticamente após vinculação para atualizar Kanban
                    # ⚠️ DESABILITADO: Módulo utils.monitoramento_automatico não existe
                    # try:
                    #     from utils.monitoramento_automatico import _consultar_duimp_automatico
                    #     resultado_temp = {'duimps_consultadas': 0, 'erros': []}
                    #     logger.info(f'📋 Consultando DUIMP {numero_documento} v{versao_final} automaticamente após vinculação...')
                    #     _consultar_duimp_automatico(numero_documento, processo_completo, resultado_temp)
                    #     logger.info(f'✅ DUIMP {numero_documento} v{versao_final} consultada automaticamente. Situação atualizada.')
                    # except Exception as e:
                    #     logger.warning(f'Erro ao consultar DUIMP automaticamente após vinculação: {e}')
                    
                    resposta = f"✅ **DUIMP vinculada com sucesso!**\n\n"
                    resposta += f"**DUIMP:** {numero_documento} v{versao_final}\n"
                    resposta += f"**Processo:** {processo_completo}\n\n"
                    resposta += f"🎯 **DUIMP vinculada ao processo!** O Kanban será atualizado automaticamente."
                    
                    return {
                        'sucesso': True,
                        'resposta': resposta,
                        'processo': processo_completo,
                        'duimp': numero_documento,
                        'versao': versao_final,
                        'tipo': 'DUIMP'
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_VINCULACAO',
                        'resposta': f"❌ **Erro ao vincular processo {processo_completo} à DUIMP {numero_documento} v{versao_final}.**"
                    }
            elif tipo_documento == 'DI':
                # Para DI, vincular diretamente
                vincular_documento_processo(processo_completo, 'DI', numero_documento)
                
                resposta = f"✅ **DI vinculada com sucesso!**\n\n"
                resposta += f"**DI:** {numero_documento}\n"
                resposta += f"**Processo:** {processo_completo}\n\n"
                resposta += f"🎯 **DI vinculada ao processo!**"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'processo': processo_completo,
                    'di': numero_documento,
                    'tipo': 'DI'
                }
                
        except Exception as e:
            logger.error(f'Erro ao vincular processo à DUIMP/DI: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro interno ao vincular processo: {str(e)}'
            }
    
    def _verificar_duimp_processo(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Verifica se há DUIMP registrada para o processo.
        
        ✅ CRÍTICO: 
        - SEMPRE prioriza DUIMPs de PRODUÇÃO sobre validação
        - Retorna DUIMP de produção se existir, senão retorna None (não retorna validação)
        - DUIMPs de validação são apenas para testes e não devem ser consideradas como produção
        """
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # ✅ CRÍTICO: Buscar PRIMEIRO DUIMP de PRODUÇÃO (prioridade máxima)
            cursor.execute('''
                SELECT numero, versao, status, ambiente, criado_em, payload_completo
                FROM duimps
                WHERE processo_referencia = ? AND ambiente = 'producao'
                ORDER BY CAST(versao AS INTEGER) DESC, criado_em DESC
                LIMIT 1
            ''', (processo_referencia,))
            
            row_producao = cursor.fetchone()
            
            if row_producao:
                # ✅ Encontrou DUIMP de PRODUÇÃO - processar e retornar
                duimp_numero = row_producao['numero']
                duimp_versao = row_producao['versao']
                versao_int = int(duimp_versao) if duimp_versao.isdigit() else 0
                
                # ✅ VALIDAÇÃO: Verificar se o payload não é uma mensagem de erro
                payload_completo_str = row_producao['payload_completo']
                if payload_completo_str:
                    try:
                        import json
                        payload_completo = json.loads(payload_completo_str) if isinstance(payload_completo_str, str) else payload_completo_str
                        if isinstance(payload_completo, dict) and payload_completo.get('code') == 'PUCX-ER0014':
                            conn.close()
                            return {'registrada': False, 'existe': False}  # Ignorar payloads de erro
                    except:
                        pass
                
                # Extrair situação do payload se disponível
                situacao_duimp = None
                try:
                    import json
                    payload_str = row_producao['payload_completo']
                    if payload_str:
                        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                        if isinstance(payload, dict):
                            situacao_obj = payload.get('situacao', {})
                            if isinstance(situacao_obj, dict):
                                situacao_duimp = situacao_obj.get('situacaoDuimp', '')
                except:
                    pass
                
                conn.close()
                
                resultado = {
                    'registrada': versao_int >= 1,  # ✅ Registrada se versão >= 1
                    'numero': duimp_numero,
                    'versao': duimp_versao,
                    'status': row_producao['status'],
                    'situacao': situacao_duimp or row_producao['status'],
                    'ambiente': 'producao',  # ✅ SEMPRE produção
                    'criado_em': row_producao['criado_em'],
                    'existe': True,  # ✅ Flag indicando que existe
                    'eh_producao': True  # ✅ Flag crítica: é produção
                }
                
                return resultado
            
            # ✅ NÃO encontrou DUIMP de PRODUÇÃO - retornar None
            # NÃO retornar DUIMP de validação aqui - ela é apenas para testes
            conn.close()
            return {'registrada': False, 'existe': False, 'eh_producao': False}
        except Exception as e:
            logger.warning(f'Erro ao verificar DUIMP do processo {processo_referencia}: {e}')
            return {'registrada': False, 'erro': str(e)}
    
    def _extrair_numero_duimp_ou_di(self, mensagem: str) -> Optional[Dict[str, str]]:
        """
        Extrai número de DUIMP ou DI da mensagem com reconhecimento automático.
        
        Retorna:
            Dict com:
            - 'tipo': 'DUIMP' ou 'DI'
            - 'numero': número sem versão (ex: '25BR0000194844')
            - 'versao': versão se informada (ex: '1'), ou None
            - 'numero_completo': número completo como informado (ex: '25BR0000194844-1')
        """
        import re
        
        # Padrão DUIMP: 25BR[digitos] ou 25BR[digitos]-[versao]
        # Ex: 25BR0000194844, 25BR0000194844-1
        padrao_duimp = r'\b(25BR\d{9,11}(?:-(\d+))?)\b'
        match_duimp = re.search(padrao_duimp, mensagem, re.IGNORECASE)
        if match_duimp:
            numero_completo = match_duimp.group(1).upper()
            versao = match_duimp.group(2) if match_duimp.group(2) else None
            # Extrair número base (sem versão)
            if '-' in numero_completo:
                numero_base = numero_completo.split('-')[0]
            else:
                numero_base = numero_completo
            return {
                'tipo': 'DUIMP',
                'numero': numero_base,
                'versao': versao,
                'numero_completo': numero_completo
            }
        
        # Padrão DI: [2 digitos]/[digitos]-[digito]
        # Ex: 25/2535383-7
        padrao_di = r'\b(\d{2}/\d+-\d)\b'
        match_di = re.search(padrao_di, mensagem)
        if match_di:
            numero_completo = match_di.group(1)
            return {
                'tipo': 'DI',
                'numero': numero_completo,
                'versao': None,  # DI não tem versão
                'numero_completo': numero_completo
            }
        
        return None
    
    def _obter_extrato_pdf_duimp(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Obtém extrato PDF da DUIMP de um processo.
        
        Versão SIMPLES: apenas consulta e retorna dados.
        Geração de PDF será implementada depois.
        
        Args:
            arguments: {
                'processo_referencia': str (opcional) - Número do processo
                'numero_duimp': str (opcional) - Número da DUIMP diretamente
            }
            context: Contexto adicional
        
        Returns:
            Dict com resultado da consulta
        """
        try:
            from services.duimp_pdf_service import DuimpPdfService
        except ImportError:
            # Fallback: tentar import relativo
            import sys
            from pathlib import Path
            services_dir = Path(__file__).parent.parent
            if str(services_dir) not in sys.path:
                sys.path.insert(0, str(services_dir))
            from duimp_pdf_service import DuimpPdfService
        
        processo_ref = arguments.get('processo_referencia', '').strip()
        numero_duimp = arguments.get('numero_duimp', '').strip()
        
        if not processo_ref and not numero_duimp:
            return {
                'sucesso': False,
                'erro': 'processo_referencia ou numero_duimp é obrigatório',
                'resposta': '❌ Referência de processo ou número da DUIMP é obrigatório.'
            }
        
        # ✅ NOVO: Se o usuário pediu "extrato do [processo]" sem especificar DUIMP/DI/CE,
        # tentar CE primeiro (mais comum), depois DI, depois DUIMP
        if processo_ref and not numero_duimp:
            # Verificar se tem CE primeiro (mais comum)
            try:
                from db_manager import obter_dados_documentos_processo
                dados_docs = obter_dados_documentos_processo(processo_ref)
                ces = dados_docs.get('ces', []) if dados_docs else []
                
                if ces and len(ces) > 0:
                    numero_ce = ces[0].get('numero', '')
                    if numero_ce:
                        logger.info(f"✅ [EXTRATO] Processo {processo_ref} tem CE {numero_ce}. Redirecionando para obter_extrato_ce...")
                        # Redirecionar para obter_extrato_ce
                        from services.ce_agent import CeAgent
                        ce_agent = CeAgent()
                        return ce_agent._obter_extrato_ce({
                            'processo_referencia': processo_ref,
                            'numero_ce': numero_ce
                        }, context)
                
                # Se não tem CE, tentar DI
                dis = dados_docs.get('dis', []) if dados_docs else []
                if dis and len(dis) > 0:
                    numero_di = dis[0].get('numero', '')
                    if numero_di:
                        logger.info(f"✅ [EXTRATO] Processo {processo_ref} tem DI {numero_di}. Redirecionando para obter_extrato_pdf_di...")
                        # Redirecionar para obter_extrato_pdf_di
                        from services.di_agent import DiAgent
                        di_agent = DiAgent()
                        return di_agent._obter_extrato_pdf_di({
                            'processo_referencia': processo_ref,
                            'numero_di': numero_di
                        }, context)
            except Exception as e:
                logger.debug(f'Erro ao verificar documentos para extrato: {e}')
        
        # Usar serviço modular
        try:
            pdf_service = DuimpPdfService()
            resultado = pdf_service.obter_dados_completos_duimp(
                processo_referencia=processo_ref if processo_ref else None,
                numero_duimp=numero_duimp if numero_duimp else None
            )
        except Exception as e:
            logger.error(f'Erro ao executar obter_dados_completos_duimp para {processo_ref}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao processar extrato da DUIMP para {processo_ref}: {str(e)}'
            }
        
        # Formatar resposta para o usuário
        resposta_pdf = ""  # Inicializar variável
        if resultado.get('sucesso'):
            numero = resultado['numero']
            versao = resultado['versao']
            total_itens = resultado.get('total_itens', 0)
            dados_capa = resultado.get('dados_capa', {})
            ambiente = resultado.get('ambiente', 'N/A')
            aviso = resultado.get('aviso', None)
            
            # Tentar gerar PDF automaticamente (só se temos dados do Portal Único)
            if dados_capa and not aviso:
                try:
                    pdf_resultado = pdf_service.gerar_pdf_duimp(
                        processo_referencia=processo_ref if processo_ref else None,
                        numero_duimp=numero_duimp if numero_duimp else None
                    )
                    
                    if pdf_resultado.get('sucesso'):
                        # PDF gerado com sucesso - incluir link na resposta (formato markdown para ser clicável)
                        caminho_pdf = pdf_resultado.get('caminho_arquivo', '')
                        nome_arquivo = pdf_resultado.get('nome_arquivo', '')
                        # Usar formato markdown de link: [texto](url)
                        # O caminho já inclui "downloads/", então usar diretamente
                        url_download = f"/api/download/{caminho_pdf}"
                        resposta_pdf = f"\n\n📄 **PDF gerado com sucesso!**\n🔗 **Download:** [Clique aqui para baixar o PDF]({url_download})\n💾 **Arquivo:** `{nome_arquivo}`"
                    else:
                        # PDF não foi gerado, mas não é crítico
                        resposta_pdf = f"\n\n⚠️ **Nota:** Não foi possível gerar o PDF: {pdf_resultado.get('erro', 'Erro desconhecido')}"
                except Exception as e:
                    logger.warning(f'Erro ao gerar PDF (não crítico): {e}')
                    resposta_pdf = f"\n\n⚠️ **Nota:** Não foi possível gerar o PDF automaticamente."
            
            # Se tem aviso, significa que consulta ao Portal Único falhou mas DUIMP foi encontrada
            if aviso:
                resposta_formatada = f"""✅ **DUIMP encontrada no banco de dados!**

📋 **DUIMP:** {numero}
📌 **Versão:** {versao}
🌍 **Ambiente:** {ambiente.upper()}

⚠️ **Nota:** Consulta completa ao Portal Único não está disponível no momento.
Por favor, use o comando "obter dados da DUIMP {numero}" para consultar detalhes completos.

{resposta_pdf if resposta_pdf else '📄 **Geração de PDF:** Não disponível (dados do Portal Único necessários).'}"""
            else:
                # Consulta ao Portal Único funcionou - extrair mais informações
                identificacao = dados_capa.get('identificacao', {})
                situacao = dados_capa.get('situacao', {})
                
                # Buscar canal - pode estar em diferentes lugares
                canal = None
                if isinstance(situacao, dict):
                    canal = situacao.get('canal') or situacao.get('codigoCanal')
                if not canal and isinstance(identificacao, dict):
                    canal = identificacao.get('canal') or identificacao.get('codigoCanal')
                
                # Montar resposta mais informativa
                resposta_formatada = f"""✅ **Extrato da DUIMP consultado com sucesso!**

📋 **DUIMP:** {numero}
📌 **Versão:** {versao}
🌍 **Ambiente:** {ambiente.upper()}
📦 **Itens:** {total_itens} item(ns)"""
                
                if canal:
                    resposta_formatada += f"\n🚪 **Canal:** {canal}"
                
                # Adicionar informações de situação se disponível
                if isinstance(situacao, dict):
                    situacao_atual = situacao.get('situacaoDuimp') or situacao.get('situacao') or situacao.get('situacaoDUIMP')
                    if situacao_atual:
                        resposta_formatada += f"\n📊 **Situação:** {situacao_atual}"
                    
                    # Data de desembaraço se disponível
                    data_desembaraco = situacao.get('dataDesembaraco') or situacao.get('dataDesembaracoAduaneiro') or situacao.get('dataHoraDesembaraco')
                    if data_desembaraco:
                        resposta_formatada += f"\n📅 **Data de Desembaraço:** {data_desembaraco}"
                
                # Informações de carga se disponível
                carga = dados_capa.get('carga', {})
                if isinstance(carga, dict):
                    # Buscar valor FOB em diferentes formatos
                    valor_fob = None
                    frete = carga.get('frete', {})
                    if isinstance(frete, dict):
                        valor_fob = frete.get('valorFob', frete.get('valorFOB'))
                    if not valor_fob:
                        valor_fob = carga.get('valorFob', carga.get('valorFOB'))
                    if valor_fob:
                        try:
                            valor_formatado = f"USD {float(valor_fob):,.2f}"
                            resposta_formatada += f"\n💰 **Valor FOB:** {valor_formatado}"
                        except (ValueError, TypeError):
                            pass
                
                # Informações de tributos - DETALHADO com somatório
                tributos = dados_capa.get('tributos', {})
                if isinstance(tributos, dict):
                    tributos_calculados = tributos.get('tributosCalculados', [])
                    if isinstance(tributos_calculados, list) and len(tributos_calculados) > 0:
                        resposta_formatada += "\n\n💵 **Tributos Detalhados:**"
                        
                        valor_total_devido = 0
                        valor_total_recolhido = 0
                        detalhes_tributos = []
                        
                        # Mapear códigos de tributos para nomes legíveis
                        nomes_tributos = {
                            'II': 'Imposto de Importação (II)',
                            'IPI': 'Imposto sobre Produtos Industrializados (IPI)',
                            'PIS': 'Programa de Integração Social (PIS)',
                            'COFINS': 'Contribuição para o Financiamento da Seguridade Social (COFINS)',
                            'ICMS': 'Imposto sobre Circulação de Mercadorias (ICMS)',
                            'TAXA_UTILIZACAO': 'Taxa de Utilização',
                            'AFRMM': 'Adicional ao Frete para Renovação da Marinha Mercante (AFRMM)'
                        }
                        
                        for tributo in tributos_calculados:
                            if isinstance(tributo, dict):
                                tipo = tributo.get('tipo', 'N/A')
                                valores_brl = tributo.get('valoresBRL', {})
                                
                                if isinstance(valores_brl, dict):
                                    # Priorizar 'devido', depois 'aRecolher', depois 'recolhido'
                                    devido = valores_brl.get('devido')
                                    a_recolher = valores_brl.get('aRecolher')
                                    recolhido = valores_brl.get('recolhido')
                                    
                                    # Usar devido se disponível, senão aRecolher
                                    valor_base = devido if devido else a_recolher
                                    
                                    valor_exibir = None
                                    if valor_base:
                                        try:
                                            valor_float = float(valor_base)
                                            valor_total_devido += valor_float
                                            valor_exibir = valor_float
                                        except (ValueError, TypeError):
                                            pass
                                    
                                    # Também somar recolhido para calcular diferença
                                    if recolhido:
                                        try:
                                            valor_recolhido_float = float(recolhido)
                                            valor_total_recolhido += valor_recolhido_float
                                        except (ValueError, TypeError):
                                            pass
                                    
                                    # Se não tem valor base mas tem recolhido, usar recolhido para exibir
                                    if not valor_exibir and recolhido:
                                        try:
                                            valor_float = float(recolhido)
                                            valor_exibir = valor_float
                                        except (ValueError, TypeError):
                                            pass
                                    
                                    if valor_exibir:
                                        nome_tributo = nomes_tributos.get(tipo, tipo)
                                        detalhes_tributos.append((nome_tributo, valor_exibir))
                        
                        # Adicionar detalhes formatados
                        for nome, valor in detalhes_tributos:
                            resposta_formatada += f"\n   - {nome}: R$ {valor:,.2f}"
                        
                        # Adicionar somatório total e detalhar pendências
                        if valor_total_devido > 0:
                            resposta_formatada += f"\n\n   💰 **TOTAL DEVIDO:** R$ {valor_total_devido:,.2f}"
                            
                            # Verificar se há diferença entre devido e recolhido (indica pendência financeira)
                            if valor_total_recolhido > 0:
                                diferenca = valor_total_devido - valor_total_recolhido
                                if diferenca > 0.01:  # Evitar problemas de ponto flutuante
                                    resposta_formatada += f"\n   ✅ **Valor Recolhido:** R$ {valor_total_recolhido:,.2f}"
                                    resposta_formatada += f"\n   ⚠️ **Valor Pendente de Recolhimento:** R$ {diferenca:,.2f}"
                                    resposta_formatada += f"\n      (Diferença entre valor devido e valor já recolhido/pago)"
                                    
                                    # Detalhar quais impostos estão pendentes
                                    resposta_formatada += "\n\n   📋 **Detalhamento de Recolhimento por Tributo:**"
                                    tem_pendencia_individual = False
                                    for tributo in tributos_calculados:
                                        if isinstance(tributo, dict):
                                            tipo = tributo.get('tipo', 'N/A')
                                            valores_brl = tributo.get('valoresBRL', {})
                                            if isinstance(valores_brl, dict):
                                                devido_trib = valores_brl.get('devido', 0)
                                                recolhido_trib = valores_brl.get('recolhido', 0)
                                                a_recolher_trib = valores_brl.get('aRecolher', 0)
                                                
                                                try:
                                                    devido_float = float(devido_trib) if devido_trib else 0
                                                    recolhido_float = float(recolhido_trib) if recolhido_trib else 0
                                                    a_recolher_float = float(a_recolher_trib) if a_recolher_trib else 0
                                                    
                                                    # Usar aRecolher se devido não estiver disponível
                                                    valor_base = devido_float if devido_float > 0 else a_recolher_float
                                                    
                                                    if valor_base > 0:
                                                        pendente_trib = valor_base - recolhido_float
                                                        nome_tributo = nomes_tributos.get(tipo, tipo)
                                                        
                                                        if recolhido_float > 0:
                                                            if pendente_trib > 0.01:
                                                                resposta_formatada += f"\n      - {nome_tributo}:"
                                                                resposta_formatada += f"\n         Devido: R$ {valor_base:,.2f} | Recolhido: R$ {recolhido_float:,.2f} | Pendente: R$ {pendente_trib:,.2f}"
                                                                tem_pendencia_individual = True
                                                            else:
                                                                resposta_formatada += f"\n      - {nome_tributo}: ✅ Totalmente recolhido (R$ {recolhido_float:,.2f})"
                                                        else:
                                                            resposta_formatada += f"\n      - {nome_tributo}: ⚠️ Pendente de recolhimento (R$ {valor_base:,.2f})"
                                                            tem_pendencia_individual = True
                                                except (ValueError, TypeError):
                                                    pass
                                else:
                                    resposta_formatada += f"\n   ✅ **Valor Totalmente Recolhido:** R$ {valor_total_recolhido:,.2f}"
                            else:
                                resposta_formatada += f"\n   ⚠️ **Valor Pendente de Recolhimento:** R$ {valor_total_devido:,.2f}"
                                resposta_formatada += f"\n      (Nenhum valor foi recolhido ainda)"
                        elif valor_total_recolhido > 0:
                            resposta_formatada += f"\n\n   💰 **TOTAL RECOLHIDO:** R$ {valor_total_recolhido:,.2f}"
                
                # Verificar se há pendências baseado na situação
                if isinstance(situacao, dict):
                    situacao_atual = situacao.get('situacaoDuimp') or situacao.get('situacao') or situacao.get('situacaoDUIMP')
                    if situacao_atual and ('AGUARDANDO' in situacao_atual or 'PENDENCIA' in situacao_atual or 'PENDENTE' in situacao_atual):
                        resposta_formatada += "\n\n⚠️ **Pendências Detectadas:**"
                        resposta_formatada += f"\n   - Situação indica: {situacao_atual}"
                        
                        # Verificar licenciamento
                        situacao_licenciamento = situacao.get('situacaoLicenciamento', '')
                        if situacao_licenciamento and situacao_licenciamento.upper() not in ['DEFERIDO', 'APROVADO']:
                            resposta_formatada += f"\n   - Licenciamento: {situacao_licenciamento}"
                        
                        # Verificar controle de carga
                        controle_carga = situacao.get('controleCarga', '')
                        if controle_carga and 'ENTREGUE' not in controle_carga.upper():
                            resposta_formatada += f"\n   - Controle de Carga: {controle_carga}"
                
                # Adicionar informação sobre PDF (já gerado ou não)
                if 'resposta_pdf' in locals() and resposta_pdf:
                    resposta_formatada += resposta_pdf
                else:
                    resposta_formatada += "\n\n⚠️ **Nota:** Não foi possível gerar o PDF automaticamente."
            
            return {
                'sucesso': True,
                'numero': numero,
                'versao': versao,
                'resposta': resposta_formatada,
                'dados_capa': dados_capa,
                'dados_itens': resultado.get('dados_itens')
            }
        else:
            return {
                'sucesso': False,
                'erro': resultado.get('erro', 'Erro desconhecido'),
                'resposta': resultado.get('resposta', '❌ Erro ao consultar extrato da DUIMP.')
            }

