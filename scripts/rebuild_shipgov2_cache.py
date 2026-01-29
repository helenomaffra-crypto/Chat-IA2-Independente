"""
Rebuild de campos logísticos (ETA/Navio/Status) a partir do shipgov2 no cache SQLite.

Motivação:
- Processos com escala/transbordo podem trocar de navio no trecho final (POD).
- O Kanban armazena `shipgov2.eventos` com ARRV/DISC no destino, mas campos denormalizados
  (`nome_navio`, `status_shipsgo`, `eta_iso`) podem ficar inconsistentes.

O que este script faz:
- Lê `processos_kanban.dados_completos_json`
- Extrai shipgov2 e calcula:
  - ETA(POD): DISC(destino) > ARRV(destino) > destino_data_chegada
  - Navio(POD): navio do evento DISC/ARRV no destino (quando existir)
  - Status: derivado dos eventos (evita ficar "BOOKED" indevidamente)
- Atualiza `processos_kanban` apenas quando houver mudança.

Uso:
  - Dry-run (padrão):  python3 scripts/rebuild_shipgov2_cache.py
  - Aplicar mudanças:  python3 scripts/rebuild_shipgov2_cache.py --apply
  - Limitar amostra:   python3 scripts/rebuild_shipgov2_cache.py --limit 200
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import os
import sys

# Garantir que a raiz do projeto esteja no sys.path quando rodar via `python3 scripts/...`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db_manager import get_db_connection  # noqa: E402
from services.utils.shipgov2_tracking_utils import resumir_shipgov2_para_painel  # noqa: E402


def _safe_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if isinstance(dt, datetime) else None


def _status_rank(status: Optional[str]) -> int:
    s = (status or "").strip().upper()
    if not s or s in {"UNKNOWN", "UNTRACKED"}:
        return 0
    if s in {"BOOKED"}:
        return 0
    if s in {"SAILING"}:
        return 1
    if s in {"ARRIVED"}:
        return 2
    if s in {"DISCHARGED"}:
        return 3
    if s in {"DELIVERED", "ENTREGUE", "ENTREGUE AO DESTINATARIO"}:
        return 4
    # Status desconhecido: não assumir que é “melhor”
    return 0


def _choose_status(old_status: Optional[str], new_status: Optional[str]) -> Optional[str]:
    """Nunca faz downgrade de status (evita DISCHARGED -> SAILING, etc)."""
    old_s = (old_status or "").strip() or None
    new_s = (new_status or "").strip() or None
    if not new_s:
        return old_s
    if not old_s:
        return new_s
    if _status_rank(new_s) >= _status_rank(old_s):
        return new_s
    return old_s


def _diff_tuple(
    old_eta: Optional[str],
    old_navio: Optional[str],
    old_status: Optional[str],
    new_eta: Optional[str],
    new_navio: Optional[str],
    new_status: Optional[str],
) -> bool:
    def norm(s: Optional[str]) -> str:
        return (s or "").strip()

    return (
        norm(old_eta) != norm(new_eta)
        or norm(old_navio) != norm(new_navio)
        or norm(old_status) != norm(new_status)
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Aplica updates no banco (padrão: dry-run)")
    ap.add_argument("--limit", type=int, default=0, help="Limite de processos para processar (0 = todos)")
    args = ap.parse_args()

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT processo_referencia, eta_iso, nome_navio, status_shipsgo, porto_codigo, porto_nome, dados_completos_json
        FROM processos_kanban
        WHERE dados_completos_json IS NOT NULL AND dados_completos_json != ''
        ORDER BY atualizado_em DESC
    """
    if args.limit and args.limit > 0:
        query += " LIMIT ?"
        cur.execute(query, (args.limit,))
    else:
        cur.execute(query)

    rows = cur.fetchall()
    total = len(rows)
    changed = 0
    scanned = 0
    failures = 0

    if args.apply:
        conn.execute("BEGIN")

    try:
        for r in rows:
            scanned += 1
            proc = r["processo_referencia"]
            old_eta = r["eta_iso"]
            old_navio = r["nome_navio"]
            old_status = r["status_shipsgo"]
            old_porto_codigo = r["porto_codigo"]
            old_porto_nome = r["porto_nome"]

            raw = r["dados_completos_json"]
            try:
                data = json.loads(raw)
            except Exception:
                failures += 1
                continue

            shipgov2 = data.get("shipgov2") or {}
            if not isinstance(shipgov2, dict) or not shipgov2:
                continue

            # Segurança: sem destino (POD), não conseguimos afirmar ETA/navio/status do trecho final.
            destino_codigo = (shipgov2.get("destino_codigo") or "").strip()
            if not destino_codigo:
                continue

            resumo = resumir_shipgov2_para_painel(shipgov2, now=datetime.now())
            new_eta = _safe_iso(resumo.eta_pod)
            new_navio = (resumo.navio_pod or None)
            new_status = (resumo.status or None)

            # Porto destino (POD) do shipgov2
            new_porto_codigo = (shipgov2.get("destino_codigo") or None)
            new_porto_nome = (shipgov2.get("destino_nome") or None)

            # ✅ Política conservadora:
            # - nunca substituir valores existentes por None/vazio
            # - nunca fazer downgrade de status (ex.: DISCHARGED -> SAILING)
            final_eta = new_eta or old_eta
            final_navio = new_navio or old_navio
            final_status = _choose_status(old_status, new_status)
            final_porto_codigo = new_porto_codigo or old_porto_codigo
            final_porto_nome = new_porto_nome or old_porto_nome

            if (
                (old_eta or "") == (final_eta or "")
                and (old_navio or "") == (final_navio or "")
                and (old_status or "") == (final_status or "")
                and (old_porto_codigo or "") == (final_porto_codigo or "")
                and (old_porto_nome or "") == (final_porto_nome or "")
            ):
                continue

            changed += 1

            print(f"\n[{changed}] {proc}")
            print("  old:", {"eta_iso": old_eta, "nome_navio": old_navio, "status": old_status, "porto": f"{old_porto_codigo} {old_porto_nome}"})
            print("  new:", {"eta_iso": final_eta, "nome_navio": final_navio, "status": final_status, "porto": f"{final_porto_codigo} {final_porto_nome}"})
            # (debug opcional)
            # print("  resumo:", asdict(resumo))

            if args.apply:
                conn.execute(
                    """
                    UPDATE processos_kanban
                    SET eta_iso = ?,
                        nome_navio = ?,
                        status_shipsgo = ?,
                        porto_codigo = ?,
                        porto_nome = ?,
                        atualizado_em = CURRENT_TIMESTAMP
                    WHERE processo_referencia = ?
                    """,
                    (final_eta, final_navio, final_status, final_porto_codigo, final_porto_nome, proc),
                )

        if args.apply:
            conn.commit()
    except Exception:
        if args.apply:
            conn.rollback()
        raise
    finally:
        conn.close()

    modo = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n✅ Concluído ({modo})")
    print(f"- total lidos: {total}")
    print(f"- processados: {scanned}")
    print(f"- alterações: {changed}")
    print(f"- falhas parse JSON: {failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

