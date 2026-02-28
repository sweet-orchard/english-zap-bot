# Raspberry Pi Telegram Bots System Documentation

## Overview

This Raspberry Pi runs multiple Telegram bots stored on a USB flash drive. The main data and code are located on the flash drive to minimize SD card usage.

---

## Flash Drive Structure

```
/media/usb/
├── bots/                          # Main bots directory
│   ├── english zap bot/           # English learning Telegram bot
│   │   ├── english_zap_bot.py     # Main Telegram bot (v3 with Mini App support)
│   │   ├── english_zap_bot_updated.py  # Updated version
│   │   ├── api_server.py          # FastAPI server for TTS & data sync
│   │   ├── english_zap_webapp.html # Web app for the Mini App
│   │   └── english_zap_bot_data.json   # User levels & chat IDs
│   │
│   ├── user_words/                # Per-user word collections
│   │   ├── words_861217697.json   # Words for user 861217697
│   │   ├── words_5911786900.json  # Words for user 5911786900
│   │   └── words_7537333010.json  # Words for user 7537333010
│   │
│   ├── venv/                      # Python virtual environment for bots
│   │   └── (python packages)
│   │
│   ├── krishna-book-telegram-bot-main/  # Hindu scripture bot
│   │   ├── bot.py
│   │   ├── progress.json
│   │   └── scheduled_users.json
│   │
│   ├── water-notifications-bot/   # Hydration reminder bot
│   │   ├── bot.py
│   │   ├── aquabot.db             # SQLite database
│   │   └── user_data.json
│   │
│   └── workout-bot/               # Workout tracking bot
│       └── workout-tracker-bot/
│           └── bot.py
│
├── anki/                          # Anki flashcard data
├── anki-data/                     # Anki app data
└── run-anki.sh                   # Script to run Anki
```

---

## How Everything Connects

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI OS                              │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐ │
│  │ Telegram    │    │ Cloudflared │    │ System Services     │ │
│  │ Bot Running │    │ (Tunnel)    │    │ (systemd)           │ │
│  └──────┬──────┘    └──────┬──────┘    └──────────┬──────────┘ │
│         │                  │                       │             │
│         ▼                  ▼                       ▼             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              USB FLASH DRIVE (/media/usb/)                  ││
│  │                                                              ││
│  │  ┌─────────────────┐    ┌─────────────────────────────┐    ││
│  │  │ english_zap_bot │    │ API Server (FastAPI)       │    ││
│  │  │ (python-telegram │    │ Port 8000                  │    ││
│  │  │ -bot)           │◄──►│ - /tts (Edge TTS)           │    ││
│  │  │                 │    │ - /user_words/{id}          │    ││
│  │  │ Listens for     │    │ - /levels                   │    ││
│  │  │ Telegram msgs   │    └─────────────────────────────┘    ││
│  │  └────────┬────────┘                   ▲                    ││
│  │           │                            │                    ││
│  │           ▼                            │                    ││
│  │  ┌─────────────────┐                 │                    ││
│  │  │ User Data        │                 │                    ││
│  │  │ - user_levels    │                 │                    ││
│  │  │ - user_chat_ids  │◄────────────────┘                    ││
│  │  │ - words_{id}.json│                                        ││
│  │  └─────────────────┘                                        ││
│  │                                                              ││
│  └──────────────────────────────────────────────────────────────││
│                                                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │                INTERNET                                       ││
│  │  ┌──────────────┐    ┌────────────────┐    ┌────────────┐  ││
│  │  │ Telegram API │    │ Cloudflare     │    │ External    │  ││
│  │  │ (api.telegram│    │ Tunnel         │    │ Services    │  ││
│  │  │ .org)        │◄──►│ (cloudflared) │◄──►│ - Datamuse  │  ││
│  │  │              │    │                │    │ - Edge TTS  │  ││
│  │  └──────────────┘    └────────────────┘    │ - Gemini AI │  ││
│  │                                              └────────────┘  ││
│  └──────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

---

## Bot 1: English Zap Bot (Main Bot)

### What It Does
- Telegram bot that teaches English vocabulary
- Sends daily words based on user level (zero/beginner/intermediate/advanced)
- Provides word definitions, examples, and audio pronunciation (Edge TTS)
- Integrates with a web-based Mini App for interactive learning

