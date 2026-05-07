#!/bin/sh
# Inicialização: pastas graváveis, migrações/esquema SQLite, arranque do Streamlit.
set -eu

umask 022
mkdir -p /app/data /app/backups
# Volumes externos podem ser criados no hospedeiro com dono UID/GID 1000 (mesmo utilizador ``app`` da imagem).
chmod 775 /app/data /app/backups 2>/dev/null || true

cd /app
python -c "from src.database.connection import create_tables; create_tables()"

exec streamlit run src/app.py \
  --server.port="${STREAMLIT_SERVER_PORT:-8501}" \
  --server.address="${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}"
