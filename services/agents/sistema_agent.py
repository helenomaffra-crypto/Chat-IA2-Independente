"""
Agent para operações do sistema (notícias do Siscomex, etc.).
Seguindo padrão de refatoração: agent especializado.
"""
import logging
from typing import Dict, Any, Optional

from services.agents.base_agent import BaseAgent
from services.repositories.noticia_repository import NoticiaRepository

logger = logging.getLogger(__name__)


class SistemaAgent(BaseAgent):
    """Agent para operações do sistema (notícias, etc.)"""
    
    def __init__(self):
        """Inicializa o SistemaAgent"""
        super().__init__()
        self.noticia_repository = NoticiaRepository()
        # Tools que são executadas via ToolExecutionService (handlers extraídos).
        # Regra: se a tool tem handler no TES, ela NÃO deve cair em fallback do ChatService.
        self._tools_tes = {
            # Email
            "enviar_email_personalizado",
            "enviar_email",
            "enviar_relatorio_email",
            "melhorar_email_draft",
            "ler_emails",
            "obter_detalhes_email",
            "responder_email",
            # NCM / NESH
            "buscar_ncms_por_descricao",
            "sugerir_ncm_com_ia",
            "detalhar_ncm",
            "baixar_nomenclatura_ncm",
            "buscar_nota_explicativa_nesh",
            # Valores
            "obter_valores_processo",
            "obter_valores_ce",
            # Consultas / regras aprendidas / bilhetadas
            "salvar_regra_aprendida",
            "salvar_consulta_personalizada",
            "buscar_consulta_personalizada",
            "executar_consulta_analitica",
            # Vendas (Make/Spalla)
            "consultar_vendas_make",
            "consultar_vendas_nf_make",
            "inspecionar_schema_nf_make",
            "listar_consultas_bilhetadas_pendentes",
            "aprovar_consultas_bilhetadas",
            "rejeitar_consultas_bilhetadas",
            "ver_status_consultas_bilhetadas",
            "listar_consultas_aprovadas_nao_executadas",
            "executar_consultas_aprovadas",
            # Sistema / observabilidade / aprendizado
            "verificar_fontes_dados",
            "obter_resumo_aprendizado",
            "obter_relatorio_observabilidade",
            # Fase 2: categorias / vínculos / reunião (handlers no TES)
            "listar_categorias_disponiveis",
            "adicionar_categoria_processo",
            "desvincular_documento_processo",
            "vincular_processo_cct",
            "gerar_resumo_reuniao",
        }
    
    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executa uma tool do sistema.
        
        Args:
            tool_name: Nome da tool a ser executada
            arguments: Argumentos da tool
            context: Contexto adicional (opcional)
        
        Returns:
            Dict com resultado da execução
        """
        # 1) Delegar para ToolExecutionService quando houver handler extraído
        if tool_name in self._tools_tes:
            return self._delegar_para_tool_execution_service(tool_name, arguments, context)

        # 2) Handlers "nativos" do SistemaAgent
        handlers = {
            "listar_noticias_siscomex": self._listar_noticias_siscomex,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada',
                'resposta': f'❌ Tool "{tool_name}" não disponível no SistemaAgent.'
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

    def _delegar_para_tool_execution_service(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executa tools que já possuem handler no ToolExecutionService (TES)."""
        try:
            from services.tool_execution_service import ToolExecutionService, ToolContext

            context = context or {}
            chat_service = context.get("chat_service")
            session_id = context.get("session_id")
            mensagem_original = context.get("mensagem_original")

            tes = getattr(chat_service, "tool_execution_service", None) if chat_service else None
            if not tes:
                tes = ToolExecutionService(tool_context=ToolContext())

            # Garantir que o ToolContext tenha dados mínimos da sessão
            if getattr(tes, "tool_context", None):
                tes.tool_context.session_id = session_id or getattr(tes.tool_context, "session_id", None)
                tes.tool_context.mensagem_original = mensagem_original or getattr(tes.tool_context, "mensagem_original", None)

                # ✅ CRÍTICO: permitir Pending Intents no preview (fonte da verdade no SQLite)
                if chat_service and hasattr(chat_service, "confirmation_handler"):
                    tes.tool_context.confirmation_handler = getattr(chat_service, "confirmation_handler", None)

                # Melhor esforço para limpeza de texto (mantém comportamento do chat)
                if chat_service and hasattr(chat_service, "_limpar_frases_problematicas"):
                    tes.tool_context.limpar_frases_problematicas = getattr(chat_service, "_limpar_frases_problematicas", None)

            resultado = tes.executar_tool(tool_name, arguments)
            if resultado is None:
                return {
                    "sucesso": False,
                    "erro": "SEM_HANDLER_TES",
                    "resposta": f'❌ Tool "{tool_name}" não tem handler no ToolExecutionService.'
                }
            return resultado
        except Exception as e:
            logger.error(f"❌ Erro ao delegar para ToolExecutionService ({tool_name}): {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": str(e),
                "resposta": f"❌ Erro ao executar {tool_name}: {str(e)}",
            }
    
    def _listar_noticias_siscomex(
        self,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Lista notícias do Siscomex.
        
        Args:
            arguments: {
                'fonte': str (opcional) - 'importacao' ou 'sistemas'
                'limite': int (opcional) - número máximo de notícias (padrão: 20)
                'dias': int (opcional) - número de dias retroativos
            }
            context: Contexto adicional (opcional)
        
        Returns:
            Dict com resultado contendo lista de notícias formatada
        """
        try:
            # Extrair argumentos
            fonte_arg = arguments.get('fonte', '').lower() if arguments.get('fonte') else None
            limite = arguments.get('limite', 20)
            dias = arguments.get('dias')
            
            # Normalizar fonte
            fonte = None
            if fonte_arg:
                if 'importacao' in fonte_arg or 'importação' in fonte_arg:
                    fonte = 'siscomex_importacao'
                elif 'sistema' in fonte_arg:
                    fonte = 'siscomex_sistemas'
            
            # Buscar notícias
            # ✅ Refinamento (18/01/2026): quando fonte não é especificada, trazer Importação + Sistemas
            # em seções separadas, para não ficar "parecendo" que só existe uma fonte.
            noticias_importacao = []
            noticias_sistemas = []
            if fonte is None:
                try:
                    limite_total = int(limite)
                except Exception:
                    limite_total = 20
                limite_import = (limite_total + 1) // 2
                limite_sist = limite_total // 2

                noticias_importacao = self.noticia_repository.listar_noticias(
                    fonte='siscomex_importacao',
                    limite=limite_import,
                    dias_retroativos=dias
                )
                noticias_sistemas = self.noticia_repository.listar_noticias(
                    fonte='siscomex_sistemas',
                    limite=limite_sist,
                    dias_retroativos=dias
                )
                noticias = noticias_importacao + noticias_sistemas
            else:
                noticias = self.noticia_repository.listar_noticias(
                    fonte=fonte,
                    limite=limite,
                    dias_retroativos=dias
                )
            
            if not noticias:
                return {
                    'sucesso': True,
                    'resposta': '📰 Nenhuma notícia encontrada do Siscomex.',
                    'dados': {'noticias': [], 'noticias_importacao': [], 'noticias_sistemas': []}
                }
            
            # Formatar resposta
            fonte_nome = {
                'siscomex_importacao': 'Importação',
                'siscomex_sistemas': 'Sistemas'
            }
            
            # ⚠️ IMPORTANTE: manter formatação simples (texto puro + URL explícita)
            # para garantir que o frontend renderize sempre e permita click/copy do link.
            resposta = f"📰 {len(noticias)} notícia(s) do Siscomex\n\n"

            def _formatar_lista(secao_nome: str, lista: list):
                nonlocal resposta
                if not lista:
                    return
                resposta += f"📌 {secao_nome}\n\n"
                for i, noticia in enumerate(lista, 1):
                    # Garantir que título sempre apareça
                    titulo = noticia.get('titulo', 'Sem título')
                    if not titulo or titulo.strip() == '':
                        titulo = 'Sem título'
                    
                    # Formatar data (preferir data_publicacao; se não houver, não inventar "hoje")
                    data_str = None
                    if noticia.get('data_publicacao'):
                        try:
                            data_raw = noticia['data_publicacao']
                            if isinstance(data_raw, str):
                                from dateutil import parser
                                data_obj = parser.parse(data_raw)
                                data_str = data_obj.strftime('%d/%m/%Y')
                            elif hasattr(data_raw, 'strftime'):
                                data_str = data_raw.strftime('%d/%m/%Y')
                        except Exception as e:
                            logger.debug(f"Erro ao formatar data: {e}, data_raw: {noticia.get('data_publicacao')}")
                    
                    fonte_display = fonte_nome.get(noticia.get('fonte', ''), noticia.get('fonte', 'Siscomex'))
                    
                    resposta += f"{i}. {titulo}\n"
                    if data_str:
                        resposta += f"   📅 {data_str} | 📂 {fonte_display}\n"
                    else:
                        resposta += f"   📂 {fonte_display}\n"
                    
                    if noticia.get('descricao'):
                        descricao = (noticia.get('descricao') or '').strip()
                        if descricao:
                            if len(descricao) > 200:
                                descricao = descricao[:200] + "..."
                            resposta += f"   {descricao}\n"
                    
                    if noticia.get('link'):
                        resposta += f"   🔗 {noticia['link']}\n"
                    
                    resposta += "\n"

            if fonte is None:
                _formatar_lista("Importação", noticias_importacao)
                _formatar_lista("Sistemas", noticias_sistemas)
            else:
                _formatar_lista(fonte_nome.get(fonte, 'Siscomex'), noticias)
            
            # Adicionar resumo
            if fonte is None:
                total_import = self.noticia_repository.contar_noticias(fonte='siscomex_importacao')
                total_sist = self.noticia_repository.contar_noticias(fonte='siscomex_sistemas')
                resposta += f"💡 Totais: Importação={total_import} | Sistemas={total_sist}\n"
                resposta += "💡 Dica: peça \"notícias importação\" ou \"notícias sistemas\" para filtrar.\n"
                total = total_import + total_sist
            else:
                total = self.noticia_repository.contar_noticias(fonte=fonte)
                if total > len(noticias):
                    resposta += f"\n💡 Mostrando {len(noticias)} de {total} notícia(s) total(is)."
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'noticias': noticias,
                    'total': total,
                    'mostradas': len(noticias),
                    'noticias_importacao': noticias_importacao,
                    'noticias_sistemas': noticias_sistemas,
                }
            }
            
        except Exception as e:
            logger.error(f'Erro ao listar notícias: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar notícias: {str(e)}'
            }