### Key Files
| File | Purpose |
|------|---------|
| `english_zap_bot.py` | Main Telegram bot using `python-telegram-bot` library |
| `api_server.py` | FastAPI server providing TTS and data sync endpoints |
| `english_zap_webapp.html` | Web app that loads inside Telegram as a Mini App |

### Configuration (in `english_zap_bot.py`)
```python
BOT_TOKEN = "8292063303:AAHlMCyMQFhIfXiM_g5Y7XeMb-ejYaPLnL4"  # Telegram Bot API token
GEMINI_KEY = "AIzaSyBu_I221fmPJl8zdEtEWNkQ4djHgwsqW28"          # Google Gemini API key
OWNER_CHAT_ID = 861217697                                         # Owner/user Telegram ID
VOICE = "en-GB-RyanNeural"                                        # Microsoft Edge TTS voice
WEBAPP_URL = "https://YOUR_TUNNEL_URL_HERE"                      # Cloudflare tunnel URL
DATA_FILE = "/media/usb/bots/english_zap_bot_data.json"         # User levels storage
WORDS_DIR = "/media/usb/bots/user_words"                         # Per-user word storage
```

### How It Works

1. **Telegram Bot** (`english_zap_bot.py`):
   - Listens for commands: `/start`, `/word`, `/level`, `/words`, `/webapp`
   - When user requests a word, fetches from Datamuse API based on level/topic
   - Sends word + definition + audio (via Edge TTS) to Telegram
   - Records word to user's personal word list

2. **API Server** (`api_server.py`):
   - Runs on port 8000
   - `/tts` endpoint: Converts text to MP3 audio (Edge TTS)
   - `/user_words/{user_id}`: Returns all words a user has learned
   - `/levels`: Returns all user levels
   - Called by the webapp to sync data

3. **Web App** (`english_zap_webapp.html`):
   - Embedded in Telegram as a Mini App
   - Shows user's word list
   - Plays pronunciation audio
   - Communicates with API server for data

4. **Data Storage**:
   - `english_zap_bot_data.json`: User levels and chat IDs
     ```json
     {
       "user_levels": {"861217697": "zero", "5911786900": "zero", "7537333010": "beginner"},
       "user_chat_ids": [861217697, 7537333010, 5911786900]
     }
     ```
   - `user_words/words_{user_id}.json`: Each user's learned words

### Running the Bot

```bash
# Activate virtual environment
source /media/usb/bots/venv/bin/activate

# Run the Telegram bot
python /media/usb/bots/english\ zap\ bot/english_zap_bot.py

# In another terminal, run the API server
python /media/usb/bots/english\ zap\ bot/api_server.py
```

---

## Bot 2: Krishna Book Telegram Bot

### What It Does
- Sends daily verses/chapters from Hindu scriptures (Bhagavad Gita, etc.)
- Users can schedule daily readings
- Tracks reading progress

### Key Files
| File | Purpose |
|------|---------|
| `bot.py` | Main bot logic |
| `progress.json` | User reading progress |
| `scheduled_users.json` | Users with scheduled deliveries |

### Configuration
Located in `/home/raspberrymilkshake/Downloads/krishna-book-telegram-bot-main/`

---

## Bot 3: Water Notifications Bot

### What It Does
- Reminds users to drink water
- Tracks hydration goals
- Stores user data in SQLite database

### Key Files
| File | Purpose |
|------|---------|
| `bot.py` | Main hydration bot |
| `aquabot.db` | SQLite database with user hydration logs |
| `user_data.json` | User preferences |

---

## Bot 4: Workout Tracker Bot

### What It Does
- Tracks workout sessions
- Logs exercise data

### Key Files
| File | Purpose |
|------|---------|
| `workout-tracker-bot/bot.py` | Main workout bot |

---

## Cloudflare Tunnel (cloudflared)

### Purpose
Creates a public URL to access services running on the Raspberry Pi (like the API server and webapp) without needing port forwarding on your router.

### Configuration Files
- `/home/raspberrymilkshake/.cloudflared/` - Cloudflare tunnel config
- Logs: `cloudflared.log`, `cloudflared_new.log`

