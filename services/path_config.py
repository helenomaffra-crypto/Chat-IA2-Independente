"""
Configuração centralizada de paths do projeto.

Objetivo: permitir mover arquivos grandes (ex.: NESH e legislacao_files) para fora do workspace
sem quebrar o runtime, e reduzir crashes do editor/indexação.
"""

from __future__ import annotations

import os
from pathlib import Path


def get_legislacao_files_dir() -> Path:
    """
    Retorna o diretório onde ficam os arquivos locais de legislação.

    ENV:
      - LEGISLACAO_FILES_DIR: caminho (absoluto ou relativo ao cwd)
    """
    return Path(os.getenv("LEGISLACAO_FILES_DIR", "legislacao_files"))


def get_nesh_chunks_path() -> Path:
    """
    Retorna o path do arquivo `nesh_chunks.json`.

    ENV:
      - NESH_CHUNKS_PATH: caminho (absoluto ou relativo ao cwd)
    """
    return Path(os.getenv("NESH_CHUNKS_PATH", "nesh_chunks.json"))

