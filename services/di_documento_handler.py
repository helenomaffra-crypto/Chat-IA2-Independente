import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


def _montar_di_data_de_sql(numero_requisitado: str, di_sql: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "numero": di_sql.get("numero", numero_requisitado),
        "tipo": "DI",
        "numero_di": di_sql.get("numero", ""),
        "numero_protocolo": None,
        "numero_identificacao": None,
        "canal_selecao_parametrizada": di_sql.get("canal", ""),
        "data_hora_desembaraco": di_sql.get("data_desembaraco"),
        "data_hora_registro": di_sql.get("data_registro"),
        "situacao_di": di_sql.get("situacao", ""),
        "situacao_entrega_carga": di_sql.get("situacao_entrega", ""),
        "data_hora_situacao_di": di_sql.get("data_situacao"),
        "atualizado_em": di_sql.get("updated_at_di_gerais"),
        "dados_completos": {
            "valor_mercadoria_descarga_dolar": di_sql.get("valor_mercadoria_descarga_dolar"),
            "valor_mercadoria_descarga_real": di_sql.get("valor_mercadoria_descarga_real"),
            "valor_mercadoria_embarque_dolar": di_sql.get("valor_mercadoria_embarque_dolar"),
            "valor_mercadoria_embarque_real": di_sql.get("valor_mercadoria_embarque_real"),
            "tipo_recolhimento_icms": di_sql.get("tipo_recolhimento_icms"),
            "data_pagamento_icms": di_sql.get("data_pagamento_icms"),
            "nome_adquirente": di_sql.get("nome_adquirente"),
            "nome_importador": di_sql.get("nome_importador"),
            "pagamentos": di_sql.get("pagamentos", []),
            "frete": di_sql.get("frete"),
            "transporte": di_sql.get("transporte"),
            "numero_ce": di_sql.get("numero_ce"),
            "ce_relacionado": di_sql.get("ce_relacionado"),
        },
    }


