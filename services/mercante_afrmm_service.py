"""
MercanteAfrmmService

Responsabilidade:
- Resolver CE-Mercante a partir de um processo (processo_referencia)
- Preparar execução do RPA (scripts/mercante_bot.py) para abrir tela Pagar AFRMM,
  preencher CE, deixar parcela em branco e clicar "Enviar".

⚠️ Importante:
- Este serviço NÃO efetiva pagamento. Ele apenas prepara/navega até a próxima etapa.
- Credenciais do Mercante não ficam no código; o `mercante_bot.py` lê do `.env`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MercanteAfrmmPlan:
    processo_referencia: str
    ce_mercante: str
    parcela: Optional[str]
    comando: str


class MercanteAfrmmService:
    """
    Serviço de preparação de AFRMM no Mercante via RPA.
    """

    def __init__(self) -> None:
        pass

    @staticmethod
    def _normalizar_ce_mercante(raw: Optional[str]) -> Optional[str]:
        """
        Normaliza CE-Mercante (apenas dígitos), tolerando texto extra do frontend.
        """
        s = (raw or "").strip()
        if not s:
            return None
        m = re.search(r"\b(\d{6,20})\b", s)
        if not m:
            return None
        return m.group(1).strip()

    @staticmethod
    def _normalizar_processo_referencia(raw: str) -> str:
        """
        Normaliza o processo para o formato XXX.NNNN/AA, tolerando pontuação/aspas do frontend.
        """
        s = (raw or "").strip().upper()
        # Extrair o padrão canônico do meio de frases: "pagar afrmm bgr.0080/25”"
        m = re.search(r"\b([A-Z]{3}\.\d{4}/\d{2})\b", s)
        if m:
            return m.group(1)
        return s

    def preparar_por_processo(
        self,
        processo_referencia: str,
        *,
        ce_mercante: Optional[str] = None,
        parcela: Optional[str] = None,
        clicar_enviar: bool = True,
        executar_local: bool = False,
    ) -> Dict[str, Any]:
        """
        Prepara (e opcionalmente dispara) o fluxo de AFRMM para um processo.

        Args:
            processo_referencia: Ex: "GYM.0050/25"
            parcela: opcional (se None/"" deixa em branco)
            clicar_enviar: se True, clica Enviar após preencher CE (vai para próxima tela)
            executar_local: se True, tenta disparar o `scripts/mercante_bot.py` em background.

        Returns:
            Dict padronizado para agents.
        """
        proc = self._normalizar_processo_referencia(processo_referencia)
        if not proc:
            return {
                "sucesso": False,
                "erro": "ARGUMENTO_INVALIDO",
                "resposta": "❌ Informe o processo no formato `XXX.NNNN/AA` (ex: `GYM.0050/25`).",
            }

        ce_override = self._normalizar_ce_mercante(ce_mercante)
        ce = ce_override or self._resolver_ce_mercante(proc)
        if not ce:
            return {
                "sucesso": False,
                "erro": "CE_NAO_ENCONTRADO",
                "resposta": f"❌ Não encontrei o CE-Mercante para o processo **{proc}** no cache/banco.",
            }

        plan = self._montar_plano(proc, ce, parcela=parcela, clicar_enviar=clicar_enviar)

        started = False
        start_error = None
        if executar_local:
            try:
                self._executar_em_background(plan)
                started = True
            except Exception as e:
                start_error = str(e)

        preview = (
            f"🧾 **AFRMM (Mercante) — Preparação**\n"
            f"- **Processo**: {proc}\n"
            f"- **CE-Mercante**: {ce}\n"
            f"- **Parcela**: {'(em branco)' if not (parcela or '').strip() else parcela}\n"
            f"- **Ação**: preencher CE e clicar **Enviar** (ir para a próxima tela)\n"
        )

        if started:
            preview += "\n✅ **Bot iniciado localmente** (janela do Chromium deve abrir)."
        else:
            preview += "\n📌 **Comando para executar localmente**:\n"
            preview += f"\n`{plan.comando}`\n"
            preview += "\n(Se quiser ver o navegador por mais tempo, adicione `--keep_open`.)"
            if start_error:
                preview += f"\n\n⚠️ Não consegui iniciar automaticamente: `{start_error}`"

        return {
            "sucesso": True,
            "resposta": preview,
            "dados": {
                "processo_referencia": proc,
                "ce_mercante": ce,
                "parcela": (parcela or "").strip() or None,
                "clicar_enviar": bool(clicar_enviar),
                "comando": plan.comando,
                "executar_local": bool(executar_local),
                "started": started,
                "start_error": start_error,
            },
        }

    def _buscar_valor_afrmm_do_banco(
        self, processo_referencia: str, ce_mercante: str
    ) -> Tuple[Optional[float], Optional[bool], Optional[str]]:
        """
        Busca valor do AFRMM e status de pagamento do CE via API Integra Comex.
        
        Retorna: (valor_afrmm, afrmm_pago, motivo)
        - valor_afrmm: Valor do AFRMM em BRL (float) ou None
        - afrmm_pago: True se já está pago, False se não está pago, None se não conseguiu verificar
        - motivo: string curta com motivo quando não conseguiu (para exibir no preview)
        """
        def _parse_valor_brl(raw: Any) -> Optional[float]:
            if raw is None:
                return None
            if isinstance(raw, (int, float)):
                try:
                    v = float(raw)
                    return v if v > 0 else None
                except Exception:
                    return None
            s = str(raw).strip()
            if not s:
                return None
            # remover moeda e textos
            s = re.sub(r"[^\d,.\-]", "", s)
            if not s:
                return None
            # Caso típico BR: 1.234,56
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            else:
                # Se só vírgula, usar como decimal
                if "," in s and "." not in s:
                    s = s.replace(",", ".")
            try:
                v = float(s)
                return v if v > 0 else None
            except Exception:
                return None

        def _extrair_valor_e_pago(ce_json: Any) -> Tuple[Optional[float], Optional[bool]]:
            if not isinstance(ce_json, dict):
                return None, None
            afrmm_pago_local = ce_json.get("afrmmTUMPago")
            # Valor pode estar no root OU dentro de afrmmTUM
            raw_val = ce_json.get("valorAFRMM")
            if raw_val is None:
                afrmm_tum = ce_json.get("afrmmTUM") or {}
                if isinstance(afrmm_tum, dict):
                    raw_val = afrmm_tum.get("valorAFRMM") or afrmm_tum.get("valorAfrmm")
            valor = _parse_valor_brl(raw_val)
            return valor, (bool(afrmm_pago_local) if afrmm_pago_local is not None else None)

        motivo: Optional[str] = None
        try:
            # ✅ PRIORIDADE 1: Buscar via API Integra Comex (mesmo endpoint usado para extrato do CE)
            from utils.integracomex_proxy import call_integracomex
            
            logger.info(f"[Mercante] 🔍 Buscando CE {ce_mercante} via API Integra Comex para obter valorAFRMM...")
            
            # Path correto da API Integra Comex para consultar CE
            # Formato: /conhecimentos-embarque/{numero} (PLURAL, SEM /carga/)
            path = f'/conhecimentos-embarque/{ce_mercante}'
            
            try:
                status_code, response_body = call_integracomex(
                    path=path,
                    method='GET',
                    processo_referencia=processo_referencia,
                )
            except RuntimeError as e:
                # Ex.: DUPLICATA (últimos 5 minutos)
                msg = str(e)
                logger.warning(f"[Mercante] ⚠️ Falha ao consultar CE via Integra Comex: {msg}")
                motivo = msg
                status_code, response_body = None, None
            
            if status_code == 200 and response_body:
                valor_afrmm, afrmm_tum_pago = _extrair_valor_e_pago(response_body)
                if valor_afrmm is not None:
                    logger.info(
                        f"[Mercante] ✅ Valor AFRMM encontrado via API: R$ {valor_afrmm:,.2f} (pago: {afrmm_tum_pago})"
                    )
                    return valor_afrmm, afrmm_tum_pago, None
                logger.warning(
                    "[Mercante] ⚠️ Campo valorAFRMM não encontrado/parseável no JSON do CE (esperado em ce_json.afrmmTUM.valorAFRMM)."
                )
                motivo = motivo or "valorAFRMM não encontrado no retorno do CE (campo afrmmTUM.valorAFRMM)"
            elif status_code is not None:
                logger.warning(f"[Mercante] ⚠️ API Integra Comex retornou status {status_code} para CE {ce_mercante}")
                motivo = motivo or f"API Integra Comex retornou status {status_code}"
            
            # ✅ PRIORIDADE 2: Tentar buscar do processo consolidado (cache)
            from services.processo_repository import ProcessoRepository
            repo = ProcessoRepository()
            processo_dto = repo.buscar_por_referencia(processo_referencia)
            
            if processo_dto and processo_dto.dados_completos:
                ce_data = processo_dto.dados_completos.get("ce", {}) if isinstance(processo_dto.dados_completos, dict) else {}
                # Estrutura do cache: ce_data contém "dados_completos" com o JSON do CE
                ce_json_cache = None
                if isinstance(ce_data, dict):
                    ce_json_cache = ce_data.get("dados_completos") or ce_data.get("json_completo") or ce_data
                elif isinstance(ce_data, list) and ce_data:
                    item0 = ce_data[0]
                    if isinstance(item0, dict):
                        ce_json_cache = item0.get("dados_completos") or item0.get("json_completo") or item0

                valor_afrmm_cache, afrmm_pago_cache = _extrair_valor_e_pago(ce_json_cache)
                if valor_afrmm_cache is not None:
                    logger.info(
                        f"[Mercante] ✅ Valor AFRMM encontrado no cache: R$ {valor_afrmm_cache:,.2f} (pago: {afrmm_pago_cache})"
                    )
                    # ⚠️ Cache pode estar defasado: avisar via motivo se a API falhou
                    return valor_afrmm_cache, afrmm_pago_cache, (motivo or "usando cache do CE (API indisponível/duplicata)")
        except Exception as e:
            logger.warning(f"[Mercante] ⚠️ Erro ao buscar valor AFRMM: {e}", exc_info=True)
            motivo = motivo or str(e)

        return None, None, (motivo or "não foi possível consultar o valor do AFRMM no momento")
    
    def _resolver_ce_mercante(self, processo_referencia: str) -> Optional[str]:
        """
        Resolve numero_ce (CE-Mercante) a partir de processo_referencia usando o ProcessoRepository.
        """
        try:
            from services.processo_repository import ProcessoRepository

            repo = ProcessoRepository()
            dto = repo.buscar_por_referencia(processo_referencia)
            if not dto:
                return None
            numero_ce = getattr(dto, "numero_ce", None)
            if numero_ce:
                return str(numero_ce).strip()
            # fallback: dados_completos (quando vier do SQL Server)
            dados = getattr(dto, "dados_completos", None) or {}
            if isinstance(dados, dict):
                ce = dados.get("ce") or {}
                if isinstance(ce, dict) and ce.get("numero"):
                    return str(ce.get("numero")).strip()
        except Exception:
            return None
        return None

    def _montar_plano(
        self, processo_referencia: str, ce_mercante: str, *, parcela: Optional[str], clicar_enviar: bool
    ) -> MercanteAfrmmPlan:
        """
        Monta comando do mercante_bot.py para abrir tela e preencher CE.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        script_path = os.path.join(project_root, "scripts", "mercante_bot.py")

        # ✅ IMPORTANTE: Usar --no_cdp por padrão (mais confiável - sempre abre janela)
        # CDP requer Chrome rodando com debug na porta 9222, o que nem sempre está disponível
        # Usuário pode configurar MERCANTE_USE_CDP=true no .env se quiser usar CDP
        args = [
            "python3",
            script_path,
            "--acao",
            "pagar_afrmm",
            "--no_cdp",  # Usar --no_cdp por padrão (abre janela normalmente)
            "--ignore_https_errors",
            "--ce",
            ce_mercante,
        ]
        # ✅ Opcional: Se MERCANTE_USE_CDP=true, tentar usar CDP (requer Chrome com debug na porta 9222)
        if os.getenv("MERCANTE_USE_CDP", "").strip().lower() in ("true", "1", "yes"):
            # Remover --no_cdp e adicionar --cdp antes de --acao
            args = [arg for arg in args if arg != "--no_cdp"]
            # Inserir --cdp e URL após --acao
            acao_idx = args.index("--acao")
            args.insert(acao_idx + 1, "--cdp")
            args.insert(acao_idx + 2, "http://127.0.0.1:9222")
        if parcela and parcela.strip():
            args += ["--parcela", parcela.strip()]
        if not clicar_enviar:
            args.append("--nao_enviar")

        # não incluir credenciais aqui; ficam no .env
        cmd = " ".join(shlex.quote(a) for a in args)
        return MercanteAfrmmPlan(
            processo_referencia=processo_referencia,
            ce_mercante=ce_mercante,
            parcela=(parcela or "").strip() or None,
            comando=cmd,
        )

    def _executar_em_background(self, plan: MercanteAfrmmPlan) -> None:
        """
        Dispara o bot em background, sem travar o request do Flask.

        ⚠️ Observação: exige ambiente com UI (máquina do usuário).
        """
        # Executar via shell é mais fácil porque `plan.comando` já está escapado.
        subprocess.Popen(
            plan.comando,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    
    def preparar_pagamento_com_preview(
        self,
        processo_referencia: str,
        *,
        ce_mercante: Optional[str] = None,
        parcela: Optional[str] = None,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Prepara pagamento AFRMM com preview (Valor do Débito + Saldo BB) e cria pending intent.
        
        ⚠️ Ação sensível que requer confirmação do usuário.
        
        Args:
            processo_referencia: Ex: "GYM.0050/25"
            parcela: opcional (se None/"" deixa em branco)
            session_id: ID da sessão para criar pending intent
        
        Returns:
            Dict padronizado para agents com preview e pending_intent_id.
        """
        proc = self._normalizar_processo_referencia(processo_referencia)
        if not proc:
            return {
                "sucesso": False,
                "erro": "ARGUMENTO_INVALIDO",
                "resposta": "❌ Informe o processo no formato `XXX.NNNN/AA` (ex: `GYM.0050/25`).",
            }
        
        ce_override = self._normalizar_ce_mercante(ce_mercante)
        ce = ce_override or self._resolver_ce_mercante(proc)
        if not ce:
            return {
                "sucesso": False,
                "erro": "CE_NAO_ENCONTRADO",
                "resposta": f"❌ Não encontrei o CE-Mercante para o processo **{proc}** no cache/banco.",
            }

        # ✅ PRIORIDADE 0: Se já temos comprovante local (pagamento concluído), NÃO bilhetar Serpro
        try:
            from services.mercante_afrmm_pagamentos_repository import MercanteAfrmmPagamentosRepository

            repo = MercanteAfrmmPagamentosRepository()
            last_ok = repo.buscar_ultimo_sucesso_por_ce(ce)
            if last_ok:
                valor_total = last_ok.get("valor_total_debito")
                valor_afrmm = last_ok.get("valor_afrmm")
                receipt_rel = last_ok.get("screenshot_relpath")
                receipt_url = f"/api/download/{receipt_rel}" if receipt_rel else None

                linhas = [
                    "✅ **AFRMM já está pago!**",
                    "",
                    f"**Processo**: {proc}",
                    f"**CE-Mercante**: {ce}",
                ]
                if valor_total:
                    linhas.append(f"**Valor Total do Débito**: R$ {float(valor_total):,.2f}")
                if valor_afrmm:
                    linhas.append(f"**Valor do AFRMM**: R$ {float(valor_afrmm):,.2f}")
                if receipt_url:
                    linhas.append(f"🧾 **Comprovante (print)**: [abrir imagem]({receipt_url})")
                linhas.append("")
                linhas.append("💡 Não é necessário pagar novamente.")
                return {"sucesso": False, "erro": "AFRMM_JA_PAGO", "resposta": "\n".join(linhas)}
        except Exception:
            pass

        # ✅ CRÍTICO: Se já existe pending intent de AFRMM para este processo na sessão,
        # reaproveitar valor_debito/afrmm_pago e NÃO rebilhetar a API (evita DUPLICATA/loop).
        valor_debito = None
        afrmm_pago = None
        try:
            from services.pending_intent_service import get_pending_intent_service
            service = get_pending_intent_service()
            if service:
                intent_existente = service.buscar_pending_intent(session_id, action_type='payment')
                if intent_existente and intent_existente.get('status') == 'pending':
                    if intent_existente.get('tool_name') == 'executar_pagamento_afrmm':
                        args_exist = intent_existente.get('args_normalizados') or {}
                        if (args_exist.get('processo_referencia') == proc) and (args_exist.get('ce_mercante') == ce):
                            valor_debito = args_exist.get('valor_debito')
                            afrmm_pago = args_exist.get('afrmm_pago')
                            logger.info(
                                f"[Mercante] ✅ Reaproveitando pending intent existente (sem bilhetar CE): {intent_existente.get('intent_id')}"
                            )
        except Exception as e:
            logger.debug(f"[Mercante] Falha ao reaproveitar pending intent: {e}")

        # ✅ Buscar valor do AFRMM via API Integra Comex apenas se não havia pending intent reaproveitável
        motivo_valor = None
        if valor_debito is None and afrmm_pago is None:
            valor_debito, afrmm_pago, motivo_valor = self._buscar_valor_afrmm_do_banco(proc, ce)
        
        # ✅ Verificar se já está pago (mesmo que não tenhamos o valor)
        if afrmm_pago is True:
            valor_msg = f"**Valor pago**: R$ {valor_debito:,.2f}\n\n" if valor_debito is not None else "\n"
            return {
                "sucesso": False,
                "erro": "AFRMM_JA_PAGO",
                "resposta": (
                    f"✅ **AFRMM já está pago!**\n\n"
                    f"**Processo**: {proc}\n"
                    f"**CE-Mercante**: {ce}\n"
                    f"{valor_msg}"
                    "💡 Não é necessário pagar novamente."
                ),
            }
        
        # ✅ IMPORTANTE: Não executar bot no preview - apenas buscar valor do banco
        # O bot só será executado quando o usuário confirmar o pagamento (em executar_pagamento)
        
        # 2) Consultar saldo BB (da mesma conta usada para pagamento)
        saldo_bb = None
        try:
            from services.banco_brasil_service import BancoBrasilService
            from datetime import datetime, timedelta
            
            bb_service = BancoBrasilService()
            agencia = os.getenv("BB_TEST_AGENCIA")
            conta = os.getenv("BB_TEST_CONTA")
            
            if agencia and conta:
                # Consultar extrato de hoje (apenas para pegar saldo disponível se a API retornar)
                # Nota: API de Extratos pode não retornar saldo disponível diretamente
                # Vamos usar o último saldo_liquido do período como aproximação
                hoje = datetime.now()
                resultado_extrato = bb_service.consultar_extrato(
                    agencia=agencia,
                    conta=conta,
                    data_inicio=hoje.replace(hour=0, minute=0, second=0),
                    data_fim=hoje.replace(hour=23, minute=59, second=59),
                )
                if resultado_extrato.get("sucesso"):
                    dados = resultado_extrato.get("dados", {})
                    # ✅ CRÍTICO: usar saldo_atual (linha "S A L D O") quando disponível
                    saldo_bb = dados.get("saldo_atual")
                    if saldo_bb is None:
                        # fallback: aproximação antiga
                        saldo_bb = dados.get("saldo_disponivel") or dados.get("saldo_liquido")
                    if saldo_bb:
                        logger.info(f"[Mercante] ✅ Saldo BB consultado: R$ {saldo_bb:,.2f}")
        except Exception as e:
            logger.warning(f"[Mercante] ⚠️ Não consegui consultar saldo BB: {e}")
        
        # 3) Gerar preview
        preview_lines = [
            f"💳 **Pagamento AFRMM — Preview**",
            f"",
            f"**Processo**: {proc}",
            f"**CE-Mercante**: {ce}",
        ]
        if parcela and parcela.strip():
            preview_lines.append(f"**Parcela**: {parcela}")
        
        if valor_debito:
            preview_lines.extend([
                f"",
                f"**Valor do Débito**: R$ {valor_debito:,.2f}",
            ])
            if afrmm_pago is False:
                preview_lines.append(f"⚠️ **Status**: AFRMM não pago (pendente)")
        else:
            msg = "⚠️ Não consegui buscar o Valor do Débito automaticamente."
            if motivo_valor:
                msg += f" ({motivo_valor})"
            preview_lines.append(msg)
        
        if saldo_bb is not None:
            preview_lines.extend([
                f"**Saldo BB disponível**: R$ {saldo_bb:,.2f}",
            ])
            if valor_debito:
                diferenca = saldo_bb - valor_debito
                if diferenca >= 0:
                    preview_lines.append(f"✅ **Saldo suficiente** (sobra R$ {diferenca:,.2f})")
                else:
                    preview_lines.append(f"⚠️ **Saldo insuficiente** (faltam R$ {abs(diferenca):,.2f})")
        else:
            preview_lines.append(f"⚠️ Não consegui consultar o saldo BB automaticamente.")
        
        preview_lines.extend([
            f"",
        ])
        
        preview_lines.append(f"⚠️ **Confirme para executar o pagamento** (sim/pagar/enviar)")
        preview_lines.append(f"⏳ **Aviso**: após confirmar, o processamento pode demorar até **2 minutos**.")
        
        preview_text = "\n".join(preview_lines)
        
        # 4) Criar pending intent
        intent_id = None
        try:
            from services.pending_intent_service import get_pending_intent_service
            
            service = get_pending_intent_service()
            if service:
                args_normalizados = {
                    "processo_referencia": proc,
                    "ce_mercante": ce,
                    "parcela": (parcela or "").strip() or None,
                    "valor_debito": valor_debito,
                    "afrmm_pago": afrmm_pago,  # ✅ NOVO: Status de pagamento
                    "valor_debito_motivo": motivo_valor,
                }
                
                # ✅ CRÍTICO: dedupe NÃO pode depender do valor_debito (às vezes vem None / varia)
                # Senão cria várias intents "iguais" e aparece lista (1)(2)(3)...
                args_hash = {
                    "tool_name": "executar_pagamento_afrmm",
                    "processo_referencia": proc,
                    "ce_mercante": ce,
                    "parcela": (parcela or "").strip() or None,
                }

                intent_id = service.criar_pending_intent(
                    session_id=session_id,
                    action_type="payment",
                    tool_name="executar_pagamento_afrmm",
                    args_normalizados=args_normalizados,
                    preview_text=preview_text,
                    ttl_hours=2,  # 2 horas para confirmação
                    args_hash=args_hash,
                )
                
                if intent_id:
                    logger.info(f"[Mercante] ✅ Pending intent criado: {intent_id}")
        except Exception as e:
            logger.error(f"[Mercante] ❌ Erro ao criar pending intent: {e}", exc_info=True)
        
        return {
            "sucesso": True,
            "resposta": preview_text,
            "dados": {
                "processo_referencia": proc,
                "ce_mercante": ce,
                "parcela": (parcela or "").strip() or None,
                "valor_debito": valor_debito,
                "saldo_bb": saldo_bb,
                "pending_intent_id": intent_id,
            },
            "pending_intent_id": intent_id,  # Para compatibilidade com ConfirmationHandler
        }
    
    def executar_pagamento(
        self,
        processo_referencia: str,
        *,
        ce_mercante: Optional[str] = None,
        parcela: Optional[str] = None,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Executa pagamento AFRMM.

        Modos:
        - ✅ CDP (preferido quando a janela já está aberta): apenas clica no botão "Pagar AFRMM"
          usando `--acao apenas_clicar_pagar` conectado no Chrome/Chromium via CDP.
        - Fallback (sem CDP): executa o fluxo completo (login + navegação + preenchimento + clique).
        
        ⚠️ Esta função só deve ser chamada após confirmação do usuário.
        """
        proc = self._normalizar_processo_referencia(processo_referencia)
        if not proc:
            return {
                "sucesso": False,
                "erro": "ARGUMENTO_INVALIDO",
                "resposta": "❌ Informe o processo no formato `XXX.NNNN/AA` (ex: `GYM.0050/25`).",
            }
        
        ce_override = self._normalizar_ce_mercante(ce_mercante)
        ce = ce_override or self._resolver_ce_mercante(proc)
        if not ce:
            return {
                "sucesso": False,
                "erro": "CE_NAO_ENCONTRADO",
                "resposta": f"❌ Não encontrei o CE-Mercante para o processo **{proc}** no cache/banco.",
            }

        # ✅ PRIORIDADE 0: Se já temos comprovante local (pagamento concluído), NÃO bilhetar / NÃO executar robô
        try:
            from services.mercante_afrmm_pagamentos_repository import MercanteAfrmmPagamentosRepository

            repo = MercanteAfrmmPagamentosRepository()
            last_ok = repo.buscar_ultimo_sucesso_por_ce(ce)
            if last_ok:
                valor_total = last_ok.get("valor_total_debito")
                receipt_rel = last_ok.get("screenshot_relpath")
                receipt_url = f"/api/download/{receipt_rel}" if receipt_rel else None
                valor_msg = f"**Valor Total do Débito**: R$ {float(valor_total):,.2f}\n\n" if valor_total else "\n"
                return {
                    "sucesso": False,
                    "erro": "AFRMM_JA_PAGO",
                    "resposta": (
                        f"✅ **AFRMM já está pago!**\n\n"
                        f"**Processo**: {proc}\n"
                        f"**CE-Mercante**: {ce}\n"
                        f"{valor_msg}"
                        + (f"🧾 **Comprovante (print)**: [abrir imagem]({receipt_url})\n\n" if receipt_url else "")
                        + "💡 Não vou executar o robô para evitar pagamento duplicado."
                    ),
                }
        except Exception:
            pass

        # ✅ Segurança: checar se já está pago antes de tentar pagar novamente
        try:
            valor_ja_pago, afrmm_pago, _motivo = self._buscar_valor_afrmm_do_banco(proc, ce)
            if afrmm_pago is True:
                valor_msg = f"**Valor**: R$ {valor_ja_pago:,.2f}\n\n" if valor_ja_pago is not None else "\n"
                return {
                    "sucesso": False,
                    "erro": "AFRMM_JA_PAGO",
                    "resposta": (
                        f"✅ **AFRMM já está pago!**\n\n"
                        f"**Processo**: {proc}\n"
                        f"**CE-Mercante**: {ce}\n"
                        f"{valor_msg}"
                        "💡 Não vou executar o robô para evitar pagamento duplicado."
                    ),
                }
        except Exception:
            # não bloquear execução se a checagem falhar (ex.: API indisponível)
            pass
        
        # ✅ MODO DE CONFIRMAÇÃO
        # Por padrão (FULL), ao confirmar "sim" o robô faz TUDO sozinho:
        # login → navegar → preencher → clicar.
        #
        # O modo CLICK_ONLY (apenas clicar na janela já aberta) fica opcional,
        # pois exige Chrome/Chromium com CDP e a janela já aberta sob esse perfil.
        confirm_mode = os.getenv("MERCANTE_CONFIRMATION_MODE", "full").strip().lower()

        def _executar_bot_ate_json(cmd: str, *, timeout_s: int = 120) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
            """
            Executa o bot e aguarda o marcador __MAIKE_JSON__ para responder na UI com sucesso/erro.
            O bot pode continuar aberto (keep_open) após emitir o JSON.
            """
            try:
                proc = subprocess.Popen(
                    cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    start_new_session=True,
                )
            except Exception as e:
                return None, f"Falha ao iniciar robô: {e}"

            deadline = datetime.now().timestamp() + timeout_s
            payload = None
            last_lines: list[str] = []

            try:
                if not proc.stdout:
                    return None, "Robô iniciado sem stdout."
                for line in proc.stdout:
                    s = (line or "").strip()
                    if s:
                        last_lines.append(s)
                        if len(last_lines) > 30:
                            last_lines.pop(0)
                    if "__MAIKE_JSON__=" in s:
                        try:
                            json_part = s.split("__MAIKE_JSON__=", 1)[1]
                            payload = json.loads(json_part)
                        except Exception:
                            payload = None
                        break
                    if datetime.now().timestamp() > deadline:
                        break
            except Exception as e:
                return None, f"Erro ao ler saída do robô: {e}"

            if payload is None:
                # Se o processo já terminou, usar returncode para mensagens mais úteis
                try:
                    rc = proc.poll()
                except Exception:
                    rc = None
                tail = "\n".join(last_lines[-12:])
                if rc == 10 or ("senha pode ter expirado" in tail.lower()):
                    return None, (
                        "Falha ao autenticar no Mercante (senha pode ter expirado — troca a cada 20 dias). "
                        "Atualize em Configurações do Mercante e tente novamente."
                    )
                if rc is not None and rc != 0:
                    return None, f"Robô terminou com erro (code={rc}). Últimas linhas:\n{tail}"
                return None, f"Timeout/sem status do robô (até {timeout_s}s). Últimas linhas:\n{tail}"
            return payload, None

        # ✅ MODO CLICK_ONLY (opcional): clicar APENAS no botão via CDP (sem refazer o fluxo)
        if confirm_mode in ("click_only", "click-only", "cdp"):
            mercante_use_cdp = os.getenv("MERCANTE_USE_CDP", "").strip().lower() in ("true", "1", "yes")
            if not mercante_use_cdp:
                return {
                    "sucesso": False,
                    "erro": "CDP_REQUIRED_FOR_CLICK_ONLY",
                    "resposta": (
                        "❌ Para usar confirmação **click-only**, é necessário habilitar CDP.\n\n"
                        "💡 Configure `MERCANTE_USE_CDP=true` e inicie o Chrome com:\n"
                        "   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\\n"
                        "     --remote-debugging-port=9222 \\\n"
                        "     --user-data-dir=/tmp/chrome-mercante\n"
                    ),
                }

            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            script_path = os.path.join(project_root, "scripts", "mercante_bot.py")
            cdp_url = os.getenv("MERCANTE_CDP_URL", "").strip() or "http://127.0.0.1:9222"

            cmd_click = (
                f"python3 {shlex.quote(script_path)} "
                f"--acao apenas_clicar_pagar "
                f"--cdp {shlex.quote(cdp_url)} "
                f"--ignore_https_errors "
            )

            # manter janela aberta para acompanhamento (só faz sentido com UI)
            mercante_headless = os.getenv("MERCANTE_HEADLESS", "").strip().lower() in ("true", "1", "yes")
            if not mercante_headless:
                cmd_click += " --keep_open --keep_open_seconds 600"
            else:
                cmd_click += " --headless"
            # ✅ Confirmar popup (OK) após clique no botão
            cmd_click += " --confirmar_popup"
            # ✅ Comprovante (print)
            try:
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                downloads_dir = os.path.join(project_root, "downloads", "mercante")
                os.makedirs(downloads_dir, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_proc = re.sub(r"[^A-Z0-9_.-]+", "_", proc)
                safe_ce = re.sub(r"[^0-9]+", "", str(ce))
                receipt_filename = f"afrmm_receipt_{safe_proc}_{safe_ce}_{ts}.png"
                receipt_path = os.path.join(downloads_dir, receipt_filename)
                cmd_click += f" --screenshot {shlex.quote(receipt_path)}"
                receipt_url = f"/api/download/mercante/{receipt_filename}"
                
                # ✅ NOVO (26/01/2026): Após screenshot ser salvo, converter para PDF automaticamente
                # Isso será feito pelo mercante_bot.py após capturar o screenshot
            except Exception:
                receipt_path = None
                receipt_url = None

            # ✅ Retorno estruturado para a UI (sem fechar navegador)
            cmd_click += " --emit_json"

            logger.info(f"[Mercante] Clique-only via CDP para AFRMM (aguardando confirmação): {proc}")
            try:
                if mercante_headless:
                    result = subprocess.run(
                        cmd_click,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        return {"sucesso": True, "resposta": "✅ Botão \"Pagar AFRMM\" clicado (CDP/headless)."}
                    stderr_output = (result.stderr or "")[:800]
                    return {
                        "sucesso": False,
                        "erro": "CLICK_ONLY_FAILED",
                        "resposta": f"❌ Falha ao clicar via CDP (headless): {stderr_output}",
                    }
                payload, err = _executar_bot_ate_json(cmd_click, timeout_s=120)
                if err:
                    return {"sucesso": False, "erro": "BOT_SEM_STATUS", "resposta": f"❌ Não consegui confirmar o resultado: {err}"}
                pagamento_ok = bool(payload.get("pagamento_sucesso")) if payload else False
                comp = (payload or {}).get("comprovante") or {}
                if pagamento_ok:
                    # ✅ Persistir comprovante localmente para evitar bilhetar Serpro no futuro
                    try:
                        from services.mercante_afrmm_pagamentos_repository import MercanteAfrmmPagamentosRepository

                        repo = MercanteAfrmmPagamentosRepository()
                        repo.registrar_sucesso(
                            processo_referencia=proc,
                            ce_mercante=ce,
                            comprovante=comp,
                            screenshot_relpath=(f"mercante/{receipt_filename}" if receipt_url else None),
                        )
                    except Exception:
                        pass
                    linhas = [
                        "✅ **Pagamento AFRMM concluído com sucesso.**",
                        f"**Processo**: {proc}",
                        f"**CE-Mercante**: {ce}",
                    ]
                    if receipt_url:
                        linhas.append(f"🧾 **Comprovante (print)**: [abrir imagem]({receipt_url})")
                    if comp:
                        # mostrar os campos mais úteis
                        for k in ("pedido", "banco", "agencia", "conta_corrente", "valor_total_debito"):
                            if comp.get(k):
                                label = {
                                    "pedido": "Nº do Pedido",
                                    "banco": "Banco",
                                    "agencia": "Agência",
                                    "conta_corrente": "Conta Corrente",
                                    "valor_total_debito": "Valor Total do Débito",
                                }.get(k, k)
                                linhas.append(f"**{label}**: {comp.get(k)}")
                    return {"sucesso": True, "resposta": "\n".join(linhas), "dados": {"receipt_url": receipt_url, "payload": payload}}
                # Falhou / não detectou sucesso
                return {
                    "sucesso": False,
                    "erro": "PAGAMENTO_NAO_CONFIRMADO",
                    "resposta": (
                        "❌ Não consegui confirmar **\"Débito efetuado com sucesso\"** na tela.\n\n"
                        + (f"🧾 Print capturado: {receipt_url}\n" if receipt_url else "")
                        + "Verifique a tela do Mercante para detalhes."
                    ),
                    "dados": {"receipt_url": receipt_url, "payload": payload},
                }
            except Exception as e:
                logger.error(f"[Mercante] ❌ Erro ao executar clique-only via CDP: {e}", exc_info=True)
                return {"sucesso": False, "erro": "CLICK_ONLY_ERROR", "resposta": f"❌ Erro: {str(e)}"}

        # ✅ MODO FULL (padrão): Executar bot COMPLETO (login + navegação + preenchimento + clique)
        # Não depende de janela pré-existente.
        plan_exec = self._montar_plano(proc, ce, parcela=parcela, clicar_enviar=True)
        
        # Montar comando completo (login + navegação + preenchimento + clique)
        cmd_exec = plan_exec.comando

        # ✅ Determinar modo headless UMA vez (evita manipulação frágil de string)
        mercante_headless = os.getenv("MERCANTE_HEADLESS", "").strip().lower() in ("true", "1", "yes")
        
        # Adicionar dados bancários se disponíveis
        bb_codigo = os.getenv("BB_CODIGO")
        bb_agencia = os.getenv("BB_TEST_AGENCIA")
        bb_conta_dv = os.getenv("BB_TEST_CONTA_DV")
        if bb_codigo and bb_agencia and bb_conta_dv:
            cmd_exec += f" --bb_codigo {shlex.quote(bb_codigo)}"
            cmd_exec += f" --bb_agencia {shlex.quote(bb_agencia)}"
            cmd_exec += f" --bb_conta_dv {shlex.quote(bb_conta_dv)}"
        
        # ✅ IMPORTANTE: manter janela aberta para acompanhar popup/confirmação (somente com UI)
        # ⚠️ Não adicionar esses flags em headless.
        if not mercante_headless:
            cmd_exec += " --keep_open --keep_open_seconds 600"

        # ✅ CRÍTICO: após confirmação do usuário, clicar no botão "Pagar AFRMM"
        # (o script por padrão NÃO clica por segurança)
        cmd_exec += " --clicar_pagar"

        # ✅ CRÍTICO: aceitar o popup de confirmação (equivale a clicar em OK)
        # Este comando só é disparado após confirmação explícita do usuário ("sim") via pending intent.
        cmd_exec += " --confirmar_popup"

        # ✅ Comprovante (print) da tela final
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            downloads_dir = os.path.join(project_root, "downloads", "mercante")
            os.makedirs(downloads_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_proc = re.sub(r"[^A-Z0-9_.-]+", "_", proc)
            safe_ce = re.sub(r"[^0-9]+", "", str(ce))
            receipt_filename = f"afrmm_receipt_{safe_proc}_{safe_ce}_{ts}.png"
            receipt_path = os.path.join(downloads_dir, receipt_filename)
            cmd_exec += f" --screenshot {shlex.quote(receipt_path)}"
            receipt_url = f"/api/download/mercante/{receipt_filename}"
        except Exception:
            receipt_path = None
            receipt_url = None

        # ✅ Retorno estruturado para a UI (sem fechar navegador)
        cmd_exec += " --emit_json"

        # ✅ Opcional: --headless se MERCANTE_HEADLESS estiver configurado
        if mercante_headless:
            cmd_exec += " --headless"

        # ✅ CONFIRMAÇÃO (21/01/2026): Em headless, também devemos aguardar o resultado real.
        # Antes: headless retornava "iniciado" apenas com returncode==0 (sem comprovante/print),
        # o que dá falsa sensação de sucesso.
        #
        # Agora: tanto headless quanto UI aguardam o marcador __MAIKE_JSON__ do bot (--emit_json),
        # e retornam sucesso/falha + print (se configurado).
        logger.info(f"[Mercante] Executando bot COMPLETO e aguardando confirmação do pagamento (headless={mercante_headless}): {proc}")
        try:
            payload, err = _executar_bot_ate_json(cmd_exec, timeout_s=180)
            if err:
                return {
                    "sucesso": False,
                    "erro": "BOT_SEM_STATUS",
                    "resposta": f"❌ Não consegui confirmar o resultado do pagamento: {err}",
                    "dados": {"receipt_url": receipt_url},
                }

            pagamento_ok = bool(payload.get("pagamento_sucesso")) if payload else False
            comp = (payload or {}).get("comprovante") or {}
            screenshot_ok = payload.get("screenshot_ok", True) if payload else True  # Default True para compatibilidade
            screenshot_path_payload = (payload or {}).get("screenshot_path")

            # ✅ CRÍTICO (21/01/2026): Verificar se arquivo de screenshot realmente existe
            receipt_path_verificado = None
            receipt_url_verificado = None
            if screenshot_path_payload:
                if os.path.exists(screenshot_path_payload) and os.path.getsize(screenshot_path_payload) > 0:
                    receipt_path_verificado = screenshot_path_payload
                    receipt_url_verificado = receipt_url
                elif screenshot_ok:
                    # Screenshot foi marcado como OK no payload mas arquivo não existe - inconsistência
                    logger.warning(f"[Mercante] ⚠️ Screenshot marcado como OK no payload mas arquivo não existe: {screenshot_path_payload}")
                else:
                    # Screenshot falhou (esperado)
                    logger.warning(f"[Mercante] ⚠️ Screenshot não foi capturado: {screenshot_path_payload}")

            if pagamento_ok:
                # ✅ Persistir comprovante localmente para evitar bilhetar Serpro no futuro
                # ✅ IMPORTANTE: Registrar mesmo se screenshot falhou (pagamento foi bem-sucedido)
                try:
                    from services.mercante_afrmm_pagamentos_repository import MercanteAfrmmPagamentosRepository

                    repo = MercanteAfrmmPagamentosRepository()
                    repo.registrar_sucesso(
                        processo_referencia=proc,
                        ce_mercante=ce,
                        comprovante=comp,
                        screenshot_relpath=(f"mercante/{receipt_filename}" if receipt_path_verificado else None),
                    )
                except Exception as e:
                    logger.error(f"[Mercante] ⚠️ Erro ao registrar pagamento no BD: {e}", exc_info=True)
                
                linhas = [
                    "✅ **Pagamento AFRMM concluído com sucesso.**",
                    f"**Processo**: {proc}",
                    f"**CE-Mercante**: {ce}",
                ]
                
                # ✅ Mostrar comprovante apenas se arquivo foi realmente capturado
                if receipt_url_verificado:
                    linhas.append(f"🧾 **Comprovante (print)**: [abrir imagem]({receipt_url_verificado})")
                elif screenshot_path_payload:
                    # Screenshot foi solicitado mas falhou - avisar mas não bloquear sucesso
                    linhas.append("⚠️ **Aviso**: Comprovante (print) não foi capturado, mas pagamento foi confirmado como bem-sucedido.")
                    linhas.append("💡 O pagamento foi registrado no sistema. Verifique manualmente no Mercante se necessário.")
                
                if comp:
                    for k in ("pedido", "banco", "agencia", "conta_corrente", "valor_total_debito"):
                        if comp.get(k):
                            label = {
                                "pedido": "Nº do Pedido",
                                "banco": "Banco",
                                "agencia": "Agência",
                                "conta_corrente": "Conta Corrente",
                                "valor_total_debito": "Valor Total do Débito",
                            }.get(k, k)
                            linhas.append(f"**{label}**: {comp.get(k)}")
                
                return {
                    "sucesso": True,
                    "resposta": "\n".join(linhas),
                    "dados": {
                        "receipt_url": receipt_url_verificado,  # None se screenshot falhou
                        "screenshot_ok": bool(receipt_path_verificado),
                        "payload": payload
                    }
                }

            return {
                "sucesso": False,
                "erro": "PAGAMENTO_NAO_CONFIRMADO",
                "resposta": (
                    "❌ Não consegui confirmar **\"Débito efetuado com sucesso\"** na tela.\n\n"
                    + (f"🧾 Print capturado: {receipt_url}\n" if receipt_url else "")
                    + "Verifique a tela do Mercante para detalhes."
                ),
                "dados": {"receipt_url": receipt_url, "payload": payload},
            }
        except Exception as e:
            logger.error(f"[Mercante] ❌ Erro ao disparar bot em background: {e}", exc_info=True)
            return {
                "sucesso": False,
                "erro": "BOT_EXECUTION_ERROR",
                "resposta": f"❌ Erro ao iniciar robô: {str(e)}",
            }
    
    def _executar_em_background_custom(self, comando: str) -> None:
        """Executa comando em background (wrapper para permitir comando customizado)."""
        subprocess.Popen(
            comando,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

