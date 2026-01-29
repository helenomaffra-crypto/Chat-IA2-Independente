"""
Schema de busca consolidada de processos no SQL Server.
Busca dados completos de CE, DI, DUIMP e CCT para processos antigos/históricos.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


def buscar_processo_consolidado_sql_server(processo_referencia: str, database: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Busca processo no SQL Server com dados CONSOLIDADOS.
    
    Args:
        processo_referencia: Ex: "ALH.0168/25"
        database: Nome do banco de dados ('mAIke_assistente' ou 'Make'). Se None, usa o padrão do adapter.
    
    Retorna estrutura completa similar ao Kanban:
    {
        'processo_referencia': 'ALH.0168/25',
        'id_processo_importacao': 111,
        'id_importacao': 15450,
        
        # CE (Conhecimento de Embarque)
        'ce': {
            'numero': '132505343511317',
            'situacao': 'Desembarcado',
            'porto_origem': '...',
            'porto_destino': '...',
            'porto_atracacao_atual': '...',
            'data_situacao': '2025-11-15',
            'valor_frete_total': 4518.31,
            'pendencia_frete': True,
            'pendencia_afrmm': False,
            'data_armazenamento': '...',
            'data_destino_final': '...',
        },
        
        # DI (Declaração de Importação)
        'di': {
            'numero': '2521440840',
            'situacao': 'DI Desembaraçada',
            'canal': 'VERDE',
            'data_desembaraco': '2025-11-15',
            'data_registro': '2025-11-10',
            'situacao_entrega': '...',
            'modalidade': 'NORMAL',
            'valor_mercadoria_descarga': 360325.37,
            'valor_mercadoria_embarque': 338017.5,
        },
        
        # DUIMP (Declaração Única de Importação)
        'duimp': {
            'numero': '25BR00001928777',
            'versao': '1',
            'situacao': 'Registrada',
            'canal': 'VERDE',
            'data_registro': '2025-11-10',
            'ultima_situacao': '...',
            'ultimo_evento': '...',
        },
        
        # CCT (Conhecimento de Carga Aérea) - se houver
        'cct': {
            'numero': '...',
            'situacao': '...',
            'data_situacao': '...',
            'recinto_aduaneiro': '...',
            'bloqueios_ativos': [...],
        }
    }
    
    Args:
        processo_referencia: Ex: "ALH.0168/25"
    
    Returns:
        Dict com dados consolidados ou None se não encontrar
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        
        from services.db_policy_service import (
            get_primary_database,
            get_legacy_database,
            log_legacy_fallback,
            should_use_legacy_database
        )
        
        sql_adapter = get_sql_adapter()
        processo_ref_upper = processo_referencia.upper().strip()
        
        # ✅ POLÍTICA CENTRAL: Usar database especificado ou primário (nunca defaultar para Make)
        if database:
            database_para_usar = database
        elif sql_adapter.database:
            database_para_usar = sql_adapter.database
        else:
            # Sem database especificado: usar primário
            database_para_usar = get_primary_database()
        
        # Se database especificado é Make, logar fallback
        if database_para_usar == get_legacy_database():
            log_legacy_fallback(
                processo_referencia=processo_ref_upper,
                tool_name='buscar_processo_consolidado_sql_server',
                caller_function='buscar_processo_consolidado_sql_server',
                reason=f"Database '{database}' explicitamente especificado como Make"
            )
        
        logger.info(f"🔍 Buscando processo consolidado no SQL Server ({database_para_usar}): {processo_ref_upper}")
        
        # 1. Buscar processo principal
        processo = _buscar_processo_principal(sql_adapter, processo_ref_upper, database_para_usar)
        if not processo:
            logger.warning(f"⚠️ Processo {processo_ref_upper} não encontrado no SQL Server")
            return None
        
        logger.info(f"✅ Processo {processo_ref_upper} encontrado. ID: {processo.get('id_processo_importacao')}")
        
        # 2. Buscar CE (se houver numero_ce)
        if processo.get('numero_ce'):
            logger.debug(f"📦 Buscando dados do CE {processo['numero_ce']}...")
            ce_data = _buscar_ce_completo(sql_adapter, processo['numero_ce'], processo.get('id_importacao'))
            if ce_data:
                processo['ce'] = ce_data
        
        # 3. Buscar DI (se houver numero_di OU buscar via id_processo/CE)
        # ⚠️ IMPORTANTE: Mesmo que numero_di esteja preenchido, pode estar em formato diferente
        # (ex: "25/0340890-6" na tabela vs "2503408906" na Di_Dados_Gerais)
        # Por isso, sempre tentamos buscar via id_importacao também como fallback
        di_data = None
        if processo.get('numero_di'):
            logger.debug(f"📄 Buscando dados da DI {processo['numero_di']}...")
            di_data = _buscar_di_completo(sql_adapter, processo['numero_di'], processo.get('id_importacao'))
            if di_data:
                logger.info(f"✅ DI {di_data.get('numero')} encontrada via numero_di direto")
                processo['di'] = di_data
        
        # Se não encontrou via numero_di (pode estar em formato diferente), tentar via id_importacao
        if not di_data:
            # ✅ FALLBACK: Tentar buscar DI relacionada via id_processo_importacao ou CE
            # Isso é necessário porque:
            # 1. numero_di pode estar em formato diferente (ex: "25/0340890-6" vs "2503408906")
            # 2. numero_di pode estar NULL mas a DI existe relacionada via id_importacao
            
            # Tentar buscar via id_processo_importacao primeiro (usa id_importacao internamente)
            if processo.get('id_processo_importacao'):
                logger.debug(f"📄 Buscando DI relacionada ao ID Processo {processo.get('id_processo_importacao')} (fallback)...")
                di_data = _buscar_di_por_id_processo(
                    sql_adapter,
                    processo.get('id_processo_importacao'),
                    processo.get('id_importacao'),
                    process_db=database_para_usar,
                )
                if di_data:
                    logger.info(f"✅ DI {di_data.get('numero')} encontrada relacionada ao ID Processo {processo.get('id_processo_importacao')} (via id_importacao)")
            
            # Se não encontrou via ID, tentar via CE
            if not di_data and processo.get('numero_ce'):
                logger.debug(f"📄 Buscando DI relacionada ao CE {processo['numero_ce']} (fallback)...")
                di_data = _buscar_di_por_ce(sql_adapter, processo['numero_ce'])
                if di_data:
                    logger.info(f"✅ DI {di_data.get('numero')} encontrada relacionada ao CE {processo['numero_ce']}")
            
            if di_data:
                processo['di'] = di_data
                processo['numero_di'] = di_data.get('numero')  # Atualizar numero_di no processo
        
        # 4. Buscar DUIMP (se houver numero_duimp)
        if processo.get('numero_duimp'):
            logger.debug(f"📋 Buscando dados da DUIMP {processo['numero_duimp']}...")
            duimp_data = _buscar_duimp_completo(sql_adapter, processo['numero_duimp'], processo_ref_upper, processo.get('id_importacao'))
            if duimp_data:
                processo['duimp'] = duimp_data
        
        # 5. Buscar CCT (se processo aéreo/rodoviário)
        if processo.get('id_importacao'):
            logger.debug(f"✈️ Buscando dados do CCT (id_importacao: {processo['id_importacao']})...")
            cct_data = _buscar_cct_completo(sql_adapter, processo['id_importacao'])
            if cct_data:
                processo['cct'] = cct_data
        
        logger.info(f"✅ Processo {processo_ref_upper} consolidado com sucesso")
        return processo
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar processo consolidado no SQL Server: {e}", exc_info=True)
        return None


def _buscar_processo_principal(sql_adapter, processo_referencia: str, database: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Busca dados principais do processo"""
    from services.db_policy_service import get_primary_database
    
    # ✅ POLÍTICA CENTRAL: Se database não especificado, usar primário
    if not database:
        database = get_primary_database()
    
    # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?, usar formatação direta (escapada)
    # ⚠️ IMPORTANTE: Escapar aspas simples para prevenir SQL injection
    processo_ref_escaped = processo_referencia.replace("'", "''")
    query = f'''
        SELECT 
            numero_processo,
            id_processo_importacao,
            id_importacao,
            numero_ce,
            numero_di,
            numero_duimp,
            data_embarque,
            data_chegada_prevista,
            data_desembaraco,
            status_processo
        FROM {database}.dbo.PROCESSO_IMPORTACAO
        WHERE numero_processo = '{processo_ref_escaped}'
    '''
    
    result = sql_adapter.execute_query(query, database, None, notificar_erro=False)  # ✅ Usar database especificado
    
    if result.get('success') and result.get('data'):
        rows = result['data']
        if rows and len(rows) > 0:
            row = rows[0]
            return {
                'processo_referencia': row.get('numero_processo', processo_referencia),
                'id_processo_importacao': row.get('id_processo_importacao'),
                'id_importacao': row.get('id_importacao'),
                'numero_ce': row.get('numero_ce'),
                'numero_di': row.get('numero_di'),
                'numero_duimp': row.get('numero_duimp'),
                'data_embarque': row.get('data_embarque'),
                'data_chegada_prevista': row.get('data_chegada_prevista'),
                'data_desembaraco': row.get('data_desembaraco'),
                'status_processo': row.get('status_processo'),
            }
    
    return None


