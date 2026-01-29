"""
ProcessoListService - Serviço para listagem de processos

Migrado do chat_service.py para centralizar lógica de listagem de processos.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ProcessoListService:
    """Serviço para listagem de processos de importação."""
    
    def __init__(self, chat_service=None):
        """
        Inicializa o ProcessoListService.
        
        Args:
            chat_service: Instância opcional do ChatService (para métodos auxiliares se necessário)
        """
        self.chat_service = chat_service
    
    def listar_processos_por_eta(
        self,
        filtro_data: str = 'semana',
        data_especifica: Optional[str] = None,
        categoria: Optional[str] = None,
        processo_referencia: Optional[str] = None,
        limite: int = 200,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista processos filtrados por ETA.
        
        Args:
            filtro_data: Filtro de data ('hoje', 'amanha', 'semana', 'proxima_semana', 'mes', 'proximo_mes', 'futuro', 'data_especifica')
            data_especifica: Data específica no formato DD/MM/AAAA ou AAAA-MM-DD (usado quando filtro_data='data_especifica')
            categoria: Categoria do processo (opcional, ex: 'ALH', 'VDM', 'MV5')
            limite: Limite de resultados
            mensagem_original: Mensagem original do usuário (para contexto)
        
        Returns:
            Dict com 'sucesso', 'resposta', 'total', 'filtro_data', 'categoria', 'dados'
        """
        try:
            # ✅ NOVO: "quando chega o PROCESSO?" → usar o pipeline de ETA (mesma tool) com filtro por processo
            if processo_referencia:
                from services.processo_repository import ProcessoRepository

                proc_ref = str(processo_referencia).strip().upper()
                repo = ProcessoRepository()
                dto = repo.buscar_por_referencia(proc_ref)

                if not dto:
                    return {
                        'sucesso': True,
                        'resposta': f"✅ **Nenhum processo encontrado com referência {proc_ref}.**",
                        'total': 0,
                        'filtro_data': filtro_data,
                        'categoria': categoria,
                        'dados': [],
                    }

                # Montar objeto no mesmo formato do relatório de chegadas (db_manager.listar_processos_por_eta)
                cat = (proc_ref.split('.', 1)[0] if '.' in proc_ref else proc_ref[:3]).upper()
                processo_item = {
                    'processo_referencia': proc_ref,
                    'categoria': cat,
                    'ce': {
                        'numero': dto.numero_ce or '',
                        'situacao': dto.situacao_ce or '',
                        'pendencia_frete': bool(dto.pendencia_frete) if dto.pendencia_frete is not None else False,
                        'pendencia_afrmm': False,
                        'carga_bloqueada': False,
                        'bloqueio_impede_despacho': False,
                    },
                    'eta': {
                        'eta_iso': dto.eta_iso.isoformat() if getattr(dto, 'eta_iso', None) else None,
                        'fonte_eta': 'kanban' if (dto.eta_iso or dto.porto_codigo or dto.nome_navio or dto.status_shipsgo) else (dto.fonte or 'kanban'),
                        'porto_codigo': dto.porto_codigo,
                        'porto_nome': dto.porto_nome,
                        'nome_navio': dto.nome_navio,
                        'status_shipsgo': dto.status_shipsgo,
                    },
                    'shipsgo': {
                        'shipsgo_eta': dto.eta_iso.isoformat() if getattr(dto, 'eta_iso', None) else None,
                        'shipsgo_porto_codigo': dto.porto_codigo,
                        'shipsgo_porto_nome': dto.porto_nome,
                        'shipsgo_navio': dto.nome_navio,
                        'shipsgo_status': dto.status_shipsgo,
                    },
                }

                # Resposta enxuta e consistente com "chegando"
                eta_fmt = None
                if processo_item['eta'].get('eta_iso'):
                    try:
                        eta_fmt = datetime.fromisoformat(processo_item['eta']['eta_iso'].replace('Z', '').split('+')[0].split('.')[0]).strftime('%d/%m/%Y %H:%M')
                    except Exception:
                        eta_fmt = str(processo_item['eta']['eta_iso'])

                if not eta_fmt:
                    resposta = (
                        f"📅 **Previsão de chegada do processo {proc_ref} (ETA/POD):**\n"
                        f"- ⚠️ ETA não disponível no snapshot do Kanban/cache no momento.\n"
                    )
                else:
                    porto_txt = processo_item['eta'].get('porto_nome') or 'N/A'
                    navio_txt = processo_item['eta'].get('nome_navio') or 'N/A'
                    status_txt = processo_item['eta'].get('status_shipsgo') or 'N/A'
                    fonte_txt = processo_item['eta'].get('fonte_eta') or 'kanban'
                    resposta = (
                        f"📅 **Previsão de chegada do processo {proc_ref} (ETA/POD):**\n"
                        f"- ETA {eta_fmt} ({fonte_txt}) – {processo_item['eta'].get('porto_codigo') or ''} - {porto_txt} – "
                        f"Navio {navio_txt} – Status: {status_txt}\n\n"
                    )

                # Anexar informações básicas (etapa/modal/CE) mantendo o padrão do chat
                if dto.etapa_kanban:
                    resposta += f"**Etapa no Kanban:** {dto.etapa_kanban}\n"
                if dto.modal:
                    resposta += f"**Modal:** {dto.modal}\n"
                resposta += "\n"
                if dto.numero_ce:
                    resposta += "**📦 Conhecimento de Embarque:**\n"
                    resposta += f"- CE {dto.numero_ce}\n"
                    if dto.situacao_ce:
                        resposta += f"- Situação: {dto.situacao_ce}\n"
                    resposta += "\n"

                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'total': 1,
                    'filtro_data': filtro_data,
                    'categoria': categoria,
                    'dados': [processo_item],
                }

            from db_manager import listar_processos_por_eta
            
            logger.info(f'🔍 ProcessoListService.listar_processos_por_eta: Buscando processos com ETA (filtro={filtro_data}, categoria={categoria}, limite={limite})')
            
            # ✅ CORREÇÃO CRÍTICA: Para "esta semana", incluir TODOS os processos com ETA na semana
            # O dashboard mostra processos com ETA nesta semana (domingo até sábado), 
            # independente de terem chegado ou não. Por isso, devemos incluir passado.
            # Isso permite mostrar tanto processos que já chegaram quanto os que vão chegar.
            incluir_passado = (filtro_data == 'semana')
            
            # Buscar processos filtrados por ETA
            processos = listar_processos_por_eta(
                filtro_data=filtro_data,
                data_especifica=data_especifica,
                categoria=categoria.upper() if categoria else None,
                limit=limite,
                incluir_passado=incluir_passado
            )
            
            logger.info(f'🔍 ProcessoListService.listar_processos_por_eta: Encontrados {len(processos)} processos')
            
            if not processos:
                # Determinar texto do filtro
                if filtro_data == 'hoje':
                    texto_filtro = 'hoje'
                elif filtro_data in ('amanha', 'amanhã'):
                    texto_filtro = 'amanhã'
                elif filtro_data == 'semana':
                    texto_filtro = 'esta semana'
                elif filtro_data == 'proxima_semana':
                    texto_filtro = 'semana que vem'
                elif filtro_data == 'mes':
                    texto_filtro = 'neste mês'
                elif filtro_data == 'proximo_mes':
                    texto_filtro = 'mês que vem'
                elif filtro_data == 'data_especifica' and data_especifica:
                    texto_filtro = f'em {data_especifica}'
                else:
                    texto_filtro = 'no período especificado'
                
                resposta = f"✅ **Nenhum processo encontrado com ETA {texto_filtro}.**\n\n"

                # ✅ UX: ajudar quando o usuário informou data “suspeita”
                # Ex: "23/01/25" (ano com 2 dígitos) ou data no passado, mas a intenção é “chegando”.
                try:
                    from datetime import datetime as _dt
                    import re as _re

                    msg = str(mensagem_original or '')
                    msg_lower = msg.lower()
                    if filtro_data == 'data_especifica' and data_especifica:
                        # Detectar entrada com ano em 2 dígitos no texto original
                        if _re.search(r'\b\d{1,2}/\d{1,2}/\d{2}\b', msg):
                            resposta += (
                                "⚠️ **Dica:** percebi que você digitou o ano com 2 dígitos (ex: `23/01/25`). "
                                "Aqui o mais seguro é usar 4 dígitos (ex: `23/01/2026`).\n\n"
                            )

                        # Se a data informada cair no passado e a pergunta sugere futuro (“chegando”),
                        # adicionar aviso explícito.
                        if '/' in str(data_especifica):
                            partes = str(data_especifica).split('/')
                            if len(partes) == 3:
                                dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
                                if 0 <= ano < 100:
                                    ano = 2000 + ano
                                dt = _dt(ano, mes, dia)
                                hoje = _dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
                                if dt < hoje and ('cheg' in msg_lower or 'chegando' in msg_lower):
                                    resposta += (
                                        f"⚠️ **Atenção:** a data informada ({dt.strftime('%d/%m/%Y')}) está no passado. "
                                        "Se você quis dizer o próximo ano, tente com o ano correto.\n\n"
                                    )
                except Exception:
                    pass
                if categoria:
                    # Verificar se existem processos da categoria sem ETA no período
                    from db_manager import listar_processos_por_categoria
                    processos_categoria = listar_processos_por_categoria(categoria.upper(), limit=5)
                    
                    if processos_categoria:
                        resposta += f"💡 **Informação:** Existem processos da categoria **{categoria.upper()}** no sistema, mas nenhum tem ETA previsto para {texto_filtro}.\n\n"
                        resposta += f"📋 **Sugestões:**\n"
                        resposta += f"   • Tente perguntar sem mencionar um período: \"quando chegam os {categoria.upper()}?\"\n"
                        resposta += f"   • Ou pergunte por outro período: \"quando chegam os {categoria.upper()} esta semana?\"\n"
                        resposta += f"   • Ou consulte um processo específico: \"como está o {processos_categoria[0]}?\""
                    else:
                        resposta += f"💡 **Dica:** Não há processos da categoria **{categoria.upper()}** no sistema.\n\n"
                        resposta += f"📋 **Sugestões:**\n"
                        resposta += f"   • Verifique se a categoria está correta (ex: ALH, VDM, MV5, NTM, etc.)\n"
                        resposta += f"   • Tente com outra categoria que você sabe que existe no sistema"
                else:
                    resposta += f"💡 **Dica:** Não há processos chegando {texto_filtro}.\n\n"
                    resposta += f"💡 **Dica:** Verifique se há processos no Kanban com ETA preenchido para este período."
            else:
                # Primeiro, verificar se a mensagem original pede agrupamento por categoria
                mensagem_original_lower = str(mensagem_original).lower() if mensagem_original else ''
                pediu_agrupado_categoria = (
                    ('agrup' in mensagem_original_lower or 'grupo' in mensagem_original_lower)
                    and 'categoria' in mensagem_original_lower
                )
                
                if pediu_agrupado_categoria and filtro_data == 'semana':
                    try:
                        from services.analytics_service import (
                            obter_chegadas_agrupadas_por_categoria,
                            formatar_resumo_chegadas_agrupadas_por_categoria,
                        )
                        dados_agrupados = obter_chegadas_agrupadas_por_categoria(
                            filtro_data=filtro_data,
                            data_especifica=data_especifica,
                            categoria=categoria,
                            limite=limite,
                            incluir_passado=False,
                        )
                        resposta_agrupada = formatar_resumo_chegadas_agrupadas_por_categoria(
                            dados_agrupados,
                            'esta semana',
                        )
                        return {
                            'sucesso': True,
                            'resposta': resposta_agrupada,
                            'total': dados_agrupados.get('total_processos', len(processos)),
                            'filtro_data': filtro_data,
                            'categoria': categoria,
                            'dados': processos,
                            'dados_agrupados': dados_agrupados,
                        }
                    except Exception as e:
                        logger.error(
                            f'Erro ao agrupar chegadas por categoria: {e}',
                            exc_info=True,
                        )
                
                # Caso não peça agrupamento ou haja erro, segue o comportamento original
                # Determinar título baseado no filtro
                if filtro_data == 'hoje':
                    titulo = 'chegam hoje'
                elif filtro_data in ('amanha', 'amanhã'):
                    titulo = 'chegam amanhã'
                elif filtro_data == 'semana':
                    titulo = 'chegam esta semana'
                elif filtro_data == 'proxima_semana':
                    titulo = 'chegam semana que vem'
                elif filtro_data == 'mes':
                    titulo = 'chegam neste mês'
                elif filtro_data == 'proximo_mes':
                    titulo = 'chegam mês que vem'
                elif filtro_data == 'data_especifica' and data_especifica:
                    titulo = f'chegam em {data_especifica}'
                else:
                    titulo = 'chegam no período especificado'
                
                if categoria:
                    resposta = f"🚢 **Processos {categoria.upper()} que {titulo}** ({len(processos)} processo(s))\n\n"
                else:
                    resposta = f"🚢 **Processos que {titulo}** ({len(processos)} processo(s))\n\n"

                # ✅ MELHORIA (19/01/2026): Formato compacto (1 linha por processo)
                # Motivo: mantém riqueza de informação sem poluir com múltiplas linhas repetidas.
                def _fmt_eta_br(eta_raw: Optional[str]) -> Optional[str]:
                    if not eta_raw:
                        return None
                    try:
                        import re
                        eta_clean = str(eta_raw).replace('Z', '')
                        eta_clean = re.sub(r'[+-]\d{2}:\d{2}$', '', eta_clean)
                        if 'T' in eta_clean:
                            dt = datetime.fromisoformat(eta_clean)
                        elif len(eta_clean) == 10 and '-' in eta_clean:
                            dt = datetime.fromisoformat(eta_clean + 'T00:00:00')
                        else:
                            return str(eta_raw)
                        return dt.strftime('%d/%m/%Y %H:%M')
                    except Exception:
                        return str(eta_raw)

                def _fmt_fonte_eta(fonte_raw: Optional[str]) -> Optional[str]:
                    fonte = (fonte_raw or '').strip().lower()
                    # Compat: versões antigas usavam "ictsi" para ETA do Kanban.
                    if fonte == 'ictsi':
                        fonte = 'kanban'
                    labels = {
                        'shipsgo': 'ShipsGo',
                        'kanban': 'Kanban (ShipsGo)',
                        'sql_server': 'SQL Server',
                    }
                    return labels.get(fonte)

                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '') or 'N/A'

                    eta_info = proc.get('eta', {}) or {}
                    shipsgo = proc.get('shipsgo', {}) or {}

                    fonte_eta_label = _fmt_fonte_eta(eta_info.get('fonte_eta'))

                    # ETA: ShipsGo tracking (api) > Kanban (alimentado por ShipsGo) > fallback
                    eta_raw = shipsgo.get('shipsgo_eta') or eta_info.get('eta_iso')
                    eta_txt = _fmt_eta_br(eta_raw) if eta_raw else None

                    porto_codigo = shipsgo.get('shipsgo_porto_codigo') or eta_info.get('porto_codigo') or ''
                    porto_nome = shipsgo.get('shipsgo_porto_nome') or eta_info.get('porto_nome') or ''
                    porto_txt = ''
                    if porto_codigo and porto_nome:
                        porto_txt = f'{porto_codigo} - {porto_nome}'
                    elif porto_codigo:
                        porto_txt = str(porto_codigo)
                    elif porto_nome:
                        porto_txt = str(porto_nome)

                    navio = shipsgo.get('shipsgo_navio') or eta_info.get('nome_navio') or ''
                    status = shipsgo.get('shipsgo_status') or eta_info.get('status_shipsgo') or ''

                    ce = proc.get('ce') or {}
                    ce_num = ce.get('numero')
                    ce_situ = ce.get('situacao')

                    partes = [f"- **{proc_ref}**"]
                    if eta_txt:
                        if fonte_eta_label:
                            partes.append(f"ETA {eta_txt} ({fonte_eta_label})")
                        else:
                            partes.append(f"ETA {eta_txt}")
                    if porto_txt:
                        partes.append(porto_txt)
                    if navio:
                        partes.append(f"Navio {navio}")
                    if status:
                        partes.append(f"Status: {status}")
                    if ce_num:
                        if ce_situ:
                            partes.append(f"CE {ce_num} ({ce_situ})")
                        else:
                            partes.append(f"CE {ce_num}")

                    resposta += " – ".join(partes) + "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'filtro_data': filtro_data,
                'categoria': categoria,
                'dados': processos
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos por ETA: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos por ETA: {str(e)}',
                'mensagem': f'Erro ao buscar processos por ETA: {str(e)}'
            }
    
    def listar_processos_por_categoria(
        self,
        categoria: str,
        limite: int = 200,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista processos de uma categoria específica.
        
        Args:
            categoria: Categoria do processo (ex: 'ALH', 'VDM', 'MV5')
            limite: Limite de resultados
            mensagem_original: Mensagem original do usuário (para contexto)
        
        Returns:
            Dict com 'sucesso', 'resposta', 'total', 'categoria', 'dados'
        """
        try:
            from services.agents.processo_agent import ProcessoAgent
            
            processo_agent = ProcessoAgent()
            resultado = processo_agent._listar_por_categoria({
                'categoria': categoria,
                'limite': limite
            }, context={'mensagem_original': mensagem_original})
            
            return resultado
        except Exception as e:
            logger.error(f'Erro ao listar processos por categoria: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos da categoria {categoria}: {str(e)}',
                'mensagem': f'Erro ao buscar processos da categoria {categoria}: {str(e)}'
            }
    
    def listar_processos_por_situacao(
        self,
        categoria: Optional[str] = None,
        situacao: Optional[str] = None,
        limite: int = 200,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista processos por situação.
        
        Args:
            categoria: Categoria do processo (opcional)
            situacao: Situação do processo (opcional)
            limite: Limite de resultados
            mensagem_original: Mensagem original do usuário (para contexto)
        
        Returns:
            Dict com 'sucesso', 'resposta', 'total', 'categoria', 'situacao', 'dados'
        """
        try:
            from services.agents.processo_agent import ProcessoAgent
            
            processo_agent = ProcessoAgent()
            resultado = processo_agent._listar_por_situacao({
                'categoria': categoria,
                'situacao': situacao,
                'limite': limite
            }, context={'mensagem_original': mensagem_original})
            
            return resultado
        except Exception as e:
            logger.error(f'Erro ao listar processos por situação: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos: {str(e)}',
                'mensagem': f'Erro ao buscar processos: {str(e)}'
            }
    
    def listar_processos_com_pendencias(
        self,
        categoria: Optional[str] = None,
        limite: int = 200,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista processos com pendências.
        
        Args:
            categoria: Categoria do processo (opcional)
            limite: Limite de resultados
            mensagem_original: Mensagem original do usuário (para contexto)
        
        Returns:
            Dict com 'sucesso', 'resposta', 'total', 'categoria', 'dados'
        """
        try:
            from services.agents.processo_agent import ProcessoAgent
            
            processo_agent = ProcessoAgent()
            resultado = processo_agent._listar_com_pendencias({
                'categoria': categoria,
                'limite': limite
            }, context={'mensagem_original': mensagem_original})
            
            return resultado
        except Exception as e:
            logger.error(f'Erro ao listar processos com pendências: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos com pendências: {str(e)}',
                'mensagem': f'Erro ao buscar processos com pendências: {str(e)}'
            }
    
    def listar_todos_processos_por_situacao(
        self,
        situacao: Optional[str] = None,
        filtro_pendencias: bool = False,
        filtro_bloqueio: bool = False,
        filtro_data_desembaraco: Optional[str] = None,
        limite: int = 500,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Lista todos os processos por situação.
        
        Args:
            situacao: Situação do processo (opcional)
            filtro_pendencias: Filtrar apenas processos com pendências
            filtro_bloqueio: Filtrar apenas processos com bloqueios
            filtro_data_desembaraco: Filtro de data de desembaraço (opcional)
            limite: Limite de resultados
            mensagem_original: Mensagem original do usuário (para contexto)
        
        Returns:
            Dict com 'sucesso', 'resposta', 'total', 'situacao', 'dados'
        """
        try:
            from services.agents.processo_agent import ProcessoAgent
            
            processo_agent = ProcessoAgent()
            resultado = processo_agent._listar_todos_por_situacao({
                'situacao': situacao,
                'filtro_pendencias': filtro_pendencias,
                'filtro_bloqueio': filtro_bloqueio,
                'filtro_data_desembaraco': filtro_data_desembaraco,
                'limite': limite
            }, context={'mensagem_original': mensagem_original})
            
            return resultado
        except Exception as e:
            logger.error(f'Erro ao listar todos os processos por situação: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos: {str(e)}',
                'mensagem': f'Erro ao buscar processos: {str(e)}'
            }
    
    def listar_processos(
        self,
        status: Optional[str] = None,
        limite: int = 20
    ) -> Dict[str, Any]:
        """
        Lista processos de importação.
        
        Args:
            status: Status do processo (opcional)
            limite: Limite de resultados
        
        Returns:
            Dict com 'sucesso', 'resposta', 'processos'
        """
        try:
            from services.agents.processo_agent import ProcessoAgent
            
            processo_agent = ProcessoAgent()
            resultado = processo_agent._listar_processos({
                'status': status,
                'limite': limite
            })
            
            return resultado
        except Exception as e:
            logger.error(f'Erro ao listar processos: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao listar processos: {str(e)}',
                'mensagem': f'Erro ao listar processos: {str(e)}'
            }
    
    def listar_processos_com_situacao_ce(
        self,
        situacao_filtro: Optional[str] = None,
        limite: int = 50
    ) -> Dict[str, Any]:
        """
        Lista processos com situação de CE.
        
        Args:
            situacao_filtro: Situação do CE para filtrar (opcional)
            limite: Limite de resultados
        
        Returns:
            Dict com 'sucesso', 'resposta', 'total', 'dados'
        """
        try:
            from db_manager import listar_processos_com_situacao_ce
            
            processos = listar_processos_com_situacao_ce(situacao_filtro=situacao_filtro, limit=limite)
            
            if not processos:
                resposta = f"✅ **Nenhum processo encontrado"
                if situacao_filtro:
                    resposta += f" com situação de CE '{situacao_filtro}'"
                resposta += ".**"
            else:
                resposta = f"📋 **Processos com situação de CE"
                if situacao_filtro:
                    resposta += f" '{situacao_filtro}'"
                resposta += f"** ({len(processos)} processo(s))\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    ce_numero = proc.get('ce_numero', '')
                    ce_situacao = proc.get('ce_situacao', '')
                    resposta += f"**{proc_ref}**\n"
                    resposta += f"   📦 CE {ce_numero}: {ce_situacao}\n\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'dados': processos
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos com situação de CE: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos: {str(e)}',
                'mensagem': f'Erro ao buscar processos: {str(e)}'
            }
    
    def listar_processos_com_duimp(
        self,
        limite: int = 50
    ) -> Dict[str, Any]:
        """
        Lista processos que têm DUIMP.
        
        Args:
            limite: Limite de resultados
        
        Returns:
            Dict com 'sucesso', 'resposta', 'total', 'dados'
        """
        try:
            from db_manager import listar_processos_com_duimp
            
            processos = listar_processos_com_duimp(limit=limite)
            
            if not processos:
                resposta = "✅ **Nenhum processo com DUIMP encontrado.**"
            else:
                resposta = f"📋 **Processos com DUIMP** ({len(processos)} processo(s))\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    duimp_num = proc.get('duimp_numero', '')
                    duimp_versao = proc.get('duimp_versao', '')
                    duimp_situacao = proc.get('duimp_situacao', '')
                    resposta += f"**{proc_ref}**\n"
                    resposta += f"   📝 DUIMP {duimp_num} v{duimp_versao}: {duimp_situacao}\n\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'dados': processos
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos com DUIMP: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos: {str(e)}',
                'mensagem': f'Erro ao buscar processos: {str(e)}'
            }
