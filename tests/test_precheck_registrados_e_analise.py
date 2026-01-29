import sys
from pathlib import Path

# Garantir root no path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from unittest.mock import Mock

import db_manager
from services.precheck_service import PrecheckService


def test_precheck_foram_registrados_chama_tool_listar_processos_registrados_hoje():
    chat = Mock()
    chat._executar_funcao_tool = Mock()
    chat._extrair_processo_referencia = Mock(return_value=None)
    chat._extrair_categoria_da_mensagem = Mock(return_value="DMD")

    svc = PrecheckService(chat)

    r = svc.tentar_responder_sem_ia(
        mensagem="quais dmd foram registrados?",
        historico=[],
        session_id="sess_test",
        nome_usuario="Teste",
    )

    assert isinstance(r, dict)
    assert "tool_calls" in r
    tc = r["tool_calls"][0]["function"]
    assert tc["name"] == "listar_processos_registrados_hoje"
    assert tc["arguments"]["categoria"] == "DMD"
    assert tc["arguments"]["limite"] == 200


def test_precheck_registramos_dia_sem_ano_chama_periodo_especifico_com_ano_atual():
    chat = Mock()
    chat._executar_funcao_tool = Mock()
    chat._extrair_processo_referencia = Mock(return_value=None)
    chat._extrair_categoria_da_mensagem = Mock(return_value=None)

    svc = PrecheckService(chat)

    r = svc.tentar_responder_sem_ia(
        mensagem="o que registramos dia 22/01?",
        historico=[],
        session_id="sess_test",
        nome_usuario="Teste",
    )

    assert isinstance(r, dict)
    assert "tool_calls" in r
    tc = r["tool_calls"][0]["function"]
    assert tc["name"] == "listar_processos_registrados_periodo"
    assert tc["arguments"]["periodo"] == "periodo_especifico"
    assert tc["arguments"]["data_inicio"].startswith("22/01/")
    assert tc["arguments"]["data_fim"] == tc["arguments"]["data_inicio"]


def test_precheck_registramos_data_sem_dia_chama_periodo_especifico():
    chat = Mock()
    chat._executar_funcao_tool = Mock()
    chat._extrair_processo_referencia = Mock(return_value=None)
    chat._extrair_categoria_da_mensagem = Mock(return_value=None)

    svc = PrecheckService(chat)

    r = svc.tentar_responder_sem_ia(
        mensagem="o que registramos 22/01?",
        historico=[],
        session_id="sess_test",
        nome_usuario="Teste",
    )

    assert isinstance(r, dict)
    assert "tool_calls" in r
    tc = r["tool_calls"][0]["function"]
    assert tc["name"] == "listar_processos_registrados_periodo"
    assert tc["arguments"]["periodo"] == "periodo_especifico"
    assert tc["arguments"]["data_inicio"].startswith("22/01/")
    assert tc["arguments"]["data_fim"] == tc["arguments"]["data_inicio"]


def test_precheck_registramos_data_sem_dia_com_ano_2_digitos_chama_periodo_especifico():
    chat = Mock()
    chat._executar_funcao_tool = Mock()
    chat._extrair_processo_referencia = Mock(return_value=None)
    chat._extrair_categoria_da_mensagem = Mock(return_value=None)

    svc = PrecheckService(chat)

    r = svc.tentar_responder_sem_ia(
        mensagem="o que registramos 22/01/26?",
        historico=[],
        session_id="sess_test",
        nome_usuario="Teste",
    )

    assert isinstance(r, dict)
    assert "tool_calls" in r
    tc = r["tool_calls"][0]["function"]
    assert tc["name"] == "listar_processos_registrados_periodo"
    assert tc["arguments"]["periodo"] == "periodo_especifico"
    assert tc["arguments"]["data_inicio"] == "22/01/2026"
    assert tc["arguments"]["data_fim"] == "22/01/2026"


def test_precheck_registramos_dia_com_ano_2_digitos_chama_periodo_especifico():
    chat = Mock()
    chat._executar_funcao_tool = Mock()
    chat._extrair_processo_referencia = Mock(return_value=None)
    chat._extrair_categoria_da_mensagem = Mock(return_value=None)

    svc = PrecheckService(chat)

    r = svc.tentar_responder_sem_ia(
        mensagem="o que registramos dia 22/01/26?",
        historico=[],
        session_id="sess_test",
        nome_usuario="Teste",
    )

    assert isinstance(r, dict)
    assert "tool_calls" in r
    tc = r["tool_calls"][0]["function"]
    assert tc["name"] == "listar_processos_registrados_periodo"
    assert tc["arguments"]["periodo"] == "periodo_especifico"
    assert tc["arguments"]["data_inicio"] == "22/01/2026"
    assert tc["arguments"]["data_fim"] == "22/01/2026"


def test_precheck_em_analise_formata_registro_quando_disponivel(monkeypatch):
    # Mock db_manager para não depender do SQLite real
    monkeypatch.setattr(
        db_manager,
        "obter_dis_em_analise",
        lambda categoria=None: [
            {
                "numero_di": "2601093918",
                "situacao_di": "AGUARDANDO_PARAMETRIZACAO",
                "canal_di": "Verde",
                "processo_referencia": "DMD.0074/25",
                "data_registro": "2026-01-16 16:27:14",
            }
        ],
    )
    monkeypatch.setattr(
        db_manager,
        "obter_duimps_em_analise",
        lambda categoria=None: [
            {
                "numero_duimp": "26BR00000003906",
                "versao": "0",
                "status": "rascunho",
                "processo_referencia": "DMD.0083/25",
                "tempo_analise": "8 dia(s)",
                "data_criacao": "2026-01-07 18:56:17",
            }
        ],
    )

    chat = Mock()
    chat._executar_funcao_tool = Mock()
    chat._extrair_processo_referencia = Mock(return_value=None)
    chat._extrair_categoria_da_mensagem = Mock(return_value="DMD")

    svc = PrecheckService(chat)

    r = svc.tentar_responder_sem_ia(
        mensagem="quais dmd está em análise?",
        historico=[],
        session_id="sess_test",
        nome_usuario="Teste",
    )

    assert isinstance(r, dict)
    assert r.get("precheck") is True
    assert r.get("precheck_tipo") == "em_analise"
    texto = r.get("resposta") or ""

    # Deve incluir “Registro:” tanto para DI quanto para DUIMP (quando vier data)
    assert "DIs EM ANÁLISE" in texto
    assert "Registro:" in texto
    assert "DUIMPs EM ANÁLISE" in texto