def _buscar_ce_completo(sql_adapter, numero_ce: str, id_importacao: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Busca dados completos do CE"""
    try:
        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?, usar formatação direta (escapada)
        numero_ce_escaped = numero_ce.replace("'", "''")
        # Query 1: Buscar CE principal (mais recente)
        query_ce = f'''
            SELECT TOP 1
                ceRoot.rootConsultaEmbarqueId,
                ceRoot.numero,
                ceRoot.situacaoCarga,
                ceRoot.dataSituacaoCarga,
                ceRoot.portoOrigem,
                ceRoot.portoDestino,
                ceRoot.portoAtracacaoAtual,
                ceRoot.valorFreteTotal,
                ceRoot.afrmmTUMPago,
                ceRoot.pendenciaAFRMM,
                ceRoot.indicadorPendenciaFrete,
                ceRoot.dataArmazenamentoCarga,
                ceRoot.dataDestinoFinal,
                ceRoot.updatedAt
            FROM Serpro.dbo.Ce_Root_Conhecimento_Embarque ceRoot
            WHERE ceRoot.numero = '{numero_ce_escaped}'
            ORDER BY ceRoot.updatedAt DESC
        '''
        
        result = sql_adapter.execute_query(query_ce, 'Serpro', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        
        if result.get('success') and result.get('data'):
            rows = result['data']
            if rows and len(rows) > 0:
                row = rows[0]
                
                # Buscar pendências de frete (se houver)
                pendencia_frete = bool(row.get('indicadorPendenciaFrete', False))
                
                # Se não encontrou pendência no root, buscar na tabela específica
                root_id = row.get('rootConsultaEmbarqueId')
                if not pendencia_frete and root_id:
                    # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
                    root_id_escaped = str(root_id).replace("'", "''")
                    query_pendencia = f'''
                        SELECT pendenciaFrete
                        FROM Serpro.dbo.Ce_Pendencia_Frete
                        WHERE rootConsultaEmbarqueId = {root_id_escaped}
                    '''
                    result_pendencia = sql_adapter.execute_query(
                        query_pendencia, 
                        'Serpro', 
                        None,  # ✅ Sem parâmetros para Node.js
                        notificar_erro=False  # ✅ Não notificar erros (enriquecimento não crítico)
                    )
                    if result_pendencia.get('success') and result_pendencia.get('data'):
                        pend_rows = result_pendencia['data']
                        if pend_rows and len(pend_rows) > 0:
                            pendencia_frete = bool(pend_rows[0].get('pendenciaFrete', False))
                
                return {
                    'numero': row.get('numero', numero_ce),
                    'situacao': row.get('situacaoCarga'),
                    'porto_origem': row.get('portoOrigem'),
                    'porto_destino': row.get('portoDestino'),
                    'porto_atracacao_atual': row.get('portoAtracacaoAtual'),
                    'data_situacao': row.get('dataSituacaoCarga'),
                    'valor_frete_total': row.get('valorFreteTotal'),
                    'pendencia_frete': pendencia_frete,
                    'pendencia_afrmm': bool(row.get('pendenciaAFRMM', False)),
                    'afrmm_tum_pago': bool(row.get('afrmmTUMPago', False)),
                    'data_armazenamento': row.get('dataArmazenamentoCarga'),
                    'data_destino_final': row.get('dataDestinoFinal'),
                    'atualizado_em': row.get('updatedAt'),
                }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar CE completo: {e}")
        return None


def _buscar_ce_por_id_importacao(sql_adapter, id_importacao: int) -> Optional[Dict[str, Any]]:
    """
    Busca CE relacionado a uma importação através do id_importacao.
    
    Similar à busca de DI: Hi_Historico_Ce.idImportacao → comex.dbo.Importacoes.id
    
    Args:
        sql_adapter: Adaptador SQL Server
        id_importacao: ID da importação
    
    Returns:
        Dict com dados do CE ou None se não encontrado
    """
    try:
        id_import_escaped = str(id_importacao).replace("'", "''")
        query_ce = f'''
            SELECT TOP 1
                ceRoot.numero,
                ceRoot.situacaoCarga,
                ceRoot.portoOrigem,
                ceRoot.portoDestino,
                ceRoot.valorFreteTotal,
                ceRoot.dataArmazenamentoCarga,
                ceRoot.dataDestinoFinal,
                ceRoot.updatedAt
            FROM Serpro.dbo.Hi_Historico_Ce ceH
            INNER JOIN Serpro.dbo.Ce_Root_Conhecimento_Embarque ceRoot ON ceH.ceId = ceRoot.rootConsultaEmbarqueId
            WHERE ceH.idImportacao = {id_import_escaped}
            ORDER BY ceRoot.updatedAt DESC
        '''
        
        result = sql_adapter.execute_query(query_ce, 'Serpro', None, notificar_erro=False)
        if result.get('success') and result.get('data'):
            rows = result['data']
            if rows and len(rows) > 0:
                row = rows[0]
                return {
                    'numero': row.get('numero'),
                    'situacao': row.get('situacaoCarga'),
                    'porto_origem': row.get('portoOrigem'),
                    'porto_destino': row.get('portoDestino'),
                    'valor_frete_total': row.get('valorFreteTotal'),
                    'data_armazenamento': row.get('dataArmazenamentoCarga'),
                    'data_destino_final': row.get('dataDestinoFinal'),
                    'atualizado_em': row.get('updatedAt'),
                }
        
        return None
    except Exception as e:
        logger.debug(f'⚠️ Erro ao buscar CE por id_importacao {id_importacao}: {e}')
        return None


def _buscar_di_completo(sql_adapter, numero_di: str, id_importacao: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Busca dados completos da DI
    
    Segue o padrão do protótipo: busca pelo número da DI diretamente nas tabelas Serpro.
    
    ⚠️ IMPORTANTE: Normaliza o numero_di removendo '/' e '-' porque:
    - Na tabela PROCESSO_IMPORTACAO pode estar como "25/0340890-6"
    - Na tabela Di_Dados_Gerais está como "2503408906"
    
    ✅ NOVO: Se id_importacao for fornecido, também busca o CE relacionado.
    """
    try:
        # Normalizar numero_di: remover / e - para buscar na tabela Di_Dados_Gerais
        # Exemplo: "25/0340890-6" -> "2503408906"
        numero_di_normalizado = numero_di.replace('/', '').replace('-', '') if numero_di else None
        
        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?, usar formatação direta (escapada)
        numero_di_escaped = numero_di.replace("'", "''") if numero_di else ''
        numero_di_normalizado_escaped = numero_di_normalizado.replace("'", "''") if numero_di_normalizado else ''
        
        # ✅ CORREÇÃO: Buscar TODOS os campos incluindo valores de mercadoria, impostos e importador
        # ✅ NOVO: Incluir dadosDiId para buscar pagamentos depois
        query_di = f'''
            SELECT TOP 1
                ddg.numeroDi,
                ddg.situacaoDi,
                ddg.dataHoraSituacaoDi,
                ddg.situacaoEntregaCarga,
                diDesp.dataHoraDesembaraco,
                diDesp.canalSelecaoParametrizada,
                diDesp.modalidadeDespacho,
                diDesp.dataHoraAutorizacaoEntrega,
                diDesp.dataHoraRegistro,
                DICM.tipoRecolhimento AS tipoRecolhimentoIcms,
                DA.nomeAdquirente,
                DI.nomeImportador,
                DVMD.totalDolares AS dollar_VLMLD,
                DVMD.totalReais AS real_VLMD,
                DVME.totalDolares AS dollar_VLME,
                DVME.totalReais AS real_VLME,
                DICM.dataPagamento,
                diRoot.updatedAt AS updatedi,
                diRoot.dadosDiId
            FROM Serpro.dbo.Di_Dados_Gerais ddg
            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON ddg.dadosGeraisId = diRoot.dadosGeraisId
            LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
            LEFT JOIN Serpro.dbo.Di_Icms DICM ON diRoot.dadosDiId = DICM.rootDiId
            LEFT JOIN Serpro.dbo.Di_Adquirente DA ON diRoot.dadosDiId = DA.adquirenteId
            LEFT JOIN Serpro.dbo.Di_Importador DI ON diRoot.importadorId = DI.importadorId
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
            WHERE ddg.numeroDi = '{numero_di_escaped}' OR ddg.numeroDi = '{numero_di_normalizado_escaped}'
            ORDER BY ddg.dataHoraSituacaoDi DESC
        '''
        
        result = sql_adapter.execute_query(query_di, 'Serpro', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        
        if result.get('success') and result.get('data'):
            rows = result['data']
            if rows and len(rows) > 0:
                row = rows[0]
                dados_di_id = row.get('dadosDiId')  # ✅ NOVO: Precisamos do dadosDiId para buscar pagamentos
                
                logger.info(f"🔍 [DI] Buscando pagamentos para DI {numero_di}. dadosDiId: {dados_di_id}")
                
                # ✅ NOVO: Buscar pagamentos/impostos da DI (similar à DUIMP)
                pagamentos = []
                if dados_di_id:
                    try:
                        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
                        dados_di_id_escaped = str(dados_di_id).replace("'", "''")
                        query_pagamentos = f'''
                            SELECT 
                                dp.codigoReceita,
                                dp.numeroRetificacao,
                                dp.valorTotal,
                                dp.dataPagamento,
                                dpcr.descricao_receita
                            FROM Serpro.dbo.Di_Pagamento dp
                            LEFT JOIN Serpro.dbo.Di_pagamentos_cod_receitas dpcr 
                                ON dpcr.cod_receita = dp.codigoReceita
                            WHERE dp.rootDiId = {dados_di_id_escaped}
                        '''
                        logger.debug(f"🔍 [DI] Executando query de pagamentos para dadosDiId={dados_di_id}")
                        result_pag = sql_adapter.execute_query(query_pagamentos, 'Serpro', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
                        logger.debug(f"🔍 [DI] Resultado da query de pagamentos: success={result_pag.get('success')}, data_count={len(result_pag.get('data', []))}")
                        if result_pag.get('success') and result_pag.get('data'):
                            # ✅ Mapear códigos de receita para tipos de imposto (similar à DUIMP)
                            MAPEAMENTO_CODIGOS_RECEITA = {
                                '0086': 'II',  # Imposto de Importação
                                '86': 'II',
                                '1038': 'IPI',  # IPI
                                '38': 'IPI',
                                '5602': 'PIS',  # PIS/PASEP
                                '602': 'PIS',
                                '5629': 'COFINS',  # COFINS
                                '629': 'COFINS',
                                '5529': 'ANTIDUMPING',  # Antidumping
                                '529': 'ANTIDUMPING',
                                '7811': 'TAXA_UTILIZACAO',  # Taxa SISCOMEX
                                '811': 'TAXA_UTILIZACAO',
                            }
                            
                            for p_row in result_pag['data']:
                                codigo_receita = str(p_row.get('codigoReceita') or '').strip()
                                valor_total = p_row.get('valorTotal')
                                data_pagamento = p_row.get('dataPagamento')  # ✅ CORREÇÃO: Removido dataHoraPagamento (coluna não existe)
                                
                                if codigo_receita and valor_total:
                                    # Mapear código para tipo de imposto
                                    tipo_imposto = MAPEAMENTO_CODIGOS_RECEITA.get(codigo_receita)
                                    if not tipo_imposto:
                                        # Se não encontrou no mapeamento, usar descrição da receita
                                        descricao = p_row.get('descricao_receita', '')
                                        if 'IMPORTAÇÃO' in descricao.upper() or 'IMPORTACAO' in descricao.upper():
                                            tipo_imposto = 'II'
                                        elif 'IPI' in descricao.upper():
                                            tipo_imposto = 'IPI'
                                        elif 'PIS' in descricao.upper():
                                            tipo_imposto = 'PIS'
                                        elif 'COFINS' in descricao.upper():
                                            tipo_imposto = 'COFINS'
                                        else:
                                            tipo_imposto = descricao or f'RECEITA_{codigo_receita}'
                                    
                                    # Converter valor para float se for string
                                    try:
                                        valor_float = float(str(valor_total).replace(',', '.')) if valor_total else 0.0
                                    except:
                                        valor_float = 0.0
                                    
                                    if valor_float > 0:
                                        pagamentos.append({
                                            'tipo': tipo_imposto,
                                            'valor': valor_float,
                                            'data_pagamento': data_pagamento,
                                            'codigo_receita': codigo_receita,
                                        })
                                        logger.debug(f"✅ [DI] Pagamento adicionado: {tipo_imposto} = R$ {valor_float:,.2f}")
                        else:
                            logger.warning(f"⚠️ [DI] Query de pagamentos não retornou sucesso ou dados. Result: {result_pag}")
                    except Exception as e:
                        logger.error(f"❌ [DI] Erro ao buscar pagamentos da DI {numero_di}: {e}", exc_info=True)
                else:
                    logger.warning(f"⚠️ [DI] dadosDiId não encontrado para DI {numero_di}. Não é possível buscar pagamentos.")
                
                # ✅ NOVO: Buscar frete da DI (conforme MAPEAMENTO_SQL_SERVER.md)
                # ⚠️ IMPORTANTE: A relação é 1:1 (dadosDiId = freteId), então não deveria ter múltiplos registros
                # Mas se houver retificações, garantir que pegamos o frete da DI mais recente
                frete_di = None
                if dados_di_id:
                    try:
                        dados_di_id_escaped = str(dados_di_id).replace("'", "''")
                        # ✅ CORREÇÃO: Buscar frete diretamente pelo dadosDiId (relação 1:1)
                        # Segundo MAPEAMENTO_SQL_SERVER.md linha 441: Di_Root_Declaracao_Importacao.dadosDiId = Di_Frete.freteId
                        query_frete = f'''
                            SELECT TOP 1
                                diFrete.valorTotalDolares,
                                diFrete.totalReais
                            FROM Serpro.dbo.Di_Frete diFrete WITH (NOLOCK)
                            WHERE diFrete.freteId = {dados_di_id_escaped}
                        '''
                        logger.debug(f"🔍 [DI] Buscando frete para dadosDiId={dados_di_id} (freteId={dados_di_id})")
                        result_frete = sql_adapter.execute_query(query_frete, 'Serpro', None, notificar_erro=False)
                        if result_frete.get('success') and result_frete.get('data'):
                            frete_rows = result_frete['data']
                            if frete_rows and len(frete_rows) > 0:
                                frete_row = frete_rows[0]
                                valor_frete_dolar = frete_row.get('valorTotalDolares')
                                valor_frete_real = frete_row.get('totalReais')
                                # Converter para float se for string
                                try:
                                    valor_frete_dolar_float = float(str(valor_frete_dolar).replace(',', '.')) if valor_frete_dolar else None
                                    valor_frete_real_float = float(str(valor_frete_real).replace(',', '.')) if valor_frete_real else None
                                except:
                                    valor_frete_dolar_float = None
                                    valor_frete_real_float = None
                                
                                if valor_frete_dolar_float or valor_frete_real_float:
                                    frete_di = {
                                        'valor_total_dolares': valor_frete_dolar_float,
                                        'valor_total_reais': valor_frete_real_float,
                                    }
                                    logger.info(f"✅ [DI] Frete encontrado: USD {valor_frete_dolar_float or 0:,.2f}, BRL {valor_frete_real_float or 0:,.2f}")
                            else:
                                logger.warning(f"⚠️ [DI] Nenhum registro de frete encontrado para dadosDiId={dados_di_id}")
                        else:
                            logger.warning(f"⚠️ [DI] Erro ao buscar frete: {result_frete.get('error')}")
                    except Exception as e:
                        logger.warning(f"⚠️ [DI] Erro ao buscar frete da DI {numero_di}: {e}", exc_info=True)
                
                # ✅ NOVO: Buscar dados de transporte/navio e CE relacionado da DI (conforme MAPEAMENTO_SQL_SERVER.md)
                transporte_di = None
                numero_ce_di = None  # ✅ NOVO: CE relacionado à DI
                if dados_di_id:
                    try:
                        numero_di_escaped = row.get('numeroDi', numero_di).replace("'", "''")
                        numero_di_normalizado_escaped = numero_di_normalizado.replace("'", "''") if numero_di_normalizado else ''
                        # ✅ CORREÇÃO (26/01/2026): Di_Dados_Embarque não existe no Serpro deste ambiente.
                        # Usar apenas Di_Transporte (nomeVeiculo = navio). CE relacionado via Di_Dados_Embarque fica indisponível.
                        query_transporte = f'''
                            SELECT TOP 1
                                diTransp.nomeVeiculo,
                                diTransp.codigoViaTransporte,
                                diTransp.nomeTransportador,
                                diTransp.numeroVeiculo
                            FROM Serpro.dbo.Di_Dados_Gerais ddg
                            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON ddg.dadosGeraisId = diRoot.dadosGeraisId
                            LEFT JOIN Serpro.dbo.Di_Transporte diTransp ON diRoot.transporteId = diTransp.transporteId
                            WHERE ddg.numeroDi = '{numero_di_escaped}' OR ddg.numeroDi = '{numero_di_normalizado_escaped}'
                            ORDER BY ddg.dataHoraSituacaoDi DESC
                        '''
                        logger.debug(f"🔍 [DI] Buscando transporte/navio e CE para DI {numero_di}")
                        result_transporte = sql_adapter.execute_query(query_transporte, 'Serpro', None, notificar_erro=False)
                        if result_transporte.get('success') and result_transporte.get('data'):
                            transporte_rows = result_transporte['data']
                            if transporte_rows and len(transporte_rows) > 0:
                                transporte_row = transporte_rows[0]
                                nome_veiculo = transporte_row.get('nomeVeiculo')
                                nome_navio = transporte_row.get('nomeNavio') or nome_veiculo  # Di_Transporte.nomeVeiculo = navio
                                nome_transportador = transporte_row.get('nomeTransportador')
                                codigo_via = transporte_row.get('codigoViaTransporte')
                                
                                # CE relacionado só existe em Di_Dados_Embarque (tabela inexistente neste ambiente)
                                numero_ce_di = (transporte_row.get('numeroConhecimentoEmbarque') or 
                                               transporte_row.get('numeroConhecimentoEmbarqueMaster') or 
                                               transporte_row.get('numeroConhecimentoEmbarqueHouse'))
                                
                                if nome_veiculo or nome_navio or nome_transportador:
                                    transporte_di = {
                                        'nome_veiculo': nome_veiculo,
                                        'nome_navio': nome_navio,
                                        'nome_transportador': nome_transportador,
                                        'codigo_via_transporte': codigo_via,
                                        'numero_veiculo': transporte_row.get('numeroVeiculo'),
                                        'primeiro_navio': transporte_row.get('primeiroNavioEmb'),
                                        'navio_destino': transporte_row.get('navioDestinoEmb'),
                                    }
                                    logger.info(f"✅ [DI] Transporte/navio encontrado: {nome_veiculo or nome_navio or 'N/A'}")
                                
                                if numero_ce_di:
                                    logger.info(f"✅ [DI] CE relacionado encontrado: {numero_ce_di}")
                    except Exception as e:
                        error_msg = str(e)
                        if 'Invalid object name' in error_msg and 'Di_Dados_Embarque' in error_msg:
                            logger.debug(f'⚠️ Tabela Di_Dados_Embarque não encontrada para DI {numero_di}. Ignorando...')
                        else:
                            logger.warning(f"⚠️ [DI] Erro ao buscar transporte/navio da DI {numero_di}: {e}")
                
                di_data = {
                    'numero': row.get('numeroDi', numero_di),
                    'situacao': row.get('situacaoDi'),
                    'canal': row.get('canalSelecaoParametrizada'),
                    'data_desembaraco': row.get('dataHoraDesembaraco'),
                    'data_autorizacao_entrega': row.get('dataHoraAutorizacaoEntrega'),
                    'data_situacao': row.get('dataHoraSituacaoDi'),
                    'data_registro': row.get('dataHoraRegistro'),
                    'situacao_entrega': row.get('situacaoEntregaCarga'),
                    'modalidade': row.get('modalidadeDespacho', 'NORMAL'),
                    # ✅ CRÍTICO: Valores de mercadoria, impostos e importador
                    'tipo_recolhimento_icms': row.get('tipoRecolhimentoIcms'),
                    'nome_adquirente': row.get('nomeAdquirente'),
                    'nome_importador': row.get('nomeImportador'),
                    # ✅ NOVO: Frete da DI
                    'frete': frete_di,
                    'valor_mercadoria_descarga_dolar': row.get('dollar_VLMLD'),
                    'valor_mercadoria_descarga_real': row.get('real_VLMD'),
                    'valor_mercadoria_embarque_dolar': row.get('dollar_VLME'),
                    'valor_mercadoria_embarque_real': row.get('real_VLME'),
                    'data_pagamento_icms': row.get('dataPagamento'),
                    'updated_at_di_root': row.get('updatedi'),
                    'dadosDiId': dados_di_id,  # ✅ CRÍTICO: Incluir dadosDiId no retorno para debug
                }
                
                # ✅ NOVO: Adicionar pagamentos se encontrados
                if pagamentos:
                    di_data['pagamentos'] = pagamentos
                    logger.info(f"✅ [DI] {len(pagamentos)} pagamento(s) encontrado(s) para DI {di_data['numero']}")
                    total_impostos = sum(p.get('valor', 0) for p in pagamentos)
                    logger.info(f"✅ [DI] Total de impostos: R$ {total_impostos:,.2f}")
                else:
                    logger.warning(f"⚠️ [DI] Nenhum pagamento encontrado para DI {di_data.get('numero', numero_di)}")
                
                # ✅ NOVO: Adicionar frete se encontrado (já está em di_data['frete'], mas garantir que está presente)
                if frete_di:
                    di_data['frete'] = frete_di
                    logger.info(f"✅ [DI] Frete adicionado ao di_data para DI {di_data['numero']}")
                
                # ✅ NOVO: Adicionar transporte se encontrado
                if transporte_di:
                    di_data['transporte'] = transporte_di
                    logger.info(f"✅ [DI] Transporte/navio adicionado ao di_data para DI {di_data['numero']}")
                
                # ✅ NOVO: Buscar CE relacionado à DI via id_importacao (processos antigos não estão no Kanban)
                if id_importacao and not numero_ce_di:
                    logger.debug(f"🔍 [DI] Buscando CE relacionado via id_importacao {id_importacao}...")
                    ce_relacionado = _buscar_ce_por_id_importacao(sql_adapter, id_importacao)
                    if ce_relacionado and ce_relacionado.get('numero'):
                        numero_ce_di = ce_relacionado.get('numero')
                        di_data['numero_ce'] = numero_ce_di
                        di_data['ce_relacionado'] = ce_relacionado  # ✅ Incluir dados completos do CE
                        logger.info(f"✅ [DI] CE relacionado encontrado via id_importacao: {numero_ce_di}")
                
                return di_data
        else:
            logger.warning(f"⚠️ Query DI retornou sem sucesso ou sem dados. Result: {result}")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar DI completa: {e}", exc_info=True)
        return None


def _buscar_di_por_id_processo(
    sql_adapter,
    id_processo_importacao: int,
    id_importacao: Optional[int] = None,
    process_db: str = 'Make',
) -> Optional[Dict[str, Any]]:
    """
    Busca DI relacionada a um processo através do id_processo_importacao.
    
    Usa a mesma lógica da query di_kanban.sql:
    - Hi_Historico_Di.idImportacao → comex.dbo.Importacoes.id → make.dbo.PROCESSO_IMPORTACAO.id_importacao
    
    Tenta buscar em:
    1. Tabela Processos_Importacao (campo numero_di) - se estiver preenchido
    2. Via Hi_Historico_Di usando id_importacao (relação: Hi_Historico_Di.idImportacao = id_importacao)
    3. Via CE do processo (busca DI relacionada ao CE)
    
    Args:
        sql_adapter: Adaptador SQL Server
        id_processo_importacao: ID do processo de importação
        id_importacao: ID da importação (opcional, para buscar em Hi_Historico_Di)
    
    Returns:
        Dict com dados da DI ou None se não encontrada
    """
    try:
        # 1. Verificar se há numero_di na tabela Processos_Importacao
        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
        id_processo_escaped = str(id_processo_importacao).replace("'", "''")
        process_db_safe = (process_db or 'Make').replace("'", "''")
        query_proc = f'''
            SELECT TOP 1
                numero_di,
                numero_ce,
                id_importacao
            FROM {process_db_safe}.dbo.PROCESSO_IMPORTACAO
            WHERE id_processo_importacao = {id_processo_escaped}
        '''
        
        # ✅ Conectar no mesmo banco do processo (mAIke_assistente ou Make) - evita dependência do legado quando não necessário
        result_proc = sql_adapter.execute_query(query_proc, process_db_safe, None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        
        if result_proc.get('success') and result_proc.get('data'):
            rows = result_proc['data']
            if rows and len(rows) > 0:
                row = rows[0]
                numero_di = row.get('numero_di')
                numero_ce = row.get('numero_ce')
                id_import = id_importacao or row.get('id_importacao')
                
                logger.debug(f"📄 Dados do processo: numero_di={numero_di}, numero_ce={numero_ce}, id_import={id_import}, id_importacao_param={id_importacao}")
                
                # Se tem numero_di, buscar diretamente
                if numero_di:
                    logger.debug(f"📄 DI encontrada no campo numero_di: {numero_di}")
                    return _buscar_di_completo(sql_adapter, numero_di, None)
                
                # 2. Se não tem numero_di, buscar via Hi_Historico_Di usando id_importacao
                # Seguindo a mesma lógica da query di_kanban.sql
                logger.debug(f"📄 Verificando se id_import está definido: {id_import} (tipo: {type(id_import)})")
                if id_import:
                    logger.info(f"📄 Buscando DI via Hi_Historico_Di com id_importacao {id_import}...")
                    logger.debug(f"📄 Buscando DI via Hi_Historico_Di com id_importacao {id_import}...")
                    try:
                        # Query baseada em di_kanban.sql: busca DI através de id_importacao com TODOS os campos
                        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
                        id_import_escaped = str(id_import).replace("'", "''")
                        query_di_historico = f'''
                            SELECT TOP 1
                                diH.idImportacao,
                                diDesp.dataHoraDesembaraco,
                                diDesp.canalSelecaoParametrizada,
                                ddg.situacaoDi,
                                ddg.numeroDi,
                                ddg.situacaoEntregaCarga,
                                ddg.updatedAt AS updatedAtDiGerais,
                                diDesp.dataHoraRegistro,
                                ddg.dataHoraSituacaoDi,
                                DICM.tipoRecolhimento AS tipoRecolhimentoIcms,
                                DA.nomeAdquirente,
                                DI.nomeImportador,
                                DVMD.totalDolares AS dollar_VLMLD,
                                DVMD.totalReais AS real_VLMD,
                                DVME.totalDolares AS dollar_VLME,
                                DVME.totalReais AS real_VLME,
                                DICM.dataPagamento,
                                diRoot.updatedAt AS updatedi,
                                diH.updatedAt AS updatehistdi,
                                diDesp.modalidadeDespacho,
                                diDesp.dataHoraAutorizacaoEntrega
                            FROM Serpro.dbo.Hi_Historico_Di diH
                            JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
                                ON diH.diId = diRoot.dadosDiId
                            JOIN Serpro.dbo.Di_Dados_Despacho diDesp
                                ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                            JOIN Serpro.dbo.Di_Dados_Gerais ddg 
                                ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                            LEFT JOIN Serpro.dbo.Di_Icms DICM 
                                ON diRoot.dadosDiId = DICM.rootDiId
                            LEFT JOIN Serpro.dbo.Di_Adquirente DA 
                                ON diRoot.dadosDiId = DA.adquirenteId
                            LEFT JOIN Serpro.dbo.Di_Importador DI
                                ON diRoot.importadorId = DI.importadorId
                            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD 
                                ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
                            LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME 
                                ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
                            WHERE diH.idImportacao = {id_import_escaped}
                            ORDER BY ddg.dataHoraSituacaoDi DESC
                        '''
                        result_historico = sql_adapter.execute_query(query_di_historico, 'Serpro', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
                        logger.info(f"📄 Resultado query Hi_Historico_Di: success={result_historico.get('success')}, has_data={bool(result_historico.get('data'))}")
                        if result_historico.get('success') and result_historico.get('data'):
                            rows_historico = result_historico['data']
                            logger.info(f"📄 Rows encontradas: {len(rows_historico) if rows_historico else 0}")
                            if rows_historico and len(rows_historico) > 0:
                                di_row = rows_historico[0]
                                numero_di_encontrado = di_row.get('numeroDi')
                                logger.info(f"📄 numeroDi encontrado: {numero_di_encontrado}")
                                if numero_di_encontrado:
                                    logger.info(f"✅ DI encontrada via Hi_Historico_Di (id_importacao={id_import}): {numero_di_encontrado}")
                                    # Retornar TODOS os campos da query di_kanban.sql
                                    return {
                                        'numero': numero_di_encontrado,
                                        'situacao': di_row.get('situacaoDi'),
                                        'canal': di_row.get('canalSelecaoParametrizada'),
                                        'data_desembaraco': di_row.get('dataHoraDesembaraco'),
                                        'data_autorizacao_entrega': di_row.get('dataHoraAutorizacaoEntrega'),
                                        'data_situacao': di_row.get('dataHoraSituacaoDi'),
                                        'data_registro': di_row.get('dataHoraRegistro'),
                                        'situacao_entrega': di_row.get('situacaoEntregaCarga'),
                                        'modalidade': di_row.get('modalidadeDespacho', 'NORMAL'),
                                        # Campos adicionais da query di_kanban.sql
                                        'id_importacao': di_row.get('idImportacao'),
                                        'updated_at_di_gerais': di_row.get('updatedAtDiGerais'),
                                        'tipo_recolhimento_icms': di_row.get('tipoRecolhimentoIcms'),
                                        'nome_adquirente': di_row.get('nomeAdquirente'),
                                        'nome_importador': di_row.get('nomeImportador'),
                                        'valor_mercadoria_descarga_dolar': di_row.get('dollar_VLMLD'),
                                        'valor_mercadoria_descarga_real': di_row.get('real_VLMD'),
                                        'valor_mercadoria_embarque_dolar': di_row.get('dollar_VLME'),
                                        'valor_mercadoria_embarque_real': di_row.get('real_VLME'),
                                        'data_pagamento_icms': di_row.get('dataPagamento'),
                                        'updated_at_di_root': di_row.get('updatedi'),
                                        'updated_at_historico': di_row.get('updatehistdi'),
                                    }
                                else:
                                    logger.warning(f"⚠️ numeroDi está vazio ou None")
                            else:
                                logger.warning(f"⚠️ Nenhuma row retornada da query Hi_Historico_Di")
                        else:
                            logger.warning(f"⚠️ Query Hi_Historico_Di não retornou success ou data: {result_historico.get('error', 'N/A')}")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao buscar DI via Hi_Historico_Di: {e}", exc_info=True)
                
                # 3. Se não tem numero_di mas tem CE, buscar DI via CE
                if numero_ce:
                    logger.debug(f"📄 Buscando DI via CE {numero_ce}...")
                    return _buscar_di_por_ce(sql_adapter, numero_ce)
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar DI por ID Processo: {e}", exc_info=True)
        return None


def _buscar_di_por_ce(sql_adapter, numero_ce: str) -> Optional[Dict[str, Any]]:
    """
    Busca DI relacionada a um CE através da tabela Di_Dados_Embarque.
    
    Args:
        sql_adapter: Adaptador SQL Server
        numero_ce: Número do CE
    
    Returns:
        Dict com dados da DI ou None se não encontrada
    """
    try:
        # Buscar DI relacionada ao CE através de Di_Dados_Embarque
        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
        numero_ce_escaped = numero_ce.replace("'", "''")
        query_di_por_ce = f'''
            SELECT TOP 1
                ddg.numeroDi,
                ddg.situacaoDi,
                ddg.dataHoraSituacaoDi,
                ddg.situacaoEntregaCarga,
                diDesp.dataHoraDesembaraco,
                diDesp.canalSelecaoParametrizada,
                diDesp.modalidadeDespacho,
                diDesp.dataHoraAutorizacaoEntrega
            FROM Serpro.dbo.Di_Dados_Gerais ddg
            INNER JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot ON ddg.dadosGeraisId = diRoot.dadosGeraisId
            LEFT JOIN Serpro.dbo.Di_Dados_Despacho diDesp ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
            LEFT JOIN Serpro.dbo.Di_Dados_Embarque diEmb ON diRoot.dadosEmbarqueId = diEmb.dadosEmbarqueId
            WHERE diEmb.numeroConhecimentoEmbarque = '{numero_ce_escaped}' 
               OR diEmb.numeroConhecimentoEmbarqueMaster = '{numero_ce_escaped}'
               OR diEmb.numeroConhecimentoEmbarqueHouse = '{numero_ce_escaped}'
            ORDER BY ddg.dataHoraSituacaoDi DESC
        '''
        
        result = sql_adapter.execute_query(query_di_por_ce, 'Serpro', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        
        # ✅ CORREÇÃO: Tratar erro de tabela não encontrada silenciosamente
        if not result.get('success'):
            error_msg = result.get('error', '')
            if 'Invalid object name' in error_msg and 'Di_Dados_Embarque' in error_msg:
                logger.debug(f'⚠️ Tabela Di_Dados_Embarque não encontrada para CE {numero_ce}. Ignorando...')
                return None
            # Se for outro erro, logar como debug (não warning para não poluir logs)
            logger.debug(f'⚠️ Erro ao buscar DI por CE {numero_ce}: {error_msg}')
            return None
        
        if result.get('data'):
            rows = result['data']
            if rows and len(rows) > 0:
                row = rows[0]
                return {
                    'numero': row.get('numeroDi'),
                    'situacao': row.get('situacaoDi'),
                    'canal': row.get('canalSelecaoParametrizada'),
                    'data_desembaraco': row.get('dataHoraDesembaraco'),
                    'data_autorizacao_entrega': row.get('dataHoraAutorizacaoEntrega'),
                    'data_situacao': row.get('dataHoraSituacaoDi'),
                    'situacao_entrega': row.get('situacaoEntregaCarga'),
                    'modalidade': row.get('modalidadeDespacho', 'NORMAL'),
                }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar DI por CE: {e}", exc_info=True)
        return None


def _buscar_duimp_completo(sql_adapter, numero_duimp: str, processo_referencia: str, id_importacao: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Busca dados completos da DUIMP usando a query oficial do Kanban
    
    ✅ NOVO: Se id_importacao for fornecido, também busca o CE relacionado (processos antigos não estão no Kanban).
    """
    logger.info(f"🔍 [DUIMP] _buscar_duimp_completo chamado: numero={numero_duimp}, processo={processo_referencia}, id_importacao={id_importacao}")
    try:
        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?, usar formatação direta (escapada)
        numero_duimp_escaped = numero_duimp.replace("'", "''")
        processo_ref_escaped = processo_referencia.replace("'", "''")
        
        # ✅ QUERY: Buscar dados básicos (usar DISTINCT sem duimp_id para evitar problemas)
        query_duimp = f'''
            SELECT DISTINCT
                d.numero,
                d.versao,
                d.ultima_situacao AS ultima_situacao_hook,
                d.ultimo_evento AS ultimo_evento_hook,
                d.data_ultimo_evento AS data_ultimo_evento_hook,
                drar.canal_consolidado AS canal_duimp,
                dd.situacao_duimp AS situacao_duimp,
                dd.data_geracao AS data_geracao_diagnostico,
                ds.situacao_licenciamento AS situacao_licenciamento,
                ds.controle_carga
            FROM Duimp.dbo.duimp d WITH (NOLOCK)
            LEFT JOIN Duimp.dbo.duimp_diagnostico dd WITH (NOLOCK)
                ON dd.duimp_id = d.duimp_id
            LEFT JOIN Duimp.dbo.duimp_situacao ds WITH (NOLOCK)
                ON ds.duimp_id = d.duimp_id
            LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar WITH (NOLOCK)
                ON drar.duimp_id = d.duimp_id
            WHERE d.numero = '{numero_duimp_escaped}' OR d.numero_processo = '{processo_ref_escaped}'
            ORDER BY d.data_ultimo_evento DESC, dd.data_geracao DESC
        '''
        
        # ✅ Buscar duimp_id separadamente
        query_id = f'''
            SELECT TOP 1 duimp_id
            FROM Duimp.dbo.duimp WITH (NOLOCK)
            WHERE numero = '{numero_duimp_escaped}' OR numero_processo = '{processo_ref_escaped}'
            ORDER BY data_ultimo_evento DESC
        '''
        
        # ✅ CORREÇÃO: Usar 'Make' como database (schema completo já está na query)
        # Primeiro buscar duimp_id
        result_id = sql_adapter.execute_query(query_id, 'Make', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        duimp_id = None
        if result_id.get('success') and result_id.get('data') and len(result_id['data']) > 0:
            duimp_id = result_id['data'][0].get('duimp_id')
            logger.info(f"✅ [DUIMP] duimp_id encontrado: {duimp_id}")
        
        result = sql_adapter.execute_query(query_duimp, 'Make', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        logger.info(f"🔍 [DUIMP] Query executada - success: {result.get('success')}, rows: {len(result.get('data', []))}")
        
        if result.get('success') and result.get('data'):
            rows = result['data']
            if rows and len(rows) > 0:
                # Pegar primeira linha para dados básicos
                row = rows[0]
                
                # ✅ Buscar canal em todas as linhas (pode estar em linha diferente)
                canal_encontrado = None
                for r in rows:
                    canal_temp = r.get('canal_duimp')
                    if canal_temp:
                        canal_encontrado = canal_temp
                        break
                
                # Extrair dados básicos (da primeira linha)
                duimp_data = {
                    'numero': row.get('numero', numero_duimp),
                    'versao': row.get('versao', '1'),
                    'situacao': row.get('situacao_duimp') or row.get('ultima_situacao_hook') or row.get('situacao_duimp_agr'),
                    'canal': canal_encontrado or row.get('canal_duimp'),  # ✅ Usar canal encontrado em qualquer linha
                    'controle_carga': row.get('controle_carga'),
                    'ultima_situacao': row.get('ultima_situacao_hook'),
                    'ultimo_evento': row.get('ultimo_evento_hook'),
                    'data_ultimo_evento': row.get('data_ultimo_evento_hook'),
                    'situacao_licenciamento': row.get('situacao_licenciamento'),
                    'situacao_analise_retificacao': row.get('situacao_analise_retificacao'),
                    'situacao_conferencia_aduaneira': row.get('situacao_conferencia_aduaneira'),
                    'orgao': row.get('orgao'),
                    'resultado': row.get('resultado'),
                }
                
                # ✅ Buscar pagamentos separadamente (para evitar JSON muito grande)
                pagamentos = []
                if duimp_id:
                    try:
                        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
                        duimp_id_escaped = str(duimp_id).replace("'", "''")
                        query_pagamentos = f'''
                            SELECT 
                                data_pagamento,
                                tributo_tipo,
                                valor
                            FROM Duimp.dbo.duimp_pagamentos WITH (NOLOCK)
                            WHERE duimp_id = {duimp_id_escaped}
                            ORDER BY data_pagamento DESC
                        '''
                        result_pag = sql_adapter.execute_query(query_pagamentos, 'Make', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
                        if result_pag.get('success') and result_pag.get('data'):
                            for p_row in result_pag['data']:
                                if p_row.get('tributo_tipo') and p_row.get('valor'):
                                    pagamentos.append({
                                        'tipo': p_row.get('tributo_tipo'),
                                        'valor': p_row.get('valor'),
                                        'data_pagamento': p_row.get('data_pagamento'),
                                    })
                    except Exception as e:
                        logger.debug(f"Erro ao buscar pagamentos: {e}")
                
                if pagamentos:
                    duimp_data['pagamentos'] = pagamentos
                    logger.info(f"✅ {len(pagamentos)} pagamento(s) encontrado(s) para DUIMP {duimp_data['numero']}")

                # ✅ NOVO (22/01/2026): Tributos calculados (mais completo que pagamentos)
                # Alguns casos não possuem registros em duimp_pagamentos, mas possuem tributos calculados.
                tributos_calculados = []
                if duimp_id:
                    try:
                        duimp_id_escaped = str(duimp_id).replace("'", "''")
                        query_tributos_calc = f'''
                            SELECT
                                tipo,
                                valor_calculado,
                                valor_devido,
                                valor_a_recolher,
                                valor_recolhido,
                                valor_suspenso,
                                valor_a_reduzir
                            FROM Duimp.dbo.duimp_tributos_calculados WITH (NOLOCK)
                            WHERE duimp_id = {duimp_id_escaped}
                            ORDER BY tipo
                        '''
                        result_tc = sql_adapter.execute_query(query_tributos_calc, 'Make', None, notificar_erro=False)
                        if result_tc.get('success') and result_tc.get('data'):
                            for row_tc in result_tc['data']:
                                if not isinstance(row_tc, dict):
                                    continue
                                tipo = row_tc.get('tipo') or 'N/A'
                                tributos_calculados.append({
                                    'tipo': tipo,
                                    'valoresBRL': {
                                        'calculado': row_tc.get('valor_calculado'),
                                        'devido': row_tc.get('valor_devido'),
                                        'aRecolher': row_tc.get('valor_a_recolher'),
                                        'recolhido': row_tc.get('valor_recolhido'),
                                        'suspenso': row_tc.get('valor_suspenso'),
                                        'aReduzir': row_tc.get('valor_a_reduzir'),
                                    }
                                })
                    except Exception as e:
                        logger.debug(f"Erro ao buscar tributos calculados: {e}")

                if tributos_calculados:
                    duimp_data['tributos_calculados'] = tributos_calculados
                    logger.info(f"✅ {len(tributos_calculados)} tributo(s) calculado(s) encontrado(s) para DUIMP {duimp_data['numero']}")
                
                logger.info(f"✅ DUIMP encontrada: {duimp_data['numero']} - Situação: {duimp_data['situacao']} - Canal: {duimp_data['canal']}")
                
                # ✅ NOVO: Buscar histórico completo de situações de duimp_diagnostico
                historico_situacoes = []
                if duimp_id:
                    try:
                        # Buscar histórico de duimp_diagnostico (situações) ordenado por data
                        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
                        duimp_id_escaped = str(duimp_id).replace("'", "''")
                        query_historico_diag = f'''
                            SELECT 
                                situacao_duimp,
                                situacao,
                                data_geracao
                            FROM duimp.dbo.duimp_diagnostico WITH (NOLOCK)
                            WHERE duimp_id = {duimp_id_escaped}
                            ORDER BY data_geracao DESC
                        '''
                        result_historico_diag = sql_adapter.execute_query(query_historico_diag, 'Make', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
                        
                        if result_historico_diag.get('success') and result_historico_diag.get('data'):
                            for diag_row in result_historico_diag['data']:
                                situacao_hist = diag_row.get('situacao_duimp') or diag_row.get('situacao')
                                if situacao_hist:  # Só adicionar se tiver situação
                                    historico_situacoes.append({
                                        'situacao': situacao_hist,
                                        'data': diag_row.get('data_geracao'),
                                    })
                            
                            if historico_situacoes:
                                duimp_data['historico_situacoes'] = historico_situacoes
                                logger.info(f"✅ Histórico de situações encontrado: {len(historico_situacoes)} registro(s)")
                    except Exception as e:
                        logger.debug(f"Erro ao buscar histórico de situações: {e}")
                
                # ✅ CRÍTICO: Tentar buscar JSON completo de uma query separada (caso exista coluna)
                # Tentar várias possíveis colunas que podem armazenar o JSON
                json_completo = None
                try:
                    # Tentar buscar de coluna json_completo
                    # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
                    numero_duimp_escaped = numero_duimp.replace("'", "''")
                    processo_ref_escaped = processo_referencia.replace("'", "''")
                    query_json = f'''
                        SELECT TOP 1 json_completo, payload, dados_completos, payload_completo
                        FROM duimp.dbo.duimp
                        WHERE numero = '{numero_duimp_escaped}' OR numero_processo = '{processo_ref_escaped}'
                    '''
                    result_json = sql_adapter.execute_query(query_json, 'Make', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
                    if result_json.get('success') and result_json.get('data'):
                        json_rows = result_json['data']
                        if json_rows and len(json_rows) > 0:
                            json_row = json_rows[0]
                            json_completo = (
                                json_row.get('json_completo') or 
                                json_row.get('payload') or 
                                json_row.get('dados_completos') or 
                                json_row.get('payload_completo')
                            )
                except Exception as e:
                    # Se a query falhar (colunas não existem), continuar sem JSON
                    logger.debug(f"Colunas de JSON não disponíveis na tabela duimp: {e}")
                
                if json_completo:
                    try:
                        import json
                        if isinstance(json_completo, str):
                            payload_parsed = json.loads(json_completo)
                        else:
                            payload_parsed = json_completo
                        
                        if isinstance(payload_parsed, dict):
                            # Extrair situação do JSON
                            situacao_obj = payload_parsed.get('situacao', {})
                            if isinstance(situacao_obj, dict):
                                situacao_duimp_json = situacao_obj.get('situacaoDuimp', '')
                                if situacao_duimp_json:
                                    duimp_data['situacao'] = situacao_duimp_json
                                    logger.info(f"✅ Situação extraída do JSON: {situacao_duimp_json}")
                            
                            # Extrair canal do JSON (sempre priorizar do JSON se disponível)
                            resultado_risco = payload_parsed.get('resultadoAnaliseRisco', {})
                            if isinstance(resultado_risco, dict):
                                canal_json = resultado_risco.get('canalConsolidado', '') or resultado_risco.get('canal', '')
                                if canal_json:
                                    duimp_data['canal'] = canal_json
                                    logger.info(f"✅ Canal extraído do JSON (resultadoAnaliseRisco.canalConsolidado): {canal_json}")
                                else:
                                    logger.warning(f"⚠️ Canal não encontrado em resultadoAnaliseRisco. Chaves disponíveis: {list(resultado_risco.keys())}")
                            else:
                                logger.warning(f"⚠️ resultadoAnaliseRisco não é dict: {type(resultado_risco)}. Valor: {resultado_risco}")
                            
                            # ✅ FALLBACK: Tentar buscar canal em outros lugares do JSON se não encontrou
                            if not duimp_data.get('canal'):
                                # Tentar buscar direto na raiz do JSON
                                canal_fallback = (
                                    payload_parsed.get('canalConsolidado') or
                                    payload_parsed.get('canal_consolidado') or
                                    payload_parsed.get('canal') or
                                    payload_parsed.get('canalSelecaoParametrizada')
                                )
                                if canal_fallback:
                                    duimp_data['canal'] = canal_fallback
                                    logger.info(f"✅ Canal encontrado em fallback do JSON: {canal_fallback}")
                            
                            # Guardar payload completo para uso posterior (impostos, etc)
                            duimp_data['payload_completo'] = payload_parsed
                    except Exception as e:
                        logger.debug(f"Erro ao parsear JSON completo da DUIMP: {e}")
                
                # ✅ NOVO: Buscar CE relacionado à DUIMP via id_importacao (similar à DI)
                # Isso é um fallback se o CE não veio do Kanban ou se o processo é antigo
                if id_importacao and not duimp_data.get('numero_ce'):
                    logger.debug(f"🔍 [DUIMP] Buscando CE relacionado via id_importacao {id_importacao} (fallback)...")
                    ce_relacionado = _buscar_ce_por_id_importacao(sql_adapter, id_importacao)
                    if ce_relacionado and ce_relacionado.get('numero'):
                        duimp_data['numero_ce'] = ce_relacionado.get('numero')
                        duimp_data['ce_relacionado'] = ce_relacionado  # ✅ Incluir dados completos do CE
                        logger.info(f"✅ [DUIMP] CE relacionado encontrado via id_importacao: {duimp_data['numero_ce']}")
                
                return duimp_data
        
        logger.warning(f"⚠️ [DUIMP] Query não retornou dados - success: {result.get('success')}, error: {result.get('error')}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar DUIMP completa: {e}", exc_info=True)
        return None


def _buscar_cct_completo(sql_adapter, id_importacao: int) -> Optional[Dict[str, Any]]:
    """Busca dados completos do CCT (Conhecimento de Carga Aérea)"""
    try:
        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
        id_import_escaped = str(id_importacao).replace("'", "''")
        # Query: Buscar CCT principal
        query_cct = f'''
            SELECT TOP 1
                cctRoot.identificacao,
                cctEstoque.situacaoAtual,
                cctEstoque.dataHoraSituacaoAtual,
                cctEstoque.recintoAduaneiro,
                cctEstoque.unidadeRfb
            FROM duimp.dbo.CCT_Aereo_RootAereoEntity cctRoot
            LEFT JOIN duimp.dbo.CCT_Aereo_PartesEstoque cctEstoque ON cctRoot.id = cctEstoque.rootAereoEntityId
            WHERE cctRoot.idImportacao = {id_import_escaped}
            ORDER BY cctEstoque.dataHoraSituacaoAtual DESC
        '''
        
        result = sql_adapter.execute_query(query_cct, 'duimp', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        
        # ✅ CORREÇÃO: Tratar erro de coluna não encontrada silenciosamente
        if not result.get('success'):
            error_msg = result.get('error', '')
            if 'Invalid column name' in error_msg and ('idRootAereoEntity' in error_msg or 'rootAereoEntityId' in error_msg):
                logger.debug(f'⚠️ Coluna de relacionamento CCT não encontrada para id_importacao {id_importacao}. Ignorando...')
                return None
            # Se for outro erro, logar como debug (não warning para não poluir logs)
            logger.debug(f'⚠️ Erro ao buscar CCT completo para id_importacao {id_importacao}: {error_msg}')
            return None
        
        if result.get('data'):
            rows = result['data']
            if rows and len(rows) > 0:
                row = rows[0]
                
                # Buscar bloqueios ativos (precisa do ID do root)
                # Tentar buscar o ID do root primeiro
                # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
                id_import_escaped = str(id_importacao).replace("'", "''")
                query_root_id = f'''
                    SELECT TOP 1 id
                    FROM duimp.dbo.CCT_Aereo_RootAereoEntity
                    WHERE idImportacao = {id_import_escaped}
                '''
                result_root = sql_adapter.execute_query(query_root_id, 'duimp', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
                cct_root_id = None
                if result_root.get('success') and result_root.get('data'):
                    root_rows = result_root['data']
                    if root_rows and len(root_rows) > 0:
                        cct_root_id = root_rows[0].get('id')
                
                bloqueios = _buscar_cct_bloqueios(sql_adapter, cct_root_id)
                
                return {
                    'numero': row.get('identificacao'),
                    'situacao': row.get('situacaoAtual'),
                    'data_situacao': row.get('dataHoraSituacaoAtual'),
                    'recinto_aduaneiro': row.get('recintoAduaneiro'),
                    'unidade_rfb': row.get('unidadeRfb'),
                    'bloqueios_ativos': bloqueios or [],
                }
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar CCT completo: {e}")
        return None


def _buscar_cct_bloqueios(sql_adapter, cct_id: Optional[int]) -> List[Dict[str, Any]]:
    """Busca bloqueios ativos do CCT"""
    if not cct_id:
        return []
    
    try:
        # ✅ CORREÇÃO: Node.js adapter não suporta parâmetros ?
        cct_id_escaped = str(cct_id).replace("'", "''")
        query = f'''
            SELECT 
                descricaoTipo,
                codigoTipo,
                justificativa,
                motivo
            FROM duimp.dbo.CCT_Aereo_BloqueiosAtivo
            WHERE rootAereoEntityId = {cct_id_escaped}
        '''
        
        result = sql_adapter.execute_query(query, 'duimp', None, notificar_erro=False)  # ✅ Sem parâmetros para Node.js, sem notificar erros
        
        # ✅ CORREÇÃO: Tratar erro de coluna não encontrada silenciosamente
        if not result.get('success'):
            error_msg = result.get('error', '')
            if 'Invalid column name' in error_msg and ('idRootAereoEntity' in error_msg or 'rootAereoEntityId' in error_msg):
                logger.debug(f'⚠️ Coluna de relacionamento CCT não encontrada para bloqueios id {cct_id}. Ignorando...')
                return []
            # Se for outro erro, logar como debug (não warning para não poluir logs)
            logger.debug(f'⚠️ Erro ao buscar bloqueios do CCT id {cct_id}: {error_msg}')
            return []
        
        if result.get('success') and result.get('data'):
            bloqueios = []
            for row in result['data']:
                bloqueios.append({
                    'descricao_tipo': row.get('descricaoTipo'),
                    'codigo_tipo': row.get('codigoTipo'),
                    'justificativa': row.get('justificativa'),
                    'motivo': row.get('motivo'),
                })
            return bloqueios
        
        return []
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar bloqueios do CCT: {e}")
        return []

