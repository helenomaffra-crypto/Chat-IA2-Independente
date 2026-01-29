# 🤖 SERVIÇO DE IA PARA DUIMP - PROTÓTIPO
# Este arquivo é COMPLETAMENTE ISOLADO e não afeta código existente
# Se falhar, a aplicação continua funcionando normalmente

import os
import json
import logging
from typing import Dict, Any, Optional, List
from functools import lru_cache
import time

# ✅ CARREGAR VARIÁVEIS DO .env (igual ao app.py)
def load_env_from_file(filepath: str = '.env') -> None:
    """Carrega variáveis de ambiente do arquivo .env"""
    from pathlib import Path
    
    # ✅ CORREÇÃO: Tentar vários caminhos possíveis (igual ao app.py)
    possible_paths = [
        Path(filepath),
        Path(__file__).parent / filepath,  # Relativo ao ai_service.py
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
                # ✅ Se encontrou e carregou, parar de procurar
                return
            except OSError:
                continue

# Carregar .env antes de definir constantes
load_env_from_file()

logger = logging.getLogger(__name__)

AI_ENABLED = os.getenv('DUIMP_AI_ENABLED', 'false').lower() == 'true'
AI_PROVIDER = os.getenv('DUIMP_AI_PROVIDER', 'openai').lower()
AI_API_KEY = os.getenv('DUIMP_AI_API_KEY', '')
# ✅ CORREÇÃO: Timeout aumentado para suportar GPT-4 (mais lento que GPT-3.5-turbo)
# GPT-4 pode levar 10-30+ segundos, especialmente com function calling
AI_TIMEOUT = float(os.getenv('DUIMP_AI_TIMEOUT', '60.0'))  # Timeout: 60 segundos (padrão)

# ✅ NOVO: Estratégia de modelos - separar operacional de analítico
# Modelo padrão (operacional - rápido e barato)
AI_MODEL_DEFAULT = os.getenv('OPENAI_MODEL_DEFAULT', os.getenv('DUIMP_AI_MODEL', 'gpt-4o'))
# Modelo analítico (BI, consultas complexas, regras aprendidas)
AI_MODEL_ANALITICO = os.getenv('OPENAI_MODEL_ANALITICO', 'gpt-4o')
# ✅ NOVO: Modelo para conhecimento geral (quando não há tool calls - respostas puramente do conhecimento do modelo)
# Usa GPT-5 para conhecimento mais atualizado e preciso
AI_MODEL_CONHECIMENTO_GERAL = os.getenv('OPENAI_MODEL_CONHECIMENTO_GERAL', 'gpt-5.1')


class AIService:
    """Serviço de IA para DUIMP - Protótipo isolado."""
    
    def __init__(self):
        self.enabled = AI_ENABLED and bool(AI_API_KEY)
        self.provider = AI_PROVIDER if self.enabled else None
        self.cache = {}  # Cache simples em memória
        
    def _cache_key(self, tipo: str, dados: Dict) -> str:
        """Gera chave de cache."""
        key_data = {k: v for k, v in dados.items() if k not in ['contexto', 'pergunta']}
        if 'contexto' in dados and dados['contexto'] is not None:
            try:
                contexto_norm = json.dumps(dados['contexto'], sort_keys=True, ensure_ascii=False)
            except TypeError:
                contexto_norm = str(dados['contexto'])
            key_data['contexto_hash'] = hash(contexto_norm)
        return f"{tipo}:{json.dumps(key_data, sort_keys=True)}"
    
    def _get_cached(self, cache_key: str) -> Optional[Dict]:
        """Busca no cache."""
        if cache_key in self.cache:
            cached_time, response = self.cache[cache_key]
            if time.time() - cached_time < 3600:  # Cache válido por 1 hora
                return response
        return None
    
    def _set_cache(self, cache_key: str, response: Dict):
        """Salva no cache."""
        self.cache[cache_key] = (time.time(), response)
    
    def _call_llm_api(self, prompt: str, system_prompt: str, tools: Optional[List[Dict]] = None, tool_choice: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None) -> Optional[Any]:
        """
        Chama API do LLM - Implementação genérica com suporte a function calling.
        
        Args:
            prompt: Prompt do usuário
            system_prompt: Prompt do sistema
            tools: Lista de ferramentas (funções) disponíveis para function calling
            tool_choice: Controle de escolha de ferramenta ("auto", "none", ou nome específico)
            model: Modelo a ser usado (opcional, usa padrão se não fornecido)
            temperature: Temperatura para geração (0.0-2.0, opcional, padrão 0.5)
        
        Returns:
            Se tools=None: retorna string com resposta
            Se tools fornecidos: retorna dict com resposta e tool_calls (se houver)
        """
        if not self.enabled:
            return None
        
        try:
            if self.provider == 'openai':
                try:
                    from openai import OpenAI
                    
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                    
                    # ✅ NOVO: Suporte a function calling
                    # ✅ CORREÇÃO CRÍTICA: Aumentar max_tokens para permitir respostas completas
                    # ✅ CORREÇÃO: Aumentar temperature para respostas mais naturais
                    # ✅ NOVO: Suporte a seleção dinâmica de modelo e temperatura
                    # Prioridade: parâmetro > variável específica > padrão
                    model_selecionado = model or AI_MODEL_DEFAULT
                    
                    # ✅ LOG: Mostrar qual modelo está sendo usado
                    logger.info(f"[AI_SERVICE] 🤖 Modelo selecionado: {model_selecionado} (parâmetro: {model}, .env: {os.getenv('DUIMP_AI_MODEL', 'não definido')})")
                    
                    # ✅ CORREÇÃO CRÍTICA: Ajustar timeout baseado no modelo
                    # GPT-4 é muito mais lento que GPT-3.5-turbo, especialmente com function calling
                    timeout_ajustado = AI_TIMEOUT
                    if 'gpt-4' in model_selecionado.lower() or 'gpt-4o' in model_selecionado.lower():
                        # GPT-4 pode levar 20-60+ segundos, especialmente com function calling
                        timeout_ajustado = max(AI_TIMEOUT, 60.0)  # Mínimo 60 segundos para GPT-4
                        logger.debug(f"[AI_SERVICE] ⏱️ Timeout ajustado para {timeout_ajustado}s (GPT-4 é mais lento)")
                    elif 'gpt-3.5' in model_selecionado.lower():
                        # GPT-3.5-turbo é rápido, 30 segundos é suficiente
                        timeout_ajustado = max(AI_TIMEOUT, 30.0)  # Mínimo 30 segundos para GPT-3.5
                    
                    client = OpenAI(api_key=AI_API_KEY, timeout=timeout_ajustado)
                    
                    # ✅ NOVO: Temperatura configurável (padrão 0.5 - sugerido para balance entre natural e consistente)
                    temperature_selecionada = temperature if temperature is not None else 0.5
                    
                    kwargs = {
                        "model": model_selecionado,
                        "messages": messages,
                        "temperature": temperature_selecionada  # ✅ Configurável (padrão 0.5)
                    }
                    
                    # ✅ CORREÇÃO CRÍTICA: Tentar usar max_completion_tokens primeiro (modelos novos)
                    # Se falhar, tentar max_tokens (modelos antigos)
                    # Alguns modelos novos (o1, o3, e possivelmente outros) não aceitam max_tokens
                    # ✅ MELHORIA: Aumentar max_tokens para 4000 para respostas mais completas (gpt-5.1 suporta)
                    max_tokens_value = 4000  # Aumentado de 800 para 4000 para respostas mais completas
                    try:
                        # Tentar primeiro com max_completion_tokens (mais compatível com modelos novos)
                        kwargs["max_completion_tokens"] = max_tokens_value
                    except:
                        # Fallback para max_tokens (modelos antigos)
                        kwargs["max_tokens"] = max_tokens_value
                    
                    if tools:
                        # ✅ GUARDRAIL (28/01/2026): OpenAI limita o array `tools` a no máximo 128 itens.
                        # Mesmo que a lista venha de outra fonte, garantimos que não estouramos o limite.
                        try:
                            max_tools_openai = 128
                            if isinstance(tools, list) and len(tools) > max_tools_openai:
                                dropped = tools[max_tools_openai:]
                                dropped_names = [
                                    (t.get("function") or {}).get("name", "<sem_nome>")
                                    for t in (dropped or [])
                                    if isinstance(t, dict)
                                ]
                                logger.warning(
                                    f"⚠️ [AI_SERVICE] Muitas tools para o limite da OpenAI: {len(tools)} > {max_tools_openai}. "
                                    f"Truncando e descartando {len(dropped)} tool(s) (amostra: {', '.join(dropped_names[:10])})"
                                )
                                tools = tools[:max_tools_openai]
                        except Exception as _e:
                            logger.debug(f"[AI_SERVICE] Não foi possível validar/truncar tools: {_e}")

                        kwargs["tools"] = tools
                        if tool_choice:
                            kwargs["tool_choice"] = tool_choice
                        else:
                            kwargs["tool_choice"] = "auto"
                    
                    logger.debug(f"[AI_SERVICE] 🔄 Chamando OpenAI com modelo {model_selecionado}, timeout={timeout_ajustado}s")
                    
                    # ✅ CORREÇÃO CRÍTICA: Tentar com max_completion_tokens primeiro, se falhar, tentar max_tokens
                    try:
                        response = client.chat.completions.create(**kwargs)
                    except Exception as e:
                        error_str = str(e)
                        # Se o erro for sobre max_completion_tokens não suportado, tentar com max_tokens
                        if 'max_completion_tokens' in error_str.lower() or 'unsupported parameter' in error_str.lower():
                            logger.warning(f"[AI_SERVICE] ⚠️ Erro com max_completion_tokens, tentando max_tokens: {e}")
                            # Remover max_completion_tokens e tentar com max_tokens
                            kwargs_fallback = {k: v for k, v in kwargs.items() if k != 'max_completion_tokens'}
                            kwargs_fallback["max_tokens"] = max_tokens_value
                            response = client.chat.completions.create(**kwargs_fallback)
                        # Se o erro for sobre max_tokens não suportado, tentar com max_completion_tokens
                        elif 'max_tokens' in error_str.lower() and 'max_completion_tokens' in error_str.lower():
                            logger.warning(f"[AI_SERVICE] ⚠️ Erro com max_tokens, tentando max_completion_tokens: {e}")
                            # Remover max_tokens e tentar com max_completion_tokens
                            kwargs_fallback = {k: v for k, v in kwargs.items() if k != 'max_tokens'}
                            kwargs_fallback["max_completion_tokens"] = max_tokens_value
                            response = client.chat.completions.create(**kwargs_fallback)
                        else:
                            # Re-raise se for outro tipo de erro
                            raise
                    
                    message = response.choices[0].message
                    
                    # ✅ MELHORIA: Logs detalhados para diagnóstico
                    logger.debug(f"[AI_SERVICE] 📥 Resposta recebida: has_content={message.content is not None}, has_tool_calls={hasattr(message, 'tool_calls') and message.tool_calls is not None}")
                    
                    # ✅ NOVO: Se há tool_calls, retornar estrutura completa
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        logger.debug(f"[AI_SERVICE] 🔧 Tool calls detectadas: {len(message.tool_calls)} chamada(s)")
                        return {
                            'content': message.content,
                            'tool_calls': [
                                {
                                    'id': tc.id,
                                    'function': {
                                        'name': tc.function.name,
                                        'arguments': tc.function.arguments
                                    }
                                }
                                for tc in message.tool_calls
                            ]
                        }
                    
                    # Resposta normal (sem tool calls)
                    if message.content:
                        logger.debug(f"[AI_SERVICE] ✅ Content retornado: {len(message.content)} caracteres")
                        return message.content.strip()
                    else:
                        logger.warning(f"[AI_SERVICE] ⚠️ message.content é None/vazio mesmo sem tool_calls. Response: {response}")
                        return None
                    
                except ImportError:
                    logger.warning("[AI_SERVICE] Biblioteca openai não instalada. Execute: pip install openai")
                    return None
            
            elif self.provider == 'anthropic':
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=AI_API_KEY)
                    
                    # ✅ NOVO: Suporte a tools para Anthropic
                    # ✅ CORREÇÃO CRÍTICA: Aumentar max_tokens para permitir respostas completas
                    # ✅ NOVO: Suporte a seleção dinâmica de modelo e temperatura (só se for Anthropic)
                    model_selecionado = model or os.getenv('DUIMP_AI_MODEL', 'claude-3-haiku-20240307')
                    # ✅ NOVO: Temperatura configurável (padrão 0.5)
                    temperature_selecionada = temperature if temperature is not None else 0.5
                    kwargs = {
                        "model": model_selecionado,
                        "max_tokens": 800,  # ✅ Reduzido para evitar exceder limite de tokens do modelo
                        "temperature": temperature_selecionada,  # ✅ Configurável (padrão 0.5)
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": prompt}],
                        "timeout": AI_TIMEOUT
                    }
                    
                    if tools:
                        # Anthropic usa formato diferente para tools
                        kwargs["tools"] = tools
                    
                    response = client.messages.create(**kwargs)
                    
                    # ✅ NOVO: Verificar se há tool use
                    if hasattr(response, 'content') and response.content:
                        for content_block in response.content:
                            if hasattr(content_block, 'type') and content_block.type == 'tool_use':
                                return {
                                    'content': None,
                                    'tool_calls': [{
                                        'id': content_block.id,
                                        'function': {
                                            'name': content_block.name,
                                            'arguments': content_block.input
                                        }
                                    }]
                                }
                    
                    return response.content[0].text.strip() if response.content else None
                except ImportError:
                    logger.warning("[AI_SERVICE] Biblioteca anthropic não instalada")
                    return None
            
            elif self.provider == 'local':
                # Para modelos locais (Ollama, etc)
                # Implementar conforme necessário
                return None
                
        except Exception as e:
            error_msg = str(e)
            # ✅ CORREÇÃO: Tratamento específico para timeout (GPT-4 é mais lento)
            if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower() or hasattr(e, '__class__') and 'Timeout' in str(e.__class__):
                logger.error(f"[AI_SERVICE] ⚠️ TIMEOUT ao chamar LLM (modelo pode ser muito lento): {error_msg}")
                logger.error(f"[AI_SERVICE] 💡 SUGESTÃO: Tente usar GPT-3.5-turbo (mais rápido) ou aumente DUIMP_AI_TIMEOUT no .env")
            else:
                logger.warning(f"[AI_SERVICE] Erro ao chamar LLM: {error_msg}")
            return None
        
        return None
    
    def _call_llm_api_stream(self, prompt: str, system_prompt: str, tools: Optional[List[Dict]] = None, tool_choice: Optional[str] = None, model: Optional[str] = None, temperature: Optional[float] = None):
        """
        Chama API do LLM com streaming - retorna generator de chunks.
        
        Args:
            prompt: Prompt do usuário
            system_prompt: Prompt do sistema
            tools: Lista de ferramentas (funções) disponíveis para function calling
            tool_choice: Controle de escolha de ferramenta ("auto", "none", ou nome específico)
            model: Modelo a ser usado (opcional, usa padrão se não fornecido)
            temperature: Temperatura para geração (0.0-2.0, opcional, padrão 0.5)
        
        Yields:
            Dict com chunks da resposta contendo:
            - chunk: str (pedaço do texto)
            - done: bool (se terminou)
            - tool_calls: list (se houver tool calls)
        """
        if not self.enabled:
            yield {'chunk': '', 'done': True, 'tool_calls': None}
            return
        
        try:
            if self.provider == 'openai':
                try:
                    from openai import OpenAI
                    
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                    
                    model_selecionado = model or AI_MODEL_DEFAULT
                    temperature_selecionada = temperature if temperature is not None else 0.5
                    
                    timeout_ajustado = AI_TIMEOUT
                    if 'gpt-4' in model_selecionado.lower() or 'gpt-4o' in model_selecionado.lower():
                        timeout_ajustado = max(AI_TIMEOUT, 60.0)
                    elif 'gpt-3.5' in model_selecionado.lower():
                        timeout_ajustado = max(AI_TIMEOUT, 30.0)
                    
                    client = OpenAI(api_key=AI_API_KEY, timeout=timeout_ajustado)
                    
                    kwargs = {
                        "model": model_selecionado,
                        "messages": messages,
                        "temperature": temperature_selecionada,
                        "stream": True  # ✅ CRÍTICO: Ativar streaming
                    }
                    
                    max_tokens_value = 4000
                    try:
                        kwargs["max_completion_tokens"] = max_tokens_value
                    except:
                        kwargs["max_tokens"] = max_tokens_value
                    
                    if tools:
                        kwargs["tools"] = tools
                        if tool_choice:
                            kwargs["tool_choice"] = tool_choice
                        else:
                            kwargs["tool_choice"] = "auto"
                    
                    logger.debug(f"[AI_SERVICE] 🔄 Chamando OpenAI com STREAMING, modelo {model_selecionado}")
                    
                    # ✅ STREAMING: Iterar sobre chunks da resposta
                    tool_calls_accumulated = []
                    full_content = ""
                    
                    try:
                        stream = client.chat.completions.create(**kwargs)
                    except Exception as e:
                        error_str = str(e)
                        if 'max_completion_tokens' in error_str.lower() or 'unsupported parameter' in error_str.lower():
                            logger.warning(f"[AI_SERVICE] ⚠️ Erro com max_completion_tokens, tentando max_tokens: {e}")
                            kwargs_fallback = {k: v for k, v in kwargs.items() if k != 'max_completion_tokens'}
                            kwargs_fallback["max_tokens"] = max_tokens_value
                            stream = client.chat.completions.create(**kwargs_fallback)
                        elif 'max_tokens' in error_str.lower() and 'max_completion_tokens' in error_str.lower():
                            logger.warning(f"[AI_SERVICE] ⚠️ Erro com max_tokens, tentando max_completion_tokens: {e}")
                            kwargs_fallback = {k: v for k, v in kwargs.items() if k != 'max_tokens'}
                            kwargs_fallback["max_completion_tokens"] = max_tokens_value
                            stream = client.chat.completions.create(**kwargs_fallback)
                        else:
                            raise
                    
                    for chunk in stream:
                        if chunk.choices and len(chunk.choices) > 0:
                            delta = chunk.choices[0].delta
                            
                            # Texto do chunk
                            if hasattr(delta, 'content') and delta.content:
                                chunk_text = delta.content
                                full_content += chunk_text
                                # ✅ Log para debug: verificar se chunks estão sendo recebidos da API
                                logger.debug(f"📦 [AI_STREAM] Chunk recebido da API ({len(chunk_text)} chars): '{chunk_text[:50]}...'")
                                yield {
                                    'chunk': chunk_text,
                                    'done': False,
                                    'tool_calls': None
                                }
                            
                            # Tool calls (acumular até terminar)
                            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                                for tool_call_delta in delta.tool_calls:
                                    idx = tool_call_delta.index
                                    while len(tool_calls_accumulated) <= idx:
                                        tool_calls_accumulated.append({
                                            'id': '',
                                            'function': {'name': '', 'arguments': ''}
                                        })
                                    
                                    if tool_call_delta.id:
                                        tool_calls_accumulated[idx]['id'] = tool_call_delta.id
                                    if hasattr(tool_call_delta, 'function'):
                                        if tool_call_delta.function.name:
                                            tool_calls_accumulated[idx]['function']['name'] = tool_call_delta.function.name
                                        if tool_call_delta.function.arguments:
                                            tool_calls_accumulated[idx]['function']['arguments'] += tool_call_delta.function.arguments
                    
                    # ✅ Se terminou e tem tool calls, retornar
                    if tool_calls_accumulated and any(tc.get('function', {}).get('name') for tc in tool_calls_accumulated):
                        yield {
                            'chunk': '',
                            'done': True,
                            'tool_calls': tool_calls_accumulated
                        }
                    else:
                        # Resposta normal terminou
                        yield {
                            'chunk': '',
                            'done': True,
                            'tool_calls': None
                        }
                    
                except ImportError:
                    logger.warning("[AI_SERVICE] Biblioteca openai não instalada. Execute: pip install openai")
                    yield {'chunk': '', 'done': True, 'tool_calls': None}
                except Exception as e:
                    error_msg = str(e)
                    if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                        logger.error(f"[AI_SERVICE] ⚠️ TIMEOUT ao chamar LLM com streaming: {error_msg}")
                    else:
                        logger.warning(f"[AI_SERVICE] Erro ao chamar LLM com streaming: {error_msg}")
                    yield {'chunk': '', 'done': True, 'tool_calls': None, 'error': error_msg}
            
            elif self.provider == 'anthropic':
                # Anthropic também suporta streaming, mas implementação diferente
                # Por enquanto, retornar erro ou implementar depois
                logger.warning("[AI_SERVICE] Streaming não implementado para Anthropic ainda")
                yield {'chunk': '', 'done': True, 'tool_calls': None, 'error': 'Streaming não suportado para Anthropic'}
            else:
                yield {'chunk': '', 'done': True, 'tool_calls': None}
                
        except Exception as e:
            logger.error(f"[AI_SERVICE] Erro geral em streaming: {e}", exc_info=True)
            yield {'chunk': '', 'done': True, 'tool_calls': None, 'error': str(e)}
    
    def interpretar_erro_api(
        self,
        codigo_erro: str,
        mensagem: str,
        campo: Optional[str] = None,
        contexto: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Interpreta erro da API do Portal Único em linguagem natural.
        """
        contexto = contexto or {}
        cache_key = self._cache_key('erro', {'codigo': codigo_erro, 'campo': campo, 'contexto': contexto})
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Base de conhecimento de erros comuns (fallback se LLM não disponível)
        erros_conhecidos = {
            'DIMP-ER8001': {
                'titulo': 'Campo Obrigatório Faltando',
                'explicacao': 'Um campo obrigatório não foi preenchido ou está vazio.',
                'acao': 'Verifique se todos os campos obrigatórios foram preenchidos corretamente.',
                'campos_comuns': ['identificacao.numeroItem', 'identificacao.importador.ni', 'carga.numeroCE']
            },
            'DIMP-ER8504': {
                'titulo': 'Situação da DUIMP Não Permite Operação',
                'explicacao': 'A DUIMP está em um estado que não permite esta operação.',
                'acao': 'Verifique o status atual da DUIMP. Algumas operações só são permitidas em EM_ELABORACAO.',
                'campos_comuns': []
            },
            'DIMP-ER8300': {
                'titulo': 'Total de Itens Divergente',
                'explicacao': 'O total de itens informado não corresponde ao total de itens registrados na DUIMP.',
                'acao': 'Recalcule o total de itens e sincronize com os itens já registrados na DUIMP.',
                'campos_comuns': ['totalItem']
            }
        }

        if codigo_erro in erros_conhecidos:
            resultado = erros_conhecidos[codigo_erro].copy()
            resultado['codigo'] = codigo_erro
            resultado['mensagem_original'] = mensagem
            resultado['campo'] = campo
            resultado['fonte'] = 'base_conhecimento'
            if contexto:
                notas: List[str] = []
                total_informado = contexto.get('totalItensInformado')
                quantidade_lista = contexto.get('quantidadeItensLista')
                numero_item = contexto.get('numeroItemRetornado')
                if codigo_erro == 'DIMP-ER8300' and total_informado is not None and quantidade_lista is not None:
                    notas.append(f"Total informado: {total_informado}. Itens detectados na lista atual: {quantidade_lista}.")
                if numero_item and codigo_erro.startswith('DIMP-ER82'):
                    notas.append(f"Ocorrência relacionada ao item número {numero_item}.")
                if notas:
                    explicacao_original = resultado.get('explicacao', '')
                    resultado['explicacao'] = f"{explicacao_original} {' '.join(notas)}".strip()
                resultado['contexto'] = contexto
            self._set_cache(cache_key, resultado)
            return resultado

        if self.enabled:
            system_prompt = """Você é um especialista em DUIMP (Declaração Única de Importação).
Sua função é interpretar erros da API do Portal Único Siscomex em linguagem natural e sugerir soluções.
Responda em JSON com: titulo, explicacao, acao, sugestoes (array).
Seja conciso e prático."""

            contexto_prompt = ''
            if contexto:
                try:
                    contexto_prompt = "\n\nContexto adicional (informado pela aplicação):\n" + json.dumps(contexto, ensure_ascii=False, indent=2)
                except TypeError:
                    contexto_prompt = f"\n\nContexto adicional (informado pela aplicação): {contexto}"

            prompt = f"""Erro da API DUIMP:
Código: {codigo_erro}
Mensagem: {mensagem}
Campo: {campo or 'N/A'}{contexto_prompt}

Interprete este erro em linguagem natural e sugira como corrigir.
Responda APENAS em JSON válido."""

            try:
                resposta_llm = self._call_llm_api(prompt, system_prompt)
                if resposta_llm:
                    try:
                        resultado = json.loads(resposta_llm)
                        resultado['codigo'] = codigo_erro
                        resultado['mensagem_original'] = mensagem
                        resultado['campo'] = campo
                        resultado['fonte'] = 'llm'
                        if contexto:
                            resultado['contexto'] = contexto
                        self._set_cache(cache_key, resultado)
                        return resultado
                    except json.JSONDecodeError:
                        resultado = {
                            'codigo': codigo_erro,
                            'titulo': 'Erro Interpretado',
                            'explicacao': resposta_llm,
                            'acao': 'Verifique o campo mencionado e corrija conforme necessário.',
                            'mensagem_original': mensagem,
                            'campo': campo,
                            'fonte': 'llm_texto'
                        }
                        if contexto:
                            resultado['contexto'] = contexto
                        self._set_cache(cache_key, resultado)
                        return resultado
            except Exception as e:
                logger.warning(f"[AI_SERVICE] Erro ao interpretar com LLM: {str(e)}")

        resultado = {
            'codigo': codigo_erro,
            'titulo': 'Erro da API',
            'explicacao': mensagem,
            'acao': 'Consulte a documentação oficial para mais detalhes.',
            'mensagem_original': mensagem,
            'campo': campo,
            'fonte': 'fallback'
        }
        if contexto:
            resultado['contexto'] = contexto
        self._set_cache(cache_key, resultado)
        return resultado
    
    def sugerir_ncm_por_descricao(self, descricao: str, contexto: Optional[Dict] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Sugere NCM baseado em descrição do produto usando IA.
        
        ⚠️ IMPORTANTE: Esta função usa o conhecimento geral do LLM.
        Para melhor precisão, considere usar RAG com a nomenclatura oficial do cache local.
        
        Args:
            descricao: Descrição do produto (ex: "alho fresco")
            contexto: Contexto adicional (ex: país de origem, tipo de produto)
        
        Returns:
            Dict com NCM sugerido, explicação e nível de confiança
        """
        if not self.enabled:
            return {
                'ncm': None,
                'explicacao': 'Serviço de IA não habilitado. Configure DUIMP_AI_ENABLED=true e DUIMP_AI_API_KEY no .env',
                'confianca': 0,
                'sugestoes_alternativas': []
            }
        
        cache_key = self._cache_key('sugerir_ncm', {'descricao': descricao.lower()})
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        contexto_str = ''
        if contexto:
            contexto_str = f"\nContexto adicional: {json.dumps(contexto, ensure_ascii=False)}"
        
        # ⚠️ LIMITAÇÃO ATUAL: A IA está usando apenas conhecimento geral do modelo LLM
        # Não está consultando a nomenclatura oficial do cache local
        # Para melhor precisão, implementar RAG (Retrieval Augmented Generation) usando:
        # 1. Cache local de NCMs (db_manager.buscar_ncms_por_descricao)
        # 2. Documentação oficial (docs oficial duimp/)
        # 3. Validação contra nomenclatura oficial
        
        # ✅ MELHORIA: Prompt melhorado com suporte a RAG
        tem_ncms_cache = contexto and 'ncms_similares_no_cache' in contexto and len(contexto['ncms_similares_no_cache']) > 0
        
        if tem_ncms_cache:
            # ✅ RAG: Usar NCMs do cache como contexto principal
            ncms_lista = contexto['ncms_similares_no_cache']
            
            # ✅ NOVO: Separar NCMs priorizados por feedback dos demais
            ncms_priorizados = [n for n in ncms_lista if n.get('prioridade_feedback', False)]
            ncms_normais = [n for n in ncms_lista if not n.get('prioridade_feedback', False)]
            
            # Construir texto com NCMs priorizados primeiro
            ncms_texto = ''
            if ncms_priorizados:
                ncms_texto += '✅ FEEDBACK CORRETO - NCMs marcados como CORRETOS por usuários anteriores (PRIORIZE ESTES):\n'
                ncms_texto += '\n'.join([
                    f"  ⭐ NCM {n['ncm']}: {n['descricao']}" + (f" (Unidade: {n.get('unidade', 'N/A')})" if n.get('unidade') else "")
                    for n in ncms_priorizados
                ])
                ncms_texto += '\n\n'
            
            if ncms_normais:
                ncms_texto += 'Outros NCMs similares encontrados no cache:\n'
                ncms_texto += '\n'.join([
                    f"- NCM {n['ncm']}: {n['descricao']}" + (f" (Unidade: {n.get('unidade', 'N/A')})" if n.get('unidade') else "")
                    for n in ncms_normais
                ])
            
            system_prompt = """Você é um especialista em classificação fiscal de produtos para importação no Brasil.
Sua tarefa é sugerir o código NCM (Nomenclatura Comum do Mercosul) mais adequado para uma descrição de produto.

✅ CRÍTICO: Você receberá uma lista de NCMs REAIS encontrados no cache local da nomenclatura oficial.
REGRA ABSOLUTA: Você DEVE sugerir APENAS NCMs que estão na lista fornecida abaixo.
NÃO invente NCMs que não estão na lista. Se não encontrar um NCM exato na lista, escolha o MAIS PRÓXIMO da lista.

⚠️ REGRA DE PRIORIDADE CRÍTICA:
- Se houver NCMs marcados com "✅ FEEDBACK CORRETO" na lista, você DEVE PRIORIZAR ESSES NCMs!
- Esses NCMs foram marcados como CORRETOS por usuários anteriores para descrições similares.
- Se algum NCM com feedback correto for relevante para a descrição atual, SUGIRA ESSE NCM!
- Use confianca >= 0.9 para NCMs com feedback correto que sejam relevantes.

💡 IMPORTANTE: Use seu conhecimento sobre classificação fiscal para validar se os NCMs da lista fazem sentido para o produto descrito.
Se a lista contém apenas NCMs claramente incorretos (ex: Cap 19 para medicamento), rejeite explicitamente e informe o problema.

Regras importantes:
- NCM sempre tem 8 dígitos
- Responda APENAS com um JSON válido no formato: {"ncm": "12345678", "explicacao": "explicação breve", "confianca": 0.8, "sugestoes_alternativas": ["12345679", "12345680"]}
- confianca deve ser um número entre 0.0 e 1.0
- Se encontrar um NCM com feedback correto relevante, use confianca >= 0.9
- Se encontrar um NCM exato na lista fornecida (sem feedback), use confianca >= 0.8
- Se não encontrar exatamente mas houver similar na lista, use confianca entre 0.6 e 0.8
- Se não houver nenhum similar na lista ou se os NCMs da lista são claramente incorretos, use confianca < 0.6 e explique o problema
- Explique brevemente por que esse NCM foi escolhido, mencionando se foi baseado em feedback anterior ou na lista fornecida
- Se houver NCMs alternativos na lista fornecida, liste até 3 no array sugestoes_alternativas
- NUNCA sugira NCMs que não estão na lista fornecida"""
            
            # ✅ NOVO: Adicionar contexto sobre feedbacks históricos se existirem
            contexto_feedback = ''
            if contexto.get('feedbacks_historicos'):
                feedbacks = contexto['feedbacks_historicos']
                contexto_feedback = f'\n\n📚 CONTEXTO DE FEEDBACKS HISTÓRICOS:\n'
                contexto_feedback += f'Para descrições similares, usuários marcaram os seguintes NCMs como CORRETOS:\n'
                for fb in feedbacks[:3]:
                    contexto_feedback += f"- Descrição: \"{fb.get('descricao_produto', '')}\" → NCM CORRETO: {fb.get('ncm_correto', '')} (NCM errado sugerido: {fb.get('ncm_sugerido', '')})\n"
                contexto_feedback += '\n⚠️ IMPORTANTE: Se a descrição atual for similar a alguma acima, PRIORIZE o NCM correto correspondente!\n'
            
            user_prompt = f"""Descrição do produto: "{descricao}"{contexto_str}

NCMs similares encontrados no cache local da nomenclatura oficial (USE APENAS ESTES):
{ncms_texto}{contexto_feedback}

REGRA CRÍTICA: Você DEVE sugerir APENAS um NCM que está na lista acima.
⚠️ PRIORIDADE: Se houver NCMs marcados com "✅ FEEDBACK CORRETO" que sejam relevantes para a descrição, SUGIRA ESSE NCM!
Se encontrar um NCM similar na lista, sugira esse NCM exato.
Se não encontrar exatamente, escolha o NCM mais próximo da lista fornecida.
NÃO invente NCMs que não estão na lista.

💡 IMPORTANTE: Use seu conhecimento sobre classificação fiscal para validar se os NCMs da lista fazem sentido.
Se a lista contém apenas NCMs claramente incorretos para o produto descrito, rejeite explicitamente na explicação e informe o problema.

Responda APENAS com o JSON, sem texto adicional."""
        else:
            # Fallback: conhecimento geral (sem RAG)
            # ✅ SIMPLIFICADO: Confia no conhecimento do modelo (GPT-5) em vez de regras explícitas
            system_prompt = """Você é um especialista em classificação fiscal de produtos para importação no Brasil.
Sua tarefa é sugerir o código NCM (Nomenclatura Comum do Mercosul) mais adequado para uma descrição de produto.

Use seu conhecimento sobre a estrutura da NCM e as regras de classificação fiscal para sugerir o NCM mais apropriado.

⚠️ IMPORTANTE: Você está usando conhecimento geral. Para precisão máxima, sempre valide contra a nomenclatura oficial.

Regras importantes:
- NCM sempre tem 8 dígitos
- Responda APENAS com um JSON válido no formato: {"ncm": "12345678", "explicacao": "explicação breve", "confianca": 0.8, "sugestoes_alternativas": ["12345679", "12345680"]}
- confianca deve ser um número entre 0.0 e 1.0
- Se não tiver certeza, coloque confianca abaixo de 0.7
- Explique brevemente por que esse NCM foi escolhido, mencionando o capítulo/posição e critérios de classificação
- Se houver NCMs alternativos, liste até 3 no array sugestoes_alternativas
- Sempre mencione na explicação que o usuário deve validar contra a nomenclatura oficial"""
            
            user_prompt = f"""Descrição do produto: "{descricao}"{contexto_str}

Sugira o NCM mais adequado baseado no conhecimento geral da Nomenclatura Comum do Mercosul.
Use seu conhecimento sobre classificação fiscal para identificar o capítulo e posição corretos.

⚠️ NOTA: Esta é uma sugestão baseada em conhecimento geral. Sempre valide contra a nomenclatura oficial.

Responda APENAS com o JSON, sem texto adicional."""
        
        # ✅ NOVO: Usar modelo especificado (ex: GPT-5) ou padrão
        modelo_para_usar = model or AI_MODEL_DEFAULT
        resposta_llm = self._call_llm_api(user_prompt, system_prompt, model=modelo_para_usar)
        
        if resposta_llm:
            try:
                # Tentar extrair JSON da resposta
                import re
                json_match = re.search(r'\{[^}]+\}', resposta_llm, re.DOTALL)
                if json_match:
                    resultado = json.loads(json_match.group())
                    if 'ncm' in resultado:
                        # Adicionar aviso sobre validação
                        if 'explicacao' in resultado:
                            resultado['explicacao'] += ' ⚠️ IMPORTANTE: Valide este NCM contra a nomenclatura oficial disponível no cache local.'
                        else:
                            resultado['explicacao'] = '⚠️ IMPORTANTE: Valide este NCM contra a nomenclatura oficial disponível no cache local.'
                        
                        self._set_cache(cache_key, resultado)
                        return resultado
            except Exception as e:
                logger.warning(f"[AI_SERVICE] Erro ao parsear resposta JSON da IA: {e}")
        
        # Fallback: retornar sem sugestão
        resultado = {
            'ncm': None,
            'explicacao': 'Não foi possível obter sugestão da IA. Use a busca por descrição para encontrar NCMs manualmente.',
            'confianca': 0,
            'sugestoes_alternativas': []
        }
        return resultado

    def sugerir_preenchimento(self, tipo: str, contexto: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sugere preenchimento de campos baseado em contexto.
        
        Args:
            tipo: Tipo de sugestão ('ncm', 'atributos', 'fundamentacao', etc)
            contexto: Contexto atual (campos já preenchidos)
        
        Returns:
            Dict com sugestões
        """
        # ⚠️ PROTÓTIPO: Implementação básica
        # Para produção, adicionar lógica específica por tipo
        
        cache_key = self._cache_key('sugestao', {'tipo': tipo, 'contexto': contexto})
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        resultado = {
            'tipo': tipo,
            'sugestoes': [],
            'fonte': 'fallback'
        }
        
        # Fallback básico sem LLM
        if tipo == 'ncm' and 'ncm' in contexto:
            # Sugestões básicas baseadas em NCM comum
            ncm = contexto.get('ncm', '')
            if ncm.startswith('07'):
                resultado['sugestoes'] = [
                    {'campo': 'unidadeComercial', 'valor': 'KG', 'confianca': 0.7, 'explicacao': 'Produtos agrícolas geralmente usam KG'}
                ]
        
        self._set_cache(cache_key, resultado)
        return resultado
    
    def validar_proativo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validação proativa antes de enviar à API.
        
        Args:
            payload: Payload que será enviado
        
        Returns:
            Dict com avisos e sugestões
        """
        avisos = []
        sugestoes = []
        
        # Validações básicas sem LLM
        if 'identificacao' in payload:
            if 'numeroItem' in payload.get('identificacao', {}):
                num_item = payload['identificacao']['numeroItem']
                if isinstance(num_item, (int, str)) and int(num_item) > 0:
                    sugestoes.append({
                        'tipo': 'info',
                        'mensagem': 'Item tem numeroItem - será usado PUT para atualizar',
                        'campo': 'identificacao.numeroItem'
                    })
            elif payload.get('identificacao') == {}:
                sugestoes.append({
                    'tipo': 'info',
                    'mensagem': 'Item sem numeroItem - será usado POST para criar',
                    'campo': 'identificacao'
                })
        
        # Verificar campos obrigatórios comuns
        campos_obrigatorios = ['produto', 'mercadoria']
        for campo in campos_obrigatorios:
            if campo not in payload:
                avisos.append({
                    'tipo': 'erro',
                    'mensagem': f'Campo obrigatório faltando: {campo}',
                    'campo': campo
                })
        
        return {
            'avisos': avisos,
            'sugestoes': sugestoes,
            'valido': len(avisos) == 0,
            'fonte': 'validacao_basica'
        }


# Instância global do serviço
_ai_service = None

def get_ai_service() -> AIService:
    """Retorna instância singleton do serviço de IA."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
