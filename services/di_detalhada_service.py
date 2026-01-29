"""
Service opcional para acesso a dados detalhados de DI via SQL Server.

Objetivo:
- Fornecer um ponto único para enriquecer respostas de DI/situação de processo
  com informações detalhadas (situação, canal, datas) quando o SQL Server estiver disponível.

Este service é projetado para ser usado de forma opcional pelos agentes
(`DiAgent`, `ProcessoAgent`, `ProcessoStatusService`), sem quebrar o
comportamento atual caso o SQL Server não esteja acessível.
"""

import logging
from typing import Optional, Dict, Any

from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server

logger = logging.getLogger(__name__)


class DiDetalhadaService:
    """
    Acesso simplificado a dados detalhados de DI a partir do SQL Server.
    """

    def obter_di_detalhada_por_processo(
        self, processo_referencia: str
    ) -> Optional[Dict[str, Any]]:
        """
        Tenta obter dados detalhados de DI para um processo via SQL Server.

        Retorna um dict com chaves principais:
        - numero_di
        - situacao
        - canal
        - data_desembaraco
        - data_registro
        - fonte: 'sql_server'
        """
        proc_ref = (processo_referencia or "").strip()
        if not proc_ref:
            return None

        try:
            processo = buscar_processo_consolidado_sql_server(proc_ref)
            if not processo:
                return None

            di = processo.get("di")
            if not di or not isinstance(di, dict):
                return None

            return {
                "numero_di": di.get("numero") or di.get("numero_di"),
                "situacao": di.get("situacao"),
                "canal": di.get("canal"),
                "data_desembaraco": di.get("data_desembaraco"),
                "data_registro": di.get("data_registro"),
                "fonte": "sql_server",
                "_processo_ref": proc_ref,
            }
        except Exception as e:
            logger.debug(
                f"[DiDetalhadaService] Erro ao obter DI detalhada para {proc_ref}: {e}",
                exc_info=False,
            )
            return None














