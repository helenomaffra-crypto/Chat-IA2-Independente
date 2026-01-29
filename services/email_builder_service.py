"""
Serviço para construir emails de classificação NCM e alíquotas.

Este serviço centraliza a lógica de montagem de emails técnicos com informações
de NCM, alíquotas, NESH e justificativa de classificação fiscal.
"""
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailBuilderService:
    """Serviço para construir emails de classificação NCM e alíquotas."""
    
    def __init__(self):
        """Inicializa o serviço."""
        pass
    
    def montar_email_classificacao_ncm(
        self,
        destinatario: str,
        contexto_ncm: Dict[str, Any],
        texto_pedido_usuario: Optional[str] = None,
        nome_usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Monta email completo de classificação NCM com alíquotas e justificativa.
        
        Args:
            destinatario: Email do destinatário
            contexto_ncm: Dict com informações de NCM:
                - ncm: str (ex: "90041000")
                - descricao: str (ex: "Óculos de sol")
                - confianca: float (ex: 0.6)
                - nota_nesh: str (texto completo da NESH)
                - aliquotas: dict com:
                    - ii: float (ex: 18.0)
                    - ipi: float (ex: 9.75)
                    - pis: float (ex: 2.1)
                    - cofins: float (ex: 9.65)
                    - icms: str (ex: "TN")
                - unidade_medida: str (ex: "Unidade")
                - fonte: str (ex: "TECwin")
                - capitulo: Optional[str] (ex: "90")
                - posicao: Optional[str] (ex: "90.04")
                - subposicao: Optional[str] (ex: "9004.10")
                - item: Optional[str] (ex: "9004.10.00")
                - explicacao: Optional[str] (explicação da IA sobre a classificação)
            texto_pedido_usuario: Texto original do pedido do usuário (opcional)
            nome_usuario: Nome do usuário para personalização (opcional)
        
        Returns:
            Dict com:
                - assunto: str
                - conteudo: str (corpo do email formatado)
                - sucesso: bool
                - erro: Optional[str]
        """
        try:
            # Validar contexto mínimo
            if not contexto_ncm.get('ncm'):
                return {
                    'sucesso': False,
                    'erro': 'NCM não encontrado no contexto',
                    'assunto': 'Classificação Fiscal',
                    'conteudo': 'NCM não encontrado no contexto da conversa.'
                }
            
            ncm = contexto_ncm.get('ncm', '')
            descricao = contexto_ncm.get('descricao', 'Produto não especificado')
            confianca = contexto_ncm.get('confianca', 0.0)
            
            # ✅ CRÍTICO: Converter nota_nesh de dict para string se necessário
            nota_nesh_raw = contexto_ncm.get('nota_nesh', '')
            nota_nesh = ''
            if nota_nesh_raw:
                if isinstance(nota_nesh_raw, dict):
                    # Se for dict, extrair texto completo formatado
                    titulo = nota_nesh_raw.get('position_title', '')
                    texto = nota_nesh_raw.get('text', '')
                    posicao_code = nota_nesh_raw.get('position_code', '')
                    if titulo and texto:
                        nota_nesh = f"**Posição {posicao_code}:** {titulo}\n\n{texto}" if posicao_code else f"{titulo}\n\n{texto}"
                    elif titulo:
                        nota_nesh = f"**Posição {posicao_code}:** {titulo}" if posicao_code else titulo
                    elif texto:
                        nota_nesh = texto
                else:
                    nota_nesh = str(nota_nesh_raw)
            
            aliquotas = contexto_ncm.get('aliquotas', {})
            unidade_medida = contexto_ncm.get('unidade_medida', 'N/A')
            fonte = contexto_ncm.get('fonte', 'Sistema')
            capitulo = contexto_ncm.get('capitulo')
            posicao = contexto_ncm.get('posicao')
            subposicao = contexto_ncm.get('subposicao')
            item = contexto_ncm.get('item')
            explicacao = contexto_ncm.get('explicacao', '')
            
            # Formatar NCM com pontos (ex: 9004.10.00)
            ncm_formatado = self._formatar_ncm(ncm)
            
            # Construir assunto
            assunto = f"Classificação NCM {ncm_formatado} – {descricao} e alíquotas de importação"
            
            # Construir corpo do email
            conteudo = self._construir_corpo_email(
                destinatario=destinatario,
                ncm=ncm,
                ncm_formatado=ncm_formatado,
                descricao=descricao,
                confianca=confianca,
                nota_nesh=nota_nesh,
                aliquotas=aliquotas,
                unidade_medida=unidade_medida,
                fonte=fonte,
                capitulo=capitulo,
                posicao=posicao,
                subposicao=subposicao,
                item=item,
                explicacao=explicacao,
                nome_usuario=nome_usuario
            )
            
            return {
                'sucesso': True,
                'assunto': assunto,
                'conteudo': conteudo,
                'erro': None
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao montar email de classificação NCM: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'assunto': 'Classificação Fiscal',
                'conteudo': f'Erro ao montar email: {str(e)}'
            }
    
    def _formatar_ncm(self, ncm: str) -> str:
        """
        Formata NCM com pontos (ex: 90041000 -> 9004.10.00).
        
        Args:
            ncm: NCM sem formatação (ex: "90041000")
        
        Returns:
            NCM formatado (ex: "9004.10.00")
        """
        ncm_limpo = re.sub(r'[^\d]', '', ncm)
        if len(ncm_limpo) == 8:
            return f"{ncm_limpo[:4]}.{ncm_limpo[4:6]}.{ncm_limpo[6:8]}"
        elif len(ncm_limpo) == 6:
            return f"{ncm_limpo[:4]}.{ncm_limpo[4:6]}"
        else:
            return ncm
    
    def _construir_corpo_email(
        self,
        destinatario: str,
        ncm: str,
        ncm_formatado: str,
        descricao: str,
        confianca: float,
        nota_nesh: str,
        aliquotas: Dict[str, Any],
        unidade_medida: str,
        fonte: str,
        capitulo: Optional[str],
        posicao: Optional[str],
        subposicao: Optional[str],
        item: Optional[str],
        explicacao: Optional[str],
        nome_usuario: Optional[str]
    ) -> str:
        """
        Constrói o corpo completo do email formatado.
        
        Returns:
            String com o corpo do email formatado
        """
        def _nome_para_saudacao(nome: Optional[str]) -> Optional[str]:
            """
            Sanitiza/valida nome para saudação.
            IMPORTANTE: `nome_usuario` pode vir de tool call / LLM e não deve ser confiado cegamente.
            """
            if not nome:
                return None
            n = str(nome).strip()
            if not n:
                return None
            # Rejeitar padrões claramente errados / instruções acopladas
            n_lower = n.lower()
            tokens_proibidos = [
                "email",
                "e-mail",
                "mandar",
                "manda",
                "enviar",
                "envia",
                "confirme",
                "confirmar",
                "pode",
                "pode enviar",
                "pode mandar",
            ]
            if any(t in n_lower for t in tokens_proibidos):
                return None
            # Não pode ser um endereço de email
            if "@" in n or "." in n:
                # (ex: helenomaffra@gmail.com / helenomaffra)
                # pontuação/abreviações tendem a ser ruins para saudação; preferir fallback do email.
                return None
            # Limitar tamanho para evitar frases inteiras
            if len(n) > 25:
                return None
            # Limitar quantidade de palavras
            if len(n.split()) > 2:
                return None
            return n

        # Extrair nome do destinatário do email (antes do @)
        nome_destinatario = destinatario.split('@')[0].split('.')[0].capitalize()
        nome_sanitizado = _nome_para_saudacao(nome_usuario)
        if nome_sanitizado:
            nome_destinatario = nome_sanitizado
        
        # Saudação
        corpo = f"Olá, {nome_destinatario},\n\n"
        corpo += "Segue abaixo a classificação fiscal e as alíquotas do produto:\n\n"
        
        # NCM e descrição
        corpo += f"• **NCM:** {ncm_formatado} – {descricao}\n"
        if confianca > 0:
            corpo += f"• **Confiança:** {confianca * 100:.0f}%\n"
        corpo += "\n"
        
        # Estrutura da classificação (Capítulo, Posição, Subposição, Item)
        if capitulo or posicao or subposicao or item:
            corpo += "**Estrutura da Classificação:**\n"
            if capitulo:
                # Buscar descrição do capítulo se disponível
                descricao_capitulo = self._obter_descricao_capitulo(capitulo)
                if descricao_capitulo:
                    corpo += f"• **Capítulo {capitulo}** – {descricao_capitulo}\n"
                else:
                    corpo += f"• **Capítulo {capitulo}**\n"
            if posicao:
                corpo += f"• **Posição {posicao}**\n"
            if subposicao:
                corpo += f"• **Subposição {subposicao}**\n"
            if item:
                corpo += f"• **Item {item}**\n"
            corpo += "\n"
        
        # Nota Explicativa NESH (se disponível)
        if nota_nesh:
            corpo += "**Nota Explicativa NESH:**\n"
            # Truncar NESH se muito longa (manter primeiras 500 palavras)
            palavras_nesh = nota_nesh.split()
            if len(palavras_nesh) > 500:
                nota_nesh_truncada = ' '.join(palavras_nesh[:500]) + "..."
                corpo += f"{nota_nesh_truncada}\n\n"
            else:
                corpo += f"{nota_nesh}\n\n"
        
        # Alíquotas
        corpo += "**Alíquotas de Importação**"
        if fonte:
            corpo += f" (segundo {fonte})"
        corpo += ":\n"
        
        if aliquotas:
            if aliquotas.get('ii') is not None:
                corpo += f"• **II (Imposto de Importação):** {aliquotas['ii']:.2f}%\n"
            if aliquotas.get('ipi') is not None:
                corpo += f"• **IPI (Imposto sobre Produtos Industrializados):** {aliquotas['ipi']:.2f}%\n"
            if aliquotas.get('pis') is not None:
                corpo += f"• **PIS/PASEP-Importação:** {aliquotas['pis']:.2f}%\n"
            if aliquotas.get('cofins') is not None:
                corpo += f"• **COFINS-Importação:** {aliquotas['cofins']:.2f}%\n"
            if aliquotas.get('icms'):
                icms_str = aliquotas['icms']
                if icms_str.upper() == 'TN':
                    corpo += f"• **ICMS:** TN (verificar alíquota estadual aplicável)\n"
                else:
                    corpo += f"• **ICMS:** {icms_str}\n"
        else:
            corpo += "• Alíquotas não disponíveis no momento.\n"
        
        corpo += "\n"
        
        # Unidade de Medida
        if unidade_medida and unidade_medida != 'N/A':
            corpo += f"**Unidade de Medida:** {unidade_medida}\n\n"
        
        # Justificativa da Classificação
        corpo += "**Justificativa da Classificação:**\n"
        if explicacao:
            corpo += f"{explicacao}\n\n"
        else:
            # Gerar justificativa básica se não tiver
            corpo += f"O produto foi classificado na NCM {ncm_formatado} por se tratar de {descricao.lower()}, "
            if subposicao:
                corpo += f"enquadrando-se na subposição {subposicao} ("
                if posicao:
                    corpo += f"posição {posicao}"
                corpo += "), conforme texto da NCM e estrutura do "
                if capitulo:
                    corpo += f"Capítulo {capitulo}"
                else:
                    corpo += "NCM"
                corpo += ". "
            corpo += "Caso o produto seja de outro tipo específico ou tenha características diferentes, a NCM pode variar e seria necessário reavaliar a descrição técnica e o uso.\n\n"
        
        # Assinatura
        corpo += "Atenciosamente,\n"
        corpo += "mAIke – Assistente de COMEX\n"
        corpo += "Make Consultores"
        
        return corpo
    
    def _obter_descricao_capitulo(self, capitulo: str) -> Optional[str]:
        """
        Obtém descrição do capítulo da NCM (se disponível no cache).
        
        Args:
            capitulo: Número do capítulo (ex: "90")
        
        Returns:
            Descrição do capítulo ou None
        """
        try:
            # Tentar buscar do cache de NCMs
            from db_manager import get_classif_ncm_completo
            # Buscar um NCM do capítulo para obter a descrição
            # Exemplo: capítulo 90 -> buscar 90000000
            ncm_capitulo = f"{capitulo}000000"
            info = get_classif_ncm_completo(ncm_capitulo)
            if info and info.get('descricao'):
                return info.get('descricao')
        except Exception as e:
            logger.debug(f'Erro ao buscar descrição do capítulo {capitulo}: {e}')
        
        return None
    
    def extrair_contexto_ncm_do_historico(
        self,
        historico: list,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extrai contexto de NCM/alíquotas do histórico de conversas.
        
        Args:
            historico: Lista de mensagens do histórico
            session_id: ID da sessão (opcional, para buscar do banco se histórico não tiver)
        
        Returns:
            Dict com contexto de NCM ou None se não encontrar
        """
        try:
            # 1. Tentar buscar do contexto persistente primeiro
            if session_id:
                from services.context_service import buscar_contexto_sessao
                contextos = buscar_contexto_sessao(session_id, tipo_contexto='ultima_classificacao_ncm')
                if contextos and len(contextos) > 0:
                    contexto = contextos[0]
                    dados = contexto.get('dados', {})
                    if dados and dados.get('ncm'):
                        logger.info(f"✅ Contexto de NCM encontrado no contexto persistente: {dados.get('ncm')}")
                        return dados
            
            # 2. Tentar extrair do histórico
            if historico and len(historico) > 0:
                # Procurar nas últimas 10 respostas
                for i in range(len(historico) - 1, max(-1, len(historico) - 11), -1):
                    resposta = historico[i].get('resposta', '')
                    if not resposta:
                        continue
                    
                    # Verificar se tem informações de NCM
                    tem_ncm = (
                        'NCM' in resposta or 
                        'NESH' in resposta or 
                        'Alíquotas' in resposta or 
                        'alíquotas' in resposta or
                        'TECwin' in resposta
                    )
                    
                    if tem_ncm:
                        contexto_extraido = self._extrair_ncm_da_resposta(resposta)
                        if contexto_extraido and contexto_extraido.get('ncm'):
                            logger.info(f"✅ Contexto de NCM extraído do histórico (índice {i}): {contexto_extraido.get('ncm')}")
                            return contexto_extraido
            
            # 3. Tentar buscar do banco de dados (última resposta da sessão)
            if session_id:
                try:
                    from db_manager import get_db_connection
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT resposta FROM conversas_chat 
                        WHERE session_id = ? 
                        AND (resposta LIKE '%NCM%' OR resposta LIKE '%TECwin%' OR resposta LIKE '%Alíquotas%')
                        ORDER BY criado_em DESC 
                        LIMIT 5
                    ''', (session_id,))
                    rows = cursor.fetchall()
                    conn.close()
                    
                    for row in rows:
                        resposta = row[0] if row else ''
                        if resposta:
                            contexto_extraido = self._extrair_ncm_da_resposta(resposta)
                            if contexto_extraido and contexto_extraido.get('ncm'):
                                logger.info(f"✅ Contexto de NCM extraído do banco: {contexto_extraido.get('ncm')}")
                                return contexto_extraido
                except Exception as e:
                    logger.debug(f'Erro ao buscar contexto NCM do banco: {e}')
            
            logger.warning("⚠️ Nenhum contexto de NCM encontrado no histórico")
            return None
            
        except Exception as e:
            logger.error(f'❌ Erro ao extrair contexto NCM do histórico: {e}', exc_info=True)
            return None
    
    def _extrair_ncm_da_resposta(self, resposta: str) -> Optional[Dict[str, Any]]:
        """
        Extrai informações de NCM de uma resposta formatada.
        
        Args:
            resposta: Texto da resposta que contém informações de NCM
        
        Returns:
            Dict com contexto de NCM ou None
        """
        try:
            contexto = {}
            
            # Extrair NCM
            padrao_ncm = r'NCM\s+(?:Sugerido|sugerido)?:?\s*(\d{4,8})'
            match_ncm = re.search(padrao_ncm, resposta, re.IGNORECASE)
            if match_ncm:
                contexto['ncm'] = match_ncm.group(1)
            
            # Extrair descrição
            padrao_desc = r'Descrição:?\s*([^\n]+)'
            match_desc = re.search(padrao_desc, resposta, re.IGNORECASE)
            if match_desc:
                contexto['descricao'] = match_desc.group(1).strip()
            
            # Extrair confiança
            padrao_conf = r'Confiança:?\s*([\d.]+)%?'
            match_conf = re.search(padrao_conf, resposta, re.IGNORECASE)
            if match_conf:
                try:
                    contexto['confianca'] = float(match_conf.group(1)) / 100.0
                except:
                    pass
            
            # Extrair alíquotas
            aliquotas = {}
            padrao_ii = r'II\s*\([^)]*\):?\s*([\d.]+)%?'
            match_ii = re.search(padrao_ii, resposta, re.IGNORECASE)
            if match_ii:
                try:
                    aliquotas['ii'] = float(match_ii.group(1))
                except:
                    pass
            
            padrao_ipi = r'IPI\s*\([^)]*\):?\s*([\d.]+)%?'
            match_ipi = re.search(padrao_ipi, resposta, re.IGNORECASE)
            if match_ipi:
                try:
                    aliquotas['ipi'] = float(match_ipi.group(1))
                except:
                    pass
            
            padrao_pis = r'PIS[^:]*:?\s*([\d.]+)%?'
            match_pis = re.search(padrao_pis, resposta, re.IGNORECASE)
            if match_pis:
                try:
                    aliquotas['pis'] = float(match_pis.group(1))
                except:
                    pass
            
            padrao_cofins = r'COFINS[^:]*:?\s*([\d.]+)%?'
            match_cofins = re.search(padrao_cofins, resposta, re.IGNORECASE)
            if match_cofins:
                try:
                    aliquotas['cofins'] = float(match_cofins.group(1))
                except:
                    pass
            
            padrao_icms = r'ICMS:?\s*([^\n]+)'
            match_icms = re.search(padrao_icms, resposta, re.IGNORECASE)
            if match_icms:
                aliquotas['icms'] = match_icms.group(1).strip()
            
            if aliquotas:
                contexto['aliquotas'] = aliquotas
            
            # Extrair unidade de medida
            padrao_unidade = r'Unidade\s+de\s+Medida:?\s*([^\n]+)'
            match_unidade = re.search(padrao_unidade, resposta, re.IGNORECASE)
            if match_unidade:
                contexto['unidade_medida'] = match_unidade.group(1).strip()
            
            # Extrair fonte
            padrao_fonte = r'Fonte:?\s*([^\n]+)'
            match_fonte = re.search(padrao_fonte, resposta, re.IGNORECASE)
            if match_fonte:
                contexto['fonte'] = match_fonte.group(1).strip()
            
            # Extrair NESH (procurar por "Nota Explicativa" ou "NESH")
            padrao_nesh = r'(?:Nota\s+Explicativa|NESH)[^:]*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\n\*\*|$)'
            match_nesh = re.search(padrao_nesh, resposta, re.IGNORECASE | re.DOTALL)
            if match_nesh:
                contexto['nota_nesh'] = match_nesh.group(1).strip()
            
            # Extrair explicação
            padrao_explicacao = r'Explicação[^:]*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\n\*\*|$)'
            match_explicacao = re.search(padrao_explicacao, resposta, re.IGNORECASE | re.DOTALL)
            if match_explicacao:
                contexto['explicacao'] = match_explicacao.group(1).strip()
            
            # Extrair estrutura (Capítulo, Posição, Subposição)
            padrao_capitulo = r'Capítulo\s+(\d+)'
            match_capitulo = re.search(padrao_capitulo, resposta, re.IGNORECASE)
            if match_capitulo:
                contexto['capitulo'] = match_capitulo.group(1)
            
            padrao_posicao = r'Posição\s+(\d+\.\d+)'
            match_posicao = re.search(padrao_posicao, resposta, re.IGNORECASE)
            if match_posicao:
                contexto['posicao'] = match_posicao.group(1)
            
            padrao_subposicao = r'Subposição\s+(\d+\.\d+)'
            match_subposicao = re.search(padrao_subposicao, resposta, re.IGNORECASE)
            if match_subposicao:
                contexto['subposicao'] = match_subposicao.group(1)
            
            return contexto if contexto.get('ncm') else None
            
        except Exception as e:
            logger.error(f'❌ Erro ao extrair NCM da resposta: {e}', exc_info=True)
            return None
    
    def montar_email_relatorio_diario(
        self,
        destinatario: str,
        relatorio_texto: str,
        data_referencia: Optional[str] = None,
        nome_usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Monta email com o relatório diário "O QUE TEMOS PRA HOJE".
        
        Args:
            destinatario: Email do destinatário
            relatorio_texto: Texto completo do relatório (já formatado)
            data_referencia: Data de referência do relatório (ex: "2025-12-19")
            nome_usuario: Nome do usuário para personalização (opcional)
        
        Returns:
            Dict com:
                - assunto: str
                - conteudo: str (corpo do email formatado)
                - sucesso: bool
                - erro: Optional[str]
        """
        try:
            from datetime import datetime
            
            # Extrair data do relatório se não fornecida
            if not data_referencia:
                # Tentar extrair do texto do relatório (ex: "O QUE TEMOS PRA HOJE - 19/12/2025")
                import re
                padrao_data = r'O QUE TEMOS PRA HOJE[^\d]*(\d{2}/\d{2}/\d{4})'
                match_data = re.search(padrao_data, relatorio_texto, re.IGNORECASE)
                if match_data:
                    data_str = match_data.group(1)
                    try:
                        # Converter DD/MM/YYYY para YYYY-MM-DD
                        data_obj = datetime.strptime(data_str, '%d/%m/%Y')
                        data_referencia = data_obj.strftime('%Y-%m-%d')
                    except:
                        data_referencia = datetime.now().strftime('%Y-%m-%d')
                else:
                    data_referencia = datetime.now().strftime('%Y-%m-%d')
            
            # Formatar data para exibição (DD/MM/YYYY)
            try:
                data_obj = datetime.strptime(data_referencia, '%Y-%m-%d')
                data_formatada = data_obj.strftime('%d/%m/%Y')
            except:
                data_formatada = datetime.now().strftime('%d/%m/%Y')
            
            # Construir assunto
            assunto = f"Resumo diário – O que temos pra hoje - {data_formatada}"
            
            # Construir corpo do email
            conteudo = self._construir_corpo_email_relatorio_diario(
                destinatario=destinatario,
                relatorio_texto=relatorio_texto,
                data_formatada=data_formatada,
                nome_usuario=nome_usuario
            )
            
            return {
                'sucesso': True,
                'assunto': assunto,
                'conteudo': conteudo,
                'erro': None
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao montar email de relatório diário: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'assunto': 'Resumo diário',
                'conteudo': f'Erro ao montar email: {str(e)}'
            }
    
    def _construir_corpo_email_relatorio_diario(
        self,
        destinatario: str,
        relatorio_texto: str,
        data_formatada: str,
        nome_usuario: Optional[str]
    ) -> str:
        """
        Constrói o corpo completo do email de relatório diário.
        
        Returns:
            String com o corpo do email formatado
        """
        # Extrair nome do destinatário do email (antes do @)
        nome_destinatario = destinatario.split('@')[0].split('.')[0].capitalize()
        if nome_usuario:
            nome_destinatario = nome_usuario
        
        # Saudação
        corpo = f"Olá, {nome_destinatario},\n\n"
        
        # Frase introdutória
        corpo += f"Segue o resumo diário de processos de importação para hoje ({data_formatada}):\n\n"
        
        # Relatório completo (já formatado)
        corpo += relatorio_texto
        corpo += "\n\n"
        
        # Encerramento opcional
        corpo += "Qualquer dúvida, estamos à disposição.\n\n"
        
        # Assinatura
        corpo += "Atenciosamente,\n"
        corpo += "mAIke – Assistente de COMEX\n"
        corpo += "Make Consultores"
        
        return corpo
    
    def montar_email_livre(
        self,
        destinatario: str,
        texto_mensagem: str,
        nome_usuario: Optional[str] = None,
        assunto_personalizado: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Monta email livre com texto ditado pelo usuário.
        
        Args:
            destinatario: Email do destinatário
            texto_mensagem: Texto que o usuário quer enviar
            nome_usuario: Nome do usuário para personalização (opcional)
            assunto_personalizado: Assunto personalizado (opcional, se não fornecido usa padrão)
        
        Returns:
            Dict com:
                - assunto: str
                - conteudo: str (corpo do email formatado)
                - sucesso: bool
                - erro: Optional[str]
        """
        try:
            # Construir assunto
            if assunto_personalizado:
                assunto = assunto_personalizado
            else:
                if nome_usuario:
                    assunto = f"Mensagem de {nome_usuario} via mAIke"
                else:
                    # Tentar extrair nome do email do destinatário
                    nome_destinatario = destinatario.split('@')[0].split('.')[0].capitalize()
                    assunto = f"Mensagem via mAIke"
            
            # Construir corpo do email
            conteudo = self._construir_corpo_email_livre(
                destinatario=destinatario,
                texto_mensagem=texto_mensagem,
                nome_usuario=nome_usuario
            )
            
            return {
                'sucesso': True,
                'assunto': assunto,
                'conteudo': conteudo,
                'erro': None
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao montar email livre: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'assunto': 'Mensagem',
                'conteudo': f'Erro ao montar email: {str(e)}'
            }
    
    def _construir_corpo_email_livre(
        self,
        destinatario: str,
        texto_mensagem: str,
        nome_usuario: Optional[str]
    ) -> str:
        """
        Constrói o corpo completo do email livre.
        
        ✅ NOVO (09/01/2026): Detecta instruções de assinatura ("assine [nome]")
        e remove do corpo do email, usando o nome especificado na assinatura.
        
        Returns:
            String com o corpo do email formatado
        """
        # ✅ NOVO: Detectar e extrair assinatura solicitada ("assine [nome]")
        assinatura_solicitada = None
        texto_limpo = texto_mensagem.strip()
        
        # Padrões: "assine [nome]", "assinar como [nome]", "assinar [nome]"
        padroes_assinatura = [
            r'assine\s+(?:como\s+)?([A-Za-zÀ-ÿ\s]+?)(?:\.|$|,|\n)',
            r'assinar\s+(?:como\s+)?([A-Za-zÀ-ÿ\s]+?)(?:\.|$|,|\n)',
            r'assinar\s+([A-Za-zÀ-ÿ\s]+?)(?:\.|$|,|\n)',
        ]
        
        for padrao in padroes_assinatura:
            match = re.search(padrao, texto_limpo, re.IGNORECASE)
            if match:
                assinatura_solicitada = match.group(1).strip()
                # Remover a instrução de assinatura do texto
                texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE).strip()
                logger.info(f'✅ [EMAIL_BUILDER] Assinatura detectada: "{assinatura_solicitada}"')
                break
        
        # Saudação simples
        corpo = "Olá,\n\n"
        
        # Texto da mensagem (após remover instrução de assinatura)
        texto_formatado = texto_limpo.strip()
        # Se o texto não termina com pontuação, adicionar ponto
        if texto_formatado and texto_formatado[-1] not in ['.', '!', '?']:
            texto_formatado += '.'
        
        corpo += texto_formatado
        corpo += "\n\n"
        
        # ✅ Assinatura: usar nome solicitado se detectado, senão usar padrão
        if assinatura_solicitada:
            corpo += f"Atenciosamente,\n{assinatura_solicitada}"
        else:
            corpo += "Enviado por mAIke – Assistente de COMEX (Make Consultores)."
        
        return corpo
    
    def montar_email_relatorio(
        self,
        relatorio: Any,  # RelatorioGerado (usar Any para evitar import circular)
        destinatario: str,
        nome_usuario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Monta email genérico com qualquer relatório gerado pela mAIke.
        
        Args:
            relatorio: Instância de RelatorioGerado (do report_service)
            destinatario: Email do destinatário
            nome_usuario: Nome do usuário para personalização (opcional)
        
        Returns:
            Dict com:
                - assunto: str
                - conteudo: str (corpo do email formatado)
                - sucesso: bool
                - erro: Optional[str]
        """
        try:
            # Gerar assunto baseado no tipo de relatório
            assunto = self._gerar_assunto_relatorio(relatorio)
            
            # Construir corpo do email
            conteudo = self._construir_corpo_email_relatorio(
                relatorio=relatorio,
                destinatario=destinatario,
                nome_usuario=nome_usuario
            )
            
            return {
                'sucesso': True,
                'assunto': assunto,
                'conteudo': conteudo,
                'erro': None
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao montar email de relatório: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'assunto': 'Relatório',
                'conteudo': f'Erro ao montar email: {str(e)}'
            }
    
    def _gerar_assunto_relatorio(self, relatorio: Any) -> str:  # RelatorioGerado
        """
        Gera assunto do email baseado no tipo de relatório.
        
        Args:
            relatorio: Instância de RelatorioGerado
        
        Returns:
            Assunto formatado
        """
        tipo = relatorio.tipo_relatorio
        categoria = relatorio.categoria
        filtros = relatorio.filtros or {}
        
        # Mapeamento de tipos para templates de assunto
        templates_assunto = {
            'o_que_tem_hoje': lambda r: f"Resumo diário – O que temos pra hoje{f' - {r.categoria}' if r.categoria else ''} - {self._extrair_data_formatada(r)}",
            'como_estao_categoria': lambda r: f"Status geral – {r.categoria or 'Processos'}",
            'fechamento_dia': lambda r: f"Fechamento do dia{f' - {r.categoria}' if r.categoria else ''} - {self._extrair_data_formatada(r)}",
            'relatorio_averbacoes': lambda r: f"Relatório de averbações{f' - {r.categoria}' if r.categoria else ''} - {self._extrair_periodo(r)}",
        }
        
        # Usar template específico ou genérico
        gerador = templates_assunto.get(tipo)
        if gerador:
            return gerador(relatorio)
        else:
            # Template genérico
            return f"Relatório - {tipo.replace('_', ' ').title()}{f' - {categoria}' if categoria else ''}"
    
    def _extrair_data_formatada(self, relatorio: Any) -> str:  # RelatorioGerado
        """Extrai e formata data do relatório (DD/MM/YYYY)."""
        try:
            filtros = relatorio.filtros or {}
            data_ref = filtros.get('data_ref')
            
            if data_ref:
                # Tentar parsear várias formatos
                if isinstance(data_ref, str):
                    # Remover hora se houver
                    data_str = data_ref.split('T')[0].split(' ')[0]
                    try:
                        data_obj = datetime.strptime(data_str, '%Y-%m-%d')
                        return data_obj.strftime('%d/%m/%Y')
                    except:
                        pass
            
            # Fallback: data atual
            return datetime.now().strftime('%d/%m/%Y')
        except:
            return datetime.now().strftime('%d/%m/%Y')
    
    def _extrair_periodo(self, relatorio: Any) -> str:  # RelatorioGerado
        """Extrai período do relatório de averbações."""
        try:
            filtros = relatorio.filtros or {}
            mes = filtros.get('mes')
            ano = filtros.get('ano')
            
            if mes and ano:
                return f"{mes}/{ano}"
            elif mes:
                return mes
            else:
                return datetime.now().strftime('%m/%Y')
        except:
            return datetime.now().strftime('%m/%Y')
    
    def _construir_corpo_email_relatorio(
        self,
        relatorio: Any,  # RelatorioGerado
        destinatario: str,
        nome_usuario: Optional[str] = None
    ) -> str:
        """
        Constrói o corpo completo do email de relatório.
        
        Args:
            relatorio: Instância de RelatorioGerado
            destinatario: Email do destinatário
            nome_usuario: Nome do usuário (opcional)
        
        Returns:
            String com o corpo do email formatado
        """
        # Extrair nome do destinatário do email (antes do @)
        nome_destinatario = destinatario.split('@')[0].split('.')[0].capitalize()
        if nome_usuario:
            nome_destinatario = nome_usuario
        
        # Saudação
        corpo = f"Olá, {nome_destinatario},\n\n"
        
        # Frase introdutória baseada no tipo
        corpo += self._gerar_introducao_relatorio(relatorio)
        corpo += "\n\n"
        
        # Relatório completo (já formatado)
        # Limpar emojis excessivos se necessário (manter estrutura mas tornar mais profissional)
        texto_relatorio = self._limpar_texto_relatorio(relatorio.texto_chat)
        corpo += texto_relatorio
        corpo += "\n\n"
        
        # Encerramento
        corpo += "Qualquer dúvida, estamos à disposição.\n\n"
        
        # Assinatura
        corpo += "Atenciosamente,\n"
        corpo += "mAIke – Assistente de COMEX\n"
        corpo += "Make Consultores"
        
        return corpo
    
    def _gerar_introducao_relatorio(self, relatorio: Any) -> str:  # RelatorioGerado
        """Gera frase introdutória baseada no tipo de relatório."""
        tipo = relatorio.tipo_relatorio
        categoria = relatorio.categoria
        data_formatada = self._extrair_data_formatada(relatorio)
        
        introducoes = {
            'o_que_tem_hoje': f"Segue o resumo diário de processos de importação para hoje ({data_formatada})" + (f" - categoria {categoria}" if categoria else "") + ":",
            'como_estao_categoria': f"Segue o status geral dos processos {categoria or 'solicitados'}:",
            'fechamento_dia': f"Segue o fechamento do dia ({data_formatada})" + (f" - categoria {categoria}" if categoria else "") + ":",
            'relatorio_averbacoes': f"Segue o relatório de averbações" + (f" - categoria {categoria}" if categoria else "") + f" - período {self._extrair_periodo(relatorio)}:",
        }
        
        return introducoes.get(tipo, f"Segue o relatório solicitado:")
    
    def _limpar_texto_relatorio(self, texto: str) -> str:
        """
        Limpa o texto do relatório para formato de email.
        
        Remove emojis excessivos mas mantém estrutura e formatação.
        """
        # Por enquanto, manter o texto como está (já está bem formatado)
        # Se necessário no futuro, pode-se remover emojis específicos ou ajustar formatação
        return texto

