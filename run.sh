#!/bin/bash
set -e

APP_MODULE="app.main:app"
HOST="127.0.0.1"
PORT="8000"

echo ">>> FastAPI Server Start"
echo ">>> Module: $APP_MODULE"
echo ">>> Host: $HOST"
echo ">>> Port: $PORT"

cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

exec python3 -m uvicorn $APP_MODULE --host $HOST --port $PORT --reload
# python3 -m uvicorn app.main:app --reload