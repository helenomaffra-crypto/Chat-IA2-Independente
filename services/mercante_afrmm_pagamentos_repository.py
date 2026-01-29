"""
MercanteAfrmmPagamentosRepository

Persistência local (SQLite) dos pagamentos AFRMM executados via Mercante RPA.

Objetivo:
- Permitir que o mAIke saiba que um AFRMM já foi pago (e mostre valores) SEM precisar rebilhetar CE na Serpro.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _parse_brl(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            f = float(val)
            return f if f > 0 else None
        except Exception:
            return None
    s = str(val).strip()
    if not s:
        return None
    # remover moeda/textos
    s = re.sub(r"[^\d,.\-]", "", s)
    if not s:
        return None
    # Caso típico BR: 1.234,56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        f = float(s)
        return f if f > 0 else None
    except Exception:
        return None


class MercanteAfrmmPagamentosRepository:
    def __init__(self) -> None:
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            from db_manager import get_db_connection

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mercante_afrmm_pagamentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT DEFAULT (datetime('now')),
                    processo_referencia TEXT,
                    ce_mercante TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pedido TEXT,
                    banco TEXT,
                    agencia TEXT,
                    conta_corrente TEXT,
                    valor_afrmm REAL,
                    valor_total_debito REAL,
                    screenshot_relpath TEXT,
                    observacoes TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mercante_afrmm_pagamentos_ce
                ON mercante_afrmm_pagamentos (ce_mercante, created_at)
                """
            )
            # ✅ Migração leve: adicionar coluna observacoes em bases antigas
            try:
                cur.execute("ALTER TABLE mercante_afrmm_pagamentos ADD COLUMN observacoes TEXT")
            except Exception:
                pass
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"[Mercante][Repo] ⚠️ Falha ao garantir tabela mercante_afrmm_pagamentos: {e}")

    def registrar_sucesso(
        self,
        *,
        processo_referencia: str,
        ce_mercante: str,
        comprovante: Optional[Dict[str, Any]] = None,
        screenshot_relpath: Optional[str] = None,
    ) -> None:
        """
        Registra um pagamento concluído com sucesso (tela "Débito efetuado com sucesso").
        """
        try:
            from db_manager import get_db_connection

            comp = comprovante or {}
            valor_total_debito = _parse_brl(comp.get("valor_total_debito"))
            valor_afrmm = _parse_brl(comp.get("valor_afrmm"))

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO mercante_afrmm_pagamentos (
                    processo_referencia, ce_mercante, status,
                    pedido, banco, agencia, conta_corrente,
                    valor_afrmm, valor_total_debito, screenshot_relpath, observacoes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (processo_referencia or "").strip().upper(),
                    str(ce_mercante).strip(),
                    "success",
                    (comp.get("pedido") or None),
                    (comp.get("banco") or None),
                    (comp.get("agencia") or None),
                    (comp.get("conta_corrente") or None),
                    valor_afrmm,
                    valor_total_debito,
                    screenshot_relpath,
                    None,
                ),
            )
            conn.commit()
            conn.close()

            # ✅ Também gravar no SQL Server (mAIke_assistente) quando disponível
            try:
                from utils.sql_server_adapter import get_sql_adapter
                from services.sql_server_mercante_afrmm_pagamentos_schema import registrar_pagamento_sucesso

                sql_adapter = get_sql_adapter()
                if sql_adapter:
                    registrar_pagamento_sucesso(
                        sql_adapter=sql_adapter,
                        processo_referencia=processo_referencia,
                        ce_mercante=ce_mercante,
                        comprovante=comp,
                        screenshot_relpath=screenshot_relpath,
                    )
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"[Mercante][Repo] ⚠️ Falha ao registrar sucesso AFRMM: {e}")

    def registrar_confirmacao_externa(
        self,
        *,
        processo_referencia: str,
        ce_mercante: str,
        valor_total_debito: Optional[float] = None,
        observacoes: Optional[str] = None,
    ) -> None:
        """
        Registra um pagamento como "confirmado externamente" quando o Mercante/BB confirma,
        mas o robô não gerou comprovante/print (ex.: execução antiga em headless).
        """
        try:
            from db_manager import get_db_connection

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO mercante_afrmm_pagamentos (
                    processo_referencia, ce_mercante, status,
                    pedido, banco, agencia, conta_corrente,
                    valor_afrmm, valor_total_debito, screenshot_relpath, observacoes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (processo_referencia or "").strip().upper(),
                    str(ce_mercante).strip(),
                    "confirmed_external",
                    None,
                    None,
                    None,
                    None,
                    None,
                    float(valor_total_debito) if valor_total_debito is not None else None,
                    None,
                    (observacoes or "").strip() or None,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"[Mercante][Repo] ⚠️ Falha ao registrar confirmação externa AFRMM: {e}")

    def buscar_ultimo_sucesso_por_ce(self, ce_mercante: str) -> Optional[Dict[str, Any]]:
        """
        Retorna o último registro de sucesso para o CE (se existir).
        """
        try:
            from db_manager import get_db_connection
            import sqlite3

            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT *
                FROM mercante_afrmm_pagamentos
                WHERE ce_mercante = ?
                  AND status IN ('success', 'confirmed_external')
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT 1
                """,
                (str(ce_mercante).strip(),),
            )
            row = cur.fetchone()
            conn.close()
            if not row:
                return None
            return dict(row)
        except Exception as e:
            logger.warning(f"[Mercante][Repo] ⚠️ Falha ao buscar sucesso AFRMM por CE: {e}")
            return None

    def listar_sucessos(
        self,
        *,
        ce_mercante: Optional[str] = None,
        processo_referencia: Optional[str] = None,
        limite: int = 50,
    ) -> list[Dict[str, Any]]:
        """Lista pagamentos AFRMM com sucesso (SQLite cache)."""
        try:
            from db_manager import get_db_connection
            import sqlite3

            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Considerar pagamento como "pago" tanto em success quanto em confirmed_external
            where = ["status IN ('success', 'confirmed_external')"]
            params: list[Any] = []

            if ce_mercante:
                where.append("ce_mercante = ?")
                params.append(str(ce_mercante).strip())
            if processo_referencia:
                where.append("processo_referencia = ?")
                params.append((processo_referencia or "").strip().upper())

            lim = int(limite or 50)
            if lim <= 0:
                lim = 50
            if lim > 200:
                lim = 200

            sql = f"""
                SELECT *
                FROM mercante_afrmm_pagamentos
                WHERE {' AND '.join(where)}
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT {lim}
            """
            cur.execute(sql, params)
            rows = cur.fetchall() or []
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"[Mercante][Repo] ⚠️ Falha ao listar pagamentos AFRMM no SQLite: {e}")
            return []

