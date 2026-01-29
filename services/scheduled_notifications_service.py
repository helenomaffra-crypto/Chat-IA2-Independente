"""
Serviço para criar notificações agendadas (resumos diários, lembretes, etc.).
"""
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, time, timedelta
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from db_manager import obter_pendencias_ativas
from services.notificacao_service import NotificacaoService

logger = logging.getLogger(__name__)


class ScheduledNotificationsService:
    """Serviço para criar notificações agendadas"""
    
    def __init__(self):
        """Inicializa o serviço de notificações agendadas"""
        self.scheduler = BackgroundScheduler()
        self.notificacao_service = NotificacaoService()
        self._configurar_agendamentos()
    
    def _configurar_agendamentos(self):
        """Configura os agendamentos de notificações"""
        # Resumo diário - 08:00 todos os dias
        self.scheduler.add_job(
            func=self._criar_resumo_diario,
            trigger=CronTrigger(hour=8, minute=0),
            id='resumo_diario_08h',
            name='Resumo Diário - 08:00',
            replace_existing=True
        )
        
        # Resumo diário - 14:00 todos os dias
        self.scheduler.add_job(
            func=self._criar_resumo_diario,
            trigger=CronTrigger(hour=14, minute=0),
            id='resumo_diario_14h',
            name='Resumo Diário - 14:00',
            replace_existing=True
        )
        
        # Resumo diário - 17:00 todos os dias
        self.scheduler.add_job(
            func=self._criar_resumo_diario,
            trigger=CronTrigger(hour=17, minute=0),
            id='resumo_diario_17h',
            name='Resumo Diário - 17:00',
            replace_existing=True
        )
        
        # Lembrete de pendências críticas - 10:00 todos os dias
        self.scheduler.add_job(
            func=self._criar_lembrete_pendencias_criticas,
            trigger=CronTrigger(hour=10, minute=0),
            id='lembrete_pendencias_10h',
            name='Lembrete Pendências Críticas - 10:00',
            replace_existing=True
        )
        
        # Lembrete de pendências críticas - 15:00 todos os dias
        self.scheduler.add_job(
            func=self._criar_lembrete_pendencias_criticas,
            trigger=CronTrigger(hour=15, minute=0),
            id='lembrete_pendencias_15h',
            name='Lembrete Pendências Críticas - 15:00',
            replace_existing=True
        )
        
        # Lembrete de processos chegando hoje - 09:00 todos os dias
        self.scheduler.add_job(
            func=self._criar_lembrete_processos_chegando_hoje,
            trigger=CronTrigger(hour=9, minute=0),
            id='lembrete_chegando_09h',
            name='Lembrete Processos Chegando Hoje - 09:00',
            replace_existing=True
        )
        
        # Lembrete de processos prontos para registro - 11:00 todos os dias
        self.scheduler.add_job(
            func=self._criar_lembrete_processos_prontos_registro,
            trigger=CronTrigger(hour=11, minute=0),
            id='lembrete_prontos_11h',
            name='Lembrete Processos Prontos - 11:00',
            replace_existing=True
        )
        
        # ✅ NOVO (17/01/2026): Verificar feeds RSS do Siscomex a cada 2 horas
        self.scheduler.add_job(
            func=self._verificar_feeds_rss_siscomex,
            trigger=IntervalTrigger(hours=2),
            id='rss_siscomex_2h',
            name='Verificar Feeds RSS Siscomex',
            replace_existing=True
        )

        # ✅ NOVO (19/01/2026): Monitoramento de ocorrências (navio em atraso + SLA por etapa)
        self.scheduler.add_job(
            func=self._rodar_monitoramento_ocorrencias,
            trigger=IntervalTrigger(minutes=int(os.getenv("MONITORAMENTO_INTERVAL_MINUTES", "15"))),
            id='monitoramento_ocorrencias',
            name='Monitoramento Ocorrências (Navio/SLA)',
            replace_existing=True
        )

        # ✅ NOVO (22/01/2026): Limpeza automática do cache de áudio TTS
        # Evita acumular milhares de .mp3 em downloads/tts.
        self.scheduler.add_job(
            func=self._limpar_cache_tts,
            trigger=IntervalTrigger(hours=int(os.getenv("TTS_CLEANUP_INTERVAL_HOURS", "6"))),
            id='tts_cache_cleanup',
            name='Limpeza Cache TTS (downloads/tts)',
            replace_existing=True
        )

        # ✅ NOVO (23/01/2026): Limpeza opcional de comprovantes Mercante (AFRMM)
        # Por padrão é DESLIGADO para não apagar auditoria sem querer.
        if os.getenv("MERCANTE_RECEIPT_CLEANUP_ENABLED", "false").lower() == "true":
            self.scheduler.add_job(
                func=self._limpar_receipts_mercante,
                trigger=IntervalTrigger(hours=int(os.getenv("MERCANTE_RECEIPT_CLEANUP_INTERVAL_HOURS", "24"))),
                id='mercante_receipt_cleanup',
                name='Limpeza Receipts Mercante (downloads/mercante)',
                replace_existing=True
            )

        # ✅ NOVO (28/01/2026): Watch de vendas (Make/Spalla) - polling do "hoje" por termos
        if os.getenv("SALES_WATCH_ENABLED", "false").lower() == "true":
            # ⚠️ Importante:
            # - IntervalTrigger por padrão roda só depois de `interval`, então o usuário pode achar que "não funciona".
            # - Rodar logo após iniciar o scheduler permite "seedar" baseline (sem notificar) e ficar pronto.
            from datetime import datetime, timedelta
            self.scheduler.add_job(
                func=self._watch_vendas_hoje,
                trigger=IntervalTrigger(minutes=int(os.getenv("SALES_WATCH_INTERVAL_MINUTES", "15"))),
                id="sales_watch_hoje",
                name="Watch Vendas Hoje (Make/Spalla)",
                replace_existing=True,
                next_run_time=datetime.now() + timedelta(seconds=10),
                coalesce=True,
                max_instances=1,
            )
        
        logger.info("✅ Agendamentos de notificações configurados")

    def _watch_vendas_hoje(self) -> None:
        """
        Verifica vendas de hoje por termos e cria notificações quando surgir NF nova.
        """
        try:
            from services.sales_watch_service import SalesWatchService, get_watch_terms

            termos = get_watch_terms()
            if not termos:
                return

            debug = os.getenv("SALES_WATCH_DEBUG", "false").strip().lower() in {"1", "true", "yes", "y"}
            if debug:
                logger.info(f"🔎 [SALES_WATCH] Tick (termos={termos})")

            svc = SalesWatchService()
            results = svc.check_once(termos=termos)
            if not results:
                if debug:
                    logger.info("🔎 [SALES_WATCH] Tick sem novas NFs")
                return
            created = svc.notificar(results)
            if created:
                logger.info(f"💰 [SALES_WATCH] Notificações criadas: {created}")
        except Exception as e:
            logger.warning(f"⚠️ Erro no watch de vendas: {e}", exc_info=True)

    def _limpar_cache_tts(self):
        """Remove mp3 antigos/expirados do cache TTS."""
        try:
            if os.getenv("OPENAI_TTS_CACHE_ENABLED", "true").lower() != "true":
                return
            from services.tts_service import TTSService

            tts = TTSService()
            resultado = tts.limpar_cache()
            if resultado.get("removidos_expirados") or resultado.get("removidos_por_tamanho"):
                logger.info(
                    "🧹 Limpeza TTS OK: "
                    f"expirados={resultado.get('removidos_expirados')}, "
                    f"por_tamanho={resultado.get('removidos_por_tamanho')}, "
                    f"days={resultado.get('cache_days')}, "
                    f"max_files={resultado.get('cache_max_files')}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar cache TTS: {e}", exc_info=True)

    def _limpar_receipts_mercante(self) -> None:
        """
        Remove comprovantes antigos em downloads/mercante (PNG/JPG/PDF).

        ⚠️ Importante:
        - Isso pode quebrar links antigos se o arquivo for removido.
        - Por isso é controlado por feature flag MERCANTE_RECEIPT_CLEANUP_ENABLED=false (default).
        """
        try:
            base = Path("downloads") / "mercante"
            if not base.exists() or not base.is_dir():
                return

            # Retenção por idade
            days = int(os.getenv("MERCANTE_RECEIPT_RETENTION_DAYS", "365"))
            if days <= 0:
                days = 365
            cutoff = datetime.now() - timedelta(days=days)

            # Retenção por quantidade (0/negativo = desabilitado)
            max_files = int(os.getenv("MERCANTE_RECEIPT_MAX_FILES", "0"))

            allowed_ext = {".png", ".jpg", ".jpeg", ".pdf"}
            files = []
            for p in base.iterdir():
                if not p.is_file():
                    continue
                if p.suffix.lower() not in allowed_ext:
                    continue
                try:
                    mtime = datetime.fromtimestamp(p.stat().st_mtime)
                except Exception:
                    continue
                files.append((mtime, p))

            if not files:
                return

            # 1) Remover expirados por idade
            removed_age = 0
            kept = []
            for mtime, p in files:
                if mtime < cutoff:
                    try:
                        p.unlink(missing_ok=True)
                        removed_age += 1
                    except Exception:
                        kept.append((mtime, p))
                else:
                    kept.append((mtime, p))

            # 2) Se ainda excede max_files, remover os mais antigos
            removed_count = 0
            if max_files and max_files > 0 and len(kept) > max_files:
                kept.sort(key=lambda x: x[0])  # mais antigos primeiro
                to_remove = kept[: max(0, len(kept) - max_files)]
                kept2 = kept[len(to_remove) :]
                for _, p in to_remove:
                    try:
                        p.unlink(missing_ok=True)
                        removed_count += 1
                    except Exception:
                        pass
                kept = kept2

            if removed_age or removed_count:
                logger.info(
                    "🧹 Limpeza Mercante OK: "
                    f"removidos_por_idade={removed_age}, "
                    f"removidos_por_quantidade={removed_count}, "
                    f"retention_days={days}, max_files={max_files or 'off'}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Erro ao limpar receipts Mercante: {e}", exc_info=True)

    def _rodar_monitoramento_ocorrencias(self):
        """Roda monitoramento de ocorrências e gera notificações (anti-spam via ocorrencias_processos)."""
        try:
            from services.monitoramento_ocorrencias_service import get_monitoramento_ocorrencias_service
            svc = get_monitoramento_ocorrencias_service()
            resultado = svc.executar()
            logger.info(
                f"✅ Monitoramento ocorrências OK: navios_alertados={resultado.get('navios_alertados')}, "
                f"sla_alertados={resultado.get('sla_alertados')}, total_processos={resultado.get('total_processos')}"
            )
        except Exception as e:
            logger.error(f"❌ Erro no monitoramento de ocorrências: {e}", exc_info=True)
    
    def iniciar(self):
        """Inicia o scheduler"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                # ✅ NOVO (26/01/2026): Aguardar um pouco e verificar se realmente iniciou
                import time
                time.sleep(0.5)  # Aguardar scheduler iniciar
                if self.scheduler.running:
                    logger.info("✅ Scheduler de notificações agendadas iniciado")
                    # Listar jobs para debug
                    jobs = self.scheduler.get_jobs()
                    logger.info(f"   Jobs agendados: {len(jobs)}")
                    for job in jobs:
                        logger.debug(f"   - {job.id}: {job.name} (próxima: {job.next_run_time})")
                else:
                    logger.error("❌ ERRO CRÍTICO: scheduler.start() retornou mas scheduler NÃO está rodando!")
            else:
                logger.warning("⚠️ Scheduler já está rodando")
        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO ao iniciar scheduler: {e}", exc_info=True)
            raise  # Re-raise para que o app.py saiba que falhou
    
    def parar(self):
        """Para o scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✅ Scheduler de notificações agendadas parado")
    
    def _criar_resumo_diario(self):
        """Cria notificação de resumo diário"""
        try:
            logger.info("📊 Criando resumo diário...")
            
            # Buscar dados do dia
            pendencias = obter_pendencias_ativas()
            
            # Buscar processos chegando hoje
            try:
                from db_manager import obter_processos_chegando_hoje
                processos_chegando = obter_processos_chegando_hoje()
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar processos chegando hoje: {e}")
                processos_chegando = []
            
            # Buscar processos prontos para registro
            try:
                from db_manager import obter_processos_prontos_registro
                processos_prontos = obter_processos_prontos_registro()
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar processos prontos: {e}")
                processos_prontos = []
            
            # Agrupar pendências por tipo
            pendencias_por_tipo = {}
            for pend in pendencias:
                tipo = pend.get('tipo_pendencia', 'Outras')
                if tipo not in pendencias_por_tipo:
                    pendencias_por_tipo[tipo] = []
                pendencias_por_tipo[tipo].append(pend)
            
            # Formatar mensagem
            hora_atual = datetime.now().strftime('%H:%M')
            data_atual = datetime.now().strftime('%d/%m/%Y')
            
            mensagem = f"📅 **RESUMO DO DIA - {data_atual} ({hora_atual})**\n\n"
            
            # Processos chegando hoje
            if processos_chegando:
                mensagem += f"🚢 **Chegando Hoje:** {len(processos_chegando)} processo(s)\n"
                for proc in processos_chegando[:5]:  # Mostrar até 5
                    mensagem += f"   • {proc.get('processo_referencia', 'N/A')}\n"
                if len(processos_chegando) > 5:
                    mensagem += f"   ... e mais {len(processos_chegando) - 5} processo(s)\n"
                mensagem += "\n"
            else:
                mensagem += "🚢 **Chegando Hoje:** Nenhum processo\n\n"
            
            # Processos prontos para registro
            if processos_prontos:
                mensagem += f"✅ **Prontos para Registro:** {len(processos_prontos)} processo(s)\n"
                for proc in processos_prontos[:5]:  # Mostrar até 5
                    mensagem += f"   • {proc.get('processo_referencia', 'N/A')}\n"
                if len(processos_prontos) > 5:
                    mensagem += f"   ... e mais {len(processos_prontos) - 5} processo(s)\n"
                mensagem += "\n"
            else:
                mensagem += "✅ **Prontos para Registro:** Nenhum processo\n\n"
            
            # Pendências ativas
            if pendencias:
                mensagem += f"⚠️ **Pendências Ativas:** {len(pendencias)} processo(s)\n"
                for tipo, lista in pendencias_por_tipo.items():
                    mensagem += f"   **{tipo}:** {len(lista)} processo(s)\n"
                mensagem += "\n"
            else:
                mensagem += "⚠️ **Pendências Ativas:** Nenhuma pendência\n\n"
            
            mensagem += "💡 Use 'O que temos pra hoje?' para ver detalhes completos."
            
            # Criar notificação
            notificacao = {
                'processo_referencia': 'SISTEMA',
                'tipo_notificacao': 'resumo_diario',
                'titulo': f'📊 Resumo Diário - {data_atual}',
                'mensagem': mensagem,
                'dados_extras': {
                    'hora': hora_atual,
                    'data': data_atual,
                    'total_pendencias': len(pendencias),
                    'total_chegando': len(processos_chegando),
                    'total_prontos': len(processos_prontos)
                }
            }
            
            self.notificacao_service._salvar_notificacao(notificacao)
            logger.info(f"✅ Resumo diário criado: {len(pendencias)} pendências, {len(processos_chegando)} chegando, {len(processos_prontos)} prontos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar resumo diário: {e}", exc_info=True)
    
    def _criar_lembrete_pendencias_criticas(self):
        """Cria notificação de lembrete de pendências críticas"""
        try:
            logger.info("⚠️ Criando lembrete de pendências críticas...")
            
            # Buscar pendências
            pendencias = obter_pendencias_ativas()
            
            if not pendencias:
                logger.info("ℹ️ Nenhuma pendência ativa - não criando lembrete")
                return
            
            # Agrupar por tipo
            pendencias_por_tipo = {}
            for pend in pendencias:
                tipo = pend.get('tipo_pendencia', 'Outras')
                if tipo not in pendencias_por_tipo:
                    pendencias_por_tipo[tipo] = []
                pendencias_por_tipo[tipo].append(pend)
            
            # Formatar mensagem
            hora_atual = datetime.now().strftime('%H:%M')
            
            mensagem = f"⚠️ **LEMBRETE DE PENDÊNCIAS ATIVAS** ({hora_atual})\n\n"
            mensagem += f"Total: **{len(pendencias)} processo(s)** com pendências\n\n"
            
            # Listar por tipo
            for tipo, lista in sorted(pendencias_por_tipo.items()):
                mensagem += f"**{tipo}** ({len(lista)} processo(s)):\n"
                for pend in lista[:3]:  # Mostrar até 3 por tipo
                    proc_ref = pend.get('processo_referencia', 'N/A')
                    acao = pend.get('acao_sugerida', 'Verificar')
                    mensagem += f"   • {proc_ref} - {acao}\n"
                if len(lista) > 3:
                    mensagem += f"   ... e mais {len(lista) - 3} processo(s)\n"
                mensagem += "\n"
            
            mensagem += "💡 Use 'O que temos pra hoje?' para ver todas as pendências."
            
            # Criar notificação
            notificacao = {
                'processo_referencia': 'SISTEMA',
                'tipo_notificacao': 'lembrete_pendencias',
                'titulo': f'⚠️ Lembrete: {len(pendencias)} Pendência(s) Ativa(s)',
                'mensagem': mensagem,
                'dados_extras': {
                    'hora': hora_atual,
                    'total_pendencias': len(pendencias),
                    'pendencias_por_tipo': {tipo: len(lista) for tipo, lista in pendencias_por_tipo.items()}
                }
            }
            
            self.notificacao_service._salvar_notificacao(notificacao)
            logger.info(f"✅ Lembrete de pendências criado: {len(pendencias)} pendências")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar lembrete de pendências: {e}", exc_info=True)
    
    def _criar_lembrete_processos_chegando_hoje(self):
        """Cria notificação de lembrete de processos chegando hoje"""
        try:
            logger.info("🚢 Criando lembrete de processos chegando hoje...")
            
            # Buscar processos chegando hoje
            try:
                from db_manager import obter_processos_chegando_hoje
                processos_chegando = obter_processos_chegando_hoje()
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar processos chegando hoje: {e}")
                processos_chegando = []
            
            if not processos_chegando:
                logger.info("ℹ️ Nenhum processo chegando hoje - não criando lembrete")
                return
            
            # Formatar mensagem
            hora_atual = datetime.now().strftime('%H:%M')
            data_atual = datetime.now().strftime('%d/%m/%Y')
            
            mensagem = f"🚢 **PROCESSOS CHEGANDO HOJE** ({data_atual} - {hora_atual})\n\n"
            mensagem += f"Total: **{len(processos_chegando)} processo(s)**\n\n"
            
            # Agrupar por categoria
            processos_por_categoria = {}
            for proc in processos_chegando:
                categoria = proc.get('processo_referencia', '').split('.')[0] if '.' in proc.get('processo_referencia', '') else 'OUTROS'
                if categoria not in processos_por_categoria:
                    processos_por_categoria[categoria] = []
                processos_por_categoria[categoria].append(proc)
            
            # Listar por categoria
            for categoria in sorted(processos_por_categoria.keys()):
                processos_cat = processos_por_categoria[categoria]
                mensagem += f"**{categoria}** ({len(processos_cat)} processo(s)):\n"
                for proc in processos_cat[:5]:  # Mostrar até 5 por categoria
                    proc_ref = proc.get('processo_referencia', 'N/A')
                    eta = proc.get('eta_iso')
                    if eta:
                        try:
                            if isinstance(eta, str):
                                from dateutil import parser
                                eta = parser.parse(eta)
                            eta_str = eta.strftime('%d/%m/%Y %H:%M')
                            mensagem += f"   • {proc_ref} - ETA: {eta_str}\n"
                        except:
                            mensagem += f"   • {proc_ref}\n"
                    else:
                        mensagem += f"   • {proc_ref}\n"
                if len(processos_cat) > 5:
                    mensagem += f"   ... e mais {len(processos_cat) - 5} processo(s)\n"
                mensagem += "\n"
            
            mensagem += "💡 Verifique se os processos precisam de registro de DI/DUIMP."
            
            # Criar notificação
            notificacao = {
                'processo_referencia': 'SISTEMA',
                'tipo_notificacao': 'lembrete_chegando',
                'titulo': f'🚢 {len(processos_chegando)} Processo(s) Chegando Hoje',
                'mensagem': mensagem,
                'dados_extras': {
                    'hora': hora_atual,
                    'data': data_atual,
                    'total_processos': len(processos_chegando)
                }
            }
            
            self.notificacao_service._salvar_notificacao(notificacao)
            logger.info(f"✅ Lembrete de processos chegando criado: {len(processos_chegando)} processos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar lembrete de processos chegando: {e}", exc_info=True)
    
    def _criar_lembrete_processos_prontos_registro(self):
        """Cria notificação de lembrete de processos prontos para registro"""
        try:
            logger.info("✅ Criando lembrete de processos prontos para registro...")
            
            # Buscar processos prontos
            try:
                from db_manager import obter_processos_prontos_registro
                processos_prontos = obter_processos_prontos_registro()
            except Exception as e:
                logger.warning(f"⚠️ Erro ao buscar processos prontos: {e}")
                processos_prontos = []
            
            if not processos_prontos:
                logger.info("ℹ️ Nenhum processo pronto para registro - não criando lembrete")
                return
            
            # Formatar mensagem
            hora_atual = datetime.now().strftime('%H:%M')
            data_atual = datetime.now().strftime('%d/%m/%Y')
            
            mensagem = f"✅ **PROCESSOS PRONTOS PARA REGISTRO** ({data_atual} - {hora_atual})\n\n"
            mensagem += f"Total: **{len(processos_prontos)} processo(s)**\n\n"
            
            # Agrupar por categoria
            processos_por_categoria = {}
            processos_com_atraso = []
            
            hoje = datetime.now().date()
            
            for proc in processos_prontos:
                categoria = proc.get('processo_referencia', '').split('.')[0] if '.' in proc.get('processo_referencia', '') else 'OUTROS'
                if categoria not in processos_por_categoria:
                    processos_por_categoria[categoria] = []
                processos_por_categoria[categoria].append(proc)
                
                # Verificar atraso
                data_chegada = proc.get('data_destino_final')
                if data_chegada:
                    try:
                        if isinstance(data_chegada, str):
                            from dateutil import parser
                            data_chegada = parser.parse(data_chegada).date()
                        elif isinstance(data_chegada, datetime):
                            data_chegada = data_chegada.date()
                        
                        dias_atraso = (hoje - data_chegada).days
                        if dias_atraso > 7:
                            processos_com_atraso.append({
                                'processo': proc,
                                'dias_atraso': dias_atraso
                            })
                    except:
                        pass
            
            # Mostrar processos com atraso crítico primeiro
            if processos_com_atraso:
                mensagem += f"🚨 **ATRASO CRÍTICO** ({len(processos_com_atraso)} processo(s) - mais de 7 dias):\n"
                for item in processos_com_atraso[:5]:
                    proc_ref = item['processo'].get('processo_referencia', 'N/A')
                    dias = item['dias_atraso']
                    mensagem += f"   • {proc_ref} - ⚠️ {dias} dia(s) de atraso\n"
                if len(processos_com_atraso) > 5:
                    mensagem += f"   ... e mais {len(processos_com_atraso) - 5} processo(s)\n"
                mensagem += "\n"
            
            # Listar por categoria
            for categoria in sorted(processos_por_categoria.keys()):
                processos_cat = processos_por_categoria[categoria]
                mensagem += f"**{categoria}** ({len(processos_cat)} processo(s)):\n"
                for proc in processos_cat[:5]:  # Mostrar até 5 por categoria
                    proc_ref = proc.get('processo_referencia', 'N/A')
                    mensagem += f"   • {proc_ref}\n"
                if len(processos_cat) > 5:
                    mensagem += f"   ... e mais {len(processos_cat) - 5} processo(s)\n"
                mensagem += "\n"
            
            mensagem += "💡 Registre DI ou DUIMP para estes processos."
            
            # Criar notificação
            notificacao = {
                'processo_referencia': 'SISTEMA',
                'tipo_notificacao': 'lembrete_prontos',
                'titulo': f'✅ {len(processos_prontos)} Processo(s) Pronto(s) para Registro',
                'mensagem': mensagem,
                'dados_extras': {
                    'hora': hora_atual,
                    'data': data_atual,
                    'total_processos': len(processos_prontos),
                    'processos_com_atraso': len(processos_com_atraso)
                }
            }
            
            self.notificacao_service._salvar_notificacao(notificacao)
            logger.info(f"✅ Lembrete de processos prontos criado: {len(processos_prontos)} processos")
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar lembrete de processos prontos: {e}", exc_info=True)
    
    def _verificar_feeds_rss_siscomex(self):
        """Verifica feeds RSS do Siscomex e cria notificações para novas notícias"""
        try:
            logger.info("📰 Verificando feeds RSS do Siscomex...")
            
            from services.rss_siscomex_service import RssSiscomexService
            
            rss_service = RssSiscomexService()
            estatisticas = rss_service.processar_novas_noticias()
            
            logger.info(
                f"✅ Feeds RSS processados: "
                f"{estatisticas['feeds_processados']} feeds, "
                f"{estatisticas['noticias_novas']} novas, "
                f"{estatisticas['notificacoes_criadas']} notificações criadas"
            )
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar feeds RSS do Siscomex: {e}", exc_info=True)

