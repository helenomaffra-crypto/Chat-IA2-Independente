"""
Serviço para gerenciar relatórios gerados pela mAIke.

Centraliza a lógica de salvamento, recuperação e formatação de relatórios
para permitir envio por email posteriormente.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict, fields

logger = logging.getLogger(__name__)


@dataclass
class RelatorioGerado:
    """
    DTO para representar um relatório gerado pela mAIke.
    
    Facilita serialização para JSON e recuperação posterior para envio por email.
    """
    tipo_relatorio: str  # Ex: "o_que_tem_hoje", "como_estao_categoria", "fechamento_dia", "relatorio_averbacoes"
    categoria: Optional[str] = None  # Ex: "MV5", "ALH", "VDM"
    texto_chat: str = ""  # Texto exatamente como foi enviado para o usuário
    filtros: Optional[Dict[str, Any]] = None  # Ex: {"data_ref": "2025-12-19", "modal": "Marítimo"}
    meta_json: Optional[Dict[str, Any]] = None  # Metadados extras: contagens, totais, etc.
    criado_em: Optional[str] = None  # Timestamp ISO
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dict (serializável para JSON)."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RelatorioGerado':
        """Cria instância a partir de dict (deserialização)."""
        # ✅ Robustez: ignorar chaves desconhecidas (evita quebrar ao ler contextos legados/heterogêneos)
        allowed = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in (data or {}).items() if k in allowed}
        return cls(**filtered)
    
    def to_json(self) -> str:
        """Serializa para JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RelatorioGerado':
        """Deserializa de JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def gerar_chave_contexto(self) -> str:
        """
        Gera chave única para salvar no contexto.
        
        Formato: {tipo_relatorio}_{categoria}_{data}
        Ex: "o_que_tem_hoje_MV5_2025-12-19"
        """
        partes = [self.tipo_relatorio]
        if self.categoria:
            partes.append(self.categoria)
        if self.filtros and self.filtros.get('data_ref'):
            data_ref = self.filtros['data_ref']
            # Normalizar data para YYYY-MM-DD
            if isinstance(data_ref, str):
                partes.append(data_ref.split('T')[0])  # Remove hora se houver
        else:
            # Usar data atual se não tiver
            partes.append(datetime.now().strftime('%Y-%m-%d'))
        
        return '_'.join(partes)


def salvar_ultimo_relatorio(
    session_id: str,
    relatorio: RelatorioGerado
) -> bool:
    """
    Salva o último relatório gerado no contexto da sessão.
    
    ✅ NOVO (12/01/2026): Também salva como "active_report_id" automaticamente.
    Isso permite que follow-ups usem o relatório ativo sem mencionar IDs explicitamente.
    
    Args:
        session_id: ID da sessão
        relatorio: Instância de RelatorioGerado
    
    Returns:
        True se salvou com sucesso
    """
    try:
        from services.context_service import salvar_contexto_sessao
        import re
        import json
        
        chave = relatorio.gerar_chave_contexto()
        
        # Garantir que criado_em está preenchido
        if not relatorio.criado_em:
            relatorio.criado_em = datetime.now().isoformat()
        
        # Serializar relatório para dados_json
        dados_json = relatorio.to_dict()
        
        sucesso = salvar_contexto_sessao(
            session_id=session_id,
            tipo_contexto='ultimo_relatorio',
            chave=chave,
            valor=relatorio.tipo_relatorio,  # Valor simples para lookup
            dados_adicionais=dados_json
        )
        
        # ✅ NOVO (12/01/2026): Extrair ID do JSON inline e salvar como active_report_id
        if sucesso and relatorio.texto_chat:
            try:
                match = re.search(r'\[REPORT_META:({.+?})\]', relatorio.texto_chat, re.DOTALL)
                if match:
                    meta_json = json.loads(match.group(1))
                    relatorio_id = meta_json.get('id')
                    if relatorio_id:
                        # ✅ CORREÇÃO B (14/01/2026): Salvar como active_report_id_<dominio>
                        # Domínios suportados:
                        # - processos (default)
                        # - financeiro (extratos/lançamentos bancários)
                        # - vendas (relatórios de vendas por NF / faturamento)
                        tipo_relatorio_lower = relatorio.tipo_relatorio.lower()
                        eh_relatorio_financeiro = any(
                            x in tipo_relatorio_lower for x in ['financeiro', 'banco', 'lançamento', 'extrato_bancario', 'extrato_banco']
                        ) and not any(x in tipo_relatorio_lower for x in ['extrato_ce', 'extrato_cct', 'extrato_di', 'extrato_duimp'])

                        eh_relatorio_vendas = any(
                            x in tipo_relatorio_lower for x in ['vendas', 'venda', 'vendas_nf', 'vendas_por_nf', 'nf']
                        )

                        if eh_relatorio_vendas and not eh_relatorio_financeiro:
                            tipo_contexto_ativo = 'active_report_id_vendas'
                            tipo_contexto_last_visible = 'last_visible_report_id_vendas'
                            dominio_label = 'vendas'
                        else:
                            tipo_contexto_ativo = 'active_report_id_financeiro' if eh_relatorio_financeiro else 'active_report_id_processos'
                            tipo_contexto_last_visible = 'last_visible_report_id_financeiro' if eh_relatorio_financeiro else 'last_visible_report_id_processos'
                            dominio_label = 'financeiro' if eh_relatorio_financeiro else 'processos'
                        
                        salvar_contexto_sessao(
                            session_id=session_id,
                            tipo_contexto=tipo_contexto_ativo,
                            chave='current',
                            valor=relatorio_id,
                            dados_adicionais={
                                'tipo_relatorio': relatorio.tipo_relatorio,
                                'criado_em': relatorio.criado_em,
                                'meta_json': meta_json
                            }
                        )
                        
                        # ✅ REFINAMENTO 1 (14/01/2026): Salvar last_visible_report_id por domínio (processos/financeiro)
                        salvar_contexto_sessao(
                            session_id=session_id,
                            tipo_contexto=tipo_contexto_last_visible,
                            chave='current',
                            valor=relatorio_id,
                            dados_adicionais={
                                'tipo_relatorio': relatorio.tipo_relatorio,
                                'criado_em': relatorio.criado_em,
                                'meta_json': meta_json,
                                'is_filtered': meta_json.get('filtrado', False)
                            }
                        )
                        
                        logger.info(f"✅ Active report ID atualizado: {relatorio_id} (tipo: {relatorio.tipo_relatorio}, domínio: {dominio_label})")
                        logger.info(f"✅ Last visible report ID salvo ({dominio_label}): {relatorio_id}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao extrair/salvar active_report_id: {e}")
        
        if sucesso:
            logger.info(f"✅ Último relatório salvo: {chave} (tipo: {relatorio.tipo_relatorio})")
        
        return sucesso
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar último relatório: {e}", exc_info=True)
        return False


def buscar_relatorio_por_id(
    session_id: str,
    relatorio_id: str
) -> Optional[RelatorioGerado]:
    """
    ✅ NOVO (12/01/2026): Busca um relatório específico por ID.
    
    O ID é extraído do JSON inline [REPORT_META:{"id":"rel_20260112_145026",...}]
    que está no texto_chat do relatório.
    
    Args:
        session_id: ID da sessão
        relatorio_id: ID do relatório (ex: "rel_20260112_145026")
    
    Returns:
        RelatorioGerado se encontrado, None caso contrário
    """
    try:
        from services.context_service import buscar_contexto_sessao
        import re
        
        # Buscar todos os relatórios da sessão
        contextos = buscar_contexto_sessao(
            session_id=session_id,
            tipo_contexto='ultimo_relatorio',
            chave=None  # Buscar todos
        )
        
        if not contextos or len(contextos) == 0:
            logger.debug(f"⚠️ Nenhum relatório encontrado para sessão {session_id}")
            return None
        
        # Procurar relatório com o ID no texto_chat (JSON inline)
        for contexto in contextos:
            dados = contexto.get('dados', {})
            if not dados:
                continue
            
            try:
                relatorio = RelatorioGerado.from_dict(dados)
                if relatorio.texto_chat:
                    # Procurar JSON inline no texto
                    match = re.search(r'\[REPORT_META:({.+?})\]', relatorio.texto_chat, re.DOTALL)
                    if match:
                        import json
                        meta_json = json.loads(match.group(1))
                        if meta_json.get('id') == relatorio_id:
                            logger.info(f"✅ Relatório encontrado por ID: {relatorio_id} (tipo: {relatorio.tipo_relatorio})")
                            return relatorio
            except Exception as e:
                logger.debug(f"⚠️ Erro ao processar relatório: {e}")
                continue
        
        logger.debug(f"⚠️ Relatório com ID {relatorio_id} não encontrado na sessão {session_id}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar relatório por ID: {e}", exc_info=True)
        return None


def obter_report_history(session_id: str, limite: int = 10) -> List[Dict[str, Any]]:
    """
    ✅ NOVO (12/01/2026): Obtém histórico dos últimos N relatórios gerados.
    
    Retorna lista de metadados (tipo, created_at, id) dos relatórios mais recentes.
    Usado para resolução inteligente de ambiguidade.
    
    Args:
        session_id: ID da sessão
        limite: Número máximo de relatórios a retornar (padrão: 10)
    
    Returns:
        Lista de dicts com: {'id': str, 'tipo': str, 'created_at': str, 'ttl_min': int}
    """
    try:
        from services.context_service import buscar_contexto_sessao
        import re
        import json
        
        contextos = buscar_contexto_sessao(
            session_id=session_id,
            tipo_contexto='ultimo_relatorio',
            chave=None  # Buscar todos
        )
        
        if not contextos or len(contextos) == 0:
            return []
        
        history = []
        for contexto in contextos[:limite]:  # Limitar aos N mais recentes
            dados = contexto.get('dados', {})
            if not dados:
                continue
            
            try:
                relatorio = RelatorioGerado.from_dict(dados)
                if relatorio.texto_chat:
                    # Extrair JSON inline
                    match = re.search(r'\[REPORT_META:({.+?})\]', relatorio.texto_chat, re.DOTALL)
                    if match:
                        meta_json = json.loads(match.group(1))
                        history.append({
                            'id': meta_json.get('id'),
                            'tipo': relatorio.tipo_relatorio,
                            'created_at': meta_json.get('created_at'),
                            'ttl_min': meta_json.get('ttl_min', 60),
                            'data': meta_json.get('data'),
                            'categoria': relatorio.categoria
                        })
            except Exception as e:
                logger.debug(f"⚠️ Erro ao processar relatório no histórico: {e}")
                continue
        
        # Ordenar por created_at (mais recente primeiro)
        history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return history
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter report_history: {e}", exc_info=True)
        return []


def obter_active_report_id(session_id: str, dominio: str = 'processos') -> Optional[str]:
    """
    ✅ ATUALIZADO (14/01/2026): Obtém o ID do relatório ativo por domínio.
    
    O active_report_id é atualizado automaticamente quando um novo relatório é gerado.
    Follow-ups (filtrar, melhorar, enviar email) usam este relatório por padrão.
    
    Args:
        session_id: ID da sessão
        dominio: 'processos' ou 'financeiro' (padrão: 'processos')
    
    Returns:
        ID do relatório ativo (ex: "rel_20260112_145026") ou None se não houver
    """
    try:
        from services.context_service import buscar_contexto_sessao
        
        # ✅ CORREÇÃO B: Usar tipo_contexto baseado no domínio
        if dominio == 'financeiro':
            tipo_contexto = 'active_report_id_financeiro'
        elif dominio == 'vendas':
            tipo_contexto = 'active_report_id_vendas'
        else:
            tipo_contexto = 'active_report_id_processos'
        
        contextos = buscar_contexto_sessao(
            session_id=session_id,
            tipo_contexto=tipo_contexto,
            chave='current'
        )
        
        if contextos and len(contextos) > 0:
            active_id = contextos[0].get('valor')
            logger.debug(f"✅ Active report ID encontrado ({dominio}): {active_id}")
            return active_id
        
        return None
    except Exception as e:
        logger.warning(f"⚠️ Erro ao obter active_report_id: {e}")
        return None


def obter_active_report_info(session_id: str, dominio: str = 'processos') -> Optional[Dict[str, Any]]:
    """
    ✅ NOVO (14/01/2026): Obtém metadados do relatório ativo por domínio.

    Útil para validações de staleness/TTL no ToolGateService sem precisar buscar o relatório inteiro.

    Args:
        session_id: ID da sessão
        dominio: 'processos' ou 'financeiro' (padrão: 'processos')

    Returns:
        Dict com:
        - id: str
        - tipo_relatorio: str (se disponível)
        - criado_em: str (timestamp ISO do relatório salvo)
        - meta_json: Dict (se disponível)
        ou None se não houver.
    """
    try:
        from services.context_service import buscar_contexto_sessao

        if dominio == 'financeiro':
            tipo_contexto = 'active_report_id_financeiro'
        elif dominio == 'vendas':
            tipo_contexto = 'active_report_id_vendas'
        else:
            tipo_contexto = 'active_report_id_processos'
        contextos = buscar_contexto_sessao(
            session_id=session_id,
            tipo_contexto=tipo_contexto,
            chave='current'
        )

        if contextos and len(contextos) > 0:
            contexto = contextos[0]
            # ✅ CORREÇÃO (20/01/2026): `contexto_service` normaliza JSON em `ctx['dados']` (não `dados_adicionais`)
            dados = (
                contexto.get('dados_adicionais')  # compat (se algum caller popular isso)
                or contexto.get('dados')          # padrão do ContextService
                or {}
            )
            return {
                'id': contexto.get('valor'),
                'tipo_relatorio': dados.get('tipo_relatorio'),
                'criado_em': dados.get('criado_em'),
                'meta_json': dados.get('meta_json'),
            }

        return None
    except Exception as e:
        logger.warning(f"⚠️ Erro ao obter active_report_info ({dominio}): {e}")
        return None


def obter_last_visible_report_id(session_id: str, dominio: str = 'processos') -> Optional[Dict[str, Any]]:
    """
    ✅ REFINAMENTO 1 (14/01/2026): Obtém o último relatório visível na tela por domínio (fonte da verdade).
    
    Este é o relatório que foi exibido por último no domínio especificado.
    Usado como fonte da verdade para "envie esse relatorio".
    
    Args:
        session_id: ID da sessão
        dominio: 'processos' ou 'financeiro' (padrão: 'processos')
    
    Returns:
        Dict com 'id', 'tipo_relatorio', 'is_filtered' ou None
    """
    try:
        from services.context_service import buscar_contexto_sessao
        
        # ✅ REFINAMENTO 1: Usar tipo_contexto baseado no domínio
        if dominio == 'financeiro':
            tipo_contexto = 'last_visible_report_id_financeiro'
        elif dominio == 'vendas':
            tipo_contexto = 'last_visible_report_id_vendas'
        else:
            tipo_contexto = 'last_visible_report_id_processos'
        
        contextos = buscar_contexto_sessao(
            session_id=session_id,
            tipo_contexto=tipo_contexto,
            chave='current'
        )
        
        if contextos and len(contextos) > 0:
            contexto = contextos[0]
            # ✅ CORREÇÃO (20/01/2026): `contexto_service` normaliza JSON em `ctx['dados']`
            dados = (
                contexto.get('dados_adicionais')
                or contexto.get('dados')
                or {}
            )
            return {
                'id': contexto.get('valor'),
                'tipo_relatorio': dados.get('tipo_relatorio'),
                'is_filtered': dados.get('is_filtered', False),
                'meta_json': dados.get('meta_json')
            }
        
        return None
        
    except Exception as e:
        logger.warning(f"⚠️ Erro ao obter last_visible_report_id ({dominio}): {e}")
        return None


def _detectar_dominio_por_mensagem(mensagem: str) -> str:
    """
    ✅ REFINAMENTO 2 (14/01/2026): Detecta domínio (processos vs financeiro) baseado na mensagem.
    
    Usa sinais específicos de banco (não só "extrato" que é ambíguo - pode ser extrato de CE/DI/DUIMP).
    
    Args:
        mensagem: Mensagem do usuário
    
    Returns:
        'financeiro' ou 'processos'
    """
    mensagem_lower = mensagem.lower()
    
    # ✅ REFINAMENTO 2: Sinais específicos de banco (não só "extrato")
    sinais_financeiro = [
        'banco', 'saldo', 'pix', 'lançamento', 'lançamentos', 'transação', 'transações',
        'conta', 'agência', 'agencia', 'bb', 'santander', 'movimentação', 'movimentações',
        'extrato do banco', 'extrato bancário', 'extrato do bb', 'extrato do santander',
        'extrato da conta', 'extrato da agência'
    ]

    # ✅ NOVO (28/01/2026): Sinais de vendas (relatórios por NF / faturamento)
    sinais_vendas = [
        'venda', 'vendas', 'nf', 'nota fiscal', 'notas fiscais', 'faturamento',
        'devolucao', 'devolução', 'icms', 'doc/icms', 'vendas por nf', 'por nf'
    ]
    
    # ✅ REFINAMENTO 2: Excluir "extrato" quando for de documentos COMEX
    sinais_comex = [
        'extrato do ce', 'extrato do cct', 'extrato da di', 'extrato do di',
        'extrato da duimp', 'extrato do duimp', 'extrato do processo'
    ]
    
    # Se menciona extrato de COMEX, não é financeiro
    if any(sinal in mensagem_lower for sinal in sinais_comex):
        return 'processos'

    # Se menciona vendas, é domínio vendas (não confundir com banco)
    if any(sinal in mensagem_lower for sinal in sinais_vendas):
        return 'vendas'
    
    # Se menciona sinais específicos de banco, é financeiro
    if any(sinal in mensagem_lower for sinal in sinais_financeiro):
        return 'financeiro'
    
    # Padrão: processos
    return 'processos'


def _parse_created_at_iso(created_at: Optional[str]) -> Optional[datetime]:
    """
    Parseia timestamps ISO vindos do REPORT_META de forma robusta.
    
    Problema real observado: `created_at` pode vir com microsegundos e/ou timezone,
    ex: `2026-01-15T16:00:28.257291` ou `2026-01-15T16:00:28-03:00`.
    
    Usar `datetime.fromisoformat` evita bugs do tipo:
    `unconverted data remains: .154506`.
    """
    if not created_at or not isinstance(created_at, str):
        return None
    texto = created_at.strip()
    if not texto:
        return None
    # fromisoformat não aceita "Z" em Python 3.9; normalizar para +00:00.
    if texto.endswith('Z'):
        texto = texto[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(texto)
    except Exception:
        pass
    # Fallbacks tolerantes (legado/formatos parciais)
    for fmt in (
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
    ):
        try:
            return datetime.strptime(texto, fmt)
        except Exception:
            continue
    return None


def _diff_minutos_desde(dt: Optional[datetime]) -> Optional[int]:
    """Retorna diferença em minutos desde dt até agora (respeitando tzinfo)."""
    if not dt:
        return None
    try:
        agora = datetime.now(dt.tzinfo) if getattr(dt, 'tzinfo', None) else datetime.now()
        return int((agora - dt).total_seconds() / 60)
    except Exception:
        return None


def pick_report(session_id: str, mensagem: str) -> Dict[str, Any]:
    """
    ✅ NOVO (12/01/2026): Função inteligente para escolher qual relatório usar.
    
    Lógica:
    1. Se mensagem menciona tipo específico ("fechamento", "hoje") → escolhe o mais recente daquele tipo
    2. Senão → escolhe active_report_id se ainda estiver dentro do TTL
    3. Se expirou → sugere atualizar
    4. Se ambíguo → retorna lista para perguntar ao usuário
    
    Args:
        session_id: ID da sessão
        mensagem: Mensagem do usuário
    
    Returns:
        Dict com:
        - 'relatorio': RelatorioGerado ou None
        - 'active_id': str ou None (ID do relatório ativo)
        - 'sugerir_atualizar': bool (se TTL expirou)
        - 'ambiguo': bool (se precisa perguntar ao usuário)
        - 'opcoes': List[Dict] (se ambíguo, lista de opções)
    """
    try:
        from datetime import datetime
        import re
        
        mensagem_lower = mensagem.lower()
        
        # 1. Verificar se mensagem menciona tipo específico
        tipo_mencionado = None
        # ✅ CORREÇÃO (13/01/2026): Detectar "fechamento" e "resumo geral" ANTES de "hoje" para evitar confusão
        if re.search(r'fechamento|fechar\s+o\s+dia|resumo\s+do\s+dia|resumo\s+geral', mensagem_lower):
            tipo_mencionado = 'fechamento_dia'
        elif re.search(r'o\s+que\s+tem|o\s+que\s+temos|dashboard', mensagem_lower):
            # ✅ CORREÇÃO: Remover "hoje" do regex para evitar pegar "fechamento do dia" ou "resumo geral"
            # "hoje" sozinho não é suficiente - precisa ser "o que temos pra hoje" ou "dashboard"
            tipo_mencionado = 'o_que_tem_hoje'
        
        # 2. Se mencionou tipo, buscar o mais recente daquele tipo
        if tipo_mencionado:
            history = obter_report_history(session_id, limite=20)
            for report_meta in history:
                if report_meta.get('tipo') == tipo_mencionado:
                    # Verificar TTL
                    created_at = report_meta.get('created_at')
                    ttl_min = report_meta.get('ttl_min', 60)
                    
                    if created_at:
                        try:
                            dt = _parse_created_at_iso(created_at)
                            diff_minutos = _diff_minutos_desde(dt)
                            if diff_minutos is None:
                                continue
                            
                            if diff_minutos <= ttl_min:
                                # Dentro do TTL, usar este
                                relatorio = buscar_relatorio_por_id(session_id, report_meta.get('id'))
                                if relatorio:
                                    # ✅ REFINAMENTO 4: Log de decisão detalhado
                                    logger.info(
                                        f"✅ [PICK_REPORT] Relatório escolhido: ID={report_meta.get('id')}, tipo={tipo_mencionado}, "
                                        f"motivo='tipo mencionado na mensagem', TTL={diff_minutos}min/{ttl_min}min"
                                    )
                                    return {
                                        'relatorio': relatorio,
                                        'active_id': report_meta.get('id'),
                                        'sugerir_atualizar': False,
                                        'ambiguo': False,
                                        'opcoes': None
                                    }
                            else:
                                # TTL expirado
                                logger.info(f"⚠️ Relatório do tipo {tipo_mencionado} encontrado mas TTL expirado ({diff_minutos} min > {ttl_min} min)")
                                return {
                                    'relatorio': None,
                                    'active_id': None,
                                    'sugerir_atualizar': True,
                                    'ambiguo': False,
                                    'opcoes': None,
                                    'tipo_mencionado': tipo_mencionado
                                }
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao verificar TTL: {e}")
            
            # Tipo mencionado mas não encontrado ou expirado
            return {
                'relatorio': None,
                'active_id': None,
                'sugerir_atualizar': True,
                'ambiguo': False,
                'opcoes': None,
                'tipo_mencionado': tipo_mencionado
            }
        
        # 3. Não mencionou tipo → usar active_report_id se dentro do TTL
        # ✅ REFINAMENTO 2: Usar detector de domínio mais preciso (não só "extrato")
        dominio = _detectar_dominio_por_mensagem(mensagem)
        active_id = obter_active_report_id(session_id, dominio=dominio)
        
        # ✅ REFINAMENTO 4: Log de decisão
        logger.info(f"🔍 [PICK_REPORT] Domínio detectado: {dominio} (motivo: análise de mensagem)")
        if active_id:
            history = obter_report_history(session_id, limite=10)
            for report_meta in history:
                if report_meta.get('id') == active_id:
                    created_at = report_meta.get('created_at')
                    ttl_min = report_meta.get('ttl_min', 60)
                    
                    if created_at:
                        try:
                            dt = _parse_created_at_iso(created_at)
                            diff_minutos = _diff_minutos_desde(dt)
                            if diff_minutos is None:
                                continue
                            
                            if diff_minutos <= ttl_min:
                                # Dentro do TTL, usar active
                                relatorio = buscar_relatorio_por_id(session_id, active_id)
                                if relatorio:
                                    # ✅ REFINAMENTO 4: Log de decisão detalhado
                                    logger.info(
                                        f"✅ [PICK_REPORT] Relatório escolhido: ID={active_id}, domínio={dominio}, "
                                        f"motivo='active_report_id', TTL={diff_minutos}min/{ttl_min}min"
                                    )
                                    return {
                                        'relatorio': relatorio,
                                        'active_id': active_id,
                                        'sugerir_atualizar': False,
                                        'ambiguo': False,
                                        'opcoes': None
                                    }
                            else:
                                # TTL expirado
                                logger.info(f"⚠️ Relatório ativo expirado ({diff_minutos} min > {ttl_min} min)")
                                return {
                                    'relatorio': None,
                                    'active_id': active_id,
                                    'sugerir_atualizar': True,
                                    'ambiguo': False,
                                    'opcoes': None
                                }
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao verificar TTL do active: {e}")
        
        # 4. Verificar se há múltiplos relatórios válidos (ambiguidade)
        history = obter_report_history(session_id, limite=10)
        relatorios_validos = []
        
        for report_meta in history:
            created_at = report_meta.get('created_at')
            ttl_min = report_meta.get('ttl_min', 60)
            
            if created_at:
                try:
                    dt = _parse_created_at_iso(created_at)
                    diff_minutos = _diff_minutos_desde(dt)
                    if diff_minutos is not None and diff_minutos <= ttl_min:
                        relatorios_validos.append(report_meta)
                except Exception:
                    continue
        
        if len(relatorios_validos) > 1:
            # Ambíguo - múltiplos relatórios válidos
            logger.info(f"⚠️ Ambiguidade detectada: {len(relatorios_validos)} relatórios válidos")
            return {
                'relatorio': None,
                'active_id': active_id,
                'sugerir_atualizar': False,
                'ambiguo': True,
                'opcoes': relatorios_validos
            }
        elif len(relatorios_validos) == 1:
            # Apenas um válido, usar ele
            relatorio = buscar_relatorio_por_id(session_id, relatorios_validos[0].get('id'))
            if relatorio:
                logger.info(f"✅ Único relatório válido escolhido (ID: {relatorios_validos[0].get('id')})")
                return {
                    'relatorio': relatorio,
                    'active_id': relatorios_validos[0].get('id'),
                    'sugerir_atualizar': False,
                    'ambiguo': False,
                    'opcoes': None
                }
        
        # Nenhum relatório válido encontrado
        return {
            'relatorio': None,
            'active_id': active_id,
            'sugerir_atualizar': True,
            'ambiguo': False,
            'opcoes': None
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao escolher relatório: {e}", exc_info=True)
        return {
            'relatorio': None,
            'active_id': None,
            'sugerir_atualizar': False,
            'ambiguo': False,
            'opcoes': None
        }


def buscar_ultimo_relatorio(
    session_id: str,
    tipo_relatorio: Optional[str] = None,
    usar_active_report_id: bool = True
) -> Optional[RelatorioGerado]:
    """
    Busca o último relatório gerado na sessão.
    
    Args:
        session_id: ID da sessão
        tipo_relatorio: Tipo específico para buscar (opcional) - busca por campo 'valor' na tabela
    
    Returns:
        RelatorioGerado se encontrado, None caso contrário
    """
    try:
        # ✅ CORREÇÃO CRÍTICA (09/01/2026): Buscar por 'valor' em vez de 'chave'
        # O campo 'valor' armazena o tipo_relatorio, enquanto 'chave' inclui categoria e data
        from services.context_service import buscar_contexto_sessao
        
        if tipo_relatorio:
            # ✅ CORREÇÃO CRÍTICA: Buscar todos os relatórios e filtrar por 'valor' (tipo_relatorio)
            # O campo 'valor' armazena o tipo_relatorio, enquanto 'chave' inclui categoria e data
            contextos = buscar_contexto_sessao(
                session_id=session_id,
                tipo_contexto='ultimo_relatorio',
                chave=None  # Buscar todos os relatórios do tipo
            )
            
            if not contextos or len(contextos) == 0:
                logger.debug(f"⚠️ Nenhum relatório encontrado para sessão {session_id}")
                return None
            
            # Filtrar pelo campo 'valor' (tipo_relatorio) e pegar o mais recente
            relatorios_filtrados = [ctx for ctx in contextos if ctx.get('valor') == tipo_relatorio]
            
            if not relatorios_filtrados:
                logger.debug(f"⚠️ Nenhum relatório encontrado para sessão {session_id} e tipo {tipo_relatorio}")
                return None
            
            # Pegar o mais recente (já vem ordenado por atualizado_em DESC, mas vamos garantir)
            contexto = sorted(relatorios_filtrados, key=lambda x: x.get('atualizado_em', ''), reverse=True)[0]
            dados = contexto.get('dados', {})
            
            if not dados:
                logger.warning(f"⚠️ Contexto encontrado mas dados_json vazio")
                return None
            
            # Deserializar
            relatorio = RelatorioGerado.from_dict(dados)
            logger.info(f"✅ Último relatório recuperado por tipo: {relatorio.tipo_relatorio}")
            
            return relatorio
        else:
            # ✅ NOVO (12/01/2026): Tentar usar active_report_id primeiro
            if usar_active_report_id:
                # ✅ CORREÇÃO B: Usar domínio 'processos' por padrão (relatórios de processos)
                active_id = obter_active_report_id(session_id, dominio='processos')
                if active_id:
                    relatorio = buscar_relatorio_por_id(session_id, active_id)
                    if relatorio:
                        logger.info(f"✅ Relatório ativo encontrado via active_report_id: {active_id}")
                        return relatorio
            
            # Fallback: Buscar todos os relatórios e pegar o mais recente
            contextos = buscar_contexto_sessao(
                session_id=session_id,
                tipo_contexto='ultimo_relatorio',
                chave=None  # Buscar todos
            )
            
            if not contextos or len(contextos) == 0:
                logger.debug(f"⚠️ Nenhum relatório encontrado para sessão {session_id}")
                return None
            
            # Pegar o mais recente (já vem ordenado por atualizado_em DESC)
            contexto = contextos[0]
            dados = contexto.get('dados', {})
            
            if not dados:
                logger.warning(f"⚠️ Contexto encontrado mas dados_json vazio")
                return None
            
            # Deserializar
            relatorio = RelatorioGerado.from_dict(dados)
            logger.info(f"✅ Último relatório recuperado: {relatorio.tipo_relatorio}")
            
            return relatorio
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar último relatório: {e}", exc_info=True)
        return None


def obter_tipo_relatorio_salvo(
    session_id: str,
    tentar_buscar_por_texto: Optional[str] = None
) -> Optional[str]:
    """
    Obtém o tipo de relatório do último relatório salvo, buscando diretamente do JSON.
    
    ✅ PASSO 6 - FASE 3: Usar JSON como fonte da verdade em vez de regex.
    
    Args:
        session_id: ID da sessão
        tentar_buscar_por_texto: Texto opcional para tentar identificar tipo (usado apenas como fallback)
    
    Returns:
        Tipo do relatório ('o_que_tem_hoje', 'fechamento_dia', etc.) ou None se não encontrado
    """
    try:
        # Primeiro, tentar buscar o último relatório sem filtro (mais recente)
        relatorio = buscar_ultimo_relatorio(session_id, tipo_relatorio=None)
        
        if relatorio:
            # ✅ FASE 3: Tipo sempre vem do JSON, não do texto
            # Verificar se tem dados_json no meta_json
            if relatorio.meta_json and relatorio.meta_json.get('dados_json'):
                tipo_json = relatorio.meta_json['dados_json'].get('tipo_relatorio')
                if tipo_json:
                    logger.debug(f'✅ Tipo de relatório obtido do JSON: {tipo_json}')
                    return tipo_json
            
            # Fallback: usar tipo_relatorio direto do RelatorioGerado
            if relatorio.tipo_relatorio:
                logger.debug(f'✅ Tipo de relatório obtido do objeto: {relatorio.tipo_relatorio}')
                return relatorio.tipo_relatorio
        
        # Fallback final: tentar identificar por texto (último recurso)
        if tentar_buscar_por_texto:
            texto_upper = tentar_buscar_por_texto.upper()
            if 'FECHAMENTO DO DIA' in texto_upper:
                logger.warning('⚠️ Usando fallback regex para detectar tipo (deveria usar JSON). Tipo: fechamento_dia')
                return 'fechamento_dia'
            elif 'O QUE TEMOS PRA HOJE' in texto_upper or 'CHEGANDO HOJE' in texto_upper:
                logger.warning('⚠️ Usando fallback regex para detectar tipo (deveria usar JSON). Tipo: o_que_tem_hoje')
                return 'o_que_tem_hoje'
        
        logger.debug(f'⚠️ Tipo de relatório não encontrado para sessão {session_id}')
        return None
        
    except Exception as e:
        logger.error(f'❌ Erro ao obter tipo de relatório salvo: {e}', exc_info=True)
        return None


def criar_relatorio_gerado(
    tipo_relatorio: str,
    texto_chat: str,
    categoria: Optional[str] = None,
    filtros: Optional[Dict[str, Any]] = None,
    meta_json: Optional[Dict[str, Any]] = None
) -> RelatorioGerado:
    """
    Helper para criar RelatorioGerado com valores padrão.
    
    Args:
        tipo_relatorio: Tipo do relatório
        texto_chat: Texto do relatório
        categoria: Categoria (opcional)
        filtros: Filtros aplicados (opcional)
        meta_json: Metadados extras (opcional)
    
    Returns:
        Instância de RelatorioGerado
    """
    # Adicionar data_ref aos filtros se não tiver
    if filtros is None:
        filtros = {}
    if 'data_ref' not in filtros:
        filtros['data_ref'] = datetime.now().strftime('%Y-%m-%d')

    # ✅ Normalizar dados_json (REPORT_META) para filtros determinísticos
    # Garante `processo_referencia` e `categoria` em itens de qualquer seção.
    try:
        if isinstance(meta_json, dict) and isinstance(meta_json.get("dados_json"), dict):
            from services.report_normalization_service import normalize_report_json
            meta_json["dados_json"] = normalize_report_json(meta_json["dados_json"])
    except Exception as e:
        logger.debug(f"⚠️ Erro ao normalizar dados_json do relatório: {e}")
    
    return RelatorioGerado(
        tipo_relatorio=tipo_relatorio,
        categoria=categoria,
        texto_chat=texto_chat,
        filtros=filtros,
        meta_json=meta_json,
        criado_em=datetime.now().isoformat()
    )



