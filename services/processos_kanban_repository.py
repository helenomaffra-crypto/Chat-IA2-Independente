import json
import logging
import sqlite3
from typing import Any, Callable, Dict, List, Optional

from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)


def listar_processos_por_navio(
    nome_navio: str,
    categoria: Optional[str] = None,
    limit: int = 200,
    *,
    obter_dados_documentos_processo: Optional[Callable[[str], Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Lista processos filtrados por nome do navio (consulta `processos_kanban`)."""
    try:
        import re
        import unicodedata
        from difflib import SequenceMatcher

        if obter_dados_documentos_processo is None:
            raise ValueError("obter_dados_documentos_processo é obrigatório (injeção para evitar import circular)")

        def _normalizar_nome_navio(s: str) -> str:
            if not s:
                return ""
            s = unicodedata.normalize("NFKD", s)
            s = "".join(ch for ch in s if not unicodedata.combining(ch))
            s = s.upper()
            s = re.sub(r"[^A-Z0-9 ]+", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            return s

        def _similaridade(a: str, b: str) -> float:
            if not a or not b:
                return 0.0
            a_n = _normalizar_nome_navio(a)
            b_n = _normalizar_nome_navio(b)
            if not a_n or not b_n:
                return 0.0
            r1 = SequenceMatcher(None, a_n, b_n).ratio()
            a_tok = " ".join(sorted(a_n.split()))
            b_tok = " ".join(sorted(b_n.split()))
            r2 = SequenceMatcher(None, a_tok, b_tok).ratio()
            return max(r1, r2)

        def _listar_navios_distintos(cursor: sqlite3.Cursor) -> List[str]:
            cursor.execute(
                """
                SELECT DISTINCT nome_navio
                FROM processos_kanban
                WHERE nome_navio IS NOT NULL
                  AND nome_navio != ''
                LIMIT 5000
                """
            )
            return [r[0] for r in cursor.fetchall() if r and r[0]]

        def _sugerir_navios(nome_busca: str, cursor: sqlite3.Cursor, top_n: int = 3) -> List[str]:
            candidatos = _listar_navios_distintos(cursor)
            scored = []
            for cand in candidatos:
                score = _similaridade(nome_busca, cand)
                if score > 0:
                    scored.append((score, cand))
            scored.sort(key=lambda x: x[0], reverse=True)
            sugestoes = []
            for score, cand in scored[: max(10, top_n)]:
                if score >= 0.72 and cand not in sugestoes:
                    sugestoes.append(cand)
                if len(sugestoes) >= top_n:
                    break
            return sugestoes

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row

        query = """
            SELECT DISTINCT pk.processo_referencia, pk.eta_iso, pk.porto_codigo, pk.porto_nome,
                   pk.nome_navio, pk.status_shipsgo
            FROM processos_kanban pk
            WHERE pk.nome_navio IS NOT NULL
            AND pk.nome_navio != ''
            AND LOWER(pk.nome_navio) LIKE LOWER(?)
        """
        params: List[Any] = [f"%{nome_navio}%"]

        categoria_upper = None
        if categoria:
            categoria_upper = categoria.upper().strip()
            query += " AND pk.processo_referencia LIKE ?"
            params.append(f"{categoria_upper}.%")

        query += " ORDER BY pk.eta_iso ASC LIMIT ?"
        params.append(limit)

        logging.info(
            f'🔍 listar_processos_por_navio: Buscando navio "{nome_navio}" (categoria={categoria}, limite={limit})'
        )

        cursor.execute(query, params)
        rows = cursor.fetchall()
        logging.info(f'🔍 listar_processos_por_navio: Encontrados {len(rows)} processos no navio "{nome_navio}"')

        fuzzy_used = False
        navio_match = nome_navio

        if not rows:
            sugestoes = _sugerir_navios(nome_navio, cursor, top_n=3)
            if sugestoes:
                melhor = sugestoes[0]
                if _similaridade(nome_navio, melhor) >= 0.86:
                    fuzzy_used = True
                    navio_match = melhor
                    logging.info(f'🔎 listar_processos_por_navio: fuzzy match "{nome_navio}" -> "{navio_match}"')
                    params2: List[Any] = [f"%{navio_match}%"]
                    if categoria_upper:
                        params2.append(f"{categoria_upper}.%")
                    params2.append(limit)
                    cursor.execute(query, params2)
                    rows = cursor.fetchall()
                    logging.info(
                        f'🔎 listar_processos_por_navio: (fuzzy) Encontrados {len(rows)} processos no navio "{navio_match}"'
                    )

        if not rows:
            conn.close()
            return []

        resultados: List[Dict[str, Any]] = []
        for row in rows:
            processo_ref = row["processo_referencia"]
            try:
                dados_docs = obter_dados_documentos_processo(processo_ref)

                processo_info: Dict[str, Any] = {
                    "processo_referencia": processo_ref,
                    "_navio_query": nome_navio,
                    "_navio_match": navio_match,
                    "_navio_fuzzy_used": fuzzy_used,
                }

                dis = dados_docs.get("dis", [])
                if dis:
                    di = dis[0]
                    processo_info["di"] = {
                        "numero": di.get("numero_di", ""),
                        "situacao": di.get("situacao_di", ""),
                        "canal": di.get("canal_selecao_parametrizada", ""),
                        "data_desembaraco": di.get("data_hora_desembaraco", ""),
                    }

                duimps = dados_docs.get("duimps", [])
                duimps_producao = [
                    d for d in duimps if d.get("vinda_do_ce", False) or d.get("ambiente") == "producao"
                ]
                if duimps_producao:
                    duimp = duimps_producao[0]
                    processo_info["duimp"] = {
                        "numero": duimp.get("numero_duimp", ""),
                        "versao": duimp.get("versao_duimp", ""),
                        "situacao": duimp.get("situacao_duimp", ""),
                        "canal": duimp.get("canal_consolidado", ""),
                    }

                ces = dados_docs.get("ces", [])
                if ces:
                    ce = ces[0]
                    processo_info["ce"] = {
                        "numero": ce.get("numero", ""),
                        "situacao": ce.get("situacao", ""),
                    }

                nome_navio_db = row["nome_navio"] if "nome_navio" in row.keys() else None
                eta_iso = row["eta_iso"] if "eta_iso" in row.keys() else None
                porto_codigo = row["porto_codigo"] if "porto_codigo" in row.keys() else None
                porto_nome = row["porto_nome"] if "porto_nome" in row.keys() else None
                status_shipsgo = row["status_shipsgo"] if "status_shipsgo" in row.keys() else None

                processo_info["eta"] = {
                    "eta_iso": eta_iso,
                    "porto_codigo": porto_codigo,
                    "porto_nome": porto_nome,
                    "nome_navio": nome_navio_db,
                    "status_shipsgo": status_shipsgo,
                }

                processo_info["shipsgo"] = {
                    "shipsgo_eta": eta_iso,
                    "shipsgo_porto_codigo": porto_codigo,
                    "shipsgo_porto_nome": porto_nome,
                    "shipsgo_navio": nome_navio_db,
                    "shipsgo_status": status_shipsgo,
                }

                resultados.append(processo_info)
            except Exception as e:
                logging.warning(f"Erro ao obter dados do processo {processo_ref}: {e}")
                continue

        conn.close()
        resultados.sort(key=lambda x: x.get("eta", {}).get("eta_iso", "") or "")
        return resultados
    except Exception as e:
        logging.error(f"Erro ao listar processos por navio: {e}")
        import traceback

        logging.error(traceback.format_exc())
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass
        return []


def listar_processos_registrados_hoje(
    categoria: Optional[str] = None,
    limit: int = 200,
    *,
    dias_atras: int = 0,
) -> List[Dict[str, Any]]:
    """Lista processos que tiveram DI ou DUIMP registrada em D dias (0=hoje, 1=ontem) via `notificacoes_processos`."""
    try:
        from datetime import datetime, timedelta
        try:
            from zoneinfo import ZoneInfo  # py3.9+
            hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
        except Exception:
            hoje = datetime.now().date()

        try:
            dias_atras_int = int(dias_atras or 0)
        except Exception:
            dias_atras_int = 0
        if dias_atras_int < 0:
            dias_atras_int = 0

        dia_ref = (hoje - timedelta(days=dias_atras_int)).strftime("%Y-%m-%d")
        label = "hoje" if dias_atras_int == 0 else "ontem" if dias_atras_int == 1 else f"D-{dias_atras_int}"
        logging.info(
            f"🔍 listar_processos_registrados_hoje: Buscando processos com DI/DUIMP registrada {label} ({dia_ref}), categoria={categoria}"
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row

        query = """
            SELECT
                n.processo_referencia,
                n.tipo_notificacao,
                n.mensagem,
                n.dados_extras,
                n.criado_em,
                pk.etapa_kanban,
                pk.modal,
                pk.numero_ce,
                pk.situacao_ce
            FROM notificacoes_processos n
            LEFT JOIN processos_kanban pk ON n.processo_referencia = pk.processo_referencia
            WHERE DATE(n.criado_em) = DATE(?)
            AND n.tipo_notificacao IN ('status_di', 'status_duimp')
            AND n.dados_extras IS NOT NULL
            AND n.dados_extras != ''
        """
        params: List[Any] = [dia_ref]

        if categoria:
            categoria_upper = categoria.upper().strip()
            query += " AND n.processo_referencia LIKE ?"
            params.append(f"{categoria_upper}.%")

        query += " ORDER BY n.criado_em DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        logging.info(
            f"🔍 listar_processos_registrados_hoje: Encontradas {len(rows)} notificações de status_di/status_duimp ({label})"
        )

        if not rows:
            conn.close()
            return []

        def _buscar_status_atual_doc(
            *,
            tipo_doc: str,
            numero_doc: str,
            processo_ref: str,
            conn_sqlite: sqlite3.Connection,
        ) -> str:
            """
            Enriquecer status exibido:
            - DI: preferir dis_cache.situacao_di (é o status mais atual que o sistema usa em relatórios)
            - DUIMP: preferir snapshot Kanban (processos_kanban.dados_completos_json.duimp[].ultima_situacao/situacao_duimp)
            """
            try:
                cur2 = conn_sqlite.cursor()
                cur2.row_factory = sqlite3.Row
                t = (tipo_doc or "").upper().strip()
                n = (numero_doc or "").strip()
                if not n:
                    return ""

                if t == "DI":
                    # Preferir snapshot Kanban (mesma fonte usada em relatórios do dia)
                    cur2.execute(
                        """
                        SELECT situacao_di, dados_completos_json
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                        LIMIT 1
                        """,
                        (processo_ref,),
                    )
                    r = cur2.fetchone()
                    if r:
                        st = r["situacao_di"]
                        if st and str(st).strip():
                            return str(st).strip()
                        # fallback: tentar extrair do JSON do Kanban
                        try:
                            if r["dados_completos_json"]:
                                js = json.loads(r["dados_completos_json"])
                            else:
                                js = {}
                        except Exception:
                            js = {}
                        if isinstance(js, dict):
                            # nível raiz (ex: processos rodoviários) ou chaves variantes
                            st2 = js.get("situacaoDI") or js.get("situacao_di")
                            if st2 and str(st2).strip():
                                return str(st2).strip()
                            dis_js = js.get("di")
                            if isinstance(dis_js, list):
                                for di_item in dis_js:
                                    if not isinstance(di_item, dict):
                                        continue
                                    numero_di_json = di_item.get("numero_di") or di_item.get("numero") or ""
                                    if str(numero_di_json).strip() == n:
                                        st3 = di_item.get("situacao_di") or di_item.get("situacao") or ""
                                        if st3 and str(st3).strip():
                                            return str(st3).strip()
                            elif isinstance(dis_js, dict):
                                numero_di_json = dis_js.get("numero_di") or dis_js.get("numero") or ""
                                if str(numero_di_json).strip() == n:
                                    st3 = dis_js.get("situacao_di") or dis_js.get("situacao") or ""
                                    if st3 and str(st3).strip():
                                        return str(st3).strip()
                    return ""

                if t == "DUIMP":
                    cur2.execute(
                        """
                        SELECT dados_completos_json
                        FROM processos_kanban
                        WHERE processo_referencia = ?
                        LIMIT 1
                        """,
                        (processo_ref,),
                    )
                    r = cur2.fetchone()
                    if not r or not r["dados_completos_json"]:
                        return ""
                    try:
                        js = json.loads(r["dados_completos_json"])
                    except Exception:
                        return ""
                    duimps_js = js.get("duimp") if isinstance(js, dict) else None
                    if isinstance(duimps_js, list):
                        for d in duimps_js:
                            if not isinstance(d, dict):
                                continue
                            if str(d.get("numero") or "").strip() != n:
                                continue
                            st = (
                                d.get("situacao_duimp")
                                or d.get("situacao_duimp_agr")
                                or d.get("ultima_situacao")
                                or d.get("situacao")
                                or ""
                            )
                            return str(st) if st else ""
                    return ""

                return ""
            except Exception:
                return ""

        processos_dict: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            try:
                dados_extras = json.loads(row["dados_extras"]) if row["dados_extras"] else {}
                status_anterior = dados_extras.get("status_anterior", "")
                status_novo = dados_extras.get("status_novo", "")

                if status_anterior and status_anterior.upper() in ["SEM STATUS", "SEM_STATUS", ""] and status_novo:
                    proc_ref = row["processo_referencia"]
                    tipo_notif = row["tipo_notificacao"]
                    criado_em = row["criado_em"]

                    numero_doc = dados_extras.get("numero_di") or dados_extras.get("numero_duimp", "")
                    tipo_doc = "DI" if tipo_notif == "status_di" else "DUIMP"

                    if proc_ref not in processos_dict:
                        processos_dict[proc_ref] = {
                            "processo_referencia": proc_ref,
                            "categoria": proc_ref.split(".")[0] if "." in proc_ref else "",
                            "etapa_kanban": row["etapa_kanban"],
                            "modal": row["modal"],
                            "numero_ce": row["numero_ce"],
                            "situacao_ce": row["situacao_ce"],
                            "documentos": [],
                            "ultima_atualizacao": criado_em,
                        }

                    doc_ja_existe = any(d.get("numero") == numero_doc for d in processos_dict[proc_ref]["documentos"])
                    if not doc_ja_existe and numero_doc:
                        # ✅ Enriquecer status exibido com fonte atual (evita "status errado" vs relatório do dia)
                        status_atual = _buscar_status_atual_doc(
                            tipo_doc=tipo_doc,
                            numero_doc=numero_doc,
                            processo_ref=proc_ref,
                            conn_sqlite=conn,
                        )
                        status_exibido = status_atual or status_novo
                        processos_dict[proc_ref]["documentos"].append(
                            {
                                "tipo": tipo_doc,
                                "numero": numero_doc,
                                "atualizado_em": criado_em,
                                "status_novo": status_exibido,
                                "status_notificacao": status_novo,
                            }
                        )

                    if criado_em > processos_dict[proc_ref]["ultima_atualizacao"]:
                        processos_dict[proc_ref]["ultima_atualizacao"] = criado_em
            except Exception as e:
                logging.warning(f'Erro ao processar notificação {row.get("id", "?")}: {e}')
                continue

        resultados = list(processos_dict.values())
        resultados.sort(key=lambda x: x.get("ultima_atualizacao", ""), reverse=True)
        resultados = resultados[:limit]

        conn.close()
        logging.info(
            f"✅ listar_processos_registrados_hoje: Retornando {len(resultados)} processos únicos com DI/DUIMP registrada ({label})"
        )
        return resultados
    except Exception as e:
        logging.error(f"Erro ao listar processos registrados hoje: {e}")
        import traceback

        logging.error(traceback.format_exc())
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass
        return []


def listar_processos_em_dta(categoria: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Lista processos em DTA (tem DTA e não tem DI/DUIMP) via `processos_kanban`."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row

        query = """
            SELECT pk.processo_referencia, pk.dados_completos_json,
                   pk.numero_ce, pk.situacao_ce, pk.etapa_kanban, pk.modal,
                   pk.numero_dta, pk.documento_despacho, pk.numero_documento_despacho,
                   pk.data_destino_final, pk.atualizado_em
            FROM processos_kanban pk
            WHERE pk.numero_dta IS NOT NULL
            AND pk.numero_dta != ''
            AND pk.dados_completos_json IS NOT NULL
            AND pk.dados_completos_json != ''
            AND (pk.numero_di IS NULL OR pk.numero_di = '' OR pk.numero_di = '/       -')
            AND (pk.numero_duimp IS NULL OR pk.numero_duimp = '')
        """
        params: List[Any] = []

        if categoria:
            query += " AND pk.processo_referencia LIKE ?"
            params.append(f"{categoria.upper()}.%")

        query += " ORDER BY pk.atualizado_em DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        processos: List[Dict[str, Any]] = []
        for row in rows:
            try:
                _ = json.loads(row["dados_completos_json"])
                processos.append(
                    {
                        "processo_referencia": row["processo_referencia"],
                        "numero_ce": row["numero_ce"],
                        "situacao_ce": row["situacao_ce"],
                        "etapa_kanban": row["etapa_kanban"],
                        "modal": row["modal"],
                        "numero_dta": row["numero_dta"],
                        "documento_despacho": row["documento_despacho"],
                        "numero_documento_despacho": row["numero_documento_despacho"],
                        "data_destino_final": row["data_destino_final"],
                        "atualizado_em": row["atualizado_em"],
                    }
                )
            except Exception as e:
                logging.warning(f'Erro ao processar processo {row["processo_referencia"]}: {e}')
                continue

        return processos
    except Exception as e:
        logging.error(f"Erro ao listar processos em DTA: {e}")
        return []

