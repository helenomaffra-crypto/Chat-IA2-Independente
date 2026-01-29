"""
Serviço para geração de relatório de importações normalizado por FOB.

Gera relatório de importações por categoria (DMD, VDM, etc.) com valores
normalizados para FOB, considerando diferentes INCOTERMs (FOB, CIF, CFR).

Para DI: FOB = VMLD - Frete - Seguro
Para DUIMP: FOB já está disponível diretamente
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def _sql_escape(value: str) -> str:
    return (value or '').replace("'", "''")


def _sql_quote(value: Optional[str]) -> str:
    if value is None:
        return 'NULL'
    return f"'{_sql_escape(str(value))}'"


def _sql_decimal(value: Optional[float]) -> str:
    if value is None:
        return 'NULL'
    try:
        # Garantir ponto como separador decimal
        return str(float(value))
    except Exception:
        return 'NULL'


def _persistir_valores_mercadoria_sql_server(
    processos: List[Dict[str, Any]],
    fonte_dados: str = 'RELATORIO_FOB',
) -> None:
    """
    Persiste valores calculados na tabela mAIke_assistente.dbo.VALOR_MERCADORIA.

    ✅ Objetivo: popular tabela que hoje está vazia e permitir consultas futuras no banco novo.
    ✅ Chave natural de upsert: (processo_referencia, numero_documento, tipo_documento, tipo_valor, moeda).
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        import json as _json

        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            return

        # Montar linhas (uma linha por tipo_valor x moeda quando houver valor)
        linhas: List[Dict[str, Any]] = []

        for proc in processos or []:
            processo_ref = proc.get('numero_processo')
            tipo_doc = (proc.get('tipo_documento') or '').upper().strip() or None
            numero_doc = proc.get('numero_di') or proc.get('numero_duimp')
            data_valor = proc.get('data_desembaraco') or proc.get('dataHoraDesembaraco')

            if not processo_ref or not tipo_doc or not numero_doc:
                continue

            # Mapear campos disponíveis
            candidatos = []
            # FOB sempre
            candidatos.append(('FOB', 'USD', proc.get('fob_usd')))
            candidatos.append(('FOB', 'BRL', proc.get('fob_brl')))

            # DI: VMLD, FRETE, SEGURO
            if tipo_doc == 'DI':
                candidatos.append(('VMLD', 'USD', proc.get('vmld_usd')))
                candidatos.append(('VMLD', 'BRL', proc.get('vmld_brl')))
                candidatos.append(('FRETE', 'USD', proc.get('frete_usd')))
                candidatos.append(('FRETE', 'BRL', proc.get('frete_brl')))
                candidatos.append(('SEGURO', 'USD', proc.get('seguro_usd')))
                candidatos.append(('SEGURO', 'BRL', proc.get('seguro_brl')))

            # DUIMP: frete_brl (se houver)
            if tipo_doc == 'DUIMP':
                candidatos.append(('FRETE', 'BRL', proc.get('frete_brl')))

            payload = None
            try:
                payload = _json.dumps(proc, ensure_ascii=False, default=str)
            except Exception:
                payload = None

            for tipo_valor, moeda, valor in candidatos:
                if valor is None:
                    continue
                try:
                    valor_f = float(valor)
                except Exception:
                    continue
                # Evitar inserir zeros "vazios" demais
                if valor_f == 0.0:
                    continue
                linhas.append({
                    'processo_referencia': str(processo_ref),
                    'numero_documento': str(numero_doc),
                    'tipo_documento': str(tipo_doc),
                    'tipo_valor': str(tipo_valor),
                    'moeda': str(moeda),
                    'valor': valor_f,
                    'data_valor': data_valor,
                    'fonte_dados': fonte_dados,
                    'json_dados_originais': payload,
                })

        if not linhas:
            return

        # Executar MERGE por linha (simples e robusto; volume típico é aceitável)
        for row in linhas:
            processo_referencia = _sql_quote(row['processo_referencia'])
            numero_documento = _sql_quote(row['numero_documento'])
            tipo_documento = _sql_quote(row['tipo_documento'])
            tipo_valor = _sql_quote(row['tipo_valor'])
            moeda = _sql_quote(row['moeda'])
            valor_sql = _sql_decimal(row['valor'])
            data_valor_sql = _sql_quote(row.get('data_valor'))
            fonte_sql = _sql_quote(row.get('fonte_dados') or fonte_dados)
            json_sql = _sql_quote(row.get('json_dados_originais'))

            merge = f"""
            MERGE mAIke_assistente.dbo.VALOR_MERCADORIA WITH (HOLDLOCK) AS tgt
            USING (
                SELECT
                    {processo_referencia} AS processo_referencia,
                    {numero_documento} AS numero_documento,
                    {tipo_documento} AS tipo_documento,
                    {tipo_valor} AS tipo_valor,
                    {moeda} AS moeda
            ) AS src
            ON tgt.processo_referencia = src.processo_referencia
               AND tgt.numero_documento = src.numero_documento
               AND tgt.tipo_documento = src.tipo_documento
               AND tgt.tipo_valor = src.tipo_valor
               AND tgt.moeda = src.moeda
            WHEN MATCHED THEN
                UPDATE SET
                    valor = {valor_sql},
                    data_valor = {data_valor_sql},
                    data_atualizacao = GETDATE(),
                    fonte_dados = {fonte_sql},
                    json_dados_originais = {json_sql},
                    atualizado_em = GETDATE()
            WHEN NOT MATCHED THEN
                INSERT (
                    processo_referencia,
                    numero_documento,
                    tipo_documento,
                    tipo_valor,
                    moeda,
                    valor,
                    taxa_cambio,
                    data_valor,
                    data_atualizacao,
                    fonte_dados,
                    json_dados_originais,
                    criado_em,
                    atualizado_em
                )
                VALUES (
                    src.processo_referencia,
                    src.numero_documento,
                    src.tipo_documento,
                    src.tipo_valor,
                    src.moeda,
                    {valor_sql},
                    NULL,
                    {data_valor_sql},
                    GETDATE(),
                    {fonte_sql},
                    {json_sql},
                    GETDATE(),
                    GETDATE()
                );
            """

            sql_adapter.execute_query(merge, database='mAIke_assistente', params=None, notificar_erro=False)

        logger.info(f"✅ VALOR_MERCADORIA populada/atualizada: {len(linhas)} linha(s) (fonte={fonte_dados})")
    except Exception as e:
        logger.warning(f"⚠️ Falha ao persistir VALOR_MERCADORIA (não crítico): {e}")


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
    
    Args:
        incoterm: Código do INCOTERM (FOB, CIF, CFR, etc.)
        vmle_usd: Valor Mercadoria Local Embarque em USD
        vmle_brl: Valor Mercadoria Local Embarque em BRL
        frete_usd: Frete em USD (opcional)
        frete_brl: Frete em BRL (opcional)
        seguro_usd: Seguro em USD (opcional)
        seguro_brl: Seguro em BRL (opcional)
    
    Returns:
        Dict com fob_usd, fob_brl, incoterm, aviso (opcional)
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


