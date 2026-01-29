#!/usr/bin/env python3
"""
Diagnóstico rápido do leitor de emails (Microsoft Graph).

Uso (dentro do Docker):
  docker compose exec web python debug_email_graph.py

Não imprime token nem secrets.
"""
from __future__ import annotations

from collections import Counter


def main() -> int:
    from services.email_service import get_email_service

    svc = get_email_service()
    print("== Email Graph debug ==")
    print(f"has_microsoft_graph: {getattr(svc, 'has_microsoft_graph', False)}")
    print(f"default_mailbox: {getattr(svc, 'default_mailbox', None)}")

    # Buscar uma janela maior para provar se existem emails recentes nessa mailbox
    result = svc.read_emails(limit=20, filter_read=False, max_days=30)
    if not result.get("sucesso"):
        print(f"ERRO: {result.get('erro')}")
        return 1

    debug = result.get("debug") or {}
    emails = result.get("emails") or []
    print(f"emails_returned: {len(emails)}")
    if debug:
        print(f"debug: {debug}")

    if not emails:
        return 0

    senders = Counter([e.get("from") or "N/A" for e in emails])
    print("top_senders:")
    for sender, count in senders.most_common(10):
        print(f"  - {sender}: {count}")

    print("\nfirst_5:")
    for e in emails[:5]:
        print(
            f"- {e.get('received_datetime')} | {e.get('from')} | {e.get('subject')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

