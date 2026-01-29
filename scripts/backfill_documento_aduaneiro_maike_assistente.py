#!/usr/bin/env python3
"""
Backfill do `mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO`.

Objetivo:
- Preencher lacunas em campos essenciais (status/situação/canal/datas/processo/JSON)
- Usar `json_dados_originais` quando existir
- Quando não existir, buscar no cache SQLite (`chat_ia.db`) (ces_cache/dis_cache/ccts_cache/duimps)

O script é idempotente: só preenche campos vazios/NULL.

Uso:
  python3 scripts/backfill_documento_aduaneiro_maike_assistente.py
  python3 scripts/backfill_documento_aduaneiro_maike_assistente.py --limit 200 --dry-run
"""

from __future__ import annotations

import argparse
import json
import ast
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402
from services.documento_historico_service import DocumentoHistoricoService  # noqa: E402


DB = "mAIke_assistente"


def _sql_escape(s: str) -> str:
    return (s or "").replace("'", "''")


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    s = s.replace("'", "''")
    return f"'{s}'"


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _fetch_json_from_sqlite(conn: sqlite3.Connection, tipo: str, numero: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Retorna (json_text, processo_referencia) a partir do cache SQLite.
    """
    cur = conn.cursor()
    tipo = (tipo or "").upper().strip()
    if tipo == "CE":
        cur.execute(
            "SELECT json_completo, processo_referencia FROM ces_cache WHERE numero_ce = ? ORDER BY atualizado_em DESC LIMIT 1",
            (numero,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)
    if tipo == "DI":
        cur.execute(
            "SELECT json_completo, processo_referencia FROM dis_cache WHERE numero_di = ? ORDER BY atualizado_em DESC LIMIT 1",
            (numero,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)
    if tipo == "CCT":
        cur.execute(
            "SELECT json_completo, processo_referencia FROM ccts_cache WHERE numero_cct = ? ORDER BY atualizado_em DESC LIMIT 1",
            (numero,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)
    if tipo == "DUIMP":
        # tabela duimps usa payload_completo e status
        cur.execute(
            "SELECT payload_completo, processo_referencia FROM duimps WHERE numero = ? ORDER BY atualizado_em DESC LIMIT 1",
            (numero,),
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)
    return (None, None)


def _fetch_from_serpro(adapter, tipo: str, numero: str) -> Optional[Dict[str, Any]]:
    """
    Busca um "payload mínimo" no SQL Server (Serpro) para CE/DI.
    Retorna dict com campos parecidos com a API (suficiente para _extrair_campos_relevantes).
    """
    tipo = (tipo or "").upper().strip()
    num_esc = _sql_escape(numero)

    if tipo == "CE":
        q = f"""
            SELECT TOP 1
                numero,
                numeroCEMaster,
                numeroBlConhecimento,
                situacaoCarga,
                dataSituacaoCarga,
                dataEmissao,
                dataDestinoFinal,
                navioPrimTransporte,
                portoOrigem,
                portoDestino,
                paisProcedencia,
                cargaBloqueada,
                bloqueioImpedeEntregaCarga
            FROM Serpro.dbo.Ce_Root_Conhecimento_Embarque
            WHERE numero = '{num_esc}'
            ORDER BY updatedAt DESC
        """
        r = adapter.execute_query(q, database=DB)
        if not r.get("success") or not r.get("data"):
            return None
        row = r["data"][0]
        # mapear para formato "parecido com API"
        return {
            "numero": row.get("numero"),
            "numeroCEMaster": row.get("numeroCEMaster"),
            "numeroBlConhecimento": row.get("numeroBlConhecimento"),
            "situacaoCarga": row.get("situacaoCarga"),
            "dataSituacaoCarga": row.get("dataSituacaoCarga"),
            "dataEmissao": row.get("dataEmissao"),
            "dataDestinoFinal": row.get("dataDestinoFinal"),
            "navioPrimTransporte": row.get("navioPrimTransporte"),
            "portoOrigem": row.get("portoOrigem"),
            "portoDestino": row.get("portoDestino"),
            "paisProcedencia": row.get("paisProcedencia"),
            "cargaBloqueada": row.get("cargaBloqueada"),
            "bloqueioImpedeEntregaCarga": row.get("bloqueioImpedeEntregaCarga"),
            "_fonte": "SERPRO",
        }

    if tipo == "DI":
        q = f"""
            SELECT TOP 1
                g.numeroDi,
                g.situacaoDi,
                g.dataHoraSituacaoDi,
                g.situacaoEntregaCarga,
                g.sequencialRetificacao,
                d.canalSelecaoParametrizada,
                d.dataHoraRegistro,
                d.dataHoraDesembaraco,
                d.dataHoraAutorizacaoEntrega
            FROM Serpro.dbo.Di_Dados_Gerais g
            LEFT JOIN Serpro.dbo.Di_Root_Declaracao_Importacao r
                ON r.dadosGeraisId = g.dadosGeraisId
            LEFT JOIN Serpro.dbo.Di_Dados_Despacho d
                ON d.dadosDespachoId = r.dadosDespachoId
            WHERE g.numeroDi = '{num_esc}'
            ORDER BY g.updatedAt DESC
        """
        r = adapter.execute_query(q, database=DB)
        if not r.get("success") or not r.get("data"):
            return None
        row = r["data"][0]
        return {
            "numero": row.get("numeroDi"),
            "situacaoDi": row.get("situacaoDi"),
            "dataHoraSituacaoDi": row.get("dataHoraSituacaoDi"),
            "situacaoEntregaCarga": row.get("situacaoEntregaCarga"),
            "numeroRetificacao": row.get("sequencialRetificacao"),
            "canalSelecaoParametrizada": row.get("canalSelecaoParametrizada"),
            "dataHoraRegistro": row.get("dataHoraRegistro"),
            "dataHoraDesembaraco": row.get("dataHoraDesembaraco"),
            "dataHoraAutorizacaoEntrega": row.get("dataHoraAutorizacaoEntrega"),
            "_fonte": "SERPRO",
        }

    return None


def _fetch_from_duimp_db(adapter, numero_duimp: str) -> Optional[Dict[str, Any]]:
    num_esc = _sql_escape(numero_duimp)
    q = f"""
        SELECT TOP 1
            numero,
            versao,
            data_registro,
            ultima_situacao,
            ultimo_evento,
            data_ultimo_evento,
            numero_processo,
            consulta_duimp
        FROM Duimp.dbo.duimp
        WHERE numero = '{num_esc}'
        ORDER BY atualizado_em DESC
    """
    r = adapter.execute_query(q, database=DB)
    if not r.get("success") or not r.get("data"):
        return None
    row = r["data"][0]
    return {
        "numero": row.get("numero"),
        "versaoDocumento": row.get("versao"),
        "situacao": row.get("ultima_situacao"),
        "ultimaSituacao": row.get("ultima_situacao"),
        "ultimaSituacaoData": row.get("data_ultimo_evento"),
        "dataRegistro": row.get("data_registro"),
        "numeroProcesso": row.get("numero_processo"),
        "consulta_duimp": row.get("consulta_duimp"),
        "_fonte": "DUIMP_DB",
    }


def _pick_update(row: Dict[str, Any], campos: Dict[str, Any], processo_from_cache: Optional[str], json_text: Optional[str], versao_norm: Optional[str]) -> Dict[str, Any]:
    update: Dict[str, Any] = {}

    # processo_referencia
    if _is_empty(row.get("processo_referencia")) and processo_from_cache:
        update["processo_referencia"] = processo_from_cache

    # versao_documento
    if _is_empty(row.get("versao_documento")) and versao_norm:
        update["versao_documento"] = versao_norm

    # status / codigo / canal / situacao
    for key in ("status_documento", "status_documento_codigo", "canal_documento", "situacao_documento"):
        if _is_empty(row.get(key)) and not _is_empty(campos.get(key)):
            update[key] = campos.get(key)

    # datas
    for key in ("data_registro", "data_situacao", "data_desembaraco"):
        if row.get(key) is None and campos.get(key) is not None:
            update[key] = campos.get(key)

    # json_dados_originais
    if row.get("json_dados_originais") is None and json_text:
        update["json_dados_originais"] = json_text

    return update


def _exists_other_with_versao(adapter, tipo: str, numero: str, versao: str, current_id: int) -> bool:
    tipo_esc = _sql_escape(tipo)
    num_esc = _sql_escape(numero)
    ver_esc = _sql_escape(versao)
    sql = f"""
        SELECT TOP 1 id_documento
        FROM dbo.DOCUMENTO_ADUANEIRO
        WHERE tipo_documento = '{tipo_esc}'
          AND numero_documento = '{num_esc}'
          AND versao_documento = '{ver_esc}'
          AND id_documento <> {int(current_id)}
    """
    r = adapter.execute_query(sql, database=DB)
    return bool(r and r.get("success") and r.get("data"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill DOCUMENTO_ADUANEIRO (mAIke_assistente).")
    parser.add_argument("--limit", type=int, default=500, help="Máx de documentos para processar (default: 500).")
    parser.add_argument("--dry-run", action="store_true", help="Não atualiza SQL Server; apenas imprime o plano.")
    args = parser.parse_args()

    adapter = get_sql_adapter()
    if not adapter:
        print("❌ SQL Server adapter não disponível")
        return 2

    sqlite_path = ROOT_DIR / "chat_ia.db"
    if not sqlite_path.exists():
        print("❌ SQLite não encontrado: chat_ia.db")
        return 1

    svc = DocumentoHistoricoService()
    sqlite_conn = sqlite3.connect(str(sqlite_path))

    # Buscar candidatos: qualquer lacuna em campos que conseguimos preencher
    sql = f"""
        SELECT TOP {int(args.limit)}
            id_documento,
            numero_documento,
            tipo_documento,
            versao_documento,
            processo_referencia,
            status_documento,
            status_documento_codigo,
            canal_documento,
            situacao_documento,
            data_registro,
            data_situacao,
            data_desembaraco,
            json_dados_originais,
            atualizado_em
        FROM dbo.DOCUMENTO_ADUANEIRO
        WHERE
            (processo_referencia IS NULL OR LTRIM(RTRIM(processo_referencia)) = '')
            OR (status_documento IS NULL OR LTRIM(RTRIM(status_documento)) = '')
            OR (status_documento_codigo IS NULL OR LTRIM(RTRIM(status_documento_codigo)) = '')
            OR (situacao_documento IS NULL OR LTRIM(RTRIM(situacao_documento)) = '')
            OR (canal_documento IS NULL OR LTRIM(RTRIM(canal_documento)) = '')
            OR (data_registro IS NULL)
            OR (data_situacao IS NULL)
            OR (data_desembaraco IS NULL)
            OR (json_dados_originais IS NULL)
        ORDER BY atualizado_em DESC
    """

    r = adapter.execute_query(sql, database=DB)
    if not r.get("success"):
        print(f"❌ Falha buscando candidatos: {r.get('error')}")
        return 1

    rows = r.get("data") or []
    print(f"🔎 Candidatos encontrados: {len(rows)} (limit={args.limit})")

    updated = 0
    skipped = 0
    errors = 0

    for row in rows:
        try:
            doc_id = int(row.get("id_documento"))
            numero = str(row.get("numero_documento") or "").strip()
            tipo = str(row.get("tipo_documento") or "").strip().upper()
            if not numero or not tipo:
                skipped += 1
                continue

            # Algumas linhas antigas tinham numero "api" — não há como backfill pelo cache
            if tipo == "DUIMP" and numero.lower() == "api":
                skipped += 1
                continue

            # Sempre tentar obter JSON do cache SQLite (em geral é mais completo que o "resumo" salvo no SQL Server)
            sqlite_json, processo_cache = _fetch_json_from_sqlite(sqlite_conn, tipo, numero)

            json_text = row.get("json_dados_originais")
            if sqlite_json:
                # Preferir o JSON mais completo (maior) do cache
                if not json_text or len(str(sqlite_json)) > len(str(json_text)):
                    json_text = sqlite_json

            # Fallback: se ainda não temos JSON útil, buscar no SQL Server fonte (Serpro/Duimp)
            if not json_text or len(str(json_text)) < 400:
                payload = None
                if tipo in ("CE", "DI"):
                    payload = _fetch_from_serpro(adapter, tipo, numero)
                elif tipo == "DUIMP":
                    payload = _fetch_from_duimp_db(adapter, numero)
                if isinstance(payload, dict):
                    try:
                        candidate = json.dumps(payload, ensure_ascii=False, default=str)
                        if not json_text or len(candidate) > len(str(json_text)):
                            json_text = candidate
                    except Exception:
                        pass

            dados = None
            if json_text:
                try:
                    dados = json.loads(json_text)
                except Exception:
                    # Algumas cargas antigas foram salvas como repr(dict) com aspas simples.
                    try:
                        dados = ast.literal_eval(json_text)
                    except Exception:
                        dados = None

            # Aceitar também [dict] (algumas APIs retornam lista)
            if isinstance(dados, list) and len(dados) == 1 and isinstance(dados[0], dict):
                dados = dados[0]

            if not isinstance(dados, dict):
                skipped += 1
                continue

            campos = svc._extrair_campos_relevantes(dados, tipo)  # reuse do mapeamento canônico
            versao_norm = svc._extrair_versao_documento(dados, tipo)

            update = _pick_update(row, campos, processo_cache, json_text, versao_norm)

            # Segurança: só setar versão se não conflitar com unique index
            if "versao_documento" in update:
                if _exists_other_with_versao(adapter, tipo, numero, update["versao_documento"], doc_id):
                    update.pop("versao_documento", None)

            if not update:
                skipped += 1
                continue

            set_parts = []
            for k, v in update.items():
                set_parts.append(f"{k} = {_sql_literal(v)}")
            set_parts.append("ultima_sincronizacao = GETDATE()")
            set_parts.append("atualizado_em = GETDATE()")

            upd_sql = f"""
                UPDATE dbo.DOCUMENTO_ADUANEIRO
                SET {', '.join(set_parts)}
                WHERE id_documento = {doc_id}
            """

            if args.dry_run:
                print(f"\n--- would update id_documento={doc_id} ({tipo} {numero}) ---")
                print(upd_sql.strip())
            else:
                rr = adapter.execute_query(upd_sql, database=DB)
                if not rr.get("success", True):
                    errors += 1
                    continue
                updated += 1

        except Exception:
            errors += 1

    sqlite_conn.close()
    print(f"✅ Backfill concluído: updated={updated}, skipped={skipped}, errors={errors}, dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

