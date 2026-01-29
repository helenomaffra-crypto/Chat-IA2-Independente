"""
Serviço para integração com API do Santander Open Banking.

Wrapper para facilitar integração com o sistema mAIke.
Versão independente - não depende de diretório externo.
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Importar serviço de consulta CPF/CNPJ
try:
    from services.consulta_cpf_cnpj_service import ConsultaCpfCnpjService
    CPF_CNPJ_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Serviço de consulta CPF/CNPJ não disponível: {e}")
    CPF_CNPJ_SERVICE_AVAILABLE = False
    ConsultaCpfCnpjService = None

# ✅ VERSÃO INDEPENDENTE: Importar do módulo interno
try:
    from utils.santander_api import SantanderExtratoAPI, SantanderConfig
    SANTANDER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Não foi possível importar santander_api: {e}")
    SANTANDER_AVAILABLE = False
    SantanderExtratoAPI = None
    SantanderConfig = None


class SantanderService:
    """Serviço para integração com API do Santander."""
    
    def __init__(self):
        """Inicializa o serviço."""
        self.api: Optional[SantanderExtratoAPI] = None
        self.enabled = SANTANDER_AVAILABLE
        
        # Inicializar serviço de consulta CPF/CNPJ
        self.cpf_cnpj_service = None
        if CPF_CNPJ_SERVICE_AVAILABLE:
            try:
                self.cpf_cnpj_service = ConsultaCpfCnpjService()
                logger.info("✅ Serviço de consulta CPF/CNPJ inicializado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar serviço CPF/CNPJ: {e}")
        
        if not self.enabled:
            logger.warning("⚠️ API do Santander não disponível")
            return
        
        try:
            # ✅ VERSÃO INDEPENDENTE: Config carrega do .env do projeto atual
            # As variáveis SANTANDER_* devem estar no .env do Chat-IA-Independente
            config = SantanderConfig()
            
            # ✅ NOVO (13/01/2026): Log do certificado configurado para diagnóstico
            if config.cert_path:
                logger.info(f"🔍 [EXTRATO] Certificado configurado: {config.cert_path}")
            elif config.cert_file and config.key_file:
                logger.info(f"🔍 [EXTRATO] Certificados configurados: cert={config.cert_file}, key={config.key_file}")
            else:
                logger.warning(f"⚠️ [EXTRATO] Nenhum certificado configurado!")
            
            self.api = SantanderExtratoAPI(config, debug=False)
            logger.info("✅ SantanderService inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SantanderService: {e}", exc_info=True)
            self.enabled = False
    
    def listar_contas(self) -> Dict[str, Any]:
        """
        Lista todas as contas disponíveis.
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: List[Dict] (lista de contas)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API do Santander não está disponível.**\n\nVerifique se:\n- O diretório SANTANDER existe\n- As dependências estão instaladas\n- As credenciais estão configuradas no .env'
            }
        
        try:
            contas = self.api.listar_contas()
            
            if not contas or not contas.get('_content'):
                return {
                    'sucesso': False,
                    'erro': 'Nenhuma conta encontrada',
                    'resposta': '❌ **Nenhuma conta encontrada.**\n\nVerifique se você tem contas cadastradas no Santander Open Banking.'
                }
            
            # Formatar resposta
            resposta = "🏦 **Contas Disponíveis no Santander:**\n\n"
            for i, conta in enumerate(contas['_content'], 1):
                agencia = conta.get('branchCode', 'N/A')
                numero = conta.get('number', 'N/A')
                compe = conta.get('compeCode', '033')
                resposta += f"**{i}. Agência {agencia} / Conta {numero}**\n"
                resposta += f"   - Código COMPE: {compe}\n\n"
            
            resposta += f"💡 **Total:** {len(contas['_content'])} conta(s) disponível(is)\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': contas['_content']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar contas: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao listar contas:** {str(e)}\n\n💡 Verifique se:\n- As credenciais estão corretas no .env\n- O certificado mTLS está configurado\n- Você tem permissão para acessar as contas'
            }
    
    def consultar_extrato(
        self,
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        statement_id: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        dias: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Consulta extrato bancário.
        
        Args:
            agencia: Código da agência (4 dígitos)
            conta: Número da conta (12 dígitos)
            statement_id: ID da conta (formato AGENCIA.CONTA)
            data_inicio: Data inicial (YYYY-MM-DD)
            data_fim: Data final (YYYY-MM-DD)
            dias: Número de dias para trás (se não fornecer datas)
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: List[Dict] (lista de transações)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API do Santander não está disponível.**'
            }
        
        try:
            # Determinar datas
            if dias:
                data_fim = datetime.now()
                data_inicio = data_fim - timedelta(days=dias)
                data_inicio_str = data_inicio.strftime("%Y-%m-%d")
                data_fim_str = data_fim.strftime("%Y-%m-%d")
            elif data_inicio and data_fim:
                # Se ambas as datas são iguais, é extrato de um dia específico
                if data_inicio == data_fim:
                    logger.info(f"📅 Extrato de um dia específico: {data_inicio}")
                data_inicio_str = data_inicio
                data_fim_str = data_fim
            elif data_inicio:
                # Se forneceu apenas data_inicio, usar como data única
                data_inicio_str = data_inicio
                data_fim_str = data_inicio  # Mesma data para início e fim
                logger.info(f"📅 Extrato de um dia específico (apenas data_inicio): {data_inicio}")
            else:
                # Padrão: últimos 7 dias
                data_fim = datetime.now()
                data_inicio = data_fim - timedelta(days=7)
                data_inicio_str = data_inicio.strftime("%Y-%m-%d")
                data_fim_str = data_fim.strftime("%Y-%m-%d")
            
            # Buscar extrato completo (todas as páginas)
            extrato_completo = self.api.get_extrato_paginado(
                agencia=agencia,
                conta=conta,
                statement_id=statement_id,
                initial_date=data_inicio_str,
                final_date=data_fim_str,
                limit=50
            )
            
            if not extrato_completo:
                return {
                    'sucesso': True,
                    'resposta': f'📋 **Extrato Bancário**\n\n**Período:** {data_inicio_str} a {data_fim_str}\n\nℹ️ Nenhuma transação encontrada neste período.',
                    'dados': []
                }
            
            # Consultar saldo real da conta
            saldo_real = None
            try:
                # Se temos statement_id, usar como balance_id. Caso contrário, usar agencia/conta
                balance_id = statement_id if statement_id else None
                logger.info(f"🔍 Consultando saldo real: agencia={agencia}, conta={conta}, balance_id={balance_id}")
                resultado_saldo = self.api.get_saldo(
                    agencia=agencia,
                    conta=conta,
                    balance_id=balance_id
                )
                logger.info(f"✅ Saldo consultado com sucesso: {resultado_saldo}")
                if resultado_saldo:
                    saldo_real = {
                        'disponivel': float(resultado_saldo.get('availableAmount', 0) or 0),
                        'bloqueado': float(resultado_saldo.get('blockedAmount', 0) or 0),
                        'investido': float(resultado_saldo.get('automaticallyInvestedAmount', 0) or 0)
                    }
                    logger.info(f"💰 Saldo real extraído: disponivel={saldo_real['disponivel']}, bloqueado={saldo_real['bloqueado']}, investido={saldo_real['investido']}")
            except Exception as e:
                logger.error(f"❌ Erro ao consultar saldo real: {e}", exc_info=True)
            
            # Formatar resposta
            resposta = f"📋 **Extrato Bancário Santander**\n\n"
            # Se é um dia único, mostrar de forma diferente
            if data_inicio_str == data_fim_str:
                resposta += f"**Data:** {data_inicio_str}\n"
            else:
                resposta += f"**Período:** {data_inicio_str} a {data_fim_str}\n"
            resposta += f"**Total de transações:** {len(extrato_completo)}\n\n"
            
            # Mostrar saldo real se disponível
            if saldo_real:
                resposta += f"💰 **Saldo Real da Conta (Santander):**\n"
                resposta += f"• Disponível: R$ {saldo_real['disponivel']:,.2f}\n"
                resposta += f"• Bloqueado: R$ {saldo_real['bloqueado']:,.2f}\n"
                if saldo_real['investido'] > 0:
                    resposta += f"• Investido automaticamente: R$ {saldo_real['investido']:,.2f}\n"
                resposta += f"\n"
            
            # Calcular totais do período (apenas para referência)
            total_credito = sum(
                float(t.get('amount', 0) or 0)
                for t in extrato_completo
                if t.get('creditDebitType') == 'CREDITO'
            )
            total_debito = sum(
                float(t.get('amount', 0) or 0)
                for t in extrato_completo
                if t.get('creditDebitType') == 'DEBITO'
            )
            
            resposta += f"📊 **Movimentações do Período:**\n"
            resposta += f"• Créditos: R$ {total_credito:,.2f}\n"
            resposta += f"• Débitos: R$ {total_debito:,.2f}\n"
            resposta += f"• Saldo líquido do período: R$ {total_credito - total_debito:,.2f}\n\n"
            
            # Listar transações (até 50)
            resposta += "**Transações:**\n\n"
            # ✅ Aumentar limite de exibição para 50 se for um período curto (até 3 dias) ou se o total for pequeno
            # Caso contrário, manter 30 para não poluir demais o chat
            limite_exibicao = 50 if (not dias or dias <= 3) else 30
            
            for i, transacao in enumerate(extrato_completo[:limite_exibicao], 1):
                tipo = transacao.get('creditDebitType', 'N/A')
                nome = transacao.get('transactionName', 'N/A')
                valor = float(transacao.get('amount', 0) or 0)
                data = transacao.get('transactionDate', 'N/A')
                complemento = transacao.get('historicComplement', '')
                
                # ✅ Informações de contrapartida (se disponíveis)
                info_contrapartida = self._formatar_contrapartida_santander(transacao)
                
                sinal = '+' if tipo == 'CREDITO' else '-'
                is_debito = tipo == 'DEBITO'
                
                resposta += f"{i}. **{data}** - {nome}\n"
                
                # Adicionar informações de contrapartida se disponíveis
                if info_contrapartida:
                    resposta += f"   👤 {info_contrapartida}\n"
                
                if complemento:
                    resposta += f"   ℹ️ {complemento}\n"
                
                # ✅ Pagamentos (débitos) em vermelho
                valor_formatado = f"{sinal} R$ {valor:,.2f}"
                if is_debito:
                    valor_formatado = f'<span style="color: red;">{valor_formatado}</span>'
                
                resposta += f"   {valor_formatado}\n\n"
            
            if len(extrato_completo) > limite_exibicao:
                resposta += f"\n💡 Mostrando {limite_exibicao} de {len(extrato_completo)} transações. Use filtros de data para ver períodos específicos.\n"
            
            resultado = {
                'sucesso': True,
                'resposta': resposta,
                'dados': extrato_completo,
                'totais': {
                    'credito': total_credito,
                    'debito': total_debito,
                    'saldo_liquido': total_credito - total_debito
                }
            }
            
            # Adicionar saldo real se disponível
            if saldo_real:
                resultado['saldo_real'] = saldo_real
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar extrato: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao consultar extrato:** {str(e)}\n\n💡 Verifique se:\n- A agência e conta estão corretas\n- As datas estão no formato correto (YYYY-MM-DD)\n- Você tem permissão para acessar esta conta'
            }
    
    def consultar_saldo(
        self,
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        statement_id: Optional[str] = None,
        data_referencia: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta saldo da conta.
        
        Se data_referencia for fornecida, calcula o saldo retroativamente
        usando o saldo atual e subtraindo transações posteriores.
        
        Args:
            agencia: Código da agência (4 dígitos)
            conta: Número da conta (12 dígitos)
            statement_id: ID da conta (formato AGENCIA.CONTA)
            data_referencia: Data de referência no formato YYYY-MM-DD (opcional)
                           Se fornecida, calcula saldo histórico retroativamente
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: Dict (dados do saldo)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API do Santander não está disponível.**'
            }
        
        try:
            # Se temos statement_id, usar como balance_id. Caso contrário, usar agencia/conta
            balance_id = statement_id if statement_id else None
            saldo_atual = self.api.get_saldo(
                agencia=agencia,
                conta=conta,
                balance_id=balance_id
            )
            
            saldo_disponivel = float(saldo_atual.get('availableAmount', 0) or 0)
            saldo_bloqueado = float(saldo_atual.get('blockedAmount', 0) or 0)
            saldo_investido = float(saldo_atual.get('automaticallyInvestedAmount', 0) or 0)
            
            # Se data_referencia foi fornecida, calcular saldo histórico
            if data_referencia:
                try:
                    data_ref = datetime.strptime(data_referencia, "%Y-%m-%d").date()
                    data_hoje = datetime.now().date()
                    
                    if data_ref > data_hoje:
                        return {
                            'sucesso': False,
                            'erro': 'Data futura',
                            'resposta': f'❌ **Data futura não permitida.**\n\nA data de referência ({data_referencia}) não pode ser maior que hoje.'
                        }
                    
                    # Consultar extrato da data_referencia até hoje
                    extrato_futuro = self.api.get_extrato_paginado(
                        agencia=agencia,
                        conta=conta,
                        statement_id=statement_id,
                        initial_date=data_referencia,
                        final_date=data_hoje.strftime("%Y-%m-%d"),
                        limit=1000
                    )
                    
                    # Calcular diferença de transações após a data de referência
                    # Créditos aumentam o saldo, débitos diminuem
                    diferenca = 0
                    for transacao in extrato_futuro:
                        valor = float(transacao.get('amount', 0) or 0)
                        tipo = transacao.get('creditDebitType', '')
                        # Transações após a data de referência: créditos diminuem o saldo histórico, débitos aumentam
                        if tipo == 'CREDITO':
                            diferenca -= valor  # Se houve crédito depois, o saldo na data era menor
                        elif tipo == 'DEBITO':
                            diferenca += valor  # Se houve débito depois, o saldo na data era maior
                    
                    # Calcular saldo histórico
                    saldo_historico_disponivel = saldo_disponivel + diferenca
                    
                    # Formatar resposta com saldo histórico
                    resposta = f"💰 **Saldo da Conta Santander em {data_referencia}**\n\n"
                    resposta += f"**Saldo Disponível (calculado):** R$ {saldo_historico_disponivel:,.2f}\n"
                    resposta += f"**Saldo Atual (hoje):** R$ {saldo_disponivel:,.2f}\n"
                    resposta += f"**Diferença:** R$ {diferenca:,.2f}\n\n"
                    resposta += f"💡 *Saldo calculado retroativamente usando o saldo atual e as transações após {data_referencia}.*\n"
                    
                    return {
                        'sucesso': True,
                        'resposta': resposta,
                        'dados': {
                            'saldo_historico': {
                                'disponivel': saldo_historico_disponivel,
                                'data_referencia': data_referencia
                            },
                            'saldo_atual': {
                                'disponivel': saldo_disponivel,
                                'bloqueado': saldo_bloqueado,
                                'investido': saldo_investido
                            },
                            'diferenca': diferenca,
                            'transacoes_apos': len(extrato_futuro)
                        }
                    }
                except ValueError as e:
                    return {
                        'sucesso': False,
                        'erro': 'Data inválida',
                        'resposta': f'❌ **Data inválida:** {data_referencia}\n\nUse o formato YYYY-MM-DD (ex: 2026-01-05).'
                    }
                except Exception as e:
                    logger.error(f"❌ Erro ao calcular saldo histórico: {e}", exc_info=True)
                    # Se falhar, retornar saldo atual mesmo assim
                    logger.warning("⚠️ Retornando saldo atual devido a erro no cálculo histórico")
            
            # Formatar resposta com saldo atual
            resposta = "💰 **Saldo da Conta Santander**\n\n"
            resposta += f"**Disponível:** R$ {saldo_disponivel:,.2f}\n"
            resposta += f"**Bloqueado:** R$ {saldo_bloqueado:,.2f}\n"
            resposta += f"**Investido automaticamente:** R$ {saldo_investido:,.2f}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'disponivel': saldo_disponivel,
                    'bloqueado': saldo_bloqueado,
                    'investido': saldo_investido
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar saldo: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao consultar saldo:** {str(e)}'
            }
    
    def _formatar_contrapartida_santander(self, transacao: Dict[str, Any]) -> str:
        """
        Formata informações de contrapartida do Santander (origem/destino do dinheiro).
        
        Args:
            transacao: Dict com dados da transação do Santander
        
        Returns:
            String formatada com informações da contrapartida ou vazio se não disponível
        """
        # O Santander pode retornar informações de contrapartida em diferentes campos
        # Verificar campos comuns da API Open Banking
        cpf_cnpj = None
        nome_contrapartida = None
        banco_contrapartida = None
        agencia_contrapartida = None
        conta_contrapartida = None
        
        # Tentar extrair CPF/CNPJ de diferentes campos possíveis
        if 'counterpartDocument' in transacao:
            cpf_cnpj = transacao.get('counterpartDocument', '').strip()
        elif 'document' in transacao:
            cpf_cnpj = transacao.get('document', '').strip()
        elif 'cpfCnpj' in transacao:
            cpf_cnpj = transacao.get('cpfCnpj', '').strip()
        
        # Tentar extrair nome
        if 'counterpartName' in transacao:
            nome_contrapartida = transacao.get('counterpartName', '').strip()
        elif 'name' in transacao:
            nome_contrapartida = transacao.get('name', '').strip()
        
        # Tentar extrair dados bancários
        if 'counterpartBank' in transacao:
            banco_contrapartida = transacao.get('counterpartBank', {}).get('code')
            agencia_contrapartida = transacao.get('counterpartBank', {}).get('branch')
            conta_contrapartida = transacao.get('counterpartBank', {}).get('account')
        
        # Se não houver CPF/CNPJ, não há informações de contrapartida
        if not cpf_cnpj:
            return ""
        
        # ✅ Consultar nome via serviço genérico (se disponível e ainda não tiver nome)
        if self.cpf_cnpj_service and not nome_contrapartida:
            try:
                # Limpar formatação do CPF/CNPJ
                cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
                resultado_consulta = self.cpf_cnpj_service.consultar(cpf_cnpj_limpo)
                if resultado_consulta and resultado_consulta.get('nome'):
                    nome_contrapartida = resultado_consulta.get('nome')
                    logger.info(f"✅ Nome encontrado para {cpf_cnpj_limpo}: {nome_contrapartida}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao consultar nome de {cpf_cnpj}: {e}")
        
        # Formatar CPF/CNPJ
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
        if len(cpf_cnpj_limpo) == 11:  # CPF
            cpf_formatado = f"{cpf_cnpj_limpo[0:3]}.{cpf_cnpj_limpo[3:6]}.{cpf_cnpj_limpo[6:9]}-{cpf_cnpj_limpo[9:11]}"
            tipo_str = "CPF"
        elif len(cpf_cnpj_limpo) == 14:  # CNPJ
            cpf_formatado = f"{cpf_cnpj_limpo[0:2]}.{cpf_cnpj_limpo[2:5]}.{cpf_cnpj_limpo[5:8]}/{cpf_cnpj_limpo[8:12]}-{cpf_cnpj_limpo[12:14]}"
            tipo_str = "CNPJ"
        else:
            cpf_formatado = cpf_cnpj
            tipo_str = "CPF/CNPJ"
        
        # Montar informações
        partes = []
        
        # ✅ Nome (se encontrado)
        if nome_contrapartida:
            partes.append(f"**{nome_contrapartida}**")
        
        # CPF/CNPJ
        partes.append(f"{tipo_str}: {cpf_formatado}")
        
        # Dados bancários (se disponíveis)
        if banco_contrapartida:
            # Mapear códigos de banco conhecidos
            bancos = {
                '001': 'Banco do Brasil',
                '033': 'Santander',
                '104': 'Caixa Econômica',
                '237': 'Bradesco',
                '341': 'Itaú',
                '422': 'Safra',
                '748': 'Sicredi',
                '756': 'Sicoob'
            }
            banco_nome = bancos.get(str(banco_contrapartida).zfill(3), f'Banco {banco_contrapartida}')
            
            if agencia_contrapartida and conta_contrapartida:
                partes.append(f"{banco_nome} - Ag. {agencia_contrapartida} C/C {conta_contrapartida}")
            else:
                partes.append(f"{banco_nome}")
        
        return " | ".join(partes) if partes else ""

