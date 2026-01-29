import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _try_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        try:
            return float(str(value).replace(",", "."))
        except Exception:
            return 0.0


def processar_duimps_producao(json_consolidado: Dict[str, Any], duimps: List[Dict[str, Any]], *, processo_referencia: str) -> None:
    """
    Processa DUIMPs no JSON consolidado (somente PRODUÇÃO):
    - Filtra DUIMP de validação
    - Define DUIMP como declaração principal
    - Extrai importador, CIF, infere FOB (quando há frete + câmbio implícito), e tributos calculados
    """
    duimps_producao: List[Dict[str, Any]] = []
    for d in duimps:
        ambiente_raw = d.get("ambiente", "") or ""
        ambiente_norm = str(ambiente_raw).strip().lower()
        vinda_do_ce = bool(d.get("vinda_do_ce", False))
        if vinda_do_ce or ambiente_norm in ("producao", "produção"):
            duimps_producao.append(d)

    for duimp in duimps_producao:
        duimp_numero = duimp.get("numero_duimp", "")
        duimp_versao = duimp.get("versao_duimp", "")
        duimp_json = duimp.get("dados_completos", {}) or {}

        ambiente_duimp = str(duimp.get("ambiente", "") or "").strip().lower()
        if ambiente_duimp == "validacao" and not duimp.get("vinda_do_ce", False):
            logger.debug(
                f"⚠️ Processo {processo_referencia}: DUIMP {duimp_numero} é de validação, ignorando no JSON consolidado"
            )
            continue

        if duimp_numero:
            json_consolidado["chaves"]["duimp_num"] = duimp_numero
            json_consolidado["chaves"]["duimp_versao"] = duimp_versao

        if not isinstance(duimp_json, dict) or not duimp_json:
            continue

        duimp_declaracao: Dict[str, Any] = {
            "tipo": "DUIMP",
            "situacao": duimp.get("situacao_duimp", ""),
            "canal": duimp.get("canal_consolidado", ""),
            "modalidade": "NORMAL",
            "datas": {
                "registro": duimp.get("data_registro", ""),
                "desembaraco": None,
                "autorizacao_entrega": None,
                "situacao_atualizada_em": duimp.get("atualizado_em", ""),
            },
            "icms": {},
            "partes": {},
            "documentos_relacionados": {},
            "observacoes": {},
        }

        json_consolidado["declaracoes"].append(duimp_declaracao)
        json_consolidado["declaracao"] = duimp_declaracao

        partes = duimp_json.get("partes", {})
        if isinstance(partes, dict) and partes:
            importador = partes.get("importador", {})
            if isinstance(importador, dict) and importador:
                identificacao = importador.get("identificacao", {}) if isinstance(importador.get("identificacao"), dict) else {}
                duimp_declaracao["partes"]["importador"] = {
                    "nome": importador.get("nome", ""),
                    "cnpj": identificacao.get("numero", ""),
                }
                json_consolidado["declaracao"]["partes"]["importador"] = duimp_declaracao["partes"]["importador"]

        tributos_duimp = duimp_json.get("tributos", {})
        if not isinstance(tributos_duimp, dict) or not tributos_duimp:
            continue

        mercadoria = tributos_duimp.get("mercadoria", {})
        if isinstance(mercadoria, dict) and mercadoria:
            valor_cif_brl = _try_float(mercadoria.get("valorTotalLocalEmbarqueBRL", 0.0))
            valor_cif_usd = _try_float(mercadoria.get("valorTotalLocalEmbarqueUSD", 0.0))

            if valor_cif_brl > 0:
                json_consolidado["valores"]["cif"] = {"moeda": valor_cif_usd, "brl": valor_cif_brl}

                frete_info = json_consolidado["valores"].get("frete", {}) if isinstance(json_consolidado.get("valores"), dict) else {}
                frete_moeda = _try_float(frete_info.get("moeda", 0)) if isinstance(frete_info, dict) else 0.0
                frete_moeda_codigo = frete_info.get("moeda_codigo", "") if isinstance(frete_info, dict) else ""

                if frete_moeda > 0 and valor_cif_usd > 0 and valor_cif_brl > 0:
                    taxa_cambio = valor_cif_brl / valor_cif_usd if valor_cif_usd > 0 else 0.0
                    if taxa_cambio > 0 and isinstance(frete_info, dict):
                        frete_brl = frete_moeda * taxa_cambio
                        json_consolidado["valores"]["frete"]["brl"] = frete_brl
                        json_consolidado["valores"]["frete"]["total_brl"] = frete_brl

                        seguro_brl = 0.0
                        seguro = json_consolidado["valores"].get("seguro", {}) if isinstance(json_consolidado.get("valores"), dict) else {}
                        if isinstance(seguro, dict):
                            seguro_brl = _try_float(seguro.get("brl", 0))

                        fob_brl = valor_cif_brl - frete_brl - seguro_brl
                        if fob_brl > 0:
                            frete_usd = frete_moeda if frete_moeda_codigo == "220" else 0.0
                            seguro_usd = _try_float(seguro.get("moeda", 0)) if isinstance(seguro, dict) else 0.0
                            fob_usd = valor_cif_usd - frete_usd - seguro_usd
                            json_consolidado["valores"]["fob"] = {
                                "moeda": fob_usd if fob_usd > 0 else (valor_cif_usd - frete_usd),
                                "brl": fob_brl,
                                "calculado": True,
                            }

        tributos_calculados = tributos_duimp.get("tributosCalculados", [])
        if isinstance(tributos_calculados, list):
            for tributo in tributos_calculados:
                if not isinstance(tributo, dict):
                    continue
                tipo_tributo = tributo.get("tipo", "")
                valores_brl = tributo.get("valoresBRL", {}) if isinstance(tributo.get("valoresBRL"), dict) else {}
                valor_recolhido = _try_float(valores_brl.get("recolhido", 0.0))
                if valor_recolhido and valor_recolhido > 0:
                    json_consolidado["tributos"]["sumario"]["total_brl"] += valor_recolhido

                    descricao_tributo = {
                        "II": "Imposto de Importação",
                        "IPI": "Imposto sobre Produtos Industrializados",
                        "PIS": "Programa de Integração Social",
                        "COFINS": "Contribuição para o Financiamento da Seguridade Social",
                        "ICMS": "Imposto sobre Circulação de Mercadorias e Serviços",
                        "TAXA_UTILIZACAO": "Taxa de Utilização",
                    }.get(tipo_tributo, tipo_tributo)

                    json_consolidado["tributos"]["pagamentos"].append(
                        {"receita": tipo_tributo, "descricao": descricao_tributo, "data": None, "valor_brl": valor_recolhido}
                    )