### How It Works
1. `cloudflared` runs as a service
2. Creates a tunnel to Cloudflare's network
3. External users can access `https://your-subdomain.trycloudflare.com`
4. Requests are forwarded to localhost on the Pi

---

## Starting Services

### Manual Start
```bash
# Start Cloudflare tunnel
cloudflared tunnel --url http://localhost:8000

# Activate venv and start bots
source /media/usb/bots/venv/bin/activate
python /media/usb/bots/english\ zap\ bot/english_zap_bot.py

# Start API server (in another terminal)
source /media/usb/bots/venv/bin/activate
python /media/usb/bots/english\ zap\ bot/api_server.py
```

### Auto-Start (systemd)
The file `krishna-bot.service` shows how to auto-start bots using systemd:
```ini
[Unit]
Description=Krishna Book Telegram Bot
After=network.target

[Service]
Type=simple
User=raspberrymilkshake
WorkingDirectory=/home/raspberrymilkshake/Downloads/krishna-book-telegram-bot-main
ExecStart=/home/raspberrymilkshake/venv-telegram-bot/bin/python /home/raspberrymilkshake/Downloads/krishna-book-telegram-bot-main/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## External Services Used

| Service | Purpose | API URL |
|---------|---------|---------|
| Telegram Bot API | Send/receive messages | `api.telegram.org` |
| Datamuse API | Word definitions & examples | `api.datamuse.com` |
| Microsoft Edge TTS | Text-to-speech audio | Edge TTS library |
| Google Gemini | AI-powered responses | `generativelanguage.googleapis.com` |
| Cloudflare Tunnel | Public URL forwarding | Cloudflare network |

---

## Moving to Mac

### What You Need to Transfer

1. **Entire `/media/usb/bots/` folder** - Contains all bot code and data
2. **Python dependencies** - Recreate virtual environment on Mac

### On Mac Setup

1. Copy the `bots` folder from flash drive to Mac
2. Install Python 3 (using Homebrew or python.org)
3. Create a new virtual environment:
   ```bash
   cd bots
   python3 -m venv venv
   source venv/bin/activate
   pip install python-telegram-bot httpx edge-tts fastapi uvicorn python-multipart
   ```

4. Update paths in bot files (remove `/media/usb/` prefix):
   - Change `DATA_FILE = "/media/usb/bots/..."` to `"bots/..."`
   - Change `WORDS_DIR = "/media/usb/bots/..."` to `"bots/user_words"`

5. Update API server paths similarly

6. Get a new Cloudflare tunnel or use localtunnel/ngrok for testing

### Environment Variables (Optional)
Instead of hardcoding tokens, use environment variables:
```python
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
```

Then run: `export BOT_TOKEN="your-token" python bot.py`

---

## Troubleshooting

### Bot not responding
1. Check bot is running: `ps aux | grep python`
2. Check logs for errors
3. Verify Telegram bot token is valid
4. Check internet connection

### Webapp not loading
1. Verify API server is running on port 8000
2. Check Cloudflare tunnel is active
3. Verify WEBAPP_URL matches the tunnel URL

### Data not syncing
1. Check `/user_words` directory exists and is writable
2. Verify JSON files have correct permissions

---

## File Locations Summary

| Component | Location |
|-----------|----------|
| English Zap Bot | `/media/usb/bots/english zap bot/` |
| API Server | `/media/usb/bots/english zap bot/api_server.py` |
| User Data | `/media/usb/bots/english_zap_bot_data.json` |
| User Words | `/media/usb/bots/user_words/` |
| Krishna Bot | `/home/raspberrymilkshake/Downloads/krishna-book-telegram-bot-main/` |
| Water Bot | `/media/usb/bots/water-notifications-bot/` |
| Workout Bot | `/media/usb/bots/workout-bot/` |
| Python venv | `/media/usb/bots/venv/` |
| Cloudflared | `/home/raspberrymilkshake/.cloudflared/` |
| Bot logs | `/home/raspberrymilkshake/english_zap_bot.log` |

---

*Generated for transferring the Raspberry Pi Telegram Bots system to macOS*
