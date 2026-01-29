#!/usr/bin/env python3
"""
Script de teste isolado para validar relatório de importações normalizado por FOB.

Teste 1: DMD em dezembro/2025 (só tem DI)
Teste 2: VDM em novembro/2025 (só tem DUIMP)
"""

import sys
import os
sys.path.insert(0, '.')

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def normalizar_fob_para_incoterm(
    incoterm: Optional[str],
    vmle_usd: float,
    vmle_brl: float,
    frete_usd: Optional[float] = None,
    frete_brl: Optional[float] = None,
    seguro_usd: Optional[float] = None,
    seguro_brl: Optional[float] = None
) -> Dict[str, Any]:
    """
    Normaliza valor para FOB baseado no INCOTERM.
    
    Returns:
        {
            'fob_usd': float,
            'fob_brl': float,
            'aviso': str (opcional)
        }
    """
    incoterm_upper = (incoterm or '').upper().strip() if incoterm else ''
    
    # INCOTERMs que já são FOB (não precisam ajuste)
    if incoterm_upper in ['FOB', 'EXW', 'FCA']:
        return {
            'fob_usd': vmle_usd,
            'fob_brl': vmle_brl,
            'incoterm': incoterm_upper
        }
    
    # CIF: CIF = FOB + Frete + Seguro
    if incoterm_upper == 'CIF':
        frete_usd = frete_usd or 0.0
        frete_brl = frete_brl or 0.0
        seguro_usd = seguro_usd or 0.0
        seguro_brl = seguro_brl or 0.0
        
        fob_usd = vmle_usd - frete_usd - seguro_usd
        fob_brl = vmle_brl - frete_brl - seguro_brl
        
        # Validação: FOB não pode ser negativo
        if fob_usd < 0 or fob_brl < 0:
            return {
                'fob_usd': vmle_usd,
                'fob_brl': vmle_brl,
                'incoterm': incoterm_upper,
                'aviso': 'FOB calculado foi negativo, usando VMLE original'
            }
        
        return {
            'fob_usd': fob_usd,
            'fob_brl': fob_brl,
            'incoterm': incoterm_upper
        }
    
    # CFR: CFR = FOB + Frete
    if incoterm_upper == 'CFR':
        frete_usd = frete_usd or 0.0
        frete_brl = frete_brl or 0.0
        
        fob_usd = vmle_usd - frete_usd
        fob_brl = vmle_brl - frete_brl
        
        if fob_usd < 0 or fob_brl < 0:
            return {
                'fob_usd': vmle_usd,
                'fob_brl': vmle_brl,
                'incoterm': incoterm_upper,
                'aviso': 'FOB calculado foi negativo, usando VMLE original'
            }
        
        return {
            'fob_usd': fob_usd,
            'fob_brl': fob_brl,
            'incoterm': incoterm_upper
        }
    
    # Outros INCOTERMs ou não informado: assumir que já é FOB
    return {
        'fob_usd': vmle_usd,
        'fob_brl': vmle_brl,
        'incoterm': incoterm_upper or 'NÃO INFORMADO',
        'aviso': f'INCOTERM {incoterm_upper or "NÃO INFORMADO"} não suportado ou não informado, usando valor original como FOB'
    }


