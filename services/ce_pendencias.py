import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def calcular_pendencias_ce(ce_json: Dict[str, Any], numero_ce: str, processo_referencia: str) -> Tuple[bool, bool, Optional[Dict[str, Any]]]:
    """
    Calcula pendências do CE marítimo.

    Returns:
        (pendencia_afrmm, pendencia_frete, pendencia_frete_detalhes)
    """
    afrmm_tum_pago = ce_json.get("afrmmTUMPago", True)
    pendencia_afrmm = not afrmm_tum_pago

    pendencia_frete = False
    pendencia_frete_detalhes: Optional[Dict[str, Any]] = None

    tipo_ce = ce_json.get("tipo", "")
    tipo_ce_upper = tipo_ce.upper() if isinstance(tipo_ce, str) else ""
    ce_tipo_valido_para_pendencia = tipo_ce_upper == "BL"

    if not ce_tipo_valido_para_pendencia:
        logger.debug(
            f'⚠️ CE {numero_ce}: Tipo "{tipo_ce_upper}" não suporta verificação de pendência de frete (apenas BL). '
            f"Ignorando pendenciaFrete."
        )
        return pendencia_afrmm, False, None

    pendencia_frete_raw = ce_json.get("pendenciaFrete", False)
    logger.debug(
        f"🔍 CE {numero_ce}: pendenciaFrete_raw do JSON = {pendencia_frete_raw} "
        f"(tipo: {type(pendencia_frete_raw).__name__})"
    )

    if isinstance(pendencia_frete_raw, bool):
        pendencia_frete = pendencia_frete_raw
    elif isinstance(pendencia_frete_raw, list):
        if len(pendencia_frete_raw) == 0:
            pendencia_frete = False
        else:
            itens_com_data = []
            for item in pendencia_frete_raw:
                if not isinstance(item, dict):
                    continue
                item_data = item.get("dataRegistroPendenciaFrete", "")
                if item_data:
                    try:
                        item_dt = datetime.fromisoformat(item_data.replace("Z", "+00:00"))
                        itens_com_data.append((item_dt, item))
                    except Exception as e:
                        logger.debug(f"⚠️ CE {numero_ce}: Erro ao parsear dataRegistroPendenciaFrete: {e}")
                        itens_com_data.append((datetime.min, item))
                else:
                    itens_com_data.append((datetime.min, item))

            if itens_com_data:
                itens_com_data.sort(key=lambda x: x[0], reverse=True)
                item_mais_recente = itens_com_data[0][1]
                item_pendencia = item_mais_recente.get("pendenciaFrete", False)
                logger.debug(
                    f"🔍 CE {numero_ce}: Item mais recente do array pendenciaFrete - "
                    f"item_pendencia={item_pendencia} (tipo: {type(item_pendencia).__name__}), "
                    f"data={item_mais_recente.get('dataRegistroPendenciaFrete', 'N/A')}"
                )

                if (
                    item_pendencia is True
                    or item_pendencia == "true"
                    or str(item_pendencia).lower() == "true"
                    or item_pendencia == 1
                ):
                    pendencia_frete = True
                    pendencia_frete_detalhes = item_mais_recente
                    logger.debug(
                        f"✅ CE {numero_ce}: Pendência de frete detectada no item mais recente "
                        f"(dataRegistroPendenciaFrete={item_mais_recente.get('dataRegistroPendenciaFrete', 'N/A')})"
                    )
                else:
                    pendencia_frete = False
                    logger.debug(
                        f"✅ CE {numero_ce}: Pendência de frete RESOLVIDA (último item com pendenciaFrete=false, "
                        f"dataRegistroPendenciaFrete={item_mais_recente.get('dataRegistroPendenciaFrete', 'N/A')})"
                    )
            else:
                pendencia_frete = False
                logger.warning(
                    f"⚠️ CE {numero_ce}: Array pendenciaFrete não pôde ser processado, assumindo sem pendência"
                )

    if not pendencia_frete:
        indicador_pendencia_frete = ce_json.get("indicadorPendenciaFrete", False)
        if indicador_pendencia_frete is True or indicador_pendencia_frete == "true" or str(indicador_pendencia_frete).lower() == "true":
            pendencia_frete = True
            logger.debug(f"✅ CE {numero_ce}: Pendência de frete detectada via indicadorPendenciaFrete")
            if (
                not pendencia_frete_detalhes
                and isinstance(pendencia_frete_raw, list)
                and len(pendencia_frete_raw) > 0
                and isinstance(pendencia_frete_raw[0], dict)
            ):
                pendencia_frete_detalhes = pendencia_frete_raw[0]

    if pendencia_frete:
        logger.info(f"✅ CE {numero_ce}: Pendência de frete FINAL = True (processo {processo_referencia})")
    else:
        logger.info(f"⚠️ CE {numero_ce}: Pendência de frete FINAL = False (processo {processo_referencia})")

    return pendencia_afrmm, pendencia_frete, pendencia_frete_detalhes

