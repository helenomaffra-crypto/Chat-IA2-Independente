#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importa `nesh_chunks.json` para SQLite (`chat_ia.db`) na tabela `nesh_chunks`.

✅ Idempotente: usa UPSERT por `record_key`.
✅ Não depende de rede.

Uso:
  python3 scripts/importar_nesh_sqlite.py --json /Users/helenomaffra/CHAT-IA-BIG/nesh_chunks.json

Se --json não for informado, tenta:
  1) ENV NESH_CHUNKS_PATH
  2) /Users/helenomaffra/CHAT-IA-BIG/nesh_chunks.json
  3) ./nesh_chunks.json (cwd)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ✅ Garantir que a raiz do projeto esteja no sys.path quando o script for executado via
# `python3 scripts/importar_nesh_sqlite.py ...` (sys.path[0] vira /scripts e não a raiz).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db_manager import get_db_connection, init_db  # noqa: E402
from services.path_config import get_nesh_chunks_path  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _clean_code(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    return str(code).strip().replace(".", "").replace("-", "").replace(" ", "")


def _record_key(pos_clean: Optional[str], subpos_clean: Optional[str]) -> str:
    # Mantém unicidade: (posição, subposição)
    # - posição geral: "0101:"
    # - subposição: "010121:0101"
    base = pos_clean or ""
    sub = subpos_clean or ""
    return f"{sub}:{base}"


def _default_json_path() -> Path:
    # 1) ENV NESH_CHUNKS_PATH (mesma lógica do runtime)
    env_path = os.getenv("NESH_CHUNKS_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p
    # 2) local big folder
    p2 = Path("/Users/helenomaffra/CHAT-IA-BIG/nesh_chunks.json")
    if p2.exists():
        return p2
    # 3) cwd
    return get_nesh_chunks_path()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", type=str, default=None)
    parser.add_argument("--batch", dest="batch", type=int, default=500)
    args = parser.parse_args()

    json_path = Path(args.json_path) if args.json_path else _default_json_path()
    if not json_path.exists():
        logger.error(f"Arquivo JSON não encontrado: {json_path}")
        return 2

    logger.info(f"Usando JSON: {json_path} ({json_path.stat().st_size / (1024*1024):.2f} MB)")

    # garantir schema
    init_db()

    data: List[Dict[str, Any]]
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        logger.error(f"Formato inesperado: esperado list, veio {type(data)}")
        return 3

    conn = get_db_connection()
    cursor = conn.cursor()

    inserted = 0
    total = len(data)

    for idx, row in enumerate(data, 1):
        if not isinstance(row, dict):
            continue

        position_code = row.get("position_code")
        subposition_code = row.get("subposition_code")

        pos_clean = _clean_code(position_code)
        sub_clean = _clean_code(subposition_code)
        rk = _record_key(pos_clean, sub_clean)

        cursor.execute(
            """
            INSERT INTO nesh_chunks (
              record_key,
              section, chapter, chapter_code, chapter_title,
              position_code, position_code_clean, position_title,
              subposition_code, subposition_code_clean, subposition_title,
              text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(record_key) DO UPDATE SET
              section=excluded.section,
              chapter=excluded.chapter,
              chapter_code=excluded.chapter_code,
              chapter_title=excluded.chapter_title,
              position_code=excluded.position_code,
              position_code_clean=excluded.position_code_clean,
              position_title=excluded.position_title,
              subposition_code=excluded.subposition_code,
              subposition_code_clean=excluded.subposition_code_clean,
              subposition_title=excluded.subposition_title,
              text=excluded.text
            """,
            (
                rk,
                row.get("section"),
                row.get("chapter"),
                row.get("chapter_code"),
                row.get("chapter_title"),
                position_code,
                pos_clean,
                row.get("position_title"),
                subposition_code,
                sub_clean,
                row.get("subposition_title"),
                row.get("text"),
            ),
        )

        inserted += 1

        if inserted % int(args.batch) == 0:
            conn.commit()
            logger.info(f"✅ Import parcial: {inserted}/{total}")

    conn.commit()
    conn.close()

    logger.info(f"✅ Import concluído: {inserted}/{total} registros upserted em nesh_chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

