import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def processar_dis(json_consolidado: Dict[str, Any], dis: List[Dict[str, Any]]) -> None:
    """
    Processa DIs no JSON consolidado:
    - chaves (DI)
    - declaracoes (DI)
    - declaracao principal (se ainda não houver)
    - partes, icms e tributos/pagamentos (quando presentes no payload)
    """
    for di in dis:
        di_numero = di.get("numero_di", "")
        di_json = di.get("dados_completos", {}) or {}

        if di_numero:
            json_consolidado["chaves"]["di"] = di_numero

        dados_despacho = di_json.get("dadosDespacho", {}) if isinstance(di_json, dict) else {}
        modalidade_despacho = dados_despacho.get("modalidadeDespacho", "NORMAL") if isinstance(dados_despacho, dict) else "NORMAL"
        data_hora_autorizacao_entrega = (
            dados_despacho.get("dataHoraAutorizacaoEntrega") if isinstance(dados_despacho, dict) else None
        )

        di_declaracao: Dict[str, Any] = {
            "tipo": "DI",
            "situacao": di.get("situacao_di", ""),
            "canal": di.get("canal_selecao_parametrizada", ""),
            "modalidade": modalidade_despacho,
            "numero_protocolo": di.get("numero_protocolo", ""),
            "situacao_entrega_carga": di.get("situacao_entrega_carga", ""),
            "datas": {
                "registro": di.get("data_hora_registro", ""),
                "desembaraco": di.get("data_hora_desembaraco", ""),
                "autorizacao_entrega": data_hora_autorizacao_entrega,
                "situacao_atualizada_em": di.get("data_hora_situacao_di", ""),
            },
            "icms": {},
            "partes": {},
            "documentos_relacionados": {},
            "observacoes": {},
        }

        json_consolidado["declaracoes"].append(di_declaracao)

        if not json_consolidado.get("declaracao"):
            json_consolidado["declaracao"] = di_declaracao

        if not isinstance(di_json, dict) or not di_json:
            continue

        partes = di_json.get("partes", {})
        if isinstance(partes, dict) and partes:
            importador = partes.get("importador", {})
            if isinstance(importador, dict) and importador:
                identificacao = importador.get("identificacao", {}) if isinstance(importador.get("identificacao"), dict) else {}
                di_declaracao["partes"]["importador"] = {
                    "nome": importador.get("nome", ""),
                    "cnpj": identificacao.get("numero", ""),
                }
                if json_consolidado.get("declaracao") == di_declaracao:
                    json_consolidado["declaracao"]["partes"]["importador"] = di_declaracao["partes"]["importador"]

            encomendante = partes.get("encomendante", {})
            if isinstance(encomendante, dict) and encomendante:
                identificacao = encomendante.get("identificacao", {}) if isinstance(encomendante.get("identificacao"), dict) else {}
                di_declaracao["partes"]["encomendante_ou_adquirente"] = {
                    "nome": encomendante.get("nome", ""),
                    "cnpj": identificacao.get("numero", ""),
                }
                if json_consolidado.get("declaracao") == di_declaracao:
                    json_consolidado["declaracao"]["partes"]["encomendante_ou_adquirente"] = di_declaracao["partes"][
                        "encomendante_ou_adquirente"
                    ]

        icms = di_json.get("icms", {})
        if isinstance(icms, dict) and icms:
            di_declaracao["icms"] = {
                "uf": icms.get("uf", ""),
                "tipo_recolhimento": icms.get("tipoRecolhimento", ""),
                "valor_brl": icms.get("valor", 0.0),
                "data_registro": icms.get("dataRegistro", ""),
            }
            json_consolidado["tributos"]["sumario"]["icms"] = {
                "uf": icms.get("uf", ""),
                "tipo_recolhimento": icms.get("tipoRecolhimento", ""),
                "valor_brl": icms.get("valor", 0.0),
            }
            if json_consolidado.get("declaracao") == di_declaracao:
                json_consolidado["declaracao"]["icms"] = di_declaracao["icms"]

        tributos = di_json.get("tributos", {})
        if isinstance(tributos, dict) and tributos:
            pagamentos = tributos.get("pagamentos", [])
            if isinstance(pagamentos, list):
                for pagamento in pagamentos:
                    if not isinstance(pagamento, dict):
                        continue
                    receita = pagamento.get("receita", {}) if isinstance(pagamento.get("receita"), dict) else {}
                    valor = pagamento.get("valor", 0.0)
                    json_consolidado["tributos"]["pagamentos"].append(
                        {
                            "receita": receita.get("codigo", ""),
                            "descricao": receita.get("descricao", ""),
                            "data": pagamento.get("dataPagamento", ""),
                            "valor_brl": valor,
                        }
                    )
                    try:
                        json_consolidado["tributos"]["sumario"]["total_brl"] += valor or 0.0
                    except Exception:
                        pass

