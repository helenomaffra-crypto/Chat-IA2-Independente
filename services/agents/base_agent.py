"""
Classe base para todos os agents do sistema.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Classe base abstrata para todos os agents.
    
    Todos os agents devem herdar desta classe e implementar o método execute().
    """
    
    def __init__(self):
        """Inicializa o agent base."""
        self.name = self.__class__.__name__
        logger.debug(f"✅ {self.name} inicializado")
    
    @abstractmethod
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa uma tool específica.
        
        Args:
            tool_name: Nome da tool a ser executada
            arguments: Argumentos da tool
            context: Contexto adicional (opcional)
        
        Returns:
            Dict com resultado da execução contendo:
            - sucesso: bool
            - resposta: str (mensagem para o usuário)
            - erro: str (se houver erro)
            - dados: Any (dados adicionais, opcional)
        """
        pass
    
    def log_execution(self, tool_name: str, arguments: Dict[str, Any], sucesso: bool):
        """
        Registra a execução de uma tool para logging e métricas.
        
        Args:
            tool_name: Nome da tool executada
            arguments: Argumentos usados
            sucesso: Se a execução foi bem-sucedida
        """
        if sucesso:
            logger.debug(f"✅ {self.name}.{tool_name} executado com sucesso")
        else:
            logger.warning(f"⚠️ {self.name}.{tool_name} falhou")
    
    def validate_arguments(self, arguments: Dict[str, Any], required: list) -> Tuple[bool, Optional[str]]:
        """
        Valida se os argumentos obrigatórios estão presentes.
        
        Args:
            arguments: Argumentos a validar
            required: Lista de argumentos obrigatórios
        
        Returns:
            Tuple (is_valid, error_message)
        """
        missing = [arg for arg in required if arg not in arguments or arguments[arg] is None]
        if missing:
            return False, f"Argumentos obrigatórios faltando: {', '.join(missing)}"
        return True, None
















