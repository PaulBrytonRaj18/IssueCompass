#!/bin/sh
set -e

cleanup() {
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    nginx -s quit 2>/dev/null || true
    wait
    exit 0
}

trap cleanup TERM INT

export PORT=${PORT:-8080}

# Validate PORT is numeric to prevent sed injection in nginx config
case "$PORT" in
    ''|*[!0-9]*) echo "FATAL: PORT must be numeric, got '$PORT'"; exit 1 ;;
esac
sed -i "s/\${PORT}/$PORT/g" /etc/nginx/nginx.conf

cd /app/backend
echo "Running database reconciliation..."
python -m scripts.db_reconcile 2>&1
echo "Running database migrations..."
alembic upgrade head 2>&1
gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile - &
BACKEND_PID=$!

cd /app/frontend
PORT=3000 node server.js &
FRONTEND_PID=$!

sleep 1

nginx -g 'daemon off;'
