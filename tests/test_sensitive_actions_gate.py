import sys
import uuid


def test_criar_duimp_bloqueado_sem_pending_intent():
    """
    Regressão de segurança:
    Nunca permitir executar criar_duimp diretamente (sem PendingIntent em status executing).
    """
    sys.path.insert(0, ".")

    from services.chat_service import ChatService

    cs = ChatService.__new__(ChatService)  # evitar init pesado; gate deve retornar antes de usar outros attrs

    r = ChatService._executar_funcao_tool(
        cs,
        "criar_duimp",
        {"processo_referencia": "DMD.0001/26", "ambiente": "validacao", "confirmar": True},
        mensagem_original="sim",
        session_id="sess_test",
    )

    assert isinstance(r, dict)
    assert r.get("sucesso") is False
    assert r.get("error") == "SENSITIVE_ACTION_REQUIRES_PENDING_INTENT"


def test_confirmacao_duimp_exige_e_passa_intent_id():
    """
    Confirmação de DUIMP deve usar PendingIntent (SQLite) e passar _confirmed_intent_id para execução.
    """
    sys.path.insert(0, ".")

    from services.pending_intent_service import PendingIntentService
    from services.handlers.confirmation_handler import ConfirmationHandler

    session_id = f"test_sess_{uuid.uuid4()}"
    intent_id = PendingIntentService.criar_pending_intent(
        session_id=session_id,
        action_type="create_duimp",
        tool_name="criar_duimp",
        args_normalizados={"processo_referencia": "DMD.0001/26", "ambiente": "validacao"},
        preview_text="preview duimp",
    )
    assert intent_id

    chamadas = []

    def _exec(tool_name, args, **kwargs):
        chamadas.append((tool_name, args, kwargs))
        return {"sucesso": True, "resposta": "ok", "numero": "X", "versao": "0"}

    ch = ConfirmationHandler(
        email_send_coordinator=None,
        obter_email_para_enviar=lambda *_args, **_kwargs: None,
        executar_funcao_tool=_exec,
        extrair_processo_referencia=lambda *_args, **_kwargs: None,
    )

    out = ch.processar_confirmacao_duimp(
        mensagem="sim",
        estado_duimp=None,
        session_id=session_id,
    )

    assert out.get("sucesso") is True
    assert chamadas, "esperava execução de criar_duimp via _executar_funcao_tool"
    tool_name, args, kwargs = chamadas[0]
    assert tool_name == "criar_duimp"
    assert args.get("_confirmed_intent_id") == intent_id
    assert args.get("_confirmed_action_type") == "create_duimp"

