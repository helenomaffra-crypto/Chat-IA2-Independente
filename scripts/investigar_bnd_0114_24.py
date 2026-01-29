import sys
import os
from datetime import datetime

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sql_server_adapter import SQLServerAdapter

def investigar_bnd_0114_24():
    adapter = SQLServerAdapter()
    # Forçar IP da VPN e banco correto
    adapter.server = '172.16.20.10'
    adapter.instance = None
    adapter.database = 'mAIke_assistente'
    
    print(f"🔍 Investigando BND.0114/24 no host {adapter.server} e banco {adapter.database}...")
    
    # 1. Buscar na DOCUMENTO_ADUANEIRO por processo
    query_doc = """
    SELECT id_documento, numero_documento, tipo_documento, data_registro, processo_referencia
    FROM dbo.DOCUMENTO_ADUANEIRO
    WHERE processo_referencia LIKE '%BND.0114/24%'
    """
    res_doc = adapter.execute_query(query_doc)
    print("\n--- Documentos vinculados ao processo BND.0114/24 ---")
    docs = res_doc.get('data', [])
    print(docs)

    # 2. Buscar QUALQUER documento registrado em Janeiro/2026 para ver se há algum BND
    query_jan_bnd = """
    SELECT id_documento, numero_documento, tipo_documento, data_registro, processo_referencia
    FROM dbo.DOCUMENTO_ADUANEIRO
    WHERE data_registro >= '2026-01-01' AND data_registro <= '2026-01-31'
      AND processo_referencia LIKE 'BND%'
    """
    res_jan_bnd = adapter.execute_query(query_jan_bnd)
    print("\n--- Documentos BND registrados em Janeiro/2026 na DOCUMENTO_ADUANEIRO ---")
    print(res_jan_bnd.get('data', []))

if __name__ == "__main__":
    investigar_bnd_0114_24()
