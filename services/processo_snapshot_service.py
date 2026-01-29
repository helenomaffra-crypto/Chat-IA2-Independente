"""
ProcessoSnapshotService
======================

Monta um "resumo completo" de um processo de importação usando o SQL Server
`mAIke_assistente` como fonte primária (fonte da verdade).

Quando dados essenciais estiverem faltando no banco novo, pode executar fallback
seletivo (Make/Serpro/Duimp) e escrever de volta no banco novo (auto-heal).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProcessoSnapshotService:
    def __init__(self) -> None:
        pass

    def obter_snapshot(
        self,
        processo_referencia: str,
        auto_heal: bool = True,
    ) -> Dict[str, Any]:
        """
        Retorna snapshot do processo.

        Args:
            processo_referencia: Ex: ALH.0001/25
            auto_heal: Se True, tenta preencher banco novo quando faltar.
        """
        from utils.sql_server_adapter import get_sql_adapter

        processo_ref = (processo_referencia or "").upper().strip()
        if not processo_ref:
            return {"sucesso": False, "erro": "processo_referencia vazio", "dados": None}

        adapter = get_sql_adapter()
        if not adapter:
            return {"sucesso": False, "erro": "SQL Server adapter não disponível", "dados": None}

        # 1) Garantir "capa" do processo no banco novo (auto-heal seletivo)
        processo_row = self._buscar_processo_importacao(adapter, processo_ref)
        if not processo_row and auto_heal:
            self._auto_heal_processo_importacao(adapter, processo_ref)
            processo_row = self._buscar_processo_importacao(adapter, processo_ref)

        # 2) Consultas principais (sempre no banco novo)
        documentos = self._buscar_documentos(adapter, processo_ref)
        valores = self._buscar_valores_mercadoria(adapter, processo_ref)
        impostos = self._buscar_impostos(adapter, processo_ref)
        despesas = self._buscar_despesas(adapter, processo_ref)

        # 3) Métricas simples de completude (para guiar próximos backfills)
        completeness = self._calcular_completude(processo_row, documentos, valores, impostos, despesas)

        snapshot = {
            "processo_referencia": processo_ref,
            "processo": processo_row,
            "documentos": documentos,
            "valores_mercadoria": valores,
            "impostos_importacao": impostos,
            "despesas": despesas,
            "completude": completeness,
        }

        return {"sucesso": True, "erro": None, "dados": snapshot}

    def _buscar_processo_importacao(self, adapter, processo_ref: str) -> Optional[Dict[str, Any]]:
        sql = f"""
            SELECT TOP 1
                id_processo_importacao,
                id_importacao,
                numero_processo,
                numero_ce,
                numero_di,
                numero_duimp,
                data_embarque,
                data_chegada_prevista,
                data_desembaraco,
                status_processo,
                criado_em,
                atualizado_em
            FROM mAIke_assistente.dbo.PROCESSO_IMPORTACAO
            WHERE numero_processo = '{processo_ref.replace("'", "''")}'
            ORDER BY atualizado_em DESC
        """
        r = adapter.execute_query(sql, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return None
        return r["data"][0]

    def _auto_heal_processo_importacao(self, adapter, processo_ref: str) -> None:
        """
        Tenta materializar o processo no banco novo usando o pipeline legado.
        """
        try:
            from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
            from services.processo_repository import ProcessoRepository

            from services.db_policy_service import (
                get_primary_database,
                get_legacy_database,
                log_legacy_fallback,
                should_use_legacy_database
            )
            
            # Tentar ler do banco novo primeiro; se não existir, buscar no Make para migrar.
            proc_novo = buscar_processo_consolidado_sql_server(processo_ref, database=get_primary_database())
            if proc_novo:
                return

            # Fallback para Make apenas se permitido
            if should_use_legacy_database(processo_ref):
                log_legacy_fallback(
                    processo_referencia=processo_ref,
                    tool_name='_auto_heal_processo',
                    caller_function='ProcessoSnapshotService._auto_heal_processo',
                    reason="Processo não encontrado no banco primário, tentando migração"
                )
                proc_antigo = buscar_processo_consolidado_sql_server(processo_ref, database=get_legacy_database())
                if not proc_antigo:
                    return
            else:
                logger.debug(f"🔒 [_auto_heal_processo] Fallback para Make desabilitado para processo {processo_ref}")
                return

            repo = ProcessoRepository()
            try:
                repo._migrar_processo_para_banco_novo(proc_antigo)  # migração controlada
            except Exception as e:
                logger.warning(f"⚠️ Falha ao migrar processo {processo_ref} para banco novo: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Auto-heal processo_importacao falhou para {processo_ref}: {e}")

    def _buscar_documentos(self, adapter, processo_ref: str) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT
                id_documento,
                numero_documento,
                tipo_documento,
                versao_documento,
                processo_referencia,
                status_documento,
                status_documento_codigo,
                canal_documento,
                situacao_documento,
                data_registro,
                data_situacao,
                data_desembaraco,
                porto_origem_codigo,
                porto_destino_codigo,
                nome_navio,
                tipo_transporte,
                fonte_dados,
                atualizado_em
            FROM mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO
            WHERE processo_referencia = '{processo_ref.replace("'", "''")}'
            ORDER BY atualizado_em DESC
        """
        r = adapter.execute_query(sql, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return []
        return r["data"]

    def _buscar_valores_mercadoria(self, adapter, processo_ref: str) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT
                id_valor,
                processo_referencia,
                numero_documento,
                tipo_documento,
                tipo_valor,
                moeda,
                valor,
                taxa_cambio,
                data_valor,
                data_atualizacao,
                fonte_dados,
                atualizado_em
            FROM mAIke_assistente.dbo.VALOR_MERCADORIA
            WHERE processo_referencia = '{processo_ref.replace("'", "''")}'
            ORDER BY data_atualizacao DESC, atualizado_em DESC
        """
        r = adapter.execute_query(sql, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return []
        return r["data"]

    def _buscar_impostos(self, adapter, processo_ref: str) -> List[Dict[str, Any]]:
        sql = f"""
            SELECT
                id_imposto,
                processo_referencia,
                numero_documento,
                tipo_documento,
                tipo_imposto,
                codigo_receita,
                descricao_imposto,
                valor_brl,
                valor_usd,
                taxa_cambio,
                data_pagamento,
                pago,
                numero_retificacao,
                fonte_dados,
                atualizado_em
            FROM mAIke_assistente.dbo.IMPOSTO_IMPORTACAO
            WHERE processo_referencia = '{processo_ref.replace("'", "''")}'
            ORDER BY data_pagamento DESC, atualizado_em DESC
        """
        r = adapter.execute_query(sql, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return []
        return r["data"]

    def _buscar_despesas(self, adapter, processo_ref: str) -> List[Dict[str, Any]]:
        # Join leve para devolver dados úteis do lançamento bancário
        sql = f"""
            SELECT
                ltd.id_lancamento_tipo_despesa,
                ltd.processo_referencia,
                ltd.categoria_processo,
                ltd.valor_despesa,
                ltd.origem_classificacao,
                ltd.nivel_confianca,
                ltd.classificacao_validada,
                ltd.criado_em,
                mb.id_movimentacao AS id_movimentacao_bancaria,
                mb.banco_origem,
                mb.data_movimentacao,
                mb.valor_movimentacao,
                mb.sinal_movimentacao,
                CAST(mb.descricao_movimentacao AS VARCHAR(MAX)) AS descricao_movimentacao
            FROM mAIke_assistente.dbo.LANCAMENTO_TIPO_DESPESA ltd
            LEFT JOIN mAIke_assistente.dbo.MOVIMENTACAO_BANCARIA mb
                ON mb.id_movimentacao = ltd.id_movimentacao_bancaria
            WHERE ltd.processo_referencia = '{processo_ref.replace("'", "''")}'
            ORDER BY ltd.criado_em DESC
        """
        r = adapter.execute_query(sql, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return []
        return r["data"]

    def _calcular_completude(
        self,
        processo_row: Optional[Dict[str, Any]],
        documentos: List[Dict[str, Any]],
        valores: List[Dict[str, Any]],
        impostos: List[Dict[str, Any]],
        despesas: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        docs_by_tipo: Dict[str, int] = {}
        for d in documentos or []:
            t = (d.get("tipo_documento") or "N/A").upper()
            docs_by_tipo[t] = docs_by_tipo.get(t, 0) + 1

        return {
            "tem_processo_importacao": bool(processo_row),
            "documentos_total": len(documentos or []),
            "documentos_por_tipo": docs_by_tipo,
            "valores_total": len(valores or []),
            "impostos_total": len(impostos or []),
            "despesas_total": len(despesas or []),
        }

