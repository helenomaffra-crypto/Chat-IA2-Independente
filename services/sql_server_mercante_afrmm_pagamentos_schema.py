"""
SQL Server schema/service para pagamentos AFRMM (Mercante RPA).

Grava no banco novo `mAIke_assistente` como fonte de verdade/auditoria.
O SQLite continua existindo como cache local.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DB_NAME = "mAIke_assistente"
TABLE_FULL = "mAIke_assistente.dbo.MERCANTE_AFRMM_PAGAMENTO"


def _esc_sql(v: Any) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    s = s.replace("'", "''")
    return f"'{s}'"


def _now_sql() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_table(sql_adapter: Any) -> None:
    """
    Cria tabela/índices se não existirem (idempotente).
    """
    ddl = f"""
IF OBJECT_ID('{TABLE_FULL}', 'U') IS NULL
BEGIN
    CREATE TABLE {TABLE_FULL} (
        id_mercante_afrmm_pagamento INT IDENTITY(1,1) PRIMARY KEY,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        processo_referencia VARCHAR(30) NULL,
        ce_mercante VARCHAR(30) NOT NULL,
        status VARCHAR(20) NOT NULL,
        pedido VARCHAR(40) NULL,
        banco VARCHAR(20) NULL,
        agencia VARCHAR(20) NULL,
        conta_corrente VARCHAR(40) NULL,
        valor_afrmm DECIMAL(18,2) NULL,
        valor_total_debito DECIMAL(18,2) NULL,
        screenshot_relpath VARCHAR(255) NULL,
        receipt_file_id INT NULL,
        payload_hash CHAR(64) NOT NULL,
        payload_json NVARCHAR(MAX) NULL
    );
    CREATE UNIQUE INDEX UX_MERCANTE_AFRMM_PAGAMENTO_hash
        ON {TABLE_FULL} (payload_hash);
    CREATE INDEX IX_MERCANTE_AFRMM_PAGAMENTO_ce
        ON {TABLE_FULL} (ce_mercante, created_at);
END
"""
    sql_adapter.execute_query(ddl, database=DB_NAME, notificar_erro=False)

    # Migração leve: adicionar coluna receipt_file_id em bases antigas
    try:
        alter = f"""
IF COL_LENGTH('{TABLE_FULL}', 'receipt_file_id') IS NULL
BEGIN
    ALTER TABLE {TABLE_FULL} ADD receipt_file_id INT NULL;
