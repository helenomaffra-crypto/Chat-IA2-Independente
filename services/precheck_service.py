import re
import logging
import os
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from services.chat_service import ChatService

from services.email_precheck_service import EmailPrecheckService
from services.processo_precheck_service import ProcessoPrecheckService
from services.ncm_precheck_service import NcmPrecheckService
from services.legislacao_precheck_service import LegislacaoPrecheckService
from services.intent_policy_service import IntentPolicyService

logger = logging.getLogger(__name__)


class PrecheckService:
    """Prechecks determinísticos antes de chamar a IA.

    Responsável por:
    - Situação/detalhe de processo (delegado para ProcessoPrecheckService)
    - Consulta de NCM no TECwin (delegado para NcmPrecheckService)
    - Identificar perguntas de NCM para não acionar lógica de categoria de processo
    - Comandos de envio de email (delegado para EmailPrecheckService)
    - Importação de legislação (delegado para LegislacaoPrecheckService)
    """

    def __init__(self, chat_service: "ChatService") -> None:
        # Referência ao ChatService para reutilizar helpers internos
        self.chat_service = chat_service
        # Serviços especializados
        self.email_precheck = EmailPrecheckService(chat_service)
        self.processo_precheck = ProcessoPrecheckService(chat_service)
        self.ncm_precheck = NcmPrecheckService(chat_service)
        self.legislacao_precheck = LegislacaoPrecheckService(chat_service)
        self.intent_policy = IntentPolicyService(chat_service)

    def tentar_responder_sem_ia(
        self,
        mensagem: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        nome_usuario: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Tenta responder a mensagem sem chamar a IA.

        Retorna um dict de resposta (mesmo formato do ChatService) ou None.
        """
        historico = historico or []
        mensagem_lower = mensagem.lower().strip()

        # ✅ NOVO (28/01/2026): Vendas (Make/Spalla) — roteamento determinístico para "por NF"
        # Evita depender da IA para escolher entre:
        # - consultar_vendas_make (agregado)
        # - consultar_vendas_nf_make (lista de documentos)
        #
        # Regra:
        # - Se o usuário pedir "vendas ..." (lista) e NÃO for pergunta de total ("quanto/total"),
        #   chamamos diretamente consultar_vendas_nf_make.
        # - Se o usuário pedir "quais X em atraso/vencidas em <mês/ano>", também roteia para modo cobrança.
        try:
            import calendar
            from datetime import datetime, timedelta

            # Meses (usado tanto para "vendas ..." quanto para "quais X em atraso em jan/26")
            meses = {
                "janeiro": 1,
                "jan": 1,
                "fevereiro": 2,
                "fev": 2,
                "marco": 3,
                "março": 3,
                "mar": 3,
                "abril": 4,
                "abr": 4,
                "maio": 5,
                "mai": 5,
                "junho": 6,
                "jun": 6,
                "julho": 7,
                "jul": 7,
                "agosto": 8,
                "ago": 8,
                "setembro": 9,
                "set": 9,
                "outubro": 10,
                "out": 10,
                "novembro": 11,
                "nov": 11,
                "dezembro": 12,
                "dez": 12,
            }

            def _parse_data_br_strict(s: str) -> Optional[datetime.date]:
                """
                Parse estrito para datas BR:
                - DD/MM/AAAA ou DD/MM/AA
                - DD-MM-AAAA ou DD-MM-AA
                Retorna date ou None se inválida.
                """
                if not s:
                    return None
                m = re.match(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2}|\d{4})$", s.strip())
                if not m:
                    return None
                dd = int(m.group(1))
                mm = int(m.group(2))
                yy_raw = m.group(3)
                yy = int(yy_raw)
                if len(yy_raw) == 2:
                    yy = 2000 + yy if yy <= 79 else 1900 + yy
                try:
                    return datetime(yy, mm, dd).date()
                except Exception:
                    return None

            # Extrair range de datas para vendas (prioridade sobre mês/ano)
            # Ex.: "vendas rastreador 01/01/25 a 30/06/25"
            m_range_vendas = re.search(
                r"\b(?:de\s+)?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s*(?:a|até|ate|\-)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b",
                mensagem_lower,
            )
            inicio_range_iso = None
            fim_range_iso_exclusivo = None
            if m_range_vendas:
                di = (m_range_vendas.group(1) or "").strip()
                df = (m_range_vendas.group(2) or "").strip()
                di_dt = _parse_data_br_strict(di)
                df_dt = _parse_data_br_strict(df)
                if not di_dt:
                    return {
                        "resposta": f"❌ Data inicial inválida: `{di}`. Use `DD/MM/AA` ou `DD/MM/AAAA` (ex.: `01/01/25`).",
                        "acao": "resposta_direta",
                        "_processado_precheck": True,
                    }
                if not df_dt:
                    return {
                        "resposta": (
                            f"❌ Data final inválida: `{df}`.\n\n"
                            "💡 Ex.: junho tem 30 dias, então use `30/06/25`.\n"
                            "Formato aceito: `DD/MM/AA` ou `DD/MM/AAAA`."
                        ),
                        "acao": "resposta_direta",
                        "_processado_precheck": True,
                    }
                if df_dt < di_dt:
                    return {
                        "resposta": f"❌ Período inválido: a data final `{df}` é menor que a inicial `{di}`.",
                        "acao": "resposta_direta",
                        "_processado_precheck": True,
                    }
                inicio_range_iso = di_dt.isoformat()
                # fim exclusivo = dia seguinte ao "até"
                fim_range_iso_exclusivo = (df_dt + timedelta(days=1)).isoformat()

            # Extrair mês/ano (aceita: "janeiro 2026", "janeiro 26", "jan 2026", "jan/26", "01/2026", "01/26")
            m_mes = re.search(
                r"\b("
                r"janeiro|jan|"
                r"fevereiro|fev|"
                r"mar[cç]o|mar|"
                r"abril|abr|"
                r"maio|mai|"
                r"junho|jun|"
                r"julho|jul|"
                r"agosto|ago|"
                r"setembro|set|"
                r"outubro|out|"
                r"novembro|nov|"
                r"dezembro|dez"
                r")\b(?:\s+de)?\s*(?:/|\s)\s*(\d{2}|\d{4})\b"
                r"|"
                # ⚠️ IMPORTANTE: não capturar "01/01/25" como mês/ano (01/01) -> 2001.
                # O negative lookahead evita match quando existe outro "/DD" em seguida.
                r"\b(0?[1-9]|1[0-2])\s*/\s*(\d{2}|\d{4})\b(?!\s*/\s*\d{1,2})",
                mensagem_lower,
            )
            periodo_mes = None
            if m_mes and not m_range_vendas:
                mes_num = None
                ano = None
                # grupos 1-2: mês por nome/abreviação
                if m_mes.group(1) and m_mes.group(2):
                    mes_nome = m_mes.group(1)
                    ano_raw = m_mes.group(2)
                    try:
                        ano_int = int(ano_raw)
                        if len(ano_raw) == 2:
                            ano_int = 2000 + ano_int if ano_int <= 79 else 1900 + ano_int
                        ano = ano_int
                    except Exception:
                        ano = None
                    mes_key = mes_nome.replace("ç", "c")
                    mes_num = meses.get(mes_key, meses.get(mes_nome, None))
                # grupos 3-4: mês numérico
                elif m_mes.group(3) and m_mes.group(4):
                    try:
                        mes_num = int(m_mes.group(3))
                    except Exception:
                        mes_num = None
                    ano_raw = m_mes.group(4)
                    try:
                        ano_int = int(ano_raw)
                        if len(ano_raw) == 2:
                            ano_int = 2000 + ano_int if ano_int <= 79 else 1900 + ano_int
                        ano = ano_int
                    except Exception:
                        ano = None

                if mes_num and ano:
                    periodo_mes = f"{ano:04d}-{mes_num:02d}"

            # Caso A) "vendas ..." (lista por NF)
            if re.search(r"^\s*vendas?\b", mensagem_lower) and not re.search(r"\bquanto\b|\btotal\b", mensagem_lower):
                termo = None
                m_termo = re.search(r"^\s*vendas?\s+(.+)$", mensagem_lower)
                if m_termo:
                    termo_raw = m_termo.group(1)
                    termo_raw = re.split(r"\s+em\s+", termo_raw, maxsplit=1)[0].strip()
                    try:
                        if m_mes:
                            termo_raw = termo_raw.replace(m_mes.group(0), " ").strip()
                    except Exception:
                        pass
                    try:
                        if m_range_vendas:
                            termo_raw = termo_raw.replace(m_range_vendas.group(0), " ").strip()
                    except Exception:
                        pass
                    # ✅ Remover palavras de "cobrança" do termo (para não virar parte do LIKE)
                    # Ex.: "vendas atrasadas vdm jan 26" -> termo="vdm" + modo="cobranca"
                    termo_raw = re.sub(
                        r"\b("
                        r"atrasad[oa]s?|em\s+atraso|vencid[oa]s?|inadimpl\w*|em\s+aberto|nao\s+pag(?:ou|aram|ar)?"
                        r")\b",
                        " ",
                        termo_raw,
                        flags=re.IGNORECASE,
                    ).strip()
                    termo_raw = re.sub(
                        r"\b("
                        r"janeiro|jan|fevereiro|fev|mar[cç]o|mar|abril|abr|maio|mai|junho|jun|julho|jul|"
                        r"agosto|ago|setembro|set|outubro|out|novembro|nov|dezembro|dez"
                        r")\b(?:\s+de)?\s*(?:/|\s)\s*\d{2,4}\b",
                        " ",
                        termo_raw,
                    ).strip()
                    termo_raw = re.sub(r"\b(0?[1-9]|1[0-2])\s*/\s*\d{2,4}\b", " ", termo_raw).strip()
                    # remover datas soltas (DD/MM/AA etc.) para não virarem tokens do termo
                    termo_raw = re.sub(r"\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b", " ", termo_raw).strip()
                    termo_raw = termo_raw.replace(" ate ", " ").replace(" até ", " ").replace(" a ", " ")
                    termo_raw = termo_raw.replace("por nf", "").replace("nf", "").strip()
                    termo_raw = re.sub(r"\s{2,}", " ", termo_raw).strip()
                    termo = termo_raw if termo_raw else None

                if (inicio_range_iso and fim_range_iso_exclusivo and termo) or (periodo_mes and termo):
                    pediu_cobranca = bool(
                        re.search(r"\bvencid|\binadimpl|\bem\s+aberto|\bem\s+atraso|\batrasad|\bnao\s+pag", mensagem_lower)
                    )
                    args = {"termo": termo, "top": 500}
                    if inicio_range_iso and fim_range_iso_exclusivo:
                        args["inicio"] = inicio_range_iso
                        args["fim"] = fim_range_iso_exclusivo
                    else:
                        args["periodo_mes"] = periodo_mes
                    if pediu_cobranca:
                        args["modo"] = "cobranca"
                    resultado = self.chat_service._executar_funcao_tool(
                        "consultar_vendas_nf_make",
                        args,
                        mensagem_original=mensagem,
                        session_id=session_id,
                    )
                    if isinstance(resultado, dict) and resultado.get("resposta"):
                        return {"resposta": resultado.get("resposta"), "acao": "resposta_direta", "_processado_precheck": True}

            # Caso B) "quais X em atraso/vencidas em <mês/ano>" (atalho para cobrança)
            if periodo_mes and re.search(r"\bem\s+atraso|\bvencid|\binadimpl|\bem\s+aberto|\batrasad", mensagem_lower):
                # Evitar confundir com pedidos de processo/ETA (domínio processos)
                if not re.search(r"\b(eta|navio|porto|chegada|carga|processo|ce|cct|di|duimp|dta|canal)\b", mensagem_lower):
                    termo = None
                    m = re.search(
                        r"^\s*(?:quais|qual|lista|listar|mostra|mostre)\s+(?:s[ãa]o\s+)?(?:as\s+|os\s+)?(.+?)\s+(?:em\s+atraso|vencid\w*|inadimpl\w*|em\s+aberto|atrasad\w*)\b",
                        mensagem_lower,
                    )
                    cand = (m.group(1) if m else "").strip()
                    # limpar palavras comuns
                    cand = re.sub(r"\b(vendas?|nfs?|nota\s+fiscal|notas\s+fiscais|por\s+nf)\b", " ", cand).strip()
                    cand = re.sub(r"\s{2,}", " ", cand).strip()

                    if cand:
                        # pegar o último token "relevante" (ex: "nfs vdm" -> "vdm")
                        toks = re.findall(r"\b[a-z0-9]{2,8}\b", cand)
                        termo = toks[-1] if toks else None
                    if not termo:
                        # fallback: procurar um token curto tipo "vdm/dmd/..." na mensagem
                        toks = re.findall(r"\b[a-z]{2,5}\b", mensagem_lower)
                        stop = set(meses.keys()) | {
                            "quais", "qual", "em", "atraso", "atrasada", "atrasadas", "atrasado", "atrasados",
                            "vencida", "vencidas", "vencido", "vencidos",
                            "inadimplente", "inadimplentes",
                            "de", "do", "da", "no", "na",
                            # stopwords comuns que podem virar "termo" errado (ex.: "o que tem ...")
                            "o", "a", "os", "as", "que", "tem", "têm",
                        }
                        termo = next((t for t in toks if t not in stop), None)

                    if termo:
                        args = {"periodo_mes": periodo_mes, "termo": termo, "top": 500, "modo": "cobranca"}
                        resultado = self.chat_service._executar_funcao_tool(
                            "consultar_vendas_nf_make",
                            args,
                            mensagem_original=mensagem,
                            session_id=session_id,
                        )
                        if isinstance(resultado, dict) and resultado.get("resposta"):
                            return {"resposta": resultado.get("resposta"), "acao": "resposta_direta", "_processado_precheck": True}

            # Caso C) "o que tem em atraso do X em <mês/ano>" (atalho para cobrança)
            # Ex.: "o que tem em atraso do vdm em jan 26"
            if periodo_mes and re.search(r"\b(o\s+que\s+tem|oq\s+tem)\b", mensagem_lower) and re.search(
                r"\bem\s+atraso|\bvencid|\binadimpl|\bem\s+aberto|\batrasad", mensagem_lower
            ):
                if not re.search(r"\b(eta|navio|porto|chegada|carga|processo|ce|cct|di|duimp|dta|canal)\b", mensagem_lower):
                    # Tentar capturar o termo após "do/da/de"
                    termo = None
                    m = re.search(r"\b(?:do|da|de)\s+([a-z]{2,6})\b", mensagem_lower)
                    if m:
                        termo = (m.group(1) or "").strip()
                    if termo and termo not in meses and termo not in {"o", "a", "os", "as", "que", "tem", "têm"}:
                        args = {"periodo_mes": periodo_mes, "termo": termo, "top": 500, "modo": "cobranca"}
                        resultado = self.chat_service._executar_funcao_tool(
                            "consultar_vendas_nf_make",
                            args,
                            mensagem_original=mensagem,
                            session_id=session_id,
                        )
                        if isinstance(resultado, dict) and resultado.get("resposta"):
                            return {"resposta": resultado.get("resposta"), "acao": "resposta_direta", "_processado_precheck": True}
        except Exception as e_vendas:
            logger.debug(f"[PRECHECK] Erro ao rotear vendas por NF: {e_vendas}")

        # ✅ NOVO (22/01/2026): "O que posso fazer?" (ajuda da UI)
        try:
            if re.search(r"^\s*o\s+que\s+voce\s+pode\s+fazer\??\s*$", mensagem_lower) or re.search(
                r"^\s*o\s+que\s+posso\s+fazer\??\s*$", mensagem_lower
            ):
                from services.help_service import obter_texto_o_que_posso_fazer

                return {"resposta": obter_texto_o_que_posso_fazer(), "acao": "resposta_direta"}
        except Exception as e_help:
            logger.debug(f"[PRECHECK] Erro ao montar help: {e_help}")

        # ✅ NOVO (22/01/2026): Histórico de pagamentos AFRMM (Mercante)
        # Ex.: "histórico do afrmm do bgr.0080/25"
        # Resposta determinística: consulta persistência (SQL Server/SQLite) e retorna links de comprovante.
        try:
            if "afrmm" in mensagem_lower and ("hist" in mensagem_lower or "comprov" in mensagem_lower):
                # Extrair processo (se houver) do texto
                m_proc = re.search(r"\b([a-z]{3}\.\d{4}/\d{2})\b", mensagem_lower, flags=re.IGNORECASE)
                processo_ref = m_proc.group(1).upper() if m_proc else None

                from services.mercante_afrmm_pagamentos_service import MercanteAfrmmPagamentosService

                svc = MercanteAfrmmPagamentosService()
                resultado = svc.listar(processo_referencia=processo_ref, limite=10)
                if not resultado or not resultado.get("sucesso"):
                    return {
                        "resposta": (resultado or {}).get("resposta") or "❌ Não consegui consultar o histórico de AFRMM agora.",
                        "acao": "resposta_direta",
                    }

                itens = ((resultado.get("dados") or {}).get("itens")) or []
                fonte = resultado.get("fonte") or "desconhecida"
                if not itens:
                    alvo = f" do processo **{processo_ref}**" if processo_ref else ""
                    return {
                        "resposta": f"ℹ️ Não encontrei pagamentos AFRMM registrados{alvo}. (fonte: {fonte})",
                        "acao": "resposta_direta",
                    }

                linhas = []
                titulo = f"📜 **Histórico AFRMM (Mercante){' — ' + processo_ref if processo_ref else ''}**"
                linhas.append(titulo)
                linhas.append(f"_Fonte: {fonte}_")
                linhas.append("")

                for i, item in enumerate(itens[:10], start=1):
                    created_at = item.get("created_at") or item.get("createdAt") or ""
                    ce = item.get("ce_mercante") or item.get("ceMercante") or ""
                    valor_total = item.get("valor_total_debito")
                    valor_afrmm = item.get("valor_afrmm")
                    screenshot_url = item.get("screenshot_url")

                    linhas.append(f"**{i}.** CE {ce} — {created_at}".strip())
                    if valor_total is not None:
                        try:
                            linhas.append(f"- Valor total: R$ {float(valor_total):,.2f}")
                        except Exception:
                            linhas.append(f"- Valor total: {valor_total}")
                    if valor_afrmm is not None:
                        try:
                            linhas.append(f"- Valor AFRMM: R$ {float(valor_afrmm):,.2f}")
                        except Exception:
                            linhas.append(f"- Valor AFRMM: {valor_afrmm}")
                    if screenshot_url:
                        linhas.append(f"- 🧾 Comprovante: [abrir imagem]({screenshot_url})")
                    linhas.append("")

                return {"resposta": "\n".join(linhas).strip(), "acao": "resposta_direta"}
        except Exception as e_afrmm_hist:
            logger.debug(f"[PRECHECK] Erro ao montar histórico AFRMM: {e_afrmm_hist}")

        # ✅ NOVO (19/01/2026): Follow-up determinístico do FECHAMENTO DO DIA
        # Ex.: "quais foram essas 10 movimentações?" / "detalhe as movimentações" / "quero as 10 completas"
        # Se houver relatório ativo do tipo fechamento_dia, abrir a seção 'movimentacoes' do relatório salvo.
        try:
            if session_id and ('movimenta' in mensagem_lower):
                pede_detalhe = bool(re.search(r'\b(quais|qual|detalh|detalhe|listar|lista|mostr|mostre|quero|complet)\b', mensagem_lower))
                if pede_detalhe:
                    from services.report_service import obter_active_report_info
                    info = obter_active_report_info(session_id, dominio='processos')
                    if info and info.get('tipo_relatorio') == 'fechamento_dia' and info.get('id'):
                        logger.info(f"[PRECHECK] Follow-up de fechamento detectado - abrindo movimentacoes (report_id={info.get('id')})")
                        return {
                            'tool_calls': [{
                                'function': {
                                    'name': 'buscar_secao_relatorio_salvo',
                                    'arguments': {
                                        'secao': 'movimentacoes',
                                        'report_id': info.get('id')
                                    }
                                }
                            }]
                        }
        except Exception as _e_fechamento_followup:
            logger.debug(f"[PRECHECK] Erro no follow-up de fechamento do dia: {_e_fechamento_followup}")

        # ✅ NOVO (20/01/2026): Follow-ups determinísticos do "O QUE TEMOS PRA HOJE"
        # Objetivo: responder rápido "em cima do relatório" (sem ir ao SQL Server) para filtros comuns.
        try:
            if session_id:
                # ✅ CORREÇÃO (20/01/2026): só usar relatório salvo se ele estiver VISÍVEL/recente no histórico
                # (evita "depende da ordem": usar um report antigo sem o usuário ter gerado na conversa atual)
                import json as _json
                from datetime import datetime as _dt
                from services.report_service import obter_last_visible_report_id

                report_id = None
                info = obter_last_visible_report_id(session_id, dominio='processos') or {}
                if info and info.get('tipo_relatorio') == 'o_que_tem_hoje' and info.get('id') and info.get('meta_json'):
                    meta = info.get('meta_json') or {}
                    try:
                        created_at = meta.get('created_at')
                        ttl_min = int(meta.get('ttl_min') or 60)
                        if created_at:
                            dt = _dt.fromisoformat(str(created_at))
                            age_min = (_dt.now(dt.tzinfo) - dt).total_seconds() / 60.0
                            if age_min <= ttl_min:
                                report_id = info.get('id')
                    except Exception:
                        report_id = None

                # Fallback extra: se o último assistente no histórico NÃO contém REPORT_META, não usar relatório salvo
                if report_id and historico:
                    try:
                        last_assistant = next((m for m in reversed(historico) if (m or {}).get('role') == 'assistant'), None)
                        txt = (last_assistant or {}).get('content') or ''
                        if '[REPORT_META:' not in txt:
                            report_id = None
                    except Exception:
                        pass

                ml = mensagem_lower

                # Se não há report válido, responder "ativos-first" sem exigir gerar relatório
                if not report_id:
                    if 'canal' in ml and ('verde' in ml or 'vermelh' in ml):
                        canal = 'Verde' if 'verde' in ml else 'Vermelho'
                        logger.info(f"[PRECHECK] Canal detectado sem relatório visível/recente - usando listar_dis_por_canal (canal={canal})")
                        return {
                            'tool_calls': [{
                                'function': {
                                    'name': 'listar_dis_por_canal',
                                    'arguments': {'canal': canal}
                                }
                            }]
                        }
                    if 'alerta' in ml and bool(re.search(r'\b(quais|qual|detalh|detalhe|listar|lista|mostr|mostre|ver)\b', ml)):
                        logger.info("[PRECHECK] Alertas detectado sem relatório visível/recente - usando listar_alertas_recentes")
                        return {'tool_calls': [{'function': {'name': 'listar_alertas_recentes', 'arguments': {}}}]}

                    if ('pronto' in ml and 'registro' in ml) or ('prontos' in ml and 'registro' in ml):
                        logger.info("[PRECHECK] Prontos para registro sem relatório visível/recente - usando listar_processos_prontos_registro")
                        return {'tool_calls': [{'function': {'name': 'listar_processos_prontos_registro', 'arguments': {}}}]}

                    if 'pend' in ml:
                        tipo = None
                        if 'frete' in ml:
                            tipo = 'Frete'
                        elif 'icms' in ml:
                            tipo = 'ICMS'
                        elif 'afrmm' in ml:
                            tipo = 'AFRMM'
                        elif 'lpco' in ml:
                            tipo = 'LPCO'
                        elif 'bloque' in ml:
                            tipo = 'Bloqueio CE'
                        logger.info(f"[PRECHECK] Pendências sem relatório visível/recente - usando listar_pendencias_ativas (tipo={tipo})")
                        args_p = {}
                        if tipo:
                            args_p['tipo_pendencia'] = tipo
                        return {'tool_calls': [{'function': {'name': 'listar_pendencias_ativas', 'arguments': args_p}}]}

                    if ('eta' in ml and ('atras' in ml or 'adiant' in ml)) or ('atras' in ml and 'dia' in ml):
                        tipo_mudanca = None
                        if 'atras' in ml:
                            tipo_mudanca = 'ATRASO'
                        elif 'adiant' in ml:
                            tipo_mudanca = 'ADIANTADO'
                        m = re.search(r'(\d{1,3})\s*(?:dia|dias)', ml)
                        min_dias = int(m.group(1)) if m else None
                        logger.info(f"[PRECHECK] ETA alterado sem relatório visível/recente - usando listar_eta_alterado (tipo={tipo_mudanca}, min_dias={min_dias})")
                        args_e = {}
                        if tipo_mudanca:
                            args_e['tipo_mudanca'] = tipo_mudanca
                        if min_dias is not None:
                            args_e['min_dias'] = min_dias
                        return {'tool_calls': [{'function': {'name': 'listar_eta_alterado', 'arguments': args_e}}]}

                    if 'duimp' in ml and 'rascunh' in ml and bool(re.search(r'\b(quais|qual|listar|lista|mostr|mostre|s[oó]|apenas)\b', ml)):
                        m2 = re.search(r'(\d{1,3})\s*(?:dia|dias)', ml)
                        min_age = int(m2.group(1)) if m2 else None
                        logger.info(f"[PRECHECK] DUIMPs rascunho sem relatório visível/recente - usando listar_duimps_em_analise (min_age={min_age})")
                        args_d = {'status_contains': 'rascunho'}
                        if min_age is not None:
                            args_d['min_age_dias'] = min_age
                        return {'tool_calls': [{'function': {'name': 'listar_duimps_em_analise', 'arguments': args_d}}]}

                    # Para outros filtros, sem relatório visível: deixar a IA decidir (evita respostas inconsistentes)
                    report_id = None

                if report_id:
                    ml = mensagem_lower

                    # ✅ NOVO (28/01/2026): Comandos "fuzzy" de filtro/agrupamento do relatório visível
                    # Garantia: chama filtrar_relatorio_fuzzy para acionar o planner (LangChain/AIService) e preservar report_id.
                    if any(x in ml for x in ('filtr', 'filtro', 'agrupe', 'agrupar', 'só ', 'so ')):
                        # Evitar capturar perguntas simples já cobertas pelos atalhos abaixo (canal/pendências/etc.)
                        # Ex.: "só canal verde" já tem atalho determinístico.
                        if not ('canal' in ml and ('verde' in ml or 'vermelh' in ml)) and 'pend' not in ml:
                            logger.info(f"[PRECHECK] Filtro/agrupamento fuzzy detectado - usando filtrar_relatorio_fuzzy (report_id={report_id})")
                            return {
                                'tool_calls': [{
                                    'function': {
                                        'name': 'filtrar_relatorio_fuzzy',
                                        'arguments': {
                                            'instrucao': mensagem,
                                            'report_id': report_id,
                                        }
                                    }
                                }]
                            }

                    # 1) Canal verde/vermelho (DIs)
                    if 'canal' in ml and ('verde' in ml or 'vermelh' in ml):
                        canal = 'Verde' if 'verde' in ml else 'Vermelho'
                        logger.info(f"[PRECHECK] Follow-up de dashboard detectado - canal {canal} (report_id={report_id})")
                        return {
                            'tool_calls': [{
                                'function': {
                                    'name': 'buscar_secao_relatorio_salvo',
                                    'arguments': {
                                        'secao': 'dis_analise',
                                        'canal': canal,
                                        'report_id': report_id,
                                    }
                                }
                            }]
                        }

                    # 2) Pendências por tipo (frete/icms/afrmm/lpco/bloqueio)
                    if 'pend' in ml:
                        tipo = None
                        if 'frete' in ml:
                            tipo = 'Frete'
                        elif 'icms' in ml:
                            tipo = 'ICMS'
                        elif 'afrmm' in ml:
                            tipo = 'AFRMM'
                        elif 'lpco' in ml:
                            tipo = 'LPCO'
                        elif 'bloque' in ml:
                            tipo = 'Bloqueio CE'
                        if tipo:
                            logger.info(f"[PRECHECK] Follow-up de dashboard detectado - pendencias {tipo} (report_id={report_id})")
                            return {
                                'tool_calls': [{
                                    'function': {
                                        'name': 'buscar_secao_relatorio_salvo',
                                        'arguments': {
                                            'secao': 'pendencias',
                                            'tipo_pendencia': tipo,
                                            'report_id': report_id,
                                        }
                                    }
                                }]
                            }

                    # 3) Prontos para registro
                    if ('pronto' in ml and 'registro' in ml) or ('prontos' in ml and 'registro' in ml):
                        logger.info(f"[PRECHECK] Follow-up de dashboard detectado - processos_prontos (report_id={report_id})")
                        return {
                            'tool_calls': [{
                                'function': {
                                    'name': 'buscar_secao_relatorio_salvo',
                                    'arguments': {
                                        'secao': 'processos_prontos',
                                        'report_id': report_id,
                                    }
                                }
                            }]
                        }

                    # 3.5) Alertas (atalho direto)
                    if 'alerta' in ml and bool(re.search(r'\b(quais|qual|detalh|detalhe|listar|lista|mostr|mostre|ver)\b', ml)):
                        logger.info(f"[PRECHECK] Follow-up de dashboard detectado - alertas (report_id={report_id})")
                        return {
                            'tool_calls': [{
                                'function': {
                                    'name': 'buscar_secao_relatorio_salvo',
                                    'arguments': {
                                        'secao': 'alertas',
                                        'report_id': report_id,
                                    }
                                }
                            }]
                        }

                    # 3.6) DIs desembaraçadas (filtrar status dentro da seção de DIs do relatório)
                    if 'di' in ml and 'desembara' in ml and bool(re.search(r'\b(quais|qual|listar|lista|mostr|mostre|s[oó]|apenas)\b', ml)):
                        logger.info(f"[PRECHECK] Follow-up de dashboard detectado - DIs desembaraçadas (report_id={report_id})")
                        return {
                            'tool_calls': [{
                                'function': {
                                    'name': 'buscar_secao_relatorio_salvo',
                                    'arguments': {
                                        'secao': 'dis_analise',
                                        'status_contains': 'desembara',
                                        'report_id': report_id,
                                    }
                                }
                            }]
                        }

                    # 3.7) DUIMPs em rascunho há > X dias
                    if 'duimp' in ml and 'rascunh' in ml and bool(re.search(r'\b(quais|qual|listar|lista|mostr|mostre|s[oó]|apenas)\b', ml)):
                        m2 = re.search(r'(\d{1,3})\s*(?:dia|dias)', ml)
                        min_age = int(m2.group(1)) if m2 else None
                        logger.info(f"[PRECHECK] Follow-up de dashboard detectado - DUIMPs rascunho (min_age={min_age}) (report_id={report_id})")
                        args = {
                            'secao': 'duimps_analise',
                            'status_contains': 'rascunho',
                            'report_id': report_id,
                        }
                        if min_age is not None:
                            args['min_age_dias'] = min_age
                        return {'tool_calls': [{'function': {'name': 'buscar_secao_relatorio_salvo', 'arguments': args}}]}

                    # 4) ETA alterado: só atrasos/adiantados e/ou acima de X dias
                    if ('eta' in ml and ('atras' in ml or 'adiant' in ml)) or ('atras' in ml and 'dia' in ml):
                        tipo_mudanca = None
                        if 'atras' in ml:
                            tipo_mudanca = 'ATRASO'
                        elif 'adiant' in ml:
                            tipo_mudanca = 'ADIANTADO'
                        # extrair número de dias se existir (ex.: "atraso > 7 dias")
                        m = re.search(r'(\d{1,3})\s*(?:dia|dias)', ml)
                        min_dias = int(m.group(1)) if m else None
                        logger.info(f"[PRECHECK] Follow-up de dashboard detectado - eta_alterado (tipo={tipo_mudanca}, min_dias={min_dias}) (report_id={report_id})")
                        args = {'secao': 'eta_alterado', 'report_id': report_id}
                        if tipo_mudanca:
                            args['tipo_mudanca'] = tipo_mudanca
                        if min_dias is not None:
                            args['min_dias'] = min_dias
                        return {'tool_calls': [{'function': {'name': 'buscar_secao_relatorio_salvo', 'arguments': args}}]}
        except Exception as _e_dash_followup:
            logger.debug(f"[PRECHECK] Erro no follow-up de dashboard: {_e_dash_followup}")

        # 0) ✅ NOVO: Detectar "continue o pagamento" e usar contexto salvo
        padroes_continuar_pagamento = [
            r'continue\s+(o\s+)?pagamento',
            r'continuar\s+(o\s+)?pagamento',
            r'confirmar\s+(o\s+)?pagamento',
            r'confirmar\s+boleto',
            r'efetivar\s+(o\s+)?pagamento',
            r'efetivar\s+boleto',
            r'autorizar\s+(o\s+)?pagamento',
            r'autorizar\s+boleto',
            r'pagar\s+(o\s+)?boleto',
            r'finalizar\s+(o\s+)?pagamento'
        ]
        for padrao in padroes_continuar_pagamento:
            if re.search(padrao, mensagem_lower):
                logger.info(f"[PRECHECK] Comando 'continuar pagamento' detectado - mensagem: '{mensagem_lower}'")
                logger.info(f"[PRECHECK] session_id disponível: {session_id is not None} (valor: {session_id})")
                if session_id:
                    try:
                        from services.context_service import buscar_contexto_sessao
                        contextos = buscar_contexto_sessao(
                            session_id=session_id,
                            tipo_contexto='pagamento_boleto'
                        )
                        if contextos:
                            contexto = contextos[0]
                            dados = contexto.get('dados_json', {})
                            if isinstance(dados, str):
                                import json
                                dados = json.loads(dados)
                            
                            payment_id = dados.get('payment_id') or contexto.get('valor')
                            valor = dados.get('valor')
                            
                            if payment_id and valor:
                                logger.info(f"[PRECHECK] ✅ Contexto de pagamento encontrado: payment_id={payment_id}, valor={valor}")
                                return {
                                    'tool_calls': [{
                                        'function': {
                                            'name': 'efetivar_bank_slip_payment_santander',
                                            'arguments': {
                                                'payment_id': payment_id,
                                                'payment_value': valor
                                                # agencia_origem e conta_origem serão obtidos do workspace
                                            }
                                        }
                                    }]
                                }
                            else:
                                logger.warning(f"[PRECHECK] ⚠️ Contexto de pagamento encontrado mas sem payment_id ou valor (payment_id={payment_id}, valor={valor})")
                        else:
                            logger.warning(f"[PRECHECK] ⚠️ Nenhum contexto de pagamento encontrado para session_id={session_id}, tipo='pagamento_boleto'")
                    except Exception as e:
                        logger.error(f"[PRECHECK] ❌ Erro ao buscar contexto de pagamento: {e}", exc_info=True)
                else:
                    logger.warning(f"[PRECHECK] ⚠️ session_id não disponível para buscar contexto de pagamento")
                break

        # 0.1) ✅ CRÍTICO: Pagamento AFRMM (Mercante) por comando direto
        # Motivo: evita depender de tool calling (limite 128 tools pode esconder `executar_pagamento_afrmm`)
        # e evita cair em "despesas do processo" quando o usuário quer pagar.
        try:
            if (
                "afrmm" in mensagem_lower
                and not re.search(r"\bhist|\bcomprov", mensagem_lower)  # não conflitar com "histórico/comprovante"
                and re.search(r"\b(pagar|pague|paga|quitar|quite|efetuar|efetue)\b", mensagem_lower)
            ):
                m_proc = re.search(r"\b([a-z]{3}\.\d{4}/\d{2})\b", mensagem_lower, flags=re.IGNORECASE)
                if m_proc:
                    processo_ref = m_proc.group(1).upper()
                    args: Dict[str, Any] = {"processo_referencia": processo_ref}
                    # parcela opcional: "parcela 2"
                    m_parc = re.search(r"\bparcela\s+(\d{1,3})\b", mensagem_lower)
                    if m_parc:
                        args["parcela"] = m_parc.group(1)
                    return {"tool_calls": [{"function": {"name": "executar_pagamento_afrmm", "arguments": args}}]}
        except Exception as e_afrmm_pay:
            logger.debug(f"[PRECHECK] Erro ao detectar pagar AFRMM: {e_afrmm_pay}")

        # 1) ✅ NOVO: Ver emails e detalhes de email (PRIORIDADE MÁXIMA ABSOLUTA)
        # Padrões para listar emails: "ver email", "ver emails", "ler email", "ler emails"
        padroes_ver_email = [
            r'^ver\s+email$',
            r'^ver\s+emails$',
            r'^ler\s+email$',
            r'^ler\s+emails$',
            # ✅ NOVO: imperativo comum ("leia meus emails")
            r'^leia\s+email$',
            r'^leia\s+emails$',
            # ✅ NOVO: variações comuns ("meus emails", "meus e-mails")
            r'^ver\s+meus\s+e-?mails$',
            r'^ler\s+meus\s+e-?mails$',
            r'^leia\s+meus\s+e-?mails$',
            r'^mostrar\s+meus\s+e-?mails$',
            r'^consultar\s+meus\s+e-?mails$',
            r'^mostrar\s+emails$',
            r'^quais\s+emails$',
            r'^verificar\s+emails$',
            r'^consultar\s+emails$',
            # ✅ NOVO: "de hoje"
            r'^(ver|ler|leia|mostrar|consultar|verificar)\s+(meus\s+)?e-?mails\s+de\s+hoje$',
            r'^(ver|ler|leia|mostrar|consultar|verificar)\s+(meus\s+)?e-?mails\s+hoje$',
        ]
        for padrao in padroes_ver_email:
            if re.search(padrao, mensagem_lower):
                logger.info(f"[PRECHECK] Comando 'ver email' detectado - chamando ler_emails diretamente")
                # ✅ Ajuste: se o usuário mencionar "hoje", reduzir a janela para 1 dia.
                # (Evita retornar emails antigos e dá mais precisão para a intenção do usuário.)
                max_dias = 1 if re.search(r'\bhoje\b', mensagem_lower) else 7
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'ler_emails',
                            'arguments': {
                                'limit': 10,
                                'apenas_nao_lidos': False,
                                'max_dias': max_dias
                            }
                        }
                    }]
                }
        
        # Padrões para detalhes de email específico: "detalhe email 8", "ler email 3", "ver email 5"
        padroes_detalhe_email = [
            r'^detalhe\s+email\s+(\d+)$',
            r'^detalhes\s+email\s+(\d+)$',
            r'^ler\s+email\s+(\d+)$',
            r'^ler\s+o\s+email\s+(\d+)$',
            r'^leia\s+email\s+(\d+)$',
            r'^leia\s+o\s+email\s+(\d+)$',
            r'^ver\s+email\s+(\d+)$',
            r'^mostrar\s+email\s+(\d+)$'
        ]
        for padrao in padroes_detalhe_email:
            match = re.search(padrao, mensagem_lower)
            if match:
                email_index = int(match.group(1))
                logger.info(f"[PRECHECK] Comando 'detalhe email {email_index}' detectado - chamando obter_detalhes_email diretamente")
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'obter_detalhes_email',
                            'arguments': {
                                'email_index': email_index
                            }
                        }
                    }]
                }

        # ✅ NOVO (16/01/2026): Detectar "foram registrados" → chamar listar_processos_registrados_hoje
        # Padrões: "quais dmd foram registrados?", "quais processos foram registrados hoje?"
        padroes_registrados = [
            r'foram\s+registrados',
            r'foi\s+registrado',
            r'registramos',
            r'registraram',
            r'foram\s+registradas',  # Para DIs/DUIMPs
            r'foi\s+registrada'
        ]
        for padrao in padroes_registrados:
            if re.search(padrao, mensagem_lower):
                logger.info(f"[PRECHECK] Pergunta 'foram registrados' detectada - mensagem: '{mensagem}'")
                # ✅ Nunca futuro: ignorar perguntas tipo "amanhã" / "futuro"
                if re.search(r'\b(amanh[ãa]|futuro|depois)\b', mensagem_lower):
                    break

                # ✅ Detectar período (prioridade: range > mês > semana > ontem/hoje)
                # Range: "de 01/01/25 a 30/05/26"
                m_range = re.search(r'\bde\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+a\s+(\d{1,2}/\d{1,2}/\d{2,4})\b', mensagem_lower)
                if m_range:
                    data_inicio = m_range.group(1)
                    data_fim = m_range.group(2)
                    # ✅ NOVO: Aplicar normalização de termos de cliente ANTES de regex
                    categoria = self._normalizar_termo_cliente(mensagem, mensagem_lower)
                    if not categoria:
                        if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                            categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
                    if not categoria:
                        match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                        if match_categoria:
                            cat_candidata = match_categoria.group(1)
                            categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                            if cat_candidata in categorias_validas:
                                categoria = cat_candidata
                    return {
                        'tool_calls': [{
                            'function': {
                                'name': 'listar_processos_registrados_periodo',
                                'arguments': {
                                    'categoria': categoria.upper() if categoria else None,
                                    'periodo': 'periodo_especifico',
                                    'data_inicio': data_inicio,
                                    'data_fim': data_fim,
                                    'limite': 200
                                }
                            }
                        }]
                    }

                # Dia específico: "dia 22/01", "em 22/01", "no dia 22/01" OU direto "registramos 22/01"
                # Regra: se não informar ano, assumir ano atual.
                m_dia = re.search(
                    r'(?:\b(?:dia|em|no\s+dia)\b\s*)?(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?=\D|$)',
                    mensagem_lower,
                )
                if m_dia:
                    from datetime import datetime
                    dd = m_dia.group(1)
                    mm = m_dia.group(2)
                    yy_opt = m_dia.group(3)
                    ano_eff = datetime.now().year if not yy_opt else (2000 + int(yy_opt)) if len(yy_opt) == 2 else int(yy_opt)
                    data_dd_mm_aaaa = f"{int(dd):02d}/{int(mm):02d}/{int(ano_eff)}"

                    categoria = self._normalizar_termo_cliente(mensagem, mensagem_lower)
                    if not categoria:
                        if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                            categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
                    if not categoria:
                        match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                        if match_categoria:
                            cat_candidata = match_categoria.group(1)
                            categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                            if cat_candidata in categorias_validas:
                                categoria = cat_candidata

                    logger.info(f"[PRECHECK] Pergunta 'registrados' com dia específico detectada: {data_dd_mm_aaaa} (categoria={categoria})")
                    return {
                        'tool_calls': [{
                            'function': {
                                'name': 'listar_processos_registrados_periodo',
                                'arguments': {
                                    'categoria': categoria.upper() if categoria else None,
                                    'periodo': 'periodo_especifico',
                                    'data_inicio': data_dd_mm_aaaa,
                                    'data_fim': data_dd_mm_aaaa,
                                    'limite': 200
                                }
                            }
                        }]
                    }

                # Mês por nome (pt-BR): "em dezembro 25", "em outubro de 2025"
                meses = {
                    'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
                    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
                }
                mes_detectado = None
                for nome_mes, num_mes in meses.items():
                    if re.search(rf'\b{re.escape(nome_mes)}\b', mensagem_lower):
                        mes_detectado = num_mes
                        break
                ano_detectado = None
                m_ano4 = re.search(r'\b(20\d{2})\b', mensagem_lower)
                if m_ano4:
                    ano_detectado = int(m_ano4.group(1))
                else:
                    m_ano2 = re.search(r'\b(\d{2})\b', mensagem_lower)
                    if m_ano2 and mes_detectado:
                        # se tem mês e só ano 2 dígitos, assumir 20xx
                        try:
                            ano_detectado = int(f"20{m_ano2.group(1)}")
                        except Exception:
                            ano_detectado = None

                if mes_detectado:
                    # ✅ NOVO: Aplicar normalização de termos de cliente ANTES de regex
                    categoria = self._normalizar_termo_cliente(mensagem, mensagem_lower)
                    if not categoria:
                        if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                            categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
                    if not categoria:
                        match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                        if match_categoria:
                            cat_candidata = match_categoria.group(1)
                            categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                            if cat_candidata in categorias_validas:
                                categoria = cat_candidata
                    # ✅ NOVO: Se não especificou ano e mês é no passado (antes do mês atual), assumir ano anterior
                    ano_eff = ano_detectado
                    if not ano_eff:
                        from datetime import datetime
                        hoje = datetime.now()
                        if mes_detectado > hoje.month:
                            # Mês futuro no ano atual não faz sentido para histórico, assumir ano anterior
                            ano_eff = hoje.year - 1
                        else:
                            # Mês passado ou atual: usar ano atual
                            ano_eff = hoje.year
                    return {
                        'tool_calls': [{
                            'function': {
                                'name': 'listar_processos_registrados_periodo',
                                'arguments': {
                                    'categoria': categoria.upper() if categoria else None,
                                    'periodo': 'mes',
                                    'mes': int(mes_detectado),
                                    'ano': int(ano_eff),
                                    'limite': 200
                                }
                            }
                        }]
                    }

                # Ano (ex.: "em 2025")
                if ano_detectado and re.search(r'\b(em|no|na)\s+20\d{2}\b', mensagem_lower):
                    # ✅ NOVO: Aplicar normalização de termos de cliente ANTES de regex
                    categoria = self._normalizar_termo_cliente(mensagem, mensagem_lower)
                    if not categoria:
                        if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                            categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
                    if not categoria:
                        match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                        if match_categoria:
                            cat_candidata = match_categoria.group(1)
                            categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                            if cat_candidata in categorias_validas:
                                categoria = cat_candidata
                    return {
                        'tool_calls': [{
                            'function': {
                                'name': 'listar_processos_registrados_periodo',
                                'arguments': {
                                    'categoria': categoria.upper() if categoria else None,
                                    'periodo': 'ano',
                                    'ano': int(ano_detectado),
                                    'limite': 200
                                }
                            }
                        }]
                    }

                # Semana: "essa semana", "nesta semana"
                if re.search(r'\b(essa|nesta)\s+semana\b', mensagem_lower) or re.search(r'\bsemana\b', mensagem_lower):
                    # ✅ NOVO: Aplicar normalização de termos de cliente ANTES de regex
                    categoria = self._normalizar_termo_cliente(mensagem, mensagem_lower)
                    if not categoria:
                        if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                            categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
                    if not categoria:
                        match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                        if match_categoria:
                            cat_candidata = match_categoria.group(1)
                            categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                            if cat_candidata in categorias_validas:
                                categoria = cat_candidata
                    return {
                        'tool_calls': [{
                            'function': {
                                'name': 'listar_processos_registrados_periodo',
                                'arguments': {
                                    'categoria': categoria.upper() if categoria else None,
                                    'periodo': 'semana',
                                    'limite': 200
                                }
                            }
                        }]
                    }

                # ✅ Detectar dia: hoje (0) / ontem (1) (fallback)
                dias_atras = 0
                if re.search(r'\bontem\b', mensagem_lower) or re.search(r'\bde\s+ontem\b', mensagem_lower):
                    dias_atras = 1

                # Extrair categoria da mensagem
                categoria = None
                if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                    categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
                # Se não encontrou categoria, tentar extrair manualmente
                if not categoria:
                    match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                    if match_categoria:
                        cat_candidata = match_categoria.group(1)
                        # Validar se é categoria conhecida
                        categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                        if cat_candidata in categorias_validas:
                            categoria = cat_candidata
                
                logger.info(f"[PRECHECK] Categoria extraída: {categoria}")
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'listar_processos_registrados_hoje',
                            'arguments': {
                                'categoria': categoria.upper() if categoria else None,
                                'limite': 200,
                                'dias_atras': dias_atras
                            }
                        }
                    }]
                }

        # ✅ NOVO (19/01/2026): Detectar "desembaraçou hoje" → listar_processos_desembaracados_hoje
        if re.search(r'desembarac|desembara[cç]', mensagem_lower) and re.search(r'\b(hoje|ontem|do\s+dia|de\s+ontem)\b', mensagem_lower):
            # ✅ Nunca futuro: não responder "amanhã"
            if re.search(r'\b(amanh[ãa]|futuro|depois)\b', mensagem_lower):
                return None

            categoria = None
            if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
            if not categoria:
                match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                if match_categoria:
                    cat_candidata = match_categoria.group(1)
                    categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                    if cat_candidata in categorias_validas:
                        categoria = cat_candidata
            dias_atras = 1 if re.search(r'\bontem\b', mensagem_lower) else 0
            logger.info(f"[PRECHECK] Pergunta 'desembaraçou' detectada - dias_atras={dias_atras} categoria={categoria}")
            return {
                'tool_calls': [{
                    'function': {
                        'name': 'listar_processos_desembaracados_hoje',
                        'arguments': {
                            'categoria': categoria.upper() if categoria else None,
                            'limite': 200,
                            'dias_atras': dias_atras
                        }
                    }
                }]
            }
        
        # ✅ NOVO (16/01/2026): Detectar "está em análise" → chamar obter_dis_em_analise + obter_duimps_em_analise
        # Padrões: "quais dmd está em análise?", "quais processos estão em análise?"
        padroes_em_analise = [
            r'est[áa]\s+em\s+an[áa]lise',
            r'est[ao]o\s+em\s+an[áa]lise',
            r'em\s+an[áa]lise',
            r'an[áa]lise',
            r'est[ao]o\s+an[áa]lisando',
            r'est[ao]o\s+an[áa]lisadas'
        ]
        for padrao in padroes_em_analise:
            if re.search(padrao, mensagem_lower):
                logger.info(f"[PRECHECK] Pergunta 'está em análise' detectada - mensagem: '{mensagem}'")
                # Extrair categoria da mensagem
                categoria = None
                if hasattr(self.chat_service, '_extrair_categoria_da_mensagem'):
                    categoria = self.chat_service._extrair_categoria_da_mensagem(mensagem)
                # Se não encontrou categoria, tentar extrair manualmente
                if not categoria:
                    match_categoria = re.search(r'\b([A-Z]{2,4})\b', mensagem.upper())
                    if match_categoria:
                        cat_candidata = match_categoria.group(1)
                        # Validar se é categoria conhecida
                        categorias_validas = ['ALH', 'VDM', 'MSS', 'BND', 'DMD', 'GYM', 'SLL', 'MV5', 'CCT', 'ARG', 'GLT', 'GPS', 'NTM', 'DBA', 'MCD', 'UPI', 'ELT']
                        if cat_candidata in categorias_validas:
                            categoria = cat_candidata
                
                logger.info(f"[PRECHECK] Categoria extraída: {categoria}")
                # Buscar DIs e DUIMPs em análise (mesma lógica do dashboard)
                try:
                    from db_manager import obter_dis_em_analise, obter_duimps_em_analise
                    
                    dis = obter_dis_em_analise(categoria.upper() if categoria else None)
                    duimps = obter_duimps_em_analise(categoria.upper() if categoria else None)
                    
                    # Formatar resposta similar ao dashboard
                    resposta = ""
                    if dis or duimps:
                        if dis:
                            resposta += f"📋 **DIs EM ANÁLISE** ({len(dis)} DI(s)):\n"
                            for di in dis[:20]:  # Limitar a 20 para não ficar muito longo
                                processo_ref = di.get('processo_referencia', 'N/A')
                                numero_di = di.get('numero_di', 'N/A')
                                situacao = di.get('situacao_di', 'N/A')
                                canal = di.get('canal_di', '')
                                data_registro = di.get('data_registro') or di.get('data_hora_registro')
                                canal_texto = f" - Canal: {canal}" if canal else ""
                                registro_texto = f" - Registro: {data_registro}" if data_registro else ""
                                resposta += f"• {numero_di} - Processo: {processo_ref} - Status: {situacao}{canal_texto}{registro_texto}\n"
                            if len(dis) > 20:
                                resposta += f"• ... e mais {len(dis) - 20} DI(s)\n"
                            resposta += "\n"
                        
                        if duimps:
                            resposta += f"📋 **DUIMPs EM ANÁLISE** ({len(duimps)} DUIMP(s)):\n"
                            for duimp in duimps[:20]:  # Limitar a 20
                                processo_ref = duimp.get('processo_referencia', 'N/A')
                                numero_duimp = duimp.get('numero_duimp', 'N/A')
                                versao = duimp.get('versao') or duimp.get('versao_duimp', '')
                                situacao = duimp.get('status') or duimp.get('situacao_duimp', 'N/A')
                                tempo = duimp.get('tempo_analise', '')
                                data_registro = duimp.get('data_criacao') or duimp.get('data_registro')
                                tempo_texto = f" (há {tempo})" if tempo else ""
                                versao_texto = f" v{versao}" if versao else ""
                                registro_texto = f" - Registro: {data_registro}" if data_registro else ""
                                resposta += f"• {numero_duimp}{versao_texto} - Processo: {processo_ref} - Status: {situacao}{tempo_texto}{registro_texto}\n"
                            if len(duimps) > 20:
                                resposta += f"• ... e mais {len(duimps) - 20} DUIMP(s)\n"
                    else:
                        categoria_texto = f" {categoria}" if categoria else ""
                        resposta = f"⚠️ Nenhum processo{categoria_texto} com DI ou DUIMP em análise encontrado."
                    
                    return {
                        'resposta': resposta,
                        'precheck': True,
                        'precheck_tipo': 'em_analise'
                    }
                except Exception as e:
                    logger.error(f"[PRECHECK] ❌ Erro ao buscar DIs/DUIMPs em análise: {e}", exc_info=True)
                    # Se der erro, deixar a IA processar
                    break
        
        # 1) Busca de artigo específico de legislação → chamar tool diretamente (PRIORIDADE)
        resposta_artigo = self.legislacao_precheck.precheck_buscar_artigo_especifico(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
        )
        if resposta_artigo is not None:
            # Se tem tool_calls, precisa processar via ChatService
            if resposta_artigo.get('tool_calls'):
                # Retornar para o ChatService processar as tool calls
                return resposta_artigo
            # Se só tem resposta, retornar direto
            if resposta_artigo.get('resposta'):
                return resposta_artigo
        
        # 2) Importação de legislação → chamar tool diretamente
        resposta_legislacao = self.legislacao_precheck.precheck_importar_legislacao(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
        )
        if resposta_legislacao is not None:
            # Se tem tool_calls, precisa processar via ChatService
            if resposta_legislacao.get('tool_calls'):
                # Retornar para o ChatService processar as tool calls
                return resposta_legislacao
            # Se só tem resposta, retornar direto
            if resposta_legislacao.get('resposta'):
                return resposta_legislacao

        # 3) ✅ Policy determinística (sem regex espalhado):
        # - NESH direto (prioridade máxima)
        # - Legislação RAG + TTL por sessão (follow-ups)
        try:
            decision = self.intent_policy.decidir(
                mensagem=mensagem,
                historico=historico,
                session_id=session_id,
            )
            if decision:
                return {
                    'tool_calls': [{
                        'function': {
                            'name': decision.tool_name,
                            'arguments': decision.arguments
                        }
                    }],
                    '_processado_precheck': True,
                    'precheck': True,
                    'precheck_tipo': decision.tipo,
                }
        except Exception as e:
            logger.debug(f"[PRECHECK] ⚠️ Falha ao aplicar IntentPolicyService (não crítico): {e}")
        
        # ✅ REMOVIDO (14/01/2026): Detecção de intenções de relatórios FOB e averbações
        # Agora o modelo gerencia essas intenções via tool calling, permitindo sinônimos como "parecer", "análise", etc.
        
        # 5) Consulta de extrato do Banco do Brasil → chamar tool diretamente
        # Padrões com agência e conta explícitas (prioridade)
        padrao_com_dados = re.search(
            r'(?:extrato|consultar|ver|mostrar)\s+(?:do\s+)?(?:banco\s+do\s+brasil|bb|b\.?b\.?)\s+(?:ag[êe]ncia|ag\.?)\s+(\d+)\s+(?:conta|ct\.?)\s+(\d+)',
            mensagem_lower
        )
        if padrao_com_dados:
            logger.info(f"[PRECHECK] Pedido de extrato BB com agência/conta detectado: '{mensagem}'")
            return {
                'tool_calls': [{
                    'function': {
                        'name': 'consultar_extrato_bb',
                        'arguments': {
                            'agencia': padrao_com_dados.group(1),
                            'conta': padrao_com_dados.group(2)
                        }
                    }
                }]
            }
        
        # ✅ NOVO (12/01/2026): Detectar referência a ID de relatório (ex: "usar rel_20260112_145026")
        padrao_id_relatorio = re.search(r'\brel_\d{8}_\d{6}\b', mensagem, re.IGNORECASE)
        if padrao_id_relatorio:
            relatorio_id = padrao_id_relatorio.group(0)
            logger.info(f'✅✅✅ [PRECHECK] ID de relatório detectado: {relatorio_id}')
            return {
                'tool_calls': [{
                    'function': {
                        'name': 'buscar_relatorio_por_id',
                        'arguments': {
                            'relatorio_id': relatorio_id
                        }
                    }
                }]
            }
        
        # ✅ REMOVIDO (14/01/2026): Detecção de melhorar/filtrar relatório via regex
        # Agora o modelo gerencia essas intenções via tool calling, permitindo sinônimos e variações naturais
        # O modelo pode usar buscar_secao_relatorio_salvo ou melhorar relatórios via tool calling
        
        # ✅ REMOVIDO: Todo o código de processamento de melhorar/filtrar relatório foi removido
        # O modelo agora gerencia essas intenções naturalmente via tool calling
        
        # ✅ REMOVIDO (14/01/2026): Todo o código de melhorar/filtrar relatório foi removido
        # O modelo agora gerencia essas intenções naturalmente via tool calling
        # Blocos removidos: melhorar relatório (linhas 236-421) e filtrar relatório (linhas 423-712)
        
        # ✅ REMOVIDO (14/01/2026): Detecção de envio de relatório via regex
        # A IA (GPT-4o) entende semanticamente "envie esse relatorio" mesmo com erros de digitação ("ralatorio")
        # Deixar a IA detectar naturalmente via tool calling - ela é mais inteligente que regex
        # O código de _enviar_relatorio_email já usa last_visible_report_id automaticamente quando não há report_id explícito
        
        # ✅ CORREÇÃO CIRÚRGICA (14/01/2026): PRIORIDADE 2 - Follow-up de extrato só com sinais explícitos
        resultado_followup_extrato = self._detectar_followup_extrato(mensagem, mensagem_lower, session_id)
        if resultado_followup_extrato:
            return resultado_followup_extrato
        
        # Padrões gerais (sem agência/conta - a tool pedirá)
        padroes_extrato_bb = [
            r'extrato\s+(?:do\s+)?(?:banco\s+do\s+brasil|bb|b\.?b\.?)',
            r'(?:banco\s+do\s+brasil|bb|b\.?b\.?)\s+extrato',
            r'consultar\s+extrato\s+(?:do\s+)?(?:banco\s+do\s+brasil|bb|b\.?b\.?)',
            r'ver\s+extrato\s+(?:do\s+)?(?:banco\s+do\s+brasil|bb|b\.?b\.?)',
            r'mostrar\s+extrato\s+(?:do\s+)?(?:banco\s+do\s+brasil|bb|b\.?b\.?)',
        ]
        
        for padrao in padroes_extrato_bb:
            if re.search(padrao, mensagem_lower):
                logger.info(f"[PRECHECK] Pedido de extrato BB detectado: '{mensagem}'")
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'consultar_extrato_bb',
                            'arguments': {}
                        }
                    }]
                }
        
        # 2) Consulta TECwin NCM → responder diretamente
        resposta_tecwin = self.ncm_precheck.precheck_tecwin_ncm(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            session_id=session_id,
        )
        if resposta_tecwin is not None:
            return resposta_tecwin

        # 3) Follow-up contextual de processo (ex.: "e a DI?", "e a DUIMP?")
        resposta_followup = self.processo_precheck.precheck_followup_processo(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            session_id=session_id,
        )
        if resposta_followup is not None:
            return resposta_followup

        # 4) Situação / detalhe de processo com número explícito
        resposta_proc = self.processo_precheck.precheck_situacao_processo(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            session_id=session_id,
        )
        if resposta_proc is not None:
            return resposta_proc

        # 5-9) Comandos de envio de email (delegado para EmailPrecheckService)
        # Ordem de prioridade mantida dentro do EmailPrecheckService:
        # 1. Email de classificação NCM + alíquotas
        # 2. Email de relatório genérico
        # 3. Email de resumo/briefing específico
        # 4. Email livre (texto ditado)
        # 5. Email com informações de processo/NCM misturado
        resposta_email = self.email_precheck.tentar_precheck_email(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            historico=historico,
            session_id=session_id,
            nome_usuario=nome_usuario,
        )
        if resposta_email is not None:
            return resposta_email

        # 10) ✅ NOVO: Busca híbrida de NCM (Cache → DuckDuckGo → Modelo)
        # Intercepta perguntas de NCM ANTES de chamar o modelo
        resposta_ncm = self.ncm_precheck.precheck_pergunta_ncm(
            mensagem=mensagem,
            mensagem_lower=mensagem_lower,
            session_id=session_id,
        )
        if resposta_ncm is not None:
            return resposta_ncm
        
        # 11) Sinalização: Perguntas de NCM → não aplicar lógica de categoria de processo
        if self.ncm_precheck.eh_pergunta_ncm(mensagem_lower):
            logger.info(f"[PRECHECK] Pergunta de NCM detectada: '{mensagem}'.")
            # Não respondemos aqui; apenas sinalizamos que não é caso de processo

        # 12) ✅ NOVO: Normalização de termos de cliente (Diamond → DMD, Bandimar → BND, etc.)
        # Executado APENAS se não for comando específico e feature flag estiver habilitada
        if os.getenv('ENABLE_CLIENTE_NORMALIZER', 'true').lower() == 'true':
            categoria_normalizada = self._normalizar_termo_cliente(mensagem, mensagem_lower)
            if categoria_normalizada:
                logger.info(f"[PRECHECK] Termo de cliente normalizado para categoria: {categoria_normalizada}")
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'listar_processos_por_categoria',
                            'arguments': {'categoria': categoria_normalizada}
                        }
                    }]
                }

        return None

    def _tem_email(self, texto: str) -> bool:
        """Verifica se o texto contém um email."""
        return bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", texto.lower()))
    
    def _eh_envio_relatorio(self, texto: str) -> bool:
        """Verifica se a mensagem é um pedido de envio de relatório por email."""
        t = texto.lower()
        tem_verbo = any(v in t for v in ["envia", "envie", "mandar", "mande", "enviar"])
        # ✅ CORREÇÃO: Aceitar variações com erro de digitação (ralatorio, relatorio, relatório)
        tem_relatorio = any(k in t for k in [
            "relatorio", "relatório", "ralatorio", "ralatório",  # Variações com/sem erro de digitação
            "dashboard", "resumo", "esse relatorio", "esse relatório",
            "esse ralatorio", "esse ralatório"  # Com erro de digitação
        ])
        return tem_verbo and tem_relatorio and self._tem_email(t)
    
    def _detectar_envio_relatorio(
        self,
        mensagem: str,
        mensagem_lower: str,
        session_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        ✅ PRIORIDADE 1: Detecta envio de relatório por email.
        
        Esta função tem precedência sobre follow-up de extrato para evitar colisões.
        
        Args:
            mensagem: Mensagem original
            mensagem_lower: Mensagem em minúsculas
            session_id: ID da sessão
        
        Returns:
            Dict com tool_call para enviar_relatorio_email ou None
        """
        # ✅✅✅ CRÍTICO: Log para debug
        logger.info(f"[PRECHECK] Verificando envio de relatório: mensagem='{mensagem}', tem_email={self._tem_email(mensagem_lower)}")
        
        if not self._eh_envio_relatorio(mensagem_lower):
            logger.info(f"[PRECHECK] Não é envio de relatório (falhou em _eh_envio_relatorio)")
            return None
        
        logger.info(f"[PRECHECK] ✅ Envio de relatório DETECTADO!")
        
        # Extrair email
        match_email = re.search(r"([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})", mensagem_lower)
        if not match_email:
            logger.warning("[PRECHECK] Envio de relatório detectado mas sem email válido")
            return None
        
        email = match_email.group(1)
        logger.info(f"[PRECHECK] Email extraído: {email}")
        
        # Buscar last_visible_report_id_processos
        if not session_id:
            logger.info("[PRECHECK] Envio de relatório detectado, mas sem session_id. Deixando IA decidir.")
            return None
        
        try:
            from services.report_service import obter_last_visible_report_id, _detectar_dominio_por_mensagem
            
            dominio = _detectar_dominio_por_mensagem(mensagem)
            last_visible = obter_last_visible_report_id(session_id, dominio=dominio)
            
            logger.info(f"[PRECHECK] last_visible encontrado: {last_visible}")
            
            if last_visible and last_visible.get('id'):
                report_id = last_visible['id']
                logger.info(f"[PRECHECK] ✅✅✅ Envio de relatório detectado. report_id={report_id}, dominio={dominio}, to={email}, is_filtered={last_visible.get('is_filtered', False)}")
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'enviar_relatorio_email',
                            'arguments': {
                                'destinatario': email,
                                'report_id': report_id,
                                'confirmar_envio': False
                            }
                        }
                    }]
                }
            else:
                logger.warning(f"[PRECHECK] ⚠️ Envio de relatório detectado, mas sem report_id visível. last_visible={last_visible}")
                return None
        except Exception as e:
            logger.error(f"[PRECHECK] ❌ Erro ao detectar envio de relatório: {e}", exc_info=True)
            return None
    
    def _detectar_followup_extrato(
        self,
        mensagem: str,
        mensagem_lower: str,
        session_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        ✅ PRIORIDADE 2: Detecta follow-up de extrato bancário.
        
        Só dispara com sinais explícitos de extrato (extrato/saldo/lançamento/banco/agência/conta).
        NÃO dispara se a mensagem contém "relatório/resumo/dashboard" (para evitar colisão).
        
        Args:
            mensagem: Mensagem original
            mensagem_lower: Mensagem em minúsculas
            session_id: ID da sessão
        
        Returns:
            Dict com tool_call para consultar_extrato ou None
        """
        # ✅ TRAVA ANTI-COLISÃO: Se tem "relatório/resumo/dashboard", NÃO é follow-up de extrato
        if any(k in mensagem_lower for k in ["relatorio", "relatório", "dashboard", "resumo"]):
            return None
        
        # ✅ SINAIS EXPLÍCITOS DE EXTRATO: Só disparar se tiver sinais claros de extrato bancário
        sinais_extrato = ["extrato", "saldo", "lançamento", "lancamento", "banco", "agencia", "agência", "conta"]
        if not any(k in mensagem_lower for k in sinais_extrato):
            return None
        
        # ✅ EXCLUIR: Extrato de CE/CCT/DI/DUIMP (não é extrato bancário)
        padroes_excluir = [
            r'extrato.*ce',
            r'extrato.*cct',
            r'extrato.*di',
            r'extrato.*duimp',
            r'extrato.*processo',
        ]
        for padrao in padroes_excluir:
            if re.search(padrao, mensagem_lower):
                return None
        
        # Padrões de follow-up de extrato (sem "envie relatorio")
        padroes_followup_extrato = [
            r'detalh[ae]r?\s+(?:os|as)?\s*\d+\s+lan[çc]amentos',
            r'detalh[ae]r?\s+(?:os|as)?\s*lan[çc]amentos',
            r'envie?\s+(?:esse|o)?\s*extrato',
            r'envi[ae]r?\s+(?:esse|o)?\s*extrato',
            r'mostre?\s+(?:os|as)?\s*lan[çc]amentos',
            r'mostre?\s+(?:os|as)?\s*transa[çc][oõ]es',
        ]
        
        eh_followup_extrato = any(re.search(p, mensagem_lower) for p in padroes_followup_extrato)
        if not eh_followup_extrato:
            return None
        
        if not session_id:
            return None
        
        try:
            from services.context_service import buscar_contexto_sessao
            contextos = buscar_contexto_sessao(session_id, tipo_contexto='ultima_consulta', chave='extrato_bancario')
            
            if not contextos:
                return None
            
            ctx_extrato = contextos[0]  # Pegar o mais recente
            dados_extrato = ctx_extrato.get('dados', {})
            banco = dados_extrato.get('banco', '')
            
            logger.info(f"[PRECHECK] Follow-up de extrato bancário detectado: banco={banco}")
            
            if banco == 'SANTANDER':
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'consultar_extrato_santander',
                            'arguments': {
                                'agencia': dados_extrato.get('agencia'),
                                'conta': dados_extrato.get('conta'),
                                'statement_id': dados_extrato.get('statement_id'),
                                'data_inicio': dados_extrato.get('data_inicio'),
                                'data_fim': dados_extrato.get('data_fim'),
                                'dias': dados_extrato.get('dias', 7)
                            }
                        }
                    }],
                    '_contexto_extrato': dados_extrato
                }
            elif banco == 'BB' or banco == 'BANCO_DO_BRASIL':
                return {
                    'tool_calls': [{
                        'function': {
                            'name': 'consultar_extrato_bb',
                            'arguments': {
                                'agencia': dados_extrato.get('agencia'),
                                'conta': dados_extrato.get('conta'),
                                'data_inicio': dados_extrato.get('data_inicio'),
                                'data_fim': dados_extrato.get('data_fim')
                            }
                        }
                    }],
                    '_contexto_extrato': dados_extrato
                }
        except Exception as e:
            logger.warning(f"[PRECHECK] Erro ao detectar follow-up de extrato: {e}", exc_info=True)
        
        return None
    
    def _normalizar_termo_cliente(self, mensagem: str, mensagem_lower: str) -> Optional[str]:
        """
        Normaliza termos de cliente para categoria usando regras aprendidas.
        
        Exemplos:
        - "Diamond" ou "diamonds" → "DMD"
        - "Bandimar" → "BND"
        
        ✅ PROTEÇÕES:
        - Não normaliza se for comando específico (email, extrato, etc.)
        - Não normaliza se já houver categoria explícita na mensagem
        - Retorna None se não encontrar regra aprendida
        
        Args:
            mensagem: Mensagem original do usuário
            mensagem_lower: Mensagem em minúsculas (para performance)
            
        Returns:
            Categoria normalizada (ex: "DMD", "BND") ou None se não encontrar
        """
        try:
            # ✅ PROTEÇÃO 1: Verificar se NÃO é comando específico
            comandos_especificos = [
                r'^ver\s+email',
                r'^detalhe\s+email',
                r'extrato\s+(?:do\s+)?(?:banco|santander|bb)',
                r'fechar\s+(?:o\s+)?dia',
                r'o\s+que\s+temos?\s+(?:pra|para)\s+hoje',
                r'fechamento',
                r'dashboard',
                r'tecwin',
                r'legislacao',
                r'importar\s+legislacao',
                r'relatorio\s+fob',
                r'relatorio\s+averbacoes',
                r'gerar\s+pdf',
                r'pdf\s+do\s+extrato',
                r'calcular\s+impostos',
                r'calcule\s+os\s+impostos',
                r'criar\s+duimp',
                r'montar\s+duimp',
                r'consultar\s+ncm',
                r'sugerir\s+ncm',
            ]
            
            eh_comando_especifico = any(re.search(padrao, mensagem_lower) for padrao in comandos_especificos)
            if eh_comando_especifico:
                logger.debug(f"[PRECHECK] Mensagem é comando específico - não normalizar: '{mensagem}'")
                return None
            
            # ✅ PROTEÇÃO 2: Verificar se já tem categoria explícita na mensagem
            # Se já tem categoria (ex: "como estão os DMD?"), não normalizar
            # ⚠️ EXCEÇÃO: Para "registramos", permitir normalizar mesmo se tiver categoria explícita
            # (ex: "o que registramos de alho" → normalizar "alho" → "ALH" mesmo se já tiver "ALH" na mensagem)
            eh_pergunta_registrados = bool(
                re.search(r'registramos|foram\s+registrados|foi\s+registrado', mensagem_lower)
            )
            if not eh_pergunta_registrados:
                categorias_existentes = ['alh', 'vdm', 'mss', 'bnd', 'dmd', 'gym', 'sll', 'mv5', 'gps', 'ntm', 'mcd', 'dba', 'arg', 'upi']
                tem_categoria_explicita = any(
                    re.search(rf'\b{cat}\b', mensagem_lower) for cat in categorias_existentes
                )
                if tem_categoria_explicita:
                    logger.debug(f"[PRECHECK] Mensagem já tem categoria explícita - não normalizar: '{mensagem}'")
                    return None
            
            # ✅ PROTEÇÃO 3: Verificar se parece ser pergunta sobre processos/categorias
            # Padrões que indicam pergunta sobre processos
            padroes_pergunta_processo = [
                r'como\s+est[aã]o',
                r'como\s+est[aã]',
                r'quais\s+(?:os|as)?\s*processos',
                r'mostre\s+(?:os|as)?\s*processos',
                r'listar\s+processos',
                r'processos?\s+do',
                r'processos?\s+de',
                r'status\s+dos?\s*processos',
                r'situacao\s+dos?\s*processos',
                r'registramos',  # ✅ NOVO: "o que registramos" também é pergunta sobre processos
                r'foram\s+registrados',
                r'foi\s+registrado',
            ]
            
            parece_pergunta_processo = any(
                re.search(padrao, mensagem_lower) for padrao in padroes_pergunta_processo
            )
            if not parece_pergunta_processo:
                logger.debug(f"[PRECHECK] Mensagem não parece ser pergunta sobre processos - não normalizar: '{mensagem}'")
                return None
            
            # Buscar regras aprendidas do tipo 'cliente_categoria' ou 'mapeamento_cliente'
            from services.learned_rules_service import buscar_regras_aprendidas
            
            regras = buscar_regras_aprendidas(
                tipo_regra='cliente_categoria',
                ativas=True
            )
            
            # Se não encontrou com tipo específico, buscar todas e filtrar
            if not regras:
                regras = buscar_regras_aprendidas(ativas=True)
                # Filtrar regras que parecem ser mapeamento cliente → categoria
                regras = [
                    r for r in regras 
                    if 'cliente' in r.get('nome_regra', '').lower() or 
                       'categoria' in r.get('nome_regra', '').lower() or
                       r.get('tipo_regra') == 'mapeamento_cliente'
                ]
            
            if not regras:
                logger.debug(f"[PRECHECK] Nenhuma regra de mapeamento cliente→categoria encontrada")
                return None
            
            # Processar regras e criar dicionário de mapeamento
            mapeamento = {}
            for regra in regras:
                nome_regra = regra.get('nome_regra', '').lower()
                descricao = regra.get('descricao', '').lower()
                aplicacao_texto = regra.get('aplicacao_texto', '').lower()
                
                # Tentar extrair mapeamento de diferentes formatos:
                # 1. "Diamond → DMD" ou "Diamond = DMD"
                # 2. "Diamond=DMD" ou "Diamond:DMD"
                # 3. "Diamond" na descrição e "DMD" na aplicacao_texto
                
                # Formato 1: "Diamond → DMD" ou "Diamond = DMD"
                match_seta = re.search(r'([a-záàâãéèêíìîóòôõúùûç\s]+)\s*[→=]\s*([a-z]{2,4})', nome_regra + ' ' + descricao)
                if match_seta:
                    termo = match_seta.group(1).strip()
                    categoria = match_seta.group(2).strip().upper()
                    mapeamento[termo] = categoria
                    logger.debug(f"[PRECHECK] Mapeamento encontrado (formato seta): '{termo}' → '{categoria}'")
                    continue
                
                # Formato 2: "Diamond=DMD" ou "Diamond:DMD"
                match_igual = re.search(r'([a-záàâãéèêíìîóòôõúùûç\s]+)[=:]([a-z]{2,4})', nome_regra + ' ' + descricao)
                if match_igual:
                    termo = match_igual.group(1).strip()
                    categoria = match_igual.group(2).strip().upper()
                    mapeamento[termo] = categoria
                    logger.debug(f"[PRECHECK] Mapeamento encontrado (formato igual): '{termo}' → '{categoria}'")
                    continue
                
                # Formato 3: Extrair do nome_regra se for simples (ex: "Diamond" → buscar "DMD" na descrição)
                # Exemplo: nome_regra="Diamond", descricao="Mapeia Diamond para categoria DMD"
                if len(nome_regra.split()) <= 2:  # Nome simples (ex: "Diamond" ou "cliente Diamond")
                    # Procurar categoria na descrição ou aplicacao_texto
                    match_categoria = re.search(r'\b([a-z]{2,4})\b', descricao + ' ' + aplicacao_texto)
                    if match_categoria:
                        categoria_candidata = match_categoria.group(1).upper()
                        # Verificar se é categoria válida
                        if categoria_candidata in ['DMD', 'BND', 'ALH', 'VDM', 'MSS', 'GYM', 'SLL', 'MV5']:
                            termo = nome_regra.strip()
                            mapeamento[termo] = categoria_candidata
                            logger.debug(f"[PRECHECK] Mapeamento encontrado (formato nome simples): '{termo}' → '{categoria_candidata}'")
                            continue
            
            if not mapeamento:
                logger.debug(f"[PRECHECK] Nenhum mapeamento válido extraído das regras")
                return None
            
            # Verificar se algum termo do mapeamento aparece na mensagem
            for termo, categoria in mapeamento.items():
                # Buscar termo como palavra completa (não substring)
                padrao_termo = rf'\b{re.escape(termo)}\b'
                if re.search(padrao_termo, mensagem_lower):
                    logger.info(f"[PRECHECK] ✅ Termo '{termo}' encontrado na mensagem → categoria '{categoria}'")
                    return categoria
            
            logger.debug(f"[PRECHECK] Nenhum termo do mapeamento encontrado na mensagem")
            return None
            
        except Exception as e:
            logger.warning(f"[PRECHECK] Erro ao normalizar termo de cliente: {e}", exc_info=True)
            return None  # ✅ SEGURO: retorna None em caso de erro
