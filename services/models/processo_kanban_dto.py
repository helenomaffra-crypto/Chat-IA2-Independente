"""
DTO (Data Transfer Object) para processos do Kanban.
Estrutura padronizada para dados de processos de importação.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
import json


@dataclass
class ProcessoKanbanDTO:
    """DTO para processo do Kanban - estrutura padronizada"""
    
    # Identificação
    processo_referencia: str  # Ex: "ALH.0168/25"
    id_processo_importacao: Optional[int] = None
    id_importacao: Optional[int] = None
    
    # Status
    etapa_kanban: str = ""  # Ex: "PEDIDO", "DI_REGISTRADA", etc.
    modal: str = ""  # "Marítimo", "Aéreo", etc.
    
    # Documentos
    numero_ce: Optional[str] = None
    numero_di: Optional[str] = None
    numero_duimp: Optional[str] = None
    numero_dta: Optional[str] = None  # DTA (Declaração de Trânsito Aduaneiro)
    documento_despacho: Optional[str] = None  # Tipo de documento de despacho: "DTA", "DI" ou "DUIMP"
    numero_documento_despacho: Optional[str] = None  # Número do documento de despacho (DTA, DI ou DUIMP)
    bl_house: Optional[str] = None  # BL (marítimo) ou AWB (aéreo) - depende do modal
    master_bl: Optional[str] = None
    
    # Status dos documentos
    situacao_ce: Optional[str] = None
    situacao_di: Optional[str] = None
    situacao_entrega: Optional[str] = None
    
    # LPCO (Licença de Processamento de Conhecimento de Origem)
    numero_lpco: Optional[str] = None  # Número do LPCO (ex: "I2501211316")
    situacao_lpco: Optional[str] = None  # Status do LPCO (ex: "Deferido", "Indeferido")
    canal_lpco: Optional[str] = None  # Canal do LPCO (ex: "VERDE", "AMARELO")
    data_situacao_lpco: Optional[datetime] = None  # Data da situação atual do LPCO
    lpco_details: List[Dict[str, Any]] = field(default_factory=list)  # Lista completa de LPCOs
    
    # Pendencias
    tem_pendencias: bool = False
    pendencia_icms: Optional[str] = None
    pendencia_frete: Optional[bool] = None
    
    # Datas
    data_criacao: Optional[datetime] = None
    data_embarque: Optional[datetime] = None
    data_desembaraco: Optional[datetime] = None
    data_entrega: Optional[datetime] = None
    
    # Datas de Chegada ao Porto (para queries rápidas: "quais chegaram hoje/semana/mês")
    data_destino_final: Optional[datetime] = None  # Chegada da carga ao porto (prioridade 1)
    data_armazenamento: Optional[datetime] = None  # Armazenamento (prioridade 2)
    data_situacao_carga_ce: Optional[datetime] = None  # Situação da carga no CE (prioridade 3)
    data_atracamento: Optional[datetime] = None  # Atracação do navio (prioridade 5)
    
    # ETA e Transporte (do Kanban - shipgov2)
    eta_iso: Optional[datetime] = None  # ETA do Kanban (destino_data_chegada)
    porto_codigo: Optional[str] = None  # Código do porto destino
    porto_nome: Optional[str] = None  # Nome do porto destino
    nome_navio: Optional[str] = None  # Nome do navio (dos eventos do shipgov2)
    status_shipsgo: Optional[str] = None  # Status do ShipsGo (ex: "SAILING", "ARRIVED", etc.)
    
    # Dados completos (JSON original)
    dados_completos: Dict[str, Any] = field(default_factory=dict)
    
    # Metadados
    atualizado_em: Optional[datetime] = None
    fonte: str = "kanban"  # "kanban", "sql_server", "sqlite"
    
    @classmethod
    def from_kanban_json(cls, json_data: Dict[str, Any]) -> 'ProcessoKanbanDTO':
        """Cria DTO a partir do JSON da API Kanban"""
        dados = json_data.get('dados_processo_kanban', {})
        
        # Helper para buscar campo em múltiplos lugares (raiz ou dentro de dados_processo_kanban)
        def get_field(key_raiz: str, key_dados: str = None, default=None):
            """Busca campo na raiz ou dentro de dados_processo_kanban"""
            # Tentar na raiz primeiro
            valor = json_data.get(key_raiz, default)
            if valor is not None and valor != default:
                return valor
            # Tentar dentro de dados_processo_kanban
            if key_dados:
                return dados.get(key_dados, default)
            # Tentar com snake_case dentro de dados
            key_snake = key_raiz.replace(' ', '_').lower()
            return dados.get(key_snake, default)
        
        # Parse de datas
        def parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                # Tentar vários formatos
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%d",
                    "%d/%m/%Y %H:%M:%S",
                    "%d/%m/%Y"
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_str.replace('Z', '').split('.')[0], fmt)
                    except:
                        continue
                # Se nenhum formato funcionou, tentar parser automático (se disponível)
                try:
                    from dateutil import parser
                    return parser.parse(date_str)
                except ImportError:
                    # dateutil não instalado, retornar None
                    pass
            except:
                pass
            return None
        
        # Buscar campos - pode estar na raiz OU dentro de dados_processo_kanban
        numero_ce = json_data.get('ceMercante') or dados.get('numero_ce') or json_data.get('numero_ce')
        numero_di = json_data.get('numeroDi') or dados.get('numero_di') or json_data.get('numero_di')
        numero_duimp_raw = json_data.get('duimp')
        numero_duimp = None
        if numero_duimp_raw:
            if isinstance(numero_duimp_raw, list) and len(numero_duimp_raw) > 0:
                numero_duimp = numero_duimp_raw[0].get('numero') if isinstance(numero_duimp_raw[0], dict) else str(numero_duimp_raw[0])
            elif isinstance(numero_duimp_raw, dict):
                numero_duimp = numero_duimp_raw.get('numero')
            elif isinstance(numero_duimp_raw, str):
                numero_duimp = numero_duimp_raw
        if not numero_duimp:
            numero_duimp = dados.get('numero_duimp')
        
        # ✅ IMPORTANTE: bl_house contém BL (marítimo) ou AWB (aéreo) - depende do modal
        # No JSON do Kanban existe apenas um campo para BL/AWB, o que define é o modal:
        # - Modal "Aéreo" → AWB (usado para consultar CCT)
        # - Modal "Marítimo" → BL (usado para consultar CE)
        bl_house = json_data.get('blHouseNovo') or dados.get('bl_house_novo') or json_data.get('bl_house')
        master_bl = json_data.get('masterBl') or dados.get('master_bl') or json_data.get('master_bl')
        
        # ✅ NOVO: Extrair documentoDespacho e numeroDocumentoDespacho do CE
        # Esses campos indicam o tipo de documento de despacho (DTA, DI ou DUIMP) e seu número
        # ⚠️ REGRA DE NEGÓCIO: O JSON mantém histórico, mas quando tem DI/DUIMP, prevalece a DI/DUIMP
        # Um processo só está "em DTA" se tem DTA E NÃO tem DI E NÃO tem DUIMP
        documento_despacho = json_data.get('documentoDespacho')
        numero_documento_despacho = json_data.get('numeroDocumentoDespacho')
        numero_dta = None
        
        # ✅ PRIORIDADE: DI/DUIMP prevalece sobre DTA
        # Se documentoDespacho é "DI", atualizar numero_di (prevalece sobre DTA)
        if documento_despacho and documento_despacho.upper() == 'DI' and numero_documento_despacho:
            if not numero_di:  # Só atualizar se ainda não tiver
                numero_di = numero_documento_despacho
            # Se tem DI, NÃO preencher numero_dta (DI prevalece)
        # Se documentoDespacho é "DUIMP", atualizar numero_duimp (prevalece sobre DTA)
        elif documento_despacho and documento_despacho.upper() == 'DUIMP' and numero_documento_despacho:
            if not numero_duimp:  # Só atualizar se ainda não tiver
                numero_duimp = numero_documento_despacho
            # Se tem DUIMP, NÃO preencher numero_dta (DUIMP prevalece)
        # Se documentoDespacho é "DTA", extrair o número (só se NÃO tiver DI nem DUIMP)
        elif documento_despacho and documento_despacho.upper() == 'DTA' and numero_documento_despacho:
            # Só preencher DTA se NÃO tiver DI nem DUIMP (regra de negócio)
            if not numero_di and not numero_duimp:
                numero_dta = numero_documento_despacho
        
        # ✅ Extrair dados do LPCO
        lpco_details = json_data.get('lpcoDetails', [])
        numero_lpco = None
        situacao_lpco = None
        canal_lpco = None
        data_situacao_lpco = None
        
        if lpco_details and isinstance(lpco_details, list) and len(lpco_details) > 0:
            # Pegar o primeiro LPCO (geralmente há apenas um)
            primeiro_lpco = lpco_details[0]
            if isinstance(primeiro_lpco, dict):
                numero_lpco = primeiro_lpco.get('LPCO')
                situacao_lpco = primeiro_lpco.get('situacao')
                canal_lpco = primeiro_lpco.get('canal')
                data_situacao_lpco = parse_datetime(primeiro_lpco.get('dataSituacaoAtual'))
        
        # ✅ Extrair ETA e informações de transporte do shipgov2
        shipgov2 = json_data.get('shipgov2', {})
        eta_iso = None
        porto_codigo = None
        porto_nome = None
        nome_navio = None
        status_shipsgo = None
        
        # ✅ NOVO: Buscar POD/ETA de múltiplas fontes (prioridade: shipgov2 > POD direto > dataPrevisaoChegada)
        # 1. Tentar shipgov2.destino_data_chegada (mais confiável - tracking de navios)
        if isinstance(shipgov2, dict):
            porto_codigo = shipgov2.get('destino_codigo')
            porto_nome = shipgov2.get('destino_nome')
            # ✅ CORREÇÃO (escala/transbordo): usar eventos do POD para ETA/navio/status
            try:
                from services.utils.shipgov2_tracking_utils import resumir_shipgov2_para_painel

                resumo = resumir_shipgov2_para_painel(shipgov2)
                # ETA do POD: DISC(destino) > ARRV(destino) > destino_data_chegada
                eta_iso = resumo.eta_pod
                # Navio do trecho final (POD) quando houver
                nome_navio = resumo.navio_pod
                # Status derivado (evita ficar "BOOKED" indevidamente)
                status_shipsgo = resumo.status
            except Exception:
                # Fallback: manter comportamento antigo (melhor ter algo do que quebrar)
                eta_iso = parse_datetime(shipgov2.get('destino_data_chegada'))
                status_shipsgo = shipgov2.get('status')
                eventos = shipgov2.get('eventos', [])
                if isinstance(eventos, list):
                    for evento in eventos:
                        if isinstance(evento, dict) and evento.get('navio_shipv2'):
                            nome_navio = evento.get('navio_shipv2')
                            break
        
        # 2. Se não encontrou no shipgov2, tentar POD direto do JSON (campo do Kanban)
        if not eta_iso:
            # Tentar campo "pod" (Port of Discharge) - pode estar em diferentes formatos
            # ✅ EXPANDIDO: Buscar POD em múltiplos formatos possíveis
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
            if pod_data:
                # POD pode ser um objeto com data ou uma string/data direta
                if isinstance(pod_data, dict):
                    eta_iso = (
                        parse_datetime(pod_data.get('data')) or 
                        parse_datetime(pod_data.get('eta')) or 
                        parse_datetime(pod_data.get('dataChegada')) or
                        parse_datetime(pod_data.get('data_chegada')) or
                        parse_datetime(pod_data.get('dataPod')) or
                        parse_datetime(pod_data.get('data_pod'))
                    )
                elif isinstance(pod_data, str):
                    # ✅ NOVO: Tentar parsear string no formato DD/MM/YY ou DD/MM/YYYY
                    eta_iso = parse_datetime(pod_data)
                    if not eta_iso and '/' in pod_data:
                        # Tentar formato brasileiro DD/MM/YY ou DD/MM/YYYY
                        try:
                            # datetime já está importado no topo do arquivo
                            partes = pod_data.strip().split('/')
                            if len(partes) == 3:
                                dia, mes, ano = partes
                                if len(ano) == 2:
                                    ano = '20' + ano  # Assumir século 21
                                data_str = f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
                                eta_iso = parse_datetime(data_str)
                        except:
                            pass
                else:
                    eta_iso = parse_datetime(str(pod_data))
        
        # 3. Se ainda não encontrou, tentar dataPrevisaoChegada (fallback)
        if not eta_iso:
            eta_iso = parse_datetime(json_data.get('dataPrevisaoChegada')) or parse_datetime(json_data.get('previsaoChegada'))
        
        # Nome do navio - também pode estar na raiz do JSON
        if not nome_navio:
            nome_navio = json_data.get('nomeNavio')
        
        return cls(
            processo_referencia=json_data.get('numeroPedido', ''),
            id_processo_importacao=json_data.get('id_processo_importacao'),
            id_importacao=json_data.get('idImportacao'),
            etapa_kanban=json_data.get('etapaKanban', ''),
            modal=json_data.get('modal', ''),
            numero_ce=numero_ce,
            numero_di=numero_di,
            numero_duimp=numero_duimp,
            numero_dta=numero_dta,  # DTA (Declaração de Trânsito Aduaneiro)
            documento_despacho=documento_despacho,  # Tipo: "DTA", "DI" ou "DUIMP"
            numero_documento_despacho=numero_documento_despacho,  # Número do documento
            bl_house=bl_house,  # BL (marítimo) ou AWB (aéreo)
            master_bl=master_bl,
            situacao_ce=json_data.get('situacaoCargaCe') or json_data.get('situacao_ce'),
            situacao_di=json_data.get('situacaoDi') or json_data.get('situacao_di'),
            situacao_entrega=json_data.get('situacaoEntregaCarga') or json_data.get('situacao_entrega'),
            numero_lpco=numero_lpco,
            situacao_lpco=situacao_lpco,
            canal_lpco=canal_lpco,
            data_situacao_lpco=data_situacao_lpco,
            lpco_details=lpco_details if isinstance(lpco_details, list) else [],
            tem_pendencias=json_data.get('pendencias', False),
            pendencia_icms=json_data.get('pendenciaIcms') or json_data.get('pendencia_icms'),
            pendencia_frete=json_data.get('pendenciaFrete'),
            data_criacao=parse_datetime(json_data.get('data_criacao')),
            data_embarque=parse_datetime(json_data.get('dataEmbarque')),
            data_desembaraco=parse_datetime(json_data.get('dataDesembaraco')),
            data_entrega=parse_datetime(json_data.get('dataEntrega')),
            # Datas de chegada ao porto (para queries rápidas)
            data_destino_final=parse_datetime(json_data.get('dataDestinoFinal')),
            data_armazenamento=parse_datetime(json_data.get('dataArmazenamento')),
            data_situacao_carga_ce=parse_datetime(json_data.get('dataSituacaoCargaCe')),
            data_atracamento=parse_datetime(json_data.get('dataAtracamento')),
            eta_iso=eta_iso,
            porto_codigo=porto_codigo,
            porto_nome=porto_nome,
            nome_navio=nome_navio,
            status_shipsgo=status_shipsgo,
            dados_completos=json_data,
            fonte="kanban"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte DTO para dicionário"""
        return {
            'processo_referencia': self.processo_referencia,
            'id_processo_importacao': self.id_processo_importacao,
            'id_importacao': self.id_importacao,
            'etapa_kanban': self.etapa_kanban,
            'modal': self.modal,
            'numero_ce': self.numero_ce,
            'numero_di': self.numero_di,
            'numero_duimp': self.numero_duimp,
            'numero_dta': self.numero_dta,  # DTA
            'documento_despacho': self.documento_despacho,  # Tipo: "DTA", "DI" ou "DUIMP"
            'numero_documento_despacho': self.numero_documento_despacho,  # Número do documento
            'bl_house': self.bl_house,  # BL (marítimo) ou AWB (aéreo)
            'master_bl': self.master_bl,
            'situacao_ce': self.situacao_ce,
            'situacao_di': self.situacao_di,
            'situacao_entrega': self.situacao_entrega,
            'numero_lpco': self.numero_lpco,
            'situacao_lpco': self.situacao_lpco,
            'canal_lpco': self.canal_lpco,
            'data_situacao_lpco': self.data_situacao_lpco.isoformat() if self.data_situacao_lpco else None,
            'tem_pendencias': self.tem_pendencias,
            'pendencia_icms': self.pendencia_icms,
            'pendencia_frete': self.pendencia_frete,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_embarque': self.data_embarque.isoformat() if self.data_embarque else None,
            'data_desembaraco': self.data_desembaraco.isoformat() if self.data_desembaraco else None,
            'data_entrega': self.data_entrega.isoformat() if self.data_entrega else None,
            'data_destino_final': self.data_destino_final.isoformat() if self.data_destino_final else None,
            'data_armazenamento': self.data_armazenamento.isoformat() if self.data_armazenamento else None,
            'data_situacao_carga_ce': self.data_situacao_carga_ce.isoformat() if self.data_situacao_carga_ce else None,
            'data_atracamento': self.data_atracamento.isoformat() if self.data_atracamento else None,
            'eta_iso': self.eta_iso.isoformat() if self.eta_iso else None,
            'porto_codigo': self.porto_codigo,
            'porto_nome': self.porto_nome,
            'nome_navio': self.nome_navio,
            'status_shipsgo': self.status_shipsgo,
            'fonte': self.fonte
        }
    
    def to_json_str(self) -> str:
        """Serializa DTO para JSON string"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)

