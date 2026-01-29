"""
Utilitário para converter PNG em PDF.
Usado para converter comprovantes AFRMM de PNG para PDF.
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def converter_png_para_pdf(png_path: str, pdf_path: Optional[str] = None) -> Optional[str]:
    """
    Converte um arquivo PNG para PDF.
    
    Args:
        png_path: Caminho do arquivo PNG
        pdf_path: Caminho de destino do PDF (opcional, usa mesmo nome com extensão .pdf)
    
    Returns:
        Caminho do PDF gerado ou None se falhar
    """
    try:
        from PIL import Image
        
        png_file = Path(png_path)
        if not png_file.exists():
            logger.warning(f"⚠️ Arquivo PNG não encontrado: {png_path}")
            return None
        
        # Se pdf_path não foi fornecido, usar mesmo nome com extensão .pdf
        if not pdf_path:
            pdf_path = str(png_file.with_suffix('.pdf'))
        
        pdf_file = Path(pdf_path)
        
        # Abrir imagem PNG
        try:
            img = Image.open(png_file)
            # Converter para RGB se necessário (PDF não suporta RGBA diretamente)
            if img.mode == 'RGBA':
                # Criar fundo branco para imagens com transparência
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Salvar como PDF
            img.save(pdf_file, 'PDF', resolution=100.0, quality=95)
            
            logger.info(f"✅ PNG convertido para PDF: {png_path} → {pdf_path}")
            return str(pdf_file)
            
        except Exception as e:
            logger.error(f"❌ Erro ao converter PNG para PDF: {e}", exc_info=True)
            return None
            
    except ImportError:
        logger.warning("⚠️ Pillow não está instalado. Instale com: pip install Pillow")
        return None
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao converter PNG para PDF: {e}", exc_info=True)
        return None
