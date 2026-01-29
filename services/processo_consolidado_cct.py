import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def processar_ccts(json_consolidado: Dict[str, Any], ccts: List[Dict[str, Any]]) -> None:
    """
    Processa CCTs no JSON consolidado:
    - legs (movimentação aérea)
    - pendências/alertas básicas
    - chaves (RUC)
    """
    for cct in ccts:
        cct_numero = cct.get("numero", "")

        leg: Dict[str, Any] = {
            "fonte": "CCT",
            "modal": "aereo",
            "status": {
                "situacao": cct.get("situacao_atual", ""),
                "entrega_autorizada": cct.get("situacao_atual") == "ENTREGUE",
                "bloqueios": {
                    "impede_entrega": False,
                    "impende_vinculacao": cct.get("tem_bloqueios", False),
                    "lista": cct.get("bloqueios_ativos", []),
                },
                "afrmm_tum_pago": True,
            },
            "rota": {
                "origem_di": cct.get("aeroporto_origem", ""),
                "origem_ce_codigo": cct.get("aeroporto_origem", ""),
                "destino_ce_codigo": cct.get("aeroporto_destino", ""),
                "viagem": {
                    "id": None,
                    "chegada_efetiva": cct.get("data_chegada_efetiva", ""),
                    "aeroporto_chegada": cct.get("aeroporto_destino", ""),
                },
            },
            "armazenagem": {},
            "veiculo": {},
        }

        json_consolidado["movimentacao"]["legs"].append(leg)

        if cct.get("pendencia_frete", False):
            json_consolidado["pendencias"]["frete"] = True

        if cct.get("tem_bloqueios", False):
            json_consolidado["alertas"].append(
                {"tipo": "bloqueio", "nivel": "error", "documento": f"CCT {cct_numero}", "mensagem": "Carga bloqueada"}
            )

        ruc = cct.get("ruc", "")
        if ruc:
            json_consolidado["chaves"]["ruc"] = ruc

