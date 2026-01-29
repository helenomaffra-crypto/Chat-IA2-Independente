import sys


def test_confirmacao_nao_casa_simpatico():
    """
    Regressão: "simpático" não pode disparar confirmação ("sim" como substring).
    """
    sys.path.insert(0, ".")

    from services.handlers.confirmation_handler import ConfirmationHandler

    ch = ConfirmationHandler(
        email_send_coordinator=None,
        obter_email_para_enviar=lambda *_args, **_kwargs: None,
        executar_funcao_tool=lambda *_args, **_kwargs: None,
        extrair_processo_referencia=lambda *_args, **_kwargs: None,
    )

    assert ch.detectar_confirmacao_email("simpatico", {"funcao": "enviar_email_personalizado"}) is False
    assert ch.detectar_confirmacao_email("sim", {"funcao": "enviar_email_personalizado"}) is True

    assert ch.detectar_confirmacao_duimp("simpatico", {"processo_referencia": "DMD.0001/26"}) is False
    assert ch.detectar_confirmacao_duimp("sim", {"processo_referencia": "DMD.0001/26"}) is True

