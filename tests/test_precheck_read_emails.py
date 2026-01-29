import sys
from pathlib import Path

# Garantir root no path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from unittest.mock import Mock

from services.precheck_service import PrecheckService


def test_precheck_ler_meus_emails_chama_ler_emails():
    chat = Mock()
    chat._executar_funcao_tool = Mock()
    chat._extrair_processo_referencia = Mock(return_value=None)
    svc = PrecheckService(chat)

    r = svc.tentar_responder_sem_ia(
        mensagem="ler meus emails",
        historico=[],
        session_id="sess_test",
        nome_usuario="Teste"
    )

    assert isinstance(r, dict)
    assert "tool_calls" in r
    assert r["tool_calls"][0]["function"]["name"] == "ler_emails"

