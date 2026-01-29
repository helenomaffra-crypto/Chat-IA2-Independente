"""ToolExecutor: camada fina para execução de tools via ToolRouter.

Objetivo imediato: tirar a lógica de roteamento de dentro do ChatService,
sem mudar comportamento, preparando o terreno para refatorar o fallback
antigo em etapas menores.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # evita import circular em tempo de execução
    from services.chat_service import ChatService
    from services.tool_router import ToolRouter

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executor de tools baseado em ToolRouter.

    Por enquanto, esta classe encapsula apenas a parte "nova" da
    arquitetura (ToolRouter). O fallback antigo continua dentro do
    ChatService._executar_funcao_tool, que chama este executor primeiro
    e só entra no fallback se necessário.
    """

    def __init__(self, tool_router: Optional["ToolRouter"]) -> None:
        self.tool_router = tool_router

    def executar(
        self,
        chat_service: "ChatService",
        nome_funcao: str,
        argumentos: Dict[str, Any],
        mensagem_original: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executa uma tool via ToolRouter, se disponível.

        Retorna o resultado do router ou um dict com `{"_use_fallback": True}`
        quando não for possível usar o router (sem quebrar o fluxo atual).
        """
        if not self.tool_router:
            return {"_use_fallback": True}

        try:
            # ✅ NOVO: Incluir session_id no context se disponível
            context_dict = {
                "mensagem_original": mensagem_original,
                "chat_service": chat_service,
            }
            # ✅ CRÍTICO: Priorizar session_id do argumentos (vem do ConfirmationHandler)
            # Se não estiver nos argumentos, usar session_id_atual do chat_service
            session_id_ctx = None
            if hasattr(chat_service, 'session_id_atual') and chat_service.session_id_atual:
                session_id_ctx = chat_service.session_id_atual
            # Se argumentos tiverem session_id (vem do ConfirmationHandler), usar esse
            if argumentos.get('session_id'):
                session_id_ctx = argumentos.get('session_id')
            if session_id_ctx:
                context_dict["session_id"] = session_id_ctx
            
            resultado_router = self.tool_router.route(
                nome_funcao,
                argumentos,
                context=context_dict,
            )

            # Se router retornou sucesso ou erro específico, usar resultado
            if not resultado_router.get("_use_fallback", False):
                return resultado_router

            # Se router indicou fallback, deixar ChatService seguir com lógica antiga
            logger.debug(
                f"🔄 Tool '{nome_funcao}' usando fallback (implementação antiga via ChatService)."
            )
            return {"_use_fallback": True}

        except Exception as e:
            logger.warning(
                f"⚠️ Erro no ToolRouter para '{nome_funcao}': {e}. Usando fallback.",
                exc_info=True,
            )
            return {"_use_fallback": True}
