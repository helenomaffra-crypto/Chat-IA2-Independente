"""
Serviço para geração de extrato PDF da DUIMP.

Estrutura modular para evitar código monolítico.
Separa responsabilidades:
- Consulta ao Portal Único (autenticada)
- Busca de dados no banco
- Geração de PDF (futuro)
"""
import logging
import json
import time
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DuimpPdfService:
    """
    Serviço para operações relacionadas a extrato PDF de DUIMP.
    
    Responsabilidades:
    1. Buscar número e versão da DUIMP no banco
    2. Consultar dados da DUIMP no Portal Único (autenticado)
    3. Gerar PDF do extrato (futuro)
    """
    
    def __init__(self):
        """Inicializa o serviço."""
        self.downloads_dir = Path('downloads')
        self.downloads_dir.mkdir(exist_ok=True)
        # Limpar PDFs antigos (mais de 1 hora) para não saturar o diretório
        self._limpar_pdfs_antigos()
    
    def _limpar_pdfs_antigos(self, horas_antigas: int = 1):
        """
        Remove PDFs antigos do diretório downloads para não saturar.
        
        Args:
            horas_antigas: Quantas horas um PDF deve ter para ser considerado antigo (padrão: 1 hora)
        """
        try:
            if not self.downloads_dir.exists():
                return
            
            agora = time.time()
            limite_tempo = horas_antigas * 3600  # Converter horas para segundos
            
            arquivos_removidos = 0
            for arquivo in self.downloads_dir.glob('*.pdf'):
                try:
                    # Verificar idade do arquivo
                    tempo_modificacao = arquivo.stat().st_mtime
                    idade_segundos = agora - tempo_modificacao
                    
                    if idade_segundos > limite_tempo:
                        arquivo.unlink()
                        arquivos_removidos += 1
                        logger.debug(f'PDF antigo removido: {arquivo.name}')
                except Exception as e:
                    logger.warning(f'Erro ao remover PDF antigo {arquivo.name}: {e}')
            
            if arquivos_removidos > 0:
                logger.info(f'✅ {arquivos_removidos} PDF(s) antigo(s) removido(s) do diretório downloads')
        except Exception as e:
            logger.warning(f'Erro ao limpar PDFs antigos: {e}')
    
    def _limpar_pdfs_antigos(self, horas_antigas: int = 1):
        """
        Remove PDFs antigos do diretório downloads para não saturar.
        
        Args:
            horas_antigas: Quantas horas um PDF deve ter para ser considerado antigo (padrão: 1 hora)
        """
        try:
            if not self.downloads_dir.exists():
                return
            
            agora = time.time()
            limite_tempo = horas_antigas * 3600  # Converter horas para segundos
            
            arquivos_removidos = 0
            for arquivo in self.downloads_dir.glob('*.pdf'):
                try:
                    # Verificar idade do arquivo
                    tempo_modificacao = arquivo.stat().st_mtime
                    idade_segundos = agora - tempo_modificacao
                    
                    if idade_segundos > limite_tempo:
                        arquivo.unlink()
                        arquivos_removidos += 1
                        logger.debug(f'PDF antigo removido: {arquivo.name}')
                except Exception as e:
                    logger.warning(f'Erro ao remover PDF antigo {arquivo.name}: {e}')
            
            if arquivos_removidos > 0:
                logger.info(f'✅ {arquivos_removidos} PDF(s) antigo(s) removido(s) do diretório downloads')
        except Exception as e:
            logger.warning(f'Erro ao limpar PDFs antigos: {e}')
    
    def buscar_duimp_banco(self, processo_referencia: str) -> Optional[Dict[str, Any]]:
        """
        Busca número e versão da DUIMP no banco de dados.
        
        Busca em múltiplas fontes:
        1. Tabela duimps (SQLite) - se tem processo_referencia
        2. Tabela processo_documentos (SQLite) - vínculo de documentos
        3. Tabela processos_kanban (SQLite) - campo numero_duimp
        4. SQL Server - banco duimp (fallback)
        
        Args:
            processo_referencia: Número do processo (ex: VDM.0003/25)
        
        Returns:
            Dict com {'numero': str, 'versao': str, 'ambiente': str} ou None se não encontrado
        """
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Buscar na tabela duimps (prioridade: produção)
            cursor.execute('''
                SELECT numero, versao, status, ambiente, criado_em
                FROM duimps
                WHERE processo_referencia = ?
                ORDER BY 
                    CASE WHEN ambiente = 'producao' THEN 1 ELSE 2 END,
                    CAST(versao AS INTEGER) DESC,
                    criado_em DESC
                LIMIT 1
            ''', (processo_referencia,))
            
            row = cursor.fetchone()
            if row:
                conn.close()
                return {
                    'numero': row['numero'],
                    'versao': row['versao'],
                    'ambiente': row['ambiente'],
                    'status': row['status']
                }
            
            # 2. Buscar em processo_documentos (vínculo de documentos)
            cursor.execute('''
                SELECT numero_documento
                FROM processo_documentos
                WHERE processo_referencia = ? AND tipo_documento = 'DUIMP'
                ORDER BY id DESC
                LIMIT 1
            ''', (processo_referencia,))
            
            row = cursor.fetchone()
            if row:
                numero_duimp = row['numero_documento']
                
                # Buscar versão e ambiente na tabela duimps pelo número
                cursor.execute('''
                    SELECT versao, ambiente, status
                    FROM duimps
                    WHERE numero = ?
                    ORDER BY 
                        CASE WHEN ambiente = 'producao' THEN 1 ELSE 2 END,
                        CAST(versao AS INTEGER) DESC
                    LIMIT 1
                ''', (numero_duimp,))
                
                row_duimp = cursor.fetchone()
                if row_duimp:
                    versao = row_duimp['versao']
                    ambiente = row_duimp['ambiente']
                    status = row_duimp['status']
                else:
                    # Se não encontrou na tabela duimps, assumir versão 1 e ambiente produção
                    versao = '1'
                    ambiente = 'producao'
                    status = 'N/A'
                
                conn.close()
                logger.info(f'DUIMP encontrada em processo_documentos para {processo_referencia}: {numero_duimp} v{versao}')
                return {
                    'numero': numero_duimp,
                    'versao': versao,
                    'ambiente': ambiente,
                    'status': status
                }
            
            # 3. Buscar em processos_kanban (campo numero_duimp)
            cursor.execute('''
                SELECT numero_duimp
                FROM processos_kanban
                WHERE processo_referencia = ? AND numero_duimp IS NOT NULL AND numero_duimp != '' AND numero_duimp != '/ -'
                LIMIT 1
            ''', (processo_referencia,))
            
            row = cursor.fetchone()
            if row:
                numero_duimp = row['numero_duimp']
                
                # Limpar formato (pode ter espaços ou caracteres)
                numero_duimp = numero_duimp.strip().replace('/ -', '').strip()
                
                if numero_duimp:
                    # Buscar versão e ambiente na tabela duimps
                    cursor.execute('''
                        SELECT versao, ambiente, status
                        FROM duimps
                        WHERE numero = ?
                        ORDER BY 
                            CASE WHEN ambiente = 'producao' THEN 1 ELSE 2 END,
                            CAST(versao AS INTEGER) DESC
                        LIMIT 1
                    ''', (numero_duimp,))
                    
                    row_duimp = cursor.fetchone()
                    if row_duimp:
                        versao = row_duimp['versao']
                        ambiente = row_duimp['ambiente']
                        status = row_duimp['status']
                    else:
                        # Se não encontrou na tabela duimps, assumir versão 1 e ambiente produção
                        versao = '1'
                        ambiente = 'producao'
                        status = 'N/A'
                    
                    conn.close()
                    logger.info(f'DUIMP encontrada em processos_kanban para {processo_referencia}: {numero_duimp} v{versao}')
                    return {
                        'numero': numero_duimp,
                        'versao': versao,
                        'ambiente': ambiente,
                        'status': status
                    }
            
            conn.close()
            
            # 4. Tentar buscar no SQL Server usando ProcessoRepository (com fallback e migração automática)
            try:
                logger.info(f'🔍 [DUIMP] Tentando buscar DUIMP no SQL Server para {processo_referencia}...')
                # ✅ CORREÇÃO: Usar ProcessoRepository que tem fallback para banco antigo e migração automática
                from services.processo_repository import ProcessoRepository
                
                repositorio = ProcessoRepository()
                logger.info(f'🔍 [DUIMP] ProcessoRepository criado, buscando processo {processo_referencia}...')
                processo_dto = repositorio.buscar_por_referencia(processo_referencia)
                
                if processo_dto:
                    logger.info(f'✅ [DUIMP] Processo {processo_referencia} encontrado via ProcessoRepository (fonte: {processo_dto.fonte})')
                    logger.info(f'📊 [DUIMP] Processo tem numero_duimp: {processo_dto.numero_duimp}')
                    
                    if processo_dto.numero_duimp:
                        numero = processo_dto.numero_duimp
                        # Buscar versão e situação dos dados completos
                        versao = '1'  # Default
                        situacao = 'N/A'
                        
                        if processo_dto.dados_completos and isinstance(processo_dto.dados_completos, dict):
                            duimp_data = processo_dto.dados_completos.get('duimp', {})
                            logger.info(f'📊 [DUIMP] dados_completos tem duimp: {bool(duimp_data)}')
                            if duimp_data:
                                versao = str(duimp_data.get('versao', '1'))
                                situacao = duimp_data.get('situacao', 'N/A')
                                logger.info(f'📊 [DUIMP] DUIMP data: numero={duimp_data.get("numero")}, versao={versao}, situacao={situacao}')
                        
                        logger.info(f'✅ [DUIMP] DUIMP encontrada via ProcessoRepository para {processo_referencia}: {numero} v{versao}')
                        return {
                            'numero': numero,
                            'versao': versao,
                            'ambiente': 'producao',  # SQL Server geralmente é produção
                            'status': situacao
                        }
                    else:
                        logger.warning(f'⚠️ [DUIMP] Processo {processo_referencia} encontrado mas não tem numero_duimp')
                else:
                    logger.warning(f'⚠️ [DUIMP] Processo {processo_referencia} não encontrado via ProcessoRepository')
            except Exception as e:
                logger.error(f'❌ [DUIMP] Erro ao buscar DUIMP no SQL Server para {processo_referencia}: {e}', exc_info=True)
            
            logger.warning(f'DUIMP não encontrada em nenhuma fonte para processo {processo_referencia}')
            return None
            
        except Exception as e:
            logger.error(f'Erro ao buscar DUIMP no banco para {processo_referencia}: {e}', exc_info=True)
            return None
    
    def consultar_duimp_portal(self, numero: str, versao: str, ambiente: Optional[str] = None) -> Tuple[int, Any]:
        """
        Consulta dados da DUIMP no Portal Único (autenticado).
        
        Args:
            numero: Número da DUIMP
            versao: Versão da DUIMP
            ambiente: 'validacao' ou 'producao' (opcional, tenta detectar automaticamente)
        
        Returns:
            Tuple (status_code, response_body)
        """
        try:
            # Usar call_portal de utils/portal_proxy que já gerencia autenticação
            try:
                from utils.portal_proxy import call_portal
            except ImportError as e:
                logger.warning(f'Erro ao importar call_portal: {e}')
                return 500, {'erro': 'Módulo não disponível', 'detalhes': str(e)}
            
            # Se ambiente não foi fornecido, usar padrão (produção primeiro)
            if not ambiente:
                ambiente = 'producao'
            
            # Consultar capa da DUIMP usando call_portal (já gerencia autenticação e ambiente)
            path = f'/duimp-api/api/ext/duimp/{numero}/{versao}'
            logger.info(f'Consultando DUIMP {numero}/{versao} no Portal Único (ambiente: {ambiente})')
            
            try:
                status, body = call_portal(path, accept='application/json')
            except Exception as e:
                error_msg = str(e)
                logger.warning(f'Erro ao chamar call_portal: {error_msg}')
                # Se for erro de certificado, retornar erro específico
                if 'cert' in error_msg.lower() or 'pfx' in error_msg.lower() or 'arquivo .pfx não encontrado' in error_msg:
                    return 500, {'erro': 'Certificado não configurado', 'detalhes': 'Certificado .pfx necessário para autenticação no Portal Único'}
                return 500, {'erro': 'Erro ao consultar Portal Único', 'detalhes': error_msg}
            
            # Normalizar resposta
            body_normalized = self._normalize_response(body)
            
            return status, body_normalized
            
        except Exception as e:
            logger.error(f'Erro ao consultar DUIMP {numero}/{versao} no Portal Único: {e}', exc_info=True)
            # Retornar erro 500 mas com mensagem clara
            error_msg = str(e)
            if 'No module named' in error_msg:
                return 500, {'erro': 'Módulo não encontrado', 'detalhes': error_msg}
            elif 'cert' in error_msg.lower() or 'pfx' in error_msg.lower() or 'arquivo .pfx não encontrado' in error_msg:
                return 500, {'erro': 'Certificado não configurado', 'detalhes': 'Certificado .pfx necessário para autenticação'}
            return 500, {'erro': error_msg}
    
    def consultar_itens_duimp_portal(self, numero: str, versao: str, indice: int, ambiente: Optional[str] = None) -> Tuple[int, Any]:
        """
        Consulta item específico da DUIMP no Portal Único.
        
        Args:
            numero: Número da DUIMP
            versao: Versão da DUIMP
            indice: Índice do item
            ambiente: 'validacao' ou 'producao' (opcional)
        
        Returns:
            Tuple (status_code, response_body)
        """
        try:
            # Usar call_portal de utils/portal_proxy que já gerencia autenticação e ambiente
            try:
                from utils.portal_proxy import call_portal
            except ImportError as e:
                logger.warning(f'Erro ao importar call_portal: {e}')
                return 500, {'erro': 'Módulo não disponível', 'detalhes': str(e)}
            
            # Se ambiente não foi fornecido, usar padrão (produção primeiro)
            if not ambiente:
                ambiente = 'producao'
            
            # Consultar item da DUIMP usando call_portal (já gerencia autenticação e ambiente)
            path = f'/duimp-api/api/ext/duimp/{numero}/{versao}/itens/{indice}'
            logger.debug(f'Consultando item {indice} da DUIMP {numero}/{versao} no Portal Único (ambiente: {ambiente})')
            
            try:
                status, body = call_portal(path, accept='application/json')
            except Exception as e:
                error_msg = str(e)
                logger.warning(f'Erro ao chamar call_portal para item: {error_msg}')
                # Se for erro de certificado, retornar erro específico
                if 'cert' in error_msg.lower() or 'pfx' in error_msg.lower() or 'arquivo .pfx não encontrado' in error_msg:
                    return 500, {'erro': 'Certificado não configurado', 'detalhes': 'Certificado .pfx necessário para autenticação no Portal Único'}
                return 500, {'erro': 'Erro ao consultar Portal Único', 'detalhes': error_msg}
            
            # Normalizar resposta
            body_normalized = self._normalize_response(body)
            
            return status, body_normalized
            
        except Exception as e:
            logger.error(f'Erro ao consultar item {indice} da DUIMP {numero}/{versao}: {e}', exc_info=True)
            # Retornar erro 500 mas com mensagem clara
            error_msg = str(e)
            if 'No module named' in error_msg:
                return 500, {'erro': 'Módulo não encontrado', 'detalhes': error_msg}
            return 500, {'erro': str(e)}
    
    def _normalize_response(self, body: Any) -> Any:
        """
        Normaliza resposta do Portal Único.
        Converte strings JSON aninhadas em dicts/listas.
        
        Args:
            body: Resposta do Portal Único
        
        Returns:
            Resposta normalizada
        """
        if isinstance(body, (dict, list)):
            return self._normalize_dict(body)
        if isinstance(body, str):
            body_stripped = body.strip()
            if (body_stripped.startswith('{') and body_stripped.endswith('}')) or \
               (body_stripped.startswith('[') and body_stripped.endswith(']')):
                try:
                    parsed = json.loads(body_stripped)
                    return self._normalize_dict(parsed)
                except json.JSONDecodeError:
                    return body
        return body
    
    def _normalize_dict(self, obj: Any, max_depth: int = 10, depth: int = 0) -> Any:
        """
        Recursivamente converte strings JSON em dicts/listas.
        
        Args:
            obj: Objeto a normalizar
            max_depth: Profundidade máxima de recursão
            depth: Profundidade atual
        
        Returns:
            Objeto normalizado
        """
        if depth > max_depth:
            return obj
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                result[k] = self._normalize_dict(v, max_depth, depth + 1)
            return result
        elif isinstance(obj, list):
            return [self._normalize_dict(item, max_depth, depth + 1) for item in obj]
        elif isinstance(obj, str):
            s = obj.strip()
            if len(s) > 1 and s[0] in ('{', '[') and s[-1] in ('}', ']'):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, (dict, list)):
                        return self._normalize_dict(parsed, max_depth, depth + 1)
                except (json.JSONDecodeError, ValueError):
                    pass
            return obj
        return obj
    
    def buscar_duimp_por_numero(self, numero_duimp: str) -> Optional[Dict[str, Any]]:
        """
        Busca DUIMP diretamente pelo número (sem processo_referencia).
        
        Args:
            numero_duimp: Número da DUIMP (ex: 25BR00002284997)
        
        Returns:
            Dict com numero, versao, ambiente, status ou None se não encontrado
        """
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Limpar número (pode ter espaços ou caracteres)
            numero_duimp_clean = numero_duimp.strip()
            
            # 1. Buscar diretamente na tabela duimps (priorizar produção)
            cursor.execute('''
                SELECT numero, versao, ambiente, status
                FROM duimps
                WHERE numero = ?
                ORDER BY 
                    CASE WHEN ambiente = 'producao' THEN 1 ELSE 2 END,
                    CAST(versao AS INTEGER) DESC
                LIMIT 1
            ''', (numero_duimp_clean,))
            
            row = cursor.fetchone()
            if row:
                conn.close()
                logger.info(f'DUIMP encontrada diretamente por número: {numero_duimp_clean} v{row["versao"]}')
                return {
                    'numero': row['numero'],
                    'versao': row['versao'],
                    'ambiente': row['ambiente'],
                    'status': row['status']
                }
            
            # 2. Buscar em processo_documentos
            cursor.execute('''
                SELECT numero_documento
                FROM processo_documentos
                WHERE numero_documento = ? AND tipo_documento = 'DUIMP'
                ORDER BY id DESC
                LIMIT 1
            ''', (numero_duimp_clean,))
            
            row = cursor.fetchone()
            if row:
                # Se encontrou, buscar versão na tabela duimps
                cursor.execute('''
                    SELECT versao, ambiente, status
                    FROM duimps
                    WHERE numero = ?
                    ORDER BY 
                        CASE WHEN ambiente = 'producao' THEN 1 ELSE 2 END,
                        CAST(versao AS INTEGER) DESC
                    LIMIT 1
                ''', (numero_duimp_clean,))
                
                row_duimp = cursor.fetchone()
                if row_duimp:
                    conn.close()
                    logger.info(f'DUIMP encontrada em processo_documentos: {numero_duimp_clean} v{row_duimp["versao"]}')
                    return {
                        'numero': numero_duimp_clean,
                        'versao': row_duimp['versao'],
                        'ambiente': row_duimp['ambiente'],
                        'status': row_duimp['status']
                    }
            
            # 3. Buscar em processos_kanban (buscar por número exato ou contido)
            cursor.execute('''
                SELECT DISTINCT numero_duimp
                FROM processos_kanban
                WHERE numero_duimp = ? 
                   OR numero_duimp LIKE ?
                   OR numero_duimp LIKE ?
                LIMIT 1
            ''', (numero_duimp_clean, f'%{numero_duimp_clean}%', f'{numero_duimp_clean}%'))
            
            row = cursor.fetchone()
            
            if row:
                # Limpar número encontrado
                numero_encontrado = row['numero_duimp'].strip().replace('/ -', '').strip()
                
                # Se encontrou, buscar versão na tabela duimps
                cursor.execute('''
                    SELECT versao, ambiente, status
                    FROM duimps
                    WHERE numero = ?
                    ORDER BY 
                        CASE WHEN ambiente = 'producao' THEN 1 ELSE 2 END,
                        CAST(versao AS INTEGER) DESC
                    LIMIT 1
                ''', (numero_duimp_clean,))
                
                row_duimp = cursor.fetchone()
                conn.close()
                
                if row_duimp:
                    logger.info(f'DUIMP encontrada em processos_kanban: {numero_duimp_clean} v{row_duimp["versao"]}')
                    return {
                        'numero': numero_duimp_clean,
                        'versao': row_duimp['versao'],
                        'ambiente': row_duimp['ambiente'],
                        'status': row_duimp['status']
                    }
                else:
                    # Se encontrou no kanban mas não na tabela duimps, assumir versão 1/produção
                    conn.close()
                    logger.info(f'DUIMP encontrada em processos_kanban mas não na tabela duimps: {numero_duimp_clean}, assumindo v1/produção')
                    return {
                        'numero': numero_duimp_clean,
                        'versao': '1',
                        'ambiente': 'producao',
                        'status': 'N/A'
                    }
            
            conn.close()
            
            # 4. Se não encontrou, assumir versão 1 e ambiente produção (vai tentar consultar Portal Único)
            logger.warning(f'DUIMP {numero_duimp_clean} não encontrada no banco, assumindo v1/produção')
            return {
                'numero': numero_duimp_clean,
                'versao': '1',
                'ambiente': 'producao',
                'status': 'N/A'
            }
            
        except Exception as e:
            logger.error(f'Erro ao buscar DUIMP por número {numero_duimp}: {e}', exc_info=True)
            return None
    
    def obter_dados_completos_duimp(self, processo_referencia: Optional[str] = None, numero_duimp: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém dados completos da DUIMP (banco + Portal Único).
        
        Versão SIMPLES: apenas consulta e retorna dados.
        Geração de PDF será implementada depois.
        
        Args:
            processo_referencia: Número do processo (ex: VDM.0003/25) - opcional
            numero_duimp: Número da DUIMP diretamente (ex: 25BR00002284997) - opcional
        
        Returns:
            Dict com resultado da consulta:
            {
                'sucesso': bool,
                'numero': str,
                'versao': str,
                'dados_capa': dict,
                'dados_itens': list,
                'erro': str (se houver)
            }
        """
        # Validar que pelo menos um dos dois foi fornecido
        if not processo_referencia and not numero_duimp:
            return {
                'sucesso': False,
                'erro': 'processo_referencia ou numero_duimp é obrigatório',
                'resposta': '❌ Referência de processo ou número da DUIMP é obrigatório.'
            }
        
        # 1. Buscar DUIMP no banco
        if numero_duimp:
            # Buscar diretamente pelo número da DUIMP
            duimp_banco = self.buscar_duimp_por_numero(numero_duimp)
            if not duimp_banco:
                return {
                    'sucesso': False,
                    'erro': f'DUIMP {numero_duimp} não encontrada no banco',
                    'resposta': f'❌ DUIMP {numero_duimp} não encontrada no banco de dados.'
                }
        else:
            # Buscar pelo processo_referencia (método original)
            duimp_banco = self.buscar_duimp_banco(processo_referencia)
            if not duimp_banco:
                return {
                    'sucesso': False,
                    'erro': f'DUIMP não encontrada no banco para o processo {processo_referencia}',
                    'resposta': f'❌ DUIMP não encontrada no banco de dados para o processo {processo_referencia}.'
                }
        
        if not duimp_banco:
            return {
                'sucesso': False,
                'erro': f'DUIMP não encontrada no banco para o processo {processo_referencia}',
                'resposta': f'❌ DUIMP não encontrada no banco de dados para o processo {processo_referencia}.'
            }
        
        numero = duimp_banco['numero']
        versao = duimp_banco['versao']
        ambiente = duimp_banco['ambiente']
        
        logger.info(f'DUIMP encontrada no banco: {numero}/{versao} (ambiente: {ambiente})')
        
        # ✅ REGRA CRÍTICA: Para EXTRATO, buscar APENAS da API oficial
        # NÃO usar informações do Kanban - apenas endpoint oficial (Portal Único)
        
        # 2. SEMPRE consultar capa da DUIMP no Portal Único (endpoint oficial)
        # Para EXTRATO, precisamos dos dados completos da API oficial
        dados_capa = None
        status_capa = None
        ambiente_usado = ambiente or 'producao'
        erro_consulta = None
        
        try:
            if ambiente == 'producao' or not ambiente:
                # Tentar produção primeiro
                try:
                    status_capa, dados_capa = self.consultar_duimp_portal(numero, versao, 'producao')
                    if status_capa == 200:
                        ambiente_usado = 'producao'
                    else:
                        erro_consulta = f'Status {status_capa}'
                except Exception as e:
                    logger.warning(f'Erro ao consultar Portal Único (produção): {e}')
                    erro_consulta = str(e)
                    status_capa = 500
            
            # Se não encontrou em produção, tentar validação
            if status_capa != 200 and ambiente != 'producao':
                try:
                    status_capa, dados_capa = self.consultar_duimp_portal(numero, versao, 'validacao')
                    if status_capa == 200:
                        ambiente_usado = 'validacao'
                    else:
                        erro_consulta = f'Status {status_capa}'
                except Exception as e:
                    logger.warning(f'Erro ao consultar Portal Único (validação): {e}')
                    if not erro_consulta:
                        erro_consulta = str(e)
                    status_capa = 500
        except Exception as e:
            logger.warning(f'Erro geral ao consultar Portal Único (continuando com dados do banco): {e}')
            erro_consulta = str(e)
            status_capa = 500
        
        # Se não conseguiu consultar, retornar dados do banco mesmo
        if status_capa != 200:
            logger.info(f'Consulta ao Portal Único falhou, retornando apenas dados do banco')
            return {
                'sucesso': True,
                'numero': numero,
                'versao': versao,
                'ambiente': ambiente_usado,
                'dados_capa': None,
                'dados_itens': [],
                'total_itens': 0,
                'resposta': f'✅ DUIMP encontrada no banco de dados!\n\n📋 **DUIMP:** {numero}\n📌 **Versão:** {versao}\n🌍 **Ambiente:** {ambiente_usado.upper()}\n\n⚠️ **Nota:** Consulta ao Portal Único não disponível no momento. Por favor, use a funcionalidade "obter dados da DUIMP" para consultar detalhes completos.',
                'aviso': f'Consulta ao Portal Único falhou: {erro_consulta or "Erro desconhecido"}. Dados retornados são do banco local.'
            }
        
        if not isinstance(dados_capa, dict):
            return {
                'sucesso': False,
                'numero': numero,
                'versao': versao,
                'erro': 'Resposta do Portal Único não é um dicionário',
                'resposta': f'❌ Resposta inválida do Portal Único para DUIMP {numero}/{versao}'
            }
        
        # 3. Consultar itens (versão simples: apenas lista de índices)
        itens = dados_capa.get('itens', [])
        dados_itens = []
        
        if isinstance(itens, list):
            for item in itens:
                if isinstance(item, dict):
                    indice = item.get('indice') or item.get('numero')
                    if indice:
                        status_item, dados_item = self.consultar_itens_duimp_portal(
                            numero, versao, indice, ambiente
                        )
                        if status_item == 200 and isinstance(dados_item, dict):
                            dados_itens.append(dados_item)
        
        # ✅ NOVO: Atualizar banco SQL Server (mAIke_assistente) via DocumentoHistoricoService
        if status_capa == 200 and isinstance(dados_capa, dict):
            try:
                # Buscar processo_referencia se não foi fornecido diretamente
                processo_ref_final = processo_referencia
                if not processo_ref_final:
                    # Tentar buscar no banco usando numero_duimp
                    try:
                        import sqlite3
                        from db_manager import get_db_connection
                        conn = get_db_connection()
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        
                        # Buscar em processos_kanban
                        cursor.execute('''
                            SELECT processo_referencia
                            FROM processos_kanban
                            WHERE numero_duimp = ? OR numero_duimp LIKE ?
                            LIMIT 1
                        ''', (numero, f'%{numero}%'))
                        row = cursor.fetchone()
                        if row:
                            processo_ref_final = row['processo_referencia']
                        else:
                            # Buscar em processo_documentos
                            cursor.execute('''
                                SELECT processo_referencia
                                FROM processo_documentos
                                WHERE numero_documento = ? AND tipo_documento = 'DUIMP'
                                LIMIT 1
                            ''', (numero,))
                            row = cursor.fetchone()
                            if row:
                                processo_ref_final = row['processo_referencia']
                        
                        conn.close()
                    except Exception as e:
                        logger.debug(f'Erro ao buscar processo_referencia para DUIMP {numero}: {e}')
                
                # Extrair dados relevantes do payload para atualizar banco
                situacao_obj = dados_capa.get('situacao', {}) if isinstance(dados_capa, dict) else {}
                resultado_risco = dados_capa.get('resultadoAnaliseRisco', {}) if isinstance(dados_capa, dict) else {}
                
                # Montar payload similar ao ProcessoStatusV2Service
                payload_doc = {
                    "identificacao": {
                        "numero": numero,
                        "versao": versao,
                    },
                    "situacao": situacao_obj,
                    "resultadoAnaliseRisco": resultado_risco,
                }
                
                # Extrair situação e canal
                situacao = None
                if isinstance(situacao_obj, dict):
                    situacao = situacao_obj.get('situacaoDuimp') or situacao_obj.get('situacao', '')
                
                canal = None
                if isinstance(resultado_risco, dict):
                    canal = resultado_risco.get('canalConsolidado', '')
                if not canal and isinstance(dados_capa, dict):
                    canal = dados_capa.get('canalConsolidado', '')
                
                # Atualizar banco SQL Server
                from services.documento_historico_service import DocumentoHistoricoService
                svc_doc = DocumentoHistoricoService()
                svc_doc.detectar_e_gravar_mudancas(
                    numero_documento=str(numero),
                    tipo_documento="DUIMP",
                    dados_novos=payload_doc,
                    fonte_dados="DUIMP_API",
                    api_endpoint=f"/duimp-api/api/ext/duimp/{numero}/{versao}",
                    processo_referencia=processo_ref_final,
                )
                logger.info(f'✅ DUIMP {numero} v{versao} atualizada no banco SQL Server (mAIke_assistente) via extrato')
            except Exception as e:
                logger.debug(f'Erro ao atualizar DUIMP no banco SQL Server: {e}')
        
        # 4. Retornar resultado (dados da API oficial, sem modificações do Kanban)
        return {
            'sucesso': True,
            'numero': numero,
            'versao': versao,
            'ambiente': ambiente,
            'dados_capa': dados_capa,  # Dados completos da API oficial (sem modificações do Kanban)
            'dados_itens': dados_itens,
            'total_itens': len(dados_itens),
            'fonte': 'api_portal',
            'resposta': f'✅ DUIMP {numero}/{versao} consultada com sucesso. {len(dados_itens)} item(ns) encontrado(s).'
        }
    
    def gerar_pdf_duimp(self, processo_referencia: Optional[str] = None, numero_duimp: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera PDF do extrato da DUIMP.
        
        Args:
            processo_referencia: Número do processo (opcional)
            numero_duimp: Número da DUIMP diretamente (opcional)
        
        Returns:
            Dict com resultado:
            {
                'sucesso': bool,
                'caminho_arquivo': str (caminho relativo para download),
                'nome_arquivo': str,
                'erro': str (se houver)
            }
        """
        try:
            from flask import render_template
            import io
            import json
            from pathlib import Path
            import os
            
            # 1. Obter dados completos da DUIMP
            dados = self.obter_dados_completos_duimp(processo_referencia=processo_referencia, numero_duimp=numero_duimp)
            
            if not dados.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': dados.get('erro', 'Erro ao obter dados da DUIMP'),
                    'resposta': dados.get('resposta', 'Erro ao obter dados da DUIMP')
                }
            
            numero = dados['numero']
            versao = dados['versao']
            dados_capa = dados.get('dados_capa')
            dados_itens = dados.get('dados_itens', [])
            ambiente = dados.get('ambiente', 'producao')
            
            # Buscar processo_referencia se não foi fornecido diretamente
            processo_ref_final = processo_referencia
            if not processo_ref_final:
                # Tentar buscar no banco usando numero_duimp
                try:
                    import sqlite3
                    from db_manager import get_db_connection
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Buscar em processos_kanban
                    cursor.execute('''
                        SELECT processo_referencia
                        FROM processos_kanban
                        WHERE numero_duimp = ? OR numero_duimp LIKE ?
                        LIMIT 1
                    ''', (numero, f'%{numero}%'))
                    row = cursor.fetchone()
                    if row:
                        processo_ref_final = row['processo_referencia']
                    else:
                        # Buscar em processo_documentos
                        cursor.execute('''
                            SELECT processo_referencia
                            FROM processo_documentos
                            WHERE numero_documento = ? AND tipo_documento = 'DUIMP'
                            LIMIT 1
                        ''', (numero,))
                        row = cursor.fetchone()
                        if row:
                            processo_ref_final = row['processo_referencia']
                    
                    conn.close()
                except Exception as e:
                    logger.debug(f'Erro ao buscar processo_referencia para DUIMP {numero}: {e}')
            
            # ✅ CORREÇÃO: Se dados_capa não estiver disponível, tentar consultar Portal Único novamente
            if not dados_capa:
                logger.info(f'⚠️ Dados da capa não disponíveis. Tentando consultar Portal Único novamente para DUIMP {numero}/{versao}...')
                try:
                    # Tentar consultar Portal Único novamente
                    status_capa, dados_capa = self.consultar_duimp_portal(numero, versao, ambiente)
                    if status_capa == 200 and dados_capa:
                        logger.info(f'✅ Consulta ao Portal Único bem-sucedida na segunda tentativa para DUIMP {numero}/{versao}')
                        # Se conseguiu consultar a capa, tentar consultar itens também
                        if not dados_itens:
                            itens = dados_capa.get('itens', [])
                            if isinstance(itens, list):
                                dados_itens = []
                                for item in itens:
                                    if isinstance(item, dict):
                                        indice = item.get('indice') or item.get('numero')
                                        if indice:
                                            status_item, dados_item = self.consultar_itens_duimp_portal(
                                                numero, versao, indice, ambiente
                                            )
                                            if status_item == 200 and isinstance(dados_item, dict):
                                                dados_itens.append(dados_item)
                    else:
                        logger.warning(f'⚠️ Segunda tentativa de consulta ao Portal Único também falhou para DUIMP {numero}/{versao}')
                        return {
                            'sucesso': False,
                            'erro': 'Dados da capa não disponíveis. Não foi possível consultar o Portal Único.',
                            'resposta': '❌ Não foi possível gerar o PDF: dados da capa não estão disponíveis. A consulta ao Portal Único falhou. Tente novamente mais tarde.'
                        }
                except Exception as e:
                    logger.error(f'❌ Erro ao tentar consultar Portal Único novamente para DUIMP {numero}/{versao}: {e}', exc_info=True)
                    return {
                        'sucesso': False,
                        'erro': f'Erro ao consultar Portal Único: {str(e)}',
                        'resposta': f'❌ Não foi possível gerar o PDF: erro ao consultar Portal Único. Tente novamente mais tarde.'
                    }
            
            # Verificar novamente se dados_capa está disponível após tentativa
            if not dados_capa:
                return {
                    'sucesso': False,
                    'erro': 'Dados da capa não disponíveis. Não foi possível consultar o Portal Único.',
                    'resposta': '❌ Não foi possível gerar o PDF: dados da capa não estão disponíveis. Tente novamente mais tarde.'
                }
            
            # 2. Preparar dados para o template (mesma estrutura do Projeto-DUIMP)
            # Normalizar estrutura: garantir que dados_capa tem a estrutura esperada
            duimp_body = dados_capa.copy()
            
            # Adicionar itens detalhados
            if dados_itens:
                # O template espera items_details, mas também precisa itens com índices
                duimp_body['items_details'] = dados_itens
                # Garantir que há lista de itens
                if 'itens' not in duimp_body or not isinstance(duimp_body['itens'], list):
                    duimp_body['itens'] = []
                    for item in dados_itens:
                        indice = item.get('indice') or item.get('numero') or item.get('identificacao', {}).get('indice')
                        if indice:
                            duimp_body['itens'].append({'indice': indice})
            
            # 3. Criar diretório downloads se não existir
            downloads_dir = Path(__file__).parent.parent / 'downloads'
            downloads_dir.mkdir(exist_ok=True)
            
            # 4. Renderizar HTML
            try:
                # Importar app para ter acesso ao render_template com contexto
                from app import app
                
                # Renderizar template com contexto (safe_dict já está disponível via context_processor)
                # Passar processo_referencia para o template se disponível
                with app.app_context():
                    html = render_template('extrato_duimp.html', 
                                         duimp=duimp_body, 
                                         processo_referencia=processo_ref_final)
            except Exception as e:
                logger.error(f'Erro ao renderizar template HTML: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': f'Erro ao renderizar template: {str(e)}',
                    'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
                }
            
            # 5. Gerar PDF usando xhtml2pdf
            try:
                from xhtml2pdf import pisa
            except ImportError:
                return {
                    'sucesso': False,
                    'erro': 'Biblioteca xhtml2pdf não está instalada',
                    'resposta': '❌ Erro: Biblioteca xhtml2pdf não está instalada. Execute: pip install xhtml2pdf'
                }
            
            # Nome do arquivo
            nome_arquivo = f'Extrato-DUIMP-{numero}-Versao-{versao}.pdf'
            caminho_arquivo = downloads_dir / nome_arquivo
            
            # Gerar PDF
            with open(caminho_arquivo, 'wb') as arquivo_pdf:
                # Converter HTML para PDF
                status_pdf = pisa.CreatePDF(io.StringIO(html), dest=arquivo_pdf, encoding='utf-8')
                
                if status_pdf.err:
                    logger.error(f'Erro ao gerar PDF: {status_pdf.err}')
                    # Tentar remover arquivo se foi criado parcialmente
                    if caminho_arquivo.exists():
                        try:
                            caminho_arquivo.unlink()
                        except:
                            pass
                    return {
                        'sucesso': False,
                        'erro': f'Erro ao gerar PDF: {status_pdf.err}',
                        'resposta': f'❌ Erro ao gerar PDF: {status_pdf.err}'
                    }
            
            # 6. Retornar sucesso com caminho relativo
            # A rota /api/download/<path:filename> aceita "downloads/nome.pdf" ou apenas "nome.pdf"
            caminho_relativo = f'downloads/{nome_arquivo}'
            
            logger.info(f'✅ PDF gerado com sucesso: {nome_arquivo}')
            
            return {
                'sucesso': True,
                'caminho_arquivo': caminho_relativo,  # Inclui "downloads/" para compatibilidade
                'nome_arquivo': nome_arquivo,
                'numero': numero,
                'versao': versao,
                'resposta': f'✅ PDF gerado com sucesso!\n\n📄 **Arquivo:** {nome_arquivo}\n🔗 **Link:** /api/download/{caminho_relativo}'
            }
            
        except Exception as e:
            logger.error(f'Erro ao gerar PDF da DUIMP: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
            }

