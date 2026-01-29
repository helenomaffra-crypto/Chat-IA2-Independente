import sys


def test_intencao_email_personalizado_detecta_frase_natural():
    sys.path.insert(0, ".")

    from services.intent_detection_service import IntentDetectionService, IntentType

    s = IntentDetectionService()
    msg = "vc consegue mandar um email simpatico para helenomaffra@gmail.com avisando que nao vou conseguir estar na reuniao de sexta feira. assine gustavo"
    out = s.detectar_intencao(msg)

    assert out.get("intent_type") == IntentType.ENVIAR_EMAIL_PERSONALIZADO

