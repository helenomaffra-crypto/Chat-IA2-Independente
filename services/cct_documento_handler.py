import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.iata_to_country import iata_to_country_code

logger = logging.getLogger(__name__)

_AIRPORTS_CACHE: Optional[Any] = None


def _pais_procedencia_por_iata(aeroporto_origem: str) -> Optional[str]:
    if not aeroporto_origem:
        return None

    codigo_iata_limpo = str(aeroporto_origem).strip().upper()
    if not codigo_iata_limpo:
        return None

    # 1) tentar tabela leve (mais estável, sem IO)
    pais = iata_to_country_code(codigo_iata_limpo)
    if pais:
        return str(pais).strip().upper()

    # 2) fallback: airports.json (quando existe no projeto)
    global _AIRPORTS_CACHE
    airports_file = Path("airports.json")
    if not airports_file.exists():
        return None

    if _AIRPORTS_CACHE is None:
        try:
            with open(airports_file, "r", encoding="utf-8") as f:
                _AIRPORTS_CACHE = json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar airports.json: {e}")
            _AIRPORTS_CACHE = {}

    airports_data = _AIRPORTS_CACHE
    try:
        if isinstance(airports_data, dict):
            for _, airport_info in airports_data.items():
                if not isinstance(airport_info, dict):
                    continue
                airport_iata = airport_info.get("iata", "")
                if airport_iata and str(airport_iata).strip().upper() == codigo_iata_limpo:
                    country = airport_info.get("country", "")
                    if country:
                        return str(country).strip().upper()
        elif isinstance(airports_data, list):
            for airport_info in airports_data:
                if not isinstance(airport_info, dict):
                    continue
                airport_iata = airport_info.get("iata", "")
                if airport_iata and str(airport_iata).strip().upper() == codigo_iata_limpo:
                    country = airport_info.get("country", "")
                    if country:
                        return str(country).strip().upper()
    except Exception:
        return None

    return None


def processar_documento_cct(
    processo_referencia: str,
    numero: str,
    *,
    buscar_cct_cache: Callable[[str], Optional[Dict[str, Any]]],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """
    Processa um documento CCT (cache), retornando:
      (cct_data ou None, alertas_cct, tem_bloqueios)
    """
    cct_cache = buscar_cct_cache(numero)
    if not cct_cache:
        return None, [], False

    aeroporto_origem = cct_cache.get("aeroporto_origem", "")
    pais_procedencia = None
    if aeroporto_origem:
        try:
            pais_procedencia = _pais_procedencia_por_iata(aeroporto_origem)
        except Exception as e:
            logger.warning(
                f"Erro ao obter país de procedência para CCT {numero} (aeroporto {aeroporto_origem}): {e}"
            )

    cct_json = cct_cache.get("json_completo", {})
    if isinstance(cct_json, str):
        try:
            cct_json = json.loads(cct_json)
        except Exception:
            cct_json = {}

    if isinstance(cct_json, list) and len(cct_json) > 0:
        cct_json = cct_json[0]
    elif isinstance(cct_json, list):
        cct_json = {}

    if not isinstance(cct_json, dict):
        cct_json = {}

    pendencia_pagamento = cct_json.get("pendenciaPagamento", "N")
    pendencia_frete_cct = pendencia_pagamento == "S"

    tem_bloqueios_cct = cct_cache.get("tem_bloqueios", False)
    if isinstance(tem_bloqueios_cct, int):
        tem_bloqueios_cct = bool(tem_bloqueios_cct)
    elif not isinstance(tem_bloqueios_cct, bool):
        tem_bloqueios_cct = bool(tem_bloqueios_cct)

    cct_data = {
        "numero": numero,
        "tipo": cct_cache.get("tipo", ""),
        "ruc": cct_cache.get("ruc", ""),
        "situacao_atual": cct_cache.get("situacao_atual", ""),
        "data_hora_situacao": cct_cache.get("data_hora_situacao_atual", ""),
        "data_chegada_efetiva": cct_cache.get("data_chegada_efetiva", ""),
        "tem_bloqueios": tem_bloqueios_cct,
        "bloqueios_ativos": cct_cache.get("bloqueios_ativos", []),
        "bloqueios_baixados": cct_cache.get("bloqueios_baixados", []),
        "aeroporto_origem": aeroporto_origem,
        "aeroporto_destino": cct_cache.get("aeroporto_destino", ""),
        "pais_procedencia": pais_procedencia,
        "quantidade_volumes": cct_cache.get("quantidade_volumes", 0),
        "peso_bruto": cct_cache.get("peso_bruto", 0),
        "valor_frete_total": cct_cache.get("valor_frete_total"),
        "moeda_frete": cct_cache.get("moeda_frete", ""),
        "identificacao_documento_consignatario": cct_cache.get("identificacao_documento_consignatario", ""),
        "duimp_vinculada": cct_cache.get("duimp_vinculada"),
        "versao_duimp": cct_cache.get("versao_duimp"),
        "pendencia_frete": pendencia_frete_cct,
        "atualizado_em": cct_cache.get("atualizado_em", ""),
        "dados_completos": cct_json,
    }

    alertas_cct: List[Dict[str, Any]] = []
    tem_bloqueios = False
    if cct_data.get("tem_bloqueios"):
        tem_bloqueios = True
        bloqueios = cct_data.get("bloqueios_ativos")
        if isinstance(bloqueios, list) and len(bloqueios) > 0:
            for bloqueio in bloqueios:
                if not isinstance(bloqueio, dict):
                    continue
                alertas_cct.append(
                    {
                        "tipo": "bloqueio",
                        "nivel": "error",
                        "documento": f"CCT {numero}",
                        "mensagem": f"Bloqueio: {bloqueio.get('tipo', 'Desconhecido')}",
                    }
                )

    return cct_data, alertas_cct, tem_bloqueios