def buscar_dmd_dezembro_2025() -> List[Dict[str, Any]]:
    """Busca processos DMD desembaraçados em dezembro/2025 com DI diretamente do SQL Server."""
    try:
        from utils.sql_server_adapter import get_sql_adapter
        sql_adapter = get_sql_adapter()
        
        # Query para buscar processos DMD com DI desembaraçados em dezembro/2025 diretamente do SQL Server
        # ✅ NOVO: Agrupar por processo para evitar duplicatas e somar frete/seguro quando houver múltiplos
        # ✅ NOVO: Tentar buscar INCOTERM da tabela Di_Adicao (se existir)
        query = '''
            -- ✅ CORREÇÃO: A DI só existe uma, mas pode haver múltiplos registros de frete/seguro
            -- Vamos pegar apenas UMA linha por processo, priorizando a que tem dataHoraDesembaraco mais recente
            WITH DI_POR_PROCESSO AS (
                SELECT 
                    p.numero_processo,
                    p.numero_di,
                    diDesp.dataHoraDesembaraco,
                    diRoot.dadosDiId,
                    diRoot.valorMercadoriaDescargaId,
                    ddg.situacaoDi,
                    ddg.numeroDi,
                    ddg.dataHoraSituacaoDi,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.numero_processo 
                        ORDER BY 
                            CASE WHEN diDesp.dataHoraDesembaraco IS NOT NULL THEN 0 ELSE 1 END,
                            COALESCE(diDesp.dataHoraDesembaraco, ddg.dataHoraSituacaoDi) DESC
                    ) AS rn
                FROM make.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                INNER JOIN Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
                    ON p.id_importacao = diH.idImportacao
                INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                    ON diH.diId = diRoot.dadosDiId
                INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                WHERE p.numero_processo LIKE 'DMD.%'
                  -- ✅ Filtrar por dataHoraDesembaraco se existir, senão usar dataHoraSituacaoDi
                  AND (
                      (diDesp.dataHoraDesembaraco IS NOT NULL 
                       AND YEAR(diDesp.dataHoraDesembaraco) = 2025 
                       AND MONTH(diDesp.dataHoraDesembaraco) = 12)
                      OR
                      (diDesp.dataHoraDesembaraco IS NULL 
                       AND YEAR(ddg.dataHoraSituacaoDi) = 2025 
                       AND MONTH(ddg.dataHoraSituacaoDi) = 12)
                  )
            )
            SELECT 
                dpp.numero_processo,
                dpp.numero_di,
                dpp.dataHoraDesembaraco,
                -- ✅ CORREÇÃO: Usar VMLD (Valor Mercadoria Descarga) ao invés de VMLE
                -- VMLD sempre inclui frete e seguro, então FOB = VMLD - Frete - Seguro
                CAST(ISNULL(DVMD.totalDolares, 0) AS FLOAT) AS vmld_usd,
                CAST(ISNULL(DVMD.totalReais, 0) AS FLOAT) AS vmld_brl,
                -- ✅ CORREÇÃO: Pegar apenas o frete da DI (relação 1:1 com dadosDiId)
                -- Segundo MAPEAMENTO_SQL_SERVER.md linha 441: Di_Root_Declaracao_Importacao.dadosDiId = Di_Frete.freteId
                CAST(ISNULL(diFrete.valorTotalDolares, 0) AS FLOAT) AS frete_usd,
                CAST(ISNULL(diFrete.totalReais, 0) AS FLOAT) AS frete_brl,
                -- ✅ CORREÇÃO: Pegar apenas o seguro da DI (relação 1:1 com dadosDiId)
                -- Segundo MAPEAMENTO_SQL_SERVER.md linha 452: Di_Root_Declaracao_Importacao.dadosDiId = Di_Seguro.seguroId
                CAST(ISNULL(diSeguro.valorTotalDolares, 0) AS FLOAT) AS seguro_usd,
                CAST(ISNULL(diSeguro.valorTotalReais, 0) AS FLOAT) AS seguro_brl,
                dpp.situacaoDi,
                dpp.dadosDiId,
                dpp.numeroDi
            FROM DI_POR_PROCESSO dpp
            -- ✅ CORREÇÃO: Usar Di_Valor_Mercadoria_Descarga (VMLD) ao invés de Di_Valor_Mercadoria_Embarque (VMLE)
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD WITH (NOLOCK)
                ON dpp.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
            -- ✅ JOIN correto segundo MAPEAMENTO_SQL_SERVER.md linha 441: dadosDiId = freteId
            -- ⚠️ Usar TOP 1 para garantir apenas um registro de frete por dadosDiId
            LEFT JOIN (
                SELECT 
                    freteId,
                    valorTotalDolares,
                    totalReais,
                    ROW_NUMBER() OVER (PARTITION BY freteId ORDER BY valorTotalDolares DESC) AS rn_frete
                FROM Serpro.dbo.Di_Frete WITH (NOLOCK)
            ) diFrete ON dpp.dadosDiId = diFrete.freteId AND diFrete.rn_frete = 1
            -- ✅ JOIN correto segundo MAPEAMENTO_SQL_SERVER.md linha 452: dadosDiId = seguroId
            -- ⚠️ Usar TOP 1 para garantir apenas um registro de seguro por dadosDiId
            LEFT JOIN (
                SELECT 
                    seguroId,
                    valorTotalDolares,
                    valorTotalReais,
                    ROW_NUMBER() OVER (PARTITION BY seguroId ORDER BY valorTotalDolares DESC) AS rn_seguro
                FROM Serpro.dbo.Di_Seguro WITH (NOLOCK)
            ) diSeguro ON dpp.dadosDiId = diSeguro.seguroId AND diSeguro.rn_seguro = 1
            WHERE dpp.rn = 1
            ORDER BY dpp.numero_processo
        '''
        
        logger.info("🔍 Buscando processos DMD desembaraçados em dezembro/2025 diretamente do SQL Server...")
        result = sql_adapter.execute_query(query, 'Make', None)
        
        if not result.get('success'):
            logger.error(f"❌ Erro ao buscar processos DMD: {result.get('error')}")
            return []
        
        rows = result.get('data', [])
        logger.info(f"✅ Encontrados {len(rows)} processos DMD em dezembro/2025 no SQL Server")
        
        processos = []
        for row in rows:
            # ✅ CORREÇÃO: Usar VMLD (Valor Mercadoria Descarga) ao invés de VMLE
            # VMLD sempre inclui frete e seguro, então FOB = VMLD - Frete - Seguro
            vmld_usd = float(str(row.get('vmld_usd') or 0).replace(',', '.')) if row.get('vmld_usd') else 0.0
            vmld_brl = float(str(row.get('vmld_brl') or 0).replace(',', '.')) if row.get('vmld_brl') else 0.0
            frete_usd = float(str(row.get('frete_usd') or 0).replace(',', '.')) if row.get('frete_usd') else 0.0
            frete_brl = float(str(row.get('frete_brl') or 0).replace(',', '.')) if row.get('frete_brl') else 0.0
            seguro_usd = float(str(row.get('seguro_usd') or 0).replace(',', '.')) if row.get('seguro_usd') else 0.0
            seguro_brl = float(str(row.get('seguro_brl') or 0).replace(',', '.')) if row.get('seguro_brl') else 0.0
            
            # ✅ DEBUG: Log para verificar valores
            dados_di_id = row.get('dadosDiId')
            numero_di = row.get('numeroDi') or row.get('numero_di')
            numero_processo = row.get('numero_processo')
            logger.info(f"🔍 Processo {numero_processo}: dadosDiId={dados_di_id}, numeroDi={numero_di}")
            logger.info(f"   VMLD: USD ${vmld_usd:,.2f}, BRL R$ {vmld_brl:,.2f}")
            logger.info(f"   Frete: USD ${frete_usd:,.2f}, BRL R$ {frete_brl:,.2f}")
            logger.info(f"   Seguro: USD ${seguro_usd:,.2f}, BRL R$ {seguro_brl:,.2f}")
            
            # ✅ LÓGICA DI: FOB = VMLD - Frete - Seguro (quando tiver)
            # VMLD sempre inclui frete e seguro, então subtraímos para obter o FOB
            fob_usd = vmld_usd - frete_usd - seguro_usd
            fob_brl = vmld_brl - frete_brl - seguro_brl
            
            # Garantir que FOB não seja negativo
            if fob_usd < 0:
                logger.warning(f"⚠️ Processo {row.get('numero_processo')}: FOB calculado negativo (USD {fob_usd}), ajustando para 0")
                fob_usd = 0.0
            if fob_brl < 0:
                logger.warning(f"⚠️ Processo {row.get('numero_processo')}: FOB calculado negativo (BRL {fob_brl}), ajustando para 0")
                fob_brl = 0.0
            
            # Calcular porcentagem do frete em relação ao FOB
            frete_pct_fob_usd = (frete_usd / fob_usd * 100) if fob_usd > 0 else 0.0
            frete_pct_fob_brl = (frete_brl / fob_brl * 100) if fob_brl > 0 else 0.0
            
            processos.append({
                'numero_processo': row.get('numero_processo'),
                'numero_di': row.get('numero_di'),
                'data_desembaraco': row.get('dataHoraDesembaraco'),
                'vmld_usd': vmld_usd,
                'vmld_brl': vmld_brl,
                'frete_usd': frete_usd,
                'frete_brl': frete_brl,
                'seguro_usd': seguro_usd,
                'seguro_brl': seguro_brl,
                'fob_usd': fob_usd,
                'fob_brl': fob_brl,
                'frete_pct_fob_usd': frete_pct_fob_usd,
                'frete_pct_fob_brl': frete_pct_fob_brl,
                'incoterm': 'FOB',  # Calculado a partir de VMLD
                'aviso': None
            })
        
        logger.info(f"✅ Processados {len(processos)} processos DMD de dezembro/2025")
        return processos
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar processos DMD: {e}", exc_info=True)
        return []


