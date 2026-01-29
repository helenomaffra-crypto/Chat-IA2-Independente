"""
Service dedicado para operações relacionadas a documentos (DI, DUIMP, CE).

Este service centraliza a lógica de obtenção de dados de documentos,
valores de processos, etc., removendo essa responsabilidade do ChatService.
"""

import logging
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


class DocumentoService:
    """
    Serviço para operações relacionadas a documentos.
    
    Responsabilidades:
    - Obter dados de DI
    - Obter dados de DUIMP
    - Obter valores de processo
    - Obter valores de CE
    """

    def __init__(self, chat_service=None):
        """
        Args:
            chat_service: Referência opcional ao ChatService para acessar métodos auxiliares
        """
        self.chat_service = chat_service

    def obter_dados_di(
        self,
        numero_di: str,
    ) -> Dict[str, Any]:
        """
        Obtém dados completos de uma DI.
        
        Args:
            numero_di: Número da DI
        
        Returns:
            Dict com dados da DI
        """
        numero_di = (numero_di or "").strip()
        
        if not numero_di:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_di é obrigatório'
            }
        
        try:
            from db_manager import buscar_di_cache
            
            di_cache = buscar_di_cache(numero_di)
            if not di_cache:
                return {
                    'sucesso': False,
                    'erro': 'DI_NAO_ENCONTRADA',
                    'mensagem': f'DI {numero_di} não encontrada no cache. Consulte a DI primeiro.'
                }
            
            situacao = di_cache.get('situacao_di', '')
            canal = di_cache.get('canal_selecao_parametrizada', '')
            data_desembaraco = di_cache.get('data_hora_desembaraco', '')
            data_registro = di_cache.get('data_hora_registro', '')
            situacao_entrega = di_cache.get('situacao_entrega_carga', '')
            
            resposta = f"📄 **DI {numero_di}**\n\n"
            resposta += f"**Situação:** {situacao or 'N/A'}\n"
            
            if canal:
                resposta += f"**Canal:** {canal}\n"
            
            if data_desembaraco:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(data_desembaraco.replace('Z', '+00:00'))
                    resposta += f"**Data de Desembaraço:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                except:
                    resposta += f"**Data de Desembaraço:** {data_desembaraco}\n"
            
            if data_registro:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(data_registro.replace('Z', '+00:00'))
                    resposta += f"**Data de Registro:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                except:
                    resposta += f"**Data de Registro:** {data_registro}\n"
            
            if situacao_entrega:
                resposta += f"**Situação de Entrega:** {situacao_entrega}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': di_cache
            }
        except Exception as e:
            logger.error(f'Erro ao obter dados da DI {numero_di}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar dados da DI: {str(e)}'
            }

    def obter_dados_duimp(
        self,
        numero_duimp: str,
        versao_duimp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Obtém dados completos de uma DUIMP.
        
        Args:
            numero_duimp: Número da DUIMP (pode incluir versão: "25BR00001928777-1")
            versao_duimp: Versão da DUIMP (opcional, será extraída do número se não fornecida)
        
        Returns:
            Dict com dados da DUIMP
        """
        numero_duimp_raw = (numero_duimp or "").strip()
        
        if not numero_duimp_raw:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_duimp é obrigatório'
            }
        
        try:
            from db_manager import buscar_duimp
            
            # Extrair número e versão se estiver no formato 25BR00001928777-1
            numero_duimp_clean = numero_duimp_raw
            versao_final = versao_duimp
            
            if '-' in numero_duimp_raw:
                partes = numero_duimp_raw.split('-', 1)
                numero_duimp_clean = partes[0]
                if len(partes) > 1:
                    versao_final = partes[1]
            
            # Se versão não fornecida, tentar buscar versão vigente
            if not versao_final:
                # Tentar buscar do processo se encontrar vinculado
                try:
                    import sqlite3
                    from db_manager import get_db_connection
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT DISTINCT pd.numero_documento, pd.versao_documento, p.numero, p.versao, p.situacao, p.status
                        FROM processo_documentos pd
                        LEFT JOIN duimps p ON pd.numero_documento = p.numero AND pd.versao_documento = p.versao
                        WHERE pd.tipo_documento = 'DUIMP' AND pd.numero_documento = ?
                        ORDER BY CAST(pd.versao_documento AS INTEGER) DESC
                        LIMIT 1
                    ''', (numero_duimp_clean,))
                    row = cursor.fetchone()
                    conn.close()
                    
                    if row:
                        versao_final = row[1] or '1'
                except:
                    versao_final = '1'  # Default para versão 1
            
            duimp_cache = buscar_duimp(numero_duimp_clean, versao_final)
            if not duimp_cache:
                return {
                    'sucesso': False,
                    'erro': 'DUIMP_NAO_ENCONTRADA',
                    'mensagem': f'DUIMP {numero_duimp_clean} (versão {versao_final or "vigente"}) não encontrada no cache.'
                }
            
            # Extrair dados da DUIMP
            versao = versao_final or duimp_cache.get('versao', '1')
            status = duimp_cache.get('status', '')
            ambiente = duimp_cache.get('ambiente', '')
            
            # Tentar extrair situação do payload
            situacao = status
            canal = ''
            try:
                payload_str = duimp_cache.get('payload_completo', '')
                if payload_str:
                    payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                    if isinstance(payload, dict):
                        situacao_obj = payload.get('situacao', {})
                        if isinstance(situacao_obj, dict):
                            situacao = situacao_obj.get('situacaoDuimp', status)
                        canal_obj = payload.get('canal', {})
                        if isinstance(canal_obj, dict):
                            canal = canal_obj.get('codigo', '') or canal_obj.get('nome', '')
            except:
                pass
            
            criado_em = duimp_cache.get('criado_em', '')
            processo_ref = duimp_cache.get('processo_referencia', '')
            
            # Se não tem processo_ref no cache, tentar buscar da tabela processo_documentos
            if not processo_ref:
                try:
                    import sqlite3
                    from db_manager import get_db_connection
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT processo_referencia
                        FROM processo_documentos
                        WHERE tipo_documento = 'DUIMP' AND numero_documento = ? AND versao_documento = ?
                        LIMIT 1
                    ''', (numero_duimp_clean, versao))
                    row = cursor.fetchone()
                    conn.close()
                    if row:
                        processo_ref = row[0]
                except:
                    pass
            
            resposta = f"📋 **DUIMP {numero_duimp_clean} v{versao or 'N/A'}**\n\n"
            resposta += f"**Situação:** {situacao or 'N/A'}\n"
            
            if canal:
                resposta += f"**Canal:** {canal}\n"
            
            if criado_em:
                try:
                    from datetime import datetime
                    if isinstance(criado_em, str):
                        dt = datetime.fromisoformat(criado_em.replace('Z', '+00:00'))
                    else:
                        dt = criado_em
                    resposta += f"**Data de Registro:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                except:
                    resposta += f"**Data de Registro:** {str(criado_em)}\n"
            
            if ambiente:
                resposta += f"**Ambiente:** {ambiente}\n"
            
            if processo_ref:
                resposta += f"**Processo:** {processo_ref}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': duimp_cache
            }
        except Exception as e:
            logger.error(f'Erro ao obter dados da DUIMP {numero_duimp_raw}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar dados da DUIMP: {str(e)}'
            }

    def obter_valores_processo(
        self,
        processo_referencia: str,
        tipo_valor: str = 'todos',
    ) -> Dict[str, Any]:
        """
        Obtém valores (frete, seguro, FOB, CIF) de um processo.
        
        Args:
            processo_referencia: Referência do processo
            tipo_valor: Tipo de valor a obter ('frete', 'seguro', 'fob', 'cif', 'todos')
        
        Returns:
            Dict com valores do processo
        """
        processo_ref = (processo_referencia or "").strip()
        tipo_valor = (tipo_valor or 'todos').strip().lower()
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'processo_referencia é obrigatório'
            }
        
        try:
            from db_manager import obter_dados_documentos_processo
            
            # Expandir processo se necessário
            processo_completo = processo_ref
            if self.chat_service and hasattr(self.chat_service, '_extrair_processo_referencia'):
                processo_completo = self.chat_service._extrair_processo_referencia(processo_ref) or processo_ref
            
            dados = obter_dados_documentos_processo(processo_completo)
            
            valores = {
                'frete': None,
                'frete_moeda': '',
                'seguro': None,
                'seguro_moeda': '',
                'fob': None,
                'fob_moeda': '',
                'cif': None,
                'cif_moeda': ''
            }
            
            # Extrair do CE
            ces = dados.get('ces', [])
            if ces:
                ce = ces[0]
                ce_json = ce.get('dados_completos', {})
                
                # Frete
                valor_frete = ce_json.get('valorFreteTotal', '')
                if valor_frete:
                    try:
                        valores['frete'] = float(str(valor_frete).replace(',', '.'))
                        valores['frete_moeda'] = ce_json.get('moedaFrete', '')
                    except:
                        pass
                
                # Tentar extrair do JSON consolidado se existir
                if 'json_consolidado' in ce:
                    json_cons = ce.get('json_consolidado', {})
                    if isinstance(json_cons, str):
                        try:
                            json_cons = json.loads(json_cons)
                        except:
                            json_cons = {}
                    
                    valores_json = json_cons.get('valores', {})
                    
                    # Frete
                    frete_info = valores_json.get('frete', {})
                    if frete_info:
                        valores['frete'] = frete_info.get('total_moeda') or frete_info.get('valor') or valores['frete']
                        valores['frete_moeda'] = frete_info.get('moeda_codigo') or frete_info.get('moeda') or valores['frete_moeda']
                    
                    # Seguro
                    seguro_info = valores_json.get('seguro', {})
                    if seguro_info:
                        valores['seguro'] = seguro_info.get('total_moeda') or seguro_info.get('valor')
                        valores['seguro_moeda'] = seguro_info.get('moeda_codigo') or seguro_info.get('moeda')
                    
                    # FOB
                    fob_info = valores_json.get('fob', {})
                    if fob_info:
                        valores['fob'] = fob_info.get('total_moeda') or fob_info.get('valor')
                        valores['fob_moeda'] = fob_info.get('moeda_codigo') or fob_info.get('moeda')
                    
                    # CIF
                    cif_info = valores_json.get('cif', {})
                    if cif_info:
                        valores['cif'] = cif_info.get('total_moeda') or cif_info.get('valor')
                        valores['cif_moeda'] = cif_info.get('moeda_codigo') or cif_info.get('moeda')
            
            # Formatar resposta
            def formatar_valor(valor, moeda=''):
                if valor is None:
                    return "N/A"
                try:
                    valor_float = float(valor)
                    if moeda:
                        # Converter código de moeda numérico para código ISO se necessário
                        codigos_moeda = {'220': 'USD', '790': 'BRL', '978': 'EUR'}
                        moeda_iso = codigos_moeda.get(str(moeda), str(moeda))
                        return f"{moeda_iso} {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    return f"{valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                except:
                    return str(valor)
            
            resposta = f"💰 **Valores do Processo {processo_completo}**\n\n"
            
            if tipo_valor in ('frete', 'todos'):
                resposta += f"🚢 **Frete:** {formatar_valor(valores['frete'], valores['frete_moeda'])}\n"
            
            if tipo_valor in ('seguro', 'todos'):
                resposta += f"🛡️ **Seguro:** {formatar_valor(valores['seguro'], valores['seguro_moeda'])}\n"
            
            if tipo_valor in ('fob', 'todos'):
                resposta += f"📦 **FOB:** {formatar_valor(valores['fob'], valores['fob_moeda'])}\n"
            
            if tipo_valor in ('cif', 'todos'):
                resposta += f"🚢 **CIF:** {formatar_valor(valores['cif'], valores['cif_moeda'])}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'valores': valores
            }
        except Exception as e:
            logger.error(f'Erro ao obter valores do processo {processo_ref}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar valores: {str(e)}'
            }

    def obter_valores_ce(
        self,
        numero_ce: str,
        tipo_valor: str = 'todos',
    ) -> Dict[str, Any]:
        """
        Obtém valores (frete, seguro, FOB, CIF) de um CE.
        
        Args:
            numero_ce: Número do CE
            tipo_valor: Tipo de valor a obter ('frete', 'seguro', 'fob', 'cif', 'todos')
        
        Returns:
            Dict com valores do CE
        """
        numero_ce = (numero_ce or "").strip()
        tipo_valor = (tipo_valor or 'todos').strip().lower()
        
        if not numero_ce:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_ce é obrigatório'
            }
        
        try:
            from db_manager import buscar_ce_cache
            
            ce_cache = buscar_ce_cache(numero_ce)
            if not ce_cache:
                return {
                    'sucesso': False,
                    'erro': 'CE_NAO_ENCONTRADO',
                    'mensagem': f'CE {numero_ce} não encontrado no cache. Consulte o CE primeiro.'
                }
            
            # Extrair valores do CE
            ce_json = ce_cache.get('dados_completos', {})
            json_consolidado = ce_cache.get('json_consolidado', {})
            
            valores = {
                'frete': None,
                'frete_moeda': '',
                'seguro': None,
                'seguro_moeda': '',
                'fob': None,
                'fob_moeda': '',
                'cif': None,
                'cif_moeda': ''
            }
            
            # Extrair do JSON consolidado se existir
            if json_consolidado:
                if isinstance(json_consolidado, str):
                    try:
                        json_consolidado = json.loads(json_consolidado)
                    except:
                        json_consolidado = {}
                
                valores_json = json_consolidado.get('valores', {})
                
                # Frete
                frete_info = valores_json.get('frete', {})
                if frete_info:
                    valores['frete'] = frete_info.get('total_moeda') or frete_info.get('valor')
                    valores['frete_moeda'] = frete_info.get('moeda_codigo') or frete_info.get('moeda')
                
                # Seguro
                seguro_info = valores_json.get('seguro', {})
                if seguro_info:
                    valores['seguro'] = seguro_info.get('total_moeda') or seguro_info.get('valor')
                    valores['seguro_moeda'] = seguro_info.get('moeda_codigo') or seguro_info.get('moeda')
                
                # FOB
                fob_info = valores_json.get('fob', {})
                if fob_info:
                    valores['fob'] = fob_info.get('total_moeda') or fob_info.get('valor')
                    valores['fob_moeda'] = fob_info.get('moeda_codigo') or fob_info.get('moeda')
                
                # CIF
                cif_info = valores_json.get('cif', {})
                if cif_info:
                    valores['cif'] = cif_info.get('total_moeda') or cif_info.get('valor')
                    valores['cif_moeda'] = cif_info.get('moeda_codigo') or cif_info.get('moeda')
            
            # Fallback: extrair do dados_completos se não encontrou no consolidado
            if not valores['frete']:
                valor_frete = ce_json.get('valorFreteTotal', '')
                if valor_frete:
                    try:
                        valores['frete'] = float(str(valor_frete).replace(',', '.'))
                        valores['frete_moeda'] = ce_json.get('moedaFrete', '')
                    except:
                        pass
            
            # Formatar resposta
            def formatar_valor(valor, moeda=''):
                if valor is None:
                    return "N/A"
                try:
                    valor_float = float(valor)
                    if moeda:
                        codigos_moeda = {'220': 'USD', '790': 'BRL', '978': 'EUR'}
                        moeda_iso = codigos_moeda.get(str(moeda), str(moeda))
                        return f"{moeda_iso} {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    return f"{valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                except:
                    return str(valor)
            
            resposta = f"💰 **Valores do CE {numero_ce}**\n\n"
            
            if tipo_valor in ('frete', 'todos'):
                resposta += f"🚢 **Frete:** {formatar_valor(valores['frete'], valores['frete_moeda'])}\n"
            
            if tipo_valor in ('seguro', 'todos'):
                resposta += f"🛡️ **Seguro:** {formatar_valor(valores['seguro'], valores['seguro_moeda'])}\n"
            
            if tipo_valor in ('fob', 'todos'):
                resposta += f"📦 **FOB:** {formatar_valor(valores['fob'], valores['fob_moeda'])}\n"
            
            if tipo_valor in ('cif', 'todos'):
                resposta += f"🚢 **CIF:** {formatar_valor(valores['cif'], valores['cif_moeda'])}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'valores': valores
            }
        except Exception as e:
            logger.error(f'Erro ao obter valores do CE {numero_ce}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar valores: {str(e)}'
            }













