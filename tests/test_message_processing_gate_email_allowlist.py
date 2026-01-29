import sys
import json


def test_message_processing_forca_tool_email_quando_modelo_erra():
    """
    Se usuário pede email, e o modelo tenta chamar criar_duimp, o gate deve impedir e forçar tool de email.
    """
    sys.path.insert(0, ".")

    from services.message_processing_service import MessageProcessingService

    mps = MessageProcessingService(ai_service=None)

    resposta_ia_raw = {
        "content": "",
        "tool_calls": [
            {
                "function": {
                    "name": "criar_duimp",
                    "arguments": json.dumps({"processo_referencia": "DMD.0001/26", "ambiente": "validacao"})
                }
            }
        ]
    }

    chamadas = []

    def exec_tool(nome_funcao, argumentos, **kwargs):
        chamadas.append((nome_funcao, argumentos))
        return {"sucesso": True, "resposta": "ok"}

    msg = "manda um email para helenomaffra@gmail.com avisando que nao vou na reuniao de sexta. assine gustavo"
    out = mps.processar_tool_calls(
        resposta_ia_raw=resposta_ia_raw,
        mensagem=msg,
        usar_tool_calling=True,
        session_id="sess_test",
        executar_funcao_tool_fn=exec_tool,
        response_formatter=None,
    )

    assert chamadas, "esperava uma execução de tool"
    assert chamadas[0][0] in ("enviar_email_personalizado", "enviar_email"), "tool deveria ser de email, não DUIMP"
    assert out.get("sucesso") is True

