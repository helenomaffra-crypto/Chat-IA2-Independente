"""
Agent para operações bancárias do Banco do Brasil.

Gerencia consultas de extrato.
"""
import logging
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from services.agents.base_agent import BaseAgent
from services.banco_brasil_service import BancoBrasilService

logger = logging.getLogger(__name__)


def _converter_data_para_datetime(data_str: str) -> Optional[datetime]:
    """
    Converte data em vários formatos para datetime.
    
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
        return datetime.combine(hoje, datetime.min.time())
    elif data_str == "ontem":
        return datetime.combine(hoje - timedelta(days=1), datetime.min.time())
    elif "semana passada" in data_str or "semana anterior" in data_str:
        return datetime.combine(hoje - timedelta(days=7), datetime.min.time())
    elif "mês passado" in data_str or "mes passado" in data_str:
        return datetime.combine(hoje - timedelta(days=30), datetime.min.time())
    
    # Formato YYYY-MM-DD
    try:
        return datetime.strptime(data_str, "%Y-%m-%d")
    except ValueError:
        pass
    
    # Formato DD/MM/YYYY
    try:
        return datetime.strptime(data_str, "%d/%m/%Y")
    except ValueError:
        pass
    
    # Formato DD-MM-YYYY
    try:
        return datetime.strptime(data_str, "%d-%m-%Y")
    except ValueError:
        pass
    
    # ✅ NOVO: Formato "dia X" ou "dia X de mês" (melhorado)
    match = re.search(r'dia\s+(\d{1,2})(?:[/-](\d{1,2}))?(?:\s+de\s+([a-zçã]+))?', data_str)
    if match:
        dia = int(match.group(1))
        mes = hoje.month
        ano = hoje.year
        
        if match.group(2):
            mes = int(match.group(2))
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
            # Se a data resultante for no futuro, assume que é do mês passado
            if dt.date() > hoje and not match.group(2) and not match.group(3):
                if mes == 1:
                    dt = datetime(ano - 1, 12, dia)
                else:
                    dt = datetime(ano, mes - 1, dia)
            return dt
        except ValueError:
            pass
    
    return None


class BancoBrasilAgent(BaseAgent):
    """
    Agent responsável por operações bancárias do Banco do Brasil.
    
    Tools suportadas:
    - consultar_extrato_bb: Consulta extrato bancário do Banco do Brasil
    """
    
    def __init__(self):
        """Inicializa o agent."""
        super().__init__()
        self.banco_brasil_service = BancoBrasilService()
        # ✅ NOVO (13/01/2026): Serviço de Pagamentos em Lote
        try:
            from services.banco_brasil_payments_service import BancoBrasilPaymentsService
            self.payments_service = BancoBrasilPaymentsService()
            logger.info("✅ BancoBrasilPaymentsService inicializado no Agent")
        except ImportError as e:
            logger.warning(f"⚠️ BancoBrasilPaymentsService não disponível: {e}")
            self.payments_service = None
        except Exception as e:
            logger.warning(f"⚠️ Erro ao inicializar BancoBrasilPaymentsService: {e}")
            self.payments_service = None
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], 
                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            # Extratos (existentes)
            'consultar_extrato_bb': self._consultar_extrato,
            'gerar_pdf_extrato_bb': self._gerar_pdf_extrato,
            'consultar_movimentacoes_bb_bd': self._consultar_movimentacoes_bd,
            # ✅ NOVO (13/01/2026): Pagamentos em Lote
            'iniciar_pagamento_lote_bb': self._iniciar_pagamento_lote,
            'consultar_lote_bb': self._consultar_lote,
            'listar_lotes_bb': self._listar_lotes,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada',
                'resposta': f'❌ Tool "{tool_name}" não disponível.'
            }
        
        try:
            return handler(arguments, context)
        except Exception as e:
            logger.error(f'Erro ao executar {tool_name}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro: {str(e)}'
            }
    
    def _consultar_extrato(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Consulta extrato bancário do Banco do Brasil.
        
        Args:
            arguments: {
                'agencia': str - Número da agência (sem dígito verificador)
                'conta': str - Número da conta (sem dígito verificador)
                'data_inicio': str - Data inicial (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
                'data_fim': str - Data final (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
            }
        """
        try:
            agencia = arguments.get('agencia')
            conta = arguments.get('conta')
            data_inicio_str = arguments.get('data_inicio')
            data_fim_str = arguments.get('data_fim')
            
            # ✅ Usar valores padrão do .env se não fornecidos
            if not agencia:
                agencia = os.getenv('BB_TEST_AGENCIA')
            
            # ✅ Suporte para múltiplas contas
            # Se conta não fornecida, usar conta padrão
            # Se conta fornecida como "2" ou "conta2", usar BB_TEST_CONTA_2
            if not conta:
                conta = os.getenv('BB_TEST_CONTA')
            elif str(conta).lower() in ['2', 'conta2', 'conta 2', 'segunda']:
                # Usar segunda conta configurada
                conta_2 = os.getenv('BB_TEST_CONTA_2')
                if conta_2:
                    conta = conta_2
                    logger.info(f"📝 Usando segunda conta configurada (BB_TEST_CONTA_2): {conta}")
                else:
                    conta = os.getenv('BB_TEST_CONTA')
                    logger.warning("⚠️ BB_TEST_CONTA_2 não configurado, usando BB_TEST_CONTA como fallback")
            # Se conta fornecida diretamente (ex: "43344"), usar como está
            
            # Validar agência e conta
            if not agencia or not conta:
                resposta = '📋 **Para consultar o extrato do Banco do Brasil, preciso de:**\n\n'
                resposta += '• **Agência** (sem dígito verificador)\n'
                resposta += '• **Conta** (sem dígito verificador)\n\n'
                resposta += '💡 **Exemplo de uso:**\n'
                resposta += '• "Extrato BB agência 1505 conta 1348"\n'
                resposta += '• "Extrato BB agência 1505 conta 1348 de hoje"\n'
                resposta += '• "Extrato BB agência 1505 conta 1348 de 01/01/2026 a 10/01/2026"\n'
                resposta += '• "Extrato BB conta 2" (usa segunda conta configurada)\n'
                resposta += '• "Extrato BB conta 43344"\n\n'
                resposta += '⚠️ **Importante:** Agência e conta devem ser informadas sem o dígito verificador.\n\n'
                resposta += '💡 **Dica:** Configure `BB_TEST_AGENCIA` e `BB_TEST_CONTA` no `.env` para usar valores padrão.\n'
                resposta += '💡 **Múltiplas contas:** Configure `BB_TEST_CONTA_2` para uma segunda conta na mesma agência.'
                
                return {
                    'sucesso': False,
                    'erro': 'AGENCIA_CONTA_FALTANDO',
                    'resposta': resposta
                }
            
            # Log quando usar valores padrão
            if not arguments.get('agencia') or not arguments.get('conta'):
                logger.info(f"📝 Usando valores padrão do .env: agência={agencia}, conta={conta}")
            
            # Converter datas
            data_inicio = None
            data_fim = None
            
            if data_inicio_str:
                data_inicio = _converter_data_para_datetime(data_inicio_str)
                if not data_inicio:
                    return {
                        'sucesso': False,
                        'erro': 'DATA_INICIO_INVALIDA',
                        'resposta': f'❌ **Data inicial inválida:** {data_inicio_str}\n\nUse formato YYYY-MM-DD ou DD/MM/YYYY.'
                    }
            
            if data_fim_str:
                data_fim = _converter_data_para_datetime(data_fim_str)
                if not data_fim:
                    return {
                        'sucesso': False,
                        'erro': 'DATA_FIM_INVALIDA',
                        'resposta': f'❌ **Data final inválida:** {data_fim_str}\n\nUse formato YYYY-MM-DD ou DD/MM/YYYY.'
                    }
            
            # Consultar extrato
            resultado = self.banco_brasil_service.consultar_extrato(
                agencia=agencia,
                conta=conta,
                data_inicio=data_inicio,
                data_fim=data_fim
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
                            valor='extrato_bb',
                        dados_adicionais={
                            'banco': 'BB',
                            'agencia': agencia,
                            'conta': conta,
                            'data_inicio': data_inicio_str,
                            'data_fim': data_fim_str,
                            'data_inicio_dt': data_inicio.strftime('%Y-%m-%d') if data_inicio else None,
                            'data_fim_dt': data_fim.strftime('%Y-%m-%d') if data_fim else None,
                            'total_transacoes': total_transacoes,
                            'timestamp': datetime.now().isoformat()
                        }
                        )
                        logger.debug(f"[CONTEXTO] Contexto de extrato BB salvo: {total_transacoes} transações")
                except Exception as e:
                    logger.debug(f"[CONTEXTO] Erro ao salvar contexto de extrato BB: {e}")
            
            return resultado
            
        except Exception as e:
            logger.error(f'Erro ao consultar extrato BB: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao consultar extrato: {str(e)}'
            }
    
    def _gerar_pdf_extrato(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Gera PDF do extrato bancário do Banco do Brasil no formato contábil.
        
        Args:
            arguments: {
                'agencia': str - Número da agência (opcional, usa padrão do .env)
                'conta': str - Número da conta (opcional, usa padrão do .env)
                'data_inicio': str - Data inicial (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
                'data_fim': str - Data final (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
            }
        """
        try:
            from services.extrato_bancario_pdf_service import ExtratoBancarioPdfService
            from datetime import datetime, timedelta
            import os
            
            agencia = arguments.get('agencia')
            conta = arguments.get('conta')
            data_inicio_str = arguments.get('data_inicio')
            data_fim_str = arguments.get('data_fim')
            
            # ✅ Usar valores padrão do .env se não fornecidos
            if not agencia:
                agencia = os.getenv('BB_TEST_AGENCIA')
            
            # ✅ Suporte para múltiplas contas
            if not conta:
                conta = os.getenv('BB_TEST_CONTA')
            elif str(conta).lower() in ['2', 'conta2', 'conta 2', 'segunda']:
                conta_2 = os.getenv('BB_TEST_CONTA_2')
                if conta_2:
                    conta = conta_2
                else:
                    conta = os.getenv('BB_TEST_CONTA')
            
            # Validar agência e conta
            if not agencia or not conta:
                return {
                    'sucesso': False,
                    'erro': 'AGENCIA_CONTA_FALTANDO',
                    'resposta': '❌ **Agência e conta são obrigatórias.**\n\nConfigure `BB_TEST_AGENCIA` e `BB_TEST_CONTA` no `.env` ou informe na solicitação.'
                }
            
            # Converter datas
            data_inicio = None
            data_fim = None
            
            if data_inicio_str:
                data_inicio = _converter_data_para_datetime(data_inicio_str)
                if not data_inicio:
                    return {
                        'sucesso': False,
                        'erro': 'DATA_INICIO_INVALIDA',
                        'resposta': f'❌ **Data inicial inválida:** {data_inicio_str}'
                    }
            
            if data_fim_str:
                data_fim = _converter_data_para_datetime(data_fim_str)
                if not data_fim:
                    return {
                        'sucesso': False,
                        'erro': 'DATA_FIM_INVALIDA',
                        'resposta': f'❌ **Data final inválida:** {data_fim_str}'
                    }
            
            # Se nenhuma data fornecida, usar últimos 30 dias
            if not data_inicio and not data_fim:
                hoje = datetime.now()
                data_fim = hoje.replace(hour=23, minute=59, second=59)
                data_inicio = (hoje - timedelta(days=30)).replace(hour=0, minute=0, second=0)
            
            # Consultar extrato primeiro para obter lançamentos
            resultado_extrato = self.banco_brasil_service.consultar_extrato(
                agencia=agencia,
                conta=conta,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            
            if not resultado_extrato.get('sucesso'):
                return resultado_extrato
            
            dados_extrato = resultado_extrato.get('dados', {})
            lancamentos = dados_extrato.get('lancamentos', [])
            
            if not lancamentos:
                return {
                    'sucesso': False,
                    'erro': 'NENHUM_LANCAMENTO',
                    'resposta': '❌ Não foi possível gerar o PDF: nenhum lançamento encontrado no período.'
                }
            
            # Gerar PDF
            pdf_service = ExtratoBancarioPdfService()
            resultado_pdf = pdf_service.gerar_pdf_extrato_bb(
                agencia=agencia,
                conta=conta,
                lancamentos=lancamentos,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            
            return resultado_pdf
            
        except Exception as e:
            logger.error(f'Erro ao gerar PDF do extrato BB: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
            }
    
    def _consultar_movimentacoes_bd(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Consulta movimentações bancárias diretamente do banco de dados SQL Server.
        
        ✅ PRIORIDADE: Use esta função quando o usuário pedir lançamentos já sincronizados,
        extratos já importados, ou movimentações do banco de dados.
        
        Esta função consulta a tabela MOVIMENTACAO_BANCARIA do SQL Server, que contém
        os lançamentos já sincronizados, sem precisar chamar a API do Banco do Brasil.
        
        Args:
            arguments: {
                'agencia': str - Número da agência (opcional, usa padrão do .env)
                'conta': str - Número da conta (opcional, usa padrão do .env)
                'data_inicio': str - Data inicial (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
                'data_fim': str - Data final (opcional, formato YYYY-MM-DD ou DD/MM/YYYY)
                'processo_referencia': str - Filtrar por processo (opcional)
                'tipo_movimentacao': str - Filtrar por tipo (opcional, ex: 'PIX', 'TRANSFERENCIA')
                'sinal': str - Filtrar por sinal (opcional: '+' para crédito, '-' para débito)
                'valor_minimo': float - Valor mínimo (opcional)
                'valor_maximo': float - Valor máximo (opcional)
                'limite': int - Limite de resultados (opcional, default: 100)
            }
        """
        try:
            from utils.sql_server_adapter import get_sql_adapter
            from datetime import datetime, timedelta
            
            adapter = get_sql_adapter()
            
            if not adapter.test_connection():
                return {
                    'sucesso': False,
                    'erro': 'SQL_SERVER_INDISPONIVEL',
                    'resposta': '❌ SQL Server não está disponível. Os lançamentos podem não ter sido sincronizados ainda.'
                }
            
            # Parâmetros de filtro
            agencia = arguments.get('agencia') or os.getenv('BB_TEST_AGENCIA')
            conta = arguments.get('conta')
            processo_ref = arguments.get('processo_referencia')
            tipo_mov = arguments.get('tipo_movimentacao')
            sinal = arguments.get('sinal')
            valor_min = arguments.get('valor_minimo')
            valor_max = arguments.get('valor_maximo')
            limite = int(arguments.get('limite', 100))
            
            # Converter conta se necessário
            if conta:
                if str(conta).lower() in ['2', 'conta2', 'conta 2', 'segunda']:
                    conta_2 = os.getenv('BB_TEST_CONTA_2')
                    if conta_2:
                        conta = conta_2
                    else:
                        conta = os.getenv('BB_TEST_CONTA')
                # Se conta fornecida diretamente, usar como está
            
            if not conta:
                conta = os.getenv('BB_TEST_CONTA')
            
            if not agencia or not conta:
                return {
                    'sucesso': False,
                    'erro': 'AGENCIA_CONTA_FALTANDO',
                    'resposta': '❌ **Agência e conta são obrigatórias.**\n\nConfigure `BB_TEST_AGENCIA` e `BB_TEST_CONTA` no `.env` ou informe na solicitação.'
                }
            
            # Converter datas
            data_inicio = None
            data_fim = None
            
            if arguments.get('data_inicio'):
                data_inicio = _converter_data_para_datetime(arguments['data_inicio'])
            
            if arguments.get('data_fim'):
                data_fim = _converter_data_para_datetime(arguments['data_fim'])
            
            # Se nenhuma data fornecida, usar últimos 30 dias
            if not data_inicio and not data_fim:
                hoje = datetime.now()
                data_fim = hoje.replace(hour=23, minute=59, second=59)
                data_inicio = (hoje - timedelta(days=30)).replace(hour=0, minute=0, second=0)
            
            # Construir query SQL
            where_clauses = [
                "banco_origem = 'BB'",
                f"agencia_origem = '{agencia}'",
                f"conta_origem = '{conta}'"
            ]
            
            if data_inicio:
                data_inicio_str = data_inicio.strftime('%Y-%m-%d')
                where_clauses.append(f"CAST(data_movimentacao AS DATE) >= '{data_inicio_str}'")
            
            if data_fim:
                data_fim_str = data_fim.strftime('%Y-%m-%d')
                where_clauses.append(f"CAST(data_movimentacao AS DATE) <= '{data_fim_str}'")
            
            if processo_ref:
                where_clauses.append(f"processo_referencia = '{processo_ref}'")
            
            if tipo_mov:
                where_clauses.append(f"tipo_movimentacao LIKE '%{tipo_mov}%'")
            
            if sinal:
                # ✅ CORREÇÃO: Converter '+' para 'C' e '-' para 'D' (formato do banco)
                sinal_banco = 'C' if sinal == '+' else 'D'
                where_clauses.append(f"sinal_movimentacao = '{sinal_banco}'")
            
            if valor_min:
                where_clauses.append(f"valor_movimentacao >= {float(valor_min)}")
            
            if valor_max:
                where_clauses.append(f"valor_movimentacao <= {float(valor_max)}")
            
            where_sql = " AND ".join(where_clauses)
            
            query = f"""
                SELECT TOP {limite}
                    id_movimentacao,
                    data_movimentacao,
                    data_lancamento,
                    sinal_movimentacao,
                    valor_movimentacao,
                    tipo_movimentacao,
                    descricao_movimentacao,
                    processo_referencia,
                    cpf_cnpj_contrapartida,
                    nome_contrapartida,
                    historico_codigo,
                    informacoes_complementares,
                    hash_dados,
                    criado_em
                FROM dbo.MOVIMENTACAO_BANCARIA
                WHERE {where_sql}
                ORDER BY data_movimentacao DESC, criado_em DESC
            """
            
            logger.info(f"🔍 Consultando movimentações BB no BD: Ag. {agencia} C/C {conta}")
            
            resultado = adapter.execute_query(query, database=adapter.database)
            
            if not resultado.get('success'):
                error_msg = resultado.get('error', 'Erro desconhecido')
                logger.error(f"❌ Erro ao consultar movimentações: {error_msg}")
                return {
                    'sucesso': False,
                    'erro': 'ERRO_CONSULTA',
                    'resposta': f'❌ Erro ao consultar movimentações no banco de dados: {error_msg}'
                }
            
            rows = resultado.get('data', [])
            
            if not rows:
                periodo_str = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}" if data_inicio and data_fim else "período informado"
                return {
                    'sucesso': True,
                    'total': 0,
                    'lancamentos': [],
                    'resposta': f'📋 **Nenhum lançamento encontrado** no banco de dados para:\n\n• Ag. {agencia} / C/C {conta}\n• Período: {periodo_str}\n\n💡 **Dica:** Verifique se os lançamentos foram sincronizados usando o botão de sincronização.'
                }
            
            # Formatar lançamentos
            lancamentos_formatados = []
            total_credito = 0.0
            total_debito = 0.0
            
            for row in rows:
                valor = float(row.get('valor_movimentacao', 0))
                sinal_mov = str(row.get('sinal_movimentacao', 'C')).strip().upper()
                
                # ✅ CORREÇÃO: Banco salva 'C' (Crédito) ou 'D' (Débito), não '+' ou '-'
                if sinal_mov == 'C' or sinal_mov == '+':
                    total_credito += valor
                    sinal_exibicao = '+'
                else:  # 'D' ou '-'
                    total_debito += valor
                    sinal_exibicao = '-'
                
                lancamento = {
                    'id': row.get('id_movimentacao'),
                    'data': row.get('data_movimentacao'),
                    'sinal': sinal_exibicao,  # Usar '+' ou '-' para exibição
                    'sinal_original': sinal_mov,  # Manter original ('C' ou 'D')
                    'valor': valor,
                    'tipo': row.get('tipo_movimentacao', ''),
                    'descricao': row.get('descricao_movimentacao', ''),
                    'processo': row.get('processo_referencia'),
                    'contrapartida': {
                        'cpf_cnpj': row.get('cpf_cnpj_contrapartida'),
                        'nome': row.get('nome_contrapartida')
                    },
                    'historico': row.get('historico_codigo', ''),
                    'info_complementar': row.get('informacoes_complementares', '')
                }
                lancamentos_formatados.append(lancamento)
            
            # Construir resposta formatada
            periodo_str = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}" if data_inicio and data_fim else "período consultado"
            
            resposta = f"📊 **Movimentações Banco do Brasil (BD)**\n\n"
            resposta += f"• **Conta:** Ag. {agencia} / C/C {conta}\n"
            resposta += f"• **Período:** {periodo_str}\n"
            resposta += f"• **Total encontrado:** {len(rows)} lançamento(s)\n\n"
            
            resposta += f"💰 **Resumo:**\n"
            resposta += f"• Créditos: R$ {total_credito:,.2f}\n"
            resposta += f"• Débitos: R$ {total_debito:,.2f}\n"
            resposta += f"• Saldo: R$ {(total_credito - total_debito):,.2f}\n\n"
            
            if processo_ref:
                resposta += f"🔗 **Filtrado por processo:** {processo_ref}\n\n"
            
            if len(rows) > 0:
                resposta += f"📋 **Últimos {min(10, len(rows))} lançamentos:**\n\n"
                
                for i, lanc in enumerate(lancamentos_formatados[:10], 1):
                    data_formatada = lanc['data'].strftime('%d/%m/%Y') if hasattr(lanc['data'], 'strftime') else str(lanc['data'])[:10]
                    sinal_sym = lanc['sinal']  # Já está como '+' ou '-' após correção
                    valor_formatado = f"R$ {lanc['valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    
                    resposta += f"{i}. **{data_formatada}** | {sinal_sym}{valor_formatado} | {lanc['tipo']}\n"
                    resposta += f"   {lanc['descricao'][:60]}{'...' if len(lanc['descricao']) > 60 else ''}\n"
                    
                    if lanc['processo']:
                        resposta += f"   🔗 Processo: {lanc['processo']}\n"
                    
                    resposta += "\n"
                
                if len(rows) > 10:
                    resposta += f"   ... e mais {len(rows) - 10} lançamento(s)\n"
            
            return {
                'sucesso': True,
                'total': len(rows),
                'lancamentos': lancamentos_formatados,
                'resumo': {
                    'credito': total_credito,
                    'debito': total_debito,
                    'saldo': total_credito - total_debito
                },
                'resposta': resposta
            }
            
        except Exception as e:
            logger.error(f'Erro ao consultar movimentações no BD: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao consultar movimentações: {str(e)}'
            }
    
    def _iniciar_pagamento_lote(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Inicia um pagamento em lote no Banco do Brasil.
        
        Args:
            arguments: {
                'agencia': str - Agência da conta (4 dígitos)
                'conta': str - Número da conta (sem dígito verificador)
                'pagamentos': List[Dict] - Lista de pagamentos, cada um com:
                    - tipo: str - Tipo ('BOLETO', 'PIX', 'TED')
                    - codigo_barras: str - Código de barras (para boleto)
                    - valor: float - Valor do pagamento
                    - beneficiario: str - Nome do beneficiário (opcional)
                    - vencimento: str - Data de vencimento YYYY-MM-DD (opcional)
                'data_pagamento': str - Data do pagamento YYYY-MM-DD (opcional)
            }
        """
        if not self.payments_service or not self.payments_service.enabled:
            return {
                'sucesso': False,
                'erro': 'Serviço não disponível',
                'resposta': '❌ **Serviço de Pagamentos em Lote do Banco do Brasil não está disponível.**\n\nVerifique se:\n- As credenciais BB_* estão configuradas no .env\n- O serviço foi inicializado corretamente'
            }
        
        try:
            agencia = arguments.get('agencia', '')
            conta = arguments.get('conta', '')
            pagamentos = arguments.get('pagamentos', [])
            data_pagamento = arguments.get('data_pagamento')
            
            if not agencia or not conta:
                return {
                    'sucesso': False,
                    'erro': 'Agência e conta são obrigatórias',
                    'resposta': '❌ **Agência e conta são obrigatórias.**\n\nForneça:\n- agencia: Número da agência (4 dígitos)\n- conta: Número da conta (sem dígito verificador)'
                }
            
            if not pagamentos:
                return {
                    'sucesso': False,
                    'erro': 'Lista de pagamentos vazia',
                    'resposta': '❌ **Lista de pagamentos está vazia.**\n\nAdicione pelo menos um pagamento à lista.'
                }
            
            resultado = self.payments_service.iniciar_pagamento_lote(
                agencia=agencia,
                conta=conta,
                pagamentos=pagamentos,
                data_pagamento=data_pagamento
            )
            
            return resultado
            
        except Exception as e:
            logger.error(f'Erro ao iniciar pagamento em lote: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao iniciar pagamento em lote:** {str(e)}'
            }
    
    def _consultar_lote(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Consulta status de um lote de pagamentos.
        
        Args:
            arguments: {
                'id_lote': str - ID do lote
            }
        """
        if not self.payments_service or not self.payments_service.enabled:
            return {
                'sucesso': False,
                'erro': 'Serviço não disponível',
                'resposta': '❌ **Serviço de Pagamentos em Lote do Banco do Brasil não está disponível.**'
            }
        
        try:
            id_lote = arguments.get('id_lote', '')
            
            if not id_lote:
                return {
                    'sucesso': False,
                    'erro': 'ID do lote é obrigatório',
                    'resposta': '❌ **ID do lote é obrigatório.**\n\nForneça:\n- id_lote: ID do lote de pagamentos'
                }
            
            resultado = self.payments_service.consultar_lote(id_lote)
            return resultado
            
        except Exception as e:
            logger.error(f'Erro ao consultar lote: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao consultar lote:** {str(e)}'
            }
    
    def _listar_lotes(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Lista lotes de pagamentos.
        
        Args:
            arguments: {
                'agencia': str - Agência (opcional)
                'conta': str - Conta (opcional)
                'data_inicio': str - Data inicial YYYY-MM-DD (opcional)
                'data_fim': str - Data final YYYY-MM-DD (opcional)
            }
        """
        if not self.payments_service or not self.payments_service.enabled:
            return {
                'sucesso': False,
                'erro': 'Serviço não disponível',
                'resposta': '❌ **Serviço de Pagamentos em Lote do Banco do Brasil não está disponível.**'
            }
        
        try:
            agencia = arguments.get('agencia')
            conta = arguments.get('conta')
            data_inicio = arguments.get('data_inicio')
            data_fim = arguments.get('data_fim')
            
            resultado = self.payments_service.listar_lotes(
                agencia=agencia,
                conta=conta,
                data_inicio=data_inicio,
                data_fim=data_fim
            )
            return resultado
            
        except Exception as e:
            logger.error(f'Erro ao listar lotes: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ **Erro ao listar lotes:** {str(e)}'
            }