def buscar_processos_di_por_mes(
    mes: int,
    ano: int,
    categoria: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Busca processos com DI desembaraçados em um mês/ano específico.
    
    Args:
        mes: Mês (1-12)
        ano: Ano (ex: 2025)
        categoria: Categoria do processo (ex: 'DMD', 'VDM') ou None para todas
    
    Returns:
        Lista de processos com dados DI e valores FOB normalizados
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import (
            get_primary_database,
            log_legacy_fallback
        )
        
        sql_adapter = get_sql_adapter()
        database_para_usar = get_primary_database()
        
        # Construir filtro de categoria
        filtro_categoria = ""
        if categoria:
            categoria_upper = categoria.upper()
            filtro_categoria = f"AND p.numero_processo LIKE '{categoria_upper}.%'"
        
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
                FROM {database}.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                INNER JOIN Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
                    ON p.id_importacao = diH.idImportacao
                INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                    ON diH.diId = diRoot.dadosDiId
                INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                WHERE 1=1
                  {filtro_categoria}
                  -- ✅ Filtrar por dataHoraDesembaraco se existir, senão usar dataHoraSituacaoDi
                  AND (
                      (diDesp.dataHoraDesembaraco IS NOT NULL 
                       AND YEAR(diDesp.dataHoraDesembaraco) = {ano} 
                       AND MONTH(diDesp.dataHoraDesembaraco) = {mes})
                      OR
                      (diDesp.dataHoraDesembaraco IS NULL 
                       AND YEAR(ddg.dataHoraSituacaoDi) = {ano} 
                       AND MONTH(ddg.dataHoraSituacaoDi) = {mes})
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
                -- ✅ CORREÇÃO: Pegar apenas o frete da DI usando subquery correlacionada
                -- Segundo MAPEAMENTO_SQL_SERVER.md linha 441: Di_Root_Declaracao_Importacao.dadosDiId = Di_Frete.freteId
                -- ⚠️ IMPORTANTE: Não usar ORDER BY por valor (pode pegar o valor errado)
                -- Usar subquery no SELECT para garantir que pegamos o primeiro registro encontrado
                CAST(ISNULL((
                    SELECT TOP 1 valorTotalDolares
                    FROM Serpro.dbo.Di_Frete WITH (NOLOCK)
                    WHERE freteId = dpp.dadosDiId
                ), 0) AS FLOAT) AS frete_usd,
                CAST(ISNULL((
                    SELECT TOP 1 totalReais
                    FROM Serpro.dbo.Di_Frete WITH (NOLOCK)
                    WHERE freteId = dpp.dadosDiId
                ), 0) AS FLOAT) AS frete_brl,
                -- ✅ CORREÇÃO: Pegar apenas o seguro da DI usando subquery correlacionada
                -- Segundo MAPEAMENTO_SQL_SERVER.md linha 452: Di_Root_Declaracao_Importacao.dadosDiId = Di_Seguro.seguroId
                CAST(ISNULL((
                    SELECT TOP 1 valorTotalDolares
                    FROM Serpro.dbo.Di_Seguro WITH (NOLOCK)
                    WHERE seguroId = dpp.dadosDiId
                ), 0) AS FLOAT) AS seguro_usd,
                CAST(ISNULL((
                    SELECT TOP 1 valorTotalReais
                    FROM Serpro.dbo.Di_Seguro WITH (NOLOCK)
                    WHERE seguroId = dpp.dadosDiId
                ), 0) AS FLOAT) AS seguro_brl,
                dpp.situacaoDi,
                dpp.dadosDiId,
                dpp.numeroDi
            FROM DI_POR_PROCESSO dpp
            -- ✅ CORREÇÃO: Usar Di_Valor_Mercadoria_Descarga (VMLD) ao invés de Di_Valor_Mercadoria_Embarque (VMLE)
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD WITH (NOLOCK)
                ON dpp.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
            WHERE dpp.rn = 1
            ORDER BY dpp.numero_processo
        '''.format(
            filtro_categoria=filtro_categoria,
            ano=ano,
            mes=mes
        )
        
        logger.info(f"🔍 Buscando processos com DI desembaraçados em {mes}/{ano} (banco: {database_para_usar})...")
        result = sql_adapter.execute_query(query, database_para_usar, None, notificar_erro=False)
        
        if not result.get('success'):
            logger.error(f"❌ Erro ao buscar processos DI: {result.get('error')}")
            return []
        
        rows = result.get('data', [])
        logger.info(f"✅ Encontrados {len(rows)} processos com DI em {mes}/{ano}")
        
        processos = []
        for row in rows:
            # Converter valores para float
            vmld_usd = float(str(row.get('vmld_usd') or 0).replace(',', '.')) if row.get('vmld_usd') else 0.0
            vmld_brl = float(str(row.get('vmld_brl') or 0).replace(',', '.')) if row.get('vmld_brl') else 0.0
            frete_usd = float(str(row.get('frete_usd') or 0).replace(',', '.')) if row.get('frete_usd') else 0.0
            frete_brl = float(str(row.get('frete_brl') or 0).replace(',', '.')) if row.get('frete_brl') else 0.0
            seguro_usd = float(str(row.get('seguro_usd') or 0).replace(',', '.')) if row.get('seguro_usd') else 0.0
            seguro_brl = float(str(row.get('seguro_brl') or 0).replace(',', '.')) if row.get('seguro_brl') else 0.0
            
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
                'tipo_documento': 'DI',
                'incoterm': 'FOB',  # Calculado: FOB = VMLD - Frete - Seguro
                'aviso': None
            })
        
        logger.info(f"✅ Processados {len(processos)} processos com DI de {mes}/{ano}")
        return processos
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar processos DI: {e}", exc_info=True)
        return []


def buscar_processos_di_por_ano(
    ano: int,
    categoria: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Busca processos com DI desembaraçados em um ANO inteiro.

    Critério de data:
    - Usa dataHoraDesembaraco quando existir; senão usa dataHoraSituacaoDi.
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import get_primary_database

        sql_adapter = get_sql_adapter()
        database_para_usar = get_primary_database()

        filtro_categoria = ""
        if categoria:
            categoria_upper = categoria.upper()
            filtro_categoria = f"AND p.numero_processo LIKE '{categoria_upper}.%'"

        query = '''
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
                FROM {database}.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                INNER JOIN Serpro.dbo.Hi_Historico_Di diH WITH (NOLOCK)
                    ON p.id_importacao = diH.idImportacao
                INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot WITH (NOLOCK)
                    ON diH.diId = diRoot.dadosDiId
                INNER JOIN Serpro.dbo.Di_Dados_Gerais ddg WITH (NOLOCK)
                    ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp WITH (NOLOCK)
                    ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                WHERE 1=1
                  {filtro_categoria}
                  AND (
                      (diDesp.dataHoraDesembaraco IS NOT NULL AND YEAR(diDesp.dataHoraDesembaraco) = {ano})
                      OR
                      (diDesp.dataHoraDesembaraco IS NULL AND YEAR(ddg.dataHoraSituacaoDi) = {ano})
                  )
            )
            SELECT
                dpp.numero_processo,
                dpp.numero_di,
                dpp.dataHoraDesembaraco,
                CAST(ISNULL(DVMD.totalDolares, 0) AS FLOAT) AS vmld_usd,
                CAST(ISNULL(DVMD.totalReais, 0) AS FLOAT) AS vmld_brl,
                CAST(ISNULL((
                    SELECT TOP 1 valorTotalDolares
                    FROM Serpro.dbo.Di_Frete WITH (NOLOCK)
                    WHERE freteId = dpp.dadosDiId
                ), 0) AS FLOAT) AS frete_usd,
                CAST(ISNULL((
                    SELECT TOP 1 totalReais
                    FROM Serpro.dbo.Di_Frete WITH (NOLOCK)
                    WHERE freteId = dpp.dadosDiId
                ), 0) AS FLOAT) AS frete_brl,
                CAST(ISNULL((
                    SELECT TOP 1 valorTotalDolares
                    FROM Serpro.dbo.Di_Seguro WITH (NOLOCK)
                    WHERE seguroId = dpp.dadosDiId
                ), 0) AS FLOAT) AS seguro_usd,
                CAST(ISNULL((
                    SELECT TOP 1 valorTotalReais
                    FROM Serpro.dbo.Di_Seguro WITH (NOLOCK)
                    WHERE seguroId = dpp.dadosDiId
                ), 0) AS FLOAT) AS seguro_brl,
                dpp.situacaoDi,
                dpp.dadosDiId,
                dpp.numeroDi
            FROM DI_POR_PROCESSO dpp
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD WITH (NOLOCK)
                ON dpp.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
            WHERE dpp.rn = 1
            ORDER BY dpp.numero_processo
        '''.format(
            database=database_para_usar,
            filtro_categoria=filtro_categoria,
            ano=ano,
        )

        logger.info(f"🔍 Buscando processos com DI desembaraçados em {ano} (ano inteiro, banco: {database_para_usar})...")
        result = sql_adapter.execute_query(query, database_para_usar, None, notificar_erro=False)

        if not result.get('success'):
            logger.error(f"❌ Erro ao buscar processos DI (ano): {result.get('error')}")
            return []

        rows = result.get('data', [])
        logger.info(f"✅ Encontrados {len(rows)} processos com DI em {ano}")

        processos: List[Dict[str, Any]] = []
        for row in rows:
            vmld_usd = float(str(row.get('vmld_usd') or 0).replace(',', '.')) if row.get('vmld_usd') else 0.0
            vmld_brl = float(str(row.get('vmld_brl') or 0).replace(',', '.')) if row.get('vmld_brl') else 0.0
            frete_usd = float(str(row.get('frete_usd') or 0).replace(',', '.')) if row.get('frete_usd') else 0.0
            frete_brl = float(str(row.get('frete_brl') or 0).replace(',', '.')) if row.get('frete_brl') else 0.0
            seguro_usd = float(str(row.get('seguro_usd') or 0).replace(',', '.')) if row.get('seguro_usd') else 0.0
            seguro_brl = float(str(row.get('seguro_brl') or 0).replace(',', '.')) if row.get('seguro_brl') else 0.0

            fob_usd = vmld_usd - frete_usd - seguro_usd
            fob_brl = vmld_brl - frete_brl - seguro_brl
            if fob_usd < 0:
                fob_usd = 0.0
            if fob_brl < 0:
                fob_brl = 0.0

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
                'tipo_documento': 'DI',
                'incoterm': 'FOB',
                'aviso': None,
            })

        logger.info(f"✅ Processados {len(processos)} processos com DI de {ano} (ano inteiro)")
        return processos
    except Exception as e:
        logger.error(f"❌ Erro ao buscar processos DI por ano: {e}", exc_info=True)
        return []


def buscar_processos_duimp_por_ano(
    ano: int,
    categoria: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Busca processos com DUIMP desembaraçados em um ANO inteiro.
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import get_primary_database

        sql_adapter = get_sql_adapter()
        database_para_usar = get_primary_database()

        filtro_categoria = ""
        if categoria:
            categoria_upper = categoria.upper()
            filtro_categoria = f"AND p.numero_processo LIKE '{categoria_upper}.%'"

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
                FROM {database}.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                INNER JOIN duimp.dbo.duimp d WITH (NOLOCK)
                    ON p.numero_duimp = d.numero
                INNER JOIN duimp.dbo.duimp_tributos_mercadoria tm WITH (NOLOCK)
                    ON d.duimp_id = tm.duimp_id
                INNER JOIN duimp.dbo.duimp_diagnostico dd WITH (NOLOCK)
                    ON d.duimp_id = dd.duimp_id
                WHERE 1=1
                  {filtro_categoria}
                  AND (dd.situacao_duimp LIKE '%DESEMBARACADA%' OR dd.situacao_duimp LIKE '%ENTREGUE%')
                  AND YEAR(dd.data_geracao) = {ano}
            )
            SELECT
                dpp.numero_processo,
                dpp.numero_duimp,
                dpp.data_desembaraco,
                dpp.fob_usd,
                dpp.fob_brl,
                dpp.situacao_duimp,
                (SELECT TOP 1 CAST(ISNULL(ceRoot2.valorFreteTotal, 0) AS FLOAT)
                 FROM Serpro.dbo.Hi_Historico_Ce ceH2 WITH (NOLOCK)
                 INNER JOIN Serpro.dbo.Ce_Root_Conhecimento_Embarque ceRoot2 WITH (NOLOCK)
                     ON ceH2.ceId = ceRoot2.rootConsultaEmbarqueId
                 WHERE ceH2.idImportacao = dpp.id_importacao
                 ORDER BY ceRoot2.updatedAt DESC) AS frete_brl
            FROM DUIMP_POR_PROCESSO dpp
            WHERE dpp.rn = 1
            ORDER BY dpp.numero_processo
        '''.format(
            database=database_para_usar,
            filtro_categoria=filtro_categoria,
            ano=ano,
        )

        logger.info(f"🔍 Buscando processos com DUIMP desembaraçados em {ano} (ano inteiro, banco: {database_para_usar})...")
        result = sql_adapter.execute_query(query, 'duimp', None, notificar_erro=False)

        if not result.get('success'):
            logger.error(f"❌ Erro ao buscar processos DUIMP (ano): {result.get('error')}")
            return []

        rows = result.get('data', [])
        logger.info(f"✅ Encontrados {len(rows)} processos com DUIMP em {ano}")

        processos: List[Dict[str, Any]] = []
        for row in rows:
            fob_usd = float(str(row.get('fob_usd') or 0).replace(',', '.')) if row.get('fob_usd') else 0.0
            fob_brl = float(str(row.get('fob_brl') or 0).replace(',', '.')) if row.get('fob_brl') else 0.0
            frete_brl = float(str(row.get('frete_brl') or 0).replace(',', '.')) if row.get('frete_brl') else 0.0
            frete_pct_fob_brl = (frete_brl / fob_brl * 100) if fob_brl > 0 else 0.0

            processos.append({
                'numero_processo': row.get('numero_processo'),
                'numero_duimp': row.get('numero_duimp'),
                'data_desembaraco': row.get('data_desembaraco'),
                'fob_usd': fob_usd,
                'fob_brl': fob_brl,
                'frete_brl': frete_brl,
                'frete_pct_fob_brl': frete_pct_fob_brl,
                'tipo_documento': 'DUIMP',
                'incoterm': 'FOB',
                'aviso': None,
            })

        logger.info(f"✅ Processados {len(processos)} processos com DUIMP de {ano} (ano inteiro)")
        return processos
    except Exception as e:
        logger.error(f"❌ Erro ao buscar processos DUIMP por ano: {e}", exc_info=True)
        return []


def buscar_processos_duimp_por_mes(
    mes: int,
    ano: int,
    categoria: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Busca processos com DUIMP desembaraçados em um mês/ano específico.
    
    Args:
        mes: Mês (1-12)
        ano: Ano (ex: 2025)
        categoria: Categoria do processo (ex: 'DMD', 'VDM') ou None para todas
    
    Returns:
        Lista de processos com dados DUIMP e valores FOB
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        from services.db_policy_service import get_primary_database
        
        sql_adapter = get_sql_adapter()
        database_para_usar = get_primary_database()
        
        # Construir filtro de categoria
        filtro_categoria = ""
        if categoria:
            categoria_upper = categoria.upper()
            filtro_categoria = f"AND p.numero_processo LIKE '{categoria_upper}.%'"
        
        query = '''
            -- ⚠️ Pode haver múltiplos registros em duimp_diagnostico, então usar ROW_NUMBER() para pegar apenas um por processo
            -- ✅ NOVO: Buscar frete do CE relacionado à DUIMP (via id_importacao)
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
                FROM {database}.dbo.PROCESSO_IMPORTACAO p WITH (NOLOCK)
                INNER JOIN duimp.dbo.duimp d WITH (NOLOCK)
                    ON p.numero_duimp = d.numero
                INNER JOIN duimp.dbo.duimp_tributos_mercadoria tm WITH (NOLOCK)
                    ON d.duimp_id = tm.duimp_id
                INNER JOIN duimp.dbo.duimp_diagnostico dd WITH (NOLOCK)
                    ON d.duimp_id = dd.duimp_id
                WHERE 1=1
                  {filtro_categoria}
                  -- ✅ Buscar DUIMPs desembaraçadas (pode ter múltiplas situações)
                  AND (dd.situacao_duimp LIKE '%DESEMBARACADA%' OR dd.situacao_duimp LIKE '%ENTREGUE%')
                  AND YEAR(dd.data_geracao) = {ano}
                  AND MONTH(dd.data_geracao) = {mes}
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
        '''.format(
            database=database_para_usar,
            filtro_categoria=filtro_categoria,
            ano=ano,
            mes=mes
        )
        
        logger.info(f"🔍 Buscando processos com DUIMP desembaraçados em {mes}/{ano} (banco: {database_para_usar})...")
        result = sql_adapter.execute_query(query, 'duimp', None, notificar_erro=False)
        
        if not result.get('success'):
            logger.error(f"❌ Erro ao buscar processos DUIMP: {result.get('error')}")
            return []
        
        rows = result.get('data', [])
        logger.info(f"✅ Encontrados {len(rows)} processos com DUIMP em {mes}/{ano}")
        
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
                'tipo_documento': 'DUIMP',
                'incoterm': 'FOB',  # DUIMP já retorna FOB direto
                'aviso': None
            })
        
        logger.info(f"✅ Processados {len(processos)} processos com DUIMP de {mes}/{ano}")
        return processos
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar processos DUIMP: {e}", exc_info=True)
        return []


