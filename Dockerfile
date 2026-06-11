# ── Stage 1: Build Next.js frontend ──────────────────────────
FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
ARG NEXT_PUBLIC_API_URL
# Default "" means the browser resolves /api/v1/* relative to the current
# host, which nginx (in this container) proxies to the FastAPI backend.
# For docker-compose or separate deployments, set this to the backend URL.
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-""}
RUN npm run build

# ── Stage 2: Build Python backend deps ───────────────────────
FROM python:3.12-slim@sha256:a39549e211a16149edf74e5fdc9ef03a6767e46cd987c5048b6659b6c9904c94 AS backend-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 3: Runtime ─────────────────────────────────────────
FROM python:3.12-slim@sha256:a39549e211a16149edf74e5fdc9ef03a6767e46cd987c5048b6659b6c9904c94 AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend-builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY backend/ ./backend/
COPY --from=frontend-builder /app/.next/standalone ./frontend/
COPY --from=frontend-builder /app/.next/static ./frontend/.next/static
COPY nginx.conf /etc/nginx/nginx.conf
COPY --chmod=755 start.sh /start.sh

RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /var/lib/nginx/proxy /var/cache/nginx \
    && chown -R app:app /app /var/lib/nginx /var/cache/nginx /tmp /var/log/nginx

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

USER app

EXPOSE 8080

CMD ["/start.sh"]
