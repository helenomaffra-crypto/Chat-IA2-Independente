# Página não abre com Docker — diagnóstico

Quando `docker compose up -d` sobe os 3 containers mas a página "não abre", use estes passos.

## 0. (Opcional) Rebuild se a imagem for antiga

Se aparece `No services to build` e você mudou algo no app/Dockerfile, force um rebuild:

```bash
docker compose build web
docker compose up -d
```

## 1. Subir de novo (nginx agora espera o app ficar saudável)

O nginx foi ajustado para só iniciar **depois** do app responder no healthcheck. Isso evita 502 por "app ainda subindo".

```bash
docker compose down
docker compose up -d
```

Espere **cerca de 1 minuto** (o app tem `start_period: 40s`).

## 2. Testar o app direto (sem nginx)

No navegador ou no terminal:

```bash
curl -s http://localhost:5001/api/health
```

- **Se responder JSON** → o app está ok. O problema é nginx ou a porta 80.
- **Se der erro / nada** → o app não está ouvindo; veja o passo 4.

## 3. Testar pela porta 80 e 8080

- **http://localhost** (porta 80)
- **http://localhost:8080** (alternativa; use se a 80 estiver em uso ou bloqueada no Mac)

Se **5001** funciona e **80/8080** não, o nginx é o suspeito (proxy, rede, etc.).

## 4. Ver logs do app (se 5001 não responder)

```bash
docker compose logs web --tail 150
```

Procure por:

- `Traceback` / `Error` → falha ao importar ou ao conectar DB/APIs
- `Booting worker` ou `Listening at` → app subiu; se mesmo assim 5001 não responder, pode ser firewall/porta

## 5. Ver logs do nginx (se 80/8080 não abrir mas 5001 sim)

```bash
docker compose logs nginx --tail 50
```

Se aparecer `upstream timed out` ou `502`, o nginx está chamando o `web` mas o backend não responde a tempo — confira se o app está realmente saudável (passo 2).

## 6. Resumo de URLs

| URL | Quem atende |
|-----|-------------|
| http://localhost:5001 | App (Gunicorn) direto |
| http://localhost:80 ou http://localhost | Nginx → app |
| http://localhost:8080 | Nginx → app (mesmo serviço, outra porta no host) |

## Alterações feitas para "não abrir"

1. **nginx só sobe depois do app estar saudável**  
   `depends_on: web: condition: service_healthy` — evita 502 no início.

2. **Porta 8080 como alternativa**  
   Se no macOS a 80 estiver bloqueada ou em uso, use `http://localhost:8080`.

3. **App na 5001**  
   O serviço `web` já expõe `5001:5001`; você pode usar sempre `http://localhost:5001` para desenvolvimento.
