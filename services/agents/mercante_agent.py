from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MercanteAgent(BaseAgent):
    """
    Agent responsável por automações RPA do Mercante (AFRMM).

    Regra: este agent prepara navegação (não efetiva pagamento).
    """

    def execute(
        self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        handlers = {
            "preparar_pagamento_afrmm": self._preparar_pagamento_afrmm,
            "executar_pagamento_afrmm": self._executar_pagamento_afrmm,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {
                "sucesso": False,
                "erro": f"Tool {tool_name} não encontrada",
                "resposta": f'❌ Tool "{tool_name}" não disponível no MercanteAgent.',
            }
        try:
            return handler(arguments, context)
        except Exception as e:
            logger.error(f"Erro ao executar {tool_name}: {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": str(e),
                "resposta": f"❌ Erro ao executar {tool_name}: {e}",
            }

    def _preparar_pagamento_afrmm(
        self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        processo_referencia = (arguments.get("processo_referencia") or "").strip()
        ce_mercante = arguments.get("ce_mercante")
        parcela = arguments.get("parcela")
        clicar_enviar = arguments.get("clicar_enviar", True)
        executar_local = arguments.get("executar_local", False)

        from services.mercante_afrmm_service import MercanteAfrmmService

        svc = MercanteAfrmmService()
        return svc.preparar_por_processo(
            processo_referencia,
            ce_mercante=ce_mercante,
            parcela=parcela,
            clicar_enviar=bool(clicar_enviar),
            executar_local=bool(executar_local),
        )
    
    def _executar_pagamento_afrmm(
        self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executa pagamento de AFRMM com preview (Valor do Débito + Saldo BB) e pending intent.
        Ou executa pagamento se confirmar_pagamento=True.
        
        ⚠️ Ação sensível que requer confirmação do usuário.
        """
        processo_referencia = (arguments.get("processo_referencia") or "").strip().upper()
        ce_mercante = arguments.get("ce_mercante")
        parcela = arguments.get("parcela")
        confirmar_pagamento = arguments.get("confirmar_pagamento", False)
        session_id = (context or {}).get("session_id") if context else None

        logger.info(f'🔍 [MercanteAgent] _executar_pagamento_afrmm chamado: processo={processo_referencia}, confirmar_pagamento={confirmar_pagamento}, session_id={session_id}')

        if not processo_referencia:
            return {
                "sucesso": False,
                "erro": "ARGUMENTO_INVALIDO",
                "resposta": "❌ Informe o processo no formato `XXX.NNNN/AA` (ex: `GYM.0050/25`).",
            }
        
        if not session_id:
            return {
                "sucesso": False,
                "erro": "SEM_SESSION_ID",
                "resposta": "❌ Erro: session_id não fornecido.",
            }

        from services.mercante_afrmm_service import MercanteAfrmmService

        svc = MercanteAfrmmService()
        
        # ✅ CRÍTICO: Se confirmar_pagamento=True, executar pagamento diretamente (não criar preview)
        if confirmar_pagamento:
            logger.info(f'✅✅✅ [MercanteAgent] confirmar_pagamento=True - executando pagamento (não criando preview)')
            return svc.executar_pagamento(
                processo_referencia,
                ce_mercante=ce_mercante,
                parcela=parcela,
                session_id=session_id,
            )
        
        # Caso contrário, gerar preview + pending intent
        logger.info(f'⚠️ [MercanteAgent] confirmar_pagamento=False - criando preview (não executando pagamento)')
        return svc.preparar_pagamento_com_preview(
            processo_referencia,
            ce_mercante=ce_mercante,
            parcela=parcela,
            session_id=session_id,
        )

