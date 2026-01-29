"""
VendasMakeService
-----------------
Consulta "vendas" no SQL Server legado (Make/Spalla) com foco em uso pelo chat,
de forma independente (sem o usuário acessar o BD diretamente).

Objetivo de negócio:
- "Quanto vendi de alho em janeiro?"
- "Quanto vendemos de rastreador hoje / por período?"

Estratégia:
- Consulta determinística por período + filtros textuais (termo) em campos disponíveis
- Agrupamentos simples (mês/dia + centro de custo + tipo de operação)
- Heurística de "o que é venda" configurável por parâmetros (TD_DES contém ...)

⚠️ Observação: Este service assume conectividade ao SQL Server (rede/VPN). Quando indisponível,
retorna erro claro e não tenta fallback para SQLite, pois os dados de vendas estão no legado.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from utils.sql_server_adapter import get_sql_adapter

logger = logging.getLogger(__name__)


def _escape_sql_literal(value: str) -> str:
    return (value or "").replace("'", "''")

def _qident(name: str) -> str:
    """
    Quote de identificador SQL Server com colchetes.
    """
    s = (name or "").strip()
    if not s:
        return ""
    return "[" + s.replace("]", "]]") + "]"


def _coerce_date_yyyy_mm_dd(s: str) -> Optional[str]:
    """
    Aceita 'YYYY-MM-DD' e retorna igual.
    Retorna None se inválido.
    """
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return None
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        return None


def _normalize_search_text(s: str) -> str:
    """
    Normaliza texto para busca "best-effort":
    - lower
    - remove acentos
    - troca separadores por espaço
    """
    if not s or not isinstance(s, str):
        return ""
    s = s.strip().lower()
    # remover acentos
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    # normalizar separadores comuns
    s = re.sub(r"[\-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize_search_terms(termo: Optional[str], *, max_terms: int = 6) -> List[str]:
    """
    Quebra um termo livre em tokens para LIKE.
    Ex.: "alho chines" -> ["alho", "chines"]
    """
    t = _normalize_search_text(termo or "")
    if not t:
        return []
    # correções bem pequenas de typos muito comuns (sem tentar "IA")
    t = t.replace("alhno", "alho")
    tokens = [p.strip() for p in t.split(" ") if p.strip()]
    # remover tokens muito curtos
    tokens = [x for x in tokens if len(x) >= 2]
    return tokens[:max_terms]


def _build_term_variants(termo: Optional[str]) -> List[List[str]]:
    """
    Gera variantes de busca para termos "colados" / typos comuns.
    Ex:
      - hikvision -> ["hikvision"] e ["hik","vision"] e ["cftv"]
      - hackvision -> ["hikvision"] e ["hik","vision"]
    """
    raw = (termo or "").strip()
    norm = _normalize_search_text(raw)
    base = _tokenize_search_terms(raw)

    variants: List[List[str]] = []
    if base:
        variants.append(base)

    # typos comuns
    if norm in ("hackvision", "hack-vision"):
        variants.append(["hikvision"])
        variants.append(["hik", "vision"])
        # typo visto no legado
        variants.append(["hikvison"])

    # typo: "hakvision" (sem o i)
    if norm in ("hakvision", "hak-vision"):
        variants.append(["hikvision"])
        variants.append(["hik", "vision"])
        variants.append(["hikvison"])

    if norm == "hikvision":
        variants.append(["hik", "vision"])
        variants.append(["cftv"])
        # typo visto no legado (sem o segundo "i")
        variants.append(["hikvison"])

    # se o termo sugere hik + vision, também tentar o typo comum
    if ("hik" in norm) and ("vision" in norm):
        variants.append(["hikvison"])

    # heurística simples: termo colado que termina com "vision" -> separar prefixo + vision
    if norm and " " not in norm and norm.endswith("vision") and len(norm) > 8:
        prefix = norm[: -len("vision")]
        prefix = prefix.strip()
        if prefix and len(prefix) >= 2:
            variants.append([prefix, "vision"])

    # dedupe mantendo ordem
    seen = set()
    out: List[List[str]] = []
    for v in variants:
        key = tuple(v)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def _month_range_from_yyyy_mm(yyyy_mm: str) -> Optional[Tuple[str, str]]:
    if not yyyy_mm or not isinstance(yyyy_mm, str):
        return None
    yyyy_mm = yyyy_mm.strip()
    if not re.match(r"^\d{4}-\d{2}$", yyyy_mm):
        return None
    try:
        y, m = yyyy_mm.split("-")
        y_i = int(y)
        m_i = int(m)
        start = date(y_i, m_i, 1)
        if m_i == 12:
            end = date(y_i + 1, 1, 1)
        else:
            end = date(y_i, m_i + 1, 1)
        return (start.isoformat(), end.isoformat())
    except Exception:
        return None


@dataclass
class VendasMakeQuery:
    sql: str
    database: Optional[str] = "Make"


class VendasMakeService:
    """
    Serviço de consulta de vendas no legado Make/Spalla.
    """

    def __init__(self) -> None:
        self._adapter = get_sql_adapter()

    def is_ready(self) -> bool:
        return self._adapter is not None

    def _run_query(self, sql: str, database: Optional[str]) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        if not self._adapter:
            return None, "SQL adapter indisponível (pyodbc/node não encontrados)."

        result = self._adapter.execute_query(sql, database=database) if database else self._adapter.execute_query(sql)
        if not isinstance(result, dict) or not result.get("success"):
            return None, (result.get("error") if isinstance(result, dict) else None) or "erro_desconhecido"

        data = result.get("data") or []
        if isinstance(data, list):
            return data, None
        if isinstance(data, dict):
            return [data], None
        return [{"value": data}], None

    def _listar_colunas_spalla(self, table: str) -> Tuple[List[str], Optional[str]]:
        """
        Lista colunas de uma tabela em `spalla` sem depender do DB atual da conexão.
        """
        table = (table or "").strip()
        if not table:
            return [], "tabela_vazia"
        # table no formato "dbo.documentos"
        if "." not in table:
            schema = "dbo"
            name = table
        else:
            schema, name = table.split(".", 1)
        sql = f"""
