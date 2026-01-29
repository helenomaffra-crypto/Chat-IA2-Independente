import re
from typing import Optional
from datetime import datetime


def extract_processo_referencia(processo_ref: str) -> str:
    if not processo_ref:
        return processo_ref
    
    processo_upper = processo_ref.upper().strip()
    
    padrao_completo = r'^[A-Z0-9]{2,4}\.\d{1,4}/\d{2}$'
    if re.match(padrao_completo, processo_upper):
        return processo_upper
    
    padrao_parcial = r'^([A-Z0-9]{2,4})\.(\d{1,4})$'
    match = re.match(padrao_parcial, processo_upper)
    if match:
        prefixo = match.group(1)
        numero = match.group(2)
        ano_atual = datetime.now().strftime('%y')
        numero_formatado = numero.zfill(4)
        return f"{prefixo}.{numero_formatado}/{ano_atual}"
    
    return processo_upper
















