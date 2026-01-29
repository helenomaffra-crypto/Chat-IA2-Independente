"""
=============================================================================
🤖 CHAT IA INDEPENDENTE - APLICAÇÃO FLASK
=============================================================================
Aplicação Flask independente para o Chat IA, extraída do projeto DUIMP-PDF.

Esta aplicação fornece:
- Interface de chat conversacional com IA
- Integração com SQL Server (processos)
- Integração com APIs oficiais (Portal Único, Integra Comex)
- Sistema de tool calling com LLMs
=============================================================================
"""
from flask import Flask, render_template, request, jsonify, session
import os
import sys
import logging
import requests
import json
import re
from threading import Lock
from pathlib import Path
from utils.json_helpers import safe_json_loads, safe_json_dumps
from routes.mercante_routes import mercante_bp
from routes.system_routes import system_bp

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente do .env
def load_env_from_file(filepath: str = '.env') -> None:
    """Carrega variáveis de ambiente do arquivo .env"""
    # Tentar vários caminhos possíveis
    possible_paths = [
        Path(filepath),
        Path(__file__).parent / filepath,  # Relativo ao app.py
        Path(os.getcwd()) / filepath,
    ]
    
    for path in possible_paths:
        if path and path.exists():
            abs_path = path.absolute()
            try:
                with open(abs_path, 'r', encoding='utf-8') as env_file:
                    for line in env_file:
                        s = line.strip()
                        if not s or s.startswith('#') or '=' not in s:
                            continue
                        k, v = s.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
                logger.info(f"✅ Variáveis de ambiente carregadas do .env: {abs_path}")
                return
            except OSError as e:
                logger.warning(f"⚠️ Erro ao carregar .env de {abs_path}: {e}")
                continue
    
    # ✅ SILENCIAR AVISO NO DOCKER: Se já temos variáveis essenciais, não avisar que faltou o arquivo
    if os.getenv('DUIMP_AI_API_KEY') or os.getenv('SQL_PASSWORD'):
        logger.info("ℹ️ Arquivo .env não encontrado, mas variáveis de ambiente detectadas (Docker/Host).")
    else:
        logger.warning(f"⚠️ Arquivo .env não encontrado em nenhum dos caminhos: {possible_paths}")

# Carregar .env antes de criar o app
load_env_from_file()

# Criar aplicação Flask
app = Flask(__name__)

# Configurações
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

# Rotas por domínio (evita crescer app.py indefinidamente)
app.register_blueprint(mercante_bp)
app.register_blueprint(system_bp)


# =============================================================================
# TEMPLATE FILTERS (para extrato_duimp.html)
# =============================================================================
@app.template_filter('format_currency')
def format_currency(value):
    """Formata valor como moeda brasileira (R$)."""
    try:
        if value is None:
            return '—'
        # ✅ CORREÇÃO: Converter para string primeiro, depois para float (trata casos como "123.45" ou "123,45")
        if isinstance(value, str):
            # Remover espaços e tentar converter
            value = value.strip().replace(',', '.')
        valor = float(value)
        return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return str(value) if value else '—'

@app.template_filter('format_currency_usd')
def format_currency_usd(value):
    """Formata valor em dólar com ponto como separador de milhar e vírgula para decimais (ex: 9.600,00)."""
    try:
        if value is None:
            return '0,00'
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        valor = float(value)
        # Formato: 9.600,00 (ponto para milhar, vírgula para decimal)
        return f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return '0,00'

@app.template_filter('get_moeda_nome')
def get_moeda_nome(codigo_moeda):
    """Retorna nome da moeda baseado no código."""
    moedas = {
        '220': 'DOLAR DOS EUA',
        '220': 'DOLAR DOS ESTADOS UNIDOS',  # Mesmo código, nome alternativo
        '978': 'EURO',
        '986': 'REAL',
    }
    return moedas.get(str(codigo_moeda), 'DOLAR DOS EUA')  # Default USD

@app.template_filter('to_float')
def to_float(value):
    """Converte valor para float de forma segura."""
    try:
        if value is None:
            return 0.0
        if isinstance(value, str):
            value = value.strip().replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return 0.0

@app.template_filter('format_number')
def format_number(value, decimals=2):
    """Formata número com separador de milhares."""
    try:
        if value is None:
            return '—'
        valor = float(value)
        return f'{valor:,.{decimals}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return str(value) if value else '—'

@app.context_processor
def inject_template_helpers():
    """Injeta funções auxiliares nos templates."""
    def safe_dict(obj):
        """Garante que retorna um dict, mesmo se obj for string ou outro tipo."""
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, str) and obj.strip():
            s = obj.strip()
            if (s.startswith('{') and s.endswith('}')) or (s.startswith('[') and s.endswith(']')):
                try:
                    import json
                    parsed = json.loads(s)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception:
                    return {}
        return {}
    
    def is_dict(obj):
        """Verifica se objeto é dict."""
        return isinstance(obj, dict)
    
    return {'safe_dict': safe_dict, 'is_dict': is_dict}

# Porta do servidor (5000 é usada pelo AirPlay no macOS, usar 5001 como padrão)
PORT = int(os.getenv('PORT', '5001'))


# Inicializar banco de dados
def init_databases():
    """
    Inicializa bancos de dados (SQLite para cache).
    """
    try:
        # Importar db_manager aqui para evitar import circular
        from db_manager import init_db
        init_db()
        logger.info("✅ Banco de dados SQLite inicializado")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco de dados: {e}")


# Testar conexão SQL Server (não bloqueante)
def test_sql_server():
    """Testa conexão com SQL Server em background (não bloqueia inicialização)."""
    import threading
    
    def _test_async():
        """Testa conexão em thread separada."""
        try:
            from utils.sql_server_adapter import get_sql_adapter
            adapter = get_sql_adapter()
            if adapter is None:
                # ✅ Robustez: em macOS sem Node adapter / sem pyodbc, get_sql_adapter pode retornar None.
                # Não deve quebrar nem poluir log com "'NoneType' object has no attribute test_connection".
                logger.warning("⚠️ SQL Server adapter não disponível (nenhum driver/adapter configurado). Pulando teste de conexão.")
                return
            # ✅ CORREÇÃO: Usar timeout menor para não travar
            result = adapter.test_connection()
            if result.get('success'):
                database_name = adapter.database
                # ✅ NOVO: Mostrar qual banco está sendo usado (novo ou antigo)
                banco_tipo = "NOVO (mAIke_assistente)" if database_name.lower() == "maike_assistente" else f"ANTIGO ({database_name})"
                logger.info(f"✅ Conexão com SQL Server OK - Banco: {database_name} ({banco_tipo})")
            else:
                logger.warning(f"⚠️ Erro ao conectar SQL Server: {result.get('error')}")
        except Exception as e:
            logger.warning(f"⚠️ SQL Server não disponível: {e}")
    
    # Executar em thread separada para não bloquear inicialização
    thread = threading.Thread(target=_test_async, daemon=True)
    thread.start()
    logger.info("🔄 Teste de conexão SQL Server iniciado em background...")


# Instância global do ChatService
_chat_service = None

def get_chat_service():
    """Retorna instância singleton do ChatService."""
    global _chat_service
    if _chat_service is None:
        try:
            from services.chat_service import ChatService
            _chat_service = ChatService()
            logger.info("✅ ChatService inicializado")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ChatService: {e}")
            raise
    return _chat_service


# =============================================================================
# BACKGROUND SERVICES (Kanban auto-sync + scheduler)
# =============================================================================
_background_services_started = False
_background_services_lock = Lock()


def _should_autostart_background_services() -> bool:
    """
    Define se o processo deve iniciar rotinas em background automaticamente.

    - No Docker/Gunicorn, o bloco __main__ não roda, então precisamos autostart.
    - Em ambientes de dev/test (import do app), evitamos iniciar sem querer.
    """
    flag = os.getenv("AUTO_START_BACKGROUND_SERVICES")
    if flag is not None:
        return flag.strip().lower() == "true"

    # Heurística: dentro do container Docker
    try:
        if os.path.exists("/.dockerenv"):
            return True
    except Exception:
        pass

    # Heurística: alguns servidores WSGI setam SERVER_SOFTWARE
    try:
        if "gunicorn" in (os.getenv("SERVER_SOFTWARE", "").lower()):
            return True
    except Exception:
        pass

    return False


def _start_background_services(source: str) -> None:
    """
    Inicia sincronização automática do Kanban e notificações agendadas.
    Idempotente por processo (evita iniciar duas vezes).
    """
    global _background_services_started
    with _background_services_lock:
        if _background_services_started:
            logger.debug(f"ℹ️ Background services já iniciados (source={source})")
            return
        _background_services_started = True

    # Inicializar DB e teste SQL Server (não bloqueante)
    try:
        init_databases()
    except Exception as e:
        logger.warning(f"⚠️ Falha ao inicializar bancos na inicialização (source={source}): {e}", exc_info=True)

    try:
        test_sql_server()
    except Exception as e:
        logger.warning(f"⚠️ Falha ao iniciar teste SQL Server (source={source}): {e}", exc_info=True)

    # Sincronização automática do Kanban (SQLite cache) - padrão 5 min
    try:
        from services.processo_kanban_service import iniciar_sincronizacao_background
        intervalo_minutos = int(os.getenv("KANBAN_SYNC_INTERVAL_MINUTES", "5"))
        iniciar_sincronizacao_background(intervalo_segundos=intervalo_minutos * 60)
        logger.info(f"✅ Sincronização automática do Kanban iniciada (a cada {intervalo_minutos} min) (source={source})")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível iniciar sincronização automática do Kanban (source={source}): {e}", exc_info=True)

    # Notificações/Jobs agendados (RSS, monitoramento, TTS cleanup, etc.)
    try:
        from services.scheduled_notifications_service import ScheduledNotificationsService
        scheduled_notifications = ScheduledNotificationsService()
        scheduled_notifications.iniciar()
        # ✅ NOVO (26/01/2026): Verificar se realmente iniciou
        if scheduled_notifications.scheduler.running:
            logger.info(f"✅ Notificações agendadas iniciadas (source={source}) - scheduler rodando")
        else:
            logger.error(f"❌ ERRO CRÍTICO: Scheduler NÃO iniciou (source={source}) - tentando novamente...")
            # Tentar iniciar novamente
            try:
                scheduled_notifications.iniciar()
                if scheduled_notifications.scheduler.running:
                    logger.info(f"✅ Scheduler iniciado na segunda tentativa (source={source})")
                else:
                    logger.error(f"❌ ERRO CRÍTICO: Scheduler falhou mesmo na segunda tentativa (source={source})")
            except Exception as e2:
                logger.error(f"❌ ERRO ao tentar iniciar scheduler na segunda tentativa: {e2}", exc_info=True)
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO: Não foi possível iniciar notificações agendadas (source={source}): {e}", exc_info=True)


# ✅ Autostart em Docker/Gunicorn (onde __main__ não executa)
if __name__ != "__main__" and _should_autostart_background_services():
    _start_background_services(source="autostart")


# =============================================================================
# ROTAS
# =============================================================================

@app.route('/')
def index():
    """Página inicial - redireciona para chat."""
    return render_template('chat-ia-isolado.html')


@app.route('/chat-ia')
def chat_ia():
    """Página do Chat IA - interface isolada estilo WhatsApp."""
    return render_template('chat-ia-isolado.html')


@app.route('/api/legislacao/importar', methods=['POST'])
def importar_legislacao_endpoint():
    """Endpoint para importar legislação via texto colado."""
    try:
        data = request.get_json()
        tipo_ato = data.get('tipo_ato', '').strip()
        numero = data.get('numero', '').strip()
        ano = data.get('ano')
        sigla_orgao = data.get('sigla_orgao', '').strip() or None
        texto = data.get('texto', '').strip()
        
        # Validação
        if not tipo_ato or not numero or not ano or not texto:
            return jsonify({
                'sucesso': False,
                'erro': 'CAMPOS_OBRIGATORIOS',
                'mensagem': 'Tipo, número, ano e texto são obrigatórios'
            }), 400
        
        # Validar ano
        try:
            ano = int(ano)
            if ano < 1900 or ano > 2100:
                return jsonify({
                    'sucesso': False,
                    'erro': 'ANO_INVALIDO',
                    'mensagem': 'Ano deve ser entre 1900 e 2100'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'sucesso': False,
                'erro': 'ANO_INVALIDO',
                'mensagem': 'Ano inválido'
            }), 400
        
        # Importar usando o serviço
        from services.legislacao_service import LegislacaoService
        service = LegislacaoService()
        
        resultado = service.importar_ato_de_texto(
            tipo_ato=tipo_ato,
            numero=numero,
            ano=ano,
            sigla_orgao=sigla_orgao or '',
            texto_bruto=texto
        )
        
        if resultado.get('sucesso'):
            return jsonify({
                'sucesso': True,
                'legislacao_id': resultado.get('legislacao_id'),
                'trechos_importados': resultado.get('trechos_importados', 0),
                'mensagem': f'{tipo_ato} {numero}/{ano} importada com sucesso'
            }), 200
        else:
            return jsonify({
                'sucesso': False,
                'erro': resultado.get('erro', 'ERRO_DESCONHECIDO'),
                'mensagem': resultado.get('resposta', 'Erro ao importar legislação')
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Erro ao importar legislação: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INESPERADO',
            'mensagem': f'Erro inesperado: {str(e)}'
        }), 500


@app.route('/api/legislacao/<int:legislacao_id>/exportar-rag', methods=['POST'])
def exportar_legislacao_rag(legislacao_id: int):
    """
    Exporta uma legislação do SQLite para `legislacao_files/*.txt` (para File Search).

    ⚠️ Requer AssistantsService habilitado (por política do projeto).
    """
    try:
        from services.assistants_service import AssistantsService
        service = AssistantsService()
        if not service.enabled:
            return jsonify({
                'sucesso': False,
                'erro': 'ASSISTANTS_DESABILITADO',
                'mensagem': 'Assistants/File Search não está habilitado. Configure DUIMP_AI_ENABLED=true e DUIMP_AI_API_KEY.'
            }), 400

        caminho = service.exportar_legislacao_para_arquivo(legislacao_id)
        if not caminho:
            return jsonify({
                'sucesso': False,
                'erro': 'ERRO_EXPORTACAO',
                'mensagem': 'Não foi possível exportar a legislação para arquivo.'
            }), 500

        from pathlib import Path
        return jsonify({
            'sucesso': True,
            'mensagem': '✅ Exportado para arquivo (pronto para vetorizar).',
            'arquivo': caminho,
            'nome_arquivo': Path(caminho).name,
            'legislacao_id': legislacao_id,
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro ao exportar legislação {legislacao_id} para RAG: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INESPERADO',
            'mensagem': f'Erro inesperado: {str(e)}'
        }), 500


