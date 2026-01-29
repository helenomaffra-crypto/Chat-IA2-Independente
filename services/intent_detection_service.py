"""
IntentDetectionService - Detecção de intenções do usuário para filtragem de tools e validação.

Este serviço detecta a intenção do usuário e permite:
1. Filtrar tools expostas ao modelo (whitelist)
2. Validar tool escolhida vs intenção (gate de mismatch)
3. Forçar tool correta quando há mismatch

Data: 14/01/2026
"""

import logging
import re
from typing import Dict, Optional, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Tipos de intenção detectáveis."""
    ENVIAR_RELATORIO_EMAIL = "enviar_relatorio_email"
    ENVIAR_EMAIL_PERSONALIZADO = "enviar_email_personalizado"
    CONSULTAR_EXTRATO_BANCARIO = "consultar_extrato_bancario"
    CONSULTAR_PROCESSO = "consultar_processo"
    CRIAR_DUIMP = "criar_duimp"
    CONSULTAR_NCM = "consultar_ncm"
    OUTROS = "outros"


class IntentDetectionService:
    """Serviço para detectar intenções do usuário."""
    
    def __init__(self):
        """Inicializa o serviço."""
        pass
    
    def detectar_intencao(
        self,
        mensagem: str,
        historico: Optional[List[Dict]] = None,
        ultima_resposta_texto: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detecta a intenção do usuário baseado na mensagem e contexto.
        
        Args:
            mensagem: Mensagem do usuário
            historico: Histórico de conversas (opcional)
            ultima_resposta_texto: Texto da última resposta (opcional)
        
        Returns:
            Dict com:
            - intent_type: IntentType detectado
            - confidence: float (0.0 a 1.0)
            - keywords: List[str] - palavras-chave encontradas
            - contexto: Dict com informações adicionais
        """
        mensagem_lower = mensagem.lower().strip()
        
        # ✅ INTENÇÃO 1: Enviar relatório por email
        if self._eh_intencao_enviar_relatorio_email(mensagem_lower, ultima_resposta_texto):
            return {
                'intent_type': IntentType.ENVIAR_RELATORIO_EMAIL,
                'confidence': 0.95,
                'keywords': self._extrair_keywords_enviar_relatorio(mensagem_lower),
                'contexto': {
                    'tem_report_meta': '[REPORT_META:' in (ultima_resposta_texto or ''),
                    'ultima_resposta_tem_relatorio': self._ultima_resposta_tem_relatorio(ultima_resposta_texto),
                }
            }
        
        # ✅ INTENÇÃO 2: Consultar extrato bancário
        if self._eh_intencao_consultar_extrato_bancario(mensagem_lower):
            return {
                'intent_type': IntentType.CONSULTAR_EXTRATO_BANCARIO,
                'confidence': 0.90,
                'keywords': self._extrair_keywords_extrato(mensagem_lower),
                'contexto': {}
            }
        
        # ✅ INTENÇÃO 3: Enviar email personalizado
        if self._eh_intencao_enviar_email_personalizado(mensagem_lower, ultima_resposta_texto):
            return {
                'intent_type': IntentType.ENVIAR_EMAIL_PERSONALIZADO,
                'confidence': 0.85,
                'keywords': self._extrair_keywords_email_personalizado(mensagem_lower),
                'contexto': {}
            }
        
        # ✅ INTENÇÃO 4: Criar DUIMP
        if self._eh_intencao_criar_duimp(mensagem_lower):
            return {
                'intent_type': IntentType.CRIAR_DUIMP,
                'confidence': 0.90,
                'keywords': self._extrair_keywords_duimp(mensagem_lower),
                'contexto': {}
            }
        
        # ✅ INTENÇÃO 5: Consultar NCM
        if self._eh_intencao_consultar_ncm(mensagem_lower):
            return {
                'intent_type': IntentType.CONSULTAR_NCM,
                'confidence': 0.85,
                'keywords': self._extrair_keywords_ncm(mensagem_lower),
                'contexto': {}
            }
        
        # ✅ INTENÇÃO 6: Consultar processo
        if self._eh_intencao_consultar_processo(mensagem_lower):
            return {
                'intent_type': IntentType.CONSULTAR_PROCESSO,
                'confidence': 0.80,
                'keywords': self._extrair_keywords_processo(mensagem_lower),
                'contexto': {}
            }
        
        # Padrão: outros
        return {
            'intent_type': IntentType.OUTROS,
            'confidence': 0.50,
            'keywords': [],
            'contexto': {}
        }
    
    def _eh_intencao_enviar_relatorio_email(
        self,
        mensagem_lower: str,
        ultima_resposta_texto: Optional[str] = None
    ) -> bool:
        """Verifica se a intenção é enviar relatório por email."""
        # Padrões de "envia/mande + email + relatório"
        padroes_envio = [
            r'envia.*relat[oó]rio.*email',
            r'mande.*relat[oó]rio.*email',
            r'envie.*relat[oó]rio.*email',
            r'manda.*relat[oó]rio.*email',
            r'envia.*esse.*relat[oó]rio',
            r'mande.*esse.*relat[oó]rio',
            r'envie.*esse.*relat[oó]rio',
            r'manda.*esse.*relat[oó]rio',
            r'envia.*relat[oó]rio.*para',
            r'mande.*relat[oó]rio.*para',
            r'envie.*relat[oó]rio.*para',
            r'manda.*relat[oó]rio.*para',
        ]
        
        for padrao in padroes_envio:
            if re.search(padrao, mensagem_lower):
                # ✅ VALIDAÇÃO: Verificar se última resposta tem relatório
                if ultima_resposta_texto:
                    tem_relatorio = (
                        '[REPORT_META:' in ultima_resposta_texto or
                        'O QUE TEMOS PRA HOJE' in ultima_resposta_texto.upper() or
                        'FECHAMENTO DO DIA' in ultima_resposta_texto.upper() or
                        'PROCESSOS CHEGANDO' in ultima_resposta_texto.upper() or
                        'DIs EM ANÁLISE' in ultima_resposta_texto.upper() or
                        'DUIMPs EM ANÁLISE' in ultima_resposta_texto.upper() or
                        'PENDÊNCIAS ATIVAS' in ultima_resposta_texto.upper()
                    )
                    if tem_relatorio:
                        return True
        
        return False
    
    def _eh_intencao_consultar_extrato_bancario(self, mensagem_lower: str) -> bool:
        """Verifica se a intenção é consultar extrato bancário."""
        padroes_extrato = [
            r'extrato.*banco',
            r'extrato.*bb',
            r'extrato.*santander',
            r'extrato.*banc[aá]rio',
            r'movimenta[çc][oõ]es.*banco',
            r'transa[çc][oõ]es.*banco',
            r'saldo.*banco',
            r'extrato.*conta',
            r'extrato.*ag[êe]ncia',
        ]
        
        # ✅ EXCLUIR: Extrato de CE/CCT/DI/DUIMP (não é extrato bancário)
        padroes_excluir = [
            r'extrato.*ce',
            r'extrato.*cct',
            r'extrato.*di',
            r'extrato.*duimp',
            r'extrato.*processo',
        ]
        
        for padrao_excluir in padroes_excluir:
            if re.search(padrao_excluir, mensagem_lower):
                return False
        
        for padrao in padroes_extrato:
            if re.search(padrao, mensagem_lower):
                return True
        
        return False
    
    def _eh_intencao_enviar_email_personalizado(
        self,
        mensagem_lower: str,
        ultima_resposta_texto: Optional[str] = None
    ) -> bool:
        """Verifica se a intenção é enviar email personalizado (não relatório)."""
        # ✅ CORREÇÃO CRÍTICA (14/01/2026):
        # Cobrir frases naturais do usuário, ex:
        # "manda um email simpático para X@gmail.com avisando que..."
        # "envie para X@gmail.com e assine Y"
        padrao_email = r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
        tem_email = bool(re.search(padrao_email, mensagem_lower))
        verbos_envio = ['manda', 'mande', 'mandar', 'envia', 'envie', 'enviar']
        tem_verbo_envio = any(v in mensagem_lower for v in verbos_envio)
        tem_palavra_email = ('email' in mensagem_lower) or ('e-mail' in mensagem_lower)
        tem_assinatura = ('assine' in mensagem_lower) or ('assinar' in mensagem_lower) or ('assinatura' in mensagem_lower)

        # Se tem email explícito e verbo de envio, isso é praticamente determinístico
        if tem_email and tem_verbo_envio:
            return True

        # Se menciona "email" (ou e-mail) + verbo de envio, também é forte
        if tem_palavra_email and tem_verbo_envio:
            return True

        # Se pede "assine X" junto de verbo de envio, normalmente é email
        if tem_assinatura and tem_verbo_envio:
            return True

        # Padrões de email personalizado
        padroes_email = [
            r'envia.*email.*sobre',
            r'mande.*email.*sobre',
            r'envie.*email.*sobre',
            r'envia.*email.*com',
            r'mande.*email.*com',
            r'envie.*email.*com',
            r'envia.*email.*explicando',
            r'mande.*email.*explicando',
            r'envie.*email.*explicando',
        ]
        
        # ✅ VALIDAÇÃO: NÃO é email personalizado se última resposta foi relatório
        if ultima_resposta_texto:
            tem_relatorio = (
                '[REPORT_META:' in ultima_resposta_texto or
                'O QUE TEMOS PRA HOJE' in ultima_resposta_texto.upper() or
                'FECHAMENTO DO DIA' in ultima_resposta_texto.upper()
            )
            if tem_relatorio:
                return False  # É relatório, não email personalizado
        
        for padrao in padroes_email:
            if re.search(padrao, mensagem_lower):
                return True
        
        return False
    
    def _eh_intencao_criar_duimp(self, mensagem_lower: str) -> bool:
        """Verifica se a intenção é criar DUIMP."""
        padroes_duimp = [
            r'criar.*duimp',
            r'registrar.*duimp',
            r'gerar.*duimp',
            r'fazer.*duimp',
            r'montar.*duimp',
            r'criar.*duimp.*processo',
            r'registrar.*duimp.*processo',
        ]
        
        for padrao in padroes_duimp:
            if re.search(padrao, mensagem_lower):
                return True
        
        return False
    
    def _eh_intencao_consultar_ncm(self, mensagem_lower: str) -> bool:
        """Verifica se a intenção é consultar NCM."""
        padroes_ncm = [
            r'ncm.*para',
            r'ncm.*de',
            r'qual.*ncm',
            r'classifica[çc][aã]o.*fiscal',
            r'al[íi]quotas',
            r'tecwin',
        ]
        
        for padrao in padroes_ncm:
            if re.search(padrao, mensagem_lower):
                return True
        
        return False
    
    def _eh_intencao_consultar_processo(self, mensagem_lower: str) -> bool:
        """Verifica se a intenção é consultar processo."""
        # Padrão de processo: CATEGORIA.NUMERO/ANO (ex: DMD.0001/26)
        padrao_processo = r'[A-Z]{2,4}\.\d{4}/\d{2}'
        if re.search(padrao_processo, mensagem_lower):
            return True
        
        padroes_consulta = [
            r'status.*processo',
            r'situa[çc][aã]o.*processo',
            r'como.*est[áa].*processo',
            r'processo.*[A-Z]{2,4}',
        ]
        
        for padrao in padroes_consulta:
            if re.search(padrao, mensagem_lower):
                return True
        
        return False
    
    def _ultima_resposta_tem_relatorio(self, ultima_resposta_texto: Optional[str]) -> bool:
        """Verifica se a última resposta contém um relatório."""
        if not ultima_resposta_texto:
            return False
        
        return (
            '[REPORT_META:' in ultima_resposta_texto or
            'O QUE TEMOS PRA HOJE' in ultima_resposta_texto.upper() or
            'FECHAMENTO DO DIA' in ultima_resposta_texto.upper() or
            'PROCESSOS CHEGANDO' in ultima_resposta_texto.upper() or
            'DIs EM ANÁLISE' in ultima_resposta_texto.upper() or
            'DUIMPs EM ANÁLISE' in ultima_resposta_texto.upper() or
            'PENDÊNCIAS ATIVAS' in ultima_resposta_texto.upper()
        )
    
    def _extrair_keywords_enviar_relatorio(self, mensagem_lower: str) -> List[str]:
        """Extrai palavras-chave relacionadas a enviar relatório."""
        keywords = []
        if 'envia' in mensagem_lower or 'envie' in mensagem_lower:
            keywords.append('envia')
        if 'mande' in mensagem_lower or 'manda' in mensagem_lower:
            keywords.append('mande')
        if 'relatorio' in mensagem_lower or 'relatório' in mensagem_lower:
            keywords.append('relatorio')
        if 'email' in mensagem_lower:
            keywords.append('email')
        return keywords
    
    def _extrair_keywords_extrato(self, mensagem_lower: str) -> List[str]:
        """Extrai palavras-chave relacionadas a extrato bancário."""
        keywords = []
        if 'extrato' in mensagem_lower:
            keywords.append('extrato')
        if 'banco' in mensagem_lower or 'bancario' in mensagem_lower:
            keywords.append('banco')
        if 'bb' in mensagem_lower:
            keywords.append('bb')
        if 'santander' in mensagem_lower:
            keywords.append('santander')
        return keywords
    
    def _extrair_keywords_email_personalizado(self, mensagem_lower: str) -> List[str]:
        """Extrai palavras-chave relacionadas a email personalizado."""
        keywords = []
        if 'email' in mensagem_lower:
            keywords.append('email')
        if 'sobre' in mensagem_lower:
            keywords.append('sobre')
        if 'explicando' in mensagem_lower:
            keywords.append('explicando')
        return keywords
    
    def _extrair_keywords_duimp(self, mensagem_lower: str) -> List[str]:
        """Extrai palavras-chave relacionadas a DUIMP."""
        keywords = []
        if 'duimp' in mensagem_lower:
            keywords.append('duimp')
        if 'criar' in mensagem_lower or 'registrar' in mensagem_lower:
            keywords.append('criar')
        return keywords
    
    def _extrair_keywords_ncm(self, mensagem_lower: str) -> List[str]:
        """Extrai palavras-chave relacionadas a NCM."""
        keywords = []
        if 'ncm' in mensagem_lower:
            keywords.append('ncm')
        if 'aliquotas' in mensagem_lower or 'alíquotas' in mensagem_lower:
            keywords.append('aliquotas')
        if 'tecwin' in mensagem_lower:
            keywords.append('tecwin')
        return keywords
    
    def _extrair_keywords_processo(self, mensagem_lower: str) -> List[str]:
        """Extrai palavras-chave relacionadas a processo."""
        keywords = []
        if 'processo' in mensagem_lower:
            keywords.append('processo')
        if re.search(r'[A-Z]{2,4}\.\d{4}/\d{2}', mensagem_lower):
            keywords.append('referencia_processo')
        return keywords
    
    def obter_whitelist_tools(self, intent_type: IntentType) -> Optional[List[str]]:
        """
        Retorna whitelist de tools permitidas para uma intenção específica.
        
        Args:
            intent_type: Tipo de intenção detectada
        
        Returns:
            Lista de nomes de tools permitidas, ou None se todas são permitidas
        """
        whitelists = {
            IntentType.ENVIAR_RELATORIO_EMAIL: [
                'enviar_relatorio_email',
                'buscar_secao_relatorio_salvo',
                'buscar_relatorio_por_id',
                'obter_last_visible_report_id',
            ],
            IntentType.ENVIAR_EMAIL_PERSONALIZADO: [
                'enviar_email_personalizado',
                'enviar_email',
            ],
            IntentType.CONSULTAR_EXTRATO_BANCARIO: [
                'consultar_extrato_bb',
                'consultar_extrato_santander',
            ],
            IntentType.CRIAR_DUIMP: [
                'criar_duimp',
                'verificar_duimp_registrada',
                'obter_dados_duimp',
            ],
            IntentType.CONSULTAR_NCM: [
                'sugerir_ncm_por_descricao',
                'consultar_tecwin_ncm',
                'consultar_aliquotas_tecwin',
            ],
            IntentType.CONSULTAR_PROCESSO: [
                'consultar_status_processo',
                'consultar_processo_consolidado',
                'listar_processos',
            ],
            IntentType.OUTROS: None,  # Sem whitelist (todas permitidas)
        }
        
        return whitelists.get(intent_type)
    
    def validar_tool_vs_intencao(
        self,
        tool_escolhida: str,
        intent_type: IntentType,
    ) -> Dict[str, Any]:
        """
        Valida se a tool escolhida pelo modelo corresponde à intenção detectada.
        
        Args:
            tool_escolhida: Nome da tool escolhida pelo modelo
            intent_type: Tipo de intenção detectada
        
        Returns:
            Dict com:
            - valido: bool
            - deve_forcar: bool - se deve forçar tool correta
            - tool_correta: Optional[str] - tool que deveria ser usada
            - motivo: str - motivo da validação
        """
        # ✅ GATE DE MISMATCH: Se intenção é "enviar relatório", bloquear extrato
        if intent_type == IntentType.ENVIAR_RELATORIO_EMAIL:
            tools_extrato = ['consultar_extrato_bb', 'consultar_extrato_santander']
            if tool_escolhida in tools_extrato:
                return {
                    'valido': False,
                    'deve_forcar': True,
                    'tool_correta': 'enviar_relatorio_email',
                    'motivo': f'MISMATCH: Intenção é enviar relatório, mas modelo escolheu {tool_escolhida} (extrato bancário). Deve usar enviar_relatorio_email.'
                }
            
            # Se não escolheu enviar_relatorio_email, forçar
            if tool_escolhida != 'enviar_relatorio_email':
                return {
                    'valido': False,
                    'deve_forcar': True,
                    'tool_correta': 'enviar_relatorio_email',
                    'motivo': f'MISMATCH: Intenção é enviar relatório, mas modelo escolheu {tool_escolhida}. Deve usar enviar_relatorio_email.'
                }
        
        # ✅ GATE DE MISMATCH: Se intenção é "consultar extrato", não permitir enviar_relatorio_email
        if intent_type == IntentType.CONSULTAR_EXTRATO_BANCARIO:
            if tool_escolhida == 'enviar_relatorio_email':
                return {
                    'valido': False,
                    'deve_forcar': True,
                    'tool_correta': 'consultar_extrato_bb',  # ou santander, dependendo do contexto
                    'motivo': f'MISMATCH: Intenção é consultar extrato bancário, mas modelo escolheu {tool_escolhida}. Deve usar consultar_extrato_bb ou consultar_extrato_santander.'
                }
        
        # ✅ VALIDAÇÃO: Verificar whitelist
        whitelist = self.obter_whitelist_tools(intent_type)
        if whitelist and tool_escolhida not in whitelist:
            return {
                'valido': False,
                'deve_forcar': True,
                'tool_correta': whitelist[0] if whitelist else None,
                'motivo': f'Tool {tool_escolhida} não está na whitelist para intenção {intent_type.value}. Whitelist: {whitelist}'
            }
        
        # ✅ Tudo OK
        return {
            'valido': True,
            'deve_forcar': False,
            'tool_correta': None,
            'motivo': 'Tool válida para a intenção detectada'
        }