def gerar_relatorio_importacoes_fob(
    mes: Optional[int],
    ano: int,
    categoria: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gera relatório de importações normalizado por FOB.
    
    Busca processos desembaraçados no mês/ano especificado e calcula
    valores FOB normalizados (considerando INCOTERMs).
    
    Args:
        mes: Mês (1-12)
        ano: Ano (ex: 2025)
        categoria: Categoria do processo (ex: 'DMD', 'VDM') ou None para todas
    
    Returns:
        Dict com estrutura determinística:
        {
            'sucesso': bool,
            'mes': int,
            'ano': int,
            'categoria': str ou None,
            'total_processos': int,
            'total_fob_usd': float,
            'total_fob_brl': float,
            'por_categoria': [
                {
                    'categoria': str,
                    'total_processos': int,
                    'total_fob_usd': float,
                    'total_fob_brl': float,
                    'processos': [...]
                }
            ],
            'erro': str (se houver)
        }
    """
    try:
        # Buscar processos com DI / DUIMP
        if mes is None:
            processos_di = buscar_processos_di_por_ano(ano, categoria)
            processos_duimp = buscar_processos_duimp_por_ano(ano, categoria)
        else:
            processos_di = buscar_processos_di_por_mes(mes, ano, categoria)
            processos_duimp = buscar_processos_duimp_por_mes(mes, ano, categoria)
        
        # Combinar todos os processos
        todos_processos = processos_di + processos_duimp

        # ✅ NOVO (19/01/2026): Persistir valores no banco novo (mAIke_assistente)
        # Isso materializa os valores calculados (FOB/VMLD/FRETE/SEGURO) em dbo.VALOR_MERCADORIA.
        _persistir_valores_mercadoria_sql_server(todos_processos, fonte_dados='RELATORIO_FOB')
        
        if not todos_processos:
            periodo_label = f"{ano}" if mes is None else f"{mes}/{ano}"
            return {
                'sucesso': True,
                'mes': mes,
                'ano': ano,
                'categoria': categoria,
                'total_processos': 0,
                'total_fob_usd': 0.0,
                'total_fob_brl': 0.0,
                'por_categoria': [],
                'mensagem': f'Nenhum processo desembaraçado encontrado em {periodo_label}'
            }
        
        # Agrupar por categoria
        por_categoria: Dict[str, Dict[str, Any]] = {}
        total_fob_usd = 0.0
        total_fob_brl = 0.0
        
        for proc in todos_processos:
            # Extrair categoria do número do processo
            numero_proc = proc.get('numero_processo', '')
            cat = numero_proc[:3].upper() if len(numero_proc) >= 3 else 'OUTROS'
            
            if cat not in por_categoria:
                por_categoria[cat] = {
                    'categoria': cat,
                    'total_processos': 0,
                    'total_fob_usd': 0.0,
                    'total_fob_brl': 0.0,
                    'processos': []
                }
            
            por_categoria[cat]['total_processos'] += 1
            por_categoria[cat]['total_fob_usd'] += proc.get('fob_usd', 0.0)
            por_categoria[cat]['total_fob_brl'] += proc.get('fob_brl', 0.0)
            por_categoria[cat]['processos'].append(proc)
            
            total_fob_usd += proc.get('fob_usd', 0.0)
            total_fob_brl += proc.get('fob_brl', 0.0)
        
        return {
            'sucesso': True,
            'mes': mes,
            'ano': ano,
            'categoria': categoria,
            'total_processos': len(todos_processos),
            'total_fob_usd': total_fob_usd,
            'total_fob_brl': total_fob_brl,
            'por_categoria': sorted(
                por_categoria.values(),
                key=lambda g: g['total_fob_brl'],
                reverse=True
            )
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório FOB: {e}", exc_info=True)
        return {
            'sucesso': False,
            'mes': mes,
            'ano': ano,
            'categoria': categoria,
            'erro': str(e),
            'mensagem': f'Erro ao gerar relatório: {str(e)}'
        }


def formatar_relatorio_fob(
    dados: Dict[str, Any]
) -> str:
    """
    Formata relatório FOB em texto legível.
    
    Args:
        dados: Resultado de gerar_relatorio_importacoes_fob()
    
    Returns:
        String formatada com o relatório
    """
    if not dados.get('sucesso'):
        return f"❌ Erro ao gerar relatório: {dados.get('mensagem', 'erro desconhecido')}"
    
    mes = dados.get('mes')
    ano = dados.get('ano')
    categoria = dados.get('categoria')
    total_processos = dados.get('total_processos', 0)
    total_fob_usd = dados.get('total_fob_usd', 0.0)
    total_fob_brl = dados.get('total_fob_brl', 0.0)
    por_categoria = dados.get('por_categoria', [])
    
    if total_processos == 0:
        if mes is None:
            return f"✅ Nenhum processo desembaraçado encontrado em {ano}."
        return f"✅ Nenhum processo desembaraçado encontrado em {mes}/{ano}."
    
    linhas = []
    if mes is None:
        linhas.append(f"📊 **Relatório de Importações Normalizado por FOB - Ano {ano}**")
    else:
        linhas.append(f"📊 **Relatório de Importações Normalizado por FOB - {mes}/{ano}**")
    if categoria:
        linhas.append(f"Categoria: {categoria}")
    linhas.append("")
    
    # Resumo geral
    linhas.append(f"**Resumo Geral:**")
    linhas.append(f"- Total de Processos: {total_processos}")
    linhas.append(f"- Total FOB (USD): ${total_fob_usd:,.2f}")
    linhas.append(f"- Total FOB (BRL): R$ {total_fob_brl:,.2f}")
    linhas.append("")
    
    # Por categoria
    if len(por_categoria) > 1:
        linhas.append("**Por Categoria:**")
        for grupo in por_categoria:
            cat = grupo.get('categoria', '?')
            qtd = grupo.get('total_processos', 0)
            fob_usd = grupo.get('total_fob_usd', 0.0)
            fob_brl = grupo.get('total_fob_brl', 0.0)
            linhas.append(f"- **{cat}**: {qtd} processo(s) - FOB: ${fob_usd:,.2f} (USD) / R$ {fob_brl:,.2f} (BRL)")
        linhas.append("")
    
    # Detalhamento por processo (apenas alguns exemplos se houver muitas categorias)
    if len(por_categoria) == 1:
        # Se só uma categoria, mostrar todos os processos
        processos = por_categoria[0].get('processos', [])
        linhas.append("**Detalhamento por Processo:**")
        for proc in processos:
            num_proc = proc.get('numero_processo', '?')
            doc = proc.get('numero_di') or proc.get('numero_duimp') or 'N/A'
            fob_usd = proc.get('fob_usd', 0.0)
            fob_brl = proc.get('fob_brl', 0.0)
            frete_brl = proc.get('frete_brl', 0.0)
            frete_pct = proc.get('frete_pct_fob_brl', 0.0)
            
            linha = f"- **{num_proc}** ({doc}): FOB R$ {fob_brl:,.2f}"
            if frete_brl > 0:
                linha += f" | Frete: R$ {frete_brl:,.2f} ({frete_pct:.1f}% do FOB)"
            linhas.append(linha)
    else:
        # Se múltiplas categorias, mostrar apenas resumo
        linhas.append("💡 Para ver detalhamento por processo, consulte uma categoria específica.")
    
    return "\n".join(linhas)

