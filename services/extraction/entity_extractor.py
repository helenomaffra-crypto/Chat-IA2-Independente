"""
=============================================================================
🔍 EXTRATOR DE ENTIDADES
=============================================================================
Responsabilidade única: Extrair entidades de mensagens.

Este módulo é uma camada fina sobre EntityExtractionService,
fornecendo interface limpa e fallback automático.

📊 TAMANHO: ~150 linhas (máximo)
=============================================================================
"""
import logging
from typing import Dict, Any, Optional
from services.entity_extraction_service import get_entity_extraction_service

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extrator de entidades.
    
    Responsabilidade: Extrair entidades de mensagens usando IA.
    """
    
    def __init__(self):
        """Inicializa o extrator"""
        self.service = get_entity_extraction_service()
    
    def extract(
        self,
        mensagem: str,
        contexto_anterior: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Extrai entidades da mensagem.
        
        Args:
            mensagem: Mensagem do usuário
            contexto_anterior: Contexto de conversa anterior
        
        Returns:
            Dicionário com entidades extraídas
        """
        try:
            return self.service.extrair_entidades(mensagem, contexto_anterior)
        except Exception as e:
            logger.error(f"❌ Erro ao extrair entidades: {e}")
            # Retornar estrutura vazia em caso de erro
            return {
                "processos": [],
                "categorias": [],
                "documentos": {"ces": [], "dis": [], "duimps": [], "ccts": []},
                "periodos_temporais": {},
                "acoes": [],
                "intencao_principal": "Não identificado"
            }
