"""
Agent para operações bancárias do Santander.

Gerencia consultas de extrato, saldo e contas.
"""
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from services.agents.base_agent import BaseAgent
from services.santander_service import SantanderService

logger = logging.getLogger(__name__)


def _normalizar_data(data_str: str) -> Optional[str]:
    """
    Normaliza data em vários formatos para YYYY-MM-DD.
    
    Suporta:
    - YYYY-MM-DD (ex: "2026-01-05")
    - DD/MM/YYYY (ex: "05/01/2026")
    - DD-MM-YYYY (ex: "05-01-2026")
    - "ontem", "hoje", "semana passada"
    - "dia X" (ex: "dia 5", "dia 10 de janeiro")
    """
    if not data_str:
        return None
    
    data_str = data_str.strip().lower()
    hoje = datetime.now().date()
    
    # Palavras-chave especiais
    if data_str == "hoje":
        return hoje.strftime("%Y-%m-%d")
    elif data_str == "ontem":
        return (hoje - timedelta(days=1)).strftime("%Y-%m-%d")
    elif "semana passada" in data_str or "semana anterior" in data_str:
        return (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
    elif "mês passado" in data_str or "mes passado" in data_str:
        # Aproximação: 30 dias atrás
        return (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Formato YYYY-MM-DD
    try:
        datetime.strptime(data_str, "%Y-%m-%d")
        return data_str
    except ValueError:
        pass
    
    # Formato DD/MM/YYYY
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    # Formato DD-MM-YYYY
    try:
        dt = datetime.strptime(data_str, "%d-%m-%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass
    
    # ✅ NOVO: Formato "dia X" ou "dia X de mês" (melhorado)
    # Padrões: "dia 03", "dia 3", "dia 03/01", "dia 03 de janeiro"
    match = re.search(r'dia\s+(\d{1,2})(?:[/-](\d{1,2}))?(?:\s+de\s+([a-zçã]+))?', data_str)
    if match:
        dia = int(match.group(1))
        mes = hoje.month
        ano = hoje.year
        
        # Se informou mês numérico (ex: dia 03/01)
        if match.group(2):
            mes = int(match.group(2))
        # Se informou mês por extenso (ex: dia 03 de janeiro)
        elif match.group(3):
            meses = {
                'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4,
                'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
                'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
            }
            mes_nome = match.group(3).lower()
            if mes_nome in meses:
                mes = meses[mes_nome]
        
        try:
            dt = datetime(ano, mes, dia)
            # Se a data resultante for no futuro (ex: hoje é dia 24 e pediu dia 25), 
            # e não especificou mês/ano, assume que é do mês passado
            if dt.date() > hoje and not match.group(2) and not match.group(3):
                if mes == 1:
                    dt = datetime(ano - 1, 12, dia)
                else:
                    dt = datetime(ano, mes - 1, dia)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    return None


class SantanderAgent(BaseAgent):
    """Agent para operações bancárias do Santander."""
    
    def __init__(self):
        """Inicializa o agent."""
        super().__init__()
        self.santander_service = SantanderService()  # Extratos
        # ✅ NOVO (12/01/2026): Serviço de Pagamentos (ISOLADO - Cenário 1)
        try:
            from services.santander_payments_service import SantanderPaymentsService
            self.payments_service = SantanderPaymentsService()
            logger.info("✅ SantanderPaymentsService inicializado no Agent")
        except ImportError as e:
            logger.warning(f"⚠️ SantanderPaymentsService não disponível: {e}")
            self.payments_service = None
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar SantanderPaymentsService: {e}")
            self.payments_service = None
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa uma tool relacionada ao Santander.
        
        Args:
            tool_name: Nome da tool
            arguments: Argumentos da tool
            context: Contexto adicional
        
        Returns:
            Dict com resultado da execução
        """
        handlers = {
            # Extratos (existentes)
            'listar_contas_santander': self._listar_contas,
            'consultar_extrato_santander': self._consultar_extrato,
            'consultar_saldo_santander': self._consultar_saldo,
            'gerar_pdf_extrato_santander': self._gerar_pdf_extrato,
            # ✅ NOVO (12/01/2026): Pagamentos (ISOLADO - Cenário 1)
            'listar_workspaces_santander': self._listar_workspaces,
            'criar_workspace_santander': self._criar_workspace,
            'iniciar_ted_santander': self._iniciar_ted,
            'efetivar_ted_santander': self._efetivar_ted,
            'consultar_ted_santander': self._consultar_ted,
            'listar_teds_santander': self._listar_teds,
            # ✅ NOVO (13/01/2026): Accounts and Taxes
            # Bank Slip Payments
            'iniciar_bank_slip_payment_santander': self._iniciar_bank_slip_payment,
            'efetivar_bank_slip_payment_santander': self._efetivar_bank_slip_payment,
            'consultar_bank_slip_payment_santander': self._consultar_bank_slip_payment,
            'listar_bank_slip_payments_santander': self._listar_bank_slip_payments,
            # Barcode Payments
            'iniciar_barcode_payment_santander': self._iniciar_barcode_payment,
            'efetivar_barcode_payment_santander': self._efetivar_barcode_payment,
            'consultar_barcode_payment_santander': self._consultar_barcode_payment,
            'listar_barcode_payments_santander': self._listar_barcode_payments,
            # Pix Payments
            'iniciar_pix_payment_santander': self._iniciar_pix_payment,
            'efetivar_pix_payment_santander': self._efetivar_pix_payment,
            'consultar_pix_payment_santander': self._consultar_pix_payment,
            'listar_pix_payments_santander': self._listar_pix_payments,
            # Vehicle Taxes Payments
            'consultar_debitos_renavam_santander': self._consultar_debitos_renavam,
            'iniciar_vehicle_tax_payment_santander': self._iniciar_vehicle_tax_payment,
            'efetivar_vehicle_tax_payment_santander': self._efetivar_vehicle_tax_payment,
            'consultar_vehicle_tax_payment_santander': self._consultar_vehicle_tax_payment,
            'listar_vehicle_tax_payments_santander': self._listar_vehicle_tax_payments,
            # Taxes by Fields Payments
            'iniciar_tax_by_fields_payment_santander': self._iniciar_tax_by_fields_payment,
            'efetivar_tax_by_fields_payment_santander': self._efetivar_tax_by_fields_payment,
            'consultar_tax_by_fields_payment_santander': self._consultar_tax_by_fields_payment,
            'listar_tax_by_fields_payments_santander': self._listar_tax_by_fields_payments,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada',
                'resposta': f'❌ Tool "{tool_name}" não disponível no SantanderAgent.'
            }
        
        try:
            return handler(arguments, context)
        except Exception as e:
            logger.error(f'Erro ao executar {tool_name}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao executar {tool_name}: {str(e)}'
            }
    
    def _listar_contas(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista contas disponíveis."""
        return self.santander_service.listar_contas()
    
    def _consultar_extrato(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta extrato bancário."""
        agencia = arguments.get('agencia')
        conta = arguments.get('conta')
        statement_id = arguments.get('statement_id')
        data_inicio = arguments.get('data_inicio')
        data_fim = arguments.get('data_fim')
        data = arguments.get('data')  # Aceitar também 'data' como alias para data única
        dias = arguments.get('dias')
        
        # Se não forneceu agência/conta/statement_id, listar contas e usar a primeira
        if not agencia and not conta and not statement_id:
            logger.info("🔍 Agência/conta não fornecidas. Listando contas disponíveis...")
            resultado_contas = self.santander_service.listar_contas()
            
            if not resultado_contas.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': 'Não foi possível listar contas',
                    'resposta': resultado_contas.get('resposta', '❌ Não foi possível listar contas disponíveis. Verifique a configuração do Santander.')
                }
            
            # O 'dados' já é a lista de contas diretamente
            contas = resultado_contas.get('dados', [])
            if not contas:
                return {
                    'sucesso': False,
                    'erro': 'Nenhuma conta encontrada',
                    'resposta': '❌ Nenhuma conta encontrada no Santander. Verifique se há contas vinculadas ao certificado digital.'
                }
            
            # Usar a primeira conta disponível
            primeira_conta = contas[0]
            agencia = primeira_conta.get('branchCode') or primeira_conta.get('branch') or primeira_conta.get('agencia')
            conta = primeira_conta.get('number') or primeira_conta.get('accountNumber') or primeira_conta.get('conta')
            
            if not agencia or not conta:
                return {
                    'sucesso': False,
                    'erro': 'Dados da conta incompletos',
                    'resposta': '❌ Não foi possível extrair agência e conta da primeira conta disponível.'
                }
            
            logger.info(f"✅ Usando primeira conta disponível: Agência {agencia}, Conta {conta}")
        
        # Se forneceu 'data' mas não 'data_inicio' nem 'data_fim', usar como data única
        if data and not data_inicio and not data_fim:
            data_normalizada = _normalizar_data(data)
            if data_normalizada:
                data_inicio = data_normalizada
                data_fim = data_normalizada  # Mesma data para início e fim = dia único
                logger.info(f"📅 Data única detectada: {data_normalizada}")
            else:
                logger.warning(f"⚠️ Data inválida ou não reconhecida: {data}")
        
        # Normalizar datas se fornecidas
        if data_inicio:
            data_normalizada = _normalizar_data(data_inicio)
            if data_normalizada:
                data_inicio = data_normalizada
        if data_fim:
            data_normalizada = _normalizar_data(data_fim)
            if data_normalizada:
                data_fim = data_normalizada
        
        # Se forneceu apenas data_inicio sem data_fim, usar como data única
        if data_inicio and not data_fim:
            data_fim = data_inicio  # Mesma data para início e fim = dia único
            logger.info(f"📅 Data única detectada (apenas data_inicio): {data_inicio}")
        
        # Se não forneceu datas nem dias, usar últimos 7 dias
        if not data_inicio and not data_fim and not dias:
            dias = 7
        
        resultado = self.santander_service.consultar_extrato(
            agencia=agencia,
            conta=conta,
            statement_id=statement_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias=dias
        )
        
        # ✅ NOVO: Salvar contexto quando extrato é consultado com sucesso
        if resultado.get('sucesso') and context:
            try:
                session_id = context.get('session_id')
                if session_id:
                    from services.context_service import salvar_contexto_sessao
                    
                    # Extrair dados do extrato para contexto
                    dados_extrato = resultado.get('dados', [])
                    total_transacoes = len(dados_extrato) if isinstance(dados_extrato, list) else 0
                    
                    # Salvar contexto de extrato bancário
                    salvar_contexto_sessao(
                        session_id=session_id,
                        tipo_contexto='ultima_consulta',
                        chave='extrato_bancario',
                        valor='extrato_santander',
                        dados_adicionais={
                            'banco': 'SANTANDER',
                            'agencia': agencia,
                            'conta': conta,
                            'statement_id': statement_id,
                            'data_inicio': data_inicio,
                            'data_fim': data_fim,
                            'dias': dias,
                            'total_transacoes': total_transacoes,
                            'timestamp': datetime.now().isoformat()
                        }
                    )
                    logger.debug(f"[CONTEXTO] Contexto de extrato Santander salvo: {total_transacoes} transações")
            except Exception as e:
                logger.debug(f"[CONTEXTO] Erro ao salvar contexto de extrato: {e}")
        
        return resultado
    
    def _consultar_saldo(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta saldo da conta."""
        agencia = arguments.get('agencia')
        conta = arguments.get('conta')
        statement_id = arguments.get('statement_id')
        data_referencia = arguments.get('data_referencia')
        data = arguments.get('data')  # Aceitar também 'data' como alias
        
        # Se forneceu 'data' mas não 'data_referencia', usar 'data'
        if data and not data_referencia:
            data_referencia = data
        
        # Normalizar data se fornecida
        if data_referencia:
            data_normalizada = _normalizar_data(data_referencia)
            if data_normalizada:
                data_referencia = data_normalizada
            else:
                logger.warning(f"⚠️ Data inválida ou não reconhecida: {data_referencia}")
                # Tentar usar como está (pode ser YYYY-MM-DD já)
        
        # Se não forneceu agência/conta/statement_id, listar contas e usar a primeira
        if not agencia and not conta and not statement_id:
            logger.info("🔍 Agência/conta não fornecidas. Listando contas disponíveis...")
            resultado_contas = self.santander_service.listar_contas()
            
            if not resultado_contas.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': 'Não foi possível listar contas',
                    'resposta': resultado_contas.get('resposta', '❌ Não foi possível listar contas disponíveis. Verifique a configuração do Santander.')
                }
            
            # O 'dados' já é a lista de contas diretamente
            contas = resultado_contas.get('dados', [])
            if not contas:
                return {
                    'sucesso': False,
                    'erro': 'Nenhuma conta encontrada',
                    'resposta': '❌ Nenhuma conta encontrada no Santander. Verifique se há contas vinculadas ao certificado digital.'
                }
            
            # Usar a primeira conta disponível
            primeira_conta = contas[0]
            agencia = primeira_conta.get('branchCode') or primeira_conta.get('branch') or primeira_conta.get('agencia')
            conta = primeira_conta.get('number') or primeira_conta.get('accountNumber') or primeira_conta.get('conta')
            
            if not agencia or not conta:
                return {
                    'sucesso': False,
                    'erro': 'Dados da conta incompletos',
                    'resposta': '❌ Não foi possível extrair agência e conta da primeira conta disponível.'
                }
            
            logger.info(f"✅ Usando primeira conta disponível: Agência {agencia}, Conta {conta}")
        
        return self.santander_service.consultar_saldo(
            agencia=agencia,
            conta=conta,
            statement_id=statement_id,
            data_referencia=data_referencia
        )
    
    def _gerar_pdf_extrato(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Gera PDF do extrato bancário do Santander no formato contábil.
        
        Args:
            arguments: {
                'agencia': str - Número da agência (opcional)
                'conta': str - Número da conta (opcional)
                'data_inicio': str - Data inicial (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
                'data_fim': str - Data final (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
                'dias': int - Número de dias para trás (opcional, padrão: 7)
            }
        """
        try:
            from services.extrato_bancario_pdf_service import ExtratoBancarioPdfService
            from datetime import datetime, timedelta
            
            agencia = arguments.get('agencia')
            conta = arguments.get('conta')
            statement_id = arguments.get('statement_id')
            data_inicio_str = arguments.get('data_inicio')
            data_fim_str = arguments.get('data_fim')
            dias = arguments.get('dias', 7)
            
            # Se não forneceu agência/conta/statement_id, listar contas e usar a primeira
            if not agencia and not conta and not statement_id:
                resultado_contas = self.santander_service.listar_contas()
                if not resultado_contas.get('sucesso'):
                    return resultado_contas
                
                contas = resultado_contas.get('dados', [])
                if not contas:
                    return {
                        'sucesso': False,
                        'erro': 'Nenhuma conta encontrada',
                        'resposta': '❌ Nenhuma conta encontrada no Santander.'
                    }
                
                primeira_conta = contas[0]
                agencia = primeira_conta.get('branchCode') or primeira_conta.get('branch')
                conta = primeira_conta.get('number') or primeira_conta.get('accountNumber')
            
            # Converter datas
            data_inicio = None
            data_fim = None
            
            if data_inicio_str:
                data_normalizada = _normalizar_data(data_inicio_str)
                if data_normalizada:
                    data_inicio = datetime.strptime(data_normalizada, "%Y-%m-%d")
            
            if data_fim_str:
                data_normalizada = _normalizar_data(data_fim_str)
                if data_normalizada:
                    data_fim = datetime.strptime(data_normalizada, "%Y-%m-%d")
            
            # Se não forneceu datas, usar dias
            if not data_inicio and not data_fim:
                hoje = datetime.now()
                data_fim = hoje.replace(hour=23, minute=59, second=59)
                data_inicio = (hoje - timedelta(days=dias)).replace(hour=0, minute=0, second=0)
            elif data_inicio and not data_fim:
                data_fim = data_inicio
            
            # Consultar extrato primeiro para obter lançamentos
            resultado_extrato = self.santander_service.consultar_extrato(
                agencia=agencia,
                conta=conta,
                statement_id=statement_id,
                data_inicio=data_inicio.strftime("%Y-%m-%d") if data_inicio else None,
                data_fim=data_fim.strftime("%Y-%m-%d") if data_fim else None,
                dias=dias if not data_inicio and not data_fim else None
            )
            
            if not resultado_extrato.get('sucesso'):
                return resultado_extrato
            
            # ✅ CORREÇÃO: dados_extrato pode ser uma lista diretamente ou um dict com 'transacoes'
            dados_extrato = resultado_extrato.get('dados', [])
            
            # Se dados_extrato é uma lista, usar diretamente
            if isinstance(dados_extrato, list):
                lancamentos = dados_extrato
            # Se é um dict, tentar pegar 'transacoes'
            elif isinstance(dados_extrato, dict):
                lancamentos = dados_extrato.get('transacoes', [])
            else:
                lancamentos = []
            
            if not lancamentos:
                return {
                    'sucesso': False,
                    'erro': 'NENHUM_LANCAMENTO',
                    'resposta': '❌ Não foi possível gerar o PDF: nenhum lançamento encontrado no período.'
                }
            
            # Gerar PDF
            pdf_service = ExtratoBancarioPdfService()
            resultado_pdf = pdf_service.gerar_pdf_extrato_santander(
                agencia=agencia or '',
                conta=conta or '',
                lancamentos=lancamentos,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            
            return resultado_pdf
            
        except Exception as e:
            logger.error(f'Erro ao gerar PDF do extrato Santander: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
            }
    
    # ==========================================
    # ✅ NOVO (12/01/2026): HANDLERS DE PAGAMENTOS (ISOLADO - Cenário 1)
    # ==========================================
    
    def _listar_workspaces(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista workspaces disponíveis."""
        if not self.payments_service:
            return {
                'sucesso': False,
                'erro': 'Serviço de pagamentos não disponível',
                'resposta': '❌ **Serviço de Pagamentos não está disponível.**\n\nVerifique se as credenciais SANTANDER_PAYMENTS_* estão configuradas no .env'
            }
        return self.payments_service.listar_workspaces()
    
    def _criar_workspace(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Cria um workspace para pagamentos."""
        if not self.payments_service:
            return {
                'sucesso': False,
                'erro': 'Serviço de pagamentos não disponível',
                'resposta': '❌ **Serviço de Pagamentos não está disponível.**'
            }
        
        tipo = arguments.get('tipo', 'PAYMENTS')
        agencia = arguments.get('agencia')
        conta = arguments.get('conta')
        description = arguments.get('description', '')
        pix_payments_active = arguments.get('pix_payments_active', False)
        bar_code_payments_active = arguments.get('bar_code_payments_active', False)
        bank_slip_payments_active = arguments.get('bank_slip_payments_active', False)
        bank_transfer_payments_active = arguments.get('bank_transfer_payments_active', False)
        
        return self.payments_service.criar_workspace(
            tipo=tipo,
            agencia=agencia,
            conta=conta,
            description=description,
            pix_payments_active=pix_payments_active,
            bar_code_payments_active=bar_code_payments_active,
            bank_slip_payments_active=bank_slip_payments_active,
            bank_transfer_payments_active=bank_transfer_payments_active
        )
    
    def _iniciar_ted(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inicia uma transferência TED."""
        if not self.payments_service:
            return {
                'sucesso': False,
                'erro': 'Serviço de pagamentos não disponível',
                'resposta': '❌ **Serviço de Pagamentos não está disponível.**'
            }
        
        return self.payments_service.iniciar_ted(
            workspace_id=arguments.get('workspace_id'),
            agencia_origem=arguments.get('agencia_origem'),
            conta_origem=arguments.get('conta_origem'),
            banco_destino=arguments.get('banco_destino'),
            agencia_destino=arguments.get('agencia_destino'),
            conta_destino=arguments.get('conta_destino'),
            valor=arguments.get('valor'),
            nome_destinatario=arguments.get('nome_destinatario'),
            cpf_cnpj_destinatario=arguments.get('cpf_cnpj_destinatario'),
            tipo_conta_destino=arguments.get('tipo_conta_destino', 'CONTA_CORRENTE'),
            ispb_destino=arguments.get('ispb_destino'),
            finalidade=arguments.get('finalidade')
        )
    
    def _efetivar_ted(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Efetiva uma TED iniciada."""
        if not self.payments_service:
            return {
                'sucesso': False,
                'erro': 'Serviço de pagamentos não disponível',
                'resposta': '❌ **Serviço de Pagamentos não está disponível.**'
            }
        
        return self.payments_service.efetivar_ted(
            workspace_id=arguments.get('workspace_id'),
            transfer_id=arguments.get('transfer_id'),
            agencia_origem=arguments.get('agencia_origem'),
            conta_origem=arguments.get('conta_origem')
        )
    
    def _consultar_ted(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta TED por ID."""
        if not self.payments_service:
            return {
                'sucesso': False,
                'erro': 'Serviço de pagamentos não disponível',
                'resposta': '❌ **Serviço de Pagamentos não está disponível.**'
            }
        
        return self.payments_service.consultar_ted(
            workspace_id=arguments.get('workspace_id'),
            transfer_id=arguments.get('transfer_id')
        )
    
    def _listar_teds(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista TEDs paginado (conciliação)."""
        if not self.payments_service:
            return {
                'sucesso': False,
                'erro': 'Serviço de pagamentos não disponível',
                'resposta': '❌ **Serviço de Pagamentos não está disponível.**'
            }
        
        return self.payments_service.listar_teds(
            workspace_id=arguments.get('workspace_id'),
            data_inicio=arguments.get('data_inicio'),
            data_fim=arguments.get('data_fim'),
            status=arguments.get('status'),
            limit=arguments.get('limit', 10)
        )
    
    # ==========================================
    # ✅ NOVO (13/01/2026): ACCOUNTS AND TAXES
    # Bank Slip Payments, Barcode Payments, Pix Payments,
    # Vehicle Taxes Payments, Taxes by Fields Payments
    # ==========================================
    
    # Bank Slip Payments (Boleto)
    def _processar_boleto_upload(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Processa upload de boleto e prepara pagamento."""
        logger.info(f"🔍 [BOLETO] _processar_boleto_upload chamado - file_path={arguments.get('file_path')}, context={context is not None}")
        from services.boleto_parser import BoletoParser
        from services.santander_service import SantanderService
        
        file_path = arguments.get('file_path')
        
        # ✅ CORREÇÃO: Priorizar session_id do context (vem do ToolExecutor)
        session_id = None
        if context:
            session_id = context.get('session_id')
        # Se não estiver no context, tentar arguments (fallback)
        if not session_id:
            session_id = arguments.get('session_id')
        
        logger.info(f"🔍 [BOLETO] session_id obtido: {session_id} (context={context is not None}, arguments tem session_id={arguments.get('session_id') is not None})")
        
        if not file_path:
            return {
                'sucesso': False,
                'erro': 'file_path obrigatório',
                'resposta': '❌ Caminho do arquivo é obrigatório.'
            }
        
        # 1. Extrair dados do boleto
        parser = BoletoParser()
        logger.info(f"🔍 [BOLETO] Iniciando extração de dados do boleto: {file_path}")
        dados = parser.extrair_dados_boleto(file_path)
        
        # ✅ NOVO: Log do método usado para extração
        metodo_extracao = dados.get('metodo', 'regex_pdfplumber')
        logger.info(f"🔍 [BOLETO] Método de extração usado: {metodo_extracao}")
        
        if not dados.get('sucesso'):
            return {
                'sucesso': False,
                'erro': dados.get('erro', 'Erro ao processar boleto'),
                'resposta': f"❌ **Erro ao processar boleto:** {dados.get('erro', 'Não foi possível extrair dados do PDF')}"
            }
        
        logger.info(f"✅ [BOLETO] Dados extraídos com sucesso: código={dados.get('codigo_barras', '')[:20]}..., valor={dados.get('valor', 0)}, método={metodo_extracao}")
        
        # 2. Consultar saldo (SEMPRE, independente do método de extração)
        logger.info(f"🔍 [BOLETO] Iniciando consulta de saldo (método extração: {metodo_extracao})...")
        import os
        santander_service = SantanderService()
        
        # ✅ CORREÇÃO: Obter agência e conta do .env ou listar contas automaticamente
        agencia = os.getenv('SANTANDER_AGENCIA')
        conta = os.getenv('SANTANDER_CONTA')
        
        # Se não tiver no .env, tentar listar contas e usar a primeira
        if not agencia or not conta:
            logger.info("🔍 Agência/conta não encontradas no .env. Listando contas disponíveis...")
            resultado_contas = santander_service.listar_contas()
            if resultado_contas.get('sucesso'):
                contas = resultado_contas.get('dados', [])
                if contas:
                    primeira_conta = contas[0]
                    agencia = primeira_conta.get('branchCode') or primeira_conta.get('branch') or primeira_conta.get('agencia')
                    conta = primeira_conta.get('number') or primeira_conta.get('accountNumber') or primeira_conta.get('conta')
                    logger.info(f"✅ Usando primeira conta disponível: Agência {agencia}, Conta {conta}")
        
        # Normalizar agência (4 dígitos) e conta (12 dígitos)
        if agencia:
            agencia = agencia.zfill(4) if agencia.isdigit() else agencia
        if conta:
            conta = conta.zfill(12) if conta.isdigit() else conta
        
        # Consultar saldo com agência e conta
        saldo_result = None
        if agencia and conta:
            logger.info(f"🔍 Consultando saldo: Agência {agencia}, Conta {conta}")
            saldo_result = santander_service.consultar_saldo(
                agencia=agencia,
                conta=conta
            )
        else:
            logger.warning("⚠️ Agência ou conta não disponíveis. Tentando consultar saldo sem parâmetros...")
            saldo_result = santander_service.consultar_saldo()
        
        saldo_disponivel = None
        if saldo_result and saldo_result.get('sucesso'):
            saldo_disponivel = saldo_result.get('dados', {}).get('disponivel', 0)
            logger.info(f"✅ [BOLETO] Saldo consultado com sucesso: R$ {saldo_disponivel:,.2f} (método extração: {metodo_extracao})")
        else:
            erro_msg = saldo_result.get('erro') if saldo_result else 'Erro desconhecido'
            logger.warning(f"⚠️ [BOLETO] Não foi possível consultar saldo: {erro_msg} (método extração: {metodo_extracao})")
        
        valor_boleto = dados.get('valor', 0)
        logger.info(f"🔍 [BOLETO] Valor do boleto: R$ {valor_boleto:,.2f}, Saldo disponível: {'R$ ' + str(saldo_disponivel) + ' (consultado)' if saldo_disponivel is not None else 'Não consultado'} (método: {metodo_extracao})")
        
        # 3. Preparar resposta
        resposta = f"📄 **Boleto Processado com Sucesso!**\n\n"
        resposta += f"**Código de Barras:** `{dados.get('codigo_barras')}`\n"
        resposta += f"**Valor:** R$ {valor_boleto:,.2f}\n"
        if dados.get('vencimento'):
            resposta += f"**Vencimento:** {dados.get('vencimento')}\n"
        if dados.get('beneficiario'):
            resposta += f"**Beneficiário:** {dados.get('beneficiario')}\n"
        
        # 4. Sempre tentar iniciar pagamento automaticamente (mesmo sem saldo, para validar)
        import uuid
        from datetime import datetime
        
        payment_id = str(uuid.uuid4())
        # ✅ CORREÇÃO: API do Santander não permite paymentDate posterior à data de hoje
        # Usar data de hoje ao invés da data de vencimento do boleto
        payment_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"🔍 [BOLETO] payment_date definido como hoje ({payment_date}) - vencimento do boleto era {dados.get('vencimento')}")
        pagamento_iniciado = False
        payment_id_retornado = None
        status_pagamento = None
        erro_pagamento = None
        
        if saldo_disponivel is not None:
            resposta += f"\n**Saldo Disponível:** R$ {saldo_disponivel:,.2f}\n"
            saldo_apos = saldo_disponivel - valor_boleto
            resposta += f"**Saldo Após Pagamento:** R$ {saldo_apos:,.2f}\n"
            
            if saldo_disponivel < valor_boleto:
                resposta += f"\n⚠️ **Saldo insuficiente!** Necessário: R$ {valor_boleto:,.2f}"
                # Mesmo com saldo insuficiente, tentar iniciar para validar o boleto
                erro_pagamento = "Saldo insuficiente"
            else:
                # ✅ Iniciar pagamento automaticamente se saldo suficiente
                resposta += f"\n💡 **Iniciando pagamento automaticamente...**\n"
        else:
            resposta += f"\n⚠️ Não foi possível consultar saldo. Tentando iniciar pagamento mesmo assim...\n"
        
        # Tentar iniciar pagamento
        logger.info(f"🔍 [BOLETO] Verificando payments_service: {self.payments_service is not None}")
        logger.info(f"🔍 [BOLETO] session_id disponível: {session_id is not None} (valor: {session_id})")
        if self.payments_service:
            logger.info(f"🔍 [BOLETO] Tentando iniciar pagamento: payment_id={payment_id}, code={dados.get('codigo_barras')[:20]}..., payment_date={payment_date}")
            try:
                resultado_inicio = self.payments_service.iniciar_bank_slip_payment(
                    payment_id=payment_id,
                    code=dados.get('codigo_barras'),
                    payment_date=payment_date
                )
                
                logger.info(f"🔍 [BOLETO] Resultado do início: sucesso={resultado_inicio.get('sucesso')}, erro={resultado_inicio.get('erro')}")
                
                if resultado_inicio.get('sucesso'):
                    payment_id_retornado = resultado_inicio.get('dados', {}).get('id', payment_id)
                    status_pagamento = resultado_inicio.get('dados', {}).get('status', 'PENDING_VALIDATION')
                    pagamento_iniciado = True
                    
                    resposta += f"\n✅ **Pagamento Iniciado com Sucesso!**\n"
                    resposta += f"**ID do Pagamento:** `{payment_id_retornado}`\n"
                    resposta += f"**Status:** {status_pagamento}\n\n"
                    resposta += f"💡 **Próximo passo:** Diga 'confirmar pagamento', 'efetivar boleto' ou 'continue o pagamento' para autorizar o pagamento de R$ {valor_boleto:,.2f}."
                    
                    logger.info(f"✅ Pagamento iniciado automaticamente: payment_id={payment_id_retornado}, status={status_pagamento}")
                    
                    # ✅ NOVO (13/01/2026): Salvar histórico de pagamento quando iniciado
                    try:
                        from db_manager import salvar_historico_pagamento
                        import os
                        
                        ambiente = 'SANDBOX' if os.getenv('SANTANDER_PAYMENTS_SANDBOX', 'true').lower() == 'true' else 'PRODUCAO'
                        
                        salvar_historico_pagamento(
                            payment_id=payment_id_retornado,
                            tipo_pagamento='BOLETO',
                            banco='SANTANDER',
                            ambiente=ambiente,
                            status=status_pagamento,
                            valor=valor_boleto,
                            codigo_barras=dados.get('codigo_barras'),
                            beneficiario=dados.get('beneficiario'),
                            vencimento=dados.get('vencimento'),
                            agencia_origem=None,  # Será preenchido na efetivação
                            conta_origem=None,  # Será preenchido na efetivação
                            saldo_disponivel_antes=saldo_disponivel,
                            saldo_apos_pagamento=saldo_disponivel - valor_boleto if saldo_disponivel else None,
                            workspace_id=None,  # Será preenchido na efetivação
                            payment_date=payment_date,
                            dados_completos=resultado_inicio.get('dados', {}),
                            observacoes="Pagamento iniciado automaticamente após processar boleto",
                            data_inicio=datetime.now()
                        )
                        logger.info(f"✅ Histórico de pagamento salvo ao iniciar: {payment_id_retornado}")
                    except Exception as e:
                        logger.error(f"❌ Erro ao salvar histórico de pagamento: {e}", exc_info=True)
                    
                    # ✅ NOVO: Salvar contexto do pagamento para uso posterior
                    logger.info(f"🔍 [BOLETO] Tentando salvar contexto: session_id={session_id}")
                    if session_id:
                        try:
                            from services.context_service import salvar_contexto_sessao
                            salvar_contexto_sessao(
                                session_id=session_id,
                                tipo_contexto='pagamento_boleto',
                                chave='payment_id',
                                valor=payment_id_retornado,
                                dados_adicionais={
                                    'payment_id': payment_id_retornado,
                                    'status': status_pagamento,
                                    'valor': valor_boleto,
                                    'codigo_barras': dados.get('codigo_barras'),
                                    'vencimento': dados.get('vencimento'),
                                    'beneficiario': dados.get('beneficiario'),
                                    'tipo_pagamento': 'bank_slip',
                                    'timestamp': datetime.now().isoformat()
                                }
                            )
                            logger.info(f"✅ Contexto de pagamento salvo: payment_id={payment_id_retornado}, session_id={session_id}")
                        except Exception as e:
                            logger.error(f"❌ Erro ao salvar contexto de pagamento: {e}", exc_info=True)
                    else:
                        logger.warning(f"⚠️ [BOLETO] session_id não disponível para salvar contexto de pagamento")
                else:
                    erro_pagamento = resultado_inicio.get('erro', 'Erro desconhecido ao iniciar pagamento')
                    resposta += f"\n⚠️ **Erro ao iniciar pagamento:** {erro_pagamento}\n"
                    resposta += f"💡 Você pode tentar manualmente usando 'iniciar_bank_slip_payment_santander'."
                    logger.error(f"❌ Erro ao iniciar pagamento: {erro_pagamento}")
            except Exception as e:
                erro_pagamento = str(e)
                logger.error(f"❌ Erro ao iniciar pagamento automaticamente: {e}", exc_info=True)
                resposta += f"\n⚠️ **Erro ao iniciar pagamento:** {erro_pagamento}\n"
                resposta += f"💡 Você pode tentar manualmente usando 'iniciar_bank_slip_payment_santander'."
        else:
            erro_pagamento = "Serviço de pagamentos não disponível"
            resposta += f"\n⚠️ **Serviço de pagamentos não disponível.**\n"
            resposta += f"💡 Verifique se as credenciais SANTANDER_PAYMENTS_* estão configuradas no .env"
            logger.warning(f"⚠️ {erro_pagamento}")
        
        # Retornar resultado
        resultado = {
            'sucesso': pagamento_iniciado,  # Só sucesso se pagamento foi iniciado
            'resposta': resposta,
            'dados': {
                **dados,
                'saldo_disponivel': saldo_disponivel,
                'saldo_apos_pagamento': saldo_disponivel - valor_boleto if saldo_disponivel else None,
                'payment_id': payment_id_retornado or payment_id,  # Sempre retornar payment_id
                'status': status_pagamento,
                'pagamento_iniciado': pagamento_iniciado
            },
            'acao': 'aprovar_pagamento' if pagamento_iniciado else None,
            'payment_id': payment_id_retornado or payment_id,  # ID para efetivação
            'pagamento_iniciado': pagamento_iniciado
        }
        
        if erro_pagamento:
            resultado['erro'] = erro_pagamento
        
        return resultado
    
    def _iniciar_bank_slip_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inicia pagamento de boleto."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.iniciar_bank_slip_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            code=arguments.get('code'),
            payment_date=arguments.get('payment_date'),
            tags=arguments.get('tags')
        )
    
    def _efetivar_bank_slip_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Efetiva pagamento de boleto."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        resultado = self.payments_service.efetivar_bank_slip_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            payment_value=arguments.get('payment_value'),
            agencia_origem=arguments.get('agencia_origem'),
            conta_origem=arguments.get('conta_origem'),
            final_payer_name=arguments.get('final_payer_name'),
            final_payer_document_type=arguments.get('final_payer_document_type'),
            final_payer_document_number=arguments.get('final_payer_document_number')
        )
        
        # ✅ NOVO (13/01/2026): Salvar histórico de pagamento após efetivar
        if resultado.get('sucesso'):
            try:
                from db_manager import salvar_historico_pagamento
                from datetime import datetime
                import os
                
                payment_id = arguments.get('payment_id')
                dados_completos = resultado.get('dados', {})
                status = dados_completos.get('status', 'PAYED')
                valor = arguments.get('payment_value') or dados_completos.get('paymentValue') or dados_completos.get('value', 0)
                
                # Determinar ambiente (SANDBOX ou PRODUCAO)
                ambiente = 'SANDBOX' if os.getenv('SANTANDER_PAYMENTS_SANDBOX', 'true').lower() == 'true' else 'PRODUCAO'
                
                # Buscar dados do pagamento iniciado (se existir no histórico)
                # Para obter dados do boleto (código de barras, beneficiário, etc.)
                conn = None
                try:
                    from db_manager import get_db_connection
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT codigo_barras, beneficiario, vencimento, saldo_disponivel_antes, 
                               saldo_apos_pagamento, workspace_id, payment_date, data_inicio
                        FROM historico_pagamentos 
                        WHERE payment_id = ?
                    ''', (payment_id,))
                    registro_existente = cursor.fetchone()
                    conn.close()
                    
                    if registro_existente:
                        codigo_barras, beneficiario, vencimento, saldo_antes, saldo_apos, workspace_id_existente, payment_date_existente, data_inicio_existente = registro_existente
                    else:
                        codigo_barras = beneficiario = vencimento = saldo_antes = saldo_apos = workspace_id_existente = payment_date_existente = data_inicio_existente = None
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar dados existentes do pagamento: {e}")
                    codigo_barras = beneficiario = vencimento = saldo_antes = saldo_apos = workspace_id_existente = payment_date_existente = data_inicio_existente = None
                
                # Salvar/atualizar histórico
                salvar_historico_pagamento(
                    payment_id=payment_id,
                    tipo_pagamento='BOLETO',
                    banco='SANTANDER',
                    ambiente=ambiente,
                    status=status,
                    valor=float(valor),
                    codigo_barras=codigo_barras,
                    beneficiario=beneficiario,
                    vencimento=vencimento,
                    agencia_origem=arguments.get('agencia_origem'),
                    conta_origem=arguments.get('conta_origem'),
                    saldo_disponivel_antes=float(saldo_antes) if saldo_antes else None,
                    saldo_apos_pagamento=float(saldo_apos) if saldo_apos else None,
                    workspace_id=arguments.get('workspace_id') or workspace_id_existente,
                    payment_date=payment_date_existente,
                    dados_completos=dados_completos,
                    observacoes=f"Efetivado via {arguments.get('final_payer_name', 'Sistema')}",
                    data_efetivacao=datetime.now()
                )
                logger.info(f"✅ Histórico de pagamento salvo após efetivação: {payment_id}")
            except Exception as e:
                logger.error(f"❌ Erro ao salvar histórico de pagamento: {e}", exc_info=True)
        
        return resultado
    
    def _consultar_bank_slip_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta pagamento de boleto por ID."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.consultar_bank_slip_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id')
        )
    
    def _listar_bank_slip_payments(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista pagamentos de boleto."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.listar_bank_slip_payments(
            workspace_id=arguments.get('workspace_id'),
            initial_date=arguments.get('data_inicio'),
            final_date=arguments.get('data_fim'),
            status=arguments.get('status'),
            limit=arguments.get('limit', 10)
        )
    
    # Barcode Payments (Código de Barras)
    def _iniciar_barcode_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inicia pagamento por código de barras."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.iniciar_barcode_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            code=arguments.get('code'),
            payment_date=arguments.get('payment_date'),
            tags=arguments.get('tags')
        )
    
    def _efetivar_barcode_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Efetiva pagamento por código de barras."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.efetivar_barcode_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            payment_value=arguments.get('payment_value'),
            agencia_origem=arguments.get('agencia_origem'),
            conta_origem=arguments.get('conta_origem'),
            final_payer_name=arguments.get('final_payer_name'),
            final_payer_document_type=arguments.get('final_payer_document_type'),
            final_payer_document_number=arguments.get('final_payer_document_number')
        )
    
    def _consultar_barcode_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta pagamento por código de barras."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.consultar_barcode_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id')
        )
    
    def _listar_barcode_payments(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista pagamentos por código de barras."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.listar_barcode_payments(
            workspace_id=arguments.get('workspace_id'),
            initial_date=arguments.get('data_inicio'),
            final_date=arguments.get('data_fim'),
            status=arguments.get('status'),
            limit=arguments.get('limit', 10)
        )
    
    # Pix Payments
    def _iniciar_pix_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inicia pagamento PIX."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.iniciar_pix_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            payment_value=arguments.get('payment_value'),
            dict_code=arguments.get('dict_code'),
            dict_code_type=arguments.get('dict_code_type'),
            qr_code=arguments.get('qr_code'),
            ibge_town_code=arguments.get('ibge_town_code'),
            payment_date=arguments.get('payment_date'),
            beneficiary=arguments.get('beneficiary'),
            remittance_information=arguments.get('remittance_information'),
            tags=arguments.get('tags')
        )
    
    def _efetivar_pix_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Efetiva pagamento PIX."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.efetivar_pix_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            payment_value=arguments.get('payment_value'),
            agencia_origem=arguments.get('agencia_origem'),
            conta_origem=arguments.get('conta_origem')
        )
    
    def _consultar_pix_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta pagamento PIX."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.consultar_pix_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id')
        )
    
    def _listar_pix_payments(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista pagamentos PIX."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.listar_pix_payments(
            workspace_id=arguments.get('workspace_id'),
            initial_date=arguments.get('data_inicio'),
            final_date=arguments.get('data_fim'),
            status=arguments.get('status'),
            limit=arguments.get('limit', 10)
        )
    
    # Vehicle Taxes Payments (IPVA)
    def _consultar_debitos_renavam(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta débitos do Renavam."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.consultar_debitos_renavam(
            workspace_id=arguments.get('workspace_id'),
            renavam=arguments.get('renavam'),
            state_abbreviation=arguments.get('state_abbreviation')
        )
    
    def _iniciar_vehicle_tax_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inicia pagamento de IPVA."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.iniciar_vehicle_tax_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            renavam=arguments.get('renavam'),
            tax_type=arguments.get('tax_type'),
            exercise_year=arguments.get('exercise_year'),
            state_abbreviation=arguments.get('state_abbreviation'),
            doc_type=arguments.get('doc_type'),
            document_number=arguments.get('document_number'),
            type_quota=arguments.get('type_quota', 'SINGLE'),
            payment_date=arguments.get('payment_date'),
            tags=arguments.get('tags')
        )
    
    def _efetivar_vehicle_tax_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Efetiva pagamento de IPVA."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.efetivar_vehicle_tax_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            agencia_origem=arguments.get('agencia_origem'),
            conta_origem=arguments.get('conta_origem')
        )
    
    def _consultar_vehicle_tax_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta pagamento de IPVA."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.consultar_vehicle_tax_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id')
        )
    
    def _listar_vehicle_tax_payments(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista pagamentos de IPVA."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.listar_vehicle_tax_payments(
            workspace_id=arguments.get('workspace_id'),
            initial_date=arguments.get('data_inicio'),
            final_date=arguments.get('data_fim'),
            status=arguments.get('status'),
            limit=arguments.get('limit', 10)
        )
    
    # Taxes by Fields Payments (GARE, DARF, GPS)
    def _iniciar_tax_by_fields_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inicia pagamento de imposto por campos."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.iniciar_tax_by_fields_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            tax_type=arguments.get('tax_type'),
            payment_date=arguments.get('payment_date'),
            city=arguments.get('city'),
            state_abbreviation=arguments.get('state_abbreviation'),
            fields=arguments.get('fields'),
            tags=arguments.get('tags')
        )
    
    def _efetivar_tax_by_fields_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Efetiva pagamento de imposto por campos."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.efetivar_tax_by_fields_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id'),
            agencia_origem=arguments.get('agencia_origem'),
            conta_origem=arguments.get('conta_origem')
        )
    
    def _consultar_tax_by_fields_payment(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Consulta pagamento de imposto por campos."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.consultar_tax_by_fields_payment(
            workspace_id=arguments.get('workspace_id'),
            payment_id=arguments.get('payment_id')
        )
    
    def _listar_tax_by_fields_payments(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista pagamentos de impostos por campos."""
        if not self.payments_service:
            return {'sucesso': False, 'erro': 'Serviço não disponível', 'resposta': '❌ Serviço de Pagamentos não está disponível.'}
        
        return self.payments_service.listar_tax_by_fields_payments(
            workspace_id=arguments.get('workspace_id'),
            initial_date=arguments.get('data_inicio'),
            final_date=arguments.get('data_fim'),
            status=arguments.get('status'),
            limit=arguments.get('limit', 10)
        )

