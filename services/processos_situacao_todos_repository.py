import logging
import sqlite3
from typing import Any, Callable, Dict, List, Optional

from services.processos_situacao_filters import (
    corresponde_filtro_data_desembaraco,
    parse_data_desembaraco_para_date,
    remover_acentos,
)
from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)


def listar_todos_processos_por_situacao(
    situacao_filtro: Optional[str] = None,
    filtro_pendencias: Optional[bool] = None,
    filtro_bloqueio: Optional[bool] = None,
    filtro_data_desembaraco: Optional[str] = None,
    limit: int = 500,
    *,
    obter_dados_documentos_processo: Callable[..., Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Lista TODOS os processos filtrados por situação/pendências/bloqueios."""
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT processo_referencia
            FROM (
                SELECT DISTINCT processo_referencia FROM processo_documentos
                UNION
                SELECT DISTINCT processo_referencia FROM processos_kanban
                WHERE processo_referencia IS NOT NULL AND processo_referencia != ''
            )
            ORDER BY processo_referencia
            LIMIT ?
            """,
            (limit * 2,),
        )
        rows = cursor.fetchall()
        processos_refs = [row["processo_referencia"] for row in rows]
        conn.close()

        if not processos_refs:
            return []

        resultados: List[Dict[str, Any]] = []
        for processo_ref in processos_refs:
            try:
                dados_docs = obter_dados_documentos_processo(processo_ref)

                processo_info: Dict[str, Any] = {"processo_referencia": processo_ref}

                # DI
                dis = dados_docs.get("dis", [])
                if dis:
                    di = dis[0]
                    processo_info["di"] = {
                        "numero": di.get("numero_di", ""),
                        "situacao": di.get("situacao_di", ""),
                        "canal": di.get("canal_selecao_parametrizada", ""),
                        "data_desembaraco": di.get("data_hora_desembaraco", ""),
                        "data_registro": di.get("data_hora_registro", ""),
                        "situacao_entrega": di.get("situacao_entrega_carga", ""),
                    }

                # DUIMP (produção)
                duimps = dados_docs.get("duimps", [])
                duimps_producao = [d for d in duimps if d.get("vinda_do_ce", False) or d.get("ambiente") == "producao"]
                if duimps_producao:
                    duimp = duimps_producao[0]
                    processo_info["duimp"] = {
                        "numero": duimp.get("numero_duimp", ""),
                        "versao": duimp.get("versao_duimp", ""),
                        "situacao": duimp.get("situacao_duimp", ""),
                        "canal": duimp.get("canal_consolidado", ""),
                        "data_registro": duimp.get("data_registro", ""),
                    }

                # CE
                ces = dados_docs.get("ces", [])
                if ces:
                    ce = ces[0]
                    pendencia_frete_raw = ce.get("pendencia_frete", False)
                    if pendencia_frete_raw in (True, False):
                        pendencia_frete_final = pendencia_frete_raw
                    elif isinstance(pendencia_frete_raw, (int, str)):
                        pendencia_frete_final = (
                            bool(pendencia_frete_raw)
                            if pendencia_frete_raw not in (0, "0", False, "false", "False", "")
                            else False
                        )
                    else:
                        pendencia_frete_final = bool(pendencia_frete_raw) if pendencia_frete_raw else False

                    numero_ce = ce.get("numero", "")
                    if not numero_ce:
                        try:
                            conn_kanban_ce = get_db_connection()
                            cursor_kanban_ce = conn_kanban_ce.cursor()
                            cursor_kanban_ce.execute(
                                """
                                SELECT numero_ce
                                FROM processos_kanban
                                WHERE processo_referencia = ?
                                AND numero_ce IS NOT NULL
                                AND numero_ce != ''
                                LIMIT 1
                                """,
                                (processo_ref,),
                            )
                            row_ce_kanban = cursor_kanban_ce.fetchone()
                            conn_kanban_ce.close()
                            if row_ce_kanban and row_ce_kanban[0]:
                                numero_ce = row_ce_kanban[0]
                        except Exception as e:
                            logging.debug(f"Erro ao buscar número do CE no Kanban para {processo_ref}: {e}")

                    processo_info["ce"] = {
                        "numero": numero_ce,
                        "situacao": ce.get("situacao", ""),
                        "pendencia_frete": pendencia_frete_final,
                        "pendencia_afrmm": ce.get("pendencia_afrmm", False),
                        "carga_bloqueada": ce.get("carga_bloqueada", False),
                        "bloqueio_impede_despacho": ce.get("bloqueio_impede_despacho", False),
                    }
                else:
                    try:
                        conn_kanban_ce_fallback = get_db_connection()
                        conn_kanban_ce_fallback.row_factory = sqlite3.Row
                        cursor_kanban_ce_fallback = conn_kanban_ce_fallback.cursor()
                        cursor_kanban_ce_fallback.execute(
                            """
                            SELECT situacao_ce, numero_ce
                            FROM processos_kanban
                            WHERE processo_referencia = ?
                            AND situacao_ce IS NOT NULL
                            AND situacao_ce != ''
                            """,
                            (processo_ref,),
                        )
                        row_ce_fallback = cursor_kanban_ce_fallback.fetchone()
                        conn_kanban_ce_fallback.close()

                        if row_ce_fallback and row_ce_fallback["situacao_ce"]:
                            processo_info["ce"] = {
                                "numero": row_ce_fallback["numero_ce"] if row_ce_fallback["numero_ce"] else "",
                                "situacao": row_ce_fallback["situacao_ce"],
                                "pendencia_frete": False,
                                "pendencia_afrmm": False,
                                "carga_bloqueada": False,
                                "bloqueio_impede_despacho": False,
                            }
                    except Exception as e:
                        logging.debug(f"Erro ao buscar CE do Kanban para {processo_ref}: {e}")

                # CCT
                ccts = dados_docs.get("ccts", [])
                if ccts:
                    cct = ccts[0]
                    processo_info["cct"] = {
                        "numero": cct.get("numero", ""),
                        "situacao": cct.get("situacao_atual", ""),
                        "pendencia_frete": cct.get("pendencia_frete", False),
                        "tem_bloqueios": cct.get("tem_bloqueios", False),
                    }

                # ShipsGo
                shipsgo = dados_docs.get("shipsgo")
                if shipsgo:
                    processo_info["shipsgo"] = shipsgo

                # 3) Filtro de situação
                situacao_filtro_normalizada = ""
                if situacao_filtro:
                    situacao_filtro_lower = situacao_filtro.lower().strip()
                    situacao_filtro_normalizada = remover_acentos(situacao_filtro_lower)

                    situacao_di = processo_info.get("di", {}).get("situacao", "").lower()
                    situacao_duimp = processo_info.get("duimp", {}).get("situacao", "").lower()
                    situacao_ce = processo_info.get("ce", {}).get("situacao", "").upper()

                    situacao_di_normalizada = remover_acentos(situacao_di)
                    situacao_duimp_normalizada = remover_acentos(situacao_duimp)

                    corresponde = False

                    # Se filtro é "armazenado" e não tem CE populado, buscar no Kanban antes
                    if "armazenad" in situacao_filtro_normalizada and not situacao_ce:
                        try:
                            conn_kanban_pre_ce = get_db_connection()
                            conn_kanban_pre_ce.row_factory = sqlite3.Row
                            cursor_kanban_pre_ce = conn_kanban_pre_ce.cursor()
                            cursor_kanban_pre_ce.execute(
                                """
                                SELECT situacao_ce, numero_ce
                                FROM processos_kanban
                                WHERE processo_referencia = ? AND situacao_ce = 'ARMAZENADA'
                                """,
                                (processo_ref,),
                            )
                            row_kanban_pre_ce = cursor_kanban_pre_ce.fetchone()
                            conn_kanban_pre_ce.close()

                            if row_kanban_pre_ce:
                                if "ce" not in processo_info:
                                    processo_info["ce"] = {}
                                processo_info["ce"]["situacao"] = "ARMAZENADA"
                                processo_info["ce"]["numero"] = (
                                    row_kanban_pre_ce["numero_ce"] if row_kanban_pre_ce["numero_ce"] else ""
                                )
                                situacao_ce = "ARMAZENADA"
                        except Exception as e:
                            logging.debug(f"Erro ao buscar CE do Kanban antes do filtro para {processo_ref}: {e}")

                    if "desembarac" in situacao_filtro_normalizada:
                        corresponde = "desembarac" in situacao_di_normalizada or "desembarac" in situacao_duimp_normalizada

                        if not corresponde:
                            try:
                                conn_kanban = get_db_connection()
                                conn_kanban.row_factory = sqlite3.Row
                                cursor_kanban = conn_kanban.cursor()
                                cursor_kanban.execute(
                                    """
                                    SELECT situacao_di, numero_di, data_desembaraco
                                    FROM processos_kanban
                                    WHERE processo_referencia = ?
                                    AND (situacao_di LIKE '%DESEMBARACADA%' OR situacao_di LIKE '%desembaracada%')
                                    """,
                                    (processo_ref,),
                                )
                                row_kanban = cursor_kanban.fetchone()
                                conn_kanban.close()

                                if row_kanban:
                                    corresponde = True
                                    if "di" not in processo_info:
                                        processo_info["di"] = {}
                                    if row_kanban["situacao_di"]:
                                        processo_info["di"]["situacao"] = row_kanban["situacao_di"]
                                    if row_kanban["numero_di"]:
                                        processo_info["di"]["numero"] = row_kanban["numero_di"]
                                    if row_kanban["data_desembaraco"]:
                                        processo_info["di"]["data_desembaraco"] = row_kanban["data_desembaraco"]

                                    if row_kanban["numero_di"] and not processo_info["di"].get("canal"):
                                        try:
                                            conn_cache = get_db_connection()
                                            cursor_cache = conn_cache.cursor()
                                            cursor_cache.execute(
                                                """
                                                SELECT canal_selecao_parametrizada
                                                FROM dis_cache
                                                WHERE numero_di = ?
                                                LIMIT 1
                                                """,
                                                (row_kanban["numero_di"],),
                                            )
                                            row_canal = cursor_cache.fetchone()
                                            conn_cache.close()
                                            if row_canal and row_canal[0]:
                                                processo_info["di"]["canal"] = row_canal[0]
                                        except Exception as e:
                                            logging.debug(f"Erro ao buscar canal da DI do cache para {processo_ref}: {e}")

                                    if not processo_info["di"].get("canal"):
                                        try:
                                            dados_docs_fallback = obter_dados_documentos_processo(processo_ref)
                                            dis_fallback = dados_docs_fallback.get("dis", [])
                                            if dis_fallback:
                                                di_fallback = dis_fallback[0]
                                                canal_fallback = di_fallback.get("canal_selecao_parametrizada", "")
                                                if canal_fallback:
                                                    processo_info["di"]["canal"] = canal_fallback
                                        except Exception as e:
                                            logging.debug(
                                                f"Erro ao buscar canal via obter_dados_documentos_processo para {processo_ref}: {e}"
                                            )
                            except Exception as e:
                                logging.warning(f"Erro ao buscar situação do DI no Kanban para {processo_ref}: {e}")

                    elif "armazenad" in situacao_filtro_normalizada:
                        if not situacao_ce:
                            try:
                                conn_kanban = get_db_connection()
                                conn_kanban.row_factory = sqlite3.Row
                                cursor_kanban = conn_kanban.cursor()
                                cursor_kanban.execute(
                                    """
                                    SELECT situacao_ce, numero_ce
                                    FROM processos_kanban
                                    WHERE processo_referencia = ? AND situacao_ce = 'ARMAZENADA'
                                    """,
                                    (processo_ref,),
                                )
                                row_kanban = cursor_kanban.fetchone()
                                conn_kanban.close()

                                if row_kanban:
                                    if "ce" not in processo_info:
                                        processo_info["ce"] = {}
                                    processo_info["ce"]["situacao"] = "ARMAZENADA"
                                    processo_info["ce"]["numero"] = row_kanban["numero_ce"] if row_kanban["numero_ce"] else ""
                                    situacao_ce = "ARMAZENADA"
                            except Exception as e:
                                logging.warning(f"Erro ao buscar situação do CE no Kanban para {processo_ref}: {e}")

                        corresponde = situacao_ce == "ARMAZENADA"

                        if corresponde and "ce" in processo_info and not processo_info["ce"].get("numero"):
                            try:
                                conn_kanban_num = get_db_connection()
                                cursor_kanban_num = conn_kanban_num.cursor()
                                cursor_kanban_num.execute(
                                    """
                                    SELECT numero_ce
                                    FROM processos_kanban
                                    WHERE processo_referencia = ? AND situacao_ce = 'ARMAZENADA'
                                    LIMIT 1
                                    """,
                                    (processo_ref,),
                                )
                                row_ce_num = cursor_kanban_num.fetchone()
                                conn_kanban_num.close()
                                if row_ce_num and row_ce_num[0]:
                                    processo_info["ce"]["numero"] = row_ce_num[0]
                            except Exception as e:
                                logging.debug(f"Erro ao buscar número do CE no Kanban para {processo_ref}: {e}")

                    elif "registrad" in situacao_filtro_normalizada:
                        corresponde = "registrad" in situacao_duimp_normalizada
                    elif "entreg" in situacao_filtro_normalizada:
                        corresponde = situacao_ce == "ENTREGUE" or "entreg" in situacao_duimp_normalizada
                    else:
                        corresponde = (
                            situacao_filtro_normalizada in situacao_di_normalizada
                            or situacao_filtro_normalizada in situacao_duimp_normalizada
                            or situacao_filtro_normalizada in situacao_ce.lower()
                        )

                    if not corresponde:
                        continue

                # 4) Filtro de data de desembaraço (apenas quando filtro situacao é desembaraço)
                if filtro_data_desembaraco and situacao_filtro and "desembarac" in (situacao_filtro_normalizada or ""):
                    di_info = processo_info.get("di", {})
                    data_desembaraco = di_info.get("data_desembaraco", "")

                    if not data_desembaraco:
                        try:
                            conn_kanban_data = get_db_connection()
                            conn_kanban_data.row_factory = sqlite3.Row
                            cursor_kanban_data = conn_kanban_data.cursor()
                            cursor_kanban_data.execute(
                                """
                                SELECT data_desembaraco
                                FROM processos_kanban
                                WHERE processo_referencia = ?
                                AND data_desembaraco IS NOT NULL
                                AND data_desembaraco != ''
                                LIMIT 1
                                """,
                                (processo_ref,),
                            )
                            row_kanban_data = cursor_kanban_data.fetchone()
                            conn_kanban_data.close()

                            if row_kanban_data and row_kanban_data["data_desembaraco"]:
                                data_desembaraco = row_kanban_data["data_desembaraco"]
                                if "di" not in processo_info:
                                    processo_info["di"] = {}
                                processo_info["di"]["data_desembaraco"] = data_desembaraco
                        except Exception as e:
                            logging.debug(f"Erro ao buscar data_desembaraco do Kanban para {processo_ref}: {e}")

                    if not data_desembaraco:
                        try:
                            dados_docs_fallback = obter_dados_documentos_processo(processo_ref)
                            dis_fallback = dados_docs_fallback.get("dis", [])
                            if dis_fallback:
                                di_fallback = dis_fallback[0]
                                data_desembaraco_fallback = di_fallback.get("data_hora_desembaraco", "")
                                if data_desembaraco_fallback:
                                    data_desembaraco = data_desembaraco_fallback
                                    if "di" not in processo_info:
                                        processo_info["di"] = {}
                                    processo_info["di"]["data_desembaraco"] = data_desembaraco
                        except Exception as e:
                            logging.debug(
                                f"Erro ao buscar data_desembaraco via obter_dados_documentos_processo para {processo_ref}: {e}"
                            )

                    if not data_desembaraco:
                        continue

                    try:
                        data_date = parse_data_desembaraco_para_date(str(data_desembaraco))
                        if not data_date:
                            continue
                        if not corresponde_filtro_data_desembaraco(data_date, str(filtro_data_desembaraco)):
                            continue
                    except Exception as e:
                        logging.debug(f"Erro ao aplicar filtro de data de desembaraço para {processo_ref}: {e}")

                # 5) Pendências
                if filtro_pendencias is True:
                    tem_pendencia = False

                    try:
                        conn_kanban_pend = get_db_connection()
                        conn_kanban_pend.row_factory = sqlite3.Row
                        cursor_kanban_pend = conn_kanban_pend.cursor()
                        cursor_kanban_pend.execute(
                            """
                            SELECT pendencia_frete, tem_pendencias
                            FROM processos_kanban
                            WHERE processo_referencia = ?
                            LIMIT 1
                            """,
                            (processo_ref,),
                        )
                        row_kanban_pend = cursor_kanban_pend.fetchone()
                        conn_kanban_pend.close()

                        if row_kanban_pend:
                            pendencia_frete_kanban = row_kanban_pend["pendencia_frete"]
                            tem_pendencias_kanban = row_kanban_pend["tem_pendencias"]

                            if pendencia_frete_kanban is True or pendencia_frete_kanban == 1 or (
                                isinstance(pendencia_frete_kanban, str)
                                and str(pendencia_frete_kanban).lower() in ("true", "1", "sim", "yes")
                            ):
                                tem_pendencia = True
                            if tem_pendencias_kanban is True or tem_pendencias_kanban == 1 or (
                                isinstance(tem_pendencias_kanban, str)
                                and str(tem_pendencias_kanban).lower() in ("true", "1", "sim", "yes")
                            ):
                                tem_pendencia = True
                    except Exception as e:
                        logging.debug(f"Erro ao buscar pendências do Kanban para {processo_ref}: {e}")

                    ce_info = processo_info.get("ce", {})
                    if ce_info:
                        pendencia_frete_ce = ce_info.get("pendencia_frete", False)
                        is_true = (
                            pendencia_frete_ce is True
                            or pendencia_frete_ce == 1
                            or (isinstance(pendencia_frete_ce, str) and pendencia_frete_ce.lower() in ("true", "1", "sim", "yes"))
                        )
                        if not is_true and pendencia_frete_ce and pendencia_frete_ce not in (
                            False,
                            0,
                            "0",
                            "false",
                            "False",
                            "",
                            None,
                        ):
                            try:
                                is_true = bool(pendencia_frete_ce)
                            except Exception:
                                is_true = False
                        if is_true:
                            tem_pendencia = True

                        pendencia_afrmm_ce = ce_info.get("pendencia_afrmm", False)
                        if pendencia_afrmm_ce is True or pendencia_afrmm_ce == 1 or (
                            isinstance(pendencia_afrmm_ce, str) and pendencia_afrmm_ce.lower() == "true"
                        ):
                            tem_pendencia = True

                    cct_info = processo_info.get("cct", {})
                    if cct_info:
                        pendencia_frete_cct = cct_info.get("pendencia_frete", False)
                        if pendencia_frete_cct is True or pendencia_frete_cct == 1 or (
                            isinstance(pendencia_frete_cct, str) and pendencia_frete_cct.lower() == "true"
                        ):
                            tem_pendencia = True

                    if not tem_pendencia:
                        continue

                # 6) Bloqueios
                if filtro_bloqueio is True:
                    tem_bloqueio = False

                    ce_info = processo_info.get("ce", {})
                    if ce_info:
                        carga_bloqueada = ce_info.get("carga_bloqueada", False)
                        bloqueio_impede_despacho = ce_info.get("bloqueio_impede_despacho", False)
                        if (
                            carga_bloqueada is True
                            or carga_bloqueada == 1
                            or bloqueio_impede_despacho is True
                            or bloqueio_impede_despacho == 1
                        ):
                            tem_bloqueio = True

                    cct_info = processo_info.get("cct", {})
                    if cct_info:
                        tem_bloqueios_cct = cct_info.get("tem_bloqueios", False)
                        if tem_bloqueios_cct is True or tem_bloqueios_cct == 1 or (
                            isinstance(tem_bloqueios_cct, str) and str(tem_bloqueios_cct).lower() == "true"
                        ):
                            tem_bloqueio = True

                    if not tem_bloqueio:
                        continue

                resultados.append(processo_info)
                if len(resultados) >= limit:
                    break
            except Exception as e:
                logging.warning(f"Erro ao processar processo {processo_ref} na listagem geral por situação: {e}")
                continue

        return resultados
    except Exception as e:
        logging.error(f"Erro ao listar todos os processos por situação {situacao_filtro}: {e}")
        return []