def buscar_vdm_novembro_2025() -> List[Dict[str, Any]]:
    """Busca processos VDM desembaraçados em novembro/2025 com DUIMP diretamente do SQL Server."""
    try:
        from utils.sql_server_adapter import get_sql_adapter
        sql_adapter = get_sql_adapter()
        
        # Query para buscar processos VDM com DUIMP desembaraçados em dezembro/2025 diretamente do SQL Server
        # ✅ CORREÇÃO: Usar duimp_diagnostico.data_geracao para filtrar por data (quando situação é DESEMBARACADA)
        # ⚠️ Pode haver múltiplos registros em duimp_diagnostico, então usar ROW_NUMBER() para pegar apenas um por processo
        # ✅ NOVO: Buscar frete do CE relacionado à DUIMP (via id_importacao)
        query = '''
            WITH DUIMP_POR_PROCESSO AS (
                SELECT 
                    p.numero_processo,
                    p.id_importacao,
                    d.numero AS numero_duimp,
                    dd.data_geracao AS data_desembaraco,
                    tm.valor_total_local_embarque_usd AS fob_usd,
                    tm.valor_total_local_embarque_brl AS fob_brl,
                    dd.situacao_duimp AS situacao_duimp,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.numero_processo 
                        ORDER BY dd.data_geracao DESC
                    ) AS rn
                FROM make.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                INNER JOIN duimp.dbo.duimp d WITH (NOLOCK)
                    ON p.numero_duimp = d.numero
                INNER JOIN duimp.dbo.duimp_tributos_mercadoria tm WITH (NOLOCK)
                    ON d.duimp_id = tm.duimp_id
                INNER JOIN duimp.dbo.duimp_diagnostico dd WITH (NOLOCK)
                    ON d.duimp_id = dd.duimp_id
                WHERE p.numero_processo LIKE 'VDM.%'
                  -- ✅ Buscar DUIMPs desembaraçadas (pode ter múltiplas situações)
                  AND (dd.situacao_duimp LIKE '%DESEMBARACADA%' OR dd.situacao_duimp LIKE '%ENTREGUE%')
                  AND YEAR(dd.data_geracao) = 2025
                  AND MONTH(dd.data_geracao) = 12
            )
            SELECT 
                dpp.numero_processo,
                dpp.numero_duimp,
                dpp.data_desembaraco,
                dpp.fob_usd,
                dpp.fob_brl,
                dpp.situacao_duimp,
                -- ✅ NOVO: Buscar frete do CE relacionado (via id_importacao)
                -- ⚠️ Pode haver múltiplos CEs, então usar subquery com TOP 1
                (SELECT TOP 1 CAST(ISNULL(ceRoot2.valorFreteTotal, 0) AS FLOAT)
                 FROM Serpro.dbo.Hi_Historico_Ce ceH2 WITH (NOLOCK)
                 INNER JOIN Serpro.dbo.Ce_Root_Conhecimento_Embarque ceRoot2 WITH (NOLOCK)
                     ON ceH2.ceId = ceRoot2.rootConsultaEmbarqueId
                 WHERE ceH2.idImportacao = dpp.id_importacao
                 ORDER BY ceRoot2.updatedAt DESC) AS frete_brl
            FROM DUIMP_POR_PROCESSO dpp
            WHERE dpp.rn = 1
            ORDER BY dpp.numero_processo
        '''
        
        logger.info("🔍 Buscando processos VDM desembaraçados em dezembro/2025 diretamente do SQL Server...")
        result = sql_adapter.execute_query(query, 'duimp', None)
        
        if not result.get('success'):
            logger.error(f"❌ Erro ao buscar processos VDM: {result.get('error')}")
            # ✅ DEBUG: Tentar query mais simples para verificar se há processos VDM
            query_debug = '''
                SELECT COUNT(*) AS total
                FROM make.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                WHERE p.numero_processo LIKE 'VDM.%'
            '''
            result_debug = sql_adapter.execute_query(query_debug, 'Make', None)
            if result_debug.get('success'):
                total_vdm = result_debug.get('data', [{}])[0].get('total', 0)
                logger.info(f"🔍 DEBUG: Total de processos VDM no banco: {total_vdm}")
            return []
        
        rows = result.get('data', [])
        logger.info(f"✅ Encontrados {len(rows)} processos VDM em dezembro/2025 no SQL Server")
        
        # ✅ DEBUG: Se não encontrou nenhum, verificar se há processos VDM com DUIMP em qualquer mês
        if len(rows) == 0:
            query_debug2 = '''
                SELECT COUNT(*) AS total
                FROM make.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                INNER JOIN duimp.dbo.duimp d WITH (NOLOCK)
                    ON p.numero_duimp = d.numero
                WHERE p.numero_processo LIKE 'VDM.%'
            '''
            result_debug2 = sql_adapter.execute_query(query_debug2, 'duimp', None)
            if result_debug2.get('success'):
                total_vdm_duimp = result_debug2.get('data', [{}])[0].get('total', 0)
                logger.info(f"🔍 DEBUG: Total de processos VDM com DUIMP: {total_vdm_duimp}")
        
        processos = []
        for row in rows:
            # Converter valores para float
            fob_usd = float(str(row.get('fob_usd') or 0).replace(',', '.')) if row.get('fob_usd') else 0.0
            fob_brl = float(str(row.get('fob_brl') or 0).replace(',', '.')) if row.get('fob_brl') else 0.0
            frete_brl = float(str(row.get('frete_brl') or 0).replace(',', '.')) if row.get('frete_brl') else 0.0
            
            # ✅ Calcular porcentagem do frete em relação ao FOB
            frete_pct_fob_brl = (frete_brl / fob_brl * 100) if fob_brl > 0 else 0.0
            
            processos.append({
                'numero_processo': row.get('numero_processo'),
                'numero_duimp': row.get('numero_duimp'),
                'data_desembaraco': row.get('data_desembaraco'),
                'fob_usd': fob_usd,
                'fob_brl': fob_brl,
                'frete_brl': frete_brl,
                'frete_pct_fob_brl': frete_pct_fob_brl,
                'incoterm': 'FOB',  # DUIMP já retorna FOB direto
            })
        
        logger.info(f"✅ Processados {len(processos)} processos VDM de dezembro/2025")
        return processos
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar processos VDM: {e}", exc_info=True)
        return []


