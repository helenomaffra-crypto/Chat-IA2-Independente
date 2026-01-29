#!/usr/bin/env python3
"""
Aplica constraints/índices no SQL Server `mAIke_assistente` de forma idempotente,
com foco em tornar o banco "fonte da verdade" com chaves naturais estáveis.

O script faz:
- Deduplicação segura de dbo.DOCUMENTO_ADUANEIRO (mantém o melhor registro por chave)
- Criação de UNIQUE INDEX em:
  - dbo.VALOR_MERCADORIA (processo_referencia, numero_documento, tipo_documento, tipo_valor, moeda)
  - dbo.IMPOSTO_IMPORTACAO (processo_referencia, numero_documento, tipo_documento, tipo_imposto, numero_retificacao)
  - dbo.DOCUMENTO_ADUANEIRO (2 únicos filtrados para tratar versao_documento vazia vs preenchida)
- Criação de índices de performance para leitura por processo/tipo/datas

Uso:
  python3 scripts/aplicar_constraints_indices_maike_assistente.py
  python3 scripts/aplicar_constraints_indices_maike_assistente.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402


DB = "mAIke_assistente"


def _exec(adapter, sql: str, database: str = DB, dry_run: bool = False) -> Dict[str, Any]:
    sql_clean = sql.strip()
    if not sql_clean:
        return {"success": True, "data": []}
    if dry_run:
        print("\n--- DRY RUN SQL ---")
        print(sql_clean)
        return {"success": True, "data": []}
    return adapter.execute_query(sql_clean, database=database)


def _fetch_rows(adapter, sql: str, database: str = DB) -> List[Dict[str, Any]]:
    r = adapter.execute_query(sql, database=database)
    if not r or not r.get("success"):
        return []
    data = r.get("data") or []
    return data if isinstance(data, list) else []


def _table_exists(adapter, table: str) -> bool:
    # table: dbo.TABELA
    parts = table.split(".")
    schema = parts[0].strip("[]") if len(parts) == 2 else "dbo"
    name = parts[1].strip("[]") if len(parts) == 2 else parts[-1].strip("[]")
    sql = f"""
        SELECT COUNT(*) as total
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{name}'
    """
    rows = _fetch_rows(adapter, sql)
    return bool(rows and int(rows[0].get("total", 0)) > 0)


def _index_exists(adapter, table: str, index_name: str) -> bool:
    sql = f"""
        SELECT COUNT(*) as total
        FROM sys.indexes
        WHERE name = '{index_name}'
          AND object_id = OBJECT_ID('{table}')
    """
    rows = _fetch_rows(adapter, sql)
    return bool(rows and int(rows[0].get("total", 0)) > 0)

def _get_check_constraint_definition(adapter, table: str, constraint_name: str) -> Optional[str]:
    sql = f"""
        SELECT cc.definition as definition
        FROM sys.check_constraints cc
        WHERE cc.parent_object_id = OBJECT_ID('{table}')
          AND cc.name = '{constraint_name}'
    """
    rows = _fetch_rows(adapter, sql)
    if not rows:
        return None
    return rows[0].get("definition")


def _ensure_chk_valor_tipo(adapter, dry_run: bool) -> None:
    """
    Garante que CHK_VALOR_TIPO permita os tipos usados pelo sistema (incluindo FRETE/SEGURO),
    para evitar erro no MERGE da persistência do relatório FOB.
    """
    if not _table_exists(adapter, "dbo.VALOR_MERCADORIA"):
        return
    current = _get_check_constraint_definition(adapter, "dbo.VALOR_MERCADORIA", "CHK_VALOR_TIPO") or ""
    needs = ("FRETE" not in current) or ("SEGURO" not in current)
    if not needs:
        print("ℹ️  CHK_VALOR_TIPO já permite FRETE/SEGURO.")
        return

    print("⚠️ Ajustando CHK_VALOR_TIPO para permitir FRETE/SEGURO...")
    sql = """
    IF EXISTS (
        SELECT 1
        FROM sys.check_constraints
        WHERE parent_object_id = OBJECT_ID('dbo.VALOR_MERCADORIA')
          AND name = 'CHK_VALOR_TIPO'
    )
    BEGIN
        ALTER TABLE dbo.VALOR_MERCADORIA DROP CONSTRAINT CHK_VALOR_TIPO;
    END;

    ALTER TABLE dbo.VALOR_MERCADORIA WITH CHECK
    ADD CONSTRAINT CHK_VALOR_TIPO CHECK (
        tipo_valor IN (
            'DESCARGA','EMBARQUE','FOB','CIF','VMLE','VMLD',
            'FRETE','SEGURO',
            'OUTROS'
        )
    );
    """
    r = _exec(adapter, sql, dry_run=dry_run)
    if not r.get("success", True):
        print(f"❌ Falha ajustando CHK_VALOR_TIPO: {r.get('error')}")
        return
    print("✅ CHK_VALOR_TIPO ajustada com sucesso.")


def _count_duplicate_groups_documento(adapter) -> int:
    if not _table_exists(adapter, "dbo.DOCUMENTO_ADUANEIRO"):
        return 0
    sql = """
        SELECT COUNT(*) as total
        FROM (
            SELECT
                tipo_documento,
                numero_documento,
                ISNULL(NULLIF(LTRIM(RTRIM(versao_documento)), ''), '') AS versao_norm,
                COUNT(*) as qtd
            FROM dbo.DOCUMENTO_ADUANEIRO
            GROUP BY
                tipo_documento,
                numero_documento,
                ISNULL(NULLIF(LTRIM(RTRIM(versao_documento)), ''), '')
            HAVING COUNT(*) > 1
        ) t
    """
    rows = _fetch_rows(adapter, sql)
    return int(rows[0].get("total", 0)) if rows else 0


def _dedup_documento_aduaneiro(adapter, dry_run: bool) -> None:
    """
    Deduplica DOCUMENTO_ADUANEIRO mantendo 1 linha por chave natural:
    (tipo_documento, numero_documento, versao_norm).

    Estratégia:
    - escolhe "melhor" registro por:
      1) possuir json_dados_originais
      2) possuir processo_referencia
      3) possuir status_documento/status_documento_codigo/situacao_documento/canal_documento
      4) possuir datas
      5) atualizado_em mais recente
    - antes de deletar, tenta enriquecer o "best" com COALESCE de um registro irmão mais completo
    """
    groups = _count_duplicate_groups_documento(adapter)
    if groups <= 0:
        print("✅ DOCUMENTO_ADUANEIRO: sem duplicidades para deduplicar.")
        return

    print(f"⚠️ DOCUMENTO_ADUANEIRO: {groups} grupo(s) duplicado(s). Iniciando dedupe...")

    sql = r"""
    ;WITH base AS (
        SELECT
            id_documento,
            tipo_documento,
            numero_documento,
            ISNULL(NULLIF(LTRIM(RTRIM(versao_documento)), ''), '') AS versao_norm,
            processo_referencia,
            status_documento,
            status_documento_codigo,
            situacao_documento,
            canal_documento,
            data_registro,
            data_situacao,
            data_desembaraco,
            json_dados_originais,
            atualizado_em,
            (
                CASE WHEN json_dados_originais IS NULL OR LTRIM(RTRIM(CAST(json_dados_originais AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN processo_referencia IS NULL OR LTRIM(RTRIM(CAST(processo_referencia AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN status_documento IS NULL OR LTRIM(RTRIM(CAST(status_documento AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN status_documento_codigo IS NULL OR LTRIM(RTRIM(CAST(status_documento_codigo AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN situacao_documento IS NULL OR LTRIM(RTRIM(CAST(situacao_documento AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN canal_documento IS NULL OR LTRIM(RTRIM(CAST(canal_documento AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN data_registro IS NULL THEN 1 ELSE 0 END
              + CASE WHEN data_situacao IS NULL THEN 1 ELSE 0 END
              + CASE WHEN data_desembaraco IS NULL THEN 1 ELSE 0 END
            ) AS missing_score
        FROM dbo.DOCUMENTO_ADUANEIRO
    ),
    ranked AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY tipo_documento, numero_documento, versao_norm
                ORDER BY
                    missing_score ASC,
                    atualizado_em DESC,
                    id_documento DESC
            ) AS rn
        FROM base
    ),
    best AS (
        SELECT * FROM ranked WHERE rn = 1
    ),
    siblings_best_src AS (
        SELECT
            b.id_documento AS best_id,
            s.id_documento AS src_id
        FROM best b
        OUTER APPLY (
            SELECT TOP 1 s.*
            FROM ranked s
            WHERE s.tipo_documento = b.tipo_documento
              AND s.numero_documento = b.numero_documento
              AND s.versao_norm = b.versao_norm
              AND s.id_documento <> b.id_documento
            ORDER BY
              s.missing_score ASC,
              s.atualizado_em DESC,
              s.id_documento DESC
        ) s
        WHERE s.id_documento IS NOT NULL
    )
    -- Enriquecer best com valores não nulos do melhor sibling
    UPDATE d
    SET
        processo_referencia = COALESCE(NULLIF(LTRIM(RTRIM(d.processo_referencia)), ''), sb.processo_referencia),
        status_documento = COALESCE(NULLIF(LTRIM(RTRIM(d.status_documento)), ''), sb.status_documento),
        status_documento_codigo = COALESCE(NULLIF(LTRIM(RTRIM(d.status_documento_codigo)), ''), sb.status_documento_codigo),
        situacao_documento = COALESCE(NULLIF(LTRIM(RTRIM(d.situacao_documento)), ''), sb.situacao_documento),
        canal_documento = COALESCE(NULLIF(LTRIM(RTRIM(d.canal_documento)), ''), sb.canal_documento),
        data_registro = COALESCE(d.data_registro, sb.data_registro),
        data_situacao = COALESCE(d.data_situacao, sb.data_situacao),
        data_desembaraco = COALESCE(d.data_desembaraco, sb.data_desembaraco),
        json_dados_originais = COALESCE(NULLIF(LTRIM(RTRIM(CAST(d.json_dados_originais AS NVARCHAR(MAX)))), ''), sb.json_dados_originais)
    FROM dbo.DOCUMENTO_ADUANEIRO d
    INNER JOIN siblings_best_src m ON m.best_id = d.id_documento
    INNER JOIN dbo.DOCUMENTO_ADUANEIRO sb ON sb.id_documento = m.src_id
    ;

    -- Remover duplicatas (manter rn=1)
    WITH base2 AS (
        SELECT
            id_documento,
            tipo_documento,
            numero_documento,
            ISNULL(NULLIF(LTRIM(RTRIM(versao_documento)), ''), '') AS versao_norm,
            atualizado_em,
            (
                CASE WHEN json_dados_originais IS NULL OR LTRIM(RTRIM(CAST(json_dados_originais AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN processo_referencia IS NULL OR LTRIM(RTRIM(CAST(processo_referencia AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN status_documento IS NULL OR LTRIM(RTRIM(CAST(status_documento AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN status_documento_codigo IS NULL OR LTRIM(RTRIM(CAST(status_documento_codigo AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN situacao_documento IS NULL OR LTRIM(RTRIM(CAST(situacao_documento AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN canal_documento IS NULL OR LTRIM(RTRIM(CAST(canal_documento AS NVARCHAR(MAX)))) = '' THEN 1 ELSE 0 END
              + CASE WHEN data_registro IS NULL THEN 1 ELSE 0 END
              + CASE WHEN data_situacao IS NULL THEN 1 ELSE 0 END
              + CASE WHEN data_desembaraco IS NULL THEN 1 ELSE 0 END
            ) AS missing_score
        FROM dbo.DOCUMENTO_ADUANEIRO
    ),
    ranked2 AS (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY tipo_documento, numero_documento, versao_norm
                ORDER BY
                    missing_score ASC,
                    atualizado_em DESC,
                    id_documento DESC
            ) AS rn
        FROM base2
    )
    DELETE d
    FROM dbo.DOCUMENTO_ADUANEIRO d
    INNER JOIN ranked2 r ON r.id_documento = d.id_documento
    WHERE r.rn > 1
    ;
    """

    _exec(adapter, sql, dry_run=dry_run)
    left = _count_duplicate_groups_documento(adapter) if not dry_run else groups
    if dry_run:
        print("✅ DRY RUN: dedupe não executado de fato.")
    else:
        print(f"✅ Dedupe concluído. Grupos duplicados restantes: {left}")


def _create_index(adapter, sql: str, index_name: str, table: str, dry_run: bool) -> None:
    if _index_exists(adapter, table, index_name):
        print(f"ℹ️  Índice já existe: {index_name}")
        return
    r = _exec(adapter, sql, dry_run=dry_run)
    if not r.get("success", True):
        print(f"❌ Falha criando índice {index_name}: {r.get('error')}")
        return
    print(f"✅ Índice criado: {index_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Aplicar índices/constraints no mAIke_assistente (SQL Server).")
    parser.add_argument("--dry-run", action="store_true", help="Não executa SQL, apenas imprime.")
    args = parser.parse_args()

    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server adapter não disponível")
        return 2

    if not _table_exists(adapter, "dbo.DOCUMENTO_ADUANEIRO"):
        print("❌ Tabela dbo.DOCUMENTO_ADUANEIRO não existe no banco.")
        return 1

    print("=" * 80)
    print("🔧 Aplicando constraints/índices - mAIke_assistente")
    print("=" * 80)
    print(f"DB: {DB}")
    print(f"Dry-run: {'sim' if args.dry_run else 'não'}")
    print()

    # 0) Garantir constraints compatíveis com o write-path atual
    _ensure_chk_valor_tipo(adapter, dry_run=args.dry_run)

    # 1) Dedup de DOCUMENTO_ADUANEIRO (necessário para índices únicos)
    _dedup_documento_aduaneiro(adapter, dry_run=args.dry_run)

    # 2) UNIQUE: VALOR_MERCADORIA (já está sem duplicatas pelo diagnóstico)
    if _table_exists(adapter, "dbo.VALOR_MERCADORIA"):
        _create_index(
            adapter,
            sql="""
            CREATE UNIQUE INDEX ux_valor_mercadoria_key
            ON dbo.VALOR_MERCADORIA (processo_referencia, numero_documento, tipo_documento, tipo_valor, moeda)
            """,
            index_name="ux_valor_mercadoria_key",
            table="dbo.VALOR_MERCADORIA",
            dry_run=args.dry_run,
        )
        _create_index(
            adapter,
            sql="""
            CREATE INDEX ix_valor_mercadoria_processo
            ON dbo.VALOR_MERCADORIA (processo_referencia, tipo_documento, data_atualizacao DESC)
            """,
            index_name="ix_valor_mercadoria_processo",
            table="dbo.VALOR_MERCADORIA",
            dry_run=args.dry_run,
        )

    # 3) UNIQUE: IMPOSTO_IMPORTACAO (por documento/imposto/retificação)
    if _table_exists(adapter, "dbo.IMPOSTO_IMPORTACAO"):
        _create_index(
            adapter,
            sql="""
            CREATE UNIQUE INDEX ux_imposto_importacao_key
            ON dbo.IMPOSTO_IMPORTACAO (processo_referencia, numero_documento, tipo_documento, tipo_imposto, numero_retificacao)
            """,
            index_name="ux_imposto_importacao_key",
            table="dbo.IMPOSTO_IMPORTACAO",
            dry_run=args.dry_run,
        )
        _create_index(
            adapter,
            sql="""
            CREATE INDEX ix_imposto_processo
            ON dbo.IMPOSTO_IMPORTACAO (processo_referencia, tipo_documento, data_pagamento DESC)
            """,
            index_name="ix_imposto_processo",
            table="dbo.IMPOSTO_IMPORTACAO",
            dry_run=args.dry_run,
        )

    # 4) UNIQUE: DOCUMENTO_ADUANEIRO
    # Nota: O SQL Server tem limitações para índices filtrados (evitar OR/funções).
    # Estratégia:
    # - "sem versão" = versao_documento IS NULL -> unique por (tipo_documento, numero_documento)
    # - "com versão" = versao_documento IS NOT NULL -> unique por (tipo_documento, numero_documento, versao_documento)
    #
    # Antes, normalizamos: qualquer string vazia vira NULL.
    _exec(
        adapter,
        """
        UPDATE dbo.DOCUMENTO_ADUANEIRO
        SET versao_documento = NULL
        WHERE versao_documento IS NOT NULL AND LTRIM(RTRIM(versao_documento)) = ''
        """,
        dry_run=args.dry_run,
    )

    # - Sem versão: 1 registro por (tipo_documento, numero_documento) quando versao_documento IS NULL
    _create_index(
        adapter,
        sql=r"""
        CREATE UNIQUE INDEX ux_documento_aduaneiro_sem_versao
        ON dbo.DOCUMENTO_ADUANEIRO (tipo_documento, numero_documento)
        WHERE versao_documento IS NULL
        """,
        index_name="ux_documento_aduaneiro_sem_versao",
        table="dbo.DOCUMENTO_ADUANEIRO",
        dry_run=args.dry_run,
    )
    # - Com versão: 1 registro por (tipo_documento, numero_documento, versao_documento) quando versao_documento IS NOT NULL
    _create_index(
        adapter,
        sql=r"""
        CREATE UNIQUE INDEX ux_documento_aduaneiro_com_versao
        ON dbo.DOCUMENTO_ADUANEIRO (tipo_documento, numero_documento, versao_documento)
        WHERE versao_documento IS NOT NULL
        """,
        index_name="ux_documento_aduaneiro_com_versao",
        table="dbo.DOCUMENTO_ADUANEIRO",
        dry_run=args.dry_run,
    )

    # 5) Índices de performance - DOCUMENTO_ADUANEIRO
    _create_index(
        adapter,
        sql="CREATE INDEX ix_documento_processo ON dbo.DOCUMENTO_ADUANEIRO (processo_referencia, atualizado_em DESC)",
        index_name="ix_documento_processo",
        table="dbo.DOCUMENTO_ADUANEIRO",
        dry_run=args.dry_run,
    )
    _create_index(
        adapter,
        sql="CREATE INDEX ix_documento_tipo_status ON dbo.DOCUMENTO_ADUANEIRO (tipo_documento, status_documento, atualizado_em DESC)",
        index_name="ix_documento_tipo_status",
        table="dbo.DOCUMENTO_ADUANEIRO",
        dry_run=args.dry_run,
    )
    _create_index(
        adapter,
        sql="CREATE INDEX ix_documento_datas ON dbo.DOCUMENTO_ADUANEIRO (data_registro, data_situacao, data_desembaraco)",
        index_name="ix_documento_datas",
        table="dbo.DOCUMENTO_ADUANEIRO",
        dry_run=args.dry_run,
    )

    # 6) Índices de performance - HISTORICO_DOCUMENTO_ADUANEIRO
    if _table_exists(adapter, "dbo.HISTORICO_DOCUMENTO_ADUANEIRO"):
        _create_index(
            adapter,
            sql="CREATE INDEX ix_hist_doc ON dbo.HISTORICO_DOCUMENTO_ADUANEIRO (id_documento, data_evento DESC)",
            index_name="ix_hist_doc",
            table="dbo.HISTORICO_DOCUMENTO_ADUANEIRO",
            dry_run=args.dry_run,
        )
        _create_index(
            adapter,
            sql="CREATE INDEX ix_hist_numero ON dbo.HISTORICO_DOCUMENTO_ADUANEIRO (numero_documento, tipo_documento, data_evento DESC)",
            index_name="ix_hist_numero",
            table="dbo.HISTORICO_DOCUMENTO_ADUANEIRO",
            dry_run=args.dry_run,
        )
        _create_index(
            adapter,
            sql="CREATE INDEX ix_hist_processo ON dbo.HISTORICO_DOCUMENTO_ADUANEIRO (processo_referencia, data_evento DESC)",
            index_name="ix_hist_processo",
            table="dbo.HISTORICO_DOCUMENTO_ADUANEIRO",
            dry_run=args.dry_run,
        )

    print("\n✅ Concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