@app.route('/api/legislacao/<int:legislacao_id>/vetorizar-rag', methods=['POST'])
def vetorizar_legislacao_rag(legislacao_id: int):
    """
    Exporta + faz upload + adiciona ao File Search (incremental) para uma legislação específica.
    """
    try:
        from services.assistants_service import AssistantsService
        service = AssistantsService()
        resultado = service.vetorizar_legislacao(legislacao_id)
        status = 200 if resultado.get('sucesso') else 400
        return jsonify(resultado), status
    except Exception as e:
        logger.error(f"❌ Erro ao vetorizar legislação {legislacao_id}: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INESPERADO',
            'mensagem': f'Erro inesperado: {str(e)}'
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """Endpoint para chat com IA - comandos em linguagem natural."""
    try:
        data = request.get_json()
        mensagem = data.get('mensagem', '').strip()
        historico = data.get('historico', [])
        executar_acao = data.get('executar_acao', False)
        model = data.get('model', None)
        temperature = data.get('temperature', None)
        session_id = data.get('session_id') or request.remote_addr  # ID da sessão
        
        # ✅ NOVO: Adicionar session_id ao histórico para contexto persistente
        if historico:
            for item in historico:
                if isinstance(item, dict) and 'session_id' not in item:
                    item['session_id'] = session_id
        
        # Validar temperatura se fornecida
        if temperature is not None:
            try:
                temperature = float(temperature)
                if temperature < 0.0 or temperature > 2.0:
                    temperature = None
            except (ValueError, TypeError):
                temperature = None
        
        if not mensagem:
            return jsonify({
                'sucesso': False,
                'erro': 'MENSAGEM_VAZIA',
                'mensagem': 'Mensagem não pode ser vazia'
            }), 400
        
        # ✅ NOVO: Detectar pedido de ajuda (antes de processar)
        mensagem_lower = mensagem.lower().strip()
        pedido_ajuda = bool(
            re.search(r'\b(me\s+ajuda|preciso\s+de\s+ajuda|ajuda|help|instrucoes|instruções|como\s+usar|o\s+que\s+posso\s+fazer|o\s+que\s+você\s+faz)\b', mensagem_lower)
        )
        
        if pedido_ajuda:
            # Retornar instruções predefinidas
            instrucoes = """📋 **INSTRUÇÕES - O QUE POSSO FAZER:**

🔍 **CONSULTAS DE PROCESSOS:**
• "Como está o processo ALH.0168/25?"
• "Quais processos ALH temos?"
• "Mostre os processos desembaraçados"
• "Quais processos têm pendência?"

📄 **DUIMPs:**
• "Criar DUIMP para ALH.0168/25"
• "Tem DUIMP para o processo X?"
• "Quais processos têm DUIMP?"

📦 **DOCUMENTOS:**
• "Vincular CE 123456789012345 ao processo ALH.0168/25"
• "Extrato da DUIMP do processo X"
• "Status do CE 123456789012345"

📊 **DASHBOARD:**
• "O que temos pra hoje?"
• "Quais processos estão chegando hoje?"
• "Mostre as pendências ativas"

💡 **DICAS:**
• Você pode me perguntar em linguagem natural
• Use o número do processo (ex: ALH.0168/25) para consultas específicas
• Use a categoria (ex: ALH, VDM) para listar todos os processos
• Se precisar de mais ajuda, é só perguntar!

Como posso ajudá-lo agora?"""
            
            return jsonify({
                'sucesso': True,
                'resposta': instrucoes,
                'tool_calling': [],
                'contexto': {}
            })
        
        # Obter serviço de chat
        try:
            chat_service = get_chat_service()
        except Exception as e:
            logger.error(f"❌ Erro ao obter ChatService: {e}")
            return jsonify({
                'sucesso': False,
                'erro': 'SERVICO_INDISPONIVEL',
                'mensagem': f'Serviço de chat não disponível: {str(e)}'
            }), 500
        
        # ✅ NOVO: Verificar/obter nome do usuário e tratar mensagem especial
        nome_usuario = None
        mensagem_original = mensagem
        
        # Buscar nome do usuário se já existe
        try:
            from db_manager import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT nome FROM usuarios_chat WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if row and row[0]:
                nome_usuario = row[0]
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao buscar nome do usuário: {e}")
        
        # ✅ NOVO: Verificar se última resposta foi pedindo o nome (via histórico)
        ultima_resposta_pediu_nome = False
        if historico and len(historico) > 0:
            ultima_resposta = historico[-1].get('resposta', '')
            if 'qual é o seu nome' in ultima_resposta.lower() or 'seu nome' in ultima_resposta.lower():
                ultima_resposta_pediu_nome = True
        
        # Verificar se usuário está informando o nome (frases específicas OU resposta direta)
        nome_extraido = None
        
        # 1. Tentar extrair de frases específicas
        if mensagem.lower().startswith(('meu nome é', 'me chamo', 'eu sou', 'sou o', 'sou a')):
            match = re.search(r'(?:meu nome é|me chamo|eu sou|sou o|sou a)\s+([A-Za-zÀ-ÿ\s]+)', mensagem, re.IGNORECASE)
            if match:
                nome_extraido = match.group(1).strip()
        
        # 2. Se última resposta pediu nome E mensagem é curta (provavelmente só o nome)
        elif ultima_resposta_pediu_nome:
            # Mensagem curta (1-3 palavras) e não parece comando/pergunta
            palavras = mensagem.strip().split()
            palavras_comandos = ['quais', 'como', 'onde', 'quando', 'qual', 'tem', 'mostre', 'liste', 'status', 'processo', 'duimp', 'ce', 'cct']
            eh_comando = any(mensagem.lower().startswith(cmd) for cmd in palavras_comandos)
            
            if len(palavras) <= 3 and not eh_comando:
                # Verificar se parece um nome (apenas letras, sem números/caracteres especiais)
                if re.match(r'^[A-Za-zÀ-ÿ\s]+$', mensagem.strip()):
                    nome_extraido = mensagem.strip()
                    logger.info(f"✅ Nome detectado como resposta direta: {nome_extraido}")
        
        # Se extraiu um nome, salvar
        if nome_extraido:
            nome_usuario = nome_extraido
            try:
                from db_manager import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO usuarios_chat (session_id, nome, atualizado_em)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (session_id, nome_usuario))
                conn.commit()
                conn.close()
                logger.info(f"✅ Nome do usuário salvo: {nome_usuario} (session: {session_id})")
                
                # ✅ NOVO: Retornar resposta cordial após salvar o nome
                return jsonify({
                    'sucesso': True,
                    'resposta': f'Olá, {nome_usuario}! 👋\n\nEu sou a Maike, assistente de COMEX da Make Consultores. Prazer em conhecê-lo! Agora posso ajudá-lo com:\n- Consultar status de processos de importação\n- Criar DUIMPs\n- Verificar documentos e bloqueios\n- Responder perguntas sobre processos, CEs e CCTs\n\n💡 Se precisar de ajuda, é só pedir! Como posso ajudá-lo hoje?',
                    'tool_calling': [],
                    'nome_usuario': nome_usuario,
                    'contexto': {}
                })
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar nome do usuário: {e}")
        
        # ✅ NOVO: Verificar se última resposta perguntou sobre categoria desconhecida
        ultima_resposta_perguntou_categoria = False
        categoria_para_adicionar = None
        processo_ref_para_adicionar = None
        if historico and len(historico) > 0:
            ultima_resposta = historico[-1].get('resposta', '')
            if 'é uma categoria de processo?' in ultima_resposta.lower() or 'categoria desconhecida detectada' in ultima_resposta.lower():
                ultima_resposta_perguntou_categoria = True
                # Tentar extrair categoria da última resposta
                match_cat = re.search(r'Categoria desconhecida detectada: (\w+)', ultima_resposta)
                if match_cat:
                    categoria_para_adicionar = match_cat.group(1).upper()
                # Tentar extrair processo da última resposta
                match_proc = re.search(r'processo_referencia["\']?\s*:\s*["\']?([A-Z]{2,4}\.\d{4}/\d{2})', ultima_resposta)
                if not match_proc:
                    # Tentar extrair do contexto
                    processo_ref_para_adicionar = chat_service._extrair_processo_referencia(ultima_resposta)
        
        # ✅ NOVO: Se usuário confirmou que é categoria (sim, é, sim é, etc)
        if ultima_resposta_perguntou_categoria and categoria_para_adicionar:
            mensagem_lower = mensagem.lower().strip()
            confirmacoes = ['sim', 'é', 'sim é', 'sim, é', 'é sim', 'correto', 'certo', 'yes', 'y']
            if mensagem_lower in confirmacoes or mensagem_lower.startswith(('sim', 'é')):
                # Adicionar categoria ao banco
                try:
                    from db_manager import adicionar_categoria_processo
                    sucesso = adicionar_categoria_processo(categoria_para_adicionar, confirmada_por_usuario=True)
                    if sucesso:
                        logger.info(f"✅ Categoria {categoria_para_adicionar} adicionada ao sistema")
                        # Retornar mensagem de confirmação e processar a mensagem original novamente
                        resposta_confirmação = f'✅ **Categoria {categoria_para_adicionar} adicionada com sucesso!**\n\n'
                        resposta_confirmação += f'Agora posso reconhecer processos da categoria {categoria_para_adicionar}.\n\n'
                        
                        # Se tinha processo na mensagem original, processar novamente
                        resultado = {}  # ✅ Tipagem: evitar "possibly unbound"
                        if processo_ref_para_adicionar:
                            resposta_confirmação += f'Processando sua consulta sobre {processo_ref_para_adicionar}...\n\n'
                            # Processar mensagem original (com o processo)
                            resultado = chat_service.processar_mensagem(
                                mensagem=f'situacao do {processo_ref_para_adicionar}',
                                historico=historico,
                                nome_usuario=nome_usuario,
                                session_id=session_id  # ✅ NOVO: Passar session_id
                            )
                            resposta_confirmação += resultado.get('resposta', '')
                        else:
                            resposta_confirmação += 'Pode fazer suas consultas normalmente!'
                        
                        return jsonify({
                            'sucesso': True,
                            'resposta': resposta_confirmação,
                            'tool_calling': resultado.get('tool_calling', []) if processo_ref_para_adicionar else [],
                            'categoria_adicionada': categoria_para_adicionar,
                            'contexto': {}
                        })
                    else:
                        return jsonify({
                            'sucesso': False,
                            'erro': 'ERRO_AO_ADICIONAR_CATEGORIA',
                            'mensagem': f'Erro ao adicionar categoria {categoria_para_adicionar}'
                        }), 500
                except Exception as e:
                    logger.error(f"❌ Erro ao adicionar categoria: {e}")
                    return jsonify({
                        'sucesso': False,
                        'erro': 'ERRO_AO_ADICIONAR_CATEGORIA',
                        'mensagem': f'Erro ao adicionar categoria: {str(e)}'
                    }), 500
        
        # Verificar se é primeira vez (sem nome) e mensagem não é sobre nome
        if not nome_usuario and not ultima_resposta_pediu_nome:
            # Primeira vez - mensagem de boas-vindas da mAIke
            return jsonify({
                'sucesso': True,
                'resposta': 'Olá, eu sou a Maike, assistente de COMEX da Make Consultores. 👋 Antes de começarmos, qual é o seu nome?\n\n💡 Se precisar de ajuda, é só pedir!',
                'solicitar_nome': True,
                'tool_calling': [],
                'contexto': {}
            })
        
        # Processar mensagem
        try:
            resultado = chat_service.processar_mensagem(
                mensagem, 
                historico, 
                model=model, 
                temperature=temperature,
                nome_usuario=nome_usuario,  # ✅ Passar nome do usuário
                session_id=session_id  # ✅ NOVO: Passar session_id para contexto persistente
            )
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}", exc_info=True)
            return jsonify({
                'sucesso': False,
                'erro': 'ERRO_PROCESSAMENTO',
                'mensagem': f'Erro ao processar mensagem: {str(e)}'
            }), 500
        
        # ✅ NOVO: Salvar conversa importante no banco
        resposta_ia = resultado.get('resposta', '')
        tool_calling = resultado.get('tool_calling') or []  # Garantir que seja lista, não None
        importante = (
            resultado.get('processo_referencia') is not None or
            resultado.get('acao') is not None or
            any(tool.get('name') in ['consultar_status_processo', 'criar_duimp', 'listar_processos_por_situacao'] 
                for tool in tool_calling if isinstance(tool, dict))
        )
        
        # ✅ NOVO: Incluir _resultado_interno na resposta JSON (para recuperar estado de email, etc)
        resultado_interno = resultado.get('_resultado_interno', {})
        
        if importante or len(mensagem) > 50:  # Salvar conversas importantes ou longas
            try:
                from db_manager import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO conversas_chat 
                    (session_id, mensagem_usuario, resposta_ia, tipo_conversa, processo_referencia, importante)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    mensagem_original,
                    resposta_ia[:1000],  # Limitar tamanho
                    'consulta' if resultado.get('processo_referencia') else 'geral',
                    resultado.get('processo_referencia'),
                    1 if importante else 0
                ))
                conn.commit()
                conn.close()
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar conversa: {e}")
        
        # Preparar resposta
        resposta = {
            'sucesso': True,
            'resposta': resposta_ia,
            'tool_calling': resultado.get('tool_calling', []),
            'acao': resultado.get('acao'),
            'processo_referencia': resultado.get('processo_referencia'),
            'contexto': resultado.get('contexto', {}),
            'nome_usuario': nome_usuario,  # ✅ Incluir nome do usuário na resposta
            '_resultado_interno': resultado.get('_resultado_interno', {})  # ✅ NOVO: Incluir resultado interno para recuperar estado (email, etc)
        }
        
        # ✅ CRÍTICO: Se o contexto foi limpo, incluir flag para o frontend limpar o histórico também
        if resultado.get('contexto_limpo') or resultado.get('limpar_historico_frontend'):
            resposta['limpar_historico_frontend'] = True
            resposta['contexto_limpo'] = True
            logger.info(f"✅ Flag 'limpar_historico_frontend' incluída na resposta para sessão {session_id}")
        
        # Executar ação se solicitado
        acao_executada = None
        deve_executar = executar_acao or resultado.get('executar_automatico', False)
        
        if deve_executar and resultado.get('acao') == 'criar_duimp' and resultado.get('processo_referencia'):
            # Ação de criar DUIMP seria executada aqui
            # Por enquanto, apenas adicionar informação na resposta
            resposta['acao_pendente'] = {
                'tipo': 'criar_duimp',
                'processo_referencia': resultado.get('processo_referencia')
            }
            logger.info(f"📋 Ação de criar DUIMP detectada para processo {resultado.get('processo_referencia')}")
        
        return jsonify(resposta)
    
    except Exception as e:
        logger.error(f"❌ Erro no endpoint /api/chat: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': f'Erro interno do servidor: {str(e)}'
        }), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """Endpoint para chat com IA usando streaming (Server-Sent Events)."""
    try:
        from flask import Response, stream_with_context
        import json
        
        data = request.get_json()
        mensagem = data.get('mensagem', '').strip()
        historico = data.get('historico', [])
        model = data.get('model', None)
        temperature = data.get('temperature', None)
        session_id = data.get('session_id') or request.remote_addr
        
        # Validar temperatura se fornecida
        if temperature is not None:
            try:
                temperature = float(temperature)
                if temperature < 0.0 or temperature > 2.0:
                    temperature = None
            except (ValueError, TypeError):
                temperature = None
        
        if not mensagem:
            return jsonify({
                'sucesso': False,
                'erro': 'MENSAGEM_VAZIA',
                'mensagem': 'Mensagem não pode estar vazia'
            }), 400
        
        # Obter nome do usuário
        nome_usuario = None
        try:
            from db_manager import get_db_connection
            import sqlite3
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT nome FROM usuarios_chat WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                nome_usuario = row['nome']
        except Exception as e:
            logger.debug(f"Erro ao buscar nome do usuário: {e}")
        
        # Obter chat service
        chat_service = get_chat_service()
        if not chat_service:
            return jsonify({
                'sucesso': False,
                'erro': 'SERVICO_INDISPONIVEL',
                'mensagem': 'Serviço de chat não disponível'
            }), 500
        
        def generate():
            """Generator para streaming de chunks."""
            try:
                logger.info(f"🔄 [STREAM] Iniciando streaming para mensagem: {mensagem[:50]}...")
                chunk_count = 0
                
                # Processar mensagem com streaming
                for chunk_data in chat_service.processar_mensagem_stream(
                    mensagem,
                    historico,
                    model=model,
                    temperature=temperature,
                    nome_usuario=nome_usuario,
                    session_id=session_id
                ):
                    chunk_count += 1
                    chunk_text = chunk_data.get('chunk', '')
                    
                    # Log apenas para debug (pode ser muito verboso)
                    if chunk_text:
                        logger.debug(f"📦 [STREAM] Chunk {chunk_count}: {len(chunk_text)} chars - '{chunk_text[:30]}...'")
                    
                    # Formatar como Server-Sent Event
                    chunk_json = json.dumps(chunk_data, ensure_ascii=False)
                    sse_line = f"data: {chunk_json}\n\n"
                    
                    # ✅ CRÍTICO: Enviar imediatamente (sem buffer)
                    yield sse_line
                    
                    # Se terminou, parar
                    if chunk_data.get('done'):
                        logger.info(f"✅ [STREAM] Streaming concluído. Total de chunks: {chunk_count}")
                        break
                
            except Exception as e:
                logger.error(f"❌ Erro no streaming: {e}", exc_info=True)
                error_data = {
                    'chunk': f'\n\n❌ Erro: {str(e)}',
                    'done': True,
                    'error': str(e)
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Desabilitar buffering no nginx
                'Connection': 'keep-alive',  # Manter conexão aberta
                'Content-Type': 'text/event-stream; charset=utf-8'  # Tipo de conteúdo explícito
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Erro no endpoint de streaming: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_STREAMING',
            'mensagem': f'Erro ao processar streaming: {str(e)}'
        }), 500


@app.route('/api/chat/voice', methods=['POST'])
def chat_voice():
    """
    Endpoint para chat por voz:
    - Recebe um pequeno áudio (multipart/form-data)
    - Transcreve usando OpenAI
    - Reaproveita o ChatService para responder
    - Opcionalmente gera áudio TTS da resposta
    """
    try:
        # Arquivo de áudio pode vir como "audio" ou "audio_file"
        file_storage = request.files.get('audio') or request.files.get('audio_file')
        if not file_storage:
            return jsonify({
                'sucesso': False,
                'erro': 'AUDIO_NAO_ENCONTRADO',
                'mensagem': 'Nenhum arquivo de áudio foi enviado (campo "audio" ou "audio_file").'
            }), 400

        # Session id compatível com outros endpoints
        session_id = request.form.get('session_id') or request.remote_addr
        session_id = str(session_id or 'default')

        # Idioma opcional (padrão pt-BR)
        language = request.form.get('language') or 'pt'

        # Transcrever áudio com OpenAI
        try:
            from openai import OpenAI
        except ImportError:
            logger.error("❌ Biblioteca 'openai' não instalada para transcrição de áudio.")
            return jsonify({
                'sucesso': False,
                'erro': 'OPENAI_NAO_INSTALADO',
                'mensagem': "Biblioteca 'openai' não instalada no servidor."
            }), 500

        api_key = os.getenv('DUIMP_AI_API_KEY', '')
        if not api_key:
            logger.error("❌ DUIMP_AI_API_KEY não configurada para transcrição de áudio.")
            return jsonify({
                'sucesso': False,
                'erro': 'CHAVE_API_NAO_CONFIGURADA',
                'mensagem': 'Chave da API de IA não configurada (DUIMP_AI_API_KEY).'
            }), 500

        client = OpenAI(api_key=api_key, timeout=60.0)

        # Modelo de transcrição (configurável via .env)
        stt_model = os.getenv('OPENAI_STT_MODEL', 'gpt-4o-mini-transcribe')

        # A nova biblioteca openai-python espera um arquivo como bytes, IOBase, PathLike
        # ou uma tupla (filename, bytes, content_type). Aqui usamos a forma de tupla,
        # garantindo compatibilidade.
        try:
            try:
                file_storage.stream.seek(0)
            except Exception:
                pass
            file_bytes = file_storage.read()
            filename = getattr(file_storage, 'filename', None) or 'audio.webm'
            content_type = getattr(file_storage, 'mimetype', None) or 'audio/webm'

            file_param = (filename, file_bytes, content_type)

            transcription = client.audio.transcriptions.create(
                model=stt_model,
                file=file_param,
                language=language
            )
        except Exception as e:
            logger.error(f"❌ Erro ao transcrever áudio: {e}", exc_info=True)
            return jsonify({
                'sucesso': False,
                'erro': 'ERRO_TRANSCRICAO',
                'mensagem': f'Erro ao transcrever áudio: {str(e)}'
            }), 500

        # A API retorna objeto com atributo "text"
        texto_usuario = getattr(transcription, 'text', None) or ''
        texto_usuario = texto_usuario.strip()

        if not texto_usuario:
            return jsonify({
                'sucesso': False,
                'erro': 'TRANSCRICAO_VAZIA',
                'mensagem': 'Não foi possível entender o áudio enviado.'
            }), 400

        # Obter nome do usuário (igual ao streaming)
        nome_usuario = None
        try:
            from db_manager import get_db_connection
            import sqlite3
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT nome FROM usuarios_chat WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                nome_usuario = row['nome']
        except Exception as e:
            logger.debug(f"Erro ao buscar nome do usuário (voz): {e}")

        # Obter ChatService
        chat_service = get_chat_service()
        if not chat_service:
            return jsonify({
                'sucesso': False,
                'erro': 'SERVICO_INDISPONIVEL',
                'mensagem': 'Serviço de chat não disponível'
            }), 500

        # Processar mensagem transcrita (sem histórico adicional aqui)
        try:
            resultado_chat = chat_service.processar_mensagem(
                mensagem=texto_usuario,
                historico=[],
                nome_usuario=nome_usuario,
                session_id=session_id
            )
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem de voz: {e}", exc_info=True)
            return jsonify({
                'sucesso': False,
                'erro': 'ERRO_CHAT',
                'mensagem': f'Erro ao processar mensagem: {str(e)}'
            }), 500

        resposta_texto = (resultado_chat or {}).get('resposta', '') or ''

        # Opcional: gerar áudio TTS da resposta
        audio_url = None
        try:
            from services.tts_service import TTSService
            tts_service = TTSService()
            if tts_service.enabled and resposta_texto:
                audio_url = tts_service.gerar_audio(resposta_texto)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gerar áudio TTS para resposta de voz: {e}", exc_info=True)

        return jsonify({
            'sucesso': True,
            'texto_usuario': texto_usuario,
            'resposta': resposta_texto,
            'audio_url': audio_url,
            'resultado_chat': resultado_chat
        })

    except Exception as e:
        logger.error(f"❌ Erro no endpoint de voz /api/chat/voice: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_VOZ',
            'mensagem': f'Erro ao processar requisição de voz: {str(e)}'
        }), 500


