"""
Definições de Tools (Funções) para Function Calling da IA
"""
from typing import List, Dict, Any, Optional
import logging

def _shorten_description(description: str, max_length: int = 200) -> str:
    """
    Encurta description mantendo informações essenciais.
    
    Args:
        description: Description completa
        max_length: Tamanho máximo desejado (padrão: 200 caracteres)
    
    Returns:
        Description encurtada
    """
    if len(description) <= max_length:
        return description
    
    # ✅ CRÍTICO: Para verificar_duimp_registrada, preservar exemplos explícitos e informação sobre "registrada"
    if 'verificar_duimp_registrada' in description or 'tem DUIMP registrada para' in description or 'tem duimp para' in description:
        # Manter exemplos críticos e informação sobre "registrada" não ser situação
        import re
        # Extrair informação crítica sobre "registrada"
        info_registrada = ''
        if 'registrada' in description.lower() and 'não é uma situação' in description.lower():
            info_match = re.search(r'registrada.*?não é uma situação.*?(?:\n|⚠️|$)', description, re.DOTALL | re.IGNORECASE)
            if info_match:
                info_registrada = re.sub(r'\s+', ' ', info_match.group(0).strip())[:80]
        
        # Extrair exemplos importantes
        exemplos_match = re.search(r'Exemplos?[:\s](.*?)(?:\n\n|⚠️|$)', description, re.DOTALL | re.IGNORECASE)
        exemplos_texto = exemplos_match.group(1) if exemplos_match else ''
        
        # Remover emojis e símbolos de prioridade no início (⚠️, ✅, etc)
        desc_clean = description.lstrip('⚠️✅❌💡🔍📋💰✈️📦🚨🚫🔄📄🌍📍🎯💾')
        
        # Remover exemplos longos, mas preservar os críticos
        desc_clean = re.sub(r'[Ee]xemplos?[:\s].*$', '', desc_clean, flags=re.DOTALL)
        
        # Remover instruções muito detalhadas (mas manter as críticas sobre "registrada")
        desc_clean = re.sub(r'⚠️\s*IMPORTANTE[:\s].*?(?=\n\n|\Z)', '', desc_clean, flags=re.DOTALL)
        # NÃO remover se contém informação sobre "registrada"
        if 'registrada' not in desc_clean.lower() or 'não é uma situação' not in desc_clean.lower():
            desc_clean = re.sub(r'⚠️\s*CRÍTICO[:\s].*?(?=\n\n|\Z)', '', desc_clean, flags=re.DOTALL)
        
        # Remover quebras de linha múltiplas
        desc_clean = re.sub(r'\n{2,}', ' ', desc_clean)
        desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
        
        # Adicionar informação crítica sobre "registrada" se não estiver presente
        if info_registrada and 'registrada' not in desc_clean.lower():
            desc_clean = f"{desc_clean}. {info_registrada}"
        
        # Adicionar exemplos críticos de volta (limitados)
        if exemplos_texto:
            exemplos_limpos = re.sub(r'\s+', ' ', exemplos_texto.strip())[:100]  # Limitar exemplos a 100 chars
            desc_clean = f"{desc_clean}. Exemplos: {exemplos_limpos}"
        
        # Se ainda estiver muito longo, truncar e adicionar "..."
        if len(desc_clean) > max_length:
            # Tentar cortar em ponto final ou vírgula próximo ao limite
            last_period = desc_clean.rfind('.', 0, max_length - 10)
            last_comma = desc_clean.rfind(',', 0, max_length - 10)
            cut_point = max(last_period, last_comma)
            
            if cut_point > max_length * 0.7:  # Se encontrou ponto próximo, usar
                desc_clean = desc_clean[:cut_point + 1]
            else:
                desc_clean = desc_clean[:max_length - 3] + '...'
        
        return desc_clean
    
    # Para outras tools, usar lógica padrão
    # Remover emojis e símbolos de prioridade no início (⚠️, ✅, etc)
    desc_clean = description.lstrip('⚠️✅❌💡🔍📋💰✈️📦🚨🚫🔄📄🌍📍🎯💾')
    
    # Remover exemplos longos (tudo após "Exemplos:" ou "Exemplo:")
    import re
    desc_clean = re.sub(r'[Ee]xemplos?[:\s].*$', '', desc_clean, flags=re.DOTALL)
    
    # Remover instruções muito detalhadas
    desc_clean = re.sub(r'⚠️\s*IMPORTANTE[:\s].*?(?=\n\n|\Z)', '', desc_clean, flags=re.DOTALL)
    desc_clean = re.sub(r'⚠️\s*CRÍTICO[:\s].*?(?=\n\n|\Z)', '', desc_clean, flags=re.DOTALL)
    
    # Remover quebras de linha múltiplas
    desc_clean = re.sub(r'\n{2,}', ' ', desc_clean)
    desc_clean = re.sub(r'\s+', ' ', desc_clean).strip()
    
    # Se ainda estiver muito longo, truncar e adicionar "..."
    if len(desc_clean) > max_length:
        # Tentar cortar em ponto final ou vírgula próximo ao limite
        last_period = desc_clean.rfind('.', 0, max_length - 10)
        last_comma = desc_clean.rfind(',', 0, max_length - 10)
        cut_point = max(last_period, last_comma)
        
        if cut_point > max_length * 0.7:  # Se encontrou ponto próximo, usar
            desc_clean = desc_clean[:cut_point + 1]
        else:
            desc_clean = desc_clean[:max_length - 3] + '...'
    
    return desc_clean

