import json
import logging
import sqlite3
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.ce_pendencias import calcular_pendencias_ce
from services.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)


def _buscar_ce_no_kanban(processo_referencia: str, numero_ce: str) -> Optional[Dict[str, Any]]:
    """Tenta montar um 'ce_cache' mínimo a partir de `processos_kanban` quando `ces_cache` não tem o CE."""
    try:
        conn_kanban = get_db_connection()
        conn_kanban.row_factory = sqlite3.Row
        cursor_kanban = conn_kanban.cursor()
        cursor_kanban.execute(
            """
            SELECT numero_ce, situacao_ce, dados_completos_json
            FROM processos_kanban
            WHERE processo_referencia = ? AND numero_ce = ?
            LIMIT 1
            """,
            (processo_referencia, numero_ce),
        )
        kanban_row = cursor_kanban.fetchone()
        conn_kanban.close()

        if not kanban_row:
            return None

        dados_json = kanban_row["dados_completos_json"]
        ce_json_kanban: Dict[str, Any] = {}
        if dados_json:
            try:
                ce_json_kanban = json.loads(dados_json) if isinstance(dados_json, str) else dados_json
                if not isinstance(ce_json_kanban, dict):
                    ce_json_kanban = {}
            except Exception:
                ce_json_kanban = {}

        situacao_ce_kanban = kanban_row["situacao_ce"]
        if not situacao_ce_kanban and ce_json_kanban:
            situacao_ce_kanban = (
                ce_json_kanban.get("situacaoCargaCe") or ce_json_kanban.get("situacaoCarga") or "ARMAZENADA"
            )

        ce_cache = {
            "numero_ce": numero_ce,
            "situacao": situacao_ce_kanban or "ARMAZENADA",
            "situacao_carga": situacao_ce_kanban or "ARMAZENADA",
            "json_completo": ce_json_kanban,
            "duimp_numero": None,
            "di_numero": None,
            "tipo": ce_json_kanban.get("tipo", "") if ce_json_kanban else "",
            "carga_bloqueada": False,
            "bloqueio_impede_despacho": False,
        }
        logger.info(
            f"✅ Processo {processo_referencia}: CE {numero_ce} encontrado no Kanban (não estava no cache ces_cache)"
        )
        return ce_cache
    except Exception as e:
        logger.warning(f"⚠️ Erro ao buscar CE {numero_ce} do Kanban: {e}")
        return None


def _extrair_duimp_do_documento_despacho(
    processo_referencia: str, numero_ce: str, ce_json: Dict[str, Any]
) -> Optional[str]:
    documento_despacho = ce_json.get("documentoDespacho", [])
    docs_para_processar: List[Any]
    if isinstance(documento_despacho, list):
        docs_para_processar = documento_despacho
    elif isinstance(documento_despacho, dict):
        docs_para_processar = [documento_despacho]
    else:
        docs_para_processar = []

    for doc in docs_para_processar:
        if not isinstance(doc, dict):
            continue
        doc_tipo = doc.get("documentoDespacho", "")
        doc_numero = doc.get("numero", "")
        if doc_tipo == "DUIMP" and doc_numero:
            logger.info(
                f"✅ Processo {processo_referencia}: DUIMP {doc_numero} extraída do documentoDespacho do CE {numero_ce} (não estava no cache)"
            )
            return str(doc_numero)

    return None


def _atualizar_duimp_numero_no_cache_ce(numero_ce: str, duimp_numero: str) -> None:
    try:
        conn_update = get_db_connection()
        cursor_update = conn_update.cursor()
        cursor_update.execute(
            """
            UPDATE ces_cache
            SET duimp_numero = ?
            WHERE numero_ce = ?
            """,
            (duimp_numero, numero_ce),
        )
        conn_update.commit()
        conn_update.close()
        logger.debug(f"✅ Cache do CE {numero_ce} atualizado com duimp_numero {duimp_numero}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao atualizar duimp_numero no cache do CE {numero_ce}: {e}")


