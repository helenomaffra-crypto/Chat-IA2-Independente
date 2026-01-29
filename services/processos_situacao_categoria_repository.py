import logging
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


def listar_processos_por_categoria_e_situacao(
    categoria: str,
    situacao_filtro: Optional[str] = None,
    filtro_pendencias: Optional[bool] = None,
    filtro_bloqueio: Optional[bool] = None,
    limit: int = 200,
    *,
    listar_processos_por_categoria: Callable[..., List[str]],
    obter_dados_documentos_processo: Callable[..., Dict[str, Any]],
    buscar_di_cache: Callable[..., Optional[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Lista processos por categoria e filtra por situação de DI/DUIMP, pendências ou bloqueios.

    Implementação extraída do `db_manager.py` para reduzir monólito.
    """
    try:
        processos_refs = listar_processos_por_categoria(categoria, limit)

        if not processos_refs:
            return []

        # Limitar número de processos a processar para evitar lentidão
        max_processos_para_processar = 50
        if len(processos_refs) > max_processos_para_processar:
            logging.info(
                f"⚠️ Muitos processos {categoria} encontrados ({len(processos_refs)}). "
                f"Processando apenas os primeiros {max_processos_para_processar} para evitar lentidão."
            )
            processos_refs = processos_refs[:max_processos_para_processar]

        resultados: List[Dict[str, Any]] = []
        for processo_ref in processos_refs:
            try:
                processo_dto_kanban = None
                dados_docs: Optional[Dict[str, Any]] = None

                # Tentar via DTO do Kanban primeiro (cache sqlite/kanban), evitando SQL Server
                try:
                    from services.processo_repository import ProcessoRepository

                    repositorio = ProcessoRepository()
                    processo_dto_kanban = repositorio._buscar_sqlite(processo_ref)
                    if not processo_dto_kanban:
                        processo_dto_kanban = repositorio._buscar_api_kanban(processo_ref)

                    if processo_dto_kanban and processo_dto_kanban.fonte in ("kanban", "sqlite"):
                        dados_docs = {"ces": [], "dis": [], "duimps": [], "ccts": [], "shipsgo": {}}

                        # CE
                        if processo_dto_kanban.numero_ce:
                            dados_docs["ces"] = [
                                {
                                    "numero": processo_dto_kanban.numero_ce,
                                    "situacao": processo_dto_kanban.situacao_ce or "",
                                    "pendencia_frete": processo_dto_kanban.pendencia_frete or False,
                                }
                            ]

                        # DI
                        if processo_dto_kanban.numero_di:
                            di_dict: Dict[str, Any] = {
                                "numero_di": processo_dto_kanban.numero_di,
                                "situacao_di": processo_dto_kanban.situacao_di or "",
                                "situacao_entrega_carga": processo_dto_kanban.situacao_entrega or "",
                                "canal_selecao_parametrizada": "",
                                "data_hora_desembaraco": None,
                                "data_hora_registro": None,
                            }

                            # Prioridade 1: JSON completo do Kanban
                            try:
                                dados_json = processo_dto_kanban.dados_completos
                                if dados_json:
                                    import json

                                    if isinstance(dados_json, str):
                                        dados_json = json.loads(dados_json)

                                    if isinstance(dados_json, dict):
                                        di_dict["canal_selecao_parametrizada"] = dados_json.get("canal", "")
                                        di_dict["data_hora_desembaraco"] = dados_json.get("dataDesembaraco") or dados_json.get(
                                            "data_desembaraco"
                                        )
                                        di_dict["data_hora_registro"] = dados_json.get("dataRegistro") or dados_json.get(
                                            "data_registro"
                                        )
                            except Exception as e:
                                logging.debug(f"Erro ao extrair dados da DI do JSON do Kanban: {e}")

                            # Prioridade 2: cache de DI
                            if not di_dict["canal_selecao_parametrizada"] or not di_dict["data_hora_desembaraco"]:
                                di_cache = buscar_di_cache(numero_di=processo_dto_kanban.numero_di)
                                if di_cache:
                                    if not di_dict["canal_selecao_parametrizada"]:
                                        di_dict["canal_selecao_parametrizada"] = di_cache.get("canal_selecao_parametrizada", "")
                                    if not di_dict["data_hora_desembaraco"]:
                                        di_dict["data_hora_desembaraco"] = di_cache.get("data_hora_desembaraco")
                                    if not di_dict["data_hora_registro"]:
                                        di_dict["data_hora_registro"] = di_cache.get("data_hora_registro")

                                    # Fallback: tentar extrair do json_completo do cache
                                    if not di_dict["canal_selecao_parametrizada"] or not di_dict["data_hora_desembaraco"]:
                                        json_completo = di_cache.get("json_completo")
                                        if json_completo:
                                            import json

                                            if isinstance(json_completo, str):
                                                try:
                                                    json_completo = json.loads(json_completo)
                                                except Exception:
                                                    json_completo = {}

                                            if isinstance(json_completo, dict):
                                                dados_despacho = json_completo.get("dadosDespacho", {})
                                                if not di_dict["canal_selecao_parametrizada"]:
                                                    di_dict["canal_selecao_parametrizada"] = dados_despacho.get(
                                                        "canalSelecaoParametrizada", ""
                                                    )
                                                if not di_dict["data_hora_desembaraco"]:
                                                    di_dict["data_hora_desembaraco"] = dados_despacho.get("dataHoraDesembaraco")
                                                if not di_dict["data_hora_registro"]:
                                                    dados_gerais = json_completo.get("dadosGerais", {})
                                                    di_dict["data_hora_registro"] = dados_gerais.get("dataHoraRegistro")

                            # Prioridade 3: obter_dados_documentos_processo (cache apenas)
                            if not di_dict["canal_selecao_parametrizada"] or not di_dict["data_hora_desembaraco"]:
                                try:
                                    dados_docs_fallback = obter_dados_documentos_processo(processo_ref, usar_sql_server=False)
                                    if dados_docs_fallback and dados_docs_fallback.get("dis"):
                                        di_fallback = dados_docs_fallback["dis"][0]
                                        if di_fallback:
                                            if not di_dict["canal_selecao_parametrizada"]:
                                                di_dict["canal_selecao_parametrizada"] = di_fallback.get(
                                                    "canal_selecao_parametrizada", ""
                                                )
                                            if not di_dict["data_hora_desembaraco"]:
                                                di_dict["data_hora_desembaraco"] = di_fallback.get("data_hora_desembaraco")
                                            if not di_dict["data_hora_registro"]:
                                                di_dict["data_hora_registro"] = di_fallback.get("data_hora_registro")
                                except Exception as e:
                                    logging.debug(
                                        f"Erro ao buscar dados completos da DI via obter_dados_documentos_processo: {e}"
                                    )

                            dados_docs["dis"] = [di_dict]

                        # DUIMP
                        if processo_dto_kanban.numero_duimp:
                            dados_docs["duimps"] = [
                                {"numero_duimp": processo_dto_kanban.numero_duimp, "situacao_duimp": "", "ambiente": "producao"}
                            ]

                        logging.debug(
                            f"✅ Dados do Kanban encontrados para {processo_ref}: "
                            f"CE={bool(processo_dto_kanban.numero_ce)}, DI={bool(processo_dto_kanban.numero_di)}, "
                            f"DUIMP={bool(processo_dto_kanban.numero_duimp)}"
                        )
                except Exception as e:
                    logging.debug(f"⚠️ Erro ao buscar dados do Kanban para {processo_ref}: {e}")

                if not processo_dto_kanban or processo_dto_kanban.fonte not in ("kanban", "sqlite"):
                    dados_docs = obter_dados_documentos_processo(processo_ref, usar_sql_server=False)
                elif not dados_docs or (not dados_docs.get("ces") and not dados_docs.get("dis") and not dados_docs.get("duimps")):
                    if not dados_docs:
                        dados_docs = {"ces": [], "dis": [], "duimps": [], "ccts": [], "shipsgo": {}}

                    dados_docs_antigo = obter_dados_documentos_processo(processo_ref, usar_sql_server=False)
                    if dados_docs_antigo:
                        if dados_docs_antigo.get("ces"):
                            dados_docs["ces"] = dados_docs_antigo.get("ces", [])
                        if dados_docs_antigo.get("dis"):
                            dados_docs["dis"] = dados_docs_antigo.get("dis", [])
                        if dados_docs_antigo.get("duimps"):
                            dados_docs["duimps"] = dados_docs_antigo.get("duimps", [])
                        if dados_docs_antigo.get("ccts"):
                            dados_docs["ccts"] = dados_docs_antigo.get("ccts", [])
                        if dados_docs_antigo.get("shipsgo"):
                            dados_docs["shipsgo"] = dados_docs_antigo.get("shipsgo", {})

                processo_info: Dict[str, Any] = {"processo_referencia": processo_ref}

                # DI
                dis = (dados_docs or {}).get("dis", [])
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
                duimps = (dados_docs or {}).get("duimps", [])
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
                ces = (dados_docs or {}).get("ces", [])
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

                    logging.info(
                        f"🔍 listar_processos_por_categoria_e_situacao: Processo {processo_ref} CE {ce.get('numero','N/A')} - "
                        f"pendencia_frete_raw={pendencia_frete_raw} (tipo: {type(pendencia_frete_raw).__name__}) → "
                        f"pendencia_frete_final={pendencia_frete_final} (tipo: {type(pendencia_frete_final).__name__})"
                    )

                    processo_info["ce"] = {
                        "numero": ce.get("numero", ""),
                        "situacao": ce.get("situacao", ""),
                        "pendencia_frete": pendencia_frete_final,
                        "pendencia_afrmm": ce.get("pendencia_afrmm", False),
                        "carga_bloqueada": ce.get("carga_bloqueada", False),
                        "bloqueio_impede_despacho": ce.get("bloqueio_impede_despacho", False),
                    }

                # CCT
                ccts = (dados_docs or {}).get("ccts", [])
                if ccts:
                    cct = ccts[0]
                    processo_info["cct"] = {
                        "numero": cct.get("numero", ""),
                        "situacao": cct.get("situacao_atual", ""),
                        "pendencia_frete": cct.get("pendencia_frete", False),
                        "tem_bloqueios": cct.get("tem_bloqueios", False),
                    }

                # ShipsGo
                shipsgo = (dados_docs or {}).get("shipsgo")
                if shipsgo:
                    processo_info["shipsgo"] = shipsgo

                # Filtro de situação
                if situacao_filtro:
                    situacao_filtro_lower = situacao_filtro.lower().strip()
                    import unicodedata

                    def remover_acentos(texto: str) -> str:
                        if not texto:
                            return texto
                        nfd = unicodedata.normalize("NFD", texto)
                        return "".join(char for char in nfd if unicodedata.category(char) != "Mn")

                    situacao_filtro_normalizada = remover_acentos(situacao_filtro_lower)
                    situacao_di = processo_info.get("di", {}).get("situacao", "").lower()
                    situacao_duimp = processo_info.get("duimp", {}).get("situacao", "").lower()
                    situacao_di_normalizada = remover_acentos(situacao_di)
                    situacao_duimp_normalizada = remover_acentos(situacao_duimp)
                    situacao_ce = processo_info.get("ce", {}).get("situacao", "").lower()
                    situacao_ce_normalizada = remover_acentos(situacao_ce)

                    corresponde = False
                    if "desembarac" in situacao_filtro_normalizada:
                        corresponde = "desembarac" in situacao_di_normalizada or "desembarac" in situacao_duimp_normalizada
                    elif "registrad" in situacao_filtro_normalizada:
                        corresponde = "registrad" in situacao_duimp_normalizada
                    elif "entreg" in situacao_filtro_normalizada:
                        corresponde = situacao_ce_normalizada == "entregue" or "entreg" in situacao_duimp_normalizada
                    elif "armazen" in situacao_filtro_normalizada:
                        corresponde = (
                            "armazen" in situacao_ce_normalizada
                            or situacao_ce_normalizada == "armazenada"
                            or situacao_ce.upper() == "ARMAZENADA"
                        )
                    elif "manifest" in situacao_filtro_normalizada:
                        corresponde = (
                            "manifest" in situacao_ce_normalizada
                            or situacao_ce_normalizada == "manifestada"
                            or situacao_ce.upper() == "MANIFESTADA"
                        )
                    else:
                        corresponde = (
                            situacao_filtro_normalizada in situacao_di_normalizada
                            or situacao_filtro_normalizada in situacao_duimp_normalizada
                            or situacao_filtro_normalizada in situacao_ce_normalizada
                        )

                    if not corresponde:
                        continue

                # Filtro pendências (não inclui bloqueios)
                if filtro_pendencias is True:
                    tem_pendencia = False

                    ce_info = processo_info.get("ce", {})
                    if ce_info:
                        pendencia_frete_ce = ce_info.get("pendencia_frete", False)
                        logging.info(
                            f"🔍 Filtro pendências: Processo {processo_ref} CE {ce_info.get('numero','N/A')} - "
                            f"pendencia_frete_ce={pendencia_frete_ce} (tipo: {type(pendencia_frete_ce).__name__})"
                        )

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

                        logging.info(
                            f"🔍 Verificação pendência frete: is_true={is_true} para pendencia_frete_ce={pendencia_frete_ce} "
                            f"(tipo: {type(pendencia_frete_ce).__name__})"
                        )
                        if is_true:
                            tem_pendencia = True
                            logging.info(
                                f"✅ Processo {processo_ref}: Pendência de frete detectada no CE {ce_info.get('numero','N/A')} "
                                f"(valor: {pendencia_frete_ce}, tipo: {type(pendencia_frete_ce).__name__})"
                            )

                        pendencia_afrmm_ce = ce_info.get("pendencia_afrmm", False)
                        logging.info(
                            f"🔍 Pendência AFRMM: Processo {processo_ref} CE {ce_info.get('numero','N/A')} - "
                            f"pendencia_afrmm_ce={pendencia_afrmm_ce} (tipo: {type(pendencia_afrmm_ce).__name__})"
                        )
                        if pendencia_afrmm_ce is True or pendencia_afrmm_ce == 1 or (
                            isinstance(pendencia_afrmm_ce, str) and pendencia_afrmm_ce.lower() == "true"
                        ):
                            tem_pendencia = True
                            logging.info(
                                f"✅ Processo {processo_ref}: Pendência de AFRMM detectada no CE {ce_info.get('numero','N/A')}"
                            )

                    cct_info = processo_info.get("cct", {})
                    if cct_info:
                        pendencia_frete_cct = cct_info.get("pendencia_frete", False)
                        if pendencia_frete_cct is True or pendencia_frete_cct == 1 or (
                            isinstance(pendencia_frete_cct, str) and pendencia_frete_cct.lower() == "true"
                        ):
                            tem_pendencia = True

                    if not tem_pendencia:
                        logging.info(f"⚠️ Processo {processo_ref}: Sem pendências detectadas (filtrado)")
                        continue
                    logging.info(f"✅ Processo {processo_ref}: Pendências detectadas - incluindo no resultado")

                # Filtro bloqueios (não inclui pendências)
                if filtro_bloqueio:
                    tem_bloqueio = False

                    ce_info = processo_info.get("ce", {})
                    if ce_info:
                        carga_bloqueada = ce_info.get("carga_bloqueada", False)
                        bloqueio_impede_despacho = ce_info.get("bloqueio_impede_despacho", False)
                        logging.info(
                            f"🔍 Filtro bloqueios: Processo {processo_ref} CE {ce_info.get('numero','N/A')} - "
                            f"carga_bloqueada={carga_bloqueada}, bloqueio_impede_despacho={bloqueio_impede_despacho}"
                        )
                        if (
                            carga_bloqueada is True
                            or carga_bloqueada == 1
                            or bloqueio_impede_despacho is True
                            or bloqueio_impede_despacho == 1
                        ):
                            tem_bloqueio = True
                            logging.info(f"✅ Processo {processo_ref}: Bloqueio detectado no CE {ce_info.get('numero','N/A')}")

                    cct_info = processo_info.get("cct", {})
                    if cct_info:
                        tem_bloqueios = cct_info.get("tem_bloqueios", False)
                        if tem_bloqueios is True or tem_bloqueios == 1 or (
                            isinstance(tem_bloqueios, str) and str(tem_bloqueios).lower() == "true"
                        ):
                            tem_bloqueio = True

                    if not tem_bloqueio:
                        logging.info(f"⚠️ Processo {processo_ref}: Sem bloqueios detectados (filtrado)")
                        continue
                    logging.info(f"✅ Processo {processo_ref}: Bloqueios detectados - incluindo no resultado")

                resultados.append(processo_info)
            except Exception as e:
                logging.warning(f"Erro ao processar processo {processo_ref} na listagem por categoria: {e}")
                continue

        return resultados
    except Exception as e:
        logging.error(f"Erro ao listar processos por categoria e situação {categoria}/{situacao_filtro}: {e}")
        return []

