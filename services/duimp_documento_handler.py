import json
import logging
import sqlite3
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)


def _coletar_duimps_do_ce(processo_referencia: str, ces: List[Dict[str, Any]]) -> Set[str]:
    duimp_numeros_do_ce: Set[str] = set()
    for ce in ces:
        duimp_numero_ce = ce.get("duimp_numero")
        if duimp_numero_ce:
            duimp_numeros_do_ce.add(str(duimp_numero_ce))
            logger.info(
                f"✅ Processo {processo_referencia}: DUIMP de PRODUÇÃO {duimp_numero_ce} encontrada no documentoDespacho do CE {ce.get('numero', 'N/A')}"
            )
        else:
            logger.debug(
                f"⚠️ Processo {processo_referencia}: CE {ce.get('numero', 'N/A')} não tem DUIMP no documentoDespacho"
            )
    return duimp_numeros_do_ce


def _tentar_duimp_producao_do_kanban(
    processo_referencia: str, get_db_connection: Callable[[], Any]
) -> Optional[str]:
    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT numero_duimp, documento_despacho, numero_documento_despacho
            FROM processos_kanban
            WHERE processo_referencia = ?
            LIMIT 1
            """,
            (processo_referencia,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None

        num_duimp_pk = row["numero_duimp"]
        doc_desp = (row["documento_despacho"] or "").strip().upper()
        num_doc_desp = row["numero_documento_despacho"]
        if num_duimp_pk and (doc_desp == "DUIMP" or num_doc_desp == num_duimp_pk):
            logger.info(
                f"✅ Processo {processo_referencia}: DUIMP de PRODUÇÃO {num_duimp_pk} encontrada no Kanban (processos_kanban)."
            )
            return str(num_duimp_pk)
    except Exception as e:
        logger.debug(f"⚠️ Erro ao buscar DUIMP no Kanban para {processo_referencia}: {e}")
    return None


def _coletar_duimps_validacao_vinculadas(
    processo_referencia: str, get_db_connection: Callable[[], Any]
) -> Set[str]:
    numeros: Set[str] = set()
    if not processo_referencia:
        return numeros

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT numero
        FROM duimps
        WHERE processo_referencia = ? AND ambiente = 'validacao'
        """,
        (processo_referencia,),
    )
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        numero = row["numero"]
        if numero:
            numeros.add(str(numero))
            logger.info(f"📋 Processo {processo_referencia}: DUIMP de VALIDAÇÃO {numero} encontrada vinculada ao processo")
    return numeros


