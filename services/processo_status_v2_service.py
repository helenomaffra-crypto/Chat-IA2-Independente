"""
ProcessoStatusV2Service
======================

Implementa o padrão:

1) **Clean path** (resposta determinística):
   - Lê apenas **SQLite (Kanban/cache)** + **SQL Server mAIke_assistente**.
   - Não usa Make/queries antigas.

2) **Fallback / Auto-heal** (opcional, seletivo):
   - Quando faltar dado crítico (ex.: valores), busca em fontes oficiais (Duimp DB/Serpro)
     e **persiste no banco novo**, depois re-lê e responde novamente pelo caminho limpo.

Objetivo: resposta estável (sem “barulho” de schema legado) e banco novo sempre enriquecido.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


def _fmt_dt(val: Any) -> Optional[str]:
    """
    Formata datas (datetime/ISO string) para dd/mm/yyyy quando possível.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        from datetime import datetime

        if hasattr(val, "strftime"):
            # datetime
            return val.strftime("%d/%m/%Y")
        # string ISO
        ss = s.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(ss)
            return dt.strftime("%d/%m/%Y")
        except Exception:
            # tentar só a data
            dt = datetime.fromisoformat(ss.split("T")[0])
            return dt.strftime("%d/%m/%Y")
    except Exception:
        return s


