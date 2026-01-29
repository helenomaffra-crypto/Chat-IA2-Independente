"""
Cliente mínimo para a API oficial do ShipsGo.

Este projeto tem duas "famílias" de API do ShipsGo:

1) **API v2 (OpenAPI 3.0 / api.shipsgo.com)**  ✅ (preferida)
   - Base URL: https://api.shipsgo.com/v2
   - Auth: header `X-Shipsgo-User-Token: <token>`
   - Endpoint: /ocean/shipments/{shipment_id}
   - Resposta contém `movements[]` com `event`, `timestamp`, `location`, `vessel`.

2) **API v1.2 (shipsgo.com/api/v1.2/ContainerService)** (legada)
   - Auth: query param `authCode=...`
   - Endpoint: /ContainerService/GetContainerInfo/?authCode=...&requestId=...

Aqui implementamos **v2** como padrão; v1.2 fica como fallback opcional.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests


class ShipsGoApiError(RuntimeError):
    pass


def _get_base_url_v1_2() -> str:
    return (os.getenv("SHIPSGO_API_BASE_URL_V1_2") or "https://shipsgo.com/api/v1.2").rstrip("/")


def _get_base_url_v2() -> str:
    return (os.getenv("SHIPSGO_API_BASE_URL") or "https://api.shipsgo.com/v2").rstrip("/")


def _get_v2_user_token() -> str:
    """
    Token da API v2 (OpenAPI) usado no header `X-Shipsgo-User-Token`.

    OBS: no seu ambiente vocês estão usando `SHIPSGO_API_KEY` para esse token.
    """
    token = (
        os.getenv("SHIPSGO_USER_TOKEN")
        or os.getenv("SHIPSGO_API_KEY")
        or ""
    ).strip()
    if not token:
        raise ShipsGoApiError("Token ShipsGo v2 ausente (configure SHIPSGO_API_KEY ou SHIPSGO_USER_TOKEN).")
    return token


def _get_v1_auth_code() -> str:
    """
    authCode da API v1.2 (ContainerService) usado como query param.

    ⚠️ IMPORTANTE: não misturar com o token v2.
    """
    auth_code = (os.getenv("SHIPSGO_AUTHCODE") or os.getenv("SHIPSGO_V1_AUTHCODE") or "").strip()
    if not auth_code:
        raise ShipsGoApiError("authCode ShipsGo v1.2 ausente (configure SHIPSGO_AUTHCODE).")
    return auth_code


class ShipsGoApiClient:
    def __init__(self, *, timeout_s: int = 20) -> None:
        self._timeout_s = timeout_s
        self._base_url_v2 = _get_base_url_v2()
        self._base_url_v1_2 = _get_base_url_v1_2()
        self._v2_token = _get_v2_user_token()
        # v1.2 é opcional; só carrega quando precisar
        self._v1_auth_code: Optional[str] = None

    def get_ocean_shipment(self, *, shipment_id: str) -> Dict[str, Any]:
        """Consulta detalhes de um embarque marítimo por shipment_id (ShipsGo API v2)."""
        sid = str(shipment_id).strip()
        if not sid:
            raise ShipsGoApiError("shipment_id vazio")

        url = f"{self._base_url_v2}/ocean/shipments/{sid}"
        headers = {"X-Shipsgo-User-Token": self._v2_token}
        resp = requests.get(url, headers=headers, timeout=self._timeout_s)
        if resp.status_code >= 400:
            raise ShipsGoApiError(f"HTTP {resp.status_code} ao consultar ShipsGo: {resp.text[:200]}")

        try:
            data = resp.json()
        except Exception as e:
            raise ShipsGoApiError(f"Resposta inválida do ShipsGo (não JSON): {e}") from e

        if not isinstance(data, dict):
            raise ShipsGoApiError(f"Resposta inválida do ShipsGo (esperado dict, veio {type(data).__name__})")

        # Alguns retornos trazem Message/Status de negócio; não falhamos aqui para não perder payload.
        return data

    def get_air_shipment(self, *, shipment_id: str) -> Dict[str, Any]:
        """Consulta detalhes de um embarque aéreo por shipment_id (ShipsGo API v2)."""
        sid = str(shipment_id).strip()
        if not sid:
            raise ShipsGoApiError("shipment_id vazio")

        url = f"{self._base_url_v2}/air/shipments/{sid}"
        headers = {"X-Shipsgo-User-Token": self._v2_token}
        resp = requests.get(url, headers=headers, timeout=self._timeout_s)
        if resp.status_code >= 400:
            raise ShipsGoApiError(f"HTTP {resp.status_code} ao consultar ShipsGo: {resp.text[:200]}")

        try:
            data = resp.json()
        except Exception as e:
            raise ShipsGoApiError(f"Resposta inválida do ShipsGo (não JSON): {e}") from e

        if not isinstance(data, dict):
            raise ShipsGoApiError(
                f"Resposta inválida do ShipsGo (esperado dict, veio {type(data).__name__})"
            )
        return data


    def get_container_info_v1_2(self, *, request_id: str) -> Dict[str, Any]:
        """Consulta container info por requestId (ShipsGo API v1.2 ContainerService)."""
        rid = str(request_id).strip()
        if not rid:
            raise ShipsGoApiError("request_id vazio")

        if not self._v1_auth_code:
            self._v1_auth_code = _get_v1_auth_code()

        url = f"{self._base_url_v1_2}/ContainerService/GetContainerInfo/"
        params = {"authCode": self._v1_auth_code, "requestId": rid}
        resp = requests.get(url, params=params, timeout=self._timeout_s)
        if resp.status_code >= 400:
            raise ShipsGoApiError(f"HTTP {resp.status_code} ao consultar ShipsGo: {resp.text[:200]}")

        try:
            data = resp.json()
        except Exception as e:
            raise ShipsGoApiError(f"Resposta inválida do ShipsGo (não JSON): {e}") from e

        if not isinstance(data, dict):
            raise ShipsGoApiError(
                f"Resposta inválida do ShipsGo (esperado dict, veio {type(data).__name__})"
            )
        return data


def parse_ocean_shipment_to_tracking(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Extrai campos úteis para o cache `shipsgo_tracking` a partir da API v2.

    Heurística (robusta para escala/transbordo):
    - Percorrer `shipment.containers[].movements[]`
    - Selecionar o movimento "mais destino" para ETA:
      - Preferir eventos DISC > ARRV
      - Entre eles, pegar o MAIOR timestamp (última perna)
    - Porto: movement.location.unlocode + movement.location.name
    - Navio: movement.vessel.name
    - Status: shipment.status (quando existir), senão movement.status (ACT/EST)
    """
    if not isinstance(data, dict):
        return {"eta_iso": None, "porto_nome": None, "porto_codigo": None, "status": None, "navio": None}

    shipment = data.get("shipment") if isinstance(data.get("shipment"), dict) else data
    status_shipment = shipment.get("status") if isinstance(shipment, dict) else None

    containers = shipment.get("containers") if isinstance(shipment, dict) else None
    if not isinstance(containers, list):
        return {"eta_iso": None, "porto_nome": None, "porto_codigo": None, "status": str(status_shipment) if status_shipment else None, "navio": None}

    best = None  # (rank_event, timestamp, movement_dict)
    for c in containers:
        if not isinstance(c, dict):
            continue
        movements = c.get("movements")
        if not isinstance(movements, list):
            continue
        for m in movements:
            if not isinstance(m, dict):
                continue
            ev = (m.get("event") or "").upper()
            ts = m.get("timestamp")
            if not ts:
                continue
            if ev not in ("DISC", "ARRV"):
                continue
            rank = 2 if ev == "DISC" else 1
            key = (rank, str(ts))
            if best is None or key > (best[0], best[1]):
                best = (rank, str(ts), m)

    if not best:
        return {"eta_iso": None, "porto_nome": None, "porto_codigo": None, "status": str(status_shipment) if status_shipment else None, "navio": None}

    m = best[2]
    loc = m.get("location") if isinstance(m.get("location"), dict) else {}
    vessel = m.get("vessel") if isinstance(m.get("vessel"), dict) else {}

    porto_codigo = loc.get("unlocode") or loc.get("unlocode_code") or None
    porto_nome = loc.get("name") or None
    navio = vessel.get("name") or None

    # status: preferir status do shipment; senão o status do movimento (ACT/EST)
    status = status_shipment or m.get("status")

    return {
        "eta_iso": m.get("timestamp"),
        "porto_nome": str(porto_nome) if porto_nome else None,
        "porto_codigo": str(porto_codigo) if porto_codigo else None,
        "status": str(status) if status else None,
        "navio": str(navio) if navio else None,
    }


