"""
SalesWatchService
-----------------
Monitora (polling) "vendas de hoje" no legado Make/Spalla e cria notificações
quando surgirem novas NFs para termos monitorados.

Ativação via .env:
- SALES_WATCH_ENABLED=true|false
- SALES_WATCH_INTERVAL_MINUTES=15
- SALES_WATCH_TERMS=rastreadoe,alho,hikvision
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from db_manager import get_db_connection
from services.notificacao_service import NotificacaoService
from services.vendas_make_service import VendasMakeService

logger = logging.getLogger(__name__)


def _today_range() -> Tuple[str, str]:
    dt = date.today()
    ini = dt.isoformat()
    fim = (dt + timedelta(days=1)).isoformat()
    return ini, fim


def _parse_terms_env(raw: str) -> List[str]:
    parts = [p.strip() for p in (raw or "").split(",")]
    out = []
    for p in parts:
        if not p:
            continue
        if p.lower() not in [x.lower() for x in out]:
            out.append(p)
    return out


def _row_key(row: Dict[str, Any]) -> str:
    # chave estável (best-effort) para detectar "NF nova"
    nf = str(row.get("numero_nf") or "").strip()
    emp = str(row.get("empresa_vendedora") or "").strip()
    data = str(row.get("data_emissao") or "").strip()
    total = str(row.get("total_nf") or "").strip()
    return "|".join([data, emp, nf, total])


def _fmt_brl(v: Any) -> str:
    try:
        n = float(v)
    except Exception:
        return "" if v is None else str(v)
    s = f"{n:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


@dataclass
class WatchResult:
    termo: str
    novas: List[Dict[str, Any]]
    total_novas: float


class SalesWatchService:
    def __init__(self) -> None:
        self._svc = VendasMakeService()
        self._notificacao = NotificacaoService()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            from services.sales_watch_schema import criar_tabela_sales_watch_state

            criar_tabela_sales_watch_state(cur)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ [SALES_WATCH] Não foi possível garantir schema: {e}", exc_info=True)

    def _load_seen(self, termo: str) -> Set[str]:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT seen_keys_json FROM sales_watch_state WHERE termo = ?", (termo,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return set()
            raw = row[0]
            if not raw:
                return set()
            data = json.loads(raw)
            if isinstance(data, list):
                return set(str(x) for x in data if x)
            return set()
        except Exception:
            return set()

    def _save_seen(self, termo: str, seen: Set[str], max_keep: int = 2000) -> None:
        try:
            # limitar tamanho
            lst = list(seen)
            if len(lst) > max_keep:
                lst = lst[-max_keep:]
            payload = json.dumps(lst)
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sales_watch_state(termo, seen_keys_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(termo) DO UPDATE SET
                    seen_keys_json=excluded.seen_keys_json,
                    updated_at=excluded.updated_at
                """,
                (termo, payload, datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ [SALES_WATCH] Erro ao salvar estado: {e}", exc_info=True)

    def check_once(self, *, termos: List[str]) -> List[WatchResult]:
        """
        Roda uma vez: para cada termo, busca vendas por NF de HOJE e detecta NFs novas.
        """
        if not self._svc.is_ready():
            logger.info("[SALES_WATCH] SQL adapter indisponível; pulando.")
            return []

        ini, fim = _today_range()
        results: List[WatchResult] = []

        for termo in termos:
            seen = self._load_seen(termo)
            resp = self._svc.consultar_vendas_por_nf(inicio=ini, fim=fim, termo=termo, top=250)
            if not resp.get("sucesso"):
                continue
            rows = resp.get("dados") or []
            novas: List[Dict[str, Any]] = []
            total_novas = 0.0
            for r in rows:
                if not isinstance(r, dict):
                    continue
                k = _row_key(r)
                if k and k not in seen:
                    novas.append(r)
                    try:
                        total_novas += float(r.get("total_nf") or 0.0)
                    except Exception:
                        pass
                if k:
                    seen.add(k)

            # persistir sempre (para não duplicar no próximo tick)
            self._save_seen(termo, seen)

            if novas:
                results.append(WatchResult(termo=termo, novas=novas, total_novas=total_novas))

        return results

    def notificar(self, results: List[WatchResult]) -> int:
        """
        Cria notificações no SQLite (notificacoes_processos) para os resultados.
        """
        created = 0
        for r in results:
            linhas = []
            for nf in r.novas[:10]:
                linhas.append(
                    f"- {nf.get('data_emissao')} | NF {nf.get('numero_nf')} | {_fmt_brl(nf.get('total_nf'))}"
                )
            if len(r.novas) > 10:
                linhas.append(f"... (+{len(r.novas) - 10} NF(s))")

            msg = (
                f"📈 **Venda detectada (HOJE)**\n\n"
                f"Termo monitorado: **{r.termo}**\n"
                f"Novas NFs: **{len(r.novas)}**\n"
                f"Total (novas): **{_fmt_brl(r.total_novas)}**\n\n"
                + "\n".join(linhas)
                + "\n\n💡 Abra o chat e peça: \"vendas por NF de {termo} hoje\" para ver tudo."
            )

            notif = {
                "processo_referencia": "SISTEMA",
                "tipo_notificacao": "vendas_watch",
                "titulo": f"💰 Venda hoje: {r.termo} (+{len(r.novas)} NF)",
                "mensagem": msg,
                "dados_extras": {"termo": r.termo, "count": len(r.novas)},
            }
            ok = self._notificacao._salvar_notificacao(notif)
            if ok:
                created += 1
        return created


def watch_enabled() -> bool:
    return os.getenv("SALES_WATCH_ENABLED", "false").lower() == "true"


def get_watch_terms() -> List[str]:
    raw = os.getenv("SALES_WATCH_TERMS", "").strip()
    if not raw:
        # vazio = não faz nada
        return []
    return _parse_terms_env(raw)

