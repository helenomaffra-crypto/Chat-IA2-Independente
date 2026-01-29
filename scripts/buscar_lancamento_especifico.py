#!/usr/bin/env python3
"""
Busca lançamento bancário específico por valor e data.

Uso:
  python3 scripts/buscar_lancamento_especifico.py --valor 13337.88 --data 22/01/2026
  python3 scripts/buscar_lancamento_especifico.py --valor 13337.88 --data 2026-01-22
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402
from services.db_policy_service import get_primary_database  # noqa: E402

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


def _normalizar_valor(valor_str: str) -> Optional[float]:
    """Normaliza valor de string para float."""
    if not valor_str:
        return None
    
    # Remover R$, espaços, pontos de milhar, substituir vírgula por ponto
    valor_limpo = valor_str.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    
    try:
        return float(valor_limpo)
    except Exception:
        return None


def buscar_lancamento(adapter, valor: Optional[float] = None, data: Optional[datetime] = None, 
                      banco: Optional[str] = None, descricao: Optional[str] = None) -> List[Dict[str, Any]]:
    """Busca lançamentos bancários com filtros."""
    db = get_primary_database()
    
    where_parts = []
    
    if valor:
        # Buscar com tolerância de 0.01 (centavos)
        where_parts.append(f"ABS(valor_movimentacao - {abs(valor)}) < 0.01")
    
    if data:
        data_str = data.strftime("%Y-%m-%d")
        where_parts.append(f"CAST(data_movimentacao AS DATE) = '{data_str}'")
    
    if banco:
        banco_esc = banco.replace("'", "''")
        where_parts.append(f"banco_origem = '{banco_esc}'")
    
    if descricao:
        desc_esc = descricao.replace("'", "''")
        where_parts.append(f"descricao_movimentacao LIKE '%{desc_esc}%'")
    
    where_clause = " AND ".join(where_parts) if where_parts else "1=1"
    
    q = f"""
        SELECT TOP 100
            id_movimentacao,
            banco_origem,
            agencia_origem,
            conta_origem,
            data_movimentacao,
            data_lancamento,
            valor_movimentacao,
            sinal_movimentacao,
            tipo_movimentacao,
            descricao_movimentacao,
            processo_referencia,
            criado_em
        FROM {db}.dbo.MOVIMENTACAO_BANCARIA
        WHERE {where_clause}
        ORDER BY data_movimentacao DESC, criado_em DESC
    """
    
    r = adapter.execute_query(q, database=db, notificar_erro=False)
    if not r.get("success"):
        logger.error(f"❌ Erro ao buscar lançamento: {r.get('error')}")
        return []
    
    return r.get("data") or []


def main() -> int:
    parser = argparse.ArgumentParser(description="Buscar lançamento bancário específico.")
    parser.add_argument("--valor", type=str, help="Valor do lançamento (ex: 13337.88 ou R$ 13.337,88)")
    parser.add_argument("--data", type=str, help="Data do lançamento (DD/MM/YYYY ou YYYY-MM-DD)")
    parser.add_argument("--banco", type=str, choices=["BB", "SANTANDER"], help="Banco (BB ou SANTANDER)")
    parser.add_argument("--descricao", type=str, help="Descrição parcial do lançamento")
    args = parser.parse_args()

    adapter = get_sql_adapter()
    if not adapter:
        logger.error("❌ SQL Server adapter não disponível")
        return 2

    # Normalizar valores
    valor_float = None
    if args.valor:
        valor_float = _normalizar_valor(args.valor)
        if not valor_float:
            logger.error(f"❌ Valor inválido: {args.valor}")
            return 1
    
    data_dt = None
    if args.data:
        data_dt = _parse_data(args.data)
        if not data_dt:
            logger.error(f"❌ Data inválida: {args.data}")
            return 1

    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 BUSCA DE LANÇAMENTO BANCÁRIO")
    logger.info(f"{'='*70}\n")
    
    if valor_float:
        logger.info(f"💰 Valor: R$ {valor_float:,.2f}")
    if data_dt:
        logger.info(f"📅 Data: {data_dt.strftime('%d/%m/%Y')}")
    if args.banco:
        logger.info(f"🏦 Banco: {args.banco}")
    if args.descricao:
        logger.info(f"📝 Descrição: {args.descricao}")
    
    logger.info("")
    
    # Buscar
    lancamentos = buscar_lancamento(
        adapter,
        valor=valor_float,
        data=data_dt,
        banco=args.banco,
        descricao=args.descricao
    )
    
    if not lancamentos:
        logger.info("❌ Nenhum lançamento encontrado com os critérios especificados.")
        return 0
    
    logger.info(f"✅ Encontrados {len(lancamentos)} lançamento(s):\n")
    
    for i, lanc in enumerate(lancamentos, 1):
        valor = lanc.get("valor_movimentacao") or 0
        sinal = lanc.get("sinal_movimentacao") or ""
        data_mov = lanc.get("data_movimentacao")
        desc = lanc.get("descricao_movimentacao") or ""
        banco = lanc.get("banco_origem") or ""
        processo = lanc.get("processo_referencia") or ""
        id_mov = lanc.get("id_movimentacao")
        
        # Formatar valor com sinal
        if sinal == "D":
            valor_str = f"-R$ {abs(valor):,.2f}"
        else:
            valor_str = f"+R$ {abs(valor):,.2f}"
        
        # Formatar data
        if data_mov:
            if isinstance(data_mov, str):
                data_str = data_mov.split("T")[0] if "T" in data_mov else data_mov.split(" ")[0]
            else:
                data_str = data_mov.strftime("%d/%m/%Y") if hasattr(data_mov, "strftime") else str(data_mov)
        else:
            data_str = "N/A"
        
        logger.info(f"{i}. {valor_str} | {data_str} | {banco}")
        logger.info(f"   ID: {id_mov}")
        logger.info(f"   Descrição: {desc[:100]}{'...' if len(desc) > 100 else ''}")
        if processo:
            logger.info(f"   Processo: {processo}")
        logger.info("")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
