#!/usr/bin/env python3
"""
Busca um email específico via Microsoft Graph por remetente (from).

Uso:
  docker compose exec web python debug_email_search.py contato@jotapetecnologia.com

Opcional:
  docker compose exec web python debug_email_search.py contato@jotapetecnologia.com 60
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python debug_email_search.py <from_email> [max_days]")
        return 2

    from_email = (sys.argv[1] or "").strip()
    max_days = int(sys.argv[2]) if len(sys.argv) >= 3 else 30

    from services.email_service import get_email_service

    svc = get_email_service()
    if not getattr(svc, "has_microsoft_graph", False):
        print("EmailService não está com Microsoft Graph habilitado.")
        return 1

    mailbox = getattr(svc, "default_mailbox", None)
    token = svc.get_access_token()
    if not token:
        print("Não consegui obter token do Graph.")
        return 1

    now_utc = datetime.now(timezone.utc)
    cutoff = (now_utc - timedelta(days=max_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Graph filter por remetente
    # https://learn.microsoft.com/en-us/graph/query-parameters?tabs=http
    filter_query = f"receivedDateTime ge {cutoff} and from/emailAddress/address eq '{from_email}'"

    url = f"https://graph.microsoft.com/v1.0/users/{mailbox}/messages"
    params = {
        "$filter": filter_query,
        "$orderby": "receivedDateTime desc",
        "$top": 25,
        "$select": "id,subject,from,receivedDateTime,parentFolderId,isRead",
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    import requests

    r = requests.get(url, headers=headers, params=params, timeout=30)
    print("== Graph search ==")
    print(f"mailbox: {mailbox}")
    print(f"from: {from_email}")
    print(f"cutoff_utc: {cutoff} (max_days={max_days})")
    print(f"status: {r.status_code}")
    if r.status_code != 200:
        print(r.text[:2000])
        return 1

    data = r.json()
    msgs = data.get("value") or []
    print(f"matches: {len(msgs)}")
    for m in msgs[:10]:
        frm = (m.get("from") or {}).get("emailAddress", {}) or {}
        print(
            f"- {m.get('receivedDateTime')} | {frm.get('address')} | {m.get('subject')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