def processar_documento_ce(
    processo_referencia: str,
    numero: str,
    *,
    buscar_ce_cache: Callable[[str], Optional[Dict[str, Any]]],
    buscar_ce_itens_cache: Callable[[str], Optional[Dict[str, Any]]],
    obter_previsao_atracacao_ce: Callable[[str, Dict[str, Any]], Optional[Dict[str, Any]]],
    buscar_di_cache: Callable[..., Optional[Dict[str, Any]]],
    obter_processo_por_documento: Callable[[str, str], Optional[str]],
    vincular_documento_processo: Callable[[str, str, str], Any],
    processo_sql_server_data: Optional[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], bool]:
    """
    Processa um documento CE (cache + fallback Kanban), retornando:
      (ce_data ou None, alertas_ce, tem_bloqueios)
    """
    ce_cache = buscar_ce_cache(numero)
    if not ce_cache:
        ce_cache = _buscar_ce_no_kanban(processo_referencia, numero)

    if not ce_cache:
        return None, [], False

    ce_json = ce_cache.get("json_completo", {})
    if isinstance(ce_json, str):
        try:
            ce_json = json.loads(ce_json)
        except Exception:
            ce_json = {}
    if not isinstance(ce_json, dict):
        ce_json = {}

    duimp_numero_cache = ce_cache.get("duimp_numero")
    if not duimp_numero_cache:
        duimp_extraida = _extrair_duimp_do_documento_despacho(processo_referencia, numero, ce_json)
        if duimp_extraida:
            duimp_numero_cache = duimp_extraida
            _atualizar_duimp_numero_no_cache_ce(numero, duimp_extraida)

    pendencia_afrmm, pendencia_frete, pendencia_frete_detalhes = calcular_pendencias_ce(
        ce_json, numero, processo_referencia
    )

    ce_data: Dict[str, Any] = {
        "numero": numero,
        "tipo": ce_cache.get("tipo", ""),
        "situacao": ce_cache.get("situacao_carga", ""),
        "data_situacao": ce_cache.get("ultima_alteracao_api", ""),
        "carga_bloqueada": ce_cache.get("carga_bloqueada", False),
        "bloqueio_impede_despacho": ce_cache.get("bloqueio_impede_despacho", False),
        "ul_destino_final": ce_cache.get("ul_destino_final", ""),
        "pais_procedencia": ce_cache.get("pais_procedencia", ""),
        "porto_destino": ce_cache.get("porto_destino", ""),
        "porto_origem": ce_cache.get("porto_origem", ""),
        "cpf_cnpj_consignatario": ce_cache.get("cpf_cnpj_consignatario", ""),
        "atualizado_em": ce_cache.get("atualizado_em", ""),
        "di_numero": ce_cache.get("di_numero"),
        "duimp_numero": duimp_numero_cache,
        "pendencia_afrmm": pendencia_afrmm,
        "pendencia_frete": pendencia_frete,
        "pendencia_frete_detalhes": pendencia_frete_detalhes,
        "dados_completos": ce_json,
    }

    # Itens do CE
    try:
        itens_ce = buscar_ce_itens_cache(numero)
        if itens_ce and itens_ce.get("json_itens_completo"):
            ce_data["itens"] = itens_ce.get("json_itens_completo", {})
            itens_obj = ce_data.get("itens") if isinstance(ce_data.get("itens"), dict) else {}
            ce_data["itens_resumo"] = {
                "qtd_total_itens": itens_ce.get("qtd_total_itens", 0),
                "qtd_itens_recebidos": itens_ce.get("qtd_itens_recebidos", 0),
                "qtd_itens_restantes": itens_ce.get("qtd_itens_restantes", 0),
                "qtd_containers": len((itens_obj or {}).get("conteineres", []) or []),
                "qtd_cargas_soltas": len((itens_obj or {}).get("cargasSoltas", []) or []),
                "qtd_graneis": len((itens_obj or {}).get("graneis", []) or []),
            }
    except Exception as e:
        logger.debug(f"Erro ao buscar itens do CE {numero}: {e}")

    # Garantir boolean
    if ce_data["pendencia_frete"] not in (True, False):
        ce_data["pendencia_frete"] = bool(ce_data["pendencia_frete"]) if ce_data["pendencia_frete"] else False

    # Enriquecer via SQL Server (quando disponível)
    try:
        if processo_sql_server_data and processo_sql_server_data.get("ce"):
            ce_sql = processo_sql_server_data["ce"]
            if ce_sql.get("numero") == numero and isinstance(ce_json, dict):
                if ce_sql.get("valor_frete_total"):
                    ce_json["valorFreteTotal"] = ce_sql.get("valor_frete_total")
                    logger.info(
                        f"✅ Processo {processo_referencia}: CE {numero} enriquecido com valor_frete_total do SQL Server: "
                        f"{ce_sql.get('valor_frete_total')}"
                    )
    except Exception:
        pass

    # Se tem DI vinculada, enriquecer e garantir vínculo
    if ce_data.get("di_numero"):
        try:
            di_cache = buscar_di_cache(numero_di=ce_data["di_numero"])
            if di_cache:
                ce_data["di_dados"] = {
                    "numero_di": di_cache.get("numero_di", ""),
                    "numero_protocolo": di_cache.get("numero_protocolo", ""),
                    "canal_selecao_parametrizada": di_cache.get("canal_selecao_parametrizada", ""),
                    "data_hora_desembaraco": di_cache.get("data_hora_desembaraco"),
                    "data_hora_registro": di_cache.get("data_hora_registro"),
                    "situacao_di": di_cache.get("situacao_di", ""),
                    "situacao_entrega_carga": di_cache.get("situacao_entrega_carga", ""),
                    "data_hora_situacao_di": di_cache.get("data_hora_situacao_di"),
                }

                try:
                    processo_existente = obter_processo_por_documento("DI", ce_data["di_numero"])
                    if not processo_existente and processo_referencia:
                        vincular_documento_processo(processo_referencia, "DI", ce_data["di_numero"])
                        logger.info(
                            f"✅ DI {ce_data['di_numero']} vinculada ao processo {processo_referencia} (detectada no CE)"
                        )
                except Exception as e:
                    logger.warning(f"Erro ao vincular DI {ce_data['di_numero']} ao processo: {e}")
        except Exception as e:
            logger.warning(f"Erro ao buscar dados da DI {ce_data['di_numero']}: {e}")

    previsao = obter_previsao_atracacao_ce(numero, ce_json)
    if previsao:
        ce_data["previsao_atracacao"] = previsao

    alertas_ce: List[Dict[str, Any]] = []
    tem_bloqueios = False
    if ce_data.get("carga_bloqueada"):
        tem_bloqueios = True
        alertas_ce.append(
            {"tipo": "bloqueio", "nivel": "error", "documento": f"CE {numero}", "mensagem": "Carga bloqueada"}
        )
    if ce_data.get("bloqueio_impede_despacho"):
        tem_bloqueios = True
        alertas_ce.append(
            {
                "tipo": "bloqueio_despacho",
                "nivel": "error",
                "documento": f"CE {numero}",
                "mensagem": "Bloqueio impede vinculação de despacho",
            }
        )

    return ce_data, alertas_ce, tem_bloqueios

