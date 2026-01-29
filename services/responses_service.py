"""
Serviço para Responses API da OpenAI (nova API que substitui Assistants API).

Este serviço permite:
- Buscar legislação usando Responses API
- Usar Code Interpreter quando necessário
- Integrar com o sistema de legislação existente

⚠️ IMPORTANTE: Assistants API será desligado em 26/08/2026.
Este serviço usa a nova Responses API recomendada.
"""
import os
import logging
from typing import Dict, Any, Optional

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
    logger.warning("⚠️ Biblioteca 'openai' não instalada. Responses API não disponível.")

AI_API_KEY = os.getenv('DUIMP_AI_API_KEY', '')
AI_ENABLED = os.getenv('DUIMP_AI_ENABLED', 'false').lower() == 'true'


class ResponsesService:
    """Serviço para Responses API da OpenAI."""
    
    def __init__(self):
        """Inicializa o serviço de Responses."""
        self.enabled = AI_ENABLED and OPENAI_AVAILABLE and bool(AI_API_KEY)
        
        if not self.enabled:
            if not OPENAI_AVAILABLE:
                logger.warning("⚠️ ResponsesService: Biblioteca 'openai' não disponível")
            elif not AI_ENABLED:
                logger.warning("⚠️ ResponsesService: IA desabilitada (DUIMP_AI_ENABLED=false)")
            elif not AI_API_KEY:
                logger.warning("⚠️ ResponsesService: API key não configurada")
            self.client = None
            return
        
        try:
            self.client = OpenAI(api_key=AI_API_KEY)
            logger.info("✅ ResponsesService inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar ResponsesService: {e}")
            self.enabled = False
            self.client = None
    
    def buscar_legislacao(
        self,
        pergunta: str,
        usar_code_interpreter: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Busca legislação usando Responses API.
        
        Args:
            pergunta: Pergunta do usuário sobre legislação
            usar_code_interpreter: Se True, habilita Code Interpreter (para cálculos se necessário)
        
        Returns:
            Dict com resposta ou None se erro
        """
        if not self.enabled or not self.client:
            logger.error("❌ ResponsesService não está habilitado")
            return None
        
        try:
            # Preparar tools
            tools = []
            if usar_code_interpreter:
                tools.append({
                    "type": "code_interpreter",
                    "container": {
                        "type": "auto",
                        "memory_limit": "1g"
                    }
                })
            
            # Instruções para o assistente
            instructions = """Você é um assistente especializado em legislação brasileira de importação e exportação (COMEX).

Sua função é buscar e responder perguntas sobre legislação usando os arquivos de legislação disponíveis e seu conhecimento.

REGRAS IMPORTANTES:
1. Sempre cite as fontes quando usar informações de legislação
2. Seja preciso e objetivo nas respostas
3. Se não encontrar informação específica, informe claramente
4. Use exemplos práticos quando relevante
5. Organize a resposta de forma clara e estruturada

FORMATO DE RESPOSTA:
- Use markdown para formatação
- Destaque artigos, parágrafos e incisos
- Inclua referências às legislações mencionadas
- Se aplicável, explique o contexto e aplicação prática"""
            
            logger.info(f"📤 Buscando legislação via Responses API: {pergunta[:100]}...")
            
            # Chamar Responses API
            resp = self.client.responses.create(
                model="gpt-4o",  # Usar gpt-4o (gpt-4.1 pode não estar disponível ainda)
                tools=tools if tools else None,
                instructions=instructions,
                input=pergunta
            )
            
            # Extrair resposta
            resposta_texto = resp.output_text if hasattr(resp, 'output_text') else str(resp)
            
            logger.info(f"✅ Resposta recebida via Responses API ({len(resposta_texto)} caracteres)")
            
            return {
                'sucesso': True,
                'resposta': resposta_texto,
                'metodo': 'responses_api',
                'modelo': 'gpt-4o'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar legislação via Responses API: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'metodo': 'responses_api'
            }
    
    def buscar_legislacao_com_calculo(
        self,
        pergunta: str,
        dados_calculo: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca legislação e permite cálculos usando Code Interpreter.
        
        Args:
            pergunta: Pergunta do usuário sobre legislação
            dados_calculo: Dados opcionais para cálculos (ex: valores, alíquotas)
        
        Returns:
            Dict com resposta ou None se erro
        """
        if not self.enabled or not self.client:
            logger.error("❌ ResponsesService não está habilitado")
            return None
        
        try:
            # Preparar input com dados de cálculo se fornecidos
            input_text = pergunta
            if dados_calculo:
                input_text += f"\n\nDados para cálculo:\n{self._formatar_dados_calculo(dados_calculo)}"
            
            # Instruções incluindo regras de cálculo
            instructions = """Você é um assistente especializado em legislação brasileira de importação e exportação (COMEX).

Sua função é buscar legislação e, quando necessário, realizar cálculos fiscais usando o Code Interpreter.

REGRAS DE LEGISLAÇÃO:
1. Sempre cite as fontes quando usar informações de legislação
2. Seja preciso e objetivo nas respostas
3. Use exemplos práticos quando relevante

REGRAS DE CÁLCULO (quando usar Code Interpreter):
1. Sempre mostre os passos do cálculo
2. Valide os resultados
3. Explique as fórmulas usadas
4. Apresente valores em BRL e USD quando aplicável

Use o python tool (Code Interpreter) quando precisar fazer cálculos complexos."""
            
            logger.info(f"📤 Buscando legislação com cálculo via Responses API: {pergunta[:100]}...")
            
            # Chamar Responses API com Code Interpreter
            resp = self.client.responses.create(
                model="gpt-4o",
                tools=[{
                    "type": "code_interpreter",
                    "container": {
                        "type": "auto",
                        "memory_limit": "1g"
                    }
                }],
                instructions=instructions,
                input=input_text
            )
            
            # Extrair resposta
            resposta_texto = resp.output_text if hasattr(resp, 'output_text') else str(resp)
            
            logger.info(f"✅ Resposta recebida via Responses API com cálculo ({len(resposta_texto)} caracteres)")
            
            return {
                'sucesso': True,
                'resposta': resposta_texto,
                'metodo': 'responses_api_com_calculo',
                'modelo': 'gpt-4o'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar legislação com cálculo via Responses API: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'metodo': 'responses_api_com_calculo'
            }
    
    def _formatar_dados_calculo(self, dados: Dict[str, Any]) -> str:
        """Formata dados de cálculo para incluir no input."""
        linhas = []
        for chave, valor in dados.items():
            if isinstance(valor, (int, float)):
                linhas.append(f"- {chave}: {valor}")
            elif isinstance(valor, dict):
                linhas.append(f"- {chave}:")
                for sub_chave, sub_valor in valor.items():
                    linhas.append(f"  - {sub_chave}: {sub_valor}")
            else:
                linhas.append(f"- {chave}: {valor}")
        return "\n".join(linhas)


def get_responses_service() -> ResponsesService:
    """Retorna instância singleton do ResponsesService."""
    if not hasattr(get_responses_service, '_instance'):
        get_responses_service._instance = ResponsesService()
    return get_responses_service._instance





