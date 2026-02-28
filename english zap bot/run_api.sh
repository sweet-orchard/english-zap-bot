#!/usr/bin/env bash
# Run the English Zap API server (TTS + webapp + sync)
# Usage: ./run_api.sh

cd "$(dirname "$0")"
source ../venv/bin/activate
python3 api_server.py
