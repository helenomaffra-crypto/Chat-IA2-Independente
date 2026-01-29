"""
EmailImprovementHandler - Centraliza lógica de melhorar emails.

Este handler gerencia o fluxo completo de melhorar emails:
1. Detecta pedido de melhorar email
2. Chama IA para melhorar
3. Extrai email melhorado da resposta da IA
4. Atualiza draft no banco
5. Reemite preview atualizado

⚠️ FUTURO: O método _extrair_email_da_resposta_ia será ELIMINADO quando
implementarmos JSON estruturado da IA em vez de regex frágil.

Data: 09/01/2026
Status: ⏳ EM DESENVOLVIMENTO
"""

import re
import logging
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)


class EmailImprovementHandler:
    """
    Handler centralizado para melhorar emails usando IA.
    
    Responsabilidades:
    - Detectar pedido de melhorar email
    - Chamar IA para melhorar o email
    - Extrair email melhorado da resposta da IA
    - Atualizar draft no banco
    - Reemitir preview atualizado
    """
    
    def __init__(
        self,
        email_draft_service: Any = None,
        ai_service: Any = None,
        prompt_builder: Any = None,
    ):
        """
        Inicializa o handler com dependências necessárias.
        
        Args:
            email_draft_service: Serviço de gerenciamento de drafts de email
            ai_service: Serviço de IA para melhorar emails
            prompt_builder: Builder de prompts para chamar IA
        """
        self.email_draft_service = email_draft_service
        self.ai_service = ai_service
        self.prompt_builder = prompt_builder
        
        # Lazy loading se não fornecido
        if not self.email_draft_service:
            try:
                from services.email_draft_service import get_email_draft_service
                self.email_draft_service = get_email_draft_service()
            except Exception as e:
                logger.warning(f'⚠️ Erro ao carregar EmailDraftService: {e}')
    
    def detectar_pedido(self, mensagem: str) -> bool:
        """
        Detecta se mensagem é pedido para melhorar email.
        
        Args:
            mensagem: Mensagem do usuário
        
        Returns:
            True se é pedido para melhorar email, False caso contrário
        """
        mensagem_lower = mensagem.lower().strip()
        
        padroes_melhorar = [
            'melhore', 'melhorar', 'melhore o email', 'melhore esse email', 'melhore esse eamail',  # Typos
            'elabore', 'elaborar', 'elabore melhor', 'elabora melhor',
            'refinar', 'refine',
            'reescrever', 'reescreva', 'reescreva melhor', 'melhore esse',
            'assine', 'assinar', 'mude a assinatura', 'troque a assinatura',
            'mais', 'mais elaborado', 'mais carinhoso', 'mais formal', 'mais didático',
            'torne mais formal', 'torne mais informal', 'torne mais profissional',
            'melhore a escrita', 'melhore o texto', 'melhore o conteúdo'
        ]
        
        # Verificar padrões simples
        for padrao in padroes_melhorar:
            if padrao in mensagem_lower:
                logger.info(f"🎯 [EMAIL_IMPROVEMENT] Pedido para melhorar email detectado: '{padrao}'")
                return True
        
        # Verificar padrões com regex (mais robusto)
        padroes_regex = [
            r'melhore\s+(?:o|esse|este)\s+(?:e?mail|e?maile?|correio)',
            r'melhore\s+esse\s+e?a?m?a?i?l',
        ]
        
        for padrao in padroes_regex:
            if re.search(padrao, mensagem_lower, re.IGNORECASE):
                logger.info(f"🎯 [EMAIL_IMPROVEMENT] Pedido para melhorar email detectado via regex: '{padrao}'")
                return True
        
        return False
    
    def processar_resposta_melhorar_email(
        self,
        resposta_ia: str,
        dados_email_original: Dict[str, Any],
        session_id: str,
        ultima_resposta_aguardando_email: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Processa a resposta da IA após pedido de melhorar email.
        
        Extrai email refinado, atualiza draft no banco e reemite preview atualizado.
        
        Args:
            resposta_ia: Resposta da IA contendo email melhorado
            dados_email_original: Dados do email original em preview
            session_id: ID da sessão
            ultima_resposta_aguardando_email: Estado atual de email pendente (opcional)
        
        Returns:
            Dict com:
            - 'sucesso': bool
            - 'resposta': str (preview atualizado ou mensagem de erro/pergunta)
            - 'dados_email_atualizados': Dict (dados atualizados, para atualizar estado)
            - 'draft_id': str (se atualizado)
            - 'revision': int (nova revisão)
            - 'erro': str (se houver)
        """
        logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Processando resposta da IA para extrair email refinado...')
        
        # Tentar extrair email refinado da resposta da IA
        logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Chamando _extrair_email_da_resposta_ia com resposta_ia (tamanho: {len(resposta_ia) if resposta_ia else 0} chars)')
        logger.debug(f'✅✅✅ [EMAIL_IMPROVEMENT] Resposta da IA (primeiros 500 chars): {resposta_ia[:500] if resposta_ia else "None"}')
        email_refinado = self._extrair_email_da_resposta_ia(resposta_ia, dados_email_original)
        
        # Se não conseguiu extrair, perguntar ao usuário
        if not email_refinado:
            logger.warning(f'⚠️⚠️⚠️ [EMAIL_IMPROVEMENT] Não conseguiu extrair email refinado da resposta da IA')
            logger.debug(f'⚠️⚠️⚠️ [EMAIL_IMPROVEMENT] Resposta completa da IA para debug:\n{resposta_ia}')
            
            # Tentar obter draft_id de múltiplas fontes
            draft_id = dados_email_original.get('draft_id')
            if not draft_id and ultima_resposta_aguardando_email:
                draft_id = ultima_resposta_aguardando_email.get('draft_id')
            
            if draft_id:
                logger.warning(f'⚠️⚠️⚠️ [EMAIL_IMPROVEMENT] Tem draft_id {draft_id}, mas extração falhou - deixando IA processar novamente')
                # Retornar resposta original da IA (pode ter informações úteis)
                return {
                    'sucesso': False,
                    'resposta': resposta_ia,  # Manter resposta original
                    'dados_email_atualizados': dados_email_original,
                    'draft_id': draft_id,
                    'erro': 'EXTRACAO_FALHOU_COM_DRAFT'
                }
            else:
                # Sem draft_id e sem extração - perguntar ao usuário
                resposta_pergunta = (
                    "❓ Não consegui identificar claramente o email melhorado na sua resposta.\n\n"
                    "Você poderia:\n"
                    "1. Reescrever o email melhorado de forma mais clara, ou\n"
                    "2. Me dizer o que você gostaria de melhorar no email atual?\n\n"
                    "Assim posso atualizar o preview corretamente."
                )
                logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Perguntando ao usuário sobre email melhorado')
                return {
                    'sucesso': False,
                    'resposta': resposta_pergunta,
                    'dados_email_atualizados': dados_email_original,
                    'erro': 'EXTRACAO_FALHOU_SEM_DRAFT'
                }
        
        # Email refinado extraído com sucesso - atualizar banco + memória + reemitir preview
        logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Email refinado extraído! Atualizando banco + memória + reemitindo preview...')
        logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] draft_id atual em dados_email_original: {dados_email_original.get("draft_id")}')
        
        # Tentar obter draft_id de múltiplas fontes
        draft_id = dados_email_original.get('draft_id')
        if not draft_id and ultima_resposta_aguardando_email:
            draft_id = ultima_resposta_aguardando_email.get('draft_id')
            logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] draft_id encontrado em ultima_resposta_aguardando_email: {draft_id}')
        
        # Preparar dados atualizados (começar com dados originais)
        dados_email_atualizados = dados_email_original.copy()
        if draft_id:
            dados_email_atualizados['draft_id'] = draft_id
        
        # 1. Atualizar banco (se tem draft_id)
        nova_revision = None
        if draft_id:
            try:
                if not self.email_draft_service:
                    from services.email_draft_service import get_email_draft_service
                    self.email_draft_service = get_email_draft_service()
                
                nova_revision = self.email_draft_service.revisar_draft(
                    draft_id=draft_id,
                    assunto=email_refinado.get('assunto'),
                    conteudo=email_refinado.get('conteudo')
                )
                
                if nova_revision:
                    logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Draft {draft_id} revisado para revision {nova_revision} no banco')
                    # Obter draft atualizado do banco (fonte da verdade)
                    draft_atualizado = self.email_draft_service.obter_draft(draft_id)
                    if draft_atualizado:
                        # Atualizar com dados do banco (sempre última versão)
                        dados_email_atualizados['assunto'] = draft_atualizado.assunto
                        dados_email_atualizados['conteudo'] = draft_atualizado.conteudo
                        dados_email_atualizados['revision'] = draft_atualizado.revision
                        logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Memória atualizada com dados do banco (revision {draft_atualizado.revision})')
                    else:
                        logger.warning(f'⚠️ Draft {draft_id} revisado mas não encontrado ao buscar - usando dados extraídos')
                        # Fallback: usar dados extraídos
                        dados_email_atualizados['assunto'] = email_refinado.get('assunto', dados_email_atualizados.get('assunto'))
                        dados_email_atualizados['conteudo'] = email_refinado.get('conteudo', dados_email_atualizados.get('conteudo'))
                else:
                    logger.warning(f'⚠️ Não foi possível revisar draft {draft_id} no banco - atualizando apenas memória')
                    # Fallback: atualizar apenas memória
                    dados_email_atualizados['assunto'] = email_refinado.get('assunto', dados_email_atualizados.get('assunto'))
                    dados_email_atualizados['conteudo'] = email_refinado.get('conteudo', dados_email_atualizados.get('conteudo'))
            except Exception as e:
                logger.warning(f'⚠️ Erro ao revisar draft {draft_id} no banco: {e} - atualizando apenas memória', exc_info=True)
                # Fallback: atualizar apenas memória
                dados_email_atualizados['assunto'] = email_refinado.get('assunto', dados_email_atualizados.get('assunto'))
                dados_email_atualizados['conteudo'] = email_refinado.get('conteudo', dados_email_atualizados.get('conteudo'))
        else:
            # Sem draft_id: criar novo draft com email melhorado
            logger.warning(f'⚠️⚠️⚠️ [EMAIL_IMPROVEMENT] Sem draft_id! Criando novo draft com email melhorado...')
            try:
                if not self.email_draft_service:
                    from services.email_draft_service import get_email_draft_service
                    self.email_draft_service = get_email_draft_service()
                
                novo_draft_id = self.email_draft_service.criar_draft(
                    destinatarios=dados_email_atualizados.get('destinatarios', []),
                    assunto=email_refinado.get('assunto', dados_email_atualizados.get('assunto')),
                    conteudo=email_refinado.get('conteudo', dados_email_atualizados.get('conteudo')),
                    session_id=session_id,
                    cc=dados_email_atualizados.get('cc'),
                    bcc=dados_email_atualizados.get('bcc'),
                    funcao_email=dados_email_atualizados.get('funcao', 'enviar_email_personalizado')
                )
                
                if novo_draft_id:
                    dados_email_atualizados['draft_id'] = novo_draft_id
                    dados_email_atualizados['revision'] = 1
                    nova_revision = 1
                    logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Novo draft criado: {novo_draft_id} (revision 1)')
                else:
                    logger.warning(f'⚠️ Não foi possível criar novo draft, atualizando apenas memória')
                    dados_email_atualizados['assunto'] = email_refinado.get('assunto', dados_email_atualizados.get('assunto'))
                    dados_email_atualizados['conteudo'] = email_refinado.get('conteudo', dados_email_atualizados.get('conteudo'))
            except Exception as e:
                logger.error(f'❌ Erro ao criar novo draft: {e}', exc_info=True)
                # Fallback: atualizar apenas memória
                dados_email_atualizados['assunto'] = email_refinado.get('assunto', dados_email_atualizados.get('assunto'))
                dados_email_atualizados['conteudo'] = email_refinado.get('conteudo', dados_email_atualizados.get('conteudo'))
        
        # 2. Reemitir preview atualizado (OBRIGATÓRIO)
        funcao_email = dados_email_atualizados.get('funcao', 'enviar_email_personalizado')
        preview_atualizado = None
        
        if funcao_email == 'enviar_email_personalizado':
            from datetime import datetime
            preview_atualizado = f"📧 **Email para Envio (Atualizado)**\n\n"
            preview_atualizado += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview_atualizado += f"**De:** Sistema mAIke (Make Consultores)\n"
            preview_atualizado += f"**Para:** {', '.join(dados_email_atualizados.get('destinatarios', []))}\n"
            if dados_email_atualizados.get('cc'):
                preview_atualizado += f"**CC:** {', '.join(dados_email_atualizados.get('cc', []))}\n"
            if dados_email_atualizados.get('bcc'):
                preview_atualizado += f"**BCC:** {', '.join(dados_email_atualizados.get('bcc', []))}\n"
            preview_atualizado += f"**Assunto:** {dados_email_atualizados.get('assunto')}\n"
            preview_atualizado += f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            preview_atualizado += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            preview_atualizado += f"**Mensagem:**\n\n"
            preview_atualizado += f"{dados_email_atualizados.get('conteudo')}\n\n"
            preview_atualizado += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            preview_atualizado += f"⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"
            logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Preview atualizado reemitido!')
        else:
            # Para outros tipos de email, manter resposta da IA mas atualizar estado
            logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Email refinado atualizado no estado (tipo: {funcao_email})')
            preview_atualizado = resposta_ia  # Manter resposta original
        
        return {
            'sucesso': True,
            'resposta': preview_atualizado,
            'dados_email_atualizados': dados_email_atualizados,
            'draft_id': dados_email_atualizados.get('draft_id'),
            'revision': nova_revision or dados_email_atualizados.get('revision', 1),
            'erro': None
        }
    
    def _extrair_email_da_resposta_ia(
        self,
        resposta_ia: str,
        dados_email_original: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai email refinado da resposta da IA quando usuário pediu para melhorar/elaborar.
        
        ⚠️ FUTURO: Este método será ELIMINADO quando implementarmos JSON estruturado da IA.
        
        Args:
            resposta_ia: Resposta da IA (pode conter preview de email ou texto livre)
            dados_email_original: Dados do email original em preview
        
        Returns:
            Dict com 'assunto' e 'conteudo' refinados, ou None se não conseguir extrair
        """
        try:
            # Tentar extrair do formato de preview estruturado
            # Padrão: **Assunto:** [assunto] ou Assunto: [assunto] ou Assunto sugerido: [assunto]
            match_assunto = re.search(r'\*\*?Assunto[:\s]+\*\*?\s*(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
            assunto_refinado = match_assunto.group(1).strip() if match_assunto else None
            
            # ✅ CORREÇÃO CRÍTICA (09/01/2026): Também tentar padrão "Assunto sugerido:" que a IA usa
            if not assunto_refinado:
                # Tentar padrão "Assunto sugerido:" primeiro (mais específico)
                match_assunto_sugerido = re.search(r'Assunto\s+sugerido[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                if match_assunto_sugerido:
                    assunto_refinado = match_assunto_sugerido.group(1).strip()
                    # Limpar possíveis marcadores no final
                    assunto_refinado = re.sub(r'\s*Corpo.*$', '', assunto_refinado, flags=re.IGNORECASE).strip()
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Assunto extraído via padrão "Assunto sugerido:": "{assunto_refinado}"')
                else:
                    # Tentar padrão alternativo: "Assunto sugerido" sem dois pontos
                    match_assunto_sugerido_alt = re.search(r'Assunto\s+sugerido[:\s]*\n\s*(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                    if match_assunto_sugerido_alt:
                        assunto_refinado = match_assunto_sugerido_alt.group(1).strip()
                        assunto_refinado = re.sub(r'\s*Corpo.*$', '', assunto_refinado, flags=re.IGNORECASE).strip()
                        logger.info(f'✅ [EMAIL_IMPROVEMENT] Assunto extraído via padrão alternativo "Assunto sugerido": "{assunto_refinado}"')
            
            # ✅ CORREÇÃO (09/01/2026): Também tentar padrão "Assunto:" seguido de texto na mesma linha ou próxima
            if not assunto_refinado:
                match_assunto_linha = re.search(r'(?:^|\n)\s*Assunto[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                if match_assunto_linha:
                    assunto_refinado = match_assunto_linha.group(1).strip()
                    assunto_refinado = re.sub(r'\s*(Corpo|Corpo do email):.*$', '', assunto_refinado, flags=re.IGNORECASE).strip()
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Assunto extraído via padrão "Assunto:": "{assunto_refinado}"')
            
            conteudo_refinado = None
            
            # Tentar extrair conteúdo
            # Padrão: **Conteúdo:** ou Conteúdo: seguido de texto
            match_conteudo = re.search(r'\*\*?Conteúdo:\*\*?\s*\n(.+?)(?:\n\n|$|⚠️|💡)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
            if match_conteudo:
                conteudo_temp = match_conteudo.group(1).strip()
                # ✅ NOVO: Se tem separador "---", pegar apenas o que está depois dele
                if '---' in conteudo_temp:
                    partes = conteudo_temp.split('---', 1)
                    if len(partes) > 1:
                        conteudo_temp = partes[1].strip()
                conteudo_refinado = conteudo_temp
                logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão "Conteúdo:" (formato markdown)')
            else:
                # Tentar padrão alternativo: texto após "Conteúdo:" até fim ou próximo marcador
                match_conteudo = re.search(r'Conteúdo[:\s]+\n(.+?)(?=\n(?:Se quiser|💡|━━━━|Confirme)|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match_conteudo:
                    conteudo_temp = match_conteudo.group(1).strip()
                    # ✅ NOVO: Se tem separador "---", pegar apenas o que está depois dele
                    if '---' in conteudo_temp:
                        partes = conteudo_temp.split('---', 1)
                        if len(partes) > 1:
                            conteudo_temp = partes[1].strip()
                    conteudo_refinado = conteudo_temp
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão "Conteúdo:"')
            
            # ✅ CORREÇÃO CRÍTICA (09/01/2026): Também tentar padrão "Corpo:" ou "Corpo do email:" que a IA usa
            # ✅ NOVO (09/01/2026): Tentar padrão quando resposta está dentro de preview formatado
            if not conteudo_refinado:
                # Tentar extrair de preview formatado: "Conteúdo:" seguido de conteúdo até "Se quiser" ou "💡"
                match_conteudo_preview = re.search(r'Conteúdo[:\s]*\n(.+?)(?=\n(?:Se quiser|💡|━━━━)|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match_conteudo_preview:
                    conteudo_temp = match_conteudo_preview.group(1).strip()
                    # ✅ CRÍTICO: Remover texto introdutório que pode estar no início
                    # Padrão: "Heleno, segue uma versão..." ou "segue uma versão..." seguido de texto
                    conteudo_temp = re.sub(r'^[^\n]*(?:Heleno[,\s]*)?(?:segue|versão|versao|email|mensagem|melhorada|elaborada)[^\n]*:?\s*\n', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                    # Remover assunto duplicado se aparecer no corpo
                    conteudo_temp = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                    # Remover "Se quiser..." se ainda estiver presente
                    conteudo_temp = re.sub(r'\nSe quiser[^\n]*$', '', conteudo_temp, flags=re.IGNORECASE | re.DOTALL)
                    conteudo_refinado = conteudo_temp.strip()
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão "Conteúdo:" do preview ({len(conteudo_refinado)} caracteres)')
                
                # Tentar padrão "Corpo do email:" primeiro (mais específico)
                if not conteudo_refinado:
                    # ✅ CORREÇÃO CRÍTICA (09/01/2026): Melhorar regex para capturar corretamente até "Se quiser" ou marcadores de fim
                    # Estratégia: capturar tudo após "Corpo do email:" até encontrar "Se quiser" (mesmo que na mesma linha ou próxima)
                    # ✅ IMPORTANTE: Usar (.*?) com DOTALL para capturar múltiplas linhas, e parar antes de "Se quiser" ou marcadores
                    match_corpo_email = re.search(r'Corpo\s+do\s+email[:\s]*\n(.*?)(?=\n\s*Se quiser|\n\n━━━━|━━━━|$)', resposta_ia, re.IGNORECASE | re.DOTALL)
                    if match_corpo_email:
                        conteudo_temp = match_corpo_email.group(1).strip()
                        logger.debug(f'✅✅✅ [EMAIL_IMPROVEMENT] Conteúdo capturado ANTES limpeza ({len(conteudo_temp)} chars): {conteudo_temp[:200]}...')
                        # ✅ CRÍTICO: Remover texto introdutório que pode estar no início
                        conteudo_temp_antes = conteudo_temp
                        conteudo_temp = re.sub(r'^[^\n]*(?:Heleno[,\s]*)?(?:segue|versão|versao|email|mensagem|melhorada|elaborada)[^\n]*:?\s*\n', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                        if conteudo_temp != conteudo_temp_antes:
                            logger.debug(f'✅✅✅ [EMAIL_IMPROVEMENT] Texto introdutório removido')
                        # Remover assunto duplicado se aparecer no corpo
                        conteudo_temp_antes = conteudo_temp
                        conteudo_temp = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                        if conteudo_temp != conteudo_temp_antes:
                            logger.debug(f'✅✅✅ [EMAIL_IMPROVEMENT] Assunto duplicado removido')
                        # Remover "Se quiser..." se ainda estiver presente no final
                        conteudo_temp_antes = conteudo_temp
                        conteudo_temp = re.sub(r'\n\s*Se quiser[^\n]*$', '', conteudo_temp, flags=re.IGNORECASE | re.DOTALL)
                        if conteudo_temp != conteudo_temp_antes:
                            logger.debug(f'✅✅✅ [EMAIL_IMPROVEMENT] "Se quiser" removido do final')
                        conteudo_refinado = conteudo_temp.strip()
                        logger.info(f'✅✅✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão "Corpo do email:" ({len(conteudo_refinado)} caracteres) - Primeiros 100 chars: {conteudo_refinado[:100]}')
                    else:
                        # ✅ FALLBACK: Tentar padrão mais simples - pegar tudo após "Corpo do email:" até encontrar linha que começa com "Se quiser"
                        match_corpo_email_simples = re.search(r'Corpo\s+do\s+email[:\s]*\n(.*?)(?=\n\s*Se quiser|\n\n━━━━|━━━━|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                        if match_corpo_email_simples:
                            conteudo_temp = match_corpo_email_simples.group(1).strip()
                            # ✅ CRÍTICO: Remover texto introdutório
                            conteudo_temp = re.sub(r'^[^\n]*(?:Heleno[,\s]*)?(?:segue|versão|versao|email|mensagem|melhorada|elaborada)[^\n]*:?\s*\n', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                            # Remover assunto duplicado
                            conteudo_temp = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                            # Remover "Se quiser..." se ainda estiver presente
                            conteudo_temp = re.sub(r'\n\s*Se quiser[^\n]*$', '', conteudo_temp, flags=re.IGNORECASE | re.DOTALL)
                            conteudo_refinado = conteudo_temp.strip()
                            logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão simples "Corpo do email:" ({len(conteudo_refinado)} caracteres)')
                        else:
                            # ✅ ÚLTIMO FALLBACK: Tentar capturar tudo após "Corpo do email:" até o final (mas limitar a 2000 chars)
                            match_corpo_email_fallback = re.search(r'Corpo\s+do\s+email[:\s]*\n(.{1,2000}?)(?=\n\n━━━━|━━━━|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                            if match_corpo_email_fallback:
                                conteudo_temp = match_corpo_email_fallback.group(1).strip()
                                # Remover "Se quiser..." se estiver presente
                                conteudo_temp = re.sub(r'\n\s*Se quiser[^\n]*$', '', conteudo_temp, flags=re.IGNORECASE | re.DOTALL)
                                conteudo_refinado = conteudo_temp.strip()
                                logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão fallback "Corpo do email:" ({len(conteudo_refinado)} caracteres)')
                
                # ✅ FALLBACK ADICIONAL: Se ainda não encontrou, tentar padrão "Corpo:" (sem "do email")
                if not conteudo_refinado:
                    # Tentar padrão mais específico: "Corpo:" seguido de conteúdo até linha que começa com "Se quiser"
                    match_corpo = re.search(r'Corpo[:\s]+\n(.*?)(?=\nSe quiser|\n\n━━━━|━━━━|$)', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    if match_corpo:
                        conteudo_temp = match_corpo.group(1).strip()
                        # ✅ CRÍTICO: Remover texto introdutório
                        conteudo_temp = re.sub(r'^[^\n]*(?:Heleno[,\s]*)?(?:segue|versão|versao|email|mensagem|melhorada|elaborada)[^\n]*:?\s*\n', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                        # Remover assunto duplicado
                        conteudo_temp = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                        # Remover "Se quiser..."
                        conteudo_temp = re.sub(r'\nSe quiser[^\n]*$', '', conteudo_temp, flags=re.IGNORECASE | re.DOTALL)
                        conteudo_refinado = conteudo_temp.strip()
                        logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão "Corpo:" ({len(conteudo_refinado)} caracteres)')
                    else:
                        # Tentar padrão simples sem lookahead: pegar tudo até linha que começa com "Se quiser"
                        match_corpo_simples = re.search(r'Corpo[:\s]+\n(.*?)\nSe quiser', resposta_ia, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                        if match_corpo_simples:
                            conteudo_temp = match_corpo_simples.group(1).strip()
                            # ✅ CRÍTICO: Remover texto introdutório e assunto duplicado
                            conteudo_temp = re.sub(r'^[^\n]*(?:Heleno[,\s]*)?(?:segue|versão|versao|email|mensagem|melhorada|elaborada)[^\n]*:?\s*\n', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                            conteudo_temp = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_temp, flags=re.IGNORECASE | re.MULTILINE)
                            conteudo_refinado = conteudo_temp.strip()
                            logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão simples "Corpo:" ({len(conteudo_refinado)} caracteres)')
            
            # Se não encontrou no formato estruturado, tentar extrair de texto livre
            if not assunto_refinado or not conteudo_refinado:
                # Verificar se a resposta contém um email completo (tem saudação e despedida)
                tem_saudacao = bool(re.search(r'^(Olá|Oi|Prezado|Querido|Meu amor|Meu querido|Olá,|Oi,|Querido|Querida)', resposta_ia, re.IGNORECASE | re.MULTILINE))
                tem_despedida = bool(re.search(r'(Atenciosamente|Com carinho|Com amor|Abraços|Beijos|Maria|\[Seu nome\]|Com carinho,|Com amor,|Atenciosamente,)', resposta_ia, re.IGNORECASE))
                
                # Se tem estrutura de email (saudação + despedida), extrair
                if tem_saudacao or tem_despedida:
                    # Assunto: tentar encontrar linha que começa com "Assunto:" ou usar padrão baseado no contexto
                    if not assunto_refinado:
                        # ✅ MELHORIA: Tentar encontrar assunto em linha separada (formato: "Assunto: Ausência na reunião...")
                        match_assunto_linha = re.search(r'Assunto[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                        if match_assunto_linha:
                            assunto_refinado = match_assunto_linha.group(1).strip()
                        else:
                            # ✅ NOVO: Tentar encontrar assunto após texto introdutório (ex: "segue uma versão... Assunto: ...")
                            match_assunto_apos_intro = re.search(r'(?:versão|versao|email|mensagem)[^:]*:\s*\n\s*Assunto[:\s]+(.+?)(?:\n|$)', resposta_ia, re.IGNORECASE | re.MULTILINE)
                            if match_assunto_apos_intro:
                                assunto_refinado = match_assunto_apos_intro.group(1).strip()
                            else:
                                # Tentar inferir assunto do contexto (ex: "convite para almoçar" → "Convite para Almoçar Hoje")
                                if 'almoçar' in resposta_ia.lower() or 'almoço' in resposta_ia.lower():
                                    assunto_refinado = 'Convite para Almoçar Hoje ❤️' if 'amor' in resposta_ia.lower() or 'amoroso' in resposta_ia.lower() else 'Convite para Almoçar Hoje'
                                elif 'reunião' in resposta_ia.lower() or 'reuniao' in resposta_ia.lower():
                                    # ✅ NOVO: Detectar assunto sobre reunião
                                    if 'ausência' in resposta_ia.lower() or 'ausencia' in resposta_ia.lower() or 'não poderei' in resposta_ia.lower():
                                        assunto_refinado = 'Ausência na reunião de hoje às 16h'
                                    else:
                                        assunto_refinado = dados_email_original.get('assunto', 'Mensagem')
                                else:
                                    assunto_refinado = dados_email_original.get('assunto', 'Mensagem')
                    
                    # Conteúdo: pegar todo o texto, removendo indicadores de fonte e marcadores
                    if not conteudo_refinado:
                        # ✅ MELHORIA: Tentar extrair conteúdo após saudação (Prezado, Olá, etc.)
                        match_email_completo = re.search(
                            r'(?:Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido)[^:]*:?\s*\n(.+?)(?:Atenciosamente|Com carinho|Com amor|Abraços|Beijos|Guilherme|\[Seu nome\])',
                            resposta_ia,
                            re.IGNORECASE | re.MULTILINE | re.DOTALL
                        )
                        if match_email_completo:
                            conteudo_bruto = match_email_completo.group(1).strip()
                            # Remover linhas introdutórias (ex: "segue uma versão...")
                            conteudo_bruto = re.sub(r'^[^\n]*(?:versão|versao|email|mensagem|melhorada|elaborada)[^\n]*\n', '', conteudo_bruto, flags=re.IGNORECASE | re.MULTILINE)
                            # Remover linha de assunto se estiver no meio
                            conteudo_bruto = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_bruto, flags=re.IGNORECASE | re.MULTILINE)
                            conteudo_refinado = conteudo_bruto.strip()
                        
                        if not conteudo_refinado:
                            # Remover indicadores de fonte e outros marcadores
                            conteudo_limpo = resposta_ia
                            # Remover tudo após marcadores de fim
                            conteudo_limpo = re.sub(r'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_limpo, flags=re.DOTALL)
                            conteudo_limpo = re.sub(r'🔍 \*\*FONTE:.*$', '', conteudo_limpo, flags=re.DOTALL)
                            conteudo_limpo = re.sub(r'💡.*$', '', conteudo_limpo, flags=re.DOTALL)
                            conteudo_limpo = re.sub(r'⚠️.*$', '', conteudo_limpo, flags=re.DOTALL)
                            # Remover linhas que começam com "Assunto:" se houver
                            conteudo_limpo = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                            # Remover linhas que começam com "Para:" se houver
                            conteudo_limpo = re.sub(r'^\*\*?Para:\*\*?\s*.*$', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                            # ✅ MELHORIA (09/01/2026): Remover texto introdutório antes do email (ex: "Heleno, segue uma versão...")
                            conteudo_limpo = re.sub(r'^[^\n]*(?:segue|versão|versao|email|mensagem|melhorada|elaborada|tom|formal|elegante)[^\n]*:?\s*\n', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                            # ✅ NOVO: Remover também padrões como "Heleno, segue..." ou "segue o mesmo email..."
                            conteudo_limpo = re.sub(r'^[^:]*:?\s*(?:segue|versão|versao|email|mensagem|melhorada|elaborada|tom|formal|elegante)[^:]*:?\s*\n', '', conteudo_limpo, flags=re.IGNORECASE | re.MULTILINE)
                            # ✅ NOVO: Remover linhas que são apenas texto introdutório (não começam com saudação)
                            linhas = conteudo_limpo.split('\n')
                            primeira_saudacao_idx = None
                            for i, linha in enumerate(linhas):
                                if re.match(r'^(Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido)', linha.strip(), re.IGNORECASE):
                                    primeira_saudacao_idx = i
                                    break
                            if primeira_saudacao_idx is not None and primeira_saudacao_idx > 0:
                                # Remover tudo antes da primeira saudação
                                conteudo_limpo = '\n'.join(linhas[primeira_saudacao_idx:])
                            conteudo_refinado = conteudo_limpo.strip()
                        
                        # Se ainda está vazio ou muito curto, usar resposta completa
                        if not conteudo_refinado or len(conteudo_refinado) < 20:
                            conteudo_refinado = resposta_ia.strip()
                            # Remover apenas indicadores de fonte no final
                            conteudo_refinado = re.sub(r'\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_refinado, flags=re.DOTALL)
            
            # Se ainda não encontrou, usar dados originais mas tentar melhorar assunto
            if not assunto_refinado:
                assunto_refinado = dados_email_original.get('assunto', 'Mensagem')
            
            # ✅ MELHORIA (09/01/2026): Se não conseguiu extrair conteúdo, tentar uma última vez com padrão mais permissivo
            if not conteudo_refinado:
                # Tentar extrair qualquer texto que pareça um email (tem saudação e despedida)
                linhas = resposta_ia.split('\n')
                primeira_saudacao_idx = None
                ultima_despedida_idx = None
                
                for i, linha in enumerate(linhas):
                    linha_limpa = linha.strip()
                    # Detectar primeira saudação
                    if primeira_saudacao_idx is None and re.match(r'^(Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido)', linha_limpa, re.IGNORECASE):
                        primeira_saudacao_idx = i
                    # Detectar última despedida (com nome ou assinatura)
                    if re.search(r'(Atenciosamente|Com carinho|Com amor|Abraços|Beijos|Guilherme|Maria|\[Seu nome\])', linha_limpa, re.IGNORECASE):
                        ultima_despedida_idx = i
                
                if primeira_saudacao_idx is not None:
                    # Extrair do início da saudação até o fim (ou até a despedida se encontrada)
                    fim_idx = ultima_despedida_idx + 1 if ultima_despedida_idx is not None else len(linhas)
                    conteudo_extraido = '\n'.join(linhas[primeira_saudacao_idx:fim_idx])
                    # Remover indicadores de fonte
                    conteudo_extraido = re.sub(r'━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_extraido, flags=re.DOTALL)
                    conteudo_extraido = re.sub(r'🔍.*$', '', conteudo_extraido, flags=re.DOTALL)
                    conteudo_extraido = re.sub(r'💡.*$', '', conteudo_extraido, flags=re.DOTALL)
                    conteudo_extraido = re.sub(r'⚠️.*$', '', conteudo_extraido, flags=re.DOTALL)
                    conteudo_refinado = conteudo_extraido.strip()
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão permissivo (linhas {primeira_saudacao_idx} até {fim_idx})')
            
            # ✅ CORREÇÃO (09/01/2026): Se ainda não conseguiu extrair, tentar padrão mais simples
            if not conteudo_refinado:
                # Padrão: remover tudo antes da primeira saudação (Prezado, Olá, etc.)
                linhas_simples = resposta_ia.split('\n')
                primeira_saudacao_simples = None
                for i, linha in enumerate(linhas_simples):
                    linha_limpa = linha.strip()
                    # ✅ MELHORIA: Detectar qualquer saudação (incluindo "Heleno," no início)
                    if re.search(r'^(Prezado|Olá|Oi|Querido|Querida|Meu amor|Meu querido|Heleno|Boa tarde|Bom dia|Boa noite)', linha_limpa, re.IGNORECASE):
                        primeira_saudacao_simples = i
                        break
                
                if primeira_saudacao_simples is not None:
                    # Pegar tudo da saudação até o fim (ou até indicador de fonte)
                    conteudo_simples = '\n'.join(linhas_simples[primeira_saudacao_simples:])
                    # Remover indicadores de fonte no final
                    conteudo_simples = re.sub(r'\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_simples, flags=re.DOTALL)
                    conteudo_simples = re.sub(r'\n🔍.*$', '', conteudo_simples, flags=re.DOTALL)
                    conteudo_simples = re.sub(r'\n💡.*$', '', conteudo_simples, flags=re.DOTALL)
                    conteudo_simples = re.sub(r'\n⚠️.*$', '', conteudo_simples, flags=re.DOTALL)
                    conteudo_refinado = conteudo_simples.strip()
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão simples (a partir da linha {primeira_saudacao_simples})')
            
            # ✅ CORREÇÃO CRÍTICA (09/01/2026): Se ainda não conseguiu, tentar remover apenas texto introdutório
            if not conteudo_refinado:
                # Tentar encontrar padrão: texto introdutório seguido de email
                match_intro_email = re.search(
                    r'(?:Heleno|segue|versão|versao|email|mensagem)[^:]*:?\s*\n\s*(Olá|Prezado|Oi|Querido|Querida|Meu amor|Meu querido|Heleno|Boa tarde|Bom dia|Boa noite)',
                    resposta_ia,
                    re.IGNORECASE | re.MULTILINE
                )
                if match_intro_email:
                    # Encontrar posição do início do email
                    pos_inicio_email = match_intro_email.end() - len(match_intro_email.group(2))
                    conteudo_do_email = resposta_ia[pos_inicio_email:]
                    # Remover indicadores de fonte
                    conteudo_do_email = re.sub(r'\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━.*$', '', conteudo_do_email, flags=re.DOTALL)
                    conteudo_do_email = re.sub(r'\n🔍.*$', '', conteudo_do_email, flags=re.DOTALL)
                    conteudo_do_email = re.sub(r'\n💡.*$', '', conteudo_do_email, flags=re.DOTALL)
                    conteudo_do_email = re.sub(r'\n⚠️.*$', '', conteudo_do_email, flags=re.DOTALL)
                    conteudo_refinado = conteudo_do_email.strip()
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído removendo texto introdutório')
            
            if not conteudo_refinado:
                # Se não conseguiu extrair, retornar None (não atualizar)
                logger.warning(f'⚠️ [EMAIL_IMPROVEMENT] Não conseguiu extrair email refinado da resposta da IA')
                logger.debug(f'⚠️ [EMAIL_IMPROVEMENT] Resposta da IA (primeiros 500 chars): {resposta_ia[:500]}')
                return None
            
            # ✅ LIMPEZA FINAL CRÍTICA (09/01/2026): Remover texto introdutório e "Se quiser..." que podem ter sido capturados
            if conteudo_refinado:
                # ✅ PRIMEIRO: Detectar e remover separador "---" e tudo antes dele (padrão comum da IA)
                # Padrão: "texto introdutório\n---\nemail real"
                linhas = conteudo_refinado.split('\n')
                linhas_apos_separador = []
                separador_encontrado = False
                
                for linha in linhas:
                    linha_strip = linha.strip()
                    
                    # ✅ Detectar separador (---, ____, ===, etc.) - pelo menos 3 caracteres
                    if re.match(r'^[-=_]{3,}$', linha_strip):
                        separador_encontrado = True
                        continue  # Pular a linha do separador
                    
                    # Se encontrou separador, adicionar todas as linhas depois
                    if separador_encontrado:
                        linhas_apos_separador.append(linha)
                    elif not separador_encontrado:
                        # Antes do separador: verificar se é linha introdutória
                        # Se não é introdutória e não encontrou separador ainda, pode ser conteúdo válido
                        if not re.search(r'(?:Heleno[,\s]*)?(?:segue|vai|aqui|versão|versao|email|mensagem|melhorada|elaborada|mantendo|objetivo|original)', linha_strip, re.IGNORECASE):
                            # Não parece introdutória, adicionar
                            linhas_apos_separador.append(linha)
                
                # Se encontrou separador, usar apenas conteúdo após separador
                if separador_encontrado:
                    conteudo_refinado = '\n'.join(linhas_apos_separador).strip()
                    logger.info(f'✅ [EMAIL_IMPROVEMENT] Removido texto antes de separador "---"')
                else:
                    # Não tem separador, processar normalmente removendo linhas introdutórias
                    linhas_limpas = []
                    inicio_email_encontrado = False
                    
                    for linha in linhas:
                        linha_strip = linha.strip()
                        
                        # Detectar início do email (primeira saudação ou conteúdo real)
                        if not inicio_email_encontrado:
                            # ✅ MELHORADO: Detectar padrões de saudação
                            if re.match(r'^(Prezado|Olá|Oi|Querido|Querida|Boa tarde|Bom dia|Boa noite)', linha_strip, re.IGNORECASE):
                                inicio_email_encontrado = True
                                linhas_limpas.append(linha)
                            elif re.search(r'(?:Heleno[,\s]*)?(?:segue|vai|aqui|versão|versao|email|mensagem|melhorada|elaborada|mantendo|objetivo|original)', linha_strip, re.IGNORECASE):
                                # Pular linhas introdutórias
                                continue
                            elif linha_strip.startswith('Assunto:'):
                                # Pular linha de assunto duplicado
                                continue
                            elif linha_strip:
                                # Linha não vazia e não introdutória - começar a partir daqui
                                inicio_email_encontrado = True
                                linhas_limpas.append(linha)
                        else:
                            # Após encontrar início, adicionar todas as linhas até encontrar "Se quiser..."
                            if re.match(r'^Se quiser', linha_strip, re.IGNORECASE):
                                # Parar aqui (não incluir "Se quiser...")
                                break
                            linhas_limpas.append(linha)
                    
                    conteudo_refinado = '\n'.join(linhas_limpas).strip()
                
                # ✅ MELHORADO: Remover frases introdutórias que possam ter ficado no início (limpeza adicional)
                # Remover padrões como "Heleno, segue...", "mantendo o objetivo...", etc. mesmo após limpeza
                conteudo_refinado = re.sub(r'^[^\n]*(?:Heleno[,\s]*)?(?:segue|vai|aqui)[^\n]*(?:versão|versao|email|mensagem|melhorada|elaborada)[^\n]*(?:mantendo[^\n]*objetivo[^\n]*original[^\n]*)?:?\s*\n+', '', conteudo_refinado, flags=re.IGNORECASE | re.MULTILINE)
                conteudo_refinado = re.sub(r'^[^\n]*(?:mantendo|objetivo|original)[^\n]*:?\s*\n+', '', conteudo_refinado, flags=re.IGNORECASE | re.MULTILINE)
                
                # Remover "Se quiser..." se ainda estiver presente no final
                conteudo_refinado = re.sub(r'\n+Se quiser[^\n]*$', '', conteudo_refinado, flags=re.IGNORECASE | re.DOTALL)
                conteudo_refinado = re.sub(r'\n+[^\n]*Se quiser[^\n]*$', '', conteudo_refinado, flags=re.IGNORECASE | re.DOTALL)
                
                # ✅ NOVO: Remover linhas vazias no início e final
                conteudo_refinado = conteudo_refinado.strip()
            
            # ✅ ESTRATÉGIA FINAL (09/01/2026): Se nenhuma extração estruturada funcionou, tentar extração genérica
            if not conteudo_refinado:
                logger.warning(f'⚠️ [EMAIL_IMPROVEMENT] Extração estruturada falhou, tentando extração genérica...')
                # Tentar encontrar primeira saudação válida e pegar tudo até marcadores de fim
                padrao_saudacao = r'(?:Olá|Prezado|Querido|Querida|Boa tarde|Bom dia|Boa noite|Oi)[,\s]*[^\n]*\n'
                match_saudacao = re.search(padrao_saudacao, resposta_ia, re.IGNORECASE)
                if match_saudacao:
                    # Pegar tudo desde a saudação até marcadores de fim
                    inicio_conteudo = match_saudacao.end()
                    # Procurar marcadores de fim: "Se quiser", "💡", "━━━━", "Confirme", ou fim do texto
                    fim_match = re.search(r'\n(?:Se quiser|💡|━━━━|Confirme|⚠️)', resposta_ia[inicio_conteudo:], re.IGNORECASE)
                    if fim_match:
                        conteudo_genérico = resposta_ia[inicio_conteudo:inicio_conteudo + fim_match.start()].strip()
                    else:
                        # Sem marcador de fim, pegar tudo até o final (mas limitar a 5000 chars para evitar problemas)
                        conteudo_genérico = resposta_ia[inicio_conteudo:inicio_conteudo + 5000].strip()
                    
                    # Limpar apenas introdutórios óbvios, mas preservar conteúdo real
                    conteudo_genérico = re.sub(r'^[^\n]*(?:Heleno[,\s]*)?(?:segue|versão|versao|email|mensagem|melhorada|elaborada)[^\n]*(?:mantendo[^\n]*objetivo[^\n]*original[^\n]*)?:?\s*\n+', '', conteudo_genérico, flags=re.IGNORECASE | re.MULTILINE, count=1)  # count=1: apenas primeira ocorrência
                    conteudo_genérico = re.sub(r'^Assunto[:\s]+.*$', '', conteudo_genérico, flags=re.IGNORECASE | re.MULTILINE)
                    conteudo_genérico = re.sub(r'^Corpo[:\s]+.*$', '', conteudo_genérico, flags=re.IGNORECASE | re.MULTILINE)
                    conteudo_refinado = conteudo_genérico.strip()
                    
                    if conteudo_refinado:
                        logger.info(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído via padrão genérico (após saudação) - {len(conteudo_refinado)} caracteres')
            
            # ✅ VALIDAÇÃO CRÍTICA: Garantir que assunto e conteúdo foram extraídos
            if not assunto_refinado:
                assunto_refinado = dados_email_original.get('assunto', 'Mensagem')
                logger.warning(f'⚠️ [EMAIL_IMPROVEMENT] Assunto não extraído, usando original: "{assunto_refinado}"')
            
            # ✅✅✅ VALIDAÇÃO CRÍTICA MELHORADA (09/01/2026): Rejeitar conteúdo muito curto ou apenas saudação
            if not conteudo_refinado:
                logger.error(f'❌ [EMAIL_IMPROVEMENT] CRÍTICO: Conteúdo não extraído após todas as tentativas! Retornando None para não sobrescrever email original.')
                logger.error(f'❌ [EMAIL_IMPROVEMENT] Resposta da IA completa para debug (primeiros 1000 chars):\n{resposta_ia[:1000]}')
                return None
            
            # ✅ NOVO: Validar se conteúdo não é apenas saudação ou muito curto
            conteudo_sem_espacos = conteudo_refinado.replace('\n', ' ').replace(' ', '').strip()
            # Padrões que indicam conteúdo muito curto ou apenas saudação
            padroes_muito_curto = [
                r'^olá[.,]?$',  # Apenas "Olá," ou "Olá."
                r'^prezado[.,]?$',  # Apenas "Prezado," ou "Prezado."
                r'^oi[.,]?$',  # Apenas "Oi," ou "Oi."
                r'^olá,?\s*$',  # "Olá," com espaços
            ]
            
            for padrao in padroes_muito_curto:
                if re.match(padrao, conteudo_sem_espacos, re.IGNORECASE):
                    logger.error(f'❌ [EMAIL_IMPROVEMENT] CRÍTICO: Conteúdo extraído é muito curto ou apenas saudação: "{conteudo_refinado[:50]}"')
                    logger.error(f'❌ [EMAIL_IMPROVEMENT] Resposta da IA completa para debug (primeiros 1000 chars):\n{resposta_ia[:1000]}')
                    return None
            
            # Validar comprimento mínimo (pelo menos 20 caracteres sem espaços/quebras)
            if len(conteudo_sem_espacos) < 20:
                logger.error(f'❌ [EMAIL_IMPROVEMENT] CRÍTICO: Conteúdo extraído muito curto ({len(conteudo_sem_espacos)} chars): "{conteudo_refinado[:100]}"')
                logger.error(f'❌ [EMAIL_IMPROVEMENT] Resposta da IA completa para debug (primeiros 1000 chars):\n{resposta_ia[:1000]}')
                return None
            
            logger.info(f'✅ [EMAIL_IMPROVEMENT] Email refinado extraído com sucesso - Assunto: "{assunto_refinado[:50]}...", Conteúdo: {len(conteudo_refinado)} caracteres')
            logger.debug(f'✅ [EMAIL_IMPROVEMENT] Assunto extraído: "{assunto_refinado}"')
            logger.debug(f'✅ [EMAIL_IMPROVEMENT] Conteúdo extraído (primeiros 200 chars): {conteudo_refinado[:200]}')
            
            return {
                'assunto': assunto_refinado,
                'conteudo': conteudo_refinado
            }
            
        except Exception as e:
            logger.error(f'❌ [EMAIL_IMPROVEMENT] Erro ao extrair email da resposta da IA: {e}', exc_info=True)
            return None


def get_email_improvement_handler(
    email_draft_service: Any = None,
    ai_service: Any = None,
    prompt_builder: Any = None,
) -> EmailImprovementHandler:
    """
    Factory function para obter instância do EmailImprovementHandler.
    
    Args:
        email_draft_service: Serviço de drafts (opcional, será carregado se não fornecido)
        ai_service: Serviço de IA (opcional)
        prompt_builder: Builder de prompts (opcional)
    
    Returns:
        Instância configurada do EmailImprovementHandler
    """
    return EmailImprovementHandler(
        email_draft_service=email_draft_service,
        ai_service=ai_service,
        prompt_builder=prompt_builder
    )
