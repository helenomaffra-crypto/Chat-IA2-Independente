#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build do índice HF/FAISS para NESH a partir do SQLite (`nesh_chunks`).

Saída:
- <index_dir>/index.faiss
- <index_dir>/meta.jsonl  (um registro por linha, alinhado ao índice)

Uso (no container):
  docker compose exec web python3 scripts/build_nesh_hf_index.py

ENV:
- DB_PATH=/app/data/chat_ia.db
- NESH_HF_INDEX_DIR=/app/data/nesh_hf_index
- NESH_HF_EMBED_MODEL=intfloat/multilingual-e5-base  (default)
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def _row_to_doc(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "section": row["section"],
        "chapter": row["chapter"],
        "chapter_code": row["chapter_code"],
        "chapter_title": row["chapter_title"],
        "position_code": row["position_code"],
        "position_title": row["position_title"],
        "subposition_code": row["subposition_code"],
        "subposition_title": row["subposition_title"],
        "text": row["text"],
    }


def _doc_to_embed_text(doc: Dict[str, Any]) -> str:
    # Texto “hierarchy-first”: ajuda bastante a NESH
    parts: List[str] = []
    sec = (doc.get("section") or "").strip()
    chap = (doc.get("chapter") or "").strip()
    chap_code = (doc.get("chapter_code") or "").strip()
    chap_title = (doc.get("chapter_title") or "").strip()
    pos_code = (doc.get("position_code") or "").strip()
    pos_title = (doc.get("position_title") or "").strip()
    sub_code = (doc.get("subposition_code") or "").strip()
    sub_title = (doc.get("subposition_title") or "").strip()
    txt = (doc.get("text") or "").strip()

    if sec:
        parts.append(f"Seção: {sec}")
    if chap or chap_code or chap_title:
        parts.append(f"Capítulo {chap_code or ''} {chap}".strip())
        if chap_title:
            parts.append(f"Título do capítulo: {chap_title}")
    if pos_code:
        parts.append(f"Posição {pos_code}: {pos_title}".strip())
    if sub_code:
        parts.append(f"Subposição {sub_code}: {sub_title}".strip())
    if txt:
        parts.append(f"Texto: {txt}")

    return "\n".join([p for p in parts if p])


def main() -> int:
    # Dependências (instale no container para rodar o build):
    import numpy as np
    import faiss  # type: ignore
    from sentence_transformers import SentenceTransformer

    db_path = os.getenv("DB_PATH", "/app/data/chat_ia.db")
    index_dir = Path(os.getenv("NESH_HF_INDEX_DIR", "/app/data/nesh_hf_index"))
    model_name = os.getenv("NESH_HF_EMBED_MODEL", "intfloat/multilingual-e5-base")
    batch = int(os.getenv("NESH_HF_BUILD_BATCH", "64") or 64)

    index_dir.mkdir(parents=True, exist_ok=True)
    out_index = index_dir / "index.faiss"
    out_meta = index_dir / "meta.jsonl"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("select count(1) from nesh_chunks")
    total = int(cur.fetchone()[0] or 0)
    if total <= 0:
        print("❌ nesh_chunks está vazio; rode importar_nesh_sqlite.py primeiro.")
        return 2

    cur.execute(
        """
        select section, chapter, chapter_code, chapter_title,
               position_code, position_title,
               subposition_code, subposition_title,
               text
        from nesh_chunks
        order by chapter_code asc, position_code_clean asc, subposition_code_clean asc
        """
    )

    model = SentenceTransformer(model_name)
    dim = int(getattr(model, "get_sentence_embedding_dimension")())

    # Index: inner product + embeddings normalizados => similaridade coseno
    index = faiss.IndexFlatIP(dim)

    # Escrever meta em jsonl
    if out_meta.exists():
        out_meta.unlink()

    written = 0
    buf_texts: List[str] = []
    buf_docs: List[Dict[str, Any]] = []

    def flush() -> None:
        nonlocal written, buf_texts, buf_docs
        if not buf_texts:
            return
        # e5: prefixar docs com "passage:"
        texts = buf_texts
        if "e5" in model_name.lower():
            texts = [f"passage: {t}" for t in texts]
        embs = model.encode(texts, normalize_embeddings=True)
        vecs = np.asarray(embs, dtype="float32")
        index.add(vecs)
        with out_meta.open("a", encoding="utf-8") as f:
            for d in buf_docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        written += len(buf_docs)
        buf_texts = []
        buf_docs = []

    for row in cur:
        doc = _row_to_doc(row)
        txt = _doc_to_embed_text(doc)
        buf_docs.append(doc)
        buf_texts.append(txt)
        if len(buf_docs) >= batch:
            flush()
            if written % 500 == 0:
                print(f"✅ indexando: {written}/{total}")

    flush()
    conn.close()

    faiss.write_index(index, str(out_index))
    print(f"✅ índice FAISS salvo em: {out_index}")
    print(f"✅ meta salvo em: {out_meta}")
    print(f"✅ total indexado: {written} (esperado: {total})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

