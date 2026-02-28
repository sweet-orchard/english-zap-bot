#!/usr/bin/env bash
# Run the English Zap Telegram bot
# Usage: ./run_bot.sh
# Start the API first: ./run_api.sh

cd "$(dirname "$0")"
source ../venv/bin/activate
python3 english_zap_bot.py
