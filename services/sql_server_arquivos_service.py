"""
SQL Server ArquivosService (BLOBs)

Armazena arquivos (ex.: comprovantes PNG do Mercante) no banco novo `mAIke_assistente`.

Motivação:
- Evitar crescer `downloads/` indefinidamente no host
- Centralizar auditoria no SQL Server
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DB_NAME = "mAIke_assistente"
TABLE_FULL = "mAIke_assistente.dbo.MAIKE_ARQUIVO"


def _esc_sql(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def _now_sql() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_table(sql_adapter: Any) -> None:
    ddl = f"""
IF OBJECT_ID('{TABLE_FULL}', 'U') IS NULL
BEGIN
    CREATE TABLE {TABLE_FULL} (
        id_maike_arquivo INT IDENTITY(1,1) PRIMARY KEY,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        origem VARCHAR(40) NULL,
        processo_referencia VARCHAR(30) NULL,
        ce_mercante VARCHAR(30) NULL,
        filename VARCHAR(255) NOT NULL,
        mime_type VARCHAR(80) NULL,
        size_bytes INT NULL,
        sha256 CHAR(64) NOT NULL,
        content VARBINARY(MAX) NOT NULL,
        created_at_local DATETIME2 NULL
    );
    CREATE UNIQUE INDEX UX_MAIKE_ARQUIVO_sha256 ON {TABLE_FULL} (sha256);
    CREATE INDEX IX_MAIKE_ARQUIVO_origem ON {TABLE_FULL} (origem, created_at);
END
"""
    sql_adapter.execute_query(ddl, database=DB_NAME, notificar_erro=False)


def salvar_arquivo(
    *,
    sql_adapter: Any,
    origem: str,
    filename: str,
    content: bytes,
    mime_type: Optional[str] = None,
    processo_referencia: Optional[str] = None,
    ce_mercante: Optional[str] = None,
) -> Optional[int]:
    """
    Salva arquivo como BLOB no SQL Server (idempotente por sha256).

    Returns:
        id_maike_arquivo (int) ou None se falhar.
    """
    try:
        ensure_table(sql_adapter)
    except Exception as e:
        logger.warning(f"[Arquivos][SQL] ⚠️ Falha ao garantir tabela: {e}")

    if not content:
        return None

    sha = hashlib.sha256(content).hexdigest()
    size_bytes = len(content)

    # Converter bytes para hex: 0xDEADBEEF...
    hex_str = content.hex()
    content_sql = f"0x{hex_str}"

    insert = f"""
IF NOT EXISTS (SELECT 1 FROM {TABLE_FULL} WHERE sha256 = {_esc_sql(sha)})
BEGIN
    INSERT INTO {TABLE_FULL} (
        origem, processo_referencia, ce_mercante,
        filename, mime_type, size_bytes, sha256, content, created_at_local
    ) VALUES (
        {_esc_sql((origem or '').strip())},
        {_esc_sql((processo_referencia or '').strip().upper() if processo_referencia else None)},
        {_esc_sql((ce_mercante or '').strip() if ce_mercante else None)},
        {_esc_sql((filename or '').strip())},
        {_esc_sql((mime_type or '').strip() if mime_type else None)},
        {int(size_bytes)},
        {_esc_sql(sha)},
        {content_sql},
        {_esc_sql(_now_sql())}
    );
END
"""
    r = sql_adapter.execute_query(insert, database=DB_NAME, notificar_erro=False)
    if not (r and r.get("success")):
        return None

    # Buscar ID (tanto para existente quanto inserido)
    q = f"SELECT TOP 1 id_maike_arquivo FROM {TABLE_FULL} WHERE sha256 = {_esc_sql(sha)}"
    rq = sql_adapter.execute_query(q, database=DB_NAME, notificar_erro=False)
    if rq and rq.get("success") and rq.get("data"):
        row = (rq.get("data") or [{}])[0] or {}
        try:
            return int(row.get("id_maike_arquivo"))
        except Exception:
            return None
    return None


def obter_arquivo_por_id(*, sql_adapter: Any, file_id: int) -> Optional[Dict[str, Any]]:
    try:
        fid = int(file_id)
    except Exception:
        return None
    try:
        ensure_table(sql_adapter)
    except Exception:
        pass
    q = f"""
SELECT TOP 1
    id_maike_arquivo, created_at, origem, processo_referencia, ce_mercante,
    filename, mime_type, size_bytes, sha256, content
FROM {TABLE_FULL}
WHERE id_maike_arquivo = {fid}
"""
    r = sql_adapter.execute_query(q, database=DB_NAME, notificar_erro=False)
    if not (r and r.get("success") and r.get("data")):
        return None
    row = (r.get("data") or [{}])[0] or {}
    # `content` pode vir como bytes (pyodbc) ou como string/hex (adapter). Tentar normalizar.
    content = row.get("content")
    if isinstance(content, (bytes, bytearray)):
        b = bytes(content)
    elif isinstance(content, str):
        s = content.strip()
        if s.startswith("0x") or s.startswith("0X"):
            s = s[2:]
        try:
            b = bytes.fromhex(s)
        except Exception:
            b = b""
    else:
        b = b""
    row["content_bytes"] = b
    return row

