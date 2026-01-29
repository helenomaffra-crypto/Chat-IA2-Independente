#!/usr/bin/env python3
"""
Compara documentos DI/DUIMP de 2025 entre bancos legados e DOCUMENTO_ADUANEIRO.

Objetivo:
- Verificar quantos documentos de 2025 estão em DOCUMENTO_ADUANEIRO
- Comparar com fontes originais (Serpro.dbo para DI, Duimp.dbo para DUIMP)
- Listar documentos que estão faltando

Uso:
  python3 scripts/comparar_documentos_2025_bancos.py
  python3 scripts/comparar_documentos_2025_bancos.py --ano 2024
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.sql_server_adapter import get_sql_adapter  # noqa: E402
from services.db_policy_service import get_primary_database  # noqa: E402

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _sql_escape(s: str) -> str:
    """Escapa strings para SQL."""
    return (s or "").replace("'", "''")


def _buscar_dis_serpro(adapter, ano: int) -> List[Dict[str, Any]]:
    """Busca todos os DI de 2025 do Serpro.dbo."""
    db = get_primary_database()
    
    q = f"""
        SELECT DISTINCT
            p.numero_processo AS processo_referencia,
            ddg.numeroDi AS numero_documento,
            ddg.situacaoDi AS situacao_documento,
            diDesp.canalSelecaoParametrizada AS canal_documento,
            diDesp.dataHoraRegistro AS data_registro,
            COALESCE(diDesp.dataHoraRegistro, ddg.dataHoraSituacaoDi) AS data_ordenacao
        FROM {db}.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
        INNER JOIN Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
            ON p.id_importacao = diH.idImportacao
        INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
            ON diH.diId = diRoot.dadosDiId
        INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
            ON diRoot.dadosGeraisId = ddg.dadosGeraisId
        LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
            ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
        WHERE (
            (diDesp.dataHoraRegistro IS NOT NULL AND YEAR(diDesp.dataHoraRegistro) = {ano})
            OR
            (diDesp.dataHoraRegistro IS NULL AND ddg.dataHoraSituacaoDi IS NOT NULL AND YEAR(ddg.dataHoraSituacaoDi) = {ano})
        )
        ORDER BY COALESCE(diDesp.dataHoraRegistro, ddg.dataHoraSituacaoDi) DESC
    """
    
    r = adapter.execute_query(q, database="Make", notificar_erro=False)
    if not r.get("success"):
        logger.error(f"❌ Erro ao buscar DI de {ano} do Serpro: {r.get('error')}")
        return []
    
    rows = r.get("data") or []
    
    # Deduplicar por número DI (pegar o mais recente)
    seen = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        num_doc = str(row.get("numero_documento") or "").strip()
        if not num_doc:
            continue
        
        data_ord = row.get("data_ordenacao")
        if num_doc not in seen:
            seen[num_doc] = row
        else:
            existing_data = seen[num_doc].get("data_ordenacao")
            if data_ord and (not existing_data or data_ord > existing_data):
                seen[num_doc] = row
    
    return list(seen.values())


def _buscar_duimps_duimp_db(adapter, ano: int) -> List[Dict[str, Any]]:
    """Busca todos os DUIMP de 2025 do Duimp.dbo."""
    
    # ✅ CORREÇÃO: Usar subquery com ROW_NUMBER para pegar um registro por número DUIMP
    # Agrupar apenas por número (não por duimp_id) para ter um registro por DUIMP
    q = f"""
        SELECT
            numero_processo AS processo_referencia,
            numero AS numero_documento,
            ultima_situacao AS situacao_documento,
            canal_documento,
            data_registro AS data_registro,
            versao AS versao_documento
        FROM (
            SELECT 
                d.numero_processo,
                d.numero,
                d.ultima_situacao,
                MAX(drar.canal_consolidado) AS canal_documento,
                d.data_registro,
                d.versao,
                ROW_NUMBER() OVER (PARTITION BY d.numero ORDER BY d.data_registro DESC) AS rn
            FROM Duimp.dbo.duimp d WITH (NOLOCK)
            LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar WITH (NOLOCK)
                ON d.duimp_id = drar.duimp_id
            WHERE d.data_registro IS NOT NULL
              AND YEAR(d.data_registro) = {ano}
            GROUP BY 
                d.numero_processo,
                d.numero,
                d.ultima_situacao,
                d.data_registro,
                d.versao
        ) ranked
        WHERE rn = 1
        ORDER BY data_registro DESC
    """
    
    r = adapter.execute_query(q, database="Make", notificar_erro=False)
    if not r.get("success"):
        logger.error(f"❌ Erro ao buscar DUIMP de {ano} do Duimp.dbo: {r.get('error')}")
        return []
    
    return r.get("data") or []


def _buscar_documentos_em_documento_aduaneiro(adapter, tipo: str, numeros: List[str]) -> Set[str]:
    """Busca quais documentos já existem em DOCUMENTO_ADUANEIRO."""
    if not numeros:
        return set()
    
    db = get_primary_database()
    
    # Construir lista de condições (em batches de 500)
    batch_size = 500
    existing = set()
    
    for i in range(0, len(numeros), batch_size):
        batch_numeros = numeros[i:i + batch_size]
        conditions = []
        for num in batch_numeros:
            num_esc = _sql_escape(num)
            conditions.append(f"CAST(numero_documento AS VARCHAR(50)) = '{num_esc}'")
        
        if not conditions:
            continue
        
        q = f"""
            SELECT DISTINCT CAST(numero_documento AS VARCHAR(50)) AS numero_documento
            FROM {db}.dbo.DOCUMENTO_ADUANEIRO
            WHERE CAST(tipo_documento AS VARCHAR(50)) = '{_sql_escape(tipo)}'
              AND ({' OR '.join(conditions)})
        """
        
        try:
            r = adapter.execute_query(q, database=db, notificar_erro=False)
            if r and r.get("success") and r.get("data"):
                for row in r.get("data", []):
                    if isinstance(row, dict):
                        num_doc = str(row.get("numero_documento") or "").strip()
                        if num_doc:
                            existing.add(num_doc)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar documentos existentes (batch {i//batch_size + 1}): {e}")
    
    return existing


def main() -> int:
    parser = argparse.ArgumentParser(description="Comparar documentos DI/DUIMP de 2025 entre bancos.")
    parser.add_argument("--ano", type=int, default=2025, help="Ano para comparar (default: 2025).")
    args = parser.parse_args()

    adapter = get_sql_adapter()
    if not adapter:
        logger.error("❌ SQL Server adapter não disponível")
        return 2

    logger.info(f"\n{'='*70}")
    logger.info(f"📊 COMPARAÇÃO DE DOCUMENTOS {args.ano}")
    logger.info(f"{'='*70}\n")

    # 1. Buscar DI do Serpro
    logger.info(f"🔍 Buscando DI de {args.ano} no Serpro.dbo...")
    dis_serpro = _buscar_dis_serpro(adapter, args.ano)
    logger.info(f"✅ Encontrados {len(dis_serpro)} DI(s) únicos no Serpro.dbo")
    
    if dis_serpro:
        numeros_di = [str(d.get("numero_documento") or "").strip() for d in dis_serpro]
        numeros_di = [n for n in numeros_di if n]
        
        logger.info(f"🔍 Verificando quais DI estão em DOCUMENTO_ADUANEIRO...")
        di_existentes = _buscar_documentos_em_documento_aduaneiro(adapter, "DI", numeros_di)
        logger.info(f"✅ {len(di_existentes)} DI(s) encontrados em DOCUMENTO_ADUANEIRO (de {len(numeros_di)})")
        
        di_faltando = [d for d in dis_serpro if str(d.get("numero_documento") or "").strip() not in di_existentes]
        
        logger.info(f"\n📋 RESUMO DI ({args.ano}):")
        logger.info(f"   ✅ Em DOCUMENTO_ADUANEIRO: {len(di_existentes)}")
        logger.info(f"   ❌ Faltando: {len(di_faltando)}")
        logger.info(f"   📊 Total no Serpro: {len(dis_serpro)}")
        
        if di_faltando:
            logger.info(f"\n❌ DI FALTANDO ({len(di_faltando)}):")
            for di in di_faltando[:20]:  # Mostrar apenas os 20 primeiros
                num = str(di.get("numero_documento") or "").strip()
                proc = str(di.get("processo_referencia") or "").strip()
                data = di.get("data_registro")
                logger.info(f"   - DI {num} (processo: {proc}, registro: {data})")
            if len(di_faltando) > 20:
                logger.info(f"   ... e mais {len(di_faltando) - 20} DI(s)")

    # 2. Buscar DUIMP do Duimp.dbo
    logger.info(f"\n{'='*70}")
    logger.info(f"🔍 Buscando DUIMP de {args.ano} no Duimp.dbo...")
    duimps_duimp_db = _buscar_duimps_duimp_db(adapter, args.ano)
    logger.info(f"✅ Encontrados {len(duimps_duimp_db)} DUIMP(s) no Duimp.dbo")
    
    if duimps_duimp_db:
        numeros_duimp = [str(d.get("numero_documento") or "").strip() for d in duimps_duimp_db]
        numeros_duimp = [n for n in numeros_duimp if n]
        
        logger.info(f"🔍 Verificando quais DUIMP estão em DOCUMENTO_ADUANEIRO...")
        duimp_existentes = _buscar_documentos_em_documento_aduaneiro(adapter, "DUIMP", numeros_duimp)
        logger.info(f"✅ {len(duimp_existentes)} DUIMP(s) encontrados em DOCUMENTO_ADUANEIRO (de {len(numeros_duimp)})")
        
        # ✅ CORREÇÃO: Filtrar corretamente os que estão faltando
        duimp_faltando = []
        for d in duimps_duimp_db:
            num = str(d.get("numero_documento") or "").strip()
            if num and num not in duimp_existentes:
                duimp_faltando.append(d)
        
        logger.info(f"\n📋 RESUMO DUIMP ({args.ano}):")
        logger.info(f"   ✅ Em DOCUMENTO_ADUANEIRO: {len(duimp_existentes)}")
        logger.info(f"   ❌ Faltando: {len(duimp_faltando)}")
        logger.info(f"   📊 Total no Duimp.dbo: {len(duimps_duimp_db)}")
        
        if duimp_faltando:
            logger.info(f"\n❌ DUIMP FALTANDO ({len(duimp_faltando)}):")
            for duimp in duimp_faltando[:20]:  # Mostrar apenas os 20 primeiros
                num = str(duimp.get("numero_documento") or "").strip()
                proc = str(duimp.get("processo_referencia") or "").strip()
                data = duimp.get("data_registro")
                logger.info(f"   - DUIMP {num} (processo: {proc}, registro: {data})")
            if len(duimp_faltando) > 20:
                logger.info(f"   ... e mais {len(duimp_faltando) - 20} DUIMP(s)")

    # Resumo final
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 RESUMO FINAL ({args.ano})")
    logger.info(f"{'='*70}")
    total_serpro = len(dis_serpro) if dis_serpro else 0
    total_duimp_db = len(duimps_duimp_db) if duimps_duimp_db else 0
    total_existentes = (len(di_existentes) if dis_serpro else 0) + (len(duimp_existentes) if duimps_duimp_db else 0)
    total_faltando = (len(di_faltando) if dis_serpro else 0) + (len(duimp_faltando) if duimps_duimp_db else 0)
    
    logger.info(f"📋 Total no Serpro/Duimp.dbo: {total_serpro + total_duimp_db}")
    logger.info(f"✅ Total em DOCUMENTO_ADUANEIRO: {total_existentes}")
    logger.info(f"❌ Total faltando: {total_faltando}")
    logger.info(f"📊 Cobertura: {((total_existentes / (total_serpro + total_duimp_db)) * 100) if (total_serpro + total_duimp_db) > 0 else 0:.1f}%")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
