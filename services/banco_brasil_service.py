"""
Serviço para integração com API de Extratos do Banco do Brasil.

Wrapper para facilitar integração com o sistema mAIke.
Baseado na documentação oficial: https://developers.bb.com.br
"""
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)

# Importar serviço de consulta CPF/CNPJ
try:
    from services.consulta_cpf_cnpj_service import ConsultaCpfCnpjService
    CPF_CNPJ_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Serviço de consulta CPF/CNPJ não disponível: {e}")
    CPF_CNPJ_SERVICE_AVAILABLE = False
    ConsultaCpfCnpjService = None

# Importar do módulo interno
try:
    from utils.banco_brasil_api import BancoBrasilExtratoAPI, BancoBrasilConfig
    BB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Não foi possível importar banco_brasil_api: {e}")
    BB_AVAILABLE = False
    BancoBrasilExtratoAPI = None
    BancoBrasilConfig = None


class BancoBrasilService:
    """Serviço para integração com API de Extratos do Banco do Brasil."""
    
    def __init__(self):
        """Inicializa o serviço."""
        self.api: Optional[BancoBrasilExtratoAPI] = None
        self.enabled = BB_AVAILABLE
        
        # Inicializar serviço de consulta CPF/CNPJ
        self.cpf_cnpj_service = None
        if CPF_CNPJ_SERVICE_AVAILABLE:
            try:
                self.cpf_cnpj_service = ConsultaCpfCnpjService()
                logger.info("✅ Serviço de consulta CPF/CNPJ inicializado")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar serviço CPF/CNPJ: {e}")
        
        if not self.enabled:
            logger.warning("⚠️ API do Banco do Brasil não disponível")
            return
        
        try:
            # ✅ O .env já é carregado automaticamente no banco_brasil_api.py
            # Mas vamos garantir que está carregado aqui também (caso seja chamado antes)
            # O utils/banco_brasil_api.py já carrega o .env na importação, então não precisa fazer nada aqui
            
            config = BancoBrasilConfig()
            
            # Validar se credenciais estão configuradas
            if not config.client_id or not config.client_secret or not config.gw_dev_app_key:
                logger.warning("⚠️ Credenciais do Banco do Brasil não configuradas no .env")
                logger.warning("⚠️ Configure: BB_CLIENT_ID, BB_CLIENT_SECRET, BB_DEV_APP_KEY")
                logger.warning("⚠️ Verifique se o arquivo .env existe e está na raiz do projeto")
                # ✅ Debug: verificar se variáveis estão no ambiente (apenas se logging estiver em DEBUG)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"   Variáveis no os.environ:")
                    logger.debug(f"   BB_CLIENT_ID: {'presente' if 'BB_CLIENT_ID' in os.environ else 'ausente'}")
                    logger.debug(f"   BB_CLIENT_SECRET: {'presente' if 'BB_CLIENT_SECRET' in os.environ else 'ausente'}")
                    logger.debug(f"   BB_DEV_APP_KEY: {'presente' if 'BB_DEV_APP_KEY' in os.environ else 'ausente'}")
                self.enabled = False
                return
            
            self.api = BancoBrasilExtratoAPI(config, debug=True)  # Ativar debug para ver logs
            logger.info("✅ BancoBrasilService inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar BancoBrasilService: {e}", exc_info=True)
            self.enabled = False
    
    def consultar_extrato(
        self,
        agencia: str,
        conta: str,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Consulta extrato de conta corrente.
        
        Args:
            agencia: Número da agência (sem dígito verificador)
            conta: Número da conta (sem dígito verificador)
            data_inicio: Data inicial (opcional)
            data_fim: Data final (opcional)
        
        Returns:
            Dict com resultado contendo:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: Dict (dados do extrato)
            - erro: str (se houver)
        """
        if not self.enabled or not self.api:
            return {
                'sucesso': False,
                'erro': 'API não disponível',
                'resposta': '❌ **API do Banco do Brasil não está disponível.**\n\nVerifique se:\n- As dependências estão instaladas\n- As credenciais estão configuradas no .env'
            }
        
        try:
            # Se apenas data_inicio fornecida, usar como data_fim também (extrato de um dia)
            if data_inicio and not data_fim:
                data_fim = data_inicio
            
            # Se nenhuma data fornecida, usar últimos 30 dias (padrão da API)
            if not data_inicio and not data_fim:
                # ✅ IMPORTANTE: Usar data de hoje como data_fim para garantir que inclui todas as transações até hoje
                # A API do BB pode ter delay na disponibilização, então usar hoje como data_fim é seguro
                hoje = datetime.now()
                data_fim = hoje.replace(hour=23, minute=59, second=59)
                data_inicio = (hoje - timedelta(days=30)).replace(hour=0, minute=0, second=0)
                logger.info(f"📅 Período padrão (últimos 30 dias): {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
            
            # Log das datas sendo consultadas
            logger.info(f"📅 Consultando extrato BB - Agência: {agencia}, Conta: {conta}")
            logger.info(f"📅 Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
            
            # Consultar extrato completo (todas as páginas)
            lancamentos = self.api.consultar_extrato_periodo(
                agencia=agencia,
                conta=conta,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            
            # Log do resultado
            if lancamentos:
                # Verificar datas dos lançamentos
                datas_lancamentos = [lanc.get('dataLancamento', 0) for lanc in lancamentos if lanc.get('dataLancamento')]
                if datas_lancamentos:
                    data_min = min(datas_lancamentos)
                    data_max = max(datas_lancamentos)
                    logger.info(f"📅 Lançamentos encontrados: {len(lancamentos)} transações")
                    logger.info(f"📅 Data mais antiga: {self._formatar_data_bb(data_min)}")
                    logger.info(f"📅 Data mais recente: {self._formatar_data_bb(data_max)}")
            else:
                logger.warning(f"⚠️ Nenhum lançamento encontrado no período")
            
            if not lancamentos:
                return {
                    'sucesso': True,
                    'resposta': f'📋 **Extrato Banco do Brasil**\n\n**Agência:** {agencia}\n**Conta:** {conta}\n\n**Período:** {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}\n\n**Total de transações:** 0\n\nNenhuma transação encontrada no período.',
                    'dados': {
                        'agencia': agencia,
                        'conta': conta,
                        'data_inicio': data_inicio.strftime("%Y-%m-%d"),
                        'data_fim': data_fim.strftime("%Y-%m-%d"),
                        'lancamentos': []
                    }
                }
            
            # ✅ Ordenar transações por data (mais recente primeiro - do presente para o passado)
            # dataLancamento vem no formato DDMMAAAA (inteiro), precisa converter para YYYYMMDD para ordenar corretamente
            def converter_data_para_ordenacao(data_int: int) -> int:
                """Converte DDMMAAAA para YYYYMMDD para ordenação correta"""
                if not data_int or data_int == 0:
                    return 0
                data_str = str(data_int).zfill(8)  # Garantir 8 dígitos
                dia = data_str[0:2]
                mes = data_str[2:4]
                ano = data_str[4:8]
                # Retornar como YYYYMMDD para ordenação numérica correta
                return int(f"{ano}{mes}{dia}")
            
            lancamentos_ordenados = sorted(
                lancamentos,
                key=lambda x: converter_data_para_ordenacao(x.get('dataLancamento', 0)),
                reverse=True  # Mais recente primeiro (do presente para o passado)
            )

            # ✅ Saldo do dia: BB retorna como lançamento informativo ("S A L D O", "SALDO DO DIA", etc.)
            # Precisamos extrair esse valor e também evitar que ele contamine os totais de crédito/débito.
            def _eh_linha_saldo(descricao_raw: Any) -> bool:
                desc = (str(descricao_raw or "")).strip().upper()
                if not desc:
                    return False
                desc_norm = re.sub(r"\s+", "", desc)
                # Exemplos vistos:
                # - "S A L D O"
                # - "SALDO DO DIA"
                # - "SALDO ANTERIOR"
                if desc_norm == "SALDO":
                    return True
                if "SALDODODIA" in desc_norm:
                    return True
                if "SALDOANTERIOR" in desc_norm:
                    return True
                return False

            saldo_atual = None
            saldo_atual_data = None
            for lanc in lancamentos_ordenados:
                if _eh_linha_saldo(lanc.get("textoDescricaoHistorico")):
                    try:
                        saldo_atual = float(lanc.get("valorLancamento", 0) or 0)
                        saldo_atual_data = lanc.get("dataLancamento")
                        break  # primeira ocorrência = mais recente
                    except Exception:
                        continue
            
            # Calcular totais
            creditos = sum(
                lanc.get('valorLancamento', 0) 
                for lanc in lancamentos_ordenados 
                if lanc.get('indicadorSinalLancamento') == 'C'
                and not _eh_linha_saldo(lanc.get("textoDescricaoHistorico"))
            )
            debitos = sum(
                lanc.get('valorLancamento', 0) 
                for lanc in lancamentos_ordenados 
                if lanc.get('indicadorSinalLancamento') == 'D'
                and not _eh_linha_saldo(lanc.get("textoDescricaoHistorico"))
            )
            saldo_liquido = creditos - debitos
            
            # Formatar resposta
            if data_inicio == data_fim:
                periodo_str = f"**Data:** {data_inicio.strftime('%d/%m/%Y')}"
            else:
                periodo_str = f"**Período:** {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
            
            resposta = f"📋 **Extrato Bancário Banco do Brasil**\n\n"
            resposta += f"**Agência:** {agencia}\n"
            resposta += f"**Conta:** {conta}\n\n"
            # ✅ NOVO (21/01/2026): Mostrar saldo da Conta Corrente no topo (como no AFRMM)
            # O BB retorna o saldo como um lançamento informativo ("S A L D O"/"SALDO DO DIA").
            # Aqui exibimos esse valor antes do período para o usuário bater rapidamente.
            if saldo_atual is not None:
                data_saldo_fmt = self._formatar_data_bb(saldo_atual_data) if saldo_atual_data else None
                if data_saldo_fmt and data_saldo_fmt != "N/A":
                    resposta += f"💰 **Saldo atual (CC):** R$ {saldo_atual:,.2f} *(em {data_saldo_fmt})*\n\n"
                else:
                    resposta += f"💰 **Saldo atual (CC):** R$ {saldo_atual:,.2f}\n\n"
            else:
                resposta += "💰 **Saldo atual (CC):** *(indisponível no extrato retornado)*\n\n"
            resposta += f"{periodo_str}\n"
            # Total exibido exclui linhas informativas de saldo
            total_exibivel = len([l for l in lancamentos_ordenados if not _eh_linha_saldo(l.get('textoDescricaoHistorico'))])
            resposta += f"**Total de transações:** {total_exibivel}\n\n"
            resposta += f"📊 **Movimentações do Período:**\n"
            resposta += f"• Créditos: R$ {creditos:,.2f}\n"
            resposta += f"• Débitos: R$ {debitos:,.2f}\n"
            resposta += f"• Saldo líquido do período: R$ {saldo_liquido:,.2f}\n\n"
            
            # ✅ Limitar consultas de CPF/CNPJ para evitar rate limiting
            # ReceitaWS permite apenas 3 consultas por minuto (API gratuita)
            # Vamos consultar apenas os primeiros 3 CNPJs únicos para não exceder o limite
            cnpjs_consultados = set()
            limite_consultas = 3  # Limite seguro para não exceder rate limit (3 consultas/minuto)
            
            # Listar transações (limitar a 50 primeiras, já ordenadas da mais recente para a mais antiga)
            resposta += f"**Transações:** (mais recentes primeiro - do presente para o passado)\n"
            lancamentos_exibiveis = [l for l in lancamentos_ordenados if not _eh_linha_saldo(l.get('textoDescricaoHistorico'))]
            
            # ✅ Aumentar limite de exibição para 50 se for um período curto (até 3 dias) ou se o total for pequeno
            # Caso contrário, manter 30 para não poluir demais o chat
            limite_exibicao = 50 if (not data_inicio or not data_fim or (data_fim - data_inicio).days <= 3) else 30
            
            for i, lanc in enumerate(lancamentos_exibiveis[:limite_exibicao], 1):
                data_lanc = self._formatar_data_bb(lanc.get('dataLancamento', 0))
                descricao = lanc.get('textoDescricaoHistorico', 'Sem descrição')
                valor = lanc.get('valorLancamento', 0)
                sinal = lanc.get('indicadorSinalLancamento', '')
                
                sinal_str = "+" if sinal == 'C' else "-"
                is_debito = sinal == 'D'
                
                # ✅ Informações de contrapartida (origem/destino do dinheiro)
                # Verificar se já consultamos muitos CNPJs para evitar rate limiting
                cpf_cnpj_raw = lanc.get('numeroCpfCnpjContrapartida', '')
                if cpf_cnpj_raw:
                    cpf_cnpj_limpo = ''.join(filter(str.isdigit, str(cpf_cnpj_raw)))
                    # Se já consultamos muitos CNPJs únicos, desabilitar consulta temporariamente
                    if len(cnpjs_consultados) >= limite_consultas and cpf_cnpj_limpo not in cnpjs_consultados:
                        # Desabilitar serviço temporariamente para esta transação
                        cpf_cnpj_service_backup = self.cpf_cnpj_service
                        self.cpf_cnpj_service = None
                        info_contrapartida = self._formatar_contrapartida(lanc)
                        self.cpf_cnpj_service = cpf_cnpj_service_backup
                    else:
                        info_contrapartida = self._formatar_contrapartida(lanc)
                        if cpf_cnpj_limpo and len(cpf_cnpj_limpo) == 14:  # CNPJ
                            cnpjs_consultados.add(cpf_cnpj_limpo)
                else:
                    info_contrapartida = self._formatar_contrapartida(lanc)
                
                # ✅ Converter para string antes de strip() (pode vir como int)
                info_complementar_raw = lanc.get('textoInformacaoComplementar', '')
                info_complementar = str(info_complementar_raw).strip() if info_complementar_raw else ''
                
                # Montar linha principal com cor vermelha para débitos
                valor_formatado = f"{sinal_str} R$ {valor:,.2f}"
                if is_debito:
                    # ✅ Pagamentos (débitos) em vermelho
                    valor_formatado = f'<span style="color: red;">{valor_formatado}</span>'
                
                linha = f"{i}. {data_lanc} - {descricao} {valor_formatado}"
                
                # Adicionar informações de contrapartida se disponíveis
                if info_contrapartida:
                    linha += f"\n   👤 {info_contrapartida}"
                
                # Adicionar informações complementares se disponíveis
                if info_complementar:
                    linha += f"\n   ℹ️ {info_complementar}"
                
                resposta += linha + "\n"
            
            # Aviso sobre limite de consultas
            if len(cnpjs_consultados) >= limite_consultas:
                resposta += f"\n💡 *Nota: Nomes de empresas consultados apenas para as primeiras {limite_consultas} empresas únicas (limite da API gratuita ReceitaWS: 3 consultas/minuto)*\n"
            
            if len(lancamentos_exibiveis) > limite_exibicao:
                resposta += f"\n💡 Mostrando {limite_exibicao} de {len(lancamentos_exibiveis)} transações (mais recentes primeiro). Use filtros de data para ver períodos específicos."
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'agencia': agencia,
                    'conta': conta,
                    'data_inicio': data_inicio.strftime("%Y-%m-%d"),
                    'data_fim': data_fim.strftime("%Y-%m-%d"),
                    'total_transacoes': len(lancamentos_exibiveis),
                    'creditos': creditos,
                    'debitos': debitos,
                    'saldo_liquido': saldo_liquido,
                    'saldo_atual': saldo_atual,
                    'saldo_atual_data': saldo_atual_data,
                    # Mantemos a lista completa (inclui linhas informativas) para usos internos/diagnóstico
                    'lancamentos': lancamentos_ordenados  # Ordenadas da mais recente para a mais antiga (do presente para o passado)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao consultar extrato BB: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao consultar extrato:** {str(e)}\n\n💡 Verifique se:\n- A agência e conta estão corretas\n- As datas estão no formato correto\n- Você tem permissão para acessar esta conta'
            }
    
    def _formatar_data_bb(self, data_int: int) -> str:
        """
        Formata data do BB (DDMMAAAA) para DD/MM/YYYY.
        
        Args:
            data_int: Data no formato DDMMAAAA (ex: 11112022)
        
        Returns:
            Data formatada (ex: "11/11/2022")
        """
        if not data_int or data_int == 0:
            return "N/A"
        
        try:
            data_str = str(data_int).zfill(8)
            dia = data_str[0:2]
            mes = data_str[2:4]
            ano = data_str[4:8]
            return f"{dia}/{mes}/{ano}"
        except:
            return str(data_int)
    
    def _formatar_contrapartida(self, lancamento: Dict[str, Any]) -> str:
        """
        Formata informações de contrapartida (origem/destino do dinheiro).
        
        Args:
            lancamento: Dict com dados do lançamento
        
        Returns:
            String formatada com informações da contrapartida ou vazio se não disponível
        """
        # ✅ Converter para string antes de strip() (API pode retornar como int)
        cpf_cnpj_raw = lancamento.get('numeroCpfCnpjContrapartida', '')
        cpf_cnpj = str(cpf_cnpj_raw).strip() if cpf_cnpj_raw else ''
        
        tipo_pessoa_raw = lancamento.get('indicadorTipoPessoaContrapartida', '')
        tipo_pessoa = str(tipo_pessoa_raw).strip() if tipo_pessoa_raw else ''
        
        codigo_banco = lancamento.get('codigoBancoContrapartida', '')
        agencia = lancamento.get('codigoAgenciaContrapartida', '')
        conta = lancamento.get('numeroContaContrapartida', '')
        
        dv_conta_raw = lancamento.get('textoDvContaContrapartida', '')
        dv_conta = str(dv_conta_raw).strip() if dv_conta_raw else ''
        
        # Se não houver CPF/CNPJ, não há informações de contrapartida
        if not cpf_cnpj or cpf_cnpj == '0' or cpf_cnpj == '':
            return ""
        
        # Formatar CPF/CNPJ primeiro para determinar o tipo
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
        if len(cpf_cnpj_limpo) == 11:  # CPF
            cpf_formatado = f"{cpf_cnpj_limpo[0:3]}.{cpf_cnpj_limpo[3:6]}.{cpf_cnpj_limpo[6:9]}-{cpf_cnpj_limpo[9:11]}"
            tipo_str = "CPF"
            tipo_consulta = "CPF"
        elif len(cpf_cnpj_limpo) == 14:  # CNPJ
            cpf_formatado = f"{cpf_cnpj_limpo[0:2]}.{cpf_cnpj_limpo[2:5]}.{cpf_cnpj_limpo[5:8]}/{cpf_cnpj_limpo[8:12]}-{cpf_cnpj_limpo[12:14]}"
            tipo_str = "CNPJ"
            tipo_consulta = "CNPJ"
        else:
            cpf_formatado = cpf_cnpj
            tipo_str = "CPF/CNPJ"
            tipo_consulta = None
        
        # ✅ Consultar nome via serviço genérico (se disponível)
        nome_contrapartida = None
        if self.cpf_cnpj_service and tipo_consulta:
            try:
                resultado_consulta = self.cpf_cnpj_service.consultar(cpf_cnpj_limpo, tipo_consulta)
                if resultado_consulta and resultado_consulta.get('nome'):
                    nome_contrapartida = resultado_consulta.get('nome')
                    logger.info(f"✅ Nome encontrado para {cpf_cnpj_limpo}: {nome_contrapartida}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao consultar nome de {cpf_cnpj_limpo}: {e}")
        
        # Montar informações
        partes = []
        
        # ✅ Nome (se encontrado)
        if nome_contrapartida:
            partes.append(f"**{nome_contrapartida}**")
        
        # CPF/CNPJ
        partes.append(f"{tipo_str}: {cpf_formatado}")
        
        # Dados bancários (se disponíveis)
        if codigo_banco:
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
            banco_nome = bancos.get(str(codigo_banco).zfill(3), f'Banco {codigo_banco}')
            
            if agencia and conta:
                conta_formatada = f"{conta}"
                if dv_conta:
                    conta_formatada += f"-{dv_conta}"
                partes.append(f"{banco_nome} - Ag. {agencia} C/C {conta_formatada}")
            else:
                partes.append(f"{banco_nome}")
        
        return " | ".join(partes)

