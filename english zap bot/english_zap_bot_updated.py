"""
English Zap Bot launcher.

This file is kept as the runnable entrypoint and injects your
existing credentials as defaults, then starts the hardened bot
implementation from english_zap_bot.py.

Run:
  python english_zap_bot_updated.py
"""

import os
import sys
from pathlib import Path

# Keep your provided values as defaults.
os.environ.setdefault("ENGLISH_ZAP_BOT_TOKEN", "8292063303:AAHlMCyMQFhIfXiM_g5Y7XeMb-ejYaPLnL4")
os.environ.setdefault("ENGLISH_ZAP_GEMINI_KEY", "AIzaSyBu_I221fmPJl8zdEtEWNkQ4djHgwsqW28")
os.environ.setdefault("ENGLISH_ZAP_OWNER_CHAT_ID", "861217697")
os.environ.setdefault("ENGLISH_ZAP_VOICE", "en-GB-RyanNeural")
os.environ.setdefault("ENGLISH_ZAP_WEBAPP_URL", "https://engzap.chikpixels.com")

# Ensure sibling import works no matter where python is launched from.
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from english_zap_bot import main


if __name__ == "__main__":
    main()
