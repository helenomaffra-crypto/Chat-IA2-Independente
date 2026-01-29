"""
Monitoramento de ocorrências para processos ativos.

MVP (19/01/2026):
- Navio em atraso (ETA passou e ainda não chegou) agrupado por navio
- SLA/tempo parado por etapa (baseado em histórico de mudanças de etapa_kanban)

Saída:
- Persiste/atualiza ocorrências em `ocorrencias_processos` (SQLite)
- Gera notificações em `notificacoes_processos` (via NotificacaoService) com anti-spam
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from db_manager import get_db_connection
from services.notificacao_service import NotificacaoService

logger = logging.getLogger(__name__)


def _parse_dt(value: Any) -> Optional[datetime]:
    """Parse robusto de datetime vindo do SQLite (str/datetime/None)."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    # Normalizar Z
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.fromisoformat(s)
    except Exception:
        pass
    # Formatos comuns
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def _now() -> datetime:
    # Usar timezone local "naive" para compatibilidade com SQLite CURRENT_TIMESTAMP.
    return datetime.now()


def _severidade_por_dias_atraso(dias: int) -> str:
    if dias >= 7:
        return "critica"
    if dias >= 3:
        return "alta"
    if dias >= 1:
        return "media"
    return "baixa"


def _sla_dias_por_etapa(etapa: str) -> Optional[float]:
    """
    SLA default (heurístico) por etapa_kanban.
    Ajustável via env MONITORAMENTO_SLA_JSON (JSON dict { "keyword": dias }).
    """
    if not etapa:
        return None
    etapa_u = etapa.upper()

    # Allow override por env (keywords)
    try:
        raw = os.getenv("MONITORAMENTO_SLA_JSON", "").strip()
        if raw:
            data = json.loads(raw)
            if isinstance(data, dict):
                for key, dias in data.items():
                    if key and str(key).upper() in etapa_u:
                        try:
                            return float(dias)
                        except Exception:
                            continue
    except Exception:
        # Ignorar override inválido
        pass

    # Defaults conservadores
    if "PARAMETR" in etapa_u:
        return 2.0
    if "REGISTR" in etapa_u:
        return 1.0
    if "LIBER" in etapa_u:
        return 1.0
    if "ARMAZEN" in etapa_u:
        return 2.0
    if "CHEG" in etapa_u or "ATRAC" in etapa_u:
        return 1.0
    if "ENTREG" in etapa_u or "RETIR" in etapa_u:
        return None
    # Default geral
    return float(os.getenv("MONITORAMENTO_SLA_DEFAULT_DIAS", "3"))


@dataclass
class ProcessoAtivoRow:
    processo_referencia: str
    etapa_kanban: str
    modal: Optional[str]
    eta_iso: Optional[datetime]
    porto_nome: Optional[str]
    nome_navio: Optional[str]
    status_shipsgo: Optional[str]
    data_destino_final: Optional[datetime]
    data_atracamento: Optional[datetime]
    data_entrega: Optional[datetime]
    atualizado_em: Optional[datetime]


