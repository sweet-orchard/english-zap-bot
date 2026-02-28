# English Zap — macOS Setup

Run everything locally on your Mac.

## Quick start

### 1. Configure `.env`

Edit `.env` and add your keys:

- `ENGLISH_ZAP_BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
- `ENGLISH_ZAP_GEMINI_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey)

### 2. Install dependencies (once)

```bash
cd "english zap bot"   # the inner project folder
source ../venv/bin/activate
pip install -r ../requirements.txt
```

### 3. Run

**Option A — API + Bot together**

```bash
./run_all.sh
```

**Option B — Separate terminals**

Terminal 1:
```bash
./run_api.sh
```

Terminal 2:
```bash
./run_bot.sh
```

### 4. Use the webapp

1. Open **http://localhost:8765/** in a browser.
2. Set your Gemini API key in Settings (if not using `.env`).
3. API URL is auto-detected on localhost.

### 5. Telegram Mini App (optional)

To use the webapp inside Telegram:

1. Start the API: `./run_api.sh`
2. Run a tunnel: `cloudflared tunnel --url http://localhost:8765`
3. Copy the `https://...trycloudflare.com` URL
4. Set in `.env`: `ENGLISH_ZAP_WEBAPP_URL=https://your-tunnel-url.trycloudflare.com`
5. In [@BotFather](https://t.me/BotFather): set the Mini App URL to that HTTPS URL

## Files

| File | Purpose |
|------|---------|
| `run_api.sh` | Starts API server (TTS, webapp, sync) |
| `run_bot.sh` | Starts Telegram bot |
| `run_all.sh` | Runs API + bot together |
| `.env` | Configuration (keep tokens secret) |
