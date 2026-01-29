"""
Serviço para extrair dados de boletos usando OpenAI Vision API (GPT-4o).

Usa GPT-4 Vision para processar PDFs/imagens de boletos que não podem ser
extraídos com métodos tradicionais (pdfplumber, PyPDF2).

💰 CUSTO: ~$0.01-0.03 por boleto (dependendo da resolução)
"""
import base64
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

try:
    from ai_service import get_ai_service
    from pdf2image import convert_from_path
    from PIL import Image
    import io
except ImportError as e:
    logger.warning(f"⚠️ Dependências não disponíveis: {e}")
    get_ai_service = None
    convert_from_path = None
    Image = None
    io = None


class BoletoParserVision:
    """Parser para extrair dados de boletos usando OpenAI Vision API."""
    
    def __init__(self):
        self.ai_service = get_ai_service() if get_ai_service else None
        if not self.ai_service or not self.ai_service.enabled:
            logger.warning("⚠️ OpenAI Vision não disponível - AI Service não está habilitado")
    
    def _pdf_para_imagem(self, pdf_path: str) -> Optional[bytes]:
        """
        Converte primeira página do PDF para imagem PNG.
        
        Args:
            pdf_path: Caminho do arquivo PDF
            
        Returns:
            Bytes da imagem PNG ou None se falhar
        """
        if not convert_from_path:
            logger.error("❌ pdf2image não está instalado. Instale com: pip install pdf2image pillow")
            return None
        
        try:
            # Converter primeira página para imagem
            images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=300)
            if not images:
                return None
            
            # Converter PIL Image para bytes PNG
            img_buffer = io.BytesIO()
            images[0].save(img_buffer, format='PNG')
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Erro ao converter PDF para imagem: {e}", exc_info=True)
            return None
    
    def _imagem_para_base64(self, image_bytes: bytes) -> str:
        """Converte bytes de imagem para base64."""
        return base64.b64encode(image_bytes).decode('utf-8')
    
    def extrair_dados_boleto_vision(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extrai dados do boleto usando OpenAI Vision API.
        
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
        if not self.ai_service or not self.ai_service.enabled:
            return {
                'sucesso': False,
                'erro': 'OpenAI Vision não está disponível. Configure DUIMP_AI_ENABLED=true e DUIMP_AI_API_KEY no .env',
                'tipo_erro': 'vision_nao_disponivel'
            }
        
        try:
            # 1. Converter PDF para imagem
            logger.info(f"🖼️ Convertendo PDF para imagem: {pdf_path}")
            image_bytes = self._pdf_para_imagem(pdf_path)
            if not image_bytes:
                return {
                    'sucesso': False,
                    'erro': 'Não foi possível converter PDF para imagem',
                    'tipo_erro': 'conversao_falhou'
                }
            
            # 2. Converter para base64
            image_base64 = self._imagem_para_base64(image_bytes)
            
            # 3. Criar prompt para GPT-4 Vision
            system_prompt = """Você é um especialista em extrair dados de boletos bancários brasileiros.

Analise a imagem do boleto e extraia APENAS os seguintes dados:
1. Código de barras (44 ou 47 dígitos, apenas números, sem pontos ou espaços)
2. Valor do documento (número decimal, ex: 900.00)
3. Data de vencimento (formato YYYY-MM-DD)
4. Nome do beneficiário/cedente (opcional)

IMPORTANTE:
- Código de barras: deve ter exatamente 44 ou 47 dígitos (apenas números)
- Valor: número decimal (ex: 900.00, 1234.56)
- Data: formato YYYY-MM-DD (ex: 2026-02-08)
- Se algum dado não estiver visível, retorne null para esse campo

Responda APENAS com um JSON válido no formato:
{
  "codigo_barras": "34191093216412992293280145580009313510000090000",
  "valor": 900.00,
  "vencimento": "2026-02-08",
  "beneficiario": "PLUXEE BENEFICIOS BRASIL S.A"
}"""

            user_prompt = "Extraia os dados do boleto bancário desta imagem."
            
            # 4. Chamar OpenAI Vision API
            logger.info("🤖 Chamando OpenAI Vision API...")
            
            # Usar método direto do OpenAI client
            try:
                from openai import OpenAI
                client = OpenAI(api_key=os.getenv('DUIMP_AI_API_KEY'))
                
                response = client.chat.completions.create(
                    model="gpt-4o",  # gpt-4o tem suporte a vision
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": user_prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=500,
                    temperature=0.1
                )
                
                # 5. Extrair resposta
                resposta_texto = response.choices[0].message.content.strip()
                logger.info(f"📥 Resposta da Vision API: {resposta_texto[:200]}...")
                
                # 6. Parsear JSON da resposta
                import json
                # Remover markdown code blocks se houver
                if "```json" in resposta_texto:
                    resposta_texto = resposta_texto.split("```json")[1].split("```")[0].strip()
                elif "```" in resposta_texto:
                    resposta_texto = resposta_texto.split("```")[1].split("```")[0].strip()
                
                dados = json.loads(resposta_texto)
                
                # 7. Validar e formatar dados
                codigo_barras = dados.get('codigo_barras', '').strip()
                # Remover pontos e espaços do código de barras
                codigo_barras = ''.join(filter(str.isdigit, codigo_barras))
                
                if len(codigo_barras) not in [44, 47]:
                    return {
                        'sucesso': False,
                        'erro': f'Código de barras inválido: {len(codigo_barras)} dígitos (deve ter 44 ou 47)',
                        'tipo_erro': 'codigo_barras_invalido',
                        'dados_parciais': dados
                    }
                
                valor = float(dados.get('valor', 0))
                vencimento = dados.get('vencimento', '').strip()
                beneficiario = dados.get('beneficiario', '').strip() or None
                
                # Validar data
                try:
                    datetime.strptime(vencimento, '%Y-%m-%d')
                except ValueError:
                    return {
                        'sucesso': False,
                        'erro': f'Data de vencimento inválida: {vencimento} (formato esperado: YYYY-MM-DD)',
                        'tipo_erro': 'vencimento_invalido',
                        'dados_parciais': dados
                    }
                
                logger.info(f"✅ Dados extraídos com sucesso: código={codigo_barras[:10]}..., valor={valor}, vencimento={vencimento}")
                
                return {
                    'sucesso': True,
                    'codigo_barras': codigo_barras,
                    'valor': valor,
                    'vencimento': vencimento,
                    'beneficiario': beneficiario,
                    'metodo': 'openai_vision'
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Erro ao parsear JSON da resposta: {e}")
                logger.error(f"Resposta recebida: {resposta_texto}")
                return {
                    'sucesso': False,
                    'erro': f'Resposta da API não é JSON válido: {str(e)}',
                    'tipo_erro': 'json_invalido',
                    'resposta_bruta': resposta_texto
                }
            except Exception as e:
                logger.error(f"❌ Erro ao chamar OpenAI Vision API: {e}", exc_info=True)
                return {
                    'sucesso': False,
                    'erro': f'Erro ao processar com Vision API: {str(e)}',
                    'tipo_erro': 'vision_api_erro'
                }
                
        except Exception as e:
            logger.error(f"❌ Erro geral ao extrair dados com Vision: {e}", exc_info=True)
            return {
                'sucesso': False,
                'erro': str(e),
                'tipo_erro': 'erro_geral'
            }
