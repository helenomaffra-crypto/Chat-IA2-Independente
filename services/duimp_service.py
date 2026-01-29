"""
Service dedicado para operações relacionadas a DUIMP (criação, validação, etc).

Este service centraliza a lógica de criação de DUIMP, validações pré-criação,
e outras operações relacionadas, removendo essa responsabilidade do ChatService.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DuimpService:
    """
    Serviço para operações relacionadas a DUIMP.
    
    Responsabilidades:
    - Validação pré-criação de DUIMP
    - Verificação de requisitos mínimos
    - Preparação de informações para criação
    """

    def __init__(self, chat_service=None):
        """
        Args:
            chat_service: Referência opcional ao ChatService para acessar métodos auxiliares
        """
        self.chat_service = chat_service

    def preparar_criacao_duimp(
        self,
        processo_referencia: str,
        ambiente: str = 'validacao',
        contexto_processo: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Prepara a criação de DUIMP validando requisitos e coletando informações.
        
        Args:
            processo_referencia: Referência do processo (ex: "VDM.0004/25")
            ambiente: Ambiente da DUIMP ('producao' ou 'validacao')
            contexto_processo: Contexto do processo (opcional, será buscado se não fornecido)
        
        Returns:
            Dict com informações de validação e preparação:
            {
                'sucesso': bool,
                'pode_criar': bool,
                'resposta': str,  # Mensagem formatada para o usuário
                'itens_faltando': List[str],
                'processo_referencia': str,
                'ambiente': str,
                'acao': 'criar_duimp',
                'mostrar_antes_criar': bool
            }
        """
        processo_ref = (processo_referencia or "").strip()
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'processo_referencia é obrigatório',
                'pode_criar': False,
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = processo_ref
        if self.chat_service and hasattr(self.chat_service, '_extrair_processo_referencia'):
            processo_completo = self.chat_service._extrair_processo_referencia(processo_ref) or processo_ref
        
        # Buscar contexto do processo se não fornecido
        if contexto_processo is None and self.chat_service and hasattr(self.chat_service, '_obter_contexto_processo'):
            contexto_processo = self.chat_service._obter_contexto_processo(processo_completo)
        
        # Construir mensagem informativa
        resposta_info = f"📋 **Informações do Processo {processo_completo}:**\n\n"
        
        # Inicializar variáveis
        tem_duimp = False
        tem_di = False
        itens_faltando: List[str] = []
        tem_ce_ou_cct = False
        
        # Verificar documentos vinculados
        if contexto_processo and contexto_processo.get('encontrado'):
            # CEs
            ces = contexto_processo.get('ces', [])
            if ces:
                tem_ce_ou_cct = True
                resposta_info += "**📦 Conhecimentos de Embarque (CE):**\n"
                for ce in ces:
                    resposta_info += f"  - CE {ce.get('numero', 'N/A')}\n"
                    if ce.get('situacao'):
                        resposta_info += f"    Situação: {ce.get('situacao')}\n"
                    if ce.get('carga_bloqueada'):
                        resposta_info += f"    ⚠️ Carga bloqueada\n"
                resposta_info += "\n"
            else:
                itens_faltando.append("CE (Conhecimento de Embarque) ou CCT (Conhecimento de Carga Aérea) vinculado")
            
            # CCTs
            ccts = contexto_processo.get('ccts', [])
            if ccts:
                tem_ce_ou_cct = True
                resposta_info += "**✈️ Conhecimentos de Carga Aérea (CCT):**\n"
                for cct in ccts:
                    resposta_info += f"  - RUC {cct.get('ruc', cct.get('numero', 'N/A'))}\n"
                    if cct.get('situacao'):
                        resposta_info += f"    Situação: {cct.get('situacao')}\n"
                resposta_info += "\n"
            
            # Verificar dados básicos do processo no Kanban
            try:
                from db_manager import get_db_connection
                import sqlite3
                conn = get_db_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT processo_referencia, modal, porto_destino, pais_origem
                    FROM processos_kanban
                    WHERE processo_referencia = ?
                    LIMIT 1
                ''', (processo_completo,))
                row_kanban = cursor.fetchone()
                conn.close()
                
                if not row_kanban:
                    itens_faltando.append("Dados básicos do processo no Kanban")
                else:
                    # Verificar se tem modal (obrigatório)
                    if not row_kanban.get('modal'):
                        itens_faltando.append("Modal de transporte definido")
            except Exception as e:
                logger.warning(f'Erro ao verificar dados do Kanban: {e}')
                itens_faltando.append("Dados básicos do processo no Kanban")
        else:
            itens_faltando.append("Processo encontrado no sistema")
            itens_faltando.append("CE ou CCT vinculado")
            resposta_info += "⚠️ Processo não encontrado ou sem documentos vinculados.\n\n"
        
        # Verificar se já tem DUIMP
        info_duimp = self._verificar_duimp_existente(processo_completo)
        tem_duimp = info_duimp['existe']
        if info_duimp['mensagem']:
            resposta_info += info_duimp['mensagem']
        
        # Verificar se já tem DI
        if contexto_processo and contexto_processo.get('encontrado'):
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
        
        resposta_info += f"🌐 **Ambiente:** {ambiente.title()}\n\n"
        
        # Validar itens mínimos necessários (só se não tem DUIMP e não tem DI)
        if not tem_duimp and not tem_di:
            if itens_faltando:
                resposta_info += "❌ **Não é possível criar DUIMP - Itens faltando:**\n\n"
                for item in itens_faltando:
                    resposta_info += f"   - {item}\n"
                resposta_info += "\n"
                resposta_info += "💡 **Ação necessária:**\n"
                resposta_info += "   1. Vincule um CE ou CCT ao processo\n"
                resposta_info += "   2. Verifique se o processo está completo no Kanban\n"
                resposta_info += "   3. Após vincular os documentos, tente criar a DUIMP novamente\n"
                
                return {
                    'sucesso': False,
                    'erro': 'ITENS_FALTANDO',
                    'acao': 'criar_duimp',
                    'processo_referencia': processo_completo,
                    'ambiente': ambiente,
                    'resposta': resposta_info,
                    'itens_faltando': itens_faltando,
                    'pode_criar': False
                }
            else:
                # Todos os itens mínimos estão presentes
                resposta_info += "✅ **Itens mínimos verificados:**\n"
                resposta_info += "   - CE ou CCT vinculado ✓\n"
                resposta_info += "   - Dados básicos do processo ✓\n\n"
                resposta_info += "❓ **Deseja criar a DUIMP para este processo?**\n\n"
                resposta_info += "💬 Responda 'sim', 'pode prosseguir', 'criar' ou 'confirmar' para criar a DUIMP."
        
        # Retornar informação para execução
        return {
            'sucesso': True,
            'acao': 'criar_duimp',
            'processo_referencia': processo_completo,
            'ambiente': ambiente,
            'resposta': resposta_info,
            'mostrar_antes_criar': True,
            'pode_criar': not itens_faltando
        }
    
    def _verificar_duimp_existente(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Verifica se já existe DUIMP para o processo.
        
        Args:
            processo_referencia: Referência do processo
        
        Returns:
            Dict com {'existe': bool, 'mensagem': str}
        """
        try:
            import sqlite3
            from db_manager import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            # Buscar QUALQUER DUIMP (produção ou validação) com número
            cursor.execute('''
                SELECT numero, versao, ambiente, status
                FROM duimps
                WHERE processo_referencia = ?
                LIMIT 1
            ''', (processo_referencia,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Se existe DUIMP (qualquer versão/situação/ambiente), não pergunta
                duimp_numero = row[0]
                duimp_versao = row[1]
                duimp_ambiente = row[2] or 'producao'
                duimp_status = row[3] or ''
                
                # Verificar se está registrada (versão >= 1 ou status não vazio)
                versao_int = int(duimp_versao) if duimp_versao and duimp_versao.isdigit() else 0
                if versao_int >= 1 or (duimp_status and duimp_status.upper() not in ['', 'RASCUNHO', 'RASCUNHO_ANULADO', 'EM_ELABORACAO']):
                    mensagem = f"⚠️ **DUIMP já registrada:** {duimp_numero} v{duimp_versao} (ambiente: {duimp_ambiente})\n\n"
                else:
                    mensagem = f"⚠️ **DUIMP existente (rascunho):** {duimp_numero} v{duimp_versao} (ambiente: {duimp_ambiente})\n\n"
                return {'existe': True, 'mensagem': mensagem}
            return {'existe': False, 'mensagem': ''}
        except Exception as e:
            logger.warning(f'Erro ao verificar DUIMP do processo {processo_referencia}: {e}')
            return {'existe': False, 'mensagem': ''}
    
    def verificar_duimp_registrada(
        self,
        processo_referencia: str,
    ) -> Dict[str, Any]:
        """
        Verifica se há DUIMP registrada para um processo (priorizando produção).
        
        Args:
            processo_referencia: Referência do processo
        
        Returns:
            Dict com informações sobre a DUIMP encontrada
        """
        processo_ref = (processo_referencia or "").strip()
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'processo_referencia é obrigatório',
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = processo_ref
        if self.chat_service and hasattr(self.chat_service, '_extrair_processo_referencia'):
            processo_completo = self.chat_service._extrair_processo_referencia(processo_ref) or processo_ref
        
        # Verificar DUIMP de PRODUÇÃO primeiro
        duimp_info = self._verificar_duimp_producao(processo_completo)
        
        if duimp_info.get('existe') and duimp_info.get('eh_producao'):
            # Encontrou DUIMP de PRODUÇÃO
            resposta = f"📋 **DUIMP de PRODUÇÃO encontrada para o processo {processo_completo}:**\n\n"
            resposta += f"**Número:** {duimp_info.get('numero', 'N/A')} v{duimp_info.get('versao', 'N/A')}\n"
            resposta += f"**Situação:** {duimp_info.get('situacao', duimp_info.get('status', 'N/A'))}\n"
            resposta += f"**Ambiente:** Produção\n"
            if duimp_info.get('criado_em'):
                resposta += f"**Criada em:** {duimp_info.get('criado_em')}\n"
        else:
            # NÃO encontrou DUIMP de PRODUÇÃO - verificar se há de validação
            duimp_validacao = self._verificar_duimp_validacao(processo_completo)
            
            # Formatar resposta
            resposta = f"⚠️ **DUIMP de PRODUÇÃO:** Não encontrada para o processo {processo_completo}.\n\n"
            
            if duimp_validacao:
                # Existe DUIMP de validação - informar como informação adicional
                resposta += f"ℹ️ **Informação adicional (ambiente de testes):**\n"
                resposta += f"   - DUIMP {duimp_validacao.get('numero', 'N/A')} v{duimp_validacao.get('versao', 'N/A')}\n"
                resposta += f"   - Situação: {duimp_validacao.get('situacao', 'Rascunho')}\n"
                resposta += f"   - Ambiente: Validação (apenas testes)\n"
                if duimp_validacao.get('criado_em'):
                    resposta += f"   - Criada em: {duimp_validacao.get('criado_em')}\n"
                resposta += f"\n💡 **Nota:** DUIMPs de validação são apenas para testes e não são consideradas como produção.\n"
            else:
                # Não há nem produção nem validação
                resposta += f"💡 **Nota:** Não há DUIMP de produção nem de validação para este processo.\n"
        
        return {
            'sucesso': True,
            'resposta': resposta,
            'duimp_info': duimp_info
        }
    
    def _verificar_duimp_producao(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Verifica se há DUIMP de PRODUÇÃO para o processo.
        
        Returns:
            Dict com {'existe': bool, 'eh_producao': bool, 'numero': str, 'versao': str, ...}
        """
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar DUIMP de PRODUÇÃO
            cursor.execute('''
                SELECT numero, versao, status, ambiente, criado_em, payload_completo
                FROM duimps
                WHERE processo_referencia = ? AND ambiente = 'producao'
                ORDER BY CAST(versao AS INTEGER) DESC, criado_em DESC
                LIMIT 1
            ''', (processo_referencia,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Extrair situação do payload
                situacao = None
                try:
                    import json
                    payload_str = row['payload_completo']
                    if payload_str:
                        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                        if isinstance(payload, dict):
                            situacao_obj = payload.get('situacao', {})
                            if isinstance(situacao_obj, dict):
                                situacao = situacao_obj.get('situacaoDuimp', '')
                except:
                    pass
                
                return {
                    'existe': True,
                    'eh_producao': True,
                    'numero': row['numero'],
                    'versao': row['versao'],
                    'status': row['status'],
                    'situacao': situacao or row['status'],
                    'ambiente': 'producao',
                    'criado_em': row['criado_em']
                }
            
            return {'existe': False, 'eh_producao': False}
        except Exception as e:
            logger.warning(f'Erro ao verificar DUIMP de produção: {e}')
            return {'existe': False, 'eh_producao': False}
    
    def _verificar_duimp_validacao(self, processo_referencia: str) -> Optional[Dict[str, Any]]:
        """
        Verifica se há DUIMP de VALIDAÇÃO para o processo.
        
        Returns:
            Dict com dados da DUIMP de validação ou None
        """
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
            ''', (processo_referencia,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # Extrair situação do payload
                situacao = None
                try:
                    import json
                    payload_str = row['payload_completo']
                    if payload_str:
                        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
                        if isinstance(payload, dict):
                            situacao_obj = payload.get('situacao', {})
                            if isinstance(situacao_obj, dict):
                                situacao = situacao_obj.get('situacaoDuimp', '')
                except:
                    pass
                
                return {
                    'numero': row['numero'],
                    'versao': row['versao'],
                    'status': row['status'],
                    'situacao': situacao or row['status'],
                    'ambiente': 'validacao',
                    'criado_em': row['criado_em']
                }
            
            return None
        except Exception as e:
            logger.debug(f'Erro ao buscar DUIMP de validação: {e}')
            return None













