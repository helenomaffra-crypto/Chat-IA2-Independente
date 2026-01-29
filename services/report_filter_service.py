"""
ReportFilterService: filtros determinísticos em relatórios JSON salvos.

Objetivo: permitir follow-ups rápidos ("só canal verde", "só pendências de frete", "atraso > 7 dias")
sem depender de nova consulta ao SQL Server e sem inflar `ProcessoAgent`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def _norm_str(v: Any) -> str:
    return str(v).strip().lower() if v is not None else ""


def filtrar_secao_relatorio(
    secao: str,
    dados_secao: Any,
    *,
    canal: Optional[str] = None,
    tipo_pendencia: Optional[str] = None,
    tipo_mudanca: Optional[str] = None,
    min_dias: Optional[int] = None,
    status_contains: Optional[str] = None,
    min_age_dias: Optional[int] = None,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Filtra uma seção do relatório (quando aplicável).

    Args:
        secao: Nome da seção (ex.: 'dis_analise', 'pendencias', 'eta_alterado')
        dados_secao: Conteúdo da seção (tipicamente list[dict])
        canal: Filtro de canal ('Verde'/'Vermelho') para DIs/DUIMPs
        tipo_pendencia: Filtro de pendência (ex.: 'Frete', 'ICMS', 'AFRMM', 'LPCO', 'Bloqueio CE')
        tipo_mudanca: Filtro de ETA alterado ('ATRASO'/'ADIANTADO')
        min_dias: Filtro numérico (ex.: atraso > 7 dias)

    Returns:
        (dados_filtrados, filtros_aplicados)
    """
    filtros_aplicados: Dict[str, Any] = {}

    if not isinstance(secao, str) or not secao:
        return dados_secao, filtros_aplicados

    secao_norm = secao.strip().lower()
    canal_norm = _norm_str(canal)
    tipo_pend_norm = _norm_str(tipo_pendencia)
    tipo_mud_norm = _norm_str(tipo_mudanca)
    status_norm = _norm_str(status_contains)

    if secao_norm in ("dis_analise", "duimps_analise"):
        if canal_norm:
            filtros_aplicados["canal"] = canal
        if status_norm:
            filtros_aplicados["status_contains"] = status_contains
        if min_age_dias is not None:
            filtros_aplicados["min_age_dias"] = min_age_dias
        if not isinstance(dados_secao, list):
            return dados_secao, filtros_aplicados
        if not canal_norm and not status_norm and min_age_dias is None:
            return dados_secao, filtros_aplicados

        def _get_canal(item: Dict[str, Any]) -> str:
            # DI usa canal_di; DUIMP usa canal_duimp (mas pode vir 'canal')
            return _norm_str(
                item.get("canal_di")
                or item.get("canal_duimp")
                or item.get("canal")
            )

        def _get_status(item: Dict[str, Any]) -> str:
            # DI tende a ter 'situacao_di'; DUIMP tende a ter 'status'
            return _norm_str(
                item.get("situacao_di")
                or item.get("status")
                or item.get("situacao")
            )

        def _get_idade_dias(item: Dict[str, Any]) -> Optional[int]:
            # Preferir tempo_analise se vier como "X dia(s)" ou "hoje"
            ta = _norm_str(item.get("tempo_analise"))
            if ta == "hoje":
                return 0
            if ta:
                import re
                m = re.search(r'(\d{1,4})\s*dia', ta)
                if m:
                    try:
                        return int(m.group(1))
                    except Exception:
                        return None
            return None

        filtrados = []
        for it in dados_secao:
            if not isinstance(it, dict):
                continue

            if canal_norm and _get_canal(it) != canal_norm:
                continue

            if status_norm and status_norm not in _get_status(it):
                continue

            if min_age_dias is not None:
                idade = _get_idade_dias(it)
                if idade is None or idade < int(min_age_dias):
                    continue

            filtrados.append(it)

        return filtrados, filtros_aplicados

    if secao_norm == "pendencias":
        if tipo_pend_norm:
            filtros_aplicados["tipo_pendencia"] = tipo_pendencia
        if not isinstance(dados_secao, list):
            return dados_secao, filtros_aplicados
        if not tipo_pend_norm:
            return dados_secao, filtros_aplicados
        filtrados = [
            it for it in dados_secao
            if isinstance(it, dict) and _norm_str(it.get("tipo_pendencia")) == tipo_pend_norm
        ]
        return filtrados, filtros_aplicados

    if secao_norm == "eta_alterado":
        if tipo_mud_norm:
            filtros_aplicados["tipo_mudanca"] = tipo_mudanca
        if min_dias is not None:
            filtros_aplicados["min_dias"] = min_dias
        if not isinstance(dados_secao, list):
            return dados_secao, filtros_aplicados

        filtrados: List[Dict[str, Any]] = []
        for it in dados_secao:
            if not isinstance(it, dict):
                continue
            tm = _norm_str(it.get("tipo_mudanca"))
            dias = it.get("dias_diferenca")
            try:
                dias_int = int(dias) if dias is not None else None
            except Exception:
                dias_int = None

            if tipo_mud_norm and tm != tipo_mud_norm:
                continue

            if min_dias is not None:
                # Para atraso usamos dias_diferenca > 0; para adiantado < 0. Aqui aplicamos por módulo.
                if dias_int is None or abs(dias_int) < int(min_dias):
                    continue

            filtrados.append(it)

        return filtrados, filtros_aplicados

    return dados_secao, filtros_aplicados

