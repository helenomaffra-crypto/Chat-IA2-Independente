"""
Serviço para Assistants API da OpenAI com File Search.

Este serviço permite:
- Criar assistentes com File Search habilitado
- Fazer upload de arquivos de legislação
- Buscar legislação automaticamente usando RAG
- Integrar com o sistema de legislação existente
"""
import os
import logging
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
try:
    from dotenv import load_dotenv
    try:
        load_dotenv()
    except (PermissionError, OSError):
        # Ignorar erros de permissão (pode ocorrer em ambientes restritos)
        pass
except ImportError:
    pass

# Verificar se OpenAI está disponível
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️ Biblioteca 'openai' não instalada. Assistants API não disponível.")

AI_API_KEY = os.getenv('DUIMP_AI_API_KEY', '')
AI_ENABLED = os.getenv('DUIMP_AI_ENABLED', 'false').lower() == 'true'


class AssistantsService:
    """Serviço para Assistants API da OpenAI com File Search."""
    
    def __init__(self):
        """Inicializa o serviço de Assistants."""
        self.enabled = AI_ENABLED and OPENAI_AVAILABLE and bool(AI_API_KEY)
        
        if not self.enabled:
            if not OPENAI_AVAILABLE:
                logger.warning("⚠️ AssistantsService: Biblioteca 'openai' não disponível")
            elif not AI_ENABLED:
                logger.warning("⚠️ AssistantsService: IA desabilitada (DUIMP_AI_ENABLED=false)")
            elif not AI_API_KEY:
                logger.warning("⚠️ AssistantsService: API key não configurada")
            self.client = None
            return
        
        try:
            self.client = OpenAI(api_key=AI_API_KEY)
            # ✅ Usar ASSISTANT_ID_LEGISLACAO (com fallback para OPENAI_ASSISTANT_ID para compatibilidade)
            self.assistant_id = os.getenv('ASSISTANT_ID_LEGISLACAO') or os.getenv('OPENAI_ASSISTANT_ID', None)
            self.vector_store_id = os.getenv('VECTOR_STORE_ID_LEGISLACAO', None)
            # ✅ Configurável via ENV (permite mover arquivos para fora do workspace)
            from services.path_config import get_legislacao_files_dir
            self.legislacao_files_dir = get_legislacao_files_dir()
            self.legislacao_files_dir.mkdir(exist_ok=True)
            logger.info("✅ AssistantsService inicializado com sucesso")
            if self.assistant_id:
                logger.info(f"   Assistente ID: {self.assistant_id}")
            if self.vector_store_id:
                logger.info(f"   Vector Store ID: {self.vector_store_id}")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar AssistantsService: {e}")
            self.enabled = False
            self.client = None
    
    def criar_assistente_legislacao(self, nome: str = "mAIke Legislação") -> Optional[str]:
        """
        Cria um assistente com File Search habilitado para buscar legislação.
        
        Args:
            nome: Nome do assistente
        
        Returns:
            ID do assistente criado ou None se erro
        """
        if not self.enabled or not self.client:
            logger.error("❌ AssistantsService não está habilitado")
            return None
        
        try:
            # ✅ CORREÇÃO: Criar assistente com file_search habilitado
            # Se vector_store_ids estiver vazio, o File Search ainda funcionará
            # mas precisará ser associado depois via update
            assistant = self.client.beta.assistants.create(
                name=nome,
                instructions="""Você é um assistente especializado em legislação brasileira de importação e exportação (COMEX).

Sua função é buscar e responder perguntas sobre legislação usando os arquivos de legislação disponíveis.

REGRAS IMPORTANTES:
1. SEMPRE use File Search para buscar informações nos arquivos de legislação antes de responder
2. Cite sempre o artigo, parágrafo, inciso ou alínea específico quando possível
3. Se não encontrar a informação nos arquivos, informe claramente
4. Use linguagem clara e técnica, adequada para profissionais de COMEX
5. Quando mencionar legislação, inclua: tipo (IN, Decreto, Lei, etc.), número e ano

EXEMPLOS DE RESPOSTAS:
- "De acordo com o Art. 5º da IN RFB nº 680/2006..."
- "Conforme o Decreto 6.759/2009, Art. 7º, § 2º..."
- "A legislação disponível não contém informações sobre este tópico específico."
""",
                model="gpt-4o",
                tools=[{"type": "file_search"}],
                tool_resources={
                    "file_search": {
                        "vector_store_ids": []  # Será atualizado depois quando vector store for criado
                    }
                }
            )
            
            logger.info(f"✅ Assistente criado: {assistant.id}")
            return assistant.id
        except Exception as e:
            logger.error(f"❌ Erro ao criar assistente: {e}", exc_info=True)
            return None
    
    def criar_vector_store(self, nome: str = "Legislação COMEX", file_ids: Optional[List[str]] = None) -> Optional[str]:
        """
        Cria um vector store para armazenar arquivos de legislação.
        
        Args:
            nome: Nome do vector store
            file_ids: Lista opcional de file_ids para adicionar ao criar
        
        Returns:
            ID do vector store criado ou None se erro
        """
        if not self.enabled or not self.client:
            logger.error("❌ AssistantsService não está habilitado")
            return None
        
        try:
            # ✅ CORREÇÃO v2.x: Tentar client.vector_stores (versão 2.x)
            try:
                if file_ids:
                    vector_store = self.client.vector_stores.create(
                        name=nome,
                        file_ids=file_ids
                    )
                else:
                    vector_store = self.client.vector_stores.create(
                        name=nome
                    )
                logger.info(f"✅ Vector store criado (v2.x): {vector_store.id}")
                return vector_store.id
            except AttributeError:
                # ✅ Fallback: Tentar client.beta.vector_stores (versão 1.x)
                if file_ids:
                    vector_store = self.client.beta.vector_stores.create(
                        name=nome,
                        file_ids=file_ids
                    )
                else:
                    vector_store = self.client.beta.vector_stores.create(
                        name=nome
                    )
                logger.info(f"✅ Vector store criado (v1.x): {vector_store.id}")
                return vector_store.id
        except AttributeError as e:
            logger.error(f"❌ Vector stores não disponível: {e}")
            logger.info("💡 Vector stores não está disponível nesta versão")
            return None
        except Exception as e:
            logger.error(f"❌ Erro ao criar vector store: {e}", exc_info=True)
            return None
    
    def fazer_upload_arquivo(self, caminho_arquivo: str) -> Optional[str]:
        """
        Faz upload de um arquivo para a OpenAI.
        
        Args:
            caminho_arquivo: Caminho do arquivo a fazer upload
        
        Returns:
            ID do arquivo ou None se erro
        """
        if not self.enabled or not self.client:
            logger.error("❌ AssistantsService não está habilitado")
            return None
        
        try:
            arquivo_path = Path(caminho_arquivo)
            if not arquivo_path.exists():
                logger.error(f"❌ Arquivo não encontrado: {caminho_arquivo}")
                return None
            
            with open(arquivo_path, 'rb') as f:
                arquivo = self.client.files.create(
                    file=f,
                    purpose="assistants"
                )
            
            logger.info(f"✅ Arquivo enviado: {arquivo.id} ({arquivo_path.name})")
            return arquivo.id
        except Exception as e:
            logger.error(f"❌ Erro ao fazer upload do arquivo: {e}", exc_info=True)
            return None
    
    def adicionar_arquivos_ao_vector_store(self, vector_store_id: str, arquivo_ids: List[str]) -> bool:
        """
        Adiciona arquivos a um vector store.
        
        Args:
            vector_store_id: ID do vector store
            arquivo_ids: Lista de IDs dos arquivos
        
        Returns:
            True se sucesso, False caso contrário
        """
        if not self.enabled or not self.client:
            logger.error("❌ AssistantsService não está habilitado")
            return False
        
        try:
            # ✅ CORREÇÃO v2.x: Tentar client.vector_stores.files.create primeiro
            try:
                for arquivo_id in arquivo_ids:
                    self.client.vector_stores.files.create(
                        vector_store_id=vector_store_id,
                        file_id=arquivo_id
                    )
                logger.info(f"✅ Arquivos adicionados ao vector store (v2.x): {len(arquivo_ids)} arquivo(s)")
                return True
            except AttributeError:
                # ✅ Fallback: Tentar client.beta.vector_stores.files.create (v1.x)
                for arquivo_id in arquivo_ids:
                    self.client.beta.vector_stores.files.create(
                        vector_store_id=vector_store_id,
                        file_id=arquivo_id
                    )
                logger.info(f"✅ Arquivos adicionados ao vector store (v1.x): {len(arquivo_ids)} arquivo(s)")
                return True
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar arquivos ao vector store: {e}", exc_info=True)
            return False
    
    def exportar_legislacao_para_arquivo(self, legislacao_id: int) -> Optional[str]:
        """
        Exporta uma legislação do banco para arquivo texto para usar no File Search.
        
        Args:
            legislacao_id: ID da legislação no banco
        
        Returns:
            Caminho do arquivo criado ou None se erro
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
            cursor = conn.cursor()
            
            # Buscar legislação
            cursor.execute('''
                SELECT tipo_ato, numero, ano, sigla_orgao, titulo_oficial, texto_integral
                FROM legislacao
                WHERE id = ?
            ''', (legislacao_id,))
            
            legislacao = cursor.fetchone()
            if not legislacao:
                logger.error(f"❌ Legislação {legislacao_id} não encontrada")
                conn.close()
                return None
            
            # Buscar trechos
            cursor.execute('''
                SELECT referencia, tipo_trecho, texto, texto_com_artigo, ordem, numero_artigo
                FROM legislacao_trecho
                WHERE legislacao_id = ?
                ORDER BY ordem
            ''', (legislacao_id,))
            
            trechos = cursor.fetchall()
            conn.close()
            
            # Criar arquivo texto
            tipo_ato = legislacao['tipo_ato']
            numero = legislacao['numero']
            ano = legislacao['ano']
            sigla_orgao = legislacao.get('sigla_orgao', '')

            # ✅ Evitar ambiguidade em siglas no cabeçalho (ex.: "PR" ≠ "Paraná")
            # Observação: guardamos "sigla_orgao" como código curto, mas no arquivo para RAG preferimos nome humano.
            sigla_orgao_raw = str(sigla_orgao or '').strip()
            sigla_orgao_upper = sigla_orgao_raw.upper()
            orgao_legivel = sigla_orgao_raw
            if sigla_orgao_upper == 'PR':
                # Presidência da República / Planalto (fontes federais)
                orgao_legivel = 'Presidência da República (Planalto)'
            
            nome_arquivo = f"{tipo_ato}_{numero}_{ano}"
            if sigla_orgao:
                nome_arquivo += f"_{sigla_orgao}"
            nome_arquivo = nome_arquivo.replace(' ', '_').replace('/', '_') + ".txt"
            
            caminho_arquivo = self.legislacao_files_dir / nome_arquivo
            
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                # Cabeçalho
                if orgao_legivel:
                    f.write(f"{tipo_ato} {orgao_legivel} nº {numero}/{ano}\n")
                else:
                    f.write(f"{tipo_ato} nº {numero}/{ano}\n")
                f.write("=" * 80 + "\n\n")
                
                if legislacao.get('titulo_oficial'):
                    f.write(f"Título: {legislacao['titulo_oficial']}\n\n")
                
                # Nota: texto_integral pode conter o texto completo, mas geralmente usamos trechos
                # Se houver texto_integral e não houver trechos, podemos usar ele
                
                f.write("=" * 80 + "\n\n")
                
                # Trechos
                artigo_atual = None
                for trecho in trechos:
                    numero_artigo = trecho.get('numero_artigo')
                    referencia = trecho.get('referencia', '')
                    texto = trecho.get('texto', '')
                    texto_com_artigo = trecho.get('texto_com_artigo', '')
                    
                    # Se mudou de artigo, adicionar separador
                    if numero_artigo and numero_artigo != artigo_atual:
                        if artigo_atual is not None:
                            f.write("\n" + "-" * 80 + "\n\n")
                        artigo_atual = numero_artigo
                    
                    # Usar texto_com_artigo se disponível (tem mais contexto)
                    texto_para_escrever = texto_com_artigo if texto_com_artigo else texto
                    
                    if referencia:
                        f.write(f"{referencia}\n")
                    f.write(f"{texto_para_escrever}\n\n")
            
            logger.info(f"✅ Legislação exportada: {caminho_arquivo}")
            return str(caminho_arquivo)
        except Exception as e:
            logger.error(f"❌ Erro ao exportar legislação: {e}", exc_info=True)
            return None

    def _obter_file_ids_assistente(self) -> List[str]:
        """
        Busca a lista atual de file_ids associados ao assistente (quando não há vector store).
        """
        if not self.enabled or not self.client or not self.assistant_id:
            return []
        try:
            assistant = self.client.beta.assistants.retrieve(assistant_id=self.assistant_id)
            tool_resources = getattr(assistant, "tool_resources", None) or {}
            file_search = tool_resources.get("file_search") or {}
            file_ids = file_search.get("file_ids") or []
            return list(file_ids) if isinstance(file_ids, list) else []
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível obter file_ids do assistente: {e}")
            return []

    def _associar_file_ids_ao_assistente(self, file_ids: List[str]) -> bool:
        """
        Associa (substitui) file_ids diretamente ao assistente (fallback sem vector store).
        """
        if not self.enabled or not self.client or not self.assistant_id:
            return False
        try:
            self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                tool_resources={
                    "file_search": {
                        "file_ids": file_ids
                    }
                }
            )
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao associar file_ids ao assistente: {e}", exc_info=True)
            return False

    def vetorizar_legislacao(self, legislacao_id: int) -> Dict[str, Any]:
        """
        Exporta uma legislação do SQLite para arquivo, faz upload e adiciona ao File Search.

        ✅ Requer AssistantsService habilitado (OpenAI + DUIMP_AI_ENABLED=true + API key).
        ✅ Fluxo incremental: adiciona somente o arquivo novo (não recria tudo).
        """
        if not self.enabled or not self.client:
            return {
                "sucesso": False,
                "erro": "ASSISTANTS_DESABILITADO",
                "mensagem": "Assistants/File Search não está habilitado. Verifique DUIMP_AI_ENABLED e DUIMP_AI_API_KEY.",
            }
        if not self.assistant_id:
            return {
                "sucesso": False,
                "erro": "ASSISTANT_ID_NAO_CONFIGURADO",
                "mensagem": "ASSISTANT_ID_LEGISLACAO não configurado. Execute o setup (scripts/configurar_assistants_legislacao.py).",
            }

        caminho = self.exportar_legislacao_para_arquivo(legislacao_id)
        if not caminho:
            return {
                "sucesso": False,
                "erro": "ERRO_EXPORTACAO",
                "mensagem": "Não foi possível exportar a legislação para arquivo.",
            }

        file_id = self.fazer_upload_arquivo(caminho)
        if not file_id:
            return {
                "sucesso": False,
                "erro": "ERRO_UPLOAD",
                "mensagem": "Falha ao fazer upload do arquivo para a OpenAI.",
            }

        # Preferir vector store quando existe (incremental sem mexer na lista inteira)
        if self.vector_store_id:
            ok = self.adicionar_arquivos_ao_vector_store(self.vector_store_id, [file_id])
            if not ok:
                return {
                    "sucesso": False,
                    "erro": "ERRO_VECTOR_STORE",
                    "mensagem": "Falha ao adicionar arquivo ao Vector Store.",
                    "file_id": file_id,
                    "arquivo": caminho,
                }
            # Garantir que o assistente aponta para o vector store configurado
            try:
                self.client.beta.assistants.update(
                    assistant_id=self.assistant_id,
                    tool_resources={
                        "file_search": {
                            "vector_store_ids": [self.vector_store_id]
                        }
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível reforçar vector_store_ids no assistente (não crítico): {e}")

            return {
                "sucesso": True,
                "mensagem": "✅ Legislação vetorizada e adicionada ao Vector Store.",
                "arquivo": caminho,
                "file_id": file_id,
                "vector_store_id": self.vector_store_id,
                "assistant_id": self.assistant_id,
            }

        # Fallback: associar file_ids direto no assistente (append)
        atuais = self._obter_file_ids_assistente()
        novos = list(dict.fromkeys(atuais + [file_id]))
        ok = self._associar_file_ids_ao_assistente(novos)
        if not ok:
            return {
                "sucesso": False,
                "erro": "ERRO_ASSOCIACAO_ASSISTENTE",
                "mensagem": "Falha ao associar arquivo ao assistente (sem vector store).",
                "file_id": file_id,
                "arquivo": caminho,
            }

        return {
            "sucesso": True,
            "mensagem": "✅ Legislação vetorizada e associada ao assistente (sem Vector Store).",
            "arquivo": caminho,
            "file_id": file_id,
            "assistant_id": self.assistant_id,
        }
    
    def exportar_todas_legislacoes(self) -> List[str]:
        """
        Exporta todas as legislações do banco para arquivos.
        
        Returns:
            Lista de caminhos dos arquivos criados
        """
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Buscar todas as legislações
            cursor.execute('SELECT id FROM legislacao')
            legislacoes = cursor.fetchall()
            conn.close()
            
            arquivos_criados = []
            for (legislacao_id,) in legislacoes:
                caminho = self.exportar_legislacao_para_arquivo(legislacao_id)
                if caminho:
                    arquivos_criados.append(caminho)
            
            logger.info(f"✅ {len(arquivos_criados)} legislação(ões) exportada(s)")
            return arquivos_criados
        except Exception as e:
            logger.error(f"❌ Erro ao exportar legislações: {e}", exc_info=True)
            return []
    
    def buscar_legislacao(self, pergunta: str, thread_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Busca legislação usando Assistants API com File Search.
        
        Args:
            pergunta: Pergunta do usuário sobre legislação
            thread_id: ID da thread (opcional, cria nova se não fornecido)
        
        Returns:
            Dict com resposta ou None se erro
        """
        if not self.enabled or not self.client:
            logger.error("❌ AssistantsService não está habilitado")
            return None
        
        if not self.assistant_id:
            logger.error("❌ Assistant ID não configurado. Configure ASSISTANT_ID_LEGISLACAO no .env")
            return None
        
        try:
            # Criar thread se não existir
            if not thread_id:
                thread = self.client.beta.threads.create()
                thread_id = thread.id
            
            # Adicionar mensagem à thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=pergunta
            )
            
            # Executar run
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            # Aguardar conclusão
            import time
            while run.status in ['queued', 'in_progress', 'cancelling']:
                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Buscar mensagens
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                
                # Pegar última mensagem do assistente
                for message in messages.data:
                    if message.role == 'assistant':
                        conteudo = ""
                        if message.content:
                            for content_block in message.content:
                                if content_block.type == 'text':
                                    conteudo += content_block.text.value
                        
                        return {
                            'sucesso': True,
                            'resposta': conteudo,
                            'thread_id': thread_id,
                            'run_id': run.id
                        }
                
                return {
                    'sucesso': False,
                    'erro': 'Nenhuma resposta encontrada'
                }
            else:
                return {
                    'sucesso': False,
                    'erro': f'Run falhou com status: {run.status}',
                    'status': run.status
                }
        except Exception as e:
            logger.error(f"❌ Erro ao buscar legislação: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e)
            }


def get_assistants_service() -> AssistantsService:
    """Retorna instância singleton do AssistantsService."""
    if not hasattr(get_assistants_service, '_instance'):
        get_assistants_service._instance = AssistantsService()
    return get_assistants_service._instance

