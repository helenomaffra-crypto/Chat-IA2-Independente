# Usar imagem oficial do Python como base (Bookworm = Debian 12 estável)
FROM python:3.9-slim-bookworm

# Evitar que o Python gere arquivos .pyc e permitir logs em tempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema (ODBC, build, PDF, Playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    unixodbc-dev \
    g++ \
    gcc \
    python3-dev \
    libpq-dev \
    ca-certificates \
    libffi-dev \
    libssl-dev \
    pkg-config \
    libgomp1 \
    libcairo2-dev \
    libjpeg-dev \
    zlib1g-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Adicionar repositório da Microsoft e instalar o driver SQL Server (MSODBC 18)
# A versão 18 é a suportada para Debian 12 em ARM64 (Mac Silicon)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Pip atualizado + requirements em camada separada para cache
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright (RPA Mercante): baixar browsers na imagem
# Evita erro: "BrowserType.launch: Executable doesn't exist ... playwright install"
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install --with-deps chromium

# Copiar o restante do código da aplicação
COPY . .

# Criar diretórios necessários e definir permissões
RUN mkdir -p downloads .secure .mtls_cache data legislacao_files \
    && chmod -R 777 downloads .secure .mtls_cache data legislacao_files

# ✅ Default: persistir SQLite em /app/data (sobrescrevível no docker-compose/.env)
ENV DB_PATH=/app/data/chat_ia.db

EXPOSE 5001

# Healthcheck para orquestração (Docker/Compose/K8s)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -sf http://localhost:5001/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--timeout", "120", "app:app"]
