#!/bin/bash
set -e

APP_MODULE="app.main:app"
HOST="127.0.0.1"
PORT="8000"

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Redis 실행 (이미 켜져 있으면 무시)
echo ">>> Redis 시작"
sudo service redis-server start 2>/dev/null || true

# Celery Worker 백그라운드 실행
echo ">>> Celery Worker 시작"
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 celery -A app.worker worker --loglevel=info --pool=solo &
CELERY_PID=$!

# 스크립트 종료 시 Celery도 같이 종료
trap "echo '>>> 종료 중...'; kill $CELERY_PID 2>/dev/null" EXIT

# FastAPI 서버 실행 (포그라운드)
echo ">>> FastAPI 서버 시작 | http://$HOST:$PORT"
python3 -m uvicorn $APP_MODULE --host $HOST --port $PORT --reload