class MonitoramentoOcorrenciasService:
    """Serviço de monitoramento e geração de ocorrências/notificações."""

    # Anti-spam: mínimo entre notificações para o mesmo record_key
    NOTIFY_COOLDOWN_MINUTES = int(os.getenv("MONITORAMENTO_NOTIFY_COOLDOWN_MINUTES", "360"))  # 6h

    def __init__(self) -> None:
        self.notificacao_service = NotificacaoService()

    def executar(self) -> Dict[str, Any]:
        """
        Executa monitoramento:
        - atualiza ocorrências (open/closed)
        - dispara notificações quando necessário
        """
        processos = self._listar_processos_ativos()
        now = _now()

        navios_alertados = self._processar_navios_em_atraso(processos, now)
        sla_alertados = self._processar_sla_etapa(processos, now)

        return {
            "sucesso": True,
            "total_processos": len(processos),
            "navios_alertados": navios_alertados,
            "sla_alertados": sla_alertados,
            "executado_em": now.isoformat(),
        }

    def _listar_processos_ativos(self) -> List[ProcessoAtivoRow]:
        conn = get_db_connection()
        conn.row_factory = None
        cursor = conn.cursor()

        # Heurística de "ativo": não entregue e (tem etapa/ETA/datas relevantes)
        cursor.execute(
            """
            SELECT
                processo_referencia,
                etapa_kanban,
                modal,
                eta_iso,
                porto_nome,
                nome_navio,
                status_shipsgo,
                data_destino_final,
                data_atracamento,
                data_entrega,
                atualizado_em
            FROM processos_kanban
            WHERE (situacao_entrega IS NULL OR UPPER(situacao_entrega) NOT LIKE '%ENTREG%')
              AND (data_entrega IS NULL OR TRIM(COALESCE(data_entrega,'')) = '')
            """
        )

        rows = []
        for r in cursor.fetchall():
            rows.append(
                ProcessoAtivoRow(
                    processo_referencia=r[0],
                    etapa_kanban=r[1] or "",
                    modal=r[2],
                    eta_iso=_parse_dt(r[3]),
                    porto_nome=r[4],
                    nome_navio=r[5],
                    status_shipsgo=r[6],
                    data_destino_final=_parse_dt(r[7]),
                    data_atracamento=_parse_dt(r[8]),
                    data_entrega=_parse_dt(r[9]),
                    atualizado_em=_parse_dt(r[10]),
                )
            )
        conn.close()
        return rows

    def _navio_chegou(self, p: ProcessoAtivoRow) -> bool:
        if p.data_destino_final or p.data_atracamento:
            return True
        st = (p.status_shipsgo or "").upper()
        return "ARRIV" in st or "ARRIVED" in st or "AT_BERTH" in st

    def _processar_navios_em_atraso(self, processos: List[ProcessoAtivoRow], now: datetime) -> int:
        # Agrupar processos com ETA vencida e navio ainda não chegou
        grupos: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for p in processos:
            if not p.nome_navio or not p.eta_iso:
                continue
            if self._navio_chegou(p):
                continue
            # Comparar por dia (ETA)
            eta = p.eta_iso
            if eta.date() >= now.date():
                continue
            key = (p.nome_navio.strip().upper(), (p.porto_nome or "").strip().upper())
            g = grupos.setdefault(
                key,
                {
                    "nome_navio": p.nome_navio,
                    "porto_nome": p.porto_nome,
                    "eta": eta,
                    "processos": [],
                },
            )
            g["processos"].append(p.processo_referencia)
            # Pegar a menor ETA do grupo (mais crítica)
            if eta < g["eta"]:
                g["eta"] = eta

        alertados = 0
        for (_navio_u, _porto_u), g in grupos.items():
            eta: datetime = g["eta"]
            dias = (now.date() - eta.date()).days
            severidade = _severidade_por_dias_atraso(dias)
            processos_afetados = sorted(set(g["processos"]))

            record_key = f"navio_atraso:{_navio_u}:{_porto_u}:{eta.date().isoformat()}"
            titulo = f"🚢 Navio em atraso: {g['nome_navio']} ({dias} dia(s))"
            msg = (
                f"🚢 **Navio em atraso**\n"
                f"- Navio: **{g['nome_navio']}**\n"
                f"- Porto: **{g.get('porto_nome') or 'N/A'}**\n"
                f"- ETA: **{eta.strftime('%d/%m/%Y')}**\n"
                f"- Atraso: **{dias} dia(s)**\n"
                f"- Processos impactados: **{len(processos_afetados)}**\n\n"
                f"📌 Primeiros processos: {', '.join(processos_afetados[:12])}"
            )

            dados_extras = {
                "tipo": "navio_atraso",
                "nome_navio": g["nome_navio"],
                "porto_nome": g.get("porto_nome"),
                "eta": eta.isoformat(),
                "dias_atraso": dias,
                "processos_afetados": processos_afetados,
            }

            opened_or_updated = self._upsert_ocorrencia(
                record_key=record_key,
                tipo="navio_atraso",
                severidade=severidade,
                processo_referencia=None,
                nome_navio=g["nome_navio"],
                etapa_kanban=None,
                titulo=titulo,
                mensagem=msg,
                dados_extras=dados_extras,
            )
            if opened_or_updated and self._deve_notificar(record_key, now):
                self._notificar(
                    processo_referencia="SISTEMA",
                    tipo_notificacao="navio_atraso",
                    titulo=titulo,
                    mensagem=msg,
                    dados_extras=dados_extras,
                )
                self._marcar_notificado(record_key)
                alertados += 1

        return alertados

    def _processar_sla_etapa(self, processos: List[ProcessoAtivoRow], now: datetime) -> int:
        alertados = 0
        for p in processos:
            etapa = (p.etapa_kanban or "").strip()
            if not etapa:
                continue
            sla_dias = _sla_dias_por_etapa(etapa)
            if not sla_dias:
                # Etapa sem SLA (ex: entregue/retirada)
                continue
            inicio_etapa = self._buscar_inicio_etapa(p.processo_referencia, fallback=p.atualizado_em)
            if not inicio_etapa:
                continue
            delta = now - inicio_etapa
            if delta < timedelta(days=sla_dias):
                # Se existir ocorrência aberta, encerrar
                record_key = f"sla_etapa:{p.processo_referencia}:{etapa.upper()}"
                self._fechar_ocorrencia(record_key)
                continue

            dias_parado = max(0, delta.days)
            severidade = _severidade_por_dias_atraso(dias_parado)
            record_key = f"sla_etapa:{p.processo_referencia}:{etapa.upper()}"
            titulo = f"⏱️ SLA estourado: {p.processo_referencia} ({etapa})"
            msg = (
                f"⏱️ **Tempo parado na etapa acima do SLA**\n"
                f"- Processo: **{p.processo_referencia}**\n"
                f"- Etapa: **{etapa}**\n"
                f"- Início estimado da etapa: **{inicio_etapa.strftime('%d/%m/%Y %H:%M')}**\n"
                f"- Tempo na etapa: **{delta.days} dia(s) e {delta.seconds // 3600}h**\n"
                f"- SLA (default): **{sla_dias} dia(s)**\n\n"
                f"💡 Sugestão: revisar gargalo desta etapa e pendências relacionadas."
            )
            dados_extras = {
                "tipo": "sla_etapa",
                "processo_referencia": p.processo_referencia,
                "etapa_kanban": etapa,
                "inicio_etapa": inicio_etapa.isoformat(),
                "tempo_na_etapa_segundos": int(delta.total_seconds()),
                "sla_dias": sla_dias,
            }

            opened_or_updated = self._upsert_ocorrencia(
                record_key=record_key,
                tipo="sla_etapa",
                severidade=severidade,
                processo_referencia=p.processo_referencia,
                nome_navio=p.nome_navio,
                etapa_kanban=etapa,
                titulo=titulo,
                mensagem=msg,
                dados_extras=dados_extras,
            )
            if opened_or_updated and self._deve_notificar(record_key, now):
                self._notificar(
                    processo_referencia=p.processo_referencia,
                    tipo_notificacao="sla_etapa",
                    titulo=titulo,
                    mensagem=msg,
                    dados_extras=dados_extras,
                )
                self._marcar_notificado(record_key)
                alertados += 1

        return alertados

    def _buscar_inicio_etapa(self, processo_referencia: str, fallback: Optional[datetime]) -> Optional[datetime]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT changed_at
            FROM processo_etapas_historico
            WHERE processo_referencia = ?
            ORDER BY changed_at DESC
            LIMIT 1
            """,
            (processo_referencia,),
        )
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return _parse_dt(row[0]) or fallback
        return fallback

    def _upsert_ocorrencia(
        self,
        record_key: str,
        tipo: str,
        severidade: str,
        processo_referencia: Optional[str],
        nome_navio: Optional[str],
        etapa_kanban: Optional[str],
        titulo: str,
        mensagem: str,
        dados_extras: Dict[str, Any],
    ) -> bool:
        """
        Cria ou atualiza ocorrência. Retorna True se a ocorrência está 'open' após a operação.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ocorrencias_processos (
                record_key, tipo, severidade, processo_referencia, nome_navio, etapa_kanban,
                titulo, mensagem, dados_extras, status, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(record_key) DO UPDATE SET
                tipo=excluded.tipo,
                severidade=excluded.severidade,
                processo_referencia=COALESCE(excluded.processo_referencia, ocorrencias_processos.processo_referencia),
                nome_navio=COALESCE(excluded.nome_navio, ocorrencias_processos.nome_navio),
                etapa_kanban=COALESCE(excluded.etapa_kanban, ocorrencias_processos.etapa_kanban),
                titulo=excluded.titulo,
                mensagem=excluded.mensagem,
                dados_extras=excluded.dados_extras,
                status='open',
                last_seen_at=CURRENT_TIMESTAMP
            """,
            (
                record_key,
                tipo,
                severidade,
                processo_referencia,
                nome_navio,
                etapa_kanban,
                titulo,
                mensagem,
                json.dumps(dados_extras, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()
        return True

    def _fechar_ocorrencia(self, record_key: str) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE ocorrencias_processos
            SET status='closed', last_seen_at=CURRENT_TIMESTAMP
            WHERE record_key = ? AND status = 'open'
            """,
            (record_key,),
        )
        conn.commit()
        conn.close()

    def _deve_notificar(self, record_key: str, now: datetime) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_notified_at FROM ocorrencias_processos WHERE record_key = ?",
            (record_key,),
        )
        row = cursor.fetchone()
        conn.close()
        last = _parse_dt(row[0]) if row and row[0] else None
        if not last:
            return True
        return (now - last) >= timedelta(minutes=self.NOTIFY_COOLDOWN_MINUTES)

    def _marcar_notificado(self, record_key: str) -> None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE ocorrencias_processos SET last_notified_at=CURRENT_TIMESTAMP WHERE record_key = ?",
            (record_key,),
        )
        conn.commit()
        conn.close()

    def _notificar(
        self,
        processo_referencia: str,
        tipo_notificacao: str,
        titulo: str,
        mensagem: str,
        dados_extras: Dict[str, Any],
    ) -> None:
        notif = {
            "processo_referencia": processo_referencia,
            "tipo_notificacao": tipo_notificacao,
            "titulo": titulo,
            "mensagem": mensagem,
            "dados_extras": dados_extras,
        }
        self.notificacao_service._salvar_notificacao(notif)


def get_monitoramento_ocorrencias_service() -> MonitoramentoOcorrenciasService:
    return MonitoramentoOcorrenciasService()

