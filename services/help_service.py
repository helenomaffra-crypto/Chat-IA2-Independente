"""
HelpService
===========

Respostas determinísticas para perguntas de ajuda do usuário (UI).
Evita depender de IA para "o que posso fazer?" e mantém a lista de capacidades atualizada.
"""

from __future__ import annotations


def obter_texto_o_que_posso_fazer() -> str:
    linhas = [
        "💡 **O que eu posso fazer (principais funções)**",
        "",
        "## Processos (Kanban / Importação)",
        "- **O que temos pra hoje?** (dashboard do dia)",
        "- **Detalhe/Status de um processo**: `detalhe BGR.0080/25`",
        "- **Sincronizar processos ativos** (atualiza o cache do Kanban automaticamente a cada 5 min; você também pode pedir manualmente)",
        "- **Pendências**: `pendências de frete`, `pendências de AFRMM`, `pendências de ICMS`",
        "",
        "## DUIMP / Documentos",
        "- **Criar DUIMP (validação)**, consultar dados e acompanhar documentos vinculados",
        "",
        "## Mercante (AFRMM) ✅",
        "- **Pagar AFRMM**: `pagar afrmm BGR.0080/25` (gera preview e pede confirmação)",
        "- **Histórico AFRMM**: `histórico do afrmm do BGR.0080/25` (mostra comprovante/print quando houver)",
        "",
        "## Emails (Microsoft 365 / Graph)",
        "- **Ler emails**: `leia meus emails de hoje` / `ler emails`",
        "- **Detalhar email**: `ler o email 1`",
        "- **Enviar/Responder email** (com confirmação quando necessário)",
        "",
        "## Siscomex / Notícias",
        "- **Notícias Siscomex**: `ultimas noticias siscomex`",
        "",
        "## Financeiro (Banco)",
        "- **Sincronizar extratos** (BB/Santander)",
        "- **Conciliação bancária** (classificar lançamentos por despesa/processo)",
        "- **Histórico de pagamentos** (menu Financeiro → Histórico de Pagamentos)",
        "",
        "## Configurações",
        "- Ajustar **email de envio** e **mailbox de leitura** (Graph)",
        "- Ajustar **Mercante usuário/senha**",
        "",
        "Se quiser, me diga seu objetivo (ex.: “quero pagar AFRMM”, “quero ver pendências”, “quero montar DUIMP”) e eu te guio no passo a passo.",
    ]
    return "\n".join(linhas)