def _norm_canal(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # Verde/Vermelho
    up = s.upper()
    if up in ("VERDE", "VERMELHO"):
        return up.title()
    return s


def _try_parse_iso_date(val: Any):
    """
    Tenta converter string ISO (ou datetime) em datetime.
    """
    if val is None:
        return None
    if hasattr(val, "strftime"):
        return val
    s = str(val).strip()
    if not s:
        return None
    try:
        from datetime import datetime

        ss = s.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(ss)
        except Exception:
            return datetime.fromisoformat(ss.split("T")[0])
    except Exception:
        return None


def _tax_order_key(tipo: str) -> Tuple[int, str]:
    t = (tipo or "").upper().strip()
    order = {
        "II": 1,
        "IPI": 2,
        "PIS": 3,
        "COFINS": 4,
        "ANTIDUMPING": 5,
        "MULTA": 6,
        "TAXA_UTILIZACAO": 7,  # Taxa SISCOMEX
        "OUTROS": 99,
    }
    return (order.get(t, 50), t)

logger = logging.getLogger(__name__)


class ProcessoStatusV2Service:
    def consultar(
        self,
        *,
        processo_referencia: str,
        auto_heal: bool = True,
        incluir_eta: bool = True,
        incluir_afrmm: bool = True,
    ) -> Dict[str, Any]:
        processo_ref = (processo_referencia or "").strip().upper()
        if not processo_ref:
            return {
                "sucesso": False,
                "erro": "processo_referencia é obrigatório",
                "resposta": "❌ Referência de processo é obrigatória.",
            }

        # Kanban (operacional) cedo para guiar auto-heal (ex.: DUIMP status mais atual)
        kanban = self._buscar_kanban_min(processo_ref) if (auto_heal or incluir_eta) else None

        # 1) Clean snapshot (mAIke_assistente)
        # Se processo não está no Kanban, tentar auto-heal para buscar dados antigos
        snapshot = self._snapshot_clean(processo_ref, tentar_auto_heal_se_sem_kanban=(kanban is None and auto_heal))
        if not snapshot.get("sucesso"):
            return snapshot

        dados = snapshot.get("dados") or {}

        # 2) Auto-heal seletivo (somente quando faltar valor e houver DUIMP)
        if auto_heal:
            # 2a) Auto-heal do documento DUIMP (situação/canal) no DOCUMENTO_ADUANEIRO
            try:
                self._autoheal_documento_duimp(dados, kanban=kanban)
            except Exception as e:
                logger.debug(f"[StatusV2] auto-heal documento DUIMP falhou: {e}")

            try:
                self._autoheal_valores_duimp_tributos_mercadoria(dados)
            except Exception as e:
                logger.debug(f"[StatusV2] auto-heal valores DUIMP falhou: {e}")
            
            # ✅ NOVO: Se DUIMP está incompleta (falta situação/canal/impostos), tentar buscar da API oficial
            # ⚠️ IMPORTANTE: Verificar DEPOIS do auto-heal para pegar dados atualizados
            try:
                doc_duimp = None
                for d in (dados.get("documentos") or []):
                    if isinstance(d, dict) and (d.get("tipo_documento") or "").upper() == "DUIMP":
                        doc_duimp = d
                        break
                
                if doc_duimp:
                    numero_duimp = doc_duimp.get("numero_documento")
                    tem_situacao = doc_duimp.get("situacao_documento") or doc_duimp.get("status_documento")
                    tem_canal = doc_duimp.get("canal_documento")
                    
                    # Verificar se faltam impostos/valores também (re-buscar após auto-heal)
                    # Re-buscar snapshot para pegar dados atualizados após auto-heal
                    snapshot_atualizado = self._snapshot_clean(processo_ref, tentar_auto_heal_se_sem_kanban=False)
                    if snapshot_atualizado.get("sucesso"):
                        dados_atualizados = snapshot_atualizado.get("dados") or {}
                        impostos = dados_atualizados.get("impostos_importacao") or []
                        valores = dados_atualizados.get("valores_mercadoria") or []
                    else:
                        impostos = dados.get("impostos_importacao") or []
                        valores = dados.get("valores_mercadoria") or []
                    
                    tem_impostos = isinstance(impostos, list) and len(impostos) > 0
                    tem_valores = isinstance(valores, list) and len(valores) > 0
                    
                    # Se falta situação, canal, impostos ou valores, buscar da API oficial
                    precisa_buscar_api = False
                    motivo = []
                    if not tem_situacao:
                        motivo.append("situação")
                        precisa_buscar_api = True
                    if not tem_canal:
                        motivo.append("canal")
                        precisa_buscar_api = True
                    if not tem_impostos:
                        motivo.append("impostos")
                        precisa_buscar_api = True
                    if not tem_valores:
                        motivo.append("valores")
                        precisa_buscar_api = True
                    
                    if numero_duimp and precisa_buscar_api:
                        logger.info(f"🔍 DUIMP {numero_duimp} incompleta (falta: {', '.join(motivo)}). Buscando da API oficial...")
                        logger.info(f"   📊 Estado atual: situação={bool(tem_situacao)}, canal={bool(tem_canal)}, impostos={len(impostos) if isinstance(impostos, list) else 0}, valores={len(valores) if isinstance(valores, list) else 0}")
                        try:
                            from services.agents.duimp_agent import DuimpAgent
                            duimp_agent = DuimpAgent()
                            resultado_api = duimp_agent._obter_dados_duimp(
                                {'numero_duimp': numero_duimp, 'versao_duimp': doc_duimp.get('versao_documento')},
                                context={'processo_referencia': processo_ref}
                            )
                            if resultado_api.get('sucesso'):
                                logger.info(f'✅ DUIMP {numero_duimp} atualizada via API oficial')
                                # Aguardar um pouco para garantir que dados foram persistidos
                                import time
                                time.sleep(0.5)
                                # Re-buscar snapshot após atualização
                                snapshot2 = self._snapshot_clean(processo_ref, tentar_auto_heal_se_sem_kanban=False)
                                if snapshot2.get("sucesso"):
                                    dados = snapshot2.get("dados") or dados
                                    # Log para debug
                                    impostos_apos = dados.get("impostos_importacao") or []
                                    logger.info(f"   📊 Estado após API: impostos={len(impostos_apos) if isinstance(impostos_apos, list) else 0}")
                            else:
                                logger.warning(f'⚠️ Falha ao buscar DUIMP da API: {resultado_api.get("erro")}')
                        except Exception as e:
                            logger.error(f'❌ Erro ao buscar DUIMP da API oficial: {e}', exc_info=True)
            except Exception as e:
                logger.debug(f"[StatusV2] erro ao verificar/enriquecer DUIMP via API: {e}")

            # 2c) Auto-heal DI (quando houver numero_di): valores (VMLD/VMLE/FRETE/SEGURO) + impostos (pagamentos)
            try:
                self._autoheal_di_valores_impostos(dados)
            except Exception as e:
                logger.debug(f"[StatusV2] auto-heal DI valores/impostos falhou: {e}")

            # re-snapshot após possíveis persistências (sem auto-heal, só reler banco novo)
            snapshot2 = self._snapshot_clean(processo_ref, tentar_auto_heal_se_sem_kanban=False)
            if snapshot2.get("sucesso"):
                dados = snapshot2.get("dados") or dados

        # 3) Enriquecimento de ETA (SQLite Kanban)
        kanban = kanban if incluir_eta else None

        # 4) Enriquecimento AFRMM (Mercante)
        afrmm = None
        if incluir_afrmm:
            try:
                afrmm = self._buscar_afrmm_pago(dados, kanban)
            except Exception:
                afrmm = None

        resposta = self._formatar_resposta(processo_ref, dados, kanban=kanban, afrmm=afrmm)
        return {"sucesso": True, "erro": None, "resposta": resposta, "dados": dados}

    # -------------------------
    # Clean path helpers
    # -------------------------

    def _snapshot_clean(self, processo_ref: str, *, tentar_auto_heal_se_sem_kanban: bool = False) -> Dict[str, Any]:
        from services.processo_snapshot_service import ProcessoSnapshotService

        svc = ProcessoSnapshotService()
        # Se processo não está no Kanban (antigo), tentar auto-heal para buscar dados do banco antigo/Make
        use_auto_heal = tentar_auto_heal_se_sem_kanban
        return svc.obter_snapshot(processo_ref, auto_heal=use_auto_heal)

    def _buscar_kanban_min(self, processo_ref: str) -> Optional[Dict[str, Any]]:
        """
        Busca campos operacionais do Kanban (cache SQLite).
        """
        try:
            # Em docker, o app roda em /app; a base fica em /app/chat_ia.db
            db_path = "chat_ia.db"
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                """
                SELECT processo_referencia, numero_ce, numero_di, numero_duimp,
                       etapa_kanban,
                       situacao_ce, situacao_entrega,
                       data_destino_final, data_armazenamento,
                       eta_iso, porto_nome, nome_navio, status_shipsgo,
                       atualizado_em
                FROM processos_kanban
                WHERE processo_referencia = ?
                """,
                (processo_ref,),
            )
            row = cur.fetchone()
            conn.close()
            if not row:
                return None
            etapa = row[4]
            situacao_ce = row[5]
            situacao_entrega = row[6]
            data_destino_final = row[7]
            data_armazenamento = row[8]
            eta_iso = row[9]
            porto_nome = row[10]
            nome_navio = row[11]
            status_shipsgo = row[12]
            atualizado_em = row[13]

            # Extrair status/canal da DUIMP do JSON do Kanban (quando existir)
            duimp_situacao = None
            duimp_canal = None
            importador_nome = None
            try:
                curj = sqlite3.connect(db_path).cursor()
                curj.execute("SELECT dados_completos_json FROM processos_kanban WHERE processo_referencia = ?", (processo_ref,))
                raw = (curj.fetchone() or [None])[0]
                curj.connection.close()
                if raw:
                    import json
                    data = json.loads(raw)
                    # procurar duimp list
                    duimps = data.get("duimp") if isinstance(data, dict) else None
                    if isinstance(duimps, list) and duimps:
                        d0 = duimps[0] if isinstance(duimps[0], dict) else None
                        if d0:
                            duimp_situacao = d0.get("situacao_duimp") or d0.get("situacao") or d0.get("ultima_situacao")
                            duimp_canal = d0.get("canal_duimp") or d0.get("canal") or d0.get("canalConsolidado")

                    # Nome do importador pode vir com chaves diferentes (Kanban/DI)
                    def _find_first_str(obj, keys_lower):
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(k, str) and k.lower() in keys_lower:
                                    if isinstance(v, str) and v.strip():
                                        return v.strip()
                                r = _find_first_str(v, keys_lower)
                                if r:
                                    return r
                        elif isinstance(obj, list):
                            for it in obj:
                                r = _find_first_str(it, keys_lower)
                                if r:
                                    return r
                        return None

                    importador_nome = _find_first_str(
                        data,
                        {
                            "nomeimportadordi",
                            "nome_razao_social",
                            "nomeimportador",
                            "razaosocialimportador",
                            "importador",
                            "importername",
                        },
                    )
            except Exception:
                pass
            return {
                "processo_referencia": row[0],
                "numero_ce": row[1],
                "numero_di": row[2],
                "numero_duimp": row[3],
                "etapa_kanban": etapa,
                "situacao_ce": situacao_ce,
                "situacao_entrega": situacao_entrega,
                "data_destino_final": data_destino_final,
                "data_armazenamento": data_armazenamento,
                "eta_iso": eta_iso,
                "porto_nome": porto_nome,
                "nome_navio": nome_navio,
                "status_shipsgo": status_shipsgo,
                "kanban_atualizado_em": atualizado_em,
                "importador_nome": importador_nome,
                "duimp_situacao": duimp_situacao,
                "duimp_canal": duimp_canal,
            }
        except Exception:
            return None

    def _buscar_afrmm_pago(self, snapshot: Dict[str, Any], kanban: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        from services.mercante_afrmm_pagamentos_service import MercanteAfrmmPagamentosService

        proc_ref = (snapshot.get("processo_referencia") or "").strip().upper()
        numero_ce = None

        # Preferir CE do Kanban, depois do processo/documents
        if kanban and kanban.get("numero_ce"):
            numero_ce = str(kanban.get("numero_ce")).strip()
        else:
            proc = snapshot.get("processo") or {}
            if isinstance(proc, dict) and proc.get("numero_ce"):
                numero_ce = str(proc.get("numero_ce")).strip()
            if not numero_ce:
                for d in (snapshot.get("documentos") or []):
                    if isinstance(d, dict) and (d.get("tipo_documento") or "").upper() == "CE":
                        numero_ce = str(d.get("numero_documento") or "").strip() or None
                        if numero_ce:
                            break

        svc = MercanteAfrmmPagamentosService()
        r = svc.listar(
            ce_mercante=numero_ce,
            processo_referencia=proc_ref or None,
            limite=1,
        )
        itens = (r.get("dados") or {}).get("itens") if isinstance(r, dict) else None
        if not isinstance(itens, list) or not itens:
            return None
        it = itens[0] or {}
        return {
            "processo_referencia": proc_ref or None,
            "ce_mercante": numero_ce,
            "created_at": it.get("created_at"),
            "status": it.get("status"),
            "pdf_url": it.get("pdf_url"),  # ✅ NOVO (26/01/2026): Incluir PDF URL se disponível
            "valor_total_debito": it.get("valor_total_debito"),
            "screenshot_relpath": it.get("screenshot_relpath"),
            "screenshot_url": it.get("screenshot_url"),
            "observacoes": it.get("observacoes"),
        }

    # -------------------------
    # Auto-heal (seletivo)
    # -------------------------

    def _autoheal_valores_duimp_tributos_mercadoria(self, snapshot: Dict[str, Any]) -> None:
        """
        Se VALOR_MERCADORIA estiver vazio e houver DUIMP, busca VMLE/FOB do Duimp DB
        (Duimp.dbo.duimp_tributos_mercadoria) e persiste em mAIke_assistente.dbo.VALOR_MERCADORIA.
        """
        # ⚠️ Importante: este auto-heal também é usado como "gancho" para preencher impostos
        # quando o processo tem DUIMP, então NÃO podemos retornar cedo só porque valores já existem.
        valores = snapshot.get("valores_mercadoria") or []
        impostos = snapshot.get("impostos_importacao") or []
        tem_valores = isinstance(valores, list) and len(valores) > 0
        tem_impostos = isinstance(impostos, list) and len(impostos) > 0
        if tem_valores and tem_impostos:
            return

        numero_duimp = None
        proc = snapshot.get("processo") or {}
        if isinstance(proc, dict) and proc.get("numero_duimp"):
            numero_duimp = proc.get("numero_duimp")
        if not numero_duimp:
            for d in (snapshot.get("documentos") or []):
                if isinstance(d, dict) and (d.get("tipo_documento") or "").upper() == "DUIMP":
                    numero_duimp = d.get("numero_documento")
                    break
        if not numero_duimp:
            return

        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import get_primary_database

        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            return
        db = get_primary_database()

        num = str(numero_duimp).replace("'", "''")
        qid = f"SELECT TOP 1 duimp_id FROM Duimp.dbo.duimp WHERE numero = '{num}'"
        rid = sql_adapter.execute_query(qid, database=db, notificar_erro=False)
        duimp_id = None
        if isinstance(rid, dict) and rid.get("success") and rid.get("data"):
            duimp_id = (rid.get("data") or [{}])[0].get("duimp_id")
        if not duimp_id:
            return

        qv = (
            "SELECT TOP 1 valor_total_local_embarque_brl, valor_total_local_embarque_usd "
            f"FROM Duimp.dbo.duimp_tributos_mercadoria WHERE duimp_id = {int(duimp_id)}"
        )
        rv = sql_adapter.execute_query(qv, database=db, notificar_erro=False)
        rowv = (rv.get("data") or [{}])[0] if (isinstance(rv, dict) and rv.get("success") and rv.get("data")) else {}
        v_brl = rowv.get("valor_total_local_embarque_brl")
        v_usd = rowv.get("valor_total_local_embarque_usd")
        try:
            v_brl_f = float(v_brl) if v_brl is not None else 0.0
        except Exception:
            v_brl_f = 0.0
        try:
            v_usd_f = float(v_usd) if v_usd is not None else 0.0
        except Exception:
            v_usd_f = 0.0

        proc_ref = (snapshot.get("processo_referencia") or "").strip().upper()
        proc_sql = proc_ref.replace("'", "''")
        duimp_sql = str(numero_duimp).replace("'", "''")

        def _merge_val(tipo_valor: str, moeda: str, valor: float) -> None:
            tv = tipo_valor.replace("'", "''")
            md = moeda.replace("'", "''")
            sqlm = f"""
                MERGE dbo.VALOR_MERCADORIA WITH (HOLDLOCK) AS tgt
                USING (
                    SELECT
                        '{proc_sql}' AS processo_referencia,
                        '{duimp_sql}' AS numero_documento,
                        'DUIMP' AS tipo_documento,
                        '{tv}' AS tipo_valor,
                        '{md}' AS moeda
                ) AS src
                ON tgt.processo_referencia = src.processo_referencia
                   AND tgt.numero_documento = src.numero_documento
                   AND tgt.tipo_documento = src.tipo_documento
                   AND tgt.tipo_valor = src.tipo_valor
                   AND tgt.moeda = src.moeda
                WHEN MATCHED THEN
                    UPDATE SET
                        valor = {float(valor)},
                        data_atualizacao = GETDATE(),
                        fonte_dados = 'DUIMP_DB',
                        atualizado_em = GETDATE()
                WHEN NOT MATCHED THEN
                    INSERT (
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
                        json_dados_originais,
                        criado_em,
                        atualizado_em
                    ) VALUES (
                        src.processo_referencia,
                        src.numero_documento,
                        src.tipo_documento,
                        src.tipo_valor,
                        src.moeda,
                        {float(valor)},
                        NULL,
                        NULL,
                        GETDATE(),
                        'DUIMP_DB',
                        NULL,
                        GETDATE(),
                        GETDATE()
                    );
            """
            sql_adapter.execute_query(sqlm, database=db, notificar_erro=False)

        # 1) Auto-heal valores (somente se estiverem faltando)
        if not tem_valores and (v_brl_f or v_usd_f):
            if v_usd_f:
                _merge_val("VMLE", "USD", v_usd_f)
                _merge_val("FOB", "USD", v_usd_f)
            if v_brl_f:
                _merge_val("VMLE", "BRL", v_brl_f)
                _merge_val("FOB", "BRL", v_brl_f)

        # 2) Auto-heal impostos (somente se estiverem faltando)
        # Fonte: Duimp.dbo.duimp_tributos_calculados (mesma origem usada no consolidado do SQL Server legado)
        if not tem_impostos:
            try:
                qtc = f"""
                    SELECT
                        tipo,
                        valor_calculado,
                        valor_devido,
                        valor_a_recolher,
                        valor_recolhido
                    FROM Duimp.dbo.duimp_tributos_calculados WITH (NOLOCK)
                    WHERE duimp_id = {int(duimp_id)}
                    ORDER BY tipo
                """
                rtc = sql_adapter.execute_query(qtc, database=db, notificar_erro=False)
                rows_tc = (rtc.get("data") or []) if isinstance(rtc, dict) and rtc.get("success") else []

                def _norm_tipo_imposto(tipo_raw: str) -> str:
                    t = (tipo_raw or "").strip().upper()
                    if not t:
                        return "OUTROS"
                    if t in ("II", "IPI", "PIS", "COFINS", "ICMS", "ANTIDUMPING"):
                        return t
                    if "IMPOSTO DE IMPORT" in t:
                        return "II"
                    if "PRODUTOS INDUSTRIALIZADOS" in t:
                        return "IPI"
                    if "COFINS" in t:
                        return "COFINS"
                    if "PIS" in t:
                        return "PIS"
                    if "ICMS" in t:
                        return "ICMS"
                    if "ANTIDUMP" in t:
                        return "ANTIDUMPING"
                    if "TAXA" in t or "UTILIZA" in t:
                        return "TAXA_UTILIZACAO"
                    return "OUTROS"

                def _pick_valor_brl(r: Dict[str, Any]) -> float:
                    # Preferir valor_recolhido > a_recolher > devido > calculado
                    for k in ("valor_recolhido", "valor_a_recolher", "valor_devido", "valor_calculado"):
                        v = r.get(k)
                        try:
                            vf = float(v) if v is not None else 0.0
                        except Exception:
                            vf = 0.0
                        if vf and vf > 0:
                            return vf
                    return 0.0

                gravados = 0
                for r in rows_tc:
                    if not isinstance(r, dict):
                        continue
                    tipo_raw = r.get("tipo") or ""
                    tipo_imp = _norm_tipo_imposto(str(tipo_raw))
                    valor_brl = _pick_valor_brl(r)
                    if not valor_brl:
                        continue

                    tipo_esc = tipo_imp.replace("'", "''")
                    desc_esc = str(tipo_raw).replace("'", "''")
                    sql_merge_imp = f"""
                        MERGE dbo.IMPOSTO_IMPORTACAO WITH (HOLDLOCK) AS tgt
                        USING (
                            SELECT
                                '{proc_sql}' AS processo_referencia,
                                '{duimp_sql}' AS numero_documento,
                                'DUIMP' AS tipo_documento,
                                '{tipo_esc}' AS tipo_imposto
                        ) AS src
                        ON tgt.processo_referencia = src.processo_referencia
                           AND tgt.numero_documento = src.numero_documento
                           AND tgt.tipo_documento = src.tipo_documento
                           AND tgt.tipo_imposto = src.tipo_imposto
                        WHEN MATCHED THEN
                            UPDATE SET
                                valor_brl = {float(valor_brl)},
                                descricao_imposto = '{desc_esc}',
                                fonte_dados = 'DUIMP_DB',
                                atualizado_em = GETDATE()
                        WHEN NOT MATCHED THEN
                            INSERT (
                                processo_referencia,
                                numero_documento,
                                tipo_documento,
                                tipo_imposto,
                                valor_brl,
                                descricao_imposto,
                                fonte_dados,
                                pago,
                                criado_em,
                                atualizado_em
                            ) VALUES (
                                '{proc_sql}',
                                '{duimp_sql}',
                                'DUIMP',
                                '{tipo_esc}',
                                {float(valor_brl)},
                                '{desc_esc}',
                                'DUIMP_DB',
                                1,
                                GETDATE(),
                                GETDATE()
                            );
                    """
                    sql_adapter.execute_query(sql_merge_imp, database=db, notificar_erro=False)
                    gravados += 1

                if gravados:
                    logger.info(f"✅ [StatusV2] Auto-heal: {gravados} imposto(s) gravado(s) em IMPOSTO_IMPORTACAO a partir de duimp_tributos_calculados (DUIMP {numero_duimp})")
            except Exception as e:
                logger.debug(f"[StatusV2] auto-heal impostos DUIMP falhou: {e}")

    def _autoheal_documento_duimp(self, snapshot: Dict[str, Any], *, kanban: Optional[Dict[str, Any]]) -> None:
        """
        Preenche `DOCUMENTO_ADUANEIRO` da DUIMP com situação/canal quando estiverem vazios.

        Fonte: Duimp DB (tabelas duimp / duimp_diagnostico / duimp_resultado_analise_risco).
        Persistência: via DocumentoHistoricoService (upsert canônico).
        """
        proc_ref = (snapshot.get("processo_referencia") or "").strip().upper()
        if not proc_ref:
            return

        # Descobrir número da DUIMP
        numero_duimp = None
        proc = snapshot.get("processo") or {}
        if isinstance(proc, dict) and proc.get("numero_duimp"):
            numero_duimp = proc.get("numero_duimp")
        if not numero_duimp:
            for d in (snapshot.get("documentos") or []):
                if isinstance(d, dict) and (d.get("tipo_documento") or "").upper() == "DUIMP":
                    numero_duimp = d.get("numero_documento")
                    break
        if not numero_duimp:
            return

        # Verificar se já está preenchido no snapshot
        doc_duimp = None
        for d in (snapshot.get("documentos") or []):
            if isinstance(d, dict) and (d.get("tipo_documento") or "").upper() == "DUIMP" and str(d.get("numero_documento") or "") == str(numero_duimp):
                doc_duimp = d
                break
        if doc_duimp and (doc_duimp.get("situacao_documento") or doc_duimp.get("status_documento")) and doc_duimp.get("canal_documento"):
            return

        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import get_primary_database

        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            return
        db = get_primary_database()

        num = str(numero_duimp).replace("'", "''")
        q0 = f"""
            SELECT TOP 1 duimp_id, versao, data_registro, data_ultimo_evento, ultima_situacao
            FROM Duimp.dbo.duimp
            WHERE numero = '{num}'
        """
        r0 = sql_adapter.execute_query(q0, database=db, notificar_erro=False)
        if not (isinstance(r0, dict) and r0.get("success") and r0.get("data")):
            # ✅ NOVO: Se não encontrou no SQL Server antigo, tentar buscar da API oficial
            logger.info(f"🔍 DUIMP {numero_duimp} não encontrada no SQL Server antigo. Tentando buscar da API oficial...")
            try:
                from services.agents.duimp_agent import DuimpAgent
                duimp_agent = DuimpAgent()
                resultado_api = duimp_agent._obter_dados_duimp(
                    {'numero_duimp': numero_duimp, 'versao_duimp': None},
                    context={'processo_referencia': proc_ref}
                )
                if resultado_api.get('sucesso'):
                    logger.info(f'✅ DUIMP {numero_duimp} encontrada e atualizada via API oficial')
                    # Dados já foram atualizados no banco SQL Server pelo obter_dados_duimp
                    return
                else:
                    logger.debug(f'DUIMP {numero_duimp} não encontrada na API oficial: {resultado_api.get("erro")}')
            except Exception as e:
                logger.debug(f'Erro ao buscar DUIMP da API oficial: {e}')
            return
        row0 = (r0.get("data") or [{}])[0] or {}
        duimp_id = row0.get("duimp_id")
        if not duimp_id:
            # ✅ NOVO: Se não tem duimp_id mas encontrou registro, tentar buscar da API oficial para dados mais completos
            logger.info(f"🔍 DUIMP {numero_duimp} encontrada no SQL Server mas sem duimp_id. Tentando buscar da API oficial para dados completos...")
            try:
                from services.agents.duimp_agent import DuimpAgent
                duimp_agent = DuimpAgent()
                resultado_api = duimp_agent._obter_dados_duimp(
                    {'numero_duimp': numero_duimp, 'versao_duimp': row0.get('versao')},
                    context={'processo_referencia': proc_ref}
                )
                if resultado_api.get('sucesso'):
                    logger.info(f'✅ DUIMP {numero_duimp} atualizada via API oficial')
                    # Dados já foram atualizados no banco SQL Server pelo obter_dados_duimp
                    return
            except Exception as e:
                logger.debug(f'Erro ao buscar DUIMP da API oficial: {e}')
            return

        # Situação/canal: priorizar Kanban (operacional) se disponível → Duimp DB
        situacao = None
        canal = None

        if kanban:
            ks = kanban.get("duimp_situacao")
            kc = kanban.get("duimp_canal")
            if ks and str(ks).strip():
                situacao = ks
            if kc and str(kc).strip():
                canal = kc

        # Se Kanban não trouxe, usar Duimp DB
        try:
            if not situacao:
                qd = f"SELECT TOP 1 situacao_duimp, situacao, data_geracao FROM Duimp.dbo.duimp_diagnostico WHERE duimp_id = {int(duimp_id)} ORDER BY data_geracao DESC"
                rd = sql_adapter.execute_query(qd, database=db, notificar_erro=False)
                if isinstance(rd, dict) and rd.get("success") and rd.get("data"):
                    drow = (rd.get("data") or [{}])[0] or {}
                    situacao = drow.get("situacao_duimp") or drow.get("situacao")
        except Exception:
            pass
        if not situacao:
            try:
                qs = f"SELECT TOP 1 situacao_duimp FROM Duimp.dbo.duimp_situacao WHERE duimp_id = {int(duimp_id)}"
                rs = sql_adapter.execute_query(qs, database=db, notificar_erro=False)
                if isinstance(rs, dict) and rs.get("success") and rs.get("data"):
                    srow = (rs.get("data") or [{}])[0] or {}
                    situacao = srow.get("situacao_duimp")
            except Exception:
                pass
        if not situacao:
            situacao = row0.get("ultima_situacao")

        if not canal:
            try:
                qr = f"SELECT TOP 1 canal_consolidado FROM Duimp.dbo.duimp_resultado_analise_risco WHERE duimp_id = {int(duimp_id)}"
                rr = sql_adapter.execute_query(qr, database=db, notificar_erro=False)
                if isinstance(rr, dict) and rr.get("success") and rr.get("data"):
                    rrow = (rr.get("data") or [{}])[0] or {}
                    canal = rrow.get("canal_consolidado")
            except Exception:
                canal = None

        payload = {
            "numero": str(numero_duimp),
            "versaoDocumento": row0.get("versao"),
            "dataRegistro": row0.get("data_registro"),
            "ultimaSituacaoData": row0.get("data_ultimo_evento"),
            "situacao": situacao,
            "ultimaSituacao": situacao,
            "situacaoCodigo": situacao,
            "canalConsolidado": canal,
            "canal": canal,
        }

        # Persistir via upsert canônico
        try:
            from services.documento_historico_service import DocumentoHistoricoService

            svc_doc = DocumentoHistoricoService()
            svc_doc.detectar_e_gravar_mudancas(
                numero_documento=str(numero_duimp),
                tipo_documento="DUIMP",
                dados_novos=payload,
                fonte_dados="DUIMP_DB",
                api_endpoint="Duimp.dbo.duimp (+diagnostico/risco)",
                processo_referencia=proc_ref,
            )
        except Exception as e:
            logger.debug(f"[StatusV2] Falha ao persistir DUIMP em DOCUMENTO_ADUANEIRO: {e}")

    def _autoheal_di_valores_impostos(self, snapshot: Dict[str, Any]) -> None:
        """
        Se existir DI para o processo e estiver faltando valores/impostos no banco novo,
        busca no Serpro DB e persiste em:
        - mAIke_assistente.dbo.VALOR_MERCADORIA (VMLD/VMLE/FRETE/SEGURO)
        - mAIke_assistente.dbo.IMPOSTO_IMPORTACAO (pagamentos)
        """
        proc_ref = (snapshot.get("processo_referencia") or "").strip().upper()
        if not proc_ref:
            return

        # Descobrir DI
        numero_di = None
        proc = snapshot.get("processo") or {}
        if isinstance(proc, dict) and proc.get("numero_di"):
            numero_di = proc.get("numero_di")
        if not numero_di:
            for d in (snapshot.get("documentos") or []):
                if isinstance(d, dict) and (d.get("tipo_documento") or "").upper() == "DI":
                    numero_di = d.get("numero_documento")
                    break
        if not numero_di:
            return

        # Se já temos valores e impostos no snapshot, não fazer nada
        valores = snapshot.get("valores_mercadoria") or []
        impostos = snapshot.get("impostos_importacao") or []
        tem_valores = isinstance(valores, list) and any(
            isinstance(v, dict) and (v.get("tipo_valor") in ("VMLD", "VMLE", "FRETE", "SEGURO", "FOB")) for v in valores
        )
        tem_impostos = isinstance(impostos, list) and len(impostos) > 0
        if tem_valores and tem_impostos:
            return

        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import get_primary_database

        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            return
        db = get_primary_database()

        di = str(numero_di).replace("'", "''")

        # 1) Buscar dadosDiId e canal/situação (min) + VMLD/VMLE
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
                diRoot.dadosDiId,
                DVMD.totalDolares AS vmld_usd,
                DVMD.totalReais AS vmld_brl,
                DVME.totalDolares AS vmle_usd,
                DVME.totalReais AS vmle_brl
            FROM Serpro.dbo.Di_Dados_Gerais ddg
            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
                ON ddg.dadosGeraisId = diRoot.dadosGeraisId
            LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp
                ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD
                ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME
                ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
            WHERE ddg.numeroDi = '{di}'
            ORDER BY ddg.updatedAt DESC
        """
        r = sql_adapter.execute_query(q, database=db, notificar_erro=False)
        if not (isinstance(r, dict) and r.get("success") and r.get("data")):
            # ✅ NOVO: Se não encontrou no SQL Server antigo, tentar buscar da API oficial
            logger.info(f"🔍 DI {numero_di} não encontrada no SQL Server antigo. Tentando buscar da API oficial...")
            try:
                from services.agents.di_agent import DiAgent
                di_agent = DiAgent()
                resultado_api = di_agent._obter_dados_di(
                    {'numero_di': numero_di},
                    context={'processo_referencia': proc_ref}
                )
                if resultado_api.get('sucesso'):
                    logger.info(f'✅ DI {numero_di} encontrada e atualizada via API oficial')
                    # Dados já foram atualizados no banco SQL Server pelo obter_dados_di
                    return
                else:
                    logger.debug(f'DI {numero_di} não encontrada na API oficial: {resultado_api.get("erro")}')
            except Exception as e:
                logger.debug(f'Erro ao buscar DI da API oficial: {e}')
            return
        row = (r.get("data") or [{}])[0] or {}
        dados_di_id = row.get("dadosDiId")
        try:
            dados_di_id_int = int(dados_di_id) if dados_di_id is not None and str(dados_di_id).strip() != "" else None
        except Exception:
            dados_di_id_int = None

        # 2) Frete/Seguro (1:1 com dadosDiId)
        valores_dict: Dict[str, Any] = {
            "vmld_usd": row.get("vmld_usd"),
            "vmld_brl": row.get("vmld_brl"),
            "vmle_usd": row.get("vmle_usd"),
            "vmle_brl": row.get("vmle_brl"),
        }
        if dados_di_id_int:
            try:
                qf = f"""
                    SELECT TOP 1 valorTotalDolares AS frete_usd, totalReais AS frete_brl
                    FROM Serpro.dbo.Di_Frete
                    WHERE freteId = {dados_di_id_int}
                """
                rf = sql_adapter.execute_query(qf, database=db, notificar_erro=False)
                if isinstance(rf, dict) and rf.get("success") and rf.get("data"):
                    fr = (rf.get("data") or [{}])[0] or {}
                    valores_dict["frete_usd"] = fr.get("frete_usd")
                    valores_dict["frete_brl"] = fr.get("frete_brl")
            except Exception:
                pass
            try:
                qs = f"""
                    SELECT TOP 1 valorTotalDolares AS seguro_usd, valorTotalReais AS seguro_brl
                    FROM Serpro.dbo.Di_Seguro
                    WHERE seguroId = {dados_di_id_int}
                """
                rs = sql_adapter.execute_query(qs, database=db, notificar_erro=False)
                if isinstance(rs, dict) and rs.get("success") and rs.get("data"):
                    sr = (rs.get("data") or [{}])[0] or {}
                    valores_dict["seguro_usd"] = sr.get("seguro_usd")
                    valores_dict["seguro_brl"] = sr.get("seguro_brl")
            except Exception:
                pass

        # Persistir valores (se faltavam)
        if not tem_valores:
            try:
                from services.imposto_valor_service import get_imposto_valor_service

                svc_iv = get_imposto_valor_service()
                svc_iv.gravar_valores_di(proc_ref, str(numero_di), {k: v for k, v in valores_dict.items() if v is not None}, fonte_dados="SERPRO_DB")
            except Exception:
                pass

        # Persistir impostos (pagamentos) da DI (se faltavam)
        if not tem_impostos and dados_di_id_int:
            try:
                qp = f"""
                    SELECT
                        dp.codigoReceita,
                        dp.numeroRetificacao,
                        dp.valorTotal,
                        dp.dataPagamento
                    FROM Serpro.dbo.Di_Pagamento dp
                    WHERE dp.rootDiId = {dados_di_id_int}
                """
                rp = sql_adapter.execute_query(qp, database=db, notificar_erro=False)
                pagamentos = rp.get("data") if isinstance(rp, dict) and rp.get("success") else []
                if isinstance(pagamentos, list) and pagamentos:
                    from services.imposto_valor_service import get_imposto_valor_service
                    svc_iv = get_imposto_valor_service()
                    svc_iv.gravar_impostos_di(proc_ref, str(numero_di), pagamentos, fonte_dados="SERPRO_DB")
            except Exception:
                pass

        # Persistir documento DI (status/canal) no DOCUMENTO_ADUANEIRO se ainda não existir
        try:
            from services.documento_historico_service import DocumentoHistoricoService

            payload_di = {
                "numero": row.get("numeroDi") or str(numero_di),
                "situacaoDi": row.get("situacaoDi"),
                "dataHoraSituacaoDi": row.get("dataHoraSituacaoDi"),
                "situacaoEntregaCarga": row.get("situacaoEntregaCarga"),
                "numeroRetificacao": row.get("sequencialRetificacao"),
                "canalSelecaoParametrizada": row.get("canalSelecaoParametrizada"),
                "dataHoraRegistro": row.get("dataHoraRegistro"),
                "dataHoraDesembaraco": row.get("dataHoraDesembaraco"),
            }
            svc_doc = DocumentoHistoricoService()
            svc_doc.detectar_e_gravar_mudancas(
                numero_documento=str(numero_di),
                tipo_documento="DI",
                dados_novos=payload_di,
                fonte_dados="SERPRO_DB",
                api_endpoint="Serpro.Di_*",
                processo_referencia=proc_ref,
            )
        except Exception:
            pass

    # -------------------------
    # Formatting
    # -------------------------

    def _formatar_resposta(
        self,
        processo_ref: str,
        snapshot: Dict[str, Any],
        *,
        kanban: Optional[Dict[str, Any]],
        afrmm: Optional[Dict[str, Any]],
    ) -> str:
        categoria = processo_ref.split(".")[0] if "." in processo_ref else "N/A"
        out: List[str] = []
        out.append(f"📋 **Processo {processo_ref}**")
        out.append("")
        out.append(f"**Categoria:** {categoria}")

        # Importador (quando disponível no Kanban/DI)
        try:
            imp = (kanban.get("importador_nome") if kanban else None)
            if imp:
                out.append(f"**Importador:** {imp}")
        except Exception:
            pass

        # Status do processo (Kanban preferido; fallback para PROCESSO_IMPORTACAO)
        try:
            st_proc = None
            if kanban:
                sc = str(kanban.get("situacao_ce") or "").upper()
                se = str(kanban.get("situacao_entrega") or "").upper()
                if "ENTREGUE" in sc or "ENTREGUE" in se:
                    st_proc = "ENTREGUE"
                else:
                    st_proc = kanban.get("etapa_kanban")
            if not st_proc:
                st_proc = (
                    (snapshot.get("processo") or {}).get("status_processo")
                    if isinstance(snapshot.get("processo"), dict)
                    else None
                )
            if st_proc:
                out.append(f"**Status Processo:** {st_proc}")
        except Exception:
            pass
        out.append("")

        # Documentos (resumo)
        docs = snapshot.get("documentos") or []
        docs_by_tipo: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for d in docs:
            if isinstance(d, dict):
                docs_by_tipo[(d.get("tipo_documento") or "").upper()].append(d)

        # ✅ Deduplicar DUIMP pelo número (evita "v1" + "sem versão" duplicados)
        if "DUIMP" in docs_by_tipo:
            by_num: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for d in docs_by_tipo["DUIMP"]:
                num = str(d.get("numero_documento") or "").strip()
                if num:
                    by_num[num].append(d)

            deduped: List[Dict[str, Any]] = []
            for num, itens in by_num.items():
                def _score(x: Dict[str, Any]) -> Tuple[int, int, int, str]:
                    versao = x.get("versao_documento")
                    try:
                        vnum = int(versao) if versao is not None and str(versao).strip() != "" else -1
                    except Exception:
                        vnum = -1
                    has_canal = 1 if (x.get("canal_documento") or "").strip() else 0
                    has_sit = 1 if (x.get("situacao_documento") or x.get("status_documento")) else 0
                    updated = str(x.get("atualizado_em") or "")
                    return (vnum, has_canal, has_sit, updated)

                best = sorted(itens, key=_score, reverse=True)[0]
                deduped.append(best)

            # ordenar por versão/data desc
            def _ord(d: Dict[str, Any]) -> Tuple[int, str]:
                versao = d.get("versao_documento")
                try:
                    vnum = int(versao) if versao is not None and str(versao).strip() != "" else -1
                except Exception:
                    vnum = -1
                return (vnum, str(d.get("atualizado_em") or ""))

            docs_by_tipo["DUIMP"] = sorted(deduped, key=_ord, reverse=True)

        # ✅ Deduplicar DI pelo número (evita DI repetida em registros capados)
        if "DI" in docs_by_tipo:
            by_num_di: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for d in docs_by_tipo["DI"]:
                num = str(d.get("numero_documento") or "").strip()
                if num:
                    by_num_di[num].append(d)

            dedup_di: List[Dict[str, Any]] = []
            for num, itens in by_num_di.items():
                def _score_di(x: Dict[str, Any]) -> Tuple[int, int, int, str]:
                    has_canal = 1 if (x.get("canal_documento") or "").strip() else 0
                    has_sit = 1 if (x.get("situacao_documento") or x.get("status_documento")) else 0
                    has_des = 1 if x.get("data_desembaraco") else 0
                    updated = str(x.get("atualizado_em") or "")
                    return (has_des, has_canal, has_sit, updated)

                best = sorted(itens, key=_score_di, reverse=True)[0]
                dedup_di.append(best)

            docs_by_tipo["DI"] = sorted(dedup_di, key=lambda d: str(d.get("atualizado_em") or ""), reverse=True)

        if "CE" in docs_by_tipo:
            out.append("**📦 Conhecimento(s) de Embarque:**")
            for d in docs_by_tipo["CE"][:3]:
                num = d.get("numero_documento")
                sit = d.get("situacao_documento") or d.get("status_documento")
                out.append(f"  - CE {num}")
                if sit and str(sit).strip() and str(sit).strip().upper() != "N/A":
                    out.append(f"    - Situação: {sit}")
            out.append("")

        if "DI" in docs_by_tipo:
            out.append("**📄 Declaração(ões) de Importação:**")
            for d in docs_by_tipo["DI"][:3]:
                num = d.get("numero_documento")
                sit = d.get("situacao_documento") or d.get("status_documento")
                canal = _norm_canal(d.get("canal_documento"))
                dt_des = _fmt_dt(d.get("data_desembaraco"))
                out.append(f"  - DI {num}")
                if sit and str(sit).strip() and str(sit).strip().upper() != "N/A":
                    out.append(f"    - Situação: {sit}")
                if canal:
                    out.append(f"    - Canal: {canal}")
                if dt_des:
                    out.append(f"    - Desembaraçado em: {dt_des}")
            out.append("")

        if "DUIMP" in docs_by_tipo:
            out.append("**📝 DUIMP(s):**")
            for d in docs_by_tipo["DUIMP"][:3]:
                num = d.get("numero_documento")
                versao = d.get("versao_documento")
                sit = d.get("situacao_documento") or d.get("status_documento")
                canal = _norm_canal(d.get("canal_documento"))
                dt_reg = _fmt_dt(d.get("data_registro"))
                dt_sit = _fmt_dt(d.get("data_situacao"))
                vtxt = f" v{versao}" if versao not in (None, "", "None") else ""
                out.append(f"  - DUIMP {num}{vtxt}")
                if sit and str(sit).strip() and str(sit).strip().upper() != "N/A":
                    out.append(f"    - Situação: {sit}")
                if canal:
                    out.append(f"    - Canal: {canal}")
                if dt_reg:
                    out.append(f"    - Registrada em: {dt_reg}")
                if dt_sit:
                    out.append(f"    - Última atualização: {dt_sit}")
            out.append("")

        # ETA (Kanban)
        if kanban and kanban.get("eta_iso"):
            out.append("**📅 Previsão de Chegada (ETA):**")
            out.append(f"  - ETA: {_fmt_dt(kanban.get('eta_iso')) or kanban.get('eta_iso')}")
            if kanban.get("porto_nome"):
                out.append(f"  - Porto: {kanban.get('porto_nome')}")
            if kanban.get("nome_navio"):
                out.append(f"  - Navio: {kanban.get('nome_navio')}")
            if kanban.get("status_shipsgo"):
                out.append(f"  - Status: {kanban.get('status_shipsgo')}")
            out.append("")

        # Datas operacionais (Kanban): destino final / armazenagem (+ lead time)
        if kanban and (kanban.get("data_destino_final") or kanban.get("data_armazenamento")):
            out.append("🗓️ **Datas Operacionais (Kanban):**")
            if kanban.get("data_destino_final"):
                out.append(f"- Destino final: {_fmt_dt(kanban.get('data_destino_final')) or kanban.get('data_destino_final')}")
            if kanban.get("data_armazenamento"):
                out.append(f"- Armazenagem: {_fmt_dt(kanban.get('data_armazenamento')) or kanban.get('data_armazenamento')}")
            try:
                dt_eta = _try_parse_iso_date(kanban.get("eta_iso"))
                dt_arm = _try_parse_iso_date(kanban.get("data_armazenamento"))
                if dt_eta and dt_arm:
                    delta = (dt_arm.date() - dt_eta.date()).days
                    out.append(f"- Δ ETA → Armazenagem: {delta} dia(s)")
            except Exception:
                pass
            out.append("")

        # Impostos (SQL)
        impostos = snapshot.get("impostos_importacao") or []
        totals_imp: Dict[str, float] = defaultdict(float)
        for imp in impostos:
            if not isinstance(imp, dict):
                continue
            tipo = (imp.get("tipo_imposto") or "OUTROS")
            val = imp.get("valor_brl")
            try:
                v = float(val) if val is not None else 0.0
            except Exception:
                v = 0.0
            if v:
                totals_imp[tipo] += v
        if totals_imp:
            out.append("💸 **Impostos (pagos / registrados):**")
            total = 0.0
            for k in sorted(totals_imp.keys(), key=_tax_order_key):
                out.append(f"- {k}: R$ {totals_imp[k]:,.2f}")
                total += totals_imp[k]
            out.append(f"- **Total**: R$ {total:,.2f}")
            out.append("")

        # Valores (SQL)
        valores = snapshot.get("valores_mercadoria") or []
        totals_val: Dict[Tuple[str, str], float] = defaultdict(float)
        for v in valores:
            if not isinstance(v, dict):
                continue
            tipo = (v.get("tipo_valor") or "").upper()
            moeda = (v.get("moeda") or "").upper()
            val = v.get("valor")
            try:
                vf = float(val) if val is not None else 0.0
            except Exception:
                vf = 0.0
            if vf and tipo and moeda:
                totals_val[(tipo, moeda)] = max(totals_val[(tipo, moeda)], vf)
        if totals_val:
            out.append("📦 **Valores (persistidos):**")
            ordem = {"VMLD": 1, "VMLE": 2, "FOB": 3, "FRETE": 4, "SEGURO": 5}
            for (tipo, moeda) in sorted(totals_val.keys(), key=lambda k: (ordem.get(k[0], 99), k[1])):
                vf = totals_val[(tipo, moeda)]
                if moeda == "USD":
                    out.append(f"- {tipo} (USD): $ {vf:,.2f}")
                else:
                    out.append(f"- {tipo} (BRL): R$ {vf:,.2f}")
            out.append("")

        # Despesas (AFRMM + despesas bancárias quando existirem)
        despesas = snapshot.get("despesas") or []
        if afrmm or (isinstance(despesas, list) and despesas):
            out.append("💰 **Despesas:**")

            # AFRMM
            if afrmm:
                status = str(afrmm.get("status") or "").strip()
                status_txt = "✅ Pago" if status == "success" else "✅ Pago (confirmado)"
                linha = f"- AFRMM: {status_txt}"
                if afrmm.get("valor_total_debito"):
                    try:
                        linha += f" | Débito: R$ {float(afrmm.get('valor_total_debito')):,.2f}"
                    except Exception:
                        linha += f" | Débito: {afrmm.get('valor_total_debito')}"
                out.append(linha)

                # ✅ NOVO (26/01/2026): Priorizar PDF se disponível, senão usar PNG
                pdf_url = afrmm.get("pdf_url")
                screenshot_url = afrmm.get("screenshot_url")
                
                if pdf_url or screenshot_url:
                    rel = (afrmm.get("screenshot_relpath") or "").strip() or None
                    nome = None
                    if rel:
                        try:
                            # Remover extensão .png e adicionar .pdf se for PDF
                            nome_base = rel.split("/")[-1]
                            if pdf_url:
                                nome = nome_base.replace(".png", ".pdf")
                            else:
                                nome = nome_base
                        except Exception:
                            nome = None
                    
                    if pdf_url:
                        # PDF disponível - mostrar link para PDF
                        if nome:
                            out.append(f"  - 🧾 Comprovante: [{nome}]({pdf_url}) 📄")
                        else:
                            out.append(f"  - 🧾 Comprovante: [abrir PDF]({pdf_url}) 📄")
                        # Opcional: também mostrar link para PNG
                        if screenshot_url:
                            out.append(f"    - [PNG]({screenshot_url})")
                    elif screenshot_url:
                        # Apenas PNG disponível
                        if nome:
                            out.append(f"  - 🧾 Comprovante: [{nome}]({screenshot_url})")
                        else:
                            out.append(f"  - 🧾 Comprovante: [abrir PNG]({screenshot_url})")
                else:
                    # Quando não existe print/comprovante salvo, ao menos linkar o registro do pagamento
                    proc_ref = afrmm.get("processo_referencia") or processo_ref
                    ce = afrmm.get("ce_mercante") or (kanban.get("numero_ce") if kanban else None)
                    try:
                        proc_q = str(proc_ref).strip().upper()
                        ce_q = str(ce).strip() if ce else ""
                        url = f"/mercante/afrmm/pagamentos?processo={proc_q}&ce={ce_q}&limite=5"
                        out.append(f"  - 🔎 Registro: [ver detalhes]({url})")
                    except Exception:
                        pass
                    obs = (afrmm.get("observacoes") or "").strip()
                    if obs:
                        out.append(f"  - 📝 Obs.: {obs}")

            # Despesas bancárias já classificadas (se existirem)
            try:
                if isinstance(despesas, list) and despesas:
                    total = 0.0
                    itens = []
                    for d in despesas:
                        if not isinstance(d, dict):
                            continue
                        v = d.get("valor_despesa")
                        try:
                            fv = float(v) if v is not None else 0.0
                        except Exception:
                            fv = 0.0
                        if fv:
                            total += fv
                        itens.append(d)
                    out.append(f"- Outras despesas (banco): {len(itens)} lançamento(s) | Total: R$ {total:,.2f}")
            except Exception:
                pass

            out.append("")

        return "\n".join(out).strip() + "\n"

