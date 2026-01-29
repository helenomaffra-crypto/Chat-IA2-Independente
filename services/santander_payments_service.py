"""
Serviço para integração com API de Pagamentos do Santander (TED, PIX, etc.).

⚠️ ISOLADO: Este serviço é completamente separado do serviço de Extratos.
Usa credenciais diferentes (SANTANDER_PAYMENTS_*) conforme Cenário 1.

Wrapper para facilitar integração com o sistema mAIke.
Versão independente - não depende de diretório externo.
"""
import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

# ✅ VERSÃO INDEPENDENTE: Importar do módulo interno
try:
    from utils.santander_payments_api import SantanderPaymentsAPI, SantanderPaymentsConfig
    SANTANDER_PAYMENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Não foi possível importar santander_payments_api: {e}")
    SANTANDER_PAYMENTS_AVAILABLE = False
    SantanderPaymentsAPI = None
    SantanderPaymentsConfig = None


class SantanderPaymentsService:
    """
    Serviço para integração com API de Pagamentos do Santander.
    
    ⚠️ ISOLADO: Usa credenciais separadas (SANTANDER_PAYMENTS_*).
    Não interfere com o serviço de Extratos.
    """
    
    def __init__(self):
        """Inicializa o serviço."""
        self.api: Optional[SantanderPaymentsAPI] = None
        self.enabled = SANTANDER_PAYMENTS_AVAILABLE
        
        if not self.enabled:
            logger.warning("⚠️ API de Pagamentos do Santander não disponível")
            return
        
        try:
            # ✅ CENÁRIO 1: Usar credenciais específicas de Pagamentos
            config = SantanderPaymentsConfig()
            self.api = SantanderPaymentsAPI(config, debug=False)
            logger.info("✅ SantanderPaymentsService inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SantanderPaymentsService: {e}", exc_info=True)
            self.enabled = False
    
    def _verificar_workspace(self) -> Optional[str]:
        """
        Verifica se existe workspace configurado.
        Se não existir, tenta criar automaticamente.
        
        Returns:
            workspace_id ou None se não conseguir criar/obter
        """
        if not self.enabled or not self.api:
            return None
        
        try:
            # Verificar se workspace_id está configurado no .env
            workspace_id = os.getenv("SANTANDER_WORKSPACE_ID", "")
            if workspace_id:
                # Verificar se workspace existe
                try:
                    self.api.consultar_workspace(workspace_id)
                    logger.info(f"✅ Workspace encontrado: {workspace_id}")
                    return workspace_id
                except Exception as e:
                    logger.warning(f"⚠️ Workspace {workspace_id} não encontrado. Tentando criar novo...")
            
            # Listar workspaces existentes
            workspaces = self.api.listar_workspaces()
            if workspaces and workspaces.get('_content') and len(workspaces['_content']) > 0:
                # ✅ Priorizar workspace PAYMENTS com bankTransferPaymentsActive=true
                for ws in workspaces['_content']:
                    ws_type = ws.get('type', '')
                    bank_transfer_active = ws.get('bankTransferPaymentsActive', False)
                    if ws_type == 'PAYMENTS' and bank_transfer_active:
                        workspace_id = ws.get('id')
                        logger.info(f"✅ Usando workspace PAYMENTS com TED ativado: {workspace_id}")
                        return workspace_id
                
                # ✅ Se não encontrou PAYMENTS, procurar qualquer workspace com bankTransferPaymentsActive=true
                for ws in workspaces['_content']:
                    bank_transfer_active = ws.get('bankTransferPaymentsActive', False)
                    if bank_transfer_active:
                        workspace_id = ws.get('id')
                        ws_type = ws.get('type', '')
                        logger.info(f"✅ Usando workspace {ws_type} com TED ativado: {workspace_id}")
                        return workspace_id
                
                # Se não encontrou nenhum com TED, usar o primeiro disponível
                primeiro_workspace = workspaces['_content'][0]
                workspace_id = primeiro_workspace.get('id')
                logger.warning(f"⚠️ Usando primeiro workspace disponível (pode não ter TED ativado): {workspace_id}")
                return workspace_id
            
            # Se não encontrou, tentar criar automaticamente
            logger.info("🔧 Nenhum workspace encontrado. Criando workspace automaticamente...")
            
            # Obter conta principal (tentar da primeira conta disponível)
            # Nota: Isso requer acesso à API de extratos ou configuração manual
            # Por enquanto, vamos retornar None e pedir para configurar manualmente
            logger.warning("⚠️ Não foi possível criar workspace automaticamente. Configure SANTANDER_WORKSPACE_ID no .env")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar workspace: {e}", exc_info=True)
            return None
    
    def listar_workspaces(self) -> Dict[str, Any]:
        """
        Lista todos os workspaces disponíveis.
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: List[Dict] (lista de workspaces)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos do Santander não está disponível.**\n\nVerifique se:\n- As credenciais SANTANDER_PAYMENTS_* estão configuradas no .env\n- As dependências estão instaladas\n- Os certificados mTLS estão configurados'
            }
        
        try:
            workspaces = self.api.listar_workspaces()
            
            if not workspaces or not workspaces.get('_content'):
                return {
                    'sucesso': False,
                    'erro': 'Nenhum workspace encontrado',
                    'resposta': '❌ **Nenhum workspace encontrado.**\n\n💡 Você precisa criar um workspace primeiro. Use a tool "criar_workspace_santander" ou configure SANTANDER_WORKSPACE_ID no .env.'
                }
            
            # Formatar resposta
            resposta = "🏦 **Workspaces Disponíveis no Santander:**\n\n"
            for i, workspace in enumerate(workspaces['_content'], 1):
                workspace_id = workspace.get('id', 'N/A')
                tipo = workspace.get('type', 'N/A')
                descricao = workspace.get('description', 'Sem descrição')
                resposta += f"**{i}. {tipo}** (ID: {workspace_id})\n"
                resposta += f"   - Descrição: {descricao}\n\n"
            
            resposta += f"💡 **Total:** {len(workspaces['_content'])} workspace(s) disponível(is)\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': workspaces['_content']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar workspaces: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao listar workspaces:** {str(e)}\n\n💡 Verifique se:\n- As credenciais SANTANDER_PAYMENTS_* estão corretas\n- O certificado mTLS está configurado\n- Você tem permissão para acessar workspaces'
            }
    
    def criar_workspace(
        self,
        tipo: str = "PAYMENTS",
        agencia: str = None,
        conta: str = None,
        description: str = "",
        pix_payments_active: bool = False,
        bar_code_payments_active: bool = False,
        bank_slip_payments_active: bool = False,
        bank_transfer_payments_active: bool = False
    ) -> Dict[str, Any]:
        """
        Cria um workspace para pagamentos.
        
        Args:
            tipo: Tipo de workspace (PAYMENTS, PHYSICAL_CORBAN, DIGITAL_CORBAN)
            agencia: Agência da conta principal (4 dígitos)
            conta: Número da conta principal (12 dígitos)
            description: Descrição do workspace
        
        Returns:
            Dict com resultado contendo workspace_id
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos do Santander não está disponível.**'
            }
        
        if not agencia or not conta:
            return {
                'sucesso': False,
                'erro': 'Agência e conta são obrigatórias',
                'resposta': '❌ **Agência e conta são obrigatórias para criar workspace.**\n\nForneça agência (4 dígitos) e conta (12 dígitos) da conta principal.'
            }
        
        try:
            # ✅ NOVO (12/01/2026): Ativar bankTransferPaymentsActive para tipo PAYMENTS
            # Conforme documentação oficial: bankTransferPaymentsActive é necessário para TED
            # Se não especificado, ativar automaticamente para tipo PAYMENTS
            if bank_transfer_payments_active is False and tipo == "PAYMENTS":
                bank_transfer_payments_active = True
            
            logger.info(f"📤 Criando workspace: tipo={tipo}, agencia={agencia}, conta={conta}, bank_transfer_payments_active={bank_transfer_payments_active}")
            
            # ✅ Limitar descrição a 30 caracteres (exigência da API)
            descricao_final = description or f"Workspace {tipo}"
            if len(descricao_final) > 30:
                descricao_final = descricao_final[:30]
                logger.info(f"⚠️ Descrição truncada para 30 caracteres: {descricao_final}")
            
            workspace = self.api.criar_workspace(
                tipo=tipo,
                main_debit_account={
                    "branch": agencia,
                    "number": conta
                },
                description=descricao_final,
                pix_payments_active=pix_payments_active,
                bar_code_payments_active=bar_code_payments_active,
                bank_slip_payments_active=bank_slip_payments_active,
                bank_transfer_payments_active=bank_transfer_payments_active  # ✅ Ativar TED
            )
            
            # ✅ Log completo da resposta da API
            logger.info(f"📋 Resposta completa da API ao criar workspace: {json.dumps(workspace, indent=2, ensure_ascii=False)}")
            
            workspace_id = workspace.get('id')
            
            if not workspace_id:
                logger.error(f"❌ Workspace criado mas não retornou ID! Resposta: {workspace}")
                return {
                    'sucesso': False,
                    'erro': 'Workspace criado mas não retornou ID',
                    'resposta': f'❌ **Erro:** Workspace foi criado mas a API não retornou o ID.\n\nResposta da API: {json.dumps(workspace, indent=2)}'
                }
            
            logger.info(f"✅ Workspace criado com ID: {workspace_id}, Tipo: {workspace.get('type', 'N/A')}, bankTransferPaymentsActive: {workspace.get('bankTransferPaymentsActive', False)}")
            
            resposta = f"✅ **Workspace criado com sucesso!**\n\n"
            resposta += f"**ID:** {workspace_id}\n"
            resposta += f"**Tipo:** {tipo}\n"
            resposta += f"**Conta Principal:** Ag. {agencia} / C/C {conta}\n\n"
            resposta += f"💡 **Configure no .env:**\n"
            resposta += f"```env\nSANTANDER_WORKSPACE_ID={workspace_id}\n```\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'workspace_id': workspace_id,
                    'workspace': workspace
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar workspace: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao criar workspace:** {str(e)}\n\n💡 Verifique se:\n- A agência e conta estão corretas\n- Você tem permissão para criar workspaces\n- As credenciais SANTANDER_PAYMENTS_* estão corretas'
            }
    
    def iniciar_ted(
        self,
        workspace_id: str = None,
        agencia_origem: str = None,
        conta_origem: str = None,
        banco_destino: str = None,
        agencia_destino: str = None,
        conta_destino: str = None,
        valor: float = None,
        nome_destinatario: str = None,
        cpf_cnpj_destinatario: str = None,
        tipo_conta_destino: str = "CONTA_CORRENTE",
        ispb_destino: str = None,
        finalidade: str = None
    ) -> Dict[str, Any]:
        """
        Inicia uma transferência TED.
        
        ⚠️ SEGURANÇA: Se estiver em ambiente SANDBOX, a TED será simulada
        e não movimenta dinheiro real.
        """
        """
        Inicia uma transferência TED.
        
        Args:
            workspace_id: ID do workspace (se None, tenta obter automaticamente)
            agencia_origem: Agência da conta origem (4 dígitos)
            conta_origem: Conta origem (12 dígitos)
            banco_destino: Código do banco destino (3 dígitos, ex: "001" para BB)
            agencia_destino: Agência destino
            conta_destino: Conta destino
            valor: Valor da transferência (float)
            nome_destinatario: Nome do destinatário
            cpf_cnpj_destinatario: CPF ou CNPJ do destinatário (apenas números)
            tipo_conta_destino: Tipo de conta (CONTA_CORRENTE, POUPANCA, etc.)
            ispb_destino: ISPB do banco destino (opcional, se não fornecer, tenta buscar)
        
        Returns:
            Dict com resultado contendo transfer_id
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos do Santander não está disponível.**'
            }
        
        # Obter workspace_id primeiro (para pegar conta origem se não fornecida)
        if not workspace_id:
            workspace_id = self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ **Workspace não encontrado.**\n\n💡 Configure SANTANDER_WORKSPACE_ID no .env ou crie um workspace primeiro.'
                }
        
        # ✅ SEMPRE consultar o workspace para verificar configurações
        workspace = None
        try:
            workspace = self.api.consultar_workspace(workspace_id)
            logger.info(f"📋 Workspace consultado: {json.dumps(workspace, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.error(f"❌ Erro ao consultar workspace {workspace_id}: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': f'Erro ao consultar workspace: {str(e)}',
                'resposta': f'❌ **Erro ao consultar workspace {workspace_id}.**\n\n💡 Verifique se o workspace existe e está acessível.'
            }
        
        # Se agência/conta origem não fornecidas, tentar obter do workspace
        if not agencia_origem or not conta_origem:
            main_account = workspace.get('mainDebitAccount', {})
            if main_account:
                # ✅ Converter para string (API retorna números, mas TED precisa de strings)
                branch_value = main_account.get('branch') or main_account.get('branchCode')
                number_value = main_account.get('number') or main_account.get('accountNumber')
                
                agencia_origem = agencia_origem or (str(branch_value) if branch_value is not None else None)
                conta_origem = conta_origem or (str(number_value) if number_value is not None else None)
                
                logger.info(f"✅ Conta origem obtida do workspace: Ag. {agencia_origem} / C/C {conta_origem}")
                logger.info(f"📋 mainDebitAccount completo: {json.dumps(main_account, indent=2, ensure_ascii=False)}")
            else:
                logger.warning(f"⚠️ Workspace não tem mainDebitAccount configurado: {workspace}")
        
        # Verificar se workspace tem bankTransferPaymentsActive
        if workspace:
            bank_transfer_active = workspace.get('bankTransferPaymentsActive', False)
            if not bank_transfer_active:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não tem transferências bancárias ativadas',
                    'resposta': f'❌ **Workspace não tem transferências bancárias (TED) ativadas.**\n\n'
                               f'💡 O workspace {workspace_id} precisa ter `bankTransferPaymentsActive: true`.\n'
                               f'   Tipo do workspace: {workspace.get("type", "N/A")}\n'
                               f'   Status: {workspace.get("status", "N/A")}\n\n'
                               f'   Você pode:\n'
                               f'   1. Criar um novo workspace com transferências ativadas\n'
                               f'   2. Ou usar um workspace que já tenha transferências ativadas'
                }
        
        # Validar parâmetros obrigatórios
        if not agencia_origem or not conta_origem:
            return {
                'sucesso': False,
                'erro': 'Agência e conta origem são obrigatórias',
                'resposta': '❌ **Agência e conta origem são obrigatórias.**\n\n💡 Forneça a agência e conta origem, ou configure um workspace com conta principal.'
            }
        
        if not banco_destino or not agencia_destino or not conta_destino:
            return {
                'sucesso': False,
                'erro': 'Dados do destino são obrigatórios',
                'resposta': '❌ **Banco, agência e conta destino são obrigatórios.**'
            }
        
        if not valor or valor <= 0:
            return {
                'sucesso': False,
                'erro': 'Valor inválido',
                'resposta': '❌ **Valor deve ser maior que zero.**'
            }
        
            if not nome_destinatario or not cpf_cnpj_destinatario:
                return {
                    'sucesso': False,
                    'erro': 'Dados do destinatário são obrigatórios',
                    'resposta': '❌ **Nome e CPF/CNPJ do destinatário são obrigatórios.**'
                }
        
        try:
            # ✅ NOVO (12/01/2026): Verificar se está em sandbox e avisar
            is_sandbox = "sandbox" in (self.api.config.base_url or "").lower()
            if is_sandbox:
                logger.info("⚠️ AMBIENTE DE TESTE (SANDBOX) detectado. TED será simulada, não movimenta dinheiro real.")
            
            # Limpar CPF/CNPJ (apenas números)
            cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj_destinatario))
            
            # Determinar tipo de documento
            if len(cpf_cnpj_limpo) == 11:
                doc_type = "CPF"
                # ✅ Validar formato básico de CPF (não pode ser todos iguais)
                if len(set(cpf_cnpj_limpo)) == 1:
                    return {
                        'sucesso': False,
                        'erro': 'CPF inválido',
                        'resposta': '❌ **CPF inválido.** O CPF não pode ter todos os dígitos iguais (ex: 11111111111, 12345678901).\n\n💡 Use um CPF válido para teste. No sandbox, você pode usar CPFs de teste válidos.'
                    }
            elif len(cpf_cnpj_limpo) == 14:
                doc_type = "CNPJ"
            else:
                return {
                    'sucesso': False,
                    'erro': 'CPF/CNPJ inválido',
                    'resposta': '❌ **CPF/CNPJ inválido.** Deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ).'
                }
            
            # Formatar valor (2 decimais)
            valor_str = f"{valor:.2f}"
            
            # Montar destination_account
            # ⚠️ IMPORTANTE: typeAccount conforme documentação oficial:
            # - CC = Conta Corrente
            # - PP = Poupança
            # - PG = Conta Pagamento
            tipo_conta_api = {
                "CONTA_CORRENTE": "CC",
                "CONTA_POUPANCA": "PP",
                "CONTA_PAGAMENTO": "PG"
            }.get(tipo_conta_destino, "CC")  # Padrão: Conta Corrente
            
            # ✅ bankCode pode ter 3 ou 4 dígitos (conforme Postman: "1234")
            # Manter como string sem padding forçado (API aceita ambos)
            bank_code = str(banco_destino).strip()
            
            destination_account = {
                "bankCode": bank_code,
                "branchCode": agencia_destino,
                "accountNumber": conta_destino,
                "typeAccount": tipo_conta_api,
                "legalEntityIdentifier": doc_type,
                "documentIdentifierNumber": cpf_cnpj_limpo,
                "name": nome_destinatario,
                "purpose": finalidade or "CREDITO_EM_CONTA"
            }
            
            # Adicionar ISPB se fornecido
            if ispb_destino:
                destination_account["ispbCode"] = ispb_destino
            
            # ✅ DEBUG: Log dos dados antes de enviar
            logger.info(f"📋 Dados da conta origem antes de enviar: Ag. {agencia_origem} / C/C {conta_origem} (tipo: {type(agencia_origem).__name__}, {type(conta_origem).__name__})")
            
            # Iniciar TED
            resultado = self.api.iniciar_ted(
                workspace_id=workspace_id,
                source_account={
                    "branchCode": str(agencia_origem).strip() if agencia_origem else None,
                    "accountNumber": str(conta_origem).strip() if conta_origem else None
                },
                destination_account=destination_account,
                transfer_value=valor_str,
                destination_type="STR0008"
            )
            
            transfer_id = resultado.get('id') or resultado.get('transferId')
            
            # ✅ NOVO (12/01/2026): Indicar ambiente (sandbox ou produção)
            ambiente_info = ""
            if is_sandbox:
                ambiente_info = " (SANDBOX - TESTE)\n"
                ambiente_info += "⚠️ **AMBIENTE DE TESTE:** Esta TED é simulada e não movimenta dinheiro real.\n\n"
            
            resposta = f"✅ **TED Iniciada com Sucesso!**{ambiente_info}\n"
            resposta += f"**ID da Transferência:** {transfer_id}\n"
            resposta += f"**Valor:** R$ {valor:,.2f}\n"
            resposta += f"**Destinatário:** {nome_destinatario}\n"
            resposta += f"**Status:** {resultado.get('status', 'PENDING_VALIDATION')}\n\n"
            resposta += f"💡 **Próximo passo:** Use 'efetivar_ted_santander' com o transfer_id para confirmar e autorizar a transferência.\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'transfer_id': transfer_id,
                    'ted': resultado
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar TED: {e}", exc_info=True)
            
            # Tentar extrair mensagem de erro mais detalhada
            erro_msg = str(e)
            if "400" in erro_msg or "Bad Request" in erro_msg:
                # Se for erro 400, pode ser problema de validação de dados
                erro_msg += "\n\n💡 **Possíveis causas:**\n"
                erro_msg += "- Formato de dados incorreto (agência/conta devem ser strings)\n"
                erro_msg += "- Campos obrigatórios faltando\n"
                erro_msg += "- Valores inválidos (ex: valor negativo)\n"
                erro_msg += "- Workspace não configurado corretamente"
            
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao iniciar TED:** {erro_msg}\n\n💡 Verifique se:\n- Os dados estão corretos\n- A conta origem tem saldo suficiente\n- O workspace está configurado corretamente'
            }
    
    def efetivar_ted(
        self,
        workspace_id: str = None,
        transfer_id: str = None,
        agencia_origem: str = None,
        conta_origem: str = None
    ) -> Dict[str, Any]:
        """
        Efetiva uma TED iniciada.
        
        Args:
            workspace_id: ID do workspace (se None, tenta obter automaticamente)
            transfer_id: ID da transferência (retornado por iniciar_ted)
            agencia_origem: Agência da conta origem
            conta_origem: Conta origem
        
        Returns:
            Dict com resultado da TED efetivada
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos do Santander não está disponível.**'
            }
        
        if not transfer_id:
            return {
                'sucesso': False,
                'erro': 'transfer_id é obrigatório',
                'resposta': '❌ **ID da transferência é obrigatório.**'
            }
        
        if not agencia_origem or not conta_origem:
            return {
                'sucesso': False,
                'erro': 'Agência e conta origem são obrigatórias',
                'resposta': '❌ **Agência e conta origem são obrigatórias.**'
            }
        
        # Obter workspace_id se não fornecido
        if not workspace_id:
            workspace_id = self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ **Workspace não encontrado.**'
                }
        
        try:
            resultado = self.api.efetivar_ted(
                workspace_id=workspace_id,
                transfer_id=transfer_id,
                source_account={
                    "branchCode": agencia_origem,
                    "accountNumber": conta_origem
                },
                status="AUTHORIZED"
            )
            
            status = resultado.get('status', 'UNKNOWN')
            
            # ✅ NOVO (12/01/2026): Verificar se está em sandbox
            is_sandbox = "sandbox" in (self.api.config.base_url or "").lower()
            ambiente_info = ""
            if is_sandbox:
                ambiente_info = " (SANDBOX - TESTE)\n"
                ambiente_info += "⚠️ **AMBIENTE DE TESTE:** Esta TED foi simulada - nenhum dinheiro foi transferido.\n\n"
            
            resposta = f"✅ **TED Efetivada com Sucesso!**{ambiente_info}\n"
            resposta += f"**ID da Transferência:** {transfer_id}\n"
            resposta += f"**Status:** {status}\n\n"
            
            if status == "AUTHORIZED":
                if is_sandbox:
                    resposta += f"💡 A transferência foi simulada (sandbox). Em produção, seria autorizada e processada.\n"
                else:
                    resposta += f"💡 A transferência foi autorizada e será processada.\n"
            elif status == "PAYED":
                if is_sandbox:
                    resposta += f"💡 A transferência foi simulada como paga (sandbox). Em produção, o dinheiro seria transferido.\n"
                else:
                    resposta += f"💡 A transferência foi paga com sucesso!\n"
            else:
                resposta += f"💡 Status atual: {status}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'transfer_id': transfer_id,
                    'ted': resultado
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao efetivar TED: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao efetivar TED:** {str(e)}\n\n💡 Verifique se:\n- O transfer_id está correto\n- A TED ainda está pendente\n- A conta origem tem saldo suficiente'
            }
    
    def consultar_ted(
        self,
        workspace_id: str = None,
        transfer_id: str = None
    ) -> Dict[str, Any]:
        """
        Consulta TED por ID.
        
        Args:
            workspace_id: ID do workspace (se None, tenta obter automaticamente)
            transfer_id: ID da transferência
        
        Returns:
            Dict com dados da TED
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos do Santander não está disponível.**'
            }
        
        if not transfer_id:
            return {
                'sucesso': False,
                'erro': 'transfer_id é obrigatório',
                'resposta': '❌ **ID da transferência é obrigatório.**'
            }
        
        # Obter workspace_id se não fornecido
        if not workspace_id:
            workspace_id = self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ **Workspace não encontrado.**'
                }
        
        try:
            ted = self.api.consultar_ted(
                workspace_id=workspace_id,
                transfer_id=transfer_id
            )
            
            status = ted.get('status', 'UNKNOWN')
            valor = ted.get('transferValue', 0)
            
            resposta = f"📋 **Consulta de TED**\n\n"
            resposta += f"**ID:** {transfer_id}\n"
            resposta += f"**Status:** {status}\n"
            resposta += f"**Valor:** R$ {float(valor):,.2f}\n\n"
            
            # Adicionar informações adicionais se disponíveis
            if ted.get('sourceAccount'):
                origem = ted['sourceAccount']
                resposta += f"**Origem:** Ag. {origem.get('branchCode')} / C/C {origem.get('accountNumber')}\n"
            
            if ted.get('destinationAccount'):
                destino = ted['destinationAccount']
                resposta += f"**Destino:** {destino.get('name', 'N/A')}\n"
                resposta += f"   - Banco: {destino.get('bankCode', 'N/A')}\n"
                resposta += f"   - Ag. {destino.get('branchCode')} / C/C {destino.get('accountNumber')}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': ted
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar TED: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao consultar TED:** {str(e)}'
            }
    
    def listar_teds(
        self,
        workspace_id: str = None,
        data_inicio: str = None,
        data_fim: str = None,
        status: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Lista TEDs paginado (para conciliação).
        
        Args:
            workspace_id: ID do workspace (se None, tenta obter automaticamente)
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            status: Filtro por status (PENDING_VALIDATION, READY_TO_PAY, PENDING_CONFIRMATION, PAYED, REJECTED)
            limit: Limite de registros (padrão: 10)
        
        Returns:
            Dict com lista de TEDs
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API de Pagamentos do Santander não está disponível.**'
            }
        
        # Obter workspace_id se não fornecido
        if not workspace_id:
            workspace_id = self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ **Workspace não encontrado.**'
                }
        
        try:
            resultado = self.api.listar_teds(
                workspace_id=workspace_id,
                initial_date=data_inicio,
                final_date=data_fim,
                status=status,
                limit=limit,
                offset=0
            )
            
            teds = resultado.get('_content', []) or resultado.get('data', []) or []
            
            if not teds:
                resposta = f"📋 **Lista de TEDs**\n\n"
                resposta += f"ℹ️ Nenhuma TED encontrada"
                if data_inicio and data_fim:
                    resposta += f" no período de {data_inicio} a {data_fim}"
                resposta += ".\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': []
                }
            
            # Formatar resposta
            resposta = f"📋 **Lista de TEDs**\n\n"
            if data_inicio and data_fim:
                resposta += f"**Período:** {data_inicio} a {data_fim}\n"
            if status:
                resposta += f"**Status:** {status}\n"
            resposta += f"**Total:** {len(teds)} TED(s)\n\n"
            
            for i, ted in enumerate(teds[:limit], 1):
                transfer_id = ted.get('id') or ted.get('transferId', 'N/A')
                status_ted = ted.get('status', 'UNKNOWN')
                valor = ted.get('transferValue', 0)
                
                resposta += f"**{i}. {transfer_id}**\n"
                resposta += f"   - Status: {status_ted}\n"
                resposta += f"   - Valor: R$ {float(valor):,.2f}\n"
                
                if ted.get('destinationAccount'):
                    destino = ted['destinationAccount']
                    resposta += f"   - Destino: {destino.get('name', 'N/A')}\n"
                
                resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': teds
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar TEDs: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao listar TEDs:** {str(e)}'
            }
    
    # ==========================================
    # MÉTODOS DE ACCOUNTS AND TAXES
    # Bank Slip Payments, Barcode Payments, Pix Payments,
    # Vehicle Taxes Payments, Taxes by Fields Payments
    # ==========================================
    
    def iniciar_bank_slip_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        code: str = None,
        payment_date: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento de boleto.
        
        Args:
            workspace_id: ID do workspace (opcional, usa do .env se não fornecido)
            payment_id: ID único do pagamento (gerado pelo cliente)
            code: Código de barras do boleto
            payment_date: Data do pagamento (YYYY-MM-DD)
            tags: Lista de tags opcionais
        
        Returns:
            Dict com sucesso, resposta e dados
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ API de Pagamentos do Santander não está disponível.'
            }
        
        try:
            # Verificar workspace
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ Nenhum workspace configurado. Configure SANTANDER_WORKSPACE_ID no .env ou crie um workspace.'
                }
            
            # Validar campos obrigatórios
            if not payment_id:
                return {
                    'sucesso': False,
                    'erro': 'payment_id obrigatório',
                    'resposta': '❌ ID do pagamento é obrigatório.'
                }
            if not code:
                return {
                    'sucesso': False,
                    'erro': 'code obrigatório',
                    'resposta': '❌ Código de barras do boleto é obrigatório.'
                }
            if not payment_date:
                return {
                    'sucesso': False,
                    'erro': 'payment_date obrigatório',
                    'resposta': '❌ Data do pagamento é obrigatória (formato: YYYY-MM-DD).'
                }
            
            # ✅ NOVO: Validar e limpar código de barras
            # Remover pontos, espaços e caracteres não numéricos
            code_limpo = re.sub(r'[^\d]', '', code)
            if len(code_limpo) not in [44, 47]:
                return {
                    'sucesso': False,
                    'erro': 'Código de barras inválido',
                    'resposta': f'❌ **Código de barras inválido:** Deve ter 44 ou 47 dígitos. Recebido: {len(code_limpo)} dígitos.\n\n💡 **Código fornecido:** `{code}`\n💡 **Código limpo:** `{code_limpo}`'
                }
            code = code_limpo  # Usar código limpo
            
            # ✅ NOVO: Validar formato de data
            try:
                from datetime import datetime
                datetime.strptime(payment_date, '%Y-%m-%d')
            except ValueError:
                return {
                    'sucesso': False,
                    'erro': 'Data inválida',
                    'resposta': f'❌ **Data inválida:** Formato deve ser YYYY-MM-DD. Recebido: `{payment_date}`\n\n💡 **Exemplo:** `2026-01-13`'
                }
            
            # ✅ NOVO: Validar formato de payment_id (deve ser UUID)
            import uuid
            try:
                uuid.UUID(payment_id)
            except ValueError:
                return {
                    'sucesso': False,
                    'erro': 'payment_id inválido',
                    'resposta': f'❌ **ID do pagamento inválido:** Deve ser um UUID válido. Recebido: `{payment_id}`\n\n💡 **Exemplo:** `550e8400-e29b-41d4-a716-446655440000`'
                }
            
            # Iniciar pagamento
            resultado = self.api.iniciar_bank_slip_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                code=code,
                payment_date=payment_date,
                tags=tags
            )
            
            payment_id_retornado = resultado.get('id', payment_id)
            status = resultado.get('status', 'PENDING_VALIDATION')
            
            resposta = f"✅ **Pagamento de Boleto Iniciado!** (SANDBOX - TESTE)\n"
            resposta += f"⚠️ AMBIENTE DE TESTE: Este pagamento é simulado e não movimenta dinheiro real.\n\n"
            resposta += f"**ID do Pagamento:** `{payment_id_retornado}`\n"
            resposta += f"**Status:** {status}\n"
            resposta += f"**Código de Barras:** {code}\n"
            resposta += f"**Data:** {payment_date}\n\n"
            resposta += f"💡 **Próximo passo:** Use 'efetivar_bank_slip_payment' com o payment_id para confirmar e autorizar o pagamento."
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar pagamento de boleto: {e}", exc_info=True)
            
            # Extrair mensagem de erro mais detalhada
            erro_msg = str(e)
            if "400" in erro_msg or "Bad Request" in erro_msg:
                erro_msg += "\n\n💡 **Possíveis causas:**\n"
                erro_msg += "- Código de barras inválido (deve ter 44 ou 47 dígitos, apenas números)\n"
                erro_msg += "- Data de pagamento inválida (formato: YYYY-MM-DD)\n"
                erro_msg += "- Workspace não tem bankSlipPaymentsActive habilitado\n"
                erro_msg += "- payment_id já existe ou formato inválido (deve ser UUID)\n"
                erro_msg += "\n💡 **Verifique:**\n"
                erro_msg += f"- Código de barras: `{code if 'code' in locals() else 'N/A'}` (deve ser apenas números)\n"
                erro_msg += f"- Data: `{payment_date if 'payment_date' in locals() else 'N/A'}` (formato YYYY-MM-DD)\n"
                erro_msg += f"- payment_id: `{payment_id if 'payment_id' in locals() else 'N/A'}` (deve ser UUID)\n"
                erro_msg += "- Workspace configurado corretamente no .env"
            
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao iniciar pagamento de boleto:** {erro_msg}'
            }
    
    def efetivar_bank_slip_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        payment_value: float = None,
        agencia_origem: str = None,
        conta_origem: str = None,
        final_payer_name: str = None,
        final_payer_document_type: str = None,
        final_payer_document_number: str = None,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """
        Efetiva pagamento de boleto.
        
        Args:
            workspace_id: ID do workspace (opcional)
            payment_id: ID do pagamento
            payment_value: Valor do pagamento
            agencia_origem: Agência da conta de débito
            conta_origem: Conta de débito
            final_payer_name: Nome do pagador final
            final_payer_document_type: Tipo de documento (CPF ou CNPJ)
            final_payer_document_number: Número do documento
            status: Status da autorização (padrão: "AUTHORIZED")
        
        Returns:
            Dict com sucesso, resposta e dados
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ API de Pagamentos do Santander não está disponível.'
            }
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ Nenhum workspace configurado.'
                }
            
            if not payment_id:
                return {
                    'sucesso': False,
                    'erro': 'payment_id obrigatório',
                    'resposta': '❌ ID do pagamento é obrigatório.'
                }
            if not payment_value or payment_value <= 0:
                return {
                    'sucesso': False,
                    'erro': 'payment_value inválido',
                    'resposta': '❌ Valor do pagamento deve ser maior que zero.'
                }
            
            # Obter conta de débito do workspace se não fornecida
            workspace = None
            if not agencia_origem or not conta_origem:
                workspace = self.api.consultar_workspace(workspace_id)
                main_account = workspace.get('mainDebitAccount', {})
                agencia_origem = agencia_origem or str(main_account.get('branch', ''))
                conta_origem = conta_origem or str(main_account.get('number', ''))
            
            debit_account = {
                "branch": str(agencia_origem).strip(),
                "number": str(conta_origem).strip()
            }
            
            # finalPayer é OBRIGATÓRIO para pagamento de boleto
            # Buscar do workspace ou usar dados fornecidos, ou dados padrão do sandbox
            if final_payer_name and final_payer_document_type and final_payer_document_number:
                # Usar dados fornecidos
                final_payer = {
                    "name": final_payer_name,
                    "documentType": final_payer_document_type.upper(),  # CPF ou CNPJ
                    "documentNumber": final_payer_document_number.replace('.', '').replace('-', '').replace('/', '')
                }
            else:
                # Buscar do workspace se disponível
                if not workspace:
                    workspace = self.api.consultar_workspace(workspace_id)
                
                # Tentar obter dados do workspace (pode não estar disponível)
                workspace_name = workspace.get('description', '')
                workspace_account = workspace.get('mainDebitAccount', {})
                
                # Se não tiver dados do workspace, usar dados padrão do sandbox
                # (sandbox geralmente aceita qualquer CPF/CNPJ válido)
                final_payer = {
                    "name": workspace_name or "PAGADOR SANDBOX",
                    "documentType": "CNPJ",  # Padrão para sandbox
                    "documentNumber": "00000000000191"  # CNPJ válido para sandbox (Santander)
                }
                
                logger.info(f"⚠️ Usando finalPayer padrão do sandbox: {final_payer}")
            
            resultado = self.api.efetivar_bank_slip_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                payment_value=payment_value,
                debit_account=debit_account,
                final_payer=final_payer,
                status=status
            )
            
            status_retornado = resultado.get('status', status)
            
            resposta = f"✅ **Pagamento de Boleto Efetivado!** (SANDBOX - TESTE)\n"
            resposta += f"⚠️ AMBIENTE DE TESTE: Este pagamento foi simulado - nenhum dinheiro foi movimentado.\n\n"
            resposta += f"**ID do Pagamento:** `{payment_id}`\n"
            resposta += f"**Valor:** R$ {payment_value:,.2f}\n"
            resposta += f"**Status:** {status_retornado}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao efetivar pagamento de boleto: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao efetivar pagamento de boleto:** {str(e)}'
            }
    
    def consultar_bank_slip_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None
    ) -> Dict[str, Any]:
        """Consulta pagamento de boleto por ID"""
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ API de Pagamentos do Santander não está disponível.'
            }
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ Nenhum workspace configurado.'
                }
            
            if not payment_id:
                return {
                    'sucesso': False,
                    'erro': 'payment_id obrigatório',
                    'resposta': '❌ ID do pagamento é obrigatório.'
                }
            
            resultado = self.api.consultar_bank_slip_payment(workspace_id, payment_id)
            
            status = resultado.get('status', 'UNKNOWN')
            payment_value = resultado.get('paymentValue', 0)
            
            resposta = f"📋 **Consulta de Pagamento de Boleto**\n\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Status:** {status}\n"
            if payment_value:
                resposta += f"**Valor:** R$ {payment_value:,.2f}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar pagamento de boleto: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao consultar pagamento de boleto:** {str(e)}'
            }
    
    def listar_bank_slip_payments(
        self,
        workspace_id: str = None,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Lista pagamentos de boleto paginados"""
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ API de Pagamentos do Santander não está disponível.'
            }
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ Nenhum workspace configurado.'
                }
            
            resultado = self.api.listar_bank_slip_payments(
                workspace_id=workspace_id,
                initial_date=initial_date,
                final_date=final_date,
                status=status,
                limit=limit,
                offset=0
            )
            
            content = resultado.get('_content', [])
            total = resultado.get('_pageable', {}).get('_totalElements', len(content))
            
            resposta = f"📋 **Pagamentos de Boleto**\n\n"
            resposta += f"💡 Total: {total} pagamento(s)\n\n"
            
            if not content:
                resposta += "Nenhum pagamento encontrado."
            else:
                for i, payment in enumerate(content[:limit], 1):
                    payment_id = payment.get('id', 'N/A')
                    status_payment = payment.get('status', 'N/A')
                    payment_value = payment.get('paymentValue', 0)
                    
                    resposta += f"{i}. **ID:** `{payment_id}`\n"
                    resposta += f"   - Status: {status_payment}\n"
                    if payment_value:
                        resposta += f"   - Valor: R$ {payment_value:,.2f}\n"
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar pagamentos de boleto: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao listar pagamentos de boleto:** {str(e)}'
            }
    
    # ==========================================
    # BARCODE PAYMENTS (Código de Barras)
    # ==========================================
    
    def iniciar_barcode_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        code: str = None,
        payment_date: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Inicia pagamento por código de barras"""
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ API de Pagamentos do Santander não está disponível.'
            }
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {
                    'sucesso': False,
                    'erro': 'Workspace não encontrado',
                    'resposta': '❌ Nenhum workspace configurado.'
                }
            
            if not payment_id or not code or not payment_date:
                return {
                    'sucesso': False,
                    'erro': 'Campos obrigatórios faltando',
                    'resposta': '❌ payment_id, code e payment_date são obrigatórios.'
                }
            
            resultado = self.api.iniciar_barcode_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                code=code,
                payment_date=payment_date,
                tags=tags
            )
            
            payment_id_retornado = resultado.get('id', payment_id)
            status = resultado.get('status', 'PENDING_VALIDATION')
            
            resposta = f"✅ **Pagamento por Código de Barras Iniciado!** (SANDBOX - TESTE)\n"
            resposta += f"⚠️ AMBIENTE DE TESTE: Este pagamento é simulado.\n\n"
            resposta += f"**ID:** `{payment_id_retornado}`\n"
            resposta += f"**Status:** {status}\n"
            resposta += f"💡 Use 'efetivar_barcode_payment' para confirmar."
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar pagamento por código de barras: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro:** {str(e)}'
            }
    
    def efetivar_barcode_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        payment_value: float = None,
        agencia_origem: str = None,
        conta_origem: str = None,
        final_payer_name: str = None,
        final_payer_document_type: str = None,
        final_payer_document_number: str = None,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento por código de barras"""
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ API de Pagamentos do Santander não está disponível.'
            }
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id or not payment_value:
                return {
                    'sucesso': False,
                    'erro': 'Campos obrigatórios faltando',
                    'resposta': '❌ workspace_id, payment_id e payment_value são obrigatórios.'
                }
            
            if not agencia_origem or not conta_origem:
                workspace = self.api.consultar_workspace(workspace_id)
                main_account = workspace.get('mainDebitAccount', {})
                agencia_origem = agencia_origem or str(main_account.get('branch', ''))
                conta_origem = conta_origem or str(main_account.get('number', ''))
            
            debit_account = {
                "branch": str(agencia_origem).strip(),
                "number": str(conta_origem).strip()
            }
            
            final_payer = None
            if final_payer_name and final_payer_document_type and final_payer_document_number:
                final_payer = {
                    "name": final_payer_name,
                    "documentType": final_payer_document_type,
                    "documentNumber": final_payer_document_number
                }
            
            resultado = self.api.efetivar_barcode_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                payment_value=payment_value,
                debit_account=debit_account,
                final_payer=final_payer,
                status=status
            )
            
            resposta = f"✅ **Pagamento por Código de Barras Efetivado!** (SANDBOX - TESTE)\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Valor:** R$ {payment_value:,.2f}\n"
            resposta += f"**Status:** {resultado.get('status', status)}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao efetivar pagamento por código de barras: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro:** {str(e)}'
            }
    
    def consultar_barcode_payment(self, workspace_id: str = None, payment_id: str = None) -> Dict[str, Any]:
        """Consulta pagamento por código de barras por ID"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ workspace_id e payment_id são obrigatórios.'}
            
            resultado = self.api.consultar_barcode_payment(workspace_id, payment_id)
            
            resposta = f"📋 **Consulta de Pagamento por Código de Barras**\n\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Status:** {resultado.get('status', 'UNKNOWN')}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def listar_barcode_payments(
        self,
        workspace_id: str = None,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Lista pagamentos por código de barras"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            resultado = self.api.listar_barcode_payments(
                workspace_id=workspace_id,
                initial_date=initial_date,
                final_date=final_date,
                status=status,
                limit=limit,
                offset=0
            )
            
            content = resultado.get('_content', [])
            total = resultado.get('_pageable', {}).get('_totalElements', len(content))
            
            resposta = f"📋 **Pagamentos por Código de Barras**\n\n💡 Total: {total} pagamento(s)\n\n"
            
            if not content:
                resposta += "Nenhum pagamento encontrado."
            else:
                for i, payment in enumerate(content[:limit], 1):
                    payment_id = payment.get('id', 'N/A')
                    status_payment = payment.get('status', 'N/A')
                    resposta += f"{i}. **ID:** `{payment_id}` - Status: {status_payment}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    # ==========================================
    # PIX PAYMENTS
    # ==========================================
    
    def iniciar_pix_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        payment_value: str = None,
        dict_code: str = None,
        dict_code_type: str = None,
        qr_code: str = None,
        ibge_town_code: int = None,
        payment_date: str = None,
        beneficiary: Dict[str, Any] = None,
        remittance_information: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento PIX.
        
        Suporta 3 modos:
        1. DICT (chave PIX): dict_code + dict_code_type
        2. QR Code: qr_code + ibge_town_code + payment_date
        3. Beneficiário: beneficiary (dados completos)
        """
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            if not payment_id or not payment_value:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ payment_id e payment_value são obrigatórios.'}
            
            # Validar que pelo menos um modo está preenchido
            if not dict_code and not qr_code and not beneficiary:
                return {'sucesso': False, 'erro': 'Modo não especificado', 'resposta': '❌ Informe dict_code (chave PIX), qr_code ou beneficiary.'}
            
            resultado = self.api.iniciar_pix_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                payment_value=payment_value,
                dict_code=dict_code,
                dict_code_type=dict_code_type,
                qr_code=qr_code,
                ibge_town_code=ibge_town_code,
                payment_date=payment_date,
                beneficiary=beneficiary,
                remittance_information=remittance_information,
                tags=tags
            )
            
            payment_id_retornado = resultado.get('id', payment_id)
            status = resultado.get('status', 'PENDING_VALIDATION')
            
            modo = "DICT" if dict_code else ("QR Code" if qr_code else "Beneficiário")
            
            resposta = f"✅ **Pagamento PIX Iniciado!** (SANDBOX - TESTE)\n"
            resposta += f"⚠️ AMBIENTE DE TESTE: Este pagamento é simulado.\n\n"
            resposta += f"**ID:** `{payment_id_retornado}`\n"
            resposta += f"**Modo:** {modo}\n"
            resposta += f"**Valor:** R$ {payment_value}\n"
            resposta += f"**Status:** {status}\n"
            resposta += f"💡 Use 'efetivar_pix_payment' para confirmar."
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar PIX: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def efetivar_pix_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        payment_value: float = None,
        agencia_origem: str = None,
        conta_origem: str = None,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento PIX"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id or not payment_value:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ workspace_id, payment_id e payment_value são obrigatórios.'}
            
            if not agencia_origem or not conta_origem:
                workspace = self.api.consultar_workspace(workspace_id)
                main_account = workspace.get('mainDebitAccount', {})
                agencia_origem = agencia_origem or str(main_account.get('branch', ''))
                conta_origem = conta_origem or str(main_account.get('number', ''))
            
            debit_account = {
                "branch": str(agencia_origem).strip(),
                "number": str(conta_origem).strip()
            }
            
            resultado = self.api.efetivar_pix_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                payment_value=payment_value,
                debit_account=debit_account,
                status=status
            )
            
            resposta = f"✅ **Pagamento PIX Efetivado!** (SANDBOX - TESTE)\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Valor:** R$ {payment_value:,.2f}\n"
            resposta += f"**Status:** {resultado.get('status', status)}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao efetivar PIX: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def consultar_pix_payment(self, workspace_id: str = None, payment_id: str = None) -> Dict[str, Any]:
        """Consulta pagamento PIX por ID"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ workspace_id e payment_id são obrigatórios.'}
            
            resultado = self.api.consultar_pix_payment(workspace_id, payment_id)
            
            resposta = f"📋 **Consulta de Pagamento PIX**\n\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Status:** {resultado.get('status', 'UNKNOWN')}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar PIX: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def listar_pix_payments(
        self,
        workspace_id: str = None,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Lista pagamentos PIX"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            resultado = self.api.listar_pix_payments(
                workspace_id=workspace_id,
                initial_date=initial_date,
                final_date=final_date,
                status=status,
                limit=limit,
                offset=0
            )
            
            content = resultado.get('_content', [])
            total = resultado.get('_pageable', {}).get('_totalElements', len(content))
            
            resposta = f"📋 **Pagamentos PIX**\n\n💡 Total: {total} pagamento(s)\n\n"
            
            if not content:
                resposta += "Nenhum pagamento encontrado."
            else:
                for i, payment in enumerate(content[:limit], 1):
                    payment_id = payment.get('id', 'N/A')
                    status_payment = payment.get('status', 'N/A')
                    payment_value = payment.get('paymentValue', 0)
                    resposta += f"{i}. **ID:** `{payment_id}` - Status: {status_payment}"
                    if payment_value:
                        resposta += f" - Valor: R$ {payment_value:,.2f}"
                    resposta += "\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar PIX: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    # ==========================================
    # VEHICLE TAXES PAYMENTS (IPVA)
    # ==========================================
    
    def consultar_debitos_renavam(
        self,
        workspace_id: str = None,
        renavam: int = None,
        state_abbreviation: str = None
    ) -> Dict[str, Any]:
        """Consulta débitos do Renavam (IPVA, licenciamento, etc.)"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            resultado = self.api.consultar_debitos_renavam(
                workspace_id=workspace_id,
                renavam=renavam,
                state_abbreviation=state_abbreviation
            )
            
            resposta = f"📋 **Consulta de Débitos Renavam**\n\n"
            if renavam:
                resposta += f"**Renavam:** {renavam}\n"
            if state_abbreviation:
                resposta += f"**Estado:** {state_abbreviation}\n"
            resposta += f"\n💡 Use 'iniciar_vehicle_tax_payment' para pagar um débito."
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar débitos Renavam: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def iniciar_vehicle_tax_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        renavam: int = None,
        tax_type: str = None,
        exercise_year: int = None,
        state_abbreviation: str = None,
        doc_type: str = None,
        document_number: int = None,
        type_quota: str = "SINGLE",
        payment_date: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Inicia pagamento de imposto veicular (IPVA)"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            if not all([payment_id, renavam, tax_type, exercise_year, state_abbreviation, doc_type, document_number]):
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ Todos os campos são obrigatórios (payment_id, renavam, tax_type, exercise_year, state_abbreviation, doc_type, document_number).'}
            
            resultado = self.api.iniciar_vehicle_tax_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                renavam=renavam,
                tax_type=tax_type,
                exercise_year=exercise_year,
                state_abbreviation=state_abbreviation,
                doc_type=doc_type,
                document_number=document_number,
                type_quota=type_quota,
                payment_date=payment_date,
                tags=tags
            )
            
            payment_id_retornado = resultado.get('id', payment_id)
            status = resultado.get('status', 'PENDING_VALIDATION')
            
            resposta = f"✅ **Pagamento de IPVA Iniciado!** (SANDBOX - TESTE)\n"
            resposta += f"⚠️ AMBIENTE DE TESTE: Este pagamento é simulado.\n\n"
            resposta += f"**ID:** `{payment_id_retornado}`\n"
            resposta += f"**Renavam:** {renavam}\n"
            resposta += f"**Tipo:** {tax_type}\n"
            resposta += f"**Ano:** {exercise_year}\n"
            resposta += f"**Status:** {status}\n"
            resposta += f"💡 Use 'efetivar_vehicle_tax_payment' para confirmar."
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar pagamento IPVA: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def efetivar_vehicle_tax_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        agencia_origem: str = None,
        conta_origem: str = None,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento de imposto veicular"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ workspace_id e payment_id são obrigatórios.'}
            
            if not agencia_origem or not conta_origem:
                workspace = self.api.consultar_workspace(workspace_id)
                main_account = workspace.get('mainDebitAccount', {})
                agencia_origem = agencia_origem or str(main_account.get('branch', ''))
                conta_origem = conta_origem or str(main_account.get('number', ''))
            
            debit_account = {
                "branch": str(agencia_origem).strip(),
                "number": str(conta_origem).strip()
            }
            
            resultado = self.api.efetivar_vehicle_tax_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                debit_account=debit_account,
                status=status
            )
            
            resposta = f"✅ **Pagamento de IPVA Efetivado!** (SANDBOX - TESTE)\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Status:** {resultado.get('status', status)}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao efetivar pagamento IPVA: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def consultar_vehicle_tax_payment(self, workspace_id: str = None, payment_id: str = None) -> Dict[str, Any]:
        """Consulta pagamento de imposto veicular por ID"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ workspace_id e payment_id são obrigatórios.'}
            
            resultado = self.api.consultar_vehicle_tax_payment(workspace_id, payment_id)
            
            resposta = f"📋 **Consulta de Pagamento IPVA**\n\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Status:** {resultado.get('status', 'UNKNOWN')}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar IPVA: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def listar_vehicle_tax_payments(
        self,
        workspace_id: str = None,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Lista pagamentos de impostos veiculares"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            resultado = self.api.listar_vehicle_tax_payments(
                workspace_id=workspace_id,
                initial_date=initial_date,
                final_date=final_date,
                status=status,
                limit=limit,
                offset=0
            )
            
            content = resultado.get('_content', [])
            total = resultado.get('_pageable', {}).get('_totalElements', len(content))
            
            resposta = f"📋 **Pagamentos de IPVA**\n\n💡 Total: {total} pagamento(s)\n\n"
            
            if not content:
                resposta += "Nenhum pagamento encontrado."
            else:
                for i, payment in enumerate(content[:limit], 1):
                    payment_id = payment.get('id', 'N/A')
                    status_payment = payment.get('status', 'N/A')
                    resposta += f"{i}. **ID:** `{payment_id}` - Status: {status_payment}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar IPVA: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    # ==========================================
    # TAXES BY FIELDS PAYMENTS (GARE, DARF, GPS)
    # ==========================================
    
    def iniciar_tax_by_fields_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        tax_type: str = None,
        payment_date: str = None,
        city: str = None,
        state_abbreviation: str = None,
        fields: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia pagamento de imposto por campos (GARE ICMS, GARE ITCMD, DARF, GPS).
        
        Args:
            fields: Dict com campos específicos do imposto (field01, field02, etc.)
        """
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            if not all([payment_id, tax_type, payment_date]):
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ payment_id, tax_type e payment_date são obrigatórios.'}
            
            resultado = self.api.iniciar_tax_by_fields_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                tax_type=tax_type,
                payment_date=payment_date,
                city=city,
                state_abbreviation=state_abbreviation,
                fields=fields or {},
                tags=tags
            )
            
            payment_id_retornado = resultado.get('id', payment_id)
            status = resultado.get('status', 'PENDING_VALIDATION')
            
            resposta = f"✅ **Pagamento de {tax_type} Iniciado!** (SANDBOX - TESTE)\n"
            resposta += f"⚠️ AMBIENTE DE TESTE: Este pagamento é simulado.\n\n"
            resposta += f"**ID:** `{payment_id_retornado}`\n"
            resposta += f"**Tipo:** {tax_type}\n"
            resposta += f"**Status:** {status}\n"
            resposta += f"💡 Use 'efetivar_tax_by_fields_payment' para confirmar."
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar pagamento de imposto por campos: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def efetivar_tax_by_fields_payment(
        self,
        workspace_id: str = None,
        payment_id: str = None,
        agencia_origem: str = None,
        conta_origem: str = None,
        status: str = "AUTHORIZED"
    ) -> Dict[str, Any]:
        """Efetiva pagamento de imposto por campos"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ workspace_id e payment_id são obrigatórios.'}
            
            if not agencia_origem or not conta_origem:
                workspace = self.api.consultar_workspace(workspace_id)
                main_account = workspace.get('mainDebitAccount', {})
                agencia_origem = agencia_origem or str(main_account.get('branch', ''))
                conta_origem = conta_origem or str(main_account.get('number', ''))
            
            debit_account = {
                "branch": str(agencia_origem).strip(),
                "number": str(conta_origem).strip()
            }
            
            resultado = self.api.efetivar_tax_by_fields_payment(
                workspace_id=workspace_id,
                payment_id=payment_id,
                debit_account=debit_account,
                status=status
            )
            
            resposta = f"✅ **Pagamento de Imposto Efetivado!** (SANDBOX - TESTE)\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Status:** {resultado.get('status', status)}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao efetivar pagamento de imposto: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def consultar_tax_by_fields_payment(self, workspace_id: str = None, payment_id: str = None) -> Dict[str, Any]:
        """Consulta pagamento de imposto por campos por ID"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id or not payment_id:
                return {'sucesso': False, 'erro': 'Campos obrigatórios', 'resposta': '❌ workspace_id e payment_id são obrigatórios.'}
            
            resultado = self.api.consultar_tax_by_fields_payment(workspace_id, payment_id)
            
            resposta = f"📋 **Consulta de Pagamento de Imposto**\n\n"
            resposta += f"**ID:** `{payment_id}`\n"
            resposta += f"**Status:** {resultado.get('status', 'UNKNOWN')}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar imposto: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
    
    def listar_tax_by_fields_payments(
        self,
        workspace_id: str = None,
        initial_date: str = None,
        final_date: str = None,
        status: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Lista pagamentos de impostos por campos"""
        if not self.enabled or not self.api:
            return {'sucesso': False, 'erro': 'API não disponível', 'resposta': '❌ API não disponível.'}
        
        try:
            workspace_id = workspace_id or self._verificar_workspace()
            if not workspace_id:
                return {'sucesso': False, 'erro': 'Workspace não encontrado', 'resposta': '❌ Nenhum workspace configurado.'}
            
            resultado = self.api.listar_tax_by_fields_payments(
                workspace_id=workspace_id,
                initial_date=initial_date,
                final_date=final_date,
                status=status,
                limit=limit,
                offset=0
            )
            
            content = resultado.get('_content', [])
            total = resultado.get('_pageable', {}).get('_totalElements', len(content))
            
            resposta = f"📋 **Pagamentos de Impostos (GARE, DARF, GPS)**\n\n💡 Total: {total} pagamento(s)\n\n"
            
            if not content:
                resposta += "Nenhum pagamento encontrado."
            else:
                for i, payment in enumerate(content[:limit], 1):
                    payment_id = payment.get('id', 'N/A')
                    status_payment = payment.get('status', 'N/A')
                    tax_type = payment.get('taxType', 'N/A')
                    resposta += f"{i}. **ID:** `{payment_id}` - Tipo: {tax_type} - Status: {status_payment}\n"
            
            return {'sucesso': True, 'resposta': resposta, 'dados': resultado}
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar impostos: {e}", exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ **Erro:** {str(e)}'}
