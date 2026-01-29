"""
Serviço para detectar mudanças em processos e criar notificações.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from db_manager import get_db_connection
from services.models.processo_kanban_dto import ProcessoKanbanDTO

logger = logging.getLogger(__name__)


class NotificacaoService:
    """Serviço para criar notificações de mudanças em processos"""
    
    def detectar_mudancas_e_notificar(self, processo_anterior: Optional[Dict], processo_novo: Dict) -> List[Dict]:
        """
        Detecta mudanças entre versão anterior e nova do processo e cria notificações.
        
        Args:
            processo_anterior: DTO ou dict da versão anterior (None se é novo processo)
            processo_novo: DTO ou dict da versão nova
            
        Returns:
            Lista de notificações criadas
        """
        notificacoes = []
        
        try:
            # Converter para DTO se necessário
            if isinstance(processo_novo, dict):
                dto_novo = ProcessoKanbanDTO.from_kanban_json(processo_novo)
            else:
                dto_novo = processo_novo
            
            # ✅ CORREÇÃO CRÍTICA: Não criar notificações para processos finalizados/entregues
            # Processos entregues não precisam de notificações de mudanças
            if self._processo_entregue(dto_novo):
                logger.debug(f"ℹ️ Processo {dto_novo.processo_referencia} está ENTREGUE - não criar notificações")
                return notificacoes
            
            # ✅ CORREÇÃO CRÍTICA: Não criar notificações para processos muito antigos sem documentos
            # Processos antigos sem documentos/ETA futuro não são processos ativos
            processo_ref = dto_novo.processo_referencia
            if processo_ref:
                # Verificar se é processo antigo (ano 2024 ou anterior, ou processo muito antigo sem atividade recente)
                try:
                    # Extrair ano do processo (formato: CATEGORIA.NUMERO/AA)
                    partes = processo_ref.split('/')
                    if len(partes) == 2:
                        ano = partes[1]
                        if ano and len(ano) == 2:
                            # Converter para ano completo (assumir 20XX)
                            ano_completo = 2000 + int(ano)
                            from datetime import datetime
                            ano_atual = datetime.now().year
                            
                            # Se processo é de 2024 ou anterior E não tem documentos nem ETA futuro, não criar notificações
                            if ano_completo < ano_atual:
                                tem_documentos = bool(
                                    dto_novo.numero_ce or 
                                    (dto_novo.numero_di and dto_novo.numero_di not in ('', '/       -')) or 
                                    dto_novo.numero_duimp
                                )
                                tem_eta_futuro = False
                                if dto_novo.eta_iso:
                                    try:
                                        # Tentar parsear ETA de diferentes formas
                                        eta_str = str(dto_novo.eta_iso)
                                        if 'T' in eta_str:
                                            eta_date = datetime.fromisoformat(eta_str.replace('Z', '').split('+')[0].split('.')[0])
                                        else:
                                            # Tentar formato YYYY-MM-DD
                                            eta_date = datetime.strptime(eta_str.split(' ')[0], '%Y-%m-%d')
                                        
                                        if eta_date.date() >= datetime.now().date():
                                            tem_eta_futuro = True
                                    except:
                                        pass
                                
                                # Se não tem documentos nem ETA futuro, é processo antigo inativo
                                if not tem_documentos and not tem_eta_futuro:
                                    logger.debug(f"ℹ️ Processo {processo_ref} é antigo ({ano_completo}) e inativo - não criar notificações")
                                    return notificacoes
                except Exception as e:
                    logger.debug(f"Erro ao verificar se processo é antigo: {e}")
            
            if processo_anterior is None:
                # Processo novo - não criar notificações ainda
                logger.debug(f"ℹ️ Processo {dto_novo.processo_referencia} é novo (sem versão anterior) - não criar notificações")
                return notificacoes
            
            # ✅ CORREÇÃO CRÍTICA: Converter anterior para DTO se necessário
            # Se não conseguir converter, NÃO criar notificações (evita notificações falsas)
            dto_anterior = None
            if isinstance(processo_anterior, dict):
                try:
                    dto_anterior = ProcessoKanbanDTO.from_kanban_json(processo_anterior)
                    # Verificar se o DTO anterior tem dados válidos (não está vazio)
                    if not dto_anterior.processo_referencia:
                        logger.debug(f"ℹ️ Processo anterior {dto_novo.processo_referencia} está vazio - não criar notificações")
                        return notificacoes
                except Exception as e:
                    # Se falhar ao converter, NÃO criar notificações (evita notificações falsas)
                    logger.debug(f"ℹ️ Erro ao converter processo anterior {dto_novo.processo_referencia}: {e} - não criar notificações")
                    return notificacoes
            elif isinstance(processo_anterior, ProcessoKanbanDTO):
                dto_anterior = processo_anterior
                # Verificar se o DTO anterior tem dados válidos
                if not dto_anterior.processo_referencia:
                    logger.debug(f"ℹ️ Processo anterior {dto_novo.processo_referencia} está vazio - não criar notificações")
                    return notificacoes
            else:
                # Se não for dict nem DTO, NÃO criar notificações
                logger.debug(f"ℹ️ Processo anterior {dto_novo.processo_referencia} tem tipo inválido - não criar notificações")
                return notificacoes
            
            # ✅ CORREÇÃO CRÍTICA: Verificar se o processo anterior é realmente diferente do novo
            # Se os dados principais são idênticos, não criar notificações (evita duplicatas)
            if (dto_anterior.situacao_ce == dto_novo.situacao_ce and
                dto_anterior.situacao_di == dto_novo.situacao_di and
                dto_anterior.situacao_entrega == dto_novo.situacao_entrega and
                dto_anterior.data_destino_final == dto_novo.data_destino_final and
                dto_anterior.eta_iso == dto_novo.eta_iso):
                # Verificar também se AFRMM mudou (pode estar nos dados_completos)
                afrmm_anterior = self._extrair_afrmm_paga(dto_anterior.dados_completos)
                afrmm_novo = self._extrair_afrmm_paga(dto_novo.dados_completos)
                if afrmm_anterior == afrmm_novo:
                    logger.debug(f"ℹ️ Processo {dto_novo.processo_referencia} não teve mudanças reais - não criar notificações")
                    return notificacoes
            
            processo_ref = dto_novo.processo_referencia
            
            # 1. Chegada confirmada (dataDestinoFinal preenchida)
            if self._chegada_confirmada(dto_anterior, dto_novo):
                notif = self._criar_notificacao_chegada(dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # 2. Mudança de status da DI
            if self._status_di_mudou(dto_anterior, dto_novo):
                notif = self._criar_notificacao_status_di(dto_anterior, dto_novo)
                if notif:
                    notificacoes.append(notif)
                
                # ✅ NOVO: Se DI desembaraçou, criar notificação especial de pagamentos
                if self._di_desembaracou(dto_anterior, dto_novo):
                    notif_pagamento = self._criar_notificacao_pagamentos_necessarios(dto_novo, tipo_documento='DI')
                    if notif_pagamento:
                        notificacoes.append(notif_pagamento)
                    
                    # ✅ NOVO (23/01/2026): Criar sugestão de vinculação bancária automática
                    try:
                        self._criar_sugestao_vinculacao_bancaria(dto_novo, tipo_documento='DI')
                    except Exception as e:
                        logger.error(f"❌ Erro ao criar sugestão de vinculação bancária: {e}", exc_info=True)
            
            # 3. Mudança de status da DUIMP
            if self._status_duimp_mudou(dto_anterior, dto_novo):
                notif = self._criar_notificacao_status_duimp(dto_anterior, dto_novo)
                if notif:
                    notificacoes.append(notif)
                
                # ✅ NOVO: Se DUIMP desembaraçou, criar notificação especial de pagamentos
                if self._duimp_desembaracou(dto_anterior, dto_novo):
                    notif_pagamento = self._criar_notificacao_pagamentos_necessarios(dto_novo, tipo_documento='DUIMP')
                    if notif_pagamento:
                        notificacoes.append(notif_pagamento)
                    
                    # ✅ NOVO (23/01/2026): Criar sugestão de vinculação bancária automática
                    try:
                        self._criar_sugestao_vinculacao_bancaria(dto_novo, tipo_documento='DUIMP')
                    except Exception as e:
                        logger.error(f"❌ Erro ao criar sugestão de vinculação bancária: {e}", exc_info=True)
            
            # 3.5. Mudança de status do CE (ex: MANIFESTADO, ARMAZENADO, etc)
            if self._status_ce_mudou(dto_anterior, dto_novo):
                notif = self._criar_notificacao_status_ce(dto_anterior, dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # 4. Pagamento AFRMM
            if self._afrmm_pago(dto_anterior, dto_novo):
                notif = self._criar_notificacao_afrmm(dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # 5. Pendência de ICMS resolvida (verificação específica)
            if self._icms_pago(dto_anterior, dto_novo):
                notif = self._criar_notificacao_icms_pago(dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # 6. Pendência resolvida (geral)
            if self._pendencias_resolvidas(dto_anterior, dto_novo):
                notif = self._criar_notificacao_pendencia_resolvida(dto_anterior, dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # 7. Pendência de frete resolvida
            if self._frete_pago(dto_anterior, dto_novo):
                notif = self._criar_notificacao_frete_pago(dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # 8. Mudança de status do LPCO
            if self._status_lpco_mudou(dto_anterior, dto_novo):
                notif = self._criar_notificacao_status_lpco(dto_anterior, dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # 9. Mudança de ETA (Estimated Time of Arrival)
            if self._eta_mudou(dto_anterior, dto_novo):
                notif = self._criar_notificacao_eta_mudou(dto_anterior, dto_novo)
                if notif:
                    notificacoes.append(notif)
            
            # ✅ NOVO: Salvar histórico de mudanças (apenas campos que mudaram) ANTES de salvar notificações
            if notificacoes:
                self._salvar_historico_mudancas(dto_anterior, dto_novo, notificacoes)
            
            # Salvar notificações no banco
            for notif in notificacoes:
                self._salvar_notificacao(notif)
            
            if notificacoes:
                logger.info(f"🔔 {len(notificacoes)} notificação(ões) criada(s) para {processo_ref}")
                for notif in notificacoes:
                    logger.debug(f"   - {notif.get('tipo_notificacao')}: {notif.get('titulo')}")
            else:
                logger.debug(f"ℹ️ Nenhuma mudança detectada para {processo_ref}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao detectar mudanças: {e}", exc_info=True)
        
        return notificacoes
    
    def _chegada_confirmada(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se chegada foi confirmada (dataDestinoFinal preenchida)"""
        return (
            not dto_anterior.data_destino_final and 
            dto_novo.data_destino_final is not None
        )
    
    def _status_di_mudou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se status da DI mudou"""
        return (
            dto_anterior.situacao_di != dto_novo.situacao_di and
            dto_novo.situacao_di is not None
        )
    
    def _status_duimp_mudou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se status da DUIMP mudou (via dados_completos)"""
        # DUIMP status está em dados_completos.duimp[].situacao
        duimp_anterior = self._extrair_status_duimp(dto_anterior.dados_completos)
        duimp_novo = self._extrair_status_duimp(dto_novo.dados_completos)
        
        # ✅ CORREÇÃO: Se anterior é None e novo não é None, também é mudança (processo novo com DUIMP)
        if duimp_anterior is None and duimp_novo is not None:
            return True
        
        return duimp_anterior != duimp_novo and duimp_novo is not None
    
    def _status_ce_mudou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se status do CE mudou (ex: MANIFESTADO, ARMAZENADO, etc)"""
        # Buscar status do CE em múltiplos lugares
        ce_anterior = self._extrair_status_ce(dto_anterior)
        ce_novo = self._extrair_status_ce(dto_novo)
        
        # Normalizar valores None/vazio para comparação
        ce_anterior_normalizado = (ce_anterior or '').strip() if ce_anterior else ''
        ce_novo_normalizado = (ce_novo or '').strip() if ce_novo else ''
        
        # Só criar notificação se mudou E novo não é vazio
        # Importante: detectar mudança de None/vazio para um status válido
        mudou = ce_anterior_normalizado != ce_novo_normalizado
        novo_valido = ce_novo_normalizado != ''
        
        if mudou and novo_valido:
            logger.debug(f"🔍 Status CE mudou para {dto_novo.processo_referencia}: '{ce_anterior_normalizado}' → '{ce_novo_normalizado}'")
        
        return mudou and novo_valido
    
    def _extrair_status_ce(self, dto: ProcessoKanbanDTO) -> Optional[str]:
        """Extrai status do CE de múltiplos lugares"""
        # Tentar do DTO primeiro
        if dto.situacao_ce:
            return dto.situacao_ce
        
        # Tentar dos dados completos
        dados = dto.dados_completos or {}
        situacao = dados.get('situacaoCargaCe') or dados.get('situacao_ce')
        
        # Se ainda não encontrou, tentar em containerDetailsCe (array de containers)
        if not situacao:
            container_details = dados.get('containerDetailsCe', [])
            if container_details and isinstance(container_details, list) and len(container_details) > 0:
                # Pegar situação do primeiro container (geralmente todos têm a mesma)
                primeiro_container = container_details[0]
                if isinstance(primeiro_container, dict):
                    situacao = primeiro_container.get('situacao') or primeiro_container.get('operacao')
        
        return situacao
    
    def _status_lpco_mudou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se status do LPCO mudou (ex: Deferido, Indeferido)"""
        # Comparar situação do LPCO
        lpco_anterior = dto_anterior.situacao_lpco
        lpco_novo = dto_novo.situacao_lpco
        
        # Só criar notificação se mudou E novo não é None/vazio
        return (
            lpco_anterior != lpco_novo and 
            lpco_novo is not None and 
            str(lpco_novo).strip() != ''
        )
    
    def _eta_mudou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se ETA (Estimated Time of Arrival) mudou"""
        eta_anterior = dto_anterior.eta_iso
        eta_novo = dto_novo.eta_iso
        
        # Se ambos são None, não há mudança
        if eta_anterior is None and eta_novo is None:
            return False
        
        # Se um é None e outro não, há mudança
        if (eta_anterior is None) != (eta_novo is None):
            return True
        
        # Se ambos existem, comparar as datas
        if eta_anterior and eta_novo:
            # Considerar mudança se a diferença for maior que 1 hora
            # (para evitar notificações por pequenas variações)
            from datetime import timedelta
            diferenca = abs((eta_novo - eta_anterior).total_seconds())
            return diferenca > 3600  # Mais de 1 hora de diferença
        
        return False
    
    def _afrmm_pago(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se AFRMM foi pago"""
        afrmm_anterior = self._extrair_afrmm_paga(dto_anterior.dados_completos)
        afrmm_novo = self._extrair_afrmm_paga(dto_novo.dados_completos)
        return not afrmm_anterior and afrmm_novo
    
    def _icms_pago(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se pendência de ICMS foi resolvida"""
        # Verificar se ICMS mudou de "Pendente" para None/False/vazio/OK
        icms_anterior = dto_anterior.pendencia_icms
        icms_novo = dto_novo.pendencia_icms
        
        # Se anterior era "Pendente" e novo não é mais (pode ser None, False, "OK", etc)
        icms_era_pendente = (
            icms_anterior and 
            str(icms_anterior).upper() in ['PENDENTE', 'PENDENTE', 'TRUE', '1', 'SIM']
        )
        
        # Novo não é mais pendente se for None, False, "OK", vazio, etc
        icms_nao_e_mais_pendente = (
            not icms_novo or 
            str(icms_novo).upper() not in ['PENDENTE', 'PENDENTE', 'TRUE', '1', 'SIM']
        )
        
        # ✅ CORREÇÃO: Criar notificação mesmo se processo está ENTREGUE
        # (usuário quer saber quando pendências são resolvidas, mesmo em processos finalizados)
        # Mas vamos adicionar uma nota na mensagem se estiver ENTREGUE
        
        resultado = icms_era_pendente and icms_nao_e_mais_pendente
        if resultado:
            logger.info(f"✅ ICMS pago detectado para {dto_novo.processo_referencia}: {icms_anterior} → {icms_novo}")
        
        return resultado
    
    def _pendencias_resolvidas(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se pendências foram resolvidas"""
        # ✅ CORREÇÃO: Criar notificação mesmo se ENTREGUE (usuário quer saber)
        return (
            dto_anterior.tem_pendencias and 
            not dto_novo.tem_pendencias
        )
    
    def _frete_pago(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se pendência de frete foi resolvida"""
        # ✅ CORREÇÃO: Criar notificação mesmo se ENTREGUE (usuário quer saber)
        return (
            dto_anterior.pendencia_frete and 
            not dto_novo.pendencia_frete
        )
    
    def _processo_entregue(self, dto: ProcessoKanbanDTO) -> bool:
        """Verifica se processo está com CE/CCT ENTREGUE (não precisa de notificações de pendências)"""
        situacao_ce = (dto.situacao_ce or '').upper()
        situacao_entrega = (dto.situacao_entrega or '').upper()
        
        # Verificar também nos dados completos
        dados = dto.dados_completos or {}
        situacao_ce_dados = (dados.get('situacaoCargaCe') or dados.get('situacao_ce') or '').upper()
        situacao_entrega_dados = (dados.get('situacaoEntregaCarga') or '').upper()
        
        return (
            'ENTREGUE' in situacao_ce or
            'ENTREGUE' in situacao_entrega or
            'ENTREGUE' in situacao_ce_dados or
            'ENTREGUE' in situacao_entrega_dados
        )
    
    def _di_desembaracou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se DI acabou de desembaraçar (mudou para desembaraçada)"""
        status_anterior = (dto_anterior.situacao_di or '').upper()
        status_novo = (dto_novo.situacao_di or '').upper()
        situacao_entrega_anterior = (dto_anterior.situacao_entrega or '').upper()
        situacao_entrega_novo = (dto_novo.situacao_entrega or '').upper()
        
        # Verificar se mudou para desembaraçada ou entrega autorizada
        estava_desembaracada = (
            'DESEMBARAC' in status_anterior or
            'ENTREGA AUTORIZADA' in status_anterior or
            'ENTREGA AUTORIZADA' in situacao_entrega_anterior
        )
        
        esta_desembaracada = (
            'DESEMBARAC' in status_novo or
            'ENTREGA AUTORIZADA' in status_novo or
            'ENTREGA AUTORIZADA' in situacao_entrega_novo
        )
        
        # Retornar True se não estava desembaraçada e agora está
        return not estava_desembaracada and esta_desembaracada
    
    def _duimp_desembaracou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> bool:
        """Verifica se DUIMP acabou de desembaraçar (mudou para desembaraçada)"""
        status_anterior = self._extrair_status_duimp(dto_anterior.dados_completos) or ''
        status_novo = self._extrair_status_duimp(dto_novo.dados_completos) or ''
        
        status_anterior_upper = status_anterior.upper()
        status_novo_upper = status_novo.upper()
        
        # Verificar se mudou para desembaraçada ou entrega autorizada
        estava_desembaracada = (
            'DESEMBARAC' in status_anterior_upper or
            'ENTREGA AUTORIZADA' in status_anterior_upper
        )
        
        esta_desembaracada = (
            'DESEMBARAC' in status_novo_upper or
            'ENTREGA AUTORIZADA' in status_novo_upper
        )
        
        # Retornar True se não estava desembaraçada e agora está
        return not estava_desembaracada and esta_desembaracada
    
    def _criar_notificacao_pagamentos_necessarios(self, dto: ProcessoKanbanDTO, tipo_documento: str = 'DI') -> Optional[Dict]:
        """
        Cria notificação especial quando DI/DUIMP desembaraça, verificando pagamentos necessários.
        
        A carga só pode sair do porto quando:
        - ICMS: pago ou exonerado
        - AFRMM: pago (quando tiver - apenas marítimo)
        - Frete: pago (quando tiver informação)
        """
        processo_ref = dto.processo_referencia
        numero_documento = dto.numero_di if tipo_documento == 'DI' else dto.numero_duimp
        
        # Verificar ICMS
        icms_status = None
        icms_pendente = False
        icms_pago_ou_exonerado = False
        
        if dto.pendencia_icms:
            icms_str = str(dto.pendencia_icms).upper()
            if icms_str in ['OK', 'PAGO', 'EXONERADO', 'EXONERADA']:
                icms_pago_ou_exonerado = True
                icms_status = 'Pago/Exonerado'
            else:
                icms_pendente = True
                icms_status = dto.pendencia_icms
        else:
            # Se não tem pendencia_icms, pode estar OK ou não ter informação
            icms_status = 'Sem informação'
        
        # Verificar AFRMM (apenas marítimo)
        afrmm_paga = False
        afrmm_pendente = False
        tem_afrmm = False
        
        if dto.modal == 'Marítimo':
            tem_afrmm = True
            afrmm_paga = self._extrair_afrmm_paga(dto.dados_completos)
            if not afrmm_paga:
                afrmm_pendente = True
        
        # Verificar Frete
        frete_pago = False
        frete_pendente = False
        tem_frete = False
        
        if dto.pendencia_frete is not None:
            tem_frete = True
            if dto.pendencia_frete:
                frete_pendente = True
            else:
                frete_pago = True
        
        # Formatar mensagem
        mensagem = f"**{tipo_documento} Desembaraçada:** {numero_documento or 'N/A'}\n\n"
        
        # ✅ NOVO: Verificar se status indica pendências (ex: DESEMBARACADA_AGUARDANDO_PENDENCIA)
        status_duimp = None
        if tipo_documento == 'DUIMP':
            status_duimp = self._extrair_status_duimp(dto.dados_completos) or ''
        elif tipo_documento == 'DI':
            status_duimp = dto.situacao_di or ''
        
        tem_pendencias_status = False
        if status_duimp and ('AGUARDANDO_PENDENCIA' in status_duimp.upper() or 'PENDENCIA' in status_duimp.upper()):
            tem_pendencias_status = True
            mensagem += f"⚠️ **STATUS:** {status_duimp.replace('_', ' ').title()}\n"
            mensagem += "💡 **ATENÇÃO:** Há pendências que precisam ser resolvidas antes da retirada da carga.\n\n"
        
        mensagem += "💰 **PAGAMENTOS NECESSÁRIOS PARA RETIRADA DA CARGA:**\n\n"
        
        # ICMS
        mensagem += f"📋 **ICMS:**\n"
        if icms_pago_ou_exonerado:
            mensagem += f"   ✅ {icms_status} - OK para retirada\n"
        elif icms_pendente:
            mensagem += f"   ⚠️ **PENDENTE:** {icms_status}\n"
            mensagem += f"   💡 **AÇÃO:** Solicitar pagamento ou exoneração do ICMS\n"
        else:
            mensagem += f"   ⚠️ Sem informação - Verificar status do ICMS\n"
        mensagem += "\n"
        
        # AFRMM (se marítimo)
        if tem_afrmm:
            mensagem += f"🚢 **AFRMM:**\n"
            if afrmm_paga:
                mensagem += f"   ✅ Pago - OK para retirada\n"
            else:
                mensagem += f"   ⚠️ **PENDENTE** - Obrigatório para retirada\n"
                mensagem += f"   💡 **AÇÃO:** Solicitar pagamento do AFRMM\n"
            mensagem += "\n"
        
        # Frete (se tem informação)
        if tem_frete:
            mensagem += f"🚚 **Frete:**\n"
            if frete_pago:
                mensagem += f"   ✅ Pago - OK para retirada\n"
            else:
                mensagem += f"   ⚠️ **PENDENTE** - Não retira carga sem pagamento\n"
                mensagem += f"   💡 **AÇÃO:** Solicitar pagamento do frete\n"
            mensagem += "\n"
        
        # Resumo
        pode_retirar = (
            icms_pago_ou_exonerado and
            (not tem_afrmm or afrmm_paga) and
            (not tem_frete or frete_pago)
        )
        
        if pode_retirar:
            mensagem += "✅ **TODOS OS PAGAMENTOS OK - CARGA PODE SER RETIRADA**"
        else:
            pendentes = []
            if icms_pendente or not icms_pago_ou_exonerado:
                pendentes.append("ICMS")
            if tem_afrmm and afrmm_pendente:
                pendentes.append("AFRMM")
            if tem_frete and frete_pendente:
                pendentes.append("Frete")
            
            mensagem += f"⚠️ **PENDÊNCIAS:** {', '.join(pendentes)}\n"
            mensagem += "💡 Resolva as pendências acima para liberar a retirada da carga.\n\n"
        
        # ✅ NOVO: Adicionar alerta sobre verificação de NCM e outras pendências
        if tem_pendencias_status or icms_pendente or afrmm_pendente or frete_pendente:
            mensagem += "📋 **VERIFICAÇÕES ADICIONAIS:**\n"
            mensagem += "   • Verificar classificação NCM dos produtos\n"
            mensagem += "   • Verificar documentação completa (Invoice, Packing List, etc.)\n"
            mensagem += "   • Verificar se há bloqueios ou retenções na Receita Federal\n"
            mensagem += "   • Confirmar se todos os tributos foram pagos ou exonerados\n"
        
        # Criar notificação
        return {
            'processo_referencia': processo_ref,
            'tipo_notificacao': 'pagamentos_necessarios',
            'titulo': f'💰 {processo_ref}: {tipo_documento} Desembaraçada - Verificar Pagamentos',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'tipo_documento': tipo_documento,
                'numero_documento': numero_documento,
                'icms_status': icms_status,
                'icms_pendente': icms_pendente,
                'icms_pago_ou_exonerado': icms_pago_ou_exonerado,
                'afrmm_paga': afrmm_paga,
                'afrmm_pendente': afrmm_pendente,
                'tem_afrmm': tem_afrmm,
                'frete_pago': frete_pago,
                'frete_pendente': frete_pendente,
                'tem_frete': tem_frete,
                'pode_retirar': pode_retirar
            })
        }
    
    def _criar_notificacao_chegada(self, dto: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de chegada confirmada"""
        data_chegada = dto.data_destino_final
        if isinstance(data_chegada, str):
            try:
                data_chegada = datetime.fromisoformat(data_chegada.replace('Z', ''))
            except:
                pass
        
        data_str = data_chegada.strftime('%d/%m/%Y') if isinstance(data_chegada, datetime) else str(data_chegada)
        
        return {
            'processo_referencia': dto.processo_referencia,
            'tipo_notificacao': 'chegada',
            'titulo': f'✅ Chegada confirmada: {dto.processo_referencia}',
            'mensagem': f'Chegada confirmada em {data_str}. Próximo passo: Verificar pendências para registro de DI/DUIMP.',
            'dados_extras': json.dumps({
                'data_chegada': data_str,
                'porto': dto.porto_nome,
                'modal': dto.modal
            })
        }
    
    def _criar_notificacao_status_di(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de mudança de status da DI"""
        status_anterior = dto_anterior.situacao_di or 'Sem status'
        status_novo = dto_novo.situacao_di
        
        # Verificar se desembaraçou e buscar pendências
        mensagem = f'Status da DI alterado:\n   Antes: {status_anterior}\n   Agora: {status_novo}'
        
        if status_novo in ['di_desembaracada', 'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO DO DESPACHO']:
            mensagem += '\n\n⚠️ Verificar pendências:'
            if dto_novo.pendencia_icms:
                mensagem += f'\n   - ICMS: {dto_novo.pendencia_icms} (pode ser pago agora)'
            if dto_novo.modal == 'Marítimo':
                afrmm_paga = self._extrair_afrmm_paga(dto_novo.dados_completos)
                if not afrmm_paga:
                    mensagem += '\n   - AFRMM: Pendente (obrigatório para retirada)'
            if dto_novo.pendencia_frete:
                mensagem += '\n   - Frete: Pendente (não retira carga)'
        
        return {
            'processo_referencia': dto_novo.processo_referencia,
            'tipo_notificacao': 'status_di',
            'titulo': f'📋 {dto_novo.processo_referencia}: Status da DI alterado',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'status_anterior': status_anterior,
                'status_novo': status_novo,
                'numero_di': dto_novo.numero_di
            })
        }
    
    def _criar_notificacao_status_ce(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de mudança de status do CE"""
        status_anterior = self._extrair_status_ce(dto_anterior) or 'Sem status'
        status_novo = self._extrair_status_ce(dto_novo)
        
        mensagem = f'Status do CE alterado:\n   Antes: {status_anterior}\n   Agora: {status_novo}'
        
        # Adicionar contexto se for mudança importante
        if status_novo == 'MANIFESTADO':
            mensagem += '\n\n💡 CE foi manifestado - aguardar armazenamento para registro de DI/DUIMP'
        elif status_novo == 'ARMAZENADA':
            mensagem += '\n\n💡 Carga armazenada - pode registrar DI/DUIMP'
        
        return {
            'processo_referencia': dto_novo.processo_referencia,
            'tipo_notificacao': 'status_ce',
            'titulo': f'📦 {dto_novo.processo_referencia}: Status do CE alterado',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'status_anterior': status_anterior,
                'status_novo': status_novo,
                'numero_ce': dto_novo.numero_ce
            })
        }
    
    def _criar_notificacao_status_lpco(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de mudança de status do LPCO"""
        status_anterior = dto_anterior.situacao_lpco or 'Sem status'
        status_novo = dto_novo.situacao_lpco
        numero_lpco = dto_novo.numero_lpco or 'N/A'
        canal_lpco = dto_novo.canal_lpco or 'Não informado'
        
        # Formatar data se disponível
        data_str = ''
        if dto_novo.data_situacao_lpco:
            try:
                data_str = dto_novo.data_situacao_lpco.strftime('%d/%m/%Y %H:%M')
            except:
                data_str = str(dto_novo.data_situacao_lpco)
        
        mensagem = f'**Processo:** {dto_novo.processo_referencia}\n'
        mensagem += f'**LPCO:** {numero_lpco}\n'
        mensagem += f'**Situação:** {status_anterior} → {status_novo}\n'
        mensagem += f'**Canal:** {canal_lpco}'
        
        if data_str:
            mensagem += f'\n**Data:** {data_str}'
        
        # Adicionar contexto baseado no status
        if status_novo == 'Deferido':
            mensagem += '\n\n✅ LPCO deferido - processo pode prosseguir'
        elif status_novo == 'Indeferido':
            mensagem += '\n\n❌ LPCO indeferido - verificar pendências e exigências'
        
        return {
            'processo_referencia': dto_novo.processo_referencia,
            'tipo_notificacao': 'status_lpco',
            'titulo': f'📋 {dto_novo.processo_referencia}: Status do LPCO alterado',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'numero_lpco': numero_lpco,
                'status_anterior': status_anterior,
                'status_novo': status_novo,
                'canal_lpco': canal_lpco,
                'data_situacao_lpco': data_str
            })
        }
    
    def _criar_notificacao_eta_mudou(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de mudança de ETA (Estimated Time of Arrival)"""
        from datetime import timedelta
        
        eta_anterior = dto_anterior.eta_iso
        eta_novo = dto_novo.eta_iso
        porto_nome = dto_novo.porto_nome or 'Porto não informado'
        nome_navio = dto_novo.nome_navio or 'Navio não informado'
        
        # ✅ NOVO: Buscar histórico de ETA para comparação mais completa
        historico_eta = self._buscar_historico_campo(dto_novo.processo_referencia, 'eta_iso', limite=3)
        historico_formatado = []
        if historico_eta:
            for h in historico_eta:
                try:
                    from dateutil import parser
                    eta_hist = parser.parse(h['valor_novo']) if h['valor_novo'] != 'None' else None
                    if eta_hist:
                        historico_formatado.append({
                            'eta': eta_hist,
                            'data_mudanca': h['criado_em']
                        })
                except:
                    pass
        
        # Formatar datas
        def formatar_eta(eta):
            if not eta:
                return 'Não informado'
            try:
                if isinstance(eta, str):
                    from dateutil import parser
                    eta = parser.parse(eta)
                return eta.strftime('%d/%m/%Y %H:%M')
            except:
                return str(eta)
        
        eta_anterior_str = formatar_eta(eta_anterior)
        eta_novo_str = formatar_eta(eta_novo)
        
        # Calcular diferença e determinar se antecipou ou atrasou
        mensagem = f'**Processo:** {dto_novo.processo_referencia}\n'
        mensagem += f'**Porto:** {porto_nome}\n'
        if nome_navio != 'Navio não informado':
            mensagem += f'**Navio:** {nome_navio}\n'
        
        # ✅ CORREÇÃO: Mostrar apenas o novo ETA, sem o anterior
        mensagem += f'**ETA:** {eta_novo_str}'
        
        # Calcular diferença se ambos existem
        horas_diferenca = None
        if eta_anterior and eta_novo:
            try:
                # Converter para datetime se necessário
                eta_ant = eta_anterior
                eta_new = eta_novo
                
                if isinstance(eta_anterior, str):
                    from dateutil import parser
                    eta_ant = parser.parse(eta_anterior)
                if isinstance(eta_novo, str):
                    from dateutil import parser
                    eta_new = parser.parse(eta_novo)
                
                diferenca = eta_new - eta_ant
                horas_diferenca = diferenca.total_seconds() / 3600
                dias_diferenca = diferenca.days
                
                if abs(horas_diferenca) < 24:
                    # Menos de 1 dia - mostrar em horas
                    if horas_diferenca > 0:
                        mensagem += f'\n\n⏰ **Atrasou:** {abs(horas_diferenca):.1f} hora(s)'
                    elif horas_diferenca < 0:
                        mensagem += f'\n\n✅ **Antecipou:** {abs(horas_diferenca):.1f} hora(s)'
                    else:
                        mensagem += f'\n\nℹ️ ETA atualizado (mesma data/hora)'
                else:
                    # Mais de 1 dia - mostrar em dias
                    if dias_diferenca > 0:
                        mensagem += f'\n\n⏰ **Atrasou:** {abs(dias_diferenca)} dia(s)'
                    elif dias_diferenca < 0:
                        mensagem += f'\n\n✅ **Antecipou:** {abs(dias_diferenca)} dia(s)'
                    else:
                        mensagem += f'\n\nℹ️ ETA atualizado (mesma data)'
            except Exception as e:
                logger.debug(f'Erro ao calcular diferença de ETA: {e}')
                mensagem += '\n\nℹ️ ETA atualizado'
        elif not eta_anterior and eta_novo:
            mensagem += '\n\n✅ ETA informado pela primeira vez'
        elif eta_anterior and not eta_novo:
            mensagem += '\n\n⚠️ ETA removido'
        
        # ✅ NOVO: Adicionar histórico de mudanças anteriores (se houver)
        if historico_formatado and len(historico_formatado) > 1:
            mensagem += '\n\n📊 **Histórico de mudanças de ETA:**'
            for i, hist in enumerate(historico_formatado[:3], 1):  # Mostrar até 3 mudanças anteriores
                try:
                    eta_str = hist['eta'].strftime('%d/%m/%Y %H:%M')
                    mensagem += f'\n   {i}. {eta_str} (em {hist["data_mudanca"]})'
                except:
                    pass
        
        return {
            'processo_referencia': dto_novo.processo_referencia,
            'tipo_notificacao': 'eta_mudou',
            'titulo': f'⏱️ {dto_novo.processo_referencia}: ETA atualizado',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'eta_anterior': eta_anterior_str,
                'eta_novo': eta_novo_str,
                'porto_nome': porto_nome,
                'nome_navio': nome_navio,
                'diferenca_horas': horas_diferenca
            })
        }
    
    def _criar_notificacao_status_duimp(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de mudança de status da DUIMP"""
        status_anterior = self._extrair_status_duimp(dto_anterior.dados_completos) or 'Sem status'
        status_novo = self._extrair_status_duimp(dto_novo.dados_completos)
        
        mensagem = f'Status da DUIMP alterado:\n   Antes: {status_anterior}\n   Agora: {status_novo}'
        
        if status_novo in ['desembaracada', 'ENTREGA AUTORIZADA SEM PROSSEGUIMENTO DO DESPACHO']:
            mensagem += '\n\n⚠️ Verificar pendências:'
            if dto_novo.pendencia_icms:
                mensagem += f'\n   - ICMS: {dto_novo.pendencia_icms} (pode ser pago agora)'
            if dto_novo.modal == 'Marítimo':
                afrmm_paga = self._extrair_afrmm_paga(dto_novo.dados_completos)
                if not afrmm_paga:
                    mensagem += '\n   - AFRMM: Pendente (obrigatório para retirada)'
            if dto_novo.pendencia_frete:
                mensagem += '\n   - Frete: Pendente (não retira carga)'
        
        return {
            'processo_referencia': dto_novo.processo_referencia,
            'tipo_notificacao': 'status_duimp',
            'titulo': f'📋 {dto_novo.processo_referencia}: Status da DUIMP alterado',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'status_anterior': status_anterior,
                'status_novo': status_novo,
                'numero_duimp': dto_novo.numero_duimp
            })
        }
    
    def _criar_notificacao_afrmm(self, dto: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de pagamento AFRMM"""
        return {
            'processo_referencia': dto.processo_referencia,
            'tipo_notificacao': 'pagamento_afrmm',
            'titulo': f'💰 AFRMM pago: {dto.processo_referencia}',
            'mensagem': f'AFRMM pago. Bloqueio removido - carga pode ser retirada.',
            'dados_extras': json.dumps({
                'modal': dto.modal,
                'numero_ce': dto.numero_ce
            })
        }
    
    def _criar_notificacao_icms_pago(self, dto: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de pagamento de ICMS"""
        # Verificar se processo está ENTREGUE para adicionar nota
        esta_entregue = self._processo_entregue(dto)
        mensagem = 'Pendência de ICMS removida.'
        if esta_entregue:
            mensagem += ' (Processo já está ENTREGUE)'
        else:
            mensagem += ' Verificar outras pendências se houver.'
        
        return {
            'processo_referencia': dto.processo_referencia,
            'tipo_notificacao': 'icms_pago',
            'titulo': f'✅ Pendência de ICMS removida: {dto.processo_referencia}',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'numero_di': dto.numero_di,
                'numero_duimp': dto.numero_duimp,
                'entregue': esta_entregue
            })
        }
    
    def _criar_notificacao_pendencia_resolvida(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de pendência resolvida"""
        esta_entregue = self._processo_entregue(dto_novo)
        mensagem = 'Todas as pendências foram resolvidas - processo liberado.'
        if esta_entregue:
            mensagem += ' (Processo já está ENTREGUE)'
        
        return {
            'processo_referencia': dto_novo.processo_referencia,
            'tipo_notificacao': 'pendencia_resolvida',
            'titulo': f'✅ Pendências resolvidas: {dto_novo.processo_referencia}',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'pendencia_icms_anterior': dto_anterior.pendencia_icms,
                'pendencia_frete_anterior': dto_anterior.pendencia_frete,
                'entregue': esta_entregue
            })
        }
    
    def _criar_notificacao_frete_pago(self, dto: ProcessoKanbanDTO) -> Optional[Dict]:
        """Cria notificação de pagamento de frete"""
        esta_entregue = self._processo_entregue(dto)
        mensagem = 'Pendência de frete removida.'
        if esta_entregue:
            mensagem += ' (Processo já está ENTREGUE)'
        else:
            mensagem += ' Carga pode ser retirada.'
        
        return {
            'processo_referencia': dto.processo_referencia,
            'tipo_notificacao': 'frete_pago',
            'titulo': f'✅ Pendência de frete removida: {dto.processo_referencia}',
            'mensagem': mensagem,
            'dados_extras': json.dumps({
                'bl_house': dto.bl_house,
                'entregue': esta_entregue
            })
        }
    
    def _salvar_notificacao(self, notificacao: Dict) -> bool:
        """Salva notificação no banco de dados e gera áudio TTS"""
        try:
            from db_manager import get_db_connection
            from services.tts_service import TTSService
            from utils.tts_text_formatter import formatar_texto_notificacao_para_tts
            from datetime import datetime, timedelta
            import json
            
            # ✅ CORREÇÃO CRÍTICA: Verificar se já existe notificação idêntica recente (últimos 5 minutos)
            # Isso evita notificações duplicadas quando a sincronização roda múltiplas vezes
            processo_ref = notificacao.get('processo_referencia')
            tipo_notif = notificacao.get('tipo_notificacao')
            titulo = notificacao.get('titulo', '')
            
            if processo_ref and tipo_notif:
                conn_check = get_db_connection()
                cursor_check = conn_check.cursor()
                
                # Buscar notificações do mesmo tipo para o mesmo processo nos últimos 5 minutos
                limite_tempo = datetime.now() - timedelta(minutes=5)
                cursor_check.execute('''
                    SELECT COUNT(*) FROM notificacoes_processos 
                    WHERE processo_referencia = ? 
                    AND tipo_notificacao = ?
                    AND titulo = ?
                    AND criado_em >= ?
                ''', (processo_ref, tipo_notif, titulo, limite_tempo.isoformat()))
                
                count = cursor_check.fetchone()[0]
                conn_check.close()
                
                if count > 0:
                    logger.debug(f"ℹ️ Notificação duplicada detectada para {processo_ref} ({tipo_notif}) - não salvar")
                    return False
            
            # Preparar dados_extras
            dados_extras = notificacao.get('dados_extras', {})
            if isinstance(dados_extras, str):
                try:
                    dados_extras = json.loads(dados_extras)
                except:
                    dados_extras = {}
            
            # Gerar áudio TTS com texto formatado
            try:
                tts = TTSService()
                if tts.enabled:
                    # Formatar texto para TTS (remove ponto, formata números, etc.)
                    texto_tts = formatar_texto_notificacao_para_tts(
                        titulo=notificacao.get('titulo', ''),
                        mensagem=notificacao.get('mensagem', ''),
                        processo_referencia=notificacao.get('processo_referencia')
                    )
                    
                    # Gerar áudio
                    audio_url = tts.gerar_audio(texto_tts)
                    if audio_url:
                        dados_extras['audio_url'] = audio_url
                        dados_extras['texto_tts'] = texto_tts  # Salvar texto formatado também
                        logger.debug(f"🎤 Áudio TTS gerado para notificação: {audio_url}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao gerar áudio TTS (continuando sem áudio): {e}")
                # Continua sem áudio se houver erro
            
            # Converter dados_extras para JSON string
            dados_extras_json = json.dumps(dados_extras) if dados_extras else None
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO notificacoes_processos 
                (processo_referencia, tipo_notificacao, titulo, mensagem, dados_extras)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                notificacao['processo_referencia'],
                notificacao['tipo_notificacao'],
                notificacao['titulo'],
                notificacao['mensagem'],
                dados_extras_json
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar notificação: {e}", exc_info=True)
            return False
    
    def notificar_erro_sistema(self, tipo_erro: str, mensagem: str, detalhes: Optional[Dict] = None) -> bool:
        """
        Cria notificação de erro do sistema (ex: conexão SQL Server, timeout, etc.)
        
        Args:
            tipo_erro: Tipo do erro (ex: 'sql_server_timeout', 'sql_server_connection_failed')
            mensagem: Mensagem de erro para o usuário
            detalhes: Dict com detalhes adicionais (opcional)
        
        Returns:
            True se notificação foi criada, False caso contrário
        """
        try:
            notificacao = {
                'processo_referencia': 'SISTEMA',
                'tipo_notificacao': f'erro_sistema_{tipo_erro}',
                'titulo': f'⚠️ Erro: {tipo_erro.replace("_", " ").title()}',
                'mensagem': mensagem,
                'dados_extras': json.dumps(detalhes or {})
            }
            
            # Verificar se já existe notificação similar recente (últimos 10 minutos)
            # Para evitar spam de notificações de erro
            conn_check = get_db_connection()
            cursor_check = conn_check.cursor()
            
            from datetime import datetime, timedelta
            limite_tempo = datetime.now() - timedelta(minutes=10)
            cursor_check.execute('''
                SELECT COUNT(*) FROM notificacoes_processos 
                WHERE processo_referencia = 'SISTEMA'
                AND tipo_notificacao = ?
                AND criado_em >= ?
            ''', (notificacao['tipo_notificacao'], limite_tempo.isoformat()))
            
            count = cursor_check.fetchone()[0]
            conn_check.close()
            
            if count > 0:
                logger.debug(f"ℹ️ Notificação de erro '{tipo_erro}' já existe nos últimos 10 minutos - não criar duplicata")
                return False
            
            # Salvar notificação
            return self._salvar_notificacao(notificacao)
        except Exception as e:
            logger.error(f"❌ Erro ao criar notificação de erro do sistema: {e}", exc_info=True)
            return False
    
    def _dict_para_dto(self, dados: Dict) -> ProcessoKanbanDTO:
        """Converte dict para DTO"""
        if isinstance(dados, ProcessoKanbanDTO):
            return dados
        return ProcessoKanbanDTO.from_kanban_json(dados)
    
    def _extrair_status_duimp(self, dados_completos: Dict) -> Optional[str]:
        """Extrai status da DUIMP dos dados completos"""
        if not dados_completos:
            return None
        duimp = dados_completos.get('duimp', [])
        if isinstance(duimp, list) and len(duimp) > 0:
            duimp_item = duimp[0] if isinstance(duimp[0], dict) else None
            if duimp_item:
                # ✅ CORREÇÃO: Buscar em múltiplos campos (situacao_duimp, situacao_duimp_agr, ultima_situacao)
                return (
                    duimp_item.get('situacao_duimp') or
                    duimp_item.get('situacao_duimp_agr') or
                    duimp_item.get('ultima_situacao') or
                    duimp_item.get('situacao') or  # Fallback
                    None
                )
        elif isinstance(duimp, dict):
            # Se duimp é um dict direto (não lista)
            return (
                duimp.get('situacao_duimp') or
                duimp.get('situacao_duimp_agr') or
                duimp.get('ultima_situacao') or
                duimp.get('situacao') or  # Fallback
                None
            )
        return None
    
    def _extrair_afrmm_paga(self, dados_completos: Dict) -> bool:
        """Extrai se AFRMM está paga dos dados completos"""
        if not dados_completos:
            return False
        return dados_completos.get('afrrmPaga', False) is True
    
    def _salvar_historico_mudancas(self, dto_anterior: ProcessoKanbanDTO, dto_novo: ProcessoKanbanDTO, notificacoes: List[Dict]) -> None:
        """Salva histórico de mudanças (apenas campos que mudaram)"""
        try:
            from db_manager import get_db_connection
            from datetime import datetime
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            processo_ref = dto_novo.processo_referencia
            
            # Mapear tipo de notificação para campo do DTO
            tipo_para_campo = {
                'chegada': 'data_destino_final',
                'status_di': 'situacao_di',
                'status_duimp': 'situacao_duimp',
                'status_ce': 'situacao_ce',
                'status_lpco': 'situacao_lpco',
                'eta_mudou': 'eta_iso',
                'icms_pago': 'pendencia_icms',
                'frete_pago': 'pendencia_frete',
                'pagamento_afrmm': 'afrmm_paga',
                'pendencia_resolvida': 'tem_pendencias'
            }
            
            # Salvar histórico para cada mudança detectada
            for notif in notificacoes:
                tipo_notif = notif.get('tipo_notificacao')
                campo = tipo_para_campo.get(tipo_notif)
                
                if not campo:
                    continue
                
                # Extrair valores anterior e novo
                valor_anterior = self._extrair_valor_campo(dto_anterior, campo)
                valor_novo = self._extrair_valor_campo(dto_novo, campo)
                
                # Formatar valores para string
                valor_anterior_str = self._formatar_valor_historico(valor_anterior)
                valor_novo_str = self._formatar_valor_historico(valor_novo)
                
                # Inserir no histórico
                cursor.execute('''
                    INSERT INTO processos_kanban_historico 
                    (processo_referencia, campo_mudado, valor_anterior, valor_novo)
                    VALUES (?, ?, ?, ?)
                ''', (processo_ref, campo, valor_anterior_str, valor_novo_str))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar histórico de mudanças: {e}", exc_info=True)
    
    def _extrair_valor_campo(self, dto: ProcessoKanbanDTO, campo: str) -> Any:
        """Extrai valor de um campo do DTO"""
        if hasattr(dto, campo):
            return getattr(dto, campo)
        
        # Campos especiais que precisam de extração
        if campo == 'situacao_duimp':
            return self._extrair_status_duimp(dto.dados_completos)
        elif campo == 'afrmm_paga':
            return self._extrair_afrmm_paga(dto.dados_completos)
        
        return None
    
    def _formatar_valor_historico(self, valor: Any) -> str:
        """Formata valor para salvar no histórico"""
        if valor is None:
            return 'None'
        
        if isinstance(valor, datetime):
            return valor.isoformat()
        
        if isinstance(valor, bool):
            return 'True' if valor else 'False'
        
        return str(valor)
    
    def _buscar_historico_campo(self, processo_referencia: str, campo: str, limite: int = 1) -> List[Dict]:
        """Busca histórico de um campo específico de um processo"""
        try:
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT valor_anterior, valor_novo, criado_em
                FROM processos_kanban_historico
                WHERE processo_referencia = ? AND campo_mudado = ?
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (processo_referencia, campo, limite))
            
            rows = cursor.fetchall()
            conn.close()
            
            historico = []
            for row in rows:
                historico.append({
                    'valor_anterior': row[0],
                    'valor_novo': row[1],
                    'criado_em': row[2]
                })
            
            return historico
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar histórico: {e}", exc_info=True)
            return []
    
    def _limpar_historico_antigo(self, dias_retencao: int = 30) -> int:
        """Remove histórico com mais de X dias (padrão: 30 dias)"""
        try:
            from db_manager import get_db_connection
            from datetime import datetime, timedelta
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            data_limite = datetime.now() - timedelta(days=dias_retencao)
            
            cursor.execute('''
                DELETE FROM processos_kanban_historico
                WHERE criado_em < ?
            ''', (data_limite.isoformat(),))
            
            registros_removidos = cursor.rowcount
            conn.commit()
            conn.close()
            
            if registros_removidos > 0:
                logger.info(f"🧹 Histórico antigo limpo: {registros_removidos} registro(s) removido(s)")
            
            return registros_removidos
            
        except Exception as e:
            logger.error(f"❌ Erro ao limpar histórico antigo: {e}", exc_info=True)
            return 0
    
    def _criar_sugestao_vinculacao_bancaria(self, dto: ProcessoKanbanDTO, tipo_documento: str = 'DI') -> None:
        """
        Cria sugestão de vinculação bancária automática quando DI/DUIMP desembaraça.
        
        Args:
            dto: DTO do processo
            tipo_documento: 'DI' ou 'DUIMP'
        """
        try:
            from services.banco_auto_vinculacao_service import BancoAutoVinculacaoService
            from services.agents.processo_agent import ProcessoAgent
            from datetime import datetime
            
            processo_ref = dto.processo_referencia
            numero_documento = dto.numero_di if tipo_documento == 'DI' else dto.numero_duimp
            
            # Buscar processo consolidado para extrair valores de impostos
            processo_agent = ProcessoAgent()
            processo_consolidado_result = processo_agent.consultar_processo_consolidado({
                'processo_referencia': processo_ref
            })
            
            if not processo_consolidado_result.get('sucesso'):
                logger.warning(f"⚠️ Não foi possível buscar processo consolidado para {processo_ref}")
                return
            
            processo_consolidado = processo_consolidado_result.get('dados', {})
            
            # Extrair total de impostos
            auto_vinculacao = BancoAutoVinculacaoService()
            total_impostos = auto_vinculacao.extrair_total_impostos_processo(processo_consolidado, tipo_documento)
            
            if not total_impostos or total_impostos <= 0:
                logger.info(f"ℹ️ Processo {processo_ref} não tem impostos para vincular (total: {total_impostos})")
                return
            
            # Extrair data de desembaraço
            data_desembaraco = None
            if tipo_documento == 'DI':
                di_data = processo_consolidado.get('di', {})
                data_desembaraco_str = di_data.get('data_desembaraco') or di_data.get('dataHoraDesembaraco')
                if data_desembaraco_str:
                    try:
                        if isinstance(data_desembaraco_str, str):
                            if 'T' in data_desembaraco_str:
                                data_desembaraco = datetime.fromisoformat(data_desembaraco_str.split('.')[0].replace('Z', '+00:00'))
                            else:
                                data_desembaraco = datetime.strptime(data_desembaraco_str[:10], '%Y-%m-%d')
                        else:
                            data_desembaraco = data_desembaraco_str
                    except:
                        pass
            else:  # DUIMP
                duimp_data = processo_consolidado.get('duimp', {})
                data_desembaraco_str = duimp_data.get('data_desembaraco') or duimp_data.get('dataHoraDesembaraco')
                if data_desembaraco_str:
                    try:
                        if isinstance(data_desembaraco_str, str):
                            if 'T' in data_desembaraco_str:
                                data_desembaraco = datetime.fromisoformat(data_desembaraco_str.split('.')[0].replace('Z', '+00:00'))
                            else:
                                data_desembaraco = datetime.strptime(data_desembaraco_str[:10], '%Y-%m-%d')
                        else:
                            data_desembaraco = data_desembaraco_str
                    except:
                        pass
            
            # Se não encontrou data de desembaraço, usar data atual
            if not data_desembaraco:
                data_desembaraco = datetime.now()
            
            # Criar sugestão
            resultado = auto_vinculacao.detectar_e_criar_sugestao(
                processo_referencia=processo_ref,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                data_desembaraco=data_desembaraco,
                total_impostos=total_impostos,
                dados_processo=processo_consolidado
            )
            
            if resultado.get('sugestao_criada'):
                logger.info(f"✅ Sugestão de vinculação criada para {processo_ref} (R$ {total_impostos:,.2f})")
            else:
                logger.debug(f"ℹ️ Sugestão não criada para {processo_ref}: {resultado.get('resposta', 'N/A')}")
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar sugestão de vinculação bancária: {e}", exc_info=True)