def main():
    """Executa testes isolados."""
    print("=" * 80)
    print("TESTE ISOLADO: Relatório de Importações Normalizado por FOB")
    print("=" * 80)
    print()
    
    # Teste 1: DMD em dezembro/2025
    print("📊 TESTE 1: DMD em dezembro/2025 (só tem DI)")
    print("-" * 80)
    processos_dmd = buscar_dmd_dezembro_2025()
    
    if not processos_dmd:
        print("❌ Nenhum processo DMD encontrado em dezembro/2025")
    else:
        total_fob_usd = 0.0
        total_fob_brl = 0.0
        total_vmle_usd = 0.0
        total_vmle_brl = 0.0
        
        print(f"\n✅ Encontrados {len(processos_dmd)} processos DMD:")
        print()
        
        for proc in processos_dmd:
            print(f"  📦 {proc['numero_processo']} - DI: {proc['numero_di']}")
            print(f"     Data Desembaraço: {proc['data_desembaraco']}")
            print(f"     VMLD (USD): ${proc['vmld_usd']:,.2f}")
            print(f"     VMLD (BRL): R$ {proc['vmld_brl']:,.2f}")
            if proc['frete_usd'] > 0 or proc['frete_brl'] > 0:
                print(f"     Frete (USD): ${proc['frete_usd']:,.2f} ({proc['frete_pct_fob_usd']:.1f}% do FOB)")
                print(f"     Frete (BRL): R$ {proc['frete_brl']:,.2f} ({proc['frete_pct_fob_brl']:.1f}% do FOB)")
            if proc['seguro_usd'] > 0 or proc['seguro_brl'] > 0:
                print(f"     Seguro (USD): ${proc['seguro_usd']:,.2f}")
                print(f"     Seguro (BRL): R$ {proc['seguro_brl']:,.2f}")
            print(f"     INCOTERM: {proc['incoterm']} (calculado: FOB = VMLD - Frete - Seguro)")
            print(f"     FOB Normalizado (USD): ${proc['fob_usd']:,.2f}")
            print(f"     FOB Normalizado (BRL): R$ {proc['fob_brl']:,.2f}")
            print()
            
            total_fob_usd += proc['fob_usd']
            total_fob_brl += proc['fob_brl']
            total_vmle_usd += proc['vmld_usd']
            total_vmle_brl += proc['vmld_brl']
        
        print("-" * 80)
        print("📊 RESUMO DMD - Dezembro/2025:")
        print(f"   Total de Processos: {len(processos_dmd)}")
        print(f"   Total VMLD (USD): ${total_vmle_usd:,.2f}")
        print(f"   Total VMLD (BRL): R$ {total_vmle_brl:,.2f}")
        print(f"   Total FOB Normalizado (USD): ${total_fob_usd:,.2f}")
        print(f"   Total FOB Normalizado (BRL): R$ {total_fob_brl:,.2f}")
        print(f"   (FOB = VMLD - Frete - Seguro)")
        print()
    
    print()
    print("=" * 80)
    print()
    
    # Teste 2: VDM em novembro/2025
    print("📊 TESTE 2: VDM em novembro/2025 (só tem DUIMP)")
    print("-" * 80)
    processos_vdm = buscar_vdm_novembro_2025()
    
    if not processos_vdm:
        print("❌ Nenhum processo VDM encontrado em novembro/2025")
    else:
        total_fob_usd = 0.0
        total_fob_brl = 0.0
        
        print(f"\n✅ Encontrados {len(processos_vdm)} processos VDM:")
        print()
        
        for proc in processos_vdm:
            print(f"  📦 {proc['numero_processo']} - DUIMP: {proc['numero_duimp']}")
            print(f"     Data Desembaraço: {proc['data_desembaraco']}")
            print(f"     FOB (USD): ${proc['fob_usd']:,.2f}")
            print(f"     FOB (BRL): R$ {proc['fob_brl']:,.2f}")
            if proc['frete_brl'] > 0:
                print(f"     Frete (BRL): R$ {proc['frete_brl']:,.2f} ({proc['frete_pct_fob_brl']:.1f}% do FOB)")
            print()
            
            total_fob_usd += proc['fob_usd']
            total_fob_brl += proc['fob_brl']
        
        print("-" * 80)
        print("📊 RESUMO VDM - Dezembro/2025:")
        print(f"   Total de Processos: {len(processos_vdm)}")
        print(f"   Total FOB (USD): ${total_fob_usd:,.2f}")
        print(f"   Total FOB (BRL): R$ {total_fob_brl:,.2f}")
        print()
    
    print("=" * 80)
    print("✅ Teste concluído!")


if __name__ == '__main__':
    main()

