from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _parse_ddmmyyyy(d: str) -> Optional[date]:
    """
    Aceita DD/MM/AAAA ou DD/MM/AA (assume 20AA).
    """
    if not d:
        return None
    s = str(d).strip()
    try:
        if "/" in s:
            parts = s.split("/")
            if len(parts) != 3:
                return None
            dd, mm, yy = parts[0].zfill(2), parts[1].zfill(2), parts[2].strip()
            if len(yy) == 2:
                yy = f"20{yy}"
            return date(int(yy), int(mm), int(dd))
    except Exception:
        return None
    return None


def _month_range(ano: int, mes: int) -> Tuple[date, date]:
    start = date(ano, mes, 1)
    if mes == 12:
        end = date(ano, 12, 31)
    else:
        end = date(ano, mes + 1, 1) - timedelta(days=1)
    return start, end


class RegistrosPeriodoService:
    """
    Lista registros (DI/DUIMP) por período usando SQL Server `mAIke_assistente`.

    Fonte durável:
    - mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO.data_registro
    """

    def listar(
        self,
        *,
        categoria: Optional[str] = None,
        periodo: Optional[str] = None,
        mes: Optional[int] = None,
        ano: Optional[int] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        limite: int = 200,
    ) -> Dict[str, Any]:
        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import get_primary_database

        adapter = get_sql_adapter()
        if not adapter:
            return {"sucesso": False, "erro": "SQL_SERVER_OFFLINE", "dados": None, "resposta": "❌ SQL Server indisponível."}

        db = get_primary_database()  # esperado: mAIke_assistente

        # Resolver período
        hoje = datetime.now().date()
        p = (periodo or "").strip().lower()

        if p in ("", "mes") and mes:
            ano_eff = int(ano) if ano else int(hoje.year)
            start_d, end_d = _month_range(ano_eff, int(mes))
        elif p in ("", "ano") and ano and not mes:
            start_d, end_d = date(int(ano), 1, 1), date(int(ano), 12, 31)
        elif p == "ontem":
            d = hoje - timedelta(days=1)
            start_d, end_d = d, d
        elif p == "semana":
            # Semana atual (seg → hoje)
            start_d = hoje - timedelta(days=hoje.weekday())
            end_d = hoje
        elif p == "periodo_especifico":
            di = _parse_ddmmyyyy(data_inicio or "")
            df = _parse_ddmmyyyy(data_fim or "")
            if not di or not df:
                return {
                    "sucesso": False,
                    "erro": "DATA_INVALIDA",
                    "dados": None,
                    "resposta": "❌ Período inválido. Use `DD/MM/AAAA` (ex: 01/01/2025 a 30/05/2026).",
                }
            start_d, end_d = (di, df) if di <= df else (df, di)
        else:
            # hoje (default)
            start_d, end_d = hoje, hoje

        # Sanitização / limites
        try:
            limite_int = int(limite or 200)
        except Exception:
            limite_int = 200
        if limite_int < 1:
            limite_int = 1
        if limite_int > 1000:
            limite_int = 1000

        categoria_norm = (categoria or "").strip().upper() or None
        if categoria_norm and not categoria_norm.endswith(".%"):
            like_categoria = f"{categoria_norm}.%"
        else:
            like_categoria = None

        # Query híbrida: DOCUMENTO_ADUANEIRO (recente) + Serpro/Duimp DB (histórico completo)
        # ⚠️ Node adapter/pyodbc: evitar parâmetros; escapar manualmente.
        start_sql = start_d.isoformat()
        end_sql = end_d.isoformat()
        where_cat = ""
        if like_categoria:
            safe_like = like_categoria.replace("'", "''")
            where_cat = f" AND processo_referencia LIKE '{safe_like}'"

        # 1) Buscar de DOCUMENTO_ADUANEIRO (processos consultados recentemente)
        q1 = f"""
            SELECT TOP {limite_int}
                COALESCE(processo_referencia, 'N/A') as processo_referencia,
                tipo_documento,
                numero_documento,
                canal_documento,
                situacao_documento,
                data_registro
            FROM {db}.dbo.DOCUMENTO_ADUANEIRO
            WHERE tipo_documento IN ('DI', 'DUIMP')
              AND data_registro IS NOT NULL
              AND CAST(data_registro AS date) >= '{start_sql}'
              AND CAST(data_registro AS date) <= '{end_sql}'
              {where_cat}
        """
        r1 = adapter.execute_query(q1, database=db, notificar_erro=False)
        rows1 = (r1.get("data") or []) if isinstance(r1, dict) and r1.get("success") else []

        # 2) Buscar DI do histórico legado (Serpro) se período for no passado
        rows2 = []
        if start_d < hoje - timedelta(days=30):  # Período > 30 dias atrás
            try:
                where_cat_serpro = ""
                if like_categoria:
                    # Extrair categoria do LIKE (ex: "DMD.%" → "DMD")
                    cat_base = like_categoria.replace(".%", "").replace("'", "''")
                    where_cat_serpro = f" AND p.numero_processo LIKE '{cat_base}.%'"

                q2 = f"""
                    SELECT DISTINCT TOP {limite_int}
                        COALESCE(p.numero_processo, 'ID:' + CAST(diH.idImportacao as VARCHAR(50))) AS processo_referencia,
                        'DI' AS tipo_documento,
                        ddg.numeroDi AS numero_documento,
                        diDesp.canalSelecaoParametrizada AS canal_documento,
                        ddg.situacaoDi AS situacao_documento,
                        diDesp.dataHoraRegistro AS data_registro
                    FROM Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
                    INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                        ON diH.diId = diRoot.dadosDiId
                    INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                        ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                    LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                        ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                    LEFT JOIN {db}.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                        ON p.id_importacao = diH.idImportacao
                    WHERE diDesp.dataHoraRegistro IS NOT NULL
                      AND CAST(diDesp.dataHoraRegistro AS date) >= '{start_sql}'
                      AND CAST(diDesp.dataHoraRegistro AS date) <= '{end_sql}'
                      {where_cat_serpro}
                    ORDER BY diDesp.dataHoraRegistro DESC
                """
                r2 = adapter.execute_query(q2, database="Make", notificar_erro=False)
                rows2 = (r2.get("data") or []) if isinstance(r2, dict) and r2.get("success") else []
            except Exception as e:
                logger.debug(f"Erro ao buscar DI do histórico Serpro: {e}")

        # 3) Buscar DUIMP do histórico legado (Duimp DB) se período for no passado
        rows3 = []
        # ✅ CORREÇÃO (29/01/2026): DUIMP pode não estar em DOCUMENTO_ADUANEIRO (recente),
        # mas existir no Duimp DB. Para evitar "DUIMP=0" incorreto em períodos recentes,
        # fazemos fallback também quando não há nenhuma DUIMP em rows1.
        has_duimp_rows1 = False
        try:
            for _r in (rows1 or []):
                if isinstance(_r, dict) and str(_r.get("tipo_documento") or "").upper() == "DUIMP":
                    has_duimp_rows1 = True
                    break
        except Exception:
            has_duimp_rows1 = False

        if (not has_duimp_rows1) or (start_d < hoje - timedelta(days=30)):  # Período recente sem DUIMP no banco + histórico
            try:
                where_cat_duimp = ""
                if like_categoria:
                    cat_base = like_categoria.replace(".%", "").replace("'", "''")
                    where_cat_duimp = f" AND d.numero_processo LIKE '{cat_base}.%'"

                q3 = f"""
                    SELECT DISTINCT TOP {limite_int}
                        COALESCE(d.numero_processo, 'ID:' + CAST(d.id_processo_importacao as VARCHAR(50))) AS processo_referencia,
                        'DUIMP' AS tipo_documento,
                        d.numero AS numero_documento,
                        drar.canal_consolidado AS canal_documento,
                        d.ultima_situacao AS situacao_documento,
                        d.data_registro AS data_registro
                    FROM Duimp.dbo.duimp d WITH (NOLOCK)
                    LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar WITH (NOLOCK)
                        ON d.duimp_id = drar.duimp_id
                    WHERE d.data_registro IS NOT NULL
                      AND CAST(d.data_registro AS date) >= '{start_sql}'
                      AND CAST(d.data_registro AS date) <= '{end_sql}'
                      {where_cat_duimp}
                    ORDER BY d.data_registro DESC
                """
                r3 = adapter.execute_query(q3, database="Make", notificar_erro=False)
                rows3 = (r3.get("data") or []) if isinstance(r3, dict) and r3.get("success") else []
            except Exception as e:
                logger.debug(f"Erro ao buscar DUIMP do histórico Duimp DB: {e}")

        # 4) Combinar resultados e deduplicar (priorizar DOCUMENTO_ADUANEIRO)
        seen = set()
        rows = []
        for row in rows1 + rows2 + rows3:
            if not isinstance(row, dict):
                continue
            num_doc = str(row.get("numero_documento") or "").strip()
            tipo_doc = (row.get("tipo_documento") or "").upper()
            chave = f"{tipo_doc}:{num_doc}"
            if chave not in seen:
                seen.add(chave)
                rows.append(row)
        
        # Ordenar por data_registro DESC (normalizar datetime/str para comparação)
        def _normalizar_data_registro(dt):
            if dt is None:
                return datetime.min
            if isinstance(dt, datetime):
                return dt
            if isinstance(dt, date):
                return datetime.combine(dt, datetime.min.time())
            # String: tentar parsear
            try:
                if isinstance(dt, str):
                    # Tentar vários formatos
                    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
                        try:
                            return datetime.strptime(dt.split("T")[0].split(" ")[0], fmt)
                        except Exception:
                            continue
            except Exception:
                pass
            return datetime.min
        
        rows.sort(key=lambda x: _normalizar_data_registro(x.get("data_registro")), reverse=True)
        rows = rows[:limite_int]

        # Totais
        total_di = 0
        total_duimp = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            td = (row.get("tipo_documento") or "").upper()
            if td == "DI":
                total_di += 1
            elif td == "DUIMP":
                total_duimp += 1

        dados = {
            "periodo": {
                "inicio": start_d.isoformat(),
                "fim": end_d.isoformat(),
                "categoria": categoria_norm,
            },
            "totais": {"di": total_di, "duimp": total_duimp, "total": total_di + total_duimp},
            "itens": rows,
            "fonte": f"{db}.dbo.DOCUMENTO_ADUANEIRO",
        }

        return {"sucesso": True, "erro": None, "dados": dados}

