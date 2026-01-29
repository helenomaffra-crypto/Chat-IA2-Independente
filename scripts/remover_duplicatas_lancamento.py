#!/usr/bin/env python3
"""
Remove duplicatas de lançamentos mantendo apenas o mais antigo (ou o classificado).

Uso:
  python3 scripts/remover_duplicatas_lancamento.py --ids "906,907" --manter 777
  python3 scripts/remover_duplicatas_lancamento.py --valor "13.337,88" --data "22/01/2026" --banco BB --agencia "1251" --conta "50483" --dry-run
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
    parser = argparse.ArgumentParser(description="Remover duplicatas de lançamentos.")
    parser.add_argument("--ids", type=str, help="IDs dos lançamentos a remover separados por vírgula (ex: 906,907)")
    parser.add_argument("--manter", type=int, help="ID do lançamento a manter (opcional, mantém o mais antigo se não especificado)")
    parser.add_argument("--valor", type=str, help="Valor do lançamento (para buscar duplicatas)")
    parser.add_argument("--data", type=str, help="Data do lançamento (para buscar duplicatas)")
    parser.add_argument("--banco", type=str, default="BB", help="Banco (BB ou SANTANDER)")
    parser.add_argument("--agencia", type=str, help="Agência (opcional)")
    parser.add_argument("--conta", type=str, help="Conta (opcional)")
    parser.add_argument("--dry-run", action="store_true", help="Apenas simular, não remover de fato")
    args = parser.parse_args()

    dry_run = args.dry_run
    if dry_run:
        logger.info("🔍 MODO DRY-RUN: Apenas simulação, nenhuma alteração será feita\n")

    # Buscar lançamentos
    adapter = get_sql_adapter()
    if not adapter:
        logger.error("❌ SQL Server não disponível")
        return 1

    ids_para_remover = []
    id_manter = args.manter

    if args.ids:
        # IDs fornecidos diretamente
        ids_para_remover = [int(id_str.strip()) for id_str in args.ids.split(",") if id_str.strip()]
    elif args.valor and args.data:
        # Buscar duplicatas por valor/data
        data_dt = _parse_data(args.data)
        if not data_dt:
            logger.error(f"❌ Data inválida: {args.data}")
            return 1

        valor_procurado = _normalizar_valor(args.valor)
        if valor_procurado == 0.0:
            logger.error(f"❌ Valor inválido: {args.valor}")
            return 1

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
                criado_em,
                (SELECT COUNT(*) FROM dbo.LANCAMENTO_TIPO_DESPESA ltd WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao) as tem_classificacao
            FROM dbo.MOVIMENTACAO_BANCARIA mb
            WHERE {where_clause}
            ORDER BY criado_em ASC
        """

        logger.info(f"🔍 Buscando duplicatas...\n")
        resultado = adapter.execute_query(query, database=adapter.database)

        if not resultado.get('success'):
            logger.error(f"❌ Erro ao consultar: {resultado.get('error', 'Erro desconhecido')}")
            return 1

        lancamentos = resultado.get('data', [])
        
        if len(lancamentos) <= 1:
            logger.info("✅ Nenhuma duplicata encontrada (menos de 2 lançamentos)")
            return 0

        logger.info(f"📊 Encontrados {len(lancamentos)} lançamentos com mesmo valor/data\n")

        # Decidir qual manter
        if not id_manter:
            # Manter o mais antigo (primeiro criado) ou o classificado
            lancamentos_ordenados = sorted(lancamentos, key=lambda x: (
                0 if x.get('tem_classificacao', 0) > 0 else 1,  # Classificados primeiro
                x.get('criado_em', '')  # Depois por data
            ))
            id_manter = lancamentos_ordenados[0].get('id_movimentacao')
            logger.info(f"✅ Mantendo lançamento ID {id_manter} (mais antigo ou classificado)")

        # IDs para remover (todos exceto o que será mantido)
        ids_para_remover = [l.get('id_movimentacao') for l in lancamentos if l.get('id_movimentacao') != id_manter]
    else:
        logger.error("❌ Forneça --ids OU --valor+--data")
        return 1

    if not ids_para_remover:
        logger.info("✅ Nenhum lançamento para remover")
        return 0

    logger.info(f"\n{'='*70}")
    logger.info(f"🗑️  REMOVENDO DUPLICATAS")
    logger.info(f"{'='*70}")
    logger.info(f"Manter: ID {id_manter}")
    logger.info(f"Remover: IDs {ids_para_remover}")
    logger.info(f"{'='*70}\n")

    if dry_run:
        logger.info("🔍 DRY-RUN: Simulando remoção...")
        logger.info("   (Nenhuma alteração será feita)")
        return 0

    # Verificar se há classificações vinculadas
    ids_str = ",".join(str(id_val) for id_val in ids_para_remover)
    query_classificacoes = f"""
        SELECT COUNT(*) as total
        FROM dbo.LANCAMENTO_TIPO_DESPESA
        WHERE id_movimentacao_bancaria IN ({ids_str})
    """
    
    resultado_class = adapter.execute_query(query_classificacoes, database=adapter.database)
    if resultado_class.get('success') and resultado_class.get('data'):
        total_class = resultado_class['data'][0].get('total', 0) if resultado_class['data'] else 0
        if total_class > 0:
            logger.error(f"❌ ATENÇÃO: {total_class} classificação(ões) vinculada(s) aos lançamentos que serão removidos!")
            logger.error("   Remova as classificações primeiro ou use --manter para manter um lançamento classificado")
            return 1

    # Remover lançamentos
    removidos = 0
    erros = 0

    for id_remover in ids_para_remover:
        query_delete = f"""
            DELETE FROM dbo.MOVIMENTACAO_BANCARIA
            WHERE id_movimentacao = {id_remover}
        """
        
        try:
            # ✅ CORREÇÃO: SQLServerAdapter usa execute_query (não execute_non_query)
            resultado = adapter.execute_query(query_delete, database=adapter.database)
            if resultado.get('success'):
                removidos += 1
                logger.info(f"✅ Removido ID {id_remover}")
            else:
                erros += 1
                logger.error(f"❌ Erro ao remover ID {id_remover}: {resultado.get('error', 'Erro desconhecido')}")
        except Exception as e:
            erros += 1
            logger.error(f"❌ Erro ao remover ID {id_remover}: {e}", exc_info=True)

    logger.info(f"\n{'='*70}")
    logger.info("📊 RESUMO:")
    logger.info(f"   Removidos: {removidos}")
    logger.info(f"   Erros: {erros}")
    logger.info(f"   Mantido: ID {id_manter}")
    logger.info(f"{'='*70}\n")

    return 0 if erros == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
