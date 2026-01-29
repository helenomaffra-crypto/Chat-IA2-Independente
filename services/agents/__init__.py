"""
Agentes de IA por domínio para o Chat Service.
Cada agente é responsável por um conjunto específico de tools relacionadas.
"""

from .base_agent import BaseAgent
from .processo_agent import ProcessoAgent
from .duimp_agent import DuimpAgent

__all__ = [
    'BaseAgent',
    'ProcessoAgent',
    'DuimpAgent',
]

