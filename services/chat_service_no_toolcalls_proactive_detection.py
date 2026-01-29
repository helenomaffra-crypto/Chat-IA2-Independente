"""
Detecção proativa quando a IA NÃO retorna tool_calls (resposta vem como string).

Este módulo existe para tirar um bloco enorme de "heurísticas/padrões" do `ChatService`,
mantendo o comportamento (e facilitando evoluções) sem deixar `chat_service.py` inchado.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def aplicar_deteccao_proativa_sem_toolcalls(
    *,
    chat_service: Any,
    mensagem: str,
    tool_calls: Optional[List[Dict[str, Any]]],
    resposta_ia_raw: Any,
    resposta_ia: Optional[str],
    deve_chamar_ia_para_refinar: bool,
    ja_processou_categoria_situacao: bool,
    resposta_ia_categoria_situacao: Optional[str],
    logger_override: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Aplica detecção proativa para casos em que a IA retorna string (sem tool_calls).

    Importante:
    - Mantém a lógica heurística existente, apenas extraindo do `ChatService`.
    - Retorna apenas o que o `ChatService` precisa preservar fora do bloco:
      `resposta_ia`, `ja_processou_categoria_situacao`, `resposta_ia_categoria_situacao`.
    """
    _logger = logger_override or logger

    # Base: resposta string, sem tool calls.
    mensagem_lower = (mensagem or "").lower()
    resposta_ia = resposta_ia_raw if resposta_ia_raw else (resposta_ia or "")

    # Se veio do precheck para refinar, a resposta da IA já foi usada acima no ChatService.
    # Aqui preservamos o comportamento original: o bloco pode sobrescrever `resposta_ia`.
    if deve_chamar_ia_para_refinar and resposta_ia_raw:
        try:
            resposta_ia = str(resposta_ia_raw)
        except Exception:
            pass

    resposta_ia_periodo = None

    # ✅ PRIORIDADE MÁXIMA: Detectar perguntas sobre consultas bilhetadas pendentes (ANTES de tudo)
    eh_pergunta_consultas_pendentes = bool(
        re.search(r"consultas?\s+pendentes?|consultas?\s+aguardando|consultas?\s+estão|quais\s+consultas?", mensagem_lower)
    )
    if eh_pergunta_consultas_pendentes:
        _logger.warning(
            "⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Pergunta sobre consultas pendentes detectada mas IA não chamou "
            "listar_consultas_bilhetadas_pendentes. Forçando chamada..."
        )
        try:
            resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                "listar_consultas_bilhetadas_pendentes",
                {"status": "pendente", "limite": 50},
                mensagem_original=mensagem,
            )
            if resultado_forcado.get("resposta"):
                resposta_ia = resultado_forcado.get("resposta")
                _logger.info("✅✅✅ Resposta da função listar_consultas_bilhetadas_pendentes forçada (PRIORIDADE MÁXIMA)")
            elif resultado_forcado.get("mensagem"):
                resposta_ia = resultado_forcado.get("mensagem")
            else:
                _logger.warning("⚠️ Função listar_consultas_bilhetadas_pendentes não retornou resposta.")
        except Exception as e:
            _logger.error(f"❌ Erro ao forçar chamada de listar_consultas_bilhetadas_pendentes: {e}", exc_info=True)

    # ✅ PRIORIDADE MÁXIMA: Detectar comandos de aprovar/rejeitar consultas (ANTES de tudo)
    eh_comando_aprovar_todas = bool(re.search(r"aprovar\s+(?:todas?\s+)?(?:as\s+)?consultas?", mensagem_lower))
    eh_comando_rejeitar_todas = bool(re.search(r"rejeitar\s+(?:todas?\s+)?(?:as\s+)?consultas?", mensagem_lower))
    eh_comando_aprovar = bool(re.search(r"aprovar\s+(?:a\s+)?consulta\s*#?(\d+)|aprovar\s+#?(\d+)", mensagem_lower))
    eh_comando_rejeitar = bool(re.search(r"rejeitar\s+(?:a\s+)?consulta\s*#?(\d+)|rejeitar\s+#?(\d+)", mensagem_lower))

    if eh_comando_aprovar_todas or eh_comando_rejeitar_todas or eh_comando_aprovar or eh_comando_rejeitar:
        try:
            nome_funcao = None
            args: Dict[str, Any] = {}

            if eh_comando_aprovar_todas:
                nome_funcao = "aprovar_consultas_bilhetadas"
                args = {"aprovar_todas": True}
                _logger.warning('⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Comando "aprovar todas" detectado. Forçando chamada...')
            elif eh_comando_rejeitar_todas:
                nome_funcao = "rejeitar_consultas_bilhetadas"
                args = {"rejeitar_todas": True}
                _logger.warning('⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Comando "rejeitar todas" detectado. Forçando chamada...')
            elif eh_comando_aprovar or eh_comando_rejeitar:
                match_aprovar = re.search(r"aprovar\s+(?:a\s+)?consulta\s*#?(\d+)|aprovar\s+#?(\d+)", mensagem_lower)
                match_rejeitar = re.search(r"rejeitar\s+(?:a\s+)?consulta\s*#?(\d+)|rejeitar\s+#?(\d+)", mensagem_lower)

                numero_consulta = None
                if match_aprovar:
                    numero_consulta = match_aprovar.group(1) or match_aprovar.group(2)
                    nome_funcao = "aprovar_consultas_bilhetadas"
                elif match_rejeitar:
                    numero_consulta = match_rejeitar.group(1) or match_rejeitar.group(2)
                    nome_funcao = "rejeitar_consultas_bilhetadas"

                if numero_consulta:
                    numero_int = int(numero_consulta)
                    args = {"ids": [numero_int]}
                    _logger.warning(f'⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Comando "{nome_funcao}" detectado para consulta {numero_int}. Forçando chamada...')

            if nome_funcao and args:
                resultado_forcado = chat_service._executar_funcao_tool(nome_funcao, args, mensagem_original=mensagem)  # noqa: SLF001
                if resultado_forcado.get("resposta"):
                    resposta_ia = resultado_forcado.get("resposta")
                    _logger.info(f"✅✅✅ Resposta da função {nome_funcao} forçada (PRIORIDADE MÁXIMA)")
                elif resultado_forcado.get("mensagem"):
                    resposta_ia = resultado_forcado.get("mensagem")
                else:
                    _logger.warning(f"⚠️ Função {nome_funcao} não retornou resposta.")
        except Exception as e:
            _logger.error(f"❌ Erro ao forçar chamada de aprovar/rejeitar consultas: {e}", exc_info=True)

    # ✅ PRIORIDADE MÁXIMA: Detectar comandos de executar consultas aprovadas (ANTES de tudo)
    eh_comando_executar_todas = bool(
        re.search(
            r"(?:executar|execultar)\s+(?:todas?\s+)?(?:as\s+)?(?:consultas?\s+)?(?:aprovadas?)?|"
            r"(?:executar|execultar)\s+(?:todas?\s+)?(?:as\s+)?aprovadas?",
            mensagem_lower,
        )
    )
    eh_comando_executar = bool(
        re.search(r"(?:executar|execultar)\s+(?:a\s+)?consulta\s*#?(\d+)|(?:executar|execultar)\s+#?(\d+)", mensagem_lower)
    )
    eh_comando_executar_aprovadas = bool(re.search(r"(?:executar|execultar)\s+consultas?\s+aprovadas?", mensagem_lower))

    if eh_comando_executar_todas or eh_comando_executar or eh_comando_executar_aprovadas:
        try:
            nome_funcao = "executar_consultas_aprovadas"
            args: Dict[str, Any] = {}

            if eh_comando_executar_todas or eh_comando_executar_aprovadas:
                args = {"executar_todas": True}
                _logger.warning('⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Comando "executar consultas aprovadas" detectado. Forçando chamada...')
            elif eh_comando_executar:
                match_executar = re.search(r"executar\s+(?:a\s+)?consulta\s*#?(\d+)|executar\s+#?(\d+)", mensagem_lower)
                numero_consulta = (match_executar.group(1) or match_executar.group(2)) if match_executar else None
                if numero_consulta:
                    numero_int = int(numero_consulta)
                    args = {"ids": [numero_int]}
                    _logger.warning(f'⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Comando "executar consulta {numero_int}" detectado. Forçando chamada...')

            if args:
                resultado_forcado = chat_service._executar_funcao_tool(nome_funcao, args, mensagem_original=mensagem)  # noqa: SLF001
                if resultado_forcado.get("resposta"):
                    resposta_ia = resultado_forcado.get("resposta")
                    _logger.info(f"✅✅✅ Resposta da função {nome_funcao} forçada (PRIORIDADE MÁXIMA)")
                elif resultado_forcado.get("mensagem"):
                    resposta_ia = resultado_forcado.get("mensagem")
                else:
                    _logger.warning(f"⚠️ Função {nome_funcao} não retornou resposta.")
        except Exception as e:
            _logger.error(f"❌ Erro ao forçar chamada de executar consultas aprovadas: {e}", exc_info=True)

    # Se já processou consultas com sucesso, pular resto
    if (
        (eh_pergunta_consultas_pendentes or eh_comando_aprovar or eh_comando_rejeitar or eh_comando_aprovar_todas or eh_comando_rejeitar_todas or eh_comando_executar_todas or eh_comando_executar or eh_comando_executar_aprovadas)
        and resposta_ia
        and len(str(resposta_ia)) > 50
    ):
        _logger.info("✅ Consultas processadas com sucesso. Pulando detecção de períodos temporais e categorias.")
        return {
            "resposta_ia": resposta_ia,
            "ja_processou_categoria_situacao": ja_processou_categoria_situacao,
            "resposta_ia_categoria_situacao": resposta_ia_categoria_situacao,
        }

    # ---------------------------------------------------------------------
    # Categoria + situação específica (antes de períodos temporais)
    # ---------------------------------------------------------------------
    categoria_detectada = chat_service._extrair_categoria_da_mensagem(mensagem)  # noqa: SLF001
    situacao_detectada = None

    categoria_situacao_processada = False

    eh_pergunta_quando_chegaram = bool(re.search(r"quando\s+(?:chegaram|chegou|chegara)", mensagem_lower))
    eh_pergunta_quando_chegam = bool(re.search(r"quando\s+(?:chegam|chega)", mensagem_lower))

    if not (eh_pergunta_quando_chegaram or eh_pergunta_quando_chegam):
        if re.search(r"\b(?:desembarac|desembaraç|di_desembaracada)", mensagem_lower):
            situacao_detectada = "di_desembaracada"
        elif re.search(r"\b(?:registrad|registr)\w*\b", mensagem_lower):
            situacao_detectada = "registrado"
        elif re.search(r"\b(?:entregu|entreg)\w*\b", mensagem_lower):
            situacao_detectada = "entregue"
        elif re.search(r"\b(?:armazenad|armazen)\w*\b", mensagem_lower):
            situacao_detectada = "armazenado"

    _logger.info(
        f'🔍 Detecção proativa: categoria={categoria_detectada}, situação={situacao_detectada}, '
        f'mensagem="{mensagem_lower}", é_pergunta_quando_chegaram={eh_pergunta_quando_chegaram}, '
        f'é_pergunta_quando_chegam={eh_pergunta_quando_chegam}'
    )

    if categoria_detectada and situacao_detectada and not (eh_pergunta_quando_chegaram or eh_pergunta_quando_chegam):
        _logger.warning(
            f'⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Categoria {categoria_detectada} + situação {situacao_detectada} detectada na mensagem "{mensagem}". '
            "Forçando listar_processos_por_situacao..."
        )
        try:
            resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                "listar_processos_por_situacao",
                {"categoria": categoria_detectada, "situacao": situacao_detectada, "limite": 200},
                mensagem_original=mensagem,
            )
            _logger.info(
                f'🔍 Resultado da função forçada: sucesso={resultado_forcado.get("sucesso")}, '
                f'tem_resposta={bool(resultado_forcado.get("resposta"))}, tem_mensagem={bool(resultado_forcado.get("mensagem"))}'
            )
            if resultado_forcado.get("resposta"):
                resposta_ia_categoria_situacao = resultado_forcado.get("resposta")
                _logger.info(
                    "✅✅✅ Resposta da função listar_processos_por_situacao forçada (PRIORIDADE MÁXIMA) - "
                    f"tamanho: {len(resposta_ia_categoria_situacao)}"
                )
                categoria_situacao_processada = True
            elif resultado_forcado.get("mensagem"):
                resposta_ia_categoria_situacao = resultado_forcado.get("mensagem")
                _logger.info("✅✅✅ Mensagem da função listar_processos_por_situacao forçada (PRIORIDADE MÁXIMA)")
                categoria_situacao_processada = True
            else:
                _logger.warning(
                    "⚠️ Função listar_processos_por_situacao não retornou resposta nem mensagem. "
                    f"resultado_forcado={resultado_forcado}"
                )
        except Exception as e:
            _logger.error(f"❌ Erro ao forçar chamada de listar_processos_por_situacao: {e}", exc_info=True)

    if categoria_situacao_processada and resposta_ia_categoria_situacao:
        resposta_ia = resposta_ia_categoria_situacao
        ja_processou_categoria_situacao = True
        _logger.info(
            "✅✅✅ Categoria+situação processadas com sucesso. "
            f"Usando resposta direta (tamanho: {len(resposta_ia)}) e pulando detecção de períodos temporais e categorias."
        )
        return {
            "resposta_ia": resposta_ia,
            "ja_processou_categoria_situacao": ja_processou_categoria_situacao,
            "resposta_ia_categoria_situacao": resposta_ia_categoria_situacao,
        }

    # ---------------------------------------------------------------------
    # Pergunta genérica sobre chegada (antes de períodos temporais)
    # ---------------------------------------------------------------------
    eh_pergunta_generica_chegada = bool(
        re.search(
            r"(?:quais|como|mostre|o\s+que\s+tem)\s+(?:os|as|processos?|pra|para)?\s*(?:estao|estão|esta|está)\s+"
            r"(?:chegando|pra\s+chegar|para\s+chegar|vai\s+chegar|vão\s+chegar)",
            mensagem_lower,
        )
    ) or bool(
        re.search(r"quais\s+[a-z]{3}\s+(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar)", mensagem_lower)
    ) or bool(re.search(r"o\s+que\s+tem\s+(?:pra|para)\s+chegar", mensagem_lower))

    categoria_chegada_generica = chat_service._extrair_categoria_da_mensagem(mensagem) if eh_pergunta_generica_chegada else None  # noqa: SLF001
    if not categoria_chegada_generica and eh_pergunta_generica_chegada:
        match_cat_chegada = re.search(
            r"quais\s+(?:os|as)?\s*([a-z]{3})\s+(?:que\s+)?(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar)",
            mensagem_lower,
        ) or re.search(r"quais\s+([a-z]{3})\s+(?:estao|estão|esta|está)\s+(?:chegando|pra\s+chegar|para\s+chegar)", mensagem_lower)
        if match_cat_chegada:
            cat_candidata = match_cat_chegada.group(1).upper()
            palavras_ignorar = {
                "DOS",
                "DAS",
                "ESTAO",
                "ESTÃO",
                "COM",
                "SÃO",
                "SAO",
                "TEM",
                "TÊM",
                "POR",
                "QUE",
                "QUAL",
                "COMO",
                "EST",
                "PAR",
                "UMA",
                "UNS",
                "TODOS",
                "TODAS",
                "TODO",
                "TODA",
                "OS",
                "AS",
                "VEM",
                "VÊM",
                "SEMANA",
                "PROXIMA",
                "PRÓXIMA",
                "MES",
                "MÊS",
                "DIA",
                "DIAS",
                "HOJE",
                "AMANHA",
                "AMANHÃ",
                "ESSA",
                "ESTA",
                "NESSA",
                "NESTA",
                "VAO",
                "VÃO",
                "IRÃO",
                "IRAO",
                "CHEGAM",
                "CHEGA",
                "CHEGAR",
                "CHEGARA",
                "CHEGARAM",
                "PRA",
                "PARA",
            }
            if cat_candidata not in palavras_ignorar and len(cat_candidata) == 3:
                categoria_chegada_generica = cat_candidata
                _logger.info(f"✅ Categoria detectada na pergunta de chegada: {categoria_chegada_generica}")

    ja_processou_pergunta_chegada_generica = False
    if eh_pergunta_generica_chegada:
        _logger.warning(
            f"⚠️⚠️⚠️ PRIORIDADE MÁXIMA: Pergunta genérica sobre chegada detectada. "
            f"Categoria: {categoria_chegada_generica or 'TODAS'}"
        )
        try:
            if categoria_chegada_generica:
                _logger.info(
                    f'🔍 Pergunta genérica sobre chegada COM categoria {categoria_chegada_generica}. '
                    'Usando listar_processos_por_eta com filtro "futuro" (ETA >= hoje, sem limite de mês)...'
                )
                resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                    "listar_processos_por_eta",
                    {"filtro_data": "futuro", "categoria": categoria_chegada_generica, "limite": 200},
                    mensagem_original=mensagem,
                )
            else:
                _logger.info(
                    '🔍 Pergunta genérica sobre chegada SEM categoria. '
                    'Usando listar_processos_por_eta com filtro "mes" (ETA neste mês, todas as categorias)...'
                )
                resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                    "listar_processos_por_eta",
                    {"filtro_data": "mes", "limite": 500},
                    mensagem_original=mensagem,
                )

            if resultado_forcado.get("resposta"):
                resposta_ia = resultado_forcado.get("resposta")
                _logger.info(
                    "✅✅✅ Resposta da função forçada (PERGUNTA GENÉRICA CHEGADA) - "
                    f"tamanho: {len(resposta_ia)}"
                )
            elif resultado_forcado.get("mensagem"):
                resposta_ia = resultado_forcado.get("mensagem")
                _logger.info("✅✅✅ Mensagem da função forçada (PERGUNTA GENÉRICA CHEGADA)")
            else:
                _logger.warning("⚠️ Função não retornou resposta para pergunta genérica sobre chegada.")
        except Exception as e:
            _logger.error(f"❌ Erro ao forçar chamada para pergunta genérica sobre chegada: {e}", exc_info=True)

        if resposta_ia and len(str(resposta_ia)) > 50:
            _logger.info("✅ Pergunta genérica sobre chegada processada com sucesso. Pulando detecção de períodos temporais e categorias.")
            ja_processou_pergunta_chegada_generica = True

    # ---------------------------------------------------------------------
    # Períodos temporais (ETA)
    # ---------------------------------------------------------------------
    periodo_temporal_detectado = None
    periodo_temporal_categoria = None
    periodo_temporal_passado = False
    periodo_temporal_data_especifica = None
    periodo_temporal_data_fim = None

    if eh_pergunta_generica_chegada:
        # Evitar herdar contexto de período temporal.
        periodo_temporal_detectado = None
        periodo_temporal_categoria = None
        periodo_temporal_passado = False
        periodo_temporal_data_especifica = None
        periodo_temporal_data_fim = None
        _logger.info("✅ Pergunta genérica sobre chegada detectada. Ignorando detecção de período temporal (evitar herdar contexto).")
    else:
        verbo_passado = bool(re.search(r"\b(?:chegaram|chegou|chegara)\b", mensagem_lower))
        if "quando" in mensagem_lower:
            verbo_passado = False

        meses_nomes = {
            "janeiro": 1,
            "fevereiro": 2,
            "março": 3,
            "marco": 3,
            "abril": 4,
            "maio": 5,
            "junho": 6,
            "julho": 7,
            "agosto": 8,
            "setembro": 9,
            "outubro": 10,
            "novembro": 11,
            "dezembro": 12,
        }

        mes_detectado = None
        ano_detectado = None

        for mes_nome, mes_num in meses_nomes.items():
            if re.search(rf"\b{mes_nome}\b", mensagem_lower):
                mes_detectado = mes_num
                ano_match = re.search(rf"{mes_nome}[\s/]*(\d{{4}})", mensagem_lower)
                if ano_match:
                    ano_detectado = int(ano_match.group(1))
                else:
                    from datetime import datetime

                    hoje_temp = datetime.now()
                    ano_detectado = hoje_temp.year if mes_num >= hoje_temp.month else (hoje_temp.year + 1)
                break

        if mes_detectado:
            periodo_temporal_detectado = "data_especifica"
            periodo_temporal_passado = False
            from datetime import datetime
            from calendar import monthrange

            if not ano_detectado:
                hoje_temp = datetime.now()
                ano_detectado = hoje_temp.year if mes_detectado >= hoje_temp.month else (hoje_temp.year + 1)

            primeiro_dia = datetime(ano_detectado, mes_detectado, 1)
            ultimo_dia_mes = monthrange(ano_detectado, mes_detectado)[1]
            ultimo_dia = datetime(ano_detectado, mes_detectado, ultimo_dia_mes)

            periodo_temporal_data_especifica = primeiro_dia.strftime("%d/%m/%Y")
            periodo_temporal_data_fim = ultimo_dia.strftime("%d/%m/%Y")
            _logger.info(
                f"🔍 Mês por nome detectado: {mes_detectado}/{ano_detectado} "
                f"(primeiro dia: {periodo_temporal_data_especifica}, último dia: {periodo_temporal_data_fim})"
            )
        elif re.search(
            r"(?:semana\s*(?:q\s*|que\s*)?vem|semana\s*(?:q\s*|que\s*)?vêm|próxima\s*semana|proxima\s*semana|"
            r"chegam\s+semana\s*(?:q\s*|que\s*)?vem|chegam\s+semana\s*(?:q\s*|que\s*)?vêm|"
            r"vao\s+chegar\s+semana\s*(?:q\s*|que\s*)?vem|vão\s+chegar\s+semana\s*(?:q\s*|que\s*)?vem)",
            mensagem_lower,
        ):
            periodo_temporal_detectado = "proxima_semana"
            periodo_temporal_passado = False
        elif re.search(r"esta\s*semana|nesta\s*semana|chegam\s+(?:esta|nesta)\s*semana|chegaram\s+(?:esta|nesta)\s*semana", mensagem_lower):
            periodo_temporal_detectado = "semana"
            periodo_temporal_passado = verbo_passado
        elif re.search(r"(?:mês\s+que\s+vem|mes\s+que\s+vem|próximo\s+mês|proximo\s+mes|vao\s+chegar\s+m[êe]s\s+que\s+vem|vão\s+chegar\s+m[êe]s\s+que\s+vem)", mensagem_lower):
            periodo_temporal_detectado = "proximo_mes"
            periodo_temporal_passado = False
        elif re.search(r"este mês|neste mês|neste mes", mensagem_lower):
            periodo_temporal_detectado = "mes"
            periodo_temporal_passado = verbo_passado
        elif re.search(r"amanhã|amanha", mensagem_lower):
            periodo_temporal_detectado = "amanha"
            periodo_temporal_passado = False
        elif re.search(r"hoje", mensagem_lower):
            periodo_temporal_detectado = "hoje"
            periodo_temporal_passado = verbo_passado

    ja_processou_periodo_temporal = False
    if periodo_temporal_detectado:
        periodo_temporal_categoria = chat_service._extrair_categoria_da_mensagem(mensagem)  # noqa: SLF001
        tem_listar_eta = (
            any(tc.get("function", {}).get("name") == "listar_processos_por_eta" for tc in (tool_calls or []))
            if tool_calls
            else False
        )

        if not tem_listar_eta:
            _logger.warning(
                f'🔍 Período temporal "{periodo_temporal_detectado}" '
                f'{"(PASSADO)" if periodo_temporal_passado else "(FUTURO)"} detectado mas IA não chamou '
                "listar_processos_por_eta. Forçando chamada..."
            )
            try:
                args_eta: Dict[str, Any] = {"filtro_data": periodo_temporal_detectado, "limite": 200}
                if periodo_temporal_detectado == "data_especifica" and periodo_temporal_data_especifica:
                    args_eta["data_especifica"] = periodo_temporal_data_especifica
                    _logger.info(
                        f"🔍 Usando data específica para mês: {periodo_temporal_data_especifica} "
                        f"(mês completo: {periodo_temporal_data_especifica} até {periodo_temporal_data_fim})"
                    )
                if periodo_temporal_categoria:
                    args_eta["categoria"] = periodo_temporal_categoria
                if periodo_temporal_passado:
                    _logger.info(
                        f"⚠️ Período temporal no PASSADO detectado: {periodo_temporal_detectado} - ajustar função para incluir passado"
                    )
                resultado_forcado = chat_service._executar_funcao_tool("listar_processos_por_eta", args_eta, mensagem_original=mensagem)  # noqa: SLF001
                _logger.info(
                    f'🔍 Resultado da função forçada (ETA): sucesso={resultado_forcado.get("sucesso")}, '
                    f'tem_resposta={bool(resultado_forcado.get("resposta"))}, tem_mensagem={bool(resultado_forcado.get("mensagem"))}'
                )
                if resultado_forcado.get("resposta"):
                    resposta_ia_periodo = resultado_forcado.get("resposta")
                    _logger.info(
                        f'✅ Usando resposta da função forçada para período temporal "{periodo_temporal_detectado}" '
                        f"(tamanho: {len(resposta_ia_periodo)})"
                    )
                elif resultado_forcado.get("mensagem"):
                    resposta_ia_periodo = resultado_forcado.get("mensagem")
                    _logger.info(f'✅ Usando mensagem da função forçada para período temporal "{periodo_temporal_detectado}"')
                else:
                    _logger.warning(
                        f'⚠️ Função forçada (ETA) não retornou resposta nem mensagem para período "{periodo_temporal_detectado}". '
                        "Usando resposta da IA como fallback."
                    )
                    resposta_ia_periodo = None
            except Exception as e:
                _logger.error(
                    f'❌ Erro ao forçar chamada de listar_processos_por_eta para período "{periodo_temporal_detectado}": {e}',
                    exc_info=True,
                )
                resposta_ia_periodo = None

        ja_processou_periodo_temporal = resposta_ia_periodo is not None
        if resposta_ia_periodo:
            resposta_ia = resposta_ia_periodo

    # ---------------------------------------------------------------------
    # Detecção de categoria/situação/pendência/bloqueio (pós período temporal)
    # ---------------------------------------------------------------------
    eh_pergunta_duimp_registrada = bool(re.search(r"tem\s+duimp\s+registrada\s+para|tem\s+duimp\s+para", mensagem_lower))

    situacoes_comuns = {
        "desembaraçado": "desembaraçado",
        "desembaracado": "desembaraçado",
        "desembaraçada": "desembaraçado",
        "desembaracada": "desembaraçado",
        "desembaraco": "desembaraçado",
        "registrada": "registrado",
        "entregue": "entregue",
        "armazenado": "armazenado",
        "armazenada": "armazenado",
        "manifestado": "manifestado",
        "manifestada": "manifestado",
    }

    situacao_detectada = None
    if not eh_pergunta_duimp_registrada:
        for palavra, situacao in situacoes_comuns.items():
            if palavra in mensagem_lower:
                if (palavra == "registrado" or palavra == "registrada") and ("tem duimp" in mensagem_lower or "duimp registrada" in mensagem_lower):
                    continue
                situacao_detectada = situacao
                break

    tem_pendencia = bool(re.search(r"pend[êe]ncia|pendente", mensagem_lower))
    tem_bloqueio = bool(re.search(r"\bbloqueio\b|\bbloqueados?\b|\bbloqueadas?\b", mensagem_lower))

    categoria_detectada_direta = chat_service._extrair_categoria_da_mensagem(mensagem)  # noqa: SLF001

    match_categoria = None
    if categoria_detectada_direta:
        class MatchSimulado:
            def __init__(self, cat: str):
                self.cat = cat

            def group(self, n: int) -> Optional[str]:
                if n == 1:
                    return self.cat.lower()
                return None

        match_categoria = MatchSimulado(categoria_detectada_direta)
    else:
        padrao_categoria_pergunta = (
            r"(?:como|quais|mostre|liste|como\s+estao|como\s+estão)\s+([a-z]{3})\b.*?"
            r"(?:processos|processo|estao|estão|com\s+)|"
            r"(?:como|quais|mostre|liste|como\s+estao|como\s+estão).*(?:processos|processo)\s+([a-z]{3})\b|"
            r"(?:^|\s)([a-z]{3})\b.*?(?:processos|processo)"
        )
        match_categoria = re.search(padrao_categoria_pergunta, mensagem_lower)

        if match_categoria:
            cat_candidata = (match_categoria.group(1) or match_categoria.group(2) or match_categoria.group(3) or "").strip().lower()
            palavras_ignorar = {"dos", "das", "estao", "estão", "com", "são", "sao", "tem", "têm", "por", "que", "qual", "como", "est", "par", "uma", "uns", "todos", "todas", "todo", "toda"}
            if cat_candidata in palavras_ignorar:
                match_categoria = None
            elif len(cat_candidata) == 3:
                if not re.search(rf"\b{re.escape(cat_candidata)}\b", mensagem_lower.replace("processos", " ").replace("processo", " ")):
                    match_categoria = None
        else:
            match_categoria = None

    padrao_generico = r"(?:quais|mostre|liste|como\s+estao|como\s+estão).*(?:processos|processo).*(?:estao|estão|com)"
    match_generico = bool(re.search(padrao_generico, mensagem_lower)) and not bool(match_categoria)

    tem_listar_todos_situacao = (
        any(tc.get("function", {}).get("name") == "listar_todos_processos_por_situacao" for tc in (tool_calls or []))
        if tool_calls
        else False
    )

    match_processo_especifico = re.search(r"\b([a-z]{3})\.\d{4}/\d{2}\b", mensagem_lower)

    if match_categoria and not match_processo_especifico and not periodo_temporal_detectado and not ja_processou_periodo_temporal and not ja_processou_pergunta_chegada_generica:
        if categoria_detectada_direta:
            categoria_detectada = categoria_detectada_direta.upper()
        else:
            categoria_detectada = (match_categoria.group(1) or match_categoria.group(2) or match_categoria.group(3) or "").strip().upper()

        if categoria_detectada and len(categoria_detectada) == 3:
            if situacao_detectada:
                _logger.warning(
                    f'🔍 Categoria {categoria_detectada} com situação "{situacao_detectada}" detectada na mensagem mas IA não chamou função. '
                    "Forçando chamada de listar_processos_por_situacao"
                )
                try:
                    resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                        "listar_processos_por_situacao",
                        {"categoria": categoria_detectada, "situacao": situacao_detectada, "limite": 200},
                        mensagem_original=mensagem,
                    )
                    _logger.info(
                        f'🔍 Resultado da função forçada: sucesso={resultado_forcado.get("sucesso")}, '
                        f'tem_resposta={bool(resultado_forcado.get("resposta"))}, tem_mensagem={bool(resultado_forcado.get("mensagem"))}'
                    )
                    if resultado_forcado.get("resposta"):
                        resposta_ia = resultado_forcado.get("resposta")
                        _logger.info(
                            f'✅ Usando resposta da função forçada para categoria {categoria_detectada} com situação "{situacao_detectada}" '
                            f"(tamanho: {len(resposta_ia)})"
                        )
                    elif resultado_forcado.get("mensagem"):
                        resposta_ia = resultado_forcado.get("mensagem")
                        _logger.info(
                            f'✅ Usando mensagem da função forçada para categoria {categoria_detectada} com situação "{situacao_detectada}"'
                        )
                    else:
                        _logger.warning(
                            f'⚠️ Função forçada não retornou resposta nem mensagem para categoria {categoria_detectada} com situação "{situacao_detectada}". '
                            "Usando resposta da IA como fallback."
                        )
                        resposta_ia = resposta_ia_raw
                except Exception as e:
                    _logger.error(
                        f'❌ Erro ao forçar chamada da função para categoria {categoria_detectada} com situação "{situacao_detectada}": {e}',
                        exc_info=True,
                    )
                    resposta_ia = resposta_ia_raw
            elif tem_pendencia:
                _logger.warning(
                    f"🔍 Categoria {categoria_detectada} com pendências detectada na mensagem mas IA não chamou função. "
                    "Forçando chamada de listar_processos_com_pendencias"
                )
                try:
                    resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                        "listar_processos_com_pendencias",
                        {"categoria": categoria_detectada, "limite": 200},
                        mensagem_original=mensagem,
                    )
                    _logger.info(
                        f'🔍 Resultado da função forçada: sucesso={resultado_forcado.get("sucesso")}, '
                        f'tem_resposta={bool(resultado_forcado.get("resposta"))}, tem_mensagem={bool(resultado_forcado.get("mensagem"))}'
                    )
                    if resultado_forcado.get("resposta"):
                        resposta_ia = resultado_forcado.get("resposta")
                        _logger.info(f"✅ Usando resposta da função forçada para categoria {categoria_detectada} com pendências (tamanho: {len(resposta_ia)})")
                    elif resultado_forcado.get("mensagem"):
                        resposta_ia = resultado_forcado.get("mensagem")
                        _logger.info(f"✅ Usando mensagem da função forçada para categoria {categoria_detectada} com pendências")
                    else:
                        _logger.warning(
                            f"⚠️ Função forçada não retornou resposta nem mensagem para categoria {categoria_detectada} com pendências. "
                            "Usando resposta da IA como fallback."
                        )
                        resposta_ia = resposta_ia_raw
                except Exception as e:
                    _logger.error(
                        f"❌ Erro ao forçar chamada da função para categoria {categoria_detectada} com pendências: {e}",
                        exc_info=True,
                    )
                    resposta_ia = resposta_ia_raw
            else:
                _logger.warning(
                    f"🔍 Categoria {categoria_detectada} detectada na mensagem mas IA não chamou função. Forçando chamada de listar_processos_por_categoria"
                )
                try:
                    resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                        "listar_processos_por_categoria",
                        {"categoria": categoria_detectada, "limite": 200},
                        mensagem_original=mensagem,
                    )
                    _logger.info(
                        f'🔍 Resultado da função forçada: sucesso={resultado_forcado.get("sucesso")}, '
                        f'tem_resposta={bool(resultado_forcado.get("resposta"))}, tem_mensagem={bool(resultado_forcado.get("mensagem"))}'
                    )
                    if resultado_forcado.get("resposta"):
                        resposta_ia = resultado_forcado.get("resposta")
                        _logger.info(f"✅ Usando resposta da função forçada para categoria {categoria_detectada} (tamanho: {len(resposta_ia)})")
                    elif resultado_forcado.get("mensagem"):
                        resposta_ia = resultado_forcado.get("mensagem")
                        _logger.info(f"✅ Usando mensagem da função forçada para categoria {categoria_detectada}")
                    else:
                        _logger.warning(
                            f"⚠️ Função forçada não retornou resposta nem mensagem para categoria {categoria_detectada}. "
                            "Usando resposta da IA como fallback."
                        )
                        resposta_ia = resposta_ia_raw
                except Exception as e:
                    _logger.error(f"❌ Erro ao forçar chamada da função para categoria {categoria_detectada}: {e}", exc_info=True)
                    resposta_ia = resposta_ia_raw
        else:
            if not ja_processou_categoria_situacao:
                resposta_ia = resposta_ia_raw
            else:
                _logger.info(f"✅ Preservando resposta de categoria+situação (tamanho: {len(resposta_ia) if resposta_ia else 0})")

    if match_generico and not tem_listar_todos_situacao and not ja_processou_categoria_situacao:
        _logger.warning("🔍 Pergunta genérica detectada (sem categoria) mas IA não chamou listar_todos_processos_por_situacao. Forçando chamada...")
        try:
            args_todos: Dict[str, Any] = {"limite": 500}
            if situacao_detectada:
                args_todos["situacao"] = situacao_detectada
            if tem_pendencia:
                args_todos["filtro_pendencias"] = True
            if tem_bloqueio:
                args_todos["filtro_bloqueio"] = True

            resultado_forcado = chat_service._executar_funcao_tool(  # noqa: SLF001
                "listar_todos_processos_por_situacao",
                args_todos,
                mensagem_original=mensagem,
            )
            _logger.info(
                f'🔍 Resultado da função forçada (genérica): sucesso={resultado_forcado.get("sucesso")}, '
                f'tem_resposta={bool(resultado_forcado.get("resposta"))}, tem_mensagem={bool(resultado_forcado.get("mensagem"))}'
            )
            if resultado_forcado.get("resposta"):
                resposta_ia = resultado_forcado.get("resposta")
                _logger.info(f"✅ Usando resposta da função forçada (genérica) (tamanho: {len(resposta_ia)})")
            elif resultado_forcado.get("mensagem"):
                resposta_ia = resultado_forcado.get("mensagem")
                _logger.info("✅ Usando mensagem da função forçada (genérica)")
            else:
                _logger.warning("⚠️ Função forçada (genérica) não retornou resposta nem mensagem. Usando resposta da IA como fallback.")
                resposta_ia = resposta_ia_raw
        except Exception as e:
            _logger.error(f"❌ Erro ao forçar chamada da função genérica: {e}", exc_info=True)
            resposta_ia = resposta_ia_raw

    return {
        "resposta_ia": resposta_ia,
        "ja_processou_categoria_situacao": ja_processou_categoria_situacao,
        "resposta_ia_categoria_situacao": resposta_ia_categoria_situacao,
    }

