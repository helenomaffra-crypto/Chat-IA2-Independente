import logging
import re
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.chat_service import ChatService

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    """Decisão determinística que pode forçar tool calls antes do modelo."""
    tool_name: str
    arguments: Dict[str, Any]
    tipo: str


class IntentPolicyService:
    """
    Camada determinística (policy-as-code) para forçar tool calls em situações críticas.

    Motivação:
    - Evitar regex espalhado em PrecheckService
    - Prioridade clara (ex: NESH deve vencer modo_legislacao)
    - Persistência por sessão (TTL) via contexto_sessao
    """

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service
        self._rules = self._carregar_regras()

    def decidir(
        self,
        *,
        mensagem: str,
        historico: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
    ) -> Optional[PolicyDecision]:
        historico = historico or []
        mensagem_lower = (mensagem or "").lower().strip()

        # ✅ PRIORIDADE 1: NESH direto (nunca pode ser atropelado por modo_legislacao)
        d_nesh = self._decidir_nesh_direto(mensagem_lower)
        if d_nesh:
            return d_nesh

        # ✅ PRIORIDADE 1.5: Notícias Siscomex (determinístico, sem depender do modelo)
        d_news = self._decidir_siscomex_noticias(mensagem_lower)
        if d_news:
            return d_news

        # ✅ PRIORIDADE 2: Legislação (gatilhos + TTL)
        d_leg = self._decidir_legislacao_rag(mensagem, mensagem_lower, session_id=session_id)
        if d_leg:
            return d_leg

        return None

    def _decidir_siscomex_noticias(self, mensagem_lower: str) -> Optional[PolicyDecision]:
        """
        Detecta pedidos de "notícias do Siscomex" e força listar_noticias_siscomex.
        """
        if not mensagem_lower:
            return None

        p = self._get_policy("siscomex_noticias") or {}
        match_any = p.get("match_any") or [
            r"\bnot[ií]cia(?:s)?\b.*\bsiscomex\b",
            r"\bsiscomex\b.*\bnot[ií]cia(?:s)?\b",
        ]
        pediu = any(re.search(rx, mensagem_lower, re.IGNORECASE) for rx in match_any)
        if not pediu:
            return None

        args: Dict[str, Any] = dict(p.get("default_args") or {"dias": 7, "limite": 20})
        logger.info("[POLICY] ✅ Notícias Siscomex: forçando listar_noticias_siscomex")
        return PolicyDecision(tool_name="listar_noticias_siscomex", arguments=args, tipo="siscomex_noticias")

    def _carregar_regras(self) -> Dict[str, Any]:
        """
        Carrega regras declarativas (JSON) para evitar regex espalhado e facilitar ajuste sem código.

        ENV:
          - INTENT_POLICY_RULES_PATH (default: config/intent_policy_rules.json)
        """
        path = os.getenv("INTENT_POLICY_RULES_PATH", "config/intent_policy_rules.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                rules = json.load(f)
            if not isinstance(rules, dict):
                raise ValueError("rules_json_not_dict")
            return rules
        except Exception as e:
            logger.warning(f"⚠️ [POLICY] Não foi possível carregar rules em '{path}'. Usando defaults em código. Motivo: {e}")
            return {
                "version": 1,
                "default_ttl_minutes": 15,
                "policies": []
            }

    def _get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        for p in (self._rules.get("policies") or []):
            if isinstance(p, dict) and p.get("id") == policy_id:
                return p
        return None

    def _decidir_nesh_direto(self, mensagem_lower: str) -> Optional[PolicyDecision]:
        """
        Detecta pedidos explícitos de NESH e força buscar_nota_explicativa_nesh.
        """
        if not mensagem_lower:
            return None

        p = self._get_policy("nesh_direto") or {}
        match_any = p.get("match_any") or [r"\bnesh\b", r"nota\s+explicativa"]
        pediu_nesh = any(re.search(rx, mensagem_lower, re.IGNORECASE) for rx in match_any)
        if not pediu_nesh:
            return None

        # Extrair NCM (se houver 4/6/8 com separadores)
        ncm_regex = p.get("ncm_regex") or r"\b(\d{2}(?:[.\s-]?\d{2}){1,3})\b"
        ncm_match = re.search(ncm_regex, mensagem_lower)
        ncm = ncm_match.group(1) if ncm_match else None

        # Extrair descrição removendo comandos comuns
        desc = mensagem_lower
        strip_words = p.get("strip_words_regex") or r"\b(busque|buscar|pesquise|pesquisar|consulte|consultar|procure|procurar|mostre|mostrar)\b"
        desc = re.sub(strip_words, "", desc, flags=re.IGNORECASE).strip()
        for phr in (p.get("strip_phrases_regex") or [r"\b(na|no)\b", r"\bnesh\b", r"\bnota\s+explicativa\b"]):
            desc = re.sub(phr, "", desc, flags=re.IGNORECASE).strip()
        desc = re.sub(r"\s+", " ", desc).strip()

        # se tem NCM e descrição vazia, ok. se não tem NCM, precisa descrição.
        descricao_produto = desc if desc else None

        args: Dict[str, Any] = dict((p.get("default_args") or {"limite": 3}))
        if ncm:
            args["ncm"] = ncm
        if descricao_produto:
            args["descricao_produto"] = descricao_produto

        logger.info(f"[POLICY] ✅ NESH direto: forçando buscar_nota_explicativa_nesh (ncm={ncm}, desc='{descricao_produto}')")
        return PolicyDecision(tool_name="buscar_nota_explicativa_nesh", arguments=args, tipo="nesh_direto")

    def _decidir_legislacao_rag(
        self,
        mensagem: str,
        mensagem_lower: str,
        *,
        session_id: Optional[str],
    ) -> Optional[PolicyDecision]:
        """
        Força buscar_legislacao_responses quando houver intenção clara de base legal
        e mantém TTL por sessão para follow-ups.
        """
        if not mensagem_lower:
            return None

        p = self._get_policy("legislacao_rag") or {}
        gatilhos = p.get("match_any") or [
            r"\blegisla[çc][ãa]o\b",
            r"\bbase\s+legal\b",
            r"\bna\s+legisla[çc][ãa]o\b",
            r"\bpela\s+legisla[çc][ãa]o\b",
            r"\bart\.?\b",
            r"\bartigo\b",
            r"\bdecreto\b",
            r"\binstru[cç][ãa]o\s+normativa\b",
            r"\blei\b",
            r"\bportaria\b",
            r"\bregulamento\s+aduaneiro\b",
        ]
        pediu_base_legal = any(re.search(rx, mensagem_lower, re.IGNORECASE) for rx in gatilhos)

        modo_legislacao_ativo = False
        if session_id:
            try:
                from services.context_service import buscar_contexto_sessao, salvar_contexto_sessao
                ttl_ctx = p.get("ttl_context") or {"tipo_contexto": "modo_legislacao", "chave": "until"}
                tipo_ctx = ttl_ctx.get("tipo_contexto", "modo_legislacao")
                chave_ctx = ttl_ctx.get("chave", "until")
                ctxs = buscar_contexto_sessao(session_id=session_id, tipo_contexto=tipo_ctx, chave=chave_ctx)
                if ctxs:
                    until_raw = (ctxs[0].get("valor") or "").strip()
                    try:
                        until_dt = datetime.fromisoformat(until_raw)
                        modo_legislacao_ativo = datetime.now() <= until_dt
                    except Exception:
                        modo_legislacao_ativo = False

                if pediu_base_legal:
                    ttl_minutes = int(p.get("ttl_minutes") or self._rules.get("default_ttl_minutes") or 15)
                    until_dt = datetime.now() + timedelta(minutes=ttl_minutes)
                    salvar_contexto_sessao(
                        session_id=session_id,
                        tipo_contexto=tipo_ctx,
                        chave=chave_ctx,
                        valor=until_dt.isoformat(),
                        dados_adicionais={"gatilho": "policy", "mensagem": (mensagem or "")[:200]},
                    )
                    modo_legislacao_ativo = True
            except Exception as e:
                logger.debug(f"[POLICY] ⚠️ Falha ao ler/salvar modo_legislacao: {e}")

        # ✅ CORREÇÃO (21/01/2026): O TTL do modo_legislacao NÃO pode “sequestrar” a conversa inteira.
        # Ex.: usuário pergunta algo de legislação → modo_legislacao liga por 15min.
        # Em seguida pergunta "o que temos pra hoje?" / "como estão os MV5?".
        # Nesse caso, NÃO devemos forçar RAG; devemos deixar o fluxo normal chamar tools operacionais.
        #
        # Regra:
        # - Se a mensagem atual tem gatilho explícito de legislação, SEMPRE pode forçar RAG.
        # - Se está apenas “no TTL” (modo_legislacao_ativo=True) mas a mensagem parece operacional,
        #   ignorar o TTL e NÃO forçar RAG.
        if modo_legislacao_ativo and not pediu_base_legal:
            ttl_exclude = p.get("ttl_exclude_match_any") or [
                # Dashboards / operação do dia
                r"\bo\s+que\s+temos\s+(?:pra|para)\s+hoje\b",
                r"\bo\s+que\s+tem\s+(?:pra|para)\s+hoje\b",
                r"\bdashboard\b",
                r"\bkanban\b",
                r"\bprocesso(?:s)?\b",
                r"\bcomo\s+est[aã]o\b",
                r"\bstatus\b",
                # Identificadores do sistema (processo/categoria/documentos)
                r"\b[a-z]{2,4}\.\d{1,4}/\d{2}\b",
                r"\b(alh|vdm|mss|bnd|dmd|gym|sll|mv5|gps|ntm|mcd|dba|arg|upi)\b",
                r"\b(ce|cct|di|duimp)\b",
                # Financeiro / pagamentos / relatórios
                r"\bextrato\b",
                r"\bconcilia",
                r"\bsincroniz",
                r"\bpagamento(?:s)?\b",
                r"\brelat[oó]rio\b",
            ]
            if any(re.search(rx, mensagem_lower, re.IGNORECASE) for rx in ttl_exclude):
                logger.info("[POLICY] ℹ️ modo_legislacao ativo, mas mensagem parece operacional; não forçando RAG.")
                return None

        if not (pediu_base_legal or modo_legislacao_ativo):
            return None

        logger.info(f"[POLICY] ✅ Legislação RAG: forçando buscar_legislacao_responses (modo={modo_legislacao_ativo}, gatilho={pediu_base_legal})")
        return PolicyDecision(
            tool_name="buscar_legislacao_responses",
            arguments={"pergunta": mensagem},
            tipo="legislacao_rag",
        )

