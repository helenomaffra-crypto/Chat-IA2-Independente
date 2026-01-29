"""
Agente responsável por operações relacionadas a processos de importação.
"""
import logging
import re
import os
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from ..utils.extractors import extract_processo_referencia
from ..utils.validators import validate_processo_referencia
from ..utils.formatters import format_lista_processos

logger = logging.getLogger(__name__)

# ✅ PASSO 6 - FASE 2: Flag para controlar formatação com IA
# ✅ HÍBRIDO (12/01/2026): Por padrão False (usa string fallback na primeira resposta - rápido)
# JSON será usado apenas quando necessário (melhorar relatório, emails, etc)
# Para ativar formatação com IA por padrão, definir FORMATAR_RELATORIOS_COM_IA=true no .env
FORMATAR_RELATORIOS_COM_IA = os.getenv('FORMATAR_RELATORIOS_COM_IA', 'false').lower() == 'true'


class RelatorioFormatterService:
    """
    Serviço para formatar relatórios com IA.
    
    ✅ PASSO 6 - FASE 2: Formatação de relatórios usando IA.
    """
    
    @staticmethod
    def _gerar_meta_json_inline(tipo_relatorio: str, dados_json: Dict[str, Any]) -> str:
        """
        ✅ NOVO (12/01/2026): Gera JSON inline compacto para incluir no final da string do relatório.
        
        Formato: [REPORT_META:{"tipo":"...","id":"...","secoes":[...],"counts":{...},"created_at":"...","ttl_min":60}]
        Este JSON permite que a IA saiba o que está na tela sem precisar buscar no banco.
        Formato visível no final do texto para que a IA possa ler.
        
        ✅ MELHORIAS (12/01/2026):
        - created_at: Timestamp de quando o relatório foi gerado (ajuda a entender "quão fresco" é)
        - counts: Contagens por seção (ajuda respostas do tipo "tem 9 pendências")
        - ttl_min: Tempo de vida em minutos (ajuda a saber se precisa atualizar)
        
        Args:
            tipo_relatorio: Tipo do relatório (ex: "o_que_tem_hoje", "fechamento_dia")
            dados_json: JSON estruturado do relatório
        
        Returns:
            String com JSON inline no formato [REPORT_META:...] (visível no final do texto)
        """
        import json
        from datetime import datetime
        
        # Gerar ID único baseado em timestamp
        agora = datetime.now()
        relatorio_id = f"rel_{agora.strftime('%Y%m%d_%H%M%S')}"
        
        # ✅ NOVO: Timestamp ISO 8601 com timezone
        created_at = agora.strftime('%Y-%m-%dT%H:%M:%S%z')
        if not created_at.endswith('00'):
            # Se não tem timezone, adicionar -03:00 (Brasil)
            created_at = agora.strftime('%Y-%m-%dT%H:%M:%S-03:00')
        
        # ✅ Contagens por seção
        # Regra: se relatório foi filtrado/derivado, a fonte da verdade são as seções visíveis (evita counts "antigos").
        counts = {}
        resumo = dados_json.get("resumo", {})
        secoes = dados_json.get("secoes", {})
        
        # Mapear nomes de seções para contagens no resumo
        mapeamento_contagens = {
            "processos_chegando": "total_chegando",
            "processos_prontos": "total_prontos",
            "processos_em_dta": "total_em_dta",
            "pendencias": "total_pendencias",
            "duimps_analise": "total_duimps",
            "dis_analise": "total_dis",
            "eta_alterado": "total_eta_alterado",
            "alertas": "total_alertas"
        }
        
        if dados_json.get("filtrado"):
            # Contar apenas o que está presente em `secoes` (visível)
            try:
                for secao, secao_dados in (secoes or {}).items():
                    if isinstance(secao_dados, list):
                        counts[secao] = len(secao_dados)
                    elif isinstance(secao_dados, dict):
                        counts[secao] = len(secao_dados)
                    else:
                        # Tipos atípicos: contar como 1 se existir
                        counts[secao] = 1 if secao_dados is not None else 0
            except Exception:
                counts = {}
        else:
            # Preencher counts do resumo (preferível no relatório "cheio")
            for secao, chave_resumo in mapeamento_contagens.items():
                if chave_resumo in resumo:
                    counts[secao] = resumo[chave_resumo]
                elif secao in secoes:
                    # Fallback: contar itens da seção se não tiver no resumo
                    secao_dados = secoes[secao]
                    if isinstance(secao_dados, list):
                        counts[secao] = len(secao_dados)
                    elif isinstance(secao_dados, dict):
                        counts[secao] = len(secao_dados)
        
        # Construir metadados
        meta = {
            "tipo": tipo_relatorio,
            "id": relatorio_id,
            "data": dados_json.get("data", agora.strftime('%Y-%m-%d')),
            "created_at": created_at,  # ✅ NOVO: Timestamp de criação
            "ttl_min": 60,  # ✅ NOVO: Tempo de vida em minutos (padrão: 60 minutos)
            "secoes": list(secoes.keys()),
            "counts": counts,  # ✅ NOVO: Contagens por seção
        }
        
        # Adicionar categoria se aplicável
        if dados_json.get("categoria"):
            meta["categoria"] = dados_json["categoria"]
        
        # Adicionar flags de filtro se aplicável
        if dados_json.get("filtrado"):
            meta["filtrado"] = True
            meta["secoes_filtradas"] = dados_json.get("secoes_filtradas", [])
        
        # Formato compacto (sem espaços para economizar bytes)
        json_str = json.dumps(meta, separators=(',', ':'))
        return f'\n\n[REPORT_META:{json_str}]'
    
    @staticmethod
    def formatar_relatorio_com_ia(dados_json: Dict[str, Any], usar_ia: bool = True, instrucao_melhorar: Optional[str] = None) -> Optional[str]:
        """
        Formata relatório usando IA baseado em JSON estruturado.
        
        Args:
            dados_json: JSON estruturado do relatório (com tipo_relatorio, secoes, etc.)
            usar_ia: Se True, usa IA para formatar. Se False, retorna None (fallback)
            instrucao_melhorar: Instrução adicional para melhorar/refinar o relatório (opcional)
        
        Returns:
            String formatada pela IA ou None se erro/IA não disponível
        """
        if not usar_ia:
            return None
        
        try:
            from ai_service import get_ai_service
            import json
            
            ai_service = get_ai_service()
            if not ai_service.enabled:
                logger.debug('⚠️ IA não disponível para formatar relatório. Usando formatação manual.')
                return None
            
            tipo_relatorio = dados_json.get('tipo_relatorio', 'desconhecido')
            data = dados_json.get('data', '')
            secoes = dados_json.get('secoes', {})
            resumo = dados_json.get('resumo', {})
            
            # ✅ MELHORIA (10/01/2026): Calcular estatísticas do JSON para orientar a IA e logs
            total_secoes = len(secoes)
            total_itens = sum(len(v) if isinstance(v, list) else 1 if v else 0 for v in secoes.values())
            
            # Construir prompt para IA
            # ✅ NOVO: Se há instrução de melhorar, adicionar ao prompt
            instrucoes_extras = ""
            if instrucao_melhorar:
                # ✅ MELHORIA CRÍTICA (10/01/2026): Instrução mais explícita para evitar perda de dados
                instrucoes_extras = f"""

⚠️⚠️⚠️ INSTRUÇÃO ESPECIAL DE MELHORIA/REORGANIZAÇÃO:
{instrucao_melhorar}

🚨🚨🚨 REGRA ABSOLUTA - NÃO PERDER DADOS:
- Você pode REORGANIZAR a apresentação, mas DEVE MANTER 100% dos dados
- Você pode MELHORAR a hierarquia visual, mas NÃO pode omitir nenhuma informação
- Você pode REFORMULAR frases, mas NÃO pode resumir ou agrupar dados de forma que perca detalhes
- Para listas longas: mostre os primeiros COMPLETOS e, APENAS se necessário, mencione os demais com contagem, mas NÃO omita informações críticas de nenhum item
- Cada processo, pendência, DI, DUIMP, alerta, etc. DEVE aparecer no relatório reformatado
- Se um dado estava no JSON original, ele DEVE aparecer na sua resposta
⚠️⚠️⚠️"""
            
            if tipo_relatorio == 'o_que_tem_hoje':
                system_prompt = """Você é um assistente especializado em formatar relatórios de processos de importação de forma clara e natural.
Use emojis apropriados, organize informações por seções e humanize a linguagem sem perder informações importantes.
Formate datas em português (DD/MM/YYYY) e seja objetivo mas conversacional.
IMPORTANTE: Use HTML inline com cores para destacar processos (ex: <span style="color: #0066cc; font-weight: bold;">ALH.0001/25</span>).
O frontend suporta HTML inline, então você pode usar tags <span> com estilos CSS diretamente no markdown."""
                
                # ✅ MELHORIA CRÍTICA (10/01/2026): Prompt mais explícito sobre manter TODOS os dados
                prompt_base = f"""Formate o seguinte relatório "O QUE TEMOS PRA HOJE" de forma natural e conversacional:

Data: {data}

🚨🚨🚨 CRITICAL - DADOS COMPLETOS OBRIGATÓRIOS:
Este relatório tem {total_secoes} seções com aproximadamente {total_itens} itens no total.
Você DEVE incluir TODAS as informações de TODAS as seções abaixo.
NÃO resuma demais. NÃO omita dados importantes. NÃO agrupe informações de forma que perca detalhes.

Seções (JSON completo - USE TODAS):
{json.dumps(secoes, indent=2, ensure_ascii=False)}

Resumo (totais):
{json.dumps(resumo, indent=2, ensure_ascii=False)}

📋 INSTRUÇÕES CRÍTICAS DE FORMATAÇÃO:
1. ⚠️⚠️⚠️ INCLUA TODAS as informações de TODAS as seções - não resuma ou omita dados
2. Para cada seção do JSON, você DEVE incluir todos os itens dessa seção no relatório formatado
3. Para listas com muitos itens:
   - Mostre os primeiros itens COMPLETOS (com todos os detalhes: processo, categoria, datas, situações, etc.)
   - Para os demais, você pode mencionar de forma mais concisa, MAS deve incluir pelo menos: número do processo, categoria, e situação principal
   - NUNCA omita completamente um item - sempre mencione-o, mesmo que resumidamente
4. Use emojis apropriados (📅, 🚢, ✅, ⚠️, 🔔, etc.)
5. Organize por seções claras e bem definidas (uma seção por tipo de dado)
6. Humanize a linguagem (não seja robótico, mas seja objetivo)
7. Formate datas em português (DD/MM/YYYY)
8. Mantenha TODAS as informações importantes (processos, números, valores, datas, situações, pendências, alertas)
9. Use quebras de linha e formatação markdown para melhor legibilidade
10. Destaque números e totais de forma clara
11. Se uma seção estiver vazia, mencione isso de forma breve
12. Para processos/DIs/DUIMPs: inclua número, situação, processo de referência, datas relevantes
13. Para pendências: inclua processo, tipo de pendência, descrição completa
14. Para ETA alterado: inclua processo, dias de atraso, datas relevantes

🎨 DESTAQUE DE PROCESSOS COM CORES (OBRIGATÓRIO):
15. ⚠️⚠️⚠️ CRITICAL: SEMPRE destaque os processos (ex: ALH.0001/25, DMD.0001/26, GLT.0046/25, BND.0084/25) usando HTML inline com cores
16. Padrão de cores sugerido:
    - Processos gerais: <span style="color: #0066cc; font-weight: bold;">PROCESSO.XXXX/YY</span> (azul)
    - Processos críticos/pendências: <span style="color: #dc3545; font-weight: bold;">PROCESSO.XXXX/YY</span> (vermelho)
    - Processos prontos: <span style="color: #28a745; font-weight: bold;">PROCESSO.XXXX/YY</span> (verde)
    - Processos em análise: <span style="color: #ffc107; font-weight: bold;">PROCESSO.XXXX/YY</span> (amarelo/laranja)
17. Formato padrão para processos: <span style="color: #0066cc; font-weight: bold;">XXX.XXXX/YY</span> onde XXX é a categoria (ALH, DMD, GLT, BND, NTM, etc.)
18. TODOS os processos mencionados no relatório DEVEM ser destacados desta forma
19. O padrão de processo é: CATEGORIA.NUMERO/ANO (ex: ALH.0001/25, DMD.0001/26, GLT.0046/25)
20. Use cores consistentes: mesma categoria = mesma cor (ou use azul padrão para todos se preferir simplicidade)

📊 EXEMPLO DE COMO TRATAR LISTAS LONGAS (NÃO OMITIR):
Se você tem 10 processos chegando hoje:
- Mostre os primeiros 3-5 COMPLETOS (processo, categoria, porto, ETA, situação, etc.)
- Para os demais 5-7, mencione: "E mais 5 processos: [lista dos números/categorias principais]"
- NÃO simplesmente diga "e mais 5 processos" sem mencionar quais são
- Cada processo DEVE ser identificado de alguma forma no relatório

{instrucoes_extras}
"""
                
                prompt = prompt_base
            
            elif tipo_relatorio == 'fechamento_dia':
                system_prompt = """Você é um assistente especializado em formatar relatórios de fechamento de dia de processos de importação.
Seja conciso, objetivo e use formatação clara com emojis apropriados.
IMPORTANTE: Use HTML inline com cores para destacar processos (ex: <span style="color: #0066cc; font-weight: bold;">ALH.0001/25</span>).
O frontend suporta HTML inline, então você pode usar tags <span> com estilos CSS diretamente no markdown."""
                
                # ✅ MELHORIA CRÍTICA (10/01/2026): Prompt mais explícito para fechamento_dia também
                prompt_fechamento = f"""Formate o seguinte relatório "FECHAMENTO DO DIA" de forma concisa e clara:

Data: {data}
Categoria: {dados_json.get('categoria', 'Todas')}

🚨🚨🚨 CRITICAL - DADOS COMPLETOS OBRIGATÓRIOS:
Este relatório tem {total_secoes} seções com aproximadamente {total_itens} itens no total.
Você DEVE incluir TODAS as informações de TODAS as seções abaixo.
NÃO resuma demais. NÃO omita dados importantes. NÃO agrupe informações de forma que perca detalhes.

Seções (JSON completo - USE TODAS):
{json.dumps(secoes, indent=2, ensure_ascii=False)}

Resumo (totais):
{json.dumps(resumo, indent=2, ensure_ascii=False)}

📋 INSTRUÇÕES CRÍTICAS DE FORMATAÇÃO:
1. ⚠️⚠️⚠️ INCLUA TODAS as informações de TODAS as seções - não resuma ou omita dados
2. Para cada seção do JSON, você DEVE incluir todos os itens dessa seção no relatório formatado
3. Use emojis apropriados (📅, ✅, 📊, etc.)
4. Seja conciso mas informativo (inclua todos os dados, mas de forma organizada)
5. Formate datas em português (DD/MM/YYYY)
6. Mantenha TODAS as informações importantes (processos, números, valores, datas, situações)
7. Use formatação markdown para melhor legibilidade
8. Para listas com muitos itens:
   - Mostre os primeiros itens COMPLETOS (com todos os detalhes)
   - Para os demais, mencione de forma concisa, MAS inclua pelo menos: número do processo, categoria, e situação
   - NUNCA omita completamente um item
9. Se uma seção estiver vazia, mencione isso de forma breve

🎨 DESTAQUE DE PROCESSOS COM CORES (OBRIGATÓRIO):
10. ⚠️⚠️⚠️ CRITICAL: SEMPRE destaque os processos (ex: ALH.0001/25, DMD.0001/26, GLT.0046/25, BND.0084/25) usando HTML inline com cores
11. Padrão de cores sugerido:
    - Processos gerais: <span style="color: #0066cc; font-weight: bold;">PROCESSO.XXXX/YY</span> (azul)
    - Processos críticos/pendências: <span style="color: #dc3545; font-weight: bold;">PROCESSO.XXXX/YY</span> (vermelho)
    - Processos prontos: <span style="color: #28a745; font-weight: bold;">PROCESSO.XXXX/YY</span> (verde)
    - Processos em análise: <span style="color: #ffc107; font-weight: bold;">PROCESSO.XXXX/YY</span> (amarelo/laranja)
12. Formato padrão para processos: <span style="color: #0066cc; font-weight: bold;">XXX.XXXX/YY</span> onde XXX é a categoria (ALH, DMD, GLT, BND, NTM, etc.)
13. TODOS os processos mencionados no relatório DEVEM ser destacados desta forma
14. O padrão de processo é: CATEGORIA.NUMERO/ANO (ex: ALH.0001/25, DMD.0001/26, GLT.0046/25)
15. Use cores consistentes: mesma categoria = mesma cor (ou use azul padrão para todos se preferir simplicidade)
{instrucoes_extras}
"""
                
                prompt = prompt_fechamento
            else:
                logger.warning(f'⚠️ Tipo de relatório desconhecido: {tipo_relatorio}. Usando formatação manual.')
                return None
            
            # ✅ MELHORIA (10/01/2026): Log detalhado do que está sendo passado para a IA
            tamanho_json = len(json.dumps(secoes, ensure_ascii=False))
            tamanho_prompt = len(prompt)
            logger.info(f'🤖 Formatando relatório {tipo_relatorio} com IA...')
            logger.info(f'   📊 Estatísticas: Seções={total_secoes}, Itens~={total_itens}, JSON={tamanho_json} chars, Prompt={tamanho_prompt} chars')
            logger.info(f'   📋 Instruções extras: {len(instrucoes_extras)} chars' if instrucoes_extras else '   📋 Sem instruções extras')
            
            # ✅ DEBUG: Logar exemplo de seções para verificar estrutura
            if secoes:
                logger.debug(f'   🔍 Exemplo de seções disponíveis: {list(secoes.keys())[:5]}')
                for secao_nome, secao_dados in list(secoes.items())[:3]:
                    if isinstance(secao_dados, list):
                        logger.debug(f'      - {secao_nome}: {len(secao_dados)} itens')
                        if secao_dados:
                            logger.debug(f'        Exemplo item: {str(secao_dados[0])[:100]}...')
                    else:
                        logger.debug(f'      - {secao_nome}: {type(secao_dados).__name__}')
            
            # ✅ CORREÇÃO CRÍTICA: Usar modelo tradicional (gpt-4o ou gpt-4o-mini) para formatação
            # Modelos com reasoning (como gpt-5.1, o1, o3) usam tokens de reasoning e deixam content vazio
            # Para formatação de texto, precisamos de conteúdo direto, não reasoning
            modelo_formatacao = os.getenv('OPENAI_MODEL_DEFAULT', 'gpt-4o-mini')
            if 'gpt-5' in modelo_formatacao.lower() or 'o1' in modelo_formatacao.lower() or 'o3' in modelo_formatacao.lower() or 'reasoning' in modelo_formatacao.lower():
                # Modelos com reasoning não são adequados para formatação - usar fallback tradicional
                logger.warning(f'⚠️ Modelo padrão {modelo_formatacao} tem reasoning e não é adequado para formatação. Usando gpt-4o-mini para formatação.')
                modelo_formatacao = 'gpt-4o-mini'
            
            resultado_ia = ai_service._call_llm_api(
                prompt=prompt,
                system_prompt=system_prompt,
                tools=None,  # Sem tools = sem tool calls possíveis
                tool_choice=None,  # None = usar comportamento padrão (sem tools = sem tool calls)
                model=modelo_formatacao,  # ✅ Usar modelo tradicional (gpt-4o-mini) para formatação
                temperature=0.7  # Um pouco mais criativo para formatação
            )
            
            # ✅ MELHORIA: Tratamento mais robusto do resultado com logs detalhados
            if resultado_ia is None:
                logger.warning('⚠️ IA retornou None. Possíveis causas: API retornou vazio, erro na chamada, ou modelo não respondeu. Usando formatação manual.')
                return None
            elif isinstance(resultado_ia, dict):
                # Se retornou dict, pode ser que tenha tool_calls (inesperado) ou content
                logger.debug(f'🔍 IA retornou dict: keys={list(resultado_ia.keys())}')
                if 'content' in resultado_ia and resultado_ia['content']:
                    logger.info('ℹ️ IA retornou dict com content. Extraindo conteúdo...')
                    conteudo = resultado_ia['content']
                    if isinstance(conteudo, str) and conteudo.strip():
                        logger.info(f'✅ Relatório formatado com IA (tamanho: {len(conteudo)} caracteres)')
                        return conteudo.strip()
                    else:
                        logger.warning(f'⚠️ Content extraído é inválido: tipo={type(conteudo)}, vazio={not conteudo if isinstance(conteudo, str) else "N/A"}. Usando formatação manual.')
                if 'tool_calls' in resultado_ia:
                    logger.warning(f'⚠️ IA retornou tool_calls inesperadas mesmo sem tools. Tool calls: {resultado_ia.get("tool_calls", [])}. Usando formatação manual.')
                logger.warning(f'⚠️ IA retornou dict inválido sem content útil. Dict: {str(resultado_ia)[:500]}. Usando formatação manual.')
                return None
            elif isinstance(resultado_ia, str):
                if resultado_ia.strip():
                    logger.info(f'✅ Relatório formatado com IA (tamanho: {len(resultado_ia)} caracteres)')
                    # ✅ NOVO (12/01/2026): Adicionar JSON inline antes de retornar
                    resultado_com_meta = resultado_ia.strip() + RelatorioFormatterService._gerar_meta_json_inline(
                        dados_json.get('tipo_relatorio', 'desconhecido'), 
                        dados_json
                    )
                    return resultado_com_meta
                else:
                    logger.warning('⚠️ IA retornou string vazia (após strip). Usando formatação manual.')
                    return None
            else:
                logger.warning(f'⚠️ IA retornou tipo inesperado: {type(resultado_ia)}. Valor: {str(resultado_ia)[:500]}. Usando formatação manual.')
                return None
                
        except Exception as e:
            logger.error(f'❌ Erro ao formatar relatório com IA: {e}', exc_info=True)
            return None
    
    @staticmethod
    def formatar_relatorio_fallback_simples(dados_json: Dict[str, Any]) -> str:
        """
        Formata relatório usando fallback detalhado (mesmo nível da formatação original).
        Gera uma resposta completa e rica do JSON estruturado, com agrupamento por categoria,
        classificação de atraso, e todos os detalhes.
        
        ✅ HÍBRIDO (12/01/2026): Restaurado nível de detalhe completo da formatação original.
        Mantém JSON disponível para melhorias quando necessário.
        
        Args:
            dados_json: JSON estruturado do relatório
        
        Returns:
            String formatada com todos os detalhes (agrupamento, classificação, etc.)
        """
        from datetime import datetime, date
        
        try:
            # ✅ Normalizar JSON antes de formatar (melhora consistência em filtros/follow-ups)
            # (Best-effort: não pode quebrar a formatação se vier algo inesperado.)
            try:
                from services.report_normalization_service import normalize_report_json
                dados_json = normalize_report_json(dados_json)
            except Exception as e:
                logger.debug(f"⚠️ Erro ao normalizar dados_json antes da formatação: {e}")

            tipo_relatorio = dados_json.get('tipo_relatorio', 'desconhecido')
            data = dados_json.get('data', '')
            categoria = dados_json.get('categoria')
            secoes = dados_json.get('secoes', {})
            resumo = dados_json.get('resumo', {})
            apenas_pendencias = dados_json.get('apenas_pendencias', False)

            # ✅ NOVO (19/01/2026): Formatação compacta para relatórios de chegadas (ETA)
            # Usado por "o que tem pra chegar essa semana?" e por filtros ("filtra só os BGR").
            if tipo_relatorio == 'processos_chegando':
                periodo = (resumo or {}).get('periodo') or (dados_json.get('filtros', {}) or {}).get('periodo') or ''
                titulo = "Processos que chegam"
                if periodo:
                    titulo += f" {periodo}"
                if categoria:
                    resposta = f"🚢 **{titulo} - {categoria.upper()}**\n\n"
                else:
                    resposta = f"🚢 **{titulo}**\n\n"

                processos = (secoes or {}).get('processos_chegando') or []
                resposta += f"Total: **{len(processos)}** processo(s)\n\n"

                # Render 1 linha por processo (estilo “rico e enxuto”)
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '') or 'N/A'

                    eta_info = proc.get('eta', {}) or {}
                    shipsgo = proc.get('shipsgo', {}) or {}
                    eta_raw = shipsgo.get('shipsgo_eta') or eta_info.get('eta_iso')

                    eta_txt = None
                    if eta_raw:
                        try:
                            import re
                            eta_clean = str(eta_raw).replace('Z', '')
                            eta_clean = re.sub(r'[+-]\\d{2}:\\d{2}$', '', eta_clean)
                            if 'T' in eta_clean:
                                dt_eta = datetime.fromisoformat(eta_clean)
                            elif len(eta_clean) == 10 and '-' in eta_clean:
                                dt_eta = datetime.fromisoformat(eta_clean + 'T00:00:00')
                            else:
                                dt_eta = None
                            if dt_eta:
                                eta_txt = dt_eta.strftime('%d/%m/%Y %H:%M')
                            else:
                                eta_txt = str(eta_raw)
                        except Exception:
                            eta_txt = str(eta_raw)

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
                        partes.append(f"ETA {eta_txt}")
                    if porto_txt:
                        partes.append(porto_txt)
                    if navio:
                        partes.append(f"Navio {navio}")
                    if status:
                        partes.append(f"Status: {status}")
                    if ce_num:
                        partes.append(f"CE {ce_num}" + (f" ({ce_situ})" if ce_situ else ""))

                    resposta += " – ".join(partes) + "\n"

                # ✅ Anexar REPORT_META (para filtros/email)
                return resposta + RelatorioFormatterService._gerar_meta_json_inline('processos_chegando', dados_json)
            
            if tipo_relatorio == 'o_que_tem_hoje':
                hoje = datetime.now().strftime('%d/%m/%Y')
                
                # ✅ NOVO: Verificar se é relatório filtrado
                eh_filtrado = dados_json.get('filtrado', False)
                secoes_filtradas = dados_json.get('secoes_filtradas', [])
                
                logger.warning(f'🚨🚨🚨 [FORMATADOR] formatar_relatorio_fallback_simples chamado. eh_filtrado={eh_filtrado}, secoes_filtradas={secoes_filtradas}, tipo_relatorio={tipo_relatorio}')
                
                resposta = f"📅 **O QUE TEMOS PRA HOJE"
                if categoria:
                    resposta += f" - {categoria.upper()}"
                resposta += f" - {hoje}**\n\n"
                resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # ✅ NOVO: Se for filtrado, mostrar apenas as seções filtradas
                if eh_filtrado and secoes_filtradas:
                    logger.warning(f'🚨🚨🚨 [FORMATADOR] Relatório FILTRADO detectado. Seções filtradas: {secoes_filtradas}')

                    # ✅ CORREÇÃO (28/01/2026): Quando o filtro é por categoria, NÃO retornar cedo
                    # em "dis_analise"/"alertas"/etc. Deve mostrar TODAS as seções filtradas com conteúdo.
                    categoria_filtro = dados_json.get('categoria_filtro')
                    if categoria_filtro:
                        logger.warning(
                            f'🚨🚨🚨 [FORMATADOR] Filtro por categoria {categoria_filtro} detectado (modo multi-seções).'
                        )

                        # Ordem desejada (similar ao relatório cheio)
                        ordem = [
                            'processos_chegando',
                            'processos_prontos',
                            'processos_em_dta',
                            'pendencias',
                            'dis_analise',
                            'duimps_analise',
                            'eta_alterado',
                            'alertas',
                        ]
                        secoes_disponiveis = [s for s in ordem if s in (secoes or {})]
                        if not secoes_disponiveis:
                            # Nada para mostrar, mas manter meta
                            resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            resposta += f"📊 **RESUMO:** 0 itens da categoria {str(categoria_filtro).upper()}\n"
                            resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                            return resposta

                        for secao_nome in secoes_disponiveis:
                            secao_dados = (secoes or {}).get(secao_nome)
                            if not secao_dados:
                                continue

                            # Processos chegando
                            if secao_nome == 'processos_chegando':
                                processos_chegando = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"🚢 **CHEGANDO HOJE** ({len(processos_chegando)} processo(s))\n\n"
                                for proc in processos_chegando:
                                    if not isinstance(proc, dict):
                                        continue
                                    resposta += f"   • **{proc.get('processo_referencia', 'N/A')}**"
                                    if proc.get('porto_nome'):
                                        resposta += f" - Porto: {proc['porto_nome']}"
                                    if proc.get('eta_iso'):
                                        resposta += f" - ETA: {proc.get('eta_iso')}"
                                    if proc.get('situacao_ce'):
                                        resposta += f" - Status: {proc.get('situacao_ce')}"
                                    resposta += "\n"
                                resposta += "\n"

                            # Prontos para registro (versão enxuta)
                            elif secao_nome == 'processos_prontos':
                                processos_prontos = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"✅ **PRONTOS PARA REGISTRO** ({len(processos_prontos)} processo(s))\n\n"
                                for proc in processos_prontos:
                                    if not isinstance(proc, dict):
                                        continue
                                    resposta += f"   • **{proc.get('processo_referencia', 'N/A')}**"
                                    if proc.get('data_destino_final'):
                                        try:
                                            data_chegada_raw = proc.get('data_destino_final')
                                            if isinstance(data_chegada_raw, str) and 'T' in data_chegada_raw:
                                                d = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                                resposta += f" - Chegou em {d.strftime('%d/%m/%Y')}"
                                            else:
                                                resposta += f" - Chegou em {data_chegada_raw}"
                                        except Exception:
                                            resposta += f" - Chegou em {proc.get('data_destino_final')}"
                                    if not proc.get('numero_di') and not proc.get('numero_duimp'):
                                        resposta += ", sem DI/DUIMP"
                                    if proc.get('tipo_documento'):
                                        resposta += f" - Tipo: {proc.get('tipo_documento')}"
                                    if proc.get('situacao_ce'):
                                        resposta += f" - Status CE: {proc.get('situacao_ce')}"
                                    resposta += "\n"
                                resposta += "\n"

                            # Em DTA (enxuto)
                            elif secao_nome == 'processos_em_dta':
                                em_dta = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"🚚 **PROCESSOS EM DTA** ({len(em_dta)} processo(s))\n\n"
                                for proc in em_dta:
                                    if not isinstance(proc, dict):
                                        continue
                                    resposta += f"   • **{proc.get('processo_referencia', 'N/A')}**\n"
                                resposta += "\n"

                            # Pendências
                            elif secao_nome == 'pendencias':
                                pendencias = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"⚠️ **PENDÊNCIAS ATIVAS** ({len(pendencias)} processo(s))\n\n"
                                for pend in pendencias:
                                    if not isinstance(pend, dict):
                                        continue
                                    resposta += f"   • **{pend.get('processo_referencia', 'N/A')}**"
                                    if pend.get('tipo_pendencia'):
                                        resposta += f" - {pend.get('tipo_pendencia')}"
                                    if pend.get('descricao_pendencia'):
                                        resposta += f" - {pend.get('descricao_pendencia')}"
                                    if pend.get('acao_sugerida'):
                                        resposta += f" - Ação: {pend.get('acao_sugerida')}"
                                    resposta += "\n"
                                resposta += "\n"

                            # DIs (registro/canal/status)
                            elif secao_nome == 'dis_analise':
                                dis_analise = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"📋 **DIs (REGISTRO/CANAL/STATUS)** ({len(dis_analise)} DI(s))\n"
                                resposta += "_Obs.: **Registro** = dataHoraRegistro; **Desembaraço** = dataHoraDesembaraco._\n\n"
                                for di in dis_analise:
                                    if not isinstance(di, dict):
                                        continue
                                    resposta += f"   • **{di.get('numero_di', di.get('numero', 'N/A'))}**"
                                    if di.get('processo_referencia'):
                                        resposta += f" - Processo: {di.get('processo_referencia')}"
                                    canal_di = di.get('canal_di') or di.get('canal')
                                    if canal_di:
                                        resposta += f" - Canal: {canal_di}"
                                    status_di = di.get('situacao_di') or di.get('situacao')
                                    if status_di:
                                        resposta += f" - Status DI: {str(status_di).replace('_', ' ').title()}"
                                    data_registro = di.get('data_registro') or di.get('data_hora_registro')
                                    if data_registro:
                                        resposta += f" - Registro: {data_registro}"
                                    data_desembaraco = di.get('data_desembaraco')
                                    if data_desembaraco:
                                        resposta += f" - Desembaraço: {data_desembaraco}"
                                    if di.get('tempo_analise'):
                                        resposta += f" (há {di.get('tempo_analise')})"
                                    resposta += "\n"
                                resposta += "\n"

                            # DUIMPs em análise
                            elif secao_nome == 'duimps_analise':
                                duimps_analise = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"📋 **DUIMPs EM ANÁLISE** ({len(duimps_analise)} DUIMP(s))\n\n"
                                for duimp in duimps_analise:
                                    if not isinstance(duimp, dict):
                                        continue
                                    resposta += f"   • **{duimp.get('numero_duimp', duimp.get('numero', 'N/A'))}**"
                                    if duimp.get('processo_referencia'):
                                        resposta += f" - Processo: {duimp.get('processo_referencia')}"
                                    status_duimp = duimp.get('situacao_duimp') or duimp.get('status')
                                    if status_duimp:
                                        resposta += f" - Status DUIMP: {str(status_duimp).replace('_', ' ').title()}"
                                    resposta += "\n"
                                resposta += "\n"

                            # ETA alterado
                            elif secao_nome == 'eta_alterado':
                                eta_alterado = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"🔄 **ETA ALTERADO** ({len(eta_alterado)} processo(s))\n\n"
                                for proc in eta_alterado:
                                    if not isinstance(proc, dict):
                                        continue
                                    resposta += f"   • **{proc.get('processo_referencia', 'N/A')}**"
                                    if proc.get('eta_iso'):
                                        resposta += f" - ETA: {proc.get('eta_iso')}"
                                    if proc.get('dias_atraso') is not None:
                                        da = proc.get('dias_atraso')
                                        try:
                                            da_int = int(da)
                                        except Exception:
                                            da_int = None
                                        if da_int is not None:
                                            if da_int > 0:
                                                resposta += f" (atraso de {da_int} dia(s))"
                                            elif da_int < 0:
                                                resposta += f" (adiantado em {abs(da_int)} dia(s))"
                                    resposta += "\n"
                                resposta += "\n"

                            # Alertas
                            elif secao_nome == 'alertas':
                                alertas = secao_dados if isinstance(secao_dados, list) else []
                                resposta += f"🔔 **ALERTAS RECENTES** ({len(alertas)} alerta(s))\n\n"
                                for alerta in alertas:
                                    if not isinstance(alerta, dict):
                                        continue
                                    titulo = alerta.get('titulo') or alerta.get('mensagem') or ''
                                    proc_ref = alerta.get('processo_referencia') or ''
                                    linha = "   • "
                                    if proc_ref:
                                        linha += f"**{proc_ref}**: "
                                    linha += titulo
                                    resposta += linha.strip() + "\n"
                                resposta += "\n"

                        # Resumo e REPORT_META
                        counts = {}
                        try:
                            for s in secoes_disponiveis:
                                v = (secoes or {}).get(s)
                                if isinstance(v, list):
                                    counts[s] = len(v)
                        except Exception:
                            counts = {}
                        resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        partes = []
                        if counts.get('processos_chegando'):
                            partes.append(f"{counts.get('processos_chegando')} chegando")
                        if counts.get('processos_prontos'):
                            partes.append(f"{counts.get('processos_prontos')} prontos")
                        if counts.get('processos_em_dta'):
                            partes.append(f"{counts.get('processos_em_dta')} em DTA")
                        if counts.get('pendencias') is not None:
                            partes.append(f"{counts.get('pendencias', 0)} pendências")
                        if counts.get('dis_analise') is not None:
                            partes.append(f"{counts.get('dis_analise', 0)} DIs")
                        if counts.get('duimps_analise') is not None:
                            partes.append(f"{counts.get('duimps_analise', 0)} DUIMPs")
                        if counts.get('eta_alterado') is not None:
                            partes.append(f"{counts.get('eta_alterado', 0)} ETA alterado")
                        resumo_txt = " | ".join(partes) if partes else "0 itens"
                        resposta += f"📊 **RESUMO:** {resumo_txt}\n"
                        resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                        return resposta.strip()

                    # Mostrar apenas as seções filtradas
                    if 'processos_prontos' in secoes_filtradas:
                        processos_prontos = secoes.get('processos_prontos', [])
                        resposta += f"✅ **PRONTOS PARA REGISTRO** ({len(processos_prontos)} processo(s))\n\n"
                        if not processos_prontos:
                            resposta += "   ℹ️ Nenhum processo pronto para registro.\n\n"
                        else:
                            # Separar processos por nível de atraso
                            processos_com_atraso_critico = []  # Mais de 7 dias
                            processos_com_atraso = []  # 3-7 dias
                            processos_recentes = []  # Menos de 3 dias
                            
                            hoje_date = date.today()
                            
                            for proc in processos_prontos:
                                # Calcular dias de atraso
                                dias_atraso = None
                                if proc.get('data_destino_final'):
                                    try:
                                        data_chegada_raw = proc['data_destino_final']
                                        if isinstance(data_chegada_raw, str):
                                            if 'T' in data_chegada_raw:
                                                data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                            else:
                                                data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                        else:
                                            data_chegada = data_chegada_raw
                                        
                                        dias_atraso = (hoje_date - data_chegada).days
                                        proc['dias_atraso'] = dias_atraso
                                    except:
                                        pass
                                
                                # Classificar por atraso
                                if dias_atraso and dias_atraso > 7:
                                    processos_com_atraso_critico.append(proc)
                                elif dias_atraso and dias_atraso >= 3:
                                    processos_com_atraso.append(proc)
                                else:
                                    processos_recentes.append(proc)
                            
                            # Mostrar processos com atraso crítico primeiro
                            if processos_com_atraso_critico:
                                resposta += f"   🚨 **ATRASO CRÍTICO** ({len(processos_com_atraso_critico)} processo(s) - mais de 7 dias):\n\n"
                                # Agrupar por categoria
                                processos_por_categoria = {}
                                for proc in processos_com_atraso_critico:
                                    proc_ref = proc.get('processo_referencia', '')
                                    cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                    if cat not in processos_por_categoria:
                                        processos_por_categoria[cat] = []
                                    processos_por_categoria[cat].append(proc)
                                
                                for cat in sorted(processos_por_categoria.keys()):
                                    processos_cat = processos_por_categoria[cat]
                                    resposta += f"      **{cat}** ({len(processos_cat)} processo(s)):\n"
                                    for proc in processos_cat:
                                        resposta += f"         • **{proc.get('processo_referencia', 'N/A')}**"
                                        if proc.get('data_destino_final'):
                                            try:
                                                data_chegada_raw = proc['data_destino_final']
                                                if isinstance(data_chegada_raw, str):
                                                    if 'T' in data_chegada_raw:
                                                        data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                                    else:
                                                        data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                                else:
                                                    data_chegada = data_chegada_raw
                                                resposta += f" - Chegou em {data_chegada.strftime('%d/%m/%Y')}"
                                                if proc.get('dias_atraso'):
                                                    resposta += f" ({proc['dias_atraso']} dia(s) de atraso)"
                                            except:
                                                resposta += f" - Chegou em {proc['data_destino_final']}"
                                        if not proc.get('numero_di') and not proc.get('numero_duimp'):
                                            resposta += ", sem DI/DUIMP"
                                        if proc.get('tipo_documento'):
                                            resposta += f" - Tipo: {proc['tipo_documento']}"
                                        if proc.get('situacao_ce'):
                                            resposta += f" - Status CE: {proc['situacao_ce']}"
                                        resposta += "\n"
                                    resposta += "\n"
                                resposta += "\n"
                            
                            # Mostrar processos com atraso moderado
                            if processos_com_atraso:
                                resposta += f"   ⚠️ **ATRASO MODERADO** ({len(processos_com_atraso)} processo(s) - 3 a 7 dias):\n\n"
                                # Agrupar por categoria
                                processos_por_categoria = {}
                                for proc in processos_com_atraso:
                                    proc_ref = proc.get('processo_referencia', '')
                                    cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                    if cat not in processos_por_categoria:
                                        processos_por_categoria[cat] = []
                                    processos_por_categoria[cat].append(proc)
                                
                                for cat in sorted(processos_por_categoria.keys()):
                                    processos_cat = processos_por_categoria[cat]
                                    resposta += f"      **{cat}** ({len(processos_cat)} processo(s)):\n"
                                    for proc in processos_cat:
                                        resposta += f"         • **{proc.get('processo_referencia', 'N/A')}**"
                                        if proc.get('data_destino_final'):
                                            try:
                                                data_chegada_raw = proc['data_destino_final']
                                                if isinstance(data_chegada_raw, str):
                                                    if 'T' in data_chegada_raw:
                                                        data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                                    else:
                                                        data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                                else:
                                                    data_chegada = data_chegada_raw
                                                resposta += f" - Chegou em {data_chegada.strftime('%d/%m/%Y')}"
                                                if proc.get('dias_atraso'):
                                                    resposta += f" ({proc['dias_atraso']} dia(s) de atraso)"
                                            except:
                                                resposta += f" - Chegou em {proc['data_destino_final']}"
                                        if not proc.get('numero_di') and not proc.get('numero_duimp'):
                                            resposta += ", sem DI/DUIMP"
                                        if proc.get('tipo_documento'):
                                            resposta += f" - Tipo: {proc['tipo_documento']}"
                                        if proc.get('situacao_ce'):
                                            resposta += f" - Status CE: {proc['situacao_ce']}"
                                        resposta += "\n"
                                    resposta += "\n"
                                resposta += "\n"
                            
                            # Mostrar processos recentes
                            if processos_recentes:
                                resposta += f"   ✅ **RECENTES** ({len(processos_recentes)} processo(s) - menos de 3 dias):\n\n"
                                # Agrupar por categoria
                                processos_por_categoria = {}
                                for proc in processos_recentes:
                                    proc_ref = proc.get('processo_referencia', '')
                                    cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                    if cat not in processos_por_categoria:
                                        processos_por_categoria[cat] = []
                                    processos_por_categoria[cat].append(proc)
                                
                                for cat in sorted(processos_por_categoria.keys()):
                                    processos_cat = processos_por_categoria[cat]
                                    resposta += f"      **{cat}** ({len(processos_cat)} processo(s)):\n"
                                    for proc in processos_cat:
                                        resposta += f"         • **{proc.get('processo_referencia', 'N/A')}**"
                                        if proc.get('data_destino_final'):
                                            try:
                                                data_chegada_raw = proc['data_destino_final']
                                                if isinstance(data_chegada_raw, str):
                                                    if 'T' in data_chegada_raw:
                                                        data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                                    else:
                                                        data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                                else:
                                                    data_chegada = data_chegada_raw
                                                resposta += f" - Chegou em {data_chegada.strftime('%d/%m/%Y')}"
                                            except:
                                                resposta += f" - Chegou em {proc['data_destino_final']}"
                                        if not proc.get('numero_di') and not proc.get('numero_duimp'):
                                            resposta += ", sem DI/DUIMP"
                                        if proc.get('tipo_documento'):
                                            resposta += f" - Tipo: {proc['tipo_documento']}"
                                        if proc.get('situacao_ce'):
                                            resposta += f" - Status CE: {proc['situacao_ce']}"
                                        resposta += "\n"
                                    resposta += "\n"
                            
                            # Resumo apenas dos prontos
                            resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            resposta += f"📊 **RESUMO:** {len(processos_prontos)} processo(s) pronto(s) para registro\n"
                            # ✅ NOVO (12/01/2026): Adicionar JSON inline antes de retornar
                            resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                            return resposta
                    
                    # ✅ NOVO: Tratar seção dis_analise quando filtrada
                    if 'dis_analise' in secoes_filtradas:
                            logger.warning(f'🚨🚨🚨 [FORMATADOR] Entrando no bloco dis_analise filtrado!')
                            dis_analise = secoes.get('dis_analise', [])
                            logger.warning(f'🚨🚨🚨 [FORMATADOR] dis_analise obtido: {len(dis_analise)} itens')
                            resposta += f"📋 **DIs (REGISTRO/CANAL/STATUS)** ({len(dis_analise)} DI(s))\n"
                            resposta += "_Obs.: **Registro** = dataHoraRegistro; **Desembaraço** = dataHoraDesembaraco._\n\n"
                            if not dis_analise:
                                resposta += "   ✅ Nenhuma DI em análise.\n\n"
                            else:
                                # Agrupar por categoria do processo
                                dis_por_categoria = {}
                                for di in dis_analise:
                                    proc_ref = di.get('processo_referencia', '')
                                    if proc_ref:
                                        cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                    else:
                                        cat = 'SEM PROCESSO'
                                    if cat not in dis_por_categoria:
                                        dis_por_categoria[cat] = []
                                    dis_por_categoria[cat].append(di)
                                
                                for cat in sorted(dis_por_categoria.keys()):
                                    dis_cat = dis_por_categoria[cat]
                                    resposta += f"   **{cat}** ({len(dis_cat)} DI(s)):\n"
                                    for di in dis_cat:
                                        resposta += f"      • **{di.get('numero_di', di.get('numero', 'N/A'))}**"
                                        if di.get('processo_referencia'):
                                            resposta += f" - Processo: {di['processo_referencia']}"
                                        if di.get('canal_di'):
                                            resposta += f" - Canal: {di['canal_di']}"
                                        elif di.get('canal'):
                                            resposta += f" - Canal: {di['canal']}"
                                        if di.get('situacao_di'):
                                            status_di_formatado = str(di['situacao_di']).replace('_', ' ').title()
                                            resposta += f" - Status DI: {status_di_formatado}"
                                        elif di.get('situacao'):
                                            status_di_formatado = str(di['situacao']).replace('_', ' ').title()
                                            resposta += f" - Status DI: {status_di_formatado}"
                                        # Mostrar data/hora de registro quando disponível
                                        data_registro = di.get('data_registro') or di.get('data_hora_registro')
                                        if data_registro:
                                            try:
                                                from datetime import datetime
                                                data_limpa = str(data_registro).replace('Z', '').replace('+00:00', '').strip()
                                                dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                                                if dt:
                                                    resposta += f" - Registro: {dt.strftime('%d/%m/%Y %H:%M')}"
                                                else:
                                                    resposta += f" - Registro: {data_registro}"
                                            except Exception:
                                                resposta += f" - Registro: {data_registro}"
                                        # Mostrar desembaraço quando disponível
                                        data_desembaraco = di.get('data_desembaraco')
                                        if data_desembaraco:
                                            try:
                                                from datetime import datetime
                                                data_limpa = str(data_desembaraco).replace('Z', '').replace('+00:00', '').strip()
                                                dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                                                if dt:
                                                    resposta += f" - Desembaraço: {dt.strftime('%d/%m/%Y %H:%M')}"
                                                else:
                                                    resposta += f" - Desembaraço: {data_desembaraco}"
                                            except Exception:
                                                resposta += f" - Desembaraço: {data_desembaraco}"
                                        if di.get('tempo_analise'):
                                            resposta += f" (há {di['tempo_analise']})"
                                        elif di.get('dias_em_analise'):
                                            resposta += f" (há {di['dias_em_analise']} dia(s))"
                                        resposta += "\n"
                                    resposta += "\n"
                            
                            # Resumo apenas das DIs
                            resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            resposta += f"📊 **RESUMO:** {len(dis_analise)} DI(s) listada(s)\n"
                            # ✅ NOVO (12/01/2026): Adicionar JSON inline antes de retornar
                            resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                            return resposta
                    
                    # ✅ NOVO: Tratar seção alertas quando filtrada
                    if 'alertas' in secoes_filtradas:
                        logger.warning(f'🚨🚨🚨 [FORMATADOR] Entrando no bloco alertas filtrado!')
                        alertas = secoes.get('alertas', [])
                        logger.warning(f'🚨🚨🚨 [FORMATADOR] alertas obtido: {len(alertas)} itens')
                        resposta += f"🔔 **ALERTAS RECENTES**\n\n"
                        if not alertas:
                            resposta += "   ✅ Nenhum alerta recente.\n\n"
                        else:
                            for alerta in alertas:
                                emoji = "⚠️" if "pendente" in alerta.get('tipo', '').lower() or "bloqueio" in alerta.get('tipo', '').lower() else "✅"
                                
                                titulo = alerta.get('titulo', alerta.get('mensagem', ''))
                                status_atual = alerta.get('status_atual')
                                processo_ref = alerta.get('processo_referencia', '')
                                
                                # Se é alerta de status e tem status atual, formatar melhor
                                if status_atual and ('status_ce' in alerta.get('tipo', '').lower() or 'status_di' in alerta.get('tipo', '').lower() or 'status_duimp' in alerta.get('tipo', '').lower()):
                                    if 'status_ce' in alerta.get('tipo', '').lower():
                                        resposta += f"   {emoji} 📦 {processo_ref}: CE - {status_atual}\n"
                                    elif 'status_di' in alerta.get('tipo', '').lower():
                                        resposta += f"   {emoji} 📋 {processo_ref}: DI - {status_atual}\n"
                                    elif 'status_duimp' in alerta.get('tipo', '').lower():
                                        resposta += f"   {emoji} 📄 {processo_ref}: DUIMP - {status_atual}\n"
                                else:
                                    # Formato genérico
                                    resposta += f"   {emoji} "
                                    if processo_ref:
                                        resposta += f"{processo_ref}: "
                                    if titulo:
                                        resposta += f"{titulo}"
                                    elif alerta.get('descricao'):
                                        resposta += f"{alerta.get('descricao')}"
                                    resposta += "\n"
                        
                        # Resumo apenas dos alertas
                        resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        resposta += f"📊 **RESUMO:** {len(alertas)} alerta(s) recente(s)\n"
                        # ✅ NOVO (12/01/2026): Adicionar JSON inline antes de retornar
                        resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                        return resposta
                    
                    # ✅ CORREÇÃO (14/01/2026): Se há filtro por categoria sem seção específica,
                    # processar TODAS as seções filtradas, não apenas as específicas
                    categoria_filtro = dados_json.get('categoria_filtro')
                    if categoria_filtro:
                        # Filtro por categoria - processar todas as seções que têm dados
                        logger.warning(f'🚨🚨🚨 [FORMATADOR] Filtro por categoria {categoria_filtro} detectado. Processando todas as seções filtradas.')
                        # Processar todas as seções disponíveis no JSON filtrado
                        secoes_disponiveis = list(secoes.keys())
                        logger.warning(f'🚨🚨🚨 [FORMATADOR] Seções disponíveis no JSON filtrado: {secoes_disponiveis}')
                        
                        # Processar cada seção que tem dados
                        for secao_nome in secoes_disponiveis:
                            if secao_nome in secoes and secoes[secao_nome]:
                                # Processar seção (lógica similar ao código não-filtrado abaixo)
                                if secao_nome == 'processos_chegando':
                                    processos_chegando = secoes.get('processos_chegando', [])
                                    if processos_chegando:
                                        resposta += f"🚢 **CHEGANDO HOJE** ({len(processos_chegando)} processo(s))\n\n"
                                        processos_por_categoria = {}
                                        for proc in processos_chegando:
                                            proc_ref = proc.get('processo_referencia', '')
                                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                            if cat not in processos_por_categoria:
                                                processos_por_categoria[cat] = []
                                            processos_por_categoria[cat].append(proc)
                                        
                                        for cat in sorted(processos_por_categoria.keys()):
                                            processos_cat = processos_por_categoria[cat]
                                            resposta += f"   **{cat}** ({len(processos_cat)} processo(s)):\n"
                                            for proc in processos_cat:
                                                resposta += f"      • **{proc.get('processo_referencia', 'N/A')}**"
                                                if proc.get('porto_nome'):
                                                    resposta += f" - Porto: {proc['porto_nome']}"
                                                if proc.get('eta_iso'):
                                                    try:
                                                        if 'T' in proc['eta_iso']:
                                                            data_eta = datetime.fromisoformat(proc['eta_iso'].replace('Z', '+00:00')).date()
                                                            resposta += f" - ETA: {data_eta.strftime('%d/%m/%Y')}"
                                                        else:
                                                            resposta += f" - ETA: {proc['eta_iso']}"
                                                    except:
                                                        resposta += f" - ETA: {proc['eta_iso']}"
                                                if proc.get('tem_apenas_eta'):
                                                    resposta += " (previsto)"
                                                elif proc.get('tem_chegada_confirmada'):
                                                    resposta += " (confirmado)"
                                                if proc.get('situacao_ce'):
                                                    resposta += f" - Status: {proc['situacao_ce']}"
                                                if proc.get('modal'):
                                                    resposta += f" - Modal: {proc['modal']}"
                                                resposta += "\n"
                                            resposta += "\n"
                                        resposta += "\n"
                                
                                elif secao_nome == 'pendencias':
                                    pendencias = secoes.get('pendencias', [])
                                    if pendencias:
                                        resposta += f"⚠️ **PENDÊNCIAS ATIVAS** ({len(pendencias)} processo(s))\n\n"
                                        pendencias_por_tipo = {}
                                        for pend in pendencias:
                                            tipo = pend.get('tipo_pendencia', 'OUTROS')
                                            if tipo not in pendencias_por_tipo:
                                                pendencias_por_tipo[tipo] = []
                                            pendencias_por_tipo[tipo].append(pend)
                                        
                                        ordem_tipos = ['ICMS', 'Frete', 'AFRMM', 'LPCO', 'Bloqueio CE']
                                        tipos_ordenados = sorted(
                                            pendencias_por_tipo.keys(),
                                            key=lambda x: (ordem_tipos.index(x) if x in ordem_tipos else 999, x)
                                        )
                                        
                                        for tipo in tipos_ordenados:
                                            pendencias_tipo = pendencias_por_tipo[tipo]
                                            resposta += f"   **{tipo}** ({len(pendencias_tipo)} processo(s)):\n"
                                            
                                            pendencias_por_categoria = {}
                                            for pend in pendencias_tipo:
                                                proc_ref = pend.get('processo_referencia', '')
                                                cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                                if cat not in pendencias_por_categoria:
                                                    pendencias_por_categoria[cat] = []
                                                pendencias_por_categoria[cat].append(pend)
                                            
                                            for cat in sorted(pendencias_por_categoria.keys()):
                                                pendencias_cat = pendencias_por_categoria[cat]
                                                resposta += f"      *{cat}* ({len(pendencias_cat)} processo(s)):\n"
                                                for pend in pendencias_cat:
                                                    resposta += f"         • **{pend.get('processo_referencia', 'N/A')}**"
                                                    if pend.get('descricao_pendencia'):
                                                        resposta += f" - {pend['descricao_pendencia']}"
                                                    if pend.get('tempo_pendente'):
                                                        resposta += f" (há {pend['tempo_pendente']})"
                                                    if pend.get('acao_sugerida'):
                                                        resposta += f" - Ação: {pend['acao_sugerida']}"
                                                    resposta += "\n"
                                            resposta += "\n"
                                        resposta += "\n"
                                
                                elif secao_nome == 'duimps_analise':
                                    duimps_analise = secoes.get('duimps_analise', [])
                                    if duimps_analise:
                                        resposta += f"📋 **DUIMPs EM ANÁLISE** ({len(duimps_analise)} DUIMP(s))\n\n"
                                        duimps_por_categoria = {}
                                        for duimp in duimps_analise:
                                            proc_ref = duimp.get('processo_referencia', '')
                                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                            if cat not in duimps_por_categoria:
                                                duimps_por_categoria[cat] = []
                                            duimps_por_categoria[cat].append(duimp)
                                        
                                        for cat in sorted(duimps_por_categoria.keys()):
                                            duimps_cat = duimps_por_categoria[cat]
                                            resposta += f"   **{cat}** ({len(duimps_cat)} DUIMP(s)):\n"
                                            for duimp in duimps_cat:
                                                resposta += f"      • **{duimp.get('numero_duimp', duimp.get('numero', 'N/A'))}**"
                                                if duimp.get('processo_referencia'):
                                                    resposta += f" - Processo: {duimp['processo_referencia']}"
                                                if duimp.get('situacao_duimp'):
                                                    status_duimp_formatado = str(duimp['situacao_duimp']).replace('_', ' ').title()
                                                    resposta += f" - Status DUIMP: {status_duimp_formatado}"
                                                if duimp.get('tempo_analise'):
                                                    resposta += f" (há {duimp['tempo_analise']})"
                                                elif duimp.get('dias_em_analise'):
                                                    resposta += f" (há {duimp['dias_em_analise']} dia(s))"
                                                resposta += "\n"
                                            resposta += "\n"
                                        resposta += "\n"
                                
                                elif secao_nome == 'eta_alterado':
                                    eta_alterado = secoes.get('eta_alterado', [])
                                    if eta_alterado:
                                        resposta += f"🔄 **ETA ALTERADO** ({len(eta_alterado)} processo(s))\n\n"
                                        # Separar por adiantado/atrasado
                                        processos_atrasados = []
                                        processos_adiantados = []
                                        
                                        for proc in eta_alterado:
                                            if proc.get('dias_atraso') and proc['dias_atraso'] > 0:
                                                processos_atrasados.append(proc)
                                            elif proc.get('dias_atraso') and proc['dias_atraso'] < 0:
                                                processos_adiantados.append(proc)
                                        
                                        if processos_atrasados:
                                            resposta += f"📅 **ATRASO** ({len(processos_atrasados)} processo(s)):\n\n"
                                            processos_por_categoria = {}
                                            for proc in processos_atrasados:
                                                proc_ref = proc.get('processo_referencia', '')
                                                cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                                if cat not in processos_por_categoria:
                                                    processos_por_categoria[cat] = []
                                                processos_por_categoria[cat].append(proc)
                                            
                                            for cat in sorted(processos_por_categoria.keys()):
                                                processos_cat = processos_por_categoria[cat]
                                                resposta += f"   **{cat}** ({len(processos_cat)} processo(s)):\n"
                                                for proc in processos_cat:
                                                    resposta += f"      • **{proc.get('processo_referencia', 'N/A')}**"
                                                    if proc.get('eta_iso'):
                                                        try:
                                                            if 'T' in proc['eta_iso']:
                                                                data_eta = datetime.fromisoformat(proc['eta_iso'].replace('Z', '+00:00')).date()
                                                                resposta += f" - ETA: {data_eta.strftime('%d/%m/%Y')}"
                                                            else:
                                                                resposta += f" - ETA: {proc['eta_iso']}"
                                                        except:
                                                            resposta += f" - ETA: {proc['eta_iso']}"
                                                    if proc.get('dias_atraso'):
                                                        resposta += f" (atraso de {proc['dias_atraso']} dia(s))"
                                                    resposta += "\n"
                                                resposta += "\n"
                                            resposta += "\n"
                                        
                                        if processos_adiantados:
                                            resposta += f"⚡ **ADIANTADO** ({len(processos_adiantados)} processo(s)):\n\n"
                                            processos_por_categoria = {}
                                            for proc in processos_adiantados:
                                                proc_ref = proc.get('processo_referencia', '')
                                                cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                                if cat not in processos_por_categoria:
                                                    processos_por_categoria[cat] = []
                                                processos_por_categoria[cat].append(proc)
                                            
                                            for cat in sorted(processos_por_categoria.keys()):
                                                processos_cat = processos_por_categoria[cat]
                                                resposta += f"   **{cat}** ({len(processos_cat)} processo(s)):\n"
                                                for proc in processos_cat:
                                                    resposta += f"      • **{proc.get('processo_referencia', 'N/A')}**"
                                                    if proc.get('eta_iso'):
                                                        try:
                                                            if 'T' in proc['eta_iso']:
                                                                data_eta = datetime.fromisoformat(proc['eta_iso'].replace('Z', '+00:00')).date()
                                                                resposta += f" - ETA: {data_eta.strftime('%d/%m/%Y')}"
                                                            else:
                                                                resposta += f" - ETA: {proc['eta_iso']}"
                                                        except:
                                                            resposta += f" - ETA: {proc['eta_iso']}"
                                                    if proc.get('dias_atraso'):
                                                        resposta += f" (adiantado em {abs(proc['dias_atraso'])} dia(s))"
                                                    resposta += "\n"
                                                resposta += "\n"
                                            resposta += "\n"
                        
                        # Adicionar resumo e JSON inline
                        if resposta.strip() and not resposta.strip().endswith('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'):
                            resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            # Contar total de processos em todas as seções
                            total_processos = sum(
                                len(secoes.get(secao, [])) if isinstance(secoes.get(secao, []), list) else 0
                                for secao in secoes_disponiveis
                            )
                            resposta += f"📊 **RESUMO:** {total_processos} processo(s) da categoria {categoria_filtro}\n"
                        
                        resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                        return resposta
                    
                    # Se outras seções filtradas, adicionar lógica similar aqui
                    # Por enquanto, retornar resposta vazia se não for processos_prontos, dis_analise ou alertas
                    # ✅ NOVO (12/01/2026): Adicionar JSON inline mesmo para resposta vazia
                    resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                    return resposta
                
                # Se apenas pendências, mostrar só isso
                if apenas_pendencias:
                    pendencias = secoes.get('pendencias', [])
                    resposta += f"⚠️ **PENDÊNCIAS ATIVAS** ({len(pendencias)} processo(s))\n\n"
                    if not pendencias:
                        resposta += "✅ Nenhuma pendência ativa hoje.\n\n"
                    else:
                        # Agrupar por tipo de pendência primeiro
                        pendencias_por_tipo = {}
                        for pend in pendencias:
                            tipo = pend.get('tipo_pendencia', 'OUTROS')
                            if tipo not in pendencias_por_tipo:
                                pendencias_por_tipo[tipo] = []
                            pendencias_por_tipo[tipo].append(pend)
                        
                        # Ordenar tipos
                        ordem_tipos = ['ICMS', 'Frete', 'AFRMM', 'LPCO', 'Bloqueio CE']
                        tipos_ordenados = sorted(
                            pendencias_por_tipo.keys(),
                            key=lambda x: (ordem_tipos.index(x) if x in ordem_tipos else 999, x)
                        )
                        
                        for tipo in tipos_ordenados:
                            pendencias_tipo = pendencias_por_tipo[tipo]
                            resposta += f"   **{tipo}** ({len(pendencias_tipo)} processo(s)):\n"
                            
                            # Agrupar por categoria dentro do tipo
                            pendencias_por_categoria = {}
                            for pend in pendencias_tipo:
                                proc_ref = pend.get('processo_referencia', '')
                                cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                                if cat not in pendencias_por_categoria:
                                    pendencias_por_categoria[cat] = []
                                pendencias_por_categoria[cat].append(pend)
                            
                            for cat in sorted(pendencias_por_categoria.keys()):
                                pendencias_cat = pendencias_por_categoria[cat]
                                resposta += f"      *{cat}* ({len(pendencias_cat)} processo(s)):\n"
                                for pend in pendencias_cat:
                                    resposta += f"         • **{pend.get('processo_referencia', 'N/A')}**"
                                    if pend.get('descricao_pendencia'):
                                        resposta += f" - {pend['descricao_pendencia']}"
                                    if pend.get('tempo_pendente'):
                                        resposta += f" (há {pend['tempo_pendente']})"
                                    if pend.get('acao_sugerida'):
                                        resposta += f" - Ação: {pend['acao_sugerida']}"
                                    resposta += "\n"
                            resposta += "\n"
                    
                    resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    resposta += f"📊 **RESUMO:** {len(pendencias)} pendência(s)\n"
                    # ✅ NOVO (12/01/2026): Adicionar JSON inline antes de retornar
                    resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                    return resposta
                
                # Processos chegando hoje - AGRUPADOS POR CATEGORIA
                processos_chegando = secoes.get('processos_chegando', [])
                resposta += f"🚢 **CHEGANDO HOJE** ({len(processos_chegando)} processo(s))\n\n"
                if not processos_chegando:
                    resposta += "   ℹ️ Nenhum processo chegando hoje.\n\n"
                else:
                    # Agrupar por categoria
                    processos_por_categoria = {}
                    for proc in processos_chegando:
                        proc_ref = proc.get('processo_referencia', '')
                        cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                        if cat not in processos_por_categoria:
                            processos_por_categoria[cat] = []
                        processos_por_categoria[cat].append(proc)
                    
                    # Ordenar categorias alfabeticamente
                    for cat in sorted(processos_por_categoria.keys()):
                        processos_cat = processos_por_categoria[cat]
                        resposta += f"   **{cat}** ({len(processos_cat)} processo(s)):\n"
                        for proc in processos_cat:
                            resposta += f"      • **{proc.get('processo_referencia', 'N/A')}**"
                            if proc.get('porto_nome'):
                                resposta += f" - Porto: {proc['porto_nome']}"
                            if proc.get('eta_iso'):
                                try:
                                    if 'T' in proc['eta_iso']:
                                        data_eta = datetime.fromisoformat(proc['eta_iso'].replace('Z', '+00:00')).date()
                                        resposta += f" - ETA: {data_eta.strftime('%d/%m/%Y')}"
                                    else:
                                        resposta += f" - ETA: {proc['eta_iso']}"
                                except:
                                    resposta += f" - ETA: {proc['eta_iso']}"
                            if proc.get('tem_apenas_eta'):
                                resposta += " (previsto)"
                            elif proc.get('tem_chegada_confirmada'):
                                resposta += " (confirmado)"
                            if proc.get('situacao_ce'):
                                resposta += f" - Status: {proc['situacao_ce']}"
                            if proc.get('modal'):
                                resposta += f" - Modal: {proc['modal']}"
                            resposta += "\n"
                        resposta += "\n"
                resposta += "\n"
                
                # Processos em DTA
                processos_em_dta = secoes.get('processos_em_dta', [])
                if processos_em_dta:
                    resposta += f"🚚 **PROCESSOS EM DTA** ({len(processos_em_dta)} processo(s))\n\n"
                    resposta += "   *Cargas em trânsito para outro recinto alfandegado*\n\n"
                    
                    # Agrupar por categoria
                    processos_por_categoria = {}
                    for proc in processos_em_dta:
                        proc_ref = proc.get('processo_referencia', '')
                        cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                        if cat not in processos_por_categoria:
                            processos_por_categoria[cat] = []
                        processos_por_categoria[cat].append(proc)
                    
                    for cat in sorted(processos_por_categoria.keys()):
                        processos_cat = processos_por_categoria[cat]
                        resposta += f"   **{cat}** ({len(processos_cat)} processo(s)):\n"
                        for proc in processos_cat:
                            resposta += f"      • **{proc.get('processo_referencia', 'N/A')}**"
                            if proc.get('numero_dta'):
                                resposta += f" - DTA: {proc['numero_dta']}"
                            if proc.get('data_destino_final'):
                                try:
                                    data_chegada_raw = proc['data_destino_final']
                                    if isinstance(data_chegada_raw, str):
                                        if 'T' in data_chegada_raw:
                                            data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                        else:
                                            data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                    else:
                                        data_chegada = data_chegada_raw
                                    resposta += f" - Chegou em {data_chegada.strftime('%d/%m/%Y')}"
                                except:
                                    resposta += f" - Chegou em {proc['data_destino_final']}"
                            if proc.get('situacao_ce'):
                                resposta += f" - Status CE: {proc['situacao_ce']}"
                            resposta += "\n"
                        resposta += "\n"
                    resposta += "\n"
                
                # Processos prontos para registro - AGRUPADOS POR CATEGORIA E COM ATRASO
                processos_prontos = secoes.get('processos_prontos', [])
                resposta += f"✅ **PRONTOS PARA REGISTRO** ({len(processos_prontos)} processo(s))\n\n"
                if not processos_prontos:
                    resposta += "   ℹ️ Nenhum processo pronto para registro.\n\n"
                else:
                    # Separar processos por nível de atraso
                    processos_com_atraso_critico = []  # Mais de 7 dias
                    processos_com_atraso = []  # 3-7 dias
                    processos_recentes = []  # Menos de 3 dias
                    
                    hoje_date = date.today()
                    
                    for proc in processos_prontos:
                        # Calcular dias de atraso
                        dias_atraso = None
                        if proc.get('data_destino_final'):
                            try:
                                data_chegada_raw = proc['data_destino_final']
                                if isinstance(data_chegada_raw, str):
                                    if 'T' in data_chegada_raw:
                                        data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                    else:
                                        data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                else:
                                    data_chegada = data_chegada_raw
                                
                                dias_atraso = (hoje_date - data_chegada).days
                                proc['dias_atraso'] = dias_atraso
                            except:
                                pass
                        
                        # Classificar por atraso
                        if dias_atraso and dias_atraso > 7:
                            processos_com_atraso_critico.append(proc)
                        elif dias_atraso and dias_atraso >= 3:
                            processos_com_atraso.append(proc)
                        else:
                            processos_recentes.append(proc)
                    
                    # Mostrar processos com atraso crítico primeiro
                    if processos_com_atraso_critico:
                        resposta += f"   🚨 **ATRASO CRÍTICO** ({len(processos_com_atraso_critico)} processo(s) - mais de 7 dias):\n\n"
                        # Agrupar por categoria
                        processos_por_categoria = {}
                        for proc in processos_com_atraso_critico:
                            proc_ref = proc.get('processo_referencia', '')
                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                            if cat not in processos_por_categoria:
                                processos_por_categoria[cat] = []
                            processos_por_categoria[cat].append(proc)
                        
                        for cat in sorted(processos_por_categoria.keys()):
                            processos_cat = processos_por_categoria[cat]
                            resposta += f"      **{cat}** ({len(processos_cat)} processo(s)):\n"
                            for proc in processos_cat:
                                resposta += f"         • **{proc.get('processo_referencia', 'N/A')}**"
                                if proc.get('data_destino_final'):
                                    try:
                                        data_chegada_raw = proc['data_destino_final']
                                        if isinstance(data_chegada_raw, str):
                                            if 'T' in data_chegada_raw:
                                                data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                            else:
                                                data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                        else:
                                            data_chegada = data_chegada_raw
                                        resposta += f" - Chegou em {data_chegada.strftime('%d/%m/%Y')}"
                                    except:
                                        resposta += f" - Chegou em {proc['data_destino_final']}"
                                if proc.get('dias_atraso'):
                                    resposta += f" ⚠️ **{proc['dias_atraso']} dia(s) de atraso**"
                                if proc.get('numero_duimp') and proc.get('numero_duimp').strip():
                                    situacao_duimp = proc.get('situacao_duimp', '')
                                    resposta += f" - DUIMP {proc['numero_duimp']} registrada"
                                    if situacao_duimp:
                                        situacao_formatada = situacao_duimp.replace('_', ' ').title()
                                        resposta += f" ({situacao_formatada})"
                                else:
                                    resposta += f", sem DI/DUIMP - Tipo: {proc.get('tipo_documento', 'DUIMP')}"
                                if proc.get('situacao_ce'):
                                    resposta += f" - Status CE: {proc['situacao_ce']}"
                                resposta += "\n"
                            resposta += "\n"
                        resposta += "\n"
                    
                    # Processos com atraso moderado (3-7 dias)
                    if processos_com_atraso:
                        resposta += f"   ⚠️ **ATRASO MODERADO** ({len(processos_com_atraso)} processo(s) - 3 a 7 dias):\n\n"
                        processos_por_categoria = {}
                        for proc in processos_com_atraso:
                            proc_ref = proc.get('processo_referencia', '')
                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                            if cat not in processos_por_categoria:
                                processos_por_categoria[cat] = []
                            processos_por_categoria[cat].append(proc)
                        
                        for cat in sorted(processos_por_categoria.keys()):
                            processos_cat = processos_por_categoria[cat]
                            resposta += f"      **{cat}** ({len(processos_cat)} processo(s)):\n"
                            for proc in processos_cat:
                                resposta += f"         • **{proc.get('processo_referencia', 'N/A')}**"
                                if proc.get('data_destino_final'):
                                    try:
                                        data_chegada_raw = proc['data_destino_final']
                                        if isinstance(data_chegada_raw, str):
                                            if 'T' in data_chegada_raw:
                                                data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                            else:
                                                data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                        else:
                                            data_chegada = data_chegada_raw
                                        resposta += f" - Chegou em {data_chegada.strftime('%d/%m/%Y')}"
                                    except:
                                        resposta += f" - Chegou em {proc['data_destino_final']}"
                                if proc.get('dias_atraso'):
                                    resposta += f" ({proc['dias_atraso']} dia(s) de atraso)"
                                if proc.get('numero_duimp') and proc.get('numero_duimp').strip():
                                    situacao_duimp = proc.get('situacao_duimp', '')
                                    resposta += f" - DUIMP {proc['numero_duimp']} registrada"
                                    if situacao_duimp:
                                        situacao_formatada = situacao_duimp.replace('_', ' ').title()
                                        resposta += f" ({situacao_formatada})"
                                else:
                                    resposta += f", sem DI/DUIMP - Tipo: {proc.get('tipo_documento', 'DUIMP')}"
                                if proc.get('situacao_ce'):
                                    resposta += f" - Status CE: {proc['situacao_ce']}"
                                resposta += "\n"
                            resposta += "\n"
                        resposta += "\n"
                    
                    # Processos recentes (menos de 3 dias)
                    if processos_recentes:
                        resposta += f"   ✅ **RECENTES** ({len(processos_recentes)} processo(s) - menos de 3 dias):\n\n"
                        processos_por_categoria = {}
                        for proc in processos_recentes:
                            proc_ref = proc.get('processo_referencia', '')
                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                            if cat not in processos_por_categoria:
                                processos_por_categoria[cat] = []
                            processos_por_categoria[cat].append(proc)
                        
                        for cat in sorted(processos_por_categoria.keys()):
                            processos_cat = processos_por_categoria[cat]
                            resposta += f"      **{cat}** ({len(processos_cat)} processo(s)):\n"
                            for proc in processos_cat:
                                resposta += f"         • **{proc.get('processo_referencia', 'N/A')}**"
                                if proc.get('data_destino_final'):
                                    try:
                                        data_chegada_raw = proc['data_destino_final']
                                        if isinstance(data_chegada_raw, str):
                                            if 'T' in data_chegada_raw:
                                                data_chegada = datetime.fromisoformat(data_chegada_raw.replace('Z', '+00:00')).date()
                                            else:
                                                data_chegada = datetime.strptime(data_chegada_raw, '%Y-%m-%d').date()
                                        else:
                                            data_chegada = data_chegada_raw
                                        resposta += f" - Chegou em {data_chegada.strftime('%d/%m/%Y')}"
                                    except:
                                        resposta += f" - Chegou em {proc['data_destino_final']}"
                                if proc.get('numero_duimp') and proc.get('numero_duimp').strip():
                                    situacao_duimp = proc.get('situacao_duimp', '')
                                    resposta += f" - DUIMP {proc['numero_duimp']} registrada"
                                    if situacao_duimp:
                                        situacao_formatada = situacao_duimp.replace('_', ' ').title()
                                        resposta += f" ({situacao_formatada})"
                                else:
                                    resposta += f", sem DI/DUIMP - Tipo: {proc.get('tipo_documento', 'DUIMP')}"
                                if proc.get('situacao_ce'):
                                    resposta += f" - Status CE: {proc['situacao_ce']}"
                                resposta += "\n"
                            resposta += "\n"
                resposta += "\n"
                
                # Pendências ativas - AGRUPADAS POR TIPO E CATEGORIA
                pendencias = secoes.get('pendencias', [])
                resposta += f"⚠️ **PENDÊNCIAS ATIVAS** ({len(pendencias)} processo(s))\n\n"
                if not pendencias:
                    resposta += "   ✅ Nenhuma pendência ativa.\n\n"
                else:
                    # Agrupar por tipo de pendência primeiro
                    pendencias_por_tipo = {}
                    for pend in pendencias:
                        tipo = pend.get('tipo_pendencia', 'OUTROS')
                        if tipo not in pendencias_por_tipo:
                            pendencias_por_tipo[tipo] = []
                        pendencias_por_tipo[tipo].append(pend)
                    
                    # Ordenar tipos
                    ordem_tipos = ['ICMS', 'Frete', 'AFRMM', 'LPCO', 'Bloqueio CE']
                    tipos_ordenados = sorted(
                        pendencias_por_tipo.keys(),
                        key=lambda x: (ordem_tipos.index(x) if x in ordem_tipos else 999, x)
                    )
                    
                    for tipo in tipos_ordenados:
                        pendencias_tipo = pendencias_por_tipo[tipo]
                        resposta += f"   **{tipo}** ({len(pendencias_tipo)} processo(s)):\n"
                        
                        # Agrupar por categoria dentro do tipo
                        pendencias_por_categoria = {}
                        for pend in pendencias_tipo:
                            proc_ref = pend.get('processo_referencia', '')
                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                            if cat not in pendencias_por_categoria:
                                pendencias_por_categoria[cat] = []
                            pendencias_por_categoria[cat].append(pend)
                        
                        for cat in sorted(pendencias_por_categoria.keys()):
                            pendencias_cat = pendencias_por_categoria[cat]
                            resposta += f"      *{cat}* ({len(pendencias_cat)} processo(s)):\n"
                            for pend in pendencias_cat:
                                resposta += f"         • **{pend.get('processo_referencia', 'N/A')}**"
                                if pend.get('descricao_pendencia'):
                                    resposta += f" - {pend['descricao_pendencia']}"
                                if pend.get('tempo_pendente'):
                                    resposta += f" (há {pend['tempo_pendente']})"
                                if pend.get('acao_sugerida'):
                                    resposta += f" - Ação: {pend['acao_sugerida']}"
                                resposta += "\n"
                        resposta += "\n"
                resposta += "\n"
                
                # DIs (registro/canal/status) - AGRUPADAS POR CATEGORIA DO PROCESSO
                dis_analise = secoes.get('dis_analise', [])
                resposta += f"📋 **DIs (REGISTRO/CANAL/STATUS)** ({len(dis_analise)} DI(s))\n"
                resposta += "_Obs.: **Registro** = dataHoraRegistro; **Desembaraço** = dataHoraDesembaraco._\n\n"
                if not dis_analise:
                    resposta += "   ✅ Nenhuma DI em análise.\n\n"
                else:
                    # Agrupar por categoria do processo
                    dis_por_categoria = {}
                    for di in dis_analise:
                        proc_ref = di.get('processo_referencia', '')
                        if proc_ref:
                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                        else:
                            cat = 'SEM PROCESSO'
                        if cat not in dis_por_categoria:
                            dis_por_categoria[cat] = []
                        dis_por_categoria[cat].append(di)
                    
                    for cat in sorted(dis_por_categoria.keys()):
                        dis_cat = dis_por_categoria[cat]
                        resposta += f"   **{cat}** ({len(dis_cat)} DI(s)):\n"
                        for di in dis_cat:
                            resposta += f"      • **{di.get('numero_di', 'N/A')}**"
                            if di.get('processo_referencia'):
                                resposta += f" - Processo: {di['processo_referencia']}"
                            if di.get('canal_di'):
                                resposta += f" - Canal: {di['canal_di']}"
                            if di.get('situacao_di'):
                                status_di_formatado = str(di['situacao_di']).replace('_', ' ').title()
                                resposta += f" - Status DI: {status_di_formatado}"
                            # ✅ NOVO (16/01/2026): Mostrar data/hora de registro quando disponível
                            data_registro = di.get('data_registro') or di.get('data_hora_registro')
                            if data_registro:
                                try:
                                    from datetime import datetime
                                    data_limpa = str(data_registro).replace('Z', '').replace('+00:00', '').strip()
                                    dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                                    if dt:
                                        resposta += f" - Registro: {dt.strftime('%d/%m/%Y %H:%M')}"
                                    else:
                                        resposta += f" - Registro: {data_registro}"
                                except Exception:
                                    resposta += f" - Registro: {data_registro}"
                            # ✅ NOVO: Mostrar desembaraço quando disponível (evita confusão com "registro")
                            data_desembaraco = di.get('data_desembaraco')
                            if data_desembaraco:
                                try:
                                    from datetime import datetime
                                    data_limpa = str(data_desembaraco).replace('Z', '').replace('+00:00', '').strip()
                                    dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                                    if dt:
                                        resposta += f" - Desembaraço: {dt.strftime('%d/%m/%Y %H:%M')}"
                                    else:
                                        resposta += f" - Desembaraço: {data_desembaraco}"
                                except Exception:
                                    resposta += f" - Desembaraço: {data_desembaraco}"
                            if di.get('tempo_analise'):
                                resposta += f" (há {di['tempo_analise']})"
                            resposta += "\n"
                        resposta += "\n"
                resposta += "\n"
                
                # DUIMPs em análise - AGRUPADAS POR CATEGORIA DO PROCESSO
                duimps_analise = secoes.get('duimps_analise', [])
                resposta += f"📋 **DUIMPs EM ANÁLISE** ({len(duimps_analise)} DUIMP(s))\n\n"
                if not duimps_analise:
                    resposta += "   ✅ Nenhuma DUIMP em análise.\n\n"
                else:
                    # Agrupar por categoria do processo
                    duimps_por_categoria = {}
                    for duimp in duimps_analise:
                        proc_ref = duimp.get('processo_referencia', '')
                        if proc_ref:
                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                        else:
                            cat = 'SEM PROCESSO'
                        if cat not in duimps_por_categoria:
                            duimps_por_categoria[cat] = []
                        duimps_por_categoria[cat].append(duimp)
                    
                    for cat in sorted(duimps_por_categoria.keys()):
                        duimps_cat = duimps_por_categoria[cat]
                        resposta += f"   **{cat}** ({len(duimps_cat)} DUIMP(s)):\n"
                        for duimp in duimps_cat:
                            resposta += f"      • **{duimp.get('numero_duimp', 'N/A')}** v{duimp.get('versao', 'N/A')}"
                            if duimp.get('processo_referencia'):
                                resposta += f" - Processo: {duimp['processo_referencia']}"
                            if duimp.get('canal_duimp'):
                                resposta += f" - Canal: {duimp['canal_duimp']}"
                            if duimp.get('status'):
                                status_duimp_formatado = str(duimp['status']).replace('_', ' ').title()
                                resposta += f" - Status DUIMP: {status_duimp_formatado}"
                            # ✅ NOVO (16/01/2026): Mostrar data/hora de registro quando disponível
                            data_registro = duimp.get('data_registro') or duimp.get('data_criacao')
                            if data_registro:
                                try:
                                    from datetime import datetime
                                    data_limpa = str(data_registro).replace('Z', '').replace('+00:00', '').strip()
                                    dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                                    if dt:
                                        resposta += f" - Registro: {dt.strftime('%d/%m/%Y %H:%M')}"
                                    else:
                                        resposta += f" - Registro: {data_registro}"
                                except Exception:
                                    resposta += f" - Registro: {data_registro}"
                            if duimp.get('tempo_analise'):
                                resposta += f" (há {duimp['tempo_analise']})"
                            resposta += "\n"
                        resposta += "\n"
                resposta += "\n"
                
                # ETA alterado - AGRUPADO POR TIPO DE MUDANÇA E CATEGORIA
                eta_alterado = secoes.get('eta_alterado', [])
                if eta_alterado:
                    resposta += f"🔄 **ETA ALTERADO** ({len(eta_alterado)} processo(s))\n\n"
                    
                    # Agrupar por tipo de mudança primeiro
                    eta_por_tipo = {}
                    for proc in eta_alterado:
                        tipo = proc.get('tipo_mudanca', 'OUTROS')
                        if tipo not in eta_por_tipo:
                            eta_por_tipo[tipo] = []
                        eta_por_tipo[tipo].append(proc)
                    
                    # Ordenar tipos (ATRASO primeiro, depois ADIANTADO)
                    ordem_tipos = ['ATRASO', 'ADIANTADO']
                    tipos_ordenados = sorted(
                        eta_por_tipo.keys(),
                        key=lambda x: (ordem_tipos.index(x) if x in ordem_tipos else 999, x)
                    )
                    
                    for tipo in tipos_ordenados:
                        processos_tipo = eta_por_tipo[tipo]
                        emoji = "📅" if tipo == 'ATRASO' else "⚡"
                        resposta += f"   {emoji} **{tipo}** ({len(processos_tipo)} processo(s)):\n"
                        
                        # Agrupar por categoria dentro do tipo
                        processos_por_categoria = {}
                        for proc in processos_tipo:
                            proc_ref = proc.get('processo_referencia', '')
                            cat = proc_ref.split('.')[0] if '.' in proc_ref else 'OUTROS'
                            if cat not in processos_por_categoria:
                                processos_por_categoria[cat] = []
                            processos_por_categoria[cat].append(proc)
                        
                        for cat in sorted(processos_por_categoria.keys()):
                            processos_cat = processos_por_categoria[cat]
                            resposta += f"      *{cat}* ({len(processos_cat)} processo(s)):\n"
                            for proc in processos_cat:
                                resposta += f"         • **{proc.get('processo_referencia', 'N/A')}**"
                                if proc.get('ultimo_eta_formatado'):
                                    resposta += f" - ETA: {proc['ultimo_eta_formatado']}"
                                elif proc.get('primeiro_eta_formatado'):
                                    resposta += f" - ETA: {proc['primeiro_eta_formatado']}"
                                if proc.get('dias_diferenca'):
                                    diferenca = proc['dias_diferenca']
                                    if diferenca > 0:
                                        resposta += f" (atraso de {diferenca} dia(s))"
                                    elif diferenca < 0:
                                        resposta += f" (adiantado em {abs(diferenca)} dia(s))"
                                resposta += "\n"
                            resposta += "\n"
                    resposta += "\n"
                
                # Alertas recentes
                alertas = secoes.get('alertas', [])
                if alertas:
                    resposta += f"🔔 **ALERTAS RECENTES**\n\n"
                    for alerta in alertas[:5]:  # Limitar a 5 alertas
                        emoji = "⚠️" if "pendente" in alerta.get('tipo', '').lower() or "bloqueio" in alerta.get('tipo', '').lower() else "✅"
                        
                        titulo = alerta.get('titulo', alerta.get('mensagem', ''))
                        status_atual = alerta.get('status_atual')
                        processo_ref = alerta.get('processo_referencia', '')
                        
                        # Se é alerta de status e tem status atual, formatar melhor
                        if status_atual and ('status_ce' in alerta.get('tipo', '').lower() or 'status_di' in alerta.get('tipo', '').lower() or 'status_duimp' in alerta.get('tipo', '').lower()):
                            if 'status_ce' in alerta.get('tipo', '').lower():
                                resposta += f"   {emoji} 📦 {processo_ref}: CE - {status_atual}"
                            elif 'status_di' in alerta.get('tipo', '').lower():
                                resposta += f"   {emoji} 📋 {processo_ref}: DI - {status_atual}"
                            elif 'status_duimp' in alerta.get('tipo', '').lower():
                                resposta += f"   {emoji} 📄 {processo_ref}: DUIMP - {status_atual}"
                        else:
                            resposta += f"   {emoji} {titulo}"
                            if processo_ref:
                                resposta += f" - {processo_ref}"
                        resposta += "\n"
                    resposta += "\n"
                
                resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                # Resumo
                total_chegando = resumo.get('total_chegando', 0)
                total_prontos = resumo.get('total_prontos', 0)
                total_em_dta = resumo.get('total_em_dta', 0)
                total_pendencias = resumo.get('total_pendencias', 0)
                total_dis = resumo.get('total_dis', 0)
                total_duimps = resumo.get('total_duimps', 0)
                total_eta_alterado = resumo.get('total_eta_alterado', 0)
                
                resposta += f"📊 **RESUMO:** {total_chegando} chegando | {total_prontos} prontos | {total_em_dta} em DTA | {total_pendencias} pendências | {total_dis} DIs | {total_duimps} DUIMPs"
                if total_eta_alterado:
                    resposta += f" | {total_eta_alterado} ETA alterado"
                resposta += "\n"
                
                # ✅ NOVO (12/01/2026): Adicionar JSON inline antes de retornar
                resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                return resposta
            
            elif tipo_relatorio == 'fechamento_dia':
                hoje = datetime.now().strftime('%d/%m/%Y')
                
                eh_filtrado = bool(dados_json.get('filtrado', False))
                secoes_filtradas = dados_json.get('secoes_filtradas', []) or []

                def _mostrar(secao_key: str) -> bool:
                    return (not eh_filtrado) or (secao_key in secoes_filtradas)

                def _fmt_dt(valor: Any) -> str:
                    """Formata timestamps para DD/MM/YYYY HH:MM (compatível com ISO ou 'YYYY-MM-DD HH:MM:SS')."""
                    if valor is None:
                        return ''
                    try:
                        from datetime import datetime, timezone, timedelta
                        texto = str(valor).strip()
                        if not texto:
                            return ''
                        # normalizar Z
                        if texto.endswith('Z'):
                            texto = texto[:-1] + '+00:00'
                        # remover microsegundos extras comuns
                        if '.' in texto and 'T' in texto:
                            # mantém timezone se existir
                            head, tail = texto.split('.', 1)
                            # tail pode conter tz (+00:00/-03:00)
                            tz = ''
                            if '+' in tail:
                                tz = '+' + tail.split('+', 1)[1]
                            elif '-' in tail:
                                # cuidado com data (YYYY-MM-DD)
                                parts = tail.split('-')
                                if len(parts) >= 2:
                                    tz = '-' + '-'.join(parts[1:])
                            texto = head + tz
                        texto = texto.replace(' ', 'T') if (' ' in texto and 'T' not in texto) else texto
                        dt = datetime.fromisoformat(texto)

                        # ✅ Ajuste de fuso horário:
                        # - Se vier com timezone (ex.: +00:00), converte para o fuso local.
                        # - Se vier sem timezone mas estiver "no futuro", assume que foi gravado em UTC e converte.
                        now_local = datetime.now().astimezone()
                        local_tz = now_local.tzinfo
                        if dt.tzinfo is not None:
                            dt = dt.astimezone(local_tz).replace(tzinfo=None)
                        else:
                            now_naive = now_local.replace(tzinfo=None)
                            delta = dt - now_naive
                            # Heurística: "futuro próximo" geralmente é UTC sendo exibido como local.
                            if delta > timedelta(minutes=5) and delta < timedelta(hours=12):
                                dt = dt.replace(tzinfo=timezone.utc).astimezone(local_tz).replace(tzinfo=None)

                        return dt.strftime('%d/%m/%Y %H:%M')
                    except Exception:
                        # fallback: tentar cortar segundos se vier "YYYY-MM-DD HH:MM:SS"
                        try:
                            s = str(valor).strip()
                            if len(s) >= 16 and ('-' in s or '/' in s):
                                # tenta converter "YYYY-MM-DD HH:MM"
                                if '-' in s and ':' in s:
                                    # pegar YYYY-MM-DD HH:MM
                                    base = s[:16]
                                    from datetime import datetime, timezone, timedelta
                                    dt = datetime.strptime(base, '%Y-%m-%d %H:%M')

                                    # Mesma heurística de fuso quando vier sem tz e estiver "no futuro".
                                    now_local = datetime.now().astimezone()
                                    local_tz = now_local.tzinfo
                                    now_naive = now_local.replace(tzinfo=None)
                                    delta = dt - now_naive
                                    if delta > timedelta(minutes=5) and delta < timedelta(hours=12):
                                        dt = dt.replace(tzinfo=timezone.utc).astimezone(local_tz).replace(tzinfo=None)

                                    return dt.strftime('%d/%m/%Y %H:%M')
                        except Exception:
                            pass
                        return str(valor)

                resposta = f"📊 **FECHAMENTO DO DIA"
                if categoria:
                    resposta += f" - {categoria.upper()}"
                resposta += f" - {hoje}**\n\n"
                resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                total_movimentacoes = resumo.get('total_movimentacoes', 0)
                resposta += f"📈 **TOTAL DE MOVIMENTAÇÕES:** {total_movimentacoes}\n\n"
                if eh_filtrado:
                    total_original = resumo.get('total_movimentacoes_original')
                    if total_original is not None and total_original != total_movimentacoes:
                        resposta = resposta.replace(
                            f"📈 **TOTAL DE MOVIMENTAÇÕES:** {total_movimentacoes}\n\n",
                            f"📈 **TOTAL DE MOVIMENTAÇÕES (filtrado):** {total_movimentacoes} (de {total_original})\n\n"
                        )
                
                # Processos que chegaram hoje
                if _mostrar('processos_chegaram'):
                    processos_chegaram = secoes.get('processos_chegaram', [])
                    if processos_chegaram:
                        resposta += f"🚢 **PROCESSOS QUE CHEGARAM HOJE** ({len(processos_chegaram)} processo(s))\n\n"
                        for proc in processos_chegaram:
                            resposta += f"   • **{proc.get('processo_referencia', 'N/A')}**"
                            if proc.get('porto_nome'):
                                resposta += f" - Porto: {proc['porto_nome']}"
                            if proc.get('numero_ce'):
                                resposta += f" - CE: {proc['numero_ce']}"
                            if proc.get('situacao_ce'):
                                resposta += f" - Status: {proc['situacao_ce']}"
                            resposta += "\n"
                        resposta += "\n"
                    else:
                        resposta += "🚢 **PROCESSOS QUE CHEGARAM HOJE:** Nenhum\n\n"
                
                # Processos desembaraçados hoje
                if _mostrar('processos_desembaracados'):
                    processos_desembaracados = secoes.get('processos_desembaracados', [])
                    if processos_desembaracados:
                        resposta += f"✅ **PROCESSOS DESEMBARAÇADOS HOJE** ({len(processos_desembaracados)} processo(s))\n\n"
                        for proc in processos_desembaracados:
                            resposta += f"   • **{proc.get('processo_referencia', 'N/A')}**"
                            if proc.get('numero_di'):
                                resposta += f" - DI: {proc['numero_di']}"
                            if proc.get('numero_duimp'):
                                resposta += f" - DUIMP: {proc['numero_duimp']}"
                            if proc.get('situacao_di'):
                                resposta += f" - Status DI: {proc['situacao_di']}"
                            elif proc.get('situacao_entrega'):
                                resposta += f" - Status: {proc['situacao_entrega']}"
                            if proc.get('data_desembaraco'):
                                resposta += f" - Desembaraço: {_fmt_dt(proc.get('data_desembaraco'))}"
                            resposta += "\n"
                        resposta += "\n"
                    else:
                        resposta += "✅ **PROCESSOS DESEMBARAÇADOS HOJE:** Nenhum\n\n"
                
                # DIs/DUIMPs registradas hoje
                duimps_criadas = secoes.get('duimps_criadas', [])
                dis_registradas = secoes.get('dis_registradas', [])
                
                if _mostrar('dis_registradas') and dis_registradas:
                    resposta += f"📄 **DIs REGISTRADAS HOJE** ({len(dis_registradas)} DI(s))\n\n"
                    for di in dis_registradas:
                        resposta += f"   • **{di.get('numero', 'N/A')}**"
                        if di.get('processo_referencia'):
                            resposta += f" - Processo: {di['processo_referencia']}"
                        resposta += f" - Status: {di.get('status', 'N/A')}"
                        data_registro = di.get('criado_em') or di.get('data_registro')
                        if data_registro:
                            resposta += f" - Registro: {_fmt_dt(data_registro)}"
                        resposta += "\n"
                    resposta += "\n"
                
                if _mostrar('duimps_criadas') and duimps_criadas:
                    resposta += f"📄 **DUIMPs REGISTRADAS HOJE** ({len(duimps_criadas)} DUIMP(s))\n\n"
                    for duimp in duimps_criadas:
                        # ✅ CORREÇÃO: Só mostrar versão se existir e não for 'N/A'
                        versao = duimp.get('versao')
                        versao_str = ""
                        if versao and versao != 'N/A' and str(versao).strip():
                            versao_str = f" (v{versao})"
                        
                        resposta += f"   • **{duimp.get('numero', 'N/A')}**{versao_str}"
                        if duimp.get('processo_referencia'):
                            resposta += f" - Processo: {duimp['processo_referencia']}"
                        resposta += f" - Status: {duimp.get('status', 'N/A')}"
                        resposta += f" - Ambiente: {duimp.get('ambiente', 'N/A')}"
                        resposta += "\n"
                    resposta += "\n"
                
                if _mostrar('dis_registradas') and _mostrar('duimps_criadas') and (not dis_registradas and not duimps_criadas):
                    resposta += "📄 **DIs/DUIMPs REGISTRADAS HOJE:** Nenhuma\n\n"

                # Mudanças de status (CE/DI/DUIMP)
                if _mostrar('mudancas_status_ce') or _mostrar('mudancas_status_di') or _mostrar('mudancas_status_duimp'):
                    mud_ce = secoes.get('mudancas_status_ce', []) if _mostrar('mudancas_status_ce') else []
                    mud_di = secoes.get('mudancas_status_di', []) if _mostrar('mudancas_status_di') else []
                    mud_du = secoes.get('mudancas_status_duimp', []) if _mostrar('mudancas_status_duimp') else []
                    if mud_ce or mud_di or mud_du:
                        def _pick_status(item: Dict[str, Any]) -> str:
                            for k in (
                                'status',
                                'situacao_ce',
                                'situacao_di',
                                'situacao_entrega',
                                'status_atual',
                                'situacao',
                            ):
                                v = item.get(k)
                                if v:
                                    return str(v)
                            return 'N/A'

                        def _pick_num(item: Dict[str, Any], *keys: str) -> str:
                            for k in keys:
                                v = item.get(k)
                                if v:
                                    return str(v)
                            return 'N/A'

                        resposta += f"🔄 **MUDANÇAS DE STATUS HOJE** ({len(mud_ce) + len(mud_di) + len(mud_du)} evento(s))\n\n"
                        for m in mud_ce:
                            num_ce = _pick_num(m, 'numero_ce', 'numeroCe', 'numero')
                            resposta += f"   • **{m.get('processo_referencia', 'N/A')}** - CE {num_ce} - Status: {_pick_status(m)}"
                            if m.get('atualizado_em'):
                                resposta += f" - {_fmt_dt(m.get('atualizado_em'))}"
                            resposta += "\n"
                        for m in mud_di:
                            num_di = _pick_num(m, 'numero_di', 'numeroDi', 'numero')
                            # Preferir mostrar a data do EVENTO (desembaraço), e deixar a data de atualização como secundária.
                            evento_txt = ""
                            if m.get('data_desembaraco'):
                                evento_txt = f" - Desembaraço: {_fmt_dt(m.get('data_desembaraco'))}"
                            resposta += f"   • **{m.get('processo_referencia', 'N/A')}** - DI {num_di} - Status: {_pick_status(m)}{evento_txt}"
                            if m.get('canal'):
                                resposta += f" - Canal: {m.get('canal')}"
                            if m.get('atualizado_em'):
                                resposta += f" (atualizado: {_fmt_dt(m.get('atualizado_em'))})"
                            resposta += "\n"
                        for m in mud_du:
                            num_duimp = _pick_num(m, 'numero_duimp', 'numeroDuimp', 'numero')
                            # Preferir mostrar a data do EVENTO (desembaraço), e deixar a data de atualização como secundária.
                            evento_txt = ""
                            if m.get('data_desembaraco'):
                                evento_txt = f" - Desembaraço: {_fmt_dt(m.get('data_desembaraco'))}"
                            resposta += f"   • **{m.get('processo_referencia', 'N/A')}** - DUIMP {num_duimp} - Status: {_pick_status(m)}{evento_txt}"
                            if m.get('ambiente'):
                                resposta += f" - Ambiente: {m.get('ambiente')}"
                            if m.get('atualizado_em'):
                                resposta += f" (atualizado: {_fmt_dt(m.get('atualizado_em'))})"
                            resposta += "\n"
                        resposta += "\n"

                # Pendências resolvidas
                if _mostrar('pendencias_resolvidas'):
                    pend = secoes.get('pendencias_resolvidas', [])
                    if pend:
                        resposta += f"✅ **PENDÊNCIAS RESOLVIDAS HOJE** ({len(pend)} item(ns))\n\n"
                        for p in pend:
                            resposta += f"   • **{p.get('processo_referencia', 'N/A')}** - {p.get('tipo_pendencia') or p.get('tipo') or 'Pendência'}"
                            if p.get('resolvido_em'):
                                resposta += f" - {p.get('resolvido_em')}"
                            resposta += "\n"
                        resposta += "\n"

                # Lista achatada (quando pedirem “as X completas”)
                if _mostrar('movimentacoes'):
                    movs = secoes.get('movimentacoes', []) or []
                    if movs:
                        # ✅ UX: deduplicar eventos óbvios no detalhamento (sem alterar o total do dia)
                        # Caso típico: desembaraço aparece como PROCESSO_DESEMBARACADO e também como STATUS_DI (mesma DI/status).
                        movs_dedup: List[Dict[str, Any]] = []
                        try:
                            chaves_desembaraco = set()
                            for m in movs:
                                if not isinstance(m, dict):
                                    continue
                                if m.get('tipo') != 'PROCESSO_DESEMBARACADO':
                                    continue
                                doc = m.get('documento') or {}
                                if isinstance(doc, dict) and doc.get('tipo') == 'DI' and doc.get('numero'):
                                    chave = (
                                        str(m.get('processo_referencia') or ''),
                                        str(doc.get('numero') or ''),
                                        str(m.get('status') or ''),
                                    )
                                    chaves_desembaraco.add(chave)

                            for m in movs:
                                if not isinstance(m, dict):
                                    movs_dedup.append(m)
                                    continue
                                if m.get('tipo') == 'STATUS_DI':
                                    doc = m.get('documento') or {}
                                    if isinstance(doc, dict) and doc.get('tipo') == 'DI' and doc.get('numero'):
                                        chave = (
                                            str(m.get('processo_referencia') or ''),
                                            str(doc.get('numero') or ''),
                                            str(m.get('status') or ''),
                                        )
                                        # Se já existe desembaraço com a mesma DI/status, omitir o STATUS_DI redundante
                                        if chave in chaves_desembaraco:
                                            continue
                                movs_dedup.append(m)
                        except Exception:
                            movs_dedup = [m for m in movs if isinstance(m, dict)]

                        if len(movs_dedup) != len(movs):
                            resposta += f"📋 **MOVIMENTAÇÕES (DETALHE)** ({len(movs_dedup)} item(ns) — deduplicado de {len(movs)})\n\n"
                        else:
                            resposta += f"📋 **MOVIMENTAÇÕES (DETALHE)** ({len(movs)} item(ns))\n\n"

                        for i, m in enumerate(movs_dedup, start=1):
                            proc_ref = m.get('processo_referencia', 'N/A')
                            tipo = m.get('tipo', 'N/A')
                            doc = m.get('documento') or {}
                            doc_txt = ""
                            if isinstance(doc, dict) and doc.get('tipo') and doc.get('numero'):
                                doc_txt = f" - {doc['tipo']}: {doc['numero']}"
                            status_txt = f" - Status: {m.get('status')}" if m.get('status') else ""
                            data_txt = f" - {_fmt_dt(m.get('data'))}" if m.get('data') else ""
                            resposta += f"   {i}. **{proc_ref}** - {tipo}{doc_txt}{status_txt}{data_txt}\n"
                        resposta += "\n"
                
                resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                if eh_filtrado and resumo.get('total_movimentacoes_original') is not None and resumo.get('total_movimentacoes_original') != total_movimentacoes:
                    resposta += f"📊 **RESUMO FINAL:** {total_movimentacoes} movimentação(ões) no filtro (de {resumo.get('total_movimentacoes_original')})\n"
                else:
                    resposta += f"📊 **RESUMO FINAL:** {total_movimentacoes} movimentação(ões) registrada(s) hoje\n"
                
                # ✅ NOVO (12/01/2026): Adicionar JSON inline antes de retornar
                resposta += RelatorioFormatterService._gerar_meta_json_inline(tipo_relatorio, dados_json)
                return resposta
            
            else:
                # Fallback genérico
                return f"📋 **Relatório {tipo_relatorio}**\n\nData: {data}\n\nDados disponíveis: {len(secoes)} seções\n"
                
        except Exception as e:
            logger.error(f'❌ Erro ao formatar relatório com fallback simples: {e}', exc_info=True)
            return f"❌ Erro ao formatar relatório: {str(e)}"


class ProcessoAgent(BaseAgent):
    """
    Agente responsável por operações relacionadas a processos de importação.
    
    Tools suportadas:
    - listar_processos: Lista processos de importação
    - consultar_status_processo: Consulta status detalhado de um processo
    - listar_processos_por_categoria: Lista processos filtrados por categoria
    - listar_processos_por_situacao: Lista processos filtrados por situação
    - listar_processos_por_eta: Lista processos filtrados por ETA
    - listar_processos_por_navio: Lista processos filtrados por navio
    - listar_processos_com_pendencias: Lista processos com pendências
    - listar_todos_processos_por_situacao: Lista todos os processos por situação
    - consultar_processo_consolidado: Consulta processo com dados consolidados
    - listar_processos_com_duimp: Lista processos que têm DUIMP
    """
    
    def execute(self, tool_name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Roteia para método específico baseado no nome da tool."""
        handlers = {
            'listar_processos': self._listar_processos,
            'consultar_status_processo': self._consultar_status_processo,
            'listar_processos_por_categoria': self._listar_por_categoria,
            'listar_processos_por_situacao': self._listar_por_situacao,
            'listar_processos_por_eta': self._listar_por_eta,
            'listar_processos_por_navio': self._listar_por_navio,
            'listar_processos_liberados_registro': self._listar_liberados_registro,
            'listar_processos_registrados_hoje': self._listar_registrados_hoje,
            'listar_processos_registrados_periodo': self._listar_registrados_periodo,
            'listar_processos_desembaracados_hoje': self._listar_desembaracados_hoje,
            'listar_processos_em_dta': self._listar_processos_em_dta,
            'listar_processos_com_pendencias': self._listar_com_pendencias,
            'listar_todos_processos_por_situacao': self._listar_todos_por_situacao,
            'consultar_processo_consolidado': self._consultar_processo_consolidado,
            'listar_processos_com_duimp': self._listar_processos_com_duimp,
            'obter_snapshot_processo': self._obter_snapshot_processo,
            'sincronizar_processos_ativos_maike': self._sincronizar_processos_ativos_maike,
            'obter_dashboard_hoje': self._obter_dashboard_hoje,
            'fechar_dia': self._fechar_dia,
            'gerar_relatorio_importacoes_fob': self._gerar_relatorio_importacoes_fob,
            'gerar_relatorio_averbacoes': self._gerar_relatorio_averbacoes,
            'obter_ajuda': self._obter_ajuda,
            'consultar_despesas_processo': self._consultar_despesas_processo,
            'consultar_contexto_sessao': self._consultar_contexto_sessao,  # ✅ NOVO (12/01/2026): Consultar contexto real
            'buscar_secao_relatorio_salvo': self._buscar_secao_relatorio_salvo,  # ✅ NOVO (12/01/2026): Buscar seção específica do relatório salvo
            'buscar_relatorio_por_id': self._buscar_relatorio_por_id,  # ✅ NOVO (12/01/2026): Buscar relatório específico por ID
            'filtrar_relatorio_fuzzy': self._filtrar_relatorio_fuzzy,  # ✅ NOVO (28/01/2026): Filtro/agrupamento fuzzy sobre relatório salvo
            'listar_dis_por_canal': self._listar_dis_por_canal,  # ✅ NOVO (20/01/2026): Lista DIs por canal (ativos-first)
            'listar_pendencias_ativas': self._listar_pendencias_ativas,  # ✅ NOVO (20/01/2026)
            'listar_alertas_recentes': self._listar_alertas_recentes,  # ✅ NOVO (20/01/2026)
            'listar_processos_prontos_registro': self._listar_processos_prontos_registro,  # ✅ NOVO (20/01/2026)
            'listar_eta_alterado': self._listar_eta_alterado,  # ✅ NOVO (20/01/2026)
            'listar_duimps_em_analise': self._listar_duimps_em_analise,  # ✅ NOVO (20/01/2026)
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                'sucesso': False,
                'erro': f'Tool {tool_name} não encontrada neste agente',
                'resposta': f'❌ Tool "{tool_name}" não está disponível no ProcessoAgent.'
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

    def _obter_snapshot_processo(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        processo_referencia = (arguments.get('processo_referencia') or '').upper().strip()
        auto_heal = arguments.get('auto_heal', True)

        if not processo_referencia:
            return {
                'sucesso': False,
                'erro': 'processo_referencia é obrigatório',
                'resposta': '❌ Informe o número do processo (ex: ALH.0001/25).'
            }

        try:
            from services.processo_snapshot_service import ProcessoSnapshotService

            svc = ProcessoSnapshotService()
            res = svc.obter_snapshot(processo_referencia, auto_heal=bool(auto_heal))
            if not res.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': res.get('erro'),
                    'resposta': f"❌ Não consegui gerar o snapshot de {processo_referencia}: {res.get('erro')}",
                }

            dados = res.get('dados') or {}
            compl = dados.get('completude') or {}

            resposta = (
                f"📌 **Snapshot do processo {processo_referencia}**\n\n"
                f"- **Documentos**: {compl.get('documentos_total', 0)} (por tipo: {compl.get('documentos_por_tipo', {})})\n"
                f"- **Valores mercadoria**: {compl.get('valores_total', 0)}\n"
                f"- **Impostos**: {compl.get('impostos_total', 0)}\n"
                f"- **Despesas conciliadas**: {compl.get('despesas_total', 0)}\n"
            )

            # Destacar 1-2 documentos mais recentes (se houver)
            docs = dados.get('documentos') or []
            if docs:
                top = docs[:3]
                resposta += "\n📄 **Últimos documentos**:\n"
                for d in top:
                    canal_txt = f" — Canal {d.get('canal_documento')}" if d.get('canal_documento') else ""
                    resposta += (
                        f"- {d.get('tipo_documento')} {d.get('numero_documento')} — "
                        f"{d.get('status_documento') or 'sem status'}"
                        f"{canal_txt}\n"
                    )

            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': dados,
            }
        except Exception as e:
            logger.error(f'Erro ao gerar snapshot do processo: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar snapshot do processo: {str(e)}'
            }
    
    def _sincronizar_processos_ativos_maike(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sincroniza processos ativos do Kanban (SQLite) para mAIke_assistente."""
        try:
            from services.processo_sync_service import ProcessoSyncService

            limite = arguments.get('limite', 50)
            incluir_documentos = arguments.get('incluir_documentos', True)
            incluir_valores_impostos = arguments.get('incluir_valores_impostos', True)

            svc = ProcessoSyncService()
            result = svc.sincronizar_processos_ativos(
                limite=int(limite) if limite is not None else 50,
                incluir_documentos=bool(incluir_documentos),
                incluir_valores_impostos=bool(incluir_valores_impostos),
            )

            if not result.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': result.get('erro') or 'ERRO_SINCRONIZACAO',
                    'resposta': f"❌ Erro ao sincronizar processos ativos: {result.get('erro')}"
                }

            resumo = result.get('resumo') or {}
            resposta = (
                "🔄 **Sincronização de processos ativos (Kanban → mAIke_assistente)**\n\n"
                f"- **Total analisado**: {resumo.get('total', 0)}\n"
                f"- **Processos upsert**: {resumo.get('processos_upsert', 0)}\n"
                f"- **Documentos upsert**: {resumo.get('documentos_upsert', 0)}\n"
                f"- **Valores upsert**: {resumo.get('valores_upsert', 0)}\n"
                f"- **Impostos upsert**: {resumo.get('impostos_upsert', 0)}\n"
                f"- **Pulados**: {resumo.get('skipped', 0)}\n"
                f"- **Erros**: {resumo.get('errors', 0)}"
            )

            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': result
            }

        except Exception as e:
            logger.error(f"❌ Erro ao sincronizar processos ativos: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f"❌ Erro ao sincronizar processos ativos: {str(e)}"
            }

    def _enriquecer_resposta_status_financeiro(
        self,
        resultado: Dict[str, Any],
        *,
        processo_referencia: str,
        processo_dto: Optional[Any] = None,
        processo_consolidado: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enriquecimento defensivo para `consultar_status_processo`.

        Anexa (quando existirem e ainda não estiverem no texto):
        - **AFRMM pago** (Mercante) com link do comprovante
        - **Impostos** já gravados em `mAIke_assistente.dbo.IMPOSTO_IMPORTACAO`
        """
        if not isinstance(resultado, dict):
            return resultado
        resposta = resultado.get("resposta")
        if not isinstance(resposta, str) or not resposta.strip():
            return resultado

        proc_ref = (processo_referencia or "").strip().upper()

        # Extrair números relevantes (CE/DI/DUIMP) de múltiplas fontes
        numero_ce = None
        numero_di = None
        numero_duimp = None

        try:
            if processo_dto is not None:
                numero_ce = getattr(processo_dto, "numero_ce", None) or numero_ce
                numero_di = getattr(processo_dto, "numero_di", None) or numero_di
                numero_duimp = getattr(processo_dto, "numero_duimp", None) or numero_duimp

                dc = getattr(processo_dto, "dados_completos", None)
                if isinstance(dc, dict):
                    ce_dc = dc.get("ce") or {}
                    di_dc = dc.get("di") or {}
                    du_dc = dc.get("duimp") or {}
                    if isinstance(ce_dc, dict) and ce_dc.get("numero"):
                        numero_ce = numero_ce or str(ce_dc.get("numero")).strip()
                    if isinstance(di_dc, dict) and di_dc.get("numero"):
                        numero_di = numero_di or str(di_dc.get("numero")).strip()
                    if isinstance(du_dc, dict) and du_dc.get("numero"):
                        numero_duimp = numero_duimp or str(du_dc.get("numero")).strip()
        except Exception:
            pass

        try:
            if isinstance(processo_consolidado, dict):
                ce_c = processo_consolidado.get("ce") or {}
                di_c = processo_consolidado.get("di") or {}
                du_c = processo_consolidado.get("duimp") or {}
                if isinstance(ce_c, dict) and ce_c.get("numero"):
                    numero_ce = numero_ce or str(ce_c.get("numero")).strip()
                if isinstance(di_c, dict) and di_c.get("numero"):
                    numero_di = numero_di or str(di_c.get("numero")).strip()
                if isinstance(du_c, dict) and du_c.get("numero"):
                    numero_duimp = numero_duimp or str(du_c.get("numero")).strip()
        except Exception:
            pass

        # 1) AFRMM pago + comprovante
        try:
            if "AFRMM" not in resposta and "Comprovante" not in resposta:
                if numero_ce:
                    from services.mercante_afrmm_pagamentos_service import MercanteAfrmmPagamentosService

                    svc_afrmm = MercanteAfrmmPagamentosService()
                    r = svc_afrmm.listar(ce_mercante=str(numero_ce), processo_referencia=proc_ref, limite=1)
                    itens = (r.get("dados") or {}).get("itens") if isinstance(r, dict) else None
                    if isinstance(itens, list) and itens:
                        it = itens[0] or {}
                        valor_total = it.get("valor_total_debito")
                        screenshot_url = it.get("screenshot_url")
                        status_txt = "✅ Pago" if str(it.get("status") or "").strip() == "success" else "✅ Pago (confirmado)"
                        bloco = ["", "💰 **AFRMM:**", f"- {status_txt}"]
                        if valor_total:
                            try:
                                bloco.append(f"- Valor débito: R$ {float(valor_total):,.2f}")
                            except Exception:
                                bloco.append(f"- Valor débito: {valor_total}")
                        if screenshot_url:
                            bloco.append(f"- 🧾 Comprovante: [abrir]({screenshot_url})")
                        resposta = (resposta.rstrip() + "\n" + "\n".join(bloco)).strip()
        except Exception:
            pass

        # 2) Impostos gravados no banco — resumo por tipo
        try:
            if "Impostos" not in resposta and "impostos" not in resposta.lower() and "tributos" not in resposta.lower():
                from services.imposto_valor_service import get_imposto_valor_service

                svc_iv = get_imposto_valor_service()
                rimp = svc_iv.buscar_impostos_processo(proc_ref)
                if isinstance(rimp, dict) and rimp.get("sucesso"):
                    impostos = rimp.get("impostos") or []
                    if isinstance(impostos, list) and impostos:
                        totals: Dict[str, float] = {}
                        total_geral = 0.0
                        for imp in impostos:
                            if not isinstance(imp, dict):
                                continue
                            tipo = (imp.get("tipo_imposto") or "OUTROS")
                            val = imp.get("valor_brl")
                            try:
                                v = float(val) if val is not None else 0.0
                            except Exception:
                                v = 0.0
                            if v:
                                totals[tipo] = totals.get(tipo, 0.0) + v
                                total_geral += v
                        if total_geral > 0:
                            bloco = ["", "💸 **Impostos (pagos / registrados):**"]
                            for k in sorted(totals.keys()):
                                bloco.append(f"- {k}: R$ {totals[k]:,.2f}")
                            bloco.append(f"- **Total**: R$ {total_geral:,.2f}")
                            resposta = (resposta.rstrip() + "\n" + "\n".join(bloco)).strip()
        except Exception:
            pass

        # 3) Valores (VMLE/VMLD/FOB/FRETE/SEGURO) já persistidos no banco novo
        try:
            if "VMLD" not in resposta and "VMLE" not in resposta:
                from utils.sql_server_adapter import get_sql_adapter
                from services.db_policy_service import get_primary_database

                sql_adapter = get_sql_adapter()
                if sql_adapter:
                    db = get_primary_database()
                    proc_sql = proc_ref.replace("'", "''")
                    q = f"""
                        SELECT
                            tipo_valor,
                            moeda,
                            MAX(valor) AS valor,
                            COUNT(1) AS qtd
                        FROM dbo.VALOR_MERCADORIA
                        WHERE processo_referencia = '{proc_sql}'
                          AND tipo_valor IN ('VMLD','VMLE','FOB','FRETE','SEGURO')
                          AND moeda IN ('BRL','USD')
                        GROUP BY tipo_valor, moeda
                        ORDER BY
                            CASE tipo_valor
                                WHEN 'VMLD' THEN 1
                                WHEN 'VMLE' THEN 2
                                WHEN 'FOB' THEN 3
                                WHEN 'FRETE' THEN 4
                                WHEN 'SEGURO' THEN 5
                                ELSE 99
                            END,
                            moeda
                    """
                    r = sql_adapter.execute_query(q, database=db, notificar_erro=False)
                    rows = r.get("data") if isinstance(r, dict) and r.get("success") else None
                    if isinstance(rows, list) and rows:
                        bloco = ["", "📦 **Valores (persistidos):**"]
                        for row in rows:
                            if not isinstance(row, dict):
                                continue
                            tipo = row.get("tipo_valor")
                            moeda = row.get("moeda")
                            val = row.get("valor")
                            qtd = row.get("qtd") or 0
                            try:
                                v = float(val) if val is not None else 0.0
                            except Exception:
                                v = 0.0
                            if not v:
                                continue
                            sufixo = f" (qtd={int(qtd)})" if int(qtd) > 1 else ""
                            if str(moeda).upper() == "USD":
                                bloco.append(f"- {tipo} (USD): $ {v:,.2f}{sufixo}")
                            else:
                                bloco.append(f"- {tipo} (BRL): R$ {v:,.2f}{sufixo}")
                        if len(bloco) > 2:
                            resposta = (resposta.rstrip() + "\n" + "\n".join(bloco)).strip()
                    else:
                        # 3b) Auto-heal leve: se não há VALOR_MERCADORIA, tentar DUIMP_DB (duimp_tributos_mercadoria)
                        # Isso cobre DUIMPs onde o "valor total local embarque" existe no banco Duimp mas ainda não foi persistido.
                        if numero_duimp:
                            try:
                                num = str(numero_duimp).replace("'", "''")
                                qid = f"SELECT TOP 1 duimp_id FROM Duimp.dbo.duimp WHERE numero = '{num}'"
                                rid = sql_adapter.execute_query(qid, database=db, notificar_erro=False)
                                duimp_id = None
                                if isinstance(rid, dict) and rid.get("success") and rid.get("data"):
                                    duimp_id = (rid.get("data") or [{}])[0].get("duimp_id")
                                if duimp_id:
                                    qv = (
                                        "SELECT TOP 1 valor_total_local_embarque_brl, valor_total_local_embarque_usd "
                                        f"FROM Duimp.dbo.duimp_tributos_mercadoria WHERE duimp_id = {int(duimp_id)}"
                                    )
                                    rv = sql_adapter.execute_query(qv, database=db, notificar_erro=False)
                                    if isinstance(rv, dict) and rv.get("success") and rv.get("data"):
                                        rowv = (rv.get("data") or [{}])[0] or {}
                                        v_brl = rowv.get("valor_total_local_embarque_brl")
                                        v_usd = rowv.get("valor_total_local_embarque_usd")
                                        try:
                                            v_brl_f = float(v_brl) if v_brl is not None else 0.0
                                        except Exception:
                                            v_brl_f = 0.0
                                        try:
                                            v_usd_f = float(v_usd) if v_usd is not None else 0.0
                                        except Exception:
                                            v_usd_f = 0.0

                                        if v_brl_f or v_usd_f:
                                            bloco = ["", "📦 **Valores (DUIMP):**"]
                                            if v_usd_f:
                                                bloco.append(f"- VMLE (USD): $ {v_usd_f:,.2f}")
                                                bloco.append(f"- FOB (USD): $ {v_usd_f:,.2f}")
                                            if v_brl_f:
                                                bloco.append(f"- VMLE (BRL): R$ {v_brl_f:,.2f}")
                                                bloco.append(f"- FOB (BRL): R$ {v_brl_f:,.2f}")
                                            resposta = (resposta.rstrip() + "\n" + "\n".join(bloco)).strip()

                                            # Persistir no banco novo (VALOR_MERCADORIA) para próximas consultas
                                            proc_sql2 = proc_ref.replace("'", "''")
                                            duimp_sql = str(numero_duimp).replace("'", "''")
                                            def _merge_val(tipo_valor: str, moeda: str, valor: float) -> None:
                                                tv = tipo_valor.replace("'", "''")
                                                md = moeda.replace("'", "''")
                                                sqlm = f"""
                                                    MERGE dbo.VALOR_MERCADORIA WITH (HOLDLOCK) AS tgt
                                                    USING (
                                                        SELECT
                                                            '{proc_sql2}' AS processo_referencia,
                                                            '{duimp_sql}' AS numero_documento,
                                                            'DUIMP' AS tipo_documento,
                                                            '{tv}' AS tipo_valor,
                                                            '{md}' AS moeda
                                                    ) AS src
                                                    ON tgt.processo_referencia = src.processo_referencia
                                                       AND tgt.numero_documento = src.numero_documento
                                                       AND tgt.tipo_documento = src.tipo_documento
                                                       AND tgt.tipo_valor = src.tipo_valor
                                                       AND tgt.moeda = src.moeda
                                                    WHEN MATCHED THEN
                                                        UPDATE SET
                                                            valor = {float(valor)},
                                                            data_atualizacao = GETDATE(),
                                                            fonte_dados = 'DUIMP_DB',
                                                            atualizado_em = GETDATE()
                                                    WHEN NOT MATCHED THEN
                                                        INSERT (
                                                            processo_referencia,
                                                            numero_documento,
                                                            tipo_documento,
                                                            tipo_valor,
                                                            moeda,
                                                            valor,
                                                            taxa_cambio,
                                                            data_valor,
                                                            data_atualizacao,
                                                            fonte_dados,
                                                            json_dados_originais,
                                                            criado_em,
                                                            atualizado_em
                                                        ) VALUES (
                                                            src.processo_referencia,
                                                            src.numero_documento,
                                                            src.tipo_documento,
                                                            src.tipo_valor,
                                                            src.moeda,
                                                            {float(valor)},
                                                            NULL,
                                                            NULL,
                                                            GETDATE(),
                                                            'DUIMP_DB',
                                                            NULL,
                                                            GETDATE(),
                                                            GETDATE()
                                                        );
                                                """
                                                sql_adapter.execute_query(sqlm, database=db, notificar_erro=False)

                                            if v_usd_f:
                                                _merge_val("VMLE", "USD", v_usd_f)
                                                _merge_val("FOB", "USD", v_usd_f)
                                            if v_brl_f:
                                                _merge_val("VMLE", "BRL", v_brl_f)
                                                _merge_val("FOB", "BRL", v_brl_f)
                            except Exception:
                                pass
        except Exception:
            pass

        resultado["resposta"] = resposta
        return resultado
    
    def _listar_processos(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos de importação."""
        status = arguments.get('status')
        limite = arguments.get('limite', 20)
        
        try:
            from db_manager import listar_processos as db_listar_processos
            
            processos = db_listar_processos(status=status if status != 'todos' else None, limit=limite)
            
            resposta = f"📋 **Processos de Importação**\n\n"
            if status and status != 'todos':
                resposta += f"Filtro: {status}\n\n"
            
            if not processos:
                resposta += "❌ Nenhum processo encontrado."
            else:
                for proc in processos[:limite]:
                    proc_ref = proc.get('processo_referencia', 'N/A')
                    status_proc = proc.get('status', 'N/A')
                    duimp_num = proc.get('duimp_numero', '')
                    resposta += f"**{proc_ref}**\n"
                    resposta += f"   - Status: {status_proc}\n"
                    if duimp_num:
                        resposta += f"   - DUIMP: {duimp_num} v{proc.get('duimp_versao', 'N/A')}\n"
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'processos': processos
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao listar processos: {str(e)}'
            }
    
    def _consultar_status_processo(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta status detalhado de um processo.
        
        ✅ NOVO: Usa ProcessoRepository para buscar em múltiplas fontes:
        - SQLite (cache do Kanban) → API Kanban → SQL Server (processos antigos)
        """
        processo_ref = arguments.get('processo_referencia', '').strip()
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'processo_referencia é obrigatório',
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = extract_processo_referencia(processo_ref)
        if not processo_completo:
            processo_completo = processo_ref

        # ✅ V2 (clean → auto-heal): para perguntas de "situação/status" retornar sempre do banco novo + SQLite,
        # e usar auto-heal seletivo só para preencher lacunas (sem rodar queries legadas barulhentas).
        mensagem_original = context.get('mensagem_original', '') if context else arguments.get('mensagem_original', '')
        try:
            msg_lower = (mensagem_original or '').lower()
            perguntou_eta_only = any(p in msg_lower for p in [' eta', 'quando chega', 'qdo chega', 'previs', 'previsão', 'previsao']) and not any(
                p in msg_lower for p in ['situacao', 'situação', 'status', 'como esta', 'como está']
            )
        except Exception:
            perguntou_eta_only = False

        if not perguntou_eta_only:
            try:
                from services.processo_status_v2_service import ProcessoStatusV2Service
                svc = ProcessoStatusV2Service()
                r = svc.consultar(processo_referencia=processo_completo, auto_heal=True, incluir_eta=True, incluir_afrmm=True)
                if isinstance(r, dict) and r.get('sucesso') and r.get('resposta'):
                    return {
                        'sucesso': True,
                        'resposta': r.get('resposta'),
                        'dados': r.get('dados'),
                    }
            except Exception as e:
                logger.debug(f"⚠️ StatusV2 falhou, caindo para fluxo antigo: {e}")
        
        # ✅ NOVO: Tentar buscar usando ProcessoRepository primeiro (Kanban + SQL Server)
        try:
            logger.info(f"🔍 Buscando processo {processo_completo} via ProcessoRepository...")
            from services.processo_repository import ProcessoRepository
            
            repositorio = ProcessoRepository()
            processo_dto = repositorio.buscar_por_referencia(processo_completo)
            
            if processo_dto:
                # Processo encontrado! Formatar resposta usando DTO
                logger.info(f"✅ Processo {processo_completo} encontrado via repositório (fonte: {processo_dto.fonte})")
                logger.info(f"📊 DTO tem: numero_ce={processo_dto.numero_ce}, numero_di={processo_dto.numero_di}, numero_duimp={processo_dto.numero_duimp}")
                logger.info(f"📊 DTO tem dados_completos: {bool(processo_dto.dados_completos)}")
                
                # ✅ CRÍTICO: Se o DTO não tem documentos mas tem dados_completos, verificar se tem dados lá
                if not processo_dto.numero_ce and not processo_dto.numero_di and not processo_dto.numero_duimp:
                    if processo_dto.dados_completos and isinstance(processo_dto.dados_completos, dict):
                        ce_data = processo_dto.dados_completos.get('ce', {})
                        di_data = processo_dto.dados_completos.get('di', {})
                        duimp_data = processo_dto.dados_completos.get('duimp', {})
                        logger.info(f"📊 dados_completos tem: ce={bool(ce_data)}, di={bool(di_data)}, duimp={bool(duimp_data)}")
                        if ce_data or di_data or duimp_data:
                            logger.info(f"✅ Dados encontrados em dados_completos, formatando resposta...")
                
                # ✅ NOVO: Passar mensagem original para detectar tipo de pergunta
                mensagem_original = mensagem_original
                
                # ✅ CRÍTICO: Verificar se tem dados completos antes de formatar
                # Se não tiver CE ou DI completa, usar o mesmo caminho do fallback (que funciona!)
                tem_ce = bool(processo_dto.numero_ce)
                tem_di_completa = False
                
                # ✅ NOVO: Verificar também em dados_completos se numero_ce estiver NULL
                if not tem_ce and processo_dto.dados_completos:
                    ce_data = processo_dto.dados_completos.get('ce', {})
                    if ce_data and ce_data.get('numero'):
                        tem_ce = True
                        logger.info(f"✅ CE encontrado em dados_completos: {ce_data.get('numero')}")
                
                if processo_dto.numero_di:
                    # Verificar se tem dados completos da DI
                    if processo_dto.dados_completos and processo_dto.dados_completos.get('di'):
                        di_data = processo_dto.dados_completos.get('di', {})
                        tem_situacao = bool(di_data.get('situacao') or di_data.get('situacao_di'))
                        tem_valores = bool(
                            di_data.get('valor_mercadoria_descarga_real') or 
                            di_data.get('real_VLMD') or
                            di_data.get('valor_mercadoria_embarque_real') or
                            di_data.get('real_VLME')
                        )
                        tem_importador = bool(di_data.get('nome_importador'))
                        tem_pagamentos = bool(di_data.get('pagamentos'))
                        tem_di_completa = tem_situacao and tem_valores and tem_importador and tem_pagamentos
                        logger.info(f"🔍 [DI] Verificando DI completa: situacao={tem_situacao}, valores={tem_valores}, importador={tem_importador}, pagamentos={tem_pagamentos}, completa={tem_di_completa}")
                
                # ✅ NOVO: Verificar também em dados_completos se numero_di estiver NULL
                if not processo_dto.numero_di and processo_dto.dados_completos:
                    di_data = processo_dto.dados_completos.get('di', {})
                    if di_data and di_data.get('numero'):
                        logger.info(f"✅ DI encontrada em dados_completos: {di_data.get('numero')}")
                        # Se tem DI mas não está completa, marcar como incompleta
                        if not tem_di_completa:
                            tem_di_completa = False  # Forçar fallback para enriquecer
                
                # ✅ CRÍTICO: Se não tem CE ou não tem DI/DUIMP completa, usar o mesmo caminho do fallback (que funciona!)
                # SEMPRE tentar o fallback se não tiver dados completos, mesmo que o DTO exista
                # ✅ NOVO: Verificar também se tem DUIMP completa (situação, canal, impostos)
                tem_duimp = bool(processo_dto.numero_duimp)
                tem_duimp_completa = False
                if tem_duimp and processo_dto.dados_completos:
                    duimp_data = processo_dto.dados_completos.get('duimp', {})
                    if isinstance(duimp_data, dict):
                        tem_situacao_duimp = bool(duimp_data.get('situacao') or duimp_data.get('situacaoDuimp') or duimp_data.get('ultima_situacao'))
                        tem_canal_duimp = bool(duimp_data.get('canal') or duimp_data.get('canalConsolidado') or duimp_data.get('canal_consolidado'))
                        # ✅ CRÍTICO: Verificar também se tem impostos (pagamentos ou tributos_calculados)
                        tem_impostos_duimp = bool(
                            duimp_data.get('pagamentos') or 
                            duimp_data.get('tributos_calculados') or
                            (duimp_data.get('tributos', {}).get('tributosCalculados') if isinstance(duimp_data.get('tributos'), dict) else False)
                        )
                        tem_duimp_completa = tem_situacao_duimp and tem_canal_duimp and tem_impostos_duimp
                        logger.info(f"🔍 [DUIMP] Verificando DUIMP completa: situacao={tem_situacao_duimp}, canal={tem_canal_duimp}, impostos={tem_impostos_duimp}, completa={tem_duimp_completa}")
                
                # Lógica simplificada: se não tem CE OU (não tem DI E não tem DUIMP) OU (tem DI mas não está completa E não tem DUIMP completa) → fallback
                # IMPORTANTE: Se tem DI mas não está completa E não tem DUIMP completa, também usar fallback
                deve_usar_fallback = not tem_ce or (not processo_dto.numero_di and not tem_duimp) or (processo_dto.numero_di and not tem_di_completa and not tem_duimp_completa)
                
                # ✅ CRÍTICO (regressão): pergunta "situação/status" DEVE tentar consolidado
                # Mesmo que a resposta do Kanban tenha ETA e pareça "completa", é no consolidado (Serpro/Duimp)
                # que entram VMLD/VMLE e impostos (pagamentos/tributos).
                try:
                    msg_lower = (mensagem_original or "").lower()
                    perguntou_situacao = (
                        "situação" in msg_lower
                        or "situacao" in msg_lower
                        or "status" in msg_lower
                        or "como esta" in msg_lower
                        or "como está" in msg_lower
                    )
                    # Evitar forçar fallback em perguntas puras de ETA/chegada
                    perguntou_so_eta = any(p in msg_lower for p in ["eta", "quando chega", "qdo chega", "previs"]) and not ("situa" in msg_lower or "status" in msg_lower)
                    if perguntou_situacao and not perguntou_so_eta:
                        deve_usar_fallback = True
                except Exception:
                    pass

                # ✅ CRÍTICO: Se tem DUIMP mas não está completa (falta impostos), SEMPRE usar fallback para enriquecer
                if tem_duimp and not tem_duimp_completa:
                    logger.info(f"⚠️ [DUIMP] DUIMP {processo_dto.numero_duimp} encontrada mas incompleta (falta impostos/situação/canal). Usando fallback para enriquecer...")
                    deve_usar_fallback = True
                
                # ✅ NOVO: SEMPRE tentar formatar primeiro para verificar se a resposta tem conteúdo
                # Se a resposta formatada só tiver categoria, usar fallback mesmo que tenha CE e DI
                resposta_formatada = self._formatar_resposta_processo_dto(processo_dto, processo_completo, mensagem_original)
                resposta_texto = resposta_formatada.get('resposta', '')
                
                # ✅ CRÍTICO: Verificar se a resposta tem impostos da DUIMP antes de retornar
                # Se tem DUIMP mas resposta não menciona impostos, usar fallback para enriquecer
                tem_impostos_na_resposta = (
                    'Impostos' in resposta_texto or 
                    'impostos' in resposta_texto.lower() or
                    'tributos' in resposta_texto.lower()
                )
                if tem_duimp and not tem_impostos_na_resposta:
                    logger.info(f"⚠️ [DUIMP] Resposta formatada não contém impostos para DUIMP {processo_dto.numero_duimp}. Usando fallback para enriquecer...")
                    deve_usar_fallback = True
                
                # ✅ SIMPLIFICADO: Se resposta tem conteúdo válido E não precisa de fallback, retornar
                # Não precisa ter documentos obrigatoriamente - processo pode ter outras informações (etapa, modal, ETA, etc.)
                linhas_resposta = [l.strip() for l in resposta_texto.split('\n') if l.strip()]
                tem_apenas_categoria = len(linhas_resposta) <= 3 and any('Categoria:' in l for l in linhas_resposta)
                resposta_tem_conteudo_valido = len(resposta_texto.strip()) > 200 or not tem_apenas_categoria
                
                # ✅ DECISÃO: Se resposta tem conteúdo válido E não precisa de fallback, retornar
                if resposta_tem_conteudo_valido and not deve_usar_fallback:
                    logger.info(f"✅ Resposta formatada tem conteúdo válido (tamanho: {len(resposta_texto.strip())}, apenas_categoria: {tem_apenas_categoria}), retornando...")
                    try:
                        resposta_formatada = self._enriquecer_resposta_status_financeiro(
                            resposta_formatada,
                            processo_referencia=processo_completo,
                            processo_dto=processo_dto,
                        )
                    except Exception:
                        pass
                    return resposta_formatada
                elif deve_usar_fallback:
                    logger.info(f"⚠️ Processo {processo_completo} precisa de fallback para enriquecer dados (DUIMP incompleta ou sem impostos). Continuando...")
                else:
                    logger.warning(f"⚠️ Processo {processo_completo} resposta muito curta ou só tem categoria, usando fallback...")
                    logger.info(f"📊 Resposta atual (primeiros 300 chars): {resposta_texto[:300]}...")
                    # Continuar para o fallback abaixo que busca do SQL Server
            else:
                # Processo não encontrado - tentar buscar documentos vinculados
                logger.warning(f"⚠️ Processo {processo_completo} não encontrado no repositório, tentando buscar documentos vinculados...")
        except ImportError as e:
            logger.error(f"❌ Erro de importação ao buscar processo no repositório: {e}")
            logger.warning("Continuando com busca antiga...")
        except Exception as e:
            logger.error(f"❌ Erro ao buscar processo no repositório: {e}", exc_info=True)
            logger.warning("Continuando com busca antiga...")
        
        # ✅ FALLBACK: Buscar documentos vinculados (pode ter CE/DI/DUIMP mesmo sem processo no Kanban)
        # ✅ CRÍTICO: SEMPRE executar este fallback, mesmo se ProcessoRepository não encontrou
        logger.info(f"🔍 [FALLBACK] Buscando documentos vinculados para {processo_completo}...")
        try:
            from db_manager import obter_dados_documentos_processo
            
            # ✅ NOVO: Verificar se a mensagem original menciona containers/itens
            # Se sim, garantir que os itens sejam consultados se necessário
            mensagem_original = context.get('mensagem_original', '') if context else ''
            if mensagem_original:
                mensagem_lower = mensagem_original.lower()
                perguntou_sobre_containers = any(palavra in mensagem_lower for palavra in [
                    'container', 'conteiner', 'lacre', 'itens', 'items', 'cargas', 'graneis'
                ])
                
                if perguntou_sobre_containers:
                    # Se perguntou sobre containers, garantir que os itens sejam consultados
                    try:
                        from db_manager import obter_dados_documentos_processo
                        dados_temp = obter_dados_documentos_processo(processo_completo)
                        ces_temp = dados_temp.get('ces', [])
                        
                        for ce_temp in ces_temp:
                            numero_ce_temp = ce_temp.get('numero', '')
                            if numero_ce_temp:
                                # Verificar se tem itens no cache
                                from db_manager import buscar_ce_itens_cache
                                itens_temp = buscar_ce_itens_cache(numero_ce_temp)
                                
                                if not itens_temp:
                                    # Não tem itens, forçar consulta via endpoint
                                    import requests
                                    import os
                                    base_url = os.getenv('FLASK_BASE_URL', 'http://localhost:5500')
                                    url_ce = f'{base_url}/api/int/integracomex/ce/{numero_ce_temp}'
                                    try:
                                        response_ce = requests.get(url_ce, timeout=10)
                                        # Isso vai disparar a consulta automática de itens
                                        logger.info(f'✅ Forçando consulta do CE {numero_ce_temp} para obter itens')
                                    except Exception as e:
                                        logger.debug(f'Erro ao forçar consulta do CE {numero_ce_temp}: {e}')
                    except Exception as e:
                        logger.debug(f'Erro ao verificar itens antes de consultar processo: {e}')
            
            dados_processo = obter_dados_documentos_processo(processo_completo)
            logger.info(f"📊 [FALLBACK] obter_dados_documentos_processo retornou: ces={len(dados_processo.get('ces', [])) if dados_processo else 0}, dis={len(dados_processo.get('dis', [])) if dados_processo else 0}, duimps={len(dados_processo.get('duimps', [])) if dados_processo else 0}")
            
            # Verificar se há documentos vinculados mesmo sem processo no Kanban
            ces = dados_processo.get('ces', []) if dados_processo else []
            dis = dados_processo.get('dis', []) if dados_processo else []
            duimps = dados_processo.get('duimps', []) if dados_processo else []
            ccts = dados_processo.get('ccts', []) if dados_processo else []
            
            # ✅ CRÍTICO: Se não tem documentos, tentar SQL Server PRIMEIRO (ele alimenta o JSON Kanban)
            if (not dados_processo or dados_processo.get('erro')) and not (ces or dis or duimps or ccts):
                logger.warning(f"⚠️ [FALLBACK] Nenhum documento encontrado no cache, buscando SQL Server PRIMEIRO (fonte primária)...")
                # ✅ PRIORIDADE: SQL Server primeiro (ele alimenta o JSON Kanban)
                try:
                    from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                    processo_consolidado = buscar_processo_consolidado_sql_server(processo_completo)
                    if processo_consolidado:
                        logger.info(f"✅ [FALLBACK] Dados consolidados encontrados para {processo_completo}, formatando resposta completa...")
                        logger.info(f"📊 [FALLBACK] processo_consolidado keys: {list(processo_consolidado.keys())}")
                        logger.info(f"📊 [FALLBACK] tem CE: {bool(processo_consolidado.get('ce'))}, tem DI: {bool(processo_consolidado.get('di'))}, tem DUIMP: {bool(processo_consolidado.get('duimp'))}")
                        
                        # Usar dados consolidados para formatar resposta completa
                        resposta = f"📋 **Processo {processo_completo}**\n\n"
                        
                        # Categoria
                        categoria = processo_completo.split('.')[0] if '.' in processo_completo else 'N/A'
                        resposta += f"**Categoria:** {categoria}\n\n"
                        
                        # CE - usar dados consolidados se disponível
                        ce_data = processo_consolidado.get('ce')
                        if ce_data and ce_data.get('numero'):
                            resposta += f"**📦 Conhecimento de Embarque:**\n"
                            resposta += f"  - CE {ce_data.get('numero', 'N/A')}\n"
                            if ce_data.get('situacao'):
                                resposta += f"  - Situação: {ce_data.get('situacao')}\n"
                            if ce_data.get('valor_frete_total'):
                                resposta += f"  - 💰 Valor Frete Total: R$ {float(ce_data.get('valor_frete_total', 0)):,.2f}\n"
                            if ce_data.get('data_situacao'):
                                resposta += f"  - Data Situação: {ce_data.get('data_situacao')}\n"
                            resposta += "\n"
                        
                        # DI - usar dados consolidados (que busca via Hi_Historico_Di) com TODOS os valores
                        di_data = processo_consolidado.get('di')
                        if di_data and di_data.get('numero'):
                            resposta += f"**📄 Declaração de Importação:**\n"
                            resposta += f"  - DI {di_data.get('numero', 'N/A')}\n"
                            if di_data.get('situacao') or di_data.get('situacao_di'):
                                resposta += f"  - Situação: {di_data.get('situacao') or di_data.get('situacao_di')}\n"
                            if di_data.get('canal'):
                                resposta += f"  - Canal: {di_data.get('canal')}\n"
                            if di_data.get('data_desembaraco'):
                                resposta += f"  - Data Desembaraço: {di_data.get('data_desembaraco')}\n"
                            if di_data.get('situacao_entrega'):
                                resposta += f"  - Situação Entrega: {di_data.get('situacao_entrega')}\n"
                            
                            # ✅ CRÍTICO: Valores de mercadoria do SQL Server
                            if di_data.get('valor_mercadoria_descarga_real'):
                                resposta += f"  - 💰 Valor Mercadoria Descarga (BRL): R$ {float(di_data.get('valor_mercadoria_descarga_real', 0)):,.2f}\n"
                            if di_data.get('valor_mercadoria_embarque_real'):
                                resposta += f"  - 💰 Valor Mercadoria Embarque (BRL): R$ {float(di_data.get('valor_mercadoria_embarque_real', 0)):,.2f}\n"
                            if di_data.get('valor_mercadoria_descarga_dolar'):
                                resposta += f"  - 💰 Valor Mercadoria Descarga (USD): ${float(di_data.get('valor_mercadoria_descarga_dolar', 0)):,.2f}\n"
                            if di_data.get('valor_mercadoria_embarque_dolar'):
                                resposta += f"  - 💰 Valor Mercadoria Embarque (USD): ${float(di_data.get('valor_mercadoria_embarque_dolar', 0)):,.2f}\n"
                            
                            if di_data.get('nome_importador'):
                                resposta += f"  - 👤 Importador: {di_data.get('nome_importador')}\n"
                            
                            # ✅ CRÍTICO: Impostos/Pagamentos (buscar do SQL Server se disponível)
                            pagamentos = di_data.get('pagamentos', [])
                            if pagamentos and isinstance(pagamentos, list) and len(pagamentos) > 0:
                                resposta += f"  - **Impostos Pagos:**\n"
                                total_impostos = 0
                                for pagamento in pagamentos:
                                    if isinstance(pagamento, dict):
                                        tipo_imposto = pagamento.get('tipo', 'N/A')
                                        valor_pago = pagamento.get('valor', 0) or pagamento.get('valor_pago', 0) or 0
                                        data_pagamento = pagamento.get('data', '') or pagamento.get('data_pagamento', '')
                                        if valor_pago:
                                            total_impostos += float(valor_pago)
                                            data_str = f" (pago em {data_pagamento})" if data_pagamento else ""
                                            resposta += f"    • {tipo_imposto}: R$ {float(valor_pago):,.2f}{data_str}\n"
                                if total_impostos > 0:
                                    resposta += f"    **Total Impostos: R$ {total_impostos:,.2f}**\n"
                            
                            resposta += "\n"
                        
                        # ✅ CORREÇÃO: DUIMP - usar dados consolidados se disponível
                        duimp_data = processo_consolidado.get('duimp')
                        if duimp_data and duimp_data.get('numero'):
                            resposta += f"**📝 DUIMP (Declaração Única de Importação):**\n"
                            resposta += f"  - DUIMP {duimp_data.get('numero', 'N/A')}\n"
                            if duimp_data.get('versao'):
                                resposta += f"  - Versão: {duimp_data.get('versao')}\n"
                            if duimp_data.get('situacao') or duimp_data.get('situacaoDuimp') or duimp_data.get('ultima_situacao'):
                                situacao_duimp = duimp_data.get('situacao') or duimp_data.get('situacaoDuimp') or duimp_data.get('ultima_situacao')
                                resposta += f"  - Situação: {situacao_duimp}\n"
                            if duimp_data.get('canal') or duimp_data.get('canalConsolidado') or duimp_data.get('canal_consolidado'):
                                canal_duimp = duimp_data.get('canal') or duimp_data.get('canalConsolidado') or duimp_data.get('canal_consolidado')
                                resposta += f"  - Canal: {canal_duimp}\n"
                            if duimp_data.get('data_registro'):
                                resposta += f"  - Data Registro: {duimp_data.get('data_registro')}\n"
                            
                            # ✅ CRÍTICO: Impostos pagos da DUIMP (do SQL Server)
                            pagamentos_duimp = duimp_data.get('pagamentos', [])
                            if pagamentos_duimp and isinstance(pagamentos_duimp, list) and len(pagamentos_duimp) > 0:
                                resposta += f"  - **Impostos Pagos:**\n"
                                total_impostos_duimp = 0
                                for pagamento in pagamentos_duimp:
                                    if isinstance(pagamento, dict):
                                        tipo_imposto = pagamento.get('tipo', 'N/A')
                                        valor_pago = pagamento.get('valor', 0) or pagamento.get('valor_pago', 0) or 0
                                        data_pagamento = pagamento.get('data', '') or pagamento.get('data_pagamento', '')
                                        if valor_pago:
                                            total_impostos_duimp += float(valor_pago)
                                            data_str = f" (pago em {data_pagamento})" if data_pagamento else ""
                                            resposta += f"    • {tipo_imposto}: R$ {float(valor_pago):,.2f}{data_str}\n"
                                if total_impostos_duimp > 0:
                                    resposta += f"    **Total Impostos: R$ {total_impostos_duimp:,.2f}**\n"
                            else:
                                # ✅ Fallback: alguns payloads de DUIMP trazem tributos calculados (não "pagamentos")
                                try:
                                    vc = duimp_data.get('tributos') or duimp_data.get('valoresCalculados') or {}
                                    if isinstance(vc, dict):
                                        tribs = vc.get('tributosCalculados', [])
                                        if tribs and isinstance(tribs, list):
                                            resposta += f"  - **Impostos (calculados):**\n"
                                            total_calc = 0.0
                                            for t in tribs:
                                                if not isinstance(t, dict):
                                                    continue
                                                tipo = t.get('tipo') or t.get('descricao') or t.get('codigoTributo') or 'N/A'
                                                valores_brl = t.get('valoresBRL', {}) or {}
                                                valor = (
                                                    valores_brl.get('aRecolher')
                                                    or t.get('valorRecolhido')
                                                    or t.get('valor')
                                                    or 0
                                                )
                                                try:
                                                    valor_f = float(valor) if valor else 0.0
                                                except Exception:
                                                    valor_f = 0.0
                                                if valor_f:
                                                    total_calc += valor_f
                                                    resposta += f"    • {tipo}: R$ {valor_f:,.2f}\n"
                                            if total_calc:
                                                resposta += f"    **Total Impostos: R$ {total_calc:,.2f}**\n"
                                except Exception:
                                    pass
                            
                            resposta += "\n"
                        
                        # ✅ CORREÇÃO: Verificar se tem CE, DI OU DUIMP (não apenas CE ou DI)
                        tem_ce_ou_di_ou_duimp = (ce_data and ce_data.get('numero')) or (di_data and di_data.get('numero')) or (duimp_data and duimp_data.get('numero'))
                        if tem_ce_ou_di_ou_duimp:
                            logger.info(f"✅ [FALLBACK] Resposta formatada com documentos (CE, DI ou DUIMP encontrados)")
                            result_ok = {
                                'sucesso': True,
                                'resposta': resposta,
                                'dados': {'processo_referencia': processo_completo}
                            }
                            try:
                                result_ok = self._enriquecer_resposta_status_financeiro(
                                    result_ok,
                                    processo_referencia=processo_completo,
                                    processo_consolidado=processo_consolidado,
                                )
                            except Exception:
                                pass
                            return result_ok
                        else:
                            logger.warning(f"⚠️ [FALLBACK] processo_consolidado encontrado mas sem CE, DI nem DUIMP. Continuando busca...")
                            # Continuar para buscar de outras formas abaixo
                except Exception as e:
                    logger.error(f"❌ Erro ao buscar processo consolidado do SQL Server: {e}", exc_info=True)
                
                # Fallback: Tentar query simples no SQL Server
                try:
                    from utils.sql_server_adapter import get_sql_adapter
                    from services.db_policy_service import (
                        get_primary_database,
                        get_legacy_database,
                        log_legacy_fallback,
                        should_use_legacy_database
                    )
                    
                    sql_adapter = get_sql_adapter()
                    database_para_usar = get_primary_database()
                    
                    query = f'''
                        SELECT TOP 1 numero_processo, id_processo_importacao, numero_ce, numero_di, numero_duimp
                        FROM {database_para_usar}.dbo.PROCESSO_IMPORTACAO
                        WHERE numero_processo = ?
                    '''
                    
                    result = sql_adapter.execute_query(query, database_para_usar, [processo_completo.upper()], notificar_erro=False)
                    
                    # Se não encontrou no primário e fallback está permitido, tentar Make
                    if (not result.get('success') or not result.get('data') or len(result.get('data', [])) == 0):
                        if should_use_legacy_database(processo_completo):
                            log_legacy_fallback(
                                processo_referencia=processo_completo,
                                tool_name='_formatar_resposta_processo_dto',
                                caller_function='ProcessoAgent._formatar_resposta_processo_dto',
                                reason="Processo não encontrado no banco primário, tentando fallback",
                                query=query
                            )
                            database_para_usar = get_legacy_database()
                            query_legacy = f'''
                                SELECT TOP 1 numero_processo, id_processo_importacao, numero_ce, numero_di, numero_duimp
                                FROM {database_para_usar}.dbo.PROCESSO_IMPORTACAO
                                WHERE numero_processo = ?
                            '''
                            result = sql_adapter.execute_query(query_legacy, database_para_usar, [processo_completo.upper()], notificar_erro=False)
                    
                    if result.get('success') and result.get('data') and len(result['data']) > 0:
                        row = result['data'][0]
                        logger.info(f"✅ [FALLBACK] Processo {processo_completo} encontrado no SQL Server diretamente")
                        # Processo existe no SQL Server, mas não tem documentos vinculados no SQLite
                        # ✅ NOVO: Tentar buscar dados consolidados do SQL Server para enriquecer
                        try:
                            from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                            processo_consolidado = buscar_processo_consolidado_sql_server(processo_completo)
                            if processo_consolidado:
                                logger.info(f"✅ [FALLBACK] Dados consolidados encontrados para {processo_completo}, formatando resposta completa...")
                                # Usar dados consolidados para formatar resposta completa
                                resposta = f"📋 **Processo {processo_completo}**\n\n"
                                
                                # Categoria
                                categoria = processo_completo.split('.')[0] if '.' in processo_completo else 'N/A'
                                resposta += f"**Categoria:** {categoria}\n\n"
                                
                                # CE - usar dados consolidados se disponível
                                ce_data = processo_consolidado.get('ce')
                                if ce_data:
                                    resposta += f"**📦 Conhecimento de Embarque:**\n"
                                    resposta += f"  - CE {ce_data.get('numero', row.get('numero_ce', 'N/A'))}\n"
                                    if ce_data.get('situacao'):
                                        resposta += f"  - Situação: {ce_data.get('situacao')}\n"
                                    if ce_data.get('data_situacao'):
                                        resposta += f"  - Data Situação: {ce_data.get('data_situacao')}\n"
                                    resposta += "\n"
                                elif row.get('numero_ce'):
                                    resposta += f"**📦 Conhecimento de Embarque:**\n"
                                    resposta += f"  - CE {row.get('numero_ce')}\n\n"
                                
                                # DI - usar dados consolidados (que busca via Hi_Historico_Di)
                                di_data = processo_consolidado.get('di')
                                if di_data:
                                    resposta += f"**📄 Declaração de Importação:**\n"
                                    resposta += f"  - DI {di_data.get('numero', 'N/A')}\n"
                                    if di_data.get('situacao'):
                                        resposta += f"  - Situação: {di_data.get('situacao')}\n"
                                    if di_data.get('canal'):
                                        resposta += f"  - Canal: {di_data.get('canal')}\n"
                                    if di_data.get('data_desembaraco'):
                                        resposta += f"  - Data Desembaraço: {di_data.get('data_desembaraco')}\n"
                                    if di_data.get('situacao_entrega'):
                                        resposta += f"  - Situação Entrega: {di_data.get('situacao_entrega')}\n"
                                    if di_data.get('valor_mercadoria_descarga_real'):
                                        resposta += f"  - Valor Mercadoria Descarga (BRL): R$ {float(di_data.get('valor_mercadoria_descarga_real', 0)):,.2f}\n"
                                    if di_data.get('valor_mercadoria_embarque_real'):
                                        resposta += f"  - Valor Mercadoria Embarque (BRL): R$ {float(di_data.get('valor_mercadoria_embarque_real', 0)):,.2f}\n"
                                    if di_data.get('nome_importador'):
                                        resposta += f"  - Importador: {di_data.get('nome_importador')}\n"
                                    resposta += "\n"
                                elif row.get('numero_di'):
                                    resposta += f"**📄 Declaração de Importação:**\n"
                                    resposta += f"  - DI {row.get('numero_di')}\n\n"
                                
                                # DUIMP - COM ENRIQUECIMENTO
                                if row.get('numero_duimp'):
                                    resposta += f"**📝 DUIMP:**\n"
                                    numero_duimp = row.get('numero_duimp')
                                    resposta += f"  - DUIMP {numero_duimp}\n"
                                    
                                    # Tentar enriquecer DUIMP com situação, canal e impostos
                                    if processo_consolidado:
                                        duimp_sql = processo_consolidado.get('duimp')
                                        if isinstance(duimp_sql, dict):
                                            situacao_duimp = duimp_sql.get('situacao', '')
                                            canal_duimp = duimp_sql.get('canal', '')
                                        elif isinstance(duimp_sql, list) and len(duimp_sql) > 0:
                                            # Se for lista, pegar o primeiro item
                                            primeiro_duimp = duimp_sql[0]
                                            if isinstance(primeiro_duimp, dict):
                                                situacao_duimp = primeiro_duimp.get('situacao', '')
                                                canal_duimp = primeiro_duimp.get('canal', '')
                                        if situacao_duimp:
                                            resposta += f"    - Situação: {situacao_duimp}\n"
                                        if canal_duimp:
                                            resposta += f"    - Canal: {canal_duimp}\n"
                                    
                                    # Tentar buscar payload completo do SQLite para impostos
                                    try:
                                        import sqlite3
                                        from db_manager import get_db_connection
                                        conn_duimp = get_db_connection()
                                        conn_duimp.row_factory = sqlite3.Row
                                        cursor_duimp = conn_duimp.cursor()
                                        cursor_duimp.execute('''
                                            SELECT payload_completo
                                            FROM duimps
                                            WHERE numero = ? AND ambiente = 'producao'
                                            ORDER BY CAST(versao AS INTEGER) DESC
                                            LIMIT 1
                                        ''', (numero_duimp,))
                                        row_duimp = cursor_duimp.fetchone()
                                        conn_duimp.close()
                                        
                                        if row_duimp and row_duimp['payload_completo']:
                                            import json
                                            payload_parsed = json.loads(row_duimp['payload_completo']) if isinstance(row_duimp['payload_completo'], str) else row_duimp['payload_completo']
                                            if isinstance(payload_parsed, dict):
                                                vc = payload_parsed.get('tributos') or payload_parsed.get('valoresCalculados') or {}
                                                if vc:
                                                    mercadoria_vc = vc.get('mercadoria', {})
                                                    if mercadoria_vc:
                                                        valor_fob_usd = mercadoria_vc.get('valorTotalLocalEmbarqueUSD', 0) or 0
                                                        valor_fob_brl = mercadoria_vc.get('valorTotalLocalEmbarqueBRL', 0) or 0
                                                        if valor_fob_usd or valor_fob_brl:
                                                            resposta += f"    - Valor FOB (USD): {valor_fob_usd:,.2f}\n" if valor_fob_usd else ""
                                                            resposta += f"    - Valor FOB (BRL): R$ {valor_fob_brl:,.2f}\n" if valor_fob_brl else ""
                                                    
                                                    tribs = vc.get('tributosCalculados', [])
                                                    if tribs:
                                                        resposta += f"    - **Impostos:**\n"
                                                        total_impostos = 0
                                                        for t in tribs:
                                                            valores_brl = t.get('valoresBRL', {}) or {}
                                                            valor_recolher = valores_brl.get('aRecolher', 0) or 0
                                                            tipo_tributo = t.get('tipo', 'N/A')
                                                            if valor_recolher:
                                                                total_impostos += float(valor_recolher)
                                                                resposta += f"      • {tipo_tributo}: R$ {float(valor_recolher):,.2f}\n"
                                                        if total_impostos > 0:
                                                            resposta += f"      **Total Impostos: R$ {total_impostos:,.2f}**\n"
                                    except Exception as e:
                                        logger.debug(f'Erro ao buscar payload completo da DUIMP {numero_duimp}: {e}')
                                    
                                    resposta += "\n"
                                
                                resposta += f"💡 **Fonte:** SQL Server (dados históricos)\n"
                                
                                return {
                                    'sucesso': True,
                                    'resposta': resposta,
                                    'dados': {'processo_existe': True, 'fonte': 'sql_server'}
                                }
                        except Exception as e:
                            logger.debug(f'Erro ao buscar dados consolidados do SQL Server: {e}')
                        
                        # Fallback: resposta básica se não conseguir enriquecer
                        resposta = f"📋 **Processo {processo_completo}**\n\n"
                        resposta += f"⚠️ **Processo encontrado no sistema, mas sem documentos vinculados no cache local.**\n\n"
                        if row.get('numero_ce'):
                            resposta += f"📦 **CE:** {row.get('numero_ce')}\n"
                        if row.get('numero_di'):
                            resposta += f"📄 **DI:** {row.get('numero_di')}\n"
                        if row.get('numero_duimp'):
                            resposta += f"📝 **DUIMP:** {row.get('numero_duimp')}\n"
                        resposta += f"\n💡 **Dica:** Este processo existe no sistema, mas os documentos ainda não foram consultados e salvos no cache local."
                        
                        return {
                            'sucesso': True,
                            'resposta': resposta,
                            'dados': {'processo_existe': True, 'fonte': 'sql_server'}
                        }
                except Exception as e:
                    logger.error(f'❌ [FALLBACK] Erro ao buscar processo no SQL Server: {e}', exc_info=True)
                
                # Se chegou aqui, processo realmente não existe
                logger.warning(f"❌ [FALLBACK] Processo {processo_completo} não encontrado em nenhuma fonte")
                erro_msg = dados_processo.get('erro', 'Processo não encontrado') if dados_processo else 'Processo não encontrado'
                return {
                    'sucesso': False,
                    'erro': erro_msg,
                    'resposta': f"❌ **Processo {processo_completo} não encontrado.**\n\n💡 **Dicas:**\n- Verifique se o número do processo está correto (formato: XXX.0000/AA)\n- O processo pode não estar mais ativo no Kanban\n- Tente buscar pelo número do CE, DI ou DUIMP"
                }
            
            # Se tem documentos mas não tem processo, ainda pode mostrar os dados
            if not dados_processo or dados_processo.get('erro'):
                # Tentar criar dados_processo mínimo com os documentos encontrados
                if ces or dis or duimps or ccts:
                    dados_processo = {
                        'ces': ces,
                        'dis': dis,
                        'duimps': duimps,
                        'ccts': ccts,
                        'resumo': {'total_documentos': len(ces) + len(dis) + len(duimps) + len(ccts)}
                    }
                else:
                    erro_msg = dados_processo.get('erro', 'Processo não encontrado') if dados_processo else 'Processo não encontrado'
                    return {
                        'sucesso': False,
                        'erro': erro_msg,
                        'resposta': f"❌ **Processo {processo_completo} não encontrado.**\n\n💡 **Dicas:**\n- Verifique se o número do processo está correto\n- O processo pode não estar mais ativo"
                    }
            
            # ✅ Formatar resposta completa com todos os dados relevantes
            resposta = f"📋 **Processo {processo_completo}**\n\n"
            
            # ✅ CORREÇÃO: Extrair categoria do processo_referencia (ex: VDM.0003/25 → VDM)
            categoria = 'N/A'
            if '.' in processo_completo:
                categoria = processo_completo.split('.')[0].upper()
            resposta += f"**Categoria:** {categoria}\n\n"
            
            # CE (Conhecimento de Embarque)
            ces = dados_processo.get('ces', [])
            if ces:
                resposta += "**📦 Conhecimento(s) de Embarque:**\n"
                for ce in ces:
                    numero_ce = ce.get('numero', 'N/A')
                    situacao_ce = ce.get('situacao_carga', ce.get('situacao_atual', 'N/A'))
                    porto_descarga = ce.get('porto_descarga', 'N/A')
                    resposta += f"  - CE {numero_ce}\n"
                    resposta += f"    - Situação: {situacao_ce}\n"
                    if porto_descarga and porto_descarga != 'N/A':
                        resposta += f"    - Porto de Descarga: {porto_descarga}\n"
                    
                    # ✅ CRÍTICO: Extrair e exibir valor de frete dos dados_completos (do SQL Server se disponível)
                    ce_dados_completos = ce.get('dados_completos', {})
                    if isinstance(ce_dados_completos, dict):
                        # Valor de frete (do SQL Server se disponível)
                        valor_frete_total = ce_dados_completos.get('valorFreteTotal') or ce_dados_completos.get('valor_frete_total')
                        if valor_frete_total:
                            resposta += f"    - 💰 Valor Frete Total: R$ {float(valor_frete_total):,.2f}\n"
                    
                    # ✅ NOVO: Extrair e exibir detalhes dos bloqueios do array bloqueio[]
                    dados_completos = ce.get('dados_completos', {})
                    if dados_completos and isinstance(dados_completos, dict):
                        bloqueios_array = dados_completos.get('bloqueio', [])
                        if isinstance(bloqueios_array, list) and len(bloqueios_array) > 0:
                            resposta += f"    - ⚠️ **Bloqueios Ativos:**\n"
                            for bloqueio in bloqueios_array:
                                if isinstance(bloqueio, dict):
                                    codigo_tipo = bloqueio.get('codigoTipo', '')
                                    descricao_tipo = bloqueio.get('descricaoTipo', '')
                                    motivo = bloqueio.get('motivo', '')
                                    data_bloqueio = bloqueio.get('data', '')
                                    justificativa = bloqueio.get('justificativa', '')
                                    
                                    # Formatar descrição do bloqueio
                                    bloqueio_desc = descricao_tipo if descricao_tipo else f'Bloqueio {codigo_tipo}' if codigo_tipo else 'Bloqueio'
                                    resposta += f"      • **{bloqueio_desc}**"
                                    if codigo_tipo:
                                        resposta += f" (Tipo: {codigo_tipo})"
                                    resposta += "\n"
                                    
                                    if motivo:
                                        resposta += f"        - Motivo: {motivo}\n"
                                    if justificativa:
                                        resposta += f"        - Justificativa: {justificativa}\n"
                                    if data_bloqueio:
                                        # Formatar data se possível
                                        try:
                                            from datetime import datetime
                                            if 'T' in data_bloqueio:
                                                dt = datetime.fromisoformat(data_bloqueio.replace('Z', '+00:00'))
                                                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                                                resposta += f"        - Data: {data_formatada}\n"
                                            else:
                                                resposta += f"        - Data: {data_bloqueio}\n"
                                        except:
                                            resposta += f"        - Data: {data_bloqueio}\n"
                        else:
                            # Fallback: verificar campos booleanos se array não estiver disponível
                            if ce.get('carga_bloqueada', False):
                                resposta += f"    - 🔒 Carga Bloqueada\n"
                            if ce.get('bloqueio_impede_despacho', False):
                                resposta += f"    - 🚫 Bloqueio Impede Despacho\n"
                    else:
                        # Fallback: verificar campos booleanos se dados_completos não estiver disponível
                        if ce.get('carga_bloqueada', False):
                            resposta += f"    - 🔒 Carga Bloqueada\n"
                        if ce.get('bloqueio_impede_despacho', False):
                            resposta += f"    - 🚫 Bloqueio Impede Despacho\n"
                    
                    # ✅ NOVO: Exibir informações dos containers (itens do CE)
                    # Prioridade 1: Usar dados já incluídos em ce.get('itens') (mais eficiente)
                    # Prioridade 2: Buscar do cache se não estiver nos dados
                    json_itens = None
                    itens_resumo = None
                    
                    if ce.get('itens'):
                        # Dados já estão disponíveis (vindos de obter_dados_documentos_processo)
                        json_itens = ce.get('itens', {})
                        itens_resumo = ce.get('itens_resumo', {})
                    else:
                        # Buscar do cache se não estiver nos dados
                        try:
                            from db_manager import buscar_ce_itens_cache
                            itens_ce = buscar_ce_itens_cache(numero_ce)
                            if itens_ce and itens_ce.get('json_itens_completo'):
                                json_itens = itens_ce.get('json_itens_completo', {})
                                itens_resumo = {
                                    'qtd_containers': len(json_itens.get('conteineres', [])),
                                    'qtd_cargas_soltas': len(json_itens.get('cargasSoltas', [])),
                                    'qtd_graneis': len(json_itens.get('graneis', []))
                                }
                        except Exception as e:
                            logger.debug(f'Erro ao buscar itens do CE {numero_ce}: {e}')
                    
                    # Exibir informações dos itens
                    if json_itens:
                        conteineres = json_itens.get('conteineres', [])
                        cargas_soltas = json_itens.get('cargasSoltas', [])
                        graneis = json_itens.get('graneis', [])
                        
                        if conteineres or cargas_soltas or graneis:
                            resposta += f"    - 📦 **Itens:**\n"
                            
                            # Containers
                            if conteineres:
                                resposta += f"      • **Containers:** {len(conteineres)}\n"
                                # Mostrar detalhes dos containers (até 5)
                                for container in conteineres[:5]:
                                    if isinstance(container, dict):
                                        identificacao = container.get('identificacao', '')
                                        tipo_conteiner = container.get('tipoConteiner', '')
                                        lacres = container.get('lacre', [])
                                        
                                        resposta += f"        - {identificacao}"
                                        if tipo_conteiner:
                                            resposta += f" ({tipo_conteiner})"
                                        resposta += "\n"
                                        
                                        if lacres and isinstance(lacres, list) and len(lacres) > 0:
                                            lacres_str = ', '.join(lacres[:3])  # Mostrar até 3 lacres
                                            if len(lacres) > 3:
                                                lacres_str += f" (+{len(lacres) - 3} mais)"
                                            resposta += f"          Lacres: {lacres_str}\n"
                                
                                if len(conteineres) > 5:
                                    resposta += f"        ... e mais {len(conteineres) - 5} container(es)\n"
                            
                            # Cargas Soltas
                            if cargas_soltas:
                                resposta += f"      • **Cargas Soltas:** {len(cargas_soltas)}\n"
                            
                            # Graneis
                            if graneis:
                                resposta += f"      • **Graneis:** {len(graneis)}\n"
                        else:
                            # Mostrar resumo mesmo sem itens (indica que ainda não foi consultado)
                            resposta += f"    - 📦 **Itens:** Não consultados ainda\n"
                            resposta += f"      💡 **Dica:** Os itens serão consultados automaticamente na próxima consulta do CE.\n"
                    
                resposta += "\n"
            
            # DI (Declaração de Importação)
            dis = dados_processo.get('dis', [])
            if dis:
                resposta += "**📄 Declaração(ões) de Importação:**\n"
                for di in dis:
                    numero_di = di.get('numero', 'N/A')
                    situacao_di = di.get('situacao_di', 'N/A')
                    canal = di.get('canal_selecao_parametrizada', 'N/A')
                    desembaraco = di.get('data_hora_desembaraco', '')
                    resposta += f"  - DI {numero_di}\n"
                    resposta += f"    - Situação: {situacao_di}\n"
                    if canal and canal != 'N/A':
                        resposta += f"    - Canal: {canal}\n"
                    if desembaraco:
                        resposta += f"    - Desembaraçado em: {desembaraco}\n"
                    
                    # ✅ CRÍTICO: Extrair e exibir valores de mercadoria, frete e impostos dos dados_completos
                    di_dados_completos = di.get('dados_completos', {})
                    
                    # ✅ NOVO: Se não tem dados_completos ou está incompleto, tentar enriquecer via SQL Server
                    precisa_enriquecer = False
                    if not di_dados_completos or not isinstance(di_dados_completos, dict):
                        precisa_enriquecer = True
                    else:
                        # Verificar se tem valores e impostos
                        tem_valores = bool(
                            di_dados_completos.get('valor_mercadoria_descarga_real') or 
                            di_dados_completos.get('real_VLMD') or
                            di_dados_completos.get('valor_mercadoria_embarque_real') or
                            di_dados_completos.get('real_VLME')
                        )
                        tem_impostos = bool(
                            di_dados_completos.get('pagamentos') or
                            di_dados_completos.get('tributos') or
                            di_dados_completos.get('valoresCalculados')
                        )
                        if not tem_valores or not tem_impostos:
                            precisa_enriquecer = True
                    
                    if precisa_enriquecer and numero_di and numero_di != 'N/A':
                        logger.info(f"🔍 [DI] Enriquecendo DI {numero_di} via SQL Server...")
                        try:
                            from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                            processo_consolidado = buscar_processo_consolidado_sql_server(processo_completo)
                            if processo_consolidado and processo_consolidado.get('di'):
                                di_enriquecida = processo_consolidado.get('di')
                                # Mesclar dados enriquecidos com dados existentes
                                if not di_dados_completos or not isinstance(di_dados_completos, dict):
                                    di_dados_completos = {}
                                
                                # Adicionar valores se não existirem
                                if not di_dados_completos.get('valor_mercadoria_descarga_real') and di_enriquecida.get('valor_mercadoria_descarga_real'):
                                    di_dados_completos['valor_mercadoria_descarga_real'] = di_enriquecida.get('valor_mercadoria_descarga_real')
                                if not di_dados_completos.get('valor_mercadoria_embarque_real') and di_enriquecida.get('valor_mercadoria_embarque_real'):
                                    di_dados_completos['valor_mercadoria_embarque_real'] = di_enriquecida.get('valor_mercadoria_embarque_real')
                                if not di_dados_completos.get('valor_mercadoria_descarga_dolar') and di_enriquecida.get('valor_mercadoria_descarga_dolar'):
                                    di_dados_completos['valor_mercadoria_descarga_dolar'] = di_enriquecida.get('valor_mercadoria_descarga_dolar')
                                if not di_dados_completos.get('valor_mercadoria_embarque_dolar') and di_enriquecida.get('valor_mercadoria_embarque_dolar'):
                                    di_dados_completos['valor_mercadoria_embarque_dolar'] = di_enriquecida.get('valor_mercadoria_embarque_dolar')
                                
                                # Adicionar impostos se não existirem
                                if not di_dados_completos.get('pagamentos') and di_enriquecida.get('pagamentos'):
                                    di_dados_completos['pagamentos'] = di_enriquecida.get('pagamentos')
                                
                                # Adicionar importador se não existir
                                if not di_dados_completos.get('nome_importador') and di_enriquecida.get('nome_importador'):
                                    di_dados_completos['nome_importador'] = di_enriquecida.get('nome_importador')
                                
                                # ✅ NOVO: Adicionar frete se não existir (conforme MAPEAMENTO_SQL_SERVER.md)
                                if not di_dados_completos.get('frete') and di_enriquecida.get('frete'):
                                    di_dados_completos['frete'] = di_enriquecida.get('frete')
                                
                                # ✅ NOVO: Adicionar transporte/navio se não existir
                                if not di_dados_completos.get('transporte') and di_enriquecida.get('transporte'):
                                    di_dados_completos['transporte'] = di_enriquecida.get('transporte')
                                
                                # ✅ NOVO: Adicionar CE relacionado se não existir (SEMPRE adicionar se encontrado)
                                if di_enriquecida.get('numero_ce'):
                                    di_dados_completos['numero_ce'] = di_enriquecida.get('numero_ce')
                                    logger.info(f"✅ [DI] numero_ce adicionado: {di_enriquecida.get('numero_ce')}")
                                
                                # ✅ NOVO: Adicionar dados completos do CE relacionado (processos antigos não estão no Kanban)
                                # SEMPRE adicionar se encontrado, mesmo que já exista (atualizar)
                                if di_enriquecida.get('ce_relacionado'):
                                    di_dados_completos['ce_relacionado'] = di_enriquecida.get('ce_relacionado')
                                    ce_num = di_enriquecida.get('ce_relacionado').get('numero') if isinstance(di_enriquecida.get('ce_relacionado'), dict) else 'N/A'
                                    logger.info(f"✅ [DI] ce_relacionado adicionado: {ce_num}")
                                
                                # ✅ CRÍTICO: Garantir que di também tenha ce_relacionado para busca posterior
                                if di_enriquecida.get('ce_relacionado'):
                                    di['ce_relacionado'] = di_enriquecida.get('ce_relacionado')
                                if di_enriquecida.get('numero_ce'):
                                    di['numero_ce'] = di_enriquecida.get('numero_ce')
                                
                                logger.info(f"✅ [DI] DI {numero_di} enriquecida com valores, impostos, frete, transporte e CE")
                        except Exception as e:
                            logger.error(f"❌ Erro ao enriquecer DI {numero_di}: {e}", exc_info=True)
                    
                    if isinstance(di_dados_completos, dict):
                        # Valores de mercadoria (do SQL Server se disponível)
                        valor_merc_descarga_real = di_dados_completos.get('valor_mercadoria_descarga_real') or di_dados_completos.get('real_VLMD')
                        valor_merc_embarque_real = di_dados_completos.get('valor_mercadoria_embarque_real') or di_dados_completos.get('real_VLME')
                        valor_merc_descarga_dolar = di_dados_completos.get('valor_mercadoria_descarga_dolar') or di_dados_completos.get('dollar_VLMLD')
                        valor_merc_embarque_dolar = di_dados_completos.get('valor_mercadoria_embarque_dolar') or di_dados_completos.get('dollar_VLME')
                        
                        if valor_merc_descarga_real:
                            resposta += f"    - 💰 Valor Mercadoria Descarga (BRL): R$ {float(valor_merc_descarga_real):,.2f}\n"
                        if valor_merc_embarque_real:
                            resposta += f"    - 💰 Valor Mercadoria Embarque (BRL): R$ {float(valor_merc_embarque_real):,.2f}\n"
                        if valor_merc_descarga_dolar:
                            resposta += f"    - 💰 Valor Mercadoria Descarga (USD): ${float(valor_merc_descarga_dolar):,.2f}\n"
                        if valor_merc_embarque_dolar:
                            resposta += f"    - 💰 Valor Mercadoria Embarque (USD): ${float(valor_merc_embarque_dolar):,.2f}\n"
                        
                        # ✅ NOVO: Frete da DI (conforme MAPEAMENTO_SQL_SERVER.md)
                        frete_di = di_dados_completos.get('frete') or di_dados_completos.get('frete_di')
                        if frete_di and isinstance(frete_di, dict):
                            valor_frete_real = frete_di.get('valor_total_reais')
                            valor_frete_dolar = frete_di.get('valor_total_dolares')
                            if valor_frete_real:
                                resposta += f"    - 💰 Frete (BRL): R$ {float(valor_frete_real):,.2f}\n"
                            if valor_frete_dolar:
                                resposta += f"    - 💰 Frete (USD): ${float(valor_frete_dolar):,.2f}\n"
                        
                        # ✅ NOVO: Transporte/Navio da DI (conforme MAPEAMENTO_SQL_SERVER.md)
                        transporte_di = di_dados_completos.get('transporte') or di.get('transporte')
                        if transporte_di and isinstance(transporte_di, dict):
                            nome_veiculo = transporte_di.get('nome_veiculo')
                            nome_navio = transporte_di.get('nome_navio')
                            nome_transportador = transporte_di.get('nome_transportador')
                            if nome_veiculo or nome_navio:
                                resposta += f"    - 🚢 Navio/Veículo: {nome_veiculo or nome_navio or 'N/A'}\n"
                            if nome_transportador:
                                resposta += f"    - 🚚 Transportador: {nome_transportador}\n"
                        
                        # ✅ NOVO: CE relacionado à DI (conforme MAPEAMENTO_SQL_SERVER.md)
                        # Buscar CE relacionado (pode vir de Di_Dados_Embarque ou via id_importacao)
                        # ✅ CRÍTICO: Buscar de múltiplas fontes para garantir que encontramos
                        numero_ce_di = (
                            di_dados_completos.get('numero_ce') or 
                            di.get('numero_ce') or
                            (di_dados_completos.get('ce_relacionado', {}).get('numero') if isinstance(di_dados_completos.get('ce_relacionado'), dict) else None) or
                            (di.get('ce_relacionado', {}).get('numero') if isinstance(di.get('ce_relacionado'), dict) else None)
                        )
                        ce_relacionado = (
                            di_dados_completos.get('ce_relacionado') or 
                            di.get('ce_relacionado')
                        )
                        
                        # ✅ DEBUG: Log para verificar se encontramos o CE relacionado
                        if numero_ce_di:
                            logger.info(f"✅ [DI] CE relacionado encontrado para DI {numero_di}: {numero_ce_di}")
                        else:
                            logger.debug(f"⚠️ [DI] CE relacionado NÃO encontrado para DI {numero_di}. di_dados_completos tem numero_ce: {bool(di_dados_completos.get('numero_ce'))}, di tem numero_ce: {bool(di.get('numero_ce'))}, ce_relacionado em di_dados_completos: {bool(di_dados_completos.get('ce_relacionado'))}, ce_relacionado em di: {bool(di.get('ce_relacionado'))}")
                        
                        # Se não encontrou, buscar do processo (mas processos antigos não estão no Kanban)
                        if not numero_ce_di:
                            # Tentar buscar do processo_dto se disponível (apenas para processos no Kanban)
                            if context and context.get('processo_dto'):
                                processo_dto = context.get('processo_dto')
                                numero_ce_di = processo_dto.numero_ce if hasattr(processo_dto, 'numero_ce') else None
                        
                        if numero_ce_di:
                            resposta += f"    - 📦 CE Relacionado: {numero_ce_di}\n"
                            # ✅ NOVO: Se temos dados completos do CE relacionado, exibir informações adicionais
                            if ce_relacionado and isinstance(ce_relacionado, dict):
                                situacao_ce = ce_relacionado.get('situacao')
                                porto_origem = ce_relacionado.get('porto_origem')
                                porto_destino = ce_relacionado.get('porto_destino')
                                valor_frete_ce = ce_relacionado.get('valor_frete_total')
                                if situacao_ce:
                                    resposta += f"      - Situação CE: {situacao_ce}\n"
                                if porto_origem:
                                    resposta += f"      - Porto Origem: {porto_origem}\n"
                                if porto_destino:
                                    resposta += f"      - Porto Destino: {porto_destino}\n"
                                if valor_frete_ce:
                                    try:
                                        valor_frete_float = float(str(valor_frete_ce).replace(',', '.'))
                                        resposta += f"      - 💰 Frete CE: R$ {valor_frete_float:,.2f}\n"
                                    except:
                                        resposta += f"      - 💰 Frete CE: {valor_frete_ce}\n"
                        
                        # ✅ CRÍTICO: Impostos/Pagamentos (prioridade para pagamentos do SQL Server)
                        pagamentos = di_dados_completos.get('pagamentos', [])
                        if pagamentos and isinstance(pagamentos, list) and len(pagamentos) > 0:
                            resposta += f"    - **Impostos Pagos:**\n"
                            total_impostos = 0
                            for pagamento in pagamentos:
                                if isinstance(pagamento, dict):
                                    tipo_imposto = pagamento.get('tipo', 'N/A')
                                    valor_pago = pagamento.get('valor', 0) or pagamento.get('valor_pago', 0) or 0
                                    data_pagamento = pagamento.get('data_pagamento', '') or pagamento.get('data', '')
                                    if valor_pago:
                                        total_impostos += float(valor_pago)
                                        data_str = f" (pago em {data_pagamento})" if data_pagamento else ""
                                        resposta += f"      • {tipo_imposto}: R$ {float(valor_pago):,.2f}{data_str}\n"
                            if total_impostos > 0:
                                resposta += f"      **Total Impostos: R$ {total_impostos:,.2f}**\n"
                        else:
                            # Fallback: tentar tributos calculados (DUIMP)
                            tributos = di_dados_completos.get('tributos') or di_dados_completos.get('valoresCalculados') or {}
                            if tributos:
                                tribs_calculados = tributos.get('tributosCalculados', [])
                                if tribs_calculados:
                                    resposta += f"    - **Impostos:**\n"
                                    total_impostos = 0
                                    for t in tribs_calculados:
                                        valores_brl = t.get('valoresBRL', {}) or {}
                                        valor_recolher = valores_brl.get('aRecolher', 0) or 0
                                        tipo_tributo = t.get('tipo', 'N/A')
                                        if valor_recolher:
                                            total_impostos += float(valor_recolher)
                                            resposta += f"      • {tipo_tributo}: R$ {float(valor_recolher):,.2f}\n"
                                    if total_impostos > 0:
                                        resposta += f"      **Total Impostos: R$ {total_impostos:,.2f}**\n"
                        
                        # Nome do importador (se disponível)
                        nome_importador = di_dados_completos.get('nome_importador')
                        if nome_importador:
                            resposta += f"    - 👤 Importador: {nome_importador}\n"
                    
                    resposta += "\n"
            
            # DUIMP - COM TODOS OS DADOS (IMPOSTOS, VALORES, ETC.)
            duimps = dados_processo.get('duimps', [])
            if duimps:
                resposta += "**📝 DUIMP(s):**\n"
                for duimp in duimps:
                    # ✅ CORREÇÃO: Extrair número da DUIMP corretamente
                    numero_duimp_str = duimp.get('numero', 'N/A')
                    # Se for string no formato "25BR00001928777 v1", extrair apenas o número
                    if isinstance(numero_duimp_str, str) and ' v' in numero_duimp_str:
                        numero_duimp_str = numero_duimp_str.split(' v')[0]
                    numero_duimp = duimp.get('numero_duimp', numero_duimp_str)
                    versao = duimp.get('versao_duimp', 'N/A')
                    situacao_duimp = duimp.get('situacao_duimp', 'N/A')
                    canal_duimp = duimp.get('canal_consolidado', 'N/A')
                    ambiente = duimp.get('ambiente', 'validacao')
                    
                    # ✅ NOVO: Se situação, canal ou impostos estão vazios, tentar enriquecer via SQL Server + SQLite
                    dados_completos = duimp.get('dados_completos', {})
                    precisa_enriquecer = (
                        (not situacao_duimp or situacao_duimp == 'N/A' or not canal_duimp or canal_duimp == 'N/A') or
                        (not dados_completos or not isinstance(dados_completos, dict) or not dados_completos.get('tributos'))
                    )
                    if precisa_enriquecer and numero_duimp and numero_duimp != 'N/A':
                        try:
                            from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                            processo_consolidado = buscar_processo_consolidado_sql_server(processo_completo)
                            if processo_consolidado and processo_consolidado.get('duimp'):
                                duimp_sql = processo_consolidado['duimp']
                                if not situacao_duimp or situacao_duimp == 'N/A':
                                    situacao_duimp = duimp_sql.get('situacao', situacao_duimp) or situacao_duimp
                                if not canal_duimp or canal_duimp == 'N/A':
                                    canal_duimp = duimp_sql.get('canal', canal_duimp) or canal_duimp
                        except Exception as e:
                            logger.debug(f'Erro ao enriquecer DUIMP {numero_duimp} via SQL Server: {e}')
                        
                        # Sempre tentar buscar payload completo do SQLite para ter impostos/valores
                        if not dados_completos or not isinstance(dados_completos, dict) or not dados_completos.get('tributos'):
                            try:
                                import sqlite3
                                from db_manager import get_db_connection
                                conn_duimp = get_db_connection()
                                conn_duimp.row_factory = sqlite3.Row
                                cursor_duimp = conn_duimp.cursor()
                                cursor_duimp.execute('''
                                    SELECT payload_completo
                                    FROM duimps
                                    WHERE numero = ? AND ambiente = 'producao'
                                    ORDER BY CAST(versao AS INTEGER) DESC
                                    LIMIT 1
                                ''', (numero_duimp,))
                                row_duimp = cursor_duimp.fetchone()
                                conn_duimp.close()
                                if row_duimp and row_duimp['payload_completo']:
                                    import json
                                    payload_parsed = json.loads(row_duimp['payload_completo']) if isinstance(row_duimp['payload_completo'], str) else row_duimp['payload_completo']
                                    if isinstance(payload_parsed, dict):
                                        dados_completos = payload_parsed
                                        # Se ainda não tem situação/canal, extrair do payload
                                        if (not situacao_duimp or situacao_duimp == 'N/A') and payload_parsed.get('situacao', {}).get('situacaoDuimp'):
                                            situacao_duimp = payload_parsed['situacao']['situacaoDuimp']
                                        if (not canal_duimp or canal_duimp == 'N/A') and payload_parsed.get('resultadoAnaliseRisco', {}).get('canalConsolidado'):
                                            canal_duimp = payload_parsed['resultadoAnaliseRisco']['canalConsolidado']
                            except Exception as e:
                                logger.debug(f'Erro ao buscar payload completo da DUIMP {numero_duimp}: {e}')
                    
                    resposta += f"  - DUIMP {numero_duimp} v{versao} ({ambiente})\n"
                    resposta += f"    - Situação: {situacao_duimp if situacao_duimp and situacao_duimp != 'N/A' else 'N/A'}\n"
                    if canal_duimp and canal_duimp != 'N/A':
                        resposta += f"    - Canal: {canal_duimp}\n"
                    
                    # ✅ EXTRAIR E MOSTRAR IMPOSTOS E VALORES DOS dados_completos (usar o enriquecido se disponível)
                    # dados_completos já foi enriquecido acima se estava vazio
                    if dados_completos and isinstance(dados_completos, dict):
                        # Valores Calculados / Tributos
                        vc = dados_completos.get('tributos') or dados_completos.get('valoresCalculados') or {}
                        if vc:
                            mercadoria_vc = vc.get('mercadoria', {})
                            if mercadoria_vc:
                                valor_fob_usd = mercadoria_vc.get('valorTotalLocalEmbarqueUSD', 0) or 0
                                valor_fob_brl = mercadoria_vc.get('valorTotalLocalEmbarqueBRL', 0) or 0
                                if valor_fob_usd or valor_fob_brl:
                                    resposta += f"    - Valor FOB (USD): {valor_fob_usd:,.2f}\n" if valor_fob_usd else ""
                                    resposta += f"    - Valor FOB (BRL): R$ {valor_fob_brl:,.2f}\n" if valor_fob_brl else ""
                            
                            # Impostos/Tributos Calculados
                            tribs = vc.get('tributosCalculados', [])
                            if tribs:
                                resposta += f"    - **Impostos:**\n"
                                total_impostos = 0
                                for t in tribs:
                                    valores_brl = t.get('valoresBRL', {}) or {}
                                    valor_recolher = valores_brl.get('aRecolher', 0) or 0
                                    tipo_tributo = t.get('tipo', 'N/A')
                                    if valor_recolher:
                                        total_impostos += float(valor_recolher)
                                        resposta += f"      • {tipo_tributo}: R$ {float(valor_recolher):,.2f}\n"
                                if total_impostos > 0:
                                    resposta += f"      **Total Impostos: R$ {total_impostos:,.2f}**\n"
                        
                        # Carga / Valores (Frete, Seguro)
                        carga = dados_completos.get('carga', {})
                        if carga:
                            frete = carga.get('frete', {}) or {}
                            if frete:
                                moeda_frete = frete.get('codigoMoedaNegociada', '')
                                valor_frete = frete.get('valorMoedaNegociada', 0) or 0
                                if valor_frete:
                                    resposta += f"    - Frete ({moeda_frete}): {valor_frete:,.2f}\n"
                            
                            seguro = carga.get('seguro', {}) or {}
                            if seguro:
                                moeda_seguro = seguro.get('codigoMoedaNegociada', '')
                                valor_seguro = seguro.get('valorMoedaNegociada', 0) or 0
                                if valor_seguro:
                                    resposta += f"    - Seguro ({moeda_seguro}): {valor_seguro:,.2f}\n"
                resposta += "\n"
            
            # ETA e porto (ShipsGo)
            shipsgo = dados_processo.get('shipsgo', {})
            if shipsgo:
                eta = shipsgo.get('eta', 'N/A')
                porto = shipsgo.get('porto', 'N/A')
                if eta and eta != 'N/A':
                    resposta += f"**⏱️ ETA:** {eta}\n"
                if porto and porto != 'N/A':
                    resposta += f"**🏭 Porto:** {porto}\n"
                resposta += "\n"

            # ✅ Melhor UX: se o processo tem ETA/porto/navio no DTO (Kanban/SQL Server), também mostrar aqui.
            # Isso cobre casos onde `dados_processo['shipsgo']` não vem preenchido.
            try:
                if getattr(processo_dto, "eta_iso", None):
                    eta_val = getattr(processo_dto, "eta_iso")
                    try:
                        from datetime import datetime
                        if isinstance(eta_val, datetime):
                            eta_txt = eta_val.strftime("%d/%m/%Y")
                        else:
                            eta_txt = str(eta_val)
                    except Exception:
                        eta_txt = str(eta_val)

                    resposta += "**📅 Previsão de Chegada (ETA):**\n"
                    resposta += f"  - ETA: {eta_txt}\n"
                    if getattr(processo_dto, "porto_nome", None):
                        resposta += f"  - Porto: {processo_dto.porto_nome}\n"
                    if getattr(processo_dto, "nome_navio", None):
                        resposta += f"  - Navio: {processo_dto.nome_navio}\n"
                    if getattr(processo_dto, "status_shipsgo", None):
                        resposta += f"  - Status: {processo_dto.status_shipsgo}\n"
                    resposta += "\n"
            except Exception:
                pass
            
            # Pendências e alertas
            alertas = dados_processo.get('alertas', [])
            if alertas:
                resposta += "**⚠️ Alertas:**\n"
                for alerta in alertas[:5]:  # Mostrar até 5 alertas
                    tipo = alerta.get('tipo', 'N/A')
                    mensagem = alerta.get('mensagem', 'N/A')
                    resposta += f"  - {tipo}: {mensagem}\n"
                resposta += "\n"

            # ✅ CRÍTICO: sempre tentar anexar impostos já gravados (ex.: CONCILIACAO_BANCARIA)
            # e AFRMM pago, mesmo quando o processo veio do Kanban "capado".
            try:
                tmp = {'sucesso': True, 'resposta': resposta}
                tmp = self._enriquecer_resposta_status_financeiro(
                    tmp,
                    processo_referencia=processo_completo,
                    processo_dto=processo_dto,
                )
                if isinstance(tmp, dict) and isinstance(tmp.get('resposta'), str):
                    resposta = tmp.get('resposta') or resposta
            except Exception:
                pass
            
            # ✅ CRÍTICO: Verificar se a resposta tem documentos antes de retornar
            # Se só tem categoria, não retornar - continuar buscando ou informar que não há documentos
            tem_ce_na_resposta = 'CE' in resposta or 'Conhecimento de Embarque' in resposta or '📦' in resposta
            tem_di_na_resposta = 'DI' in resposta or 'Declaração de Importação' in resposta or '📄' in resposta
            tem_duimp_na_resposta = 'DUIMP' in resposta or '📝' in resposta
            tem_documentos_na_resposta = tem_ce_na_resposta or tem_di_na_resposta or tem_duimp_na_resposta
            
            # ✅ NOVO: Verificar se a resposta tem outras informações relevantes (etapa, modal, transporte, ETA, pendências)
            tem_etapa_kanban = 'Etapa no Kanban' in resposta or 'etapaKanban' in resposta
            tem_modal = 'Modal:' in resposta
            tem_transporte = 'Transporte' in resposta or '🚚' in resposta or 'BL/House' in resposta
            tem_eta = 'ETA' in resposta or 'Previsão de Chegada' in resposta or '📅' in resposta
            tem_pendencias = 'Pendências' in resposta or '⚠️' in resposta or 'Pendente' in resposta
            tem_outras_informacoes = tem_etapa_kanban or tem_modal or tem_transporte or tem_eta or tem_pendencias
            
            # Verificar se só tem categoria (sem documentos E sem outras informações)
            linhas_resposta = [l.strip() for l in resposta.split('\n') if l.strip()]
            tem_apenas_categoria = len(linhas_resposta) <= 3 and any('Categoria:' in l for l in linhas_resposta) and not tem_documentos_na_resposta and not tem_outras_informacoes
            
            # ✅ CORREÇÃO: Só tentar buscar do SQL Server se realmente não tem informações E SQL Server está disponível
            if (tem_apenas_categoria or (not tem_documentos_na_resposta and not tem_outras_informacoes and len(resposta.strip()) < 200)):
                # ✅ NOVO: Verificar se SQL Server está disponível antes de tentar buscar (evita timeout)
                sql_server_disponivel = False
                try:
                    from utils.sql_server_adapter import get_sql_adapter
                    sql_adapter = get_sql_adapter()
                    if sql_adapter:
                        result = sql_adapter.execute_query("SELECT 1 AS test", notificar_erro=False)
                        sql_server_disponivel = result.get('success', False) if result else False
                except Exception as e:
                    logger.debug(f"⚠️ SQL Server não disponível: {e}")
                    sql_server_disponivel = False
                
                if sql_server_disponivel:
                    logger.warning(f"⚠️ [FALLBACK] Resposta só tem categoria ou não tem documentos. Buscando do SQL Server...")
                    # Tentar buscar do SQL Server uma última vez
                    try:
                        from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                        processo_consolidado = buscar_processo_consolidado_sql_server(processo_completo)
                        if processo_consolidado:
                            ce_data = processo_consolidado.get('ce')
                            di_data = processo_consolidado.get('di')
                            if (ce_data and ce_data.get('numero')) or (di_data and di_data.get('numero')):
                                # Tem documentos no SQL Server, formatar resposta completa
                                logger.info(f"✅ [FALLBACK] Encontrou documentos no SQL Server, formatando resposta completa...")
                                resposta = f"📋 **Processo {processo_completo}**\n\n"
                                resposta += f"**Categoria:** {categoria}\n\n"
                                
                                if ce_data and ce_data.get('numero'):
                                    resposta += f"**📦 Conhecimento de Embarque:**\n"
                                    resposta += f"  - CE {ce_data.get('numero')}\n"
                                    if ce_data.get('situacao'):
                                        resposta += f"  - Situação: {ce_data.get('situacao')}\n"
                                    if ce_data.get('valor_frete_total'):
                                        resposta += f"  - 💰 Valor Frete Total: R$ {float(ce_data.get('valor_frete_total', 0)):,.2f}\n"
                                    resposta += "\n"
                                
                                if di_data and di_data.get('numero'):
                                    resposta += f"**📄 Declaração de Importação:**\n"
                                    resposta += f"  - DI {di_data.get('numero')}\n"
                                    if di_data.get('situacao') or di_data.get('situacao_di'):
                                        resposta += f"  - Situação: {di_data.get('situacao') or di_data.get('situacao_di')}\n"
                                    if di_data.get('canal'):
                                        resposta += f"  - Canal: {di_data.get('canal')}\n"
                                    if di_data.get('data_desembaraco'):
                                        resposta += f"  - Data Desembaraço: {di_data.get('data_desembaraco')}\n"
                                    if di_data.get('situacao_entrega'):
                                        resposta += f"  - Situação Entrega: {di_data.get('situacao_entrega')}\n"
                                    
                                    # ✅ CRÍTICO: Valores de mercadoria
                                    if di_data.get('valor_mercadoria_descarga_real'):
                                        resposta += f"  - 💰 Valor Mercadoria Descarga (BRL): R$ {float(di_data.get('valor_mercadoria_descarga_real', 0)):,.2f}\n"
                                    if di_data.get('valor_mercadoria_embarque_real'):
                                        resposta += f"  - 💰 Valor Mercadoria Embarque (BRL): R$ {float(di_data.get('valor_mercadoria_embarque_real', 0)):,.2f}\n"
                                    if di_data.get('valor_mercadoria_descarga_dolar'):
                                        resposta += f"  - 💰 Valor Mercadoria Descarga (USD): ${float(di_data.get('valor_mercadoria_descarga_dolar', 0)):,.2f}\n"
                                    if di_data.get('valor_mercadoria_embarque_dolar'):
                                        resposta += f"  - 💰 Valor Mercadoria Embarque (USD): ${float(di_data.get('valor_mercadoria_embarque_dolar', 0)):,.2f}\n"
                                    
                                    if di_data.get('nome_importador'):
                                        resposta += f"  - 👤 Importador: {di_data.get('nome_importador')}\n"
                                    
                                    # ✅ CRÍTICO: Impostos/Pagamentos
                                    pagamentos = di_data.get('pagamentos', [])
                                    if pagamentos and isinstance(pagamentos, list) and len(pagamentos) > 0:
                                        resposta += f"  - **Impostos Pagos:**\n"
                                        total_impostos = 0
                                        for pagamento in pagamentos:
                                            if isinstance(pagamento, dict):
                                                tipo_imposto = pagamento.get('tipo', 'N/A')
                                                valor_pago = pagamento.get('valor', 0) or pagamento.get('valor_pago', 0) or 0
                                                data_pagamento = pagamento.get('data', '') or pagamento.get('data_pagamento', '')
                                                if valor_pago:
                                                    total_impostos += float(valor_pago)
                                                    data_str = f" (pago em {data_pagamento})" if data_pagamento else ""
                                                    resposta += f"    • {tipo_imposto}: R$ {float(valor_pago):,.2f}{data_str}\n"
                                        if total_impostos > 0:
                                            resposta += f"    **Total Impostos: R$ {total_impostos:,.2f}**\n"
                                    
                                    resposta += "\n"
                                
                                return {
                                    'sucesso': True,
                                    'resposta': resposta,
                                    'dados': dados_processo
                                }
                    except Exception as e:
                        logger.error(f"❌ Erro ao buscar do SQL Server no final: {e}", exc_info=True)
                else:
                    # SQL Server offline - retornar resposta atual mesmo sem documentos (pode ter outras informações)
                    logger.info(f"✅ [FALLBACK] SQL Server offline, retornando resposta atual (pode ter outras informações além de documentos)")
                    # Se a resposta já tem informações (etapa, modal, transporte, ETA, etc.), retornar como está
                    if tem_outras_informacoes:
                        return {
                            'sucesso': True,
                            'resposta': resposta,
                            'dados': dados_processo
                        }
                
                # Se chegou aqui, não encontrou documentos em lugar nenhum E não tem outras informações
                # Mas ainda assim, tentar buscar dados básicos do cache antes de retornar mensagem genérica
                if not tem_outras_informacoes:
                    # Tentar buscar dados básicos do processo do cache (etapa, modal, ETA, etc.)
                    try:
                        from db_manager import get_db_connection
                        import sqlite3
                        conn = get_db_connection()
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT processo_referencia, etapa_kanban, modal, eta_iso, porto_nome, nome_navio, 
                                   situacao_ce, numero_ce, numero_di, numero_duimp, dados_completos_json, bl_house
                            FROM processos_kanban
                            WHERE processo_referencia = ?
                        ''', (processo_completo,))
                        row = cursor.fetchone()
                        conn.close()
                        
                        if row:
                            # Processo encontrado no cache - formatar resposta com dados disponíveis
                            resposta = f"📋 **Processo {processo_completo}**\n\n"
                            resposta += f"**Categoria:** {categoria}\n\n"
                            
                            if row['etapa_kanban']:
                                resposta += f"**Etapa no Kanban:** {row['etapa_kanban']}\n"
                            if row['modal']:
                                resposta += f"**Modal:** {row['modal']}\n"
                            resposta += "\n"
                            
                            # Transporte
                            bl_house = row.get('bl_house') or ''
                            if bl_house or row.get('dados_completos_json'):
                                resposta += "**🚚 Transporte:**\n"
                                if bl_house:
                                    resposta += f"  - BL/House: {bl_house}\n"
                                resposta += "\n"
                            
                            # ETA
                            if row['eta_iso']:
                                resposta += "**📅 Previsão de Chegada (ETA):**\n"
                                resposta += f"  - ETA: {row['eta_iso']}\n"
                                if row['porto_nome']:
                                    resposta += f"  - Porto: {row['porto_nome']}\n"
                                if row['nome_navio']:
                                    resposta += f"  - Navio: {row['nome_navio']}\n"
                                resposta += "\n"
                            
                            # Pendências (se houver)
                            if row.get('dados_completos_json'):
                                try:
                                    import json
                                    dados_json = json.loads(row['dados_completos_json'])
                                    if dados_json.get('pendenciaIcms') == 'Pendente':
                                        resposta += "**⚠️ Pendências:**\n"
                                        resposta += "  - ICMS: Pendente\n"
                                        resposta += "\n"
                                except:
                                    pass
                            
                            # Documentos (se houver)
                            if not row['numero_ce'] and not row['numero_di'] and not row['numero_duimp']:
                                resposta += "⚠️ **Nenhum documento encontrado** (CE, DI ou DUIMP) para este processo.\n\n"
                                resposta += "💡 **Dicas:**\n"
                                resposta += "- O processo pode não ter documentos registrados ainda\n"
                                resposta += "- Verifique se o número do processo está correto\n"
                                resposta += "- O processo pode estar em uma etapa anterior ao registro de documentos"
                            
                            return {
                                'sucesso': True,
                                'resposta': resposta,
                                'dados': dados_processo
                            }
                    except Exception as e:
                        logger.debug(f"Erro ao buscar dados básicos do cache: {e}")
                
                # Se chegou aqui, não encontrou processo em lugar nenhum
                resposta = f"📋 **Processo {processo_completo}**\n\n"
                resposta += f"**Categoria:** {categoria}\n\n"
                resposta += "⚠️ **Nenhum documento encontrado** (CE, DI ou DUIMP) para este processo.\n\n"
                resposta += "💡 **Dicas:**\n"
                resposta += "- O processo pode não ter documentos registrados ainda\n"
                resposta += "- Verifique se o número do processo está correto\n"
                resposta += "- O processo pode estar em uma etapa anterior ao registro de documentos"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': dados_processo
            }
        except Exception as e:
            logger.error(f'Erro ao consultar status do processo: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao consultar processo: {str(e)}'
            }
    
    def _listar_por_categoria(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos filtrados por categoria.
        
        ✅ MELHORIA: Usa as mesmas funções do dashboard "o que temos hoje" para ter a mesma riqueza de informações.
        
        ⚠️ CRÍTICO: NÃO delegar para chat_service._executar_funcao_tool pois isso causa recursão infinita
        (chat_service -> ToolRouter -> ProcessoAgent -> chat_service -> ...)
        Usar implementação própria diretamente.
        """
        categoria = arguments.get('categoria', '').strip().upper()
        limite = arguments.get('limite', 200)  # ✅ Usar limite padrão maior como na implementação antiga
        forcar_eta_futuro = arguments.get('forcar_eta_futuro', False)
        
        if not categoria:
            return {
                'sucesso': False,
                'erro': 'categoria é obrigatória',
                'resposta': '❌ Categoria é obrigatória.'
            }
        
        try:
            # ✅ MELHORIA: Usar as mesmas funções do dashboard para ter a mesma riqueza de informações
            from db_manager import (
                obter_processos_chegando_hoje,
                obter_processos_prontos_registro,
                obter_pendencias_ativas,
                obter_duimps_em_analise,
                obter_dis_em_analise,
                obter_processos_eta_alterado,
                obter_alertas_recentes,
                listar_processos_em_dta,
                listar_processos_liberados_registro  # ✅ NOVO: Para processos que chegaram sem DI/DUIMP (não apenas hoje)
            )
            
            logger.info(f'🔍 listar_processos_por_categoria: Buscando processos {categoria} usando funções do dashboard')
            
            # ✅ Buscar dados usando as mesmas funções do dashboard, mas formatar como relatório geral
            # ✅ CORREÇÃO: Usar listar_processos_liberados_registro para processos que chegaram sem DI/DUIMP (TODOS, não apenas hoje)
            processos_chegados_sem_docs = listar_processos_liberados_registro(categoria=categoria, dias_retroativos=None, limit=200)
            processos_chegando = obter_processos_chegando_hoje(categoria=categoria)  # Apenas os que chegam hoje
            processos_prontos = obter_processos_prontos_registro(categoria=categoria)  # Prontos para registro (chegaram sem docs)
            processos_em_dta = listar_processos_em_dta(categoria=categoria)
            pendencias = obter_pendencias_ativas(categoria=categoria)
            duimps_analise = obter_duimps_em_analise(categoria=categoria)
            dis_analise = obter_dis_em_analise(categoria=categoria)
            eta_alterado = obter_processos_eta_alterado(categoria=categoria)
            alertas = obter_alertas_recentes(limite=10, categoria=categoria)
            
            # ✅ Formatar como relatório geral "como estão os X?" (não "o que temos pra hoje")
            # ✅ CORREÇÃO: Passar processos_chegados_sem_docs (todos que chegaram sem DI/DUIMP) em vez de apenas processos_chegando (hoje)
            resposta = self._formatar_relatorio_geral_categoria(
                processos_chegados_sem_docs,  # ✅ TODOS os processos que chegaram sem DI/DUIMP (não apenas hoje)
                processos_prontos,
                processos_em_dta,
                pendencias,
                duimps_analise,
                dis_analise,
                eta_alterado,
                alertas,
                categoria
            )
            
            # ✅ NOVO: Salvar relatório no contexto para uso em emails
            try:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                from datetime import datetime
                session_id_para_salvar = context.get('session_id') if context else None
                if session_id_para_salvar:
                    relatorio = criar_relatorio_gerado(
                        tipo_relatorio='como_estao_categoria',
                        texto_chat=resposta,
                        categoria=categoria,
                        filtros={
                            'data_ref': datetime.now().strftime('%Y-%m-%d')
                        },
                        meta_json={
                            'total_chegados_sem_docs': len(processos_chegados_sem_docs),
                            'total_prontos': len(processos_prontos),
                            'total_em_dta': len(processos_em_dta),
                            'total_pendencias': len(pendencias),
                            'total_duimps': len(duimps_analise),
                            'total_dis': len(dis_analise),
                            'total_eta_alterado': len(eta_alterado)
                        }
                    )
                    salvar_ultimo_relatorio(session_id_para_salvar, relatorio)
            except Exception as e:
                logger.debug(f'Erro ao salvar relatório no contexto: {e}')
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos_chegando) + len(processos_prontos) + len(pendencias),
                'categoria': categoria
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos por categoria {categoria}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar processos da categoria {categoria}: {str(e)}'
            }
    
    def _listar_por_situacao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos filtrados por situação."""
        categoria = arguments.get('categoria', '').strip().upper()
        situacao = arguments.get('situacao', '').strip().lower()
        limite = arguments.get('limite', 200)
        
        if not categoria:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Categoria é obrigatória (ex: ALH, VDM, MSS)'
            }
        
        try:
            from db_manager import listar_processos_por_categoria_e_situacao
            
            logger.info(f'🔍 _listar_por_situacao: Buscando processos {categoria} com situação {situacao} (limite={limite})')
            
            processos = listar_processos_por_categoria_e_situacao(categoria, situacao_filtro=situacao, limit=limite)
            
            logger.info(f'🔍 _listar_por_situacao: Encontrados {len(processos)} processos {categoria} com situação {situacao}')
            
            if not processos:
                # Verificar se pelo menos existe algum processo dessa categoria no banco (mesmo sem documentos)
                try:
                    logger.debug(f'🔍 listar_processos_por_categoria: Nenhum processo com documentos encontrado, verificando se existem processos {categoria} sem documentos...')
                    processos_refs = listar_processos_por_categoria(categoria, limit=10)
                    logger.debug(f'🔍 listar_processos_por_categoria: Encontrados {len(processos_refs)} processos {categoria} no total (com ou sem documentos)')
                    
                    if processos_refs:
                        # Existe pelo menos um processo, mas não tem documentos vinculados
                        resposta = f"📋 **Processos {categoria} encontrados, mas sem documentos vinculados**\n\n"
                        resposta += f"Processos encontrados:\n"
                        for proc_ref in processos_refs[:10]:  # Mostrar até 10
                            resposta += f"- {proc_ref}\n"
                        if len(processos_refs) > 10:
                            resposta += f"- ... e mais {len(processos_refs) - 10} processo(s)\n"
                        resposta += f"\n💡 **Dica:** Estes processos existem mas não têm CE, CCT, DI ou DUIMP vinculados ainda."
                    else:
                        # Não existe nenhum processo dessa categoria
                        logger.warning(f'⚠️ listar_processos_por_categoria: Nenhum processo da categoria {categoria} encontrado (nem com documentos, nem sem documentos)')
                        resposta = f"⚠️ **Nenhum processo da categoria {categoria} encontrado.**\n\n"
                        resposta += f"💡 **Dica:** Verifique se a categoria está correta. "
                        resposta += f"Exemplos de categorias válidas: ALH, VDM, MSS, BND, DMD, GYM, SLL, MV5, etc.\n\n"
                        resposta += f"Se você digitou errado, tente novamente com a categoria correta."
                    
                    # ✅ GARANTIR: Sempre retornar resposta mesmo se não encontrou processos
                    logger.info(f'✅ listar_processos_por_categoria: Retornando resposta para categoria {categoria} (tamanho: {len(resposta)})')
                except Exception as e:
                    logger.error(f'❌ Erro ao verificar processos da categoria {categoria}: {e}', exc_info=True)
                    resposta = f"⚠️ **Nenhum processo da categoria {categoria} com documentos encontrado.**\n\n"
                    resposta += f"💡 **Dica:** Verifique se a categoria está correta. "
                    resposta += f"Exemplos de categorias válidas: ALH, VDM, MSS, BND, DMD, MV5, etc."
            else:
                # ✅ NOVO: Aplicar filtros para mostrar apenas processos que precisam de atenção
                # Organizados em 4 fases: Chegou sem docs, Tem ETA sem docs, Em desembaraço, Desembaracado com pendências
                
                from datetime import datetime, date
                import json
                
                hoje = date.today()
                
                def parse_date(date_str):
                    if not date_str:
                        return None
                    try:
                        if isinstance(date_str, str):
                            # Tentar diferentes formatos
                            date_clean = date_str.split('T')[0].split(' ')[0]
                            return datetime.strptime(date_clean, "%Y-%m-%d").date()
                        return None
                    except:
                        return None
                
                def obter_data_chegada(dados_json):
                    """
                    Retorna data de chegada confirmada da carga ao porto (NÃO ETA, NÃO entrega ao cliente).
                    
                    ⚠️ CONTEXTO DE DESPACHO ADUANEIRO:
                    - Chegada = navio/carga chegou ao porto (dataDestinoFinal) - PRIMEIRO passo
                    - Armazenamento = carga foi armazenada (dataArmazenamento) - SEGUNDO passo
                    - Entrega = entrega ao cliente final (dataEntrega) - ÚLTIMO passo (já saiu do escopo do despacho)
                    
                    ⚠️ IMPORTANTE: Esta função retorna apenas datas CONFIRMADAS de chegada ao porto.
                    NUNCA retorna ETA (previsão) como se fosse data de chegada confirmada.
                    NUNCA retorna dataEntrega (é entrega ao cliente, não chegada ao porto).
                    
                    Ordem de prioridade (para processos ATIVOS que o despacho cuida):
                    1. dataDestinoFinal - Data de chegada da carga ao porto (mais confiável para chegada)
                    2. dataArmazenamento - Data de armazenamento (confirma que chegou e foi armazenada)
                    3. dataAtracamento - Data da atracação do navio (se atracou, carga chegou - exceto sinistros raros)
                    4. containerDetailsCe.[].operacaoData - Data da operação do container
                    
                    ⚠️ NÃO usar dataSituacaoCargaCe - é data de mudança de status do CE (manifestada→armazenada→vinculada),
                    não é data de chegada da carga.
                    """
                    # ✅ Prioridade 1: Data de destino final (chegada da carga ao porto)
                    if dados_json.get('dataDestinoFinal'):
                        data = parse_date(str(dados_json['dataDestinoFinal']))
                        if data:
                            return data
                    
                    # ✅ Prioridade 2: Data de armazenamento (confirma que chegou e foi armazenada)
                    if dados_json.get('dataArmazenamento'):
                        data = parse_date(str(dados_json['dataArmazenamento']))
                        if data:
                            return data
                    
                    # ✅ Prioridade 3: Data de atracação (se navio atracou, carga chegou - exceto sinistros raros)
                    if dados_json.get('dataAtracamento'):
                        data = parse_date(str(dados_json['dataAtracamento']))
                        if data:
                            return data
                    
                    # ✅ Prioridade 4: Data da operação do container
                    container_details = dados_json.get('containerDetailsCe', [])
                    if container_details and isinstance(container_details, list):
                        for container in container_details:
                            if container.get('operacaoData'):
                                data = parse_date(str(container['operacaoData']))
                                if data:
                                    return data
                    
                    # ✅ Prioridade 6: Data de chegada efetiva (para modal aéreo - CCT)
                    if dados_json.get('dataHoraChegadaEfetiva'):
                        data = parse_date(str(dados_json['dataHoraChegadaEfetiva']))
                        if data:
                            return data
                    
                    # ✅ Prioridade 7: Data de chegada genérica (se disponível)
                    if dados_json.get('dataChegada'):
                        data = parse_date(str(dados_json['dataChegada']))
                        if data:
                            return data
                    
                    # ⚠️ NUNCA usar ETA como data de chegada confirmada!
                    # ⚠️ NUNCA usar dataEntrega (é entrega ao cliente, não chegada ao porto)!
                    # Se não encontrou nenhuma data confirmada de chegada ao porto, retornar None
                    return None
                
                def obter_eta(dados_json):
                    """Retorna ETA (previsão de chegada)"""
                    # Tentar múltiplos campos para ETA
                    eta = dados_json.get('dataPrevisaoChegada') or dados_json.get('data_previsao_chegada')
                    if eta:
                        eta_parsed = parse_date(eta)
                        if eta_parsed:
                            # Normalizar para datetime com hora 00:00:00 para comparação
                            if isinstance(eta_parsed, date) and not isinstance(eta_parsed, datetime):
                                return datetime.combine(eta_parsed, datetime.min.time())
                            return eta_parsed
                    
                    # Tentar do shipgov2
                    shipgov2 = dados_json.get('shipgov2', {})
                    if isinstance(shipgov2, dict):
                        eta = shipgov2.get('destino_data_chegada')
                        if eta:
                            eta_parsed = parse_date(eta)
                            if eta_parsed:
                                # Normalizar para datetime com hora 00:00:00 para comparação
                                if isinstance(eta_parsed, date) and not isinstance(eta_parsed, datetime):
                                    return datetime.combine(eta_parsed, datetime.min.time())
                                return eta_parsed
                    
                    return None
                
                def esta_desembaracado(di, duimp):
                    """Verifica se DI ou DUIMP está desembaracada"""
                    if di:
                        situacao_di = di.get('situacao', '') or ''
                        if 'desembarac' in situacao_di.lower():
                            return True
                    if duimp:
                        situacao_duimp = duimp.get('situacao', '') or ''
                        if 'desembarac' in situacao_duimp.lower():
                            return True
                    return False
                
                def ce_ou_cct_entregue(ce, cct):
                    """Verifica se CE ou CCT está com status ENTREGUE"""
                    if ce:
                        situacao_ce = (ce.get('situacao', '') or '').upper()
                        if 'ENTREGUE' in situacao_ce:
                            return True
                    if cct:
                        situacao_cct = (cct.get('situacao', '') or '').upper()
                        if 'ENTREGUE' in situacao_cct:
                            return True
                    return False
                
                # ✅ FUNÇÕES AUXILIARES: Validação de DI/DUIMP
                def tem_di_valida(di_dict):
                    """Verifica se DI é válida (não vazia, não '/ -', etc)"""
                    if not di_dict:
                        return False
                    # Verificar múltiplos campos possíveis
                    numero_di = (di_dict.get('numero') or di_dict.get('numero_di') or '').strip()
                    if not numero_di or numero_di in ['', '/ -', '/-', '-', 'None', 'null', 'NULL']:
                        return False
                    # Verificar se não é apenas espaços ou caracteres especiais
                    if len(numero_di.replace('/', '').replace('-', '').replace(' ', '').strip()) == 0:
                        return False
                    return True
                
                def tem_duimp_valida(duimp_dict):
                    """Verifica se DUIMP é válida (não vazia, etc)"""
                    if not duimp_dict:
                        return False
                    # Verificar múltiplos campos possíveis
                    numero_duimp = (duimp_dict.get('numero') or duimp_dict.get('numero_duimp') or '').strip()
                    if not numero_duimp or numero_duimp in ['', '/ -', '/-', '-', 'None', 'null', 'NULL']:
                        return False
                    # Verificar se não é apenas espaços ou caracteres especiais
                    if len(numero_duimp.replace('/', '').replace('-', '').replace(' ', '').strip()) == 0:
                        return False
                    return True
                
                # Buscar dados completos do Kanban para cada processo
                processos_categorizados = {
                    'chegaram_sem_docs': [],
                    'tem_eta_sem_docs': [],
                    'em_desembaraco': [],
                    'desembaracado_com_pendencias': []
                }
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    di = proc.get('di')
                    duimp = proc.get('duimp')
                    ce = proc.get('ce')
                    cct = proc.get('cct')
                    
                    # Buscar dados completos do Kanban
                    processo_dto = None  # ✅ NOVO: Inicializar processo_dto
                    try:
                        from services.processo_repository import ProcessoRepository
                        repositorio = ProcessoRepository()
                        processo_dto = repositorio.buscar_por_referencia(proc_ref)
                        
                        if processo_dto:
                            # Usar dados_completos do DTO (é um dict)
                            dados_json = processo_dto.dados_completos if processo_dto.dados_completos else {}
                            
                            # Se não tem dados_completos, tentar buscar direto do SQLite
                            if not dados_json:
                                try:
                                    from db_manager import get_db_connection
                                    conn = get_db_connection()
                                    cursor = conn.cursor()
                                    cursor.execute('''
                                        SELECT dados_completos_json
                                        FROM processos_kanban
                                        WHERE processo_referencia = ?
                                    ''', (proc_ref,))
                                    row = cursor.fetchone()
                                    conn.close()
                                    if row and row[0]:
                                        dados_json = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                                except:
                                    dados_json = {}
                        else:
                            dados_json = {}
                    except Exception as e:
                        logger.debug(f'Erro ao buscar dados completos do processo {proc_ref}: {e}')
                        dados_json = {}
                    
                    # Verificar documentos usando funções auxiliares
                    tem_di = tem_di_valida(di)
                    tem_duimp = tem_duimp_valida(duimp)
                    
                    # Verificar chegada
                    data_chegada = obter_data_chegada(dados_json)
                    eta = obter_eta(dados_json)
                    chegou = data_chegada and data_chegada <= hoje
                    
                    # Verificar se está desembaracado
                    desembaracado = esta_desembaracado(di, duimp)
                    
                    # Verificar se está entregue
                    entregue = ce_ou_cct_entregue(ce, cct)
                    
                    # Excluir processos entregues
                    if entregue:
                        continue
                    
                    # Verificar pendências (só se não estiver entregue)
                    pendencia_icms = dados_json.get('pendenciaIcms') == 'Pendente'
                    pendencia_frete = (ce and ce.get('pendencia_frete')) or (cct and cct.get('pendencia_frete')) or False
                    situacao_entrega = dados_json.get('situacaoEntregaCarga') or ''
                    
                    if not pendencia_icms and 'ICMS' in situacao_entrega.upper() and 'NAO AUTORIZADA' in situacao_entrega.upper():
                        pendencia_icms = True
                    
                    # CATEGORIZAR
                    
                    # Verificar se é processo aguardando embarque (sem DI/DUIMP, sem ETA, sem CE/CCT, sem data chegada)
                    if not tem_di and not tem_duimp and not eta and not chegou and not ce and not cct:
                        continue  # Não listar (aguardando embarque)
                    
                    # FASE 1A: Chegou sem DI/DUIMP
                    if chegou and not tem_di and not tem_duimp:
                        # ✅ NOVO: Verificar se tem DTA
                        numero_dta = None
                        if processo_dto and processo_dto.numero_dta:
                            numero_dta = processo_dto.numero_dta
                        elif dados_json:
                            # Tentar buscar do JSON se não estiver no DTO
                            documento_despacho = dados_json.get('documentoDespacho')
                            numero_documento_despacho = dados_json.get('numeroDocumentoDespacho')
                            if documento_despacho == 'DTA' and numero_documento_despacho:
                                numero_dta = numero_documento_despacho
                        
                        # ✅ NOVO: Verificar se tem LPCO
                        numero_lpco = None
                        situacao_lpco = None
                        if processo_dto and processo_dto.numero_lpco:
                            # Se DTO tem LPCO, usar do DTO
                            numero_lpco = processo_dto.numero_lpco
                            situacao_lpco = processo_dto.situacao_lpco
                        elif dados_json:
                            # Se DTO não tem LPCO ou não existe, tentar buscar do JSON
                            lpco_details = dados_json.get('lpcoDetails', [])
                            if lpco_details and isinstance(lpco_details, list) and len(lpco_details) > 0:
                                primeiro_lpco = lpco_details[0]
                                if isinstance(primeiro_lpco, dict):
                                    numero_lpco = primeiro_lpco.get('LPCO')
                                    situacao_lpco = primeiro_lpco.get('situacao')
                        
                        processos_categorizados['chegaram_sem_docs'].append({
                            'processo': proc,
                            'dados_json': dados_json,
                            'data_chegada': data_chegada,
                            'ce': ce,
                            'cct': cct,
                            'numero_dta': numero_dta,  # ✅ NOVO: Incluir DTA
                            'numero_lpco': numero_lpco,  # ✅ NOVO: Incluir LPCO
                            'situacao_lpco': situacao_lpco  # ✅ NOVO: Incluir situação LPCO
                        })
                    
                    # FASE 1B: Tem ETA FUTURO mas sem DI/DUIMP
                    # ✅ CORREÇÃO: Apenas incluir se ETA for FUTURO (chegando), não passado
                    elif eta and not tem_di and not tem_duimp:
                        # ✅ VALIDAÇÃO: Normalizar ETA e hoje para comparação
                        # Converter ETA para datetime se for date
                        eta_datetime = eta
                        if isinstance(eta, date) and not isinstance(eta, datetime):
                            eta_datetime = datetime.combine(eta, datetime.min.time())
                        elif isinstance(eta, datetime):
                            eta_datetime = eta
                        
                        # Converter hoje para datetime se for date
                        hoje_datetime = hoje
                        if isinstance(hoje, date) and not isinstance(hoje, datetime):
                            hoje_datetime = datetime.combine(hoje, datetime.min.time())
                        elif isinstance(hoje, datetime):
                            hoje_datetime = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
                        
                        # ✅ VALIDAÇÃO: ETA deve ser >= hoje (futuro) para estar "chegando"
                        # Se ETA já passou, não está "chegando", pode ter chegado ou estar atrasado
                        # Comparar apenas as datas (sem hora)
                        eta_date_only = eta_datetime.date() if isinstance(eta_datetime, datetime) else eta_datetime
                        hoje_date_only = hoje_datetime.date() if isinstance(hoje_datetime, datetime) else hoje_datetime
                        if eta_date_only >= hoje_date_only:
                            # ETA futuro = realmente chegando
                            # ✅ NOVO: Verificar se tem DTA
                            numero_dta = None
                            if processo_dto and processo_dto.numero_dta:
                                numero_dta = processo_dto.numero_dta
                            elif dados_json:
                                # Tentar buscar do JSON se não estiver no DTO
                                documento_despacho = dados_json.get('documentoDespacho')
                                numero_documento_despacho = dados_json.get('numeroDocumentoDespacho')
                                if documento_despacho == 'DTA' and numero_documento_despacho:
                                    numero_dta = numero_documento_despacho
                            
                            # ✅ NOVO: Verificar se tem LPCO
                            numero_lpco = None
                            situacao_lpco = None
                            if processo_dto and processo_dto.numero_lpco:
                                # Se DTO tem LPCO, usar do DTO
                                numero_lpco = processo_dto.numero_lpco
                                situacao_lpco = processo_dto.situacao_lpco
                            elif dados_json:
                                # Se DTO não tem LPCO ou não existe, tentar buscar do JSON
                                lpco_details = dados_json.get('lpcoDetails', [])
                                if lpco_details and isinstance(lpco_details, list) and len(lpco_details) > 0:
                                    primeiro_lpco = lpco_details[0]
                                    if isinstance(primeiro_lpco, dict):
                                        numero_lpco = primeiro_lpco.get('LPCO')
                                        situacao_lpco = primeiro_lpco.get('situacao')
                            
                            processos_categorizados['tem_eta_sem_docs'].append({
                                'processo': proc,
                                'dados_json': dados_json,
                                'eta': eta,
                                'data_chegada': data_chegada,
                                'ce': ce,
                                'cct': cct,
                                'numero_dta': numero_dta,  # ✅ NOVO: Incluir DTA
                                'numero_lpco': numero_lpco,  # ✅ NOVO: Incluir LPCO
                                'situacao_lpco': situacao_lpco  # ✅ NOVO: Incluir situação LPCO
                            })
                        # Se ETA passou mas não tem data de chegada confirmada, pode ter chegado sem confirmação
                        # ou estar atrasado - por enquanto, não incluir em nenhuma categoria (aguardando dados)
                        else:
                            eta_str = eta_datetime.strftime("%d/%m/%Y") if isinstance(eta_datetime, datetime) else str(eta)
                            logger.debug(f'⚠️ Processo {proc_ref}: ETA {eta_str} já passou mas sem data de chegada confirmada - não incluindo em "chegando"')
                    
                    # FASE 2: Tem DI/DUIMP e CE/CCT mas não desembaracou
                    elif (tem_di or tem_duimp) and (ce or cct or data_chegada) and not desembaracado:
                        processos_categorizados['em_desembaraco'].append({
                            'processo': proc,
                            'di': di,
                            'duimp': duimp,
                            'ce': ce,
                            'cct': cct
                        })
                    
                    # FASE 3: Desembaracou mas tem pendências (e não está entregue)
                    elif desembaracado and (pendencia_icms or pendencia_frete):
                        pendencias = []
                        if pendencia_icms:
                            pendencias.append('ICMS')
                        if pendencia_frete:
                            pendencias.append('Frete')
                        
                        processos_categorizados['desembaracado_com_pendencias'].append({
                            'processo': proc,
                            'di': di,
                            'duimp': duimp,
                            'ce': ce,
                            'cct': cct,
                            'pendencias': pendencias
                        })
                
                # Formatar resposta
                total_filtrado = (
                    len(processos_categorizados['chegaram_sem_docs']) +
                    len(processos_categorizados['tem_eta_sem_docs']) +
                    len(processos_categorizados['em_desembaraco']) +
                    len(processos_categorizados['desembaracado_com_pendencias'])
                )
                
                if total_filtrado == 0:
                    # ✅ MELHORIA: Mostrar processos encontrados com mais detalhes, similar ao dashboard
                    # Incluir processos que chegaram e processos com ETA futuro
                    total_processos = len(processos)
                    resposta = f"📋 **Processos {categoria} - Status Geral**\n\n"
                    resposta += f"📊 **Total verificado: {total_processos} processo(s)**\n\n"
                    
                    # Inicializar listas antes do if
                    processos_chegados = []
                    processos_com_eta = []
                    processos_finalizados = []
                    
                    if total_processos > 0:
                        # Buscar processos que chegaram e processos com ETA futuro
                        
                        for proc in processos:
                            proc_ref = proc.get('processo_referencia', '')
                            di = proc.get('di')
                            duimp = proc.get('duimp')
                            ce = proc.get('ce')
                            cct = proc.get('cct')
                            
                            # Buscar dados completos do Kanban
                            dados_json = {}
                            processo_dto = None
                            try:
                                from services.processo_repository import ProcessoRepository
                                repositorio = ProcessoRepository()
                                processo_dto = repositorio.buscar_por_referencia(proc_ref)
                                if processo_dto:
                                    dados_json = processo_dto.dados_completos if processo_dto.dados_completos else {}
                                    # ✅ Se dados_completos está vazio, tentar buscar do SQLite
                                    if not dados_json:
                                        try:
                                            from db_manager import get_db_connection
                                            conn = get_db_connection()
                                            cursor = conn.cursor()
                                            cursor.execute('''
                                                SELECT dados_completos_json
                                                FROM processos_kanban
                                                WHERE processo_referencia = ?
                                            ''', (proc_ref,))
                                            row = cursor.fetchone()
                                            conn.close()
                                            if row and row[0]:
                                                dados_json = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                                        except:
                                            pass
                            except Exception as e:
                                logger.debug(f'Erro ao buscar dados completos do processo {proc_ref}: {e}')
                            
                            # ✅ CORREÇÃO: Usar dados do DTO diretamente se disponível
                            # Verificar chegada e ETA
                            data_chegada = None
                            eta = None
                            
                            # Tentar obter data de chegada do DTO primeiro
                            if processo_dto:
                                if processo_dto.data_destino_final:
                                    try:
                                        if isinstance(processo_dto.data_destino_final, str):
                                            data_chegada = parse_date(processo_dto.data_destino_final)
                                        else:
                                            data_chegada = processo_dto.data_destino_final.date() if hasattr(processo_dto.data_destino_final, 'date') else processo_dto.data_destino_final
                                    except:
                                        pass
                                
                                if processo_dto.eta_iso:
                                    try:
                                        if isinstance(processo_dto.eta_iso, str):
                                            eta = parse_date(processo_dto.eta_iso)
                                        else:
                                            eta = processo_dto.eta_iso.date() if hasattr(processo_dto.eta_iso, 'date') else processo_dto.eta_iso
                                    except:
                                        pass
                            
                            # Se não encontrou no DTO, tentar do JSON
                            if not data_chegada:
                                data_chegada = obter_data_chegada(dados_json)
                            if not eta:
                                eta = obter_eta(dados_json)
                            chegou = data_chegada and data_chegada <= hoje
                            
                            # Verificar se está finalizado
                            desembaracado = esta_desembaracado(di, duimp)
                            entregue = ce_ou_cct_entregue(ce, cct)
                            
                            # Buscar informações do DTO primeiro, depois do JSON (para todas as categorias)
                            porto_nome = ''
                            modal = ''
                            situacao_ce = ''
                            nome_navio = ''
                            if processo_dto:
                                porto_nome = processo_dto.porto_nome or ''
                                modal = processo_dto.modal or ''
                                situacao_ce = processo_dto.situacao_ce or ''
                                nome_navio = processo_dto.nome_navio or ''
                            
                            # Se não encontrou no DTO, buscar do JSON
                            if not porto_nome:
                                porto_nome = dados_json.get('portoNome') or dados_json.get('porto_nome') or ''
                            if not modal:
                                modal = dados_json.get('modal') or ''
                            if not situacao_ce:
                                situacao_ce = dados_json.get('situacaoCargaCe') or dados_json.get('situacao_ce') or ''
                            if not nome_navio:
                                nome_navio = dados_json.get('nomeNavio') or dados_json.get('nome_navio') or ''
                            
                            # ✅ CORREÇÃO: Priorizar chegada sobre status finalizado
                            # Se chegou, mostrar em "CHEGARAM" (mesmo que esteja desembaracado)
                            if chegou:
                                processos_chegados.append({
                                    'proc': proc,
                                    'proc_ref': proc_ref,
                                    'data_chegada': data_chegada,
                                    'di': di,
                                    'duimp': duimp,
                                    'dados_json': dados_json,
                                    'porto_nome': porto_nome,
                                    'modal': modal,
                                    'situacao_ce': situacao_ce,
                                    'desembaracado': desembaracado,
                                    'entregue': entregue
                                })
                            elif eta:
                                # Verificar se ETA é futuro
                                eta_datetime = eta
                                if isinstance(eta, date) and not isinstance(eta, datetime):
                                    eta_datetime = datetime.combine(eta, datetime.min.time())
                                eta_date_only = eta_datetime.date() if isinstance(eta_datetime, datetime) else eta_datetime
                                hoje_date_only = hoje
                                if eta_date_only >= hoje_date_only:
                                    processos_com_eta.append({
                                        'proc': proc,
                                        'proc_ref': proc_ref,
                                        'eta': eta,
                                        'dados_json': dados_json,
                                        'porto_nome': porto_nome,
                                        'modal': modal,
                                        'nome_navio': nome_navio
                                    })
                                else:
                                    # ETA passado mas não chegou - adicionar a finalizados
                                    processos_finalizados.append({
                                        'proc': proc,
                                        'proc_ref': proc_ref,
                                        'di': di,
                                        'duimp': duimp,
                                        'dados_json': dados_json,
                                        'porto_nome': porto_nome,
                                        'modal': modal,
                                        'situacao_ce': situacao_ce,
                                        'desembaracado': desembaracado,
                                        'entregue': entregue,
                                        'eta': eta
                                    })
                            else:
                                # ✅ CORREÇÃO: Todos os outros processos vão para finalizados (mesmo sem estar desembaracado/entregue)
                                # Isso garante que todos os processos sejam mostrados
                                processos_finalizados.append({
                                    'proc': proc,
                                    'proc_ref': proc_ref,
                                    'di': di,
                                    'duimp': duimp,
                                    'dados_json': dados_json,
                                    'porto_nome': porto_nome,
                                    'modal': modal,
                                    'situacao_ce': situacao_ce,
                                    'desembaracado': desembaracado,
                                    'entregue': entregue
                                })
                        
                        # Mostrar processos que chegaram
                        if processos_chegados:
                            resposta += f"✅ **CHEGARAM** ({len(processos_chegados)} processo(s)):\n\n"
                            for item in processos_chegados[:20]:  # Limitar a 20
                                proc_ref = item['proc_ref']
                                data_chegada = item['data_chegada']
                                di = item['di']
                                duimp = item['duimp']
                                porto_nome = item['porto_nome']
                                modal = item['modal']
                                situacao_ce = item['situacao_ce']
                                desembaracado = item.get('desembaracado', False)
                                entregue = item.get('entregue', False)
                                
                                data_str = data_chegada.strftime("%d/%m/%Y") if data_chegada else "N/A"
                                
                                linha = f"  • **{proc_ref}**"
                                if porto_nome:
                                    linha += f" - Porto: {porto_nome}"
                                if modal:
                                    linha += f" - Modal: {modal}"
                                linha += f" - Chegou: {data_str}"
                                if situacao_ce:
                                    linha += f" - Status CE: {situacao_ce}"
                                
                                # Verificar documentos
                                tem_di = tem_di_valida(di)
                                tem_duimp = tem_duimp_valida(duimp)
                                if tem_di:
                                    numero_di = di.get('numero') or di.get('numero_di') or 'N/A'
                                    situacao_di = di.get('situacao', '')
                                    linha += f" - DI: {numero_di}"
                                    if desembaracado:
                                        linha += f" ({situacao_di})"
                                elif tem_duimp:
                                    numero_duimp = duimp.get('numero') or duimp.get('numero_duimp') or 'N/A'
                                    situacao_duimp = duimp.get('situacao', '')
                                    linha += f" - DUIMP: {numero_duimp}"
                                    if desembaracado:
                                        linha += f" ({situacao_duimp})"
                                else:
                                    linha += " - ⚠️ Sem DI/DUIMP"
                                
                                # Adicionar status final se aplicável
                                if entregue:
                                    linha += " - ✅ ENTREGUE"
                                elif desembaracado:
                                    linha += " - ✅ DESEMBARACADO"
                                
                                resposta += linha + "\n"
                            if len(processos_chegados) > 20:
                                resposta += f"  • ... e mais {len(processos_chegados) - 20} processo(s)\n"
                            resposta += "\n"
                        
                        # Mostrar processos com ETA futuro
                        if processos_com_eta:
                            resposta += f"📅 **COM ETA (SEM CHEGADA AINDA)** ({len(processos_com_eta)} processo(s)):\n\n"
                            for item in processos_com_eta[:20]:  # Limitar a 20
                                proc_ref = item['proc_ref']
                                eta = item['eta']
                                porto_nome = item['porto_nome']
                                modal = item['modal']
                                nome_navio = item['nome_navio']
                                
                                eta_str = eta.strftime("%d/%m/%Y") if eta else "N/A"
                                
                                linha = f"  • **{proc_ref}**"
                                if porto_nome:
                                    linha += f" - Porto: {porto_nome}"
                                if modal:
                                    linha += f" - Modal: {modal}"
                                if nome_navio:
                                    linha += f" - Navio: {nome_navio}"
                                linha += f" - ETA: {eta_str}"
                                
                                resposta += linha + "\n"
                            if len(processos_com_eta) > 20:
                                resposta += f"  • ... e mais {len(processos_com_eta) - 20} processo(s)\n"
                            resposta += "\n"
                        
                        # Mostrar processos finalizados (resumo)
                        if processos_finalizados:
                            resposta += f"📋 **OUTROS PROCESSOS** ({len(processos_finalizados)} processo(s)):\n\n"
                            for item in processos_finalizados[:20]:  # Limitar a 20
                                proc_ref = item['proc_ref']
                                di = item['di']
                                duimp = item['duimp']
                                porto_nome = item.get('porto_nome', '')
                                modal = item.get('modal', '')
                                situacao_ce = item.get('situacao_ce', '')
                                desembaracado = item.get('desembaracado', False)
                                entregue = item.get('entregue', False)
                                eta = item.get('eta')
                                
                                linha = f"  • **{proc_ref}**"
                                
                                # Adicionar informações adicionais
                                if porto_nome:
                                    linha += f" - Porto: {porto_nome}"
                                if modal:
                                    linha += f" - Modal: {modal}"
                                
                                # Adicionar ETA se disponível
                                if eta:
                                    try:
                                        if isinstance(eta, date) or isinstance(eta, datetime):
                                            eta_str = eta.strftime("%d/%m/%Y") if hasattr(eta, 'strftime') else str(eta)
                                        else:
                                            eta_str = str(eta)
                                        linha += f" - ETA: {eta_str}"
                                    except:
                                        pass
                                
                                # Verificar documentos
                                tem_di = tem_di_valida(di)
                                tem_duimp = tem_duimp_valida(duimp)
                                if tem_di:
                                    numero_di = di.get('numero') or di.get('numero_di') or 'N/A'
                                    situacao_di = di.get('situacao', '')
                                    linha += f" - DI: {numero_di}"
                                    if situacao_di:
                                        linha += f" ({situacao_di})"
                                elif tem_duimp:
                                    numero_duimp = duimp.get('numero') or duimp.get('numero_duimp') or 'N/A'
                                    situacao_duimp = duimp.get('situacao', '')
                                    linha += f" - DUIMP: {numero_duimp}"
                                    if situacao_duimp:
                                        linha += f" ({situacao_duimp})"
                                else:
                                    linha += " - ⚠️ Sem DI/DUIMP"
                                
                                # Adicionar status final
                                if entregue:
                                    linha += " - ✅ ENTREGUE"
                                elif desembaracado:
                                    linha += " - ✅ DESEMBARACADO"
                                elif situacao_ce:
                                    linha += f" - Status CE: {situacao_ce}"
                                
                                resposta += linha + "\n"
                            if len(processos_finalizados) > 20:
                                resposta += f"  • ... e mais {len(processos_finalizados) - 20} processo(s)\n"
                            resposta += "\n"
                    
                    resposta += "✅ **Resumo:**\n"
                    if processos_chegados:
                        resposta += f"  - {len(processos_chegados)} processo(s) chegaram\n"
                    if processos_com_eta:
                        resposta += f"  - {len(processos_com_eta)} processo(s) com ETA (sem chegada ainda)\n"
                    if processos_finalizados:
                        resposta += f"  - {len(processos_finalizados)} processo(s) finalizados\n"
                    if not processos_chegados and not processos_com_eta and not processos_finalizados:
                        resposta += "  - Nenhum processo encontrado com informações completas\n"
                else:
                    resposta = f"📋 **Processos {categoria} que Precisam de Atenção** ({total_filtrado} processo(s))\n\n"
                    resposta += "=" * 80 + "\n\n"
                    
                    # FASE 1A: Chegaram sem documentos
                    if processos_categorizados['chegaram_sem_docs']:
                        resposta += "🆕 **CHEGARAM MAS SEM DI/DUIMP:**\n\n"
                        for item in processos_categorizados['chegaram_sem_docs']:
                            proc = item['processo']
                            proc_ref = proc.get('processo_referencia', '')
                            data_chegada = item['data_chegada']
                            ce = item['ce']
                            cct = item['cct']
                            numero_dta = item.get('numero_dta')  # ✅ NOVO: Obter DTA
                            numero_lpco = item.get('numero_lpco')  # ✅ NOVO: Obter LPCO
                            situacao_lpco = item.get('situacao_lpco')  # ✅ NOVO: Obter situação LPCO
                            
                            data_str = data_chegada.strftime("%d/%m/%Y") if data_chegada else "N/A"
                            ce_str = ""
                            if ce:
                                situacao_ce = ce.get('situacao', 'N/A')
                                ce_str = f" (CE: {ce.get('numero', 'N/A')} - {situacao_ce})"
                            elif cct:
                                situacao_cct = cct.get('situacao', 'N/A')
                                ce_str = f" (CCT: {cct.get('numero', 'N/A')} - {situacao_cct})"
                            
                            # ✅ NOVO: Adicionar informação de DTA na linha
                            # ⚠️ REGRA: Só mostrar DTA se NÃO tiver DI nem DUIMP (DI/DUIMP prevalece)
                            dta_str = ""
                            # Esta categoria já é "chegaram_sem_docs", então não tem DI nem DUIMP, pode mostrar DTA
                            if numero_dta:
                                dta_str = f" 🚚 DTA: {numero_dta}"
                            
                            # ✅ NOVO: Adicionar informação de LPCO na linha
                            lpco_str = ""
                            if numero_lpco:
                                lpco_str = f" 📋 LPCO: {numero_lpco}"
                                # Adicionar status se for "deferida" (case-insensitive)
                                if situacao_lpco and 'deferid' in situacao_lpco.lower():
                                    lpco_str += " (deferida)"
                            
                            resposta += f"  **{proc_ref}**\n"
                            resposta += f"    ✅ Chegou: {data_str}{ce_str}{dta_str}{lpco_str}\n"
                            resposta += f"    ⚠️ Sem DI e sem DUIMP\n"
                            resposta += f"    💡 Ação: Registrar DI ou DUIMP\n\n"
                    
                    # FASE 1B: Tem ETA sem documentos
                    if processos_categorizados['tem_eta_sem_docs']:
                        resposta += "📅 **CHEGANDO (TEM ETA) MAS SEM DI/DUIMP:**\n\n"
                        for item in processos_categorizados['tem_eta_sem_docs']:
                            proc = item['processo']
                            proc_ref = proc.get('processo_referencia', '')
                            eta = item['eta']
                            data_chegada = item['data_chegada']
                            ce = item['ce']
                            cct = item['cct']
                            numero_dta = item.get('numero_dta')  # ✅ NOVO: Obter DTA
                            numero_lpco = item.get('numero_lpco')  # ✅ NOVO: Obter LPCO
                            situacao_lpco = item.get('situacao_lpco')  # ✅ NOVO: Obter situação LPCO
                            
                            eta_str = eta.strftime("%d/%m/%Y") if eta else "N/A"
                            
                            # ✅ NOVO: Adicionar informação de DTA na linha
                            dta_str = ""
                            if numero_dta:
                                dta_str = f" 🚚 DTA: {numero_dta}"
                            
                            # ✅ NOVO: Adicionar informação de LPCO na linha
                            lpco_str = ""
                            if numero_lpco:
                                lpco_str = f" 📋 LPCO: {numero_lpco}"
                                # Adicionar status se for "deferida" (case-insensitive)
                                if situacao_lpco and 'deferid' in situacao_lpco.lower():
                                    lpco_str += " (deferida)"
                            
                            resposta += f"  **{proc_ref}**\n"
                            if data_chegada:
                                chegada_str = data_chegada.strftime("%d/%m/%Y")
                                resposta += f"    ✅ Chegada confirmada: {chegada_str}{dta_str}{lpco_str}\n"
                            else:
                                resposta += f"    📅 ETA: {eta_str}{dta_str}{lpco_str}\n"
                            
                            if ce:
                                situacao_ce = ce.get('situacao', 'N/A')
                                resposta += f"    📦 CE: {ce.get('numero', 'N/A')} ({situacao_ce})\n"
                            elif cct:
                                situacao_cct = cct.get('situacao', 'N/A')
                                resposta += f"    ✈️ CCT: {cct.get('numero', 'N/A')} ({situacao_cct})\n"
                            
                            resposta += f"    ⚠️ Sem DI e sem DUIMP\n"
                            resposta += f"    💡 Ação: Registrar DI ou DUIMP quando chegar\n\n"
                        
                    
                    # FASE 2: Em processo de desembaraço
                    if processos_categorizados['em_desembaraco']:
                        resposta += "⏳ **EM PROCESSO DE DESEMBARACO:**\n\n"
                        for item in processos_categorizados['em_desembaraco']:
                            proc = item['processo']
                            proc_ref = proc.get('processo_referencia', '')
                            di = item['di']
                            duimp = item['duimp']
                            ce = item['ce']
                            cct = item['cct']
                            
                            resposta += f"  **{proc_ref}**\n"
                            
                            # ✅ CORREÇÃO: Usar a mesma função de validação
                            if tem_di_valida(di):
                                situacao = di.get('situacao', 'N/A')
                                canal = di.get('canal', '')
                                canal_str = f" (Canal: {canal})" if canal else ""
                                numero_di_display = di.get('numero') or di.get('numero_di') or 'N/A'
                                resposta += f"    📄 DI: {numero_di_display} ({situacao}){canal_str}\n"
                            
                            if tem_duimp_valida(duimp):
                                situacao = duimp.get('situacao', 'N/A')
                                canal = duimp.get('canal', '')
                                canal_str = f" (Canal: {canal})" if canal else ""
                                numero_duimp_display = duimp.get('numero') or duimp.get('numero_duimp') or 'N/A'
                                resposta += f"    📋 DUIMP: {numero_duimp_display} v{duimp.get('versao', 'N/A')} ({situacao}){canal_str}\n"
                            
                            if ce:
                                resposta += f"    📦 CE: {ce.get('numero', 'N/A')}\n"
                            elif cct:
                                resposta += f"    ✈️ CCT: {cct.get('numero', 'N/A')}\n"
                            
                            resposta += f"    💡 Ação: Aguardar desembaraço\n\n"
                        
                    
                    # FASE 3: Desembaracado com pendências
                    if processos_categorizados['desembaracado_com_pendencias']:
                        resposta += "⚠️ **DESEMBARACADOS MAS COM PENDÊNCIAS FINAIS:**\n\n"
                        for item in processos_categorizados['desembaracado_com_pendencias']:
                            proc = item['processo']
                            proc_ref = proc.get('processo_referencia', '')
                            di = item['di']
                            duimp = item['duimp']
                            ce = item['ce']
                            cct = item['cct']
                            pendencias = item['pendencias']
                            
                            resposta += f"  **{proc_ref}**\n"
                            
                            if di:
                                resposta += f"    📄 DI: {di.get('numero', 'N/A')} (desembaracada)\n"
                            
                            if duimp:
                                resposta += f"    📋 DUIMP: {duimp.get('numero', 'N/A')} (desembaracada)\n"
                            
                            if ce:
                                resposta += f"    📦 CE: {ce.get('numero', 'N/A')}\n"
                            elif cct:
                                resposta += f"    ✈️ CCT: {cct.get('numero', 'N/A')}\n"
                            
                            pendencias_str = ', '.join(pendencias) if pendencias else 'N/A'
                            resposta += f"    ⚠️ Pendências: {pendencias_str}\n"
                            resposta += f"    💡 Ação: Resolver pendências para retirar carga\n\n"
                        
                    
                    resposta += "=" * 80 + "\n\n"
                    resposta += "✅ **Resumo:**\n"
                    resposta += f"  • {len(processos_categorizados['chegaram_sem_docs'])} processo(s) chegaram sem documentos\n"
                    resposta += f"  • {len(processos_categorizados['tem_eta_sem_docs'])} processo(s) chegando (tem ETA) sem documentos\n"
                    resposta += f"  • {len(processos_categorizados['em_desembaraco'])} processo(s) em processo de desembaraço\n"
                    resposta += f"  • {len(processos_categorizados['desembaracado_com_pendencias'])} processo(s) desembaracados com pendências\n"
                    resposta += f"  • **Total: {total_filtrado} processo(s) precisando de atenção**"
            
            # Determinar total para retorno
            total_retorno = total_filtrado if 'total_filtrado' in locals() else len(processos) if processos else 0
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': total_retorno,
                'categoria': categoria
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos por categoria {categoria}: {e}')
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar processos da categoria {categoria}: {str(e)}'
            }
    
    def _listar_por_situacao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos filtrados por situação."""
        categoria = arguments.get('categoria', '').strip().upper()
        situacao = arguments.get('situacao', '').strip().lower()
        limite = arguments.get('limite', 200)
        
        if not categoria:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'resposta': '❌ Categoria é obrigatória (ex: ALH, VDM, MSS)'
            }
        
        try:
            from db_manager import listar_processos_por_categoria_e_situacao
            
            logger.info(f'🔍 _listar_por_situacao: Buscando processos {categoria} com situação {situacao} (limite={limite})')
            
            processos = listar_processos_por_categoria_e_situacao(categoria, situacao_filtro=situacao, limit=limite)
            
            logger.info(f'🔍 _listar_por_situacao: Encontrados {len(processos)} processos {categoria} com situação {situacao}')
            
            if not processos:
                resposta = f"⚠️ **Nenhum processo {categoria} com situação '{situacao}' encontrado.**\n\n"
                resposta += f"💡 **Dica:** Verifique se:\n"
                resposta += f"- A categoria está correta (ex: ALH, VDM, MSS, BND, MV5, etc.)\n"
                resposta += f"- A situação está correta (ex: di_desembaracada, registrado, entregue)\n"
                resposta += f"- Existem processos desta categoria no sistema\n"
            else:
                # Determinar título baseado na situação
                titulo_situacao = situacao.replace('_', ' ').title()
                resposta = f"📋 **Processos {categoria} - {titulo_situacao}** ({len(processos)} processo(s))\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    resposta += f"**{proc_ref}**\n"
                    
                    # DI
                    di = proc.get('di')
                    if di:
                        situacao_di = di.get('situacao', '')
                        canal_di = di.get('canal', '')
                        data_desembaraco = di.get('data_desembaraco', '')
                        
                        resposta += f"   📄 DI {di.get('numero', 'N/A')}: {situacao_di.lower() if situacao_di else 'N/A'}"
                        
                        # ✅ Sempre mostrar canal se disponível
                        if canal_di:
                            resposta += f" (Canal: {canal_di})"
                        resposta += "\n"
                        
                        # ✅ Sempre mostrar data de desembaraço se disponível
                        if data_desembaraco:
                            try:
                                from datetime import datetime
                                # Tentar múltiplos formatos de data
                                data_limpa = str(data_desembaraco).replace('Z', '').replace('+00:00', '').strip()
                                # Remover microsegundos se existirem
                                if '.' in data_limpa:
                                    data_limpa = data_limpa.split('.')[0]
                                
                                # Tentar parsear
                                dt = None
                                if 'T' in data_limpa:
                                    try:
                                        dt = datetime.fromisoformat(data_limpa)
                                    except:
                                        pass
                                
                                if not dt:
                                    # Tentar outros formatos
                                    formatos = [
                                        "%Y-%m-%dT%H:%M:%S",
                                        "%Y-%m-%d %H:%M:%S", 
                                        "%Y-%m-%d",
                                        "%d/%m/%Y %H:%M:%S",
                                        "%d/%m/%Y %H:%M",
                                        "%d/%m/%Y"
                                    ]
                                    for fmt in formatos:
                                        try:
                                            dt = datetime.strptime(data_limpa, fmt)
                                            break
                                        except:
                                            continue
                                
                                if dt:
                                    data_formatada = dt.strftime('%d/%m/%Y')
                                    resposta += f"   📅 Data de Desembaraço: {data_formatada}\n"
                                else:
                                    # Se não conseguiu parsear, mostrar como está
                                    resposta += f"   📅 Data de Desembaraço: {data_desembaraco}\n"
                            except Exception as e:
                                logger.debug(f'Erro ao formatar data de desembaraço: {e}')
                                # Tentar mostrar a data como está
                                resposta += f"   📅 Data de Desembaraço: {data_desembaraco}\n"
                    
                    # DUIMP
                    duimp = proc.get('duimp')
                    if duimp:
                        situacao_duimp = duimp.get('situacao', '')
                        canal_duimp = duimp.get('canal', '')
                        resposta += f"   ⚠️ DUIMP {duimp.get('numero', 'N/A')} v{duimp.get('versao', 'N/A')}: {situacao_duimp.lower() if situacao_duimp else 'N/A'}"
                        if canal_duimp:
                            resposta += f" (Canal: {canal_duimp})"
                        resposta += "\n"
                    
                    # CE
                    ce = proc.get('ce')
                    if ce:
                        situacao_ce = ce.get('situacao', '')
                        resposta += f"   📦 CE {ce.get('numero', 'N/A')}: {situacao_ce if situacao_ce else 'N/A'}\n"
                    
                    # CCT
                    cct = proc.get('cct')
                    if cct:
                        situacao_cct = cct.get('situacao', '')
                        resposta += f"   ✈️ CCT {cct.get('numero', 'N/A')}: {situacao_cct if situacao_cct else 'N/A'}\n"
                    
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'processos': processos
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos por situação: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao listar processos: {str(e)}'
            }
    
    def _listar_por_eta(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos filtrados por ETA."""
        filtro_data = arguments.get('filtro_data', 'semana')
        data_especifica = arguments.get('data_especifica')
        categoria = arguments.get('categoria')
        processo_referencia = arguments.get('processo_referencia')
        limite = arguments.get('limite', 200)
        
        try:
            # ✅ MIGRADO: Usar ProcessoListService para garantir consistência
            from services.processo_list_service import ProcessoListService
            
            logger.info(f'🔍 ProcessoAgent._listar_por_eta: Buscando processos com ETA (filtro={filtro_data}, categoria={categoria}, limite={limite})')
            
            # ✅ Usar ProcessoListService que já tem a lógica correta de incluir_passado
            processo_list_service = ProcessoListService()
            resultado = processo_list_service.listar_processos_por_eta(
                filtro_data=filtro_data,
                data_especifica=data_especifica,
                categoria=categoria,
                processo_referencia=processo_referencia,
                limite=limite,
                mensagem_original=context.get('mensagem_original') if context else None
            )

            # ✅ MELHORIA (19/01/2026): Persistir listagem por ETA como "relatório visível"
            # Motivo: follow-ups do usuário (ex: "filtra só os BGR") precisam filtrar o relatório que acabou de aparecer na tela.
            try:
                session_id = (context or {}).get('session_id')
                if session_id and resultado and resultado.get('sucesso'):
                    from services.report_service import criar_relatorio_gerado, salvar_ultimo_relatorio

                    processos = resultado.get('dados') or []
                    categoria_norm = (categoria or '').strip().upper() if categoria else None

                    # Mapear filtro_data para texto humano (consistente com ProcessoListService)
                    texto_periodo = {
                        'hoje': 'hoje',
                        'amanha': 'amanhã',
                        'amanhã': 'amanhã',
                        'semana': 'esta semana',
                        'proxima_semana': 'semana que vem',
                        'mes': 'neste mês',
                        'proximo_mes': 'mês que vem',
                        'data_especifica': f'em {data_especifica}' if data_especifica else 'em data específica',
                    }.get(filtro_data, str(filtro_data))

                    # ✅ JSON estruturado mínimo para permitir filtro por categoria via buscar_secao_relatorio_salvo
                    # Seção "processos_chegando" é a mais adequada para o caso "o que tem pra chegar?"
                    dados_json = {
                        'tipo_relatorio': 'processos_chegando',
                        'data': None,
                        'categoria': categoria_norm,
                        'resumo': {
                            'total_chegando': len(processos),
                            'periodo': texto_periodo,
                        },
                        'secoes': {
                            'processos_chegando': processos
                        }
                    }

                    # Anexar REPORT_META no texto exibido (fonte da verdade para ferramentas de email/filtragem)
                    texto_chat = resultado.get('resposta', '') or ''
                    if '[REPORT_META:' not in texto_chat:
                        texto_chat = texto_chat + RelatorioFormatterService._gerar_meta_json_inline('processos_chegando', dados_json)

                    # Persistir relatório (isso atualiza active_report_id/last_visible_report_id automaticamente)
                    relatorio = criar_relatorio_gerado(
                        tipo_relatorio='processos_chegando',
                        texto_chat=texto_chat,
                        categoria=categoria_norm,
                        filtros={
                            'filtro_data': filtro_data,
                            'data_especifica': data_especifica,
                            'periodo': texto_periodo,
                        },
                        meta_json={
                            'dados_json': dados_json
                        }
                    )
                    salvar_ultimo_relatorio(session_id, relatorio)

                    # Atualizar resposta para incluir REPORT_META (caso caller use o texto retornado)
                    resultado['resposta'] = texto_chat
            except Exception as e:
                # Não deve quebrar a listagem se falhar persistência
                logger.warning(f"⚠️ Falha ao salvar relatório de ETA (não crítico): {e}", exc_info=True)

            # ✅ Retornar resultado do ProcessoListService (agora com REPORT_META quando possível)
            return resultado
        except Exception as e:
            logger.error(f'Erro ao listar processos por ETA: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar processos por ETA: {str(e)}'
            }
    
    def _listar_por_navio(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos filtrados por nome do navio."""
        nome_navio = arguments.get('nome_navio', '').strip()
        categoria = arguments.get('categoria')
        limite = arguments.get('limite', 200)
        
        if not nome_navio:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBIGATORIO',
                'mensagem': 'nome_navio é obrigatório'
            }
        
        try:
            from db_manager import listar_processos_por_navio
            
            logger.info(f'🔍 listar_processos_por_navio: Buscando processos no navio "{nome_navio}" (categoria={categoria}, limite={limite})')
            
            # Buscar processos filtrados por navio
            processos = listar_processos_por_navio(
                nome_navio=nome_navio,
                categoria=categoria.upper() if categoria else None,
                limit=limite
            )
            
            logger.info(f'🔍 listar_processos_por_navio: Encontrados {len(processos)} processos no navio "{nome_navio}"')
            
            # Se o DB fez fuzzy match, refletir no texto (sem mudar comportamento do usuário)
            navio_match = None
            fuzzy_used = False
            if processos:
                try:
                    navio_match = processos[0].get('_navio_match')
                    fuzzy_used = bool(processos[0].get('_navio_fuzzy_used', False))
                except Exception:
                    navio_match = None
                    fuzzy_used = False

            nome_navio_exibicao = navio_match or nome_navio

            if not processos:
                resposta = f"✅ **Nenhum processo encontrado no navio \"{nome_navio}\".**\n\n"
                if categoria:
                    resposta += f"💡 **Dica:** Não há processos da categoria **{categoria.upper()}** no navio \"{nome_navio}\".\n"
                else:
                    resposta += f"💡 **Dica:** Não há processos no navio \"{nome_navio}\" no sistema."
            else:
                if fuzzy_used and navio_match and navio_match.strip().lower() != nome_navio.strip().lower():
                    resposta = f"🔎 **Interpretei seu navio como:** \"{navio_match}\" (correção automática de grafia)\n\n"
                else:
                    resposta = ""
                if categoria:
                    resposta += f"🚢 **Processos {categoria.upper()} no navio \"{nome_navio_exibicao}\"** ({len(processos)} processo(s))\n\n"
                else:
                    resposta += f"🚢 **Processos no navio \"{nome_navio_exibicao}\"** ({len(processos)} processo(s))\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    resposta += f"**{proc_ref}**\n"
                    
                    # ShipsGo (ETA/Porto/Navio/Status) - destacar primeiro, formatado em linhas separadas
                    shipsgo = proc.get('shipsgo')
                    if shipsgo:
                        eta = shipsgo.get('shipsgo_eta')
                        porto_codigo = shipsgo.get('shipsgo_porto_codigo', '')
                        porto_nome = shipsgo.get('shipsgo_porto_nome', '')
                        navio = shipsgo.get('shipsgo_navio', '')
                        status = shipsgo.get('shipsgo_status', '')
                        
                        if eta:
                            try:
                                from datetime import datetime
                                eta_date = datetime.fromisoformat(eta.replace('Z', '+00:00'))
                                eta_formatado = eta_date.strftime('%d/%m/%Y às %H:%M')
                                resposta += f"   🚢 **ETA:** {eta_formatado}\n"
                            except:
                                resposta += f"   🚢 **ETA:** {eta}\n"
                        
                        if porto_codigo or porto_nome:
                            if porto_codigo and porto_nome:
                                porto_txt = f"{porto_codigo} - {porto_nome}"
                            elif porto_codigo:
                                porto_txt = porto_codigo
                            elif porto_nome:
                                porto_txt = porto_nome
                            else:
                                porto_txt = ''
                            if porto_txt:
                                resposta += f"   ⚓ **Porto:** {porto_txt}\n"
                        
                        if navio:
                            resposta += f"   🚢 **Navio:** {navio}\n"
                        
                        if status:
                            resposta += f"   📊 **Status:** {status}\n"
                    
                    # DI
                    di = proc.get('di')
                    if di:
                        situacao_di = di.get('situacao', '')
                        canal_di = di.get('canal', '')
                        resposta += f"   📄 DI {di.get('numero', 'N/A')}: {situacao_di.lower() if situacao_di else 'N/A'}"
                        if canal_di:
                            resposta += f" (Canal: {canal_di})"
                        resposta += "\n"
                    
                    # DUIMP
                    duimp = proc.get('duimp')
                    if duimp:
                        situacao_duimp = duimp.get('situacao', '')
                        canal_duimp = duimp.get('canal', '')
                        resposta += f"   ⚠️ DUIMP {duimp.get('numero', 'N/A')} v{duimp.get('versao', 'N/A')}: {situacao_duimp.lower() if situacao_duimp else 'N/A'}"
                        if canal_duimp:
                            resposta += f" (Canal: {canal_duimp})"
                        resposta += "\n"
                    
                    # CE
                    ce = proc.get('ce')
                    if ce:
                        situacao_ce = ce.get('situacao', '')
                        resposta += f"   📦 CE {ce.get('numero', 'N/A')}: {situacao_ce if situacao_ce else 'N/A'}\n"
                    
                    # CCT
                    cct = proc.get('cct')
                    if cct:
                        situacao_cct = cct.get('situacao', '')
                        resposta += f"   ✈️ CCT {cct.get('numero', 'N/A')}: {situacao_cct if situacao_cct else 'N/A'}\n"
                    
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'nome_navio': nome_navio,
                'categoria': categoria
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos por navio: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar processos por navio: {str(e)}'
            }
    
    def _listar_por_navio(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos filtrados por nome do navio."""
        nome_navio = arguments.get('nome_navio', '').strip()
        categoria = arguments.get('categoria')
        limite = arguments.get('limite', 200)
        
        if not nome_navio:
            return {
                'sucesso': False,
                'erro': 'PARAMETRO_OBRIGATORIO',
                'mensagem': 'nome_navio é obrigatório'
            }
        
        try:
            from db_manager import listar_processos_por_navio
            
            logger.info(f'🔍 listar_processos_por_navio: Buscando processos no navio "{nome_navio}" (categoria={categoria}, limite={limite})')
            
            # Buscar processos filtrados por navio
            processos = listar_processos_por_navio(
                nome_navio=nome_navio,
                categoria=categoria.upper() if categoria else None,
                limit=limite
            )
            
            logger.info(f'🔍 listar_processos_por_navio: Encontrados {len(processos)} processos no navio "{nome_navio}"')
            
            if not processos:
                resposta = f"✅ **Nenhum processo encontrado no navio \"{nome_navio}\".**\n\n"
                if categoria:
                    resposta += f"💡 **Dica:** Não há processos da categoria **{categoria.upper()}** no navio \"{nome_navio}\".\n"
                else:
                    resposta += f"💡 **Dica:** Não há processos no navio \"{nome_navio}\" no sistema."
            else:
                if categoria:
                    resposta = f"🚢 **Processos {categoria.upper()} no navio \"{nome_navio}\"** ({len(processos)} processo(s))\n\n"
                else:
                    resposta = f"🚢 **Processos no navio \"{nome_navio}\"** ({len(processos)} processo(s))\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    resposta += f"**{proc_ref}**\n"
                    
                    # ShipsGo (ETA/Porto/Navio/Status) - destacar primeiro, formatado em linhas separadas
                    shipsgo = proc.get('shipsgo')
                    if shipsgo:
                        eta = shipsgo.get('shipsgo_eta')
                        porto_codigo = shipsgo.get('shipsgo_porto_codigo', '')
                        porto_nome = shipsgo.get('shipsgo_porto_nome', '')
                        navio = shipsgo.get('shipsgo_navio', '')
                        status = shipsgo.get('shipsgo_status', '')
                        
                        if eta:
                            try:
                                from datetime import datetime
                                eta_date = datetime.fromisoformat(eta.replace('Z', '+00:00'))
                                eta_formatado = eta_date.strftime('%d/%m/%Y às %H:%M')
                                resposta += f"   🚢 **ETA:** {eta_formatado}\n"
                            except:
                                resposta += f"   🚢 **ETA:** {eta}\n"
                        
                        if porto_codigo or porto_nome:
                            if porto_codigo and porto_nome:
                                porto_txt = f"{porto_codigo} - {porto_nome}"
                            elif porto_codigo:
                                porto_txt = porto_codigo
                            elif porto_nome:
                                porto_txt = porto_nome
                            else:
                                porto_txt = ''
                            if porto_txt:
                                resposta += f"   ⚓ **Porto:** {porto_txt}\n"
                        
                        if navio:
                            resposta += f"   🚢 **Navio:** {navio}\n"
                        
                        if status:
                            resposta += f"   📊 **Status:** {status}\n"
                    
                    # DI
                    di = proc.get('di')
                    if di:
                        situacao_di = di.get('situacao', '')
                        canal_di = di.get('canal', '')
                        resposta += f"   📄 DI {di.get('numero', 'N/A')}: {situacao_di.lower() if situacao_di else 'N/A'}"
                        if canal_di:
                            resposta += f" (Canal: {canal_di})"
                        resposta += "\n"
                    
                    # DUIMP
                    duimp = proc.get('duimp')
                    if duimp:
                        situacao_duimp = duimp.get('situacao', '')
                        canal_duimp = duimp.get('canal', '')
                        resposta += f"   ⚠️ DUIMP {duimp.get('numero', 'N/A')} v{duimp.get('versao', 'N/A')}: {situacao_duimp.lower() if situacao_duimp else 'N/A'}"
                        if canal_duimp:
                            resposta += f" (Canal: {canal_duimp})"
                        resposta += "\n"
                    
                    # CE
                    ce = proc.get('ce')
                    if ce:
                        situacao_ce = ce.get('situacao', '')
                        resposta += f"   📦 CE {ce.get('numero', 'N/A')}: {situacao_ce if situacao_ce else 'N/A'}\n"
                    
                    # CCT
                    cct = proc.get('cct')
                    if cct:
                        situacao_cct = cct.get('situacao', '')
                        resposta += f"   ✈️ CCT {cct.get('numero', 'N/A')}: {situacao_cct if situacao_cct else 'N/A'}\n"
                    
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'nome_navio': nome_navio,
                'categoria': categoria
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos por navio: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar processos por navio: {str(e)}'
            }
    
    def _listar_liberados_registro(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos que chegaram e não têm DI nem DUIMP (liberados para registro/despacho)."""
        categoria = arguments.get('categoria')
        dias_retroativos = arguments.get('dias_retroativos', 5)
        data_inicio = arguments.get('data_inicio')
        data_fim = arguments.get('data_fim')
        limite = arguments.get('limite', 200)
        
        try:
            from db_manager import listar_processos_liberados_registro
            
            logger.info(f'🔍 listar_processos_liberados_registro: Buscando processos que chegaram sem DI/DUIMP (categoria={categoria}, dias={dias_retroativos}, limite={limite})')
            
            # Buscar processos liberados para registro
            processos = listar_processos_liberados_registro(
                categoria=categoria.upper() if categoria else None,
                dias_retroativos=dias_retroativos,
                data_inicio=data_inicio,
                data_fim=data_fim,
                limit=limite
            )
            
            logger.info(f'🔍 listar_processos_liberados_registro: Encontrados {len(processos)} processos liberados para registro')
            
            if not processos:
                resposta = f"✅ **Nenhum processo encontrado que chegou sem DI/DUIMP.**\n\n"
                if categoria:
                    resposta += f"💡 **Dica:** Não há processos da categoria **{categoria.upper()}** que chegaram sem registro de DI ou DUIMP no período especificado."
                else:
                    resposta += f"💡 **Dica:** Todos os processos que chegaram já têm DI ou DUIMP registrada."
            else:
                if categoria:
                    resposta = f"📋 **Processos {categoria.upper()} que chegaram sem despacho** ({len(processos)} processo(s))\n\n"
                else:
                    resposta = f"📋 **Processos que chegaram sem despacho** ({len(processos)} processo(s))\n\n"
                
                resposta += f"💡 **Estes processos precisam de registro de DI ou DUIMP:**\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    data_chegada_str = proc.get('data_chegada', '')
                    categoria_proc = proc.get('categoria', '')
                    numero_ce = proc.get('numero_ce', '')
                    situacao_ce = proc.get('situacao_ce', '')
                    nome_navio = proc.get('nome_navio', '')
                    porto_nome = proc.get('porto_nome', '')
                    
                    resposta += f"**{proc_ref}**\n"
                    
                    # Data de chegada
                    if data_chegada_str:
                        try:
                            from datetime import datetime
                            data_chegada = datetime.fromisoformat(data_chegada_str.split('T')[0])
                            resposta += f"   📅 **Chegou em:** {data_chegada.strftime('%d/%m/%Y')}\n"
                        except:
                            resposta += f"   📅 **Chegou em:** {data_chegada_str}\n"
                    
                    # CE (se houver)
                    if numero_ce:
                        resposta += f"   📦 **CE:** {numero_ce}\n"
                        if situacao_ce:
                            resposta += f"      - Situação: {situacao_ce}\n"
                    
                    # Transporte
                    if nome_navio:
                        resposta += f"   🚢 **Navio:** {nome_navio}\n"
                    if porto_nome:
                        resposta += f"   ⚓ **Porto:** {porto_nome}\n"
                    
                    resposta += "\n"

                # 🔍 Adicionar análise cambial (PTAX) para decisão de registro hoje vs amanhã
                try:
                    from utils.ptax_bcb import obter_ptax_dia_util_anterior
                    from datetime import datetime, timedelta

                    hoje_dt = datetime.now()
                    hoje_str = hoje_dt.strftime('%m-%d-%Y')
                    amanha_dt = hoje_dt + timedelta(days=1)
                    amanha_str = amanha_dt.strftime('%m-%d-%Y')

                    ptax_registro_hoje = obter_ptax_dia_util_anterior(hoje_str)
                    ptax_registro_amanha = obter_ptax_dia_util_anterior(amanha_str)

                    if ptax_registro_hoje and ptax_registro_amanha and \
                       ptax_registro_hoje.get('sucesso') and ptax_registro_amanha.get('sucesso'):
                        v_hoje = ptax_registro_hoje.get('cotacao_venda')
                        v_amanha = ptax_registro_amanha.get('cotacao_venda')
                        if v_hoje and v_amanha and v_hoje > 0:
                            delta = (v_amanha - v_hoje) / v_hoje * 100.0
                            sinal = "mais barato" if delta < 0 else "mais caro" if delta > 0 else "igual"
                            delta_abs = abs(delta)

                            resposta += "📉 **Impacto cambial estimado (PTAX de venda)**\n"
                            resposta += f"- PTAX p/ registrar **hoje** (D-1 de hoje): R$ {v_hoje:.4f}\n"
                            resposta += f"- PTAX se registrar **amanhã** (D-1 de amanhã): R$ {v_amanha:.4f}\n"
                            if delta_abs > 0:
                                resposta += f"- Tendência: registrar **amanhã** fica **{delta_abs:.2f}% {sinal}** em termos de câmbio.\n"
                            else:
                                resposta += "- Tendência: não há diferença relevante de câmbio entre registrar hoje ou amanhã.\n"

                            resposta += "  _(Apenas indicativo; a PTAX oficial de amanhã só é conhecida no próprio dia.)_\n"
                except Exception as e_ptax:
                    logger.warning(f'⚠️ Erro ao calcular análise cambial para registro: {e_ptax}')
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'categoria': categoria,
                'dias_retroativos': dias_retroativos
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos liberados para registro: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar processos liberados para registro: {str(e)}'
            }
    
    def _listar_registrados_hoje(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos que tiveram DI ou DUIMP registrada HOJE."""
        categoria = arguments.get('categoria')
        limite = arguments.get('limite', 200)
        dias_atras = arguments.get('dias_atras', 0)
        
        try:
            from db_manager import listar_processos_registrados_hoje
            
            try:
                dias_atras_int = int(dias_atras or 0)
            except Exception:
                dias_atras_int = 0
            if dias_atras_int < 0:
                dias_atras_int = 0

            label = "hoje" if dias_atras_int == 0 else "ontem" if dias_atras_int == 1 else f"D-{dias_atras_int}"
            logger.info(
                f'🔍 listar_processos_registrados_hoje: Buscando processos com DI/DUIMP registrada {label} '
                f'(categoria={categoria}, limite={limite})'
            )
            
            processos = listar_processos_registrados_hoje(
                categoria=categoria.upper() if categoria else None,
                limit=limite,
                dias_atras=dias_atras_int,
            )
            
            logger.info(f'🔍 listar_processos_registrados_hoje: Encontrados {len(processos)} processos registrados {label}')
            
            if not processos:
                resposta = f"✅ **Nenhum processo registrado {label}.**\n\n"
                if categoria:
                    resposta += f"💡 Não há processos da categoria **{categoria.upper()}** que tiveram DI ou DUIMP registrada {label}."
                else:
                    resposta += f"💡 Nenhum processo teve DI ou DUIMP registrada {label}."
            else:
                if categoria:
                    resposta = f"📋 **Processos {categoria.upper()} registrados {label}** ({len(processos)} processo(s))\n\n"
                else:
                    resposta = f"📋 **Processos registrados {label}** ({len(processos)} processo(s))\n\n"
                
                resposta += f"💡 **DI/DUIMP registradas {label}:**\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    documentos = proc.get('documentos', [])
                    ultima_atualizacao = proc.get('ultima_atualizacao', '')
                    
                    resposta += f"**{proc_ref}**\n"
                    
                    # Listar documentos registrados hoje
                    for doc in documentos:
                        tipo_doc = doc.get('tipo', '')
                        num_doc = doc.get('numero', '')
                        atualizado_em = doc.get('atualizado_em', '')
                        status_novo = doc.get('status_novo', '')
                        
                        # Formatar hora
                        try:
                            from datetime import datetime, timezone
                            # Se vier com 'Z', tratar como UTC. Se vier sem timezone, assumir UTC (servidor costuma gravar em UTC).
                            texto = atualizado_em.strip() if isinstance(atualizado_em, str) else str(atualizado_em)
                            if texto.endswith('Z'):
                                texto = texto.replace('Z', '+00:00')
                            dt = datetime.fromisoformat(texto)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            dt_local = dt.astimezone(timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/Sao_Paulo'))
                            data_hora_str = dt_local.strftime('%d/%m %H:%M')
                        except:
                            # Fallback: se vier "YYYY-MM-DD HH:MM:SS"
                            try:
                                data_partes = atualizado_em.split(' ')
                                if len(data_partes) >= 2:
                                    data_hora_str = f"{data_partes[0]} {data_partes[1][:5]}"
                                else:
                                    data_hora_str = atualizado_em
                            except Exception:
                                data_hora_str = atualizado_em
                        
                        resposta += f"   📄 **{tipo_doc}:** {num_doc} (registrado em {data_hora_str})\n"
                        if status_novo:
                            resposta += f"      Status: {status_novo}\n"
                    
                    # Etapa do Kanban
                    etapa = proc.get('etapa_kanban', '')
                    if etapa:
                        resposta += f"   📍 **Etapa:** {etapa}\n"
                    
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'categoria': categoria,
                'dias_atras': dias_atras_int,
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos registrados hoje: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar processos registrados hoje: {str(e)}'
            }

    def _listar_registrados_periodo(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista registros (DI/DUIMP) em um período usando SQL Server (`mAIke_assistente`)."""
        try:
            from datetime import datetime
            from services.registros_periodo_service import RegistrosPeriodoService

            categoria = arguments.get("categoria")
            periodo = arguments.get("periodo")
            mes = arguments.get("mes")
            ano = arguments.get("ano")
            data_inicio = arguments.get("data_inicio")
            data_fim = arguments.get("data_fim")
            limite = arguments.get("limite", 200)

            svc = RegistrosPeriodoService()
            r = svc.listar(
                categoria=categoria,
                periodo=periodo,
                mes=mes,
                ano=ano,
                data_inicio=data_inicio,
                data_fim=data_fim,
                limite=limite,
            )
            if not r.get("sucesso"):
                return {
                    "sucesso": False,
                    "erro": r.get("erro"),
                    "resposta": r.get("resposta") or "❌ Não consegui listar registros do período.",
                }

            dados = r.get("dados") or {}
            per = (dados.get("periodo") or {})
            inicio = per.get("inicio")
            fim = per.get("fim")
            cat = per.get("categoria")
            totais = dados.get("totais") or {}
            itens = dados.get("itens") or []

            titulo = "📅 **O QUE REGISTRAMOS**"
            if cat:
                titulo += f" — {cat}"
            if inicio and fim:
                titulo += f"\n_Período: {inicio} → {fim}_"

            linhas = [titulo, "", "💡 _Base: `DOCUMENTO_ADUANEIRO.data_registro` (DI/DUIMP)_", ""]
            linhas.append(
                f"✅ **Totais:** DI={totais.get('di', 0)} | DUIMP={totais.get('duimp', 0)} | Total={totais.get('total', 0)}"
            )
            linhas.append("")

            max_show = 50
            if itens:
                linhas.append("📋 **Registros (mais recentes primeiro):**")
                for row in itens[:max_show]:
                    if not isinstance(row, dict):
                        continue
                    td = (row.get("tipo_documento") or "").upper()
                    num = row.get("numero_documento") or ""
                    proc = row.get("processo_referencia") or ""
                    canal = row.get("canal_documento")
                    situ = row.get("situacao_documento")
                    dt = row.get("data_registro")

                    dt_txt = ""
                    try:
                        if isinstance(dt, datetime):
                            dt_txt = dt.strftime("%d/%m/%Y")
                        else:
                            dt_txt = str(dt).split("T")[0].split(" ")[0]
                    except Exception:
                        dt_txt = str(dt) if dt else ""

                    linha = f"- **{td} {num}**"
                    if proc:
                        linha += f" — Processo: {proc}"
                    if canal:
                        linha += f" — Canal: {canal}"
                    if situ:
                        linha += f" — Situação: {situ}"
                    if dt_txt:
                        linha += f" — Registro: {dt_txt}"
                    linhas.append(linha)

                if len(itens) > max_show:
                    linhas.append(f"- ... e mais {len(itens) - max_show} registro(s) (aumente `limite` se precisar).")
            else:
                linhas.append("ℹ️ Nenhum registro de DI/DUIMP encontrado nesse período.")

            return {"sucesso": True, "resposta": "\n".join(linhas).strip(), "dados": dados}
        except Exception as e:
            logger.error(f"Erro ao listar registros por período: {e}", exc_info=True)
            return {"sucesso": False, "erro": str(e), "resposta": f"❌ Erro ao listar registros do período: {str(e)}"}

    def _listar_desembaracados_hoje(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos que desembaraçaram HOJE (data/hora de desembaraço)."""
        categoria = arguments.get('categoria')
        modal = arguments.get('modal')
        limite = arguments.get('limite', 200)
        dias_atras = arguments.get('dias_atras', 0)

        try:
            from db_manager import listar_processos_desembaracados_hoje

            try:
                dias_atras_int = int(dias_atras or 0)
            except Exception:
                dias_atras_int = 0
            if dias_atras_int < 0:
                dias_atras_int = 0
            label = "hoje" if dias_atras_int == 0 else "ontem" if dias_atras_int == 1 else f"D-{dias_atras_int}"

            processos = listar_processos_desembaracados_hoje(
                categoria=categoria.upper() if isinstance(categoria, str) and categoria else None,
                modal=modal,
                limit=limite,
                dias_atras=dias_atras_int,
            )

            if not processos:
                resposta = f"✅ **Nenhum processo desembaraçado {label}.**\n\n"
                if categoria:
                    resposta += f"💡 Não há processos da categoria **{categoria.upper()}** com desembaraço {label}."
                else:
                    resposta += f"💡 Nenhum processo teve desembaraço {label}."
                return {'sucesso': True, 'resposta': resposta, 'total': 0, 'categoria': categoria, 'modal': modal, 'dias_atras': dias_atras_int}

            titulo = f"✅ **PROCESSOS DESEMBARAÇADOS {label.upper()}**"
            if categoria:
                titulo = f"✅ **PROCESSOS {categoria.upper()} DESEMBARAÇADOS {label.upper()}**"
            resposta = f"{titulo} ({len(processos)} processo(s))\n\n"

            for proc in processos:
                proc_ref = proc.get('processo_referencia', 'N/A')
                resposta += f"• **{proc_ref}**"
                if proc.get('numero_di'):
                    resposta += f" - DI: {proc.get('numero_di')}"
                if proc.get('numero_duimp'):
                    resposta += f" - DUIMP: {proc.get('numero_duimp')}"
                if proc.get('situacao_di'):
                    resposta += f" - Status DI: {proc.get('situacao_di')}"
                elif proc.get('situacao_entrega'):
                    resposta += f" - Status: {proc.get('situacao_entrega')}"
                if proc.get('data_desembaraco'):
                    try:
                        from datetime import datetime
                        data_limpa = str(proc.get('data_desembaraco')).replace('Z', '').replace('+00:00', '').strip()
                        dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                        if dt:
                            resposta += f" - Desembaraço: {dt.strftime('%d/%m/%Y %H:%M')}"
                        else:
                            resposta += f" - Desembaraço: {proc.get('data_desembaraco')}"
                    except Exception:
                        resposta += f" - Desembaraço: {proc.get('data_desembaraco')}"
                resposta += "\n"

            resposta += "\n_Obs.: **Registro** = dataHoraRegistro; **Desembaraço** = dataHoraDesembaraco._"

            return {'sucesso': True, 'resposta': resposta, 'total': len(processos), 'categoria': categoria, 'modal': modal, 'dias_atras': dias_atras_int}
        except Exception as e:
            logger.error(f'Erro ao listar processos desembaraçados hoje: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar processos desembaraçados hoje: {str(e)}'
            }

    def _listar_dis_por_canal(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        ✅ NOVO (20/01/2026): Lista DIs do Kanban/SQLite filtrando por canal.
        Útil quando o usuário pergunta sobre canal antes de gerar um relatório.
        """
        try:
            canal = arguments.get('canal')
            status_contains = arguments.get('status_contains')
            if not canal or canal not in ('Verde', 'Vermelho'):
                return {
                    'sucesso': False,
                    'erro': 'CANAL_INVALIDO',
                    'resposta': '❌ Canal inválido. Use "Verde" ou "Vermelho".'
                }

            from db_manager import obter_dis_em_analise
            from services.report_filter_service import filtrar_secao_relatorio

            dis = obter_dis_em_analise(categoria=None) or []
            dis_filtradas, _ = filtrar_secao_relatorio(
                'dis_analise',
                dis,
                canal=canal,
                status_contains=status_contains,
            )

            # Formatar como seção (sem gerar relatório completo)
            dados_json = {
                'tipo_relatorio': 'o_que_tem_hoje',
                'data': '',
                'secoes': {'dis_analise': dis_filtradas},
                'filtrado': True,
                'secoes_filtradas': ['dis_analise'],
            }
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)

            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {'dis_analise': dis_filtradas},
                'total': len(dis_filtradas) if isinstance(dis_filtradas, list) else 0,
            }
        except Exception as e:
            logger.error(f'Erro ao listar DIs por canal: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao listar DIs por canal: {str(e)}'
            }

    def _listar_pendencias_ativas(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """✅ NOVO (20/01/2026): Pendências ativas (ativos-first) sem exigir relatório."""
        try:
            tipo_pendencia = arguments.get('tipo_pendencia')
            categoria = arguments.get('categoria')
            modal = arguments.get('modal')

            from db_manager import obter_pendencias_ativas
            from services.report_filter_service import filtrar_secao_relatorio

            pendencias = obter_pendencias_ativas(
                categoria=categoria.upper() if isinstance(categoria, str) and categoria else None,
                modal=modal,
            ) or []
            pend_filtradas, _ = filtrar_secao_relatorio(
                'pendencias',
                pendencias,
                tipo_pendencia=tipo_pendencia,
            )

            from datetime import datetime
            dados_json = {
                'tipo_relatorio': 'o_que_tem_hoje',
                'data': datetime.now().strftime('%Y-%m-%d'),
                'secoes': {'pendencias': pend_filtradas},
                'filtrado': True,
                'secoes_filtradas': ['pendencias'],
            }
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)

            # ✅ Persistir como relatório visível (para follow-ups e "envie esse relatorio")
            session_id = context.get('session_id') if context else None
            if session_id:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                rel = criar_relatorio_gerado(
                    tipo_relatorio='o_que_tem_hoje',
                    texto_chat=resposta,
                    categoria=None,
                    filtros={'secao': 'pendencias', 'tipo_pendencia': tipo_pendencia, 'categoria': categoria, 'modal': modal},
                    meta_json={'dados_json': dados_json},
                )
                salvar_ultimo_relatorio(session_id, rel)

            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {'pendencias': pend_filtradas},
                'total': len(pend_filtradas) if isinstance(pend_filtradas, list) else 0,
            }
        except Exception as e:
            logger.error(f'Erro ao listar pendências ativas: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao listar pendências: {str(e)}'}

    def _listar_alertas_recentes(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """✅ NOVO (20/01/2026): Alertas recentes (ativos-first) sem exigir relatório."""
        try:
            limite = arguments.get('limite', 10)
            categoria = arguments.get('categoria')

            from db_manager import obter_alertas_recentes
            from datetime import datetime

            alertas = obter_alertas_recentes(limite=int(limite or 10), categoria=categoria.upper() if isinstance(categoria, str) and categoria else None) or []
            dados_json = {
                'tipo_relatorio': 'o_que_tem_hoje',
                'data': datetime.now().strftime('%Y-%m-%d'),
                'secoes': {'alertas': alertas},
                'filtrado': True,
                'secoes_filtradas': ['alertas'],
            }
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)

            session_id = context.get('session_id') if context else None
            if session_id:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                rel = criar_relatorio_gerado(
                    tipo_relatorio='o_que_tem_hoje',
                    texto_chat=resposta,
                    categoria=None,
                    filtros={'secao': 'alertas', 'categoria': categoria, 'limite': limite},
                    meta_json={'dados_json': dados_json},
                )
                salvar_ultimo_relatorio(session_id, rel)

            return {'sucesso': True, 'resposta': resposta, 'dados': {'alertas': alertas}, 'total': len(alertas)}
        except Exception as e:
            logger.error(f'Erro ao listar alertas recentes: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao listar alertas: {str(e)}'}

    def _listar_processos_prontos_registro(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """✅ NOVO (20/01/2026): Processos prontos para registro (ativos-first) sem exigir relatório."""
        try:
            categoria = arguments.get('categoria')
            modal = arguments.get('modal')

            from db_manager import obter_processos_prontos_registro
            from datetime import datetime

            prontos = obter_processos_prontos_registro(
                categoria=categoria.upper() if isinstance(categoria, str) and categoria else None,
                modal=modal,
            ) or []
            dados_json = {
                'tipo_relatorio': 'o_que_tem_hoje',
                'data': datetime.now().strftime('%Y-%m-%d'),
                'secoes': {'processos_prontos': prontos},
                'filtrado': True,
                'secoes_filtradas': ['processos_prontos'],
            }
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)

            session_id = context.get('session_id') if context else None
            if session_id:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                rel = criar_relatorio_gerado(
                    tipo_relatorio='o_que_tem_hoje',
                    texto_chat=resposta,
                    categoria=None,
                    filtros={'secao': 'processos_prontos', 'categoria': categoria, 'modal': modal},
                    meta_json={'dados_json': dados_json},
                )
                salvar_ultimo_relatorio(session_id, rel)

            return {'sucesso': True, 'resposta': resposta, 'dados': {'processos_prontos': prontos}, 'total': len(prontos)}
        except Exception as e:
            logger.error(f'Erro ao listar prontos para registro: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao listar prontos para registro: {str(e)}'}

    def _listar_eta_alterado(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """✅ NOVO (20/01/2026): ETA alterado (ativos-first) sem exigir relatório."""
        try:
            tipo_mudanca = arguments.get('tipo_mudanca')
            min_dias = arguments.get('min_dias')
            categoria = arguments.get('categoria')

            from db_manager import obter_processos_eta_alterado
            from services.report_filter_service import filtrar_secao_relatorio
            from datetime import datetime

            itens = obter_processos_eta_alterado(categoria=categoria.upper() if isinstance(categoria, str) and categoria else None) or []
            itens_f, _ = filtrar_secao_relatorio(
                'eta_alterado',
                itens,
                tipo_mudanca=tipo_mudanca,
                min_dias=min_dias,
            )
            dados_json = {
                'tipo_relatorio': 'o_que_tem_hoje',
                'data': datetime.now().strftime('%Y-%m-%d'),
                'secoes': {'eta_alterado': itens_f},
                'filtrado': True,
                'secoes_filtradas': ['eta_alterado'],
            }
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)

            session_id = context.get('session_id') if context else None
            if session_id:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                rel = criar_relatorio_gerado(
                    tipo_relatorio='o_que_tem_hoje',
                    texto_chat=resposta,
                    categoria=None,
                    filtros={'secao': 'eta_alterado', 'tipo_mudanca': tipo_mudanca, 'min_dias': min_dias, 'categoria': categoria},
                    meta_json={'dados_json': dados_json},
                )
                salvar_ultimo_relatorio(session_id, rel)

            return {'sucesso': True, 'resposta': resposta, 'dados': {'eta_alterado': itens_f}, 'total': len(itens_f) if isinstance(itens_f, list) else 0}
        except Exception as e:
            logger.error(f'Erro ao listar ETA alterado: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao listar ETA alterado: {str(e)}'}

    def _listar_duimps_em_analise(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """✅ NOVO (20/01/2026): DUIMPs em análise (ativos-first) sem exigir relatório."""
        try:
            categoria = arguments.get('categoria')
            status_contains = arguments.get('status_contains')
            min_age_dias = arguments.get('min_age_dias')

            from db_manager import obter_duimps_em_analise
            from services.report_filter_service import filtrar_secao_relatorio
            from datetime import datetime

            duimps = obter_duimps_em_analise(categoria=categoria.upper() if isinstance(categoria, str) and categoria else None) or []
            duimps_f, _ = filtrar_secao_relatorio(
                'duimps_analise',
                duimps,
                status_contains=status_contains,
                min_age_dias=min_age_dias,
            )
            dados_json = {
                'tipo_relatorio': 'o_que_tem_hoje',
                'data': datetime.now().strftime('%Y-%m-%d'),
                'secoes': {'duimps_analise': duimps_f},
                'filtrado': True,
                'secoes_filtradas': ['duimps_analise'],
            }
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)

            session_id = context.get('session_id') if context else None
            if session_id:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                rel = criar_relatorio_gerado(
                    tipo_relatorio='o_que_tem_hoje',
                    texto_chat=resposta,
                    categoria=None,
                    filtros={'secao': 'duimps_analise', 'categoria': categoria, 'status_contains': status_contains, 'min_age_dias': min_age_dias},
                    meta_json={'dados_json': dados_json},
                )
                salvar_ultimo_relatorio(session_id, rel)

            return {'sucesso': True, 'resposta': resposta, 'dados': {'duimps_analise': duimps_f}, 'total': len(duimps_f) if isinstance(duimps_f, list) else 0}
        except Exception as e:
            logger.error(f'Erro ao listar DUIMPs em análise: {e}', exc_info=True)
            return {'sucesso': False, 'erro': str(e), 'resposta': f'❌ Erro ao listar DUIMPs: {str(e)}'}
    
    def _listar_processos_em_dta(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos que estão em DTA (Declaração de Trânsito Aduaneiro)."""
        try:
            categoria = arguments.get('categoria')
            limite = arguments.get('limite', 200)
            
            # ✅ CORREÇÃO: Se categoria for "EM" (interpretação incorreta de "em DTA"), ignorar
            if categoria and categoria.upper() == 'EM':
                logger.warning(f'⚠️ Categoria "EM" detectada - provavelmente interpretação incorreta de "em DTA". Ignorando filtro de categoria.')
                categoria = None
            
            from db_manager import listar_processos_em_dta
            
            processos = listar_processos_em_dta(categoria=categoria, limit=limite)
            
            if not processos:
                resposta = "📋 **Processos em DTA**\n\n"
                resposta += "✅ Nenhum processo em DTA encontrado."
                if categoria:
                    resposta += f"\n\n(Categoria filtrada: {categoria})"
                return {
                    'sucesso': True,
                    'resposta': resposta
                }
            
            resposta = f"🚚 **Processos em DTA** ({len(processos)} processo(s))\n\n"
            resposta += "💡 **DTA (Declaração de Trânsito Aduaneiro)**: Cargas que já chegaram e estão sendo removidas para outro recinto alfandegado, onde será registrada uma DI ou DUIMP posteriormente.\n\n"
            
            for proc in processos:
                proc_ref = proc.get('processo_referencia', 'N/A')
                numero_dta = proc.get('numero_dta', 'N/A')
                doc_despacho = proc.get('documento_despacho', '')
                num_doc_despacho = proc.get('numero_documento_despacho', '')
                ce = proc.get('numero_ce', '')
                situacao_ce = proc.get('situacao_ce', '')
                etapa = proc.get('etapa_kanban', '')
                modal = proc.get('modal', '')
                
                resposta += f"**{proc_ref}**\n"
                resposta += f"   🚚 **DTA:** {numero_dta}\n"
                if doc_despacho:
                    resposta += f"   📄 **Documento Despacho:** {doc_despacho}"
                    if num_doc_despacho:
                        resposta += f" ({num_doc_despacho})"
                    resposta += "\n"
                # ✅ CORREÇÃO: Só mostrar CE se o modal for Marítimo
                # Processos rodoviários e aéreos não têm CE
                if ce and modal and 'marítimo' in modal.lower():
                    resposta += f"   📦 **CE:** {ce}"
                    if situacao_ce:
                        resposta += f" ({situacao_ce})"
                    resposta += "\n"
                if etapa:
                    resposta += f"   📊 **Etapa:** {etapa}\n"
                if modal:
                    # Usar emoji correto baseado no modal
                    if 'rodovi' in modal.lower() or 'terrestre' in modal.lower():
                        emoji_modal = "🚚"
                    elif 'aéreo' in modal.lower() or 'aereo' in modal.lower():
                        emoji_modal = "✈️"
                    else:
                        emoji_modal = "🚢"
                    resposta += f"   {emoji_modal} **Modal:** {modal}\n"
                resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta
            }
        except Exception as e:
            logger.error(f'❌ Erro ao listar processos em DTA: {e}', exc_info=True)
            return {
                'sucesso': False,
                'resposta': f'❌ Erro ao listar processos em DTA: {str(e)}'
            }
    
    def _listar_com_pendencias(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos com pendências."""
        categoria = arguments.get('categoria', '').strip().upper() if arguments.get('categoria') else None
        limite = arguments.get('limite', 200)
        
        # ✅ CORREÇÃO: Se não tem categoria, usar listar_todos_processos_por_situacao
        if not categoria:
            try:
                from db_manager import listar_todos_processos_por_situacao
                
                logger.info(f'🔍 listar_processos_com_pendencias: Sem categoria, usando listar_todos_processos_por_situacao com filtro_pendencias=True (limite={limite})')
                
                processos = listar_todos_processos_por_situacao(
                    situacao_filtro=None,
                    filtro_pendencias=True,
                    filtro_bloqueio=False,
                    limit=limite
                )
                
                logger.info(f'🔍 listar_processos_com_pendencias: Encontrados {len(processos)} processos com pendências (todas as categorias)')
                
                if not processos:
                    resposta = f"✅ **Nenhum processo com pendências encontrado.**\n\n"
                    resposta += f"💡 **Dica:** Todos os processos estão sem pendências de frete, AFRMM ou bloqueios."
                else:
                    resposta = f"⚠️ **Processos com Pendências** ({len(processos)} processo(s))\n\n"
                    
                    for proc in processos:
                        proc_ref = proc.get('processo_referencia', '')
                        resposta += f"**{proc_ref}**\n"
                        
                        # Listar pendências
                        pendencias_lista = []
                        
                        # CE
                        ce = proc.get('ce')
                        if ce:
                            situacao_ce = ce.get('situacao', '')
                            resposta += f"   📦 CE {ce.get('numero', 'N/A')}: {situacao_ce if situacao_ce else 'N/A'}\n"
                            
                            if ce.get('pendencia_frete', False):
                                pendencias_lista.append("💰 Pendência de Frete")
                            if ce.get('pendencia_afrmm', False):
                                pendencias_lista.append("⚓ Pendência de AFRMM")
                        
                        # CCT
                        cct = proc.get('cct')
                        if cct:
                            situacao_cct = cct.get('situacao', '')
                            resposta += f"   ✈️ CCT {cct.get('numero', 'N/A')}: {situacao_cct if situacao_cct else 'N/A'}\n"
                            
                            if cct.get('pendencia_frete', False):
                                pendencias_lista.append("💰 Pendência de Frete")
                        
                        # DI
                        di = proc.get('di')
                        if di:
                            situacao_di = di.get('situacao', '')
                            canal_di = di.get('canal', '')
                            resposta += f"   📄 DI {di.get('numero', 'N/A')}: {situacao_di.lower() if situacao_di else 'N/A'}"
                            if canal_di:
                                resposta += f" (Canal: {canal_di})"
                            resposta += "\n"
                        
                        # DUIMP
                        duimp = proc.get('duimp')
                        if duimp:
                            situacao_duimp = duimp.get('situacao', '')
                            canal_duimp = duimp.get('canal', '')
                            resposta += f"   ⚠️ DUIMP {duimp.get('numero', 'N/A')} v{duimp.get('versao', 'N/A')}: {situacao_duimp.lower() if situacao_duimp else 'N/A'}"
                            if canal_duimp:
                                resposta += f" (Canal: {canal_duimp})"
                            resposta += "\n"
                        
                        # Mostrar lista de pendências
                        if pendencias_lista:
                            resposta += f"   ⚠️ **Pendências:** {', '.join(pendencias_lista)}\n"
                        
                        resposta += "\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': processos
                }
            except Exception as e:
                logger.error(f'Erro ao listar processos com pendências (sem categoria): {e}', exc_info=True)
                return {
                    'sucesso': False,
                    'erro': str(e),
                    'resposta': f'❌ Erro ao buscar processos com pendências: {str(e)}'
                }
        
        try:
            from db_manager import listar_processos_por_categoria_e_situacao
            
            logger.info(f'🔍 listar_processos_com_pendencias: Buscando processos {categoria} com pendências (limite={limite})')
            
            # Buscar processos da categoria filtrados por pendências
            processos = listar_processos_por_categoria_e_situacao(categoria, situacao_filtro=None, filtro_pendencias=True, limit=limite)
            
            logger.info(f'🔍 listar_processos_com_pendencias: Encontrados {len(processos)} processos {categoria} com pendências')
            
            # ✅ DEBUG: Log detalhado se não encontrou processos mas a categoria existe
            if not processos:
                # Verificar se existem processos da categoria sem pendências
                from db_manager import listar_processos_por_categoria
                processos_todos = listar_processos_por_categoria(categoria, limit=10)
                if processos_todos:
                    logger.warning(f'⚠️ listar_processos_com_pendencias: Encontrados {len(processos_todos)} processos {categoria} no total, mas nenhum com pendências detectadas')
                
                resposta = f"✅ **Nenhum processo {categoria} com pendências encontrado.**\n\n"
                resposta += f"💡 **Dica:** Todos os processos {categoria} estão sem pendências de frete, AFRMM ou bloqueios."
            else:
                resposta = f"⚠️ **Processos {categoria} com Pendências** ({len(processos)} processo(s))\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    resposta += f"**{proc_ref}**\n"
                    
                    # Listar pendências
                    pendencias_lista = []
                    
                    # CE
                    ce = proc.get('ce')
                    if ce:
                        situacao_ce = ce.get('situacao', '')
                        resposta += f"   📦 CE {ce.get('numero', 'N/A')}: {situacao_ce if situacao_ce else 'N/A'}\n"
                        
                        # ⚠️ IMPORTANTE: listar_processos_com_pendencias retorna APENAS pendências (frete, AFRMM), NÃO bloqueios
                        if ce.get('pendencia_frete', False):
                            pendencias_lista.append("💰 Pendência de Frete")
                        if ce.get('pendencia_afrmm', False):
                            pendencias_lista.append("⚓ Pendência de AFRMM")
                        # ⚠️ NÃO incluir bloqueios aqui - bloqueios são tratados separadamente
                    
                    # CCT
                    cct = proc.get('cct')
                    if cct:
                        situacao_cct = cct.get('situacao', '')
                        resposta += f"   ✈️ CCT {cct.get('numero', 'N/A')}: {situacao_cct if situacao_cct else 'N/A'}\n"
                        
                        # ⚠️ IMPORTANTE: listar_processos_com_pendencias retorna APENAS pendências (frete), NÃO bloqueios
                        if cct.get('pendencia_frete', False):
                            pendencias_lista.append("💰 Pendência de Frete")
                        # ⚠️ NÃO incluir bloqueios aqui - bloqueios são tratados separadamente
                    
                    # DI
                    di = proc.get('di')
                    if di:
                        situacao_di = di.get('situacao', '')
                        canal_di = di.get('canal', '')
                        resposta += f"   📄 DI {di.get('numero', 'N/A')}: {situacao_di.lower() if situacao_di else 'N/A'}"
                        if canal_di:
                            resposta += f" (Canal: {canal_di})"
                        resposta += "\n"
                    
                    # DUIMP
                    duimp = proc.get('duimp')
                    if duimp:
                        situacao_duimp = duimp.get('situacao', '')
                        canal_duimp = duimp.get('canal', '')
                        resposta += f"   ⚠️ DUIMP {duimp.get('numero', 'N/A')} v{duimp.get('versao', 'N/A')}: {situacao_duimp.lower() if situacao_duimp else 'N/A'}"
                        if canal_duimp:
                            resposta += f" (Canal: {canal_duimp})"
                        resposta += "\n"
                    
                    # ✅ NOVO: ShipsGo (ETA/Porto/Navio/Status)
                    shipsgo = proc.get('shipsgo')
                    if shipsgo:
                        eta = shipsgo.get('shipsgo_eta')
                        porto_codigo = shipsgo.get('shipsgo_porto_codigo', '')
                        porto_nome = shipsgo.get('shipsgo_porto_nome', '')
                        navio = shipsgo.get('shipsgo_navio', '')
                        status = shipsgo.get('shipsgo_status', '')
                        
                        if eta:
                            try:
                                from datetime import datetime
                                eta_date = datetime.fromisoformat(eta.replace('Z', '+00:00'))
                                eta_formatado = eta_date.strftime('%d/%m/%Y, %H:%M:%S')
                                resposta += f"   🚢 ETA: {eta_formatado}"
                            except:
                                resposta += f"   🚢 ETA: {eta}"
                        
                        if porto_codigo or porto_nome:
                            porto_txt = ' · '.join(filter(None, [porto_codigo, porto_nome]))
                            resposta += f" ⚓ Porto: {porto_txt}"
                        
                        if navio:
                            resposta += f" 🚢 Navio: {navio}"
                        
                        if status:
                            resposta += f" 📊 Status: {status}"
                        
                        if eta or porto_codigo or porto_nome or navio or status:
                            resposta += "\n"
                    
                    # Listar pendências encontradas
                    if pendencias_lista:
                        resposta += f"   ⚠️ **Pendências:** {', '.join(pendencias_lista)}\n"
                    
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'categoria': categoria
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos com pendências {categoria}: {e}')
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'mensagem': f'Erro ao buscar processos {categoria} com pendências: {str(e)}'
            }
    
    def _listar_todos_por_situacao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Lista todos os processos por situação (sem filtro de categoria).
        
        Suporta filtros adicionais:
        - filtro_pendencias: Filtra processos com pendências
        - filtro_bloqueio: Filtra processos com bloqueios
        - filtro_data_desembaraco: Filtra por data de desembaraço ("hoje", "semana", "mes", data DD/MM/AAAA)
        """
        situacao = arguments.get('situacao', '').strip().lower() or None
        filtro_pendencias = arguments.get('filtro_pendencias', False)
        filtro_bloqueio = arguments.get('filtro_bloqueio', False)
        filtro_data_desembaraco = arguments.get('filtro_data_desembaraco')  # ✅ NOVO: Filtro de data
        limite = arguments.get('limite', 500)
        
        try:
            from db_manager import listar_todos_processos_por_situacao
            
            # Buscar processos de todas as categorias filtrados
            processos = listar_todos_processos_por_situacao(
                situacao_filtro=situacao,
                filtro_pendencias=filtro_pendencias,
                filtro_bloqueio=filtro_bloqueio,
                filtro_data_desembaraco=filtro_data_desembaraco,  # ✅ NOVO: Passar filtro de data
                limit=limite
            )
            
            if not processos:
                # Determinar o que foi solicitado
                filtro_desc = []
                if situacao:
                    filtro_desc.append(f"situação '{situacao}'")
                if filtro_pendencias:
                    filtro_desc.append("pendências")
                if filtro_bloqueio:
                    filtro_desc.append("bloqueios")
                
                filtro_texto = ", ".join(filtro_desc) if filtro_desc else "nenhum filtro"
                
                resposta = f"⚠️ **Nenhum processo com {filtro_texto} encontrado.**\n\n"
                resposta += f"💡 **Dica:** Verifique se existem processos com essas características no sistema."
            else:
                # Determinar título baseado nos filtros
                titulo = "Processos"
                if situacao:
                    titulo_situacao = situacao.replace('_', ' ').title()
                    titulo += f" - {titulo_situacao}"
                if filtro_pendencias:
                    titulo += " com Pendências"
                if filtro_bloqueio:
                    titulo += " com Bloqueio"
                
                resposta = f"📋 **{titulo}** ({len(processos)} processo(s))\n\n"
                
                for proc in processos:
                    proc_ref = proc.get('processo_referencia', '')
                    resposta += f"**{proc_ref}**\n"
                    
                    # DI
                    di = proc.get('di')
                    if di:
                        situacao_di = di.get('situacao', '')
                        canal_di = di.get('canal', '')
                        data_desembaraco = di.get('data_desembaraco', '')
                        
                        resposta += f"   📄 DI {di.get('numero', 'N/A')}: {situacao_di.lower() if situacao_di else 'N/A'}"
                        if canal_di:
                            resposta += f" (Canal: {canal_di})"
                        resposta += "\n"
                        
                        # ✅ CORREÇÃO: Sempre mostrar data de desembaraço se disponível (não apenas quando situacao contém 'desembarac')
                        if data_desembaraco:
                            try:
                                from datetime import datetime
                                # Tentar múltiplos formatos
                                data_limpa = str(data_desembaraco).replace('Z', '').replace('+00:00', '').strip()
                                if '.' in data_limpa:
                                    data_limpa = data_limpa.split('.')[0]
                                
                                dt = None
                                if 'T' in data_limpa:
                                    try:
                                        dt = datetime.fromisoformat(data_limpa)
                                    except:
                                        pass
                                
                                if not dt:
                                    formatos = [
                                        "%Y-%m-%dT%H:%M:%S",
                                        "%Y-%m-%d %H:%M:%S", 
                                        "%Y-%m-%d"
                                    ]
                                    for fmt in formatos:
                                        try:
                                            dt = datetime.strptime(data_limpa, fmt)
                                            break
                                        except:
                                            continue
                                
                                if dt:
                                    data_formatada = dt.strftime('%d/%m/%Y')
                                    resposta += f"   📅 Data de Desembaraço: {data_formatada}\n"
                                else:
                                    resposta += f"   📅 Data de Desembaraço: {data_desembaraco}\n"
                            except Exception as e:
                                logger.debug(f'Erro ao formatar data de desembaraço: {e}')
                                resposta += f"   📅 Data de Desembaraço: {data_desembaraco}\n"
                    
                    # DUIMP
                    duimp = proc.get('duimp')
                    if duimp:
                        situacao_duimp = duimp.get('situacao', '')
                        canal_duimp = duimp.get('canal', '')
                        resposta += f"   ⚠️ DUIMP {duimp.get('numero', 'N/A')} v{duimp.get('versao', 'N/A')}: {situacao_duimp.lower() if situacao_duimp else 'N/A'}"
                        if canal_duimp:
                            resposta += f" (Canal: {canal_duimp})"
                        resposta += "\n"
                    
                    # CE
                    ce = proc.get('ce')
                    if ce:
                        situacao_ce = ce.get('situacao', '')
                        resposta += f"   📦 CE {ce.get('numero', 'N/A')}: {situacao_ce if situacao_ce else 'N/A'}\n"
                        
                        # Mostrar pendências e bloqueios se existirem
                        if filtro_pendencias or filtro_bloqueio:
                            pendencias_lista = []
                            if ce.get('pendencia_frete', False):
                                pendencias_lista.append("💰 Pendência de Frete")
                            if ce.get('pendencia_afrmm', False):
                                pendencias_lista.append("⚓ Pendência de AFRMM")
                            
                            # ✅ NOVO: Extrair detalhes dos bloqueios do array bloqueio[]
                            dados_completos = ce.get('dados_completos', {})
                            bloqueios_detalhes = []
                            if dados_completos and isinstance(dados_completos, dict):
                                bloqueios_array = dados_completos.get('bloqueio', [])
                                if isinstance(bloqueios_array, list) and len(bloqueios_array) > 0:
                                    for bloqueio in bloqueios_array:
                                        if isinstance(bloqueio, dict):
                                            descricao_tipo = bloqueio.get('descricaoTipo', '')
                                            codigo_tipo = bloqueio.get('codigoTipo', '')
                                            if descricao_tipo:
                                                bloqueios_detalhes.append(f"🚫 {descricao_tipo}")
                                            elif codigo_tipo:
                                                bloqueios_detalhes.append(f"🚫 Bloqueio Tipo {codigo_tipo}")
                            
                            # Fallback: usar campos booleanos se array não estiver disponível
                            if not bloqueios_detalhes:
                                if ce.get('carga_bloqueada', False):
                                    bloqueios_detalhes.append("🔒 Carga Bloqueada")
                                if ce.get('bloqueio_impede_despacho', False):
                                    bloqueios_detalhes.append("🚫 Bloqueio Impede Despacho")
                            
                            if bloqueios_detalhes:
                                pendencias_lista.extend(bloqueios_detalhes)
                            
                            if pendencias_lista:
                                resposta += f"   ⚠️ **Pendências/Bloqueios:** {', '.join(pendencias_lista)}\n"
                    
                    # CCT
                    cct = proc.get('cct')
                    if cct:
                        situacao_cct = cct.get('situacao', '')
                        resposta += f"   ✈️ CCT {cct.get('numero', 'N/A')}: {situacao_cct if situacao_cct else 'N/A'}\n"
                    
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(processos),
                'situacao': situacao,
                'filtro_pendencias': filtro_pendencias,
                'filtro_bloqueio': filtro_bloqueio
            }
        except Exception as e:
            logger.error(f'Erro ao listar todos os processos por situação: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos: {str(e)}'
            }
    
    def _consultar_processo_consolidado(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta processo com dados consolidados (DI, DUIMP, CE, CCT, pendências).
        
        Retorna informações completas do processo em formato consolidado.
        """
        processo_ref = arguments.get('processo_referencia', '').strip()
        
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
            # ✅ CORREÇÃO: Chamar função diretamente em vez de fazer requisição HTTP
            # (estamos no mesmo processo, não precisa de HTTP)
            from db_manager import gerar_json_consolidado_processo
            
            json_consolidado = gerar_json_consolidado_processo(processo_completo)
            
            # Verificar se há erro no JSON consolidado
            if 'erro' in json_consolidado:
                logger.error(f'Erro ao gerar JSON consolidado: {json_consolidado.get("erro")}')
                return {
                    'sucesso': False,
                    'erro': 'ERRO_GERAR_CONSOLIDADO',
                    'resposta': f'❌ {json_consolidado.get("erro", "Erro ao gerar JSON consolidado")}'
                }
            
            # Se não houver erro, continuar com o processamento
            if json_consolidado:
                # Construir resposta formatada para a IA
                resposta = f"📋 **Processo {processo_completo}**\n\n"
                
                # ✅ CORREÇÃO: Mostrar todas as declarações (DI e DUIMP)
                # ✅ VALIDAÇÃO: Garantir que declaracoes é uma lista
                declaracoes = json_consolidado.get('declaracoes', [])
                if not isinstance(declaracoes, list):
                    # Se não é lista, tentar converter ou criar lista vazia
                    declaracao = json_consolidado.get('declaracao')
                    if isinstance(declaracao, dict):
                        declaracoes = [declaracao]
                    else:
                        declaracoes = []
                
                if not declaracoes:
                    # Fallback: usar declaração principal se não houver lista
                    declaracao = json_consolidado.get('declaracao')
                    if isinstance(declaracao, dict):
                        declaracoes = [declaracao]
                
                # Mostrar DI primeiro (se houver)
                di_encontrada = None
                duimp_encontrada = None
                for decl in declaracoes:
                    # ✅ VALIDAÇÃO: Verificar se decl é um dict antes de usar .get()
                    if not isinstance(decl, dict):
                        continue
                    if decl.get('tipo') == 'DI':
                        di_encontrada = decl
                    elif decl.get('tipo') == 'DUIMP':
                        duimp_encontrada = decl
                
                # Mostrar DI se houver
                if di_encontrada:
                    situacao_di = di_encontrada.get('situacao', '')
                    canal_di = di_encontrada.get('canal', '')
                    numero_protocolo = di_encontrada.get('numero_protocolo', '')
                    situacao_entrega = di_encontrada.get('situacao_entrega_carga', '')
                    modalidade = di_encontrada.get('modalidade', '')
                    datas_di = di_encontrada.get('datas', {})
                    
                    di_numero = json_consolidado.get('chaves', {}).get('di', '')
                    if di_numero:
                        resposta += f"📄 **DI {di_numero}:** {situacao_di.lower() if situacao_di else 'N/A'}\n"
                    else:
                        resposta += f"📄 **DI:** {situacao_di.lower() if situacao_di else 'N/A'}\n"
                    
                    # Canal
                    if canal_di:
                        resposta += f"   - Canal: {canal_di}\n"
                    
                    # Protocolo
                    if numero_protocolo:
                        resposta += f"   - Protocolo: {numero_protocolo}\n"
                    
                    # Situação de Entrega da Carga
                    if situacao_entrega:
                        resposta += f"   - Situação de Entrega: {situacao_entrega}\n"
                    
                    # Modalidade de Despacho
                    if modalidade and modalidade != 'NORMAL':
                        resposta += f"   - Modalidade: {modalidade}\n"
                    
                    # Datas importantes
                    if isinstance(datas_di, dict):
                        data_registro = datas_di.get('registro')
                        data_desembaraco = datas_di.get('desembaraco')
                        data_autorizacao = datas_di.get('autorizacao_entrega')
                        data_situacao = datas_di.get('situacao_atualizada_em')
                        
                        if data_registro:
                            # Formatar data para exibição legível
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(data_registro.replace('Z', '+00:00'))
                                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                                resposta += f"   - Data de Registro: {data_formatada}\n"
                            except:
                                resposta += f"   - Data de Registro: {data_registro}\n"
                        
                        if data_desembaraco:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(data_desembaraco.replace('Z', '+00:00'))
                                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                                resposta += f"   - Data de Desembaraço: {data_formatada}\n"
                            except:
                                resposta += f"   - Data de Desembaraço: {data_desembaraco}\n"
                        
                        if data_autorizacao:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(data_autorizacao.replace('Z', '+00:00'))
                                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                                resposta += f"   - Data de Autorização de Entrega: {data_formatada}\n"
                            except:
                                resposta += f"   - Data de Autorização de Entrega: {data_autorizacao}\n"
                        
                        if data_situacao:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(data_situacao.replace('Z', '+00:00'))
                                data_formatada = dt.strftime('%d/%m/%Y %H:%M')
                                resposta += f"   - Situação Atualizada em: {data_formatada}\n"
                            except:
                                resposta += f"   - Situação Atualizada em: {data_situacao}\n"
                    
                    resposta += "\n"
                
                # Mostrar DUIMP se houver
                if duimp_encontrada:
                    situacao_duimp = duimp_encontrada.get('situacao', '')
                    canal_duimp = duimp_encontrada.get('canal', '')
                    duimp_numero = json_consolidado.get('chaves', {}).get('duimp_num', '')
                    if duimp_numero:
                        resposta += f"⚠️ **DUIMP {duimp_numero}:** {situacao_duimp.lower() if situacao_duimp else 'N/A'}\n"
                    else:
                        resposta += f"⚠️ **DUIMP:** {situacao_duimp.lower() if situacao_duimp else 'N/A'}\n"
                    if canal_duimp:
                        resposta += f"   - Canal: {canal_duimp}\n"
                    resposta += "\n"
                
                # Pendências
                pendencias = json_consolidado.get('pendencias', {})
                if pendencias.get('frete'):
                    resposta += f"⚠️ **Pendência de Frete:** Sim\n"
                else:
                    resposta += f"✅ **Pendência de Frete:** Não\n"
                
                if pendencias.get('afrmm'):
                    resposta += f"⚠️ **Pendência de AFRMM:** Sim\n"
                else:
                    resposta += f"✅ **Pendência de AFRMM:** Não\n"
                
                # CEs
                ces = json_consolidado.get('chaves', {}).get('ce_house') or json_consolidado.get('chaves', {}).get('ce_master')
                if ces:
                    resposta += f"\n📦 **Conhecimentos de Embarque (CE):**\n"
                    if json_consolidado.get('chaves', {}).get('ce_house'):
                        ce_num = json_consolidado['chaves']['ce_house']
                        # Buscar situação do CE
                        for leg in json_consolidado.get('movimentacao', {}).get('legs', []):
                            if leg.get('fonte') == 'CE':
                                situacao = leg.get('status', {}).get('situacao', '')
                                resposta += f"   - CE {ce_num}: {situacao}\n"
                                break
                
                # CCTs
                legs = json_consolidado.get('movimentacao', {}).get('legs', [])
                ccts_legs = [leg for leg in legs if leg.get('fonte') == 'CCT']
                if ccts_legs:
                    resposta += f"\n✈️ **Conhecimentos de Carga Aérea (CCT):**\n"
                    # Buscar número do CCT do processo (da tabela processo_documentos)
                    try:
                        from db_manager import listar_documentos_processo
                        documentos = listar_documentos_processo(processo_completo)
                        ccts = [doc for doc in documentos if doc.get('tipo_documento') == 'CCT']
                        for i, leg in enumerate(ccts_legs):
                            situacao = leg.get('status', {}).get('situacao', '')
                            if i < len(ccts):
                                cct_num = ccts[i].get('numero_documento', '')
                                resposta += f"   - CCT {cct_num}: {situacao}\n"
                            else:
                                resposta += f"   - CCT: {situacao}\n"
                    except Exception as e:
                        logger.warning(f'Erro ao buscar CCTs do processo {processo_completo}: {e}')
                        for leg in ccts_legs:
                            situacao = leg.get('status', {}).get('situacao', '')
                            resposta += f"   - CCT: {situacao}\n"
                
                return {
                    'sucesso': True,
                    'resposta': resposta,
                    'dados': json_consolidado
                }
            else:
                return {
                    'sucesso': False,
                    'erro': 'PROCESSO_NAO_ENCONTRADO',
                    'resposta': f'❌ Processo {processo_completo} não encontrado.'
                }
        except Exception as e:
            logger.error(f'Erro ao consultar processo consolidado {processo_completo}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_INTERNO',
                'resposta': f'❌ Erro ao consultar processo consolidado: {str(e)}'
            }
    
    def _listar_processos_com_duimp(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Lista processos que têm DUIMP registrada."""
        limite = arguments.get('limite', 50)
        
        # Buscar processos com DUIMP no banco
        try:
            import sqlite3
            from db_manager import get_db_connection
            
            conn = get_db_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Buscar DUIMPs com processo_referencia
            cursor.execute('''
                SELECT DISTINCT processo_referencia, numero, versao, status, ambiente, criado_em
                FROM duimps
                WHERE processo_referencia IS NOT NULL AND processo_referencia != ''
                ORDER BY criado_em DESC
                LIMIT ?
            ''', (limite,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                resposta = "⚠️ **Nenhum processo com DUIMP registrada encontrado.**"
            else:
                resposta = f"📋 **Processos com DUIMP Registrada** ({len(rows)} processo(s))\n\n"
                for row in rows:
                    proc_ref = row[0]
                    duimp_num = row[1]
                    duimp_versao = row[2]
                    duimp_status = row[3]
                    ambiente = row[4]
                    
                    resposta += f"**{proc_ref}**\n"
                    resposta += f"   - DUIMP: {duimp_num} v{duimp_versao}\n"
                    resposta += f"   - Status DUIMP: {duimp_status}\n"
                    resposta += f"   - Ambiente: {ambiente}\n"
                    resposta += "\n"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'total': len(rows) if rows else 0
            }
        except Exception as e:
            logger.error(f'Erro ao listar processos com DUIMP: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': 'ERRO_BUSCA',
                'resposta': f'❌ Erro ao buscar processos com DUIMP: {str(e)}'
            }
    
    def _formatar_resposta_processo_dto(self, processo_dto, processo_referencia: str, mensagem_original: Optional[str] = None) -> Dict[str, Any]:
        """
        Formata resposta usando ProcessoKanbanDTO.
        
        ✅ NOVO: Usa dados do repositório (Kanban ou SQL Server)
        ✅ MELHORIA: Detecta tipo de pergunta e responde de forma mais direta
        """
        try:
            from services.models.processo_kanban_dto import ProcessoKanbanDTO
            
            # ✅ NOVO: Detectar tipo de pergunta para resposta mais direta
            mensagem_lower = mensagem_original.lower() if mensagem_original else ''
            
            # ✅ CRÍTICO: Se a pergunta é especificamente sobre o CE, buscar dados completos do CE
            pergunta_sobre_ce = bool(
                re.search(r'como\s+est[ao]\s+o\s+ce|status\s+do\s+ce|situa[çc][ãa]o\s+do\s+ce|dados\s+do\s+ce|informa[çc][õo]es\s+do\s+ce|detalhes\s+do\s+ce|ce\s+do\s+[a-z]{3}\.|o\s+ce\s+do', mensagem_lower)
            ) if mensagem_original else False
            
            # Se pergunta é sobre CE e tem número de CE, buscar dados completos
            if pergunta_sobre_ce and processo_dto.numero_ce:
                logger.info(f'🔍 Pergunta específica sobre CE detectada. Buscando dados completos do CE {processo_dto.numero_ce}...')
                try:
                    from services.ce_agent import CeAgent
                    ce_agent = CeAgent()
                    resultado_ce = ce_agent._consultar_ce_maritimo({
                        'numero_ce': processo_dto.numero_ce,
                        'processo_referencia': processo_referencia
                    }, context={'mensagem_original': mensagem_original})
                    
                    if resultado_ce and resultado_ce.get('sucesso'):
                        # Retornar resposta do CE diretamente (mais completa)
                        return resultado_ce
                    else:
                        logger.warning(f'⚠️ Não foi possível buscar dados completos do CE {processo_dto.numero_ce}, usando dados básicos do DTO')
                except Exception as e:
                    logger.warning(f'⚠️ Erro ao buscar dados completos do CE: {e}, usando dados básicos do DTO')
            # ✅ UX: usuários perguntam "quando chega", "chega quando", "previsão/ETA", além de "já chegou?"
            pergunta_quando_chega = bool(re.search(r'\b(quando|qdo)\b.*\bcheg', mensagem_lower)) if mensagem_lower else False
            pergunta_eta = any(p in mensagem_lower for p in [' eta', 'previs', 'previsão', 'previsao']) if mensagem_lower else False
            pergunta_chegou = any(palavra in mensagem_lower for palavra in ['chegou', 'chegou?', 'chegaram', 'chega', 'chegar', 'chegada']) or pergunta_quando_chega or pergunta_eta
            pergunta_armazenou = any(palavra in mensagem_lower for palavra in ['armazenou', 'armazenou?', 'aramzenou', 'aramzenou?', 'armazenado', 'armazenada'])
            pergunta_desembaracou = any(palavra in mensagem_lower for palavra in ['desembaraçou', 'desembaraçou?', 'desembaracou', 'desembaracou?', 'desembaraçado', 'desembaracado'])
            pergunta_desbloqueou = any(palavra in mensagem_lower for palavra in ['desbloqueou', 'desbloqueou?', 'desbloqueado', 'desbloqueado?', 'bloqueio'])
            
            resposta_inicial = ""
            tem_resposta_direta = False
            
            # ✅ Respostas diretas para perguntas específicas
            if pergunta_chegou:
                tem_resposta_direta = True
                logger.info(f"🎯 Detectada pergunta sobre chegada para processo {processo_referencia}")
                # Verificar se chegou
                situacoes_chegou = ['ENTREGUE', 'DESCARREGADA', 'ARMAZENADA']
                chegou = processo_dto.situacao_ce and processo_dto.situacao_ce.upper() in situacoes_chegou
                
                # ✅ Buscar data de chegada de múltiplos campos do JSON do Kanban
                data_chegada = None
                if processo_dto.dados_completos:
                    json_data = processo_dto.dados_completos
                    
                    # Helper para parsear data
                    def parse_date(date_str):
                        if not date_str:
                            return None
                        from datetime import datetime
                        if isinstance(date_str, datetime):
                            return date_str
                        if isinstance(date_str, str):
                            # Tentar vários formatos
                            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
                                try:
                                    date_str_clean = date_str.split('T')[0].split(' ')[0]
                                    return datetime.strptime(date_str_clean, "%Y-%m-%d")
                                except:
                                    continue
                        return None
                    
                    # Tentar vários campos de data de chegada ao porto do Kanban (em ordem de prioridade)
                    # ⚠️ CONTEXTO: Chegada = carga chegou ao porto (NÃO entrega ao cliente)
                    # ⚠️ IMPORTANTE: NUNCA usar dataPrevisaoChegada (ETA) como data confirmada!
                    # ⚠️ IMPORTANTE: NUNCA usar dataEntrega (é entrega ao cliente, não chegada ao porto)!
                    # ⚠️ IMPORTANTE: NUNCA usar dataSituacaoCargaCe (é mudança de status, não chegada)!
                    campos_data_chegada = [
                        'dataDestinoFinal',        # Data de chegada da carga ao porto (Kanban) - mais confiável
                        'dataArmazenamento',       # Data de armazenamento (confirma que chegou e foi armazenada)
                        'dataAtracamento',         # Data da atracação do navio (se atracou, carga chegou - exceto sinistros)
                        # ❌ REMOVIDO: 'dataEntrega' - é entrega ao cliente, não chegada ao porto!
                        # ❌ REMOVIDO: 'dataPrevisaoChegada' - ETA não é data confirmada!
                        # ❌ REMOVIDO: 'dataSituacaoCargaCe' - é mudança de status do CE, não chegada!
                    ]
                    
                    for campo in campos_data_chegada:
                        data_raw = json_data.get(campo)
                        if data_raw:
                            data_chegada = parse_date(data_raw)
                            if data_chegada:
                                break
                    
                    # ⚠️ NUNCA usar shipgov2.destino_data_chegada como fallback - é ETA (previsão), não data confirmada!
                    # Se não encontrou nos campos confirmados acima, não usar ETA
                
                # Se não encontrou no JSON, usar data_entrega do DTO
                if not data_chegada:
                    data_chegada = processo_dto.data_entrega
                
                # Se a pergunta foi "quando chega"/ETA, responder focado em ETA (sem “sim/não chegou”)
                if pergunta_quando_chega or pergunta_eta:
                    resposta_inicial += f"📅 **Previsão de chegada do processo {processo_referencia} (ETA/POD):**\n"

                    # ✅ Buscar ETA/POD de múltiplas fontes (DTO, JSON direto, shipgov2)
                    eta_para_exibir = processo_dto.eta_iso
                    logger.info(f'🔍 [ETA] Processo {processo_referencia}: eta_iso do DTO = {eta_para_exibir}')
                    
                    # Se não encontrou no DTO, tentar buscar diretamente do JSON do Kanban
                    if not eta_para_exibir and processo_dto.dados_completos:
                        json_data = processo_dto.dados_completos
                        logger.info(f'🔍 [ETA] Processo {processo_referencia}: Buscando POD/ETA diretamente do JSON do Kanban (dados_completos disponível)')
                        
                        # Helper para parsear data
                        def parse_eta_date(date_str):
                            if not date_str:
                                return None
                            from datetime import datetime
                            if isinstance(date_str, datetime):
                                return date_str
                            if isinstance(date_str, str):
                                for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
                                    try:
                                        date_str_clean = date_str.split('T')[0].split(' ')[0]
                                        return datetime.strptime(date_str_clean, "%Y-%m-%d")
                                    except:
                                        continue
                            return None
                        
                        # 1. Tentar POD direto do JSON (campo do Kanban)
                        # ✅ EXPANDIDO: Buscar POD em múltiplos formatos possíveis (mesmo que ProcessoKanbanDTO)
                        pod_data = (
                            json_data.get('pod') or 
                            json_data.get('POD') or 
                            json_data.get('portOfDischarge') or
                            json_data.get('port_of_discharge') or
                            json_data.get('dataPod') or
                            json_data.get('data_pod') or
                            json_data.get('etaPod') or
                            json_data.get('eta_pod')
                        )
                        logger.debug(f'🔍 [ETA] Processo {processo_referencia}: pod_data encontrado = {pod_data} (tipo: {type(pod_data).__name__ if pod_data else "None"})')
                        if pod_data:
                            if isinstance(pod_data, dict):
                                eta_para_exibir = (
                                    parse_eta_date(pod_data.get('data')) or 
                                    parse_eta_date(pod_data.get('eta')) or 
                                    parse_eta_date(pod_data.get('dataChegada')) or
                                    parse_eta_date(pod_data.get('data_chegada')) or
                                    parse_eta_date(pod_data.get('dataPod')) or
                                    parse_eta_date(pod_data.get('data_pod'))
                                )
                            elif isinstance(pod_data, str) and '/' in pod_data:
                                # ✅ NOVO: Tentar parsear string no formato DD/MM/YY ou DD/MM/YYYY
                                try:
                                    from datetime import datetime
                                    partes = pod_data.strip().split('/')
                                    if len(partes) == 3:
                                        dia, mes, ano = partes
                                        if len(ano) == 2:
                                            ano = '20' + ano  # Assumir século 21
                                        data_str = f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
                                        eta_para_exibir = parse_eta_date(data_str)
                                except:
                                    eta_para_exibir = parse_eta_date(pod_data)
                            else:
                                eta_para_exibir = parse_eta_date(pod_data)
                        
                        # 2. Se não encontrou POD, tentar shipgov2.destino_data_chegada (previsão/ETA)
                        if not eta_para_exibir:
                            shipgov2 = json_data.get('shipgov2', {})
                            if isinstance(shipgov2, dict):
                                destino_data = shipgov2.get('destino_data_chegada')
                                logger.debug(f'🔍 [ETA] Processo {processo_referencia}: shipgov2.destino_data_chegada = {destino_data}')
                                eta_para_exibir = parse_eta_date(destino_data)

                    if eta_para_exibir:
                        try:
                            from datetime import datetime
                            if isinstance(eta_para_exibir, datetime):
                                eta_txt = eta_para_exibir.strftime('%d/%m/%Y')
                            else:
                                eta_txt = str(eta_para_exibir)
                        except Exception:
                            eta_txt = str(eta_para_exibir)

                        resposta_inicial += f"  - ETA: {eta_txt}\n"
                        if processo_dto.porto_nome:
                            resposta_inicial += f"  - Porto: {processo_dto.porto_nome}\n"
                        if processo_dto.nome_navio:
                            resposta_inicial += f"  - Navio: {processo_dto.nome_navio}\n"
                        if processo_dto.status_shipsgo:
                            resposta_inicial += f"  - Status: {processo_dto.status_shipsgo}\n"
                    else:
                        resposta_inicial += "  - ⚠️ ETA não disponível no snapshot do Kanban/cache no momento.\n"

                    resposta_inicial += "\n"
                else:
                    # Pergunta "já chegou?" -> manter resposta sim/não + (se não chegou) mostrar ETA
                    if chegou:
                        resposta_inicial += f"✅ **Sim, o processo {processo_referencia} chegou!**\n\n"
                        resposta_inicial += f"**Situação:** {processo_dto.situacao_ce}\n"
                        if data_chegada:
                            from datetime import datetime
                            if isinstance(data_chegada, datetime):
                                resposta_inicial += f"**Data de chegada:** {data_chegada.strftime('%d/%m/%Y')}\n"
                            else:
                                resposta_inicial += f"**Data de chegada:** {data_chegada}\n"
                    else:
                        resposta_inicial += f"❌ **Não, o processo {processo_referencia} ainda não chegou.**\n\n"
                        if processo_dto.situacao_ce:
                            resposta_inicial += f"**Situação atual:** {processo_dto.situacao_ce}\n"

                        # ✅ NOVO: Buscar ETA/POD de múltiplas fontes (DTO, JSON direto, shipgov2)
                        eta_para_exibir = processo_dto.eta_iso
                        logger.info(f'🔍 [ETA] Processo {processo_referencia}: eta_iso do DTO = {eta_para_exibir}')

                        json_data = processo_dto.dados_completos if (processo_dto.dados_completos and isinstance(processo_dto.dados_completos, dict)) else {}
                        if not eta_para_exibir and json_data:
                            # 3. Se ainda não encontrou, tentar dataPrevisaoChegada (fallback)
                            data_previsao = json_data.get('dataPrevisaoChegada') or json_data.get('previsaoChegada')
                            logger.debug(f'🔍 [ETA] Processo {processo_referencia}: dataPrevisaoChegada = {data_previsao}')
                            eta_para_exibir = parse_eta_date(data_previsao)

                        logger.info(f'🔍 [ETA] Processo {processo_referencia}: eta_para_exibir após busca no JSON = {eta_para_exibir}')
                        if not eta_para_exibir and not json_data:
                            logger.warning(f'⚠️ [ETA] Processo {processo_referencia}: dados_completos não disponível para buscar POD/ETA')
                    
                    if eta_para_exibir:
                        from datetime import datetime
                        try:
                            eta_str = eta_para_exibir.strftime('%d/%m/%Y') if isinstance(eta_para_exibir, datetime) else str(eta_para_exibir)
                            resposta_inicial += f"**Previsão de chegada (ETA):** {eta_str}\n"
                        except:
                            pass
                resposta_inicial += "\n"
            
            elif pergunta_armazenou:
                tem_resposta_direta = True
                # Verificar se armazenou
                armazenou = processo_dto.situacao_ce and processo_dto.situacao_ce.upper() == 'ARMAZENADA'
                
                if armazenou:
                    resposta_inicial += f"✅ **Sim, o processo {processo_referencia} foi armazenado!**\n\n"
                    resposta_inicial += f"**Situação:** {processo_dto.situacao_ce}\n"
                else:
                    resposta_inicial += f"❌ **Não, o processo {processo_referencia} ainda não foi armazenado.**\n\n"
                    if processo_dto.situacao_ce:
                        resposta_inicial += f"**Situação atual:** {processo_dto.situacao_ce}\n"
                resposta_inicial += "\n"
            
            elif pergunta_desembaracou:
                tem_resposta_direta = True
                # Verificar se desembaraçou
                desembaracou = processo_dto.situacao_di and 'DESEMBARACADA' in processo_dto.situacao_di.upper()
                
                if desembaracou:
                    data_desemb = processo_dto.data_desembaraco.strftime('%d/%m/%Y') if processo_dto.data_desembaraco else 'N/A'
                    resposta_inicial += f"✅ **Sim, o processo {processo_referencia} foi desembaraçado!**\n\n"
                    resposta_inicial += f"**Situação DI:** {processo_dto.situacao_di}\n"
                    if processo_dto.data_desembaraco:
                        resposta_inicial += f"**Data de desembaraço:** {data_desemb}\n"
                else:
                    resposta_inicial += f"❌ **Não, o processo {processo_referencia} ainda não foi desembaraçado.**\n\n"
                    if processo_dto.situacao_di:
                        resposta_inicial += f"**Situação DI atual:** {processo_dto.situacao_di}\n"
                    elif not processo_dto.numero_di:
                        resposta_inicial += f"**Observação:** O processo ainda não possui DI registrada.\n"
                resposta_inicial += "\n"
            
            elif pergunta_desbloqueou:
                tem_resposta_direta = True
                # Verificar bloqueios
                resposta_inicial += f"📋 **Status de bloqueio do processo {processo_referencia}:**\n\n"
                # TODO: Buscar bloqueios do cache do CE
                if processo_dto.numero_ce:
                    resposta_inicial += f"**CE:** {processo_dto.numero_ce}\n"
                    resposta_inicial += f"**Situação:** {processo_dto.situacao_ce or 'N/A'}\n"
                    resposta_inicial += f"\n⚠️ **Nota:** Para verificar bloqueios detalhados, é necessário buscar do cache do CE.\n"
                else:
                    resposta_inicial += f"⚠️ O processo não possui CE vinculado.\n"
                resposta_inicial += "\n"
            
            # ✅ Começar resposta: se tem resposta direta, usar ela; senão, começar do zero
            resposta = resposta_inicial if tem_resposta_direta else ""
            
            # Se não tem resposta direta, começar resposta completa
            if not resposta:
                resposta = f"📋 **Processo {processo_referencia}**\n\n"
            
            # Categoria
            categoria = 'N/A'
            if '.' in processo_referencia:
                categoria = processo_referencia.split('.')[0].upper()
            
            # Se já tem resposta direta, não adicionar categoria separada (já foi respondido)
            if not tem_resposta_direta:
                resposta += f"**Categoria:** {categoria}\n\n"
            
            # Status geral
            if processo_dto.etapa_kanban:
                resposta += f"**Etapa no Kanban:** {processo_dto.etapa_kanban}\n"
            if processo_dto.modal:
                resposta += f"**Modal:** {processo_dto.modal}\n"
            resposta += "\n"
            
            # Documentos
            tem_documentos = False
            
            # CE - ✅ CRÍTICO: Verificar também em dados_completos se numero_ce estiver NULL
            numero_ce_final = processo_dto.numero_ce
            ce_data_completo = None
            
            # Se não tem numero_ce no DTO, tentar extrair dos dados_completos (SQL Server)
            if not numero_ce_final and processo_dto.dados_completos:
                ce_data_completo = processo_dto.dados_completos.get('ce', {})
                if ce_data_completo:
                    numero_ce_final = ce_data_completo.get('numero')
                    logger.info(f'✅ CE encontrado em dados_completos: {numero_ce_final}')
            
            if numero_ce_final:
                tem_documentos = True
                resposta += "**📦 Conhecimento de Embarque:**\n"
                resposta += f"  - CE {numero_ce_final}\n"
                
                # Situação: priorizar do DTO, depois dados_completos
                situacao_ce = processo_dto.situacao_ce
                if not situacao_ce and ce_data_completo:
                    situacao_ce = ce_data_completo.get('situacao')
                if situacao_ce:
                    resposta += f"    - Situação: {situacao_ce}\n"
                
                # ✅ CRÍTICO: Exibir valor de frete do SQL Server se disponível
                if processo_dto.dados_completos and isinstance(processo_dto.dados_completos, dict):
                    ce_data_para_frete = ce_data_completo if ce_data_completo else processo_dto.dados_completos.get('ce', {})
                    if ce_data_para_frete:
                        valor_frete_total = ce_data_para_frete.get('valor_frete_total')
                        if valor_frete_total:
                            resposta += f"    - 💰 Valor Frete Total: R$ {float(valor_frete_total):,.2f}\n"
                
                resposta += "\n"
            
            # DI - ✅ CORREÇÃO: Verificar também em dados_completos mesmo se numero_di estiver NULL
            di_data_completo = None
            numero_di_final = processo_dto.numero_di
            
            logger.info(f"🔍 [DI] Verificando DI para {processo_referencia}: numero_di no DTO={numero_di_final}, tem dados_completos={bool(processo_dto.dados_completos)}")
            
            # Se não tem numero_di no DTO, tentar extrair dos dados_completos (SQL Server)
            if not numero_di_final and processo_dto.dados_completos:
                di_data_completo = processo_dto.dados_completos.get('di', {})
                if di_data_completo:
                    numero_di_final = di_data_completo.get('numero')
                    logger.info(f"✅ [DI] numero_di extraído de dados_completos: {numero_di_final}")
            
            # ✅ CRÍTICO: Se ainda não tem numero_di, tentar buscar do SQL Server usando processo_referencia
            # ✅ CORREÇÃO: Só buscar do SQL Server se estiver disponível (evita timeout)
            if not numero_di_final:
                # Verificar se SQL Server está disponível antes de tentar buscar
                sql_server_disponivel = False
                try:
                    from utils.sql_server_adapter import get_sql_adapter
                    sql_adapter = get_sql_adapter()
                    if sql_adapter:
                        result = sql_adapter.execute_query("SELECT 1 AS test", notificar_erro=False)
                        sql_server_disponivel = result.get('success', False) if result else False
                except Exception as e:
                    logger.debug(f"⚠️ SQL Server não disponível: {e}")
                    sql_server_disponivel = False
                
                if sql_server_disponivel:
                    logger.warning(f"⚠️ [DI] numero_di não encontrado no DTO nem em dados_completos. Buscando DI via processo_referencia {processo_referencia}...")
                    try:
                        from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                        processo_consolidado = buscar_processo_consolidado_sql_server(processo_referencia)
                        if processo_consolidado:
                            logger.info(f"✅ [DI] Processo consolidado encontrado. Tem DI: {bool(processo_consolidado.get('di'))}")
                            if processo_consolidado.get('di'):
                                di_data_completo = processo_consolidado.get('di', {})
                                numero_di_final = di_data_completo.get('numero')
                                if numero_di_final:
                                    logger.info(f"✅ [DI] DI encontrada via SQL Server para {processo_referencia}: {numero_di_final}")
                                    # Atualizar dados_completos do DTO se necessário
                                    if not processo_dto.dados_completos:
                                        processo_dto.dados_completos = {}
                                    if 'di' not in processo_dto.dados_completos:
                                        processo_dto.dados_completos['di'] = di_data_completo
                                else:
                                    logger.warning(f"⚠️ [DI] di_data_completo encontrado mas sem 'numero'. Chaves: {list(di_data_completo.keys())}")
                            else:
                                logger.warning(f"⚠️ [DI] Processo consolidado não tem DI para {processo_referencia}")
                        else:
                            logger.warning(f"⚠️ [DI] Processo consolidado não encontrado para {processo_referencia}")
                    except Exception as e:
                        logger.error(f'❌ [DI] Erro ao buscar DI via processo_referencia {processo_referencia}: {e}', exc_info=True)
            
            # ✅ CRÍTICO: Só processar DI se tiver número válido (não vazio, não None)
            if numero_di_final and str(numero_di_final).strip() and str(numero_di_final).strip() not in ['', 'None', 'null', 'NULL', 'N/A', 'n/a']:
                logger.info(f"✅ [DI] Processando DI {numero_di_final} para {processo_referencia}")
                tem_documentos = True
                resposta += "**📄 Declaração de Importação:**\n"
                resposta += f"  - DI {numero_di_final}\n"
                
                # ✅ CRÍTICO: Sempre enriquecer dados da DI do SQL Server se faltarem informações essenciais
                # Usar di_data_completo se disponível, senão tentar dados_completos
                di_data_para_extrair = di_data_completo if di_data_completo else (processo_dto.dados_completos.get('di', {}) if processo_dto.dados_completos else {})
                
                # ✅ REGRA: Se faltarem dados essenciais (situação, valores, importador, pagamentos), buscar do SQL Server
                precisa_enriquecer_di = False
                if di_data_para_extrair:
                    tem_situacao = bool(di_data_para_extrair.get('situacao') or di_data_para_extrair.get('situacao_di'))
                    tem_valores = bool(
                        di_data_para_extrair.get('valor_mercadoria_descarga_real') or 
                        di_data_para_extrair.get('real_VLMD') or
                        di_data_para_extrair.get('valor_mercadoria_embarque_real') or
                        di_data_para_extrair.get('real_VLME')
                    )
                    tem_importador = bool(di_data_para_extrair.get('nome_importador'))
                    tem_pagamentos = bool(di_data_para_extrair.get('pagamentos'))
                    
                    if not tem_situacao or not tem_valores or not tem_importador or not tem_pagamentos:
                        precisa_enriquecer_di = True
                        logger.info(f"🔍 [DI] Dados incompletos detectados para DI {numero_di_final} (situacao={tem_situacao}, valores={tem_valores}, importador={tem_importador}, pagamentos={tem_pagamentos}). Buscando dados completos do SQL Server...")
                else:
                    precisa_enriquecer_di = True
                    logger.info(f"🔍 [DI] di_data_para_extrair vazio para DI {numero_di_final}. Buscando dados completos do SQL Server...")
                
                # ✅ Buscar dados completos do SQL Server ANTES de escrever situação
                # ✅ CORREÇÃO: Só buscar do SQL Server se estiver disponível (evita timeout)
                situacao_di = processo_dto.situacao_di
                if precisa_enriquecer_di and numero_di_final:
                    # Verificar se SQL Server está disponível antes de tentar buscar
                    sql_server_disponivel = False
                    try:
                        from utils.sql_server_adapter import get_sql_adapter
                        sql_adapter = get_sql_adapter()
                        if sql_adapter:
                            result = sql_adapter.execute_query("SELECT 1 AS test", notificar_erro=False)
                            sql_server_disponivel = result.get('success', False) if result else False
                    except Exception as e:
                        logger.debug(f"⚠️ SQL Server não disponível: {e}")
                        sql_server_disponivel = False
                    
                    if sql_server_disponivel:
                        try:
                            from services.sql_server_processo_schema import _buscar_di_completo
                            if sql_adapter:
                                # ✅ CRÍTICO: Buscar id_importacao do processo para passar para _buscar_di_completo (necessário para buscar CE relacionado)
                                id_importacao_para_ce = None
                                if processo_dto.id_importacao:
                                    id_importacao_para_ce = processo_dto.id_importacao
                                elif processo_dto.dados_completos:
                                    id_importacao_para_ce = processo_dto.dados_completos.get('id_importacao')
                                
                                di_sql_completo = _buscar_di_completo(sql_adapter, numero_di_final, id_importacao_para_ce)
                                if di_sql_completo and isinstance(di_sql_completo, dict):
                                    # ✅ Mesclar dados: SQL Server tem prioridade (mais completo)
                                    if not di_data_para_extrair:
                                        di_data_para_extrair = {}
                                    # Mesclar mantendo dados existentes se SQL Server não tiver
                                    for key, value in di_sql_completo.items():
                                        if value or key == 'pagamentos' or key == 'ce_relacionado' or key == 'numero_ce':  # Incluir pagamentos, ce_relacionado e numero_ce mesmo se vazio
                                            di_data_para_extrair[key] = value
                                    
                                    # ✅ CRÍTICO: Garantir que ce_relacionado e numero_ce estão presentes
                                    if di_sql_completo.get('ce_relacionado'):
                                        di_data_para_extrair['ce_relacionado'] = di_sql_completo.get('ce_relacionado')
                                        logger.info(f"✅ [DI] ce_relacionado adicionado ao di_data_para_extrair: {di_sql_completo.get('ce_relacionado').get('numero') if isinstance(di_sql_completo.get('ce_relacionado'), dict) else 'N/A'}")
                                    if di_sql_completo.get('numero_ce'):
                                        di_data_para_extrair['numero_ce'] = di_sql_completo.get('numero_ce')
                                        logger.info(f"✅ [DI] numero_ce adicionado ao di_data_para_extrair: {di_sql_completo.get('numero_ce')}")
                                    
                                    # ✅ CRÍTICO: Atualizar situação se foi encontrada no SQL Server
                                    situacao_di_enriquecida = di_sql_completo.get('situacao') or di_sql_completo.get('situacao_di')
                                    if situacao_di_enriquecida:
                                        situacao_di = situacao_di_enriquecida
                                        logger.info(f"✅ [DI] Situação encontrada no SQL Server para DI {numero_di_final}: {situacao_di_enriquecida}")
                                    
                                    logger.info(f"✅ [DI] Dados completos enriquecidos do SQL Server para DI {numero_di_final}")
                        except Exception as e:
                            logger.error(f'❌ [DI] Erro ao enriquecer dados da DI {numero_di_final} do SQL Server: {e}', exc_info=True)
                
                # ✅ Fallback: tentar extrair da estrutura de dados completos, se ainda não tiver situação
                if not situacao_di:
                    if di_data_completo:
                        situacao_di = di_data_completo.get('situacao') or di_data_completo.get('situacao_di')
                    elif processo_dto.dados_completos:
                        try:
                            di_data = processo_dto.dados_completos.get('di') or {}
                            situacao_di = di_data.get('situacao') or di_data.get('situacao_di')
                        except Exception:
                            situacao_di = None
                    # ✅ Tentar também de di_data_para_extrair (já enriquecido)
                    if not situacao_di and di_data_para_extrair:
                        situacao_di = di_data_para_extrair.get('situacao') or di_data_para_extrair.get('situacao_di')
                
                # ✅ Agora escrever situação (já enriquecida se necessário)
                if situacao_di:
                    resposta += f"    - Situação: {situacao_di}\n"
                else:
                    resposta += "    - Situação: não informada\n"
                
                # ✅ Extrair canal e data de desembaraco dos dados_completos (SQL Server ou Kanban)
                canal_di = None
                data_desembaraco_di = None
                
                if di_data_para_extrair:
                    canal_di = di_data_para_extrair.get('canal')
                    data_desembaraco_raw = di_data_para_extrair.get('data_desembaraco')
                    if data_desembaraco_raw:
                        try:
                            from datetime import datetime
                            if isinstance(data_desembaraco_raw, datetime):
                                data_desembaraco_di = data_desembaraco_raw
                            elif isinstance(data_desembaraco_raw, str):
                                # Tentar parsear várias formatos
                                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                                    try:
                                        data_desembaraco_di = datetime.strptime(data_desembaraco_raw.split('.')[0], fmt)
                                        break
                                    except:
                                        continue
                        except:
                            pass
                    
                    # ✅ CRÍTICO: Exibir TODAS as informações da DI do SQL Server (valores, impostos, etc.)
                    if di_data_para_extrair.get('situacao_entrega'):
                        resposta += f"    - Situação Entrega: {di_data_para_extrair.get('situacao_entrega')}\n"
                    
                    # ✅ Valores de mercadoria (do SQL Server)
                    valor_merc_descarga_real = di_data_para_extrair.get('valor_mercadoria_descarga_real') or di_data_para_extrair.get('real_VLMD')
                    valor_merc_embarque_real = di_data_para_extrair.get('valor_mercadoria_embarque_real') or di_data_para_extrair.get('real_VLME')
                    valor_merc_descarga_dolar = di_data_para_extrair.get('valor_mercadoria_descarga_dolar') or di_data_para_extrair.get('dollar_VLMLD')
                    valor_merc_embarque_dolar = di_data_para_extrair.get('valor_mercadoria_embarque_dolar') or di_data_para_extrair.get('dollar_VLME')
                    
                    if valor_merc_descarga_real:
                        resposta += f"    - 💰 Valor Mercadoria Descarga (BRL): R$ {float(valor_merc_descarga_real):,.2f}\n"
                    if valor_merc_embarque_real:
                        resposta += f"    - 💰 Valor Mercadoria Embarque (BRL): R$ {float(valor_merc_embarque_real):,.2f}\n"
                    if valor_merc_descarga_dolar:
                        resposta += f"    - 💰 Valor Mercadoria Descarga (USD): ${float(valor_merc_descarga_dolar):,.2f}\n"
                    if valor_merc_embarque_dolar:
                        resposta += f"    - 💰 Valor Mercadoria Embarque (USD): ${float(valor_merc_embarque_dolar):,.2f}\n"
                    
                    # ✅ Nome do importador (do SQL Server)
                    if di_data_para_extrair.get('nome_importador'):
                        resposta += f"    - 👤 Importador: {di_data_para_extrair.get('nome_importador')}\n"
                
                # Se não encontrou nos dados_completos, tentar do Kanban JSON (canal está no JSON raiz)
                if not canal_di and processo_dto.dados_completos:
                    canal_di = processo_dto.dados_completos.get('canal') or processo_dto.dados_completos.get('canalSelecaoParametrizada')
                
                if canal_di:
                    resposta += f"    - Canal: {canal_di}\n"
                
                if data_desembaraco_di:
                    resposta += f"    - Desembaraço: {data_desembaraco_di.strftime('%d/%m/%Y')}\n"
                elif processo_dto.data_desembaraco:
                    resposta += f"    - Desembaraço: {processo_dto.data_desembaraco.strftime('%d/%m/%Y')}\n"
                
                # ✅ NOVO: Exibir impostos pagos da DI (similar à DUIMP)
                # ✅ REGRA: Pagamentos já devem estar em di_data_para_extrair após enriquecimento acima
                pagamentos_di = None
                
                # Prioridade 1: Buscar de di_data_para_extrair (já enriquecido do SQL Server se necessário)
                if di_data_para_extrair and isinstance(di_data_para_extrair, dict):
                    pagamentos_di = di_data_para_extrair.get('pagamentos')
                    if pagamentos_di:
                        logger.info(f"✅ [DI] {len(pagamentos_di)} pagamento(s) encontrado(s) em di_data_para_extrair para DI {numero_di_final}")
                    else:
                        logger.debug(f"⚠️ [DI] di_data_para_extrair não tem pagamentos. Chaves disponíveis: {list(di_data_para_extrair.keys())}")
                
                # Prioridade 2: Buscar de di_data_completo (se diferente de di_data_para_extrair)
                if not pagamentos_di and di_data_completo and isinstance(di_data_completo, dict):
                    pagamentos_di = di_data_completo.get('pagamentos')
                    if pagamentos_di:
                        logger.info(f"✅ [DI] {len(pagamentos_di)} pagamento(s) encontrado(s) em di_data_completo para DI {numero_di_final}")
                
                # Prioridade 3: Buscar diretamente do SQL Server (fallback final - só se não foi enriquecido acima)
                # ✅ REGRA: Se precisa_enriquecer_di foi True, já foi enriquecido acima e pagamentos devem estar lá
                # Só buscar novamente se não foi enriquecido E ainda não tem pagamentos
                if not pagamentos_di and numero_di_final:
                    # Se foi enriquecido acima mas ainda não tem pagamentos, pode ser que não existam pagamentos
                    # Mas vamos tentar uma última vez para garantir
                    if precisa_enriquecer_di:
                        logger.debug(f"⚠️ [DI] Dados foram enriquecidos acima mas sem pagamentos. Pode ser que não existam pagamentos para DI {numero_di_final}")
                    else:
                        logger.info(f"🔍 [DI] Buscando pagamentos diretamente do SQL Server para DI {numero_di_final} (fallback final)...")
                        try:
                            from utils.sql_server_adapter import get_sql_adapter
                            from services.sql_server_processo_schema import _buscar_di_completo
                            sql_adapter = get_sql_adapter()
                            if sql_adapter:
                                # ✅ CRÍTICO: Buscar id_importacao do processo para passar para _buscar_di_completo
                                id_importacao_para_ce = None
                                if processo_dto.id_importacao:
                                    id_importacao_para_ce = processo_dto.id_importacao
                                elif processo_dto.dados_completos:
                                    id_importacao_para_ce = processo_dto.dados_completos.get('id_importacao')
                                
                                di_sql_temp = _buscar_di_completo(sql_adapter, numero_di_final, id_importacao_para_ce)
                                if di_sql_temp and isinstance(di_sql_temp, dict):
                                    pagamentos_di = di_sql_temp.get('pagamentos')
                                    if pagamentos_di:
                                        logger.info(f"✅ [DI] {len(pagamentos_di)} pagamento(s) encontrado(s) no SQL Server para DI {numero_di_final}")
                                    else:
                                        logger.warning(f"⚠️ [DI] _buscar_di_completo retornou dados mas sem pagamentos. Chaves: {list(di_sql_temp.keys())}")
                                    
                                    # ✅ CRÍTICO: Adicionar ce_relacionado e numero_ce ao di_data_para_extrair se encontrado
                                    if di_sql_temp.get('ce_relacionado'):
                                        di_data_para_extrair['ce_relacionado'] = di_sql_temp.get('ce_relacionado')
                                        logger.info(f"✅ [DI] ce_relacionado adicionado ao di_data_para_extrair (fallback): {di_sql_temp.get('ce_relacionado').get('numero') if isinstance(di_sql_temp.get('ce_relacionado'), dict) else 'N/A'}")
                                    if di_sql_temp.get('numero_ce'):
                                        di_data_para_extrair['numero_ce'] = di_sql_temp.get('numero_ce')
                                        logger.info(f"✅ [DI] numero_ce adicionado ao di_data_para_extrair (fallback): {di_sql_temp.get('numero_ce')}")
                                else:
                                    logger.warning(f"⚠️ [DI] _buscar_di_completo não retornou dados para DI {numero_di_final}")
                            else:
                                logger.warning(f"⚠️ [DI] SQL adapter não disponível para buscar pagamentos")
                        except Exception as e:
                            logger.error(f'❌ [DI] Erro ao buscar pagamentos da DI {numero_di_final}: {e}', exc_info=True)
                
                if pagamentos_di and len(pagamentos_di) > 0:
                    resposta += f"    - **Impostos Pagos:**\n"
                    total_impostos = 0
                    for pag in pagamentos_di:
                        tipo_imposto = pag.get('tipo', 'N/A')
                        valor = pag.get('valor', 0)
                        if valor:
                            total_impostos += float(valor)
                            data_pag = pag.get('data_pagamento', '')
                            resposta += f"      • {tipo_imposto}: R$ {float(valor):,.2f}"
                            if data_pag:
                                # Formatar data se for string
                                try:
                                    from datetime import datetime
                                    if isinstance(data_pag, str):
                                        # Tentar parsear várias formatos
                                        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                                            try:
                                                dt = datetime.strptime(data_pag.split('.')[0], fmt)
                                                resposta += f" (pago em {dt.strftime('%d/%m/%Y')})"
                                                break
                                            except:
                                                continue
                                    else:
                                        resposta += f" (pago em {data_pag})"
                                except:
                                    resposta += f" (pago em {data_pag})"
                            resposta += "\n"
                    if total_impostos > 0:
                        resposta += f"      **Total Impostos: R$ {total_impostos:,.2f}**\n"
                
                # ✅ NOVO: CE relacionado à DI (conforme MAPEAMENTO_SQL_SERVER.md)
                # Buscar CE relacionado de múltiplas fontes
                numero_ce_di = (
                    di_data_para_extrair.get('numero_ce') or
                    di_data_completo.get('numero_ce') if di_data_completo else None or
                    (di_data_para_extrair.get('ce_relacionado', {}).get('numero') if isinstance(di_data_para_extrair.get('ce_relacionado'), dict) else None) or
                    (di_data_completo.get('ce_relacionado', {}).get('numero') if di_data_completo and isinstance(di_data_completo.get('ce_relacionado'), dict) else None)
                )
                ce_relacionado = (
                    di_data_para_extrair.get('ce_relacionado') or
                    (di_data_completo.get('ce_relacionado') if di_data_completo else None)
                )
                
                # ✅ DEBUG: Log para verificar se encontramos o CE relacionado
                if numero_ce_di:
                    logger.info(f"✅ [DI] CE relacionado encontrado para DI {numero_di_final}: {numero_ce_di}")
                else:
                    logger.debug(f"⚠️ [DI] CE relacionado NÃO encontrado para DI {numero_di_final}. di_data_para_extrair tem numero_ce: {bool(di_data_para_extrair.get('numero_ce')) if di_data_para_extrair else False}, di_data_completo tem numero_ce: {bool(di_data_completo.get('numero_ce')) if di_data_completo else False}, ce_relacionado em di_data_para_extrair: {bool(di_data_para_extrair.get('ce_relacionado')) if di_data_para_extrair else False}, ce_relacionado em di_data_completo: {bool(di_data_completo.get('ce_relacionado')) if di_data_completo else False}")
                
                if numero_ce_di:
                    resposta += f"    - 📦 CE Relacionado: {numero_ce_di}\n"
                    # ✅ NOVO: Se temos dados completos do CE relacionado, exibir informações adicionais
                    if ce_relacionado and isinstance(ce_relacionado, dict):
                        situacao_ce = ce_relacionado.get('situacao')
                        porto_origem = ce_relacionado.get('porto_origem')
                        porto_destino = ce_relacionado.get('porto_destino')
                        valor_frete_ce = ce_relacionado.get('valor_frete_total')
                        if situacao_ce:
                            resposta += f"      - Situação CE: {situacao_ce}\n"
                        if porto_origem:
                            resposta += f"      - Porto Origem: {porto_origem}\n"
                        if porto_destino:
                            resposta += f"      - Porto Destino: {porto_destino}\n"
                        if valor_frete_ce:
                            try:
                                valor_frete_float = float(str(valor_frete_ce).replace(',', '.'))
                                resposta += f"      - 💰 Frete CE: R$ {valor_frete_float:,.2f}\n"
                            except:
                                resposta += f"      - 💰 Frete CE: {valor_frete_ce}\n"
                
                resposta += "\n"
            
            # DUIMP - COM TODOS OS DADOS (SITUAÇÃO, CANAL, IMPOSTOS)
            # ✅ CRÍTICO: Tentar buscar DUIMP mesmo se numero_duimp estiver vazio no DTO
            numero_duimp = processo_dto.numero_duimp
            if not numero_duimp and processo_dto.dados_completos:
                # Tentar extrair do dados_completos
                duimp_data = processo_dto.dados_completos.get('duimp')
                if isinstance(duimp_data, dict):
                    numero_duimp = duimp_data.get('numero') or duimp_data.get('numero_duimp')
                elif isinstance(duimp_data, list) and len(duimp_data) > 0:
                    # Se for lista, pegar o primeiro item
                    primeiro_duimp = duimp_data[0]
                    if isinstance(primeiro_duimp, dict):
                        numero_duimp = primeiro_duimp.get('numero') or primeiro_duimp.get('numero_duimp')
            
            # Se ainda não encontrou, tentar buscar no SQL Server diretamente
            if not numero_duimp:
                try:
                    from services.sql_server_processo_schema import buscar_processo_consolidado_sql_server
                    processo_consolidado_temp = buscar_processo_consolidado_sql_server(processo_referencia)
                    if processo_consolidado_temp:
                        duimp_temp = processo_consolidado_temp.get('duimp')
                        if isinstance(duimp_temp, dict):
                            numero_duimp = duimp_temp.get('numero') or duimp_temp.get('numero_duimp')
                        elif isinstance(duimp_temp, list) and len(duimp_temp) > 0:
                            # Se for lista, pegar o primeiro item
                            primeiro_duimp = duimp_temp[0]
                            if isinstance(primeiro_duimp, dict):
                                numero_duimp = primeiro_duimp.get('numero') or primeiro_duimp.get('numero_duimp')
                except Exception as e:
                    logger.debug(f'Erro ao buscar DUIMP no SQL Server para {processo_referencia}: {e}')
            
            if numero_duimp:
                logger.info(f"🔍 [DUIMP] Enriquecendo DUIMP {numero_duimp} para processo {processo_referencia}")
                tem_documentos = True
                resposta += "**📝 DUIMP:**\n"
                
                # ✅ NOVO: Enriquecer DUIMP com situação, canal e impostos
                situacao_duimp = None
                canal_duimp = None
                dados_completos_duimp = {}
                historico_situacoes_duimp = []
                duimp_sql = None  # ✅ Variável para guardar dados do SQL Server
                duimp_data = None  # ✅ Variável para guardar dados do Kanban/JSON
                
                # 1. Tentar buscar do JSON do Kanban (dados_completos) - pode ter dados que não estão no SQL Server
                if processo_dto.dados_completos:
                    # Tentar extrair do JSON do Kanban diretamente
                    dados_kanban = processo_dto.dados_completos
                    
                    # Verificar se tem DUIMP no JSON do Kanban
                    duimp_kanban = dados_kanban.get('duimp') or dados_kanban.get('duimp_data') or dados_kanban.get('dados_duimp')
                    if isinstance(duimp_kanban, dict):
                        duimp_data = duimp_kanban  # ✅ Guardar dados do Kanban
                        if not situacao_duimp:
                            situacao_duimp = duimp_kanban.get('situacao') or duimp_kanban.get('situacaoDuimp') or duimp_kanban.get('ultima_situacao')
                        if not canal_duimp:
                            canal_duimp = duimp_kanban.get('canal') or duimp_kanban.get('canalConsolidado') or duimp_kanban.get('canal_consolidado')
                        logger.info(f"✅ [DUIMP] Situação/canal encontrados no JSON Kanban: situacao={situacao_duimp}, canal={canal_duimp}")
                    elif isinstance(duimp_kanban, list) and len(duimp_kanban) > 0:
                        primeiro_duimp = duimp_kanban[0]
                        if isinstance(primeiro_duimp, dict):
                            duimp_data = primeiro_duimp  # ✅ Guardar dados do Kanban (primeiro item da lista)
                            if not situacao_duimp:
                                situacao_duimp = primeiro_duimp.get('situacao') or primeiro_duimp.get('situacaoDuimp') or primeiro_duimp.get('ultima_situacao')
                            if not canal_duimp:
                                canal_duimp = primeiro_duimp.get('canal') or primeiro_duimp.get('canalConsolidado') or primeiro_duimp.get('canal_consolidado')
                            logger.info(f"✅ [DUIMP] Situação/canal encontrados no JSON Kanban (lista): situacao={situacao_duimp}, canal={canal_duimp}")
                    
                    # Também tentar buscar de campos diretos no JSON raiz (caso a DUIMP esteja em estrutura diferente)
                    if not situacao_duimp:
                        # Tentar vários caminhos possíveis no JSON
                        situacao_duimp = (
                            dados_kanban.get('situacao_duimp') or
                            dados_kanban.get('situacaoDuimp') or
                            dados_kanban.get('duimp_situacao') or
                            dados_kanban.get('ultima_situacao_duimp')
                        )
                    if not canal_duimp:
                        canal_duimp = (
                            dados_kanban.get('canal_duimp') or
                            dados_kanban.get('canalDuimp') or
                            dados_kanban.get('canal_consolidado') or
                            dados_kanban.get('canalConsolidado')
                        )
                    
                    # ✅ CRÍTICO: Buscar em estruturas aninhadas do JSON do Kanban
                    # O JSON do Kanban pode ter a DUIMP em diferentes lugares
                    def buscar_em_json_recursivo(obj, chaves_busca):
                        """Busca recursiva em estruturas JSON aninhadas"""
                        if not isinstance(obj, dict):
                            return None
                        for chave in chaves_busca:
                            valor = obj.get(chave)
                            if valor:
                                return valor
                        # Buscar recursivamente em valores que são dicts
                        for valor in obj.values():
                            if isinstance(valor, dict):
                                resultado = buscar_em_json_recursivo(valor, chaves_busca)
                                if resultado:
                                    return resultado
                            elif isinstance(valor, list):
                                for item in valor:
                                    if isinstance(item, dict):
                                        resultado = buscar_em_json_recursivo(item, chaves_busca)
                                        if resultado:
                                            return resultado
                        return None
                    
                    # Buscar situação em estruturas aninhadas
                    if not situacao_duimp:
                        situacao_encontrada = buscar_em_json_recursivo(dados_kanban, [
                            'situacaoDuimp', 'situacao_duimp', 'ultima_situacao', 
                            'situacao', 'status', 'estado'
                        ])
                        if situacao_encontrada and isinstance(situacao_encontrada, str):
                            situacao_duimp = situacao_encontrada
                            logger.info(f"✅ [DUIMP] Situação encontrada em JSON aninhado: {situacao_duimp}")
                    
                    # Buscar canal em estruturas aninhadas
                    if not canal_duimp:
                        canal_encontrado = buscar_em_json_recursivo(dados_kanban, [
                            'canalConsolidado', 'canal_consolidado', 'canal',
                            'canalSelecaoParametrizada', 'canal_selecao'
                        ])
                        if canal_encontrado and isinstance(canal_encontrado, str):
                            canal_duimp = canal_encontrado
                            logger.info(f"✅ [DUIMP] Canal encontrado em JSON aninhado: {canal_duimp}")
                
                # 2. SEMPRE tentar buscar payload completo do SQLite para ter impostos/valores
                # (mesmo se já tem situação/canal, precisamos dos impostos)
                if numero_duimp:
                    logger.info(f"🔍 [DUIMP] Buscando payload completo no SQLite para {numero_duimp}...")
                    try:
                        import sqlite3
                        from db_manager import get_db_connection
                        conn_duimp = get_db_connection()
                        conn_duimp.row_factory = sqlite3.Row
                        cursor_duimp = conn_duimp.cursor()
                        # ✅ CRÍTICO: Buscar também em validação se não encontrar em produção
                        cursor_duimp.execute('''
                            SELECT payload_completo, versao, ambiente
                            FROM duimps
                            WHERE numero = ? AND ambiente IN ('producao', 'validacao')
                            ORDER BY 
                                CASE WHEN ambiente = 'producao' THEN 1 ELSE 2 END,
                                CAST(versao AS INTEGER) DESC
                            LIMIT 1
                        ''', (numero_duimp,))
                        row_duimp = cursor_duimp.fetchone()
                        conn_duimp.close()
                        
                        if row_duimp and row_duimp['payload_completo']:
                            logger.info(f"✅ [DUIMP] Payload encontrado no SQLite para {numero_duimp} (ambiente: {row_duimp.get('ambiente', 'N/A')})")
                            import json
                            payload_parsed = json.loads(row_duimp['payload_completo']) if isinstance(row_duimp['payload_completo'], str) else row_duimp['payload_completo']
                            if isinstance(payload_parsed, dict):
                                dados_completos_duimp = payload_parsed
                                # Extrair situação e canal do payload (sempre, mesmo se já tem)
                                situacao_obj = payload_parsed.get('situacao', {})
                                if situacao_obj and isinstance(situacao_obj, dict):
                                    situacao_extraida = situacao_obj.get('situacaoDuimp', '')
                                    if situacao_extraida:
                                        situacao_duimp = situacao_extraida
                                        logger.info(f"✅ [DUIMP] Situação extraída do payload: {situacao_duimp}")
                                resultado_risco = payload_parsed.get('resultadoAnaliseRisco', {})
                                if resultado_risco and isinstance(resultado_risco, dict):
                                    canal_extraido = resultado_risco.get('canalConsolidado', '') or resultado_risco.get('canal', '')
                                    if canal_extraido:
                                        canal_duimp = canal_extraido
                                        logger.info(f"✅ [DUIMP] Canal extraído do payload (resultadoAnaliseRisco.canalConsolidado): {canal_duimp}")
                                    else:
                                        logger.warning(f"⚠️ [DUIMP] Canal não encontrado em resultadoAnaliseRisco. Chaves: {list(resultado_risco.keys())}")
                                else:
                                    logger.warning(f"⚠️ [DUIMP] resultadoAnaliseRisco não é dict ou não existe: {type(resultado_risco) if resultado_risco else 'None'}")
                                
                                # ✅ FALLBACK: Tentar buscar canal em outros lugares do JSON se não encontrou
                                if not canal_duimp:
                                    canal_fallback = (
                                        payload_parsed.get('canalConsolidado') or
                                        payload_parsed.get('canal_consolidado') or
                                        payload_parsed.get('canal') or
                                        payload_parsed.get('canalSelecaoParametrizada')
                                    )
                                    if canal_fallback:
                                        canal_duimp = canal_fallback
                                        logger.info(f"✅ [DUIMP] Canal encontrado em fallback do JSON: {canal_duimp}")
                        else:
                            logger.warning(f"⚠️ [DUIMP] Payload não encontrado no SQLite para {numero_duimp}")
                    except Exception as e:
                        logger.error(f'❌ [DUIMP] Erro ao buscar payload completo da DUIMP {numero_duimp}: {e}', exc_info=True)
                
                # 3. Se ainda não encontrou, tentar SQL Server diretamente usando _buscar_duimp_completo
                if (not situacao_duimp or not canal_duimp or not dados_completos_duimp) and numero_duimp:
                    logger.info(f"🔍 [DUIMP] Buscando no SQL Server diretamente usando _buscar_duimp_completo para {numero_duimp}...")
                    try:
                        from utils.sql_server_adapter import get_sql_adapter
                        from services.sql_server_processo_schema import _buscar_duimp_completo
                        sql_adapter = get_sql_adapter()
                        # ✅ CRÍTICO: Buscar id_importacao do processo para passar para _buscar_duimp_completo (necessário para buscar CE relacionado)
                        id_importacao_para_ce_duimp = None
                        if processo_dto.id_importacao:
                            id_importacao_para_ce_duimp = processo_dto.id_importacao
                        elif processo_dto.dados_completos:
                            id_importacao_para_ce_duimp = processo_dto.dados_completos.get('id_importacao')
                        duimp_sql_temp = _buscar_duimp_completo(sql_adapter, numero_duimp, processo_referencia, id_importacao_para_ce_duimp)
                        if duimp_sql_temp and isinstance(duimp_sql_temp, dict):
                            duimp_sql = duimp_sql_temp  # ✅ Guardar para uso posterior
                            if not situacao_duimp:
                                situacao_duimp = duimp_sql.get('situacao', '')
                                logger.info(f"✅ [DUIMP] Situação encontrada no SQL Server: {situacao_duimp}")
                            if not canal_duimp:
                                canal_duimp = duimp_sql.get('canal', '')
                                logger.info(f"✅ [DUIMP] Canal encontrado no SQL Server: {canal_duimp}")
                            # ✅ CRÍTICO: Se o SQL Server retornou payload_completo, usar ele para impostos
                            if not dados_completos_duimp and duimp_sql.get('payload_completo'):
                                dados_completos_duimp = duimp_sql.get('payload_completo')
                                logger.info(f"✅ [DUIMP] Payload completo encontrado no SQL Server para impostos")
                            
                            # ✅ NOVO: Guardar histórico de situações se disponível
                            if duimp_sql.get('historico_situacoes'):
                                historico_situacoes_duimp = duimp_sql.get('historico_situacoes', [])
                                logger.info(f"✅ [DUIMP] Histórico de situações encontrado: {len(historico_situacoes_duimp)} registro(s)")
                            
                            # ✅ NOVO: Guardar pagamentos do SQL Server se disponível
                            if duimp_sql.get('pagamentos'):
                                logger.info(f"✅ [DUIMP] {len(duimp_sql.get('pagamentos', []))} pagamento(s) encontrado(s) no SQL Server")
                            
                            # ✅ CRÍTICO: Mesclar dados do SQL Server (incluindo CE relacionado) com duimp_data
                            if not isinstance(duimp_data, dict):
                                duimp_data = {}
                            # Mesclar dados do SQL Server (prioridade para SQL Server)
                            if duimp_sql.get('numero_ce'):
                                duimp_data['numero_ce'] = duimp_sql.get('numero_ce')
                            if duimp_sql.get('ce_relacionado'):
                                duimp_data['ce_relacionado'] = duimp_sql.get('ce_relacionado')
                                logger.info(f"✅ [DUIMP] CE relacionado mesclado em duimp_data: {duimp_data.get('numero_ce')}")
                        else:
                            logger.warning(f"⚠️ [DUIMP] DUIMP não encontrada no SQL Server para {numero_duimp}")
                    except Exception as e:
                        logger.error(f'❌ [DUIMP] Erro ao buscar DUIMP {numero_duimp} via SQL Server: {e}', exc_info=True)
                
                # Formatar resposta da DUIMP (sempre mostrar número, mesmo se não tem situação/canal)
                resposta += f"  - DUIMP {numero_duimp}"
                if situacao_duimp:
                    resposta += f"\n    - Situação: {situacao_duimp}"
                else:
                    resposta += f"\n    - Situação: N/A"
                if canal_duimp:
                    resposta += f"\n    - Canal: {canal_duimp}"
                else:
                    resposta += f"\n    - Canal: N/A"
                
                # ✅ NOVO: Mostrar histórico de situações se disponível
                if historico_situacoes_duimp and len(historico_situacoes_duimp) > 1:
                    resposta += f"\n    - **Histórico de Situações:**"
                    for hist in historico_situacoes_duimp[:5]:  # Mostrar até 5 mais recentes
                        situacao_hist = hist.get('situacao', 'N/A')
                        data_hist = hist.get('data', '')
                        if situacao_hist and situacao_hist != 'N/A':
                            resposta += f"\n      • {situacao_hist}"
                            if data_hist:
                                try:
                                    from datetime import datetime
                                    if isinstance(data_hist, str):
                                        # Tentar parsear data
                                        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                                            try:
                                                dt = datetime.strptime(data_hist.split('.')[0], fmt)
                                                resposta += f" ({dt.strftime('%d/%m/%Y %H:%M')})"
                                                break
                                            except:
                                                continue
                                    else:
                                        resposta += f" ({data_hist})"
                                except:
                                    resposta += f" ({data_hist})"
                
                # ✅ EXTRAIR E MOSTRAR IMPOSTOS E VALORES
                # Prioridade 1: Pagamentos do SQL Server (duimp_pagamentos)
                # Prioridade 2: JSON completo (tributos.tributosCalculados)
                pagamentos_duimp = None
                if duimp_sql and isinstance(duimp_sql, dict) and duimp_sql.get('pagamentos'):
                    pagamentos_duimp = duimp_sql.get('pagamentos')
                
                if pagamentos_duimp and len(pagamentos_duimp) > 0:
                    # Usar pagamentos do SQL Server
                    resposta += f"\n    - **Impostos Pagos:**"
                    total_impostos = 0
                    for pag in pagamentos_duimp:
                        tipo_tributo = pag.get('tipo', 'N/A')
                        valor = pag.get('valor', 0)
                        if valor:
                            total_impostos += float(valor)
                            data_pag = pag.get('data_pagamento', '')
                            resposta += f"\n      • {tipo_tributo}: R$ {float(valor):,.2f}"
                            if data_pag:
                                resposta += f" (pago em {data_pag})"
                    if total_impostos > 0:
                        resposta += f"\n      **Total Impostos: R$ {total_impostos:,.2f}**"
                elif duimp_sql and isinstance(duimp_sql, dict) and duimp_sql.get('tributos_calculados'):
                    # ✅ Fallback: tributos calculados do SQL Server (duimp_tributos_calculados)
                    try:
                        tribs = duimp_sql.get('tributos_calculados') or []
                        if isinstance(tribs, list) and tribs:
                            resposta += f"\n    - **Impostos (calculados):**"
                            total_calc = 0.0
                            for t in tribs:
                                if not isinstance(t, dict):
                                    continue
                                tipo = t.get('tipo') or 'N/A'
                                vb = t.get('valoresBRL', {}) or {}
                                # Priorizar 'devido', depois 'aRecolher', depois 'recolhido', depois 'calculado'
                                val = vb.get('devido')
                                if val is None:
                                    val = vb.get('aRecolher')
                                if val is None:
                                    val = vb.get('recolhido')
                                if val is None:
                                    val = vb.get('calculado')
                                try:
                                    val_f = float(val) if val is not None and str(val).strip() != '' else 0.0
                                except Exception:
                                    val_f = 0.0
                                if val_f:
                                    total_calc += val_f
                                    resposta += f"\n      • {tipo}: R$ {val_f:,.2f}"
                            if total_calc:
                                resposta += f"\n      **Total Impostos: R$ {total_calc:,.2f}**"
                    except Exception:
                        pass
                elif dados_completos_duimp and isinstance(dados_completos_duimp, dict):
                    # Fallback: Valores Calculados / Tributos do JSON
                    vc = dados_completos_duimp.get('tributos') or dados_completos_duimp.get('valoresCalculados') or {}
                    if vc:
                        mercadoria_vc = vc.get('mercadoria', {})
                        if mercadoria_vc:
                            valor_fob_usd = mercadoria_vc.get('valorTotalLocalEmbarqueUSD', 0) or 0
                            valor_fob_brl = mercadoria_vc.get('valorTotalLocalEmbarqueBRL', 0) or 0
                            if valor_fob_usd or valor_fob_brl:
                                resposta += f"\n    - Valor FOB (USD): {valor_fob_usd:,.2f}" if valor_fob_usd else ""
                                resposta += f"\n    - Valor FOB (BRL): R$ {valor_fob_brl:,.2f}" if valor_fob_brl else ""
                        
                        # Impostos/Tributos Calculados
                        tribs = vc.get('tributosCalculados', [])
                        if tribs:
                            resposta += f"\n    - **Impostos:**"
                            total_impostos = 0
                            for t in tribs:
                                valores_brl = t.get('valoresBRL', {}) or {}
                                valor_recolher = valores_brl.get('aRecolher', 0) or 0
                                tipo_tributo = t.get('tipo', 'N/A')
                                if valor_recolher:
                                    total_impostos += float(valor_recolher)
                                    resposta += f"\n      • {tipo_tributo}: R$ {float(valor_recolher):,.2f}"
                            if total_impostos > 0:
                                resposta += f"\n      **Total Impostos: R$ {total_impostos:,.2f}**"
                
                # ✅ NOVO: CE relacionado à DUIMP (conforme MAPEAMENTO_SQL_SERVER.md)
                # Buscar CE relacionado de múltiplas fontes
                numero_ce_duimp = (
                    duimp_sql.get('numero_ce') if duimp_sql and isinstance(duimp_sql, dict) else None or
                    (duimp_data.get('numero_ce') if isinstance(duimp_data, dict) else None) or
                    (duimp_sql.get('ce_relacionado', {}).get('numero') if duimp_sql and isinstance(duimp_sql.get('ce_relacionado'), dict) else None) or
                    (duimp_data.get('ce_relacionado', {}).get('numero') if isinstance(duimp_data, dict) and isinstance(duimp_data.get('ce_relacionado'), dict) else None)
                )
                ce_relacionado_duimp = (
                    (duimp_sql.get('ce_relacionado') if duimp_sql and isinstance(duimp_sql, dict) else None) or
                    (duimp_data.get('ce_relacionado') if isinstance(duimp_data, dict) else None)
                )
                
                # ✅ DEBUG: Log para verificar se encontramos o CE relacionado
                if numero_ce_duimp:
                    logger.info(f"✅ [DUIMP] CE relacionado encontrado para DUIMP {numero_duimp}: {numero_ce_duimp}")
                else:
                    logger.debug(f"⚠️ [DUIMP] CE relacionado NÃO encontrado para DUIMP {numero_duimp}. duimp_sql tem numero_ce: {bool(duimp_sql.get('numero_ce') if duimp_sql and isinstance(duimp_sql, dict) else False)}, duimp_data tem numero_ce: {bool(duimp_data.get('numero_ce') if isinstance(duimp_data, dict) else False)}, ce_relacionado em duimp_sql: {bool(duimp_sql.get('ce_relacionado') if duimp_sql and isinstance(duimp_sql, dict) else False)}, ce_relacionado em duimp_data: {bool(duimp_data.get('ce_relacionado') if isinstance(duimp_data, dict) else False)}")
                
                if numero_ce_duimp:
                    resposta += f"    - 📦 CE Relacionado: {numero_ce_duimp}\n"
                    # ✅ NOVO: Se temos dados completos do CE relacionado, exibir informações adicionais
                    if ce_relacionado_duimp and isinstance(ce_relacionado_duimp, dict):
                        situacao_ce = ce_relacionado_duimp.get('situacao')
                        porto_origem = ce_relacionado_duimp.get('porto_origem')
                        porto_destino = ce_relacionado_duimp.get('porto_destino')
                        valor_frete_ce = ce_relacionado_duimp.get('valor_frete_total')
                        if situacao_ce:
                            resposta += f"      - Situação CE: {situacao_ce}\n"
                        if porto_origem:
                            resposta += f"      - Porto Origem: {porto_origem}\n"
                        if porto_destino:
                            resposta += f"      - Porto Destino: {porto_destino}\n"
                        if valor_frete_ce:
                            try:
                                valor_frete_float = float(str(valor_frete_ce).replace(',', '.'))
                                resposta += f"      - 💰 Frete CE: R$ {valor_frete_float:,.2f}\n"
                            except:
                                resposta += f"      - 💰 Frete CE: {valor_frete_ce}\n"
                
                resposta += "\n\n"
            
            # Transporte
            if processo_dto.bl_house:
                resposta += "**🚚 Transporte:**\n"
                resposta += f"  - BL/House: {processo_dto.bl_house}\n"
                if processo_dto.master_bl:
                    resposta += f"  - Master BL: {processo_dto.master_bl}\n"
                resposta += "\n"
            
            # ✅ NOVO: Informações de ETA/Transporte (sempre exibir quando disponível, mesmo sem documentos)
            tem_info_transporte = False
            if processo_dto.eta_iso:
                if not tem_info_transporte:
                    resposta += "**📅 Previsão de Chegada (ETA):**\n"
                    tem_info_transporte = True
                from datetime import datetime
                try:
                    if isinstance(processo_dto.eta_iso, datetime):
                        eta_str = processo_dto.eta_iso.strftime('%d/%m/%Y')
                    else:
                        eta_str = str(processo_dto.eta_iso)
                    resposta += f"  - ETA: {eta_str}\n"
                except:
                    resposta += f"  - ETA: {processo_dto.eta_iso}\n"
            
            # ✅ NOVO: Se não encontrou ETA no DTO, tentar buscar do JSON diretamente
            if not processo_dto.eta_iso and processo_dto.dados_completos:
                json_data = processo_dto.dados_completos
                
                # Helper para parsear data
                def parse_eta_date(date_str):
                    if not date_str:
                        return None
                    from datetime import datetime
                    if isinstance(date_str, datetime):
                        return date_str
                    if isinstance(date_str, str):
                        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
                            try:
                                date_str_clean = date_str.split('T')[0].split(' ')[0]
                                return datetime.strptime(date_str_clean, "%Y-%m-%d")
                            except:
                                continue
                    return None
                
                # Buscar POD/ETA de múltiplas fontes
                pod_data = (
                    json_data.get('pod') or 
                    json_data.get('POD') or 
                    json_data.get('portOfDischarge') or
                    json_data.get('port_of_discharge') or
                    json_data.get('dataPod') or
                    json_data.get('data_pod') or
                    json_data.get('etaPod') or
                    json_data.get('eta_pod')
                )
                
                eta_encontrado = None
                if pod_data:
                    if isinstance(pod_data, dict):
                        eta_encontrado = (
                            parse_eta_date(pod_data.get('data')) or 
                            parse_eta_date(pod_data.get('eta')) or 
                            parse_eta_date(pod_data.get('dataChegada')) or
                            parse_eta_date(pod_data.get('data_chegada')) or
                            parse_eta_date(pod_data.get('dataPod')) or
                            parse_eta_date(pod_data.get('data_pod'))
                        )
                    elif isinstance(pod_data, str) and '/' in pod_data:
                        try:
                            from datetime import datetime
                            partes = pod_data.strip().split('/')
                            if len(partes) == 3:
                                dia, mes, ano = partes
                                if len(ano) == 2:
                                    ano = '20' + ano
                                data_str = f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
                                eta_encontrado = parse_eta_date(data_str)
                        except:
                            eta_encontrado = parse_eta_date(pod_data)
                    else:
                        eta_encontrado = parse_eta_date(pod_data)
                
                # Se não encontrou POD, tentar shipgov2
                if not eta_encontrado:
                    shipgov2 = json_data.get('shipgov2', {})
                    if isinstance(shipgov2, dict):
                        eta_encontrado = parse_eta_date(shipgov2.get('destino_data_chegada'))
                
                # Se ainda não encontrou, tentar dataPrevisaoChegada
                if not eta_encontrado:
                    eta_encontrado = parse_eta_date(json_data.get('dataPrevisaoChegada')) or parse_eta_date(json_data.get('previsaoChegada'))
                
                if eta_encontrado:
                    if not tem_info_transporte:
                        resposta += "**📅 Previsão de Chegada (ETA):**\n"
                        tem_info_transporte = True
                    try:
                        from datetime import datetime
                        if isinstance(eta_encontrado, datetime):
                            eta_str = eta_encontrado.strftime('%d/%m/%Y')
                        else:
                            eta_str = str(eta_encontrado)
                        resposta += f"  - ETA: {eta_str}\n"
                    except:
                        resposta += f"  - ETA: {eta_encontrado}\n"
            
            if processo_dto.porto_nome or processo_dto.porto_codigo:
                if not tem_info_transporte:
                    resposta += "**📅 Previsão de Chegada (ETA):**\n"
                    tem_info_transporte = True
                if processo_dto.porto_nome:
                    resposta += f"  - Porto: {processo_dto.porto_nome}\n"
                elif processo_dto.porto_codigo:
                    resposta += f"  - Porto: {processo_dto.porto_codigo}\n"
            
            if processo_dto.nome_navio:
                if not tem_info_transporte:
                    resposta += "**📅 Previsão de Chegada (ETA):**\n"
                    tem_info_transporte = True
                resposta += f"  - Navio: {processo_dto.nome_navio}\n"
            
            if tem_info_transporte:
                resposta += "\n"
            
            # Pendencias
            if processo_dto.tem_pendencias:
                resposta += "**⚠️ Pendências:**\n"
                if processo_dto.pendencia_icms:
                    resposta += f"  - ICMS: {processo_dto.pendencia_icms}\n"
                if processo_dto.pendencia_frete:
                    resposta += f"  - Frete: Pendente\n"
                resposta += "\n"
            
            # Datas importantes
            tem_datas = False
            if processo_dto.data_embarque or processo_dto.data_desembaraco or processo_dto.data_entrega:
                resposta += "**📅 Datas Importantes:**\n"
                tem_datas = True
                
                if processo_dto.data_embarque:
                    resposta += f"  - Embarque: {processo_dto.data_embarque.strftime('%d/%m/%Y')}\n"
                if processo_dto.data_desembaraco:
                    resposta += f"  - Desembaraço: {processo_dto.data_desembaraco.strftime('%d/%m/%Y')}\n"
                if processo_dto.data_entrega:
                    resposta += f"  - Entrega: {processo_dto.data_entrega.strftime('%d/%m/%Y')}\n"
                resposta += "\n"
            
            # Se não tem documentos, informar fonte
            if not tem_documentos:
                resposta += f"💡 **Fonte:** {processo_dto.fonte}\n"
                if processo_dto.fonte == 'sql_server':
                    resposta += "⚠️ Processo histórico - alguns dados podem estar incompletos.\n"
            
            # ✅ NOVO (08/01/2026): Incluir despesas conciliadas automaticamente
            try:
                from services.banco_concilacao_service import get_banco_concilacao_service
                
                conciliacao_service = get_banco_concilacao_service()
                despesas_resultado = conciliacao_service.consultar_despesas_processo(
                    processo_referencia=processo_referencia,
                    incluir_pendentes=False,  # Por enquanto, só conciliadas
                    incluir_rastreamento=False
                )
                
                if despesas_resultado.get('sucesso') and despesas_resultado.get('despesas_conciliadas'):
                    # Adicionar apenas seção de despesas conciliadas (resumo)
                    quantidade = despesas_resultado.get('quantidade_conciliadas', 0)
                    if quantidade > 0:
                        resposta += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        resposta += f"💰 **DESPESAS CONCILIADAS:**\n\n"
                        
                        for despesa in despesas_resultado.get('despesas_conciliadas', [])[:5]:  # Máximo 5 para não poluir
                            valor_formatado = f"R$ {despesa.get('valor', 0):,.2f}"
                            tipo_despesa = despesa.get('tipo_despesa', 'N/A')
                            data_pagamento = despesa.get('data_pagamento', '')
                            banco = despesa.get('banco', '')
                            
                            resposta += f"  ✅ **{tipo_despesa}** - {valor_formatado}"
                            if data_pagamento:
                                resposta += f" ({data_pagamento})"
                            if banco:
                                resposta += f" - {banco}"
                            resposta += "\n"
                        
                        total_conciliado = despesas_resultado.get('total_conciliado', 0.0)
                        if quantidade > 5:
                            resposta += f"  ... e mais {quantidade - 5} despesa(s)\n"
                        resposta += f"\n📊 Total: R$ {total_conciliado:,.2f} ({quantidade} despesa(s) conciliada(s))\n"
                        resposta += f"\n💡 Use 'despesas do {processo_referencia}' para ver detalhes completos.\n"
            except Exception as e:
                logger.debug(f'⚠️ Erro ao consultar despesas (não crítico): {e}')
                # Não falhar a consulta do processo se houver erro ao buscar despesas
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': processo_dto.to_dict(),
                'fonte': processo_dto.fonte
            }
            
        except Exception as e:
            logger.error(f'Erro ao formatar resposta do processo DTO: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao formatar resposta: {str(e)}'
            }
    
    def _obter_dashboard_hoje(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retorna dashboard consolidado do dia atual.
        """
        try:
            from db_manager import (
                obter_processos_chegando_hoje,
                obter_processos_prontos_registro,
                obter_pendencias_ativas,
                obter_duimps_em_analise,
                obter_dis_em_analise,  # ✅ NOVO: DIs em análise
                obter_processos_eta_alterado,
                obter_alertas_recentes,
                listar_processos_em_dta  # ✅ NOVO: Processos em DTA
            )
            
            # Extrair filtros
            categoria = arguments.get('categoria')
            modal = arguments.get('modal')
            apenas_pendencias = arguments.get('apenas_pendencias', False)
            
            # Buscar dados
            processos_chegando = obter_processos_chegando_hoje(categoria, modal)
            processos_prontos = obter_processos_prontos_registro(categoria, modal) if not apenas_pendencias else []
            processos_em_dta = listar_processos_em_dta(categoria) if not apenas_pendencias else []  # ✅ NOVO: Processos em DTA
            pendencias = obter_pendencias_ativas(categoria, modal)
            duimps_analise = obter_duimps_em_analise(categoria) if not apenas_pendencias else []  # ✅ CORREÇÃO: Passar categoria
            dis_analise = obter_dis_em_analise(categoria) if not apenas_pendencias else []  # ✅ CORREÇÃO: Passar categoria
            eta_alterado = obter_processos_eta_alterado(categoria) if not apenas_pendencias else []
            alertas = obter_alertas_recentes(limite=10, categoria=categoria) if not apenas_pendencias else []  # ✅ CORREÇÃO: Passar categoria
            
            # ✅ PASSO 6 - FASE 4: Criar JSON estruturado primeiro (fonte da verdade)
            from datetime import datetime
            dados_json = {
                'tipo_relatorio': 'o_que_tem_hoje',  # ← Tipo explícito, não precisa regex!
                'data': datetime.now().strftime('%Y-%m-%d'),
                'categoria': categoria,
                'modal': modal,
                'apenas_pendencias': apenas_pendencias,
                'secoes': {
                    'processos_chegando': processos_chegando,
                    'processos_prontos': processos_prontos,
                    'processos_em_dta': processos_em_dta,
                    'pendencias': pendencias,
                    'duimps_analise': duimps_analise,
                    'dis_analise': dis_analise,
                    'eta_alterado': eta_alterado,
                    'alertas': alertas
                },
                'resumo': {
                    'total_chegando': len(processos_chegando),
                    'total_prontos': len(processos_prontos),
                    'total_em_dta': len(processos_em_dta),
                    'total_pendencias': len(pendencias),
                    'total_duimps': len(duimps_analise),
                    'total_dis': len(dis_analise),
                    'total_eta_alterado': len(eta_alterado),
                    'total_alertas': len(alertas)
                }
            }
            
            # ✅ PASSO 6 - FASE 4: Gerar resposta usando fallback simples (substitui _formatar_dashboard_hoje)
            # A formatação com IA será feita depois pelo ResponseFormatter se precisar_formatar=True
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)
            
            # ✅ NOVO: Salvar relatório no contexto para uso em emails (usando report_service)
            # ✅ PASSO 6 - FASE 1: Incluir dados_json no meta_json para uso futuro
            try:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                session_id_para_salvar = context.get('session_id') if context else None
                if session_id_para_salvar:
                    relatorio = criar_relatorio_gerado(
                        tipo_relatorio='o_que_tem_hoje',
                        texto_chat=resposta,
                        categoria=categoria,
                        filtros={
                            'data_ref': datetime.now().strftime('%Y-%m-%d'),
                            'modal': modal,
                            'apenas_pendencias': apenas_pendencias
                        },
                        meta_json={
                            'total_chegando': len(processos_chegando),
                            'total_prontos': len(processos_prontos),
                            'total_em_dta': len(processos_em_dta),
                            'total_pendencias': len(pendencias),
                            'total_duimps': len(duimps_analise),
                            'total_dis': len(dis_analise),
                            'total_eta_alterado': len(eta_alterado),
                            'dados_json': dados_json  # ✅ PASSO 6: Incluir JSON estruturado completo
                        }
                    )
                    salvar_ultimo_relatorio(session_id_para_salvar, relatorio)
            except Exception as e:
                logger.debug(f'Erro ao salvar relatório no contexto: {e}')
            
            return {
                'sucesso': True,
                'resposta': resposta,  # ← String formatada (mantém compatibilidade/fallback)
                'dados_json': dados_json,  # ← JSON estruturado (nova estrutura)
                'precisa_formatar': FORMATAR_RELATORIOS_COM_IA,  # ← ✅ PASSO 6 - FASE 2: Controlado por variável de ambiente
                'dados': {  # ← Mantém estrutura antiga para compatibilidade
                    'processos_chegando': processos_chegando,
                    'processos_prontos': processos_prontos,
                    'processos_em_dta': processos_em_dta,
                    'pendencias': pendencias,
                    'duimps_analise': duimps_analise,
                    'dis_analise': dis_analise,
                    'eta_alterado': eta_alterado,
                    'alertas': alertas
                }
            }
        except Exception as e:
            logger.error(f'Erro ao obter dashboard hoje: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao obter dashboard: {str(e)}'
            }
    
    # ✅ PASSO 6 - FASE 4: _formatar_dashboard_hoje REMOVIDA (~585 linhas)
    # Substituída por RelatorioFormatterService.formatar_relatorio_fallback_simples()
    # A formatação agora usa JSON + IA (quando disponível) ou fallback simples
    # Esta função foi removida em 10/01/2026 como parte da refatoração
    
    def _formatar_relatorio_geral_categoria(
        self,
        processos_chegando: List[Dict[str, Any]],
        processos_prontos: List[Dict[str, Any]],
        processos_em_dta: List[Dict[str, Any]],
        pendencias: List[Dict[str, Any]],
        duimps_analise: List[Dict[str, Any]],
        dis_analise: List[Dict[str, Any]],
        eta_alterado: List[Dict[str, Any]],
        alertas: List[Dict[str, Any]],
        categoria: str
    ) -> str:
        """
        Formata relatório geral "como estão os X?" (não apenas "o que temos pra hoje").
        Mostra visão completa dos processos da categoria.
        """
        from datetime import datetime
        
        hoje = datetime.now().strftime('%d/%m/%Y')
        
        resposta = f"📋 **PROCESSOS {categoria.upper()} - STATUS GERAL**\n\n"
        resposta += f"📊 **Data:** {hoje}\n\n"
        resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # 1. Processos que chegaram SEM DI/DUIMP (todos, não apenas hoje)
        # ✅ CORREÇÃO: processos_chegando agora contém processos que chegaram sem DI/DUIMP (de listar_processos_liberados_registro)
        if processos_chegando:
            resposta += f"✅ **CHEGARAM (SEM DI/DUIMP)** ({len(processos_chegando)} processo(s)):\n\n"
            for proc in processos_chegando[:20]:
                proc_ref = proc.get('processo_referencia', 'N/A')
                porto = proc.get('porto_nome', '') or proc.get('porto', '')
                modal = proc.get('modal', '')
                # ✅ CORREÇÃO: listar_processos_liberados_registro retorna data_chegada em formato ISO
                data_chegada_raw = proc.get('data_chegada', '')
                situacao_ce = proc.get('situacao_ce', '') or proc.get('situacaoCargaCe', '')
                numero_ce = proc.get('numero_ce', '')
                numero_lpco = proc.get('numero_lpco', '')
                situacao_lpco = proc.get('situacao_lpco', '')
                
                # Formatar data de chegada
                data_chegada_str = ''
                if data_chegada_raw:
                    try:
                        from datetime import datetime
                        if isinstance(data_chegada_raw, str):
                            # Tentar parsear ISO format
                            data_chegada_clean = data_chegada_raw.replace('Z', '').split('+')[0].split('.')[0]
                            if 'T' in data_chegada_clean:
                                dt = datetime.fromisoformat(data_chegada_clean)
                            else:
                                dt = datetime.strptime(data_chegada_clean, '%Y-%m-%d')
                            data_chegada_str = dt.strftime('%d/%m/%Y')
                        else:
                            data_chegada_str = str(data_chegada_raw)
                    except:
                        data_chegada_str = str(data_chegada_raw)[:10]  # Pegar apenas a data se falhar
                
                linha = f"  • **{proc_ref}**"
                if porto:
                    linha += f" - Porto: {porto}"
                if modal:
                    linha += f" - Modal: {modal}"
                if data_chegada_str:
                    linha += f" - Chegou: {data_chegada_str}"
                if situacao_ce:
                    linha += f" - Status CE: {situacao_ce}"
                if numero_ce:
                    linha += f" - CE: {numero_ce}"
                if numero_lpco:
                    linha += f" - LPCO: {numero_lpco}"
                    if situacao_lpco and 'deferid' in situacao_lpco.lower():
                        linha += " (deferida)"
                
                # ✅ Estes processos já não têm DI/DUIMP (vêm de listar_processos_liberados_registro)
                linha += " - ⚠️ Sem DI/DUIMP"
                
                resposta += linha + "\n"
            if len(processos_chegando) > 20:
                resposta += f"  • ... e mais {len(processos_chegando) - 20} processo(s)\n"
            resposta += "\n"
        else:
            resposta += "✅ **CHEGARAM (SEM DI/DUIMP):** Nenhum processo chegou sem DI/DUIMP.\n\n"
        
        # 2. Processos com ETA futuro (sem chegada ainda)
        processos_com_eta = []
        for proc in processos_prontos:
            if proc.get('eta') and not proc.get('data_chegada'):
                processos_com_eta.append(proc)
        
        if processos_com_eta:
            resposta += f"📅 **COM ETA (SEM CHEGADA AINDA)** ({len(processos_com_eta)} processo(s)):\n\n"
            for proc in processos_com_eta[:20]:
                proc_ref = proc.get('processo_referencia', 'N/A')
                porto = proc.get('porto_nome', '')
                modal = proc.get('modal', '')
                eta = proc.get('eta', '')
                nome_navio = proc.get('nome_navio', '')
                
                linha = f"  • **{proc_ref}**"
                if porto:
                    linha += f" - Porto: {porto}"
                if modal:
                    linha += f" - Modal: {modal}"
                if nome_navio:
                    linha += f" - Navio: {nome_navio}"
                if eta:
                    linha += f" - ETA: {eta}"
                
                resposta += linha + "\n"
            if len(processos_com_eta) > 20:
                resposta += f"  • ... e mais {len(processos_com_eta) - 20} processo(s)\n"
            resposta += "\n"
        
        # 3. Processos em DTA
        if processos_em_dta:
            resposta += f"🚚 **PROCESSOS EM DTA** ({len(processos_em_dta)} processo(s)):\n\n"
            for proc in processos_em_dta[:10]:
                proc_ref = proc.get('processo_referencia', 'N/A')
                dta = proc.get('numero_dta', '')
                data_chegada = proc.get('data_chegada', '')
                situacao_ce = proc.get('situacao_ce', '')
                
                linha = f"  • **{proc_ref}**"
                if dta:
                    linha += f" - DTA: {dta}"
                if data_chegada:
                    linha += f" - Chegou: {data_chegada}"
                if situacao_ce:
                    linha += f" - Status CE: {situacao_ce}"
                
                resposta += linha + "\n"
            if len(processos_em_dta) > 10:
                resposta += f"  • ... e mais {len(processos_em_dta) - 10} processo(s)\n"
            resposta += "\n"
        
        # 4. Pendências ativas
        if pendencias:
            resposta += f"⚠️ **PENDÊNCIAS ATIVAS** ({len(pendencias)} processo(s)):\n\n"
            for pend in pendencias[:10]:
                proc_ref = pend.get('processo_referencia', 'N/A')
                tipo = pend.get('tipo_pendencia', '')
                descricao = pend.get('descricao_pendencia', '')
                tempo = pend.get('tempo_pendente', '')
                acao = pend.get('acao_sugerida', '')
                
                linha = f"  • **{proc_ref}**"
                if tipo:
                    linha += f" - {tipo}"
                if descricao:
                    linha += f": {descricao}"
                if tempo:
                    linha += f" (há {tempo})"
                if acao:
                    linha += f" - Ação: {acao}"
                
                resposta += linha + "\n"
            if len(pendencias) > 10:
                resposta += f"  • ... e mais {len(pendencias) - 10} processo(s)\n"
            resposta += "\n"
        else:
            resposta += "✅ **PENDÊNCIAS ATIVAS:** Nenhuma pendência ativa.\n\n"
        
        # 5. DIs (registro/canal/status)
        if dis_analise:
            resposta += f"📋 **DIs (REGISTRO/CANAL/STATUS)** ({len(dis_analise)} DI(s)):\n"
            resposta += "_Obs.: **Registro** = dataHoraRegistro; **Desembaraço** = dataHoraDesembaraco._\n\n"
            for di in dis_analise[:10]:
                numero_di = di.get('numero_di', 'N/A')
                proc_ref = di.get('processo_referencia', 'N/A')
                canal = di.get('canal') or di.get('canal_di', '')
                situacao = di.get('situacao_di', '')
                desembaraco = di.get('data_desembaraco', '')
                entrega = di.get('situacao_entrega') or di.get('situacao_entrega_carga') or di.get('situacao_entrega_tabela') or ''
                data_registro = di.get('data_registro') or di.get('data_hora_registro')
                
                linha = f"  • **{numero_di}** - Processo: {proc_ref}"
                if canal:
                    linha += f" - Canal: {canal}"
                if situacao:
                    linha += f" - Status: {situacao}"
                if data_registro:
                    try:
                        from datetime import datetime
                        data_limpa = str(data_registro).replace('Z', '').replace('+00:00', '').strip()
                        dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                        if dt:
                            linha += f" - Registro: {dt.strftime('%d/%m/%Y %H:%M')}"
                        else:
                            linha += f" - Registro: {data_registro}"
                    except Exception:
                        linha += f" - Registro: {data_registro}"
                if desembaraco:
                    try:
                        from datetime import datetime
                        data_limpa = str(desembaraco).replace('Z', '').replace('+00:00', '').strip()
                        dt = datetime.fromisoformat(data_limpa.replace(' ', 'T')) if ('T' in data_limpa or ' ' in data_limpa) else None
                        if dt:
                            linha += f" - Desembaraço: {dt.strftime('%d/%m/%Y %H:%M')}"
                        else:
                            linha += f" - Desembaraço: {desembaraco}"
                    except Exception:
                        linha += f" - Desembaraço: {desembaraco}"
                if entrega:
                    linha += f" - Entrega: {entrega}"
                
                resposta += linha + "\n"
            if len(dis_analise) > 10:
                resposta += f"  • ... e mais {len(dis_analise) - 10} DI(s)\n"
            resposta += "\n"
        else:
            resposta += "✅ **DIs (REGISTRO/CANAL/STATUS):** Nenhuma DI listada.\n\n"
        
        # 6. DUIMPs em análise
        if duimps_analise:
            resposta += f"📋 **DUIMPs EM ANÁLISE** ({len(duimps_analise)} DUIMP(s)):\n\n"
            for duimp in duimps_analise[:10]:
                numero_duimp = duimp.get('numero_duimp', 'N/A')
                versao = duimp.get('versao', '')
                proc_ref = duimp.get('processo_referencia', 'N/A')
                canal = duimp.get('canal') or duimp.get('canal_duimp', '')
                situacao = duimp.get('situacao_duimp', '') or duimp.get('status', '')
                data_registro = duimp.get('data_registro') or duimp.get('data_criacao')
                
                linha = f"  • **{numero_duimp}**"
                if versao:
                    linha += f" v{versao}"
                linha += f" - Processo: {proc_ref}"
                if canal:
                    linha += f" - Canal: {canal}"
                if situacao:
                    linha += f" - Status: {situacao}"
                if data_registro:
                    linha += f" - Registro: {data_registro}"
                
                resposta += linha + "\n"
            if len(duimps_analise) > 10:
                resposta += f"  • ... e mais {len(duimps_analise) - 10} DUIMP(s)\n"
            resposta += "\n"
        else:
            resposta += "✅ **DUIMPs EM ANÁLISE:** Nenhuma DUIMP em análise.\n\n"
        
        # 7. ETA alterado
        if eta_alterado:
            resposta += f"🔄 **ETA ALTERADO** ({len(eta_alterado)} processo(s)):\n\n"
            for proc in eta_alterado[:10]:
                proc_ref = proc.get('processo_referencia', 'N/A')
                eta_anterior = proc.get('eta_anterior', '')
                eta_novo = proc.get('eta_novo', '')
                
                linha = f"  • **{proc_ref}**"
                if eta_anterior and eta_novo:
                    linha += f" - ETA: {eta_anterior} → {eta_novo}"
                elif eta_novo:
                    linha += f" - Novo ETA: {eta_novo}"
                
                resposta += linha + "\n"
            if len(eta_alterado) > 10:
                resposta += f"  • ... e mais {len(eta_alterado) - 10} processo(s)\n"
            resposta += "\n"
        
        # 8. Alertas recentes
        if alertas:
            resposta += f"🔔 **ALERTAS RECENTES** ({len(alertas)} alerta(s)):\n\n"
            for alerta in alertas[:5]:
                tipo = alerta.get('tipo', '')
                proc_ref = alerta.get('processo_referencia', 'N/A')
                mensagem = alerta.get('mensagem', '')
                data = alerta.get('data', '')
                
                linha = f"  • **{proc_ref}**"
                if tipo:
                    linha += f" - {tipo}"
                if mensagem:
                    linha += f": {mensagem}"
                if data:
                    linha += f" ({data})"
                
                resposta += linha + "\n"
            if len(alertas) > 5:
                resposta += f"  • ... e mais {len(alertas) - 5} alerta(s)\n"
            resposta += "\n"
        
        # Resumo final
        resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        resposta += "✅ **RESUMO:**\n"
        resposta += f"  • {len(processos_chegando)} processo(s) chegaram (sem DI/DUIMP)\n"
        resposta += f"  • {len(processos_com_eta)} processo(s) com ETA (sem chegada ainda)\n"
        resposta += f"  • {len(processos_em_dta)} processo(s) em DTA\n"
        resposta += f"  • {len(pendencias)} pendência(s) ativa(s)\n"
        resposta += f"  • {len(dis_analise)} DI(s) em análise\n"
        resposta += f"  • {len(duimps_analise)} DUIMP(s) em análise\n"
        
        return resposta
    
    def _gerar_sugestoes_acoes(
        self,
        processos_chegando: List[Dict[str, Any]],
        processos_prontos: List[Dict[str, Any]],
        pendencias: List[Dict[str, Any]],
        duimps_analise: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Gera sugestões de ações priorizadas, com foco em processos com atraso crítico.
        """
        from datetime import datetime, date
        sugestoes = []
        hoje = date.today()
        
        # ✅ NOVO: Separar processos prontos por nível de atraso
        processos_com_atraso_critico = []  # Mais de 7 dias
        processos_com_atraso = []  # 3-7 dias
        processos_recentes = []  # Menos de 3 dias
        
        for proc in processos_prontos:
            dias_atraso = None
            if proc.get('data_destino_final'):
                try:
                    if isinstance(proc['data_destino_final'], str):
                        if 'T' in proc['data_destino_final']:
                            data_chegada = datetime.fromisoformat(proc['data_destino_final'].replace('Z', '+00:00')).date()
                        else:
                            data_chegada = datetime.strptime(proc['data_destino_final'], '%Y-%m-%d').date()
                    else:
                        data_chegada = proc['data_destino_final']
                    dias_atraso = (hoje - data_chegada).days
                except:
                    pass
            
            if dias_atraso and dias_atraso > 7:
                processos_com_atraso_critico.append(proc)
            elif dias_atraso and dias_atraso >= 3:
                processos_com_atraso.append(proc)
            else:
                processos_recentes.append(proc)
        
        # Prioridade 1: Processos com ATRASO CRÍTICO (mais de 7 dias) - MÁXIMA PRIORIDADE
        for proc in processos_com_atraso_critico:
            if proc.get('processo_referencia'):
                dias_atraso = proc.get('dias_atraso', 0)
                sugestoes.append(f"🚨 URGENTE: Criar {proc.get('tipo_documento', 'DUIMP')} para {proc['processo_referencia']} ({dias_atraso} dia(s) de atraso!)")
        
        # Prioridade 2: Processos chegando hoje sem DUIMP
        for proc in processos_chegando:
            if proc.get('processo_referencia'):
                sugestoes.append(f"🔥 Criar DUIMP para {proc['processo_referencia']} (urgente - chegou hoje)")
        
        # Prioridade 3: Pendências bloqueantes
        for pend in pendencias:
            if pend.get('tipo_pendencia') in ['Bloqueio CE', 'LPCO']:
                sugestoes.append(f"⚠️ Verificar {pend['tipo_pendencia'].lower()} de {pend['processo_referencia']} (bloqueante)")
        
        # Prioridade 4: Processos com atraso moderado (3-7 dias)
        for proc in processos_com_atraso:
            if proc.get('processo_referencia'):
                dias_atraso = proc.get('dias_atraso', 0)
                sugestoes.append(f"⚠️ Criar {proc.get('tipo_documento', 'DUIMP')} para {proc['processo_referencia']} ({dias_atraso} dia(s) de atraso)")
        
        # Prioridade 5: Processos prontos recentes (menos de 3 dias)
        for proc in processos_recentes[:3]:  # Limitar a 3
            if proc.get('processo_referencia'):
                sugestoes.append(f"📋 Criar {proc.get('tipo_documento', 'DUIMP')} para {proc['processo_referencia']} (pronto para registro)")
        
        # Prioridade 6: Pendências não bloqueantes
        for pend in pendencias:
            if pend.get('tipo_pendencia') in ['ICMS', 'AFRMM']:
                tempo = pend.get('tempo_pendente', '')
                if 'dia' in tempo and int(tempo.split()[0]) >= 2:  # Pendente há 2+ dias
                    sugestoes.append(f"⚠️ Verificar {pend['tipo_pendencia']} de {pend['processo_referencia']} (pendente há {tempo})")
        
        return sugestoes[:10]  # Limitar a 10 sugestões
    
    def _fechar_dia(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retorna resumo de todas as movimentações do dia (fechamento do dia).
        """
        try:
            from db_manager import obter_movimentacoes_hoje
            
            # Extrair filtros
            categoria = arguments.get('categoria')
            modal = arguments.get('modal')
            
            # ✅ CRÍTICO: Se categoria foi passada mas não foi mencionada explicitamente pelo usuário, limpar
            # Isso previne uso de categoria do contexto quando não deveria
            if categoria:
                logger.info(f'🔍 fechar_dia recebeu categoria={categoria} - será usado como filtro')
            else:
                logger.info(f'🔍 fechar_dia SEM categoria - retornando todas as movimentações')
            
            # Buscar movimentações
            movimentacoes = obter_movimentacoes_hoje(categoria, modal)

            # ✅ Correção (14/01/2026): Deduplicar DIs registradas hoje
            # Observação: algumas fontes podem retornar a mesma DI repetida; para o fechamento do dia,
            # exibimos DIs únicas por número.
            try:
                dis_registradas_raw = movimentacoes.get('dis_registradas', []) or []
                dis_unicas: List[Any] = []
                vistos: set = set()
                for di in dis_registradas_raw:
                    if isinstance(di, dict):
                        numero = str(di.get('numero') or di.get('numero_di') or di.get('di') or '').strip()
                        chave = numero if numero else str(di)
                    else:
                        chave = str(di)
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    dis_unicas.append(di)
                movimentacoes['dis_registradas'] = dis_unicas
            except Exception as _e_dedupe:
                logger.debug(f'⚠️ Não foi possível deduplicar dis_registradas no fechamento do dia: {_e_dedupe}')
            
            # ✅ PASSO 6 - FASE 4: Criar JSON estruturado primeiro (fonte da verdade)
            from datetime import datetime

            # ✅ NOVO: Lista achatada (para responder “quais foram essas X movimentações?”)
            movimentacoes_flat: List[Dict[str, Any]] = []
            try:
                def _add_mov(tipo: str, item: Any) -> None:
                    if not isinstance(item, dict):
                        movimentacoes_flat.append({'tipo': tipo, 'raw': item})
                        return

                    mov: Dict[str, Any] = {'tipo': tipo}
                    proc_ref = item.get('processo_referencia')
                    if proc_ref:
                        mov['processo_referencia'] = proc_ref

                    # Documento (se houver)
                    if item.get('numero_ce') or item.get('numeroCe'):
                        mov['documento'] = {'tipo': 'CE', 'numero': item.get('numero_ce') or item.get('numeroCe')}
                    elif item.get('numero_di') or item.get('numeroDi'):
                        mov['documento'] = {'tipo': 'DI', 'numero': item.get('numero_di') or item.get('numeroDi')}
                    elif item.get('numero_duimp') or item.get('numeroDuimp'):
                        mov['documento'] = {'tipo': 'DUIMP', 'numero': item.get('numero_duimp') or item.get('numeroDuimp')}
                    elif item.get('numero') and isinstance(item.get('numero'), str) and item.get('numero').isdigit():
                        # DIs/DUIMPs (sqlite)
                        mov['documento'] = {'tipo': item.get('tipo') or 'DOC', 'numero': item.get('numero')}

                    # Status (se houver)
                    for k in ('status', 'situacao_ce', 'situacao_di', 'situacao_entrega'):
                        if item.get(k):
                            mov['status'] = item.get(k)
                            break

                    # Data (se houver)
                    # Preferir a data real do evento (ex.: desembaraço/registro/chegada) quando disponível.
                    for k in ('data_desembaraco', 'data_registro', 'data_chegada', 'atualizado_em', 'criado_em'):
                        if item.get(k):
                            mov['data'] = item.get(k)
                            break

                    movimentacoes_flat.append(mov)

                for it in (movimentacoes.get('processos_chegaram') or []):
                    _add_mov('PROCESSO_CHEGOU', it)
                for it in (movimentacoes.get('processos_desembaracados') or []):
                    _add_mov('PROCESSO_DESEMBARACADO', it)
                for it in (movimentacoes.get('dis_registradas') or []):
                    _add_mov('DI_REGISTRADA', it)
                for it in (movimentacoes.get('duimps_criadas') or []):
                    _add_mov('DUIMP_REGISTRADA', it)
                for it in (movimentacoes.get('mudancas_status_ce') or []):
                    _add_mov('STATUS_CE', it)
                for it in (movimentacoes.get('mudancas_status_di') or []):
                    _add_mov('STATUS_DI', it)
                for it in (movimentacoes.get('mudancas_status_duimp') or []):
                    _add_mov('STATUS_DUIMP', it)
                for it in (movimentacoes.get('pendencias_resolvidas') or []):
                    _add_mov('PENDENCIA_RESOLVIDA', it)
            except Exception as _e_flat:
                logger.debug(f'⚠️ Erro ao montar movimentacoes_flat no fechamento: {_e_flat}')

            dados_json = {
                'tipo_relatorio': 'fechamento_dia',  # ← Tipo explícito, não precisa regex!
                'data': datetime.now().strftime('%Y-%m-%d'),
                'categoria': categoria,
                'modal': modal,
                'secoes': {
                    'processos_chegaram': movimentacoes.get('processos_chegaram', []),
                    'processos_desembaracados': movimentacoes.get('processos_desembaracados', []),
                    'duimps_criadas': movimentacoes.get('duimps_criadas', []),
                    'dis_registradas': movimentacoes.get('dis_registradas', []),
                    'mudancas_status_ce': movimentacoes.get('mudancas_status_ce', []),
                    'mudancas_status_di': movimentacoes.get('mudancas_status_di', []),
                    'mudancas_status_duimp': movimentacoes.get('mudancas_status_duimp', []),
                    'pendencias_resolvidas': movimentacoes.get('pendencias_resolvidas', []),
                    'movimentacoes': movimentacoes_flat,
                },
                'resumo': {
                    'total_movimentacoes': movimentacoes.get('total_movimentacoes', 0),
                    'total_chegaram': len(movimentacoes.get('processos_chegaram', [])),
                    'total_desembaracados': len(movimentacoes.get('processos_desembaracados', [])),
                    'total_duimps_criadas': len(movimentacoes.get('duimps_criadas', [])),
                    'total_dis_registradas': len(movimentacoes.get('dis_registradas', [])),
                    'total_mudancas_status_ce': len(movimentacoes.get('mudancas_status_ce', [])),
                    'total_mudancas_status_di': len(movimentacoes.get('mudancas_status_di', [])),
                    'total_mudancas_status_duimp': len(movimentacoes.get('mudancas_status_duimp', [])),
                    'total_pendencias_resolvidas': len(movimentacoes.get('pendencias_resolvidas', [])),
                    'total_movimentacoes_detalhadas': len(movimentacoes_flat),
                }
            }
            
            # ✅ PASSO 6 - FASE 4: Gerar resposta usando fallback simples (substitui _formatar_fechamento_dia)
            # A formatação com IA será feita depois pelo ResponseFormatter se precisar_formatar=True
            resposta = RelatorioFormatterService.formatar_relatorio_fallback_simples(dados_json)
            
            # ✅ NOVO: Salvar relatório no contexto para uso em emails
            # ✅ PASSO 6 - FASE 1: Incluir dados_json no meta_json para uso futuro
            try:
                from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                session_id_para_salvar = context.get('session_id') if context else None
                if session_id_para_salvar:
                    relatorio = criar_relatorio_gerado(
                        tipo_relatorio='fechamento_dia',
                        texto_chat=resposta,
                        categoria=categoria,
                        filtros={
                            'data_ref': datetime.now().strftime('%Y-%m-%d'),
                            'modal': modal
                        },
                        meta_json={
                            'total_movimentacoes': movimentacoes.get('total_movimentacoes', 0),
                            'processos_chegaram': len(movimentacoes.get('processos_chegaram', [])),
                            'processos_desembaracados': len(movimentacoes.get('processos_desembaracados', [])),
                            'duimps_criadas': len(movimentacoes.get('duimps_criadas', [])),
                            'dis_registradas': len(movimentacoes.get('dis_registradas', [])),
                            'dados_json': dados_json  # ✅ PASSO 6: Incluir JSON estruturado completo
                        }
                    )
                    salvar_ultimo_relatorio(session_id_para_salvar, relatorio)
            except Exception as e:
                logger.debug(f'Erro ao salvar relatório no contexto: {e}')
            
            return {
                'sucesso': True,
                'resposta': resposta,  # ← String formatada (mantém compatibilidade)
                'dados_json': dados_json,  # ← JSON estruturado (nova estrutura)
                'precisa_formatar': FORMATAR_RELATORIOS_COM_IA,  # ← ✅ PASSO 6 - FASE 2: Controlado por variável de ambiente
                'dados': movimentacoes  # ← Mantém estrutura antiga para compatibilidade
            }
        except Exception as e:
            logger.error(f'Erro ao fechar dia: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao fechar dia: {str(e)}'
            }
    
    # ✅ PASSO 6 - FASE 4: _formatar_fechamento_dia REMOVIDA (~140 linhas)
    # Substituída por RelatorioFormatterService.formatar_relatorio_fallback_simples()
    # A formatação agora usa JSON + IA (quando disponível) ou fallback simples
    # Esta função foi removida em 10/01/2026 como parte da refatoração
    
    def _consultar_contexto_sessao(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        ✅ NOVO (12/01/2026): Consulta o contexto REAL salvo na sessão atual.
        
        Retorna APENAS o que está realmente salvo no banco de dados,
        sem inventar ou inferir informações detalhadas.
        """
        try:
            session_id = context.get('session_id') if context else None
            
            if not session_id:
                return {
                    'sucesso': False,
                    'erro': 'SESSION_ID_NAO_FORNECIDO',
                    'resposta': '❌ Não foi possível consultar o contexto: session_id não fornecido.'
                }
            
            from services.context_service import obter_contexto_formatado_para_usuario
            
            contexto_texto = obter_contexto_formatado_para_usuario(session_id)
            
            # ✅ NOVO (12/01/2026): Buscar JSON inline do último relatório para mostrar contexto visual
            json_inline_info = ""
            try:
                from services.report_service import buscar_ultimo_relatorio
                relatorio_salvo = buscar_ultimo_relatorio(session_id, tipo_relatorio=None)
                if relatorio_salvo and relatorio_salvo.texto_chat:
                    # Procurar JSON inline no texto do relatório
                    import re
                    # ✅ CORREÇÃO (12/01/2026): Regex corrigido para capturar JSON completo (pode ter chaves aninhadas)
                    match_json = re.search(r'\[REPORT_META:({.+?})\]', relatorio_salvo.texto_chat, re.DOTALL)
                    if match_json:
                        import json
                        try:
                            meta_json = json.loads(match_json.group(1))
                            json_inline_info = f"\n\n📊 **RELATÓRIO EM TELA (JSON Inline):**\n"
                            json_inline_info += f"- Tipo: {meta_json.get('tipo', 'N/A')}\n"
                            json_inline_info += f"- ID: {meta_json.get('id', 'N/A')}\n"
                            json_inline_info += f"- Data: {meta_json.get('data', 'N/A')}\n"
                            
                            # ✅ NOVO (12/01/2026): Mostrar created_at e calcular idade
                            created_at = meta_json.get('created_at')
                            if created_at:
                                try:
                                    from datetime import datetime
                                    # Parsear timestamp ISO 8601 (formato: 2026-01-12T14:58:32-03:00)
                                    if 'T' in created_at:
                                        # Extrair data e hora (ignorar timezone por simplicidade)
                                        partes = created_at.split('T')
                                        data_part = partes[0]
                                        hora_part = partes[1].split('-')[0].split('+')[0]  # Remover timezone
                                        dt = datetime.strptime(f"{data_part}T{hora_part}", '%Y-%m-%dT%H:%M:%S')
                                        agora = datetime.now()
                                        diff_minutos = int((agora - dt).total_seconds() / 60)
                                        hora_formatada = hora_part
                                        json_inline_info += f"- Criado há: {diff_minutos} minuto(s) atrás ({hora_formatada})\n"
                                except Exception as e:
                                    json_inline_info += f"- Criado em: {created_at}\n"
                            
                            # ✅ NOVO (12/01/2026): Mostrar TTL
                            ttl_min = meta_json.get('ttl_min')
                            if ttl_min:
                                json_inline_info += f"- TTL: {ttl_min} minutos\n"
                            
                            # ✅ NOVO (12/01/2026): Mostrar contagens por seção
                            counts = meta_json.get('counts', {})
                            if counts:
                                json_inline_info += f"- Contagens: "
                                counts_str = []
                                for secao, count in counts.items():
                                    if count > 0:  # Só mostrar seções com itens
                                        counts_str.append(f"{secao}: {count}")
                                if counts_str:
                                    json_inline_info += ', '.join(counts_str) + "\n"
                                else:
                                    json_inline_info += "nenhuma seção com itens\n"
                            
                            secoes = meta_json.get('secoes', [])
                            if secoes:
                                json_inline_info += f"- Seções disponíveis: {', '.join(secoes)}\n"
                            if meta_json.get('categoria'):
                                json_inline_info += f"- Categoria: {meta_json.get('categoria')}\n"
                            if meta_json.get('filtrado'):
                                json_inline_info += f"- Filtrado: Sim (seções: {', '.join(meta_json.get('secoes_filtradas', []))})\n"
                            logger.info(f"✅ JSON inline encontrado no último relatório: {meta_json.get('tipo')} (ID: {meta_json.get('id')})")
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️ Erro ao parsear JSON inline do relatório")
            except Exception as e:
                logger.debug(f"Erro ao buscar JSON inline do relatório: {e}")
            
            if contexto_texto == "Nenhum contexto salvo no momento.":
                if json_inline_info:
                    resposta = f"📌 **CONTEXTO ATUAL:**\n\nNenhum contexto salvo no momento.{json_inline_info}\n\n💡 O contexto é limpo automaticamente quando você:\n- Menciona outro processo\n- Usa comandos como 'reset' ou 'limpar contexto'"
                else:
                    resposta = "📌 **CONTEXTO ATUAL:**\n\nNenhum contexto salvo no momento.\n\n💡 O contexto é limpo automaticamente quando você:\n- Menciona outro processo\n- Usa comandos como 'reset' ou 'limpar contexto'"
            else:
                resposta = f"📌 **CONTEXTO ATUAL:**\n\n{contexto_texto}{json_inline_info}\n\n💡 **IMPORTANTE:** Este é o contexto REAL salvo no banco de dados.\n⚠️ NÃO inclui informações detalhadas sobre processos (modal, situação, CE, valores, etc.) - apenas o número do processo e categoria mencionados anteriormente.\n\n💡 Para ver detalhes de um processo, pergunte especificamente sobre ele (ex: 'como está o BND.0083/25?')."
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'contexto': contexto_texto,
                    'session_id': session_id
                }
            }
        except Exception as e:
            logger.error(f'❌ Erro ao consultar contexto de sessão: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao consultar contexto: {str(e)}'
            }
    
    def _buscar_secao_relatorio_salvo(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        ✅ NOVO (12/01/2026): Busca uma seção específica do último relatório salvo.
        
        Permite que a IA busque apenas a seção solicitada do JSON salvo,
        sem precisar gerar um novo relatório completo.
        
        ✅ MELHORIA (14/01/2026): Usa active_report_id primeiro (mais confiável).
        """
        try:
            session_id = context.get('session_id') if context else None
            
            if not session_id:
                return {
                    'sucesso': False,
                    'erro': 'SESSION_ID_NAO_FORNECIDO',
                    'resposta': '❌ Não foi possível buscar a seção: session_id não fornecido.'
                }
            
            secao = arguments.get('secao')
            categoria = arguments.get('categoria')  # ✅ NOVO (14/01/2026): Aceitar categoria para filtrar
            tipo_relatorio = arguments.get('tipo_relatorio')
            report_id = arguments.get('report_id')  # ✅ NOVO: Aceitar report_id diretamente
            # ✅ NOVO (20/01/2026): Filtros comuns de follow-up do dashboard
            canal = arguments.get('canal')  # ex.: 'Verde'/'Vermelho'
            tipo_pendencia = arguments.get('tipo_pendencia')  # ex.: 'Frete', 'ICMS'
            tipo_mudanca = arguments.get('tipo_mudanca')  # ex.: 'ATRASO'/'ADIANTADO'
            min_dias = arguments.get('min_dias')  # ex.: 7 (atraso > 7)
            status_contains = arguments.get('status_contains')  # ex.: 'desembara', 'rascunho'
            min_age_dias = arguments.get('min_age_dias')  # ex.: 7 (>= 7 dias)
            
            # ✅ NOVO (14/01/2026): Se categoria fornecida mas secao não, filtrar por categoria
            if categoria and not secao:
                # Filtrar relatório por categoria (processar todas as seções filtradas)
                logger.info(f'✅ Filtro por categoria detectado: {categoria}')
                # Continuar processamento abaixo - vai filtrar todas as seções
            elif not secao and not categoria:
                return {
                    'sucesso': False,
                    'erro': 'SECAO_OU_CATEGORIA_NAO_FORNECIDA',
                    'resposta': '❌ Seção ou categoria não fornecida. Seções disponíveis: alertas, dis_analise, duimps_analise, processos_prontos, pendencias, eta_alterado, processos_chegando. Ou forneça uma categoria (ex: DMD, ALH, VDM) para filtrar o relatório.'
                }
            
            # Buscar relatório salvo
            from services.report_service import buscar_ultimo_relatorio, obter_tipo_relatorio_salvo, buscar_relatorio_por_id, obter_active_report_id
            
            relatorio_salvo = None
            
            # ✅ MELHORIA (14/01/2026): Prioridade 1 - Se report_id fornecido, usar diretamente
            if report_id:
                relatorio_salvo = buscar_relatorio_por_id(session_id, report_id)
                if relatorio_salvo:
                    logger.info(f"✅ Relatório encontrado por report_id: {report_id}")
            
            # ✅ MELHORIA (14/01/2026): Prioridade 2 - Usar active_report_id (mais confiável)
            if not relatorio_salvo:
                # ✅ CORREÇÃO B: Usar domínio 'processos' por padrão
                active_id = obter_active_report_id(session_id, dominio='processos')
                if active_id:
                    relatorio_salvo = buscar_relatorio_por_id(session_id, active_id)
                    if relatorio_salvo:
                        logger.info(f"✅ Relatório encontrado via active_report_id: {active_id}")
            
            # ✅ MELHORIA (14/01/2026): Prioridade 3 - Buscar por tipo_relatorio
            if not relatorio_salvo:
                # Se tipo não fornecido, tentar detectar automaticamente
                if not tipo_relatorio:
                    tipo_relatorio = obter_tipo_relatorio_salvo(session_id)
                
                if tipo_relatorio:
                    relatorio_salvo = buscar_ultimo_relatorio(session_id, tipo_relatorio=tipo_relatorio)
                    if relatorio_salvo:
                        logger.info(f"✅ Relatório encontrado por tipo: {tipo_relatorio}")
            
            # ✅ MELHORIA (14/01/2026): Prioridade 4 - Buscar último relatório sem filtro
            if not relatorio_salvo:
                relatorio_salvo = buscar_ultimo_relatorio(session_id, tipo_relatorio=None)
                if relatorio_salvo:
                    logger.info(f"✅ Relatório encontrado (último sem filtro)")
            
            if not relatorio_salvo or not relatorio_salvo.meta_json:
                return {
                    'sucesso': False,
                    'erro': 'RELATORIO_NAO_ENCONTRADO',
                    'resposta': '❌ Relatório salvo não encontrado ou sem dados JSON. Gere um novo relatório primeiro (ex: "o que temos pra hoje?") e depois peça a seção específica.'
                }
            
            # Buscar JSON (priorizar original completo)
            dados_json = relatorio_salvo.meta_json.get('dados_json_original') or relatorio_salvo.meta_json.get('dados_json')
            
            if not dados_json:
                return {
                    'sucesso': False,
                    'erro': 'JSON_NAO_ENCONTRADO',
                    'resposta': '❌ Dados JSON do relatório não encontrados.'
                }
            
            # ✅ UX (19/01/2026): Se o usuário pedir "filtre só os X" em cima de um relatório JÁ filtrado,
            # voltar automaticamente para o relatório-base (não filtrado) mais recente do mesmo tipo.
            # Isso evita o comportamento confuso: "filtre BGR" → depois "filtre MCD" e dizer que não existe.
            if categoria and not report_id and isinstance(dados_json, dict) and dados_json.get('filtrado'):
                try:
                    from services.context_service import buscar_contexto_sessao
                    import re
                    import json as _json
                    from services.report_service import buscar_relatorio_por_id as _buscar_por_id

                    tipo_alvo = relatorio_salvo.tipo_relatorio
                    contextos = buscar_contexto_sessao(session_id=session_id, tipo_contexto='ultimo_relatorio', chave=None) or []

                    melhor_id = None
                    melhor_ts = None
                    for ctx in contextos:
                        dados_ctx = ctx.get('dados', {}) or {}
                        try:
                            texto_chat_ctx = (dados_ctx.get('texto_chat') or '')
                            if not texto_chat_ctx:
                                continue
                            # só considerar mesmo tipo
                            if (dados_ctx.get('tipo_relatorio') or '') != tipo_alvo:
                                continue
                            m = re.search(r'\[REPORT_META:({.+?})\]', texto_chat_ctx, re.DOTALL)
                            if not m:
                                continue
                            meta = _json.loads(m.group(1))
                            if meta.get('filtrado'):
                                continue
                            rid = meta.get('id')
                            ts = meta.get('created_at')
                            if not rid:
                                continue
                            if (melhor_ts is None) or (ts and ts > melhor_ts):
                                melhor_id = rid
                                melhor_ts = ts

                        except Exception:
                            continue

                    if melhor_id:
                        base = _buscar_por_id(session_id, melhor_id)
                        if base and base.meta_json:
                            dados_base = base.meta_json.get('dados_json_original') or base.meta_json.get('dados_json')
                            if isinstance(dados_base, dict) and dados_base.get('secoes'):
                                logger.info(f'✅ Filtro em cascata: usando relatório-base não filtrado (id={melhor_id}, tipo={tipo_alvo})')
                                relatorio_salvo = base
                                dados_json = dados_base
                except Exception as _e_base:
                    logger.debug(f'⚠️ Não foi possível voltar ao relatório-base para novo filtro: {_e_base}')

            secoes = dados_json.get('secoes', {})
            
            # ✅ NOVO (14/01/2026): Se categoria fornecida, filtrar todas as seções por categoria
            if categoria:
                logger.info(f'✅ Filtrando relatório por categoria: {categoria}')
                
                def _extrair_processo_ref(item: Any) -> str:
                    """
                    Extrai melhor-effort um processo no formato XXX.0000/00 de dicts heterogêneos.
                    Evita falso negativo em seções como DUIMPs/alertas.
                    """
                    if not isinstance(item, dict):
                        return ''
                    for k in (
                        'processo_referencia',
                        'processo',
                        'processo_ref',
                        'processoRefer',
                        'processoReferencia',
                        'processo_atual',
                        'processoAtual',
                    ):
                        v = item.get(k)
                        if isinstance(v, str) and v.strip():
                            return v.strip()
                    # fallback: procurar padrão em strings do dict
                    try:
                        import re
                        for v in item.values():
                            if not isinstance(v, str):
                                continue
                            m = re.search(r'\b([A-Z]{2,5}\.\d{4}/\d{2})\b', v.upper())
                            if m:
                                return m.group(1)
                    except Exception:
                        return ''
                    return ''

                # Filtrar todas as seções por categoria
                secoes_filtradas_por_categoria = {}
                secoes_filtradas_keys = []
                
                for secao_key, secao_dados in secoes.items():
                    if isinstance(secao_dados, list):
                        # Filtrar itens da seção que pertencem à categoria
                        itens_filtrados = [
                            item for item in secao_dados
                            if _extrair_processo_ref(item).upper().startswith(f'{categoria.upper()}.')
                        ]
                        if itens_filtrados:
                            secoes_filtradas_por_categoria[secao_key] = itens_filtrados
                            secoes_filtradas_keys.append(secao_key)
                    elif isinstance(secao_dados, dict):
                        # Para seções que são dicts (ex: alertas), verificar se tem processos da categoria
                        # Por enquanto, manter a seção se tiver dados
                        if secao_dados:
                            secoes_filtradas_por_categoria[secao_key] = secao_dados
                            secoes_filtradas_keys.append(secao_key)
                
                if not secoes_filtradas_por_categoria:
                    # ✅ UX: explicar o contexto e listar categorias presentes no relatório-base
                    categorias_presentes = set()
                    try:
                        for _k, _v in (secoes or {}).items():
                            if not isinstance(_v, list):
                                continue
                            for item in _v:
                                if not isinstance(item, dict):
                                    continue
                                proc_ref = _extrair_processo_ref(item).strip()
                                if '.' in proc_ref:
                                    categorias_presentes.add(proc_ref.split('.', 1)[0].upper())
                    except Exception:
                        categorias_presentes = set()

                    tipo_atual = (dados_json.get('tipo_relatorio') or relatorio_salvo.tipo_relatorio or '').strip()
                    data_ref = (dados_json.get('data') or '').strip()
                    titulo_ctx = 'relatório'
                    if tipo_atual == 'fechamento_dia':
                        titulo_ctx = 'fechamento do dia'
                    elif tipo_atual == 'o_que_tem_hoje':
                        titulo_ctx = 'o que temos pra hoje'

                    cats_txt = ''
                    if categorias_presentes:
                        cats_txt = f"\n\n📌 Categorias que aparecem neste {titulo_ctx}: **{', '.join(sorted(categorias_presentes))}**."

                    data_txt = f" ({data_ref})" if data_ref else ""
                    return {
                        'sucesso': False,
                        'erro': 'CATEGORIA_NAO_ENCONTRADA',
                        'resposta': (
                            f"❌ Não encontrei **{categoria.upper()}** no {titulo_ctx}{data_txt}."
                            f"{cats_txt}"
                        )
                    }
                
                # ✅ CORREÇÃO (14/01/2026): Manter tipo original do relatório (não usar "resumo" genérico)
                tipo_relatorio_original = dados_json.get('tipo_relatorio', tipo_relatorio)
                if tipo_relatorio_original == 'resumo':
                    # Se o tipo original já era "resumo" (não deveria acontecer), usar tipo do relatório salvo
                    tipo_relatorio_original = relatorio_salvo.tipo_relatorio if relatorio_salvo else 'o_que_tem_hoje'
                
                # Formatar relatório filtrado por categoria
                # ✅ Ajuste: manter período do resumo, mas recalcular totais para o filtro
                resumo_original = dados_json.get('resumo', {}) or {}
                resumo_filtrado = dict(resumo_original) if isinstance(resumo_original, dict) else {}
                try:
                    if tipo_relatorio_original == 'processos_chegando':
                        total_filtrado = len(secoes_filtradas_por_categoria.get('processos_chegando') or [])
                        resumo_filtrado['total_chegando'] = total_filtrado
                    elif tipo_relatorio_original == 'fechamento_dia':
                        # ✅ CRÍTICO: Ao filtrar fechamento, o total deve refletir o filtro (e não o dia inteiro)
                        total_original = resumo_original.get('total_movimentacoes') if isinstance(resumo_original, dict) else None
                        # Preferir a lista achatada (se existir), senão somar listas das seções filtradas
                        if isinstance(secoes_filtradas_por_categoria.get('movimentacoes'), list):
                            total_filtrado = len(secoes_filtradas_por_categoria.get('movimentacoes') or [])
                        else:
                            total_filtrado = 0
                            for _k, _v in secoes_filtradas_por_categoria.items():
                                if isinstance(_v, list):
                                    total_filtrado += len(_v)
                        resumo_filtrado['total_movimentacoes_original'] = total_original
                        resumo_filtrado['total_movimentacoes'] = total_filtrado
                        # Recalcular contagens por seção do fechamento (quando existir)
                        mapa = {
                            'processos_chegaram': 'total_chegaram',
                            'processos_desembaracados': 'total_desembaracados',
                            'duimps_criadas': 'total_duimps_criadas',
                            'dis_registradas': 'total_dis_registradas',
                            'mudancas_status_ce': 'total_mudancas_status_ce',
                            'mudancas_status_di': 'total_mudancas_status_di',
                            'mudancas_status_duimp': 'total_mudancas_status_duimp',
                            'pendencias_resolvidas': 'total_pendencias_resolvidas',
                            'movimentacoes': 'total_movimentacoes_detalhadas',
                        }
                        for sec_key, resumo_key in mapa.items():
                            sec_val = secoes_filtradas_por_categoria.get(sec_key)
                            if isinstance(sec_val, list):
                                resumo_filtrado[resumo_key] = len(sec_val)
                except Exception:
                    # Não quebrar filtro por causa do resumo
                    resumo_filtrado = resumo_original if isinstance(resumo_original, dict) else {}

                dados_json_filtrado = {
                    'tipo_relatorio': tipo_relatorio_original,  # ✅ Manter tipo original (não "resumo")
                    'data': dados_json.get('data', ''),
                    # ✅ NOVO (19/01/2026): preservar resumo original (ex.: período/contagens)
                    # Isso permite que o formatador de "processos_chegando" mostre "esta semana" e total.
                    'resumo': resumo_filtrado,
                    'secoes': secoes_filtradas_por_categoria,
                    'filtrado': True,
                    'secoes_filtradas': secoes_filtradas_keys,  # ✅ Seções filtradas reais
                    'categoria_filtro': categoria.upper()  # ✅ Adicionar categoria_filtro para o formatador
                }
            else:
                # Buscar seção solicitada (comportamento original)
                # ✅ UX (28/01/2026): Se o relatório atual está filtrado (ex.: "filtre DBA")
                # e o usuário pede uma seção que não ficou no relatório filtrado (ex.: DIs em análise),
                # voltar automaticamente para o relatório-base não filtrado mais recente do mesmo tipo.
                if (
                    secao
                    and not report_id
                    and isinstance(dados_json, dict)
                    and dados_json.get('filtrado')
                    and secao not in (secoes or {})
                ):
                    try:
                        from services.context_service import buscar_contexto_sessao
                        import re
                        import json as _json
                        from services.report_service import buscar_relatorio_por_id as _buscar_por_id

                        tipo_alvo = relatorio_salvo.tipo_relatorio
                        contextos = buscar_contexto_sessao(
                            session_id=session_id,
                            tipo_contexto='ultimo_relatorio',
                            chave=None
                        ) or []

                        melhor_id = None
                        melhor_ts = None
                        for ctx in contextos:
                            dados_ctx = ctx.get('dados', {}) or {}
                            try:
                                texto_chat_ctx = (dados_ctx.get('texto_chat') or '')
                                if not texto_chat_ctx:
                                    continue
                                if (dados_ctx.get('tipo_relatorio') or '') != tipo_alvo:
                                    continue
                                m = re.search(r'\[REPORT_META:({.+?})\]', texto_chat_ctx, re.DOTALL)
                                if not m:
                                    continue
                                meta = _json.loads(m.group(1))
                                if meta.get('filtrado'):
                                    continue
                                rid = meta.get('id')
                                ts = meta.get('created_at')
                                if not rid:
                                    continue
                                if (melhor_ts is None) or (ts and ts > melhor_ts):
                                    melhor_id = rid
                                    melhor_ts = ts
                            except Exception:
                                continue

                        if melhor_id:
                            base = _buscar_por_id(session_id, melhor_id)
                            if base and base.meta_json:
                                dados_base = base.meta_json.get('dados_json_original') or base.meta_json.get('dados_json')
                                if isinstance(dados_base, dict) and isinstance(dados_base.get('secoes'), dict):
                                    # Atualizar "janela" de trabalho para a base não filtrada
                                    logger.info(
                                        f'✅ Seção ausente no relatório filtrado: usando relatório-base não filtrado '
                                        f'(id={melhor_id}, tipo={tipo_alvo}, secao={secao})'
                                    )
                                    relatorio_salvo = base
                                    dados_json = dados_base
                                    secoes = dados_json.get('secoes', {})
                    except Exception as _e_base_secao:
                        logger.debug(f'⚠️ Não foi possível voltar ao relatório-base para seção: {_e_base_secao}')

                if secao not in secoes:
                    secoes_disponiveis = list(secoes.keys())
                    return {
                        'sucesso': False,
                        'erro': 'SECAO_NAO_ENCONTRADA',
                        'resposta': f'❌ Seção "{secao}" não encontrada no relatório salvo.\n\n📋 Seções disponíveis: {", ".join(secoes_disponiveis) if secoes_disponiveis else "nenhuma"}'
                    }
                
                dados_secao = secoes[secao]

                # ✅ Aplicar filtros determinísticos na seção (quando fornecidos)
                try:
                    from services.report_filter_service import filtrar_secao_relatorio
                    dados_secao, filtros_aplicados = filtrar_secao_relatorio(
                        secao,
                        dados_secao,
                        canal=canal,
                        tipo_pendencia=tipo_pendencia,
                        tipo_mudanca=tipo_mudanca,
                        min_dias=min_dias,
                        status_contains=status_contains,
                        min_age_dias=min_age_dias,
                    )
                except Exception:
                    filtros_aplicados = {}
                
                # ✅ CORREÇÃO (14/01/2026): Manter tipo original do relatório (não usar "resumo" genérico)
                tipo_relatorio_original = dados_json.get('tipo_relatorio', tipo_relatorio)
                if tipo_relatorio_original == 'resumo':
                    # Se o tipo original já era "resumo" (não deveria acontecer), usar tipo do relatório salvo
                    tipo_relatorio_original = relatorio_salvo.tipo_relatorio if relatorio_salvo else 'o_que_tem_hoje'
                
                # Formatar seção usando o formatador
                dados_json_filtrado = {
                    'tipo_relatorio': tipo_relatorio_original,  # ✅ Manter tipo original (não "resumo")
                    'data': dados_json.get('data', ''),
                    # ✅ NOVO (19/01/2026): preservar resumo original (quando existir)
                    'resumo': dados_json.get('resumo', {}) or {},
                    'secoes': {secao: dados_secao},
                    'filtrado': True,
                    'secoes_filtradas': [secao]  # ✅ Seção filtrada real
                }
                if isinstance(filtros_aplicados, dict) and filtros_aplicados:
                    dados_json_filtrado['filtros'] = filtros_aplicados
            
            # Usar o formatador para formatar apenas a seção solicitada
            resposta_formatada = RelatorioFormatterService.formatar_relatorio_fallback_simples(
                dados_json_filtrado
            )
            
            if not resposta_formatada or resposta_formatada.strip() == '':
                # Se formatação retornou vazio, formatar manualmente
                if categoria:
                    resposta_formatada = f"📊 **RELATÓRIO FILTRADO - {categoria.upper()}**\n\n"
                    total_itens = sum(len(v) if isinstance(v, list) else 1 for v in secoes_filtradas_por_categoria.values())
                    resposta_formatada += f"Total: {total_itens} item(ns) encontrado(s)\n\n"
                else:
                    resposta_formatada = f"📊 **{secao.upper().replace('_', ' ')}**\n\n"
                    if isinstance(dados_secao, list):
                        resposta_formatada += f"Total: {len(dados_secao)} item(ns)\n\n"
                        if dados_secao:
                            resposta_formatada += "Dados da seção encontrados, mas formatação não disponível.\n"
                    else:
                        resposta_formatada += "Dados da seção encontrados, mas formatação não disponível.\n"
            
            if categoria:
                total_itens = sum(len(v) if isinstance(v, list) else 1 for v in secoes_filtradas_por_categoria.values())
                # ✅ CORREÇÃO: Usar tipo do relatório salvo original (não tipo_relatorio que pode estar None ou "resumo")
                tipo_para_log = relatorio_salvo.tipo_relatorio if relatorio_salvo else (dados_json.get('tipo_relatorio', tipo_relatorio) or 'o_que_tem_hoje')
                if tipo_para_log == 'resumo':
                    tipo_para_log = 'o_que_tem_hoje'  # ✅ Não usar "resumo" genérico no log
                logger.info(f'✅ Relatório filtrado por categoria {categoria.upper()} do relatório salvo (tipo: {tipo_para_log}): {total_itens} item(ns)')
                dados_retorno = secoes_filtradas_por_categoria
            else:
                # ✅ CORREÇÃO: Usar tipo do relatório salvo original (não tipo_relatorio que pode estar None ou "resumo")
                tipo_para_log = relatorio_salvo.tipo_relatorio if relatorio_salvo else (dados_json.get('tipo_relatorio', tipo_relatorio) or 'o_que_tem_hoje')
                if tipo_para_log == 'resumo':
                    tipo_para_log = 'o_que_tem_hoje'  # ✅ Não usar "resumo" genérico no log
                logger.info(f'✅ Seção "{secao}" buscada do relatório salvo (tipo: {tipo_para_log}): {len(dados_secao) if isinstance(dados_secao, list) else 1} item(ns)')
                dados_retorno = dados_secao
            
            # ✅ CRÍTICO (14/01/2026): Salvar relatório filtrado como novo relatório para que "envie esse relatorio" funcione
            # Isso garante que quando o usuário pedir "envie esse relatorio" após filtrar, o sistema use o relatório filtrado
            if (categoria or secao) and session_id:
                try:
                    from services.report_service import salvar_ultimo_relatorio, criar_relatorio_gerado
                    from datetime import datetime
                    import re
                    import json
                    
                    # Extrair ID do relatório original do texto formatado (se houver)
                    relatorio_id_original = None
                    match_meta = re.search(r'\[REPORT_META:({.+?})\]', resposta_formatada, re.DOTALL)
                    if match_meta:
                        try:
                            meta_json = json.loads(match_meta.group(1))
                            relatorio_id_original = meta_json.get('id')
                        except:
                            pass
                    
                    # ✅ CORREÇÃO (14/01/2026): Manter tipo original do relatório (não usar "resumo" genérico)
                    # Usar tipo do relatório salvo original, não o tipo_relatorio que pode estar None ou "resumo"
                    tipo_relatorio_original = relatorio_salvo.tipo_relatorio if relatorio_salvo else (tipo_relatorio or 'o_que_tem_hoje')
                    
                    # ✅ CORREÇÃO: Se for filtrado, manter tipo original + sufixo "_filtrado" se necessário
                    # Mas NUNCA usar "resumo" genérico
                    if tipo_relatorio_original == 'resumo':
                        # Se o tipo original já era "resumo" (não deveria acontecer, mas corrigir se acontecer)
                        tipo_relatorio_original = 'o_que_tem_hoje'  # Fallback seguro
                    
                    # ✅ CORREÇÃO: Usar secoes_filtradas reais (não inventar seção)
                    secoes_filtradas_reais = dados_json_filtrado.get('secoes_filtradas', [])
                    # ✅ CORREÇÃO: Se não tem secoes_filtradas mas tem categoria, usar primeira seção encontrada
                    if not secoes_filtradas_reais and categoria:
                        secoes_filtradas_reais = list(secoes_filtradas_por_categoria.keys()) if categoria else []
                    secao_real = secoes_filtradas_reais[0] if secoes_filtradas_reais else secao
                    
                    # Criar novo relatório filtrado
                    relatorio_filtrado = criar_relatorio_gerado(
                        tipo_relatorio=tipo_relatorio_original,  # ✅ Manter tipo original (não "resumo")
                        texto_chat=resposta_formatada,  # Já inclui [REPORT_META:...] com novo ID
                        categoria=categoria,
                        filtros={
                            'categoria_filtro': categoria.upper() if categoria else None,
                            'secao_filtro': secao_real,  # ✅ Usar seção real filtrada (não inventar)
                            'relatorio_original_id': relatorio_id_original,
                            'filtrado': True  # ✅ Marcar explicitamente como filtrado
                        },
                        meta_json={
                            'dados_json': dados_json_filtrado,
                            'dados_json_original': relatorio_salvo.meta_json.get('dados_json') if relatorio_salvo.meta_json else None,
                            'filtrado': True,  # ✅ Marcar no meta_json também
                            'secoes_filtradas': secoes_filtradas_reais  # ✅ Persistir seções filtradas reais
                        }
                    )
                    
                    # Salvar relatório filtrado (isso atualiza o active_report_id para o filtrado)
                    salvar_ultimo_relatorio(session_id, relatorio_filtrado)
                    logger.info(f'✅ Relatório filtrado salvo como novo relatório (tipo: {tipo_relatorio_original}, categoria: {categoria}, secoes_filtradas: {secoes_filtradas_reais}, secao_real: {secao_real})')
                except Exception as e:
                    logger.warning(f'⚠️ Erro ao salvar relatório filtrado: {e}', exc_info=True)
                    # Continuar mesmo se não conseguir salvar
            
            return {
                'sucesso': True,
                'resposta': resposta_formatada,
                'dados': {
                    'secao': secao,
                    'categoria': categoria,
                    'tipo_relatorio': tipo_relatorio,
                    'total_itens': sum(len(v) if isinstance(v, list) else 1 for v in secoes_filtradas_por_categoria.values()) if categoria else (len(dados_secao) if isinstance(dados_secao, list) else 1),
                    'dados_secao': dados_retorno
                }
            }
        except Exception as e:
            logger.error(f'Erro ao buscar seção do relatório salvo: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar seção do relatório: {str(e)}'
            }
    
    def _buscar_relatorio_por_id(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        ✅ NOVO (12/01/2026): Busca um relatório específico por ID.
        
        Permite que o usuário referencie um relatório específico usando seu ID
        (ex: "usar rel_20260112_145026" ou "filtre o rel_20260112_145026").
        Isso evita confusão quando há múltiplos relatórios na mesma sessão.
        """
        try:
            session_id = context.get('session_id') if context else None
            
            if not session_id:
                return {
                    'sucesso': False,
                    'erro': 'SESSION_ID_NAO_FORNECIDO',
                    'resposta': '❌ Não foi possível buscar o relatório: session_id não fornecido.'
                }
            
            relatorio_id = arguments.get('relatorio_id')
            
            if not relatorio_id:
                return {
                    'sucesso': False,
                    'erro': 'RELATORIO_ID_NAO_FORNECIDO',
                    'resposta': '❌ ID do relatório não fornecido. Formato esperado: "rel_YYYYMMDD_HHMMSS" (ex: "rel_20260112_145026").'
                }
            
            # Buscar relatório por ID
            from services.report_service import buscar_relatorio_por_id
            
            relatorio = buscar_relatorio_por_id(session_id, relatorio_id)
            
            if not relatorio:
                return {
                    'sucesso': False,
                    'erro': 'RELATORIO_NAO_ENCONTRADO',
                    'resposta': f'❌ Relatório com ID "{relatorio_id}" não encontrado. Verifique se o ID está correto ou se o relatório ainda existe na sessão.'
                }
            
            # Extrair JSON inline do texto
            import re
            import json
            match_json = re.search(r'\[REPORT_META:({.+?})\]', relatorio.texto_chat, re.DOTALL)
            
            resposta = f"✅ **Relatório encontrado por ID:** `{relatorio_id}`\n\n"
            resposta += f"- Tipo: {relatorio.tipo_relatorio}\n"
            resposta += f"- Categoria: {relatorio.categoria or 'N/A'}\n"
            resposta += f"- Criado em: {relatorio.criado_em or 'N/A'}\n\n"
            
            if match_json:
                try:
                    meta_json = json.loads(match_json.group(1))
                    resposta += "📊 **Metadados (JSON Inline):**\n"
                    resposta += f"- Data: {meta_json.get('data', 'N/A')}\n"
                    if meta_json.get('created_at'):
                        resposta += f"- Criado em: {meta_json.get('created_at')}\n"
                    if meta_json.get('ttl_min'):
                        resposta += f"- TTL: {meta_json.get('ttl_min')} minutos\n"
                    if meta_json.get('counts'):
                        counts = meta_json.get('counts', {})
                        resposta += f"- Contagens: {', '.join([f'{k}: {v}' for k, v in counts.items() if v > 0])}\n"
                    if meta_json.get('secoes'):
                        resposta += f"- Seções: {', '.join(meta_json.get('secoes', []))}\n"
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao parsear JSON inline: {e}")
            
            resposta += f"\n💡 Este relatório está disponível para operações como filtrar, melhorar ou enviar por email."
            
            logger.info(f'✅ Relatório encontrado por ID: {relatorio_id} (tipo: {relatorio.tipo_relatorio})')
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': {
                    'relatorio_id': relatorio_id,
                    'tipo_relatorio': relatorio.tipo_relatorio,
                    'categoria': relatorio.categoria,
                    'criado_em': relatorio.criado_em,
                    'relatorio': relatorio  # Relatório completo para uso posterior
                }
            }
        except Exception as e:
            logger.error(f'Erro ao buscar relatório por ID: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao buscar relatório por ID: {str(e)}'
            }

    def _filtrar_relatorio_fuzzy(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        🧠📊 Aplica filtro/agrupamento "fuzzy" no relatório salvo/visível (sem regex no core).
        - Interpreta a instrução em plano estruturado
        - Reusa `buscar_secao_relatorio_salvo` para filtros determinísticos e persistência do report_id (email)
        """
        try:
            session_id = (context or {}).get('session_id')
            if not session_id:
                return {
                    'sucesso': False,
                    'erro': 'SESSION_ID_NAO_FORNECIDO',
                    'resposta': '❌ Não foi possível filtrar o relatório: session_id não fornecido.'
                }

            instrucao = (arguments.get('instrucao') or '').strip()
            report_id = (arguments.get('report_id') or '').strip() or None
            if not instrucao:
                return {
                    'sucesso': False,
                    'erro': 'INSTRUCAO_OBRIGATORIA',
                    'resposta': '❌ Informe a instrução (ex: "filtra DMD", "só canal verde", "agrupe por canal").'
                }

            # Best-effort: usar REPORT_META do relatório ativo para ajudar o planner.
            report_meta: Dict[str, Any] = {}
            relatorio_base_tipo: Optional[str] = None
            relatorio_base_id: Optional[str] = None
            try:
                from services import report_service
                relatorio = None
                if report_id:
                    relatorio = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=report_id)
                    relatorio_base_id = report_id
                else:
                    # ✅ Preferir o último relatório visível (fonte da verdade para follow-ups)
                    last_visible = report_service.obter_last_visible_report_id(session_id=session_id, dominio='processos')
                    last_visible_id = (last_visible or {}).get('id') if isinstance(last_visible, dict) else None
                    if last_visible_id:
                        relatorio = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=last_visible_id)
                        relatorio_base_id = last_visible_id
                    else:
                        # Fallback: active_report_id
                        active_id = report_service.obter_active_report_id(session_id=session_id, dominio='processos')
                        if active_id:
                            relatorio = report_service.buscar_relatorio_por_id(session_id=session_id, relatorio_id=active_id)
                            relatorio_base_id = active_id
                if relatorio and getattr(relatorio, 'texto_chat', None):
                    relatorio_base_tipo = getattr(relatorio, 'tipo_relatorio', None)
                    import re as _re
                    import json as _json
                    m = _re.search(r'\[REPORT_META:({.+?})\]', relatorio.texto_chat, _re.DOTALL)
                    if m:
                        report_meta = _json.loads(m.group(1))
            except Exception:
                report_meta = {}

            from services.report_fuzzy_planner_service import planejar_filtro
            plano = planejar_filtro(instrucao=instrucao, report_meta=report_meta)
            acao = (plano.get('acao') or '').strip().lower()

            if acao in ('', 'erro'):
                return {
                    'sucesso': False,
                    'erro': 'PLANO_INVALIDO',
                    'resposta': '❌ Não consegui interpretar seu filtro. Tente: "filtra DMD", "só canal verde", "só atrasos > 7 dias", "pendências de frete", "agrupe por canal".',
                    'dados': {'plano': plano}
                }

            # ✅ UX "humana": se o relatório base é FECHAMENTO e o usuário não especificou o tipo,
            # perguntar em qual relatório aplicar o filtro (evita surpresa).
            try:
                tipo_meta = (report_meta.get('tipo') if isinstance(report_meta, dict) else None) or relatorio_base_tipo
                tipo_pedido = plano.get('tipo_relatorio')
                if (
                    not report_id
                    and not tipo_pedido
                    and isinstance(tipo_meta, str)
                    and tipo_meta.strip().lower() == 'fechamento_dia'
                    and acao in ('filtrar_categoria', 'buscar_secao', 'agrupar_por_canal')
                ):
                    rid = relatorio_base_id or '(desconhecido)'
                    return {
                        'sucesso': True,
                        'resposta': (
                            "Em qual relatório você quer aplicar esse filtro?\n\n"
                            f"(1) **Fechamento do dia** (relatório atual: `{rid}`)\n"
                            "(2) **Dashboard** — \"o que temos pra hoje\" (posso gerar agora e aplicar o filtro)\n\n"
                            "Responda com **1** ou **2** (ou diga: \"no fechamento\" / \"no dashboard\")."
                        ),
                        'dados': {
                            'requer_escolha': True,
                            'opcoes': [
                                {'id': rid, 'tipo_relatorio': 'fechamento_dia', 'label': 'Fechamento do dia'},
                                {'id': None, 'tipo_relatorio': 'o_que_tem_hoje', 'label': 'Dashboard (gerar)'},
                            ],
                            'plano': plano,
                        }
                    }
            except Exception:
                pass

            # Ação especial: agrupar por canal (gera relatório derivado e salva para "envie esse relatório")
            if acao == 'agrupar_por_canal':
                secao = (plano.get('secao') or '').strip() or None
                if not secao and isinstance(report_meta, dict):
                    secoes_meta = report_meta.get('secoes') if isinstance(report_meta.get('secoes'), list) else []
                    if 'dis_analise' in secoes_meta:
                        secao = 'dis_analise'
                    elif 'duimps_analise' in secoes_meta:
                        secao = 'duimps_analise'
                secao = secao or 'dis_analise'

                from services.report_service import (
                    buscar_ultimo_relatorio,
                    buscar_relatorio_por_id as _buscar_por_id,
                    criar_relatorio_gerado,
                    salvar_ultimo_relatorio,
                )
                relatorio_base = _buscar_por_id(session_id, report_id) if report_id else None
                if not relatorio_base:
                    relatorio_base = buscar_ultimo_relatorio(session_id, tipo_relatorio=None, usar_active_report_id=True)
                if not relatorio_base or not relatorio_base.meta_json:
                    return {
                        'sucesso': False,
                        'erro': 'RELATORIO_NAO_ENCONTRADO',
                        'resposta': '❌ Não encontrei um relatório salvo para agrupar. Gere um relatório primeiro e tente novamente.'
                    }
                dados_base = relatorio_base.meta_json.get('dados_json_original') or relatorio_base.meta_json.get('dados_json') or {}
                secoes_base = (dados_base.get('secoes') or {}) if isinstance(dados_base, dict) else {}
                itens = secoes_base.get(secao)

                from services.report_grouping_service import agrupar_lista_por_chave, formatar_grupos_simples
                grupos, counts = agrupar_lista_por_chave(itens, chave='canal_di')
                if not grupos:
                    grupos, counts = agrupar_lista_por_chave(itens, chave='canal')

                texto = formatar_grupos_simples(f"Agrupado por canal — {secao.replace('_',' ')}", grupos, mostrar_max_por_grupo=30)

                dados_json_derivado = {
                    'tipo_relatorio': (dados_base.get('tipo_relatorio') if isinstance(dados_base, dict) else None) or getattr(relatorio_base, 'tipo_relatorio', 'o_que_tem_hoje'),
                    'data': (dados_base.get('data') if isinstance(dados_base, dict) else None) or '',
                    'resumo': {
                        'counts_por_canal': counts,
                        'secao': secao,
                    },
                    'secoes': {secao: itens},
                    'filtrado': True,
                    'secoes_filtradas': [secao],
                    'filtros': {'agrupar_por': 'canal'},
                }
                texto = texto + RelatorioFormatterService._gerar_meta_json_inline(dados_json_derivado.get('tipo_relatorio') or 'o_que_tem_hoje', dados_json_derivado)

                relatorio_novo = criar_relatorio_gerado(
                    tipo_relatorio=dados_json_derivado.get('tipo_relatorio') or 'o_que_tem_hoje',
                    texto_chat=texto,
                    categoria=None,
                    filtros={'agrupar_por': 'canal', 'secao': secao},
                    meta_json={'dados_json': dados_json_derivado, 'dados_json_original': dados_base},
                )
                salvar_ultimo_relatorio(session_id, relatorio_novo)

                return {
                    'sucesso': True,
                    'resposta': texto,
                    'dados': {'plano': plano, 'counts': counts, 'secao': secao},
                }

            # Reuso: traduzir para buscar_secao_relatorio_salvo (filtra/persiste report_id)
            args = {
                'secao': plano.get('secao'),
                'categoria': plano.get('categoria'),
                'tipo_relatorio': plano.get('tipo_relatorio'),
                'report_id': report_id,
                'canal': plano.get('canal'),
                'tipo_pendencia': plano.get('tipo_pendencia'),
                'tipo_mudanca': plano.get('tipo_mudanca'),
                'min_dias': plano.get('min_dias'),
                'status_contains': plano.get('status_contains'),
                'min_age_dias': plano.get('min_age_dias'),
            }
            args = {k: v for k, v in args.items() if v is not None and v != ''}

            resultado = self._buscar_secao_relatorio_salvo(args, context=context)
            if isinstance(resultado, dict):
                dados = resultado.get('dados')
                if isinstance(dados, dict):
                    dados['plano'] = plano
            return resultado

        except Exception as e:
            logger.error(f'Erro ao filtrar relatório (fuzzy): {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao filtrar relatório: {str(e)}'
            }
    
    def _obter_ajuda(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retorna uma mensagem de ajuda com todas as funcionalidades e palavras-chave disponíveis.
        """
        resposta = """# 📚 GUIA DE AJUDA - CHAT IA ASSISTENTE DUIMP

Olá! Eu sou seu assistente inteligente para processos de importação e DUIMP. Aqui está tudo que você pode fazer:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🎯 **PALAVRAS-CHAVE PRINCIPAIS**

### 📋 **CONSULTAS DE PROCESSOS**
- **`detalhe [PROCESSO]`** ou **`detalhes [PROCESSO]`** - Mostra informações completas de um processo específico
  - Exemplo: `detalhe ALH.0145/25` ou `detalhes do processo VDM.0003/25`
  
- **`situacao [CATEGORIA]`** ou **`situação [CATEGORIA]`** - Lista processos de uma categoria por situação
  - Exemplo: `quais ALH estão desembaraçados?` ou `situação VDM registrados`
  
- **`[CATEGORIA]`** - Lista processos de uma categoria específica
  - Exemplo: `ALH`, `VDM`, `MSS`, `BND`, `DMD`, `GYM`, `SLL`, `MV5`

### 📄 **EXTRATOS E DOCUMENTOS**
- **`extrato DI [PROCESSO]`** ou **`extrato da DI [PROCESSO]`** - Obtém extrato PDF da DI
  - Exemplo: `extrato DI ALH.0145/25` ou `pdf da DI do processo VDM.0003/25`
  
- **`extrato CE [PROCESSO]`** ou **`extrato do CE [PROCESSO]`** - Obtém extrato do CE
  - Exemplo: `extrato CE ALH.0145/25` ou `extrato do CE 132505378018702`
  
- **`extrato DUIMP [PROCESSO]`** ou **`extrato da DUIMP [PROCESSO]`** - Obtém extrato PDF da DUIMP
  - Exemplo: `extrato DUIMP ALH.0145/25` ou `pdf da DUIMP 25BR00000276148`

### 📝 **CRIAÇÃO DE DUIMP**
- **`registrar DUIMP [PROCESSO]`** ou **`criar DUIMP [PROCESSO]`** - Cria uma nova DUIMP para um processo
  - Exemplo: `registrar DUIMP MV5.0013/25` ou `criar DUIMP do processo BND.0097/25`
  - ⚠️ O sistema mostrará um resumo antes de criar - você precisa confirmar com "sim" ou "pode prosseguir"

### 📅 **DASHBOARD DO DIA**
- **`o que temos pra hoje?`** ou **`o que temos para hoje?`** - Mostra resumo consolidado do dia
  - Exemplo: `o que temos pra hoje?`, `dashboard de hoje`, `resumo do dia`
  - Filtros opcionais:
    - `o que temos pra hoje ALH?` - Filtra por categoria
    - `o que temos pra hoje aéreo?` - Filtra por modal (aéreo/marítimo)
    - `o que temos pra hoje com pendências?` - Mostra apenas pendências

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 **OUTRAS FUNCIONALIDADES**

### 📊 **Consultas por Situação**
- `quais [CATEGORIA] estão desembaraçados?`
- `quais [CATEGORIA] estão registrados?`
- `quais [CATEGORIA] estão entregues?`
- `quais [CATEGORIA] estão armazenados?`
- `quais [CATEGORIA] estão bloqueados?`

### ⚠️ **Consultas de Pendências**
- `quais [CATEGORIA] têm pendências?`
- `quais [CATEGORIA] têm pendência de frete?`
- `quais [CATEGORIA] têm pendência de AFRMM?`
- `quais processos têm pendências?` (sem categoria)

### 📦 **Consultas de CE/CCT**
- `status do CE [NÚMERO]` ou `status CE [PROCESSO]`
- `extrato do CE [PROCESSO/NÚMERO]`
- `extrato do CCT [PROCESSO/NÚMERO]`

### 📋 **Consultas de DI/DUIMP**
- `tem DUIMP para [PROCESSO]?` - Verifica se existe DUIMP
- `quais processos têm DUIMP?` - Lista processos com DUIMP
- `status da DI [PROCESSO]`
- `extrato da DI [PROCESSO]`

### 🚢 **Consultas de ETA e Navio**
- `quais [CATEGORIA] chegam hoje?`
- `quais [CATEGORIA] chegam amanhã?`
- `quais [CATEGORIA] chegam esta semana?`
- `processos do navio [NOME]`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 💡 **DICAS DE USO**

1. **Formato de Processo**: Use o formato `CATEGORIA.NNNN/AA` (ex: `ALH.0145/25`, `MV5.0013/25`)

2. **Confirmações**: Quando criar uma DUIMP, o sistema mostrará um resumo. Responda:
   - `sim`, `pode prosseguir`, `confirmar`, `criar` para confirmar
   - `não`, `cancelar` para cancelar

3. **Contexto**: O sistema mantém contexto da conversa. Você pode perguntar:
   - `quais estão bloqueados?` (mantém a categoria da conversa anterior)

4. **Linguagem Natural**: Você pode usar linguagem natural:
   - `me mostre os processos ALH que estão desembaraçados`
   - `como está o processo VDM.0003/25?`
   - `preciso criar uma DUIMP para o MV5.0013/25`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🆘 **PRECISA DE AJUDA?**

Digite **`ajuda`** ou **`help`** a qualquer momento para ver este guia novamente!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        return {
            'sucesso': True,
            'resposta': resposta
        }
    
    def _gerar_relatorio_importacoes_fob(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Gera relatório de importações normalizado por FOB.
        
        Args:
            arguments: Dict com mes, ano, categoria (opcionais)
            context: Contexto adicional (opcional)
        
        Returns:
            Dict com sucesso, resposta formatada, dados
        """
        try:
            from services.relatorio_fob_service import gerar_relatorio_importacoes_fob, formatar_relatorio_fob
            from datetime import datetime
            
            # Extrair parâmetros
            mes = arguments.get('mes')
            ano = arguments.get('ano')
            categoria = arguments.get('categoria')
            
            # Se não fornecido, usar mês/ano atual.
            # ✅ MELHORIA (19/01/2026): Se usuário informar apenas o ano (ex: "em 2025"), tratar como ANO INTEIRO (mes=None).
            agora = datetime.now()
            if not ano:
                ano = agora.year
            if mes is None:
                # ano informado sem mês => ano inteiro; se nem ano veio, cai no padrão mês atual.
                if arguments.get('ano') is None:
                    mes = agora.month
            
            logger.info(f"📊 Gerando relatório FOB: mês={mes}, ano={ano}, categoria={categoria}")
            
            # Gerar relatório
            dados = gerar_relatorio_importacoes_fob(mes, ano, categoria)
            
            if not dados.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': dados.get('erro', 'Erro desconhecido'),
                    'resposta': f"❌ Erro ao gerar relatório: {dados.get('mensagem', 'erro desconhecido')}"
                }
            
            # Formatar resposta
            resposta = formatar_relatorio_fob(dados)
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': dados
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao gerar relatório FOB: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar relatório FOB: {str(e)}'
            }
    
    def _gerar_relatorio_averbacoes(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Gera relatório de averbações de seguro em formato Excel.
        
        Args:
            arguments: Dict com mes, ano, categoria (opcionais)
            context: Contexto adicional (opcional)
        
        Returns:
            Dict com sucesso, resposta formatada, dados
        """
        try:
            from services.relatorio_averbacoes_service import RelatorioAverbacoesService
            from datetime import datetime
            
            # Extrair parâmetros
            mes = arguments.get('mes')
            ano = arguments.get('ano')
            categoria = arguments.get('categoria')
            
            # Se não fornecido, usar mês/ano atual
            agora = datetime.now()
            if not mes:
                mes = str(agora.month)
            if not ano:
                ano = agora.year
            
            logger.info(f"📊 Gerando relatório de averbações: mês={mes}, ano={ano}, categoria={categoria}")
            
            # Gerar relatório
            service = RelatorioAverbacoesService()
            resultado = service.gerar_relatorio_averbacoes(mes, ano, categoria)
            
            if not resultado.get('sucesso'):
                erro = resultado.get('erro', 'ERRO_DESCONHECIDO')
                mensagem = resultado.get('mensagem', 'Erro desconhecido')
                
                if erro == 'NENHUM_PROCESSO':
                    return {
                        'sucesso': False,
                        'erro': erro,
                        'resposta': f"✅ {mensagem}"
                    }
                else:
                    return {
                        'sucesso': False,
                        'erro': erro,
                        'resposta': f"❌ Erro ao gerar relatório: {mensagem}"
                    }
            
            # Formatar resposta
            caminho_arquivo = resultado.get('caminho_arquivo', '')
            total_processos = resultado.get('total_processos', 0)
            total_erros = resultado.get('total_erros', 0)
            erros = resultado.get('erros', [])
            
            resposta = f"✅ **Relatório de Averbações gerado com sucesso!**\n\n"
            resposta += f"📁 **Arquivo:** `{caminho_arquivo}`\n"
            resposta += f"📊 **Total de processos:** {total_processos}\n"
            
            if total_erros > 0:
                resposta += f"⚠️ **Erros:** {total_erros} processo(s) com erro\n"
                if erros:
                    resposta += "\n**Detalhes dos erros:**\n"
                    for erro_item in erros[:5]:  # Mostrar apenas os primeiros 5
                        resposta += f"- {erro_item}\n"
                    if len(erros) > 5:
                        resposta += f"- ... e mais {len(erros) - 5} erro(s)\n"
            
            resposta += f"\n💡 O arquivo Excel está disponível para download em: `{caminho_arquivo}`"
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao gerar relatório de averbações: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar relatório de averbações: {str(e)}'
            }
    
    def _consultar_despesas_processo(self, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Consulta despesas vinculadas a um processo.
        
        ✅ NOVO (08/01/2026): Permite visualizar despesas conciliadas e pendentes.
        """
        processo_ref = arguments.get('processo_referencia', '').strip()
        incluir_pendentes = arguments.get('incluir_pendentes', True)
        incluir_rastreamento = arguments.get('incluir_rastreamento', False)
        
        if not processo_ref:
            return {
                'sucesso': False,
                'erro': 'processo_referencia é obrigatório',
                'resposta': '❌ Referência de processo é obrigatória.'
            }
        
        # Expandir processo se necessário
        processo_completo = extract_processo_referencia(processo_ref)
        if not processo_completo:
            processo_completo = processo_ref
        
        try:
            from services.banco_concilacao_service import get_banco_concilacao_service
            
            conciliacao_service = get_banco_concilacao_service()
            resultado = conciliacao_service.consultar_despesas_processo(
                processo_referencia=processo_completo,
                incluir_pendentes=incluir_pendentes,
                incluir_rastreamento=incluir_rastreamento
            )
            
            if not resultado.get('sucesso'):
                return {
                    'sucesso': False,
                    'erro': resultado.get('erro', 'ERRO_DESCONHECIDO'),
                    'resposta': resultado.get('mensagem', f'❌ Erro ao consultar despesas do processo {processo_completo}')
                }
            
            # Formatar resposta
            resposta = self._formatar_despesas_processo(resultado)
            
            return {
                'sucesso': True,
                'resposta': resposta,
                'dados': resultado
            }
            
        except Exception as e:
            logger.error(f'❌ Erro ao consultar despesas do processo {processo_completo}: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao consultar despesas: {str(e)}'
            }
    
    def _formatar_despesas_processo(self, dados: Dict[str, Any]) -> str:
        """
        Formata despesas do processo para exibição no chat.
        
        ✅ NOVO (08/01/2026): Formatação contextual e clara.
        """
        processo_ref = dados.get('processo_referencia', '')
        despesas_conciliadas = dados.get('despesas_conciliadas', [])
        despesas_pendentes = dados.get('despesas_pendentes', [])
        total_conciliado = dados.get('total_conciliado', 0.0)
        total_pendente = dados.get('total_pendente', 0.0)
        percentual_conciliado = dados.get('percentual_conciliado', 0.0)
        
        resposta = f"💰 **DESPESAS - {processo_ref}**\n"
        resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Despesas conciliadas
        if despesas_conciliadas:
            resposta += f"✅ **CONCILIADAS** ({len(despesas_conciliadas)} despesa(s)):\n\n"
            
            for idx, despesa in enumerate(despesas_conciliadas, 1):
                valor_formatado = f"R$ {despesa.get('valor', 0):,.2f}"
                tipo_despesa = despesa.get('tipo_despesa', 'N/A')
                data_pagamento = despesa.get('data_pagamento', '')
                banco = despesa.get('banco', '')
                agencia = despesa.get('agencia', '')
                conta = despesa.get('conta', '')
                descricao = despesa.get('descricao_lancamento', '')
                contrapartida = despesa.get('contrapartida', {})
                
                resposta += f"  {idx}. **{tipo_despesa}** - {valor_formatado}\n"
                
                if data_pagamento:
                    resposta += f"     📅 Data: {data_pagamento}\n"
                
                if banco:
                    banco_info = f"🏦 {banco}"
                    if agencia:
                        banco_info += f" - Ag. {agencia}"
                    if conta:
                        banco_info += f" C/C {conta}"
                    resposta += f"     {banco_info}\n"
                
                if descricao:
                    resposta += f"     📝 {descricao}\n"
                
                if contrapartida.get('nome'):
                    origem = contrapartida.get('nome', '')
                    if contrapartida.get('cpf_cnpj'):
                        origem += f" ({contrapartida.get('cpf_cnpj')})"
                    resposta += f"     👤 Origem: {origem}\n"
                
                resposta += "\n"
        else:
            resposta += "ℹ️ Nenhuma despesa conciliada ainda.\n\n"
        
        # Despesas pendentes
        if despesas_pendentes:
            resposta += f"⚠️ **PENDENTES** ({len(despesas_pendentes)} despesa(s)):\n\n"
            
            for idx, pendente in enumerate(despesas_pendentes, 1):
                tipo_despesa = pendente.get('tipo_despesa', 'N/A')
                valor_estimado = pendente.get('valor_estimado', 0)
                sugestao_periodo = pendente.get('sugestao_periodo', '')
                
                resposta += f"  {idx}. **{tipo_despesa}** - R$ {valor_estimado:,.2f} (estimado)\n"
                
                if sugestao_periodo:
                    resposta += f"     💡 Sugestão: Buscar lançamento no período {sugestao_periodo}\n"
                
                resposta += "\n"
        
        # Resumo
        resposta += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        resposta += f"📊 **RESUMO:**\n"
        resposta += f"  • Total conciliado: R$ {total_conciliado:,.2f}\n"
        
        if total_pendente > 0:
            resposta += f"  • Total pendente: R$ {total_pendente:,.2f}\n"
        
        resposta += f"  • Percentual conciliado: {percentual_conciliado:.1f}%\n"
        
        return resposta
    