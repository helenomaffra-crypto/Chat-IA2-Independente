"""
Serviço para geração de extrato PDF de extratos bancários (BB e Santander).

Formato contábil padrão:
- Coluna Data
- Coluna Histórico (com quebra de linha)
- Coluna Crédito
- Coluna Débito
- Coluna Saldo
"""
import logging
import io
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtratoBancarioPdfService:
    """
    Serviço para geração de PDFs de extratos bancários.
    
    Suporta:
    - Banco do Brasil
    - Santander
    """
    
    def __init__(self):
        """Inicializa o serviço."""
        self.downloads_dir = Path('downloads')
        self.downloads_dir.mkdir(exist_ok=True)
        # Limpar PDFs antigos (mais de 1 hora) para não saturar o diretório
        self._limpar_pdfs_antigos()

    def _buscar_processos_conciliados_por_hash(self, hashes: List[str]) -> Dict[str, str]:
        """
        Busca processos vinculados (conciliação) no SQL Server, por hash_dados.

        Retorna um mapa: hash_dados -> "PROC.0001/26, PROC.0002/26".

        Observação:
        - Se SQL Server estiver indisponível, retorna {} (sem bloquear geração de PDF).
        """
        try:
            hashes = [h for h in (hashes or []) if isinstance(h, str) and h.strip()]
            if not hashes:
                return {}

            # Evitar query gigante
            hashes = list(dict.fromkeys(hashes))[:500]

            from utils.sql_server_adapter import get_sql_adapter

            adapter = get_sql_adapter()
            if not adapter:
                return {}
            try:
                if hasattr(adapter, "test_connection") and not adapter.test_connection():
                    return {}
            except Exception:
                # Não bloquear por falha no teste; tentativa de query abaixo pode funcionar.
                pass

            # hashes são hex (sha256), mas ainda assim escapar aspas por segurança
            hashes_sql_parts = []
            for h in hashes:
                hashes_sql_parts.append("'" + h.replace("'", "''") + "'")
            hashes_sql = ", ".join(hashes_sql_parts)

            query = f"""
                SELECT
                    mb.hash_dados,
                    STRING_AGG(p.processo_referencia, ', ') AS processos
                FROM dbo.MOVIMENTACAO_BANCARIA mb
                JOIN (
                    SELECT DISTINCT
                        ltd.id_movimentacao_bancaria,
                        LTRIM(RTRIM(ltd.processo_referencia)) AS processo_referencia
                    FROM dbo.LANCAMENTO_TIPO_DESPESA ltd
                    WHERE ltd.processo_referencia IS NOT NULL
                      AND LTRIM(RTRIM(ltd.processo_referencia)) != ''
                ) p
                  ON p.id_movimentacao_bancaria = mb.id_movimentacao
                WHERE mb.hash_dados IN ({hashes_sql})
                GROUP BY mb.hash_dados
            """

            r = adapter.execute_query(query, database=getattr(adapter, "database", None))
            if not (r and r.get("success")):
                return {}
            rows = r.get("data") or []
            out: Dict[str, str] = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                h = (row.get("hash_dados") or "").strip()
                proc = (row.get("processos") or "").strip()
                if h and proc:
                    out[h] = proc
            return out
        except Exception:
            # Silencioso: não atrapalhar geração de PDF
            return {}
    
    def _limpar_pdfs_antigos(self, horas_antigas: int = 1):
        """
        Remove PDFs antigos do diretório downloads para não saturar.
        
        Args:
            horas_antigas: Quantas horas um PDF deve ter para ser considerado antigo (padrão: 1 hora)
        """
        try:
            if not self.downloads_dir.exists():
                return
            
            agora = time.time()
            limite_tempo = horas_antigas * 3600  # Converter horas para segundos
            
            arquivos_removidos = 0
            for arquivo in self.downloads_dir.glob('Extrato-Bancario-*.pdf'):
                try:
                    # Verificar idade do arquivo
                    tempo_modificacao = arquivo.stat().st_mtime
                    idade_segundos = agora - tempo_modificacao
                    
                    if idade_segundos > limite_tempo:
                        arquivo.unlink()
                        arquivos_removidos += 1
                        logger.debug(f'PDF antigo removido: {arquivo.name}')
                except Exception as e:
                    logger.warning(f'Erro ao remover PDF antigo {arquivo.name}: {e}')
            
            if arquivos_removidos > 0:
                logger.info(f'✅ {arquivos_removidos} PDF(s) antigo(s) removido(s) do diretório downloads')
        except Exception as e:
            logger.warning(f'Erro ao limpar PDFs antigos: {e}')
    
    def _formatar_data_bb(self, data_int: int) -> str:
        """
        Formata data do BB (DDMMAAAA) para DD/MM/AAAA.
        
        Args:
            data_int: Data no formato DDMMAAAA (ex: 6012026)
        
        Returns:
            Data formatada (ex: "06/01/2026")
        """
        if not data_int or data_int == 0:
            return ""
        
        data_str = str(data_int).zfill(8)  # Garantir 8 dígitos
        dia = data_str[0:2]
        mes = data_str[2:4]
        ano = data_str[4:8]
        
        return f"{dia}/{mes}/{ano}"
    
    def _formatar_data_santander(self, data_str: str) -> str:
        """
        Formata data do Santander (YYYY-MM-DD) para DD/MM/YYYY.
        
        Args:
            data_str: Data no formato YYYY-MM-DD (ex: "2026-01-06")
        
        Returns:
            Data formatada (ex: "06/01/2026")
        """
        if not data_str:
            return ""
        
        try:
            # Tentar parsear data ISO
            if 'T' in data_str:
                data_str = data_str.split('T')[0]
            
            dt = datetime.strptime(data_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except:
            return data_str
    
    def _calcular_saldo_acumulado(self, lancamentos: list, banco: str) -> list:
        """
        Calcula saldo acumulado para cada lançamento.
        
        Args:
            lancamentos: Lista de lançamentos ordenados (mais antigo primeiro)
            banco: "BB" ou "SANTANDER"
        
        Returns:
            Lista de lançamentos com saldo acumulado
        """
        saldo_atual = 0.0
        lancamentos_com_saldo = []
        
        for lanc in lancamentos:
            if banco == "BB":
                valor = float(lanc.get('valorLancamento', 0))
                sinal = lanc.get('indicadorSinalLancamento', '')
                if sinal == 'C':
                    saldo_atual += valor
                elif sinal == 'D':
                    saldo_atual -= valor
            else:  # SANTANDER
                # ✅ CORREÇÃO: Tratar amount que pode ser string, dict, número ou lista
                amount_obj = lanc.get('amount')
                if isinstance(amount_obj, str):
                    # ✅ CORREÇÃO: Santander retorna amount como STRING!
                    try:
                        valor = float(amount_obj)
                    except (ValueError, TypeError):
                        valor = 0.0
                elif isinstance(amount_obj, dict):
                    valor = float(amount_obj.get('amount', 0) or 0)
                elif isinstance(amount_obj, (int, float)):
                    valor = float(amount_obj)
                elif isinstance(amount_obj, list) and len(amount_obj) > 0:
                    primeiro_item = amount_obj[0]
                    if isinstance(primeiro_item, dict):
                        valor = float(primeiro_item.get('amount', 0) or 0)
                    elif isinstance(primeiro_item, (int, float)):
                        valor = float(primeiro_item)
                    elif isinstance(primeiro_item, str):
                        try:
                            valor = float(primeiro_item)
                        except (ValueError, TypeError):
                            valor = 0.0
                    else:
                        valor = 0.0
                else:
                    valor = 0.0
                # ✅ CORREÇÃO: Santander usa 'creditDebitType' com valores 'CREDITO'/'DEBITO'
                tipo = lanc.get('creditDebitType') or lanc.get('transactionType', '')
                if tipo in ['CREDIT', 'CREDITO']:
                    saldo_atual += valor
                elif tipo in ['DEBIT', 'DEBITO']:
                    saldo_atual -= valor
            
            # Adicionar saldo ao lançamento
            lanc_com_saldo = lanc.copy()
            # ✅ CORREÇÃO: Garantir que saldo_acumulado nunca seja None
            lanc_com_saldo['saldo_acumulado'] = round(float(saldo_atual or 0), 2)
            lancamentos_com_saldo.append(lanc_com_saldo)
        
        return lancamentos_com_saldo
    
    def gerar_pdf_extrato_bb(
        self,
        agencia: str,
        conta: str,
        lancamentos: list,
        data_inicio: datetime,
        data_fim: datetime,
        saldo_inicial: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Gera PDF do extrato do Banco do Brasil no formato contábil.
        
        Args:
            agencia: Número da agência
            conta: Número da conta
            lancamentos: Lista de lançamentos do extrato
            data_inicio: Data inicial do período
            data_fim: Data final do período
            saldo_inicial: Saldo inicial (opcional)
        
        Returns:
            Dict com resultado da geração do PDF
        """
        try:
            from flask import render_template
            from app import app
            
            if not lancamentos:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum lançamento encontrado',
                    'resposta': '❌ Não foi possível gerar o PDF: nenhum lançamento encontrado no período.'
                }
            
            # Ordenar lançamentos por data (mais antigo primeiro para cálculo de saldo)
            def converter_data_para_ordenacao(data_int) -> int:
                """Converte DDMMAAAA para YYYYMMDD para ordenação correta"""
                # ✅ CORREÇÃO: Tratar None e valores inválidos - SEMPRE retornar int
                try:
                    if data_int is None:
                        return 0
                    if data_int == 0:
                        return 0
                    data_int = int(data_int)
                    data_str = str(data_int).zfill(8)
                    if len(data_str) != 8:
                        return 0
                    dia = data_str[0:2]
                    mes = data_str[2:4]
                    ano = data_str[4:8]
                    resultado = int(f"{ano}{mes}{dia}")
                    return resultado if resultado > 0 else 0
                except (ValueError, TypeError, AttributeError):
                    return 0
            
            # ✅ CORREÇÃO: Garantir que lancamentos é uma lista de dicionários
            if not isinstance(lancamentos, list):
                lancamentos = []
            
            # Filtrar apenas itens que são dicionários
            lancamentos_validos = [l for l in lancamentos if isinstance(l, dict)]
            
            if not lancamentos_validos:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum lançamento válido encontrado',
                    'resposta': '❌ Não foi possível gerar o PDF: nenhum lançamento válido encontrado.'
                }
            
            # ✅ NOVO (24/01/2026): Enriquecer "Histórico" do PDF com processos conciliados (se houver)
            try:
                from services.banco_sincronizacao_service import BancoSincronizacaoService

                hash_svc = BancoSincronizacaoService.__new__(BancoSincronizacaoService)  # evita init (sem APIs)
                hashes = []
                for l in lancamentos_validos:
                    try:
                        h = hash_svc.gerar_hash_lancamento(l, agencia=str(agencia), conta=str(conta), banco="BB")
                        if h:
                            l["_hash_dados"] = h
                            hashes.append(h)
                    except Exception:
                        continue

                proc_map = self._buscar_processos_conciliados_por_hash(hashes)
                if proc_map:
                    for l in lancamentos_validos:
                        h = l.get("_hash_dados")
                        if h and h in proc_map:
                            l["processos_conciliados"] = proc_map[h]
            except Exception:
                pass

            lancamentos_ordenados = sorted(
                lancamentos_validos,
                key=lambda x: converter_data_para_ordenacao(x.get('dataLancamento') if isinstance(x, dict) else None)
            )
            
            # Calcular saldo acumulado
            # ✅ CORREÇÃO: Verificar se o primeiro lançamento é "SALDO ANTERIOR"
            if saldo_inicial is None:
                # Tentar calcular saldo inicial baseado no primeiro lançamento
                if lancamentos_ordenados:
                    primeiro_lanc = lancamentos_ordenados[0]
                    descricao_primeiro = str(primeiro_lanc.get('textoDescricaoHistorico', '')).upper()
                    
                    # ✅ CORREÇÃO: Se o primeiro lançamento é "SALDO ANTERIOR", usar o valor dele como saldo inicial
                    if 'SALDO ANTERIOR' in descricao_primeiro or 'SALDO ANTERIOR' in descricao_primeiro:
                        primeiro_valor = float(primeiro_lanc.get('valorLancamento', 0) or 0)
                        primeiro_sinal = primeiro_lanc.get('indicadorSinalLancamento', '')
                        
                        # Se é crédito, o valor já é o saldo inicial
                        if primeiro_sinal == 'C':
                            saldo_inicial = primeiro_valor
                        # Se é débito, o saldo inicial é negativo
                        elif primeiro_sinal == 'D':
                            saldo_inicial = -primeiro_valor
                        else:
                            # Se não tem sinal, assumir que é o saldo inicial direto
                            saldo_inicial = primeiro_valor
                        
                        logger.info(f"✅ Saldo inicial extraído de 'SALDO ANTERIOR': R$ {saldo_inicial:,.2f}")
                    else:
                        # Tentar calcular saldo inicial baseado no primeiro lançamento normal
                        primeiro_valor = float(primeiro_lanc.get('valorLancamento', 0) or 0)
                        primeiro_sinal = primeiro_lanc.get('indicadorSinalLancamento', '')
                        primeiro_saldo_raw = primeiro_lanc.get('saldo_acumulado')
                        
                        # ✅ CORREÇÃO: Tratar None corretamente
                        if primeiro_saldo_raw is not None:
                            primeiro_saldo = float(primeiro_saldo_raw)
                        else:
                            primeiro_saldo = 0.0
                        
                        # Se o primeiro lançamento já tem saldo, calcular saldo inicial
                        if primeiro_saldo != 0:
                            if primeiro_sinal == 'C':
                                saldo_inicial = primeiro_saldo - primeiro_valor
                            elif primeiro_sinal == 'D':
                                saldo_inicial = primeiro_saldo + primeiro_valor
                            else:
                                saldo_inicial = primeiro_saldo
                        else:
                            saldo_inicial = 0.0
                else:
                    saldo_inicial = 0.0
            
            # ✅ CORREÇÃO: Garantir que saldo_inicial nunca seja None
            if saldo_inicial is None:
                saldo_inicial = 0.0
            
            saldo_atual = float(saldo_inicial)
            lancamentos_com_saldo = []
            
            for lanc in lancamentos_ordenados:
                # ✅ CORREÇÃO: Ignorar lançamentos de "SALDO DO DIA" e "SALDO ANTERIOR" - são apenas informativos
                descricao = str(lanc.get('textoDescricaoHistorico', '')).upper()
                tipo_lancamento = lanc.get('indicadorTipoLancamento', '')
                
                # ✅ CORREÇÃO: Filtrar lançamentos de saldo (não devem ser incluídos no cálculo)
                # BB retorna "SALDO DO DIA", "S A L D O" ou "SALDO ANTERIOR" como lançamentos informativos
                # "SALDO ANTERIOR" já foi usado para calcular saldo_inicial, não deve alterar o saldo acumulado
                # "S A L D O" e "SALDO DO DIA" são informativos e não devem alterar o saldo acumulado
                is_saldo_informativo = (
                    'SALDO ANTERIOR' in descricao or
                    'SALDO DO DIA' in descricao or
                    'S A L D O' in descricao or
                    descricao.strip() == 'SALDO' or
                    tipo_lancamento in ['S', 'A', 'D', 'L', 'C', 'U']
                )
                
                if is_saldo_informativo:
                    # Este é um lançamento informativo de saldo, não deve alterar o saldo acumulado
                    # Mas vamos manter o lançamento na lista para exibição
                    valor = 0.0
                    sinal = ''
                    # ✅ IMPORTANTE: Não alterar saldo_atual para lançamentos informativos
                else:
                    # ✅ CORREÇÃO: Tratar None corretamente
                    valor_raw = lanc.get('valorLancamento')
                    if valor_raw is None:
                        valor = 0.0
                    else:
                        try:
                            valor = float(valor_raw)
                        except (ValueError, TypeError):
                            valor = 0.0
                    
                    sinal = lanc.get('indicadorSinalLancamento', '') or ''
                    
                    if sinal == 'C':
                        saldo_atual += valor
                    elif sinal == 'D':
                        saldo_atual -= valor
                
                # ✅ CORREÇÃO: Criar novo dict com apenas valores válidos
                lanc_com_saldo = {}
                for key, value in lanc.items():
                    if key == 'saldo_acumulado':
                        # Será definido abaixo
                        continue
                    elif key == 'valorLancamento':
                        lanc_com_saldo[key] = float(value or 0) if value is not None else 0.0
                    elif key == 'dataLancamento':
                        try:
                            lanc_com_saldo[key] = int(value or 0) if value is not None else 0
                        except (ValueError, TypeError):
                            lanc_com_saldo[key] = 0
                    elif value is None:
                        lanc_com_saldo[key] = ''
                    else:
                        lanc_com_saldo[key] = value
                
                # ✅ CORREÇÃO: Para lançamentos informativos de saldo, usar o valor do lançamento como saldo acumulado
                # Para outros lançamentos, usar o saldo_atual calculado
                if is_saldo_informativo:
                    # Para "S A L D O" ou "SALDO DO DIA", usar o valor do lançamento como saldo acumulado
                    valor_saldo_info = lanc.get('valorLancamento', 0)
                    if valor_saldo_info:
                        try:
                            lanc_com_saldo['saldo_acumulado'] = round(float(valor_saldo_info), 2)
                        except (ValueError, TypeError):
                            lanc_com_saldo['saldo_acumulado'] = round(float(saldo_atual or 0), 2)
                    else:
                        lanc_com_saldo['saldo_acumulado'] = round(float(saldo_atual or 0), 2)
                else:
                    # ✅ CORREÇÃO: Garantir que saldo_acumulado nunca seja None
                    lanc_com_saldo['saldo_acumulado'] = round(float(saldo_atual or 0), 2)
                
                lancamentos_com_saldo.append(lanc_com_saldo)
            
            # ✅ CORREÇÃO FINAL: Garantir que TODOS os lançamentos tenham valores válidos
            # Serializar todos os valores para garantir que não há None ou objetos complexos
            lancamentos_finais = []
            for lanc in lancamentos_com_saldo:
                lanc_final = {}
                for key, value in lanc.items():
                    try:
                        if key in ['saldo_acumulado', 'valorLancamento']:
                            # Valores numéricos: garantir float válido
                            if value is None:
                                lanc_final[key] = 0.0
                            else:
                                try:
                                    lanc_final[key] = float(value)
                                except (ValueError, TypeError):
                                    lanc_final[key] = 0.0
                        elif key == 'dataLancamento':
                            # Data: garantir int válido
                            if value is None:
                                lanc_final[key] = 0
                            else:
                                try:
                                    lanc_final[key] = int(value)
                                except (ValueError, TypeError):
                                    lanc_final[key] = 0
                        elif isinstance(value, (dict, list)):
                            # Objetos complexos: converter para string JSON ou string vazia
                            try:
                                import json
                                lanc_final[key] = json.dumps(value) if value else ''
                            except:
                                lanc_final[key] = str(value) if value else ''
                        elif value is None:
                            lanc_final[key] = ''
                        else:
                            # Outros campos: converter para string se necessário
                            lanc_final[key] = str(value) if not isinstance(value, (int, float, bool, str)) else value
                    except Exception as e:
                        logger.warning(f'⚠️ Erro ao processar campo {key}: {e}')
                        lanc_final[key] = ''
                lancamentos_finais.append(lanc_final)
            
            # Preparar dados para o template
            # ✅ CORREÇÃO: Se o último lançamento é "SALDO DO DIA", usar o valor dele como saldo final
            # Caso contrário, usar o saldo acumulado calculado
            saldo_final_valido = round(float(saldo_atual or 0), 2)
            
            # ✅ CORREÇÃO: Verificar se o último lançamento é um "SALDO DO DIA"
            if lancamentos_finais:
                ultimo_lanc = lancamentos_finais[-1]
                descricao_ultimo = str(ultimo_lanc.get('textoDescricaoHistorico', '')).upper()
                tipo_ultimo = str(ultimo_lanc.get('indicadorTipoLancamento', ''))
                
                # Se o último lançamento é "SALDO DO DIA", usar o valor dele como saldo final
                if 'SALDO' in descricao_ultimo or tipo_ultimo in ['S', 'A', 'D', 'L', 'C', 'U']:
                    # Tentar pegar o valor do saldo do último lançamento
                    # Pode estar em valorLancamento (se for crédito) ou no saldo_acumulado
                    valor_saldo_dia = ultimo_lanc.get('valorLancamento', 0)
                    saldo_acumulado_ultimo = ultimo_lanc.get('saldo_acumulado', 0)
                    
                    # Se tem valorLancamento e é crédito, usar ele
                    if valor_saldo_dia and ultimo_lanc.get('indicadorSinalLancamento') == 'C':
                        try:
                            saldo_final_valido = round(float(valor_saldo_dia), 2)
                            logger.info(f"✅ Usando saldo do dia do último lançamento: R$ {saldo_final_valido:,.2f}")
                        except (ValueError, TypeError):
                            pass
                    # Se não, usar o saldo acumulado do último lançamento (que pode estar correto)
                    elif saldo_acumulado_ultimo:
                        try:
                            saldo_final_valido = round(float(saldo_acumulado_ultimo), 2)
                            logger.info(f"✅ Usando saldo acumulado do último lançamento: R$ {saldo_final_valido:,.2f}")
                        except (ValueError, TypeError):
                            pass
            
            saldo_inicial_valido = float(saldo_inicial or 0) if saldo_inicial is not None else 0.0
            
            # ✅ VALIDAÇÃO EXTRA: Verificar se há None nos dados antes de renderizar
            for lanc in lancamentos_finais:
                for key, value in lanc.items():
                    if value is None:
                        logger.warning(f"⚠️ Valor None encontrado em lançamento: {key}={value}")
                        if key in ['saldo_acumulado', 'valorLancamento']:
                            lanc[key] = 0.0
                        elif key == 'dataLancamento':
                            lanc[key] = 0
                        else:
                            lanc[key] = ''
            
            dados_template = {
                'banco': 'Banco do Brasil',
                'agencia': str(agencia) if agencia else '',
                'conta': str(conta) if conta else '',
                'data_inicio': data_inicio.strftime("%d/%m/%Y") if data_inicio else '',
                'data_fim': data_fim.strftime("%d/%m/%Y") if data_fim else '',
                'lancamentos': lancamentos_finais,
                'saldo_inicial': saldo_inicial_valido,
                'saldo_final': saldo_final_valido,
                'data_geracao': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            
            # Renderizar HTML
            with app.app_context():
                html = render_template('extrato_bancario.html', **dados_template)
            
            # ✅ CORREÇÃO FINAL: Limpar HTML de possíveis valores None antes de gerar PDF
            import re
            html_limpo = html
            # Substituir None em valores numéricos
            html_limpo = re.sub(r'(\d+\.\d+)\s*None', r'\1', html_limpo)
            html_limpo = re.sub(r'None\s*(\d+\.\d+)', r'\1', html_limpo)
            # Garantir que não há "None" em atributos HTML
            html_limpo = re.sub(r'="None"', r'=""', html_limpo)
            html_limpo = re.sub(r"='None'", r"=''", html_limpo)
            # Remover qualquer ocorrência de None como texto
            html_limpo = re.sub(r'>None<', r'><', html_limpo)
            # Remover None em qualquer contexto (última tentativa)
            html_limpo = re.sub(r'\bNone\b', r'0', html_limpo)
            
            # Gerar PDF usando xhtml2pdf
            try:
                from xhtml2pdf import pisa
            except ImportError:
                return {
                    'sucesso': False,
                    'erro': 'Biblioteca xhtml2pdf não está instalada',
                    'resposta': '❌ Erro: Biblioteca xhtml2pdf não está instalada. Execute: pip install xhtml2pdf'
                }
            
            # Nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f'Extrato-Bancario-BB-{agencia}-{conta}-{timestamp}.pdf'
            caminho_arquivo = self.downloads_dir / nome_arquivo
            
            # Gerar PDF
            try:
                with open(caminho_arquivo, 'wb') as arquivo_pdf:
                    status_pdf = pisa.CreatePDF(io.StringIO(html_limpo), dest=arquivo_pdf, encoding='utf-8')
                    
                    if status_pdf.err:
                        logger.error(f'Erro ao gerar PDF: {status_pdf.err}')
                        # ✅ CORREÇÃO: Sempre remover PDF em branco quando há erro
                        arquivo_pdf.close()
                        if caminho_arquivo.exists():
                            try:
                                caminho_arquivo.unlink()
                                logger.info(f'✅ PDF em branco removido: {nome_arquivo}')
                            except Exception as e:
                                logger.warning(f'⚠️ Não foi possível remover PDF em branco: {e}')
                        return {
                            'sucesso': False,
                            'erro': f'Erro ao gerar PDF: {status_pdf.err}',
                            'resposta': f'❌ Erro ao gerar PDF: {status_pdf.err}'
                        }
            except Exception as e:
                logger.error(f'Erro ao gerar PDF (exceção): {e}', exc_info=True)
                # ✅ CORREÇÃO: Sempre remover PDF em branco quando há exceção
                if caminho_arquivo.exists():
                    try:
                        caminho_arquivo.unlink()
                        logger.info(f'✅ PDF em branco removido após exceção: {nome_arquivo}')
                    except:
                        pass
                return {
                    'sucesso': False,
                    'erro': f'Erro ao gerar PDF: {str(e)}',
                    'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
                }
            
            caminho_relativo = f'downloads/{nome_arquivo}'
            url_download = f"/api/download/{caminho_relativo}"
            
            logger.info(f'✅ PDF gerado com sucesso: {nome_arquivo}')
            
            return {
                'sucesso': True,
                'caminho_arquivo': caminho_relativo,
                'nome_arquivo': nome_arquivo,
                'arquivo_url': url_download,
                'resposta': (
                    "✅ **PDF gerado com sucesso!**\n\n"
                    f"📄 **Arquivo:** `{nome_arquivo}`\n"
                    f"🔗 **Abrir:** [Clique aqui para abrir o PDF]({url_download})\n"
                    f"📁 **Localização:** `{caminho_relativo}`\n\n"
                    "💡 O arquivo está disponível para download."
                )
            }
            
        except Exception as e:
            logger.error(f'Erro ao gerar PDF do extrato BB: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
            }
    
    def gerar_pdf_extrato_santander(
        self,
        agencia: str,
        conta: str,
        lancamentos: list,
        data_inicio: datetime,
        data_fim: datetime,
        saldo_inicial: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Gera PDF do extrato do Santander no formato contábil.
        
        Args:
            agencia: Número da agência
            conta: Número da conta
            lancamentos: Lista de lançamentos do extrato
            data_inicio: Data inicial do período
            data_fim: Data final do período
            saldo_inicial: Saldo inicial (opcional)
        
        Returns:
            Dict com resultado da geração do PDF
        """
        try:
            from flask import render_template
            from app import app
            
            if not lancamentos:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum lançamento encontrado',
                    'resposta': '❌ Não foi possível gerar o PDF: nenhum lançamento encontrado no período.'
                }
            
            # Ordenar lançamentos por data (mais antigo primeiro para cálculo de saldo)
            def converter_data_para_ordenacao(data_str: str) -> int:
                """Converte YYYY-MM-DD para YYYYMMDD para ordenação correta"""
                # ✅ CORREÇÃO: Tratar None e valores inválidos
                if data_str is None or not data_str:
                    return 0
                try:
                    if 'T' in data_str:
                        data_str = data_str.split('T')[0]
                    dt = datetime.strptime(data_str, "%Y-%m-%d")
                    return int(dt.strftime("%Y%m%d"))
                except (ValueError, TypeError, AttributeError):
                    return 0
            
            # ✅ CORREÇÃO: Garantir que lancamentos é uma lista de dicionários
            if not isinstance(lancamentos, list):
                lancamentos = []
            
            # Filtrar apenas itens que são dicionários
            lancamentos_validos = [l for l in lancamentos if isinstance(l, dict)]
            
            if not lancamentos_validos:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum lançamento válido encontrado',
                    'resposta': '❌ Não foi possível gerar o PDF: nenhum lançamento válido encontrado.'
                }
            
            lancamentos_ordenados = sorted(
                lancamentos_validos,
                key=lambda x: converter_data_para_ordenacao(x.get('transactionDate', '') if isinstance(x, dict) else '')
            )
            
            # Calcular saldo acumulado
            # Se não tiver saldo inicial, tentar pegar do primeiro lançamento ou usar 0
            if saldo_inicial is None:
                # Tentar calcular saldo inicial baseado no primeiro lançamento
                if lancamentos_ordenados:
                    primeiro_lanc = lancamentos_ordenados[0]
                    
                    # ✅ CORREÇÃO: Tratar amount que pode ser dict, número ou lista
                    amount_obj = primeiro_lanc.get('amount')
                    if isinstance(amount_obj, dict):
                        primeiro_valor_raw = amount_obj.get('amount', 0)
                    elif isinstance(amount_obj, (int, float)):
                        primeiro_valor_raw = amount_obj
                    elif isinstance(amount_obj, list) and len(amount_obj) > 0:
                        # Se for lista, pegar o primeiro item
                        primeiro_valor_raw = amount_obj[0] if isinstance(amount_obj[0], (int, float)) else 0
                    else:
                        primeiro_valor_raw = 0
                    
                    primeiro_valor = float(primeiro_valor_raw or 0)
                    # ✅ CORREÇÃO: Santander usa 'creditDebitType' com valores 'CREDITO'/'DEBITO'
                    primeiro_tipo = primeiro_lanc.get('creditDebitType') or primeiro_lanc.get('transactionType', '')
                    
                    # ✅ CORREÇÃO: Tratar balance que pode ser dict, número ou lista
                    balance_obj = primeiro_lanc.get('balance')
                    if isinstance(balance_obj, dict):
                        primeiro_saldo_raw = balance_obj.get('amount')
                    elif isinstance(balance_obj, (int, float)):
                        primeiro_saldo_raw = balance_obj
                    elif isinstance(balance_obj, list) and len(balance_obj) > 0:
                        primeiro_saldo_raw = balance_obj[0] if isinstance(balance_obj[0], (int, float)) else None
                    else:
                        primeiro_saldo_raw = None
                    
                    # ✅ CORREÇÃO: Tratar None corretamente
                    if primeiro_saldo_raw is not None:
                        primeiro_saldo = float(primeiro_saldo_raw)
                    else:
                        primeiro_saldo = 0.0
                    
                    # Se o primeiro lançamento já tem saldo, calcular saldo inicial
                    if primeiro_saldo != 0:
                        # ✅ CORREÇÃO: Mapear valores do Santander
                        if primeiro_tipo in ['CREDIT', 'CREDITO']:
                            saldo_inicial = primeiro_saldo - primeiro_valor
                        elif primeiro_tipo in ['DEBIT', 'DEBITO']:
                            saldo_inicial = primeiro_saldo + primeiro_valor
                        else:
                            saldo_inicial = primeiro_saldo
                    else:
                        saldo_inicial = 0.0
                else:
                    saldo_inicial = 0.0
            
            # ✅ CORREÇÃO: Garantir que saldo_inicial nunca seja None
            if saldo_inicial is None:
                saldo_inicial = 0.0
            
            saldo_atual = float(saldo_inicial)
            lancamentos_com_saldo = []
            
            for lanc in lancamentos_ordenados:
                # ✅ CORREÇÃO: Tratar amount que pode ser dict, número ou lista
                amount_obj = lanc.get('amount')
                
                # ✅ DEBUG: Log primeiro lançamento para ver estrutura
                if len(lancamentos_com_saldo) == 0:
                    logger.info(f"🔍 [DEBUG SANTANDER] Primeiro lançamento: {lanc}")
                    logger.info(f"🔍 [DEBUG SANTANDER] amount_obj type: {type(amount_obj)}, value: {amount_obj}")
                    logger.info(f"🔍 [DEBUG SANTANDER] creditDebitType: {lanc.get('creditDebitType')}")
                    logger.info(f"🔍 [DEBUG SANTANDER] transactionDate: {lanc.get('transactionDate')}")
                    logger.info(f"🔍 [DEBUG SANTANDER] transactionName: {lanc.get('transactionName')}")
                
                if isinstance(amount_obj, str):
                    # ✅ CORREÇÃO: Santander retorna amount como STRING!
                    try:
                        valor_raw = float(amount_obj)
                    except (ValueError, TypeError):
                        valor_raw = 0
                elif isinstance(amount_obj, dict):
                    valor_raw = amount_obj.get('amount')
                elif isinstance(amount_obj, (int, float)):
                    valor_raw = amount_obj
                elif isinstance(amount_obj, list) and len(amount_obj) > 0:
                    # ✅ CORREÇÃO: Tratar lista corretamente
                    primeiro_item = amount_obj[0]
                    if isinstance(primeiro_item, dict):
                        valor_raw = primeiro_item.get('amount', 0) if isinstance(primeiro_item, dict) else 0
                    elif isinstance(primeiro_item, (int, float)):
                        valor_raw = primeiro_item
                    elif isinstance(primeiro_item, str):
                        try:
                            valor_raw = float(primeiro_item)
                        except (ValueError, TypeError):
                            valor_raw = 0
                    else:
                        valor_raw = 0
                else:
                    valor_raw = 0
                
                valor = float(valor_raw or 0)
                # ✅ CORREÇÃO: Santander usa 'creditDebitType' com valores 'CREDITO'/'DEBITO', não 'transactionType' com 'CREDIT'/'DEBIT'
                tipo = lanc.get('creditDebitType') or lanc.get('transactionType', '')
                
                # ✅ CORREÇÃO: Mapear valores do Santander
                if tipo in ['CREDIT', 'CREDITO']:
                    saldo_atual += valor
                elif tipo in ['DEBIT', 'DEBITO']:
                    saldo_atual -= valor
                
                # ✅ CORREÇÃO: Criar novo dict com apenas valores válidos (não usar copy para evitar referências)
                # ✅ IMPORTANTE: Garantir que lanc seja um dict antes de iterar
                if not isinstance(lanc, dict):
                    logger.warning(f"⚠️ Lançamento não é dict: {type(lanc)}, pulando...")
                    continue
                
                lanc_com_saldo = {}
                for key, value in lanc.items():
                    if key == 'saldo_acumulado':
                        # Será definido abaixo
                        continue
                    elif key == 'amount':
                        # ✅ CORREÇÃO CRÍTICA: Santander retorna amount como STRING, não número!
                        # Tratar todos os casos possíveis: string, número, dict, lista
                        if isinstance(value, str):
                            # ✅ CASO MAIS COMUM NO SANTANDER: string (ex: "303880.15")
                            try:
                                lanc_com_saldo[key] = {'amount': float(value)}
                            except (ValueError, TypeError):
                                lanc_com_saldo[key] = {'amount': 0.0}
                        elif isinstance(value, (int, float)):
                            # Número direto
                            lanc_com_saldo[key] = {'amount': float(value)}
                        elif isinstance(value, dict):
                            # Se já é dict, garantir que amount interno seja float válido
                            amount_interno = value.get('amount')
                            if amount_interno is None:
                                lanc_com_saldo[key] = {'amount': 0.0}
                            else:
                                try:
                                    # Pode ser string, número, etc
                                    lanc_com_saldo[key] = {'amount': float(amount_interno)}
                                except (ValueError, TypeError):
                                    lanc_com_saldo[key] = {'amount': 0.0}
                        elif isinstance(value, list) and len(value) > 0:
                            # Se é lista, pegar primeiro item numérico
                            try:
                                primeiro_item = value[0]
                                if isinstance(primeiro_item, (int, float)):
                                    lanc_com_saldo[key] = {'amount': float(primeiro_item)}
                                elif isinstance(primeiro_item, str):
                                    lanc_com_saldo[key] = {'amount': float(primeiro_item)}
                                elif isinstance(primeiro_item, dict):
                                    # Se o primeiro item da lista é um dict, tentar pegar 'amount'
                                    lanc_com_saldo[key] = {'amount': float(primeiro_item.get('amount', 0) or 0)}
                                else:
                                    lanc_com_saldo[key] = {'amount': 0.0}
                            except (ValueError, TypeError, IndexError):
                                lanc_com_saldo[key] = {'amount': 0.0}
                        elif value is None:
                            lanc_com_saldo[key] = {'amount': 0.0}
                        else:
                            # Qualquer outro tipo, tentar converter para float
                            try:
                                lanc_com_saldo[key] = {'amount': float(value)}
                            except (ValueError, TypeError):
                                logger.warning(f"⚠️ amount tem tipo inesperado: {type(value)} = {value}, convertendo para 0.0")
                                lanc_com_saldo[key] = {'amount': 0.0}
                    elif key == 'transactionDate':
                        # Data: garantir string válida
                        if value is None:
                            lanc_com_saldo[key] = ''
                        else:
                            lanc_com_saldo[key] = str(value)
                    elif isinstance(value, list):
                        # ✅ CORREÇÃO: Listas devem ser tratadas especialmente
                        # Se for lista vazia, converter para string vazia
                        if len(value) == 0:
                            lanc_com_saldo[key] = ''
                        else:
                            # Tentar converter primeiro item se for simples, senão JSON
                            try:
                                primeiro = value[0]
                                if isinstance(primeiro, (str, int, float, bool)):
                                    lanc_com_saldo[key] = str(primeiro)
                                else:
                                    import json
                                    lanc_com_saldo[key] = json.dumps(value)
                            except:
                                lanc_com_saldo[key] = str(value)
                    elif isinstance(value, dict):
                        # Dicts: converter para string JSON ou manter como dict se necessário
                        # Mas não converter campos especiais como 'amount' que já foram tratados
                        if key not in ['amount', 'balance']:  # Estes já foram tratados acima
                            try:
                                import json
                                lanc_com_saldo[key] = json.dumps(value) if value else ''
                            except:
                                lanc_com_saldo[key] = str(value) if value else ''
                        else:
                            # Se for amount ou balance que ainda é dict, manter como está (já foi tratado)
                            lanc_com_saldo[key] = value
                    elif value is None:
                        lanc_com_saldo[key] = ''
                    else:
                        # Outros campos: copiar como está
                        lanc_com_saldo[key] = value
                
                # ✅ CORREÇÃO: Garantir que saldo_acumulado nunca seja None
                lanc_com_saldo['saldo_acumulado'] = round(float(saldo_atual or 0), 2)
                
                # ✅ VALIDAÇÃO FINAL CRÍTICA: Garantir que amount NUNCA seja lista
                if 'amount' in lanc_com_saldo:
                    amount_val = lanc_com_saldo['amount']
                    if isinstance(amount_val, list):
                        logger.error(f"❌ ERRO CRÍTICO: amount ainda é lista após processamento! Convertendo para dict...")
                        try:
                            if len(amount_val) > 0:
                                primeiro = amount_val[0]
                                if isinstance(primeiro, dict):
                                    lanc_com_saldo['amount'] = {'amount': float(primeiro.get('amount', 0) or 0)}
                                elif isinstance(primeiro, (int, float)):
                                    lanc_com_saldo['amount'] = {'amount': float(primeiro)}
                                else:
                                    lanc_com_saldo['amount'] = {'amount': 0.0}
                            else:
                                lanc_com_saldo['amount'] = {'amount': 0.0}
                        except Exception as e:
                            logger.error(f"❌ Erro ao converter amount de lista: {e}")
                            lanc_com_saldo['amount'] = {'amount': 0.0}
                    elif not isinstance(amount_val, dict):
                        # ✅ CORREÇÃO: Pode ser string, número, etc - tentar converter
                        try:
                            if isinstance(amount_val, str):
                                lanc_com_saldo['amount'] = {'amount': float(amount_val)}
                            elif isinstance(amount_val, (int, float)):
                                lanc_com_saldo['amount'] = {'amount': float(amount_val)}
                            else:
                                logger.warning(f"⚠️ amount não é dict: {type(amount_val)}, convertendo...")
                                lanc_com_saldo['amount'] = {'amount': 0.0}
                        except (ValueError, TypeError):
                            logger.warning(f"⚠️ amount não é dict: {type(amount_val)}, convertendo para 0.0...")
                            lanc_com_saldo['amount'] = {'amount': 0.0}
                
                lancamentos_com_saldo.append(lanc_com_saldo)
            
            # ✅ VALIDAÇÃO EXTRA: Verificar se há None ou listas nos dados antes de renderizar
            for lanc in lancamentos_com_saldo:
                for key, value in lanc.items():
                    if value is None:
                        logger.warning(f"⚠️ Valor None encontrado em lançamento Santander: {key}={value}")
                        if key == 'amount':
                            lanc[key] = {'amount': 0.0}
                        elif key in ['saldo_acumulado']:
                            lanc[key] = 0.0
                        elif key == 'transactionDate':
                            lanc[key] = ''
                        else:
                            lanc[key] = ''
                    elif key == 'amount':
                        # ✅ CORREÇÃO CRÍTICA: Garantir que amount sempre seja um dict
                        if isinstance(value, list):
                            # Se ainda for lista, converter para dict
                            logger.warning(f"⚠️ amount ainda é lista em lançamento Santander, convertendo...")
                            try:
                                if len(value) > 0:
                                    primeiro_item = value[0]
                                    if isinstance(primeiro_item, dict):
                                        valor = float(primeiro_item.get('amount', 0) or 0)
                                    elif isinstance(primeiro_item, (int, float)):
                                        valor = float(primeiro_item)
                                    else:
                                        valor = 0.0
                                else:
                                    valor = 0.0
                            except (ValueError, TypeError, IndexError):
                                valor = 0.0
                            lanc[key] = {'amount': valor}
                        elif isinstance(value, dict):
                            # Garantir que amount.amount não seja None
                            if 'amount' not in value or value['amount'] is None:
                                value['amount'] = 0.0
                            else:
                                try:
                                    value['amount'] = float(value['amount'])
                                except (ValueError, TypeError):
                                    value['amount'] = 0.0
                        elif isinstance(value, (int, float)):
                            # Se for número direto, converter para dict
                            lanc[key] = {'amount': float(value)}
                        else:
                            # Qualquer outro tipo, converter para dict com 0.0
                            logger.warning(f"⚠️ amount tem tipo inesperado: {type(value)}, convertendo para 0.0")
                            lanc[key] = {'amount': 0.0}
            
            # ✅ VALIDAÇÃO FINAL ABSOLUTA: Garantir que TODOS os amount sejam dict antes de passar para template
            for lanc_final in lancamentos_com_saldo:
                if 'amount' in lanc_final:
                    amount_final = lanc_final['amount']
                    if isinstance(amount_final, list):
                        logger.error(f"❌ ERRO FINAL: amount ainda é lista! Convertendo...")
                        try:
                            if len(amount_final) > 0:
                                primeiro = amount_final[0]
                                if isinstance(primeiro, dict):
                                    lanc_final['amount'] = {'amount': float(primeiro.get('amount', 0) or 0)}
                                elif isinstance(primeiro, (int, float)):
                                    lanc_final['amount'] = {'amount': float(primeiro)}
                                else:
                                    lanc_final['amount'] = {'amount': 0.0}
                            else:
                                lanc_final['amount'] = {'amount': 0.0}
                        except Exception as e:
                            logger.error(f"❌ Erro ao converter amount final: {e}")
                            lanc_final['amount'] = {'amount': 0.0}
                    elif not isinstance(amount_final, dict):
                        logger.warning(f"⚠️ amount final não é dict: {type(amount_final)}, convertendo...")
                        lanc_final['amount'] = {'amount': 0.0}
                    elif 'amount' not in amount_final or amount_final['amount'] is None:
                        amount_final['amount'] = 0.0

            # ✅ NOVO (24/01/2026): Enriquecer "Histórico" do PDF com processos conciliados (se houver)
            try:
                from services.banco_sincronizacao_service import BancoSincronizacaoService

                hash_svc = BancoSincronizacaoService.__new__(BancoSincronizacaoService)  # evita init (sem APIs)
                hashes = []
                for l in lancamentos_com_saldo:
                    try:
                        h = hash_svc.gerar_hash_lancamento(l, agencia=str(agencia), conta=str(conta), banco="SANTANDER")
                        if h:
                            l["_hash_dados"] = h
                            hashes.append(h)
                    except Exception:
                        continue

                proc_map = self._buscar_processos_conciliados_por_hash(hashes)
                if proc_map:
                    for l in lancamentos_com_saldo:
                        h = l.get("_hash_dados")
                        if h and h in proc_map:
                            l["processos_conciliados"] = proc_map[h]
            except Exception:
                pass
            
            # Preparar dados para o template
            # ✅ CORREÇÃO: Garantir que todos os valores numéricos sejam floats válidos
            saldo_final_valido = round(float(saldo_atual or 0), 2)
            saldo_inicial_valido = float(saldo_inicial or 0) if saldo_inicial is not None else 0.0
            
            # ✅ VALIDAÇÃO EXTRA: Verificar se há listas em qualquer campo antes de renderizar
            for lanc_check in lancamentos_com_saldo:
                if not isinstance(lanc_check, dict):
                    logger.error(f"❌ Lançamento não é dict: {type(lanc_check)}")
                    continue
                for key_check, value_check in lanc_check.items():
                    if isinstance(value_check, list):
                        logger.warning(f"⚠️ Campo '{key_check}' é lista em lançamento Santander: {value_check}")
                        # Converter lista para string ou dict dependendo do campo
                        if key_check == 'amount':
                            # Já deveria ter sido tratado, mas garantir
                            lanc_check[key_check] = {'amount': 0.0}
                        else:
                            # Outros campos: converter para string
                            try:
                                import json
                                lanc_check[key_check] = json.dumps(value_check) if value_check else ''
                            except:
                                lanc_check[key_check] = str(value_check) if value_check else ''
            
            dados_template = {
                'banco': 'Santander',
                'agencia': str(agencia) if agencia else '',
                'conta': str(conta) if conta else '',
                'data_inicio': data_inicio.strftime("%d/%m/%Y") if data_inicio else '',
                'data_fim': data_fim.strftime("%d/%m/%Y") if data_fim else '',
                'lancamentos': lancamentos_com_saldo,
                'saldo_inicial': saldo_inicial_valido,
                'saldo_final': saldo_final_valido,
                'data_geracao': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
            
            # Renderizar HTML
            with app.app_context():
                html = render_template('extrato_bancario.html', **dados_template)
            
            # ✅ CORREÇÃO FINAL: Limpar HTML de possíveis valores None antes de gerar PDF
            import re
            html_limpo = html
            # Substituir None em valores numéricos
            html_limpo = re.sub(r'(\d+\.\d+)\s*None', r'\1', html_limpo)
            html_limpo = re.sub(r'None\s*(\d+\.\d+)', r'\1', html_limpo)
            # Garantir que não há "None" em atributos HTML
            html_limpo = re.sub(r'="None"', r'=""', html_limpo)
            html_limpo = re.sub(r"='None'", r"=''", html_limpo)
            # Remover qualquer ocorrência de None como texto
            html_limpo = re.sub(r'>None<', r'><', html_limpo)
            # Remover None em qualquer contexto (última tentativa)
            html_limpo = re.sub(r'\bNone\b', r'0', html_limpo)
            
            # Gerar PDF usando xhtml2pdf
            try:
                from xhtml2pdf import pisa
            except ImportError:
                return {
                    'sucesso': False,
                    'erro': 'Biblioteca xhtml2pdf não está instalada',
                    'resposta': '❌ Erro: Biblioteca xhtml2pdf não está instalada. Execute: pip install xhtml2pdf'
                }
            
            # Nome do arquivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f'Extrato-Bancario-Santander-{agencia}-{conta}-{timestamp}.pdf'
            caminho_arquivo = self.downloads_dir / nome_arquivo
            
            # Gerar PDF
            try:
                with open(caminho_arquivo, 'wb') as arquivo_pdf:
                    status_pdf = pisa.CreatePDF(io.StringIO(html_limpo), dest=arquivo_pdf, encoding='utf-8')
                    
                    if status_pdf.err:
                        logger.error(f'Erro ao gerar PDF: {status_pdf.err}')
                        # ✅ CORREÇÃO: Sempre remover PDF em branco quando há erro
                        arquivo_pdf.close()
                        if caminho_arquivo.exists():
                            try:
                                caminho_arquivo.unlink()
                                logger.info(f'✅ PDF em branco removido: {nome_arquivo}')
                            except Exception as e:
                                logger.warning(f'⚠️ Não foi possível remover PDF em branco: {e}')
                        return {
                            'sucesso': False,
                            'erro': f'Erro ao gerar PDF: {status_pdf.err}',
                            'resposta': f'❌ Erro ao gerar PDF: {status_pdf.err}'
                        }
            except Exception as e:
                logger.error(f'Erro ao gerar PDF (exceção): {e}', exc_info=True)
                # ✅ CORREÇÃO: Sempre remover PDF em branco quando há exceção
                if caminho_arquivo.exists():
                    try:
                        caminho_arquivo.unlink()
                        logger.info(f'✅ PDF em branco removido após exceção: {nome_arquivo}')
                    except:
                        pass
                return {
                    'sucesso': False,
                    'erro': f'Erro ao gerar PDF: {str(e)}',
                    'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
                }
            
            caminho_relativo = f'downloads/{nome_arquivo}'
            url_download = f"/api/download/{caminho_relativo}"
            
            logger.info(f'✅ PDF gerado com sucesso: {nome_arquivo}')
            
            return {
                'sucesso': True,
                'caminho_arquivo': caminho_relativo,
                'nome_arquivo': nome_arquivo,
                'arquivo_url': url_download,
                'resposta': (
                    "✅ **PDF gerado com sucesso!**\n\n"
                    f"📄 **Arquivo:** `{nome_arquivo}`\n"
                    f"🔗 **Abrir:** [Clique aqui para abrir o PDF]({url_download})\n"
                    f"📁 **Localização:** `{caminho_relativo}`\n\n"
                    "💡 O arquivo está disponível para download."
                )
            }
            
        except Exception as e:
            logger.error(f'Erro ao gerar PDF do extrato Santander: {e}', exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'resposta': f'❌ Erro ao gerar PDF: {str(e)}'
            }

