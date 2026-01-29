"""
Router que direciona tool calls para agents específicos.
Implementa o padrão Router para escalabilidade.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ToolRouter:
    """
    Router que direciona tool calls para agents específicos.
    
    Cada tool é mapeada para um agent responsável por executá-la.
    Isso permite escalabilidade e separação de responsabilidades.
    """
    
    def __init__(self):
        """Inicializa o router e carrega todos os agents."""
        self.agents = {}
        self._agent_classes = {}
        self.tool_to_agent = {}
        self._initialize_agents()
        self._build_tool_mapping()
    
    def _initialize_agents(self):
        """Inicializa todos os agents disponíveis."""
        try:
            # Importar agents disponíveis (alguns podem não existir ainda)
            agents_config = {}
            
            try:
                from .agents.processo_agent import ProcessoAgent
                agents_config['processo'] = ProcessoAgent
                logger.debug("✅ ProcessoAgent importado")
            except Exception as e:
                logger.error(f"❌ Erro ao importar ProcessoAgent: {e}", exc_info=True)
                logger.warning(f"⚠️ ProcessoAgent não disponível: {e}")
            
            try:
                from .agents.duimp_agent import DuimpAgent
                agents_config['duimp'] = DuimpAgent
                logger.debug("✅ DuimpAgent importado")
            except Exception as e:
                logger.error(f"❌ Erro ao importar DuimpAgent: {e}", exc_info=True)
                logger.warning(f"⚠️ DuimpAgent não disponível: {e}")
            
            try:
                from .agents.ce_agent import CeAgent
                agents_config['ce'] = CeAgent
            except ImportError as e:
                logger.warning(f"⚠️ CeAgent não disponível: {e}")
            
            try:
                from .agents.di_agent import DiAgent
                agents_config['di'] = DiAgent
                logger.debug("✅ DiAgent importado")
            except Exception as e:
                logger.error(f"❌ Erro ao importar DiAgent: {e}", exc_info=True)
                logger.warning(f"⚠️ DiAgent não disponível: {e}")
            
            try:
                from .agents.cct_agent import CctAgent
                agents_config['cct'] = CctAgent
            except ImportError as e:
                logger.warning(f"⚠️ CctAgent não disponível: {e}")
            
            try:
                from .agents.legislacao_agent import LegislacaoAgent
                agents_config['legislacao'] = LegislacaoAgent
            except ImportError as e:
                logger.warning(f"⚠️ LegislacaoAgent não disponível: {e}")
            
            try:
                from .agents.calculo_agent import CalculoAgent
                agents_config['calculo'] = CalculoAgent
            except ImportError as e:
                logger.warning(f"⚠️ CalculoAgent não disponível: {e}")
            
            try:
                from .agents.santander_agent import SantanderAgent
                agents_config['santander'] = SantanderAgent
            except ImportError as e:
                logger.warning(f"⚠️ SantanderAgent não disponível: {e}")
            
            try:
                from .agents.banco_brasil_agent import BancoBrasilAgent
                agents_config['banco_brasil'] = BancoBrasilAgent
            except ImportError as e:
                logger.warning(f"⚠️ BancoBrasilAgent não disponível: {e}")
            
            try:
                from .agents.sistema_agent import SistemaAgent
                agents_config['sistema'] = SistemaAgent
            except ImportError as e:
                logger.warning(f"⚠️ SistemaAgent não disponível: {e}")

            try:
                from .agents.mercante_agent import MercanteAgent
                agents_config['mercante'] = MercanteAgent
            except ImportError as e:
                logger.warning(f"⚠️ MercanteAgent não disponível: {e}")
            
            # Inicializar cada agent individualmente para capturar erros específicos
            # ✅ Importante: manter o registro das classes mesmo se a instância falhar,
            # para permitir inicialização "lazy" (sob demanda) e evitar "Agent não encontrado".
            self._agent_classes = dict(agents_config)
            self.agents = {}
            for agent_key, agent_class in agents_config.items():
                try:
                    self.agents[agent_key] = agent_class()
                    logger.debug(f"✅ Agent '{agent_key}' inicializado")
                except Exception as e:
                    logger.error(f"❌ Erro ao inicializar agent '{agent_key}': {e}", exc_info=True)
            
            if self.agents:
                logger.info(f"✅ ToolRouter inicializado com {len(self.agents)} agents: {list(self.agents.keys())}")
                # Log detalhado de cada agent
                for agent_key, agent_instance in self.agents.items():
                    logger.debug(f"   - {agent_key}: {type(agent_instance).__name__}")
            else:
                logger.error("❌ Nenhum agent foi inicializado! Verifique os logs acima.")
        except ImportError as e:
            logger.error(f"❌ Erro de importação ao inicializar agents: {e}", exc_info=True)
            self.agents = {}
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar agents: {e}", exc_info=True)
            self.agents = {}
    
    def _build_tool_mapping(self):
        """
        Constrói mapeamento de tools para agents.
        
        Este mapeamento define qual agent é responsável por cada tool.
        Para adicionar nova tool, basta adicionar aqui e implementar no agent correspondente.
        """
        self.tool_to_agent = {
            # ========== PROCESSOS ==========
            'listar_processos': 'processo',
            'gerar_relatorio_importacoes_fob': 'processo',
            'consultar_status_processo': 'processo',
            'consultar_despesas_processo': 'processo',
                'obter_snapshot_processo': 'processo',
            'sincronizar_processos_ativos_maike': 'processo',
            'listar_processos_por_categoria': 'processo',
            'listar_processos_por_situacao': 'processo',
            'listar_processos_por_eta': 'processo',
            'listar_processos_por_navio': 'processo',
            'listar_processos_liberados_registro': 'processo',
            'listar_processos_registrados_hoje': 'processo',
            'listar_processos_registrados_periodo': 'processo',
            'listar_processos_desembaracados_hoje': 'processo',
            'listar_processos_em_dta': 'processo',
            'listar_processos_com_pendencias': 'processo',
            'listar_todos_processos_por_situacao': 'processo',
            'consultar_processo_consolidado': 'processo',
            'obter_dashboard_hoje': 'processo',
            'fechar_dia': 'processo',
            'gerar_relatorio_averbacoes': 'processo',
            'consultar_contexto_sessao': 'processo',  # ✅ NOVO (12/01/2026): Consultar contexto real da sessão
            'buscar_secao_relatorio_salvo': 'processo',  # ✅ NOVO (12/01/2026): Buscar seção específica do relatório salvo
            'listar_dis_por_canal': 'processo',  # ✅ NOVO (20/01/2026): Lista DIs por canal (ativos-first)
            'listar_pendencias_ativas': 'processo',  # ✅ NOVO (20/01/2026): Pendências ativas (ativos-first)
            'listar_alertas_recentes': 'processo',  # ✅ NOVO (20/01/2026): Alertas recentes (ativos-first)
            'listar_processos_prontos_registro': 'processo',  # ✅ NOVO (20/01/2026): Prontos p/ registro (ativos-first)
            'listar_eta_alterado': 'processo',  # ✅ NOVO (20/01/2026): ETA alterado (ativos-first)
            'listar_duimps_em_analise': 'processo',  # ✅ NOVO (20/01/2026): DUIMPs em análise (ativos-first)
            'buscar_relatorio_por_id': 'processo',  # ✅ NOVO (12/01/2026): Buscar relatório específico por ID
            'filtrar_relatorio_fuzzy': 'processo',  # ✅ NOVO (28/01/2026): Filtro/agrupamento fuzzy no relatório salvo
            
            # ========== DUIMP ==========
            'criar_duimp': 'duimp',
            'verificar_duimp_registrada': 'duimp',
            'obter_dados_duimp': 'duimp',
            'vincular_processo_duimp': 'duimp',
            'obter_extrato_pdf_duimp': 'duimp',
            
            # ========== CE ==========
            'consultar_ce_maritimo': 'ce',
            'verificar_atualizacao_ce': 'ce',
            # 'vincular_processo_ce': 'ce',  # ✅ DESABILITADO: Nesta aplicação não vinculamos manualmente
            'listar_processos_com_situacao_ce': 'ce',
            'obter_extrato_ce': 'ce',
            # ✅ ROTEADO: handler existe no ToolExecutionService (delegado via SistemaAgent)
            'obter_valores_ce': 'sistema',
            
            # ========== DI (Declaração de Importação) ==========
            'obter_dados_di': 'di',
            'vincular_processo_di': 'di',
            'obter_extrato_pdf_di': 'di',
            'consultar_adicoes_di': 'di',
            
            # ========== CCT (Conhecimento de Carga Aérea) ==========
            'consultar_cct': 'cct',
            # 'vincular_processo_cct': 'cct',  # ✅ DESABILITADO: Nesta aplicação não vinculamos manualmente
            'obter_extrato_cct': 'cct',
            
            # ========== LEGISLAÇÃO ==========
            'buscar_legislacao': 'legislacao',
            'buscar_trechos_legislacao': 'legislacao',
            'buscar_em_todas_legislacoes': 'legislacao',
            'buscar_legislacao_responses': 'legislacao',  # ✅ NOVO: Responses API (recomendado)
            'buscar_legislacao_assistants': 'legislacao',  # ⚠️ LEGADO: Assistants API (deprecated)
            'buscar_e_importar_legislacao': 'legislacao',
            'importar_legislacao_preview': 'legislacao',
            'confirmar_importacao_legislacao': 'legislacao',
            
            # ========== CÁLCULOS ==========
            'calcular_impostos_ncm': 'calculo',  # ✅ MIGRADO: Handler no CalculoAgent / ToolExecutionService
            'calcular_percentual': 'calculo',  # ✅ Cálculos simples de percentual
            
            # ========== SANTANDER OPEN BANKING ==========
            'listar_contas_santander': 'santander',  # ✅ NOVO: Listar contas do Santander
            'consultar_extrato_santander': 'santander',  # ✅ NOVO: Consultar extrato bancário
            'consultar_saldo_santander': 'santander',  # ✅ NOVO: Consultar saldo da conta
            'gerar_pdf_extrato_santander': 'santander',  # ✅ NOVO: Gerar PDF do extrato bancário do Santander
            # ✅ NOVO (12/01/2026): Pagamentos Santander (ISOLADO - Cenário 1)
            'listar_workspaces_santander': 'santander',  # Listar workspaces para pagamentos
            'criar_workspace_santander': 'santander',  # Criar workspace para pagamentos
            'iniciar_ted_santander': 'santander',  # Iniciar transferência TED
            'efetivar_ted_santander': 'santander',  # Efetivar TED iniciada
            'consultar_ted_santander': 'santander',  # Consultar TED por ID
            'listar_teds_santander': 'santander',  # Listar TEDs (conciliação)
            # ✅ NOVO (13/01/2026): Accounts and Taxes (Bank Slip, Barcode, PIX, Vehicle Taxes, Taxes by Fields)
            # Bank Slip Payments
            'processar_boleto_upload': 'santander',  # Processar upload de boleto (extrair dados)
            'iniciar_bank_slip_payment_santander': 'santander',  # Iniciar pagamento de boleto
            'efetivar_bank_slip_payment_santander': 'santander',  # Efetivar pagamento de boleto
            'consultar_bank_slip_payment_santander': 'santander',  # Consultar pagamento de boleto
            'listar_bank_slip_payments_santander': 'santander',  # Listar pagamentos de boleto
            # Barcode Payments
            'iniciar_barcode_payment_santander': 'santander',  # Iniciar pagamento por código de barras
            'efetivar_barcode_payment_santander': 'santander',  # Efetivar pagamento por código de barras
            'consultar_barcode_payment_santander': 'santander',  # Consultar pagamento por código de barras
            'listar_barcode_payments_santander': 'santander',  # Listar pagamentos por código de barras
            # Pix Payments
            'iniciar_pix_payment_santander': 'santander',  # Iniciar pagamento PIX
            'efetivar_pix_payment_santander': 'santander',  # Efetivar pagamento PIX
            'consultar_pix_payment_santander': 'santander',  # Consultar pagamento PIX
            'listar_pix_payments_santander': 'santander',  # Listar pagamentos PIX
            # Vehicle Taxes Payments
            'consultar_debitos_renavam_santander': 'santander',  # Consultar débitos Renavam
            'iniciar_vehicle_tax_payment_santander': 'santander',  # Iniciar pagamento de IPVA
            'efetivar_vehicle_tax_payment_santander': 'santander',  # Efetivar pagamento de IPVA
            'consultar_vehicle_tax_payment_santander': 'santander',  # Consultar pagamento de IPVA
            'listar_vehicle_tax_payments_santander': 'santander',  # Listar pagamentos de IPVA
            # Taxes by Fields Payments
            'iniciar_tax_by_fields_payment_santander': 'santander',  # Iniciar pagamento de imposto por campos (GARE, DARF, GPS)
            'efetivar_tax_by_fields_payment_santander': 'santander',  # Efetivar pagamento de imposto por campos
            'consultar_tax_by_fields_payment_santander': 'santander',  # Consultar pagamento de imposto por campos
            'listar_tax_by_fields_payments_santander': 'santander',  # Listar pagamentos de impostos por campos
            
            # ========== BANCO DO BRASIL EXTRATOS API ==========
            'consultar_movimentacoes_bb_bd': 'banco_brasil',  # ✅ NOVO: Consultar movimentações BB do banco de dados (prioridade)
            'consultar_extrato_bb': 'banco_brasil',  # ✅ NOVO: Consultar extrato bancário do Banco do Brasil (API)
            'gerar_pdf_extrato_bb': 'banco_brasil',  # ✅ NOVO: Gerar PDF do extrato bancário do Banco do Brasil
            # ✅ NOVO (13/01/2026): Pagamentos em Lote Banco do Brasil
            'iniciar_pagamento_lote_bb': 'banco_brasil',  # Iniciar pagamento em lote no BB
            'consultar_lote_bb': 'banco_brasil',  # Consultar status de lote de pagamentos
            'listar_lotes_bb': 'banco_brasil',  # Listar lotes de pagamentos

            # ========== MERCANTE (AFRMM) ==========
            # 'preparar_pagamento_afrmm': 'mercante',  # ⚠️ TEMPORARIAMENTE DESABILITADA: limite de 128 tools
            'executar_pagamento_afrmm': 'mercante',
            
            # ========== SISTEMA (Notícias, etc.) ==========
            'listar_noticias_siscomex': 'sistema',  # ✅ NOVO (18/01/2026): Listar notícias do Siscomex coletadas via RSS

            # ========== HANDLERS EXTRAÍDOS (ToolExecutionService) ==========
            # Regra: se existe handler no ToolExecutionService, NÃO deve ser None aqui.
            # O SistemaAgent delega para o ToolExecutionService preservando session_id e PendingIntents.
            # Sistema / observabilidade / aprendizado
            'verificar_fontes_dados': 'sistema',
            'obter_resumo_aprendizado': 'sistema',
            'obter_relatorio_observabilidade': 'sistema',
            # Email
            'enviar_email_personalizado': 'sistema',
            'enviar_email': 'sistema',
            'enviar_relatorio_email': 'sistema',
            'melhorar_email_draft': 'sistema',
            'ler_emails': 'sistema',
            'obter_detalhes_email': 'sistema',
            'responder_email': 'sistema',
            # NCM / NESH
            'buscar_ncms_por_descricao': 'sistema',
            'sugerir_ncm_com_ia': 'sistema',
            'detalhar_ncm': 'sistema',
            'baixar_nomenclatura_ncm': 'sistema',
            'buscar_nota_explicativa_nesh': 'sistema',
            # Valores
            'obter_valores_processo': 'sistema',
            # Consultas / regras / bilhetadas
            'salvar_regra_aprendida': 'sistema',
            'salvar_consulta_personalizada': 'sistema',
            'buscar_consulta_personalizada': 'sistema',
            'executar_consulta_analitica': 'sistema',
            'consultar_vendas_make': 'sistema',  # ✅ NOVO (28/01/2026): Vendas no legado (Make/Spalla)
            'consultar_vendas_nf_make': 'sistema',  # ✅ NOVO (28/01/2026): Vendas por NF (Make/Spalla)
            'filtrar_relatorio_vendas': 'sistema',  # ✅ NOVO (28/01/2026): Refino do relatório de vendas (sem reconsultar SQL)
            'curva_abc_vendas': 'sistema',  # ✅ NOVO (28/01/2026): Curva ABC em cima do relatório de vendas
            'inspecionar_schema_nf_make': 'sistema',  # ✅ NOVO (28/01/2026): Descoberta de schema NF no legado
            'listar_consultas_bilhetadas_pendentes': 'sistema',
            'aprovar_consultas_bilhetadas': 'sistema',
            'rejeitar_consultas_bilhetadas': 'sistema',
            'ver_status_consultas_bilhetadas': 'sistema',
            'listar_consultas_aprovadas_nao_executadas': 'sistema',
            'executar_consultas_aprovadas': 'sistema',
            
            # Fase 2: fallback residual (categorias / vínculo docs / reunião)
            'listar_categorias_disponiveis': 'sistema',
            'adicionar_categoria_processo': 'sistema',
            'desvincular_documento_processo': 'sistema',
            'vincular_processo_cct': 'sistema',
            'gerar_resumo_reuniao': 'sistema',
        }
    
    def route(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Roteia tool call para agent específico.
        
        Args:
            tool_name: Nome da tool a executar
            arguments: Argumentos da tool
            context: Contexto adicional (mensagem_original, chat_service, etc.)
        
        Returns:
            Dict com resultado da execução:
            - sucesso: bool
            - resposta: str (mensagem formatada)
            - dados: Any (dados brutos, opcional)
            - erro: str (mensagem de erro, se houver)
        """
        agent_name = self.tool_to_agent.get(tool_name)
        
        # Se tool não está mapeada ou agent é None, usar fallback (chat_service.py antigo)
        if agent_name is None:
            logger.debug(f"⚠️ Tool '{tool_name}' não mapeada ou ainda não migrada. Usando fallback.")
            return {
                'sucesso': False,
                'erro': 'TOOL_NAO_MAPEADA',
                'mensagem': f'Tool {tool_name} ainda não foi migrada para arquitetura de agents. Usando implementação antiga.',
                '_use_fallback': True  # Flag para indicar que deve usar chat_service.py
            }
        
        agent = self.agents.get(agent_name)
        if not agent:
            # ✅ Lazy init: tentar inicializar sob demanda se a classe existe
            agent_class = self._agent_classes.get(agent_name)
            if agent_class:
                try:
                    self.agents[agent_name] = agent_class()
                    agent = self.agents.get(agent_name)
                    logger.info(f"✅ Agent '{agent_name}' inicializado sob demanda (lazy)")
                except Exception as e:
                    logger.error(f"❌ Erro ao inicializar agent '{agent_name}' sob demanda: {e}", exc_info=True)
                    agent = None
            if not agent:
                logger.error(f"❌ Agent '{agent_name}' não encontrado para tool '{tool_name}'")
                logger.error(f"🔍 Agents disponíveis: {list(self.agents.keys())}")
                logger.error(f"🔍 Total de agents: {len(self.agents)}")
                return {
                    'sucesso': False,
                    'erro': 'AGENT_NAO_ENCONTRADO',
                    'mensagem': f'Agent {agent_name} não encontrado. Agents disponíveis: {list(self.agents.keys())}'
                }
        
        try:
            logger.info(f"🔄 Roteando tool '{tool_name}' para agent '{agent_name}'")
            resultado = agent.execute(tool_name, arguments, context)
            
            # Garantir que resultado tem estrutura padrão
            if not isinstance(resultado, dict):
                resultado = {'sucesso': True, 'resposta': str(resultado)}
            
            # Adicionar metadados
            resultado['_agent'] = agent_name
            resultado['_tool'] = tool_name
            
            return resultado
        except Exception as e:
            logger.error(f"❌ Erro ao executar tool '{tool_name}' no agent '{agent_name}': {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_EXECUCAO',
                'mensagem': f'Erro ao executar {tool_name}: {str(e)}',
                '_agent': agent_name,
                '_tool': tool_name
            }
    
    def get_available_agents(self) -> Dict[str, list]:
        """
        Retorna lista de tools disponíveis por agent.
        
        Returns:
            Dict {agent_name: [lista_de_tools]}
        """
        agent_tools = {}
        for tool, agent in self.tool_to_agent.items():
            if agent:
                if agent not in agent_tools:
                    agent_tools[agent] = []
                agent_tools[agent].append(tool)
        return agent_tools

