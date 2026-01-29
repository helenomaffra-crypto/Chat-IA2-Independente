"""
ToolGateService - Resolução automática de contexto para tools.

✅ NOVO (14/01/2026): Fase 2A - Resolução automática de contexto com escopo pequeno e seguro.

Este serviço injeta automaticamente valores faltantes nos argumentos das tools baseado
no contexto da sessão, ANTES de executar. Começa apenas com report_id para tools de relatório.

Regra de ouro: NUNCA sobrescrever valores explícitos fornecidos pelo usuário/IA.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List, Tuple

logger = logging.getLogger(__name__)

# Feature flag para habilitar/desabilitar ToolGate
TOOL_GATE_ENABLED = os.getenv('TOOL_GATE_ENABLED', 'true').lower() == 'true'

# ✅ Fase 2A: Guard de staleness (minutos) para não injetar report_id velho
TOOL_GATE_REPORT_MAX_AGE_MIN = int(os.getenv('TOOL_GATE_REPORT_MAX_AGE_MIN', '60'))

# ✅ Fase 2A: Allowlist de tools que aceitam injeção de report_id
TOOLS_RELATORIO = [
    'buscar_secao_relatorio_salvo',
    'filtrar_relatorio',
    'melhorar_relatorio',
    'enviar_relatorio_email',
]

# ✅ Fase 2A: Domínio determinístico por tool (evita injetar report_id de outro domínio)
TOOL_DOMINIO = {tool: 'processos' for tool in TOOLS_RELATORIO}

# Prioridade de resolução de report_id (ordem importa)
PRIORIDADE_REPORT_ID = [
    'active_report_id',      # Relatório ativo na sessão
    'last_visible_report_id', # Último relatório visível ao usuário
    'REPORT_META',           # Metadata do último response (se disponível)
]


class ToolGateService:
    """
    Serviço para resolução automática de contexto de tools.
    
    Funcionalidades:
    - Injetar report_id automaticamente quando faltar
    - Validar que valores explícitos não são sobrescritos
    - Logging detalhado de todas as injeções
    """
    
    def __init__(self):
        self.enabled = TOOL_GATE_ENABLED
    
    def resolver_contexto_tool(
        self,
        nome_tool: str,
        args: Dict[str, Any],
        session_id: Optional[str] = None,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve contexto automaticamente para uma tool.
        
        ✅ Fase 2A: Apenas report_id para tools de relatório.
        
        Args:
            nome_tool: Nome da tool a executar
            args: Argumentos fornecidos pela IA/usuário
            session_id: ID da sessão (para buscar contexto)
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            {
                'args_resolvidos': Dict,  # Argumentos com valores injetados
                'injections': List[Dict], # Lista de injeções realizadas
                'erro': str (opcional)    # Se não conseguir resolver
            }
        """
        if not self.enabled:
            logger.debug(f'🔒 ToolGate desabilitado - retornando args originais para {nome_tool}')
            return {
                'args_resolvidos': args,
                'injections': [],
                'erro': None
            }
        
        # Copiar args para não modificar o original
        args_resolvidos = args.copy()
        injections = []
        
        # ✅ Fase 2A: Resolver report_id para tools de relatório
        if nome_tool in TOOLS_RELATORIO:
            resultado_report_id = self._resolver_report_id(
                nome_tool=nome_tool,
                args=args_resolvidos,
                session_id=session_id,
                mensagem_original=mensagem_original
            )
            
            if resultado_report_id.get('erro'):
                return {
                    'args_resolvidos': args_resolvidos,
                    'injections': injections,
                    'erro': resultado_report_id['erro']
                }
            
            if resultado_report_id.get('injection'):
                injections.append(resultado_report_id['injection'])
                args_resolvidos['report_id'] = resultado_report_id['report_id']
        
        return {
            'args_resolvidos': args_resolvidos,
            'injections': injections,
            'erro': None
        }
    
    def _resolver_report_id(
        self,
        nome_tool: str,
        args: Dict[str, Any],
        session_id: Optional[str] = None,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve report_id automaticamente quando faltar.
        
        ✅ REGRA CRÍTICA: Nunca sobrescrever se report_id já foi fornecido explicitamente.
        
        Prioridade:
        1. active_report_id (relatório ativo na sessão)
        2. last_visible_report_id (último relatório visível)
        3. REPORT_META (metadata do último response, se disponível)
        
        Returns:
            {
                'report_id': str (opcional),
                'injection': Dict (opcional),  # Detalhes da injeção
                'erro': str (opcional)        # Se não conseguir resolver
            }
        """
        # ✅ REGRA CRÍTICA: Se report_id já foi fornecido explicitamente, não injetar
        if 'report_id' in args and args['report_id']:
            logger.debug(f'✅ Tool {nome_tool} já tem report_id explícito: {args["report_id"]} - não injetar')
            return {'report_id': args['report_id']}
        
        if not session_id:
            return {
                'erro': 'Nenhum relatório ativo. Gere um relatório primeiro (ex: "o que temos pra hoje?")'
            }
        
        dominio = TOOL_DOMINIO.get(nome_tool, 'processos')

        # Tentar resolver report_id seguindo ordem de prioridade
        for fonte in PRIORIDADE_REPORT_ID:
            report_id, ts_str = self._buscar_report_id_por_fonte(fonte, session_id, dominio, mensagem_original)
            
            if report_id:
                # ✅ Guard de staleness: se temos timestamp e está velho, NÃO usar
                if ts_str and self._is_timestamp_stale(ts_str, max_age_min=TOOL_GATE_REPORT_MAX_AGE_MIN):
                    logger.warning(
                        f'⚠️ [ToolGate] Ignorando report_id stale para {nome_tool}: '
                        f'valor={report_id}, fonte={fonte}, dominio={dominio}, ts={ts_str}, max_age_min={TOOL_GATE_REPORT_MAX_AGE_MIN}'
                    )
                    continue

                # ✅ Logging detalhado da injeção
                logger.info(
                    f'✅✅✅ [ToolGate] Injetado report_id para {nome_tool}: '
                    f'valor={report_id}, fonte={fonte}, dominio={dominio}, session={session_id}'
                )
                
                return {
                    'report_id': report_id,
                    'injection': {
                        'campo': 'report_id',
                        'valor': report_id,
                        'fonte': fonte,
                        'dominio': dominio,
                        'timestamp': ts_str,
                        'tool': nome_tool
                    }
                }
        
        # Se chegou aqui, não conseguiu resolver
        return {
            'erro': 'Nenhum relatório ativo. Gere um relatório primeiro (ex: "o que temos pra hoje?")'
        }
    
    def _buscar_report_id_por_fonte(
        self,
        fonte: str,
        session_id: str,
        dominio: str,
        mensagem_original: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Busca report_id por uma fonte específica.
        
        Args:
            fonte: Fonte de busca ('active_report_id', 'last_visible_report_id', 'REPORT_META')
            session_id: ID da sessão
            mensagem_original: Mensagem original (para extrair REPORT_META se necessário)
        
        Returns:
            (report_id, timestamp_str) se encontrado, (None, None) caso contrário
        """
        try:
            if fonte == 'active_report_id':
                from services.report_service import obter_active_report_info
                info = obter_active_report_info(session_id, dominio=dominio)
                if info and isinstance(info, dict):
                    # Preferir created_at do meta_json (se existir), senão criado_em do contexto
                    meta_json = info.get('meta_json') or {}
                    ts = meta_json.get('created_at') or info.get('criado_em')
                    return info.get('id'), ts
                return None, None
            
            elif fonte == 'last_visible_report_id':
                from services.report_service import obter_last_visible_report_id
                last_visible = obter_last_visible_report_id(session_id, dominio=dominio)
                if last_visible and isinstance(last_visible, dict):
                    meta_json = last_visible.get('meta_json') or {}
                    ts = meta_json.get('created_at')
                    return last_visible.get('id'), ts
                return None, None
            
            elif fonte == 'REPORT_META':
                # ✅ Fase 2B (14/01/2026): Fallback por REPORT_META usando histórico persistido
                # Fonte preferida: reports persistidos (ultimo_relatorio) → parse [REPORT_META:{...}] do texto_chat
                from services.report_service import obter_report_history, buscar_relatorio_por_id

                # Buscar últimos N reports (mais recentes primeiro)
                history = obter_report_history(session_id, limite=10) or []
                for item in history:
                    try:
                        report_id = item.get('id')
                        tipo = item.get('tipo')
                        ts = item.get('created_at')

                        if not report_id or not isinstance(report_id, str):
                            continue

                        # Se timestamp for inválido, ignorar (staleness check não confiável)
                        if ts and not self._parse_timestamp(ts):
                            logger.warning(
                                f'⚠️ [ToolGate] REPORT_META descartado (timestamp inválido): '
                                f'id={report_id}, ts={ts}, dominio={dominio}, session={session_id}'
                            )
                            continue

                        # Validar domínio pelo tipo do relatório (evita pegar report financeiro)
                        if tipo and self._infer_dominio_por_tipo_relatorio(tipo) != dominio:
                            logger.info(
                                f'ℹ️ [ToolGate] REPORT_META descartado (domínio mismatch): '
                                f'id={report_id}, tipo={tipo}, dominio_esperado={dominio}, session={session_id}'
                            )
                            continue

                        # Validar existência no banco/contexto (fonte da verdade)
                        relatorio = buscar_relatorio_por_id(session_id, report_id)
                        if not relatorio:
                            logger.info(
                                f'ℹ️ [ToolGate] REPORT_META descartado (id não existe no banco): '
                                f'id={report_id}, dominio={dominio}, session={session_id}'
                            )
                            continue

                        # Validar domínio de forma redundante (com base no tipo_relatorio real)
                        try:
                            tipo_real = getattr(relatorio, 'tipo_relatorio', None)
                            if tipo_real and self._infer_dominio_por_tipo_relatorio(tipo_real) != dominio:
                                logger.info(
                                    f'ℹ️ [ToolGate] REPORT_META descartado (domínio mismatch - tipo_real): '
                                    f'id={report_id}, tipo_real={tipo_real}, dominio_esperado={dominio}, session={session_id}'
                                )
                                continue
                        except Exception:
                            pass

                        return report_id, ts
                    except Exception as e:
                        logger.warning(
                            f'⚠️ [ToolGate] Erro processando REPORT_META no history: {e}',
                            exc_info=True
                        )
                        continue

                return None, None
            
            return None, None
            
        except Exception as e:
            logger.warning(f'⚠️ Erro ao buscar report_id por fonte {fonte}: {e}')
            return None, None

    def _parse_timestamp(self, ts: str) -> Optional[datetime]:
        """
        Parse robusto de timestamps comuns no projeto:
        - ISO 8601 (python isoformat): 2026-01-14T15:10:00(.ffffff)
        - SQLite CURRENT_TIMESTAMP:    2026-01-14 15:10:00(.ffffff)
        """
        if not ts or not isinstance(ts, str):
            return None
        for parser in (
            lambda s: datetime.fromisoformat(s),
            lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S"),
            lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f"),
        ):
            try:
                return parser(ts)
            except Exception:
                continue
        return None

    def _is_timestamp_stale(self, ts: str, max_age_min: int) -> bool:
        dt = self._parse_timestamp(ts)
        if not dt:
            # Se não conseguimos parsear, não bloquear (mas logar)
            logger.debug(f'⚠️ [ToolGate] Não foi possível parsear timestamp "{ts}" para staleness check')
            return False
        return dt < (datetime.now() - timedelta(minutes=max_age_min))

    def _infer_dominio_por_tipo_relatorio(self, tipo_relatorio: str) -> str:
        """
        Inferência determinística e simples de domínio baseada no tipo do relatório.
        Mantém compatibilidade com a lógica de salvamento de domínio no report_service.
        """
        if not tipo_relatorio:
            return 'processos'
        t = str(tipo_relatorio).lower()
        sinais_financeiro = ['financeiro', 'banco', 'lançamento', 'lancamento', 'extrato_banco', 'extrato_bancario']
        sinais_comex_excluir = ['extrato_ce', 'extrato_cct', 'extrato_di', 'extrato_duimp']
        eh_fin = any(x in t for x in sinais_financeiro) and not any(x in t for x in sinais_comex_excluir)
        return 'financeiro' if eh_fin else 'processos'


# Singleton instance
_tool_gate_service_instance = None


def get_tool_gate_service() -> ToolGateService:
    """
    Retorna instância singleton do ToolGateService.
    
    Returns:
        Instância do ToolGateService
    """
    global _tool_gate_service_instance
    if _tool_gate_service_instance is None:
        _tool_gate_service_instance = ToolGateService()
    return _tool_gate_service_instance
