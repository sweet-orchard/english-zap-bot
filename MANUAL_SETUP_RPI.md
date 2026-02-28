# 🛠 Manual Setup Guide (Raspberry Pi)

If your Mini App is failing to load, follow these manual steps one by one to ensure the connection is established correctly.

## 1. Start the API Server
Open a terminal (or tmux session) and run:
```bash
cd ~/english_zap_bot/"english zap bot"
source venv/bin/activate
python3 api_server.py
```
**Verify it's working**: Open another terminal and run:
```bash
curl http://localhost:8765/health
```
You should see `{"status":"ok","service":"English Zap API"}`.

---

## 2. Start the Cloudflare Tunnel
Open a **new** terminal (or tmux session) and run:
```bash
cloudflared tunnel --url http://localhost:8765
```
**Important**: Look for a line that says:
`+  https://your-random-name.trycloudflare.com`
**Copy this URL exactly.**

---

## 3. Update your .env Configuration
You must tell the Telegram Bot which URL to use for the Mini App button.
1. Open the `.env` file in the `english zap bot` folder:
   ```bash
   nano ~/english_zap_bot/"english zap bot"/.env
   ```
2. Find the line `ENGLISH_ZAP_WEBAPP_URL`.
3. Change it to your new URL. Here is the **reference content** for your `.env` file (you can copy this):

```env
# English Zap — Raspberry Pi setup
# Fill in your values.

# Required: Telegram Bot token from @BotFather
ENGLISH_ZAP_BOT_TOKEN=8292063303:AAHlMCyMQFhIfXiM_g5Y7XeMb-ejYaPLnL4

# Recommended: Google Gemini API key for word definitions
ENGLISH_ZAP_GEMINI_KEY=AIzaSyDASTLISEt7D2kM_E1xJ24mK4Sgdc7qCuA
ENGLISH_ZAP_GEMINI_MODEL=gemini-2.5-flash

# Your Telegram user ID (optional)
ENGLISH_ZAP_OWNER_CHAT_ID=861217697

# Webapp URL — for Telegram Mini App (must be HTTPS)
# Update this with the URL from cloudflared!
ENGLISH_ZAP_WEBAPP_URL=https://your-random-name.trycloudflare.com

# Voice for Edge TTS
ENGLISH_ZAP_VOICE=en-GB-RyanNeural
```
4. Press `Ctrl + O`, `Enter` (to save), then `Ctrl + X` (to exit).

---

## 4. Start the Telegram Bot
Open a **third** terminal (or tmux session) and run:
```bash
cd ~/english_zap_bot/"english zap bot"
source venv/bin/activate
python3 english_zap_bot.py
```

---

## ⚠️ Why might it fail? (Common Issues)

1. **Wait for Tunnel**: The Mini App button in Telegram caches the URL for a bit. After restarting the bot, try to close the bot chat and reopen it.
2. **Port Blocked**: Ensure no other process is using port 8765 (`fuser 8765/tcp`).
3. **HTTPS required**: Telegram **only** allows `https` URLs for Mini Apps. If your `.env` starts with `http://`, it will fail.
4. **Missing dependencies**: If you get a "ModuleNotFoundError", run `pip install -r requirements.txt` again inside the virtual environment.
