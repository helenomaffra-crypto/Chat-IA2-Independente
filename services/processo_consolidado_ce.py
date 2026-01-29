import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _try_parse_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return 0.0


def processar_ces(json_consolidado: Dict[str, Any], ces: List[Dict[str, Any]]) -> None:
    """
    Processa CEs no JSON consolidado:
    - chaves (BL, manifesto, RUC, dossiê, recinto, URF)
    - legs (movimentação marítima)
    - valores (frete do CE, quando disponível)
    - carga
    - AFRMM/TUM
    - pendências/alertas básicas
    """
    for ce in ces:
        ce_numero = ce.get("numero", "")
        ce_json = ce.get("dados_completos", {}) or {}

        tipo_ce = (ce.get("tipo", "") or "").upper()
        if tipo_ce == "HOUSE":
            json_consolidado["chaves"]["ce_house"] = ce_numero
        elif tipo_ce == "MASTER":
            json_consolidado["chaves"]["ce_master"] = ce_numero

        leg: Dict[str, Any] = {
            "fonte": "CE",
            "modal": "maritimo",
            "status": {
                "situacao": ce.get("situacao", ""),
                "entrega_autorizada": ce.get("situacao") == "ENTREGUE",
                "bloqueios": {
                    "impede_entrega": ce.get("bloqueio_impede_despacho", False),
                    "impende_vinculacao": ce.get("carga_bloqueada", False),
                    "lista": [],
                },
                "afrmm_tum_pago": not ce.get("pendencia_afrmm", False),
            },
            "rota": {
                "origem_di": ce.get("porto_origem", ""),
                "origem_ce_codigo": ce.get("porto_origem", ""),
                "destino_ce_codigo": ce.get("porto_destino", ""),
                "viagem": {"id": None, "chegada_efetiva": None, "aeroporto_chegada": None},
            },
            "armazenagem": {},
            "veiculo": {},
        }

        if ce_json:
            veiculo = ce_json.get("veiculo", {}) if isinstance(ce_json, dict) else {}
            if isinstance(veiculo, dict) and veiculo:
                leg["veiculo"]["navio"] = veiculo.get("nomeNavio", "")

            armazenagem = ce_json.get("armazenagem", {}) if isinstance(ce_json, dict) else {}
            if isinstance(armazenagem, dict) and armazenagem:
                operador = armazenagem.get("operadorArmazenagem", {}) if isinstance(armazenagem.get("operadorArmazenagem"), dict) else {}
                recinto_alf = armazenagem.get("recintoAlfandegado", {}) if isinstance(armazenagem.get("recintoAlfandegado"), dict) else {}
                leg["armazenagem"]["operador"] = operador.get("nome", "")
                leg["armazenagem"]["recinto"] = recinto_alf.get("numeroRecinto", "")
                leg["armazenagem"]["setor"] = armazenagem.get("setor", "")
                leg["armazenagem"]["data_armazenagem"] = armazenagem.get("dataArmazenagem", "")

            bl = ce_json.get("numeroBL", "") if isinstance(ce_json, dict) else ""
            if bl:
                json_consolidado["chaves"]["bl"] = bl

            manifesto = ce_json.get("numeroManifesto", "") if isinstance(ce_json, dict) else ""
            if manifesto:
                json_consolidado["chaves"]["manifesto"] = manifesto

            ruc = ce_json.get("numeroRUC", "") if isinstance(ce_json, dict) else ""
            if ruc:
                json_consolidado["chaves"]["ruc"] = ruc

            dossie = ce_json.get("numeroDossie", "") if isinstance(ce_json, dict) else ""
            if dossie:
                json_consolidado["chaves"]["dossie"] = dossie

            urf_despacho = ce_json.get("urfDespacho", "") if isinstance(ce_json, dict) else ""
            if urf_despacho:
                json_consolidado["chaves"]["urf_despacho"] = urf_despacho

            recinto = ""
            if isinstance(armazenagem, dict) and armazenagem:
                recinto_alf = armazenagem.get("recintoAlfandegado", {}) if isinstance(armazenagem.get("recintoAlfandegado"), dict) else {}
                recinto = recinto_alf.get("numeroRecinto", "")
            if recinto:
                json_consolidado["chaves"]["recinto"] = recinto

            # Valores: frete do CE (se disponível)
            valor_frete_total_str = ce_json.get("valorFreteTotal", "") if isinstance(ce_json, dict) else ""
            moeda_frete_codigo = ce_json.get("moedaFrete", "") if isinstance(ce_json, dict) else ""
            if valor_frete_total_str:
                valor_frete_total = _try_parse_float(valor_frete_total_str)
                if valor_frete_total > 0:
                    json_consolidado["valores"]["frete"] = {
                        "moeda": valor_frete_total,
                        "brl": 0.0,
                        "pagamento": ce_json.get("pagamentoFrete", "") if isinstance(ce_json, dict) else "",
                        "modalidade": ce_json.get("modalidadeFrete", "") if isinstance(ce_json, dict) else "",
                        "moeda_codigo": moeda_frete_codigo,
                        "componentes": ce_json.get("componenteFrete", []) if isinstance(ce_json, dict) else [],
                        "total_moeda": valor_frete_total,
                        "total_brl": 0.0,
                    }
                    if moeda_frete_codigo:
                        json_consolidado["valores"]["moeda_codigo"] = moeda_frete_codigo

            carga_ce = ce_json.get("carga", {}) if isinstance(ce_json, dict) else {}
            if isinstance(carga_ce, dict) and carga_ce:
                json_consolidado["carga"]["descricao"] = carga_ce.get("descricaoMercadoria", "")
                json_consolidado["carga"]["ncm_principal"] = carga_ce.get("ncmPrincipal", "")
                json_consolidado["carga"]["volumes"] = carga_ce.get("quantidadeVolumes", 0)
                json_consolidado["carga"]["peso_bruto_kg"] = carga_ce.get("pesoBruto", 0.0)
                json_consolidado["carga"]["peso_liquido_kg"] = carga_ce.get("pesoLiquido", 0.0)
                json_consolidado["carga"]["cubagem_m3"] = carga_ce.get("cubagem", 0.0)

            afrmm_tum = ce_json.get("afrmmTUM", {}) if isinstance(ce_json, dict) else {}
            if isinstance(afrmm_tum, dict) and afrmm_tum:
                json_consolidado["tributos"]["afrmm_tum"]["afrmm_evento_pagamento"] = afrmm_tum.get("valorAFRMM", 0.0)
                json_consolidado["tributos"]["afrmm_tum"]["afrmm_saldo_ce"] = afrmm_tum.get("saldoAFRMM", 0.0)
                json_consolidado["tributos"]["afrmm_tum"]["tum_devida"] = afrmm_tum.get("valorTUM", 0.0)
                json_consolidado["tributos"]["afrmm_tum"]["pago"] = ce_json.get("afrmmTUMPago", False)

        json_consolidado["movimentacao"]["legs"].append(leg)

        if ce.get("pendencia_frete", False):
            json_consolidado["pendencias"]["frete"] = True
        if ce.get("pendencia_afrmm", False):
            json_consolidado["pendencias"]["afrmm"] = True

        if ce.get("carga_bloqueada", False):
            json_consolidado["alertas"].append(
                {"tipo": "bloqueio", "nivel": "error", "documento": f"CE {ce_numero}", "mensagem": "Carga bloqueada"}
            )

