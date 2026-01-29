import sys
from pathlib import Path

# Garantir root no path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))


def test_tool_router_tem_mapeamento_listar_processos_registrados_hoje():
    from services.tool_router import ToolRouter

    router = ToolRouter()
    assert router.tool_to_agent.get("listar_processos_registrados_hoje") == "processo"

