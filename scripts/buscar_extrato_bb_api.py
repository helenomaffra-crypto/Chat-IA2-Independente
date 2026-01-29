#!/usr/bin/env python3
"""
Busca extrato do Banco do Brasil via API e mostra lançamentos com valor específico.

Uso:
  python3 scripts/buscar_extrato_bb_api.py --valor "13.337,88" --data "22/01/2026" --agencia "1251" --conta "50483"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from services.banco_sincronizacao_service import BancoSincronizacaoService  # noqa: E402

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
    parser = argparse.ArgumentParser(description="Buscar extrato BB via API e filtrar por valor.")
    parser.add_argument("--valor", type=str, required=True, help="Valor do lançamento (ex: 13.337,88 ou 13337.88)")
    parser.add_argument("--data", type=str, required=True, help="Data do lançamento (DD/MM/YYYY ou YYYY-MM-DD)")
    parser.add_argument("--agencia", type=str, required=True, help="Agência")
    parser.add_argument("--conta", type=str, required=True, help="Conta")
    parser.add_argument("--dias", type=int, default=1, help="Dias retroativos (padrão: 1)")
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
    logger.info(f"🔍 BUSCANDO EXTRATO BB VIA API")
    logger.info(f"💰 Valor procurado: R$ {valor_procurado:,.2f}")
    logger.info(f"📅 Data: {data_dt.strftime('%d/%m/%Y')}")
    logger.info(f"🏦 Agência: {args.agencia} | Conta: {args.conta}")
    logger.info(f"{'='*70}\n")

    # Buscar extrato via API (sem importar)
    try:
        service = BancoSincronizacaoService()
        
        if not service.bb_service:
            logger.error("❌ BancoBrasilService não disponível")
            return 1
        
        # Usar mesma data para início e fim (extrato de um dia)
        data_str = data_dt.strftime("%Y-%m-%d")
        
        logger.info(f"📅 Consultando API Banco do Brasil para data: {data_str}")
        logger.info("")
        
        # ✅ Buscar diretamente da API sem importar
        resultado_consulta = service.bb_service.consultar_extrato(
            agencia=args.agencia,
            conta=args.conta,
            data_inicio=data_dt,
            data_fim=data_dt
        )
        
        if not resultado_consulta.get("sucesso"):
            logger.error(f"❌ Erro ao consultar extrato: {resultado_consulta.get('erro', 'Erro desconhecido')}")
            return 1
        
        # Buscar lançamentos do resultado da API
        lancamentos_api = resultado_consulta.get("dados", {}).get("lancamentos", [])
        if not lancamentos_api:
            logger.warning("⚠️ Nenhum lançamento retornado pela API")
            return 0
        
        logger.info(f"📊 Total de lançamentos retornados pela API: {len(lancamentos_api)}\n")
        
        # Filtrar lançamentos com valor próximo
        encontrados = []
        for lanc in lancamentos_api:
            valor_lanc = float(lanc.get('valorLancamento', 0) or 0)
            if abs(abs(valor_lanc) - valor_procurado) < 0.01:
                encontrados.append(lanc)
        
        if not encontrados:
            logger.warning(f"⚠️ Nenhum lançamento encontrado com valor R$ {valor_procurado:,.2f}")
            logger.info("\n📋 Todos os lançamentos retornados pela API:")
            for i, lanc in enumerate(lancamentos_api[:20], 1):  # Mostrar primeiros 20
                valor = float(lanc.get('valorLancamento', 0) or 0)
                data_lanc = lanc.get('dataLancamento', 0)
                descricao = lanc.get('textoDescricaoHistorico', '')[:50]
                logger.info(f"  {i}. Valor: R$ {valor:,.2f} | Data: {data_lanc} | {descricao}...")
            return 0
        
        logger.info(f"✅ Encontrados {len(encontrados)} lançamento(s) com valor R$ {valor_procurado:,.2f}\n")
        
        # Mostrar detalhes dos lançamentos encontrados
        for i, lanc in enumerate(encontrados, 1):
            logger.info(f"{'='*70}")
            logger.info(f"📋 LANÇAMENTO {i} DA API")
            logger.info(f"{'='*70}")
            logger.info(f"Valor: R$ {float(lanc.get('valorLancamento', 0)):,.2f}")
            logger.info(f"Data: {lanc.get('dataLancamento', 'N/A')}")
            logger.info(f"Tipo: {lanc.get('tipoLancamento', 'N/A')}")
            logger.info(f"Indicador: {lanc.get('indicadorSinalLancamento', 'N/A')}")
            logger.info(f"Número Documento: {lanc.get('numeroDocumento', 'N/A')}")
            logger.info(f"Número Lote: {lanc.get('numeroLote', 'N/A')}")
            logger.info(f"Código Histórico: {lanc.get('codigoHistorico', 'N/A')}")
            logger.info(f"Descrição: {lanc.get('textoDescricaoHistorico', 'N/A')}")
            logger.info(f"Info Complementar: {lanc.get('textoInformacaoComplementar', 'N/A')}")
            logger.info(f"\n📦 JSON completo:")
            print(json.dumps(lanc, indent=2, ensure_ascii=False, default=str))
            logger.info("")
        
        # Resumo
        logger.info(f"{'='*70}")
        logger.info("📊 RESUMO:")
        logger.info(f"   Total de lançamentos na API: {len(lancamentos_api)}")
        logger.info(f"   Lançamentos com valor R$ {valor_procurado:,.2f}: {len(encontrados)}")
        logger.info(f"{'='*70}\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
