import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def inicializar_json_consolidado(processo_referencia: str, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Cria a estrutura base do JSON consolidado do processo.
    """
    now_dt = now or datetime.now()
    return {
        "meta": {
            "schema_version": "2.0",
            "id": processo_referencia,
            "closed": False,
            "last_updated": now_dt.isoformat() + "Z",
        },
        "chaves": {},
        "declaracao": None,
        "declaracoes": [],  # Lista de declarações (DI e DUIMP)
        "movimentacao": {"legs": []},
        "carga": {},
        "valores": {},
        "tributos": {
            "pagamentos": [],
            "sumario": {"total_brl": 0.0, "icms": {}},
            "afrmm_tum": {
                "afrmm_evento_pagamento": 0.0,
                "afrmm_saldo_ce": 0.0,
                "tum_devida": 0.0,
                "pago": False,
            },
        },
        "timeline": {},
        "semantica": {"resumo_pt": "", "keyphrases": [], "entities": {"cnpjs": [], "ids": []}},
        "pendencias": {"frete": False, "afrmm": False, "tum": False, "bloqueios": []},
        "alertas": [],
    }

