import re
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from services.chat_service import ChatService

from services.context_service import salvar_contexto_sessao, buscar_contexto_sessao

logger = logging.getLogger(__name__)


class NcmPrecheckService:
    """Serviço especializado em prechecks relacionados a NCM (Nomenclatura Comum do Mercosul).
    
    Responsável por:
    - Consulta de NCM no TECwin
    - Detecção de perguntas sobre NCM/classificação fiscal
    """

    def __init__(self, chat_service: "ChatService") -> None:
        self.chat_service = chat_service

    def precheck_tecwin_ncm(
        self,
        mensagem: str,
        mensagem_lower: str,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Precheck para consulta de NCM no TECwin.

        Detecta padrões como:
        - "tecwin ncm 07032090"
        - "tecwin 07032090" (sem "ncm")
        - "consulta tecwin ncm 07032090"
        """
        padrao_tecwin_ncm = r"\btecwin\s+ncm\s+(\d{4,8})"
        match = re.search(padrao_tecwin_ncm, mensagem_lower)

        if not match:
            padrao_tecwin_direto = r"\btecwin\s+(\d{4,8})\b"
            match = re.search(padrao_tecwin_direto, mensagem_lower)

        if not match and ("tecwin" in mensagem_lower and "ncm" in mensagem_lower):
            matches_ncm = re.findall(r"(\d{4,8})", mensagem)
            if matches_ncm:
                for ncm_candidato in matches_ncm:
                    if 4 <= len(ncm_candidato) <= 8:
                        match = type("Match", (), {"group": lambda x: ncm_candidato})()
                        break

        if not match and "tecwin" in mensagem_lower:
            match = re.search(r"\btecwin\s+(\d{4,8})\b", mensagem_lower)
            if not match:
                matches_ncm = re.findall(r"(\d{4,8})", mensagem)
                if matches_ncm:
                    for ncm_candidato in matches_ncm:
                        if 4 <= len(ncm_candidato) <= 8:
                            match = type("Match", (), {"group": lambda x: ncm_candidato})()
                            break

        if not match:
            return None

        codigo_ncm = match.group(1) if hasattr(match, "group") else match
        codigo_ncm = str(codigo_ncm or "").replace(".", "").strip()

        logger.info(
            f"[NCM_PRECHECK] Consulta TECwin NCM detectada. NCM: {codigo_ncm} | Mensagem: '{mensagem}'"
        )

        try:
            from services.tecwin_service import TecwinService

            dados = TecwinService(headless=True).consultar_ncm(codigo_ncm)
            if not isinstance(dados, dict):
                raise RuntimeError("Resposta inválida do TecwinService (não dict).")

            if not dados.get("sucesso", False):
                err = dados.get("erro") or "TECWIN_ERRO"
                msg = dados.get("mensagem") or "Falha ao consultar TECwin."
                if err == "TECWIN_CREDENTIALS_MISSING":
                    msg += " Configure `TECWIN_EMAIL` e `TECWIN_SENHA` no ambiente."
                if err == "TECWIN_DISABLED":
                    msg += " (TECWIN_ENABLED=false)"
                return {
                    "sucesso": False,
                    "resposta": f"❌ **Erro ao consultar NCM {codigo_ncm} no TECwin:** {msg}",
                    "_processado_precheck": True,
                }

            html = str(dados.get("html") or "")
            codigo_ncm_sem_ponto = codigo_ncm.replace(".", "")

            def extrair_tr_atributos(html_str: str) -> Dict[str, str]:
                padrao_tr = rf'<tr[^>]*ncm=["\']?{re.escape(codigo_ncm_sem_ponto)}["\']?[^>]*>'
                m = re.search(padrao_tr, html_str, re.IGNORECASE)
                if not m:
                    return {}
                tr_tag = m.group(0)

                def _get(nome: str) -> str:
                    mm = re.search(rf'{nome}=["\']([^"\']*)["\']', tr_tag, re.IGNORECASE)
                    return mm.group(1) if mm else ""

                return {
                    "ii": _get("ii"),
                    "ipi": _get("ipi"),
                    "pis": _get("pis"),
                    "cofins": _get("cofins"),
                    "icms": _get("icms"),
                    "unidmedida": _get("unidmedida"),
                    "descricao": _get("descricao") or _get("mercadoria"),
                }

            attrs = extrair_tr_atributos(html)
            resposta = f"📋 **NCM {codigo_ncm} - TECwin**\n\n"

            if any(attrs.get(k) for k in ("ii", "ipi", "pis", "cofins", "icms")):
                resposta += "**Alíquotas:**\n"
                if attrs.get("ii"):
                    resposta += f"• **II (Imposto de Importação):** {attrs['ii']}%\n"
                if attrs.get("ipi"):
                    resposta += f"• **IPI (Imposto sobre Produtos Industrializados):** {attrs['ipi']}%\n"
                if attrs.get("pis"):
                    resposta += f"• **PIS/PASEP:** {attrs['pis']}%\n"
                if attrs.get("cofins"):
                    resposta += f"• **COFINS:** {attrs['cofins']}%\n"
                if attrs.get("icms"):
                    resposta += f"• **ICMS:** {attrs['icms']}\n"
                resposta += "\n"

                if attrs.get("unidmedida"):
                    resposta += f"**Unidade de Medida:** {attrs['unidmedida']}\n\n"
            else:
                # Se não encontrou atributos (HTML mudou), ainda devolvemos o link para auditoria.
                resposta += "_Não consegui extrair as alíquotas automaticamente (o HTML do TECwin pode ter mudado)._ \n\n"

            if dados.get("url"):
                resposta += f"\n🔗 **Fonte:** [TECwin]({dados['url']})"

            # Salvar contexto (para email/cálculo) — reaproveita NESH/confiança do contexto anterior
            try:
                session_id_para_salvar = (
                    session_id
                    or getattr(self.chat_service, "session_id_atual", None)
                    if hasattr(self, "chat_service")
                    else None
                )
                if session_id_para_salvar:
                    aliquotas: Dict[str, Any] = {}
                    if attrs.get("ii"):
                        try:
                            aliquotas["ii"] = float(attrs["ii"].replace("%", "").replace(",", "."))
                        except Exception:
                            pass
                    if attrs.get("ipi"):
                        try:
                            aliquotas["ipi"] = float(attrs["ipi"].replace("%", "").replace(",", "."))
                        except Exception:
                            pass
                    if attrs.get("pis"):
                        try:
                            aliquotas["pis"] = float(attrs["pis"].replace("%", "").replace(",", "."))
                        except Exception:
                            pass
                    if attrs.get("cofins"):
                        try:
                            aliquotas["cofins"] = float(attrs["cofins"].replace("%", "").replace(",", "."))
                        except Exception:
                            pass
                    if attrs.get("icms"):
                        aliquotas["icms"] = attrs["icms"]

                    contexto_anterior = None
                    try:
                        contextos = buscar_contexto_sessao(
                            session_id_para_salvar, tipo_contexto="ultima_classificacao_ncm"
                        )
                        if contextos:
                            contexto_anterior = contextos[0].get("dados", {})
                    except Exception:
                        contexto_anterior = None

                    nota_nesh_anterior = (
                        (contexto_anterior or {}).get("nota_nesh", "") if isinstance(contexto_anterior, dict) else ""
                    )
                    nota_nesh_string = ""
                    if nota_nesh_anterior:
                        if isinstance(nota_nesh_anterior, dict):
                            titulo = nota_nesh_anterior.get("position_title", "")
                            texto = nota_nesh_anterior.get("text", "")
                            nota_nesh_string = f"{titulo}\n\n{texto}" if titulo and texto else (titulo or texto or "")
                        else:
                            nota_nesh_string = str(nota_nesh_anterior)

                    contexto_ncm = {
                        "ncm": codigo_ncm,
                        "descricao": (attrs.get("descricao") or (contexto_anterior or {}).get("descricao") or ""),
                        "confianca": float((contexto_anterior or {}).get("confianca", 0.0) or 0.0)
                        if isinstance(contexto_anterior, dict)
                        else 0.0,
                        "nota_nesh": nota_nesh_string,
                        "aliquotas": aliquotas,
                        "unidade_medida": attrs.get("unidmedida")
                        or ((contexto_anterior or {}).get("unidade_medida", "") if isinstance(contexto_anterior, dict) else ""),
                        "fonte": "TECwin",
                        "explicacao": (contexto_anterior or {}).get("explicacao", "")
                        if isinstance(contexto_anterior, dict)
                        else "",
                    }

                    salvar_contexto_sessao(
                        session_id=session_id_para_salvar,
                        tipo_contexto="ultima_classificacao_ncm",
                        chave="ncm",
                        valor=codigo_ncm,
                        dados_adicionais=contexto_ncm,
                    )

                    if aliquotas:
                        salvar_contexto_sessao(
                            session_id=session_id_para_salvar,
                            tipo_contexto="ncm_aliquotas",
                            chave="ncm",
                            valor=codigo_ncm,
                            dados_adicionais={
                                "ncm": codigo_ncm,
                                "aliquotas": aliquotas,
                                "descricao": attrs.get("descricao") or "",
                            },
                        )

                    logger.info(f"✅ Contexto de NCM/alíquotas salvo: {codigo_ncm}")
            except Exception as e:
                logger.debug(f"Erro ao salvar contexto NCM após TECwin: {e}")

            return {
                "sucesso": True,
                "resposta": resposta,
                "tool_calls": [
                    {"name": "consultar_tecwin_ncm", "arguments": {"ncm": codigo_ncm}},
                ],
                "_processado_precheck": True,
            }

        except Exception as e:
            logger.error(f"[NCM_PRECHECK] Erro ao consultar TECwin NCM {codigo_ncm}: {e}", exc_info=True)
            return {
                "sucesso": False,
                "resposta": f"❌ **Erro ao consultar NCM {codigo_ncm} no TECwin:** {str(e)}",
                "_processado_precheck": True,
            }

    def eh_pergunta_ncm(self, mensagem_lower: str) -> bool:
        """Detecta perguntas sobre NCM/classificação fiscal."""
        padroes_ncm = [
            r"\bncm\b",
            r"qual\s+a\s+ncm\b",
            r"qual\s+é\s+o?\s*ncm\b",
            r"classificar\s+produto\b",
            r"classifica[cç][aã]o\s+fiscal\b",
        ]
        return any(re.search(p, mensagem_lower) for p in padroes_ncm)
    
    def precheck_pergunta_ncm(
        self,
        mensagem: str,
        mensagem_lower: str,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        ✅ BUSCA HÍBRIDA DE NCM (Cache → DuckDuckGo → Modelo)
        
        Intercepta perguntas de NCM e faz busca híbrida ANTES de chamar o modelo:
        1. Cache local (buscar_ncms_por_descricao)
        2. DuckDuckGo (se cache não retornar resultados suficientes)
        3. Modelo (como último recurso, via sugerir_ncm_com_ia)
        
        Detecta padrões como:
        - "qual a ncm de oculos?"
        - "ncm de alho"
        - "classificar produto X"
        """
        # Verificar se é pergunta de NCM
        if not self.eh_pergunta_ncm(mensagem_lower):
            return None
        
        # Extrair descrição do produto da mensagem
        # Padrões: "qual a ncm de X", "ncm de X", "qual ncm para X", "classificar X"
        descricao_produto = None
        
        # Padrão 1: "qual a ncm de X" ou "qual é a ncm de X"
        match = re.search(r'qual\s+(?:é\s+)?(?:a\s+)?ncm\s+(?:de|para|do|da)\s+(.+?)(?:\?|$)', mensagem_lower)
        if match:
            descricao_produto = match.group(1).strip()
        
        # Padrão 2: "ncm de X" ou "ncm para X"
        if not descricao_produto:
            match = re.search(r'ncm\s+(?:de|para|do|da)\s+(.+?)(?:\?|$)', mensagem_lower)
            if match:
                descricao_produto = match.group(1).strip()
        
        # Padrão 3: "qual ncm X" ou "ncm X" (mais genérico)
        if not descricao_produto:
            match = re.search(r'(?:qual\s+)?ncm\s+(.+?)(?:\?|$)', mensagem_lower)
            if match:
                descricao_produto = match.group(1).strip()
                # ✅ CORREÇÃO: Remover palavras comuns do início ("de", "para", "do", "da")
                palavras_comuns = ['de', 'para', 'do', 'da', 'dos', 'das']
                palavras_descricao = descricao_produto.split()
                if palavras_descricao and palavras_descricao[0].lower() in palavras_comuns:
                    descricao_produto = ' '.join(palavras_descricao[1:]).strip()
        
        # Padrão 4: "classificar X" ou "classificação fiscal de X"
        if not descricao_produto:
            match = re.search(r'classificar\s+(.+?)(?:\?|$)', mensagem_lower)
            if match:
                descricao_produto = match.group(1).strip()
        
        if not descricao_produto or len(descricao_produto) < 2:
            # Não conseguiu extrair descrição, deixar IA processar
            logger.debug(f"[NCM_PRECHECK] Pergunta de NCM detectada mas não conseguiu extrair descrição: '{mensagem}'")
            return None
        
        logger.info(f"[NCM_PRECHECK] ✅ Busca híbrida de NCM iniciada para: '{descricao_produto}'")
        
        try:
            from services.ncm_service import NCMService
            ncm_service = NCMService(self.chat_service)

            def _append_nesh_meta_to_response(resposta: str, nota_nesh: Optional[Dict[str, Any]], *, modo: str) -> str:
                """
                Adiciona rodapé estilo REPORT_META com fonte da NESH.
                Ex.: [NESH_META:{"fonte":"HF","modo":"descricao"}]

                Controlado por ENV: NESH_SHOW_SOURCE_IN_RESPONSE=true
                """
                try:
                    import json
                    import os

                    show = str(os.getenv("NESH_SHOW_SOURCE_IN_RESPONSE", "false")).strip().lower() in (
                        "1",
                        "true",
                        "yes",
                        "y",
                        "on",
                    )
                    if not show:
                        return resposta
                    # Se a resposta já tem NESH_META (ex.: o NCMService anexou), não duplicar.
                    if isinstance(resposta, str) and "[NESH_META:" in resposta:
                        return resposta
                    if not isinstance(resposta, str) or not resposta.strip():
                        return resposta
                    fonte = None
                    if isinstance(nota_nesh, dict):
                        fonte = nota_nesh.get("_nesh_source") or nota_nesh.get("nesh_source")
                    meta = {"fonte": str(fonte or "desconhecida"), "modo": str(modo or "desconhecido")}
                    return resposta + f"[NESH_META:{json.dumps(meta, ensure_ascii=False)}]"
                except Exception:
                    return resposta
            
            # ✅ PASSO 1: Buscar no cache local primeiro
            resultado_cache = ncm_service.buscar_ncms_por_descricao(
                termo=descricao_produto,
                limite=10,
                incluir_relacionados=True,
                mensagem_original=mensagem
            )
            
            # Se encontrou resultados no cache, retornar diretamente
            if resultado_cache.get('sucesso') and resultado_cache.get('total', 0) > 0:
                logger.info(f"[NCM_PRECHECK] ✅ Cache local retornou {resultado_cache.get('total')} resultados")
                return {
                    'sucesso': True,
                    'resposta': resultado_cache.get('resposta', ''),
                    'tool_calls': [{
                        'name': 'buscar_ncms_por_descricao',
                        'arguments': {
                            'termo': descricao_produto,
                            'limite': 10
                        }
                    }],
                    '_processado_precheck': True,
                }
            
            # ✅ PASSO 2: Busca híbrida completa (DuckDuckGo → Top 5 → Modelo → NESH)
            logger.info(f"[NCM_PRECHECK] Cache local não retornou resultados suficientes, usando busca híbrida completa (DuckDuckGo → Top 5 → Modelo → NESH)")
            
            # ✅ FLUXO HÍBRIDO ORIGINAL RESTAURADO:
            # 1. DuckDuckGo para produtos modernos (ex: iPhone → telefone celular)
            # 2. Buscar top 5 NCMs do cache baseado na categoria identificada
            # 3. Modelo ajuda a classificar entre os top 5
            # 4. Match na NESH para validação final
            
            # Usar sugerir_ncm_com_ia que já tem toda a lógica híbrida integrada:
            # - DuckDuckGo (via _buscar_web_para_produto)
            # - Top 5 NCMs do cache (via buscar_ncms_por_descricao)
            # - Modelo para classificar (via ai_service.sugerir_ncm_por_descricao)
            # - NESH para validação (via buscar_notas_explicativas_nesh_por_descricao)
            resultado_ia = ncm_service.sugerir_ncm_com_ia(
                descricao=descricao_produto,
                contexto=None,
                usar_cache=True,  # ✅ CRÍTICO: Usar cache para buscar top 5
                validar_sugestao=True,  # ✅ CRÍTICO: Validar contra cache oficial
                mensagem_original=mensagem
            )
            
            if resultado_ia.get('sucesso'):
                logger.info(f"[NCM_PRECHECK] ✅ Busca híbrida concluída com sucesso (DuckDuckGo + Top 5 + Modelo + NESH)")
                
                # ✅ GARANTIR: A resposta já inclui NESH se foi encontrada
                # O método sugerir_ncm_com_ia já busca NESH e formata na resposta
                resposta_final = resultado_ia.get('resposta', '')
                try:
                    # Se o fluxo híbrido já trouxe nota_nesh estruturada, usar ela para marcar fonte
                    nota_nesh_resultado = resultado_ia.get("nota_nesh") if isinstance(resultado_ia, dict) else None
                    resposta_final = _append_nesh_meta_to_response(
                        resposta_final,
                        nota_nesh_resultado if isinstance(nota_nesh_resultado, dict) else None,
                        modo="precheck_hibrido",
                    )
                except Exception:
                    pass

                # ✅ CRÍTICO: Salvar contexto de NCM para uso em emails
                # Isso permite que o usuário consulte TECwin depois e depois monte o email com tudo junto
                try:
                    from services.context_service import salvar_contexto_sessao
                    session_id_para_salvar = session_id or getattr(self.chat_service, 'session_id_atual', None) if hasattr(self, 'chat_service') else None
                    
                    if session_id_para_salvar:
                        # Extrair informações do resultado da busca híbrida
                        ncm_sugerido = resultado_ia.get('ncm_sugerido', '')
                        confianca = resultado_ia.get('confianca', 0.0)
                        
                        # ✅ CRÍTICO: Converter nota_nesh de dict para string se necessário
                        nota_nesh_resultado = resultado_ia.get('nota_nesh')
                        nota_nesh_string = ''
                        if nota_nesh_resultado:
                            if isinstance(nota_nesh_resultado, dict):
                                # Se for dict, extrair texto completo
                                titulo = nota_nesh_resultado.get('position_title', '')
                                texto = nota_nesh_resultado.get('text', '')
                                if titulo:
                                    nota_nesh_string = f"{titulo}\n\n{texto}" if texto else titulo
                                else:
                                    nota_nesh_string = texto if texto else ''
                            else:
                                nota_nesh_string = str(nota_nesh_resultado)
                        
                        # Extrair explicação
                        explicacao = resultado_ia.get('explicacao', '')
                        
                        # Montar contexto completo
                        contexto_ncm = {
                            'ncm': ncm_sugerido,
                            'descricao': descricao_produto,
                            'confianca': confianca,
                            'nota_nesh': nota_nesh_string,  # ✅ String, não dict
                            'explicacao': explicacao,
                            'fonte': 'Busca Híbrida (Cache + DuckDuckGo + Modelo + NESH)',
                            'ncms_alternativos': resultado_ia.get('ncms_alternativos', [])
                        }
                        
                        salvar_contexto_sessao(
                            session_id=session_id_para_salvar,
                            tipo_contexto='ultima_classificacao_ncm',
                            chave='ncm',
                            valor=ncm_sugerido,
                            dados_adicionais=contexto_ncm
                        )
                        logger.info(f"[NCM_PRECHECK] ✅ Contexto de NCM salvo: {ncm_sugerido} (com NESH e explicação)")
                except Exception as e:
                    logger.warning(f"[NCM_PRECHECK] ⚠️ Erro ao salvar contexto de NCM: {e}")
                
                # ✅ VERIFICAÇÃO: Se a resposta não menciona NESH, adicionar nota
                if 'NESH' not in resposta_final and 'nesh' not in resposta_final.lower():
                    logger.warning(f"[NCM_PRECHECK] ⚠️ NESH não encontrada ou não exibida na resposta para '{descricao_produto}'")
                    # Tentar buscar NESH manualmente para garantir
                    try:
                        from db_manager import buscar_nota_explicativa_nesh_por_ncm, buscar_notas_explicativas_nesh_por_descricao

                        # ✅ Prioridade: NESH pelo NCM sugerido (validação correta)
                        ncm_sugerido = resultado_ia.get('ncm_sugerido', '')
                        nota_nesh = None
                        if ncm_sugerido:
                            nota_nesh = buscar_nota_explicativa_nesh_por_ncm(ncm_sugerido)

                        # Fallback: se não tiver NESH por NCM, tentar por descrição (auxiliar)
                        if not nota_nesh:
                            notas_nesh = buscar_notas_explicativas_nesh_por_descricao(descricao_produto, limite=1)
                            if notas_nesh:
                                nota_nesh = notas_nesh[0] if isinstance(notas_nesh, list) else notas_nesh

                        if nota_nesh:
                            posicao = nota_nesh.get('position_code', '')
                            titulo = nota_nesh.get('position_title', '')
                            texto_nesh = nota_nesh.get('text', '')
                            
                            if texto_nesh:
                                resposta_final += f"\n\n📚 **Nota Explicativa NESH (Posição {posicao}):**\n"
                                if titulo:
                                    resposta_final += f"   {titulo}\n\n"
                                texto_resumido = texto_nesh[:1000] + '...' if len(texto_nesh) > 1000 else texto_nesh
                                resposta_final += f"   {texto_resumido}\n"
                                # ✅ Rodapé de auditoria (fonte da NESH) também no fallback manual
                                resposta_final = _append_nesh_meta_to_response(
                                    resposta_final,
                                    nota_nesh if isinstance(nota_nesh, dict) else None,
                                    modo="precheck_manual",
                                )
                                logger.info(f"[NCM_PRECHECK] ✅ NESH adicionada manualmente à resposta")
                    except Exception as e:
                        logger.warning(f"[NCM_PRECHECK] ⚠️ Erro ao buscar NESH manualmente: {e}")
                
                return {
                    'sucesso': True,
                    'resposta': resposta_final,
                    'tool_calls': [{
                        'name': 'sugerir_ncm_com_ia',
                        'arguments': {
                            'descricao': descricao_produto
                        }
                    }],
                    '_processado_precheck': True,
                }
            else:
                # Se falhou, deixar IA processar normalmente
                logger.warning(f"[NCM_PRECHECK] ⚠️ Busca híbrida falhou, deixando IA processar: {resultado_ia.get('erro')}")
                return None
                
        except Exception as e:
            logger.error(f"[NCM_PRECHECK] ❌ Erro na busca híbrida de NCM: {e}", exc_info=True)
            # Em caso de erro, deixar IA processar normalmente
            return None





