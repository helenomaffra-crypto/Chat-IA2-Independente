#!/usr/bin/env python3
"""
Investiga por que lançamentos duplicados têm hashes diferentes.

Uso:
  python3 scripts/investigar_duplicatas_hash.py --ids "777,906,907"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402
from services.banco_sincronizacao_service import BancoSincronizacaoService  # noqa: E402

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Investigar duplicatas com hash diferente.")
    parser.add_argument("--ids", type=str, required=True, help="IDs dos lançamentos separados por vírgula (ex: 777,906,907)")
    args = parser.parse_args()

    # Parse IDs
    ids = [int(id_str.strip()) for id_str in args.ids.split(",") if id_str.strip()]
    if not ids:
        logger.error("❌ Nenhum ID válido fornecido")
        return 1

    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 INVESTIGANDO DUPLICATAS - {len(ids)} lançamentos")
    logger.info(f"{'='*70}\n")

    # Buscar lançamentos
    adapter = get_sql_adapter()
    if not adapter:
        logger.error("❌ SQL Server não disponível")
        return 1

    # Buscar dados completos dos lançamentos
    ids_str = ",".join(str(id_val) for id_val in ids)
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
            json_dados_originais,
            processo_referencia,
            criado_em,
            (SELECT COUNT(*) FROM dbo.LANCAMENTO_TIPO_DESPESA ltd WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao) as tem_classificacao
        FROM dbo.MOVIMENTACAO_BANCARIA mb
        WHERE id_movimentacao IN ({ids_str})
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

    # Analisar cada lançamento
    service = BancoSincronizacaoService()
    
    for i, lanc in enumerate(lancamentos, 1):
        id_mov = lanc.get('id_movimentacao')
        hash_atual = lanc.get('hash_dados', 'SEM_HASH')
        json_original = lanc.get('json_dados_originais')
        tem_class = lanc.get('tem_classificacao', 0) > 0
        status = "✅ Classificado" if tem_class else "❌ Não classificado"
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📋 LANÇAMENTO {i}: ID {id_mov} - {status}")
        logger.info(f"{'='*70}")
        logger.info(f"Hash atual: {hash_atual}")
        logger.info(f"Criado em: {lanc.get('criado_em')}")
        logger.info(f"Valor: R$ {float(lanc.get('valor_movimentacao', 0)):,.2f}")
        logger.info(f"Data: {lanc.get('data_movimentacao')}")
        logger.info(f"Descrição: {lanc.get('descricao_movimentacao', '')[:100]}...")
        
        # Tentar recriar hash a partir dos dados originais
        if json_original:
            try:
                dados_originais = json.loads(json_original) if isinstance(json_original, str) else json_original
                
                logger.info(f"\n📦 Dados originais (JSON):")
                print(json.dumps(dados_originais, indent=2, ensure_ascii=False, default=str))
                
                # Recriar hash
                banco = lanc.get('banco_origem', 'BB')
                agencia = lanc.get('agencia_origem')
                conta = lanc.get('conta_origem')
                
                hash_recalculado = service.gerar_hash_lancamento(
                    dados_originais,
                    agencia=agencia,
                    conta=conta,
                    banco=banco
                )
                
                logger.info(f"\n🔑 Hash recalculado: {hash_recalculado}")
                
                if hash_recalculado == hash_atual:
                    logger.info("✅ Hash coincide com o armazenado")
                else:
                    logger.warning(f"⚠️ Hash DIFERENTE! Armazenado: {hash_atual[:16]}... Recalculado: {hash_recalculado[:16]}...")
                    
                    # Investigar diferenças
                    logger.info("\n🔍 Investigando diferenças nos campos usados no hash:")
                    
                    if banco == 'BB':
                        numero_doc = dados_originais.get('numeroDocumento') or dados_originais.get('numeroLote', '')
                        logger.info(f"   numeroDocumento: {numero_doc}")
                        logger.info(f"   dataLancamento: {dados_originais.get('dataLancamento', 'N/A')}")
                        logger.info(f"   valorLancamento: {dados_originais.get('valorLancamento', 'N/A')}")
                        logger.info(f"   textoDescricaoHistorico: {dados_originais.get('textoDescricaoHistorico', '')[:50]}...")
                    else:  # SANTANDER
                        transaction_id = dados_originais.get('transactionId', '')
                        logger.info(f"   transactionId: {transaction_id}")
                        logger.info(f"   transactionDate: {dados_originais.get('transactionDate', 'N/A')}")
                        logger.info(f"   amount: {dados_originais.get('amount', 'N/A')}")
                        logger.info(f"   transactionName: {dados_originais.get('transactionName', '')[:50]}...")
                        logger.info(f"   historicComplement: {dados_originais.get('historicComplement', '')[:50]}...")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar JSON original: {e}", exc_info=True)
        else:
            logger.warning("⚠️ Sem dados originais (json_dados_originais está NULL)")

    # Comparar campos entre os lançamentos
    logger.info(f"\n{'='*70}")
    logger.info("🔍 COMPARAÇÃO ENTRE LANÇAMENTOS")
    logger.info(f"{'='*70}\n")
    
    campos_comparacao = ['valor_movimentacao', 'data_movimentacao', 'descricao_movimentacao', 'hash_dados']
    
    for campo in campos_comparacao:
        valores = [str(lanc.get(campo, 'N/A'))[:50] for lanc in lancamentos]
        if len(set(valores)) == 1:
            logger.info(f"✅ {campo}: IGUAL em todos ({valores[0][:50]}...)")
        else:
            logger.warning(f"⚠️ {campo}: DIFERENTE entre lançamentos")
            for i, lanc in enumerate(lancamentos, 1):
                logger.info(f"   {i}. ID {lanc.get('id_movimentacao')}: {str(lanc.get(campo, 'N/A'))[:80]}...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
