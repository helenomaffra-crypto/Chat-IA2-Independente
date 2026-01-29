"""
Utilitário para consultar PTAX (cotação do dólar) do Banco Central do Brasil.

API oficial: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/

✅ REGRA DE DIAS ÚTEIS:
- Se a data solicitada NÃO é dia útil (sábado/domingo/feriado), usar cotação do último dia útil anterior
- Se a data solicitada É dia útil, usar cotação do próprio dia
- Exemplo: 15/12/2025 (domingo) → usar cotação de 13/12/2025 (último dia útil)
- Exemplo: 16/12/2025 (segunda) → usar cotação de 16/12/2025 (próprio dia)

✅ REGRA PARA REGISTRO DE DUIMP/DI:
- HOJE: Para registrar DUIMP/DI HOJE, usa a PTAX de ONTEM (último dia útil anterior)
- AMANHÃ: Para registrar DUIMP/DI AMANHÃ, usa a PTAX de HOJE
- PASSADO: Usa a PTAX da data solicitada (com regra de dias úteis)
- FUTURO (>1 dia): Usa a última PTAX disponível
"""
import requests
import logging
import calendar
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# URL base da API do Banco Central
BCB_PTAX_API_BASE = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"


def _eh_dia_util(data_dt: datetime) -> bool:
    """
    Verifica se uma data é dia útil (segunda a sexta, não feriado).
    
    ⚠️ NOTA: Esta função não verifica feriados nacionais. Apenas verifica se é segunda a sexta.
    Para verificação completa de feriados, seria necessário usar biblioteca externa.
    
    Args:
        data_dt: Data como datetime
    
    Returns:
        True se for dia útil (segunda a sexta), False caso contrário
    """
    # 0 = Segunda, 1 = Terça, ..., 4 = Sexta, 5 = Sábado, 6 = Domingo
    dia_semana = data_dt.weekday()
    return dia_semana < 5  # Segunda (0) a Sexta (4)


def _obter_ultimo_dia_util(data_dt: datetime, max_dias: int = 10) -> Optional[datetime]:
    """
    Obtém o último dia útil anterior à data fornecida.
    
    Args:
        data_dt: Data de referência
        max_dias: Máximo de dias para buscar (evitar loop infinito)
    
    Returns:
        datetime do último dia útil ou None se não encontrou
    """
    for i in range(1, max_dias + 1):
        data_anterior = data_dt - timedelta(days=i)
        if _eh_dia_util(data_anterior):
            return data_anterior
    return None


