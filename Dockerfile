# BeaBa Gestão — pacote Docker (Streamlit). Executável como utilizador não-root (UID/GID 1000).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --shell /sbin/nologin --home-dir /home/app --create-home app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh /docker-entrypoint.sh
COPY . .

RUN mkdir -p /app/data /app/backups \
    && chown -R app:app /app \
    && chmod 775 /app/data /app/backups \
    && chmod +x /docker-entrypoint.sh

USER app

EXPOSE 8501

ENTRYPOINT ["/docker-entrypoint.sh"]