def parse_container_info_v1_2_to_tracking(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Extrai campos úteis para o cache `shipsgo_tracking` a partir da API v1.2.

    Campos comuns:
    - Pod (nome)
    - Vessel (nome)
    - Status
    - DischargeDate.Date / ArrivalDate.Date / ETA / FirstETA
    """
    if not isinstance(data, dict):
        return {"eta_iso": None, "porto_nome": None, "porto_codigo": None, "status": None, "navio": None}

    def _get_date_field(obj: Any) -> Optional[str]:
        if isinstance(obj, dict):
            v = obj.get("Date") or obj.get("date")
            return str(v) if v else None
        if isinstance(obj, str):
            return obj
        return None

    discharge = _get_date_field(data.get("DischargeDate"))
    arrival = _get_date_field(data.get("ArrivalDate"))
    eta = data.get("ETA")
    first_eta = data.get("FirstETA")

    eta_iso = None
    for cand in [discharge, arrival, str(eta) if eta else None, str(first_eta) if first_eta else None]:
        if cand and str(cand).strip():
            eta_iso = str(cand).strip()
            break

    porto_nome = data.get("Pod") or data.get("POD") or None
    navio = data.get("Vessel") or None
    status = data.get("Status") or None

    # v1.2 geralmente não traz UN/LOCODE
    porto_codigo = None

    return {
        "eta_iso": eta_iso,
        "porto_nome": str(porto_nome) if porto_nome else None,
        "porto_codigo": str(porto_codigo) if porto_codigo else None,
        "status": str(status) if status else None,
        "navio": str(navio) if navio else None,
    }


def parse_air_shipment_to_tracking(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Extrai campos úteis para o cache `shipsgo_tracking` a partir da API v2 (aéreo).

    Heurística:
    - Percorrer `shipment.movements[]`
    - Selecionar o movimento "mais destino" para ETA:
      - Preferir DLV > ARR > RCF > DEP
      - Entre eles, pegar o MAIOR timestamp
    - "porto" aqui vira aeroporto: location.iata + location.name
    - Campo `navio` do cache recebe o número do voo (flight) quando disponível
    - Status: shipment.status
    """
    if not isinstance(data, dict):
        return {"eta_iso": None, "porto_nome": None, "porto_codigo": None, "status": None, "navio": None}

    shipment = data.get("shipment") if isinstance(data.get("shipment"), dict) else data
    status_shipment = shipment.get("status") if isinstance(shipment, dict) else None

    movements = shipment.get("movements") if isinstance(shipment, dict) else None
    if not isinstance(movements, list):
        return {"eta_iso": None, "porto_nome": None, "porto_codigo": None, "status": str(status_shipment) if status_shipment else None, "navio": None}

    rank_map = {"DEP": 1, "RCF": 2, "ARR": 3, "DLV": 4}
    best = None  # (rank, timestamp, movement_dict)
    for m in movements:
        if not isinstance(m, dict):
            continue
        ev = (m.get("event") or "").upper()
        ts = m.get("timestamp")
        if not ts or ev not in rank_map:
            continue
        key = (rank_map[ev], str(ts))
        if best is None or key > (best[0], best[1]):
            best = (key[0], key[1], m)

    if not best:
        return {"eta_iso": None, "porto_nome": None, "porto_codigo": None, "status": str(status_shipment) if status_shipment else None, "navio": None}

    m = best[2]
    loc = m.get("location") if isinstance(m.get("location"), dict) else {}
    porto_codigo = loc.get("iata") or None
    porto_nome = loc.get("name") or None
    flight = m.get("flight") or None

    return {
        "eta_iso": m.get("timestamp"),
        "porto_nome": str(porto_nome) if porto_nome else None,
        "porto_codigo": str(porto_codigo) if porto_codigo else None,
        "status": str(status_shipment) if status_shipment else (str(m.get("status")) if m.get("status") else None),
        "navio": str(flight) if flight else None,
    }

