"""
Serviço de Sincronização de Extratos Bancários para SQL Server.

Este serviço é responsável por:
1. Importar lançamentos bancários da API do Banco do Brasil
2. Detectar e evitar duplicatas usando hash único
3. Vincular lançamentos a processos de importação
4. Manter histórico completo de movimentações

Baseado em: docs/INTEGRACAO_EXTRATOS_BANCARIOS.md
"""
import hashlib
import json
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BancoSincronizacaoService:
    """
    Serviço para sincronização de extratos bancários com SQL Server.
    
    Responsabilidades:
    - Gerar hash único para cada lançamento (detecção de duplicatas)
    - Importar lançamentos para tabela MOVIMENTACAO_BANCARIA
    - Detectar processos automaticamente pela descrição
    - Validar contrapartidas (compliance COAF)
    """
    
    def __init__(self):
        """Inicializa o serviço."""
        self.sql_adapter = None
        self.bb_service = None
        self.santander_service = None
        # Evita spam de logs quando SQL Server fica indisponível no meio da importação
        self._sql_server_down_logged = False
        self._inicializar_dependencias()

    @staticmethod
    def _is_sql_server_connection_error(error_msg: str) -> bool:
        """Heurística: detecta erros típicos de indisponibilidade/conexão do SQL Server."""
        em = (error_msg or "").lower()
        return any(
            s in em
            for s in (
                "failed to connect",
                "etimeout",
                "timeout",
                "econnrefused",
                "login timeout",
                "could not open a connection",
                "sql server não acessível",
                "sql server nao acessivel",
            )
        )

    def _log_sql_server_down_once(self, error_msg: str) -> None:
        if self._sql_server_down_logged:
            return
        self._sql_server_down_logged = True
        logger.warning(
            "⚠️ SQL Server indisponível durante sincronização do extrato. "
            "Interrompendo a importação para evitar timeouts repetidos. "
            f"Motivo: {error_msg}"
        )
    
    def _inicializar_dependencias(self):
        """Inicializa dependências (SQL Server adapter e serviços bancários)."""
        # SQL Server adapter
        try:
            from utils.sql_server_adapter import get_sql_adapter
            self.sql_adapter = get_sql_adapter()
            logger.debug("✅ SQL Server adapter inicializado")
        except Exception as e:
            logger.warning(f"⚠️ SQL Server adapter não disponível: {e}")
            self.sql_adapter = None
        
        # Banco do Brasil service
        try:
            from services.banco_brasil_service import BancoBrasilService
            self.bb_service = BancoBrasilService()
            if not self.bb_service.enabled:
                logger.warning("⚠️ BancoBrasilService não está habilitado")
                self.bb_service = None
            else:
                logger.debug("✅ BancoBrasilService inicializado")
        except Exception as e:
            logger.warning(f"⚠️ BancoBrasilService não disponível: {e}")
            self.bb_service = None
        
        # Santander service
        try:
            from services.santander_service import SantanderService
            self.santander_service = SantanderService()
            if not self.santander_service.enabled:
                logger.warning("⚠️ SantanderService não está habilitado")
                self.santander_service = None
            else:
                logger.debug("✅ SantanderService inicializado")
        except Exception as e:
            logger.warning(f"⚠️ SantanderService não disponível: {e}")
            self.santander_service = None

        # ✅ NOVO (24/01/2026): Serviço de consulta CPF/CNPJ para identificar contrapartidas
        try:
            from services.consulta_cpf_cnpj_service import ConsultaCpfCnpjService
            self.cpf_cnpj_service = ConsultaCpfCnpjService()
            logger.debug("✅ ConsultaCpfCnpjService inicializado")
        except Exception as e:
            logger.warning(f"⚠️ ConsultaCpfCnpjService não disponível: {e}")
            self.cpf_cnpj_service = None
    
    # =========================================================================
    # FUNÇÃO DE HASH - DETECÇÃO DE DUPLICATAS
    # =========================================================================
    
    def gerar_hash_lancamento(
        self,
        lancamento: Dict[str, Any],
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        banco: str = 'BB'
    ) -> str:
        """
        Gera hash único para um lançamento bancário.
        
        O hash é calculado a partir de campos que identificam unicamente um lançamento:
        - Banco + Agência + Conta (origem) - opcional para Santander
        - Data do lançamento
        - Valor
        - Tipo/Sinal (crédito ou débito)
        - Descrição (primeiros 100 caracteres)
        - ✅ CRÍTICO (23/01/2026): Identificador único do lançamento:
          * Banco do Brasil: numeroDocumento (ou numeroLote como fallback)
          * Santander: transactionId
        
        Isso garante que dois lançamentos com mesmo valor, mesma data e mesma descrição
        sejam tratados como diferentes se tiverem números de documento/ID diferentes.
        
        Args:
            lancamento: Dict com dados do lançamento (BB ou Santander)
            agencia: Número da agência (opcional para Santander)
            conta: Número da conta (opcional para Santander)
            banco: Código do banco ('BB' ou 'SANTANDER')
        
        Returns:
            Hash SHA-256 (64 caracteres hexadecimais)
        """
        if banco == 'SANTANDER':
            # Formato do Santander
            # ✅ CORREÇÃO: Incluir historicComplement no hash para evitar duplicatas incorretas
            transaction_name = str(lancamento.get('transactionName', '')).strip()
            historic_complement = str(lancamento.get('historicComplement', '')).strip()
            # Combinar transactionName + historicComplement (igual ao que é salvo no banco)
            descricao_completa = f"{transaction_name} - {historic_complement}".strip() if historic_complement else transaction_name
            
            # ✅ CORREÇÃO (23/01/2026): Incluir transactionId no hash para evitar duplicatas quando
            # dois lançamentos têm mesmo valor, mesma data e mesma descrição
            transaction_id = str(lancamento.get('transactionId', '')).strip()
            
            dados_hash = {
                'banco': banco,
                'agencia': str(agencia).strip() if agencia else '',
                'conta': str(conta).strip() if conta else '',
                'data_lancamento': str(lancamento.get('transactionDate', '')),  # Formato YYYY-MM-DD
                'valor': float(lancamento.get('amount', 0.0) or 0.0),
                'tipo': str(lancamento.get('creditDebitType', '')).strip(),  # 'CREDITO' ou 'DEBITO'
                'nome': transaction_name,
                # ✅ Usar descrição completa (transactionName + historicComplement) nos primeiros 100 caracteres
                'descricao': descricao_completa[:100].strip(),
                # ✅ CRÍTICO: transactionId é único por transação - garante que lançamentos diferentes
                # com mesmo valor/data/descrição não sejam tratados como duplicados
                'transaction_id': transaction_id if transaction_id else ''
            }
        else:
            # Formato do Banco do Brasil
            # ✅ CORREÇÃO (23/01/2026): Incluir numeroDocumento no hash para evitar duplicatas quando
            # dois lançamentos têm mesmo valor, mesma data e mesma descrição
            numero_documento = str(lancamento.get('numeroDocumento', '')).strip()
            if not numero_documento:
                # Fallback: tentar numeroLote se numeroDocumento não existir
                numero_documento = str(lancamento.get('numeroLote', '')).strip()
            
            dados_hash = {
                'banco': banco,
                'agencia': str(agencia).strip(),
                'conta': str(conta).strip(),
                'data_lancamento': lancamento.get('dataLancamento', 0),  # Formato DDMMAAAA
                'valor': float(lancamento.get('valorLancamento', 0.0)),
                'tipo': str(lancamento.get('tipoLancamento', '')).strip(),
                'indicador': str(lancamento.get('indicadorSinalLancamento', '')).strip(),  # 'C' ou 'D'
                # Usar primeiros 100 caracteres da descrição
                'descricao': str(lancamento.get('textoDescricaoHistorico', ''))[:100].strip(),
                # ✅ CRÍTICO: numeroDocumento é único por lançamento - garante que lançamentos diferentes
                # com mesmo valor/data/descrição não sejam tratados como duplicados
                'numero_documento': numero_documento if numero_documento else ''
            }
        
        # Serializar de forma determinística (sempre mesma ordem)
        dados_json = json.dumps(dados_hash, sort_keys=True, ensure_ascii=False)
        
        # Calcular SHA-256
        hash_obj = hashlib.sha256(dados_json.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        logger.debug(f"🔑 Hash gerado: {hash_hex[:16]}... para lançamento de {dados_hash.get('data_lancamento', 'N/A')}")
        
        return hash_hex
    
    # =========================================================================
    # CONVERSÃO DE DADOS
    # =========================================================================
    
    def _converter_data_bb(self, data_int: int) -> Optional[datetime]:
        """
        Converte data do BB (DDMMAAAA) para datetime.
        
        Args:
            data_int: Data no formato DDMMAAAA (ex: 7012026 = 07/01/2026)
        
        Returns:
            datetime ou None se inválido
        """
        if not data_int or data_int == 0:
            return None
        
        try:
            data_str = str(data_int).zfill(8)  # Garantir 8 dígitos
            dia = int(data_str[0:2])
            mes = int(data_str[2:4])
            ano = int(data_str[4:8])
            return datetime(ano, mes, dia)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao converter data {data_int}: {e}")
            return None
    
    def _converter_data_santander(self, data_str: str) -> Optional[datetime]:
        """
        Converte data do Santander para datetime.
        
        ✅ USA A MESMA LÓGICA DO EXTRATO: A API retorna transactionDate diretamente.
        O extrato exibe sem conversão, então devemos usar o valor exato da API.
        
        Aceita múltiplos formatos (na ordem de prioridade):
        - DD/MM/YYYY (ex: "08/01/2026") - formato exibido no chat/extrato
        - YYYY-MM-DD (ex: "2026-01-08") - formato ISO padrão de APIs
        - DD-MM-YYYY (ex: "08-01-2026")
        
        Args:
            data_str: Data em qualquer formato suportado
        
        Returns:
            datetime ou None se inválido
        """
        if not data_str:
            return None
        
        # Limpar espaços
        data_str = str(data_str).strip()
        
        # ✅ PRIORIDADE 1: DD/MM/YYYY (formato exibido no chat/extrato)
        # Este é o formato que aparece no chat quando funciona corretamente
        try:
            if len(data_str) >= 10:
                return datetime.strptime(data_str[:10], '%d/%m/%Y')
        except ValueError:
            pass
        
        # ✅ PRIORIDADE 2: YYYY-MM-DD (formato ISO padrão de APIs REST)
        try:
            if len(data_str) >= 10:
                return datetime.strptime(data_str[:10], '%Y-%m-%d')
        except ValueError:
            pass
        
        # ✅ PRIORIDADE 3: DD-MM-YYYY
        try:
            if len(data_str) >= 10:
                return datetime.strptime(data_str[:10], '%d-%m-%Y')
        except ValueError:
            pass
        
        # Se nenhum formato funcionou, logar erro com detalhes
        logger.warning(f"⚠️ Erro ao converter data Santander '{data_str}' (tipo: {type(data_str)}, len: {len(data_str) if data_str else 0}): formato não reconhecido")
        return None
    
    def _formatar_data_sql(self, dt: Optional[datetime]) -> Optional[str]:
        """
        Formata datetime para SQL Server (YYYY-MM-DD HH:MM:SS).
        
        ✅ CORREÇÃO: Para datas do Santander, usar apenas a parte da data (sem hora)
        para evitar problemas de timezone que podem fazer a data retroceder um dia.
        
        Args:
            dt: datetime ou None
        
        Returns:
            String formatada ou None
        """
        if dt is None:
            return None
        # ✅ CORREÇÃO CRÍTICA: Usar apenas a data (sem hora) para evitar problemas de timezone
        # Isso garante que "08/01/2026" seja salvo como "2026-01-08 00:00:00" e não seja
        # convertido para UTC e depois para timezone local, causando perda de um dia
        return dt.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    
    # =========================================================================
    # DETECÇÃO DE PROCESSO POR DESCRIÇÃO
    # =========================================================================
    
    def detectar_processo_por_descricao(self, descricao: str) -> Optional[str]:
        """
        Detecta referência de processo na descrição do lançamento.
        
        Padrões reconhecidos:
        - "PAG FRETE DMD 0083/25" → DMD.0083/25
        - "IMPOSTOS ALH.0168/25" → ALH.0168/25
        - "VDM.0004/25" → VDM.0004/25
        - "BND0093" → BND.0093/25 (ano atual)
        
        Args:
            descricao: Texto da descrição do lançamento
        
        Returns:
            Referência do processo (ex: "DMD.0083/25") ou None
        """
        if not descricao:
            return None
        
        descricao_upper = descricao.upper()
        
        # Padrão 1: Formato completo (ex: DMD.0083/25 ou DMD 0083/25)
        # 2-4 letras + ponto ou espaço + 4 dígitos + barra + 2 dígitos
        match_completo = re.search(r'\b([A-Z]{2,4})[\.\s]?(\d{4})/(\d{2})\b', descricao_upper)
        if match_completo:
            categoria = match_completo.group(1)
            numero = match_completo.group(2)
            ano = match_completo.group(3)
            processo = f"{categoria}.{numero}/{ano}"
            logger.debug(f"🔍 Processo detectado (completo): {processo}")
            return processo
        
        # Padrão 2: Formato parcial sem ano (ex: DMD.0083 ou DMD 0083)
        match_parcial = re.search(r'\b([A-Z]{2,4})[\.\s]?(\d{4})\b', descricao_upper)
        if match_parcial:
            categoria = match_parcial.group(1)
            numero = match_parcial.group(2)
            # Usar ano atual
            ano_atual = datetime.now().strftime('%y')
            processo = f"{categoria}.{numero}/{ano_atual}"
            logger.debug(f"🔍 Processo detectado (parcial): {processo}")
            return processo
        
        # Padrão 3: Formato sem separador (ex: DMD0083)
        match_junto = re.search(r'\b([A-Z]{2,4})(\d{4})\b', descricao_upper)
        if match_junto:
            categoria = match_junto.group(1)
            numero = match_junto.group(2)
            ano_atual = datetime.now().strftime('%y')
            processo = f"{categoria}.{numero}/{ano_atual}"
            logger.debug(f"🔍 Processo detectado (junto): {processo}")
            return processo
        
        return None

    def extrair_cnpj_por_descricao(self, descricao: str) -> Optional[str]:
        """
        Extrai CNPJ ou CPF da descrição do lançamento (ex: PIX/TED).
        
        Muitas vezes o banco coloca o CNPJ do depositante na descrição ou no complemento.
        """
        if not descricao:
            return None
        # Padrão para CNPJ (14 dígitos) ou CPF (11 dígitos) numéricos puros
        match = re.search(r'\b(\d{11}|\d{14})\b', descricao)
        return match.group(1) if match else None
    
    # =========================================================================
    # VERIFICAÇÃO DE DUPLICATAS
    # =========================================================================
    
    def verificar_duplicata(self, hash_lancamento: str) -> bool:
        """
        Verifica se um lançamento já existe no banco de dados.
        
        Args:
            hash_lancamento: Hash SHA-256 do lançamento
        
        Returns:
            True se já existe (duplicata), False se não existe
        """
        if not self.sql_adapter:
            logger.warning("⚠️ SQL Server não disponível para verificar duplicata")
            return False
        
        try:
            # ✅ CORREÇÃO: Usar parâmetro nomeado (escapado) para evitar SQL injection
            # SQL Server via Node.js pode ter problemas com ?, usar concatenação segura
            query = """
                SELECT id_movimentacao 
                FROM dbo.MOVIMENTACAO_BANCARIA 
                WHERE hash_dados = @hash
            """
            
            # ✅ CORREÇÃO: Passar database e params corretamente
            # Tentar usar params primeiro (funciona com pyodbc), se falhar usar concatenação
            resultado = self.sql_adapter.execute_query(
                query.replace('@hash', f"'{hash_lancamento}'"),  # Escape simples mas seguro para hash (sempre hex)
                database=self.sql_adapter.database
            )
            
            # ✅ CORREÇÃO: Verificar resultado corretamente (é um dict, não lista)
            if resultado.get('success') and resultado.get('data'):
                rows = resultado['data']
                if len(rows) > 0:
                    logger.debug(f"⏭️ Duplicata detectada (hash: {hash_lancamento[:16]}...)")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar duplicata: {e}", exc_info=True)
            return False
    
    def verificar_duplicata_com_data(self, hash_lancamento: str, data_lanc: Optional[datetime], banco: str) -> Dict[str, Any]:
        """
        Verifica se um lançamento já existe no banco e se a data precisa ser atualizada.
        
        Args:
            hash_lancamento: Hash SHA-256 do lançamento
            data_lanc: Data do lançamento (datetime)
            banco: Código do banco ('BB' ou 'SANTANDER')
        
        Returns:
            Dict com:
            - existe: bool (se já existe)
            - data_diferente: bool (se a data no banco é diferente)
            - id_movimentacao: int (ID do lançamento se existir)
            - data_antiga: str (data atual no banco se diferente)
        """
        if not self.sql_adapter or not data_lanc:
            return {'existe': False, 'data_diferente': False}
        
        try:
            # Buscar lançamento pelo hash
            query = f"""
                SELECT 
                    id_movimentacao,
                    CAST(data_movimentacao AS DATE) as data_movimentacao_date
                FROM dbo.MOVIMENTACAO_BANCARIA 
                WHERE hash_dados = '{hash_lancamento}'
            """
            
            resultado = self.sql_adapter.execute_query(
                query,
                database=self.sql_adapter.database
            )
            
            if resultado.get('success') and resultado.get('data'):
                rows = resultado['data']
                if rows:
                    row = rows[0]
                    if isinstance(row, dict):
                        id_mov = row.get('id_movimentacao')
                        data_banco_str = str(row.get('data_movimentacao_date', ''))
                    else:
                        id_mov = row[0] if len(row) > 0 else None
                        data_banco_str = str(row[1]) if len(row) > 1 else ''
                    
                    if id_mov:
                        # Comparar datas (apenas a parte da data, sem hora)
                        data_lanc_str = data_lanc.strftime('%Y-%m-%d')
                        data_banco_clean = data_banco_str[:10] if len(data_banco_str) >= 10 else data_banco_str
                        
                        if data_lanc_str != data_banco_clean:
                            logger.info(f"🔄 Data diferente detectada: banco={data_banco_clean}, nova={data_lanc_str}")
                            return {
                                'existe': True,
                                'data_diferente': True,
                                'id_movimentacao': id_mov,
                                'data_antiga': data_banco_clean
                            }
                        else:
                            return {
                                'existe': True,
                                'data_diferente': False,
                                'id_movimentacao': id_mov
                            }
            
            return {'existe': False, 'data_diferente': False}
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar duplicata com data: {e}", exc_info=True)
            return {'existe': False, 'data_diferente': False}
    
    def _verificar_duplicata_por_valor_descricao(self, lancamento: Dict[str, Any], data_lanc: datetime, agencia: Optional[str], conta: Optional[str]) -> Dict[str, Any]:
        """
        Verifica duplicata por valor + descrição + data próxima (útil quando hash mudou).
        
        Usado quando o hash não encontra porque a descrição mudou (ex: historicComplement foi adicionado).
        """
        if not self.sql_adapter or not data_lanc:
            return {'existe': False, 'data_diferente': False}
        
        try:
            # Extrair dados do lançamento
            valor = float(lancamento.get('amount', 0.0) or 0.0)
            transaction_name = str(lancamento.get('transactionName', '')).strip()
            historic_complement = str(lancamento.get('historicComplement', '')).strip()
            descricao_completa = f"{transaction_name} - {historic_complement}".strip() if historic_complement else transaction_name
            sinal = 'C' if str(lancamento.get('creditDebitType', '')).strip() == 'CREDITO' else 'D'
            
            # Buscar por valor + descrição parcial + data próxima (07 ou 08 de janeiro)
            # Isso encontra lançamentos salvos com data errada
            agencia_escaped = (agencia or "").replace("'", "''")
            conta_escaped = (conta or "").replace("'", "''")
            transaction_name_escaped = transaction_name.replace("'", "''")
            descricao_completa_escaped = descricao_completa.replace("'", "''")
            
            query = f"""
                SELECT TOP 1
                    id_movimentacao,
                    CAST(data_movimentacao AS DATE) as data_movimentacao_date,
                    CAST(descricao_movimentacao AS VARCHAR(MAX)) as descricao_movimentacao
                FROM dbo.MOVIMENTACAO_BANCARIA 
                WHERE banco_origem = 'SANTANDER'
                  AND agencia_origem = '{agencia_escaped}'
                  AND conta_origem = '{conta_escaped}'
                  AND ABS(valor_movimentacao - {valor}) < 0.01
                  AND sinal_movimentacao = '{sinal}'
                  AND (
                      CAST(descricao_movimentacao AS VARCHAR(MAX)) LIKE '%{transaction_name_escaped}%'
                      OR CAST(descricao_movimentacao AS VARCHAR(MAX)) = '{descricao_completa_escaped}'
                  )
                  AND CAST(data_movimentacao AS DATE) IN ('2026-01-07', '2026-01-08')
                ORDER BY id_movimentacao DESC
            """
            
            resultado = self.sql_adapter.execute_query(query, database=self.sql_adapter.database)
            
            if resultado.get('success') and resultado.get('data'):
                rows = resultado['data']
                if rows:
                    row = rows[0]
                    if isinstance(row, dict):
                        id_mov = row.get('id_movimentacao')
                        data_banco_str = str(row.get('data_movimentacao_date', ''))
                    else:
                        id_mov = row[0] if len(row) > 0 else None
                        data_banco_str = str(row[1]) if len(row) > 1 else ''
                    
                    if id_mov:
                        data_lanc_str = data_lanc.strftime('%Y-%m-%d')
                        data_banco_clean = data_banco_str[:10] if len(data_banco_str) >= 10 else data_banco_str
                        
                        if data_lanc_str != data_banco_clean:
                            logger.info(f"🔄 [VALOR+DESC] Data diferente detectada: banco={data_banco_clean}, nova={data_lanc_str} (ID: {id_mov})")
                            return {
                                'existe': True,
                                'data_diferente': True,
                                'id_movimentacao': id_mov,
                                'data_antiga': data_banco_clean
                            }
                        else:
                            return {
                                'existe': True,
                                'data_diferente': False,
                                'id_movimentacao': id_mov
                            }
            
            return {'existe': False, 'data_diferente': False}
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar duplicata por valor+descrição: {e}", exc_info=True)
            return {'existe': False, 'data_diferente': False}
    
    # =========================================================================
    # IMPORTAÇÃO DE LANÇAMENTOS
    # =========================================================================
    
    def importar_lancamento(
        self,
        lancamento: Dict[str, Any],
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        banco: str = 'BB'
    ) -> Dict[str, Any]:
        """
        Importa um único lançamento para o SQL Server.
        
        Args:
            lancamento: Dict com dados do lançamento (BB ou Santander)
            agencia: Número da agência (opcional para Santander)
            conta: Número da conta (opcional para Santander)
            banco: Código do banco ('BB' ou 'SANTANDER')
        
        Returns:
            Dict com resultado:
            - sucesso: bool
            - acao: 'inserido' | 'duplicado' | 'erro'
            - id_movimentacao: int (se inserido)
            - hash: str
            - erro: str (se houver)
        """
        if not self.sql_adapter:
            return {
                'sucesso': False,
                'acao': 'erro',
                'erro': 'SQL Server não disponível'
            }
        
        try:
            # 1. Gerar hash do lançamento
            hash_lanc = self.gerar_hash_lancamento(lancamento, agencia, conta, banco)
            
            # 2. Extrair e converter data ANTES de verificar duplicata (para poder atualizar data se necessário)
            data_lanc = None
            if banco == 'SANTANDER':
                transaction_date_raw = lancamento.get('transactionDate', '')
                data_lanc = self._converter_data_santander(transaction_date_raw)
                if data_lanc:
                    data_lanc = data_lanc.replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # BB
                data_lancamento_bb = lancamento.get('dataLancamento', '')
                if data_lancamento_bb:
                    try:
                        data_lanc = self._converter_data_bb(data_lancamento_bb)
                        if data_lanc:
                            data_lanc = data_lanc.replace(hour=0, minute=0, second=0, microsecond=0)
                    except:
                        pass
            
            # 3. Verificar se já existe (duplicata) e se a data precisa ser atualizada
            duplicata_info = {'existe': False, 'data_diferente': False}
            if data_lanc:
                # ✅ Tentar primeiro pelo hash (mais preciso)
                duplicata_info = self.verificar_duplicata_com_data(hash_lanc, data_lanc, banco)
                
                # ✅ Se não encontrou pelo hash, tentar por valor + descrição + data próxima
                # Isso resolve o caso onde o hash mudou (ex: historicComplement foi adicionado)
                if not duplicata_info.get('existe') and banco == 'SANTANDER':
                    duplicata_info = self._verificar_duplicata_por_valor_descricao(lancamento, data_lanc, agencia, conta)
            
            if duplicata_info.get('existe'):
                # Se existe mas a data está diferente, atualizar
                if duplicata_info.get('data_diferente') and duplicata_info.get('id_movimentacao'):
                    logger.info(f"🔄 Atualizando data do lançamento {duplicata_info['id_movimentacao']} de {duplicata_info['data_antiga']} para {data_lanc.strftime('%Y-%m-%d')}")
                    data_str = self._formatar_data_sql(data_lanc)
                    query_update = f"""
                        UPDATE dbo.MOVIMENTACAO_BANCARIA
                        SET data_movimentacao = '{data_str}',
                            data_lancamento = '{data_str}'
                        WHERE id_movimentacao = {duplicata_info['id_movimentacao']}
                    """
                    resultado_update = self.sql_adapter.execute_query(
                        query_update,
                        database=self.sql_adapter.database
                    )
                    if resultado_update.get('success'):
                        logger.info(f"✅ Data atualizada com sucesso para lançamento {duplicata_info['id_movimentacao']}")
                    else:
                        logger.error(f"❌ Erro ao atualizar data: {resultado_update.get('error')}")
                
                return {
                    'sucesso': True,
                    'acao': 'duplicado',
                    'hash': hash_lanc,
                    'data_atualizada': duplicata_info.get('data_diferente', False)
                }
            
            # 4. Extrair dados do lançamento (formato específico por banco)
            if banco == 'SANTANDER':
                # Formato Santander
                transaction_date_raw = lancamento.get('transactionDate', '')
                
                # ✅ LOG DETALHADO: Capturar formato exato da API (igual ao extrato)
                # Log apenas para datas que contêm "08" para diagnosticar o problema
                if '08' in str(transaction_date_raw) or '2026-01-08' in str(transaction_date_raw):
                    logger.info(f"🔍 [DEBUG DATA] transactionDate raw da API: '{transaction_date_raw}' (tipo: {type(transaction_date_raw)}, repr: {repr(transaction_date_raw)})")
                
                # ✅ Data já foi convertida acima, apenas validar
                if data_lanc is None:
                    logger.error(f"❌ Não foi possível converter data do Santander: {transaction_date_raw}")
                else:
                    # ✅ DEBUG: Log da data convertida para verificar se está correta
                    # Log apenas para datas do dia 08/01/2026 para não poluir logs
                    if data_lanc.year == 2026 and data_lanc.month == 1 and data_lanc.day == 8:
                        logger.info(f"✅ [DIA 08 OK] Data convertida corretamente: {data_lanc.strftime('%Y-%m-%d')} (original da API: '{transaction_date_raw}')")
                    elif data_lanc.year == 2026 and data_lanc.month == 1 and data_lanc.day == 7:
                        # ⚠️ ALERTA: Verificar se a data original tinha 08
                        if '08' in str(transaction_date_raw) or '2026-01-08' in str(transaction_date_raw):
                            logger.error(f"❌ [ERRO DATA] Data original tinha 08 mas foi convertida para 07! Original: '{transaction_date_raw}', Convertida: {data_lanc.strftime('%Y-%m-%d')}")
                        else:
                            logger.debug(f"📅 Data convertida para 07/01/2026 (original: '{transaction_date_raw}')")
                valor = float(lancamento.get('amount', 0.0) or 0.0)
                credit_debit = str(lancamento.get('creditDebitType', '')).strip()
                sinal = 'C' if credit_debit == 'CREDITO' else 'D'
                
                # ✅ Combinar transactionName com historicComplement (igual ao formato do chat)
                transaction_name = str(lancamento.get('transactionName', '')).strip()
                historic_complement = str(lancamento.get('historicComplement', '')).strip()
                
                # Se houver complemento, combinar: "PIX ENVIADO - RIO BRASIL TERMINAL"
                if historic_complement:
                    descricao = f"{transaction_name} - {historic_complement}".strip()
                else:
                    descricao = transaction_name
                
                tipo = str(lancamento.get('transactionType', '')).strip()
                historico_codigo = str(lancamento.get('transactionId', '')).strip()
                info_complementar = historic_complement  # Manter também em info_complementar para referência
                
                # Contrapartida (Santander pode ter campos diferentes)
                cpf_cnpj_contra = None
                nome_contra = None
                if 'counterpartDocument' in lancamento:
                    cpf_cnpj_contra = str(lancamento.get('counterpartDocument', '')).strip()
                elif 'document' in lancamento:
                    cpf_cnpj_contra = str(lancamento.get('document', '')).strip()
                
                if 'counterpartName' in lancamento:
                    nome_contra = str(lancamento.get('counterpartName', '')).strip()
                elif 'name' in lancamento:
                    nome_contra = str(lancamento.get('name', '')).strip()

                if not cpf_cnpj_contra or cpf_cnpj_contra == '0':
                    cpf_cnpj_contra = None
                
                # ✅ NOVO (24/01/2026): Tentar buscar nome pelo CNPJ se não veio da API
                if cpf_cnpj_contra and not nome_contra and self.cpf_cnpj_service:
                    try:
                        res_cnpj = self.cpf_cnpj_service.consultar(cpf_cnpj_contra)
                        if res_cnpj and res_cnpj.get('nome'):
                            nome_contra = res_cnpj.get('nome')
                            logger.info(f"✅ Nome do cliente identificado via CNPJ: {nome_contra}")
                    except Exception as e_cnpj:
                        logger.warning(f"⚠️ Erro ao consultar nome via CNPJ: {e_cnpj}")

                tipo_pessoa_contra = None
                banco_contra = None
                if 'counterpartBank' in lancamento:
                    banco_contra = str(lancamento.get('counterpartBank', {}).get('code', '')).strip()
                agencia_contra = None
                conta_contra = None
                dv_conta_contra = None
                
                # Para Santander, agência e conta podem vir do statement_id ou ser None
                if not agencia:
                    agencia = str(lancamento.get('branchCode', '')).strip() or None
                if not conta:
                    conta = str(lancamento.get('number', '')).strip() or None
                
                fonte_dados = 'SANTANDER_API'
            else:
                # Formato Banco do Brasil
                data_lanc = self._converter_data_bb(lancamento.get('dataLancamento', 0))
                valor = float(lancamento.get('valorLancamento', 0.0))
                sinal = str(lancamento.get('indicadorSinalLancamento', 'C')).strip()
                if sinal not in ('C', 'D'):
                    sinal = 'C'  # Default para crédito
                
                descricao = str(lancamento.get('textoDescricaoHistorico', '')).strip()
                tipo = str(lancamento.get('tipoLancamento', '')).strip()
                historico_codigo = str(lancamento.get('codigoHistoricoBanco', '')).strip()
                info_complementar = str(lancamento.get('textoInformacaoComplementar', '')).strip()
                
                # Contrapartida
                cpf_cnpj_contra = str(lancamento.get('numeroCpfCnpjContrapartida', '')).strip()
                if cpf_cnpj_contra == '0':
                    cpf_cnpj_contra = None
                
                nome_contra = None
                # ✅ NOVO (24/01/2026): Tentar buscar nome pelo CNPJ (BB não traz nome no extrato)
                if cpf_cnpj_contra and self.cpf_cnpj_service:
                    try:
                        res_cnpj = self.cpf_cnpj_service.consultar(cpf_cnpj_contra)
                        if res_cnpj and res_cnpj.get('nome'):
                            nome_contra = res_cnpj.get('nome')
                            logger.info(f"✅ Nome do cliente identificado via CNPJ (BB): {nome_contra}")
                    except Exception as e_cnpj:
                        logger.warning(f"⚠️ Erro ao consultar nome via CNPJ: {e_cnpj}")

                tipo_pessoa_contra = str(lancamento.get('indicadorTipoPessoaContrapartida', '')).strip()
                banco_contra = str(lancamento.get('codigoBancoContrapartida', '')).strip()
                agencia_contra = str(lancamento.get('codigoAgenciaContrapartida', '')).strip()
                conta_contra = str(lancamento.get('numeroContaContrapartida', '')).strip()
                dv_conta_contra = str(lancamento.get('textoDvContaContrapartida', '')).strip()
                
                fonte_dados = 'BB_API'
            
            # Detectar processo automaticamente
            processo_ref = self.detectar_processo_por_descricao(descricao)
            if processo_ref:
                logger.info(f"🔗 Processo detectado automaticamente: {processo_ref}")
            
            # 4. Inserir no banco
            # ✅ CORREÇÃO: Construir query INSERT diretamente com valores escapados corretamente
            def _escapar_sql(valor):
                """Escapa valor para SQL de forma segura."""
                if valor is None:
                    return 'NULL'
                if isinstance(valor, str):
                    # Escapar aspas simples (SQL injection protection)
                    valor_esc = valor.replace("'", "''")
                    return f"'{valor_esc}'"
                if isinstance(valor, (int, float)):
                    return str(valor)
                # Para outros tipos, converter para string e escapar
                valor_str = str(valor)
                valor_esc = valor_str.replace("'", "''")
                return f"'{valor_esc}'"
            
            # Formatar data para SQL
            # ✅ CRÍTICO: data_movimentacao não pode ser NULL
            if data_lanc is None:
                logger.error(f"❌ Data inválida para lançamento: {descricao[:50]}... (valor: {lancamento.get('transactionDate') if banco == 'SANTANDER' else lancamento.get('dataLancamento')})")
                return {
                    'sucesso': False,
                    'acao': 'erro',
                    'erro': f'Data inválida ou não encontrada no lançamento'
                }
            
            data_str = self._formatar_data_sql(data_lanc)
            if not data_str:
                logger.error(f"❌ Erro ao formatar data para SQL: {data_lanc}")
                return {
                    'sucesso': False,
                    'acao': 'erro',
                    'erro': f'Erro ao formatar data para SQL'
                }
            
            # ✅ DEBUG: Log da data sendo salva (apenas para Santander, para debug)
            if banco == 'SANTANDER':
                logger.debug(f"📅 Data convertida para SQL: {data_str} (original: {transaction_date_raw if 'transaction_date_raw' in locals() else 'N/A'})")
            
            data_sql = f"'{data_str}'"
            
            # JSON dos dados originais (limitar tamanho se necessário)
            json_original = json.dumps(lancamento, ensure_ascii=False)
            # ✅ SQL Server NVARCHAR(MAX) suporta até 2GB, mas limitar para evitar problemas
            # Se muito grande, truncar (provavelmente não necessário, mas precaução)
            if len(json_original) > 1000000:  # 1MB
                logger.warning(f"⚠️ JSON muito grande ({len(json_original)} chars), truncando...")
                json_original = json_original[:1000000]
            
            query_insert = f"""
                INSERT INTO dbo.MOVIMENTACAO_BANCARIA (
                    banco_origem, agencia_origem, conta_origem,
                    data_movimentacao, data_lancamento,
                    tipo_movimentacao, sinal_movimentacao,
                    valor_movimentacao, moeda,
                    cpf_cnpj_contrapartida, nome_contrapartida, tipo_pessoa_contrapartida,
                    banco_contrapartida, agencia_contrapartida,
                    conta_contrapartida, dv_conta_contrapartida,
                    descricao_movimentacao, historico_codigo,
                    informacoes_complementares,
                    processo_referencia,
                    fonte_dados, hash_dados, json_dados_originais
                ) VALUES (
                    {_escapar_sql(banco)},
                    {_escapar_sql(agencia)},
                    {_escapar_sql(conta)},
                    {data_sql},
                    {data_sql},
                    {_escapar_sql(tipo)},
                    {_escapar_sql(sinal)},
                    {valor},
                    'BRL',
                    {_escapar_sql(cpf_cnpj_contra)},
                    {_escapar_sql(nome_contra)},
                    {_escapar_sql(tipo_pessoa_contra)},
                    {_escapar_sql(banco_contra)},
                    {_escapar_sql(agencia_contra)},
                    {_escapar_sql(conta_contra)},
                    {_escapar_sql(dv_conta_contra)},
                    {_escapar_sql(descricao)},
                    {_escapar_sql(historico_codigo)},
                    {_escapar_sql(info_complementar)},
                    {_escapar_sql(processo_ref)},
                    {_escapar_sql(fonte_dados)},
                    {_escapar_sql(hash_lanc)},
                    {_escapar_sql(json_original)}
                )
            """
            
            # ✅ CORREÇÃO: Usar execute_query() (método execute_non_query() não existe)
            # Log da query para debug (apenas primeiro INSERT para não poluir logs)
            if not hasattr(self, '_debug_logged_insert'):
                logger.debug(f"🔍 Primeira query INSERT (exemplo): {query_insert[:200]}...")
                self._debug_logged_insert = True
            
            resultado = self.sql_adapter.execute_query(
                query_insert,
                database=self.sql_adapter.database
            )
            
            if not resultado.get('success'):
                error_msg = resultado.get('error', 'Erro desconhecido')
                # ✅ CORREÇÃO (21/01/2026): Quando SQL Server está fora da rede (ETIMEOUT),
                # evitar spam (query + stacktrace) e deixar o loop abortar cedo.
                if self._is_sql_server_connection_error(error_msg):
                    self._log_sql_server_down_once(error_msg)
                    return {
                        'sucesso': False,
                        'acao': 'sql_server_indisponivel',
                        'erro': error_msg,
                        'erro_tipo': 'SQL_SERVER_INDISPONIVEL',
                    }

                logger.error(f"❌ Erro ao inserir lançamento no SQL Server: {error_msg}")
                logger.debug(f"🔍 Query INSERT (trecho): {query_insert[:300]}...")
                return {
                    'sucesso': False,
                    'acao': 'erro',
                    'erro': f"Erro ao inserir lançamento: {error_msg}",
                }
            
            logger.info(f"✅ Lançamento importado: {descricao[:50]}... (R$ {valor:.2f})")
            
            return {
                'sucesso': True,
                'acao': 'inserido',
                'hash': hash_lanc,
                'processo_detectado': processo_ref
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao importar lançamento: {e}", exc_info=True)
            return {
                'sucesso': False,
                'acao': 'erro',
                'erro': str(e)
            }
    
    def importar_lancamentos(
        self,
        lancamentos: List[Dict[str, Any]],
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        banco: str = 'BB'
    ) -> Dict[str, Any]:
        """
        Importa múltiplos lançamentos para o SQL Server.
        
        Args:
            lancamentos: Lista de lançamentos da API (BB ou Santander)
            agencia: Número da agência (opcional para Santander)
            conta: Número da conta (opcional para Santander)
            banco: Código do banco ('BB' ou 'SANTANDER')
        
        Returns:
            Dict com resultado:
            - sucesso: bool
            - total: int (total de lançamentos processados)
            - novos: int (lançamentos inseridos)
            - duplicados: int (lançamentos pulados)
            - erros: int (lançamentos com erro)
            - processos_detectados: List[str] (processos detectados automaticamente)
            - resposta: str (mensagem formatada)
        """
        if not lancamentos:
            return {
                'sucesso': True,
                'total': 0,
                'novos': 0,
                'duplicados': 0,
                'erros': 0,
                'processos_detectados': [],
                'resposta': '📋 Nenhum lançamento para importar.'
            }
        
        novos = 0
        duplicados = 0
        erros = 0
        processos_detectados = []
        sql_server_indisponivel = False
        erro_sql_server = None
        processados = 0
        
        logger.info(f"🔄 Iniciando importação de {len(lancamentos)} lançamentos...")
        
        for i, lanc in enumerate(lancamentos, 1):
            try:
                resultado = self.importar_lancamento(lanc, agencia, conta, banco)
                processados = i
                
                if resultado.get('acao') == 'inserido':
                    novos += 1
                    if resultado.get('processo_detectado'):
                        processos_detectados.append(resultado['processo_detectado'])
                elif resultado.get('acao') == 'duplicado':
                    duplicados += 1
                elif resultado.get('acao') == 'sql_server_indisponivel':
                    sql_server_indisponivel = True
                    erro_sql_server = resultado.get('erro')
                    erros += 1
                    logger.warning(f"⚠️ Abortando importação no item {i}/{len(lancamentos)} por indisponibilidade do SQL Server.")
                    break
                else:
                    erros += 1
                    # ✅ DEBUG: Logar erro detalhado para os primeiros 3 erros
                    if erros <= 3:
                        erro_msg = resultado.get('erro', 'Erro desconhecido')
                        logger.error(f"❌ Erro ao importar lançamento {i}/{len(lancamentos)}: {erro_msg}")
                        logger.debug(f"❌ Dados do lançamento: {str(lanc)[:200]}...")
            except Exception as e:
                erros += 1
                logger.error(f"❌ Exceção ao processar lançamento {i}/{len(lancamentos)}: {e}", exc_info=True)
            
            # Log de progresso a cada 10 lançamentos
            if i % 10 == 0:
                logger.info(f"📊 Progresso: {i}/{len(lancamentos)} ({novos} novos, {duplicados} duplicados, {erros} erros)")
        
        # Resumo final
        logger.info(f"✅ Importação concluída: {novos} novos, {duplicados} duplicados, {erros} erros")
        
        # Montar resposta formatada
        resposta = f"📊 **Importação de Extrato Bancário**\n\n"
        resposta += f"**Conta:** {banco} Ag. {agencia} C/C {conta}\n"
        if sql_server_indisponivel:
            resposta += f"**Total processado:** {processados}/{len(lancamentos)} lançamentos *(interrompido por SQL Server indisponível)*\n\n"
        else:
            resposta += f"**Total processado:** {len(lancamentos)} lançamentos\n\n"
        resposta += f"**Resultado:**\n"
        resposta += f"• ✅ Novos inseridos: {novos}\n"
        resposta += f"• ⏭️ Duplicados (pulados): {duplicados}\n"
        if erros > 0:
            resposta += f"• ❌ Erros: {erros}\n"

        if sql_server_indisponivel:
            resposta += (
                "\n⚠️ **SQL Server indisponível (timeout/conexão).**\n"
                "💡 Você provavelmente está fora da rede do escritório/VPN.\n"
                "✅ Pode sincronizar novamente quando o SQL Server estiver acessível — duplicatas são detectadas automaticamente pelo hash.\n"
            )
            if erro_sql_server:
                resposta += f"\nDetalhe: `{erro_sql_server}`\n"
        
        if processos_detectados:
            processos_unicos = list(set(processos_detectados))
            resposta += f"\n**Processos detectados automaticamente:** {len(processos_unicos)}\n"
            for proc in processos_unicos[:10]:  # Limitar a 10
                resposta += f"• {proc}\n"
            if len(processos_unicos) > 10:
                resposta += f"• ... e mais {len(processos_unicos) - 10}\n"
        
        return {
            'sucesso': not sql_server_indisponivel,
            'total': len(lancamentos),
            'processados': processados if sql_server_indisponivel else len(lancamentos),
            'novos': novos,
            'duplicados': duplicados,
            'erros': erros,
            'sql_server_indisponivel': sql_server_indisponivel,
            'processos_detectados': list(set(processos_detectados)),
            # Frontend do modal usa data.erro || data.mensagem || 'Erro desconhecido'
            # então garantimos mensagem/erro em falhas controladas.
            'mensagem': (
                "SQL Server indisponível (timeout/conexão). Conecte na VPN/rede do escritório e sincronize novamente. "
                "Duplicatas são detectadas automaticamente."
                if sql_server_indisponivel
                else None
            ),
            # Preferir erro amigável para UI; manter detalhe técnico separado
            'erro': ("SQL Server indisponível (timeout/conexão). Conecte na VPN/rede e tente novamente." if sql_server_indisponivel else None),
            'erro_tecnico': (erro_sql_server if sql_server_indisponivel else None),
            'resposta': resposta
        }
    
    # =========================================================================
    # SINCRONIZAÇÃO COMPLETA
    # =========================================================================
    
    def sincronizar_extrato(
        self,
        banco: str = 'BB',
        agencia: Optional[str] = None,
        conta: Optional[str] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        dias_retroativos: int = 7
    ) -> Dict[str, Any]:
        """
        Sincroniza extrato bancário completo (consulta API + importa para SQL Server).
        
        Args:
            banco: Código do banco ('BB' ou 'SANTANDER')
            agencia: Número da agência (obrigatório para BB, opcional para Santander)
            conta: Número da conta (obrigatório para BB, opcional para Santander)
            data_inicio: Data inicial (opcional)
            data_fim: Data final (opcional)
            dias_retroativos: Dias retroativos se datas não fornecidas (default: 7)
        
        Returns:
            Dict com resultado da sincronização
        """
        # Validar parâmetros por banco
        if banco == 'BB':
            if not agencia or not conta:
                return {
                    'sucesso': False,
                    'erro': 'PARAMETROS_FALTANDO',
                    'resposta': '❌ Para Banco do Brasil, "agencia" e "conta" são obrigatórios.'
                }
            if not self.bb_service:
                return {
                    'sucesso': False,
                    'erro': 'BancoBrasilService não disponível',
                    'resposta': '❌ Serviço do Banco do Brasil não está disponível.'
                }
        elif banco == 'SANTANDER':
            if not self.santander_service:
                return {
                    'sucesso': False,
                    'erro': 'SantanderService não disponível',
                    'resposta': '❌ Serviço do Santander não está disponível.'
                }
        else:
            return {
                'sucesso': False,
                'erro': 'BANCO_INVALIDO',
                'resposta': f'❌ Banco "{banco}" não suportado. Use "BB" ou "SANTANDER".'
            }
        
        if not self.sql_adapter:
            return {
                'sucesso': False,
                'erro': 'SQL Server não disponível',
                'resposta': '❌ SQL Server não está disponível para armazenar os dados.'
            }
        
        # Definir período se não fornecido
        if not data_inicio or not data_fim:
            hoje = datetime.now()
            # ✅ CORREÇÃO: Garantir que data_fim inclua todo o dia atual (até 23:59:59)
            # Isso evita que lançamentos do dia atual sejam perdidos
            data_fim = hoje.replace(hour=23, minute=59, second=59)
            data_inicio = (hoje - timedelta(days=dias_retroativos)).replace(hour=0, minute=0, second=0)
            logger.info(f"📅 Usando período padrão: {data_inicio.strftime('%d/%m/%Y %H:%M')} a {data_fim.strftime('%d/%m/%Y %H:%M')}")
        
        try:
            # 1. Consultar extrato da API
            if banco == 'BB':
                logger.info(f"🔄 Consultando extrato BB: Ag. {agencia} C/C {conta}")
                resultado_consulta = self.bb_service.consultar_extrato(
                    agencia=agencia,
                    conta=conta,
                    data_inicio=data_inicio,
                    data_fim=data_fim
                )
                lancamentos = resultado_consulta.get('dados', {}).get('lancamentos', [])
            else:  # SANTANDER
                logger.info(f"🔄 Consultando extrato Santander")
                # Para Santander, converter datetime para string YYYY-MM-DD
                # ✅ IMPORTANTE: A API do Santander usa apenas a data (sem hora)
                # Se data_fim é hoje, garantir que inclua o dia completo
                data_inicio_str = data_inicio.strftime('%Y-%m-%d') if data_inicio else None
                data_fim_str = data_fim.strftime('%Y-%m-%d') if data_fim else None
                logger.info(f"📅 Período para API Santander: {data_inicio_str} a {data_fim_str}")
                
                # ✅ Santander precisa de agencia e conta OU statement_id
                # Se não foram fornecidos, listar contas e usar a primeira (mesma lógica do santander_agent)
                if not agencia or not conta:
                    logger.info("🔍 Agência/conta não fornecidas. Listando contas disponíveis...")
                    resultado_contas = self.santander_service.listar_contas()
                    
                    if not resultado_contas.get('sucesso'):
                        return {
                            'sucesso': False,
                            'erro': 'Não foi possível listar contas',
                            'resposta': resultado_contas.get('resposta', '❌ Não foi possível listar contas disponíveis. Verifique a configuração do Santander.')
                        }
                    
                    # O 'dados' já é a lista de contas diretamente
                    contas = resultado_contas.get('dados', [])
                    if not contas:
                        return {
                            'sucesso': False,
                            'erro': 'Nenhuma conta encontrada',
                            'resposta': '❌ Nenhuma conta encontrada no Santander. Verifique se há contas vinculadas ao certificado digital.'
                        }
                    
                    # Usar a primeira conta disponível (já vem formatada corretamente da API)
                    primeira_conta = contas[0]
                    agencia = primeira_conta.get('branchCode') or primeira_conta.get('branch') or primeira_conta.get('agencia')
                    conta = primeira_conta.get('number') or primeira_conta.get('accountNumber') or primeira_conta.get('conta')
                    
                    if not agencia or not conta:
                        return {
                            'sucesso': False,
                            'erro': 'Dados da conta incompletos',
                            'resposta': '❌ Não foi possível extrair agência e conta da primeira conta disponível.'
                        }
                    
                    logger.info(f"✅ Usando primeira conta disponível: Agência {agencia}, Conta {conta}")
                
                resultado_consulta = self.santander_service.consultar_extrato(
                    agencia=agencia,
                    conta=conta,
                    data_inicio=data_inicio_str,
                    data_fim=data_fim_str
                )
                lancamentos = resultado_consulta.get('dados', [])
            
            if not resultado_consulta.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': resultado_consulta.get('erro', 'Erro ao consultar extrato'),
                    'resposta': resultado_consulta.get('resposta', '❌ Erro ao consultar extrato.')
                }
            
            if not lancamentos:
                return {
                    'sucesso': True,
                    'total': 0,
                    'novos': 0,
                    'duplicados': 0,
                    'erros': 0,
                    'resposta': f'📋 Nenhum lançamento encontrado no período ({data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}).'
                }
            
            # 2. Importar lançamentos para SQL Server
            logger.info(f"📥 Importando {len(lancamentos)} lançamentos para SQL Server...")
            resultado_importacao = self.importar_lancamentos(
                lancamentos=lancamentos,
                agencia=agencia,
                conta=conta,
                banco=banco
            )
            
            # Adicionar informações do período
            resultado_importacao['periodo'] = {
                'data_inicio': data_inicio.strftime('%Y-%m-%d'),
                'data_fim': data_fim.strftime('%Y-%m-%d')
            }
            
            return resultado_importacao
            
        except Exception as e:
            logger.error(f"❌ Erro na sincronização: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro na sincronização: {str(e)}'
            }
    
    # =========================================================================
    # VINCULAÇÃO MANUAL DE LANÇAMENTOS A PROCESSOS
    # =========================================================================
    
    def vincular_lancamento_processo(
        self,
        id_movimentacao: int,
        processo_referencia: str,
        tipo_relacionamento: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Vincula um lançamento bancário a um processo de importação.
        
        Args:
            id_movimentacao: ID do lançamento na tabela MOVIMENTACAO_BANCARIA
            processo_referencia: Referência do processo (ex: 'DMD.0083/25')
            tipo_relacionamento: Tipo do relacionamento (ex: 'PAGAMENTO_FRETE', 'PAGAMENTO_IMPOSTOS')
        
        Returns:
            Dict com resultado da vinculação
        """
        if not self.sql_adapter:
            return {
                'sucesso': False,
                'erro': 'SQL Server não disponível',
                'resposta': '❌ SQL Server não está disponível.'
            }
        
        try:
            query = """
                UPDATE MOVIMENTACAO_BANCARIA
                SET processo_referencia = ?,
                    tipo_relacionamento = ?,
                    atualizado_em = GETDATE()
                WHERE id_movimentacao = ?
            """
            
            self.sql_adapter.execute_non_query(query, (
                processo_referencia,
                tipo_relacionamento,
                id_movimentacao
            ))
            
            logger.info(f"✅ Lançamento {id_movimentacao} vinculado ao processo {processo_referencia}")
            
            return {
                'sucesso': True,
                'resposta': f'✅ Lançamento vinculado ao processo {processo_referencia}'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao vincular lançamento: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao vincular lançamento: {str(e)}'
            }
    
    # =========================================================================
    # CONSULTAS
    # =========================================================================
    
    def listar_lancamentos_nao_vinculados(
        self,
        limite: int = 50,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Lista lançamentos que não estão vinculados a nenhum processo.
        
        Args:
            limite: Número máximo de resultados
            data_inicio: Data inicial (opcional)
            data_fim: Data final (opcional)
        
        Returns:
            Dict com lista de lançamentos não vinculados
        """
        if not self.sql_adapter:
            return {
                'sucesso': False,
                'erro': 'SQL Server não disponível',
                'lancamentos': []
            }
        
        try:
            query = """
                SELECT TOP (?)
                    id_movimentacao,
                    banco_origem,
                    agencia_origem,
                    conta_origem,
                    data_movimentacao,
                    valor_movimentacao,
                    sinal_movimentacao,
                    descricao_movimentacao,
                    cpf_cnpj_contrapartida,
                    nome_contrapartida
                FROM MOVIMENTACAO_BANCARIA
                WHERE processo_referencia IS NULL
            """
            
            params = [limite]
            
            if data_inicio:
                query += " AND data_movimentacao >= ?"
                params.append(self._formatar_data_sql(data_inicio))
            
            if data_fim:
                query += " AND data_movimentacao <= ?"
                params.append(self._formatar_data_sql(data_fim))
            
            query += " ORDER BY data_movimentacao DESC"
            
            resultado = self.sql_adapter.execute_query(query, tuple(params))
            
            lancamentos = []
            if resultado:
                for row in resultado:
                    lancamentos.append({
                        'id_movimentacao': row.get('id_movimentacao'),
                        'banco': row.get('banco_origem'),
                        'agencia': row.get('agencia_origem'),
                        'conta': row.get('conta_origem'),
                        'data': row.get('data_movimentacao'),
                        'valor': row.get('valor_movimentacao'),
                        'sinal': row.get('sinal_movimentacao'),
                        'descricao': row.get('descricao_movimentacao'),
                        'cpf_cnpj_contrapartida': row.get('cpf_cnpj_contrapartida'),
                        'nome_contrapartida': row.get('nome_contrapartida')
                    })
            
            return {
                'sucesso': True,
                'total': len(lancamentos),
                'lancamentos': lancamentos
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar lançamentos: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'lancamentos': []
            }
    
    def obter_resumo_movimentacoes_processo(self, processo_referencia: str) -> Dict[str, Any]:
        """
        Obtém resumo de movimentações bancárias de um processo.
        
        Args:
            processo_referencia: Referência do processo (ex: 'DMD.0083/25')
        
        Returns:
            Dict com resumo das movimentações
        """
        if not self.sql_adapter:
            return {
                'sucesso': False,
                'erro': 'SQL Server não disponível'
            }
        
        try:
            query = """
                SELECT 
                    COUNT(*) as total_lancamentos,
                    SUM(CASE WHEN sinal_movimentacao = 'D' THEN valor_movimentacao ELSE 0 END) as total_debitos,
                    SUM(CASE WHEN sinal_movimentacao = 'C' THEN valor_movimentacao ELSE 0 END) as total_creditos,
                    MIN(data_movimentacao) as primeira_movimentacao,
                    MAX(data_movimentacao) as ultima_movimentacao
                FROM MOVIMENTACAO_BANCARIA
                WHERE processo_referencia = ?
            """
            
            resultado = self.sql_adapter.execute_query(query, (processo_referencia,))
            
            if resultado and len(resultado) > 0:
                row = resultado[0]
                return {
                    'sucesso': True,
                    'processo_referencia': processo_referencia,
                    'total_lancamentos': row.get('total_lancamentos', 0),
                    'total_debitos': float(row.get('total_debitos', 0) or 0),
                    'total_creditos': float(row.get('total_creditos', 0) or 0),
                    'saldo': float(row.get('total_creditos', 0) or 0) - float(row.get('total_debitos', 0) or 0),
                    'primeira_movimentacao': row.get('primeira_movimentacao'),
                    'ultima_movimentacao': row.get('ultima_movimentacao')
                }
            
            return {
                'sucesso': True,
                'processo_referencia': processo_referencia,
                'total_lancamentos': 0,
                'total_debitos': 0,
                'total_creditos': 0,
                'saldo': 0
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter resumo: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }


# =========================================================================
# SINGLETON
# =========================================================================

_banco_sincronizacao_service = None

def get_banco_sincronizacao_service() -> BancoSincronizacaoService:
    """Retorna instância singleton do serviço de sincronização."""
    global _banco_sincronizacao_service
    if _banco_sincronizacao_service is None:
        _banco_sincronizacao_service = BancoSincronizacaoService()
    return _banco_sincronizacao_service

