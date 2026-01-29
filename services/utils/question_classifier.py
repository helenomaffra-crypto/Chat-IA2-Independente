"""
Utilitários para classificação de perguntas do usuário.

Classifica perguntas em diferentes tipos para seleção automática de modelo de IA
e decisões de processamento.
"""
import re
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class QuestionClassifier:
    """Utilitários estáticos para classificação de perguntas."""
    
    @staticmethod
    def eh_pergunta_analitica(mensagem: str) -> bool:
        """
        Detecta perguntas de análise/BI onde vale a pena usar o modelo analítico.
        
        Exemplos-alvo:
        - "top 10 clientes por valor CIF importado em 2025"
        - "quais fornecedores mais atrasam entrega?"
        - "quantas cargas foram desembaraçadas por mês em 2025?"
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            True se for pergunta analítica, False caso contrário
        """
        msg = mensagem.lower()
        
        # Sinais fortes de ranking / agregação
        if "top " in msg or "top10" in msg or "ranking" in msg:
            return True
        
        # Palavras de agregação / estatística
        palavras_agregacao = [
            "total de ", "soma de ", "somar ", "média de", "media de",
            "por mês", "por mes", "por ano", "por semana",
            "distribuição", "distribuicao", "tendência", "tendencia",
            "evolução", "evolucao", "percentual", "percentual de",
        ]
        if any(p in msg for p in palavras_agregacao):
            return True
        
        # Termos típicos de BI COMEX
        termos_bi = [
            "valor cif", "valor fob", "valor importado",
            "clientes", "fornecedores", "ncm", "familias", "produtos",
            "kpi", "indicador", "relatório", "relatorio", "dashboard",
        ]
        if any(t in msg for t in termos_bi) and ("top" in msg or "mais " in msg or "menos " in msg):
            return True
        
        return False
    
    @staticmethod
    def eh_pergunta_conhecimento_geral(mensagem: str) -> bool:
        """
        Detecta perguntas de conhecimento geral onde vale a pena usar GPT-5.
        
        ✅ ESTRATÉGIA HÍBRIDA: Usa GPT-5 para conhecimento geral (mais atualizado)
        e GPT-4o para operações com tools (mais rápido e barato).
        
        Exemplos-alvo:
        - "qual a cotação de frete de um container de 20 da china pro brasil?"
        - "explique sobre multas em importação" (sem mencionar legislação específica)
        - "como funciona o processo de importação?"
        - "qual a diferença entre DI e DUIMP?"
        
        Exemplos que NÃO são conhecimento geral (usam tools):
        - "situacao do gym.0047/25" (menciona processo específico)
        - "qual a ncm de iphone" (usa tool de NCM)
        - "como estão os mv5?" (usa tool de processos)
        - "qual a explicação para classificação de carro de golfe" (usa tool de NESH)
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            True se for pergunta de conhecimento geral, False caso contrário
        """
        msg = mensagem.lower()
        
        # ✅ CRÍTICO: Excluir perguntas sobre classificação fiscal (devem usar NESH)
        # Essas perguntas devem usar buscar_nota_explicativa_nesh ou buscar_legislacao_responses
        termos_classificacao = [
            "classificacao", "classificação", "classificar", "classificar",
            "explicacao.*classif", "explicação.*classif", "explica.*classif",
            "como classificar", "onde classificar", "ncm de", "ncm para",
            "nota explicativa", "nesh", "critérios.*classif", "criterios.*classif",
        ]
        if any(re.search(t, msg, re.IGNORECASE) for t in termos_classificacao):
            # É pergunta sobre classificação fiscal - NÃO é conhecimento geral
            # Deve usar tool de NESH
            return False
        
        # ✅ Sinais de que É conhecimento geral (não usa tools):
        # Perguntas conceituais/educacionais sem menção a entidades específicas
        perguntas_conceituais = [
            "o que é", "o que significa", "me explica", "explique",
            "como funciona", "qual a diferença", "diferença entre",
            "quanto custa", "qual o preço", "qual a cotação",
            "quanto é", "quanto vale", "qual o valor de mercado",
        ]
        if any(p in msg for p in perguntas_conceituais):
            # ✅ Verificar se NÃO menciona entidades específicas do sistema
            entidades_sistema = [
                # Processos
                r'\b[a-z]{2,4}\.\d{1,4}/\d{2}\b',  # ALH.0001/25, VDM.003/25
                r'\b(alh|vdm|mss|bnd|dmd|gym|sll|mv5|gps|ntm|mcd|dba|arg|upi)\b',  # Categorias
                # Documentos
                r'\b(ce|cct|di|duimp)\s+\d+',  # CE 123456, DI 1234567890
                r'\b(ncm|ncms)\s+\d{8}',  # NCM 85171231
                # Ações específicas
                r'\b(criar|registrar|montar|gerar)\s+(duimp|di)',  # Criar DUIMP
                r'\b(vincular|associar)\s+',  # Vincular documento
                r'\b(consultar|verificar|buscar)\s+(processo|ce|cct|di|duimp)',  # Consultar específico
            ]
            
            # Se menciona entidades do sistema, NÃO é conhecimento geral
            for padrao in entidades_sistema:
                if re.search(padrao, msg, re.IGNORECASE):
                    return False
            
            # Se não menciona entidades, É conhecimento geral
            return True
        
        # ✅ Perguntas sobre mercado/preços/cotações (conhecimento geral)
        termos_mercado = [
            "cotação", "cotaçao", "preço", "preco", "valor de mercado",
            "quanto custa", "quanto é", "quanto vale", "preço de",
            "custo de", "tarifa de", "taxa de",
        ]
        if any(t in msg for t in termos_mercado):
            # Verificar se não menciona processo/documento específico
            if not re.search(r'\b[a-z]{2,4}\.\d{1,4}/\d{2}\b', msg, re.IGNORECASE):
                if not re.search(r'\b(ce|cct|di|duimp)\s+\d+', msg, re.IGNORECASE):
                    return True
        
        return False
    
    @staticmethod
    def eh_pergunta_generica(mensagem: str, extrair_categoria_callback: Optional[Callable[[str], Optional[str]]] = None) -> bool:
        """
        Identifica se a mensagem é uma pergunta genérica que deve limpar o contexto anterior.
        
        Exemplos de perguntas genéricas (limpam contexto):
        - "quais processos têm pendência?" → Genérica (sem categoria)
        - "quais processos estão bloqueados?" → Genérica
        - "mostre todos os processos" → Genérica
        
        Exemplos de perguntas específicas (mantêm contexto):
        - "quais estão bloqueados?" → Específica (mantém categoria do histórico)
        - "quais têm pendência?" → Específica (mantém categoria do histórico)
        
        Args:
            mensagem: Mensagem do usuário
            extrair_categoria_callback: Função opcional para extrair categoria da mensagem
                                        (ex: lambda msg: EntityExtractors.extrair_categoria(msg))
        
        Returns:
            True se for pergunta genérica, False caso contrário
        """
        mensagem_lower = mensagem.lower()
        
        # Padrões de perguntas genéricas (mencionam "processos" ou "todos")
        padroes_genericos = [
            r'quais\s+processos',
            r'todos\s+os\s+processos',
            r'todas\s+as\s+processos',
            r'mostre\s+(?:todos|todas)',
            r'listar\s+(?:todos|todas)',
            r'quais\s+são\s+os\s+processos',
            r'quais\s+são\s+as\s+processos',
        ]
        
        # Verificar se é pergunta genérica
        for padrao in padroes_genericos:
            if re.search(padrao, mensagem_lower):
                # Verificar se NÃO menciona categoria específica
                categoria_na_mensagem = None
                if extrair_categoria_callback:
                    try:
                        categoria_na_mensagem = extrair_categoria_callback(mensagem)
                    except Exception as e:
                        logger.debug(f'Erro ao extrair categoria da mensagem: {e}')
                
                if not categoria_na_mensagem:
                    return True
        
        return False
    
    @staticmethod
    def identificar_se_precisa_contexto(mensagem: str, extrair_processo_callback: Optional[Callable[[str], Optional[str]]] = None) -> bool:
        """
        Identifica se a mensagem precisa de contexto de processo/CE mas não o menciona.
        
        Exemplos:
        - "tem bloqueio?" → Precisa contexto
        - "qual o frete?" → Precisa contexto
        - "consulte o CE do processo MSS.0018/25" → Não precisa (já tem)
        - "qual processo tem bloqueio?" → Não precisa (pergunta geral)
        
        Args:
            mensagem: Mensagem do usuário
            extrair_processo_callback: Função opcional para extrair processo da mensagem
                                       (ex: lambda msg: EntityExtractors.extrair_processo_referencia(msg))
        
        Returns:
            True se precisa de contexto, False caso contrário
        """
        mensagem_lower = mensagem.lower()
        
        # Perguntas que precisam de contexto específico
        perguntas_especificas = [
            r'tem\s+bloqueio',
            r'qual\s+(?:o|a)\s+(?:frete|situa[çc][ãa]o|status|origem|destino|navio|afrmm|tum|consignat[áa]rio)',
            r'peso\s+e\s+cubagem',
            r'quanto\s+(?:de|é|vale)',
            r'j[áa]\s+descarreg',
            r'quando\s+descarreg',
            r'bloqueado',
            r'm[ée]tricas',
            r'densidade',
            r'consignat[áa]rio',
            r'quem\s+é\s+(?:o|a)\s+consignat[áa]rio',
            r'cnpj\s+consignat[áa]rio'
        ]
        
        # ✅ CRÍTICO: Verificar se é pergunta geral ANTES de verificar se precisa contexto
        # Perguntas gerais começam com "qual processo", "quais processos", "que processo", etc.
        # Essas perguntas NÃO precisam de contexto (são consultas gerais)
        padroes_pergunta_geral = [
            r'qual\s+processo',
            r'quais\s+processos',
            r'que\s+processo',
            r'quais\s+são\s+os\s+processos',
            r'quais\s+são\s+as\s+processos',
        ]
        
        for padrao_geral in padroes_pergunta_geral:
            if re.search(padrao_geral, mensagem_lower):
                # É pergunta geral → não precisa de contexto
                return False
        
        # Verificar se a mensagem contém alguma dessas perguntas específicas
        for padrao in perguntas_especificas:
            if re.search(padrao, mensagem_lower):
                # Verificar se já menciona processo ou CE
                tem_processo = False
                tem_ce = bool(re.search(r'(?:CE|ce)\s+\d{15}', mensagem))
                
                if extrair_processo_callback:
                    try:
                        tem_processo = bool(extrair_processo_callback(mensagem))
                    except Exception as e:
                        logger.debug(f'Erro ao extrair processo da mensagem: {e}')
                else:
                    # Fallback: usar regex simples
                    tem_processo = bool(re.search(r'\b[a-z]{2,4}\.\d{1,4}/\d{2}\b', mensagem, re.IGNORECASE))
                
                # Se não tem processo nem CE, precisa de contexto
                if not tem_processo and not tem_ce:
                    return True
        
        return False