SELECT c.name AS coluna
FROM spalla.sys.columns c
JOIN spalla.sys.objects o ON o.object_id = c.object_id
JOIN spalla.sys.schemas s ON s.schema_id = o.schema_id
WHERE o.type = 'U'
  AND s.name = '{_escape_sql_literal(schema)}'
  AND o.name = '{_escape_sql_literal(name)}'
ORDER BY c.column_id;
""".strip()
        rows, err = self._run_query(sql, database="Make")
        if err:
            rows, err = self._run_query(sql, database=None)
        if err:
            return [], err
        cols = []
        for r in rows or []:
            if isinstance(r, dict) and r.get("coluna"):
                cols.append(str(r.get("coluna")))
        return cols, None

    def _find_cliente_join_candidate(self) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Tenta descobrir uma tabela de cadastro (cliente/pessoa/parceiro) no legado contendo:
        - uma coluna ID (codigo_cliente/codigo_pessoa/codigo_parceiro/...)
        - uma coluna nome/razao_social

        Retorna dict com {schema, table, id_col, name_col} (best-effort).
        """
        # conjuntos (lowercase) para detectar colunas prováveis
        id_cols = [
            "codigo_cliente",
            "cod_cliente",
            "cliente_codigo",
            "cliente_id",
            "codigo_parceiro",
            "cod_parceiro",
            "parceiro_codigo",
            "parceiro_id",
            "codigo_pessoa",
            "cod_pessoa",
            "pessoa_codigo",
            "pessoa_id",
        ]
        name_cols = [
            "nome_cliente",
            "cliente_nome",
            "razao_social",
            "nome",
            "nome_pessoa",
            "pessoa_nome",
            "nome_parceiro",
            "parceiro_nome",
            "nm_cliente",
            "nm_pessoa",
        ]

        ids_in = ", ".join(f"'{_escape_sql_literal(c)}'" for c in id_cols)
        names_in = ", ".join(f"'{_escape_sql_literal(c)}'" for c in name_cols)

        def _query_for_db(db: str) -> str:
            # `INFORMATION_SCHEMA` depende do DB prefixado
            return f"""
WITH cols AS (
    SELECT
        c.TABLE_SCHEMA AS schema_name,
        c.TABLE_NAME AS table_name,
        MAX(CASE WHEN LOWER(c.COLUMN_NAME) IN ({ids_in}) THEN c.COLUMN_NAME END) AS id_col,
        MAX(CASE WHEN LOWER(c.COLUMN_NAME) IN ({names_in}) THEN c.COLUMN_NAME END) AS name_col
    FROM {db}.INFORMATION_SCHEMA.COLUMNS c
    WHERE LOWER(c.COLUMN_NAME) IN ({ids_in}, {names_in})
    GROUP BY c.TABLE_SCHEMA, c.TABLE_NAME
),
ranked AS (
    SELECT
        schema_name,
        table_name,
        id_col,
        name_col,
        CASE
            WHEN LOWER(table_name) LIKE '%cliente%' THEN 0
            WHEN LOWER(table_name) LIKE '%pessoa%' THEN 1
            WHEN LOWER(table_name) LIKE '%parceiro%' THEN 2
            WHEN LOWER(table_name) LIKE '%cad%' THEN 3
            ELSE 9
        END AS score
    FROM cols
    WHERE id_col IS NOT NULL AND name_col IS NOT NULL
)
SELECT TOP 1 schema_name, table_name, id_col, name_col
FROM ranked
ORDER BY score, table_name;
""".strip()

        # procurar primeiro em spalla, depois em Make
        for db in ("spalla", "Make"):
            sql = _query_for_db(db)
            rows, err = self._run_query(sql, database="Make")
            if err:
                rows, err = self._run_query(sql, database=None)
            if err:
                continue
            if not rows:
                continue
            r0 = rows[0] if isinstance(rows[0], dict) else {}
            schema_name = (r0.get("schema_name") or "").strip()
            table_name = (r0.get("table_name") or "").strip()
            id_col = (r0.get("id_col") or "").strip()
            name_col = (r0.get("name_col") or "").strip()
            if not (schema_name and table_name and id_col and name_col):
                continue
            return {"db": db, "schema": schema_name, "table": table_name, "id_col": id_col, "name_col": name_col}, None
        return None, None

    def _find_empresa_join_candidate(self) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """
        Tenta descobrir uma tabela de cadastro de empresa/filial/emitente contendo:
        - coluna ID (codigo_empresa/codigo_filial/codigo_emitente/...)
        - coluna nome/descricao/fantasia
        """
        id_cols = [
            "codigo_empresa",
            "cod_empresa",
            "empresa_codigo",
            "empresa_id",
            "codigo_filial",
            "cod_filial",
            "filial_codigo",
            "filial_id",
            "codigo_emitente",
            "cod_emitente",
            "emitente_codigo",
            "emitente_id",
        ]
        name_cols = [
            "nome_empresa",
            "empresa_nome",
            "razao_social",
            "fantasia",
            "nome",
            "descricao",
            "descricao_empresa",
            "descricao_filial",
            "nome_filial",
            "nome_emitente",
        ]

        ids_in = ", ".join(f"'{_escape_sql_literal(c)}'" for c in id_cols)
        names_in = ", ".join(f"'{_escape_sql_literal(c)}'" for c in name_cols)

        def _query_for_db(db: str) -> str:
            return f"""
WITH cols AS (
    SELECT
        c.TABLE_SCHEMA AS schema_name,
        c.TABLE_NAME AS table_name,
        MAX(CASE WHEN LOWER(c.COLUMN_NAME) IN ({ids_in}) THEN c.COLUMN_NAME END) AS id_col,
        MAX(CASE WHEN LOWER(c.COLUMN_NAME) IN ({names_in}) THEN c.COLUMN_NAME END) AS name_col
    FROM {db}.INFORMATION_SCHEMA.COLUMNS c
    WHERE LOWER(c.COLUMN_NAME) IN ({ids_in}, {names_in})
    GROUP BY c.TABLE_SCHEMA, c.TABLE_NAME
),
ranked AS (
    SELECT
        schema_name,
        table_name,
        id_col,
        name_col,
        CASE
            WHEN LOWER(table_name) LIKE '%empresa%' THEN 0
            WHEN LOWER(table_name) LIKE '%filial%' THEN 1
            WHEN LOWER(table_name) LIKE '%emitente%' THEN 2
            WHEN LOWER(table_name) LIKE '%cad%' THEN 3
            ELSE 9
        END AS score
    FROM cols
    WHERE id_col IS NOT NULL AND name_col IS NOT NULL
)
SELECT TOP 1 schema_name, table_name, id_col, name_col
FROM ranked
ORDER BY score, table_name;
""".strip()

        for db in ("spalla", "Make"):
            sql = _query_for_db(db)
            rows, err = self._run_query(sql, database="Make")
            if err:
                rows, err = self._run_query(sql, database=None)
            if err:
                continue
            if not rows:
                continue
            r0 = rows[0] if isinstance(rows[0], dict) else {}
            schema_name = (r0.get("schema_name") or "").strip()
            table_name = (r0.get("table_name") or "").strip()
            id_col = (r0.get("id_col") or "").strip()
            name_col = (r0.get("name_col") or "").strip()
            if not (schema_name and table_name and id_col and name_col):
                continue
            return {"db": db, "schema": schema_name, "table": table_name, "id_col": id_col, "name_col": name_col}, None
        return None, None

    def _best_doc_column(
        self,
        cols_doc: Sequence[str],
        *,
        must_contain_any: Sequence[str],
        prefer_contains_any: Optional[Sequence[str]] = None,
        exclude_contains_any: Optional[Sequence[str]] = None,
    ) -> Optional[str]:
        """
        Escolhe a "melhor" coluna em `spalla.dbo.documentos` por heurística de nome.
        """
        must = [m.lower() for m in (must_contain_any or []) if isinstance(m, str) and m.strip()]
        prefer = [p.lower() for p in (prefer_contains_any or []) if isinstance(p, str) and p.strip()]
        excl = [e.lower() for e in (exclude_contains_any or []) if isinstance(e, str) and e.strip()]
        best = None
        best_score = -10_000
        for c in cols_doc or []:
            if not isinstance(c, str):
                continue
            cl = c.lower()
            if must and not any(m in cl for m in must):
                continue
            if excl and any(e in cl for e in excl):
                continue
            score = 0
            # preferências
            for p in prefer:
                if p in cl:
                    score += 10
            # penalizar coisas que parecem texto quando queremos chave
            if "descricao" in cl or "observ" in cl:
                score -= 5
            if score > best_score:
                best_score = score
                best = c
        return best

    def _pick_best_nonnull_doc_column(
        self,
        *,
        dt_ini: str,
        dt_fim: str,
        where_venda_sql: str,
        where_termo_sql: str,
        candidate_cols: Sequence[str],
        top_candidates: int = 10,
    ) -> Optional[str]:
        """
        Seleciona a coluna "mais preenchida" (non-null) dentre candidatas no período.
        Útil quando o schema varia e o nome da coluna não é óbvio.
        """
        uniq: List[str] = []
        seen = set()
        for c in candidate_cols or []:
            if not isinstance(c, str):
                continue
            c = c.strip()
            if not c or c.lower() in seen:
                continue
            seen.add(c.lower())
            uniq.append(c)
        uniq = uniq[: max(3, min(int(top_candidates), 25))]
        if not uniq:
            return None

        best_col = None
        best_nn = -1
        best_ratio = -1.0

        for col in uniq:
            col_q = _qident(col)
            if not col_q:
                continue
            sql = f"""
SELECT
    SUM(CASE WHEN d.{col_q} IS NULL THEN 0 ELSE 1 END) AS nn,
    COUNT(1) AS total
FROM spalla.dbo.documentos d
JOIN Make.dbo.TIPOS_DOCUMENTO_SPALLA tds
    ON tds.TD_COD = d.codigo_tipo_documento
LEFT JOIN spalla.dbo.centro_custo cc
    ON cc.codigo_centro_custo = d.codigo_setor
WHERE d.data_emissao >= '{_escape_sql_literal(dt_ini)}'
  AND d.data_emissao <  '{_escape_sql_literal(dt_fim)}'
  AND {where_venda_sql}
  AND {where_termo_sql};
""".strip()
            rows, err = self._run_query(sql, database="Make")
            if err:
                rows, err = self._run_query(sql, database=None)
            if err or not rows:
                continue
            r0 = rows[0] if isinstance(rows[0], dict) else {}
            try:
                nn = int(r0.get("nn") or 0)
                total = int(r0.get("total") or 0)
                ratio = (float(nn) / float(total)) if total > 0 else 0.0
            except Exception:
                continue
            if nn > best_nn or (nn == best_nn and ratio > best_ratio):
                best_col = col
                best_nn = nn
                best_ratio = ratio

        return best_col

    def inspecionar_schema_nf(self, *, top: int = 80) -> Dict[str, Any]:
        """
        Descobre (best-effort) onde ficam campos de NF/cliente/itens no legado.
        Retorna colunas de `spalla.dbo.documentos` e sugestões de colunas prováveis.
        """
        if not self._adapter:
            return {"sucesso": False, "erro": "SQL_ADAPTER_INDISPONIVEL", "dados": None}

        cols_doc, err = self._listar_colunas_spalla("dbo.documentos")
        if err:
            return {"sucesso": False, "erro": err, "dados": None}

        cols_l = {c.lower(): c for c in cols_doc}

        def pick_candidates(cands: Sequence[str]) -> List[str]:
            out = []
            for c in cands:
                if c.lower() in cols_l:
                    out.append(cols_l[c.lower()])
            return out

        candidatos_nf = pick_candidates(
            [
                "numero_nf",
                "numero_nfe",
                "numero_nota",
                "numero_documento",
                "nr_documento",
                "nro_documento",
                "numero",
                "número",
                "chave_nfe",
                "chave_acesso",
                "chave",
            ]
        )
        candidatos_cliente = pick_candidates(
            [
                "codigo_cliente",
                "cod_cliente",
                "cliente",
                "cliente_codigo",
                "cliente_id",
                "codigo_parceiro",
                "cod_parceiro",
                "parceiro_codigo",
                "codigo_pessoa",
                "cod_pessoa",
                "pessoa_codigo",
                "nome_cliente",
                "razao_social",
                "cliente_nome",
            ]
        )
        candidatos_obs = pick_candidates(
            [
                "observacao",
                "observacoes",
                "historico",
                "descricao",
                "complemento",
                "descricao_documento",
                "texto",
            ]
        )

        # Também listar tabelas prováveis de itens/produtos
        sql_tab = f"""
SELECT TOP {min(max(int(top), 10), 200)}
    t.TABLE_SCHEMA AS schema_name,
    t.TABLE_NAME AS table_name
FROM spalla.INFORMATION_SCHEMA.TABLES t
WHERE t.TABLE_TYPE='BASE TABLE'
  AND (
      t.TABLE_NAME LIKE '%item%'
      OR t.TABLE_NAME LIKE '%itens%'
      OR t.TABLE_NAME LIKE '%produto%'
      OR t.TABLE_NAME LIKE '%produtos%'
      OR t.TABLE_NAME LIKE '%mercadoria%'
      OR t.TABLE_NAME LIKE '%nfe%'
      OR t.TABLE_NAME LIKE '%nota%'
  )
ORDER BY t.TABLE_NAME;
""".strip()
        tab_rows, tab_err = self._run_query(sql_tab, database="Make")
        if tab_err:
            tab_rows, tab_err = self._run_query(sql_tab, database=None)
        tabelas_sugeridas = tab_rows or []

        return {
            "sucesso": True,
            "dados": {
                "documentos_colunas": cols_doc,
                "candidatos": {
                    "numero_nf": candidatos_nf,
                    "cliente": candidatos_cliente,
                    "observacoes": candidatos_obs,
                },
                "tabelas_sugeridas_itens_produtos": tabelas_sugeridas,
            },
        }

    def _build_like_where(self, column_sql: str, termos: Sequence[str]) -> str:
        termos = [t.strip() for t in (termos or []) if isinstance(t, str) and t.strip()]
        if not termos:
            return "1=1"
        parts = []
        for t in termos:
            parts.append(f"{column_sql} LIKE '%{_escape_sql_literal(t)}%'")
        return "(" + " OR ".join(parts) + ")"

    def _build_where_tokens_all_columns(self, *, tokens: Sequence[str], columns_sql: Sequence[str]) -> str:
        """
        Monta WHERE exigindo que TODOS os tokens apareçam em pelo menos uma das colunas.
        Ex. tokens=["alho","chines"], columns=[cc, tds] =>
          (cc LIKE %alho% OR tds LIKE %alho%) AND (cc LIKE %chines% OR tds LIKE %chines%)
        """
        toks = [t for t in (tokens or []) if isinstance(t, str) and t.strip()]
        cols = [c for c in (columns_sql or []) if isinstance(c, str) and c.strip()]
        if not toks or not cols:
            return "1=1"
        per_token = []
        for t in toks:
            ors = [f"{c} LIKE '%{_escape_sql_literal(t)}%'" for c in cols]
            per_token.append("(" + " OR ".join(ors) + ")")
        return "(" + " AND ".join(per_token) + ")"

    def _build_where_termo_variants(self, *, termo: Optional[str], columns_sql: Sequence[str]) -> str:
        """
        Constrói WHERE para termo com fallback em variantes.
        Ex: (match hikvision) OR (match hik AND vision)
        """
        variants = _build_term_variants(termo)
        if not variants:
            return "1=1"
        parts = [self._build_where_tokens_all_columns(tokens=v, columns_sql=columns_sql) for v in variants]
        return "(" + " OR ".join(parts) + ")"

    def _resolve_periodo(
        self,
        *,
        inicio: Optional[str],
        fim: Optional[str],
        periodo_mes: Optional[str],
        apenas_hoje: bool,
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Retorna (inicio_yyyy_mm_dd, fim_yyyy_mm_dd, erro)
        """
        if apenas_hoje:
            try:
                from datetime import timedelta

                dt = date.today()
                hoje = dt.isoformat()
                amanha = (dt + timedelta(days=1)).isoformat()
            except Exception:
                hoje = date.today().isoformat()
                # fallback: se timedelta falhar (muito improvável), usar o próprio "hoje"
                amanha = hoje
            return hoje, amanha, None

        if periodo_mes:
            rng = _month_range_from_yyyy_mm(periodo_mes)
            if not rng:
                return None, None, "periodo_mes inválido. Use YYYY-MM (ex: 2025-01)."
            return rng[0], rng[1], None

        ini = _coerce_date_yyyy_mm_dd(inicio or "")
        end = _coerce_date_yyyy_mm_dd(fim or "")
        if not ini or not end:
            return None, None, "Período inválido. Use inicio/fim em YYYY-MM-DD (ou periodo_mes=YYYY-MM)."
        if ini >= end:
            return None, None, "Período inválido: inicio deve ser < fim (fim é exclusivo)."
        return ini, end, None

    def consultar_vendas(
        self,
        *,
        inicio: Optional[str] = None,
        fim: Optional[str] = None,
        periodo_mes: Optional[str] = None,
        apenas_hoje: bool = False,
        termo: Optional[str] = None,
        venda_td_des_like: Optional[Sequence[str]] = None,
        top: int = 50,
        granularidade: str = "mes",  # "mes" | "dia"
    ) -> Dict[str, Any]:
        """
        Consulta vendas agregadas no período.

        Heurística de venda:
        - filtra por `tds.TD_DES LIKE %...%` (configurável via venda_td_des_like)

        Filtro de termo (produto/serviço):
        - best-effort em `cc.descricao_centro_custo` e/ou `tds.TD_DES`
        """
        if not self._adapter:
            return {"sucesso": False, "erro": "SQL_ADAPTER_INDISPONIVEL", "dados": None}

        if top <= 0:
            top = 50
        top = min(int(top), 500)

        granularidade = (granularidade or "mes").strip().lower()
        if granularidade not in ("mes", "dia"):
            granularidade = "mes"

        dt_ini, dt_fim, err = self._resolve_periodo(
            inicio=inicio,
            fim=fim,
            periodo_mes=periodo_mes,
            apenas_hoje=bool(apenas_hoje),
        )
        if err:
            return {"sucesso": False, "erro": err, "dados": None}

        like_venda = list(venda_td_des_like or [])
        # fallback default (conservador; usuário pode ajustar por aprendizado depois)
        if not like_venda:
            # ✅ Inclui também movimentos que compõem "venda" na prática:
            # - Nota Fiscal Complementar de Imposto (operações de saída)
            # - Devolução de venda (com vínculo)
            # - Simples faturamento / entrega futura
            like_venda = [
                "VENDA",
                "FATUR",
                "NF",
                "NOTA FISCAL COMPLEMENTAR",
                "COMPLEMENTAR DE IMPOSTO",
                "DEVOLUÇÃO DE VENDA",
                "ENTREGA FUTURA",
                "SIMPLES FATURAMENTO",
            ]

        termo_raw = (termo or "").strip()
        termo_norm = _normalize_search_text(termo_raw) if termo_raw else ""
        termo_tokens = _tokenize_search_terms(termo_raw)

        # Campos base (já usados no script e validados em conversa)
        periodo_expr = (
            "FORMAT(CONVERT(date, d.data_emissao), 'yyyy-MM-dd')" if granularidade == "dia"
            else "FORMAT(CONVERT(date, d.data_emissao), 'yyyy-MM')"
        )

        where_venda = self._build_like_where("tds.TD_DES", like_venda)

        # termo: preferir centro de custo (é onde normalmente aparece 'ALHO', 'RASTREADOR', etc.)
        where_termo = "1=1"
        if termo_tokens:
            where_termo = self._build_where_termo_variants(
                termo=termo_raw,
                columns_sql=["cc.descricao_centro_custo", "tds.TD_DES"],
            )

        sql = f"""
WITH base AS (
    SELECT
        {periodo_expr} AS periodo,
        d.tipo_movimento AS tipo_movimento_documento,
        tds.TD_DES AS descricao_tipo_operacao_documento,
        d.codigo_setor AS codigo_centro_custo_documento,
        cc.descricao_centro_custo AS descricao_centro_custo_documento,
        CAST(d.valor_documento AS decimal(18,2)) AS valor_documento
    FROM spalla.dbo.documentos d
    JOIN Make.dbo.TIPOS_DOCUMENTO_SPALLA tds
        ON tds.TD_COD = d.codigo_tipo_documento
    LEFT JOIN spalla.dbo.centro_custo cc
        ON cc.codigo_centro_custo = d.codigo_setor
    WHERE d.data_emissao >= '{_escape_sql_literal(dt_ini)}'
      AND d.data_emissao <  '{_escape_sql_literal(dt_fim)}'
      AND {where_venda}
      AND {where_termo}
),
agg AS (
    SELECT
        periodo,
        tipo_movimento_documento,
        descricao_tipo_operacao_documento,
        codigo_centro_custo_documento,
        descricao_centro_custo_documento,
        SUM(valor_documento) AS total_valor,
        COUNT(1) AS qtd_documentos
    FROM base
    GROUP BY
        periodo,
        tipo_movimento_documento,
        descricao_tipo_operacao_documento,
        codigo_centro_custo_documento,
        descricao_centro_custo_documento
)
SELECT TOP {top}
    a.*,
    CAST(100.0 * a.total_valor / NULLIF(SUM(a.total_valor) OVER (PARTITION BY a.periodo), 0) AS decimal(9,2)) AS pct_no_periodo
FROM agg a
ORDER BY a.periodo DESC, a.total_valor DESC;
""".strip()

        rows, qerr = self._run_query(sql, database="Make")
        if qerr:
            # fallback: alguns ambientes já conectam no DB default certo
            rows, qerr = self._run_query(sql, database=None)
        if qerr:
            logger.warning(f"[VENDAS_MAKE] erro ao consultar: {qerr}")
            return {
                "sucesso": False,
                "erro": qerr,
                "dados": None,
                "meta": {
                    "inicio": dt_ini,
                    "fim": dt_fim,
                    "granularidade": granularidade,
                    "termo": termo_norm or None,
                    "termo_tokens": termo_tokens,
                    "venda_td_des_like": like_venda,
                },
                "sql_preview": sql[:800],
            }

        return {
            "sucesso": True,
            "dados": rows or [],
            "meta": {
                "inicio": dt_ini,
                "fim": dt_fim,
                "granularidade": granularidade,
                "termo": termo_norm or None,
                "termo_tokens": termo_tokens,
                "venda_td_des_like": like_venda,
                "linhas": len(rows or []),
            },
        }

    def consultar_vendas_por_nf(
        self,
        *,
        inicio: Optional[str] = None,
        fim: Optional[str] = None,
        periodo_mes: Optional[str] = None,
        apenas_hoje: bool = False,
        termo: Optional[str] = None,
        venda_td_des_like: Optional[Sequence[str]] = None,
        top: int = 80,
    ) -> Dict[str, Any]:
        """
        Vendas por NF (nível "documento"): data, número NF, cliente (se existir), total e centro de custo.

        ⚠️ Importante:
        - Como o schema do Make/Spalla varia, este método descobre colunas em `spalla.dbo.documentos`
          e só usa as que existirem.
        - Se não encontrar uma coluna de número NF, retorna erro orientando rodar `inspecionar_schema_nf`.
        """
        if not self._adapter:
            return {"sucesso": False, "erro": "SQL_ADAPTER_INDISPONIVEL", "dados": None}

        dt_ini, dt_fim, err = self._resolve_periodo(
            inicio=inicio,
            fim=fim,
            periodo_mes=periodo_mes,
            apenas_hoje=bool(apenas_hoje),
        )
        if err:
            return {"sucesso": False, "erro": err, "dados": None}

        cols_doc, err_cols = self._listar_colunas_spalla("dbo.documentos")
        if err_cols:
            return {"sucesso": False, "erro": err_cols, "dados": None}
        cols_l = {c.lower(): c for c in cols_doc}

        def first_existing(cands: Sequence[str]) -> Optional[str]:
            for c in cands:
                if c.lower() in cols_l:
                    return cols_l[c.lower()]
            return None

        col_nf = first_existing(
            [
                "numero_nf",
                "numero_nfe",
                "numero_nota",
                "numero_documento",
                "nr_documento",
                "nro_documento",
                "numero",
                "chave_nfe",
                "chave_acesso",
            ]
        )
        if not col_nf:
            return {
                "sucesso": False,
                "erro": "COLUNA_NF_NAO_ENCONTRADA",
                "dados": None,
                "resposta": (
                    "❌ Não consegui localizar a coluna de número NF em `spalla.dbo.documentos`.\n\n"
                    "💡 Rode primeiro: **inspecionar_schema_nf_make** para eu descobrir quais colunas existem."
                ),
            }

        # ✅ Cliente: ampliar candidatos porque o schema do legado varia bastante
        col_cliente_nome = first_existing(
            [
                "nome_cliente",
                "cliente_nome",
                "razao_social",
                "nome_parceiro",
                "parceiro_nome",
                "nome_pessoa",
                "pessoa_nome",
                "nm_cliente",
                "nm_pessoa",
            ]
        )
        col_cliente_cod = first_existing(
            [
                "codigo_cliente",
                "cod_cliente",
                "cliente_codigo",
                "cliente_id",
                "codigo_parceiro",
                "cod_parceiro",
                "parceiro_codigo",
                "parceiro_id",
                "codigo_pessoa",
                "cod_pessoa",
                "pessoa_codigo",
                "pessoa_id",
            ]
        )

        # ✅ Se ainda não achou cliente, tentar heurística por nome de coluna em `documentos`
        if not col_cliente_nome:
            col_cliente_nome = self._best_doc_column(
                cols_doc,
                must_contain_any=["cliente", "pessoa", "parceiro", "destinat", "tomador"],
                prefer_contains_any=["nome", "razao", "social"],
                exclude_contains_any=["codigo", "cod_", "id"],
            )
            if col_cliente_nome and col_cliente_nome.lower() not in cols_l:
                col_cliente_nome = None
        if not col_cliente_cod:
            col_cliente_cod = self._best_doc_column(
                cols_doc,
                must_contain_any=["cliente", "pessoa", "parceiro", "destinat", "tomador"],
                prefer_contains_any=["codigo", "cod", "_id", "id"],
                exclude_contains_any=["nome", "razao", "social", "descricao"],
            )
            if col_cliente_cod and col_cliente_cod.lower() not in cols_l:
                col_cliente_cod = None

        # ✅ Empresa vendedora (best-effort): tentar achar coluna que indique filial/empresa/emitente
        col_empresa = first_existing(
            [
                "empresa",
                "codigo_empresa",
                "cod_empresa",
                "empresa_id",
                "filial",
                "codigo_filial",
                "cod_filial",
                "filial_id",
                "emitente",
                "codigo_emitente",
                "cod_emitente",
            ]
        )
        if not col_empresa:
            col_empresa = self._best_doc_column(
                cols_doc,
                must_contain_any=["empresa", "filial", "emitente", "matriz"],
                prefer_contains_any=["codigo", "cod", "_id", "id", "nome"],
                exclude_contains_any=["descricao"],
            )
            if col_empresa and col_empresa.lower() not in cols_l:
                col_empresa = None

        like_venda = list(venda_td_des_like or [])
        if not like_venda:
            like_venda = [
                "VENDA",
                "FATUR",
                "NF",
                "NOTA FISCAL COMPLEMENTAR",
                "COMPLEMENTAR DE IMPOSTO",
                "DEVOLUÇÃO DE VENDA",
                "ENTREGA FUTURA",
                "SIMPLES FATURAMENTO",
            ]

        termo_raw = (termo or "").strip()
        termo_norm = _normalize_search_text(termo_raw) if termo_raw else ""
        termo_tokens = _tokenize_search_terms(termo_raw)

        where_venda = self._build_like_where("tds.TD_DES", like_venda)
        where_termo = "1=1"
        if termo_tokens:
            where_termo = self._build_where_termo_variants(
                termo=termo_raw,
                columns_sql=["cc.descricao_centro_custo", "tds.TD_DES"],
            )

        # ✅ Seleção por "realidade" (coluna mais preenchida) para cliente/empresa.
        # Se ainda não achou, tenta identificar pelo preenchimento real no período.
        if not col_cliente_nome:
            cand_nome = [
                c
                for c in cols_doc
                if isinstance(c, str)
                and any(x in c.lower() for x in ("cliente", "pessoa", "parceiro", "destinat", "tomador"))
                and any(x in c.lower() for x in ("nome", "razao", "social", "fantas"))
                and not any(x in c.lower() for x in ("codigo", "cod_", "id"))
            ]
            col_cliente_nome = self._pick_best_nonnull_doc_column(
                dt_ini=dt_ini,
                dt_fim=dt_fim,
                where_venda_sql=where_venda,
                where_termo_sql=where_termo,
                candidate_cols=cand_nome,
            )

        if not col_cliente_cod:
            cand_cod = [
                c
                for c in cols_doc
                if isinstance(c, str)
                and any(x in c.lower() for x in ("cliente", "pessoa", "parceiro", "destinat", "tomador"))
                and any(x in c.lower() for x in ("codigo", "cod", "_id", "id"))
                and not any(x in c.lower() for x in ("nome", "razao", "social", "descricao"))
            ]
            col_cliente_cod = self._pick_best_nonnull_doc_column(
                dt_ini=dt_ini,
                dt_fim=dt_fim,
                where_venda_sql=where_venda,
                where_termo_sql=where_termo,
                candidate_cols=cand_cod,
            )

        if not col_empresa:
            cand_emp = [
                c
                for c in cols_doc
                if isinstance(c, str)
                and any(x in c.lower() for x in ("empresa", "filial", "emitente"))
                and any(x in c.lower() for x in ("codigo", "cod", "_id", "id"))
            ]
            col_empresa = self._pick_best_nonnull_doc_column(
                dt_ini=dt_ini,
                dt_fim=dt_fim,
                where_venda_sql=where_venda,
                where_termo_sql=where_termo,
                candidate_cols=cand_emp,
            )

        # ✅ Empresa emissora + Cliente (fonte correta)
        # Cliente (nome) vem do legado via ANALISE_VENDAS_SPALLA.CF_RSOCIAL (join por filial/tipo/cod_doc).
        # Empresa emissora vem de empresas_filiais.nome_fantasia.
        join_ef = "LEFT JOIN spalla.dbo.empresas_filiais ef ON ef.codigo_empresa_filial = d.codigo_empresa_filial"
        # ⚠️ IMPORTANTE: ANALISE_VENDAS_SPALLA pode ter múltiplas linhas por documento.
        # Usar OUTER APPLY (TOP 1) evita duplicar NFs/valores no relatório.
        apply_avs = """
OUTER APPLY (
    SELECT TOP 1 avs.CF_RSOCIAL
    FROM Make.dbo.ANALISE_VENDAS_SPALLA avs
    WHERE d.codigo_empresa_filial = avs.FL_COD
      AND d.tipo_movimento = avs.CF_TIPO
      AND d.codigo_documento = avs.FT_COD
    ORDER BY avs.CF_RSOCIAL
) avs1
""".strip()

        # ✅ Financeiro (títulos): somar recebido e sugerir em aberto por NF
        # ⚠️ IMPORTANTE: titulos/titulos_baixa podem ter múltiplas linhas (parcelas/baixas).
        # Usar OUTER APPLY agregado evita multiplicar linhas do documento.
        apply_titulos = """
OUTER APPLY (
    SELECT
        SUM(COALESCE(CAST(t.valor_titulo AS decimal(18,2)), CAST(t.valor_titulo_original AS decimal(18,2)), 0)) AS valor_titulo_total,
        SUM(COALESCE(CAST(t.total_baixado_geral AS decimal(18,2)), CAST(t.total_baixado_titulo AS decimal(18,2)), 0)) AS valor_recebido_total,
        MIN(t.data_vencimento) AS proximo_vencimento
    FROM spalla.dbo.titulos t WITH (NOLOCK)
    WHERE t.codigo_empresa_filial = d.codigo_empresa_filial
      AND t.tipo_movimento = d.tipo_movimento
      AND t.codigo_movimento = d.codigo_documento
) tit1
""".strip()

        # Select cliente best-effort (fallback) — se avs não tiver, tenta os caminhos anteriores.
        cliente_select_base = "NULL"
        join_cliente = ""
        if col_cliente_nome:
            cliente_select_base = f"d.{_qident(col_cliente_nome)}"
        elif col_cliente_cod:
            # ✅ tentar enriquecer com nome via JOIN best-effort
            cand, cand_err = self._find_cliente_join_candidate()
            if cand and cand.get("schema") and cand.get("table") and cand.get("id_col") and cand.get("name_col"):
                db = cand.get("db") or "spalla"
                schema = cand["schema"]
                table = cand["table"]
                id_col = cand["id_col"]
                name_col = cand["name_col"]
                join_cliente = (
                    f"LEFT JOIN {_qident(db)}.{_qident(schema)}.{_qident(table)} cli "
                    f"ON CAST(cli.{_qident(id_col)} AS varchar(60)) = CAST(d.{_qident(col_cliente_cod)} AS varchar(60))"
                )
                cliente_select_base = f"cli.{_qident(name_col)}"
            else:
                cliente_select_base = f"CAST(d.{_qident(col_cliente_cod)} AS varchar(60))"

        # Empresa vendedora: tentar trazer nome via join (expressão SEM alias)
        empresa_expr = "NULL"
        join_empresa = ""
        if col_empresa:
            emp_cand, _emp_err = self._find_empresa_join_candidate()
            if emp_cand and emp_cand.get("schema") and emp_cand.get("table") and emp_cand.get("id_col") and emp_cand.get("name_col"):
                db = emp_cand.get("db") or "spalla"
                schema = emp_cand["schema"]
                table = emp_cand["table"]
                id_col = emp_cand["id_col"]
                name_col = emp_cand["name_col"]
                join_empresa = (
                    f"LEFT JOIN {_qident(db)}.{_qident(schema)}.{_qident(table)} emp "
                    f"ON CAST(emp.{_qident(id_col)} AS varchar(60)) = CAST(d.{_qident(col_empresa)} AS varchar(60))"
                )
                empresa_expr = f"emp.{_qident(name_col)}"
            else:
                empresa_expr = f"CAST(d.{_qident(col_empresa)} AS varchar(80))"

        # Preferir nome fantasia da filial (ef), com fallback para o que já tínhamos.
        empresa_select_final = f"COALESCE(ef.nome_fantasia, {empresa_expr}) AS empresa_vendedora"

        # Cliente final: preferir avs.CF_RSOCIAL, com fallback (e por último vazio).
        cliente_select_final = f"COALESCE(avs1.CF_RSOCIAL, {cliente_select_base}) AS cliente"

        total_nf_expr = "CAST(d.valor_documento AS decimal(18,2))"

        sql = f"""
SELECT TOP {min(max(int(top), 10), 500)}
    CONVERT(date, d.data_emissao) AS data_emissao,
    CAST(d.{_qident(col_nf)} AS varchar(60)) AS numero_nf,
    {cliente_select_final},
    {empresa_select_final},
    d.tipo_movimento AS tipo_movimento_documento,
    tds.TD_DES AS descricao_tipo_operacao_documento,
    d.codigo_setor AS codigo_centro_custo_documento,
    cc.descricao_centro_custo AS descricao_centro_custo_documento,
    {total_nf_expr} AS total_nf,
    CAST(COALESCE(tit1.valor_recebido_total, 0) AS decimal(18,2)) AS valor_recebido,
    CAST(({total_nf_expr} - CAST(COALESCE(tit1.valor_recebido_total, 0) AS decimal(18,2))) AS decimal(18,2)) AS valor_em_aberto,
    CONVERT(date, tit1.proximo_vencimento) AS proximo_vencimento
FROM spalla.dbo.documentos d
JOIN Make.dbo.TIPOS_DOCUMENTO_SPALLA tds
    ON tds.TD_COD = d.codigo_tipo_documento
{join_ef}
{apply_avs}
{apply_titulos}
{join_cliente}
{join_empresa}
LEFT JOIN spalla.dbo.centro_custo cc
    ON cc.codigo_centro_custo = d.codigo_setor
WHERE d.data_emissao >= '{_escape_sql_literal(dt_ini)}'
  AND d.data_emissao <  '{_escape_sql_literal(dt_fim)}'
  AND {where_venda}
  AND {where_termo}
ORDER BY d.data_emissao DESC, total_nf DESC;
""".strip()

        rows, qerr = self._run_query(sql, database="Make")
        if qerr:
            rows, qerr = self._run_query(sql, database=None)
        if qerr:
            return {
                "sucesso": False,
                "erro": qerr,
                "dados": None,
                "meta": {
                    "inicio": dt_ini,
                    "fim": dt_fim,
                    "termo": termo_norm or None,
                    "termo_tokens": termo_tokens,
                    "venda_td_des_like": like_venda,
                },
                "sql_preview": sql[:900],
            }

        # ✅ “LangChain cirúrgico” (fallback de termo): se deu 0 linhas, tentar 1 vez normalizar o termo e reconsultar.
        # Objetivo: evitar manutenção infinita de typos (hakvision/hikvison/etc.).
        try:
            if (not rows) and termo_raw:
                from services.sales_fuzzy_term_service import SalesFuzzyTermService

                sug = SalesFuzzyTermService.sugerir(termo_raw) or {}
                termo_corrigido = (sug.get("termo_principal") or "").strip()
                if termo_corrigido and termo_corrigido.lower() != termo_raw.strip().lower():
                    # Recalcular where_termo e reexecutar com o termo corrigido
                    where_termo_2 = self._build_where_termo_variants(
                        termo=termo_corrigido,
                        columns_sql=["cc.descricao_centro_custo", "tds.TD_DES"],
                    )
                    sql2 = sql.replace(f"  AND {where_termo}", f"  AND {where_termo_2}")
                    rows2, qerr2 = self._run_query(sql2, database="Make")
                    if qerr2:
                        rows2, qerr2 = self._run_query(sql2, database=None)
                    if (not qerr2) and rows2:
                        rows = rows2
                        termo_norm = _normalize_search_text(termo_corrigido)
                        termo_tokens = _tokenize_search_terms(termo_corrigido)
                        # marcar meta de autocorreção
                        auto_meta = {
                            "termo_original": termo_raw,
                            "termo_corrigido": termo_corrigido,
                        }
                    else:
                        auto_meta = None
                else:
                    auto_meta = None
            else:
                auto_meta = None
        except Exception:
            auto_meta = None

        return {
            "sucesso": True,
            "dados": rows or [],
            "meta": {
                "inicio": dt_ini,
                "fim": dt_fim,
                "termo": termo_norm or None,
                "termo_tokens": termo_tokens,
                "venda_td_des_like": like_venda,
                "coluna_nf": col_nf,
                "coluna_cliente_nome": col_cliente_nome,
                "coluna_cliente_cod": col_cliente_cod,
                "coluna_empresa": col_empresa,
                "cliente_join": bool(join_cliente.strip()),
                "empresa_join": bool(join_empresa.strip()),
                "cliente_avs_join": True,
                "empresa_filial_join": True,
                "linhas": len(rows or []),
                **({"fuzzy_term": auto_meta} if auto_meta else {}),
            },
        }

