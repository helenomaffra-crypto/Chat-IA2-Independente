import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def carregar_documentos_base(
    processo_referencia: str,
    *,
    listar_documentos_processo: Callable[[str], List[Dict[str, Any]]],
    usar_sql_server: bool,
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Carrega lista base de documentos do processo.

    - Primeiro via `listar_documentos_processo` (SQLite)
    - Se vazio e `usar_sql_server=True`, faz fallback no SQL Server (quando disponível) e converte para lista de documentos

    Returns:
        (documentos, processo_sql_server_data)
    """
    documentos = listar_documentos_processo(processo_referencia)

    processo_sql_server_data: Optional[Dict[str, Any]] = None
    if (not documentos or len(documentos) == 0) and usar_sql_server:
        logger.info(
            f"⚠️ Processo {processo_referencia}: Nenhum documento encontrado no cache. Buscando do SQL Server..."
        )
        try:
            from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server

            processo_sql_server = buscar_processo_consolidado_sql_server(processo_referencia)
            if processo_sql_server:
                logger.info(
                    f"✅ Processo {processo_referencia}: Dados encontrados no SQL Server. Convertendo para formato de documentos..."
                )
                if processo_sql_server.get("ce"):
                    ce_sql = processo_sql_server["ce"]
                    documentos.append({"tipo_documento": "CE", "numero_documento": ce_sql.get("numero", "")})
                if processo_sql_server.get("di"):
                    di_sql = processo_sql_server["di"]
                    documentos.append({"tipo_documento": "DI", "numero_documento": di_sql.get("numero", "")})
                if processo_sql_server.get("duimp"):
                    duimp_sql = processo_sql_server["duimp"]
                    documentos.append({"tipo_documento": "DUIMP", "numero_documento": duimp_sql.get("numero", "")})
                if processo_sql_server.get("cct"):
                    cct_sql = processo_sql_server["cct"]
                    documentos.append({"tipo_documento": "CCT", "numero_documento": cct_sql.get("numero", "")})

                processo_sql_server_data = processo_sql_server
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar processo do SQL Server: {e}")

    return documentos, processo_sql_server_data


def ordenar_documentos_e_identificar_di_prioritaria(
    processo_referencia: str,
    documentos: List[Dict[str, Any]],
    *,
    buscar_ce_cache: Callable[[str], Optional[Dict[str, Any]]],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Ordena documentos colocando CEs primeiro e identifica a DI prioritária (a DI que está no documentoDespacho do CE).
    """
    documentos_ces = [d for d in documentos if d.get("tipo_documento") == "CE"]
    documentos_outros = [d for d in documentos if d.get("tipo_documento") != "CE"]
    documentos_ordenados = documentos_ces + documentos_outros

    di_prioritaria_do_ce: Optional[str] = None
    for doc_ce in documentos_ces:
        ce_cache_temp = buscar_ce_cache(doc_ce.get("numero_documento", ""))
        if ce_cache_temp:
            di_numero_ce = ce_cache_temp.get("di_numero")
            if di_numero_ce:
                di_prioritaria_do_ce = di_numero_ce
                logger.debug(
                    f"✅ Processo {processo_referencia}: DI prioritária identificada: {di_prioritaria_do_ce} "
                    f"(vinda do CE {doc_ce.get('numero_documento')})"
                )
                break

    return documentos_ordenados, di_prioritaria_do_ce

