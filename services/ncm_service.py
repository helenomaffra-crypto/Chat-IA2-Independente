"""
NCMService - Serviço para operações relacionadas a NCM (Nomenclatura Comum do Mercosul)

Este serviço centraliza todas as operações de busca, sugestão, detalhamento e download de NCMs.
Migrado do chat_service.py em 15/12/2025 para reduzir complexidade.
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ✅ NOVO: Importar DuckDuckGo para busca web (opcional)
try:
    from duckduckgo_search import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False
    logger.warning("⚠️ duckduckgo-search não disponível. Busca web desabilitada.")


class NCMService:
    """Serviço para operações relacionadas a NCM"""
    
    def __init__(self, chat_service=None):
        """
        Inicializa o NCMService
        
        Args:
            chat_service: Instância opcional do ChatService (para métodos auxiliares se necessário)
        """
        self.chat_service = chat_service
        # ✅ NOVO: Cache simples em memória para buscas web (evitar múltiplas buscas para mesmo produto)
        self._cache_web_search = {}  # {descricao_normalizada: resultado_web}
        self._cache_web_search_max_size = 100  # Limitar tamanho do cache
    
    def buscar_ncms_por_descricao(
        self,
        termo: str,
        limite: int = 50,
        incluir_relacionados: bool = True,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca NCMs por descrição de produto
        
        Args:
            termo: Termo de busca
            limite: Limite de resultados
            incluir_relacionados: Se deve incluir NCMs relacionados
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict com sucesso, resposta, total e termo
        """
        if not termo or len(termo) < 2:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_INVALIDO',
                'mensagem': 'Termo de busca deve ter pelo menos 2 caracteres'
            }
        
        try:
            from db_manager import buscar_ncms_por_descricao, get_classif_ncm_completo
            
            logger.info(f'🔍 buscar_ncms_por_descricao: Buscando NCMs com termo "{termo}" (limite={limite}, incluir_relacionados={incluir_relacionados})')
            
            # Buscar NCMs
            resultados = buscar_ncms_por_descricao(termo, limite, incluir_relacionados)
            
            logger.info(f'🔍 buscar_ncms_por_descricao: Encontrados {len(resultados)} NCMs')
            
            if not resultados:
                resposta = f"⚠️ **Nenhum NCM encontrado com o termo '{termo}'.**\n\n"
                resposta += f"💡 **Dica:** Tente usar termos mais genéricos ou verifique a ortografia."
            else:
                # Se for um pedido "qual a NCM de X", entregar recomendação + fundamentação (NESH),
                # sem exigir que o usuário escolha 1/2.
                msg_lower = (mensagem_original or "").strip().lower()
                eh_pergunta_direta = False
                try:
                    eh_pergunta_direta = bool(
                        msg_lower
                        and (
                            "qual a ncm" in msg_lower
                            or "qual é a ncm" in msg_lower
                            or re.search(r"\bncm\s+(de|para|do|da)\b", msg_lower or "")
                            or msg_lower.startswith("ncm ")
                            or msg_lower.startswith("classifique ")
                            or msg_lower.startswith("classificar ")
                        )
                    )
                except Exception:
                    eh_pergunta_direta = False

                recomendacao_bloco = ""
                if eh_pergunta_direta:
                    try:
                        from db_manager import buscar_nota_explicativa_nesh_por_ncm, buscar_notas_explicativas_nesh_por_descricao

                        desc_l = (termo or "").strip().lower()
                        semeadura_kw = ("semeadura", "sementeira", "plantio", "plantar", "semente", "muda")
                        consumo_kw = ("fresco", "in natura", "supermercado", "consumo", "culin", "cozinha", "aliment", "refriger")
                        desid_kw = ("desidrat", "seco", "sec", "em pó", "po ", "pó", "granulad", "floco", "em pó")

                        # Coletar subitens 8 dígitos por grupo6
                        opcs8 = []
                        for r in resultados:
                            n = (r.get("ncm") or "").strip()
                            d = (r.get("descricao") or "").strip()
                            if len(n) == 8 and n.isdigit():
                                opcs8.append({"ncm": n, "descricao": d})

                        grupo6_map: Dict[str, List[Dict[str, str]]] = {}
                        for o in opcs8:
                            g6 = o["ncm"][:6]
                            grupo6_map.setdefault(g6, []).append(o)

                        # ✅ Dica da NESH por descrição: escolher o capítulo/posição mais provável
                        # Ex.: "ventilador" → NESH 84.14 → priorizar grupo 8414xx
                        nesh_hint_4 = None
                        try:
                            notas_hint = buscar_notas_explicativas_nesh_por_descricao(termo, limite=1)
                            if notas_hint and isinstance(notas_hint, list) and isinstance(notas_hint[0], dict):
                                code = notas_hint[0].get("position_code") or notas_hint[0].get("subposition_code") or ""
                                clean = str(code).strip().replace(".", "").replace("-", "").replace(" ", "")
                                if clean and len(clean) >= 4 and clean[:4].isdigit():
                                    nesh_hint_4 = clean[:4]
                        except Exception:
                            nesh_hint_4 = None

                        # Selecionar grupo 6: para alho, normalmente 070320 (fresco/refrigerado) vs 071290 (seco/desidratado)
                        grupo6_escolhido = None
                        if any(k in desc_l for k in desid_kw):
                            # preferir grupo com 071290 e "alho" na descrição
                            cand = [g for g, items in grupo6_map.items() if g.startswith("071290")]
                            grupo6_escolhido = cand[0] if cand else None
                        else:
                            cand = [g for g, items in grupo6_map.items() if g.startswith("070320")]
                            grupo6_escolhido = cand[0] if cand else None

                        # ✅ Seleção genérica do grupo 6 (sem regra por produto):
                        # 1) Se NESH der hint (4 dígitos), escolher dentro desse capítulo.
                        # 2) Desempatar por "match de palavras" entre o termo do usuário e descrições dos itens.
                        if grupo6_map:
                            # tokens do usuário (simples, sem stemming pesado)
                            tokens = [t for t in re.split(r"[^a-z0-9áéíóúãõâêîôûç]+", desc_l) if len(t) >= 3]

                            def _score_items(items: List[Dict[str, str]]) -> int:
                                blob = " ".join([(i.get("descricao") or "").lower() for i in items])
                                score = 0
                                for tok in tokens[:6]:
                                    if tok in blob:
                                        score += 3
                                return score

                            candidatos = list(grupo6_map.keys())
                            if nesh_hint_4:
                                cand_hint = [g for g in candidatos if g.startswith(nesh_hint_4)]
                                if cand_hint:
                                    candidatos = cand_hint

                            grupo6_escolhido = max(
                                sorted(candidatos),
                                key=lambda g: _score_items(grupo6_map.get(g) or []),
                            )

                        if not grupo6_escolhido and grupo6_map:
                            grupo6_escolhido = sorted(grupo6_map.keys())[0]

                        ncm_recomendado = None
                        motivo = None
                        if grupo6_escolhido:
                            itens = grupo6_map.get(grupo6_escolhido, [])
                            # subitem: semeadura vs outros
                            semeadura_item = next((i for i in itens if "semeadura" in (i.get("descricao", "").lower())), None)
                            outros_item = next((i for i in itens if (i.get("descricao", "").lower().strip().startswith("outros"))), None)

                            if semeadura_item and outros_item:
                                if any(k in desc_l for k in semeadura_kw):
                                    ncm_recomendado = semeadura_item["ncm"]
                                    motivo = "você mencionou semeadura/plantio"
                                else:
                                    ncm_recomendado = outros_item["ncm"]
                                    if any(k in desc_l for k in consumo_kw) or not any(k in desc_l for k in desid_kw):
                                        motivo = "consumo/supermercado/in natura (sem indicação de semeadura)"
                                    else:
                                        motivo = "por padrão, sem indicação de semeadura"
                            else:
                                # Fallback genérico: primeiro item do grupo escolhido
                                if itens:
                                    ncm_recomendado = itens[0]["ncm"]
                                    motivo = "melhor candidato no grupo encontrado"

                        if ncm_recomendado:
                            ncm_fmt = f"{ncm_recomendado[:2]}.{ncm_recomendado[2:4]}.{ncm_recomendado[4:6]}.{ncm_recomendado[6:]}"
                            recomendacao_bloco += f"🧭 **Recomendação (com base na tabela NCM)**\n\n"
                            recomendacao_bloco += f"✅ **NCM recomendado:** **{ncm_fmt}**\n"
                            if motivo:
                                recomendacao_bloco += f"📌 **Por quê:** {motivo}\n"

                            # NESH (fundamentação) — usar NESH por NCM recomendado
                            nota_nesh = buscar_nota_explicativa_nesh_por_ncm(ncm_recomendado)
                            if nota_nesh and isinstance(nota_nesh, dict):
                                posicao = nota_nesh.get("position_code", "") or ""
                                titulo = nota_nesh.get("position_title", "") or ""
                                texto_nesh = (nota_nesh.get("text") or "").strip()
                                if texto_nesh:
                                    recomendacao_bloco += f"\n📚 **Fundamentação (NESH — Posição {posicao})**\n"
                                    if titulo:
                                        recomendacao_bloco += f"{titulo}\n\n"
                                    texto_res = texto_nesh[:900] + "..." if len(texto_nesh) > 900 else texto_nesh
                                    recomendacao_bloco += f"{texto_res}\n"

                                    # Rodapé de auditoria
                                    try:
                                        import os
                                        show = str(os.getenv("NESH_SHOW_SOURCE_IN_RESPONSE", "false")).strip().lower() in (
                                            "1",
                                            "true",
                                            "yes",
                                            "y",
                                            "on",
                                        )
                                        if show:
                                            meta = {"fonte": nota_nesh.get("_nesh_source") or "desconhecida", "modo": "cache_recomendacao"}
                                            recomendacao_bloco += f"[NESH_META:{json.dumps(meta, ensure_ascii=False)}]"
                                    except Exception:
                                        pass

                            # ✅ Explicação do modelo (como antes), mas sem deixar o modelo "trocar" o NCM:
                            # passar apenas candidatos da lista e forçar que ele escolha o recomendado (e explique).
                            try:
                                from ai_service import AIService

                                ai = AIService()
                                if ai and getattr(ai, "enabled", False):
                                    # Montar lista curta de candidatos (recomendado + até 5 alternativos do mesmo grupo6)
                                    candidatos = []
                                    itens_grupo = (grupo6_map.get(grupo6_escolhido) or []) if grupo6_escolhido else []
                                    # recomendado primeiro
                                    rec_desc = next((i.get("descricao") for i in itens_grupo if i.get("ncm") == ncm_recomendado), "") or ""
                                    candidatos.append({"ncm": ncm_recomendado, "descricao": rec_desc})
                                    for it in itens_grupo:
                                        if it.get("ncm") != ncm_recomendado:
                                            candidatos.append({"ncm": it.get("ncm"), "descricao": it.get("descricao")})
                                        if len(candidatos) >= 6:
                                            break

                                    contexto_modelo = {
                                        "ncms_similares_no_cache": candidatos,
                                        "instrucao_rag": (
                                            f"Você DEVE sugerir o NCM {ncm_recomendado} (já decidido por regra) "
                                            "e apenas explicar o porquê e o que faria mudar de subitem."
                                        ),
                                    }
                                    resp = ai.sugerir_ncm_por_descricao(termo, contexto=contexto_modelo)
                                    explic = (resp or {}).get("explicacao")
                                    if explic and isinstance(explic, str):
                                        recomendacao_bloco += f"\n🧠 **Explicação do modelo (refino)**\n{explic.strip()}\n"
                            except Exception as e:
                                logger.debug(f"⚠️ Falha ao gerar explicação do modelo no cache: {e}")

                            recomendacao_bloco += "\n\n" + ("─" * 50) + "\n\n"
                    except Exception as e:
                        logger.debug(f"⚠️ Falha ao montar recomendação + NESH no cache: {e}")

                resposta = (recomendacao_bloco or "") + f"🔍 **NCMs encontrados para '{termo}'** ({len(resultados)} resultado(s))\n\n"
                
                # ✅ NOVO: Agrupar hierarquicamente (capítulo → posição → subitens)
                
                # ✅ CORREÇÃO: Remover duplicatas primeiro (mesmo NCM pode aparecer múltiplas vezes)
                ncms_unicos = {}
                for ncm_data in resultados:
                    ncm = ncm_data.get('ncm', '')
                    if ncm:
                        # Manter apenas a primeira ocorrência de cada NCM
                        if ncm not in ncms_unicos:
                            ncms_unicos[ncm] = ncm_data
                
                # Estrutura hierárquica: capitulos -> posicoes -> subitens
                hierarquia = {}  # {capitulo: {posicao: [subitens]}}
                ncms_4_digitos = {}  # NCMs de 4 dígitos (capítulos)
                ncms_6_digitos = {}  # NCMs de 6 dígitos (posições)
                ncms_8_digitos = []  # NCMs de 8 dígitos (subitens)
                
                # Processar apenas NCMs únicos
                for ncm_key, ncm_data in ncms_unicos.items():
                    ncm = ncm_data.get('ncm', '') or ncm_key
                    descricao = ncm_data.get('descricao', '')
                    unidade = ncm_data.get('unidade', '')
                    
                    if len(ncm) == 8:
                        # Subitem de 8 dígitos: agrupar por posição (6 dígitos)
                        posicao = ncm[:6]
                        capitulo = ncm[:4]
                        
                        if capitulo not in hierarquia:
                            hierarquia[capitulo] = {}
                        if posicao not in hierarquia[capitulo]:
                            hierarquia[capitulo][posicao] = []
                        
                        # ✅ CORREÇÃO: Verificar se já existe antes de adicionar (evitar duplicatas)
                        ja_existe = any(item.get('ncm') == ncm for item in hierarquia[capitulo][posicao])
                        if not ja_existe:
                            hierarquia[capitulo][posicao].append({
                                'ncm': ncm,
                                'descricao': descricao,
                                'unidade': unidade
                            })
                    elif len(ncm) == 6:
                        # Posição de 6 dígitos: guardar separadamente
                        ncms_6_digitos[ncm] = {
                            'ncm': ncm,
                            'descricao': descricao,
                            'unidade': unidade
                        }
                    elif len(ncm) == 4:
                        # Capítulo de 4 dígitos: guardar separadamente
                        ncms_4_digitos[ncm] = {
                            'ncm': ncm,
                            'descricao': descricao,
                            'unidade': unidade
                        }
                
                # ✅ Mostrar resultados hierarquicamente
                capitulos_processados = set()
                
                # Processar hierarquia (capítulos que têm subitens)
                for capitulo_key in sorted(hierarquia.keys()):
                    capitulos_processados.add(capitulo_key)
                    
                    # Buscar descrição do capítulo
                    info_capitulo = get_classif_ncm_completo(capitulo_key)
                    descricao_capitulo = info_capitulo.get('descricao', '') if info_capitulo else ''
                    formato_capitulo = f"{capitulo_key[:2]}.{capitulo_key[2:]}"
                    
                    # Mostrar capítulo
                    if descricao_capitulo:
                        resposta += f"📚 **Capítulo (4 dígitos): {formato_capitulo}**\n"
                        resposta += f"   {descricao_capitulo}\n\n"
                    else:
                        resposta += f"📚 **Capítulo: {formato_capitulo}**\n\n"
                    
                    # Processar posições dentro do capítulo
                    for posicao_key in sorted(hierarquia[capitulo_key].keys()):
                        # Buscar descrição da posição (pode estar nos resultados ou no banco)
                        descricao_posicao = None
                        formato_posicao = f"{posicao_key[:2]}.{posicao_key[2:4]}.{posicao_key[4:]}"
                        
                        # Se a posição está nos resultados de 6 dígitos, usar sua descrição
                        if posicao_key in ncms_6_digitos:
                            descricao_posicao = ncms_6_digitos[posicao_key].get('descricao', '')
                        else:
                            # Buscar no banco
                            info_posicao = get_classif_ncm_completo(posicao_key)
                            descricao_posicao = info_posicao.get('descricao', '') if info_posicao else ''
                        
                        # Mostrar posição
                        if descricao_posicao:
                            resposta += f"📖 **Posição (6 dígitos): {formato_posicao}**\n"
                            resposta += f"   {descricao_posicao}\n\n"
                        
                        # Mostrar subitens (8 dígitos) da posição
                        subitens = hierarquia[capitulo_key][posicao_key]
                        for subitem in sorted(subitens, key=lambda x: x['ncm']):
                            ncm_sub = subitem['ncm']
                            desc_sub = subitem['descricao']
                            unid_sub = subitem.get('unidade', '')
                            
                            ncm_formatado = f"{ncm_sub[:2]}.{ncm_sub[2:4]}.{ncm_sub[4:6]}.{ncm_sub[6:]}"
                            resposta += f"  - **{ncm_formatado}**: {desc_sub}"
                            if unid_sub:
                                resposta += f" (Unidade: {unid_sub})"
                            resposta += "\n"
                        
                        resposta += "\n"
                
                # Processar capítulos que aparecem sozinhos (sem subitens)
                for capitulo_key in sorted(ncms_4_digitos.keys()):
                    if capitulo_key not in capitulos_processados:
                        info_capitulo = get_classif_ncm_completo(capitulo_key)
                        descricao_capitulo = info_capitulo.get('descricao', '') if info_capitulo else ''
                        formato_capitulo = f"{capitulo_key[:2]}.{capitulo_key[2:]}"
                        
                        if descricao_capitulo:
                            resposta += f"📚 **Capítulo (4 dígitos): {formato_capitulo}**\n"
                            resposta += f"   {descricao_capitulo}\n\n"
                
                # Processar posições que aparecem sozinhas (sem subitens)
                for posicao_key in sorted(ncms_6_digitos.keys()):
                    # Verificar se já foi processada na hierarquia
                    ja_processada = False
                    for cap in hierarquia.values():
                        if posicao_key in cap:
                            ja_processada = True
                            break
                    
                    if not ja_processada:
                        info_posicao = get_classif_ncm_completo(posicao_key)
                        descricao_posicao = info_posicao.get('descricao', '') if info_posicao else ''
                        formato_posicao = f"{posicao_key[:2]}.{posicao_key[2:4]}.{posicao_key[4:]}"
                        
                        if descricao_posicao:
                            resposta += f"📖 **Posição (6 dígitos): {formato_posicao}**\n"
                            resposta += f"   {descricao_posicao}\n\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(resultados),
                'termo': termo
            }
        except Exception as e:
            logger.error(f'Erro ao buscar NCMs por descrição: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar NCMs: {str(e)}'
            }
    
    def _buscar_web_para_produto(self, descricao: str) -> Optional[Dict[str, Any]]:
        """
        Busca informações na web sobre o produto usando DuckDuckGo
        
        ✅ OBJETIVO: Enriquecer classificação para produtos modernos que não aparecem
        literalmente na NESH/NCM (ex: "iPhone" → "telefone celular")
        
        ✅ MELHORIA: Usa cache em memória para evitar múltiplas buscas para o mesmo produto
        
        Args:
            descricao: Descrição do produto (ex: "iPhone 15 Pro")
        
        Returns:
            Dict com informações da web ou None se erro/indisponível
        """
        if not DDG_AVAILABLE:
            return None
        
        # ✅ NOVO: Verificar cache primeiro (normalizar descrição para chave)
        descricao_normalizada = descricao.lower().strip()
        if descricao_normalizada in self._cache_web_search:
            logger.info(f'🌐 Cache hit para busca web: "{descricao}"')
            return self._cache_web_search[descricao_normalizada]
        
        try:
            logger.info(f'🌐 Buscando na web informações sobre: "{descricao}"')
            
            # ✅ MELHORIA: Criar múltiplas queries para melhor cobertura
            queries = [
                f"{descricao} NCM Brasil",
                f"{descricao} classificação fiscal NCM",
                f"{descricao} código NCM importação"
            ]
            
            todos_resultados = []
            with DDGS() as ddgs:
                for query in queries:
                    try:
                        # Buscar resultados (máximo 3 por query = 9 total, limitado a 5)
                        resultados_query = list(ddgs.text(query, max_results=3))
                        todos_resultados.extend(resultados_query)
                        if len(todos_resultados) >= 5:
                            break
                    except Exception as e:
                        logger.warning(f'⚠️ Erro na query "{query}": {e}')
                        continue
            
            resultados = todos_resultados[:5]  # Limitar a 5 resultados
            
            if not resultados:
                logger.warning(f'⚠️ Nenhum resultado encontrado na web para "{descricao}"')
                return None
            
            # Extrair informações relevantes
            informacoes_web = {
                'utilizado': True,
                'resultados': [],
                'ncms_mentionados': [],
                'descricao_identificada': None,
                'categoria_identificada': None,
                'fontes': []
            }
            
            # ✅ MELHORIA: Padrões para encontrar NCMs mencionados
            # Aceita: 85171200, 8517.12.00, 8517 12 00
            padrao_ncm = r'\b(\d{4})[.\s]?(\d{2})[.\s]?(\d{2})\b'
            
            for resultado in resultados:
                titulo = resultado.get('title', '')
                snippet = resultado.get('body', '')
                url = resultado.get('href', '')
                
                # Buscar NCMs mencionados no texto
                texto_busca = f"{titulo} {snippet}"
                matches_ncm = re.findall(padrao_ncm, texto_busca)
                
                # Converter matches para formato NCM (8 dígitos)
                for match in matches_ncm:
                    if len(match) == 3:  # (4 dígitos, 2 dígitos, 2 dígitos)
                        ncm_formatado = f"{match[0]}{match[1]}{match[2]}"
                        if len(ncm_formatado) == 8 and ncm_formatado not in informacoes_web['ncms_mentionados']:
                            informacoes_web['ncms_mentionados'].append(ncm_formatado)
                
                informacoes_web['resultados'].append({
                    'titulo': titulo,
                    'snippet': snippet[:300],  # Limitar tamanho
                    'url': url
                })
                
                if url:
                    informacoes_web['fontes'].append(url)
            
            # Tentar identificar categoria/descrição genérica do produto
            # Ex: "iPhone" → "telefone celular", "smartphone"
            texto_completo = ' '.join([r.get('titulo', '') + ' ' + r.get('snippet', '') for r in informacoes_web['resultados']])
            
            # ✅ MELHORIA: Procurar termos comuns de classificação (mais abrangente)
            termos_classificacao = [
                ('telefone celular', ['telefone celular', 'celular', 'mobile phone']),
                ('smartphone', ['smartphone', 'smart phone', 'iphone', 'android']),
                ('aparelho telefônico', ['aparelho telefônico', 'telefone', 'phone']),
                ('notebook', ['notebook', 'laptop', 'computador portátil']),
                ('computador portátil', ['computador portátil', 'portátil']),
                ('tablet', ['tablet', 'ipad']),
                ('equipamento eletrônico', ['equipamento eletrônico', 'eletrônico']),
                ('veículo', ['veículo', 'automóvel', 'carro', 'vehicle']),
                ('máquina', ['máquina', 'machine']),
                ('equipamento', ['equipamento', 'equipment']),
                ('aparelho', ['aparelho', 'device', 'aparelho'])
            ]
            
            texto_lower = texto_completo.lower()
            for categoria, variantes in termos_classificacao:
                for variante in variantes:
                    if variante.lower() in texto_lower:
                        informacoes_web['categoria_identificada'] = categoria
                        logger.info(f'✅ Categoria identificada: {categoria} (via termo: {variante})')
                        break
                if informacoes_web['categoria_identificada']:
                    break
            
            logger.info(f'✅ Web search: {len(informacoes_web["resultados"])} resultados, {len(informacoes_web["ncms_mentionados"])} NCMs mencionados')
            
            # ✅ NOVO: Salvar no cache (com limite de tamanho)
            if len(self._cache_web_search) >= self._cache_web_search_max_size:
                # Remover item mais antigo (FIFO simples - remover primeiro item)
                primeiro_item = next(iter(self._cache_web_search))
                del self._cache_web_search[primeiro_item]
                logger.debug(f'🗑️ Cache web search cheio, removendo item mais antigo: "{primeiro_item}"')
            
            self._cache_web_search[descricao_normalizada] = informacoes_web
            logger.debug(f'💾 Resultado salvo no cache web search para: "{descricao}"')
            
            return informacoes_web
            
        except Exception as e:
            logger.warning(f'⚠️ Erro ao buscar na web para "{descricao}": {e}')
            # ✅ NOVO: Salvar None no cache para evitar tentativas repetidas (com TTL implícito via limite de cache)
            # Não salvar erro no cache para permitir retry em caso de erro temporário
            return None
    
    def sugerir_ncm_com_ia(
        self,
        descricao: str,
        contexto: Optional[Dict] = None,
        usar_cache: bool = True,
        validar_sugestao: bool = True,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sugere NCM usando IA com RAG, feedbacks históricos e web search
        
        ✅ NOVO: Busca web integrada para produtos modernos (ex: iPhone → telefone celular)
        
        Args:
            descricao: Descrição do produto
            contexto: Contexto adicional (opcional)
            usar_cache: Se deve usar cache local
            validar_sugestao: Se deve validar sugestão contra cache
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict com sucesso, resposta, ncm_sugerido, confianca e validado
        """
        if not descricao:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'Descrição do produto é obrigatória'
            }
        
        try:
            # ✅ MELHORIA: Usar o mesmo método da aba de consulta
            # Isso garante consistência e usa toda a lógica de RAG, feedbacks e web search
            logger.info(f'🤖 sugerir_ncm_com_ia: Sugerindo NCM para "{descricao}" (usando método da aba de consulta)')
            
            # Preparar contexto igual ao endpoint /api/int/classif/ia/sugerir-ncm
            from ai_service import AIService
            from db_manager import buscar_ncms_por_descricao, get_classif_ncm_completo, buscar_notas_explicativas_nesh_por_descricao, buscar_feedbacks_similares
            
            ai_service = AIService()
            contexto_ia = contexto.copy() if contexto else {}
            
            # ✅ NOVO: Buscar informações na web ANTES de chamar a IA
            # Isso ajuda especialmente com produtos modernos que não aparecem literalmente na NESH/NCM
            # ✅ MELHORIA: Tratamento de erros melhorado (continua sem web search se houver erro)
            contexto_web = None
            try:
                contexto_web = self._buscar_web_para_produto(descricao)
            except Exception as e:
                logger.warning(f'⚠️ Erro ao buscar na web para "{descricao}" (continuando sem web search): {e}')
                contexto_web = None  # Continuar sem web search se houver erro
            
            if contexto_web:
                logger.info(f'🌐 Web search ativado: {len(contexto_web.get("resultados", []))} resultados encontrados')
                
                # ✅ Validar NCMs mencionados na web contra cache oficial
                ncms_web_validados = []
                if contexto_web.get('ncms_mentionados'):
                    for ncm_web in contexto_web['ncms_mentionados']:
                        ncm_info = get_classif_ncm_completo(ncm_web)
                        if ncm_info:
                            ncms_web_validados.append({
                                'ncm': ncm_web,
                                'descricao': ncm_info.get('descricao', ''),
                                'fonte': 'web_validado'
                            })
                            logger.info(f'✅ NCM {ncm_web} mencionado na web e validado no cache oficial')
                
                # ✅ Adicionar NCMs validados ao contexto_web (para retornar na resposta)
                if ncms_web_validados:
                    contexto_web['ncms_web_validados'] = ncms_web_validados
                
                # ✅ Adicionar contexto_web ao contexto_ia (para passar para a IA)
                contexto_ia['contexto_web'] = contexto_web
                
                # ✅ Adicionar instrução para IA usar informações da web
                if contexto_web.get('categoria_identificada'):
                    instrucao_web = f'🌐 INFORMAÇÃO DA WEB: O produto "{descricao}" foi identificado como "{contexto_web["categoria_identificada"]}" em fontes da web. Use esta informação para classificar corretamente. '
                else:
                    instrucao_web = f'🌐 INFORMAÇÃO DA WEB: Foram encontradas informações sobre "{descricao}" na web. Use estas informações para entender melhor o produto e classificar corretamente. '
                
                if ncms_web_validados:
                    instrucao_web += f'Os seguintes NCMs foram mencionados na web e VALIDADOS no cache oficial: {", ".join([n["ncm"] for n in ncms_web_validados])}. Considere estes NCMs como candidatos prioritários. '
                
                contexto_ia['instrucao_web'] = instrucao_web

            # ✅ Termo para busca NESH (híbrido): se a web identificar categoria genérica,
            # usar isso para buscar NESH por descrição (ex: "iPhone" → "telefone celular").
            termo_para_nesh = descricao
            try:
                cat_web = (contexto_web or {}).get('categoria_identificada')
                if cat_web and isinstance(cat_web, str) and len(cat_web.strip()) >= 3:
                    termo_para_nesh = cat_web.strip()
            except Exception:
                pass
            
            # ✅ RAG: Buscar NCMs similares no cache (mesma lógica do endpoint)
            ncms_similares_cache = []
            if usar_cache:
                try:
                    # Buscar primeiro com o termo completo
                    ncms_similares_cache = buscar_ncms_por_descricao(descricao, limite=10, incluir_relacionados=False)
            
                    # Se não encontrou, tentar buscar apenas palavras-chave principais
                    if not ncms_similares_cache:
                        palavras_comuns = {'para', 'de', 'em', 'com', 'sem', 'por', 'a', 'o', 'e', 'ou', 'do', 'da', 'dos', 'das'}
                        palavras_descricao = [p.lower() for p in descricao.split() if p.lower() not in palavras_comuns and len(p) > 2]
                        
                        for palavra in palavras_descricao[:3]:
                            resultados_parciais = buscar_ncms_por_descricao(palavra, limite=5, incluir_relacionados=False)
                            if resultados_parciais:
                                ncms_existentes = {n['ncm'] for n in ncms_similares_cache}
                                for ncm in resultados_parciais:
                                    if ncm['ncm'] not in ncms_existentes:
                                        ncms_similares_cache.append(ncm)
                                        ncms_existentes.add(ncm['ncm'])
                                        if len(ncms_similares_cache) >= 10:
                                            break
                            if len(ncms_similares_cache) >= 10:
                                break
                    
                    # Buscar feedbacks históricos
                    feedbacks_similares = []
                    ncms_corretos_feedback = {}
                    try:
                        feedbacks_similares = buscar_feedbacks_similares(descricao, limite=5)
                        if feedbacks_similares:
                            for feedback in feedbacks_similares:
                                ncm_correto = feedback.get('ncm_correto')
                                desc_ncm_correto = feedback.get('descricao_ncm_correto', '')
                                if ncm_correto:
                                    ncms_corretos_feedback[ncm_correto] = desc_ncm_correto
                        logger.info(f"[IA_FEEDBACK] Encontrados {len(feedbacks_similares)} feedbacks similares para '{descricao}'")
                    except Exception as e:
                        logger.warning(f"[IA_FEEDBACK] Erro ao buscar feedbacks: {e}")
                    
                    # Priorizar NCMs com feedback
                    if ncms_similares_cache:
                        ncms_lista_priorizada = []
                        ncms_adicionados = set()
                        
                        # PRIMEIRO: Adicionar NCMs corretos dos feedbacks
                        if ncms_corretos_feedback:
                            for ncm_correto, desc_correto in ncms_corretos_feedback.items():
                                ncm_info = get_classif_ncm_completo(ncm_correto)
                                if ncm_info:
                                    ncms_lista_priorizada.append({
                                        'ncm': ncm_correto,
                                        'descricao': desc_correto or ncm_info.get('descricao', ''),
                                        'unidade': ncm_info.get('unidade', ''),
                                        'prioridade_feedback': True
                                    })
                                    ncms_adicionados.add(ncm_correto)
                        
                        # SEGUNDO: Adicionar outros NCMs similares
                        for n in ncms_similares_cache[:10]:
                            if n['ncm'] not in ncms_adicionados:
                                ncms_lista_priorizada.append({
                                    'ncm': n['ncm'],
                                    'descricao': n['descricao'],
                                    'unidade': n.get('unidadeMedidaEstatistica', ''),
                                    'prioridade_feedback': False
                                })
                                ncms_adicionados.add(n['ncm'])
                        
                        contexto_ia['ncms_similares_no_cache'] = ncms_lista_priorizada[:10]
                        contexto_ia['feedbacks_historicos'] = feedbacks_similares
                        
                        instrucao_rag = 'Estes são NCMs reais encontrados no cache local da nomenclatura oficial. '
                        if ncms_corretos_feedback:
                            instrucao_rag += f'⚠️ ATENÇÃO ESPECIAL: Os NCMs marcados com "✅ FEEDBACK CORRETO" foram previamente marcados como CORRETOS por usuários para descrições similares. PRIORIZE ESTES NCMs! '
                        instrucao_rag += 'Use-os como referência PRINCIPAL. Se encontrar um NCM similar na lista, sugira esse NCM exato. Se não encontrar exatamente, sugira o NCM mais próximo da lista. NUNCA sugira NCMs que não existem na lista fornecida.'
                        contexto_ia['instrucao_rag'] = instrucao_rag
                        
                        logger.info(f"[IA_RAG] Encontrados {len(ncms_similares_cache)} NCMs similares no cache para '{descricao}'")
                    
                except Exception as e:
                    logger.warning(f"[IA_RAG] Erro ao buscar NCMs similares no cache: {e}")
            
            # ✅ ABORDAGEM HÍBRIDA: GPT-5 + NESH
            # 1. GPT-5 sugere o NCM (conhecimento mais atualizado)
            # 2. Buscar NESH para o produto (fallback do fallback)
            # 3. Combinar descrição do NCM + NESH para validação
            
            import os
            modelo_ncm = os.getenv('OPENAI_MODEL_CONHECIMENTO_GERAL', 'gpt-5.1')
            logger.info(f'🤖 Usando modelo {modelo_ncm} para classificação de NCM (GPT-5 para melhor precisão)')
            resultado_ia = ai_service.sugerir_ncm_por_descricao(
                descricao, 
                contexto_ia if contexto_ia else None,
                model=modelo_ncm  # ✅ GPT-5 para melhor classificação
            )
            
            # ✅ NOVO: Buscar NESH para o produto (fallback do fallback)
            # Isso enriquece a resposta e valida se o NCM sugerido faz sentido
            nota_nesh_produto = None
            ncm_sugerido_ia = resultado_ia.get('ncm')
            try:
                from db_manager import buscar_notas_explicativas_nesh_por_descricao
                logger.info(f'📚 Buscando NESH para produto "{termo_para_nesh}" (validação híbrida)')
                notas_nesh = buscar_notas_explicativas_nesh_por_descricao(termo_para_nesh, limite=3)
                if notas_nesh:
                    # Pegar a primeira nota mais relevante
                    nota_nesh_produto = notas_nesh[0] if isinstance(notas_nesh, list) else notas_nesh
                    logger.info(f'✅ NESH encontrada para produto "{termo_para_nesh}"')
                    
                    # ✅ Observação (NESH por descrição): pode retornar falso-positivo
                    # (ex.: palavra aparece em um trecho não relacionado ao produto).
                    # Não usar isso como "fonte de verdade" para validar o NCM final.
                    if ncm_sugerido_ia and nota_nesh_produto:
                        # A NESH não tem "ncm" direto; derivar de position_code/subposition_code
                        def _clean_code(code: str) -> str:
                            return str(code or '').strip().replace('.', '').replace('-', '').replace(' ', '')
                        ncm_nesh = _clean_code(
                            nota_nesh_produto.get('subposition_code')
                            or nota_nesh_produto.get('position_code')
                            or ''
                        )
                        # Se o "capítulo" derivado do trecho NESH por descrição difere do NCM sugerido,
                        # avisar o usuário (sem reduzir confiança automaticamente, pois é evidência fraca).
                        if ncm_nesh and ncm_nesh[:4] != ncm_sugerido_ia[:4]:
                            logger.warning(f'⚠️ NCM sugerido ({ncm_sugerido_ia[:4]}) difere do capítulo da NESH encontrada ({ncm_nesh[:4]})')
                            resultado_ia['explicacao'] += (
                                f" ⚠️ ATENÇÃO: a busca NESH por palavra ('{termo_para_nesh}') encontrou um trecho que sugere capítulo {ncm_nesh[:4]}, "
                                f"mas o NCM sugerido começa com {ncm_sugerido_ia[:4]}. Use a NESH do NCM final para validar."
                            )
            except Exception as e:
                logger.warning(f'⚠️ Erro ao buscar NESH para produto "{descricao}": {e}')
                nota_nesh_produto = None
            
            # ✅ VALIDAÇÃO: Verificar se o NCM sugerido existe no cache (mesma lógica do endpoint)
            ncm_sugerido_valido = False
            ncm_sugerido = resultado_ia.get('ncm')
            ncm_final = ncm_sugerido
            
            # Obter lista de NCMs do cache para fallback (do contexto_ia ou buscar novamente)
            ncms_lista_cache = []
            if contexto_ia and 'ncms_similares_no_cache' in contexto_ia:
                ncms_lista_cache = contexto_ia['ncms_similares_no_cache']
            elif usar_cache:
                # Se não tem no contexto, buscar novamente
                ncms_lista_cache = buscar_ncms_por_descricao(descricao, limite=10, incluir_relacionados=False)
            
            if validar_sugestao and ncm_sugerido:
                ncm_info = get_classif_ncm_completo(ncm_sugerido)
                if ncm_info and ncm_info.get('ncm'):
                    ncm_sugerido_valido = True
                else:
                    # NCM sugerido não existe no cache - usar NCMs similares do cache
                    if ncms_lista_cache:
                        # Pegar o primeiro NCM do cache como fallback
                        ncm_final = ncms_lista_cache[0].get('ncm', '')
                        ncm_info_cache = get_classif_ncm_completo(ncm_final)
                        if ncm_info_cache and ncm_info_cache.get('ncm'):
                            ncm_sugerido_valido = True
                            logger.info(f'✅ Usando NCM {ncm_final} do cache (NCM {ncm_sugerido} sugerido pela IA não estava no cache)')
            
            # ✅ FALLBACK: Se IA não retornou NCM, usar primeiro do cache
            if not ncm_final and ncms_lista_cache:
                ncm_final = ncms_lista_cache[0].get('ncm', '')
                ncm_info_cache = get_classif_ncm_completo(ncm_final)
                if ncm_info_cache and ncm_info_cache.get('ncm'):
                    ncm_sugerido_valido = True
                    logger.info(f'✅ Fallback: Usando primeiro NCM do cache: {ncm_final}')

            # ✅ Resolver "pegadinha" de subitem (8 dígitos) com regra determinística:
            # Se existir "para semeadura" vs "outros" no MESMO grupo de 6 dígitos,
            # assumir "Outros" para consumo/supermercado/in natura (default),
            # e só usar "Semeadura" quando o usuário mencionar explicitamente.
            subitem_decisao = None
            try:
                if ncm_final and isinstance(ncm_final, str):
                    ncm_clean8 = ncm_final.strip().replace('.', '').replace('-', '').replace(' ', '')
                    if len(ncm_clean8) == 8 and ncm_clean8.isdigit():
                        from db_manager import buscar_ncms_relacionados_hierarquia

                        grupo6 = ncm_clean8[:6]
                        relacionados = buscar_ncms_relacionados_hierarquia(ncm_clean8) or []
                        opcs = []
                        for r in relacionados:
                            n = (r.get("ncm") or "").strip()
                            d = (r.get("descricao") or "").strip()
                            if len(n) == 8 and n.isdigit() and n.startswith(grupo6):
                                opcs.append({"ncm": n, "descricao": d})

                        if len(opcs) >= 2:
                            semeadura_opts = [
                                o for o in opcs
                                if any(k in (o.get("descricao", "").lower()) for k in ("semeadura", "sementeira"))
                            ]
                            outros_opts = [
                                o for o in opcs
                                if (o.get("descricao", "").lower().strip().startswith("outros"))
                            ]

                            if semeadura_opts and outros_opts:
                                desc_l = (descricao or "").lower()
                                semeadura_kw = ("semeadura", "sementeira", "plantio", "plantar", "semente", "muda")
                                consumo_kw = ("fresco", "in natura", "supermercado", "consumo", "culin", "cozinha", "aliment")

                                if any(k in desc_l for k in semeadura_kw):
                                    escolhido = semeadura_opts[0]["ncm"]
                                    motivo = "você mencionou semeadura/plantio"
                                else:
                                    # Default seguro para casos genéricos de consumidor:
                                    # se menciona consumo (ou não menciona semeadura), cair em "Outros".
                                    escolhido = outros_opts[0]["ncm"]
                                    motivo = "por padrão, assumi consumo (não há indicação de semeadura)"
                                    if any(k in desc_l for k in consumo_kw):
                                        motivo = "você mencionou consumo/supermercado/in natura"

                                if escolhido and escolhido != ncm_clean8:
                                    logger.info(f"✅ Ajuste subitem: {ncm_clean8} -> {escolhido} (grupo {grupo6})")
                                    ncm_final = escolhido
                                    # Revalidar no cache
                                    ncm_info2 = get_classif_ncm_completo(ncm_final)
                                    if ncm_info2 and ncm_info2.get("ncm"):
                                        ncm_sugerido_valido = True

                                subitem_decisao = {
                                    "grupo6": grupo6,
                                    "escolhido": ncm_final,
                                    "motivo": motivo,
                                    "opcoes": opcs[:5],
                                }
            except Exception as e:
                logger.debug(f"⚠️ Erro ao resolver subitem OUTROS/semeadura: {e}")
            
            # ✅ Buscar nota explicativa NESH para o NCM final (prioridade)
            # A NESH exibida ao usuário deve ser a do NCM final (fonte de validação).
            # A NESH por descrição (nota_nesh_produto) fica como auxiliar, não como validação.
            nota_nesh_ncm = None
            if ncm_final:
                # Se já temos NESH do produto e o NCM coincide, usar ela
                ncm_nesh_prod = ''
                if nota_nesh_produto:
                    try:
                        def _clean_code(code: str) -> str:
                            return str(code or '').strip().replace('.', '').replace('-', '').replace(' ', '')
                        ncm_nesh_prod = _clean_code(
                            nota_nesh_produto.get('subposition_code')
                            or nota_nesh_produto.get('position_code')
                            or ''
                        )
                    except Exception:
                        ncm_nesh_prod = ''
                if ncm_nesh_prod and ncm_nesh_prod.startswith(ncm_final[:4]):
                    nota_nesh_ncm = nota_nesh_produto
                    logger.info(f'📚 Usando NESH do produto para NCM {ncm_final}')
                else:
                    # Buscar NESH específica do NCM
                    try:
                        from db_manager import buscar_nota_explicativa_nesh_por_ncm
                        nota_nesh_ncm = buscar_nota_explicativa_nesh_por_ncm(ncm_final)
                        if nota_nesh_ncm:
                            logger.info(f'📚 NESH encontrada para NCM {ncm_final}')
                    except Exception as e:
                        logger.warning(f'⚠️ Erro ao buscar nota NESH para NCM {ncm_final}: {e}')
            
            # Preparar NCMs alternativos (usar sugestões da IA ou do cache)
            ncms_alternativos = []
            sugestoes_ia = resultado_ia.get('sugestoes_alternativas', [])
            if sugestoes_ia:
                # Usar sugestões da IA
                for ncm_alt in sugestoes_ia[:5]:
                    ncm_info_alt = get_classif_ncm_completo(ncm_alt)
                    if ncm_info_alt:
                        ncms_alternativos.append({
                            'ncm': ncm_alt,
                            'descricao': ncm_info_alt.get('descricao', '')
                        })
            elif ncms_lista_cache:
                # Se não tem sugestões da IA, usar do cache
                if ncm_final and ncm_final == ncms_lista_cache[0].get('ncm', ''):
                    ncms_alternativos = [{'ncm': n.get('ncm', ''), 'descricao': n.get('descricao', '')} for n in ncms_lista_cache[1:6]]
                else:
                    ncms_alternativos = [{'ncm': n.get('ncm', ''), 'descricao': n.get('descricao', '')} for n in ncms_lista_cache[:5]]
            
            # Verificar se web search foi usado
            web_search_utilizado = contexto_ia.get('contexto_web', {}).get('utilizado', False) if contexto_ia else False
            contexto_web_resp = contexto_ia.get('contexto_web') if contexto_ia else None
            
            # ✅ Preparar explicação híbrida (GPT-5 + NESH)
            explicacao_final = resultado_ia.get('explicacao', f'NCM sugerido baseado na descrição: {descricao}')
            
            # ✅ Não duplicar NESH dentro da "Explicação da IA".
            # A NESH relevante é exibida no bloco "Nota Explicativa NESH", baseada no NCM final.
            
            # Preparar resultado (usar ncm_final que pode ter sido substituído pelo cache)
            resultado = {
                'ncm_sugerido': ncm_final or '',
                'confianca': resultado_ia.get('confianca', 0.8) if ncm_sugerido_valido else 0.5,
                'explicacao': explicacao_final,
                'validado': ncm_sugerido_valido,
                'ncms_alternativos': ncms_alternativos,
                'nota_nesh': nota_nesh_ncm,
                'nota_nesh_produto': nota_nesh_produto,  # ✅ NOVO: NESH do produto (fallback)
                'web_search_utilizado': web_search_utilizado,
                'contexto_web': contexto_web_resp,
                'ncm_original_ia': ncm_sugerido_ia if ncm_sugerido_ia and ncm_sugerido_ia != ncm_final else None,
                'sugestoes_alternativas': sugestoes_ia,
                'abordagem_hibrida': True,  # ✅ Flag indicando que usou abordagem híbrida
                'subitem_decisao': subitem_decisao,
            }
            
            # Formatar resposta
            resposta = self._formatar_resposta_sugestao_ncm(resultado, descricao, ncms_lista_cache)
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'ncm_sugerido': resultado.get('ncm_sugerido', ''),
                'confianca': resultado.get('confianca', 0),
                'validado': resultado.get('validado', False)
            }
        except Exception as e:
            logger.error(f'Erro ao sugerir NCM com IA: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro ao sugerir NCM: {str(e)}'
            }
    
    def _formatar_resposta_sugestao_ncm(
        self,
        resultado: Dict[str, Any],
        descricao: str,
        ncms_lista_cache: List[Dict]
    ) -> str:
        """Formata resposta de sugestão de NCM"""
        resposta = f"🤖 **Sugestão de NCM para '{descricao}'**\n\n"
        
        ncm_sugerido_resp = resultado.get('ncm_sugerido', '')
        confianca = resultado.get('confianca', 0)
        explicacao = resultado.get('explicacao', '')
        validado = resultado.get('validado', False)
        ncms_alternativos = resultado.get('ncms_alternativos', [])
        nota_nesh = resultado.get('nota_nesh')
        web_search_utilizado_resp = resultado.get('web_search_utilizado', False)
        contexto_web_resp = resultado.get('contexto_web')
        subitem_decisao = resultado.get('subitem_decisao') if isinstance(resultado, dict) else None
        
        if ncm_sugerido_resp:
            resposta += f"**NCM Sugerido:** {ncm_sugerido_resp}\n"
            resposta += f"**Confiança:** {confianca * 100:.1f}%\n"
            
            # ✅ Informar se NCM foi substituído pelo cache
            ncm_original_ia = resultado.get('ncm_original_ia')
            if ncm_original_ia and ncm_original_ia != ncm_sugerido_resp:
                resposta += f"⚠️ **Ajuste:** NCM {ncm_original_ia} sugerido pela IA não estava no cache. Usando NCM {ncm_sugerido_resp} do cache oficial.\n"
            
            # ✅ Informar se usou web search
            if web_search_utilizado_resp and contexto_web_resp:
                resposta += f"🌐 **Busca na web utilizada** para enriquecer a sugestão\n"
                
                # Mostrar categoria identificada
                if contexto_web_resp.get('categoria_identificada'):
                    resposta += f"   📦 Produto identificado como: **{contexto_web_resp['categoria_identificada']}**\n"
                
                # Mostrar NCMs validados da web
                ncms_web_validados = contexto_web_resp.get('ncms_web_validados', [])
                if ncms_web_validados:
                    resposta += f"   ✅ NCMs mencionados na web e validados: {', '.join([n['ncm'] for n in ncms_web_validados])}\n"
                
                # Mostrar fontes
                if contexto_web_resp.get('fontes'):
                    num_fontes = len(contexto_web_resp.get('fontes', []))
                    resposta += f"   🔗 Fontes consultadas: {num_fontes}\n"
            
            if validado:
                resposta += f"✅ **Validado:** NCM existe no cache\n"
            else:
                resposta += f"⚠️ **Atenção:** NCM não encontrado no cache\n"

            # ✅ Explicar a regra do subitem (ex.: semeadura vs Outros) sem pedir "1/2"
            try:
                if isinstance(subitem_decisao, dict) and subitem_decisao.get("grupo6") and subitem_decisao.get("opcoes"):
                    grupo6 = subitem_decisao.get("grupo6")
                    opcs = subitem_decisao.get("opcoes") or []
                    escolhido = subitem_decisao.get("escolhido")
                    motivo = subitem_decisao.get("motivo") or ""

                    semeadura = next((o for o in opcs if "semeadura" in (o.get("descricao", "").lower())), None)
                    outros = next((o for o in opcs if (o.get("descricao", "").lower().strip().startswith("outros"))), None)

                    if semeadura and outros:
                        resposta += f"\n🧭 **Escolha do subitem (grupo {grupo6})**\n"
                        resposta += f"- Se for **para semeadura/plantio**: **{semeadura.get('ncm')}** — {semeadura.get('descricao')}\n"
                        resposta += f"- Se for **para consumo (supermercado/in natura)**: **{outros.get('ncm')}** — {outros.get('descricao')}\n"
                        if escolhido:
                            resposta += f"✅ **Assumi:** **{escolhido}** ({motivo})\n"
            except Exception:
                pass
            
            # ✅ NOVO: Adicionar nota explicativa NESH se disponível (sempre mostrar, mesmo se NCM não validado)
            if nota_nesh:
                posicao = nota_nesh.get('position_code', '')
                titulo = nota_nesh.get('position_title', '')
                texto_nesh = nota_nesh.get('text', '')
                
                resposta += f"\n📚 **Nota Explicativa NESH (Posição {posicao}):**\n"
                if titulo:
                    resposta += f"   {titulo}\n\n"
                # Limitar tamanho do texto (primeiros 1000 caracteres para mais contexto)
                if texto_nesh:
                    texto_resumido = texto_nesh[:1000] + '...' if len(texto_nesh) > 1000 else texto_nesh
                    resposta += f"   {texto_resumido}\n"

                # ✅ Rodapé de auditoria (fonte da NESH) direto na resposta de NCM
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
                    if show and isinstance(nota_nesh, dict):
                        meta = {
                            "fonte": nota_nesh.get("_nesh_source") or "desconhecida",
                            "modo": "ncm_sugestao",
                        }
                        resposta += f"[NESH_META:{json.dumps(meta, ensure_ascii=False)}]"
                except Exception:
                    pass
            
            if explicacao:
                resposta += f"\n**Explicação da IA:**\n{explicacao}\n"
            
            if ncms_alternativos:
                resposta += f"\n**NCMs Alternativos:**\n"
                for alt in ncms_alternativos[:5]:  # Máximo 5 alternativas
                    alt_ncm = alt.get('ncm', '')
                    alt_desc = alt.get('descricao', '')
                    resposta += f"  - {alt_ncm}: {alt_desc}\n"
        else:
            # ✅ MELHORIA: Se não tem NCM sugerido mas tem do cache, usar o primeiro
            if ncms_lista_cache and not ncm_sugerido_resp:
                primeiro_ncm = ncms_lista_cache[0]
                ncm_sugerido_resp = primeiro_ncm.get('ncm', '')
                if ncm_sugerido_resp:
                    # Validar o NCM do cache
                    from db_manager import get_classif_ncm_completo, buscar_nota_explicativa_nesh_por_ncm
                    ncm_info_cache = get_classif_ncm_completo(ncm_sugerido_resp)
                    validado = ncm_info_cache is not None and ncm_info_cache.get('ncm') == ncm_sugerido_resp
                    confianca = 0.7 if validado else 0.5
                    
                    resposta = f"🤖 **Sugestão de NCM para '{descricao}'**\n\n"
                    resposta += f"**NCM Sugerido:** {ncm_sugerido_resp}\n"
                    resposta += f"**Confiança:** {confianca * 100:.1f}%\n"
                    resposta += f"💡 **Fonte:** NCM encontrado no cache local (IA não retornou sugestão)\n"
                    
                    if validado:
                        resposta += f"✅ **Validado:** NCM existe no cache\n"
                        
                        # Buscar NESH para o NCM do cache
                        try:
                            nota_nesh_cache = buscar_nota_explicativa_nesh_por_ncm(ncm_sugerido_resp)
                            if nota_nesh_cache:
                                posicao = nota_nesh_cache.get('position_code', '')
                                titulo = nota_nesh_cache.get('position_title', '')
                                texto_nesh = nota_nesh_cache.get('text', '')
                                
                                resposta += f"\n📚 **Nota Explicativa NESH (Posição {posicao}):**\n"
                                if titulo:
                                    resposta += f"   {titulo}\n\n"
                                if texto_nesh:
                                    texto_resumido = texto_nesh[:1000] + '...' if len(texto_nesh) > 1000 else texto_nesh
                                    resposta += f"   {texto_resumido}\n"
                        except Exception as e:
                            logger.warning(f'⚠️ Erro ao buscar NESH para NCM do cache: {e}')
                    
                    # Mostrar alternativos se houver
                    if len(ncms_lista_cache) > 1:
                        resposta += f"\n**NCMs Alternativos Encontrados:**\n"
                        for alt in ncms_lista_cache[1:6]:  # Próximos 5
                            alt_ncm = alt.get('ncm', '')
                            alt_desc = alt.get('descricao', '')
                            resposta += f"  - {alt_ncm}: {alt_desc}\n"
                else:
                    resposta += f"⚠️ **Não foi possível sugerir um NCM.**\n"
                    resposta += f"💡 **Dica:** Tente usar a função buscar_ncms_por_descricao para encontrar NCMs similares.\n"
            else:
                resposta += f"⚠️ **Não foi possível sugerir um NCM.**\n"
                resposta += f"💡 **Dica:** Tente usar a função buscar_ncms_por_descricao para encontrar NCMs similares.\n"
                
                if ncms_alternativos:
                    resposta += f"\n**NCMs Similares Encontrados:**\n"
                    for alt in ncms_alternativos[:5]:
                        alt_ncm = alt.get('ncm', '')
                        alt_desc = alt.get('descricao', '')
                        resposta += f"  - {alt_ncm}: {alt_desc}\n"
        
        return resposta
    
    def detalhar_ncm(
        self,
        ncm: str,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detalha um NCM mostrando hierarquia e todos os NCMs de 8 dígitos do grupo
        
        Args:
            ncm: NCM a detalhar
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict com sucesso, resposta, hierarquia, total_8_digitos e grupo_base
        """
        if not ncm:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'NCM é obrigatório'
            }
        
        try:
            from db_manager import buscar_ncms_do_grupo
            
            logger.info(f'📋 detalhar_ncm: Detalhando NCM "{ncm}"')
            
            # Buscar hierarquia e todos os NCMs de 8 dígitos do grupo
            resultado = buscar_ncms_do_grupo(ncm)
            
            if resultado.get('erro'):
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro'),
                    'mensagem': f'Erro ao detalhar NCM: {resultado.get("erro")}'
                }
            
            hierarquia = resultado.get('hierarquia', [])
            ncms_8_digitos = resultado.get('ncms_8_digitos', [])
            grupo_base = resultado.get('grupo_base', '')
            total_8_digitos = resultado.get('total_8_digitos', 0)
            
            # Formatar resposta
            resposta = f"📋 **Detalhamento do NCM {ncm}**\n\n"
            
            # Mostrar hierarquia
            if hierarquia:
                resposta += "**📊 Hierarquia Completa:**\n\n"
                for item in hierarquia:
                    nivel = item.get('nivel', '')
                    ncm_item = item.get('ncm', '')
                    descricao = item.get('descricao', '')
                    formato = item.get('formato', ncm_item)
                    
                    # Emoji baseado no nível
                    emoji = {
                        'capitulo': '📚',
                        'posicao': '📖',
                        'subitem': '📄'
                    }.get(nivel, '📋')
                    
                    nivel_nome = {
                        'capitulo': 'Capítulo (4 dígitos)',
                        'posicao': 'Posição (6 dígitos)',
                        'subitem': 'Subitem (8 dígitos)'
                    }.get(nivel, nivel)
                    
                    resposta += f"{emoji} **{nivel_nome}:** {formato}\n"
                    resposta += f"   {descricao}\n\n"
            else:
                resposta += "⚠️ **Hierarquia não encontrada no cache.**\n\n"
            
            # Mostrar todos os NCMs de 8 dígitos do grupo
            if ncms_8_digitos:
                resposta += f"**📋 Todos os NCMs de 8 dígitos do grupo {grupo_base}** ({total_8_digitos} NCM(s)):\n\n"
                
                # Agrupar por posição (6 dígitos) para melhor organização
                ncms_por_posicao = {}
                for ncm_8_item in ncms_8_digitos:
                    ncm_8 = ncm_8_item.get('ncm', '')
                    if len(ncm_8) >= 6:
                        posicao = ncm_8[:6]
                        if posicao not in ncms_por_posicao:
                            ncms_por_posicao[posicao] = []
                        ncms_por_posicao[posicao].append(ncm_8_item)
                
                # Mostrar agrupado por posição
                for posicao, items in sorted(ncms_por_posicao.items()):
                    formato_posicao = f"{posicao[:2]}.{posicao[2:4]}.{posicao[4:]}"
                    resposta += f"**Posição {formato_posicao}** ({len(items)} NCM(s)):\n"
                    
                    for item in items[:20]:  # Máximo 20 por posição
                        ncm_8 = item.get('ncm', '')
                        descricao_8 = item.get('descricao', '')
                        formato_8 = item.get('formato', ncm_8)
                        
                        resposta += f"  - **{formato_8}**: {descricao_8}\n"
                    
                    if len(items) > 20:
                        resposta += f"  ... e mais {len(items) - 20} NCM(s)\n"
                    
                    resposta += "\n"
            else:
                resposta += f"⚠️ **Nenhum NCM de 8 dígitos encontrado para o grupo {grupo_base}.**\n"
                resposta += f"💡 **Dica:** O grupo pode não ter NCMs de 8 dígitos cadastrados no cache.\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'hierarquia': hierarquia,
                'total_8_digitos': total_8_digitos,
                'grupo_base': grupo_base
            }
        except Exception as e:
            logger.error(f'Erro ao detalhar NCM: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'mensagem': f'Erro ao detalhar NCM: {str(e)}'
            }
    
    def baixar_nomenclatura_ncm(
        self,
        forcar_atualizacao: bool = False,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Baixa e atualiza a tabela de NCMs do Portal Único Siscomex
        
        Args:
            forcar_atualizacao: Se deve forçar atualização mesmo se recente
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict com sucesso, resposta, total_itens, ncm_processados e total_no_banco
        """
        try:
            logger.info(f'📥 baixar_nomenclatura_ncm: Iniciando download da nomenclatura (forçar={forcar_atualizacao})')
            
            # Importar dependências necessárias
            from db_manager import init_classif_cache, save_classif_ncm, set_classif_last_update, get_db_connection, get_classif_last_update
            import sqlite3
            import requests
            
            try:
                # Verificar se precisa atualizar (última atualização > 24h ou force=True)
                if not forcar_atualizacao:
                    last_update = get_classif_last_update()
                    now = datetime.now()
                    if last_update:
                        delta = now - last_update
                        if delta.total_seconds() < 86400:  # 24 horas
                            horas_atras = int(delta.total_seconds() / 3600)
                            return {
                                'sucesso': True,
                                'resposta': f'✅ **Tabela NCM já está atualizada!**\n\n📅 Última atualização: há {horas_atras} hora(s)\n\n💡 **Dica:** A tabela NCM raramente muda. Se quiser forçar atualização mesmo assim, peça explicitamente para "forçar atualização NCM".'
                            }
                
                # Inicializar cache se necessário
                init_classif_cache()
                
                # URL do ambiente de validação
                url_nomenclatura = 'https://val.portalunico.siscomex.gov.br/classif/api/publico/nomenclatura/download/json'
                
                logger.info(f'[CLASSIF] Iniciando download da nomenclatura de: {url_nomenclatura}')
                
                # Fazer download (sem autenticação - é serviço público)
                response = requests.get(url_nomenclatura, timeout=900)  # 15 minutos
                
                if response.status_code != 200:
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_DOWNLOAD',
                        'resposta': f'❌ **Erro ao baixar nomenclatura.**\n\nStatus: {response.status_code}\n\n💡 **Dica:** Verifique sua conexão com a internet ou tente novamente mais tarde.'
                    }
                
                # Parsear JSON
                try:
                    nomenclatura = response.json()
                except json.JSONDecodeError as e:
                    return {
                        'sucesso': False,
                        'erro': 'ERRO_JSON',
                        'resposta': f'❌ **Erro ao processar arquivo JSON.**\n\nDetalhes: {str(e)}'
                    }
                
                # Extrair lista de nomenclaturas
                if isinstance(nomenclatura, dict):
                    lista_ncms = nomenclatura.get('Nomenclaturas', nomenclatura.get('nomenclaturas', []))
                    if not lista_ncms:
                        lista_ncms = nomenclatura.get('itens', nomenclatura.get('ncms', nomenclatura.get('nomenclatura', [])))
                elif isinstance(nomenclatura, list):
                    lista_ncms = nomenclatura
                else:
                    return {
                        'sucesso': False,
                        'erro': 'FORMATO_INVALIDO',
                        'resposta': f'❌ **Formato do arquivo não reconhecido.**\n\nTipo recebido: {type(nomenclatura).__name__}'
                    }
                
                if not lista_ncms or len(lista_ncms) == 0:
                    return {
                        'sucesso': False,
                        'erro': 'LISTA_VAZIA',
                        'resposta': '❌ **Lista de nomenclaturas vazia ou não encontrada no arquivo.**'
                    }
                
                logger.info(f'[CLASSIF] Processando {len(lista_ncms)} itens da nomenclatura')
                
                # Processar cada item
                ncm_processados = 0
                ncm_com_unidade = 0
                
                for item in lista_ncms:
                    if not isinstance(item, dict):
                        continue
                    
                    # Extrair NCM
                    ncm = (item.get('Codigo') or
                           item.get('codigo') or
                           item.get('ncm') or
                           item.get('codigoNcm') or
                           item.get('codigoNCM') or
                           item.get('codigo_ncm') or
                           item.get('codigo_nc') or
                           item.get('codigoNomenclatura') or
                           item.get('numeroNcm') or
                           item.get('ncmCodigo'))
                    
                    if not ncm:
                        for key, value in item.items():
                            if key.lower() in ('ncm', 'codigoncm', 'codigo', 'codigo_ncm'):
                                ncm = value
                                break
                    
                    if not ncm:
                        continue
                    
                    # Normalizar NCM
                    ncm_str = str(ncm).strip().replace('.', '').replace('-', '').replace(' ', '')
                    if len(ncm_str) > 8:
                        ncm_str = ncm_str[:8]
                    
                    # Validar tamanho: 4, 6 ou 8 dígitos
                    if len(ncm_str) < 4 or not ncm_str.isdigit() or len(ncm_str) not in [4, 6, 8]:
                        continue
                    
                    # Unidade estatística (não vem no JSON)
                    unidade = None
                    
                    # Descrição
                    descricao = (item.get('Descricao') or
                                item.get('descricao') or
                                item.get('descricaoNcm') or
                                item.get('descricao_ncm') or
                                item.get('descricaoMercadoria') or
                                item.get('descricao_mercadoria') or
                                item.get('nome') or
                                item.get('texto') or
                                '')
                    
                    # Limpar descrição
                    if descricao:
                        descricao = descricao.strip()
                        if descricao.startswith('- '):
                            descricao = descricao[2:].strip()
                        elif descricao.startswith('-'):
                            descricao = descricao[1:].strip()
                    
                    # Salvar NCM
                    if save_classif_ncm(ncm_str, unidade or '', descricao):
                        ncm_processados += 1
                        if unidade:
                            ncm_com_unidade += 1
                
                # Atualizar data da última atualização
                set_classif_last_update(datetime.now())
                
                logger.info(f'[CLASSIF] Processamento concluído: {ncm_processados} NCMs processados')
                
                # Verificar total no banco
                try:
                    conn_verif = get_db_connection()
                    cursor_verif = conn_verif.cursor()
                    cursor_verif.execute('SELECT COUNT(*) FROM classif_cache')
                    total_salvo = cursor_verif.fetchone()[0]
                    conn_verif.close()
                except:
                    total_salvo = 'N/A'
                
                resposta_final = f'✅ **Nomenclatura NCM baixada e processada com sucesso!**\n\n'
                resposta_final += f'📊 **Estatísticas:**\n'
                resposta_final += f'   - Total de itens processados: {len(lista_ncms)}\n'
                resposta_final += f'   - NCMs salvos no banco: {ncm_processados}\n'
                resposta_final += f'   - Total de NCMs no banco: {total_salvo}\n'
                if ncm_com_unidade > 0:
                    resposta_final += f'   - NCMs com unidade estatística: {ncm_com_unidade}\n'
                resposta_final += f'\n💡 **Nota:** O arquivo do Portal Único não contém unidade estatística. Este campo ficará vazio no cache.\n\n'
                resposta_final += f'✅ A tabela NCM está atualizada e pronta para uso!'
                
                return {
                    'sucesso': True,
                    'resposta': resposta_final,
                    'total_itens': len(lista_ncms),
                    'ncm_processados': ncm_processados,
                    'total_no_banco': total_salvo
                }
                
            except requests.exceptions.Timeout:
                return {
                    'sucesso': False,
                    'erro': 'TIMEOUT',
                    'resposta': '❌ **Timeout ao baixar nomenclatura.**\n\n⏳ O arquivo é muito grande e o download demorou mais de 15 minutos.\n\n💡 **Dica:** Tente novamente mais tarde ou verifique sua conexão com a internet.'
                }
            except requests.exceptions.RequestException as e:
                logger.error(f'Erro ao baixar nomenclatura: {str(e)}')
                return {
                    'sucesso': False,
                    'erro': 'ERRO_NETWORK',
                    'resposta': f'❌ **Erro de rede ao baixar nomenclatura.**\n\nDetalhes: {str(e)}\n\n💡 **Dica:** Verifique sua conexão com a internet.'
                }
            except Exception as e:
                logger.error(f'Erro ao processar nomenclatura: {str(e)}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': 'ERRO',
                    'resposta': f'❌ **Erro ao processar nomenclatura.**\n\nDetalhes: {str(e)}'
                }
                
        except Exception as e:
            logger.error(f'Erro ao baixar nomenclatura NCM: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ **Erro interno ao baixar nomenclatura NCM.**\n\nDetalhes: {str(e)}'
            }
    
    def buscar_nota_explicativa_nesh(
        self,
        ncm: Optional[str] = None,
        descricao_produto: Optional[str] = None,
        limite: int = 3,
        mensagem_original: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Busca notas explicativas NESH por NCM e/ou descrição do produto
        
        Args:
            ncm: NCM para buscar (opcional)
            descricao_produto: Descrição do produto para buscar (opcional)
            limite: Limite de resultados
            mensagem_original: Mensagem original do usuário (opcional)
        
        Returns:
            Dict com sucesso, resposta, total, ncm e descricao_produto
        """
        if not ncm and not descricao_produto:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'É necessário fornecer NCM ou descrição do produto'
            }
        
        try:
            from db_manager import buscar_nota_explicativa_nesh_por_ncm, buscar_notas_explicativas_nesh_por_descricao, buscar_notas_explicativas_nesh_por_ncm_e_descricao
            
            logger.info(f'📚 buscar_nota_explicativa_nesh: NCM={ncm}, Descrição={descricao_produto}, Limite={limite}')
            
            notas = []
            
            # Se tem ambos, usar função combinada
            if ncm and descricao_produto:
                notas = buscar_notas_explicativas_nesh_por_ncm_e_descricao(ncm, descricao_produto, limite)
            # Se tem apenas NCM
            elif ncm:
                nota = buscar_nota_explicativa_nesh_por_ncm(ncm)
                if nota:
                    notas = [nota]
            # Se tem apenas descrição
            elif descricao_produto:
                notas = buscar_notas_explicativas_nesh_por_descricao(descricao_produto, limite)
            
            logger.info(f'📚 buscar_nota_explicativa_nesh: Encontradas {len(notas)} notas')
            
            # ✅ FUNÇÃO AUXILIAR: Destacar palavras buscadas em negrito
            def destacar_palavras_buscadas(texto: str, termo_busca: str) -> str:
                """
                Destaca as palavras buscadas em negrito (markdown) no texto.
                Funciona para palavras simples e compostas.
                """
                if not texto or not termo_busca:
                    return texto
                
                # Extrair palavras do termo de busca (suporta frases compostas)
                palavras = termo_busca.lower().split()
                
                # ✅ EXPANDIR PALAVRAS COM VARIAÇÕES (stemming básico)
                palavras_expandidas = []
                for palavra in palavras:
                    if len(palavra) > 2:
                        palavras_expandidas.append(palavra)
                        # Adicionar variações comuns de plural/singular
                        if palavra.endswith('o'):
                            palavras_expandidas.append(palavra + 's')  # alho → alhos
                        elif palavra.endswith('s') and len(palavra) > 3:
                            palavras_expandidas.append(palavra[:-1])  # alhos → alho
                        if palavra.endswith('dor'):
                            palavras_expandidas.append(palavra + 'es')  # ventilador → ventiladores
                        elif palavra.endswith('dores'):
                            palavras_expandidas.append(palavra[:-2])  # ventiladores → ventilador
                        if palavra.endswith('ção'):
                            palavras_expandidas.append(palavra[:-3] + 'coes')  # classificação → classificações
                        elif palavra.endswith('coes'):
                            palavras_expandidas.append(palavra[:-4] + 'ção')  # classificações → classificação
                
                # Remover duplicatas mantendo ordem
                palavras_expandidas = list(dict.fromkeys(palavras_expandidas))
                
                # Criar padrões para cada palavra (busca case-insensitive, palavra completa)
                texto_modificado = texto
                for palavra in palavras_expandidas:
                    if len(palavra) > 2:  # Ignorar palavras muito curtas
                        # Padrão para palavra completa (case-insensitive)
                        pattern = re.compile(r'\b(' + re.escape(palavra) + r')\b', re.IGNORECASE)
                        # Substituir por versão em negrito (mantendo case original)
                        texto_modificado = pattern.sub(r'**\1**', texto_modificado)
                
                return texto_modificado
            
            if not notas:
                resposta = f"⚠️ **Nenhuma nota explicativa NESH encontrada.**\n\n"
                if ncm:
                    resposta += f"💡 **Dica:** Não foi encontrada nota explicativa para o NCM {ncm}."
                if descricao_produto:
                    resposta += f"💡 **Dica:** Não foram encontradas notas explicativas para '{descricao_produto}'."
            else:
                # Extrair termo de busca para destacar
                termo_busca = descricao_produto or (ncm if ncm else '')
                
                resposta = f"📚 **Notas Explicativas NESH** ({len(notas)} nota(s))\n\n"
                
                for idx, nota in enumerate(notas, 1):
                    section = nota.get('section', '')
                    chapter = nota.get('chapter', '')
                    chapter_code = nota.get('chapter_code', '')
                    chapter_title = nota.get('chapter_title', '')
                    position_code = nota.get('position_code', '')
                    position_title = nota.get('position_title', '')
                    subposition_code = nota.get('subposition_code')
                    subposition_title = nota.get('subposition_title')
                    text = nota.get('text', '')
                    
                    # ✅ Destacar palavras buscadas em negrito
                    if termo_busca:
                        chapter_title = destacar_palavras_buscadas(chapter_title, termo_busca)
                        position_title = destacar_palavras_buscadas(position_title, termo_busca)
                        if subposition_title:
                            subposition_title = destacar_palavras_buscadas(subposition_title, termo_busca)
                        if text:
                            text = destacar_palavras_buscadas(text, termo_busca)
                    
                    resposta += f"**Nota {idx}:**\n\n"
                    
                    if section:
                        resposta += f"📑 **{section}**\n"
                    if chapter:
                        resposta += f"📚 **{chapter}** ({chapter_code}): {chapter_title}\n"
                    if position_code:
                        resposta += f"📖 **Posição {position_code}**: {position_title}\n"
                    if subposition_code:
                        resposta += f"📄 **Subposição {subposition_code}**: {subposition_title}\n"
                    
                    resposta += "\n"
                    
                    # Mostrar texto da nota (limitar tamanho se muito longo)
                    if text:
                        if len(text) > 1500:
                            texto_resumido = text[:1500] + "\n\n... (texto truncado, use 'detalhar NCM' para ver mais)"
                            resposta += f"**Nota Explicativa:**\n{texto_resumido}\n"
                        else:
                            resposta += f"**Nota Explicativa:**\n{text}\n"
                    
                    # ✅ Adicionar informação sobre palavras destacadas
                    if termo_busca:
                        palavras_buscadas = termo_busca.split()
                        palavras_encontradas = []
                        texto_lower = text.lower()
                        for palavra in palavras_buscadas:
                            if len(palavra) > 2 and palavra.lower() in texto_lower:
                                palavras_encontradas.append(f"**{palavra}**")
                        
                        if palavras_encontradas:
                            resposta += f"\n💡 **Palavras encontradas e destacadas:** {', '.join(palavras_encontradas)}\n"
                        else:
                            resposta += f"\n💡 **Nota:** As palavras buscadas ('{termo_busca}') podem não aparecer literalmente no trecho acima (texto truncado ou contexto diferente).\n"
                    
                    resposta += "\n" + ("─" * 50) + "\n\n"

            # ✅ Rodapé de auditoria (fonte da NESH), no mesmo estilo de REPORT_META
            # Ex.: [NESH_META:{"fonte":"HF","modo":"descricao"}]
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
                if show and notas and isinstance(notas[0], dict):
                    fonte = notas[0].get("_nesh_source") or "desconhecida"
                    if ncm and descricao_produto:
                        modo = "ncm+descricao"
                    elif ncm:
                        modo = "ncm"
                    else:
                        modo = "descricao"

                    meta = {"fonte": str(fonte), "modo": modo}
                    resposta += f"[NESH_META:{json.dumps(meta, ensure_ascii=False)}]"
            except Exception:
                pass
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(notas),
                'ncm': ncm,
                'descricao_produto': descricao_produto
            }
        except Exception as e:
            logger.error(f'Erro ao buscar nota explicativa NESH: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar nota explicativa NESH: {str(e)}'
            }












