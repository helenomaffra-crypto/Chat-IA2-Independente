"""
Utilitários para processamento de emails.

Funções auxiliares para limpeza e formatação de conteúdo de email.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmailUtils:
    """Utilitários estáticos para processamento de emails."""
    
    @staticmethod
    def limpar_frases_problematicas(texto: str) -> str:
        """
        Remove frases problemáticas que a IA insiste em adicionar.
        Mantém a funcionalidade de email intacta, apenas remove menções não solicitadas.
        
        Exemplos de frases removidas:
        - "heleno pode mandar o email"
        - "pode enviar por email"
        - "se quiser, posso enviar por email"
        
        Args:
            texto: Texto a ser limpo
        
        Returns:
            Texto limpo sem frases problemáticas
        """
        if not texto:
            return texto
        
        # Lista de frases problemáticas a remover (padrões regex)
        # ✅ CORREÇÃO (10/01/2026): Melhorar padrões para capturar variações com pontuação e espaços
        # Ordem importa: padrões mais específicos primeiro
        padroes_problematicos = [
            # "Oi, heleno pode mandar o email!" (com vírgula, ponto de exclamação e quebra de linha)
            r'(?i)oi\s*,?\s*heleno\s+pode\s+mandar\s+o\s+email[!.,?\s\n]*',
            # "heleno pode mandar o email" (sem "Oi" no início)
            r'(?i)heleno\s+pode\s+mandar\s+o\s+email[!.,?\s\n]*',
            # "pode mandar o email" (genérico)
            r'(?i)pode\s+mandar\s+o\s+email[!.,?\s\n]*',
            # "pode enviar o email"
            r'(?i)pode\s+enviar\s+o\s+email[!.,?\s\n]*',
            # "pode enviar por email"
            r'(?i)pode\s+enviar\s+por\s+email[!.,?\s\n]*',
            # "se quiser, posso enviar por email"
            r'(?i)se\s+quiser\s*,?\s*posso\s+enviar\s+por\s+email[!.,?\s\n]*',
            # "posso enviar por email"
            r'(?i)posso\s+enviar\s+por\s+email[!.,?\s\n]*',
            # "quiser, posso enviar"
            r'(?i)quiser\s*,?\s*posso\s+enviar[!.,?\s\n]*',
        ]
        
        texto_limpo = texto
        for padrao in padroes_problematicos:
            # Remover a frase (já está case-insensitive no padrão com (?i))
            texto_limpo = re.sub(padrao, '', texto_limpo)
        
        # Limpar espaços múltiplos (mas preservar quebras de linha)
        texto_limpo = re.sub(r'[ \t]+', ' ', texto_limpo)  # Apenas espaços e tabs
        texto_limpo = re.sub(r'\n\s*\n\s*\n+', '\n\n', texto_limpo)  # Múltiplas quebras de linha
        
        # Limpar espaços no início e fim, mas preservar estrutura geral
        linhas = texto_limpo.split('\n')
        linhas_limpas = [linha.strip() for linha in linhas]
        texto_limpo = '\n'.join(linhas_limpas)
        
        return texto_limpo
    
    @staticmethod
    def limpar_frases_problematicas_de_preview(texto: str) -> str:
        """
        Versão especializada para limpar previews de email.
        
        ⚠️ NOTA: Em previews de email, não devemos aplicar limpeza agressiva,
        pois pode remover conteúdo importante. Esta função é mais conservadora.
        
        Args:
            texto: Texto do preview a ser limpo
        
        Returns:
            Texto limpo (versão conservadora)
        """
        # Por enquanto, usa a mesma lógica, mas pode ser ajustada no futuro
        # para ser mais conservadora com previews
        return EmailUtils.limpar_frases_problematicas(texto)
