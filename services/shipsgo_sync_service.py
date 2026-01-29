"""
ShipsGoSyncService

Responsabilidade:
- Sincronizar tracking oficial do ShipsGo (API) para o cache SQLite `shipsgo_tracking`.

Princípios:
- Conservador com custo: só chama API se houver `requestId` (id_externo_shipsgo) e se o cache estiver ausente/antigo.
- Não bloqueia sincronização do Kanban: falhas são logadas e retornam sem quebrar o fluxo.
"""

from __future__ import annotations

import logging
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from db_manager import get_db_connection, shipsgo_upsert_tracking
from utils.shipsgo_api import (
    ShipsGoApiClient,
    ShipsGoApiError,
    parse_container_info_v1_2_to_tracking,
    parse_air_shipment_to_tracking,
    parse_ocean_shipment_to_tracking,
)

logger = logging.getLogger(__name__)


class ShipsGoSyncService:
    # Circuit breaker simples para não spammar logs/credits em caso de auth inválida
    _disabled_until: Optional[datetime] = None

    def __init__(self, *, ttl_minutes: int = 60, timeout_s: int = 20) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._client = ShipsGoApiClient(timeout_s=timeout_s)

    def _needs_refresh(self, processo_referencia: str) -> bool:
        try:
            conn = get_db_connection()
            conn.row_factory = None
            cur = conn.cursor()
            cur.execute(
                """
                SELECT atualizado_em
                FROM shipsgo_tracking
                WHERE processo_referencia = ?
                """,
                (processo_referencia,),
            )
            row = cur.fetchone()
            conn.close()
            if not row or not row[0]:
                return True
            try:
                # SQLite geralmente salva como "YYYY-MM-DD HH:MM:SS"
                ts = str(row[0]).replace("T", " ").split(".")[0]
                last = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except Exception:
                return True
            return (datetime.now() - last) > self._ttl
        except Exception:
            return True

    @staticmethod
    def _extract_request_id_from_kanban_json(processo_json: Dict[str, Any]) -> Optional[str]:
        dados = processo_json.get("dados_processo_kanban") or {}
        rid = (
            dados.get("id_externo_shipsgo")
            or processo_json.get("id_externo_shipsgo")
            or processo_json.get("requestId")
            or processo_json.get("request_id")
        )
        rid = str(rid).strip() if rid is not None else ""
        return rid or None

    def sync_from_kanban_snapshot(self, *, processo_referencia: str, processo_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincroniza tracking do ShipsGo para um processo, usando requestId do snapshot do Kanban.
        """
        proc = (processo_referencia or "").strip().upper()
        if not proc:
            return {"sucesso": False, "erro": "PROCESSO_VAZIO"}

        shipment_id = self._extract_request_id_from_kanban_json(processo_json)
        if not shipment_id:
            return {"sucesso": False, "erro": "SHIPMENT_ID_AUSENTE"}

        if self.__class__._disabled_until and datetime.now() < self.__class__._disabled_until:
            return {"sucesso": True, "pulado": True, "motivo": "AUTH_DISABLED"}

        if not self._needs_refresh(proc):
            return {"sucesso": True, "pulado": True, "motivo": "TTL"}

        try:
            # Detectar modal (Aéreo vs Marítimo) a partir do snapshot do Kanban.
            modal_raw = (
                processo_json.get("modal")
                or (processo_json.get("dados_processo_kanban") or {}).get("modal")
                or ""
            )
            modal_lower = str(modal_raw).strip().lower()
            # Normalizar acentos: "Aéreo" -> "aereo"
            modal_norm = "".join(
                ch for ch in unicodedata.normalize("NFKD", modal_lower) if not unicodedata.combining(ch)
            )
            is_air = ("aer" in modal_norm) or ("air" in modal_norm)

            # AUTO: tentar v2 primeiro (OpenAPI). Se falhar com "Invalid Authentication Code", tentar v1.2.
            payload = None
            parsed = None
            try:
                if is_air:
                    payload = self._client.get_air_shipment(shipment_id=shipment_id)
                    parsed = parse_air_shipment_to_tracking(payload)
                else:
                    payload = self._client.get_ocean_shipment(shipment_id=shipment_id)
                    parsed = parse_ocean_shipment_to_tracking(payload)
            except ShipsGoApiError as e_v2:
                msg = str(e_v2)
                if "HTTP 401" in msg and "Invalid Authentication" in msg:
                    # Provável: token v2 inválido (ou usando authCode errado). NÃO tentar v1.2 sem authCode configurado.
                    try:
                        payload = self._client.get_container_info_v1_2(request_id=shipment_id)
                        parsed = parse_container_info_v1_2_to_tracking(payload)
                    except ShipsGoApiError:
                        # Se não tiver authCode v1.2, retornar o erro do v2 para orientar config.
                        raise
                else:
                    raise

            parsed = parsed or {"eta_iso": None, "porto_codigo": None, "porto_nome": None, "status": None, "navio": None}

            ok = shipsgo_upsert_tracking(
                processo_referencia=proc,
                eta_iso=parsed.get("eta_iso"),
                porto_codigo=parsed.get("porto_codigo"),
                porto_nome=parsed.get("porto_nome"),
                navio=parsed.get("navio"),
                payload_raw=payload,
                status=parsed.get("status"),
            )

            return {
                "sucesso": bool(ok),
                "processo_referencia": proc,
                "shipment_id": shipment_id,
                "eta_iso": parsed.get("eta_iso"),
                "porto_nome": parsed.get("porto_nome"),
                "navio": parsed.get("navio"),
                "status": parsed.get("status"),
            }
        except ShipsGoApiError as e:
            # 404 é comum quando o shipment_id não existe na API v2 (ou ainda não foi criado).
            # Não queremos poluir logs com WARNING em cada sync do Kanban.
            if "HTTP 404" in str(e):
                logger.info(f"ℹ️ ShipsGo: shipment não encontrado para {proc}: {e}")
                return {"sucesso": True, "pulado": True, "motivo": "NOT_FOUND", "processo_referencia": proc, "shipment_id": shipment_id}

            logger.warning(f"⚠️ ShipsGo API error para {proc}: {e}")
            # Se auth inválida, desabilitar por 30 minutos para evitar spam
            if "HTTP 401" in str(e) and "Invalid Authentication" in str(e):
                self.__class__._disabled_until = datetime.now() + timedelta(minutes=30)
            return {"sucesso": False, "erro": str(e), "processo_referencia": proc, "shipment_id": shipment_id}
        except Exception as e:
            logger.warning(f"⚠️ Erro inesperado no ShipsGoSyncService para {proc}: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "processo_referencia": proc, "shipment_id": shipment_id}

