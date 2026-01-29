"""
Serviço para geração de extrato PDF da DI.

Estrutura modular para evitar código monolítico.
Separa responsabilidades:
- Consulta ao Integra Comex (Serpro) - API bilhetada
- Busca de dados no banco
- Geração de PDF
"""
import logging
import json
import time
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class DiPdfService:
    """
    Serviço para operações relacionadas a extrato PDF de DI.
    
    Responsabilidades:
    1. Buscar número da DI no banco
    2. Consultar dados da DI no Integra Comex (Serpro) - API bilhetada
    3. Gerar PDF do extrato
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
            for arquivo in self.downloads_dir.glob('Extrato-DI-*.pdf'):
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
    
    def buscar_di_banco(self, processo_referencia: Optional[str] = None, numero_di: Optional[str] = None) -> Optional[str]:
        """
        Busca número da DI no banco de dados.
        
        ✅ MELHORIA: Usa obter_dados_documentos_processo como primeira opção (já busca em múltiplas fontes incluindo SQL Server)
        
        Busca em múltiplas fontes:
        1. obter_dados_documentos_processo (busca em Kanban + processo_documentos + SQL Server) - PRIORIDADE
        2. Tabela processos_kanban (campo numero_di) - direto
        3. Tabela dis_cache - por processo_referencia ou numero_di
        4. SQL Server direto (fallback adicional)
        
        Args:
            processo_referencia: Número do processo (ex: VDM.0003/25)
            numero_di: Número da DI diretamente (ex: 2524635120 ou "25/0727581-1")
        
        Returns:
            Número da DI normalizado (str) ou None se não encontrado
        """
        def normalizar_numero_di(numero_di_raw: str) -> str:
            """
            Normaliza número da DI para formato da API.
            Aceita formatos: "25/0727581-1", "2507275811", "25-0727581-1", etc.
            Retorna formato numérico sem formatação (ex: "2507275811")
            """
            if not numero_di_raw:
                return None
            
            # Remover espaços e caracteres especiais
            numero_limpo = numero_di_raw.strip().replace('/', '').replace('-', '').replace(' ', '').replace('.', '')
            
            # Se ainda tem letras ou outros caracteres, retornar como está (pode ser formato especial)
            if not numero_limpo.isdigit():
                return numero_di_raw.strip()  # Retornar original se não for só números
            
            return numero_limpo
        
        try:
            import sqlite3
            from db_manager import get_db_connection, obter_dados_documentos_processo, buscar_di_cache
            
            # Se numero_di foi fornecido diretamente, normalizar e verificar se existe no cache
            if numero_di:
                numero_di_normalizado = normalizar_numero_di(numero_di)
                if numero_di_normalizado:
                    di_cache = buscar_di_cache(numero_di=numero_di_normalizado)
                    if di_cache:
                        logger.info(f'DI encontrada no cache: {numero_di_normalizado}')
                        return numero_di_normalizado
            
            # Se processo_referencia foi fornecido, buscar DI vinculada
            if processo_referencia:
                # ✅ PRIORIDADE 1: Usar ProcessoRepository (busca em SQLite → API Kanban → SQL Server)
                try:
                    logger.debug(f'Buscando DI via ProcessoRepository para {processo_referencia}...')
                    from services.processo_repository import ProcessoRepository
                    repositorio = ProcessoRepository()
                    processo_dto = repositorio.buscar_por_referencia(processo_referencia.upper())
                    
                    if processo_dto and processo_dto.numero_di:
                        numero_di_encontrado = processo_dto.numero_di
                        # Normalizar número da DI
                        numero_di_normalizado = normalizar_numero_di(numero_di_encontrado)
                        if numero_di_normalizado:
                            logger.info(f'✅ DI encontrada via ProcessoRepository para {processo_referencia}: {numero_di_encontrado} → {numero_di_normalizado} (fonte: {processo_dto.fonte})')
                            return numero_di_normalizado
                except Exception as e:
                    logger.warning(f'Erro ao buscar via ProcessoRepository: {e}')
                
                # ✅ PRIORIDADE 2: Usar obter_dados_documentos_processo (busca em processo_documentos)
                try:
                    logger.debug(f'Buscando DI via obter_dados_documentos_processo para {processo_referencia}...')
                    dados_docs = obter_dados_documentos_processo(processo_referencia)
                    
                    if dados_docs:
                        dis = dados_docs.get('dis', [])
                        if dis and len(dis) > 0:
                            di = dis[0]
                            numero_di_encontrado = di.get('numero_di', '') or di.get('numero', '')
                            
                            if numero_di_encontrado:
                                # Normalizar número da DI
                                numero_di_normalizado = normalizar_numero_di(numero_di_encontrado)
                                if numero_di_normalizado:
                                    logger.info(f'✅ DI encontrada via obter_dados_documentos_processo para {processo_referencia}: {numero_di_encontrado} → {numero_di_normalizado}')
                                    return numero_di_normalizado
                except Exception as e:
                    logger.warning(f'Erro ao buscar via obter_dados_documentos_processo: {e}')
                
                # 2. Buscar em processos_kanban (campo numero_di) - busca direta
                try:
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT numero_di
                        FROM processos_kanban
                        WHERE processo_referencia = ? 
                          AND numero_di IS NOT NULL 
                          AND numero_di != '' 
                          AND numero_di != '/ -'
                        LIMIT 1
                    ''', (processo_referencia,))
                    
                    row = cursor.fetchone()
                    if row:
                        numero_di_encontrado = row['numero_di'].strip()
                        if numero_di_encontrado:
                            conn.close()
                            numero_di_normalizado = normalizar_numero_di(numero_di_encontrado)
                            if numero_di_normalizado:
                                logger.info(f'✅ DI encontrada em processos_kanban para {processo_referencia}: {numero_di_encontrado} → {numero_di_normalizado}')
                                return numero_di_normalizado
                    
                    conn.close()
                except Exception as e:
                    logger.warning(f'Erro ao buscar em processos_kanban: {e}')
                
                # 3. Buscar em dis_cache por processo_referencia
                try:
                    conn = get_db_connection()
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT numero_di
                        FROM dis_cache
                        WHERE processo_referencia = ?
                        ORDER BY atualizado_em DESC
                        LIMIT 1
                    ''', (processo_referencia,))
                    
                    row = cursor.fetchone()
                    if row:
                        numero_di_encontrado = row['numero_di']
                        if numero_di_encontrado:
                            conn.close()
                            numero_di_normalizado = normalizar_numero_di(numero_di_encontrado)
                            if numero_di_normalizado:
                                logger.info(f'✅ DI encontrada em dis_cache para {processo_referencia}: {numero_di_encontrado} → {numero_di_normalizado}')
                                return numero_di_normalizado
                    
                    conn.close()
                except Exception as e:
                    logger.warning(f'Erro ao buscar em dis_cache: {e}')
                
                # 4. Tentar buscar no SQL Server diretamente (fallback adicional)
                try:
                    logger.debug(f'Tentando buscar DI no SQL Server diretamente para {processo_referencia}...')
                    from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                    
                    processo_consolidado = buscar_processo_consolidado_sql_server(processo_referencia)
                    if processo_consolidado and processo_consolidado.get('di'):
                        di_data = processo_consolidado['di']
                        numero = di_data.get('numero')
                        
                        if numero:
                            numero_di_normalizado = normalizar_numero_di(str(numero))
                            if numero_di_normalizado:
                                logger.info(f'✅ DI encontrada no SQL Server para {processo_referencia}: {numero} → {numero_di_normalizado}')
                                return numero_di_normalizado
                except Exception as e:
                    logger.debug(f'Erro ao buscar DI no SQL Server para {processo_referencia}: {e}')
            
            logger.warning(f'⚠️ DI não encontrada em nenhuma fonte para processo {processo_referencia or "N/A"} ou número {numero_di or "N/A"}')
            return None
            
        except Exception as e:
            logger.error(f'Erro ao buscar DI no banco: {e}', exc_info=True)
            return None
    
    def consultar_di_integracomex(self, numero_di: str) -> Tuple[int, Any]:
        """
        Consulta dados da DI no Integra Comex (Serpro) - API bilhetada.
        
        ⚠️ ATENÇÃO: Esta API é BILHETADA (paga por consulta).
        
        Args:
            numero_di: Número da DI (ex: 2524635120)
        
        Returns:
            Tuple (status_code, response_body)
        """
        try:
            from utils.integracomex_proxy import call_integracomex
            import os
            
            # ✅ Base URL específica para DI (produção por padrão)
            env = os.getenv('INTEGRACOMEX_ENV', '').lower().strip()
            is_validacao = env == 'val' or env == 'validacao' or env == 'homologacao'
            
            # Verificar se há base URL específica para DI configurada
            di_base_url = os.getenv('INTEGRACOMEX_DI_BASE_URL', '').strip()
            if not di_base_url:
                # ✅ PADRÃO: PRODUÇÃO (não validação)
                if is_validacao:
                    di_base_url = 'https://gateway.apiserpro.serpro.gov.br/integra-comex-di-hom/v1'
                else:
                    di_base_url = 'https://gateway.apiserpro.serpro.gov.br/integra-comex-di/v1'
            
            logger.info(f'Consultando DI {numero_di} via Integra Comex DI (base: {di_base_url})...')
            
            # ✅ Endpoint oficial: GET /declaracao-importacao/{numeroDi}
            # ✅ CRÍTICO: Indicar que API pública foi verificada antes (sempre verificamos antes de chegar aqui)
            try:
                status, body = call_integracomex(
                    f'/declaracao-importacao/{numero_di}',
                    method='GET',
                    base_url_override=di_base_url,
                    usou_api_publica_antes=True  # ✅ SEMPRE verificamos API pública antes
                )
                
                logger.info(f'Resposta da API Integra Comex: status={status}')
                return status, body
            except RuntimeError as e:
                # ✅ Tratar erro de duplicata
                if str(e).startswith('DUPLICATA:'):
                    logger.warning(f'⚠️ {str(e)} - Retornando erro de duplicata.')
                    return 429, {'erro': 'DUPLICATA', 'mensagem': str(e)}
                raise
            except Exception as e:
                error_msg = str(e)
                logger.warning(f'Erro ao chamar call_integracomex: {error_msg}')
                return 500, {'erro': 'Erro ao consultar Integra Comex', 'detalhes': error_msg}
            
        except SystemExit as e:
            # ✅ Erro de configuração (credenciais faltando)
            error_msg = str(e)
            logger.error(f'Erro de configuração Integra Comex: {error_msg}')
            if 'INTEGRACOMEX_CONSUMER_KEY' in error_msg or 'CONSUMER_KEY' in error_msg:
                return 500, {
                    'erro': 'Credenciais não configuradas',
                    'detalhes': 'INTEGRACOMEX_CONSUMER_KEY não está definida no .env. Configure as credenciais Integra Comex no arquivo .env.'
                }
            elif 'INTEGRACOMEX_CONSUMER_SECRET' in error_msg or 'CONSUMER_SECRET' in error_msg:
                return 500, {
                    'erro': 'Credenciais não configuradas',
                    'detalhes': 'INTEGRACOMEX_CONSUMER_SECRET não está definida no .env. Configure as credenciais Integra Comex no arquivo .env.'
                }
            return 500, {'erro': 'Erro de configuração', 'detalhes': error_msg}
        except Exception as e:
            logger.error(f'Erro ao consultar DI {numero_di} no Integra Comex: {e}', exc_info=True)
            error_msg = str(e)
            if 'No module named' in error_msg:
                return 500, {'erro': 'Módulo não encontrado', 'detalhes': error_msg}
            elif 'cert' in error_msg.lower() or 'pfx' in error_msg.lower():
                return 500, {'erro': 'Certificado não configurado', 'detalhes': 'Certificado .pfx necessário para autenticação'}
            elif 'CONSUMER_KEY' in error_msg or 'CONSUMER_SECRET' in error_msg:
                return 500, {
                    'erro': 'Credenciais Integra Comex não configuradas',
                    'detalhes': 'Configure INTEGRACOMEX_CONSUMER_KEY e INTEGRACOMEX_CONSUMER_SECRET no arquivo .env'
                }
            return 500, {'erro': error_msg}
    
    def obter_dados_completos_di(self, processo_referencia: Optional[str] = None, numero_di: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém dados completos da DI (banco + Integra Comex).
        
        Args:
            processo_referencia: Número do processo (ex: VDM.0003/25) - opcional
            numero_di: Número da DI diretamente (ex: 2524635120) - opcional
        
        Returns:
            Dict com resultado da consulta:
            {
                'sucesso': bool,
                'numero': str,
                'dados_di': dict,
                'erro': str (se houver)
            }
        """
        # Validar que pelo menos um dos dois foi fornecido
        if not processo_referencia and not numero_di:
            return {
                'sucesso': False,
                'erro': 'processo_referencia ou numero_di é obrigatório',
                'resposta': '❌ Referência de processo ou número da DI é obrigatório.'
            }
        
        # 1. Buscar número da DI no banco
        numero_di_encontrado = None
        
        if numero_di:
            numero_di_encontrado = numero_di
        else:
            # Buscar pelo processo_referencia
            numero_di_encontrado = self.buscar_di_banco(processo_referencia=processo_referencia)
            if not numero_di_encontrado:
                return {
                    'sucesso': False,
                    'erro': f'DI não encontrada no banco para o processo {processo_referencia}',
                    'resposta': f'❌ DI não encontrada no banco de dados para o processo {processo_referencia}.'
                }
        
        logger.info(f'DI encontrada: {numero_di_encontrado}')
        
        # ✅ REGRA CRÍTICA: Para EXTRATO, SEMPRE consultar API oficial (ignorar cache)
        # NÃO usar cache - sempre buscar direto do endpoint oficial (Integra Comex)
        # Isso garante dados atualizados e completos para o PDF
        
        logger.info(f'⚠️ EXTRATO: Ignorando cache. Consultando Integra Comex (endpoint oficial) para DI {numero_di_encontrado}...')
        status_api, body_response = self.consultar_di_integracomex(numero_di_encontrado)
        
        if status_api == 200 and isinstance(body_response, dict):
            dados_di_api = body_response
            
            # Salvar no cache SQLite para uso futuro (mas não usar para extrato)
            try:
                from db_manager import salvar_di_cache
                salvar_di_cache(
                    numero_di=numero_di_encontrado,
                    json_completo=body_response,
                    processo_referencia=processo_referencia
                )
                logger.info(f'✅ DI {numero_di_encontrado} salva no cache SQLite')
            except Exception as e:
                logger.warning(f'Erro ao salvar DI no cache SQLite: {e}')
            
            # ✅ NOVO: Atualizar banco SQL Server (mAIke_assistente) via DocumentoHistoricoService
            try:
                # Extrair dados relevantes do payload para atualizar banco
                dados_gerais = dados_di_api.get('dadosGerais', {}) if isinstance(dados_di_api, dict) else {}
                dados_despacho = dados_di_api.get('dadosDespacho', {}) if isinstance(dados_di_api, dict) else {}
                
                # Montar payload similar ao ProcessoStatusV2Service
                payload_doc = {
                    "numero": numero_di_encontrado,
                    "situacaoDi": dados_gerais.get('situacaoDI', '') if isinstance(dados_gerais, dict) else '',
                    "dataHoraSituacaoDi": dados_gerais.get('dataHoraSituacaoDi', '') if isinstance(dados_gerais, dict) else '',
                    "situacaoEntregaCarga": dados_gerais.get('situacaoEntregaCarga', '') if isinstance(dados_gerais, dict) else '',
                    "canalSelecaoParametrizada": dados_despacho.get('canalSelecaoParametrizada', '') if isinstance(dados_despacho, dict) else '',
                    "dataHoraRegistro": dados_despacho.get('dataHoraRegistro', '') if isinstance(dados_despacho, dict) else '',
                    "dataHoraDesembaraco": dados_despacho.get('dataHoraDesembaraco', '') if isinstance(dados_despacho, dict) else '',
                }
                
                # Atualizar banco SQL Server
                from services.documento_historico_service import DocumentoHistoricoService
                svc_doc = DocumentoHistoricoService()
                svc_doc.detectar_e_gravar_mudancas(
                    numero_documento=str(numero_di_encontrado),
                    tipo_documento="DI",
                    dados_novos=payload_doc,
                    fonte_dados="INTEGRACOMEX_API",
                    api_endpoint=f"/declaracao-importacao/{numero_di_encontrado}",
                    processo_referencia=processo_referencia,
                )
                logger.info(f'✅ DI {numero_di_encontrado} atualizada no banco SQL Server (mAIke_assistente)')
            except Exception as e:
                logger.debug(f'Erro ao atualizar DI no banco SQL Server: {e}')
            
            return {
                'sucesso': True,
                'numero': numero_di_encontrado,
                'dados_di': dados_di_api,  # Dados completos da API oficial
                'fonte': 'api_bilhetada',
                'resposta': f'✅ DI {numero_di_encontrado} consultada com sucesso (API bilhetada).'
            }
        
        # Tratar erros
        erro_msg = body_response.get('erro') if isinstance(body_response, dict) else 'DI não encontrada'
        if status_api == 429:
            return {
                'sucesso': False,
                'erro': 'DUPLICATA',
                'resposta': f'⚠️ Esta DI já foi consultada recentemente. Aguarde alguns minutos antes de consultar novamente.'
            }
        elif status_api == 404:
            return {
                'sucesso': False,
                'erro': 'DI_NAO_ENCONTRADA',
                'resposta': f'❌ DI {numero_di_encontrado} não encontrada na API Integra Comex.'
            }
        else:
            return {
                'sucesso': False,
                'erro': erro_msg,
                'resposta': f'❌ Erro ao consultar DI {numero_di_encontrado}: {erro_msg}'
            }
    
    def _gerar_pdf_di_com_dados(self, dados_di: Dict[str, Any], numero_di: str, processo_referencia: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera PDF do extrato da DI usando dados já consultados (evita consulta duplicada).
        
        Args:
            dados_di: Dados da DI já consultados (dict)
            numero_di: Número da DI
            processo_referencia: Número do processo (opcional)
        
        Returns:
            Dict com resultado da geração do PDF
        """
        try:
            from flask import render_template
            import io
            from pathlib import Path
            
            numero = numero_di
            
            if not dados_di:
                return {
                    'sucesso': False,
                    'erro': 'Dados da DI não disponíveis',
                    'resposta': '❌ Não foi possível gerar o PDF: dados da DI não estão disponíveis.'
                }
            
            # Buscar processo_referencia se não foi fornecido diretamente
            processo_ref_final = processo_referencia
            if not processo_ref_final:
                # Tentar buscar no banco usando numero_di
                try:
                    from db_manager import obter_processo_por_documento
                    processo_encontrado = obter_processo_por_documento('DI', numero)
                    if processo_encontrado:
                        processo_ref_final = processo_encontrado
                except Exception as e:
                    logger.debug(f'Erro ao buscar processo_referencia para DI {numero}: {e}')
            
            downloads_dir = Path(__file__).parent.parent / 'downloads'
            downloads_dir.mkdir(exist_ok=True)
            
            # ✅ NOVO (26/01/2026): Carregar logo da Receita Federal em base64
            logo_base64 = None
            try:
                logo_path = Path(__file__).parent.parent / 'static' / 'logo-receita-federal.png'
                if logo_path.exists():
                    import base64
                    with open(logo_path, 'rb') as f:
                        logo_data = base64.b64encode(f.read()).decode('utf-8')
                        logo_base64 = f'data:image/png;base64,{logo_data}'
                        logger.debug('✅ Logo da Receita Federal carregado em base64')
                else:
                    logger.debug('⚠️ Logo da Receita Federal não encontrado em static/logo-receita-federal.png')
            except Exception as e:
                logger.warning(f'⚠️ Erro ao carregar logo: {e}')
            
            # Renderizar HTML usando template específico
            try:
                from app import app
                
                with app.app_context():
                    html = render_template(
                        'extrato_di.html',
                        di=dados_di,
                        processo_referencia=processo_ref_final,
                        logo_receita_federal=logo_base64
                    )
            except Exception as e:
                logger.error(f'Erro ao renderizar HTML: {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': f'Erro ao renderizar HTML: {str(e)}',
                    'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
                }
            
            # Gerar PDF usando xhtml2pdf
            try:
                from xhtml2pdf import pisa
            except ImportError:
                return {
                    'sucesso': False,
                    'erro': 'Biblioteca xhtml2pdf não está instalada',
                    'resposta': '❌ Erro: Biblioteca xhtml2pdf não está instalada.'
                }
            
            # Nome do arquivo
            nome_arquivo = f'Extrato-DI-{numero}.pdf'
            caminho_arquivo = downloads_dir / nome_arquivo
            
            # Gerar PDF
            with open(caminho_arquivo, 'wb') as arquivo_pdf:
                status_pdf = pisa.CreatePDF(io.StringIO(html), dest=arquivo_pdf, encoding='utf-8')
                
                if status_pdf.err:
                    logger.error(f'Erro ao gerar PDF: {status_pdf.err}')
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
            
            # 5. Retornar sucesso
            caminho_relativo = f'downloads/{nome_arquivo}'
            
            logger.info(f'✅ PDF gerado com sucesso: {nome_arquivo}')
            
            return {
                'sucesso': True,
                'caminho_arquivo': caminho_relativo,
                'nome_arquivo': nome_arquivo,
                'numero': numero,
                'resposta': f'✅ PDF gerado com sucesso!\n\n📄 **Arquivo:** {nome_arquivo}'
            }
            
        except Exception as e:
            logger.error(f'Erro ao gerar PDF da DI: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
            }
    
    def gerar_pdf_di(self, processo_referencia: Optional[str] = None, numero_di: Optional[str] = None) -> Dict[str, Any]:
        """
        Gera PDF do extrato da DI (busca dados automaticamente se necessário).
        
        ⚠️ ATENÇÃO: Este método consulta a API novamente. Se você já tem os dados,
        use _gerar_pdf_di_com_dados() para evitar consulta duplicada.
        
        Args:
            processo_referencia: Número do processo (opcional)
            numero_di: Número da DI diretamente (opcional)
        
        Returns:
            Dict com resultado da geração do PDF
        """
        # Obter dados completos da DI
        dados = self.obter_dados_completos_di(processo_referencia=processo_referencia, numero_di=numero_di)
        
        if not dados.get('sucesso'):
            return {
                'sucesso': False,
                'erro': dados.get('erro', 'Erro ao obter dados da DI'),
                'resposta': dados.get('resposta', 'Erro ao obter dados da DI')
            }
        
        numero = dados['numero']
        dados_di = dados.get('dados_di', {})
        
        if not dados_di:
            return {
                'sucesso': False,
                'erro': 'Dados da DI não disponíveis',
                'resposta': '❌ Não foi possível gerar o PDF: dados da DI não estão disponíveis.'
            }
        
        # Usar método interno que aceita dados já consultados (evita duplicação)
        return self._gerar_pdf_di_com_dados(
            dados_di=dados_di,
            numero_di=numero,
            processo_referencia=processo_referencia
        )