def _buscar_rows_duimps_por_numeros(
    duimp_numeros_para_buscar: Iterable[str], get_db_connection: Callable[[], Any]
) -> List[Any]:
    numeros = list(duimp_numeros_para_buscar)
    if not numeros:
        return []

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(numeros))
    cursor.execute(
        f"""
        SELECT numero, versao, payload_completo, ambiente, atualizado_em, processo_referencia
        FROM duimps
        WHERE numero IN ({placeholders})
        ORDER BY CAST(versao AS INTEGER) DESC, atualizado_em DESC
        """,
        tuple(numeros),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def _montar_duimp_data_basico_producao(duimp_numero: str) -> Dict[str, Any]:
    return {
        "numero": duimp_numero,
        "tipo": "DUIMP",
        "numero_duimp": duimp_numero,
        "versao_duimp": "0",
        "situacao_duimp": "",
        "controle_carga": "",
        "canal_consolidado": "",
        "data_registro": None,
        "ambiente": "producao",
        "atualizado_em": None,
        "dados_completos": {},
        "vinda_do_ce": True,
        "nao_consultada_ainda": True,
    }


def _montar_duimp_data_de_row(
    processo_referencia: str,
    row_duimp: Any,
    *,
    ambiente_duimp: str,
    duimp_numeros_do_ce: Set[str],
) -> Optional[Dict[str, Any]]:
    duimp_numero = row_duimp["numero"]
    duimp_versao = row_duimp["versao"]
    versao_int = int(duimp_versao) if str(duimp_versao).isdigit() else 0

    payload_completo = json.loads(row_duimp["payload_completo"]) if row_duimp["payload_completo"] else {}
    if isinstance(payload_completo, dict) and payload_completo.get("code") == "PUCX-ER0014":
        logger.warning(
            f"⚠️ DUIMP {duimp_numero} v{duimp_versao} tem payload de erro (parada programada). Ignorando esta versão."
        )
        return None

    identificacao = payload_completo.get("identificacao", {}) if isinstance(payload_completo, dict) else {}
    situacao = payload_completo.get("situacao", {}) if isinstance(payload_completo, dict) else {}
    resultado_analise_risco = payload_completo.get("resultadoAnaliseRisco", {}) if isinstance(payload_completo, dict) else {}

    situacao_duimp = situacao.get("situacaoDuimp", "") if isinstance(situacao, dict) else ""
    if versao_int >= 1 and not situacao_duimp:
        logger.warning(
            f"⚠️ DUIMP {duimp_numero} v{duimp_versao} é versão {versao_int} mas não tem situação. Isso pode indicar problema na consulta."
        )

    duimp_data: Dict[str, Any] = {
        "numero": f"{duimp_numero} v{duimp_versao}",
        "tipo": "DUIMP",
        "numero_duimp": duimp_numero,
        "versao_duimp": duimp_versao,
        "situacao_duimp": situacao_duimp,
        "controle_carga": situacao.get("controleCarga", "") if isinstance(situacao, dict) else "",
        "canal_consolidado": resultado_analise_risco.get("canalConsolidado", "") if isinstance(resultado_analise_risco, dict) else "",
        "data_registro": identificacao.get("dataRegistro") if isinstance(identificacao, dict) else None,
        "ambiente": ambiente_duimp,
        "atualizado_em": row_duimp["atualizado_em"],
        "dados_completos": payload_completo,
        "vinda_do_ce": (str(duimp_numero) in duimp_numeros_do_ce),
    }

    ambiente_info = "PRODUÇÃO" if ambiente_duimp == "producao" else "VALIDAÇÃO (teste)"
    logger.info(
        f"✅ DUIMP {duimp_numero} v{duimp_versao} encontrada ({ambiente_info}, situação: {situacao_duimp or 'N/A'})"
    )
    return duimp_data


def _buscar_duimp_validacao_direto(
    duimp_numero_validacao: str, get_db_connection: Callable[[], Any]
) -> Optional[Any]:
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT numero, versao, payload_completo, ambiente, atualizado_em, processo_referencia
        FROM duimps
        WHERE numero = ? AND ambiente = 'validacao'
        ORDER BY CAST(versao AS INTEGER) DESC, atualizado_em DESC
        LIMIT 1
        """,
        (duimp_numero_validacao,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def buscar_duimps_vinculadas_ao_processo(
    processo_referencia: str,
    ces: List[Dict[str, Any]],
    *,
    get_db_connection: Callable[[], Any],
) -> List[Dict[str, Any]]:
    """
    Busca DUIMPs vinculadas ao processo, incluindo:
    - DUIMPs de PRODUÇÃO (vindas do documentoDespacho do CE, ou fallback Kanban quando aplicável)
    - DUIMPs de VALIDAÇÃO (ambiente='validacao' vinculadas via processo_referencia)
    """
    # 1) Coletar DUIMPs vindas do CE (produção)
    duimp_numeros_do_ce = _coletar_duimps_do_ce(processo_referencia, ces)

    # 1.b) fallback Kanban quando não há DUIMP no CE/cache
    if not duimp_numeros_do_ce and processo_referencia:
        duimp_pk = _tentar_duimp_producao_do_kanban(processo_referencia, get_db_connection)
        if duimp_pk:
            duimp_numeros_do_ce.add(duimp_pk)

    # 2) adicionar também validação vinculada
    duimp_numeros_para_buscar: Set[str] = set(duimp_numeros_do_ce)
    duimp_numeros_para_buscar.update(_coletar_duimps_validacao_vinculadas(processo_referencia, get_db_connection))

    if not duimp_numeros_para_buscar:
        logger.debug(f"⚠️ Processo {processo_referencia}: Nenhuma DUIMP encontrada (nem produção nem validação).")
        return []

    logger.info(
        f"📋 Processo {processo_referencia}: {len(duimp_numeros_do_ce)} DUIMP(s) de produção encontrada(s) no CE: "
        f"{', '.join(sorted(duimp_numeros_do_ce)) if duimp_numeros_do_ce else '(nenhuma)'}"
    )
    if len(duimp_numeros_para_buscar) > len(duimp_numeros_do_ce):
        duimp_numeros_validacao = duimp_numeros_para_buscar - duimp_numeros_do_ce
        logger.info(
            f"📋 Processo {processo_referencia}: {len(duimp_numeros_validacao)} DUIMP(s) de validação encontrada(s): "
            f"{', '.join(sorted(duimp_numeros_validacao)) if duimp_numeros_validacao else '(nenhuma)'}"
        )

    # 3) buscar por número (não filtrar por processo_referencia, pois produção pode não ter vinculação na tabela)
    rows_duimp = _buscar_rows_duimps_por_numeros(duimp_numeros_para_buscar, get_db_connection)

    duimps_encontradas: Dict[str, Dict[str, Any]] = {}
    versoes_processadas: Dict[str, int] = {}

    for row_duimp in rows_duimp:
        try:
            duimp_numero = str(row_duimp["numero"])
            duimp_versao = str(row_duimp["versao"])
            versao_int = int(duimp_versao) if duimp_versao.isdigit() else 0

            ambiente_duimp = row_duimp["ambiente"] or "validacao"
            if duimp_numero in duimp_numeros_do_ce:
                ambiente_duimp = "producao"
                logger.debug(f"✅ DUIMP {duimp_numero} confirmada como PRODUÇÃO (vinda do CE)")
            else:
                ambiente_duimp = "validacao"
                logger.debug(f"📋 DUIMP {duimp_numero} identificada como VALIDAÇÃO (teste)")

            if duimp_numero in versoes_processadas:
                versao_ja = versoes_processadas[duimp_numero]
                if versao_int < versao_ja:
                    logger.debug(
                        f"⚠️ DUIMP {duimp_numero} v{duimp_versao} ignorada (já temos versão {versao_ja} que é maior)"
                    )
                    continue
                if versao_int > versao_ja:
                    logger.info(f"✅ DUIMP {duimp_numero}: Substituindo versão {versao_ja} por versão {versao_int} (maior)")
                    if duimp_numero in duimps_encontradas:
                        del duimps_encontradas[duimp_numero]

            duimp_data = _montar_duimp_data_de_row(
                processo_referencia,
                row_duimp,
                ambiente_duimp=ambiente_duimp,
                duimp_numeros_do_ce=duimp_numeros_do_ce,
            )
            if not duimp_data:
                continue

            duimps_encontradas[duimp_numero] = duimp_data
            versoes_processadas[duimp_numero] = versao_int
        except Exception as e:
            try:
                logger.warning(f"Erro ao processar DUIMP {row_duimp.get('numero', 'N/A')}: {e}")
            except Exception:
                logger.warning(f"Erro ao processar DUIMP: {e}")

    # 4) Incluir DUIMPs vindas do CE mesmo sem registro local na tabela duimps
    for duimp_numero_ce in duimp_numeros_do_ce:
        if duimp_numero_ce not in duimps_encontradas:
            logger.info(
                f"📋 Processo {processo_referencia}: DUIMP de PRODUÇÃO {duimp_numero_ce} encontrada no CE mas não na tabela duimps. "
                f"Criando estrutura básica (será consultada automaticamente)."
            )
            duimps_encontradas[duimp_numero_ce] = _montar_duimp_data_basico_producao(duimp_numero_ce)
        else:
            logger.debug(
                f"✅ Processo {processo_referencia}: DUIMP {duimp_numero_ce} já encontrada na tabela duimps (com dados completos)"
            )

    # 5) Garantir inclusão de DUIMPs de validação vinculadas, mesmo se a busca inicial não retornou
    duimp_numeros_validacao = duimp_numeros_para_buscar - duimp_numeros_do_ce
    for duimp_numero_validacao in duimp_numeros_validacao:
        if duimp_numero_validacao in duimps_encontradas:
            continue

        logger.debug(
            f"📋 Processo {processo_referencia}: DUIMP de VALIDAÇÃO {duimp_numero_validacao} vinculada mas não encontrada na busca. Buscando diretamente..."
        )
        try:
            row_validacao = _buscar_duimp_validacao_direto(duimp_numero_validacao, get_db_connection)
            if not row_validacao:
                continue
            duimp_data = _montar_duimp_data_de_row(
                processo_referencia,
                row_validacao,
                ambiente_duimp="validacao",
                duimp_numeros_do_ce=duimp_numeros_do_ce,
            )
            if duimp_data:
                duimp_data["vinda_do_ce"] = False
                duimps_encontradas[str(row_validacao["numero"])] = duimp_data
                logger.info(
                    f"📋 DUIMP {row_validacao['numero']} v{row_validacao['versao']} de VALIDAÇÃO (teste) encontrada e incluída no monitoramento"
                )
        except Exception as e:
            logger.debug(f"Erro ao buscar DUIMP de validação {duimp_numero_validacao}: {e}")

    return list(duimps_encontradas.values())

