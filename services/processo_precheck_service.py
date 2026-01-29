import re
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from services.chat_service import ChatService

from services.processo_status_service import ProcessoStatusService
from services.context_service import salvar_contexto_sessao, buscar_contexto_sessao
from services.di_detalhada_service import DiDetalhadaService
from services.utils.processo_helpers import eh_pergunta_painel, eh_followup_processo, eh_pergunta_conceitual

# Import condicional para evitar erro se db_manager não estiver disponível
try:
    from db_manager import verificar_categoria_processo
except ImportError:
    verificar_categoria_processo = None

logger = logging.getLogger(__name__)


class ProcessoPrecheckService:
    """Serviço especializado em prechecks relacionados a processos de importação.
    
    Responsável por:
    - Situação/detalhe de processo com número explícito
    - Follow-up contextual de processo (ex.: "e a DI?", "e a DUIMP?")
    """

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service
        self.processo_status_service = ProcessoStatusService()

    def precheck_situacao_processo(
        self,
        mensagem: str,
        mensagem_lower: str,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Precheck para perguntas de situação/detalhe de processo.

        Exemplos:
        - "como está o vdm.0004/25?"
        - "situação do ALH.0168/25"
        - "detalhe do MSS.0003/25"
        
        ⚠️ REGRA: NÃO processa perguntas de painel/visão geral (ex: "como estão os MV5?").
        """
        # ✅ REGRA 1: Se for pergunta de painel, NÃO processar aqui
        if eh_pergunta_painel(mensagem_lower):
            logger.debug(
                f"[PROCESSO_PRECHECK] Pergunta de painel detectada - não processar como situação de processo específico: '{mensagem}'"
            )
            return None

        # Detectar se é pergunta de situação/detalhe
        eh_pergunta_situacao = bool(
            re.search(r"\b(situa[cç][aã]o|status|como\s+est[aã]o?|detalhe)\b", mensagem_lower)
        )
        if not eh_pergunta_situacao:
            return None

        # ✅ REGRA 2: Extrair processo usando helper do ChatService
        # Só processar se tiver processo EXPLÍCITO na mensagem
        processo_ref = self.chat_service._extrair_processo_referencia(mensagem)
        if not processo_ref:
            return None

        logger.info(
            f"[PROCESSO_PRECHECK] Situação de processo detectada. Processo: {processo_ref} | Mensagem: '{mensagem}'"
        )

        try:
            # Usar serviço dedicado para situação de processo
            resultado = self.processo_status_service.consultar_status_processo(
                processo_referencia=processo_ref,
                mensagem_original=mensagem,
            )
            
            # ✅ CRÍTICO: Sempre retornar resposta estruturada, mesmo se sucesso=False
            # Isso evita que a IA gere respostas genéricas incorretas
            if resultado and resultado.get("resposta"):
                logger.info(
                    f"[PROCESSO_PRECHECK] Resposta determinística de situação usada para {processo_ref} (sucesso={resultado.get('sucesso', False)})"
                )

                # ✅ REGRA 3: Salvar contexto de processo atual APENAS se:
                # - Tem session_id
                # - Processo foi mencionado explicitamente (já verificado acima)
                # - NÃO é pergunta de painel (já verificado acima)
                if session_id:
                    try:
                        salvar_contexto_sessao(
                            session_id=session_id,
                            tipo_contexto="processo_atual",
                            chave="referencia",
                            valor=processo_ref,
                            dados_adicionais={
                                "origem": "precheck_situacao_processo",
                            },
                        )
                        logger.debug(
                            f"[PROCESSO_PRECHECK] Contexto de processo_atual salvo: {processo_ref}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"[PROCESSO_PRECHECK] Erro ao salvar contexto de processo_atual ({processo_ref}): {e}"
                        )

                return {
                    "sucesso": resultado.get("sucesso", True),  # Usar sucesso do resultado, ou True por padrão
                    "resposta": resultado["resposta"],
                    # Mantém formato compatível para quem já usa tool_calls no front
                    "tool_calls": [
                        {
                            "name": "consultar_status_processo",
                            "arguments": {"processo_referencia": processo_ref},
                        }
                    ],
                    "_processado_precheck": True,
                }
            elif resultado and resultado.get("erro"):
                # Se tem erro mas não tem resposta, criar resposta estruturada do erro
                logger.warning(
                    f"[PROCESSO_PRECHECK] Erro ao consultar processo {processo_ref}: {resultado.get('erro')}"
                )
                return {
                    "sucesso": False,
                    "resposta": resultado.get("resposta", f"❌ **Erro ao consultar processo {processo_ref}:** {resultado.get('erro')}"),
                    "_processado_precheck": True,
                }
        except Exception as e:
            logger.error(
                f"[PROCESSO_PRECHECK] Erro ao executar consultar_status_processo no precheck: {e}",
                exc_info=True,
            )
            # Retornar resposta de erro estruturada em vez de None
            return {
                "sucesso": False,
                "resposta": f"❌ **Erro ao consultar processo {processo_ref}:** {str(e)}",
                "_processado_precheck": True,
            }

        return None

    def precheck_followup_processo(
        self,
        mensagem: str,
        mensagem_lower: str,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Detecta perguntas curtas de follow-up que dependem do último processo consultado.

        ✅ REGRA: Contexto só é usado se:
        - A mensagem NÃO tiver processo/categoria explícito (ex: "vdm.0004/25", "mv5")
        - NÃO for palavra-chave especial (NCM, extrato, criar DUIMP, etc.)
        - NÃO for pergunta de painel/visão geral
        - NÃO for pergunta conceitual (ex: "o que é uma DI?")
        
        Exemplos válidos de follow-up:
        - "qual a situação da DI?" (sem processo explícito)
        - "e a DUIMP?" (sem processo explícito)
        - "e a DI, como está?" (sem processo explícito)
        - "e o CE?" (sem processo explícito)
        
        Exemplos que NÃO devem usar contexto:
        - "situacao vdm.0005/25" (tem processo explícito - é outro assunto)
        - "como estao os mv5?" (pergunta de painel - é outro assunto)
        - "o que temos pra hoje?" (pergunta de painel - é outro assunto)
        - "qual a ncm?" (palavra-chave especial - não usa contexto)
        - "criar duimp" (palavra-chave especial - não usa contexto)
        - "o que é uma DI?" (pergunta conceitual - não usa contexto)
        - "vc sabe o que é um CE?" (pergunta conceitual - não usa contexto)
        """
        # ✅ REGRA 0: Se for pergunta conceitual, NÃO usar contexto de processo_atual
        # Deixar a IA responder genericamente sobre o conceito
        if eh_pergunta_conceitual(mensagem_lower):
            logger.debug(
                f"[PROCESSO_PRECHECK] Pergunta conceitual detectada - não usar contexto de processo_atual: '{mensagem}'"
            )
            return None
        
        if not session_id:
            return None

        # ✅ REGRA 1: Se for pergunta de painel, NÃO usar contexto de processo_atual
        if eh_pergunta_painel(mensagem_lower):
            logger.debug(
                f"[PROCESSO_PRECHECK] Pergunta de painel detectada - não usar contexto de processo_atual: '{mensagem}'"
            )
            return None

        # ✅ REGRA 2: Se a mensagem já tiver um número de processo explícito, não é follow-up
        try:
            proc_explicito = self.chat_service._extrair_processo_referencia(mensagem)
            if proc_explicito:
                logger.debug(f"[PROCESSO_PRECHECK] Processo explícito detectado ({proc_explicito}) - não usar contexto")
                return None
        except Exception:
            # Em caso de erro, seguir sem considerar processo explícito
            pass

        # ✅ REGRA 3: Verificar se menciona categoria de processo (ex: "mv5", "vdm", "alh")
        # Se mencionar categoria, é outro assunto, não follow-up
        if verificar_categoria_processo:
            try:
                # Padrão: 2-4 letras/números que podem ser categoria (ex: MV5, VDM, ALH, BND)
                padrao_categoria = r'\b([A-Z0-9]{2,4})\b'
                matches = re.findall(padrao_categoria, mensagem.upper())
                for match in matches:
                    if verificar_categoria_processo(match):
                        logger.debug(f"[PROCESSO_PRECHECK] Categoria explícita detectada ({match}) - não usar contexto")
                        return None
            except Exception as e:
                logger.debug(f"[PROCESSO_PRECHECK] Erro ao verificar categoria: {e}")

        # ✅ REGRA 4: Verificar se é palavra-chave especial que NÃO deve usar contexto
        # TODO (tuning futuro): Se aparecer muito "montar DUIMP", "rodar DUIMP", "gerar extrato",
        # pode valer incluir essas variações aqui
        palavras_chave_especiais = [
            r'\bncm\b',
            r'\bextrato\b',
            r'criar\s+duimp',
            r'criar\s+di',
            r'registrar\s+duimp',
            r'registrar\s+di',
            r'classificar',
            r'classifica[cç][aã]o',
        ]
        for padrao in palavras_chave_especiais:
            if re.search(padrao, mensagem_lower):
                logger.debug(f"[PROCESSO_PRECHECK] Palavra-chave especial detectada - não usar contexto")
                return None

        # ✅ REGRA 5: Verificar se é follow-up claro de processo
        # Deve mencionar contexto de documento/condição, não algo totalmente genérico
        eh_pergunta_situacao = bool(
            re.search(r"\b(situa[cç][aã]o|status|como\s+est[aã]o?|detalhe)\b", mensagem_lower)
        )
        menciona_di = bool(re.search(r"\bdi\b", mensagem_lower))
        menciona_duimp = "duimp" in mensagem_lower
        menciona_ce = bool(re.search(r"\bce\b", mensagem_lower))
        menciona_cct = "cct" in mensagem_lower
        menciona_documento = any(
            [
                menciona_di,
                menciona_duimp,
                menciona_ce,
                menciona_cct,
                "conhecimento" in mensagem_lower,
                "declara" in mensagem_lower,
            ]
        )

        # Também considerar mensagens muito curtas como "e a DI?", "e a DUIMP?"
        # Limite aumentado para 80 chars para capturar variações como "e a DI, me traz a situação?"
        eh_mensagem_curta = len(mensagem_lower) <= 80 and mensagem_lower.endswith("?")

        # ✅ REGRA 6: Usar helper para verificar se é follow-up claro
        if not (eh_followup_processo(mensagem_lower) or (eh_pergunta_situacao or (menciona_documento and eh_mensagem_curta))):
            return None

        # Buscar último processo_atual no contexto de sessão
        try:
            contextos = buscar_contexto_sessao(
                session_id=session_id,
                tipo_contexto="processo_atual",
            )
        except Exception as e:
            logger.warning(f"[PROCESSO_PRECHECK] Erro ao buscar contexto de sessão: {e}")
            return None

        if not contextos:
            return None

        processo_ref = contextos[0].get("valor")
        if not processo_ref:
            return None

        # Se a pergunta é sobre DI ou DUIMP, tratar como equivalente (ambas nacionalizam o processo)
        if menciona_di or menciona_duimp:
            logger.info(
                f"[PROCESSO_PRECHECK] Follow-up de declaração (DI/DUIMP) detectado. Usando processo_atual do contexto: {processo_ref} | Mensagem: '{mensagem}'"
            )
            try:
                # 1. Tentar buscar DI primeiro
                di_service = DiDetalhadaService()
                di_info = di_service.obter_di_detalhada_por_processo(processo_ref)
                
                # 2. Se não encontrou DI, tentar buscar DUIMP via SQL Server
                if not di_info:
                    try:
                        from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                        processo_consolidado = buscar_processo_consolidado_sql_server(processo_ref)
                        if processo_consolidado and processo_consolidado.get("duimp"):
                            duimp_data = processo_consolidado["duimp"]
                            di_info = {
                                "numero_di": duimp_data.get("numero") or "N/A",
                                "situacao": duimp_data.get("situacao") or "N/A",
                                "canal": duimp_data.get("canal") or "N/A",
                                "data_desembaraco": duimp_data.get("data_ultimo_evento") or "N/A",
                                "data_registro": duimp_data.get("data_registro") or "N/A",
                                "tipo": "DUIMP",  # Marcar que é DUIMP, não DI
                            }
                    except Exception as e:
                        logger.debug(f"[PROCESSO_PRECHECK] Erro ao buscar DUIMP via SQL Server: {e}")
                
                # 3. Se ainda não encontrou, tentar buscar DUIMP via SQLite
                if not di_info:
                    try:
                        import sqlite3
                        from db_manager import get_db_connection
                        conn = get_db_connection()
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT numero, versao, status, ambiente, criado_em, payload_completo
                            FROM duimps
                            WHERE processo_referencia = ? AND ambiente = 'producao'
                            ORDER BY CAST(versao AS INTEGER) DESC, criado_em DESC
                            LIMIT 1
                        ''', (processo_ref,))
                        row = cursor.fetchone()
                        conn.close()
                        
                        if row:
                            # Tentar extrair situação do payload se disponível
                            situacao_duimp = row['status'] or "N/A"
                            if row.get('payload_completo'):
                                try:
                                    import json
                                    payload = json.loads(row['payload_completo']) if isinstance(row['payload_completo'], str) else row['payload_completo']
                                    if isinstance(payload, dict):
                                        situacao_obj = payload.get('situacao', {})
                                        if isinstance(situacao_obj, dict):
                                            situacao_duimp = situacao_obj.get('situacaoDuimp', '') or situacao_duimp
                                except:
                                    pass
                            
                            di_info = {
                                "numero_di": row['numero'],
                                "situacao": situacao_duimp,
                                "canal": "N/A",  # DUIMP do SQLite pode não ter canal facilmente
                                "data_desembaraco": "N/A",
                                "data_registro": row['criado_em'] or "N/A",
                                "tipo": "DUIMP",
                            }
                    except Exception as e:
                        logger.debug(f"[PROCESSO_PRECHECK] Erro ao buscar DUIMP via SQLite: {e}")
                
                # 4. Se encontrou DI ou DUIMP, formatar resposta focada
                if di_info:
                    tipo_declaracao = di_info.get("tipo", "DI")
                    numero = di_info.get("numero_di") or "N/A"
                    situacao = di_info.get("situacao") or "N/A"
                    canal = di_info.get("canal") or "N/A"
                    data_desembaraco = di_info.get("data_desembaraco") or "N/A"
                    data_registro = di_info.get("data_registro") or "N/A"

                    resposta = f"📄 **{tipo_declaracao} do processo {processo_ref}**\n\n"
                    resposta += f"**Número:** {numero}\n"
                    resposta += f"**Situação:** {situacao}\n"
                    if canal and canal != "N/A":
                        resposta += f"**Canal:** {canal}\n"
                    if data_registro != "N/A":
                        resposta += f"**Data de Registro:** {data_registro}\n"
                    if data_desembaraco != "N/A":
                        resposta += f"**Data de Desembaraço:** {data_desembaraco}\n"

                    # Opcional: anexar resumo completo do processo para manter riqueza de detalhes
                    try:
                        resultado_proc = self.processo_status_service.consultar_status_processo(
                            processo_referencia=processo_ref,
                            mensagem_original=mensagem,
                        )
                        if resultado_proc and resultado_proc.get("sucesso") and resultado_proc.get("resposta"):
                            resposta += "\n\n---\n\n"
                            resposta += resultado_proc["resposta"]
                    except Exception as e:
                        logger.debug(f"[PROCESSO_PRECHECK] Erro ao anexar resumo completo do processo {processo_ref}: {e}")

                    return {
                        "sucesso": True,
                        "resposta": resposta,
                        "tool_calls": [
                            {
                                "name": "consultar_status_processo",
                                "arguments": {"processo_referencia": processo_ref},
                            }
                        ],
                        "_processado_precheck": True,
                        "_usou_contexto_processo_atual": True,
                        "_resposta_focada_declaracao": True,
                    }
            except Exception as e:
                logger.error(
                    f"[PROCESSO_PRECHECK] Erro ao obter declaração (DI/DUIMP) para {processo_ref}: {e}",
                    exc_info=True,
                )

        # Caso geral: repetir situação completa do processo (comportamento atual)
        logger.info(
            f"[PROCESSO_PRECHECK] Follow-up de processo detectado. Usando processo_atual do contexto: {processo_ref} | Mensagem: '{mensagem}'"
        )

        try:
            resultado = self.processo_status_service.consultar_status_processo(
                processo_referencia=processo_ref,
                mensagem_original=mensagem,
            )
            if resultado and resultado.get("sucesso") and resultado.get("resposta"):
                return {
                    "sucesso": True,
                    "resposta": resultado["resposta"],
                    "tool_calls": [
                        {
                            "name": "consultar_status_processo",
                            "arguments": {"processo_referencia": processo_ref},
                        }
                    ],
                    "_processado_precheck": True,
                    "_usou_contexto_processo_atual": True,
                }
        except Exception as e:
            logger.error(
                f"[PROCESSO_PRECHECK] Erro ao executar consultar_status_processo (follow-up) para {processo_ref}: {e}",
                exc_info=True,
            )

        return None

