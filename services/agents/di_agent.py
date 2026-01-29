"""
Agente responsável por operações relacionadas a DI (Declaração de Importação).
"""
import logging
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from ..utils.extractors import extract_processo_referencia

logger = logging.getLogger(__name__)


class DiAgent(BaseAgent):
    """
    Agente responsável por operações relacionadas a DI (Declaração de Importação).
    
    Tools suportadas:
    - obter_dados_di: Obtém dados completos de uma DI
    - vincular_processo_di: Vincula DI a um processo
    """
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            'obter_dados_di': self._obter_dados_di,
            'vincular_processo_di': self._vincular_processo_di,
            'obter_extrato_pdf_di': self._obter_extrato_pdf_di,
            'consultar_adicoes_di': self._consultar_adicoes_di,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada neste agente',
                'resposta': f'❌ Tool "{tool_name}" não está disponível no DiAgent.'
            }
        
        try:
            resultado = handler(arguments, context)
            self.log_execution(tool_name, arguments, resultado.get('sucesso', False))
            return resultado
        except Exception as e:
            logger.error(f'Erro ao executar {tool_name}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao executar {tool_name}: {str(e)}'
            }
    
    def _obter_dados_di(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Obtém dados completos de uma DI.
        
        Retorna situação, canal, data de desembaraço, data de registro e situação de entrega.
        """
        numero_di = arguments.get('numero_di', '').strip()
        
        if not numero_di:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Número da DI é obrigatório.'
            }
        
        try:
            from db_manager import buscar_di_cache
            
            di_cache = buscar_di_cache(numero_di)
            
            # ✅ NOVO: Se não encontrou no cache, buscar da API Integra Comex
            if not di_cache:
                logger.info(f'DI {numero_di} não encontrada no cache. Buscando da API Integra Comex...')
                try:
                    from services.di_pdf_service import DiPdfService
                    pdf_service = DiPdfService()
                    
                    # Buscar processo_referencia do contexto se disponível
                    processo_ref = None
                    if context and isinstance(context, dict):
                        processo_ref = context.get('processo_referencia') or context.get('processo_atual')
                    
                    # Buscar da API
                    dados_completos = pdf_service.obter_dados_completos_di(
                        processo_referencia=processo_ref,
                        numero_di=numero_di
                    )
                    
                    if dados_completos.get('sucesso'):
                        # Dados já foram salvos no cache e banco SQL Server pelo obter_dados_completos_di
                        # Buscar novamente do cache para usar a mesma estrutura
                        di_cache = buscar_di_cache(numero_di)
                        if not di_cache:
                            # Se ainda não encontrou, usar dados da API diretamente
                            dados_di = dados_completos.get('dados_di', {})
                            if dados_di:
                                # Criar estrutura similar ao cache
                                dados_gerais = dados_di.get('dadosGerais', {}) if isinstance(dados_di, dict) else {}
                                dados_despacho = dados_di.get('dadosDespacho', {}) if isinstance(dados_di, dict) else {}
                                di_cache = {
                                    'numero_di': numero_di,
                                    'situacao_di': dados_gerais.get('situacaoDI', '') if isinstance(dados_gerais, dict) else '',
                                    'canal_selecao_parametrizada': dados_despacho.get('canalSelecaoParametrizada', '') if isinstance(dados_despacho, dict) else '',
                                    'data_hora_desembaraco': dados_despacho.get('dataHoraDesembaraco', '') if isinstance(dados_despacho, dict) else '',
                                    'data_hora_registro': dados_despacho.get('dataHoraRegistro', '') if isinstance(dados_despacho, dict) else '',
                                    'situacao_entrega_carga': dados_gerais.get('situacaoEntregaCarga', '') if isinstance(dados_gerais, dict) else '',
                                }
                    else:
                        return {
                            'sucesso': False,
                            'erro': 'DI_NAO_ENCONTRADA_API',
                            'resposta': f'⚠️ **DI {numero_di} não encontrada no cache nem na API.**\n\n💡 **Dica:** Verifique se o número da DI está correto.'
                        }
                except Exception as e:
                    logger.warning(f'Erro ao buscar DI da API: {e}')
                    return {
                        'sucesso': False,
                        'erro': 'DI_NAO_ENCONTRADA',
                        'resposta': f'⚠️ **DI {numero_di} não encontrada no cache.**\n\n💡 **Dica:** Consulte a DI primeiro antes de obter os dados.'
                    }
            
            if not di_cache:
                return {
                    'sucesso': False,
                    'erro': 'DI_NAO_ENCONTRADA',
                    'resposta': f'⚠️ **DI {numero_di} não encontrada no cache.**\n\n💡 **Dica:** Consulte a DI primeiro antes de obter os dados.'
                }
            
            situacao = di_cache.get('situacao_di', '')
            canal = di_cache.get('canal_selecao_parametrizada', '')
            data_desembaraco = di_cache.get('data_hora_desembaraco', '')
            data_registro = di_cache.get('data_hora_registro', '')
            situacao_entrega = di_cache.get('situacao_entrega_carga', '')
            
            resposta = f"📄 **DI {numero_di}**\n\n"
            resposta += f"**Situação:** {situacao or 'N/A'}\n"
            
            if canal:
                resposta += f"**Canal:** {canal}\n"
            
            if data_desembaraco:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(data_desembaraco.replace('Z', '+00:00'))
                    resposta += f"**Data de Desembaraço:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                except:
                    resposta += f"**Data de Desembaraço:** {data_desembaraco}\n"
            
            if data_registro:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(data_registro.replace('Z', '+00:00'))
                    resposta += f"**Data de Registro:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                except:
                    resposta += f"**Data de Registro:** {data_registro}\n"
            
            if situacao_entrega:
                resposta += f"**Situação de Entrega:** {situacao_entrega}\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': di_cache
            }
        except Exception as e:
            logger.error(f'Erro ao obter dados da DI {numero_di}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar dados da DI: {str(e)}'
            }
    
    def _vincular_processo_di(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Vincula DI a um processo.
        
        ✅ IMPORTANTE: Cada processo deve ter apenas uma DI (relação 1:1).
        """
        numero_di = arguments.get('numero_di', '').strip()
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        if not numero_di:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Número da DI é obrigatório.'
            }
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = extract_processo_referencia(processo_ref)
        if not processo_completo:
            processo_completo = processo_ref
        
        try:
            from db_manager import atualizar_processo_di_cache, buscar_di_cache, vincular_documento_processo
            
            # Verificar se a DI existe no cache
            di_cache = buscar_di_cache(numero_di=numero_di)
            if not di_cache:
                return {
                    'sucesso': False,
                    'erro': 'DI_NAO_ENCONTRADO_CACHE',
                    'resposta': f"⚠️ **DI {numero_di} não encontrada no cache.**\n\n💡 **Dica:** É necessário consultar a DI primeiro antes de vincular a um processo."
                }
            
            # Vincular processo à DI
            vincular_documento_processo(processo_completo, 'DI', numero_di)
            
            # Atualizar também o cache da DI
            sucesso = atualizar_processo_di_cache(numero_di, processo_completo)
            
            if sucesso:
                resposta = f"✅ **Processo vinculado com sucesso!**\n\n"
                resposta += f"**DI:** {numero_di}\n"
                resposta += f"**Processo:** {processo_completo}\n\n"
                resposta += f"🎯 **DI vinculada ao processo!**"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'processo': processo_completo,
                    'di': numero_di
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'ERRO_VINCULACAO',
                    'resposta': f"❌ **Erro ao vincular processo {processo_completo} à DI {numero_di}.**"
                }
                
        except Exception as e:
            logger.error(f'Erro ao vincular processo à DI: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro interno ao vincular processo: {str(e)}'
            }
    
    def _obter_extrato_pdf_di(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Obtém extrato PDF da DI de um processo.
        
        ⚠️ ATENÇÃO: Esta função consulta a API Integra Comex (Serpro) que é BILHETADA.
        A consulta só será feita se a DI não estiver no cache.
        
        Args:
            processo_referencia: Número do processo (ex: VDM.0003/25) - opcional
            numero_di: Número da DI diretamente (ex: 2524635120) - opcional
        
        Returns:
            Dict com resultado:
            {
                'sucesso': bool,
                'resposta': str (mensagem formatada),
                'dados': dict (dados da DI se disponível),
                'pdf_link': str (link para download do PDF se gerado)
            }
        """
        processo_referencia = arguments.get('processo_referencia', '').strip() or None
        numero_di = arguments.get('numero_di', '').strip() or None
        
        # Validar que pelo menos um dos dois foi fornecido
        if not processo_referencia and not numero_di:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Referência de processo ou número da DI é obrigatório.'
            }
        
        try:
            from services.di_pdf_service import DiPdfService
            
            pdf_service = DiPdfService()
            
            # 1. Obter dados completos da DI
            dados_completos = pdf_service.obter_dados_completos_di(
                processo_referencia=processo_referencia,
                numero_di=numero_di
            )
            
            if not dados_completos.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': dados_completos.get('erro', 'Erro ao obter dados da DI'),
                    'resposta': dados_completos.get('resposta', 'Erro ao obter dados da DI')
                }
            
            numero_di_encontrado = dados_completos.get('numero')
            dados_di = dados_completos.get('dados_di', {})
            fonte = dados_completos.get('fonte', 'cache')
            
            # 2. Formatizar resposta com dados principais
            resposta = f"📄 **Extrato da DI {numero_di_encontrado}**\n\n"
            
            if isinstance(dados_di, dict):
                dados_gerais = dados_di.get('dadosGerais', {})
                dados_despacho = dados_di.get('dadosDespacho', {})
                
                # Situação da DI
                situacao = dados_gerais.get('situacaoDI', '')
                if situacao:
                    resposta += f"**Situação:** {situacao}\n"
                
                # Canal
                canal = dados_despacho.get('canalSelecaoParametrizada', '')
                if canal:
                    resposta += f"**Canal:** {canal}\n"
                
                # Data de desembaraço
                data_desembaraco = dados_despacho.get('dataHoraDesembaraco')
                if data_desembaraco:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(data_desembaraco.replace('Z', '+00:00'))
                        resposta += f"**Data de Desembaraço:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                    except:
                        resposta += f"**Data de Desembaraço:** {data_desembaraco}\n"
                
                # Data de registro
                data_registro = dados_despacho.get('dataHoraRegistro')
                if data_registro:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(data_registro.replace('Z', '+00:00'))
                        resposta += f"**Data de Registro:** {dt.strftime('%d/%m/%Y %H:%M')}\n"
                    except:
                        resposta += f"**Data de Registro:** {data_registro}\n"
                
                # Situação de entrega
                situacao_entrega = dados_gerais.get('situacaoEntregaCarga', '')
                if situacao_entrega:
                    resposta += f"**Situação de Entrega:** {situacao_entrega}\n"
            
            # 3. Informar sobre a fonte (CRÍTICO: avisar sobre consulta bilhetada)
            if fonte == 'api_bilhetada':
                resposta += f"\n\n⚠️ **ATENÇÃO:** Esta consulta utilizou a API Integra Comex **BILHETADA** (paga por consulta).\n\n💡 **Dica:** Para evitar custos desnecessários, os dados são armazenados em cache. Consultas subsequentes desta DI não gerarão novos custos."
            else:
                if fonte == 'api_bilhetada':
                    resposta += f"\n\n⚠️ **ATENÇÃO:** Esta consulta utilizou a API Integra Comex BILHETADA (paga por consulta)."
                else:
                    resposta += f"\n\n✅ **Fonte:** Cache local (sem custo - consulta anterior armazenada)"
            
            # 4. Tentar gerar PDF automaticamente (só se temos dados completos)
            resposta_pdf = ""
            pdf_link = None
            
            if dados_di:
                try:
                    # ✅ CORREÇÃO: Passar dados_di diretamente para evitar consulta duplicada
                    # Usar método interno que aceita dados_di já consultados
                    pdf_resultado = pdf_service._gerar_pdf_di_com_dados(
                        dados_di=dados_di,
                        numero_di=numero_di_encontrado,
                        processo_referencia=processo_referencia
                    )
                    
                    if pdf_resultado.get('sucesso'):
                        nome_arquivo = pdf_resultado.get('nome_arquivo')
                        caminho_arquivo = pdf_resultado.get('caminho_arquivo')
                        # A rota /api/download/<path:filename> aceita "downloads/nome.pdf" ou apenas "nome.pdf"
                        # Usar apenas o nome do arquivo (a rota já gerencia o diretório downloads)
                        pdf_link = f"/api/download/{nome_arquivo}"
                        resposta_pdf = f"\n\n📄 **PDF Gerado:** [Clique aqui para baixar o PDF]({pdf_link})"
                    else:
                        resposta_pdf = f"\n\n⚠️ **Nota:** Não foi possível gerar o PDF: {pdf_resultado.get('erro', 'Erro desconhecido')}"
                except Exception as e:
                    logger.warning(f'Erro ao gerar PDF (não crítico): {e}')
                    resposta_pdf = f"\n\n⚠️ **Nota:** Não foi possível gerar o PDF automaticamente."
            
            resposta += resposta_pdf
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': dados_di,
                'numero_di': numero_di_encontrado,
                'fonte': fonte,
                'pdf_link': pdf_link
            }
            
        except Exception as e:
            logger.error(f'Erro ao obter extrato PDF da DI: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao obter extrato PDF da DI: {str(e)}'
            }

    def _consultar_adicoes_di(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta as adições de uma DI (endpoint oficial Integra Comex).
        """
        processo_referencia = (arguments.get('processo_referencia') or '').strip() or None
        numero_di = (arguments.get('numero_di') or '').strip() or None
        max_paginas = arguments.get('max_paginas', 10)
        max_itens = arguments.get('max_itens', 500)
        modo = (arguments.get('modo') or 'detalhado').strip().lower()
        if modo not in ('resumo', 'detalhado'):
            modo = 'detalhado'
        
        if not numero_di and not processo_referencia:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Informe o número da DI ou o processo (ex: DMD.0079/25).'
            }

        try:
            from services.di_adicoes_service import DiAdicoesService
            from services.di_pdf_service import DiPdfService
            from services.di_adicoes_service import extrair_produto_de_adicao

            # ✅ Mesma regra do extrato DI: aceitar processo e resolver o numero_di no banco
            numero_di_resolvido = numero_di
            if not numero_di_resolvido and processo_referencia:
                pdf = DiPdfService()
                numero_di_resolvido = pdf.buscar_di_banco(processo_referencia=processo_referencia)
                if not numero_di_resolvido:
                    return {
                        'sucesso': False,
                        'erro': 'DI_NAO_ENCONTRADA',
                        'resposta': f'⚠️ Não encontrei DI vinculada ao processo **{processo_referencia}**.'
                    }
            svc = DiAdicoesService()
            result = svc.consultar_adicoes(
                numero_di_resolvido,
                max_paginas=int(max_paginas or 10),
                max_itens=int(max_itens or 500),
                usou_api_publica_antes=True,
            )

            if not result.sucesso:
                return {
                    'sucesso': False,
                    'erro': result.erro or 'ERRO_CONSULTA_ADICOES',
                    'resposta': f'❌ Erro ao consultar adições da DI {numero_di}: {result.erro or "erro desconhecido"}'
                }

            adicoes = result.adicoes or []
            produtos = [extrair_produto_de_adicao(a) for a in adicoes if isinstance(a, dict)]

            # Formatar resposta (best-effort: não assumimos schema fixo aqui)
            titulo_num = numero_di_resolvido or (numero_di or '')
            resposta = f"📦 **ADIÇÕES DA DI {titulo_num}**\n\n"
            if processo_referencia:
                resposta += f"Processo: **{processo_referencia}**\n"
            resposta += f"Total: **{len(adicoes)}** adição(ões)\n"
            resposta += f"Páginas consultadas: **{result.paginas_consultadas}**\n\n"
            if not adicoes:
                resposta += "✅ Nenhuma adição retornada pelo endpoint.\n"
            else:
                # ✅ Produto "completo" para UI: mostrar campos principais e, no modo detalhado, expandir mais
                limite = 10 if modo == 'detalhado' else 30
                for idx, p in enumerate(produtos[:limite], start=1):
                    if not isinstance(p, dict):
                        continue
                    num_ad = p.get('numero_adicao') or 'N/A'
                    desc_adicao = str(p.get('descricao') or '').strip()
                    desc_adicao_norm = desc_adicao.lower()
                    linha = f"• ({idx}) **Adição {num_ad}**"
                    if p.get('ncm'):
                        linha += f" | NCM: {p.get('ncm')}"
                    if p.get('quantidade') or p.get('unidade'):
                        linha += f" | Qtd: {p.get('quantidade') or 'N/A'} {p.get('unidade') or ''}".rstrip()
                    if p.get('peso_liquido'):
                        linha += f" | Peso líq: {p.get('peso_liquido')}"
                    if p.get('moeda') and (p.get('valor_unitario') or p.get('valor_total')):
                        if p.get('valor_unitario'):
                            linha += f" | VU: {p.get('moeda')} {p.get('valor_unitario')}"
                        if p.get('valor_total'):
                            linha += f" | VT: {p.get('moeda')} {p.get('valor_total')}"
                    if p.get('aplicacao'):
                        linha += f" | Aplicação: {str(p.get('aplicacao'))[:40]}"
                    if desc_adicao:
                        linha += f" | {desc_adicao[:140]}"
                    resposta += linha + "\n"
                    
                    if modo == 'detalhado':
                        # Mostrar também peso bruto (se existir) e um bloco com chaves relevantes detectadas
                        extras = []
                        if p.get('peso_bruto'):
                            extras.append(f"Peso br.: {p.get('peso_bruto')}")
                        if p.get('exportador_nome') or p.get('pais_aquisicao_codigo'):
                            extras.append(
                                f"Exportador: {p.get('exportador_nome') or 'N/A'}"
                                f" | País aquisição: {p.get('pais_aquisicao_codigo') or 'N/A'}"
                            )
                        if p.get('fabricante_nome') or p.get('pais_origem_codigo'):
                            extras.append(
                                f"Fabricante: {p.get('fabricante_nome') or 'N/A'}"
                                f" | País origem: {p.get('pais_origem_codigo') or 'N/A'}"
                            )
                        if p.get('incoterm') or p.get('moeda_condicao_venda'):
                            extras.append(
                                f"Incoterm: {p.get('incoterm') or 'N/A'}"
                                f" | Moeda (cond. venda): {p.get('moeda_condicao_venda') or 'N/A'}"
                            )
                        if extras:
                            resposta += f"    ↳ " + " | ".join(extras) + "\n"

                        # ✅ Mostrar itens (quando existirem) - é aqui que vem descrição/quantidade/unidade/valorUnitario
                        itens = p.get('itens') if isinstance(p.get('itens'), list) else []
                        # ✅ Evitar poluição visual: suprimir descrição do item se for idêntica à descrição da adição
                        # ✅ E deduplicar itens idênticos (mesmo qtd/und/vu/descrição)
                        itens_printed = 0
                        dedupe_counts = {}
                        dedupe_first = {}
                        for it in itens:
                            if not isinstance(it, dict):
                                continue
                            desc_it_norm = str(it.get('descricao_mercadoria') or '').strip().lower()
                            key = (
                                str(it.get('quantidade') or '').strip(),
                                str(it.get('unidade_medida') or '').strip(),
                                str(it.get('valor_unitario') or '').strip(),
                                desc_it_norm,
                            )
                            dedupe_counts[key] = dedupe_counts.get(key, 0) + 1
                            if key not in dedupe_first:
                                dedupe_first[key] = it

                        for key, it in dedupe_first.items():
                            if not isinstance(it, dict):
                                continue
                            desc_it = it.get('descricao_mercadoria') or ''
                            qtd_it = it.get('quantidade')
                            und_it = it.get('unidade_medida')
                            vu_it = it.get('valor_unitario')
                            seq_it = it.get('numero_sequencial_item')
                            rep = dedupe_counts.get(key, 1)

                            linha_it = "    • Item"
                            if seq_it is not None:
                                linha_it += f" {seq_it}"
                            if qtd_it or und_it:
                                linha_it += f" | Qtd: {qtd_it or 'N/A'} {und_it or ''}".rstrip()
                            if vu_it:
                                linha_it += f" | VU: {vu_it}"
                            # Só mostrar descrição do item se ela for diferente da descrição da adição
                            if desc_it and str(desc_it).strip().lower() != desc_adicao_norm:
                                linha_it += f" | {str(desc_it)[:160]}"
                            if rep and rep > 1:
                                linha_it += f"  (repetido x{rep})"
                            resposta += linha_it + "\n"
                            itens_printed += 1
                            if itens_printed >= 10:
                                break

                if len(produtos) > limite:
                    resposta += f"\n… (+{len(produtos) - limite} adição(ões))\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'numero_di': numero_di_resolvido or numero_di,
                    'processo_referencia': processo_referencia,
                    'adicoes': adicoes,
                    'produtos': produtos,
                    'paginas_consultadas': result.paginas_consultadas,
                    'next_link': result.next_link,
                    'modo': modo,
                }
            }
        except RuntimeError as e:
            # Ex.: DUPLICATA (consulta bilhetada recente)
            msg = str(e)
            return {
                'sucesso': False,
                'erro': msg,
                'resposta': f'⚠️ Não foi possível consultar adições da DI {numero_di or processo_referencia}: {msg}'
            }
        except Exception as e:
            logger.error(f'Erro ao consultar adições da DI {numero_di}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao consultar adições da DI: {str(e)}'
            }