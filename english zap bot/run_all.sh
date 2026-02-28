#!/usr/bin/env bash
# Run both API server and bot on macOS
# API runs in background; bot runs in foreground (Ctrl+C to stop)

cd "$(dirname "$0")"
source ../venv/bin/activate

echo "Starting API server on http://localhost:8765 ..."
python3 api_server.py &
API_PID=$!

sleep 2
if ! kill -0 $API_PID 2>/dev/null; then
  echo "API failed to start. Check logs above."
  exit 1
fi

echo "Starting Telegram bot..."
trap "kill $API_PID 2>/dev/null; exit" INT TERM
python3 english_zap_bot.py
