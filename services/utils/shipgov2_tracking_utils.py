"""
Utilitários para interpretar tracking do ShipsGo dentro do `shipgov2` (Kanban).

Problema recorrente: processos com escala/transbordo podem trocar de navio.
O Kanban armazena uma lista de eventos e um `destino_codigo` (POD). Para exibição
confiável, precisamos:
- ETA (POD): preferir evento DISC no destino; senão ARRV no destino; senão destino_data_chegada.
- Navio: preferir navio do evento do POD (DISC/ARRV); senão último navio conhecido.
- Status: não confiar cegamente em shipgov2.status (às vezes fica "BOOKED" mesmo em viagem);
          derivar a partir do último evento passado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Shipgov2Resumo:
    eta_pod: Optional[datetime]
    navio_pod: Optional[str]
    status: Optional[str]


def _parse_dt(dt_raw: Optional[str]) -> Optional[datetime]:
    """Parse robusto de datetime ISO, tolerando timezone e 'Z'."""
    if not dt_raw:
        return None
    try:
        s = str(dt_raw).strip()
        s = s.replace("Z", "")
        # remover timezone tipo -03:00 / +03:00 (evita aware vs naive)
        # shipgov2 costuma vir sem timezone, mas não custa.
        if len(s) >= 6 and (s[-6] in ("+", "-")) and s[-3] == ":":
            s = s[:-6]
        s = s.split(".")[0]  # remover ms
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _eventos_normalizados(shipgov2: Dict[str, Any]) -> List[Dict[str, Any]]:
    eventos = shipgov2.get("eventos") or []
    if not isinstance(eventos, list):
        return []
    norm: List[Dict[str, Any]] = []
    for e in eventos:
        if not isinstance(e, dict):
            continue
        dt = _parse_dt(e.get("atual_data_evento"))
        if not dt:
            continue
        norm.append(
            {
                "evento": (e.get("atual_evento") or "").strip().upper(),
                "codigo": (e.get("atual_codigo") or "").strip().upper(),
                "nome": (e.get("atual_nome") or "").strip(),
                "dt": dt,
                "navio": e.get("navio_shipv2") or e.get("navio") or e.get("navio_ship"),
            }
        )
    return norm


def _pick_latest(
    eventos: List[Dict[str, Any]],
    *,
    codigo: Optional[str] = None,
    tipos: Optional[Tuple[str, ...]] = None,
) -> Optional[Dict[str, Any]]:
    filtro = eventos
    if codigo:
        codigo_u = codigo.strip().upper()
        filtro = [e for e in filtro if e.get("codigo") == codigo_u]
    if tipos:
        tipos_u = {t.upper() for t in tipos}
        filtro = [e for e in filtro if (e.get("evento") or "").upper() in tipos_u]
    if not filtro:
        return None
    return max(filtro, key=lambda e: e.get("dt") or datetime.min)


def resumir_shipgov2_para_painel(
    shipgov2: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
) -> Shipgov2Resumo:
    """Extrai ETA(POD), navio(POD) e status derivado dos eventos."""
    if not isinstance(shipgov2, dict):
        return Shipgov2Resumo(eta_pod=None, navio_pod=None, status=None)

    destino = (shipgov2.get("destino_codigo") or "").strip().upper() or None
    eventos = _eventos_normalizados(shipgov2)

    # ETA(POD): DISC no destino > ARRV no destino > destino_data_chegada
    evt_disc_dest = _pick_latest(eventos, codigo=destino, tipos=("DISC",)) if destino else None
    evt_arrv_dest = _pick_latest(eventos, codigo=destino, tipos=("ARRV",)) if destino else None
    eta_dt = (evt_disc_dest or evt_arrv_dest or {}).get("dt")
    if not eta_dt:
        eta_dt = _parse_dt(shipgov2.get("destino_data_chegada"))

    # Navio: preferir navio do evento do POD (DISC/ARRV) > último navio no destino > último navio global
    navio = None
    for candidate in (evt_disc_dest, evt_arrv_dest):
        if candidate and candidate.get("navio"):
            navio = str(candidate.get("navio")).strip()
            break
    if not navio and destino:
        last_any_dest = _pick_latest(eventos, codigo=destino, tipos=None)
        if last_any_dest and last_any_dest.get("navio"):
            navio = str(last_any_dest.get("navio")).strip()
    if not navio:
        last_any = _pick_latest(eventos, codigo=None, tipos=None)
        if last_any and last_any.get("navio"):
            navio = str(last_any.get("navio")).strip()

    # Status: derivar do último evento passado (evita shipgov2.status ficar "BOOKED" indevidamente)
    if now is None:
        now = datetime.now()
    status = None
    eventos_passados = [e for e in eventos if isinstance(e.get("dt"), datetime) and e["dt"] <= now]
    ultimo_passado = max(eventos_passados, key=lambda e: e["dt"], default=None)
    if ultimo_passado:
        ev = (ultimo_passado.get("evento") or "").upper()
        cod = (ultimo_passado.get("codigo") or "").upper()
        if destino and cod == destino and ev in ("DISC", "ARRV"):
            status = "ARRIVED"
        # Se não chegou no destino, mas já teve embarque/saída em algum ponto, considerar em viagem.
        # (caso típico: escala/transbordo com ARRV em porto intermediário)
        if not status:
            teve_saida_ou_embarque = any(
                (e.get("evento") or "").upper() in ("DEPA", "LOAD") for e in eventos_passados
            )
            if teve_saida_ou_embarque:
                status = "SAILING"
    if not status:
        raw = shipgov2.get("status")
        if isinstance(raw, str) and raw.strip():
            status = raw.strip().upper()

    return Shipgov2Resumo(eta_pod=eta_dt, navio_pod=navio, status=status)

