"""
NESH HF Service (MVP): embeddings + FAISS para busca semântica na NESH.

Objetivo:
- Melhorar recall/precisão em consultas por descrição ("ventilador axial industrial")
- Manter compatibilidade: se dependências/índice não existirem, o sistema cai no SQLite/LIKE atual.

Design:
- Indexação offline (script em /scripts) gera:
  - index.faiss
  - meta.jsonl (um json por linha com campos principais + texto)
- Em runtime: carrega índice + meta e retorna top-k candidatos.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in ("1", "true", "yes", "y", "on")


@dataclass
class NeshHit:
    score: float
    row: Dict[str, Any]


class NeshHfService:
    """
    Runtime retrieval em cima do índice FAISS.
    """

    def __init__(self) -> None:
        self.enabled = _env_bool("NESH_HF_ENABLED", "false")
        self.index_dir = Path(os.getenv("NESH_HF_INDEX_DIR", "/app/data/nesh_hf_index"))
        self.embed_model = os.getenv("NESH_HF_EMBED_MODEL", "intfloat/multilingual-e5-base")
        self.top_k = int(os.getenv("NESH_HF_TOP_K", "15") or 15)
        self._loaded = False

        self._index = None
        self._meta: List[Dict[str, Any]] = []
        self._embedder = None

    def _deps_available(self) -> bool:
        try:
            import faiss  # type: ignore
            import numpy  # noqa: F401
            from sentence_transformers import SentenceTransformer  # noqa: F401
            return True
        except Exception:
            return False

    def _index_paths(self) -> Tuple[Path, Path]:
        return (self.index_dir / "index.faiss", self.index_dir / "meta.jsonl")

    def is_ready(self) -> bool:
        if not self.enabled:
            return False
        if not self._deps_available():
            return False
        idx_path, meta_path = self._index_paths()
        return idx_path.exists() and meta_path.exists()

    def _load(self) -> None:
        if self._loaded:
            return
        if not self.is_ready():
            self._loaded = True
            return

        idx_path, meta_path = self._index_paths()

        try:
            import faiss  # type: ignore
            self._index = faiss.read_index(str(idx_path))
        except Exception as e:
            logger.warning(f"⚠️ NESH_HF: falha ao carregar FAISS index: {e}")
            self._index = None

        try:
            meta: List[Dict[str, Any]] = []
            with meta_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            meta.append(obj)
                    except Exception:
                        continue
            self._meta = meta
        except Exception as e:
            logger.warning(f"⚠️ NESH_HF: falha ao carregar meta.jsonl: {e}")
            self._meta = []

        self._loaded = True
        logger.info(
            f"✅ NESH_HF carregado: index={bool(self._index)}, meta={len(self._meta)} itens, dir={self.index_dir}"
        )

    def _embed_query(self, query: str) -> Optional["Any"]:
        """
        Gera embedding para a query. Para e5, prefixar com 'query:' melhora.
        """
        q = (query or "").strip()
        if not q:
            return None
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer

            # ✅ Performance: cachear o modelo HF (evita reload a cada busca)
            if self._embedder is None:
                self._embedder = SentenceTransformer(self.embed_model)
            model = self._embedder
            # e5: usar prefixos
            if "e5" in (self.embed_model or "").lower():
                q = f"query: {q}"
            vec = model.encode([q], normalize_embeddings=True)
            return np.asarray(vec, dtype="float32")
        except Exception as e:
            logger.warning(f"⚠️ NESH_HF: falha ao embed query: {e}")
            return None

    def buscar_por_descricao(self, descricao: str, *, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Retorna lista de dicts no formato compatível com `db_manager._nesh_row_to_dict`.
        """
        if not self.enabled:
            return []

        self._load()
        if not self._index or not self._meta:
            return []

        qv = self._embed_query(descricao)
        if qv is None:
            return []

        try:
            k = max(1, min(int(self.top_k), 50))
            D, I = self._index.search(qv, k)  # type: ignore
        except Exception as e:
            logger.warning(f"⚠️ NESH_HF: falha ao buscar no index: {e}")
            return []

        hits: List[NeshHit] = []
        try:
            # D: maior = mais similar quando IP/normalize (dependendo do index)
            # Aqui tratamos como score diretamente.
            for score, idx in zip(D[0].tolist(), I[0].tolist()):
                if idx < 0:
                    continue
                if idx >= len(self._meta):
                    continue
                row = self._meta[idx]
                if isinstance(row, dict):
                    hits.append(NeshHit(score=float(score), row=row))
        except Exception:
            hits = []

        # Ordenar e cortar
        hits.sort(key=lambda h: h.score, reverse=True)
        out: List[Dict[str, Any]] = []
        for h in hits[: max(1, int(limite or 5))]:
            row = h.row if isinstance(h.row, dict) else {}
            # ✅ Marcar fonte para o NCMService renderizar no rodapé (não quebra compatibilidade)
            if "_nesh_source" not in row:
                row["_nesh_source"] = "HF"
            out.append(row)
        return out


def get_nesh_hf_service() -> NeshHfService:
    if not hasattr(get_nesh_hf_service, "_instance"):
        get_nesh_hf_service._instance = NeshHfService()
    return get_nesh_hf_service._instance

