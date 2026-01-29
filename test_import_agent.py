
import sys
import os
import logging

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    print("🔍 Tentando importar ProcessoAgent...")
    from services.agents.processo_agent import ProcessoAgent
    print("✅ ProcessoAgent importado com sucesso!")
    
    print("🔍 Tentando inicializar ProcessoAgent...")
    agent = ProcessoAgent()
    print("✅ ProcessoAgent inicializado com sucesso!")
    
except ImportError as e:
    print(f"❌ Erro de IMPORTAÇÃO: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Erro GERAL: {e}")
    import traceback
    traceback.print_exc()
