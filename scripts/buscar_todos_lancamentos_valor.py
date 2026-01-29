#!/usr/bin/env python3
"""
Busca TODOS os lançamentos com um valor específico, sem filtrar por agência/conta.

Uso:
  python3 scripts/buscar_todos_lancamentos_valor.py --valor "13.337,88" --data "22/01/2026" --banco BB
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

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
    
    if "-" in data_str:
        try:
            return datetime.strptime(data_str.split(" ")[0], "%Y-%m-%d")
        except Exception:
            pass
    
    return None


def _normalizar_valor(valor_str: str) -> float:
    """Normaliza valor removendo R$, espaços. Detecta formato brasileiro (1.234,56) ou decimal (1234.56)."""
    valor_str = str(valor_str).replace("R$", "").replace(" ", "").strip()
    
    if "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    elif valor_str.count(".") > 1:
        valor_str = valor_str.replace(".", "")
    
    try:
        return abs(float(valor_str))
    except ValueError:
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Buscar TODOS os lançamentos com valor específico.")
    parser.add_argument("--valor", type=str, required=True, help="Valor do lançamento (ex: 13.337,88 ou 13337.88)")
    parser.add_argument("--data", type=str, required=True, help="Data do lançamento (DD/MM/YYYY ou YYYY-MM-DD)")
    parser.add_argument("--banco", type=str, default="BB", help="Banco (BB ou SANTANDER)")
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
    logger.info(f"🔍 BUSCANDO TODOS OS LANÇAMENTOS - {args.banco}")
    logger.info(f"💰 Valor: R$ {valor_procurado:,.2f}")
    logger.info(f"📅 Data: {data_dt.strftime('%d/%m/%Y')}")
    logger.info(f"{'='*70}\n")

    # Buscar lançamentos
    adapter = get_sql_adapter()
    if not adapter:
        logger.error("❌ SQL Server não disponível")
        return 1

    # Construir query SEM filtrar por agência/conta
    data_str = data_dt.strftime("%Y-%m-%d")
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
        WHERE banco_origem = '{args.banco}'
          AND CAST(data_movimentacao AS DATE) = '{data_str}'
          AND ABS(valor_movimentacao - {valor_procurado}) < 0.01
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

    # Mostrar resultados
    for i, lanc in enumerate(lancamentos, 1):
        id_mov = lanc.get('id_movimentacao')
        hash_val = str(lanc.get('hash_dados', 'SEM_HASH'))
        tem_class = lanc.get('tem_classificacao', 0) > 0
        status = "✅ Classificado" if tem_class else "❌ Não classificado"
        
        logger.info(f"{'='*70}")
        logger.info(f"📋 LANÇAMENTO {i}: ID {id_mov} - {status}")
        logger.info(f"{'='*70}")
        logger.info(f"Hash: {hash_val[:32]}...")
        logger.info(f"Criado em: {lanc.get('criado_em')}")
        logger.info(f"Agência: {lanc.get('agencia_origem', 'N/A')}")
        logger.info(f"Conta: {lanc.get('conta_origem', 'N/A')}")
        logger.info(f"Valor: R$ {float(lanc.get('valor_movimentacao', 0)):,.2f}")
        logger.info(f"Data: {lanc.get('data_movimentacao')}")
        logger.info(f"Descrição: {lanc.get('descricao_movimentacao', '')[:100]}...")
        if tem_class:
            logger.info(f"Processo: {lanc.get('processo_referencia', 'N/A')}")
        logger.info("")

    # Resumo
    logger.info(f"{'='*70}")
    logger.info("📊 RESUMO:")
    logger.info(f"   Total de lançamentos: {len(lancamentos)}")
    classificados = sum(1 for l in lancamentos if l.get('tem_classificacao', 0) > 0)
    nao_classificados = len(lancamentos) - classificados
    logger.info(f"   Classificados: {classificados}")
    logger.info(f"   Não classificados: {nao_classificados}")
    logger.info(f"{'='*70}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
