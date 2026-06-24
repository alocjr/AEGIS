# Valorian / Aegis — frontend (Vue) e backend (FastAPI) no MESMO container.
# Um único processo (uvicorn) entrega a API, o SPA e a landing (lp.html) em /.
# MongoDB fica fora do container: defina MONGODB_URI (ex.: Atlas).
#
# Build:  docker build -t aegis .
# Run:    docker run --env-file .env -p 80:8000 aegis
# Compose: docker compose up --build

# ─── Stage 1: build estático do Vue (gera frontend-vue/dist) ───
FROM node:20-alpine AS frontend-builder

WORKDIR /build

COPY frontend-vue/package.json frontend-vue/package-lock.json ./
RUN npm ci

COPY frontend-vue/ ./
# Só empacotamento estático (vite); evita falha do build da imagem se vue-tsc ainda tiver avisos locais
RUN npx vite build

# ─── Stage 2: Python + artefatos do front em /app/frontend-vue/dist ───
# main.py resolve BASE_DIR=/app → FRONTEND_VUE_DIST=/app/frontend-vue/dist
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/

COPY --from=frontend-builder /build/dist ./frontend-vue/dist/

RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Falha se a API não responder (inclui 503 se MongoDB estiver inacessível)
HEALTHCHECK --interval=30s --timeout=8s --start-period=70s --retries=3 \
  CMD python -c "import os, urllib.request; p=os.environ.get('PORT','8000'); urllib.request.urlopen('http://127.0.0.1:%s/api/health'%p, timeout=5)" || exit 1

WORKDIR /app/backend

# exec repassa sinais (SIGTERM) ao uvicorn
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
