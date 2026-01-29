"""
Service dedicado para operações de vinculação de documentos a processos.

Este service centraliza a lógica de vinculação/desvinculação de documentos
(CE, CCT, DI, DUIMP) a processos, removendo essa responsabilidade do ChatService.
"""

import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VinculacaoService:
    """
    Serviço para operações de vinculação de documentos a processos.
    
    Responsabilidades:
    - Vincular CE a processo
    - Vincular CCT a processo
    - Vincular DI a processo
    - Vincular DUIMP a processo
    - Desvincular documentos de processos
    """

    def __init__(self, chat_service=None):
        """
        Args:
            chat_service: Referência opcional ao ChatService para acessar métodos auxiliares
        """
        self.chat_service = chat_service

    def vincular_ce(
        self,
        numero_ce: str,
        processo_referencia: str,
    ) -> Dict[str, Any]:
        """
        Vincula um CE a um processo.
        
        Args:
            numero_ce: Número do CE
            processo_referencia: Referência do processo
        
        Returns:
            Dict com resultado da vinculação
        """
        numero_ce = (numero_ce or "").strip()
        processo_ref = (processo_referencia or "").strip()
        
        if not numero_ce:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_ce é obrigatório'
            }
        
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
        
        # Desvincular CEs existentes antes de vincular o novo
        from db_manager import desvincular_todos_documentos_tipo, listar_documentos_processo
        ces_existentes = [doc for doc in listar_documentos_processo(processo_completo) if doc.get('tipo_documento') == 'CE']
        if ces_existentes:
            desvinculados = desvincular_todos_documentos_tipo(processo_completo, 'CE')
            if desvinculados > 0:
                logger.info(f'✅ {desvinculados} CE(s) antigo(s) desvinculado(s) do processo {processo_completo} antes de vincular o novo')
        
        try:
            from db_manager import atualizar_processo_ce_cache, buscar_ce_cache, vincular_documento_processo
            
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
                'mensagem': f'Erro interno ao vincular processo: {str(e)}'
            }

    def vincular_cct(
        self,
        numero_cct: str,
        processo_referencia: str,
    ) -> Dict[str, Any]:
        """
        Vincula um CCT a um processo.
        
        Args:
            numero_cct: Número do CCT
            processo_referencia: Referência do processo
        
        Returns:
            Dict com resultado da vinculação
        """
        numero_cct = (numero_cct or "").strip()
        processo_ref = (processo_referencia or "").strip()
        
        if not numero_cct:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_cct é obrigatório'
            }
        
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
        
        # Desvincular CCTs existentes antes de vincular o novo
        from db_manager import desvincular_todos_documentos_tipo, listar_documentos_processo
        ccts_existentes = [doc for doc in listar_documentos_processo(processo_completo) if doc.get('tipo_documento') == 'CCT']
        if ccts_existentes:
            desvinculados = desvincular_todos_documentos_tipo(processo_completo, 'CCT')
            if desvinculados > 0:
                logger.info(f'✅ {desvinculados} CCT(s) antigo(s) desvinculado(s) do processo {processo_completo} antes de vincular o novo')
        
        try:
            from db_manager import atualizar_processo_cct_cache, buscar_cct_cache, vincular_documento_processo
            
            # Normalizar número do CCT (aceitar com ou sem hífen)
            cct_cache = buscar_cct_cache(numero_cct)
            
            # Se não encontrou, tentar formatos alternativos
            if not cct_cache:
                # Tentar sem hífen (se tinha hífen)
                numero_cct_alternativo = numero_cct.replace('-', '')
                if numero_cct_alternativo != numero_cct:
                    cct_cache = buscar_cct_cache(numero_cct_alternativo)
                    if cct_cache:
                        numero_cct = numero_cct_alternativo
                        logger.info(f'✅ CCT encontrado no formato alternativo: {numero_cct}')
            
            # Se ainda não encontrou, tentar com hífen (se não tinha)
            if not cct_cache:
                # Tentar adicionar hífen após 3 letras (ex: MIA4673 -> MIA-4673)
                if len(numero_cct) > 3 and numero_cct[3] != '-':
                    numero_cct_alternativo = f"{numero_cct[:3]}-{numero_cct[3:]}"
                    cct_cache = buscar_cct_cache(numero_cct_alternativo)
                    if cct_cache:
                        numero_cct = numero_cct_alternativo
                        logger.info(f'✅ CCT encontrado no formato alternativo: {numero_cct}')
            
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
                    'mensagem': resposta,
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
                'mensagem': f'Erro interno ao vincular processo: {str(e)}'
            }

    def vincular_di(
        self,
        numero_di: str,
        processo_referencia: str,
    ) -> Dict[str, Any]:
        """
        Vincula uma DI a um processo.
        
        Args:
            numero_di: Número da DI
            processo_referencia: Referência do processo
        
        Returns:
            Dict com resultado da vinculação
        """
        numero_di = (numero_di or "").strip()
        processo_ref = (processo_referencia or "").strip()
        
        if not numero_di:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_di é obrigatório'
            }
        
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
            from db_manager import atualizar_processo_di_cache, buscar_di_cache, vincular_documento_processo
            
            # Verificar se a DI existe no cache
            di_cache = buscar_di_cache(numero_di=numero_di)
            if not di_cache:
                return {
                    'sucesso': False,
                    'erro': 'DI_NAO_ENCONTRADO_CACHE',
                    'resposta': f"⚠️ **DI {numero_di} não encontrada no cache.**\n\n💡 **Dica:** É necessário consultar a DI primeiro antes de vincular a um processo."
                }
            
            # Vincular processo à DI
            vincular_documento_processo(processo_completo, 'DI', numero_di)
            
            # Atualizar também o cache da DI
            sucesso = atualizar_processo_di_cache(numero_di, processo_completo)
            
            if sucesso:
                resposta = f"✅ **Processo vinculado com sucesso!**\n\n"
                resposta += f"**DI:** {numero_di}\n"
                resposta += f"**Processo:** {processo_completo}\n\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'numero_di': numero_di,
                    'processo_referencia': processo_completo
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_VINCULACAO',
                    'resposta': f"❌ **Erro ao vincular processo {processo_completo} à DI {numero_di}.**"
                }
                
        except Exception as e:
            logger.error(f'Erro ao vincular processo à DI: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro interno ao vincular processo: {str(e)}'
            }

    def vincular_duimp(
        self,
        numero_duimp: str,
        processo_referencia: str,
    ) -> Dict[str, Any]:
        """
        Vincula uma DUIMP a um processo.
        
        Args:
            numero_duimp: Número da DUIMP
            processo_referencia: Referência do processo
        
        Returns:
            Dict com resultado da vinculação
        """
        numero_duimp = (numero_duimp or "").strip()
        processo_ref = (processo_referencia or "").strip()
        
        if not numero_duimp:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_duimp é obrigatório'
            }
        
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
            from db_manager import vincular_documento_processo, get_db_connection
            import sqlite3
            
            # Verificar se a DUIMP existe
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT numero, versao, ambiente
                FROM duimps
                WHERE numero = ?
                LIMIT 1
            ''', (numero_duimp,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {
                    'sucesso': False,
                    'erro': 'DUIMP_NAO_ENCONTRADA',
                    'resposta': f"⚠️ **DUIMP {numero_duimp} não encontrada.**\n\n💡 **Dica:** Verifique se o número da DUIMP está correto."
                }
            
            # Vincular processo à DUIMP
            vincular_documento_processo(processo_completo, 'DUIMP', numero_duimp)
            
            # Atualizar processo_referencia na tabela duimps
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE duimps
                SET processo_referencia = ?
                WHERE numero = ?
            ''', (processo_completo, numero_duimp))
            conn.commit()
            conn.close()
            
            resposta = f"✅ **Processo vinculado com sucesso!**\n\n"
            resposta += f"**DUIMP:** {numero_duimp}\n"
            resposta += f"**Processo:** {processo_completo}\n\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'numero_duimp': numero_duimp,
                'processo_referencia': processo_completo
            }
                
        except Exception as e:
            logger.error(f'Erro ao vincular processo à DUIMP: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro interno ao vincular processo: {str(e)}'
            }

    def vincular_processo_duimp(
        self,
        numero_duimp_raw: str,
        processo_referencia: str,
        versao_duimp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Vincula uma DUIMP ou DI a um processo com reconhecimento automático.
        
        Esta função reconhece automaticamente se o número informado é uma DUIMP ou DI
        baseado no padrão do número, e vincula o documento correto ao processo.
        
        Args:
            numero_duimp_raw: Número do documento (pode ser DUIMP ou DI)
            processo_referencia: Referência do processo
            versao_duimp: Versão da DUIMP (opcional, será detectada automaticamente se não informada)
        
        Returns:
            Dict com resultado da vinculação
        """
        numero_duimp_raw = (numero_duimp_raw or "").strip()
        processo_ref = (processo_referencia or "").strip()
        versao_duimp_param = (versao_duimp or "").strip() if versao_duimp else None
        
        if not numero_duimp_raw:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'numero_duimp é obrigatório'
            }
        
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
            # ✅ Reconhecer automaticamente DUIMP vs DI pelo padrão do número
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
            
            # ✅ Para DUIMP, se versão não foi informada, usar padrão
            versao_final = None
            if tipo_documento == 'DUIMP':
                # Prioridade: versão do parâmetro > versão detectada > padrão (0)
                versao_final = versao_duimp_param or versao_detectada
                
                if not versao_final:
                    # Usar versão 0 como padrão (rascunho)
                    versao_final = '0'
                    logger.info(f'⚠️ Versão não informada para DUIMP {numero_documento}. Usando versão 0 (rascunho).')
            elif tipo_documento == 'DI':
                # DI não tem versão
                versao_final = None
            
            # Vincular documento ao processo
            from db_manager import vincular_documento_processo
            
            if tipo_documento == 'DUIMP':
                # Para DUIMP, verificar se existe antes de vincular
                from db_manager import buscar_duimp, atualizar_processo_duimp_cache
                
                duimp = buscar_duimp(numero_documento, versao_final or '0')
                
                if not duimp:
                    # Se não encontrou, ainda assim vincular (DUIMP pode não estar no banco local ainda)
                    logger.info(f'⚠️ DUIMP {numero_documento} v{versao_final} não encontrada no banco local. Vinculando mesmo assim (pode ser consultada automaticamente).')
                
                # Vincular
                vincular_documento_processo(processo_completo, 'DUIMP', f"{numero_documento}v{versao_final}")
                
                # Atualizar também o banco da DUIMP
                sucesso = atualizar_processo_duimp_cache(numero_documento, versao_final, processo_completo)
                
                if sucesso:
                    resposta = f"✅ **DUIMP vinculada com sucesso!**\n\n"
                    resposta += f"**DUIMP:** {numero_documento} v{versao_final}\n"
                    resposta += f"**Processo:** {processo_completo}\n\n"
                    resposta += f"🎯 **DUIMP vinculada ao processo!** O Kanban será atualizado automaticamente."
                    
                    return {
                        'sucesso': True,
                        'mensagem': resposta,
                        'resposta': resposta,  # Compatibilidade
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
                    'mensagem': resposta,
                    'resposta': resposta,  # Compatibilidade
                    'processo': processo_completo,
                    'di': numero_documento,
                    'tipo': 'DI'
                }
                
        except Exception as e:
            logger.error(f'Erro ao vincular processo à DUIMP/DI: {e}', exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro interno ao vincular processo: {str(e)}'
            }

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
        padrao_di = r'\b(\d{2}/\d{7,10}-\d)\b'
        match_di = re.search(padrao_di, mensagem)
        if match_di:
            numero_di = match_di.group(1)
            return {
                'tipo': 'DI',
                'numero': numero_di,
                'versao': None,
                'numero_completo': numero_di
            }
        
        return None

    def desvincular_documento(
        self,
        processo_referencia: str,
        tipo_documento: str,
        numero_documento: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Desvincula um documento de um processo.
        
        Args:
            processo_referencia: Referência do processo
            tipo_documento: Tipo do documento ('CE', 'CCT', 'DI', 'DUIMP')
            numero_documento: Número do documento (opcional, se None desvincula todos do tipo)
        
        Returns:
            Dict com resultado da desvinculação
        """
        processo_ref = (processo_referencia or "").strip()
        tipo_doc = (tipo_documento or "").strip().upper()
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'processo_referencia é obrigatório'
            }
        
        if not tipo_doc:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'tipo_documento é obrigatório'
            }
        
        # Expandir processo se necessário
        processo_completo = processo_ref
        if self.chat_service and hasattr(self.chat_service, '_extrair_processo_referencia'):
            processo_completo = self.chat_service._extrair_processo_referencia(processo_ref) or processo_ref
        
        try:
            from db_manager import desvincular_documento_processo, desvincular_todos_documentos_tipo
            
            if numero_documento:
                # Desvincular documento específico
                sucesso = desvincular_documento_processo(processo_completo, tipo_doc, numero_documento)
                if sucesso:
                    resposta = f"✅ **Documento desvinculado com sucesso!**\n\n"
                    resposta += f"**Tipo:** {tipo_doc}\n"
                    resposta += f"**Número:** {numero_documento}\n"
                    resposta += f"**Processo:** {processo_completo}\n"
                    
                    return {
                        'sucesso': True,
                        'resposta': resposta
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_DESVINCULACAO',
                        'resposta': f"❌ **Erro ao desvincular {tipo_doc} {numero_documento} do processo {processo_completo}.**"
                    }
            else:
                # Desvincular todos os documentos do tipo
                desvinculados = desvincular_todos_documentos_tipo(processo_completo, tipo_doc)
                if desvinculados > 0:
                    resposta = f"✅ **{desvinculados} documento(s) {tipo_doc} desvinculado(s) com sucesso!**\n\n"
                    resposta += f"**Processo:** {processo_completo}\n"
                    
                    return {
                        'sucesso': True,
                        'resposta': resposta,
                        'total_desvinculados': desvinculados
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': 'NENHUM_DOCUMENTO',
                        'resposta': f"⚠️ **Nenhum documento {tipo_doc} encontrado para desvincular do processo {processo_completo}.**"
                    }
                
        except Exception as e:
            logger.error(f'Erro ao desvincular documento: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro interno ao desvincular documento: {str(e)}'
            }













