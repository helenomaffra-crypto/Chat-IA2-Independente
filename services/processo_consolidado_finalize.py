import logging
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _safe_get(d: Any, *keys: str, default: Any = "") -> Any:
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


def finalizar_consolidado(
    json_consolidado: Dict[str, Any],
    *,
    ces: List[Dict[str, Any]],
    ccts: List[Dict[str, Any]],
) -> None:
    """
    Finaliza o JSON consolidado:
    - timeline
    - semantica (resumo_pt, keyphrases, entities)
    - meta.closed
    """
    # Timeline
    legs = _safe_get(json_consolidado, "movimentacao", "legs", default=[])
    if isinstance(legs, list) and legs:
        primeiro_leg = legs[0]
        ultimo_leg = legs[-1]
        json_consolidado["timeline"]["embarque"] = _safe_get(primeiro_leg, "rota", "origem_ce_codigo", default="")
        json_consolidado["timeline"]["chegada"] = _safe_get(ultimo_leg, "rota", "viagem", "chegada_efetiva", default="")
        json_consolidado["timeline"]["armazenagem"] = _safe_get(ultimo_leg, "armazenagem", "data_armazenagem", default="")

    declaracao = json_consolidado.get("declaracao")
    if isinstance(declaracao, dict):
        datas = declaracao.get("datas", {}) if isinstance(declaracao.get("datas"), dict) else {}
        json_consolidado["timeline"]["registro_declaracao"] = datas.get("registro", "")
        json_consolidado["timeline"]["desembaraco"] = datas.get("desembaraco", "")

    # Semântica
    resumo_parts: List[str] = []
    keyphrases: List[str] = []
    entities_cnpjs: Set[str] = set()
    entities_ids: Set[str] = set()

    if isinstance(declaracao, dict):
        tipo_decl = declaracao.get("tipo", "")
        situacao_decl = declaracao.get("situacao", "")
        canal = declaracao.get("canal", "")
        situacao_lower = str(situacao_decl).lower() if situacao_decl else ""

        if tipo_decl == "DI":
            resumo_parts.append(f"DI {json_consolidado.get('chaves', {}).get('di', 'N/A')} {situacao_lower}")
        elif tipo_decl == "DUIMP":
            resumo_parts.append(f"DUIMP {json_consolidado.get('chaves', {}).get('duimp_num', 'N/A')} {situacao_lower}")

        if canal:
            resumo_parts.append(f"(canal {canal})")
            keyphrases.append(f"canal {canal}")

    chaves = json_consolidado.get("chaves", {}) if isinstance(json_consolidado.get("chaves"), dict) else {}
    ce_house = chaves.get("ce_house")
    if ce_house:
        resumo_parts.append(f"CE {ce_house}")
        entities_ids.add(str(ce_house))
        for leg in legs if isinstance(legs, list) else []:
            if isinstance(leg, dict) and leg.get("fonte") == "CE":
                situacao_ce = _safe_get(leg, "status", "situacao", default="")
                if situacao_ce:
                    resumo_parts.append(str(situacao_ce))
                    keyphrases.append(str(situacao_ce))

    pendencias = json_consolidado.get("pendencias", {}) if isinstance(json_consolidado.get("pendencias"), dict) else {}
    if pendencias.get("frete"):
        resumo_parts.append("pendência de frete")
        keyphrases.append("pendência de frete")
    if pendencias.get("afrmm"):
        resumo_parts.append("pendência AFRMM")
        keyphrases.append("pendência AFRMM")

    valores = json_consolidado.get("valores", {}) if isinstance(json_consolidado.get("valores"), dict) else {}
    cif = valores.get("cif") if isinstance(valores.get("cif"), dict) else None
    if isinstance(cif, dict):
        cif_brl = cif.get("brl", 0) or 0
        try:
            cif_brl_num = float(cif_brl)
        except Exception:
            cif_brl_num = 0.0
        if cif_brl_num > 0:
            resumo_parts.append(f"CIF {cif_brl_num:,.2f} BRL")
            keyphrases.append(f"CIF {cif_brl_num:,.2f}")

    json_consolidado["semantica"]["resumo_pt"] = ". ".join([p for p in resumo_parts if p])
    json_consolidado["semantica"]["keyphrases"] = list(set([p for p in keyphrases if p]))

    for ce in ces:
        cnpj = ce.get("cpf_cnpj_consignatario")
        if cnpj:
            entities_cnpjs.add(str(cnpj))
    for cct in ccts:
        cnpj = cct.get("identificacao_documento_consignatario")
        if cnpj:
            entities_cnpjs.add(str(cnpj))

    importador_cnpj = _safe_get(declaracao, "partes", "importador", "cnpj", default="")
    if importador_cnpj:
        entities_cnpjs.add(str(importador_cnpj))

    if chaves.get("di"):
        entities_ids.add(str(chaves.get("di")))
    if chaves.get("duimp_num"):
        entities_ids.add(str(chaves.get("duimp_num")))
    if chaves.get("bl"):
        entities_ids.add(str(chaves.get("bl")))
    if chaves.get("manifesto"):
        entities_ids.add(str(chaves.get("manifesto")))

    json_consolidado["semantica"]["entities"]["cnpjs"] = list(entities_cnpjs)
    json_consolidado["semantica"]["entities"]["ids"] = list(entities_ids)

    # Determinar se processo está fechado
    if isinstance(declaracao, dict):
        situacao = declaracao.get("situacao")
        if situacao in ["DI_DESEMBARACADA", "DUIMP_REGISTRADA"]:
            json_consolidado["meta"]["closed"] = True

