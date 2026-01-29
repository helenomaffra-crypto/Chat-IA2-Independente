"""
Serviço para extrair dados de boletos bancários de PDFs.
"""
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# ✅ NOVO: Suporte a OpenAI Vision API para PDFs que não podem ser extraídos
try:
    from services.boleto_parser_vision import BoletoParserVision
    vision_parser = BoletoParserVision()
except ImportError:
    vision_parser = None
except Exception as e:
    logger.warning(f"⚠️ Vision parser não disponível: {e}")
    vision_parser = None

logger = logging.getLogger(__name__)


class BoletoParser:
    """Parser para extrair dados de boletos bancários de PDFs."""
    
    def extrair_dados_boleto(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrai dados do boleto do PDF.
        
        Args:
            pdf_path: Caminho do arquivo PDF do boleto
        
        Returns:
            Dict com:
            - sucesso: bool
            - codigo_barras: str (44 ou 47 dígitos)
            - valor: float
            - vencimento: str (YYYY-MM-DD)
            - beneficiario: str (opcional)
            - erro: str (se sucesso=False)
        """
        if not PyPDF2:
            return {
                'sucesso': False,
                'erro': 'PyPDF2 não instalado. Instale com: pip install PyPDF2'
            }
        
        logger.info(f"📄 Processando boleto: {pdf_path}")
        
        # 1. Extrair texto do PDF
        texto = self._extrair_texto_pdf(pdf_path)
        
        if not texto:
            # ✅ NOVO: Tentar OpenAI Vision API como fallback
            if vision_parser:
                logger.info("🖼️ PDF não tem texto extraível. Tentando extrair com OpenAI Vision API...")
                resultado_vision = vision_parser.extrair_dados_boleto_vision(pdf_path)
                if resultado_vision.get('sucesso'):
                    logger.info("✅ Dados extraídos com sucesso usando OpenAI Vision! (PDF escaneado/imagem)")
                    # ✅ GARANTIR: Adicionar flag para indicar que foi usado Vision API
                    resultado_vision['metodo'] = 'openai_vision'
                    resultado_vision['pdf_escaneado'] = True
                    return resultado_vision
                else:
                    logger.warning(f"⚠️ Vision API também falhou: {resultado_vision.get('erro')}")
            
            return {
                'sucesso': False,
                'erro': 'PDF escaneado ou em formato de imagem. Não foi possível extrair texto automaticamente. Use OCR ou forneça os dados manualmente.',
                'tipo_erro': 'pdf_escaneado',
                'sugestao': 'fornecer_dados_manuais' if not vision_parser else 'vision_api_falhou'
            }
        
        logger.info(f"✅ Texto extraído com pdfplumber: {len(texto)} caracteres")
        
        # ✅ GARANTIR: Definir método de extração usado
        metodo_extracao = 'pdfplumber'
        
        # 2. Extrair código de barras
        codigo_barras = self._extrair_codigo_barras(texto)
        if not codigo_barras:
            logger.warning("⚠️ Código de barras não encontrado no PDF")
        
        # 3. Extrair valor
        valor = self._extrair_valor(texto)
        if not valor:
            logger.warning("⚠️ Valor não encontrado no PDF")
        
        # 4. Extrair vencimento
        vencimento = self._extrair_vencimento(texto)
        
        # 5. Extrair beneficiário
        beneficiario = self._extrair_beneficiario(texto)
        
        # ✅ VALIDAÇÃO ADICIONAL: Verificar se beneficiário extraído parece incorreto
        # Se contém palavras de campos adjacentes, tratar como None para acionar fallback
        if beneficiario:
            palavras_invalidas = ['espécie', 'vencimento', 'real', 'dm', 'aceite', 'número', 'nosso']
            beneficiario_lower = beneficiario.lower()
            if any(palavra in beneficiario_lower for palavra in palavras_invalidas):
                logger.warning(f"⚠️ Beneficiário parece incorreto (contém campo adjacente): '{beneficiario}'. Acionando fallback Vision API...")
                beneficiario = None  # Tratar como None para acionar fallback
        
        # ✅ NOVO: Se beneficiário não foi encontrado via regex OU foi detectado como incorreto, tentar Vision API como fallback
        # Mesmo quando o PDF tem texto extraível, a Vision API pode ter melhor resultado
        # porque "vê" o layout visual do documento
        if not beneficiario and vision_parser and codigo_barras and valor:
            logger.info("🖼️ Beneficiário não encontrado via regex, tentando Vision API como fallback...")
            try:
                resultado_vision = vision_parser.extrair_dados_boleto_vision(pdf_path)
                if resultado_vision.get('sucesso') and resultado_vision.get('beneficiario'):
                    beneficiario = resultado_vision.get('beneficiario')
                    logger.info(f"✅ Beneficiário extraído via Vision API: {beneficiario}")
                else:
                    logger.debug("⚠️ Vision API também não encontrou beneficiário")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao usar Vision API como fallback: {e}")
        
        if not codigo_barras or not valor:
            return {
                'sucesso': False,
                'erro': 'Não foi possível extrair código de barras ou valor do boleto. Verifique se o PDF está completo e legível.',
                'codigo_barras': codigo_barras,
                'valor': valor,
                'vencimento': vencimento,
                'beneficiario': beneficiario
            }
        
        logger.info(f"✅ Dados extraídos: código={codigo_barras[:10]}..., valor=R${valor:,.2f}, vencimento={vencimento}, beneficiario={beneficiario or 'não encontrado'}")
        
        return {
            'sucesso': True,
            'codigo_barras': codigo_barras,
            'valor': valor,
            'vencimento': vencimento,
            'beneficiario': beneficiario,
            'metodo': metodo_extracao,  # ✅ GARANTIR: Adicionar flag de método usado
            'pdf_escaneado': False  # ✅ GARANTIR: Flag para indicar que não é escaneado
        }
    
    def _extrair_texto_pdf(self, pdf_path: str) -> str:
        """Extrai texto de conteúdo PDF."""
        # ✅ NOVO: Tentar pdfplumber primeiro (mais robusto)
        if pdfplumber:
            try:
                logger.debug("🔍 Tentando extrair com pdfplumber...")
                with pdfplumber.open(pdf_path) as pdf:
                    texto = ""
                    for i, page in enumerate(pdf.pages, start=1):
                        try:
                            # Método 1: Extrair texto direto
                            texto_pagina = page.extract_text()
                            if texto_pagina:
                                texto += texto_pagina + "\n"
                                logger.debug(f"✅ Página {i} (pdfplumber): {len(texto_pagina)} caracteres extraídos")
                            else:
                                # Método 2: Tentar extrair de tabelas
                                logger.debug(f"⚠️ Página {i}: Nenhum texto direto, tentando extrair de tabelas...")
                                tabelas = page.extract_tables()
                                if tabelas:
                                    logger.debug(f"📊 Página {i}: Encontradas {len(tabelas)} tabela(s)")
                                    for j, tabela in enumerate(tabelas):
                                        if tabela:
                                            # Converter tabela em texto
                                            for linha in tabela:
                                                if linha:
                                                    linha_texto = " ".join([str(cell) if cell else "" for cell in linha])
                                                    if linha_texto.strip():
                                                        texto += linha_texto + "\n"
                                            
                                            if texto.strip():
                                                logger.info(f"✅ Texto extraído de tabelas na página {i}")
                                                break
                                
                                # Método 3: Tentar extrair palavras individuais
                                if not texto.strip():
                                    palavras = page.extract_words()
                                    if palavras:
                                        logger.debug(f"📝 Página {i}: Encontradas {len(palavras)} palavra(s)")
                                        texto_pagina = " ".join([w.get('text', '') for w in palavras if w.get('text')])
                                        if texto_pagina:
                                            texto += texto_pagina + "\n"
                                            logger.info(f"✅ Texto extraído de palavras na página {i}")
                        except Exception as e:
                            logger.warning(f"⚠️ Erro ao extrair página {i} com pdfplumber: {e}")
                            continue
                    
                    if texto.strip():
                        logger.info(f"✅ Texto extraído com pdfplumber: {len(texto)} caracteres")
                        return texto.strip()
                    else:
                        logger.warning("⚠️ pdfplumber não extraiu texto, tentando PyPDF2...")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao usar pdfplumber: {e}, tentando PyPDF2...")
        
        # Fallback: PyPDF2
        if not PyPDF2:
            return ""
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                logger.debug(f"📄 PDF tem {len(pdf_reader.pages)} página(s)")
                
                # Verificar se PDF está criptografado
                if pdf_reader.is_encrypted:
                    logger.warning("⚠️ PDF está criptografado, tentando descriptografar...")
                    try:
                        pdf_reader.decrypt("")  # Tentar sem senha
                    except:
                        logger.error("❌ PDF requer senha para leitura")
                        return ""
                
                texto = ""
                for i, page in enumerate(pdf_reader.pages, start=1):
                    try:
                        texto_pagina = page.extract_text()
                        if texto_pagina:
                            texto += texto_pagina + "\n"
                            logger.debug(f"✅ Página {i} (PyPDF2): {len(texto_pagina)} caracteres extraídos")
                        else:
                            logger.warning(f"⚠️ Página {i}: Nenhum texto extraído (pode ser escaneada/imagem)")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao extrair texto da página {i}: {e}")
                        continue
                
                if not texto.strip():
                    logger.warning("⚠️ ATENÇÃO: PDF não retornou texto. Pode ser PDF escaneado (requer OCR)")
                
                return texto.strip()
                
        except FileNotFoundError:
            logger.error(f"❌ Arquivo não encontrado: {pdf_path}")
            return ""
        except PermissionError:
            logger.error(f"❌ Sem permissão para ler arquivo: {pdf_path}")
            return ""
        except Exception as e:
            logger.error(f"❌ Erro ao ler PDF: {e}", exc_info=True)
            return ""
    
    def _extrair_codigo_barras(self, texto: str) -> Optional[str]:
        """Extrai código de barras do texto."""
        # Padrão 1: Código com pontos e espaços (formato legível)
        # Ex: 34191.09321 64129.922932 80145.580009 3 13510000090000
        padrao1 = r'(\d{5}\.?\d{5}\s?\d{5}\.?\d{6}\s?\d{5}\.?\d{6}\s?\d\s?\d{14})'
        match = re.search(padrao1, texto)
        if match:
            codigo = match.group(1)
            # Limpar pontos e espaços
            codigo_limpo = re.sub(r'[.\s]', '', codigo)
            # Validar tamanho (44 ou 47 dígitos)
            if len(codigo_limpo) in [44, 47]:
                return codigo_limpo
        
        # Padrão 2: Código sem formatação (44 ou 47 dígitos consecutivos)
        padrao2 = r'(\d{44,47})'
        match = re.search(padrao2, texto)
        if match:
            codigo = match.group(1)
            if len(codigo) in [44, 47]:
                return codigo
        
        # Padrão 3: Linha de código de barras (Autenticação Mecânica)
        padrao3 = r'Autenticação\s+Mecânica.*?(\d{5}\.?\d{5}\s?\d{5}\.?\d{6}\s?\d{5}\.?\d{6}\s?\d\s?\d{14})'
        match = re.search(padrao3, texto, re.IGNORECASE | re.DOTALL)
        if match:
            codigo = match.group(1)
            codigo_limpo = re.sub(r'[.\s]', '', codigo)
            if len(codigo_limpo) in [44, 47]:
                return codigo_limpo
        
        return None
    
    def _extrair_valor(self, texto: str) -> Optional[float]:
        """Extrai valor do boleto."""
        # Padrão 1: "Valor do documento" ou "Valor documento" (PRIORIDADE MÁXIMA)
        # Formato brasileiro: R$ 4.019,40 ou 4.019,40
        padroes_prioritarios = [
            r'Valor\s+(?:do\s+)?documento\s*:?\s*R?\$?\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'Valor\s+(?:do\s+)?documento\s*:?\s*R?\$?\s*([\d.,]+)',
        ]
        
        for padrao in padroes_prioritarios:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                valor_str = match.group(1)
                # Validar formato: deve ter vírgula (centavos) ou ser um número razoável
                if ',' in valor_str or '.' in valor_str:
                    # Formato brasileiro: 4.019,40 -> 4019.40
                    valor_limpo = valor_str.replace('.', '').replace(',', '.')
                else:
                    # Se não tem vírgula/ponto, provavelmente não é valor monetário
                    continue
                
                try:
                    valor_float = float(valor_limpo)
                    # Validar: valor deve ser razoável (entre R$ 0,01 e R$ 1.000.000,00)
                    if 0.01 <= valor_float <= 1000000.0:
                        logger.debug(f"✅ Valor extraído (padrão prioritário): R$ {valor_float:,.2f}")
                        return valor_float
                except:
                    continue
        
        # Padrão 2: "Valor cobrado" ou "Valor" (formato monetário brasileiro)
        padroes_secundarios = [
            r'\(=\).*?Valor\s+(?:cobrado|documento)?\s*:?\s*R?\$?\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'Valor\s+cobrado\s*:?\s*R?\$?\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{2})?)',
        ]
        
        for padrao in padroes_secundarios:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                valor_str = match.group(1)
                if ',' in valor_str or '.' in valor_str:
                    valor_limpo = valor_str.replace('.', '').replace(',', '.')
                else:
                    continue
                
                try:
                    valor_float = float(valor_limpo)
                    if 0.01 <= valor_float <= 1000000.0:
                        logger.debug(f"✅ Valor extraído (padrão secundário): R$ {valor_float:,.2f}")
                        return valor_float
                except:
                    continue
        
        # Padrão 3: Buscar qualquer número com formato monetário brasileiro (último recurso)
        # Formato: X.XXX,XX ou X,XX (com pelo menos uma vírgula para centavos)
        padrao_monetario = r'R?\$?\s*([\d]{1,3}(?:\.\d{3})*,\d{2})'
        matches = re.finditer(padrao_monetario, texto, re.IGNORECASE)
        
        # Pegar o primeiro valor que faça sentido (não muito grande)
        for match in matches:
            valor_str = match.group(1)
            valor_limpo = valor_str.replace('.', '').replace(',', '.')
            try:
                valor_float = float(valor_limpo)
                if 0.01 <= valor_float <= 1000000.0:
                    logger.debug(f"✅ Valor extraído (padrão monetário genérico): R$ {valor_float:,.2f}")
                    return valor_float
            except:
                continue
        
        logger.warning("⚠️ Nenhum valor válido encontrado no boleto")
        return None
    
    def _extrair_vencimento(self, texto: str) -> Optional[str]:
        """Extrai data de vencimento."""
        # Padrão 1: "Vencimento" seguido de data DD/MM/YYYY
        padroes = [
            r'Vencimento\s*:?\s*(\d{2}/\d{2}/\d{4})',
            r'Venc\.\s*:?\s*(\d{2}/\d{2}/\d{4})',
            r'Vencimento\s+(\d{2}/\d{2}/\d{4})',
            # Padrão alternativo: data após "Vencimento" sem dois pontos
            r'Vencimento[^\d]*(\d{2}/\d{2}/\d{4})',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                data_str = match.group(1)
                # Converter para YYYY-MM-DD
                try:
                    dt = datetime.strptime(data_str, '%d/%m/%Y')
                    return dt.strftime('%Y-%m-%d')
                except:
                    continue
        
        return None
    
    def _extrair_beneficiario(self, texto: str) -> Optional[str]:
        """Extrai nome do beneficiário (também conhecido como cedente)."""
        # ✅ CORREÇÃO: Buscar tanto "Beneficiário" quanto "Cedente" (são sinônimos)
        # Exemplos de formatos encontrados:
        # - "Beneficiário MercadoPago.com Representações Ltda CNPJ 10.573.521/0001-91"
        # - "Cedente PLUXEE BENEFICIOS BRASIL S.A"
        # - "Beneficiário Final MercadoPago.com Representações Ltda"
        
        # ✅ CORREÇÃO CRÍTICA: Evitar capturar campos adjacentes como "Espécie", "Vencimento"
        # Priorizar captura até CNPJ, que é o delimitador mais confiável
        padroes = [
            # Padrão 1: "Beneficiário" seguido de nome até CNPJ (PRIORIDADE MÁXIMA)
            # Captura até encontrar "CNPJ" (delimitador mais confiável)
            r'Beneficiário\s+([A-Z][A-Za-z0-9\s\.\-,/]+?)(?=\s+CNPJ)',
            # Padrão 2: "Beneficiário Final" seguido de nome até CNPJ
            r'Beneficiário\s+Final\s+([A-Z][A-Za-z0-9\s\.\-,/]+?)(?=\s+CNPJ)',
            # Padrão 3: "Cedente" seguido de nome até CNPJ ou Agência/Código
            r'Cedente\s+([A-Z][A-Za-z0-9\s\.\-,/]+?)(?=\s+(?:CNPJ|Agência|Código))',
            # Padrão 4: "Beneficiário" seguido de nome até Agência/Código (se não tiver CNPJ)
            r'Beneficiário\s+([A-Z][A-Za-z0-9\s\.\-,/]+?)(?=\s+(?:Agência|Código|Av\.|Rua|Endereço|CEP))',
            # Padrão 5: "Cedente" seguido de nome até Agência/Código (se não tiver CNPJ)
            r'Cedente\s+([A-Z][A-Za-z0-9\s\.\-,/]+?)(?=\s+(?:Agência|Código|Av\.|Rua|Endereço|CEP))',
            # Padrão 6: "Beneficiário" ou "Cedente" em linha separada, nome na próxima linha
            r'(?:Beneficiário|Cedente)\s*\n\s*([A-Z][A-Za-z0-9\s\.\-,/]+?)(?=\s+(?:CNPJ|Agência|Código|\n\n|\n))',
        ]
        
        for i, padrao in enumerate(padroes, 1):
            match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                beneficiario = match.group(1).strip()
                # Limpar quebras de linha, espaços extras e caracteres especiais no final
                beneficiario = re.sub(r'\s+', ' ', beneficiario)
                beneficiario = re.sub(r'\s*[|]\s*$', '', beneficiario)  # Remove pipe no final
                beneficiario = re.sub(r'\s*/\s*$', '', beneficiario)  # Remove barra no final
                beneficiario = beneficiario.strip()
                
                # ✅ VALIDAÇÃO MELHORADA: Rejeitar se contém palavras de campos adjacentes
                palavras_invalidas = ['Espécie', 'Vencimento', 'Real', 'DM', 'Aceite', 'Número', 'Nosso']
                if any(palavra.lower() in beneficiario.lower() for palavra in palavras_invalidas):
                    logger.debug(f"⚠️ Beneficiário rejeitado (contém campo adjacente): {beneficiario}")
                    continue
                
                # Validar: deve ter pelo menos 3 caracteres e não ser apenas números
                if beneficiario and len(beneficiario) > 3:
                    # Verificar se não é apenas números/CNPJ
                    texto_limpo = beneficiario.replace('.', '').replace('/', '').replace('-', '').replace(' ', '')
                    if not texto_limpo.isdigit():
                        logger.info(f"✅ Beneficiário extraído (padrão {i}): {beneficiario}")
                        return beneficiario
        
        logger.warning("⚠️ Beneficiário/Cedente não encontrado no PDF")
        return None
