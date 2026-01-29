"""
ProcessoSyncService
===================

Sincroniza processos ativos do Kanban (cache SQLite `processos_kanban`)
para o SQL Server `mAIke_assistente` (fonte da verdade).

Escopo:
- Upsert PROCESSO_IMPORTACAO (capa do processo)
- Descobrir números CE/DI via Serpro.*_Consulta (por id_importacao) quando faltarem
- Upsert DOCUMENTO_ADUANEIRO (CE/DI/DUIMP) com payload mínimo vindo do Serpro/Duimp DB
- Persistir valores/impostos básicos da DI (VMLD/VMLE/FRETE + pagamentos) em VALOR_MERCADORIA/IMPOSTO_IMPORTACAO (idempotente)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    total: int = 0
    processos_upsert: int = 0
    documentos_upsert: int = 0
    valores_upsert: int = 0
    impostos_upsert: int = 0
    skipped: int = 0
    errors: int = 0


class ProcessoSyncService:
    def __init__(self, sqlite_path: Optional[str] = None) -> None:
        self.sqlite_path = sqlite_path or str(Path.cwd() / "chat_ia.db")

    def sincronizar_processos_ativos(
        self,
        limite: int = 50,
        incluir_documentos: bool = True,
        incluir_valores_impostos: bool = True,
    ) -> Dict[str, Any]:
        """
        Sincroniza processos do cache `processos_kanban` para o SQL Server novo.
        """
        from utils.sql_server_adapter import get_sql_adapter
        from services.documento_historico_service import DocumentoHistoricoService
        from services.imposto_valor_service import get_imposto_valor_service

        adapter = get_sql_adapter()
        if not adapter:
            return {"sucesso": False, "erro": "SQL Server adapter não disponível"}

        # Garantias de schema mínimas para evitar truncamentos em produção
        try:
            self._ensure_schema(adapter)
        except Exception as e:
            logger.warning(f"⚠️ Não consegui validar/ajustar schema do mAIke_assistente: {e}")

        stats = SyncStats()
        svc_doc = DocumentoHistoricoService()
        svc_iv = get_imposto_valor_service()

        conn = sqlite3.connect(self.sqlite_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                processo_referencia,
                id_importacao,
                etapa_kanban,
                data_embarque,
                eta_iso,
                data_desembaraco,
                numero_ce,
                numero_di,
                numero_duimp
            FROM processos_kanban
            ORDER BY atualizado_em DESC
            LIMIT ?
            """,
            (int(limite),),
        )
        rows = cur.fetchall()
        conn.close()

        stats.total = len(rows)

        for (
            processo_ref,
            id_importacao,
            etapa_kanban,
            data_embarque,
            eta_iso,
            data_desembaraco,
            numero_ce,
            numero_di,
            numero_duimp,
        ) in rows:
            try:
                proc = (processo_ref or "").upper().strip()
                if not proc:
                    stats.skipped += 1
                    continue

                # Descobrir CE/DI por id_importacao (Serpro)
                id_imp = int(id_importacao) if id_importacao is not None else None
                ce = (numero_ce or "").strip() or None
                di = (numero_di or "").strip() or None
                duimp = (numero_duimp or "").strip() or None

                if id_imp:
                    if not ce:
                        ce = self._buscar_ce_por_id_importacao_serpro(adapter, id_imp)
                    if not di:
                        di = self._buscar_di_por_id_importacao_serpro(adapter, id_imp)

                if not duimp:
                    duimp = self._buscar_duimp_por_processo_duimp_db(adapter, proc)

                # Upsert PROCESSO_IMPORTACAO
                ok_proc = self._upsert_processo_importacao(
                    adapter=adapter,
                    processo_referencia=proc,
                    id_importacao=id_imp,
                    numero_ce=ce,
                    numero_di=di,
                    numero_duimp=duimp,
                    data_embarque=data_embarque,
                    data_chegada_prevista=eta_iso,
                    data_desembaraco=data_desembaraco,
                    status_processo=etapa_kanban,
                )
                if ok_proc:
                    stats.processos_upsert += 1

                if incluir_documentos:
                    docs_written = 0
                    if ce:
                        payload_ce = self._payload_min_ce_serpro(adapter, ce)
                        if payload_ce:
                            svc_doc.detectar_e_gravar_mudancas(
                                numero_documento=str(ce),
                                tipo_documento="CE",
                                dados_novos=payload_ce,
                                fonte_dados="SERPRO_DB",
                                api_endpoint="Serpro.Ce_Root_Conhecimento_Embarque",
                                processo_referencia=proc,
                            )
                            docs_written += 1
                    if di:
                        payload_di, dados_di_id = self._payload_min_di_serpro(adapter, di)
                        if payload_di:
                            svc_doc.detectar_e_gravar_mudancas(
                                numero_documento=str(di),
                                tipo_documento="DI",
                                dados_novos=payload_di,
                                fonte_dados="SERPRO_DB",
                                api_endpoint="Serpro.Di_*",
                                processo_referencia=proc,
                            )
                            docs_written += 1
                    if duimp:
                        payload_duimp = self._payload_min_duimp_db(adapter, duimp, proc)
                        if payload_duimp:
                            svc_doc.detectar_e_gravar_mudancas(
                                numero_documento=str(duimp),
                                tipo_documento="DUIMP",
                                dados_novos=payload_duimp,
                                fonte_dados="DUIMP_DB",
                                api_endpoint="Duimp.duimp + joins",
                                processo_referencia=proc,
                            )
                            docs_written += 1

                    stats.documentos_upsert += docs_written

                if incluir_valores_impostos and di:
                    payload_di, dados_di_id = self._payload_min_di_serpro(adapter, di)
                    if dados_di_id:
                        pagamentos = self._buscar_pagamentos_di_serpro(adapter, dados_di_id)
                    else:
                        pagamentos = []

                    valores = self._buscar_valores_di_serpro(adapter, di)

                    if valores:
                        rvals = svc_iv.gravar_valores_di(proc, di, valores, fonte_dados="SERPRO_DB")
                        if rvals.get("sucesso") and rvals.get("total"):
                            stats.valores_upsert += int(rvals.get("total") or 0)

                    if pagamentos:
                        rimp = svc_iv.gravar_impostos_di(proc, di, pagamentos, fonte_dados="SERPRO_DB")
                        if rimp.get("sucesso") and rimp.get("total"):
                            stats.impostos_upsert += int(rimp.get("total") or 0)

            except Exception as e:
                stats.errors += 1
                logger.warning(f"⚠️ Falha ao sincronizar {processo_ref}: {e}", exc_info=True)

        return {
            "sucesso": True,
            "resumo": {
                "total": stats.total,
                "processos_upsert": stats.processos_upsert,
                "documentos_upsert": stats.documentos_upsert,
                "valores_upsert": stats.valores_upsert,
                "impostos_upsert": stats.impostos_upsert,
                "skipped": stats.skipped,
                "errors": stats.errors,
            },
        }

    def _ensure_schema(self, adapter) -> None:
        """
        Ajustes defensivos de schema no banco novo.
        - status_documento_codigo em DOCUMENTO_ADUANEIRO precisa suportar códigos maiores que 20 chars.
        """
        q = """
            SELECT CHARACTER_MAXIMUM_LENGTH AS len
            FROM mAIke_assistente.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME='DOCUMENTO_ADUANEIRO'
              AND COLUMN_NAME='status_documento_codigo'
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return
        try:
            current_len = int(r["data"][0].get("len") or 0)
        except Exception:
            current_len = 0
        if current_len and current_len < 50:
            logger.info(f"🔧 Ajustando DOCUMENTO_ADUANEIRO.status_documento_codigo: {current_len} → 50")
            adapter.execute_query(
                "ALTER TABLE mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO ALTER COLUMN status_documento_codigo VARCHAR(50) NULL",
                database="mAIke_assistente",
            )

    def _upsert_processo_importacao(
        self,
        adapter,
        processo_referencia: str,
        id_importacao: Optional[int],
        numero_ce: Optional[str],
        numero_di: Optional[str],
        numero_duimp: Optional[str],
        data_embarque: Optional[str],
        data_chegada_prevista: Optional[str],
        data_desembaraco: Optional[str],
        status_processo: Optional[str],
    ) -> bool:
        proc = processo_referencia.replace("'", "''")
        ce = numero_ce.replace("'", "''") if numero_ce else None
        di = numero_di.replace("'", "''") if numero_di else None
        du = numero_duimp.replace("'", "''") if numero_duimp else None
        status = (status_processo or "").strip()
        status = status.replace("'", "''") if status else None

        id_sql = str(int(id_importacao)) if id_importacao is not None else "NULL"
        ce_sql = f"'{ce}'" if ce else "NULL"
        di_sql = f"'{di}'" if di else "NULL"
        du_sql = f"'{du}'" if du else "NULL"
        st_sql = f"'{status}'" if status else "NULL"

        # datas em ISO/texto — deixar SQL Server converter quando possível
        def _dt(v: Optional[str]) -> str:
            if not v:
                return "NULL"
            vv = str(v).replace("'", "''")
            return f"'{vv}'"

        sql = f"""
            MERGE mAIke_assistente.dbo.PROCESSO_IMPORTACAO WITH (HOLDLOCK) AS tgt
            USING (
                SELECT
                    '{proc}' AS numero_processo
            ) AS src
            ON tgt.numero_processo = src.numero_processo
            WHEN MATCHED THEN
                UPDATE SET
                    id_importacao = COALESCE({id_sql}, tgt.id_importacao),
                    numero_ce = COALESCE({ce_sql}, tgt.numero_ce),
                    numero_di = COALESCE({di_sql}, tgt.numero_di),
                    numero_duimp = COALESCE({du_sql}, tgt.numero_duimp),
                    data_embarque = COALESCE({_dt(data_embarque)}, tgt.data_embarque),
                    data_chegada_prevista = COALESCE({_dt(data_chegada_prevista)}, tgt.data_chegada_prevista),
                    data_desembaraco = COALESCE({_dt(data_desembaraco)}, tgt.data_desembaraco),
                    status_processo = COALESCE({st_sql}, tgt.status_processo),
                    atualizado_em = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (
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
                ) VALUES (
                    {id_sql},
                    src.numero_processo,
                    {ce_sql},
                    {di_sql},
                    {du_sql},
                    {_dt(data_embarque)},
                    {_dt(data_chegada_prevista)},
                    {_dt(data_desembaraco)},
                    {st_sql},
                    GETDATE(),
                    GETDATE()
                );
        """
        r = adapter.execute_query(sql, database="mAIke_assistente")
        return bool(r and r.get("success"))

    def _buscar_ce_por_id_importacao_serpro(self, adapter, id_importacao: int) -> Optional[str]:
        q = f"""
            SELECT TOP 1 ce
            FROM Serpro.dbo.Ce_Consulta
            WHERE idImportacao = {int(id_importacao)}
            ORDER BY CASE WHEN active = 1 THEN 0 ELSE 1 END, id DESC
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if r.get("success") and r.get("data"):
            return r["data"][0].get("ce")
        return None

    def _buscar_di_por_id_importacao_serpro(self, adapter, id_importacao: int) -> Optional[str]:
        q = f"""
            SELECT TOP 1 di
            FROM Serpro.dbo.Di_Consulta
            WHERE idImportacao = {int(id_importacao)}
            ORDER BY CASE WHEN active = 1 THEN 0 ELSE 1 END, id DESC
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if r.get("success") and r.get("data"):
            return r["data"][0].get("di")
        return None

    def _buscar_duimp_por_processo_duimp_db(self, adapter, processo_ref: str) -> Optional[str]:
        proc = processo_ref.replace("'", "''")
        q = f"""
            SELECT TOP 1 numero
            FROM Duimp.dbo.duimp
            WHERE numero_processo = '{proc}'
            ORDER BY data_ultimo_evento DESC, atualizado_em DESC
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if r.get("success") and r.get("data"):
            return r["data"][0].get("numero")
        return None

    def _payload_min_ce_serpro(self, adapter, numero_ce: str) -> Optional[Dict[str, Any]]:
        ce = numero_ce.replace("'", "''")
        q = f"""
            SELECT TOP 1
                numero,
                situacaoCarga,
                dataSituacaoCarga,
                dataEmissao,
                dataDestinoFinal,
                navioPrimTransporte,
                portoOrigem,
                portoDestino,
                paisProcedencia
            FROM Serpro.dbo.Ce_Root_Conhecimento_Embarque
            WHERE numero = '{ce}'
            ORDER BY updatedAt DESC
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return None
        row = r["data"][0]
        return {
            "numero": row.get("numero"),
            "situacaoCarga": row.get("situacaoCarga"),
            "dataSituacaoCarga": row.get("dataSituacaoCarga"),
            "dataRegistro": row.get("dataEmissao"),
            "dataDestinoFinal": row.get("dataDestinoFinal"),
            "navioPrimTransporte": row.get("navioPrimTransporte"),
            "portoOrigem": row.get("portoOrigem"),
            "portoDestino": row.get("portoDestino"),
            "paisProcedencia": row.get("paisProcedencia"),
        }

    def _payload_min_di_serpro(self, adapter, numero_di: str) -> Tuple[Optional[Dict[str, Any]], Optional[int]]:
        di = str(numero_di).replace("'", "''")
        q = f"""
            SELECT TOP 1
                ddg.numeroDi,
                ddg.situacaoDi,
                ddg.dataHoraSituacaoDi,
                ddg.situacaoEntregaCarga,
                ddg.sequencialRetificacao,
                diDesp.canalSelecaoParametrizada,
                diDesp.dataHoraRegistro,
                diDesp.dataHoraDesembaraco,
                diRoot.dadosDiId
            FROM Serpro.dbo.Di_Dados_Gerais ddg
            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
                ON ddg.dadosGeraisId = diRoot.dadosGeraisId
            LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp
                ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
            WHERE ddg.numeroDi = '{di}'
            ORDER BY ddg.updatedAt DESC
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return (None, None)
        row = r["data"][0]
        dados_di_id = row.get("dadosDiId")
        try:
            dados_di_id_int = int(dados_di_id) if dados_di_id is not None and str(dados_di_id).strip() != "" else None
        except Exception:
            dados_di_id_int = None
        payload = {
            "numero": row.get("numeroDi"),
            "situacaoDi": row.get("situacaoDi"),
            "dataHoraSituacaoDi": row.get("dataHoraSituacaoDi"),
            "situacaoEntregaCarga": row.get("situacaoEntregaCarga"),
            "numeroRetificacao": row.get("sequencialRetificacao"),
            "canalSelecaoParametrizada": row.get("canalSelecaoParametrizada"),
            "dataHoraRegistro": row.get("dataHoraRegistro"),
            "dataHoraDesembaraco": row.get("dataHoraDesembaraco"),
        }
        return (payload, dados_di_id_int)

    def _buscar_pagamentos_di_serpro(self, adapter, dados_di_id: int) -> List[Dict[str, Any]]:
        q = f"""
            SELECT
                dp.codigoReceita,
                dp.numeroRetificacao,
                dp.valorTotal,
                dp.dataPagamento,
                dpcr.descricao_receita
            FROM Serpro.dbo.Di_Pagamento dp
            LEFT JOIN Serpro.dbo.Di_pagamentos_cod_receitas dpcr
                ON dpcr.cod_receita = dp.codigoReceita
            WHERE dp.rootDiId = {int(dados_di_id)}
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        return r.get("data") if r.get("success") and r.get("data") else []

    def _buscar_valores_di_serpro(self, adapter, numero_di: str) -> Dict[str, Any]:
        di = str(numero_di).replace("'", "''")
        q = f"""
            SELECT TOP 1
                DVMD.totalDolares AS vmld_usd,
                DVMD.totalReais AS vmld_brl,
                DVME.totalDolares AS vmle_usd,
                DVME.totalReais AS vmle_brl,
                diRoot.dadosDiId
            FROM Serpro.dbo.Di_Dados_Gerais ddg
            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
                ON ddg.dadosGeraisId = diRoot.dadosGeraisId
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD
                ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME
                ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
            WHERE ddg.numeroDi = '{di}'
            ORDER BY ddg.updatedAt DESC
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return {}
        row = r["data"][0] or {}
        valores: Dict[str, Any] = {
            "vmld_usd": row.get("vmld_usd"),
            "vmld_brl": row.get("vmld_brl"),
            "vmle_usd": row.get("vmle_usd"),
            "vmle_brl": row.get("vmle_brl"),
        }

        # Frete (por dadosDiId = freteId)
        dados_di_id = row.get("dadosDiId")
        try:
            dados_di_id_int = int(dados_di_id) if dados_di_id is not None and str(dados_di_id).strip() != "" else None
        except Exception:
            dados_di_id_int = None
        if dados_di_id_int:
            qf = f"""
                SELECT TOP 1
                    valorTotalDolares AS frete_usd,
                    totalReais AS frete_brl
                FROM Serpro.dbo.Di_Frete
                WHERE freteId = {dados_di_id_int}
            """
            rf = adapter.execute_query(qf, database="mAIke_assistente")
            if rf.get("success") and rf.get("data"):
                fr = rf["data"][0] or {}
                valores["frete_usd"] = fr.get("frete_usd")
                valores["frete_brl"] = fr.get("frete_brl")

        # Seguro (se existir tabela; se não existir, ignorar)
        try:
            if dados_di_id_int:
                qs = f"""
                    SELECT TOP 1
                        valorTotalDolares AS seguro_usd,
                        valorTotalReais AS seguro_brl
                    FROM Serpro.dbo.Di_Seguro
                    WHERE seguroId = {dados_di_id_int}
                """
                rs = adapter.execute_query(qs, database="mAIke_assistente")
                if rs.get("success") and rs.get("data"):
                    sr = rs["data"][0] or {}
                    valores["seguro_usd"] = sr.get("seguro_usd")
                    valores["seguro_brl"] = sr.get("seguro_brl")
        except Exception:
            pass

        return {k: v for k, v in valores.items() if v is not None}

    def _payload_min_duimp_db(self, adapter, numero_duimp: str, processo_ref: str) -> Optional[Dict[str, Any]]:
        num = numero_duimp.replace("'", "''")
        proc = processo_ref.replace("'", "''")
        q = f"""
            SELECT TOP 1
                d.numero,
                d.versao,
                d.data_registro,
                d.ultima_situacao,
                d.data_ultimo_evento,
                drar.canal_consolidado AS canal_consolidado
            FROM Duimp.dbo.duimp d
            LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar
                ON drar.duimp_id = d.duimp_id
            WHERE d.numero = '{num}' OR d.numero_processo = '{proc}'
            ORDER BY d.data_ultimo_evento DESC
        """
        r = adapter.execute_query(q, database="mAIke_assistente")
        if not r.get("success") or not r.get("data"):
            return None
        row = r["data"][0]
        return {
            "numero": row.get("numero"),
            "versaoDocumento": row.get("versao"),
            "situacao": row.get("ultima_situacao"),
            "situacaoCodigo": row.get("ultima_situacao"),
            "ultimaSituacao": row.get("ultima_situacao"),
            "ultimaSituacaoData": row.get("data_ultimo_evento"),
            "dataRegistro": row.get("data_registro"),
            "canalConsolidado": row.get("canal_consolidado"),
            "canal": row.get("canal_consolidado"),
        }

