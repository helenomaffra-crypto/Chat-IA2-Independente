import json
import logging
import re
import sqlite3
from typing import Any, Callable, Dict, List, Optional

from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)


def listar_processos_liberados_registro(
    categoria: Optional[str] = None,
    dias_retroativos: Optional[int] = 5,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    limit: int = 200,
    *,
    obter_dados_documentos_processo: Callable[..., Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Lista processos que chegaram (data de chegada/destino <= hoje) e NÃO têm DI nem DUIMP registrada.

    Implementação extraída do `db_manager.py` para reduzir monólito.
    """
    try:
        from datetime import datetime, timedelta

        if obter_dados_documentos_processo is None:
            raise ValueError("obter_dados_documentos_processo é obrigatório (injeção para evitar import circular)")

        # Calcular período de busca
        hoje = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)

        if data_inicio:
            try:
                if "/" in data_inicio:
                    partes = data_inicio.split("/")
                    if len(partes) == 3:
                        data_inicio_dt = datetime(int(partes[2]), int(partes[1]), int(partes[0]))
                    else:
                        logging.warning(f"Formato de data_inicio inválido: {data_inicio}")
                        data_inicio_dt = hoje - timedelta(days=5)
                else:
                    data_inicio_dt = datetime.fromisoformat(data_inicio.split("T")[0])
            except Exception as e:
                logging.warning(f"Erro ao parsear data_inicio {data_inicio}: {e}")
                data_inicio_dt = hoje - timedelta(days=5)
        elif dias_retroativos:
            data_inicio_dt = hoje - timedelta(days=dias_retroativos)
        else:
            data_inicio_dt = hoje - timedelta(days=365)

        if data_fim:
            try:
                if "/" in data_fim:
                    partes = data_fim.split("/")
                    if len(partes) == 3:
                        data_fim_dt = datetime(int(partes[2]), int(partes[1]), int(partes[0]), 23, 59, 59)
                    else:
                        logging.warning(f"Formato de data_fim inválido: {data_fim}")
                        data_fim_dt = hoje
                else:
                    data_fim_dt = datetime.fromisoformat(data_fim.split("T")[0])
                    data_fim_dt = data_fim_dt.replace(hour=23, minute=59, second=59)
            except Exception as e:
                logging.warning(f"Erro ao parsear data_fim {data_fim}: {e}")
                data_fim_dt = hoje
        else:
            data_fim_dt = hoje

        logging.info(
            f"🔍 listar_processos_liberados_registro: Buscando processos que chegaram entre {data_inicio_dt.date()} e {data_fim_dt.date()}, sem DI/DUIMP (categoria={categoria})"
        )

        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT pk.processo_referencia, pk.dados_completos_json,
                   pk.numero_ce, pk.situacao_ce, pk.etapa_kanban, pk.modal,
                   pk.numero_di, pk.numero_duimp
            FROM processos_kanban pk
            WHERE (pk.numero_di IS NULL OR pk.numero_di = '' OR pk.numero_di = '/       -')
            AND (pk.numero_duimp IS NULL OR pk.numero_duimp = '')
            AND (pk.numero_dta IS NULL OR pk.numero_dta = '')
            AND pk.dados_completos_json IS NOT NULL
            AND pk.dados_completos_json != ''
            AND pk.processo_referencia IS NOT NULL
            AND pk.processo_referencia != ''
        """
        params: List[Any] = []

        if categoria:
            categoria_upper = categoria.upper().strip()
            query += " AND pk.processo_referencia LIKE ?"
            params.append(f"{categoria_upper}.%")

        cursor.execute(query, params)
        rows = cursor.fetchall()

        logging.info(
            f"🔍 listar_processos_liberados_registro: Encontrados {len(rows)} processos sem DI/DUIMP (antes de filtrar por data de chegada)"
        )

        if not rows:
            conn.close()
            return []

        def parse_date_from_json(date_str: Any) -> Optional["datetime"]:
            if not date_str:
                return None
            try:
                if isinstance(date_str, datetime):
                    return date_str
                if isinstance(date_str, str):
                    formats = [
                        "%Y-%m-%d",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%dT%H:%M:%S.%f",
                        "%d/%m/%Y",
                        "%d/%m/%Y %H:%M:%S",
                    ]
                    date_str_clean = date_str.split("T")[0].split(" ")[0]
                    for fmt in formats:
                        try:
                            return datetime.strptime(date_str_clean, fmt.split()[0] if " " in fmt else fmt)
                        except Exception:
                            continue
            except Exception:
                pass
            return None

        def extrair_data_chegada(json_data: Dict[str, Any], modal: Optional[str] = None) -> Optional["datetime"]:
            if not json_data or not isinstance(json_data, dict):
                return None

            if not modal:
                modal = json_data.get("modal", "").upper()
                if (
                    json_data.get("ceMercante")
                    or json_data.get("numero_ce")
                    or json_data.get("dados_processo_kanban", {}).get("numero_ce")
                ):
                    modal = "MARITIMO"
                elif json_data.get("cct_data") or json_data.get("awbBl") or json_data.get("Shipsgo_air"):
                    modal = "AEREO"

            modal_upper = str(modal).upper()

            if "MARITIMO" in modal_upper or json_data.get("ceMercante") or json_data.get("dados_processo_kanban", {}).get(
                "numero_ce"
            ):
                data_destino = json_data.get("dataDestinoFinal")
                if data_destino:
                    data_parsed = parse_date_from_json(data_destino)
                    if data_parsed:
                        return data_parsed

                data_armazenamento = json_data.get("dataArmazenamento")
                if data_armazenamento:
                    data_parsed = parse_date_from_json(data_armazenamento)
                    if data_parsed:
                        return data_parsed

            elif "AEREO" in modal_upper or json_data.get("cct_data") or json_data.get("awbBl") or json_data.get("Shipsgo_air"):
                data_chegada_efetiva = json_data.get("dataHoraChegadaEfetiva")
                if data_chegada_efetiva:
                    data_parsed = parse_date_from_json(data_chegada_efetiva)
                    if data_parsed:
                        return data_parsed

                shipsgo_air = json_data.get("Shipsgo_air")
                if isinstance(shipsgo_air, dict):
                    chegada_efetiva = shipsgo_air.get("dataHoraChegadaEfetiva")
                    if chegada_efetiva:
                        data_parsed = parse_date_from_json(chegada_efetiva)
                        if data_parsed:
                            return data_parsed

                viagem = json_data.get("viagem", {})
                if isinstance(viagem, dict):
                    chegada_efetiva = viagem.get("dataHoraChegadaEfetiva")
                    if chegada_efetiva:
                        data_parsed = parse_date_from_json(chegada_efetiva)
                        if data_parsed:
                            return data_parsed

            if not modal or modal_upper not in ("MARITIMO", "AEREO"):
                data_destino = json_data.get("dataDestinoFinal")
                if data_destino:
                    data_parsed = parse_date_from_json(data_destino)
                    if data_parsed:
                        return data_parsed

                data_chegada_efetiva = json_data.get("dataHoraChegadaEfetiva")
                if data_chegada_efetiva:
                    data_parsed = parse_date_from_json(data_chegada_efetiva)
                    if data_parsed:
                        return data_parsed

            return None

        def tem_di_duimp_desembaracada(processo_ref: str) -> bool:
            """Verifica se o processo tem DI ou DUIMP desembaraçada (usa cache apenas)."""
            try:
                dados_docs = obter_dados_documentos_processo(processo_ref, usar_sql_server=False)

                dis = dados_docs.get("dis", [])
                for di in dis:
                    situacao_di = (di.get("situacao_di") or "").upper()
                    data_desembaraco = di.get("data_hora_desembaraco")
                    situacao_entrega = (di.get("situacao_entrega_carga") or "").upper()

                    tem_desembaracada_no_nome = "DESEMBARACADA" in situacao_di or "DESEMBARACADO" in situacao_di
                    tem_entrega_autorizada = (
                        "ENTREGA AUTORIZADA SEM PROSSEGUIMENTO" in situacao_di
                        or "ENTREGA AUTORIZADA SEM PROSSEGUIMENTO" in situacao_entrega
                    )

                    if tem_desembaracada_no_nome or tem_entrega_autorizada or data_desembaraco:
                        return True

                duimps = dados_docs.get("duimps", [])
                duimps_producao = [d for d in duimps if d.get("vinda_do_ce", False) or d.get("ambiente") == "producao"]
                for duimp in duimps_producao:
                    situacao_duimp = (duimp.get("situacao_duimp") or "").upper()
                    data_desembaraco = duimp.get("data_hora_desembaraco")

                    tem_desembaracada_no_nome = "DESEMBARACADA" in situacao_duimp or "DESEMBARACADO" in situacao_duimp
                    if tem_desembaracada_no_nome or data_desembaraco:
                        return True
            except Exception as e:
                logging.warning(f"Erro ao verificar DI/DUIMP desembaraçada para {processo_ref}: {e}")
            return False

        def is_vazio_ou_invalido(valor: Any) -> bool:
            if not valor:
                return True
            valor_normalizado = re.sub(r"\s+", " ", str(valor).strip()).strip()
            if valor_normalizado in ("", "/", "-", "/ -", "- /", " / ", "/ - ", "- / "):
                return True
            if re.match(r"^[/\s-]+$", valor_normalizado):
                return True
            return False

        resultados: List[Dict[str, Any]] = []
        for row in rows:
            try:
                processo_ref = row["processo_referencia"]

                json_str = row["dados_completos_json"]
                if not json_str:
                    continue

                try:
                    json_data = json.loads(json_str)
                except Exception:
                    logging.warning(f"Erro ao parsear JSON do processo {processo_ref}")
                    continue

                if tem_di_duimp_desembaracada(processo_ref):
                    continue

                modal = row["modal"] if "modal" in row.keys() else json_data.get("modal", "")

                numero_di_db = row["numero_di"] if "numero_di" in row.keys() and row["numero_di"] else ""
                numero_duimp_db = row["numero_duimp"] if "numero_duimp" in row.keys() and row["numero_duimp"] else ""

                dados_processo = json_data.get("dados_processo_kanban", {})
                numero_di_json = (
                    json_data.get("numeroDi")
                    or json_data.get("numero_di")
                    or (dados_processo.get("numero_di") if isinstance(dados_processo, dict) else "")
                    or ""
                )

                numero_duimp_raw = json_data.get("duimp") or (dados_processo.get("numero_duimp") if isinstance(dados_processo, dict) else None)
                numero_duimp_json = None
                duimp_registrada = False

                if numero_duimp_raw:
                    if isinstance(numero_duimp_raw, list) and len(numero_duimp_raw) > 0:
                        duimp_item = numero_duimp_raw[0]
                        if isinstance(duimp_item, dict):
                            numero_duimp_json = duimp_item.get("numero") or str(duimp_item.get("numero_duimp", ""))
                            situacao_duimp = (
                                duimp_item.get("situacao_duimp")
                                or duimp_item.get("ultima_situacao")
                                or duimp_item.get("situacao_duimp_agr")
                                or ""
                            )
                            if situacao_duimp and (
                                "REGISTRADA" in situacao_duimp.upper() or "AGUARDANDO" in situacao_duimp.upper()
                            ):
                                duimp_registrada = True
                        else:
                            numero_duimp_json = str(duimp_item)
                    elif isinstance(numero_duimp_raw, dict):
                        numero_duimp_json = numero_duimp_raw.get("numero") or numero_duimp_raw.get("numero_duimp")
                        situacao_duimp = (
                            numero_duimp_raw.get("situacao_duimp")
                            or numero_duimp_raw.get("ultima_situacao")
                            or numero_duimp_raw.get("situacao_duimp_agr")
                            or ""
                        )
                        if situacao_duimp and ("REGISTRADA" in situacao_duimp.upper() or "AGUARDANDO" in situacao_duimp.upper()):
                            duimp_registrada = True
                    elif isinstance(numero_duimp_raw, str):
                        numero_duimp_json = numero_duimp_raw

                if not duimp_registrada:
                    ce_data = json_data.get("ce")
                    if isinstance(ce_data, list) and len(ce_data) > 0:
                        ce_data = ce_data[0]
                    if isinstance(ce_data, dict):
                        documento_despacho = ce_data.get("documentoDespacho", [])
                        if isinstance(documento_despacho, list):
                            for doc in documento_despacho:
                                if isinstance(doc, dict) and doc.get("tipo") == "DUIMP":
                                    situacao_doc = doc.get("situacao", "")
                                    if situacao_doc and (
                                        "REGISTRADA" in situacao_doc.upper() or "AGUARDANDO" in situacao_doc.upper()
                                    ):
                                        duimp_registrada = True
                                        break

                if duimp_registrada:
                    continue

                numero_di = numero_di_db or numero_di_json
                numero_duimp = numero_duimp_db or numero_duimp_json

                numero_di_clean = None
                if numero_di and not is_vazio_ou_invalido(numero_di):
                    numero_di_clean = str(numero_di).strip()

                numero_duimp_clean = None
                if numero_duimp and not is_vazio_ou_invalido(numero_duimp):
                    numero_duimp_clean = str(numero_duimp).strip()

                if numero_di_clean or numero_duimp_clean:
                    continue

                data_chegada = extrair_data_chegada(json_data, modal)
                if not data_chegada:
                    continue

                if data_chegada > hoje:
                    continue

                if data_chegada < data_inicio_dt.replace(hour=0, minute=0, second=0):
                    continue
                if data_chegada > data_fim_dt:
                    continue

                tem_lpco = False
                lpco_deferido = False
                numero_lpco = None
                situacao_lpco = None

                lpco_data = None
                if json_data.get("lpco"):
                    lpco_data = json_data.get("lpco", {})
                    if isinstance(lpco_data, list) and len(lpco_data) > 0:
                        lpco_data = lpco_data[0]
                elif json_data.get("lpcoDetails"):
                    lpco_data = json_data.get("lpcoDetails", {})
                    if isinstance(lpco_data, list) and len(lpco_data) > 0:
                        lpco_data = lpco_data[0]

                if lpco_data and isinstance(lpco_data, dict):
                    tem_lpco = True
                    numero_lpco = lpco_data.get("LPCO") or lpco_data.get("numero_lpco") or lpco_data.get("numero")
                    situacao_lpco = (
                        lpco_data.get("situacao") or lpco_data.get("situacao_lpco") or lpco_data.get("status")
                    )
                    if situacao_lpco:
                        lpco_deferido = "deferido" in str(situacao_lpco).lower()

                if tem_lpco and not lpco_deferido:
                    logging.debug(
                        f"Processo {processo_ref} tem LPCO mas não está deferido (situação: {situacao_lpco}). Não pode registrar DI/DUIMP."
                    )
                    continue

                processo_info: Dict[str, Any] = {
                    "processo_referencia": processo_ref,
                    "data_chegada": data_chegada.isoformat(),
                    "categoria": processo_ref.split(".")[0].upper() if "." in processo_ref else None,
                    "numero_ce": row["numero_ce"] or json_data.get("ceMercante") or json_data.get("numero_ce"),
                    "situacao_ce": row["situacao_ce"]
                    or json_data.get("situacaoCargaCe")
                    or json_data.get("situacao_ce"),
                    "etapa_kanban": row["etapa_kanban"] or json_data.get("etapaKanban", ""),
                    "modal": row["modal"] or json_data.get("modal", ""),
                    "tem_lpco": tem_lpco,
                    "lpco_deferido": lpco_deferido,
                    "numero_lpco": numero_lpco,
                    "situacao_lpco": situacao_lpco,
                }

                shipgov2 = json_data.get("shipgov2", {})
                if isinstance(shipgov2, dict):
                    processo_info["nome_navio"] = shipgov2.get("destino_navio") or json_data.get("nomeNavio")
                    processo_info["porto_codigo"] = shipgov2.get("destino_codigo")
                    processo_info["porto_nome"] = shipgov2.get("destino_nome")
                    processo_info["status_shipsgo"] = shipgov2.get("status")

                resultados.append(processo_info)

            except Exception as e:
                proc_ref_error = row["processo_referencia"] if "processo_referencia" in row.keys() else "UNKNOWN"
                logging.warning(f"Erro ao processar processo {proc_ref_error}: {e}")
                continue

        conn.close()

        resultados.sort(key=lambda x: x.get("data_chegada", ""), reverse=True)
        resultados = resultados[:limit]

        logging.info(
            f"✅ listar_processos_liberados_registro: Encontrados {len(resultados)} processos que chegaram sem DI/DUIMP no período especificado"
        )
        return resultados

    except Exception as e:
        logging.error(f"Erro ao listar processos liberados para registro: {e}")
        import traceback

        logging.error(traceback.format_exc())
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass
        return []