END
"""
        sql_adapter.execute_query(alter, database=DB_NAME, notificar_erro=False)
    except Exception:
        pass


def _tentar_salvar_receipt_no_sql(
    *,
    sql_adapter: Any,
    processo_referencia: str,
    ce_mercante: str,
    screenshot_relpath: Optional[str],
) -> Optional[int]:
    """
    Se houver screenshot_relpath (downloads/mercante/...), tenta salvar o arquivo no SQL Server como BLOB
    e retorna o file_id.
    """
    if os.getenv("MERCANTE_RECEIPT_STORE_IN_DB", "true").lower() != "true":
        return None
    rel = (screenshot_relpath or "").strip().lstrip("/")
    if not rel:
        return None
    # Somente receipts do Mercante (evitar pegar PDFs temporários etc.)
    if not (rel.startswith("mercante/") or rel.startswith("downloads/mercante/")):
        return None
    # normalizar: "downloads/mercante/x.png" -> "mercante/x.png"
    if rel.startswith("downloads/"):
        rel = rel[len("downloads/") :]

    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        downloads_dir = os.path.join(project_root, "downloads")
        file_path = os.path.join(downloads_dir, rel)

        downloads_abs = os.path.abspath(downloads_dir)
        file_abs = os.path.abspath(file_path)
        if not file_abs.startswith(downloads_abs):
            return None
        if not os.path.exists(file_abs) or not os.path.isfile(file_abs):
            return None

        with open(file_abs, "rb") as f:
            content = f.read()
        if not content:
            return None

        filename = os.path.basename(file_abs)
        mime = "image/png" if filename.lower().endswith(".png") else "application/octet-stream"

        from services.sql_server_arquivos_service import salvar_arquivo

        file_id = salvar_arquivo(
            sql_adapter=sql_adapter,
            origem="mercante_afrmm",
            filename=filename,
            content=content,
            mime_type=mime,
            processo_referencia=processo_referencia,
            ce_mercante=ce_mercante,
        )
        if file_id and os.getenv("MERCANTE_RECEIPT_DELETE_AFTER_STORE", "false").lower() == "true":
            try:
                os.remove(file_abs)
            except Exception:
                pass
        return file_id
    except Exception:
        return None


def registrar_pagamento_sucesso(
    *,
    sql_adapter: Any,
    processo_referencia: str,
    ce_mercante: str,
    comprovante: Optional[Dict[str, Any]] = None,
    screenshot_relpath: Optional[str] = None,
) -> bool:
    """
    Registra pagamento AFRMM concluído no SQL Server (idempotente por payload_hash).
    """
    try:
        ensure_table(sql_adapter)
    except Exception as e:
        logger.warning(f"[Mercante][SQL] ⚠️ Falha ao garantir tabela: {e}")

    comp = comprovante or {}

    # Hash idempotente (não depende de horário)
    payload_for_hash = {
        "processo_referencia": (processo_referencia or "").strip().upper(),
        "ce_mercante": str(ce_mercante).strip(),
        "pedido": comp.get("pedido"),
        "valor_total_debito": comp.get("valor_total_debito"),
        "banco": comp.get("banco"),
        "agencia": comp.get("agencia"),
        "conta_corrente": comp.get("conta_corrente"),
    }
    payload_str = json.dumps(payload_for_hash, sort_keys=True, ensure_ascii=False)
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    payload_json = None
    try:
        payload_json = json.dumps(
            {
                "comprovante": comp,
                "screenshot_relpath": screenshot_relpath,
                "created_at_local": _now_sql(),
            },
            ensure_ascii=False,
        )
    except Exception:
        payload_json = None

    # Parse valores (tentar float; se falhar, NULL)
    def _try_float(x: Any) -> Optional[float]:
        if x is None:
            return None
        try:
            f = float(str(x).replace(".", "").replace(",", "."))
            return f if f > 0 else None
        except Exception:
            return None

    valor_total = _try_float(comp.get("valor_total_debito"))
    valor_afrmm = _try_float(comp.get("valor_afrmm"))

    receipt_file_id = _tentar_salvar_receipt_no_sql(
        sql_adapter=sql_adapter,
        processo_referencia=(processo_referencia or "").strip().upper(),
        ce_mercante=str(ce_mercante).strip(),
        screenshot_relpath=screenshot_relpath,
    )

    insert = f"""
IF NOT EXISTS (SELECT 1 FROM {TABLE_FULL} WHERE payload_hash = {_esc_sql(payload_hash)})
BEGIN
    INSERT INTO {TABLE_FULL} (
        processo_referencia, ce_mercante, status, pedido, banco, agencia, conta_corrente,
        valor_afrmm, valor_total_debito, screenshot_relpath, receipt_file_id, payload_hash, payload_json
    ) VALUES (
        {_esc_sql((processo_referencia or '').strip().upper())},
        {_esc_sql(str(ce_mercante).strip())},
        {_esc_sql('success')},
        {_esc_sql(comp.get('pedido'))},
        {_esc_sql(comp.get('banco'))},
        {_esc_sql(comp.get('agencia'))},
        {_esc_sql(comp.get('conta_corrente'))},
        {str(valor_afrmm) if valor_afrmm is not None else 'NULL'},
        {str(valor_total) if valor_total is not None else 'NULL'},
        {_esc_sql(screenshot_relpath)},
        {str(int(receipt_file_id)) if receipt_file_id else 'NULL'},
        {_esc_sql(payload_hash)},
        {_esc_sql(payload_json)}
    );
END
"""
    r = sql_adapter.execute_query(insert, database=DB_NAME, notificar_erro=False)
    return bool(r and r.get("success"))

