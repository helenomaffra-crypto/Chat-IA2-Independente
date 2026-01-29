#!/usr/bin/env python3
"""
Busca extrato do Santander de uma data específica e mostra JSON puro.

Uso:
  python3 scripts/buscar_extrato_santander_json.py --data 22/01/2026
  python3 scripts/buscar_extrato_santander_json.py --data 2026-01-22
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402
from services.santander_service import SantanderService  # noqa: E402

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Buscar extrato Santander e mostrar JSON puro.")
    parser.add_argument("--data", type=str, required=True, help="Data do extrato (DD/MM/YYYY ou YYYY-MM-DD)")
    parser.add_argument("--agencia", type=str, help="Agência (opcional, usa padrão do .env se não fornecido)")
    parser.add_argument("--conta", type=str, help="Conta (opcional, usa padrão do .env se não fornecido)")
    args = parser.parse_args()

    # Parse data
    data_dt = _parse_data(args.data)
    if not data_dt:
        logger.error(f"❌ Data inválida: {args.data}")
        return 1

    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 BUSCANDO EXTRATO SANTANDER - {data_dt.strftime('%d/%m/%Y')}")
    logger.info(f"{'='*70}\n")

    # Buscar extrato via SantanderService
    try:
        service = SantanderService()
        
        # Usar mesma data para início e fim (extrato de um dia)
        data_str = data_dt.strftime("%Y-%m-%d")
        
        # Se não forneceu agência/conta, listar contas e usar a primeira
        agencia = args.agencia
        conta = args.conta
        statement_id = None
        
        if not agencia or not conta:
            logger.info("🔍 Agência/conta não fornecidas. Listando contas disponíveis...")
            resultado_contas = service.listar_contas()
            if resultado_contas.get("sucesso"):
                contas = resultado_contas.get("dados", [])
                if contas:
                    primeira_conta = contas[0]
                    # Tentar diferentes campos possíveis
                    statement_id = primeira_conta.get("statementId") or primeira_conta.get("id") or primeira_conta.get("accountId")
                    agencia = primeira_conta.get("branchCode") or primeira_conta.get("branch") or primeira_conta.get("agencia")
                    conta = primeira_conta.get("number") or primeira_conta.get("accountNumber") or primeira_conta.get("conta")
                    logger.info(f"✅ Usando primeira conta disponível:")
                    logger.info(f"   Statement ID: {statement_id}")
                    logger.info(f"   Agência: {agencia}")
                    logger.info(f"   Conta: {conta}")
                else:
                    logger.error("❌ Nenhuma conta encontrada")
                    return 1
            else:
                logger.error(f"❌ Erro ao listar contas: {resultado_contas.get('erro', 'Erro desconhecido')}")
                return 1
        
        logger.info(f"📅 Consultando API Santander para data: {data_str}")
        if statement_id:
            logger.info(f"🏦 Statement ID: {statement_id}")
        else:
            logger.info(f"🏦 Agência: {agencia}")
            logger.info(f"🏦 Conta: {conta}")
        logger.info("")
        
        resultado = service.consultar_extrato(
            agencia=agencia,
            conta=conta,
            statement_id=statement_id,
            data_inicio=data_str,
            data_fim=data_str
        )
        
        if not resultado.get("sucesso"):
            logger.error(f"❌ Erro ao consultar extrato: {resultado.get('erro', 'Erro desconhecido')}")
            return 1
        
        dados = resultado.get("dados")
        if not dados:
            logger.warning("⚠️ Nenhum dado retornado")
            return 0
        
        # Mostrar JSON puro
        logger.info("📋 JSON PURO DO EXTRATO:\n")
        print(json.dumps(dados, indent=2, ensure_ascii=False, default=str))
        logger.info("")
        
        # Resumo
        if isinstance(dados, dict):
            lancamentos = dados.get("lancamentos") or dados.get("transacoes") or []
            if isinstance(lancamentos, list):
                logger.info(f"✅ Total de lançamentos encontrados: {len(lancamentos)}")
                
                # Procurar pelo valor específico
                valor_procurado = 13337.88
                encontrados = []
                for lanc in lancamentos:
                    if isinstance(lanc, dict):
                        valor = lanc.get("valor") or lanc.get("amount") or lanc.get("valor_movimentacao")
                        if valor:
                            try:
                                valor_float = float(str(valor).replace(",", "."))
                                if abs(abs(valor_float) - abs(valor_procurado)) < 0.01:
                                    encontrados.append(lanc)
                            except Exception:
                                pass
                
                if encontrados:
                    logger.info(f"\n💰 Encontrados {len(encontrados)} lançamento(s) com valor próximo a R$ 13.337,88:")
                    for i, lanc in enumerate(encontrados, 1):
                        logger.info(f"\n{i}. Lançamento:")
                        print(json.dumps(lanc, indent=2, ensure_ascii=False, default=str))
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
