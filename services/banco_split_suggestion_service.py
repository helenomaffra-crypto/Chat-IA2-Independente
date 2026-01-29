import logging
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from utils.sql_server_adapter import get_sql_adapter
from services.learned_rules_service import buscar_regras_aprendidas
from services.repositories.processo_kanban_repository import ProcessoKanbanRepository

logger = logging.getLogger(__name__)

_instance: Optional["BancoSplitSuggestionService"] = None


def get_banco_split_suggestion_service() -> "BancoSplitSuggestionService":
    global _instance
    if _instance is None:
        _instance = BancoSplitSuggestionService()
    return _instance


@dataclass
class SplitSugestao:
    processo_referencia: str
    id_tipo_despesa: Optional[int]
    valor_despesa: float
    score: float
    evidencias: List[str]


class BancoSplitSuggestionService:
    """
    Sugere um "split" de classificações para um lançamento bancário.

    ⚠️ Importante:
    - NÃO grava nada.
    - Retorna apenas sugestões (para o usuário confirmar/editar no modal).
    """

    _PROCESSO_REGEX = re.compile(r"\b[A-Z0-9]{2,4}\.\d{1,4}/\d{2}\b")
    _CATEGORIA_REGEX = re.compile(r"\b([A-Z]{2,4})\b")

    def __init__(self) -> None:
        self.sql = get_sql_adapter()
        self.proc_repo = ProcessoKanbanRepository()
        self._tipos_cache: Tuple[datetime, List[Dict[str, Any]]] = (datetime.min, [])

    def sugerir_split(
        self,
        *,
        id_movimentacao: int,
        limite_processos: int = 3,
    ) -> Dict[str, Any]:
        lanc = self._buscar_lancamento(id_movimentacao)
        if not lanc:
            return {
                "sucesso": False,
                "erro": "LANCAMENTO_NAO_ENCONTRADO",
                "mensagem": f"Lançamento {id_movimentacao} não encontrado.",
            }

        descricao = (lanc.get("descricao_movimentacao") or "").strip()
        valor_total = self._to_money_abs(lanc.get("valor_movimentacao"))

        tipos = self._listar_tipos_despesa()
        id_tipo_sugerido, evid_tipo = self._sugerir_tipo_despesa_id(descricao, tipos)

        processos_explicitos = self._extrair_processos(descricao)
        evidencias_gerais: List[str] = []

        if processos_explicitos:
            evidencias_gerais.append("processo_explicito_na_descricao")
            sugestoes = self._split_entre_processos(
                processos=processos_explicitos,
                valor_total=valor_total,
                id_tipo_despesa=id_tipo_sugerido,
                score_base=0.90,
                evidencias=evidencias_gerais + evid_tipo,
            )
            return {
                "sucesso": True,
                "tipo": "splitavel",
                "mensagem": "Sugestão baseada em processo(s) explícito(s) na descrição.",
                "lancamento": {
                    "id_movimentacao": id_movimentacao,
                    "descricao": descricao,
                    "valor_total": float(valor_total),
                },
                "sugestoes": [s.__dict__ for s in sugestoes],
            }

        # Categoria por regra aprendida (ex: Diamond -> DMD) ou por código na descrição
        categoria, evid_cat = self._inferir_categoria(descricao)
        if categoria:
            evidencias_gerais.append("categoria_inferida")
            evidencias_gerais += evid_cat
            refs = self.proc_repo.listar_referencias_por_categoria(categoria, limite=max(2, int(limite_processos)))
            if refs:
                sugestoes = self._split_entre_processos(
                    processos=refs[: max(2, int(limite_processos))],
                    valor_total=valor_total,
                    id_tipo_despesa=id_tipo_sugerido,
                    score_base=0.70,
                    evidencias=evidencias_gerais + evid_tipo,
                )
                return {
                    "sucesso": True,
                    "tipo": "splitavel",
                    "mensagem": f"Sugestão baseada em categoria '{categoria}' (processos recentes).",
                    "lancamento": {
                        "id_movimentacao": id_movimentacao,
                        "descricao": descricao,
                        "valor_total": float(valor_total),
                    },
                    "categoria": categoria,
                    "sugestoes": [s.__dict__ for s in sugestoes],
                }

        return {
            "sucesso": True,
            "tipo": "splitavel",
            "mensagem": "Não foi possível inferir processo/categoria com confiança. Selecione manualmente e/ou informe o processo na descrição.",
            "lancamento": {
                "id_movimentacao": id_movimentacao,
                "descricao": descricao,
                "valor_total": float(valor_total),
            },
            "sugestoes": [],
        }

    def _buscar_lancamento(self, id_movimentacao: int) -> Optional[Dict[str, Any]]:
        try:
            id_int = int(id_movimentacao)
        except Exception:
            return None

        query = f"""
            SELECT
                id_movimentacao,
                valor_movimentacao,
                sinal_movimentacao,
                data_movimentacao,
                descricao_movimentacao
            FROM dbo.MOVIMENTACAO_BANCARIA
            WHERE id_movimentacao = {id_int}
        """
        res = self.sql.execute_query(query, database=self.sql.database)
        if not res or not res.get("success") or not res.get("data"):
            return None
        return res["data"][0]

    def _listar_tipos_despesa(self) -> List[Dict[str, Any]]:
        # cache simples em memória por 10 minutos
        cached_at, cached = self._tipos_cache
        if cached and (datetime.now() - cached_at).total_seconds() < 600:
            return cached

        query = """
            SELECT id_tipo_despesa, nome_despesa
            FROM dbo.TIPO_DESPESA
            WHERE ativo = 1
            ORDER BY nome_despesa
        """
        res = self.sql.execute_query(query, database=self.sql.database)
        tipos = res.get("data", []) if res and res.get("success") else []
        self._tipos_cache = (datetime.now(), tipos)
        return tipos

    def _sugerir_tipo_despesa_id(self, descricao: str, tipos: List[Dict[str, Any]]) -> Tuple[Optional[int], List[str]]:
        d = (descricao or "").lower()
        if not d or not tipos:
            return None, []

        # heurística por palavras-chave
        candidatos = [
            ("afrmm", ["afrmm"]),
            ("frete", ["frete"]),
            ("seguro", ["seguro"]),
            ("armazen", ["armazen", "armazenagem"]),
            ("despach", ["despach", "despachante"]),
            ("siscomex", ["siscomex", "taxa siscomex"]),
        ]
        for key, pats in candidatos:
            if any(p in d for p in pats):
                for t in tipos:
                    nome = (t.get("nome_despesa") or "").lower()
                    if key in nome:
                        return int(t["id_tipo_despesa"]), [f"tipo_despesa_por_palavra:{key}"]
        return None, []

    def _extrair_processos(self, descricao: str) -> List[str]:
        encontrados = self._PROCESSO_REGEX.findall((descricao or "").upper())
        # manter ordem, remover duplicatas
        seen = set()
        out = []
        for p in encontrados:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def _inferir_categoria(self, descricao: str) -> Tuple[Optional[str], List[str]]:
        d = (descricao or "").strip().lower()
        if not d:
            return None, []

        # 1) regras aprendidas cliente_categoria (Diamond -> DMD)
        try:
            regras = buscar_regras_aprendidas(tipo_regra="cliente_categoria", ativas=True)
        except Exception:
            regras = []

        mapeamento: Dict[str, str] = {}
        for regra in regras or []:
            nome_regra = (regra.get("nome_regra") or "").lower()
            descricao_regra = (regra.get("descricao") or "").lower()
            aplicacao_texto = (regra.get("aplicacao_texto") or "").lower()
            blob = f"{nome_regra} {descricao_regra} {aplicacao_texto}"
            m = re.search(r"([a-záàâãéèêíìîóòôõúùûç0-9\\s]+)\\s*[→=]\\s*([a-z]{2,4})", blob)
            if m:
                termo = m.group(1).strip()
                cat = m.group(2).strip().upper()
                if termo and cat:
                    mapeamento[termo] = cat

        for termo, cat in mapeamento.items():
            if termo and termo in d and self.proc_repo.existe_categoria(cat):
                return cat, [f"regra_aprendida:{termo}->{cat}"]

        # 2) código direto (ex: DMD) validado contra processos_kanban
        for m in self._CATEGORIA_REGEX.finditer(descricao.upper()):
            cat = (m.group(1) or "").upper()
            if self.proc_repo.existe_categoria(cat):
                return cat, [f"categoria_no_texto:{cat}"]

        return None, []

    def _split_entre_processos(
        self,
        *,
        processos: List[str],
        valor_total: Decimal,
        id_tipo_despesa: Optional[int],
        score_base: float,
        evidencias: List[str],
    ) -> List[SplitSugestao]:
        if not processos:
            return []

        n = len(processos)
        # divisão igualitária com ajuste no último item (garante soma exata)
        valor_unit = (valor_total / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        valores = [valor_unit] * n
        soma = sum(valores)
        diff = (valor_total - soma).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        valores[-1] = (valores[-1] + diff).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        sugestoes: List[SplitSugestao] = []
        for i, proc in enumerate(processos):
            sugestoes.append(
                SplitSugestao(
                    processo_referencia=proc,
                    id_tipo_despesa=id_tipo_despesa,
                    valor_despesa=float(valores[i]),
                    score=max(0.0, min(1.0, score_base - (i * 0.03))),
                    evidencias=list(evidencias),
                )
            )
        return sugestoes

    def _to_money_abs(self, valor: Any) -> Decimal:
        try:
            d = Decimal(str(valor).replace(",", "."))
        except Exception:
            d = Decimal("0")
        if d < 0:
            d = -d
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

