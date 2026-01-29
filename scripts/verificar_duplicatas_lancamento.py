#!/usr/bin/env python3
"""
Verifica duplicatas de um lançamento específico no banco de dados.

Uso:
  python3 scripts/verificar_duplicatas_lancamento.py --valor 13337.88 --data 22/01/2026 --banco BB
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _parse_data(data_str: str) -> Optional[datetime]:
    """Converte string de data para datetime."""
    if not data_str:
        return None
    
    data_str = data_str.strip()
    
    # Tentar DD/MM/YYYY ou DD/MM/YY
    if "/" in data_str:
        try:
            partes = data_str.split("/")
            if len(partes) == 3:
                dd, mm, yy = partes[0].zfill(2), partes[1].zfill(2), partes[2].strip()
                if len(yy) == 2:
                    yy = f"20{yy}"
                return datetime(int(yy), int(mm), int(dd))
        except Exception:
            pass
    
    # Tentar YYYY-MM-DD
    if "-" in data_str:
        try:
            return datetime.strptime(data_str.split(" ")[0], "%Y-%m-%d")
        except Exception:
            pass
    
    return None


def _normalizar_valor(valor_str: str) -> float:
    """Normaliza valor removendo R$, espaços. Detecta formato brasileiro (1.234,56) ou decimal (1234.56)."""
    valor_str = str(valor_str).replace("R$", "").replace(" ", "").strip()
    
    # Se tem vírgula, assume formato brasileiro (1.234,56)
    if "," in valor_str:
        # Remover pontos (separadores de milhar) e substituir vírgula por ponto
        valor_str = valor_str.replace(".", "").replace(",", ".")
    # Se não tem vírgula mas tem ponto, pode ser decimal (1234.56) ou brasileiro sem vírgula (1.234)
    # Tentar detectar: se tem mais de um ponto, provavelmente é brasileiro
    elif valor_str.count(".") > 1:
        # Formato brasileiro sem vírgula (1.234)
        valor_str = valor_str.replace(".", "")
    
    try:
        return abs(float(valor_str))
    except ValueError:
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verificar duplicatas de lançamento.")
    parser.add_argument("--valor", type=str, required=True, help="Valor do lançamento (ex: 13337.88 ou R$ 13.337,88)")
    parser.add_argument("--data", type=str, required=True, help="Data do lançamento (DD/MM/YYYY ou YYYY-MM-DD)")
    parser.add_argument("--banco", type=str, default="BB", help="Banco (BB ou SANTANDER)")
    parser.add_argument("--agencia", type=str, help="Agência (opcional)")
    parser.add_argument("--conta", type=str, help="Conta (opcional)")
    args = parser.parse_args()

    # Parse data
    data_dt = _parse_data(args.data)
    if not data_dt:
        logger.error(f"❌ Data inválida: {args.data}")
        return 1

    # Normalizar valor
    valor_procurado = _normalizar_valor(args.valor)
    if valor_procurado == 0.0:
        logger.error(f"❌ Valor inválido: {args.valor}")
        return 1

    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 VERIFICANDO DUPLICATAS - {args.banco}")
    logger.info(f"💰 Valor: R$ {valor_procurado:,.2f}")
    logger.info(f"📅 Data: {data_dt.strftime('%d/%m/%Y')}")
    logger.info(f"{'='*70}\n")

    # Buscar lançamentos
    adapter = get_sql_adapter()
    if not adapter:
        logger.error("❌ SQL Server não disponível")
        return 1

    # Construir query
    data_str = data_dt.strftime("%Y-%m-%d")
    where_parts = [
        f"banco_origem = '{args.banco}'",
        f"CAST(data_movimentacao AS DATE) = '{data_str}'",
        f"ABS(valor_movimentacao - {valor_procurado}) < 0.01"
    ]

    if args.agencia:
        where_parts.append(f"agencia_origem = '{args.agencia}'")
    if args.conta:
        where_parts.append(f"conta_origem = '{args.conta}'")

    where_clause = " AND ".join(where_parts)

    query = f"""
        SELECT
            id_movimentacao,
            banco_origem,
            agencia_origem,
            conta_origem,
            data_movimentacao,
            valor_movimentacao,
            sinal_movimentacao,
            CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao,
            hash_dados,
            processo_referencia,
            criado_em,
            -- Verificar se tem classificação
            (SELECT COUNT(*) FROM dbo.LANCAMENTO_TIPO_DESPESA ltd WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao) as tem_classificacao
        FROM dbo.MOVIMENTACAO_BANCARIA mb
        WHERE {where_clause}
        ORDER BY criado_em ASC
    """

    logger.info(f"📝 Query SQL:\n{query}\n")

    resultado = adapter.execute_query(query, database=adapter.database)

    if not resultado.get('success'):
        logger.error(f"❌ Erro ao consultar: {resultado.get('error', 'Erro desconhecido')}")
        return 1

    lancamentos = resultado.get('data', [])
    
    if not lancamentos:
        logger.warning("⚠️ Nenhum lançamento encontrado")
        return 0

    logger.info(f"📊 Total de lançamentos encontrados: {len(lancamentos)}\n")

    # Agrupar por hash para identificar duplicatas
    hash_groups: Dict[str, List[Dict[str, Any]]] = {}
    for lanc in lancamentos:
        hash_val = str(lanc.get('hash_dados', 'SEM_HASH'))
        if hash_val not in hash_groups:
            hash_groups[hash_val] = []
        hash_groups[hash_val].append(lanc)

    # Mostrar resultados
    logger.info(f"🔑 Total de hashes únicos: {len(hash_groups)}\n")

    duplicatas_encontradas = False
    for hash_val, grupo in hash_groups.items():
        if len(grupo) > 1:
            duplicatas_encontradas = True
            logger.warning(f"⚠️ DUPLICATAS ENCONTRADAS (hash: {hash_val[:16]}...): {len(grupo)} lançamentos")
            for i, lanc in enumerate(grupo, 1):
                tem_class = lanc.get('tem_classificacao', 0) > 0
                status = "✅ Classificado" if tem_class else "❌ Não classificado"
                logger.info(f"\n  {i}. ID: {lanc.get('id_movimentacao')} - {status}")
                logger.info(f"     Criado em: {lanc.get('criado_em')}")
                logger.info(f"     Descrição: {lanc.get('descricao_movimentacao', '')[:80]}...")
        else:
            lanc = grupo[0]
            tem_class = lanc.get('tem_classificacao', 0) > 0
            status = "✅ Classificado" if tem_class else "❌ Não classificado"
            logger.info(f"✅ Hash único (hash: {hash_val[:16]}...): ID {lanc.get('id_movimentacao')} - {status}")

    # Verificar se há lançamentos com mesmo valor/data mas hash diferente
    logger.info("\n" + "="*70)
    logger.info("🔍 Verificando lançamentos com mesmo valor/data mas hash diferente...\n")

    # Agrupar por valor+data+descrição (sem hash)
    grupos_sem_hash: Dict[str, List[Dict[str, Any]]] = {}
    for lanc in lancamentos:
        chave = f"{lanc.get('valor_movimentacao')}_{lanc.get('data_movimentacao')}_{str(lanc.get('descricao_movimentacao', ''))[:50]}"
        if chave not in grupos_sem_hash:
            grupos_sem_hash[chave] = []
        grupos_sem_hash[chave].append(lanc)

    possiveis_duplicatas = False
    for chave, grupo in grupos_sem_hash.items():
        if len(grupo) > 1:
            possiveis_duplicatas = True
            logger.warning(f"⚠️ Possíveis duplicatas (mesmo valor/data/descrição, hash diferente): {len(grupo)} lançamentos")
            for i, lanc in enumerate(grupo, 1):
                hash_val = str(lanc.get('hash_dados', 'SEM_HASH'))
                tem_class = lanc.get('tem_classificacao', 0) > 0
                status = "✅ Classificado" if tem_class else "❌ Não classificado"
                logger.info(f"\n  {i}. ID: {lanc.get('id_movimentacao')} - {status}")
                logger.info(f"     Hash: {hash_val[:16]}...")
                logger.info(f"     Criado em: {lanc.get('criado_em')}")
                logger.info(f"     Descrição: {lanc.get('descricao_movimentacao', '')[:80]}...")

    if not duplicatas_encontradas and not possiveis_duplicatas:
        logger.info("✅ Nenhuma duplicata encontrada (todos os lançamentos têm hash único)")

    # Resumo final
    logger.info("\n" + "="*70)
    logger.info("📊 RESUMO:")
    logger.info(f"   Total de lançamentos: {len(lancamentos)}")
    logger.info(f"   Hashes únicos: {len(hash_groups)}")
    classificados = sum(1 for l in lancamentos if l.get('tem_classificacao', 0) > 0)
    nao_classificados = len(lancamentos) - classificados
    logger.info(f"   Classificados: {classificados}")
    logger.info(f"   Não classificados: {nao_classificados}")
    logger.info("="*70 + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
