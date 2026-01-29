"""
Serviço para detectar e sugerir vinculações automáticas de lançamentos bancários a processos.

Quando uma DI/DUIMP é desembaraçada, o sistema:
1. Calcula o total de impostos (II + IPI + PIS + COFINS + TAXA_UTILIZACAO)
2. Busca lançamentos bancários não classificados com valor compatível
3. Cria sugestão de vinculação
4. Usuário pode aplicar ou ignorar
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

from db_manager import get_db_connection
from utils.sql_server_adapter import get_sql_adapter

logger = logging.getLogger(__name__)


class BancoAutoVinculacaoService:
    """Serviço para detectar e sugerir vinculações automáticas."""
    
    # ✅ Estados de conciliação por processo (usados para evitar sugestões repetidas)
    STATUS_NAO_ANALISADO = "NAO_ANALISADO"
    STATUS_CONCILIADO_BANCO = "CONCILIADO_BANCO_MAIKE"
    STATUS_PAGO_DIRETO_CLIENTE = "PAGO_DIRETO_CLIENTE"
    
    def __init__(self):
        self.sql_adapter = get_sql_adapter()
    
    def detectar_e_criar_sugestao(
        self,
        processo_referencia: str,
        tipo_documento: str,  # 'DI' ou 'DUIMP'
        numero_documento: Optional[str],
        data_desembaraco: datetime,
        total_impostos: Decimal,
        dados_processo: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detecta lançamentos bancários compatíveis e cria sugestão de vinculação.
        
        Args:
            processo_referencia: Referência do processo (ex: GLT.0011/26)
            tipo_documento: 'DI' ou 'DUIMP'
            numero_documento: Número da DI/DUIMP
            data_desembaraco: Data do desembaraço
            total_impostos: Valor total dos impostos
            dados_processo: Dados completos do processo (opcional, para extrair mais info)
        
        Returns:
            Dict com sucesso, sugestao_criada, matches_encontrados
        """
        try:
            # 0. Verificar status de conciliação do processo (evita sugestões desnecessárias)
            status_processo = self._obter_status_conciliacao_processo(processo_referencia)
            if status_processo == self.STATUS_CONCILIADO_BANCO:
                logger.info(f"ℹ️ Processo {processo_referencia} já conciliado no banco (impostos de importação). Não criando nova sugestão.")
                return {
                    'sucesso': True,
                    'sugestao_criada': False,
                    'matches_encontrados': 0,
                    'status_processo': status_processo,
                    'resposta': f'ℹ️ Processo {processo_referencia} já possui conciliação de impostos de importação. Nenhuma nova sugestão foi gerada.'
                }
            
            if status_processo == self.STATUS_PAGO_DIRETO_CLIENTE:
                logger.info(f"ℹ️ Processo {processo_referencia} marcado como pago direto na conta do cliente. Não criando sugestão.")
                return {
                    'sucesso': True,
                    'sugestao_criada': False,
                    'matches_encontrados': 0,
                    'status_processo': status_processo,
                    'resposta': f'ℹ️ Processo {processo_referencia} está marcado como pago direto na conta do cliente. Não há conciliação bancária a sugerir.'
                }

            # 1. Buscar lançamentos bancários compatíveis
            matches = self._buscar_lancamentos_compativeis(
                valor_esperado=float(total_impostos),
                data_desembaraco=data_desembaraco,
                tolerancia_valor=0.10,  # R$ 0,10 de tolerância
                tolerancia_dias=2  # ±2 dias
            )
            
            if not matches:
                logger.info(f"⚠️ Nenhum lançamento compatível encontrado para {processo_referencia} (valor: R$ {total_impostos:,.2f})")
                return {
                    'sucesso': True,
                    'sugestao_criada': False,
                    'matches_encontrados': 0,
                    'resposta': f'⚠️ Nenhum lançamento bancário compatível encontrado para {processo_referencia} (valor esperado: R$ {total_impostos:,.2f})'
                }
            
            # 2. Escolher melhor match (maior score de confiança)
            melhor_match = max(matches, key=lambda m: m.get('score_confianca', 0))
            
            # 3. Verificar se já existe sugestão pendente para este processo
            sugestao_existente = self._buscar_sugestao_pendente(processo_referencia)
            if sugestao_existente:
                logger.info(f"ℹ️ Sugestão já existe para {processo_referencia} (ID: {sugestao_existente.get('id')})")
                return {
                    'sucesso': True,
                    'sugestao_criada': False,
                    'sugestao_existente': True,
                    'matches_encontrados': len(matches),
                    'resposta': f'ℹ️ Sugestão já existe para {processo_referencia}'
                }
            
            # 4. Criar sugestão no banco
            sugestao_id = self._criar_sugestao(
                processo_referencia=processo_referencia,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                data_desembaraco=data_desembaraco,
                total_impostos=total_impostos,
                id_movimentacao=melhor_match.get('id_movimentacao'),
                score_confianca=melhor_match.get('score_confianca', 0),
                observacoes=f"Encontrados {len(matches)} lançamento(s) compatível(is). Melhor match: {melhor_match.get('score_confianca', 0)}% de confiança."
            )
            
            logger.info(f"✅ Sugestão criada: ID {sugestao_id} para {processo_referencia} (match: {melhor_match.get('id_movimentacao')}, score: {melhor_match.get('score_confianca', 0)}%)")
            
            return {
                'sucesso': True,
                'sugestao_criada': True,
                'sugestao_id': sugestao_id,
                'matches_encontrados': len(matches),
                'melhor_match': melhor_match,
                'resposta': f'✅ Sugestão de vinculação criada para {processo_referencia} (R$ {total_impostos:,.2f} → lançamento ID {melhor_match.get("id_movimentacao")})'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao detectar e criar sugestão: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao criar sugestão: {str(e)}'
            }
    
    def _buscar_lancamentos_compativeis(
        self,
        valor_esperado: float,
        data_desembaraco: datetime,
        tolerancia_valor: float = 0.10,
        tolerancia_dias: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Busca lançamentos bancários compatíveis com o valor e data esperados.
        
        Args:
            valor_esperado: Valor total dos impostos
            data_desembaraco: Data do desembaraço
            tolerancia_valor: Tolerância em reais (padrão: R$ 0,10)
            tolerancia_dias: Tolerância em dias (padrão: ±2 dias)
        
        Returns:
            Lista de matches com score de confiança
        """
        if not self.sql_adapter:
            return []
        
        try:
            # Calcular range de datas
            data_inicio = (data_desembaraco - timedelta(days=tolerancia_dias)).strftime('%Y-%m-%d')
            data_fim = (data_desembaraco + timedelta(days=tolerancia_dias)).strftime('%Y-%m-%d')
            
            # Padrões de descrição para pagamentos de impostos
            padroes_descricao = [
                '%importação siscomex%',
                '%PAGAMENTO DE SISCOMEX%',
                '%PAGAMENTO PUCOMEX%',
                '%SISCOMEX%',
                '%PUCOMEX%'
            ]
            
            # Construir query
            where_descricao = ' OR '.join([f"CAST(mb.descricao_movimentacao AS VARCHAR(MAX)) LIKE '{p}'" for p in padroes_descricao])
            
            query = f"""
                SELECT
                    mb.id_movimentacao,
                    mb.banco_origem,
                    mb.agencia_origem,
                    mb.conta_origem,
                    mb.data_movimentacao,
                    mb.valor_movimentacao,
                    mb.sinal_movimentacao,
                    CAST(mb.descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao,
                    mb.criado_em,
                    -- Verificar se já está classificado
                    (SELECT COUNT(*) FROM dbo.LANCAMENTO_TIPO_DESPESA ltd WHERE ltd.id_movimentacao_bancaria = mb.id_movimentacao) as tem_classificacao
                FROM dbo.MOVIMENTACAO_BANCARIA mb
                WHERE mb.sinal_movimentacao = 'D'  -- Apenas débitos
                  AND CAST(mb.data_movimentacao AS DATE) >= '{data_inicio}'
                  AND CAST(mb.data_movimentacao AS DATE) <= '{data_fim}'
                  AND ABS(mb.valor_movimentacao - {valor_esperado}) <= {tolerancia_valor}
                  AND ({where_descricao})
                  -- Não classificado
                  AND NOT EXISTS (
                      SELECT 1
                      FROM dbo.LANCAMENTO_TIPO_DESPESA ltd2
                      WHERE ltd2.id_movimentacao_bancaria = mb.id_movimentacao
                  )
                ORDER BY 
                    ABS(mb.valor_movimentacao - {valor_esperado}) ASC,  -- Valor mais próximo primeiro
                    ABS(DATEDIFF(day, CAST(mb.data_movimentacao AS DATE), '{data_desembaraco.strftime("%Y-%m-%d")}')) ASC  -- Data mais próxima primeiro
            """
            
            resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
            
            if not resultado.get('success'):
                logger.error(f"❌ Erro ao buscar lançamentos compatíveis: {resultado.get('error')}")
                return []
            
            rows = resultado.get('data', [])
            matches = []
            
            for row in rows:
                if isinstance(row, dict):
                    valor_lanc = float(row.get('valor_movimentacao', 0))
                    data_lanc_str = str(row.get('data_movimentacao', ''))[:10]
                    
                    # Calcular score de confiança (0-100)
                    score = self._calcular_score_confianca(
                        valor_esperado=valor_esperado,
                        valor_encontrado=valor_lanc,
                        data_esperada=data_desembaraco,
                        data_encontrada=data_lanc_str
                    )
                    
                    matches.append({
                        'id_movimentacao': row.get('id_movimentacao'),
                        'banco': row.get('banco_origem', ''),
                        'agencia': row.get('agencia_origem', ''),
                        'conta': row.get('conta_origem', ''),
                        'data_movimentacao': data_lanc_str,
                        'valor_movimentacao': valor_lanc,
                        'descricao': row.get('descricao_movimentacao', ''),
                        'score_confianca': score
                    })
            
            return matches
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar lançamentos compatíveis: {e}", exc_info=True)
            return []
    
    def _calcular_score_confianca(
        self,
        valor_esperado: float,
        valor_encontrado: float,
        data_esperada: datetime,
        data_encontrada: str
    ) -> int:
        """
        Calcula score de confiança (0-100) baseado em valor e data.
        
        Score:
        - Valor exato: 50 pontos
        - Data exata: 50 pontos
        - Valor próximo (±R$ 0,10): 40 pontos
        - Data próxima (±1 dia): 40 pontos
        - Data próxima (±2 dias): 30 pontos
        """
        score = 0
        
        # Score por valor (máx 50 pontos)
        diferenca_valor = abs(valor_esperado - valor_encontrado)
        if diferenca_valor < 0.01:  # Exato
            score += 50
        elif diferenca_valor <= 0.10:  # Próximo
            score += 40
        elif diferenca_valor <= 1.00:  # Aceitável
            score += 30
        else:
            score += max(0, 30 - int(diferenca_valor))
        
        # Score por data (máx 50 pontos)
        try:
            data_encontrada_dt = datetime.strptime(data_encontrada[:10], '%Y-%m-%d')
            diferenca_dias = abs((data_esperada.date() - data_encontrada_dt.date()).days)
            
            if diferenca_dias == 0:  # Exato
                score += 50
            elif diferenca_dias == 1:  # ±1 dia
                score += 40
            elif diferenca_dias == 2:  # ±2 dias
                score += 30
            else:
                score += max(0, 30 - (diferenca_dias * 5))
        except:
            pass
        
        return min(100, max(0, score))
    
    # ============================================
    # ✅ Novos helpers: status de conciliação por processo
    # ============================================
    
    def _garantir_tabela_status(self) -> None:
        """
        Garante que a tabela de status de conciliação por processo exista no SQLite.
        
        Estrutura:
        - processo_referencia: TEXT (PK)
        - status: TEXT ('NAO_ANALISADO', 'CONCILIADO_BANCO_MAIKE', 'PAGO_DIRETO_CLIENTE')
        - atualizado_em: TIMESTAMP
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processo_conciliacao_status (
                    processo_referencia TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            # Não quebrar fluxo de sugestão se o SQLite estiver indisponível
            logger.warning(f"⚠️ Não foi possível garantir tabela processo_conciliacao_status: {e}", exc_info=True)
    
    def _obter_status_sqlite(self, processo_referencia: str) -> Optional[str]:
        """Obtém status de conciliação do processo a partir do SQLite (se existir)."""
        try:
            self._garantir_tabela_status()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status
                FROM processo_conciliacao_status
                WHERE processo_referencia = ?
                LIMIT 1
            """, (processo_referencia,))
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return str(row[0])
            return None
        except Exception as e:
            logger.warning(f"⚠️ Erro ao ler status de conciliação no SQLite para {processo_referencia}: {e}", exc_info=True)
            return None
    
    def _salvar_status_sqlite(self, processo_referencia: str, status: str) -> None:
        """Salva/atualiza status de conciliação do processo no SQLite."""
        try:
            self._garantir_tabela_status()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processo_conciliacao_status (processo_referencia, status, atualizado_em)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(processo_referencia) DO UPDATE SET
                    status = excluded.status,
                    atualizado_em = excluded.atualizado_em
            """, (processo_referencia, status))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao salvar status de conciliação no SQLite para {processo_referencia}: {e}", exc_info=True)
    
    def _processo_conciliado_no_banco(self, processo_referencia: str) -> bool:
        """
        Verifica no SQL Server se o processo já possui conciliação de impostos de importação.
        
        Critérios:
        - Existe pelo menos um registro em LANCAMENTO_TIPO_DESPESA para o processo
        - E (origem_classificacao = 'IMPOSTOS_IMPORTACAO' OU nome_despesa = 'Impostos de Importação')
        """
        if not self.sql_adapter or not processo_referencia:
            return False
        
        try:
            proc = processo_referencia.strip()
            if not proc:
                return False
            
            proc_upper = proc.upper()
            proc_escaped = proc.replace("'", "''")
            
            query = f"""
                SELECT TOP 1 1 as tem
                FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
                JOIN dbo.TIPO_DESPESA td ON td.id_tipo_despesa = ltd.id_tipo_despesa
                WHERE 
                    (
                        UPPER(LTRIM(RTRIM(ltd.processo_referencia))) = '{proc_upper}'
                        OR LTRIM(RTRIM(ltd.processo_referencia)) = '{proc_escaped}'
                        OR ltd.processo_referencia = '{proc_escaped}'
                    )
                    AND (
                        ltd.origem_classificacao = 'IMPOSTOS_IMPORTACAO'
                        OR td.nome_despesa = 'Impostos de Importação'
                    )
            """
            resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
            if not resultado.get('success') or not resultado.get('data'):
                return False
            rows = resultado.get('data', [])
            return bool(rows)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao verificar conciliação de impostos no banco para {processo_referencia}: {e}", exc_info=True)
            return False
    
    def _obter_status_conciliacao_processo(self, processo_referencia: str) -> str:
        """
        Obtém o status de conciliação de um processo:
        - PAGO_DIRETO_CLIENTE: marcado manualmente como pago direto na conta do cliente
        - CONCILIADO_BANCO_MAIKE: já possui conciliação de impostos no SQL Server
        - NAO_ANALISADO: padrão (pode receber sugestões)
        """
        proc = (processo_referencia or "").strip()
        if not proc:
            return self.STATUS_NAO_ANALISADO
        
        # 1. Verificar status salvo em SQLite (manual/override)
        status_sqlite = self._obter_status_sqlite(proc)
        if status_sqlite == self.STATUS_PAGO_DIRETO_CLIENTE:
            return self.STATUS_PAGO_DIRETO_CLIENTE
        if status_sqlite == self.STATUS_CONCILIADO_BANCO:
            return self.STATUS_CONCILIADO_BANCO
        
        # 2. Verificar no SQL Server se já há conciliação de impostos
        if self._processo_conciliado_no_banco(proc):
            # Opcional: cachear no SQLite
            self._salvar_status_sqlite(proc, self.STATUS_CONCILIADO_BANCO)
            return self.STATUS_CONCILIADO_BANCO
        
        # 3. Caso contrário, considerar como não analisado (pode sugerir)
        return self.STATUS_NAO_ANALISADO
    
    # Métodos públicos para uso futuro (endpoints/chat) -----------------------
    
    def marcar_processo_pago_direto(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Marca um processo como "PAGO_DIRETO_CLIENTE", evitando sugestões de conciliação bancária.
        """
        proc = (processo_referencia or "").strip()
        if not proc:
            return {
                'sucesso': False,
                'erro': 'PROCESSO_INVALIDO',
                'mensagem': 'processo_referencia é obrigatório para marcar como pago direto.'
            }
        self._salvar_status_sqlite(proc, self.STATUS_PAGO_DIRETO_CLIENTE)
        logger.info(f"✅ Processo {proc} marcado como PAGO_DIRETO_CLIENTE (sem conciliação bancária esperada).")
        return {
            'sucesso': True,
            'status': self.STATUS_PAGO_DIRETO_CLIENTE,
            'processo_referencia': proc,
            'mensagem': f'Processo {proc} marcado como pago direto na conta do cliente.'
        }
    
    def marcar_processo_conciliado_banco(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Marca explicitamente um processo como já conciliado no banco.
        Útil após aplicar sugestão automática ou conciliação manual confirmada.
        """
        proc = (processo_referencia or "").strip()
        if not proc:
            return {
                'sucesso': False,
                'erro': 'PROCESSO_INVALIDO',
                'mensagem': 'processo_referencia é obrigatório para marcar como conciliado.'
            }
        self._salvar_status_sqlite(proc, self.STATUS_CONCILIADO_BANCO)
        logger.info(f"✅ Processo {proc} marcado como CONCILIADO_BANCO_MAIKE (impostos de importação).")
        return {
            'sucesso': True,
            'status': self.STATUS_CONCILIADO_BANCO,
            'processo_referencia': proc,
            'mensagem': f'Processo {proc} marcado como conciliado com o banco (impostos de importação).'
        }
    
    def _buscar_sugestao_pendente(self, processo_referencia: str) -> Optional[Dict[str, Any]]:
        """Busca sugestão pendente para um processo."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, processo_referencia, status, criado_em
                FROM sugestoes_vinculacao_bancaria
                WHERE processo_referencia = ?
                  AND status = 'pendente'
                ORDER BY criado_em DESC
                LIMIT 1
            """, (processo_referencia,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'processo_referencia': row[1],
                    'status': row[2],
                    'criado_em': row[3]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar sugestão pendente: {e}", exc_info=True)
            return None
    
    def _criar_sugestao(
        self,
        processo_referencia: str,
        tipo_documento: str,
        numero_documento: Optional[str],
        data_desembaraco: datetime,
        total_impostos: Decimal,
        id_movimentacao: int,
        score_confianca: int,
        observacoes: Optional[str] = None
    ) -> int:
        """Cria sugestão no banco de dados."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sugestoes_vinculacao_bancaria (
                    processo_referencia,
                    tipo_documento,
                    numero_documento,
                    data_desembaraco,
                    total_impostos,
                    id_movimentacao_sugerida,
                    score_confianca,
                    status,
                    observacoes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pendente', ?)
            """, (
                processo_referencia,
                tipo_documento,
                numero_documento,
                data_desembaraco.strftime('%Y-%m-%d'),
                float(total_impostos),
                id_movimentacao,
                score_confianca,
                observacoes
            ))
            
            sugestao_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return sugestao_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar sugestão: {e}", exc_info=True)
            raise
    
    def extrair_total_impostos_processo(self, processo_consolidado: Dict[str, Any], tipo_documento: str = 'DI') -> Optional[Decimal]:
        """
        Extrai o total de impostos (II + IPI + PIS + COFINS + TAXA_UTILIZACAO) do processo consolidado.
        
        Args:
            processo_consolidado: Dados completos do processo
            tipo_documento: 'DI' ou 'DUIMP'
        
        Returns:
            Total de impostos ou None se não encontrado
        """
        try:
            total = Decimal('0.0')
            
            # Buscar pagamentos da DI ou DUIMP
            if tipo_documento == 'DI':
                di_data = processo_consolidado.get('di')
                if not di_data:
                    return None
                
                pagamentos = di_data.get('pagamentos', [])
            else:  # DUIMP
                duimp_data = processo_consolidado.get('duimp')
                if not duimp_data:
                    return None
                
                pagamentos = duimp_data.get('pagamentos', [])
                
                # Fallback: tentar tributos calculados
                if not pagamentos:
                    tributos = duimp_data.get('tributos') or duimp_data.get('valoresCalculados', {})
                    if isinstance(tributos, dict):
                        tribs_calc = tributos.get('tributosCalculados', [])
                        if tribs_calc:
                            for t in tribs_calc:
                                if isinstance(t, dict):
                                    valores_brl = t.get('valoresBRL', {}) or {}
                                    valor = (
                                        valores_brl.get('aRecolher')
                                        or t.get('valorRecolhido')
                                        or t.get('valor')
                                        or 0
                                    )
                                    try:
                                        total += Decimal(str(float(valor) if valor else 0))
                                    except:
                                        pass
                            if total > 0:
                                return total
            
            # Somar valores dos pagamentos
            if pagamentos and isinstance(pagamentos, list):
                for pagamento in pagamentos:
                    if isinstance(pagamento, dict):
                        tipo_imposto = str(pagamento.get('tipo', '')).upper()
                        valor_pago = pagamento.get('valor', 0) or pagamento.get('valor_pago', 0) or 0
                        
                        # Incluir apenas impostos relevantes (II, IPI, PIS, COFINS, TAXA_UTILIZACAO)
                        if tipo_imposto in ['II', 'IPI', 'PIS', 'COFINS', 'TAXA_UTILIZACAO', 'TAXA UTILIZACAO']:
                            try:
                                total += Decimal(str(float(valor_pago) if valor_pago else 0))
                            except:
                                pass
            
            return total if total > 0 else None
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair total de impostos: {e}", exc_info=True)
            return None
    
    def listar_sugestoes_pendentes(self, limite: int = 50) -> Dict[str, Any]:
        """
        Lista sugestões pendentes de vinculação.
        
        Returns:
            Dict com sucesso, total, sugestoes
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id,
                    processo_referencia,
                    tipo_documento,
                    numero_documento,
                    data_desembaraco,
                    total_impostos,
                    id_movimentacao_sugerida,
                    score_confianca,
                    criado_em,
                    observacoes
                FROM sugestoes_vinculacao_bancaria
                WHERE status = 'pendente'
                ORDER BY score_confianca DESC, criado_em DESC
                LIMIT ?
            """, (limite,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Buscar dados dos lançamentos do SQL Server
            sugestoes = []
            for row in rows:
                sugestao = {
                    'id': row[0],
                    'processo_referencia': row[1],
                    'tipo_documento': row[2],
                    'numero_documento': row[3],
                    'data_desembaraco': row[4],
                    'total_impostos': float(row[5]) if row[5] else 0,
                    'id_movimentacao_sugerida': row[6],
                    'score_confianca': row[7],
                    'criado_em': row[8],
                    'observacoes': row[9],
                    'lancamento': None
                }
                
                # Buscar dados do lançamento no SQL Server
                if row[6] and self.sql_adapter:
                    lancamento = self._buscar_lancamento_por_id(row[6])
                    if lancamento:
                        sugestao['lancamento'] = lancamento
                
                sugestoes.append(sugestao)
            
            return {
                'sucesso': True,
                'total': len(sugestoes),
                'sugestoes': sugestoes
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar sugestões: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'sugestoes': []
            }
    
    def _buscar_lancamento_por_id(self, id_movimentacao: int) -> Optional[Dict[str, Any]]:
        """Busca dados de um lançamento bancário por ID."""
        if not self.sql_adapter:
            return None
        
        try:
            query = f"""
                SELECT
                    id_movimentacao,
                    banco_origem,
                    agencia_origem,
                    conta_origem,
                    data_movimentacao,
                    valor_movimentacao,
                    sinal_movimentacao,
                    CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao
                FROM dbo.MOVIMENTACAO_BANCARIA
                WHERE id_movimentacao = {id_movimentacao}
            """
            
            resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
            
            if resultado.get('success') and resultado.get('data'):
                rows = resultado['data']
                if rows:
                    row = rows[0]
                    if isinstance(row, dict):
                        return {
                            'id_movimentacao': row.get('id_movimentacao'),
                            'banco_origem': row.get('banco_origem', ''),
                            'agencia_origem': row.get('agencia_origem', ''),
                            'conta_origem': row.get('conta_origem', ''),
                            'data_movimentacao': str(row.get('data_movimentacao', ''))[:10],
                            'valor_movimentacao': float(row.get('valor_movimentacao', 0)),
                            'sinal_movimentacao': row.get('sinal_movimentacao', 'D'),
                            'descricao_movimentacao': row.get('descricao_movimentacao', '')
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar lançamento {id_movimentacao}: {e}", exc_info=True)
            return None