def obter_ptax_dolar(data: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Obtém a cotação PTAX do dólar americano para uma data específica.
    
    ✅ CORREÇÃO: Usa endpoint CotacaoMoedaPeriodo para buscar todas as cotações do dia
    e seleciona a correta baseado no tipo de boletim (prioridade: Fechamento Interbancário > Intermediário > Fechamento > Abertura)
    
    Args:
        data: Data no formato 'MM-DD-YYYY' (ex: '12-15-2025'). 
              Se None, usa a data de hoje.
    
    Returns:
        Dict com:
        - 'data_cotacao': Data da cotação (YYYY-MM-DD)
        - 'cotacao_compra': Valor de compra (float)
        - 'cotacao_venda': Valor de venda (float)
        - 'cotacao_media': Média entre compra e venda (float)
        - 'tipo_boletim': Tipo de boletim usado (ex: 'Fechamento Interbancário', 'Intermediário')
        - 'timestamp': Timestamp da consulta
        - 'sucesso': True/False
        - 'erro': Mensagem de erro (se houver)
    
    Exemplo:
        >>> ptax = obter_ptax_dolar('12-15-2025')
        >>> print(f"PTAX: R$ {ptax['cotacao_media']:.4f}")
    """
    try:
        # Se não especificou data, usar hoje
        if data is None:
            hoje = datetime.now()
            data = hoje.strftime('%m-%d-%Y')
        
        # ✅ CRÍTICO: Verificar se a data solicitada é dia útil
        # Parsear data solicitada
        partes = data.split('-')
        if len(partes) != 3:
            return {
                'sucesso': False,
                'erro': f'Formato de data inválido: {data}. Use MM-DD-YYYY',
                'data_cotacao': data,
                'cotacao_compra': None,
                'cotacao_venda': None,
                'cotacao_media': None,
                'timestamp': datetime.now().isoformat()
            }
        
        mes, dia, ano = int(partes[0]), int(partes[1]), int(partes[2])
        data_solicitada_dt = datetime(ano, mes, dia)
        
        # ✅ REGRA PARA REGISTRO DE DUIMP/DI:
        # 1. HOJE: Para registrar HOJE, usa PTAX de ONTEM (último dia útil anterior)
        # 2. AMANHÃ: Para registrar AMANHÃ, usa PTAX de HOJE
        # 3. PASSADO: Usa PTAX da data solicitada (com regra de dias úteis)
        # 4. FUTURO (>1 dia): Usa última PTAX disponível
        hoje_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        data_solicitada_dt_limpa = data_solicitada_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        amanha_dt = hoje_dt + timedelta(days=1)
        
        eh_hoje = data_solicitada_dt_limpa == hoje_dt
        eh_amanha = data_solicitada_dt_limpa == amanha_dt
        eh_data_futura = data_solicitada_dt_limpa > amanha_dt
        eh_passado = data_solicitada_dt_limpa < hoje_dt
        
        data_para_buscar_dt = data_solicitada_dt
        
        # ✅ REGRA 1: Se é HOJE, usar PTAX de ONTEM (último dia útil anterior)
        if eh_hoje:
            ultimo_dia_util = _obter_ultimo_dia_util(data_solicitada_dt)
            if ultimo_dia_util:
                data_para_buscar_dt = ultimo_dia_util
                data_para_buscar = data_para_buscar_dt.strftime('%m-%d-%Y')
                logger.info(f"📅 {data} é HOJE. Para registro de DUIMP/DI HOJE, usando PTAX de ONTEM: {data_para_buscar}")
            else:
                return {
                    'sucesso': False,
                    'erro': f'Não foi possível encontrar dia útil anterior a {data}',
                    'data_cotacao': data,
                    'cotacao_compra': None,
                    'cotacao_venda': None,
                    'cotacao_media': None,
                    'timestamp': datetime.now().isoformat()
                }
        # ✅ REGRA 2: Se é AMANHÃ, usar PTAX de HOJE
        elif eh_amanha:
            # Verificar se hoje é dia útil
            if _eh_dia_util(hoje_dt):
                data_para_buscar_dt = hoje_dt
                data_para_buscar = data_para_buscar_dt.strftime('%m-%d-%Y')
                logger.info(f"📅 {data} é AMANHÃ. Para registro de DUIMP/DI AMANHÃ, usando PTAX de HOJE: {data_para_buscar}")
            else:
                # Se hoje não é dia útil, usar último dia útil anterior
                ultimo_dia_util = _obter_ultimo_dia_util(hoje_dt)
                if ultimo_dia_util:
                    data_para_buscar_dt = ultimo_dia_util
                    data_para_buscar = data_para_buscar_dt.strftime('%m-%d-%Y')
                    logger.info(f"📅 {data} é AMANHÃ. Hoje não é dia útil, usando último dia útil: {data_para_buscar}")
                else:
                    return {
                        'sucesso': False,
                        'erro': f'Não foi possível encontrar dia útil anterior',
                        'data_cotacao': data,
                        'cotacao_compra': None,
                        'cotacao_venda': None,
                        'cotacao_media': None,
                        'timestamp': datetime.now().isoformat()
                    }
        # ✅ REGRA 3: Se é PASSADO, usar PTAX da data solicitada (com regra de dias úteis)
        elif eh_passado:
            # Se não é dia útil, buscar último dia útil anterior
            if not _eh_dia_util(data_solicitada_dt):
                ultimo_dia_util = _obter_ultimo_dia_util(data_solicitada_dt)
                if ultimo_dia_util:
                    data_para_buscar_dt = ultimo_dia_util
                    data_para_buscar = data_para_buscar_dt.strftime('%m-%d-%Y')
                    logger.info(f"⚠️ {data} não é dia útil ({calendar.day_name[data_solicitada_dt.weekday()]}). Usando último dia útil: {data_para_buscar}")
                else:
                    return {
                        'sucesso': False,
                        'erro': f'Não foi possível encontrar dia útil anterior a {data}',
                        'data_cotacao': data,
                        'cotacao_compra': None,
                        'cotacao_venda': None,
                        'cotacao_media': None,
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                data_para_buscar = data
        # ✅ REGRA 4: Se é FUTURO (>1 dia), usar última PTAX disponível
        else:  # eh_data_futura
            # Usar último dia útil disponível (hoje ou anterior)
            if _eh_dia_util(hoje_dt):
                data_para_buscar_dt = hoje_dt
                data_para_buscar = data_para_buscar_dt.strftime('%m-%d-%Y')
                logger.info(f"📅 {data} é data futura (>1 dia). Usando última PTAX disponível (HOJE): {data_para_buscar}")
            else:
                ultimo_dia_util = _obter_ultimo_dia_util(hoje_dt)
                if ultimo_dia_util:
                    data_para_buscar_dt = ultimo_dia_util
                    data_para_buscar = data_para_buscar_dt.strftime('%m-%d-%Y')
                    logger.info(f"📅 {data} é data futura (>1 dia). Usando última PTAX disponível: {data_para_buscar}")
                else:
                    return {
                        'sucesso': False,
                        'erro': f'Não foi possível encontrar dia útil anterior',
                        'data_cotacao': data,
                        'cotacao_compra': None,
                        'cotacao_venda': None,
                        'cotacao_media': None,
                        'timestamp': datetime.now().isoformat()
                    }
        
        logger.info(f"🔍 Consultando PTAX do dólar para {data} (buscando cotação de {data_para_buscar})...")
        
        # ✅ CORREÇÃO: Usar endpoint CotacaoMoedaPeriodo para buscar todas as cotações do dia
        # Isso permite selecionar a cotação correta baseada no tipo de boletim
        url = f"{BCB_PTAX_API_BASE}/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='USD'&@dataInicial='{data_para_buscar}'&@dataFinalCotacao='{data_para_buscar}'&$format=json"
        
        # Fazer requisição
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parsear JSON
        data_json = response.json()
        
        # A API retorna em 'value' (array de cotações do dia)
        if 'value' not in data_json or len(data_json['value']) == 0:
            # ✅ NOVO: Se é data futura ou hoje sem cotação, usar último dia útil disponível
            if eh_data_futura or (eh_hoje and data_para_buscar == data):
                logger.info(f"⚠️ {data} é data futura ou hoje sem cotação ainda. Buscando último dia útil disponível...")
                ultimo_dia_util = _obter_ultimo_dia_util(data_solicitada_dt)
                if ultimo_dia_util:
                    data_para_buscar_dt = ultimo_dia_util
                    data_para_buscar = data_para_buscar_dt.strftime('%m-%d-%Y')
                    logger.info(f"🔄 Tentando cotação de {data_para_buscar} (último dia útil disponível)...")
                    # Tentar novamente com último dia útil
                    url = f"{BCB_PTAX_API_BASE}/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='USD'&@dataInicial='{data_para_buscar}'&@dataFinalCotacao='{data_para_buscar}'&$format=json"
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    data_json = response.json()
            
            # Se ainda não tem cotação, retornar erro
            if 'value' not in data_json or len(data_json['value']) == 0:
                logger.warning(f"⚠️ Nenhuma cotação encontrada para {data_para_buscar}")
                return {
                    'sucesso': False,
                    'erro': f'Nenhuma cotação encontrada para {data_para_buscar}',
                    'data_cotacao': data,
                    'cotacao_compra': None,
                    'cotacao_venda': None,
                    'cotacao_media': None,
                    'timestamp': datetime.now().isoformat()
                }
        
        # ✅ NOVO: Selecionar a melhor cotação baseada no tipo de boletim
        # Prioridade: Fechamento Interbancário > Fechamento > Intermediário (mais recente) > Abertura
        cots = data_json['value']
        
        # ✅ CRÍTICO: Se é hoje e só tem Abertura (dia ainda não fechou), buscar Fechamento do dia anterior
        # ⚠️ EXCEÇÃO: Se a data solicitada é AMANHÃ, usar Abertura de HOJE (não buscar Fechamento de ontem)
        eh_data_buscada_hoje = data_para_buscar_dt.date() == datetime.now().date()
        eh_solicitada_amanha = eh_amanha  # Já calculado acima
        tem_apenas_abertura = len(cots) == 1 and cots[0].get('tipoBoletim', '').lower() == 'abertura'
        
        # Se é HOJE e só tem Abertura, buscar Fechamento do dia anterior
        # Mas se a solicitação é para AMANHÃ, usar Abertura de HOJE (não buscar Fechamento)
        if eh_data_buscada_hoje and tem_apenas_abertura and not eh_solicitada_amanha:
            # Dia ainda não fechou - buscar Fechamento do último dia útil anterior
            logger.info(f"⚠️ {data_para_buscar} só tem cotação de Abertura (dia ainda não fechou). Buscando Fechamento do último dia útil anterior...")
            ultimo_dia_util = _obter_ultimo_dia_util(data_para_buscar_dt)
            if ultimo_dia_util:
                data_fechamento = ultimo_dia_util.strftime('%m-%d-%Y')
                url_fechamento = f"{BCB_PTAX_API_BASE}/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@moeda='USD'&@dataInicial='{data_fechamento}'&@dataFinalCotacao='{data_fechamento}'&$format=json"
                try:
                    response_fechamento = requests.get(url_fechamento, timeout=10)
                    response_fechamento.raise_for_status()
                    data_json_fechamento = response_fechamento.json()
                    if 'value' in data_json_fechamento and len(data_json_fechamento['value']) > 0:
                        # Buscar Fechamento do dia anterior
                        cots_anterior = data_json_fechamento['value']
                        fechamento_anterior = None
                        for cot in cots_anterior:
                            if 'fechamento' in cot.get('tipoBoletim', '').lower():
                                fechamento_anterior = cot
                                break
                        if fechamento_anterior:
                            logger.info(f"✅ Usando Fechamento de {data_fechamento} para {data} (dia ainda não fechou)")
                            cots = [fechamento_anterior]  # Usar apenas o Fechamento do dia anterior
                            data_para_buscar_dt = ultimo_dia_util
                            data_para_buscar = data_fechamento
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao buscar Fechamento do dia anterior: {e}. Usando Abertura do dia atual.")
        
        # ✅ CORREÇÃO: Ordenar por tipo de boletim (prioridade) e depois por hora (mais recente primeiro)
        # Prioridade: Fechamento Interbancário > Fechamento > Intermediário (mais recente) > Abertura
        # O Fechamento é a cotação oficial do dia para fins fiscais
        def prioridade_boletim(cot):
            tipo = cot.get('tipoBoletim', '').lower()
            hora = cot.get('dataHoraCotacao', '')
            # Prioridade: 1=Fechamento Interbancário, 2=Fechamento, 3=Intermediário (mais recente), 4=Abertura
            if 'fechamento interbancário' in tipo or 'fechamento interbancario' in tipo:
                return (1, hora)  # Maior prioridade
            elif 'fechamento' in tipo and 'interbanc' not in tipo:
                return (2, hora)  # Fechamento normal (cotação oficial do dia)
            elif 'intermediário' in tipo or 'intermediario' in tipo:
                return (3, hora)  # Intermediário (usar mais recente se não tiver Fechamento)
            elif 'abertura' in tipo:
                return (4, hora)  # Abertura (menor prioridade - só usar se não tiver outras)
            else:
                return (5, hora)  # Outros tipos
        
        # Ordenar e pegar a melhor
        # Para Intermediário, queremos o mais recente (hora maior), então inverter ordem
        def key_sort(cot):
            prioridade, hora = prioridade_boletim(cot)
            # Para Intermediário (prioridade 3), ordenar por hora decrescente (mais recente primeiro)
            if prioridade == 3:
                # Converter hora para ordenação (usar timestamp negativo para ordem decrescente)
                # Como hora é string ISO, podemos ordenar diretamente (maior = mais recente)
                return (prioridade, hora)  # Ordenar depois com reverse=True para Intermediário
            else:
                return (prioridade, hora)
        
        # Separar Intermediários dos outros para ordenar separadamente
        intermediarios = [c for c in cots if prioridade_boletim(c)[0] == 3]
        outros = [c for c in cots if prioridade_boletim(c)[0] != 3]
        
        # Ordenar outros normalmente
        outros_ordenados = sorted(outros, key=key_sort)
        # Ordenar Intermediários por hora decrescente (mais recente primeiro)
        intermediarios_ordenados = sorted(intermediarios, key=lambda x: prioridade_boletim(x)[1], reverse=True)
        
        # Combinar: outros primeiro, depois Intermediários
        cots_ordenadas = outros_ordenados + intermediarios_ordenados
        cotacao = cots_ordenadas[0]  # Melhor cotação
        
        # Extrair valores
        data_cotacao = cotacao.get('dataHoraCotacao', '').split('T')[0] if cotacao.get('dataHoraCotacao') else data
        tipo_boletim = cotacao.get('tipoBoletim', 'N/A')
        cotacao_compra = float(cotacao.get('cotacaoCompra', 0))
        cotacao_venda = float(cotacao.get('cotacaoVenda', 0))
        cotacao_media = (cotacao_compra + cotacao_venda) / 2.0
        
        resultado = {
            'data_cotacao': data_cotacao,
            'cotacao_compra': cotacao_compra,
            'cotacao_venda': cotacao_venda,
            'cotacao_media': cotacao_media,
            'tipo_boletim': tipo_boletim,
            'data_solicitada': data,  # ✅ NOVO: Data que foi solicitada (pode ser diferente de data_cotacao)
            'data_cotacao_real': data_para_buscar,  # ✅ NOVO: Data real da cotação (último dia útil se necessário)
            'timestamp': datetime.now().isoformat(),
            'sucesso': True,
            'erro': None
        }
        
        # ✅ Log informativo se usou dia útil anterior
        if data_para_buscar != data:
            logger.info(f"✅ PTAX obtida para {data}: R$ {cotacao_media:.4f} (usando cotação de {data_para_buscar}, tipo: {tipo_boletim})")
        else:
            logger.info(f"✅ PTAX obtida: R$ {cotacao_media:.4f} (compra: {cotacao_compra:.4f}, venda: {cotacao_venda:.4f}, tipo: {tipo_boletim})")
        
        return resultado
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao consultar PTAX: {e}")
        return {
            'sucesso': False,
            'erro': f"Erro de conexão: {str(e)}",
            'data_cotacao': data,
            'cotacao_compra': None,
            'cotacao_venda': None,
            'cotacao_media': None,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Erro ao processar PTAX: {e}", exc_info=True)
        return {
            'sucesso': False,
            'erro': f"Erro ao processar resposta: {str(e)}",
            'data_cotacao': data,
            'cotacao_compra': None,
            'cotacao_venda': None,
            'cotacao_media': None,
            'timestamp': datetime.now().isoformat()
        }


def obter_ptax_dia_util_anterior(data: str) -> Optional[Dict[str, Any]]:
    """
    Tenta obter PTAX do último dia útil anterior à data especificada.
    Útil quando a data é fim de semana ou feriado.
    """
    try:
        # Parsear data
        partes = data.split('-')
        if len(partes) != 3:
            return None
        
        mes, dia, ano = int(partes[0]), int(partes[1]), int(partes[2])
        data_dt = datetime(ano, mes, dia)
        
        # Tentar até 5 dias anteriores (para pegar dia útil)
        for i in range(1, 6):
            data_anterior = data_dt - timedelta(days=i)
            data_str = data_anterior.strftime('%m-%d-%Y')
            
            logger.info(f"🔍 Tentando PTAX para {data_str}...")
            
            # Chamar API diretamente (sem recursão para evitar loop)
            url = f"{BCB_PTAX_API_BASE}/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{data_str}'&$format=json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data_json = response.json()
            
            if 'value' in data_json and len(data_json['value']) > 0:
                cotacao = data_json['value'][0]
                data_cotacao = cotacao.get('dataHoraCotacao', '').split('T')[0] if cotacao.get('dataHoraCotacao') else data_str
                cotacao_compra = float(cotacao.get('cotacaoCompra', 0))
                cotacao_venda = float(cotacao.get('cotacaoVenda', 0))
                cotacao_media = (cotacao_compra + cotacao_venda) / 2.0
                
                resultado = {
                    'data_cotacao': data_cotacao,
                    'cotacao_compra': cotacao_compra,
                    'cotacao_venda': cotacao_venda,
                    'cotacao_media': cotacao_media,
                    'timestamp': datetime.now().isoformat(),
                    'sucesso': True,
                    'erro': None,
                    'data_original_solicitada': data,
                    'data_util_encontrada': data_str
                }
                logger.info(f"✅ PTAX encontrada para {data_str}: R$ {cotacao_media:.4f}")
                return resultado
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar dia útil anterior: {e}")
        return None


def obter_ptax_periodo(data_inicio: str, data_fim: str) -> Optional[list]:
    """
    Obtém cotações PTAX para um período.
    
    Args:
        data_inicio: Data inicial (MM-DD-YYYY)
        data_fim: Data final (MM-DD-YYYY)
    
    Returns:
        Lista de dicts com cotações do período
    """
    try:
        # Converter para formato da API (YYYY-MM-DD)
        partes_inicio = data_inicio.split('-')
        partes_fim = data_fim.split('-')
        
        if len(partes_inicio) != 3 or len(partes_fim) != 3:
            return None
        
        data_inicio_api = f"{partes_inicio[2]}-{partes_inicio[0]}-{partes_inicio[1]}"
        data_fim_api = f"{partes_fim[2]}-{partes_fim[0]}-{partes_fim[1]}"
        
        # URL da API para período
        url = f"{BCB_PTAX_API_BASE}/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='{data_inicio_api}'&@dataFinalCotacao='{data_fim_api}'&$format=json"
        
        logger.info(f"🔍 Consultando PTAX do período {data_inicio} a {data_fim}...")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data_json = response.json()
        
        if 'value' not in data_json:
            return []
        
        resultados = []
        for cotacao in data_json['value']:
            data_cotacao = cotacao.get('dataHoraCotacao', '').split('T')[0] if cotacao.get('dataHoraCotacao') else None
            cotacao_compra = float(cotacao.get('cotacaoCompra', 0))
            cotacao_venda = float(cotacao.get('cotacaoVenda', 0))
            cotacao_media = (cotacao_compra + cotacao_venda) / 2.0
            
            resultados.append({
                'data_cotacao': data_cotacao,
                'cotacao_compra': cotacao_compra,
                'cotacao_venda': cotacao_venda,
                'cotacao_media': cotacao_media
            })
        
        logger.info(f"✅ {len(resultados)} cotações encontradas no período")
        
        return resultados
        
    except Exception as e:
        logger.error(f"❌ Erro ao consultar PTAX do período: {e}", exc_info=True)
        return None


# Teste rápido
if __name__ == "__main__":
    print("🔍 Testando PTAX do dólar...")
    
    # Teste 1: PTAX de hoje
    print("\n1. PTAX de hoje:")
    ptax_hoje = obter_ptax_dolar()
    if ptax_hoje and ptax_hoje.get('sucesso'):
        print(f"   Data: {ptax_hoje['data_cotacao']}")
        print(f"   Compra: R$ {ptax_hoje['cotacao_compra']:.4f}")
        print(f"   Venda: R$ {ptax_hoje['cotacao_venda']:.4f}")
        print(f"   Média: R$ {ptax_hoje['cotacao_media']:.4f}")
    else:
        print(f"   ❌ Erro: {ptax_hoje.get('erro') if ptax_hoje else 'Resposta vazia'}")
    
    # Teste 2: PTAX de data específica
    print("\n2. PTAX de 12-15-2025:")
    ptax_data = obter_ptax_dolar('12-15-2025')
    if ptax_data and ptax_data.get('sucesso'):
        print(f"   Data: {ptax_data['data_cotacao']}")
        print(f"   Média: R$ {ptax_data['cotacao_media']:.4f}")
    else:
        print(f"   ❌ Erro: {ptax_data.get('erro') if ptax_data else 'Resposta vazia'}")













