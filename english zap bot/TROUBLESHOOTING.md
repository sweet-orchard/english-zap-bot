# English Zap — Troubleshooting Guide

## Quick checklist

| Symptom | Cause | Fix |
|---------|-------|-----|
| **Port 8765 already in use** | Old API process still running | `lsof -i :8765` then `kill <PID>` |
| **Invalid token / 404 from Telegram** | Wrong or placeholder token in `.env` | Put real token from @BotFather in `ENGLISH_ZAP_BOT_TOKEN` |
| **Gemini API error** | See error text in definition area | **403** → Enable Generative Language API, check key. **400 location** → API not in your region, enable billing. **401** → Invalid key. **429** → Rate limit, wait and retry. |
| **TTS / sync fails in webapp** | API server not running or wrong URL | Start `./run_api.sh`; on localhost, API URL should be `http://localhost:8765` |
| **Mini App (Telegram menu) doesn't open** | Webapp URL in `.env` points to dead tunnel | Run `cloudflared tunnel --url http://localhost:8765`, copy new URL, update `ENGLISH_ZAP_WEBAPP_URL` in `.env`, restart bot |
| **Sync shows "Немає URL сервера"** | API URL empty | In Settings → API → URL сервера, set `http://localhost:8765` |
| **Sync shows "Помилка" / error** | Wrong User ID or no words yet | Enter your Telegram User ID (get from @userinfobot); use /word in bot first so `words_{id}.json` exists |
| **"python: command not found"** | macOS uses `python3` | Use `./run_all.sh` (already fixed) |

---

## Common issues explained

### 1. Mini App URL (Telegram menu button)
`ENGLISH_ZAP_WEBAPP_URL` must be an **HTTPS** URL. Quick tunnels create a new URL each run. If you closed the tunnel, the old URL stops working. You need to:

1. Start API: `./run_api.sh` (or `./run_all.sh`)
2. Run `./run_tunnel.sh` (or `cloudflared tunnel --url http://localhost:8765`)
3. Copy the new `https://...trycloudflare.com` URL
4. Update `ENGLISH_ZAP_WEBAPP_URL` in `.env`
5. Restart the bot: `./run_bot.sh`

### 2. Sync requires matching User ID
The webapp syncs words from the API's `user_words/{user_id}`. The bot writes words to `words_{user_id}.json`. These use the **Telegram user ID**. If you open the webapp in a browser (not inside Telegram), you must enter your Telegram User ID manually (Settings → Data → Telegram User ID, or the input in the sync bar).

### 3. Words appear only after using the bot
The sync pulls words the bot has already sent you. Use the bot first (e.g. /word, /start), then sync in the webapp.

### 4. Gemini errors — what they mean
The app now shows clearer error messages:
- **403 Permission denied** → Enable [Generative Language API](https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com), check API key restrictions
- **400 Location not supported** → Gemini may not be available in your region; enable billing in Google AI Studio, or try a VPN
- **400 Billing required** → Enable billing in [Google AI Studio](https://aistudio.google.com)
- **401 Invalid API key** → Get a new key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **429 Rate limit** → Wait a minute and try again

---

## Restart everything

```bash
# Kill anything on port 8765
lsof -i :8765
kill <PID>

# Start fresh
cd "/Users/virasaienko/Desktop/english zap bot/english zap bot"
./run_all.sh
```

Then open **http://localhost:8765/** in your browser.
