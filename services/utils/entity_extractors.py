"""
Utilitários para extração de entidades de mensagens de texto.

Extrai referências de processos, números de CE, CCT, DI, DUIMP de mensagens de usuário.
"""
import re
import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class EntityExtractors:
    """Utilitários estáticos para extração de entidades de mensagens."""
    
    @staticmethod
    def extrair_processo_referencia(mensagem: str, buscar_no_banco: bool = True) -> Optional[str]:
        """
        Extrai referência de processo da mensagem (ex: ALH.0001/25, vdm.003, etc.).
        
        Args:
            mensagem: Mensagem do usuário
            buscar_no_banco: Se True, tenta buscar processo completo no banco quando encontra variação parcial
        
        Returns:
            Referência completa do processo (ex: 'VDM.0003/25') ou None
        """
        mensagem_upper = mensagem.upper()
        
        # Padrão completo: ALH.0001/25, DMD.0035/25, MV5.0013/25, etc.
        # ✅ CORREÇÃO: Aceitar números na categoria (ex: MV5, GPS)
        padrao_completo = r'([A-Z0-9]{2,4}\.\d{4}/\d{2})'
        match = re.search(padrao_completo, mensagem_upper)
        if match:
            return match.group(1)

        # ✅ MELHORIA (22/01/2026): aceitar "VDM.003/25" (3 dígitos com ano explícito)
        # Regra: se o usuário informou o ano (/25), NÃO inferir ano atual (/26).
        padrao_parcial_com_ano = r'([A-Z0-9]{2,4})\.(\d{1,4})/(\d{2})'
        match_parcial_ano = re.search(padrao_parcial_com_ano, mensagem_upper)
        if match_parcial_ano:
            prefixo = match_parcial_ano.group(1)
            numero = match_parcial_ano.group(2)
            ano = match_parcial_ano.group(3)
            numero_formatado = numero.zfill(4)
            return f"{prefixo}.{numero_formatado}/{ano}"
        
        # ✅ MELHORIA: Aceitar variações parciais (ex: vdm.003, VDM.003, vdm.0003, mv5.0013)
        # Padrão parcial: 2-4 caracteres (letras e/ou números), ponto, 1-4 dígitos
        padrao_parcial = r'([A-Z0-9]{2,4})\.(\d{1,4})'
        match_parcial = re.search(padrao_parcial, mensagem_upper)
        if match_parcial:
            prefixo = match_parcial.group(1)  # Ex: VDM
            numero = match_parcial.group(2)   # Ex: 003
            
            # Tentar expandir para formato completo buscando no banco
            if buscar_no_banco:
                # ✅ Busca completa (apenas_ativos=False) para extrair processo de mensagem genérica
                # Se for para relatório do dia, deve ser filtrado depois pela fonte de dados
                processo_completo = EntityExtractors.buscar_processo_por_variacao(
                    prefixo, numero, 
                    apenas_ativos=False,  # Busca completa (ativos + históricos)
                    buscar_externamente=False  # Não busca externamente automaticamente
                )
                if processo_completo:
                    return processo_completo
            
            # Se não encontrou, tentar inferir o ano atual (últimos 2 dígitos)
            ano_atual = datetime.now().strftime('%y')
            # Preencher com zeros à esquerda se necessário
            numero_formatado = numero.zfill(4)
            return f"{prefixo}.{numero_formatado}/{ano_atual}"
        
        # ✅ NOVO: Aceitar formato sem ponto (ex: bnd0093, alh0176, mv50013)
        # Padrão: 2-4 caracteres (letras e/ou números) seguidas de 1-4 dígitos (sem ponto, sem barra)
        # ✅ CORREÇÃO: Aceitar números na categoria (ex: MV5, GPS)
        padrao_sem_ponto = r'\b([A-Z0-9]{2,4})(\d{1,4})\b'
        match_sem_ponto = re.search(padrao_sem_ponto, mensagem_upper)
        if match_sem_ponto:
            prefixo = match_sem_ponto.group(1)  # Ex: BND
            numero = match_sem_ponto.group(2)   # Ex: 0093
            
            # ✅ Verificar se é categoria conhecida de processo (do banco de dados)
            try:
                from db_manager import verificar_categoria_processo
                if verificar_categoria_processo(prefixo):
                    # Tentar expandir para formato completo buscando no banco
                    if buscar_no_banco:
                        # ✅ Busca completa (apenas_ativos=False) para extrair processo de mensagem genérica
                        processo_completo = EntityExtractors.buscar_processo_por_variacao(
                            prefixo, numero,
                            apenas_ativos=False,  # Busca completa (ativos + históricos)
                            buscar_externamente=False  # Não busca externamente automaticamente
                        )
                        if processo_completo:
                            return processo_completo
                    
                    # Se não encontrou, tentar inferir o ano atual
                    ano_atual = datetime.now().strftime('%y')
                    numero_formatado = numero.zfill(4)
                    return f"{prefixo}.{numero_formatado}/{ano_atual}"
            except Exception as e:
                logger.debug(f'Erro ao verificar categoria de processo {prefixo}: {e}')
        
        return None
    
    @staticmethod
    def buscar_processo_por_variacao(prefixo: str, numero: str, apenas_ativos: bool = False, buscar_externamente: bool = False) -> Optional[str]:
        """
        Busca processo completo no banco por variação parcial (ex: VDM, 003).
        
        ✅ ARQUITETURA mAIke (10/01/2026):
        - processos_kanban (SQLite) = cache de processos ATIVOS (filtrados pelo Kanban)
        - BD maike_assistente (SQL Server) = fonte completa (ativos + históricos)
        - Fontes externas = Kanban API, SQL Server Make antigo → adaptadas via ProcessoRepository
        
        Args:
            prefixo: Prefixo do processo (ex: 'VDM', 'ALH', 'MV5')
            numero: Número do processo (ex: '003', '0003')
            apenas_ativos: Se True, busca apenas em processos_kanban (para relatórios do dia)
                          Se False, busca completo (processos_kanban → BD maike_assistente → externo)
            buscar_externamente: Se True e não encontrar no mAIke, busca em fontes externas via ProcessoRepository
        
        Returns:
            Processo completo encontrado (ex: 'VDM.0003/25') ou None
        """
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            numero_formatado = numero.zfill(4)  # 003 -> 0003
            padrao_like = f"{prefixo}.{numero_formatado}%"
            
            # ✅ PRIORIDADE 1: Sempre buscar em processos_kanban primeiro (cache rápido de ativos)
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT processo_referencia 
                FROM processos_kanban
                WHERE processo_referencia LIKE ?
                ORDER BY processo_referencia DESC
                LIMIT 1
            ''', (padrao_like,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                processo_encontrado = row[0]
                logger.debug(f'✅ Processo encontrado no mAIke (processos_kanban): {processo_encontrado}')
                
                # Se busca apenas ativos, retornar imediatamente (para relatórios do dia)
                if apenas_ativos:
                    return processo_encontrado
                # Se busca completa, também retornar (já encontrou, não precisa buscar mais)
                return processo_encontrado
            
            # ✅ PRIORIDADE 2: Se busca apenas ativos e não encontrou, retornar None
            # (processo não está mais ativo ou nunca esteve)
            if apenas_ativos:
                logger.debug(f'⚠️ Processo {prefixo}.{numero_formatado}* não encontrado em processos ativos (apenas_ativos=True)')
                return None
            
            # ✅ PRIORIDADE 3: Se busca completa, tentar buscar no BD maike_assistente (fonte completa)
            logger.debug(f'📊 Processo não encontrado em processos_kanban, buscando no BD maike_assistente...')
            processo = EntityExtractors._buscar_em_maike_assistente(padrao_like)
            if processo:
                logger.info(f'✅ Processo encontrado no BD maike_assistente: {processo}')
                return processo
            
            # ✅ PRIORIDADE 4: Se não encontrou e buscar_externamente=True, 
            # usar ProcessoRepository (busca em fontes externas e grava no mAIke via DTO)
            if buscar_externamente:
                try:
                    logger.debug(f'📡 Processo não encontrado no mAIke, buscando em fontes externas via ProcessoRepository...')
                    from services.processo_repository import ProcessoRepository
                    
                    # Tentar buscar processo completo usando ProcessoRepository
                    # Ele busca: processos_kanban → SQL Server maike novo → SQL Server antigo → API Kanban
                    # E grava automaticamente no mAIke (processos_kanban e BD maike_assistente)
                    repositorio = ProcessoRepository()
                    
                    # Tentar algumas variações possíveis
                    from datetime import datetime
                    ano_atual = datetime.now().strftime('%y')
                    ano_anterior = str(int(ano_atual) - 1).zfill(2)
                    ano_2_antes = str(int(ano_atual) - 2).zfill(2)
                    
                    variações_tentativas = [
                        f"{prefixo}.{numero_formatado}/{ano_atual}",
                        f"{prefixo}.{numero_formatado}/{ano_anterior}",
                        f"{prefixo}.{numero_formatado}/{ano_2_antes}",
                    ]
                    
                    for processo_tentativa in variações_tentativas:
                        processo_dto = repositorio.buscar_por_referencia(processo_tentativa)
                        if processo_dto and processo_dto.processo_referencia:
                            logger.info(f'✅ Processo encontrado em fonte externa e salvo no mAIke: {processo_dto.processo_referencia}')
                            return processo_dto.processo_referencia
                    
                except Exception as e:
                    logger.debug(f'⚠️ Erro ao buscar processo em fontes externas (não crítico): {e}')
            
            return None
        except Exception as e:
            logger.warning(f'Erro ao buscar processo por variação {prefixo}.{numero}: {e}')
            return None
    
    @staticmethod
    def _buscar_em_maike_assistente(padrao_like: str) -> Optional[str]:
        """
        Busca processo no BD maike_assistente (SQL Server) por padrão LIKE.
        
        Args:
            padrao_like: Padrão LIKE (ex: 'VDM.0003%')
        
        Returns:
            Processo completo encontrado ou None
        """
        try:
            from utils.sql_server_adapter import get_sql_adapter
            
            sql_adapter = get_sql_adapter()
            
            # Escapar aspas simples para prevenir SQL injection
            padrao_escaped = padrao_like.replace("'", "''")
            
            # Buscar processo no BD maike_assistente
            query = f'''
                SELECT TOP 1 numero_processo
                FROM mAIke_assistente.dbo.PROCESSO_IMPORTACAO
                WHERE numero_processo LIKE '{padrao_escaped}'
                ORDER BY numero_processo DESC
            '''
            
            result = sql_adapter.execute_query(query, 'mAIke_assistente', None, notificar_erro=False)
            
            if result.get('success') and result.get('data'):
                rows = result['data']
                if rows and len(rows) > 0:
                    processo = rows[0].get('numero_processo')
                    if processo:
                        logger.debug(f'✅ Processo encontrado no BD maike_assistente: {processo}')
                        return processo
            
            return None
        except Exception as e:
            logger.debug(f'⚠️ Erro ao buscar processo no BD maike_assistente (não crítico): {e}')
            return None
    
    @staticmethod
    def extrair_numero_ce(mensagem: str) -> Optional[str]:
        """
        Extrai número de CE da mensagem.
        
        CE é sempre numérico (geralmente 15 dígitos, mas aceita 10-15 dígitos).
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            Número de CE encontrado (10-15 dígitos) ou None
        """
        # CE é sempre numérico - aceitar 10-15 dígitos para flexibilidade
        padrao = r'\b(\d{10,15})\b'
        match = re.search(padrao, mensagem)
        if match:
            return match.group(1)
        return None
    
    @staticmethod
    def extrair_numero_cct(mensagem: str) -> Optional[str]:
        """
        Extrai número de CCT da mensagem.
        
        Padrões suportados:
        - MIA-XXXX (ex: MIA-4675)
        - MIAXXXX (ex: MIA4673) - sem hífen
        - CWL-XXXX ou CWLXXXX (ex: CWL25100012, CWL-25100012)
        - Outros padrões com 3 letras seguidas de hífen (opcional) e números
        
        ⚠️ IMPORTANTE: Retorna o número EXATAMENTE como está na mensagem (preserva formato original).
        A normalização (adicionar/remover hífen) é feita na função de vinculação.
        
        ⚠️ CRÍTICO: NÃO detectar como CCT se for uma categoria de processo conhecida (ALH, VDM, BND, etc.)
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            Número de CCT encontrado (ex: 'MIA-4675' ou 'MIA4673') ou None
        """
        mensagem_upper = mensagem.upper()
        
        # Padrão: 3 letras maiúsculas + hífen (opcional) + números
        # Ex: MIA-4675, MIA4673, CWL25100012, CWL-25100012
        padrao_cct = r'\b([A-Z]{3})(?:-)?(\d+)\b'
        match = re.search(padrao_cct, mensagem_upper)
        if match:
            prefixo = match.group(1)
            numero = match.group(2)
            
            # ✅ CRÍTICO: Se o prefixo é uma categoria de processo conhecida, NÃO é CCT
            try:
                from db_manager import verificar_categoria_processo
                # Também verificar se não é CCT, CE, DI, DUIMP (palavras reservadas)
                palavras_reservadas = ['CCT', 'CE', 'DI', 'DUIMP']
                if prefixo in palavras_reservadas or verificar_categoria_processo(prefixo):
                    logger.debug(f'⚠️ {prefixo}{numero} detectado como categoria de processo, não CCT')
                    return None
            except Exception as e:
                logger.debug(f'Erro ao verificar categoria de processo para CCT: {e}')
            
            # ✅ CORREÇÃO: Preservar formato original da mensagem (com ou sem hífen)
            # Verificar se tinha hífen na mensagem original
            if f"{prefixo}-{numero}" in mensagem_upper or f"{prefixo}-{numero.lower()}" in mensagem_upper:
                return f"{prefixo}-{numero}"
            else:
                # Sem hífen na mensagem original - retornar sem hífen
                return f"{prefixo}{numero}"
        
        return None
    
    @staticmethod
    def extrair_numero_duimp_ou_di(mensagem: str) -> Optional[Dict[str, str]]:
        """
        Extrai número de DUIMP ou DI da mensagem com reconhecimento automático.
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            Dict com:
            - 'tipo': 'DUIMP' ou 'DI'
            - 'numero': número sem versão (ex: '25BR0000194844')
            - 'versao': versão se informada (ex: '1'), ou None
            - 'numero_completo': número completo como informado (ex: '25BR0000194844-1')
            Ou None se não encontrar
        """
        # Padrão DUIMP: 25BR[digitos] ou 25BR[digitos]-[versao]
        # Ex: 25BR0000194844, 25BR0000194844-1
        padrao_duimp = r'\b(25BR\d{9,11}(?:-(\d+))?)\b'
        match_duimp = re.search(padrao_duimp, mensagem, re.IGNORECASE)
        if match_duimp:
            numero_completo = match_duimp.group(1).upper()
            versao = match_duimp.group(2) if match_duimp.group(2) else None
            # Extrair número base (sem versão)
            if '-' in numero_completo:
                numero_base = numero_completo.split('-')[0]
            else:
                numero_base = numero_completo
            return {
                'tipo': 'DUIMP',
                'numero': numero_base,
                'versao': versao,
                'numero_completo': numero_completo
            }
        
        # Padrão DI: [2 digitos]/[digitos]-[digito]
        # Ex: 25/2535383-7
        padrao_di = r'\b(\d{2}/\d+-\d)\b'
        match_di = re.search(padrao_di, mensagem)
        if match_di:
            numero_completo = match_di.group(1)
            return {
                'tipo': 'DI',
                'numero': numero_completo,
                'versao': None,  # DI não tem versão
                'numero_completo': numero_completo
            }
        
        return None
