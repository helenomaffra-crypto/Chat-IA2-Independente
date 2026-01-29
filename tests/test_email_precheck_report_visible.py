import sys
from types import SimpleNamespace


def test_email_precheck_report_visible_never_returns_none(monkeypatch):
    """
    Regressão do bug:
    usuário: "melhore esse relatório e envie pra X e assine Gustavo"
    com last_visible_report_id resolvido -> não pode cair em tool aleatória (ex: extrato Santander).
    """
    sys.path.insert(0, ".")

    from services.email_precheck_service import EmailPrecheckService
    import services.report_service as report_service

    # Fake report salvo (existe no banco)
    fake_report = SimpleNamespace(
        texto_chat="📌 Relatório de legislação...\n\nDecreto 6759/2009 ...\n[REPORT_META:{\"id\":\"rel_leg_123\"}]",
        tipo_relatorio="legislacao",
        categoria=None,
        criado_em="2026-01-14T16:00:00-03:00",
        meta_json={"id": "rel_leg_123"},
    )

    # Patch resolução de report_id
    monkeypatch.setattr(report_service, "_detectar_dominio_por_mensagem", lambda _msg: "processos", raising=True)
    monkeypatch.setattr(report_service, "obter_last_visible_report_id", lambda _sid, dominio="processos": {"id": "rel_leg_123"}, raising=True)
    monkeypatch.setattr(report_service, "buscar_relatorio_por_id", lambda _sid, _rid: fake_report, raising=True)

    calls = []

    class DummyChat:
        session_id_atual = "sess_test"

        def _executar_funcao_tool(self, tool_name, args, mensagem_original=None, session_id=None):
            calls.append((tool_name, args))
            # Simula preview retornado pelo ChatService.enviar_email_personalizado (confirmar_envio=False)
            if tool_name == "enviar_email_personalizado":
                preview = "📧 **Email para Envio**\n\n"
                preview += f"**Para:** {', '.join(args.get('destinatarios', []))}\n"
                preview += f"**Assunto:** {args.get('assunto')}\n\n"
                preview += f"**Mensagem:**\n{args.get('conteudo')}\n"
                preview += "\n⚠️ **Confirme para enviar** (digite 'sim' ou 'enviar')"
                return {"sucesso": True, "resposta": preview, "aguardando_confirmacao": True}
            return {"sucesso": False, "resposta": "tool não suportada no stub"}

    svc = EmailPrecheckService(DummyChat())
    msg = "melhore esse relatório e envie pra helenomaffra@gmail.com e assine Gustavo"
    res = svc.tentar_precheck_email(
        mensagem=msg,
        mensagem_lower=msg.lower(),
        historico=[{"role": "assistant", "content": "texto anterior"}],
        session_id="sess_test",
        nome_usuario="Heleno",
    )

    assert isinstance(res, dict)
    assert res.get("sucesso") is True
    assert res.get("aguardando_confirmacao") is True
    assert res.get("_processado_precheck") is True
    assert res.get("_deve_chamar_ia_para_refinar") is True
    assert "Gustavo" in (res.get("resposta") or "")

    # Não pode ter disparado ferramentas de banco/extrato
    tool_names = [c[0] for c in calls]
    assert "consultar_extrato_santander" not in tool_names
    assert "consultar_extrato_bb" not in tool_names
    assert "enviar_email_personalizado" in tool_names

