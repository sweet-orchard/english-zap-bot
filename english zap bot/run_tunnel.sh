#!/usr/bin/env bash
# Run Cloudflare tunnel for Telegram Mini App (HTTPS required)
# 1. Start API first: ./run_api.sh (or ./run_all.sh)
# 2. Run this: ./run_tunnel.sh
# 3. Copy the https://...trycloudflare.com URL
# 4. Update ENGLISH_ZAP_WEBAPP_URL in .env
# 5. Restart the bot: ./run_bot.sh

echo "Starting tunnel to http://localhost:8765 ..."
echo "After it starts, copy the https://...trycloudflare.com URL"
echo "Then update .env: ENGLISH_ZAP_WEBAPP_URL=<that-url>"
echo "Then restart the bot with ./run_bot.sh"
echo ""
cloudflared tunnel --url http://localhost:8765
