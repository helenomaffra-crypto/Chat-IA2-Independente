"""
Service dedicado para consulta de status/detalhes de processo.

✅ V2 (clean + auto-heal):
- Clean path: SQLite (Kanban/cache) + SQL Server `mAIke_assistente`
- Auto-heal seletivo: só quando faltar dado, busca em fontes oficiais e persiste no banco novo

Objetivo: resposta estável (sem barulho de schema legado) e banco novo enriquecido.
"""

import logging
from typing import Dict, Any, Optional

from services.processo_status_v2_service import ProcessoStatusV2Service

logger = logging.getLogger(__name__)


class ProcessoStatusService:
    """
    Serviço fino em torno do `ProcessoAgent` para consultar status de processo.

    Mantém o comportamento atual de `consultar_status_processo`, apenas
    expondo uma interface mais clara para outros serviços.
    """

    def __init__(self) -> None:
        self._svc = ProcessoStatusV2Service()

    def consultar_status_processo(
        self,
        processo_referencia: str,
        mensagem_original: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Consulta status detalhado de um processo.

        Args:
            processo_referencia: Referência do processo (ex: "ALH.0174/25").
            mensagem_original: Mensagem original do usuário (para heurísticas de fallback).
        """
        processo_ref = (processo_referencia or "").strip()

        if not processo_ref:
            return {
                "sucesso": False,
                "erro": "processo_referencia é obrigatório",
                "resposta": "❌ Referência de processo é obrigatória.",
            }

        try:
            logger.info(f"[ProcessoStatusService] Consultando status V2 (clean+auto-heal) para {processo_ref}...")
            return self._svc.consultar(
                processo_referencia=processo_ref,
                auto_heal=True,
                incluir_eta=True,
                incluir_afrmm=True,
            )
        except Exception as e:
            logger.error(
                f"[ProcessoStatusService] Erro ao consultar status do processo {processo_ref}: {e}",
                exc_info=True,
            )
            return {
                "sucesso": False,
                "erro": str(e),
                "resposta": f"❌ Erro ao consultar o status do processo {processo_ref}: {str(e)}",
            }

"""Serviço determinístico para resolver situação completa de um processo.

Este módulo expõe uma função principal:

    resolver_situacao_processo(processo_referencia: str) -> dict

Ela centraliza toda a lógica de consolidação de informações de processo (CE, CCT,
DI, DUIMP, pendências, ETA, etc.), usando as funções já existentes no db_manager
(como gerar_json_consolidado_processo e obter_dados_documentos_processo).

Objetivo:
- Tornar a decisão sobre "tem DUIMP? tem CE? qual situação?" determinística
  no backend.
- Permitir que o chat_service e a mAIke apenas NARREM o resultado, sem "chutar".
"""
from typing import Dict, Any
import logging

from db_manager import gerar_json_consolidado_processo

logger = logging.getLogger(__name__)


def resolver_situacao_processo(processo_referencia: str) -> Dict[str, Any]:
    """Resolve a situação completa de um processo (ativo ou histórico).

    Args:
        processo_referencia: Número do processo (ex: "VDM.0004/25"). Pode vir
            abreviado; a normalização é feita por quem chama (chat_service).

    Returns:
        Dict no formato:
        {
            "sucesso": bool,
            "processo_referencia": str,
            "tem_ce": bool,
            "tem_di": bool,
            "tem_duimp": bool,
            "json_consolidado": dict | None,
            "erro": str | None,
        }
    """
    processo = (processo_referencia or "").strip()
    if not processo:
        return {
            "sucesso": False,
            "processo_referencia": processo_referencia,
            "tem_ce": False,
            "tem_di": False,
            "tem_duimp": False,
            "json_consolidado": None,
            "erro": "PROCESSO_VAZIO",
        }

    try:
        # Usa o JSON consolidado já existente no db_manager.
        json_consolidado = gerar_json_consolidado_processo(processo)

        if not json_consolidado or isinstance(json_consolidado, dict) and json_consolidado.get("erro"):
            erro_msg = None
            if isinstance(json_consolidado, dict):
                erro_msg = json_consolidado.get("erro")
            logger.error(
                "[resolver_situacao_processo] Erro ao gerar JSON consolidado para %s: %s",
                processo,
                erro_msg or "desconhecido",
            )
            return {
                "sucesso": False,
                "processo_referencia": processo,
                "tem_ce": False,
                "tem_di": False,
                "tem_duimp": False,
                "json_consolidado": None,
                "erro": erro_msg or "ERRO_GERAR_JSON_CONSOLIDADO",
            }

        # Derivar flags simples a partir do JSON consolidado.
        chaves = json_consolidado.get("chaves", {}) if isinstance(json_consolidado, dict) else {}
        declaracoes = json_consolidado.get("declaracoes", []) if isinstance(json_consolidado, dict) else []

        tem_di = bool(chaves.get("di")) or any(
            isinstance(d, dict) and d.get("tipo") == "DI" for d in declaracoes
        )
        tem_duimp = bool(chaves.get("duimp_num")) or any(
            isinstance(d, dict) and d.get("tipo") == "DUIMP" for d in declaracoes
        )

        # CE/CCT vêm mais de obter_dados_documentos_processo, mas o JSON consolidado
        # agrega isso via chaves ou via timeline/movimentacao.
        tem_ce = bool(chaves.get("ce_house") or chaves.get("ce_master"))

        return {
            "sucesso": True,
            "processo_referencia": processo,
            "tem_ce": tem_ce,
            "tem_di": tem_di,
            "tem_duimp": tem_duimp,
            "json_consolidado": json_consolidado,
            "erro": None,
        }

    except Exception as e:
        logger.error(
            "[resolver_situacao_processo] Erro inesperado ao resolver situação do processo %s: %s",
            processo,
            e,
            exc_info=True,
        )
        return {
            "sucesso": False,
            "processo_referencia": processo,
            "tem_ce": False,
            "tem_di": False,
            "tem_duimp": False,
            "json_consolidado": None,
            "erro": str(e),
        }