def get_available_tools(compact: bool = True, whitelist: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Retorna lista de funções disponíveis para a IA usar via function calling.
    
    Cada função define:
    - name: Nome da função
    - description: Descrição do que a função faz (encurtada se compact=True)
    - parameters: Schema JSON Schema dos parâmetros
    
    Args:
        compact: Se True, encurta descriptions para reduzir tokens (padrão: True)
        whitelist: Lista de nomes de tools permitidas (None = todas permitidas)
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "criar_duimp",
                "description": "🚨🚨🚨 PRIORIDADE MÁXIMA - CRIAR DUIMP: Cria uma DUIMP para um processo no Portal Único Siscomex. Use QUANDO O USUÁRIO PEDIR EXPLICITAMENTE para 'registrar', 'criar', 'gerar', 'fazer', 'montar' uma DUIMP. ⚠️⚠️⚠️ CRÍTICO: SEMPRE chame esta função diretamente quando o usuário pedir para criar/registrar/montar DUIMP. NÃO faça perguntas ao usuário sobre dados - a função busca automaticamente os dados do processo (CE/CCT, valores, etc.) e cria a DUIMP. Se faltarem dados, a função retornará um erro específico que você pode informar ao usuário. Exemplos OBRIGATÓRIOS: 'registre a duimp do MSS.0018/25' → criar_duimp(processo_referencia='MSS.0018/25'), 'crie duimp para VDM.0003/25' → criar_duimp(processo_referencia='VDM.0003/25'), 'montar duimp alh.0166/25' → criar_duimp(processo_referencia='ALH.0166/25'). ⚠️ NÃO use verificar_duimp_registrada quando o usuário pedir para REGISTRAR - use criar_duimp diretamente. ⚠️ NÃO faça perguntas sobre modal, incoterm, itens, etc. - chame a função diretamente e deixe ela buscar os dados automaticamente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: MSS.0018/25, VDM.0003/25). Pode aceitar variações como MSS.0018 ou vdm.003 que serão expandidas automaticamente."
                        },
                        "ambiente": {
                            "type": "string",
                            "enum": ["validacao", "producao"],
                            "description": "Ambiente onde criar a DUIMP. Padrão: validacao. Use 'producao' apenas se o usuário especificar explicitamente.",
                            "default": "validacao"
                        }
                    },
                    "required": ["processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_snapshot_processo",
                "description": "Gera um snapshot (resumo completo) de um processo a partir do banco novo mAIke_assistente: documentos (CE/DI/DUIMP/CCT), valores (FOB/VMLD/FRETE/SEGURO), impostos e despesas conciliadas. Se faltar dado, faz auto-heal seletivo (busca em fontes legadas e grava no banco novo).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: ALH.0001/25)."
                        },
                        "auto_heal": {
                            "type": "boolean",
                            "description": "Se true, tenta preencher o banco novo quando faltar informação (default: true).",
                            "default": True
                        }
                    },
                    "required": ["processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "sincronizar_processos_ativos_maike",
                "description": "Sincroniza processos ativos do Kanban (cache SQLite `processos_kanban`) para o banco novo mAIke_assistente (fonte da verdade), fazendo upsert de PROCESSO_IMPORTACAO e (opcionalmente) materializando documentos (CE/DI/DUIMP) e impostos/valores básicos da DI.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos do Kanban para sincronizar (default: 50).",
                            "default": 50
                        },
                        "incluir_documentos": {
                            "type": "boolean",
                            "description": "Se true, tenta materializar/atualizar DOCUMENTO_ADUANEIRO para CE/DI/DUIMP (default: true).",
                            "default": True
                        },
                        "incluir_valores_impostos": {
                            "type": "boolean",
                            "description": "Se true, tenta gravar valores (VMLE/VMLD/FRETE/SEGURO quando disponíveis) e impostos de DI em VALOR_MERCADORIA/IMPOSTO_IMPORTACAO (default: true).",
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_status_processo",
                "description": "Consulta status e informações detalhadas de UM processo específico (formato CATEGORIA.NNNN/AA, ex: VDM.0003/25). Use SEMPRE quando o usuário mencionar um NÚMERO DE PROCESSO ESPECÍFICO. NÃO use listar_processos_por_categoria quando houver número específico. Retorna: CEs, CCTs, DI, DUIMP, bloqueios, pendências, documentos enviados na DUIMP. ✅ NOVO: Agora também inclui despesas conciliadas automaticamente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: MSS.0018/25, VDM.0003/25). Pode aceitar variações como MSS.0018 ou vdm.003."
                        }
                    },
                    "required": ["processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_despesas_processo",
                "description": "🚨🚨🚨 PRIORIDADE MÁXIMA - DESPESAS CONCILIADAS: Consulta despesas vinculadas a um processo que foram CONCILIADAS (classificadas e vinculadas a lançamentos bancários), mostrando status de conciliação, origem dos recursos e pendências. ⚠️⚠️⚠️ CRÍTICO: Use SEMPRE quando o usuário perguntar sobre 'despesas', 'pagamentos', 'conciliação' ou 'o que foi conciliado' de um processo. NÃO use obter_valores_processo quando o usuário mencionar 'despesas' ou 'conciliação'. Exemplos OBRIGATÓRIOS: 'despesas do BGR.0070/25' → consultar_despesas_processo(processo_referencia='BGR.0070/25'), 'quais pagamentos foram feitos para o BGR.0070/25' → consultar_despesas_processo(processo_referencia='BGR.0070/25'), 'o que foi conciliado no BGR.0070/25' → consultar_despesas_processo(processo_referencia='BGR.0070/25'), 'mostre as despesas do BGR.0070/25' → consultar_despesas_processo(processo_referencia='BGR.0070/25'). ⚠️ DIFERENÇA: obter_valores_processo retorna valores do CE (frete, seguro, FOB, CIF). consultar_despesas_processo retorna despesas CONCILIADAS (vinculadas a lançamentos bancários).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Referência do processo (ex: BGR.0070/25)"
                        },
                        "incluir_pendentes": {
                            "type": "boolean",
                            "description": "Incluir despesas pendentes de conciliação (default: true)"
                        },
                        "incluir_rastreamento": {
                            "type": "boolean",
                            "description": "Incluir rastreamento completo de origem dos recursos para compliance (default: false)"
                        }
                    },
                    "required": ["processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos",
                "description": "⚠️ ATENÇÃO: Use esta função APENAS quando o usuário pedir uma lista GERAL de processos SEM mencionar uma categoria específica. Lista processos de importação com filtros opcionais. Use quando o usuário pedir para ver processos, listar processos, mostrar processos pendentes, etc. ⚠️ NÃO use esta função se o usuário mencionar uma categoria (ex: ALH, VDM, DMD, MSS) - use listar_processos_por_categoria nesse caso.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pendente", "processando", "sucesso", "erro", "todos"],
                            "description": "Filtrar processos por status. Use 'todos' para listar todos os processos."
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 20.",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "verificar_duimp_registrada",
                "description": "✅ CONSULTA: Verifica se há uma DUIMP registrada para um processo específico. Use SEMPRE quando o usuário PERGUNTAR sobre DUIMP de UM processo específico. ⚠️ IMPORTANTE: A palavra 'registrada' aqui NÃO é uma situação - é apenas uma forma de perguntar se EXISTE uma DUIMP. Exemplos: 'tem DUIMP registrada para VDM.0003/25?', 'tem duimp para MV5.0019/25?', 'a duimp foi registrada?', 'já tem duimp?', 'foi criada?', 'tem duimp?', 'há duimp?', 'existe duimp?', 'tem DUIMP registrada para o processo X?'. Esta função verifica se há DUIMP de PRODUÇÃO ou VALIDAÇÃO vinculada ao processo. ⚠️ NÃO use quando o usuário PEDIR para registrar/criar - use criar_duimp nesse caso. ⚠️ NÃO use para múltiplos processos - use listar_processos_com_duimp. ⚠️ NÃO confunda com 'processos registrados' (situação) - use listar_processos_por_situacao para isso.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: MSS.0018/25, VDM.0003/25)."
                        }
                    },
                    "required": ["processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "verificar_atualizacao_ce",
                "description": "✅ VERIFICAÇÃO INTELIGENTE (API PÚBLICA GRATUITA): Verifica se um CE precisa ser atualizado consultando a API pública gratuita antes de decidir se precisa bilhetar. Use esta função ANTES de consultar_ce_maritimo para tomar uma decisão inteligente sobre se precisa bilhetar ou não. Esta função consulta a API pública (gratuita) e compara com o cache para determinar se há alterações. Retorna se precisa atualizar (bilhetar) ou se pode usar cache (sem custo). Exemplos: Antes de consultar um CE, use esta função para verificar se precisa bilhetar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_ce": {
                            "type": "string",
                            "description": "Número do CE (Conhecimento de Embarque) marítimo. Geralmente tem 15 dígitos (ex: 132505317461600, 152505190990910)."
                        }
                    },
                    "required": ["numero_ce"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_ce_maritimo",
                "description": "⚠️ API BILHETADA: Consulta um CE (Conhecimento de Embarque) marítimo. ⚠️ DECISÃO INTELIGENTE: Esta função AUTOMATICAMENTE consulta a API pública (gratuita) antes de bilhetar para verificar se há alterações. Se não houver alterações, retorna do cache (SEM bilhetar). Se houver alterações ou não estiver no cache, consulta API bilhetada. Use quando o usuário pedir para consultar, buscar ou verificar um CE ESPECÍFICO. Pode consultar pelo número do CE OU pelo número do processo (que já tem CE vinculado). ⚠️ IMPORTANTE: Se você quer evitar bilhetar desnecessariamente, NÃO use forcar_consulta_api=True. Deixe o sistema decidir inteligentemente usando a API pública. Use forcar_consulta_api=True APENAS quando o usuário pedir explicitamente para 'consultar' e você quiser garantir dados atualizados mesmo sem alterações. Exemplos: 'consulte o CE 132505317461600' → deixar sistema decidir (pode usar cache se não houver alterações), 'quais processos estão armazenados?' → usar listar_processos_com_situacao_ce (SEM bilhetar).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_ce": {
                            "type": "string",
                            "description": "Número do CE (Conhecimento de Embarque) marítimo. Geralmente tem 15 dígitos (ex: 132505317461600, 152505190990910). Obrigatório se processo_referencia não for fornecido."
                        },
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: MSS.0018/25, VDM.0003/25). Se fornecido, busca o CE vinculado a este processo. Obrigatório se numero_ce não for fornecido."
                        },
                        "usar_cache_apenas": {
                            "type": "boolean",
                            "description": "✅ USE TRUE quando: 1) O usuário perguntar sobre situação/status sem pedir para 'consultar' (ex: 'qual a situação?', 'está armazenado?'), 2) Você quer SEMPRE evitar custos de API bilhetada, mesmo que haja alterações. Se True, busca apenas no cache local SEM consultar API pública nem bilhetada. Padrão: False (sistema decide inteligentemente).",
                            "default": False
                        },
                        "forcar_consulta_api": {
                            "type": "boolean",
                            "description": "⚠️ USE TRUE APENAS quando: 1) O usuário pedir explicitamente para 'consultar' e você quiser garantir dados atualizados mesmo sem alterações na API pública, 2) Você precisa forçar atualização independente de alterações. Se False (padrão), o sistema consulta API pública primeiro e só bilheta se houver alterações. Padrão: False (sistema decide inteligentemente usando API pública).",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_com_situacao_ce",
                "description": "✅ SEM CUSTO (CACHE APENAS): Lista processos com situação dos CEs (Conhecimentos de Embarque) usando apenas cache local, SEM consultar API bilhetada. Use quando o usuário perguntar sobre processos em geral com situação de CE, como: 'quais processos estão armazenados?', 'quais processos têm CE entregue?', 'mostre processos com situação X', 'listar processos e situação dos CEs'. Esta função NUNCA consulta API bilhetada, apenas usa dados do cache, então é GRATUITA. Exemplos: 'quais processos estão armazenados?' → usar esta função, 'mostre processos com CE entregue' → usar esta função.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "situacao_filtro": {
                            "type": "string",
                            "description": "Filtrar processos por situação do CE. Valores comuns: 'ARMAZENADA', 'ENTREGUE', 'EM_TRANSITO', 'DESCARREGADA', etc. Se não fornecido, retorna todos os processos com suas situações.",
                            "enum": ["ARMAZENADA", "ENTREGUE", "EM_TRANSITO", "DESCARREGADA", "BLOQUEADA", "todas"]
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 50.",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 200
                        }
                    }
                }
            }
        },
        # ✅ DESABILITADO: Função de vinculação manual removida
        # Nesta aplicação não vinculamos manualmente - o sistema busca automaticamente o processo vinculado
        # {
        #     "type": "function",
        #     "function": {
        #         "name": "vincular_processo_ce",
        #         ...
        #     }
        # },
        {
            "type": "function",
            "function": {
                "name": "desvincular_documento_processo",
                "description": "🚨 PRIORIDADE MÁXIMA - DESVINCULAR: Remove/desvincula um documento (CE, CCT, DI, DUIMP, RODOVIARIO) de um processo. ⚠️ CRÍTICO: Use SEMPRE esta função quando o usuário usar palavras como: 'desvincule', 'remova', 'delete', 'retire', 'desligue', 'desassocie' + documento + processo. ⚠️ NUNCA use vincular_processo_ce quando o usuário pedir para DESVINCULAR. Exemplos OBRIGATÓRIOS de quando usar esta função: 'desvincule o CE 132505317461600 do DMD.0068/25' → usar esta função, 'remova o CE do processo X' → usar esta função, 'desvincule a DI do processo Y' → usar esta função, 'delete essa vinculação' → usar esta função. ⚠️ DIFERENÇA CRÍTICA: Se o usuário diz 'desvincule' ou 'remova' → use desvincular_documento_processo. Se o usuário diz 'vincule' ou 'associe' → use vincular_processo_ce. ⚠️ IMPORTANTE: Cada processo deve ter apenas um CE e um CCT. Esta função é essencial para corrigir erros de vinculação.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: VDM.0003/25, MSS.0018/25)"
                        },
                        "tipo_documento": {
                            "type": "string",
                            "enum": ["CE", "CCT", "DI", "DUIMP", "RODOVIARIO"],
                            "description": "Tipo do documento a ser desvinculado"
                        },
                        "numero_documento": {
                            "type": "string",
                            "description": "Número do documento a ser desvinculado (ex: 132505284666402 para CE, 25BR00001928777v1 para DUIMP)"
                        }
                    },
                    "required": ["processo_referencia", "tipo_documento", "numero_documento"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_processo_consolidado",
                "description": "✅ CONSULTA COMPLETA: Consulta JSON consolidado completo de um processo, incluindo todos os documentos (CE, CCT, DI, DUIMP), valores, tributos, timeline, semântica, pendências, etc. Use esta função quando o usuário perguntar sobre um processo e você quiser uma visão completa e enriquecida com todos os dados. Esta função retorna informações detalhadas como: situação da DUIMP/DI, canal, pendências de frete e AFRMM, CEs vinculados, valores (FOB, frete, seguro, CIF), tributos, timeline, etc. Exemplos: 'como está o processo VDM.0003/25?', 'me mostre tudo sobre o processo MV5.0019/25', 'consulte o processo MSS.0018/25'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: VDM.0003/25, MV5.0019/25, MSS.0018/25). Pode aceitar variações como MSS.0018 ou vdm.003."
                        }
                    },
                    "required": ["processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_cct",
                "description": "✅ API GRATUITA: Consulta um CCT (Conhecimento de Carga Aérea). ⚠️ IMPORTANTE: A API de CCT é GRATUITA (não é bilhetada), então pode ser consultada sem custo. Use quando o usuário pedir para consultar, buscar ou verificar um CCT ESPECÍFICO. Pode consultar pelo número do CCT OU pelo número do processo (que já tem CCT vinculado). Esta função consulta a API gratuita e salva no cache automaticamente. Use quando o usuário perguntar sobre um CCT específico, como: 'como está o CCT CWL25100012?', 'consulte o CCT X', 'qual a situação do CCT Y?', 'mostre dados do CCT Z'. Exemplos: 'como está o cct CWL25100012' → usar esta função, 'consulte o CCT CWL25100012' → usar esta função.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_cct": {
                            "type": "string",
                            "description": "Número do CCT (Conhecimento de Carga Aérea). Formato pode variar (ex: CWL25100012, identificação do CCT). Obrigatório se processo_referencia não for fornecido."
                        },
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: MSS.0018/25, VDM.0003/25). Se fornecido, busca o CCT vinculado a este processo. Obrigatório se numero_cct não for fornecido."
                        },
                        "usar_cache_apenas": {
                            "type": "boolean",
                            "description": "✅ USE TRUE quando: 1) O usuário perguntar sobre situação/status sem pedir para 'consultar' (ex: 'qual a situação?', 'está recepcionado?'), 2) Você quer SEMPRE evitar consultar a API, mesmo que haja alterações. Se True, busca apenas no cache local SEM consultar API. Padrão: False (sempre consulta API gratuita).",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "vincular_processo_cct",
                "description": "⚠️ PRIORIDADE ALTA: Vincula um processo de importação a um CCT (Conhecimento de Carga Aérea) que já foi consultado mas não tem processo vinculado. Use esta função quando: 1) O usuário informar qual processo vincular a um CCT (ex: 'vincule ao processo MSS.0018/25'), 2) A última resposta perguntou qual processo vincular e o usuário respondeu com um número de processo, 3) O usuário fornecer um processo após você perguntar sobre vinculação de CCT. ⚠️ CRÍTICO: Esta função atualiza o cache do CCT e deixa pronto para gerar DUIMP. Cada processo deve ter apenas um CCT - CCTs antigos são automaticamente desvinculados. SEMPRE use esta função quando o usuário fornecer um processo para vincular a um CCT.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_cct": {
                            "type": "string",
                            "description": "Número do CCT (Conhecimento de Carga Aérea). Geralmente tem formato específico do sistema (ex: identificação do CCT)."
                        },
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: MSS.0018/25, VDM.0003/25) a ser vinculado ao CCT."
                        }
                    },
                    "required": ["numero_cct", "processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "vincular_processo_di",
                "description": "Vincula um processo de importação a uma DI (Declaração de Importação) que já foi consultada mas não tem processo vinculado. Use esta função quando: 1) O usuário informar qual processo vincular a uma DI, 2) Você precisar vincular uma DI a um processo para facilitar consultas. ⚠️ IMPORTANTE: Esta função atualiza o cache da DI. Uma DI pode estar vinculada a múltiplos processos se necessário.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_di": {
                            "type": "string",
                            "description": "Número da DI (Declaração de Importação). Formato: número da DI (ex: 2524635120)."
                        },
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: MSS.0018/25, VDM.0003/25) a ser vinculado à DI."
                        }
                    },
                    "required": ["numero_di", "processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "vincular_processo_duimp",
                "description": "⚠️ USE ESTA FUNÇÃO quando o usuário pedir para incluir/vincular um número de DUIMP ou DI a um processo. Aceita comandos naturais como: 'inclua o numero duimp 25BR0000194844-1 no processo GLT.0034/25', 'vincular duimp 25BR0000194844 ao processo X', 'incluir di 25/2535383-7 no processo Y'. A função reconhece automaticamente se é DUIMP (padrão 25BR...) ou DI (padrão XX/XXXXX-X) pelo formato do número. Se a versão da DUIMP não for informada, busca automaticamente a versão vigente. ⚠️ IMPORTANTE: Esta função é especialmente útil para CCTs aéreos, onde o número da DUIMP não vem automaticamente no JSON do CCT.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_duimp": {
                            "type": "string",
                            "description": "Número da DUIMP ou DI. Formato DUIMP: 25BR0000194844 ou 25BR0000194844-1 (versão opcional). Formato DI: 25/2535383-7. A função reconhece automaticamente o tipo pelo padrão do número."
                        },
                        "versao_duimp": {
                            "type": "string",
                            "description": "Versão da DUIMP (opcional). Se não informada, a função busca automaticamente a versão vigente. Para DI, este parâmetro é ignorado pois DI não tem versão. Se o usuário informar número no formato 25BR0000194844-1, a versão será extraída automaticamente.",
                            "default": None
                        },
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: GLT.0034/25, MSS.0018/25, VDM.0003/25) a ser vinculado à DUIMP ou DI."
                        }
                    },
                    "required": ["numero_duimp", "processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_por_categoria",
                "description": "Lista todos os processos de uma categoria específica (ex: ALH, VDM, MSS, MV5). Use para perguntas genéricas como: 'como estão os processos ALH?', 'mostre os processos VDM'. NÃO use quando: (1) pergunta for 'quais os embarques [CATEGORIA] chegaram?' → use listar_processos_liberados_registro. (2) pergunta mencionar período específico (hoje, amanhã) → use listar_processos_por_eta. Retorna: ETA/Porto/Navio/Status do Kanban quando disponível.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (ex: 'ALH', 'VDM', 'MSS', 'MV5'). O formato do processo é sempre CATEGORIA.NNNN/AA (ex: ALH.0001/25, MV5.0001/25)."
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": ["categoria"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_resumo_aprendizado",
                "description": "📚 Resumo de aprendizado: Mostra o que a mAIke aprendeu em uma sessão específica. Use quando o usuário perguntar 'o que você aprendeu comigo?', 'o que você aprendeu nesta sessão?', 'resumo de aprendizado', 'o que você guardou?'. Esta função lista regras aprendidas e consultas salvas criadas na sessão atual.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID da sessão (opcional, usa sessão atual se não fornecido)"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_relatorio_observabilidade",
                "description": "📊 Relatório de observabilidade: Gera relatórios sobre uso do sistema (consultas bilhetadas, consultas salvas, regras aprendidas). Use quando o usuário perguntar 'relatório de uso', 'quanto custou?', 'quais consultas são mais usadas?', 'quais regras são mais usadas?', 'relatório de custos', 'observabilidade'. Esta função mostra estatísticas de uso, custos de consultas bilhetadas, e identificação de consultas/regras não utilizadas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data_inicio": {
                            "type": "string",
                            "description": "Data de início (YYYY-MM-DD) ou None para últimos 30 dias"
                        },
                        "data_fim": {
                            "type": "string",
                            "description": "Data de fim (YYYY-MM-DD) ou None para hoje"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_categorias_disponiveis",
                "description": "Lista todas as categorias de processos disponíveis no sistema. Use quando o usuário perguntar 'quais categorias temos?', 'quais categorias estão disponíveis?', 'vc consegue ver quais categorias temos?', 'listar categorias', 'mostre as categorias', etc. Esta função retorna todas as categorias cadastradas no banco de dados, incluindo categorias confirmadas pelo usuário e categorias detectadas automaticamente.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "adicionar_categoria_processo",
                "description": "⚠️ USE APENAS quando o usuário CONFIRMAR explicitamente que uma categoria é válida. Adiciona uma nova categoria de processo ao sistema. Esta função deve ser usada APENAS quando o usuário confirmar que uma categoria desconhecida é realmente uma categoria de processo (ex: usuário responde 'sim' ou 'é' quando perguntado se algo é categoria). NÃO use esta função para adicionar categorias sem confirmação do usuário.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria de processo a adicionar (ex: 'MV5', 'ALH', 'VDM'). Deve ter 2-4 caracteres."
                        }
                    },
                    "required": ["categoria"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_por_situacao",
                "description": "Lista processos de uma categoria específica FILTRADOS por situação (desembaraçados, registrados, entregues). Use quando: usuário perguntar sobre categoria ESPECÍFICA (ALH, VDM, MSS, etc.) com situação específica. Exemplos: 'quais ALH estão desembaraçados?' → situacao='di_desembaracada', 'quais processos GYM estão entregues?' → situacao='entregue'. NÃO use quando pergunta for 'quais os embarques [CATEGORIA] chegaram?' → use listar_processos_liberados_registro. Retorna processos da categoria que correspondem à situação, mostrando canal e data de desembaraço quando disponível.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (ex: 'ALH', 'VDM', 'MSS', 'MV5'). O formato do processo é sempre CATEGORIA.NNNN/AA (ex: ALH.0001/25, MV5.0001/25)."
                        },
                        "situacao": {
                            "type": "string",
                            "description": "Situação a filtrar. Valores comuns: 'desembaraçado', 'desembaracado', 'registrado', 'entregue', 'di_desembaracada', 'desembaracada_carga_entregue', etc. A função busca na situação da DI e/ou DUIMP.",
                            "enum": ["desembaraçado", "desembaracado", "registrado", "entregue", "di_desembaracada", "desembaracada_carga_entregue", "todas"]
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": ["categoria", "situacao"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_com_pendencias",
                "description": "⚠️ USE ESTA FUNÇÃO quando o usuário perguntar sobre processos com PENDÊNCIAS (frete não pago, AFRMM não pago). ⚠️ IMPORTANTE: BLOQUEIOS são diferentes de PENDÊNCIAS. Bloqueios são bloqueios físicos/administrativos da carga (cargaBloqueada, bloqueio_impede_despacho). Pendências são valores não pagos (frete, AFRMM). Use quando o usuário perguntar sobre pendências, como: 'quais processos têm pendência?', 'quais processos estão com pendência?', 'mostre processos com pendência', 'quais ALH estão com pendências?', 'quais processos de ALH têm pendência de frete?', 'mostre processos VDM com pendência', 'quais MSS têm pendências?', 'listar ALH com pendências', 'quais ALH têm pendência de frete?'. ⚠️ CRÍTICO: Se o usuário perguntar 'quais processos têm pendência?' SEM mencionar categoria, esta função agora funciona também (retorna processos de todas as categorias). Se mencionar categoria específica, filtra por essa categoria. Esta função retorna apenas processos que têm pelo menos uma das seguintes PENDÊNCIAS: pendência de frete ou pendência de AFRMM (CE marítimo apenas). ⚠️ NÃO use esta função para bloqueios - use listar_todos_processos_por_situacao com filtro_bloqueio=True.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (ex: 'ALH', 'VDM', 'MSS', 'DMD', 'BND', 'MV5'). O formato do processo é sempre CATEGORIA.NNNN/AA (ex: ALH.0001/25, MV5.0001/25). Se não fornecido, retorna processos de todas as categorias com pendências."
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_registrados_hoje",
                "description": "📋 Lista processos que tiveram DI ou DUIMP registrada HOJE (data de vinculação = hoje). Use quando o usuário perguntar 'o que registramos hoje?', 'quais processos foram registrados hoje?', 'o que foi registrado hoje?', 'quais DIs/DUIMPs foram registradas hoje?', 'o que registramos hoje de [CATEGORIA]?'. ⚠️ IMPORTANTE: Esta função busca processos com DI/DUIMP vinculada HOJE usando a data de `atualizado_em` da tabela `processo_documentos`. Não confia em histórico antigo - apenas processos que tiveram documento vinculado HOJE aparecem. Se o usuário mencionar categoria específica (ex: 'o que registramos hoje de MSS?'), filtra por essa categoria.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (opcional, ex: 'MSS', 'VDM', 'ALH'). Se fornecido, filtra apenas processos dessa categoria. Se None, retorna processos de todas as categorias registrados hoje.",
                            "default": None
                        },
                        "dias_atras": {
                            "type": "integer",
                            "description": "Quantos dias para trás (0=hoje, 1=ontem). Nunca use valores negativos. Padrão: 0.",
                            "default": 0,
                            "minimum": 0,
                            "maximum": 7
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_desembaracados_hoje",
                "description": "✅ Lista processos que DESEMBARAÇARAM HOJE (data/hora de desembaraço). Use quando o usuário perguntar 'o que desembaraçou hoje?', 'quais processos desembaraçaram hoje?', 'teve desembaraço hoje?', 'quais DIs desembaraçaram hoje?'. ⚠️ IMPORTANTE: Isso é diferente de 'registrados hoje' (registro → canal → exigências → desembaraço).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (opcional, ex: 'DMD', 'ALH', 'VDM'). Se não fornecida, retorna todas as categorias.",
                            "default": None
                        },
                        "modal": {
                            "type": "string",
                            "description": "Filtro opcional por modal ('Marítimo'/'Aéreo').",
                            "default": None
                        },
                        "dias_atras": {
                            "type": "integer",
                            "description": "Quantos dias para trás (0=hoje, 1=ontem). Nunca use valores negativos. Padrão: 0.",
                            "default": 0,
                            "minimum": 0,
                            "maximum": 7
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_todos_processos_por_situacao",
                "description": "⚠️⚠️⚠️ ATENÇÃO: Lista TODOS os processos (de TODAS as categorias) filtrados por situação, BLOQUEIO ou pendências. ⚠️⚠️⚠️ USE APENAS quando o usuário perguntar de forma GENÉRICA SEM mencionar categoria específica (ALH, VDM, MSS, BND, DMD, GYM, SLL, etc.), como: 'quais processos estão desembaraçados?' (SEM mencionar ALH, VDM, etc.), 'quais processos estão armazenados?' (sem categoria), 'quais processos estão com bloqueio?' (sem categoria), 'quais processos estão bloqueados?' (sem categoria), 'quais processos estão com pendência?' (sem categoria), 'mostre processos desembaracados' (sem categoria), 'listar processos armazenados' (sem categoria). ⚠️⚠️⚠️ CRÍTICO: Se o usuário mencionar categoria específica (ex: ALH, VDM, MSS, BND, DMD, GYM, SLL) NA PERGUNTA, NÃO USE ESTA FUNÇÃO - use listar_processos_por_situacao com a categoria mencionada. Exemplos OBRIGATÓRIOS: 'quais ALH estão desembaraçados?' → use listar_processos_por_situacao(categoria='ALH', situacao='di_desembaracada'), 'quais os alh que estao desembaracados?' → use listar_processos_por_situacao(categoria='ALH', situacao='di_desembaracada'), NÃO use esta função. ⚠️ IMPORTANTE: BLOQUEIOS são diferentes de PENDÊNCIAS. Bloqueios são bloqueios físicos/administrativos da carga (cargaBloqueada: true, bloqueio_impede_despacho: true). Pendências são valores não pagos (frete, AFRMM). Para BLOQUEIOS, use filtro_bloqueio=True. Para PENDÊNCIAS, use filtro_pendencias=True. Esta função retorna processos de TODAS as categorias que correspondem ao filtro solicitado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "situacao": {
                            "type": "string",
                            "description": "Situação a filtrar. Valores comuns: 'desembaraçado', 'desembaracado', 'armazenado', 'armazenada', 'registrado', 'entregue', 'di_desembaracada', etc. Se não fornecido, não filtra por situação.",
                            "enum": ["desembaraçado", "desembaracado", "armazenado", "armazenada", "registrado", "entregue", "di_desembaracada", ""]
                        },
                        "filtro_pendencias": {
                            "type": "boolean",
                            "description": "Se True, filtra apenas processos com pendências (frete ou AFRMM). Use quando o usuário perguntar 'quais processos estão com pendência?' ou 'processos com pendência'.",
                            "default": False
                        },
                        "filtro_bloqueio": {
                            "type": "boolean",
                            "description": "Se True, filtra apenas processos com bloqueios (carga bloqueada ou bloqueio de despacho). Use quando o usuário perguntar 'quais processos estão com bloqueio?' ou 'processos com bloqueio'.",
                            "default": False
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 500.",
                            "default": 500,
                            "minimum": 1,
                            "maximum": 1000
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_valores_processo",
                "description": "💰 OBTER VALORES: Obtém valores monetários de um processo específico (frete, seguro, FOB, CIF). Use quando o usuário perguntar sobre valores monetários, como: 'qual o valor do frete do processo VDM.0003/25?', 'quanto é o frete do processo X?', 'qual o valor FOB do processo Y?', 'quanto é o seguro do processo Z?', 'qual o CIF do processo W?', 'mostre os valores do processo X', 'qual a moeda do frete do processo Y?'. Esta função retorna os valores encontrados no CE vinculado ao processo, incluindo frete, seguro, FOB, CIF e suas respectivas moedas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo de importação no formato XXX.NNNN/AA (ex: VDM.0003/25, MV5.0019/25). Pode aceitar variações como MSS.0018 ou vdm.003."
                        },
                        "tipo_valor": {
                            "type": "string",
                            "enum": ["frete", "seguro", "fob", "cif", "todos"],
                            "description": "Tipo de valor a retornar. Use 'todos' para retornar todos os valores disponíveis. Padrão: 'todos'.",
                            "default": "todos"
                        }
                    },
                    "required": ["processo_referencia"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_valores_ce",
                "description": "💰 OBTER VALORES DE CE: Obtém valores monetários de um CE específico (frete, seguro, FOB, CIF). Use quando o usuário perguntar sobre valores de um CE específico, como: 'quanto é o frete do CE 132505284200462?', 'qual o valor do frete do CE X?', 'qual a moeda do frete do CE Y?', 'mostre os valores do CE Z'. Esta função retorna os valores encontrados no CE, incluindo frete, seguro, FOB, CIF e suas respectivas moedas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_ce": {
                            "type": "string",
                            "description": "Número do CE (Conhecimento de Embarque) marítimo. Geralmente tem 15 dígitos (ex: 132505284200462, 132505317461600)."
                        },
                        "tipo_valor": {
                            "type": "string",
                            "enum": ["frete", "seguro", "fob", "cif", "todos"],
                            "description": "Tipo de valor a retornar. Use 'todos' para retornar todos os valores disponíveis. Padrão: 'todos'.",
                            "default": "todos"
                        }
                    },
                    "required": ["numero_ce"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_dados_di",
                "description": "📄 OBTER DADOS DE DI: Obtém informações detalhadas de uma DI (Declaração de Importação) específica. Use quando o usuário perguntar sobre uma DI específica, como: 'qual a situação da DI 2521440840?', 'qual canal da DI 2521440840?', 'quando foi o desembaraço da DI 2521440840?', 'mostre dados da DI X', 'como está a DI Y?'. Esta função retorna informações como: situação, canal, data de desembaraço, data de registro, situação de entrega, processo vinculado, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_di": {
                            "type": "string",
                            "description": "Número da DI (Declaração de Importação). Formato: número da DI sem barras (ex: 2521440840, 2524635120)."
                        }
                    },
                    "required": ["numero_di"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_dados_duimp",
                "description": "📋 OBTER DADOS DE DUIMP: Obtém informações detalhadas de uma DUIMP (Declaração Única de Importação) específica. Use quando o usuário perguntar sobre uma DUIMP específica, como: 'qual a situação da DUIMP 25BR00000250599?', 'como está a DUIMP 25BR00001928777?', 'mostre dados da DUIMP X', 'qual o canal da DUIMP Y?'. Esta função retorna informações como: situação, canal, data de registro, versão, processo vinculado, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "numero_duimp": {
                            "type": "string",
                            "description": "Número da DUIMP (Declaração Única de Importação). Formato: 25BR00001928777 ou 25BR00001928777-1 (versão opcional). Se a versão não for informada, busca automaticamente a versão vigente."
                        },
                        "versao_duimp": {
                            "type": "string",
                            "description": "Versão da DUIMP (opcional). Se não informada, busca automaticamente a versão vigente. Se o número for informado no formato 25BR00001928777-1, a versão será extraída automaticamente.",
                            "default": None
                        }
                    },
                    "required": ["numero_duimp"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_extrato_pdf_duimp",
                "description": "🚨🚨🚨 PRIORIDADE MÁXIMA - EXTRATO PDF DA DUIMP: Obtém o extrato completo da DUIMP, consultando diretamente o Portal Único Siscomex (autenticado). Use QUANDO O USUÁRIO PEDIR EXPLICITAMENTE 'extrato da duimp do [processo]', 'extrato da duimp [número]', 'qual o extrato da duimp [número]', 'pdf da duimp do [processo]', 'gerar extrato duimp [processo/número]', 'mostrar extrato duimp [processo/número]', 'extrato duimp [processo/número]'. ⚠️⚠️⚠️ CRÍTICO: Esta função é DIFERENTE de consultar_status_processo. Use esta função quando o usuário pedir especificamente o EXTRATO ou PDF da DUIMP. ⚠️⚠️⚠️ IMPORTANTE: Se o usuário pedir apenas 'extrato do [processo]' SEM mencionar DUIMP/DI/CE, NÃO use esta função. Use obter_extrato_ce primeiro (mais comum), depois obter_extrato_pdf_di, depois esta função. Exemplos OBRIGATÓRIOS: 'extrato da duimp do vdm.0003/25' → obter_extrato_pdf_duimp(processo_referencia='VDM.0003/25'), 'qual o extrato da duimp 25BR00002284997?' → obter_extrato_pdf_duimp(numero_duimp='25BR00002284997'), 'extrato da duimp 25BR00002284997' → obter_extrato_pdf_duimp(numero_duimp='25BR00002284997').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo (ex: VDM.0003/25, ALH.0010/25, MSS.0020/25). Formato: [CATEGORIA].[NUMERO]/[ANO]. Esta função busca a DUIMP deste processo no banco e consulta os dados completos no Portal Único. Use quando o usuário fornecer o processo_referencia."
                        },
                        "numero_duimp": {
                            "type": "string",
                            "description": "Número da DUIMP diretamente (ex: 25BR00002284997, 25BR00001928777). Use quando o usuário fornecer diretamente o número da DUIMP, sem mencionar o processo. Formato: 25BR + 11 dígitos (ex: 25BR00002284997)."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_extrato_ce",
                "description": "🚨🚨🚨 PRIORIDADE MÁXIMA - EXTRATO DO CE: Obtém o extrato completo do CE, consultando diretamente a API do Integra Comex (Serpro) - API BILHETADA. Use QUANDO O USUÁRIO PEDIR EXPLICITAMENTE 'extrato do ce do [processo]', 'extrato do ce [número]', 'qual o extrato do ce [número]', 'pdf do ce do [processo]', 'gerar extrato ce [processo/número]', 'mostrar extrato ce [processo/número]', 'extrato ce [processo/número]'. ⚠️⚠️⚠️ CRÍTICO: Esta função é DIFERENTE de consultar_ce_maritimo. Use esta função quando o usuário pedir especificamente o EXTRATO do CE. Esta função: 1) Busca número do CE no banco pelo processo_referencia OU pelo numero_ce diretamente, 2) Consulta cache local primeiro (sem custo), 3) Se não encontrar no cache ou precisar atualizar, consulta API Integra Comex (Serpro) - BILHETADA (paga por consulta), 4) Retorna dados formatados do extrato. ⚠️ ATENÇÃO: A API Integra Comex é BILHETADA. A consulta só será feita se necessário. ⚠️ NÃO use consultar_ce_maritimo quando o usuário pedir 'extrato do ce'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo (ex: VDM.0003/25, ALH.0010/25, MSS.0020/25). Formato: [CATEGORIA].[NUMERO]/[ANO]. Esta função busca o CE deste processo no banco e consulta os dados completos no Integra Comex (Serpro). Use quando o usuário fornecer o processo_referencia."
                        },
                        "numero_ce": {
                            "type": "string",
                            "description": "Número do CE diretamente (ex: 132505317461600). Use quando o usuário fornecer diretamente o número do CE, sem mencionar o processo. Formato: 15 dígitos numéricos."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_extrato_cct",
                "description": "🚨🚨🚨 PRIORIDADE MÁXIMA - EXTRATO DO CCT: Obtém o extrato completo do CCT (Conhecimento de Carga Aérea), consultando diretamente a API CCTA - API GRATUITA. Use QUANDO O USUÁRIO PEDIR EXPLICITAMENTE 'extrato do cct do [processo]', 'extrato do cct [número]', 'qual o extrato do cct [número]', 'pdf do cct do [processo]', 'gerar extrato cct [processo/número]', 'mostrar extrato cct [processo/número]', 'extrato cct [processo/número]'. ⚠️⚠️⚠️ CRÍTICO: Esta função é DIFERENTE de consultar_cct. Use esta função quando o usuário pedir especificamente o EXTRATO do CCT. Esta função: 1) Busca número do CCT no banco pelo processo_referencia OU pelo numero_cct diretamente, 2) Consulta cache local primeiro (sem custo), 3) Se não encontrar no cache ou precisar atualizar, consulta API CCTA - GRATUITA (não bilhetada), 4) Retorna dados formatados do extrato. ⚠️ ATENÇÃO: A API CCTA é GRATUITA (não bilhetada). ⚠️ NÃO use consultar_cct quando o usuário pedir 'extrato do cct'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo (ex: VDM.0003/25, ALH.0010/25, MSS.0020/25). Formato: [CATEGORIA].[NUMERO]/[ANO]. Esta função busca o CCT deste processo no banco e consulta os dados completos na API CCTA. Use quando o usuário fornecer o processo_referencia."
                        },
                        "numero_cct": {
                            "type": "string",
                            "description": "Número do CCT diretamente (ex: MIA-4673, CWL25100012). Use quando o usuário fornecer diretamente o número do CCT, sem mencionar o processo."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_extrato_pdf_di",
                "description": "🚨🚨🚨 PRIORIDADE MÁXIMA - EXTRATO PDF DA DI: Obtém o extrato completo da DI, consultando diretamente o Integra Comex (Serpro) - API BILHETADA. Use QUANDO O USUÁRIO PEDIR EXPLICITAMENTE 'extrato da di do [processo]', 'extrato da di [número]', 'qual o extrato da di [número]', 'pdf da di do [processo]', 'gerar extrato di [processo/número]', 'mostrar extrato di [processo/número]', 'extrato di [processo/número]'. ⚠️⚠️⚠️ CRÍTICO: Esta função é DIFERENTE de obter_dados_di. Use esta função quando o usuário pedir especificamente o EXTRATO ou PDF da DI. Esta função: 1) Busca número da DI no banco pelo processo_referencia OU pelo numero_di diretamente, 2) Consulta cache local primeiro (sem custo), 3) Se não encontrar no cache, consulta API Integra Comex (Serpro) - BILHETADA (paga por consulta), 4) Gera PDF do extrato. ⚠️ ATENÇÃO: A API Integra Comex é BILHETADA. A consulta só será feita se a DI não estiver no cache. ⚠️ NÃO use obter_dados_di quando o usuário pedir 'extrato' ou 'pdf' da DI! Exemplos: 'extrato da di do vdm.0003/25' → obter_extrato_pdf_di, 'pdf da di do alh.0010/25' → obter_extrato_pdf_di, 'extrato da di 2524635120' → obter_extrato_pdf_di",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Número do processo (ex: VDM.0003/25, ALH.0010/25, MSS.0020/25). Formato: [CATEGORIA].[NUMERO]/[ANO]. Esta função busca a DI deste processo no banco e consulta os dados completos no Integra Comex (Serpro). Use quando o usuário fornecer o processo_referencia."
                        },
                        "numero_di": {
                            "type": "string",
                            "description": "Número da DI diretamente (ex: 2524635120). Use quando o usuário fornecer diretamente o número da DI, sem mencionar o processo."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "consultar_adicoes_di",
                "description": "📦 CONSULTAR ADIÇÕES DA DI (Integra Comex / Serpro): Consulta as adições de uma DI via endpoint oficial `GET /declaracao-importacao/{numeroDI}/adicoes/` com paginação via header `links` (rel=self/rel=next). Aceita `numero_di` OU `processo_referencia` (mesma regra do extrato da DI: se vier processo, resolve o número da DI no banco primeiro). Use quando o usuário pedir para ver 'adições da DI', 'itens/produtos da DI', 'quais adições tem a DI X'. ⚠️ ATENÇÃO: API bilhetada (paga por consulta).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "Processo no formato CATEGORIA.NNNN/AA (ex: DMD.0079/25). Se fornecido, o sistema busca o número da DI vinculada e consulta as adições."
                        },
                        "numero_di": {
                            "type": "string",
                            "description": "Número da DI (ex: 2521440840)."
                        },
                        "max_paginas": {
                            "type": "integer",
                            "description": "Máximo de páginas a percorrer (padrão: 10).",
                            "default": 10
                        },
                        "max_itens": {
                            "type": "integer",
                            "description": "Máximo de adições a retornar (padrão: 500).",
                            "default": 500
                        },
                        "modo": {
                            "type": "string",
                            "enum": ["resumo", "detalhado"],
                            "description": "Formato de saída na UI. 'resumo' lista campos principais; 'detalhado' mostra todos os campos relevantes do produto por adição (quando existirem).",
                            "default": "detalhado"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_por_eta",
                "description": "⚠️⚠️⚠️ CRÍTICO - USE APENAS COM PERÍODO ESPECÍFICO: Use esta função SOMENTE quando o usuário mencionar um período específico (hoje, amanhã, esta semana, próximo mês, data específica). ⚠️⚠️⚠️ NÃO USE quando o usuário perguntar 'quando chegam os [CATEGORIA]?' SEM mencionar período - use listar_processos_por_categoria(categoria='CATEGORIA') em vez disso! Esta função filtra processos pelo ETA (Estimated Time of Arrival) do Kanban e ordena por data de chegada. Use quando o usuário mencionar período específico como: 'quais processos chegam amanhã?', 'quais chegam hoje?', 'quais chegam na próxima semana?', 'quais chegam semana que vem?', 'quais chegam esta semana?', 'quais processos chegam neste mês?', 'quais processos chegam mês que vem?', 'quais chegam em 22/11/2025?', 'o que tem pra chegar?' (quando perguntar genericamente sobre chegadas). ⚠️ CRÍTICO: Se a pergunta for 'quando chegam os [CATEGORIA]?' ou 'quando chegarão os [CATEGORIA]?' SEM período específico, NÃO USE ESTA FUNÇÃO - use listar_processos_por_categoria. ⚠️⚠️⚠️ MUITO IMPORTANTE: Para perguntas genéricas como 'o que tem pra chegar?' ou 'quais processos estão chegando?' SEM categoria específica mencionada, use esta função com filtro_data='mes' (ou 'futuro') e categoria=None (NÃO passe categoria do contexto anterior, a menos que o usuário explicitamente mencione a categoria na mensagem atual). IMPORTANTE: 'esta semana' = da segunda-feira desta semana até domingo. 'semana que vem' ou 'próxima semana' = da próxima segunda-feira até o próximo domingo. 'este mês', 'neste mês' ou apenas 'mês' = do primeiro dia do mês atual até o último dia do mês atual. 'mês que vem' ou 'próximo mês' = do primeiro dia do próximo mês até o último dia do próximo mês.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "processo_referencia": {
                            "type": "string",
                            "description": "✅ NOVO (ETA de um processo específico): Informe um processo (ex: NTM.0001/26) quando a pergunta for do tipo 'quando chega o NTM.0001/26?' / 'qual o ETA do NTM.0001/26?'. Quando este campo é fornecido, o sistema retorna a previsão de chegada (ETA/POD) deste processo e IGNORA a lógica de listagem por período, usando o tracking mais atualizado (Kanban/cache) para exibir ETA/Porto/Navio/Status."
                        },
                        "filtro_data": {
                            "type": "string",
                            "enum": ["hoje", "amanha", "amanhã", "semana", "proxima_semana", "mes", "proximo_mes", "futuro", "todos_futuros", "data_especifica"],
                            "description": "Filtro de data relativa. ⚠️⚠️⚠️ CRÍTICO: Use APENAS quando o usuário mencionar período específico (hoje, amanhã, semana, mês, data). Se a pergunta for 'quando chegam os [CATEGORIA]?' SEM período, NÃO USE esta função - use listar_processos_por_categoria! Use 'hoje' para processos que chegam hoje, 'amanha' ou 'amanhã' para amanhã, 'semana' para esta semana (quando o usuário mencionar 'esta semana', 'na semana'), 'proxima_semana' para semana que vem (quando o usuário mencionar 'semana que vem', 'próxima semana'), 'mes' para este mês (quando o usuário mencionar 'este mês', 'neste mês' ou perguntas genéricas como 'o que tem pra chegar?' sem período específico), 'proximo_mes' para o mês que vem (quando o usuário mencionar 'mês que vem', 'próximo mês'), 'futuro' ou 'todos_futuros' para TODOS os processos com ETA >= hoje sem limite (quando o usuário perguntar 'quais processos estão chegando?' SEM categoria e SEM período). Se o usuário mencionar uma data específica (ex: '22/11/2025'), use 'data_especifica'. ⚠️ Para perguntas genéricas como 'o que tem pra chegar?' sem período mencionado, use 'mes' como padrão.",
                            "default": "semana"
                        },
                        "data_especifica": {
                            "type": "string",
                            "description": "Data específica no formato DD/MM/AAAA ou AAAA-MM-DD (ex: '22/11/2025' ou '2025-11-22'). Use apenas quando filtro_data for 'data_especifica' ou quando o usuário mencionar uma data específica.",
                            "default": None
                        },
                        "categoria": {
                            "type": "string",
                            "description": "⚠️⚠️⚠️ CRÍTICO - Categoria do processo (ex: 'ALH', 'VDM', 'MSS', 'MV5'). Opcional. Use APENAS se o usuário MENCIONAR explicitamente uma categoria na mensagem atual. NÃO use categoria de contexto anterior ou histórico quando a pergunta for genérica (ex: 'o que tem pra chegar?' sem mencionar categoria). Para perguntas genéricas sem categoria específica, deixe como None para retornar processos de TODAS as categorias.",
                            "default": None
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_por_navio",
                "description": "🚢⚠️⚠️⚠️ PRIORIDADE MÁXIMA - BUSCAR PROCESSOS POR NAVIO: Lista processos filtrados por nome do navio. Use ESTA função quando o usuário perguntar sobre processos em um navio específico, como: 'quais processos estão no navio CMA CGM BAHIA?', 'quais processos mv5 estão no navio X?', 'quais processos MSS estão no navio Y?', 'mostre processos do navio Z', 'listar processos do navio W'. ⚠️ CRÍTICO: Se o usuário mencionar uma categoria específica (ex: MV5, MSS) junto com o navio, use o parâmetro categoria. Exemplos OBRIGATÓRIOS: 'quais processos estão no navio CMA CGM BAHIA?' → listar_processos_por_navio(nome_navio='CMA CGM BAHIA'), 'quais processos mv5 estão no navio CMA CGM BAHIA?' → listar_processos_por_navio(nome_navio='CMA CGM BAHIA', categoria='MV5'), 'quais processos MSS estão no navio X?' → listar_processos_por_navio(nome_navio='X', categoria='MSS'). Esta função busca no SQLite (tabela processos_kanban) usando busca parcial case-insensitive no campo nome_navio e retorna processos ordenados por ETA, incluindo informações de ETA, Porto, Navio e Status do Kanban quando disponível.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nome_navio": {
                            "type": "string",
                            "description": "Nome do navio para filtrar (ex: 'CMA CGM BAHIA', 'MSC ALLEGRA'). A busca é parcial e case-insensitive, então pode usar parte do nome (ex: 'BAHIA' encontra 'CMA CGM BAHIA')."
                        },
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (opcional, ex: 'MV5', 'MSS', 'ALH'). Use APENAS se o usuário mencionar explicitamente uma categoria junto com o navio. Se não fornecido, retorna processos de TODAS as categorias do navio.",
                            "default": None
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": ["nome_navio"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_em_dta",
                "description": "🚚⚠️⚠️⚠️ PRIORIDADE - PROCESSOS EM DTA: Lista processos que estão em DTA (Declaração de Trânsito Aduaneiro). DTA significa que a carga já chegou e está sendo removida para outro recinto alfandegado, onde será registrada uma DI ou DUIMP posteriormente. ⚠️⚠️⚠️ CRÍTICO: 'em DTA' NÃO é uma categoria! 'em DTA' significa que o processo TEM um documento DTA. NÃO passe categoria='EM' quando o usuário perguntar 'quais processos estão em DTA?'. ⚠️⚠️⚠️ USE ESTA FUNÇÃO quando o usuário perguntar: 'quais processos estão em DTA?', 'quais processos têm DTA?', 'mostre processos em DTA', 'listar processos com DTA', 'quais MV5 estão em DTA?', 'quais processos estão em trânsito?'. Exemplos OBRIGATÓRIOS: 'quais processos estão em DTA?' → listar_processos_em_dta() (SEM categoria), 'quais MV5 estão em DTA?' → listar_processos_em_dta(categoria='MV5'). ⚠️⚠️⚠️ REGRA CRÍTICA: Se a pergunta é apenas 'quais processos estão em DTA?' (sem mencionar categoria específica como MV5, ALH, etc.), NÃO passe o parâmetro categoria. Esta função retorna processos que têm número de DTA preenchido, indicando que estão em trânsito para outro recinto alfandegado.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (opcional, ex: 'MV5', 'ALH', 'VDM'). ⚠️⚠️⚠️ CRÍTICO: Use APENAS se o usuário mencionar explicitamente uma categoria ESPECÍFICA como MV5, ALH, VDM, etc. NÃO use se a pergunta for apenas 'quais processos estão em DTA?' - nesse caso, NÃO passe este parâmetro (ou passe null/None). 'em DTA' NÃO é uma categoria! Se não fornecido, retorna processos de TODAS as categorias.",
                            "default": None
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_liberados_registro",
                "description": "📋⚠️⚠️⚠️ PRIORIDADE ABSOLUTA - PROCESSOS QUE CHEGARAM SEM DESPACHO: Lista processos que chegaram (data de chegada/destino <= hoje) e NÃO têm registro de DI nem de DUIMP. ⚠️⚠️⚠️⚠️⚠️ CRÍTICO MÁXIMO - USE ESTA FUNÇÃO QUANDO A PERGUNTA CONTÉM: 'quais os embarques [CATEGORIA] chegaram?' ou 'quais embarques [CATEGORIA] chegaram?'. Esta é a FUNÇÃO CORRETA para essas perguntas. NÃO use listar_processos_por_categoria. Palavras-chave que indicam esta função: 'embarques' + 'chegaram', 'chegaram sem despacho', 'liberados para registro', 'chegaram para despacho'. ⚠️⚠️⚠️ REGRA DE OURO: Se a pergunta contém 'embarques' E 'chegaram', SEMPRE use esta função. Exemplos OBRIGATÓRIOS: 'quais os embarques GYM chegaram?' → listar_processos_liberados_registro(categoria='GYM', dias_retroativos=5), 'quais os embarques ALH chegaram?' → listar_processos_liberados_registro(categoria='ALH', dias_retroativos=5), 'quais embarques VDM chegaram?' → listar_processos_liberados_registro(categoria='VDM', dias_retroativos=5). Outras perguntas: 'quais processos chegaram sem despacho?', 'quais processos estão liberados para registro?', 'quais processos chegaram nos últimos 5 dias?', 'quais ALH chegaram sem DI?'. ⚠️ CRÍTICO: Esta função filtra processos que JÁ chegaram (data <= hoje) com data preenchida (dataDestinoFinal para CE, dataHoraChegadaEfetiva para CCT) e que NÃO têm DI nem DUIMP desembaraçada. Por padrão, filtra dos últimos 5 dias. Se o usuário não mencionar período, use dias_retroativos=5.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (opcional, ex: 'GYM', 'ALH', 'VDM'). Use APENAS se o usuário mencionar explicitamente uma categoria. Se não fornecido, retorna processos de TODAS as categorias.",
                            "default": None
                        },
                        "dias_retroativos": {
                            "type": "integer",
                            "description": "Número de dias para buscar retroativamente a partir de hoje (padrão: 30). Use para filtrar apenas processos que chegaram recentemente. Se None, busca todos os processos que chegaram até hoje (pode trazer muitos resultados). Se o usuário mencionar período específico como 'última semana', use 7. Se mencionar 'este mês', calcule os dias desde o início do mês. Para perguntas sobre 'embarques que chegaram' sem período específico, use 30 dias como padrão para garantir que encontra processos recentes.",
                            "default": 30,
                            "minimum": 1,
                            "maximum": 365
                        },
                        "data_inicio": {
                            "type": "string",
                            "description": "Data início do período (formato YYYY-MM-DD ou DD/MM/YYYY). Opcional. Se fornecido, ignora dias_retroativos. Use quando o usuário mencionar período específico.",
                            "default": None
                        },
                        "data_fim": {
                            "type": "string",
                            "description": "Data fim do período (formato YYYY-MM-DD ou DD/MM/YYYY). Opcional. Se None, usa hoje. Use quando o usuário mencionar período específico.",
                            "default": None
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de processos a retornar. Padrão: 200.",
                            "default": 200,
                            "minimum": 1,
                            "maximum": 500
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "obter_dashboard_hoje",
                "description": "📅⚠️⚠️⚠️ PRIORIDADE ABSOLUTA - DASHBOARD DO DIA: Retorna um resumo consolidado de todas as informações relevantes para o dia atual. ⚠️⚠️⚠️ USE ESTA FUNÇÃO quando o usuário perguntar: 'o que temos pra hoje?', 'o que temos para hoje?', 'dashboard de hoje', 'resumo do dia', 'parecer do dia', 'análise do dia', 'visão geral de hoje', 'panorama de hoje', 'o que precisa ser feito hoje?', 'o que está chegando hoje?', 'processos de hoje', 'o que temos hoje?', 'o que tem pra hoje?'. Sinônimos aceitos: parecer, análise, visão geral, panorama, resumo, dashboard. ⚠️⚠️⚠️ CRÍTICO: Esta função NÃO é sobre categorias de processos (ALH, VDM, etc.) - é sobre um resumo geral do dia. Se o usuário perguntar 'o que temos pra hoje?' ou usar sinônimos como 'parecer', 'análise', 'visão geral', 'panorama' SEM mencionar categoria específica, SEMPRE use esta função. Esta função consolida: processos chegando hoje, processos prontos para registro DI/DUIMP, pendências ativas (ICMS, AFRMM, LPCO, bloqueios), DUIMPs em análise, processos com ETA alterado, alertas recentes e sugestões de ações priorizadas. ⚠️ IMPORTANTE: Esta função retorna um dashboard completo formatado em markdown, não apenas uma lista. Use esta função quando o usuário pedir qualquer tipo de resumo, parecer, análise ou visão geral do dia atual.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Filtro opcional por categoria (ex: 'ALH', 'VDM', 'GYM'). Use quando o usuário mencionar categoria específica, como 'o que temos pra hoje ALH?' ou 'dashboard de hoje VDM?'."
                        },
                        "modal": {
                            "type": "string",
                            "enum": ["Marítimo", "Aéreo"],
                            "description": "Filtro opcional por modal. Use quando o usuário mencionar 'aéreo' ou 'marítimo', como 'o que temos pra hoje aéreo?' ou 'dashboard marítimo de hoje?'."
                        },
                        "apenas_pendencias": {
                            "type": "boolean",
                            "description": "Se true, mostra apenas pendências. Use quando o usuário perguntar 'o que temos pra hoje com pendências?' ou 'pendências de hoje?'.",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "gerar_resumo_reuniao",
                "description": "📊 MODO REUNIÃO: Gera um resumo executivo completo para reunião com cliente/categoria. Use quando o usuário pedir: 'prepara resumo para reunião do cliente X', 'resumo executivo para reunião', 'prepara apresentação para cliente Y', 'resumo para reunião da categoria Z', 'modo reunião para cliente X desta semana'. Esta função combina múltiplas análises: atrasos no período, pendências abertas, DUIMPs/DI registradas, ETA alterado, processos chegando, e gera um texto formatado pronto para apresentação com: Resumo Executivo, Pontos de Atenção, Próximos Passos. ⚠️ IMPORTANTE: Esta função usa modo analítico (modelo mais forte) para gerar análises complexas e texto executivo. ⚠️⚠️⚠️ CRÍTICO - NÃO USE PARA: 'resumo do mv5', 'resumo do dmd', 'envia um email com o resumo do mv5' → Use 'enviar_relatorio_email' com categoria=[CATEGORIA] e tipo_relatorio='resumo' em vez desta função! Esta função é APENAS para resumos executivos de reunião, não para relatórios simples de categoria.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do cliente (ex: 'GYM', 'ALH', 'VDM'). Se não fornecido, gera resumo geral."
                        },
                        "periodo": {
                            "type": "string",
                            "enum": ["hoje", "semana", "mes", "periodo_especifico"],
                            "description": "Período do resumo. Padrão: 'semana'.",
                            "default": "semana"
                        },
                        "data_inicio": {
                            "type": "string",
                            "description": "Data de início (formato DD/MM/AAAA) se periodo='periodo_especifico'."
                        },
                        "data_fim": {
                            "type": "string",
                            "description": "Data de fim (formato DD/MM/AAAA) se periodo='periodo_especifico'."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "fechar_dia",
                "description": "Retorna resumo de todas as movimentações do dia atual (fechamento do dia). ✅ AJUSTE (12/01/2026): 'fechamento do dia' e 'resumo do dia' são a MESMA COISA. Use quando: usuário perguntar 'fechar o dia', 'fechamento do dia', 'resumo do dia', 'parecer do fechamento', 'análise do fechamento', 'visão geral do fechamento', 'panorama do fechamento', 'o que movimentou hoje?', 'o que aconteceu hoje?'. Sinônimos aceitos: parecer, análise, visão geral, panorama, resumo, fechamento. NUNCA use quando o usuário pedir para ENVIAR por email - use enviar_relatorio_email nesse caso. Lista: processos que chegaram hoje, desembaraçados hoje, DUIMPs criadas hoje, mudanças de status CE/DI/DUIMP hoje. Diferente de 'obter_dashboard_hoje' - mostra o que JÁ ACONTECEU (fechamento), não planejamento.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Filtro opcional por categoria (ex: 'MV5', 'VDM', 'GYM'). ⚠️⚠️⚠️ CRÍTICO: Use APENAS quando o usuário mencionar categoria específica na mensagem atual, como 'fechar o dia MV5?' ou 'fechamento do dia VDM?'. NUNCA use categoria do contexto anterior se o usuário não mencionou na mensagem atual. Se o usuário pedir apenas 'fechamento do dia' sem mencionar categoria, deixe este campo vazio/null."
                        },
                        "modal": {
                            "type": "string",
                            "enum": ["Marítimo", "Aéreo"],
                            "description": "Filtro opcional por modal. Use quando o usuário mencionar 'aéreo' ou 'marítimo', como 'fechar o dia aéreo?' ou 'fechamento marítimo de hoje?'."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_processos_registrados_periodo",
                "description": "📅 Lista registros de DI/DUIMP em um período (histórico) usando `mAIke_assistente.dbo.DOCUMENTO_ADUANEIRO.data_registro`. Use quando o usuário perguntar: 'o que registramos ontem?', 'o que registramos hoje?', 'o que registramos dia 22/01?', 'o que registramos dia 22/01/26?', 'o que registramos em 22/01?', 'o que registramos em dezembro/2025?', 'o que registramos esse mês?', 'o que registramos essa semana?', 'o que registramos de 01/01/2025 a 30/05/2026?', 'o que registramos em outubro de BND?'. ⚠️ Data sem ano (ex: 22/01) = ano atual. Mesmo critério do dashboard (Registro = data_registro da DI/DUIMP). Suporta filtro por categoria (ALH/VDM/BND/etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "categoria": {
                            "type": "string",
                            "description": "Filtro opcional por categoria (ex: 'BND', 'VDM', 'DMD')."
                        },
                        "periodo": {
                            "type": "string",
                            "enum": ["hoje", "ontem", "semana", "mes", "ano", "periodo_especifico"],
                            "description": "Tipo de período. Se omitir, assume 'hoje'."
                        },
                        "mes": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 12,
                            "description": "Mês (1-12) quando periodo='mes'."
                        },
                        "ano": {
                            "type": "integer",
                            "minimum": 2000,
                            "maximum": 2100,
                            "description": "Ano (ex: 2025) quando periodo='mes' ou periodo='ano'."
                        },
                        "data_inicio": {
                            "type": "string",
                            "description": "Data início DD/MM/AAAA (ou DD/MM/AA) quando periodo='periodo_especifico'."
                        },
                        "data_fim": {
                            "type": "string",
                            "description": "Data fim DD/MM/AAAA (ou DD/MM/AA) quando periodo='periodo_especifico'."
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Limite de itens retornados (máx 1000).",
                            "default": 200
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "gerar_relatorio_importacoes_fob",
                "description": "📊 Gera relatório de importações normalizado por FOB (Free On Board). Use quando: usuário perguntar 'quanto foi importado em [mês]?', 'quanto foi importado em [ano]?', 'quanto o [categoria] importou em [mês/ano]?', 'valor importado [categoria] [mês]', 'relatório fob [mês]', 'fob importado [categoria] [mês]', 'parecer de importações [mês/ano]', 'análise de importações [mês/ano]', 'visão geral de importações [mês/ano]', 'panorama de importações [mês/ano]'. ✅ NOVO: Se o usuário informar APENAS o ano (ex: 'em 2025'), gere o relatório do ANO INTEIRO (mes omitido). Esta função busca processos desembaraçados (DI ou DUIMP) no período especificado e calcula valores FOB normalizados. Para DI: FOB = VMLD - Frete - Seguro. Para DUIMP: FOB já está disponível diretamente. Retorna valores em USD e BRL, agrupados por categoria.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mes": {
                            "type": "integer",
                            "description": "Mês (1-12). Se omitido e ano for fornecido, interpreta como ANO INTEIRO. Se omitido e ano também não for fornecido, usa mês atual.",
                            "minimum": 1,
                            "maximum": 12
                        },
                        "ano": {
                            "type": "integer",
                            "description": "Ano (ex: 2025). Se não fornecido, usa ano atual.",
                            "minimum": 2000,
                            "maximum": 2100
                        },
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (ex: 'DMD', 'VDM', 'ALH', 'BND'). Se não fornecido, busca todas as categorias.",
                            "enum": ["DMD", "VDM", "ALH", "BND", "MSS", "GYM", "SLL", "MV5"]
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "gerar_relatorio_averbacoes",
                "description": "📊 Gera relatório de averbações de seguro em formato Excel. Use quando: usuário perguntar 'averbacao [categoria] [mês]', 'averbação [categoria] [mês]', 'relatorio averbacao [categoria] [mês]', 'relatório averbação [categoria] [mês]', 'parecer de averbações [categoria] [mês]', 'análise de averbações [categoria] [mês]', 'visão geral de averbações [categoria] [mês]', 'panorama de averbações [categoria] [mês]'. Sinônimos aceitos: relatório, parecer, análise, visão geral, panorama, resumo. Esta função busca processos com DI registrada no mês/ano especificado e gera um arquivo Excel com dados para averbação de seguro, incluindo: país de origem, porto origem, cidade destino, data do BL, tipo transporte, mercadoria, nome navio, custo USD, frete USD, despesas, lucros, impostos da DI USD, número da DI, e observações (processo_referencia).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "mes": {
                            "type": "string",
                            "description": "Mês no formato MM (ex: '11') ou YYYY-MM (ex: '2025-11'). Se não fornecido, usa mês atual."
                        },
                        "ano": {
                            "type": "integer",
                            "description": "Ano (ex: 2025). Se não fornecido, usa ano atual.",
                            "minimum": 2000,
                            "maximum": 2100
                        },
                        "categoria": {
                            "type": "string",
                            "description": "Categoria do processo (ex: 'DMD', 'VDM', 'ALH', 'BND'). Se não fornecido, busca todas as categorias.",
                            "enum": ["DMD", "VDM", "ALH", "BND", "MSS", "GYM", "SLL", "MV5"]
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "buscar_ncms_por_descricao",
                "description": "🔍 Busca NCMs (Nomenclatura Comum do Mercosul) por descrição do produto. Use esta função quando o usuário perguntar sobre NCMs de um produto, como: 'qual o NCM de alho?', 'buscar NCM para celular', 'encontrar NCM de medicamento', 'quais NCMs têm alho na descrição?', 'buscar NCM por descrição X'. Esta função retorna uma lista de NCMs que contêm o termo de busca na descrição, agrupados por hierarquia.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "termo": {
                            "type": "string",
                            "description": "Termo de busca para descrição do produto (ex: 'alho', 'celular', 'medicamento'). Deve ter pelo menos 2 caracteres."
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de resultados a retornar. Padrão: 50, máximo: 200.",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 200
                        },
                        "incluir_relacionados": {
                            "type": "boolean",
                            "description": "Se True, inclui NCMs relacionados na hierarquia (ex: quando encontra 'alho', mostra também 'outros' do mesmo grupo). Padrão: True.",
                            "default": True
                        }
                    },
                    "required": ["termo"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "sugerir_ncm_com_ia",
                "description": "🤖 Sugere NCM usando IA baseado em descrição do produto com RAG (Retrieval Augmented Generation). Use esta função quando o usuário perguntar sobre NCM de um produto, como: 'qual o ncm do gv50?', 'qual o ncm do gps?', 'qual o ncm de alho?', 'qual ncm usar para X?', 'IA sugerir NCM para Y', 'recomendar NCM para produto Z'. ⚠️ CRÍTICO: Use esta função para perguntas sobre NCM de PRODUTOS (não categorias de processos como ALH, VDM, etc.). Esta função usa IA para analisar a descrição e sugerir o NCM mais adequado, validando se o NCM sugerido existe no cache e sugerindo alternativas similares se necessário.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "descricao": {
                            "type": "string",
                            "description": "Descrição do produto para sugerir NCM (ex: 'alho para tempero', 'celular smartphone', 'medicamento para dor de cabeça')."
                        },
                        "contexto": {
                            "type": "object",
                            "description": "Contexto adicional opcional (ex: país de origem, tipo de produto, etc.).",
                            "default": {}
                        },
                        "usar_cache": {
                            "type": "boolean",
                            "description": "Se True, usa RAG com cache local para maior precisão. Padrão: True.",
                            "default": True
                        },
                        "validar_sugestao": {
                            "type": "boolean",
                            "description": "Se True, valida se NCM sugerido existe no cache. Padrão: True.",
                            "default": True
                        }
                    },
                    "required": ["descricao"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "detalhar_ncm",
                "description": "📋 Detalha a hierarquia completa de um NCM e lista todos os NCMs de 8 dígitos que pertencem ao grupo. Use esta função quando o usuário pedir para 'detalhar NCM X', 'mostrar hierarquia do NCM Y', 'quais são todos os NCMs de 8 dígitos do grupo Z?', 'detalhe o NCM 841451', 'mostre a hierarquia completa do 8415'. Esta função aceita NCMs de 4, 6 ou 8 dígitos e retorna: 1) A hierarquia completa (4, 6 e 8 dígitos), 2) Todos os NCMs de 8 dígitos que pertencem àquele grupo. Exemplos: 'detalhar NCM 841451' → mostra hierarquia e todos os NCMs de 8 dígitos do grupo 841451, 'detalhar 8415' → mostra hierarquia e todos os NCMs de 8 dígitos do grupo 8415.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ncm": {
                            "type": "string",
                            "description": "NCM a detalhar (4, 6 ou 8 dígitos). Ex: '8414', '841451', '84145100'. Pode ter ou não pontos/traços (será normalizado automaticamente)."
                        }
                    },
                    "required": ["ncm"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "buscar_nota_explicativa_nesh",
                "description": "📚 Busca Notas Explicativas NESH (Nomenclatura Estatística SH) da Receita Federal do Brasil. Use esta função quando o usuário perguntar sobre regras de classificação, critérios de inclusão/exclusão, ou quiser entender melhor como classificar um produto em um NCM específico. ⚠️ IMPORTANTE: Se o usuário pedir explicitamente para 'buscar na NESH', 'consultar NESH', 'pesquisar NESH' ou 'NESH de [produto]', use ESTA função diretamente (busca direta, sem passar por IA ou outras validações). Exemplos de busca direta: 'buscar na nesh alho', 'consultar nesh para ventilador', 'nesh de 0703.20', 'pesquisar nesh sobre celular'. Exemplos gerais: 'qual a nota explicativa do NCM 841451?', 'quais são os critérios para classificar ventilador?', 'o que diz a NESH sobre o NCM 84.14.51?', 'mostre a nota explicativa da posição 84.14', 'quais produtos são incluídos no NCM 841451?'. Esta função retorna as Notas Explicativas oficiais da Receita Federal que detalham como classificar produtos na NCM.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ncm": {
                            "type": "string",
                            "description": "Código NCM (4, 6 ou 8 dígitos) para buscar a nota explicativa. Ex: '8414', '841451', '84145100', '84.14.51'. Pode ter ou não pontos/traços (será normalizado automaticamente).",
                            "default": None
                        },
                        "descricao_produto": {
                            "type": "string",
                            "description": "Descrição do produto para busca semântica nas notas explicativas. Use quando o usuário perguntar sobre regras de classificação de um produto específico sem mencionar o código NCM. Ex: 'ventilador de teto', 'copo descartável', 'alho'. Se fornecido junto com NCM, busca notas que combinem ambos.",
                            "default": None
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de notas explicativas a retornar. Padrão: 3.",
                            "default": 3,
                            "minimum": 1,
                            "maximum": 10
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_consultas_bilhetadas_pendentes",
                "description": "💰 Lista consultas bilhetadas pendentes de aprovação. ⚠️ CRÍTICO: Esta função mostra APENAS consultas com status 'pendente' por padrão. Consultas já aprovadas, rejeitadas ou executadas NÃO aparecem nesta lista. Use quando o usuário perguntar sobre consultas pendentes, quiser ver quais consultas precisam ser aprovadas, ou quiser revisar consultas antes de aprovar. Exemplos: 'quais consultas estão pendentes?', 'mostrar consultas pendentes', 'listar consultas de CE pendentes', 'quantas consultas estão aguardando aprovação?'. Esta função mostra detalhes de cada consulta (tipo, documento, processo, motivo, custo estimado) para ajudar na decisão de aprovar ou rejeitar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["pendente", "aprovado", "rejeitado", "executado"],
                            "description": "⚠️ IMPORTANTE: Por padrão, esta função mostra apenas consultas 'pendente'. Se o usuário pedir para ver consultas aprovadas/executadas, use 'aprovado' ou 'executado'. Padrão: 'pendente'."
                        },
                        "tipo_consulta": {
                            "type": "string",
                            "enum": ["CE", "DI", "Manifesto", "Escala", "CCT"],
                            "description": "Filtrar consultas por tipo (CE, DI, Manifesto, Escala, CCT). Se não fornecido, retorna todos os tipos."
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de consultas a retornar. Padrão: 50.",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 200
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "aprovar_consultas_bilhetadas",
                "description": "✅ Aprova consultas bilhetadas pendentes para execução. Use quando o usuário pedir para aprovar consultas, autorizar consultas, ou permitir que consultas sejam executadas. ⚠️ CRÍTICO: Quando o usuário diz 'aprovar consulta X' (onde X é um número pequeno como 1, 2, 3), SEMPRE interprete como o NÚMERO DA LISTA mostrada na última listagem de consultas pendentes, NÃO como ID real. A função converte automaticamente. Exemplos: 'aprovar consulta 1' → número 1 da lista (pode ser ID 40), 'aprovar consulta 40' → ID real 40, 'aprovar todas as consultas de CE', 'autorizar consultas pendentes', 'aprovar todas'. Esta função aprova as consultas e tenta executá-las imediatamente. ⚠️ CUSTO: Consultas aprovadas serão bilhetadas (R$ 0,942 por consulta).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "⚠️ CRÍTICO: Quando o usuário diz 'consulta X' e X é um número pequeno (1-100), SEMPRE use o número da lista mostrada na última listagem, NÃO o ID real. A função converte automaticamente números da lista (1-100) para IDs reais. Ex: Se usuário diz 'consulta 2' e a lista mostra '2. Consulta #39', passe [2] (não [39]). Para IDs reais (>100), passe diretamente. Se não fornecido e aprovar_todas=False, retorna erro."
                        },
                        "tipo_consulta": {
                            "type": "string",
                            "enum": ["CE", "DI", "Manifesto", "Escala", "CCT"],
                            "description": "Se aprovar_todas=True, filtrar por tipo de consulta. Ex: 'CE' para aprovar apenas consultas de CE."
                        },
                        "aprovar_todas": {
                            "type": "boolean",
                            "description": "Se True, aprova todas as consultas pendentes (ou do tipo especificado em tipo_consulta). Padrão: False.",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "rejeitar_consultas_bilhetadas",
                "description": "❌ Rejeita consultas bilhetadas pendentes. Use quando o usuário pedir para rejeitar consultas, negar aprovação, ou cancelar consultas. ⚠️ CRÍTICO: Quando o usuário diz 'rejeitar consulta X' (onde X é um número pequeno como 1, 2, 3), SEMPRE interprete como o NÚMERO DA LISTA mostrada na última listagem de consultas pendentes, NÃO como ID real. A função converte automaticamente. Exemplos: 'rejeitar consulta 1' → número 1 da lista (pode ser ID 40), 'rejeitar consulta 40' → ID real 40, 'rejeitar todas as consultas de DI', 'cancelar consultas pendentes', 'rejeitar todas'. Esta função rejeita as consultas e elas não serão executadas (economia de custo).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "⚠️ CRÍTICO: Quando o usuário diz 'consulta X' e X é um número pequeno (1-100), SEMPRE use o número da lista mostrada na última listagem, NÃO o ID real. A função converte automaticamente números da lista (1-100) para IDs reais. Ex: Se usuário diz 'consulta 2' e a lista mostra '2. Consulta #39', passe [2] (não [39]). Para IDs reais (>100), passe diretamente. Se não fornecido e rejeitar_todas=False, retorna erro."
                        },
                        "tipo_consulta": {
                            "type": "string",
                            "enum": ["CE", "DI", "Manifesto", "Escala", "CCT"],
                            "description": "Se rejeitar_todas=True, filtrar por tipo de consulta. Ex: 'DI' para rejeitar apenas consultas de DI."
                        },
                        "rejeitar_todas": {
                            "type": "boolean",
                            "description": "Se True, rejeita todas as consultas pendentes (ou do tipo especificado em tipo_consulta). Padrão: False.",
                            "default": False
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Motivo da rejeição (opcional). Ex: 'Dados já atualizados', 'Consulta desnecessária'."
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ver_status_consultas_bilhetadas",
                "description": "📊 Verifica o status de consultas bilhetadas (individual ou estatísticas gerais). Use quando o usuário perguntar sobre o status de uma consulta específica ou quiser ver estatísticas gerais. Exemplos: 'status da consulta 123', 'como está a consulta 1?', 'estatísticas de consultas', 'quantas consultas foram aprovadas?', 'mostrar status das consultas'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "consulta_id": {
                            "type": "integer",
                            "description": "ID da consulta específica para verificar status. Se não fornecido, retorna estatísticas gerais."
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "listar_consultas_aprovadas_nao_executadas",
                "description": "📋 Lista consultas bilhetadas que foram aprovadas mas ainda não foram executadas. Use quando o usuário perguntar sobre consultas aprovadas que estão aguardando execução, quiser ver quais consultas precisam ser executadas, ou quiser revisar consultas aprovadas. Exemplos: 'quais consultas foram aprovadas mas não executadas?', 'mostrar consultas aprovadas', 'listar consultas aprovadas de CE', 'quantas consultas estão aprovadas aguardando execução?'. Esta função mostra detalhes de cada consulta aprovada (tipo, documento, processo, quando foi aprovada) para ajudar na decisão de executar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tipo_consulta": {
                            "type": "string",
                            "enum": ["CE", "DI", "Manifesto", "Escala", "CCT"],
                            "description": "Filtrar consultas por tipo (CE, DI, Manifesto, Escala, CCT). Se não fornecido, retorna todos os tipos."
                        },
                        "limite": {
                            "type": "integer",
                            "description": "Número máximo de consultas a retornar. Padrão: 50.",
                            "default": 50,
                            "minimum": 1,
                            "maximum": 200
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "executar_consultas_aprovadas",
                "description": "🚀 Executa consultas bilhetadas que foram aprovadas mas ainda não foram executadas. Use quando o usuário pedir para executar consultas aprovadas, processar consultas aprovadas, ou rodar consultas que estão aguardando execução. ⚠️ CRÍTICO: Quando o usuário diz 'executar consulta X' (onde X é um número pequeno como 1, 2, 3), SEMPRE interprete como o NÚMERO DA LISTA mostrada na última listagem de consultas aprovadas, NÃO como ID real. A função converte automaticamente. Exemplos: 'executar consulta 1' → número 1 da lista de aprovadas (pode ser ID 40), 'executar consulta 40' → ID real 40, 'executar todas as consultas aprovadas de CE', 'processar consultas aprovadas', 'executar todas as aprovadas'. Esta função executa as consultas bilhetadas imediatamente. ⚠️ CUSTO: Consultas executadas serão bilhetadas (R$ 0,942 por consulta).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "⚠️ CRÍTICO: Quando o usuário diz 'consulta X' e X é um número pequeno (1-100), SEMPRE use o número da lista mostrada na última listagem de consultas aprovadas, NÃO o ID real. A função converte automaticamente números da lista (1-100) para IDs reais. Ex: Se usuário diz 'consulta 2' e a lista mostra '2. Consulta #39', passe [2] (não [39]). Para IDs reais (>100), passe diretamente. Se não fornecido e executar_todas=False, retorna erro."
                        },
                        "tipo_consulta": {
                            "type": "string",
                            "enum": ["CE", "DI", "Manifesto", "Escala", "CCT"],
                            "description": "Se executar_todas=True, filtrar por tipo de consulta. Ex: 'CE' para executar apenas consultas de CE."
                        },
                        "executar_todas": {
                            "type": "boolean",
                            "description": "Se True, executa todas as consultas aprovadas (ou do tipo especificado em tipo_consulta). Padrão: False.",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "baixar_nomenclatura_ncm",
                "description": "📥 Baixa e atualiza a tabela de NCMs (Nomenclatura Comum do Mercosul) do Portal Único Siscomex. Use esta função quando o usuário pedir para 'baixar nomenclatura NCM', 'atualizar tabela NCM', 'sincronizar NCM', 'popular NCM', 'baixar classificação fiscal', 'atualizar classificação fiscal'. ⚠️ IMPORTANTE: Esta operação pode levar vários minutos (o arquivo é grande). O usuário será informado sobre o progresso. A tabela NCM raramente muda, então esta operação não precisa ser feita frequentemente (mensalmente é suficiente). Esta função faz download do arquivo JSON oficial do Portal Único e popula a tabela classif_cache local.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "forcar_atualizacao": {
                            "type": "boolean",
                            "description": "Se True, força atualização mesmo se já foi atualizada recentemente (últimas 24h). Padrão: False.",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        }
    ]
    
    # ✅ REDUZIR TAMANHO: Se compact=True, encurtar descriptions para reduzir tokens
    if compact:
        for tool in tools:
            if 'function' in tool and 'description' in tool['function']:
                original_desc = tool['function']['description']
                # Encurtar para ~150 caracteres (reduz ~50% do tamanho)
                tool['function']['description'] = _shorten_description(original_desc, max_length=150)
    
    # ✅ NOVO: Tool para verificar fontes de dados disponíveis
    tools.append({
        "type": "function",
        "function": {
            "name": "verificar_fontes_dados",
            "description": "Verifica quais fontes de dados estão disponíveis (SQLite, SQL Server, APIs). Use quando o usuário perguntar sobre disponibilidade de dados, conexão, ou quando uma consulta falhar por falta de acesso. Retorna status de cada fonte e informa se está offline/online.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })
    
    # ✅ NOVO: Tools para consultas analíticas SQL
    tools.append({
        "type": "function",
        "function": {
            "name": "executar_consulta_analitica",
            "description": "Executa uma consulta SQL analítica de forma segura (somente leitura). Use quando o usuário pedir análises, rankings, agregações ou relatórios que precisem de SQL. A query será validada e executada apenas se for SELECT seguro. LIMIT será aplicado automaticamente se não especificado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "Query SQL a executar (deve ser SELECT). Exemplo: 'SELECT processo_referencia, COUNT(*) as total FROM processos_kanban GROUP BY processo_referencia LIMIT 10'"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limite de resultados (opcional, padrão: 100, máximo: 1000)",
                        "minimum": 1,
                        "maximum": 1000
                    }
                },
                "required": ["sql"]
            }
        }
    })

    # ✅ NOVO: Tool para vendas no legado Make/Spalla (ex.: "quanto vendi de alho em janeiro?")
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_vendas_make",
            "description": "Consulta vendas no SQL Server legado (Make/Spalla) por período, com filtro opcional por termo (produto/serviço) e quebra por centro de custo/tipo de operação. Use para perguntas do tipo: 'quanto vendi de alho em janeiro?', 'quanto vendemos de rastreador hoje?', 'vendas por período'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "inicio": {
                        "type": "string",
                        "description": "Data inicial inclusiva (YYYY-MM-DD). Ex: 2025-01-01"
                    },
                    "fim": {
                        "type": "string",
                        "description": "Data final exclusiva (YYYY-MM-DD). Ex: 2025-02-01"
                    },
                    "periodo_mes": {
                        "type": "string",
                        "description": "Alternativa a inicio/fim: mês no formato YYYY-MM. Ex: 2025-01"
                    },
                    "apenas_hoje": {
                        "type": "boolean",
                        "description": "Se True, consulta apenas hoje (hoje até amanhã).",
                        "default": False
                    },
                    "termo": {
                        "type": "string",
                        "description": "Termo para filtrar produto/serviço (best-effort em centro de custo e tipo de operação). Ex: 'alho', 'rastreador'."
                    },
                    "venda_td_des_like": {
                        "type": "array",
                        "description": "Heurística do que conta como venda: lista de substrings para filtrar em TD_DES (ex.: ['VENDA','FATUR','NF']).",
                        "items": {"type": "string"}
                    },
                    "granularidade": {
                        "type": "string",
                        "description": "Agrupar por mês ou dia: 'mes' | 'dia'.",
                        "default": "mes"
                    },
                    "top": {
                        "type": "integer",
                        "description": "Limite de linhas na resposta (padrão: 50).",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 50
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO: Descoberta de schema (NF/cliente/itens) no legado Make/Spalla
    tools.append({
        "type": "function",
        "function": {
            "name": "inspecionar_schema_nf_make",
            "description": "Inspeciona o schema do legado (Make/Spalla) para descobrir onde estão campos de NF (número/chave), cliente e possíveis tabelas de itens/produtos. Use quando você precisar ajustar a definição de 'vendas por NF' ou quando a coluna de NF/cliente não for encontrada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "top": {
                        "type": "integer",
                        "description": "Limite de tabelas sugeridas a listar (padrão: 80).",
                        "minimum": 10,
                        "maximum": 200,
                        "default": 80
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO: Vendas por NF (nível documento)
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_vendas_nf_make",
            "description": "Consulta vendas por NF no SQL Server legado (Make/Spalla): data, número NF (best-effort), cliente (se existir), total da NF e centro de custo. Use para perguntas do tipo: 'vendas por NF em janeiro', 'quanto vendemos de alho em janeiro por NF', 'liste as NFs de venda hoje'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "inicio": {
                        "type": "string",
                        "description": "Data inicial inclusiva (YYYY-MM-DD). Ex: 2025-01-01"
                    },
                    "fim": {
                        "type": "string",
                        "description": "Data final exclusiva (YYYY-MM-DD). Ex: 2025-02-01"
                    },
                    "periodo_mes": {
                        "type": "string",
                        "description": "Alternativa a inicio/fim: mês no formato YYYY-MM. Ex: 2025-01"
                    },
                    "apenas_hoje": {
                        "type": "boolean",
                        "description": "Se True, consulta apenas hoje (hoje até amanhã).",
                        "default": False
                    },
                    "termo": {
                        "type": "string",
                        "description": "Termo para filtrar (best-effort em centro de custo e tipo de operação). Ex: 'alho', 'rastreador'."
                    },
                    "venda_td_des_like": {
                        "type": "array",
                        "description": "Heurística do que conta como venda: lista de substrings para filtrar em TD_DES (ex.: ['VENDA','FATUR','NF']).",
                        "items": {"type": "string"}
                    },
                    "top": {
                        "type": "integer",
                        "description": "Limite de linhas na resposta (padrão: 80).",
                        "minimum": 1,
                        "maximum": 500,
                        "default": 80
                    },
                    "modo": {
                        "type": "string",
                        "description": "Modo de saída. Use 'cobranca' para listar apenas NFs em aberto e VENCIDAS (inadimplência) com status e dias em atraso.",
                        "enum": ["normal", "cobranca"],
                        "default": "normal"
                    },
                    "somente_vencidas": {
                        "type": "boolean",
                        "description": "Se True, filtra apenas NFs em aberto cujo vencimento já passou (atrasadas). No modo 'cobranca' isso é implicitamente True.",
                        "default": False
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (28/01/2026): Filtrar relatório de vendas salvo (sem reconsultar SQL)
    tools.append({
        "type": "function",
        "function": {
            "name": "filtrar_relatorio_vendas",
            "description": "🧾🔎 Filtra/refina o ÚLTIMO relatório de vendas por NF que já está na tela (salvo com [REPORT_META:...]) sem reconsultar o SQL Server. Use para follow-ups como: 'agora filtra só o cliente X', 'só devolução', 'dia 22', 'só ICMS/DOC', 'empresa Queimados', 'ordena por valor', 'top 10'. ⚠️ IMPORTANTE: isso aplica filtros nas linhas já carregadas e recalcula A/B/A-B (vendas brutas, devoluções e líquido). Se houver múltiplos relatórios, passe report_id explicitamente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "description": "Opcional: ID do relatório base (ex: rel_20260128_183012). Se omitido, usa o last_visible do domínio vendas."
                    },
                    "cliente": {
                        "type": "string",
                        "description": "Filtra por cliente (contains, case-insensitive). Ex: 'AC BARBEITO'."
                    },
                    "empresa": {
                        "type": "string",
                        "description": "Filtra por empresa vendedora (contains, case-insensitive)."
                    },
                    "operacao": {
                        "type": "string",
                        "description": "Filtra por tipo de operação (contains em descrição). Ex: 'Comissão', 'Nacionalização', 'Devolução'."
                    },
                    "data": {
                        "type": "string",
                        "description": "Filtra por data específica (YYYY-MM-DD ou DD/MM/YYYY)."
                    },
                    "inicio": {
                        "type": "string",
                        "description": "Filtra por data mínima inclusiva (YYYY-MM-DD)."
                    },
                    "fim": {
                        "type": "string",
                        "description": "Filtra por data máxima exclusiva (YYYY-MM-DD)."
                    },
                    "apenas_devolucao": {
                        "type": "boolean",
                        "description": "Se True, mantém apenas devoluções.",
                        "default": False
                    },
                    "apenas_icms": {
                        "type": "boolean",
                        "description": "Se True, mantém apenas DOC/ICMS.",
                        "default": False
                    },
                    "min_valor": {
                        "type": "number",
                        "description": "Valor mínimo (total_nf) para filtrar."
                    },
                    "max_valor": {
                        "type": "number",
                        "description": "Valor máximo (total_nf) para filtrar."
                    },
                    "ordenar_por": {
                        "type": "string",
                        "description": "Ordenação: 'data' | 'valor' | 'nf'.",
                        "enum": ["data", "valor", "nf"],
                        "default": "data"
                    },
                    "ordem": {
                        "type": "string",
                        "description": "Ordem: 'asc' | 'desc'.",
                        "enum": ["asc", "desc"],
                        "default": "desc"
                    },
                    "top": {
                        "type": "integer",
                        "description": "Limite de linhas após filtrar (ex: top 10).",
                        "minimum": 1,
                        "maximum": 500
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (28/01/2026): Curva ABC sobre relatório de vendas salvo (sem reconsultar SQL)
    tools.append({
        "type": "function",
        "function": {
            "name": "curva_abc_vendas",
            "description": "📊 Curva ABC sobre o relatório de vendas por NF que já está na tela (salvo com [REPORT_META:...]) sem reconsultar o SQL Server. Use para: 'faz curva ABC', 'curva abc por cliente', 'abc por centro', 'abc por empresa'. Calcula em cima do líquido por grupo (vendas - devoluções), excluindo DOC/ICMS e operações excluídas (ex.: comissão).",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "description": "Opcional: ID do relatório base (ex: rel_20260128_214212). Se omitido, usa o last_visible do domínio vendas."
                    },
                    "agrupar_por": {
                        "type": "string",
                        "description": "Dimensão para ABC: 'cliente' | 'centro' | 'empresa' | 'operacao'.",
                        "enum": ["cliente", "centro", "empresa", "operacao"],
                        "default": "cliente"
                    },
                    "a_pct": {
                        "type": "number",
                        "description": "Corte da classe A (padrão 0.80).",
                        "default": 0.8
                    },
                    "b_pct": {
                        "type": "number",
                        "description": "Corte da classe B (padrão 0.95).",
                        "default": 0.95
                    },
                    "top": {
                        "type": "integer",
                        "description": "Quantos grupos mostrar no output (padrão 30).",
                        "minimum": 5,
                        "maximum": 200,
                        "default": 30
                    },
                    "min_total": {
                        "type": "number",
                        "description": "Opcional: ignora grupos com líquido abaixo desse valor."
                    },
                    "incluir_outros": {
                        "type": "boolean",
                        "description": "Se True, agrega o restante como 'Outros'.",
                        "default": True
                    }
                },
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "salvar_consulta_personalizada",
            "description": "Salva uma consulta SQL ajustada como relatório reutilizável. Use quando o usuário pedir para salvar uma consulta que funcionou bem. Exemplo: 'salva essa consulta como Atrasos críticos por cliente'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_exibicao": {
                        "type": "string",
                        "description": "Nome amigável do relatório (ex: 'Atrasos críticos por cliente no ano')"
                    },
                    "slug": {
                        "type": "string",
                        "description": "Identificador único em snake_case (ex: 'atrasos_criticos_cliente_ano')"
                    },
                    "descricao": {
                        "type": "string",
                        "description": "Descrição do que o relatório faz"
                    },
                    "sql": {
                        "type": "string",
                        "description": "Query SQL final que funcionou (pode conter placeholders como :ano, :min_dias)"
                    },
                    "parametros": {
                        "type": "array",
                        "description": "Lista de parâmetros esperados (opcional). Ex: [{'nome': 'ano', 'tipo': 'int'}, {'nome': 'min_dias', 'tipo': 'int'}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "nome": {"type": "string"},
                                "tipo": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["nome_exibicao", "slug", "descricao", "sql"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_consulta_personalizada",
            "description": "Busca uma consulta salva baseada no texto do pedido do usuário. Use quando o usuário pedir para 'rodar aquele relatório' ou mencionar um relatório salvo anteriormente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "texto_pedido_usuario": {
                        "type": "string",
                        "description": "Texto da pergunta do usuário (ex: 'Roda aquele relatório de atrasos críticos por cliente em 2025')"
                    }
                },
                "required": ["texto_pedido_usuario"]
            }
        }
    })
    
    # ✅ NOVO: Tool para salvar regras aprendidas
    tools.append({
        "type": "function",
        "function": {
            "name": "salvar_regra_aprendida",
            "description": "Salva uma regra ou definição aprendida do usuário. Use quando o usuário explicar como fazer algo, definir um campo, dar uma instrução que deve ser lembrada, ou criar mapeamento de termos. Exemplos: 1) 'usar campo destfinal como confirmação de chegada' → salva regra de campo. 2) 'o ALH vai ser alho' ou 'Diamond vai ser DMD' → salva mapeamento cliente→categoria (tipo_regra='cliente_categoria', contexto='normalizacao_cliente', nome_regra='ALH → ALHO' ou 'Diamond → DMD', aplicacao_texto='ALH → ALHO' ou 'Diamond → DMD'). Para mapeamentos cliente→categoria, SEMPRE use tipo_regra='cliente_categoria' e contexto='normalizacao_cliente'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_regra": {
                        "type": "string",
                        "description": "Tipo da regra: 'campo_definicao', 'regra_negocio', 'preferencia_usuario', etc."
                    },
                    "contexto": {
                        "type": "string",
                        "description": "Contexto onde se aplica: 'chegada_processos', 'analise_vdm', 'filtros_gerais', etc."
                    },
                    "nome_regra": {
                        "type": "string",
                        "description": "Nome amigável da regra (ex: 'destfinal como confirmação de chegada')"
                    },
                    "descricao": {
                        "type": "string",
                        "description": "Descrição completa da regra"
                    },
                    "aplicacao_sql": {
                        "type": "string",
                        "description": "Como aplicar em SQL (ex: 'WHERE data_destino_final IS NOT NULL')"
                    },
                    "aplicacao_texto": {
                        "type": "string",
                        "description": "Como aplicar em texto/linguagem natural"
                    },
                    "exemplo_uso": {
                        "type": "string",
                        "description": "Exemplo de quando usar essa regra"
                    }
                },
                "required": ["tipo_regra", "contexto", "nome_regra", "descricao"]
            }
        }
    })
    
    # ✅ Tools para envio de emails
    tools.append({
        "type": "function",
        "function": {
            "name": "enviar_email",
            "description": "📧 ENVIAR EMAIL SIMPLES (APENAS PARA CASOS MUITO ESPECÍFICOS): ⚠️⚠️⚠️ NÃO USE ESTA FUNÇÃO para emails personalizados ou quando o usuário pedir para 'montar', 'preparar' ou 'criar' um email. Use apenas quando o usuário pedir explicitamente para 'enviar email' com conteúdo JÁ FORNECIDO COMPLETO. ⚠️⚠️⚠️ CRÍTICO: Esta função SEMPRE mostra preview e pede confirmação antes de enviar. Use sempre 'enviar_email_personalizado' para emails personalizados. ⚠️⚠️⚠️ REGRA OBRIGATÓRIA: NUNCA envie email sem confirmação do usuário. Sempre mostre preview primeiro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destinatario": {
                        "type": "string",
                        "description": "Email do destinatário (ex: 'helenomaffra@gmail.com')"
                    },
                    "assunto": {
                        "type": "string",
                        "description": "Assunto do email (ex: 'Aviso de Não Comparecimento à Reunião')"
                    },
                    "corpo": {
                        "type": "string",
                        "description": "Corpo/mensagem do email em texto. Pode incluir quebras de linha e formatação básica."
                    }
                },
                "required": ["destinatario", "assunto", "corpo"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "enviar_relatorio_email",
            "description": "📊 ENVIAR RELATÓRIO DE PROCESSOS POR EMAIL: Use APENAS quando a última resposta contém [REPORT_META:...] OU quando o usuário pedir para enviar um relatório que foi gerado/filtrado anteriormente. Esta função envia relatórios de processos/importações (ex: 'O QUE TEMOS PRA HOJE', 'FECHAMENTO DO DIA', 'DUIMPs EM ANÁLISE', relatórios filtrados por categoria). ⚠️ REGRA CRÍTICA: Se última resposta tem [REPORT_META:...] OU se o usuário disse 'envie esse relatorio' após ver um relatório → use esta função. Se NÃO tem [REPORT_META:...] e é email personalizado → use enviar_email_personalizado. O sistema detecta automaticamente qual relatório enviar usando last_visible_report_id. Sempre mostre preview primeiro (confirmar_envio=false).",
            "parameters": {
                "type": "object",
                "properties": {
                    "destinatario": {
                        "type": "string",
                        "description": "Email do destinatário (ex: 'helenomaffra@gmail.com'). 🚨🚨🚨 CRÍTICO: Se não fornecido e não houver email padrão, PERGUNTE ao usuário antes de chamar a função. É MELHOR PERGUNTAR do que enviar para email errado."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Categoria do resumo (opcional, ex: 'MV5', 'ALH', 'VDM'). Use quando o usuário mencionar categoria específica, como 'resumo mv5 por email'."
                    },
                    "tipo_relatorio": {
                        "type": "string",
                        "enum": ["resumo", "fechamento", "briefing", "dashboard", "relatorio"],
                        "description": "Tipo de relatório a enviar. Use 'resumo' para 'o que temos pra hoje' ou 'fechamento' para 'fechamento do dia'/'resumo geral'. Padrão: 'resumo'.",
                        "default": "resumo"
                    },
                    "modal": {
                        "type": "string",
                        "enum": ["Marítimo", "Aéreo"],
                        "description": "Filtro opcional por modal (Marítimo ou Aéreo)."
                    },
                    "apenas_pendencias": {
                        "type": "boolean",
                        "description": "Se True, envia apenas pendências. Padrão: False.",
                        "default": False
                    }
                },
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "ler_emails",
            "description": "📥 LER EMAILS: Lê emails da caixa de entrada via Microsoft Graph API. Use quando o usuário pedir para ler, verificar, ver ou consultar emails. Exemplos: 'ver email', 'ler meus emails', 'verificar emails não lidos', 'mostrar últimos emails', 'quais emails chegaram?', 'ver emails'. Esta função lê emails da caixa de entrada configurada e retorna lista de emails com assunto, remetente, data e conteúdo. 🚨 CRÍTICO: Se o usuário disser apenas 'ver email' ou 'ver emails', SEMPRE chame esta função. NÃO responda com outras informações ou perguntas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de emails para retornar. Padrão: 10.",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "apenas_nao_lidos": {
                        "type": "boolean",
                        "description": "Se True, retorna apenas emails não lidos. Padrão: False (todos os emails).",
                        "default": False
                    },
                    "max_dias": {
                        "type": "integer",
                        "description": "Número máximo de dias para buscar emails (padrão: 7).",
                        "default": 7,
                        "minimum": 1,
                        "maximum": 30
                    }
                },
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "obter_detalhes_email",
            "description": "📧 OBTER DETALHES DE EMAIL: Obtém detalhes completos de um email específico. Use quando o usuário pedir para ver detalhes, ler ou mostrar conteúdo completo de um email. Exemplos: 'detalhe email 7', 'ler email 1', 'mostrar email 3', 'ver email 2'. Esta função busca o email pelo ID (obtido da lista de ler_emails) e retorna assunto, remetente, destinatários, data, corpo completo e anexos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID da mensagem (obtido de ler_emails). Se o usuário disser 'email 7' ou 'detalhe email 7', use o ID do email número 7 da lista retornada por ler_emails."
                    },
                    "email_index": {
                        "type": "integer",
                        "description": "Índice numérico do email na lista (começando em 1). Use quando o usuário disser 'email 1', 'email 7', 'detalhe email 8', etc. Se fornecido, o sistema buscará o ID do email na lista anterior. PREFIRA usar email_index quando o usuário mencionar um número (ex: 'email 8', 'detalhe email 3')."
                    }
                },
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "responder_email",
            "description": "📧 RESPONDER EMAIL: Responde a um email específico via Microsoft Graph API. Use quando o usuário pedir para responder um email. Exemplos: 'responder o email 1', 'responder email de João', 'responder esse email dizendo que...'. Esta função responde ao email original mantendo o histórico da conversa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "ID da mensagem original (obtido de ler_emails). Se o usuário disser 'email 1' ou 'primeiro email', use o ID do primeiro email da lista retornada por ler_emails."
                    },
                    "resposta": {
                        "type": "string",
                        "description": "Conteúdo da resposta (texto ou HTML)."
                    }
                },
                "required": ["message_id", "resposta"]
            }
        }
    })
    
    # ✅ NOVO: Email personalizado com preview/confirmação
    tools.append({
        "type": "function",
        "function": {
            "name": "enviar_email_personalizado",
            "description": "📧 ENVIAR EMAIL PERSONALIZADO: Use quando o usuário pedir para enviar email com conteúdo customizado. ⚠️ REGRA SIMPLES: Se última resposta NÃO tem [REPORT_META:...] → use esta função. Se tem [REPORT_META:...] → use enviar_relatorio_email. Casos válidos: emails pessoais, informações de NCM/alíquotas, informações de processo específico (sem [REPORT_META:...]), emails formais/pessoais. Use APENAS o conteúdo da última resposta do histórico. Sempre mostre preview primeiro (confirmar_envio=false).",
            "parameters": {
                "type": "object",
                "properties": {
                    "destinatarios": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de emails dos destinatários (ex: ['joao@exemplo.com']). OBRIGATÓRIO."
                    },
                    "assunto": {
                        "type": "string",
                        "description": "Assunto do email. OBRIGATÓRIO. Se o usuário não especificar, gere um assunto apropriado baseado no conteúdo."
                    },
                    "conteudo": {
                        "type": "string",
                        "description": "Conteúdo do email em texto ou HTML. OBRIGATÓRIO. 🚨🚨🚨 CRÍTICO - USAR APENAS A ÚLTIMA RESPOSTA DO HISTÓRICO: Quando o usuário pedir 'envia email do [processo]' ou 'mande esse relatorio', você DEVE usar APENAS o conteúdo da ÚLTIMA RESPOSTA no histórico. NÃO use informações de conversas antigas. REGRAS: 1) Se última resposta contém PROCESSO ESPECÍFICO (ex: GPS.0010/24, ALH.0166/25) → COPIE EXATAMENTE o conteúdo completo da última resposta sobre o processo. 2) Se última resposta contém NCM/alíquotas → inclua NCM completo, confiança, NESH COMPLETA, TODAS as alíquotas. 3) NÃO invente informações - use APENAS o que está na última resposta. 4) Se não houver contexto claro, pergunte ao usuário. ✍️✍️✍️ CRÍTICO - ASSINATURA: Se o usuário pedir 'assine [nome]', 'assinar como [nome]' ou 'assinar [nome]', o conteúdo do email DEVE terminar com 'Atenciosamente,\\n[nome]' (sem incluir a frase 'assine [nome]' no corpo). Se não especificar assinatura, termine com 'Atenciosamente,\\nmAIke – Assistente de COMEX\\nMake Consultores'. FORMATO: Use quebras de linha reais (\\n). Formate profissionalmente com tabelas para alíquotas."
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de emails em cópia (opcional)."
                    },
                    "bcc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de emails em cópia oculta (opcional)."
                    },
                    "confirmar_envio": {
                        "type": "boolean",
                        "description": "⚠️⚠️⚠️ CRÍTICO: Se false ou não fornecido, apenas mostra o preview e pede confirmação. Se true, confirma e envia o email. NUNCA defina como true na primeira chamada - sempre mostre o preview primeiro e aguarde o usuário confirmar.",
                        "default": False
                    }
                },
                "required": ["destinatarios", "assunto", "conteudo"]
            }
        }
    })
    
    # ✅ NOVO (09/01/2026): Tool opcional para melhorar email draft (sistema de versões)
    tools.append({
        "type": "function",
        "function": {
            "name": "melhorar_email_draft",
            "description": "📧 MELHORAR EMAIL DRAFT: Melhora/elabora um email que está em preview. Use quando o usuário pedir para 'melhorar este email', 'elaborar melhor', 'reescrever', 'refinar', 'mais formal', 'mais carinhoso', etc. Esta função cria uma nova revisão do email com o conteúdo melhorado. ⚠️ IMPORTANTE: Esta tool é OPCIONAL - o sistema também funciona sem ela (usando extração automática). Use quando quiser garantir que a melhoria seja salva corretamente no draft.",
            "parameters": {
                "type": "object",
                "properties": {
                    "draft_id": {
                        "type": "string",
                        "description": "ID do draft a melhorar (obtido do estado do email em preview). Se não fornecido, o sistema tentará encontrar automaticamente."
                    },
                    "assunto": {
                        "type": "string",
                        "description": "Novo assunto melhorado (opcional, mantém anterior se não fornecido)."
                    },
                    "conteudo": {
                        "type": "string",
                        "description": "Novo conteúdo melhorado (opcional, mantém anterior se não fornecido). Deve ser o email completo melhorado conforme pedido pelo usuário."
                    },
                    "instrucoes": {
                        "type": "string",
                        "description": "Instruções de como melhorar (ex: 'mais formal', 'mais carinhoso', 'mais elaborado'). Usado apenas para contexto."
                    }
                },
                "required": []
            }
        }
    })
    
    # Adicionar tools de legislação
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_legislacao",
            "description": "Busca um ato normativo específico (IN, Lei, Decreto, etc.) no banco de dados. Use quando o usuário perguntar sobre uma legislação específica, quiser saber informações básicas, ou perguntar 'do que fala', 'sobre o que é', 'o que trata' uma legislação. Exemplos: 'buscar IN 1984/2020', 'do que fala a IN 1984?', 'o que é a IN 680?', 'mostre a Lei 12345/2020'. Retorna informações básicas e, se o usuário perguntar sobre o conteúdo, inclui resumo dos primeiros artigos. IMPORTANTE: A legislação deve ter sido importada anteriormente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_ato": {
                        "type": "string",
                        "description": "Tipo do ato normativo (ex: 'IN', 'Lei', 'Decreto', 'Portaria', 'Instrução Normativa')",
                        "enum": ["IN", "Lei", "Lei Complementar", "Decreto", "Portaria", "Instrução Normativa"]
                    },
                    "numero": {
                        "type": "string",
                        "description": "Número do ato (ex: '680', '12345')"
                    },
                    "ano": {
                        "type": "integer",
                        "description": "Ano do ato (ex: 2006, 2024). Opcional, mas recomendado para maior precisão."
                    },
                    "sigla_orgao": {
                        "type": "string",
                        "description": "Sigla do órgão emissor (ex: 'RFB', 'MF', 'MDIC'). Opcional."
                    },
                    "pergunta": {
                        "type": "string",
                        "description": "Pergunta original do usuário (opcional). Use para detectar se o usuário quer saber sobre o conteúdo da legislação (ex: 'do que fala', 'sobre o que é'). Se fornecido, a resposta incluirá resumo dos primeiros artigos."
                    }
                },
                "required": ["tipo_ato", "numero"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_trechos_legislacao",
            "description": "🔍 Busca trechos específicos de uma legislação por palavra-chave OU busca um artigo completo por número. Use quando: 1) o usuário perguntar sobre um tópico dentro de uma legislação específica (ex: 'o que a IN 680 fala sobre canal?', 'Decreto 6759 sobre multas'); 2) o usuário pedir um artigo específico por número (ex: 'detalhe o art 725 do decreto 6759', 'mostre o artigo 64', 'artigo 702 do decreto 6759', 'qual o art 725?', 'detalhe art 725'). ⚠️ CRÍTICO: Se o usuário pedir um artigo específico (ex: 'art 725', 'artigo 64', 'detalhe art 725'), passe APENAS o número do artigo como único termo em 'termos' (ex: ['725'], ['64']). Se for busca por palavra-chave, extraia os termos principais (ex: ['multas'], ['canal']). A legislação deve ter sido importada anteriormente. Retorna o artigo completo com todos os parágrafos e incisos se for busca por número, ou trechos relevantes se for busca por palavra-chave.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_ato": {
                        "type": "string",
                        "description": "Tipo do ato normativo (ex: 'IN', 'Lei', 'Decreto')",
                        "enum": ["IN", "Lei", "Lei Complementar", "Decreto", "Portaria", "Instrução Normativa"]
                    },
                    "numero": {
                        "type": "string",
                        "description": "Número do ato (ex: '680', '12345')"
                    },
                    "termos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de palavras-chave para buscar nos trechos OU número do artigo específico. Se o usuário pedir um artigo específico (ex: 'art 725', 'artigo 64'), passe APENAS o número como único item (ex: ['725'], ['64']). Se for busca por palavra-chave, extraia os termos principais (ex: ['canal', 'conferência'], ['multas'], ['base', 'cálculo'])"
                    },
                    "ano": {
                        "type": "integer",
                        "description": "Ano do ato (opcional, mas recomendado)"
                    },
                    "sigla_orgao": {
                        "type": "string",
                        "description": "Sigla do órgão emissor (opcional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de trechos a retornar (padrão: 10)",
                        "default": 10
                    }
                },
                "required": ["tipo_ato", "numero", "termos"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_em_todas_legislacoes",
            "description": "🔍 Busca genérica em TODAS as legislações do banco de dados por palavra-chave (SQLite local). ⚠️ IMPORTANTE: Esta função busca por palavras-chave exatas no banco local. Para perguntas conceituais (ex: 'o que fala sobre perdimento?', 'explique sobre multas?'), use buscar_legislacao_assistants PRIMEIRO (ela usa RAG e busca semanticamente). Use esta função apenas quando: 1) O usuário mencionar uma legislação específica (ex: 'IN 680') - então use buscar_trechos_legislacao. 2) O usuário pedir um artigo específico (ex: 'art 725 do decreto 6759') - então use buscar_trechos_legislacao. 3) Quando buscar_legislacao_assistants não estiver disponível ou falhar. ⚠️ PRIORIDADE BAIXA: Para perguntas conceituais, SEMPRE priorize buscar_legislacao_assistants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de palavras-chave para buscar em todas as legislações (ex: ['multas'], ['canal', 'conferência'], ['despacho', 'aduaneiro']). Extraia os termos principais da pergunta do usuário."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Número máximo de trechos a retornar por legislação (padrão: 20). Se houver muitas legislações, pode retornar muitos resultados.",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "incluir_revogados": {
                        "type": "boolean",
                        "description": "Se True, inclui trechos revogados nos resultados. Padrão: False.",
                        "default": False
                    }
                },
                "required": ["termos"]
            }
        }
    })
    
    # ✅ NOVO: Tool para buscar legislação usando Assistants API com File Search (RAG)
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_legislacao_responses",
            "description": "🔍🔍🔍 BUSCA DE LEGISLAÇÃO COM RAG (Responses API) - PRIORIDADE MÁXIMA para perguntas conceituais sobre legislação. Use SEMPRE esta função para perguntas conceituais sobre legislação (ex: 'o que fala sobre perdimento?', 'explique sobre multas?', 'quais as regras de importação?'). Esta função usa Responses API (nova API recomendada) para buscar semanticamente em legislações, encontrando informações mesmo quando não há palavras-chave exatas. ⚠️ IMPORTANTE: Esta função tem PRIORIDADE MÁXIMA para perguntas conceituais. Use buscar_em_todas_legislacoes apenas quando: 1) O usuário mencionar uma legislação específica (ex: 'IN 680') - então use buscar_trechos_legislacao. 2) O usuário pedir um artigo específico (ex: 'art 725 do decreto 6759') - então use buscar_trechos_legislacao. 3) Quando esta função não estiver disponível ou falhar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pergunta": {
                        "type": "string",
                        "description": "Pergunta do usuário sobre legislação (ex: 'o que fala sobre perdimento?', 'qual a base legal para multas?', 'explique sobre canal de conferência')"
                    }
                },
                "required": ["pergunta"]
            }
        }
    })
    
    # ✅ NOVO: Tool para buscar preview de legislação (NÃO salva)
    tools.append({
        "type": "function",
        "function": {
            "name": "importar_legislacao_preview",
            "description": "🔍 Busca uma legislação na internet e mostra preview SEM salvar. Use quando o usuário pedir para 'importar', 'baixar', 'buscar', 'trazer' uma legislação (ex: 'importar IN 680/2006 da RFB', 'baixar legislação da IN 680/06', 'trazer IN 680 da RFB', 'busque o Decreto 6759/2009'). Esta função: 1) Busca URL oficial usando IA, 2) Baixa e extrai conteúdo, 3) Parseia em artigos/trechos, 4) Retorna preview com resumo (NÃO salva no banco). IMPORTANTE: Após mostrar preview, SEMPRE pergunte ao usuário se quer salvar usando confirmar_importacao_legislacao.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_ato": {
                        "type": "string",
                        "description": "Tipo do ato normativo (ex: 'IN', 'Lei', 'Decreto', 'Portaria')",
                        "enum": ["IN", "Lei", "Lei Complementar", "Decreto", "Portaria", "Instrução Normativa"]
                    },
                    "numero": {
                        "type": "string",
                        "description": "Número do ato (ex: '680', '6759', '12345')"
                    },
                    "ano": {
                        "type": "integer",
                        "description": "Ano do ato (ex: 2006, 2009, 2024). Obrigatório."
                    },
                    "sigla_orgao": {
                        "type": "string",
                        "description": "Sigla do órgão emissor (ex: 'RFB', 'MF', 'PR', 'MDIC'). Opcional."
                    },
                    "titulo_oficial": {
                        "type": "string",
                        "description": "Título ou ementa do ato (opcional)"
                    }
                },
                "required": ["tipo_ato", "numero", "ano"]
            }
        }
    })
    
    # ✅ NOVO: Tool para confirmar e salvar legislação após preview
    tools.append({
        "type": "function",
        "function": {
            "name": "confirmar_importacao_legislacao",
            "description": "💾 Confirma e salva uma legislação que foi visualizada em preview. Use APENAS quando o usuário confirmar explicitamente que quer gravar (ex: 'sim, salvar', 'confirmar importação', 'gravar', 'salvar no banco'). Esta função grava a legislação no banco de dados para consultas futuras. IMPORTANTE: Só use esta função após o usuário ter visto o preview e confirmado que quer salvar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_ato": {
                        "type": "string",
                        "description": "Tipo do ato normativo",
                        "enum": ["IN", "Lei", "Lei Complementar", "Decreto", "Portaria", "Instrução Normativa"]
                    },
                    "numero": {
                        "type": "string",
                        "description": "Número do ato"
                    },
                    "ano": {
                        "type": "integer",
                        "description": "Ano do ato"
                    },
                    "sigla_orgao": {
                        "type": "string",
                        "description": "Sigla do órgão emissor (opcional)"
                    },
                    "titulo_oficial": {
                        "type": "string",
                        "description": "Título ou ementa (opcional)"
                    },
                    "url": {
                        "type": "string",
                        "description": "URL encontrada no preview (opcional, mas recomendado para evitar buscar novamente)"
                    }
                },
                "required": ["tipo_ato", "numero", "ano"]
            }
        }
    })
    
    # ✅ Tool legada: buscar_e_importar_legislacao (mantida para compatibilidade, mas prefira usar importar_legislacao_preview + confirmar)
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_e_importar_legislacao",
            "description": "🚀 [LEGADO] Busca e importa uma legislação automaticamente SEM preview. Use apenas se o usuário pedir explicitamente para 'buscar e gravar direto' ou 'importar sem perguntar'. Para fluxo normal, prefira usar importar_legislacao_preview primeiro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_ato": {
                        "type": "string",
                        "description": "Tipo do ato normativo",
                        "enum": ["IN", "Lei", "Lei Complementar", "Decreto", "Portaria", "Instrução Normativa"]
                    },
                    "numero": {
                        "type": "string",
                        "description": "Número do ato"
                    },
                    "ano": {
                        "type": "integer",
                        "description": "Ano do ato"
                    },
                    "sigla_orgao": {
                        "type": "string",
                        "description": "Sigla do órgão emissor (opcional)"
                    },
                    "titulo_oficial": {
                        "type": "string",
                        "description": "Título ou ementa (opcional)"
                    }
                },
                "required": ["tipo_ato", "numero", "ano"]
            }
        }
    })
    
    # ✅ NOVO: Tool para calcular impostos após consulta TECwin
    tools.append({
        "type": "function",
        "function": {
            "name": "calcular_impostos_ncm",
            "description": "💰💰💰 CALCULAR IMPOSTOS DE IMPORTAÇÃO (PYTHON LOCAL - RÁPIDO E COM EXPLICAÇÕES) - Use SEMPRE esta função quando o usuário pedir para calcular impostos (II, IPI, PIS, COFINS). Esta função é RÁPIDA, SEM CUSTO de API e fornece explicações detalhadas passo a passo quando solicitado. ⚠️ CRÍTICO: Para cálculos simples de PERCENTUAL (ex: 'quanto é 1,5% do CIF?'), use calcular_percentual em vez desta. Exemplos OBRIGATÓRIOS de uso: 'calcule os impostos', 'quanto fica de imposto', 'calcular impostos para carga de X dólares', 'calcule II e IPI', 'quanto pago de imposto com frete de Y', 'calcule os impostos para carga de 10.000 dólares, frete 1.500, seguro 200, cotação 5.5283', 'calcule imposto de 30% para CIF de 30.000 dólares a câmbio de 5,10', 'calcule explicando o imposto de importação de 30% para um cif de 30000 dólares'. 🚨 CRÍTICO: A função aceita: 1) CIF direto (cif_usd) OU custo_usd + frete_usd + seguro_usd separados. 2) Alíquotas fornecidas pelo usuário (aliquotas_ii, aliquotas_ipi, etc.) OU busca do contexto TECwin. Se o usuário fornecer CIF direto ou alíquotas, use esses valores. Se não houver alíquotas no contexto e o usuário não fornecer, informe que é necessário consultar o NCM no TECwin primeiro. 💡 VANTAGENS: Rápido, sem custo de API, previsível. Use para cálculos de impostos simples e rápidos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "custo_usd": {
                        "type": "number",
                        "description": "Valor da mercadoria em USD (VMLE). Use null se o usuário fornecer CIF direto (cif_usd)."
                    },
                    "frete_usd": {
                        "type": "number",
                        "description": "Valor do frete em USD. Use null se o usuário fornecer CIF direto (cif_usd)."
                    },
                    "seguro_usd": {
                        "type": "number",
                        "description": "Valor do seguro em USD. Se o usuário não fornecer, use 0 (zero) como padrão. Use null se o usuário fornecer CIF direto (cif_usd)."
                    },
                    "cif_usd": {
                        "type": "number",
                        "description": "✅ NOVO: CIF direto em USD. Se o usuário fornecer CIF diretamente (ex: 'CIF de 30.000 dólares'), use este parâmetro e deixe custo_usd, frete_usd, seguro_usd como null."
                    },
                    "cotacao_ptax": {
                        "type": "number",
                        "description": "Cotação PTAX (R$ / USD). Se o usuário não fornecer, use null e pergunte ou busque a cotação do dia."
                    },
                    "aliquotas_ii": {
                        "type": "number",
                        "description": "✅ NOVO: Alíquota de II (Imposto de Importação) em percentual (ex: 30 para 30%). Se o usuário fornecer alíquota diretamente (ex: 'imposto de 30%'), use este valor em vez de buscar do contexto TECwin."
                    },
                    "aliquotas_ipi": {
                        "type": "number",
                        "description": "✅ NOVO: Alíquota de IPI em percentual. Se o usuário fornecer, use este valor."
                    },
                    "aliquotas_pis": {
                        "type": "number",
                        "description": "✅ NOVO: Alíquota de PIS em percentual. Se o usuário fornecer, use este valor."
                    },
                    "aliquotas_cofins": {
                        "type": "number",
                        "description": "✅ NOVO: Alíquota de COFINS em percentual. Se o usuário fornecer, use este valor."
                    }
                },
                "required": []
            }
        }
    })
    
    # ✅ NOVO: Tool para cálculos simples de percentual
    tools.append({
        "type": "function",
        "function": {
            "name": "calcular_percentual",
            "description": "📊 CALCULAR PERCENTUAL SIMPLES - Use esta função para cálculos simples de percentual que NÃO requerem cotação PTAX ou cálculo de impostos. Exemplos OBRIGATÓRIOS: 'quanto é 1,5% do CIF de 30.000 dólares?', 'calcule 10% de 50.000', 'quanto é 2% de 100.000 dólares?', 'calcule 1,5% de 30.000'. ⚠️ CRÍTICO: Use esta função APENAS para cálculos simples de percentual. Para cálculos de impostos, use calcular_impostos_ncm. Esta função é RÁPIDA e SEM CUSTO.",
            "parameters": {
                "type": "object",
                "properties": {
                    "valor": {
                        "type": "number",
                        "description": "Valor base para calcular o percentual (ex: 30000 para 30.000 dólares)"
                    },
                    "percentual": {
                        "type": "number",
                        "description": "Percentual a calcular (ex: 1.5 para 1,5%, 10 para 10%)"
                    }
                },
                "required": ["valor", "percentual"]
            }
        }
    })
    
    # ✅ NOVO: Tools para integração com Santander Open Banking
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_contas_santander",
            "description": "🏦 LISTAR CONTAS SANTANDER - Use esta função quando o usuário pedir para listar contas bancárias do Santander ou ver quais contas estão disponíveis. Exemplos OBRIGATÓRIOS: 'listar contas do santander', 'quais contas tenho no santander', 'mostrar contas disponíveis', 'contas do banco'. ⚠️ IMPORTANTE: Esta função lista todas as contas disponíveis no Santander Open Banking vinculadas ao certificado digital configurado.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_extrato_santander",
            "description": "📋 CONSULTAR EXTRATO SANTANDER - Use esta função quando o usuário pedir para ver extrato bancário, movimentações, transações do Santander. Exemplos OBRIGATÓRIOS: 'extrato do santander', 'movimentações da conta', 'transações do banco', 'extrato de hoje', 'extrato dos últimos 7 dias', 'extrato de janeiro', 'extrato do dia 30/12/2025', 'extrato de 30/12/25', 'mostrar extrato da conta X'. ⚠️ IMPORTANTE: Se o usuário não fornecer agência/conta, use a primeira conta disponível (chame listar_contas_santander primeiro se necessário). Se não fornecer datas, use últimos 7 dias como padrão. Se fornecer apenas uma data (sem data_fim), usa a mesma data para início e fim (extrato de um dia específico).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Código da agência (4 dígitos, ex: '3003'). Se não fornecido, usa primeira conta disponível."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta (12 dígitos, ex: '000130827180'). Se não fornecido, usa primeira conta disponível."
                    },
                    "statement_id": {
                        "type": "string",
                        "description": "ID da conta no formato AGENCIA.CONTA (ex: '3003.000130827180'). Se fornecido, ignora agencia e conta."
                    },
                    "data": {
                        "type": "string",
                        "description": "Data única no formato YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY ou palavras-chave ('hoje', 'ontem', 'dia X', etc.). Se fornecido sem data_inicio/data_fim, usa a mesma data para início e fim (extrato de um dia específico). Exemplos: '30/12/2025', '2025-12-30', 'dia 30 de dezembro'."
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-01', '01/01/2026', 'hoje'). Se fornecido sem data_fim, usa a mesma data para início e fim (extrato de um dia específico). Se não fornecido, usa 7 dias atrás."
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-06', '06/01/2026', 'hoje'). Se não fornecido e data_inicio foi fornecido, usa a mesma data de data_inicio (extrato de um dia específico). Se não fornecido e data_inicio também não foi fornecido, usa hoje."
                    },
                    "dias": {
                        "type": "integer",
                        "description": "Número de dias para trás (ex: 7 para últimos 7 dias, 30 para últimos 30 dias). Se fornecido, ignora data, data_inicio e data_fim."
                    }
                },
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_saldo_santander",
            "description": "💰 CONSULTAR SALDO SANTANDER - Use esta função quando o usuário pedir para ver saldo da conta, saldo disponível, saldo bloqueado do Santander. Exemplos OBRIGATÓRIOS: 'saldo do santander', 'quanto tem na conta', 'saldo disponível', 'saldo da conta X', 'saldo em 05/01/2026', 'saldo de ontem', 'saldo do dia 10 de janeiro'. ⚠️ IMPORTANTE: Se o usuário não fornecer agência/conta, usa primeira conta disponível. Se fornecer data_referencia, calcula saldo histórico retroativamente (saldo atual - transações após a data).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Código da agência (4 dígitos, ex: '3003'). Se não fornecido, usa primeira conta disponível."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta (12 dígitos, ex: '000130827180'). Se não fornecido, usa primeira conta disponível."
                    },
                    "statement_id": {
                        "type": "string",
                        "description": "ID da conta no formato AGENCIA.CONTA (ex: '3003.000130827180'). Se fornecido, ignora agencia e conta."
                    },
                    "data_referencia": {
                        "type": "string",
                        "description": "Data de referência no formato YYYY-MM-DD (ex: '2026-01-05') para calcular saldo histórico. Se fornecida, calcula o saldo retroativamente usando o saldo atual e subtraindo transações posteriores. Se não fornecida, retorna saldo atual."
                    },
                    "data": {
                        "type": "string",
                        "description": "Alias para data_referencia. Aceita formatos: YYYY-MM-DD, DD/MM/YYYY, 'ontem', 'hoje', 'semana passada', etc. Será convertido para YYYY-MM-DD."
                    }
                },
                "required": []
            }
        }
    })
    
    # ✅ NOVO: Tools para integração com Banco do Brasil - Banco de Dados (prioridade)
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_movimentacoes_bb_bd",
            "description": "📊 CONSULTAR MOVIMENTAÇÕES BB NO BANCO DE DADOS - ✅ PRIORIDADE ALTA: Use SEMPRE esta função quando o usuário pedir lançamentos já sincronizados, movimentações do banco de dados, extratos já importados, ou quando mencionar 'lançamentos do banco', 'movimentações sincronizadas', 'extrato do bd', 'extrato do banco de dados'. Esta função consulta diretamente o SQL Server (tabela MOVIMENTACAO_BANCARIA), sem precisar chamar a API do Banco do Brasil. Exemplos OBRIGATÓRIOS: 'mostrar lançamentos do bb', 'extrato bb do banco de dados', 'movimentações sincronizadas', 'lançamentos já importados', 'extrato bb do bd', 'ver lançamentos do banco', 'mostrar movimentações bb do sql server'. ⚠️ IMPORTANTE: Se o usuário mencionar 'extrato do banco' ou 'do bd' ou 'sincronizados', use SEMPRE esta função. Se mencionar apenas 'extrato bb' sem especificar banco de dados, use consultar_extrato_bb (que consulta a API). Se não fornecer agência/conta, usa valores padrão do .env. Se não fornecer datas, usa últimos 30 dias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Número da agência sem dígito verificador (ex: '1251'). Se não fornecido, usa valor padrão do .env (BB_TEST_AGENCIA)."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta sem dígito verificador (ex: '50483', '43344'). Também aceita '2', 'conta2' ou 'segunda' para usar a segunda conta configurada (BB_TEST_CONTA_2). Se não fornecido, usa a conta padrão (BB_TEST_CONTA)."
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-01', '01/01/2026', 'hoje'). Se não fornecido, usa 30 dias atrás."
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-07', '07/01/2026', 'hoje'). Se não fornecido, usa hoje."
                    },
                    "processo_referencia": {
                        "type": "string",
                        "description": "Filtrar por processo de importação (ex: 'DMD.0083/25'). Opcional."
                    },
                    "tipo_movimentacao": {
                        "type": "string",
                        "description": "Filtrar por tipo de movimentação (ex: 'PIX', 'TRANSFERENCIA', 'PAGAMENTO'). Opcional."
                    },
                    "sinal": {
                        "type": "string",
                        "description": "Filtrar por sinal: '+' para créditos, '-' para débitos. Opcional."
                    },
                    "valor_minimo": {
                        "type": "number",
                        "description": "Valor mínimo da movimentação. Opcional."
                    },
                    "valor_maximo": {
                        "type": "number",
                        "description": "Valor máximo da movimentação. Opcional."
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Limite de resultados (default: 100). Opcional."
                    }
                },
                "required": []
            }
        }
    })
    
    # ✅ NOVO: Tools para integração com Banco do Brasil Extratos API
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_extrato_bb",
            "description": "🏦 CONSULTAR EXTRATO BANCO DO BRASIL - Use SEMPRE esta função quando o usuário pedir para VER/CONSULTAR extrato bancário, movimentações, transações do Banco do Brasil. ⚠️⚠️⚠️ CRÍTICO - NÃO USE PARA ENVIAR POR EMAIL: Esta função é APENAS para CONSULTAR/VISUALIZAR extratos. Se o usuário pedir para ENVIAR relatório por email e a última resposta foi sobre PROCESSOS/IMPORTAÇÕES (não extrato bancário) → use enviar_relatorio_email. Se o usuário pedir para ENVIAR extrato bancário por email → use enviar_email_personalizado. Exemplos OBRIGATÓRIOS: 'extrato do banco do brasil', 'extrato do BB', 'movimentações da conta BB', 'transações do banco do brasil', 'extrato de hoje', 'extrato dos últimos 30 dias', 'extrato de janeiro', 'extrato do dia 30/12/2025', 'extrato de 30/12/25', 'mostrar extrato da conta X do BB', 'extrato do BB conta 2', 'extrato da segunda conta do BB', 'extrato do BB conta 43344'. ⚠️ CRÍTICO: SEMPRE chame esta função quando o usuário mencionar extrato do BB para CONSULTAR/VISUALIZAR, mesmo que não forneça agência/conta. Se não fornecer agência/conta, usa valores padrão do .env (BB_TEST_AGENCIA e BB_TEST_CONTA). Se o usuário mencionar 'conta 2', 'segunda conta' ou 'conta2', passe conta='2' ou conta='segunda' para usar a segunda conta (BB_TEST_CONTA_2). Se o usuário mencionar um número de conta específico (ex: 'conta 43344'), passe esse número diretamente. Se não fornecer datas, retorna últimos 30 dias (padrão da API). Se fornecer apenas uma data (sem data_fim), usa a mesma data para início e fim (extrato de um dia específico). Período máximo: 31 dias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Número da agência sem dígito verificador (ex: '1505'). Se não fornecido, a função retornará uma mensagem pedindo agência e conta."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta sem dígito verificador (ex: '1348', '43344'). Também aceita '2', 'conta2' ou 'segunda' para usar a segunda conta configurada (BB_TEST_CONTA_2). Se não fornecido, usa a conta padrão (BB_TEST_CONTA)."
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-01', '01/01/2026', 'hoje'). Se fornecido sem data_fim, usa a mesma data para início e fim (extrato de um dia específico). Se não fornecido, usa 30 dias atrás (padrão da API)."
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-06', '06/01/2026', 'hoje'). Se não fornecido e data_inicio foi fornecido, usa a mesma data de data_inicio (extrato de um dia específico). Se não fornecido e data_inicio também não foi fornecido, usa hoje."
                    }
                },
                "required": []
            }
        }
    })
    
    # Tool: Gerar PDF Extrato Banco do Brasil
    tools.append({
        "type": "function",
        "function": {
            "name": "gerar_pdf_extrato_bb",
            "description": "📄 GERAR PDF EXTRATO BANCO DO BRASIL - Use esta função quando o usuário pedir para gerar PDF do extrato bancário do Banco do Brasil. Gera PDF no formato contábil padrão (Data, Histórico, Crédito, Débito, Saldo). Exemplos: 'gerar pdf do extrato bb', 'pdf do extrato banco do brasil', 'extrato bb em pdf', 'gerar extrato bb pdf'. ⚠️ IMPORTANTE: Esta função consulta o extrato primeiro e depois gera o PDF. Se não fornecer agência/conta, usa valores padrão do .env. Se não fornecer datas, usa últimos 30 dias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Número da agência sem dígito verificador (ex: '1505'). Se não fornecido, usa valor padrão do .env (BB_TEST_AGENCIA)."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta sem dígito verificador (ex: '1348', '43344'). Também aceita '2', 'conta2' ou 'segunda' para usar a segunda conta configurada (BB_TEST_CONTA_2). Se não fornecido, usa a conta padrão (BB_TEST_CONTA)."
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-01', '01/01/2026', 'hoje'). Se não fornecido, usa 30 dias atrás."
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-06', '06/01/2026', 'hoje'). Se não fornecido, usa hoje."
                    }
                },
                "required": []
            }
        }
    })
    
    # ✅ NOVO (13/01/2026): Tool: Iniciar Pagamento em Lote Banco do Brasil
    tools.append({
        "type": "function",
        "function": {
            "name": "iniciar_pagamento_lote_bb",
            "description": "💰 INICIAR PAGAMENTO EM LOTE BANCO DO BRASIL - Use esta função quando o usuário pedir para pagar múltiplos boletos ou fazer pagamentos em lote no Banco do Brasil. Exemplos: 'pagar boletos em lote no BB', 'fazer pagamento em lote banco do brasil', 'processar pagamentos em lote BB', 'pagar vários boletos de uma vez BB'. ⚠️ IMPORTANTE: Esta função usa a API de Pagamentos em Lote do BB. Requer agência, conta e lista de pagamentos. Cada pagamento deve ter tipo (BOLETO, PIX, TED), valor e dados específicos (código de barras para boleto, chave PIX para PIX, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Número da agência (4 dígitos, ex: '1505'). Obrigatório."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta sem dígito verificador (ex: '1348'). Obrigatório."
                    },
                    "pagamentos": {
                        "type": "array",
                        "description": "Lista de pagamentos. Cada pagamento deve ter: tipo (BOLETO, PIX, TED), valor (float), e dados específicos conforme o tipo.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tipo": {
                                    "type": "string",
                                    "description": "Tipo de pagamento: 'BOLETO', 'PIX' ou 'TED'"
                                },
                                "valor": {
                                    "type": "number",
                                    "description": "Valor do pagamento (ex: 100.50)"
                                },
                                "codigo_barras": {
                                    "type": "string",
                                    "description": "Código de barras (obrigatório para BOLETO, 44 ou 47 dígitos)"
                                },
                                "beneficiario": {
                                    "type": "string",
                                    "description": "Nome do beneficiário (opcional)"
                                },
                                "vencimento": {
                                    "type": "string",
                                    "description": "Data de vencimento YYYY-MM-DD (opcional, para BOLETO)"
                                },
                                "chave_pix": {
                                    "type": "string",
                                    "description": "Chave PIX (obrigatório para PIX)"
                                },
                                "agencia_destino": {
                                    "type": "string",
                                    "description": "Agência de destino (obrigatório para TED)"
                                },
                                "conta_destino": {
                                    "type": "string",
                                    "description": "Conta de destino (obrigatório para TED)"
                                },
                                "banco_destino": {
                                    "type": "string",
                                    "description": "Código do banco de destino (opcional para TED, padrão: 001 para BB)"
                                }
                            },
                            "required": ["tipo", "valor"]
                        }
                    },
                    "data_pagamento": {
                        "type": "string",
                        "description": "Data do pagamento YYYY-MM-DD (opcional, padrão: hoje)"
                    }
                },
                "required": ["agencia", "conta", "pagamentos"]
            }
        }
    })
    
    # ✅ NOVO (13/01/2026): Tool: Consultar Lote de Pagamentos Banco do Brasil
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_lote_bb",
            "description": "📋 CONSULTAR LOTE DE PAGAMENTOS BANCO DO BRASIL - Use esta função quando o usuário pedir para verificar status de um lote de pagamentos no Banco do Brasil. Exemplos: 'status do lote X', 'consultar lote de pagamentos BB', 'verificar lote BB', 'status pagamento em lote'. ⚠️ IMPORTANTE: Requer ID do lote retornado ao iniciar pagamento em lote.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id_lote": {
                        "type": "string",
                        "description": "ID do lote de pagamentos (obrigatório)"
                    }
                },
                "required": ["id_lote"]
            }
        }
    })
    
    # ✅ NOVO (13/01/2026): Tool: Listar Lotes de Pagamentos Banco do Brasil
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_lotes_bb",
            "description": "📋 LISTAR LOTES DE PAGAMENTOS BANCO DO BRASIL - Use esta função quando o usuário pedir para listar todos os lotes de pagamentos no Banco do Brasil. Exemplos: 'listar lotes de pagamentos BB', 'mostrar lotes BB', 'todos os lotes banco do brasil', 'histórico de lotes'. ⚠️ IMPORTANTE: Pode filtrar por agência, conta e período (data_inicio, data_fim).",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Agência (opcional, para filtrar)"
                    },
                    "conta": {
                        "type": "string",
                        "description": "Conta (opcional, para filtrar)"
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial YYYY-MM-DD (opcional)"
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final YYYY-MM-DD (opcional)"
                    }
                },
                "required": []
            }
        }
    })
    
    # Tool: Gerar PDF Extrato Santander
    tools.append({
        "type": "function",
        "function": {
            "name": "gerar_pdf_extrato_santander",
            "description": "📄 GERAR PDF EXTRATO SANTANDER - Use esta função quando o usuário pedir para gerar PDF do extrato bancário do Santander. Gera PDF no formato contábil padrão (Data, Histórico, Crédito, Débito, Saldo). Exemplos: 'gerar pdf do extrato santander', 'pdf do extrato', 'extrato santander em pdf', 'gerar extrato pdf'. ⚠️ IMPORTANTE: Esta função consulta o extrato primeiro e depois gera o PDF. Se não fornecer agência/conta, usa primeira conta disponível. Se não fornecer datas, usa últimos 7 dias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agencia": {
                        "type": "string",
                        "description": "Código da agência (4 dígitos, ex: '3003'). Se não fornecido, usa primeira conta disponível."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta (12 dígitos, ex: '000130827180'). Se não fornecido, usa primeira conta disponível."
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-01', '01/01/2026', 'hoje'). Se não fornecido, usa 7 dias atrás."
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final no formato YYYY-MM-DD, DD/MM/YYYY ou palavras-chave (ex: '2026-01-06', '06/01/2026', 'hoje'). Se não fornecido, usa hoje."
                    },
                    "dias": {
                        "type": "integer",
                        "description": "Número de dias para trás (ex: 7, 30). Usado apenas se data_inicio e data_fim não forem fornecidos. Padrão: 7 dias."
                    }
                },
                "required": []
            }
        }
    })
    
    # ✅ NOVO (12/01/2026): Tool para consultar contexto de sessão real
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_contexto_sessao",
            "description": "🔍 Consulta o contexto REAL salvo na sessão atual. Retorna APENAS o que está realmente salvo no banco de dados (processo, categoria, última consulta), SEM inventar ou inferir informações detalhadas. Use quando o usuário perguntar 'o que está no seu contexto?', 'qual seu contexto?', 'me mostra seu contexto', 'contexto agora'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })
    
    # ✅ NOVO (12/01/2026): Tool para buscar seção específica do relatório salvo
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_secao_relatorio_salvo",
            "description": "📊 Busca uma seção ESPECÍFICA de um relatório salvo (ex: 'mostre os alertas', 'mostre as DIs em análise', 'mostre as pendências', 'mostre ETA alterado'). ✅ Também cobre FECHAMENTO DO DIA: se o usuário pedir 'quais foram essas 10 movimentações?' ou 'detalhe as movimentações', use secao='movimentacoes' (lista completa) ou secao='mudancas_status_di/ce/duimp'. ⚠️ IMPORTANTE: se o usuário pedir filtro/agrupamento em linguagem natural (ex: 'filtre só os DMD', 'só canal verde', 'agrupe por canal', 'só atrasos > 7 dias'), use **filtrar_relatorio_fuzzy** (não esta tool).",
            "parameters": {
                "type": "object",
                "properties": {
                    "secao": {
                        "type": "string",
                        "enum": [
                            "alertas",
                            "dis_analise",
                            "duimps_analise",
                            "processos_prontos",
                            "pendencias",
                            "eta_alterado",
                            "processos_chegando",
                            "processos_chegaram",
                            "processos_desembaracados",
                            "duimps_criadas",
                            "dis_registradas",
                            "mudancas_status_ce",
                            "mudancas_status_di",
                            "mudancas_status_duimp",
                            "pendencias_resolvidas",
                            "movimentacoes"
                        ],
                        "description": "Seção do relatório a buscar. Para dashboard: alertas, dis_analise, duimps_analise, processos_prontos, pendencias, eta_alterado, processos_chegando. Para FECHAMENTO: processos_chegaram, processos_desembaracados, duimps_criadas, dis_registradas, mudancas_status_ce/di/duimp, pendencias_resolvidas e movimentacoes (lista completa). ⚠️ Se o usuário pedir para filtrar por categoria, deixe secao como None e forneça categoria."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Categoria (opcional) para filtrar dentro da seção quando fizer sentido. ⚠️ Se o pedido for um filtro 'fuzzy' (ex: 'filtre só os DMD'), use filtrar_relatorio_fuzzy."
                    },
                    "tipo_relatorio": {
                        "type": "string",
                        "enum": ["resumo", "fechamento", "fob", "averbacoes"],
                        "description": "Tipo do relatório salvo. Se não fornecido, busca automaticamente o último relatório salvo. 'resumo' = 'o que temos pra hoje?', 'fechamento' = 'fechamento do dia', 'fob' = relatório FOB, 'averbacoes' = relatório de averbações."
                    },
                    "report_id": {
                        "type": "string",
                        "description": "✅ NOVO (14/01/2026): ID do relatório no formato 'rel_YYYYMMDD_HHMMSS' (ex: 'rel_20260114_104333'). Se fornecido, busca este relatório específico. Se não fornecido, usa o relatório ativo automaticamente."
                    },
                    "canal": {
                        "type": "string",
                        "enum": ["Verde", "Vermelho"],
                        "description": "Filtro de canal (útil para 'DIs em análise' e 'DUIMPs em análise'). Ex.: 'só canal verde', 'quais estão em canal vermelho?'."
                    },
                    "tipo_pendencia": {
                        "type": "string",
                        "enum": ["Frete", "ICMS", "AFRMM", "LPCO", "Bloqueio CE"],
                        "description": "Filtro de pendências por tipo (ex.: 'só pendências de frete', 'só ICMS'). Usado quando secao='pendencias'."
                    },
                    "tipo_mudanca": {
                        "type": "string",
                        "enum": ["ATRASO", "ADIANTADO"],
                        "description": "Filtro em 'ETA alterado' por tipo de mudança (ex.: 'só atrasos', 'só adiantados'). Usado quando secao='eta_alterado'."
                    },
                    "min_dias": {
                        "type": "integer",
                        "description": "Filtro numérico mínimo para seções como 'ETA alterado' (ex.: 7 = mostrar apenas mudanças >= 7 dias)."
                    },
                    "status_contains": {
                        "type": "string",
                        "description": "Filtro textual (contém) para status dentro da seção. Ex.: 'desembara' (para DIs), 'rascunho' (para DUIMPs)."
                    },
                    "min_age_dias": {
                        "type": "integer",
                        "description": "Filtro mínimo de idade em dias (quando a seção tiver 'tempo_analise'). Ex.: 7 = mostrar apenas itens com 7+ dias."
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (28/01/2026): Tool para filtrar/agrupamento "fuzzy" sobre relatório salvo (sem regex)
    tools.append({
        "type": "function",
        "function": {
            "name": "filtrar_relatorio_fuzzy",
            "description": "🧠📊 Interpreta um pedido 'fuzzy' de filtro/agrupamento SOBRE o relatório que já está na tela (salvo com [REPORT_META:...]) e aplica de forma determinística no JSON salvo, gerando um NOVO relatório filtrado/agrupado e atualizando last_visible_report_id. Use quando o usuário disser coisas como: 'filtra DMD', 'mostra só atrasados', 'só canal verde', 'agrupe por canal', 'só pendências de frete'. ⚠️ CRÍTICO: não gere relatório novo no SQL; apenas filtre/transforme o relatório salvo para preservar contexto e permitir 'envie esse relatório por email' em seguida.",
            "parameters": {
                "type": "object",
                "properties": {
                    "instrucao": {
                        "type": "string",
                        "description": "Pedido do usuário em linguagem natural (ex: 'filtra DMD', 'só canal verde', 'agrupe por canal', 'só atrasos acima de 7 dias')."
                    },
                    "report_id": {
                        "type": "string",
                        "description": "Opcional. ID do relatório no formato 'rel_YYYYMMDD_HHMMSS'. Se omitido, usa o relatório ativo/visível da sessão."
                    }
                },
                "required": ["instrucao"]
            }
        }
    })

    # ✅ NOVO (20/01/2026): Tool para listar DIs por canal (sem depender de relatório salvo)
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_dis_por_canal",
            "description": "📋 Lista DIs (do Kanban/SQLite - processos ativos) filtrando por canal (Verde/Vermelho). Use quando o usuário perguntar sobre 'canal verde/vermelho' SEM necessariamente ter gerado um relatório ('o que temos pra hoje?') antes. ⚠️ Importante: este comando é 'ativos-first' (não faz varredura histórica completa).",
            "parameters": {
                "type": "object",
                "properties": {
                    "canal": {
                        "type": "string",
                        "enum": ["Verde", "Vermelho"],
                        "description": "Canal a filtrar."
                    },
                    "status_contains": {
                        "type": "string",
                        "description": "Filtro opcional de status (contém). Ex.: 'desembara', 'interromp'."
                    }
                },
                "required": ["canal"]
            }
        }
    })

    # ✅ NOVO (20/01/2026): Tool para listar pendências ativas (ativos-first, sem relatório)
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_pendencias_ativas",
            "description": "⚠️ Lista pendências ativas dos processos ativos (Kanban/SQLite), sem exigir relatório. Use quando o usuário perguntar por pendências SEM ter gerado 'o que temos pra hoje?'. Exemplos: 'quais pendências de frete?', 'tem ICMS pendente?', 'mostre só AFRMM', 'pendências ativas'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_pendencia": {
                        "type": "string",
                        "enum": ["Frete", "ICMS", "AFRMM", "LPCO", "Bloqueio CE"],
                        "description": "Filtro opcional por tipo de pendência."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Filtro opcional por categoria (ex: DMD, ALH)."
                    },
                    "modal": {
                        "type": "string",
                        "description": "Filtro opcional por modal (ex: Marítimo, Aéreo)."
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (20/01/2026): Tool para listar alertas recentes (ativos-first, sem relatório)
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_alertas_recentes",
            "description": "🔔 Lista alertas recentes (últimas 24h) do sistema (processos ativos), sem exigir relatório. Use quando o usuário pedir 'quais alertas?', 'mostre alertas', 'alertas recentes'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de alertas (padrão: 10).",
                        "default": 10
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Filtro opcional por categoria (ex: DMD, BGR)."
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (20/01/2026): Tool para listar processos prontos para registro (ativos-first, sem relatório)
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_processos_prontos_registro",
            "description": "✅ Lista processos prontos para registro (ativos) sem exigir relatório. Use quando o usuário perguntar 'quais estão prontos para registro?' sem ter gerado 'o que temos pra hoje?'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Filtro opcional por categoria."
                    },
                    "modal": {
                        "type": "string",
                        "description": "Filtro opcional por modal (Marítimo/Aéreo)."
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (20/01/2026): Tool para listar ETA alterado (ativos-first, sem relatório)
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_eta_alterado",
            "description": "🔄 Lista processos com ETA alterado (atraso/adiantado) a partir do Kanban/SQLite, sem exigir relatório. Use quando o usuário perguntar 'quais atrasaram?', 'só atrasos acima de 7 dias', etc, sem ter gerado relatório antes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_mudanca": {
                        "type": "string",
                        "enum": ["ATRASO", "ADIANTADO"],
                        "description": "Filtro por tipo de mudança."
                    },
                    "min_dias": {
                        "type": "integer",
                        "description": "Filtro mínimo em dias (ex: 7 = mudanças >= 7 dias)."
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Filtro opcional por categoria."
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (20/01/2026): Tool para listar DUIMPs em análise (ativos-first, sem relatório)
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_duimps_em_analise",
            "description": "📋 Lista DUIMPs em análise/rascunho (ativos) sem exigir relatório. Use quando o usuário perguntar 'duimps em rascunho há 7 dias', 'quais duimps em análise', etc, antes de gerar relatório.",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "Filtro opcional por categoria."
                    },
                    "status_contains": {
                        "type": "string",
                        "description": "Filtro textual (contém) para status. Ex.: 'rascunho'."
                    },
                    "min_age_dias": {
                        "type": "integer",
                        "description": "Filtro mínimo de idade em dias (usa 'tempo_analise' quando disponível)."
                    }
                },
                "required": []
            }
        }
    })
    
    # ✅ NOVO (12/01/2026): Tool para buscar relatório específico por ID
    tools.append({
        "type": "function",
        "function": {
            "name": "buscar_relatorio_por_id",
            "description": "🔍 Busca um relatório específico por ID. Use quando o usuário mencionar um ID de relatório (ex: 'usar rel_20260112_145026', 'filtre o rel_20260112_145026', 'melhore o rel_20260112_145026'). O ID está no formato 'rel_YYYYMMDD_HHMMSS' e aparece no JSON inline [REPORT_META:...] no final de cada relatório. Isso permite referenciar um relatório específico quando há múltiplos relatórios na mesma sessão, evitando confusão.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relatorio_id": {
                        "type": "string",
                        "description": "ID do relatório no formato 'rel_YYYYMMDD_HHMMSS' (ex: 'rel_20260112_145026'). Este ID está disponível no JSON inline [REPORT_META:...] no final de cada relatório gerado."
                    }
                },
                "required": ["relatorio_id"]
            }
        }
    })
    
    # ✅ NOVO (12/01/2026): Tools para Pagamentos Santander (ISOLADO - Cenário 1)
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_workspaces_santander",
            "description": "🏦 LISTAR WORKSPACES SANTANDER - Use esta função quando o usuário pedir para listar workspaces do Santander ou ver quais workspaces estão disponíveis para pagamentos. Exemplos: 'listar workspaces', 'workspaces disponíveis', 'ver workspaces do santander'. ⚠️ IMPORTANTE: Workspace é necessário para fazer pagamentos (TED, PIX, etc.). Se não houver workspace, use criar_workspace_santander primeiro.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "criar_workspace_santander",
            "description": "🔧 CRIAR WORKSPACE SANTANDER - Use esta função quando o usuário pedir para criar um workspace para pagamentos no Santander. Exemplos: 'criar workspace', 'configurar workspace', 'workspace para pagamentos'. ⚠️ IMPORTANTE: Workspace é pré-requisito para fazer pagamentos. Precisa de agência e conta da conta principal. Tipo padrão: PAYMENTS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo": {
                        "type": "string",
                        "enum": ["PAYMENTS", "PHYSICAL_CORBAN", "DIGITAL_CORBAN"],
                        "description": "Tipo de workspace. PAYMENTS = pagamentos gerais (padrão), PHYSICAL_CORBAN = corban físico, DIGITAL_CORBAN = corban digital."
                    },
                    "agencia": {
                        "type": "string",
                        "description": "Agência da conta principal (4 dígitos, ex: '3003'). Obrigatório."
                    },
                    "conta": {
                        "type": "string",
                        "description": "Número da conta principal (12 dígitos, ex: '000130827180'). Obrigatório."
                    },
                    "description": {
                        "type": "string",
                        "description": "Descrição do workspace (opcional)."
                    }
                },
                "required": ["agencia", "conta"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "iniciar_ted_santander",
            "description": "💸 INICIAR TED SANTANDER - Use esta função quando o usuário pedir para fazer uma transferência TED, enviar dinheiro via TED, transferir valores. Exemplos OBRIGATÓRIOS: 'fazer ted', 'transferir 100 reais', 'enviar ted para conta X', 'ted de 500 para joão', 'transferir dinheiro via ted'. ⚠️ IMPORTANTE: Esta função INICIA a TED (cria em estado PENDING_VALIDATION). Depois, use efetivar_ted_santander para confirmar e autorizar. Precisa de: agência/conta origem, banco/agência/conta destino, valor, nome e CPF/CNPJ do destinatário. Se não fornecer workspace_id, usa o configurado no .env ou tenta obter automaticamente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional). Se não fornecido, usa SANTANDER_WORKSPACE_ID do .env ou tenta obter automaticamente."
                    },
                    "agencia_origem": {
                        "type": "string",
                        "description": "Agência da conta origem (4 dígitos, ex: '3003'). Opcional - se não fornecido, usa a conta principal do workspace."
                    },
                    "conta_origem": {
                        "type": "string",
                        "description": "Número da conta origem (12 dígitos, ex: '000130827180'). Opcional - se não fornecido, usa a conta principal do workspace."
                    },
                    "banco_destino": {
                        "type": "string",
                        "description": "Código do banco destino (3 dígitos, ex: '001' para Banco do Brasil, '033' para Santander, '104' para Caixa). Obrigatório."
                    },
                    "agencia_destino": {
                        "type": "string",
                        "description": "Agência da conta destino. Obrigatório."
                    },
                    "conta_destino": {
                        "type": "string",
                        "description": "Número da conta destino. Obrigatório."
                    },
                    "valor": {
                        "type": "number",
                        "description": "Valor da transferência em reais (ex: 100.50). Obrigatório e deve ser maior que zero."
                    },
                    "nome_destinatario": {
                        "type": "string",
                        "description": "Nome completo do destinatário. Obrigatório."
                    },
                    "cpf_cnpj_destinatario": {
                        "type": "string",
                        "description": "CPF (11 dígitos) ou CNPJ (14 dígitos) do destinatário, apenas números. Obrigatório."
                    },
                    "tipo_conta_destino": {
                        "type": "string",
                        "enum": ["CONTA_CORRENTE", "CONTA_POUPANCA", "CONTA_PAGAMENTO"],
                        "description": "Tipo de conta destino. Padrão: CONTA_CORRENTE. CC = Conta Corrente, PP = Poupança, PG = Conta Pagamento."
                    },
                    "ispb_destino": {
                        "type": "string",
                        "description": "ISPB do banco destino (opcional, se não fornecer, tenta buscar automaticamente)."
                    }
                },
                "required": ["banco_destino", "agencia_destino", "conta_destino", "valor", "nome_destinatario", "cpf_cnpj_destinatario"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "efetivar_ted_santander",
            "description": "✅ EFETIVAR TED SANTANDER - Use esta função quando o usuário pedir para confirmar, autorizar ou efetivar uma TED que foi iniciada. Exemplos: 'efetivar ted', 'confirmar transferência', 'autorizar ted', 'finalizar ted'. ⚠️ IMPORTANTE: Esta função EFETIVA uma TED que foi iniciada com iniciar_ted_santander. Precisa do transfer_id retornado pela função de iniciar. Fluxo: 1) iniciar_ted_santander → retorna transfer_id, 2) efetivar_ted_santander → confirma e autoriza.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional). Se não fornecido, usa SANTANDER_WORKSPACE_ID do .env."
                    },
                    "transfer_id": {
                        "type": "string",
                        "description": "ID da transferência retornado por iniciar_ted_santander. Obrigatório."
                    },
                    "agencia_origem": {
                        "type": "string",
                        "description": "Agência da conta origem (4 dígitos). Obrigatório."
                    },
                    "conta_origem": {
                        "type": "string",
                        "description": "Número da conta origem (12 dígitos). Obrigatório."
                    }
                },
                "required": ["transfer_id", "agencia_origem", "conta_origem"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_ted_santander",
            "description": "🔍 CONSULTAR TED SANTANDER - Use esta função quando o usuário pedir para ver status de uma TED, consultar transferência, verificar ted. Exemplos: 'consultar ted X', 'status da transferência', 'ver ted', 'como está a ted'. ⚠️ IMPORTANTE: Precisa do transfer_id retornado por iniciar_ted_santander.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional). Se não fornecido, usa SANTANDER_WORKSPACE_ID do .env."
                    },
                    "transfer_id": {
                        "type": "string",
                        "description": "ID da transferência retornado por iniciar_ted_santander. Obrigatório."
                    }
                },
                "required": ["transfer_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_teds_santander",
            "description": "📋 LISTAR TEDs SANTANDER - Use esta função quando o usuário pedir para listar TEDs, ver histórico de transferências, conciliar pagamentos, ver todas as teds. Exemplos: 'listar teds', 'histórico de transferências', 'todas as teds', 'conciliação de pagamentos', 'teds de janeiro'. ⚠️ IMPORTANTE: Útil para conciliação bancária. Pode filtrar por data e status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional). Se não fornecido, usa SANTANDER_WORKSPACE_ID do .env."
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial no formato YYYY-MM-DD (ex: '2026-01-01'). Opcional."
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final no formato YYYY-MM-DD (ex: '2026-01-31'). Opcional."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["PENDING_VALIDATION", "READY_TO_PAY", "PENDING_CONFIRMATION", "PAYED", "REJECTED"],
                        "description": "Filtro por status. Opcional. PENDING_VALIDATION = aguardando validação, READY_TO_PAY = pronta para pagar, PENDING_CONFIRMATION = aguardando confirmação, PAYED = paga, REJECTED = rejeitada."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limite de registros (padrão: 10). Opcional."
                    }
                },
                "required": []
            }
        }
    })
    
    # ==========================================
    # ✅ NOVO (13/01/2026): ACCOUNTS AND TAXES
    # Bank Slip Payments, Barcode Payments, Pix Payments,
    # Vehicle Taxes Payments, Taxes by Fields Payments
    # ==========================================
    
    # Bank Slip Payments (Boleto)
    # ✅ NOVO (13/01/2026): Processar upload de boleto
    tools.append({
                "type": "function",
                "function": {
                    "name": "processar_boleto_upload",
                    "description": "📄 PROCESSAR BOLETO UPLOAD (SANTANDER) - Use quando o usuário enviar um PDF de boleto para pagamento ou pedir para processar/pagar um boleto anexado. Extrai código de barras, valor, vencimento e INICIA pagamento automaticamente via Santander. Exemplos: 'pague esse boleto', 'processar boleto', 'pagar boleto anexado', 'maike pague esse boleto'. ⚠️ IMPORTANTE: Esta função processa o PDF, extrai dados e INICIA o pagamento automaticamente via Santander Payments API. O pagamento fica em status READY_TO_PAY. Depois use efetivar_bank_slip_payment_santander para confirmar. ⚠️ CRÍTICO: Esta função usa SANTANDER, não Banco do Brasil.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "Caminho do arquivo PDF do boleto. Obrigatório."
                            },
                            "session_id": {
                                "type": "string",
                                "description": "ID da sessão do chat. Opcional."
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            })
            
    tools.append({
        "type": "function",
        "function": {
            "name": "iniciar_bank_slip_payment_santander",
            "description": "💳 INICIAR PAGAMENTO DE BOLETO SANTANDER - Use quando o usuário pedir para pagar boleto, iniciar pagamento de boleto, pagar conta com boleto. Exemplos: 'pagar boleto', 'iniciar pagamento de boleto X', 'pagar conta com código de barras'. ⚠️ IMPORTANTE: Esta função INICIA o pagamento (PENDING_VALIDATION). Depois use efetivar_bank_slip_payment_santander para confirmar. ⚠️ CRÍTICO: Gere um UUID único para payment_id (ex: 550e8400-e29b-41d4-a716-446655440000). O código de barras deve ter 44 ou 47 dígitos (apenas números, sem pontos/espaços). A data deve ser YYYY-MM-DD (ex: 2026-01-13).",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional). Se não fornecido, usa SANTANDER_WORKSPACE_ID do .env."
                    },
                    "payment_id": {
                        "type": "string",
                        "description": "ID único do pagamento (UUID gerado automaticamente). Obrigatório. Exemplo: 550e8400-e29b-41d4-a716-446655440000. GERE UM UUID ÚNICO A CADA VEZ."
                    },
                    "code": {
                        "type": "string",
                        "description": "Código de barras do boleto (44 ou 47 dígitos, APENAS NÚMEROS, sem pontos ou espaços). Obrigatório. Exemplo: 34191093216412992293280145580009313510000090000. Se o usuário fornecer com pontos/espaços, remova-os antes de enviar."
                    },
                    "payment_date": {
                        "type": "string",
                        "description": "Data do pagamento no formato YYYY-MM-DD. Obrigatório. Se o usuário não especificar, use a data de hoje. Exemplo: 2026-01-13."
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags opcionais para identificação."
                    }
                },
                "required": ["payment_id", "code", "payment_date"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "efetivar_bank_slip_payment_santander",
            "description": "✅ EFETIVAR PAGAMENTO DE BOLETO SANTANDER - Use quando o usuário pedir para confirmar, autorizar ou efetivar pagamento de boleto iniciado. Exemplos: 'efetivar boleto', 'confirmar pagamento de boleto X', 'autorizar boleto'. ⚠️ IMPORTANTE: Esta função EFETIVA um pagamento iniciado. Precisa: payment_id, payment_value, agencia_origem, conta_origem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional)."
                    },
                    "payment_id": {
                        "type": "string",
                        "description": "ID do pagamento retornado por iniciar_bank_slip_payment_santander. Obrigatório."
                    },
                    "payment_value": {
                        "type": "number",
                        "description": "Valor do pagamento em reais. Obrigatório."
                    },
                    "agencia_origem": {
                        "type": "string",
                        "description": "Agência da conta de débito (opcional, usa do workspace se não fornecido)."
                    },
                    "conta_origem": {
                        "type": "string",
                        "description": "Conta de débito (opcional, usa do workspace se não fornecido)."
                    },
                    "final_payer_name": {
                        "type": "string",
                        "description": "Nome do pagador final (opcional)."
                    },
                    "final_payer_document_type": {
                        "type": "string",
                        "enum": ["CPF", "CNPJ"],
                        "description": "Tipo de documento do pagador final (opcional)."
                    },
                    "final_payer_document_number": {
                        "type": "string",
                        "description": "Número do documento do pagador final (opcional)."
                    }
                },
                "required": ["payment_id", "payment_value"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_bank_slip_payment_santander",
            "description": "🔍 CONSULTAR PAGAMENTO DE BOLETO SANTANDER - Use quando o usuário pedir para ver status de pagamento de boleto, consultar boleto. Exemplos: 'consultar boleto X', 'status do pagamento de boleto', 'ver boleto'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional)."
                    },
                    "payment_id": {
                        "type": "string",
                        "description": "ID do pagamento. Obrigatório."
                    }
                },
                "required": ["payment_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_bank_slip_payments_santander",
            "description": "📋 LISTAR PAGAMENTOS DE BOLETO SANTANDER - Use quando o usuário pedir para listar pagamentos de boleto, ver histórico de boletos, conciliar boletos. Exemplos: 'listar boletos', 'histórico de boletos', 'todos os boletos pagos'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {
                        "type": "string",
                        "description": "ID do workspace (opcional)."
                    },
                    "data_inicio": {
                        "type": "string",
                        "description": "Data inicial (YYYY-MM-DD). Opcional."
                    },
                    "data_fim": {
                        "type": "string",
                        "description": "Data final (YYYY-MM-DD). Opcional."
                    },
                    "status": {
                        "type": "string",
                        "enum": ["PENDING_VALIDATION", "READY_TO_PAY", "PENDING_CONFIRMATION", "PAYED", "REJECTED"],
                        "description": "Filtro por status. Opcional."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limite de registros (padrão: 10). Opcional."
                    }
                },
                "required": []
            }
        }
    })
    
    # Barcode Payments (Código de Barras)
    tools.append({
        "type": "function",
        "function": {
            "name": "iniciar_barcode_payment_santander",
            "description": "💳 INICIAR PAGAMENTO POR CÓDIGO DE BARRAS SANTANDER - Use quando o usuário pedir para pagar por código de barras, pagar conta com código de barras. Exemplos: 'pagar código de barras', 'pagar conta com código X'. ⚠️ IMPORTANTE: Esta função INICIA o pagamento. Depois use efetivar_barcode_payment_santander para confirmar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID único do pagamento (UUID). Obrigatório."},
                    "code": {"type": "string", "description": "Código de barras. Obrigatório."},
                    "payment_date": {"type": "string", "description": "Data do pagamento (YYYY-MM-DD). Obrigatório."},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags opcionais."}
                },
                "required": ["payment_id", "code", "payment_date"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "efetivar_barcode_payment_santander",
            "description": "✅ EFETIVAR PAGAMENTO POR CÓDIGO DE BARRAS SANTANDER - Use para confirmar pagamento por código de barras iniciado. Exemplos: 'efetivar código de barras', 'confirmar pagamento código X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."},
                    "payment_value": {"type": "number", "description": "Valor do pagamento. Obrigatório."},
                    "agencia_origem": {"type": "string", "description": "Agência de débito (opcional)."},
                    "conta_origem": {"type": "string", "description": "Conta de débito (opcional)."},
                    "final_payer_name": {"type": "string", "description": "Nome do pagador (opcional)."},
                    "final_payer_document_type": {"type": "string", "enum": ["CPF", "CNPJ"], "description": "Tipo de documento (opcional)."},
                    "final_payer_document_number": {"type": "string", "description": "Número do documento (opcional)."}
                },
                "required": ["payment_id", "payment_value"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_barcode_payment_santander",
            "description": "🔍 CONSULTAR PAGAMENTO POR CÓDIGO DE BARRAS SANTANDER - Use para ver status de pagamento por código de barras.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."}
                },
                "required": ["payment_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_barcode_payments_santander",
            "description": "📋 LISTAR PAGAMENTOS POR CÓDIGO DE BARRAS SANTANDER - Use para listar pagamentos por código de barras realizados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "data_inicio": {"type": "string", "description": "Data inicial (YYYY-MM-DD). Opcional."},
                    "data_fim": {"type": "string", "description": "Data final (YYYY-MM-DD). Opcional."},
                    "status": {"type": "string", "enum": ["PENDING_VALIDATION", "READY_TO_PAY", "PENDING_CONFIRMATION", "PAYED", "REJECTED"], "description": "Filtro por status. Opcional."},
                    "limit": {"type": "integer", "description": "Limite de registros. Opcional."}
                },
                "required": []
            }
        }
    })
    
    # Pix Payments
    tools.append({
        "type": "function",
        "function": {
            "name": "iniciar_pix_payment_santander",
            "description": "💸 INICIAR PAGAMENTO PIX SANTANDER - Use quando o usuário pedir para fazer PIX, enviar PIX, transferir via PIX. Exemplos: 'fazer pix', 'enviar pix de 100 reais', 'pix para chave X'. ⚠️ IMPORTANTE: Esta função INICIA o PIX. Suporta 3 modos: 1) DICT (chave PIX): dict_code + dict_code_type, 2) QR Code: qr_code + ibge_town_code + payment_date, 3) Beneficiário: beneficiary (dados completos). Depois use efetivar_pix_payment_santander para confirmar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID único do pagamento (UUID). Obrigatório."},
                    "payment_value": {"type": "string", "description": "Valor do pagamento (ex: '100.50'). Obrigatório."},
                    "dict_code": {"type": "string", "description": "Chave PIX (para modo DICT). Ex: email, CPF, CNPJ, telefone, chave aleatória."},
                    "dict_code_type": {"type": "string", "enum": ["EMAIL", "CPF", "CNPJ", "PHONE", "RANDOM_KEY"], "description": "Tipo da chave PIX (para modo DICT)."},
                    "qr_code": {"type": "string", "description": "Código QR do PIX (para modo QR Code)."},
                    "ibge_town_code": {"type": "integer", "description": "Código IBGE da cidade (para modo QR Code)."},
                    "payment_date": {"type": "string", "description": "Data do pagamento (YYYY-MM-DD, para modo QR Code)."},
                    "beneficiary": {"type": "object", "description": "Dados do beneficiário (para modo Beneficiário). Deve conter: branch, number, type, documentType, documentNumber, name, bankCode, ispb."},
                    "remittance_information": {"type": "string", "description": "Informação da remessa (opcional)."},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags opcionais."}
                },
                "required": ["payment_id", "payment_value"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "efetivar_pix_payment_santander",
            "description": "✅ EFETIVAR PAGAMENTO PIX SANTANDER - Use para confirmar e efetivar PIX iniciado. Exemplos: 'efetivar pix', 'confirmar pix X', 'autorizar pix'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."},
                    "payment_value": {"type": "number", "description": "Valor do pagamento. Obrigatório."},
                    "agencia_origem": {"type": "string", "description": "Agência de débito (opcional)."},
                    "conta_origem": {"type": "string", "description": "Conta de débito (opcional)."}
                },
                "required": ["payment_id", "payment_value"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_pix_payment_santander",
            "description": "🔍 CONSULTAR PAGAMENTO PIX SANTANDER - Use para ver status de PIX, consultar pix. Exemplos: 'consultar pix X', 'status do pix', 'ver pix'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."}
                },
                "required": ["payment_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_pix_payments_santander",
            "description": "📋 LISTAR PAGAMENTOS PIX SANTANDER - Use para listar PIXs realizados, ver histórico de PIX, conciliar PIX. Exemplos: 'listar pix', 'histórico de pix', 'todos os pix'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "data_inicio": {"type": "string", "description": "Data inicial (YYYY-MM-DD). Opcional."},
                    "data_fim": {"type": "string", "description": "Data final (YYYY-MM-DD). Opcional."},
                    "status": {"type": "string", "enum": ["PENDING_VALIDATION", "READY_TO_PAY", "PENDING_CONFIRMATION", "PAYED", "REJECTED"], "description": "Filtro por status. Opcional."},
                    "limit": {"type": "integer", "description": "Limite de registros. Opcional."}
                },
                "required": []
            }
        }
    })
    
    # Vehicle Taxes Payments (IPVA)
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_debitos_renavam_santander",
            "description": "🚗 CONSULTAR DÉBITOS RENAVAM SANTANDER - Use quando o usuário pedir para consultar débitos do Renavam, ver IPVA, consultar multas veiculares. Exemplos: 'consultar débitos renavam', 'ver IPVA do veículo', 'consultar multas'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "renavam": {"type": "integer", "description": "Número do Renavam. Opcional."},
                    "state_abbreviation": {"type": "string", "description": "Sigla do estado (ex: 'SP', 'MG'). Opcional."}
                },
                "required": []
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "iniciar_vehicle_tax_payment_santander",
            "description": "🚗 INICIAR PAGAMENTO DE IPVA SANTANDER - Use quando o usuário pedir para pagar IPVA, iniciar pagamento de IPVA. Exemplos: 'pagar IPVA', 'iniciar pagamento de IPVA do veículo X'. ⚠️ IMPORTANTE: Esta função INICIA o pagamento. Depois use efetivar_vehicle_tax_payment_santander para confirmar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID único do pagamento (UUID). Obrigatório."},
                    "renavam": {"type": "integer", "description": "Número do Renavam. Obrigatório."},
                    "tax_type": {"type": "string", "description": "Tipo de imposto (ex: 'IPVA'). Obrigatório."},
                    "exercise_year": {"type": "integer", "description": "Ano de exercício. Obrigatório."},
                    "state_abbreviation": {"type": "string", "description": "Sigla do estado (ex: 'SP'). Obrigatório."},
                    "doc_type": {"type": "string", "enum": ["CPF", "CNPJ"], "description": "Tipo de documento. Obrigatório."},
                    "document_number": {"type": "integer", "description": "Número do documento. Obrigatório."},
                    "type_quota": {"type": "string", "enum": ["SINGLE", "MULTIPLE"], "description": "Tipo de quota (padrão: SINGLE). Opcional."},
                    "payment_date": {"type": "string", "description": "Data do pagamento (YYYY-MM-DD). Opcional."},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags opcionais."}
                },
                "required": ["payment_id", "renavam", "tax_type", "exercise_year", "state_abbreviation", "doc_type", "document_number"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "efetivar_vehicle_tax_payment_santander",
            "description": "✅ EFETIVAR PAGAMENTO DE IPVA SANTANDER - Use para confirmar pagamento de IPVA iniciado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."},
                    "agencia_origem": {"type": "string", "description": "Agência de débito (opcional)."},
                    "conta_origem": {"type": "string", "description": "Conta de débito (opcional)."}
                },
                "required": ["payment_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_vehicle_tax_payment_santander",
            "description": "🔍 CONSULTAR PAGAMENTO DE IPVA SANTANDER - Use para ver status de pagamento de IPVA.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."}
                },
                "required": ["payment_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_vehicle_tax_payments_santander",
            "description": "📋 LISTAR PAGAMENTOS DE IPVA SANTANDER - Use para listar pagamentos de IPVA realizados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "data_inicio": {"type": "string", "description": "Data inicial (YYYY-MM-DD). Opcional."},
                    "data_fim": {"type": "string", "description": "Data final (YYYY-MM-DD). Opcional."},
                    "status": {"type": "string", "enum": ["PENDING_VALIDATION", "READY_TO_PAY", "PENDING_CONFIRMATION", "PAYED", "REJECTED"], "description": "Filtro por status. Opcional."},
                    "limit": {"type": "integer", "description": "Limite de registros. Opcional."}
                },
                "required": []
            }
        }
    })
    
    # Taxes by Fields Payments (GARE, DARF, GPS)
    tools.append({
        "type": "function",
        "function": {
            "name": "iniciar_tax_by_fields_payment_santander",
            "description": "📄 INICIAR PAGAMENTO DE IMPOSTO POR CAMPOS SANTANDER - Use quando o usuário pedir para pagar GARE, DARF, GPS, pagar imposto por campos. Exemplos: 'pagar GARE ICMS', 'pagar DARF', 'pagar GPS', 'iniciar pagamento de imposto'. ⚠️ IMPORTANTE: Esta função INICIA o pagamento. Tipos suportados: 'GARE ICMS', 'GARE ITCMD', 'DARF', 'GPS'. Cada tipo tem campos específicos (field01, field02, etc.). Depois use efetivar_tax_by_fields_payment_santander para confirmar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID único do pagamento (UUID). Obrigatório."},
                    "tax_type": {"type": "string", "enum": ["GARE ICMS", "GARE ITCMD", "DARF", "GPS"], "description": "Tipo de imposto. Obrigatório."},
                    "payment_date": {"type": "string", "description": "Data do pagamento (YYYY-MM-DD). Obrigatório."},
                    "city": {"type": "string", "description": "Cidade. Opcional."},
                    "state_abbreviation": {"type": "string", "description": "Sigla do estado (ex: 'SP'). Opcional."},
                    "fields": {"type": "object", "description": "Campos específicos do imposto (field01, field02, etc.). Estrutura varia conforme tax_type. Opcional mas recomendado."},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags opcionais."}
                },
                "required": ["payment_id", "tax_type", "payment_date"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "efetivar_tax_by_fields_payment_santander",
            "description": "✅ EFETIVAR PAGAMENTO DE IMPOSTO POR CAMPOS SANTANDER - Use para confirmar pagamento de imposto (GARE, DARF, GPS) iniciado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."},
                    "agencia_origem": {"type": "string", "description": "Agência de débito (opcional)."},
                    "conta_origem": {"type": "string", "description": "Conta de débito (opcional)."}
                },
                "required": ["payment_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "consultar_tax_by_fields_payment_santander",
            "description": "🔍 CONSULTAR PAGAMENTO DE IMPOSTO POR CAMPOS SANTANDER - Use para ver status de pagamento de imposto (GARE, DARF, GPS).",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "payment_id": {"type": "string", "description": "ID do pagamento. Obrigatório."}
                },
                "required": ["payment_id"]
            }
        }
    })
    
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_tax_by_fields_payments_santander",
            "description": "📋 LISTAR PAGAMENTOS DE IMPOSTOS POR CAMPOS SANTANDER - Use para listar pagamentos de impostos (GARE, DARF, GPS) realizados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workspace_id": {"type": "string", "description": "ID do workspace (opcional)."},
                    "data_inicio": {"type": "string", "description": "Data inicial (YYYY-MM-DD). Opcional."},
                    "data_fim": {"type": "string", "description": "Data final (YYYY-MM-DD). Opcional."},
                    "status": {"type": "string", "enum": ["PENDING_VALIDATION", "READY_TO_PAY", "PENDING_CONFIRMATION", "PAYED", "REJECTED"], "description": "Filtro por status. Opcional."},
                    "limit": {"type": "integer", "description": "Limite de registros. Opcional."}
                },
                "required": []
            }
        }
    })
    
    # ✅ NOVO (18/01/2026): Tool para listar notícias do Siscomex
    tools.append({
        "type": "function",
        "function": {
            "name": "listar_noticias_siscomex",
            "description": "📰 Lista notícias do Siscomex (Importação e Sistemas) que foram coletadas automaticamente via feeds RSS. Use quando o usuário perguntar: 'quais notícias do siscomex?', 'mostre as notícias', 'notícias recentes', 'o que tem de novo no siscomex?', 'notícias de importação', 'notícias de sistemas'. Permite filtrar por fonte (importação ou sistemas) e limitar por número de dias. Retorna lista formatada com título, data, descrição e link clicável para cada notícia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fonte": {
                        "type": "string",
                        "description": "Fonte das notícias: 'importacao' ou 'sistemas'. Deixe vazio para todas as fontes.",
                        "enum": ["importacao", "sistemas"]
                    },
                    "limite": {
                        "type": "integer",
                        "description": "Número máximo de notícias a retornar (padrão: 20, máximo recomendado: 50)"
                    },
                    "dias": {
                        "type": "integer",
                        "description": "Número de dias retroativos para buscar (ex: 7 = últimas notícias dos últimos 7 dias). Deixe vazio para buscar todas."
                    }
                },
                "required": []
            }
        }
    })

    # ✅ NOVO (21/01/2026): Mercante - AFRMM (RPA)
    # ⚠️ TEMPORARIAMENTE COMENTADA: Limite de 128 tools atingido. Use executar_pagamento_afrmm que cobre o caso principal.
    # tools.append({
    #     "type": "function",
    #     "function": {
    #         "name": "preparar_pagamento_afrmm",
    #         "description": "🚢 AFRMM (Mercante) - Prepara Marinha Mercante: resolve CE-Mercante do processo e abre 'Pagamento → Pagar AFRMM', preenche CE, deixa 'Nr. da Parcela' em branco (se não informado) e clica 'Enviar' para ir à próxima tela. ⚠️ Não efetiva pagamento (apenas prepara/navega).",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "processo_referencia": {
    #                     "type": "string",
    #                     "description": "Processo no formato XXX.NNNN/AA (ex: GYM.0050/25). O Maike resolve o CE automaticamente."
    #                 },
    #                 "parcela": {
    #                     "type": "string",
    #                     "description": "Nr. da parcela (opcional). Se omitido, deixa em branco."
    #                 },
    #                 "clicar_enviar": {
    #                     "type": "boolean",
    #                     "description": "Se true (padrão), clica 'Enviar' após preencher o CE (vai para a próxima tela).",
    #                     "default": True
    #                 },
    #                 "executar_local": {
    #                     "type": "boolean",
    #                     "description": "Se true, tenta disparar o bot localmente em background. Se false (padrão), retorna o comando para você executar.",
    #                     "default": False
    #                 }
    #             },
    #             "required": ["processo_referencia"]
    #         }
    #     }
    # })
    
    # ✅ NOVO (21/01/2026): Mercante - AFRMM (Execução com Preview + Confirmação)
    tools.append({
        "type": "function",
        "function": {
            "name": "executar_pagamento_afrmm",
            "description": "💳 PAGAR AFRMM (Mercante) - Executa pagamento de AFRMM: mostra preview com Valor do Débito + Saldo BB, cria pending intent para confirmação e só executa após confirmação do usuário. ⚠️ Ação sensível que requer confirmação.",
            "parameters": {
                "type": "object",
                "properties": {
                    "processo_referencia": {
                        "type": "string",
                        "description": "Processo no formato XXX.NNNN/AA (ex: GYM.0050/25). O Maike resolve o CE automaticamente."
                    },
                    "ce_mercante": {
                        "type": "string",
                        "description": "CE-Mercante (somente números) opcional. Use se o processo não estiver com CE no cache ainda (ex: 172605011670595)."
                    },
                    "parcela": {
                        "type": "string",
                        "description": "Nr. da parcela (opcional). Se omitido, deixa em branco."
                    }
                },
                "required": ["processo_referencia"]
            }
        }
    })
    
    # ✅ FILTRO POR WHITELIST (14/01/2026): Se whitelist fornecida, filtrar tools
    if whitelist is not None:
        logger_whitelist = logging.getLogger(__name__)
        total_tools = len(tools)
        tools_filtradas = []
        for tool in tools:
            tool_name = tool.get('function', {}).get('name', '')
            if tool_name in whitelist:
                tools_filtradas.append(tool)
        tools = tools_filtradas
        logger_whitelist.info(f'🔍 [WHITELIST] Tools filtradas: {len(tools)} de {total_tools} (whitelist: {whitelist})')
    
    # ✅ GUARDRAIL (28/01/2026): OpenAI limita o array `tools` a no máximo 128 itens.
    # - Deduplica por `function.name` (evita exceder por duplicatas acidentais)
    # - Trunca mantendo a ordem (as tools "prioridade máxima" tendem a estar no topo)
    MAX_TOOLS_OPENAI = 128
    logger_tools = logging.getLogger(__name__)

    seen_names = set()
    deduped_tools: List[Dict[str, Any]] = []
    dup_names: List[str] = []
    for tool in tools:
        name = (tool.get('function') or {}).get('name')
        if not name:
            # Se por algum motivo vier uma tool sem nome, mantém (mas não ajuda na dedupe)
            deduped_tools.append(tool)
            continue
        if name in seen_names:
            dup_names.append(name)
            continue
        seen_names.add(name)
        deduped_tools.append(tool)

    if dup_names:
        # Mostrar no log apenas uma amostra pra não poluir
        sample = ", ".join(dup_names[:10])
        logger_tools.warning(
            f"⚠️ [TOOLS] Duplicatas removidas por function.name: {len(dup_names)} (amostra: {sample})"
        )

    tools = deduped_tools

    # ✅ Preferir remover tools "nice-to-have" antes de truncar na marra.
    # Motivo: a ordem no final do arquivo pode fazer a truncagem cortar tools importantes (ex: pagamentos).
    if len(tools) > MAX_TOOLS_OPENAI:
        drop_first_names = [
            # Notícias é útil, mas não é core do fluxo (e foi adicionada no fim do arquivo).
            "listar_noticias_siscomex",
            # Diagnóstico é útil, mas não é essencial para operações do chat.
            "verificar_fontes_dados",
        ]
        before = len(tools)
        removed: List[str] = []
        for drop_name in drop_first_names:
            if len(tools) <= MAX_TOOLS_OPENAI:
                break
            removed_one = False
            filtered: List[Dict[str, Any]] = []
            for t in tools:
                n = (t.get("function") or {}).get("name")
                if (not removed_one) and n == drop_name:
                    removed.append(drop_name)
                    removed_one = True
                    continue
                filtered.append(t)
            tools = filtered

        if removed:
            logger_tools.warning(
                f"⚠️ [TOOLS] Removidas {len(removed)} tool(s) 'nice-to-have' para respeitar limite {MAX_TOOLS_OPENAI}: "
                f"{', '.join(removed)} (antes={before}, agora={len(tools)})"
            )

    if len(tools) > MAX_TOOLS_OPENAI:
        dropped = tools[MAX_TOOLS_OPENAI:]
        dropped_names = [
            (t.get('function') or {}).get('name', '<sem_nome>')
            for t in dropped
        ]
        sample_dropped = ", ".join(dropped_names[:15])
        logger_tools.warning(
            f"⚠️ [TOOLS] Muitas tools para o limite da OpenAI: {len(tools)} > {MAX_TOOLS_OPENAI}. "
            f"Truncando e descartando {len(dropped)} tool(s) (amostra: {sample_dropped})"
        )
        tools = tools[:MAX_TOOLS_OPENAI]

    return tools