@app.route('/api/chat/status', methods=['GET'])
def chat_status():
    """Endpoint para verificar status do serviço de chat."""
    try:
        from ai_service import get_ai_service
        ai_service = get_ai_service()
        
        return jsonify({
            'sucesso': True,
            'ia_habilitada': ai_service.enabled,
            'provedor': ai_service.provider if ai_service.enabled else None,
            'chat_disponivel': True
        })
    except Exception as e:
        logger.error(f"❌ Erro ao verificar status: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/api/chat/limpar-contexto', methods=['POST'])
def limpar_contexto_endpoint():
    """
    Endpoint para limpar contexto de sessão.
    
    Limpa todo o contexto persistente (processo_atual, categoria_atual, etc.)
    """
    try:
        data = request.get_json() or {}
        # ✅ Tipagem/robustez: garantir string (request.remote_addr pode ser None)
        session_id = str(data.get('session_id') or request.remote_addr or 'default')
        
        from services.context_service import limpar_contexto_sessao
        
        # Limpar todo o contexto
        sucesso = limpar_contexto_sessao(session_id)
        
        if sucesso:
            logger.info(f"✅ Contexto limpo para sessão {session_id}")
            return jsonify({
                'sucesso': True,
                'mensagem': 'Contexto limpo com sucesso'
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Erro ao limpar contexto'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Erro ao limpar contexto: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/api/chat/resumo-aprendizado', methods=['GET', 'POST'])
def resumo_aprendizado():
    """
    Endpoint para obter resumo de aprendizado de uma sessão.
    
    GET: Retorna resumo formatado
    POST: Aceita session_id no body
    """
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            session_id = str(data.get('session_id') or request.remote_addr or 'default')
        else:
            session_id = str(request.args.get('session_id') or request.remote_addr or 'default')
        
        from services.learning_summary_service import obter_resumo_aprendizado_sessao, formatar_resumo_aprendizado
        
        resumo = obter_resumo_aprendizado_sessao(session_id)
        
        if resumo.get('sucesso'):
            texto_formatado = formatar_resumo_aprendizado(resumo)
            return jsonify({
                'sucesso': True,
                'resposta': texto_formatado,
                'dados': resumo
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': resumo.get('erro', 'Erro desconhecido')
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Erro ao obter resumo de aprendizado: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/api/chat/briefing-dia', methods=['GET', 'POST'])
def briefing_dia():
    """
    Endpoint para obter briefing do dia com TTS integrado.
    
    Retorna:
    - texto: Texto do briefing
    - audio_url: URL do arquivo de áudio gerado (se TTS habilitado)
    - audio_base64: Áudio em base64 (alternativa)
    """
    try:
        # Obter parâmetros
        if request.method == 'POST':
            data = request.get_json() or {}
            categoria = data.get('categoria')
            modal = data.get('modal')
            gerar_audio = data.get('gerar_audio', True)
        else:
            categoria = request.args.get('categoria')
            modal = request.args.get('modal')
            gerar_audio = request.args.get('gerar_audio', 'true').lower() == 'true'
        
        # Obter dashboard do dia
        from services.chat_service import get_chat_service
        chat_service = get_chat_service()
        
        args_tool = {}
        if categoria:
            args_tool['categoria'] = categoria
        if modal:
            args_tool['modal'] = modal
        
        resultado = chat_service._executar_funcao_tool('obter_dashboard_hoje', args_tool)
        
        if not resultado.get('sucesso'):
            return jsonify({
                'sucesso': False,
                'erro': resultado.get('erro', 'Erro ao obter dashboard')
            }), 500
        
        texto_briefing = resultado.get('resposta', '')
        
        resposta = {
            'sucesso': True,
            'texto': texto_briefing,
            'audio_url': None,
            'audio_base64': None
        }
        
        # Gerar áudio se solicitado
        if gerar_audio and texto_briefing:
            try:
                from ai_service import get_ai_service
                ai_service = get_ai_service()
                
                # Verificar se TTS está disponível
                tts_model = os.getenv('OPENAI_TTS_MODEL', 'tts-1')
                tts_voice = os.getenv('OPENAI_TTS_VOICE', 'alloy')
                
                if ai_service.enabled:
                    try:
                        from openai import OpenAI
                        client = OpenAI(api_key=os.getenv('DUIMP_AI_API_KEY'))
                        
                        # Gerar áudio
                        response = client.audio.speech.create(
                            model=tts_model,
                            voice=tts_voice,
                            input=texto_briefing[:4000]  # Limitar tamanho do texto
                        )
                        
                        # Salvar arquivo temporário
                        import tempfile
                        import base64
                        from pathlib import Path
                        
                        # Criar diretório downloads/tts se não existir
                        downloads_dir = Path('downloads/tts')
                        downloads_dir.mkdir(parents=True, exist_ok=True)
                        
                        # Nome do arquivo baseado em hash do texto
                        import hashlib
                        texto_hash = hashlib.md5(texto_briefing.encode()).hexdigest()
                        audio_path = downloads_dir / f"{texto_hash}.mp3"
                        
                        # Salvar áudio
                        response.stream_to_file(str(audio_path))
                        
                        # Ler como base64
                        with open(audio_path, 'rb') as f:
                            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
                        
                        resposta['audio_url'] = f"/downloads/tts/{texto_hash}.mp3"
                        resposta['audio_base64'] = audio_base64
                        resposta['audio_format'] = 'mp3'
                        
                        logger.info(f"✅ Áudio gerado: {audio_path}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao gerar áudio: {e}")
                        # Continuar sem áudio
                        
            except Exception as e:
                logger.warning(f"⚠️ TTS não disponível: {e}")
                # Continuar sem áudio
        
        return jsonify(resposta)
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar briefing do dia: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/downloads/tts/<path:filename>', methods=['GET'])
def servir_audio_tts(filename):
    """Serve arquivos de áudio TTS gerados."""
    try:
        from flask import send_from_directory
        from pathlib import Path
        
        downloads_dir = Path('downloads/tts')
        if downloads_dir.exists() and (downloads_dir / filename).exists():
            return send_from_directory(str(downloads_dir), filename, mimetype='audio/mpeg')
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Arquivo de áudio não encontrado'
            }), 404
    except Exception as e:
        logger.error(f"❌ Erro ao servir áudio: {e}")
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'chat-ia-independente'
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Endpoint para retornar configurações do sistema (modelo atual, etc)."""
    try:
        # ✅ CORREÇÃO: Buscar modelo do .env com prioridade correta (OPENAI_MODEL_DEFAULT > DUIMP_AI_MODEL)
        # Isso garante que o modelo exibido no cabeçalho seja o mesmo que está sendo usado
        modelo_atual = os.getenv('OPENAI_MODEL_DEFAULT') or os.getenv('DUIMP_AI_MODEL') or 'gpt-5.1'
        
        return jsonify({
            'model': modelo_atual,
            'success': True
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter configuração: {e}")
        return jsonify({'error': str(e), 'model': 'gpt-3.5-turbo'}), 500


@app.route('/api/config/email', methods=['GET'])
def get_email_config():
    """Obtém configurações de email (sem senha por segurança)."""
    try:
        smtp_server = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        email_sender = os.getenv('EMAIL_SENDER', '')
        email_default_mailbox = os.getenv('EMAIL_DEFAULT_MAILBOX', '')
        
        return jsonify({
            'success': True,
            'config': {
                'smtp_server': smtp_server,
                'smtp_port': smtp_port,
                'email_sender': email_sender,
                # ✅ NOVO: Mailbox usada para leitura via Microsoft Graph
                'email_default_mailbox': email_default_mailbox,
                'configured': bool(email_sender and os.getenv('EMAIL_PASSWORD'))
            }
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter configuração de email: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/contas-bancarias', methods=['GET'])
def get_contas_bancarias():
    """
    Retorna lista de contas bancárias configuradas (BB e Santander).
    
    Returns:
        JSON com lista de contas disponíveis para sincronização
    """
    try:
        contas = []
        
        # Banco do Brasil - Conta 1
        bb_agencia = os.getenv('BB_TEST_AGENCIA') or os.getenv('BB_AGENCIA')
        bb_conta = os.getenv('BB_TEST_CONTA') or os.getenv('BB_CONTA')
        
        if bb_agencia and bb_conta:
            contas.append({
                'banco': 'BB',
                'nome': f'BB - Ag. {bb_agencia} - C/C {bb_conta}',
                'agencia': bb_agencia,
                'conta': bb_conta,
                'id': 'bb_conta1'
            })
            logger.debug(f"✅ BB Conta 1 adicionada: Ag. {bb_agencia} - C/C {bb_conta}")
        else:
            logger.debug(f"⚠️ BB Conta 1 não configurada: BB_TEST_AGENCIA={os.getenv('BB_TEST_AGENCIA')}, BB_TEST_CONTA={os.getenv('BB_TEST_CONTA')}")
        
        # Banco do Brasil - Conta 2
        bb_conta_2 = os.getenv('BB_TEST_CONTA_2') or os.getenv('BB_CONTA_2')
        if bb_agencia and bb_conta_2:
            contas.append({
                'banco': 'BB',
                'nome': f'BB - Ag. {bb_agencia} - C/C {bb_conta_2}',
                'agencia': bb_agencia,
                'conta': bb_conta_2,
                'id': 'bb_conta2'
            })
            logger.debug(f"✅ BB Conta 2 adicionada: Ag. {bb_agencia} - C/C {bb_conta_2}")
        else:
            logger.debug(f"⚠️ BB Conta 2 não configurada: BB_TEST_CONTA_2={os.getenv('BB_TEST_CONTA_2')}, BB_CONTA_2={os.getenv('BB_CONTA_2')}")
        
        # ✅ Santander - API é 1:1 (uma credencial = uma conta), já vinculada à conta configurada
        # A API do Santander obriga criar uma API (app) por conta corrente
        # Ag 3003, CC 130827180 (já configurada nas credenciais)
        santander_client_id = os.getenv('SANTANDER_CLIENT_ID')
        if santander_client_id:
            # Verificar se tem agência/conta configuradas (opcional, para exibição)
            santander_agencia = os.getenv('SANTANDER_AGENCIA', '3003')
            santander_conta = os.getenv('SANTANDER_CONTA', '130827180')
            contas.append({
                'banco': 'SANTANDER',
                'nome': f'Santander - Ag. {santander_agencia} C/C {santander_conta}',
                'agencia': santander_agencia,
                'conta': santander_conta,
                'id': 'santander'
            })
            logger.debug(f"✅ Santander adicionado: Ag. {santander_agencia} C/C {santander_conta}")
        else:
            logger.debug(f"⚠️ Santander não configurado: SANTANDER_CLIENT_ID não encontrado")
        
        logger.info(f"📋 Total de contas encontradas: {len(contas)}")
        
        return jsonify({
            'success': True,
            'contas': contas
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter contas bancárias: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'contas': []
        }), 500


@app.route('/api/config/mercante', methods=['GET'])
def get_mercante_config():
    """Obtém configurações do Mercante (CPF e se senha está configurada, sem mostrar senha)."""
    try:
        # ✅ Fonte da verdade: arquivo .env (quando existir)
        mercante_user = os.getenv('MERCANTE_USER', '')
        mercante_pass = os.getenv('MERCANTE_PASS', '')

        env_path = None
        possible_paths = [
            Path('.env'),
            Path(__file__).parent / '.env',
            Path(os.getcwd()) / '.env',
        ]
        for path in possible_paths:
            if path.exists():
                env_path = path.absolute()
                break

        if env_path and env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                for line in content.split('\n'):
                    if line.startswith('MERCANTE_USER='):
                        mercante_user = line.split('=', 1)[1] if '=' in line else mercante_user
                    elif line.startswith('MERCANTE_PASS='):
                        mercante_pass = line.split('=', 1)[1] if '=' in line else mercante_pass
            except Exception:
                # Se falhar leitura do arquivo, manter fallback do ambiente
                pass
        
        return jsonify({
            'success': True,
            'config': {
                'mercante_user': mercante_user,
                'mercante_pass_configured': bool(mercante_pass),
            }
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter configuração do Mercante: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/mercante', methods=['POST'])
def save_mercante_config():
    """Salva configurações do Mercante (CPF e senha) no arquivo .env."""
    try:
        data = request.get_json()
        mercante_user = (data.get('mercante_user') or '').strip()
        mercante_pass = (data.get('mercante_pass') or '').strip()
        
        if not mercante_user:
            return jsonify({
                'success': False,
                'error': 'CPF do Mercante é obrigatório'
            }), 400
        
        # Encontrar arquivo .env
        env_path = None
        possible_paths = [
            Path('.env'),
            Path(__file__).parent / '.env',
            Path(os.getcwd()) / '.env',
        ]
        
        for path in possible_paths:
            if path.exists():
                env_path = path.absolute()
                break
        
        if not env_path:
            env_path = Path(__file__).parent / '.env'
            env_path.touch()
        
        # Ler conteúdo atual do .env
        env_content = ''
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
        
        # Atualizar ou adicionar variáveis
        lines = env_content.split('\n')
        updated_lines = []
        found_user = False
        found_pass = False
        
        # ✅ CORREÇÃO: Ler senha atual diretamente do arquivo .env (não confiar no os.getenv)
        senha_atual_arquivo = ''
        for line in lines:
            if line.startswith('MERCANTE_PASS='):
                senha_atual_arquivo = line.split('=', 1)[1] if '=' in line else ''
                break
        
        # Se não encontrou no arquivo, tentar do ambiente (fallback)
        if not senha_atual_arquivo:
            senha_atual_arquivo = os.getenv('MERCANTE_PASS', '')
        
        for line in lines:
            if line.startswith('MERCANTE_USER='):
                updated_lines.append(f'MERCANTE_USER={mercante_user}')
                found_user = True
            elif line.startswith('MERCANTE_PASS='):
                # ✅ CORREÇÃO: Se mercante_pass foi fornecido (não vazio), SEMPRE salvar
                # Isso garante que mesmo senhas vazias no frontend sejam tratadas corretamente
                if mercante_pass:
                    updated_lines.append(f'MERCANTE_PASS={mercante_pass}')
                    logger.info(f'✅ Senha do Mercante atualizada no .env (tamanho: {len(mercante_pass)})')
                else:
                    # Preservar senha existente do arquivo
                    if senha_atual_arquivo:
                        updated_lines.append(f'MERCANTE_PASS={senha_atual_arquivo}')
                        logger.debug(f'✅ Preservando senha existente do Mercante (não foi fornecida nova)')
                    else:
                        # Se não tinha senha antes, manter vazio (mas criar a linha)
                        updated_lines.append('MERCANTE_PASS=')
                found_pass = True
            else:
                updated_lines.append(line)
        
        # Adicionar variáveis que não existiam
        if not found_user:
            updated_lines.append(f'MERCANTE_USER={mercante_user}')
        if not found_pass:
            if mercante_pass:
                updated_lines.append(f'MERCANTE_PASS={mercante_pass}')
                logger.info(f'✅ Nova senha do Mercante adicionada no .env (tamanho: {len(mercante_pass)})')
            elif senha_atual_arquivo:
                updated_lines.append(f'MERCANTE_PASS={senha_atual_arquivo}')
                logger.debug(f'✅ Senha existente do Mercante preservada (não foi fornecida nova)')
            else:
                updated_lines.append('MERCANTE_PASS=')
        
        # Salvar arquivo .env
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
            if not updated_lines[-1].endswith('\n'):
                f.write('\n')

        # ✅ Atualizar variáveis na sessão atual (sem expor senha na resposta)
        mercante_pass_final = mercante_pass if mercante_pass else (senha_atual_arquivo or '')
        os.environ['MERCANTE_USER'] = mercante_user
        os.environ['MERCANTE_PASS'] = mercante_pass_final

        logger.info(
            f"✅ Configuração do Mercante salva: CPF={mercante_user[:3]}*** "
            f"(senha configurada: {bool(mercante_pass_final)})"
        )
        
        return jsonify({
            'success': True,
            'message': 'Configuração do Mercante salva com sucesso'
        })
    except Exception as e:
        logger.error(f"❌ Erro ao salvar configuração do Mercante: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/email', methods=['POST'])
def save_email_config():
    """Salva configurações de email no arquivo .env."""
    try:
        data = request.get_json()
        smtp_server = data.get('smtp_server', 'smtp.gmail.com')
        smtp_port = data.get('smtp_port', 587)
        email_sender = data.get('email_sender', '').strip()
        email_password = data.get('email_password', '').strip()
        email_default_mailbox = (data.get('email_default_mailbox') or '').strip()
        
        if not email_sender:
            return jsonify({
                'success': False,
                'error': 'Email sender é obrigatório'
            }), 400

        # ✅ Compatibilidade: se mailbox não foi informada, manter padrão antigo (igual ao sender)
        if not email_default_mailbox:
            email_default_mailbox = email_sender
        
        # Encontrar arquivo .env
        env_path = None
        possible_paths = [
            Path('.env'),
            Path(__file__).parent / '.env',
            Path(os.getcwd()) / '.env',
        ]
        
        for path in possible_paths:
            if path.exists():
                env_path = path.absolute()
                break
        
        if not env_path:
            # Criar novo arquivo .env se não existir
            env_path = Path(__file__).parent / '.env'
            env_path.touch()
        
        # Ler conteúdo atual do .env
        env_content = ''
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                env_content = f.read()
        
        # Atualizar ou adicionar variáveis
        lines = env_content.split('\n')
        updated_lines = []
        found_smtp_server = False
        found_smtp_port = False
        found_email_sender = False
        found_email_password = False
        found_email_default_mailbox = False
        
        # ✅ Buscar senha atual do .env para preservar se não for fornecida
        senha_atual = os.getenv('EMAIL_PASSWORD', '')
        
        for line in lines:
            if line.startswith('EMAIL_SMTP_SERVER='):
                # ✅ Só atualizar se não existir ou se foi fornecido explicitamente
                if not found_smtp_server:
                    updated_lines.append(f'EMAIL_SMTP_SERVER={smtp_server}')
                else:
                    updated_lines.append(line)
                found_smtp_server = True
            elif line.startswith('EMAIL_SMTP_PORT='):
                # ✅ Só atualizar se não existir ou se foi fornecido explicitamente
                if not found_smtp_port:
                    updated_lines.append(f'EMAIL_SMTP_PORT={smtp_port}')
                else:
                    updated_lines.append(line)
                found_smtp_port = True
            elif line.startswith('EMAIL_SENDER='):
                updated_lines.append(f'EMAIL_SENDER={email_sender}')
                found_email_sender = True
            elif line.startswith('EMAIL_DEFAULT_MAILBOX='):
                # ✅ CRÍTICO: permitir mailbox de leitura diferente do email de envio
                updated_lines.append(f'EMAIL_DEFAULT_MAILBOX={email_default_mailbox}')
                found_email_default_mailbox = True
            elif line.startswith('EMAIL_PASSWORD='):
                # ✅ CORREÇÃO: Preservar senha existente se não for fornecida
                if email_password:
                    updated_lines.append(f'EMAIL_PASSWORD={email_password}')
                else:
                    # Manter senha atual do .env
                    senha_existente = line.split('=', 1)[1] if '=' in line else ''
                    if senha_existente:
                        updated_lines.append(line)  # Manter linha original
                    else:
                        updated_lines.append(f'EMAIL_PASSWORD={senha_atual}' if senha_atual else 'EMAIL_PASSWORD=')
                found_email_password = True
            else:
                updated_lines.append(line)
        
        # Adicionar variáveis que não existiam
        if not found_smtp_server:
            updated_lines.append(f'EMAIL_SMTP_SERVER={smtp_server}')
        if not found_smtp_port:
            updated_lines.append(f'EMAIL_SMTP_PORT={smtp_port}')
        if not found_email_sender:
            updated_lines.append(f'EMAIL_SENDER={email_sender}')
        # ✅ CRÍTICO: Sempre adicionar/atualizar EMAIL_DEFAULT_MAILBOX (mailbox de leitura do Graph)
        if not found_email_default_mailbox:
            updated_lines.append(f'EMAIL_DEFAULT_MAILBOX={email_default_mailbox}')
        if not found_email_password:
            # ✅ Só adicionar senha se foi fornecida
            if email_password:
                updated_lines.append(f'EMAIL_PASSWORD={email_password}')
            elif senha_atual:
                updated_lines.append(f'EMAIL_PASSWORD={senha_atual}')
        
        # Escrever de volta
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
        
        # Atualizar variáveis de ambiente na sessão atual
        os.environ['EMAIL_SMTP_SERVER'] = smtp_server
        os.environ['EMAIL_SMTP_PORT'] = str(smtp_port)
        os.environ['EMAIL_SENDER'] = email_sender
        # ✅ CRÍTICO: Atualizar EMAIL_DEFAULT_MAILBOX também na sessão atual
        os.environ['EMAIL_DEFAULT_MAILBOX'] = email_default_mailbox
        if email_password:
            os.environ['EMAIL_PASSWORD'] = email_password
        
        logger.info(f"✅ Configuração de email salva: {email_sender} (servidor: {smtp_server}:{smtp_port})")
        logger.info(f"✅ EMAIL_DEFAULT_MAILBOX atualizado para: {email_default_mailbox}")
        
        # ✅ IMPORTANTE: Invalidar instâncias globais dos serviços de email para recarregar com nova configuração
        # Isso é necessário porque EmailService lê as variáveis de ambiente no __init__
        try:
            # Invalidar EmailService (lê EMAIL_DEFAULT_MAILBOX no __init__)
            import services.email_service as email_service_module
            email_service_module._email_service_instance = None
            logger.info(f"✅ Instância global do EmailService invalidada")
            
            # Invalidar EmailSendCoordinator (tem referência ao EmailService)
            try:
                from services.email_send_coordinator import get_email_send_coordinator
                if hasattr(get_email_send_coordinator, '_instance'):
                    delattr(get_email_send_coordinator, '_instance')
                    logger.info(f"✅ Instância global do EmailSendCoordinator invalidada")
            except Exception as e2:
                logger.debug(f"⚠️ Não foi possível invalidar EmailSendCoordinator: {e2}")
            
            logger.info(f"✅ Serviços de email serão recriados na próxima chamada com nova configuração: {email_sender}")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível invalidar serviços de email: {e} (não crítico, será recarregado no próximo uso ou após reiniciar Flask)")
        
        return jsonify({
            'success': True,
            'message': 'Configuração de email salva com sucesso'
        })
    except Exception as e:
        logger.error(f"❌ Erro ao salvar configuração de email: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/network', methods=['GET'])
def get_network_config():
    """Obtém configurações de rede e conectividade."""
    try:
        sql_mode = os.getenv('SQL_SERVER_MODE', 'auto')
        kanban_url = os.getenv('KANBAN_API_URL', 'http://172.16.10.211:5000/api/kanban/pedidos')
        
        return jsonify({
            'success': True,
            'config': {
                'sql_server_mode': sql_mode,
                'kanban_api_url': kanban_url
            }
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter configuração de rede: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/network', methods=['POST'])
def save_network_config():
    """Salva configurações de rede no arquivo .env."""
    try:
        data = request.get_json()
        sql_mode = (data.get('sql_server_mode') or 'auto').strip().lower()
        kanban_url = (data.get('kanban_api_url') or '').strip()
        
        if sql_mode not in ('auto', 'office', 'vpn', 'legacy'):
            return jsonify({
                'success': False,
                'error': 'Modo SQL Server inválido. Use: auto, office, vpn ou legacy'
            }), 400
            
        # Encontrar arquivo .env
        env_path = None
        possible_paths = [
            Path('.env'),
            Path(__file__).parent / '.env',
            Path(os.getcwd()) / '.env',
        ]
        for path in possible_paths:
            if path.exists():
                env_path = path.absolute()
                break
        
        if not env_path:
            env_path = Path(__file__).parent / '.env'
            env_path.touch()
            
        # Ler conteúdo atual
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        updated_lines = []
        found_sql_mode = False
        found_kanban_url = False
        
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith('SQL_SERVER_MODE='):
                updated_lines.append(f'SQL_SERVER_MODE={sql_mode}\n')
                found_sql_mode = True
            elif line_strip.startswith('KANBAN_API_URL='):
                if kanban_url:
                    updated_lines.append(f'KANBAN_API_URL={kanban_url}\n')
                    found_kanban_url = True
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
                
        if not found_sql_mode:
            updated_lines.append(f'SQL_SERVER_MODE={sql_mode}\n')
        if not found_kanban_url and kanban_url:
            updated_lines.append(f'KANBAN_API_URL={kanban_url}\n')
            
        # Salvar
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
            
        # Atualizar ambiente
        os.environ['SQL_SERVER_MODE'] = sql_mode
        if kanban_url:
            os.environ['KANBAN_API_URL'] = kanban_url
            
        return jsonify({
            'success': True,
            'message': 'Configurações de rede salvas com sucesso'
        })
    except Exception as e:
        logger.error(f"❌ Erro ao salvar configuração de rede: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config/network/refresh', methods=['POST'])
def refresh_network_config():
    """Força o recarregamento do adaptador SQL Server invalidando o singleton."""
    try:
        from utils.sql_server_adapter import load_env_from_file
        import utils.sql_server_adapter as adapter_module
        
        # 1. Recarregar .env
        load_env_from_file()
        
        # 2. Invalidar singleton
        adapter_module._sql_adapter_instance = None
        
        logger.info("🔄 Adaptador SQL Server invalidado para recarregamento (via UI)")
        return jsonify({'success': True, 'message': 'Adaptador SQL Server será recarregado na próxima consulta'})
    except Exception as e:
        logger.error(f"❌ Erro ao dar refresh na config de rede: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/utils/consultar-cnpj/<cnpj>', methods=['GET'])
def api_consultar_cnpj(cnpj):
    """Consulta nome da empresa pelo CNPJ via serviço interno."""
    try:
        from services.consulta_cpf_cnpj_service import ConsultaCpfCnpjService
        svc = ConsultaCpfCnpjService()
        res = svc.consultar(cnpj)
        if res and res.get('nome'):
            return jsonify({'sucesso': True, 'nome': res['nome']})
        return jsonify({'sucesso': False, 'erro': 'Não encontrado'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/ptax', methods=['GET'])
def get_ptax():
    """
    Endpoint para retornar PTAX de venda relevante para decisão de registro:
    - registro_hoje: PTAX do dia útil anterior a hoje
    - registro_amanha: PTAX do dia útil anterior a amanhã
    """
    try:
        from utils.ptax_bcb import obter_ptax_dolar, obter_ptax_dia_util_anterior
        from datetime import datetime, timedelta

        hoje_dt = datetime.now()
        hoje_str = hoje_dt.strftime('%m-%d-%Y')

        # PTAX de mercado de hoje (somente informativa)
        ptax_mercado_hoje = obter_ptax_dolar(hoje_str)

        # PTAX para registrar HOJE = dia útil anterior a hoje
        ptax_registro_hoje = obter_ptax_dia_util_anterior(hoje_str)

        # PTAX para registrar AMANHÃ = dia útil anterior a amanhã
        amanha_dt = hoje_dt + timedelta(days=1)
        amanha_str = amanha_dt.strftime('%m-%d-%Y')
        ptax_registro_amanha = obter_ptax_dia_util_anterior(amanha_str)

        resultado = {
            'registro_hoje': {
                'cotacao_venda': ptax_registro_hoje.get('cotacao_venda') if ptax_registro_hoje else None,
                'data_util': ptax_registro_hoje.get('data_util_encontrada') if ptax_registro_hoje else None,
                'sucesso': ptax_registro_hoje.get('sucesso', False) if ptax_registro_hoje else False,
            },
            'registro_amanha': {
                'cotacao_venda': ptax_registro_amanha.get('cotacao_venda') if ptax_registro_amanha else None,
                'data_util': ptax_registro_amanha.get('data_util_encontrada') if ptax_registro_amanha else None,
                'sucesso': ptax_registro_amanha.get('sucesso', False) if ptax_registro_amanha else False,
            },
            'mercado_hoje': {
                'cotacao_venda': ptax_mercado_hoje.get('cotacao_venda') if ptax_mercado_hoje else None,
                'data': ptax_mercado_hoje.get('data_cotacao') if ptax_mercado_hoje else None,
                'sucesso': ptax_mercado_hoje.get('sucesso', False) if ptax_mercado_hoje else False,
            },
            'success': True,
        }

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"❌ Erro ao obter PTAX: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'registro_hoje': {'sucesso': False},
            'registro_amanha': {'sucesso': False},
            'mercado_hoje': {'sucesso': False},
        }), 500


# ============================================
# ENDPOINTS DE SINCRONIZAÇÃO BANCÁRIA
# ============================================

@app.route('/api/banco/upload-boleto', methods=['POST'])
def upload_boleto():
    """
    Endpoint para upload de boleto PDF.
    
    Processo:
    1. Recebe PDF do boleto
    2. Extrai dados (código de barras, valor, vencimento)
    3. Consulta saldo
    4. Retorna dados para aprovação
    """
    from flask import request
    from services.boleto_parser import BoletoParser
    from services.santander_service import SantanderService
    import os
    import uuid
    
    try:
        if 'file' not in request.files:
            return jsonify({
                'sucesso': False,
                'erro': 'Nenhum arquivo enviado'
            }), 400
        
        file = request.files['file']
        session_id = request.form.get('session_id', 'default')
        filename = file.filename or ''
        
        if filename == '':
            return jsonify({
                'sucesso': False,
                'erro': 'Nome de arquivo vazio'
            }), 400
        
        if not filename.lower().endswith('.pdf'):
            return jsonify({
                'sucesso': False,
                'erro': 'Apenas arquivos PDF são permitidos'
            }), 400
        
        # Salvar arquivo temporariamente
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'boletos')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_id = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f'{file_id}.pdf')
        file.save(file_path)
        
        logger.info(f"🔍 [UPLOAD BOLETO] Arquivo salvo: {file_path}, session_id={session_id}")
        
        # ✅ CORREÇÃO: Chamar SantanderAgent._processar_boleto_upload para iniciar pagamento automaticamente
        logger.info(f"🔍 [UPLOAD BOLETO] Iniciando processamento via agent - file_path={file_path}, session_id={session_id}")
        try:
            from services.agents.santander_agent import SantanderAgent
            logger.info(f"🔍 [UPLOAD BOLETO] Importando SantanderAgent...")
            agent = SantanderAgent()
            logger.info(f"🔍 [UPLOAD BOLETO] Agent criado, chamando _processar_boleto_upload...")
            
            # Chamar método do agent que processa e inicia pagamento automaticamente
            # ✅ IMPORTANTE: Não remover arquivo antes - o agent precisa dele para processar
            resultado = agent._processar_boleto_upload(
                arguments={'file_path': file_path, 'session_id': session_id},
                context={'session_id': session_id}
            )
            
            logger.info(f"🔍 [UPLOAD BOLETO] Resultado do agent: sucesso={resultado.get('sucesso')}, pagamento_iniciado={resultado.get('pagamento_iniciado')}, payment_id={resultado.get('payment_id')}")
            
            # Limpar arquivo temporário após processamento (o agent já leu o arquivo)
            try:
                os.remove(file_path)
            except:
                pass
            
            # Se o agent processou com sucesso, retornar resultado dele
            if resultado.get('sucesso'):
                logger.info(f"✅ [UPLOAD BOLETO] Retornando sucesso - payment_id={resultado.get('payment_id')}, pagamento_iniciado={resultado.get('pagamento_iniciado')}")
                return jsonify({
                    'sucesso': True,
                    'dados': resultado.get('dados', {}),
                    'resposta': resultado.get('resposta', ''),
                    'payment_id': resultado.get('payment_id'),
                    'pagamento_iniciado': resultado.get('pagamento_iniciado', False),
                    'acao': 'aprovar_pagamento' if resultado.get('pagamento_iniciado') else None
                })
            else:
                # Se falhou, retornar erro do agent
                logger.warning(f"⚠️ [UPLOAD BOLETO] Agent retornou erro: {resultado.get('erro')}")
                return jsonify({
                    'sucesso': False,
                    'erro': resultado.get('erro', 'Erro ao processar boleto'),
                    'resposta': resultado.get('resposta', ''),
                    'dados': resultado.get('dados', {})
                }), 400
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar boleto via agent: {e}", exc_info=True)
            # Fallback: processar manualmente se agent falhar
            parser = BoletoParser()
            dados = parser.extrair_dados_boleto(file_path)
            
            # Limpar arquivo temporário após processamento
            try:
                os.remove(file_path)
            except:
                pass
            
            if not dados.get('sucesso'):
                erro_msg = dados.get('erro', 'Não foi possível extrair dados do boleto')
                if 'não retornou texto' in erro_msg.lower() or 'escaneado' in erro_msg.lower():
                    erro_msg = 'PDF escaneado ou em formato de imagem. Não foi possível extrair texto automaticamente.\n\n💡 **Solução:** Você pode fornecer os dados manualmente:\n- Código de barras (44 ou 47 dígitos)\n- Valor do boleto\n- Data de vencimento (opcional)'
                
                return jsonify({
                    'sucesso': False,
                    'erro': erro_msg,
                    'dados': dados,
                    'sugestao': 'fornecer_dados_manuais'
                }), 400
            
            # Consultar saldo (opcional - não falha se não conseguir)
            saldo_disponivel = None
            try:
                santander_service = SantanderService()
                saldo_result = santander_service.consultar_saldo()
                if saldo_result.get('sucesso'):
                    saldo_disponivel = saldo_result.get('dados', {}).get('disponivel', 0)
            except Exception as e_saldo:
                logger.warning(f"⚠️ Não foi possível consultar saldo: {e_saldo}")
            
            # Preparar resposta (fallback)
            resposta_dados = {
                **dados,
                'saldo_disponivel': saldo_disponivel,
                'saldo_apos_pagamento': saldo_disponivel - dados.get('valor', 0) if saldo_disponivel else None,
                'file_id': file_id
            }
            
            return jsonify({
                'sucesso': True,
                'dados': resposta_dados,
                'acao': 'aprovar_pagamento',
                'erro_fallback': f'Agent não disponível, usando processamento manual: {str(e)}'
            })
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar upload de boleto: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/api/banco/sincronizar', methods=['POST'])
def sincronizar_extrato_bancario():
    """
    Endpoint para sincronizar extratos bancários com SQL Server.
    
    Importa lançamentos da API do Banco do Brasil ou Santander para a tabela MOVIMENTACAO_BANCARIA,
    detectando e evitando duplicatas automaticamente usando hash único.
    
    Body (JSON):
    {
        "banco": "BB",               # Opcional (default: "BB") - "BB" ou "SANTANDER"
        "agencia": "1251",            # Obrigatório para BB, opcional para Santander
        "conta": "50483",             # Obrigatório para BB, opcional para Santander
        "data_inicio": "2026-01-01",  # Opcional (default: 7 dias atrás)
        "data_fim": "2026-01-07",     # Opcional (default: hoje)
        "dias_retroativos": 7         # Opcional (usado se datas não fornecidas)
    }
    
    Returns:
        JSON com resultado da sincronização:
        - sucesso: bool
        - total: int (lançamentos processados)
        - novos: int (lançamentos inseridos)
        - duplicados: int (lançamentos pulados)
        - erros: int (lançamentos com erro)
        - processos_detectados: List[str] (processos vinculados automaticamente)
        - resposta: str (mensagem formatada)
    """
    try:
        from services.banco_sincronizacao_service import get_banco_sincronizacao_service
        from datetime import datetime
        
        data = request.get_json() or {}
        
        # Parâmetro banco (opcional, default: BB)
        banco = data.get('banco', 'BB').upper()
        if banco not in ('BB', 'SANTANDER'):
            return jsonify({
                'sucesso': False,
                'erro': 'BANCO_INVALIDO',
                'mensagem': 'Parâmetro "banco" deve ser "BB" ou "SANTANDER"'
            }), 400
        
        # Parâmetros agencia e conta
        agencia = data.get('agencia')
        conta = data.get('conta')
        
        # Validação: para BB, agencia e conta são obrigatórios
        # Para Santander, são opcionais (a API já está vinculada à conta)
        if banco == 'BB':
            if not agencia or not conta:
                return jsonify({
                    'sucesso': False,
                    'erro': 'PARAMETROS_FALTANDO',
                    'mensagem': 'Para Banco do Brasil, "agencia" e "conta" são obrigatórios'
                }), 400
        
        # Parâmetros opcionais de data
        data_inicio = None
        data_fim = None
        
        if data.get('data_inicio'):
            try:
                data_inicio = datetime.strptime(data['data_inicio'], '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'sucesso': False,
                    'erro': 'DATA_INVALIDA',
                    'mensagem': 'data_inicio deve estar no formato YYYY-MM-DD'
                }), 400
        
        if data.get('data_fim'):
            try:
                data_fim = datetime.strptime(data['data_fim'], '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'sucesso': False,
                    'erro': 'DATA_INVALIDA',
                    'mensagem': 'data_fim deve estar no formato YYYY-MM-DD'
                }), 400
        
        dias_retroativos = int(data.get('dias_retroativos', 7))
        
        # Executar sincronização
        service = get_banco_sincronizacao_service()
        resultado = service.sincronizar_extrato(
            banco=banco,
            agencia=agencia,
            conta=conta,
            data_inicio=data_inicio,
            data_fim=data_fim,
            dias_retroativos=dias_retroativos
        )
        
        # ✅ UX (21/01/2026): Para erros “controlados” (ex: SQL Server indisponível),
        # retornar 200 com sucesso=False e mensagem preenchida para a UI não cair em "Erro desconhecido".
        if resultado.get('sucesso'):
            return jsonify(resultado), 200

        # Garantir que sempre exista `mensagem` em falhas
        if not resultado.get('mensagem'):
            resultado['mensagem'] = resultado.get('resposta') or resultado.get('erro') or 'Erro desconhecido'

        if resultado.get('sql_server_indisponivel'):
            # Não é erro do usuário; é ambiente (VPN/rede). Devolver 200 para UI exibir corretamente.
            return jsonify(resultado), 200

        # Demais falhas inesperadas continuam como 500 (mantém sinalização de erro no servidor)
        return jsonify(resultado), 500
            
    except Exception as e:
        logger.error(f"❌ Erro ao sincronizar extrato: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': f'Erro interno: {str(e)}'
        }), 500


@app.route('/api/banco/lancamentos-nao-vinculados', methods=['GET'])
def listar_lancamentos_nao_vinculados():
    """
    Lista lançamentos bancários que não estão vinculados a nenhum processo.
    
    Query params:
        - limite: int (default: 50)
        - data_inicio: str (YYYY-MM-DD, opcional)
        - data_fim: str (YYYY-MM-DD, opcional)
    
    Returns:
        JSON com lista de lançamentos não vinculados
    """
    try:
        from services.banco_sincronizacao_service import get_banco_sincronizacao_service
        from datetime import datetime
        
        limite = int(request.args.get('limite', 50))
        
        data_inicio = None
        data_fim = None
        
        if request.args.get('data_inicio'):
            try:
                data_inicio = datetime.strptime(request.args['data_inicio'], '%Y-%m-%d')
            except ValueError:
                pass
        
        if request.args.get('data_fim'):
            try:
                data_fim = datetime.strptime(request.args['data_fim'], '%Y-%m-%d')
            except ValueError:
                pass
        
        service = get_banco_sincronizacao_service()
        resultado = service.listar_lancamentos_nao_vinculados(
            limite=limite,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar lançamentos: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'lancamentos': []
        }), 500


@app.route('/api/pagamentos/historico', methods=['GET'])
def get_historico_pagamentos():
    """
    Endpoint para buscar histórico de pagamentos.
    
    Query Parameters:
        - banco: Filtrar por banco (SANTANDER, BANCO_DO_BRASIL)
        - ambiente: Filtrar por ambiente (SANDBOX, PRODUCAO)
        - tipo: Filtrar por tipo (BOLETO, PIX, TED, BARCODE)
        - status: Filtrar por status (READY_TO_PAY, PENDING_VALIDATION, PAYED, CANCELLED, FAILED)
        - data_inicio: Data início (YYYY-MM-DD)
        - data_fim: Data fim (YYYY-MM-DD)
        - limite: Limite de resultados (default: 100)
    
    Returns:
        JSON com lista de pagamentos:
        {
            "sucesso": true,
            "pagamentos": [
                {
                    "payment_id": "...",
                    "tipo_pagamento": "BOLETO",
                    "banco": "SANTANDER",
                    "ambiente": "SANDBOX",
                    "status": "PAYED",
                    "valor": 900.00,
                    "beneficiario": "...",
                    "data_efetivacao": "2026-01-13T14:48:00",
                    ...
                }
            ],
            "total": 10
        }
    """
    try:
        from db_manager import get_db_connection
        from flask import request
        import sqlite3
        
        # Parâmetros de filtro
        banco = request.args.get('banco', '').upper()
        ambiente = request.args.get('ambiente', '').upper()
        tipo = request.args.get('tipo', '').upper()
        status = request.args.get('status', '').upper()
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        limite = int(request.args.get('limite', 100))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Construir query com filtros
        query = 'SELECT * FROM historico_pagamentos WHERE 1=1'
        params = []
        
        if banco:
            query += ' AND banco = ?'
            params.append(banco)
        
        if ambiente:
            query += ' AND ambiente = ?'
            params.append(ambiente)
        
        if tipo:
            query += ' AND tipo_pagamento = ?'
            params.append(tipo)
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if data_inicio:
            query += ' AND (data_efetivacao >= ? OR (data_efetivacao IS NULL AND data_inicio >= ?))'
            params.extend([data_inicio, data_inicio])
        
        if data_fim:
            query += ' AND (data_efetivacao <= ? OR (data_efetivacao IS NULL AND data_inicio <= ?))'
            params.extend([data_fim, data_fim])
        
        # Ordenar por data de efetivação (mais recente primeiro) ou data de início
        query += ' ORDER BY COALESCE(data_efetivacao, data_inicio) DESC LIMIT ?'
        params.append(limite)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Converter para lista de dicts
        colunas = [desc[0] for desc in cursor.description]
        pagamentos = []
        
        for row in rows:
            pagamento = dict(zip(colunas, row))
            # Converter dados_completos de JSON string para dict (se existir)
            if pagamento.get('dados_completos'):
                try:
                    import json
                    pagamento['dados_completos'] = json.loads(pagamento['dados_completos'])
                except:
                    pass
            pagamentos.append(pagamento)
        
        conn.close()
        
        logger.info(f"✅ Histórico de pagamentos consultado: {len(pagamentos)} registros")
        
        return jsonify({
            'sucesso': True,
            'pagamentos': pagamentos,
            'total': len(pagamentos)
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar histórico de pagamentos: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'pagamentos': []
        }), 500


@app.route('/api/banco/vincular', methods=['POST'])
def vincular_lancamento_processo():
    """
    Vincula um lançamento bancário a um processo de importação.
    
    Body (JSON):
    {
        "id_movimentacao": 12345,           # Obrigatório
        "processo_referencia": "DMD.0083/25", # Obrigatório
        "tipo_relacionamento": "PAGAMENTO_FRETE" # Opcional
    }
    
    Returns:
        JSON com resultado da vinculação
    """
    try:
        from services.banco_sincronizacao_service import get_banco_sincronizacao_service
        
        data = request.get_json() or {}
        
        id_movimentacao = data.get('id_movimentacao')
        processo_referencia = data.get('processo_referencia')
        tipo_relacionamento = data.get('tipo_relacionamento')
        
        if not id_movimentacao or not processo_referencia:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETROS_FALTANDO',
                'mensagem': 'Parâmetros "id_movimentacao" e "processo_referencia" são obrigatórios'
            }), 400
        
        service = get_banco_sincronizacao_service()
        resultado = service.vincular_lancamento_processo(
            id_movimentacao=int(id_movimentacao),
            processo_referencia=processo_referencia,
            tipo_relacionamento=tipo_relacionamento
        )
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
        
    except Exception as e:
        logger.error(f"❌ Erro ao vincular lançamento: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/api/banco/resumo-processo/<processo_referencia>', methods=['GET'])
def resumo_movimentacoes_processo(processo_referencia):
    """
    Obtém resumo de movimentações bancárias de um processo.
    
    Path param:
        - processo_referencia: str (ex: DMD.0083/25)
    
    Returns:
        JSON com resumo das movimentações do processo
    """
    try:
        from services.banco_sincronizacao_service import get_banco_sincronizacao_service
        
        service = get_banco_sincronizacao_service()
        resultado = service.obter_resumo_movimentacoes_processo(processo_referencia)
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter resumo: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/api/banco/lancamentos-nao-classificados', methods=['GET'])
def listar_lancamentos_nao_classificados():
    """
    Lista lançamentos bancários que não estão classificados (sem tipo de despesa vinculado).
    
    ✅ NOVO: Suporta paginação para melhor performance.
    
    Query params:
        - page: int (opcional, padrão: 1) - Número da página
        - per_page: int (opcional, padrão: 50, máximo: 100) - Itens por página
        - limite: int (DEPRECATED - use page/per_page)
        - data_inicio: str (YYYY-MM-DD, opcional)
        - data_fim: str (YYYY-MM-DD, opcional)
    
    Returns:
        JSON com lista de lançamentos não classificados e informações de paginação
    """
    try:
        from services.banco_concilacao_service import get_banco_concilacao_service
        
        # ✅ NOVO: Suportar paginação
        page = request.args.get('page', type=int) or 1
        per_page = request.args.get('per_page', type=int) or 50
        limite = request.args.get('limite', type=int)  # DEPRECATED, mas mantido para compatibilidade
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        service = get_banco_concilacao_service()
        resultado = service.listar_lancamentos_nao_classificados(
            limite=limite,  # DEPRECATED
            page=page,
            per_page=per_page,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
    except Exception as e:
        logger.error(f"❌ Erro ao listar lançamentos não classificados: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/lancamentos-classificados', methods=['GET'])
def listar_lancamentos_classificados():
    """
    Lista lançamentos bancários que já estão classificados (para permitir edição).
    
    Query params:
        - limite: int (opcional, padrão: 50)
        - processo_referencia: str (opcional, filtrar por processo)
        - data_inicio: str (YYYY-MM-DD, opcional)
        - data_fim: str (YYYY-MM-DD, opcional)
    
    Returns:
        JSON com lista de lançamentos classificados
    """
    try:
        from services.banco_concilacao_service import get_banco_concilacao_service
        
        limite = int(request.args.get('limite', 50))
        processo_referencia = request.args.get('processo_referencia')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        service = get_banco_concilacao_service()
        resultado = service.listar_lancamentos_classificados(
            limite=limite,
            processo_referencia=processo_referencia,
            data_inicio=data_inicio,
            data_fim=data_fim
        )
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
    except Exception as e:
        logger.error(f"❌ Erro ao listar lançamentos classificados: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/tipos-despesa', methods=['GET'])
def listar_tipos_despesa():
    """
    Lista todos os tipos de despesa disponíveis no catálogo.
    
    Returns:
        JSON com lista de tipos de despesa
    """
    try:
        from services.banco_concilacao_service import get_banco_concilacao_service
        
        service = get_banco_concilacao_service()
        resultado = service.listar_tipos_despesa()
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
    except Exception as e:
        logger.error(f"❌ Erro ao listar tipos de despesa: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/sugestoes-vinculacao', methods=['GET'])
def listar_sugestoes_vinculacao():
    """
    Lista sugestões pendentes de vinculação bancária automática.
    
    Query params:
        - limite: int (opcional, padrão: 50)
    
    Returns:
        JSON com lista de sugestões pendentes
    """
    try:
        from services.banco_auto_vinculacao_service import BancoAutoVinculacaoService
        
        limite = int(request.args.get('limite', 50))
        
        service = BancoAutoVinculacaoService()
        resultado = service.listar_sugestoes_pendentes(limite=limite)
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar sugestões: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e),
            'sugestoes': []
        }), 500


@app.route('/api/banco/aplicar-sugestao', methods=['POST'])
def aplicar_sugestao_vinculacao():
    """
    Aplica uma sugestão de vinculação bancária (vincula lançamento ao processo).
    
    Body (JSON):
    {
        "sugestao_id": 1,  # ID da sugestão
        "id_movimentacao": 777,  # ID do lançamento (opcional, usa o da sugestão se não fornecido)
        "processo_referencia": "GLT.0011/26"  # Opcional, usa o da sugestão se não fornecido
    }
    
    Returns:
        JSON com resultado da aplicação
    """
    try:
        from services.banco_concilacao_service import get_banco_concilacao_service
        from db_manager import get_db_connection
        
        data = request.get_json() or {}
        sugestao_id = data.get('sugestao_id')
        
        if not sugestao_id:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_FALTANDO',
                'mensagem': 'Parâmetro "sugestao_id" é obrigatório'
            }), 400
        
        # Buscar sugestão
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id,
                processo_referencia,
                id_movimentacao_sugerida,
                total_impostos,
                status
            FROM sugestoes_vinculacao_bancaria
            WHERE id = ?
        """, (sugestao_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'sucesso': False,
                'erro': 'SUGESTAO_NAO_ENCONTRADA',
                'mensagem': f'Sugestão {sugestao_id} não encontrada'
            }), 404
        
        if row[4] != 'pendente':  # status
            return jsonify({
                'sucesso': False,
                'erro': 'SUGESTAO_JA_APLICADA',
                'mensagem': f'Sugestão {sugestao_id} já foi aplicada ou ignorada'
            }), 400
        
        processo_ref = data.get('processo_referencia') or row[1]
        id_movimentacao = data.get('id_movimentacao') or row[2]
        
        # Buscar ID do tipo de despesa "Impostos de Importação"
        conciliacao_service = get_banco_concilacao_service()
        tipos_despesa = conciliacao_service.listar_tipos_despesa()
        
        id_tipo_despesa = None
        if tipos_despesa.get('sucesso'):
            for tipo in tipos_despesa.get('tipos', []):
                if tipo.get('nome_despesa', '').upper() == 'IMPOSTOS DE IMPORTAÇÃO':
                    id_tipo_despesa = tipo.get('id_tipo_despesa')
                    break
        
        if not id_tipo_despesa:
            return jsonify({
                'sucesso': False,
                'erro': 'TIPO_DESPESA_NAO_ENCONTRADO',
                'mensagem': 'Tipo de despesa "Impostos de Importação" não encontrado no catálogo'
            }), 404
        
        # Classificar lançamento como "Impostos de Importação"
        resultado_classificacao = conciliacao_service.classificar_lancamento(
            id_movimentacao=id_movimentacao,
            classificacoes=[{
                'id_tipo_despesa': id_tipo_despesa,
                'valor_despesa': float(row[3]),  # total_impostos
                'processo_referencia': processo_ref
            }]
        )
        
        if not resultado_classificacao.get('sucesso'):
            return jsonify({
                'sucesso': False,
                'erro': 'ERRO_CLASSIFICACAO',
                'mensagem': resultado_classificacao.get('erro', 'Erro ao classificar lançamento')
            }), 500
        
        # Após classificar com sucesso, marcar processo como conciliado no serviço de auto-vinculação
        try:
            from services.banco_auto_vinculacao_service import BancoAutoVinculacaoService
            auto_svc = BancoAutoVinculacaoService()
            auto_svc.marcar_processo_conciliado_banco(processo_ref)
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível marcar processo {processo_ref} como conciliado no auto-vinculação: {e}")
        
        # Marcar sugestão como aplicada
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sugestoes_vinculacao_bancaria
            SET status = 'aplicada',
                aplicado_em = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (sugestao_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'✅ Lançamento vinculado ao processo {processo_ref}',
            'sugestao_id': sugestao_id,
            'id_movimentacao': id_movimentacao,
            'processo_referencia': processo_ref
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro ao aplicar sugestão: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/ignorar-sugestao', methods=['POST'])
def ignorar_sugestao_vinculacao():
    """
    Ignora uma sugestão de vinculação bancária (marca como ignorada).
    
    Body (JSON):
    {
        "sugestao_id": 1  # ID da sugestão
    }
    
    Returns:
        JSON com resultado
    """
    try:
        from db_manager import get_db_connection
        
        data = request.get_json() or {}
        sugestao_id = data.get('sugestao_id')
        
        if not sugestao_id:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_FALTANDO',
                'mensagem': 'Parâmetro "sugestao_id" é obrigatório'
            }), 400
        
        # Marcar sugestão como ignorada
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sugestoes_vinculacao_bancaria
            SET status = 'ignorada'
            WHERE id = ? AND status = 'pendente'
        """, (sugestao_id,))
        conn.commit()
        conn.close()
        
        if cursor.rowcount > 0:
            return jsonify({
                'sucesso': True,
                'mensagem': f'✅ Sugestão {sugestao_id} ignorada'
            }), 200
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'SUGESTAO_NAO_ENCONTRADA',
                'mensagem': f'Sugestão {sugestao_id} não encontrada ou já foi processada'
            }), 404
        
    except Exception as e:
        logger.error(f"❌ Erro ao ignorar sugestão: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/desvincular-lancamento', methods=['POST'])
def desvincular_lancamento():
    """
    Desvincula um lançamento bancário de um processo (correção).
    
    Body (JSON):
    {
        "id_movimentacao": 777  # ID do lançamento
    }
    
    Returns:
        JSON com resultado da desvinculação
    """
    try:
        from services.banco_concilacao_service import get_banco_concilacao_service
        
        data = request.get_json() or {}
        id_movimentacao = data.get('id_movimentacao')
        
        if not id_movimentacao:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_FALTANDO',
                'mensagem': 'Parâmetro "id_movimentacao" é obrigatório'
            }), 400
        
        # Remover todas as classificações do lançamento
        conciliacao_service = get_banco_concilacao_service()
        
        # Buscar classificações existentes
        lancamento = conciliacao_service.obter_lancamento_com_classificacoes(id_movimentacao)
        
        if not lancamento.get('sucesso'):
            return jsonify({
                'sucesso': False,
                'erro': 'LANCAMENTO_NAO_ENCONTRADO',
                'mensagem': f'Lançamento {id_movimentacao} não encontrado'
            }), 404
        
        # ✅ CORREÇÃO: obter_lancamento_com_classificacoes retorna {"lancamento": {..., "classificacoes": [...]}}
        lancamento_payload = lancamento.get('lancamento') or {}
        classificacoes = lancamento_payload.get('classificacoes', []) or lancamento.get('classificacoes', [])
        
        if not classificacoes:
            return jsonify({
                'sucesso': False,
                'erro': 'LANCAMENTO_NAO_CLASSIFICADO',
                'mensagem': f'Lançamento {id_movimentacao} não está classificado'
            }), 400
        
        # Remover cada classificação
        removidos = 0
        erros = 0
        
        for classificacao in classificacoes:
            id_lancamento_tipo_despesa = classificacao.get('id_lancamento_tipo_despesa')
            if id_lancamento_tipo_despesa:
                resultado = conciliacao_service.remover_classificacao(id_lancamento_tipo_despesa)
                if resultado.get('sucesso'):
                    removidos += 1
                else:
                    erros += 1
        
        if removidos > 0:
            return jsonify({
                'sucesso': True,
                'mensagem': f'✅ {removidos} classificação(ões) removida(s) do lançamento {id_movimentacao}',
                'removidos': removidos,
                'erros': erros
            }), 200
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'ERRO_REMOCAO',
                'mensagem': f'Erro ao remover classificações: {erros} erro(s)'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Erro ao desvincular lançamento: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/admin/remover-classificacao-imposto', methods=['POST'])
def admin_remover_classificacao_imposto():
    """
    Endpoint administrativo para remover classificações de impostos de importação
    de um processo específico para um determinado lançamento Siscomex.

    Útil para corrigir casos em que o mesmo pagamento de impostos foi vinculado
    a mais de um processo (ex.: GLT.0009/26 e GLT.0011/26 com o mesmo doc SISCOMEX).

    Body (JSON):
    {
        "processo_referencia": "GLT.0009/26",
        "data": "2026-01-22",
        "valor": 13337.88,
        "doc": "2103533900101"
    }
    """
    try:
        from utils.sql_server_adapter import get_sql_adapter
        from services.banco_concilacao_service import get_banco_concilacao_service

        data = request.get_json() or {}
        proc = (data.get('processo_referencia') or '').strip()
        data_mov = (data.get('data') or '').strip()
        valor = data.get('valor')
        doc = (data.get('doc') or '').strip()

        if not proc or not data_mov or valor is None or not doc:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETROS_INVALIDOS',
                'mensagem': 'Informe "processo_referencia", "data", "valor" e "doc".'
            }), 400

        sql_adapter = get_sql_adapter()
        if not sql_adapter:
            return jsonify({
                'sucesso': False,
                'erro': 'SQL_SERVER_INDISPONIVEL',
                'mensagem': 'SQL Server não disponível para limpar classificações.'
            }), 500

        proc_escaped = proc.replace("'", "''")
        proc_upper = proc.upper()
        doc_escaped = doc.replace("'", "''")

        query = f"""
            SELECT 
                ltd.id_lancamento_tipo_despesa,
                ltd.id_movimentacao_bancaria,
                mb.valor_movimentacao,
                mb.data_movimentacao,
                mb.descricao_movimentacao
            FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
            JOIN dbo.MOVIMENTACAO_BANCARIA mb 
              ON mb.id_movimentacao = ltd.id_movimentacao_bancaria
            WHERE (
                UPPER(LTRIM(RTRIM(ltd.processo_referencia))) = '{proc_upper}'
                OR LTRIM(RTRIM(ltd.processo_referencia)) = '{proc_escaped}'
            )
              AND CAST(mb.data_movimentacao AS DATE) = '{data_mov}'
              AND ABS(mb.valor_movimentacao - {float(valor)}) < 0.01
              AND CAST(mb.descricao_movimentacao AS VARCHAR(MAX)) LIKE '%{doc_escaped}%'
        """

        resultado = sql_adapter.execute_query(query, database=sql_adapter.database)
        if not resultado.get('success'):
            return jsonify({
                'sucesso': False,
                'erro': 'ERRO_CONSULTA',
                'mensagem': resultado.get('error', 'Erro ao consultar classificações para remoção.')
            }), 500

        rows = resultado.get('data') or []
        if not rows:
            return jsonify({
                'sucesso': False,
                'erro': 'NADA_ENCONTRADO',
                'mensagem': f'Nenhuma classificação encontrada para processo {proc} com esses filtros.'
            }), 404

        conciliacao_service = get_banco_concilacao_service()
        removidos = 0
        erros = 0
        detalhes = []

        for row in rows:
            if isinstance(row, dict):
                ild = row.get('id_lancamento_tipo_despesa')
                id_mov = row.get('id_movimentacao_bancaria')
                desc = row.get('descricao_movimentacao')
            else:
                ild = row[0]
                id_mov = row[1]
                desc = row[4] if len(row) > 4 else ''

            if not ild:
                continue

            resultado_remocao = conciliacao_service.remover_classificacao(int(ild))
            detalhes.append({
                'id_lancamento_tipo_despesa': ild,
                'id_movimentacao_bancaria': id_mov,
                'descricao': desc,
                'resultado': resultado_remocao
            })

            if resultado_remocao.get('sucesso'):
                removidos += 1
            else:
                erros += 1

        status_code = 200 if removidos > 0 else 500
        return jsonify({
            'sucesso': removidos > 0,
            'processo_referencia': proc,
            'removidos': removidos,
            'erros': erros,
            'detalhes': detalhes
        }), status_code

    except Exception as e:
        logger.error(f"❌ Erro no admin_remover_classificacao_imposto: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/impostos-processo/<path:processo_referencia>', methods=['GET'])
def buscar_impostos_processo(processo_referencia):
    """
    Busca impostos sugeridos de um processo (da DI/DUIMP).
    
    Path param:
        - processo_referencia: str (ex: BGR.0070/25)
    
    Query params:
        - numero_documento: str (opcional, filtra por DI/DUIMP específica)
        - tipo_documento: str (opcional, 'DI' ou 'DUIMP')
    
    Returns:
        JSON com lista de impostos sugeridos da DI/DUIMP
    """
    try:
        processo_ref = (processo_referencia or '').strip().upper()
        logger.info(
            f"🔍 [IMPOSTOS-PROCESSO] GET processo={processo_ref} "
            f"(raw={processo_referencia!r}) numero_documento={request.args.get('numero_documento')} tipo_documento={request.args.get('tipo_documento')}"
        )
        from services.imposto_valor_service import get_imposto_valor_service
        from db_manager import obter_dados_documentos_processo
        from db_manager import get_db_connection
        import json
        import sqlite3
        
        numero_documento = request.args.get('numero_documento')
        tipo_documento = request.args.get('tipo_documento')
        
        # Buscar impostos já gravados
        imposto_service = get_imposto_valor_service()
        resultado_gravados = imposto_service.buscar_impostos_processo(
            processo_referencia=processo_ref,
            numero_documento=numero_documento,
            tipo_documento=tipo_documento
        )

        # ✅ PERFORMANCE/UX: se já existem impostos gravados, devolver imediatamente.
        try:
            if (
                isinstance(resultado_gravados, dict)
                and resultado_gravados.get('sucesso') is True
                and int(resultado_gravados.get('total') or 0) > 0
            ):
                logger.info(
                    f"✅ [IMPOSTOS-PROCESSO] early-return impostos_gravados={resultado_gravados.get('total')} "
                    f"para processo={processo_ref}"
                )
                return jsonify({
                    'sucesso': True,
                    'impostos_gravados': resultado_gravados.get('impostos', []),
                    'impostos_sugeridos': [],
                    'total_gravados': resultado_gravados.get('total', 0),
                    'total_sugeridos': 0
                }), 200
        except Exception:
            pass
        
        # ✅ PRIORIDADE 1 (26/01/2026): Processo consolidado SQL Server (mesma fonte do status/chat que mostra impostos)
        impostos_sugeridos = []
        pagamentos = []
        numero_di = ''
        fonte = None
        try:
            from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
            from services.db_policy_service import get_legacy_database, should_use_legacy_database
            consolidated = buscar_processo_consolidado_sql_server(processo_ref)
            if not consolidated and should_use_legacy_database(processo_ref):
                consolidated = buscar_processo_consolidado_sql_server(processo_ref, database=get_legacy_database())
                if consolidated:
                    logger.info(f"✅ [IMPOSTOS-PROCESSO] Processo {processo_ref} encontrado no legado (Make)")
            if consolidated and consolidated.get('di'):
                di_cons = consolidated['di']
                pagamentos = di_cons.get('pagamentos') or []
                numero_di = di_cons.get('numero', '') or numero_di
                if pagamentos:
                    fonte = 'consolidado'
                    logger.info(
                        f"✅ [IMPOSTOS-PROCESSO] {len(pagamentos)} pagamento(s) da DI (consolidado) para {processo_ref}"
                    )
                else:
                    logger.debug(f"🔍 [IMPOSTOS-PROCESSO] Consolidado tem DI mas sem pagamentos para {processo_ref}")
            else:
                logger.debug(f"🔍 [IMPOSTOS-PROCESSO] Consolidado sem DI para {processo_ref} (consolidated={bool(consolidated)})")
        except Exception as e:
            logger.warning(f"⚠️ [IMPOSTOS-PROCESSO] Erro ao buscar consolidado para {processo_ref}: {e}")
        
        # ✅ PRIORIDADE 2: obter_dados_documentos_processo (Kanban + di_documento_handler). Sempre chamar (DUIMP usa dados_docs).
        dados_docs = obter_dados_documentos_processo(processo_ref, usar_sql_server=True)
        if not pagamentos:
            di_data = dados_docs.get('dis', [])
            logger.info(f"🔍 [IMPOSTOS-PROCESSO] obter_dados: dis={len(di_data)} para {processo_ref}")
            if di_data and len(di_data) > 0:
                di = di_data[0]
                numero_di = di.get('numero', '') or di.get('numero_di', '') or numero_di
                dados_completos = di.get('dados_completos', {})
                if isinstance(dados_completos, str):
                    try:
                        dados_completos = json.loads(dados_completos)
                    except Exception:
                        dados_completos = {}
                pagamentos = (
                    (dados_completos.get('pagamentos', []) if isinstance(dados_completos, dict) else [])
                    or di.get('pagamentos', [])
                    or []
                )
                if pagamentos:
                    fonte = 'dados_docs'
                    logger.info(
                        f"✅ [IMPOSTOS-PROCESSO] {len(pagamentos)} pagamento(s) da DI (dados_docs) para {processo_ref}"
                    )
        
        # Mapear pagamentos → impostos_sugeridos (consolidado ou dados_docs)
        if pagamentos:
            logger.debug(f"📋 Primeiro pagamento (exemplo): {pagamentos[0] if pagamentos else 'N/A'}")
            codigos_receita = {
                '0086': 'II', '86': 'II',
                '1038': 'IPI', '38': 'IPI',
                '5602': 'PIS', '602': 'PIS',
                '5629': 'COFINS', '629': 'COFINS',
                '5529': 'ANTIDUMPING', '529': 'ANTIDUMPING',
                '7811': 'TAXA_UTILIZACAO', '811': 'TAXA_UTILIZACAO',
            }
            for pagamento in pagamentos:
                tipo_imposto = pagamento.get('tipo')
                valor = pagamento.get('valor') or pagamento.get('valorTotal') or pagamento.get('valor_total') or 0
                codigo = pagamento.get('codigo_receita') or pagamento.get('codigoReceita') or ''
                if not tipo_imposto and codigo:
                    tipo_imposto = codigos_receita.get(str(codigo).strip(), 'OUTROS')
                if not tipo_imposto:
                    nome = pagamento.get('nomeReceita') or pagamento.get('nome_receita') or pagamento.get('nome') or ''
                    if 'IMPORTAÇÃO' in nome.upper() or 'IMPORTACAO' in nome.upper():
                        tipo_imposto = 'II'
                    elif 'IPI' in nome.upper():
                        tipo_imposto = 'IPI'
                    elif 'PIS' in nome.upper():
                        tipo_imposto = 'PIS'
                    elif 'COFINS' in nome.upper():
                        tipo_imposto = 'COFINS'
                    else:
                        tipo_imposto = 'OUTROS'
                try:
                    valor_float = float(valor) if valor else 0.0
                except (ValueError, TypeError):
                    valor_float = 0.0
                if tipo_imposto and tipo_imposto != 'OUTROS' and valor_float > 0:
                    nome_receita = pagamento.get('nomeReceita') or pagamento.get('nome_receita') or pagamento.get('nome') or f'Imposto {tipo_imposto}'
                    impostos_sugeridos.append({
                        'tipo_imposto': tipo_imposto,
                        'codigo_receita': codigo or '',
                        'nome_receita': nome_receita,
                        'valor_brl': valor_float,
                        'numero_documento': numero_di,
                        'tipo_documento': 'DI'
                    })
                    logger.info(f"💰 Imposto encontrado: {tipo_imposto} (código {codigo}) = R$ {valor_float:,.2f}")

        # ✅ NOVO: Buscar DUIMP e sugerir tributos separados (igual DI)
        # Estratégia:
        # - Priorizar snapshot do Kanban (processos_kanban.dados_completos_json), que costuma conter `duimp[].tributos_calculados`
        # - Se não tiver, tentar `dados_docs['duimps']` quando vier payload completo
        try:
            def _norm_tipo_imp(s):
                t = str(s or "").strip().upper()
                if not t:
                    return ""
                t = t.replace("TAXA SISCOMEX", "TAXA_UTILIZACAO")
                t = t.replace("TAXA_UTILIZAÇÃO", "TAXA_UTILIZACAO")
                t = t.replace("TAXA UTILIZACAO", "TAXA_UTILIZACAO")
                return t

            def _append_imposto_duimp(tipo_imp, valor_imp, numero_duimp):
                tipo_norm = _norm_tipo_imp(tipo_imp)
                if not tipo_norm:
                    return
                try:
                    v = float(valor_imp) if valor_imp is not None else 0.0
                except Exception:
                    v = 0.0
                if v <= 0:
                    return
                impostos_sugeridos.append({
                    'tipo_imposto': tipo_norm,
                    'codigo_receita': '',
                    'nome_receita': f'Tributo {tipo_norm}',
                    'valor_brl': v,
                    'numero_documento': str(numero_duimp or '').strip(),
                    'tipo_documento': 'DUIMP'
                })

            # Descobrir DUIMP prioritária (Kanban/cache costuma ter)
            numero_duimp_cache = None
            try:
                conn = get_db_connection()
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    "SELECT numero_duimp, dados_completos_json FROM processos_kanban WHERE processo_referencia = ? LIMIT 1",
                    (processo_ref,),
                )
                row = cur.fetchone()
                conn.close()
                if row and row["numero_duimp"]:
                    numero_duimp_cache = str(row["numero_duimp"]).strip()
                dados_json = {}
                if row and row["dados_completos_json"]:
                    try:
                        dados_json = json.loads(row["dados_completos_json"])
                    except Exception:
                        dados_json = {}

                # Tentar tributos_calculados no snapshot do Kanban
                if numero_duimp_cache and isinstance(dados_json, dict):
                    duimps_json = dados_json.get("duimp")
                    if isinstance(duimps_json, list):
                        for d in duimps_json:
                            if not isinstance(d, dict):
                                continue
                            if str(d.get("numero") or "").strip() != numero_duimp_cache:
                                continue
                            tributos = d.get("tributos_calculados") or d.get("tributosCalculados") or []
                            if isinstance(tributos, list) and len(tributos) > 0:
                                for t in tributos:
                                    if not isinstance(t, dict):
                                        continue
                                    tipo_imp = t.get("tipo") or t.get("tipo_imposto") or t.get("tributo_tipo")
                                    valor_imp = (
                                        t.get("valor_a_recolher")
                                        or t.get("valor_recolhido")
                                        or t.get("valor_calculado")
                                        or t.get("valor_devido")
                                        or t.get("valor")
                                        or 0
                                    )
                                    _append_imposto_duimp(tipo_imp, valor_imp, numero_duimp_cache)
                            else:
                                # fallback: pagamentos dentro da DUIMP do Kanban
                                pagamentos_duimp = d.get("pagamentos") or []
                                if isinstance(pagamentos_duimp, list):
                                    for p in pagamentos_duimp:
                                        if not isinstance(p, dict):
                                            continue
                                        tipo_imp = p.get("tributo_tipo") or p.get("tributoTipo") or p.get("tipo") or p.get("tipo_imposto")
                                        valor_imp = p.get("valor") or p.get("valorTotal") or p.get("valor_total") or 0
                                        _append_imposto_duimp(tipo_imp, valor_imp, numero_duimp_cache)
                            break
            except Exception as e:
                logger.debug(f"⚠️ Erro ao buscar DUIMP/tributos no snapshot do Kanban para {processo_ref}: {e}")

            # Se não achou no Kanban, tentar DUIMP via documentos do processo (quando houver payload completo)
            if not any(i.get('tipo_documento') == 'DUIMP' for i in impostos_sugeridos):
                duimps_data = dados_docs.get('duimps', [])
                if isinstance(duimps_data, list) and len(duimps_data) > 0:
                    d0 = duimps_data[0]
                    if isinstance(d0, dict):
                        numero_duimp = d0.get('numero_duimp') or d0.get('numero_duimp') or d0.get('numero') or numero_duimp_cache
                        duimp_completo = d0.get('dados_completos') or {}
                        if isinstance(duimp_completo, str):
                            try:
                                duimp_completo = json.loads(duimp_completo)
                            except Exception:
                                duimp_completo = {}

                        tributos = duimp_completo.get('tributos_calculados') if isinstance(duimp_completo, dict) else None
                        if isinstance(tributos, list) and len(tributos) > 0:
                            for t in tributos:
                                if not isinstance(t, dict):
                                    continue
                                tipo_imp = t.get("tipo") or t.get("tipo_imposto") or t.get("tributo_tipo")
                                valor_imp = (
                                    t.get("valor_a_recolher")
                                    or t.get("valor_recolhido")
                                    or t.get("valor_calculado")
                                    or t.get("valor_devido")
                                    or t.get("valor")
                                    or 0
                                )
                                _append_imposto_duimp(tipo_imp, valor_imp, numero_duimp)
        except Exception as e:
            logger.debug(f"⚠️ Erro ao sugerir impostos de DUIMP para {processo_ref}: {e}")
        
        logger.info(
            f"📊 [IMPOSTOS-PROCESSO] Total sugeridos para {processo_ref}: {len(impostos_sugeridos)} "
            f"(fonte DI={fonte or 'nenhuma'})"
        )
        
        return jsonify({
            'sucesso': True,
            'impostos_gravados': resultado_gravados.get('impostos', []),
            'impostos_sugeridos': impostos_sugeridos,
            'total_gravados': resultado_gravados.get('total', 0),
            'total_sugeridos': len(impostos_sugeridos)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar impostos do processo: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/classificar-lancamento', methods=['POST'])
def classificar_lancamento():
    """
    Classifica um lançamento bancário vinculando-o a tipos de despesa e processos.
    
    ✅ NOVO: Suporta serviço V2 (robusto) via parâmetro ?v2=true
    
    Body JSON:
    {
        "id_movimentacao": 123,
        "classificacoes": [
            {
                "id_tipo_despesa": 1,
                "processo_referencia": "DMD.0083/25",
                "valor_despesa": 5000.00,  // Opcional
                "percentual_valor": 50.0   // Opcional
            },
            {
                "id_tipo_despesa": 3,
                "processo_referencia": "DMD.0083/25",
                "valor_despesa": 3000.00
            }
        ],
        "distribuicao_impostos": {...},  // Opcional
        "processo_referencia": "DMD.0083/25"  // Opcional
    }
    
    Query params:
        - v2: bool (opcional, padrão: false) - Se true, usa serviço V2 (robusto)
    
    Returns:
        JSON com sucesso e mensagem
    """
    try:
        # ✅ NOVO: Verificar se deve usar serviço V2
        usar_v2 = request.args.get('v2', 'false').lower() == 'true'
        service_v2 = None
        service_legacy = None
        
        if usar_v2:
            from services.banco_concilacao_service_v2 import get_banco_concilacao_service_v2
            service_v2 = get_banco_concilacao_service_v2()
            logger.info("🔒 Usando serviço V2 (robusto) para classificação")
        else:
            from services.banco_concilacao_service import get_banco_concilacao_service
            service_legacy = get_banco_concilacao_service()
            logger.info("📊 Usando serviço original para classificação")
        
        data = request.get_json() or {}
        id_movimentacao = data.get('id_movimentacao')

        # ✅ Robustez: `classificacoes` deve ser lista (mas pode vir como dict/None/valor inválido)
        raw_classificacoes = data.get('classificacoes', [])
        if raw_classificacoes is None:
            classificacoes = []
        elif isinstance(raw_classificacoes, list):
            classificacoes = raw_classificacoes
        elif isinstance(raw_classificacoes, dict):
            classificacoes = [raw_classificacoes]
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_INVALIDO',
                'mensagem': f'Parâmetro "classificacoes" deve ser uma lista (recebido: {type(raw_classificacoes).__name__})'
            }), 400

        distribuicao_impostos = data.get('distribuicao_impostos')  # ✅ NOVO: Distribuição de impostos
        processo_referencia = data.get('processo_referencia')  # ✅ NOVO: Processo para impostos (quando não há classificações)

        # ✅ Robustez: aceitar distribuicao_impostos como dict OU lista [{tipo_imposto, valor_brl}, ...]
        if isinstance(distribuicao_impostos, list):
            distribuicao_dict = {}
            for item in distribuicao_impostos:
                if isinstance(item, dict):
                    tipo = item.get('tipo_imposto') or item.get('tipo') or item.get('imposto')
                    valor = item.get('valor_brl') if 'valor_brl' in item else item.get('valor')
                    if tipo is not None and valor is not None:
                        distribuicao_dict[str(tipo)] = valor
            distribuicao_impostos = distribuicao_dict
        elif distribuicao_impostos is not None and not isinstance(distribuicao_impostos, dict):
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_INVALIDO',
                'mensagem': f'Parâmetro "distribuicao_impostos" deve ser um objeto/dict (recebido: {type(distribuicao_impostos).__name__})'
            }), 400
        
        # ✅ DEBUG: Logar o que está sendo recebido
        logger.info(f"🔍 [DEBUG classificar_lancamento] Recebido:")
        logger.info(f"   - id_movimentacao: {id_movimentacao}")
        logger.info(f"   - classificacoes len: {len(classificacoes) if isinstance(classificacoes, list) else 0}")
        logger.info(f"   - distribuicao_impostos: {bool(distribuicao_impostos)}")
        if isinstance(distribuicao_impostos, dict):
            logger.info(f"   - distribuicao_impostos keys: {list(distribuicao_impostos.keys()) if distribuicao_impostos else 'N/A'}")
        else:
            logger.info(f"   - distribuicao_impostos type: {type(distribuicao_impostos).__name__}")
        logger.info(f"   - processo_referencia (do body): {processo_referencia}")
        
        if not id_movimentacao:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'Parâmetro "id_movimentacao" é obrigatório'
            }), 400
        
        # ✅ CORREÇÃO: Se houver distribuição de impostos, não exigir classificações
        tem_distribuicao_impostos = isinstance(distribuicao_impostos, dict) and len(distribuicao_impostos) > 0
        if not tem_distribuicao_impostos and (not classificacoes or len(classificacoes) == 0):
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'É necessário fornecer "classificacoes" ou "distribuicao_impostos"'
            }), 400
        
        # ✅ NOVO: Obter usuário da sessão (se disponível) para auditoria
        usuario = None
        try:
            # Tentar obter da sessão Flask (flask.session)
            if 'user_id' in session:
                usuario = session.get('user_id')
            # Ou de headers customizados
            elif request.headers.get('X-User-ID'):
                usuario = request.headers.get('X-User-ID')
        except:
            pass
        
        # Chamar serviço (V2 ou original)
        if usar_v2:
            assert service_v2 is not None
            resultado = service_v2.classificar_lancamento(
                id_movimentacao=id_movimentacao,
                classificacoes=classificacoes,
                distribuicao_impostos=distribuicao_impostos,
                processo_referencia=processo_referencia,
                usuario=usuario  # ✅ NOVO: Passar usuário para auditoria
            )
        else:
            assert service_legacy is not None
            # ✅ NOVO (24/01/2026): Adicionar natureza_recurso se vier do frontend
            natureza_recurso = data.get('natureza_recurso')
            if natureza_recurso and classificacoes:
                for c in classificacoes:
                    c['natureza_recurso'] = natureza_recurso

            resultado = service_legacy.classificar_lancamento(
                id_movimentacao=id_movimentacao,
                classificacoes=classificacoes,
                distribuicao_impostos=distribuicao_impostos,
                processo_referencia=processo_referencia
            )
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 400
    except Exception as e:
        logger.error(f"❌ Erro ao classificar lançamento: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/lastro-cliente', methods=['GET'])
def get_lastro_cliente():
    """Obtém o saldo da carteira virtual do cliente (lastro financeiro)."""
    try:
        from services.banco_carteira_virtual_service import BancoCarteiraVirtualService
        from services.processo_repository import ProcessoRepository
        
        processo_ref = request.args.get('processo')
        if not processo_ref:
            return jsonify({'sucesso': False, 'erro': 'Processo não informado'}), 400
            
        # 1. Descobrir o CNPJ do importador do processo
        repo = ProcessoRepository()
        proc = repo.buscar_por_referencia(processo_ref)
        
        if not proc or not proc.dados_completos:
            return jsonify({'sucesso': False, 'erro': 'Processo não encontrado'}), 404
            
        di = proc.dados_completos.get('di', {})
        duimp = proc.dados_completos.get('duimp', {})
        cnpj = di.get('cnpj_importador') or duimp.get('cnpj_importador')
        
        if not cnpj:
            return jsonify({'sucesso': False, 'erro': 'CNPJ do importador não encontrado'}), 404
            
        # 2. Buscar saldo
        service = BancoCarteiraVirtualService()
        saldo = service.obter_saldo_cliente(cnpj)
        
        return jsonify({
            'sucesso': True,
            'cnpj': cnpj,
            'saldo': float(saldo)
        })
    except Exception as e:
        logger.error(f"❌ Erro ao obter lastro do cliente: {e}", exc_info=True)
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@app.route('/api/banco/lancamento/<int:id_movimentacao>/classificacoes', methods=['GET'])
def obter_lancamento_classificacoes(id_movimentacao):
    """
    Obtém um lançamento bancário com suas classificações.
    
    Returns:
        JSON com dados do lançamento e suas classificações
    """
    try:
        from services.banco_concilacao_service import get_banco_concilacao_service
        
        service = get_banco_concilacao_service()
        resultado = service.obter_lancamento_com_classificacoes(id_movimentacao=id_movimentacao)
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 404
    except Exception as e:
        logger.error(f"❌ Erro ao obter lançamento com classificações: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': str(e)
        }), 500


@app.route('/api/banco/classificacoes/<int:id_movimentacao>', methods=['GET'])
def obter_classificacoes_lancamento(id_movimentacao):
    """
    Obtém todas as classificações de um lançamento.
    
    Path param:
        - id_movimentacao: int
    
    Returns:
        JSON com lista de classificações do lançamento
    """
    try:
        from services.banco_concilacao_service import get_banco_concilacao_service
        
        service = get_banco_concilacao_service()
        resultado = service.obter_lancamento_com_classificacoes(id_movimentacao=id_movimentacao)
        
        return jsonify(resultado), 200 if resultado.get('sucesso') else 500
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter classificações: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e)
        }), 500


@app.route('/api/banco/lancamento/<int:id_movimentacao>/sugestoes-split', methods=['GET'])
def sugerir_split_lancamento(id_movimentacao: int):
    """
    Sugere classificações (split) para um lançamento bancário.

    ✅ Read-only: não grava nada.
    ✅ Pensado para preencher automaticamente o modal de conciliação (split por processo + tipo de despesa).

    Query params:
      - limite_processos: int (padrão: 3) — quantos processos sugerir quando só houver categoria/cliente na descrição.
    """
    try:
        limite_processos = request.args.get('limite_processos', '3')
        try:
            limite_processos_int = max(2, min(5, int(limite_processos)))
        except Exception:
            limite_processos_int = 3

        from services.banco_split_suggestion_service import get_banco_split_suggestion_service

        service = get_banco_split_suggestion_service()
        resultado = service.sugerir_split(
            id_movimentacao=id_movimentacao,
            limite_processos=limite_processos_int,
        )
        status = 200 if resultado.get('sucesso', True) else 404
        return jsonify(resultado), status
    except Exception as e:
        logger.error(f"❌ Erro ao sugerir split do lançamento {id_movimentacao}: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': f'Erro ao sugerir split: {str(e)}'
        }), 500


@app.route('/api/notificacoes', methods=['GET'])
def get_notificacoes():
    """Endpoint para buscar notificações não lidas (polling)"""
    try:
        from db_manager import get_db_connection
        
        # Parâmetros opcionais
        apenas_nao_lidas = request.args.get('apenas_nao_lidas', 'true').lower() == 'true'
        limite = int(request.args.get('limite', 50))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if apenas_nao_lidas:
            cursor.execute('''
                SELECT id, processo_referencia, tipo_notificacao, titulo, mensagem, 
                       dados_extras, criado_em
                FROM notificacoes_processos
                WHERE lida = 0
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (limite,))
        else:
            cursor.execute('''
                SELECT id, processo_referencia, tipo_notificacao, titulo, mensagem, 
                       dados_extras, criado_em, lida
                FROM notificacoes_processos
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (limite,))
        
        notificacoes = []
        for row in cursor.fetchall():
            notif = {
                'id': row[0],
                'processo_referencia': row[1],
                'tipo_notificacao': row[2],
                'titulo': row[3],
                'mensagem': row[4],
                'dados_extras': safe_json_loads(row[5], default={}),
                'criado_em': row[6].isoformat() if hasattr(row[6], 'isoformat') else str(row[6]),
                'lida': row[7] if len(row) > 7 else False
            }
            notificacoes.append(notif)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'notificacoes': notificacoes,
            'total': len(notificacoes)
        })
    except Exception as e:
        logger.error(f"❌ Erro ao buscar notificações: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'notificacoes': []
        }), 500


@app.route('/api/notificacoes/<int:notificacao_id>/marcar-lida', methods=['POST'])
def marcar_notificacao_lida(notificacao_id):
    """Endpoint para marcar notificação como lida"""
    try:
        from db_manager import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE notificacoes_processos
            SET lida = 1, lida_em = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (notificacao_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"❌ Erro ao marcar notificação como lida: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoramento/ocorrencias/rodar', methods=['POST'])
def rodar_monitoramento_ocorrencias():
    """
    Executa o monitoramento de ocorrências "agora" (MVP):
    - Navio em atraso (ETA vencida sem chegada) agrupado por navio
    - SLA/tempo parado por etapa (baseado em etapa_kanban)
    """
    try:
        from services.monitoramento_ocorrencias_service import get_monitoramento_ocorrencias_service
        svc = get_monitoramento_ocorrencias_service()
        resultado = svc.executar()
        status = 200 if resultado.get('sucesso', True) else 500
        return jsonify(resultado), status
    except Exception as e:
        logger.error(f"❌ Erro ao rodar monitoramento de ocorrências: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e),
        }), 500


@app.route('/api/ocorrencias', methods=['GET'])
def listar_ocorrencias():
    """Lista ocorrências (default: open)."""
    try:
        status = request.args.get('status', 'open').lower().strip()
        limite = int(request.args.get('limite', '50'))
        limite = max(1, min(200, limite))

        from db_manager import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        if status in ('open', 'closed'):
            cursor.execute(
                """
                SELECT id, record_key, tipo, severidade, processo_referencia, nome_navio, etapa_kanban,
                       titulo, mensagem, dados_extras, status, first_seen_at, last_seen_at, last_notified_at
                FROM ocorrencias_processos
                WHERE status = ?
                ORDER BY last_seen_at DESC
                LIMIT ?
                """,
                (status, limite),
            )
        else:
            cursor.execute(
                """
                SELECT id, record_key, tipo, severidade, processo_referencia, nome_navio, etapa_kanban,
                       titulo, mensagem, dados_extras, status, first_seen_at, last_seen_at, last_notified_at
                FROM ocorrencias_processos
                ORDER BY last_seen_at DESC
                LIMIT ?
                """,
                (limite,),
            )

        ocorrencias = []
        for row in cursor.fetchall():
            ocorrencias.append({
                'id': row[0],
                'record_key': row[1],
                'tipo': row[2],
                'severidade': row[3],
                'processo_referencia': row[4],
                'nome_navio': row[5],
                'etapa_kanban': row[6],
                'titulo': row[7],
                'mensagem': row[8],
                'dados_extras': safe_json_loads(row[9], default={}),
                'status': row[10],
                'first_seen_at': row[11].isoformat() if hasattr(row[11], 'isoformat') else str(row[11]),
                'last_seen_at': row[12].isoformat() if hasattr(row[12], 'isoformat') else str(row[12]),
                'last_notified_at': row[13].isoformat() if (row[13] and hasattr(row[13], 'isoformat')) else (str(row[13]) if row[13] else None),
            })
        conn.close()

        return jsonify({
            'sucesso': True,
            'status': status,
            'total': len(ocorrencias),
            'ocorrencias': ocorrencias,
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro ao listar ocorrências: {e}", exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'ocorrencias': [],
        }), 500


@app.route('/api/relatorio/averbacoes', methods=['POST'])
def gerar_relatorio_averbacoes():
    """
    Gera relatório de averbações de seguro.
    
    Body JSON:
    {
        "mes": "2025-06" ou "06",  # Formato YYYY-MM ou MM
        "ano": 2025,  # Opcional se fornecido no mes
        "categoria": "BND"  # Opcional (BND, ALH, VDM, etc.)
    }
    """
    try:
        data = request.get_json() or {}
        mes = data.get('mes', '')
        ano = data.get('ano')
        categoria = data.get('categoria')
        
        if not mes:
            return jsonify({
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'Parâmetro "mes" é obrigatório (formato: "2025-06" ou "06")'
            }), 400
        
        from services.relatorio_averbacoes_service import RelatorioAverbacoesService
        
        service = RelatorioAverbacoesService()
        resultado = service.gerar_relatorio_averbacoes(mes=mes, ano=ano, categoria=categoria)
        
        if resultado.get('sucesso'):
            # Retornar caminho relativo para download
            caminho_arquivo = resultado.get('caminho_arquivo', '')
            if caminho_arquivo:
                # Extrair apenas o nome do arquivo
                nome_arquivo = Path(caminho_arquivo).name
                resultado['arquivo'] = f'/api/download/{nome_arquivo}'
            
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f'❌ Erro ao gerar relatório de averbações: {e}', exc_info=True)
        return jsonify({
            'sucesso': False,
            'erro': 'ERRO_INTERNO',
            'mensagem': f'Erro ao gerar relatório: {str(e)}'
        }), 500


@app.route('/api/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """Endpoint para download de arquivos (PDFs, TTS, etc)."""
    from flask import send_from_directory
    import os
    
    # Segurança: apenas permitir arquivos do diretório downloads
    downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
    
    # O filename pode vir como "downloads/tts/nome.mp3" ou apenas "tts/nome.mp3" ou "nome.pdf"
    # Remover "downloads/" do início se presente
    if filename.startswith('downloads/'):
        filename = filename[len('downloads/'):]
    
    file_path = os.path.join(downloads_dir, filename)
    
    # Verificar que o arquivo está dentro do diretório downloads (prevenção de path traversal)
    downloads_dir_abs = os.path.abspath(downloads_dir)
    file_path_abs = os.path.abspath(file_path)
    
    if not file_path_abs.startswith(downloads_dir_abs):
        logger.warning(f'Tentativa de acesso a arquivo fora de downloads: {filename}')
        return jsonify({
            'sucesso': False,
            'erro': 'Acesso negado'
        }), 403
    
    if not os.path.exists(file_path):
        logger.warning(f'❌ Arquivo não encontrado: {file_path} (filename recebido: {filename})')
        logger.warning(f'   downloads_dir: {downloads_dir}')
        logger.warning(f'   file_path_abs: {file_path_abs}')
        return jsonify({
            'sucesso': False,
            'erro': f'Arquivo não encontrado: {filename}'
        }), 404
    
    # Determinar mimetype baseado na extensão
    mimetype = 'application/octet-stream'
    if filename.endswith('.pdf'):
        mimetype = 'application/pdf'
    elif filename.endswith('.mp3'):
        mimetype = 'audio/mpeg'
    elif filename.endswith('.wav'):
        mimetype = 'audio/wav'
    elif filename.endswith('.png'):
        mimetype = 'image/png'
    elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
        mimetype = 'image/jpeg'
    
    logger.debug(f'📁 Servindo arquivo: {filename} (mimetype: {mimetype})')
    
    # Se o arquivo está em subdiretório (ex: tts/arquivo.mp3), precisamos enviar do diretório pai
    # mas com o caminho relativo correto
    if os.path.sep in filename:
        # Arquivo em subdiretório (ex: tts/arquivo.mp3)
        # send_from_directory precisa do diretório base e do caminho relativo
        return send_from_directory(
            downloads_dir,
            filename,
            as_attachment=False,
            mimetype=mimetype
        )
    else:
        # Arquivo na raiz de downloads
        return send_from_directory(
            downloads_dir,
            filename,
            as_attachment=False,
            mimetype=mimetype
        )


# ============================================================================
# Endpoints para Classif (Nomenclatura Fiscal - NCM)
# ============================================================================

@app.route('/api/int/classif/baixar-nomenclatura', methods=['POST'])
def baixar_nomenclatura():
    """Baixa o arquivo JSON da nomenclatura do Portal Único e processa no cache local.
    
    Este endpoint:
    1. Faz download do arquivo JSON da nomenclatura do ambiente de validação
    2. Processa o arquivo e extrai informações de NCM (código, descrição)
    3. Salva no cache local (SQLite) - tabela classif_cache
    4. Retorna estatísticas do processamento
    
    ⚠️ IMPORTANTE: O JSON do Portal Único NÃO contém unidade estatística.
    A unidade estatística deve ser consultada em outro endpoint ou tabela.
    """
    try:
        from datetime import datetime
        from db_manager import init_classif_cache, save_classif_ncm, set_classif_last_update, get_db_connection
        import sqlite3
        
        # Inicializar cache se necessário
        init_classif_cache()
        
        # URL do ambiente de validação (conforme classif.json)
        url_nomenclatura = 'https://val.portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json'
        
        logger.info(f'[CLASSIF] Iniciando download da nomenclatura de: {url_nomenclatura}')
        
        # Fazer download (sem autenticação - é serviço público)
        # ✅ Aumentar timeout para 15 minutos (arquivo muito grande)
        response = requests.get(url_nomenclatura, timeout=900)  # 15 minutos de timeout
        
        if response.status_code != 200:
            return jsonify({
                'error': 'ERRO_DOWNLOAD',
                'message': f'Erro ao baixar nomenclatura. Status: {response.status_code}',
                'status_code': response.status_code
            }), response.status_code
        
        # Tentar parsear como JSON
        try:
            nomenclatura = response.json()
            logger.info(f'[CLASSIF] JSON baixado (tipo): {type(nomenclatura).__name__}')
            if isinstance(nomenclatura, dict):
                logger.info(f'[CLASSIF] JSON é dict, chaves: {list(nomenclatura.keys())[:10]}')
            elif isinstance(nomenclatura, list):
                logger.info(f'[CLASSIF] JSON é list, tamanho: {len(nomenclatura)}')
        except json.JSONDecodeError as e:
            logger.error(f'[CLASSIF] Erro ao parsear JSON: {str(e)}')
            conteudo_preview = response.text[:500] if hasattr(response, 'text') else str(response.content)[:500]
            logger.error(f'[CLASSIF] Preview do conteúdo recebido: {conteudo_preview}')
            return jsonify({
                'error': 'ERRO_JSON',
                'message': f'Erro ao parsear JSON da nomenclatura: {str(e)}'
            }), 400
        
        # Processar nomenclatura conforme estrutura real da API Classif
        # Estrutura: {"Data_Ultima_Atualizacao_NCM": "...", "Ato": {...}, "Nomenclaturas": [...]}
        ncm_processados = 0
        ncm_com_unidade = 0
        
        # Extrair lista de nomenclaturas conforme estrutura real
        if isinstance(nomenclatura, dict):
            # Estrutura oficial: {"Nomenclaturas": [...]}
            lista_ncms = nomenclatura.get('Nomenclaturas', nomenclatura.get('nomenclaturas', []))
            if not lista_ncms:
                # Tentar outras variações
                lista_ncms = nomenclatura.get('itens', nomenclatura.get('ncms', nomenclatura.get('nomenclatura', [])))
        elif isinstance(nomenclatura, list):
            # Se já for uma lista direta
            lista_ncms = nomenclatura
        else:
            logger.error(f'[CLASSIF] Formato não reconhecido: {type(nomenclatura).__name__}')
            return jsonify({
                'error': 'FORMATO_INVALIDO',
                'message': f'Formato do JSON da nomenclatura não reconhecido. Tipo recebido: {type(nomenclatura).__name__}'
            }), 400
        
        if not lista_ncms or len(lista_ncms) == 0:
            logger.error(f'[CLASSIF] Lista de nomenclaturas vazia ou não encontrada.')
            return jsonify({
                'error': 'LISTA_VAZIA',
                'message': 'Lista de nomenclaturas vazia ou não encontrada no JSON',
                'chaves_encontradas': list(nomenclatura.keys()) if isinstance(nomenclatura, dict) else []
            }), 400
        
        logger.info(f'[CLASSIF] Processando {len(lista_ncms)} itens da nomenclatura')
        
        # Processar cada item
        for item in lista_ncms:
            if not isinstance(item, dict):
                continue
            
            # Tentar extrair NCM - estrutura real: campo "Codigo" (com C maiúsculo)
            # Pode vir com pontos: "07.03.20.90" ou sem: "07032090"
            ncm = (item.get('Codigo') or  # ← Estrutura real do JSON Classif
                   item.get('codigo') or 
                   item.get('ncm') or 
                   item.get('codigoNcm') or 
                   item.get('codigoNCM') or 
                   item.get('codigo_ncm') or
                   item.get('codigo_nc') or
                   item.get('codigoNomenclatura') or
                   item.get('numeroNcm') or
                   item.get('ncmCodigo'))
            
            # Se não encontrou, tentar com todas as chaves (case insensitive)
            if not ncm:
                for key, value in item.items():
                    if key.lower() in ('ncm', 'codigoncm', 'codigo', 'codigo_ncm'):
                        ncm = value
                        break
            
            if not ncm:
                continue
            
            # Normalizar NCM (remover formatação)
            # O Codigo pode vir como "07.03.20.90" → precisa remover pontos
            ncm_str = str(ncm).strip().replace('.', '').replace('-', '').replace(' ', '')
            
            # Se tiver mais de 8 dígitos, pegar só os 8 primeiros (pode ter dígitos verificadores)
            if len(ncm_str) > 8:
                ncm_str = ncm_str[:8]
            
            # ✅ CORREÇÃO: Aceitar NCMs de 4, 6 ou 8 dígitos
            # NCMs de 4 dígitos são importantes para a hierarquia (ex: 0703 = "Cebolas, chalotas, alhos...")
            # NCMs de 6 dígitos são importantes para a hierarquia (ex: 070320 = "Alhos")
            # NCMs de 8 dígitos são os subitens (ex: 07032010, 07032090)
            if len(ncm_str) < 4 or not ncm_str.isdigit():
                continue
            
            # Validar tamanho: deve ser 4, 6 ou 8 dígitos
            if len(ncm_str) not in [4, 6, 8]:
                continue
            
            # ⚠️ IMPORTANTE: Este JSON da Classif NÃO contém unidade estatística
            # A unidade estatística deve ser consultada em outro endpoint ou tabela
            # Por enquanto, deixar vazio (será preenchido manualmente ou por outra fonte)
            unidade = None  # Este JSON não fornece unidade estatística
            
            # Log informativo (apenas primeiro item)
            if ncm_processados == 0:
                logger.warning('[CLASSIF] ⚠️ ATENÇÃO: O JSON da Classif não contém campo de unidade estatística. Este campo será deixado vazio no cache.')
            
            # Descrição - estrutura real: campo "Descricao" (com D maiúsculo)
            descricao = (item.get('Descricao') or  # ← Estrutura real do JSON Classif
                        item.get('descricao') or 
                        item.get('descricaoNcm') or 
                        item.get('descricao_ncm') or
                        item.get('descricaoMercadoria') or
                        item.get('descricao_mercadoria') or
                        item.get('nome') or
                        item.get('texto') or
                        '')
            
            # ✅ CORREÇÃO: Limpar descrição (remover hífen inicial e espaços extras)
            # Exemplo: "- Alhos" → "Alhos"
            if descricao:
                descricao = descricao.strip()
                # Remover hífen inicial seguido de espaço
                if descricao.startswith('- '):
                    descricao = descricao[2:].strip()
                elif descricao.startswith('-'):
                    descricao = descricao[1:].strip()
            
            # ✅ CORREÇÃO: Salvar NCMs de 4, 6 e 8 dígitos
            # NCMs de 4 dígitos são importantes para a hierarquia (ex: 0703 = "Cebolas, chalotas, alhos...")
            # NCMs de 6 dígitos são importantes para a hierarquia (ex: 070320 = "Alhos")
            # NCMs de 8 dígitos são os subitens (ex: 07032010, 07032090)
            if save_classif_ncm(ncm_str, unidade or '', descricao):
                ncm_processados += 1
                if unidade:
                    ncm_com_unidade += 1
        
        # Atualizar data da última atualização
        set_classif_last_update(datetime.now())
        
        logger.info(f'[CLASSIF] Processamento concluído: {ncm_processados} NCMs processados e salvos, {ncm_com_unidade} com unidade estatística')
        
        # ✅ Verificar se realmente salvou no banco
        try:
            conn_verif = get_db_connection()
            cursor_verif = conn_verif.cursor()
            cursor_verif.execute('SELECT COUNT(*) FROM classif_cache')
            total_salvo = cursor_verif.fetchone()[0]
            conn_verif.close()
            logger.info(f'[CLASSIF] ✅ Verificação: Total de NCMs no banco após salvamento: {total_salvo}')
        except Exception as e:
            logger.warning(f'[CLASSIF] Não foi possível verificar total no banco: {e}')
        
        return jsonify({
            'message': 'Nomenclatura baixada e processada com sucesso',
            'total_itens': len(lista_ncms),
            'ncm_processados': ncm_processados,
            'ncm_com_unidade': ncm_com_unidade,
            'data_atualizacao': datetime.now().isoformat()
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'TIMEOUT',
            'message': 'Timeout ao baixar nomenclatura. O arquivo pode ser muito grande.'
        }), 408
    except requests.exceptions.RequestException as e:
        logger.error(f'Erro ao baixar nomenclatura: {str(e)}')
        return jsonify({
            'error': 'ERRO_NETWORK',
            'message': f'Erro de rede ao baixar nomenclatura: {str(e)}'
        }), 500
    except Exception as e:
        logger.error(f'Erro ao processar nomenclatura: {str(e)}', exc_info=True)
        return jsonify({
            'error': 'ERRO',
            'message': f'Erro ao processar nomenclatura: {str(e)}'
        }), 500


# ============================================================================
# Endpoints de Teste para TTS (Text-to-Speech)
# ============================================================================

@app.route('/api/teste/tts', methods=['POST'])
def teste_tts():
    """Endpoint de teste para gerar áudio TTS"""
    try:
        # ✅ FORÇAR recarregamento do .env com caminho absoluto
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    s = line.strip()
                    if s and not s.startswith('#') and '=' in s:
                        k, v = s.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
            logger.info(f"✅ .env recarregado forçadamente de {env_path}")
        
        # Debug: verificar variáveis após recarregar
        tts_enabled_env = os.getenv('OPENAI_TTS_ENABLED', 'false')
        logger.info(f"🔍 DEBUG endpoint: OPENAI_TTS_ENABLED='{tts_enabled_env}' (cwd: {os.getcwd()})")
        
        # Importar DEPOIS de carregar .env
        # Forçar recarregamento do módulo para pegar variáveis atualizadas
        import importlib
        if 'services.tts_service' in sys.modules:
            importlib.reload(sys.modules['services.tts_service'])
        
        from services.tts_service import TTSService
        
        data = request.get_json() or {}
        texto = data.get('texto', '')
        voz = data.get('voz', None)
        formatar_processo = data.get('formatar_processo', True)  # ✅ NOVO: Opção para formatar processos
        
        if not texto:
            return jsonify({
                'success': False,
                'error': 'Texto não fornecido'
            }), 400
        
        # ✅ NOVO: Formatar texto para TTS usando preparar_texto_tts (seguindo regras especificadas)
        texto_original = texto  # Guardar original para retornar
        if formatar_processo:
            try:
                from utils.tts_text_formatter import preparar_texto_tts
                texto_formatado = preparar_texto_tts(texto)
                logger.info(f"🔍 Texto original: {texto[:100]}...")
                logger.info(f"🔍 Texto formatado: {texto_formatado[:100]}...")
                texto = texto_formatado
            except Exception as e:
                logger.warning(f"⚠️ Erro ao formatar texto para TTS: {e}. Usando texto original.")
                texto_formatado = texto_original
        else:
            texto_formatado = texto_original
        
        tts = TTSService()
        
        logger.info(f"🔍 DEBUG endpoint: tts.enabled={tts.enabled}, tts.voice={tts.voice}, OPENAI_TTS_ENABLED={os.getenv('OPENAI_TTS_ENABLED', 'não definido')}")
        
        if not tts.enabled:
            # Debug adicional
            env_file_exists = os.path.exists('.env')
            env_value = os.getenv('OPENAI_TTS_ENABLED', 'não definido')
            cwd = os.getcwd()
            
            logger.error(f"❌ TTS desabilitado! env_file_exists={env_file_exists}, cwd={cwd}, OPENAI_TTS_ENABLED='{env_value}'")
            
            return jsonify({
                'success': False,
                'error': f'TTS desabilitado. OPENAI_TTS_ENABLED={env_value}. Configure OPENAI_TTS_ENABLED=true no .env (cwd: {cwd})'
            }), 400
        
        audio_url = tts.gerar_audio(texto, voz=voz)
        
        if audio_url:
            return jsonify({
                'success': True,
                'audio_url': audio_url,
                'texto': texto,  # Texto formatado enviado para TTS
                'texto_original': texto_original,  # Texto original antes da formatação
                'texto_formatado': texto_formatado if formatar_processo else texto_original,  # Texto formatado
                'voz': voz or tts.voice
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha ao gerar áudio'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Erro no teste TTS: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/teste/tts/multiplas', methods=['POST'])
def teste_tts_multiplas():
    """Endpoint de teste para gerar múltiplos áudios TTS"""
    try:
        # ✅ FORÇAR recarregamento do .env com caminho absoluto
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    s = line.strip()
                    if s and not s.startswith('#') and '=' in s:
                        k, v = s.split('=', 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")
        
        # Importar DEPOIS de carregar .env
        from services.tts_service import TTSService
        
        data = request.get_json() or {}
        frases = data.get('frases', [])
        voz = data.get('voz', None)
        
        if not frases or not isinstance(frases, list):
            return jsonify({
                'success': False,
                'error': 'Lista de frases não fornecida'
            }), 400
        
        tts = TTSService()
        
        if not tts.enabled:
            return jsonify({
                'success': False,
                'error': 'TTS desabilitado. Configure OPENAI_TTS_ENABLED=true no .env'
            }), 400
        
        resultados = []
        sucessos = 0
        falhas = 0
        
        for i, frase in enumerate(frases):
            audio_url = tts.gerar_audio(frase, voz=voz)
            
            if audio_url:
                resultados.append({
                    'indice': i,
                    'texto': frase,
                    'audio_url': audio_url,
                    'sucesso': True
                })
                sucessos += 1
            else:
                resultados.append({
                    'indice': i,
                    'texto': frase,
                    'audio_url': None,
                    'sucesso': False,
                    'erro': 'Falha ao gerar áudio'
                })
                falhas += 1
        
        return jsonify({
            'success': True,
            'total': len(frases),
            'sucessos': sucessos,
            'falhas': falhas,
            'resultados': resultados
        })
            
    except Exception as e:
        logger.error(f"❌ Erro no teste TTS múltiplas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/teste-tts', methods=['GET'])
def pagina_teste_tts():
    """Página HTML para testar TTS"""
    try:
        html_path = Path(__file__).parent / 'test_tts_html.html'
        if html_path.exists():
            with open(html_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return jsonify({
                'success': False,
                'error': 'Página de teste não encontrada'
            }), 404
    except Exception as e:
        logger.error(f"❌ Erro ao servir página de teste TTS: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/teste/reproduzir-notificacao/<int:notificacao_id>', methods=['POST'])
def forcar_reproducao_notificacao(notificacao_id):
    """Endpoint para forçar reprodução de uma notificação específica (para testes)"""
    try:
        from db_manager import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, processo_referencia, tipo_notificacao, titulo, mensagem, 
                   dados_extras, criado_em
            FROM notificacoes_processos
            WHERE id = ?
        ''', (notificacao_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'success': False,
                'error': 'Notificação não encontrada'
            }), 404
        
        notif = {
            'id': row[0],
            'processo_referencia': row[1],
            'tipo_notificacao': row[2],
            'titulo': row[3],
            'mensagem': row[4],
            'dados_extras': safe_json_loads(row[5], default={}),
            'criado_em': row[6].isoformat() if hasattr(row[6], 'isoformat') else str(row[6])
        }
        
        return jsonify({
            'success': True,
            'notificacao': notif,
            'audio_url': notif.get('dados_extras', {}).get('audio_url'),
            'message': 'Use esta notificação para testar no frontend'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar notificação: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/teste/notificacao-tts', methods=['GET', 'POST'])
@app.route('/teste-notificacao', methods=['GET'])  # ✅ Rota alternativa mais simples
def teste_notificacao_tts():
    """Endpoint para testar criação de notificação com TTS (GET ou POST)"""
    try:
        from services.notificacao_service import NotificacaoService
        from db_manager import get_db_connection
        
        # ✅ NOVO: Suportar GET também para facilitar teste
        if request.method == 'GET':
            data = {
                'processo_referencia': request.args.get('processo_referencia', 'TEST.0001/25'),
                'tipo_notificacao': request.args.get('tipo_notificacao', 'chegada'),
                'titulo': request.args.get('titulo', '🔔 Notificação de Teste'),
                'mensagem': request.args.get('mensagem', 'Esta é uma notificação de teste para verificar se o TTS está funcionando corretamente.')
            }
        else:
            data = request.get_json() or {}
        
        processo_referencia = data.get('processo_referencia', 'TEST.0001/25')
        tipo_notificacao = data.get('tipo_notificacao', 'chegada')
        titulo = data.get('titulo', '🔔 Notificação de Teste')
        mensagem = data.get('mensagem', f'{processo_referencia} chegou ao destino. Status CE: ARMAZENADA.')
        
        # Criar notificação de teste
        notificacao_service = NotificacaoService()
        
        notificacao = {
            'processo_referencia': processo_referencia,
            'tipo_notificacao': tipo_notificacao,
            'titulo': titulo,
            'mensagem': mensagem,
            'dados_extras': {}
        }
        
        # Salvar notificação (isso vai gerar o TTS automaticamente)
        sucesso = notificacao_service._salvar_notificacao(notificacao)
        
        if sucesso:
            # Buscar a notificação criada para retornar com audio_url
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, processo_referencia, tipo_notificacao, titulo, mensagem, 
                       dados_extras, criado_em
                FROM notificacoes_processos
                WHERE processo_referencia = ? AND tipo_notificacao = ?
                ORDER BY criado_em DESC
                LIMIT 1
            ''', (processo_referencia, tipo_notificacao))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                notif_result = {
                    'id': row[0],
                    'processo_referencia': row[1],
                    'tipo_notificacao': row[2],
                    'titulo': row[3],
                    'mensagem': row[4],
                    'dados_extras': safe_json_loads(row[5], default={}),
                    'criado_em': row[6].isoformat() if hasattr(row[6], 'isoformat') else str(row[6])
                }
                
                logger.info(f"✅ Notificação de teste criada: ID={notif_result['id']}, audio_url={notif_result.get('dados_extras', {}).get('audio_url')}")
                
                return jsonify({
                    'success': True,
                    'message': 'Notificação de teste criada com sucesso!',
                    'notificacao': notif_result,
                    'audio_url': notif_result.get('dados_extras', {}).get('audio_url'),
                    'texto_tts': notif_result.get('dados_extras', {}).get('texto_tts')
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Notificação criada, mas não foi possível recuperar os dados'
                })
        else:
            return jsonify({
                'success': False,
                'error': 'Falha ao criar notificação de teste'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Erro no teste de notificação TTS: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================
# Nota: A inicialização é feita no bloco if __name__ == '__main__' abaixo


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # ✅ CORREÇÃO: Forçar flush imediato do output
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    print("=" * 70)
    print("🚀 INICIANDO CHAT IA INDEPENDENTE")
    print("=" * 70)
    print(f"📡 Porta: {PORT}")
    print(f"🐛 Debug: {app.config['DEBUG']}")
    print("=" * 70)
    sys.stdout.flush()
    
    logger.info(f"🚀 Iniciando Chat IA Independente na porta {PORT}...")
    sys.stdout.flush()
    
    # Inicializar antes de iniciar servidor (idempotente)
    try:
        print("🔄 Iniciando serviços em background (Kanban + scheduler)...")
        sys.stdout.flush()
        _start_background_services(source="__main__")
        print("✅ Serviços em background iniciados")
        sys.stdout.flush()
    except Exception as e:
        logger.warning(f"⚠️ Aviso na inicialização: {e}", exc_info=True)
        print(f"⚠️ Aviso na inicialização: {e}")
        sys.stdout.flush()
    
    # Iniciar servidor Flask
    print()
    print("=" * 70)
    print("🌐 INICIANDO SERVIDOR FLASK")
    print("=" * 70)
    
    # Tentar detectar IP da rede local
    local_ip = None
    try:
        import socket
        # Conectar a um servidor externo para descobrir o IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        # Se falhar, tentar outras formas
        try:
            import subprocess
            if sys.platform == 'darwin':  # macOS
                result = subprocess.run(['ipconfig', 'getifaddr', 'en0'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    local_ip = result.stdout.strip()
        except Exception:
            pass
    
    print(f"📱 Acesse localmente: http://localhost:{PORT}/chat-ia")
    if local_ip:
        print(f"🌐 Acesse na rede: http://{local_ip}:{PORT}/chat-ia")
        print(f"   Compartilhe este IP com outros na mesma rede: {local_ip}")
    else:
        print(f"🌐 Para acessar na rede, descubra seu IP local e use: http://<SEU_IP>:{PORT}/chat-ia")
        print(f"   No macOS: ifconfig | grep 'inet ' | grep -v 127.0.0.1")
    print("=" * 70)
    print()
    sys.stdout.flush()
    
    try:
        app.run(
            host='0.0.0.0',
            port=PORT,
            debug=app.config['DEBUG']
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor interrompido pelo usuário")
        sys.stdout.flush()
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        raise





