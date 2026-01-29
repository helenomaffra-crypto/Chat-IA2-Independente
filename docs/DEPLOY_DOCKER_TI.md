# Manual para TI — Docker do mAIke

## Objetivo
Subir o **mAIke (Flask + UI + APIs)** em Docker/Compose de forma simples e replicável, mantendo dados e downloads persistentes, e com acesso às integrações externas (SQL Server / certificados).

---

## 1) O que vai rodar em Docker (recomendação)

- **Container `maike-web`**: Flask (`app.py`) + `services/` + `templates/`
- **Volumes persistentes**:
  - **SQLite** (cache e pending intents)
  - **downloads/** (prints Mercante, TTS etc.)
  - **legislacao_files/** (se aplicável)
  - **.secure/** (certificados) como *read-only*
- **RPA Mercante (navegador)**: **fora do container** (host), ou headless no host.  
  Motivo: browser/GUI/Keychain/certificados no macOS em container costuma dar dor.

---

## 2) Comentário do TI: “SQLite sempre dá problema no Docker”

### Verdade e como evitar
SQLite funciona bem em Docker **desde que**:
- O DB esteja em **um volume local** (bind mount ou volume Docker)
- O app rode com **1 worker** (sem gunicorn com vários workers escrevendo no mesmo arquivo)
- Use **WAL** com cuidado e evite concorrência alta
- Se precisarem escalar/concurrency alta: migrar para Postgres (mais “padrão TI”)

### Pergunta para TI
- O mAIke vai ter **quantos usuários simultâneos**?
  - Se for baixo/moderado: SQLite ok com 1 worker.
  - Se for alto: melhor Postgres.

---

## 3) Perguntas que preciso que o TI responda

### A) Ambiente / onde vai rodar
- Vai rodar em **Linux server** (recomendado), Windows Server, ou Mac?
- Vai ser **Docker Compose** simples ou Kubernetes?

### B) Rede / SQL Server (crítico)
- Do container, conseguimos acessar o SQL Server?
  - Host/instância: `SQL_SERVER_OFFICE` / `SQL_SERVER_VPN` / `SQL_SERVER`
  - Porta: 1433 ou porta dinâmica?
  - DNS interno funciona dentro do Docker?
  - Se for via VPN: o container **enxerga a VPN** do host?
- Existe firewall/restrição de origem?

### C) Segredos / certificados
- Onde ficarão os certificados (`.pfx`, `.pem`, `.key`)?
  - O TI prefere: volume montado `read-only` ou secret manager?
- Vocês aceitam `.env` no host (não versionado) ou preferem secrets?

### D) Domínio / HTTPS / proxy reverso
- Vai ficar atrás de **Nginx/Traefik**?
- Precisa de HTTPS (certificado corporativo/Let’s Encrypt)?
- Porta esperada (5001 ou 80/443)?

### E) Persistência
- Onde vão persistir:
  - `chat_ia.db` (SQLite)
  - `downloads/` (prints/comprovantes)
  - `legislacao_files/` (se existir)
- Em caso de backup/restore: política do TI?

### F) Operação / logs / observabilidade
- Logs vão para onde? (stdout do container, ELK, CloudWatch, etc.)
- Healthcheck: `/api/health` ou `/health` está ok?

---

## 4) “Como vai ser o comando de subir” (esperado)
- `docker compose up -d --build`
- Atualização: `docker compose pull && docker compose up -d`

---

## 5) Decisão importante (SQLite vs Postgres)

### Se TI insistir em não usar SQLite
Eu adapto para **Postgres** (Docker-friendly), mas isso é uma mudança maior:
- trocar persistência de conversas/pending intents/cache
- migração de schema
- ajustar `db_manager`/repos

**Pergunta:** TI exige Postgres desde o início ou SQLite com 1 worker é aceitável?

---

## 6) Checklist final para TI
- [ ] Docker host definido (Linux/Windows/Mac)
- [ ] Acesso do container ao SQL Server validado (DNS/porta/VPN)
- [ ] Definição de secrets/certs (`.secure` montado read-only ou secrets)
- [ ] Definição de volumes persistentes (`data/`, `downloads/`, etc.)
- [ ] Decisão SQLite vs Postgres
- [ ] Proxy/HTTPS definido (se necessário)