def processar_documento_di(
    processo_referencia: str,
    numero: str,
    *,
    buscar_di_cache: Callable[..., Optional[Dict[str, Any]]],
    usar_sql_server: bool,
    processo_sql_server_data: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Processa um documento DI, tentando:
    - cache (dis_cache)
    - SQL Server (via payload já carregado em processo_sql_server_data)
    - SQL Server via id_importacao (quando usar_sql_server=True)

    Returns:
        di_data ou None
    """
    di_cache = buscar_di_cache(numero_di=numero)

    # 1) SQL Server (quando já veio no pacote do processo)
    if not di_cache and processo_sql_server_data and processo_sql_server_data.get("di"):
        di_sql = processo_sql_server_data["di"]
        numero_normalizado = numero.replace("/", "").replace("-", "") if numero else ""
        if di_sql.get("numero") == numero or (numero_normalizado and di_sql.get("numero") == numero_normalizado):
            logger.info(f"✅ Processo {processo_referencia}: DI {numero} encontrada no SQL Server (com valores/impostos)")
            return _montar_di_data_de_sql(numero, di_sql)

    # 2) SQL Server via id_importacao (MAPEAMENTO_SQL_SERVER.md)
    if not di_cache and usar_sql_server:
        logger.info(
            f"⚠️ Processo {processo_referencia}: DI {numero} não encontrada no cache. Buscando via id_importacao do SQL Server..."
        )
        try:
            from utils.sql_server_adapter import get_sql_adapter
            from services.sql_server_processo_schema import _buscar_di_completo, _buscar_di_por_id_processo

            from services.db_policy_service import (
                get_primary_database,
                get_legacy_database,
                log_legacy_fallback,
                should_use_legacy_database
            )
            
            sql_adapter = get_sql_adapter()
            if sql_adapter:
                # ✅ POLÍTICA CENTRAL: Tentar primário primeiro
                processo_ref_escaped = processo_referencia.replace("'", "''")
                database_para_usar = get_primary_database()
                
                query_id = f"""
                    SELECT TOP 1 id_importacao, id_processo_importacao
                    FROM {database_para_usar}.dbo.PROCESSO_IMPORTACAO
                    WHERE numero_processo = '{processo_ref_escaped}'
                """
                result_id = sql_adapter.execute_query(query_id, database_para_usar, None, notificar_erro=False)
                
                # Se não encontrou no primário e fallback está permitido, tentar Make
                if (not result_id.get("success") or not result_id.get("data") or len(result_id["data"]) == 0):
                    if should_use_legacy_database(processo_referencia):
                        log_legacy_fallback(
                            processo_referencia=processo_referencia,
                            tool_name='processar_documento_di',
                            caller_function='di_documento_handler.processar_documento_di',
                            reason="Processo não encontrado no banco primário para buscar id_importacao",
                            query=query_id
                        )
                        database_para_usar = get_legacy_database()
                        query_id_legacy = f"""
                            SELECT TOP 1 id_importacao, id_processo_importacao
                            FROM {database_para_usar}.dbo.PROCESSO_IMPORTACAO
                            WHERE numero_processo = '{processo_ref_escaped}'
                        """
                        result_id = sql_adapter.execute_query(query_id_legacy, database_para_usar, None, notificar_erro=False)
                if result_id.get("success") and result_id.get("data") and len(result_id["data"]) > 0:
                    row_id = result_id["data"][0]
                    id_importacao = row_id.get("id_importacao")
                    id_processo_importacao = row_id.get("id_processo_importacao")

                    if id_importacao:
                        logger.info(f"✅ Processo {processo_referencia}: id_importacao={id_importacao}, buscando DI via Hi_Historico_Di...")
                        numero_di_normalizado = numero.replace("/", "").replace("-", "") if numero else None
                        di_sql2 = _buscar_di_completo(sql_adapter, numero, id_importacao)
                        if not di_sql2 and numero_di_normalizado and numero_di_normalizado != numero:
                            di_sql2 = _buscar_di_completo(sql_adapter, numero_di_normalizado, id_importacao)
                        if not di_sql2 and id_processo_importacao:
                            di_sql2 = _buscar_di_por_id_processo(sql_adapter, id_processo_importacao, id_importacao)

                        if di_sql2 and di_sql2.get("numero"):
                            logger.info(
                                f"✅ Processo {processo_referencia}: DI {di_sql2.get('numero')} encontrada via id_importacao (com valores/impostos)"
                            )
                            return _montar_di_data_de_sql(numero, di_sql2)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar DI via id_importacao: {e}")

    # 3) Cache (com enriquecimento do SQL Server quando disponível)
    if di_cache:
        di_json = di_cache.get("json_completo", {})
        di_data = {
            "numero": numero,
            "tipo": "DI",
            "numero_di": di_cache.get("numero_di", ""),
            "numero_protocolo": di_cache.get("numero_protocolo", ""),
            "numero_identificacao": di_cache.get("numero_identificacao", ""),
            "canal_selecao_parametrizada": di_cache.get("canal_selecao_parametrizada", ""),
            "data_hora_desembaraco": di_cache.get("data_hora_desembaraco"),
            "data_hora_registro": di_cache.get("data_hora_registro"),
            "situacao_di": di_cache.get("situacao_di", ""),
            "situacao_entrega_carga": di_cache.get("situacao_entrega_carga", ""),
            "data_hora_situacao_di": di_cache.get("data_hora_situacao_di"),
            "atualizado_em": di_cache.get("atualizado_em", ""),
            "dados_completos": di_json,
        }

        if processo_sql_server_data and processo_sql_server_data.get("di"):
            di_sql = processo_sql_server_data["di"]
            numero_normalizado = numero.replace("/", "").replace("-", "") if numero else ""
            if di_sql.get("numero") == numero or (numero_normalizado and di_sql.get("numero") == numero_normalizado):
                if isinstance(di_json, dict):
                    di_json["valor_mercadoria_descarga_dolar"] = di_sql.get("valor_mercadoria_descarga_dolar")
                    di_json["valor_mercadoria_descarga_real"] = di_sql.get("valor_mercadoria_descarga_real")
                    di_json["valor_mercadoria_embarque_dolar"] = di_sql.get("valor_mercadoria_embarque_dolar")
                    di_json["valor_mercadoria_embarque_real"] = di_sql.get("valor_mercadoria_embarque_real")
                    di_json["tipo_recolhimento_icms"] = di_sql.get("tipo_recolhimento_icms")
                    di_json["data_pagamento_icms"] = di_sql.get("data_pagamento_icms")
                    di_json["nome_importador"] = di_sql.get("nome_importador")
                    if di_sql.get("pagamentos"):
                        di_json["pagamentos"] = di_sql.get("pagamentos")
                        try:
                            logger.info(
                                f"✅ Processo {processo_referencia}: DI {numero} enriquecida com "
                                f"{len(di_sql.get('pagamentos', []))} pagamento(s) do SQL Server"
                            )
                        except Exception:
                            pass
                    if di_sql.get("frete"):
                        di_json["frete"] = di_sql.get("frete")
                    logger.info(f"✅ Processo {processo_referencia}: DI {numero} enriquecida com valores, impostos e frete do SQL Server")

        try:
            from utils.siscomex_di_publica import consultar_data_ultima_atualizacao_di

            if numero:
                resultado_publica = consultar_data_ultima_atualizacao_di([numero])
                data_publica = resultado_publica.get(numero)
                if data_publica:
                    di_data["data_ultima_atualizacao_publica"] = data_publica.isoformat()
        except Exception as e:
            logger.debug(f"Erro ao consultar API pública para DI {numero}: {e}")

        return di_data

    return None

