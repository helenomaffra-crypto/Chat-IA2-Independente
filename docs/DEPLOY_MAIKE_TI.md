# Guia para TI — Deploy do **mAIke (Chat IA Independente)** no servidor (`maike.makeconsultores.com.br`)

## Visão geral (o que vai rodar)
- **Aplicação**: `Chat-IA2-Independente` (Flask) em **Docker Compose**
- **Proxy**: **Nginx local** no servidor (reverse proxy + TLS)
- **Persistência local**: **SQLite** (histórico, contexto, pending intents, etc.)
- **Fonte externa**: **SQL Server** (acesso direto do servidor — **sem VPN**)
- **Arquivos grandes**: **NESH** (ficam no servidor e são montados como volume no container)

---

## Pré‑requisitos no servidor
- **Linux** + **Docker Engine**
- **Docker Compose** (`docker compose version`)
- **Nginx** instalado (ou já existente)
- **Rede**:
  - saída HTTPS para provedores de IA (OpenAI/Anthropic) e demais integrações usadas
  - acesso ao **SQL Server** (host/porta/instância) pela rede interna
- **DNS**: `maike.makeconsultores.com.br` apontando para o IP do servidor

---

## O que precisa ser persistido (não pode ficar “dentro do container”)
Esses itens precisam ficar em **pastas do servidor** e serem montados via **volume**:
- **SQLite** (arquivo `chat_ia.db`)
- **NESH** (pasta grande)
- (se existir) pastas de **uploads**, **logs**, **cache**

Sugestão de estrutura no servidor:

```text
/srv/maike/
  app/                # código do projeto (docker-compose.yml, Dockerfile, etc.)
  data/
    sqlite/           # chat_ia.db (persistente)
  nesh/               # base NESH (arquivos grandes)
  logs/               # logs (opcional)
  env/
    .env              # variáveis de ambiente de produção
```

---

## Variáveis de ambiente (`.env`)
Criar um `.env` de produção no servidor contendo:
- **IA**: provider e API key (OpenAI/Anthropic)
- **SQL Server**: host / database / user / password e flags de modo
- **Paths**: caminho da NESH (o path “dentro do container”, via volume)
- **Porta interna**: app padrão **5001** (o Nginx vai fazer proxy)

> Importante: o `.env` **não é versionado** e não deve ficar exposto.

---

## Apoio do agente (mAIke) — o que dá pra fazer / limitações
**O agente consegue ajudar muito**, mas não consegue “entrar no servidor” sozinho.

- **O que eu consigo fazer (como agente):**
  - montar o roteiro de deploy (passo a passo) específico do ambiente de vocês
  - ajustar arquivos (compose, paths, documentação) para rodar no servidor
  - guiar o time/usuário via comandos copiáveis e troubleshooting (analisando logs/outputs)

- **O que eu não consigo fazer:**
  - executar comandos no servidor da empresa sem que alguém com acesso rode
  - copiar arquivos para o servidor (projeto, NESH, SQLite) sem que alguém faça o upload
  - configurar Nginx/TLS diretamente no servidor sem acesso

**Se a TI (ou alguém com acesso) conseguir rodar comandos e colar os outputs**, dá para fazer o deploy guiado com segurança.

---

## Como tratar a NESH (arquivos grandes)
Não colocar a NESH dentro da imagem Docker. Fazer via volume:
1. **Copiar a pasta NESH para o servidor** (ex.: `/srv/maike/nesh/`)
2. **Montar como volume** no `docker-compose.yml` (bind mount)
3. Ajustar no `.env` o caminho usado pela aplicação para localizar a NESH (apontando para o path montado no container, ex.: `/data/nesh`).

---

## Subida do projeto no servidor (sem “copiar Docker do micro”)
Você não transfere “o Docker” do seu computador. Você transfere **o projeto** (ou a imagem) e o servidor roda o compose.

### Opção A (recomendada): levar o código e buildar no servidor
1. Transferir a pasta do projeto para `/srv/maike/app/` (git/zip/rsync/scp)
2. No servidor:

```bash
cd /srv/maike/app
docker compose up -d --build
docker compose ps
docker compose logs -f web
```

### Opção B: levar a imagem pronta
No seu micro:

```bash
docker images
docker save <nome_da_imagem>:<tag> -o maike_web.tar
```

No servidor:

```bash
docker load -i maike_web.tar
cd /srv/maike/app
docker compose up -d
```

---

## Nginx (reverse proxy + HTTPS)
Configurar um site para `maike.makeconsultores.com.br`:
- Nginx escuta **80/443**
- Faz proxy para o container (porta exposta no host ou rede docker)
- Habilitar headers padrão (`X-Forwarded-For`, `X-Forwarded-Proto`)
- Ajustar timeouts (algumas respostas podem demorar)
- TLS via Let’s Encrypt (se já usam padrão interno, repetir o mesmo)

---

## Pontos que costumam “pegar”
### SQL Server
Como o SQL Server está “direto” do servidor, normalmente é só:
- confirmar host/porta/instância
- credenciais e databases corretos no `.env`
- garantir que o modo de conexão usado no container (pyodbc/Node adapter) está funcional no ambiente

### Persistência do SQLite
Sem volume, a aplicação perde:
- histórico e contexto
- pending intents (confirmações de ações sensíveis)

---

## Operação (comandos úteis)

```bash
# status
docker compose ps

# logs
docker compose logs -f web

# reiniciar só o backend
docker compose restart web

# atualizar (rebuild)
docker compose up -d --build

# parar
docker compose down
```

---

## Informações que TI precisa confirmar para fechar o deploy
- Path definitivo (ex.: `/srv/maike/`)
- Como será o TLS (Let’s Encrypt / padrão interno)
- Se vão migrar o `chat_ia.db` atual do micro ou começar vazio
- Onde a NESH vai ficar (ex.: `/srv/maike/nesh/`)
- Porta do serviço atrás do Nginx (qual porta o compose publica no host)

